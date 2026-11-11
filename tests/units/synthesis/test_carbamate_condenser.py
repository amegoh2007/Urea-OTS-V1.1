"""What 322E002 DOES — behaviour, with no V1 tree required.

Why this is separate from the equivalence suite
-----------------------------------------------
`tests/equivalence/test_carbamate_condenser_equivalence.py` proves the port is V1. This file
proves the model is a carbamate condenser. The second question does not need the V1 tree, so
these tests keep running on a machine that has only the rewrite.

Seven behaviours are pinned:

  * the design state is the licensor balance exactly — 170.0 C out, and the duty is raised as
    steam with nothing retained;
  * the flash CONVERGES to the measured calibration at the calibration point, to within a few
    ulps, rather than being short-circuited to it;
  * the equilibrium split is violently stiff, which is why the film lag exists at all;
  * the film relaxation is a first-order state on the condenser's own holdup time;
  * the disturbance gate returns the design point BIT-EXACTLY at zero, and the full live
    response at one;
  * the NTU quench has the right asymptotes: no flow gives the shell temperature, infinite
    flow gives the adiabatic reaction temperature;
  * the exotherm is 99 % of the duty, and the shell raises what the product does not carry out.
"""

from __future__ import annotations

import pytest

from ureasim.core.stream import MW_COMP
from ureasim.data import unit_322e002 as d
from ureasim.data.unit_320 import SYN_P_DES_BARA
from ureasim.data.unit_322r001 import REACTOR_FEED_HC_DES, REACTOR_FEED_NC_DES
from ureasim.units.synthesis.carbamate_condenser import (
    DESIGN,
    FEED_DES_KMOLH,
    LIQ_DES_KGH,
    UA_KJHK,
    bubble_p_322e002,
    carbamate_condenser_322e002,
    hpcc_flash_split,
)
from ureasim.units.synthesis.ejector import DESIGN as EJECTOR_DES
from ureasim.units.synthesis.stripper import TOP_DES_KMOLH, TOP_DES_T_C

GAS, T_GAS = TOP_DES_KMOLH, TOP_DES_T_C
LIQ, T_LIQ = EJECTOR_DES.comp_kgh, EJECTOR_DES.t_c


def run(gas=None, t_gas=None, liq=None, t_liq=None, **kwargs):
    """The condenser at design, with named arguments replaced."""
    return carbamate_condenser_322e002(
        GAS if gas is None else gas, T_GAS if t_gas is None else t_gas,
        LIQ if liq is None else liq, T_LIQ if t_liq is None else t_liq, **kwargs)


def scaled(vector: dict, factor: float) -> dict:
    """A composition vector scaled uniformly."""
    return {k: v * factor for k, v in vector.items()}


# ======================================================================================
# 1. The design anchor
# ======================================================================================

def test_the_design_outlet_is_the_licensor_temperature_exactly():
    """170.0 C, and exactly, because the conductance is back-solved to make it so."""
    assert DESIGN.t_prod == d.T_PROD_DES_C


def test_the_design_duty_is_raised_entirely_as_steam():
    """At the design outlet the product carries nothing extra, so duty and q_steam coincide.

    That identity is what makes the shell a stable back-pressure on the LP header: any rise
    in the outlet above the design pin is heat the product takes away instead of boiling, and
    the header feels it immediately.
    """
    assert DESIGN.q_steam_kw == DESIGN.duty_kw
    assert DESIGN.steam_kgh == pytest.approx(DESIGN.duty_kw * 3600.0 / d.LATENT_4BAR,
                                             rel=1e-12)


def test_the_exotherm_is_almost_all_of_the_duty():
    """1395 kmol/h of CO2 absorbed at 160 kJ/mol is 62 MW; the sensible term is 0.6 MW.

    Worth stating because it says where to look when the duty moves: this unit is a reactor
    with a cooling jacket, not a heat exchanger with a reaction in it.
    """
    co2_absorbed = GAS["CO2"] - DESIGN.gas_kmolh["CO2"]
    q_carb = co2_absorbed * 1000.0 * d.DH_CARB_KJMOL / 3600.0
    assert co2_absorbed == pytest.approx(1395.0, abs=1.0)
    assert q_carb / DESIGN.duty_kw > 0.99


