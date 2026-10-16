"""V1 <-> V1.1 for 328C004's decided divergences, each asserted from both sides.

`test_second_desorber_equivalence.py` proves the port ``==`` V1's transcription with every departure
switched in (`_v1_c004`, its twelve switches). Here each departure is switched out of V1's side in
turn and both sides are run on the same ticks (`_both`): the tick they part, what V1 does, what the
port does instead. FFIC-329401 on 735 (B-39); a negative duty condensing vapour (decision 15); the
heel and the overflow (decision 11); LV-328505's vendor trim (decision 23) and its flash (B-46);
FIC-329401 on span (decision 10); the liquid paying what boils (decision 24); FV-329401 on the live
LP header (B-73); the backward pressure step where the explicit one would ring (B-51).
"""

from __future__ import annotations

import pytest

from ureasim.data import desorption_train as t
from ureasim.data import unit_328c004 as c
from ureasim.data.unit_328d003 import M735_DES_KGH
from ureasim.units.desorption import second_desorber as sd
from tests.equivalence import test_first_desorber_equivalence as c002_eq
from tests.equivalence import test_second_desorber_equivalence as c004_eq
from tests.equivalence.test_second_desorber_equivalence import (
    ALL,
    DT,
    STEAM_LOST,
    _both,
    _both_manual,
    _design,
    _feed,
    _manual,
    _port,
    _set_point,
    _step,
    _v1_c004,
    _v1_state,
)
from tests.equivalence.v1_loader import v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

tank_v1 = c004_eq.tank_v1
e007_v1 = c004_eq.e007_v1
c002_v1 = c004_eq.c002_v1
c003_v1 = c004_eq.c003_v1
v1 = c004_eq.v1


def test_ffic_329401_on_the_desorbers_feed_decided_divergence(v1):
    """B-39, decided 2026-09-30. 735 cut a fifth: V1's FFIC-329401 reads 744, which does not
    move, and holds 6495 kg/h of LP steam for good; the port's reads 735, and its ratio station
    (B-49) asks FIC-329401 for 5196 kg/h, the ratio's 80 %, on the tick the feed moves. The
    steam follows at FIC-329401's pace: 6420 kg/h at 30 s, 6194 at 120 s, 5523 ten minutes on,
    5196.3 in an hour, FV-329401 on the column's moving bottom pressure (B-73). They part on the
    tick the feed moves."""
    r = _both(v1, _step(10, m735=0.8 * M735_DES_KGH), 7200, 0.5, None, ALL - {"735"})
    assert r.parted == 10
    assert r.a["931"] == pytest.approx(t.C004_M931_DES_KGH, abs=1e-6)
    assert r.b.ffic_op_kgh == pytest.approx(0.8 * t.C004_M931_DES_KGH, rel=1e-12)
    assert r.b.m_931_kgh == pytest.approx(5196.266, abs=1e-3)
    assert r.b.ffic_pv == pytest.approx(c.FFIC_329401_RATIO_DES, rel=1e-4)
    for ticks, steam in ((60, 6420.10), (240, 6193.81), (1200, 5523.44)):
        q = _both(v1, _step(10, m735=0.8 * M735_DES_KGH), ticks, 0.5, None, ALL - {"735"})
        assert (q.a["931"], q.b.m_931_kgh) == (pytest.approx(t.C004_M931_DES_KGH, abs=1e-6),
                                               pytest.approx(steam, abs=0.01))


def test_a_negative_duty_decided_divergence(v1):
    """Decision 15. The LP steam lost with 749 at 130 C: the net duty goes negative on the tick
    the feed cools. V1 clamps the boil-up at zero and holds 141.08 C at 3.494 bar a, discarding
    419 kW; the port condenses its vapour down to 2.470 bar a and its bottoms to the feed's
    130 C, its duty back to zero, the condensate lifting the level to 53.8 %. (Unstripped, both
    sides' bottoms carry 0.9 % ammonia to LV-328505 and it flashes there, B-46: on V1's lines
    without the choke, -418.76 kW, 141.0780 C, 3.4941 bar a. V1's side takes the backward pressure
    step, B-51, as its overhead's differential closes; on V1's explicit step it held 140.96 C at
    3.482 bar a, discarding 414 kW.)"""
    r = _both(v1, _step(10, t749=130.0), 1200, 0.5, _both_manual(*STEAM_LOST), ALL - {"B-42"})
    assert r.parted == r.first["condensing"] == 10
    assert r.a["gen"] == 0.0 and r.a["q"] == pytest.approx(-418.87, abs=0.01)
    assert (r.s.a328_c004_T, r.s.a328_c004_P) == (pytest.approx(141.0809, abs=1e-4),
                                                  pytest.approx(3.4944, abs=1e-4))
    assert (r.col.t_c, r.col.p_bara) == (pytest.approx(129.998, abs=1e-3),
                                         pytest.approx(2.4699, abs=1e-4))
    assert abs(r.b.q_kw) < 0.1 and r.b.level_pct == pytest.approx(53.81, abs=0.01)


