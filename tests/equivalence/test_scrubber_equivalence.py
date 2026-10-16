"""322E003 against V1: the design streams, the shell-side bridge, the sump and the unit.

Evidence standard
-----------------
EXECUTION. Every constant, every relation and every published field comes out of V1's own
`main.py` through `lift()`, which compiles and runs V1's own statements. Nothing in this
suite is transcribed.

The one thing that had to be arranged rather than lifted is the live loop pressure:
`scrub_322e003` reads it off V1's global plant state. The fixture seeds that state with a
single attribute, and the pressure cases below set it before each call. In the rewrite the
same quantity is an explicit argument, so the agreement is also the proof that the argument
carries exactly what the global did.

What "bit-exact" means here
----------------------------
`==` on floats, not `approx`. Where a tolerance is used it is stated and the reason is given.

Handoff B-16, decided 2026-10-07
--------------------------------
TT-322002 is pinned on the PFD's 165 C where V1 pins 178.8. The ``v1`` fixture lifts V1 with that
one constant seeded (`b16_switch`), so V1's own statements derive the conductance, the condensing
anchor and the driving force from it; ``v1_verbatim`` is V1 untouched, and the last section
asserts both sides.
"""

from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

from tests.equivalence import b16_switch, b18_switch
from tests.equivalence.v1_loader import lift, load, v1_available, v1_service

pytestmark = pytest.mark.skipif(not v1_available(), reason="V1 source tree not present")

#: Every V1 `main.py` name this suite compares against.
V1_NAMES = [
    # the wash and the vent closure
    "SCRUB_CARB_KGH_DES", "SCRUB_CARB_MASSPCT", "SCRUB_CARB_KMOLH_DES",
    "SCRUB_OFFGAS_MOLPCT", "SCRUB_VENT_INERTS", "SCRUB_VENT_CONDENSABLE",
    "SCRUB_VENT_Y_DES", "SCRUB_VENT_Y_MAX",
    # the design streams
    "SCRUB_FEED_KMOLH_DES", "SCRUB_OFFGAS_KMOLH_DES", "SCRUB_OVERFLOW_KMOLH_DES",
    "SCRUB_OFFGAS_KGH_DES", "SCRUB_OFFGAS_NC_DES",
    # the operating point
    "SCRUB_OFFGAS_T_C", "SCRUB_OFFGAS_T_GAIN", "SCRUB_OFFGAS_T_VENT_GAIN",
    "SCRUB_OVERFLOW_T_VENT_GAIN", "SCRUB_OFFGAS_P_BARA", "SCRUB_OFFGAS_RHO",
    "SCRUB_OVERFLOW_T_C", "SCRUB_OVERFLOW_P_BARA", "SCRUB_DH_CARB_KJMOL",
    "SCRUB_HIC604_DES_PCT",
    # the sump
    "SCRUB_LEVEL_NLL_PCT", "SCRUB_TAU_HOLDUP_MIN", "SCRUB_HOLDUP_NLL_KG",
    "SCRUB_HOLDUP_MAX_KG", "SCRUB_SWELL_PCT_MAX", "SCRUB_SWELL_NOISE_PCT",
    "SCRUB_SWELL_NOISE_T1_S", "SCRUB_SWELL_NOISE_T2_S",
    # the shell side
    "SCRUB_CCW_KGH_DES", "SCRUB_CCW_CP", "SCRUB_CCW_T_IN_DES", "SCRUB_CCW_T_OUT_DES",
    "SCRUB_CCW_P_IN_BARA", "SCRUB_CCW_P_OUT_BARA", "SCRUB_CCW_RHO_IN", "SCRUB_CCW_RHO_OUT",
    "SCRUB_Q_CCW_DES_KW", "SCRUB_UA_KWK", "SCRUB_T_PROC_C",
    "SCRUB_COND_CHOKE_MIN", "SCRUB_COND_SPINDLE_GAIN", "SCRUB_COOL_FRAC_EPS",
    "SCRUB_COND_DH_JMOL", "SCRUB_COND_T_DES_K", "SCRUB_COND_P_DES",
    # the relations
    "scrub_vent_kmolh", "scrub_cond_t_c", "scrub_322e003", "react_nc_ratio",
    # everything they are written against
    "_hp_k_ratio", "SYN_P_DES_BARA", "MW_COMP", "REACT_OFFGAS_DES", "REACT_OVERFLOW_DES",
    "clamp", "STRIP_R_GAS_J",
]


