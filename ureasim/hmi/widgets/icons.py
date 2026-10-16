"""Icon overlays: pumps, block valves and modulating valves.

These three share one problem — they are **rotated symbols on an anisotropically stretched
stage**, so they all go through `icon_geometry` to land back on the shape the slide
deleted. See that module for why the transform order matters.

    PumpWidget         26 elements. Green when running, grey when stopped.
    BlockValveWidget    6 elements. Bowtie: green open, red closed. Clickable where the
                        engine models the valve.
    ActuatedValveWidget 47 elements. A modulating valve — the symbol plus its stem
                        position as a percentage, because a control valve's *opening* is
                        what the operator is actually watching.

Commandability
--------------
A pump or valve icon is only clickable when the engine models that machine. The rest render
their default state and are inert. That is honest: a symbol that accepts a click and does
nothing teaches a trainee that the command failed silently, which is worse than a symbol
that visibly is not a control.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import QWidget

from ureasim.hmi import theme
from ureasim.hmi.state_access import format_value, get_path
from ureasim.hmi.widgets.base import OverlayWidget
from ureasim.hmi.widgets.icon_geometry import icon_geometry

#: Icon artwork, carried over from V1 so the symbols are the ones operators know.
ICON_DIR = Path(__file__).resolve().parents[1] / "assets" / "icons"

#: Default icon boxes from V1's stylesheet, used when the drawing gave no extent.
PUMP_DEFAULT = (54.0, 54.0)
VALVE_DEFAULT = (34.0, 34.0)

_PIXMAP_CACHE: dict[str, QPixmap] = {}


def _pixmap(name: str) -> QPixmap:
    """Load and cache an icon. Cached because 26 pumps share two images."""
    if name not in _PIXMAP_CACHE:
        _PIXMAP_CACHE[name] = QPixmap(str(ICON_DIR / name))
    return _PIXMAP_CACHE[name]


class _IconOverlay(OverlayWidget):
    """Shared painting for a rotated, mirrored, un-squashed symbol."""

    def __init__(self, element: Mapping[str, Any], default_box: tuple[float, float],
                 parent: QWidget | None = None):
        super().__init__(element, parent)
        w = float(element.get("w") or default_box[0])
        h = float(element.get("h") or default_box[1])
        self._geom = icon_geometry(
            w, h,
            rot=float(element.get("rot") or 0.0),
            flip_x=bool(element.get("fx")),
            flip_y=bool(element.get("fy")),
        )
        # The widget box is the UN-STRETCHED rectangle, so centring the widget centres the
        # symbol. The stretch is applied by the painter, about the widget's own centre.
        self.resize_to(int(round(self._geom.width)), int(round(self._geom.height)))
        self._state = True

    def _paint_pixmap(self, p: QPainter, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            return
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        cx, cy = self.width() / 2.0, self.height() / 2.0
        p.translate(cx, cy)
        p.setTransform(self._geom.transform, True)
        p.drawPixmap(
            QRectF(-self._geom.width / 2.0, -self._geom.height / 2.0,
                   self._geom.width, self._geom.height).toRect(),
            pixmap,
        )
        p.resetTransform()

    def _paint_edit_outline(self, p: QPainter) -> None:
        if self.editing:
            p.setPen(QColor(theme.EDIT_OUTLINE))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(self.rect().adjusted(0, 0, -1, -1))


class PumpWidget(_IconOverlay):
    """Pump symbol — green running, grey stopped.

    The bound path is the pump *object* (``'pumpA'``), and the running state is its ``on``
    field. Binding to the object rather than the boolean is what lets a left-click open the
    machine's own faceplate with its speed, current and mode.
    """

    def __init__(self, element: Mapping[str, Any], parent: QWidget | None = None):
        super().__init__(element, PUMP_DEFAULT, parent)
        # An icon the engine does not model shows its drawn default: A duty running,
        # B standby stopped, unless the drawing says otherwise.
        self._state = element.get("def", True) is not False
        self.setToolTip(f"{element.get('tag', '')}")

    def update_from(self, snapshot: Mapping[str, Any] | None) -> None:
        bind = self.element.get("bind")
        if bind:
            node = get_path(snapshot, bind)
            on = bool(node.get("on")) if isinstance(node, Mapping) else bool(node)
        else:
            on = self.element.get("def", True) is not False
        if on != self._state:
            self._state = on
            self.update()
        self.setToolTip(
            f"{self.element.get('tag', '')} — {'ON' if on else 'OFF'}"
            + (" (click for START/STOP faceplate)" if bind else " (not modelled)")
        )

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        self._paint_pixmap(p, _pixmap("pump-on.png" if self._state else "pump-off.png"))
        self._paint_edit_outline(p)


class BlockValveWidget(_IconOverlay):
    """On-off block valve (XV) — bowtie symbol, open or closed.

    Process utility: these are the valves an interlock slams. XV-321901 and XV-322901 are
    the NH3 feed isolations that TRIP_21_x close, so their state is the first thing an
    operator looks at after a trip.
    """

    def __init__(self, element: Mapping[str, Any], parent: QWidget | None = None):
        super().__init__(element, VALVE_DEFAULT, parent)
        self._state = element.get("def", True) is not False

    def update_from(self, snapshot: Mapping[str, Any] | None) -> None:
        bind = self.element.get("bind")
        open_ = bool(get_path(snapshot, bind)) if bind else self._state
        if open_ != self._state:
            self._state = open_
            self.update()
        self.setToolTip(
            f"{self.element.get('tag', '')} — {'OPEN' if open_ else 'CLOSED'}")

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        self._paint_pixmap(p, _pixmap("xv-open.png" if self._state else "xv-close.png"))
        self._paint_edit_outline(p)


class ActuatedValveWidget(OverlayWidget):
    """Modulating control valve — the symbol with its stem position beneath it.

    Process utility
    ---------------
    A control valve's *opening* is the operator's window into the controller: a loop
    sitting at 5 % or 95 % is saturated and has no authority left, whichever way its PV
    reads. That is why the opening is drawn as a number under the symbol rather than only
    as a stem position.
    """

    #: Box for the symbol plus the readout beneath it.
    BODY_H = 20
    READOUT_H = 14

    def __init__(self, element: Mapping[str, Any], parent: QWidget | None = None):
        super().__init__(element, parent)
        self._opening: float | None = None
        w = int(element.get("w") or VALVE_DEFAULT[0])
        self.resize_to(max(34, w), self.BODY_H + self.READOUT_H)
        self._font = QFont()
        self._font.setFamilies(theme.VALUE_FONT_FAMILIES)
        self._font.setPixelSize(theme.UNIT_FONT_PX)

    def update_from(self, snapshot: Mapping[str, Any] | None) -> None:
        raw = get_path(snapshot, self.element.get("bind"))
        opening = None
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            opening = float(raw)
        elif isinstance(raw, Mapping):
            # A valve bound to its controller object reads the controller output.
            op = raw.get("op")
            if isinstance(op, (int, float)):
                opening = float(op)
        if opening != self._opening:
            self._opening = opening
            self.update()
        self.setToolTip(
            f"{self.element.get('tag', '')} — "
            + (format_value(opening, 1) + " % open" if opening is not None else "no data")
        )

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w = self.width()
        body = QRectF(0, 0, w, self.BODY_H)

        # Bowtie body: two triangles meeting at the stem. Filled proportionally to the
        # opening, so the symbol itself shows how far the valve is off its seat.
        frac = 0.0 if self._opening is None else max(0.0, min(1.0, self._opening / 100.0))
        seat = QColor(theme.BTN_GREEN)
        seat.setAlphaF(0.25 + 0.75 * frac)

        p.setPen(QColor(theme.PI_BORDER))
        p.setBrush(seat)
        mid_x, mid_y = body.center().x(), body.center().y()
        p.drawPolygon(QPointF(body.left(), body.top()),
                      QPointF(body.left(), body.bottom()),
                      QPointF(mid_x, mid_y))
        p.drawPolygon(QPointF(body.right(), body.top()),
                      QPointF(body.right(), body.bottom()),
                      QPointF(mid_x, mid_y))

        # Opening readout: black field, white frame, like every other DCS number.
        read = QRectF(0, self.BODY_H, w, self.READOUT_H)
        p.setPen(QColor(theme.PI_BORDER))
        p.setBrush(QColor(theme.PI_BG))
        p.drawRect(read)
        p.setFont(self._font)
        p.setPen(QColor(theme.PI_TEXT))
        p.drawText(read, Qt.AlignmentFlag.AlignCenter,
                   format_value(self._opening, 1) if self._opening is not None else "--")

        if self.editing:
            p.setPen(QColor(theme.EDIT_OUTLINE))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(self.rect().adjusted(0, 0, -1, -1))


__all__ = ["PumpWidget", "BlockValveWidget", "ActuatedValveWidget", "ICON_DIR"]
