"""Tests of ureasim/hmi/intro/canvas.py and its use by the splash (handoff A-26).

The canvas is the GPU surface the intro is painted on where the machine has a GPU, and the window draws
itself everywhere else. Pinned without a GPU: which renderers count as software, that a platform with no
OpenGL, the kill switch, a failing probe and a canvas that cannot make its context all end with the splash
drawing itself, that the probe is made once, and that the splash asks it unless told. Pinned where this
machine has a GPU (skipped elsewhere): the canvas draws the very frame the raster path draws, it takes no
mouse events, and ``repaint()`` paints at once while ``update()`` waits for the event loop.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QGuiApplication, QImage
from PyQt6.QtWidgets import QApplication

from ureasim.data.intro import RENDER
from ureasim.hmi.intro import IntroSplash
from ureasim.hmi.intro import canvas as canvas_module
from ureasim.hmi.intro import splash as splash_module
from ureasim.hmi.intro.canvas import GLCanvas, is_software_renderer, opengl_available


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def fresh_probe(monkeypatch):
    """Every test decides afresh: the probe's answer is cached for a run of the application."""
    monkeypatch.delenv(RENDER.env_switch, raising=False)
    opengl_available.cache_clear()
    yield
    opengl_available.cache_clear()


def _gpu_here(app) -> bool:
    return QGuiApplication.platformName() not in RENDER.no_gl_platforms and opengl_available()


@pytest.mark.parametrize("renderer, software", [
    ("Intel(R) Iris(R) Xe Graphics", False),
    ("NVIDIA GeForce RTX 3060/PCIe/SSE2", False),
    ("AMD Radeon(TM) Graphics", False),
    ("GDI Generic", True),
    ("Microsoft Basic Render Driver", True),
    ("llvmpipe (LLVM 15.0.7, 256 bits)", True),
    ("Mesa Software Rasterizer", True),
    ("SOFTPIPE", True),                    # the comparison ignores case
])
def test_a_software_renderer_is_refused_and_a_gpu_is_not(renderer: str, software: bool) -> None:
    assert is_software_renderer(renderer) is software


def test_a_platform_with_no_opengl_gets_no_canvas_and_is_not_probed(app, monkeypatch) -> None:
    def probed():
        raise AssertionError("a platform with no OpenGL must not be probed")
    monkeypatch.setattr(canvas_module, "_hardware_context", probed)
    for name in RENDER.no_gl_platforms:
        opengl_available.cache_clear()
        monkeypatch.setattr(QGuiApplication, "platformName", staticmethod(lambda n=name: n))
        assert opengl_available() is False, name


def test_the_kill_switch_turns_the_canvas_off_without_probing(app, monkeypatch) -> None:
    monkeypatch.setattr(QGuiApplication, "platformName", staticmethod(lambda: "windows"))
    monkeypatch.setattr(canvas_module, "_hardware_context", lambda: pytest.fail("probed"))
    monkeypatch.setenv(RENDER.env_switch, " Raster ")
    assert opengl_available() is False


