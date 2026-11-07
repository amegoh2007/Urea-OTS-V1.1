"""The hand-over from the intro to the console — `ureasim.hmi.startup`.

Pinned:
* (the 100% LOAD key's command, the engine's own ``freeze`` with ``on`` stated, is pinned in
  ``tests/data/test_intro.py``);
* the press builds the console first, waits for the engine, and connects the bridge only then;
* the release goes out once per link, again after a reconnect, and the first packet (never an empty
  one) ends the wait;
* a refusal, a silent engine and a missing engine each end the wait with a reason instead of leaving
  the intro on "STARTING SIMULATOR";
* the console is shown only when the intro asks for it;
* LOAD (decision 171): the engine's exercises asked for and offered, nothing sent until one is chosen,
  the chosen one restored and only then released, and the wait ended by the packet that follows the
  release's acceptance, never the restored plant's rehearsed one; a refused exercise opens the chooser again
  with the engine's reason, the plant still held; Cancel or no saved exercise takes the intro back to its
  buttons, saying so, nothing started, and the next press goes on from the same console and link; the wait
  does not run while the chooser is open or the buttons wait; each step goes out once per link and again
  after a reconnect;
* over a real link, from a real scenario file, to a running console: ``tests/hmi/test_start_from_exercise.py``.
"""

from __future__ import annotations

import dataclasses
import threading
import time

import pytest
from PyQt6.QtCore import QCoreApplication, QObject, pyqtSignal

from ureasim.data.intro import LOAD_OPTION, START_OPTION, STARTUP
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
        self.rearmed: list[str] = []
        self.ready = 0
        self.raised = 0

    def set_status(self, text: str) -> None:
        self.statuses.append(text)

    def rearm(self, status: str) -> None:
        self.rearmed.append(status)

    def repaint(self) -> None:
        pass

    def mark_ready(self) -> None:
        self.ready += 1

    def raise_(self) -> None:
        self.raised += 1


class FakeBridge(QObject):
    """The bridge as the controller sees it: four signals, a link flag and what was sent."""

    status = pyqtSignal(str, str)
    command_result = pyqtSignal(int, bool, str)
    snapshot = pyqtSignal(object)
    exercises_received = pyqtSignal(object, str)

    def __init__(self) -> None:
        super().__init__()
        self.connected = False
        self.connects: list[tuple[str, int]] = []
        self.sent: list[dict] = []
        self.lists = 0

    def connect_to(self, host: str, port: int) -> None:
        self.connects.append((host, port))

    def send_command(self, command) -> int:
        if not self.connected:
            return 0
        self.sent.append(dict(command))
        return len(self.sent)

    def request_exercises(self) -> bool:
        if not self.connected:
            return False
        self.lists += 1
        return True

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
        self.offered: list[list[str]] = []                 # what the chooser was shown
        self.notes: list[str] = []                         # and the note it was shown with
        self.answer = None                                 # how to answer it, once shown
        self.controller = StartupController(
            splash=self.splash, bridge=self.bridge, make_window=self._make_window,
            engine_ready=self.ready, engine_alive=lambda: self.alive, host="127.0.0.1", port=8765,
            choose=self._choose)
        self.controller.failed.connect(self.failures.append)

    def _make_window(self) -> FakeWindow:
        self.built.append(FakeWindow())
        return self.built[-1]

    def _choose(self, names, done, note) -> None:
        self.offered.append(list(names))
        self.notes.append(note)
        self.answer = done

    def press(self, key: str = START_OPTION.key) -> None:
        self.splash.start_requested.emit(key)

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


def test_100_percent_load_does_not_listen_for_exercises(rig) -> None:
    rig.ready.set()
    rig.press()
    rig.settle(lambda: rig.bridge.connects)
    rig.bridge.link_up()
    assert rig.bridge.receivers(rig.bridge.exercises_received) == 0 and rig.bridge.lists == 0
    rig.bridge.exercises_received.emit(["x"], "")      # someone else's list: not this start's
    assert rig.offered == [] and rig.bridge.sent == [{"type": "freeze", "on": False}]


