"""322R001 against V1: the design anchors, the column march, the hydraulics and the unit.

Evidence standard
-----------------
EXECUTION, throughout. V1's `backend/reactor.py` imports cleanly — it is the one module V1
kept quarantined, with zero dependency on `main.py` — so every column and hydraulic relation
is compared against V1's own bytes directly. The unit function and every design constant come
out of `main.py` through `lift()`, which compiles and runs V1's own statements.

One thing is transcribed rather than lifted, and it is named where it happens: `main.py`
hands the jointly-solved pre-exponential to the kinetics dictionary with a SUBSCRIPT
assignment, `REACT_KIN_CAL["A2"] = _a8_a2`, which binds no name and so cannot be indexed by
the lifter. The test performs that one handoff itself. The value it assigns is lifted, and the
assertion below checks that V1's own module global already holds it, so the transcription is
verified rather than assumed.

What "bit-exact" means here
----------------------------
`==` on floats, not `approx`. Where a tolerance is used it is stated and the reason is given.
"""

from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

from tests.equivalence.v1_loader import lift, load, v1_available, v1_service

pytestmark = pytest.mark.skipif(not v1_available(), reason="V1 source tree not present")

#: Every V1 `main.py` name this suite compares against.
V1_NAMES = [
    "REACT_OVERFLOW_DES", "REACT_OFFGAS_DES", "REACT_XI_UREA_DES", "REACT_XI_BIU_DES",
    "REACT_THETA_OG", "REACT_HIC605_DES_PCT", "REACT_OVERFLOW_T_C",
    "REACT_NC_LOOP_GAIN", "REACT_OFFGAS_T_C", "REACT_P_BARA", "REACT_OFFGAS_P_BARA",
    "REACT_OVERFLOW_RHO", "REACT_OVERFLOW_RHO_DES_LIVE", "REACT_OFFGAS_RHO",
    "REACT_ID_MM", "REACT_LIQ_H_MM", "REACT_THERM_TAU_MIN", "REACT_TT_EL_MM",
    "_react_area_m2", "_react_mdot_kgh", "_react_vdot_m3h", "REACT_TAU_TOT_MIN",
    "REACT_LEVEL_NLL_PCT", "REACT_V_SPAN_M3", "REACT_BETA_DAMK",
    "REACT_NODE_TAGS", "REACT_ZETA_NODES", "REACT_TAU_NODE_MIN", "REACT_DT_COL_DES",
    "REACT_OFFGAS_GAMMA", "REACT_LIQ_H_M", "REACT_LEVEL_DES_M",
    "REACT_LT_SPAN_M", "REACT_LT_ABOVE_OVF_M", "REACT_WEIR_CREST_M",
    "REACT_FUNNEL_ID_M", "REACT_WEIR_CW", "REACT_OFFGAS_DEFICIT_GAIN",
    "REACT_PI_KAPPA", "REACT_NC_OVERFLOW_GAIN", "REACT_TAU_REC_MIN",
    "REACT_FRESH_FRAC", "REACT_FWD_GAIN", "REACT_FWD_TAU_MIN",
    "REACT_N_ATOMS", "REACT_C_ATOMS", "REACT_NC_SPAN_MAX",
    "REACT_XI_CARB_DES", "REACT_Q_COL_DES", "REACT_M_OVERFLOW_DES", "REACT_CP_MELT",
    "REACT_KIN_CAL", "_a8_a2", "_rederive_react_bulk_anchors",
    "REACT_T_BULK_DES", "REACT_RHO_BULK_DES", "REACT_M_LIQ_DES",
    "react_322r001", "_react_delta", "_anchored_split", "_hp_k_ratio",
    "_HPCC_DES", "HPCC_T_PROD_DES_C", "SYN_P_DES_BARA", "CO2_DES_KGH",
    "MW_COMP", "STRIP_FEED207_KMOLH",
]


@pytest.fixture(scope="module")
def v1r():
    """V1's `backend/reactor.py`, imported as itself."""
    return load("reactor")


