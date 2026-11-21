"""Stage 2's four controllers — `ureasim.units.evaporation.second_evaporator_loops`.

Moved out of `second_evaporator` in session 133 (decision 252); the stage's tests drive them. This
file pins the seeds and that `second_evaporator` still hands out the same factories.
"""

from __future__ import annotations

from ureasim.data import unit_324 as d
from ureasim.data.unit_335 import LIC_324501_X_DES_PCT
from ureasim.units.evaporation import second_evaporator as se
from ureasim.units.evaporation import second_evaporator_loops as sl


def test_second_evaporator_re_exports_every_moved_name():
    """A caller of ``second_evaporator`` (and a saved exercise's class path) sees no change."""
    for name in sl.__all__:
        assert getattr(se, name) is getattr(sl, name)


def test_each_loop_is_seeded_at_the_design_point():
    """Set point and measurement at design, and each output at its design stroke."""
    tic, pic, vac = sl.tic_324002(), sl.pic_329212(), sl.pic_324203()
    assert (tic.sp, tic.pv, tic.op) == (d.E003_T_DES_C, d.E003_T_DES_C, d.E003_PCHEST_DES_BARA)
    assert pic.mode == "CAS" and pic.op == sl.PV_329212_CHEST.op_des_pct
    assert sl.pic_329212(sl.V1_CHEST).op == d.E003_OP_DES_PCT
    assert (vac.sp, vac.op) == (d.F003_P_DES_BARA, d.PV_324203_OP_DES_PCT)


def test_lic_324501_seeds_on_ac4_on_the_vendor_trim_and_on_v1():
    """AC4's header X 35 % (decision 224), LV-324501A's vendor stroke (decision 150), V1's 75 %."""
    assert sl.lic_324501().op == LIC_324501_X_DES_PCT
    assert sl.lic_324501(ac4=False).op == d.LV_324501A_OP_DES_PCT
    assert sl.lic_324501(vendor=False).op == d.LIC_324501_OP_DES_PCT
    for loop in (sl.lic_324501(), sl.lic_324501(vendor=False)):
        assert loop.sp == loop.pv == d.F003_LEVEL_SP_PCT and loop.act == -1.0
