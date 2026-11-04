"""The hand-over from the intro to the console — `ureasim.hmi.startup`.

Pinned:
* (the 100% LOAD key's command, the engine's own ``freeze`` with ``on`` stated, is pinned in
  ``tests/data/test_intro.py``);
* the press builds the console first, waits for the engine, and connects the bridge only then;
* the release goes out once per link, again after a reconnect, and the first packet (never an empty
  one) ends the wait;
* a refusal, a silent engine and a missing engine each end the wait with a reason instead of leaving
  the intro on "STARTING SIMULATOR";
* the console is shown only when the intro asks for it.
"""

from __future__ import annotations

import dataclasses
import threading
import time

import pytest
from PyQt6.QtCore import QCoreApplication, QObject, pyqtSignal

from ureasim.data.intro import START_OPTION, STARTUP
from ureasim.hmi import startup
from ureasim.hmi.bridge import FIRST_PACKET_STALE_MS
from ureasim.hmi.startup import StartupController


class FakeSplash(QObject):
    """The intro as the controller sees it: two signals and four calls."""

    start_requested = pyqtSignal(str)
    reveal = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.statuses: list[str] = []
        self.ready = 0
        self.raised = 0

    def set_status(self, text: str) -> None:
        self.statuses.append(text)

    def repaint(self) -> None:
        pass

    def mark_ready(self) -> None:
        self.ready += 1

    def raise_(self) -> None:
        self.raised += 1


class FakeBridge(QObject):
    """The bridge as the controller sees it: three signals, a link flag and what was sent."""

    status = pyqtSignal(str, str)
    command_result = pyqtSignal(int, bool, str)
    snapshot = pyqtSignal(object)

    def __init__(self) -> None:
        super().__init__()
        self.connected = False
        self.connects: list[tuple[str, int]] = []
        self.sent: list[dict] = []

    def connect_to(self, host: str, port: int) -> None:
        self.connects.append((host, port))

    def send_command(self, command) -> int:
        if not self.connected:
            return 0
        self.sent.append(dict(command))
        return len(self.sent)

    def link_up(self) -> None:
        self.connected = True
        self.status.emit("connected — engine: test", "ok")

    def link_down(self) -> None:
        self.connected = False
        self.status.emit("DISCONNECTED — link lost", "fault")


class FakeWindow:
    def __init__(self) -> None:
        self.shown = 0

    def show(self) -> None:
        self.shown += 1


class Rig:
    """A controller over fakes, with an engine whose readiness the test decides."""

    def __init__(self, qapp, monkeypatch, **timing) -> None:
        monkeypatch.setattr(startup, "STARTUP", dataclasses.replace(STARTUP, poll_ms=5, watch_ms=5, **timing))
        self.splash, self.bridge = FakeSplash(), FakeBridge()
        self.ready, self.alive = threading.Event(), True
        self.built: list[FakeWindow] = []
        self.failures: list[str] = []
        self.controller = StartupController(
            splash=self.splash, bridge=self.bridge, make_window=self._make_window,
            engine_ready=self.ready, engine_alive=lambda: self.alive, host="127.0.0.1", port=8765)
        self.controller.failed.connect(self.failures.append)

    def _make_window(self) -> FakeWindow:
        self.built.append(FakeWindow())
        return self.built[-1]

    def press(self) -> None:
        self.splash.start_requested.emit(START_OPTION.key)

    def settle(self, condition, timeout: float = 2.0) -> None:
        end = time.monotonic() + timeout
        while not condition() and time.monotonic() < end:
            QCoreApplication.processEvents()
            time.sleep(0.002)
        assert condition()


@pytest.fixture()
def rig(qapp, monkeypatch) -> Rig:
    return Rig(qapp, monkeypatch)


def test_the_press_builds_the_console_then_waits_for_the_engine_before_it_connects(rig) -> None:
    rig.press()
    assert len(rig.built) == 1 and rig.built[0].shown == 0
    assert rig.splash.statuses == [STARTUP.building, STARTUP.engine]
    for _ in range(10):                                # let the 5 ms poll run a few times
        QCoreApplication.processEvents()
        time.sleep(0.005)
    assert rig.bridge.connects == []                 # the engine is not ready: no connection yet
    rig.ready.set()
    rig.settle(lambda: rig.bridge.connects)
    assert rig.bridge.connects == [("127.0.0.1", 8765)]
    assert rig.splash.statuses[-1] == STARTUP.connecting


