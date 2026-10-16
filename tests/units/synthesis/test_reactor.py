"""322R001 behaviour — what the reactor does, and what its calibration leaves undone.

These tests are about the plant, not about V1. Equivalence is proven separately and bit for
bit in `tests/equivalence/test_reactor_equivalence.py`; what is asserted here is that the
ported model behaves the way a urea reactor behaves, and that the places where it does not
are measured rather than assumed.
"""

from __future__ import annotations

import math

import pytest

from ureasim.core.stream import MW_COMP
from ureasim.data.unit_320 import SYN_P_DES_BARA
from ureasim.data.unit_321 import CO2_DES_KGH
from ureasim.data.unit_322r001 import (
    AREA_M2,
    HIC605_DES_PCT,
    LEVEL_NLL_PCT,
    LIQ_H_M,
    NODE_TAGS,
    OFFGAS_DES_KMOLH,
    OVERFLOW_DES_KGH,
    OVERFLOW_DES_KMOLH,
    OVERFLOW_T_DES_C,
    THETA_OFFGAS,
    VDOT_DES_M3H,
    WEIR_CREST_M,
    WEIR_CW,
    XI_BIURET_DES,
    XI_UREA_DES,
    ZETA_NODES,
)
from ureasim.thermo.kinetics import urea_keq_overall
from ureasim.thermo.service import anchored_split
from ureasim.units.synthesis.carbamate_condenser import DESIGN as HPCC_DES
from ureasim.units.synthesis.reactor import (
    ANCHOR_SEED,
    CP_MELT_KJKGK,
    DESIGN,
    KINETICS,
    M_LIQ_DES_KG,
    NODE_PROFILE_DES,
    Q_COL_DES_KJH,
    RHO_BULK_DES,
    T_BULK_DES_C,
    XI_CARBAMATE_DES,
    apply_reaction_extents,
    reactor_322r001,
)
from ureasim.units.synthesis.reactor_column import (
    biuret_extent,
    equilibrium_extent,
    node_liquid_volumes,
    urea_extent_pfr,
)
from ureasim.units.synthesis.reactor_hydraulics import (
    hv322605_kv,
    level_from_holdup,
    melt_density,
    node_dtdt,
    outlet_line_outflow_kgh,
    weir_outflow_kgh,
)

DESIGN_LEVEL = LEVEL_NLL_PCT / 100.0
DESIGN_CO2_TH = CO2_DES_KGH / 1000.0


def run(**kwargs):
    """Evaluate the reactor at design unless a keyword overrides it."""
    args = dict(feed_kmolh=HPCC_DES.feed_kmolh,
                gas_co2_in_kmolh=HPCC_DES.gas_kmolh["CO2"],
                co2_feed_th=DESIGN_CO2_TH, hic605_pct=HIC605_DES_PCT,
                p_loop_bara=SYN_P_DES_BARA, kinetics=KINETICS)
    args.update(kwargs)
    return reactor_322r001(**args)


# ======================================================================================
# The design point
# ======================================================================================

def test_axial_profile_rises_monotonically_to_the_overflow():
    """Bottom to top, and it lands on the PFD's 183 C at the lip — an anchor, not a fit."""
    assert NODE_PROFILE_DES == sorted(NODE_PROFILE_DES)
    assert NODE_PROFILE_DES[-1] == pytest.approx(OVERFLOW_T_DES_C, abs=1e-9)
    assert NODE_PROFILE_DES[0] > HPCC_DES.t_prod       # node 1 is already above the feed


def test_design_march_makes_the_published_extent():
    """A2 is solved for exactly this, so it is a check on the solve, not on the physics."""
    xi, per_node = urea_extent_pfr(
        HPCC_DES.feed_kmolh, NODE_PROFILE_DES, ZETA_NODES, AREA_M2, LIQ_H_M,
        DESIGN_LEVEL, VDOT_DES_M3H, KINETICS)
    assert xi == pytest.approx(XI_UREA_DES, rel=1e-12)
    assert sum(per_node) == pytest.approx(xi, rel=1e-12)
    assert all(x > 0.0 for x in per_node)