@pytest.fixture(scope="module")
def v1(v1r):
    """V1 `main.py`'s 322R001 block, executed statement by statement.

    `state` is seeded with the one attribute `react_322r001` reads off the global plant
    state — the live loop pressure. In the rewrite that is an explicit argument; seeding it
    here is what lets the two be compared at all, and it is also the proof that the argument
    carries exactly what the global did.
    """
    ns = lift(V1_NAMES, seed={
        "math": math,
        "reactor": v1r,
        "jet_pump": load("jet_pump"),
        "h0_enthalpy": load("gap_g6_h0_enthalpy"),
        "thermo_service": v1_service(),
        "iapws_if97": load("iapws_if97"),
        "state": SimpleNamespace(p_syn_bara=140.7),
    })
    # The one transcribed line: `REACT_KIN_CAL["A2"] = _a8_a2`. It binds no Name, so the
    # lifter cannot index it. V1's module global already carries the same value because
    # `thermal_kinetic_fixed_point` assigned it, which the assertion verifies.
    assert v1r.A2_PRE == ns["_a8_a2"]
    ns["REACT_KIN_CAL"]["A2"] = ns["_a8_a2"]
    # V1's bulk anchors are re-solved by a bare module-level call, which is likewise not a
    # binding statement. Run it so the lifted namespace holds the values V1 runs on.
    ns["_rederive_react_bulk_anchors"]()
    return ns


# ======================================================================================
# The design constants
# ======================================================================================

def test_design_vectors(v1):
    """The two published product vectors and the split derived from them."""
    from ureasim.data.unit_322r001 import (
        OFFGAS_DES_KMOLH, OVERFLOW_DES_KGH, OVERFLOW_DES_KMOLH, THETA_OFFGAS)

    assert OVERFLOW_DES_KMOLH == v1["REACT_OVERFLOW_DES"]
    assert OFFGAS_DES_KMOLH == v1["REACT_OFFGAS_DES"]
    assert THETA_OFFGAS == v1["REACT_THETA_OG"]
    assert OVERFLOW_DES_KGH == v1["REACT_M_OVERFLOW_DES"] == v1["_react_mdot_kgh"]


def test_stream_207_is_one_object(v1):
    """The stripper's feed and the reactor's overflow are the same vector, not two copies."""
    from ureasim.data.unit_322e001 import FEED_207_KMOLH
    from ureasim.data.unit_322r001 import OVERFLOW_DES_KMOLH

    assert FEED_207_KMOLH is OVERFLOW_DES_KMOLH
    assert FEED_207_KMOLH == v1["STRIP_FEED207_KMOLH"]


@pytest.mark.parametrize("ours, theirs", [
    ("XI_UREA_DES", "REACT_XI_UREA_DES"),
    ("XI_BIURET_DES", "REACT_XI_BIU_DES"),
    ("HIC605_DES_PCT", "REACT_HIC605_DES_PCT"),
    ("OVERFLOW_T_DES_C", "REACT_OVERFLOW_T_C"),
    ("OFFGAS_T_DES_C", "REACT_OFFGAS_T_C"),
    ("OFFGAS_GAMMA", "REACT_OFFGAS_GAMMA"),
    ("P_DES_BARA", "REACT_P_BARA"),
    ("OFFGAS_P_DES_BARA", "REACT_OFFGAS_P_BARA"),
    ("OVERFLOW_RHO", "REACT_OVERFLOW_RHO"),
    ("OFFGAS_RHO", "REACT_OFFGAS_RHO"),
    ("OVERFLOW_RHO_DES_LIVE", "REACT_OVERFLOW_RHO_DES_LIVE"),
    ("VDOT_DES_M3H", "_react_vdot_m3h"),
    ("ID_MM", "REACT_ID_MM"),
    ("LIQ_H_MM", "REACT_LIQ_H_MM"),
    ("LIQ_H_M", "REACT_LIQ_H_M"),
    ("AREA_M2", "_react_area_m2"),
    ("V_SPAN_M3", "REACT_V_SPAN_M3"),
    ("TT_EL_MM", "REACT_TT_EL_MM"),
    ("NODE_TAGS", "REACT_NODE_TAGS"),
    ("ZETA_NODES", "REACT_ZETA_NODES"),
    ("TAU_TOT_MIN", "REACT_TAU_TOT_MIN"),
    ("TAU_NODE_MIN", "REACT_TAU_NODE_MIN"),
    ("THERM_TAU_MIN", "REACT_THERM_TAU_MIN"),
    ("BETA_DAMKOHLER", "REACT_BETA_DAMK"),
    ("DT_COL_DES_C", "REACT_DT_COL_DES"),
    ("LEVEL_NLL_PCT", "REACT_LEVEL_NLL_PCT"),
    ("LEVEL_DES_M", "REACT_LEVEL_DES_M"),
    ("LT_SPAN_M", "REACT_LT_SPAN_M"),
    ("LT_ABOVE_OVF_M", "REACT_LT_ABOVE_OVF_M"),
    ("WEIR_CREST_M", "REACT_WEIR_CREST_M"),
    ("FUNNEL_ID_M", "REACT_FUNNEL_ID_M"),
    ("WEIR_CW", "REACT_WEIR_CW"),
    ("NC_LOOP_GAIN", "REACT_NC_LOOP_GAIN"),
    ("NC_OVERFLOW_GAIN", "REACT_NC_OVERFLOW_GAIN"),
    ("OFFGAS_DEFICIT_GAIN", "REACT_OFFGAS_DEFICIT_GAIN"),
    ("PI_KAPPA", "REACT_PI_KAPPA"),
    ("TAU_REC_MIN", "REACT_TAU_REC_MIN"),
    ("FRESH_FRAC", "REACT_FRESH_FRAC"),
    ("FWD_GAIN", "REACT_FWD_GAIN"),
    ("FWD_TAU_MIN", "REACT_FWD_TAU_MIN"),
    ("N_ATOMS", "REACT_N_ATOMS"),
    ("C_ATOMS", "REACT_C_ATOMS"),
    ("NC_SPAN_MAX", "REACT_NC_SPAN_MAX"),
])
def test_main_constants(v1, ours, theirs):
    """Every 322R001 constant `main.py` carries, against the rewrite's data module."""
    from ureasim.data import unit_322r001 as d

    assert getattr(d, ours) == v1[theirs]


