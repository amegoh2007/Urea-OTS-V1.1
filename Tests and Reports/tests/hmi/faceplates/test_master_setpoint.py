"""The MASTER SP faceplate — `ureasim.hmi.faceplates.master_setpoint`.

Pinned on the design packet (master ON at 5.01 bar a): only the master set point is editable, shown
in bar g and sent in bar a; OFF unlocks the legs, whose SET sends each leg's set point; every
command is one the engine takes.
"""

from __future__ import annotations

import pytest

from ureasim.engine.command import apply_command
from ureasim.engine.plant import build_plant
from ureasim.hmi.faceplates.master_setpoint import MasterSetpointFaceplate
from ureasim.hmi.state_access import ATM_BAR


def test_on_the_master_set_point_alone(bridge):
    face = MasterSetpointFaceplate(bridge)
    face.show()
    assert face.mode_chip.text() == "ON" and face.sp_field.isEnabled()
    assert face.sp_field.text() == f"{5.01 - ATM_BAR:.2f}"
    assert not any(leg["sp"].isEnabled() for leg in face.legs.values())
    face.sp_field.setText("4.0")
    face.primary.click()
    assert bridge.sent[-1] == {"type": "master207_set", "sp": pytest.approx(4.0 + ATM_BAR)}
    face.close()


def test_off_the_legs_are_set_each(bridge, packet):
    face = MasterSetpointFaceplate(bridge)
    face.show()
    ss = dict(packet["STEAM_SYSTEM"], MASTER_SP_329207={"on": False, "sp": 5.01, "pv": 5.01})
    bridge.publish(dict(packet, STEAM_SYSTEM=ss))
    assert face.mode_chip.text() == "OFF" and not face.sp_field.isEnabled()
    face.legs["B"]["sp"].setText("3.9")
    face.primary.click()
    sent = {c["type"]: c for c in bridge.sent}
    assert sent["pic329207b_set"]["sp"] == pytest.approx(3.9 + ATM_BAR)
    plant = build_plant()[1]
    assert apply_command(plant, {"type": "master207_set", "on": False}).ok
    assert all(apply_command(plant, c).ok for c in bridge.sent)
    face.close()
