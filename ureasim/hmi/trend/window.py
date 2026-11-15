"""The multi-pen trend window: a separate top-level window, ten pens, seven spans, ten rulers.

What it shows
-------------
Up to ten instruments against plant time, each on its own range, over a span of one minute to
eight hours (or one typed, 5 s to 24 h), live or scrolled back through the historian's eight
hours. Under the plot a table gives each pen's live value, its MIN / MAX / AVG over the view,
its range and its value under every ruler. A pen is added from a screen element's menu
("Trend") or by dragging the element onto the plot or onto a row; CLEAR takes every pen off.

Where the samples come from
---------------------------
From the engine's historian, and only from it. The window keeps no samples: once a second, while
it is live, it asks for its whole visible window (`EngineBridge.request_history`, one request in
flight) and repaints the answer; scrolled back, it asks once for the window it moved to. Two
consoles trending one tag therefore draw one trace, and a console that reconnects has lost
nothing. A refused or lost answer blanks the pens and says so — a trend that froze on its last
answer would look live and not be. What the window does keep is its view: the pens chosen, the
span, the rulers, the ranges typed, which V1 kept in the browser's storage and the port keeps in
the console's settings.

Source: V1 ``frontend/trend.js`` (the popup role). The port's changes: the historian as the only
source, where V1 also appended every packet's values to its pens; and the CLEAR button, which V1
did not have (the process engineer's request of 2026-11-15, decision 211).
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from typing import Any, Mapping

from PyQt6.QtCore import QSettings, Qt, QTimer
from PyQt6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QVBoxLayout, QWidget)

from ureasim.data.trend import (DEFAULT_SPAN_S, HISTORY_DEPTH_S, MAX_POINTS, PAN_FRACTION,
                                POLL_MS, RULERS_MAX, SLOTS, SPANS, STALE_S)
from ureasim.hmi import theme
from ureasim.hmi.state_access import ATM_BAR, NO_DATA, get_path
from ureasim.hmi.trend.plot import TrendPlot
from ureasim.hmi.trend.series import (PenSource, auto_range, desk_clock, hms, newest_time,
                                      parse_span, pen_points, span_label, to_percent,
                                      value_at, wall_at, window_stats)
from ureasim.hmi.trend.table import PenTable, RowView

#: An answer not back within this long is given up and asked again [s].
REQUEST_TIMEOUT_S = 5.0
#: How long a refusal note stays up [ms] (V1's 1.4 s).
FLASH_MS = 1400
#: The settings key the view is kept under.
SETTINGS_KEY = "trend/view"


@dataclass
class _Pen:
    """One slot's pen: what it trends and the range it is drawn on."""

    source: PenSource
    lo: float
    hi: float
    auto: bool


