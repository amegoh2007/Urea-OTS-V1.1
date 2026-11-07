"""Tests of ureasim/hmi/intro/painter.py: the scene's operations rendered by QPainter, off screen.

Skipped where PyQt6 is not installed. Runs on Qt's native platform: the offscreen one sees no fonts on the development machine.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtCore import QLineF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter
from PyQt6.QtWidgets import QApplication

from ureasim.data.intro import (
    BUTTON,
    HAIRLINE_MAX_PX,
    LOAD_OPTION,
    PALETTE,
    STAGE,
    START_OPTION,
    START_OPTIONS,
    STRINGS,
    TIMELINE,
    TITLE,
)
from ureasim.hmi.intro import painter as painter_module
from ureasim.hmi.intro.ops import Circle, GradientRect, Line, Lines, Rect, Static, Text
from ureasim.hmi.intro.painter import IntroPainter
from ureasim.hmi.intro.scene import ButtonState, ButtonStates, build_frame, button_rect, view_rect


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _render(
    t: float, w: int = int(STAGE.width), h: int = int(STAGE.height), status: str = "", button: ButtonStates = ButtonState.IDLE
) -> QImage:
    image = QImage(w, h, QImage.Format.Format_ARGB32)
    image.fill(QColor("white"))
    view = view_rect(w, h)
    p = QPainter(image)
    IntroPainter().paint(p, build_frame(t, view, status=status, button=button), view, w, h)
    p.end()
    return image


def _count_near(image: QImage, hex_color: str, tolerance: int = 28, step: int = 3) -> int:
    target = QColor(hex_color)
    n = 0
    for y in range(0, image.height(), step):
        for x in range(0, image.width(), step):
            c = image.pixelColor(x, y)
            if (
                abs(c.red() - target.red()) <= tolerance
                and abs(c.green() - target.green()) <= tolerance
                and abs(c.blue() - target.blue()) <= tolerance
            ):
                n += 1
    return n


def test_first_frame_has_no_brand_colour(app) -> None:
    assert _count_near(_render(0.0), PALETTE.orange) == 0


def test_hold_frame_shows_the_orange_of_the_logo_and_the_divider(app) -> None:
    assert _count_near(_render(TIMELINE.hold), PALETTE.orange) > 300


def test_hold_frame_differs_from_first_frame(app) -> None:
    assert _render(0.0) != _render(TIMELINE.hold)


def test_title_text_is_drawn_where_the_scene_puts_it(app) -> None:
    image = _render(TIMELINE.hold)
    y0 = int(TITLE.line_1_y - TITLE.line_1_size / 2.0)
    y1 = int(TITLE.line_1_y + TITLE.line_1_size / 2.0)
    band = QImage.copy(image, 380, y0, 606, y1 - y0)
    assert _count_near(band, PALETTE.teal_deep, tolerance=40, step=1) > 150


def test_status_line_changes_the_footer_only(app) -> None:
    plain, with_status = _render(TIMELINE.hold), _render(TIMELINE.hold, status="Starting console")
    assert plain != with_status
    top = int(TITLE.footer_y - 40)
    assert QImage.copy(plain, 0, 0, plain.width(), top) == QImage.copy(with_status, 0, 0, plain.width(), top)


@pytest.mark.parametrize("size", [(1920, 1080), (1920, 1200), (1280, 1024), (2560, 1080)])
def test_other_sizes_paint_the_whole_widget(app, size) -> None:
    image = _render(TIMELINE.hold, *size)
    corners = [image.pixelColor(0, 0), image.pixelColor(size[0] - 1, 0), image.pixelColor(0, size[1] - 1)]
    # the paper runs to every corner: no bar of the white the image was cleared with
    assert all(c.red() < 255 or c.green() < 255 or c.blue() < 255 for c in corners)
    assert _count_near(image, PALETTE.orange, step=4) > 100


def test_a_missing_asset_is_reported_by_name(app, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(painter_module, "ASSET_DIR", tmp_path)
    with pytest.raises(FileNotFoundError, match="hfc-logo"):
        _render(TIMELINE.hold)


def test_subtitle_text_constant_is_not_clipped_by_the_stage(app) -> None:
    assert STRINGS.subtitle  # the string drawn in the hold frame is non-empty
    image = _render(TIMELINE.hold)
    y = int(TITLE.subtitle_y)
    assert any(image.pixelColor(x, y).red() < 235 for x in range(400, 966, 2))


def _near(c: QColor, hex_color: str, tolerance: int = 24) -> bool:
    t = QColor(hex_color)
    return abs(c.red() - t.red()) <= tolerance and abs(c.green() - t.green()) <= tolerance and abs(c.blue() - t.blue()) <= tolerance


def test_the_button_pill_is_drawn_where_the_hit_test_says(app) -> None:
    r = button_rect()
    x, y = int(r.x + 22), int(r.cy)  # inside the pill, left of the play triangle
    assert _near(_render(TIMELINE.hold).pixelColor(x, y), PALETTE.teal_deep)
    assert not _near(_render(TIMELINE.hold).pixelColor(int(r.x - 12), y), PALETTE.teal_deep)


def test_button_states_paint_their_own_fill(app) -> None:
    r = button_rect()
    x, y = int(r.x + 22), int(r.cy)
    assert _near(_render(TIMELINE.hold, button=ButtonState.HOVER).pixelColor(x, y), PALETTE.teal)
    busy = _render(TIMELINE.hold, button=ButtonState.BUSY).pixelColor(x, y)
    assert not _near(busy, PALETTE.teal_deep) and not _near(busy, PALETTE.teal)


def test_the_play_triangle_and_the_label_are_drawn(app) -> None:
    r = button_rect()
    image = _render(TIMELINE.hold)
    tx, ty = int(r.cx + START_OPTION.icon_dx), int(r.cy)
    assert _near(image.pixelColor(tx, ty), PALETTE.orange, tolerance=40)
    whites = sum(
        1
        for x in range(int(r.cx - 60), int(r.cx + 90))
        for y in range(int(r.cy - 12), int(r.cy + 12))
        if _near(image.pixelColor(x, y), PALETTE.white, tolerance=20)
    )
    assert whites > 80


def test_no_button_before_it_arrives(app) -> None:
    r = button_rect()
    assert not _near(_render(TIMELINE.button_in[0] - 0.05).pixelColor(int(r.x + 22), int(r.cy)), PALETTE.teal_deep)


def test_the_load_pill_its_folder_and_its_label_are_drawn_where_the_hit_test_says(app) -> None:
    r = button_rect(LOAD_OPTION.key)
    image = _render(TIMELINE.hold)
    assert _near(image.pixelColor(int(r.x + 12), int(r.cy)), PALETTE.teal_deep)      # the pill, left of the folder
    assert not _near(image.pixelColor(int(r.right + 12), int(r.cy)), PALETTE.teal_deep)
    assert _near(image.pixelColor(int(r.cx + LOAD_OPTION.icon_dx), int(r.cy + 1)), PALETTE.orange, tolerance=40)
    whites = sum(
        1
        for x in range(int(r.cx - 20), int(r.cx + 50))
        for y in range(int(r.cy - 12), int(r.cy + 12))
        if _near(image.pixelColor(x, y), PALETTE.white, tolerance=20)
    )
    assert whites > 40


def test_hovering_one_pill_lights_that_pill_only(app) -> None:
    load, full = button_rect(LOAD_OPTION.key), button_rect()
    image = _render(TIMELINE.hold, button={LOAD_OPTION.key: ButtonState.HOVER})
    assert _near(image.pixelColor(int(load.x + 12), int(load.cy)), PALETTE.teal)
    assert _near(image.pixelColor(int(full.x + 22), int(full.cy)), PALETTE.teal_deep)


@pytest.mark.parametrize("option", START_OPTIONS, ids=lambda o: o.key)
def test_every_label_fits_its_pill_clear_of_its_icon(app, option) -> None:
    """Measured with the painter's own font: the label stays off the rounded end and clear of the glyph."""
    r = button_rect(option.key)
    width, _ascent, _descent = painter_module._text_metrics(round(BUTTON.label_size), True, BUTTON.label_spacing, option.label)
    left, right = r.cx + option.label_dx - width / 2.0, r.cx + option.label_dx + width / 2.0
    icon_left = r.cx + option.icon_dx - 1.1 * BUTTON.icon_half_height
    icon_right = r.cx + option.icon_dx + 1.1 * BUTTON.icon_half_height
    assert r.x + 12.0 <= icon_left and icon_right + 8.0 <= left and right <= r.right - 12.0, (option.key, left, right)