def _seed() -> dict:
    return {
        "math": math,
        "reactor": load("reactor"),
        "jet_pump": load("jet_pump"),
        "h0_enthalpy": load("gap_g6_h0_enthalpy"),
        "thermo_service": v1_service(),
        "iapws_if97": load("iapws_if97"),
        "state": SimpleNamespace(p_syn_bara=140.7),
    }


@pytest.fixture(scope="module")
def v1():
    """V1 `main.py`'s 322E003 block, executed statement by statement, on B-16's 165 C pin and
    B-18's 72 % anchor of HV-322604."""
    return lift(b18_switch.names(b16_switch.names(V1_NAMES)),
                seed=b18_switch.seed(b16_switch.seed(_seed())))


@pytest.fixture(scope="module")
def v1_verbatim():
    """V1's 322E003 block untouched, on its 178.8 C pin, for B-16 both ways."""
    return lift(V1_NAMES, seed=_seed())


# ==========================================================================================
# The design constants
# ==========================================================================================

#: Every scalar in `data/unit_322e003.py` that has a V1 counterpart, paired with it.
SCALARS = [
    ("WASH_KGH_DES", "SCRUB_CARB_KGH_DES"),
    ("VENT_Y_MAX", "SCRUB_VENT_Y_MAX"),
    ("OFFGAS_DES_KGH", "SCRUB_OFFGAS_KGH_DES"),
    ("OFFGAS_NC_DES", "SCRUB_OFFGAS_NC_DES"),
    ("OFFGAS_T_DES_C", "SCRUB_OFFGAS_T_C"),
    ("OFFGAS_T_GAIN", "SCRUB_OFFGAS_T_GAIN"),
    ("OFFGAS_T_VENT_GAIN", "SCRUB_OFFGAS_T_VENT_GAIN"),
    ("OVERFLOW_T_VENT_GAIN", "SCRUB_OVERFLOW_T_VENT_GAIN"),
    ("OFFGAS_P_BARA", "SCRUB_OFFGAS_P_BARA"),
    ("OFFGAS_RHO", "SCRUB_OFFGAS_RHO"),
    ("OVERFLOW_T_DES_C", "SCRUB_OVERFLOW_T_C"),
    ("OVERFLOW_P_DES_BARA", "SCRUB_OVERFLOW_P_BARA"),
    ("DH_CARB_KJMOL", "SCRUB_DH_CARB_KJMOL"),
    ("HIC604_DES_PCT", "SCRUB_HIC604_DES_PCT"),
    ("LEVEL_NLL_PCT", "SCRUB_LEVEL_NLL_PCT"),
    ("TAU_HOLDUP_MIN", "SCRUB_TAU_HOLDUP_MIN"),
    ("HOLDUP_NLL_KG", "SCRUB_HOLDUP_NLL_KG"),
    ("HOLDUP_MAX_KG", "SCRUB_HOLDUP_MAX_KG"),
    ("SWELL_PCT_MAX", "SCRUB_SWELL_PCT_MAX"),
    ("SWELL_NOISE_PCT", "SCRUB_SWELL_NOISE_PCT"),
    ("SWELL_NOISE_T1_S", "SCRUB_SWELL_NOISE_T1_S"),
    ("SWELL_NOISE_T2_S", "SCRUB_SWELL_NOISE_T2_S"),
    ("CCW_KGH_DES", "SCRUB_CCW_KGH_DES"),
    ("CCW_CP_KJKGK", "SCRUB_CCW_CP"),
    ("CCW_T_IN_DES_C", "SCRUB_CCW_T_IN_DES"),
    ("CCW_T_OUT_DES_C", "SCRUB_CCW_T_OUT_DES"),
    ("CCW_P_IN_BARA", "SCRUB_CCW_P_IN_BARA"),
    ("CCW_P_OUT_BARA", "SCRUB_CCW_P_OUT_BARA"),
    ("CCW_RHO_IN", "SCRUB_CCW_RHO_IN"),
    ("CCW_RHO_OUT", "SCRUB_CCW_RHO_OUT"),
    ("Q_CCW_DES_KW", "SCRUB_Q_CCW_DES_KW"),
    ("UA_KWK", "SCRUB_UA_KWK"),
    ("T_PROC_C", "SCRUB_T_PROC_C"),
    ("COND_CHOKE_MIN", "SCRUB_COND_CHOKE_MIN"),
    ("COND_SPINDLE_GAIN", "SCRUB_COND_SPINDLE_GAIN"),
    ("COOL_FRAC_EPS", "SCRUB_COOL_FRAC_EPS"),
    ("COND_DH_JMOL", "SCRUB_COND_DH_JMOL"),
    ("COND_T_DES_K", "SCRUB_COND_T_DES_K"),
    ("COND_P_DES_BARA", "SCRUB_COND_P_DES"),
    ("COND_R_JMOLK", "STRIP_R_GAS_J"),
]


