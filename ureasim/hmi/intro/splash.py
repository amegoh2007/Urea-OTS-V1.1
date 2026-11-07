"""The start-up intro window: plays the scene, waits on the start button, fades out.

Plant equipment modelled: none (presentation only).
Reference document: ``ureasim/data/intro.py`` (tick period, the start option); CLAUDE.md section 4a (the
console renders and emits, it owns no plant state).
Equations: none.

Process utility
---------------
Shown before the main console. It never reads the plant, so it cannot show a stale value; it shows one
line of status text that the application passes in (``set_status``), and nothing else live.

The frame is drawn by the window itself, or, where the machine has a GPU to give it, by a ``GLCanvas`` child
that fills the window (``canvas.py``, handoff A-26): the same painter and the same operations either way, so
the picture is the same and only the cost of drawing it moves. ``opengl`` forces the choice; left as None
it is the canvas module's own test of the machine.

The scene ends on two buttons. Pressing "100% LOAD" (click, or Enter / Space) raises
``start_requested("load_100")``; clicking "LOAD" raises ``start_requested("load_exercise")`` (the start
from a saved exercise; it has no key, so Enter keeps meaning 100% LOAD). The application starts the
simulator and calls ``mark_ready`` when the console is up; the splash then raises ``reveal`` (show the
console now, it is underneath) and fades out; or it calls ``rearm`` (no exercise was chosen) and the
buttons are live again. A key press or click *before* the buttons are on screen only skips ahead to
them. One press is taken at a time, whichever button it was.

Typical use (see INTEGRATION.md for the full recipe)::

    splash = IntroSplash()
    splash.start_requested.connect(start_simulator)   # builds the console, then calls splash.mark_ready()
    splash.reveal.connect(show_console)
    splash.finished.connect(splash.deleteLater)
    splash.play()
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import QCoreApplication, QElapsedTimer, QEvent, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QGuiApplication, QKeyEvent, QMouseEvent, QPaintDevice, QPainter, QPaintEvent
from PyQt6.QtWidgets import QWidget

from ureasim.data.intro import RENDER, START_OPTION, STAGE, STRINGS, TICK_MS
from ureasim.hmi.intro.canvas import GLCanvas, opengl_available
from ureasim.hmi.intro.painter import IntroPainter
from ureasim.hmi.intro.scene import ButtonState, ButtonStates, build_frame, button_at, to_design, view_rect
from ureasim.hmi.intro.sequencer import Event, IntroSequencer, Phase

log = logging.getLogger(__name__)

# Share of the screen the windowed intro may occupy, so it never overflows a small laptop panel.
_SCREEN_FILL = 0.92

# Keys that press the 100% LOAD button once it is on screen; any key skips the scene before that.
_START_KEY_CODES = frozenset(k.value for k in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space))


class IntroSplash(QWidget):
    """Frameless window that plays the intro, then raises ``start_requested``, ``reveal``, ``finished``."""

    start_requested = pyqtSignal(str)
    reveal = pyqtSignal()
    finished = pyqtSignal()

    def __init__(self, parent: QWidget | None = None, *, fullscreen: bool = False,
                 opengl: bool | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self._fullscreen = fullscreen
        self._seq = IntroSequencer()
        self._painter = IntroPainter()
        self._painter.warm_up()  # the font database and the logo, before the window is on screen
        self._status = ""
        self._hover: str | None = None          # the key of the button under the pointer
        self._start_key = START_OPTION.key      # the key of the button pressed
        self._clock = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._on_tick)
        self._canvas: GLCanvas | None = None
        if opengl_available() if opengl is None else opengl:
            self._canvas = GLCanvas(self, self._draw)

    # -- application-facing API -------------------------------------------------------------

    def play(self) -> None:
        """Show the window, centred (or full screen) and start the clock."""
        if self._fullscreen:
            self.showFullScreen()
        else:
            self._size_and_centre()
            self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()
        self._clock.start()
        self._timer.start()

    def set_status(self, text: str) -> None:
        """The one line of live text: what the application is doing while the intro waits."""
        self._status = text
        self.update()

    def mark_ready(self) -> None:
        """The simulator is started and the console is built; the exit fade may begin.

        May be called before the start is pressed (the console was built while the intro played); the
        fade then begins at the press.
        """
        self._seq.mark_ready()

    def skip(self) -> None:
        """Jump to the last frame and its button. Never starts the simulator."""
        self._seq.skip(self._now())

    def rearm(self, status: str = "") -> None:
        """The press did not start the simulator (after LOAD the operator chose no exercise): the buttons are
        live again, ``status`` on the status line, and nothing starts until the operator presses one."""
        if self._seq.cancel_start():
            self._status = status
            self.update()

    # -- input ------------------------------------------------------------------------------

    def _key(self, code: int) -> None:
        """A key was pressed: skip the scene, or press the 100% LOAD button once it is live."""
        if self._seq.phase is Phase.PLAYING:
            self.skip()
        elif code in _START_KEY_CODES:
            self._press_start(START_OPTION.key)

    def _click_at(self, x_px: float, y_px: float) -> None:
        """A click at a widget pixel: skip the scene, or press the start button under it."""
        if self._seq.phase is Phase.PLAYING:
            self.skip()
        elif self._seq.awaiting_start and (key := self._button_under(x_px, y_px)) is not None:
            self._press_start(key)

    def _button_under(self, x_px: float, y_px: float) -> str | None:
        """The key of the start button at a widget pixel, or None."""
        w, h = float(self.width()), float(self.height())
        dx, dy = to_design(x_px, y_px, view_rect(w, h), w, h)
        return button_at(dx, dy)

    def _set_hover(self, key: str | None) -> None:
        """The button under the pointer (its key), or None."""
        if key != self._hover:
            self._hover = key
            self.setCursor(Qt.CursorShape.PointingHandCursor if key is not None else Qt.CursorShape.ArrowCursor)
            self.update()

    def _press_start(self, key: str) -> None:
        """A start button was pressed; the sequencer takes one press, and its key is the one announced."""
        if self._seq.press_start(self._now()):
            self._start_key = key
            self._set_hover(None)
            self.update()

    # -- internals --------------------------------------------------------------------------

    def _now(self) -> float:
        return self._clock.nsecsElapsed() / 1.0e9

    def _size_and_centre(self) -> None:
        screen = QGuiApplication.primaryScreen()
        avail = screen.availableGeometry() if screen is not None else None
        w, h = int(STAGE.width), int(STAGE.height)
        if avail is not None:
            fit = min(1.0, _SCREEN_FILL * avail.width() / w, _SCREEN_FILL * avail.height() / h)
            w, h = int(w * fit), int(h * fit)
        self.resize(w, h)
        if avail is not None:
            self.move(avail.x() + (avail.width() - w) // 2, avail.y() + (avail.height() - h) // 2)

    def _on_tick(self) -> None:
        for event in self._seq.advance(self._now()):
            if event is Event.START:
                self._status = STRINGS.starting  # the application may replace it from its slot
                self.repaint()  # draw the working state now: the slot below may block for seconds
                self.start_requested.emit(self._start_key)
            elif event is Event.REVEAL:
                self.reveal.emit()
            elif event is Event.FINISHED:
                self._timer.stop()
                self.hide()
                self.finished.emit()
                return
        if self._seq.phase is Phase.FADING:
            self.setWindowOpacity(self._seq.opacity)
        if self._canvas is not None and not self._canvas.isValid() and self._now() > RENDER.settle_s:
            self._drop_canvas()
        self.update()

    def _drop_canvas(self) -> None:
        """The canvas could not make its OpenGL context: the window draws itself from here on."""
        log.warning("the intro's OpenGL canvas is not valid; drawing on the CPU")
        self._canvas.hide()
        self._canvas.deleteLater()
        self._canvas = None

    def _button_state(self) -> ButtonStates:
        """Both buttons working once one is pressed; otherwise the one under the pointer lit."""
        if self._seq.busy:
            return ButtonState.BUSY
        return {} if self._hover is None else {self._hover: ButtonState.HOVER}

    # -- Qt overrides -----------------------------------------------------------------------

    def _draw(self, device: QPaintDevice) -> None:
        """One frame on ``device``: this window, or the canvas that stands in for it."""
        w, h = float(self.width()), float(self.height())
        view = view_rect(w, h)
        ops = build_frame(
            self._seq.scene_time, view, status=self._status, wall=self._seq.wall_time, button=self._button_state()
        )
        p = QPainter(device)
        self._painter.paint(p, ops, view, w, h)
        p.end()

    def paintEvent(self, event: QPaintEvent | None) -> None:  # noqa: N802
        if self._canvas is None:
            self._draw(self)

    def update(self) -> None:  # noqa: A003
        """Ask for a repaint of whatever draws the frame: the canvas when there is one."""
        if self._canvas is not None:
            self._canvas.update()
        else:
            super().update()

    def repaint(self) -> None:
        """Paint now, because the application is about to block the event loop for seconds.

        A ``QOpenGLWidget`` renders when its window's update request is delivered, not inside its own
        ``repaint()`` (measured: no frame is drawn by it), so with a canvas the request is delivered here.
        """
        if self._canvas is not None:
            self._canvas.update()
            QCoreApplication.sendPostedEvents(self, QEvent.Type.UpdateRequest)
        else:
            super().repaint()

    def resizeEvent(self, event) -> None:  # noqa: N802, ANN001
        if self._canvas is not None:
            self._canvas.setGeometry(self.rect())
        super().resizeEvent(event)

    def keyPressEvent(self, event: QKeyEvent | None) -> None:  # noqa: N802
        if event is not None:
            self._key(event.key())

    def mousePressEvent(self, event: QMouseEvent | None) -> None:  # noqa: N802
        if event is not None and event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            self._click_at(pos.x(), pos.y())

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:  # noqa: N802
        if event is not None:
            pos = event.position()
            self._set_hover(self._button_under(pos.x(), pos.y()) if self._seq.awaiting_start else None)

    def leaveEvent(self, event) -> None:  # noqa: N802, ANN001
        self._set_hover(None)

    def closeEvent(self, event) -> None:  # noqa: N802, ANN001
        self._timer.stop()
        super().closeEvent(event)
