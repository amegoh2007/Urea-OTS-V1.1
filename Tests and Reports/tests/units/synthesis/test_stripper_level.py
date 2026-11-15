"""LIC-322501 on its own: the direct-acting velocity form on the plant DCS's tuning.

The loop closed on the sump is `test_stripper_sump` section 2; the controller against V1's is
`tests/equivalence/test_stripper_sump_equivalence`.
"""

from __future__ import annotations

import pytest

from ureasim.data.unit_322e001 import LEVEL_SP_DES_PCT, LIC_322501_KC, LV_322501_OPEN_DES_PCT
from ureasim.units.synthesis.stripper_level import BottomLevelLoop


def test_at_its_set_point_the_loop_holds_its_design_stroke():
    lic = BottomLevelLoop()
    assert lic.step(LEVEL_SP_DES_PCT, 0.1) == LV_322501_OPEN_DES_PCT


def test_a_set_point_move_kicks_the_valve_by_the_gain():
    """The proportional term acts on the error, so a set-point step kicks the stroke by -Kc . dSP
    on the first tick (plus that tick's integral), as the plant's DCS does."""
    lic = BottomLevelLoop()
    lic.step(LEVEL_SP_DES_PCT, 0.1)
    lic.sp = LEVEL_SP_DES_PCT + 10.0
    op = lic.step(LEVEL_SP_DES_PCT, 0.1)
    assert op - LV_322501_OPEN_DES_PCT == pytest.approx(-LIC_322501_KC * 10.0, rel=1e-3)


def test_manual_holds_the_stroke_and_a_bad_level_freezes_it():
    lic = BottomLevelLoop(mode="MAN", op=30.0)
    assert lic.step(80.0, 0.1) == 30.0
    lic = BottomLevelLoop()
    lic.step(60.0, 0.1)
    op = lic.op
    assert lic.step(float("nan"), 0.1) == op and lic.pv_bad


def test_publish_writes_the_settled_level_as_the_faceplate_pv():
    lic = BottomLevelLoop()
    lic.publish(42.0)
    assert lic.pv == 42.0
