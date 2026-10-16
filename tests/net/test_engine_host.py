"""The engine host — `ureasim.net.engine_host` — the plant served over a real socket.

Pinned:
* a pass paid in slices runs exactly the steps, and leaves exactly the plant, of one paid at once
  (the commands are drained between slices, so the slicing must be invisible to the physics);
* commands reach the plant between two ticks in arrival order, and each ack carries the plant's
  answer — accepted, or refused with the process reason;
* the role and the assignment are the server's, enforced before the engine sees a command: an
  observer commands nothing, a trainee assigned unit 323 is refused a unit-328 faceplate and the
  synthesis loop's hand valve, and the instructor's simulator controls stay the instructor's;
* the console packet is published on V1's paths with the engine's status, and a trend's backfill
  is answered over the protocol.
"""

from __future__ import annotations

import asyncio

from ureasim.data.engine import MAX_PASS_NS
from ureasim.engine.session import EngineSession
from ureasim.net import protocol
from ureasim.net.engine_host import EngineHost
from ureasim.net.protocol import Kind, Role
from ureasim.net.server import StationServer
from tests.net.test_server import Client


def test_a_pass_paid_in_slices_is_a_pass_paid_at_once(tmp_path):
    """0.5 s at FAST pacing — 300 steps — through the host's slices and through one call: the
    same steps, the same plant, to the bit."""
    sliced, whole = EngineSession(tmp_path), EngineSession(tmp_path)
    for s in (sliced, whole):
        s.handle({"type": "set_sim_mode", "mode": "FAST"})
        s.handle({"type": "hic605_set", "op": 45.0})
    host = EngineHost(sliced, StationServer())
    assert host.pay(MAX_PASS_NS + 123_456_789) == whole.advance(MAX_PASS_NS) == 300
    assert sliced.packet(0.0, health=False) == whole.packet(0.0, health=False)


async def _serve(tmp_path):
    server = StationServer()
    port = await server.start("127.0.0.1", 0)
    host = EngineHost(EngineSession(tmp_path), server, "test-engine")
    host.start()
    return server, port, host


async def _ack(client: Client, cmd_id: int) -> dict:
    while True:
        acks = [m for m in client.of_kind(Kind.ACK) if m["id"] == cmd_id]
        if acks:
            return acks[0]
        await client.pump(len(client.inbox) + 1, timeout=10.0)


def test_commands_reach_the_plant_between_ticks_with_the_plants_answer(tmp_path):
    async def scenario():
        server, port, host = await _serve(tmp_path)
        op = await Client.connect(port, Role.OPERATOR, "trainee-1")
        await op.send(protocol.command(1, {"type": "hic605_set", "op": 45.0}))
        await op.send(protocol.command(2, {"type": "xv_toggle", "id": "322915"}))
        await op.send(protocol.command(3, {"type": "hic605_set", "op": 55.0}))
        a1, a2, a3 = [await _ack(op, i) for i in (1, 2, 3)]
        assert a1["ok"] and a3["ok"] and host.session.plant.operator["HIC-322605"] == 55.0
        assert not a2["ok"] and "XV-322915 has no operator open" in a2["reason"]
        acks = [m["id"] for m in op.of_kind(Kind.ACK)]
        assert acks == [1, 2, 3]
        assert [e["cmd"]["op"] for e in op.of_kind(Kind.EVENT)] == [45.0, 55.0]
        await op.close()
        host.stop()
        await server.stop()
    asyncio.run(scenario())


