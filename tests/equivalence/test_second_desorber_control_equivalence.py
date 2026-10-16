"""V1 <-> V1.1 equivalence for 328C004's control structures — handoffs B-49 and B-50, B-48 kept.

What is being proved
--------------------
On 2026-09-30 the process engineer decided that V1 had missed control wiring the P&IDs and the
functional diagrams show, and that the port wires it as drawn:

  * **B-49** — FFIC-329401 is a ratio station (UD-MR-329-FF-0002 page 2, RATIOSTN): FIC-329401's
    set point is the ratio set point times the feed, FIC-328402's 735 in m3/h, times 1000 kg/t.
    V1 runs a PI on the measured ratio (8.0e5, 40 s) whose output is that set point.
  * **B-50** — LIC-328505 is FIC-328406's master (UD-MR-328-FF-0002 page 2): while FIC-328406 is
    in cascade, LIC-328505's output / 100 x FIC-328406:MAX, FT-328406's 60 m3/h, is its set point
    and LV-328505 is switched shut; 741 leaves 328C004's bottoms ahead of LV-328505 (P&ID sheet
    104). V1 steps FIC-328406 in 328D003's stage with no master, its set point to 34.0 m3/h, and
    takes 741 out of 740 downstream of the column: its column never sees it.

The third, **B-48** — TIC-328012 onto FIC-329402's set point — was measured and kept as V1 has
it: on V1's PV, T - T_746, the drawn cascade runs away (deferred to Phase 7, for a tray
temperature to control on). Its test here proves TIC-328012's output still drives nothing.

`test_second_desorber_equivalence.py` carries both structures as its transcription's "station"
and "recycle" switches and compares the port with it on every tick of every scenario. Here the
operator's moves those scenarios do not make — modes switched mid-run, a cascade closed — run
the same way, the port against the transcription with every departure on each tick, while V1's
own structure runs beside it: bit-exact until the structure first acts, then each side's
behaviour asserted. What makes each a true station and a true cascade is asserted on the port,
tick by tick.
"""

from __future__ import annotations

import pytest

from ureasim.data import desorption_train as t
from ureasim.data import unit_328c004 as c
from ureasim.data.unit_328d003 import FT_328406_SPAN_M3H, M735_DES_KGH
from ureasim.units.desorption import second_desorber as sd
from tests.equivalence import test_hydrolyser_equivalence as c003_eq
from tests.equivalence import test_second_desorber_equivalence as c004_eq
from tests.equivalence.v1_loader import v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

#: V1's namespaces, built as 328C004's own equivalence test builds them.
tank_v1 = c004_eq.tank_v1
e007_v1 = c004_eq.e007_v1
c002_v1 = c004_eq.c002_v1
c003_v1 = c004_eq.c003_v1
v1 = c004_eq.v1

ALL = c004_eq.ALL
DT = 0.5


def _ticks(v1, script, ticks, act, v1_decided):
    """V1's structure beside the port, one tick at a time. The port is compared on every tick
    with the transcription carrying every departure; V1 runs with `v1_decided`. `act(k, states,
    loops)` moves the controllers of both V1 states and the port's before tick k. Yields the
    tick, V1's tick, the port's result, V1's state, the column and its loops."""
    s, s_all = c004_eq._v1_state(v1, v1_decided), c004_eq._v1_state(v1)
    col, loops = sd.SecondDesorber(fv_329401=sd.V1_FV_329401), sd.SecondDesorberLoops(fic_329401=sd.fic_329401(sd.V1_FV_329401))
    for k in range(ticks):
        act(k, (s, s_all), loops)
        x = script(k)
        for state in (s, s_all):
            c004_eq._feed(state, x)
        a = c004_eq._v1_c004(v1, s, x["m749"], x["t749"], DT, v1_decided)
        a_all = c004_eq._v1_c004(v1, s_all, x["m749"], x["t749"], DT)
        b = c004_eq._port(col, loops, x, DT)
        c004_eq._assert_tick(a_all, b, s_all, col, loops, f"tick {k}")
        yield k, a, b, s, col, loops


def _parted(k, a, b, s, col, loops, seen: dict) -> None:
    """Record the first tick V1's structure and the port's part."""
    if "parted" not in seen:
        try:
            c004_eq._assert_tick(a, b, s, col, loops, f"tick {k}")
        except AssertionError:
            seen["parted"] = k


