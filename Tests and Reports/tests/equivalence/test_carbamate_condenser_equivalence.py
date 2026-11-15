"""V1 vs V1.1 — 322E002, the HP carbamate condenser.

Evidence standard
-----------------
Execution. `hpcc_322e002`, `_hpcc_flash_split` and `bubble_p_322e002` are all module-level
functions in `main.py`, so all three come through `v1_loader.lift` and every assertion below
compares V1's own bytes against the rewrite's. The design constants are lifted with them.

The one thing that needs care
------------------------------
V1's `hpcc_322e002` reads the shell conductance from a MODULE GLOBAL that is `None` until a
boot routine sets it. The rewrite makes it a parameter with a module-level default, which is
the same two states expressed differently: `ua_kjhk=None` is V1 before the pin, and the
default is V1 after it. Both are exercised here, and the lifted namespace's global is written
directly so the post-pin comparison is against V1's own code path rather than a stand-in.

The decided divergence
----------------------
Below N/C 3.0 the melt's bubble pressure follows the Extended UNIQUAC rise toward its azeotrope
(decided 2026-10-22, handoff B-106), where V1's K_N line falls. Every comparison above runs the
port on V1's line (``low_nc=False``); section 5 runs both ways.
"""

from __future__ import annotations

import math

import pytest

from ureasim.core.stream import MW_COMP
from ureasim.data import unit_322e002 as d
from ureasim.units.synthesis.carbamate_condenser import (
    UA_KJHK,
    bubble_p_322e002,
    carbamate_condenser_322e002,
    hpcc_flash_split,
    low_nc_rise,
)

from . import b6_switch, b9_switch
from .v1_loader import lift, load, v1_available, v1_service

pytestmark = pytest.mark.skipif(not v1_available(),
                                reason="V1 reference tree not present on this machine")

V1_NAMES = [
    "hpcc_322e002", "_hpcc_flash_split", "bubble_p_322e002", "HPCC_UA",
    "HPCC_FRAC_GAS_DES", "HPCC_T_PROD_DES_C", "HPCC_P_DES_BARA",
    "HPCC_STEAM_P_BARA", "HPCC_STEAM_TSAT_PFD_C", "HPCC_STEAM_TSAT_C",
    "HPCC_DH_CARB_KJMOL", "HPCC_CP_GAS", "HPCC_LATENT_4BAR",
    "HPCC_FLASH_DH", "HPCC_FLASH_ITERS", "_HPCC_BUB_T0_K",
    "HPCC_BUB_DHVAP_JMOL", "HPCC_BUB_KN", "HPCC_BUB_KW",
    "HPCC_TAU_FILL_MIN", "HPCC_LEVEL_NLL_PCT",
    "stripper_322e001", "ejector_322f001",
    "CO2_DES_KGH", "STRIP_STEAM_T_DES_C", "STRIP_P_DES_BARA",
    "EJ_MOTIVE_NH3_DES", "EJ_MOTIVE_T_DES_C", "EJ_OPEN_DES",
    "SYN_P_DES_BARA",
]


