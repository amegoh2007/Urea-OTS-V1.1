"""Indicator box — the live value readout, and 199 of the 387 elements on these screens.

What an operator reads from it
------------------------------
    value      the process variable, to the decimals the drawing specifies
    unit       the engineering unit, in a dimmer colour so the number dominates
    mode badge A / E / M / O for a controller — AUTO, CAS, MAN, out of service
    frame      cyan when a left-click opens a faceplate; white when the tag is drawn on
               the slide but the engine does not model it yet

The empty slot is a feature
---------------------------
A tag that the drawing publishes but the engine has no value for renders as a **white
frame carrying only its tag text**. That is a deliberate, visible statement of "not
modelled yet" — as opposed to a box showing a stale number, which is indistinguishable
from a working instrument and is how a trainee learns something false.

An empty slot picks up a live value the moment any screen binds the same tag, through
`ureasim.hmi.state_access.BindMap`.

Why this is painted rather than built from labels
-------------------------------------------------
Three reasons, all of which showed up in practice:

1. **Width.** The box is sized by its *content*, and the drawing's collision budget is
   tight — two boxes on 324-1b sit 80 px apart. A layout's size hint carries each child
   label's own margins plus the layout's spacing, which inflated the box by about 20 px
   and created collisions that are not in the drawing. Painting gives the exact V1 box
   model: ``1 px border + 4 px padding + content + 4 px padding + 1 px border``.
2. **Stylesheet scope.** A Qt stylesheet rule with no selector also matches a widget's
   children, so ``border: 1px solid`` on the box drew a frame around the value, the unit
   and the mode badge as well.
3. **Cost.** 199 indicators refreshing at the UI rate would be 600 child widgets laying
   themselves out on every tick.
"""

from __future__ import annotations

from typing import Any, Mapping

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter
from PyQt6.QtWidgets import QWidget

from ureasim.hmi import theme
from ureasim.hmi.state_access import (
    NO_DATA,
    format_value,
    get_path,
    mode_letter,
    to_display_units,
)
from ureasim.hmi.widgets.base import OverlayWidget

#: Box metrics from V1's ``.ov.ind`` / ``.ov.ind.empty`` rules, in stage pixels.
MIN_W = 30
BOX_H = 18
EMPTY_MIN_W = 34
EMPTY_H = 16
PAD_X = 4          # horizontal padding inside the border
GAP = 3            # gap between value, unit and mode badge
BORDER = 1


def _value_font(px: int, bold: bool) -> QFont:
    """Monospaced, fixed-pitch font so a changing digit does not shift the layout.

    Without fixed pitch a '1' is narrower than an '8', so a live readout re-lays itself
    out on every tick and reads as instrument noise rather than as a steady value.
    """
    f = QFont()
    f.setFamilies(theme.VALUE_FONT_FAMILIES)
    f.setPixelSize(px)
    f.setBold(bold)
    f.setStyleHint(QFont.StyleHint.Monospace)
    return f


