"""The console beside a frozen engine — handoff A-27 — over a real loopback link, at the real constants.

The engine (`EngineSession`, `EngineHost`, `StationServer`) runs on its own thread and event loop; the
console is a real `EngineBridge` and `MainWindow` connected to it over TCP. The bridge's staleness
watchdog is 5 s (`STALE_MS`) and blanks a console that gets no packet, which is right for a dead link
and wrong for a live engine that is held. Pinned here:

* a plant reset, or an exercise restored, while frozen puts a packet on the console at once and keeps
  the console live for longer than the watchdog (six seconds, 10 packets a second, no DISCONNECTED, the
  engine label still FROZEN, the readouts not blank), the plant's clock where the reset or the exercise
  put it, and the plant not stepped;
* the watchdog still does its work: an engine that goes silent with the link up blanks the console about
  5 s later and keeps it blank through the reconnects that follow (handoff A-28, decision 172), and a link
  that closes blanks it at once.

The bridge's watchdog must already be in its strict state before any wait here counts, so the engine is
started running, not held: a console that has never had a packet is on the 30 s first-packet allowance and
would pass these waits for the wrong reason.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Callable

import pytest
from PyQt6.QtTest import QTest

from ureasim.hmi.bridge import STALE_MS, EngineBridge
from ureasim.hmi.main_window import MainWindow
from ureasim.hmi.state_access import NO_DATA
from ureasim.engine.session import EngineSession
from ureasim.net.engine_host import EngineHost
from ureasim.net.server import StationServer

#: Longer than the watchdog, so a console that was going to blank has done so.
PAST_THE_WATCHDOG_S = STALE_MS / 1000.0 + 1.0


class _Rig:
    """An engine on its own thread, and a console attached to it over loopback."""

    def __init__(self, exercise_dir) -> None:
        self.loop = asyncio.new_event_loop()
        self.server = StationServer()
        self.port = self.loop.run_until_complete(self.server.start("127.0.0.1", 0))
        self.session = EngineSession(exercise_dir)
        self.host = EngineHost(self.session, self.server, "test-engine")
        self.host.start(self.loop)
        self._thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self._thread.start()
        self._server_up = True

        self.statuses: list[tuple[float, str]] = []
        self.snapshots: list[tuple[float, dict]] = []
        self.results: dict[int, tuple[bool, str]] = {}
        self.bridge = EngineBridge("console")
        self.bridge.status.connect(lambda text, level: self.statuses.append((time.monotonic(), text)))
        self.bridge.snapshot.connect(lambda state: self.snapshots.append((time.monotonic(), state)))
        self.bridge.command_result.connect(lambda i, ok, reason: self.results.__setitem__(i, (ok, reason)))
        self.window = MainWindow(self.bridge)
        self.bridge.connect_to("127.0.0.1", self.port)

    # -- waiting ------------------------------------------------------------------------------

    def wait_for(self, condition: Callable[[], bool], seconds: float, what: str) -> None:
        end = time.monotonic() + seconds
        while not condition():
            if time.monotonic() > end:
                raise AssertionError(f"not within {seconds:g} s: {what}")
            QTest.qWait(20)

    def sit(self, seconds: float) -> None:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            QTest.qWait(20)

    # -- what the console has -----------------------------------------------------------------

    def command(self, cmd: dict) -> None:
        """Send ``cmd`` and wait for the engine's answer; it must be an acceptance."""
        cmd_id = self.bridge.send_command(cmd)
        assert cmd_id, f"not sent: {cmd}"
        self.wait_for(lambda: cmd_id in self.results, 10.0, f"an answer to {cmd}")
        assert self.results[cmd_id] == (True, ""), (cmd, self.results[cmd_id])

    @property
    def t_sim(self) -> float | None:
        return self.bridge.latest.get("t_sim") if self.bridge.latest else None

    def engine_label(self) -> str:
        return self.window._engine_label.text()

    def readouts(self) -> list[str]:
        """What the bound indicators of the screen on show read (``--`` where they have no data)."""
        screen = self.window._stack.currentWidget()
        return [w._text_value for w in screen.stage.overlays if getattr(w, "_bound", False)]

    def disconnects(self, since: float) -> list[tuple[float, str]]:
        return [(t, text) for t, text in self.statuses if t >= since and text.startswith("DISCONNECTED")]

    # -- stopping -----------------------------------------------------------------------------

    def stop_server(self) -> None:
        if self._server_up:
            asyncio.run_coroutine_threadsafe(self.server.stop(), self.loop).result(10)
            self._server_up = False

    def close(self) -> None:
        self.bridge.close()
        self.window.close()
        self.host.stop()
        self.stop_server()
        self.loop.call_soon_threadsafe(self.loop.stop)
        self._thread.join(10)
        self.loop.close()


@pytest.fixture()
def rig(qapp, tmp_path):
    r = _Rig(tmp_path)
    r.wait_for(lambda: r.t_sim is not None, 90.0, "the first live packet")       # the first tick is cold
    yield r
    r.close()


