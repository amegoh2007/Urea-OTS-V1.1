"""Playback state machine of the start-up intro: clock in, scene time, opacity and events out.

Plant equipment modelled: none (presentation only).
Reference document: ``ureasim/data/intro.py`` (the ``Timeline`` hold and fade).
Equations: linear opacity ramp, opacity = 1 - (now - start) / fade, clamped at zero.

Process utility
---------------
The intro is the doorway to the simulator. It plays its scene and then stops on the start button; the
operator, not a timer, decides when the plant starts. Starting the simulator takes seconds (the engine
comes up, ten screens and 393 overlay widgets are built), so after the press the splash stays up,
showing that work is in progress, and leaves only when the application says it is ready. This class owns
that logic with no Qt in it, so every path (play through, skip, press early, application slower or
faster than the operator) is tested without a display.

Phases::

    PLAYING --(scene over, or skip)--> AWAITING --(start pressed)--> STARTING
    STARTING --(application ready)--> FADING --(opacity 0)--> DONE
    STARTING --(start withdrawn)--> AWAITING

A press can be withdrawn by the application while it starts (``cancel_start``): after LOAD the operator
may choose no exercise, and the buttons are then live again, nothing started.

Events, each raised once and in this order:

``START``     the operator pressed the start button. The application starts the simulator now and
              calls ``mark_ready`` when its console is up (it may do both inside the slot).
``REVEAL``    the application is ready and the exit fade begins; show the console underneath.
``FINISHED``  the fade is complete; the splash can be closed.

A skip never starts the simulator: it only jumps to the button, so a stray key press cannot start a
plant by accident.
"""

from __future__ import annotations

from enum import Enum, auto

from ureasim.data.intro import TIMELINE
from ureasim.hmi.intro.timeline import clamp01


class Event(Enum):
    """What the sequencer tells the splash widget to announce."""

    START = auto()
    REVEAL = auto()
    FINISHED = auto()


class Phase(Enum):
    """Where playback is."""

    PLAYING = auto()
    AWAITING = auto()
    STARTING = auto()
    FADING = auto()
    DONE = auto()


class IntroSequencer:
    """Turns wall-clock seconds into scene time, window opacity and one-shot events."""

    def __init__(self) -> None:
        self._phase = Phase.PLAYING
        self._ready = False
        self._start_pending = False
        self._skipped = False
        self._now = 0.0
        self._fade_start = 0.0

    @property
    def phase(self) -> Phase:
        return self._phase

    @property
    def scene_time(self) -> float:
        """Scene clock: wall time while playing, the last frame from then on."""
        return min(self._now, TIMELINE.hold) if self._phase is Phase.PLAYING else TIMELINE.hold

    @property
    def wall_time(self) -> float:
        """Unclamped clock for idle motion while the operator or the application is busy."""
        return self._now

    @property
    def opacity(self) -> float:
        """Window opacity: 1 until the exit fade, then ramping to 0."""
        if self._phase is Phase.DONE:
            return 0.0
        if self._phase is Phase.FADING:
            return 1.0 - clamp01((self._now - self._fade_start) / TIMELINE.fade)
        return 1.0

    @property
    def skipped(self) -> bool:
        return self._skipped

    @property
    def awaiting_start(self) -> bool:
        """True while the start button is live: the scene is over and nothing has been pressed."""
        return self._phase is Phase.AWAITING

    @property
    def busy(self) -> bool:
        """True from the press until the splash is gone: the button is drawn as working."""
        return self._phase in (Phase.STARTING, Phase.FADING)

    def mark_ready(self) -> None:
        """The application has its console up. It may be called before the press (the console was
        built while the intro played); the fade then begins as soon as the start is pressed."""
        self._ready = True

    def skip(self, now: float) -> None:
        """Operator pressed a key or clicked during the scene: jump to the last frame and its button."""
        self._now = max(self._now, now)
        if self._phase is Phase.PLAYING:
            self._skipped = True
            self._phase = Phase.AWAITING

    def press_start(self, now: float) -> bool:
        """The start button was pressed. Returns whether the press was accepted.

        Process utility: only an operator who has the button on screen can press it, and only once;
        a second press while the plant is starting must not start it twice.
        """
        self._now = max(self._now, now)
        if self._phase is not Phase.AWAITING:
            return False
        self._phase = Phase.STARTING
        self._start_pending = True
        return True

    def cancel_start(self) -> bool:
        """The application did not start the simulator from the press: the buttons are live again.
        Returns whether the press was withdrawn.

        Process utility: after LOAD the operator may choose no exercise (Cancel, or nothing to load), and
        a plant must not start that nobody asked for; the operator presses 100% LOAD or LOAD again. Only a
        press that is starting and whose console is not yet ready can be withdrawn.
        """
        if self._phase is not Phase.STARTING or self._ready:
            return False
        self._phase = Phase.AWAITING
        self._start_pending = False
        return True

    def advance(self, now: float) -> list[Event]:
        """Move the clock to ``now`` seconds and return the events newly raised."""
        events: list[Event] = []
        self._now = max(self._now, now)

        if self._phase is Phase.PLAYING and self._now >= TIMELINE.hold:
            self._phase = Phase.AWAITING

        if self._phase is Phase.STARTING:
            if self._start_pending:
                self._start_pending = False
                events.append(Event.START)
                # The slot behind START may block for as long as the simulator takes to start; the fade
                # begins on the next call, from that later clock, so the build never swallows it.
            elif self._ready:
                self._phase = Phase.FADING
                self._fade_start = self._now
                events.append(Event.REVEAL)
        elif self._phase is Phase.FADING and self.opacity <= 0.0:
            self._phase = Phase.DONE
            events.append(Event.FINISHED)
        return events
