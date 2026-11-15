"""Behaviour of 322C001's packed beds — `ureasim.units.absorption.packed_beds`.

Equivalence with V1 is proven in `tests/equivalence/test_packed_beds_equivalence.py`. This file
pins what the beds DO: the calibration lands the PFD's 204 -> 797 split, and the uptake answers a
heavier gas, a hotter liquor and a lost polish the way a rate-based bed must.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_322c001 as c
from ureasim.units.absorption import lp_absorber as la
from ureasim.units.absorption import packed_beds as pb

MW = pb.MW_COMP


def _solve(scale=1.0, t_liq=43.0, m_cpl=c.C001_CPL_DES_KGH, passes=200):
    pin = la.design_pin()
    comp = {k: v * scale for k, v in pin.gas_kmolh.items()}
    return comp, pb.solve(comp, t_liq, c.C001_T_CPL_C, c.C001_P_BARA, c.C001_M755_DES_KGH,
                          c.W_S755, m_cpl, c.W_C001_DES, pin.cal, passes=passes)


def test_the_calibration_lands_the_pfds_split():
    """Relaxed, the design gas gives up NH3 89.33 and CO2 62.00 kg/h and picks up 21.34 of water,
    the PFD's 204 -> 797 split; the vent leaves 1.79 kg/h of NH3 and is 2.28 mol % water, PFD
    797's. The factors: 0.80 and 0.84 on Onda's k_G, 0.88 the vent's water activity."""
    pin = la.design_pin()
    _, r = _solve()
    absorbed = {k: v * MW[k] for k, v in r.absorbed_kmolh.items()}
    assert absorbed["NH3"] == pytest.approx(c.C001_ABS_NH3_DES_KGH, abs=1e-8)
    assert absorbed["CO2"] == pytest.approx(c.C001_ABS_CO2_DES_KGH, abs=1e-8)
    assert absorbed["H2O"] == pytest.approx(c.C001_ABS_H2O_DES_KGH, abs=1e-8)
    assert r.vent_kmolh["NH3"] * MW["NH3"] == pytest.approx(1.794, abs=1e-3)
    assert r.vent_kmolh["H2O"] / sum(r.vent_kmolh.values()) == pytest.approx(0.02281, abs=1e-5)
    assert (pin.cal.nh3, pin.cal.co2, pin.cal.a_w) == pytest.approx((0.800, 0.838, 0.881),
                                                                    abs=1e-3)


def test_twice_the_gas_slips_four_times_the_ammonia():
    """The same packing for twice the gas: fewer transfer units each, so 96.0 % of the ammonia is
    taken up instead of 98.0 %, and the slip to atmosphere goes from 1.79 to 7.39 kg/h."""
    comp, one = _solve()
    comp2, two = _solve(scale=2.0)
    assert one.absorbed_kmolh["NH3"] / comp["NH3"] == pytest.approx(0.9803, abs=1e-4)
    assert two.absorbed_kmolh["NH3"] / comp2["NH3"] == pytest.approx(0.9595, abs=1e-4)
    assert two.vent_kmolh["NH3"] * MW["NH3"] == pytest.approx(7.388, abs=1e-3)


def test_a_hot_liquor_holds_back_more():
    """The sump at 70 C: its back-pressure stands at 3.4 mol % NH3, and 5.73 kg/h slips."""
    _, r = _solve(t_liq=70.0)
    assert r.y_star_lo["NH3"] == pytest.approx(0.0339, abs=1e-4)
    assert r.vent_kmolh["NH3"] * MW["NH3"] == pytest.approx(5.726, abs=1e-3)


def test_without_954_the_upper_bed_does_nothing():
    """954 lost: the upper bed has no wash, no transfer units and no rise; 13.3 kg/h of NH3
    slips."""
    _, r = _solve(m_cpl=0.0)
    assert (r.ntu["up_NH3"], r.dt_up_k) == (0.0, 0.0)
    assert r.vent_kmolh["NH3"] * MW["NH3"] == pytest.approx(13.277, abs=1e-3)


def test_no_gas_leaves_the_upper_bed_clean():
    """HV-322604 shut: nothing is taken up, and the uptake the unit lags toward is zero."""
    _, r = _solve(scale=0.0, passes=1)
    assert r.abs_up == {"NH3": 0.0, "CO2": 0.0, "dT": 0.0}
    assert set(r.absorbed_kmolh.values()) == {0.0}


def test_the_954_trickles_through_the_upper_bed_in_23_s():
    """The upper bed's film holdup over the design 954 at 46 C: 23.4 s, the beds' coupling lag;
    no wash, the hour's ceiling."""
    assert pb.liquid_residence_s(pb.BED_UP, c.C001_CPL_DES_KGH, 319.15) == pytest.approx(
        23.443, abs=1e-3)
    assert pb.liquid_residence_s(pb.BED_UP, 0.0, 319.15) == pb.RESIDENCE_MAX_S


def test_the_washes_wet_part_of_the_packing():
    """Onda: the 954 wets 44 % of the upper bed's packing, the 755 71 % of the lower's."""
    assert pb.wetted_fraction(c.C001_CPL_DES_KGH / 3600.0 / pb.BED_UP.area_m2, 319.15) == (
        pytest.approx(0.4412, abs=1e-4))
    assert pb.wetted_fraction(c.C001_M755_DES_KGH / 3600.0 / pb.BED_LO.area_m2, 316.15) == (
        pytest.approx(0.7145, abs=1e-4))
    assert pb.wetted_fraction(0.0, 316.15) == 0.0
