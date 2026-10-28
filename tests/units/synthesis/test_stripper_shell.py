"""322E001's shell: the split's enthalpy balance, the shell's duty bound (handoff B-102) and the
tubes standing full (handoff B-104).

What the module does, without a V1 tree: the LMTD and its design anchor, the capacity ratio on the
live steam, the lifted split's conservation and its two ends, the bisection meeting its target, and
the submerged share's derate and its cooled bottoms.
The bound against V1's unbounded split, both ways, is `tests/equivalence/test_stripper_equivalence`
section 5.
"""

from __future__ import annotations

import math

import pytest

from ureasim.core.stream import MW_COMP
from ureasim.data import unit_322e001 as d
from ureasim.data.unit_321 import CO2_DES_KGH
from ureasim.thermo import iapws
from ureasim.units.synthesis.stripper import DUTY_RAW_DES_KW, stripper_322e001
from ureasim.units.synthesis.stripper_shell import (
    LIFTED,
    LMTD_DES_K,
    bounded_split,
    enthalpy_balance,
    lifted_split,
    shell_capacity_ratio,
    shell_lmtd_k,
    submerged_bottoms_c,
    submerged_fraction,
    unsubmerged_factor,
)

CO2_DES_TH = CO2_DES_KGH / 1000.0


def _overloaded():
    """The stripper fed 1.3 times the design overflow, its split unbounded."""
    overflow = {k: v * 1.3 for k, v in d.FEED_207_KMOLH.items()}
    return stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA, overflow_kmolh=overflow,
                            shell_bound=False)


def test_the_design_lmtd_is_the_datasheet_profile_on_the_models_steam():
    """211.62 C steam on a tube side from 187 to 172 C: 24.62 and 39.62 K at the ends, 31.53 K."""
    assert LMTD_DES_K == pytest.approx(31.5292, abs=1e-4)
    d_top = d.STEAM_T_DES_C - d.T_TOPGAS_DES_C
    d_bot = d.STEAM_T_DES_C - d.T_BOTTOM_DES_C
    assert LMTD_DES_K == (d_bot - d_top) / math.log(d_bot / d_top)


def test_the_lmtd_is_its_end_difference_when_the_two_are_equal_and_finite_at_the_shell():
    assert shell_lmtd_k(200.0, 180.0, 180.0) == 20.0
    # A tube end at the shell's temperature transfers nothing, and the floor keeps it finite.
    assert 0.0 < shell_lmtd_k(187.0, 187.0, 172.0) < 6.0


def test_the_capacity_moves_with_the_steam_alone():
    """Exactly 1.0 on the design steam; a sagging header gives less, a raised one more."""
    assert shell_capacity_ratio(d.STEAM_T_DES_C) == 1.0
    assert shell_capacity_ratio(iapws.tsat_c(18.9)) == pytest.approx(0.9327, abs=1e-4)
    assert shell_capacity_ratio(iapws.tsat_c(20.5)) == pytest.approx(1.0650, abs=1e-4)


def test_the_balance_is_the_stripper_s_own():
    """`enthalpy_balance` on the stripper's design split returns its published terms exactly."""
    r = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA)
    b = enthalpy_balance(r.top_kmolh, r.bot_kmolh, r.co2_feed_kmolh, r.xi_hydrolysis, r.t_bot,
                         r.t_top, r.t_feed)
    assert (b.total_kw, b.q_carbamate_kw, b.q_sensible_kw) == (
        r.duty_raw_kw, r.q_carbamate_kw, r.q_sensible_kw)
    assert b.total_kw == DUTY_RAW_DES_KW


def test_the_lifted_split_moves_mass_and_makes_none():
    """lambda 1 is the split itself, lambda 0 lifts only the sweep; every total is kept."""
    r = _overloaded()
    top1, bot1 = lifted_split(r.top_kmolh, r.bot_kmolh, r.co2_feed_kmolh, 1.0)
    assert (top1, bot1) == (r.top_kmolh, r.bot_kmolh)
    top0, bot0 = lifted_split(r.top_kmolh, r.bot_kmolh, r.co2_feed_kmolh, 0.0)
    for k in MW_COMP:
        assert top0[k] + bot0[k] == pytest.approx(r.top_kmolh[k] + r.bot_kmolh[k], rel=1e-14)
        if k in LIFTED:
            assert top0[k] == min(r.top_kmolh[k], r.co2_feed_kmolh[k])
        else:
            assert (top0[k], bot0[k]) == (r.top_kmolh[k], r.bot_kmolh[k])


def test_the_bisection_meets_the_shell_s_capacity():
    """1.3 times the overflow asks 1.35 design duties; V1's bundle's shell gives 1 . (1 + band),
    the replacement's 1.142 . (1 + band) (decision 154), lambda 0.847."""
    r = _overloaded()
    target = DUTY_RAW_DES_KW * (1.0 + d.SHELL_DUTY_BAND)
    assert r.duty_raw_kw / DUTY_RAW_DES_KW == pytest.approx(1.3517, abs=1e-4)
    lam, top, bot = bounded_split(r.top_kmolh, r.bot_kmolh, r.co2_feed_kmolh, r.xi_hydrolysis,
                                  r.t_bot, r.t_top, r.t_feed, target)
    assert lam == pytest.approx(0.743091, abs=1e-6)
    b = enthalpy_balance(top, bot, r.co2_feed_kmolh, r.xi_hydrolysis, r.t_bot, r.t_top, r.t_feed)
    assert b.total_kw == pytest.approx(target, rel=1e-12)
    overflow = {k: v * 1.3 for k, v in d.FEED_207_KMOLH.items()}
    bounded = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA,
                               overflow_kmolh=overflow, bundle=d.BUNDLE_V1)
    assert (bounded.shell_lambda, bounded.top_kmolh, bounded.duty_raw_kw) == (lam, top, b.total_kw)
    assert bounded.duty_demand_raw_kw == r.duty_raw_kw
    new = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA, overflow_kmolh=overflow)
    assert new.shell_lambda == pytest.approx(0.847259, abs=1e-6)
    assert new.duty_raw_kw == pytest.approx(target * d.BUNDLE.shell_capacity, rel=1e-12)


