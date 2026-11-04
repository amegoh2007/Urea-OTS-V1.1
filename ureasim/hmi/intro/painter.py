"""Qt painter of the start-up intro: draws the operations of ``scene.build_frame`` with QPainter.

Plant equipment modelled: none (presentation only).
Reference document: ``ureasim/data/intro.py`` (fonts, logo file name).
Equations: none; the painter applies the design-to-screen transform
screen = (design - view origin) x scale.

Process utility
---------------
The one place the intro touches Qt. It is an interpreter: it keeps no animation state and decides
nothing, so the scene stays testable without a display and the painter can be swapped for a video
renderer when the intro is reviewed. Per CLAUDE.md section 4a it renders what it is given and
computes nothing of its own.

Frame cost (session 85, As-Built Part XCVII). The frame is redrawn sixty times a second on a display that
may scale it, so three things keep a repaint cheap, none of them changing what is drawn:

* a ``Static`` group (the paper and its grid) seen on two consecutive frames is drawn once into a
  bitmap at the device's resolution and blitted afterwards;
* batches of separate wire segments use flat pen caps: a round cap costs about three times the
  antialiased fill of a flat one on a 1 px line, and a segment's cap is hidden by the next anyway;
* a batch no wider than ``HAIRLINE_MAX_PX`` on the device is drawn one device pixel wide with its opacity
  scaled by its width, which Qt rasterizes on a fast path and which keeps the ink;
* the fonts and the width of each text are made once and kept (bounded), because a label is the same
  string and size frame after frame;
* the QLineF objects a batch needs are kept and refilled, not made anew: making 1,900 a frame took
  2 ms, refilling them 0.8 ms.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PyQt6.QtCore import QLineF, QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetricsF,
    QImage,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
    QPolygonF,
)

from ureasim.data.intro import FONT_FAMILIES, HAIRLINE_MAX_PX
from ureasim.hmi.intro.ops import (
    Circle,
    GradientRect,
    Image,
    Line,
    Lines,
    Op,
    Polygon,
    Rect,
    RoundRect,
    Static,
    Text,
)
from ureasim.hmi.intro.scene import pixel_scale

ASSET_DIR = Path(__file__).resolve().parent / "assets"


_BASE_COLORS: dict[str, QColor] = {}  # one parsed QColor per palette entry (a dozen)


def _color(hex_color: str, alpha: float = 1.0) -> QColor:
    """``#RRGGBB`` plus an opacity in [0, 1] as a QColor."""
    base = _BASE_COLORS.get(hex_color)
    if base is None:
        base = _BASE_COLORS[hex_color] = QColor(hex_color)
    c = QColor(base)
    c.setAlphaF(max(0.0, min(1.0, alpha)))
    return c


def _rect(r: Rect) -> QRectF:
    return QRectF(r.x, r.y, r.w, r.h)


@lru_cache(maxsize=256)
def _font(size: int, bold: bool, spacing: float) -> QFont:
    """The font of a text operation, made once per (size, weight, letter spacing)."""
    font = QFont()
    font.setFamilies(list(FONT_FAMILIES))
    font.setPixelSize(max(1, size))
    font.setWeight(QFont.Weight.Bold if bold else QFont.Weight.Normal)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    return font


@lru_cache(maxsize=2048)
def _text_metrics(size: int, bold: bool, spacing: float, text: str) -> tuple[float, float, float]:
    """(width, ascent, descent) of one line; the width has the trailing letter space backed out."""
    fm = QFontMetricsF(_font(size, bold, spacing))
    return fm.horizontalAdvance(text) - spacing, fm.ascent(), fm.descent()


@dataclass
class _Slot:
    """What the painter remembers of the n-th ``Static`` group of a frame."""

    seen: tuple | None = None  # the key of the previous frame's group
    key: tuple | None = None  # the key the bitmap below was drawn for
    pixmap: QPixmap | None = None