# -- the start from a saved exercise (LOAD, decision 171) ----------------------------------------------------

_RELEASE = {"type": "freeze", "on": False}
_PACKET = {"_health": {"ok": True}}


def _restore(name: str) -> dict:
    return {"type": "snapshot_load", "name": name}


def _at_the_chooser(rig: Rig, names=("load095_steam", "load100_steam")) -> None:
    """LOAD pressed, the link up, the engine's list in, the chooser open."""
    rig.ready.set()
    rig.press(LOAD_OPTION.key)
    rig.settle(lambda: rig.bridge.connects)
    rig.bridge.link_up()
    assert rig.bridge.lists == 1 and rig.splash.statuses[-1] == STARTUP.listing
    rig.bridge.exercises_received.emit(list(names), "")


def test_load_asks_for_the_exercises_and_sends_nothing_until_one_is_chosen(rig) -> None:
    _at_the_chooser(rig)
    assert rig.offered == [["load095_steam", "load100_steam"]]
    assert rig.splash.statuses[-1] == STARTUP.choosing
    assert rig.bridge.sent == []                         # no release, no restore: the plant stays held
    rig.bridge.status.emit("ENGINE FROZEN — the plant clock is held", "warn")
    rig.bridge.snapshot.emit(_PACKET)                    # a packet is not the plant running yet
    assert rig.bridge.sent == [] and rig.splash.ready == 0


def test_the_chosen_exercise_is_restored_then_released_and_the_packet_after_that_ends_the_wait(rig) -> None:
    _at_the_chooser(rig)
    rig.answer("load100_steam")
    assert rig.bridge.sent == [_restore("load100_steam")]
    assert rig.splash.statuses[-1] == STARTUP.restoring.format(name="load100_steam")
    rig.bridge.snapshot.emit(_PACKET)                    # the restored plant's rehearsed tick, still held
    assert rig.splash.ready == 0
    rig.bridge.command_result.emit(1, True, "")          # the exercise accepted: now the release
    assert rig.bridge.sent == [_restore("load100_steam"), _RELEASE]
    assert rig.splash.statuses[-1] == STARTUP.releasing
    rig.bridge.snapshot.emit(_PACKET)                    # published before the release was applied
    assert rig.splash.ready == 0
    rig.bridge.command_result.emit(2, True, "")          # the release accepted
    rig.bridge.snapshot.emit({})                         # a blank console is not the plant running
    assert rig.splash.ready == 0
    rig.bridge.snapshot.emit(_PACKET)
    assert rig.splash.ready == 1
    assert rig.bridge.receivers(rig.bridge.exercises_received) == 0      # the hand-over let go of the list


def test_a_refused_exercise_opens_the_chooser_again_with_the_engines_reason_and_sends_no_release(
        qapp, monkeypatch) -> None:
    """Decided 2026-11-06: the plant stays held, the operator sees why and chooses another or cancels."""
    rig = Rig(qapp, monkeypatch, packet_timeout_s=0.05)
    _at_the_chooser(rig)
    assert rig.notes == [""]                             # the first offer carries no note
    rig.answer("load100_steam")
    rig.bridge.command_result.emit(99, False, "someone else's command")  # not ours: ignored
    assert len(rig.offered) == 1
    rig.bridge.command_result.emit(1, False, "not a ureasim exercise snapshot")
    refusal = STARTUP.refused.format(name="load100_steam", reason="not a ureasim exercise snapshot")
    assert rig.offered == [["load095_steam", "load100_steam"]] * 2 and rig.notes[-1] == refusal
    assert rig.splash.statuses[-1] == refusal and rig.splash.ready == 0
    assert rig.bridge.sent == [_restore("load100_steam")]          # no release: the plant stays held
    for _ in range(40):                                  # the wait stopped again while the operator decides
        QCoreApplication.processEvents()
        time.sleep(0.005)
    assert rig.splash.ready == 0
    rig.answer("load095_steam")                          # another exercise, restored and released
    assert rig.bridge.sent == [_restore("load100_steam"), _restore("load095_steam")]
    rig.bridge.command_result.emit(2, True, "")
    rig.bridge.command_result.emit(3, True, "")
    rig.bridge.snapshot.emit(_PACKET)
    assert rig.splash.ready == 1 and rig.bridge.sent[-1] == _RELEASE


