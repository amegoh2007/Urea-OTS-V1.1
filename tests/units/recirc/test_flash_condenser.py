"""Behaviour of 323E011 / 323D011 — `ureasim.units.recirc.flash_condenser`.

Equivalence with V1 is proven tick by tick in
`tests/equivalence/test_flash_condenser_equivalence.py`. This file pins what the node DOES:
what sets its pressure — PV-323203's stroke, the condenser's dew-point capacity (B-30, decided
2026-10-15; V1's constant and its floors are asserted in the equivalence test) and, one tick
later, 323F004's flash — and the decided divergences: PIC-323203 on its transmitter's span (B-32)
and 323P008's heel (B-33);
SV32357's relief (A-16, decided 2026-10-01); and 323F004's vapour space in the node (B-51, decided
2026-10-07), which slows every transient of the node by a third and holds a full envelope steady.
Every number here was measured on the module before it was written down, with LV-323503 and
FV-323418 on their vendor trims (B-44, decided 2026-09-30): the level loop the trims move shifts
the tank's vapour space, so the node's settling moves in the sixth decimal.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_323 as d
from ureasim.data import unit_323e011 as e
from ureasim.data.design_point import R323_M314_DES
from ureasim.units.recirc import flash_condenser as fc
from ureasim.units.recirc import flash_tank as ft

M701 = e.E011_M701_DES_KGH


def _run(seconds: float, dt: float = 0.1, m701=None, pic_man: float = None,
         pic_sp: float = None, trace: tuple = (), trip: bool = True):
    """Run the condenser alone on its design boundaries. Returns the last result, the results
    at the `trace` times, the first times the node and the tank reach their floors, the vent
    shuts and the pump loses suction, the liquor the tank created (+) or destroyed (-), and the
    three controllers. ``trip`` False runs without 323P008's low-level trip (B-93)."""
    cond = fc.FlashCondenser()
    if not trip:
        cond.l2_pct = None
    pic, lic, fic = fc.pic_323203(), fc.lic_323503(), fc.fic_323418()
    if pic_man is not None:
        pic.set_mode("MAN")
        pic.op = pic_man
    if pic_sp is not None:
        pic.sp = pic_sp
    r, at, first, created = None, {}, {}, 0.0
    for k in range(1, int(round(seconds / dt)) + 1):
        t = round(k * dt, 6)
        m_before = cond.m_kg
        r = cond.step(pic, lic, fic, m701(t) if m701 else M701, 0.0, 0.0,
                      e.E011_M786_DES_KGH, e.E011_M321_DES_KGH, e.E011_M402_DES_KGH, dt)
        created += ((cond.m_kg - m_before)
                    - (r.in_kgh - r.m_702_kgh - r.m_relief_kgh - r.m_718a_kgh - r.m_718b_kgh)
                    / 3600.0 * dt)
        if r.p_bara == e.E011_P_FLOOR_BARA:
            first.setdefault("node floor", t)
        if cond.m_kg == e.D011_M_FLOOR_KG:
            first.setdefault("tank floor", t)
        if r.pic_op_pct == 0.0:
            first.setdefault("vent shut", t)
        if r.suction_lost:
            first.setdefault("suction lost", t)
        if r.p008_tripped:
            first.setdefault("323P008 tripped", t)
        if t in trace:
            at[t] = r
    return r, at, first, created, (pic, lic, fic)


def _step(factor: float, t0: float = 10.0):
    return lambda t: M701 * (factor if t > t0 else 1.0)


# ======================================================================================
# 1. The design point, and what PV-323203 alone sets
# ======================================================================================

