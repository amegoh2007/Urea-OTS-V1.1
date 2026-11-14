"""The step panel: a caption, a published readout, and two buttons that each ask the engine for one step.

What it is
----------
322-1's CO2 FEED panel (decision 220, the process engineer's instruction I-1 of 2026-11-13), V1's
"Compressor Speed" hand station (``frontend/co2_compressor.js``) restored: the CO2 asked of 320K002 in
per cent of its design feed, stepped down or up by one press. V1 kept the percentage in the browser
and suppressed its own resync for 1.5 s after a press; here the engine holds the demand and does the
step (``co2_step``), and the panel shows only what the packet publishes. A burst of presses is a burst
of commands, each stepping from the engine's own value, so no press is lost to a stale readout.

The buttons grey at the published limits, as V1's did, so an operator cannot press past them; the
engine clamps a step that arrives anyway. The colours are V1's panel's. 324-1b's GRANULATION HEADERS
panel (decision 224, I-3 of 2026-11-14) is the same panel on the header valves online, DECREASE and
INCREASE; each panel's command, limits and captions are data (`data.faceplates.STEP_PANELS`).

Interaction
-----------
An overlay emits; it never acts (`ureasim.hmi.widgets.base`). A press and release on DOWN or UP emits
``command_requested`` with the engine command the element names and the step's direction, which the
screen relays to the console's bridge; a click on the panel's body is an ordinary ``activated``.

Source: V1 ``frontend/co2_compressor.js`` (the layout, the captions, the colours, the limits).
"""

from __future__ import annotations

from typing import Any, Mapping

from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QWidget

from ureasim.data.faceplates import STEP_PANELS
from ureasim.hmi import theme
from ureasim.hmi.state_access import get_path
from ureasim.hmi.widgets.base import OverlayWidget

__all__ = ["StepPanelWidget"]

#: The panel's inner layout [px], V1's: padding, caption height, gap (the button width is the
#: panel's own, `data.faceplates.StepPanel.button_px`).
_PAD_X, _PAD_TOP, _CAPTION_H, _GAP, _PAD_BOTTOM = 8, 5, 13, 6, 6


