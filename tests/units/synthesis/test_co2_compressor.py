"""320K002 as a boundary feed — `ureasim.units.synthesis.co2_compressor`.

What is being proved
--------------------
320K002 is outside the simulator's scope (decided 2026-10-08): its hardwired governor delivers
the demanded CO2 into the discharge line at whatever pressure the line presents. Pinned: the
delivery is the demand, never negative; the discharge line it feeds closes its design point
exactly; a part load and a line packing up behind a shut XV-322902 take the demand without a
surge, a stonewall or a lag; and no operator command reaches the demand.
"""

from __future__ import annotations

import pytest

from ureasim.data.unit_320 import (
    CO2_CHECK_CRACK_BAR,
    CO2_DP_HP_DES,
    CO2_P_DES_BARA,
    SYN_P_DES_BARA,
)
from ureasim.data.unit_321 import CO2_DES_KGH
from ureasim.units.synthesis.co2_compressor import delivery_kgh
from ureasim.units.synthesis.co2_line import CO2FeedLine, vent_pressure_loop

DT = 0.1


@pytest.mark.parametrize("demand", [0.0, 0.8 * CO2_DES_KGH, CO2_DES_KGH, 1.2 * CO2_DES_KGH])
def test_the_delivery_is_the_demand(demand):
    assert delivery_kgh(demand) == demand


def test_a_negative_demand_delivers_nothing():
    """A governor cannot drive a machine backwards."""
    assert delivery_kgh(-5000.0) == 0.0


def test_the_line_holds_its_design_point_exactly():
    line, pic = CO2FeedLine(), vent_pressure_loop()
    for _ in range(600):
        r = line.step(pic, CO2_DES_KGH / 1000.0, SYN_P_DES_BARA, DT)
    assert line.pressure_bara == CO2_P_DES_BARA
    assert r.delivered_kgh == CO2_DES_KGH and r.vent_th == 0.0
    assert r.load_pct == pytest.approx(100.0, rel=1e-12)


def test_a_part_load_is_delivered_at_once_and_the_line_settles_below_design():
    """At 80 % the boundary delivers 80 % on the first tick — no governor lag, no surge — and the
    line settles where the check valve passes it: the differential above the crack pressure falls
    as the flow squared."""
    line, pic = CO2FeedLine(), vent_pressure_loop()
    first = line.step(pic, 0.8 * CO2_DES_KGH / 1000.0, SYN_P_DES_BARA, DT)
    assert first.delivered_kgh == 0.8 * CO2_DES_KGH
    for _ in range(6000):
        r = line.step(pic, 0.8 * CO2_DES_KGH / 1000.0, SYN_P_DES_BARA, DT)
    assert r.feed_kgh == pytest.approx(0.8 * CO2_DES_KGH, rel=1e-6)
    assert line.pressure_bara - SYN_P_DES_BARA == pytest.approx(
        CO2_CHECK_CRACK_BAR + 0.64 * (CO2_DP_HP_DES - CO2_CHECK_CRACK_BAR), rel=1e-6)


def test_a_shut_isolation_packs_the_line_until_sv32064_relieves_the_demand():
    """XV-322902 shut: the boundary keeps delivering and the line packs up to SV32064's 161.013
    bar a set, below PIC-322203's 168.01 (handoff B-83, decided 2026-10-09); the valve stays lifted
    and relieves the whole demand at 147.55 bar a, the vent shut. (Before B-83 the line packed to
    PIC-322203's set point and the vent took the demand there.)"""
    line, pic = CO2FeedLine(), vent_pressure_loop()
    line.xv_322902_open = False
    for _ in range(20000):
        r = line.step(pic, CO2_DES_KGH / 1000.0, SYN_P_DES_BARA, DT)
    assert r.feed_th == 0.0 and r.vent_th == 0.0 and r.relief_lifted
    assert line.pressure_bara == pytest.approx(147.55, abs=0.05)
    assert r.relief_kgh == pytest.approx(CO2_DES_KGH, rel=1e-3)


def test_no_process_screen_reaches_the_demand_decided_divergence():
    """The battery-limit CO2 rate is the instructor's boundary, never a trainee's control (decision
    73). V1's screen 322-1 carried its COMPRESSOR SPEED hand station, which sends ``co2_set``
    (``frontend/co2_compressor.js``); the port's screens send it from no element, and of the
    console's modules only the instructor's panel does (decision 149)."""
    import pathlib

    from ureasim.data.screen_layout import OVERLAYS
    js = pathlib.Path(r"E:/Simulator/Urea Simulation/frontend/co2_compressor.js")
    if js.exists():
        assert "type: 'co2_set'" in js.read_text(encoding="utf-8", errors="replace")
    assert all(e.get("cmd") != "co2_set" for els in OVERLAYS.values() for e in els)
    hmi = pathlib.Path(__file__).resolve().parents[3] / "ureasim" / "hmi"
    senders = {p.relative_to(hmi).as_posix() for p in hmi.rglob("*.py")
               if "co2_set" in p.read_text(encoding="utf-8")}
    assert senders == {"instructor/panel.py"}