def test_cancel_after_a_refusal_goes_back_to_the_buttons(rig) -> None:
    _at_the_chooser(rig)
    rig.answer("load100_steam")
    rig.bridge.command_result.emit(1, False, "cannot read it")
    rig.answer(None)
    assert rig.splash.rearmed == [STARTUP.no_choice]
    assert rig.bridge.sent == [_restore("load100_steam")] and rig.splash.ready == 0


def test_a_refused_release_after_a_restore_ends_the_wait_with_the_engines_reason(rig) -> None:
    _at_the_chooser(rig)
    rig.answer("load100_steam")
    rig.bridge.command_result.emit(1, True, "")
    rig.bridge.command_result.emit(2, False, "plant latched")
    assert rig.splash.ready == 1 and rig.splash.statuses[-1] == "the engine refused the start: plant latched"


def test_cancel_goes_back_to_the_buttons_and_100_percent_load_then_starts_on_the_same_console(rig) -> None:
    """Decided 2026-11-06: nothing starts until the operator presses a button again."""
    _at_the_chooser(rig)
    rig.answer(None)
    assert rig.splash.rearmed == [STARTUP.no_choice] and rig.bridge.sent == []
    rig.bridge.snapshot.emit(_PACKET)                    # back at the buttons a packet ends nothing
    assert rig.splash.ready == 0
    rig.answer("load100_steam")                          # a late answer changes nothing
    assert rig.bridge.sent == []
    rig.press(START_OPTION.key)                          # 100% LOAD now: the console and its link are up
    assert len(rig.built) == 1 and rig.bridge.connects == [("127.0.0.1", 8765)]
    assert rig.bridge.sent == [_RELEASE] and rig.splash.statuses[-1] == STARTUP.releasing
    rig.bridge.snapshot.emit(_PACKET)                    # nothing was restored: as after 100% LOAD
    assert rig.splash.ready == 1


def test_load_pressed_again_after_cancel_asks_for_the_exercises_again(rig) -> None:
    _at_the_chooser(rig)
    rig.answer(None)
    rig.press(LOAD_OPTION.key)
    assert len(rig.built) == 1 and rig.bridge.lists == 2
    rig.bridge.exercises_received.emit(["load100_steam"], "")
    assert rig.offered[-1] == ["load100_steam"]
    rig.answer("load100_steam")
    rig.bridge.command_result.emit(1, True, "")
    rig.bridge.command_result.emit(2, True, "")
    rig.bridge.snapshot.emit(_PACKET)
    assert rig.bridge.sent == [_restore("load100_steam"), _RELEASE] and rig.splash.ready == 1


def test_no_saved_exercise_goes_back_to_the_buttons_and_says_so(rig) -> None:
    _at_the_chooser(rig, names=())
    assert rig.offered == []                             # no empty chooser
    assert rig.splash.rearmed == [STARTUP.no_exercises] and rig.bridge.sent == []


def test_a_list_the_engine_refused_goes_back_to_the_buttons_with_its_reason(rig) -> None:
    rig.ready.set()
    rig.press(LOAD_OPTION.key)
    rig.settle(lambda: rig.bridge.connects)
    rig.bridge.link_up()
    rig.bridge.exercises_received.emit([], "no engine attached")
    assert rig.splash.rearmed == [f"{STARTUP.no_exercises} (no engine attached)"]
    assert rig.bridge.sent == []


