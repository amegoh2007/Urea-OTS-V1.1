"""Station protocol — framing, message kinds, roles and command authorisation.

Why a protocol at all
---------------------
The OTS runs as **one plant with several consoles**: an instructor station and one or more
trainee stations, all watching the same simulation. That cannot be done in a single
process, so the engine is a server and every console is a client.

This module is the contract between them. It is pure Python with no Qt and no sockets, so
both halves share exactly one definition of every message, and the whole thing is testable
without opening a port.

Framing
-------
Length-prefixed JSON over a stream socket::

    +--------+------------------------+
    | uint32 |  UTF-8 JSON payload    |
    |  BE    |  (length bytes)        |
    +--------+------------------------+

Length-prefixed rather than newline-delimited because a snapshot is a single large object
and a delimiter scan would have to escape the payload. JSON rather than a binary codec
because a training simulator's snapshot is read by humans during commissioning, and at
10 Hz across a handful of stations the cost is irrelevant — V1 sent the same payload over a
WebSocket.

Roles
-----
    observer     sees the plant, commands nothing
    operator     every command V1's operator screens exposed
    instructor   the above, plus the simulator controls
    superuser    every command and every list, no unit assignment — the single-machine console

The split is deliberately conservative: an **operator station can do exactly what V1's UI
allowed**, and the only commands moved behind the instructor role are the ones that are not
plant equipment at all — malfunction injection, reset, and simulation pacing. Re-classifying
a plant control would change what a trainee is being taught, which the rewrite must not do.

**Single-machine mode (decided 2026-10-07).** The default deployment is one engine and one
console on one machine (``run.py`` with no mode). That console is the ``superuser``: no command
type is refused for its role and no unit assignment narrows it. The server grants the role only to
a console on its own machine (a loopback peer), so the multi-station path is no weaker for it. A
superuser's command is still the engine's to refuse: a latched trip or an interlock answers with
its reason, as for any role.

Station login (handoff A-2, closed 2026-10-16)
----------------------------------------------
An engine may be started with a shared station token. A station then presents it in its `hello`,
and the server refuses one that presents none, or another, before it reads the role the station
asks for. The token admits a station to the plant; among the stations it admits, each still
requests its role, as on a closed classroom network. An engine started with no token checks none,
and a `hello` with no token is the same message it always was.

Unit assignment
---------------
An instructor assigns each trainee a set of **plant sections** (321, 322, 323, 324, 328,
329, 335). A command to a tag outside your sections is refused, by name, before it reaches
the engine — so two trainees on one exercise cannot fight over the same loop without
either realising.

A station with **no** assignment is unrestricted. Assignment is a narrowing the instructor
applies; a classroom that has not set one up behaves as it did before. Instructors are
never restricted.

Which section a command acts on is resolved by `ureasim.data.tags.section_of_command`. A
command it cannot attribute is refused for an **assigned** station, so the gap is visible
and fixable rather than becoming a hole in the assignment.

Command arbitration within a section
------------------------------------
Inside a station's own sections, commands are applied by the engine in arrival order and
the last one wins — the way a real DCS resolves two operators reaching for one valve. Every
accepted command is broadcast to **all** stations as an `event`, so the instructor sees each
trainee action as it happens and the exercise has a transcript.

History
-------
A trend window opened mid-exercise backfills its pens from the engine's historian: a
`history` request names the pens' paths and the span, and a `history_paths` request asks
what the historian records (V1's ``/api/hist`` and ``/api/hist/paths``, carried here
because a console has no other channel to the engine). Reading history changes nothing, so
every role may ask; each answer is a `history_data` with the request's id.

The instructor's panel
----------------------
The instructor runs the exercise from a panel that needs two things only the server knows: the
stations connected and the plant each holds, sent to every instructor console as a `roster`
whenever a station joins, leaves or is assigned; and the saved exercises, which an instructor
asks for with `exercise_list` and receives as `exercises`. Both are lists, not plant state: the
consoles render them and command nothing through them.
"""

from __future__ import annotations

import json
import struct
from enum import Enum
from typing import Any, Iterator, Mapping

