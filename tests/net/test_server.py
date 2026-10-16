"""Station server: fan-out, role enforcement, audit broadcast, late joiners.

These run against a real socket on an ephemeral port, because the behaviours that matter —
several stations receiving one encoded frame, a refusal reaching the station that caused
it, a late joiner being brought up to date — are exactly the ones an in-process fake would
not exercise.
"""

from __future__ import annotations

import asyncio
import contextlib

from ureasim.net import protocol
from ureasim.net.protocol import FrameReader, Kind, Role
from ureasim.net.server import StationServer

class Client:
    """A minimal asyncio station, used only by these tests.

    The roster an instructor console is sent whenever a station joins, leaves or is assigned
    arrives apart from the request-and-answer flow, so it is filed in `rosters`, not `inbox`.
    """

    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.frames = FrameReader()
        self.inbox: list[dict] = []
        self.rosters: list[dict] = []

    @classmethod
    async def connect(cls, port: int, role: Role, name: str) -> "Client":
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        client = cls(reader, writer)
        await client.send(protocol.hello(role, name))
        return client

    async def send(self, message) -> None:
        self.writer.write(protocol.encode(message))
        await self.writer.drain()

    async def pump(self, expect: int = 1, timeout: float = 2.0) -> list[dict]:
        """Read until `expect` messages have arrived, or fail the test on timeout."""
        deadline = asyncio.get_running_loop().time() + timeout
        while len(self.inbox) < expect:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise AssertionError(
                    f"timed out waiting for {expect} messages; got "
                    f"{[m['t'] for m in self.inbox]}")
            chunk = await asyncio.wait_for(self.reader.read(65536), remaining)
            if not chunk:
                break
            for m in self.frames.feed(chunk):
                (self.rosters if m["t"] == Kind.ROSTER.value else self.inbox).append(m)
        return self.inbox

    async def settle(self, timeout: float = 0.2) -> None:
        """Read whatever arrives within ``timeout`` (the asynchronous roster)."""
        with contextlib.suppress(asyncio.TimeoutError):
            while True:
                chunk = await asyncio.wait_for(self.reader.read(65536), timeout)
                if not chunk:
                    return
                for m in self.frames.feed(chunk):
                    (self.rosters if m["t"] == Kind.ROSTER.value else self.inbox).append(m)

    def of_kind(self, kind: Kind) -> list[dict]:
        if kind is Kind.ROSTER:
            return self.rosters
        return [m for m in self.inbox if m["t"] == kind.value]

    async def close(self) -> None:
        self.writer.close()


def run(coro):
    """Drive one coroutine to completion on a fresh event loop."""
    return asyncio.run(coro)


# --------------------------------------------------------------------------------------
# Handshake
# --------------------------------------------------------------------------------------

def test_handshake_grants_the_requested_role():
    async def scenario():
        server = StationServer(engine_name="test-engine")
        port = await server.start("127.0.0.1", 0)
        client = await Client.connect(port, Role.OPERATOR, "trainee-1")
        # welcome + the immediate catch-up snapshot
        await client.pump(2)
        welcome = client.of_kind(Kind.WELCOME)[0]
        assert welcome["role"] == "operator"
        assert welcome["engine"] == "test-engine"
        assert welcome["protocol"] == protocol.PROTOCOL_VERSION
        await client.close()
        await server.stop()
    run(scenario())


def test_wrong_protocol_version_is_refused():
    async def scenario():
        server = StationServer()
        port = await server.start("127.0.0.1", 0)
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        bad = protocol.hello(Role.OPERATOR, "x")
        bad["protocol"] = protocol.PROTOCOL_VERSION + 99
        writer.write(protocol.encode(bad))
        await writer.drain()
        frames = FrameReader()
        messages = list(frames.feed(await asyncio.wait_for(reader.read(65536), 2.0)))
        assert messages[0]["t"] == Kind.REFUSED.value
        assert "protocol version" in messages[0]["reason"]
        writer.close()
        await server.stop()
    run(scenario())