def _idle(k, states, loops):
    pass


def _loop(loops, name):
    loop = getattr(loops, name)
    return loop.loop if isinstance(loop, sd.FlowLoop) else loop


def _mode(v1_name, name, mode, t0, op=None):
    """A loop put in `mode` before tick t0, on both V1 states and the port — in MAN at `op`."""
    def act(k, states, loops):
        if k == t0:
            for s in states:
                getattr(s, v1_name)["mode"] = mode
                if op is not None:
                    getattr(s, v1_name)["op"] = op
            loop = _loop(loops, name)
            loop.set_mode(mode)
            if op is not None:
                loop.op = op
    return act


def _then(*acts):
    def act(k, states, loops):
        for a in acts:
            a(k, states, loops)
    return act


def _ratio_sp(value, t0):
    def act(k, states, loops):
        if k == t0:
            for s in states:
                s.FFIC_329401["sp"] = value
            loops.ffic_329401.set_sp(value)
    return act


def _feed_m3h(x) -> float:
    return x["m735"] / c.RHO_735_KGM3


# --------------------------------------------------------------------------------------
# B-49: FFIC-329401, a ratio station
# --------------------------------------------------------------------------------------

def test_ffic_329401_a_ratio_station_decided_divergence(v1):
    """B-49, decided 2026-09-30. 735 cut a fifth. V1's PI on the measured ratio slams
    FIC-329401's set point to 0 kg/h for 54 s, the steam falling fastest while it is there, and
    settles at the ratio's 5196 kg/h in five minutes; the port's station asks 5196 kg/h on the
    tick the feed moves and on every tick after it, and the steam follows at FIC-329401's own
    pace. They part on the tick the feed moves."""
    script = c004_eq._step(10, m735=0.8 * M735_DES_KGH)
    seen, zero, steam = {}, [], {}
    for k, a, b, s, col, loops in _ticks(v1, script, 1810, _idle, ALL - {"station"}):
        _parted(k, a, b, s, col, loops, seen)
        if k >= 10:
            assert b.ffic_op_kgh == pytest.approx(0.8 * t.C004_M931_DES_KGH, rel=1e-12)
            assert loops.fic_329401.loop.sp == b.ffic_op_kgh
        if a["ffic_op"] == 0.0:
            zero.append(k)
        if (k - 9) % 60 == 0 and k > 9:
            steam[(k - 9) * DT] = (a["931"], b.m_931_kgh)
    # FV-329401's pressure term (B-73) carries the column's last-bit pressure drift into the
    # measured ratio, which V1's PI amplifies: the two part in the last bits before the feed moves.
    assert seen["parted"] <= 10
    assert (zero[0], zero[-1], len(zero)) == (10, 116, 107)
    expected = {30.0: (6048.14, 6406.34), 60.0: (5643.13, 6326.85), 120.0: (5235.37, 6182.49),
                300.0: (5195.96, 5847.88), 900.0: (5196.00, 5355.62)}
    for when, pair in expected.items():
        assert steam[when] == pytest.approx(pair, abs=0.01), when


def test_the_station_sets_the_slave_on_the_tick(v1):
    """On every tick in cascade FIC-329401's set point is the station's output, and that is the
    ratio set point times the feed times 1000: through a feed cut, a feed rise and a ratio set
    point move — which FIC-329401 receives on the tick it is made, where V1's PI would have
    moved it 431 kg/h. The feed moves do not touch the ratio set point."""
    def script(k):
        return c004_eq._design(m735=M735_DES_KGH * (1.0 if k < 10 else 0.8 if k < 600 else 1.1))

    ratio = c.FFIC_329401_RATIO_DES
    for k, a, b, s, col, loops in _ticks(v1, script, 1800, _ratio_sp(0.25, 1200), ALL):
        st, x = loops.ffic_329401, script(k)
        assert st.sp == (ratio if k < 1200 else 0.25)
        assert loops.fic_329401.loop.mode == "CAS"
        assert loops.fic_329401.loop.sp == b.ffic_op_kgh == st.op == min(
            st.sp * _feed_m3h(x) * 1000.0, c.FFIC_329401_OP_HI_KGH)
    assert loops.fic_329401.loop.sp == pytest.approx(0.25 * 1.1 * 31.4 * 1000.0, rel=1e-12)
    q = c004_eq._both(v1, lambda k: c004_eq._design(), 1, DT,
                      c004_eq._set_point("FFIC_329401", "ffic_329401", 0.25), ALL - {"station"})
    assert q.parted == 0
    assert (q.a["ffic_op"], q.b.ffic_op_kgh) == (pytest.approx(6926.53, abs=0.01), 7850.0)