@pytest.mark.parametrize("ours, theirs", [
    ("REACTOR_FEED_NC_DES", "L0_DES"),
    ("REACTOR_FEED_HC_DES", "W0_DES"),
    ("REACTOR_T_DES_C", "T0_DES_C"),
    ("X_DES", "X_DES"),
    ("X_INF", "X_INF"),
    ("MELT_RHO_REF", "RHO_REF"),
    ("MELT_BETA_THERMAL", "BETA_THERMAL"),
    ("M_HOLDUP_MIN", "M_HOLDUP_MIN"),
    ("T_AMBIENT_C", "T_AMBIENT_C"),
    ("TAU_LOSS_S", "TAU_LOSS_S"),
    ("HV322605_KV_TABLE", "HV322605_KV_TABLE"),
])
def test_reactor_module_constants(v1r, ours, theirs):
    """Every constant V1 keeps in its quarantined `reactor.py`."""
    from ureasim.data import unit_322r001 as d

    assert getattr(d, ours) == getattr(v1r, theirs)


# ======================================================================================
# The shared chemistry
# ======================================================================================

@pytest.mark.parametrize("ours, theirs", [
    ("CARBAMATE_DH_JMOL", "DH_CARB_JMOL"),
    ("DEHYDRATION_DH_JMOL", "DH_DEHYD_JMOL"),
    ("UREA_OVERALL_DH_JMOL", "DH_OVERALL_JMOL"),
    ("DEHYDRATION_EA_JMOL", "EA_DEHYD_JMOL"),
    ("BIURET_FORMATION_EA_JMOL", "BIU_EA_JMOL"),
    ("HYDROLYSIS_B_K", "EA_HYD_REV_K"),
])
def test_chemistry_constants(v1r, ours, theirs):
    """The enthalpies and activation energies, now in one place instead of three."""
    from ureasim.thermo import kinetics as k

    assert getattr(k, ours) == getattr(v1r, theirs)


def test_fitted_gas_constant_is_v1s(v1r):
    """The ROUNDED constant the rate laws were fitted with, not the CODATA one."""
    from ureasim.thermo.parameters import R_FITTED

    assert R_FITTED == v1r.R_GAS_J == v1r.R_GAS == 8.314


@pytest.mark.parametrize("t_c", [120.0, 160.0, 183.0, 200.0, 240.0])
def test_rate_laws(v1r, v1, t_c):
    """The two rate constants and the equilibrium constant, at the calibrated parameters."""
    from ureasim.thermo.kinetics import (
        biuret_k_m3_kmol_h, dehydration_k_per_h, urea_keq_overall)

    cal = v1["REACT_KIN_CAL"]
    assert dehydration_k_per_h(t_c, cal["A2"]) == v1r.k2_dehydration(t_c)
    assert urea_keq_overall(t_c, cal["Keq_ov_ref"], cal["T_ref_K"]) == v1r.keq_overall(t_c)
    # V1 writes the biuret constant out inline rather than in a named function.
    assert biuret_k_m3_kmol_h(t_c, cal["biu_A"]) == pytest.approx(
        cal["biu_A"] * math.exp(-v1r.BIU_EA_JMOL / (v1r.R_GAS_J * (t_c + 273.15))), rel=0, abs=0)


# ======================================================================================
# The column march
# ======================================================================================

