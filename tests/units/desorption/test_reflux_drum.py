"""Behaviour of 328D001 and 328E004, the reflux drum — `ureasim.units.desorption.reflux_drum`.

Equivalence with V1 is proven in `tests/equivalence/test_reflux_drum_equivalence.py` and
`test_reflux_drum_decided_equivalence.py`. This file pins what the drum DOES: the PFD's design
point on the first tick; a cut in 328C002's overhead; 328E004 held above its cooling water
(decision 28); the vent backing up behind a pressurised 323E011 (decision 29); 328C002's overflow
arriving (decision 30); SV32353 relieving a shut vent (A-16); and the two limits of decision 11 —
328P002 at the heel and the full drum overflowing — with the liquid's books closed on what stays
vapour (decision 24). TV-328002 is on Metso's Neldisc from its 55.04 % design stroke (decided
2026-10-17); held at that stroke the drum does what it did at V1's 50 %.
"""

from __future__ import annotations

import pytest

from ureasim.data import desorption_train as t
from ureasim.data import unit_328c002 as c2
from ureasim.data import unit_328d001 as d
from ureasim.units.desorption import reflux_drum as rd

DT = 0.5


def _loop(loops, name):
    loop = getattr(loops, name)
    return loop.loop if isinstance(loop, rd.FlowLoop) else loop


def _run(ticks, dt=DT, man=None, over=None, t0=10):
    """Drive the drum from its design seed; `man` holds loops at an output, `over` replaces
    boundaries from tick t0. Returns the drum, every result, and the liquid the books did not
    see — the liquid loses what stays vapour (decision 24)."""
    drum, loops = rd.RefluxDrum(), rd.RefluxDrumLoops()
    for name, op in (man or {}).items():
        _loop(loops, name).set_mode("MAN")
        _loop(loops, name).op = op
    out, made = [], 0.0
    for k in range(ticks):
        x = dict(m737=t.C002_M737_DES_KGH, mover=0.0, m718a=d.D001_M718A_DES_KGH, m793=0.0,
                 pe011=d.PV202_P2_BARA)
        if over and k >= t0:
            x.update(over)
        pre = drum.m_kg
        r = drum.step(loops, x["m737"], t.C002_T_BOT_C, t.C002_P_TOP_BARA, c2.C002_M_DES_KG,
                      t.C002_IN_DES_KGH, x["mover"], x["m718a"], x["m793"], 56.0, x["pe011"], dt)
        made += drum.m_kg - pre - (r.in_kgh - r.gen_kgh - r.m_775_kgh - r.m_776_kgh
                                   - r.m_overflow_kgh) * dt / 3600.0
        out.append(r)
    return drum, out, made


def test_the_design_point_is_the_pfds():
    """The first tick passes the PFD's 786, 775 and 776 on 737 and 718A, at 61 C and 2.6 bar a;
    328E004 takes its 4357 kW on TV-328002 at its 55.04 % design stroke, the cooling water returns
    at 38 C, and TIC-328008 reads 737's 46.21 mol% of water."""
    drum, out, _ = _run(1, dt=0.1)
    r = out[0]
    assert (r.in_kgh, r.m_786_kgh, r.m_775_kgh, r.m_776_kgh, r.gen_kgh) == (
        d.D001_IN_DES_KGH, 276.0, 1675.0, 8275.5, 276.0)
    assert (r.p_bara, r.t_c, r.level_pct, r.q_net_kw) == (2.6, 61.0, 50.5, 0.0)
    assert (r.q_e004_kw, r.tic_op_pct, r.t_cw_return_c) == (4357.0, d.TV_328002_OP_DES_PCT, 38.0)
    assert (r.t_737_c, r.h2o_737_molpct, r.reflux_sp_kgh) == (117.0, 46.21, 1675.0)
    assert not r.suction_lost and r.m_overflow_kgh == 0.0


def test_tv_328002_on_its_vendor_trim():
    """Decision 23's class, decided 2026-10-17: 328E004's duty and TT-329007 read the water Metso's
    Neldisc passes against its design stroke's, where V1 reads the stroke over 50 %. At 55.04 %
    both give 4357 kW and 38 C; at the sheet's 21.2 % the Neldisc passes 24.3 % of its design
    water, 1060 kW, the water back at 62.9 C (V1's law: 42.4 %), and at 90.5 % 3.08 times it,
    13 434 kW (V1's 1.81) — the duty still held above the cooling water (decision 28)."""
    for op, q, t_cw in ((d.TV_328002_OP_DES_PCT, 4357.0, 38.0), (21.2, 1060.35, 62.872),
                        (90.5, 13433.93, 32.595)):
        _, out, _ = _run(1, dt=0.1, man={"tic_328002": op})
        assert (out[0].q_e004_kw, out[0].t_cw_return_c) == (pytest.approx(q, abs=0.01),
                                                            pytest.approx(t_cw, abs=1e-3))
    assert rd.TV_328002_TRIM == (d.TV_328002_OP_DES_PCT, d.TV_328002_CHAR)


