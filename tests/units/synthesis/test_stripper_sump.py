"""What the 322E001 bottom sump DOES — behaviour, with no V1 tree required.

Why this is separate from the equivalence suite
-----------------------------------------------
`tests/equivalence/test_stripper_sump_equivalence.py` proves the port is V1. This file proves
the model is a level-controlled sump on a 140 bar letdown. The second question does not need
the V1 tree, so these tests keep running on a machine that has only the rewrite.

Seven behaviours are pinned, each an operating lesson the model exists to teach:

  * the design tick reproduces the licensor balance exactly — 172.0 deg C out, 119.0 deg C to
    323C003, the seal identically 1.0 and the blow-through identically 0.0;
  * LIC-322501 closes correct negative feedback and brings the level back to its set point;
  * the letdown is driven by the LIVE loop pressure, so a depressurised loop drains nothing
    however far the valve is opened — and it flashes, choking on the bottoms' own vapour
    pressure (B-46);
  * a cooling bottom throttles its own outlet, so the level RISES as the drain falls, and
    past a point the valve saturates and the sump floods — the closing-direction runaway;
  * opening LV-322501 raises TT-322004 and throttling it cools the bottoms toward the
    crystallisation floor, which is the mechanism behind the previous bullet;
  * a lost seal converts the drain to gas rather than stopping it — but only in MAN or with
    the controller saturated, because in AUTO the loop shuts the valve first;
  * the bottoms transit moves with flow: a stripper at half rate takes twice as long.
"""

from __future__ import annotations

import math

import pytest

from ureasim.data.unit_320 import SYN_P_DES_BARA
from ureasim.data.unit_322e001 import (
    BOTTOMS_DES_KGH,
    BOTTOMS_TD_DES_S,
    LEVEL_SP_DES_PCT,
    LV_322501_OPEN_DES_PCT,
    T_BOTTOM_DES_C,
    T_CRYSTALLISATION_C,
    T_DOWNSTREAM_DES_C,
    T_STRIPPER_TAU_S,
    TUBES_FULL_KG,
)
from ureasim.units.consequence.seal import expansion_factor
from ureasim.units.synthesis import stripper_sump as ss
from ureasim.units.synthesis.stripper_level import BottomLevelLoop
from ureasim.units.synthesis.stripper_sump import (
    LV_322501_DP_ANCHOR_BAR,
    LV_322501_PV_DES_BARA,
    bottoms_pv_bara,
    StripperSump,
    StripperSumpResult,
    letdown_kgh,
    sump_outlet_temperature_c,
)

# --------------------------------------------------------------------------------------
# The stripper tick the sump consumes, at the licensor balance.
# --------------------------------------------------------------------------------------

#: `stripper.stripper_322e001` at design, in the five pieces the sump reads. The bottoms
#: flow is the stripper's own 130 480 kg/h, which is 2 kg/h under the 130 482 kg/h PFD
#: anchor the letdown law is normalised on — see `test_the_design_tick_is_the_licensor_state`.
DESIGN = dict(bottoms_kgh=130480.0, t_bot_c=T_BOTTOM_DES_C, t_steam_c=211.62164907088414,
              top_mw=25.963686431610723,
              top_kmolh={"NH3": 3571.6015782, "CO2": 1734.0, "H2O": 483.8},
              bot_mass_pct=dict(ss._BOTTOMS_DES.bot_mass_pct))


def run(n: int = 1, dt: float = 1.0, level0: float = LEVEL_SP_DES_PCT,
        mode: str = "AUTO", sp: float = LEVEL_SP_DES_PCT,
        op0: float = LV_322501_OPEN_DES_PCT, syn_bara: float = SYN_P_DES_BARA,
        tube_ceiling: bool = True,
        **strip) -> tuple[StripperSumpResult, StripperSump, BottomLevelLoop]:
    """Run the sump for `n` ticks and return the last result with both state objects."""
    tick = dict(DESIGN)
    tick.update(strip)
    sump = StripperSump(level_pct=level0, tube_ceiling=tube_ceiling)
    lic = BottomLevelLoop(op=op0, sp=sp, pv=level0, mode=mode)
    result = None
    for _ in range(n):
        result = sump.step(lic, tick["bottoms_kgh"], tick["t_bot_c"], tick["t_steam_c"],
                           tick["top_kmolh"], tick["top_mw"], syn_bara, tick["bot_mass_pct"],
                           dt)
    return result, sump, lic


# ======================================================================================
# 1. The design anchor
# ======================================================================================

