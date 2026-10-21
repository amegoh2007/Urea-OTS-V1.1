"""Overlay geometry gates, carried over from V1's UI-migration verification procedure.

V1's rule was "measure it, do not eyeball it". These are the same measurements, done with
Qt widget geometry instead of `getBoundingClientRect()`:

  * every screen builds, with a widget for every element and no unknown types;
  * **no overlay-on-overlay collision** — nav and stream hotspots included, because they are
    transparent and an overlap steals a click rather than showing a visible defect (zero on
    every screen since A-7's decision, 2026-10-09);
  * the element counts the drawings give, as a floor that guards against a silent loss;
  * shared tags resolve to one value across screens;
  * at the design state, with one more digit in every readout, no readout covers a drawn label,
    symbol or block, nor touches another element; every page button has its block drawn
    (decision 129, 2026-10-16: the pages revised from their slides).

A note on font metrics
----------------------
An indicator is sized by its content, so its width depends on the value font actually
being present. Under a font fallback the metrics inflate by roughly 1.8x and the collision
measurement becomes a measurement of the test environment. The collision test therefore
requires one of `theme.VALUE_FONT_FAMILIES` to be installed, and skips with that reason
when it is not.
"""

from __future__ import annotations

import numpy as np
import pytest
from PyQt6.QtGui import QColor, QFontDatabase, QFontMetrics, QImage, QPainter
from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QRegion
from PyQt6.QtWidgets import QApplication, QWidget

from ureasim.data.screen_layout import OVERLAYS, SCREENS, STAGE_H, STAGE_W
from ureasim.hmi import theme
from ureasim.hmi.screen_view import SCREEN_DIR, Stage
from ureasim.hmi.state_access import BindMap

#: Counts the 2026-09 drawings publish. These are FLOORS: a revision may add instruments,
#: and if one legitimately removes an instrument the floor moves WITH a note saying what
#: the deck stopped showing. That accounting is the only record of such a change. The 47
#: modulating valves are indicators since decision 129 (2026-10-16): no valve icon but the
#: XVs', each valve's opening a readout in per cent — 199 + 47 indicators, no "avalve".
TYPE_FLOORS = {
    "ind": 246, "nav": 67, "pump": 26,
    "bar": 22, "strm": 12, "xv": 6, "hs": 4, "ae": 2,
}

#: Total bound tags across all screens. Guards against a binding silently disappearing in
#: a re-conversion.
BOUND_TAG_FLOOR = 200

#: Collisions accepted on a screen. EMPTY: zero overlap on every screen, as V1's migration
#: procedure requires (handoff A-7, decided 2026-10-09). The five V1 left — four hand-placed
#: stream hotspots over a nav label or a crossing run, and TV-323013A / B drawn 31 px apart while
#: the valve and its readout stand 34 px — are resolved by the converter's `NUDGE` rows
#: (`tools/convert_overlays.py`): the stream hotspots yield to the nav labels and stop one pixel
#: short of the run they cross, and TV-323013B moves down 3 px. A row added here needs its reason
#: and a handoff item.
KNOWN_COLLISIONS: dict = {}


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def bind_map():
    return BindMap(OVERLAYS)


@pytest.fixture(scope="module")
def stages(app, bind_map):
    """Build all ten screens once; every geometry test reads these."""
    return {sid: Stage(sid, OVERLAYS[sid], bind_map) for sid, _ in SCREENS}


def _value_font_available(app) -> bool:
    families = set(QFontDatabase.families())
    return any(f in families for f in theme.VALUE_FONT_FAMILIES)


# --------------------------------------------------------------------------------------
# Structure
# --------------------------------------------------------------------------------------

def test_every_screen_is_declared():
    assert len(SCREENS) == 10
    for sid, _title in SCREENS:
        assert sid in OVERLAYS, sid


def test_every_screen_has_a_background_render():
    """A missing PNG renders as flat teal — readable, but not the drawing."""
    for sid, _title in SCREENS:
        assert (SCREEN_DIR / f"{sid}.png").is_file(), sid


def test_element_type_floors():
    counts: dict[str, int] = {}
    for elements in OVERLAYS.values():
        for el in elements:
            counts[el["t"]] = counts.get(el["t"], 0) + 1
    for kind, floor in TYPE_FLOORS.items():
        assert counts.get(kind, 0) >= floor, f"{kind}: {counts.get(kind, 0)} < {floor}"


