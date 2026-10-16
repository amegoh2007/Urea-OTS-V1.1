"""The feed pumps' speed faceplates — `ureasim.hmi.faceplates.speed`.

Pinned on the design packet (321P002A stopped in MAN, 321P002B running in CAS): a stopped pump's
faceplate offers MAN alone and says why; a mode button sends the mode at once; SET sends the
output in MAN and, in CAS, the ratio master's set point; every command is one the engine takes.
"""

from __future__ import annotations

from ureasim.engine.command import apply_command
from ureasim.engine.plant import build_plant
from ureasim.hmi.faceplates.speed import SpeedFaceplate


def test_a_stopped_pump_offers_man_alone(bridge):
    face = SpeedFaceplate(bridge, "SIC_321950")
    face.show()
    assert face.mode_chip.text() == "MAN" and "PUMP STOPPED — MAN" in face.status.text()
    assert [m for m, b in face.mode_buttons.items() if b.isEnabled()] == ["MAN"]
    face.mv_field.setText("35")
    face.set_button.click()
    assert bridge.sent[-1] == {"type": "controller_set", "id": "SIC_321950", "mode": "MAN",
                               "op": 35.0}
    assert apply_command(build_plant()[1], bridge.sent[-1]).ok
    face.close()


def test_in_cas_set_writes_the_ratio_masters_set_point(bridge):
    face = SpeedFaceplate(bridge, "SIC_321951")
    face.show()
    assert face.mode_chip.text() == "CAS"
    assert all(b.isEnabled() for b in face.mode_buttons.values())
    assert face.fsp_field.isEnabled() and not face.sp_field.isEnabled()
    face.fsp_field.setText("3.6")
    face.set_button.click()
    assert bridge.sent[-1] == {"type": "ratio_set", "sp": 3.6}
    face.mode_buttons["AUTO"].click()
    assert bridge.sent[-1] == {"type": "controller_set", "id": "SIC_321951", "mode": "AUTO"}
    plant = build_plant()[1]
    assert all(apply_command(plant, c).ok for c in bridge.sent)
    face.close()
