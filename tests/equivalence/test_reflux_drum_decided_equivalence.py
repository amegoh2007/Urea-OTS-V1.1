"""V1 <-> V1.1 equivalence for 328D001's decided divergences, each asserted from both sides.

What is being proved
--------------------
`test_reflux_drum_equivalence.py` compares the port with the transcription carrying every
departure on every tick of every scenario. Here each departure runs both ways: V1's lines for it
against the port, bit-exact until it first acts, then V1's behaviour asserted on V1's side and
the port's on the port's. Four were decided by the process engineer for this unit on 2026-09-30
(decisions 28, 29 and 30, and handoff B-53), one on 2026-10-01 (SV32353, handoffs B-47 and A-16);
five are classes decided on other units and applied under §5 rule 7 (decisions 24, 11, 23 and
10), TV-328002's Neldisc among decision 23's (2026-10-17), which the other harness runs on V1's
linear law (`test_reflux_drum_equivalence._drum_and_loops`).
"""

from __future__ import annotations

import pytest

from ureasim.data import desorption_train as t
from ureasim.data import unit_328d001 as d
from ureasim.units.desorption import reflux_drum as rd
from tests.equivalence import test_first_desorber_equivalence as c002_eq
from tests.equivalence import test_reflux_drum_equivalence as d001_eq
from tests.equivalence.v1_loader import v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

#: V1's namespaces, built as 328D001's own equivalence test builds them.
tank_v1 = d001_eq.tank_v1
e007_v1 = d001_eq.e007_v1
c002_v1 = d001_eq.c002_v1
v1 = d001_eq.v1

ALL = d001_eq.ALL
_both, _design, _step = d001_eq._both, d001_eq._design, d001_eq._step
_manual, _set_point = d001_eq._manual, d001_eq._set_point


# --------------------------------------------------------------------------------------
# Decided for this unit, 2026-09-30
# --------------------------------------------------------------------------------------

def test_328e004_held_above_its_cooling_water_decided_divergence(v1):
    """Decision 28. 737 lost with TV-328002 held at 50 %: V1's stroke-proportional duty goes on
    taking 4357 kW and the drum passes 30 C, the cooling water, 84 s on, and -494 C, far below
    absolute zero, at 40 minutes. The port's 328E004 takes only what brings the drum to 30 C: it
    holds 30 C on 59.4 kW, 718A's heat from 45 C, and the drum falls to 323E011's pressure."""
    r = _both(v1, _step(10, m737=0.0), 4800, 0.5, _manual("TIC_328002", "tic_328002", 50.0),
              ALL - {"pinch"})
    assert r.parted == 178 and (r.parted - 10) * 0.5 == 84.0
    assert r.s.a328_d001_T == pytest.approx(-493.864, abs=1e-3) and r.s.a328_d001_P == 0.1
    assert r.drum.t_c == pytest.approx(30.0, abs=1e-9)
    assert r.b.q_e004_kw == pytest.approx(3561.5 * 4.0 * 15.0 / 3600.0, rel=0.01)
    assert r.drum.p_bara == pytest.approx(1.1109, abs=1e-4) and r.b.m_786_kgh == 0.0
    assert abs(r.made) < 1e-6


def test_328e004_wide_open_on_design_feeds_decided_divergence(v1):
    """Decision 28. TV-328002 wide open on the design feeds: V1 takes 8714 kW, twice the design,
    and the drum goes on cooling to -246 C; the port holds 30 C on 4710 kW, and the vapour
    328E004 leaves uncondensed falls to 255 kg/h."""
    r = _both(v1, lambda k: _design(), 4800, 0.5, _manual("TIC_328002", "tic_328002", 100.0),
              ALL - {"pinch"})
    assert r.parted == 179
    assert r.s.a328_d001_T == pytest.approx(-245.918, abs=1e-3) and r.a["Q"] == 8714.0
    assert (r.drum.t_c, r.b.q_e004_kw, r.b.gen_kgh) == (
        pytest.approx(30.0, abs=1e-9), pytest.approx(4709.99, abs=0.01),
        pytest.approx(255.31, abs=0.01))