def test_lv_328505_at_the_heel_decided_divergence(v1):
    """Decision 11. LV-328505 held wide open drains 44.5 t/h against the 33.7 t/h that arrives
    and does not boil: the column reaches its heel at 461 s. V1's letdown goes on passing
    44.5 t/h and its 1 kg floor makes the difference — 2.2 t in the next 12 minutes; the port's
    passes what arrives and does not boil, 33 724 kg/h, flagged, and makes none."""
    r = _both(v1, lambda k: _design(), 2400, 0.5, _manual("LIC_328505", "lic_328505", 100.0),
              ALL - {"heel"})
    assert r.parted == r.first["lost"] == 922
    assert r.made_v1 == pytest.approx(2204.85, abs=0.01) and abs(r.made) < 1e-6
    assert r.a["739"] == pytest.approx(44466.4, abs=0.1)
    assert r.b.drain_lost and r.b.m_739_kgh == pytest.approx(t.C004_M739_DES_KGH, abs=0.01)


def test_a_full_desorber_overflows_decided_divergence(v1):
    """Decision 11. LV-328505 shut: the column fills at 33.7 t/h and is full at 1422.5 s. V1 goes
    on filling past its 15.99 m3 shell, 20.2 t in it at 2000 s — 137 % of what it holds; the
    port's holds 14 763 kg and lets the rest go as the overflow, its books closed. (Both sides
    take the backward pressure step as the head space closes, from 976 s at this 0.5 s step —
    handoff B-51; on the explicit step both rang, and the column was full at 1427 s.)"""
    r = _both(v1, lambda k: _design(), 4000, 0.5, _manual("LIC_328505", "lic_328505", 0.0),
              ALL - {"overflow"})
    assert r.parted == r.first["over"] == 2845
    assert r.s.a328_c004_M == pytest.approx(20173.15, abs=0.01)
    assert r.s.a328_c004_M / c.C004_FULL_KG > 1.3
    assert r.col.m_kg == c.C004_FULL_KG
    assert abs(r.made_v1) < 1e-6 and abs(r.made) < 1e-6


def _ringing_windows(trace, window=100, step=0.01):
    """10-s windows (at 0.1 s) whose tick-to-tick pressure changes of at least ``step`` reverse
    six times or more over a 0.05 bar peak to peak: the Phase 7 runner's measure (B-51)."""
    rings = 0
    for i in range(0, len(trace) - window + 1, window):
        w = trace[i:i + window]
        rev, last = 0, 0.0
        for a, b in zip(w, w[1:]):
            d = b - a
            if abs(d) >= step:
                if last and (d > 0) != (last > 0):
                    rev += 1
                last = d
        if rev >= 6 and max(w) - min(w) >= 0.05:
            rings += 1
    return rings


def test_the_backward_pressure_step_decided_divergence(v1):
    """B-51, decided 2026-10-09. LV-328505 shut at the 0.1 s step: the column fills towards its
    roof. On V1's explicit step the pressure rings from 1380 s — 750 alternating shut and open
    every tick, 62 ringing windows in 2000 s — and swings 2.09 to 4.76 bar a once the shell is
    full; the port takes the backward step from 1333.2 s, where dt . df/dP passes -1, and holds
    3.6997 to 3.6998 bar a without a ringing window."""
    s, col, loops = _v1_state(v1, ALL - {"B-51"}), sd.SecondDesorber(fv_329401=sd.V1_FV_329401), sd.SecondDesorberLoops(fic_329401=sd.fic_329401(sd.V1_FV_329401))
    _manual("LIC_328505", "lic_328505", 0.0)(s, col, loops)
    parted, first_backward, p_v1, p_port = None, None, [], []
    for k in range(20000):
        x = _design()
        _feed(s, x)
        _v1_c004(v1, s, x["m749"], x["t749"], DT, ALL - {"B-51"})
        b = _port(col, loops, x, DT)
        if first_backward is None and b.pressure_backward:
            first_backward = k
        if parted is None and s.a328_c004_P != col.p_bara:
            parted = k
        p_v1.append(s.a328_c004_P)
        p_port.append(col.p_bara)
    assert parted == first_backward == 13332
    assert _ringing_windows(p_v1) == 62 and _ringing_windows(p_port) == 0
    assert _ringing_windows(p_v1[13700:13800]) == 0 and _ringing_windows(p_v1[13800:13900]) == 1
    tail_v1, tail = p_v1[16000:], p_port[16000:]
    assert (min(tail_v1), max(tail_v1)) == (pytest.approx(2.087, abs=1e-3),
                                            pytest.approx(4.757, abs=1e-3))
    assert (min(tail), max(tail)) == (pytest.approx(3.6997, abs=1e-4),
                                      pytest.approx(3.6998, abs=1e-4))


