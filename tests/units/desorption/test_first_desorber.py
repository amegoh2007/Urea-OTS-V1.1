"""Behaviour of 328C002, desorber I — `ureasim.units.desorption.first_desorber`.

Equivalence with V1 is proven in `tests/equivalence/test_first_desorber_equivalence.py`. This
file pins what the column DOES: the PFD's design point on the first tick; the chain duty ->
boil-up -> pressure -> bubble point, both ways; the stripping vapour lost, the column condensing
its vapour down to the feeds' mixing temperature (decided 2026-09-30, handoff B-42); 328C004's
overhead halved, LV-328503 holding the level on the bottoms' own bubble pressure (decided
2026-09-30, handoff B-43); and the two limits of decision 11 — 328P006 at the heel and the full
shell overflowing — with the liquid's books closed on what boils (decision 24).
"""

from __future__ import annotations

import pytest

from ureasim.data import desorption_train as t
from ureasim.data import unit_328c002 as c
from ureasim.units.desorption import first_desorber as fd

DT = 0.1


def _run(ticks, over=None, man=None, t0=10):
    """Drive the column from its design seed; `over` replaces boundaries from tick t0, `man`
    holds LV-328503. Returns the column, every result, and the liquid the books did not see —
    the liquid loses what boils (decision 24)."""
    col, lic = fd.FirstDesorber(), fd.lic_328503()
    if man is not None:
        lic.set_mode("MAN")
        lic.op = man
    out, made = [], 0.0
    for k in range(ticks):
        x = dict(m738=t.C002_M738_DES_KGH, t738=t.C002_T738_DES_C, m748=t.C002_M748_DES_KGH,
                 m750=t.C002_M750_DES_KGH, m775=t.C002_M775_DES_KGH)
        if over and k >= t0:
            x.update(over)
        pre = col.m_kg
        r = col.step(lic, x["m738"], x["t738"], x["m748"], dict(t.DES_C003.y), x["m750"],
                     dict(t.DES_C004.y), x["m775"], t.C003_P_BARA, t.D001_P_BARA, DT)
        made += col.m_kg - pre - (r.in_kgh - r.gen_kgh - r.m_743_kgh
                                  - r.m_overflow_kgh) * DT / 3600.0
        out.append(r)
    return col, out, made


def test_the_design_point_is_the_pfds():
    """The first tick passes the PFD's 737 and 743 and boils what it passes; the bubble point
    comes back 6e-14 K off 139 C, IF97's round trip."""
    _, out, _ = _run(1)
    r = out[0]
    assert (r.in_kgh, r.m_737_kgh, r.m_743_kgh, r.gen_kgh) == (40434.0, 6665.0, 33769.0, 6665.0)
    assert (r.p_bara, r.level_pct, r.t_top_c) == (3.5, 50.0, r.t_c - 22.0)
    assert r.t_c == pytest.approx(139.0, abs=1e-13) and r.q_kw == c.C002_Q_DES_KW
    assert not r.suction_lost and r.m_overflow_kgh == 0.0


@pytest.mark.parametrize("m750, p, t_c, m737", [
    (1.2 * t.C002_M750_DES_KGH, 3.86916, 142.5460, 7874.97),
    (0.8 * t.C002_M750_DES_KGH, 3.19024, 135.7846, 5405.33),
])
def test_the_stripping_vapour_sets_the_pressure_and_the_temperature(m750, p, t_c, m737):
    """750 a fifth up or down: the duty moves the boil-up, the boil-up the pressure, the
    pressure the bubble point — five minutes on."""
    _, out, _ = _run(3000, dict(m750=m750))
    r = out[-1]
    assert (r.p_bara, r.t_c, r.m_737_kgh) == (pytest.approx(p, abs=1e-5),
                                              pytest.approx(t_c, abs=1e-4),
                                              pytest.approx(m737, abs=0.01))


def test_the_stripping_vapour_lost_the_column_cools_to_its_feeds():
    """748 and 750 stopped: the net duty goes negative and condenses the column's vapour; the
    overhead closes at 328D001's pressure, and the pressure and its bubble point go on falling
    until the duty balances — five minutes on, 1.482 bar a and 111.28 C, the two liquid feeds'
    mixing temperature (111.29 C). V1 clamps the boil-up at zero and holds 128.5 C, making the
    622.5 kW it discards (decided 2026-09-30, handoff B-42)."""
    _, out, made = _run(3000, dict(m748=0.0, m750=0.0))
    r = out[-1]
    assert r.m_737_kgh == 0.0 and abs(r.q_kw) < 0.6
    assert r.p_bara == pytest.approx(1.48257, abs=1e-5)
    assert r.t_c == pytest.approx(111.2794, abs=1e-4)
    t_mix = ((t.C002_M738_DES_KGH * t.C002_T738_DES_C + t.C002_M775_DES_KGH * t.D001_T_C)
             / (t.C002_M738_DES_KGH + t.C002_M775_DES_KGH))
    assert r.t_c == pytest.approx(t_mix, abs=0.02)
    assert abs(made) < 1e-9