def test_the_design_tick_is_the_licensor_state():
    """Every anchored quantity lands on its PFD value, and three of them land exactly."""
    result, _, _ = run()
    assert result.lv_opening_pct == LV_322501_OPEN_DES_PCT
    assert result.drain_kgh == BOTTOMS_DES_KGH          # exactly: both ratios are exactly 1
    assert result.mushy_factor == 1.0
    assert result.seal_fraction == 1.0
    assert result.blowthrough_kgh == 0.0
    assert result.t_out_c == T_BOTTOM_DES_C             # exactly: r = 1 collapses the balance
    assert result.tt_322004_c == T_BOTTOM_DES_C
    assert result.tt_323001_c == T_DOWNSTREAM_DES_C     # exactly: the gain multiplies zero
    assert result.dp_lv_bar == LV_322501_DP_ANCHOR_BAR
    assert result.bottoms_dead_time_s == pytest.approx(BOTTOMS_TD_DES_S, rel=1e-4)
    assert result.solidification is False
    assert result.lv_erosion is False


def test_the_design_sump_carries_a_two_kilogram_imbalance_and_no_more():
    """The stripper's split gives 130 480 kg/h against the 130 482 kg/h letdown anchor.

    Two numbers from two different places in the licensor package, agreeing to 15 ppm. It is
    worth pinning rather than hiding, because it means the design sump is not EXACTLY in
    balance: the level falls at 0.025 % per hour with the controller in MAN. In AUTO the loop
    absorbs it with a 0.001 % stroke change and it is unobservable.
    """
    result, sump, _ = run(mode="MAN")
    assert result.drain_kgh - result.bottoms_in_kgh == pytest.approx(2.0, abs=0.01)
    drift_pct_per_hour = (sump.level_pct - LEVEL_SP_DES_PCT) * 3600.0
    assert drift_pct_per_hour == pytest.approx(-0.025, abs=0.002)


def test_the_design_state_is_a_fixed_point_of_the_closed_loop():
    """An hour in AUTO at design does not move the level off its set point."""
    _, sump, lic = run(n=3600)
    assert sump.level_pct == pytest.approx(LEVEL_SP_DES_PCT, abs=0.01)
    assert lic.op == pytest.approx(LV_322501_OPEN_DES_PCT, abs=0.05)


# ======================================================================================
# 2. LIC-322501
# ======================================================================================

@pytest.mark.parametrize("level0", [20.0, 35.0, 65.0, 80.0])
def test_the_loop_brings_the_level_back_to_its_set_point(level0):
    """Direct acting on an air-to-open valve is correct negative feedback, both ways.

    On the plant DCS's tuning (0.20 and 280 s, decided 2026-10-08) the loop is slow and
    underdamped: from 20 % the level overshoots to 61.5 % and settles inside 0.05 % of its set
    point in 6,387 s, where V1's 2.5 and 90 s settled inside 4,000 s."""
    _, sump, _ = run(n=6400, level0=level0)
    assert sump.level_pct == pytest.approx(LEVEL_SP_DES_PCT, abs=0.05)


def test_a_high_level_opens_the_valve_and_a_low_level_shuts_it():
    """The sign of the action, stated on its own so a direction slip cannot hide in a settle."""
    high, _, _ = run(level0=70.0)
    low, _, _ = run(level0=30.0)
    assert high.lv_opening_pct > LV_322501_OPEN_DES_PCT
    assert low.lv_opening_pct < LV_322501_OPEN_DES_PCT
    assert high.drain_kgh > BOTTOMS_DES_KGH > low.drain_kgh


def test_manual_mode_freezes_the_output_but_keeps_tracking_the_error():
    """Which is what makes the return to AUTO bumpless rather than a step out of the valve.

    The tracked error is one tick behind the published PV, and that is the declared tear
    rather than a rounding artefact: the controller acts on the level at the TOP of a tick
    and the faceplate is written from the level at the BOTTOM of it.
    """
    _, sump, lic = run(n=50, level0=70.0, mode="MAN")
    assert lic.op == LV_322501_OPEN_DES_PCT
    published = lic.pv
    sump.step(lic, DESIGN["bottoms_kgh"], DESIGN["t_bot_c"], DESIGN["t_steam_c"],
              DESIGN["top_kmolh"], DESIGN["top_mw"], SYN_P_DES_BARA, DESIGN["bot_mass_pct"], 1.0)
    assert lic.e_prev == published - lic.sp


