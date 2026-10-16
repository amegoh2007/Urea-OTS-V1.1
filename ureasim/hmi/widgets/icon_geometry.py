"""Anisotropic slide geometry — the reason rotated icons look like themselves.

The problem
-----------
PowerPoint slides are 12192000 x 6858000 EMU. The HMI stage is 1366 x 720 px. Those are
both 16:9, but the scale factors are **not equal**:

    sx = 1366 / 12192000   across
    sy = 720  / 6858000    down
    SLIDE_RX = sx / sy = 1.0671875

The slide render is stretched 6.7 % wider than it is tall, relative to the drawing. For a
box that is not rotated, that does not matter — the element is simply sized in stage
pixels and lands in the hole its symbol left.

For a **rotated** icon it matters a great deal. A pump symbol rotated 90 degrees and then
stretched horizontally is an ellipse, not a pump.

The fix, and the order of operations
------------------------------------
Reproduce the slide's own order: draw the image at its **un-stretched** size, rotate it,
then apply the horizontal stretch.

    image size      (w / SLIDE_RX)  x  h
    transform       scaleX(SLIDE_RX) . rotate(theta) . scale(+/-1, +/-1)
                    ^ applied last                     ^ applied first

The right-most transform applies first, which is PowerPoint's order: mirror the symbol
inside its own box, rotate the box, then undo the stage's anisotropic squash. Getting that
order wrong puts a flipped-and-rotated pump on the wrong side of its line.

This is exact for any angle, and at theta = 0 with no mirror it collapses to a plain
``w x h`` box.

A bug this replaced
-------------------
In V1 the overlay box kept a fixed 54x54 / 34x34 default while the image inside carried the
real size. Because the box is centred but the image is laid out from its top-left, every
icon sat half the size difference off its symbol — the 321-1 pumps by 11 x 6 px and the
XVs by 17. The box is now sized to the same un-stretched rectangle as the image.
"""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QTransform

from ureasim.data.screen_layout import SLIDE_RX


@dataclass(frozen=True)
class IconGeometry:
    """Un-stretched box size and the transform that puts an icon back on its symbol.

    Attributes
    ----------
    width, height
        The size to draw the image at, **before** the horizontal stretch. The widget is
        sized to this same rectangle so that centring the widget centres the symbol.
    transform
        Applied to the painter (or to the pixmap) to produce the on-stage appearance.
    """

    width: float
    height: float
    transform: QTransform


def icon_geometry(w: float, h: float, rot: float = 0.0,
                  flip_x: bool = False, flip_y: bool = False) -> IconGeometry:
    """Build the geometry for one icon overlay.

    Parameters
    ----------
    w, h
        The icon's on-stage box **after** the anisotropic stretch — i.e. the ``w`` and
        ``h`` fields recorded in `ureasim.data.screen_layout`.
    rot
        Rotation in degrees, PowerPoint convention (clockwise positive).
    flip_x, flip_y
        Mirror the symbol inside its own box.

    Returns
    -------
    IconGeometry
        ``width``/``height`` to draw at, and the composed transform.
    """
    iw = w / SLIDE_RX
    ih = h

    # Compose in application order. QTransform multiplies on the right, so the calls below
    # read in the order the operations are APPLIED to the image: un-squash last means it is
    # written first here.
    t = QTransform()
    t.scale(SLIDE_RX, 1.0)                       # undo the stage's horizontal squash
    if rot:
        t.rotate(rot)                            # rotate the box
    if flip_x or flip_y:
        t.scale(-1.0 if flip_x else 1.0,         # mirror inside the box
                -1.0 if flip_y else 1.0)

    return IconGeometry(width=iw, height=ih, transform=t)


def bounding_size(geom: IconGeometry) -> tuple[float, float]:
    """On-stage bounding box of a transformed icon, in pixels.

    Used only for hit-testing and for the overlay-collision check; the widget itself keeps
    the un-stretched rectangle so that its centre is the symbol's centre.
    """
    rect = geom.transform.mapRect(
        QRectF(-geom.width / 2.0, -geom.height / 2.0, geom.width, geom.height)
    )
    return rect.width(), rect.height()


__all__ = ["SLIDE_RX", "IconGeometry", "icon_geometry", "bounding_size"]
