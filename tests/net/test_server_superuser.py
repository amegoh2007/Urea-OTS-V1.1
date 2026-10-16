"""The station server's single-machine superuser — `ureasim.net.server`.

Decided 2026-10-07: the default deployment is one machine, its one console the superuser — every
command, never assigned — and the server grants the role only to a console on its own machine (kept
when A-2 and A-8 closed, 2026-10-16; the station token is `test_server_login.py`'s).
"""

from __future__ import annotations

import pytest

from ureasim.net import protocol
from ureasim.net import server as server_module
from ureasim.net.protocol import FrameReader, Kind, Role
from ureasim.net.server import StationServer
from tests.net.test_server import Client, run


def test_the_superuser_on_this_machine_is_refused_nothing_and_never_assigned():
    """The local console as ``run.py`` starts it: the role granted, a simulator control and a
    plant command both passed to the engine, an assignment that does not bind it, the roster
    and the exercises sent to it."""
    async def scenario():
        saw = []

        def handler(cmd, station):
            saw.append(cmd["type"])
            return True, ""

        server = StationServer(command_handler=handler)
        server.set_exercise_lister(lambda: ["shift-a"])
        port = await server.start("127.0.0.1", 0)
        su = await Client.connect(port, Role.SUPERUSER, "console")
        await su.pump(2)
        assert su.of_kind(Kind.WELCOME)[0]["role"] == "superuser"
        await su.send(protocol.command(
            1, {"type": "assign", "station": "console", "sections": ["323"]}))
        await su.send(protocol.command(2, {"type": "trigger_fault", "id": "pumpA"}))
        await su.send(protocol.command(3, {"type": "controller_set", "tag": "LIC-322501"}))
        await su.send(protocol.exercise_list(4))
        # welcome, snapshot; assign ack, assignment, event; two acks, two events; exercises.
        await su.pump(10)
        acks = {m["id"]: m for m in su.of_kind(Kind.ACK)}
        assert all(acks[i]["ok"] for i in (1, 2, 3))
        assert saw == ["trigger_fault", "controller_set"]
        assert su.of_kind(Kind.EXERCISES)[-1]["names"] == ["shift-a"]
        assert su.rosters
        await su.close()
        await server.stop()
    run(scenario())


class _Writer:
    """A connection's writer that keeps what the server sends."""

    def __init__(self):
        self.sent = bytearray()

    def write(self, data: bytes) -> None:
        self.sent += data


@pytest.mark.parametrize("host, granted", [
    ("127.0.0.1", True), ("127.5.0.9", True), ("::1", True), ("::ffff:127.0.0.1", True),
    ("10.0.0.5", False), ("192.168.1.20", False), ("fe80::1%eth0", False), ("", False),
])
def test_the_superuser_is_granted_only_to_a_console_on_the_engines_machine(host, granted):
    server = StationServer()
    writer = _Writer()
    station = server_module._Station(writer, f"{host}:50000", host)
    server._stations.add(station)
    server._handle(station, protocol.hello(Role.SUPERUSER, "console"))
    sent = list(FrameReader().feed(bytes(writer.sent)))
    assert station.ready is granted
    if granted:
        assert sent[0]["t"] == "welcome" and sent[0]["role"] == "superuser"
    else:
        assert [m["t"] for m in sent] == ["refused"]
        assert "engine's own machine" in sent[0]["reason"]
