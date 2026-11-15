"""The urea melt main header — `ureasim.units.finishing.melt_header` (decisions 224, 236 and 237).

Pinned: every factor of the header's ratio form is exactly 1.0 at the design seed and the header
holds 3.5 bar g there on its first evaluation, LV-324501A at the header's design stroke, the same trim
as unit 324's sizing stroke; one header valve fewer raises the header and one more lowers it, before
LV-324501A's positioner answers, by the plant's step of 5 November 2026 at 13:30 within 0.004 of its
ratio and 0.4 % of PIC-335201's output kick, and the header recovers without a ring; at tau 0 the
valve stands on PIC-335201's output to the bit, and in MAN it follows the output on its lag;
HV-335602 drains it, opening in 3 s and closing in 25 s; no valve online dead-heads the
pumps and PIC-335201 shuts LV-324501A; both pumps stopped pass nothing; E1's inverse hands a
pressure back to LIC-324501's output; the band each number of valves holds between 3.2 and 3.8 bar g
is the process engineer's table; and, on a level integrator with LIC-324501's tuning, each load from
70 to 120 % with its matching valves settles on 3.5 bar g with LV-324501B shut, while one valve
fewer rides the header on E1's 3.8 bar g ceiling and LV-324501B returns the excess.
"""

from __future__ import annotations

import math

import pytest

from ureasim.control.granulation_trips import HEALTHY_35, Unit35Actions
from ureasim.control.valve import cv_fraction
from ureasim.data import unit_324 as d
from ureasim.data import unit_335 as u
from ureasim.data.unit_335 import HEADER_VALVES_DES, LIC_324501_X_DES_PCT
from ureasim.units.evaporation import second_evaporator as se
from ureasim.units.finishing import melt_header as mh

#: More than any tick's drain: the heel never limits these runs [kg/h].
NO_HEEL = 1.0e9


def _step(header, pic, x=LIC_324501_X_DES_PCT, n=HEADER_VALVES_DES, hic=0.0, running=True):
    return header.step(pic, x, n, hic, running, NO_HEEL, 0.1)


def test_every_factor_is_one_at_the_seed_and_the_header_holds_its_design():
    assert mh.nozzle_fraction(HEADER_VALVES_DES, 3.5) == 1.0
    assert mh.hv_fraction(0.0, 3.5) == 0.0 and mh.recycle_fraction(0.0) == 0.0
    assert mh.forward_fraction(u.LV_324501A_HEADER_OP_DES_PCT, 0.0, 3.5) == 1.0
    assert mh.e1_setpoint_barg(LIC_324501_X_DES_PCT) == 3.5
    assert mh.lv_b_stroke_pct(LIC_324501_X_DES_PCT) == 0.0
    header, pic = mh.MeltHeader(), mh.pic_335201()
    for _ in range(100):
        r = _step(header, pic)
        assert (r.p_barg, r.forward_kgh, r.recycle_kgh, r.iterations) == (3.5, d.P2_DES_KGH, 0.0, 1)
        assert (r.lv_a_pct, r.lv_a_position_pct, r.lv_b_pct, r.hv_share, r.residual) == (
            u.LV_324501A_HEADER_OP_DES_PCT, u.LV_324501A_HEADER_OP_DES_PCT, 0.0, 0.0, 0.0)


def test_the_headers_design_stroke_is_unit_324s_trim_on_the_headers_differential():
    """Decision 237: LV-324501A's inlet the sheet's 6.9 bar a, its differential on the 3.5 bar g
    header 2.387 bar, its design stroke 79.09 % (75.35 % across the sizing case's 3.2 bar): the same
    trim, cv(79.09) / cv(75.35) = sqrt(3.2 / 2.387), which the seal's blow-through keeps."""
    assert u.LV_324501A_DP_DES_BAR == 6.9 - (3.5 + 1.01325)
    assert u.LV_324501A_HEADER_OP_DES_PCT == pytest.approx(79.0946, abs=1e-4)
    ratio = (cv_fraction(u.LV_324501A_HEADER_OP_DES_PCT / 100.0, d.LV_324501_CHAR)
             / cv_fraction(d.LV_324501A_OP_DES_PCT / 100.0, d.LV_324501_CHAR))
    assert ratio == pytest.approx(math.sqrt(d.LV_324501_DP_DES_BAR / u.LV_324501A_DP_DES_BAR),
                                  rel=1e-14)
    assert mh.KAPPA == pytest.approx(0.1516, abs=1e-4)
    assert mh.dead_head_barg(0.0) == pytest.approx(6.2486, abs=1e-4)