def test_the_station_tracks_and_returns_bumpless(v1):
    """FV-329401 put in MAN at 30 % for ten minutes, then back in cascade. While FIC-329401 is not
    listening the station's ratio set point tracks the measured ratio, so on the tick it returns
    its set point is the flow it was passing and its output does not move. V1's PI winds up to
    its 12 000 kg/h limit against the stroke and hands FIC-329401 that on return: a bump."""
    man = _mode("FIC_329401", "fic_329401", "MAN", 10, op=30.0)
    cas = _mode("FIC_329401", "fic_329401", "CAS", 1210)
    seen, before = {}, None
    for k, a, b, s, col, loops in _ticks(v1, lambda k: c004_eq._design(), 1810, _then(man, cas),
                                         ALL - {"station"}):
        _parted(k, a, b, s, col, loops, seen)
        st, fic = loops.ffic_329401, loops.fic_329401
        if 10 <= k < 1210:
            assert fic.loop.mode == "MAN" and st.sp == b.ffic_pv
        if k == 1209:
            before = (b.m_931_kgh, fic.loop.op, a["ffic_op"])
        if k == 1210:
            # The flow it was passing, last tick's: FV-329401's pressure term moves (B-73).
            assert fic.loop.sp == pytest.approx(before[0], rel=1e-8)
            assert fic.loop.op == pytest.approx(before[1], abs=1e-7)
            assert (before[2], s.FIC_329401["sp"]) == (c.FFIC_329401_OP_HI_KGH,
                                                       c.FFIC_329401_OP_HI_KGH)
    # B-73's pressure term carries the column's last-bit drift into V1's PI (see above).
    assert seen["parted"] <= 11
    assert fic.loop.op == pytest.approx(30.0, abs=1e-5)


# --------------------------------------------------------------------------------------
# B-50: LIC-328505 on FIC-328406, 741 drawn from the column
# --------------------------------------------------------------------------------------

def test_lic_328505_cascades_fic_328406_decided_divergence(v1):
    """B-50, decided 2026-09-30. FIC-328406 put in cascade at the design point. V1's column never
    sees it: 741 leaves 740 downstream, LV-328505 goes on holding 50 %. The port's LV-328505 is
    switched shut and the whole bottoms recycle as 741 on LIC-328505's output across FT-328406's
    60 m3/h — 54.0 m3/h on the switch, above V1's 34.0 m3/h limit. The level swings 30.7-77.2 %
    in the first quarter hour and is back within 0.3 % of 50 % in two hours, 741 within 1 % of
    the design bottoms, LIC-328505 near 57.5 %."""
    levels_15, seen = [], {}
    act = _mode("FIC_328406", "fic_328406", "CAS", 0)
    for k, a, b, s, col, loops in _ticks(v1, lambda k: c004_eq._design(), 14400, act,
                                         ALL - {"recycle"}):
        _parted(k, a, b, s, col, loops, seen)
        fic = loops.fic_328406.loop
        assert (b.lv_op_pct, b.m_export_kgh, b.m_739_kgh) == (0.0, 0.0, b.m_741_kgh)
        assert fic.sp == pytest.approx(b.lic_op_pct / 100.0 * FT_328406_SPAN_M3H, rel=1e-12)
        assert (a["741"], a["739"]) == (0.0, pytest.approx(t.C004_M739_DES_KGH, rel=1e-12))
        assert a["LI_328505"] == pytest.approx(50.0, abs=1e-9)
        if k == 0:
            assert fic.sp == pytest.approx(54.04, abs=0.01) and fic.sp > s.FIC_328406["sp_hi"]
        if k < 1800:
            levels_15.append(b.level_pct)
    assert seen["parted"] == 0
    assert (min(levels_15), max(levels_15)) == (pytest.approx(30.66, abs=0.01),
                                                pytest.approx(77.16, abs=0.01))
    assert b.level_pct == pytest.approx(50.0, abs=0.3)
    assert b.m_741_kgh == pytest.approx(t.C004_M739_DES_KGH, rel=0.01)
    assert b.lic_op_pct == pytest.approx(57.47, abs=0.01)


