"""The station server's login — `ureasim.net.server`, the station token.

Decided 2026-10-16 (handoffs A-2 and A-8 closed): an engine started with a station token admits only
the stations whose ``hello`` presents it, refuses the others with the reason before it reads the role
they ask for, and disconnects them; an engine started with none admits every station, as the rest of
`tests/net` pins. Run on a real socket, because what matters — the refusal reaching the station and
the connection closing — is what an in-process fake would not exercise. The admitted instructor is
the classroom deployment's: its roster and its exercise list arrive as they do for the superuser.
"""

from __future__ import annotations

import asyncio

import pytest

from ureasim.net import protocol
from ureasim.net.protocol import FrameReader, Kind, Role
from ureasim.net.server import StationServer
from tests.net.test_server import Client, run

TOKEN = "class-7 été"          # a non-ASCII token compares as its UTF-8 bytes


async def _login(port: int, role: Role, name: str, token: str | None) -> Client:
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    client = Client(reader, writer)
    await client.send(protocol.hello(role, name, token))
    return client


async def _closed_by_server(client: Client, timeout: float = 2.0) -> bool:
    """True when the server has closed the connection: every further read is end of stream."""
    while True:
        chunk = await asyncio.wait_for(client.reader.read(65536), timeout)
        if not chunk:
            return True
        for m in client.frames.feed(chunk):
            client.inbox.append(m)


def test_a_station_presenting_the_token_is_admitted_as_the_role_it_asks_for():
    """The classroom: an instructor and an operator with the token, the instructor sent the roster
    and its exercise list, the operator a plant command and refused a simulator control."""
    async def scenario():
        saw = []

        def handler(cmd, station):
            saw.append((cmd["type"], station))
            return True, ""

        server = StationServer(command_handler=handler, token=TOKEN)
        server.set_exercise_lister(lambda: ["shift-a"])
        port = await server.start("127.0.0.1", 0)
        teacher = await _login(port, Role.INSTRUCTOR, "teacher", TOKEN)
        await teacher.pump(2)
        trainee = await _login(port, Role.OPERATOR, "trainee-a", TOKEN)
        await trainee.pump(2)
        assert teacher.of_kind(Kind.WELCOME)[0]["role"] == "instructor"
        assert trainee.of_kind(Kind.WELCOME)[0]["role"] == "operator"
        await teacher.send(protocol.exercise_list(1))
        await teacher.pump(3)
        assert teacher.of_kind(Kind.EXERCISES)[-1]["names"] == ["shift-a"]
        await trainee.send(protocol.command(1, {"type": "controller_set", "tag": "LIC-322501"}))
        await trainee.send(protocol.command(2, {"type": "reset_sim"}))
        await trainee.pump(5)
        acks = {m["id"]: m for m in trainee.of_kind(Kind.ACK)}
        assert acks[1]["ok"] and not acks[2]["ok"]
        assert saw == [("controller_set", "trainee-a")]
        await teacher.settle()
        assert {s["station"] for s in teacher.rosters[-1]["stations"]} == {"teacher", "trainee-a"}
        assert server.station_count == 2
        await teacher.close()
        await trainee.close()
        await server.stop()
    run(scenario())


@pytest.mark.parametrize("presented, reason", [
    (None, "this engine requires a station token, and the station presented none"),
    ("", "this engine requires a station token, and the station presented none"),
    ("class-8", "the station token is not this engine's"),
    (TOKEN + " ", "the station token is not this engine's"),
])
def test_a_station_without_the_token_is_refused_with_the_reason_and_disconnected(
        presented, reason):
    """Refused before its role is read — even the superuser on the engine's own machine — never
    made ready, never sent a snapshot, and disconnected; the reason never echoes a token."""
    async def scenario():
        server = StationServer(token=TOKEN)
        port = await server.start("127.0.0.1", 0)
        for role in (Role.OPERATOR, Role.SUPERUSER):
            client = await _login(port, role, "intruder", presented)
            assert await _closed_by_server(client)
            assert [m["t"] for m in client.inbox] == ["refused"]
            assert client.inbox[0]["reason"] == reason
            assert TOKEN not in client.inbox[0]["reason"]
            await client.close()
        assert server.station_count == 0
        await server.stop()
    run(scenario())


def test_the_superuser_still_needs_its_own_machine_with_the_token():
    """The token admits; the loopback rule still grants the superuser. A remote superuser with the
    right token is refused for its address, as without one."""
    class _Writer:
        def __init__(self):
            self.sent = bytearray()

        def write(self, data: bytes) -> None:
            self.sent += data

    from ureasim.net import server as server_module
    for host, granted in (("127.0.0.1", True), ("10.0.0.5", False)):
        server = StationServer(token=TOKEN)
        writer = _Writer()
        station = server_module._Station(writer, f"{host}:50000", host)
        server._stations.add(station)
        server._handle(station, protocol.hello(Role.SUPERUSER, "console", TOKEN))
        sent = list(FrameReader().feed(bytes(writer.sent)))
        assert station.ready is granted
        assert sent[0]["t"] == ("welcome" if granted else "refused")


def test_an_engine_with_no_token_admits_a_station_that_presents_one():
    """No token, no check: a console started with a token still joins a token-less engine."""
    async def scenario():
        server = StationServer()
        port = await server.start("127.0.0.1", 0)
        client = await _login(port, Role.OPERATOR, "s1", "class-7")
        await client.pump(2)
        assert client.of_kind(Kind.WELCOME)[0]["role"] == "operator"
        await client.close()
        await server.stop()
    run(scenario())


def test_an_empty_token_is_not_a_login():
    """An empty token would read as a login and admit every station: refused at construction."""
    with pytest.raises(ValueError, match="empty station token"):
        StationServer(token="")