@pytest.fixture(scope="module")
def v1():
    """The condenser, its two helpers and its constants, with the shell conductance pinned.

    V1 leaves `HPCC_UA` at None until its boot routine runs an 18 000-tick settle. The UA
    LINE inside that routine uses a synthetic single call, not the settle, so the value is
    reproduced here in one pass — and it is written back into the lifted namespace, which is
    what V1's function reads, so the post-pin path below is V1's own.
    """
    # The standard atmosphere and gravity (B-6, B-7, decided) under 322F001's design suction.
    ns = lift(b6_switch.names(V1_NAMES), seed=b6_switch.seed({
        "math": math, "jet_pump": load("jet_pump"), "h0_enthalpy": load("gap_g6_h0_enthalpy"),
        "reactor": load("reactor"), "thermo_service": v1_service(),
        "iapws_if97": load("iapws_if97")}))
    b9_switch.switch(ns)                      # 322E001's one flood ceiling (B-9, decided)
    gas = ns["stripper_322e001"](ns["CO2_DES_KGH"] / 1000.0, ns["STRIP_STEAM_T_DES_C"],
                                 ns["STRIP_P_DES_BARA"])
    liq = ns["ejector_322f001"](ns["EJ_MOTIVE_NH3_DES"], ns["EJ_MOTIVE_T_DES_C"],
                                ns["EJ_OPEN_DES"])
    synthetic = ns["hpcc_322e002"](gas, liq, gate=1.0)
    ns["HPCC_UA"] = -synthetic["m_dot"] * ns["HPCC_CP_GAS"] * math.log(
        (ns["HPCC_T_PROD_DES_C"] - ns["HPCC_STEAM_TSAT_C"])
        / (synthetic["T_adb"] - ns["HPCC_STEAM_TSAT_C"]))
    ns["_design_gas"] = gas
    ns["_design_liq"] = liq
    return ns


# ======================================================================================
# 1. The constants
# ======================================================================================

SCALARS = [
    ("T_PROD_DES_C", "HPCC_T_PROD_DES_C"),
    ("P_DES_BARA", "HPCC_P_DES_BARA"),
    ("STEAM_P_BARA", "HPCC_STEAM_P_BARA"),
    ("STEAM_TSAT_PFD_C", "HPCC_STEAM_TSAT_PFD_C"),
    ("STEAM_TSAT_C", "HPCC_STEAM_TSAT_C"),
    ("DH_CARB_KJMOL", "HPCC_DH_CARB_KJMOL"),
    ("CP_GAS", "HPCC_CP_GAS"),
    ("LATENT_4BAR", "HPCC_LATENT_4BAR"),
    ("FLASH_ITERS", "HPCC_FLASH_ITERS"),
    ("FLASH_T0_K", "_HPCC_BUB_T0_K"),
    ("BUB_DHVAP_JMOL", "HPCC_BUB_DHVAP_JMOL"),
    ("BUB_KN", "HPCC_BUB_KN"),
    ("BUB_KW", "HPCC_BUB_KW"),
    ("TAU_FILL_MIN", "HPCC_TAU_FILL_MIN"),
    ("LEVEL_NLL_PCT", "HPCC_LEVEL_NLL_PCT"),
]


@pytest.mark.parametrize("ours,theirs", SCALARS)
def test_constants_match_v1(v1, ours, theirs):
    assert getattr(d, ours) == v1[theirs]


@pytest.mark.parametrize("ours,theirs", [("FRAC_GAS_DES", "HPCC_FRAC_GAS_DES"),
                                         ("FLASH_DH", "HPCC_FLASH_DH")])
def test_vectors_match_v1(v1, ours, theirs):
    assert getattr(d, ours) == v1[theirs]


def test_the_shell_saturation_is_the_shared_iapws_boundary(v1):
    """151.936 C, not the licensor's rounded 146.3 — and the rounded figure is kept as
    provenance so the difference cannot be mistaken for a port error."""
    assert d.STEAM_TSAT_C == pytest.approx(151.936, abs=0.001)
    assert d.STEAM_TSAT_PFD_C == 146.3
    assert d.STEAM_TSAT_C != d.STEAM_TSAT_PFD_C


def test_the_conductance_back_calc_matches_v1(v1):
    """The one number in this unit that is derived rather than sourced."""
    assert UA_KJHK == v1["HPCC_UA"]


# ======================================================================================
# 2. The flash
# ======================================================================================

#: The design tube-side feed, and three deliberate departures from it.
def feed_at(v1, **scale):
    """The design combined feed with named components scaled."""
    gas, liq = v1["_design_gas"], v1["_design_liq"]
    feed = {k: gas["top_kmolh"].get(k, 0.0) + liq["comp"].get(k, 0.0) / MW_COMP[k]
            for k in MW_COMP}
    for k, factor in scale.items():
        feed[k] = feed[k] * factor
    return feed