def test_the_vent_on_323e011s_live_pressure_decided_divergence(v1):
    """Decision 29. 323E011 at 1.8 bar a from 5 s: V1's vent goes on passing its 276 kg/h against
    the design 1.13 bar a; the port's passes 236.6 kg/h on the tick, and the drum rises to 2.861
    bar a, where PV-328202 passes the uncondensed 276 again."""
    r = _both(v1, _step(10, pe011=1.8), 1200, 0.5, None, ALL - {"vent"})
    assert r.parted == 10
    assert (r.a["786"], r.s.a328_d001_P) == (pytest.approx(276.0, rel=1e-12), 2.6)
    assert r.drum.p_bara == pytest.approx(2.8608, abs=1e-4)
    q = _both(v1, _step(10, pe011=1.8), 11, 0.5, None, ALL - {"vent"})
    assert q.b.m_786_kgh == pytest.approx(236.574, abs=1e-3)


def test_328c002s_overflow_enters_the_drum_decided_divergence(v1):
    """Decision 30. 2000 kg/h of liquid carried out of a full 328C002 at its 139 C bottoms: V1 has
    no such stream and the drum stays at 50.5 %; the port's drum takes it — LI-328501 at 53.8 %
    ten minutes on, LV-328501 passing 10 620 kg/h, the drum at 61.38 C — its books closed."""
    r = _both(v1, _step(10, mover=2000.0), 1200, 0.5, None, ALL - {"A-15"})
    assert r.parted == 10
    assert (r.a["LI_328501"], r.s.a328_d001_T) == (pytest.approx(50.5, abs=1e-9),
                                                  pytest.approx(61.0, abs=1e-9))
    assert (r.b.level_pct, r.b.m_776_kgh, r.drum.t_c) == (
        pytest.approx(53.782, abs=1e-3), pytest.approx(10620.31, abs=0.01),
        pytest.approx(61.384, abs=1e-3))
    assert abs(r.made) < 1e-6


def test_the_vessel_and_its_taps_decided_divergence(v1):
    """B-53. The drum seeded at rest on both sides, LI-328501 at 50.5 %: V1 holds 2401.7 kg on its
    cylinder's reading, the port 3029.7 on the taps'. LV-328501 shut: V1's 4.34 m3 cylinder is full
    at 1024 s; the port's 5.5 m3 vessel at 1301.5 s, its LI-328501 at 100 % from 793 s, when the
    liquid covers the upper tap. 737 cut a fifth: the taps read 48.32 % ten minutes on, V1 48.40."""
    r = _both(v1, lambda k: _design(), 1, 0.5, None, ALL - {"B-53"})
    assert r.parted == 0
    assert (r.a["LI_328501"], r.b.level_pct) == (pytest.approx(50.5, abs=1e-12), 50.5)
    q = _both(v1, lambda k: _design(), 4000, 0.5, _manual("LIC_328501", "lic_328501", 0.0),
              ALL - {"B-53"})
    assert q.first["over"] == 2603 and q.drum.m_kg == d.D001_FULL_KG == 6022.5
    assert q.s.a328_d001_M == pytest.approx(4755.79, abs=0.01)
    c = _both(v1, _step(10, m737=0.8 * t.C002_M737_DES_KGH), 1200, 0.5, None, ALL - {"B-53"})
    assert (c.a["LI_328501"], c.b.level_pct) == (pytest.approx(48.396, abs=1e-3),
                                                 pytest.approx(48.316, abs=1e-3))


# --------------------------------------------------------------------------------------
# Decided for this unit, 2026-10-01: SV32353 (handoffs B-47, A-16)
# --------------------------------------------------------------------------------------

