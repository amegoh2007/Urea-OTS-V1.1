"""Console server: the handshake, commands to the engine, the audit echo, a reconnect.

These run against a real socket on an ephemeral port, because the behaviours that matter —
a refusal reaching the console with its reason, a reconnecting console brought up to date at
once — are exactly the ones an in-process fake would not exercise. The single console is
decision 149 (2026-10-22): no role, token or unit assignment is checked.
"""

from __future__ import annotations

import asyncio

import pytest

from ureasim.net import protocol
from ureasim.net import server as server_module
from ureasim.net.protocol import FrameReader, Kind
from ureasim.net.server import StationServer


class Client:
    """A minimal asyncio console, used only by these tests."""

    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.frames = FrameReader()
        self.inbox: list[dict] = []

    @classmethod
    async def connect(cls, port: int, name: str = "console") -> "Client":
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        client = cls(reader, writer)
        await client.send(protocol.hello(name))
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
            self.inbox.extend(self.frames.feed(chunk))
        return self.inbox

    def of_kind(self, kind: Kind) -> list[dict]:
        return [m for m in self.inbox if m["t"] == kind.value]

    async def close(self) -> None:
        self.writer.close()


def run(coro):
    """Drive one coroutine to completion on a fresh event loop."""
    return asyncio.run(coro)


# --------------------------------------------------------------------------------------
# Handshake
# --------------------------------------------------------------------------------------

def test_the_handshake_names_the_engine_and_checks_no_role():
    async def scenario():
        server = StationServer(engine_name="test-engine")
        port = await server.start("127.0.0.1", 0)
        client = await Client.connect(port, "console")
        # welcome + the immediate catch-up snapshot
        await client.pump(2)
        welcome = client.of_kind(Kind.WELCOME)[0]
        assert welcome == {"t": "welcome", "station": "console",
                           "protocol": protocol.PROTOCOL_VERSION, "engine": "test-engine"}
        await client.close()
        await server.stop()
    run(scenario())


def test_wrong_protocol_version_is_refused():
    """A console of the multi-station protocol (version 1, with its role and token) is refused
    with the reason, not misread."""
    async def scenario():
        server = StationServer()
        port = await server.start("127.0.0.1", 0)
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(protocol.encode({"t": "hello", "role": "operator", "station": "x",
                                      "protocol": 1}))
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


class _Writer:
    """A connection's writer that keeps what the server sends."""

    def __init__(self):
        self.sent = bytearray()

    def write(self, data: bytes) -> None:
        self.sent += data


@pytest.mark.parametrize("host, admitted", [
    ("127.0.0.1", True), ("127.5.0.9", True), ("::1", True), ("::ffff:127.0.0.1", True),
    ("10.0.0.5", False), ("192.168.1.20", False), ("fe80::1%eth0", False), ("", False),
])
def test_only_a_console_on_the_engines_machine_is_admitted(host, admitted):
    """The server binds the loopback interface; a peer elsewhere — a server bound wider — is
    refused at `hello`, since no login stands between it and the plant."""
    server = StationServer()
    writer = _Writer()
    station = server_module._Station(writer, f"{host}:50000", host)
    server._stations.add(station)
    server._handle(station, protocol.hello("console"))
    sent = list(FrameReader().feed(bytes(writer.sent)))
    assert station.ready is admitted
    if admitted:
        assert sent[0]["t"] == "welcome"
    else:
        assert [m["t"] for m in sent] == ["refused"]
        assert "its own machine" in sent[0]["reason"]


def test_the_default_host_is_the_loopback_interface():
    assert server_module.DEFAULT_HOST == "127.0.0.1"


# --------------------------------------------------------------------------------------
# Snapshots
# --------------------------------------------------------------------------------------

def test_the_console_sees_the_published_snapshot():
    async def scenario():
        server = StationServer()
        port = await server.start("127.0.0.1", 0)
        client = await Client.connect(port)
        await client.pump(2)                      # welcome + catch-up snapshot

        server.publish({"PT_329201": 140.7, "pumpA": {"on": True}}, t_plant=12.5)

        await client.pump(3)
        latest = client.of_kind(Kind.SNAPSHOT)[-1]
        assert latest["state"]["PT_329201"] == 140.7
        assert latest["state"]["pumpA"]["on"] is True
        assert latest["t_plant"] == 12.5
        await client.close()
        await server.stop()
    run(scenario())


def test_snapshot_sequence_increments():
    """A console uses `seq` to notice a dropped or reordered frame."""
    async def scenario():
        server = StationServer()
        port = await server.start("127.0.0.1", 0)
        client = await Client.connect(port)
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