def test_the_design_point_holds_to_the_bit():
    r, _, _, created, _ = _run(3600.0)
    assert (r.p_bara, r.t_c, r.m_kg, r.pic_op_pct) == (
        e.E011_P_BARA, e.E011_T_C, e.D011_M_DES_KG, e.E011_PV_OP_DES_PCT)
    assert (r.m_702_kgh, r.gen_kgh, r.m_718a_kgh, r.m_718b_kgh) == (
        e.E011_MV_DES_KGH, e.E011_MV_DES_KGH, e.M718A_DES_KGH, e.M718B_DES_KGH)
    assert created == 0.0


@pytest.mark.parametrize("stroke, p_settled", [(10.0, 1.14798), (50.0, 1.10530)])
def test_the_stroke_and_the_dew_point_set_the_node(stroke, p_settled):
    """The node settles where what the condenser leaves on its dew point is what PV-323203 passes,
    G - cap(P) = m_702(P) (B-30, decided 2026-10-15): 1.148 bar a at 10 %, 1.105 at 50 %, where
    V1's constant capacity left the stroke alone to set it, 1.81 and 1.03."""
    r, _, _, _, _ = _run(1800.0, pic_man=stroke)
    assert r.gen_kgh == pytest.approx(r.m_702_kgh, abs=0.02)
    assert r.p_bara == pytest.approx(p_settled, abs=1e-5)


def test_the_node_follows_its_gas_in_seconds():
    """701 up 10 %, PV-323203 held at 25 %: the condenser takes most of the extra gas on a dew point
    raised by the node, which goes from 1.13 to 1.158 bar a within 4.4 s, venting 486 kg/h (V1's
    constant capacity: 883 kg/h and 1.52 bar a)."""
    r, at, _, _, _ = _run(1800.0, m701=_step(1.1), pic_man=25.0, trace=(14.4, 20.0))
    assert r.gen_kgh == pytest.approx(485.7, abs=0.1)
    assert (at[14.4].p_bara, at[20.0].p_bara) == pytest.approx((1.15852, 1.15849), abs=1e-5)
    assert r.p_bara == pytest.approx(1.15840, abs=1e-5)


# ======================================================================================
# 2. Handoff B-30, decided 2026-10-15: the condenser holds the node on its dew point
# ======================================================================================

def test_the_dew_point_capacity_is_anchored_on_v1s_constant():
    """cap = 5589 (T_dew - 35) / 10, T_dew = 45 + Tsat(P) - Tsat(1.13): V1's 5589 kg/h at the
    design node to the bit, about 14 100 kg/h per bar about it, nothing below 0.79 bar a."""
    assert fc.condensation_capacity_kgh(e.E011_P_BARA) == e.E011_CONDENSATION_CAPACITY_DES_KGH
    assert fc.dew_point_c(e.E011_P_BARA) == e.E011_T_C
    slope = (fc.condensation_capacity_kgh(1.14) - fc.condensation_capacity_kgh(1.12)) / 0.02
    assert slope == pytest.approx(14121.8, abs=0.1)
    assert fc.condensation_capacity_kgh(0.78) == 0.0 < fc.condensation_capacity_kgh(0.80)


def test_below_v1s_capacity_the_node_holds_on_its_dew_point():
    """701 down 10 % puts the gas 3 kg/h under V1's 5589 kg/h, PV-323203 held at 25 %. V1's node
    empties to its 0.1 bar a floor, 248.8 s on, its vent running backwards (the equivalence test).
    On the dew point the node falls only until the condenser leaves what the vent passes:
    1.102 bar a within 6 s, 391 kg/h vented, no floor, not a gram created."""
    r, at, first, created, _ = _run(1800.0, m701=_step(0.9), pic_man=25.0, trace=(15.6,))
    assert at[15.6].p_bara == pytest.approx(1.10233, abs=1e-5)
    assert "node floor" not in first and abs(created) < 1e-9
    assert (r.p_bara, r.m_702_kgh) == (pytest.approx(1.10244, abs=1e-5),
                                        pytest.approx(390.58, abs=0.01))
    assert r.gen_kgh == pytest.approx(r.m_702_kgh, abs=0.02)


