"""The console's bridge — `ureasim.hmi.bridge` — on the messages the console needs.

Pinned without a socket: an exercise list is re-emitted as a signal, one refused carries its
reason, and a request on a link that is down is not sent; the historian's answer to a trend
likewise. On a real socket, against a server on its own thread: the console is welcomed with no
role to ask for (decision 149) and its request answered, an engine that refuses its `hello`
is shown with the reason and not retried, and a bridge that is closed does not reconnect (handoff
A-30, decision 173).

The staleness watchdog (session 85, handoff A-25 point 2): the strict window blanks a console that gets
no packet, but an engine held at its design seed publishes nothing until released and its first tick is
cold, so a bridge that has never had a packet waits far longer; once one has arrived the strict window
applies again, for a reconnect too.
"""

from __future__ import annotations

import asyncio
import threading
import time

import pytest
from PyQt6.QtTest import QTest

from ureasim.hmi import bridge as bridge_module
from ureasim.hmi.bridge import FIRST_PACKET_STALE_MS, STALE_MS, EngineBridge
from ureasim.net import protocol
from ureasim.net.server import StationServer


def test_the_exercises_are_re_emitted(qapp):
    bridge = EngineBridge("console")
    lists = []
    bridge.exercises_received.connect(lambda names, reason: lists.append((names, reason)))
    bridge._dispatch(protocol.exercises(1, True, "", ["shift-a"]))
    bridge._dispatch(protocol.exercises(2, False, "no engine attached"))
    assert lists == [(["shift-a"], ""), ([], "no engine attached")]
    assert bridge.request_exercises() is False             # not connected: nothing sent
    bridge.close()


def test_a_history_answer_is_re_emitted_and_a_request_needs_the_link(qapp):
    """The historian's answer reaches the trend by its request id, a refusal with its reason; with
    the link down no request is sent."""
    bridge = EngineBridge("console")
    got = []
    bridge.history_received.connect(lambda *a: got.append(a))
    bridge._dispatch(protocol.history_data(7, True, "", {"t_sim": [1.0], "series": {}}))
    bridge._dispatch(protocol.history_data(8, False, "no engine attached"))
    assert got == [(7, True, "", {"t_sim": [1.0], "series": {}}),
                   (8, False, "no engine attached", None)]
    assert bridge.request_history(["X.p"], 60.0) == 0 and bridge.request_history_paths() == 0
    bridge.close()


def _on_a_thread(start):
    """Run the server ``start`` returns (``(stop, port)``) on its own thread's event loop."""
    loop = asyncio.new_event_loop()
    stop, port = loop.run_until_complete(start())
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()

    def close() -> None:
        asyncio.run_coroutine_threadsafe(stop(), loop).result(5)
        loop.call_soon_threadsafe(loop.stop)
        thread.join(5)
        loop.close()
    return port, close


@pytest.fixture()
def console_server():
    """The console server with no engine attached."""
    async def start():
        server = StationServer()
        return server.stop, await server.start("127.0.0.1", 0)
    port, close = _on_a_thread(start)
    yield port
    close()


@pytest.fixture()
def refusing_server():
    """An engine that refuses every console's `hello`, as one of another version does."""
    async def answer(reader, writer):
        await reader.read(65536)
        writer.write(protocol.encode(protocol.refused("protocol version 2 != 3")))
        await writer.drain()
        await reader.read(65536)                    # hold the link until the console drops it

    async def start():
        server = await asyncio.start_server(answer, "127.0.0.1", 0)

        async def stop():
            server.close()
            await server.wait_closed()
        return stop, server.sockets[0].getsockname()[1]
    port, close = _on_a_thread(start)
    yield port
    close()