def test_the_design_makes_189_tonnes_of_carbamate_an_hour():
    """The liquid to 322R001, which is what the reactor's kinetics are calibrated against."""
    assert LIQ_DES_KGH == pytest.approx(189_258.0, abs=1.0)
    assert DESIGN.gas_kgh == pytest.approx(61_381.0, abs=1.0)


def test_the_unit_conserves_mass():
    """No reaction extent is tracked here, so what arrives leaves, component by component."""
    for k in MW_COMP:
        assert DESIGN.gas_kmolh[k] + DESIGN.liq_kmolh[k] \
            == pytest.approx(DESIGN.feed_kmolh[k], rel=1e-12, abs=1e-12)
    assert DESIGN.gas_mol + DESIGN.liq_mol \
        == pytest.approx(sum(DESIGN.feed_kmolh.values()), rel=1e-12)
    assert DESIGN.gas_kgh + DESIGN.liq_kgh == pytest.approx(DESIGN.m_dot_kgh, rel=1e-12)


def test_the_conductance_is_derived_and_positive():
    """A back-solved number, so the only thing to pin is that the inversion was well posed."""
    assert UA_KJHK > 0.0
    assert DESIGN.t_adb > d.T_PROD_DES_C > d.STEAM_TSAT_C


# ======================================================================================
# 2. The flash, and why it does not simply return the calibration
# ======================================================================================

def test_the_flash_converges_to_the_calibration_at_the_calibration_point():
    """Finding A-15: the identity short-circuit is gone, so the residual is now visible.

    It is a few ulps, which is the answer one wants — but it is MEASURED here rather than
    guaranteed by a branch, so a later change to the K-value model that moved it would show
    up instead of being hidden behind an equality test on the inputs.
    """
    equilibrium = hpcc_flash_split(FEED_DES_KMOLH, d.T_PROD_DES_C, SYN_P_DES_BARA)
    for k in ("CO2", "NH3", "H2O", "N2"):
        assert equilibrium[k] == pytest.approx(d.FRAC_GAS_DES[k], abs=1e-12)
        assert equilibrium[k] != d.FRAC_GAS_DES[k] or k == "N2"   # converged, not returned


def test_only_the_distributing_components_flash():
    """The four that are calibrated at exactly 0 or 1 come back untouched, by construction."""
    equilibrium = hpcc_flash_split(FEED_DES_KMOLH, 200.0, 100.0)
    for k in ("O2", "CH4", "H2"):
        assert equilibrium[k] == 1.0
    for k in ("Urea", "Biuret"):
        assert equilibrium[k] == 0.0


def test_the_equilibrium_split_is_violently_stiff():
    """A 20 C swing takes the CO2 split from almost nothing to everything.

    This is the measurement that justifies the film lag. The distributing K-values are tightly
    clustered, so a common factor moves the whole mixture together — which is not how a
    falling-film condenser behaves, and is why the flash is used as a TARGET rather than as
    the answer.
    """
    cold = hpcc_flash_split(FEED_DES_KMOLH, 155.0, SYN_P_DES_BARA)["CO2"]
    hot = hpcc_flash_split(FEED_DES_KMOLH, 190.0, SYN_P_DES_BARA)["CO2"]
    assert cold < 0.02
    assert hot > 0.99


def test_the_flash_responds_to_pressure_as_well_as_temperature():
    """Which the frozen calibration could not do at all — a loop excursion moved nothing."""
    at_design = hpcc_flash_split(FEED_DES_KMOLH, 170.0, SYN_P_DES_BARA)["CO2"]
    at_low = hpcc_flash_split(FEED_DES_KMOLH, 170.0, 0.5 * SYN_P_DES_BARA)["CO2"]
    at_high = hpcc_flash_split(FEED_DES_KMOLH, 170.0, 2.0 * SYN_P_DES_BARA)["CO2"]
    assert at_low > at_design > at_high


@pytest.mark.parametrize("empty", [{k: 0.0 for k in MW_COMP},
                                   {k: (0.0 if k in ("CO2", "NH3", "H2O", "N2") else 1.0)
                                    for k in MW_COMP}])
