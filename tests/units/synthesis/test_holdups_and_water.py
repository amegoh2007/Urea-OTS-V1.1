"""322E002's LT-322E002, 322E003's sump and its tempered water, stepped as V1 steps them."""

from __future__ import annotations

import pytest

from ureasim.core.stream import MW_COMP
from ureasim.data.unit_322e003 import (
    CCW_KGH_DES,
    CCW_T_IN_DES_C,
    HOLDUP_MAX_KG,
    HOLDUP_NLL_KG,
    OVERFLOW_DES_KMOLH,
)
from ureasim.engine.plant import build_plant
from ureasim.engine.scheduler import Scheduler
from ureasim.units.synthesis.ccw_loop import V1_FV_329409, CcwLoop
from ureasim.units.synthesis.condenser_holdup import CondenserHoldup
from ureasim.units.synthesis.scrubber_sump import ScrubberSump

DT = 0.1


@pytest.fixture(scope="module")
def seed():
    sch, plant = build_plant()
    return Scheduler(sch, plant).tick().results


# ----- 322E002 ------------------------------------------------------------------------------

def _condenser(unit, seed, phi_fwd=1.0):
    s, e = seed["322E001"].stripper, seed["322F001"]
    return unit.step(s.top_kmolh, s.t_top, e.comp_kgh, e.t_c, seed["329"].t_lp_c, 140.7,
                     phi_fwd, DT)


def test_the_condenser_seed_holds_its_nll(seed):
    """At the seed the liquid make is the pin's to the bit, so LT-322E002 holds 50 %."""
    r = _condenser(CondenserHoldup(), seed)
    assert r.level_pct == 50.0


def test_a_slower_forward_circulation_settles_higher(seed):
    """phi_fwd 0.9: the gravity drain settles the level at L_eq = 50 / 0.9 = 55.6 % on its 6 min."""
    unit = CondenserHoldup()
    for _ in range(36000):
        r = _condenser(unit, seed, phi_fwd=0.9)
    phi_in = r.condenser.liq_kgh / 189257.54705597984
    assert r.level_pct == pytest.approx(50.0 * phi_in / 0.9, abs=0.05)


# ----- 322E003's tempered water -------------------------------------------------------------

def test_the_tempered_water_holds_its_design():
    c = CcwLoop().step(1.0, 0.0, DT)
    assert (c.m_ccw_kgh, c.t_ccw_in_c, c.pump_frac) == (CCW_KGH_DES, CCW_T_IN_DES_C, 1.0)


def test_both_pumps_stopped_the_circulation_decays_on_its_lag():
    """No head: FT-329409 falls on its 3 s lag while FIC-329409 opens FV-329409 against it — from
    its Neldisc's 46.85 % to 88.7 % in 30 s (V1's valve, from 60 %, is wide open by then)."""
    loop = CcwLoop(p329p006a=False)
    for _ in range(300):
        c = loop.step(1.0, 0.0, DT)
    assert c.pump_frac == 0.0 and c.m_ccw_kgh < 1.0e-3 * CCW_KGH_DES
    assert c.fv_329409_pct == pytest.approx(88.718, abs=1e-3)
    loop = CcwLoop(p329p006a=False, **V1_FV_329409)
    for _ in range(300):
        c = loop.step(1.0, 0.0, DT)
    assert c.fv_329409_pct == 100.0


def test_fv_329409_on_its_vendor_trim():
    """Decision 108's class, decided 2026-10-15: FV-329409 on Metso's DN 150 Neldisc from 46.85 %,
    where its normal case passes 306 t/h at the sheet's 95 C (V1 linear from 60 %; the harness
    proves V1's ``==``). FIC-329409's set point cut 10 %: five minutes on, V1's valve at 57.76 % with
    294.68 t/h, the Neldisc at 45.23 % with 292.09; after an hour 54.02 % and 42.83 %, both on
    275.5 t/h. Ten points opened by hand: V1's valve passes 357.0 t/h, the Neldisc 438.0."""
    seen = {}
    for name, loop in (("v1", CcwLoop(**V1_FV_329409)), ("port", CcwLoop())):
        loop.fic_sp = 306.0 * 0.9
        for k in range(1, 36001):
            loop.step(1.0, 0.0, DT)
            if k in (3000, 36000):
                seen[name, k] = (loop.fic_pv, loop.fic_op)
    assert seen["v1", 3000] == (pytest.approx(294.677, abs=1e-3), pytest.approx(57.762, abs=1e-3))
    assert seen["port", 3000] == (pytest.approx(292.090, abs=1e-3),
                                  pytest.approx(45.227, abs=1e-3))
    assert seen["v1", 36000][1] == pytest.approx(54.023, abs=1e-3)
    assert seen["port", 36000][1] == pytest.approx(42.833, abs=1e-3)
    for loop, flow in ((CcwLoop(**V1_FV_329409), 357.0), (CcwLoop(), 437.977)):
        loop.fic_mode, loop.fic_op = "MAN", loop.fic_op + 10.0
        for _ in range(600):
            loop.step(1.0, 0.0, DT)
        assert loop.fic_pv == pytest.approx(flow, abs=1e-3)