def _wait(condition, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "timed out"
        QTest.qWait(10)


def test_the_console_is_welcomed_and_its_request_answered(qapp, console_server):
    bridge = EngineBridge("console")
    statuses, lists = [], []
    bridge.status.connect(lambda text, level: statuses.append((text, level)))
    bridge.exercises_received.connect(lambda names, reason: lists.append(reason))
    bridge.connect_to("127.0.0.1", console_server)
    _wait(lambda: bridge.connected)
    assert statuses[-1] == ("connected — engine: unattached", "warn")
    assert bridge.request_exercises()
    _wait(lambda: lists)
    assert lists == ["no engine attached"]
    bridge.close()


def test_a_refusal_is_shown_and_not_retried(qapp, refusing_server):
    bridge = EngineBridge("console")
    statuses = []
    bridge.status.connect(lambda text, level: statuses.append((text, level)))
    bridge.connect_to("127.0.0.1", refusing_server)
    _wait(lambda: any(t.startswith("REFUSED") for t, _ in statuses))
    QTest.qWait(1500)                                 # past the first two retry delays
    assert not bridge.connected and bridge.latest == {}
    assert statuses[-1] == ("REFUSED — protocol version 2 != 3", "fault")   # not overwritten
    assert sum(t.startswith("connecting") for t, _ in statuses) == 1        # never retried
    bridge.close()


def test_a_closed_bridge_does_not_reconnect(qapp, console_server):
    """Handoff A-30 (decision 173): `close` aborts the socket, whose `disconnected` arrives at once, and the
    bridge schedules no retry for it; it stays closed past the retry delays, and `connect_to` opens it again."""
    bridge = EngineBridge("console")
    statuses = []
    bridge.status.connect(lambda text, level: statuses.append((text, level)))
    bridge.connect_to("127.0.0.1", console_server)
    _wait(lambda: bridge.connected)
    closed_at = len(statuses)
    bridge.close()
    assert not bridge._retry.isActive()
    QTest.qWait(2500)                                 # past the 0.5 s and 1 s retry delays: 1.5 s
    assert not bridge.connected and not bridge._retry.isActive()
    assert not any(t.startswith("connect") for t, _ in statuses[closed_at:]), statuses[closed_at:]
    bridge.connect_to("127.0.0.1", console_server)
    _wait(lambda: bridge.connected)
    bridge.close()


PACKET =protocol.snapshot(1, 0.1, {"_health": {"ok": True}})


def _watched(monkeypatch, strict_ms: int, first_ms: int):
    """A bridge on short watchdog windows, its blanks and snapshots recorded. The constants are read when
    the watchdog is armed, so patching the module is enough."""
    monkeypatch.setattr(bridge_module, "STALE_MS", strict_ms)
    monkeypatch.setattr(bridge_module, "FIRST_PACKET_STALE_MS", first_ms)
    bridge = EngineBridge("console")
    statuses, snapshots = [], []
    bridge.status.connect(lambda text, level: statuses.append(text))
    bridge.snapshot.connect(snapshots.append)
    return bridge, statuses, snapshots


def test_the_first_packet_may_come_after_the_strict_window_without_a_false_disconnect(qapp, monkeypatch):
    """A first tick later than the strict window after the connect: the console is not blanked, and the
    packet, when it comes, is delivered; then the strict window is the one that applies."""
    bridge, statuses, snapshots = _watched(monkeypatch, strict_ms=60, first_ms=600)
    bridge._on_connected()
    assert bridge._stale.interval() == 600
    QTest.qWait(200)                                   # over three strict windows with no packet
    assert not any(t.startswith("DISCONNECTED") for t in statuses) and snapshots == []
    bridge._dispatch(PACKET)
    assert snapshots == [PACKET["state"]] and bridge._stale.interval() == 60
    bridge.close()


def test_five_seconds_of_silence_after_the_first_packet_still_blanks_the_console(qapp, monkeypatch):
    bridge, statuses, snapshots = _watched(monkeypatch, strict_ms=60, first_ms=600)
    bridge._on_connected()
    bridge._dispatch(PACKET)
    snapshots.clear()
    _wait(lambda: any(t.startswith("DISCONNECTED") for t in statuses), timeout=2.0)
    assert snapshots == [{}] and statuses[-1] == "DISCONNECTED — no data from the engine"
    bridge.close()


def test_a_reconnect_after_a_packet_gets_the_strict_window(qapp, monkeypatch):
    bridge, _, _ = _watched(monkeypatch, strict_ms=60, first_ms=600)
    bridge._on_connected()
    bridge._dispatch(PACKET)
    bridge._on_connected()                             # the link came back
    assert bridge._stale.interval() == 60
    bridge.close()


def test_a_blank_snapshot_does_not_end_the_startup_allowance(qapp, monkeypatch):
    bridge, _, _ = _watched(monkeypatch, strict_ms=60, first_ms=600)
    bridge._on_connected()
    bridge._dispatch(protocol.snapshot(2, 0.0, {}))
    assert bridge._stale.interval() == 600
    bridge.close()


def test_the_shipped_windows_are_the_ones_the_start_up_relies_on(qapp):
    """The first packet is allowed ten times a cold first tick (2.3 s), and the strict window stays 5 s."""
    assert STALE_MS == 5000 and FIRST_PACKET_STALE_MS == 30_000