#: A spread of column states: design, a drained column, a flooded one, a cold one, a hot one.
COLUMN_CASES = [
    ([170.7, 174.9, 179.2, 183.0], 0.80, 228.46),
    ([170.7, 174.9, 179.2, 183.0], 0.30, 228.46),
    ([170.7, 174.9, 179.2, 183.0], 1.00, 228.46),
    ([150.0, 155.0, 160.0, 165.0], 0.80, 228.46),
    ([190.0, 200.0, 210.0, 220.0], 0.80, 228.46),
    ([170.7, 174.9, 179.2, 183.0], 0.80, 120.00),
    ([170.7, 174.9, 179.2, 183.0], 0.80, 400.00),
    ([170.7, 174.9, 179.2, 183.0], 0.02, 228.46),
]


@pytest.mark.parametrize("nodes, level, vdot", COLUMN_CASES)
def test_node_liquid_volumes(v1r, v1, nodes, level, vdot):
    from ureasim.units.synthesis.reactor_column import node_liquid_volumes

    assert node_liquid_volumes(v1["REACT_ZETA_NODES"], v1["_react_area_m2"],
                               v1["REACT_LIQ_H_M"], level) == \
        v1r._node_liquid_volumes(v1["REACT_ZETA_NODES"], v1["_react_area_m2"],
                                 v1["REACT_LIQ_H_M"], level)


@pytest.mark.parametrize("nodes, level, vdot", COLUMN_CASES)
def test_urea_extent_pfr(v1r, v1, nodes, level, vdot):
    """The axial march, including its per-node breakdown."""
    from ureasim.units.synthesis.reactor import KINETICS
    from ureasim.units.synthesis.reactor_column import urea_extent_pfr

    feed = v1["_HPCC_DES"]["feed_kmolh"]
    args = (feed, nodes, v1["REACT_ZETA_NODES"], v1["_react_area_m2"], v1["REACT_LIQ_H_M"],
            level, vdot)
    xi_v1, per_v1 = v1r.urea_extent_pfr(*args)
    xi, per = urea_extent_pfr(*args, KINETICS)
    assert xi == xi_v1
    assert per == per_v1


@pytest.mark.parametrize("nodes, level, vdot", COLUMN_CASES)
def test_biuret_extent(v1r, v1, nodes, level, vdot):
    from ureasim.units.synthesis.reactor import KINETICS
    from ureasim.units.synthesis.reactor_column import biuret_extent

    urea = v1["REACT_OVERFLOW_DES"]["Urea"]
    args = (nodes, v1["REACT_ZETA_NODES"], v1["_react_area_m2"], v1["REACT_LIQ_H_M"],
            level, vdot, urea)
    assert biuret_extent(*args, KINETICS) == v1r.biuret_extent(*args)


@pytest.mark.parametrize("scale", [0.0, 0.2, 1.0, 5.0])
@pytest.mark.parametrize("t_c", [150.0, 183.0, 230.0])
def test_equilibrium_extent(v1r, v1, scale, t_c):
    """The signed equilibrium extent, including the reverse branch a hot column reaches."""
    from ureasim.units.synthesis.reactor import KINETICS
    from ureasim.units.synthesis.reactor_column import equilibrium_extent
    from ureasim.thermo.kinetics import urea_keq_overall

    feed = {k: v * (1.0 if k != "Urea" else 1.0 + 400.0 * scale)
            for k, v in v1["_HPCC_DES"]["feed_kmolh"].items()}
    keq_ours = urea_keq_overall(t_c, KINETICS.keq_ov_ref, KINETICS.t_ref_k)
    assert keq_ours == v1r.keq_overall(t_c)
    assert equilibrium_extent(feed, 228.46, keq_ours) == \
        v1r._equilibrium_extent(feed, 228.46, v1r.keq_overall(t_c))


def test_carbamate_node_extents_and_heat(v1r, v1):
    from ureasim.units.synthesis.reactor_column import (
        carbamate_node_extents, node_heat_kjh, node_liquid_volumes)

    vols = node_liquid_volumes(v1["REACT_ZETA_NODES"], v1["_react_area_m2"],
                               v1["REACT_LIQ_H_M"], 0.80)
    for xi_carb in (0.0, -5.0, 291.66, 1000.0):
        carb = carbamate_node_extents(xi_carb, vols)
        assert carb == v1r.carbamate_node_extents(xi_carb, vols)
        dehyd = [60.2, 471.0, 459.6, 311.5]
        assert node_heat_kjh(carb, dehyd) == v1r.node_heat_kjh(carb, dehyd)