def test_a_load_rise_warms_the_supply_and_tic_329005_opens_its_cooler():
    """10 % more load: the steady supply warms 1 K; TIC-329005 opens TV-329005 and pulls it back
    — on the DCS table's 1.50 and 300 s over TT-329005's 0-200 C (decision 10's class), 80.58 C
    after ten minutes, 80.27 after thirty and within 0.002 K in three hours, TV-329005 at 53.33 %."""
    loop = CcwLoop()
    for k in range(1, 108001):
        c = loop.step(1.1, 0.0, DT)
        if k == 6000:
            assert c.t_ccw_in_c == pytest.approx(80.577, abs=1e-3)
    assert c.tv_329005_pct == pytest.approx(53.33, abs=0.01)
    assert c.t_ccw_in_c == pytest.approx(CCW_T_IN_DES_C, abs=0.002)


# ----- 322E003's sump -----------------------------------------------------------------------

def _overflow_kgh() -> float:
    return sum(v * MW_COMP[k] for k, v in OVERFLOW_DES_KMOLH.items())


def test_the_sump_holds_its_nll_on_its_design():
    sump = ScrubberSump()
    r = sump.step(dict(OVERFLOW_DES_KMOLH), 178.8, _overflow_kgh(), 1.0, 0.1, DT)
    assert r.holdup_kg == pytest.approx(HOLDUP_NLL_KG, rel=1e-12) and r.held_kg == 0.0


def test_a_stalled_ejector_fills_the_sump_and_the_scrubber_holds_the_excess():
    """No entrainment: the sump fills from NLL to full in 4 min (its holdup time), then what it
    cannot hold is held back in the scrubber (handoff B-78 item 1, decided 2026-10-03) — every
    kilogram the scrubber made is in one of the two."""
    sump = ScrubberSump()
    t_full = None
    for k in range(4000):
        r = sump.step(dict(OVERFLOW_DES_KMOLH), 178.8, 0.0, 1.0, 0.1 * k, DT)
        if t_full is None and r.holdup_kg == HOLDUP_MAX_KG:
            t_full = k * DT
    assert t_full == pytest.approx(240.0, abs=0.2)
    made = HOLDUP_NLL_KG + 4000 * _overflow_kgh() * DT / 3600.0
    assert r.holdup_kg + r.held_kg == pytest.approx(made, rel=1e-12)
    # The ejector restarts: the held condensate runs down into the sump before the sump falls.
    r = sump.step(dict(OVERFLOW_DES_KMOLH), 178.8, 2.0 * _overflow_kgh(), 1.0, 400.0, DT)
    assert r.holdup_kg == HOLDUP_MAX_KG and r.held_kg < r.holdup_kg


def test_a_cold_overflow_throttles_the_suction_line_and_stays_in_the_sump():
    """At 62 C, 2 K into the 5 K band above carbamate's 60 C: the whole overflow runs into the sump
    and the factor 0.4 throttles the line to 322F001 on the next tick (B-78 item 3)."""
    sump = ScrubberSump()
    r = sump.step(dict(OVERFLOW_DES_KMOLH), 62.0, 0.0, 1.0, 0.1, DT)
    assert r.mushy_factor == sump.mushy_factor == pytest.approx(0.4, rel=1e-12)
    assert r.solidification and r.m_cond_in_kgh == pytest.approx(_overflow_kgh(), rel=1e-12)
    assert r.holdup_kg == pytest.approx(HOLDUP_NLL_KG + _overflow_kgh() * DT / 3600.0, rel=1e-12)


def test_the_recondensed_backlog_and_the_forward_pulse_reach_the_sump():
    """What PT-329201's backlog recondensed (B-76) runs in; the forward-carbamate pulse (B-78 item
    2) runs out — the balance closes on both."""
    r = ScrubberSump().step(dict(OVERFLOW_DES_KMOLH), 178.8, _overflow_kgh(), 1.0, 0.1, DT,
                            recond_kgh=3600.0, pulse_kgh=1800.0)
    assert r.holdup_kg == pytest.approx(HOLDUP_NLL_KG + 0.05, rel=1e-12)
    assert (r.recond_kgh, r.pulse_kgh) == (3600.0, 1800.0)