def test_lv_328505_on_its_vendor_trim_decided_divergence(v1):
    """Decision 23. LV-328505 held at 50 %: on V1's linear trim from 50 % it passes the design
    33 724 kg/h; on Valtek's modified equal percentage from 90.07 % it passes 10 154 — and ten
    minutes on the port's column is filling, LI-328505 at 185 %. (V1's linear trim takes the
    B-46 choke on V1's default FL, 0.9, which binds at its design state: its level drifts
    4e-6 % in twenty minutes as the bottoms' vapour pressure moves.)"""
    s0 = _v1_state(v1, ALL - {"valve"})
    assert s0.LIC_328505["op"] == 50.0
    r = _both(v1, lambda k: _design(), 1, 0.5, _manual("LIC_328505", "lic_328505", 50.0),
              ALL - {"valve"})
    assert r.parted == 0
    assert (r.a["739"], r.b.m_739_kgh) == (pytest.approx(t.C004_M739_DES_KGH, rel=1e-12),
                                           pytest.approx(10154.17, abs=0.01))
    r = _both(v1, lambda k: _design(), 1200, 0.5, _manual("LIC_328505", "lic_328505", 50.0),
              ALL - {"valve"})
    assert (r.a["LI_328505"], r.b.level_pct) == (pytest.approx(50.0, abs=1e-5),
                                                 pytest.approx(185.12, abs=0.01))


def test_a_hot_740_flashes_lv_328505_decided_divergence(v1):
    """B-46, decided 2026-09-30. 328E007 loses its cold side and 740 reaches LV-328505 at the
    column's 143 C, boiling at 4.04 bar a, above the valve's 3.81 bar a inlet: the liquid
    arrives saturated and flashes. V1's lines have no vapour pressure and pass the design
    33 724 kg/h; the port's choke, FL^2 (P1 - FF . P1), is 0.26 bar of the 2.81 across the
    valve, and it passes 10 306 kg/h on the tick 740 heats. LIC-328505 strokes LV-328505 fully
    open within a minute and still cannot hold the column: LI-328505 at 107 % five minutes on.
    At 120 C the choke costs 22 % at once, and LIC-328505 wins it back at 98 % open."""
    r = _both(v1, _step(10, t740=143.0), 11, 0.5, None, ALL - {"flash"})
    assert r.parted == 10
    assert r.a["739"] == pytest.approx(t.C004_M739_DES_KGH, rel=1e-9)
    assert r.b.m_739_kgh == pytest.approx(10305.68, abs=0.01)
    r = _both(v1, _step(10, t740=143.0), 600, 0.5, None, ALL - {"flash"})
    assert r.a["LI_328505"] == pytest.approx(50.0, abs=1e-9)
    assert r.b.lv_op_pct == 100.0 and r.b.level_pct == pytest.approx(106.73, abs=0.01)
    assert abs(r.made_v1) < 1e-6 and abs(r.made) < 1e-6
    r = _both(v1, _step(10, t740=120.0), 11, 0.5, None, ALL - {"flash"})
    assert r.b.m_739_kgh / t.C004_M739_DES_KGH == pytest.approx(0.7844, abs=1e-4)
    r = _both(v1, _step(10, t740=120.0), 2400, 0.5, None, ALL - {"flash"})
    assert r.b.lv_op_pct == pytest.approx(98.17, abs=0.01)
    assert r.b.level_pct == pytest.approx(50.0, abs=1e-3)


@pytest.mark.parametrize("ticks, v1_steam, steam", [(1200, 5442.27, 6135.34),
                                                    (6000, 5004.11, 5370.80)])
def test_fic_329401_on_span_decided_divergence(v1, ticks, v1_steam, steam):
    """Decision 10. FFIC-329401 in MAN asking 5000 kg/h, at the fixed 0.1 s step: V1's
    FIC-329401, on the table's 0.30 per kg/h, is at 5442 kg/h two minutes on and 5004 at ten;
    the port's, on 0.0025 %/(kg/h) of FT-329401's 12 000 kg/h, at 6135 and 5371."""
    r = _both(v1, lambda k: _design(), ticks, DT, _manual("FFIC_329401", "ffic_329401", 5000.0),
              ALL - {"gains"})
    assert r.parted == 0
    assert (r.a["931"], r.b.m_931_kgh) == (pytest.approx(v1_steam, abs=0.01),
                                           pytest.approx(steam, abs=0.01))