def test_below_v1s_capacity_pic_323203_trims_the_node_back_to_its_set_point():
    """The same cut in AUTO. V1's node stood at 0.896 bar a with the vent shut, below the absorber
    it vents to. On the dew point the node dips to 1.105 bar a, PIC-323203 closes PV-323203 from
    25 to 16 % in ten minutes, and the node climbs back towards 1.13 (1.121 after half an hour)."""
    r, at, first, _, _ = _run(1800.0, m701=_step(0.9), trace=(60.0, 600.0))
    assert (at[60.0].p_bara, at[60.0].pic_op_pct) == (pytest.approx(1.10463, abs=1e-5),
                                                       pytest.approx(22.714, abs=1e-3))
    assert (at[600.0].p_bara, at[600.0].pic_op_pct) == (pytest.approx(1.11142, abs=1e-5),
                                                         pytest.approx(16.049, abs=1e-3))
    assert r.p_bara == pytest.approx(1.12121, abs=1e-5) and "node floor" not in first


def test_a_shut_vent_stands_on_the_condensers_ceiling():
    """PV-323203 shut on the design load. V1's node has no ceiling of its own: 7.1 bar a at 100 s,
    SV32357 lifting from 110 s (the next test). On the dew point the node rises until the
    condenser takes the whole gas, 1.1615 bar a within 10 s, and SV32357 never lifts."""
    r, at, first, created, _ = _run(1800.0, pic_man=0.0, trace=(10.0,))
    assert at[10.0].p_bara == pytest.approx(1.16162, abs=1e-5)
    assert r.p_bara == pytest.approx(1.16152, abs=1e-5) and abs(r.gen_kgh) < 0.02
    assert not r.relief_lifted and r.m_relief_kgh == 0.0 and abs(created) < 1e-9


def test_sv32357_holds_a_shut_vent():
    """SV32357's law (A-16), on V1's constant capacity, which gives a shut vent no ceiling of its
    own: 7.1 bar a at 100 s, 24.9 at 400 s on the envelope's volume (the equivalence test asserts
    V1's side). SV32357 lifts at its 6.01 bar a set pressure 110.3 s on and vents 816 kg/h of the
    node's vapour, nearly twice the 440 kg/h excess, so the node falls to 5.51 bar a, where the
    valve reseats, and climbs again: a lift every 25.4 s, 12 in 400 s, the peak 6.0125 bar a,
    36.4 kg vented (on the envelope's volume alone, B-51: 82.1 s, 17 lifts every 19.1 s). The
    tank books the relief as it books the vent: not a gram is created."""
    cond = fc.FlashCondenser(dew_capacity=False)
    pic, lic, fic = fc.pic_323203(), fc.lic_323503(), fc.fic_323418()
    pic.set_mode("MAN")
    pic.op = 0.0
    lifts, lifted, p_hi, p_lo, vented, created = [], False, 0.0, 99.0, 0.0, 0.0
    for k in range(1, 4001):
        m_before = cond.m_kg
        r = cond.step(pic, lic, fic, M701, 0.0, 0.0, e.E011_M786_DES_KGH, e.E011_M321_DES_KGH,
                      e.E011_M402_DES_KGH, 0.1)
        created += ((cond.m_kg - m_before)
                    - (r.in_kgh - r.m_702_kgh - r.m_relief_kgh - r.m_718a_kgh - r.m_718b_kgh)
                    / 3600.0 * 0.1)
        if r.relief_lifted and not lifted:
            lifts.append(round(k * 0.1, 6))
        lifted = r.relief_lifted
        vented += r.m_relief_kgh * 0.1 / 3600.0
        p_hi = max(p_hi, r.p_bara)
        if lifts:
            p_lo = min(p_lo, r.p_bara)
    assert lifts[:3] == [110.3, 135.6, 161.1] and len(lifts) == 12
    assert p_hi == pytest.approx(6.0125, abs=1e-4) and p_lo == e.SV32357_RESEAT_BARA == 5.51
    assert vented == pytest.approx(36.40, abs=0.01)
    assert abs(created) < 1e-9