@pytest.mark.parametrize("t_c", [80.0, 130.0, 160.0, 169.9, 170.0, 170.1, 185.0, 220.0,
                                 300.0, -50.0])
def test_flash_temperature_sweep_matches_v1(v1, t_c):
    """Over the whole band, including the calibration point itself.

    V1 deleted an identity short-circuit at exactly (T_des, P_des) — finding A-15 — so the
    routine now CONVERGES to the design split there rather than returning it. This sweep
    brackets that point on both sides and lands on it.
    """
    feed = feed_at(v1)
    assert hpcc_flash_split(feed, t_c, v1["SYN_P_DES_BARA"]) \
        == v1["_hpcc_flash_split"](feed, t_c, v1["SYN_P_DES_BARA"])


@pytest.mark.parametrize("p_loop", [0.0, 1e-7, 1.0, 40.0, 100.0, 140.7, 144.2, 200.0, 400.0])
def test_flash_pressure_sweep_matches_v1(v1, p_loop):
    """Including the 1e-6 floor, which is the only guard in the pressure ratio."""
    feed = feed_at(v1)
    assert hpcc_flash_split(feed, 170.0, p_loop) \
        == v1["_hpcc_flash_split"](feed, 170.0, p_loop)


@pytest.mark.parametrize("scale", [{"CO2": 0.0}, {"NH3": 0.0}, {"H2O": 0.0},
                                   {"CO2": 0.0, "NH3": 0.0, "H2O": 0.0, "N2": 0.0},
                                   {"CO2": 3.0}, {"NH3": 0.1}, {"H2O": 10.0},
                                   {"CO2": 1e-14, "NH3": 1e-14, "H2O": 1e-14, "N2": 1e-14}])
def test_flash_composition_sweep_matches_v1(v1, scale):
    """Including both degenerate-feed guards, which each protect a division."""
    feed = feed_at(v1, **scale)
    assert hpcc_flash_split(feed, 170.0, v1["SYN_P_DES_BARA"]) \
        == v1["_hpcc_flash_split"](feed, 170.0, v1["SYN_P_DES_BARA"])


def test_flash_on_an_empty_feed_matches_v1(v1):
    """A cold, empty condenser flashes nothing and both hold the design vector."""
    empty = {k: 0.0 for k in MW_COMP}
    assert hpcc_flash_split(empty, 170.0, 140.7) \
        == v1["_hpcc_flash_split"](empty, 170.0, 140.7)


@pytest.mark.parametrize("t_c,p_loop", [(120.0, 90.0), (200.0, 180.0), (155.0, 144.2),
                                        (170.0, 140.7)])
def test_flash_off_design_pairs_match_v1(v1, t_c, p_loop):
    """Temperature and pressure moving together, which is what a real excursion does."""
    feed = feed_at(v1)
    assert hpcc_flash_split(feed, t_c, p_loop) \
        == v1["_hpcc_flash_split"](feed, t_c, p_loop)


# ======================================================================================
# 3. The bubble pressure
# ======================================================================================

@pytest.mark.parametrize("t_c", [60.0, 120.0, 170.0, 200.0, 250.0])
@pytest.mark.parametrize("nc", [1.5, 3.072961, 3.5, 6.0])
@pytest.mark.parametrize("hc", [0.2, 0.39824129577331385, 0.8, 4.0])
def test_bubble_pressure_matches_v1(v1, t_c, nc, hc):
    """All three arguments, including the range where either factor floors at zero."""
    assert bubble_p_322e002(t_c, nc, hc, low_nc=False) == v1["bubble_p_322e002"](t_c, nc, hc)