def test_the_output_cannot_leave_its_own_span():
    """A sustained excursion saturates the stroke at a rail rather than winding past it.

    It takes an excursion the valve cannot answer. A one-off level offset does not do it —
    the loop simply corrects it, which is the test above — so the high rail is driven by a
    bottoms flow larger than a fully open LV-322501 can pass, and the low rail by no bottoms
    flow at all. On the DCS's tuning the rails take 1,250 s and 1,072 s to reach.
    """
    _, flooded, wide = run(n=1400, bottoms_kgh=500_000.0)
    assert wide.op == 100.0
    assert flooded.level_pct == 100.0

    _, _, shut = run(n=1400, bottoms_kgh=0.0)
    assert shut.op == 0.0


def test_a_bad_level_freezes_the_loop_instead_of_latching_it():
    """The contrast with V1's PIC-322203, which does not manage this (As-Built §XVII.5)."""
    _, sump, lic = run(n=20, level0=62.0)
    op_before, e_before = lic.op, lic.e_prev
    sump.level_pct = float("nan")
    sump.step(lic, DESIGN["bottoms_kgh"], DESIGN["t_bot_c"], DESIGN["t_steam_c"],
              DESIGN["top_kmolh"], DESIGN["top_mw"], SYN_P_DES_BARA, DESIGN["bot_mass_pct"], 1.0)
    assert lic.pv_bad is True
    assert lic.op == op_before
    assert lic.e_prev == e_before


# ======================================================================================
# 3. The letdown law
# ======================================================================================

def test_the_letdown_is_linear_in_the_stroke():
    """Linear trim, so the operator's hand movement maps to flow one for one."""
    half = letdown_kgh(LV_322501_OPEN_DES_PCT / 2.0, SYN_P_DES_BARA, LV_322501_PV_DES_BARA)
    assert half == pytest.approx(BOTTOMS_DES_KGH / 2.0, rel=1e-12)
    assert letdown_kgh(0.0, SYN_P_DES_BARA, LV_322501_PV_DES_BARA) == 0.0


def test_the_letdown_chokes_on_the_bottoms_vapour_pressure():
    """B-46. The design bottoms boil at 101.4 bar a: the choked differential, 0.845 x (140.7 -
    FF . 101.4) = 52.9 bar, not the 136.7 bar across the valve, sets the flow. So the bottoms'
    vapour pressure moves the drain — 10 % more Pv, 5.6 % less flow — and what is downstream
    does not."""
    assert bottoms_pv_bara(DESIGN["bot_mass_pct"], T_BOTTOM_DES_C) == LV_322501_PV_DES_BARA
    assert LV_322501_PV_DES_BARA == pytest.approx(101.431, abs=1e-3)
    ff = 0.96 - 0.28 * math.sqrt(LV_322501_PV_DES_BARA / 220.64)
    assert 0.845 * (SYN_P_DES_BARA - ff * LV_322501_PV_DES_BARA) == pytest.approx(52.88, abs=0.01)
    wetter = letdown_kgh(LV_322501_OPEN_DES_PCT, SYN_P_DES_BARA, 1.1 * LV_322501_PV_DES_BARA)
    assert wetter / BOTTOMS_DES_KGH == pytest.approx(0.9443, abs=1e-4)
    hotter = bottoms_pv_bara(DESIGN["bot_mass_pct"], T_BOTTOM_DES_C + 5.0)
    assert hotter > LV_322501_PV_DES_BARA


@pytest.mark.parametrize("syn_bara", [0.0, 1.013, 3.0, 3.999, 4.0])
def test_a_depressurised_loop_drains_nothing(syn_bara):
    """The start-up lesson: LV-322501 is a letdown, not a gravity drain.

    At or below the downstream reference there is no head, so the valve can be wide open and
    pass nothing. A frozen design differential would have the sump emptying itself into an
    unpressurised LP section on every black start.
    """
    result, sump, _ = run(n=10, level0=80.0, syn_bara=syn_bara, mode="MAN", op0=100.0)
    assert result.dp_lv_bar == 0.0
    assert result.drain_kgh == 0.0
    assert sump.level_pct > 80.0          # the bottoms keep arriving and nothing leaves


def test_the_live_head_is_what_moves_the_product():
    """A loop running 3 bar low delivers 2.4 % less at the same stroke — on the choked
    differential, twice the 1.1 % V1's full-differential law gives (B-46)."""
    low = letdown_kgh(LV_322501_OPEN_DES_PCT, SYN_P_DES_BARA - 3.0, LV_322501_PV_DES_BARA)
    ff = 0.96 - 0.28 * math.sqrt(LV_322501_PV_DES_BARA / 220.64)
    assert low / BOTTOMS_DES_KGH == pytest.approx(
        ((SYN_P_DES_BARA - 3.0 - ff * LV_322501_PV_DES_BARA)
         / (SYN_P_DES_BARA - ff * LV_322501_PV_DES_BARA)) ** 0.5, rel=1e-12)
    assert 0.975 < low / BOTTOMS_DES_KGH < 0.977
    assert (1.0 - 3.0 / LV_322501_DP_ANCHOR_BAR) ** 0.5 == pytest.approx(0.989, abs=1e-3)


