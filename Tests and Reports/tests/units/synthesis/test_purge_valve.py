"""Behaviour of HV-322604, the inert-purge letdown.

`tests/equivalence/test_purge_valve_equivalence.py` proves this module is V1's to the bit.
This file pins what the valve DOES — the process behaviour a trainee sees — a finding, handoff
B-18, so it is not re-opened from memory, and B-19's decided outlet below the dew point. Every
number asserted here was measured on the module before it was written down.
"""

from __future__ import annotations

import math

import pytest

from ureasim.control.valve import cv_fraction
from ureasim.core.stream import MW_COMP
from ureasim.data.unit_322e003 import (
    CCW_KGH_DES,
    CCW_T_IN_DES_C,
    HIC604_DES_PCT,
    HV604_MW_DES,
    HV604_P_OUT_BARA,
    OFFGAS_DES_KGH,
    OFFGAS_DES_KMOLH,
    OFFGAS_P_BARA,
    OFFGAS_T_DES_C,
)
from ureasim.data.unit_322r001 import OFFGAS_DES_KMOLH as REACTOR_OFFGAS_DES_KMOLH
from ureasim.units.synthesis.purge_valve import (
    DESIGN,
    purge_capacity_fraction,
    purge_mw,
    purge_valve_322604,
    seat_ceiling_kgh,
    valve_factor,
)
from ureasim.thermo import real_gas
from ureasim.units.synthesis.scrubber import scrubber_322e003


def _factor(hic=HIC604_DES_PCT, p=OFFGAS_P_BARA, t=OFFGAS_T_DES_C, mw=HV604_MW_DES):
    return valve_factor(hic, p, t, mw)


def _scrubber(cool_frac):
    return scrubber_322e003(REACTOR_OFFGAS_DES_KMOLH, 1.0, CCW_T_IN_DES_C, CCW_KGH_DES,
                            cool_frac=cool_frac)


def _kgh(comp):
    return sum(comp[k] * MW_COMP[k] for k in MW_COMP)


# ======================================================================================
# 1. The design point
# ======================================================================================

def test_the_design_call_is_pfd_204_as_it_enters_322c001():
    assert DESIGN.comp_kmolh == OFFGAS_DES_KMOLH
    assert DESIGN.mass_kgh == OFFGAS_DES_KGH
    assert DESIGN.valve_frac == 1.0 and DESIGN.pass_frac == 1.0
    assert DESIGN.t_out_c == 94.8                     # report D-4: SRK, not 0.55 C/bar
    assert DESIGN.dp_bar == OFFGAS_P_BARA - HV604_P_OUT_BARA
    assert DESIGN.carbamate_deposition is False


def test_the_published_capacity_is_one_at_design_and_zero_shut():
    assert purge_capacity_fraction(HIC604_DES_PCT, OFFGAS_P_BARA) == 1.0
    assert purge_capacity_fraction(0.0, OFFGAS_P_BARA) == 0.0


# ======================================================================================
# 2. The seat: choked, equal percentage, and the vendor's trim
# ======================================================================================

def test_a_shut_valve_isolates_the_loop():
    """Report D-2: V1's earlier form still passed 14 % of the design purge at 0 %."""
    shut = purge_valve_322604(OFFGAS_DES_KMOLH, OFFGAS_T_DES_C, 0.0, OFFGAS_P_BARA)
    assert shut.valve_frac == 0.0
    assert shut.mass_kgh == 0.0
    assert all(v == 0.0 for v in shut.comp_kmolh.values())
    assert shut.t_out_c == OFFGAS_T_DES_C             # nothing flows, nothing cools


def test_the_first_increment_of_travel_passes_the_trims_minimum_kv():
    """Kv0/Kvs = 2 % is the vendor's stated rangeability, so the characteristic steps.

    Against the 72 % design anchor (handoff B-18, decided 2026-10-10) that step is 50^-0.72 =
    6.0 % of the design purge, where V1's 50 % made it 14.1 %: the valve cannot throttle the purge
    below it except by shutting.
    """
    assert _factor(hic=0.001) == pytest.approx(
        50.0 ** ((0.001 - HIC604_DES_PCT) / 100.0), rel=1e-12)
    assert 0.0598 < _factor(hic=0.001) < 0.0599


@pytest.mark.parametrize("p", [14.0, 20.0, 42.0, 100.0, 128.0, 151.0])
def test_choked_flow_follows_the_upstream_pressure_alone(p):
    """Choked down to about 13.2 bar a upstream (x = F_gamma.xT = 0.696 against 4 bar a)."""
    assert _factor(p=p) / _factor() == pytest.approx(p / OFFGAS_P_BARA, rel=1e-12)


