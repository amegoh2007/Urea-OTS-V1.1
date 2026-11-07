"""Console server — the engine's end of the link to its console.

What it is
----------
An asyncio TCP server on the loopback interface that sends the plant state to the console and
passes the console's commands to the engine. Pure Python: **no Qt anywhere**, because the
engine runs headless — physics and presentation share no object, and the test suites and the
Phase 7 runners drive the engine with no display.

    engine  --snapshot-->  StationServer  --snapshot-->  the local console
    engine  <--command---  StationServer  <--command---  the local console

One console (decided 2026-10-22, `project.md` decision 149)
-----------------------------------------------------------
The simulator is a single-console application: one engine and one console on one machine
(``python run.py``). The server binds the loopback interface and admits only a console on its
own machine; it checks no role, no token and no unit assignment, and passes every command to
the engine. Those were the multi-station deployment's (decisions 72, 124 and 125, handoffs A-2
and A-8) and were removed with it.

A console that reconnects can hold two connections for a moment, its old one not yet noticed
closed; the server serves every connection that has said `hello`, so the new one is never
refused for the old one's sake.

Commands reach the engine in arrival order
------------------------------------------
The engine host (`ureasim.net.engine_host`) steps the plant on its own thread and applies each
command between two ticks. Its handler therefore answers with an awaitable; the server sends the
ack — and echoes the audit event — when the engine has answered, so a refusal's reason is the
plant's, never a timeout's. A handler that answers at once (a test's, or none attached) is taken
as it is.

A silent engine's last packet is not replayed (handoff A-28, decision 172)
--------------------------------------------------------------------------
A console that connects is sent the last packet and engine status at once, so it is not blank until
the next publish. That packet is a tenth of a second old while the engine runs, and while it is
frozen, since a held plant still publishes every pass. An engine that has stopped publishing — a
physics pass longer than the console's watchdog, or its thread dead — would otherwise put its last
values back on the console as live after every watchdog blank. So a packet older than
``SNAPSHOT_REPLAY_MAX_AGE_S`` of wall-clock time is not replayed: the console gets an empty snapshot
and an ENGINE SILENT fault in place of the stored status, which the next publish restores. An engine
that has never published (the plant held behind the start-up intro) is answered as before.

History and the exercise list
-----------------------------
A `history` or `history_paths` request goes to the history handler the host attaches, answered
the same way; an `exercise_list` request is answered from the exercise lister the host attaches.

Back-pressure
-------------
A console whose socket cannot keep up would otherwise grow an unbounded write queue and
eventually take the engine's memory with it. Each connection therefore drops snapshots it
has not managed to flush: a console that falls behind sees the *latest* plant state when it
catches up, never a backlog of stale ones. Commands and acks are never dropped — losing an
operator action is not acceptable, losing a frame of a 10 Hz animation is.
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import ipaddress
import logging
import math
import time
from typing import Any, Callable, Mapping

from ureasim.data.engine import SNAPSHOT_REPLAY_MAX_AGE_S
from ureasim.net import protocol
from ureasim.net.protocol import FrameReader, Kind, ProtocolError

log = logging.getLogger(__name__)

#: Default listening port. Chosen outside the registered range and away from V1's 8000.
DEFAULT_PORT = 8765
#: The loopback interface: the engine serves the console on its own machine only.
DEFAULT_HOST = "127.0.0.1"

#: How many unflushed snapshot frames a slow console may accumulate before the server
#: starts dropping them for that connection. One in flight plus one queued is enough to keep
#: a healthy console saturated without letting a sick one build a backlog.
MAX_QUEUED_SNAPSHOTS = 2

#: Command handler signature: it receives the command dict and the console's name, and
#: returns ``(accepted, reason)``, or an awaitable of it.
CommandHandler = Callable[[Mapping[str, Any], str], Any]

#: History handler signature: it receives the request message and returns the historian's answer
#: (or an awaitable of it), raising ``ValueError`` for a request it cannot answer.
HistoryHandler = Callable[[Mapping[str, Any]], Any]


def _finite(obj: Any) -> Any:
    """``obj`` with every non-finite float replaced by None: JSON has no NaN, and a console shows
    None as ``--``, which is what a value the engine could not compute should read."""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _finite(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_finite(v) for v in obj]
    return obj


def _is_loopback(host: str) -> bool:
    """True when `host` is this machine: a loopback address (127.0.0.0/8, ::1), or IPv4 loopback
    mapped into IPv6."""
    try:
        address = ipaddress.ip_address(host.split("%")[0])
    except ValueError:
        return False
    mapped = getattr(address, "ipv4_mapped", None)
    return address.is_loopback or (mapped is not None and mapped.is_loopback)


class _Station:
    """One console connection."""

    def __init__(self, writer: asyncio.StreamWriter, peer: str, host: str = ""):
        self.writer = writer
        self.peer = peer
        #: The peer's address, without its port: a loopback address is this machine.
        self.host = host
        self.name = peer
        self.ready = False              # True once `hello` has been accepted
        self.silenced = False           # True once told the engine is silent, until the next publish
        self.dropped = 0                # snapshots skipped for back-pressure
        self._queued = 0

    def send(self, message: Mapping[str, Any]) -> None:
        """Queue a message. Never raises on a dead socket — the reader task notices."""
        try:
            self.writer.write(protocol.encode(message))
        except (ProtocolError, RuntimeError, ConnectionError) as exc:  # pragma: no cover
            log.debug("send to %s failed: %s", self.peer, exc)

    def send_snapshot(self, frame: bytes) -> None:
        """Write a pre-encoded snapshot, dropping it if this console is behind.

        The transport's own buffer is the measure of "behind": if bytes are still waiting
        to go out, this console is not keeping up and another frame would only deepen the
        backlog. It will receive the next one it can actually take.
        """
        transport = self.writer.transport
        if transport is None or transport.is_closing():
            return
        if self.writer.transport.get_write_buffer_size() > 0:
            self._queued += 1
            if self._queued > MAX_QUEUED_SNAPSHOTS:
                self.dropped += 1
                return
        else:
            self._queued = 0
        try:
            self.writer.write(frame)
        except (RuntimeError, ConnectionError) as exc:  # pragma: no cover
            log.debug("snapshot to %s failed: %s", self.peer, exc)

    def describe(self) -> str:
        return f"{self.name} ({self.peer})"


class StationServer:
    """Serves one simulation to its local console.

    Parameters
    ----------
    command_handler
        Called for each command with ``(cmd, console_name)``. Returns ``(accepted, reason)``.
        The engine owns the decision: a pump start refused by a latched trip is the engine's
        answer, and it must reach the operator with its reason.
    engine_name
        Reported in `welcome`, so a console can tell which engine build it is attached to.
    clock
        The wall clock a published packet's age is measured on [s]: monotonic, so neither the
        plant's own clock, which a frozen plant holds, nor a change of the system time moves it.
        A test passes its own.
    """

    def __init__(self, command_handler: CommandHandler | None = None,
                 engine_name: str = "unattached",
                 clock: Callable[[], float] = time.monotonic):
        self._stations: set[_Station] = set()
        self._command_handler = command_handler
        self._history_handler: HistoryHandler | None = None
        self._exercise_lister: Callable[[], list[str]] | None = None
        self._engine_name = engine_name
        self._server: asyncio.AbstractServer | None = None
        self._seq = 0
        self._latest: dict[str, Any] = {}
        self._latest_t_plant = 0.0
        self._clock = clock
        #: When the engine last published, on `clock`; None before its first publish.
        self._latest_at: float | None = None
        self._status: tuple[str, str] | None = None

    # ----------------------------------------------------------------------------------
    # Lifecycle
    # ----------------------------------------------------------------------------------

    async def start(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> int:
        """Bind and begin serving. Returns the port actually bound.

        Passing ``port=0`` binds an ephemeral port and returns it, which is how the tests
        avoid fighting over a fixed number.
        """
        self._server = await asyncio.start_server(self._serve_client, host, port)
        bound = self._server.sockets[0].getsockname()[1]
        log.info("console server listening on %s:%d", host, bound)
        return bound

    async def stop(self) -> None:
        """Close every connection and stop listening."""
        for station in list(self._stations):
            with contextlib.suppress(Exception):
                station.writer.close()
        self._stations.clear()
        if self._server is not None:
            self._server.close()
            with contextlib.suppress(Exception):
                await self._server.wait_closed()
            self._server = None

    @property
    def station_count(self) -> int:
        """Connections that have completed the handshake."""
        return sum(1 for s in self._stations if s.ready)

    # ----------------------------------------------------------------------------------
    # Engine side
    # ----------------------------------------------------------------------------------

    def publish(self, state: Mapping[str, Any], t_plant: float = 0.0) -> None:
        """Send one plant state to the console.

        Called by the engine once per publish interval. The frame is encoded once, whatever
        the number of connections.
        """
        self._seq += 1
        try:
            frame = protocol.encode(protocol.snapshot(self._seq, t_plant, state))
        except (ProtocolError, ValueError):
            # A value the engine could not compute (NaN, inf) is not JSON: send it as None.
            state = _finite(state)
            frame = protocol.encode(protocol.snapshot(self._seq, t_plant, state))
        self._latest = dict(state)
        self._latest_t_plant = t_plant
        self._latest_at = self._clock()
        for station in list(self._stations):
            if station.ready:
                if station.silenced:
                    # The engine speaks again: the status this console was told in place of the
                    # stored one is withdrawn. The engine host sends a status only when it changes,
                    # so without this the silence would stay on a live console's status bar.
                    station.silenced = False
                    if self._status is not None:
                        station.send(protocol.status(*self._status))
                station.send_snapshot(frame)

    def snapshot_age_s(self) -> float | None:
        """Wall-clock seconds since the engine last published; None before its first publish."""
        if self._latest_at is None:
            return None
        return self._clock() - self._latest_at

    def publish_status(self, text: str, level: str) -> None:
        """Send engine health, and remember it for a console that connects later."""
        self._status = (text, level)
        message = protocol.status(text, level)
        for station in list(self._stations):
            if station.ready:
                station.send(message)

    def set_command_handler(self, handler: CommandHandler, engine_name: str) -> None:
        """Attach the engine. Until this is called, every command is refused with a reason."""
        self._command_handler = handler
        self._engine_name = engine_name

    def set_history_handler(self, handler: HistoryHandler) -> None:
        """Attach the historian. Until this is called, every history request is refused."""
        self._history_handler = handler

    def set_exercise_lister(self, lister: Callable[[], list[str]]) -> None:
        """Attach the saved exercises' lister. Until this is called, a request is refused."""
        self._exercise_lister = lister

    # ----------------------------------------------------------------------------------
    # Connection handling
    # ----------------------------------------------------------------------------------

    async def _serve_client(self, reader: asyncio.StreamReader,
                            writer: asyncio.StreamWriter) -> None:
        peer_info = writer.get_extra_info("peername")
        peer = f"{peer_info[0]}:{peer_info[1]}" if peer_info else "?"
        station = _Station(writer, peer, str(peer_info[0]) if peer_info else "")
        self._stations.add(station)
        frames = FrameReader()
        log.info("console connected: %s", peer)

        try:
            while True:
                chunk = await reader.read(65536)
                if not chunk:
                    break
                for message in frames.feed(chunk):
                    self._handle(station, message)
                await writer.drain()
        except ProtocolError as exc:
            log.warning("protocol error from %s: %s", peer, exc)
            station.send(protocol.refused(str(exc)))
            with contextlib.suppress(Exception):
                await writer.drain()
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            self._stations.discard(station)
            with contextlib.suppress(Exception):
                writer.close()
            log.info("console disconnected: %s (%d snapshots dropped)",
                     station.describe(), station.dropped)

    def _handle(self, station: _Station, message: Mapping[str, Any]) -> None:
        kind = message.get("t")

        if kind == Kind.HELLO.value:
            self._handle_hello(station, message)
            return

        if not station.ready:
            station.send(protocol.refused("first message must be 'hello'"))
            return

        if kind == Kind.COMMAND.value:
            self._handle_command(station, message)
        elif kind in (Kind.HISTORY.value, Kind.HISTORY_PATHS.value):
            self._handle_history(station, message)
        elif kind == Kind.EXERCISE_LIST.value:
            self._handle_exercise_list(station, message)
        elif kind == Kind.PING.value:
            station.send(protocol.pong(int(message.get("id", 0))))
        else:
            log.debug("ignoring unknown message kind %r from %s", kind, station.peer)

    def _handle_hello(self, station: _Station, message: Mapping[str, Any]) -> None:
        version = message.get("protocol")
        if version != protocol.PROTOCOL_VERSION:
            # Refuse rather than negotiate. A field that changed meaning between versions
            # would otherwise be misread silently, and this is a control system.
            station.send(protocol.refused(
                f"protocol version {version} != {protocol.PROTOCOL_VERSION}"))
            return
        if not _is_loopback(station.host):
            # The server binds the loopback interface; a peer elsewhere means it was bound
            # wider, and a console there would command the plant with no login at all.
            where = station.host or "an unknown address"
            station.send(protocol.refused(
                f"the engine serves only a console on its own machine; this console "
                f"connects from {where}"))
            return

        station.name = str(message.get("station") or station.peer)
        station.ready = True
        station.send(protocol.welcome(station.name, self._engine_name))
        log.info("console ready: %s", station.describe())

        # Bring the console up to date immediately: the current state and the current
        # engine health, so it is not blank until the next publish. Not an engine's last packet
        # once it has stopped publishing (module docstring, handoff A-28): the console stays
        # blank and says why.
        age = self.snapshot_age_s()
        if age is not None and age > SNAPSHOT_REPLAY_MAX_AGE_S:
            station.silenced = True
            station.send(protocol.status(f"ENGINE SILENT — no packet for {age:.0f} s", "fault"))
            station.send(protocol.snapshot(self._seq, self._latest_t_plant, {}))
            return
        if self._status is not None:
            station.send(protocol.status(*self._status))
        station.send(protocol.snapshot(self._seq, self._latest_t_plant, self._latest))

    def _handle_command(self, station: _Station, message: Mapping[str, Any]) -> None:
        cmd_id = int(message.get("id", 0))
        cmd = message.get("cmd")
        if not isinstance(cmd, dict) or not cmd.get("type"):
            station.send(protocol.ack(cmd_id, False, "command has no 'type'"))
            return

        cmd_type = str(cmd["type"])

        if self._command_handler is None:
            station.send(protocol.ack(cmd_id, False, "no engine attached"))
            return

        try:
            answer = self._command_handler(cmd, station.name)
        except Exception as exc:                            # pragma: no cover - defensive
            # A failing command must not take the server, and therefore the console's link,
            # down with it.
            log.exception("command handler raised on %s", cmd_type)
            station.send(protocol.ack(cmd_id, False, f"engine error: {exc}"))
            return
        if inspect.isawaitable(answer):
            asyncio.ensure_future(self._finish_command(station, cmd_id, cmd, answer))
        else:
            self._answer_command(station, cmd_id, cmd, *answer)

    async def _finish_command(self, station: _Station, cmd_id: int, cmd: Mapping[str, Any],
                              answer) -> None:
        """Send the ack once the engine has answered, between two of its ticks."""
        try:
            accepted, reason = await answer
        except Exception as exc:                            # pragma: no cover - defensive
            log.exception("engine raised on %s", cmd.get("type"))
            accepted, reason = False, f"engine error: {exc}"
        self._answer_command(station, cmd_id, cmd, accepted, reason)

    def _answer_command(self, station: _Station, cmd_id: int, cmd: Mapping[str, Any],
                        accepted: bool, reason: str) -> None:
        station.send(protocol.ack(cmd_id, accepted, reason))
        if accepted:
            self._broadcast_event(station, cmd)

    def _handle_history(self, station: _Station, message: Mapping[str, Any]) -> None:
        """A trend's backfill or the historian's path list."""
        req_id = int(message.get("id", 0))
        if self._history_handler is None:
            station.send(protocol.history_data(req_id, False, "no engine attached"))
            return
        try:
            answer = self._history_handler(message)
        except ValueError as exc:
            station.send(protocol.history_data(req_id, False, str(exc)))
            return
        if inspect.isawaitable(answer):
            asyncio.ensure_future(self._finish_history(station, req_id, answer))
        else:
            station.send(protocol.history_data(req_id, True, "", _finite(answer)))

    def _handle_exercise_list(self, station: _Station, message: Mapping[str, Any]) -> None:
        """The saved exercises' names, for the instructor's panel."""
        req_id = int(message.get("id", 0))
        if self._exercise_lister is None:
            station.send(protocol.exercises(req_id, False, "no engine attached"))
        else:
            station.send(protocol.exercises(req_id, True, "", self._exercise_lister()))

    async def _finish_history(self, station: _Station, req_id: int, answer) -> None:
        try:
            result = await answer
        except ValueError as exc:
            station.send(protocol.history_data(req_id, False, str(exc)))
            return
        station.send(protocol.history_data(req_id, True, "", _finite(result)))

    def _broadcast_event(self, origin: _Station, cmd: Mapping[str, Any]) -> None:
        """Echo an accepted command, and the console that sent it, to every connection."""
        text = f"{origin.name}: {cmd.get('type')}"
        target = cmd.get("id") or cmd.get("tag")
        if target:
            text += f" {target}"
        message = protocol.event(origin.name, cmd, text)
        for station in list(self._stations):
            if station.ready:
                station.send(message)


__all__ = ["StationServer", "DEFAULT_HOST", "DEFAULT_PORT", "CommandHandler",
           "HistoryHandler"]