# ======================================================================================
# 4. The mushy zone, and the closing-direction runaway
# ======================================================================================

def test_a_cooling_bottom_throttles_its_own_outlet():
    """Inside the band the drain is restricted and the flag is raised. The colder bottoms boil
    lower, 40.2 bar a, so the valve's choke relaxes (B-46): what the band restricts is a letdown
    1.31 times the design one."""
    t_bot_c = T_CRYSTALLISATION_C + 2.0
    result, _, _ = run(t_bot_c=t_bot_c, mode="MAN")
    assert result.mushy_factor == pytest.approx(0.4)
    relaxed = letdown_kgh(LV_322501_OPEN_DES_PCT, SYN_P_DES_BARA,
                          bottoms_pv_bara(DESIGN["bot_mass_pct"], t_bot_c))
    assert relaxed / BOTTOMS_DES_KGH == pytest.approx(1.3071, abs=1e-4)
    assert result.drain_kgh == pytest.approx(0.4 * relaxed, rel=1e-12)
    assert result.solidification is True


def test_the_loop_compensates_a_mild_restriction_by_opening_the_valve():
    """At 136 deg C the factor is 0.66 and LIC-322501 simply strokes further open.

    This is the recoverable half of the excursion, and the operator sees it as a valve
    position that has drifted away from normal at an apparently normal flow. The colder
    bottoms boil at 41.9 bar a, so the choke relaxes 1.30 times (B-46) and the stroke settles
    at 53.8 %, not the 70 % the restriction alone would ask.
    """
    result, sump, lic = run(n=8000, t_bot_c=136.0)
    assert result.mushy_factor == pytest.approx(0.66, abs=0.01)
    relax = letdown_kgh(LV_322501_OPEN_DES_PCT, SYN_P_DES_BARA,
                        bottoms_pv_bara(DESIGN["bot_mass_pct"], 136.0)) / BOTTOMS_DES_KGH
    assert lic.op == pytest.approx(LV_322501_OPEN_DES_PCT / (0.66 * relax), rel=0.01)
    assert lic.op > 1.15 * LV_322501_OPEN_DES_PCT
    assert result.drain_kgh == pytest.approx(DESIGN["bottoms_kgh"], rel=0.01)
    assert sump.level_pct == pytest.approx(LEVEL_SP_DES_PCT, abs=0.5)


def test_past_the_valve_rail_the_sump_floods():
    """At 134 deg C the factor is 0.26, the stroke saturates and the level goes to the top.

    The un-drained mass has nowhere to go but the level ODE, so the level rises — which is
    the signature an operator gets minutes before the line stops moving, and the reason the
    restriction is modelled as a flow factor rather than as a trip. Wide open on the relaxed
    choke (B-46) the valve passes 74 % of the bottoms, and the rest floods the sump (in 1,317 s
    on the DCS's tuning).
    """
    result, sump, lic = run(n=1400, t_bot_c=134.0)
    assert result.mushy_factor == pytest.approx(0.26, abs=0.01)
    assert lic.op == 100.0
    assert sump.level_pct == 100.0
    assert result.drain_kgh < 0.75 * BOTTOMS_DES_KGH


def test_the_restriction_is_reversible():
    """Warming the bottoms back up restores the drain with no latch and no reset."""
    sump = StripperSump(level_pct=LEVEL_SP_DES_PCT)
    lic = BottomLevelLoop(op=LV_322501_OPEN_DES_PCT, mode="MAN")

    def tick(t_bot_c):
        return sump.step(lic, DESIGN["bottoms_kgh"], t_bot_c, DESIGN["t_steam_c"],
                         DESIGN["top_kmolh"], DESIGN["top_mw"], SYN_P_DES_BARA,
                         DESIGN["bot_mass_pct"], 1.0)

    assert tick(T_BOTTOM_DES_C).drain_kgh == BOTTOMS_DES_KGH
    assert tick(134.0).solidification is True
    recovered = tick(T_BOTTOM_DES_C)
    assert recovered.solidification is False
    assert recovered.drain_kgh == BOTTOMS_DES_KGH


# ======================================================================================
# 5. The sump energy balance
# ======================================================================================

