"""What 322E001 does — the behaviour of the ported HP stripper.

Why this is separate from the equivalence suite
-----------------------------------------------
`tests/equivalence/test_stripper_equivalence.py` proves the port is V1. This file proves the
model is a stripper. The two questions are different and the second one does not need the V1
tree, so these tests keep running on a machine that has only the rewrite.

Six behaviours are pinned here, each an operating lesson the model exists to teach and each
one that a silent regression would otherwise survive:

  * the flooding block is IDENTICALLY INACTIVE at design, by the inequality 0.7448 < 1.0
    rather than by a tolerance;
  * a feed spike drives the bottom temperature UP, never down, toward the reactor liquor it
    was fed: the two flood rises share one 11 C ceiling (decided 2026-10-07, handoff B-9);
  * a feed collapse at constant CO2 drives it DOWN, because the sweep endotherm overpowers the
    steam-heating branch;
  * a composition choke does not cut the thermal split — it pushes NH3 and CO2 overhead as
    slip, which is the vapour load the carbamate condenser then has to take;
  * no species split fraction can exceed what was fed, whatever the K-value ratio does;
  * the duty responds to COMPOSITION and not only to tonnage.
"""

from __future__ import annotations

import math

import pytest

from ureasim.core.stream import MW_COMP
from ureasim.data import unit_322e001 as d
from ureasim.data.unit_321 import CO2_DES_KGH
from ureasim.data.unit_322r001 import REACTOR_FEED_HC_DES, REACTOR_FEED_NC_DES
from ureasim.thermo import iapws
from ureasim.units.synthesis.stripper import (
    HYDROLYSIS_GROUP_DES,
    hydrolysis_rate_group,
    stripper_322e001,
)

CO2_DES_TH = CO2_DES_KGH / 1000.0


# ======================================================================================
# 3. The flooding block
# ======================================================================================
# The tests below have to put the TUBE BUNDLE at a chosen fraction of its hydraulic limit,
# and scaling the reactor overflow does not do that on its own: the CO2 sweep is part of the
# tube-side mass and it does not scale with the liquid. So the overflow scale is solved for.

SWEEP_DES_KGH = d.FEED_DES_KGH - sum(
    d.FEED_207_KMOLH[k] * MW_COMP[k] for k in d.FEED_207_KMOLH)
OVERFLOW_DES_KGH = d.FEED_DES_KGH - SWEEP_DES_KGH


def overflow_at_flood_fraction(fraction: float) -> dict:
    """The reactor overflow that puts the bundle at ``fraction`` of its flooding limit."""
    target_kgh = d.N_TUBES * d.FLOOD_KGH_PER_TUBE * fraction
    scale = (target_kgh - SWEEP_DES_KGH) / OVERFLOW_DES_KGH
    return {k: v * scale for k, v in d.FEED_207_KMOLH.items()}


def test_flooding_is_inactive_at_design_by_inequality_not_tolerance():
    """0.7448 of the limit, so the excess is the literal 0.0 that `max` returns.

    The whole bit-exactness argument for this block is that it is a ONE-SIDED constraint the
    plant genuinely operates below — not an anchored ratio that happens to evaluate to one.
    """
    r = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA)
    assert r.flood_frac == d.FLOOD_DES_FRAC
    assert d.FLOOD_DES_FRAC < 1.0
    assert r.flood_excess == 0.0            # exactly, from max(negative, 0.0)
    assert r.dt_flood == 0.0
    assert r.g_flood == 1.0
    # 108.0 kg/h per tube against the 145 kg/h limit.
    assert r.flood_kgh_per_tube == pytest.approx(108.0, abs=0.1)


def test_flooding_starts_at_about_134_per_cent_of_design_load():
    """The plant-level limit that falls out of the DDS geometry and the IFS-166 figure.

    2600 tubes x 145 kg/h is 377 000 kg/h, which is 1/0.7448 of the design feed. That it lands
    near the source's own "110 % when new, 120 % at end of life" is the corroboration that the
    geometry and the limit belong together.
    """
    onset = 1.0 / d.FLOOD_DES_FRAC
    assert onset == pytest.approx(1.34, abs=0.01)
    assert d.N_TUBES * d.FLOOD_KGH_PER_TUBE == pytest.approx(377_000.0, rel=1e-3)

    lo = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA,
                          overflow_kmolh=overflow_at_flood_fraction(0.99))
    hi = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA,
                          overflow_kmolh=overflow_at_flood_fraction(1.02))
    assert lo.flood_frac == pytest.approx(0.99, abs=1e-6)
    assert lo.flood_excess == 0.0 and lo.g_flood == 1.0
    assert hi.flood_excess > 0.0 and hi.g_flood < 1.0


