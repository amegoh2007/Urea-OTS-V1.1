"""`core.node.stable_pressure_step` — V1's explicit step where it is monotone, the backward step
where it would ring (handoff B-51, decided 2026-10-09).

The node equations themselves are proved against V1 in `tests/equivalence/test_core_equivalence.py`.
"""

from __future__ import annotations

import math

import pytest

from ureasim.core.node import EXPLICIT_STEP_LIMIT, stable_pressure_step


def _linear(k_per_s: float, p_star: float):
    """dP/dt = -k (P - P*): a node relaxing towards P* on a pole of -k."""
    return lambda p: -k_per_s * (p - p_star)


def test_a_monotone_explicit_step_is_returned_to_the_bit():
    """dt . k = 0.5: forward Euler is monotone, so the step is P + f(P) . dt, exactly."""
    dpdt = _linear(5.0, 3.5)
    p, backward = stable_pressure_step(3.7, 0.1, dpdt, 0.1)
    assert backward is False
    assert p == 3.7 + dpdt(3.7) * 0.1


def test_a_stiff_step_takes_the_backward_step():
    """dt . k = 3: forward Euler would land at 3.5 - 2 . 0.2 and alternate, growing; the
    backward step lands on (P + dt k P*) / (1 + dt k), between the old pressure and P*."""
    dpdt = _linear(30.0, 3.5)
    p, backward = stable_pressure_step(3.7, 0.1, dpdt, 0.1)
    assert backward is True
    assert p == pytest.approx((3.7 + 3.0 * 3.5) / 4.0, abs=1e-12)
    assert 3.5 < p < 3.7


def test_the_switch_is_the_monotone_edge():
    """The limit is -1 on dt . df/dP: just inside it the explicit step, just past it the
    backward one."""
    assert EXPLICIT_STEP_LIMIT == -1.0
    assert stable_pressure_step(3.7, 0.1, _linear(9.9, 3.5), 0.1)[1] is False
    assert stable_pressure_step(3.7, 0.1, _linear(10.1, 3.5), 0.1)[1] is True


def test_a_stiff_node_settles_without_ringing():
    """dt . k = 3 for 50 ticks: every step moves towards P* and none crosses it."""
    dpdt = _linear(30.0, 3.5)
    p = 5.0
    for _ in range(50):
        p_new, _ = stable_pressure_step(p, 0.1, dpdt, 0.1)
        assert 3.5 <= p_new <= p
        p = p_new
    assert p == pytest.approx(3.5, abs=1e-12)


def test_an_overhead_line_knee_is_approached_from_above_without_overshoot():
    """A line whose flow follows sqrt(P - P_out) has an infinite slope at zero differential:
    with no generation the explicit step jumps below the receiver and stops the flow; the
    backward step closes on the receiver's pressure from above, to the Newton's rounding. The
    first explicit step would have landed at 2.97 bar a."""
    def dpdt(p):
        return -20.0 * math.sqrt(max(p - 3.5, 0.0))
    assert 3.6 + dpdt(3.6) * 0.1 == pytest.approx(2.968, abs=1e-3)
    p = 3.6
    for _ in range(200):
        p, _ = stable_pressure_step(p, 0.1, dpdt, 0.1)
        assert p >= 3.5 - 1e-6
    assert p == pytest.approx(3.5, abs=1e-3)


def test_the_floor_bounds_the_backward_step():
    """A node emptying towards a pressure below its floor stops on the floor."""
    p, backward = stable_pressure_step(0.2, 0.1, _linear(30.0, -1.0), 0.1)
    assert backward is True and p == pytest.approx(0.1, abs=1e-12)
