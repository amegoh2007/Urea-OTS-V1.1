"""The engine host — the plant stepped on its own thread and served to the console.

What it is
----------
The loop V1 ran as ``sim_task`` and ``push_task``, joined to the console server. A physics thread
pays the wall clock to the engine session in fixed 0.1 s steps at the instructor's pacing
(`ureasim.engine.session`), applies the console's commands between two ticks in arrival order,
answers trend queries from the historian, and hands the console packet to the server once a
pass, 10 times a second. The server's event loop does nothing but the network, so a long pass —
x10 pacing, a stiff transient — never delays the console's ack or its snapshot.

    console --command--> StationServer --submit--> queue --> physics thread: session.handle
    console <--ack------ StationServer <--future-- answered between two ticks
    console <--snapshot- StationServer <--publish- physics thread: session.published_state

Why commands go through the physics thread
------------------------------------------
A command changes the plant's objects — a set point, a valve, a latch — and the tick reads them.
Applied from another thread it could land halfway through a tick, and a unit read before it and a
unit read after it would see two different plants. Queued, each command is applied whole between
two ticks (`project.md` §3.6, step 1 of a tick), and its answer — accepted, or the plant's reason
for refusing it — travels back on the future the server is awaiting. A pass is paid in slices of
at most ``SLICE_S`` of wall time, the queue drained between them, so under a fast pacing a command
waits at most a slice's steps, not a whole pass's.

The slices change nothing the plant sees: the simulator keeps its owed time in integer
nanoseconds, so a pass paid in slices runs exactly the steps it runs paid at once. The pass is
capped at V1's 0.5 s before it is sliced, as V1 caps it.

Source: V1 ``backend/main.py`` ``sim_task`` (11991-12025) and ``push_task`` (12058-12070).
"""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
import time
from typing import Any, Callable, Mapping

from ureasim.data.engine import DT_S, MAX_PASS_NS
from ureasim.engine.session import EngineSession
from ureasim.net.server import StationServer

__all__ = ["PASS_S", "SLICE_S", "EngineHost"]

log = logging.getLogger(__name__)

#: One pass of the physics thread [s] — V1's ``sim_task`` sleeps ``DT`` between passes and its
#: ``push_task`` sends a packet every 0.1 s; one pass is both here.
PASS_S = DT_S

#: The longest slice of wall time paid to the plant between two drains of the command queue [s]:
#: 10 ms of wall time is 0.1 s of plant at x10 pacing, one step.
SLICE_S = 0.01
_SLICE_NS = int(SLICE_S * 1e9)


def _resolve(fut: asyncio.Future, value: Any) -> None:
    if not fut.done():
        fut.set_result(value)


def _fail(fut: asyncio.Future, exc: BaseException) -> None:
    if not fut.done():
        fut.set_exception(exc)


class EngineHost:
    """Runs one engine session for its console server."""

    def __init__(self, session: EngineSession, server: StationServer,
                 engine_name: str = "ureasim") -> None:
        self.session = session
        self.server = server
        self.engine_name = engine_name
        self._jobs: queue.SimpleQueue = queue.SimpleQueue()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._status: tuple[str, str] | None = None

    # ---- lifecycle ----

    def start(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        """Attach to the server and start the physics thread. Called on the server's event loop."""
        self._loop = loop or asyncio.get_running_loop()
        self.server.set_command_handler(self.submit, self.engine_name)
        self.server.set_history_handler(self.history)
        # A directory listing: the physics thread does not touch it, so it is read here.
        self.server.set_exercise_lister(self.session.exercises)
        self._thread = threading.Thread(target=self._run, name="engine-physics", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the physics thread after its current pass."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)

    # ---- what the server calls, on its event loop ----

    def _job(self, work: Callable[[], Any]) -> asyncio.Future:
        fut = self._loop.create_future()
        self._jobs.put((work, fut))
        return fut

    def submit(self, cmd: Mapping[str, Any], station: str) -> asyncio.Future:
        """The server's command handler: the command queued for the next gap between ticks, its
        ``(accepted, reason)`` on the returned future."""
        cmd = dict(cmd)
        return self._job(lambda: self.session.handle(cmd, station))

    def history(self, message: Mapping[str, Any]) -> asyncio.Future:
        """The server's history handler: a trend's backfill, or the recorded paths."""
        if message.get("t") == "history_paths":
            return self._job(self.session.history_paths)
        paths = message.get("paths")
        if not paths or not isinstance(paths, (list, tuple)):
            raise ValueError("a history request names its paths")
        span = float(message.get("span", 600.0))
        points = int(message.get("max_points", 800))
        end = message.get("end")
        return self._job(lambda: self.session.history(paths, span, points, end))

    # ---- the physics thread ----

    def _drain(self) -> None:
        """Apply every queued job, each whole, in arrival order."""
        while True:
            try:
                work, fut = self._jobs.get_nowait()
            except queue.Empty:
                return
            try:
                value = work()
            except Exception as exc:  # noqa: BLE001 - an engine error answers the console
                log.exception("engine job raised")
                self._loop.call_soon_threadsafe(_fail, fut, exc)
            else:
                self._loop.call_soon_threadsafe(_resolve, fut, value)

    def pay(self, elapsed_ns: int) -> int:
        """Pay ``elapsed_ns`` of wall time (capped at V1's 0.5 s) in slices, draining the queue
        between them. Returns the steps run."""
        owed = min(max(elapsed_ns, 0), MAX_PASS_NS)
        steps = 0
        while True:
            self._drain()
            piece = min(owed, _SLICE_NS)
            steps += self.session.advance(piece)
            owed -= piece
            if owed <= 0:
                self._drain()
                return steps

    def publish(self) -> None:
        """Hand this pass's packet, and any change of the engine's state, to the server."""
        packet = self.session.published_state()
        if packet:
            self._loop.call_soon_threadsafe(self.server.publish, packet, self.session.t_plant)
        status = self._engine_status(packet.get("_health") if packet else None)
        if status != self._status:
            self._status = status
            self._loop.call_soon_threadsafe(self.server.publish_status, *status)

    def _engine_status(self, health: Mapping[str, Any] | None) -> tuple[str, str]:
        """The status bar's text and level: a fault, a freeze, or the pacing the plant runs at."""
        if health is not None and not health["ok"]:
            return f"ENGINE FAULT — {health['error']}", "fault"
        if self.session.frozen:
            return "ENGINE FROZEN — the plant clock is held", "warn"
        return f"ENGINE RUNNING — {self.session.simulator.pacing}", "ok"

    def _run(self) -> None:
        last = time.monotonic_ns()
        next_pass = time.monotonic()
        while not self._stop.is_set():
            now = time.monotonic_ns()
            try:
                self.pay(now - last)
                self.publish()
            except Exception:  # noqa: BLE001 - the host must outlive a fault, as V1's loop does
                log.exception("engine pass failed")
            last = now
            next_pass += PASS_S
            delay = next_pass - time.monotonic()
            if delay < 0.0:
                next_pass = time.monotonic()     # behind: start the next pass now, not a burst
                delay = 0.0
            self._stop.wait(delay)
