"""The engine's clock constants — the physics step, the pacing modes, the catch-up cap, the replay age.

What this is
------------
The few numbers that decide how plant time advances against the wall clock. The step is an
architectural law (`Claude.md` §1 rule 10, handoff A-14): every recycle tear carries one step of
delay, so the step must never move, or a transient would depend on machine load.

Source
------
V1 ``backend/main.py``: ``DT`` (line 277), ``STEP_CAP`` (286), and ``sim_task``'s per-pass cap on
the wall-clock elapsed (12013). The pacing modes replace V1's ``SIM_SPEED`` (285), SLOW and FAST, with
x1 to x10 in steps of one (2026-11-23, the process engineer's instruction; `project.md` decision 321).
The replay age is the rewrite's own (handoff A-28, decision 172).
"""

from __future__ import annotations

__all__ = ["DT_S", "DT_NS", "SIM_SPEED", "DEFAULT_PACING", "MAX_PASS_S", "MAX_PASS_NS", "STEP_CAP_S",
           "SNAPSHOT_REPLAY_MAX_AGE_S"]

#: The physics step [s]: V1's ``DT``, the step of V1's design pin and of every equivalence test.
#: Fixed (decided 2026-09-27, handoff A-14).
DT_S = 0.1

#: The same step in integer nanoseconds, so the simulator owes and pays plant time exactly.
DT_NS = 100_000_000

#: Plant seconds advanced per wall-clock second in each pacing mode, x1 (real time) to x10 in
#: steps of one, held as integers so the owed time is integer arithmetic. V1's ``SIM_SPEED`` was
#: ``{"SLOW": 1.0, "FAST": 60.0}``; the instructor's panel offers the ten factors instead
#: (decision 321). A loaded machine that cannot run the steps a factor owes falls behind the wall
#: clock (``MAX_PASS_S``); the step itself never changes.
SIM_SPEED = {f"x{n}": n for n in range(1, 11)}

#: The pacing a session starts at: real time, V1's SLOW.
DEFAULT_PACING = "x1"

#: The most wall-clock time one pass may owe [s]: V1's ``min(now - last_t, 0.5)``. A stalled
#: machine catches up with more steps, up to this much per pass; past it, plant time falls
#: behind the wall clock rather than racing to make it up.
MAX_PASS_S = 0.5
MAX_PASS_NS = 500_000_000

#: V1's largest physical sub-step [s], the stability bound of its fastest flow loops. Not an
#: operating step here: the engine steps DT_S, always.
STEP_CAP_S = 0.25

#: The oldest packet the console server replays to a console that connects [s of wall time]: ten
#: publish passes of DT_S. A running or frozen engine publishes every pass, so its last packet is
#: at most a pass old; one older comes from an engine that has stopped publishing, and replaying it
#: would show the engine's last values as live after every watchdog blank (`ureasim.net.server`).
#: Source: handoff A-28 option (a), decided by the process engineer 2026-11-06 (`project.md`
#: decision 172); "about 1 s" is the option's own figure.
SNAPSHOT_REPLAY_MAX_AGE_S = 1.0