def test_sv32353_on_the_written_out_law(v1):
    """PV-328202 shut on the design feeds, the transcription carrying the relief: bit-exact for
    forty minutes of SV32353 lifting and reseating."""
    d001_eq._run(v1, lambda k: _design(), 4800, 0.5,
                 before=_manual("PIC_328202", "pic_328202", 0.0))


def test_sv32353_relieves_a_shut_vent_decided_divergence(v1):
    """PV-328202 shut on the design feeds: 328E004 leaves its 276 kg/h uncondensed and the head
    space has no way out. V1 relieves nothing: its drum stands at 111.6 bar a forty minutes on.
    The port is bit-exact with it until SV32353 lifts at its 6.01 bar a set pressure, 75.5 s on;
    from then on the valve vents the drum to 5.51 bar a, on the gas blowdown, and lifts again every
    12.5 s — 186 times in forty minutes, peaking at 6.032 bar a and venting 178.2 kg, all but the
    head space's rise to set of what 328E004 left uncondensed. The liquid's books close on both
    sides: the relief comes out of the head space alone."""
    before = _manual("PIC_328202", "pic_328202", 0.0)
    r = _both(v1, lambda k: _design(), 4800, 0.5, before, ALL - {"relief"})
    assert r.parted == 151 and r.parted * 0.5 == 75.5
    assert r.s.a328_d001_P == pytest.approx(111.635, abs=1e-3)
    assert r.drum.p_bara == pytest.approx(6.0097, abs=1e-4)
    assert abs(r.made) < 1e-6 and abs(r.made_v1) < 1e-6
    s, (drum, loops) = d001_eq._v1_state(v1, ALL), d001_eq._drum_and_loops()
    before(s, drum, loops)
    lifts, was, p_hi, p_lo, vented = [], False, 0.0, 99.0, 0.0
    for k in range(4800):
        b = d001_eq._port(drum, loops, _design(), 0.5)
        if b.relief_lifted and not was:
            lifts.append(k)
        was = b.relief_lifted
        vented += b.m_relief_kgh * 0.5 / 3600.0
        p_hi = max(p_hi, b.p_bara)
        if lifts:
            p_lo = min(p_lo, b.p_bara)
    assert lifts[:3] == [151, 176, 201] and len(lifts) == 186
    assert p_hi == pytest.approx(6.0325, abs=1e-4) and p_lo == d.SV32353_RESEAT_BARA == 5.51
    assert vented == pytest.approx(178.25, abs=0.01)


# --------------------------------------------------------------------------------------
# Classes decided on other units, applied under §5 rule 7
# --------------------------------------------------------------------------------------

def test_the_liquid_pays_what_stays_vapour_decided_divergence(v1):
    """Decision 24. TV-328002 at 30 % by hand: 328E004 leaves 460 kg/h uncondensed, which the
    head space takes, while PV-328202 vents 463. V1's liquid loses the vent's flow and makes 2.24
    kg in ten minutes; the port's loses what stays vapour, and makes none."""
    r = _both(v1, lambda k: _design(), 1200, 0.5, _manual("TIC_328002", "tic_328002", 30.0),
              ALL - {"vapour"})
    assert r.parted == 0
    assert (r.a["gen"], r.a["786"]) == (pytest.approx(460.0, rel=1e-12),
                                        pytest.approx(462.589, abs=1e-3))
    assert r.made_v1 == pytest.approx(2.237, abs=1e-3) and abs(r.made) < 1e-6


def test_328p002_at_the_heel_decided_divergence(v1):
    """Decision 11. LV-328501 wide open drains the drum to its heel at 548 s. V1's 776 goes on at
    28 163 kg/h and its 1 kg floor makes 3.60 t in the next 20 minutes; the port's 775 and 776
    share what arrives and does not stay vapour, flagged, making none."""
    r = _both(v1, lambda k: _design(), 2400, 0.5, _manual("LIC_328501", "lic_328501", 100.0),
              ALL - {"heel"})
    assert r.parted == r.first["lost"] == 1096
    assert r.a["776"] == pytest.approx(28162.75, abs=0.01)
    assert r.made_v1 == pytest.approx(3600.42, abs=0.01) and abs(r.made) < 1e-6
    assert r.b.suction_lost and r.drum.m_kg == pytest.approx(1.0, abs=1e-9)
    assert r.b.m_775_kgh + r.b.m_776_kgh == pytest.approx(
        r.b.in_kgh - r.b.gen_kgh, rel=1e-9)