def test_the_bottom_node_is_the_smallest_contributor():
    """It is 4 % of the column height, so it gets 4 % of the residence time.

    Worth pinning because the SUPERSEDED heat-release shape put nearly the whole temperature
    rise below the second thermowell. The march's own profile does not: the extent is spread
    over the three tall nodes and the short bottom one contributes least of all.
    """
    per_node = DESIGN.xi_nodes
    assert per_node[0] == min(per_node)
    assert per_node[0] / sum(per_node) < 0.06
    assert node_liquid_volumes(ZETA_NODES, AREA_M2, LIQ_H_M, DESIGN_LEVEL)[0] \
        == pytest.approx(0.04 * LIQ_H_M * AREA_M2, rel=1e-12)


def test_the_profile_against_the_plants_own_trend():
    """The four thermowells against 1921 DCS samples of normal operation.

    Source: `References/Urea_NormalOp_29-06-2025_Trends.md`, the mean of each tag. The
    licensor's mechanism — carbamate absorption distributed over the liquid volume, with no
    fitted shape parameter — lands inside half a degree everywhere.

    The figure V1's own comment quotes for this model (RMS 0.78 C, profile
    170.77 / 173.60 / 178.20 / 183.00) is STALE: it predates the joint solve that fixes the
    profile and the pre-exponential together. Re-measured here against the same trend.
    """
    measured = {"TT_322008": 171.134, "TT_322007": 174.303,
                "TT_322006": 179.697, "TT_322005": 183.084}
    errors = [NODE_PROFILE_DES[i] - measured[tag] for i, tag in enumerate(NODE_TAGS)]
    rms = math.sqrt(sum(e * e for e in errors) / len(errors))
    assert max(abs(e) for e in errors) < 0.60
    assert rms == pytest.approx(0.432, abs=0.005)


def test_the_exotherm_is_carbamate_and_the_dehydration_takes_a_sixth_of_it_back():
    """The two terms oppose, which is why more urea means LESS heat."""
    from ureasim.thermo.kinetics import CARBAMATE_DH_JMOL, DEHYDRATION_DH_JMOL

    carbamate_kw = XI_CARBAMATE_DES * (-CARBAMATE_DH_JMOL) / 3600.0
    dehydration_kw = XI_UREA_DES * DEHYDRATION_DH_JMOL / 3600.0
    assert carbamate_kw == pytest.approx(9481.0, rel=1e-3)
    assert dehydration_kw == pytest.approx(5607.0, rel=1e-3)
    assert Q_COL_DES_KJH / 3600.0 == pytest.approx(carbamate_kw - dehydration_kw, rel=1e-12)
    # Net 3.87 MW into 226 t/h of melt at 4.74 kJ/(kg.K) is the PFD's 13 C, by construction.
    assert Q_COL_DES_KJH / (OVERFLOW_DES_KGH * CP_MELT_KJKGK) == pytest.approx(13.0, rel=1e-12)


def test_the_holdup_is_a_hundred_and_thirty_six_tonnes():
    """Level, density and bore in one number — and the reason this vessel is slow."""
    assert T_BULK_DES_C == pytest.approx(176.96, abs=0.01)
    assert RHO_BULK_DES == pytest.approx(994.19, abs=0.01)
    assert M_LIQ_DES_KG == pytest.approx(135_904.0, rel=1e-4)
    assert level_from_holdup(M_LIQ_DES_KG, T_BULK_DES_C, AREA_M2) == pytest.approx(
        DESIGN_LEVEL * LIQ_H_M, rel=1e-12)


# ======================================================================================
# What the calibration leaves undone
# ======================================================================================