# ======================================================================================
# 3. Handoff B-32, decided: PIC-323203 on its transmitter's span
# ======================================================================================

def _stroke_passing(r) -> float:
    """The PV-323203 stroke whose vent equals the generation at the node's pressure [%]."""
    return 25.0 * r.gen_kgh / 440.0 * (0.13 / (r.p_bara - 1.0)) ** 0.5


def test_pic_323203_holds_the_node_on_its_span_gain():
    """60 %/bar, the table's 0.60 on PT-323203's 1 bar span. 701 up 10 % in AUTO: 1.156 bar a
    after a minute, the condenser taking most of the extra gas, and 1.133 after the hour, at the
    47.33 % stroke that passes what the condenser leaves (on V1's constant capacity: 1.25, then
    1.130 on 50.15 %). A set point of 1.30 on the design load is beyond the condenser's ceiling:
    PIC-323203 shuts the vent and the node stands at 1.1615 bar a, where the condenser takes the
    whole gas (V1's constant capacity reached 1.30 on 16.46 %)."""
    r, at, _, _, _ = _run(3600.0, m701=_step(1.1), trace=(60.0,))
    assert at[60.0].p_bara == pytest.approx(1.15555, abs=1e-5)
    assert r.p_bara == pytest.approx(1.13287, abs=1e-5)
    assert r.pic_op_pct == pytest.approx(_stroke_passing(r), abs=1e-2)
    r, at, _, _, _ = _run(3600.0, pic_sp=1.30, trace=(600.0,))
    assert at[600.0].p_bara == pytest.approx(1.16150, abs=1e-5)
    assert (r.p_bara, r.pic_op_pct) == (pytest.approx(1.16152, abs=1e-5), 0.0)


# ======================================================================================
# 4. 323F004's flash, one tick late, adds to the condenser's restoring force
# ======================================================================================

def _coupled(seconds: float, m314=None, pic_man: float = None, trace: tuple = ()):
    """323F004 on the node's pressure of the tick before, into the condenser."""
    drum, lic5 = ft.FlashTank(), ft.lic_323505()
    cond = fc.FlashCondenser()
    loops = (fc.pic_323203(), fc.lic_323503(), fc.fic_323418())
    if pic_man is not None:
        loops[0].set_mode("MAN")
        loops[0].op = pic_man
    at = {}
    dt = 0.1
    for k in range(1, int(round(seconds / dt)) + 1):
        t = round(k * dt, 6)
        b2 = drum.step(lic5, m314(t) if m314 else R323_M314_DES, d.C003_T_SP_C, d.W_S314,
                       cond.p_bara, d.F010_P_BARA, dt)
        r = cond.step(*loops, b2.m_701_kgh, b2.blowthrough_kgh, 0.0, e.E011_M786_DES_KGH,
                      e.E011_M321_DES_KGH, e.E011_M402_DES_KGH, dt)
        if t in trace:
            at[t] = (b2, r)
    return at


def test_the_flash_tank_and_the_condenser_hold_a_cut():
    """A 10 % cut in the column bottoms. The lower node flashes more out of 323F004 and condenses
    less, and PIC-323203 trims the vent: 1.121 bar a after half an hour, PV-323203 at 8.6 %
    passing 147 kg/h, 323F004 flashing 4007 kg/h. (On V1's constant capacity the vent shut and the
    node settled at 1.129 bar a, where the flash alone equalled the capacity.)"""
    at = _coupled(1800.0, m314=lambda t: R323_M314_DES * (0.9 if t > 10.0 else 1.0),
                  trace=(1800.0,))
    b2, r = at[1800.0]
    assert r.p_bara == pytest.approx(1.12113, abs=1e-5)
    assert (r.pic_op_pct, r.m_702_kgh) == (pytest.approx(8.625, abs=1e-3),
                                           pytest.approx(146.53, abs=0.01))
    assert b2.m_701_kgh == pytest.approx(4007.5, abs=0.1)


