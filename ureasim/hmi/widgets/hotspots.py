"""Hotspots and pushbuttons: nav, stream, analyser, hand switch, override, generic button.

These six types carry no analogue value. They are places on the drawing that *do*
something when clicked.

    NavHotspotWidget    67 elements. Transparent screen-jump. Invisible until hovered,
                        because the drawing already labels the destination.
    StreamHotspotWidget 12 elements. Opens the stream inspector for a drawn process line.
    AnalyserWidget       2 elements. AE-* composition readout.
    HandSwitchWidget     4 elements. The green square inside an "Open XV-..." panel.
    OverrideButtonWidget 6 elements. A maintained keyswitch — HS-322915's override and trip
                        21.2's five (decision 98) — with a lamp lit while its interlock is
                        latched.
    PushButtonWidget     1 element.  Generic faceplate button.

Why a nav hotspot must be invisible but findable
------------------------------------------------
It sits on top of a label the drawing already rendered ("322F001 -> 322-2"). Drawing a box
over it would hide the label; leaving no affordance would make it undiscoverable. So it is
transparent, and grows a cyan border on hover.

They also count for overlap testing: a transparent hotspot that overlaps a live indicator
**steals the click** rather than showing a visible defect, which is exactly the kind of
fault that survives a visual review.
"""

from __future__ import annotations

from typing import Any, Mapping

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QWidget

from ureasim.hmi import theme
from ureasim.hmi.state_access import get_path
from ureasim.hmi.widgets.base import OverlayWidget


class _HoverHotspot(OverlayWidget):
    """Transparent clickable region that reveals itself on hover."""

    HOVER_BORDER = theme.HOTSPOT_HOVER_BORDER
    HOVER_BG = theme.HOTSPOT_HOVER_BG
    EDIT_BORDER = theme.EDIT_NAV_OUTLINE

    def __init__(self, element: Mapping[str, Any], default_box: tuple[int, int],
                 parent: QWidget | None = None):
        super().__init__(element, parent)
        self._hovered = False
        self.resize_to(int(element.get("w") or default_box[0]),
                       int(element.get("h") or default_box[1]))
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        rect = self.rect().adjusted(0, 0, -1, -1)
        if self._hovered:
            p.fillRect(rect, QColor(self.HOVER_BG))
            p.setPen(QColor(self.HOVER_BORDER))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(rect)
        elif self.editing:
            p.setPen(QColor(self.EDIT_BORDER))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(rect)


class NavHotspotWidget(_HoverHotspot):
    """Transparent screen-jump hotspot over a drawn "-> page" label."""

    def __init__(self, element: Mapping[str, Any], parent: QWidget | None = None):
        super().__init__(element, (100, 24), parent)
        self.setToolTip(f"{element.get('tag', '')} (click to open)")


class StreamHotspotWidget(_HoverHotspot):
    """Hotspot over a drawn process line — opens the stream inspector.

    Process utility: lets a trainee interrogate what is actually flowing in a line —
    mass rate, temperature, pressure and composition — which is the question behind most
    "why did that happen" moments on a real console.
    """

    HOVER_BORDER = theme.HOTSPOT_HOVER_BORDER
    EDIT_BORDER = "rgba(255, 160, 60, 178)"

    def __init__(self, element: Mapping[str, Any], parent: QWidget | None = None):
        super().__init__(element, (60, 18), parent)
        self.setToolTip(f"{element.get('tag', '')} — click for stream detail")


class AnalyserWidget(OverlayWidget):
    """Composition indicator (AE-* tag) — opens the composition view."""

    def __init__(self, element: Mapping[str, Any], parent: QWidget | None = None):
        super().__init__(element, parent)
        self._font = QFont()
        self._font.setFamilies(theme.VALUE_FONT_FAMILIES)
        self._font.setPixelSize(10)
        self._font.setBold(True)
        self._text = str(element.get("tag", ""))
        self.setStyleSheet(
            f"background:{theme.AE_BG}; border:1px solid {theme.AE_BORDER}; "
            f"border-radius:3px; color:{theme.AE_TEXT};")
        self.setToolTip(f"{self._text} — "
                        f"{element.get('note') or 'click to view composition'}")
        self.resize_to(int(element.get("w") or 64), int(element.get("h") or 18))

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        rect = self.rect().adjusted(0, 0, -1, -1)
        p.fillRect(rect, QColor(theme.AE_BG))
        p.setPen(QColor(theme.AE_BORDER))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(rect)
        p.setFont(self._font)
        p.setPen(QColor(theme.AE_TEXT))
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._text)