@pytest.mark.parametrize("zeta", [0.0, 0.04, 0.316, 0.592, 0.868, 1.0])
def test_damkohler_seed_profile(v1r, v1, zeta):
    from ureasim.units.synthesis.reactor_column import damkohler_g, node_profile_ss

    beta = v1["REACT_BETA_DAMK"]
    assert damkohler_g(zeta, beta) == v1r.damkohler_G(zeta, beta)
    assert node_profile_ss(170.0, 183.0, v1["REACT_ZETA_NODES"], beta) == \
        v1r.node_profile_ss(170.0, 183.0, v1["REACT_ZETA_NODES"], beta)


# ======================================================================================
# The two back-solves
# ======================================================================================

def test_calibration_and_fixed_point(v1, v1r):
    """Both design pins, and the profile and pre-exponential the joint solve returns.

    This is the whole import-time chain: the seed profile, the equilibrium constant, the
    biuret pre-exponential, the carbamate extent, the melt heat capacity, and then the joint
    solve. Every one of them is a float compared with `==`.
    """
    from ureasim.units.synthesis import reactor as R

    cal = v1["REACT_KIN_CAL"]
    assert R.KINETICS.a2_pre_per_h == cal["A2"] == v1["_a8_a2"]
    assert R.KINETICS.keq_ov_ref == cal["Keq_ov_ref"]
    assert R.KINETICS.t_ref_k == cal["T_ref_K"]
    assert R.KINETICS.biuret_a == cal["biu_A"]
    assert R.XI_CARBAMATE_DES == v1["REACT_XI_CARB_DES"]
    assert R.Q_COL_DES_KJH == v1["REACT_Q_COL_DES"]
    assert R.CP_MELT_KJKGK == v1["REACT_CP_MELT"]
    assert R.NODE_PROFILE_DES == v1["REACT_NODE_SS_DES"]
    assert R.FEED_T_DES_C == v1["HPCC_T_PROD_DES_C"]


def test_bulk_anchors_need_no_rederive_pass(v1):
    """The rewrite's bulk anchors equal V1's AFTER its re-derive, not before it.

    V1 computes these against the import-time SEED profile, replaces the profile twice, and
    then has to re-solve them in a separate pass — the `_rederive_react_bulk_anchors` the
    fixture calls. Solving them once, in the right order, gives the same numbers with no pass:
    the seeded holdup and the seeded profile are one design point instead of two that
    reconcile on the first tick.
    """
    from ureasim.units.synthesis import reactor as R

    assert R.T_BULK_DES_C == v1["REACT_T_BULK_DES"]
    assert R.RHO_BULK_DES == v1["REACT_RHO_BULK_DES"]
    assert R.M_LIQ_DES_KG == v1["REACT_M_LIQ_DES"]


# ======================================================================================
# The hydraulics
# ======================================================================================

@pytest.mark.parametrize("t_c", [20.0, 100.0, 176.96, 183.0, 220.0, 400.0])
def test_melt_density(v1r, t_c):
    from ureasim.units.synthesis.reactor_hydraulics import melt_density

    assert melt_density(t_c) == v1r.liquid_density(t_c)


@pytest.mark.parametrize("m_kg", [1.0, 50_000.0, 135_903.7, 200_000.0])
@pytest.mark.parametrize("t_c", [100.0, 183.0])
def test_level_from_holdup(v1r, v1, m_kg, t_c):
    from ureasim.units.synthesis.reactor_hydraulics import level_from_holdup

    assert level_from_holdup(m_kg, t_c, v1["_react_area_m2"]) == \
        v1r.level_from_holdup(m_kg, t_c, area_m2=v1["_react_area_m2"])


@pytest.mark.parametrize("flow_frac", [1.0, 0.5, 0.0, 1.0e-3])
@pytest.mark.parametrize("tau_s", [107.7, 743.1, float("inf"), 0.0])
def test_node_dtdt(v1r, flow_frac, tau_s):
    from ureasim.units.synthesis.reactor_hydraulics import node_dtdt

    assert node_dtdt(179.0, 174.0, 3.2, tau_s, flow_frac) == \
        v1r.node_dTdt(179.0, 174.0, 3.2, tau_s, flow_frac)


@pytest.mark.parametrize("level_m", [0.0, 19.0, 19.3, 19.35, 20.0, 25.0])
def test_weir_outflow(v1r, v1, level_m):
    from ureasim.units.synthesis.reactor_hydraulics import weir_outflow_kgh

    assert weir_outflow_kgh(level_m, 176.96, v1["REACT_WEIR_CREST_M"], v1["REACT_WEIR_CW"]) == \
        v1r.weir_outflow_kgph(level_m, 176.96, crest_m=v1["REACT_WEIR_CREST_M"],
                              cw=v1["REACT_WEIR_CW"])


