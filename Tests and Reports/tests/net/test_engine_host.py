"""The engine host — `ureasim.net.engine_host` — the plant served over a real socket.

Pinned:
* a pass paid in slices runs exactly the steps, and leaves exactly the plant, of one paid at once
  (the commands are drained between slices, so the slicing must be invisible to the physics);
* commands reach the plant between two ticks in arrival order, and each ack carries the plant's
  answer — accepted, or refused with the process reason;
* every command is the engine's to answer (decision 149): a simulator control and a faceplate in
  any section reach the plant, and a refusal is the plant's;
* the console packet is published on V1's paths with the engine's status, and a trend's backfill
  is answered over the protocol;
* a plant frozen and then reset or restored goes on publishing a packet every pass (handoff A-27), its
  clock where the reset or the exercise put it, and is not stepped.
"""

from __future__ import annotations

import asyncio

from ureasim.data.engine import MAX_PASS_NS
from ureasim.engine.session import EngineSession
from ureasim.net import protocol
from ureasim.net.engine_host import EngineHost
from ureasim.net.protocol import Kind
from ureasim.net.server import StationServer
from tests.net.test_server import Client


def test_a_pass_paid_in_slices_is_a_pass_paid_at_once(tmp_path):
    """0.5 s at x10 pacing — 50 steps — through the host's slices and through one call: the
    same steps, the same plant, to the bit."""
    sliced, whole = EngineSession(tmp_path), EngineSession(tmp_path)
    for s in (sliced, whole):
        s.handle({"type": "set_sim_mode", "mode": "x10"})
        s.handle({"type": "hic605_set", "op": 45.0})
    host = EngineHost(sliced, StationServer())
    assert host.pay(MAX_PASS_NS + 123_456_789) == whole.advance(MAX_PASS_NS) == 50
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
        op = await Client.connect(port)
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


def test_the_engine_answers_every_command_and_refuses_only_for_the_process(tmp_path):
    """The single console (decision 149): a simulator control and a faceplate in any section reach
    the plant; the only refusals are the plant's, with its reason."""
    async def scenario():
        server, port, host = await _serve(tmp_path)
        console = await Client.connect(port)
        for i, cmd in enumerate((
                {"type": "r323_ctrl_set", "id": "LIC_328505", "mode": "MAN", "op": 10.0},
                {"type": "r323_ctrl_set", "id": "LIC_323505", "mode": "MAN", "op": 40.0},
                {"type": "hic605_set", "op": 10.0},
                {"type": "freeze", "on": True}), start=1):
            await console.send(protocol.command(i, cmd))
            assert (await _ack(console, i))["ok"], cmd
        assert host.session.plant.operator["HIC-322605"] == 10.0 and host.session.frozen
        await console.send(protocol.command(5, {"type": "xv_toggle", "id": "322915"}))
        assert "XV-322915 has no operator open" in (await _ack(console, 5))["reason"]
        await console.close()
        host.stop()
        await server.stop()
    asyncio.run(scenario())


def test_the_packet_status_and_history_reach_the_console(tmp_path):
    async def scenario():
        server, port, host = await _serve(tmp_path)
        obs = await Client.connect(port)
        while not [m for m in obs.of_kind(Kind.SNAPSHOT) if m["state"]]:
            await obs.pump(len(obs.inbox) + 1, timeout=10.0)
        state = [m for m in obs.of_kind(Kind.SNAPSHOT) if m["state"]][-1]["state"]
        assert state["RECIRC_323"]["C003"]["TIC_323007"]["pv"] == 135.0
        assert state["_health"]["ok"] is True
        while not obs.of_kind(Kind.STATUS):
            await obs.pump(len(obs.inbox) + 1, timeout=10.0)
        assert obs.of_kind(Kind.STATUS)[-1]["text"] == "ENGINE RUNNING — x1"
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
        # The instructor's panel saves an exercise between two ticks; the list comes from the
        # session.
        teacher = await Client.connect(port)
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


def test_a_frozen_plant_goes_on_publishing_every_pass_after_a_reset_or_a_restore(tmp_path):
    """Ten packets a second while held, so a console's watchdog is fed; none from a stepping plant."""
    async def collect(console: Client, seconds: float) -> list[dict]:
        end = asyncio.get_running_loop().time() + seconds
        while (left := end - asyncio.get_running_loop().time()) > 0:
            try:
                await console.pump(len(console.inbox) + 1, timeout=left)
            except (AssertionError, TimeoutError):
                break
        return [m["state"] for m in console.of_kind(Kind.SNAPSHOT) if m["state"]]

    async def scenario():
        server, port, host = await _serve(tmp_path)
        console = await Client.connect(port)
        while not [m for m in console.of_kind(Kind.SNAPSHOT) if m["state"]]:
            await console.pump(len(console.inbox) + 1, timeout=60.0)
        for i, cmd in enumerate(({"type": "snapshot_save", "name": "start"}, {"type": "freeze", "on": True},
                                 {"type": "reset_sim"}), start=1):
            await console.send(protocol.command(i, cmd))
            assert (await _ack(console, i))["ok"], cmd
        console.inbox.clear()
        seed = await collect(console, 1.2)
        assert len(seed) >= 8 and {s["t_sim"] for s in seed} == {0.0} and host.session.plant.clock.tick == 0
        await console.send(protocol.command(4, {"type": "snapshot_load", "name": "start"}))
        assert (await _ack(console, 4))["ok"]
        console.inbox.clear()
        restored = await collect(console, 1.2)
        tick = host.session.plant.clock.tick
        assert len(restored) >= 8 and {s["t_sim"] for s in restored} == {tick * 0.1}
        await console.close()
        host.stop()
        await server.stop()
    asyncio.run(scenario())
