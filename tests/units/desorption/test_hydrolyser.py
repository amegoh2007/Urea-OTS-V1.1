"""Behaviour of 328C003, the hydrolyser, and 328E021 — `ureasim.units.desorption.hydrolyser`.

Equivalence with V1 is proven in `tests/equivalence/test_hydrolyser_equivalence.py`. This file
pins what the column DOES: the PFD's design point on the first tick; the conversion answering the
steam, the feed and the urea it carries; the liquid paying for everything that boils, so a
throttled PV-328203 raises the pressure and not the temperature (decision 24); 328E021 giving the
feed only what its hot side gave (decision 14); and the two limits of decision 11 — LV-328504 at
the heel and the full shell overflowing — with the liquid's books closed on what boils.
"""

from __future__ import annotations

import math

import pytest

from ureasim.data import desorption_train as t
from ureasim.data import unit_328c003 as c
from ureasim.units.desorption import hydrolyser as hy

DT = 0.5


def _loop(loops, name):
    loop = getattr(loops, name)
    return loop.loop if isinstance(loop, hy.FlowLoop) else loop


def _run(ticks, dt=DT, man=None, over=None, t0=10):
    """Drive the column from its design seed; `man` holds loops at an output, `over` replaces
    boundaries from tick t0. Returns the column, every result, and the liquid the books did not
    see — the liquid loses what boils (decision 24)."""
    col, loops = hy.Hydrolyser(), hy.HydrolyserLoops()
    for name, op in (man or {}).items():
        _loop(loops, name).set_mode("MAN")
        _loop(loops, name).op = op
    out, made = [], 0.0
    for k in range(ticks):
        x = dict(m746=t.C003_M746_DES_KGH, w746=dict(t.W_S743), tc002=t.C002_T_BOT_C,
                 pc002=t.C002_P_TOP_BARA, pc004=t.C004_P_BARA)
        if over and k >= t0:
            x.update(over)
        pre = col.m_kg
        r = col.step(loops, x["m746"], dict(x["w746"]), x["tc002"], x["pc002"], x["pc004"], dt)
        made += col.m_kg - pre - (x["m746"] + r.m_911_kgh - r.gen_748_kgh - r.m_747_kgh
                                  - r.m_overflow_kgh) * dt / 3600.0
        out.append(r)
    return col, out, made


def test_the_design_point_is_the_pfds():
    """The first tick passes the PFD's 748, 747 and 911, generates what it vents, and holds
    200 C and 16.8 bar a; the urea left in 747 is 0.61 ppm."""
    _, out, _ = _run(1, dt=0.1)
    r = out[0]
    assert (r.m_748_kgh, r.gen_748_kgh, r.m_747_kgh, r.m_911_kgh) == (
        t.C003_M748_DES_KGH, t.C003_M748_DES_KGH, t.C003_M747_DES_KGH, t.C003_M911_DES_KGH)
    assert (r.t_c, r.p_bara, r.level_pct, r.m_kg) == (200.0, 16.8, 50.0, c.C003_M_DES_KG)
    assert (r.t_746_c, r.t_749_c, r.e021_pinched) == (190.0, 148.0, False)
    assert abs(r.q_net_kw) < 1e-9 and r.q_hyd_kw == pytest.approx(hy.C003_QHYD_DES_KW, rel=1e-12)
    assert r.urea_747_ppm == pytest.approx(0.6065, abs=1e-4)
    assert r.x_hyd == pytest.approx(0.999919, abs=1e-6)


def test_the_mp_steam_lost_the_column_cools_and_the_urea_slips():
    """FIC-329402 shut: nothing carries the reaction's heat, the column cools to 185.9 C in an
    hour and the condensate carries 77.6 ppm of urea."""
    _, out, made = _run(7200, man={"fic_329402": 0.0})
    r = out[-1]
    assert r.m_911_kgh == 0.0
    assert (r.t_c, r.urea_747_ppm) == (pytest.approx(185.915, abs=1e-3),
                                       pytest.approx(77.645, abs=1e-3))
    assert abs(made) < 1e-6


def test_a_heavier_feed_shortens_the_residence():
    """746 a fifth up: less residence, a colder column — 197.38 C an hour on — and 7.16 ppm."""
    _, out, made = _run(7200, over=dict(m746=1.2 * t.C003_M746_DES_KGH))
    r = out[-1]
    assert (r.t_c, r.urea_747_ppm) == (pytest.approx(197.383, abs=1e-3),
                                       pytest.approx(7.155, abs=1e-3))
    assert abs(made) < 1e-6


def test_twice_the_urea_is_mostly_destroyed():
    """746 carrying twice the urea: the extent doubles, the endotherm cools the column to 195.2 C,
    and 10.1 ppm slips."""
    rich = dict(t.W_S743)
    rich["Urea"] = 2.0 * t.W_S743["Urea"]
    rich["H2O"] = t.W_S743["H2O"] - t.W_S743["Urea"]
    _, out, made = _run(7200, over=dict(w746=rich))
    r = out[-1]
    assert (r.t_c, r.urea_747_ppm, r.xi_kmolh) == (pytest.approx(195.161, abs=1e-3),
                                                   pytest.approx(10.062, abs=1e-3),
                                                   pytest.approx(8.5412, abs=1e-4))
    assert abs(made) < 1e-6


