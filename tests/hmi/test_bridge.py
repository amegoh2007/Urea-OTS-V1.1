"""The console's bridge — `ureasim.hmi.bridge` — on the messages the instructor's panel needs.

Pinned without a socket: a roster and an exercise list from the server are re-emitted as signals,
an exercise list refused carries its reason, and a request on a link that is down is not sent; the
historian's answer to a trend likewise. On a real socket, against a station server on its own
thread: the station token (handoff A-2, closed 2026-10-16) admits the console as the role it asks
for, and a wrong one is refused with the server's reason and not retried.
"""

from __future__ import annotations

import asyncio
import threading
import time

import pytest
from PyQt6.QtTest import QTest

from ureasim.hmi.bridge import EngineBridge
from ureasim.net import protocol
from ureasim.net.protocol import Role
from ureasim.net.server import StationServer


def test_the_roster_and_the_exercises_are_re_emitted(qapp):
    bridge = EngineBridge("teacher")
    rosters, lists = [], []
    bridge.roster_changed.connect(rosters.append)
    bridge.exercises_received.connect(lambda names, reason: lists.append((names, reason)))
    bridge._dispatch(protocol.roster([{"station": "s1", "role": "operator", "sections": None}]))
    bridge._dispatch(protocol.exercises(1, True, "", ["shift-a"]))
    bridge._dispatch(protocol.exercises(2, False, "no engine attached"))
    assert rosters == [[{"station": "s1", "role": "operator", "sections": None}]]
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


@pytest.fixture()
def token_server():
    """A station server requiring a token, serving on its own thread's event loop."""
    loop = asyncio.new_event_loop()
    server = StationServer(token="class-7")
    port = loop.run_until_complete(server.start("127.0.0.1", 0))
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    yield port
    asyncio.run_coroutine_threadsafe(server.stop(), loop).result(5)
    loop.call_soon_threadsafe(loop.stop)
    thread.join(5)
    loop.close()


def _wait(condition, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "timed out"
        QTest.qWait(10)


@pytest.mark.parametrize("token, admitted", [("class-7", True), ("class-8", False), (None, False)])
def test_the_console_presents_its_token_and_a_refusal_is_not_retried(
        qapp, token_server, token, admitted):
    bridge = EngineBridge("teacher", Role.INSTRUCTOR, token=token)
    roles, statuses, lists = [], [], []
    bridge.role_changed.connect(roles.append)
    bridge.status.connect(lambda text, level: statuses.append((text, level)))
    bridge.exercises_received.connect(lambda names, reason: lists.append(reason))
    bridge.connect_to("127.0.0.1", token_server)
    _wait(lambda: roles or any(t.startswith("REFUSED") for t, _ in statuses))
    if admitted:
        assert roles == ["instructor"] and bridge.connected
        assert bridge.request_exercises()
        _wait(lambda: lists)
        assert lists == ["no engine attached"]       # the server answered the instructor
    else:
        QTest.qWait(1500)                             # past the first two retry delays
        reason = ("the station token is not this engine's" if token
                  else "this engine requires a station token, and the station presented none")
        assert roles == [] and not bridge.connected
        assert statuses[-1] == (f"REFUSED — {reason}", "fault")   # not overwritten
        assert sum(t.startswith("connecting") for t, _ in statuses) == 1   # never retried
        assert bridge.latest == {}
    bridge.close()