def test_more_drain_is_hotter_and_less_drain_is_colder():
    """The sign is structural: dT/dr is tau(1+tau)(T_bot - T_amb)/(r+tau)^2, always positive."""
    temperatures = [sump_outlet_temperature_c(T_BOTTOM_DES_C, 211.6, r * BOTTOMS_DES_KGH)
                    for r in (0.1, 0.2, 0.5, 1.0, 1.5, 3.0, 20.0)]
    assert all(b > a for a, b in zip(temperatures, temperatures[1:]))


def test_the_design_drain_returns_the_design_bottoms_exactly():
    """r = 1 collapses the closed form, which is what keeps the licensor balance bit-exact."""
    assert sump_outlet_temperature_c(T_BOTTOM_DES_C, 211.6, BOTTOMS_DES_KGH) \
        == T_BOTTOM_DES_C


def test_a_throttled_sump_cools_toward_the_crystallisation_floor():
    """Which closes the loop with the mushy zone: throttling is self-reinforcing."""
    nearly_shut = sump_outlet_temperature_c(T_BOTTOM_DES_C, 211.6, 0.01 * BOTTOMS_DES_KGH)
    assert T_CRYSTALLISATION_C < nearly_shut < T_BOTTOM_DES_C
    assert sump_outlet_temperature_c(T_BOTTOM_DES_C, 211.6, 0.0) == T_CRYSTALLISATION_C


def test_the_film_temperature_is_the_open_valve_asymptote():
    """Wide open, the sump has no residence time left and the outlet reaches the film."""
    wide = sump_outlet_temperature_c(T_BOTTOM_DES_C, 211.6, 1e6 * BOTTOMS_DES_KGH)
    assert wide == pytest.approx(176.0, abs=0.05)


def test_the_bottoms_can_never_out_heat_the_condensing_shell():
    """A real cap, not an unreachable guard: it binds above about 205 deg C of film feed."""
    t_steam = 211.62164907088414
    assert sump_outlet_temperature_c(200.0, t_steam, 20.0 * BOTTOMS_DES_KGH) < t_steam
    assert sump_outlet_temperature_c(208.0, t_steam, 20.0 * BOTTOMS_DES_KGH) == t_steam


def test_below_the_floor_the_energy_balance_is_bypassed():
    """A cold start has no hot-film residence effect, so the film passes straight through."""
    assert sump_outlet_temperature_c(T_CRYSTALLISATION_C, 211.6, 0.5 * BOTTOMS_DES_KGH) \
        == T_CRYSTALLISATION_C
    assert sump_outlet_temperature_c(25.0, 211.6, 0.5 * BOTTOMS_DES_KGH) == 25.0


def test_tt_323001_tracks_the_bottoms_at_the_flash_gain():
    """The 323C003 inlet moves 0.7 deg C for every 1 deg C at TT-322004."""
    hot, _, _ = run(n=200, t_bot_c=180.0, mode="MAN")
    assert hot.tt_323001_c - T_DOWNSTREAM_DES_C \
        == pytest.approx(0.7 * (hot.t_out_c - T_BOTTOM_DES_C), rel=1e-12)
    assert hot.tt_323001_c > T_DOWNSTREAM_DES_C


def test_the_published_temperature_lags_the_computed_one():
    """The 180 s constant is the stripper's own liquid holdup plus HP shell metal.

    The lag is lazy-initialised to its first sample, so it shows against a CHANGE and never
    as a boot transient — which is part of what keeps the design seed pinned.
    """
    sump = StripperSump()
    lic = BottomLevelLoop(op=LV_322501_OPEN_DES_PCT, mode="MAN")

    def tick(t_bot_c):
        return sump.step(lic, DESIGN["bottoms_kgh"], t_bot_c, DESIGN["t_steam_c"],
                         DESIGN["top_kmolh"], DESIGN["top_mw"], SYN_P_DES_BARA,
                         DESIGN["bot_mass_pct"], 1.0)

    assert tick(T_BOTTOM_DES_C).tt_322004_c == T_BOTTOM_DES_C     # no boot transient

    # Step the bottoms 8 deg C and follow the published measurement up the exponential. The
    # hotter bottoms boil higher and choke the drain to 92.5 % (B-46), so the sump outlet
    # settles at 179.65 deg C, a little under the film.
    results = [tick(180.0) for _ in range(400)]
    trace = [r.tt_322004_c for r in results]
    step = results[0].t_out_c - 172.0
    assert results[0].t_out_c == pytest.approx(179.648, abs=0.001)
    assert trace[0] == pytest.approx(172.0 + step / (T_STRIPPER_TAU_S + 1.0), abs=0.001)
    assert trace[179] == pytest.approx(172.0 + step * (1.0 - math.exp(-1.0)), abs=0.05)
    assert trace[399] == pytest.approx(178.81, abs=0.05)
    assert all(b >= a for a, b in zip(trace, trace[1:]))