def test_the_passing_stroke_inverts_the_forward_flow():
    """Decision 238: the stroke a restore opens LV-324501A at, back from the flow it passes, over the
    trim, LV-324501B's share and the header up to the pumps' dead head; the design back to its
    stroke to the bit; no flow shut; a flow the trim cannot pass, or a header beyond the dead head,
    full open."""
    for h in (2.5, 20.0, 50.0, 79.0946, 95.0, 100.0):
        for beta in (0.0, 0.1, 0.3):
            for p in (0.5, 2.8, 3.5, 3.8, 6.0):
                phi = mh.forward_fraction(h, beta, p)
                assert mh.passing_stroke_pct(phi, beta, p) == pytest.approx(h, abs=1e-12)
    assert mh.passing_stroke_pct(1.0, 0.0, 3.5) == u.LV_324501A_HEADER_OP_DES_PCT
    assert mh.passing_stroke_pct(0.0, 0.0, 3.5) == 0.0
    assert mh.passing_stroke_pct(2.0, 0.0, 3.5) == 100.0 == mh.passing_stroke_pct(0.5, 0.0, 6.5)


def test_one_valve_fewer_raises_the_header_and_one_more_lowers_it():
    """On the tick the operator moves a valve, LV-324501A behind its positioner: 9 valves 3.77,
    11 valves 3.25 and 12 valves 3.02 bar g (3.62, 3.39 and 3.28 before decisions 236 and 237), each
    closing the header's balance to the solver's tolerance."""
    for n, p in ((9, 3.7739), (11, 3.2475), (12, 3.0156)):
        r = _step(mh.MeltHeader(), mh.pic_335201(), n=n)
        assert r.p_barg == pytest.approx(p, abs=1e-4) and abs(r.residual) <= 1e-12


def _settled(x, n, ticks=9000, hic=0.0):
    header, pic = mh.MeltHeader(), mh.pic_335201()
    for _ in range(ticks):
        r = _step(header, pic, x=x, n=n, hic=hic)
    return header, pic, r


@pytest.mark.parametrize("n1, n2, ratio, kick, plant_ratio, plant_kick", [
    (8, 9, 0.920664, 4.911230, 0.918, 5.3), (9, 10, 0.928876, 4.402885, 0.932, 4.4)])
def test_a_valve_added_steps_the_header_as_the_plant_did_at_13_30(n1, n2, ratio, kick, plant_ratio,
                                                                  plant_kick):
    """As-Built §CXXIII.9: 5 November 2026, 13:30:06 and 13:30:48, the header on E1's 3.8 bar g
    ceiling with LV-324501B open (X 63.75 %), one valve brought online. The first tick's header over
    the settled one and PIC-335201's output kick stand within 0.004 and 0.4 % of the plant's
    (0.918 and 5.3 %, 0.932 and 4.4 %); as built before decision 236 they were 0.964 and 2.2 %."""
    header, pic, r0 = _settled(63.75, n1)
    assert r0.p_barg == pytest.approx(3.8, abs=1e-6)
    r1 = _step(header, pic, x=63.75, n=n2)
    assert r1.p_barg / r0.p_barg == pytest.approx(ratio, abs=1e-6)
    assert r1.lv_a_pct - r0.lv_a_pct == pytest.approx(kick, abs=1e-6)
    assert abs(r1.p_barg / r0.p_barg - plant_ratio) < 0.004 and abs(r1.lv_a_pct - r0.lv_a_pct
                                                                   - plant_kick) < 0.4