class IntroPainter:
    """Draws one frame of operations into a QPainter, loading each asset once."""

    def __init__(self) -> None:
        self._pixmaps: dict[str, QPixmap] = {}
        self._slots: list[_Slot] = []
        self._slot_index = 0
        self._frame: tuple = ()
        self._device_scale = 1.0  # design pixels to device pixels
        self._line_pool: list[QLineF] = []  # QLineF objects reused every batch (making 1,900 a frame costs 2 ms)
        self._handlers = {
            Static: self._draw_static,
            GradientRect: self._draw_gradient,
            Line: self._draw_line,
            Lines: self._draw_lines,
            Circle: self._draw_circle,
            RoundRect: self._draw_round_rect,
            Polygon: self._draw_polygon,
            Image: self._draw_image,
            Text: self._draw_text,
        }

    def warm_up(self) -> None:
        """Pay the one-time costs before the first frame: the logo's decode and Qt's font database.

        The first text measured in a process takes about 0.6 s while Qt builds its font database, which,
        left to the first frame that has text, is a stall in the middle of the animation. Done before the
        window shows, it is a short wait with nothing yet on screen.
        """
        self._pixmap("hfc-logo")
        _text_metrics(12, False, 0.0, "0")

    def _pixmap(self, name: str) -> QPixmap:
        pix = self._pixmaps.get(name)
        if pix is None:
            path = ASSET_DIR / f"{name}.png"
            pix = QPixmap(str(path))
            if pix.isNull():
                raise FileNotFoundError(f"intro asset missing or unreadable: {path}")
            self._pixmaps[name] = pix
        return pix

    def paint(self, p: QPainter, ops: list[Op], view: Rect, width_px: float, height_px: float) -> None:
        """Paint ``ops`` so that design-space ``view`` fills a widget of the given pixel size."""
        p.save()
        self._hints(p)
        s = pixel_scale(width_px, height_px)
        self._frame = (view, width_px, height_px, p.device().devicePixelRatioF())
        self._device_scale = s * self._frame[3]
        self._slot_index = 0
        p.scale(s, s)
        p.translate(-view.x, -view.y)
        for op in ops:
            self._draw(p, op)
        p.restore()

    @staticmethod
    def _hints(p: QPainter) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    def _draw_static(self, p: QPainter, group: Static) -> None:
        """Draw a group as it is, or, once an opaque one has repeated, blit the bitmap it was drawn into.

        A group is bitmapped only when it is the same on two frames in a row: while the grid fades in
        every frame differs, and a bitmap drawn for one frame would be the cost of a frame for nothing.
        The bitmap is keyed on the group and on the view, the widget's size and its pixel ratio, so a
        resize or a move to another screen draws afresh.
        """
        if not group.opaque:  # only a group that covers the widget can be bitmapped without changing it
            for op in group.ops:
                self._draw(p, op)
            return
        index = self._slot_index
        self._slot_index += 1
        while len(self._slots) <= index:
            self._slots.append(_Slot())
        slot = self._slots[index]
        key = (group, self._frame)
        if slot.key != key:
            slot.pixmap, slot.key = None, None
            if slot.seen == key:
                slot.pixmap, slot.key = self._bake(group), key
        slot.seen = key
        if slot.pixmap is None:
            for op in group.ops:
                self._draw(p, op)
            return
        p.save()
        p.resetTransform()
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)  # a copy, no blend
        p.drawPixmap(0, 0, slot.pixmap)
        p.restore()

    def _bake(self, group: Static) -> QPixmap:
        """The group drawn once into a bitmap the size of the widget, at the device's resolution.

        It is drawn through the very transform the direct drawing uses, so a baked group lands on the same
        device pixels as an unbaked one (a test holds the two frames equal, pixel for pixel).
        """
        view, width_px, height_px, ratio = self._frame
        image = QImage(math.ceil(width_px * ratio), math.ceil(height_px * ratio), QImage.Format.Format_RGB32)
        image.setDevicePixelRatio(ratio)
        q = QPainter(image)
        self._hints(q)
        q.scale(self._device_scale / ratio, self._device_scale / ratio)
        q.translate(-view.x, -view.y)
        for op in group.ops:
            self._draw(q, op)
        q.end()
        return QPixmap.fromImage(image)

    def _draw(self, p: QPainter, op: Op) -> None:
        """One operation, found by its type (a dictionary lookup, not a chain of ``isinstance``)."""
        self._handlers[type(op)](p, op)

    @staticmethod
    def _draw_gradient(p: QPainter, op: GradientRect) -> None:
        g = QLinearGradient(op.rect.x, op.rect.y, op.rect.x, op.rect.bottom)
        g.setColorAt(0.0, _color(op.top))
        g.setColorAt(1.0, _color(op.bottom))
        p.fillRect(_rect(op.rect), QBrush(g))

    def _draw_line(self, p: QPainter, op: Line) -> None:
        p.setPen(self._pen(op.color, op.alpha, op.width))
        p.drawLine(QPointF(op.x1, op.y1), QPointF(op.x2, op.y2))

    def _draw_lines(self, p: QPainter, op: Lines) -> None:
        width_px = op.width * self._device_scale
        if width_px <= HAIRLINE_MAX_PX:
            pen = self._pen(op.color, op.alpha * width_px, 1.0 / self._device_scale, Qt.PenCapStyle.FlatCap)
        else:
            pen = self._pen(op.color, op.alpha, op.width, Qt.PenCapStyle.FlatCap)
        p.setPen(pen)
        pool = self._line_pool
        while len(pool) < len(op.segments):
            pool.append(QLineF())
        lines = pool[: len(op.segments)]
        for line, (x1, y1, x2, y2) in zip(lines, op.segments):
            line.setLine(x1, y1, x2, y2)
        p.drawLines(lines)

    def _draw_circle(self, p: QPainter, op: Circle) -> None:
        if op.width > 0.0:
            p.setPen(self._pen(op.color, op.alpha, op.width))
            p.setBrush(Qt.BrushStyle.NoBrush)
        else:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(_color(op.color, op.alpha)))
        p.drawEllipse(QPointF(op.cx, op.cy), op.r, op.r)

    def _draw_round_rect(self, p: QPainter, op: RoundRect) -> None:
        if op.width > 0.0:
            p.setPen(self._pen(op.color, op.alpha, op.width))
            p.setBrush(Qt.BrushStyle.NoBrush)
        else:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(_color(op.color, op.alpha)))
        p.drawRoundedRect(_rect(op.rect), op.radius, op.radius)

    @staticmethod
    def _draw_polygon(p: QPainter, op: Polygon) -> None:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(_color(op.color, op.alpha)))
        p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in op.points]))

    def _draw_image(self, p: QPainter, op: Image) -> None:
        p.setOpacity(max(0.0, min(1.0, op.alpha)))
        p.drawPixmap(_rect(op.dst), self._pixmap(op.name), _rect(op.src))
        p.setOpacity(1.0)

    @staticmethod
    def _pen(color: str, alpha: float, width: float, cap: Qt.PenCapStyle = Qt.PenCapStyle.RoundCap) -> QPen:
        pen = QPen(_color(color, alpha), width)
        pen.setCapStyle(cap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        return pen

    @staticmethod
    def _draw_text(p: QPainter, op: Text) -> None:
        """One anchored line; letter spacing is also added after the last glyph, so it is backed out."""
        size = round(op.size)
        p.setFont(_font(size, op.bold, op.spacing))
        p.setPen(_color(op.color, op.alpha))
        width, ascent, descent = _text_metrics(size, op.bold, op.spacing, op.text)
        if op.anchor == "center":
            x = op.x - width / 2.0
        elif op.anchor == "right":
            x = op.x - width
        else:
            x = op.x
        baseline = op.y + (ascent - descent) / 2.0
        p.drawText(QPointF(x, baseline), op.text)