def test_a_full_drum_overflows_decided_divergence(v1):
    """Decision 11. LV-328501 shut: the drum is full at 1301.5 s. V1 goes on filling past its 5.5
    m3, 7.6 t at 2000 s — 127 % of what it holds; the port's holds 6022.5 kg and lets the 8275.5
    kg/h that arrives go as the overflow, its books closed."""
    r = _both(v1, lambda k: _design(), 4000, 0.5, _manual("LIC_328501", "lic_328501", 0.0),
              ALL - {"overflow"})
    assert r.parted == r.first["over"] == 2603
    assert r.s.a328_d001_M == pytest.approx(7627.16, abs=0.01)
    assert r.s.a328_d001_M / d.D001_FULL_KG > 1.26
    assert r.drum.m_kg == d.D001_FULL_KG
    assert r.b.m_overflow_kgh == pytest.approx(8275.50, abs=0.01)
    assert abs(r.made_v1) < 1e-6 and abs(r.made) < 1e-6


@pytest.mark.parametrize("v1_name, name, op, field, v1_flow, flow", [
    ("LIC_328501", "lic_328501", 50.0, "776", 8275.5, 14081.37),
    ("PIC_328202", "pic_328202", 50.0, "786", 276.0, 202.36),
    ("FIC_328404", "fic_328404", 30.2, "775", 1675.0, 754.06),
], ids=["LV-328501 at 50 %", "PV-328202 at 50 %", "FV-328404 at 30.2 %"])
def test_the_valves_on_their_vendor_trims_decided_divergence(v1, v1_name, name, op, field,
                                                             v1_flow, flow):
    """Decision 23. Each valve held at V1's design stroke: V1 passes the design flow there; the
    port's, on its vendor trim from the stroke its Kvs gives, passes what the trim passes."""
    r = _both(v1, lambda k: _design(), 1, 0.5, _manual(v1_name, name, op), ALL - {"valve"})
    assert r.parted == 0
    port = {"776": r.b.m_776_kgh, "786": r.b.m_786_kgh, "775": r.b.m_775_kgh}[field]
    assert (r.a[field], port) == (pytest.approx(v1_flow, rel=1e-12),
                                  pytest.approx(flow, abs=0.01))


def test_tv_328002_on_its_vendor_trim_decided_divergence(v1):
    """Decision 23's class, decided 2026-10-17: TV-328002 on Metso's DN 200 Neldisc, its printed
    capacities as its curve, from its 55.04 % design stroke, where V1 runs it linear from 50 %:
    328E004's duty and TT-329007 read the water the trim passes against its design stroke's. At the
    design seed both duties are 4357 kW and the strokes differ, so the two part on the first tick's
    TIC-328002 output and nothing else. 737 cut a fifth at 5 s: ten minutes on V1's TV-328002 has
    closed 10.5 points, to 39.50 %, and its drum stands at 59.050 C; the Neldisc closes 9.3 points,
    to 48.54 (45.73 before decision 178) %, and its drum stands at 59.848 (59.303 before decision 178) C, 328E004 taking 3446 kW against V1's 3442. Neither
    side makes liquid."""
    r = _both(v1, lambda k: _design(m737=(0.8 * t.C002_M737_DES_KGH if k >= 10
                                          else t.C002_M737_DES_KGH)),
              1200, 0.5, None, ALL, port=(rd.RefluxDrum(), rd.RefluxDrumLoops()))
    assert r.parted == 0
    assert (r.a["tic"], r.b.tic_op_pct) == (pytest.approx(39.496, abs=1e-3),
                                            pytest.approx(48.541, abs=1e-3))
    assert (r.s.a328_d001_T, r.drum.t_c) == (pytest.approx(59.050, abs=1e-3),
                                             pytest.approx(59.848, abs=1e-3))
    assert abs(r.made) < 1e-6 and abs(r.made_v1) < 1e-6


