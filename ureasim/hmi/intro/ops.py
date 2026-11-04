"""Drawing operations of the start-up intro.

Plant equipment modelled: none (presentation only).
Reference document: none; the operations are the vocabulary the intro's scene is written in.
Equations: none.

Process utility
---------------
The intro is described frame by frame as a flat list of these operations, in the 1366 x 720 design
space of the DCS stages. Because a frame is plain data, the scene that produces it needs no display
to be tested, the Qt painter that draws it stays a thin interpreter, and the same frame can be
rendered to a still or a video for review. This module imports nothing from Qt.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Literal

Point = tuple[float, float]
Anchor = Literal["left", "center", "right"]


@dataclass(frozen=True, slots=True)
class Rect:
    """An axis-aligned rectangle in design pixels."""

    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @property
    def cx(self) -> float:
        return self.x + self.w / 2.0

    @property
    def cy(self) -> float:
        return self.y + self.h / 2.0


@dataclass(frozen=True, slots=True)
class GradientRect:
    """A rectangle filled with a vertical two-colour gradient (the paper behind the intro)."""

    rect: Rect
    top: str
    bottom: str


@dataclass(frozen=True, slots=True)
class Line:
    """A straight line with round caps."""

    x1: float
    y1: float
    x2: float
    y2: float
    color: str
    width: float
    alpha: float = 1.0


@dataclass(frozen=True, slots=True)
class Lines:
    """Many separate segments ``(x1, y1, x2, y2)`` that share one colour, width and opacity.

    The flyby's wireframe is a thousand segments; batching them by ink keeps a frame to a few dozen
    operations and lets the painter draw each batch with a single call.
    """

    segments: tuple[tuple[float, float, float, float], ...]
    color: str
    width: float
    alpha: float = 1.0


@dataclass(frozen=True, slots=True)
class Circle:
    """A circle: filled when ``width`` is zero, otherwise an outline of that width."""

    cx: float
    cy: float
    r: float
    color: str
    alpha: float = 1.0
    width: float = 0.0


@dataclass(frozen=True, slots=True)
class RoundRect:
    """A rounded rectangle: filled when ``width`` is zero, otherwise an outline of that width."""

    rect: Rect
    radius: float
    color: str
    alpha: float = 1.0
    width: float = 0.0


@dataclass(frozen=True, slots=True)
class Polygon:
    """A filled polygon (the play triangle of the start button)."""

    points: tuple[Point, ...]
    color: str
    alpha: float = 1.0


@dataclass(frozen=True, slots=True)
class Text:
    """One line of text anchored at ``x`` (left, centre or right) and vertically centred on ``y``."""

    x: float
    y: float
    text: str
    size: float
    color: str
    alpha: float = 1.0
    anchor: Anchor = "center"
    spacing: float = 0.0
    bold: bool = False


@dataclass(frozen=True, slots=True)
class Image:
    """A sub-rectangle ``src`` of a named asset drawn into ``dst``."""

    name: str
    src: Rect
    dst: Rect
    alpha: float = 1.0


@dataclass(frozen=True, slots=True)
class Static:
    """A group of operations that is the same from frame to frame (the paper and its grid).

    Process utility: a painter that sees the same group on consecutive frames may draw it once into a
    bitmap and blit that, instead of stroking sixty grid lines sixty times a second. The group stays
    where it is in the frame, so the drawing order, and with it what lies over what, is unchanged;
    a painter that does not cache simply draws the operations inside, one after another.

    ``opaque`` says the group covers the whole view, so its bitmap needs no alpha channel and blits
    at memory-copy speed. Only opaque groups are worth bitmapping: Qt blends antialiased text onto an
    opaque window and onto a transparent bitmap with different weights, so a bitmapped group with text
    would change the picture the moment it settled.
    """

    ops: tuple[Op, ...]
    opaque: bool = False


Op = GradientRect | Line | Lines | Circle | RoundRect | Polygon | Text | Image | Static


def flatten(ops: Iterable[Op]) -> Iterator[Op]:
    """The drawing operations of a frame with every ``Static`` group opened, in drawing order."""
    for op in ops:
        if isinstance(op, Static):
            yield from flatten(op.ops)
        else:
            yield op