#: Wire-format version. A client whose version differs is refused at `hello`, with the
#: reason, rather than being allowed to misread a field that changed meaning.
PROTOCOL_VERSION = 1

#: Frame header: one big-endian unsigned 32-bit length.
_HEADER = struct.Struct(">I")
HEADER_SIZE = _HEADER.size

#: Refuse a declared length larger than this. A corrupt or hostile header would otherwise
#: make the reader allocate arbitrary memory while it waits for bytes that never arrive.
MAX_FRAME_BYTES = 8 * 1024 * 1024


class ProtocolError(ValueError):
    """Malformed frame or message. Always fatal for the connection that produced it."""


# ======================================================================================
# Roles
# ======================================================================================

class Role(str, Enum):
    """What a connected station is permitted to do."""

    OBSERVER = "observer"
    OPERATOR = "operator"
    INSTRUCTOR = "instructor"
    #: The single-machine console (decided 2026-10-07): every command, never assigned.
    SUPERUSER = "superuser"


#: The roles that run the exercise: the instructor's commands, lists and roster, never narrowed
#: by a unit assignment.
EXERCISE_ROLES = frozenset({Role.INSTRUCTOR, Role.SUPERUSER})

#: The roles the server grants only to a console on its own machine.
LOCAL_ONLY_ROLES = frozenset({Role.SUPERUSER})


def runs_the_exercise(role: Role) -> bool:
    """True for a role with the instructor's rights: the simulator controls, the exercise list,
    the roster, and no unit assignment."""
    return role in EXERCISE_ROLES


#: Simulator controls — NOT plant equipment. These change the exercise rather than the
#: process, so a trainee must not reach them: a trainee who can clear their own malfunction
#: or reset the plant is not being trained.
INSTRUCTOR_ONLY_COMMANDS = frozenset({
    "trigger_fault",      # malfunction injection
    "clear_fault",
    "reset_sim",          # reinitialise the plant to a seed
    "set_sim_mode",       # SLOW / FAST simulation pacing
    "freeze",             # hold the integrator
    "snapshot_save",      # store an exercise state
    "snapshot_load",      # restore one
    "assign",             # give a trainee station its plant sections
    "co2_set",            # the battery-limit CO2 rate: 320K002 is a boundary feed outside the
                          # simulated plant, with no operator lever (decided 2026-10-08)
})


def is_authorised(role: Role, command_type: str) -> bool:
    """True when `role` may issue `command_type`.

    An observer commands nothing. An operator may issue every plant command V1's screens
    exposed — including the ``*_fault`` suffix form V1 accepted through its generic ``set``
    handler, which is treated as fault injection here and therefore gated. The superuser may
    issue every command.
    """
    if role is Role.SUPERUSER:
        return True
    if role is Role.OBSERVER:
        return False
    gated = (command_type in INSTRUCTOR_ONLY_COMMANDS
             or command_type.endswith("_fault"))
    if gated:
        return runs_the_exercise(role)
    return True


# ======================================================================================
# Message kinds
# ======================================================================================

class Kind(str, Enum):
    """Message discriminator, carried as the ``t`` field."""

    # client -> server
    HELLO = "hello"            # {role, station, protocol[, token]}
    COMMAND = "command"        # {id, cmd}
    PING = "ping"              # {id}
    HISTORY = "history"        # {id, paths, span, max_points, end}
    HISTORY_PATHS = "history_paths"  # {id}
    EXERCISE_LIST = "exercise_list"  # {id}

    # server -> client
    WELCOME = "welcome"        # {role, station, protocol, engine, sections}
    ASSIGNMENT = "assignment"  # {station, sections}
    REFUSED = "refused"        # {reason}
    SNAPSHOT = "snapshot"      # {seq, t_plant, state}
    STATUS = "status"          # {text, level}
    ACK = "ack"                # {id, ok, reason}
    EVENT = "event"            # {station, role, cmd, text}
    PONG = "pong"              # {id}
    HISTORY_DATA = "history_data"  # {id, ok, reason, result}
    ROSTER = "roster"          # {stations: [{station, role, sections}]}
    EXERCISES = "exercises"    # {id, ok, reason, names}


