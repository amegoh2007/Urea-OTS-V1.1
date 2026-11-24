"""The trend window — `ureasim.hmi.trend.window` — over a bridge that records its requests.

Pinned: a pen is added by tag (refused unbound, refused past ten, not duplicated); every change
asks the historian for the whole window, the live window once a second with one request in flight;
the window draws the answer it was given and nothing it was given before — no samples are kept;
a superseded answer is ignored; a refusal or a lost link blanks the pens and says why; the table's
live value is the packet's, gauge where it reads gauge; MIN / MAX / AVG and the rulers read the
answer; scrolling back asks for the window it moved to, and LIVE returns; marking a pen moves the
left axis onto its range; a typed range fixes it and blank returns it to auto-scale; CLEAR takes
every pen off, asks the historian nothing and drops an answer still due, keeping the span and the
rulers (decision 211); the view is kept in the console's settings; the window saves as an image;
and a real engine session's historian answers it.
"""

from __future__ import annotations

import pytest
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QPushButton

from ureasim.data.trend import DEFAULT_SPAN_S, MAX_POINTS, RULERS_MAX, SLOTS
from ureasim.hmi.state_access import ATM_BAR
from ureasim.hmi.trend import series as se
from ureasim.hmi.trend.table import (C_AVG, C_MAX, C_MIN, C_RANGE, C_RULER, C_TAG, C_UNIT,
                                     C_VALUE)
from ureasim.hmi.trend.window import SETTINGS_KEY, TrendWindow
from tests.hmi.conftest import FakeBridge

SOURCES = {
    "PIC-1": se.PenSource("PIC-1", "X.p", "BARG", 2, (0.0, 200.0), True),
    "TI-1": se.PenSource("TI-1", "X.t", "C", 1, (0.0, 250.0), False),
    "XV-1": se.PenSource("XV-1", "X.xv", "", 0, (0.0, 1.0), False),
}
for i in range(SLOTS):
    SOURCES[f"T-{i}"] = se.PenSource(f"T-{i}", f"Z.{i}", "%", 1, (0.0, 100.0), False)

LATEST = {"t": 1_700_000_000.0, "t_sim": 120.0, "X": {"p": 3.01325, "t": 41.0, "xv": True}}


def _answer(t0: float, n: int, **series) -> dict:
    t = [t0 + k for k in range(n)]
    return {"t_sim": t, "t_wall": [1_700_000_000.0 - 120.0 + x for x in t],
            "series": {path: [f(x) for x in t] for path, f in series.items()}}


@pytest.fixture()
def win(qapp):
    w = TrendWindow(FakeBridge(dict(LATEST)), SOURCES)
    yield w
    w.close()


def _cell(w: TrendWindow, row: int, col: int) -> str:
    return w.table.item(row, col).text()


def _drawn(w: TrendWindow, slot: int) -> int:
    """How many points a pen's curve holds (an emptied curve holds none)."""
    xs = w.plot._curves[slot].getData()[0]
    return 0 if xs is None else len(xs)


def test_pens_are_added_by_tag(win):
    assert not win.add_tag("NOPE") and win.flash_label.text() == "NOT BOUND"
    assert win.add_tag("TI-1") and win.slots[0].source.tag == "TI-1"
    assert win.add_tag("TI-1") and sum(p is not None for p in win.slots) == 1
    assert win.add_tag("PIC-1", 4) and win.slots[4].source.tag == "PIC-1"
    for i in range(SLOTS):
        win.add_tag(f"T-{i}")
    assert win.flash_label.text() == "SLOTS FULL"
    assert win.slots[0].auto and win.slots[0].lo == 0.0 and win.slots[0].hi == 250.0