def test_the_bubble_anchor_defaults_to_the_reactor_feed(v1):
    """V1 falls back to the reactor-feed N/C until its boot captures the settled melt."""
    from ureasim.data.unit_322r001 import REACTOR_FEED_NC_DES

    assert bubble_p_322e002(170.0, REACTOR_FEED_NC_DES, 0.39824129577331385) \
        == pytest.approx(d.P_DES_BARA, rel=1e-12)
    assert bubble_p_322e002(170.0, 3.5, 0.39824129577331385, nc_anchor=3.5) \
        == pytest.approx(d.P_DES_BARA, rel=1e-12)


# ======================================================================================
# 4. The unit
# ======================================================================================

FIELDS = [("phi_gas", "phi_gas"), ("phi_film", "phi_film"), ("phi_eq", "phi_eq"),
          ("feed_kmolh", "feed_kmolh"), ("gas_kmolh", "gas_kmolh"), ("liq_kmolh", "liq_kmolh"),
          ("gas_kgh", "gas_kgh"), ("liq_kgh", "liq_kgh"), ("gas_th", "gas_th"),
          ("liq_th", "liq_th"), ("gas_mol", "gas_mol"), ("liq_mol", "liq_mol"),
          ("gas_MW", "gas_mw"), ("liq_MW", "liq_mw"),
          ("gas_mol_pct", "gas_mol_pct"), ("liq_mass_pct", "liq_mass_pct"),
          ("T_prod", "t_prod"), ("T_feed_mix", "t_feed_mix"), ("T_adb", "t_adb"),
          ("duty_kw", "duty_kw"), ("q_steam_kw", "q_steam_kw"), ("steam_kgh", "steam_kgh"),
          ("m_dot", "m_dot_kgh"), ("P_bub", "p_bub_bara"),
          ("L_hpcc", "melt_nc"), ("W_hpcc", "melt_hc")]


#: V1's keyword names against the rewrite's. The rewrite suffixes a unit where V1 does not,
#: which is the house style; the tests are written in V1's names and translated here once.
KEYWORDS = {"t_shell": "t_shell_c", "t_prod_prev": "t_prod_prev_c", "p_loop": "p_loop_bara"}


def assert_same(v1, where, gas=None, liq=None, **kwargs):
    """Drive both implementations with the same state and compare every published field."""
    gas = v1["_design_gas"] if gas is None else gas
    liq = v1["_design_liq"] if liq is None else liq
    theirs = v1["hpcc_322e002"](gas, liq, **kwargs)
    ours = carbamate_condenser_322e002(
        gas["top_kmolh"], gas["T_top"], liq["comp"], liq["T_C"], low_nc=False, release_heat=False,
        **{KEYWORDS.get(k, k): v for k, v in kwargs.items()})
    for old_key, new_key in FIELDS:
        a, b = theirs[old_key], getattr(ours, new_key)
        assert a == b, f"{where}: {old_key} {a!r} != {b!r}"


def test_design_call_agrees(v1):
    """The design state, every published field, bit for bit."""
    assert_same(v1, "design")


def test_the_unpinned_pass_agrees(v1):
    """`ua_kjhk=None` against V1's pre-boot `HPCC_UA is None` — the back-calc state."""
    saved = v1["HPCC_UA"]
    v1["HPCC_UA"] = None
    try:
        gas, liq = v1["_design_gas"], v1["_design_liq"]
        theirs = v1["hpcc_322e002"](gas, liq, gate=1.0)
        ours = carbamate_condenser_322e002(gas["top_kmolh"], gas["T_top"], liq["comp"],
                                           liq["T_C"], gate=1.0, ua_kjhk=None, low_nc=False,
                                           release_heat=False)
        for old_key, new_key in FIELDS:
            assert theirs[old_key] == getattr(ours, new_key), old_key
    finally:
        v1["HPCC_UA"] = saved


@pytest.mark.parametrize("gate", [0.0, 0.001, 0.25, 0.5, 0.75, 0.999, 1.0])
def test_gate_sweep_agrees(v1, gate):
    """The Option-1 disturbance factor, across its whole range and at both ends."""
    assert_same(v1, f"gate={gate}", gate=gate)