@pytest.mark.parametrize("stroke", [-5.0, 0.0, 2.5, 5.0, 25.0, 50.0, 60.0, 75.0, 98.53,
                                    100.0, 120.0])
def test_hv322605_kv(v1r, stroke):
    from ureasim.units.synthesis.reactor_hydraulics import hv322605_kv

    assert hv322605_kv(stroke) == v1r.hv322605_kv(stroke)


@pytest.mark.parametrize("level_m", [18.0, 19.3, 19.4, 20.0, 24.0])
@pytest.mark.parametrize("stroke", [0.0, 30.0, 60.0, 100.0])
def test_outlet_line(v1r, v1, level_m, stroke):
    from ureasim.units.synthesis.reactor_hydraulics import outlet_line_outflow_kgh

    args = (level_m, v1["_react_mdot_kgh"], stroke, v1["REACT_HIC605_DES_PCT"],
            v1["REACT_WEIR_CREST_M"], v1["REACT_WEIR_CW"], 176.96)
    assert outlet_line_outflow_kgh(*args) == v1r.outlet_line_outflow_kgph(*args)


# ======================================================================================
# The anchored split
# ======================================================================================

@pytest.mark.parametrize("r_co2, r_nh3", [(1.0, 1.0), (1.4, 0.8), (0.5, 2.0), (50.0, 0.02)])
def test_anchored_split(v1, r_co2, r_nh3):
    """The Rachford-Rice re-solve, against V1's own, on the reactor's calibrated vector."""
    from ureasim.thermo.service import anchored_split

    feed = v1["_HPCC_DES"]["feed_kmolh"]
    ratio = {k: 1.0 for k in v1["MW_COMP"]}
    ratio["CO2"], ratio["NH3"] = r_co2, r_nh3
    assert anchored_split(v1["REACT_THETA_OG"], feed, ratio) == \
        v1["_anchored_split"](v1["REACT_THETA_OG"], feed, ratio)


def test_anchored_split_leaves_structural_species_alone(v1):
    """Urea, biuret and the four inerts never distribute, by arithmetic not by exception."""
    from ureasim.thermo.service import anchored_split

    ratio = {k: 3.0 for k in v1["MW_COMP"]}
    out = anchored_split(v1["REACT_THETA_OG"], v1["_HPCC_DES"]["feed_kmolh"], ratio)
    for species in ("Urea", "Biuret"):
        assert out[species] == 0.0
    for species in ("N2", "O2", "CH4", "H2"):
        assert out[species] == 1.0


# ======================================================================================
# The unit
# ======================================================================================

#: The name each `ReactorResult` field has in V1's returned dictionary.
FIELD_NAMES = {
    "overflow_kmolh": "overflow_kmolh",
    "offgas_kmolh": "offgas_kmolh",
    "feed_kmolh": "feed_kmolh",
    "feed_corrected_kmolh": "feed_corrected_kmolh",
    "xi_urea": "xi_urea",
    "xi_biuret": "xi_biu",
    "xi_carbamate": "xi_carb",
    "xi_nodes": "xi_nodes",
    "q_nodes_kjh": "q_nodes_kjh",
    "x_conv": "X_conv",
    "delta_x": "delta_X",
    "l_feed": "L_feed",
    "w_feed": "W_feed",
    "t_overflow_c": "T_overflow",
    "t_offgas_c": "T_offgas",
    "p_bara": "P_bara",
    "p_offgas_bara": "P_offgas",
    "phi": "phi",
    "phi_des": "phi_des",
    "co2_scale": "co2_scale",
    "p_nh3_offgas_bara": "p_nh3_og",
    "p_co2_offgas_bara": "p_co2_og",
    "tear_mass_kgh": "tear_mass_kgh",
    "closure_resid": "closure_resid",
}

#: Operating points: design, both ratio drives, load turndown and overload, a drained and a
#: flooded column, a cold column, a hot column, both valve extremes and a pressure excursion.
UNIT_CASES = [
    dict(),
    dict(L_drive=3.30),
    dict(L_drive=2.80),
    dict(W_drive=0.55),
    dict(co2_th=38.0),
    dict(co2_th=60.0),
    dict(level_frac=0.35),
    dict(level_frac=1.00),
    dict(t_nodes_c=[150.0, 155.0, 160.0, 165.0]),
    dict(t_nodes_c=[195.0, 205.0, 215.0, 225.0]),
    dict(hic=0.0),
    dict(hic=100.0),
    dict(p_loop=120.0),
    dict(p_loop=165.0),
    dict(vdot_m3h=140.0),
    dict(L_drive=3.30, W_drive=0.55, co2_th=45.0, level_frac=0.5, p_loop=132.0),
]