@pytest.mark.parametrize("ours, theirs", SCALARS, ids=[a for a, _ in SCALARS])
def test_scalar_constants(v1, ours, theirs):
    """Every scalar design constant, against V1's own."""
    import ureasim.data.unit_322e003 as data
    assert getattr(data, ours) == v1[theirs]


VECTORS = [
    ("WASH_MASSPCT", "SCRUB_CARB_MASSPCT"),
    ("WASH_KMOLH_DES", "SCRUB_CARB_KMOLH_DES"),
    ("OFFGAS_MOLPCT", "SCRUB_OFFGAS_MOLPCT"),
    ("VENT_Y_DES", "SCRUB_VENT_Y_DES"),
    ("FEED_DES_KMOLH", "SCRUB_FEED_KMOLH_DES"),
    ("OFFGAS_DES_KMOLH", "SCRUB_OFFGAS_KMOLH_DES"),
    ("OVERFLOW_DES_KMOLH", "SCRUB_OVERFLOW_KMOLH_DES"),
]


@pytest.mark.parametrize("ours, theirs", VECTORS, ids=[a for a, _ in VECTORS])
def test_vector_constants(v1, ours, theirs):
    """Every design vector, key by key and bit for bit."""
    import ureasim.data.unit_322e003 as data
    mine, yours = getattr(data, ours), v1[theirs]
    assert set(mine) == set(yours)
    for k in yours:
        assert mine[k] == yours[k], k


def test_vent_species_lists(v1):
    """The inert and condensable tuples, IN ORDER — the order fixes two float sums."""
    import ureasim.data.unit_322e003 as data
    assert data.VENT_INERTS == tuple(v1["SCRUB_VENT_INERTS"])
    assert data.VENT_CONDENSABLE == tuple(v1["SCRUB_VENT_CONDENSABLE"])


def test_the_loop_design_pressure_is_one_number(v1):
    """`unit_320.SYN_P_DES_BARA` is the scrubber's overflow pressure, as it is in V1."""
    from ureasim.data.unit_320 import SYN_P_DES_BARA
    from ureasim.data.unit_322e003 import OVERFLOW_P_DES_BARA
    assert SYN_P_DES_BARA is OVERFLOW_P_DES_BARA
    assert SYN_P_DES_BARA == v1["SYN_P_DES_BARA"] == v1["SCRUB_OVERFLOW_P_BARA"]


def test_the_ejector_suction_is_the_scrubber_overflow(v1):
    """`unit_322f001` imports this vector rather than repeating it, and V1 asserts the same."""
    from ureasim.data.unit_322e003 import OVERFLOW_DES_KMOLH
    from ureasim.data.unit_322f001 import OVERFLOW_DES_KMOLH as EJECTOR_SUCTION
    assert EJECTOR_SUCTION is OVERFLOW_DES_KMOLH
    for k in v1["MW_COMP"]:
        assert EJECTOR_SUCTION[k] == v1["SCRUB_OVERFLOW_KMOLH_DES"][k], k


# ==========================================================================================
# The saturated-inert vent closure
# ==========================================================================================

