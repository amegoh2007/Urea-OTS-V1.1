"""The urea melt main header — `ureasim.units.finishing.melt_header` (decision 224).

Pinned: every factor of the header's ratio form is exactly 1.0 at the design seed and the header
holds 3.5 bar g there on its first evaluation; one header valve fewer raises the header and one more
lowers it; HV-335602 drains it, opening in 3 s and closing in 25 s; no valve online dead-heads the
pumps and PIC-335201 shuts LV-324501A; both pumps stopped pass nothing; E1's inverse hands a
pressure back to LIC-324501's output; the band each number of valves holds between 3.2 and 3.8 bar g
is the process engineer's table; and, on a level integrator with LIC-324501's tuning, each load from
70 to 120 % with its matching valves settles on 3.5 bar g with LV-324501B shut, while one valve
fewer rides the header on E1's 3.8 bar g ceiling and LV-324501B returns the excess.
"""

from __future__ import annotations

import math

import pytest

from ureasim.data import unit_324 as d
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
    assert mh.forward_fraction(d.LV_324501A_OP_DES_PCT, 0.0, 3.5) == 1.0
    assert mh.e1_setpoint_barg(LIC_324501_X_DES_PCT) == 3.5
    assert mh.lv_b_stroke_pct(LIC_324501_X_DES_PCT) == 0.0
    header, pic = mh.MeltHeader(), mh.pic_335201()
    for _ in range(100):
        r = _step(header, pic)
        assert (r.p_barg, r.forward_kgh, r.recycle_kgh, r.iterations) == (3.5, d.P2_DES_KGH, 0.0, 1)
        assert (r.lv_a_pct, r.lv_b_pct, r.hv_share, r.residual) == (d.LV_324501A_OP_DES_PCT, 0.0,
                                                                  0.0, 0.0)


def test_one_valve_fewer_raises_the_header_and_one_more_lowers_it():
    """On the tick the operator moves a valve, before PIC-335201 answers: 9 valves 3.62, 11 valves
    3.39 and 12 valves 3.28 bar g, each closing the header's balance to the solver's tolerance."""
    for n, p in ((9, 3.6225), (11, 3.3881), (12, 3.2849)):
        r = _step(mh.MeltHeader(), mh.pic_335201(), n=n)
        assert r.p_barg == pytest.approx(p, abs=1e-4) and abs(r.residual) <= 1e-12


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
    header, pic = mh.MeltHeader(), mh.pic_335201()
    for _ in range(600):
        r = _step(header, pic, n=0)
    assert r.p_barg == mh.dead_head_barg(0.0) and r.phi_forward == 0.0
    assert r.lv_a_pct == 0.0


def test_both_pumps_stopped_pass_nothing():
    r = _step(mh.MeltHeader(), mh.pic_335201(), x=80.0, running=False)
    assert (r.p_barg, r.forward_kgh, r.recycle_kgh, r.phi_recycle) == (0.0, 0.0, 0.0, 0.0)
    assert r.lv_b_pct == 60.0


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
