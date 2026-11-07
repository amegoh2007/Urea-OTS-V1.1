"""The intro's LOAD button over a real loopback link: a scenario file restored, then the plant released.

Decision 171. The engine (`EngineSession`, `EngineHost`, `StationServer`) runs on its own thread and event
loop, built held as ``run.py`` builds it behind the intro: frozen, never reset or restored, so it publishes
nothing. The console is a real `EngineBridge` and `MainWindow`, and the `StartupController` drives the
hand-over with a chooser that answers by itself. Pinned:

* LOAD restores the chosen scenario and only then releases the plant: the engine's audit feed carries the
  restore before the release; the packet that ends the hand-over is the scenario's (its plant clock at the
  file's ``t_plant_s`` or later, where the design seed's is 0); the plant then steps on from the scenario's
  tick; the engine label reads RUNNING; and no DISCONNECTED was shown from the press on;
* a file the engine refuses reopens the chooser with the engine's reason, and the next choice reaches the
  running console from the scenario, the refused restore having installed nothing;
* Cancel takes the intro back to its buttons, nothing started, and 100% LOAD pressed then starts the design
  seed on the same console;
* with the bridge's first-packet watchdog cut to 1 s and the chooser left open for 2.5 s, the silent held
  link is dropped and reconnected while the operator decides, and the hand-over still reaches the running
  console from the scenario.

The engine is built as run.py builds it, a shipped folder beside the instructor's own; the scenario is copied
into a shipped folder of the test's own, since the repository's ``scenarios`` may be being written meanwhile.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import threading
import time
from collections.abc import Callable

import pytest
from PyQt6.QtCore import QTimer
from PyQt6.QtTest import QTest

import run
from tests.hmi.test_startup import FakeSplash
from ureasim.data.intro import LOAD_OPTION, START_OPTION, STARTUP
from ureasim.engine.session import EngineSession
from ureasim.hmi import bridge as bridge_module
from ureasim.hmi.bridge import EngineBridge
from ureasim.hmi.main_window import MainWindow
from ureasim.hmi.startup import StartupController
from ureasim.net.engine_host import EngineHost
from ureasim.net.server import StationServer


def _wait_for(condition: Callable[[], bool], seconds: float, what: str) -> None:
    end = time.monotonic() + seconds
    while not condition():
        if time.monotonic() > end:
            raise AssertionError(f"not within {seconds:g} s: {what}")
        QTest.qWait(20)


def _scenario(tmp_path) -> tuple[str, int, float]:
    """A saved steady state of the repository, copied into the test's shipped folder: its name, tick and time."""
    preferred = run.SCENARIO_DIR / "load100_steam.json"
    found = sorted(run.SCENARIO_DIR.glob("*.json")) if run.SCENARIO_DIR.is_dir() else []
    source = preferred if preferred.exists() else (found[0] if found else None)
    if source is None:
        pytest.skip(f"no saved exercise in {run.SCENARIO_DIR}")
    (tmp_path / "shipped").mkdir(exist_ok=True)
    shutil.copy(source, tmp_path / "shipped" / source.name)
    head = json.loads(source.read_text(encoding="utf-8"))
    return source.stem, int(head["tick"]), float(head["t_plant_s"])


class _Engine:
    """The engine as run.py serves it behind the intro: held, on its own thread and event loop."""

    def __init__(self, own_dir, shipped_dir) -> None:
        self.loop = asyncio.new_event_loop()
        self.server = StationServer()
        self.port = self.loop.run_until_complete(self.server.start("127.0.0.1", 0))
        self.session = EngineSession(own_dir, shipped_dir=shipped_dir)
        self.session.frozen = True
        self.host = EngineHost(self.session, self.server, "test-engine")
        self.host.start(self.loop)
        self._thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self._thread.start()

    def close(self) -> None:
        self.host.stop()
        asyncio.run_coroutine_threadsafe(self.server.stop(), self.loop).result(10)
        self.loop.call_soon_threadsafe(self.loop.stop)
        self._thread.join(10)
        self.loop.close()


class _Console:
    """The console the controller builds at the press, its status and audit lines recorded."""

    def __init__(self, engine: _Engine, choose) -> None:
        self.statuses: list[tuple[float, str]] = []
        self.audit: list[str] = []
        self.windows: list[MainWindow] = []
        self.bridge = EngineBridge("console")
        self.bridge.status.connect(lambda text, _level: self.statuses.append((time.monotonic(), text)))
        self.bridge.audit_event.connect(self.audit.append)
        self.splash = FakeSplash()
        served = threading.Event()
        served.set()
        self.controller = StartupController(
            splash=self.splash, bridge=self.bridge, make_window=self._make_window, engine_ready=served,
            engine_alive=lambda: True, host="127.0.0.1", port=engine.port, choose=choose)

    def _make_window(self) -> MainWindow:
        self.windows.append(MainWindow(self.bridge))
        return self.windows[-1]

    def disconnects(self, before: float = float("inf")) -> list[str]:
        return [text for t, text in self.statuses if text.startswith("DISCONNECTED") and t < before]

    def close(self) -> None:
        self.bridge.close()
        self.bridge._retry.stop()        # close() aborts the socket, whose `disconnected` schedules a retry
        for window in self.windows:
            window.close()


@pytest.fixture()
def rig(qapp, tmp_path):
    made: dict = {}

    def build(choose) -> tuple[_Engine, _Console]:
        made["engine"] = _Engine(tmp_path / "own", tmp_path / "shipped")
        made["console"] = _Console(made["engine"], choose)
        return made["engine"], made["console"]
    yield build
    if "console" in made:
        made["console"].close()
    if "engine" in made:
        made["engine"].close()


