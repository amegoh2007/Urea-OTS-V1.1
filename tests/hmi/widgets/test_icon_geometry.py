"""The icon overlay geometry — `ureasim.hmi.widgets.icon_geometry`.

Pinned: the widget box is the symbol's un-stretched size (the drawing's width divided by the
stage's squash), the transform restores the stretch, so an unrotated icon's bounding box is the
drawing's own box; mirroring changes nothing in the bounding box; a quarter turn swaps the
un-stretched sides before the stretch is applied.
"""

from __future__ import annotations

import pytest

from ureasim.hmi.widgets.icon_geometry import SLIDE_RX, bounding_size, icon_geometry


def test_the_box_is_unstretched_and_the_transform_restores_it():
    g = icon_geometry(54.0, 40.0)
    assert (g.width, g.height) == pytest.approx((54.0 / SLIDE_RX, 40.0))
    assert bounding_size(g) == pytest.approx((54.0, 40.0))


@pytest.mark.parametrize("fx, fy", [(True, False), (False, True), (True, True)])
def test_mirroring_keeps_the_bounding_box(fx, fy):
    assert bounding_size(icon_geometry(54.0, 40.0, flip_x=fx, flip_y=fy)) == pytest.approx(
        (54.0, 40.0))


def test_a_quarter_turn_swaps_the_unstretched_sides():
    g = icon_geometry(54.0, 40.0, rot=90.0)
    assert bounding_size(g) == pytest.approx((40.0 * SLIDE_RX, 54.0 / SLIDE_RX), abs=1e-9)