def test_command_before_hello_is_refused():
    async def scenario():
        server = StationServer(command_handler=lambda c, s: (True, ""))
        port = await server.start("127.0.0.1", 0)
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(protocol.encode(protocol.command(1, {"type": "pump_toggle"})))
        await writer.drain()
        frames = FrameReader()
        messages = list(frames.feed(await asyncio.wait_for(reader.read(65536), 2.0)))
        assert messages[0]["t"] == Kind.REFUSED.value
        writer.close()
        await server.stop()
    run(scenario())


# --------------------------------------------------------------------------------------
# Fan-out
# --------------------------------------------------------------------------------------

def test_every_station_sees_the_same_snapshot():
    """The point of the whole exercise: one plant, several consoles."""
    async def scenario():
        server = StationServer()
        port = await server.start("127.0.0.1", 0)
        instructor = await Client.connect(port, Role.INSTRUCTOR, "instructor")
        trainee_a = await Client.connect(port, Role.OPERATOR, "trainee-a")
        trainee_b = await Client.connect(port, Role.OPERATOR, "trainee-b")
        for c in (instructor, trainee_a, trainee_b):
            await c.pump(2)                       # welcome + catch-up snapshot

        server.publish({"PT_329201": 140.7, "pumpA": {"on": True}}, t_plant=12.5)

        for c in (instructor, trainee_a, trainee_b):
            await c.pump(3)
            latest = c.of_kind(Kind.SNAPSHOT)[-1]
            assert latest["state"]["PT_329201"] == 140.7
            assert latest["state"]["pumpA"]["on"] is True
            assert latest["t_plant"] == 12.5
            await c.close()
        await server.stop()
    run(scenario())


def test_snapshot_sequence_increments():
    """A console uses `seq` to notice a dropped or reordered frame."""
    async def scenario():
        server = StationServer()
        port = await server.start("127.0.0.1", 0)
        client = await Client.connect(port, Role.OBSERVER, "obs")
        await client.pump(2)
        for i in range(3):
            server.publish({"n": i})
        await client.pump(5)
        seqs = [m["seq"] for m in client.of_kind(Kind.SNAPSHOT)]
        assert seqs == sorted(seqs)
        assert seqs[-1] - seqs[0] == 3
        await client.close()
        await server.stop()
    run(scenario())


def test_late_joiner_gets_current_state_and_status():
    """A console that connects mid-exercise must not sit blank until the next publish."""
    async def scenario():
        server = StationServer()
        port = await server.start("127.0.0.1", 0)
        server.publish({"PT_329201": 141.2}, t_plant=99.0)
        server.publish_status("running", "ok")

        late = await Client.connect(port, Role.OPERATOR, "late")
        await late.pump(3)                        # welcome + status + snapshot
        assert late.of_kind(Kind.STATUS)[0]["text"] == "running"
        assert late.of_kind(Kind.SNAPSHOT)[0]["state"]["PT_329201"] == 141.2
        await late.close()
        await server.stop()
    run(scenario())


# --------------------------------------------------------------------------------------
# Commands, roles and audit
# --------------------------------------------------------------------------------------

def test_operator_command_reaches_the_engine_and_is_broadcast():
    async def scenario():
        seen = []

        def handler(cmd, station):
            seen.append((dict(cmd), station))
            return True, ""

        server = StationServer(command_handler=handler, engine_name="e")
        port = await server.start("127.0.0.1", 0)
        instructor = await Client.connect(port, Role.INSTRUCTOR, "instructor")
        trainee = await Client.connect(port, Role.OPERATOR, "trainee-a")
        for c in (instructor, trainee):
            await c.pump(2)

        await trainee.send(protocol.command(1, {"type": "pump_toggle", "id": "A"}))

        await trainee.pump(4)                     # + ack + event
        assert seen == [({"type": "pump_toggle", "id": "A"}, "trainee-a")]
        ack = trainee.of_kind(Kind.ACK)[0]
        assert ack["id"] == 1 and ack["ok"] is True

        # The instructor sees the trainee's action without asking for it.
        await instructor.pump(3)
        audit = instructor.of_kind(Kind.EVENT)[0]
        assert audit["station"] == "trainee-a"
        assert audit["cmd"]["type"] == "pump_toggle"
        assert "trainee-a" in audit["text"] and "pump_toggle" in audit["text"]

        for c in (instructor, trainee):
            await c.close()
        await server.stop()
    run(scenario())


