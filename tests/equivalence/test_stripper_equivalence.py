"""V1 <-> V1.1 equivalence for 322E001, the HP CO2 stripper.

What is being proved, and how strongly
--------------------------------------
This port is proven by EXECUTION, not by transcription. `v1_loader.lift` compiles V1's own
`stripper_322e001`, `strip_hyd_rate_group`, `_hp_k_ratio`, `_ratio_shift_frac`, `_kmolh_to_w`,
`tsat_steam`, `urea_hydrolysis_k_m3_kmol_h`, `clamp` and every constant they transitively
depend on, straight out of `backend/main.py`, and runs them. What the tests compare is V1's
bytes against V1.1's bytes over the same inputs.

That is a stronger standard than unit 321 and the CO2 line could reach, and the reason is
structural rather than lucky: the stripper's physics is a module-level FUNCTION in V1, so it
can be lifted whole. Only the `step_sim` statements that wire it — the live steam
temperature, the Darcy-Weisbach tube-side pressure and the reactor tear — sit inside the
4,100-line body and are not exercised here. They belong to the sump and wiring module and are
tracked under handoff A-12 with the rest.

What is in this file, and what is next door
-------------------------------------------
This file holds everything that drives BOTH implementations and compares them: the design
point, the five off-design sweeps, the two extreme states, and the three shared helpers that
V1 and V1.1 both own a version of.

The tests that assert what the ported model DOES — the flooding block, the bottom-temperature
signs, slip, the two reaction laws, the enthalpy balance — live in
`tests/units/synthesis/test_stripper.py`. They need no V1 tree, so they keep running on a
machine that has only the rewrite, where this file skips.

Handoff B-9, decided 2026-10-07
-------------------------------
The port's two flood rises share one ceiling, ``max(dT_bot, dT_flood)``, where V1 adds them.
The ``v1`` fixture is V1's stripper with that one statement switched (`b9_switch`), every other
line V1's own; ``v1_verbatim`` is V1 untouched, and the last section asserts both sides.
"""

from __future__ import annotations

import math

import pytest

from ureasim.core.stream import MW_COMP, mass_fractions_from_kmolh
from ureasim.data import unit_322e001 as d
from ureasim.data.unit_321 import CO2_DES_KGH
from ureasim.data.unit_322r001 import REACTOR_FEED_HC_DES, REACTOR_FEED_NC_DES
from ureasim.thermo.kinetics import urea_hydrolysis_k_m3_kmol_h
from ureasim.thermo.service import ratio_shift_frac
from ureasim.units.synthesis.stripper import (
    DUTY_RAW_DES_KW,
    HYDROLYSIS_GROUP_DES,
    TOP_DES_CO2_FREE_KMOLH,
    TOP_DES_KMOLH_TOTAL,
    TOP_DES_NH3_KMOLH,
    hydrolysis_rate_group,
    stripper_322e001,
)
from tests.equivalence import b9_switch
from tests.equivalence.v1_loader import lift, load, v1_available, v1_service

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

CO2_DES_TH = CO2_DES_KGH / 1000.0


def _lift_v1() -> dict:
    """V1's stripper and its whole constant chain, executed out of `main.py`."""
    return lift(
        ["stripper_322e001", "strip_hyd_rate_group", "_ratio_shift_frac", "_kmolh_to_w",
         "urea_hydrolysis_k_m3_kmol_h", "tsat_steam", "STRIP_HYD_GROUP_DES",
         "STRIP_STEAM_T_DES_C", "STRIP_P_DES_BARA", "STRIP_FEED207_KMOLH",
         "STRIP_FEED_DES_KGH", "STRIP_N_TUBES", "STRIP_FLOOD_KGH_TUBE",
         "STRIP_DUTY_RAW_DES_KW", "STRIP_TOP_MOL_DES", "STRIP_TOP_NH3_DES",
         "STRIP_TOP_CO2FREE_DES", "CO2_DES_KGH", "MW_COMP"],
        seed={"math": math, "reactor": load("reactor"),
              "thermo_service": v1_service(), "iapws_if97": load("iapws_if97")},
    )


@pytest.fixture(scope="module")
def v1():
    """V1's stripper with B-9's one statement switched; every other line V1's own."""
    return b9_switch.switch(_lift_v1())


@pytest.fixture(scope="module")
def v1_verbatim():
    """V1's stripper untouched, for the tests that assert B-9 both ways."""
    return _lift_v1()


