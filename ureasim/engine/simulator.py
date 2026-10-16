"""The fixed-step simulator: plant time paid out of the wall clock in whole 0.1 s steps.

What this is
------------
The loop that turns real time into plant time. Each pass the server makes owes the plant the
wall-clock time since the last pass times the pacing factor — 1 in SLOW, 60 in FAST — and the
simulator pays it in whole physics steps of exactly 0.1 s, carrying the remainder to the next
pass. The step never moves (decided 2026-09-27, handoff A-14; `Claude.md` §1 rule 10): every
recycle tear carries one step of delay, so a variable step would make every transient that
crosses a tear depend on machine load. SLOW and FAST run the identical sequence of steps; only
the number per real second changes, and an exercise replays bit for bit.

V1's ``sim_task`` integrates ``min(elapsed, 0.5) x speed`` in sub-steps of at most 0.25 s — a
step of whatever the event loop left, about 0.1 s on an idle machine and more under load. The
per-pass cap is kept; the variable step is not.

Equations
---------
    owed_ns += min(elapsed_ns, 0.5 s) . pacing           [integer nanoseconds: exact]
    steps    = owed_ns // 0.1 s,   owed_ns -= steps . 0.1 s

Source: V1 ``backend/main.py`` ``sim_task`` (12008-12035), ``DT``, ``SIM_SPEED``; the constants
in `ureasim.data.engine`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ureasim.data.engine import DT_NS, DT_S, MAX_PASS_NS, SIM_SPEED

__all__ = ["Simulator"]


@dataclass
class Simulator:
    """Pays wall-clock time, at a pacing, in whole fixed physics steps.

    ``step`` advances the plant by one physics step and is handed the step, always DT_S. A step
    that raises freezes the plant for the rest of the pass — the owed time is dropped, as V1
    drops it — and the fault is held for the server to report; the next pass tries again.
    """

    step: Callable[[float], None]
    pacing: str = "SLOW"
    #: Plant time owed and not yet paid [ns], always under one step after a pass.
    owed_ns: int = 0
    #: Steps run since the simulator was made.
    steps: int = 0
    #: The last step's exception, or None while the plant runs.
    fault: BaseException | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.set_pacing(self.pacing)

    def set_pacing(self, mode: str) -> None:
        """Change the pacing; the owed remainder carries over, so no step is lost or made."""
        if mode not in SIM_SPEED:
            raise ValueError(f"unknown pacing {mode!r}: one of {sorted(SIM_SPEED)}")
        self.pacing = mode

    def advance(self, elapsed_ns: int) -> int:
        """Owe the plant ``elapsed_ns`` of wall-clock time at the pacing; run the whole steps it
        buys. Returns the number of steps run on this pass.

        Process utility: the server calls this once per pass of its loop. A pass that comes
        late — a loaded machine — owes more and runs more steps, never larger ones, up to the
        0.5 s per pass V1 allows; past that the plant falls behind the wall clock.
        """
        if elapsed_ns < 0:
            raise ValueError("wall-clock time runs forward")
        self.owed_ns += min(elapsed_ns, MAX_PASS_NS) * SIM_SPEED[self.pacing]
        due, self.owed_ns = divmod(self.owed_ns, DT_NS)
        return self._run(due)

    def run(self, n_steps: int) -> int:
        """Run exactly ``n_steps`` physics steps, the wall clock aside: an exercise's replay, a
        settle, a test. Returns the steps run."""
        return self._run(n_steps)

    def _run(self, due: int) -> int:
        """Run up to ``due`` steps; a raising step stops the pass and drops what it still owed."""
        done = 0
        for _ in range(due):
            try:
                self.step(DT_S)
            except Exception as exc:  # noqa: BLE001 - any physics fault freezes the plant
                self.fault = exc
                self.owed_ns = 0
                return done
            self.fault = None
            done += 1
            self.steps += 1
        return done