@pytest.mark.parametrize("t_shell", [100.0, 140.0, 151.93597693401904, 160.0, 175.0, 200.0])
def test_shell_temperature_sweep_agrees(v1, t_shell):
    """The LP header moving, which is the coupling the gate exists to tame."""
    assert_same(v1, f"t_shell={t_shell}", t_shell=t_shell)


@pytest.mark.parametrize("t_prev", [120.0, 160.0, 170.0, 180.0, 210.0])
def test_torn_product_temperature_sweep_agrees(v1, t_prev):
    """The previous tick's outlet, which is what the split is flashed at."""
    assert_same(v1, f"t_prev={t_prev}", t_prod_prev=t_prev)


@pytest.mark.parametrize("p_loop", [100.0, 140.7, 144.2, 160.0, 200.0])
def test_loop_pressure_sweep_agrees(v1, p_loop):
    assert_same(v1, f"p_loop={p_loop}", p_loop=p_loop)


@pytest.mark.parametrize("dt", [0.0, 0.05, 0.25, 1.0, 10.0, 360.0, 1000.0])
def test_film_relaxation_step_sweep_agrees(v1, dt):
    """Including `dt = 0`, which holds the split, and a step past the whole holdup time."""
    assert_same(v1, f"dt={dt}", dt=dt, t_prod_prev=185.0)


def test_a_film_state_carried_in_agrees(v1):
    """The split is a STATE, so the caller supplies last tick's and the model relaxes it."""
    half = {k: 0.5 * v for k, v in v1["HPCC_FRAC_GAS_DES"].items()}
    assert_same(v1, "phi_prev", phi_prev=half, dt=1.0, t_prod_prev=180.0)


def test_a_film_state_missing_a_species_agrees(v1):
    """Both fall back to the calibration for a component the caller did not supply."""
    partial = {"CO2": 0.30, "NH3": 0.40}
    assert_same(v1, "partial phi_prev", phi_prev=partial, dt=1.0)


def test_a_relaxed_film_state_agrees(v1):
    """Two ticks in sequence, so the second sees a film that has genuinely moved."""
    gas, liq = v1["_design_gas"], v1["_design_liq"]
    first = v1["hpcc_322e002"](gas, liq, t_prod_prev=190.0, dt=1.0)
    assert_same(v1, "second tick", phi_prev=first["phi_film"], dt=1.0, t_prod_prev=190.0)


# ======================================================================================
# 5. Off-design feeds
# ======================================================================================

def scaled(stream: dict, key: str, factor: float) -> dict:
    """A copy of a V1 feed dict with its composition vector scaled."""
    out = dict(stream)
    out[key] = {k: v * factor for k, v in stream[key].items()}
    return out


@pytest.mark.parametrize("factor", [0.0, 0.25, 0.5, 0.9, 1.1, 1.5, 3.0])
def test_gas_feed_turndown_agrees(v1, factor):
    """Throughput is what the NTU quench is a function of, so this is the asymptote sweep."""
    assert_same(v1, f"gas x{factor}",
                gas=scaled(v1["_design_gas"], "top_kmolh", factor))


@pytest.mark.parametrize("factor", [0.0, 0.5, 0.9, 1.5, 4.0])
def test_liquid_feed_turndown_agrees(v1, factor):
    """An ejector running slow, which cools the mixed feed as well as thinning it."""
    assert_same(v1, f"liq x{factor}", liq=scaled(v1["_design_liq"], "comp", factor))


def test_both_feeds_lost_agrees(v1):
    """The `m_dot > 1e-9` guard: with nothing arriving, the outlet is the shell."""
    assert_same(v1, "dead",
                gas=scaled(v1["_design_gas"], "top_kmolh", 0.0),
                liq=scaled(v1["_design_liq"], "comp", 0.0))


