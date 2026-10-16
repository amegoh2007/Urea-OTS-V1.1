"""One process screen: the drawing, and the live elements that sit in its holes.

The image-backed principle
--------------------------
The background is a PowerPoint equipment drawing exported at stage resolution with the
live symbols **deleted**. Vessels, lines, valve bodies and equipment labels are painted
once and never redrawn in code. Every element that must show live data is an overlay
positioned at the deleted shape's own centre, sized from its own extent, rotated and
mirrored by its own transform.

So an overlay cannot drift off its symbol: it lands in the hole the symbol left.

Two layers, and why
-------------------
    Stage       a plain QWidget fixed at 1366 x 720. It owns the background pixmap and
                every overlay child. All overlay coordinates are stage pixels, exactly as
                `ureasim.data.screen_layout` records them.
    ScreenView  a QGraphicsView holding that stage through a proxy, scaled uniformly with
                `fitInView`.

Scaling this way — one transform on the whole stage — means the drawing and its overlays
scale **together**, so alignment is preserved at any window size. Scaling each overlay
individually would accumulate rounding and walk the symbols off their holes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from PyQt6.QtCore import QPoint, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsView, QWidget

from ureasim.data.screen_layout import STAGE_H, STAGE_W
from ureasim.hmi import theme
from ureasim.hmi.state_access import BindMap
from ureasim.hmi.widgets import OverlayWidget, build_widget

#: Background renders, carried over from V1 so the drawings are the ones operators know.
SCREEN_DIR = Path(__file__).resolve().parent / "assets" / "screens"


class Stage(QWidget):
    """The fixed 1366 x 720 coordinate frame: background pixmap plus overlay children."""

    def __init__(self, screen_id: str, elements: Iterable[Mapping[str, Any]],
                 bind_map: BindMap, parent: QWidget | None = None):
        super().__init__(parent)
        self.screen_id = screen_id
        self.setFixedSize(STAGE_W, STAGE_H)

        self._background = QPixmap(str(SCREEN_DIR / f"{screen_id}.png"))
        self._overlays: list[OverlayWidget] = []

        for element in elements:
            # Resolve a shared tag to its bound occurrence BEFORE the widget is built, so
            # an unbound box on this screen renders a live value rather than an empty slot
            # when another screen binds the same instrument.
            self._overlays.append(build_widget(bind_map.effective(element), self))

    @property
    def overlays(self) -> list[OverlayWidget]:
        return self._overlays

    def update_from(self, snapshot: Mapping[str, Any] | None) -> None:
        """Push one engine snapshot through every overlay on this screen."""
        for widget in self._overlays:
            widget.update_from(snapshot)

    def set_editing(self, editing: bool) -> None:
        for widget in self._overlays:
            widget.set_editing(editing)

    def connect_overlays(self,
                         on_activate: Callable[[Mapping[str, Any]], None],
                         on_context: Callable[[Mapping[str, Any], QPoint], None],
                         on_moved: Callable[[Mapping[str, Any], float, float], None],
                         on_drag: Callable[[Mapping[str, Any]], None] | None = None
                         ) -> None:
        """Wire every overlay's signals to the screen's handlers."""
        for widget in self._overlays:
            widget.activated.connect(on_activate)
            widget.context_requested.connect(on_context)
            widget.moved.connect(on_moved)
            if on_drag is not None:
                widget.drag_requested.connect(on_drag)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        if self._background.isNull():
            # No render for this screen: paint the stage colour so overlays stay readable,
            # rather than a black rectangle that looks like a crash.
            p.fillRect(self.rect(), QColor(theme.BG))
            return
        p.drawPixmap(self.rect(), self._background)


class ScreenView(QGraphicsView):
    """A `Stage` scaled uniformly to fit the window.

    Signals
    -------
    navigate(screen_id)
        A nav hotspot was clicked.
    element_activated(element)
        Any other overlay was left-clicked; the main window routes it.
    element_context(element, global_pos)
        An overlay was right-clicked.
    element_moved(screen_id, key, x, y)
        An overlay was dragged in edit-layout mode.
    element_dragged(element)
        An overlay was dragged in run mode, toward the trend window.
    """

    navigate = pyqtSignal(str)
    element_activated = pyqtSignal(object)
    element_context = pyqtSignal(object, QPoint)
    element_moved = pyqtSignal(str, str, float, float)
    element_dragged = pyqtSignal(object)

    def __init__(self, screen_id: str, elements: Iterable[Mapping[str, Any]],
                 bind_map: BindMap, parent: QWidget | None = None):
        super().__init__(parent)
        self.screen_id = screen_id

        self.stage = Stage(screen_id, elements, bind_map)
        self.stage.connect_overlays(self._on_activate, self._on_context, self._on_moved,
                                    self.element_dragged.emit)

        scene = QGraphicsScene(self)
        scene.setSceneRect(QRectF(0, 0, STAGE_W, STAGE_H))
        self._proxy = scene.addWidget(self.stage)
        self._proxy.setPos(0, 0)
        self.setScene(scene)

        self.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform
                            | QPainter.RenderHint.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setBackgroundBrush(QColor(theme.PAGE_BG))
        self.setMinimumSize(683, 360)          # half the stage; below that labels are lost

    # ----------------------------------------------------------------------------------

    def update_from(self, snapshot: Mapping[str, Any] | None) -> None:
        self.stage.update_from(snapshot)

    def set_editing(self, editing: bool) -> None:
        self.stage.set_editing(editing)

    # ----------------------------------------------------------------------------------

    def _on_activate(self, element: Mapping[str, Any]) -> None:
        if element.get("t") == "nav" and element.get("goto"):
            self.navigate.emit(str(element["goto"]))
            return
        self.element_activated.emit(element)

    def _on_context(self, element: Mapping[str, Any], pos: QPoint) -> None:
        self.element_context.emit(element, pos)

    def _on_moved(self, element: Mapping[str, Any], x: float, y: float) -> None:
        """Report a dragged position.

        The main window persists it to `QSettings` per screen and element key, so an
        operator's layout survives a restart. Layout is per machine and is never written
        back into `screen_layout.py` — that file belongs to the drawing.
        """
        self.element_moved.emit(self.screen_id, str(element.get("k", "")), x, y)

    # ----------------------------------------------------------------------------------

    def resizeEvent(self, event) -> None:
        """Fit the whole stage, preserving aspect ratio."""
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        super().resizeEvent(event)


__all__ = ["Stage", "ScreenView", "SCREEN_DIR"]