def test_bound_tag_floor(bind_map):
    assert len(bind_map.bound_tags()) >= BOUND_TAG_FLOOR


def test_every_element_builds_a_widget(stages):
    for sid, stage in stages.items():
        assert len(stage.overlays) == len(OVERLAYS[sid]), sid


def test_element_keys_unique_within_a_screen():
    for sid, elements in OVERLAYS.items():
        keys = [el["k"] for el in elements]
        assert len(keys) == len(set(keys)), sid


def test_nav_hotspots_point_at_a_real_screen():
    known = {sid for sid, _ in SCREENS}
    for sid, elements in OVERLAYS.items():
        for el in elements:
            if el["t"] == "nav":
                assert el.get("goto") in known, f"{sid}/{el['k']} -> {el.get('goto')}"


# --------------------------------------------------------------------------------------
# Geometry — measured, not eyeballed
# --------------------------------------------------------------------------------------

def test_no_new_overlay_collisions(app, stages):
    """No overlay-on-overlay collision on any screen (A-7: zero).

    Nav and stream hotspots count. They are transparent, so an overlap does not look like
    anything — it just silently steals the click from whatever is under it.
    """
    if not _value_font_available(app):
        pytest.skip(
            "none of theme.VALUE_FONT_FAMILIES is installed; indicator widths would be "
            "measured under a font fallback, which inflates them by roughly 1.8x"
        )

    unexpected = []
    seen = set()
    for sid, stage in stages.items():
        rects = [(w.element.get("k"), w.element.get("tag"), w.geometry())
                 for w in stage.overlays]
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                if not rects[i][2].intersects(rects[j][2]):
                    continue
                key = (sid, rects[i][0], rects[j][0])
                if key in KNOWN_COLLISIONS:
                    seen.add(key)
                    continue
                unexpected.append(
                    f"{sid}: {rects[i][1]} ({rects[i][0]}) overlaps "
                    f"{rects[j][1]} ({rects[j][0]})"
                )

    assert not unexpected, "new overlay collisions:\n" + "\n".join(unexpected[:40])

    # A pinned collision that no longer occurs means the drawing or the widget sizing was
    # fixed — delete the row rather than leaving it to mask a future regression.
    stale = set(KNOWN_COLLISIONS) - seen
    assert not stale, f"pinned collisions no longer occur; remove them: {sorted(stale)}"


def test_overlays_land_on_the_stage(stages):
    """Every overlay's centre is inside the stage.

    An element that falls off the stage is invisible, and the collision test cannot see it
    either — so it is checked separately.
    """
    for sid, stage in stages.items():
        for w in stage.overlays:
            cx, cy = w.centre
            assert 0 <= cx <= STAGE_W, f"{sid}/{w.element.get('k')} x={cx}"
            assert 0 <= cy <= STAGE_H, f"{sid}/{w.element.get('k')} y={cy}"


def test_overlay_is_centred_on_its_recorded_point(stages):
    """The widget's centre must be the coordinate the drawing recorded, within rounding.

    This is the invariant that keeps an overlay in the hole its symbol left. V1 broke it
    once by keeping a default box size while the image inside carried the real size, which
    put every icon half the size difference off its symbol.

    The centre is computed as ``x + w/2``, not with ``QRect.center()``: Qt defines a
    rectangle's centre on its integer grid as ``x + (w-1)/2``, half a pixel low, which is a
    property of QRect rather than of the layout.
    """
    for sid, stage in stages.items():
        for w in stage.overlays:
            cx, cy = w.centre
            g = w.geometry()
            gx = g.x() + g.width() / 2.0
            gy = g.y() + g.height() / 2.0
            assert abs(gx - cx) <= 0.5, f"{sid}/{w.element.get('k')} x {gx} vs {cx}"
            assert abs(gy - cy) <= 0.5, f"{sid}/{w.element.get('k')} y {gy} vs {cy}"


# --------------------------------------------------------------------------------------
# Shared tags and snapshot robustness
# --------------------------------------------------------------------------------------

def test_shared_tags_resolve_to_one_binding(bind_map):
    """An unbound occurrence of a bound tag inherits that binding.

    Without this, the same instrument would read live on one screen and `--` on another.
    """
    for elements in OVERLAYS.values():
        for el in elements:
            if el["t"] == "ind" and not el.get("bind"):
                effective = bind_map.effective(el)
                if effective.get("bind"):
                    assert effective["tag"] == el["tag"]


