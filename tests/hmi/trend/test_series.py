"""What a trend pen reads — `ureasim.hmi.trend.series` — on plain historian answers.

Pinned (V1 ``trend.js``'s rules): the registry over the screens, the first bound occurrence, a
pump's ``.on`` flag, an absolute pressure trended gauge, a unit with no seed range on 0 - 1; a pen's
points from an answer, its no-data gaps left out; hold semantics under a ruler; MIN / MAX / AVG and
the auto range over the view only, padded 5 %, a flat trace given a band; the per-cent grid and a
degenerate range at mid-scale; the desktop clock from the answer's own stamps; the clocks; the typed
span.
"""

from __future__ import annotations

import pytest

from ureasim.data.screen_layout import OVERLAYS
from ureasim.hmi.state_access import ATM_BAR
from ureasim.hmi.trend import series as se

SCREENS = {
    "a": [{"t": "ind", "tag": "PIC-1", "bind": "X.p", "u": "BAR A", "dec": 2},
          {"t": "ind", "tag": "TI-1", "bind": "X.t", "u": "C"},
          {"t": "bar", "tag": "LI-1", "bind": "X.l", "u": "%"},
          {"t": "pump", "tag": "P-1", "bind": "pumpA"},
          {"t": "ind", "tag": "AI-1", "bind": "X.a", "u": "us/cm", "dec": 0},
          {"t": "ind", "tag": "FI-1"}],
    "b": [{"t": "ind", "tag": "PIC-1", "bind": "Y.p", "u": "%"},
          {"t": "xv", "tag": "XV-1", "bind": "XV_1"},
          {"t": "avalve", "tag": "PV-1", "bind": "X.pv", "u": "%", "dec": 0}],
}


def test_the_registry_follows_v1s_trend_map():
    s = se.trend_sources(SCREENS)
    assert sorted(s) == ["AI-1", "P-1", "PIC-1", "PV-1", "TI-1", "XV-1"]   # no bar, no unbound
    assert s["PIC-1"] == se.PenSource("PIC-1", "X.p", "BARG", 2, (0.0, 200.0), True)
    assert s["TI-1"] == se.PenSource("TI-1", "X.t", "C", 1, (0.0, 250.0), False)
    assert s["P-1"].path == "pumpA.on" and s["P-1"].digital and s["P-1"].seed == (0.0, 1.0)
    assert s["XV-1"].path == "XV_1" and s["XV-1"].digital
    assert s["AI-1"].unit == "US/CM" and s["AI-1"].seed == (0.0, 1.0) and not s["AI-1"].digital


def test_the_registry_over_the_ten_screens():
    """234 trendable tags: every bound indicator, valve opening, push button, block valve and
    pump, AI-329701 among them (decision 98), the six auxiliary pumps bound to their run
    state (decision 222), and the melt header's FT-335401, HIC-335602 and HV-335602 (decisions
    224 and 225), and the pump pairs decision 227 gives a run state; 25 pressures trend
    gauge, 25 tags are digital."""
    s = se.trend_sources(OVERLAYS)
    assert len(s) == 234 and s["AI-329701"].path == "ANALYSERS.AI_329701"
    assert sum(v.gauge for v in s.values()) == 25 and sum(v.digital for v in s.values()) == 25
    assert s["323P001A"].path == "PUMPS.323P001A.on" and s["323P001A"].digital
    assert s["PIC-323203"].path == "LPCC_3232.E011.PIC_323203.pv" and s["PIC-323203"].gauge


ANSWER = {"t_sim": [10.0, 11.0, 12.0, 13.0, 14.0], "t_wall": [1000.0, 1001.0, 1002.0, 1003.0, 1004.5],
          "series": {"X.p": [2.0, 2.5, None, 3.0, 2.0], "X.t": [40.0, 40.0, 40.0, 40.0, 40.0]}}


def test_a_pen_reads_its_points_gauge_and_skips_no_data():
    s = se.trend_sources(SCREENS)
    pts = se.pen_points(ANSWER, s["PIC-1"])
    assert pts == [(10.0, 2.0 - ATM_BAR), (11.0, 2.5 - ATM_BAR), (13.0, 3.0 - ATM_BAR),
                   (14.0, 2.0 - ATM_BAR)]
    assert se.pen_points(ANSWER, s["XV-1"]) == [] and se.pen_points(None, s["TI-1"]) == []
    assert se.newest_time(ANSWER) == 14.0 and se.newest_time({}) is None


def test_a_ruler_reads_the_last_sample_at_or_before_it():
    pts = [(10.0, 1.0), (11.0, 2.0), (13.0, 3.0)]
    assert [se.value_at(pts, t) for t in (9.9, 10.0, 12.5, 13.0, 99.0, None)] == [
        None, 1.0, 2.0, 3.0, 3.0, None]


def test_statistics_and_auto_range_cover_the_view_only():
    pts = [(10.0, 1.0), (11.0, 5.0), (12.0, 3.0), (20.0, 100.0)]
    assert se.window_stats(pts, 10.0, 12.0) == (1.0, 5.0, 3.0)
    assert se.window_stats(pts, 30.0, 40.0) is None
    assert se.auto_range(pts, 10.0, 12.0) == pytest.approx((0.8, 5.2))
    assert se.auto_range([(1.0, 7.0), (2.0, 7.0)], 0.0, 5.0) == pytest.approx((6.45, 7.55))
    assert se.auto_range(pts, 30.0, 40.0) is None


def test_the_per_cent_grid():
    assert se.to_percent(5.0, 0.0, 10.0) == 50.0
    assert se.to_percent(15.0, 0.0, 10.0) == 150.0          # proportional, not clipped
    assert se.to_percent(3.0, 2.0, 2.0) == 50.0             # a degenerate range: mid-scale


def test_the_desktop_clock_comes_from_the_answers_stamps():
    assert se.wall_at(ANSWER, 9.0) is None
    assert se.wall_at(ANSWER, 10.0) == 1000.0
    assert se.wall_at(ANSWER, 13.5) == pytest.approx(1003.75)
    assert se.wall_at(ANSWER, 16.0) == pytest.approx(1006.5)  # carried past the newest
    assert se.wall_at({}, 10.0) is None


def test_the_clocks_and_the_typed_span():
    assert se.hms(3725.9) == "01:02:05" and se.hms(-5.0) == "00:00:00"
    assert se.desk_clock(None) == "--:--:--" and se.desk_clock(float("nan")) == "--:--:--"
    assert [se.parse_span(t) for t in ("30s", "10m", "3h", "90", "1.5m", " 2 H ")] == [
        30, 600, 10800, 90, 90, 7200]
    assert [se.parse_span(t) for t in ("4s", "25h", "x", "", "-5m", "1e3", "3d")] == [
        None, None, None, None, None, None, None]
    assert [se.span_label(s) for s in (60, 3600, 28800, 7200 * 3, 600, 45)] == [
        "1m", "1h", "8h", "6h", "10m", "45s"]