def test_the_server_arbitrates_roles_and_assignments_before_the_engine(tmp_path):
    async def scenario():
        server, port, host = await _serve(tmp_path)
        obs = await Client.connect(port, Role.OBSERVER, "visitor")
        trainee = await Client.connect(port, Role.OPERATOR, "trainee-323")
        inst = await Client.connect(port, Role.INSTRUCTOR, "instructor")
        await inst.send(protocol.command(1, {"type": "assign", "station": "trainee-323",
                                             "sections": ["323"]}))
        assert (await _ack(inst, 1))["ok"]
        await obs.send(protocol.command(1, {"type": "hic605_set", "op": 10.0}))
        assert "role 'observer' may not issue" in (await _ack(obs, 1))["reason"]
        for i, cmd in enumerate((
                {"type": "r323_ctrl_set", "id": "LIC_328505", "mode": "MAN", "op": 10.0},
                {"type": "r323_ctrl_set", "id": "FIC_329402", "mode": "MAN", "op": 10.0},
                {"type": "hic605_set", "op": 10.0},
                {"type": "freeze", "on": True}), start=1):
            await trainee.send(protocol.command(i, cmd))
            assert not (await _ack(trainee, i))["ok"], cmd
        await trainee.send(protocol.command(9, {"type": "r323_ctrl_set", "id": "LIC_323505",
                                                "mode": "MAN", "op": 40.0}))
        assert (await _ack(trainee, 9))["ok"]
        reasons = {m["id"]: m["reason"] for m in trainee.of_kind(Kind.ACK)}
        assert "section 328" in reasons[1] and "section 329" in reasons[2]
        assert "section 322" in reasons[3] and "may not issue 'freeze'" in reasons[4]
        plant = host.session.plant
        assert plant.operator["HIC-322605"] == 60.0 and not host.session.frozen
        await inst.send(protocol.command(2, {"type": "freeze", "on": True}))
        assert (await _ack(inst, 2))["ok"] and host.session.frozen
        for c in (obs, trainee, inst):
            await c.close()
        host.stop()
        await server.stop()
    asyncio.run(scenario())


def test_the_packet_status_and_history_reach_the_stations(tmp_path):
    async def scenario():
        server, port, host = await _serve(tmp_path)
        obs = await Client.connect(port, Role.OBSERVER, "visitor")
        while not [m for m in obs.of_kind(Kind.SNAPSHOT) if m["state"]]:
            await obs.pump(len(obs.inbox) + 1, timeout=10.0)
        state = [m for m in obs.of_kind(Kind.SNAPSHOT) if m["state"]][-1]["state"]
        assert state["RECIRC_323"]["C003"]["TIC_323007"]["pv"] == 135.0
        assert state["_health"]["ok"] is True
        while not obs.of_kind(Kind.STATUS):
            await obs.pump(len(obs.inbox) + 1, timeout=10.0)
        assert obs.of_kind(Kind.STATUS)[-1]["text"] == "ENGINE RUNNING — SLOW"
        await asyncio.sleep(1.2)
        await obs.send(protocol.history(7, ["RECIRC_323.C003.TIC_323007.pv"], 60.0))
        await obs.send(protocol.history_paths(8))
        await obs.send({"t": "history", "id": 9, "paths": []})
        replies = {}
        while len(replies) < 3:
            await obs.pump(len(obs.inbox) + 1, timeout=10.0)
            replies = {m["id"]: m for m in obs.of_kind(Kind.HISTORY_DATA)}
        assert replies[7]["ok"] and replies[7]["result"]["series"][
            "RECIRC_323.C003.TIC_323007.pv"][-1] == 135.0
        assert "STRIP_322E001.LIC_322501.pv" in replies[8]["result"]["paths"]
        assert not replies[9]["ok"] and "names its paths" in replies[9]["reason"]
        # The instructor saves an exercise between two ticks; the list comes from the session.
        teacher = await Client.connect(port, Role.INSTRUCTOR, "teacher")
        await teacher.send(protocol.command(11, {"type": "snapshot_save",
                                                 "name": "start-of-shift"}))
        assert (await _ack(teacher, 11))["ok"]
        await teacher.send(protocol.exercise_list(10))
        while not teacher.of_kind(Kind.EXERCISES):
            await teacher.pump(len(teacher.inbox) + 1, timeout=10.0)
        assert teacher.of_kind(Kind.EXERCISES)[-1]["names"] == ["start-of-shift"]
        await teacher.close()
        await obs.close()
        host.stop()
        await server.stop()
    asyncio.run(scenario())