def test_trainee_cannot_inject_a_malfunction():
    """The central authorisation rule. A trainee who can clear their own fault is not
    being trained."""
    async def scenario():
        called = []
        server = StationServer(command_handler=lambda c, s: (called.append(c), (True, ""))[1])
        port = await server.start("127.0.0.1", 0)
        trainee = await Client.connect(port, Role.OPERATOR, "trainee-a")
        await trainee.pump(2)

        await trainee.send(protocol.command(
            5, {"type": "trigger_fault", "id": "pumpA_fault"}))
        await trainee.pump(3)

        ack = trainee.of_kind(Kind.ACK)[0]
        assert ack["ok"] is False
        assert "operator" in ack["reason"] and "trigger_fault" in ack["reason"]
        assert called == [], "the command must not reach the engine at all"
        assert trainee.of_kind(Kind.EVENT) == [], "a refused command is not an audit event"

        await trainee.close()
        await server.stop()
    run(scenario())


def test_instructor_may_inject_a_malfunction():
    async def scenario():
        called = []

        def handler(cmd, station):
            called.append(cmd["type"])
            return True, ""

        server = StationServer(command_handler=handler)
        port = await server.start("127.0.0.1", 0)
        instructor = await Client.connect(port, Role.INSTRUCTOR, "instructor")
        await instructor.pump(2)
        await instructor.send(protocol.command(1, {"type": "trigger_fault", "id": "x"}))
        await instructor.pump(4)
        assert called == ["trigger_fault"]
        assert instructor.of_kind(Kind.ACK)[0]["ok"] is True
        await instructor.close()
        await server.stop()
    run(scenario())


def test_observer_cannot_command():
    async def scenario():
        server = StationServer(command_handler=lambda c, s: (True, ""))
        port = await server.start("127.0.0.1", 0)
        observer = await Client.connect(port, Role.OBSERVER, "obs")
        await observer.pump(2)
        await observer.send(protocol.command(1, {"type": "pump_toggle", "id": "A"}))
        await observer.pump(3)
        assert observer.of_kind(Kind.ACK)[0]["ok"] is False
        await observer.close()
        await server.stop()
    run(scenario())


def test_engine_refusal_reaches_the_operator_with_its_reason():
    """A process interlock is the ENGINE's decision, not the server's, and its reason must
    travel all the way back to the operator who tried."""
    async def scenario():
        def handler(cmd, station):
            return False, "start blocked by latched trip 21_2"

        server = StationServer(command_handler=handler)
        port = await server.start("127.0.0.1", 0)
        trainee = await Client.connect(port, Role.OPERATOR, "trainee-a")
        await trainee.pump(2)
        await trainee.send(protocol.command(9, {"type": "pump_toggle", "id": "A"}))
        await trainee.pump(3)
        ack = trainee.of_kind(Kind.ACK)[0]
        assert ack["id"] == 9 and ack["ok"] is False
        assert ack["reason"] == "start blocked by latched trip 21_2"
        assert trainee.of_kind(Kind.EVENT) == []
        await trainee.close()
        await server.stop()
    run(scenario())


def test_no_engine_attached_is_said_not_swallowed():
    async def scenario():
        server = StationServer()                  # no handler
        port = await server.start("127.0.0.1", 0)
        trainee = await Client.connect(port, Role.OPERATOR, "trainee-a")
        await trainee.pump(2)
        await trainee.send(protocol.command(1, {"type": "pump_toggle", "id": "A"}))
        await trainee.pump(3)
        assert trainee.of_kind(Kind.ACK)[0]["reason"] == "no engine attached"
        await trainee.close()
        await server.stop()
    run(scenario())


def test_command_without_a_type_is_refused():
    async def scenario():
        server = StationServer(command_handler=lambda c, s: (True, ""))
        port = await server.start("127.0.0.1", 0)
        trainee = await Client.connect(port, Role.OPERATOR, "t")
        await trainee.pump(2)
        await trainee.send(protocol.command(1, {"id": "A"}))
        await trainee.pump(3)
        assert "type" in trainee.of_kind(Kind.ACK)[0]["reason"]
        await trainee.close()
        await server.stop()
    run(scenario())