def test_the_bottom_temperature_signature_matches_the_source_observation():
    """3.5 deg C of bottom rise at 10 % over the flooding limit — the number K was fixed on.

    The ramp constant is not tuned: it is back-solved from Brouwer's reported 3-4 deg C in
    15 minutes. So this test checks that the constant still does what it was solved for.
    """
    r = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA,
                         overflow_kmolh=overflow_at_flood_fraction(1.10))
    assert r.flood_excess == pytest.approx(0.10, abs=1e-6)
    assert r.dt_flood == pytest.approx(3.5, abs=0.01)


def test_the_efficiency_knockdown_is_a_few_per_cent_not_a_collapse():
    """About 3 %, from the carbamate energy balance — no fitted constant anywhere in it.

    The superseded form used a borrowed 1/(1 + 1.5x), which gave a 13 % loss at 10 % over the
    limit against roughly 1-3 % from three independent checks, and double-counted the thermal
    path on top. The replacement needs no new constant because the bottom-temperature rise and
    the efficiency loss are the SAME event measured two ways.
    """
    r = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA,
                         overflow_kmolh=overflow_at_flood_fraction(1.10))
    assert 0.95 < r.g_flood < 1.0
    # 2.2 %, inside the 1-3 % band the three independent cross-checks give.
    assert 1.0 - r.g_flood == pytest.approx(0.022, abs=0.005)


def test_the_hydraulic_knockdown_saturates_far_above_its_own_floor():
    """It never reaches 0.50, and the reason is the energy balance rather than the clamp.

    The knockdown is `1 - m.cp.dT_flood / (n_carb.dH_carb)`. Both the numerator and the
    carbamate denominator are proportional to the feed, so the feed cancels and what is left
    is set by dT_flood, which saturates at the 11 deg C reactor-liquor gap. The limit is about
    0.93, whatever the overflow does.

    That is worth pinning rather than glossing: the 0.50 floor is a GUARD against an
    unphysical input, not an operating state the model can reach. Anyone reading the constant
    and expecting a deep hydraulic collapse would be reading it wrong — the deep collapse is
    g_T's, and this term is incremental to it.
    """
    previous = 1.0
    for fraction in (1.5, 3.0, 10.0, 100.0):
        r = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA,
                             overflow_kmolh=overflow_at_flood_fraction(fraction))
        assert r.flood_excess > 0.0
        assert r.g_flood <= previous
        assert r.g_flood > d.FLOOD_ETA_FLOOR
        previous = r.g_flood
    assert previous == pytest.approx(0.93, abs=0.01)
# ======================================================================================
# 4. The bottom temperature has the right SIGN in both directions
# ======================================================================================

def test_a_feed_spike_drives_the_bottom_up_monotonically_and_never_past_the_shell():
    """Never down, and bounded by the reactor liquor it was fed. Handoff B-9, decided 2026-10-07.

    This is the defect the separate dT_bot driver exists to fix. Feeding the raw linear load
    into the temperature drove it down without bound — an infinite feed gave about -0.4 deg C,
    which is absurd and the wrong sign as well. A flooded stripper is steam-limited: the
    carbamate endotherm fades and hot reactor liquor falls through the tubes untouched, so the
    bottom must RISE toward the liquor it was fed.

    The ceiling: the steam-dilution branch saturates at +11 deg C and the hydraulic flooding
    branch at +11 deg C, both on the gap to the reactor liquor, and they describe one end state.
    The port takes the larger of the two (the process engineer's decision on handoff B-9), so
    the bottoms tend to the 183 deg C fed. V1 adds them and tends to 194 deg C; the equivalence
    file asserts both sides.
    """
    previous = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA).t_bot
    for scale in (1.2, 1.6, 2.5, 5.0, 20.0):
        overflow = {k: v * scale for k, v in d.FEED_207_KMOLH.items()}
        r = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA, overflow_kmolh=overflow)
        assert r.t_bot >= previous, f"bottom fell at x{scale}"
        assert r.t_bot <= r.t_steam, f"bottom passed the shell at x{scale}"
        # The flood rise is inside the 11 deg C reactor-liquor gap, and so is the larger of
        # the two (B-9): one ceiling, not two stacked.
        assert r.dt_flood <= d.FLOOD_GAP_DES_C + 1e-9
        assert r.dt_flood <= r.dt_bot <= d.FLOOD_GAP_DES_C + 1e-9
        previous = r.t_bot
    # ...so the bottoms tend to the reactor liquor, 183 deg C.
    assert previous == pytest.approx(d.T_BOTTOM_DES_C + d.FLOOD_GAP_DES_C, abs=0.05)