@pytest.mark.parametrize("t_top", [120.0, 170.0, 187.0, 210.0])
def test_gas_feed_temperature_sweep_agrees(v1, t_top):
    """The sensible term floors at the design outlet, which is a branch in both."""
    gas = dict(v1["_design_gas"])
    gas["T_top"] = t_top
    assert_same(v1, f"T_top={t_top}", gas=gas)


@pytest.mark.parametrize("t_liq", [20.0, 107.5656221649078, 150.0, 178.8])
def test_liquid_feed_temperature_sweep_agrees(v1, t_liq):
    gas = v1["_design_gas"]
    liq = dict(v1["_design_liq"])
    liq["T_C"] = t_liq
    assert_same(v1, f"T_liq={t_liq}", gas=gas, liq=liq)


def test_a_co2_starved_feed_agrees(v1):
    """The ratio clamps, which V1 added because the melt N/C diverges as CO2 goes to zero."""
    for factor in (1e-3, 1e-6, 1e-9, 1e-12, 0.0):
        assert_same(v1, f"CO2 x{factor}",
                    gas=scaled(v1["_design_gas"], "top_kmolh", 1.0),
                    liq=scaled(v1["_design_liq"], "comp", factor))


def test_a_full_upset_state_agrees(v1):
    """Everything off design at once, which is the only test of the interactions."""
    assert_same(v1, "upset",
                gas=scaled(v1["_design_gas"], "top_kmolh", 0.6),
                liq=scaled(v1["_design_liq"], "comp", 1.4),
                t_shell=168.0, gate=0.8, t_prod_prev=196.0, p_loop=131.0, dt=2.0)


# ======================================================================================
# 5. The decided divergence: the azeotropic rise below N/C 3.0 (handoff B-106)
# ======================================================================================

@pytest.mark.parametrize("t_c", [120.0, 170.0, 200.0])
@pytest.mark.parametrize("nc", [3.0, 3.072961, 3.5, 6.0])
def test_at_and_above_the_branch_the_melt_is_v1s(v1, t_c, nc):
    """From N/C 3.0 up the port's default is V1's K_N line, to the bit."""
    hc = 0.39824129577331385
    assert bubble_p_322e002(t_c, nc, hc) == v1["bubble_p_322e002"](t_c, nc, hc)


@pytest.mark.parametrize("nc, v1_bara, port_bara, rise_bar", [
    (2.95, 141.0084, 143.4525, 1.1463), (2.9, 139.7106, 145.3167, 3.0104),
    (2.8, 137.1150, 151.6879, 9.3816), (2.6, 131.9238, 180.3498, 38.0435)])
def test_below_the_branch_the_melt_rises_toward_its_azeotrope_decided_divergence(
        v1, nc, v1_bara, port_bara, rise_bar):
    """Both ways at 170 C on the design H/C and V1's default anchor, the reactor feed's N/C: V1's
    line falls with the N/C, the port's bubble pressure rises on the Extended UNIQUAC model's rise
    (B-106), added in bar to its value at the branch, 142.31 bar a (B-111): at 170 C the rise's
    every bar is a bar of PI-322E002."""
    hc = 0.39824129577331385
    theirs = v1["bubble_p_322e002"](170.0, nc, hc)
    ours = bubble_p_322e002(170.0, nc, hc)
    assert theirs == bubble_p_322e002(170.0, nc, hc, low_nc=False)
    assert theirs == pytest.approx(v1_bara, abs=1e-4)
    assert ours == pytest.approx(port_bara, abs=1e-4)
    assert ours - bubble_p_322e002(170.0, 3.0, hc) == pytest.approx(low_nc_rise(nc), rel=1e-12)
    assert low_nc_rise(nc) == pytest.approx(rise_bar, abs=1e-4)
    assert ours > bubble_p_322e002(170.0, 3.0, hc) > theirs