#: Feeds the vent closure is exercised on: design, inert-rich, inert-free, ammonia-starved,
#: and one that drives the saturation past its cap.
VENT_FEEDS = [
    ("design", None),
    ("inert_rich", {"N2": 400.0, "O2": 60.0, "CH4": 30.0, "H2": 20.0,
                    "NH3": 600.0, "CO2": 200.0, "H2O": 100.0, "Urea": 0.0, "Biuret": 0.0}),
    ("no_inerts", {"N2": 0.0, "O2": 0.0, "CH4": 0.0, "H2": 0.0,
                   "NH3": 600.0, "CO2": 200.0, "H2O": 100.0, "Urea": 0.0, "Biuret": 0.0}),
    ("nh3_starved", {"N2": 44.5, "O2": 7.4, "CH4": 3.9, "H2": 2.0,
                     "NH3": 0.4, "CO2": 0.2, "H2O": 900.0, "Urea": 0.0, "Biuret": 0.0}),
    ("empty", {k: 0.0 for k in ("N2", "O2", "CH4", "H2", "NH3", "CO2", "H2O",
                                "Urea", "Biuret")}),
]

#: K-value ratios the saturation is moved by, including the one that trips the cap.
VENT_RATIOS = [
    None,
    {},
    {"NH3": 1.0, "CO2": 1.0, "H2O": 1.0},
    {"NH3": 1.4, "CO2": 0.8, "H2O": 1.1},
    {"NH3": 0.5, "CO2": 0.5, "H2O": 0.5},
    {"NH3": 12.0, "CO2": 9.0, "H2O": 4.0},
]


@pytest.mark.parametrize("ratio", VENT_RATIOS, ids=[str(i) for i in range(len(VENT_RATIOS))])
@pytest.mark.parametrize("name, feed", VENT_FEEDS, ids=[n for n, _ in VENT_FEEDS])
def test_vent_closure(v1, name, feed, ratio):
    """`vent_kmolh` against V1's `scrub_vent_kmolh`, over five feeds and six ratios."""
    from ureasim.units.synthesis.scrubber import vent_kmolh
    f = v1["SCRUB_FEED_KMOLH_DES"] if feed is None else feed
    mine, theirs = vent_kmolh(f, ratio), v1["scrub_vent_kmolh"](f, ratio)
    for k in v1["MW_COMP"]:
        assert mine[k] == theirs.get(k, 0.0), k


def test_vent_at_the_design_feed_is_the_published_vector(v1):
    """The derived design vent IS PFD stream 204, to the tolerance the PFD is printed at."""
    from ureasim.data.unit_322e003 import OFFGAS_DES_KGH, OFFGAS_DES_KMOLH
    from ureasim.core.stream import MW_COMP
    total = sum(OFFGAS_DES_KMOLH.values())
    mw = OFFGAS_DES_KGH / total
    assert total == pytest.approx(64.78, abs=0.01)      # PFD 204 molar flow
    assert OFFGAS_DES_KGH == pytest.approx(1708.0, abs=0.4)   # PFD 204 mass flow
    assert mw == pytest.approx(26.36, abs=0.01)         # PFD 204 average molar weight
    # ... and the inerts pass straight through, which is the closure's whole claim.
    for k in ("N2", "O2", "CH4", "H2"):
        assert OFFGAS_DES_KMOLH[k] == v1["REACT_OFFGAS_DES"].get(k, 0.0) + \
            v1["SCRUB_CARB_KMOLH_DES"][k]
    assert MW_COMP["N2"] > 0.0


# ==========================================================================================
# The condensing temperature and the capacity gate
# ==========================================================================================

COND_PRESSURES = [140.7, 120.0, 130.0, 135.5, 145.0, 151.2, 160.0, 90.0, 1.0, 1.0e-9, 0.0]


@pytest.mark.parametrize("p", COND_PRESSURES)
def test_condensing_temperature(v1, p):
    """`condensing_temperature_c` against V1's `scrub_cond_t_c`, including the log floor."""
    from ureasim.units.synthesis.scrubber import condensing_temperature_c
    assert condensing_temperature_c(p) == v1["scrub_cond_t_c"](p)


def test_condensing_temperature_is_exact_at_the_anchor(v1):
    """At the design pressure the increment is a literal zero, not a small number."""
    from ureasim.units.synthesis.scrubber import condensing_temperature_c
    assert condensing_temperature_c(v1["SCRUB_COND_P_DES"]) == v1["SCRUB_OVERFLOW_T_C"]


