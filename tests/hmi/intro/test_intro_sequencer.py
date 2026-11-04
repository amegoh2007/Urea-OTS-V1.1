"""Tests of ureasim/hmi/intro/sequencer.py: every playback path, with no display and no real clock."""

from __future__ import annotations

import pytest

from ureasim.data.intro import TIMELINE
from ureasim.hmi.intro.sequencer import Event, IntroSequencer, Phase

_TICK = 0.016


def _run(seq: IntroSequencer, start: float, stop: float, *, on=None) -> list[tuple[float, Event]]:
    """Advance in 16 ms ticks and collect (time, event); ``on`` is called with each event."""
    out: list[tuple[float, Event]] = []
    now = start
    while now <= stop:
        for ev in seq.advance(now):
            out.append((now, ev))
            if on is not None:
                on(ev)
        now += _TICK
    return out


def _to_awaiting() -> IntroSequencer:
    seq = IntroSequencer()
    _run(seq, 0.0, TIMELINE.hold + 0.1)
    assert seq.phase is Phase.AWAITING
    return seq


def test_the_scene_ends_on_the_button_and_waits_there_forever() -> None:
    seq = IntroSequencer()
    assert _run(seq, 0.0, TIMELINE.hold + 600.0) == []
    assert seq.phase is Phase.AWAITING and seq.awaiting_start and not seq.busy
    assert seq.opacity == 1.0 and seq.scene_time == pytest.approx(TIMELINE.hold)


def test_scene_time_is_clamped_and_wall_time_is_not() -> None:
    seq = IntroSequencer()
    seq.advance(3.0)
    assert seq.scene_time == pytest.approx(3.0) and seq.wall_time == pytest.approx(3.0)
    seq.advance(TIMELINE.hold + 4.0)
    assert seq.scene_time == pytest.approx(TIMELINE.hold) and seq.wall_time == pytest.approx(TIMELINE.hold + 4.0)


def test_clock_never_runs_backwards() -> None:
    seq = IntroSequencer()
    seq.advance(5.0)
    seq.advance(2.0)
    assert seq.wall_time == pytest.approx(5.0)


def test_press_then_ready_raises_start_reveal_finished_once_each_in_order() -> None:
    seq = _to_awaiting()
    now = TIMELINE.hold + 1.0
    assert seq.press_start(now)
    seq.mark_ready()
    events = _run(seq, now, now + TIMELINE.fade + 0.5)
    assert [e for _, e in events] == [Event.START, Event.REVEAL, Event.FINISHED]
    assert seq.phase is Phase.DONE and seq.opacity == 0.0


def test_start_is_raised_on_the_tick_after_the_press_and_the_fade_lasts_the_full_fade() -> None:
    seq = _to_awaiting()
    seq.mark_ready()
    now = TIMELINE.hold + 2.0
    seq.press_start(now)
    events = dict((e, t) for t, e in _run(seq, now, now + 5.0))
    assert events[Event.START] - now <= _TICK
    assert events[Event.REVEAL] - events[Event.START] <= 2 * _TICK
    assert events[Event.FINISHED] - events[Event.REVEAL] >= TIMELINE.fade


def test_the_simulator_start_may_block_inside_the_slot_without_swallowing_the_fade() -> None:
    """START's slot starts the simulator and may take seconds; the fade must still run afterwards."""
    seq = _to_awaiting()
    t0 = TIMELINE.hold + 1.0
    seq.press_start(t0)
    assert seq.advance(t0 + _TICK) == [Event.START]
    seq.mark_ready()  # the slot returned 4 s later by the wall clock
    later = t0 + 4.0
    assert seq.advance(later) == [Event.REVEAL]
    assert seq.opacity == pytest.approx(1.0)
    assert seq.advance(later + TIMELINE.fade / 2.0) == []
    assert seq.opacity == pytest.approx(0.5, abs=0.02)
    assert seq.advance(later + TIMELINE.fade + 0.01) == [Event.FINISHED]