def _answers(name: str, after_ms: int, log: list[float], notes: list[str] | None = None, picks=None):
    """A chooser that is shown the engine's names and picks ``name`` ``after_ms`` later; ``picks``, when
    given, are taken one per showing instead, and each showing's note is kept in ``notes``."""
    queue = list(picks or [])

    def choose(names, done, note) -> None:
        pick = queue.pop(0) if queue else name
        assert pick in names, names
        if notes is not None:
            notes.append(note)

        def answer() -> None:
            log.append(time.monotonic())
            done(pick)
        QTimer.singleShot(after_ms, answer)
    return choose


def _running_from_the_scenario(engine: _Engine, console: _Console, tick: int, t_saved: float) -> None:
    """The hand-over ended on the scenario's plant, released after its restore, and the plant runs on."""
    assert console.splash.statuses[-1] == STARTUP.releasing, console.splash.statuses
    latest = console.bridge.latest
    assert latest and latest["t_sim"] >= t_saved - 1e-6, latest.get("t_sim")      # not the design seed's 0
    restores = [i for i, text in enumerate(console.audit) if "snapshot_load" in text]
    releases = [i for i, text in enumerate(console.audit) if "freeze" in text]
    assert restores and releases and max(restores) < releases[0], console.audit
    _wait_for(lambda: engine.session.plant.clock.tick > tick + 5, 30.0, "the plant stepping on")
    _wait_for(lambda: console.windows[0]._engine_label.text().startswith("ENGINE RUNNING"), 10.0,
              "the engine label RUNNING")
    assert not engine.session.frozen


def test_load_restores_a_scenario_then_releases_the_plant_to_a_running_console(rig, tmp_path) -> None:
    name, tick, t_saved = _scenario(tmp_path)
    chosen: list[float] = []
    engine, console = rig(_answers(name, 200, chosen))
    console.splash.start_requested.emit(LOAD_OPTION.key)
    _wait_for(lambda: console.splash.ready == 1, 90.0, "the hand-over")
    assert chosen and console.splash.statuses.count(STARTUP.choosing) == 1
    _running_from_the_scenario(engine, console, tick, t_saved)
    assert console.disconnects() == [], console.disconnects()


def test_a_refused_file_reopens_the_chooser_and_the_next_choice_reaches_a_running_console(rig, tmp_path) -> None:
    """Decided 2026-11-06: the engine refuses a file that is no exercise, the plant held and untouched."""
    name, tick, t_saved = _scenario(tmp_path)
    (tmp_path / "own").mkdir()
    (tmp_path / "own" / "broken.json").write_text("{}", encoding="utf-8")   # the instructor's own folder
    chosen: list[float] = []
    notes: list[str] = []
    engine, console = rig(_answers(name, 200, chosen, notes, picks=["broken", name]))
    console.splash.start_requested.emit(LOAD_OPTION.key)
    _wait_for(lambda: console.splash.ready == 1, 90.0, "the hand-over")
    assert notes[0] == "" and notes[1].startswith(STARTUP.refused.format(name="broken", reason=""))
    assert "not a ureasim exercise snapshot" in notes[1]
    _running_from_the_scenario(engine, console, tick, t_saved)
    assert sum("snapshot_load" in text for text in console.audit) == 1      # the refusal installed nothing
    assert console.disconnects() == [], console.disconnects()


def test_load_rides_out_the_bridges_watchdog_dropping_the_silent_link_while_the_chooser_is_open(
        rig, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(bridge_module, "FIRST_PACKET_STALE_MS", 1000)
    name, tick, t_saved = _scenario(tmp_path)
    chosen: list[float] = []
    engine, console = rig(_answers(name, 2500, chosen))
    console.splash.start_requested.emit(LOAD_OPTION.key)
    _wait_for(lambda: console.splash.ready == 1, 90.0, "the hand-over")
    assert console.disconnects(before=chosen[0]), "the held link was not dropped while the chooser was open"
    _running_from_the_scenario(engine, console, tick, t_saved)


def test_cancel_goes_back_to_the_buttons_and_100_percent_load_then_starts_the_design_seed(rig, tmp_path) -> None:
    """Decided 2026-11-06: no exercise chosen, nothing starts until the operator presses a button again."""
    _scenario(tmp_path)
    shown: list[list[str]] = []

    def choose(names, done, note) -> None:
        shown.append(list(names))
        QTimer.singleShot(200, lambda: done(None))
    engine, console = rig(choose)
    console.splash.start_requested.emit(LOAD_OPTION.key)
    _wait_for(lambda: console.splash.rearmed, 60.0, "the intro's buttons back")
    assert console.splash.rearmed == [STARTUP.no_choice] and console.splash.ready == 0
    QTest.qWait(500)
    assert engine.session.frozen and engine.session.plant.clock.tick == 0    # held: nothing started
    console.splash.start_requested.emit(START_OPTION.key)
    _wait_for(lambda: console.splash.ready == 1, 60.0, "the hand-over")
    assert len(console.windows) == 1 and len(shown) == 1
    assert console.bridge.latest["t_sim"] < 5.0                               # the design seed, released
    assert not any("snapshot_load" in text for text in console.audit)
    _wait_for(lambda: engine.session.plant.clock.tick > 5, 30.0, "the plant stepping")
    assert console.disconnects() == [], console.disconnects()
