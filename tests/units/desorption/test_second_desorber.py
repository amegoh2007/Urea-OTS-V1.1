"""Behaviour of 328C004, desorber II — `ureasim.units.desorption.second_desorber`.

Equivalence with V1 is proven in `tests/equivalence/test_second_desorber_equivalence.py`. This
file pins what the column DOES: the PFD's design point on the first tick; the LP steam following
the desorbers' feed on FFIC-329401, a ratio station (decided 2026-09-30, handoffs B-39 and B-49),
and the ammonia a steam cut lets through to AI-328701; LIC-328505 on FIC-328406 recycling the
bottoms as 741, drawn ahead of LV-328505 (decided the same day, B-50); a cold feed with the steam
lost condensing the column's vapour (decision 15); and the two limits of decision 11 — LV-328505
at the heel and the full shell overflowing — with the liquid's books closed on what boils
(decision 24).
"""

from __future__ import annotations

import math

import pytest

from ureasim.data import desorption_train as t
from ureasim.data import unit_328c004 as c
from ureasim.data.unit_328d003 import M735_DES_KGH
from ureasim.units.desorption import second_desorber as sd

DT = 0.5


def _loop(loops, name):
    loop = getattr(loops, name)
    return loop.loop if isinstance(loop, sd.FlowLoop) else loop


def _run(ticks, dt=DT, man=None, over=None, t0=10, cas=()):
    """Drive the column from its design seed; `man` holds loops at an output, `cas` puts loops in
    cascade, `over` replaces boundaries from tick t0. Returns the column, every result, and the
    liquid the books did not see — the liquid loses what boils (decision 24)."""
    col, loops = sd.SecondDesorber(), sd.SecondDesorberLoops()
    for name, op in (man or {}).items():
        _loop(loops, name).set_mode("MAN")
        _loop(loops, name).op = op
    for name in cas:
        _loop(loops, name).set_mode("CAS")
    out, made = [], 0.0
    for k in range(ticks):
        x = dict(m749=t.C004_M749_DES_KGH, t749=t.C004_T749_C, w749=dict(t.W_S747),
                 m735=M735_DES_KGH, pc002=t.C002_P_TOP_BARA, t740=c.LV505_T_IN_DES_C)
        if over and k >= t0:
            x.update(over)
        pre = col.m_kg
        r = col.step(loops, x["m749"], x["t749"], dict(x["w749"]), x["m735"], x["pc002"],
                     x["t740"], dt)
        made += col.m_kg - pre - (r.in_kgh - r.gen_kgh - r.m_739_kgh
                                  - r.m_overflow_kgh) * dt / 3600.0
        out.append(r)
    return col, out, made


def test_the_design_point_is_the_pfds():
    """The first tick passes the PFD's 931, 739 and 750 and boils what it passes, at 143 C and
    3.7 bar a; LV-328505 sits at its vendor design stroke; AI-328701 reads 6.93 uS/cm."""
    col, out, _ = _run(1, dt=0.1)
    r = out[0]
    assert (r.m_931_kgh, r.m_739_kgh, r.m_750_kgh, r.gen_kgh) == (
        t.C004_M931_DES_KGH, t.C004_M739_DES_KGH, t.C004_M750_DES_KGH, t.C004_M750_DES_KGH)
    assert (r.p_bara, r.level_pct, r.lic_op_pct) == (3.7, 50.0, c.LV505_OP_DES_PCT)
    assert r.t_c == pytest.approx(143.0, abs=1e-12) and r.t_top_c == r.t_c - 3.0
    assert r.ffic_pv == c.FFIC_329401_RATIO_DES and r.q_kw == c.C004_Q_DES_KW
    assert r.ai_328701_us_cm == pytest.approx(6.933, abs=1e-3)
    assert not r.drain_lost and r.m_overflow_kgh == 0.0


def test_the_steam_follows_the_desorbers_feed():
    """B-39 and B-49, decided. 735 cut a fifth: the ratio station asks FIC-329401 for 5196 kg/h —
    the ratio's 80 % — on the tick the feed moves, and the LP steam is at 5196.0 kg/h in an hour
    (FV-329401 on the column's moving bottom pressure, B-73, and on its Neldisc, decided
    2026-10-15; 5196.3 on V1's valve); with 749 unchanged the column strips less, and 15 ppm of
    ammonia reaches AI-328701, 32 uS/cm."""
    col, out, made = _run(7200, over=dict(m735=0.8 * M735_DES_KGH))
    assert out[9].ffic_op_kgh == t.C004_M931_DES_KGH
    assert all(r.ffic_op_kgh == pytest.approx(0.8 * t.C004_M931_DES_KGH, rel=1e-12)
               for r in out[10:])
    r = out[-1]
    assert r.m_931_kgh == pytest.approx(5196.001, abs=1e-3)
    assert (r.p_bara, r.t_c) == (pytest.approx(3.6329, abs=1e-4), pytest.approx(142.383, abs=1e-3))
    assert col.w["NH3"] * 1e6 == pytest.approx(15.30, abs=0.01)
    assert r.ai_328701_us_cm == pytest.approx(32.17, abs=0.01)
    assert abs(made) < 1e-6