def test_the_flash_tank_and_the_condenser_cap_a_shut_vent():
    """PV-323203 shut: the rising node suppresses 323F004's flash and condenses more, and the two
    meet at 1.156 bar a, 4348.8 kg/h flashed (V1's constant capacity, the flash alone: 1.286)."""
    at = _coupled(1800.0, pic_man=0.0, trace=(1800.0,))
    b2, r = at[1800.0]
    assert r.p_bara == pytest.approx(1.15589, abs=1e-5)
    assert b2.m_701_kgh == pytest.approx(4348.8, abs=0.1)
    assert abs(r.gen_kgh) < 0.02


# ======================================================================================
# 5. Handoff B-33, decided: 323P008 cannot pump an empty 323D011
# ======================================================================================

def test_the_flash_lost_runs_the_tank_to_its_heel_and_323p008_loses_suction():
    """The 323F004 flash stops, 323P008's low-level trip off (B-93 is the next test): 3136 kg/h
    still arrives. PIC-323203 shuts the vent 66 s later and the node falls until the condenser
    takes no more than the gas left, 0.875 bar a (V1's constant capacity: 0.695 bar a, the node
    standing where the vent left it). FIC-323418 keeps drawing its 3561.5 kg/h set point, and
    the tank reaches its 1 kg heel at 1993 s. There 323P008 loses suction: 718B falls to what
    arrives, FT-323418 follows it down, FIC-323418 opens fully against it, and nothing is made
    up. (V1 kept drawing 3561.5 kg/h off its floor and made 2.78 t in the same four hours.)"""
    r, _, first, created, (pic, lic, fic) = _run(4 * 3600.0, dt=1.0,
                                                 m701=lambda t: 0.0 if t > 60.0 else M701,
                                                 trip=False)
    assert first["vent shut"] == 126.0 and "node floor" not in first
    assert r.p_bara == pytest.approx(0.87533, abs=1e-5)
    assert first["suction lost"] == first["tank floor"] == 1993.0
    assert r.suction_lost and r.m_kg == e.D011_M_FLOOR_KG
    assert r.in_kgh == pytest.approx(3136.39, abs=0.01)
    assert (r.m_718b_kgh, r.m_718a_kgh) == (pytest.approx(r.in_kgh, rel=1e-12), 0.0)
    assert fic.measurement == pytest.approx(r.m_718b_kgh, rel=1e-9) and fic.loop.op == 100.0
    assert abs(created) < 1e-9


def _trip_cycles(hyst: float) -> tuple:
    """The flash lost for four hours with LT-323503's L2 hysteresis ``hyst``: the stops, the first
    restarts and the level's band in the last hour."""
    cond = fc.FlashCondenser()
    cond.l2_hyst_pct = hyst
    loops = (fc.pic_323203(), fc.lic_323503(), fc.fic_323418())
    stops, was, restarts, levels = 0, False, [], []
    for k in range(1, 4 * 3600 + 1):
        r = cond.step(*loops, 0.0 if k > 60 else M701, 0.0, 0.0, e.E011_M786_DES_KGH,
                      e.E011_M321_DES_KGH, e.E011_M402_DES_KGH, 1.0)
        stops += r.p008_tripped and not was
        if was and not r.p008_tripped:
            restarts.append(k)
        was = r.p008_tripped
        if k > 3 * 3600:
            levels.append(r.level_pct)
    return stops, restarts[:2], min(levels), max(levels)


