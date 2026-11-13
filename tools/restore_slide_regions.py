"""Copy decided regions of a slide's render into its screen background — a slide revised after migration.

Why this tool exists
--------------------
Each background is its UI-page slide rendered with the live symbols deleted, the overlay layer drawing
them again in their holes. When the process engineer revises a slide's drawing after the migration —
a leader moved, a tick removed — the background must take the revision and nothing else: every
overlay still lands in its hole, and no label the overlay draws is printed a second time by the
background.

What it does
------------
For every row of `DECIDED_REGIONS` it takes a rectangle of the slide's render and copies it into the
committed background. The rectangle is never typed by hand: it is a named shape's own extent in the
revised slide, or — for a shape the revision removed, which has no extent left — the bounding box of
the pixels in which the background differs from the render inside the window the comparison found,
each widened by `MARGIN` for the line's antialiasing.

The keep-out is each overlay widget's real geometry on a built screen (`ureasim.hmi.screen_view.Stage`,
Qt on the native platform, so an indicator is measured in its own font). A rectangle that meets an
element is clipped at that element's edge: the side kept is the one that keeps the most of the
rectangle. A rectangle the clip would empty, or cut to less than half (an element inside it, or one
that splits it), is refused: the revision must then be decided again, not copied over a readout.

Usage
-----
    powershell -ExecutionPolicy Bypass -File tools/export_slides.ps1 <renders>
    python tools/restore_slide_regions.py <renders> [--screens <dir>] [--slides <dir>] [--check]

``--check`` reports what would change and writes nothing.
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ureasim.data.screen_layout import OVERLAYS, SLIDE_EMU_H, SLIDE_EMU_W, STAGE_H, STAGE_W  # noqa: E402

DEFAULT_SCREENS = Path(__file__).resolve().parents[1] / "ureasim" / "hmi" / "assets" / "screens"
DEFAULT_SLIDES = Path(r"D:\Work\Urea Simulation Docs\Equipment Drawing\UI Pages")

#: A pixel differs when any channel differs by more than this (0-255), as `restore_nav_blocks`.
PIXEL_THRESHOLD = 60
#: Margin [px] around a shape's extent or a removed shape's pixels, for the line's antialiasing.
MARGIN = 2
#: A clipped rectangle must keep at least this fraction of its area, or it is refused.
MIN_KEPT_FRACTION = 0.5

#: The process engineer's decided slide revisions: (screen, what it is, how its rectangle is found).
#: ``("shape", name)`` is a shape's extent in the revised slide; ``("removed", (x0, y0, x1, y1))`` is
#: the window in which the background still draws a shape the revision deleted.
DECIDED_REGIONS = (
    # Decided 2026-11-13 (decision 221, the process engineer's instruction I-2 of that day): slide 328-2
    # was revised after the migration. FT-322402's label now leads right, by a horizontal leader, to
    # the ammonia-water line at x 221.8, and the old vertical tick down to the line from 322E003 is
    # gone (As-Built §CXVI.1). The label itself is the overlay's to draw.
    ("screen-328-2", "FT-322402's new leader", ("shape", "Straight Connector 191")),
    # The window is the region session 106's comparison reported (x 160-168, y 336-352), widened by
    # the 6 px it masked around every element.
    ("screen-328-2", "FT-322402's removed tick", ("removed", (154, 330, 174, 358))),
)

_NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main",
       "p": "http://schemas.openxmlformats.org/presentationml/2006/main"}

Rect = tuple[int, int, int, int]


class RegionRefused(RuntimeError):
    """A decided region cannot be copied without printing over an overlay element."""


def shape_rect(deck: Path, name: str) -> Rect:
    """A named shape's extent on the stage (x0, y0, x1, y1), the slide's anisotropic mapping."""
    with zipfile.ZipFile(deck) as z:
        root = ET.fromstring(z.read("ppt/slides/slide1.xml"))
    for shape in root.iter():
        nv = shape.find("./*/p:cNvPr", _NS)
        if nv is None or nv.get("name") != name or shape.find("p:spPr/a:xfrm", _NS) is None:
            continue
        off = shape.find("p:spPr/a:xfrm/a:off", _NS)
        ext = shape.find("p:spPr/a:xfrm/a:ext", _NS)
        sx, sy = STAGE_W / SLIDE_EMU_W, STAGE_H / SLIDE_EMU_H
        x, y, w, h = (int(off.get("x")), int(off.get("y")), int(ext.get("cx")), int(ext.get("cy")))
        return (int(np.floor(x * sx)), int(np.floor(y * sy)),
                int(np.ceil((x + w) * sx)), int(np.ceil((y + h) * sy)))
    raise RegionRefused(f"{deck.name}: no shape named {name!r}")


def removed_rect(bg: np.ndarray, slide: np.ndarray, window: Rect) -> Rect:
    """The bounding box of the pixels the background draws and the revised slide does not, inside
    the window."""
    x0, y0, x1, y1 = window
    # Lit in the background and not in the slide: a label the slide draws and the background
    # leaves to its overlay differs the other way and is not taken.
    drawn = (bg[y0:y1, x0:x1].astype(int) - slide[y0:y1, x0:x1].astype(int)).max(axis=2)
    ys, xs = np.nonzero(drawn > PIXEL_THRESHOLD)
    if not len(xs):
        raise RegionRefused(f"nothing differs inside {window}: the removed shape is not there")
    return (x0 + int(xs.min()), y0 + int(ys.min()), x0 + int(xs.max()) + 1, y0 + int(ys.max()) + 1)


def widen(r: Rect, margin: int) -> Rect:
    return (max(r[0] - margin, 0), max(r[1] - margin, 0),
            min(r[2] + margin, STAGE_W), min(r[3] + margin, STAGE_H))


def _area(r: Rect) -> int:
    return max(r[2] - r[0], 0) * max(r[3] - r[1], 0)


def _meets(a: Rect, b: Rect) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def clip(region: Rect, keep_out: list[tuple[str, Rect]]) -> Rect:
    """The region clipped at the edge of every element it meets, keeping the larger side each time;
    refused when the clip leaves less than `MIN_KEPT_FRACTION` of it."""
    r = region
    for key, e in keep_out:
        if not _meets(r, e):
            continue
        sides = [(r[0], r[1], e[0], r[3]), (e[2], r[1], r[2], r[3]),
                 (r[0], r[1], r[2], e[1]), (r[0], e[3], r[2], r[3])]
        best = max(sides, key=_area)
        if _area(best) == 0:
            raise RegionRefused(f"{region} lies inside element {key!r}")
        r = best
    if _area(r) < MIN_KEPT_FRACTION * _area(region):
        raise RegionRefused(f"{region} would keep only {r} clear of the elements")
    return r


def element_rects(sid: str) -> list[tuple[str, Rect]]:
    """Each overlay element's real widget rectangle on the built screen."""
    from PyQt6.QtWidgets import QApplication

    from ureasim.hmi.screen_view import Stage
    from ureasim.hmi.state_access import BindMap

    _app = QApplication.instance() or QApplication([])
    stage = Stage(sid, OVERLAYS[sid], BindMap(OVERLAYS))
    out = []
    for w in stage.overlays:
        g = w.geometry()
        out.append((str(w.element.get("k")), (g.x(), g.y(), g.x() + g.width(), g.y() + g.height())))
    return out