class IndicatorWidget(OverlayWidget):
    """Live analogue readout for one DCS tag."""

    def __init__(self, element: Mapping[str, Any], parent: QWidget | None = None):
        super().__init__(element, parent)

        self._bound = bool(element.get("bind"))
        self._has_faceplate = bool(element.get("fp") or element.get("face")
                                   or element.get("ctl"))

        size_px = int(element.get("fs") or (theme.VALUE_FONT_PX if self._bound
                                            else theme.VALUE_FONT_PX_EMPTY))
        self._font_value = _value_font(size_px, bold=self._bound)
        self._font_unit = _value_font(theme.UNIT_FONT_PX, bold=False)
        self._font_mode = _value_font(theme.MODE_FONT_PX, bold=True)

        # Until the first snapshot arrives, a bound box reads '--' and an unbound box shows
        # its tag — so a screen opened before the engine starts is still a readable drawing.
        self._text_value = NO_DATA if self._bound else str(element.get("tag", ""))
        self._text_unit = str(element.get("u") or "") if self._bound else ""
        self._text_mode = ""

        self.setToolTip(str(element.get("tag", "")))
        self._relayout()

    # ----------------------------------------------------------------------------------
    # Sizing
    # ----------------------------------------------------------------------------------

    def _content_width(self) -> int:
        """Exact V1 box model: border + padding + value [+ gap + unit] [+ gap + mode] ..."""
        w = QFontMetrics(self._font_value).horizontalAdvance(self._text_value)
        if self._text_unit:
            w += GAP + QFontMetrics(self._font_unit).horizontalAdvance(self._text_unit)
        if self._text_mode:
            w += GAP + QFontMetrics(self._font_mode).horizontalAdvance(self._text_mode)
        return w + 2 * PAD_X + 2 * BORDER

    def _relayout(self) -> None:
        w = self._content_width()
        if self._bound:
            self.resize_to(max(MIN_W, w), BOX_H)
        else:
            self.resize_to(max(EMPTY_MIN_W, w), EMPTY_H)

    # ----------------------------------------------------------------------------------
    # Live update
    # ----------------------------------------------------------------------------------

    def update_from(self, snapshot: Mapping[str, Any] | None) -> None:
        """Refresh value, unit and mode badge from the snapshot."""
        el = self.element
        if not el.get("bind"):
            # Empty slot: it shows its tag and nothing else. Nothing to update.
            return

        value = get_path(snapshot, el.get("bind"))
        value, unit = to_display_units(value, el.get("u"))

        text_value = format_value(value, el.get("dec"))
        text_unit = str(unit or "")
        text_mode = mode_letter(snapshot, el)

        if (text_value, text_unit, text_mode) == (self._text_value, self._text_unit,
                                                  self._text_mode):
            return                                  # nothing changed; skip the repaint

        self._text_value = text_value
        self._text_unit = text_unit
        self._text_mode = text_mode
        self.setToolTip(self._tooltip(unit, text_mode))
        self._relayout()
        self.update()

    def _tooltip(self, unit, letter) -> str:
        parts = [str(self.element.get("tag", ""))]
        if unit:
            parts.append(f"[{unit}]")
        if letter:
            parts.append("— " + theme.MODE_NAMES.get(letter, letter))
        text = " ".join(parts)
        if self.element.get("note"):
            text += "\n" + str(self.element["note"])
        return text

    # ----------------------------------------------------------------------------------
    # Painting
    # ----------------------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        rect = self.rect().adjusted(0, 0, -BORDER, -BORDER)

        if self._bound:
            bg = QColor(theme.IND_BG)
            border = QColor(theme.IND_FACEPLATE_BORDER if self._has_faceplate
                            else theme.IND_BORDER)
            value_colour = QColor(theme.IND_TEXT)
        else:
            # A translucent field, so the drawing beneath a white-framed empty slot still
            # shows through and the slot reads as "nothing modelled here yet".
            bg = QColor(8, 16, 14, 115)
            border = QColor(theme.IND_EMPTY_BORDER)
            value_colour = QColor(theme.IND_EMPTY_TEXT)

        p.fillRect(rect, bg)
        p.setPen(QColor(theme.EDIT_OUTLINE) if self.editing else border)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(rect)

        x = PAD_X + BORDER
        top = BORDER
        height = rect.height() - BORDER

        p.setFont(self._font_value)
        p.setPen(value_colour)
        vw = QFontMetrics(self._font_value).horizontalAdvance(self._text_value)
        p.drawText(QRect(x, top, vw, height),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   self._text_value)
        x += vw

        if self._text_unit:
            x += GAP
            p.setFont(self._font_unit)
            p.setPen(QColor(theme.IND_UNIT))
            uw = QFontMetrics(self._font_unit).horizontalAdvance(self._text_unit)
            p.drawText(QRect(x, top, uw, height),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       self._text_unit)
            x += uw

        if self._text_mode:
            x += GAP
            p.setFont(self._font_mode)
            p.setPen(QColor(theme.MODE_COLOURS.get(self._text_mode, theme.IND_UNIT)))
            mw = QFontMetrics(self._font_mode).horizontalAdvance(self._text_mode)
            # The badge sits at the TOP of the box, as it does on the real faceplate, so it
            # never competes with the value for the reader's eye.
            p.drawText(QRect(x, top, mw, height),
                       Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                       self._text_mode)


__all__ = ["IndicatorWidget"]
