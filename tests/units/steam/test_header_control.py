"""Behaviour of unit 329's controllers — `ureasim.units.steam.header_control`."""

from __future__ import annotations

import pytest

from ureasim.data import unit_329_network as n
from ureasim.units.steam.header_control import (
    SUPPLY_BIAS_PCT,
    Hv329601,
    LevelLoop,
    Pic329204,
    Pic329205,
    Pic329207,
    v1_pic_329204,
    v1_pic_329207,
)


def test_the_design_seeds():
    """At design every loop sits on its seed: PV-329204 at its Metso design stroke, 44.1 %
    (decided 2026-10-15; V1's 50 %), PV-329205A at its vendor stroke, the trio's A and C shut, B
    on PV-329207B's 54.96 % (V1's 50 % bias)."""
    assert SUPPLY_BIAS_PCT == pytest.approx(50.0, abs=1e-12)
    assert Pic329204().step(19.7, False, 0.1) == pytest.approx(44.1, abs=1e-12)
    assert v1_pic_329204().step(19.7, False, 0.1) == pytest.approx(50.0, abs=1e-12)
    assert Pic329205().step(9.0, 0.1) == (pytest.approx(n.PV205A_OP_DES_PCT, abs=1e-12), 0.0)
    assert Pic329205(table=False).step(9.0, 0.1) == (
        pytest.approx(n.PV205A_OP_DES_PCT, abs=1e-12), 0.0)
    assert Pic329207().step(5.01325, 0.1) == (0.0, n.PV207B_OP_DES_PCT, 0.0)
    assert n.PV207B_OP_DES_PCT == pytest.approx(54.963, abs=1e-3)
    assert v1_pic_329207().step(5.01325, 0.1) == (0.0, 50.0, 0.0)


def test_the_gains_on_span():
    """Decision 10: PIC-329204's table 1.80 on PT-329204's 40 bar, 4.5 %/bar; the trio's 6.00,
    4.00 and 4.00 on PT-329207's 6 bar, 100 and 66.7 %/bar."""
    assert (n.PIC_329204_KC, n.PIC_329204_KI) == (4.5, 0.045)
    assert n.PIC_329207_KC == {"A": 100.0, "B": pytest.approx(66.667, abs=1e-3),
                               "C": pytest.approx(66.667, abs=1e-3)}
    pic = Pic329204()
    assert pic.step(19.2, False, 0.1) == pytest.approx(44.1 + 4.5 * 0.5 + 0.045 * 0.05, abs=1e-12)


def test_trip_21_2_loads_10_bar_g_into_pic_329204():
    """Uhde's sheet 3: on trip 21.2 the set point is 10 bar g, 11.01325 bar a on the standard
    atmosphere (handoff B-6; 11.013 on V1's), for two seconds; the operator may move it
    afterwards."""
    pic = Pic329204()
    pic.step(19.7, True, 0.1)
    assert pic.sp_bara == pytest.approx(11.01325, abs=1e-12)
    for _ in range(25):
        pic.step(19.0, True, 0.1)
    pic.sp_bara = 15.0
    pic.step(19.0, True, 0.1)
    assert pic.sp_bara == 15.0


def test_hv_329601_forced_by_trip_21_2():
    """Above 12 bar g with the trip active HV-329601 is forced open and the operator blocked;
    falling below, forced shut for 3 s, then the operator's — at the shut value it was forced to.
    Without the trip the operator's stroke passes."""
    hv = Hv329601(hic_pct=30.0)
    assert hv.step(19.7, False, 0.1) == 30.0 and not hv.blocked
    assert hv.step(19.7, True, 0.1) == 100.0 and hv.blocked
    assert hv.step(12.9, True, 0.1) == 0.0 and hv.blocked
    for _ in range(29):
        assert hv.step(12.9, True, 0.1) == 0.0
    assert hv.step(12.9, True, 0.1) == 0.0 and not hv.blocked


def test_pic_329205s_split_range():
    """Rising pressure shuts PV-329205A first; past it PV-329205B opens. V1's proportional split
    (``table=False``): 0.5 bar over set, A shut and B at 0.45 %; 0.5 bar under, A at 39.5 %. The
    plant DCS's PI (decided 2026-10-28), 3.00 x 100 % / 16 bar = 18.75 %/bar and 50 s: the same
    half bar over takes A 9.394 % down on the tick and the integral keeps closing it; in MAN the
    split tracks the strokes, so AUTO takes over without a bump."""
    pic = Pic329205(table=False)
    assert pic.step(9.5, 0.1) == (0.0, pytest.approx(0.452, abs=1e-3))
    assert pic.step(8.5, 0.1) == (pytest.approx(39.548, abs=1e-3), 0.0)
    pic.mode = "MAN"
    assert pic.step(12.0, 0.1) == (pytest.approx(39.548, abs=1e-3), 0.0)
    pi = Pic329205()
    a1, b1 = pi.step(9.5, 0.1)
    assert (a1, b1) == (pytest.approx(n.PV205A_OP_DES_PCT - 18.75 * 0.5 * 1.002, abs=1e-9), 0.0)
    assert pi.step(9.5, 0.1)[0] == pytest.approx(a1 - 18.75 * 0.1 / 50.0 * 0.5, abs=1e-9)
    pi.mode, pi.op_a_pct, pi.op_b_pct = "MAN", 0.0, 20.0
    assert pi.step(9.5, 0.1) == (0.0, 20.0) and pi.split_pct == -20.0


def test_the_trio_fans_out_its_master():
    """The master to 4.4 bar a stamps A at 4.5 and C at 4.3; master off, the legs are their own."""
    trio = Pic329207(master_sp_bara=4.4)
    trio.step(5.01325, 0.1)
    assert (trio.legs["A"].sp_bara, trio.legs["B"].sp_bara, trio.legs["C"].sp_bara) == (
        pytest.approx(4.5, abs=1e-12), 4.4, pytest.approx(4.3, abs=1e-12))
    trio.master_on, trio.legs["C"].sp_bara = False, 4.0
    trio.step(5.01325, 0.1)
    assert trio.legs["C"].sp_bara == 4.0


def test_the_level_loops():
    """Velocity PI on per cent of level: LIC-329503 on its row, 2.00 and 200 s; a drain opens on
    a rising level, a make-up closes."""
    drain = LevelLoop("LIC-329503", True, 50.0)
    assert drain.step(51.0, 0.1) == pytest.approx(50.0 + 2.0 * (1.0 + 0.1 / 200.0), abs=1e-12)
    makeup = LevelLoop("LIC-329504", False, 50.0)
    assert makeup.step(51.0, 0.1) < 50.0
