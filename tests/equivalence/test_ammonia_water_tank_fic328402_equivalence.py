"""V1 <-> V1.1 equivalence for FIC-328402 on 328D003 — the decided divergences of handoffs B-38
and B-39.

What is being proved
--------------------
Handoff B-39, decided 2026-10-09 (and B-87's option c): FIC-328402 meters PFD 735, 328P003's feed
to 328E007 and the desorbers, as every plant source puts it, and 744 is what 322P002 delivers — it
has no control valve on P&ID 102. V1 hangs the loop on 744 and draws 735 in proportion to
compartment II's holdup, a level-following draw the plant does not have (LT-328507 and LT-328508
are open-loop indicators): in Phase 7's cold start it doubled 735 when compartment I filled.

Handoff B-38, decided 2026-09-27, rides with the loop onto 735: the loop carries the DCS table's
0.75 read per cent of FT-328402's 0-70 m3/h span, where V1 runs 0.06 per kg/h, and FT-328402 reads
the flow 328P003 delivers when the tank's heel caps it.

Each runs both ways on the transcription in `test_ammonia_water_tank_equivalence.py`: its ``b39``
switch carries the loop's place, its ``decided`` switch the gain and the transmitter — the port
against the switched transcription tick by tick, and V1 against the port, bit-exact to the tick
the departure first acts, then V1's behaviour asserted on V1's side and the port's on the port's.
All at the engine's 0.1 s step, on FV-328402's vendor trim (handoff B-44, ``valves_decided``).
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_328d003 as d
from ureasim.units.desorption import ammonia_water_tank as awt
from tests.equivalence import test_ammonia_water_tank_equivalence as tank_eq
from tests.equivalence.v1_loader import v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

#: V1's namespace for the tank, built as the tank's own equivalence test builds it.
v1 = tank_eq.v1

DT = 0.1
SP_25 = tank_eq._sp("FIC_328402", "fic_328402", 25.0)


def STOP_RESTART(k):
    """322P002 A and B stopped at 1 s and started again two minutes later."""
    return tank_eq._design(p002=not 10 <= k < 1210)


def _both(v1, script, ticks, act=None, decided=False, b39=True, start=None, dt=DT):
    """V1 on its own gain and transmitter (``decided``) and its own structure (``b39``), the
    valve as decided, and the port side by side, one tick at a time."""
    s = tank_eq._v1_state(v1, decided, b39=b39)
    tank, loops = awt.AmmoniaWaterTank(), awt.TankLoops()
    if start:
        tank_eq._set_state(s, tank, *start)
    for k in range(ticks):
        if act:
            act(k, s, loops)
        x = script(k)
        tank_eq._feed(s, x)
        a = tank_eq._v1_stage2(v1, s, x["m343"], dt, decided=decided)
        b = tank_eq._port(tank, loops, x, dt)
        yield k, s, a, b, tank, loops


def _tank(s):
    return (s.a328_d003_MI, s.a328_d003_MII, s.a328_d003_MIII, s.a328_d003_TI, s.a328_d003_TII,
            s.a328_d003_TIII)


def test_the_gain_is_the_tables_per_cent_of_span(v1):
    """V1 seeds 0.06 per kg/h in m3/h, on 744; the port 0.75 per cent of output per cent of
    0-70 m3/h."""
    s = tank_eq._v1_state(v1, b39=False)
    assert (s.FIC_328402["Kc"], s.FIC_328402["Ti"]) == (0.06 * v1["RHO_744_KGM3"], 60.0)
    loop = awt.TankLoops().fic_328402.loop
    assert (loop.Kc, loop.Ti) == (d.FIC_328402_KC, d.FIC_328402_TI_S)
    assert d.FIC_328402_KC == 0.75 * 100.0 / 70.0
    assert s.FIC_328402["Kc"] / loop.Kc == pytest.approx(56.1391, abs=1e-4)


@pytest.mark.parametrize("script, act", [(STOP_RESTART, None),
                                         (lambda k: tank_eq._design(), SP_25)],
                         ids=["322P002 stopped and restarted", "FIC-328402 to 25 m3/h"])
def test_the_port_against_its_transcription(v1, script, act):
    tank_eq._run(v1, script, 3000, DT, act=act, decided=True)


def test_the_set_point_move_decided_divergence(v1):
    """B-38. FIC-328402, on 735 both sides, from 31.4 to 25 m3/h: both loops move monotonically,
    V1's within 1 % of the new set point in 198.5 s, the port's in 414.7 s."""
    within, last = {}, {"v1": 31.4, "port": 31.4}
    for k, s, a, b, tank, loops in _both(v1, lambda k: tank_eq._design(), 12010, SP_25):
        if k < 10:
            tank_eq._assert_tick(a, b, s, tank, loops, f"tick {k}")
        elif k == 10:
            assert a["735"] != b.m_735_kgh  # the controllers part on the move itself
        pv = {"v1": s.FIC_328402["pv"], "port": loops.fic_328402.loop.pv}
        for side, value in pv.items():
            assert value <= last[side] + 1e-12, (side, k)
            last[side] = value
            if k > 10 and abs(value - 25.0) < 0.25:
                within.setdefault(side, k)
    assert {side: (k - 10) * DT for side, k in within.items()} == pytest.approx(
        {"v1": 198.5, "port": 414.7}, abs=1e-9)
    assert (s.FIC_328402["pv"], loops.fic_328402.loop.pv) == pytest.approx((25.0, 25.0), abs=2e-3)


def test_the_condensates_up_decided_divergence(v1):
    """B-39. The vacuum train's condensates up 30 % for an hour, from 1 s. Bit-exact until they
    rise; then V1's 735, following compartment II's holdup, takes 1133.2 kg/h of the surplus and
    the tank stands at 51.8 %; the port's FIC-328402 holds 735 on its set point and the tank takes
    the whole surplus, 51.94 %. 744 is the PFD's on both."""
    cond = {k: 1.3 * v for k, v in tank_eq.COND.items()}
    for k, s, a, b, tank, loops in _both(v1, tank_eq._step(10, **cond), 7200, decided=True,
                                         b39=False, dt=0.5):
        if k < 10:   # the loops sit on different streams; the tank and its draws are the same
            assert (a["735"], a["744"], _tank(s)) == (b.m_735_kgh, b.m_744_kgh, (
                tank.m_i_kg, tank.m_ii_kg, tank.m_iii_kg, tank.t_i_c, tank.t_ii_c, tank.t_iii_c)), k
        assert a["744"] == b.m_744_kgh == d.M744_DES_KGH, k
    assert a["735"] == pytest.approx(32247.180, abs=1e-3) and b.m_735_kgh == d.M735_DES_KGH
    assert a["LI"]["LI_328II"] == 51.8
    assert b.level_ii_pct == pytest.approx(51.9401300, abs=1e-6)


def test_a_full_compartment_doubles_735_decided_divergence(v1):
    """B-39, B-87's link 4. The tank at 99.95 % on the design inflows: V1 draws 735 at 1.999 times
    its design, 62 197 kg/h, into 328E007 and the desorbers; the port's FIC-328402 holds 31 114."""
    _, s, a, b, _, _ = next(_both(v1, lambda k: tank_eq._design(), 1, decided=True, b39=False,
                                  start=tank_eq.NEAR_FULL))
    assert a["735"] == pytest.approx(1.999 * d.M735_DES_KGH, rel=1e-12)
    assert b.m_735_kgh == d.M735_DES_KGH