def test_below_the_choke_the_flow_falls_away():
    assert _factor(p=12.0) / (12.0 / OFFGAS_P_BARA) < 0.9995
    assert _factor(p=8.0) / (8.0 / OFFGAS_P_BARA) == pytest.approx(0.9668, abs=1e-4)
    assert _factor(p=HV604_P_OUT_BARA) == 0.0
    assert _factor(p=2.0) == 0.0                      # reversed: the seat passes nothing


def test_each_percent_of_travel_multiplies_the_flow_by_the_same_ratio():
    assert _factor(hic=HIC604_DES_PCT + 1.0) / _factor() == pytest.approx(50.0 ** 0.01, rel=1e-12)
    assert _factor(hic=76.0) / _factor(hic=75.0) == pytest.approx(50.0 ** 0.01, rel=1e-12)


@pytest.mark.parametrize("stroke, kv", [(0.05, 0.05107), (0.25, 0.1117), (0.50, 0.297),
                                        (0.75, 0.7899), (1.00, 2.1)])
def test_the_trim_is_the_vendors(stroke, kv):
    """The Uhde CONVAL sizing, UD-MR-G00-DZ-0042-010 page 3, "Characteristics values table":
    Kv against stroke for Kvs 2.1. The ported law reproduces it to its printed figures."""
    assert 2.1 * cv_fraction(stroke) == pytest.approx(kv, rel=5e-4)


def test_a_heavier_or_colder_purge_passes_more_kilograms():
    """Choked mass flow goes as p1 . sqrt(M / T): the composition does not cancel out."""
    assert _factor(mw=2.0 * HV604_MW_DES) == pytest.approx(math.sqrt(2.0), rel=1e-12)
    t_hot = OFFGAS_T_DES_C + 50.0
    assert _factor(t=t_hot) == pytest.approx(
        math.sqrt((OFFGAS_T_DES_C + 273.15) / (t_hot + 273.15)), rel=1e-12)


def test_the_seat_does_not_fractionate():
    rich = {k: v + {"NH3": 200.0, "CO2": 50.0}.get(k, 0.0) for k, v in OFFGAS_DES_KMOLH.items()}
    out = purge_valve_322604(rich, 130.3, 78.188, 139.603)
    n_in, n_out = sum(rich.values()), sum(out.comp_kmolh.values())
    for k in MW_COMP:
        assert out.comp_kmolh[k] / n_out == pytest.approx(rich[k] / n_in, rel=1e-12, abs=0.0)


def test_an_empty_offer_is_handled():
    empty = purge_valve_322604({k: 0.0 for k in MW_COMP}, 114.0, 50.0, 140.7, 100.0)
    assert empty.mass_kgh == 0.0
    assert empty.pass_frac == 1.0                     # no division by an empty offer
    assert empty.t_out_c == 114.0
    assert purge_mw({}) == HV604_MW_DES


# ======================================================================================
# 3. The ceiling: a cooling loss is retained, not vented
# ======================================================================================

def test_a_cooling_loss_is_retained_in_the_loop_not_vented():
    """At zero condensation capacity 322E003 offers 13 times the design purge.

    Without the ceiling the valve would vent almost all of it, a boundary mass balance
    would close, and the excursion would vanish. With it, the seat passes the purge the
    shell would have produced with full cooling, and over 20 t/h stays in the loop.
    """
    r = _scrubber(0.0)
    offered = _kgh(r.offgas_kmolh)
    cap = seat_ceiling_kgh(r.offgas_kmolh, r.uncond_kgh)
    capped = purge_valve_322604(r.offgas_kmolh, r.t_offgas_c, HIC604_DES_PCT, 140.7, cap)
    uncapped = purge_valve_322604(r.offgas_kmolh, r.t_offgas_c, HIC604_DES_PCT, 140.7, None)

    assert offered == pytest.approx(22354.6, abs=0.1)
    assert cap == pytest.approx(OFFGAS_DES_KGH, rel=1e-12)
    assert capped.mass_kgh == pytest.approx(1602.2, abs=0.1)
    assert uncapped.mass_kgh == pytest.approx(20966.6, abs=0.1)
    assert offered - capped.mass_kgh > 20000.0
    #  What does pass is the loop's gas, not the inert purge: nine times the design ammonia.
    assert capped.comp_kmolh["NH3"] == pytest.approx(47.72, abs=0.01)
    assert DESIGN.comp_kmolh["NH3"] == pytest.approx(5.351, abs=0.001)


def test_the_ceiling_never_adds_flow():
    r = _scrubber(1.0)
    offered = _kgh(r.offgas_kmolh)
    wide = purge_valve_322604(r.offgas_kmolh, r.t_offgas_c, HIC604_DES_PCT, 140.7, 2.0 * offered)
    assert wide.pass_frac == 1.0
    assert wide == purge_valve_322604(r.offgas_kmolh, r.t_offgas_c, HIC604_DES_PCT, 140.7, None)


def test_at_design_the_ceiling_is_exactly_the_offer():
    r = _scrubber(1.0)
    assert seat_ceiling_kgh(r.offgas_kmolh, r.uncond_kgh) == OFFGAS_DES_KGH