# ======================================================================================
# 6. The lost seal
# ======================================================================================

def test_in_auto_an_emptied_sump_blows_through_until_its_seal_recovers():
    """On the plant DCS's tuning (0.20 and 280 s, decided 2026-10-08) the loop is too gentle to
    shut the valve on an emptied sump: its first tick strokes LV-322501 from 46.1 to 36.1 %, the
    uncovered nozzle passes 19.8 t/h of gas into 323C003, and only the bottoms re-covering the
    seal stop it — 28 kg in 14 s. V1's 2.5 and 90 s shut the valve in two ticks and nothing blew.
    """
    result, _, lic = run(n=1, level0=0.0)
    assert lic.op == pytest.approx(36.06, abs=0.01)
    assert result.blowthrough_kgh == pytest.approx(19_833.0, abs=1.0)
    assert result.lv_erosion is True
    result, sump, lic = run(n=14, level0=0.0)
    assert result.blowthrough_kgh == 0.0 and lic.op > 30.0


@pytest.mark.parametrize("level0,expected_seal", [(2.0, 2.0 / 3.0), (1.5, 0.5),
                                                  (0.5, 1.0 / 6.0), (0.0, 0.0)])
def test_in_manual_a_lost_seal_converts_the_drain_to_gas(level0, expected_seal):
    """Liquid falls with the seal and gas rises with what is left of the nozzle."""
    result, _, _ = run(level0=level0, mode="MAN", syn_bara=144.0)
    assert result.seal_fraction == pytest.approx(expected_seal)
    assert result.drain_kgh == pytest.approx(expected_seal * 133878.0, rel=1e-4)
    assert result.blowthrough_kgh > 0.0
    assert result.lv_erosion is True


def test_the_fully_uncovered_nozzle_passes_twenty_five_tonnes_an_hour():
    """The derived rate, against the 25 t/h that had been hand-entered for this valve in V1."""
    result, _, _ = run(level0=0.0, mode="MAN")
    assert result.drain_kgh == 0.0
    assert result.blowthrough_kgh == pytest.approx(25_350.0, rel=0.01)


def test_the_blow_through_is_choked_at_every_normal_loop_pressure():
    """So the LP section's own pressure has dropped out of the answer entirely.

    That is what the ceiling means, and it is the difference between a trainable upset and a
    numerical explosion downstream: blowing 323C003 down does not pull more gas through
    LV-322501. What still moves the rate is the UPSTREAM side, and it moves it roughly in
    proportion, because the choked effective drop and the gas density are both linear in the
    loop pressure. The rise is slightly steeper than linear because the compressibility falls
    as the loop is pushed up.
    """
    y, dp_eff_bar, choked = expansion_factor(LV_322501_DP_ANCHOR_BAR, SYN_P_DES_BARA)
    assert choked is True
    assert y == pytest.approx(2.0 / 3.0)
    assert dp_eff_bar < LV_322501_DP_ANCHOR_BAR    # the valve never sees the full 136.7 bar

    at_design, _, _ = run(level0=0.0, mode="MAN")
    higher, _, _ = run(level0=0.0, mode="MAN", syn_bara=148.0)
    assert higher.blowthrough_kgh > at_design.blowthrough_kgh
    linear = 148.0 / SYN_P_DES_BARA
    assert higher.blowthrough_kgh / at_design.blowthrough_kgh \
        == pytest.approx(linear, abs=0.02)
    assert higher.blowthrough_kgh / at_design.blowthrough_kgh > linear


# ======================================================================================
# 7. The bottoms transit
# ======================================================================================

@pytest.mark.parametrize("scale,expected_s", [(1.0, 60.0), (0.5, 120.0), (0.25, 240.0),
                                              (2.0, 30.0)])
def test_the_transit_moves_with_flow(scale, expected_s):
    """rho.V/m_dot. A stripper at half rate takes twice as long to fill the sump line."""
    result, _, _ = run(bottoms_kgh=BOTTOMS_DES_KGH * scale, mode="MAN")
    assert result.bottoms_dead_time_s == pytest.approx(expected_s, rel=1e-3)


def test_a_stalled_line_gives_a_long_but_finite_delay():
    """Capped, so an empty stripper does not allocate an unbounded FIFO."""
    result, _, _ = run(bottoms_kgh=0.0, mode="MAN")
    assert result.bottoms_dead_time_s == 3600.0