# --------------------------------------------------------------------------------------
# How a V1 dict and a V1.1 record are compared
# --------------------------------------------------------------------------------------
# V1 returns a dict keyed in its own naming; V1.1 returns a frozen dataclass in the house
# naming. The map below is the ONLY place the two vocabularies meet, so a renamed field shows
# up here as a failure rather than as a silently skipped comparison.

SCALARS = {
    "top_kgh": "top_kgh", "bot_kgh": "bot_kgh", "top_th": "top_th", "bot_th": "bot_th",
    "top_mol": "top_kmolh_total", "bot_mol": "bot_kmolh_total",
    "top_MW": "top_mw", "bot_MW": "bot_mw",
    "T_top": "t_top", "T_bot": "t_bot", "T_feed": "t_feed", "T_steam": "t_steam",
    "xi_hyd": "xi_hydrolysis", "xi_biu": "xi_biuret",
    "eta_T": "eta_t", "eta_T_steam": "eta_t_steam",
    "g_NC": "g_nc", "g_HC": "g_hc", "g_T": "g_t", "slip": "slip",
    "L_strip": "feed_nc", "W_strip": "feed_hc",
    "dT_load": "dt_load", "dT_bot": "dt_bot", "dT_strip": "dt_strip",
    "r_GL": "r_gl", "m_feed_kgh": "feed_kgh",
    "flood_frac": "flood_frac", "flood_x": "flood_excess", "g_flood": "g_flood",
    "dT_flood": "dt_flood", "flood_kgh_tube": "flood_kgh_per_tube",
    "duty_raw_kw": "duty_raw_kw", "q_carb_kw": "q_carbamate_kw", "q_nh3_kw": "q_nh3_kw",
    "q_h2o_kw": "q_h2o_kw", "q_hyd_kw": "q_hydrolysis_kw", "q_sens_kw": "q_sensible_kw",
    "n_co2_desorb": "n_co2_desorbed", "n_nh3_free": "n_nh3_free",
}

VECTORS = {
    "feed_kmolh": "feed_kmolh", "co2_feed_kmolh": "co2_feed_kmolh",
    "top_kmolh": "top_kmolh", "bot_kmolh": "bot_kmolh",
    "top_comp_pct": "top_comp_pct", "bot_mass_pct": "bot_mass_pct",
}


def assert_same(v1_result: dict, result, where: str) -> None:
    """Every published field of both implementations, compared exactly."""
    for v1_key, attr in SCALARS.items():
        assert v1_result[v1_key] == getattr(result, attr), f"{where}: {v1_key}"
    for v1_key, attr in VECTORS.items():
        live = getattr(result, attr)
        for species in MW_COMP:
            assert v1_result[v1_key][species] == live[species], (
                f"{where}: {v1_key}[{species}]")


def run_both(v1, co2_th, t_steam_c, p_bara, overflow_kmolh=None, nc=None, hc=None,
             t_feed=None, level=None):
    """Drive both implementations with one set of inputs."""
    kwargs_v1 = {}
    kwargs_new = {}
    if overflow_kmolh is not None:
        kwargs_v1["overflow_kmolh"] = overflow_kmolh
        kwargs_new["overflow_kmolh"] = overflow_kmolh
    if nc is not None:
        kwargs_v1["L_feed"] = nc
        kwargs_new["feed_nc"] = nc
    if hc is not None:
        kwargs_v1["W_feed"] = hc
        kwargs_new["feed_hc"] = hc
    if t_feed is not None:
        kwargs_v1["T_feed_C"] = t_feed
        kwargs_new["t_feed_c"] = t_feed
    if level is not None:
        kwargs_v1["strip_level_pct"] = level
        kwargs_new["level_pct"] = level
    return (v1["stripper_322e001"](co2_th, t_steam_c, p_bara, **kwargs_v1),
            stripper_322e001(co2_th, t_steam_c, p_bara, **kwargs_new))


# ======================================================================================
# 1. The design point
# ======================================================================================

def test_the_design_point_is_bit_exact(v1):
    """At the licensor's own design condition the two implementations agree to the bit."""
    a, b = run_both(v1, CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA)
    assert_same(a, b, "design point")