def test_biuret_is_calibrated_at_the_superseded_profile():
    """The biuret pre-exponential is solved at the SEED profile and never re-solved.

    `calibrate_kinetics` fixes it against the residence-time seed; the joint solve then moves
    the profile 2.7 C colder on the node mean and re-solves the UREA pre-exponential against
    its own anchor — but nothing re-solves the biuret one. At the profile the plant actually
    runs, the extent therefore comes out about 13 % below the PFD's 2.414 kmol/h, on the
    plant's principal product-quality specification.

    V1 has the same gap and corrects it at boot, by re-running the whole calibration against
    a settled plant. Nothing at import can do that, so the number is measured here and the
    engine's obligation is recorded in `handoff.md`.
    """
    xi = biuret_extent(NODE_PROFILE_DES, ZETA_NODES, AREA_M2, LIQ_H_M, DESIGN_LEVEL,
                       VDOT_DES_M3H, OVERFLOW_DES_KMOLH["Urea"], KINETICS)
    assert xi == pytest.approx(2.0737, abs=0.001)
    assert xi / XI_BIURET_DES == pytest.approx(0.859, abs=0.002)

    # And it is the temperature, not anything else: evaluating the same rate law at the SEED
    # profile the constant was solved at returns the PFD extent to the last bit.
    from ureasim.data.unit_322r001 import BETA_DAMKOHLER
    from ureasim.units.synthesis.reactor_column import node_profile_ss

    seed = node_profile_ss(HPCC_DES.t_prod, OVERFLOW_T_DES_C, ZETA_NODES, BETA_DAMKOHLER)
    assert sum(seed) / 4.0 - T_BULK_DES_C == pytest.approx(2.75, abs=0.01)
    assert biuret_extent(seed, ZETA_NODES, AREA_M2, LIQ_H_M, DESIGN_LEVEL, VDOT_DES_M3H,
                         OVERFLOW_DES_KMOLH["Urea"], KINETICS) == pytest.approx(
                             XI_BIURET_DES, rel=1e-12)


def test_the_anchor_throughput_is_on_a_different_density_basis():
    """Two design throughputs, 0.42 % apart, and the extent notices.

    The calibration divides the design overflow by the PFD's constant solution density; the
    boot anchor divides it by the melt density at the column's own bulk temperature. The
    second is the more physical of the two and it is NOT the one the pre-exponential was
    solved at, so calling the unit through the anchor without re-calibrating overshoots the
    published extent.

    V1 records the same mismatch and resolves it the same way this one must be: re-run the
    calibration at whatever state the engine actually seeds.
    """
    assert ANCHOR_SEED["vdot_m3h"] / VDOT_DES_M3H == pytest.approx(0.99579, abs=1e-5)
    at_calibration = run(vdot_m3h=VDOT_DES_M3H).xi_urea
    at_anchor = run(vdot_m3h=ANCHOR_SEED["vdot_m3h"]).xi_urea
    assert at_calibration == pytest.approx(XI_UREA_DES, rel=1e-12)
    assert at_anchor > at_calibration                  # longer residence, more conversion
    assert at_anchor / at_calibration - 1.0 == pytest.approx(0.0028, abs=0.0004)


# ======================================================================================
# The conversion optimum
# ======================================================================================

def test_conversion_has_an_optimum_in_temperature():
    """Rate rises with temperature, the attainable conversion falls, and they cross.

    This is the single most important thing the Phase 3 rate law bought over the correlation
    it replaced, and it is not a fitted parabola: it falls out of an Arrhenius rate constant
    working against an EXOTHERMIC overall equilibrium. An operator pushing reactor
    temperature for conversion is trading one against the other, and past the optimum the
    trade stops paying.
    """
    def extent(t_c: float) -> float:
        return urea_extent_pfr(HPCC_DES.feed_kmolh, [t_c] * 4, ZETA_NODES, AREA_M2, LIQ_H_M,
                               DESIGN_LEVEL, VDOT_DES_M3H, KINETICS)[0]

    grid = list(range(150, 271, 5))
    extents = [extent(float(t)) for t in grid]
    peak = max(range(len(grid)), key=lambda i: extents[i])
    assert 0 < peak < len(grid) - 1, "the optimum must be interior, not at a bracket end"
    assert 180.0 <= grid[peak] <= 215.0
    assert extents[-1] < 0.85 * extents[peak], "an over-hot column must LOSE conversion"


