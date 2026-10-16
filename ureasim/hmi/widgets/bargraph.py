"""Vertical level bargraph — the level element a slide comment marks as a display bar.

What an operator reads from it
------------------------------
Tank, drum and column level as a filled column, 0-100 %. A bargraph is read faster than a
number, which is why every level on these drawings has one beside its transmitter: the
operator sees "filling" or "draining" from across the room, then reads the number when it
matters.

Empty state
-----------
When the bound path yields nothing, the bar draws as a white outline with no fill — the
same "not modelled / no data" statement the empty indicator slot makes. A bar stuck at a
plausible-looking 50 % would be indistinguishable from a real level.
"""

from __future__ import annotations

from typing import Any, Mapping

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget

from ureasim.hmi import theme
from ureasim.hmi.state_access import get_path
from ureasim.hmi.widgets.base import OverlayWidget

#: Fallback box when the drawing gave no extent, from V1's stylesheet.
DEFAULT_W = 12
DEFAULT_H = 60


class BargraphWidget(OverlayWidget):
    """Vertical level bargraph bound to a 0-100 % level."""

    def __init__(self, element: Mapping[str, Any], parent: QWidget | None = None):
        super().__init__(element, parent)
        self._level: float | None = None
        self.resize_to(int(element.get("w") or DEFAULT_W),
                       int(element.get("h") or DEFAULT_H))
        self.setToolTip(f"{element.get('tag', '')} - no data")

    def update_from(self, snapshot: Mapping[str, Any] | None) -> None:
        raw = get_path(snapshot, self.element.get("bind"))
        level = None
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            v = float(raw)
            if v == v:                                   # not NaN
                level = max(0.0, min(100.0, v))          # clamp: a bar cannot overfill
        if level != self._level:
            self._level = level
            self.update()
        tag = self.element.get("tag", "")
        self.setToolTip(f"{tag} - " + ("no data" if level is None else f"{level:.1f} %"))

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        rect = self.rect().adjusted(0, 0, -1, -1)

        if self._level is None:
            # No data: white outline, transparent field.
            p.setPen(QColor(theme.BAR_EMPTY_BORDER))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(rect)
            return

        p.fillRect(rect, QColor(theme.BAR_BG))
        # Fill grows from the BOTTOM, as a liquid level does.
        fill_h = int(round(rect.height() * self._level / 100.0))
        if fill_h > 0:
            p.fillRect(rect.left(), rect.bottom() - fill_h + 1,
                       rect.width(), fill_h, QColor(theme.BAR_FILL))
        p.setPen(QColor(theme.BAR_BORDER))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(rect)

        if self.editing:
            p.setPen(QColor(theme.EDIT_OUTLINE))
            p.drawRect(rect)


__all__ = ["BargraphWidget"]