def test_a_split_that_costs_more_than_its_target_at_no_lift_lifts_only_the_sweep():
    r = _overloaded()
    lam, top, _ = bounded_split(r.top_kmolh, r.bot_kmolh, r.co2_feed_kmolh, r.xi_hydrolysis,
                                r.t_bot, r.t_top, r.t_feed, -1.0e9)
    assert lam == 0.0
    assert top["NH3"] == min(r.top_kmolh["NH3"], r.co2_feed_kmolh["NH3"])


def test_a_turndown_is_unbounded():
    """The whole feed at 80 %: the split asks 0.90 of the design duty, the shell still gives 1 —
    1.142 on the replacement bundle the plant runs (decision 154)."""
    overflow = {k: v * 0.8 for k, v in d.FEED_207_KMOLH.items()}
    r = stripper_322e001(0.8 * CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA, overflow_kmolh=overflow)
    assert r.shell_lambda == 1.0 and r.shell_capacity_ratio == d.BUNDLE.shell_capacity
    assert r.duty_raw_kw == r.duty_demand_raw_kw < DUTY_RAW_DES_KW


# ======================================================================================
# The tubes standing full (handoff B-104, decided 2026-10-22)
# ======================================================================================

def test_the_submerged_share_runs_from_dry_to_full():
    """sigma is the held liquor over the bundle standing full, clamped to [0, 1] — 10 663 kg on the
    replacement the plant runs, 8 689 kg on V1's; the factor falls from exactly 1 dry to 322E003's
    0.30 floor full."""
    full = d.TUBES_FULL_KG
    assert full == pytest.approx(10662.72, abs=0.01)
    assert d.BUNDLE_V1.v_tubes_m3 * d.RHO_BOTTOM == pytest.approx(8688.66, abs=0.01)
    assert (submerged_fraction(0.0), submerged_fraction(full / 2), submerged_fraction(2 * full))         == (0.0, 0.5, 1.0)
    assert (unsubmerged_factor(0.0), unsubmerged_factor(full)) == (1.0, pytest.approx(0.30))
    assert unsubmerged_factor(full / 2) == pytest.approx(0.65, abs=1e-12)


def test_the_bottoms_cool_toward_the_crystallisation_floor_and_never_warm():
    """T' = 132.7 + f (T - 132.7): 172 C off a full bundle leaves at 144.49 C; a dry bundle and a
    bottoms at or below the floor are untouched."""
    assert submerged_bottoms_c(172.0, 0.30) == pytest.approx(144.49, abs=1e-9)
    assert submerged_bottoms_c(172.0, 1.0) == 172.0
    assert submerged_bottoms_c(130.0, 0.30) == 130.0


@pytest.mark.parametrize("bundle, held, lam, t_bot, nh3", [
    (d.BUNDLE_V1, 0.0, 1.0, 172.0, 7.931), (d.BUNDLE_V1, 0.25, 0.8693, 165.123, 12.480),
    (d.BUNDLE_V1, 0.5, 0.7333, 158.245, 16.395), (d.BUNDLE_V1, 1.0, 0.4575, 144.49, 22.693),
    (d.BUNDLE, 0.0, 1.0, 172.0, 7.931), (d.BUNDLE, 0.25, 0.9809, 165.123, 8.467),
    (d.BUNDLE, 0.5, 0.8213, 158.245, 13.805), (d.BUNDLE, 1.0, 0.4977, 144.49, 21.846)])
def test_a_submerged_bundle_strips_less_and_its_bottoms_run_colder(bundle, held, lam, t_bot, nh3):
    """The design feed with the bundle a quarter, half and wholly submerged: the shell pays its
    derated capacity, lambda scales the lift, and the unstripped ammonia leaves in the bottoms,
    whose temperature falls toward the floor — which itself takes some of the duty off the
    shell, so V1's full bundle keeps 0.46 of its lift on 0.30 of its capacity. The replacement's
    shell starts 14 % higher (decision 154), so a quarter submerged barely binds."""
    r = stripper_322e001(CO2_DES_TH, d.STEAM_T_DES_C, d.P_DES_BARA, bundle=bundle,
                         held_kg=held * bundle.v_tubes_m3 * d.RHO_BOTTOM)
    assert r.submerged_frac == held
    assert r.shell_capacity_ratio == pytest.approx(bundle.shell_capacity * (1.0 - 0.7 * held),
                                                   abs=1e-12)
    assert r.shell_lambda == pytest.approx(lam, abs=1e-4)
    assert r.t_bot == pytest.approx(t_bot, abs=1e-3)
    assert r.bot_mass_pct["NH3"] == pytest.approx(nh3, abs=1e-3)