def test_the_flash_lost_trips_323p008_at_lt_323503s_l2_and_restarts_it_past_its_hysteresis():
    """Handoffs B-93 and B-96, decided 2026-10-14 and 2026-10-15: AC4 stops 323P008A / B while
    LT-323503 stands below its L2, 5 % (PC23.1.9 / 1.10), and runs them again once the level is
    2 % above it (a stated stand-in for the limit's hysteresis). The same flash lost trips the pumps
    at 1755 s, the tank at 118.6 kg; nothing is drawn and nothing is made. On the hysteresis they
    restart at 7 %, 55 s later, and cycle 48 times in four hours, the level between 5.0 and 7.0 %;
    on the live flag they relayed 5808 times, the level held at 4.96-5.04 % (both ways)."""
    r, _, first, created, (pic, lic, fic) = _run(4 * 3600.0, dt=1.0,
                                                 m701=lambda t: 0.0 if t > 60.0 else M701)
    assert first["323P008 tripped"] == 1755.0 and "tank floor" not in first
    assert "suction lost" not in first and abs(created) < 1e-9
    stops, restarts, lo, hi = _trip_cycles(e.LT_323503_L2_HYST_PCT)
    assert (stops, restarts) == (48, [1810, 2074])
    assert (lo, hi) == (pytest.approx(4.995, abs=1e-3), pytest.approx(7.017, abs=1e-3))
    stops, restarts, lo, hi = _trip_cycles(0.0)
    assert (stops, restarts) == (5808, [1756, 1761])
    assert (lo, hi) == (pytest.approx(4.958, abs=1e-3), pytest.approx(5.037, abs=1e-3))


# ======================================================================================
# 6. Handoff A-15, decided 2026-10-03: a full 328D001 overflows into the shell
# ======================================================================================

def _one_tick(over: float, t_over: float = 61.0, live_inlets: bool = True):
    cond = fc.FlashCondenser(live_inlets=live_inlets)
    r = cond.step(fc.pic_323203(), fc.lic_323503(), fc.fic_323418(), M701, 0.0, 0.0,
                  e.E011_M786_DES_KGH, e.E011_M321_DES_KGH, e.E011_M402_DES_KGH, 0.1,
                  m_d001_over_kgh=over, t_d001_over_c=t_over)
    return r, cond


def test_328d001s_overflow_lands_in_the_tank_as_liquid_not_gas_load():
    """30 t/h of the drum's 61 C liquor enters the shell: the feed rises by exactly that, the gas
    load and the condensation do not move, the tank gains it whole on the tick, and its sensible
    heat warms the tank (the vapour space it takes lifts the node 0.3 mbar)."""
    (a, ca), (b, cb) = _one_tick(0.0), _one_tick(30000.0)
    assert b.in_kgh - a.in_kgh == 30000.0
    assert (b.gen_kgh, b.m_cond_kgh, b.m_702_kgh) == (a.gen_kgh, a.m_cond_kgh, a.m_702_kgh)
    assert cb.m_kg - ca.m_kg == pytest.approx(30000.0 / 3600.0 * 0.1, rel=1e-12)
    assert b.t_c > a.t_c and 0.0 < b.p_bara - a.p_bara < 5e-4


def test_with_no_overflow_the_condenser_is_unchanged():
    """No overflow is the condenser as it was, to the bit, whatever temperature is handed in — on
    V1's inlets: the drum's temperature is 786's too since B-31, which warms the tank."""
    (a, _), (b, _) = _one_tick(0.0, live_inlets=False), _one_tick(0.0, 10.0, live_inlets=False)
    assert a == b
    (a, _), (b, _) = _one_tick(0.0), _one_tick(0.0, t_over=10.0)
    assert b.t_c < a.t_c and (b.gen_kgh, b.m_702_kgh) == (a.gen_kgh, a.m_702_kgh)