def test_a_feed_with_nothing_to_flash_holds_the_calibration(empty):
    """A degenerate-input answer, not a bypass: there is no flash to solve."""
    assert hpcc_flash_split(empty, 170.0, SYN_P_DES_BARA) == d.FRAC_GAS_DES


# ======================================================================================
# 3. The film relaxation
# ======================================================================================

def test_a_zero_step_holds_the_split_exactly():
    """Which is what the boot and the conductance back-calculation both need."""
    held = run(t_prod_prev_c=190.0, dt=0.0)
    assert held.phi_gas == d.FRAC_GAS_DES


@pytest.mark.parametrize("dt,fraction", [(36.0, 0.10), (90.0, 0.25), (180.0, 0.50),
                                         (360.0, 1.00), (1000.0, 1.00)])
def test_the_film_relaxes_linearly_over_its_own_holdup_time(dt, fraction):
    """First order on the 6 min condenser holdup, and saturated at one step of it.

    The same constant sets the level fill time, and deliberately: both are how long liquid
    stays in this vessel.
    """
    result = run(t_prod_prev_c=190.0, dt=dt)
    expected = (d.FRAC_GAS_DES["CO2"]
                + fraction * (result.phi_eq["CO2"] - d.FRAC_GAS_DES["CO2"]))
    assert result.phi_gas["CO2"] == pytest.approx(expected, rel=1e-12)
    assert d.TAU_FILL_MIN * 60.0 == 360.0


def test_the_film_is_a_state_the_caller_carries():
    """Two ticks in sequence move further than one tick of the same length.

    That is what makes the split a dynamic state rather than an algebraic map, and it is the
    audit's missing equation for this tag: the condenser had no composition dynamics at all.
    """
    first = run(t_prod_prev_c=190.0, dt=36.0)
    second = run(t_prod_prev_c=190.0, dt=36.0, phi_prev=first.phi_film)
    assert second.phi_gas["CO2"] > first.phi_gas["CO2"]
    assert second.phi_gas["CO2"] < first.phi_eq["CO2"]


def test_a_partial_film_state_falls_back_to_the_calibration():
    """A caller that supplies only some components gets the measured split for the rest."""
    result = run(phi_prev={"CO2": 0.30}, dt=360.0, t_prod_prev_c=d.T_PROD_DES_C)
    assert result.phi_film["NH3"] == pytest.approx(result.phi_eq["NH3"], rel=1e-12)


# ======================================================================================
# 4. The disturbance gate
# ======================================================================================

def test_a_closed_gate_returns_the_calibration_bit_exactly():
    """Not approximately. This is what stops the fresh seed self-exciting a thermal runaway.

    Both gated couplings are pinned at once: the split is the measured vector to the bit, and
    the outlet is the design pin whatever the shell is doing.
    """
    hot = run(t_shell_c=175.0, gate=0.0, t_prod_prev_c=200.0, dt=60.0)
    assert hot.phi_gas == d.FRAC_GAS_DES
    assert hot.t_prod == d.T_PROD_DES_C


@pytest.mark.parametrize("gate", [0.0, 0.25, 0.5, 0.75, 1.0])
def test_the_gate_interpolates_the_outlet_linearly(gate):
    """So a partial disturbance gives a partial response rather than a switch."""
    live = run(t_shell_c=160.0, gate=1.0).t_prod
    expected = d.T_PROD_DES_C + gate * (live - d.T_PROD_DES_C)
    assert run(t_shell_c=160.0, gate=gate).t_prod == pytest.approx(expected, rel=1e-12)


def test_an_open_gate_lets_the_shell_move_the_outlet():
    """The coupling the gate exists to tame, with the gate out of the way."""
    cool = run(t_shell_c=140.0).t_prod
    design = run(t_shell_c=d.STEAM_TSAT_C).t_prod
    warm = run(t_shell_c=165.0).t_prod
    assert cool < design < warm


# ======================================================================================
# 5. The NTU quench
# ======================================================================================