def _sign_changes(ps):
    d_p = [b - a for a, b in zip(ps, ps[1:])]
    return sum(1 for a, b in zip(d_p, d_p[1:]) if a * b < 0.0 and abs(a) > 1e-9 and abs(b) > 1e-9)


@pytest.mark.parametrize("x, n1, n2", [(35.0, 8, 7), (35.0, 7, 8), (63.75, 9, 10), (35.0, 11, 12)])
def test_the_header_recovers_from_a_valve_step_without_a_ring(x, n1, n2):
    """A minute after the step, tick by tick, the header moves one way only: the lag inside the
    solve does not ring, at seven valves, at twelve, and with LV-324501B open."""
    header, pic, _r = _settled(x, n1)
    ps = [_step(header, pic, x=x, n=n2).p_barg for _ in range(600)]
    assert _sign_changes(ps) == 0


def test_hv_335602_opening_turns_the_header_once():
    """HV-335602 opened at the seed: the header falls while the valve travels and PIC-335201 opens
    LV-324501A behind it, and turns once."""
    header, pic, _r = _settled(35.0, 10)
    ps = [_step(header, pic, hic=100.0).p_barg for _ in range(600)]
    assert _sign_changes(ps) == 1 and min(ps) == pytest.approx(2.6434, abs=1e-4)


def test_at_tau_zero_the_valve_stands_on_pic_335201s_output(monkeypatch):
    """Decision 236's null: with no lag LV-324501A is PIC-335201's output, to the bit, through a
    valve step, HV-335602 travelling and both pumps stopped."""
    monkeypatch.setattr(mh, "LV_324501A_TAU_S", 0.0)
    header, pic = mh.MeltHeader(), mh.pic_335201()
    for n, hic, running in ((11, 0.0, True), (9, 100.0, True), (10, 0.0, False), (10, 0.0, True)):
        for _ in range(300):
            r = header.step(pic, LIC_324501_X_DES_PCT, n, hic, running, NO_HEEL, 0.1)
            assert r.lv_a_position_pct == r.lv_a_pct == pic.op == header.lv_a_position_pct


def test_in_man_the_valve_follows_pic_335201s_output_on_its_lag():
    """PIC-335201 in MAN, its output stepped to 85 %: LV-324501A travels as 85 - (85 - h0) 0.9^k,
    dt over tau 0.1 a tick."""
    header, pic = mh.MeltHeader(), mh.pic_335201()
    pic.mode, pic.op = "MAN", 85.0
    h0 = u.LV_324501A_HEADER_OP_DES_PCT
    for k in range(1, 21):
        r = _step(header, pic)
        assert r.lv_a_pct == 85.0
        assert r.lv_a_position_pct == pytest.approx(85.0 - (85.0 - h0) * 0.9 ** k, abs=1e-9)


def test_hv_335602_drains_the_header_opening_in_3_s_and_closing_in_25_s():
    header, pic = mh.MeltHeader(), mh.pic_335201()
    for _ in range(15):
        r = _step(header, pic, hic=100.0)
    assert r.hv_pct == pytest.approx(50.0, abs=1e-9) and r.p_barg < 3.5 and r.hv_share > 0.0
    for _ in range(16):
        r = _step(header, pic, hic=100.0)
    assert r.hv_pct == 100.0
    for _ in range(125):
        r = _step(header, pic, hic=0.0)
    assert r.hv_pct == pytest.approx(50.0, abs=1e-9)
    for _ in range(126):
        r = _step(header, pic, hic=0.0)
    assert (r.hv_pct, r.phi_hv, r.hv_share) == (0.0, 0.0, 0.0)


def test_no_valve_online_dead_heads_the_pumps_and_pic_335201_shuts_lv_324501a():
    """PIC-335201's output reaches 0 %; LV-324501A follows on its lag and a minute on stands within
    1e-12 % of its seat, passing under 1e-9 of PFD 402 at the dead head (decision 236)."""
    header, pic = mh.MeltHeader(), mh.pic_335201()
    for _ in range(600):
        r = _step(header, pic, n=0)
    assert r.p_barg == mh.dead_head_barg(0.0) and r.phi_forward < 1e-9
    assert r.lv_a_pct == 0.0 and 0.0 < r.lv_a_position_pct < 1e-12