def test_the_sump_sees_a_step_only_after_the_line_has_emptied():
    """A cut in the stripper's bottoms takes a minute to reach the level measurement."""
    sump = StripperSump(level_pct=LEVEL_SP_DES_PCT)
    lic = BottomLevelLoop(op=LV_322501_OPEN_DES_PCT, mode="MAN")

    def tick(bottoms_kgh):
        return sump.step(lic, bottoms_kgh, DESIGN["t_bot_c"], DESIGN["t_steam_c"],
                         DESIGN["top_kmolh"], DESIGN["top_mw"], SYN_P_DES_BARA,
                         DESIGN["bot_mass_pct"], 1.0)

    for _ in range(120):
        tick(DESIGN["bottoms_kgh"])
    halved = DESIGN["bottoms_kgh"] / 2.0
    # The transit at the reduced flow is 120 s, so nothing has changed at the sump yet.
    for _ in range(100):
        arriving = tick(halved).bottoms_in_kgh
    assert arriving == pytest.approx(DESIGN["bottoms_kgh"], rel=1e-12)
    for _ in range(60):
        arriving = tick(halved).bottoms_in_kgh
    assert arriving == pytest.approx(halved, rel=1e-12)


# ======================================================================================
# 8. The level state
# ======================================================================================

def test_the_level_cannot_leave_its_own_span():
    """Both rails, because a level outside [0, 100] is not a measurement the DCS can show."""
    _, flooded, _ = run(n=50, dt=5.0, level0=99.9, mode="MAN", op0=0.0,
                        bottoms_kgh=500_000.0)
    assert flooded.level_pct == 100.0
    _, emptied, _ = run(n=50, dt=5.0, level0=0.1, mode="MAN", op0=100.0, bottoms_kgh=0.0)
    assert emptied.level_pct == 0.0


def test_a_full_sump_holds_its_excess_back_in_the_tubes():
    """B-103, decided 2026-10-21 (decision 62's class): LV-322501 shut and 500 t/h of bottoms
    for 250 s. LT-322501 reads 100 %, and every kilogram the full sump cannot take is held back
    in the tubes above it — what the sump and the tubes gained is what ran in. V1's clamp, the
    switch off, deletes it. Without the tubes' ceiling (B-104, its own test below)."""
    result, flooded, _ = run(n=50, dt=5.0, level0=99.9, mode="MAN", op0=0.0,
                             bottoms_kgh=500_000.0, tube_ceiling=False)
    span_kg = ss.SUMP_SPAN_KG
    assert flooded.level_pct == 100.0 and result.held_kg == flooded.held_kg > 0.0
    # The bottoms line delivers its design flow until the step has crossed it; what it delivered
    # over the run is in the sump or above it.
    assert result.dm_kgh == pytest.approx(result.bottoms_in_kgh, rel=1e-9)
    gained = flooded.level_pct / 100.0 * span_kg + flooded.held_kg - 0.999 * span_kg
    assert 0.0 < gained < 500_000.0 * 250.0 / 3600.0
    sump = StripperSump(level_pct=99.9, hold_full=False)
    lic = BottomLevelLoop(op=0.0, mode="MAN")
    for _ in range(50):
        r = sump.step(lic, 500_000.0, DESIGN["t_bot_c"], DESIGN["t_steam_c"], DESIGN["top_kmolh"],
                      DESIGN["top_mw"], SYN_P_DES_BARA, DESIGN["bot_mass_pct"], 5.0)
    assert (sump.level_pct, sump.held_kg, r.held_kg, r.dm_kgh) == (100.0, 0.0, 0.0, 0.0)


def test_the_tubes_hold_no_more_than_their_standing_full_liquor():
    """B-104, decided 2026-10-22: the liquor held back above a full sump is capped at the tubes
    standing full, 8 689 kg; what still arrives is handed back to 322R001, and the room the tubes
    publish for HV-322605 is the drain alone. The same run as above: the tubes fill and stay full,
    and the sump's gain and what it handed back are what ran in."""
    result, flooded, _ = run(n=50, dt=5.0, level0=99.9, mode="MAN", op0=0.0,
                             bottoms_kgh=500_000.0)
    assert (flooded.level_pct, flooded.held_kg) == (100.0, TUBES_FULL_KG)
    assert result.held_kg == TUBES_FULL_KG and result.drain_kgh == 0.0
    assert result.backup_kgh > 0.0
    assert result.backup_kgh == pytest.approx(result.bottoms_in_kgh, rel=1e-9)
    assert result.dm_kgh == pytest.approx(0.0, abs=1e-6)
    assert result.take_kgh == 0.0