def test_the_release_is_sent_once_per_link_and_the_first_packet_ends_the_wait(rig) -> None:
    rig.ready.set()
    rig.press()
    rig.settle(lambda: rig.bridge.connects)
    rig.bridge.status.emit("connecting …", "warn")     # link not up yet: nothing to send
    assert rig.bridge.sent == []
    rig.bridge.link_up()
    rig.bridge.status.emit("ENGINE FROZEN — the plant clock is held", "warn")
    assert rig.bridge.sent == [{"type": "freeze", "on": False}]
    assert rig.splash.statuses[-1] == STARTUP.releasing
    rig.bridge.snapshot.emit({})                       # a blank console is not the plant running
    assert rig.splash.ready == 0
    rig.bridge.snapshot.emit({"_health": {"ok": True}})
    assert rig.splash.ready == 1
    rig.bridge.snapshot.emit({"_health": {"ok": True}})
    assert rig.splash.ready == 1                       # once only


def test_a_dropped_link_gets_the_release_again(rig) -> None:
    rig.ready.set()
    rig.press()
    rig.settle(lambda: rig.bridge.connects)
    rig.bridge.link_up()
    rig.bridge.link_down()
    rig.bridge.link_up()
    assert rig.bridge.sent == [{"type": "freeze", "on": False}] * 2


def test_the_console_is_shown_only_when_the_intro_reveals_it(rig) -> None:
    rig.ready.set()
    rig.press()
    rig.settle(lambda: rig.bridge.connects)
    rig.bridge.link_up()
    rig.bridge.snapshot.emit({"_health": {"ok": True}})
    assert rig.built[0].shown == 0
    rig.splash.reveal.emit()
    assert rig.built[0].shown == 1 and rig.splash.raised == 1


def test_a_refused_release_still_ends_the_wait_with_the_engines_reason(rig) -> None:
    rig.ready.set()
    rig.press()
    rig.settle(lambda: rig.bridge.connects)
    rig.bridge.link_up()
    rig.bridge.command_result.emit(99, False, "someone else's command")   # not ours: ignored
    assert rig.splash.ready == 0
    rig.bridge.command_result.emit(1, False, "plant latched")
    assert rig.splash.ready == 1
    assert rig.splash.statuses[-1] == "the engine refused the start: plant latched"


def test_a_silent_engine_ends_the_wait_after_the_packet_timeout(qapp, monkeypatch) -> None:
    rig = Rig(qapp, monkeypatch, packet_timeout_s=0.05)
    rig.ready.set()
    rig.press()
    rig.settle(lambda: rig.bridge.connects)
    rig.bridge.link_up()
    rig.settle(lambda: rig.splash.ready == 1)
    assert rig.splash.statuses[-1].startswith("no packet from the engine within")


def test_an_engine_that_never_started_fails_the_application(rig) -> None:
    rig.alive = False
    rig.press()
    rig.settle(lambda: rig.failures)
    assert rig.failures == ["the engine did not start"]
    assert rig.bridge.connects == [] and rig.splash.ready == 0


def test_an_engine_that_is_too_slow_fails_the_application(qapp, monkeypatch) -> None:
    rig = Rig(qapp, monkeypatch, engine_timeout_s=0.02)
    rig.press()
    rig.settle(lambda: rig.failures)
    assert rig.failures == ["the engine did not start"]


def test_an_engine_that_dies_before_the_press_fails_the_application_at_launch(rig) -> None:
    """A port held by another instance: the thread ends without serving, long before 100% LOAD."""
    rig.alive = False
    rig.settle(lambda: rig.failures)                   # no press
    assert rig.failures == ["the engine did not start"]
    assert rig.built == [] and rig.bridge.connects == []


def test_a_healthy_engine_is_left_alone_before_the_press(rig) -> None:
    rig.ready.set()
    for _ in range(10):
        QCoreApplication.processEvents()
        time.sleep(0.005)
    rig.alive = False                                  # a thread that ended after serving is not a failure
    for _ in range(10):
        QCoreApplication.processEvents()
        time.sleep(0.005)
    assert rig.failures == []


def test_the_controllers_wait_for_the_first_packet_outlasts_the_bridges() -> None:
    """The bridge's own watchdog must speak first, or the two race at the same instant."""
    assert STARTUP.packet_timeout_s * 1000 > FIRST_PACKET_STALE_MS