def test_every_change_asks_for_the_whole_window_one_request_at_a_time(win):
    bridge = win.bridge
    win.add_tag("TI-1")
    assert bridge.history[-1] == {"id": 100, "paths": ["X.t"], "span": DEFAULT_SPAN_S,
                                  "max_points": MAX_POINTS, "end": None}
    win.show()
    win.poll()
    assert len(bridge.history) == 1                    # the answer is still due
    bridge.answer(_answer(100.0, 21, **{"X.t": lambda t: 40.0}))
    win.poll()
    assert len(bridge.history) == 2 and bridge.history[-1]["end"] is None


def test_the_window_draws_its_answer_and_keeps_nothing(win):
    """Answer A covers 100-120 s; answer B, 115-120 s. After B the pen holds B's six points only:
    the window accumulates nothing between answers."""
    win.add_tag("TI-1")
    win.bridge.answer(_answer(100.0, 21, **{"X.t": lambda t: t - 60.0}))
    xs, ys = win.plot._curves[0].getData()
    assert len(xs) == 21 and xs[-1] == 0.0 and xs[0] == -20.0
    assert (_cell(win, 0, C_MIN), _cell(win, 0, C_MAX), _cell(win, 0, C_AVG)) == (
        "40.0", "60.0", "50.0")
    assert _cell(win, 0, C_RANGE) == "39.0 – 61.0 A"           # auto: padded 5 %
    assert ys[0] == pytest.approx(100.0 / 22.0) and ys[-1] == pytest.approx(2100.0 / 22.0)
    win.request(force=True)
    win.bridge.answer(_answer(115.0, 6, **{"X.t": lambda t: 50.0}))
    xs, _ = win.plot._curves[0].getData()
    assert len(xs) == 6 and win.points(0)[0] == (115.0, 50.0)


def test_a_superseded_answer_is_ignored(win):
    win.add_tag("TI-1")
    win.add_tag("PIC-1")
    first, second = win.bridge.history[0]["id"], win.bridge.history[1]["id"]
    win.bridge.answer(_answer(100.0, 3, **{"X.t": lambda t: 1.0}), req_id=first)
    assert win.answer is None
    win.bridge.answer(_answer(100.0, 3, **{"X.t": lambda t: 2.0, "X.p": lambda t: 3.0}),
                      req_id=second)
    assert win.points(0) == [(100.0, 2.0), (101.0, 2.0), (102.0, 2.0)]


def test_a_refusal_or_a_lost_link_blanks_the_pens_and_says_why(win):
    win.add_tag("TI-1")
    win.bridge.answer(_answer(100.0, 5, **{"X.t": lambda t: 1.0}))
    assert _drawn(win, 0) == 5
    win.request(force=True)
    win.bridge.answer(None, ok=False, reason="no engine attached")
    assert win.answer is None and _drawn(win, 0) == 0
    assert win.no_history.text() == "HISTORY UNAVAILABLE — no engine attached"
    win.request(force=True)
    win.bridge.answer(_answer(100.0, 5, **{"X.t": lambda t: 1.0}))
    assert not win.history_reason
    win.bridge.publish({})
    assert win.answer is None and win.history_reason == "LINK DOWN"
    win.bridge.connected = False
    win.request(force=True)
    assert win.history_reason == "LINK DOWN"


def test_the_table_reads_the_packet_and_the_answer(win):
    win.add_tag("PIC-1")
    win.add_tag("XV-1")
    win.bridge.answer(_answer(100.0, 21, **{"X.p": lambda t: 3.0, "X.xv": lambda t: 1.0}))
    assert _cell(win, 0, C_VALUE) == f"{3.01325 - ATM_BAR:.2f}" and _cell(win, 0, C_UNIT) == "BARG"
    assert _cell(win, 1, C_VALUE) == "1" and _cell(win, 1, C_UNIT) == ""
    assert win.slots[1].lo == 0.0 and win.slots[1].hi == 1.0      # digital: never auto-scaled
    xs, ys = win.plot._curves[1].getData()
    assert len(xs) == 42 and set(ys) == {100.0}                   # stepped
    win.bridge.publish(dict(LATEST, t_sim=200.0))
    assert _cell(win, 0, C_UNIT) == "STALE"