def test_tic_328002_on_span_decided_divergence(v1):
    """Decision 10. TIC-328002 to 55 C at the 0.1 s step: V1's 3.0 per K and the port's 1.875 %/K
    on TT-328002's 0-160 C part on the tick; ten minutes on the drum is at 56.88 and 56.95 C."""
    r = _both(v1, lambda k: _design(), 6000, 0.1, _set_point("TIC_328002", "tic_328002", 55.0),
              ALL - {"gains"})
    assert r.parted == 0
    assert (r.s.a328_d001_T, r.drum.t_c) == (pytest.approx(56.881, abs=1e-3),
                                             pytest.approx(56.946, abs=1e-3))


def test_tic_328008_on_its_faceplate_decided_divergence(v1):
    """Decision 160 (B-116 (b)), 2026-10-28. TIC-328008 to 48 mol% at the 0.1 s step: V1's 240 kg/h
    of reflux per mol% and 110 s and the port's faceplate row — 1.00 and 60 s on 0-100 wt% water,
    84.59 kg/h per mol% on 737's slope — part on the tick; ten minutes on, 737 carries 47.9945
    mol% on V1's tuning and 48.9513 on the row, which is still on its first overshoot (on the drum
    alone both settle, the row's decay ratio 0.87 a 22-minute period against V1's 0.61)."""
    r = _both(v1, lambda k: _design(), 6000, 0.1, _set_point("TIC_328008", "tic_328008", 48.0),
              ALL - {"gains"})
    assert r.parted == 0
    assert (r.s.TIC_328008["pv"], r.loops.tic_328008.pv) == (pytest.approx(47.9945, abs=1e-4),
                                                             pytest.approx(48.9513, abs=1e-4))


def test_pic_328202_on_span_decided_divergence(v1):
    """Decision 10. PIC-328202 to 3.7 bar a, closed through 328C002 — its transmitter on the
    column, its valve on the drum's vent: V1's 2.5 per bar has taken the column 0.044 bar in ten
    minutes, the port's 25 %/bar on PT-328202's 0-10 bar g 0.161 (FIC-328404 and TIC-328008 on
    their faceplates' rows, decisions 156 and 160: 0.1609 where V1's tunings gave 0.1613), both
    monotone. Both run in the
    transcriptions, the port's lines on the side of the gain — bit-exact with the ported column
    and drum coupled (`test_the_drum_takes_737_on_the_same_tick`)."""
    pv = {}
    for side, decided in (("v1", ALL - {"gains"}), ("port", ALL)):
        s = d001_eq._v1_state(v1, decided)
        seen = []
        for k in range(6000):
            if k == 10:
                s.PIC_328202["sp"] = 3.7
            x2 = c002_eq._design(m775=s.tlag.get("R328_775", t.C002_M775_DES_KGH),
                                 pd001=s.a328_d001_P)
            c002_eq._feed(s, x2)
            a2 = c002_eq._v1_c002(v1, s, x2["m738"], x2["t738"], 0.1)
            s.tlag["R3232_718A"], s.a328_d003_TII = d.D001_M718A_DES_KGH, 56.0
            d001_eq._v1_d001(v1, s, a2["737"], a2["in"], 0.0, 0.1, decided, a2["over"])
            seen.append(s.a328_c002_P)
        assert all(b >= a - 1e-12 for a, b in zip(seen, seen[1:])), side
        pv[side] = seen[-1]
    assert (pv["v1"], pv["port"]) == (pytest.approx(3.5440, abs=1e-4),
                                      pytest.approx(3.6609, abs=1e-4))