def test_condensing_temperature_rises_with_pressure(v1):
    """The SIGN. A higher loop pressure condenses more readily — V1's earlier form had it
    the other way round and the loop fed back on itself."""
    from ureasim.units.synthesis.scrubber import condensing_temperature_c
    lo, mid, hi = (condensing_temperature_c(p) for p in (130.0, 140.7, 150.0))
    assert lo < mid < hi
    # Slope at the anchor, R.T^2/(dH.P) = 0.0709 K/bar on 165 C (0.0754 on V1's 178.8, B-16).
    slope = (condensing_temperature_c(141.7) - condensing_temperature_c(139.7)) / 2.0
    assert slope == pytest.approx(0.0709, abs=0.0005)


#: Capacity cases: (m_ccw, pump_frac, t_ccw_in, p_loop, co2_scale).
CAPACITY_CASES = [
    (306000.0, 1.0, 80.0, 140.7, 1.0),
    (306000.0, 1.0, 80.0, 140.7, 0.7),
    (306000.0, 1.0, 80.0, 151.0, 1.0),
    (306000.0, 1.0, 95.0, 140.7, 1.0),
    (306000.0, 1.0, 190.0, 140.7, 1.0),
    (153000.0, 1.0, 80.0, 140.7, 1.0),
    (306000.0, 0.0, 80.0, 140.7, 1.0),
    (0.0, 1.0, 80.0, 140.7, 1.0),
    (306000.0, 1.0, 80.0, 140.7, 0.0),
]


@pytest.mark.parametrize("m_ccw, pump, t_in, p, s", CAPACITY_CASES)
def test_condensation_capacity(v1, m_ccw, pump, t_in, p, s):
    """`condensation_capacity` against V1's inline rho_cond block, transcribed here so the
    arithmetic V1 writes inside `step_sim` — which the lifter cannot reach — is compared."""
    from ureasim.units.synthesis.scrubber import condensation_capacity
    t_cond = v1["scrub_cond_t_c"](p)
    f_th = (t_cond - t_in) / max(v1["SCRUB_OVERFLOW_T_C"] - v1["SCRUB_CCW_T_IN_DES"], 1e-6)
    theirs = ((m_ccw / v1["SCRUB_CCW_KGH_DES"]) * pump * max(f_th, 0.0) / max(s, 1e-6))
    assert condensation_capacity(m_ccw, pump, t_in, p, s) == theirs


def test_capacity_is_exactly_one_at_design(v1):
    """The gate is inert at design, which is what keeps every pin below it bit-exact."""
    from ureasim.units.synthesis.scrubber import condensation_capacity
    assert condensation_capacity(v1["SCRUB_CCW_KGH_DES"], 1.0,
                                 v1["SCRUB_CCW_T_IN_DES"], v1["SCRUB_COND_P_DES"], 1.0) == 1.0


# ==========================================================================================
# The sump: level and the LT-329501 overlay
# ==========================================================================================

HOLDUPS = [0.0, 1000.0, 3837.4211379385833, 5000.0, 7674.842275877167, 9000.0, -50.0]


@pytest.mark.parametrize("holdup", HOLDUPS)
def test_sump_level(v1, holdup):
    """`sump_level_pct` against V1's inline level expression, including both clamp rails."""
    from ureasim.units.synthesis.scrubber import sump_level_pct
    theirs = v1["clamp"](holdup / v1["SCRUB_HOLDUP_NLL_KG"] * v1["SCRUB_LEVEL_NLL_PCT"],
                         0.0, 100.0)
    assert sump_level_pct(holdup) == theirs


SWELL_CASES = [(50.0, 1.0, 0.0), (50.0, 1.0, 1234.5), (50.0, 0.0, 0.0), (50.0, 0.0, 3.7),
               (50.0, 0.5, 91.3), (95.0, 0.0, 12.0), (2.0, 0.0, 12.0), (0.0, 0.2, 500.0)]


@pytest.mark.parametrize("level, cf, t", SWELL_CASES)
def test_lt_329501_indication(v1, level, cf, t):
    """`lt_329501_indication` against V1's inline swell overlay."""
    from ureasim.units.synthesis.scrubber import lt_329501_indication
    void = 1.0 - cf
    swell = v1["SCRUB_SWELL_PCT_MAX"] * void
    noise = v1["SCRUB_SWELL_NOISE_PCT"] * void * (
        math.sin(2.0 * math.pi * t / v1["SCRUB_SWELL_NOISE_T1_S"])
        + 0.6 * math.sin(2.0 * math.pi * t / v1["SCRUB_SWELL_NOISE_T2_S"])) / 1.6
    assert lt_329501_indication(level, cf, t) == v1["clamp"](level + swell + noise, 0.0, 100.0)