def test_rulers_read_the_answer_under_them(win):
    win.add_tag("TI-1")
    win.bridge.answer(_answer(100.0, 21, **{"X.t": lambda t: t}))
    assert win.add_ruler(105.5) and not win.add_ruler(105.5)
    assert not win.table.isColumnHidden(C_RULER) and win.table.isColumnHidden(C_RULER + 1)
    assert _cell(win, 0, C_RULER) == "105.0"
    for k in range(RULERS_MAX - 1):
        win.add_ruler(101.0 + k)
    assert not win.add_ruler(119.0) and win.flash_label.text() == f"MAX {RULERS_MAX} RULERS"
    win.remove_ruler(0)
    assert len(win.rulers) == RULERS_MAX - 1
    win.set_span(5)                                     # the view narrows: rulers out of it go
    assert win.rulers == [] or all(r >= 115.0 for r in win.rulers)


def test_scrolling_back_asks_for_the_window_it_moved_to(win):
    win.bridge.publish(dict(LATEST, t_sim=7200.0))
    win.add_tag("TI-1")
    win.bridge.answer(_answer(3600.0, 3601, **{"X.t": lambda t: 1.0}))
    assert win.live and not win.fwd_button.isEnabled()
    win.pan(-1)
    assert win.view_end_t == 7200.0 - 900.0 and win.bridge.history[-1]["end"] == 6300.0
    assert win.live_button.text() == "HISTORY" and win.fwd_button.isEnabled()
    for _ in range(20):
        win.pan(-1)
    assert win.view_end_t == 3600.0 and not win.back_button.isEnabled()
    win.show()
    n = len(win.bridge.history)
    win.bridge.answer(_answer(0.0, 10, **{"X.t": lambda t: 1.0}))
    win.poll()
    assert len(win.bridge.history) == n                 # scrolled back, the window does not poll
    win.go_live()
    assert win.live and win.bridge.history[-1]["end"] is None


def test_marking_moves_the_axis_and_ranges_can_be_fixed(win):
    win.add_tag("TI-1")
    win.add_tag("PIC-1")
    win.bridge.answer(_answer(100.0, 21, **{"X.t": lambda t: t, "X.p": lambda t: 2.0}))
    assert win._axis_label(50.0) == "50%"
    win.set_mark(0, True)
    win.set_mark(1, True)
    assert win.marked == [0, 1] and win._axis_label(0.0) == f"{win.slots[1].lo:.2f}"
    win.set_mark(1, False)
    assert win.axis_pen == 0
    win.commit_range(0, "lo", "50")
    win.commit_range(0, "hi", "40")
    assert win.flash_label.text() == "BAD RANGE" and win.slots[0].lo == 50.0
    win.commit_range(0, "hi", "150")
    assert (win.slots[0].lo, win.slots[0].hi, win.slots[0].auto) == (50.0, 150.0, False)
    assert _cell(win, 0, C_RANGE) == "50.0 – 150.0"
    win.commit_range(0, "lo", " ")
    assert win.slots[0].auto and win.slots[0].lo == pytest.approx(99.0)
    win.remove_slot(0)
    assert win.slots[0] is None and win.marked == [] and win.axis_pen == -1


