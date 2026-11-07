"""`run.py` — the single-console launch (decided 2026-10-22, `project.md` decision 149).

``python run.py`` starts the engine on the loopback interface and the console attached to it;
there is no server-only or station-only mode, and no role or token to give.

The start-up intro (session 84, decision 166) is the default: the engine is built held and the 100% LOAD
press releases it. Pinned, over a real socket and the real engine:

* ``python run.py`` plays the intro, ``--no-intro`` runs the plant from the start, as before;
* a plant built held publishes no packet and its clock does not move;
* the intro's start command releases it, the engine acks, and the plant publishes from its design seed;
* a plant built the other way runs from the start;
* the repository's ``scenarios`` folder is shipped beside the instructor's folder (``UREASIM_EXERCISES`` or
  ``~/ureasim-exercises``): the intro's LOAD and the instructor's panel list both, SAVE writes only the
  instructor's and refuses a shipped name, and every scenario there loads on the present model (decision 171).
"""

from __future__ import annotations

import asyncio
import socket
import threading
from pathlib import Path

import pytest

import run
from tests.net.test_server import Client
from ureasim.data.intro import START_COMMANDS, START_OPTION
from ureasim.engine import snapshot
from ureasim.engine.plant import build_plant
from ureasim.engine.session import EXERCISE_DIR_ENV
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


# -- the exercise folders (decision 171) -----------------------------------------------------------------------


def test_the_repositorys_scenarios_folder_is_the_shipped_one() -> None:
    assert run.SCENARIO_DIR == Path(run.__file__).resolve().parent / "scenarios"


async def _ask(port: int, *messages: dict) -> list[dict]:
    """Send ``messages`` as a console would and collect one answer to each: an ack or the exercise list."""
    console = await Client.connect(port)
    for message in messages:
        await console.send(message)
    while len(console.of_kind(Kind.EXERCISES)) + len(console.of_kind(Kind.ACK)) < len(messages):
        await console.pump(len(console.inbox) + 1, timeout=10.0)
    await console.close()
    return console.of_kind(Kind.EXERCISES) + console.of_kind(Kind.ACK)


def _shipped() -> list[str]:
    return sorted(p.stem for p in run.SCENARIO_DIR.glob("*.json")) if run.SCENARIO_DIR.is_dir() else []


def test_the_engine_run_py_serves_lists_the_shipped_scenarios_beside_the_instructors_folder(monkeypatch, tmp_path):
    """The intro's LOAD and the instructor's panel see one list: the shipped files and the instructor's own."""
    monkeypatch.setenv(EXERCISE_DIR_ENV, str(tmp_path))
    (tmp_path / "drill_1.json").write_text("{}", encoding="utf-8")

    async def scenario():
        task, port = await _engine(hold=True)
        answers = await _ask(port, protocol.exercise_list(7))
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        return answers
    [answer] = asyncio.run(scenario())
    assert answer["ok"] is True and answer["names"] == sorted({*_shipped(), "drill_1"})


def test_save_writes_the_instructors_folder_and_never_the_repository(monkeypatch, tmp_path):
    """CLAUDE.md section 6 keeps training saves out of the tree; a shipped name is refused, not shadowed."""
    if not _shipped():
        pytest.skip(f"no saved exercise in {run.SCENARIO_DIR}")
    monkeypatch.setenv(EXERCISE_DIR_ENV, str(tmp_path))
    before = sorted(p.name for p in run.SCENARIO_DIR.iterdir())

    async def scenario():
        task, port = await _engine(hold=True)
        answers = await _ask(port, protocol.command(1, {"type": "snapshot_save", "name": "drill_2"}),
                             protocol.command(2, {"type": "snapshot_save", "name": _shipped()[0]}))
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        return answers
    acks = {a["id"]: a for a in asyncio.run(scenario())}
    assert acks[1]["ok"] is True and (tmp_path / "drill_2.json").is_file()
    assert acks[2]["ok"] is False and "shipped" in acks[2]["reason"]
    assert sorted(p.name for p in run.SCENARIO_DIR.iterdir()) == before


def test_every_saved_scenario_loads_on_the_present_model() -> None:
    """``snapshot.load`` checks a file against the plant the model builds today; a stale file is refused."""
    paths = sorted(run.SCENARIO_DIR.glob("*.json")) if run.SCENARIO_DIR.is_dir() else []
    if not paths:
        pytest.skip(f"no saved exercise in {run.SCENARIO_DIR}")
    for path in paths:
        plant = snapshot.load(str(path), build_plant()[1])
        assert plant.clock.tick > 0, path.name


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