def test_a_flood_gives_hot_but_unstripped_bottoms():
    """Hot AND choked at once, which is the whole point of separating the two drivers.

    g_T stays on the raw load while the temperature saturates, so the volatiles are left in
    the bottoms and slip to the LP section through LV-322501 — more NH3 to LP recirculation,
    LP pressure rises, and the operator has to cut load. That cascade is the lesson.
    """
    overflow = {k: v * 2.0 for k, v in d.FEED_207_KMOLH.items()}
    r = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA, overflow_kmolh=overflow)
    design = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA)
    assert r.t_bot > design.t_bot                       # hotter
    assert r.g_t < 1.0                                  # and choked
    # The NH3 that was not stripped is in the bottoms, per unit of solution.
    assert r.bot_mass_pct["NH3"] > design.bot_mass_pct["NH3"]


def test_a_feed_collapse_at_constant_sweep_drives_the_bottom_colder():
    """The G/L endotherm OVERPOWERS the steam-heating branch, which is the plant behaviour.

    The compressor holds the sweep while the liquid feed falls away, so the gas/liquid ratio
    spikes. The excess gas forces carbamate decomposition and an NH3/CO2 flash, and that
    endotherm is larger than the extra specific heating the steam now delivers. Without this
    term the model would say a stripper losing its liquid feed runs toward steam saturation,
    which is the opposite of what happens.
    """
    design = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA)
    overflow = {k: v * 0.35 for k, v in d.FEED_207_KMOLH.items()}
    r = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA, overflow_kmolh=overflow)
    assert r.r_gl > 0.0
    assert r.dt_strip < 0.0
    assert r.dt_load > 0.0                              # the steam branch IS heating
    assert r.t_bot < design.t_bot                       # and it still ends up colder


def test_the_endotherm_saturates_instead_of_running_away():
    """No pole as the liquid feed goes to zero; it approaches its stated asymptote."""
    overflow = {k: v * 0.001 for k, v in d.FEED_207_KMOLH.items()}
    r = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA, overflow_kmolh=overflow)
    assert math.isfinite(r.t_bot)
    assert r.dt_strip > -d.STRIPCOOL_MAX_C
    assert r.dt_strip == pytest.approx(-d.STRIPCOOL_MAX_C, abs=0.5)


def test_neither_product_can_out_heat_the_condensing_shell():
    """A hard ceiling on both, at every steam pressure and every feed rate."""
    for p_mp in (12.0, 19.7, 25.0):
        t_steam = iapws.tsat_c(p_mp)
        for scale in (0.3, 1.0, 3.0):
            overflow = {k: v * scale for k, v in d.FEED_207_KMOLH.items()}
            r = stripper_322e001(CO2_DES_TH, t_steam, d.P_DES_BARA, overflow_kmolh=overflow)
            assert r.t_bot <= t_steam + 1e-12
            assert r.t_top <= t_steam + 1e-12


def test_the_overhead_feels_the_two_drivers_with_different_weights():
    """The load swing arrives attenuated; the sweep endotherm arrives at full weight.

    That asymmetry is physical rather than a fitting choice: the feed-load swing is a
    liquid-side reboiler effect, while the rising vapour is the first thing to carry the
    latent load of the sweep-gas flash.
    """
    overflow = {k: v * 1.8 for k, v in d.FEED_207_KMOLH.items()}
    flooded = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA, overflow_kmolh=overflow)
    # The overhead moved by the attenuation factor times the bottom's own load-driven rise.
    top_rise = flooded.t_top - d.T_TOPGAS_DES_C
    assert top_rise == pytest.approx(d.T_TOP_LOAD_K * flooded.dt_bot + flooded.dt_strip,
                                     abs=1e-9)

    lean = {k: v * 0.35 for k, v in d.FEED_207_KMOLH.items()}
    cooled = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA, overflow_kmolh=lean)
    # On the strip-cool branch the overhead takes the FULL endotherm.
    assert cooled.t_top - d.T_TOPGAS_DES_C == pytest.approx(
        d.T_TOP_LOAD_K * cooled.dt_bot + cooled.dt_strip, abs=1e-9)
    assert cooled.dt_strip < 0.0
