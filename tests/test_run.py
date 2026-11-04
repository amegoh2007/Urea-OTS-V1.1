"""`run.py` — the single-console launch (decided 2026-10-22, `project.md` decision 149).

``python run.py`` starts the engine on the loopback interface and the console attached to it;
there is no server-only or station-only mode, and no role or token to give.

The start-up intro (session 84, decision 166) is the default: the engine is built held and the 100% LOAD
press releases it. Pinned, over a real socket and the real engine:

* ``python run.py`` plays the intro, ``--no-intro`` runs the plant from the start, as before;
* a plant built held publishes no packet and its clock does not move;
* the intro's start command releases it, the engine acks, and the plant publishes from its design seed;
* a plant built the other way runs from the start.
"""

from __future__ import annotations

import asyncio
import socket
import threading

import pytest

import run
from tests.net.test_server import Client
from ureasim.data.intro import START_COMMANDS, START_OPTION
from ureasim.net import protocol
from ureasim.net.protocol import Kind


def _launched(monkeypatch, argv):
    """The port the engine `run.main(argv)` would start serves, and the console it would open."""
    served, consoles = [], []

    def serve(port):
        served.append(port)

    def console(port, name):
        consoles.append((port, name))
        return 0
    monkeypatch.setattr(run, "_serve_in_background", serve)
    monkeypatch.setattr(run, "_run_console", console)
    assert run.main(argv) == 0
    return served, consoles


def test_the_engine_and_its_console_start_together_on_one_port(monkeypatch):
    served, consoles = _launched(monkeypatch, ["--no-intro", "--port", "8766", "--station", "desk"])
    assert served == [8766] and consoles == [(8766, "desk")]


@pytest.mark.parametrize("argv, fullscreen", [([], False), (["--fullscreen-intro"], True)])
def test_the_intro_is_the_default_start(monkeypatch, argv, fullscreen):
    """No ``--no-intro``: the intro path runs, the plain console path does not."""
    intro = []
    monkeypatch.setattr(run, "_run_with_intro", lambda port, name, full: intro.append((port, name, full)) or 0)
    monkeypatch.setattr(run, "_run_console", lambda *_: pytest.fail("the plain console started"))
    monkeypatch.setattr(run, "_serve_in_background", lambda *_: pytest.fail("the engine started running"))
    assert run.main(["--port", "8767", "--station", "desk", *argv]) == 0
    assert intro == [(8767, "desk", fullscreen)]


def test_the_engine_serves_the_loopback_interface_only():
    assert run.DEFAULT_HOST == "127.0.0.1"


@pytest.mark.parametrize("argv", [["server"], ["station"], ["--role", "instructor"],
                                  ["--token", "T"], ["--host", "0.0.0.0"]])
def test_the_multi_station_options_are_gone(argv):
    with pytest.raises(SystemExit):
        run._parse_args(argv)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def _engine(hold: bool):
    """The engine as run.py serves it, on a free port; returns (task, port)."""
    port = _free_port()
    ready = threading.Event()
    task = asyncio.create_task(run._serve(port, ready, hold))
    for _ in range(600):
        if ready.is_set():
            return task, port
        await asyncio.sleep(0.1)
    raise AssertionError("the engine did not come up in 60 s")


async def _snapshots(client: Client, seconds: float) -> list[dict]:
    """The non-empty packets that arrive in ``seconds``."""
    end = asyncio.get_running_loop().time() + seconds
    while (left := end - asyncio.get_running_loop().time()) > 0:
        try:
            await client.pump(len(client.inbox) + 1, timeout=left)
        except (AssertionError, TimeoutError):
            break
    return [m for m in client.of_kind(Kind.SNAPSHOT) if m["state"]]


def test_a_held_plant_publishes_nothing_until_the_start_key_releases_it() -> None:
    async def scenario():
        task, port = await _engine(hold=True)
        console = await Client.connect(port)
        assert await _snapshots(console, 1.0) == []
        statuses = [m["text"] for m in console.of_kind(Kind.STATUS)]
        assert statuses and statuses[-1].startswith("ENGINE FROZEN")

        await console.send(protocol.command(1, dict(START_COMMANDS[START_OPTION.key])))
        packets: list[dict] = []
        while not packets:
            await console.pump(len(console.inbox) + 1, timeout=30.0)
            packets = [m for m in console.of_kind(Kind.SNAPSHOT) if m["state"]]
        assert [a["ok"] for a in console.of_kind(Kind.ACK)] == [True]
        assert packets[0]["state"]["_health"]["ok"] is True
        while not console.of_kind(Kind.STATUS)[-1]["text"].startswith("ENGINE RUNNING"):
            await console.pump(len(console.inbox) + 1, timeout=10.0)

        await console.close()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    asyncio.run(scenario())


def test_a_plant_that_is_not_held_runs_from_the_start() -> None:
    async def scenario():
        task, port = await _engine(hold=False)
        console = await Client.connect(port)
        packets = []
        while not packets:
            await console.pump(len(console.inbox) + 1, timeout=30.0)
            packets = [m for m in console.of_kind(Kind.SNAPSHOT) if m["state"]]
        await console.close()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    asyncio.run(scenario())
