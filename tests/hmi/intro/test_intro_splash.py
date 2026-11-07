"""Tests of ureasim/hmi/intro/splash.py: the start buttons and their keys, signal order, skip, paint.

Skipped where PyQt6 is not installed. The clock is replaced by a variable, so no test waits. The splash
here draws itself (``opengl=False``): dozens of shown windows each holding a GPU context would exhaust a
driver, and the picture must not depend on the machine running the tests. The GPU canvas has its own
tests in ``test_intro_canvas.py``.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from ureasim.data.intro import LOAD_OPTION, START_OPTION, STRINGS, TIMELINE
from ureasim.hmi.intro import IntroSplash
from ureasim.hmi.intro.scene import ButtonState, button_rect, pixel_scale, view_rect
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
        self.splash = IntroSplash(opengl=False)
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

    def button_px(self, key: str = START_OPTION.key) -> tuple[float, float]:
        view, s = view_rect(_W, _H), pixel_scale(_W, _H)
        r = button_rect(key)
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
    assert "hfc-logo" in IntroSplash(opengl=False)._painter._pixmaps


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
    rig.splash._set_hover(START_OPTION.key)
    assert rig.splash._hover == START_OPTION.key
    rig.splash._click_at(*rig.button_px())
    assert rig.splash._hover is None  # pressing clears it


def test_paint_event_renders_and_the_button_states_differ(app) -> None:
    rig = _Rig().at_button()
    idle = rig.splash.grab().toImage()
    ratio = idle.devicePixelRatio()  # 1.25 on a 125 % display: the grab is in device pixels
    assert idle.width() == round(_W * ratio) and idle.height() == round(_H * ratio)
    rig.splash._set_hover(START_OPTION.key)
    hover = rig.splash.grab().toImage()
    assert hover != idle
    rig.splash._set_hover(LOAD_OPTION.key)
    hover_load = rig.splash.grab().toImage()
    assert hover_load not in (idle, hover)
    rig.splash._set_hover(None)
    rig.splash._click_at(*rig.button_px())
    rig.tick(rig.now + 0.02)  # START: busy, status line shown
    assert rig.splash.grab().toImage() not in (idle, hover)


def test_a_click_on_load_raises_its_own_start_key(app) -> None:
    rig = _Rig().at_button()
    rig.splash._click_at(*rig.button_px(LOAD_OPTION.key))
    rig.tick(rig.now + 0.02)
    assert rig.log == [f"start:{LOAD_OPTION.key}"] and LOAD_OPTION.key == "load_exercise"
    rig.splash.mark_ready()
    rig.tick(rig.now + 0.02)
    assert rig.log == ["start:load_exercise", "reveal"]


def test_enter_still_presses_100_percent_load_not_load(app) -> None:
    rig = _Rig().at_button()
    rig.splash._set_hover(LOAD_OPTION.key)               # the pointer resting on LOAD does not redirect Enter
    rig.splash._key(Qt.Key.Key_Return.value)
    rig.tick(rig.now + 0.02)
    assert rig.log == ["start:load_100"]


def test_one_press_is_taken_whichever_button_it_was(app) -> None:
    rig = _Rig().at_button()
    rig.splash._click_at(*rig.button_px(LOAD_OPTION.key))
    rig.splash._click_at(*rig.button_px())
    rig.splash._key(Qt.Key.Key_Return.value)
    for i in range(1, 4):
        rig.tick(rig.now + 0.5 * i)
    assert rig.log == ["start:load_exercise"]


def test_a_click_between_the_two_buttons_does_nothing(app) -> None:
    rig = _Rig().at_button()
    (x0, y), (x1, _) = rig.button_px(), rig.button_px(LOAD_OPTION.key)
    view, s = view_rect(_W, _H), pixel_scale(_W, _H)
    gap_x = ((button_rect().right + button_rect(LOAD_OPTION.key).x) / 2.0 - view.x) * s
    assert x0 < gap_x < x1
    rig.splash._click_at(gap_x, y)
    rig.tick(rig.now + 0.1)
    assert rig.log == [] and rig.splash._seq.awaiting_start


def test_the_pointer_lights_the_button_under_it_and_both_work_after_a_press(app) -> None:
    rig = _Rig().at_button()
    rig.splash._set_hover(LOAD_OPTION.key)
    assert rig.splash._button_state() == {LOAD_OPTION.key: ButtonState.HOVER}
    rig.splash._set_hover(None)
    assert rig.splash._button_state() == {}
    rig.splash._click_at(*rig.button_px(LOAD_OPTION.key))
    rig.tick(rig.now + 0.02)
    assert rig.splash._button_state() is ButtonState.BUSY


def test_rearm_puts_the_buttons_back_with_the_reason_and_the_next_press_starts_again(app) -> None:
    """After LOAD the operator chose no exercise: the buttons are live again, nothing started."""
    rig = _Rig().at_button()
    rig.splash._click_at(*rig.button_px(LOAD_OPTION.key))
    rig.tick(rig.now + 0.02)
    assert rig.splash._button_state() is ButtonState.BUSY
    rig.splash.rearm("No exercise chosen")
    assert rig.splash._seq.awaiting_start and rig.splash._status == "No exercise chosen"
    assert rig.splash._button_state() == {}                           # both pills waiting again
    rig.tick(rig.now + 2.0)
    assert rig.log == ["start:load_exercise"] and rig.splash.isVisible()
    rig.splash._key(Qt.Key.Key_Return.value)                          # now 100% LOAD
    rig.tick(rig.now + 0.02)
    assert rig.log == ["start:load_exercise", "start:load_100"]


def test_rearm_does_nothing_once_the_console_is_ready(app) -> None:
    rig = _Rig().at_button()
    rig.splash._click_at(*rig.button_px())
    rig.tick(rig.now + 0.02)
    rig.splash.mark_ready()
    rig.splash.rearm("late")
    assert not rig.splash._seq.awaiting_start and rig.splash._status != "late"


def test_status_text_repaints(app) -> None:
    rig = _Rig().at_button()
    before = rig.splash.grab().toImage()
    rig.splash.set_status("Building screens")
    assert rig.splash.grab().toImage() != before