# -- frame cost (session 85, handoff A-25 point 1) ---------------------------------------------------------


def _paint(painter: IntroPainter, w: float, h: float, ratio: float, ops, view=None) -> QImage:
    """One frame of ``ops`` painted by ``painter`` on a window-shaped image at a device pixel ratio."""
    image = QImage(round(w * ratio), round(h * ratio), QImage.Format.Format_RGB32)
    image.setDevicePixelRatio(ratio)
    p = QPainter(image)
    painter.paint(p, ops, view or view_rect(w, h), w, h)
    p.end()
    return image


_SIZES = [(1366.0, 720.0, 1.0), (1366.0, 720.0, 1.25), (1366.0, 720.0, 1.5), (1100.0, 700.0, 1.25), (1920.0, 1012.0, 1.0), (1537.0, 811.0, 1.75)]


@pytest.mark.parametrize("w, h, ratio", _SIZES)
def test_a_bitmapped_paper_is_the_paper_drawn_directly_pixel_for_pixel(app, w: float, h: float, ratio: float) -> None:
    """The cache must change the cost and nothing else: the same frame, painted before the cache is warm and
    after it, is the same image."""
    view = view_rect(w, h)
    ops = build_frame(TIMELINE.hold, view)
    direct = _paint(IntroPainter(), w, h, ratio, ops)
    warm = IntroPainter()
    _paint(warm, w, h, ratio, ops)
    _paint(warm, w, h, ratio, ops)  # a second identical frame bakes the group
    assert warm._slots[0].pixmap is not None
    assert _paint(warm, w, h, ratio, ops) == direct


