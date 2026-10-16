"""Station server — one engine, many consoles.

What it is
----------
An asyncio TCP server that fans the plant state out to every connected station and funnels
operator commands back to the engine. Pure Python: **no Qt anywhere**, because the engine
must run headless on a server box with no display.

    engine  --snapshot-->  StationServer  --broadcast-->  instructor + trainee consoles
    engine  <--command---  StationServer  <--command----  a console, if its role allows

Session shape
-------------
A typical OTS session is one instructor station and one to four trainee stations, all
watching the same plant. The instructor sees every trainee action as it happens, because
each accepted command is broadcast back as an audit `event`.

Why broadcast-on-tick rather than per-client polling
----------------------------------------------------
The snapshot is encoded **once** per publish and the same bytes are written to every
station. With a 400-tag packet at 10 Hz, per-client encoding would multiply the engine's
serialisation cost by the number of consoles for no benefit — every station wants the same
state, by definition.

Unit assignment
---------------
An instructor narrows a trainee station to a set of plant sections. The server resolves
each incoming command to its section (`ureasim.data.tags`) and refuses one that falls
outside, naming the instrument, before the engine sees it. A station with no assignment is
unrestricted, and an instructor (or the single-machine superuser) is never restricted.

The superuser
-------------
The default deployment is one machine (decided 2026-10-07), its one console the ``superuser`` —
every command, never assigned. The server grants that role only to a console on its own machine:
a loopback peer. A station elsewhere asking for it is refused at ``hello``, with the reason.

Station login
-------------
A server started with a station token (handoff A-2, closed 2026-10-16) admits only a station whose
``hello`` presents it, the superuser included; the comparison takes the same time whatever the
token sent, and a station refused for its token is disconnected, so it cannot try again on the
same connection. A server started with no token admits every station, as before.

Commands reach the engine in arrival order
------------------------------------------
The engine host (`ureasim.net.engine_host`) steps the plant on its own thread and applies each
command between two ticks. Its handler therefore answers with an awaitable; the server sends the
ack — and broadcasts the audit event — when the engine has answered, so a refusal's reason is the
plant's, never a timeout's. A handler that answers at once (a test's, or none attached) is taken
as it is.

History
-------
A `history` or `history_paths` request goes to the history handler the host attaches, answered
the same way; any ready station may ask, since reading the past commands nothing.

The instructor's lists
----------------------
Every instructor console is sent the `roster` — each ready station, its role and its sections —
when a station joins, leaves or is assigned, and answered an `exercise_list` request from the
exercise lister the host attaches. Only an instructor (or the superuser) may ask for the
exercises, as only they may save or restore one.

Back-pressure
-------------
A station whose socket cannot keep up would otherwise grow an unbounded write queue and
eventually take the engine's memory with it. Each connection therefore drops snapshots it
has not managed to flush: a console that falls behind sees the *latest* plant state when it
catches up, never a backlog of stale ones. Commands and acks are never dropped — losing an
operator action is not acceptable, losing a frame of a 10 Hz animation is.
"""

from __future__ import annotations

import asyncio
import contextlib
import hmac
import inspect
import ipaddress
import logging
import math
from typing import Any, Callable, Mapping

from ureasim.data import tags
from ureasim.net import protocol
from ureasim.net.protocol import FrameReader, Kind, ProtocolError, Role

log = logging.getLogger(__name__)

#: Default listening port. Chosen outside the registered range and away from V1's 8000.
DEFAULT_PORT = 8765
DEFAULT_HOST = "0.0.0.0"

#: How many unflushed snapshot frames a slow station may accumulate before the server
#: starts dropping them for that station. One in flight plus one queued is enough to keep a
#: healthy console saturated without letting a sick one build a backlog.
MAX_QUEUED_SNAPSHOTS = 2