def test_the_equilibrium_constant_falls_with_temperature():
    """van 't Hoff on an exothermic overall reaction. The ceiling drops as the column heats."""
    keq = [urea_keq_overall(t, KINETICS.keq_ov_ref, KINETICS.t_ref_k)
           for t in (150.0, 183.0, 220.0, 260.0)]
    assert keq == sorted(keq, reverse=True)


def test_equilibrium_extent_goes_negative_on_a_product_rich_hot_stream():
    """The signed extent is what makes the reverse branch real rather than a floor at zero."""
    rich = dict(HPCC_DES.feed_kmolh)
    rich["Urea"] = 2000.0
    rich["H2O"] = 4000.0
    hot = urea_keq_overall(280.0, KINETICS.keq_ov_ref, KINETICS.t_ref_k)
    assert equilibrium_extent(rich, VDOT_DES_M3H, hot) < 0.0
    cold = urea_keq_overall(150.0, KINETICS.keq_ov_ref, KINETICS.t_ref_k)
    assert equilibrium_extent(HPCC_DES.feed_kmolh, VDOT_DES_M3H, cold) > 0.0


def test_no_flow_and_no_equilibrium_are_refused_rather_than_divided_by():
    assert equilibrium_extent(HPCC_DES.feed_kmolh, 0.0, 1.0) == 0.0
    assert equilibrium_extent(HPCC_DES.feed_kmolh, VDOT_DES_M3H, 0.0) == 0.0
    assert urea_extent_pfr(HPCC_DES.feed_kmolh, NODE_PROFILE_DES, ZETA_NODES, AREA_M2,
                           LIQ_H_M, DESIGN_LEVEL, 0.0, KINETICS) == (0.0, [0.0] * 4)


# ======================================================================================
# Residence time is a plant variable
# ======================================================================================

def test_draining_the_column_costs_conversion():
    """Level IS residence time here, so protecting the stripper costs product."""
    full = run(level_frac=1.00).x_conv
    normal = run(level_frac=DESIGN_LEVEL).x_conv
    half = run(level_frac=0.50).x_conv
    empty = run(level_frac=0.0).x_conv
    assert full > normal > half > empty
    assert empty == 0.0
    assert half / normal < 0.95


def test_a_node_above_the_surface_contributes_nothing():
    """A node spans from the thermowell below it, so it dries out below THAT elevation.

    Node 4 runs from zeta 0.592 to 0.868. At half level it is entirely dry; at 0.60 it is
    still wetted, by the 0.008 of span between the third thermowell and the surface. The
    distinction matters because it is what makes the conversion loss on a level drop
    continuous rather than stepped.
    """
    dry = node_liquid_volumes(ZETA_NODES, AREA_M2, LIQ_H_M, 0.50)
    assert dry[3] == 0.0
    assert dry[2] > 0.0
    assert sum(dry) == pytest.approx(0.50 * LIQ_H_M * AREA_M2, rel=1e-12)

    partly = node_liquid_volumes(ZETA_NODES, AREA_M2, LIQ_H_M, 0.60)
    assert partly[3] == pytest.approx((0.60 - 0.592) * LIQ_H_M * AREA_M2, rel=1e-12)


def test_turndown_raises_per_pass_conversion_and_the_sign_is_the_point():
    """Same vessel, less throughput, longer residence — so conversion RISES on turndown.

    The column's wetted volume is set by geometry and level, not by flow, so scaling the feed
    scales the residence time inversely. A plant at 70 % load converts 0.660 per pass against
    0.542 at design and 0.510 at 110 %. That is the right sign and it is the reason the
    anchor scales its throughput with the feed mass at all: freezing the throughput instead
    turns a turndown into a concentration change, and V1 measured the conversion moving the
    OTHER way (0.541 at 70 % to 0.559 at 110 %) before the scaling was added.

    It is also why hitting nameplate is harder than hitting half of it: per-pass conversion
    falls as the plant is pushed, and the recycle loop absorbs the difference.
    """
    from ureasim.units.synthesis.reactor import ColumnAnchor

    m_feed_des = sum(HPCC_DES.feed_kmolh.get(k, 0.0) * MW_COMP[k] for k in MW_COMP)
    anchor = ColumnAnchor(t_nodes_c=list(NODE_PROFILE_DES), level_frac=DESIGN_LEVEL,
                          vdot_m3h=VDOT_DES_M3H, m_feed_kgh=m_feed_des)
    conversions = {}
    for load in (0.70, 0.85, 1.00, 1.10):
        feed = {k: v * load for k, v in HPCC_DES.feed_kmolh.items()}
        conversions[load] = reactor_322r001(
            feed, HPCC_DES.gas_kmolh["CO2"] * load, DESIGN_CO2_TH * load, HIC605_DES_PCT,
            SYN_P_DES_BARA, KINETICS, anchor=anchor).x_conv
    loads = sorted(conversions)
    assert [conversions[k] for k in loads] == sorted(
        (conversions[k] for k in loads), reverse=True)
    assert conversions[1.00] == pytest.approx(XI_UREA_DES / HPCC_DES.feed_kmolh["CO2"],
                                              rel=1e-3)
    assert conversions[0.70] == pytest.approx(0.660, abs=0.005)
    assert conversions[1.10] == pytest.approx(0.510, abs=0.005)


