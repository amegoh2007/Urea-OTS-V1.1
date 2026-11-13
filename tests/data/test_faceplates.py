"""The faceplates' command table — `ureasim.data.faceplates` — against the engine that takes it.

Pinned: every hand station's command and payload field is accepted by the engine; V1's front end
sent ``value`` to three of them, which the engine (as V1's own handler) does not read; every loop
faceplate's command is an engine command, and every inline faceplate takes ``r323_ctrl_set``; every
cascade the notes name is a CAS the faceplate offers; FIC-328406 can be put in CAS (B-50); every
malfunction is one the engine injects; the speed controllers and the MASTER SP legs name engine
commands.
"""

from __future__ import annotations

import pytest

from ureasim.data import faceplates as fp
from ureasim.data.operator_commands import FACEPLATE_MODES
from ureasim.engine.command import PLANT_COMMANDS, apply_command
from ureasim.engine.plant import build_plant


@pytest.fixture()
def plant():
    return build_plant()[1]


@pytest.mark.parametrize("tag", sorted(fp.HAND_VALVES))
def test_every_hand_station_is_taken_by_the_engine(plant, tag):
    hv = fp.HAND_VALVES[tag]
    r = apply_command(plant, {"type": hv.command, hv.field: 40.0})
    assert r.ok, (tag, r.reason)


@pytest.mark.parametrize("tag", ["HIC-329605", "HIC-329606", "HIC-323605"])
def test_v1s_value_field_was_never_read_and_the_ports_op_is(plant, tag):
    """V1's front end sent ``value``; its handler read ``op`` and dropped the entry. The port's
    table sends ``op``, which the engine takes; ``value`` it refuses with the reason."""
    hv = fp.HAND_VALVES[tag]
    assert hv.field == "op"
    refused = apply_command(plant, {"type": hv.command, "value": 40.0})
    assert not refused.ok and "'op'" in refused.reason
    assert apply_command(plant, {"type": hv.command, "op": 40.0}).ok


def test_every_loop_command_is_an_engine_command():
    for tag in fp.LOOP_COMMANDS:
        assert fp.loop_command(tag) in PLANT_COMMANDS, tag
    for tag in FACEPLATE_MODES:
        assert fp.loop_command(tag) == ("r323_ctrl_set" if tag not in fp.LOOP_COMMANDS
                                        else fp.LOOP_COMMANDS[tag])
    assert fp.loop_command("TT-321001") is None


def test_every_cascade_the_notes_name_is_offered():
    for slave in fp.CAS_MASTERS:
        assert "CAS" in FACEPLATE_MODES[slave], slave
    for loop in fp.CAS_UNWIRED:
        assert "CAS" in FACEPLATE_MODES[loop], loop


def test_fic_328406_can_be_put_under_lic_328505(plant):
    """B-50's cascade: V1's whitelist offered MAN only, so no console could engage it."""
    r = apply_command(plant, {"type": "r323_ctrl_set", "id": "FIC-328406", "mode": "CAS"})
    assert r.ok, r.reason
    assert plant.loops["328C004"][0].fic_328406.loop.mode == "CAS"


@pytest.mark.parametrize("m", fp.MALFUNCTIONS, ids=lambda m: m.equipment)
def test_every_malfunction_is_one_the_engine_injects(plant, m):
    assert apply_command(plant, {"type": "trigger_fault", "id": m.fault_id}).ok
    assert apply_command(plant, {"type": "clear_fault", "id": m.fault_id}).ok


def test_the_speed_controllers_and_the_master_legs_are_engine_commands(plant):
    for cid in fp.SPEED_CONTROLLERS:
        assert apply_command(plant, {"type": "controller_set", "id": cid, "mode": "MAN"}).ok
    for _leg, _key, command, _caption in fp.MASTER_SP_LEGS:
        assert command in PLANT_COMMANDS
    assert set(fp.PUMP_TRIPS) == {"A", "B"}


def test_the_co2_feed_panels_command_is_the_engines_step(plant):
    """Decision 220: the command and field 322-1's CO2 FEED panel sends are the engine's
    ``co2_step``, and the only element that sends it is that panel."""
    from ureasim.data.screen_layout import OVERLAYS

    assert PLANT_COMMANDS[fp.CO2_STEP_COMMAND].__name__ == "_co2_step"
    assert apply_command(plant, {"type": fp.CO2_STEP_COMMAND, fp.CO2_STEP_FIELD: 1}).ok
    senders = [(sid, e["k"]) for sid, els in OVERLAYS.items() for e in els
               if e.get("cmd") == fp.CO2_STEP_COMMAND]
    assert senders == [("screen-322-1", "co2step")]
