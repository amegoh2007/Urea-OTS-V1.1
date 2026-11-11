"""Numerical helpers shared by every layer above `thermo`.

Why this module exists
----------------------
V1 defines `clamp` **twice**, in `backend/main.py` and in `backend/consequence.py`, and the
two are *not* the same function. The difference only shows on a NaN, which is exactly the
input a collapsing plant produces, so the two forms are ported separately and named for
what they do rather than merged into one "tidier" version.

Nothing in here knows about the plant. It is arithmetic, and it is here so that the limiter
V1 used at a given call site can be reproduced without guessing which of the two it was.
"""

from __future__ import annotations

import math
from typing import Callable

__all__ = ["clamp", "clamp_preserving_nan", "is_finite_positive", "bracketed_root",
           "RootLedger", "ROOT_LEDGER", "SECONDS_PER_HOUR"]

#: One hour in seconds. Every flow in this engine is kg/h or kmol/h while every integration
#: step is in seconds, so this factor appears in almost every accumulation term.
SECONDS_PER_HOUR = 3600.0


def clamp(x: float, lo: float, hi: float) -> float:
    """Limit ``x`` to ``[lo, hi]``. **A NaN comes back as** ``hi``.

    Process utility
    ---------------
    This is V1's `main.py` limiter, and it guards operating envelopes: valve strokes to
    0-100 %, a controller output to its span, a vessel pressure to its PSV and vacuum
    brackets. §5.5 of the agent directives forbids widening any of them.

    The NaN behaviour is a consequence of Python's `min`/`max` rather than a decision:
    ``min(hi, nan)`` compares ``nan < hi``, which is false, so it returns ``hi``, and
    ``max(lo, hi)`` then returns ``hi``. A limiter that swallows a NaN into its upper bound
    is not obviously right, but it is what every V1 call site was tuned against, so it is
    ported unchanged and documented instead of fixed.
    """
    return max(lo, min(hi, x))


def clamp_preserving_nan(x: float, lo: float, hi: float) -> float:
    """Limit ``x`` to ``[lo, hi]``. **A NaN comes back as a NaN.**

    Process utility
    ---------------
    This is V1's `consequence.py` limiter. The consequence layer converts a deviation into
    a *rate* — a leak rate, a carry-over fraction, a crystallisation restriction — and there
    a NaN must stay visible rather than be silently pinned to the upper bound, which for a
    restriction fraction would read as "fully open" and hide the defect that produced it.

    Both comparisons against a NaN are false, so the value falls through unchanged.
    """
    return lo if x < lo else (hi if x > hi else x)


def is_finite_positive(x: float) -> bool:
    """True when ``x`` is a usable magnitude: finite and strictly greater than zero.

    Process utility
    ---------------
    Guards every division by a flow, an area or a heat-capacity rate. A stopped pump, a shut
    valve or an empty line legitimately gives zero, so the guard is a normal operating case
    and not an error path.
    """
    return math.isfinite(x) and x > 0.0


class RootLedger:
    """How many bracketed solves ran out of iterations with their bracket still open.

    Process utility
    ---------------
    A residual with a step in it — a thermo memo's bin edge (decision 163) — can hold a bracket
    open through every iteration, and the solve then returns its midpoint without saying so. The
    ledger counts each such return so the engine can publish it in its health (handoff A-37,
    decision 184). It is a diagnostic: nothing in the physics reads it, and the root returned is
    the same to the bit whether it counts or not.
    """

    def __init__(self) -> None:
        self.exhausted = 0


#: The process's one ledger; the engine reads its count, the solver adds to it.
ROOT_LEDGER = RootLedger()


def bracketed_root(fn: Callable[[float], float], lo: float, hi: float, f_lo: float, f_hi: float,
                   tol: float = 1e-12, max_iter: int = 80) -> float:
    """A root of ``fn`` inside ``[lo, hi]``, where ``f_lo`` and ``f_hi`` bracket it in sign.

    Process utility
    ---------------
    Solves an algebraic loop a unit closes within its own tick — a fraction that sets a state
    which in turn sets the fraction — where taking it across the tick would ring. The bracket
    keeps the answer inside its physical range; the Illinois variant of regula falsi converges
    in a handful of evaluations, each of which can be a whole unit model.

    Method
    ------
    False position on the bracket, the retained end's value halved whenever the same end is
    kept twice (Illinois), until the bracket is narrower than ``tol`` or ``fn`` is zero to it.
    A solve that runs out of iterations with the bracket still wider than ``tol`` returns the
    bracket's midpoint, as before, and adds one to `ROOT_LEDGER` (handoff A-37).
    """
    side = 0
    for _ in range(max_iter):
        if hi - lo <= tol:
            break
        x = hi - f_hi * (hi - lo) / (f_hi - f_lo) if f_hi != f_lo else 0.5 * (lo + hi)
        if not lo < x < hi:
            x = 0.5 * (lo + hi)
        f_x = fn(x)
        if abs(f_x) <= tol:
            return x
        if (f_x > 0.0) == (f_hi > 0.0):
            hi, f_hi = x, f_x
            if side == -1:          # the low end kept twice running
                f_lo *= 0.5
            side = -1
        else:
            lo, f_lo = x, f_x
            if side == 1:           # the high end kept twice running
                f_hi *= 0.5
            side = 1
    else:
        if hi - lo > tol:           # out of iterations, the bracket still open
            ROOT_LEDGER.exhausted += 1
    return 0.5 * (lo + hi)