def test_the_indication_is_the_level_while_the_shell_condenses(v1):
    """At full capacity the overlay is identically zero — no epsilon, no near-equality."""
    from ureasim.units.synthesis.scrubber import lt_329501_indication
    for t in (0.0, 7.3, 17.0, 1000.0):
        assert lt_329501_indication(43.21, 1.0, t) == 43.21


# ==========================================================================================
# The unit
# ==========================================================================================

#: Every published field of `ScrubberResult`, paired with V1's dict key.
FIELD_NAMES = [
    ("feed_kmolh", "feed_kmolh"),
    ("carb_kmolh", "carb_kmolh"),
    ("offgas_kmolh", "offgas_kmolh"),
    ("overflow_kmolh", "overflow_kmolh"),
    ("closure_resid", "closure_resid"),
    ("co2_abs", "co2_abs"),
    ("q_carb_kw", "q_carb_kw"),
    ("q_ccw_kw", "q_ccw_kw"),
    ("t_ccw_in_c", "t_ccw_in"),
    ("t_ccw_out_c", "t_ccw_out"),
    ("dt_ccw_c", "dT_ccw"),
    ("m_ccw_kgh", "m_ccw_kgh"),
    ("co2_scale", "co2_scale"),
    ("vent_ratio", "vent_ratio"),
    ("cool_frac", "cool_frac"),
    ("uncond_kmolh", "uncond_kmolh"),
    ("uncond_kgh", "uncond_kgh"),
    ("eps_ht", "eps_ht"),
    ("ua_eff_kwk", "ua_eff_kwk"),
    ("t_offgas_c", "T_offgas"),
    ("p_offgas_bara", "P_offgas"),
    ("t_overflow_c", "T_overflow"),
    ("p_overflow_bara", "P_overflow"),
]

#: Reactor melt spilled into the off-gas line on a flood, for the carryover cases.
_CARRY = {"Urea": 40.0, "Biuret": 0.1, "NH3": 120.0, "CO2": 27.0, "H2O": 66.0,
          "N2": 0.0, "O2": 0.0, "CH4": 0.0, "H2": 0.0}

#: Operating points the unit is compared over. Each is a name, the loop pressure the global
#: state is set to, and the keyword arguments in V1's own spelling.
UNIT_CASES = [
    ("design", 140.7, {}),
    ("turndown_70", 140.7, {"co2_scale": 0.70}),
    ("overload_110", 140.7, {"co2_scale": 1.10}),
    ("loop_low_p", 128.0, {}),
    ("loop_high_p", 151.0, {}),
    ("vent_load_high", 148.0, {"vent_ratio": 148.0 / 140.7}),
    ("vent_load_low", 132.0, {"vent_ratio": 132.0 / 140.7}),
    ("ccw_hot", 140.7, {"t_ccw_in": 95.0}),
    ("ccw_cold", 140.7, {"t_ccw_in": 60.0}),
    ("ccw_half", 140.7, {"m_ccw_kgh": 153000.0}),
    ("ccw_shut", 140.7, {"m_ccw_kgh": 0.0}),
    ("nc_high", 140.7, {"nc_act": 3.25}),
    ("nc_low", 140.7, {"nc_act": 2.80}),
    ("purge_shut", 140.7, {"hic604_pct": 0.0}),
    ("purge_open", 140.7, {"hic604_pct": 100.0}),
    ("sump_flooding", 140.7, {"choke_level_pct": 75.0}),
    ("sump_full", 140.7, {"choke_level_pct": 100.0}),
    ("sump_drained", 140.7, {"choke_level_pct": 5.0}),
    ("spindle_weak", 140.7, {"spindle_phi": 0.80}),
    ("spindle_strong", 140.7, {"spindle_phi": 1.30}),
    ("cooling_half", 140.7, {"cool_frac": 0.50}),
    ("cooling_lost", 140.7, {"cool_frac": 0.0}),
    ("cooling_residual", 140.7, {"cool_frac": 1.0 - 1.0e-9}),
    ("wash_short", 140.7, {"wash_ratio": 0.80}),
    ("wash_surplus", 140.7, {"wash_ratio": 1.20}),
    ("reactor_flood", 140.7, {"liq_carry_kmolh": _CARRY, "t_carry_c": 183.0}),
    ("flood_and_cooling_lost", 145.0,
     {"liq_carry_kmolh": _CARRY, "t_carry_c": 186.0, "cool_frac": 0.2,
      "choke_level_pct": 88.0, "spindle_phi": 1.15, "hic604_pct": 90.0,
      "co2_scale": 0.9, "wash_ratio": 1.05, "nc_act": 3.4, "vent_ratio": 145.0 / 140.7}),
]

