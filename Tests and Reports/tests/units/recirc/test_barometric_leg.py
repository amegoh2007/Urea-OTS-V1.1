"""323F010's barometric leg — `ureasim.units.recirc.barometric_leg`.

V1's leg (report A-17) is proven against V1's executed ``gravity_outflow_323f010`` in
`tests/equivalence/test_pre_evaporator_equivalence.py`, which also asserts the decided drain beside
it (handoff B-119, option (b), decided 2026-10-30). This file pins the premise the decision rests
on, read from the leg's isometric and the tank's general assembly, and the drain's law; the stage's
response to it is in `tests/units/recirc/test_pre_evaporator.py`, section 6.
"""

from __future__ import annotations

import pytest

from ureasim.core.units_of_measure import ATM_BARA, G_ACC, PA_PER_BAR
from ureasim.data import unit_323 as d
from ureasim.data.design_point import R323_D002_RHO, R323_M317_DES
from ureasim.units.recirc import barometric_leg as bl
from ureasim.units.recirc import pre_evaporator as pe


def test_the_leg_is_taller_than_any_column_the_vacuum_holds():
    """The premise, checked in the code before the relation changed for it (decision 158's class).
    The isometric's N2 at EL +15 740 stands 9.645 m above 323D002/N1, which the tank's drawing puts
    5 295 mm above its +800 reference. A full vacuum holds 8.98 m of PFD 317's 1 151 kg/m3 melt, so
    with the tank at its 4.95 m design liquid level the column's top stays 1.013 m below N2: the
    leg never fills to the separator."""
    assert d.F010_N2_EL_M - d.D002_N1_EL_M == pytest.approx(9.645, abs=1e-9)
    assert d.D002_REF_EL_M + 5.295 == pytest.approx(d.D002_N1_EL_M, abs=1e-9)
    assert ATM_BARA * PA_PER_BAR / (R323_D002_RHO * G_ACC) == pytest.approx(8.9768, abs=1e-4)
    assert d.F010_LEG_MARGIN_M == pytest.approx(1.0132, abs=1e-4)


def test_the_drain_on_the_separators_own_head():
    """m_317 = m_317,des . sqrt(M / M_des): the design drain at the design holdup, 10 % more for
    21 % more holdup, nothing from an empty separator, and no pressure to answer."""
    assert bl.own_head_leg_kgh(d.F010_M_DES_KG) == R323_M317_DES
    assert bl.own_head_leg_kgh(1.21 * d.F010_M_DES_KG) == pytest.approx(1.1 * R323_M317_DES,
                                                                        rel=1e-12)
    assert bl.own_head_leg_kgh(0.0) == 0.0 == bl.own_head_leg_kgh(-5.0)


def test_v1s_leg_moved_whole_and_the_stage_re_exports_it():
    """V1's leg left `pre_evaporator` unchanged for the 600-line target; the stage re-exports both
    drains under their names."""
    assert pe.barometric_leg_kgh is bl.barometric_leg_kgh
    assert pe.own_head_leg_kgh is bl.own_head_leg_kgh
    assert pe.barometric_leg_kgh(d.F010_M_DES_KG, d.F010_P_BARA) == R323_M317_DES
