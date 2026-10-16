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

__all__ = ["clamp", "clamp_preserving_nan", "is_finite_positive",
           "SECONDS_PER_HOUR"]

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