def test_the_view_is_kept_and_the_window_saves_as_an_image(qapp, tmp_path):
    settings = QSettings(str(tmp_path / "ots.ini"), QSettings.Format.IniFormat)
    w = TrendWindow(FakeBridge(dict(LATEST)), SOURCES, settings)
    w.add_tag("TI-1")
    w.add_tag("PIC-1", 3)
    w.set_span(600)
    w.commit_range(3, "hi", "5")
    w.set_mark(3, True)
    assert w.save_image(str(tmp_path / "t.png")) and (tmp_path / "t.png").stat().st_size > 0
    w.close()
    again = TrendWindow(FakeBridge(dict(LATEST)), SOURCES, settings)
    assert again.span == 600 and again.slots[0].source.tag == "TI-1"
    assert (again.slots[3].lo, again.slots[3].hi, again.slots[3].auto) == (0.0, 5.0, False)
    assert again.marked == [3] and again.axis_pen == 3 and again.span_edit.text() == "10m"
    settings.setValue(SETTINGS_KEY, "not json")
    assert TrendWindow(FakeBridge(), SOURCES, settings).slots == [None] * SLOTS
    again.close()


def test_clear_takes_every_pen_off_and_keeps_the_span_and_rulers(qapp, tmp_path):
    settings = QSettings(str(tmp_path / "ots.ini"), QSettings.Format.IniFormat)
    w = TrendWindow(FakeBridge(dict(LATEST)), SOURCES, settings)
    (clear,) = [b for b in w.findChildren(QPushButton) if b.text() == "CLEAR"]
    clear.click()                                       # nothing to clear: nothing asked
    assert w.bridge.history == []
    w.add_tag("TI-1")
    w.add_tag("PIC-1", 4)
    w.set_mark(4, True)
    w.set_span(600)
    w.bridge.answer(_answer(100.0, 21, **{"X.t": lambda t: 40.0, "X.p": lambda t: 3.0}))
    assert w.add_ruler(110.0) and _drawn(w, 0) == 21 and _drawn(w, 4) == 21
    w.request(force=True)                               # an answer is due for the old pens
    due, sent = w.bridge.history[-1]["id"], len(w.bridge.history)
    clear.click()
    assert w.slots == [None] * SLOTS and w.marked == [] and w.axis_pen == -1
    assert len(w.bridge.history) == sent                # no pen, no request
    assert _drawn(w, 0) == 0 and _drawn(w, 4) == 0
    empty = _cell(w, SLOTS - 1, C_TAG)                  # a slot never used
    assert _cell(w, 0, C_TAG) == empty and _cell(w, 4, C_TAG) == empty and "TI-1" not in empty
    w.bridge.answer(_answer(100.0, 21, **{"X.t": lambda t: 41.0}), req_id=due)
    assert w.answer is None and _drawn(w, 0) == 0
    assert w.span == 600 and w.rulers == [110.0]
    w.close()
    again = TrendWindow(FakeBridge(dict(LATEST)), SOURCES, settings)
    assert again.slots == [None] * SLOTS and again.span == 600 and again.marked == []
    again.close()


def test_a_drop_trends_the_tag(win):
    win.plot.tag_dropped.emit("TI-1")
    win.table.tag_dropped.emit("PIC-1", 6)
    assert win.slots[0].source.tag == "TI-1" and win.slots[6].source.tag == "PIC-1"


def test_a_real_engine_historian_answers_the_window(qapp, tmp_path):
    """Thirty plant seconds of the design plant through `EngineSession`'s historian, asked as the
    station server asks it: the window draws PIC-323203's gauge pressure at its design 0.12 barg."""
    from ureasim.data.screen_layout import OVERLAYS
    from ureasim.engine.session import EngineSession

    session = EngineSession(tmp_path)
    session.handle({"type": "set_sim_mode", "mode": "x10"})
    session.simulator.run(300)
    bridge = FakeBridge(session.packet(0.0, health=False))
    w = TrendWindow(bridge, se.trend_sources(OVERLAYS))
    w.add_tag("PIC-323203")
    req = bridge.history[-1]
    bridge.answer(session.history(req["paths"], req["span"], req["max_points"], req["end"]))
    pts = w.points(0)
    assert len(pts) >= 29 and pts[-1][1] == pytest.approx(1.13 - ATM_BAR, abs=0.02)
    assert _cell(w, 0, C_UNIT) == "BARG"
    w.close()