def test_the_design_constants_are_the_same_numbers(v1):
    """The derived constants V1.1 computes match the ones V1 computes, exactly.

    These are the numbers downstream units anchor on, so a discrepancy here would move the
    carbamate condenser and the reactor even if the stripper itself matched.
    """
    assert d.STEAM_T_DES_C == v1["STRIP_STEAM_T_DES_C"]
    assert d.FEED_DES_KGH == v1["STRIP_FEED_DES_KGH"]
    assert HYDROLYSIS_GROUP_DES == v1["STRIP_HYD_GROUP_DES"]
    assert DUTY_RAW_DES_KW == v1["STRIP_DUTY_RAW_DES_KW"]
    assert TOP_DES_KMOLH_TOTAL == v1["STRIP_TOP_MOL_DES"]
    assert TOP_DES_NH3_KMOLH == v1["STRIP_TOP_NH3_DES"]
    assert TOP_DES_CO2_FREE_KMOLH == v1["STRIP_TOP_CO2FREE_DES"]


def test_the_design_point_reproduces_the_licensor_balance():
    """The PFD numbers themselves, not merely agreement with V1.

    A port can agree with its source and still have both be wrong. These are the licensor's
    published values for the design state, so this is the check that the anchor is the anchor.
    """
    r = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA)
    assert r.t_bot == d.T_BOTTOM_DES_C                 # TT-322004, exactly 172.0
    assert r.t_top == d.T_TOPGAS_DES_C                 # TT-322013, exactly 187.0
    assert r.xi_hydrolysis == d.XI_HYDROLYSIS_DES      # exactly 88.1
    assert r.xi_biuret == d.XI_BIURET_DES              # exactly 0.667
    assert r.eta_t == 1.0
    # The design bottoms flow the sump and LV-322501 are anchored on, to 0.01 %.
    assert r.bot_kgh == pytest.approx(d.BOTTOMS_DES_KGH, rel=1.0e-4)


def test_every_efficiency_term_is_exactly_one_at_design():
    """Not approximately one. Each is an identity at the seed, by the arithmetic.

    This is the property the whole anchored-departure design rests on: if any one of these
    were 1.0 only to a tolerance, the pinned design state would drift the first time the
    flowsheet was stepped.
    """
    r = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA)
    assert r.eta_t_steam == 1.0
    assert r.g_nc == 1.0
    assert r.g_hc == 1.0
    assert r.g_t == 1.0
    assert r.g_flood == 1.0
    assert r.slip == 0.0
    assert r.dt_load == 0.0
    assert r.dt_bot == 0.0
    assert r.dt_strip == 0.0
    assert r.dt_flood == 0.0
    assert r.r_gl == 0.0


def test_the_duty_ratio_is_exactly_one_at_design():
    """The enthalpy balance is used only as a ratio, so its 4 % offset must cancel exactly.

    The absolute balance comes out at about 37 831 kW against the licensor's 39 400 kW. That
    4 % residue is real — shell loss, biuret, the mean-cp approximation — and it is precisely
    why the absolute number is never used. What the MP header sees is
    `DUTY_DES_KW * (live / design)`, so the offset has to divide out to a literal 1.0.
    """
    r = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA)
    assert r.duty_raw_kw / DUTY_RAW_DES_KW == 1.0
    # And the offset it cancels is the one the constant block documents.
    assert DUTY_RAW_DES_KW / d.DUTY_DES_KW == pytest.approx(0.960, abs=0.005)


# ======================================================================================
# 2. Off design, driver by driver
# ======================================================================================

@pytest.mark.parametrize("co2_th", [0.0, 5.0, 20.0, 40.0, CO2_DES_TH, 60.0, 80.0])
def test_the_co2_sweep_rate_sweeps_identically(v1, co2_th):
    """From a lost compressor to 47 % over design sweep."""
    a, b = run_both(v1, co2_th, d.STEAM_T_DES_C, d.P_DES_BARA)
    assert_same(a, b, f"co2={co2_th} t/h")


@pytest.mark.parametrize("p_mp", [12.0, 16.0, 19.7, 22.0, 25.0])
def test_the_shell_steam_pressure_sweeps_identically(v1, p_mp):
    """A live MP header, from a badly sagged one to the battery-limit maximum."""
    t_steam = v1["tsat_steam"](p_mp)
    a, b = run_both(v1, CO2_DES_TH, t_steam, d.P_DES_BARA)
    assert_same(a, b, f"P_MP={p_mp} bar a")