def _frozen_and_live(r: _Rig, since: float, t_sim: float, tick: int) -> None:
    """The console after a long wait on a held engine: live, not blank, the clock where it was put."""
    first = len([1 for t, _ in r.snapshots if t >= since])
    r.sit(PAST_THE_WATCHDOG_S)
    assert r.disconnects(since) == [], r.disconnects(since)
    assert r.bridge.connected and r.t_sim == t_sim
    assert len([1 for t, _ in r.snapshots if t >= since]) - first >= 30        # 10 packets a second
    assert r.engine_label().startswith("ENGINE FROZEN"), r.engine_label()
    assert any(text != NO_DATA for text in r.readouts()), r.readouts()
    assert r.session.plant.clock.tick == tick                                  # held: not one step taken


def test_a_reset_and_a_restored_exercise_keep_a_frozen_console_live_past_the_watchdog(rig):
    assert STALE_MS == 5000 and rig.bridge._stale.interval() == STALE_MS      # the strict window is in force
    assert any(text != NO_DATA for text in rig.readouts())

    # An exercise saved at a known plant time: freeze, save, run on, freeze again.
    rig.command({"type": "freeze", "on": True})
    saved_tick = rig.session.plant.clock.tick
    saved_t = saved_tick * 0.1
    assert saved_tick > 0
    rig.command({"type": "snapshot_save", "name": "mark"})
    rig.command({"type": "freeze", "on": False})
    rig.wait_for(lambda: (rig.t_sim or 0.0) >= saved_t + 0.5, 30.0, "the plant running on")
    rig.command({"type": "freeze", "on": True})
    assert rig.session.plant.clock.tick > saved_tick

    # Reset while frozen: the seed is on the console at once, and stays for longer than the watchdog.
    since = time.monotonic()
    rig.command({"type": "reset_sim"})
    rig.wait_for(lambda: rig.t_sim == 0.0, 2.0, "the reset plant's packet")
    _frozen_and_live(rig, since, 0.0, 0)

    # An exercise restored while frozen: the exercise's own time is on the console, likewise held.
    since = time.monotonic()
    rig.command({"type": "snapshot_load", "name": "mark"})
    rig.wait_for(lambda: rig.t_sim == pytest.approx(saved_t), 2.0, "the restored exercise's packet")
    _frozen_and_live(rig, since, rig.t_sim, saved_tick)

    # Released, the plant steps on from where it was put.
    rig.command({"type": "freeze", "on": False})
    rig.wait_for(lambda: (rig.t_sim or 0.0) > saved_t, 10.0, "the released plant stepping")
    assert rig.engine_label().startswith("ENGINE RUNNING")


def test_the_watchdog_still_blanks_a_console_whose_engine_goes_silent(rig):
    """The link up and nothing arriving is the case the watchdog is for: the engine's thread stopped.

    After the first blank the bridge reconnects, and the server does not replay the dead engine's last packet
    (handoff A-28, decision 172): across two more reconnect cycles the console stays blank, and each
    reconnect is told the engine is silent."""
    assert rig.bridge._stale.interval() == STALE_MS and rig.bridge.connected
    quiet_from = time.monotonic()
    rig.host.stop()
    rig.wait_for(lambda: rig.disconnects(quiet_from), 15.0, "the watchdog's blanking")
    when, text = rig.disconnects(quiet_from)[0]
    assert "no data from the engine" in text
    assert STALE_MS / 1000.0 - 0.6 <= when - quiet_from <= STALE_MS / 1000.0 + 1.5, when - quiet_from
    assert rig.bridge.latest == {} and all(text == NO_DATA for text in rig.readouts())

    def watchdog_blanks() -> int:
        return sum("no data from the engine" in text for _, text in rig.disconnects(when))

    rig.wait_for(lambda: watchdog_blanks() >= 3, 3 * PAST_THE_WATCHDOG_S + 6.0,
                 "two more reconnect cycles, each blanked by the watchdog")
    assert all(not state for t, state in rig.snapshots if t >= when), "a silent engine's packet reached the console"
    silences = [text for t, text in rig.statuses if t >= when and text.startswith("ENGINE SILENT")]
    assert len(silences) >= 2, rig.statuses[-12:]
    assert rig.bridge.latest == {} and all(text == NO_DATA for text in rig.readouts())


def test_a_closed_link_blanks_the_console_at_once_not_after_the_watchdog(rig):
    closed_at = time.monotonic()
    rig.stop_server()
    rig.wait_for(lambda: rig.disconnects(closed_at), STALE_MS / 1000.0, "the link-lost blanking")
    when, text = rig.disconnects(closed_at)[0]
    assert "no data from the engine" not in text and when - closed_at < STALE_MS / 1000.0 - 1.0
    assert rig.bridge.latest == {} and all(text == NO_DATA for text in rig.readouts())