def test_snapshot_absence_never_raises(stages):
    """An empty snapshot must render as '--' everywhere, not raise.

    This is the state the console runs in before the engine layer lands, and it is also
    what happens on the first tick after a reset.
    """
    for stage in stages.values():
        stage.update_from({})
        stage.update_from(None)


def test_the_decided_additions_are_on_their_screens():
    """Decision 98 (2026-10-10): trip 21.2's five keyswitches and AI-329701, each on the screen of
    the equipment it serves, through the converter's `DECIDED_ADDITIONS`."""
    where = {el["tag"]: sid for sid, elements in OVERLAYS.items() for el in elements
             if el["k"] in ("ovrhs321634", "ovrhs321603", "ovrhs321604", "ovrhs322606",
                            "ovrhs323604", "ai329701")}
    assert where == {"HS-321634": "screen-321-1", "HS-321603": "screen-321-1",
                     "HS-321604": "screen-321-1", "HS-322606": "screen-322-1",
                     "HS-323604": "screen-323-2", "AI-329701": "screen-329-1"}


def test_no_element_is_a_valve_icon():
    """Decision 129: the only valve icons are the block valves' (XV)."""
    assert not [(sid, el["k"]) for sid, els in OVERLAYS.items() for el in els
                if el["t"] == "avalve"]


# --------------------------------------------------------------------------------------
# The drawing under the overlays (decision 129)
# --------------------------------------------------------------------------------------

def _background(sid: str) -> np.ndarray:
    """A screen's background as an (h, w, 3) integer array."""
    img = QImage(str(SCREEN_DIR / f"{sid}.png")).convertToFormat(QImage.Format.Format_RGB888)
    ptr = img.constBits()
    ptr.setsize(img.sizeInBytes())
    rows = np.frombuffer(ptr, np.uint8).reshape(img.height(), img.bytesPerLine())
    return rows[:, :img.width() * 3].reshape(img.height(), img.width(), 3).astype(int)


def _thin(full: np.ndarray, max_width: int = 3) -> np.ndarray:
    """The full-span rows (or columns) that belong to a line: runs at most ``max_width`` wide."""
    out = full.copy()
    i, n = 0, len(full)
    while i < n:
        if full[i]:
            j = i
            while j < n and full[j]:
                j += 1
            if j - i > max_width:
                out[i:j] = False
            i = j
        else:
            i += 1
    return out