def test_the_probe_decides_and_is_made_once(app, monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(QGuiApplication, "platformName", staticmethod(lambda: "windows"))
    monkeypatch.setattr(canvas_module, "_hardware_context", lambda: calls.append(1) or True)
    assert opengl_available() is True and opengl_available() is True and calls == [1]
    opengl_available.cache_clear()
    monkeypatch.setattr(canvas_module, "_hardware_context", lambda: calls.append(2) or False)
    assert opengl_available() is False and calls == [1, 2]


def test_a_probe_that_raises_means_no_canvas_and_says_so(app, monkeypatch, caplog) -> None:
    def broken():
        raise OSError("the driver fell over")
    monkeypatch.setattr(QGuiApplication, "platformName", staticmethod(lambda: "windows"))
    monkeypatch.setattr(canvas_module, "_hardware_context", broken)
    with caplog.at_level("ERROR"):
        assert opengl_available() is False
    assert any("the driver fell over" in (r.exc_text or "") for r in caplog.records)


def test_the_real_probe_runs_where_a_platform_has_opengl(app) -> None:
    if QGuiApplication.platformName() in RENDER.no_gl_platforms:
        pytest.skip("this platform has no OpenGL")
    assert canvas_module._hardware_context() in (True, False)      # it answers; it does not raise


def test_the_splash_asks_the_probe_unless_it_is_told(app, monkeypatch) -> None:
    asked = []
    monkeypatch.setattr(splash_module, "opengl_available", lambda: asked.append(1) or False)
    assert IntroSplash()._canvas is None and asked == [1]
    assert IntroSplash(opengl=False)._canvas is None and asked == [1]


def test_a_canvas_that_cannot_make_its_context_is_dropped_and_the_window_draws_itself(app, monkeypatch) -> None:
    monkeypatch.setattr(GLCanvas, "isValid", lambda self: False)
    now = [0.0]
    splash = IntroSplash(opengl=True)
    splash._now = lambda: now[0]                        # type: ignore[method-assign]
    assert isinstance(splash._canvas, GLCanvas)
    now[0] = RENDER.settle_s - 0.1
    splash._on_tick()
    assert splash._canvas is not None                   # still within the time it has to come up
    now[0] = RENDER.settle_s + 0.1
    splash._on_tick()
    assert splash._canvas is None
    splash.resize(683, 360)
    frame = splash.grab().toImage()
    assert not frame.isNull() and frame.width() > 0     # it paints itself again


def test_a_canvas_that_is_valid_is_kept(app, monkeypatch) -> None:
    monkeypatch.setattr(GLCanvas, "isValid", lambda self: True)
    splash = IntroSplash(opengl=True)
    splash._now = lambda: 60.0                          # type: ignore[method-assign]
    splash._on_tick()
    assert isinstance(splash._canvas, GLCanvas)


# ---- where this machine has a GPU ----


def _live_gl_splash(app) -> IntroSplash:
    splash = IntroSplash(opengl=True)
    splash.play()
    splash.skip()
    splash._timer.stop()                                # a frame that holds still
    for _ in range(100):
        app.processEvents()
        if splash._canvas.isValid():
            break
    assert splash._canvas.isValid()
    return splash


def _gray_edges(image: QImage) -> tuple[np.ndarray, float]:
    image = image.convertToFormat(QImage.Format.Format_RGB32)
    ptr = image.constBits()
    ptr.setsize(image.sizeInBytes())
    px = np.frombuffer(ptr, dtype=np.uint8).reshape(image.height(), image.bytesPerLine())[:, : image.width() * 4]
    gray = px.reshape(image.height(), image.width(), 4)[..., :3].astype(float).mean(axis=2)
    return gray, float(np.abs(np.diff(gray, axis=1)).mean() + np.abs(np.diff(gray, axis=0)).mean())


def test_the_canvas_draws_the_very_frame_the_raster_path_draws(app) -> None:
    if not _gpu_here(app):
        pytest.skip("no hardware OpenGL on this machine")
    splash = _live_gl_splash(app)
    try:
        gpu = splash._canvas.grabFramebuffer()
        cpu = QImage(gpu.size(), QImage.Format.Format_RGB32)
        cpu.setDevicePixelRatio(splash.devicePixelRatioF())
        splash._draw(cpu)
        g, g_edges = _gray_edges(gpu)
        c, c_edges = _gray_edges(cpu)
        assert g.shape == c.shape
        assert np.abs(g - c).mean() < 3.0                       # of 255: edges and text differ in the last bits only
        assert g_edges == pytest.approx(c_edges, rel=0.05)      # multisampling keeps the edges as sharp (0.4 % measured)
        assert (255.0 - g).sum() == pytest.approx((255.0 - c).sum(), rel=0.02)   # and the ink
    finally:
        splash.close()


def test_the_canvas_fills_the_window_and_takes_no_mouse_events(app) -> None:
    if not _gpu_here(app):
        pytest.skip("no hardware OpenGL on this machine")
    splash = _live_gl_splash(app)
    try:
        splash.resize(900, 500)
        app.processEvents()
        assert splash._canvas.geometry() == splash.rect()
        assert splash._canvas.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        assert splash.childAt(QPoint(450, 250)) is None            # a click lands on the splash, not the canvas
    finally:
        splash.close()


def test_repaint_paints_at_once_and_update_waits_for_the_event_loop(app, monkeypatch) -> None:
    if not _gpu_here(app):
        pytest.skip("no hardware OpenGL on this machine")
    drawn = []
    real = IntroSplash._draw
    monkeypatch.setattr(IntroSplash, "_draw", lambda self, device: (drawn.append(1), real(self, device))[1])
    splash = _live_gl_splash(app)
    try:
        for _ in range(5):
            app.processEvents()
        drawn.clear()
        splash.update()
        assert drawn == []                                         # scheduled, not painted
        splash.repaint()
        assert len(drawn) >= 1                                     # painted before the call returned
    finally:
        splash.close()
