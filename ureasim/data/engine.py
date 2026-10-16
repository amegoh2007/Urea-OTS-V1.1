"""The engine's clock constants — the physics step, the pacing modes, the catch-up cap.

What this is
------------
The few numbers that decide how plant time advances against the wall clock. The step is an
architectural law (`Claude.md` §1 rule 10, handoff A-14): every recycle tear carries one step of
delay, so the step must never move, or a transient would depend on machine load.

Source
------
V1 ``backend/main.py``: ``DT`` (line 277), ``SIM_SPEED`` (285), ``STEP_CAP`` (286), and
``sim_task``'s per-pass cap on the wall-clock elapsed (12013).
"""

from __future__ import annotations

__all__ = ["DT_S", "DT_NS", "SIM_SPEED", "MAX_PASS_S", "MAX_PASS_NS", "STEP_CAP_S"]

#: The physics step [s]: V1's ``DT``, the step of V1's design pin and of every equivalence test.
#: Fixed (decided 2026-09-27, handoff A-14).
DT_S = 0.1

#: The same step in integer nanoseconds, so the simulator owes and pays plant time exactly.
DT_NS = 100_000_000

#: Plant seconds advanced per wall-clock second in each pacing mode: V1's ``SIM_SPEED``,
#: ``{"SLOW": 1.0, "FAST": 60.0}``, held as integers so the owed time is integer arithmetic.
SIM_SPEED = {"SLOW": 1, "FAST": 60}

#: The most wall-clock time one pass may owe [s]: V1's ``min(now - last_t, 0.5)``. A stalled
#: machine catches up with more steps, up to this much per pass; past it, plant time falls
#: behind the wall clock rather than racing to make it up.
MAX_PASS_S = 0.5
MAX_PASS_NS = 500_000_000

#: V1's largest physical sub-step [s], the stability bound of its fastest flow loops. Not an
#: operating step here: the engine steps DT_S, always.
STEP_CAP_S = 0.25