# --------------------------------------------------------------------------------------
# Constructors — one function per message, so no call site hand-builds a dict
# --------------------------------------------------------------------------------------

def hello(role: Role, station: str, token: str | None = None) -> dict:
    """Client's opening message: who it is and what it claims to be.

    ``token`` is the engine's station token, carried only when the station has one: an engine
    started with a token admits no station without it.
    """
    message = {"t": Kind.HELLO.value, "role": Role(role).value,
               "station": station, "protocol": PROTOCOL_VERSION}
    if token is not None:
        message["token"] = token
    return message


def welcome(role: Role, station: str, engine: str, sections=None) -> dict:
    """Server's acceptance, echoing the role actually granted and any assignment.

    ``sections`` is ``None`` for an unrestricted station, which is what a station with no
    assignment is. An empty list would mean "assigned nothing", which is a different thing.
    """
    return {"t": Kind.WELCOME.value, "role": Role(role).value, "station": station,
            "protocol": PROTOCOL_VERSION, "engine": engine,
            "sections": None if sections is None else sorted(sections)}


def assignment(station: str, sections) -> dict:
    """A station's plant sections, sent when the instructor changes them.

    ``sections`` of ``None`` means unrestricted. The station shows this in its status bar,
    so a trainee always knows which plant they are holding.
    """
    return {"t": Kind.ASSIGNMENT.value, "station": station,
            "sections": None if sections is None else sorted(sections)}


def refused(reason: str) -> dict:
    """Server's rejection of a station's `hello` or of a frame it could not read."""
    return {"t": Kind.REFUSED.value, "reason": reason}


def snapshot(seq: int, t_plant: float, state: Mapping[str, Any]) -> dict:
    """A plant state.

    ``seq`` increments once per publish so a client can detect a dropped or reordered
    frame; ``t_plant`` is simulated time in seconds, which is what the trend window plots
    against — wall-clock would break as soon as the instructor uses FAST pacing.
    """
    return {"t": Kind.SNAPSHOT.value, "seq": seq, "t_plant": t_plant, "state": state}


def status(text: str, level: str) -> dict:
    """Engine health for the station's status bar. ``level`` is ok / warn / fault."""
    return {"t": Kind.STATUS.value, "text": text, "level": level}


def command(cmd_id: int, cmd: Mapping[str, Any]) -> dict:
    """An operator action. ``cmd`` is the V1 command dict, with its ``type`` field."""
    return {"t": Kind.COMMAND.value, "id": cmd_id, "cmd": dict(cmd)}


def ack(cmd_id: int, ok: bool, reason: str = "") -> dict:
    """Result of one command.

    A refusal always carries its reason. A command that is silently dropped teaches a
    trainee that the plant ignored them, which is the opposite of what an OTS is for.
    """
    return {"t": Kind.ACK.value, "id": cmd_id, "ok": ok, "reason": reason}


def event(station: str, role: Role, cmd: Mapping[str, Any], text: str) -> dict:
    """Audit broadcast: an accepted command, echoed to every station.

    This is what lets an instructor watch a trainee work without looking over a shoulder,
    and it is also the exercise transcript.
    """
    return {"t": Kind.EVENT.value, "station": station, "role": Role(role).value,
            "cmd": dict(cmd), "text": text}


def history(req_id: int, paths, span_s: float, max_points: int = 800,
            end_sim: float | None = None) -> dict:
    """A trend's backfill request: ``span_s`` plant seconds of ``paths``, ending at ``end_sim``
    (the newest sample when None), decimated to at most ``max_points`` points a pen."""
    return {"t": Kind.HISTORY.value, "id": req_id, "paths": list(paths), "span": span_s,
            "max_points": max_points, "end": end_sim}


def history_paths(req_id: int) -> dict:
    """Ask which paths the historian records, and each ring's occupancy."""
    return {"t": Kind.HISTORY_PATHS.value, "id": req_id}


