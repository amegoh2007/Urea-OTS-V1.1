"""Behaviour of 328D003, the ammonia water tank — `ureasim.units.desorption.ammonia_water_tank`.

Equivalence with V1 is proven in `tests/equivalence/test_ammonia_water_tank_equivalence.py`.
This file pins what the tank DOES: the PFD held at design; the three bays standing at one level,
with 429/490 of any disturbance in compartment III; 735 on FIC-328402 and 744 on 322P002, so the
level takes every imbalance (B-39, decided 2026-10-09: no loop follows the level, which is the
operator's on FIC-328402's set point); the 741 328C004 sends back warming compartment II; the two
limits decided on 2026-09-27 — the pumps stopping at the tank's heel, and the full tank
overflowing; and FIC-328402 as decided the same day (B-38) — on the DCS table's gain, its
transmitter reading what 328P003 delivers. The four valves run their vendor trims (B-44, decided
2026-09-30), on which every number here was measured. FIC-328406 and its valve are 328C004's
(B-50): 741 arrives here as a boundary.
"""

from __future__ import annotations

import pytest

from ureasim.control.valve import cv_fraction
from ureasim.data import unit_328d003 as d
from ureasim.units.desorption import ammonia_water_tank as awt

COND = (d.D003_M719_DES_KGH, d.D003_M720_DES_KGH, d.D003_M721_DES_KGH, d.D003_M759_DES_KGH)
M343 = 34180.0


def _run(ticks, dt=0.5, m343=M343, cond=1.0, m741=0.0, p002=True,
         tank=None, loops=None, every=None):
    tank = tank or awt.AmmoniaWaterTank()
    loops = loops or awt.TankLoops()
    b = None
    for k in range(ticks):
        b = tank.step(loops, m343, *(v * cond for v in COND), m741, p002, dt)
        if every:
            every(k, b)
    return tank, loops, b


def _total(tank):
    return tank.m_i_kg + tank.m_ii_kg + tank.m_iii_kg


def test_the_design_holds_every_pfd_draw():
    seed = awt.AmmoniaWaterTank()
    tank, loops, b = _run(600, dt=0.1)
    assert (b.m_735_kgh, b.m_744_kgh, b.m_734_kgh, b.m_791_kgh, b.m_793_kgh, b.m_741_kgh) == (
        31114.0, 31478.0, 1534.0, 1534.0, 0.0, 0.0)
    assert (b.in_i_kgh, b.out_i_kgh, b.in_ii_kgh, b.out_ii_kgh) == (31478.0, 31478.0, 34182.0,
                                                                   34182.0)
    assert (tank.m_i_kg, tank.m_ii_kg, tank.m_iii_kg, tank.t_i_c, tank.t_ii_c) == (
        seed.m_i_kg, seed.m_ii_kg, seed.m_iii_kg, 44.0, 56.0)
    assert tank.t_iii_c == pytest.approx(seed.t_iii_c, abs=1e-12)
    assert b.level_i_pct == b.level_ii_pct == b.level_iii_pct == 50.0
    assert not (b.suction_lost_i or b.suction_lost_ii) and b.m_overflow_kgh == 0.0


def test_the_bays_stand_at_one_level_and_compartment_iii_takes_429_of_490():
    """The condensates up 30 % for an hour: compartment I's surplus spreads over all three bays,
    so the levels rise together, and compartment III — 429 of the 490 m3 — holds that share."""
    seed = awt.AmmoniaWaterTank()
    tank, loops, b = _run(7200, cond=1.3)
    assert b.level_i_pct == pytest.approx(51.9428283, abs=1e-6)
    assert b.level_ii_pct == pytest.approx(b.level_i_pct, rel=1e-12)
    assert b.level_iii_pct == pytest.approx(b.level_i_pct, rel=1e-12)
    assert ((tank.m_iii_kg - seed.m_iii_kg) / (_total(tank) - _total(seed))
            == pytest.approx(429.0 / 490.0, rel=1e-12))
    # FIC-328402 holds 735 on its set point (B-39): the whole surplus stays in the tank, where
    # V1's 735, following compartment II's holdup, took 1134.7 kg/h of it (51.82 %).
    assert b.m_735_kgh == d.M735_DES_KGH
    # The back-solved heat term holds compartment I at 44 C on the condensates, whatever flow.
    assert b.t_i_c == pytest.approx(44.0, abs=1e-9)


