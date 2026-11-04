"""The hand-over from the start-up intro to the console: the 100% LOAD press starts the plant.

Plant equipment modelled
------------------------
None. This module sequences the application; it computes no process quantity and reads no engine value
except that a packet has arrived.

Reference documents
-------------------
* ``project.md`` decision 149 (one plant, one local console) and the decision that holds the plant until
  the operator presses 100% LOAD.
* ``ureasim/data/intro.py``: the start key, the engine command each key sends, the status texts and the
  waits (``START_COMMANDS``, ``STARTUP``).
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
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Mapping
from typing import Any

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from ureasim.data.intro import START_COMMANDS, STARTUP

__all__ = ["StartupController"]

log = logging.getLogger(__name__)


class StartupController(QObject):
    """Builds the console, connects it and releases the held plant when the intro asks to start.

    ``splash`` is the intro window (``set_status``, ``repaint``, ``mark_ready``, ``raise_``, and the
    signals ``start_requested`` and ``reveal``); ``bridge`` is the console's link to the engine;
    ``make_window`` builds the hidden console on that bridge; ``engine_ready`` is set once the engine
    serves and ``engine_alive`` tells whether the thread building it still runs.
    """

    #: The engine never started: the application cannot run and should exit with this reason.
    failed = pyqtSignal(str)

    def __init__(self, *, splash: Any, bridge: Any, make_window: Callable[[], Any],
                 engine_ready: threading.Event, engine_alive: Callable[[], bool],
                 host: str, port: int, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._splash = splash
        self._bridge = bridge
        self._make_window = make_window
        self._engine_ready = engine_ready
        self._engine_alive = engine_alive
        self._host = host
        self._port = port

        self.window: Any = None
        self._command: Mapping[str, Any] = {}
        self._cmd_id = 0
        self._sent = False
        self._done = False
        self._engine_deadline = 0.0

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
        """The start button was pressed: build the console, then wait for the engine."""
        self._command = dict(START_COMMANDS[key])
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
        self._packet_deadline.start(int(STARTUP.packet_timeout_s * 1000))
        self._bridge.connect_to(self._host, self._port)

    def _on_status(self, _text: str, _level: str) -> None:
        """Send the release once the link is up, again after a reconnect, never twice on one link."""
        if self._done:
            return
        if not self._bridge.connected:
            self._sent = False
            return
        if not self._sent:
            self._cmd_id = self._bridge.send_command(self._command)
            self._sent = bool(self._cmd_id)
            if self._sent:
                self._say(STARTUP.releasing)

    def _on_result(self, cmd_id: int, ok: bool, reason: str) -> None:
        if cmd_id == self._cmd_id and not ok and not self._done:
            self._give_up(f"the engine refused the start: {reason}")

    def _on_snapshot(self, state: Mapping[str, Any]) -> None:
        """The first packet is the plant running: nothing is published while it is held."""
        if state and not self._done:
            self._finish()

    def _on_packet_timeout(self) -> None:
        self._give_up(f"no packet from the engine within {STARTUP.packet_timeout_s:g} s")

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