# ======================================================================================
# 5. Composition choke, slip, and the split transform
# ======================================================================================

def test_a_composition_choke_pushes_volatiles_overhead_rather_than_cutting_the_split():
    """Excess NH3 in the reactor feed raises the vapour load back to the carbamate condenser.

    This is the counter-intuitive one and it is why the penalty is not simply a multiplier on
    the split. A solution that is hard to strip THERMALLY does not quietly keep its volatiles:
    it breaks them through to the overhead, and the condenser downstream has to take them.
    """
    design = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA)
    rich = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA,
                            feed_nc=REACTOR_FEED_NC_DES + 0.2)
    assert rich.g_nc < 1.0
    assert rich.slip > 0.0
    assert rich.eta_t < design.eta_t                    # the REPORTED efficiency falls
    # ...and yet more NH3 and CO2 leave overhead, not less.
    assert rich.top_kmolh["NH3"] > design.top_kmolh["NH3"]
    assert rich.top_kmolh["CO2"] > design.top_kmolh["CO2"]


def test_the_two_composition_penalties_have_a_floor():
    """Neither can drive the term below 0.50, however far off the feed ratios go."""
    r = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA,
                         feed_nc=REACTOR_FEED_NC_DES + 5.0,
                         feed_hc=REACTOR_FEED_HC_DES + 5.0)
    assert r.g_nc == d.ETA_FLOOR
    assert r.g_hc == d.ETA_FLOOR
    assert r.slip == pytest.approx(1.0, abs=1e-12)


def test_no_species_can_be_stripped_more_than_it_was_fed():
    """The property the multiply this replaced could not hold.

    A bare `theta * eta_P` at eta_P = 1.15 sent the N2 split to 1.148 and let a clamp silently
    truncate the excess — i.e. the column was asked to strip more nitrogen than entered it.
    `ratio_shift_frac` maps [0,1] onto [0,1] for any ratio, so the question cannot arise.
    """
    for p_bara in (100.0, 120.0, 144.0, 170.0, 200.0):
        for nc in (REACTOR_FEED_NC_DES, REACTOR_FEED_NC_DES + 0.5):
            r = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, p_bara, feed_nc=nc)
            for species in MW_COMP:
                assert r.top_kmolh[species] >= 0.0
                assert r.bot_kmolh[species] >= -1e-12
                total = r.top_kmolh[species] + r.bot_kmolh[species]
                assert r.top_kmolh[species] <= total + 1e-9
def test_a_non_distributing_species_stays_non_distributing():
    """Urea does not leave a stripper overhead at any pressure, and an inert does not stay."""
    for p_bara in (100.0, 144.0, 200.0):
        r = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, p_bara)
        assert r.top_kmolh["Urea"] == 0.0
        assert r.top_kmolh["Biuret"] == 0.0
        assert r.bot_kmolh["N2"] < 0.01 * max(r.feed_kmolh["N2"], 1e-12)

def test_the_rate_law_cannot_reach_the_pfd_extent_which_is_why_it_is_anchored():
    """The measurement that decided hydrolysis is anchored rather than predicted.

    Even with the WHOLE vessel flooded — the bundle plus the sump at 100 % — the second-order
    group delivers about a fifth of the licensor extent. The constant is therefore not urea
    hydrolysis alone; it lumps carbamate decomposition, which is what the stripper is for.
    Predicting it outright would be fitting a rate constant to a different reaction.
    """
    # The bundle alone: 12.02 kmol/h, a seventh of the licensor extent.
    bundle_only = hydrolysis_rate_group(
        d.T_BOTTOM_DES_C, d.FEED_DES_KMOLH["Urea"], d.FEED_DES_KMOLH["H2O"],
        d.VDOT_DES_M3H, d.V_TUBES_M3)
    assert bundle_only == pytest.approx(12.02, abs=0.05)
    # Bundle plus the sump at its design level: 17.48, which is the anchor denominator.
    assert HYDROLYSIS_GROUP_DES == pytest.approx(17.48, abs=0.05)
    # The whole vessel liquid-full — the physical maximum — still reaches only 26 %.
    flooded_group = hydrolysis_rate_group(
        d.T_BOTTOM_DES_C, d.FEED_DES_KMOLH["Urea"], d.FEED_DES_KMOLH["H2O"],
        d.VDOT_DES_M3H, d.V_TUBES_M3 + d.V_SUMP_M3)
    assert flooded_group == pytest.approx(22.94, abs=0.05)
    assert flooded_group < 0.30 * d.XI_HYDROLYSIS_DES