@pytest.mark.parametrize("case", UNIT_CASES)
def test_unit_matches_v1(v1, case):
    """`reactor_322r001` against V1's `react_322r001`, field by field, bit for bit."""
    from ureasim.units.synthesis.reactor import KINETICS, reactor_322r001

    hpcc = v1["_HPCC_DES"]
    co2_th = case.get("co2_th", v1["CO2_DES_KGH"] / 1000.0)
    hic = case.get("hic", v1["REACT_HIC605_DES_PCT"])
    p_loop = case.get("p_loop", v1["SYN_P_DES_BARA"])
    # The tear arguments, under each side's own spelling. The cases are written in V1's
    # names so the operating points stay readable against V1's source.
    theirs_kw = dict(L_drive=case.get("L_drive"), W_drive=case.get("W_drive"),
                     t_nodes_c=case.get("t_nodes_c"), level_frac=case.get("level_frac"),
                     vdot_m3h=case.get("vdot_m3h"))
    ours_kw = dict(l_drive=case.get("L_drive"), w_drive=case.get("W_drive"),
                   t_nodes_c=case.get("t_nodes_c"), level_frac=case.get("level_frac"),
                   vdot_m3h=case.get("vdot_m3h"))

    # V1 reads the loop pressure off the global plant state; the rewrite takes it as an
    # argument. Moving the global is what makes the two comparable.
    v1["state"].p_syn_bara = p_loop
    expected = v1["react_322r001"](hpcc, co2_th, hic, **theirs_kw)
    got = reactor_322r001(hpcc["feed_kmolh"], hpcc["gas_kmolh"]["CO2"], co2_th, hic,
                          p_loop, KINETICS, **ours_kw)

    for ours, theirs in FIELD_NAMES.items():
        assert getattr(got, ours) == expected[theirs], f"{ours} / {theirs}"


def test_unit_matches_v1_with_boot_pins(v1):
    """The same comparison with all four boot pins supplied, which is the engine's path.

    The pins are what turn this unit's output into the published PFD vectors, and none of them
    is available at import — so a design self-call cannot reproduce the design point and V1's
    cannot either. Driving both implementations with the same pins proves the arguments carry
    exactly what V1's module globals did.
    """
    from ureasim.units.synthesis.reactor import ColumnAnchor, KINETICS, reactor_322r001

    hpcc = v1["_HPCC_DES"]
    feed = hpcc["feed_kmolh"]
    mw = v1["MW_COMP"]

    # The tear V1's boot pin builds: the feed implied by the published product vectors run
    # backwards through both reactions, subtracted from the feed actually received.
    xu, xb = v1["REACT_XI_UREA_DES"], v1["REACT_XI_BIU_DES"]
    implied = {k: v1["REACT_OVERFLOW_DES"].get(k, 0.0) + v1["REACT_OFFGAS_DES"].get(k, 0.0)
               for k in mw}
    implied["CO2"] += xu
    implied["NH3"] += 2.0 * xu - xb
    implied["Urea"] += -xu + 2.0 * xb
    implied["H2O"] += -xu
    implied["Biuret"] += -xb
    tear = {k: feed.get(k, 0.0) - implied[k] for k in mw}
    l_pin = feed["NH3"] / feed["CO2"]
    x_pin = xu / feed["CO2"]
    anchor = ColumnAnchor(
        t_nodes_c=list(v1["REACT_NODE_SS_DES"]),
        level_frac=v1["REACT_LEVEL_NLL_PCT"] / 100.0,
        vdot_m3h=max(v1["REACT_M_OVERFLOW_DES"]
                     / max(v1["REACT_RHO_BULK_DES"], 1e-6), 1e-6),
        m_feed_kgh=sum(feed.get(k, 0.0) * mw[k] for k in mw))

    # `react_322r001` closes over the lifted namespace, so rebinding these four names in it
    # is exactly what V1's boot pin does to its own module globals. Restored afterwards so
    # the fixture stays the pre-pin state the other cases are written against.
    pins = {"REACT_TEAR_DES": tear, "REACT_L_FEED_DES": l_pin, "REACT_X_DES": x_pin,
            "REACT_KIN_ANCHOR": {"T_node": anchor.t_nodes_c, "lvl": anchor.level_frac,
                                 "vdot": anchor.vdot_m3h, "m_feed": anchor.m_feed_kgh}}
    v1_globals = v1["react_322r001"].__globals__
    v1_globals.update(pins)

    v1["state"].p_syn_bara = v1["SYN_P_DES_BARA"]
    expected = v1["react_322r001"](hpcc, v1["CO2_DES_KGH"] / 1000.0,
                                   v1["REACT_HIC605_DES_PCT"])
    got = reactor_322r001(feed, hpcc["gas_kmolh"]["CO2"], v1["CO2_DES_KGH"] / 1000.0,
                          v1["REACT_HIC605_DES_PCT"], v1["SYN_P_DES_BARA"], KINETICS,
                          anchor=anchor, tear_des_kmolh=tear, l_feed_des=l_pin,
                          x_des_live=x_pin)

    for key in pins:
        v1_globals[key] = None

    for ours, theirs in FIELD_NAMES.items():
        assert getattr(got, ours) == expected[theirs], f"{ours} / {theirs}"