@pytest.mark.parametrize("p_bara", [120.0, 135.0, 144.0, 150.0, 160.0])
def test_the_tube_side_pressure_sweeps_identically(v1, p_bara):
    """This is the path that exercises the Extended UNIQUAC K-value ratio.

    It is also the one that was a dead lever in V1 until the species-blind linear surrogate
    was replaced: the pressure reached the split through one number applied to NH3, CO2, H2O
    and four inerts alike.
    """
    a, b = run_both(v1, CO2_DES_TH, d.STEAM_T_DES_C, p_bara)
    assert_same(a, b, f"P={p_bara} bar a")


@pytest.mark.parametrize("scale", [0.4, 0.7, 1.0, 1.3, 1.6])
def test_the_reactor_overflow_rate_sweeps_identically(v1, scale):
    """The liquid feed, from a deep turndown to a flood."""
    overflow = {k: v * scale for k, v in d.FEED_207_KMOLH.items()}
    a, b = run_both(v1, CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA, overflow_kmolh=overflow)
    assert_same(a, b, f"overflow x{scale}")


@pytest.mark.parametrize("nc", [2.6, 3.0, REACTOR_FEED_NC_DES, 3.4, 4.0])
@pytest.mark.parametrize("hc", [0.30, REACTOR_FEED_HC_DES, 0.55])
def test_the_reactor_feed_ratios_sweep_identically(v1, nc, hc):
    """Both composition penalties, including the range where each hits its floor."""
    a, b = run_both(v1, CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA, nc=nc, hc=hc)
    assert_same(a, b, f"N/C={nc} H/C={hc}")


@pytest.mark.parametrize("t_feed", [150.0, 170.0, 183.0, 195.0])
@pytest.mark.parametrize("level", [0.0, 20.0, 50.0, 85.0, 100.0])
def test_the_feed_temperature_and_sump_level_sweep_identically(v1, t_feed, level):
    """The feed temperature drives the sensible term; the level drives the reaction holdup."""
    a, b = run_both(v1, CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA,
                    t_feed=t_feed, level=level)
    assert_same(a, b, f"T_feed={t_feed} level={level}")


def test_an_empty_stripper_agrees(v1):
    """No liquid feed and no sweep gas — every guarded division taken at once.

    A black start passes through exactly this state, so the guards are not hypothetical.
    """
    empty = {k: 0.0 for k in d.FEED_207_KMOLH}
    a, b = run_both(v1, 0.0, d.STEAM_T_DES_C, d.P_DES_BARA, overflow_kmolh=empty)
    assert_same(a, b, "empty")


def test_a_combined_severe_excursion_agrees(v1):
    """Everything wrong at once: cold steam, low pressure, rich feed, flooded, hot liquor."""
    overflow = {k: v * 1.45 for k, v in d.FEED_207_KMOLH.items()}
    a, b = run_both(v1, 30.0, v1["tsat_steam"](14.0), 132.0,
                    overflow_kmolh=overflow, nc=3.6, hc=0.52, t_feed=190.0, level=95.0)
    assert_same(a, b, "combined excursion")


# ======================================================================================
# 3. The three transforms both implementations own a version of
# ======================================================================================

def test_the_split_transform_is_an_identity_at_unit_ratio_and_bounded_elsewhere(v1):
    """`ratio_shift_frac` against V1's `_ratio_shift_frac`, and its two structural claims."""
    for theta in (0.0, 1e-6, 0.1313, 0.5, 0.8546, 0.999, 1.0):
        for r in (0.02, 0.5, 1.0, 2.0, 50.0):
            assert ratio_shift_frac(theta, r) == v1["_ratio_shift_frac"](theta, r)
    # Exactly theta at r == 1.0, by the arithmetic rather than a short-circuit.
    for theta in (0.1313, 0.5, 0.8546):
        assert ratio_shift_frac(theta, 1.0) == theta
    # Monotone in r, and inside [0, 1] for every ratio.
    previous = -1.0
    for r in (0.02, 0.1, 0.5, 1.0, 2.0, 10.0, 50.0):
        value = ratio_shift_frac(0.8546, r)
        assert 0.0 <= value <= 1.0
        assert value > previous
        previous = value


