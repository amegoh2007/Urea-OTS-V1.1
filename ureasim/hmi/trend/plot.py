"""The trend window's plot: ten pens on a per-cent grid, two clocks, and up to ten rulers.

Every pen is drawn on 0 - 100 % of its own range, so ten instruments in ten units share one
grid; the left axis reads in engineering units of the pen last marked, or in per cent. The time
axis runs from minus the span to the view's right edge: the plant clock above, the desktop clock
below. A click on empty plot drops a ruler; a ruler dragged slides along the time axis. The plot
draws what the window hands it and reports clicks, drags and drops — it holds no samples.

Source: V1 ``frontend/trend.js`` ``buildChart``, ``rulerPlugin``, ``redraw`` and the canvas's
pointer handlers.
"""

from __future__ import annotations

from typing import Callable

import pyqtgraph as pg
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from ureasim.hmi import theme

#: The y range [%]: a little either side of the grid so a pen at 0 or 100 stays visible.
Y_RANGE = (-2.0, 102.0)
#: A ruler is grabbed within this many pixels of its line (V1's ``RULER_HIT_PX``).
RULER_HIT_PX = 6
#: The drag-and-drop payload: a screen element's tag.
TAG_MIME = "application/x-ots-tag"


class _ClockAxis(pg.AxisItem):
    """A time axis that labels each tick through the window's clock (plant or desktop)."""

    def __init__(self, label: Callable[[float], str], **kwargs):
        super().__init__("bottom", **kwargs)
        self._label = label

    def tickStrings(self, values, scale, spacing):
        return [self._label(v) for v in values]


class _ValueAxis(pg.AxisItem):
    """The left axis: 0 - 100 % in steps of 20, read through the marked pen's range."""

    def __init__(self, label: Callable[[float], str], **kwargs):
        super().__init__("left", **kwargs)
        self._label = label
        self.setTickSpacing(major=20.0, minor=20.0)

    def tickStrings(self, values, scale, spacing):
        return [self._label(v) if -0.001 <= v <= 100.001 else "" for v in values]


class TrendPlot(pg.PlotWidget):
    """The plot area.

    Signals
    -------
    clicked(x)
        A click on empty plot, ``x`` seconds from the view's right edge (negative).
    ruler_dragged(index, x)
        A ruler slid to ``x`` seconds from the view's right edge.
    tag_dropped(tag)
        A screen element dropped on the plot: trend it in the first free pen.
    """

    clicked = pyqtSignal(float)
    ruler_dragged = pyqtSignal(int, float)
    tag_dropped = pyqtSignal(str)

    def __init__(self, plant_label: Callable[[float], str], desk_label: Callable[[float], str],
                 value_label: Callable[[float], str], slots: int, parent=None):
        self._plant_axis = _ClockAxis(plant_label)
        self._value_axis = _ValueAxis(value_label)
        super().__init__(parent, background=theme.TW_PLOT_BG,
                         axisItems={"bottom": self._plant_axis, "left": self._value_axis})
        item = self.getPlotItem()
        item.hideButtons()
        item.setMenuEnabled(False)
        item.setMouseEnabled(x=False, y=False)
        item.showGrid(x=True, y=True, alpha=0.5)
        # The desktop clock: a second time axis under the plant clock, on the same view.
        self._desk_axis = _ClockAxis(desk_label)
        self._desk_axis.linkToView(item.getViewBox())
        item.layout.addItem(self._desk_axis, 4, 1)
        for axis, colour in ((self._plant_axis, theme.TW_TICK), (self._desk_axis,
                             theme.TW_DESK_TICK), (self._value_axis, theme.TW_Y_TICK)):
            axis.setPen(pg.mkPen(theme.TW_GRID))
            axis.setTextPen(pg.mkPen(colour))
        self._plant_axis.setLabel("PLANT CLOCK", color=theme.TW_PLANT_TITLE)
        self._desk_axis.setLabel("DESKTOP CLOCK", color=theme.TW_DESK_TICK)
        item.setYRange(*Y_RANGE, padding=0.0)

        self._curves = [item.plot([], [], connect="finite") for _ in range(slots)]
        self._rulers: list[pg.InfiniteLine] = []
        self._placing = False
        self.scene().sigMouseClicked.connect(self._on_click)
        self.setAcceptDrops(True)

    # ---- drawing -------------------------------------------------------------------

    def set_span(self, span_s: float) -> None:
        """Show the last ``span_s`` seconds of the view."""
        self.getPlotItem().setXRange(-float(span_s), 0.0, padding=0.0)

    def draw_pen(self, slot: int, xs: list[float], ys: list[float], colour: str,
                 marked: bool, faded: bool) -> None:
        """Draw one pen: points at x seconds from the right edge, y per cent of its range."""
        c = QColor(colour)
        if faded:
            c.setAlpha(theme.TREND_FADE_ALPHA)
        curve = self._curves[slot]
        curve.setPen(pg.mkPen(c, width=theme.TREND_PEN_W_MARKED if marked else theme.TREND_PEN_W))
        curve.setZValue(1 if marked else 0)
        curve.setData(xs, ys)

    def clear_pen(self, slot: int) -> None:
        self._curves[slot].setData([], [])

    def set_rulers(self, rulers: list[tuple[float, str, str]]) -> None:
        """Place the rulers, each ``(x, label, colour)``, x seconds from the right edge."""
        self._placing = True
        while len(self._rulers) > len(rulers):
            self.removeItem(self._rulers.pop())
        while len(self._rulers) < len(rulers):
            index = len(self._rulers)
            line = pg.InfiniteLine(angle=90, movable=True, label="",
                                   labelOpts={"position": 0.97 - 0.06 * index,
                                              "anchors": [(0.5, 0), (0.5, 0)],
                                              "color": theme.TW_PLOT_BG})
            line.sigPositionChanged.connect(lambda ln, i=index: self._on_dragged(i, ln))
            self.addItem(line)
            self._rulers.append(line)
        for i, (x, label, colour) in enumerate(rulers):
            line = self._rulers[i]
            line.setPen(pg.mkPen(colour, width=1, style=Qt.PenStyle.DashLine))
            line.setHoverPen(pg.mkPen(colour, width=2))
            line.setValue(x)
            line.label.setFormat(label)
            line.label.fill = pg.mkBrush(colour)
            line.label.update()
        self._placing = False

    # ---- pointer -------------------------------------------------------------------

    def _on_dragged(self, index: int, line: pg.InfiniteLine) -> None:
        if not self._placing:
            self.ruler_dragged.emit(index, float(line.value()))

    def _on_click(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        box = self.getPlotItem().getViewBox()
        if not box.sceneBoundingRect().contains(event.scenePos()):
            return
        x = box.mapSceneToView(event.scenePos()).x()
        for line in self._rulers:
            px = box.mapViewToScene(pg.Point(line.value(), 0.0)).x()
            if abs(px - event.scenePos().x()) <= RULER_HIT_PX:
                return
        self.clicked.emit(float(x))

    # ---- drag and drop -------------------------------------------------------------

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat(TAG_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasFormat(TAG_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        if event.mimeData().hasFormat(TAG_MIME):
            self.tag_dropped.emit(bytes(event.mimeData().data(TAG_MIME)).decode("utf-8"))
            event.acceptProposedAction()


__all__ = ["TrendPlot", "TAG_MIME", "Y_RANGE", "RULER_HIT_PX"]