def test_every_inlet_lost_the_column_stands_hot_and_full_of_its_liquid():
    _, out, made = _run(3000, dict(m738=0.0, m748=0.0, m750=0.0, m775=0.0))
    r = out[-1]
    assert (r.m_737_kgh, r.m_743_kgh) == (0.0, 0.0)
    assert r.m_kg == pytest.approx(918.15, abs=0.01) and r.t_c == pytest.approx(126.826, abs=1e-3)
    assert abs(made) < 1e-9


def test_lv_328503_holds_the_level_when_328c004s_overhead_is_halved():
    """750 halved: the column strips far less — its bottoms carry 5.4 % NH3 ten minutes on — and
    LV-328503, choking on the bottoms' own bubble pressure at 139 C, still passes them: the level
    holds 50 %, the valve at 57.98 % on Fisher's trim (decision 150). On V1's choke at 328E021's
    outlet, 190 C, the valve is wide open and the level through 145 % (decided 2026-09-30, handoff
    B-43)."""
    col, out, _ = _run(6000, dict(m750=0.5 * t.C002_M750_DES_KGH))
    r = out[-1]
    assert r.level_pct == pytest.approx(50.00, abs=0.01)
    assert r.m_743_kgh == pytest.approx(33635.2, abs=0.1)
    assert r.lic_op_pct == pytest.approx(57.98, abs=0.01)
    assert col.w["NH3"] == pytest.approx(0.05423, abs=1e-5)


def test_328p006_at_the_heel_delivers_what_the_column_holds():
    """Decision 11. LV-328503 held wide open, on Fisher's equal percentage (decision 150), draws
    several times the 33.8 t/h of liquid: the pump reaches the heel at 38.6 s, and from then on delivers only what arrives less what
    boils, flagged, making no liquid."""
    col, out, made = _run(6000, man=100.0)
    first = next(k for k, r in enumerate(out) if r.suction_lost)
    assert first * DT == pytest.approx(38.6, abs=1e-9)
    assert all(r.suction_lost for r in out[first:])
    assert col.m_kg == pytest.approx(c.C002_M_FLOOR_KG, abs=1e-6)
    assert out[-1].m_743_kgh == pytest.approx(out[-1].in_kgh - out[-1].gen_kgh, rel=1e-9)
    assert abs(made) < 1e-9


def test_a_full_shell_overflows():
    """Decision 11. LV-328503 held at 20 %, on Fisher's equal percentage (decision 150): the shell
    fills at 25 t/h and is full at 1462.4 s; from then on the column holds 11 988 kg and 25.4 t/h
    leaves as the overflow, the books closed to 1e-8 kg over the 2000 s."""
    col, out, made = _run(20000, man=20.0)
    first = next(k for k, r in enumerate(out) if r.m_overflow_kgh > 0.0)
    assert first * DT == pytest.approx(1462.4, abs=1e-9)
    assert col.m_kg == c.C002_FULL_KG == pytest.approx(11987.77, abs=0.01)
    assert out[-1].m_overflow_kgh == pytest.approx(25386.5, abs=0.1)
    assert out[-1].level_pct == pytest.approx(377.40, abs=0.01)
    assert abs(made) < 1e-8


def test_sv32850_and_sv32851_hold_a_blocked_column():
    """B-47. 328D001 at 7.0 bar a: the overhead stops and the column climbs to SV32850's set,
    6.01 bar a, 11.9 s on. Both valves lift together — each certified for 25 t/h at 6.51 bar a,
    so 51.9 t/h at the set pressure on the column's vapour — and vent the head space down to
    5.51 bar a, 10 % of the set pressure below it, where they reseat. The column then cycles
    between the two every 2.7 s, venting what it boils."""
    col, lic = fd.FirstDesorber(), fd.lic_328503()
    out = []
    for k in range(6000):
        out.append(col.step(lic, t.C002_M738_DES_KGH, t.C002_T738_DES_C, t.C002_M748_DES_KGH,
                            dict(t.DES_C003.y), t.C002_M750_DES_KGH, dict(t.DES_C004.y),
                            t.C002_M775_DES_KGH, t.C003_P_BARA,
                            7.0 if k >= 10 else t.D001_P_BARA, DT))
    lifts = [k for k in range(1, len(out))
             if out[k].relief_lifted and not out[k - 1].relief_lifted]
    assert lifts[0] == 119 and out[118].p_bara >= c.SV32850_SET_BARA
    assert out[119].m_relief_kgh == pytest.approx(51916.11, abs=0.01)
    assert (lifts[-1] - lifts[-2]) * DT == pytest.approx(2.7, abs=1e-9)
    assert min(r.p_bara for r in out[119:]) == pytest.approx(c.SV32850_RESEAT_BARA, abs=1e-9)
    assert out[-1].m_737_kgh == 0.0
    assert sum(r.m_relief_kgh for r in out) * DT / 3600.0 == pytest.approx(816.56, abs=0.01)

