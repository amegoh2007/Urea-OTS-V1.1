"""The level bargraph — `ureasim.hmi.widgets.bargraph`.

Pinned: the bar shows the published level clamped to 0-100 % (a bar cannot overfill or go
negative), a missing, boolean or NaN value shows "no data" and an empty outline, the drawing's box
is used and V1's 12 x 60 is the fallback, and the fill grows from the bottom as a liquid does.
"""

from __future__ import annotations

import pytest
from PyQt6.QtGui import QColor

from ureasim.hmi import theme
from ureasim.hmi.widgets.bargraph import DEFAULT_H, DEFAULT_W, BargraphWidget


@pytest.fixture()
def bar(qapp):
    w = BargraphWidget({"x": 100, "y": 100, "tag": "LI-1", "bind": "X.level", "w": 20, "h": 100})
    yield w
    w.close()


@pytest.mark.parametrize("raw, level, tip", [
    (42.25, 42.25, "LI-1 - 42.2 %"), (130.0, 100.0, "LI-1 - 100.0 %"),
    (-5.0, 0.0, "LI-1 - 0.0 %"), (True, None, "LI-1 - no data"),
    (float("nan"), None, "LI-1 - no data"), (None, None, "LI-1 - no data")])
def test_the_level_is_clamped_and_bad_data_shows_none(bar, raw, level, tip):
    bar.update_from({"X": {"level": raw}})
    assert bar._level == level and bar.toolTip() == tip


def test_the_box_and_its_fallback(qapp):
    w = BargraphWidget({"x": 100, "y": 100, "tag": "LI-2", "bind": "X.level"})
    assert (w.width(), w.height()) == (DEFAULT_W, DEFAULT_H)
    w.close()


def test_the_fill_grows_from_the_bottom(bar):
    bar.update_from({"X": {"level": 50.0}})
    img = bar.grab().toImage()
    x = img.width() // 2
    assert img.pixelColor(x, img.height() - 5) == QColor(theme.BAR_FILL)
    assert img.pixelColor(x, 5) == QColor(theme.BAR_BG)
