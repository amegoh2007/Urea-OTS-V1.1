"""EngineBridge — the console's single connection to the plant.

Why this moved out of `ureasim/engine`
--------------------------------------
Multi-station operation makes the engine a **headless server**: it runs on a box with no
display and must not import Qt at all. The bridge is the *console's* end of that link, so
it belongs with the console.

    ureasim/net/       protocol + server   — pure Python, no Qt, runs headless
    ureasim/hmi/bridge EngineBridge        — QTcpSocket client, lives with the UI

Everything that crosses between the plant and this console still crosses here, and nowhere
else:

    plant   ->  UI      `snapshot`, `status`, `audit_event` signals
    server  ->  UI      `roster_changed`, `exercises_received` (the instructor's lists)
    engine  ->  UI      `history_received` (the historian's answer to a trend)
    UI      ->  plant   `send_command`, `request_exercises`, `request_history`

A widget that opened its own socket, or a solver that touched a widget, would be a defect
visible in one import statement.

Why QTcpSocket and not a thread with a blocking socket
-------------------------------------------------------
`QTcpSocket` is signal-driven and lives on the GUI thread's event loop, so there is no
worker thread, no lock and no queue between the wire and the widgets. Reassembly is handled
by `protocol.FrameReader`, which holds any partial frame, so `readyRead` stays a three-line
slot.

Reconnection
------------
A console that loses its link retries with a bounded backoff and says so in the status bar.
It does **not** keep showing the last values it received: a frozen screen that looks live is
the single most dangerous thing an OTS console can do, so a stale link drives every
indicator back to `--`.

History
-------
A trend draws the engine historian's ring buffers, never samples of its own: it asks with
`request_history` and receives the answer, matched by its request id, on `history_received`.
The bridge forwards both and holds nothing, so a console that reconnects has lost no history.

Station login
-------------
A console given the engine's station token presents it in every `hello`, reconnections included
(handoff A-2, closed 2026-10-16). An engine that refuses it says why, and the console shows the
reason and does not retry: a wrong token stays wrong.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtNetwork import QAbstractSocket, QTcpSocket

from ureasim.net import protocol
from ureasim.net.protocol import FrameReader, Kind, ProtocolError, Role

log = logging.getLogger(__name__)

#: Reconnect backoff [ms]: quick first retry, then ease off so a server that is down does
#: not get hammered, capped so a console recovers promptly once it comes back.
RECONNECT_MS = (500, 1000, 2000, 5000)

#: No snapshot for this long means the link is stale even if the socket still looks open —
#: a half-open TCP connection reports nothing until it is written to.
STALE_MS = 5000


class EngineBridge(QObject):
    """This console's link to the plant.

    Signals
    -------
    snapshot(mapping)
        A new plant state.
    status(text, level)
        Engine or link health for the status bar. ``level`` is ok / warn / fault.
    audit_event(text)
        An accepted command from any station, including this one — the audit feed.
        Named `audit_event`, not `event`: `QObject.event()` is the virtual Qt calls for
        every event delivery, and a signal of that name replaces it. The process then
        crashes on construction, which is how this was found.
    command_result(cmd_id, ok, reason)
        The outcome of a command this console sent.
    role_changed(role)
        The role the server actually granted, which may differ from the one requested.
    assignment_changed(text)
        The plant sections this station holds, as a display string. Empty means
        unrestricted.
    roster_changed(stations)
        The connected stations, each ``{station, role, sections}`` — sent to instructors.
    exercises_received(names, reason)
        The saved exercises' names, answering `request_exercises`; ``reason`` is the server's
        when it gave none.
    history_received(req_id, ok, reason, result)
        The historian's answer to `request_history` or `request_history_paths`: its
        ``history_data`` result, or the reason it was refused.
    """

    snapshot = pyqtSignal(object)
    status = pyqtSignal(str, str)
    audit_event = pyqtSignal(str)
    command_result = pyqtSignal(int, bool, str)
    role_changed = pyqtSignal(str)
    assignment_changed = pyqtSignal(str)
    roster_changed = pyqtSignal(object)
    exercises_received = pyqtSignal(object, str)
    history_received = pyqtSignal(int, bool, str, object)

    def __init__(self, station: str = "station", role: Role = Role.OPERATOR,
                 parent: QObject | None = None, *, token: str | None = None):
        super().__init__(parent)
        self._station = station
        self._requested_role = Role(role)
        #: The engine's station token, presented in every `hello`; ``None`` presents none.
        self._token = token
        self._granted_role = Role.OBSERVER
        self._sections: list[str] | None = None
        self._host = ""
        self._port = 0

        self._socket = QTcpSocket(self)
        self._frames = FrameReader()
        self._latest: Mapping[str, Any] = {}
        self._next_command_id = 1
        self._attempt = 0
        self._connected = False
        #: True once the server has refused this console: no retry until `connect_to` again.
        self._refused = False

        self._socket.readyRead.connect(self._on_ready_read)
        self._socket.connected.connect(self._on_connected)
        self._socket.disconnected.connect(self._on_disconnected)
        self._socket.errorOccurred.connect(self._on_error)

        self._retry = QTimer(self)
        self._retry.setSingleShot(True)
        self._retry.timeout.connect(self._attempt_connect)

        # Watchdog for a half-open link: the socket can stay "connected" long after the
        # far end has gone, and only the absence of snapshots reveals it.
        self._stale = QTimer(self)
        self._stale.setInterval(STALE_MS)
        self._stale.timeout.connect(self._on_stale)

    # ----------------------------------------------------------------------------------
    # Connection
    # ----------------------------------------------------------------------------------

    def connect_to(self, host: str, port: int) -> None:
        """Connect to a station server, retrying until it succeeds or `close` is called."""
        self._host = host
        self._port = port
        self._attempt = 0
        self._refused = False
        self._attempt_connect()

    def _attempt_connect(self) -> None:
        self.status.emit(f"connecting to {self._host}:{self._port} …", "warn")
        self._frames.reset()
        self._socket.abort()
        self._socket.connectToHost(self._host, self._port)

    def close(self) -> None:
        """Disconnect and stop retrying."""
        self._retry.stop()
        self._stale.stop()
        self._socket.abort()
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def role(self) -> Role:
        """The role the SERVER granted. Never assume the requested one was allowed."""
        return self._granted_role

    @property
    def sections(self) -> list[str] | None:
        """Plant sections this station may command; ``None`` means unrestricted."""
        return self._sections

    @property
    def latest(self) -> Mapping[str, Any]:
        """The most recent snapshot. Empty while the link is down."""
        return self._latest

    @property
    def running(self) -> bool:
        """True when this console is attached to a server that has an engine."""
        return self._connected

    # ----------------------------------------------------------------------------------
    # Socket events
    # ----------------------------------------------------------------------------------

    def _on_connected(self) -> None:
        self._attempt = 0
        self._socket.write(protocol.encode(
            protocol.hello(self._requested_role, self._station, self._token)))
        self._stale.start()

    def _on_disconnected(self) -> None:
        self._connected = False
        self._stale.stop()
        if self._refused:
            return                                  # the refusal's reason stays on the bar
        self._go_blank("link lost")
        self._schedule_retry()

    def _on_error(self, _error: QAbstractSocket.SocketError) -> None:
        self._connected = False
        self._stale.stop()
        if self._refused:
            return
        self._go_blank(self._socket.errorString())
        self._schedule_retry()

    def _on_stale(self) -> None:
        """No snapshot within the watchdog window: treat the link as dead."""
        self._go_blank("no data from the engine")
        self._socket.abort()
        self._schedule_retry()

    def _schedule_retry(self) -> None:
        if not self._host or self._refused:
            return
        delay = RECONNECT_MS[min(self._attempt, len(RECONNECT_MS) - 1)]
        self._attempt += 1
        self._retry.start(delay)

    def _go_blank(self, reason: str) -> None:
        """Drive every indicator back to `--` and say why.

        A console that keeps displaying the last values it received looks live and is not.
        On a training simulator that teaches a trainee to trust a frozen screen, which is
        the worst habit an operator can acquire.
        """
        self._latest = {}
        self.snapshot.emit({})
        self.status.emit(f"DISCONNECTED — {reason}", "fault")

    def _on_ready_read(self) -> None:
        try:
            for message in self._frames.feed(bytes(self._socket.readAll())):
                self._dispatch(message)
        except ProtocolError as exc:
            log.error("protocol error from server: %s", exc)
            self._go_blank(f"protocol error: {exc}")
            self._socket.abort()
            self._schedule_retry()

    # ----------------------------------------------------------------------------------
    # Message dispatch
    # ----------------------------------------------------------------------------------

    def _dispatch(self, message: Mapping[str, Any]) -> None:
        kind = message.get("t")

        if kind == Kind.SNAPSHOT.value:
            self._stale.start()                     # restart the watchdog
            state = message.get("state") or {}
            self._latest = state
            self.snapshot.emit(state)

        elif kind == Kind.WELCOME.value:
            self._connected = True
            granted = Role(str(message.get("role", Role.OBSERVER.value)))
            self._granted_role = granted
            self.role_changed.emit(granted.value)
            self._apply_sections(message.get("sections"))
            engine = message.get("engine", "unattached")
            if granted is not self._requested_role:
                # Say so loudly. A trainee who believes they are an operator but was
                # granted observer will read every refusal as a plant fault.
                self.status.emit(
                    f"connected as {granted.value} — requested "
                    f"{self._requested_role.value} — engine: {engine}", "warn")
            else:
                self.status.emit(f"connected as {granted.value} — engine: {engine}",
                                 "ok" if engine != "unattached" else "warn")

        elif kind == Kind.REFUSED.value:
            reason = str(message.get("reason", "refused"))
            log.error("server refused the connection: %s", reason)
            # No retry: the reason will not change. The flag is set before the abort, whose
            # `disconnected` would otherwise schedule one (a refused token retried every few
            # seconds, found in session 56).
            self._refused = True
            self._connected = False
            self._retry.stop()
            self._stale.stop()
            self._latest = {}
            self.snapshot.emit({})
            self.status.emit(f"REFUSED — {reason}", "fault")
            self._socket.abort()

        elif kind == Kind.STATUS.value:
            self.status.emit(str(message.get("text", "")), str(message.get("level", "ok")))

        elif kind == Kind.ACK.value:
            self.command_result.emit(int(message.get("id", 0)),
                                     bool(message.get("ok")),
                                     str(message.get("reason", "")))

        elif kind == Kind.ASSIGNMENT.value:
            self._apply_sections(message.get("sections"))

        elif kind == Kind.EVENT.value:
            self.audit_event.emit(str(message.get("text", "")))

        elif kind == Kind.ROSTER.value:
            self.roster_changed.emit(list(message.get("stations") or []))

        elif kind == Kind.EXERCISES.value:
            self.exercises_received.emit(list(message.get("names") or []),
                                         "" if message.get("ok") else str(message.get("reason")))

        elif kind == Kind.HISTORY_DATA.value:
            self.history_received.emit(int(message.get("id", 0)), bool(message.get("ok")),
                                       str(message.get("reason", "")), message.get("result"))

    def _apply_sections(self, sections) -> None:
        """Record and announce this station's assigned plant.

        ``None`` is unrestricted and shows nothing; an EMPTY list is 'assigned nothing' and
        must be visible, or a trainee sees every command refused with no explanation on the
        screen in front of them.
        """
        self._sections = None if sections is None else [str(s) for s in sections]
        if self._sections is None:
            self.assignment_changed.emit("")
        elif not self._sections:
            self.assignment_changed.emit("NO PLANT ASSIGNED")
        else:
            self.assignment_changed.emit("UNITS " + " ".join(sorted(self._sections)))

    # ----------------------------------------------------------------------------------
    # Commands
    # ----------------------------------------------------------------------------------

    def send_command(self, command: Mapping[str, Any]) -> int:
        """Send an operator action. Returns its id, or 0 if the link is down.

        The result arrives later on `command_result`, carrying the engine's own reason for
        any refusal — a latched trip, an interlock, or a role that does not allow it.
        """
        if not self._connected:
            return 0
        cmd_id = self._next_command_id
        self._next_command_id += 1
        self._socket.write(protocol.encode(protocol.command(cmd_id, command)))
        return cmd_id

    def request_exercises(self) -> bool:
        """Ask the server for the saved exercises; the answer arrives on `exercises_received`."""
        if not self._connected:
            return False
        self._socket.write(protocol.encode(protocol.exercise_list(self._next_command_id)))
        self._next_command_id += 1
        return True

    def request_history(self, paths, span_s: float, max_points: int = 800,
                        end_sim: float | None = None) -> int:
        """Ask the historian for ``span_s`` plant seconds of ``paths`` ending at ``end_sim`` (the
        newest sample when None). Returns the request's id, or 0 if the link is down; the
        answer arrives on `history_received` with that id."""
        if not self._connected:
            return 0
        req_id = self._next_command_id
        self._next_command_id += 1
        self._socket.write(protocol.encode(
            protocol.history(req_id, list(paths), float(span_s), int(max_points), end_sim)))
        return req_id

    def request_history_paths(self) -> int:
        """Ask which paths the historian records. Returns the request's id, or 0 if the link
        is down; the answer arrives on `history_received`."""
        if not self._connected:
            return 0
        req_id = self._next_command_id
        self._next_command_id += 1
        self._socket.write(protocol.encode(protocol.history_paths(req_id)))
        return req_id

    def shutdown(self) -> None:
        """Close the link. Called when the console window closes."""
        self.close()


__all__ = ["EngineBridge", "RECONNECT_MS", "STALE_MS"]