def test_the_adiabatic_temperature_is_intensive():
    """q_carb and m_dot both scale with throughput, so the exotherm spike barely moves.

    That is what keeps the asymptotes physical. If the spike scaled with flow, a turned-down
    condenser would approach a different temperature than a flooded one for reasons that had
    nothing to do with the shell.
    """
    temperatures = [run(gas=scaled(GAS, f), liq=scaled(LIQ, f)).t_adb
                    for f in (0.25, 0.5, 1.0, 2.0, 4.0)]
    assert max(temperatures) - min(temperatures) < 1e-6


def test_no_flow_quenches_all_the_way_to_the_shell():
    """Infinite NTU. A stalled condenser sits at whatever the boiling water is at."""
    trickle = run(gas=scaled(GAS, 0.02), liq=scaled(LIQ, 0.02))
    assert trickle.t_prod == pytest.approx(d.STEAM_TSAT_C, abs=0.01)


def test_a_flooded_condenser_approaches_the_adiabatic_temperature():
    """Zero NTU. The shell cannot reach the fluid fast enough to take any of it away."""
    flooded = run(gas=scaled(GAS, 100.0), liq=scaled(LIQ, 100.0))
    assert flooded.t_prod > 0.95 * flooded.t_adb
    assert flooded.t_prod < flooded.t_adb


def test_the_outlet_rises_monotonically_with_throughput():
    """Between the two asymptotes, which is the operating range an upset moves through."""
    temperatures = [run(gas=scaled(GAS, f), liq=scaled(LIQ, f)).t_prod
                    for f in (0.1, 0.5, 1.0, 1.5, 2.0, 5.0)]
    assert all(b > a for a, b in zip(temperatures, temperatures[1:]))


def test_a_dead_condenser_reports_the_shell_temperature():
    """The `m_dot > 1e-9` guard, which stops the mixed feed dividing by nothing."""
    dead = run(gas=scaled(GAS, 0.0), liq=scaled(LIQ, 0.0))
    assert dead.t_feed_mix == d.STEAM_TSAT_C
    assert dead.m_dot_kgh == 0.0
    assert dead.duty_kw == 0.0


# ======================================================================================
# 6. What the shell actually raises
# ======================================================================================

def test_a_hotter_product_carries_heat_away_from_the_shell():
    """The LP header's own negative feedback, and the reason the two are stable together."""
    hot = run(t_shell_c=200.0)
    assert hot.t_prod > d.T_PROD_DES_C
    assert hot.q_steam_kw < hot.duty_kw


def test_the_steam_raised_never_goes_negative():
    """Floored at zero, which is the full-quench limit rather than a numerical guard."""
    for t_shell in (240.0, 300.0, 500.0):
        assert run(t_shell_c=t_shell).q_steam_kw >= 0.0


def test_a_cold_feed_still_raises_steam():
    """The exotherm does not care how the reactants arrived, only that they react."""
    cold = run(t_gas=120.0, t_liq=20.0)
    assert cold.duty_kw > 0.0
    assert cold.t_feed_mix < DESIGN.t_feed_mix


def test_the_sensible_term_floors_at_the_design_outlet():
    """A gas feed below the design outlet contributes no sensible duty, only the exotherm."""
    below = run(t_gas=d.T_PROD_DES_C - 20.0)
    at = run(t_gas=d.T_PROD_DES_C)
    assert below.duty_kw == pytest.approx(at.duty_kw, rel=1e-12)


# ======================================================================================
# 7. PI-322E002, the melt bubble pressure
# ======================================================================================

def test_the_bubble_pressure_is_monotone_the_right_way_in_all_three():
    """Hotter and NH3-richer raise it; wetter lowers it."""
    base = bubble_p_322e002(170.0, REACTOR_FEED_NC_DES, REACTOR_FEED_HC_DES)
    assert bubble_p_322e002(180.0, REACTOR_FEED_NC_DES, REACTOR_FEED_HC_DES) > base
    assert bubble_p_322e002(170.0, REACTOR_FEED_NC_DES + 0.5, REACTOR_FEED_HC_DES) > base
    assert bubble_p_322e002(170.0, REACTOR_FEED_NC_DES, REACTOR_FEED_HC_DES + 0.1) < base


