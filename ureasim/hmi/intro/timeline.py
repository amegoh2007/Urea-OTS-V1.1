"""Easing curves and time windows of the start-up intro.

Plant equipment modelled: none (presentation only).
Reference document: none.
Equations: the cubic and back easing curves below, each a function of normalised progress u in [0, 1].

Process utility
---------------
An intro that moves at constant speed looks mechanical; one that eases looks deliberate. Every
element of the scene asks "how far along am I?" through ``window`` and shapes the answer with one of
these curves, so all timing lives in ``ureasim/data/intro.py`` and none in the drawing code.
"""

from __future__ import annotations

from collections.abc import Callable


def clamp01(x: float) -> float:
    """Pin ``x`` to [0, 1]; progress never runs backwards or past its end."""
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def lerp(a: float, b: float, u: float) -> float:
    """Linear blend from ``a`` (u = 0) to ``b`` (u = 1)."""
    return a + (b - a) * u


def window(t: float, start: float, end: float) -> float:
    """Progress of an element that runs from ``start`` to ``end``: 0 before it, 1 after it."""
    if end <= start:
        return 1.0 if t >= end else 0.0
    return clamp01((t - start) / (end - start))


def ease_out_cubic(u: float) -> float:
    """Fast start, soft landing: 1 - (1 - u)^3. The default for things that appear."""
    v = 1.0 - clamp01(u)
    return 1.0 - v * v * v


def ease_in_out_cubic(u: float) -> float:
    """Slow start and end, quick middle. The default for things that travel."""
    u = clamp01(u)
    if u < 0.5:
        return 4.0 * u * u * u
    v = -2.0 * u + 2.0
    return 1.0 - v * v * v / 2.0


def ease_out_back(u: float, overshoot: float = 1.70158) -> float:
    """Overshoots 1 slightly and settles back: a small 'pop' for dots and the emblem."""
    v = clamp01(u) - 1.0
    c3 = overshoot + 1.0
    return 1.0 + c3 * v * v * v + overshoot * v * v


def invert_monotonic(f: Callable[[float], float], y: float, *, iterations: int = 48) -> float:
    """Solve f(u) = y for u in [0, 1] by bisection, f non-decreasing on [0, 1].

    Used to ask when a travelling front reaches a fixed point: the node of a ribbon is lit at the
    instant the eased front passes its position.
    """
    lo, hi = 0.0, 1.0
    for _ in range(iterations):
        mid = (lo + hi) / 2.0
        if f(mid) < y:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0