def test_a_group_is_bitmapped_only_when_it_repeats_and_drawn_afresh_when_it_changes(app) -> None:
    w, h, ratio = 800.0, 450.0, 1.0
    view = view_rect(w, h)
    painter = IntroPainter()

    def frame(k: float) -> list:
        return build_frame(0.3 + k, view)  # the grid fades in over the first 0.6 s: a different paper each time

    _paint(painter, w, h, ratio, frame(0.0))
    assert painter._slots[0].pixmap is None  # seen once: not worth a bitmap
    _paint(painter, w, h, ratio, frame(0.05))
    assert painter._slots[0].pixmap is None  # a different group again
    _paint(painter, w, h, ratio, frame(10.0))
    _paint(painter, w, h, ratio, frame(11.0))  # settled: the same group twice
    baked = painter._slots[0].pixmap
    assert baked is not None
    _paint(painter, w, h, ratio, frame(12.0))
    assert painter._slots[0].pixmap is baked  # reused, not redrawn
    _paint(painter, w + 20, h, ratio, build_frame(TIMELINE.hold, view_rect(w + 20, h)))
    assert painter._slots[0].pixmap is None  # a resize draws afresh


def test_a_group_that_is_not_opaque_is_never_bitmapped(app) -> None:
    """Qt blends text onto an opaque window and onto a transparent bitmap with different weights, so only a
    group that covers the window may be bitmapped without changing the picture."""
    group = Static((Text(100.0, 100.0, "TAG", 20.0, "#000000"),))
    painter = IntroPainter()
    for _ in range(3):
        _paint(painter, 400.0, 300.0, 1.0, [group], view=Rect(0.0, 0.0, 400.0, 300.0))
    assert painter._slots == []


def test_the_view_and_the_pixel_ratio_are_part_of_the_cache_key(app) -> None:
    ops = build_frame(TIMELINE.hold, view_rect(800.0, 450.0))
    painter = IntroPainter()
    _paint(painter, 800.0, 450.0, 1.0, ops)
    _paint(painter, 800.0, 450.0, 1.0, ops)
    first = painter._slots[0].pixmap
    _paint(painter, 800.0, 450.0, 2.0, ops)  # the same widget on a denser display
    assert painter._slots[0].pixmap is None
    _paint(painter, 800.0, 450.0, 2.0, ops)
    assert painter._slots[0].pixmap is not first and painter._slots[0].pixmap.devicePixelRatio() == 2.0