def test_biuret_rises_with_temperature_and_with_residence_time():
    """The quality lesson: everything that makes the reactor productive also makes biuret."""
    base = biuret_extent(NODE_PROFILE_DES, ZETA_NODES, AREA_M2, LIQ_H_M, DESIGN_LEVEL,
                         VDOT_DES_M3H, OVERFLOW_DES_KMOLH["Urea"], KINETICS)
    hotter = biuret_extent([t + 15.0 for t in NODE_PROFILE_DES], ZETA_NODES, AREA_M2,
                           LIQ_H_M, DESIGN_LEVEL, VDOT_DES_M3H,
                           OVERFLOW_DES_KMOLH["Urea"], KINETICS)
    fuller = biuret_extent(NODE_PROFILE_DES, ZETA_NODES, AREA_M2, LIQ_H_M, 1.00,
                           VDOT_DES_M3H, OVERFLOW_DES_KMOLH["Urea"], KINETICS)
    assert hotter > 1.5 * base
    assert fuller > base


# ======================================================================================
# Conservation
# ======================================================================================

N_ATOMS_ALL = {"NH3": 1, "Urea": 2, "Biuret": 3, "N2": 2}
C_ATOMS_ALL = {"CO2": 1, "Urea": 1, "Biuret": 2, "CH4": 1}


def atoms(vec: dict) -> tuple[float, float]:
    """Nitrogen and carbon in a molar vector [kmol/h each]."""
    return (sum(vec.get(k, 0.0) * n for k, n in N_ATOMS_ALL.items()),
            sum(vec.get(k, 0.0) * c for k, c in C_ATOMS_ALL.items()))


@pytest.mark.parametrize("xi_urea, xi_biuret", [(0.0, 0.0), (1302.27, 2.414),
                                                (500.0, 30.0), (-100.0, 5.0)])
def test_stoichiometry_conserves_atoms(xi_urea, xi_biuret):
    out = apply_reaction_extents(HPCC_DES.feed_kmolh, xi_urea, xi_biuret)
    n_in, c_in = atoms(HPCC_DES.feed_kmolh)
    n_out, c_out = atoms(out)
    assert n_out == pytest.approx(n_in, rel=1e-12)
    assert c_out == pytest.approx(c_in, rel=1e-12)
    # Only the urea step changes the mole count, by one per extent.
    assert sum(out.values()) == pytest.approx(
        sum(HPCC_DES.feed_kmolh.values()) - xi_urea, rel=1e-12)


@pytest.mark.parametrize("case", [
    dict(), dict(l_drive=3.4), dict(l_drive=2.7), dict(level_frac=0.4),
    dict(p_loop_bara=125.0), dict(p_loop_bara=160.0), dict(co2_feed_th=35.0),
    dict(t_nodes_c=[200.0, 210.0, 220.0, 230.0]),
])
def test_the_unit_conserves_every_species_it_splits(case):
    """Both composition shifts are re-partitions. Nothing is created anywhere."""
    result = run(**case)
    for k in MW_COMP:
        total = result.overflow_kmolh[k] + result.offgas_kmolh[k]
        expected = apply_reaction_extents(result.feed_corrected_kmolh, result.xi_urea,
                                          result.xi_biuret)[k]
        assert total == pytest.approx(expected, rel=1e-12, abs=1e-9)
    assert abs(result.closure_resid) < 1e-6


