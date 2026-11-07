"""The hand-over from the start-up intro to the console: the 100% LOAD or LOAD press starts the plant.

Plant equipment modelled
------------------------
None. This module sequences the application; it computes no process quantity and reads no engine value
except that a packet has arrived, the engine's answers to its commands and the names of its saved exercises.

Reference documents
-------------------
* ``project.md`` decision 149 (one plant, one local console), decision 166 (the plant held until the
  operator presses 100% LOAD), decision 169 (a plant restored while held publishes its rehearsed first
  tick) and decision 171 (the LOAD button: the plant started from a saved exercise).
* ``ureasim/data/intro.py``: the start keys, the engine command each key sends, the restore command, the
  status texts and the waits (``START_OPTIONS``, ``START_COMMANDS``, ``RESTORE_COMMAND``, ``STARTUP``).
* CLAUDE.md section 4a: the engine owns the plant, the console owns nothing.

Equations
---------
None.

Process utility
---------------
A trainee who has not pressed 100% LOAD has not started a plant, so the engine is built and held at its
design seed while the intro plays (``run.py``): its plant clock does not move, no trend fills and no
packet is published. The press releases that hold with the engine's own ``freeze`` command, the same
one the instructor's RUN button sends, so the engine learns nothing new. The plant therefore starts
at the instant the operator chooses and from the 1750 MTPD design seed, as every start did before.

Sequence after the press, each step waiting on the one before::

    build the console (hidden)  ->  wait for the engine  ->  connect the bridge
        ->  send the release  ->  first packet  ->  splash.mark_ready()  ->  the console is shown

The console is connected only at the press. A bridge connected to a held engine receives no packet,
and the first tick after the release is cold (2.3 s on the development machine), so the bridge waits
`FIRST_PACKET_STALE_MS` (30 s) for its first packet before the strict five-second watchdog applies;
this controller's own wait is longer, so the bridge's watchdog speaks first (a test pins it).

When a step fails or runs out of time the console is shown anyway: its status bar already carries the
bridge's and the engine's own words (a refused command, a lost link), which is where an operator looks,
and an intro that waits for ever would hide them. Only an engine that never started ends the
application, as it always did. The engine's thread is watched from the moment the controller exists,
not from the press, so a port held by another instance ends the application within a second of
launch, as it did before the intro, and the operator is not left to press 100% LOAD first.

The start from a saved exercise (LOAD)
--------------------------------------
LOAD starts the same plant from an exercise the operator chooses among those the engine has saved::

    build the console (hidden)  ->  wait for the engine  ->  connect the bridge  ->  ask for the exercises
        ->  the chooser over the intro  ->  restore the chosen one  ->  its acceptance  ->  send the release
        ->  its acceptance  ->  the next packet  ->  splash.mark_ready()  ->  the console is shown

A plant restored while it is held publishes its rehearsed first tick (decision 169), so a packet that
arrives before the release is accepted is not the plant running and does not end the wait. The release
goes out only once the engine has accepted the exercise. A refused exercise opens the chooser again with
the engine's reason, the plant still held and untouched (a refused restore installs nothing), so the
operator chooses another or cancels. Cancel, or an engine with no saved exercise, takes the intro back to
its two buttons with the reason on its status line (``splash.rearm``), nothing started; the console and
its link stay up, so the next press, 100% LOAD or LOAD, goes on from the link (both decided by the process
engineer on 2026-11-06). The wait for the engine stops while the chooser is open or the buttons are
waiting (the operator's time is not the engine's) and starts again, whole, at the choice or the press.
Meanwhile the held engine is silent and the bridge's first-packet watchdog may drop and reconnect the
link, so each step's message is sent once per link and again on the next: a list asked twice, an
exercise restored twice or a release sent twice leaves the plant where one of them would.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from enum import Enum, auto
from typing import Any

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from ureasim.data.intro import RESTORE_COMMAND, START_COMMANDS, START_OPTIONS, STARTUP
from ureasim.hmi.exercise_chooser import open_chooser

__all__ = ["StartupController"]

log = logging.getLogger(__name__)

#: The operator's chooser: shown with the engine's exercise names and a note (empty, or the engine's refusal
#: of the exercise chosen before), it calls back with a name or None.
Chooser = Callable[[Sequence[str], Callable[[str | None], None], str], Any]

_RESTORES = {option.key: option.restores_exercise for option in START_OPTIONS}


class _Step(Enum):
    """Where the start from a saved exercise (LOAD) is; the 100% LOAD start has no steps."""

    LIST = auto()       # the saved exercises asked for
    CHOOSE = auto()     # the chooser is open: nothing is sent and no wait runs
    RESTORE = auto()    # the chosen exercise sent, the engine's answer awaited
    RELEASE = auto()    # the release sent, the engine's answer awaited
    RUNNING = auto()    # the release accepted: the next packet is the plant running
    IDLE = auto()       # no exercise chosen: back at the intro's buttons, nothing sent, no wait running


class StartupController(QObject):
    """Builds the console, connects it and releases the held plant when the intro asks to start.

    ``splash`` is the intro window (``set_status``, ``repaint``, ``mark_ready``, ``rearm``, ``raise_``,
    and the signals ``start_requested`` and ``reveal``); ``bridge`` is the console's link to the engine;
    ``make_window`` builds the hidden console on that bridge; ``engine_ready`` is set once the engine
    serves and ``engine_alive`` tells whether the thread building it still runs. ``choose`` shows the
    engine's exercise names to the operator after LOAD and calls back with the one chosen or None; by
    default the chooser dialog opens over the intro (a test hands in its own, as the instructor's panel
    takes its own ``confirm``).
    """

    #: The engine never started: the application cannot run and should exit with this reason.
    failed = pyqtSignal(str)

    def __init__(self, *, splash: Any, bridge: Any, make_window: Callable[[], Any],
                 engine_ready: threading.Event, engine_alive: Callable[[], bool],
                 host: str, port: int, choose: Chooser | None = None,
                 parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._splash = splash
        self._bridge = bridge
        self._make_window = make_window
        self._engine_ready = engine_ready
        self._engine_alive = engine_alive
        self._host = host
        self._port = port
        self._choose = choose or self._open_chooser

        self.window: Any = None
        self._command: Mapping[str, Any] = {}
        self._cmd_id = 0
        self._sent = False
        self._done = False
        self._engine_deadline = 0.0
        self._step: _Step | None = None           # None: the 100% LOAD start; a step: the LOAD start
        self._exercise: str | None = None
        self._names: list[str] = []               # the engine's exercises, offered again after a refusal
        self._listening = False                   # the exercise list's signal is connected

        self._poll = QTimer(self)
        self._poll.setInterval(STARTUP.poll_ms)
        self._poll.timeout.connect(self._poll_engine)
        self._packet_deadline = QTimer(self)
        self._packet_deadline.setSingleShot(True)
        self._packet_deadline.timeout.connect(self._on_packet_timeout)
        self._watch = QTimer(self)
        self._watch.setInterval(STARTUP.watch_ms)
        self._watch.timeout.connect(self._watch_engine)
        self._watch.start()

        splash.start_requested.connect(self.begin)
        splash.reveal.connect(self._reveal)

    # -- the steps ----------------------------------------------------------------------------

    def begin(self, key: str) -> None:
        """A start button was pressed: build the console, then wait for the engine. Pressed again after
        LOAD went back to the buttons, the console and its link are already up: go on from the link."""
        self._command = dict(START_COMMANDS[key])
        self._step = _Step.LIST if _RESTORES[key] else None
        if self.window is not None:
            self._sent = False
            self._packet_deadline.start(int(STARTUP.packet_timeout_s * 1000))
            if self._step is not None:
                self._send_step()
            elif self._bridge.connected:
                self._send_release()
            return
        self._say(STARTUP.building)
        self.window = self._make_window()          # blocks for seconds; the status above is on screen
        self._say(STARTUP.engine)
        self._engine_deadline = time.monotonic() + STARTUP.engine_timeout_s
        self._poll.start()
        self._poll_engine()

    def _watch_engine(self) -> None:
        """Before the press: end the application if the engine's thread died without serving."""
        if self._engine_ready.is_set():
            self._watch.stop()
        elif not self._engine_alive():
            self._watch.stop()
            self._engine_failed()

    def _poll_engine(self) -> None:
        if self._engine_ready.is_set():
            self._poll.stop()
            self._connect()
        elif not self._engine_alive() or time.monotonic() > self._engine_deadline:
            self._poll.stop()
            self._engine_failed()

    def _engine_failed(self) -> None:
        reason = "the engine did not start"
        log.error(reason)
        self._say(reason)
        self.failed.emit(reason)

    def _connect(self) -> None:
        self._say(STARTUP.connecting)
        self._bridge.status.connect(self._on_status)
        self._bridge.command_result.connect(self._on_result)
        self._bridge.snapshot.connect(self._on_snapshot)
        if self._step is not None:
            self._bridge.exercises_received.connect(self._on_exercises)
            self._listening = True
        self._packet_deadline.start(int(STARTUP.packet_timeout_s * 1000))
        self._bridge.connect_to(self._host, self._port)

    def _on_status(self, _text: str, _level: str) -> None:
        """Send the release once the link is up, again after a reconnect, never twice on one link; after
        LOAD, the message of the step it is at."""
        if self._done:
            return
        if not self._bridge.connected:
            self._sent = False
            return
        if self._step is not None:
            self._send_step()
            return
        self._send_release()

    def _send_release(self) -> None:
        """The release, once on this link."""
        if not self._sent:
            self._cmd_id = self._bridge.send_command(self._command)
            self._sent = bool(self._cmd_id)
            if self._sent:
                self._say(STARTUP.releasing)

    def _on_result(self, cmd_id: int, ok: bool, reason: str) -> None:
        if self._step is not None:
            self._on_load_result(cmd_id, ok, reason)
            return
        if cmd_id == self._cmd_id and not ok and not self._done:
            self._give_up(f"the engine refused the start: {reason}")

    def _on_snapshot(self, state: Mapping[str, Any]) -> None:
        """The first packet is the plant running: nothing is published while it is held. After LOAD the
        restored plant publishes its rehearsed first tick while held (decision 169), so only a packet that
        follows the release's acceptance counts."""
        if self._step is not None and self._step is not _Step.RUNNING:
            return
        if state and not self._done:
            self._finish()

    def _on_packet_timeout(self) -> None:
        if self._step is _Step.LIST:
            self._give_up(f"no exercise list from the engine within {STARTUP.packet_timeout_s:g} s")
            return
        self._give_up(f"no packet from the engine within {STARTUP.packet_timeout_s:g} s")

    # -- the start from a saved exercise (LOAD) -------------------------------------------------

    def _go(self, step: _Step) -> None:
        """Move on to ``step``: its message goes out now if the link is up, else when it next comes up."""
        self._step = step
        self._sent = False
        self._send_step()

    def _send_step(self) -> None:
        """The step's message, once on this link: the list request, the chosen exercise or the release.
        Nothing while the chooser is open."""
        if self._sent or not self._bridge.connected:
            return
        if self._step is _Step.LIST:
            self._sent = bool(self._bridge.request_exercises())
            if self._sent:
                self._say(STARTUP.listing)
        elif self._step is _Step.RESTORE:
            self._cmd_id = self._bridge.send_command({**RESTORE_COMMAND, "name": self._exercise})
            self._sent = bool(self._cmd_id)
        elif self._step in (_Step.RELEASE, _Step.RUNNING):
            self._send_release()

    def _on_exercises(self, names: Sequence[str], reason: str) -> None:
        """The engine's saved exercises: the chooser opens over the intro and the wait for the engine stops.
        None to choose from takes the intro back to its buttons, the status saying so."""
        if self._done or self._step is not _Step.LIST:
            return
        self._packet_deadline.stop()
        names = [str(n) for n in names]
        if not names:
            self._back_to_buttons(f"{STARTUP.no_exercises} ({reason})" if reason else STARTUP.no_exercises)
            return
        self._names = names
        self._step = _Step.CHOOSE
        self._say(STARTUP.choosing)
        self._choose(names, self._on_choice, "")

    def _on_choice(self, name: str | None) -> None:
        """The operator's answer: the exercise to restore, or none (Cancel), which goes back to the buttons."""
        if self._done or self._step is not _Step.CHOOSE:
            return
        if name is None:
            self._back_to_buttons(STARTUP.no_choice)
            return
        self._exercise = name
        self._say(STARTUP.restoring.format(name=name))
        self._packet_deadline.start(int(STARTUP.packet_timeout_s * 1000))
        self._go(_Step.RESTORE)

    def _on_load_result(self, cmd_id: int, ok: bool, reason: str) -> None:
        """The engine's answer to the restore, then to the release."""
        if self._done or cmd_id != self._cmd_id:
            return
        if self._step is _Step.RESTORE:
            if ok:
                self._go(_Step.RELEASE)
            else:
                self._offer_again(STARTUP.refused.format(name=self._exercise, reason=reason))
        elif self._step is _Step.RELEASE:
            if ok:
                self._step = _Step.RUNNING
            else:
                self._give_up(f"the engine refused the start: {reason}")

    def _offer_again(self, note: str) -> None:
        """A refused exercise: the chooser opens again over the intro with the engine's reason, the plant
        still held and untouched, and the wait stops again while the operator decides."""
        log.warning(note)
        self._packet_deadline.stop()
        self._exercise = None
        self._step = _Step.CHOOSE
        self._say(note)
        self._choose(self._names, self._on_choice, note)

    def _back_to_buttons(self, text: str) -> None:
        """No exercise to restore: the intro's buttons are live again with ``text`` on its status line, and
        nothing starts until the operator presses one (``begin`` goes on from the link). The plant stays
        held and untouched; the wait for the engine stops."""
        self._packet_deadline.stop()
        self._step = _Step.IDLE
        self._exercise = None
        self._splash.rearm(text)

    def _open_chooser(self, names: Sequence[str], done: Callable[[str | None], None], note: str) -> None:
        """The chooser dialog over the intro, not blocking the event loop (``hmi/exercise_chooser.py``)."""
        open_chooser(self._splash, names, done, note)

    # -- ending -------------------------------------------------------------------------------

    def _give_up(self, reason: str) -> None:
        """Show the console anyway, with the reason in the log and on the intro's last line."""
        log.error(reason)
        self._say(reason)
        self._finish()

    def _finish(self) -> None:
        self._done = True
        self._packet_deadline.stop()
        for signal, slot in ((self._bridge.status, self._on_status),
                             (self._bridge.command_result, self._on_result),
                             (self._bridge.snapshot, self._on_snapshot)):
            signal.disconnect(slot)
        if self._listening:
            self._bridge.exercises_received.disconnect(self._on_exercises)
            self._listening = False
        self._splash.mark_ready()

    def _reveal(self) -> None:
        """The intro asks for the console: show it and keep the intro's fade on top."""
        if self.window is not None:
            self.window.show()
        self._splash.raise_()

    def _say(self, text: str) -> None:
        """The intro's one live line, painted now: the next step may block the event loop."""
        self._splash.set_status(text)
        self._splash.repaint()