class HandSwitchWidget(OverlayWidget):
    """The green square inside an "Open XV-..." panel.

    It reflects the block valve's state and opens that valve's faceplate. On the real
    panel this is the physical switch an operator turns, so it is drawn as a switch rather
    than as a readout.
    """

    def __init__(self, element: Mapping[str, Any], parent: QWidget | None = None):
        super().__init__(element, parent)
        self._open = False
        self.resize_to(int(element.get("w") or 26), int(element.get("h") or 20))

    def update_from(self, snapshot: Mapping[str, Any] | None) -> None:
        xv = self.element.get("xv")
        open_ = bool(get_path(snapshot, xv)) if xv else False
        if open_ != self._open:
            self._open = open_
            self.update()
        valve = xv.split(".")[-1].replace("_", "-") if xv else ""
        self.setToolTip(
            f"{self.element.get('tag', '')} — {valve} "
            f"{'OPEN' if open_ else 'CLOSED'} (click for faceplate)")

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        rect = self.rect().adjusted(0, 0, -1, -1)
        p.fillRect(rect, QColor(theme.BTN_GREEN if self._open else theme.HS_BG))
        p.setPen(QColor(theme.HS_BORDER))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(rect)


class OverrideButtonWidget(OverlayWidget):
    """Interlock override pushbutton, with an armed lamp.

    Process utility
    ---------------
    A latched interlock has to be *deliberately* overridden — that is the whole safety
    argument for having one. The lamp blinks amber while the interlock is latched (override
    available) and the button commands the block valve when pressed. When no interlock is
    latched the button is dark and pressing it does nothing, which matches the panel.
    """

    LAMP_W, LAMP_H = 13, 9

    def __init__(self, element: Mapping[str, Any], parent: QWidget | None = None):
        super().__init__(element, parent)
        self._armed = False
        self._valve_open = False
        self._font = QFont()
        self._font.setFamilies(theme.VALUE_FONT_FAMILIES)
        self._font.setPixelSize(10)
        self._font.setBold(True)
        self._text = str(element.get("tag", ""))
        self.resize_to(int(element.get("w") or 120), int(element.get("h") or 18))

    def update_from(self, snapshot: Mapping[str, Any] | None) -> None:
        latch = self.element.get("latch", "21_2")
        path = self.element.get("xv") or "XV_322901"
        self._armed = bool(get_path(snapshot, f"trip_latched.{latch}"))
        self._valve_open = bool(get_path(snapshot, path))
        # The green lamp is the valve's state, or, on a trip 21.2 keyswitch, the key's own.
        state = (("KEY TURNED" if self._valve_open else "KEY RELEASED")
                 if path.startswith("HAND_SWITCHES.")
                 else f"XV {'OPEN' if self._valve_open else 'CLOSED'}")
        self.setToolTip(
            f"{self._text} — interlock "
            f"{'LATCHED (override available)' if self._armed else 'clear'}; "
            f"{state} (click for the keyswitch)")
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        rect = self.rect().adjusted(0, 0, -1, -1)
        bg = theme.OVRD_ARMED_BG if self._armed else theme.OVRD_BG
        border = theme.OVRD_ARMED if self._armed else theme.OVRD_BORDER
        text = theme.OVRD_ARMED if self._armed else theme.OVRD_TEXT
        p.fillRect(rect, QColor(bg))
        p.setPen(QColor(border))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(rect)

        lamp_x = rect.left() + 4
        lamp_y = rect.center().y() - self.LAMP_H // 2
        if self._armed:
            lamp = theme.OVRD_ARMED
        elif self._valve_open:
            lamp = theme.BTN_GREEN
        else:
            lamp = theme.OVRD_LAMP_IDLE
        p.fillRect(lamp_x, lamp_y, self.LAMP_W, self.LAMP_H, QColor(lamp))
        p.setPen(QColor(border))
        p.drawRect(lamp_x, lamp_y, self.LAMP_W, self.LAMP_H)

        p.setFont(self._font)
        p.setPen(QColor(text))
        p.drawText(rect.adjusted(self.LAMP_W + 8, 0, -2, 0),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._text)


class PushButtonWidget(OverlayWidget):
    """Generic pushbutton that opens a faceplate."""

    def __init__(self, element: Mapping[str, Any], parent: QWidget | None = None):
        super().__init__(element, parent)
        self._font = QFont()
        self._font.setFamilies(theme.UI_FONT_FAMILIES)
        self._font.setPixelSize(11)
        self._font.setBold(True)
        self._text = str(element.get("tag", ""))
        self.resize_to(int(element.get("w") or 80), int(element.get("h") or 20))
        self.setToolTip(f"{self._text} — click for faceplate")

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        rect = self.rect().adjusted(0, 0, -1, -1)
        p.fillRect(rect, QColor(theme.PANEL_BG))
        p.setPen(QColor(theme.PANEL_BORDER))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(rect)
        p.setFont(self._font)
        p.setPen(QColor(theme.TAB_TEXT))
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._text)


__all__ = [
    "NavHotspotWidget", "StreamHotspotWidget", "AnalyserWidget",
    "HandSwitchWidget", "OverrideButtonWidget", "PushButtonWidget",
]
