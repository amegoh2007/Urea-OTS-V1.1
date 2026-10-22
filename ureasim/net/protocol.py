"""Console protocol — framing and message kinds between the engine and its console.

Why a protocol at all
---------------------
The OTS is **one plant with a single local console** (decided 2026-10-22, `project.md`
decision 149). The engine still runs headless, on its own physics thread, and the console
reaches it over a loopback socket: physics and presentation share no object, the equivalence
suites and the Phase 7 runners drive the engine with no display at all, and a console that
stalls never delays a tick.

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
10 Hz the cost is irrelevant — V1 sent the same payload over a WebSocket.

Commands and refusals
---------------------
The console sends every command the engine takes: the plant controls V1's operator screens
exposed, from the screens and faceplates, and the simulator controls that are not plant
equipment — malfunction injection, reset, pacing, freeze, exercise save and restore, and the
battery-limit CO2 demand — from the instructor's panel. The separation is the console's layout,
not a permission: no command is refused for who sent it. The engine refuses what the process
refuses — a latched trip, an interlock, a closed valve — and its reason travels back on the
command's `ack`, so the operator learns why.

Station roles, the station token, the roster and unit assignment by plant section were the
multi-station deployment's (decisions 72, 124 and 125, handoffs A-2 and A-8) and were removed
with it (decision 149).

Audit
-----
Every accepted command is echoed back as an `event`: the console's audit line, and the
exercise's transcript.

History
-------
A trend window opened mid-exercise backfills its pens from the engine's historian: a
`history` request names the pens' paths and the span, and a `history_paths` request asks
what the historian records (V1's ``/api/hist`` and ``/api/hist/paths``, carried here
because a console has no other channel to the engine). Each answer is a `history_data` with the
request's id.

The instructor's panel
----------------------
The panel restores a saved exercise from a list only the engine's side knows, which it asks for
with `exercise_list` and receives as `exercises`. It is a list, not plant state: the console
renders it and commands nothing through it.
"""

from __future__ import annotations

import json
import struct
from enum import Enum
from typing import Any, Iterator, Mapping

#: Wire-format version. A client whose version differs is refused at `hello`, with the
#: reason, rather than being allowed to misread a field that changed meaning. 2 since the
#: single-console conversion (decision 149): `hello`, `welcome` and `event` carry no role,
#: token or sections.
PROTOCOL_VERSION = 2

#: Frame header: one big-endian unsigned 32-bit length.
_HEADER = struct.Struct(">I")
HEADER_SIZE = _HEADER.size

#: Refuse a declared length larger than this. A corrupt or hostile header would otherwise
#: make the reader allocate arbitrary memory while it waits for bytes that never arrive.
MAX_FRAME_BYTES = 8 * 1024 * 1024


class ProtocolError(ValueError):
    """Malformed frame or message. Always fatal for the connection that produced it."""


# ======================================================================================
# Message kinds
# ======================================================================================

class Kind(str, Enum):
    """Message discriminator, carried as the ``t`` field."""

    # client -> server
    HELLO = "hello"            # {station, protocol}
    COMMAND = "command"        # {id, cmd}
    PING = "ping"              # {id}
    HISTORY = "history"        # {id, paths, span, max_points, end}
    HISTORY_PATHS = "history_paths"  # {id}
    EXERCISE_LIST = "exercise_list"  # {id}

    # server -> client
    WELCOME = "welcome"        # {station, protocol, engine}
    REFUSED = "refused"        # {reason}
    SNAPSHOT = "snapshot"      # {seq, t_plant, state}
    STATUS = "status"          # {text, level}
    ACK = "ack"                # {id, ok, reason}
    EVENT = "event"            # {station, cmd, text}
    PONG = "pong"              # {id}
    HISTORY_DATA = "history_data"  # {id, ok, reason, result}
    EXERCISES = "exercises"    # {id, ok, reason, names}


# --------------------------------------------------------------------------------------
# Constructors — one function per message, so no call site hand-builds a dict
# --------------------------------------------------------------------------------------

def hello(station: str) -> dict:
    """Client's opening message: the console's name, for the audit line, and its version."""
    return {"t": Kind.HELLO.value, "station": station, "protocol": PROTOCOL_VERSION}


def welcome(station: str, engine: str) -> dict:
    """Server's acceptance, naming the engine build the console is attached to."""
    return {"t": Kind.WELCOME.value, "station": station, "protocol": PROTOCOL_VERSION,
            "engine": engine}


def refused(reason: str) -> dict:
    """Server's rejection of a console's `hello` or of a frame it could not read."""
    return {"t": Kind.REFUSED.value, "reason": reason}


def snapshot(seq: int, t_plant: float, state: Mapping[str, Any]) -> dict:
    """A plant state.

    ``seq`` increments once per publish so a client can detect a dropped or reordered
    frame; ``t_plant`` is simulated time in seconds, which is what the trend window plots
    against — wall-clock would break as soon as the instructor uses FAST pacing.
    """
    return {"t": Kind.SNAPSHOT.value, "seq": seq, "t_plant": t_plant, "state": state}


def status(text: str, level: str) -> dict:
    """Engine health for the console's status bar. ``level`` is ok / warn / fault."""
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


def event(station: str, cmd: Mapping[str, Any], text: str) -> dict:
    """Audit echo: an accepted command, sent back to the console.

    The console's audit line shows the last one, and the sequence is the exercise's
    transcript.
    """
    return {"t": Kind.EVENT.value, "station": station, "cmd": dict(cmd), "text": text}


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
    "ProtocolError", "Kind",
    "hello", "welcome", "refused", "snapshot", "status",
    "command", "ack", "event", "ping", "pong", "history", "history_paths", "history_data",
    "exercise_list", "exercises",
    "encode", "decode", "FrameReader",
]