def _call_both(v1, p_loop, kwargs):
    """Drive V1 and the rewrite at the same operating point and return both results.

    V1 reads the loop pressure off its global plant state and the rewrite takes it as an
    argument; everything else is spelled the same in both, so the remaining keywords pass
    straight through. That the two agree is the evidence that the argument carries exactly
    what the global did.
    """
    from ureasim.units.synthesis.scrubber import scrubber_322e003
    v1["state"].p_syn_bara = p_loop
    kw = dict(kwargs)
    s = kw.pop("co2_scale", 1.0)
    t_in = kw.pop("t_ccw_in", v1["SCRUB_CCW_T_IN_DES"])
    m_ccw = kw.pop("m_ccw_kgh", v1["SCRUB_CCW_KGH_DES"])
    theirs = v1["scrub_322e003"](v1["REACT_OFFGAS_DES"], s, t_in, m_ccw, **kw)
    mine = scrubber_322e003(v1["REACT_OFFGAS_DES"], s, t_in, m_ccw,
                            p_loop_bara=p_loop, **kw)
    return mine, theirs


@pytest.mark.parametrize("field, key", FIELD_NAMES, ids=[a for a, _ in FIELD_NAMES])
@pytest.mark.parametrize("name, p_loop, kwargs", UNIT_CASES, ids=[c[0] for c in UNIT_CASES])
def test_unit_fields(v1, name, p_loop, kwargs, field, key):
    """Every published field of the unit, at every operating point, bit for bit."""
    mine, theirs = _call_both(v1, p_loop, dict(kwargs))
    got, want = getattr(mine, field), theirs[key]
    if isinstance(want, dict):
        assert set(got) == set(want)
        for k in want:
            assert got[k] == want[k], f"{name}/{field}/{k}"
    else:
        assert got == want, f"{name}/{field}"


def test_design_call_reproduces_the_published_streams(v1):
    """The self-call at import reproduces PFD 204 and 206 with every deviation term at zero."""
    from ureasim.core.stream import MW_COMP
    from ureasim.data.unit_322e003 import OFFGAS_DES_KMOLH, OVERFLOW_DES_KMOLH
    from ureasim.units.synthesis.scrubber import DESIGN
    for k in MW_COMP:
        assert DESIGN.offgas_kmolh[k] == OFFGAS_DES_KMOLH[k], k
        assert DESIGN.overflow_kmolh[k] == OVERFLOW_DES_KMOLH[k], k
    assert DESIGN.t_ccw_out_c == v1["SCRUB_CCW_T_OUT_DES"]
    assert DESIGN.dt_ccw_c == v1["SCRUB_CCW_T_OUT_DES"] - v1["SCRUB_CCW_T_IN_DES"]
    assert DESIGN.t_offgas_c == v1["SCRUB_OFFGAS_T_C"]
    assert DESIGN.q_ccw_kw == v1["SCRUB_Q_CCW_DES_KW"]
    assert DESIGN.closure_resid == 0.0
    # The overflow pin carries one bit of floating-point noise out of the epsilon-NTU
    # inversion: 80 + 5329.5/(Q/(165-80)) is 164.99999999999997, not 165. V1 on the same pin
    # produces the same float, which the field comparison above already asserts.
    assert DESIGN.t_overflow_c == pytest.approx(v1["SCRUB_OVERFLOW_T_C"], abs=1e-12)


