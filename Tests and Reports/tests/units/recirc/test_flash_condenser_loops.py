"""323E011 / 323D011's three controllers — `ureasim.units.recirc.flash_condenser_loops`.

Pinned: each loop is seeded ``pv == sp == pv1 == pv2`` at its design point, LIC-323503 on LT-323503's
tap reading of the design holdup (decision 233) and on V1's 50 % with ``taps=False``; and
`flash_condenser` re-exports the three factories it held before the split (session 123).
"""

from __future__ import annotations

from ureasim.data import unit_323e011 as e
from ureasim.units.recirc import flash_condenser as fc
from ureasim.units.recirc import flash_condenser_loops as loops


def test_each_loop_is_seeded_on_its_design_point():
    pic, fic = loops.pic_323203(), loops.fic_323418().loop
    v = e.M718B_DES_KGH / e.RHO_718_KGM3
    assert (pic.sp, pic.pv, pic.pv1, pic.pv2) == (e.E011_P_BARA,) * 4
    assert (fic.sp, fic.pv, fic.pv1, fic.pv2) == (v,) * 4
    for taps, r in ((True, e.LT_323503_DES_PCT), (False, e.D011_LVL_SP_PCT)):
        lic = loops.lic_323503(taps=taps)
        assert (lic.sp, lic.pv, lic.pv1, lic.pv2, lic.op) == (r, r, r, r, e.LV503_OP_DES_PCT)
    assert loops.lic_323503().sp == e.LT_323503_DES_PCT


def test_flash_condenser_re_exports_the_factories():
    assert (fc.pic_323203, fc.lic_323503, fc.fic_323418) == (
        loops.pic_323203, loops.lic_323503, loops.fic_323418)
