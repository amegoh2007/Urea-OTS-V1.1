"""The instructor's panel — `ureasim.hmi.instructor.panel`.

Pinned: each control sends one command — the pacing, FREEZE / RUN, RESET only once confirmed,
each malfunction armed and cleared, 322E002's tube leak with the rate its box holds (B-90), the CO2
demand on 320K002 within V1's 0 to 120 % of the design feed, an exercise saved and, once
confirmed, restored; the pacing and the CO2 demand shown are the packet's; every answer is shown
with its reason; and every command is one the engine session takes. The single console (decision
149) has no roster and no unit assignment.
"""

from __future__ import annotations

import pytest

from ureasim.data.unit_321 import CO2_DES_KGH
from ureasim.engine.session import EngineSession
from ureasim.hmi.instructor import InstructorPanel


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
    assert panel.co2_now.text() == "now 54.62 t/h"
    assert panel.co2_demand.value() == pytest.approx(CO2_DES_KGH / 1000.0)
    assert panel.co2_demand.maximum() == pytest.approx(1.2 * CO2_DES_KGH / 1000.0, abs=5e-4)
    panel.co2_demand.setValue(60.08)
    panel.co2()
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
        {"type": "co2_set", "value": 60.08},
        {"type": "snapshot_save", "name": "shift-a", "note": "before the trip"},
        {"type": "snapshot_load", "name": "shift-a"}, {"type": "reset_sim"}]
    session = EngineSession(tmp_path)
    for cmd in bridge.sent:
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


def test_a_saved_exercise_refreshes_the_list(bridge):
    panel, _ = _panel(bridge)
    panel.name_field.setText("shift-b")
    panel.save()
    bridge.command_result.emit(1, True, "")
    assert bridge.requests == 1
    bridge.exercises_received.emit([], "no engine attached")
    assert panel.message.text() == "no engine attached"
    panel.close()
