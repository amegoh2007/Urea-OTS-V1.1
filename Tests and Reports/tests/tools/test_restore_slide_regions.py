"""The slide-revision tool — `tools/restore_slide_regions.py` — and page 328-2 as revised.

Pinned: a decided region is clipped at the edge of an element it meets, keeping the larger side, and
refused when an element lies inside it or splits it; a removed shape is found from the pixels the
background draws and the slide does not, never from a label the slide draws and the overlay owns;
328-2's background carries FT-322402's new leader to the ammonia-water line and no longer its old tick
(decision 221, the process engineer's instruction I-2 of 2026-11-13).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
import restore_slide_regions as rsr  # noqa: E402

SCREENS = Path(__file__).resolve().parents[3] / "ureasim" / "hmi" / "assets" / "screens"


def test_a_region_clear_of_every_element_is_kept_whole():
    assert rsr.clip((10, 10, 30, 20), [("a", (40, 0, 60, 30))]) == (10, 10, 30, 20)


def test_a_region_meeting_an_element_is_clipped_at_its_edge():
    """The element covers the region's left end: the right side is kept, from the element's edge."""
    assert rsr.clip((10, 10, 40, 20), [("a", (0, 0, 15, 30))]) == (15, 10, 40, 20)


def test_a_region_holding_or_split_by_an_element_is_refused():
    with pytest.raises(rsr.RegionRefused, match="inside"):
        rsr.clip((10, 10, 20, 20), [("a", (0, 0, 30, 30))])
    with pytest.raises(rsr.RegionRefused, match="keep only"):
        rsr.clip((0, 10, 100, 20), [("a", (40, 0, 60, 30))])


def test_the_margin_stays_on_the_stage():
    assert rsr.widen((0, 1, rsr.STAGE_W, 5), 2) == (0, 0, rsr.STAGE_W, 7)


def test_a_removed_shape_is_what_the_background_alone_draws():
    """A tick the background still draws is found; a label only the slide draws is not."""
    bg = np.zeros((40, 40, 3), np.uint8)
    slide = np.zeros((40, 40, 3), np.uint8)
    bg[20:30, 12] = 200          # the old tick, gone from the revised slide
    slide[5:9, 2:20] = 200       # a label the slide draws and the background leaves to its overlay
    assert rsr.removed_rect(bg, slide, (0, 0, 40, 40)) == (12, 20, 13, 30)
    with pytest.raises(rsr.RegionRefused):
        rsr.removed_rect(slide, slide, (0, 0, 40, 40))


def test_328_2_carries_the_revised_leader_and_not_the_old_tick():
    """The leader runs from FT-322402's label (x 200) to the ammonia-water line (x 221.8) on y 322;
    the old tick down the label's foot (x 165-166, y 334-350) is gone."""
    bg = np.asarray(Image.open(SCREENS / "screen-328-2.png").convert("RGB")).astype(int)
    lit = bg.max(axis=2) > 60
    assert lit[320:325, 201:221].any(axis=0).all()
    assert not lit[334:348, 163:169].any()


def test_every_decided_shape_is_clear_of_the_overlays():
    """A revised shape's rectangle, as the tool copied it, meets no element's real widget: a label the
    overlay draws is never printed a second time by the background. (A removed shape's rectangle is
    found on the unrevised background, which no longer holds it; the pixel test above pins it.)"""
    shapes = [row for row in rsr.DECIDED_REGIONS if row[2][0] == "shape"]
    for sid, what, (_kind, name) in shapes:
        deck = rsr.DEFAULT_SLIDES / f"{sid.removeprefix('screen-')}.pptx"
        if not deck.exists():
            pytest.skip("the UI-page decks are not on this machine")
        region = rsr.widen(rsr.shape_rect(deck, name), rsr.MARGIN)
        assert rsr.clip(region, rsr.element_rects(sid)) == region, what