def test_a_raising_handler_does_not_take_the_server_down():
    """One bad command must not disconnect every other console."""
    async def scenario():
        def handler(cmd, station):
            raise RuntimeError("solver diverged")

        server = StationServer(command_handler=handler)
        port = await server.start("127.0.0.1", 0)
        trainee = await Client.connect(port, Role.OPERATOR, "t")
        await trainee.pump(2)
        await trainee.send(protocol.command(1, {"type": "pump_toggle", "id": "A"}))
        await trainee.pump(3)
        ack = trainee.of_kind(Kind.ACK)[0]
        assert ack["ok"] is False and "solver diverged" in ack["reason"]

        # Still serving: the next publish arrives.
        server.publish({"ok": 1})
        await trainee.pump(4)
        assert trainee.of_kind(Kind.SNAPSHOT)[-1]["state"] == {"ok": 1}
        await trainee.close()
        await server.stop()
    run(scenario())


# --------------------------------------------------------------------------------------
# Bookkeeping
# --------------------------------------------------------------------------------------

def test_station_roster_tracks_connections():
    async def scenario():
        server = StationServer()
        port = await server.start("127.0.0.1", 0)
        assert server.station_count == 0
        a = await Client.connect(port, Role.INSTRUCTOR, "instructor")
        b = await Client.connect(port, Role.OPERATOR, "trainee-a")
        await a.pump(2)
        await b.pump(2)
        assert server.station_count == 2
        roster = " ".join(server.stations())
        assert "instructor" in roster and "trainee-a" in roster
        await a.close()
        await b.close()
        await server.stop()
    run(scenario())


def test_ping_is_answered():
    async def scenario():
        server = StationServer()
        port = await server.start("127.0.0.1", 0)
        client = await Client.connect(port, Role.OBSERVER, "obs")
        await client.pump(2)
        await client.send(protocol.ping(42))
        await client.pump(3)
        assert client.of_kind(Kind.PONG)[0]["id"] == 42
        await client.close()
        await server.stop()
    run(scenario())


# --------------------------------------------------------------------------------------
# Unit assignment (handoff A-8)
# --------------------------------------------------------------------------------------

def test_unassigned_station_is_unrestricted():
    """Assignment is a narrowing an instructor applies.

    A classroom that has not set one up must behave exactly as it did before.
    """
    async def scenario():
        saw = []

        def handler(cmd, station):
            saw.append(cmd["type"])
            return True, ""

        server = StationServer(command_handler=handler)
        port = await server.start("127.0.0.1", 0)
        trainee = await Client.connect(port, Role.OPERATOR, "trainee-a")
        await trainee.pump(2)
        assert trainee.of_kind(Kind.WELCOME)[0]["sections"] is None

        for cmd in ({"type": "controller_set", "tag": "LIC-322501"},
                    {"type": "controller_set", "tag": "TIC-323007"},
                    {"type": "steam_hpvent_set", "v": 0}):
            await trainee.send(protocol.command(1, cmd))
        await trainee.pump(5)
        assert saw == ["controller_set", "controller_set", "steam_hpvent_set"]
        assert all(m["ok"] for m in trainee.of_kind(Kind.ACK))
        await trainee.close()
        await server.stop()
    run(scenario())


def test_assigned_station_is_held_to_its_sections():
    """The whole point: two trainees cannot reach into one another plant sections."""
    async def scenario():
        saw = []

        def handler(cmd, station):
            saw.append((cmd["type"], station))
            return True, ""

        server = StationServer(command_handler=handler)
        port = await server.start("127.0.0.1", 0)
        instructor = await Client.connect(port, Role.INSTRUCTOR, "instructor")
        trainee = await Client.connect(port, Role.OPERATOR, "trainee-a")
        for c in (instructor, trainee):
            await c.pump(2)

        await instructor.send(protocol.command(
            1, {"type": "assign", "station": "trainee-a", "sections": ["323"]}))
        await instructor.pump(5)
        assert instructor.of_kind(Kind.ACK)[0]["ok"] is True

        # The trainee is told, so the status bar can show it.
        await trainee.pump(4)
        assert trainee.of_kind(Kind.ASSIGNMENT)[0]["sections"] == ["323"]

        # Inside the assignment: allowed.
        await trainee.send(protocol.command(
            10, {"type": "controller_set", "tag": "TIC-323007"}))
        # Outside it: refused, by name, before the engine sees it.
        await trainee.send(protocol.command(
            11, {"type": "controller_set", "tag": "LIC-322501"}))
        await trainee.pump(7)

        acks = {m["id"]: m for m in trainee.of_kind(Kind.ACK)}
        assert acks[10]["ok"] is True
        assert acks[11]["ok"] is False
        assert "LIC-322501" in acks[11]["reason"]
        assert "322" in acks[11]["reason"] and "323" in acks[11]["reason"]
        assert saw.count(("controller_set", "trainee-a")) == 1, \
            "the out-of-scope command must not reach the engine"

        for c in (instructor, trainee):
            await c.close()
        await server.stop()
    run(scenario())