def test_both_pumps_stopped_pass_nothing():
    r = _step(mh.MeltHeader(), mh.pic_335201(), x=80.0, running=False)
    assert (r.p_barg, r.forward_kgh, r.recycle_kgh, r.phi_recycle) == (0.0, 0.0, 0.0, 0.0)
    assert r.lv_b_pct == 60.0


def test_a_pump_restart_lifts_the_header_once_on_the_wound_up_valve():
    """Both 335P001 pumps stopped for 30 s: PIC-335201's output winds to 100 % and LV-324501A
    follows it. On the restart the valve, behind its positioner, is still near its stop: the header
    lifts to 4.65 bar g on the first tick (2.09 at tau 0, where PIC-335201 shuts it inside the
    solve), under the 6.25 bar g dead head, turns once at 2.12 and stands at 3.29 two minutes on."""
    header, pic = mh.MeltHeader(), mh.pic_335201()
    for running in (True, False):
        for _ in range(300):
            r = _step(header, pic, running=running)
    assert r.lv_a_pct == 100.0 and r.lv_a_position_pct == pytest.approx(100.0, abs=1e-9)
    ps = [_step(header, pic).p_barg for _ in range(1200)]
    assert ps[0] == pytest.approx(4.6511, abs=1e-4) and max(ps) == ps[0] < mh.dead_head_barg(0.0)
    assert _sign_changes(ps) == 1 and min(ps) == pytest.approx(2.1214, abs=1e-4)
    assert ps[-1] == pytest.approx(3.2905, abs=1e-4)


def test_e1s_inverse_hands_a_header_back_to_lic_324501():
    assert mh.x_for_setpoint(3.5) == LIC_324501_X_DES_PCT
    assert mh.e1_setpoint_barg(mh.x_for_setpoint(3.3)) == pytest.approx(3.3, abs=1e-9)
    assert (mh.x_for_setpoint(2.0), mh.x_for_setpoint(4.5)) == (0.0, 50.0)


#: The process engineer's bands (2026-11-14): the plant loads [%] each number of header valves
#: holds between 3.2 and 3.8 bar g.
BANDS = {7: (66.9, 72.9), 8: (76.5, 83.4), 9: (86.1, 93.8), 10: (95.6, 104.2),
         11: (105.2, 114.6), 12: (114.7, 125.0)}


@pytest.mark.parametrize("n", sorted(BANDS))
def test_each_number_of_valves_holds_the_engineers_band(n):
    lo, hi = BANDS[n]
    assert (round(mh.nozzle_fraction(n, 3.2) * 100.0, 1),
            round(mh.nozzle_fraction(n, 3.8) * 100.0, 1)) == (lo, hi)


def _settle(load: float, n: int, ticks: int, dt: float = 0.1):
    """324F003's holdup on LIC-324501 (its tuning, its design holdup and span) draining through
    the header at ``load`` of PFD 402 with ``n`` valves online: the last tick's header, the
    largest LV-324501B stroke over the run, and the mean drain and header over its last tenth."""
    header, pic, lic = mh.MeltHeader(), mh.pic_335201(), se.lic_324501()
    m, feed = d.F003_M_DES_KG, load * d.P2_DES_KGH
    h_b_max, tail_drain, tail_p, tail = 0.0, 0.0, 0.0, ticks // 10
    for k in range(ticks):
        x = lic.step(m / d.F003_M_FULL_KG * 100.0, dt)
        r = header.step(pic, x, n, 0.0, True, (m - d.F003_M_FLOOR_KG) * 3600.0 / dt, dt)
        m += (feed - r.forward_kgh - r.recycle_kgh) / 3600.0 * dt
        h_b_max = max(h_b_max, r.lv_b_pct)
        if k >= ticks - tail:
            tail_drain += (r.forward_kgh + r.recycle_kgh) / tail
            tail_p += r.p_barg / tail
    return r, h_b_max, tail_drain, tail_p


