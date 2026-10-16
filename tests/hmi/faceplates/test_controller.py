"""The loop faceplate — `ureasim.hmi.faceplates.controller`.

Pinned on the design plant's packet: a loop block's PV, set point, output and mode are shown; the
mode buttons choose what SET sends — the output in MAN, the set point in AUTO (bumpless from the
PV), nothing in CAS but the mode — and what it sends the engine takes; a cascade slave names its
master; a pressure is shown in gauge and sent in absolute; a loop the packet carries no block for is
not on this model and sends nothing; the field the operator types in is not overwritten; the answer
to the faceplate's own command is shown with its reason.
"""

from __future__ import annotations

import pytest

from ureasim.engine.command import apply_command
from ureasim.engine.plant import build_plant
from ureasim.hmi.faceplates.controller import ControllerFaceplate, loop_spec
from ureasim.hmi.state_access import ATM_BAR

LIC = {"t": "ind", "tag": "LIC-323501", "bind": "RECIRC_323.C003.LIC_323501.pv", "u": "%",
       "mode": "RECIRC_323.C003.LIC_323501.mode"}
PIC = {"t": "ind", "tag": "PIC-329202", "bind": "RECIRC_323.C003.PIC_329202.pv", "u": "BAR A",
       "mode": "RECIRC_323.C003.PIC_329202.mode", "cas": True}
FIC_328406 = {"t": "ind", "tag": "FIC-328406", "bind": "ABSORB_328.D003.FIC_328406.pv",
              "u": "M3/H"}


def _open(bridge, element):
    face = ControllerFaceplate(bridge, loop_spec(element))
    face.show()
    return face


def test_the_block_is_shown_and_man_sends_the_output_the_engine_takes(bridge):
    face = _open(bridge, LIC)
    assert face.pv_field.text() == "60.0 %"
    assert (face.sp_field.text(), face.op_field.text()) == ("60.000", "56.600")
    assert face.mode_chip.text() == "AUTO" and face.sp_field.isReadOnly() is False
    face.mode_buttons["MAN"].click()
    assert face.op_field.isReadOnly() is False and face.sp_field.isReadOnly()
    face.op_field.setText("40")
    face.set_button.click()
    cmd = bridge.sent[-1]
    assert cmd == {"type": "r323_ctrl_set", "id": "LIC-323501", "mode": "MAN", "op": 40.0}
    assert apply_command(build_plant()[1], cmd).ok
    face.close()


def test_auto_from_man_takes_the_pv_as_set_point(bridge, packet):
    face = _open(bridge, LIC)
    face.mode_buttons["MAN"].click()
    face.sp_field.setText("1.0")
    face.mode_buttons["AUTO"].click()
    assert face.sp_field.text() == "60.000"
    face.set_button.click()
    assert bridge.sent[-1] == {"type": "r323_ctrl_set", "id": "LIC-323501", "mode": "AUTO",
                               "sp": 60.0}
    face.close()


def test_a_slave_names_its_master_and_a_pressure_is_gauge_on_screen(bridge):
    face = _open(bridge, PIC)
    assert face.mode_chip.text() == "CAS" and face.mode_buttons["CAS"].isVisibleTo(face)
    assert "TIC-323007" in face.note.text()
    assert face.pv_field.text() == f"{3.9 - ATM_BAR:.1f} BARG"
    face.mode_buttons["AUTO"].click()
    face.sp_field.setText("3.0")
    face.set_button.click()
    assert bridge.sent[-1]["sp"] == pytest.approx(3.0 + ATM_BAR, abs=1e-12)
    face.close()


def test_fic_328406_offers_its_decided_cascade(bridge):
    face = _open(bridge, FIC_328406)
    assert face.mode_buttons["CAS"].isVisibleTo(face) and "LIC-328505" in face._note("CAS")
    face.close()


def test_a_loop_with_no_block_is_not_on_this_model(bridge):
    face = _open(bridge, {"t": "ind", "tag": "TIC-399999", "bind": "TI_top1", "u": "C"})
    assert not face.set_button.isEnabled() and "not on this model" in face.note.text()
    face.set_button.click()
    assert bridge.sent == []
    face.close()


def test_the_typed_field_is_kept_and_the_answer_is_shown(bridge, packet):
    face = _open(bridge, LIC)
    face.mode_buttons["MAN"].click()
    face.op_field.setText("12.5")
    bridge.publish(packet)
    assert face.op_field.text() == "12.5"                  # the operator's, left as typed
    assert face.sp_field.text() == "60.000"                # the plant's, following
    face.set_button.click()
    bridge.command_result.emit(len(bridge.sent), False, "LIC-323501 offers MAN, AUTO, not X")
    assert face.message.text() == "REFUSED: LIC-323501 offers MAN, AUTO, not X"
    face.close()