def test_the_hydrolysis_rate_group_matches_v1(v1):
    """The Inoue-Otsuka group itself, over temperature, concentration and holdup."""
    for t_c in (120.0, 150.0, 172.0, 190.0, 210.0):
        for vdot in (100.0, 283.7, 600.0):
            for v_liq in (7.66, 11.14, 20.0):
                assert hydrolysis_rate_group(t_c, 1302.6, 2222.0, vdot, v_liq) == (
                    v1["strip_hyd_rate_group"](t_c, 1302.6, 2222.0, vdot, v_liq))
    # The guards, which a black start actually takes.
    assert hydrolysis_rate_group(172.0, 1302.6, 2222.0, 0.0, 11.14) == 0.0
    assert hydrolysis_rate_group(172.0, 1302.6, 2222.0, 283.7, 0.0) == 0.0


def test_the_rate_constant_matches_v1_and_its_published_value(v1):
    """The Arrhenius line, against V1 and against the value V1's own note quotes."""
    for t_c in (25.0, 100.0, 172.0, 210.0):
        assert urea_hydrolysis_k_m3_kmol_h(t_c) == v1["urea_hydrolysis_k_m3_kmol_h"](t_c)
    assert urea_hydrolysis_k_m3_kmol_h(172.0) == pytest.approx(0.043482, abs=1e-6)
    # 11 100 K in the exponent: roughly a doubling per 10 deg C around the stripper bottom.
    ratio = urea_hydrolysis_k_m3_kmol_h(182.0) / urea_hydrolysis_k_m3_kmol_h(172.0)
    assert 1.7 < ratio < 2.1

def test_the_molar_to_mass_fraction_conversion_matches_v1(v1):
    """Including its deliberate pure-water fallback on an empty vector."""
    for vector in (d.FEED_207_KMOLH, d.FEED_DES_KMOLH,
                   {k: 0.0 for k in MW_COMP}, {"NH3": 1.0}):
        live = mass_fractions_from_kmolh(vector)
        reference = v1["_kmolh_to_w"](vector)
        for species in MW_COMP:
            assert live[species] == reference[species]
    empty = mass_fractions_from_kmolh({k: 0.0 for k in MW_COMP})
    assert empty["H2O"] == 1.0
    assert sum(empty.values()) == 1.0


# ======================================================================================
# 4. The decided divergence: one flood ceiling (handoff B-9, 2026-10-07), both sides
# ======================================================================================

def test_below_the_flooding_limit_the_switch_is_inert(v1, v1_verbatim):
    """Below 134 % of design load the flood rise is exactly 0.0 and max() returns the other
    branch: V1 verbatim and the port agree to the bit, the design point included."""
    for scale in (0.4, 1.0, 1.3):
        overflow = {k: v * scale for k, v in d.FEED_207_KMOLH.items()}
        a = v1_verbatim["stripper_322e001"](CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA,
                                           overflow_kmolh=overflow)
        b = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA, overflow_kmolh=overflow)
        assert b.dt_flood == 0.0
        assert_same(a, b, f"overflow x{scale}")


@pytest.mark.parametrize("fraction, steam, flood, v1_bot, port_bot", [
    (1.10, 10.93, 3.50, 186.43, 182.93),
    (1.50, 11.00, 9.38, 192.38, 183.00),
    (10.0, 11.00, 11.00, 194.00, 183.00),
])
def test_a_flooded_stripper_tends_to_its_liquor_decided_divergence(
        v1_verbatim, fraction, steam, flood, v1_bot, port_bot):
    """The bundle past its flooding limit (handoff B-9's sweep). V1 adds the two rises and its
    bottoms tend to 194 C; the port takes the larger and tends to the 183 C fed. The flood rise
    is the same on both sides; its efficiency knockdown moves by under 0.4 %, through the
    carbamate the cooler bottoms decompose, which is its denominator."""
    from tests.units.synthesis.test_stripper import overflow_at_flood_fraction
    overflow = overflow_at_flood_fraction(fraction)
    a = v1_verbatim["stripper_322e001"](CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA,
                                       overflow_kmolh=overflow)
    b = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA, overflow_kmolh=overflow)
    assert (a["dT_flood"], a["dT_load"]) == (b.dt_flood, b.dt_load)
    assert abs(a["g_flood"] - b.g_flood) < 0.004
    assert a["dT_flood"] == pytest.approx(flood, abs=0.01)
    assert a["dT_bot"] == pytest.approx(steam + flood, abs=0.02)
    assert b.dt_bot == pytest.approx(max(steam, flood), abs=0.01)
    assert a["T_bot"] == pytest.approx(v1_bot, abs=0.01)
    assert b.t_bot == pytest.approx(port_bot, abs=0.01)