@pytest.mark.parametrize("n", sorted(BANDS))
def test_each_load_with_its_valves_settles_on_the_design_header(n):
    """70 to 120 % of PFD 402 with 7 to 12 valves: LV-324501B never opens and, after half an hour,
    the header is within 0.03 bar of 3.5 bar g (the level loop's slow swing, period about 2000 s,
    still decaying) and the drain meets the feed."""
    load = n / 10.0
    r, h_b_max, drain, _p = _settle(load, n, 20000)
    assert h_b_max == 0.0 and abs(r.p_barg - 3.5) < 0.03
    assert drain == pytest.approx(load * d.P2_DES_KGH, rel=6e-3)


@pytest.mark.parametrize("load, n", [(0.7, 6), (1.0, 9), (1.2, 11)])
def test_one_valve_fewer_rides_the_ceiling_and_lv_324501b_returns_the_excess(load, n):
    """With one valve fewer than the load asks for the header rides E1's 3.8 bar g ceiling and
    LV-324501B returns the excess: over the last five minutes of an hour the mean drain meets the
    feed and the mean header stands on 3.8 bar g. (Where the excess is under LV-324501B's 2 % trim
    floor, 6.6 % of PFD 402, the valve relays at its seat: As-Built Part CXXI.)"""
    r, h_b_max, drain, p = _settle(load, n, 36000)
    assert h_b_max > 0.0 and p == pytest.approx(3.8, abs=0.01)
    assert drain == pytest.approx(load * d.P2_DES_KGH, rel=5e-3)
    assert mh.nozzle_fraction(n, 3.8) < load < mh.nozzle_fraction(n + 1, 3.8) or math.isclose(
        mh.nozzle_fraction(n + 1, 3.5), load)


def test_trip_35_4_shuts_lv_324501a_clamps_pic_335201_and_opens_hv_335602():
    """Decision 228: on 35.4 LV-324501A's solenoid shuts it at once, PIC-335201 stands on its
    stand-in clamp reference, 0 %, and HV-335602 opens in its 3 s; the header drains to 0 bar g."""
    header, pic = mh.MeltHeader(), mh.pic_335201()
    act = Unit35Actions(lv_324501a_shut=True, hv_335602_open=True,
                        pic_335201_hold_pct=u.PIC_335201_CLAMPREF_PCT, p002_permit=False)
    rs = [header.step(pic, LIC_324501_X_DES_PCT, HEADER_VALVES_DES, 0.0, True, NO_HEEL, 0.1, act)
          for _ in range(31)]
    assert all(r.lv_a_position_pct == r.lv_a_pct == r.forward_kgh == r.p_barg == 0.0 for r in rs)
    assert rs[0].hv_pct == pytest.approx(100.0 / 30.0, abs=1e-12)
    assert rs[29].hv_pct == pytest.approx(100.0, abs=1e-12) and rs[-1].hv_pct == 100.0
    assert (pic.op, rs[-1].lv_b_pct, rs[-1].recycle_kgh) == (0.0, 0.0, 0.0)


def test_trip_35_1_fails_lv_324501b_open_on_running_pumps():
    """With an override holding 35.4's actions off and a pump running, LV-324501B fails open on its
    full stroke whatever LIC-324501 asks."""
    header, pic = mh.MeltHeader(), mh.pic_335201()
    r = header.step(pic, LIC_324501_X_DES_PCT, HEADER_VALVES_DES, 0.0, True, NO_HEEL, 0.1,
                    Unit35Actions(lv_324501b_open=True))
    assert r.lv_b_pct == 100.0 and r.phi_recycle == mh.recycle_fraction(100.0) > 0.0


def test_healthy_actions_are_the_call_without_them_to_the_bit():
    a, pa, b, pb = mh.MeltHeader(), mh.pic_335201(), mh.MeltHeader(), mh.pic_335201()
    for n in (HEADER_VALVES_DES,) * 5 + (HEADER_VALVES_DES - 1,) * 300:
        assert (_step(a, pa, n=n) == b.step(pb, LIC_324501_X_DES_PCT, n, 0.0, True, NO_HEEL, 0.1,
                                             HEALTHY_35))