def test_lic_328505_on_fic_328406_recycles_the_bottoms():
    """B-50, decided. FIC-328406 put in cascade at the design point: LV-328505 is switched shut
    and LIC-328505 sets FIC-328406 across FT-328406's 60 m3/h — 54.0 m3/h on the switch — so the
    whole bottoms go back to 328D003 as 741. The level swings 30.7-77.2 % in the first quarter
    hour and is within 0.3 % of 50 % in two hours, LIC-328505 near 57.5 %, the books closed."""
    col, out, made = _run(14400, cas=("fic_328406",))
    assert all((r.lv_op_pct, r.m_export_kgh, r.m_739_kgh) == (0.0, 0.0, r.m_741_kgh)
               for r in out)
    levels = [r.level_pct for r in out[:1800]]
    assert (min(levels), max(levels)) == (pytest.approx(30.66, abs=0.01),
                                          pytest.approx(77.16, abs=0.01))
    r = out[-1]
    assert r.level_pct == pytest.approx(50.0, abs=0.3)
    assert r.m_741_kgh == pytest.approx(t.C004_M739_DES_KGH, rel=0.01)
    assert r.lic_op_pct == pytest.approx(57.47, abs=0.01)
    assert abs(made) < 1e-6


def test_fv_328406_by_hand_draws_ahead_of_lv_328505():
    """FV-328406 at 50 % by hand takes its trim's 17 256 kg/h out of the bottoms from the first
    tick, and LIC-328505 takes LV-328505 back to 66.1 % over the hour: the export 16 468 kg/h,
    the bottoms the PFD's 33 724 again, the level at 50 %."""
    col, out, made = _run(7200, man={"fic_328406": 50.0})
    assert all(r.m_741_kgh == pytest.approx(17255.617, abs=1e-3)
               and r.m_739_kgh == r.m_export_kgh + r.m_741_kgh for r in out)
    r = out[-1]
    assert (r.m_export_kgh, r.m_739_kgh, r.lic_op_pct, r.level_pct) == (
        pytest.approx(16468.44, abs=0.01), pytest.approx(t.C004_M739_DES_KGH, abs=0.1),
        pytest.approx(66.14, abs=0.01), pytest.approx(50.0, abs=1e-4))
    assert abs(made) < 1e-6


def test_a_cold_feed_with_the_steam_lost_condenses_the_column():
    """Decision 15. The LP steam lost and 749 at 130 C: the duty goes negative and condenses the
    column's vapour; its pressure and bubble point fall until the duty balances — 2.470 bar a and
    the feed's 130 C ten minutes on — and the condensate lifts the level to 53.8 %."""
    col, out, made = _run(1200, man={"ffic_329401": 0.0, "fic_329401": 0.0},
                          over=dict(t749=130.0))
    r = out[-1]
    assert r.m_931_kgh == 0.0 and abs(r.q_kw) < 0.1
    assert (r.p_bara, r.t_c) == (pytest.approx(2.4699, abs=1e-4), pytest.approx(129.998, abs=1e-3))
    assert r.level_pct == pytest.approx(53.81, abs=0.01)
    assert abs(made) < 1e-6


def test_lv_328505_at_the_heel_passes_what_arrives():
    """Decision 11. LV-328505 held wide open: the column reaches its heel at 461 s, and from then
    on 739 is what arrives less what boils — 33 724 kg/h — flagged, making no liquid."""
    col, out, made = _run(2400, man={"lic_328505": 100.0})
    first = next(k for k, r in enumerate(out) if r.drain_lost)
    assert first * DT == pytest.approx(461.0, abs=1e-9)
    assert all(r.drain_lost for r in out[first:])
    assert col.m_kg == pytest.approx(c.C004_M_FLOOR_KG, abs=1e-6)
    assert out[-1].m_739_kgh == pytest.approx(t.C004_M739_DES_KGH, abs=0.01)
    assert abs(made) < 1e-6