def test_assigned_station_fails_closed_on_an_unattributable_command():
    """A command the resolver cannot attribute must not become a hole in the assignment."""
    async def scenario():
        saw = []

        def handler(cmd, station):
            saw.append(cmd["type"])
            return True, ""

        server = StationServer(command_handler=handler)
        port = await server.start("127.0.0.1", 0)
        instructor = await Client.connect(port, Role.INSTRUCTOR, "instructor")
        trainee = await Client.connect(port, Role.OPERATOR, "trainee-a")
        for c in (instructor, trainee):
            await c.pump(2)
        await instructor.send(protocol.command(
            1, {"type": "assign", "station": "trainee-a", "sections": ["323"]}))
        await instructor.pump(4)
        await trainee.pump(4)

        # `trip_reset` with no id clears every latch in the plant.
        await trainee.send(protocol.command(20, {"type": "trip_reset"}))
        await trainee.pump(5)
        ack = [m for m in trainee.of_kind(Kind.ACK) if m["id"] == 20][0]
        assert ack["ok"] is False
        assert "trip_reset" in ack["reason"]
        assert saw == []

        for c in (instructor, trainee):
            await c.close()
        await server.stop()
    run(scenario())


def test_instructor_is_never_restricted():
    async def scenario():
        saw = []

        def handler(cmd, station):
            saw.append(cmd["type"])
            return True, ""

        server = StationServer(command_handler=handler)
        port = await server.start("127.0.0.1", 0)
        instructor = await Client.connect(port, Role.INSTRUCTOR, "instructor")
        await instructor.pump(2)
        # An instructor may even assign themselves a section; it must not bind them.
        await instructor.send(protocol.command(
            1, {"type": "assign", "station": "instructor", "sections": ["323"]}))
        await instructor.pump(5)
        await instructor.send(protocol.command(
            2, {"type": "controller_set", "tag": "LIC-322501"}))
        # welcome, catch-up snapshot, assign ack, assignment, assign event,
        # controller_set ack, controller_set event.
        await instructor.pump(7)
        acks = {m["id"]: m for m in instructor.of_kind(Kind.ACK)}
        assert acks[2]["ok"] is True
        assert "controller_set" in saw
        await instructor.close()
        await server.stop()
    run(scenario())


def test_assignment_survives_a_reconnect():
    """Assignments are keyed by station NAME.

    A trainee whose console drops mid-exercise must come back holding the same plant, not
    silently unrestricted.
    """
    async def scenario():
        server = StationServer(command_handler=lambda c, s: (True, ""))
        port = await server.start("127.0.0.1", 0)
        instructor = await Client.connect(port, Role.INSTRUCTOR, "instructor")
        trainee = await Client.connect(port, Role.OPERATOR, "trainee-a")
        for c in (instructor, trainee):
            await c.pump(2)
        await instructor.send(protocol.command(
            1, {"type": "assign", "station": "trainee-a", "sections": ["328", "329"]}))
        await instructor.pump(4)
        await trainee.close()
        await asyncio.sleep(0.05)

        again = await Client.connect(port, Role.OPERATOR, "trainee-a")
        await again.pump(2)
        assert again.of_kind(Kind.WELCOME)[0]["sections"] == ["328", "329"]
        await again.close()
        await instructor.close()
        await server.stop()
    run(scenario())