def _c004_books(p_bara, t_c, m_kg, y):
    return (m_kg, c002_eq.head_space_kg(p_bara, t_c, m_kg, c.C004_VOL_M3, c.C004_RHO_KGM3, 1.0),
            c002_eq.vapour_mw(y))


@pytest.mark.parametrize("name, script, before, v1_made", [
    ("328C002 at 4.2 bar a", _step(10, pc002=4.2), None, 4.21),
    ("FFIC-329401 to 0.25 t/m3", lambda k: _design(),
     _set_point("FFIC_329401", "ffic_329401", 0.25), 0.42),
])
def test_the_liquid_pays_what_boils_decided_divergence(v1, name, script, before, v1_made):
    """Decision 24. V1's liquid loses what the overhead line passes while the pressure integral
    fills the head space with the boil-up. The books — the liquid plus the head space's vapour,
    read off the pressure state at the molar mass each tick ran on, against what crossed the
    boundary — kept on both sides for ten minutes: V1 makes exactly its integral of boil-up less
    overhead, 4.21 kg with 328C002 0.7 bar higher and 0.42 kg on a 21 % steam step — small here,
    for 328C004's head space is 14 m3 of steam at 3.7 bar a; the port's close within 10 g. V1's
    side keeps its explicit pressure step: the backward step's 750 at the settled pressure
    presupposes this decision's books (B-51)."""
    dt = 0.5
    s, col, loops = _v1_state(v1), sd.SecondDesorber(fv_329401=sd.V1_FV_329401), sd.SecondDesorberLoops(fic_329401=sd.fic_329401(sd.V1_FV_329401))
    if before:
        before(s, col, loops)
    made_v1 = made = held_back = 0.0
    for k in range(1200):
        x = script(k)
        _feed(s, x)
        pre_v1 = _c004_books(s.a328_c004_P, s.a328_c004_T, s.a328_c004_M, s.y_328_750)
        pre = _c004_books(col.p_bara, col.t_c, col.m_kg, col.y_750)
        a = _v1_c004(v1, s, x["m749"], x["t749"], dt, ALL - {"vapour", "B-51"})
        b = _port(col, loops, x, dt)
        made_v1 += c002_eq._made(pre_v1, s.a328_c004_M, s.a328_c004_P, s.a328_c004_T,
                                 c.C004_VOL_M3, c.C004_RHO_KGM3,
                                 a["in"] - a["750"] - a["739"] - a["over"], dt)
        made += c002_eq._made(pre, col.m_kg, col.p_bara, col.t_c, c.C004_VOL_M3,
                              c.C004_RHO_KGM3, b.in_kgh - b.m_750_kgh - b.m_739_kgh
                              - b.m_overflow_kgh, dt)
        held_back += (a["gen"] - a["750"]) * dt / 3600.0
    assert made_v1 == pytest.approx(v1_made, abs=0.01)
    assert made_v1 == pytest.approx(held_back, abs=0.01)
    assert abs(made) < 0.01



def test_fv_329401_on_the_live_lp_header_decided_divergence(v1):
    """B-73, decided 2026-10-02 (the Typo Rule). The LP header falls from its 5.013 bar a to 4.1.
    V1's flow element is a pure gain on the stroke: its 931 holds 6495 kg/h for good. The port's
    FV-329401 passes the header's steam to the column's bottom at 3.93 bar a: on the tick after the
    fall its 931 is 3123 kg/h, FIC-329401 opens against it — 5057 kg/h ten minutes on — and after
    twenty FV-329401 is at 98.5 % passing 5640 kg/h, the column at 142.58 C where V1's holds 143.
    (The column's design pressure moves its last bits, 5e-13 bar, so the two part before the fall.)
    """
    for ticks, steam, op in ((12, 3122.997, 51.603), (1210, 5056.668, 83.367),
                             (2400, 5640.063, 98.546)):
        r = _both(v1, _step(10, plp=4.1), ticks, 0.5, None, ALL - {"B-73"})
        assert r.a["931"] == t.C004_M931_DES_KGH
        assert (r.b.m_931_kgh, r.loops.fic_329401.loop.op) == (pytest.approx(steam, abs=1e-3),
                                                               pytest.approx(op, abs=1e-3))
    assert (r.b.t_c, r.s.a328_c004_T) == (pytest.approx(142.5807, abs=1e-4),
                                          pytest.approx(143.0, abs=1e-9))
    assert sd.fv_329401_pressure_ratio(4.1, c.FV_329401_P2_DES_BARA) == pytest.approx(0.3927,
                                                                                      abs=1e-4)
