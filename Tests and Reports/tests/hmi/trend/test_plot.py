"""The trend plot — `ureasim.hmi.trend.plot`.

Pinned: the view shows the last span seconds to the right edge on a fixed -2 to 102 % axis; a pen is
drawn where it is told, thickened and on top when marked, faded when another is marked, and an
emptied pen holds no points; rulers are placed, re-used and removed to match the list given, and
placing them emits nothing while a drag reports the ruler's index and position; the clock and value
axes print what the window's callables return.
"""

from __future__ import annotations

import pytest

from ureasim.hmi import theme
from ureasim.hmi.trend.plot import Y_RANGE, TrendPlot


@pytest.fixture()
def plot(qapp):
    p = TrendPlot(lambda x: f"P{x:g}", lambda x: f"D{x:g}", lambda pct: f"V{pct:g}", 4)
    yield p
    p.close()


def test_the_span_and_the_value_axis(plot):
    plot.set_span(600)
    (x0, x1), (y0, y1) = plot.getPlotItem().getViewBox().viewRange()
    assert (x0, x1) == pytest.approx((-600.0, 0.0)) and (y0, y1) == pytest.approx(Y_RANGE)
    assert plot._plant_axis.tickStrings([-60.0], 1.0, 60.0) == ["P-60"]
    assert plot._desk_axis.tickStrings([-60.0], 1.0, 60.0) == ["D-60"]
    assert plot._value_axis.tickStrings([50.0], 1.0, 10.0) == ["V50"]


def test_pens_draw_mark_fade_and_clear(plot):
    plot.draw_pen(0, [-2.0, -1.0, 0.0], [10.0, 20.0, 30.0], "#ff0000", True, False)
    plot.draw_pen(1, [-1.0, 0.0], [5.0, 6.0], "#00ff00", False, True)
    xs, ys = plot._curves[0].getData()
    assert list(xs) == [-2.0, -1.0, 0.0] and list(ys) == [10.0, 20.0, 30.0]
    assert plot._curves[0].zValue() == 1 and plot._curves[1].zValue() == 0
    assert plot._curves[0].opts["pen"].widthF() == pytest.approx(theme.TREND_PEN_W_MARKED)
    assert plot._curves[1].opts["pen"].widthF() == pytest.approx(theme.TREND_PEN_W)
    assert plot._curves[1].opts["pen"].color().alpha() == theme.TREND_FADE_ALPHA
    plot.clear_pen(0)
    xs, _ = plot._curves[0].getData()
    assert xs is None or len(xs) == 0


def test_rulers_follow_the_list_and_only_a_drag_reports(plot):
    dragged = []
    plot.ruler_dragged.connect(lambda i, x: dragged.append((i, x)))
    plot.set_rulers([(-30.0, "R1", "#ffff00"), (-10.0, "R2", "#00ffff")])
    first = plot._rulers[0]
    assert [ln.value() for ln in plot._rulers] == [-30.0, -10.0] and dragged == []
    plot.set_rulers([(-20.0, "R1", "#ffff00")])
    assert plot._rulers == [first] and first.value() == -20.0 and dragged == []
    first.setValue(-25.0)                                   # the operator drags it
    assert dragged == [(0, -25.0)]
    plot.set_rulers([])
    assert plot._rulers == []