def test_a_throttled_overhead_raises_the_pressure_not_the_temperature():
    """Decision 24. PV-328203 held at 20 %: the column generates 812 kg/h and the valve passes
    less; the liquid loses and pays for the 812, the rest stays in the head space — the pressure
    rises while the temperature holds 200 C, until SV32852 lifts at 24.01 bar a, 618.5 s on
    (B-47). From there the valve holds the column between 21.71 and 24.01 bar a, venting 482 kg
    in the hour (LV-328504 on Fisher's trim, decision 150). (Unrelieved, 40.6 bar a in the hour; V1 charged the
    liquid only what the valve passed, made 505 kg and ran 3.1 K hot.)"""
    _, out, made = _run(7200, man={"pic_328203": 20.0})
    r = out[-1]
    assert r.gen_748_kgh == pytest.approx(t.C003_M748_DES_KGH, rel=1e-9)
    first = next(k for k, x in enumerate(out) if x.relief_lifted)
    assert first * DT == 618.5
    assert max(x.p_bara for x in out) < c.SV32852_SET_BARA + 0.01
    assert min(x.p_bara for x in out[first:]) == pytest.approx(c.SV32852_RESEAT_BARA, abs=1e-9)
    assert sum(x.m_relief_kgh for x in out) * DT / 3600.0 == pytest.approx(481.97, abs=0.01)
    assert r.t_c == pytest.approx(200.0, abs=1e-6)
    assert abs(made) < 1e-6


def test_sv32852_lifts_at_its_set_pressure_and_reseats_at_its_blowdown():
    """B-47. PV-328203 shut: the column reaches SV32852's set, 24.01 bar a, at 459 s. The valve
    lifts and vents the head space at its certified capacity carried to the column's vapour —
    27 142 kg/h at 24.01 bar a, falling with the pressure — and reseats at 21.71 bar a, 10 % of
    the set pressure below it; the cycle repeats every 152.5 s while the overhead stays shut."""
    _, out, _ = _run(7200, man={"pic_328203": 0.0})
    lifts = [k for k in range(1, len(out))
             if out[k].relief_lifted and not out[k - 1].relief_lifted]
    assert lifts[0] * DT == 459.0 and len(lifts) == 20
    assert (lifts[-1] - lifts[-2]) * DT == 152.5
    assert out[lifts[0] - 1].p_bara >= c.SV32852_SET_BARA
    assert out[lifts[0]].m_relief_kgh == pytest.approx(27141.85, abs=0.01)
    assert all(x.m_relief_kgh == 0.0 for x in out if not x.relief_lifted)
    assert sum(x.m_relief_kgh for x in out) * DT / 3600.0 == pytest.approx(693.71, abs=0.01)


def test_328e021_gives_the_feed_what_its_hot_side_gave():
    """Decision 14. LV-328504 held where it passes 80 % of its design flow (52.10 % on Fisher's
    trim, decision 150; 40 % on V1's line): 747 is too little to heat 746 to 190 C; the feed takes
    what the hot side gave, 188.06 C an hour on, pinched, and the column runs 1.03 K cold."""
    _, out, made = _run(7200, man={"lic_328504": c.LV504_OP_DES_PCT
                                    + 100.0 * math.log(0.8) / math.log(50.0)})
    r = out[-1]
    assert r.e021_pinched and r.t_749_c == t.C002_T_BOT_C
    assert (r.t_746_c, r.t_c, r.urea_747_ppm) == (pytest.approx(188.061, abs=1e-3),
                                                  pytest.approx(198.966, abs=1e-3),
                                                  pytest.approx(1.164, abs=1e-3))
    assert abs(made) < 1e-6


def test_lv_328504_at_the_heel_passes_what_arrives():
    """Decision 11. LV-328504 held wide open on Fisher's equal percentage (decision 150): the
    column reaches its heel at 1628.5 s, and from
    then on 747 is what arrives less what boils — the PFD's 34 062 kg/h — flagged, making no
    liquid."""
    col, out, made = _run(21600, man={"lic_328504": 100.0})
    first = next(k for k, r in enumerate(out) if r.drain_lost)
    assert first * DT == pytest.approx(1628.5, abs=1e-9)
    assert all(r.drain_lost for r in out[first:])
    assert col.m_kg == pytest.approx(c.C003_M_FLOOR_KG, abs=1e-6)
    assert out[-1].m_747_kgh == pytest.approx(t.C003_M747_DES_KGH, rel=1e-9)
    assert abs(made) < 1e-6


def test_a_full_hydrolyser_overflows():
    """Decision 11. LV-328504 shut: the column is full at 2378.5 s; from then on it holds
    56 571 kg and 34.1 t/h leaves as the overflow, the books closed."""
    col, out, made = _run(7200, man={"lic_328504": 0.0})
    first = next(k for k, r in enumerate(out) if r.m_overflow_kgh > 0.0)
    assert first * DT == pytest.approx(2378.5, abs=1e-9)
    assert col.m_kg == c.C003_FULL_KG == pytest.approx(56570.51, abs=0.01)
    assert out[-1].m_overflow_kgh == pytest.approx(34090.5, abs=0.1)
    assert out[-1].level_pct == pytest.approx(83.04, abs=0.01)
    assert abs(made) < 1e-6
