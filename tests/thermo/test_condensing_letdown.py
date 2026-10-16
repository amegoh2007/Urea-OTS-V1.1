"""Behaviour of the condensing letdown — `ureasim.thermo.condensing_letdown`.

The relation is the rewrite's, decided by the process engineer on 2026-10-01 (handoff B-19): V1's
single-phase solve is kept for a gas that stays dry, and the decided divergence below its dew
point is asserted against V1 in `tests/equivalence/test_purge_valve_equivalence.py`. This file
pins the flash itself: the design purge stays dry and V1's; a cooling-loss purge settles where
its gas, its liquor and its enthalpy all balance; the answer depends on the composition alone.
"""

from __future__ import annotations

import pytest

from ureasim.data.unit_322e003 import CCW_KGH_DES, CCW_T_IN_DES_C, OFFGAS_DES_KMOLH
from ureasim.data.unit_322r001 import OFFGAS_DES_KMOLH as REACTOR_OFFGAS_DES_KMOLH
from ureasim.thermo import condensing_letdown as cl
from ureasim.thermo import iapws, real_gas
from ureasim.thermo.ammonia_backpressure import liquid_state
from ureasim.thermo.domains import MW
from ureasim.units.synthesis.scrubber import scrubber_322e003


def _cooling_loss(cool_frac):
    r = scrubber_322e003(REACTOR_OFFGAS_DES_KMOLH, 1.0, CCW_T_IN_DES_C, CCW_KGH_DES,
                         cool_frac=cool_frac)
    return {k: v for k, v in r.offgas_kmolh.items() if v > 0.0}, r.t_offgas_c


def test_the_design_purge_stays_dry_and_is_v1s():
    """PFD 204 let down to 4 bar a: dry all the way, its outlet V1's single-phase SRK answer."""
    r = cl.letdown(OFFGAS_DES_KMOLH, 114.0, 140.7, 4.0)
    assert not r.condensing and set(r.liquor_kmolh.values()) == {0.0}
    assert r.t_out_c == r.t_single_phase_c == real_gas.isenthalpic_letdown(
        OFFGAS_DES_KMOLH, 114.0, 140.7, 4.0)["t_out_c"]
    assert round(r.t_out_c, 1) == 94.8


def test_a_cooling_loss_purge_balances_its_gas_its_liquor_and_its_enthalpy():
    """322E003 at 70 % cooling: V1's answer is its bracket's floor, -36 C. The flash settles at
    76.45 C with a liquor of 162 mol NH3 and 66 mol CO2 per kg of water, every pressure the gas
    carries equal to what the liquor holds back, and the enthalpy the inlet's to 1e-13."""
    comp, t_in = _cooling_loss(0.7)
    r = cl.letdown(comp, t_in, 140.7, 4.0)
    assert r.t_single_phase_c == -36.0 and r.condensing and r.converged
    assert r.t_out_c == pytest.approx(76.454, abs=1e-3)
    liq = r.liquor_kmolh
    m_w = liq["H2O"] * 0.0180152
    assert (liq["NH3"] / m_w, liq["CO2"] / m_w) == (pytest.approx(162.38, abs=0.01),
                                                    pytest.approx(66.31, abs=0.01))
    w = {k: liq[k] * MW[k] for k in liq}
    w = {k: v / sum(w.values()) for k, v in w.items()}
    p_n, p_c, a_w = liquid_state(w, r.t_out_c)
    v = sum(r.vapour_kmolh.values())
    held = {"NH3": p_n, "CO2": p_c, "H2O": a_w * iapws.psat_bara(r.t_out_c) * 1.0e5}
    for k, p in held.items():
        assert r.vapour_kmolh[k] / v * 4.0e5 == pytest.approx(p, rel=1e-10), k
    n = sum(comp.values())
    h_in = real_gas.h_molar({k: x / n for k, x in comp.items()}, t_in + 273.15, 140.7e5) * n
    assert cl.two_phase_enthalpy(comp, liq, r.t_out_c, 4.0) == pytest.approx(h_in, rel=1e-12)


