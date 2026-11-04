"""Tests of ureasim/hmi/intro/timeline.py: the easing curves and the time window."""

from __future__ import annotations

import pytest

from ureasim.hmi.intro.timeline import (
    clamp01,
    ease_in_out_cubic,
    ease_out_back,
    ease_out_cubic,
    invert_monotonic,
    lerp,
    window,
)

_STEPS = [i / 200.0 for i in range(201)]


def test_clamp_and_lerp() -> None:
    assert clamp01(-3.0) == 0.0 and clamp01(0.25) == 0.25 and clamp01(9.0) == 1.0
    assert lerp(10.0, 20.0, 0.0) == 10.0 and lerp(10.0, 20.0, 1.0) == 20.0 and lerp(10.0, 20.0, 0.25) == 12.5


def test_window_is_zero_before_one_after_and_linear_between() -> None:
    assert window(0.9, 1.0, 3.0) == 0.0
    assert window(1.0, 1.0, 3.0) == 0.0
    assert window(2.0, 1.0, 3.0) == pytest.approx(0.5)
    assert window(3.0, 1.0, 3.0) == 1.0
    assert window(9.0, 1.0, 3.0) == 1.0


def test_degenerate_window_steps_at_its_end() -> None:
    assert window(1.9, 2.0, 2.0) == 0.0
    assert window(2.0, 2.0, 2.0) == 1.0


@pytest.mark.parametrize("ease", [ease_out_cubic, ease_in_out_cubic, ease_out_back])
def test_easings_start_at_zero_and_end_at_one(ease) -> None:
    assert ease(0.0) == pytest.approx(0.0, abs=1e-12)
    assert ease(1.0) == pytest.approx(1.0, abs=1e-12)


@pytest.mark.parametrize("ease", [ease_out_cubic, ease_in_out_cubic])
def test_cubic_easings_never_run_backwards(ease) -> None:
    values = [ease(u) for u in _STEPS]
    assert all(b >= a for a, b in zip(values, values[1:]))
    assert all(0.0 <= v <= 1.0 for v in values)


def test_ease_out_back_overshoots_then_settles() -> None:
    values = [ease_out_back(u) for u in _STEPS]
    assert max(values) > 1.0
    assert max(values) < 1.15
    assert values[-1] == pytest.approx(1.0)


def test_easings_clamp_their_input() -> None:
    assert ease_out_cubic(-1.0) == 0.0 and ease_out_cubic(2.0) == 1.0
    assert ease_in_out_cubic(-1.0) == 0.0 and ease_in_out_cubic(2.0) == 1.0


def test_invert_monotonic_round_trips() -> None:
    for u in (0.0, 0.1, 0.37, 0.5, 0.82, 1.0):
        y = ease_in_out_cubic(u)
        assert ease_in_out_cubic(invert_monotonic(ease_in_out_cubic, y)) == pytest.approx(y, abs=1e-9)