def test_both_composition_shifts_are_zero_at_their_own_reference():
    """Each is written on a deviation, so each vanishes where the deviation does."""
    feed = HPCC_DES.feed_kmolh
    pinned = run(l_feed_des=feed["NH3"] / feed["CO2"],
                 x_des_live=DESIGN.x_conv)
    unshifted = apply_reaction_extents(pinned.feed_corrected_kmolh, pinned.xi_urea,
                                       pinned.xi_biuret)
    theta = anchored_split(THETA_OFFGAS, unshifted, {k: 1.0 for k in MW_COMP})
    assert pinned.delta_x == 0.0
    for k in ("NH3", "CO2"):
        assert pinned.overflow_kmolh[k] == pytest.approx(
            unshifted[k] * (1.0 - theta[k]), rel=1e-12)


def test_the_calibrated_split_is_a_fixed_point_of_its_own_re_flash():
    """At the design vector and unit ratios, the re-solve returns the published split.

    Not guaranteed by the algebra — the phase ratio the splits IMPLY need not be the
    Rachford-Rice root of the K-values they back-solve to — so it is measured rather than
    assumed. It holds to 7e-16, which is what makes the design point survive the re-flash.
    """
    total = {k: OVERFLOW_DES_KMOLH.get(k, 0.0) + OFFGAS_DES_KMOLH.get(k, 0.0)
             for k in MW_COMP}
    out = anchored_split(THETA_OFFGAS, total, {k: 1.0 for k in MW_COMP})
    for k in MW_COMP:
        assert out[k] == pytest.approx(THETA_OFFGAS[k], rel=1e-14, abs=1e-15)
    for k in ("CO2", "NH3", "H2O", "Urea", "Biuret"):
        assert total[k] * (1.0 - out[k]) == pytest.approx(OVERFLOW_DES_KMOLH[k], rel=1e-12)


def test_the_analyser_shift_tracks_the_feed_ratio():
    """AT-322701 must move when the operator moves the N/C, and it is NH3-only so atoms hold."""
    lean = run(l_drive=2.80)
    rich = run(l_drive=3.40)
    assert rich.overflow_kmolh["NH3"] > lean.overflow_kmolh["NH3"]
    assert rich.offgas_kmolh["NH3"] < lean.offgas_kmolh["NH3"]
    for case in (lean, rich):
        assert case.overflow_kmolh["CO2"] + case.offgas_kmolh["CO2"] == pytest.approx(
            DESIGN.overflow_kmolh["CO2"] + DESIGN.offgas_kmolh["CO2"], rel=1e-12)


def test_conversion_slip_is_one_sided():
    """Below design, unconverted reagent leaves as gas; at or above design, nothing moves."""
    cold = run(t_nodes_c=[150.0, 152.0, 154.0, 156.0])
    assert cold.delta_x > 0.2
    assert cold.offgas_kmolh["NH3"] / cold.overflow_kmolh["NH3"] > \
        DESIGN.offgas_kmolh["NH3"] / DESIGN.overflow_kmolh["NH3"]
    over = run(x_des_live=0.30)               # a design reference the column beats easily
    assert over.delta_x == 0.0


# ======================================================================================
# Hydraulics
# ======================================================================================

def test_the_reactor_cannot_drain_below_the_funnel_lip():
    """Cut the feed, open the valve fully, and the level parks 0.7 m under normal."""
    assert weir_outflow_kgh(WEIR_CREST_M, T_BULK_DES_C, WEIR_CREST_M, WEIR_CW) == 0.0
    assert weir_outflow_kgh(WEIR_CREST_M - 1.0, T_BULK_DES_C, WEIR_CREST_M, WEIR_CW) == 0.0
    assert outlet_line_outflow_kgh(WEIR_CREST_M, OVERFLOW_DES_KGH, 100.0, HIC605_DES_PCT,
                                   WEIR_CREST_M, WEIR_CW, T_BULK_DES_C) == 0.0


