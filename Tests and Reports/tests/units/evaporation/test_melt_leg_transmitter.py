"""LY-324501 on AC4's formula, LT-324501's LRV floor applied to the level (decision 252).

The stage's response, both ways against V1's level, is
`tests/equivalence/test_second_evaporator_decided_equivalence`.
"""

from __future__ import annotations

import pytest

from ureasim.core.units_of_measure import ATM_BARA
from ureasim.data import unit_324 as d
from ureasim.data.low_level_stops import L2_PCT
from ureasim.units.evaporation.melt_leg_transmitter import ly_324501, ly_floor_pct


def test_the_floor_on_rosemounts_lrv():
    """As-Built §CXLV.2: 20.6 % at the design 0.131 bar a, 24.1 % at 0.10 and 12.8 % at 0.20;
    19.2 % on the loop summary's -0.87 bar g; the stand-in L2 of 5 % only above 0.269 bar a."""
    assert ly_floor_pct(0.131) == pytest.approx(20.593, abs=1e-3)
    assert ly_floor_pct(0.10) == pytest.approx(24.096, abs=1e-3)
    assert ly_floor_pct(0.20) == pytest.approx(12.797, abs=1e-3)
    assert ly_floor_pct(ATM_BARA - 0.87) == pytest.approx(19.209, abs=1e-3)
    p_l2 = ATM_BARA + (d.LT_324501_LRV_MBAR - L2_PCT["LY-324501"] / 100.0 * d.LY_324501_SPAN_MBAR) / 1000.0
    assert p_l2 == pytest.approx(0.269, abs=1e-3)
    assert ly_floor_pct(p_l2) == pytest.approx(L2_PCT["LY-324501"], abs=1e-12)


def test_the_formula_round_trip_is_exact_above_the_floor():
    """Above the floor LY-324501 is the level object itself, so the design point is kept to the bit;
    the written formula, LT-324501 built and AC4's subtraction undone, agrees to 1e-13 %."""
    p = 0.131
    for level in (d.F003_LEVEL_SP_PCT, 21.0, 60.123456789, 100.0):
        assert ly_324501(level, p) is level or ly_324501(level, p) == level
        lt = d.LY_324501_SPAN_MBAR * level / 100.0 + 1000.0 * (p - ATM_BARA)
        ly = (max(lt, d.LT_324501_LRV_MBAR) - 1000.0 * (p - ATM_BARA)) / d.LY_324501_SPAN_MBAR * 100.0
        assert ly == pytest.approx(ly_324501(level, p), abs=1e-13)


def test_below_the_floor_it_reads_the_floor_and_v1_reads_the_level():
    """An empty leg at the design vacuum: AC4 reads the floor, V1 (``ac4=False``) the level; both
    clamp V1's 0 to 100 %, and at the atmosphere the floor is below zero and never acts."""
    p = 0.131
    assert ly_324501(3.0, p) == ly_floor_pct(p)
    assert ly_324501(-4.0, p) == ly_floor_pct(p)
    assert ly_324501(3.0, p, ac4=False) == 3.0
    assert ly_324501(-4.0, p, ac4=False) == 0.0
    assert ly_324501(130.0, p) == 100.0 == ly_324501(130.0, p, ac4=False)
    assert ly_floor_pct(ATM_BARA) < 0.0
    assert ly_324501(0.0, ATM_BARA) == 0.0