def test_pinned_path_reproduces_the_published_carbon_and_water(v1):
    """With the pins and the calibration's own throughput, the carbon balance is the PFD's.

    This is what the four boot pins are FOR, and it is worth demonstrating rather than
    asserting in a comment: remove the recycle tear, anchor the analyser shift on the feed
    the plant actually runs, anchor the deficit slip on the conversion it actually achieves,
    and the reactor's two product streams come back as the published stream table.

    Exactly for CO2 and H2O; see `test_biuret_is_calibrated_at_the_superseded_profile` in the
    unit suite for why nitrogen and the two organics are 0.3 kmol/h out. The throughput is
    given explicitly as the calibration's own, because the anchor's is on a different density
    basis — also measured in the unit suite.
    """
    from ureasim.data.unit_322r001 import VDOT_DES_M3H
    from ureasim.units.synthesis.reactor import KINETICS, reactor_322r001

    hpcc = v1["_HPCC_DES"]
    feed = hpcc["feed_kmolh"]
    mw = v1["MW_COMP"]
    xu, xb = v1["REACT_XI_UREA_DES"], v1["REACT_XI_BIU_DES"]
    implied = {k: v1["REACT_OVERFLOW_DES"].get(k, 0.0) + v1["REACT_OFFGAS_DES"].get(k, 0.0)
               for k in mw}
    implied["CO2"] += xu
    implied["NH3"] += 2.0 * xu - xb
    implied["Urea"] += -xu + 2.0 * xb
    implied["H2O"] += -xu
    implied["Biuret"] += -xb
    tear = {k: feed.get(k, 0.0) - implied[k] for k in mw}

    got = reactor_322r001(
        feed, hpcc["gas_kmolh"]["CO2"], v1["CO2_DES_KGH"] / 1000.0,
        v1["REACT_HIC605_DES_PCT"], v1["SYN_P_DES_BARA"], KINETICS,
        vdot_m3h=VDOT_DES_M3H, tear_des_kmolh=tear,
        l_feed_des=feed["NH3"] / feed["CO2"], x_des_live=xu / feed["CO2"])

    # The urea extent is the PFD's to the last bit — that is what A2 was solved for.
    assert got.xi_urea == v1["REACT_XI_UREA_DES"]
    # Neither composition shift contributes: both are written on deviations that are zero.
    assert got.delta_x == 0.0
    assert got.l_feed == feed["NH3"] / feed["CO2"]
    for k in ("CO2", "H2O"):
        assert got.overflow_kmolh[k] == pytest.approx(
            v1["REACT_OVERFLOW_DES"][k], rel=1e-12, abs=1e-9)
        assert got.offgas_kmolh[k] == pytest.approx(
            v1["REACT_OFFGAS_DES"][k], rel=1e-12, abs=1e-9)
    # Nitrogen closes to the biuret shortfall, which is one reaction the pins do not cover.
    biuret_short = v1["REACT_XI_BIU_DES"] - got.xi_biuret
    assert got.overflow_kmolh["Biuret"] == pytest.approx(
        v1["REACT_OVERFLOW_DES"]["Biuret"] - biuret_short, rel=1e-12)
    assert got.overflow_kmolh["Urea"] == pytest.approx(
        v1["REACT_OVERFLOW_DES"]["Urea"] + 2.0 * biuret_short, rel=1e-9)


def test_reaction_stoichiometry(v1):
    """`apply_reaction_extents` against V1's `_react_delta`."""
    from ureasim.units.synthesis.reactor import apply_reaction_extents

    feed = v1["_HPCC_DES"]["feed_kmolh"]
    for xu, xb in ((0.0, 0.0), (1302.27, 2.414), (-50.0, 10.0), (2000.0, 0.0)):
        assert apply_reaction_extents(feed, xu, xb) == v1["_react_delta"](feed, xu, xb)
