"""Base class for every overlay element.

Positioning contract
--------------------
`ureasim.data.screen_layout` records each element's **centre**, because that is the centre
of the shape the slide deleted. Qt lays widgets out from their top-left, so every overlay
converts once, here:

    top-left = centre - size/2

Nothing else in the HMI may set an overlay's position. When V1 got this wrong — keeping a
fixed default box size while the image inside carried the real size — every icon sat half
the size difference off its symbol.

Interaction contract
--------------------
An overlay emits; it never acts. Left-click, right-click and drag are reported upward as
signals and the screen decides what they mean. A widget that sent a command directly would
put plant control inside the presentation layer.

A click is a press and a release without a drag, as V1's browser click was: a press that moves
past the platform's drag distance is a drag to the trend window, and opens no faceplate.
"""

from __future__ import annotations

from typing import Any, Mapping

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtWidgets import QApplication, QWidget


class OverlayWidget(QWidget):
    """One live element on a process screen.

    Signals
    -------
    activated(element)
        Left-click in run mode. The screen routes it to a faceplate, a valve command, a
        screen jump or a popup, according to the element's type and fields.
    context_requested(element, global_pos)
        Right-click. The screen opens the element menu (trend, properties, edit).
    moved(element, x, y)
        Dragged to a new centre in edit-layout mode.
    drag_requested(element)
        Dragged in run mode: the console starts a drag of the element's tag to the trend.
    command_requested(command)
        A button drawn on the element itself was pressed in run mode (322-1's CO2 FEED panel,
        decision 220): the engine command the element names, which the console sends as it is.
    """

    activated = pyqtSignal(object)
    context_requested = pyqtSignal(object, QPoint)
    moved = pyqtSignal(object, float, float)
    drag_requested = pyqtSignal(object)
    command_requested = pyqtSignal(object)

    def __init__(self, element: Mapping[str, Any], parent: QWidget | None = None):
        super().__init__(parent)
        self.element = dict(element)
        self._centre = (float(element["x"]), float(element["y"]))
        self._editing = False
        self._drag_origin: QPoint | None = None
        self._press_origin: QPoint | None = None

        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    # ----------------------------------------------------------------------------------
    # Geometry
    # ----------------------------------------------------------------------------------

    @property
    def centre(self) -> tuple[float, float]:
        """Element centre on the stage [px]."""
        return self._centre

    def set_centre(self, x: float, y: float) -> None:
        """Move the element so its CENTRE lands at ``(x, y)``."""
        self._centre = (x, y)
        self._apply_centre()

    def resize_to(self, w: int, h: int) -> None:
        """Resize and re-centre in one step.

        Resizing alone would move the element, because Qt grows a widget from its top-left
        and the layout table addresses it by its centre.
        """
        self.resize(max(1, int(round(w))), max(1, int(round(h))))
        self._apply_centre()

    def _apply_centre(self) -> None:
        x, y = self._centre
        self.move(int(round(x - self.width() / 2.0)),
                  int(round(y - self.height() / 2.0)))

    # ----------------------------------------------------------------------------------
    # Live update — subclasses override
    # ----------------------------------------------------------------------------------

    def update_from(self, snapshot: Mapping[str, Any] | None) -> None:
        """Refresh this element from an engine snapshot. Overridden by every subclass."""

    # ----------------------------------------------------------------------------------
    # Edit-layout mode
    # ----------------------------------------------------------------------------------

    def set_editing(self, editing: bool) -> None:
        """Enter or leave edit-layout mode (drag to reposition)."""
        self._editing = editing
        self.setCursor(Qt.CursorShape.SizeAllCursor if editing
                       else Qt.CursorShape.PointingHandCursor)
        self.update()

    @property
    def editing(self) -> bool:
        return self._editing

    # ----------------------------------------------------------------------------------
    # Mouse
    # ----------------------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self._editing:
                self._drag_origin = event.pos()
            else:
                self._press_origin = event.pos()
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            self.context_requested.emit(self.element, event.globalPosition().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._editing and self._drag_origin is not None:
            delta = event.pos() - self._drag_origin
            x, y = self._centre
            self.set_centre(x + delta.x(), y + delta.y())
            event.accept()
            return
        if (self._press_origin is not None
                and event.buttons() & Qt.MouseButton.LeftButton
                and (event.pos() - self._press_origin).manhattanLength()
                >= QApplication.startDragDistance()):
            self._press_origin = None
            self.drag_requested.emit(self.element)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._editing and self._drag_origin is not None:
            self._drag_origin = None
            self.moved.emit(self.element, *self._centre)
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton and self._press_origin is not None:
            self._press_origin = None
            self.activated.emit(self.element)
            event.accept()
            return
        super().mouseReleaseEvent(event)


__all__ = ["OverlayWidget"]