class _Recorder:
    """The two calls ``IntroPainter._draw_lines`` makes on a QPainter, recorded."""

    def __init__(self) -> None:
        self.pen = None
        self.lines: list[QLineF] = []

    def setPen(self, pen) -> None:  # noqa: N802
        self.pen = pen

    def drawLines(self, lines) -> None:  # noqa: N802
        self.lines = list(lines)


def _batch(width: float, alpha: float = 0.6) -> Lines:
    return Lines(((0.0, 0.0, 10.0, 0.0), (10.0, 0.0, 10.0, 10.0)), "#1F5A58", width, alpha)


@pytest.mark.parametrize("device_scale, width", [(1.0, 1.0), (1.25, 1.0), (1.25, 1.1), (1.5, 1.0)])
def test_a_thin_batch_is_a_hairline_that_keeps_its_ink(app, device_scale: float, width: float) -> None:
    """No wider than HAIRLINE_MAX_PX on the device: one device pixel wide, opacity scaled by the width."""
    painter, rec = IntroPainter(), _Recorder()
    painter._device_scale = device_scale
    assert width * device_scale <= HAIRLINE_MAX_PX
    painter._draw_lines(rec, _batch(width))
    assert rec.pen.widthF() * device_scale == pytest.approx(1.0)
    assert rec.pen.color().alphaF() == pytest.approx(0.6 * width * device_scale, abs=1 / 255)
    assert rec.pen.capStyle() == Qt.PenCapStyle.FlatCap


@pytest.mark.parametrize("device_scale, width", [(1.25, 2.0), (1.75, 1.0), (2.0, 1.0)])
def test_a_wide_batch_keeps_its_width_and_its_opacity(app, device_scale: float, width: float) -> None:
    painter, rec = IntroPainter(), _Recorder()
    painter._device_scale = device_scale
    assert width * device_scale > HAIRLINE_MAX_PX
    painter._draw_lines(rec, _batch(width))
    assert rec.pen.widthF() == pytest.approx(width)
    assert rec.pen.color().alphaF() == pytest.approx(0.6, abs=1 / 255)
    assert rec.pen.capStyle() == Qt.PenCapStyle.FlatCap  # a segment's cap is hidden by the next one's


def _thin_wire_ink(w: float, h: float, ratio: float, hairline: bool, monkeypatch) -> float:
    """Total ink (255 minus the red channel, summed) of the hold frame's thin wire batches on a white window."""
    monkeypatch.setattr(painter_module, "HAIRLINE_MAX_PX", HAIRLINE_MAX_PX if hairline else 0.0)
    view = view_rect(w, h)
    thin = [o for o in build_frame(TIMELINE.hold, view) if isinstance(o, Lines) and o.width in (1.0, 1.1)]
    assert len(thin) >= 8 and sum(len(o.segments) for o in thin) > 1000  # the shell and ground wires of the hold frame
    image = QImage(round(w * ratio), round(h * ratio), QImage.Format.Format_RGB32)
    image.setDevicePixelRatio(ratio)
    image.fill(QColor("white"))
    p = QPainter(image)
    IntroPainter().paint(p, thin, view, w, h)
    p.end()
    ptr = image.constBits()
    ptr.setsize(image.sizeInBytes())
    pixels = np.frombuffer(ptr, dtype=np.uint8).reshape(image.height(), image.bytesPerLine())[:, : image.width() * 4]
    return float((255 - pixels.reshape(image.height(), image.width(), 4)[..., 2].astype(float)).sum())


def test_a_hairline_keeps_the_ink_of_the_true_width_wires_within_five_per_cent_on_the_hold_frame(app, monkeypatch) -> None:
    """XCVII.3 states 3.7 % less ink at 125 % display scaling and 1 % at 100 %, measured on the hold frame's thin
    wires; this is that measurement, held to 5 %."""
    w, h = STAGE.width, STAGE.height
    for ratio in (1.25, 1.0):
        true = _thin_wire_ink(w, h, ratio, hairline=False, monkeypatch=monkeypatch)
        hair = _thin_wire_ink(w, h, ratio, hairline=True, monkeypatch=monkeypatch)
        assert true > 0.0 and hair == pytest.approx(true, rel=0.05), ratio


