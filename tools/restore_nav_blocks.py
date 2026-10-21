"""Put back into the screen backgrounds the destination blocks V1's migration stripped from them.

Why this tool exists
--------------------
Each background is its UI-page slide rendered with the live symbols deleted, the overlay layer
drawing them again in their holes. On the seven pages V1 migrated in September 2026 (323-1,
323-2, 324-1, 324-1b, 328-1, 328-2, 329-1) its strip list also took out the drawn destination
blocks — "322E002", "328C003" and the like — because each carries a nav hotspot. The hotspot is
transparent by design ("the drawing already labels the destination"), so on those pages the
blocks were simply gone: 52 page buttons with nothing drawn. The three pages migrated earlier
(321-1, 322-1, 322-2) kept theirs. Decided 2026-10-16 (project.md decision 129): the pages are
revised from their slides, and the blocks come back.

What it does
------------
For every nav element in `ureasim.data.screen_layout`, it compares the background with the
slide's render inside the element's rectangle. Where most of the rectangle differs (a block the
background lacks; an antialiasing difference is a few per cent), it copies the slide's pixels of
that rectangle, widened by a small margin for the block's frame, into the background. Nothing
else in a background changes, so every overlay still lands in its hole.

Usage
-----
    powershell -ExecutionPolicy Bypass -File tools/export_slides.ps1 <renders>
    python tools/restore_nav_blocks.py <renders> [--screens <dir>] [--check]

``--check`` reports what would change and writes nothing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ureasim.data.screen_layout import OVERLAYS  # noqa: E402

DEFAULT_SCREENS = Path(__file__).resolve().parents[1] / "ureasim" / "hmi" / "assets" / "screens"

#: A pixel differs when any channel differs by more than this (0-255).
PIXEL_THRESHOLD = 60
#: A block is missing when more than this fraction of its rectangle differs. Present blocks
#: differ by 2-14 % (antialiasing); stripped ones by 83-92 %.
MISSING_FRACTION = 0.5
#: Margin [px] around the hotspot's rectangle taken with the block, for its frame.
MARGIN = 4


def nav_rect(el: dict) -> tuple[int, int, int, int]:
    """The hotspot's rectangle (x0, y0, x1, y1) in stage pixels: centre - size / 2."""
    w, h = float(el.get("w") or 100), float(el.get("h") or 24)
    x0, y0 = int(round(el["x"] - w / 2)), int(round(el["y"] - h / 2))
    return x0, y0, x0 + int(round(w)), y0 + int(round(h))


def restore(renders: Path, screens: Path, check: bool) -> int:
    """Restore the missing blocks on every screen; return how many were restored."""
    total = 0
    for sid, elements in OVERLAYS.items():
        page = sid.removeprefix("screen-")
        render_path = renders / f"{page}.png"
        bg_path = screens / f"{sid}.png"
        bg = np.asarray(Image.open(bg_path).convert("RGB")).copy()
        slide = np.asarray(Image.open(render_path).convert("RGB"))
        if slide.shape != bg.shape:
            raise SystemExit(f"{render_path}: {slide.shape} is not the stage {bg.shape}")
        diff = np.abs(bg.astype(int) - slide.astype(int)).max(axis=2) > PIXEL_THRESHOLD
        hgt, wid = diff.shape
        restored = []
        for el in elements:
            if el["t"] != "nav":
                continue
            x0, y0, x1, y1 = nav_rect(el)
            if diff[max(y0, 0):y1, max(x0, 0):x1].mean() <= MISSING_FRACTION:
                continue
            xa, ya = max(x0 - MARGIN, 0), max(y0 - MARGIN, 0)
            xb, yb = min(x1 + MARGIN, wid), min(y1 + MARGIN, hgt)
            bg[ya:yb, xa:xb] = slide[ya:yb, xa:xb]
            restored.append(el["k"])
        if restored:
            total += len(restored)
            print(f"{sid}: {len(restored)} block(s) restored: {', '.join(restored)}")
            if not check:
                Image.fromarray(bg).save(bg_path)
    return total


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("renders", type=Path, help="the slide renders from export_slides.ps1")
    ap.add_argument("--screens", type=Path, default=DEFAULT_SCREENS)
    ap.add_argument("--check", action="store_true", help="report only; write nothing")
    args = ap.parse_args(argv)
    n = restore(args.renders, args.screens, args.check)
    print(f"{n} block(s) {'would be ' if args.check else ''}restored")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