class StepPanelWidget(OverlayWidget):
    """A caption over a readout between two buttons; each asks the engine for one step."""

    def __init__(self, element: Mapping[str, Any], parent: QWidget | None = None):
        super().__init__(element, parent)
        self.panel = STEP_PANELS[str(element["cmd"])]
        self.resize_to(int(element.get("w") or 196), int(element.get("h") or 53))
        self._value: float | None = None
        self._caption_font = QFont()
        self._caption_font.setFamilies(theme.UI_FONT_FAMILIES)
        self._caption_font.setPixelSize(11)
        self._caption_font.setBold(True)
        self._button_font = QFont(self._caption_font)
        self._value_font = QFont()
        self._value_font.setFamilies(theme.VALUE_FONT_FAMILIES)
        self._value_font.setPixelSize(15)
        self._value_font.setBold(True)
        self._unit_font = QFont(self._value_font)
        self._unit_font.setPixelSize(10)
        self._unit_font.setBold(False)
        self.setToolTip(f"{element.get('tag', '')} — {element.get('cap', '')}: {self.panel.hint}")

    # ----------------------------------------------------------------------------------
    # Geometry
    # ----------------------------------------------------------------------------------

    def _row(self) -> QRect:
        top = _PAD_TOP + _CAPTION_H + 4
        return QRect(_PAD_X, top, self.width() - 2 * _PAD_X, self.height() - top - _PAD_BOTTOM)

    def button_rect(self, direction: int) -> QRect:
        """The step down (-1) on the left of the row, the step up (+1) on its right."""
        row, width = self._row(), self.panel.button_px
        x = row.left() if direction < 0 else row.right() - width + 1
        return QRect(x, row.top(), width, row.height())

    def _readout_rect(self) -> QRect:
        row, width = self._row(), self.panel.button_px
        return row.adjusted(width + _GAP, 0, -(width + _GAP), 0)

    # ----------------------------------------------------------------------------------
    # State: the packet's, nothing kept
    # ----------------------------------------------------------------------------------

    def update_from(self, snapshot: Mapping[str, Any] | None) -> None:
        value = get_path(snapshot, str(self.element.get("bind", "")))
        self._value = float(value) if isinstance(value, (int, float)) else None
        self.update()

    def enabled(self, direction: int) -> bool:
        """A button is live unless the published value already stands at its limit."""
        if self._value is None:
            return True
        if direction > 0:
            return self._value < self.panel.hi - 1e-6
        return self._value > self.panel.lo + 1e-6

    def command(self, direction: int) -> dict:
        """The engine command one press sends: the element's command and the step's direction."""
        return {"type": self.panel.command, self.panel.field: direction}

    def _direction_at(self, pos: QPoint) -> int | None:
        for direction in (-1, +1):
            if self.button_rect(direction).contains(pos):
                return direction
        return None

    # ----------------------------------------------------------------------------------
    # Mouse
    # ----------------------------------------------------------------------------------

    def mouseReleaseEvent(self, event) -> None:
        if (not self.editing and event.button() == Qt.MouseButton.LeftButton
                and self._press_origin is not None):
            direction = self._direction_at(event.position().toPoint())
            if direction is not None:
                self._press_origin = None
                if self.enabled(direction):
                    self.command_requested.emit(self.command(direction))
                event.accept()
                return
        super().mouseReleaseEvent(event)

    # ----------------------------------------------------------------------------------
    # Painting (V1's panel)
    # ----------------------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        rect = self.rect().adjusted(0, 0, -1, -1)
        at_max = self._value is not None and not self.enabled(+1)
        p.fillRect(rect, QColor(theme.RATIO))
        p.setPen(QColor(theme.OVRD_ARMED if at_max else theme.STEP_PANEL_BORDER))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(rect)

        p.setFont(self._caption_font)
        p.setPen(QColor(theme.STEP_PANEL_CAPTION))
        p.drawText(QRect(0, _PAD_TOP, self.width(), _CAPTION_H), Qt.AlignmentFlag.AlignCenter,
                   str(self.element.get("cap", "")).upper())

        p.setFont(self._button_font)
        metrics = p.fontMetrics()
        for direction, label, glyph in ((-1, self.panel.labels[0], "▼"),
                                        (+1, self.panel.labels[1], "▲")):
            box = self.button_rect(direction)
            live = self.enabled(direction)
            p.setOpacity(1.0 if live else theme.STEP_BUTTON_DEAD_OPACITY)
            p.fillRect(box, QColor(theme.TAB_BG if live else theme.STEP_BUTTON_DEAD))
            p.setPen(QColor(theme.TAB_BORDER))
            p.drawRect(box.adjusted(0, 0, -1, -1))
            # The glyph in the button's colour (UP green, DOWN amber), the word in the tab text.
            head, tail = f"{glyph} ", label
            x = box.left() + (box.width() - metrics.horizontalAdvance(head + tail)) // 2
            p.setPen(QColor((theme.BTN_GREEN if direction > 0 else theme.OVRD_ARMED) if live
                            else theme.STEP_BUTTON_DEAD_TEXT))
            p.drawText(QRect(x, box.top(), box.width(), box.height()),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, head)
            p.setPen(QColor(theme.TAB_TEXT if live else theme.STEP_BUTTON_DEAD_TEXT))
            p.drawText(QRect(x + metrics.horizontalAdvance(head), box.top(), box.width(), box.height()),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, tail)
        p.setOpacity(1.0)

        box = self._readout_rect()
        p.fillRect(box, QColor(theme.PI_BG))
        p.setPen(QColor(theme.PI_BORDER))
        p.drawRect(box.adjusted(0, 0, -1, -1))
        dec = int(self.element.get("dec", 1))
        text = "--" if self._value is None else f"{self._value:.{dec}f}"
        p.setFont(self._value_font)
        p.setPen(QColor(theme.OVRD_ARMED if at_max else theme.STEP_PANEL_VALUE))
        value_box = box.adjusted(0, 0, -14, 0)
        p.drawText(value_box, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, text)
        p.setFont(self._unit_font)
        p.setPen(QColor(theme.STEP_PANEL_UNIT))
        p.drawText(box.adjusted(box.width() - 13, 0, 0, 0),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   str(self.element.get("u", "")))