def test_a_full_envelope_publishes_its_excess():
    """The envelope at its 4204 kg of liquid with 30 t/h of 328D001's overflow arriving and the
    draw shut: the excess leaves as the overflow and the envelope stays full."""
    cond = fc.FlashCondenser()
    pic, lic, fic = fc.pic_323203(), fc.lic_323503(), fc.fic_323418()
    lic.set_mode("MAN"); lic.op = 0.0
    fic.loop.set_mode("MAN"); fic.loop.op = 0.0
    cond.m_kg = e.E011_FULL_KG
    for _ in range(50):
        r = cond.step(pic, lic, fic, M701, 0.0, 0.0, e.E011_M786_DES_KGH, e.E011_M321_DES_KGH,
                      e.E011_M402_DES_KGH, 0.1, m_d001_over_kgh=30000.0)
    assert cond.m_kg == pytest.approx(e.E011_FULL_KG, abs=1e-9)
    assert r.m_overflow_kgh == pytest.approx(
        r.in_kgh - r.m_702_kgh - r.m_relief_kgh - r.m_718a_kgh - r.m_718b_kgh, rel=1e-9)
    assert e.E011_FULL_KG == pytest.approx(4204.4, abs=0.1)


# ======================================================================================
# 7. Handoff B-51, decided 2026-10-07: 323F004's vapour space is part of the node
# ======================================================================================

def _full_envelope(seconds: float, dew_capacity: bool = True):
    """323F004 into a full envelope, 323P008's draw shut, every inlet at design: the minimum and
    maximum node pressure over each minute."""
    drum, lic5 = ft.FlashTank(), ft.lic_323505()
    cond = fc.FlashCondenser(dew_capacity=dew_capacity)
    pic, lic, fic = fc.pic_323203(), fc.lic_323503(), fc.fic_323418()
    for loop in (lic, fic.loop):
        loop.set_mode("MAN")
        loop.op = 0.0
    cond.m_kg = e.E011_FULL_KG
    bands, minute = [], []
    for k in range(1, int(round(seconds / 0.1)) + 1):
        b2 = drum.step(lic5, R323_M314_DES, d.C003_T_SP_C, d.W_S314, cond.p_bara,
                       d.F010_P_BARA, 0.1)
        r = cond.step(pic, lic, fic, b2.m_701_kgh, b2.blowthrough_kgh, 0.0,
                      e.E011_M786_DES_KGH, e.E011_M321_DES_KGH, e.E011_M402_DES_KGH, 0.1)
        minute.append(r.p_bara)
        if k % 600 == 0:
            bands.append((min(minute), max(minute)))
            minute = []
    return bands, r


def test_a_full_envelope_holds_its_node_on_323f004s_vapour_space():
    """With the envelope full its own free volume is V1's 2 % floor, 0.0875 m3. On that alone the
    node limit-cycles against 323F004's flash, one tick late — 0.59 to 1.82 bar a in every minute
    of five. With 323F004's 1.083 m3 in the node the same plant holds 1.1300 bar a, PV-323203 on
    its 25 % design stroke, and the excess leaves as the overflow."""
    bands, r = _full_envelope(300.0)
    assert all(hi - lo < 1e-9 for lo, hi in bands)
    assert r.p_bara == pytest.approx(e.E011_P_BARA, abs=1e-9)
    assert r.pic_op_pct == pytest.approx(e.E011_PV_OP_DES_PCT, abs=1e-6)
    assert r.m_overflow_kgh > 0.0


def test_on_the_envelopes_volume_alone_a_full_envelope_rings(monkeypatch):
    """The alternative the process engineer turned down: the node on the envelope alone, on V1's
    constant capacity. (On the dew point the backward step holds even that, B-30.)"""
    monkeypatch.setattr(fc, "F004_VAPOUR_M3", 0.0)
    bands, _ = _full_envelope(300.0, dew_capacity=False)
    assert all(lo < 0.65 and hi > 1.70 for lo, hi in bands)
    bands, _ = _full_envelope(60.0)
    assert all(hi - lo < 1e-9 for lo, hi in bands)