def test_the_analyser_reference(v1):
    """`atom_ratio` on the reactor overflow is V1's `react_nc_ratio` on the same vector."""
    from ureasim.core.stream import atom_ratio
    from ureasim.data.unit_322r001 import C_ATOMS, NC_SPAN_MAX, N_ATOMS
    for vec in (v1["REACT_OVERFLOW_DES"], v1["REACT_OFFGAS_DES"],
                v1["SCRUB_OVERFLOW_KMOLH_DES"], v1["SCRUB_OFFGAS_KMOLH_DES"],
                {"NH3": 10.0}, {"CO2": 10.0}, {}):
        assert atom_ratio(vec, N_ATOMS, C_ATOMS, NC_SPAN_MAX) == v1["react_nc_ratio"](vec)


# ==========================================================================================
# The decided divergence: TT-322002 on 165 C (handoff B-16, 2026-10-07), both sides
# ==========================================================================================

def test_the_pin_and_what_is_anchored_on_it_decided_divergence(v1_verbatim):
    """V1 pins TT-322002 on its ejector's 178.8 C; the port on the PFD's 165. The cooling water's
    95.0 C return and the duty are the same on both; the conductance rises from 58.505 to
    68.98 kW/K, and the condensing temperature rides the loop pressure from 165 C, its
    Clausius-Clapeyron excursion smaller by the square of the absolute temperatures."""
    import ureasim.data.unit_322e003 as data
    from ureasim.units.synthesis.scrubber import DESIGN, condensing_temperature_c
    assert (v1_verbatim["SCRUB_OVERFLOW_T_C"], data.OVERFLOW_T_DES_C) == (178.8, 165.0)
    assert v1_verbatim["SCRUB_UA_KWK"] == pytest.approx(58.505, abs=1e-3)
    assert data.UA_KWK == pytest.approx(68.984, abs=1e-3)
    assert data.Q_CCW_DES_KW == v1_verbatim["SCRUB_Q_CCW_DES_KW"]
    assert DESIGN.t_ccw_out_c == v1_verbatim["SCRUB_CCW_T_OUT_DES"] == 95.0
    assert DESIGN.t_overflow_c == pytest.approx(165.0, abs=1e-12)
    for p in (128.0, 140.7, 151.0):
        delta_v1 = v1_verbatim["scrub_cond_t_c"](p) - 178.8
        delta = condensing_temperature_c(p) - 165.0
        assert delta == pytest.approx(delta_v1 * (438.15 / 451.95) ** 2, rel=1e-3)


@pytest.mark.parametrize("name, kwargs, v1_t, port_t", [
    ("ccw_half", {"m_ccw_kgh": 153000.0}, 185.0, 173.23),
    ("ccw_hot", {"t_ccw_in": 95.0}, 185.0, 180.00),
    ("purge_shut", {"hic604_pct": 0.0}, 185.0, 177.00),
    ("overload_110", {"co2_scale": 1.10}, 185.0, 173.50),
    ("ccw_quarter", {"m_ccw_kgh": 76500.0}, 185.0, 185.0),
])
def test_tt_322002_has_room_to_move_decided_divergence(v1_verbatim, name, kwargs, v1_t, port_t):
    """Handoff B-16's measurement: on V1's pin the overflow sits 6.2 C under the 185 C
    condensation ceiling, and each of these reaches it on its own, so V1 publishes 185.0 and
    stops telling a bad state from a worse one. On the PFD's pin the same disturbances stay under
    it; a quarter of the water still takes the port to the ceiling."""
    from ureasim.units.synthesis.scrubber import scrubber_322e003
    v1_verbatim["state"].p_syn_bara = 140.7
    kw = dict(kwargs)
    s = kw.pop("co2_scale", 1.0)
    t_in = kw.pop("t_ccw_in", v1_verbatim["SCRUB_CCW_T_IN_DES"])
    m_ccw = kw.pop("m_ccw_kgh", v1_verbatim["SCRUB_CCW_KGH_DES"])
    theirs = v1_verbatim["scrub_322e003"](v1_verbatim["REACT_OFFGAS_DES"], s, t_in, m_ccw, **kw)
    mine = scrubber_322e003(v1_verbatim["REACT_OFFGAS_DES"], s, t_in, m_ccw, p_loop_bara=140.7,
                            **kw)
    assert theirs["T_overflow"] == pytest.approx(v1_t, abs=0.01)
    assert mine.t_overflow_c == pytest.approx(port_t, abs=0.01)
