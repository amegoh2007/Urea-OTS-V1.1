"""The instructor's panel — `ureasim.hmi.instructor.panel`.

Pinned: each control sends one command — the pacing, FREEZE / RUN, RESET only once confirmed,
each malfunction armed and cleared, 322E002's tube leak with the rate its box holds (B-90), an
exercise saved and, once confirmed, restored; the roster the
server sends is shown and a station's plant assigned or released; the pacing shown is the packet's;
every answer is shown with its reason; and every command is one the server lets an instructor send
and the engine session takes.
"""

from __future__ import annotations

from ureasim.engine.session import EngineSession
from ureasim.hmi.instructor import InstructorPanel
from ureasim.net import protocol
from ureasim.net.protocol import Role

ROSTER = [{"station": "instructor", "role": "instructor", "sections": None},
          {"station": "trainee-a", "role": "operator", "sections": ["323"]}]


def _panel(bridge, answer=True):
    asked = []

    def confirm(title, text):
        asked.append(title)
        return answer
    panel = InstructorPanel(bridge, confirm=confirm)
    panel.show()
    return panel, asked


def test_the_exercise_controls(bridge, packet, tmp_path):
    panel, asked = _panel(bridge)
    panel.refresh(packet)
    assert panel.pacing_buttons["SLOW"].property("active") is True
    panel.pacing_buttons["FAST"].click()
    panel.freeze(True)
    panel.freeze(False)
    panel.fault("A", True)
    panel.fault("A", False)
    assert panel.fault_rates["322E002"].value() == 10.0
    panel.fault_rates["322E002"].setValue(2.5)
    panel.fault("322E002", True)
    panel.fault("322E002", False)
    panel.name_field.setText("shift-a")
    panel.note_field.setText("before the trip")
    panel.save()
    panel.show_exercises(["shift-a"], "")
    panel.exercise_list.setCurrentRow(0)
    panel.restore()
    panel.reset()
    assert asked == ["Restore shift-a?", "Reset the simulation?"]
    assert bridge.sent == [
        {"type": "set_sim_mode", "mode": "FAST"}, {"type": "freeze", "on": True},
        {"type": "freeze", "on": False}, {"type": "trigger_fault", "id": "A"},
        {"type": "clear_fault", "id": "A"},
        {"type": "trigger_fault", "id": "322E002", "rate": 2.5},
        {"type": "clear_fault", "id": "322E002"},
        {"type": "snapshot_save", "name": "shift-a", "note": "before the trip"},
        {"type": "snapshot_load", "name": "shift-a"}, {"type": "reset_sim"}]
    session = EngineSession(tmp_path)
    for cmd in bridge.sent:
        assert protocol.is_authorised(Role.INSTRUCTOR, cmd["type"])
        assert session.handle(cmd) == (True, ""), cmd
    panel.close()


def test_nothing_is_discarded_unconfirmed(bridge):
    panel, asked = _panel(bridge, answer=False)
    panel.reset()
    panel.show_exercises(["shift-a"], "")
    panel.exercise_list.setCurrentRow(0)
    panel.restore()
    assert len(asked) == 2 and bridge.sent == []
    panel.close()


def test_the_roster_and_the_assignment(bridge):
    panel, _ = _panel(bridge)
    bridge.roster_changed.emit(ROSTER)
    rows = [[panel.roster_table.item(r, c).text() for c in range(3)] for r in range(2)]
    assert rows == [["instructor", "instructor", "whole plant"],
                    ["trainee-a", "operator", "323"]]
    panel.assign()
    assert panel.message.text() == "choose a station" and bridge.sent == []
    panel.roster_table.selectRow(1)
    assert panel.section_boxes["323"].isChecked() and not panel.section_boxes["328"].isChecked()
    panel.section_boxes["328"].setChecked(True)
    panel.assign()
    panel.release()
    assert bridge.sent == [{"type": "assign", "station": "trainee-a", "sections": ["323", "328"]},
                           {"type": "assign", "station": "trainee-a", "sections": None}]
    bridge.command_result.emit(1, True, "")
    bridge.command_result.emit(2, False, "unknown section(s) 999")
    assert panel.message.text() == "whole plant to trainee-a: REFUSED — unknown section(s) 999"
    panel.close()


def test_a_saved_exercise_refreshes_the_list(bridge):
    panel, _ = _panel(bridge)
    panel.name_field.setText("shift-b")
    panel.save()
    bridge.command_result.emit(1, True, "")
    assert bridge.requests == 1
    bridge.exercises_received.emit([], "only an instructor lists exercises")
    assert panel.message.text() == "only an instructor lists exercises"
    panel.close()