def history_data(req_id: int, ok: bool, reason: str = "", result: Any = None) -> dict:
    """The answer to a `history` or `history_paths` request; a refusal carries its reason."""
    return {"t": Kind.HISTORY_DATA.value, "id": req_id, "ok": ok, "reason": reason,
            "result": result}


def roster(stations) -> dict:
    """The connected stations, for the instructors: each one's name, role and sections
    (``None`` unrestricted)."""
    return {"t": Kind.ROSTER.value, "stations": [dict(s) for s in stations]}


def exercise_list(req_id: int) -> dict:
    """Ask for the names of the saved exercises."""
    return {"t": Kind.EXERCISE_LIST.value, "id": req_id}


def exercises(req_id: int, ok: bool, reason: str = "", names=None) -> dict:
    """The saved exercises' names, or the reason there are none to give."""
    return {"t": Kind.EXERCISES.value, "id": req_id, "ok": ok, "reason": reason,
            "names": list(names or [])}


def ping(seq: int) -> dict:
    return {"t": Kind.PING.value, "id": seq}


def pong(seq: int) -> dict:
    return {"t": Kind.PONG.value, "id": seq}


# ======================================================================================
# Codec
# ======================================================================================

def encode(message: Mapping[str, Any]) -> bytes:
    """Serialise one message into a length-prefixed frame.

    ``separators`` is set explicitly: the default encoder emits a space after every comma
    and colon, which on a 400-tag snapshot at 10 Hz is several hundred kilobytes a minute
    of nothing.
    """
    body = json.dumps(message, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")
    if len(body) > MAX_FRAME_BYTES:
        raise ProtocolError(f"frame of {len(body)} bytes exceeds the {MAX_FRAME_BYTES} limit")
    return _HEADER.pack(len(body)) + body


def decode(body: bytes) -> dict:
    """Parse one frame body into a message, checking that it is a tagged object."""
    try:
        message = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError(f"undecodable frame: {exc}") from exc
    if not isinstance(message, dict) or "t" not in message:
        raise ProtocolError("frame is not a tagged message object")
    return message


class FrameReader:
    """Reassembles frames from an arbitrarily chunked byte stream.

    A TCP read returns whatever happened to arrive: half a frame, three frames, or a frame
    split across two reads. Feed every chunk in and iterate whatever completed.

    Holding the partial frame here — rather than in the socket callback — is what lets the
    Qt client be a plain ``readyRead`` slot with no buffering logic of its own.
    """

    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, chunk: bytes) -> Iterator[dict]:
        """Add received bytes; yield every message that is now complete."""
        self._buffer.extend(chunk)
        while True:
            if len(self._buffer) < HEADER_SIZE:
                return
            (length,) = _HEADER.unpack_from(self._buffer, 0)
            if length > MAX_FRAME_BYTES:
                # Refuse rather than wait: a length this large is corruption, and waiting
                # for it would stall the connection forever while the buffer grows.
                raise ProtocolError(
                    f"declared frame length {length} exceeds the {MAX_FRAME_BYTES} limit")
            if len(self._buffer) < HEADER_SIZE + length:
                return
            body = bytes(self._buffer[HEADER_SIZE:HEADER_SIZE + length])
            del self._buffer[:HEADER_SIZE + length]
            yield decode(body)

    @property
    def pending_bytes(self) -> int:
        """Bytes held for an incomplete frame. Useful in tests and diagnostics."""
        return len(self._buffer)

    def reset(self) -> None:
        """Discard any partial frame. Called on reconnect."""
        self._buffer.clear()


__all__ = [
    "PROTOCOL_VERSION", "HEADER_SIZE", "MAX_FRAME_BYTES",
    "ProtocolError", "Role", "Kind",
    "INSTRUCTOR_ONLY_COMMANDS", "EXERCISE_ROLES", "LOCAL_ONLY_ROLES", "runs_the_exercise",
    "is_authorised",
    "hello", "welcome", "assignment", "refused", "snapshot", "status",
    "command", "ack", "event", "ping", "pong", "history", "history_paths", "history_data",
    "roster", "exercise_list", "exercises",
    "encode", "decode", "FrameReader",
]