def test_a_slow_simulator_start_keeps_the_splash_up_and_busy() -> None:
    seq = _to_awaiting()
    t0 = TIMELINE.hold + 1.0
    seq.press_start(t0)
    events = _run(seq, t0, t0 + 120.0)
    assert [e for _, e in events] == [Event.START]
    assert seq.phase is Phase.STARTING and seq.busy and seq.opacity == 1.0
    seq.mark_ready()
    assert [e for _, e in _run(seq, t0 + 121.0, t0 + 122.0)][:1] == [Event.REVEAL]


def test_a_console_ready_before_the_press_reveals_straight_after_it() -> None:
    seq = IntroSequencer()
    seq.mark_ready()  # built while the intro played
    _run(seq, 0.0, TIMELINE.hold + 1.0)
    assert seq.phase is Phase.AWAITING  # ready alone never ends the show
    now = TIMELINE.hold + 2.0
    seq.press_start(now)
    assert [e for _, e in _run(seq, now, now + 3 * _TICK)] == [Event.START, Event.REVEAL]


def test_opacity_never_rises_while_fading() -> None:
    seq = _to_awaiting()
    seq.mark_ready()
    now = TIMELINE.hold + 1.0
    seq.press_start(now)
    last = 1.0
    for _ in range(400):
        seq.advance(now)
        assert seq.opacity <= last + 1e-12
        last = seq.opacity
        if seq.phase is Phase.DONE:
            break
        now += _TICK
    assert seq.phase is Phase.DONE and last == 0.0


def test_a_press_before_the_button_is_on_screen_is_refused() -> None:
    seq = IntroSequencer()
    seq.advance(2.0)
    assert not seq.press_start(2.0)
    assert seq.phase is Phase.PLAYING
    assert _run(seq, 2.0, TIMELINE.hold - 0.1) == []


def test_a_second_press_does_not_start_the_simulator_twice() -> None:
    seq = _to_awaiting()
    now = TIMELINE.hold + 1.0
    assert seq.press_start(now)
    assert not seq.press_start(now + 0.01)
    assert not seq.press_start(now + 5.0)
    seq.mark_ready()
    events = _run(seq, now, now + 3.0)
    assert [e for _, e in events].count(Event.START) == 1
    assert not seq.press_start(now + 9.0)


def test_skip_jumps_to_the_button_and_never_starts_the_simulator() -> None:
    seq = IntroSequencer()
    _run(seq, 0.0, 1.0)
    seq.skip(1.0)
    assert seq.skipped and seq.phase is Phase.AWAITING and seq.awaiting_start
    assert seq.scene_time == pytest.approx(TIMELINE.hold)
    assert _run(seq, 1.0, 60.0) == []
    assert seq.opacity == 1.0


def test_after_a_skip_the_button_still_starts_the_simulator() -> None:
    seq = IntroSequencer()
    seq.mark_ready()
    seq.skip(1.0)
    assert seq.press_start(1.5)
    assert [e for _, e in _run(seq, 1.5, 1.5 + 4 * _TICK)][:2] == [Event.START, Event.REVEAL]


def test_skip_is_inert_once_the_scene_is_over_or_the_plant_is_starting() -> None:
    seq = _to_awaiting()
    seq.skip(TIMELINE.hold + 2.0)
    assert not seq.skipped and seq.phase is Phase.AWAITING
    seq.press_start(TIMELINE.hold + 3.0)
    seq.skip(TIMELINE.hold + 4.0)
    assert seq.phase is Phase.STARTING


def test_busy_covers_the_working_and_fading_phases_only() -> None:
    seq = IntroSequencer()
    assert not seq.busy
    _run(seq, 0.0, TIMELINE.hold + 0.1)
    assert not seq.busy
    seq.press_start(TIMELINE.hold + 1.0)
    assert seq.busy
    seq.mark_ready()
    _run(seq, TIMELINE.hold + 1.0, TIMELINE.hold + 1.1)
    assert seq.phase is Phase.FADING and seq.busy
    _run(seq, TIMELINE.hold + 1.1, TIMELINE.hold + 3.0)
    assert seq.phase is Phase.DONE and not seq.busy
    assert seq.advance(TIMELINE.hold + 9.0) == []