def _covers_drawing(bg: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> bool:
    """Whether a box covers a drawn label, symbol or block — anything but the black stage, a
    blue panel's fill (readouts sit in panels by design) and the thin leader or signal lines a
    readout sits on."""
    reg = bg[max(y0, 0):y1, max(x0, 0):x1]
    ink = reg.max(axis=2) > 70
    if not ink.any():
        return False
    vals, cnt = np.unique(reg[ink] // 16, axis=0, return_counts=True)
    fill = vals[cnt.argmax()] * 16
    if cnt.max() > 0.3 * ink.size and fill[2] > fill[0] + 40 and fill[2] > 120:
        ink &= ~np.all(reg // 16 == vals[cnt.argmax()], axis=2)
    h, w = ink.shape
    ink[_thin(ink.sum(axis=1) >= 0.8 * w), :] = False
    ink[:, _thin(ink.sum(axis=0) >= 0.8 * h)] = False
    # A graze of the frame's outer 2 px is not a covered drawing: a line ending at the box, or a
    # symbol's edge a pixel off it.
    ink[:, :2] = ink[:, -2:] = False
    ink[:2, :] = ink[-2:, :] = False
    ys, xs = np.nonzero(ink)
    return bool(len(xs) > 10 and xs.max() - xs.min() >= 3 and ys.max() - ys.min() >= 4)


#: Readouts that sit on drawn ink by construction: a pushbutton laid exactly over the box the
#: slide draws for it, and the dashed corners or line stubs a readout's own leader makes inside
#: its box. Each was looked at on the rendered screen (2026-10-16).
COVERS_BY_DESIGN = {
    ("screen-322-1", "hs203"),          # HS-322203's button over its drawn box
    ("screen-322-2", "pt9201"), ("screen-329-1", "pic329205"), ("screen-323-1", "pic329202"),
    ("screen-323-1", "tic323012"), ("screen-323-2", "fic328405"), ("screen-328-1", "fic328404"),
    ("screen-328-1", "tt328012"), ("screen-328-1", "tt328009"), ("screen-328-1", "fv329402"),
    ("screen-324-1", "pic329203"), ("screen-324-1", "fic324401"),
    ("screen-324-1b", "ffic335406"), ("screen-324-1b", "fic335405a"),
}


@pytest.fixture(scope="module")
def design_packet():
    from ureasim.engine.packet import build_packet
    from ureasim.engine.plant import build_plant
    from ureasim.engine.scheduler import Scheduler
    sched = Scheduler(*build_plant())
    sched.tick()
    return build_packet(sched.plant, sched.results, sched.tears_read, sim_mode="SLOW",
                        t_wall=0.0)


def test_no_readout_covers_the_drawing_or_another_at_design(app, bind_map, design_packet):
    """At the design state, each live readout widened by one more digit: no readout covers a
    drawn label, symbol or block, and none touches another element (decision 129)."""
    if not _value_font_available(app):
        pytest.skip("none of theme.VALUE_FONT_FAMILIES is installed")
    faults = []
    for sid, _title in SCREENS:
        stage = Stage(sid, OVERLAYS[sid], bind_map)
        stage.update_from(design_packet)
        bg = _background(sid)
        boxes = []
        for w in stage.overlays:
            g, el = w.geometry(), w.element
            r = [g.x(), g.y(), g.x() + g.width(), g.y() + g.height()]
            if el["t"] == "ind" and el.get("bind"):
                digit = QFontMetrics(w._font_value).horizontalAdvance("0")
                r[0] -= digit // 2 + 1
                r[2] += digit // 2 + 1
            boxes.append((el["k"], el["t"], r))
        for i, (k, t, r) in enumerate(boxes):
            if t in ("ind", "btn", "hs", "ovrd", "ae") and (sid, k) not in COVERS_BY_DESIGN \
                    and _covers_drawing(bg, *r):
                faults.append(f"{sid}/{k} covers the drawing")
            for k2, t2, r2 in boxes[i + 1:]:
                if "strm" in (t, t2):
                    continue
                if min(r[2], r2[2]) > max(r[0], r2[0]) and min(r[3], r2[3]) > max(r[1], r2[1]):
                    faults.append(f"{sid}/{k} touches {k2}")
    assert not faults, "\n".join(faults)


def test_every_page_button_has_its_block_drawn():
    """A nav hotspot is transparent: the block it opens must be in the drawing. V1's migration
    stripped 51 of them from seven pages; tools/restore_nav_blocks.py put them back from the
    slides (decision 129). A drawn block fills 79 % of its rectangle or more; a stripped one
    almost none."""
    blank = []
    for sid, elements in OVERLAYS.items():
        bg = _background(sid)
        for el in elements:
            if el["t"] != "nav":
                continue
            w, h = float(el.get("w") or 100), float(el.get("h") or 24)
            x0, y0 = int(round(el["x"] - w / 2)), int(round(el["y"] - h / 2))
            reg = bg[y0:y0 + int(round(h)), x0:x0 + int(round(w))]
            if (reg.max(axis=2) > 70).mean() < 0.5:
                blank.append(f"{sid}/{el['k']} ({el['tag']})")
    assert not blank, "page buttons with no drawn block:\n" + "\n".join(blank)


def test_a_hovered_hotspot_tints_rather_than_blacks_out(app):
    """The hover colours are CSS rgba() tokens, which QColor does not parse: handed one it
    painted opaque black over the drawn label, so a hovered page button vanished (fixed
    2026-10-16). Hovered over white, the hotspot's centre stays light."""
    from ureasim.hmi.widgets.hotspots import NavHotspotWidget
    assert QColor(*theme.rgba(theme.HOTSPOT_HOVER_BG)).alpha() < 255
    hot = NavHotspotWidget({"k": "n", "t": "nav", "x": 50, "y": 12, "w": 100, "h": 24,
                            "tag": "X", "goto": "screen-321-1"})
    hot._hovered = True
    img = QImage(100, 24, QImage.Format.Format_ARGB32)
    img.fill(QColor("#ffffff"))
    painter = QPainter(img)
    hot.render(painter, QPoint(), QRegion(), QWidget.RenderFlag.DrawChildren)
    painter.end()
    assert QColor(img.pixel(50, 12)).lightness() > 180