def restore(renders: Path, screens: Path, slides: Path, check: bool) -> int:
    """Copy every decided region; return how many were copied."""
    done = 0
    for sid in dict.fromkeys(sid for sid, _what, _how in DECIDED_REGIONS):
        page = re.sub(r"^screen-", "", sid)
        bg_path = screens / f"{sid}.png"
        bg = np.asarray(Image.open(bg_path).convert("RGB")).copy()
        slide = np.asarray(Image.open(renders / f"{page}.png").convert("RGB"))
        if slide.shape != bg.shape:
            raise SystemExit(f"{page}.png: {slide.shape} is not the stage {bg.shape}")
        keep_out = element_rects(sid)
        rects = []
        for row_sid, what, (kind, arg) in DECIDED_REGIONS:
            if row_sid != sid:
                continue
            found = (shape_rect(slides / f"{page}.pptx", arg) if kind == "shape"
                     else removed_rect(bg, slide, arg))
            region = clip(widen(found, MARGIN), keep_out)
            rects.append((what, found, region))
        for what, found, (x0, y0, x1, y1) in rects:
            bg[y0:y1, x0:x1] = slide[y0:y1, x0:x1]
            print(f"{sid}: {what}: found {found}, copied x {x0}-{x1} y {y0}-{y1}")
            done += 1
        if not check:
            Image.fromarray(bg).save(bg_path)
    return done


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("renders", type=Path, help="the slide renders from export_slides.ps1")
    ap.add_argument("--screens", type=Path, default=DEFAULT_SCREENS)
    ap.add_argument("--slides", type=Path, default=DEFAULT_SLIDES)
    ap.add_argument("--check", action="store_true", help="report only; write nothing")
    args = ap.parse_args(argv)
    n = restore(args.renders, args.screens, args.slides, args.check)
    print(f"{n} region(s) {'would be ' if args.check else ''}copied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
