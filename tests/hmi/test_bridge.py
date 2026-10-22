"""The console's bridge — `ureasim.hmi.bridge` — on the messages the console needs.

Pinned without a socket: an exercise list is re-emitted as a signal, one refused carries its
reason, and a request on a link that is down is not sent; the historian's answer to a trend
likewise. On a real socket, against a server on its own thread: the console is welcomed with no
role to ask for (decision 149) and its request answered, and an engine that refuses its `hello`
is shown with the reason and not retried.
"""

from __future__ import annotations

import asyncio
import threading
import time

import pytest
from PyQt6.QtTest import QTest

from ureasim.hmi.bridge import EngineBridge
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