def test_a_reconnecting_console_gets_current_state_and_status():
    """A console that reconnects mid-exercise must not sit blank until the next publish."""
    async def scenario():
        server = StationServer()
        port = await server.start("127.0.0.1", 0)
        server.publish({"PT_329201": 141.2}, t_plant=99.0)
        server.publish_status("running", "ok")

        late = await Client.connect(port)
        await late.pump(3)                        # welcome + status + snapshot
        assert late.of_kind(Kind.STATUS)[0]["text"] == "running"
        assert late.of_kind(Kind.SNAPSHOT)[0]["state"]["PT_329201"] == 141.2
        await late.close()
        await server.stop()
    run(scenario())


def test_a_reconnect_overlapping_its_old_connection_is_served():
    """While the old connection is not yet noticed closed, the new one is served too: a
    reconnecting console is never refused for its own stale link."""
    async def scenario():
        server = StationServer()
        port = await server.start("127.0.0.1", 0)
        old = await Client.connect(port)
        new = await Client.connect(port)
        for c in (old, new):
            await c.pump(2)
        assert server.station_count == 2
        server.publish({"n": 1})
        await new.pump(3)
        assert new.of_kind(Kind.SNAPSHOT)[-1]["state"] == {"n": 1}
        await old.close()
        await new.close()
        await server.stop()
    run(scenario())


# --------------------------------------------------------------------------------------
# Commands and audit
# --------------------------------------------------------------------------------------

def test_a_command_reaches_the_engine_and_is_echoed():
    async def scenario():
        seen = []

        def handler(cmd, station):
            seen.append((dict(cmd), station))
            return True, ""

        server = StationServer(command_handler=handler, engine_name="e")
        port = await server.start("127.0.0.1", 0)
        console = await Client.connect(port, "console")
        await console.pump(2)

        await console.send(protocol.command(1, {"type": "pump_toggle", "id": "A"}))

        await console.pump(4)                     # + ack + event
        assert seen == [({"type": "pump_toggle", "id": "A"}, "console")]
        ack = console.of_kind(Kind.ACK)[0]
        assert ack["id"] == 1 and ack["ok"] is True
        audit = console.of_kind(Kind.EVENT)[0]
        assert audit["station"] == "console" and audit["cmd"]["type"] == "pump_toggle"
        assert audit["text"] == "console: pump_toggle A"
        await console.close()
        await server.stop()
    run(scenario())


#: The simulator controls and the instructor's boundary, the multi-station deployment's
#: instructor-only commands (decision 149 removed the gate), and V1's ``*_fault`` suffix form.
SIMULATOR_COMMANDS = [
    "trigger_fault", "clear_fault", "reset_sim", "set_sim_mode", "freeze",
    "snapshot_save", "snapshot_load", "co2_set", "pumpA_fault",
]


def test_every_command_is_the_engines_to_answer():
    """No command is refused for who sent it: a simulator control and a plant command alike reach
    the engine, whose answer the console receives."""
    async def scenario():
        saw = []

        def handler(cmd, station):
            saw.append(cmd["type"])
            return True, ""

        server = StationServer(command_handler=handler)
        port = await server.start("127.0.0.1", 0)
        console = await Client.connect(port)
        await console.pump(2)
        kinds = SIMULATOR_COMMANDS + ["controller_set", "trip_reset", "assign"]
        for i, kind in enumerate(kinds, start=1):
            await console.send(protocol.command(i, {"type": kind}))
        await console.pump(2 + 2 * len(kinds))
        assert saw == kinds
        assert all(m["ok"] for m in console.of_kind(Kind.ACK))
        await console.close()
        await server.stop()
    run(scenario())


def test_engine_refusal_reaches_the_operator_with_its_reason():
    """A process interlock is the ENGINE's decision, and its reason must travel all the way
    back to the operator who tried."""
    async def scenario():
        def handler(cmd, station):
            return False, "start blocked by latched trip 21_2"

        server = StationServer(command_handler=handler)
        port = await server.start("127.0.0.1", 0)
        console = await Client.connect(port)
        await console.pump(2)
        await console.send(protocol.command(9, {"type": "pump_toggle", "id": "A"}))
        await console.pump(3)
        ack = console.of_kind(Kind.ACK)[0]
        assert ack["id"] == 9 and ack["ok"] is False
        assert ack["reason"] == "start blocked by latched trip 21_2"
        assert console.of_kind(Kind.EVENT) == [], "a refused command is not an audit event"
        await console.close()
        await server.stop()
    run(scenario())


