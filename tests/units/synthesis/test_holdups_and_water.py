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


def test_pfd_308_reaches_the_wash_a_line_residence_late():
    """B-110, decided 2026-10-22: 308's line from 323P001 to 322E003/N5, 47.8 m of 74.7 mm bore
    (0.2095 m3, 255 kg of carbamate at 1218 kg/m3), turns over in 24.94 s at the design 36.8 t/h.
    A settled line hands back what departed, to the bit; a step in 323D001's water and
    temperature departing on one tick arrives 250 ticks later, 25.0 s, and at half the flow 499
    ticks later; without the line it arrives at once."""
    from ureasim.data.process_routes import PROCESS_ROUTES
    from ureasim.data.unit_323e003 import E003_M308_DES_KGH, E003_T_C, W_308
    from ureasim.units.synthesis.scrubber_sump import WASH_ROUTE

    assert PROCESS_ROUTES[WASH_ROUTE].design_dead_time_s == pytest.approx(24.937, abs=1e-3)
    wet = {"NH3": W_308["NH3"] - 0.02, "CO2": W_308["CO2"] - 0.01, "H2O": W_308["H2O"] + 0.03,
           "Urea": W_308["Urea"]}
    for flow, ticks in ((E003_M308_DES_KGH, 250), (0.5 * E003_M308_DES_KGH, 499)):
        sump = ScrubberSump()
        w0 = dict(W_308)
        t, w = sump.wash_arrival(flow, E003_T_C, w0, DT)
        assert t == E003_T_C and w == w0
        arrived = [sump.wash_arrival(flow, 76.0, wet, DT) for _ in range(600)]
        first = next(k for k, (t, _) in enumerate(arrived) if t != E003_T_C)
        assert first == ticks
        assert arrived[first][0] == pytest.approx(76.0, abs=1e-12)
        assert arrived[first][1]["H2O"] == pytest.approx(wet["H2O"], abs=1e-12)
    v1 = ScrubberSump(wash_line=False)
    assert v1.wash_arrival(E003_M308_DES_KGH, 76.0, wet, DT) == (76.0, wet)