def test_back_at_the_buttons_nothing_is_sent_and_no_wait_runs(qapp, monkeypatch) -> None:
    rig = Rig(qapp, monkeypatch, packet_timeout_s=0.05)
    _at_the_chooser(rig)
    rig.answer(None)
    rig.bridge.link_down()                               # the watchdog's drops while the operator decides
    rig.bridge.link_up()
    for _ in range(40):                                  # 0.2 s, four times the wait
        QCoreApplication.processEvents()
        time.sleep(0.005)
    assert rig.splash.ready == 0 and rig.bridge.sent == [] and rig.bridge.lists == 1
    rig.press(START_OPTION.key)                          # the next press starts the wait again
    rig.settle(lambda: rig.splash.ready == 1)
    assert rig.splash.statuses[-1].startswith("no packet from the engine within")


def test_the_wait_for_the_engine_stops_while_the_chooser_is_open_and_restarts_at_the_choice(qapp, monkeypatch) -> None:
    rig = Rig(qapp, monkeypatch, packet_timeout_s=0.05)
    _at_the_chooser(rig)
    for _ in range(40):                                  # 0.2 s, four times the wait, with the chooser open
        QCoreApplication.processEvents()
        time.sleep(0.005)
    assert rig.splash.ready == 0 and rig.splash.statuses[-1] == STARTUP.choosing
    rig.answer("load100_steam")
    rig.settle(lambda: rig.splash.ready == 1)            # and once chosen, a silent engine still ends it
    assert rig.splash.statuses[-1].startswith("no packet from the engine within")


def test_a_list_that_never_comes_ends_the_wait(qapp, monkeypatch) -> None:
    rig = Rig(qapp, monkeypatch, packet_timeout_s=0.05)
    rig.ready.set()
    rig.press(LOAD_OPTION.key)
    rig.settle(lambda: rig.bridge.connects)
    rig.bridge.link_up()
    rig.settle(lambda: rig.splash.ready == 1)
    assert rig.splash.statuses[-1].startswith("no exercise list from the engine within")
    assert rig.bridge.sent == []


def test_each_step_goes_out_once_per_link_and_again_after_a_reconnect(rig) -> None:
    """A held engine is silent, so the bridge's first-packet watchdog may drop and reconnect the link."""
    rig.ready.set()
    rig.press(LOAD_OPTION.key)
    rig.settle(lambda: rig.bridge.connects)
    rig.bridge.link_up()
    rig.bridge.status.emit("connected — engine: test", "ok")          # the same link: not asked again
    rig.bridge.link_down()
    rig.bridge.link_up()
    assert rig.bridge.lists == 2                         # the list asked again on the new link
    rig.bridge.exercises_received.emit(["a", "b"], "")
    rig.bridge.exercises_received.emit(["a", "b"], "")   # the second link's answer: the chooser opens once
    assert rig.offered == [["a", "b"]]
    rig.bridge.link_down()
    rig.bridge.link_up()                                 # chooser open: nothing to send, nothing asked
    assert rig.bridge.sent == [] and rig.bridge.lists == 2
    rig.bridge.link_down()
    rig.answer("b")                                      # chosen with the link down: sent when it is back
    assert rig.bridge.sent == []
    rig.bridge.link_up()
    assert rig.bridge.sent == [_restore("b")]
    rig.bridge.link_down()                               # its answer lost with the link: restored again
    rig.bridge.link_up()
    assert rig.bridge.sent == [_restore("b")] * 2
    rig.bridge.command_result.emit(2, True, "")
    assert rig.bridge.sent == [_restore("b")] * 2 + [_RELEASE]
    rig.bridge.link_down()
    rig.bridge.link_up()
    assert rig.bridge.sent == [_restore("b")] * 2 + [_RELEASE] * 2
    rig.bridge.command_result.emit(4, True, "")
    rig.bridge.snapshot.emit(_PACKET)
    assert rig.splash.ready == 1