def test_the_outlet_depends_on_the_composition_alone():
    """Twice the purge: the same outlet to the bit and twice the liquor; a repeat call is served
    from the cache."""
    comp, t_in = _cooling_loss(0.7)
    one = cl.letdown(comp, t_in, 140.7, 4.0)
    two = cl.letdown({k: 2.0 * v for k, v in comp.items()}, t_in, 140.7, 4.0)
    assert two.t_out_c == one.t_out_c
    assert two.liquor_kmolh["NH3"] == pytest.approx(2.0 * one.liquor_kmolh["NH3"], rel=1e-15)
    assert cl.letdown(comp, t_in, 140.7, 4.0) is one


def test_a_gas_with_no_carbon_dioxide_builds_no_carbamate_liquor():
    """Without both NH3 and CO2 there is no carbamate liquor to condense: the answer is the
    single-phase one, cold as it is."""
    dry = {k: v for k, v in OFFGAS_DES_KMOLH.items() if v > 0.0 and k != "CO2"}
    r = cl.letdown(dry, 30.0, 140.7, 4.0)
    assert not r.condensing and r.t_out_c == r.t_single_phase_c < 0.0


def test_the_liquid_state_grid_carries_v1s_pressures_and_the_water():
    """On its own grid the liquid state reads the back-pressure's two pressures to the bit; PFD 755
    holds its water at a_w 0.95, a 150 / 60 molal carbamate liquor at 60 C at 0.22."""
    from ureasim.thermo.ammonia_backpressure import back_pressure
    w755 = {"NH3": 0.0417, "CO2": 0.0381, "H2O": 0.9113}
    assert liquid_state(w755, 40.0)[:2] == back_pressure(w755, 40.0)[:2]
    assert liquid_state(w755, 40.0)[2] == pytest.approx(0.9516, abs=1e-4)
    wc = {"NH3": 150 * 0.0170304, "CO2": 60 * 0.0440098, "H2O": 1.0}
    wc = {k: v / sum(wc.values()) for k, v in wc.items()}
    assert liquid_state(wc, 60.0)[2] == pytest.approx(0.2153, abs=1e-4)


#: 322E003's vent three seconds after 321P002B stops, measured on the assembled plant (session 40):
#: CO2-rich and almost dry, let down from the loop to 322C001.
LOST_MOTIVE_VENT = {"CO2": 0.3836, "H2O": 0.00164, "N2": 0.48103, "NH3": 0.05207, "O2": 0.08167}


def test_a_dry_co2_rich_purge_condenses_no_liquor_and_lays_solid_carbamate():
    """The lost-motive vent's incipient liquor leaves the model's range before it holds its water
    back below what the gas carries; no isothermal flash converges (handoff A-18) — and it costs a
    few thousand liquid-state evaluations, not the 50 000 to 100 000 the unbounded solve spent. Its
    dry outlet, 29.60 C, stands far above solid carbamate's saturation (p_NH3^2 p_CO2 0.057 bar^3
    against Kp 6.5e-4), so it lays the solid down (handoff B-79 (b), decided 2026-10-14): 4.45 mmol
    per mole of gas, the outlet held at 51.01 C, the gas left exactly on Kp."""
    calls = {"n": 0}
    held = cl._held_back_pa

    def counted(*a):
        calls["n"] += 1
        return held(*a)

    cl._held_back_pa = counted
    try:
        r = cl.letdown(LOST_MOTIVE_VENT, 81.07, 140.67, 3.7945)
    finally:
        cl._held_back_pa = held
    assert not r.condensing and r.converged
    assert r.t_single_phase_c == pytest.approx(29.60, abs=0.01)
    assert r.t_out_c == pytest.approx(51.007, abs=1e-3)
    assert r.solid_kmolh == pytest.approx(0.0044494, abs=1e-7)
    assert set(r.liquor_kmolh.values()) == {0.0}
    v = r.vapour_kmolh
    n = sum(v.values())
    assert (v["NH3"] / n * 3.7945) ** 2 * (v["CO2"] / n * 3.7945) == pytest.approx(
        cl.carbamate_kp_bar3(r.t_out_c), rel=1e-9)
    assert calls["n"] < 8000