# ======================================================================================
# 4. The outlet temperature
# ======================================================================================

def test_a_higher_loop_pressure_cools_the_purge_more():
    t = {p: purge_valve_322604(OFFGAS_DES_KMOLH, OFFGAS_T_DES_C, HIC604_DES_PCT, p).t_out_c
         for p in (128.0, 140.7, 151.0)}
    assert t == {128.0: 96.2, 140.7: 94.8, 151.0: 93.7}


def test_a_cold_purge_condenses_and_raises_the_deposition_flag():
    """The design purge from a 30 C vent: dry, the letdown would reach -6.4 C, 31 K below the
    gas's dew point. It condenses 1.66 kmol/h of carbamate liquor instead and settles at 34.8 C
    (handoff B-19); the liquor in the line is the deposit L3-7 warns of."""
    cold = purge_valve_322604(OFFGAS_DES_KMOLH, 30.0, HIC604_DES_PCT, 140.7)
    assert cold.t_out_c == 34.8
    assert cold.condensing is True and cold.carbamate_deposition is True
    assert sum(cold.liquor_kmolh.values()) == pytest.approx(1.6642, abs=1e-4)
    assert cold.mass_kgh > 0.0                        # a fouling warning, not a restriction


def test_the_purge_condenses_a_carbamate_liquor_in_a_cooling_loss():
    """Handoff B-19, decided 2026-10-01: the floor replaced by the isenthalpic flash.

    As 322E003 loses its cooling the purge turns ammonia-rich and its dew point climbs to about
    80 C at 4 bar a. V1's single-phase solve fell below it — 26 C at 90 % cooling — and from
    70 % returned its bracket's floor, T_in - 150 K = -36 C. The port condenses an ammonium-
    carbamate liquor whose heat holds the outlet a few kelvin under the dew point: 66.8 to
    77.9 C, the liquor from 24 kg/h to 4.3 t/h. Above the dew point, the design included, the
    outlet is V1's.
    """
    measured = {1.0: (94.8, 0.0), 0.95: (66.8, 24.1), 0.9: (71.7, 120.4), 0.8: (75.3, 375.0),
                0.7: (76.5, 696.2), 0.5: (77.4, 1529.7), 0.0: (77.9, 4342.3)}
    v1 = {1.0: 94.8, 0.95: 53.3, 0.9: 26.0, 0.8: -11.1, 0.7: -36.0, 0.5: -36.0, 0.0: -36.0}
    for cf, (t_out, liq_kgh) in measured.items():
        r = _scrubber(cf)
        out = purge_valve_322604(r.offgas_kmolh, r.t_offgas_c, HIC604_DES_PCT, 140.7)
        assert out.t_out_c == t_out, cf
        assert _kgh(out.liquor_kmolh) == pytest.approx(liq_kgh, abs=0.1), cf
        assert out.condensing is (liq_kgh > 0.0), cf
        single = real_gas.isenthalpic_letdown(out.comp_kmolh, r.t_offgas_c, 140.7, 4.0)
        assert round(single["t_out_c"], 1) == v1[cf], cf
    assert _scrubber(0.0).t_offgas_c - 150.0 == -36.0


def test_the_outlet_follows_the_absorbers_pressure():
    """Handoff A-17: the seat discharges against 322C001's live pressure. Choked, it passes the
    same purge; the gas leaves the seat 0.4 K warmer at SV32253's 6.013 bar a than at 4.0, and
    0.3 K colder at 2.5."""
    at = {p: purge_valve_322604(OFFGAS_DES_KMOLH, OFFGAS_T_DES_C, HIC604_DES_PCT,
                                OFFGAS_P_BARA, p_out_bara=p) for p in (2.5, 4.0, 6.013)}
    assert at[4.0] == DESIGN
    assert at[2.5].mass_kgh == at[6.013].mass_kgh == DESIGN.mass_kgh
    assert (at[2.5].t_out_c, at[6.013].t_out_c) == (94.5, 95.2)


# ======================================================================================
# 5. The anchor opening — handoff B-18
# ======================================================================================

def test_the_plants_own_opening_passes_a_quarter_more_than_the_design_purge():
    """Handoff B-18, decided 2026-10-10: the characteristic anchored at the 72 % the vendor's trim
    passes the design purge at. The plant holds HIC-322604 at 78.188 % at 100.4 % load, a factor of
    50^0.06188 on the equal-percentage trim, 1.27; V1's 50 % anchor makes it 3.01
    (`test_purge_valve_equivalence`)."""
    assert _factor(hic=78.188) == pytest.approx(50.0 ** 0.06188, rel=1e-12)
    assert _factor(hic=78.188) == pytest.approx(1.2739, abs=1e-4)
    assert purge_capacity_fraction(78.188, 139.603) == pytest.approx(1.2640, abs=1e-4)