class TrendWindow(QWidget):
    """The trend window; one per console."""

    def __init__(self, bridge, sources: Mapping[str, PenSource],
                 settings: QSettings | None = None, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Trend — Urea OTS")
        self.resize(1040, 720)
        self.bridge = bridge
        self.sources = dict(sources)
        self.settings = settings
        self.slots: list[_Pen | None] = [None] * SLOTS
        self.span = DEFAULT_SPAN_S
        self.marked: list[int] = []
        self.axis_pen = -1
        self.rulers: list[float] = []
        self.view_end_t: float | None = None
        self.answer: Mapping[str, Any] | None = None
        self.history_reason = ""
        self._pending = 0
        self._pending_at = 0.0
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(self.poll)
        self._timer.start()
        bridge.history_received.connect(self._on_history)
        bridge.snapshot.connect(self._on_snapshot)
        self._restore()
        self.render()

    # ---- construction --------------------------------------------------------------

    def _button(self, text: str, slot, tip: str = "") -> QPushButton:
        b = QPushButton(text, self)
        b.setToolTip(tip)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.clicked.connect(slot)
        return b

    def _build_ui(self) -> None:
        self.setStyleSheet(
            f"QWidget {{ background:{theme.TW_BG}; color:{theme.PANEL_TEXT}; }}"
            f"QPushButton {{ background:{theme.TW_BUTTON_BG}; color:{theme.TW_BUTTON_TEXT}; "
            f"border:1px solid {theme.TW_BORDER}; padding:3px 7px; border-radius:3px; "
            f"font-weight:bold; }}"
            f"QPushButton:checked {{ background:{theme.TW_SPAN_ON_BG}; color:#fff; "
            f"border-color:{theme.TW_SPAN_ON_BORDER}; }}"
            f"QPushButton:disabled {{ color:{theme.TW_EMPTY_TEXT}; }}"
            f"QLineEdit {{ background:{theme.TW_BUTTON_BG}; color:{theme.TW_BUTTON_TEXT}; "
            f"border:1px solid {theme.TW_BORDER}; padding:3px; }}")
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)

        head = QHBoxLayout()
        head.setContentsMargins(8, 6, 8, 6)
        title = QLabel("TREND", self)
        title.setStyleSheet("font-weight:bold; letter-spacing:1px;")
        head.addWidget(title)
        self.no_history = QLabel("", self)
        self.no_history.setStyleSheet(
            f"background:{theme.TW_NOHIST_BG}; border:1px solid {theme.TW_NOHIST_BORDER}; "
            f"color:{theme.TW_NOHIST_TEXT}; padding:1px 5px;")
        self.no_history.hide()
        head.addWidget(self.no_history)
        self.flash_label = QLabel("", self)
        self.flash_label.setStyleSheet(f"background:{theme.TW_FLASH_BG}; "
                                       f"color:{theme.TW_FLASH_TEXT}; padding:1px 8px;")
        self.flash_label.hide()
        head.addWidget(self.flash_label)
        head.addStretch(1)
        self.span_buttons: dict[int, QPushButton] = {}
        for seconds, label in SPANS:
            b = self._button(label, lambda _c=False, s=seconds: self.set_span(s))
            b.setCheckable(True)
            self.span_buttons[seconds] = b
            head.addWidget(b)
        self.span_edit = QLineEdit(self)
        self.span_edit.setPlaceholderText("e.g. 30s")
        self.span_edit.setFixedWidth(60)
        self.span_edit.setToolTip("Custom span — type a value like 30s, 10m, 3h, then press Enter")
        self.span_edit.returnPressed.connect(self._custom_span)
        head.addWidget(self.span_edit)
        head.addWidget(self._button("CLEAR", self.clear_pens, "Remove every pen from the table"))
        head.addWidget(self._button("SAVE", self.save_dialog, "Save trend image"))
        column.addLayout(head)

        self.plot = TrendPlot(lambda x: self._clock(x, plant=True),
                              lambda x: self._clock(x, plant=False), self._axis_label, SLOTS,
                              self)
        self.plot.clicked.connect(lambda x: self.add_ruler(self.view_end() + x))
        self.plot.ruler_dragged.connect(self._ruler_dragged)
        self.plot.tag_dropped.connect(lambda tag: self.add_tag(tag))
        column.addWidget(self.plot, 1)

        bar = QHBoxLayout()
        bar.setContentsMargins(8, 4, 8, 4)
        bar.setSpacing(8)
        self.back_button = self._button("◀", lambda: self.pan(-1), "Scroll back")
        self.fwd_button = self._button("▶", lambda: self.pan(+1), "Scroll forward")
        self.live_button = self._button("LIVE", self.go_live, "Return to live")
        bar.addWidget(self.back_button)
        bar.addWidget(self.fwd_button)
        bar.addWidget(self.live_button)
        bar.addWidget(QLabel("CURRENT", self))
        self.plant_clock = QLabel("00:00:00", self)
        self.desk_clock = QLabel("--:--:--", self)
        self.plant_clock.setStyleSheet(f"color:{theme.TW_LIVE_TEXT}; font-weight:bold;")
        self.desk_clock.setStyleSheet(f"color:{theme.TW_DESK_TICK};")
        bar.addWidget(self.plant_clock)
        bar.addWidget(self.desk_clock)
        bar.addWidget(QLabel("RULERS", self))
        self.ruler_row = QHBoxLayout()
        bar.addLayout(self.ruler_row)
        self.ruler_hint = QLabel(f"click plot to add · drag to move (up to {RULERS_MAX})", self)
        self.ruler_hint.setStyleSheet(f"color:{theme.TW_EMPTY_TEXT}; font-style:italic;")
        bar.addWidget(self.ruler_hint)
        bar.addStretch(1)
        column.addLayout(bar)

        self.table = PenTable(SLOTS, theme.TREND_PENS, self)
        self.table.setFixedHeight(250)
        self.table.mark_toggled.connect(self.set_mark)
        self.table.remove_clicked.connect(self.remove_slot)
        self.table.range_committed.connect(self.commit_range)
        self.table.tag_dropped.connect(self.add_tag)
        column.addWidget(self.table)

    # ---- the view ------------------------------------------------------------------

    @property
    def live(self) -> bool:
        return self.view_end_t is None

    def now_sim(self) -> float:
        """The plant clock: the latest packet's, or the newest sample's."""
        t = (self.bridge.latest or {}).get("t_sim")
        if isinstance(t, (int, float)):
            return float(t)
        return newest_time(self.answer) or 0.0

    def view_end(self) -> float:
        """The plant time at the plot's right edge: the newest sample while live."""
        if not self.live:
            return float(self.view_end_t)
        newest = newest_time(self.answer)
        return newest if newest is not None else self.now_sim()

    def max_pan_back(self) -> float:
        return max(0.0, min(self.now_sim(), HISTORY_DEPTH_S) - self.span)

    def _clock(self, x: float, plant: bool) -> str:
        t = self.view_end() + x
        if t < 0:
            return ""
        if plant:
            return hms(t)
        w = wall_at(self.answer, t)
        return "" if w is None else desk_clock(w)

    def _axis_label(self, pct: float) -> str:
        pen = self.slots[self.axis_pen] if 0 <= self.axis_pen < SLOTS else None
        if pen is None:
            return f"{pct:g}%"
        return f"{pen.lo + pct / 100.0 * (pen.hi - pen.lo):.{pen.source.dec}f}"

    # ---- the historian -------------------------------------------------------------

    def paths(self) -> list[str]:
        return sorted({p.source.path for p in self.slots if p is not None})

    def poll(self) -> None:
        """The live window's once-a-second request; scrolled back, the window does not move."""
        if self.live and self.isVisible():
            self.request()

    def request(self, force: bool = False) -> None:
        """Ask the historian for the whole visible window, unless an answer is already due."""
        paths = self.paths()
        if not paths:
            self.answer, self._pending = None, 0
            self.render()
            return
        if (self._pending and not force
                and time.monotonic() - self._pending_at < REQUEST_TIMEOUT_S):
            return
        req = self.bridge.request_history(paths, self.span, MAX_POINTS,
                                          None if self.live else self.view_end_t)
        if not req:
            self._no_history("LINK DOWN")
            return
        self._pending, self._pending_at = req, time.monotonic()

    def _on_history(self, req_id: int, ok: bool, reason: str, result: Any) -> None:
        if req_id != self._pending:
            return                          # superseded by a newer request
        self._pending = 0
        if not ok or not isinstance(result, Mapping):
            self._no_history(reason or "no answer")
            return
        self.answer, self.history_reason = result, ""
        self.render()

    def _no_history(self, reason: str) -> None:
        """No answer to draw: blank the pens and say why, rather than freeze on the last."""
        self.answer, self.history_reason, self._pending = None, reason, 0
        self.render()

    def _on_snapshot(self, state: Mapping[str, Any]) -> None:
        if not state:
            self._no_history("LINK DOWN")
            return
        self._render_clocks()
        self._render_table()

    def _render_clocks(self) -> None:
        """CURRENT: the plant clock and the desktop clock of the latest packet."""
        self.plant_clock.setText(hms(self.now_sim()))
        self.desk_clock.setText(desk_clock((self.bridge.latest or {}).get("t")))

    # ---- operator actions ----------------------------------------------------------

    def flash(self, message: str) -> None:
        self.flash_label.setText(message)
        self.flash_label.show()
        QTimer.singleShot(FLASH_MS, self.flash_label.hide)

    def add_tag(self, tag: str, slot: int | None = None) -> bool:
        """Trend ``tag`` in ``slot``, or in the first free slot."""
        source = self.sources.get(tag)
        if source is None:
            self.flash("NOT BOUND")
            return False
        existing = next((i for i, p in enumerate(self.slots) if p and p.source.tag == tag), -1)
        if existing >= 0 and slot in (None, existing):
            return True
        if slot is None:
            slot = next((i for i, p in enumerate(self.slots) if p is None), None)
        if slot is None:
            self.flash("SLOTS FULL")
            return False
        self.slots[slot] = _Pen(source, source.seed[0], source.seed[1], not source.digital)
        self._changed()
        return True

    def remove_slot(self, slot: int) -> None:
        if self.slots[slot] is None:
            return
        self.slots[slot] = None
        self.set_mark(slot, False)
        self._changed()

    def clear_pens(self) -> None:
        """Take every pen off the plot and the table; the span and the rulers stay.

        The cleared view is kept, and with no pen left the window asks the historian nothing, so
        an answer still due for the old pens is dropped when it arrives.
        """
        if all(p is None for p in self.slots):
            return
        self.slots = [None] * SLOTS
        self.marked = []
        self.axis_pen = -1
        self._changed()

    def set_mark(self, slot: int, on: bool) -> None:
        """Mark a pen: thickened, drawn on top, the others faded; the last marked reads the
        left axis."""
        on = on and self.slots[slot] is not None
        if slot in self.marked:
            self.marked.remove(slot)
        if on:
            self.marked.append(slot)
        self.axis_pen = self.marked[-1] if self.marked else -1
        self._save()
        self.render()

    def commit_range(self, slot: int, which: str, text: str) -> None:
        """Fix a pen's LOW or HIGH; blank returns it to auto-scale."""
        pen = self.slots[slot]
        if pen is None:
            return
        if not text.strip():
            pen.auto = True
        else:
            try:
                v = float(text)
            except ValueError:
                v = math.nan
            lo, hi = (v, pen.hi) if which == "lo" else (pen.lo, v)
            if not math.isfinite(v) or hi - lo <= 0.0:
                self.flash("BAD RANGE")
            else:
                pen.lo, pen.hi, pen.auto = lo, hi, False
        self._save()
        self.render()

    def set_span(self, span_s: int) -> None:
        self.span = int(span_s)
        self._changed()

    def _custom_span(self) -> None:
        s = parse_span(self.span_edit.text())
        if s is None:
            self.flash("BAD SPAN (e.g. 30s 10m 3h)")
            return
        self.set_span(s)

    def pan(self, direction: int) -> None:
        """Scroll a quarter of the span back (-1) or forward (+1); forward past now is live."""
        target = self.view_end() + self.span * PAN_FRACTION * direction
        now = self.now_sim()
        self.view_end_t = None if target >= now else max(target, now - self.max_pan_back())
        self._changed()

    def go_live(self) -> None:
        if not self.live:
            self.view_end_t = None
            self._changed()

    def add_ruler(self, t: float) -> bool:
        if any(abs(r - t) < 1e-6 for r in self.rulers):
            return False
        if len(self.rulers) >= RULERS_MAX:
            self.flash(f"MAX {RULERS_MAX} RULERS")
            return False
        self.rulers.append(t)
        self.render()
        return True

    def remove_ruler(self, index: int) -> None:
        if 0 <= index < len(self.rulers):
            del self.rulers[index]
            self.render()

    def _ruler_dragged(self, index: int, x: float) -> None:
        if 0 <= index < len(self.rulers):
            ve = self.view_end()
            self.rulers[index] = min(max(ve + x, ve - self.span), ve)
            self._render_table()
            self._render_rulers()

    def _changed(self) -> None:
        """The view changed: repaint what is known now, and ask for the new window."""
        self._save()
        self.render()
        self.request(force=True)

    # ---- rendering -----------------------------------------------------------------

    def points(self, slot: int) -> list[tuple[float, float]]:
        pen = self.slots[slot]
        return [] if pen is None else pen_points(self.answer, pen.source)

    def render(self) -> None:
        """Repaint everything from the last answer and the view."""
        ve = self.view_end()
        start = ve - self.span
        self.rulers = [r for r in self.rulers if start <= r <= ve]
        self.plot.set_span(self.span)
        for i, pen in enumerate(self.slots):
            if pen is None:
                self.plot.clear_pen(i)
                continue
            pts = [(t, v) for t, v in self.points(i) if start <= t <= ve]
            if pen.auto and not pen.source.digital:
                rng = auto_range(pts, start, ve)
                if rng is not None:
                    pen.lo, pen.hi = rng
            xs = [t - ve for t, _ in pts]
            ys = [to_percent(v, pen.lo, pen.hi) for _, v in pts]
            if pen.source.digital and xs:
                # A state pen holds each value until the next: drawn as steps.
                xs = [x for pair in zip(xs, xs[1:] + [xs[-1]]) for x in pair]
                ys = [y for y in ys for _ in (0, 1)]
            self.plot.draw_pen(i, xs, ys, theme.TREND_PENS[i], i in self.marked,
                               bool(self.marked) and i not in self.marked)
        self._render_rulers()
        self._render_table()
        self._render_clocks()
        self.span_edit.setText("" if any(self.span == s for s, _ in SPANS)
                               else span_label(self.span))
        for seconds, button in self.span_buttons.items():
            button.setChecked(seconds == self.span)
        self.live_button.setText("LIVE" if self.live else "HISTORY")
        self.live_button.setStyleSheet(
            f"background:{theme.TW_LIVE_BG if self.live else theme.TW_HIST_BG}; "
            f"color:{theme.TW_LIVE_TEXT if self.live else theme.TW_HIST_TEXT};")
        self.fwd_button.setEnabled(not self.live)
        self.back_button.setEnabled(self.now_sim() - ve < self.max_pan_back() - 1e-6)
        self.no_history.setText(f"HISTORY UNAVAILABLE — {self.history_reason}")
        self.no_history.setVisible(bool(self.history_reason))

    def _render_rulers(self) -> None:
        ve = self.view_end()
        colours = theme.TREND_RULERS
        self.plot.set_rulers([(t - ve, f"R{i + 1} {hms(t)}", colours[i])
                              for i, t in enumerate(self.rulers)])
        while self.ruler_row.count():
            old = self.ruler_row.takeAt(0).widget()
            old.hide()                      # out of the layout now, not only when deleted
            old.deleteLater()
        for i, t in enumerate(self.rulers):
            w = wall_at(self.answer, t)
            chip = self._button(f"R{i + 1} {hms(t)}" + ("" if w is None else
                                                          f" / {desk_clock(w)}") + " ✕",
                                lambda _c=False, k=i: self.remove_ruler(k), "Remove ruler")
            chip.setStyleSheet(f"color:{colours[i]}; border:1px solid {colours[i]};")
            self.ruler_row.addWidget(chip)
        self.ruler_hint.setVisible(not self.rulers)

    def live_value(self, pen: _Pen) -> str:
        """The pen's live value, as every indicator on the screens reads it."""
        v = get_path(self.bridge.latest, pen.source.path)
        if isinstance(v, bool):
            v = 1.0 if v else 0.0
        if not isinstance(v, (int, float)) or not math.isfinite(v):
            return NO_DATA
        return f"{v - ATM_BAR if pen.source.gauge else v:.{pen.source.dec}f}"

    def _render_table(self) -> None:
        ve = self.view_end()
        start, now = ve - self.span, self.now_sim()
        colours = theme.TREND_RULERS[:len(self.rulers)]
        self.table.set_ruler_columns(len(self.rulers), colours)
        for i, pen in enumerate(self.slots):
            if pen is None:
                self.table.show_row(i, RowView(), colours)
                continue
            dec = pen.source.dec
            pts = self.points(i)
            stats = window_stats(pts, start, ve)
            stale = bool(pts) and now - pts[-1][0] > STALE_S
            fmt = (lambda v: NO_DATA if v is None else f"{v:.{dec}f}")
            self.table.show_row(i, RowView(
                tag=pen.source.tag, value=self.live_value(pen),
                stats=tuple(fmt(s) for s in stats) if stats else (NO_DATA,) * 3,
                range_text=f"{pen.lo:.{dec}f} – {pen.hi:.{dec}f}", auto=pen.auto,
                rulers=tuple(fmt(value_at(pts, r)) for r in self.rulers),
                unit="STALE" if stale else pen.source.unit,
                low=f"{pen.lo:.{dec}f}", high=f"{pen.hi:.{dec}f}",
                marked=i in self.marked), colours)

    # ---- the image and the kept view -----------------------------------------------

    def save_image(self, path: str) -> bool:
        """Write the window — plot, clocks, rulers and table — to a PNG."""
        return self.grab().save(path, "PNG")

    def save_dialog(self) -> None:
        name = time.strftime("Trend_Report_%Y-%m-%d_%H-%M-%S.png")
        path, _ = QFileDialog.getSaveFileName(self, "Save trend image", name, "PNG image (*.png)")
        if path:
            self.save_image(path)

    def _save(self) -> None:
        if self.settings is None:
            return
        self.settings.setValue(SETTINGS_KEY, json.dumps({
            "span": self.span, "marked": self.marked, "axis": self.axis_pen,
            "tags": [p.source.tag if p else None for p in self.slots],
            "ranges": [[p.lo, p.hi] if p and not p.auto else None for p in self.slots]}))

    def _restore(self) -> None:
        if self.settings is None:
            return
        try:
            kept = json.loads(str(self.settings.value(SETTINGS_KEY, "") or "{}"))
        except ValueError:
            return
        span = kept.get("span")
        if isinstance(span, int) and span > 0:
            self.span = span
        for i, tag in enumerate((kept.get("tags") or [])[:SLOTS]):
            source = self.sources.get(tag) if tag else None
            if source is None:
                continue
            pen = _Pen(source, source.seed[0], source.seed[1], not source.digital)
            r = (kept.get("ranges") or [None] * SLOTS)[i]
            if isinstance(r, list) and len(r) == 2 and r[1] > r[0]:
                pen.lo, pen.hi, pen.auto = float(r[0]), float(r[1]), False
            self.slots[i] = pen
        self.marked = [i for i in kept.get("marked") or []
                       if isinstance(i, int) and 0 <= i < SLOTS and self.slots[i]]
        self.axis_pen = self.marked[-1] if self.marked else -1

    def closeEvent(self, event) -> None:
        self._save()
        super().closeEvent(event)


__all__ = ["TrendWindow", "REQUEST_TIMEOUT_S", "SETTINGS_KEY"]
