"""Behaviour of 323E003 / 323D001 / 323P001 — `ureasim.units.recirc.lp_carbamate_condenser`.

Equivalence with V1 is proven tick by tick in
`tests/equivalence/test_lp_carbamate_condenser_equivalence.py`. This file pins what the node
DOES: the dew point that holds it, PIC-323202 on its transmitter's span (handoff B-32), the
condenser drawing the node down under surplus cooling (B-34), the tempered water that moves it,
and 323P001 at the tank's heel (B-35) — the three decided on 2026-09-27 — and PFD 734 from
328D003 in its inlets as its departure from the PFD's row (B-37 and B-94, decided 2026-10-10 and
2026-10-14). Every number here was measured on the module
before it was written down.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_323 as d
from ureasim.data import unit_323e003 as e3
from ureasim.data import unit_323e011 as e
from ureasim.units.recirc import lp_carbamate_condenser as lp

M305, FLASH, POOL = e3.E003_M305_DES_KGH, d.M_FLASH_GAS_DES_KGH, d.M_POOL_VAP_DES_KGH


def _run(seconds: float, dt: float = 1.0, gas=None, pic_man: float = None,
         tic_sp: float = None, sic_man: float = None, trace: tuple = ()):
    """Run the LPCC alone on its design boundaries, the 305 gas scaled by `gas(t)`. Returns the
    last result, the results at the `trace` times, the first times the capacity passes the gas
    that arrives ("cap binds", where V1's cap would), the vent shuts and the tank reaches its
    floor, and the liquor the tank created (+)."""
    u = lp.LpCarbamateCondenser()
    pic, lic, sic, tic = lp.pic_323202(), lp.lic_323502(), lp.sic_323901(), lp.tic_323013()
    if pic_man is not None:
        pic.set_mode("MAN")
        pic.op = pic_man
    if sic_man is not None:
        sic.set_mode("MAN")
        sic.op = sic_man
    if tic_sp is not None:
        tic.set_mode("AUTO")
        tic.sp = tic_sp
    r, at, first, created = None, {}, {}, 0.0
    for k in range(1, int(round(seconds / dt)) + 1):
        t = round(k * dt, 6)
        f = gas(t) if gas else 1.0
        m_before = u.m_kg
        r = u.step(pic, lic, sic, tic, M305 * f, FLASH * f, POOL * f, 0.0, 0.0,
                   e3.E003_M718B_DES_KGH, e3.E003_M776_DES_KGH, e.E011_P_BARA, dt)
        created += (u.m_kg - m_before) - (r.in_kgh - r.m_321_kgh - r.m_308_kgh) / 3600.0 * dt
        if r.capacity_kgh > r.env_in_kgh:
            first.setdefault("cap binds", t)
        if r.pic_op_pct == 0.0:
            first.setdefault("vent shut", t)
        if u.m_kg == e3.D001_M_FLOOR_KG:
            first.setdefault("tank floor", t)
        if t in trace:
            at[t] = r
    return r, at, first, created


def _step(factor: float, t0: float = 10.0):
    return lambda t: factor if t > t0 else 1.0


# ======================================================================================
# 1. The design point
# ======================================================================================

def test_the_design_point_holds_to_the_bit():
    r, _, first, created = _run(3600.0)
    assert (r.p_bara, r.t_c, r.m_kg, r.pic_op_pct) == (
        e3.D001_P_BARA, e3.E003_T_C, e3.D001_M_DES_KG, e3.E003_PV_OP_DES_PCT)
    assert (r.m_321_kgh, r.m_308_kgh, r.q_kw) == (
        e3.E003_M321_DES_KGH, e3.E003_M308_DES_KGH, e3.E003_Q_DES_KW)
    assert (r.tw_supply_c, r.tw_return_c, r.tic_op_pct) == (
        e3.TW_SUP_T_C, e3.TW_RET_T_C, e3.TV13_DES_PCT)
    # 24 998 . 14 / 14, one rounding off the design condensation.
    assert r.env_cond_kgh == r.capacity_kgh == pytest.approx(e3.E003_M_COND_DES_KGH, rel=1e-15)
    assert first == {} and created == 0.0


# ======================================================================================
# 2. The dew point holds the node; PIC-323202 trims it (handoff B-32, decided)
# ======================================================================================

def test_the_dew_point_takes_the_extra_gas():
    """305 up 10 % with PV-323202 held at 25 %: 2456 kg/h more gas, and the node settles at
    3.372 bar a, where the higher dew point condenses 2402 kg/h of it — the vent takes 54."""
    r, at, _, _ = _run(3600.0, gas=_step(1.1), pic_man=25.0, trace=(20.0,))
    assert at[20.0].p_bara == pytest.approx(3.3389, abs=1e-4)
    assert r.p_bara == pytest.approx(3.3717, abs=1e-4)
    extra = r.env_in_kgh - e3.E003_M305_DES_KGH - e3.E003_M797_DES_KGH
    assert r.env_cond_kgh - e3.E003_M_COND_DES_KGH == pytest.approx(0.978 * extra, abs=1.0)


def test_pic_323202_on_its_span_gain():
    """The same load in AUTO, on 20 %/bar and 100 s: 3.349 bar a after a minute, 3.306 after
    ten, 3.215 after the hour with PV-323202 at 68 % (V1's 5.0 %/bar and 40 s: 3.234)."""
    r, at, _, _ = _run(3600.0, gas=_step(1.1), trace=(60.0, 600.0))
    assert (at[60.0].p_bara, at[600.0].p_bara) == pytest.approx((3.3489, 3.3065), abs=1e-4)
    assert r.p_bara == pytest.approx(3.2145, abs=1e-4)
    assert r.pic_op_pct == pytest.approx(68.01, abs=0.01)


# ======================================================================================
# 3. Handoff B-34, decided: the condenser draws the node down on its dew point
# ======================================================================================

def test_surplus_cooling_draws_the_node_down_to_where_the_capacity_meets_the_load():
    """TIC-323013 set to 45 C: the capacity passes the gas at 440 s and PIC-323202 shuts
    PV-323202 five seconds later. The condenser keeps drawing on the envelope's gas, and the
    node follows the cooling water down — 2.746 bar a at 600 s, 2.458 an hour on, 0.74 below
    the set point, with the capacity on the load. V1's cap froze it at 2.725 (on V1's tuning)."""
    r, at, first, created = _run(3600.0, tic_sp=45.0, trace=(600.0,))
    assert (first["cap binds"], first["vent shut"]) == (440.0, 445.0)
    assert at[600.0].p_bara == pytest.approx(2.7455, abs=1e-4)
    assert r.p_bara == pytest.approx(2.4576, abs=1e-4)
    assert (r.pic_op_pct, r.m_321_kgh, r.env_cond_kgh) == (0.0, 0.0, r.capacity_kgh)
    assert r.capacity_kgh - r.env_in_kgh == pytest.approx(0.0, abs=0.2)
    assert abs(created) < 1e-9


def test_less_cooling_lifts_the_node_until_the_vent_is_wide_open():
    """TIC-323013 set to 65 C: the dew point carries the node up, PV-323202 is wide open within
    half an hour, and the node is still climbing at 3.835 bar a an hour on."""
    r, at, _, _ = _run(3600.0, tic_sp=65.0, trace=(1800.0,))
    assert at[1800.0].pic_op_pct == 100.0
    assert r.p_bara == pytest.approx(3.8353, abs=1e-4) and r.p_bara > at[1800.0].p_bara


def test_the_gas_gone_takes_the_node_to_the_recycle_s_dew_point():
    """The 305 overhead gone — a stripper trip: only the 797 recycle arrives, the capacity
    passes it at once, the vent shuts at 23 s, and the node falls until the dew point has
    closed on the water far enough to condense just the recycle — 1.867 bar a within five
    minutes. V1's cap left it standing at 2.364 (on the decided tuning)."""
    r, at, first, _ = _run(3600.0, gas=_step(0.0), trace=(300.0,))
    assert (first["cap binds"], first["vent shut"]) == (11.0, 23.0)
    assert at[300.0].p_bara == pytest.approx(1.8672, abs=1e-4)
    assert r.p_bara == pytest.approx(1.8672, abs=1e-4)
    assert r.env_in_kgh == e3.E003_M797_DES_KGH
    assert r.capacity_kgh == pytest.approx(r.env_in_kgh, abs=1e-6)


# ======================================================================================
# 4. Handoff B-35, decided: 323P001 at 323D001's heel
# ======================================================================================

def test_the_pump_loses_suction_at_the_heel_and_makes_nothing():
    """SIC-323901 held at 100 rpm draws 61.5 t/h against 38.2 t/h arriving: the tank reaches its
    1 kg heel at 989 s, where 323P001 delivers the liquid above it and what arrives, and from
    then on only what arrives, with its suction lost. Nothing is made — V1's floor guard made
    6.2 kg at this 1 s step."""
    r, _, first, created = _run(1500.0, sic_man=100.0)
    assert first["tank floor"] == 989.0
    assert r.suction_lost and r.sic_op_rpm == 100.0
    assert r.m_308_kgh == r.in_kgh - r.m_321_kgh
    assert abs(created) < 1e-9


def _run_734(m_734_kgh, ticks: int) -> dict:
    """The LPCC on its design boundaries with FIC-323401 delivering ``m_734_kgh``; the results at
    ten minutes and at the end."""
    u = lp.LpCarbamateCondenser()
    loops = (lp.pic_323202(), lp.lic_323502(), lp.sic_323901(), lp.tic_323013())
    at = {}
    for k in range(1, ticks + 1):
        r = u.step(*loops, M305, FLASH, POOL, 0.0, 0.0, e3.E003_M718B_DES_KGH,
                   e3.E003_M776_DES_KGH, e.E011_P_BARA, 1.0, m_734_kgh=m_734_kgh)
        if k in (600, ticks):
            at[k] = r
    return at


def test_pfd_734_enters_as_its_departure_from_the_pfd():
    """Handoffs B-37 and B-94, decided 2026-10-10 and 2026-10-14: FIC-323401's ammonia water enters
    at 56 C as its departure from PFD 734's 1534 kg/h, which the PFD's 323E003 balance closes
    without. At the design flow the unit is V1's to the bit. FIC-323401 at 2000 kg/h lifts 323D001
    0.25 % in ten minutes and LIC-323502, on the plant DCS's tuning, passes the 466 kg/h on in PFD
    308: after four hours 37 304.4 kg/h, 469.2 over the design, the level back on 50 %; shut, 308
    carries 1544.6 kg/h less."""
    assert _run_734(1534.0, 600)[600] == _run_734(None, 600)[600]
    up = _run_734(2000.0, 4 * 3600)
    assert up[600].in_kgh == pytest.approx(e3.E003_IN_DES_KGH + 466.0, rel=1e-12)
    assert up[600].level_pct == pytest.approx(50.249, abs=1e-3)
    assert up[14400].m_308_kgh == pytest.approx(37304.4, abs=0.1)
    assert up[14400].level_pct == pytest.approx(50.0, abs=1e-3)
    assert up[14400].t_c == pytest.approx(73.993, abs=1e-3)
    shut = _run_734(0.0, 4 * 3600)
    assert shut[600].in_kgh == pytest.approx(e3.E003_IN_DES_KGH - 1534.0, rel=1e-12)
    assert shut[14400].m_308_kgh - e3.E003_M308_DES_KGH == pytest.approx(-1544.6, abs=0.1)