def test_a_full_desorber_overflows():
    """Decision 11. LV-328505 shut: the column is full at 1422.5 s; from then on it holds
    14 763 kg — LI-328505 at 514 % — and the excess leaves as the overflow, the books closed. Its
    pressure takes the backward step as the head space closes (B-51)."""
    col, out, made = _run(4000, man={"lic_328505": 0.0})
    first = next(k for k, r in enumerate(out) if r.m_overflow_kgh > 0.0)
    assert first * DT == pytest.approx(1422.5, abs=1e-9)
    assert col.m_kg == c.C004_FULL_KG == pytest.approx(14763.45, abs=0.01)
    assert out[-1].level_pct == pytest.approx(513.88, abs=0.01)
    assert abs(made) < 1e-6


def test_a_hot_740_flashes_and_chokes_lv_328505():
    """B-46. 328E007's cold side lost: 740 reaches LV-328505 at the column's 143 C, saturated at
    the valve's inlet, and flashes. The choke, FL^2 (P1 - FF . P1), is 0.26 bar of the 2.81
    across the valve, so the drain falls to 30.6 % at once. At 89 C, boiling at 0.68 bar a, the
    valve stood 0.03 bar short of its choke."""
    p1, dp = c.LV505_P1_DES_BARA, c.LV505_P1_DES_BARA - c.LV505_P2_BARA

    def choke(pv):
        return c.LV505_FL ** 2 * (p1 - (0.96 - 0.28 * math.sqrt(pv / 220.64)) * pv)

    assert choke(c.LV505_PV_DES_BARA) - dp == pytest.approx(0.0307, abs=1e-4)
    col, out, _ = _run(1, over={"t740": 143.0}, t0=0)
    assert out[0].m_739_kgh == pytest.approx(
        t.C004_M739_DES_KGH * math.sqrt(choke(p1) / dp), rel=1e-12)
    assert out[0].m_739_kgh / t.C004_M739_DES_KGH == pytest.approx(0.3056, abs=1e-4)


def _sagging_header(v1: bool, p_lp: float, ticks: int = 3600, dt: float = DT):
    """The LP header dropped to ``p_lp`` at tick 10 for half an hour, FV-329401 on V1's valve or
    on Metso's trim: 931 and FIC-329401's output after 30 s and at the end, and AI-328701."""
    valve = sd.V1_FV_329401 if v1 else sd.FV_329401_TRIM
    col = sd.SecondDesorber(fv_329401=valve)
    loops = sd.SecondDesorberLoops(fic_329401=sd.fic_329401(valve))
    for k in range(ticks):
        r = col.step(loops, t.C004_M749_DES_KGH, t.C004_T749_C, dict(t.W_S747), M735_DES_KGH,
                     t.C002_P_TOP_BARA, c.LV505_T_IN_DES_C, dt,
                     p_lp_bara=p_lp if k >= 10 else c.FV_329401_P1_DES_BARA)
        if k == 70:
            early = (r.m_931_kgh, loops.fic_329401.loop.op)
    return early, (r.m_931_kgh, loops.fic_329401.loop.op), r.ai_328701_us_cm


def test_fv_329401_on_its_vendor_trim_holds_the_stripping_steam_on_a_sagging_header():
    """Decision 108's class, decided 2026-10-15: FV-329401 on Metso's DN 200 Neldisc from its
    26.0 % design stroke and its normal case's xT 0.53, where V1 runs it linear from 50 % on the
    globe's 0.75 (the harness proves V1's ``==``). The LP header at 4.5 bar a: 30 s on, V1's valve
    passes 5291 kg/h at 53.9 %, the Neldisc 5775 at 28.4 %; after half an hour V1's 6426 at 68.2 %,
    the Neldisc 6494.5 at 30.9 %. At 4.1 bar a V1's valve is wide open on 5690 kg/h and 17.8 uS/cm
    of ammonia reaches AI-328701; the Neldisc holds 6457 kg/h at 45.7 % and 7.0 uS/cm."""
    v1, port = _sagging_header(True, 4.5), _sagging_header(False, 4.5)
    assert v1[0] == (pytest.approx(5291.2, abs=0.1), pytest.approx(53.863, abs=1e-3))
    assert port[0] == (pytest.approx(5775.2, abs=0.1), pytest.approx(28.391, abs=1e-3))
    assert v1[1] == (pytest.approx(6426.2, abs=0.1), pytest.approx(68.243, abs=1e-3))
    assert port[1] == (pytest.approx(6494.5, abs=0.1), pytest.approx(30.921, abs=1e-3))
    v1, port = _sagging_header(True, 4.1), _sagging_header(False, 4.1)
    assert v1[1] == (pytest.approx(5690.4, abs=0.1), 100.0) and v1[2] == pytest.approx(17.75, abs=0.01)
    assert port[1] == (pytest.approx(6456.9, abs=0.1), pytest.approx(45.717, abs=1e-3))
    assert port[2] == pytest.approx(7.04, abs=0.01)