def test_assigning_an_unknown_section_is_refused_not_dropped():
    """A typo that silently assigned nothing would lock a trainee out of a plant the
    instructor believes they are holding."""
    async def scenario():
        server = StationServer(command_handler=lambda c, s: (True, ""))
        port = await server.start("127.0.0.1", 0)
        instructor = await Client.connect(port, Role.INSTRUCTOR, "instructor")
        await instructor.pump(2)
        await instructor.send(protocol.command(
            1, {"type": "assign", "station": "trainee-a", "sections": ["323", "999"]}))
        await instructor.pump(3)
        ack = instructor.of_kind(Kind.ACK)[0]
        assert ack["ok"] is False and "999" in ack["reason"]
        assert server.assignment_of("trainee-a") is None
        await instructor.close()
        await server.stop()
    run(scenario())


def test_assignment_can_be_cleared():
    async def scenario():
        server = StationServer(command_handler=lambda c, s: (True, ""))
        port = await server.start("127.0.0.1", 0)
        instructor = await Client.connect(port, Role.INSTRUCTOR, "instructor")
        await instructor.pump(2)
        await instructor.send(protocol.command(
            1, {"type": "assign", "station": "trainee-a", "sections": ["323"]}))
        await instructor.pump(4)
        assert server.assignment_of("trainee-a") == {"323"}
        await instructor.send(protocol.command(
            2, {"type": "assign", "station": "trainee-a", "sections": None}))
        await instructor.pump(7)
        assert server.assignment_of("trainee-a") is None
        await instructor.close()
        await server.stop()
    run(scenario())


def test_a_trainee_cannot_assign():
    """Otherwise the restriction is self-service and means nothing."""
    async def scenario():
        server = StationServer(command_handler=lambda c, s: (True, ""))
        port = await server.start("127.0.0.1", 0)
        trainee = await Client.connect(port, Role.OPERATOR, "trainee-a")
        await trainee.pump(2)
        await trainee.send(protocol.command(
            1, {"type": "assign", "station": "trainee-a", "sections": None}))
        await trainee.pump(3)
        ack = trainee.of_kind(Kind.ACK)[0]
        assert ack["ok"] is False and "assign" in ack["reason"]
        await trainee.close()
        await server.stop()
    run(scenario())


def test_station_roster_shows_the_assignment():
    """The instructor roster has to say who is holding what."""
    async def scenario():
        server = StationServer(command_handler=lambda c, s: (True, ""))
        port = await server.start("127.0.0.1", 0)
        instructor = await Client.connect(port, Role.INSTRUCTOR, "instructor")
        trainee = await Client.connect(port, Role.OPERATOR, "trainee-a")
        for c in (instructor, trainee):
            await c.pump(2)
        await instructor.send(protocol.command(
            1, {"type": "assign", "station": "trainee-a", "sections": ["323", "328"]}))
        await instructor.pump(4)
        roster = " | ".join(server.stations())
        assert "trainee-a (operator, 323,328" in roster
        assert "instructor (instructor, all" in roster
        for c in (instructor, trainee):
            await c.close()
        await server.stop()
    run(scenario())


def test_an_engine_that_answers_later_is_acked_when_it_answers():
    """The engine host answers on a future: the ack and the audit event wait for it, and a
    refusal still carries the engine's reason."""
    async def scenario():
        loop = asyncio.get_running_loop()
        pending: list = []

        def handler(cmd, station):
            fut = loop.create_future()
            pending.append((cmd, fut))
            return fut
        server = StationServer(command_handler=handler)
        port = await server.start("127.0.0.1", 0)
        op = await Client.connect(port, Role.OPERATOR, "trainee-1")
        await op.pump(2)
        await op.send(protocol.command(1, {"type": "hic605_set", "op": 45.0}))
        await op.send(protocol.command(2, {"type": "xv_toggle", "id": "322915"}))
        while len(pending) < 2:
            await asyncio.sleep(0.01)
        assert not op.of_kind(Kind.ACK)
        pending[0][1].set_result((True, ""))
        pending[1][1].set_result((False, "held shut by I 22.1"))
        await op.pump(5)
        acks = op.of_kind(Kind.ACK)
        assert [(a["id"], a["ok"]) for a in acks] == [(1, True), (2, False)]
        assert acks[1]["reason"] == "held shut by I 22.1"
        assert [e["cmd"]["type"] for e in op.of_kind(Kind.EVENT)] == ["hic605_set"]
        await op.close()
        await server.stop()
    run(scenario())