def test_322p002_stopped_fills_the_tank():
    """322P002 stopped for an hour: 744 stops and the tank takes its 31 478 kg/h, 56.48 % after
    the hour; FIC-328402 holds 735 where it was (B-39). V1's 735, following the level, took
    3782 kg/h of it (56.08 %). Restarted, 322P002 delivers the design 744 at once: it has no
    control valve (P&ID 102)."""
    tank, loops, b = _run(7200, p002=False)
    assert b.m_744_kgh == 0.0
    assert b.level_ii_pct == pytest.approx(56.4758887, abs=1e-6)
    assert b.m_735_kgh == d.M735_DES_KGH
    assert loops.fic_328402.loop.op == d.FIC_328402_OP_DES_PCT
    tank, loops, b = _run(1, tank=tank, loops=loops)
    assert b.m_744_kgh == d.M744_DES_KGH


def test_fic_328402_on_the_tables_gain():
    """Set point 31.4 to 25 m3/h: 0.75 per cent of the 0-70 m3/h span moves 735 monotonically,
    within 1 % of the new set point in 414.7 s on FV-328402's trim."""
    loops, pv = awt.TankLoops(), []
    loops.fic_328402.loop.sp = 25.0
    _run(12000, dt=0.1, loops=loops, every=lambda k, b: pv.append(loops.fic_328402.loop.pv))
    assert all(later <= earlier for earlier, later in zip(pv, pv[1:]))
    assert next(k for k, v in enumerate(pv) if v - 25.0 < 0.25) == 4147
    assert pv[-1] == pytest.approx(25.0, abs=2e-3)
    assert loops.fic_328402.loop.Kc == 0.75 * 100.0 / d.FT_328402_SPAN_M3H


def test_343_gone_draws_compartment_ii_down():
    """323C005's bottoms gone for an hour: 328P003 goes on drawing the header and the tank falls
    to 42.97 % (V1's 735, following the level, slowed it to 43.40 %)."""
    tank, loops, b = _run(7200, m343=0.0)
    assert b.level_ii_pct == pytest.approx(42.9682357, abs=1e-6)
    assert b.m_735_kgh == d.M735_DES_KGH
    assert b.t_ii_c == pytest.approx(53.1648375, abs=1e-6)


def test_741_back_to_compartment_ii():
    """What FV-328406 half open passes, its trim's 22.4 % of its 77 169 kg/h, taken into
    compartment II at 40 C for an hour: the tank rises to 53.55 % and cools to 51.15 C."""
    m741 = d.S741_CAP_KGH * cv_fraction(0.5, d.FV_328406_CHAR)
    assert m741 == pytest.approx(17255.617, abs=1e-3)
    tank, loops, b = _run(7200, m741=m741)
    assert b.m_741_kgh == m741 and b.in_ii_kgh == M343 + m741 + d.D003_ROUNDING_II_KGH
    assert b.level_ii_pct == pytest.approx(53.5499541, abs=1e-6)
    assert b.t_ii_c == pytest.approx(51.1548257, abs=1e-6)


