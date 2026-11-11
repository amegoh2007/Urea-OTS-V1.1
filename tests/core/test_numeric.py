"""Behaviour of `ureasim.core.numeric`: the two clamps and the bracketed root."""

from __future__ import annotations

import math

import pytest

from ureasim.core.numeric import ROOT_LEDGER, bracketed_root, clamp, clamp_preserving_nan


def test_the_two_clamps_differ_only_on_a_nan():
    assert clamp(5.0, 0.0, 1.0) == clamp_preserving_nan(5.0, 0.0, 1.0) == 1.0
    assert clamp(-5.0, 0.0, 1.0) == clamp_preserving_nan(-5.0, 0.0, 1.0) == 0.0
    assert clamp(math.nan, 0.0, 1.0) == 1.0
    assert math.isnan(clamp_preserving_nan(math.nan, 0.0, 1.0))


def test_the_bracketed_root_converges_in_a_handful_of_evaluations():
    """0.3 - x^3 on [0, 1]: the cube root of 0.3 to 1e-12 in ten evaluations."""
    calls = []

    def fn(x: float) -> float:
        calls.append(x)
        return 0.3 - x ** 3

    root = bracketed_root(fn, 0.0, 1.0, fn(0.0), fn(1.0))
    assert root == pytest.approx(0.3 ** (1.0 / 3.0), abs=1e-12)
    assert len(calls) <= 12


def test_the_bracketed_root_handles_a_falling_function_and_a_kink():
    """A falling function with a kink, as the saturation fraction's excess has: f(P_bub(f)) - f."""
    def fn(x: float) -> float:
        return min(1.0, 1.6 - 1.2 * x) - x

    root = bracketed_root(fn, 0.0, 1.0, fn(0.0), fn(1.0), tol=1e-10)
    assert root == pytest.approx(1.6 / 2.2, abs=1e-9)


def test_a_solve_that_runs_out_of_iterations_is_counted_and_returns_as_before():
    """A-37 (decision 184): a residual with a step in it, the shape a thermo memo's bin edge gives
    (decision 163), holds the bracket open through all 80 iterations; the solve returns the bracket's
    midpoint, as it always did, and the ledger counts it once. A solve that converges is not
    counted."""
    def step(x: float) -> float:
        return 1.0e6 if x >= 0.5 else -1.0

    before = ROOT_LEDGER.exhausted
    root = bracketed_root(step, 0.0, 1.0, step(0.0), step(1.0))
    assert ROOT_LEDGER.exhausted == before + 1
    assert root == pytest.approx(0.5, abs=0.01) and root != 0.5
    bracketed_root(lambda x: 0.3 - x ** 3, 0.0, 1.0, 0.3, -0.7)
    assert ROOT_LEDGER.exhausted == before + 1