def test_history_is_answered_for_every_role_and_refused_without_an_engine():
    async def scenario():
        server = StationServer()
        port = await server.start("127.0.0.1", 0)
        obs = await Client.connect(port, Role.OBSERVER, "visitor")
        await obs.pump(2)
        await obs.send(protocol.history(1, ["a.b"], 60.0))
        await obs.pump(3)
        assert obs.of_kind(Kind.HISTORY_DATA)[0]["reason"] == "no engine attached"
        server.set_history_handler(lambda m: {"series": {"a.b": [1.0, float("nan")]}})
        await obs.send(protocol.history(2, ["a.b"], 60.0))
        await obs.pump(4)
        reply = obs.of_kind(Kind.HISTORY_DATA)[1]
        assert reply["ok"] and reply["result"] == {"series": {"a.b": [1.0, None]}}
        await obs.close()
        await server.stop()
    run(scenario())


def test_a_value_the_engine_could_not_compute_is_published_as_none():
    """A NaN in the plant state is not JSON: the snapshot goes out with None in its place,
    which a console shows as ``--``, instead of failing the publish."""
    async def scenario():
        server = StationServer()
        port = await server.start("127.0.0.1", 0)
        obs = await Client.connect(port, Role.OBSERVER, "visitor")
        await obs.pump(2)
        server.publish({"A": {"pv": float("nan"), "sp": 1.0}}, 0.1)
        await obs.pump(3)
        assert obs.of_kind(Kind.SNAPSHOT)[-1]["state"] == {"A": {"pv": None, "sp": 1.0}}
        await obs.close()
        await server.stop()
    run(scenario())


# --------------------------------------------------------------------------------------
# The instructor's lists
# --------------------------------------------------------------------------------------

def test_the_instructors_are_sent_the_roster_as_it_changes():
    """A station joining, being assigned and leaving: each instructor console is sent the roster
    every time; a trainee console never is."""
    async def scenario():
        server = StationServer(command_handler=lambda c, s: (True, ""))
        port = await server.start("127.0.0.1", 0)
        instructor = await Client.connect(port, Role.INSTRUCTOR, "instructor")
        await instructor.pump(2)
        trainee = await Client.connect(port, Role.OPERATOR, "trainee-a")
        await trainee.pump(2)
        await instructor.settle()
        assert instructor.of_kind(Kind.ROSTER)[-1]["stations"] == [
            {"station": "instructor", "role": "instructor", "sections": None},
            {"station": "trainee-a", "role": "operator", "sections": None}]
        await instructor.send(protocol.command(
            1, {"type": "assign", "station": "trainee-a", "sections": ["323"]}))
        await instructor.pump(4)
        await instructor.settle()
        assert instructor.of_kind(Kind.ROSTER)[-1]["stations"][1]["sections"] == ["323"]
        await trainee.close()
        await instructor.settle()
        assert [s["station"] for s in instructor.of_kind(Kind.ROSTER)[-1]["stations"]] == [
            "instructor"]
        await trainee.settle()
        assert trainee.of_kind(Kind.ROSTER) == []
        await instructor.close()
        await server.stop()
    run(scenario())


def test_the_exercises_are_listed_for_an_instructor_only():
    async def scenario():
        server = StationServer()
        port = await server.start("127.0.0.1", 0)
        instructor = await Client.connect(port, Role.INSTRUCTOR, "instructor")
        trainee = await Client.connect(port, Role.OPERATOR, "trainee-a")
        await trainee.pump(2)
        await instructor.send(protocol.exercise_list(1))
        await instructor.pump(3)
        assert instructor.of_kind(Kind.EXERCISES)[-1]["reason"] == "no engine attached"
        server.set_exercise_lister(lambda: ["shift-a", "trip-22-2"])
        await instructor.send(protocol.exercise_list(2))
        await trainee.send(protocol.exercise_list(3))
        await instructor.pump(4)
        await trainee.pump(3)
        assert instructor.of_kind(Kind.EXERCISES)[-1] == {
            "t": "exercises", "id": 2, "ok": True, "reason": "", "names": ["shift-a", "trip-22-2"]}
        refused = trainee.of_kind(Kind.EXERCISES)[-1]
        assert refused["ok"] is False and refused["names"] == []
        for c in (instructor, trainee):
            await c.close()
        await server.stop()
    run(scenario())