def test_the_tubes_take_the_drain_and_their_unsubmerged_share_of_the_design_bottoms():
    """With no liquor held the tubes bound nothing; holding some, they take the drain and their
    unsubmerged share of the design bottoms, so HV-322605 eases off as they fill. Without the
    ceiling, B-103's, nothing is published."""
    result, _, _ = run()
    assert (result.held_kg, result.backup_kgh, result.take_kgh) == (0.0, 0.0, None)
    sump = StripperSump(level_pct=100.0, held_kg=0.25 * TUBES_FULL_KG)
    lic = BottomLevelLoop(op=LV_322501_OPEN_DES_PCT, mode="MAN")
    r = sump.step(lic, BOTTOMS_DES_KGH, DESIGN["t_bot_c"], DESIGN["t_steam_c"], DESIGN["top_kmolh"],
                  DESIGN["top_mw"], SYN_P_DES_BARA, DESIGN["bot_mass_pct"], 1.0)
    assert r.take_kgh == pytest.approx(
        r.drain_kgh + (1.0 - r.held_kg / TUBES_FULL_KG) * BOTTOMS_DES_KGH, rel=1e-12)
    result, _, _ = run(tube_ceiling=False)
    assert (result.backup_kgh, result.take_kgh) == (0.0, None)


def test_a_drained_sump_fills_its_tubes_to_the_ceiling_and_passes_what_drains():
    """The sump with LV-322501 at 10 % and the stripper's feed capped at what the tubes take (the
    reactor's bound, one kilogram of bottoms per kilogram taken): the tubes fill to their 8 689 kg
    in about ten minutes, what the transit still delivers past the ceiling, 2 505 kg, is handed
    back, and then the tubes take exactly what drains."""
    sump = StripperSump(level_pct=99.9)
    lic = BottomLevelLoop(op=10.0, mode="MAN")
    bottoms, back = BOTTOMS_DES_KGH - 2.0, 0.0
    tick = (DESIGN["t_bot_c"], DESIGN["t_steam_c"], DESIGN["top_kmolh"], DESIGN["top_mw"],
            SYN_P_DES_BARA, DESIGN["bot_mass_pct"], 1.0)
    for _ in range(2000):
        r = sump.step(lic, bottoms, *tick)
        back += r.backup_kgh / 3600.0
        bottoms = (BOTTOMS_DES_KGH - 2.0 if r.take_kgh is None
                   else min(BOTTOMS_DES_KGH - 2.0, max(r.take_kgh, 0.0)))
    assert sump.held_kg == TUBES_FULL_KG
    assert back == pytest.approx(2505.3, abs=0.1)
    assert r.take_kgh == r.drain_kgh == pytest.approx(28304.1, abs=0.1)
    assert r.bottoms_in_kgh == pytest.approx(r.drain_kgh, rel=1e-9)


def test_held_liquor_runs_down_before_the_level_falls():
    """What the tubes held back drains first: the level stays at 100 % until it is gone."""
    sump = StripperSump(level_pct=100.0, held_kg=1000.0)
    lic = BottomLevelLoop(op=LV_322501_OPEN_DES_PCT, mode="MAN")
    tick = (DESIGN["t_bot_c"], DESIGN["t_steam_c"], DESIGN["top_kmolh"], DESIGN["top_mw"],
            SYN_P_DES_BARA, DESIGN["bot_mass_pct"], 1.0)
    r = sump.step(lic, 0.0, *tick)
    assert sump.level_pct == 100.0
    assert sump.held_kg == pytest.approx(1000.0 - r.drain_kgh / 3600.0, rel=1e-12)
    assert r.dm_kgh == pytest.approx(-r.drain_kgh, rel=1e-9)


def test_the_level_integrates_the_real_net_flow():
    """Finding A-3: no fitted fill gate deleting most of the net inflow.

    One tick of a 36 000 kg/h surplus into a 7893 kg span is 0.127 % of level, which is the
    arithmetic and nothing else.
    """
    span_kg = 4.638 * 1.5 * 1134.64
    sump = StripperSump(level_pct=LEVEL_SP_DES_PCT)
    lic = BottomLevelLoop(op=LV_322501_OPEN_DES_PCT, mode="MAN")
    surplus = BOTTOMS_DES_KGH + 36_000.0
    result = sump.step(lic, surplus, DESIGN["t_bot_c"], DESIGN["t_steam_c"],
                       DESIGN["top_kmolh"], DESIGN["top_mw"], SYN_P_DES_BARA,
                       DESIGN["bot_mass_pct"], 1.0)
    expected = LEVEL_SP_DES_PCT + (result.bottoms_in_kgh - result.drain_kgh) \
        / 3600.0 / span_kg * 100.0
    assert sump.level_pct == pytest.approx(expected, rel=1e-12)