def test_a_cut_in_328c002s_overhead():
    """737 cut a fifth: less to condense, so TIC-328002 closes TV-328002 to 48.5 (45.7 before decision 178) % on its Neldisc
    and the drum settles 1.7 K cooler (39.5 % and 2 K on V1's linear trim); LIC-328501 draws less,
    6721 (6722 before decision 178) kg/h to 323E003 ten minutes on."""
    drum, out, made = _run(1200, over=dict(m737=0.8 * t.C002_M737_DES_KGH))
    r = out[-1]
    assert (r.t_c, r.p_bara, r.level_pct) == (pytest.approx(59.848, abs=1e-3),
                                              pytest.approx(2.6203, abs=1e-4),
                                              pytest.approx(48.318, abs=1e-3))
    assert (r.tic_op_pct, r.m_776_kgh, r.m_775_kgh) == (
        pytest.approx(48.541, abs=1e-3), pytest.approx(6720.86, abs=0.01), 1675.0)
    assert abs(made) < 1e-6


def test_328e004_holds_the_drum_at_its_cooling_water():
    """Decision 28. 737 lost with TV-328002 held at its design stroke: the drum cools to the 30 C
    cooling water in 84 s and holds there, 328E004 taking only 718A's heat from 45 C."""
    drum, out, made = _run(4800, man={"tic_328002": d.TV_328002_OP_DES_PCT},
                           over=dict(m737=0.0))
    first = next(k for k, r in enumerate(out) if r.q_e004_kw < 4357.0)
    assert (first - 10) * DT == 84.0
    assert min(r.t_c for r in out) == pytest.approx(30.0, abs=1e-9)
    assert out[-1].q_e004_kw == pytest.approx(59.42, abs=0.01)
    assert abs(made) < 1e-6


def test_the_vent_backs_up_behind_a_pressurised_323e011():
    """Decision 29. 323E011 at 1.8 bar a: PV-328202 passes 236.6 kg/h on the tick, and the drum
    rises to 2.861 bar a, where it vents the uncondensed 276 again."""
    drum, out, made = _run(1200, over=dict(pe011=1.8))
    assert out[10].m_786_kgh == pytest.approx(236.574, abs=1e-3)
    assert (out[-1].p_bara, out[-1].m_786_kgh) == (pytest.approx(2.8608, abs=1e-4),
                                                   pytest.approx(276.0, abs=0.01))
    assert abs(made) < 1e-6


def test_328c002s_overflow_arrives():
    """Decision 30. 2000 kg/h of 328C002's bottoms carried over at 139 C: LI-328501 at 53.8 %
    ten minutes on, LV-328501 passing 10 621 kg/h forward to 323E003."""
    drum, out, made = _run(1200, over=dict(mover=2000.0))
    r = out[-1]
    assert r.in_kgh == d.D001_IN_DES_KGH + 2000.0
    assert (r.level_pct, r.m_776_kgh) == (pytest.approx(53.781, abs=1e-3),
                                          pytest.approx(10620.65, abs=0.01))
    assert abs(made) < 1e-6


def test_328p002_at_the_heel_passes_what_arrives():
    """Decision 11. LV-328501 wide open: the drum reaches its heel at 548 s, and from then on
    775 and 776 share what arrives less what stays vapour — flagged, making no liquid."""
    drum, out, made = _run(2400, man={"lic_328501": 100.0})
    first = next(k for k, r in enumerate(out) if r.suction_lost)
    assert first * DT == 548.0
    r = out[-1]
    assert r.suction_lost and drum.m_kg == pytest.approx(d.D001_M_FLOOR_KG, abs=1e-9)
    assert r.m_775_kgh + r.m_776_kgh == pytest.approx(r.in_kgh - r.gen_kgh, rel=1e-9)
    assert abs(made) < 1e-6


def test_a_full_drum_overflows():
    """Decision 11 and B-53. LV-328501 shut: LI-328501 reaches 100 % at 793 s, when the liquid
    covers LT-328501's upper tap; the vessel is full at 1301.5 s, and from then on it holds its
    6022.5 kg and the 8275.5 kg/h that arrives leaves as the overflow."""
    drum, out, made = _run(4000, man={"lic_328501": 0.0})
    first = next(k for k, r in enumerate(out) if r.m_overflow_kgh > 0.0)
    assert first * DT == 1301.5
    assert next(k for k, r in enumerate(out) if r.level_pct >= 100.0) * DT == 793.0
    assert drum.m_kg == d.D001_FULL_KG == 6022.5
    assert out[-1].level_pct == pytest.approx(100.0, abs=1e-9)
    assert out[-1].m_overflow_kgh == pytest.approx(8275.50, abs=0.01)
    assert abs(made) < 1e-6


def test_sv32353_holds_a_shut_vent():
    """PV-328202 shut: the 276 kg/h 328E004 leaves uncondensed has no way out of the head space.
    SV32353 (A-16, decided 2026-10-01) lifts at 6.01 bar a 75.5 s on, vents to 5.51 on the gas
    blowdown and lifts again every 12.5 s; the liquid's books close, the relief leaving the head
    space alone."""
    drum, out, made = _run(4800, man={"pic_328202": 0.0})
    lifts = [k for k, r in enumerate(out)
             if r.relief_lifted and (k == 0 or not out[k - 1].relief_lifted)]
    assert lifts[:3] == [151, 176, 201] and len(lifts) == 186
    assert max(r.p_bara for r in out) == pytest.approx(6.0325, abs=1e-4)
    assert min(r.p_bara for r in out[151:]) == d.SV32353_RESEAT_BARA == 5.51
    assert all(r.m_786_kgh == 0.0 for r in out) and abs(made) < 1e-6