def test_hydrolysis_rises_with_holdup_and_with_temperature():
    """The two departures the rate law is there to supply."""
    low = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA, level_pct=0.0)
    high = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA, level_pct=100.0)
    assert high.xi_hydrolysis > low.xi_hydrolysis

    hot = stripper_322e001(CO2_DES_TH, iapws.tsat_c(25.0), d.P_DES_BARA)
    design = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA)
    assert hot.t_bot > design.t_bot
    assert hot.xi_hydrolysis > design.xi_hydrolysis


def test_hydrolysis_can_never_consume_more_than_is_present():
    """Capped by the scarcer of urea and water, and never negative."""
    dry = dict(d.FEED_207_KMOLH, H2O=5.0)
    r = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA,
                         overflow_kmolh=dry, level_pct=100.0)
    assert 0.0 <= r.xi_hydrolysis <= 5.0
    lean = dict(d.FEED_207_KMOLH, Urea=3.0)
    r = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA,
                         overflow_kmolh=lean, level_pct=100.0)
    assert 0.0 <= r.xi_hydrolysis <= 3.0


def test_biuret_is_second_order_in_urea_and_rises_on_turndown():
    """Both corrections to the superseded first-order form, checked separately.

    2 Urea -> Biuret + NH3 is second order, and it has a holdup term. A deep turndown means a
    more urea-rich melt sitting longer, which raises biuret — the reason biuret is a turndown
    problem on a real plant and not a full-rate one.
    """
    design = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA)
    # Second order: doubling the urea alone quadruples the concentration term.
    double_urea = dict(d.FEED_207_KMOLH, Urea=2.0 * d.FEED_207_KMOLH["Urea"])
    r = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA, overflow_kmolh=double_urea)
    assert r.xi_biuret > 3.0 * design.xi_biuret
    # Holdup: the same throughput held longer. This is the residence-time term, and it is the
    # one a turndown actually reaches on the plant — through the sump level, not through the
    # feed rate. Scaling the whole overflow down does NOT raise biuret per unit of urea,
    # because concentration and residence time move together and cancel; what raises it is
    # holding liquid up while throughput falls.
    shallow = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA, level_pct=0.0)
    deep = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA, level_pct=100.0)
    assert deep.xi_biuret > shallow.xi_biuret
    # Temperature: the Arrhenius term, at the design holdup.
    hot = stripper_322e001(CO2_DES_TH, iapws.tsat_c(25.0), d.P_DES_BARA)
    assert hot.t_bot > design.t_bot
    assert hot.xi_biuret > design.xi_biuret


def test_biuret_can_never_consume_more_urea_than_hydrolysis_left():
    """Two urea per biuret, taken from what survived the first reaction."""
    lean = dict(d.FEED_207_KMOLH, Urea=10.0)
    r = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA,
                         overflow_kmolh=lean, level_pct=100.0)
    urea_left = max(10.0 - r.xi_hydrolysis, 0.0)
    assert 0.0 <= r.xi_biuret <= 0.5 * urea_left + 1e-12


def test_the_reactions_conserve_atoms_into_the_split():
    """Both stoichiometries, checked on the vector that is actually split.

    Urea + H2O -> 2 NH3 + CO2, and 2 Urea -> Biuret + NH3. If the deltas were wrong the unit
    would create or destroy nitrogen, and the loop balance would close on a fiction.
    """
    for scale in (0.5, 1.0, 1.5):
        overflow = {k: v * scale for k, v in d.FEED_207_KMOLH.items()}
        r = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA, overflow_kmolh=overflow)
        available = {k: r.top_kmolh[k] + r.bot_kmolh[k] for k in MW_COMP}
        xi_h, xi_b = r.xi_hydrolysis, r.xi_biuret
        assert available["Urea"] == pytest.approx(
            r.feed_kmolh["Urea"] - xi_h - 2.0 * xi_b, abs=1e-9)
        assert available["NH3"] == pytest.approx(
            r.feed_kmolh["NH3"] + 2.0 * xi_h + xi_b, abs=1e-9)
        assert available["CO2"] == pytest.approx(r.feed_kmolh["CO2"] + xi_h, abs=1e-9)
        assert available["H2O"] == pytest.approx(r.feed_kmolh["H2O"] - xi_h, abs=1e-9)
        assert available["Biuret"] == pytest.approx(r.feed_kmolh["Biuret"] + xi_b, abs=1e-9)