def test_the_line_pool_is_reused_not_remade(app) -> None:
    painter, rec = IntroPainter(), _Recorder()
    painter._draw_lines(rec, _batch(1.0))
    first = list(painter._line_pool)
    assert len(first) == 2
    assert [(ln.x1(), ln.y1(), ln.x2(), ln.y2()) for ln in rec.lines] == [(0.0, 0.0, 10.0, 0.0), (10.0, 0.0, 10.0, 10.0)]
    painter._draw_lines(rec, Lines(((1.0, 2.0, 3.0, 4.0),), "#000000", 1.0, 1.0))
    assert len(rec.lines) == 1 and rec.lines[0].y2() == 4.0  # a shorter batch draws only its own segments
    assert all(a is b for a, b in zip(painter._line_pool, first))  # the same QLineF objects, refilled


def test_the_paint_turns_on_antialiasing_and_smooth_pixmap_transform(app) -> None:
    """A downscaled logo must be filtered, not point-sampled: SmoothPixmapTransform is on for every operation
    (handoff A-25 point 5), and so is antialiasing."""
    seen: list = []
    painter = IntroPainter()
    original = painter._handlers[Line]

    def spy(p, op) -> None:
        seen.append(p.renderHints())
        original(p, op)

    painter._handlers[Line] = spy
    _paint(painter, 200.0, 100.0, 1.0, [Line(0.0, 0.0, 10.0, 10.0, "#000000", 1.0)], view=Rect(0.0, 0.0, 200.0, 100.0))
    hints = seen[0]
    assert hints & QPainter.RenderHint.SmoothPixmapTransform
    assert hints & QPainter.RenderHint.Antialiasing and hints & QPainter.RenderHint.TextAntialiasing


def test_the_logo_is_drawn_from_the_doubled_atlas_without_scaling_it_up(app) -> None:
    """On a windowed stage the 1280 px atlas is drawn 480 px wide: always scaled down, never up."""
    pix = IntroPainter()._pixmap("hfc-logo")
    assert (pix.width(), pix.height()) == (1280, 602)
    assert 480.0 / pix.width() < 1.0


def test_fonts_and_text_widths_are_made_once(app) -> None:
    assert painter_module._font(11, True, 1.5) is painter_module._font(11, True, 1.5)
    assert painter_module._font(11, True, 1.5) is not painter_module._font(11, False, 1.5)
    assert painter_module._text_metrics(11, True, 1.5, "322R001") is painter_module._text_metrics(11, True, 1.5, "322R001")
    width, ascent, descent = painter_module._text_metrics(11, True, 1.5, "322R001")
    assert width > 0 and ascent > 0 and descent >= 0


def test_a_warm_up_loads_the_logo_before_the_first_frame(app) -> None:
    painter = IntroPainter()
    assert painter._pixmaps == {}
    painter.warm_up()
    assert "hfc-logo" in painter._pixmaps


def test_the_dispatch_table_has_a_handler_for_every_operation(app) -> None:
    from ureasim.hmi.intro import ops

    assert set(IntroPainter()._handlers) == set(ops.Op.__args__)


def test_a_gradient_and_a_circle_are_drawn_through_their_handlers(app) -> None:
    w, h = STAGE.width, STAGE.height  # the painter maps the stage onto the widget
    image = _paint(
        IntroPainter(),
        w,
        h,
        1.0,
        [GradientRect(Rect(0, 0, w, h), "#FFFFFF", "#000000"), Circle(w / 2, h / 2, 100.0, "#FF0000")],
    )
    centre = image.pixelColor(int(w / 2), int(h / 2))
    assert centre.red() > 200 and centre.green() < 80  # the red disc
    assert image.pixelColor(5, 5).red() > image.pixelColor(5, int(h) - 5).red() + 150  # light at the top, dark below