def test_no_engine_attached_is_said_not_swallowed():
    async def scenario():
        server = StationServer()                  # no handler
        port = await server.start("127.0.0.1", 0)
        console = await Client.connect(port)
        await console.pump(2)
        await console.send(protocol.command(1, {"type": "pump_toggle", "id": "A"}))
        await console.pump(3)
        assert console.of_kind(Kind.ACK)[0]["reason"] == "no engine attached"
        await console.close()
        await server.stop()
    run(scenario())


def test_command_without_a_type_is_refused():
    async def scenario():
        server = StationServer(command_handler=lambda c, s: (True, ""))
        port = await server.start("127.0.0.1", 0)
        console = await Client.connect(port)
        await console.pump(2)
        await console.send(protocol.command(1, {"id": "A"}))
        await console.pump(3)
        assert "type" in console.of_kind(Kind.ACK)[0]["reason"]
        await console.close()
        await server.stop()
    run(scenario())


def test_a_raising_handler_does_not_take_the_server_down():
    """One bad command must not drop the console's link."""
    async def scenario():
        def handler(cmd, station):
            raise RuntimeError("solver diverged")

        server = StationServer(command_handler=handler)
        port = await server.start("127.0.0.1", 0)
        console = await Client.connect(port)
        await console.pump(2)
        await console.send(protocol.command(1, {"type": "pump_toggle", "id": "A"}))
        await console.pump(3)
        ack = console.of_kind(Kind.ACK)[0]
        assert ack["ok"] is False and "solver diverged" in ack["reason"]

        # Still serving: the next publish arrives.
        server.publish({"ok": 1})
        await console.pump(4)
        assert console.of_kind(Kind.SNAPSHOT)[-1]["state"] == {"ok": 1}
        await console.close()
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
        op = await Client.connect(port)
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


# --------------------------------------------------------------------------------------
# Bookkeeping, history and the exercise list
# --------------------------------------------------------------------------------------

def test_the_server_counts_its_connections():
    async def scenario():
        server = StationServer()
        port = await server.start("127.0.0.1", 0)
        assert server.station_count == 0
        console = await Client.connect(port)
        await console.pump(2)
        assert server.station_count == 1
        await console.close()
        await server.stop()
    run(scenario())


def test_ping_is_answered():
    async def scenario():
        server = StationServer()
        port = await server.start("127.0.0.1", 0)
        client = await Client.connect(port)
        await client.pump(2)
        await client.send(protocol.ping(42))
        await client.pump(3)
        assert client.of_kind(Kind.PONG)[0]["id"] == 42
        await client.close()
        await server.stop()
    run(scenario())


def test_history_is_answered_and_refused_without_an_engine():
    async def scenario():
        server = StationServer()
        port = await server.start("127.0.0.1", 0)
        console = await Client.connect(port)
        await console.pump(2)
        await console.send(protocol.history(1, ["a.b"], 60.0))
        await console.pump(3)
        assert console.of_kind(Kind.HISTORY_DATA)[0]["reason"] == "no engine attached"
        server.set_history_handler(lambda m: {"series": {"a.b": [1.0, float("nan")]}})
        await console.send(protocol.history(2, ["a.b"], 60.0))
        await console.pump(4)
        reply = console.of_kind(Kind.HISTORY_DATA)[1]
        assert reply["ok"] and reply["result"] == {"series": {"a.b": [1.0, None]}}
        await console.close()
        await server.stop()
    run(scenario())


def test_a_value_the_engine_could_not_compute_is_published_as_none():
    """A NaN in the plant state is not JSON: the snapshot goes out with None in its place,
    which a console shows as ``--``, instead of failing the publish."""
    async def scenario():
        server = StationServer()
        port = await server.start("127.0.0.1", 0)
        console = await Client.connect(port)
        await console.pump(2)
        server.publish({"A": {"pv": float("nan"), "sp": 1.0}}, 0.1)
        await console.pump(3)
        assert console.of_kind(Kind.SNAPSHOT)[-1]["state"] == {"A": {"pv": None, "sp": 1.0}}
        await console.close()
        await server.stop()
    run(scenario())


def test_the_exercises_are_listed_and_refused_without_an_engine():
    async def scenario():
        server = StationServer()
        port = await server.start("127.0.0.1", 0)
        console = await Client.connect(port)
        await console.pump(2)
        await console.send(protocol.exercise_list(1))
        await console.pump(3)
        assert console.of_kind(Kind.EXERCISES)[-1]["reason"] == "no engine attached"
        server.set_exercise_lister(lambda: ["shift-a", "trip-22-2"])
        await console.send(protocol.exercise_list(2))
        await console.pump(4)
        assert console.of_kind(Kind.EXERCISES)[-1] == {
            "t": "exercises", "id": 2, "ok": True, "reason": "", "names": ["shift-a", "trip-22-2"]}
        await console.close()
        await server.stop()
    run(scenario())