# ======================================================================================
# 7. The enthalpy balance
# ======================================================================================

def test_the_duty_responds_to_composition_and_not_only_to_tonnage():
    """The defect the per-species balance exists to fix.

    The superseded form was duty proportional to feed MASS, which says a stripper fed the same
    tonnage of pure water and of carbamate-rich reactor liquor needs the same steam. Here the
    same tonnage of a carbamate-lean feed costs visibly less.
    """
    design = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA)
    # Same total moles, but the NH3/CO2 moved into urea and water: far less to dissociate.
    lean = dict(d.FEED_207_KMOLH)
    moved = 0.6 * lean["CO2"]
    lean["CO2"] -= moved
    lean["NH3"] -= 2.0 * moved
    lean["H2O"] += 3.0 * moved
    r = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA, overflow_kmolh=lean)
    assert r.q_carbamate_kw < design.q_carbamate_kw
    assert r.duty_raw_kw < design.duty_raw_kw


def test_the_carbamate_term_dominates_the_design_duty():
    """About 58 % of it — which is the sink the feed-proportional form made invisible."""
    r = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA)
    assert r.q_carbamate_kw / r.duty_raw_kw == pytest.approx(0.58, abs=0.05)
    # Water is the small one, and hydrolysis gives heat BACK.
    assert r.q_h2o_kw / r.duty_raw_kw == pytest.approx(0.07, abs=0.03)
    assert r.q_hydrolysis_kw < 0.0


def test_the_sweep_gas_is_not_charged_to_the_duty():
    """CO2 that arrives already gaseous needs no dissociation or desorption heat.

    Getting this wrong would make the steam header pay for the compressor's work, and the duty
    would rise with the sweep rate instead of falling with it.
    """
    r = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA)
    assert r.n_co2_desorbed == pytest.approx(
        r.top_kmolh["CO2"] - r.co2_feed_kmolh["CO2"], abs=1e-9)
    assert r.n_co2_desorbed < r.top_kmolh["CO2"]
    # With no sweep at all, every overhead CO2 mole came out of the liquid.
    dry = stripper_322e001(0.0, d.STEAM_T_DES_C, d.P_DES_BARA)
    assert dry.n_co2_desorbed == dry.top_kmolh["CO2"]


def test_a_hotter_reactor_reduces_the_steam_demand():
    """The sensible term, and the reason the live feed temperature is passed in at all."""
    cool = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA, t_feed_c=175.0)
    hot = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA, t_feed_c=192.0)
    assert hot.q_sensible_kw < cool.q_sensible_kw
    assert hot.duty_raw_kw < cool.duty_raw_kw


def test_the_nh3_desorption_enthalpy_is_the_loop_s_own_value():
    """23 000 J/mol, the same number the carbamate condenser uses at the other end.

    NH3 is supercritical at stripper temperature, so there is no latent heat to look up; what
    the duty pays is the desorption enthalpy out of the melt. It is restated in the data module
    rather than aliased because the two units are ported at different times — this assertion is
    what stops them drifting apart in the meantime.
    """
    assert d.DH_NH3_DESORB_JMOL == 23_000.0
    # And the water term is the steam-table latent heat at about 170 deg C.
    assert d.DH_H2O_VAP_JMOL / 18.0152 == pytest.approx(2049.0, abs=2.0)


def test_the_derived_geometry_agrees_with_the_datasheet_surface():
    """The DDS is self-consistent, which is what licenses using it for a hydraulic limit.

    N . pi . d_o . L against the tabulated exchange surface: 1519.27 versus 1519.00 m2.
    """
    computed = d.N_TUBES * math.pi * d.TUBE_OD_M * d.TUBE_L_EFF_M
    assert computed == pytest.approx(d.SURFACE_DES_M2, rel=2.0e-4)
    # And the tube ID is 0.984 inch, so the one-inch flooding figure needs no scaling.
    assert d.TUBE_ID_M / 0.0254 == pytest.approx(0.984, abs=0.001)


def test_the_design_pressure_drop_is_a_subtraction_not_a_decimal():
    """Handoff A-13, at this unit's own design differential."""
    assert d.DP_TO_LOOP_DES_BAR == d.P_DES_BARA - 140.7
    assert d.DP_TO_LOOP_DES_BAR == pytest.approx(3.3, abs=1e-9)