#: Command handler signature: it receives the command dict and the issuing station's name,
#: and returns ``(accepted, reason)``, or an awaitable of it.
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
    """One connected console."""

    def __init__(self, writer: asyncio.StreamWriter, peer: str, host: str = ""):
        self.writer = writer
        self.peer = peer
        #: The peer's address, without its port: a loopback address is this machine.
        self.host = host
        self.name = peer
        self.role = Role.OBSERVER
        self.ready = False              # True once `hello` has been accepted
        #: Plant sections this station may command. ``None`` means unrestricted, which is
        #: NOT the same as an empty set (assigned nothing).
        self.sections: set[str] | None = None
        self.dropped = 0                # snapshots skipped for back-pressure
        self._queued = 0

    def send(self, message: Mapping[str, Any]) -> None:
        """Queue a message. Never raises on a dead socket — the reader task notices."""
        try:
            self.writer.write(protocol.encode(message))
        except (ProtocolError, RuntimeError, ConnectionError) as exc:  # pragma: no cover
            log.debug("send to %s failed: %s", self.peer, exc)

    def send_snapshot(self, frame: bytes) -> None:
        """Write a pre-encoded snapshot, dropping it if this station is behind.

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
        scope = ("all" if self.sections is None
                 else ",".join(sorted(self.sections)) or "none")
        return f"{self.name} ({self.role.value}, {scope}, {self.peer})"


class StationServer:
    """Serves one simulation to many consoles.

    Parameters
    ----------
    command_handler
        Called for each authorised command with ``(cmd, station_name)``. Returns
        ``(accepted, reason)``. The engine owns the decision: the server only enforces the
        *role*, never the process interlocks — a pump start refused by a latched trip is
        the engine's answer, and it must reach the operator with its reason.
    engine_name
        Reported in `welcome`, so a console can tell which engine build it is attached to.
    token
        The station token every ``hello`` must present, or ``None`` to admit every station.
        An empty token is refused here: it would read as a login and admit anyone.
    """

    def __init__(self, command_handler: CommandHandler | None = None,
                 engine_name: str = "unattached", token: str | None = None):
        if token is not None and not token:
            raise ValueError("an empty station token admits every station; pass None instead")
        self._token = token
        self._stations: set[_Station] = set()
        self._command_handler = command_handler
        self._history_handler: HistoryHandler | None = None
        self._exercise_lister: Callable[[], list[str]] | None = None
        self._engine_name = engine_name
        self._server: asyncio.AbstractServer | None = None
        self._seq = 0
        self._latest: dict[str, Any] = {}
        self._latest_t_plant = 0.0
        self._status: tuple[str, str] | None = None
        #: station name -> sections. Kept by NAME, not by connection, so a trainee who
        #: reconnects mid-exercise keeps the plant the instructor gave them.
        self._assignments: dict[str, set[str]] = {}

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
        log.info("station server listening on %s:%d", host, bound)
        return bound

    async def stop(self) -> None:
        """Close every station and stop listening."""
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
        """Consoles that have completed the handshake."""
        return sum(1 for s in self._stations if s.ready)

    def stations(self) -> list[str]:
        """Descriptions of the connected consoles, for the instructor's station list."""
        return [s.describe() for s in self._stations if s.ready]

    # ----------------------------------------------------------------------------------
    # Unit assignment
    # ----------------------------------------------------------------------------------

    def assign(self, station: str, sections) -> tuple[bool, str]:
        """Give a station its plant sections. ``None`` restores unrestricted access.

        Returns ``(accepted, reason)``. An unknown section id is refused rather than
        dropped, because a typo that silently assigns nothing would leave a trainee locked
        out of a plant the instructor believes they are holding.
        """
        if sections is None:
            self._assignments.pop(station, None)
            self._notify_assignment(station, None)
            return True, ""

        wanted = {str(s) for s in sections}
        unknown = sorted(wanted - tags.SECTION_IDS)
        if unknown:
            return False, (f"unknown section(s) {', '.join(unknown)}; "
                           f"valid: {', '.join(sorted(tags.SECTION_IDS))}")

        self._assignments[station] = wanted
        self._notify_assignment(station, wanted)
        return True, ""

    def assignment_of(self, station: str) -> set[str] | None:
        """Sections a station holds, or ``None`` when it is unrestricted."""
        return self._assignments.get(station)

    def _notify_assignment(self, station: str, sections) -> None:
        """Tell the affected station, and every instructor, what changed.

        The trainee needs it for their status bar; instructors need it because they are
        the ones running the exercise.
        """
        message = protocol.assignment(station, sections)
        for s in list(self._stations):
            # A station may hold more than one connection only transiently, during a
            # reconnect, so update every connection carrying this name.
            if s.name == station:
                s.sections = None if sections is None else set(sections)
            if s.ready and (s.name == station or protocol.runs_the_exercise(s.role)):
                s.send(message)
        self._broadcast_roster()

    # ----------------------------------------------------------------------------------
    # Engine side
    # ----------------------------------------------------------------------------------

    def publish(self, state: Mapping[str, Any], t_plant: float = 0.0) -> None:
        """Broadcast one plant state to every station.

        Called by the engine once per publish interval. The frame is encoded once and the
        same bytes go to everyone.
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
        for station in list(self._stations):
            if station.ready:
                station.send_snapshot(frame)

    def publish_status(self, text: str, level: str) -> None:
        """Broadcast engine health, and remember it for stations that connect later."""
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

    def roster(self) -> list[dict]:
        """Every ready station: its name, role and sections (``None`` unrestricted)."""
        return [{"station": s.name, "role": s.role.value,
                 "sections": None if s.sections is None else sorted(s.sections)}
                for s in sorted(self._stations, key=lambda st: st.name) if s.ready]

    def _broadcast_roster(self) -> None:
        """Send the roster to every instructor console."""
        message = protocol.roster(self.roster())
        for s in list(self._stations):
            if s.ready and protocol.runs_the_exercise(s.role):
                s.send(message)

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
        log.info("station connected: %s", peer)

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
            if station.ready:
                self._broadcast_roster()
            with contextlib.suppress(Exception):
                writer.close()
            log.info("station disconnected: %s (%d snapshots dropped)",
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
        refusal = self._login_refusal(message.get("token"))
        if refusal:
            # Before the role is read: a station without the token learns nothing more.
            log.warning("station login refused from %s: %s", station.peer, refusal)
            station.send(protocol.refused(refusal))
            with contextlib.suppress(Exception):
                station.writer.close()
            return
        try:
            role = Role(str(message.get("role", Role.OBSERVER.value)))
        except ValueError:
            station.send(protocol.refused(f"unknown role {message.get('role')!r}"))
            return
        if role in protocol.LOCAL_ONLY_ROLES and not _is_loopback(station.host):
            where = station.host or "an unknown address"
            station.send(protocol.refused(
                f"the {role.value} role is granted only to a console on the engine's own "
                f"machine; this station connects from {where}"))
            return

        station.role = role
        station.name = str(message.get("station") or station.peer)
        station.ready = True
        # Assignments are kept by station NAME, so a trainee who reconnects mid-exercise
        # keeps the plant the instructor gave them.
        station.sections = self._assignments.get(station.name)
        station.send(protocol.welcome(role, station.name, self._engine_name,
                                      station.sections))
        log.info("station ready: %s", station.describe())

        # Bring the newcomer up to date immediately: the current state and the current
        # engine health, so it is not blank until the next publish.
        if self._status is not None:
            station.send(protocol.status(*self._status))
        station.send(protocol.snapshot(self._seq, self._latest_t_plant, self._latest))
        self._broadcast_roster()

    def _login_refusal(self, token: Any) -> str:
        """Why a ``hello`` presenting ``token`` is refused, or ``""`` when it is admitted.

        The comparison is `hmac.compare_digest`, whose time does not depend on how much of the
        token was right, so the server's answer time gives a guesser nothing to climb.
        """
        if self._token is None:
            return ""
        if not isinstance(token, str) or not token:
            return "this engine requires a station token, and the station presented none"
        if not hmac.compare_digest(token.encode("utf-8"), self._token.encode("utf-8")):
            return "the station token is not this engine's"
        return ""

    def _handle_command(self, station: _Station, message: Mapping[str, Any]) -> None:
        cmd_id = int(message.get("id", 0))
        cmd = message.get("cmd")
        if not isinstance(cmd, dict) or not cmd.get("type"):
            station.send(protocol.ack(cmd_id, False, "command has no 'type'"))
            return

        cmd_type = str(cmd["type"])

        if not protocol.is_authorised(station.role, cmd_type):
            # Named refusal, not a silent drop: the operator must learn that the command
            # was rejected and why, exactly as a real DCS tells them.
            station.send(protocol.ack(
                cmd_id, False,
                f"role '{station.role.value}' may not issue '{cmd_type}'"))
            log.info("refused %s from %s", cmd_type, station.describe())
            return

        # `assign` is the instructor's own control over the exercise, not a plant command:
        # it is handled here and never reaches the engine.
        if cmd_type == "assign":
            accepted, reason = self.assign(str(cmd.get("station", "")),
                                           cmd.get("sections"))
            station.send(protocol.ack(cmd_id, accepted, reason))
            if accepted:
                self._broadcast_event(station, cmd)
            return

        allowed, reason = self._within_assignment(station, cmd)
        if not allowed:
            station.send(protocol.ack(cmd_id, False, reason))
            log.info("out of scope: %s from %s", cmd_type, station.describe())
            return

        if self._command_handler is None:
            station.send(protocol.ack(cmd_id, False, "no engine attached"))
            return

        try:
            answer = self._command_handler(cmd, station.name)
        except Exception as exc:                            # pragma: no cover - defensive
            # A failing command must not take the server, and therefore every other
            # console, down with it.
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
        """A trend's backfill or the historian's path list, for any ready station."""
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
        """The saved exercises' names, for an instructor."""
        req_id = int(message.get("id", 0))
        if not protocol.runs_the_exercise(station.role):
            station.send(protocol.exercises(req_id, False, "only an instructor lists exercises"))
        elif self._exercise_lister is None:
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

    def _within_assignment(self, station: _Station,
                           cmd: Mapping[str, Any]) -> tuple[bool, str]:
        """Is this command inside the station's assigned plant?

        An unassigned station, an instructor and the superuser are unrestricted. For an assigned
        station, a command that cannot be attributed to a section is refused — failing
        closed, so the assignment cannot be bypassed by a command the resolver does not
        know about.
        """
        if protocol.runs_the_exercise(station.role) or station.sections is None:
            return True, ""

        section = tags.section_of_command(cmd)
        if section is None:
            return False, (
                f"'{cmd.get('type')}' cannot be attributed to a plant section, so this "
                f"station cannot issue it while assigned to "
                f"{tags.describe_sections(station.sections)}")
        if section not in station.sections:
            target = tags.target_of_command(cmd) or cmd.get("type")
            return False, (
                f"{target} is in section {section} "
                f"({tags.SECTIONS[section]['name']}); this station is assigned "
                f"{tags.describe_sections(station.sections)}")
        return True, ""

    def _broadcast_event(self, origin: _Station, cmd: Mapping[str, Any]) -> None:
        """Tell every station what just happened, and who did it."""
        text = f"{origin.name}: {cmd.get('type')}"
        target = cmd.get("id") or cmd.get("tag")
        if target:
            text += f" {target}"
        message = protocol.event(origin.name, origin.role, cmd, text)
        for station in list(self._stations):
            if station.ready:
                station.send(message)


__all__ = ["StationServer", "DEFAULT_HOST", "DEFAULT_PORT", "CommandHandler",
           "HistoryHandler"]
