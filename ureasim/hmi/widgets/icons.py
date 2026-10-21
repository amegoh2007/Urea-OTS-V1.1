"""Icon overlays: pumps and block valves.

These three share one problem — they are **rotated symbols on an anisotropically stretched
stage**, so they all go through `icon_geometry` to land back on the shape the slide
deleted. See that module for why the transform order matters.

    PumpWidget         26 elements. Green when running, grey when stopped.
    BlockValveWidget    6 elements. Bowtie: green open, red closed. Clickable where the
                        engine models the valve.

A modulating valve has no icon of its own (decided 2026-10-16, project.md decision 129): the
drawing carries its symbol, and its opening is an indicator's readout in per cent.

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

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtWidgets import QWidget

from ureasim.hmi import theme
from ureasim.hmi.state_access import get_path
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


__all__ = ["PumpWidget", "BlockValveWidget", "ICON_DIR"]
