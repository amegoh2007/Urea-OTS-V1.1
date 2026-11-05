"""The intro's GPU canvas, and the test of whether this machine can give it one.

Plant equipment modelled: none (presentation only).
Reference document: ``ureasim/data/intro.py`` (``RENDER``: the multisampling, the kill switch, the platforms
and software renderers that get no canvas); handoff A-26, As-Built Part XCIX.1.
Equations: none.

Process utility
---------------
The intro redraws its whole frame sixty times a second. On the CPU rasterizer the cost of that grows with
the window's pixels, so a full-screen window on a scaled display leaves little of the 16.6 ms for anything
else the machine is doing, and the animation drops frames. Painted through a ``QOpenGLWidget`` the same
``IntroPainter`` operations cost the main thread about the same whatever the window's size (the GPU does
the fill), which is what keeps the frame rate up while a build, a backup or a browser has the CPU.

The canvas changes nothing in what is drawn: it is a child of the splash that fills it and calls back into
the splash's own paint routine with itself as the paint device, so the painter, the scene and the data are
the very ones the raster path uses. It is used only where a hardware OpenGL 2.0 context can be made. A
machine without one, a remote session, a virtual machine, the headless test platforms and an operator who
sets the switch in ``RENDER.env_switch`` to ``raster`` get the splash drawing itself, as it did before.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from functools import lru_cache

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication, QOffscreenSurface, QOpenGLContext, QPaintDevice, QSurfaceFormat
from PyQt6.QtOpenGL import QOpenGLVersionFunctionsFactory, QOpenGLVersionProfile
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtWidgets import QWidget

from ureasim.data.intro import RENDER

__all__ = ["GLCanvas", "is_software_renderer", "opengl_available"]

log = logging.getLogger(__name__)

_GL_RENDERER = 0x1F01  # glGetString's name for the renderer description


def is_software_renderer(renderer: str) -> bool:
    """Whether an OpenGL renderer description names a software rasterizer (``RENDER.software_renderers``)."""
    lowered = renderer.lower()
    return any(name.lower() in lowered for name in RENDER.software_renderers)


def _hardware_context() -> bool:
    """Make an OpenGL context off screen and say whether it is a hardware one of version 2.0 or later.

    The renderer's name is read so that a driver-less machine's software OpenGL ("GDI Generic", the
    "Microsoft Basic Render Driver", Mesa's llvmpipe) is refused: drawn there, the canvas is slower than
    the CPU rasterizer it was meant to relieve.
    """
    context = QOpenGLContext()
    if not context.create():
        return False
    fmt = context.format()
    if (fmt.majorVersion(), fmt.minorVersion()) < RENDER.min_gl_version:
        return False
    surface = QOffscreenSurface()
    surface.setFormat(fmt)
    surface.create()
    if not surface.isValid() or not context.makeCurrent(surface):
        return False
    try:
        profile = QOpenGLVersionProfile()
        profile.setVersion(2, 1)
        functions = QOpenGLVersionFunctionsFactory.get(profile, context)
        if functions is None:  # an OpenGL ES context, or one that is not a desktop 2.1: not tried
            return False
        renderer = str(functions.glGetString(_GL_RENDERER))
    finally:
        context.doneCurrent()
    log.info("intro OpenGL renderer: %s", renderer)
    return not is_software_renderer(renderer)


@lru_cache(maxsize=1)
def opengl_available() -> bool:
    """Whether the intro may paint on the GPU: decided once, on the first call, and kept.

    False on a platform with no OpenGL, when ``RENDER.env_switch`` is ``raster``, and when the probe in
    `_hardware_context` finds no hardware context or fails for any reason.
    """
    if os.environ.get(RENDER.env_switch, "").strip().lower() == "raster":
        return False
    if QGuiApplication.instance() is None or QGuiApplication.platformName() in RENDER.no_gl_platforms:
        return False
    try:
        return _hardware_context()
    except Exception:  # noqa: BLE001 - a driver that raises is a driver that cannot be used
        log.exception("the OpenGL probe failed; the intro draws on the CPU")
        return False


class GLCanvas(QOpenGLWidget):
    """A child of the splash that paints each frame through ``draw``, a function of a paint device.

    It takes no mouse events (the splash keeps them) and is multisampled so a wire's edge is smooth as it
    is on the raster path (measured: the same edge energy within 0.5 %).
    """

    def __init__(self, parent: QWidget, draw: Callable[[QPaintDevice], None]) -> None:
        super().__init__(parent)
        fmt = QSurfaceFormat()
        fmt.setSamples(RENDER.samples)
        self.setFormat(fmt)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._draw = draw

    def paintGL(self) -> None:  # noqa: N802
        self._draw(self)