def test_the_pumps_stop_at_the_tanks_heel():
    """Nothing arriving, from 300 kg: 322P002 loses suction at 13.8 s and 328P003 at 14.6 s (with
    735 on FIC-328402, B-39 — V1's 735 fell with the level, 26.1 and 31.6 s); the tank holds its
    heel level, 27.2 kg, and makes nothing but V1's 1 kg/h rounding."""
    tank = awt.AmmoniaWaterTank()
    tank.m_i_kg, tank.m_ii_kg, tank.m_iii_kg = (300.0 * f / sum(awt.FULL_KG) for f in awt.FULL_KG)
    events, made = {}, [0.0]

    def watch(k, b):
        if b.suction_lost_i:
            events.setdefault("i", k)
        if b.suction_lost_ii:
            events.setdefault("ii", k)

    loops = awt.TankLoops()
    for k in range(3000):
        before = _total(tank)
        b = tank.step(loops, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, True, 0.1)
        watch(k, b)
        made[0] += (_total(tank) - before - (b.in_i_kgh + b.in_ii_kgh - b.out_i_kgh
                                            - b.out_ii_kgh) * 0.1 / 3600.0)
    assert events == {"i": 137, "ii": 145}
    assert _total(tank) == pytest.approx(awt.HEEL_LEVEL * sum(awt.FULL_KG), rel=1e-12)
    assert (tank.m_i_kg, tank.m_ii_kg) == pytest.approx((1.0, 43.0 / 18.0), rel=1e-12)
    # 322P002 gives nothing; 328P003 pumps out only the +2 kg/h rounding, shared by its legs.
    assert b.m_744_kgh == 0.0
    assert b.m_735_kgh + b.m_734_kgh + b.m_791_kgh + b.m_793_kgh == pytest.approx(2.0, rel=1e-9)
    # The transmitters read what is delivered, so FIC-328402 sees its shortfall and opens.
    assert loops.fic_328402.measurement == pytest.approx(b.m_735_kgh, rel=1e-9)
    assert b.m_735_kgh < 2.0 and loops.fic_328402.loop.op == 100.0
    assert 0.0 <= made[0] <= 300.0 * d.D003_ROUNDING_I_KGH / 3600.0


def test_a_full_tank_overflows():
    """All of 328C004's design bottoms, 33 724 kg/h, recycled as 741 from 99.95 %: the tank
    overflows at 25.5 s and settles at 100 % with the whole 33 724 kg/h over the top, FIC-328402
    holding 735 at its set point (B-39). V1's 735, at twice its design at full, took all but
    2610 kg/h, and the tank first overflowed at 333.5 s."""
    tank = awt.AmmoniaWaterTank()
    tank.m_i_kg, tank.m_ii_kg, tank.m_iii_kg = (0.9995 * f for f in awt.FULL_KG)
    loops = awt.TankLoops()
    first, unbooked = None, 0.0
    for k in range(14400):
        before = _total(tank)
        b = tank.step(loops, M343, *COND, d.C004_M739_DES_KGH, True, 0.5)
        if first is None and b.m_overflow_kgh > 0.0:
            first = k
        unbooked += (_total(tank) - before - (b.in_i_kgh + b.in_ii_kgh - b.out_i_kgh
                                             - b.out_ii_kgh - b.m_overflow_kgh) * 0.5 / 3600.0)
    assert first == 51
    assert b.m_overflow_kgh == pytest.approx(d.C004_M739_DES_KGH, abs=1e-5)
    assert b.t_overflow_c == pytest.approx(51.5553376, abs=1e-6)
    assert max(b.level_i_pct, b.level_ii_pct, b.level_iii_pct) == pytest.approx(100.0, abs=1e-9)
    assert (b.m_735_kgh, b.m_741_kgh) == (d.M735_DES_KGH, d.C004_M739_DES_KGH)
    # Every kilogram is booked: what came in, less what the pumps and the overflow took.
    assert abs(unbooked) < 1e-6


def test_the_heel_is_one_level_for_the_whole_tank():
    assert awt.HEEL_I_KG == d.D003_M_FLOOR_KG == 1.0
    assert awt.HEEL_II_KG == pytest.approx(43.0 / 18.0, rel=1e-12)
    assert awt.HEEL_LEVEL * d.D003_MI_FULL_KG == pytest.approx(1.0, rel=1e-15)