def test_at_design_the_valve_sets_the_discharge_and_the_weir_has_margin():
    """The `min` picks the valve term, so the design pin is the valve's Kv ratio exactly."""
    at_design = outlet_line_outflow_kgh(
        LEVEL_NLL_PCT / 100.0 * LIQ_H_M, OVERFLOW_DES_KGH, HIC605_DES_PCT, HIC605_DES_PCT,
        WEIR_CREST_M, WEIR_CW, T_BULK_DES_C)
    assert at_design == pytest.approx(OVERFLOW_DES_KGH, rel=1e-12)
    weir_capacity = weir_outflow_kgh(LEVEL_NLL_PCT / 100.0 * LIQ_H_M, T_BULK_DES_C,
                                     WEIR_CREST_M, WEIR_CW)
    assert weir_capacity > 50.0 * OVERFLOW_DES_KGH


def test_hv322605_is_shut_at_zero_stroke():
    """The class-IV seat, not the trim line's 12 m3/h intercept."""
    assert hv322605_kv(0.0) == 0.0
    assert hv322605_kv(100.0) == 600.0
    strokes = [0.0, 5.0, 25.0, 50.0, 60.0, 75.0, 100.0]
    kvs = [hv322605_kv(s) for s in strokes]
    assert kvs == sorted(kvs)


def test_cooling_drops_the_level_at_constant_mass():
    """Thermal contraction, and the mechanism that takes a stagnant reactor under the lip."""
    hot = level_from_holdup(M_LIQ_DES_KG, T_BULK_DES_C, AREA_M2)
    cold = level_from_holdup(M_LIQ_DES_KG, 60.0, AREA_M2)
    assert melt_density(60.0) > melt_density(T_BULK_DES_C)
    assert cold < hot
    assert hot - cold == pytest.approx(hot * (1.0 - melt_density(T_BULK_DES_C)
                                              / melt_density(60.0)), rel=1e-12)


def test_wall_loss_is_off_at_design_flow_and_full_when_stagnant():
    """The gate is exactly zero at design, so the as-built profile is untouched."""
    tau_des = 743.1
    assert node_dtdt(183.0, 183.0, 0.0, tau_des, 1.0) == 0.0
    # Stagnant: the flow term is signalled away with an infinite residence time, and what is
    # left is a six-hour relaxation toward ambient.
    stagnant = node_dtdt(183.0, 170.0, 5.0, float("inf"), 0.0)
    assert stagnant == pytest.approx(-(183.0 - 40.0) / 21600.0, rel=1e-12)
    assert stagnant < 0.0


def test_the_column_takes_three_quarters_of_an_hour():
    """The number behind every complaint that the reactor is slow to respond."""
    from ureasim.data.unit_322r001 import TAU_TOT_MIN

    assert TAU_TOT_MIN == pytest.approx(44.9, abs=0.1)
    assert sum(node_liquid_volumes(ZETA_NODES, AREA_M2, LIQ_H_M, 1.0)) \
        == pytest.approx(0.868 * LIQ_H_M * AREA_M2, rel=1e-12)


# ======================================================================================
# Degenerate inputs
# ======================================================================================

def test_a_reactor_with_no_carbon_publishes_zero_conversion_rather_than_dividing():
    dry = {k: (0.0 if k == "CO2" else v) for k, v in HPCC_DES.feed_kmolh.items()}
    result = run(feed_kmolh=dry)
    assert result.x_conv == 0.0
    from ureasim.data.unit_322r001 import REACTOR_FEED_HC_DES, REACTOR_FEED_NC_DES

    assert result.l_feed == REACTOR_FEED_NC_DES
    assert result.w_feed == REACTOR_FEED_HC_DES


def test_an_empty_off_gas_line_reports_zero_partial_pressures():
    result = run(level_frac=0.0, feed_kmolh={k: 0.0 for k in MW_COMP})
    assert result.p_nh3_offgas_bara == 0.0
    assert result.p_co2_offgas_bara == 0.0