def test_the_bubble_pressure_is_the_design_constant_at_its_own_anchor():
    """Exactly 144.2 when the melt sits at the anchor composition and the design temperature."""
    assert bubble_p_322e002(d.T_PROD_DES_C, REACTOR_FEED_NC_DES, REACTOR_FEED_HC_DES) \
        == pytest.approx(d.P_DES_BARA, rel=1e-12)


def test_the_design_indication_carries_a_small_offset_from_the_fallback_anchor():
    """144.35, not 144.2, because the melt is marginally NH3-richer than the reactor feed.

    V1 removes that offset by capturing the SETTLED melt N/C at boot; until it does, the
    reactor-feed value is the fallback and this is what the indication reads. Pinned here so
    the 0.1 % is a recorded decision rather than a surprise on a screen.
    """
    assert DESIGN.p_bub_bara == pytest.approx(144.35, abs=0.01)
    assert DESIGN.melt_nc == pytest.approx(3.0786, abs=0.0005)
    assert DESIGN.melt_nc > REACTOR_FEED_NC_DES


def test_a_co2_starved_feed_cannot_drive_the_indication_to_infinity():
    """The ratio clamps. Without them the melt N/C diverges and PI-322E002 impulses to 330 bar.

    Both ratios are NH3/CO2 and H2O/CO2, so on the way through a CO2 cut they blow up for
    arithmetic reasons rather than physical ones. Clamping to half and twice the design keeps
    the published indication inside a bounded physical range.
    """
    for factor in (1e-2, 1e-4, 1e-8):
        starved = run(gas={k: (v * factor if k == "CO2" else v) for k, v in GAS.items()},
                      liq={k: (v * factor if k == "CO2" else v) for k, v in LIQ.items()})
        assert starved.melt_nc <= d.BUB_RATIO_HI_FRAC * REACTOR_FEED_NC_DES
        assert starved.melt_hc <= d.BUB_RATIO_HI_FRAC * REACTOR_FEED_HC_DES
        assert starved.p_bub_bara < 250.0


def test_a_feed_with_no_co2_at_all_holds_the_design_ratios():
    """The `CO2 > 1e-9` branch, which is a division guard and not a physical statement."""
    no_co2 = run(gas={k: (0.0 if k == "CO2" else v) for k, v in GAS.items()},
                 liq={k: (0.0 if k == "CO2" else v) for k, v in LIQ.items()})
    assert no_co2.melt_nc == REACTOR_FEED_NC_DES
    assert no_co2.melt_hc == REACTOR_FEED_HC_DES


# ======================================================================================
# B-129: the heat of a net CO2 release (decided 2026-11-11, decision 185)
# ======================================================================================

def test_a_net_co2_release_costs_its_heat_and_v1_clamps_it_at_zero():
    """A melt that holds none of its volatiles (saturation fraction 0) sends the ejector's carbamate
    CO2 out with the gas, 2 403.50 kmol/h. V1 clamps the CO2 absorbed at zero: the duty is the gas's
    sensible heat, 2 366.90 kW, and the outlet 147.33 C. The rewrite charges the decomposition: the
    duty -20 704.31 kW, no steam raised, the outlet held at the shell's 147.0 C (As-Built Part CX)."""
    v1 = run(sat_frac=0.0, t_shell_c=147.0, release_heat=False)
    ours = run(sat_frac=0.0, t_shell_c=147.0)
    assert v1.gas_kmolh == ours.gas_kmolh and ours.gas_kmolh["CO2"] == pytest.approx(2403.50, abs=0.01)
    assert v1.duty_kw == pytest.approx(2366.90, abs=0.01) and v1.t_prod == pytest.approx(147.33, abs=0.01)
    assert ours.duty_kw == pytest.approx(-20704.31, abs=0.01)
    assert ours.q_steam_kw == 0.0 and ours.t_prod == 147.0


@pytest.mark.parametrize("sat_frac", [1.0, 0.3])
def test_where_the_melt_absorbs_co2_the_two_sides_are_the_same_to_the_bit(sat_frac):
    """The design point and a partly saturated melt absorb CO2, so the switch changes nothing."""
    assert run(sat_frac=sat_frac, release_heat=False) == run(sat_frac=sat_frac)