def test_egan_potts_puts_one_atmosphere_at_58_7_c():
    """Egan, Potts and Potts (1946), admitted 2026-10-14: the solid's dissociation pressure is
    1 atm at 58.7 C and 89 Torr at 25 C, Kp = (4/27) P^3."""
    p = lambda t: (cl.carbamate_kp_bar3(t) * 27.0 / 4.0) ** (1.0 / 3.0)
    assert p(58.7) == pytest.approx(1.01325, abs=0.004)
    assert p(25.0) * 750.06 == pytest.approx(89.0, abs=0.5)


def test_the_solid_closes_the_letdowns_enthalpy_and_mass():
    """The deposit's heat holds the outlet up exactly as much as the balance asks: the inlet's
    SRK enthalpy equals the gas left plus the solid on Voskov and Voronin's enthalpy, and the NH3
    and CO2 the gas lost are the solid's two and one."""
    from ureasim.thermo import enthalpy as h0
    from ureasim.thermo import real_gas
    r = cl.letdown(LOST_MOTIVE_VENT, 81.07, 140.67, 3.7945)
    n = sum(LOST_MOTIVE_VENT.values())
    h_in = real_gas.h_molar({k: v / n for k, v in LOST_MOTIVE_VENT.items()}, 81.07 + 273.15,
                            140.67e5) * n
    v = r.vapour_kmolh
    n_v = sum(v.values())
    t_k = r.t_out_c + 273.15
    h_out = (real_gas.h_molar({k: x / n_v for k, x in v.items()}, t_k, 3.7945e5) * n_v
             + r.solid_kmolh * h0.h_species("Carbamate", "solid", t_k))
    assert h_out == pytest.approx(h_in, abs=0.05)
    assert LOST_MOTIVE_VENT["NH3"] - v["NH3"] == pytest.approx(2.0 * r.solid_kmolh, rel=1e-12)
    assert LOST_MOTIVE_VENT["CO2"] - v["CO2"] == pytest.approx(r.solid_kmolh, rel=1e-12)


#: The lost-motive vent 30 s after 321P002B stops on session 51's plant: 78 % CO2, 1.8 % NH3.
VENT_30S = {"CO2": 0.7822, "H2O": 0.0006, "N2": 0.1698, "NH3": 0.0184, "O2": 0.0289}


def test_the_solid_lifts_the_purge_off_its_dry_answer_decided_divergence(monkeypatch):
    """B-79 (b) both ways, on the vent 30 s into a lost motive (86.4 C, 140.13 to 2.66 bar a):
    without the solid the outlet is the dry SRK answer, -8.69 C, flagged by nothing but its
    temperature; with it the line lays 7.41 mmol of carbamate per mole of gas and the outlet
    stands at 24.03 C. The design purge deposits nothing either way."""
    cl._CACHE.clear()
    on = cl.letdown(VENT_30S, 86.4, 140.13, 2.66)
    monkeypatch.setattr(cl, "solid_deposit", lambda *a, **k: None)
    cl._CACHE.clear()
    off = cl.letdown(VENT_30S, 86.4, 140.13, 2.66)
    cl._CACHE.clear()
    assert off.t_out_c == off.t_single_phase_c == on.t_single_phase_c == pytest.approx(-8.69,
                                                                                    abs=0.01)
    assert off.solid_kmolh == 0.0
    assert on.t_out_c == pytest.approx(24.03, abs=0.01)
    assert on.solid_kmolh == pytest.approx(7.4116e-3, rel=1e-4)

