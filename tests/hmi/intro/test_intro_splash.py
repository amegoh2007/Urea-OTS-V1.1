"""Tests of ureasim/hmi/intro/splash.py: the start button, signal order, skip, paint.

Skipped where PyQt6 is not installed. The clock is replaced by a variable, so no test waits.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from ureasim.data.intro import START_OPTION, STRINGS, TIMELINE
from ureasim.hmi.intro import IntroSplash
from ureasim.hmi.intro.scene import button_rect, pixel_scale, view_rect
from ureasim.hmi.intro.sequencer import Phase

_W, _H = 683, 360


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class _Rig:
    """A splash with a manual clock and a log of the signals it raises."""

    def __init__(self) -> None:
        self.now = 0.0
        self.log: list[str] = []
        self.splash = IntroSplash()
        self.splash.resize(_W, _H)
        self.splash._now = lambda: self.now  # type: ignore[method-assign]
        self.splash.start_requested.connect(lambda key: self.log.append(f"start:{key}"))
        self.splash.reveal.connect(lambda: self.log.append("reveal"))
        self.splash.finished.connect(lambda: self.log.append("finished"))
        self.splash.show()

    def tick(self, now: float) -> None:
        self.now = now
        self.splash._on_tick()

    def at_button(self) -> "_Rig":
        """Run the scene to its end so the button is live."""
        self.tick(TIMELINE.hold + 0.02)
        assert self.splash._seq.phase is Phase.AWAITING
        return self

    def button_px(self) -> tuple[float, float]:
        view, s = view_rect(_W, _H), pixel_scale(_W, _H)
        r = button_rect()
        return (r.cx - view.x) * s, (r.cy - view.y) * s


def test_lazy_export_gives_the_splash_class() -> None:
    from ureasim.hmi.intro.splash import IntroSplash as direct

    assert IntroSplash is direct


def test_the_scene_plays_and_then_waits_on_the_button_without_starting_anything(app) -> None:
    rig = _Rig()
    for t in (0.0, 2.0, 5.0, TIMELINE.hold, TIMELINE.hold + 30.0):
        rig.tick(t)
    assert rig.log == [] and rig.splash.isVisible()


def test_click_on_the_button_starts_the_simulator_then_ready_reveals_then_finishes(app) -> None:
    rig = _Rig().at_button()
    rig.splash._click_at(*rig.button_px())
    rig.tick(rig.now + 0.02)
    assert rig.log == [f"start:{START_OPTION.key}"] and START_OPTION.key == "load_100"
    assert rig.splash._status == STRINGS.starting
    rig.tick(rig.now + 3.0)
    assert rig.log == ["start:load_100"]  # the console is not ready: still waiting, still visible
    assert rig.splash.isVisible()
    rig.splash.mark_ready()
    rig.tick(rig.now + 0.02)
    assert rig.log == ["start:load_100", "reveal"]
    rig.tick(rig.now + TIMELINE.fade / 2.0)
    assert rig.splash.windowOpacity() == pytest.approx(0.5, abs=0.1)
    rig.tick(rig.now + TIMELINE.fade)
    assert rig.log == ["start:load_100", "reveal", "finished"] and not rig.splash.isVisible()


def test_a_click_beside_the_button_does_nothing(app) -> None:
    rig = _Rig().at_button()
    x, y = rig.button_px()
    for dx, dy in ((0.0, 120.0), (-200.0, 0.0), (200.0, 0.0), (0.0, -120.0)):
        rig.splash._click_at(x + dx, y + dy)
    rig.tick(rig.now + 0.1)
    assert rig.log == [] and rig.splash._seq.phase is Phase.AWAITING


def test_enter_return_and_space_press_the_button_other_keys_do_not(app) -> None:
    for key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
        rig = _Rig().at_button()
        rig.splash._key(key.value)
        rig.tick(rig.now + 0.02)
        assert rig.log == ["start:load_100"], key
    rig = _Rig().at_button()
    for key in (Qt.Key.Key_A, Qt.Key.Key_Escape, Qt.Key.Key_Tab):
        rig.splash._key(key.value)
    rig.tick(rig.now + 0.1)
    assert rig.log == []


def test_a_key_or_click_during_the_scene_only_skips_to_the_button(app) -> None:
    for act in (lambda r: r.splash._key(Qt.Key.Key_A.value), lambda r: r.splash._click_at(10.0, 10.0), lambda r: r.splash._key(Qt.Key.Key_Return.value)):
        rig = _Rig()
        rig.tick(1.0)
        act(rig)
        assert rig.splash._seq.skipped and rig.splash._seq.awaiting_start
        rig.tick(1.5)
        rig.tick(30.0)
        assert rig.log == [] and rig.splash.isVisible()


def test_after_a_skip_the_button_starts_the_simulator(app) -> None:
    rig = _Rig()
    rig.tick(1.0)
    rig.splash._key(Qt.Key.Key_A.value)
    rig.splash._click_at(*rig.button_px())
    rig.tick(1.1)
    assert rig.log == ["start:load_100"]


def test_the_painter_is_warmed_before_the_window_is_shown(app) -> None:
    """The font database and the logo are paid for in the constructor, not in the middle of the animation."""
    assert "hfc-logo" in IntroSplash()._painter._pixmaps


def test_pressing_twice_starts_once(app) -> None:
    rig = _Rig().at_button()
    for _ in range(3):
        rig.splash._click_at(*rig.button_px())
        rig.splash._key(Qt.Key.Key_Return.value)
    for i in range(1, 6):
        rig.tick(rig.now + 0.5 * i)
    assert rig.log.count("start:load_100") == 1


def test_a_console_ready_before_the_press_reveals_right_after_it(app) -> None:
    rig = _Rig()
    rig.splash.mark_ready()
    rig.at_button()
    assert rig.log == []  # ready alone never ends the show
    rig.splash._click_at(*rig.button_px())
    rig.tick(rig.now + 0.02)
    rig.tick(rig.now + 0.02)
    assert rig.log == ["start:load_100", "reveal"]


def test_pressing_the_button_clears_its_hover_state(app) -> None:
    rig = _Rig().at_button()
    rig.splash._set_hover(True)
    assert rig.splash._hover
    rig.splash._click_at(*rig.button_px())
    assert not rig.splash._hover  # pressing clears it


def test_paint_event_renders_and_the_button_states_differ(app) -> None:
    rig = _Rig().at_button()
    idle = rig.splash.grab().toImage()
    ratio = idle.devicePixelRatio()  # 1.25 on a 125 % display: the grab is in device pixels
    assert idle.width() == round(_W * ratio) and idle.height() == round(_H * ratio)
    rig.splash._set_hover(True)
    hover = rig.splash.grab().toImage()
    assert hover != idle
    rig.splash._set_hover(False)
    rig.splash._click_at(*rig.button_px())
    rig.tick(rig.now + 0.02)  # START: busy, status line shown
    assert rig.splash.grab().toImage() not in (idle, hover)


def test_status_text_repaints(app) -> None:
    rig = _Rig().at_button()
    before = rig.splash.grab().toImage()
    rig.splash.set_status("Building screens")
    assert rig.splash.grab().toImage() != before