def test_fv_328406_in_man_draws_from_the_column_decided_divergence(v1):
    """FV-328406 put at 50 % by hand: its trim's 17 256 kg/h leaves 328C004's bottoms ahead of
    LV-328505 on the first tick, and LIC-328505 takes LV-328505 back to 66.1 % over the hour,
    the export 16 468 kg/h and the bottoms 33 724 again. V1's column goes on at 50 % sending
    33 724 kg/h to 740, from which V1's tank takes its 741 (the tank's file)."""
    seen = {}
    act = _mode("FIC_328406", "fic_328406", "MAN", 0, op=50.0)
    for k, a, b, s, col, loops in _ticks(v1, lambda k: c004_eq._design(), 7200, act,
                                         ALL - {"recycle"}):
        _parted(k, a, b, s, col, loops, seen)
        assert b.m_741_kgh == pytest.approx(17255.617, abs=1e-3)
        assert b.m_739_kgh == b.m_export_kgh + b.m_741_kgh and b.lv_op_pct == b.lic_op_pct
        assert (a["741"], a["LI_328505"]) == (0.0, pytest.approx(50.0, abs=1e-9))
        if k == 0:
            assert b.m_739_kgh == pytest.approx(t.C004_M739_DES_KGH + 17255.617, abs=1e-3)
    assert seen["parted"] == 0
    assert (b.m_export_kgh, b.m_739_kgh, b.lic_op_pct) == (
        pytest.approx(16468.44, abs=0.01), pytest.approx(t.C004_M739_DES_KGH, abs=0.1),
        pytest.approx(66.14, abs=0.01))
    assert b.level_pct == pytest.approx(50.0, abs=1e-4)


def test_the_recycle_at_the_heel(v1):
    """FV-328406 wide open by hand asks its 77 169 kg/h of a column that receives 33 724: the
    column reaches its heel at 95 s. The recycle is served first — 741 is what arrives and does
    not boil, FT-328406 reads it (decision 11), LV-328505 is closed by its level loop and passes
    nothing — and the column's books close."""
    act = _mode("FIC_328406", "fic_328406", "MAN", 0, op=100.0)
    first, made, pre = None, 0.0, sd.SecondDesorber(fv_329401=sd.V1_FV_329401).m_kg
    for k, a, b, s, col, loops in _ticks(v1, lambda k: c004_eq._design(), 2400, act, ALL):
        if b.drain_lost and first is None:
            first = k
        made += col.m_kg - pre - (b.in_kgh - b.gen_kgh - b.m_739_kgh
                                  - b.m_overflow_kgh) * DT / 3600.0
        pre = col.m_kg
    assert first == 190 and abs(made) < 1e-6
    assert col.cap_741_kgh == b.m_741_kgh == b.m_739_kgh == pytest.approx(
        t.C004_M739_DES_KGH, abs=0.01)
    assert (b.m_export_kgh, b.lic_op_pct) == (0.0, 0.0)
    assert loops.fic_328406.measurement == pytest.approx(t.C004_M739_DES_KGH, abs=0.01)
    assert b.level_pct == pytest.approx(0.0348, abs=1e-4)


# --------------------------------------------------------------------------------------
# B-48 kept: TIC-328012 drives nothing
# --------------------------------------------------------------------------------------

def test_tic_328012_stays_on_its_faceplate(v1):
    """TIC-328012's set point taken to 0 K: its output runs to 100 % and nothing follows it —
    FIC-329402 stays in cascade with no remote set point, on its seed, and 911 on its design
    1105 kg/h, the port bit-exact with V1 on every tick. The P&ID's cascade stays unwired
    (handoff B-48, deferred to Phase 7)."""
    s, col, loops, b = c003_eq._run(v1, lambda k: c003_eq._design(), 1200, DT,
                                    c003_eq._set_point("TIC_328012", "tic_328012", 0.0))
    fic = loops.fic_329402.loop
    assert b.tic_op_pct == 100.0 and loops.tic_328012.op == 100.0
    assert (fic.mode, fic.sp, b.m_911_kgh) == ("CAS", t.C003_M911_DES_KGH, t.C003_M911_DES_KGH)
