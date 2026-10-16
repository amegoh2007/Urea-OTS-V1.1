"""The tick: every unit stepped once, in the schedule's order, its arguments from its wiring.

What this is
------------
The engine's one physics step. A tick resolves each step's wiring against the plant state and the
results of the steps before it, runs the step, and when every unit has stepped writes the recycle
tears for the next tick and advances the clock (`PlantState.end_tick`) — V1's tear-write points,
sections 25 and 32 of ``step_sim``. Nothing a step read during the tick changes under it: a
``Tear`` is the frozen `TearState`, a later unit's ``State`` is as that unit left it, and the
clock moves only when the tick is committed.

The schedule is validated before the first tick (`Schedule.validate`), so a tick never reads the
future; the tick itself counts every unit's runs and refuses to commit one in which a unit did not
step exactly once. The step is fixed at 0.1 s (`Claude.md` §1 rule 10, handoff A-14): every tear
carries one step of delay, so a tick of any other length is refused.

Source: ``project.md`` §3.6 (the draft, 2026-09-27) and V1 ``backend/main.py`` ``step_sim``
(7269-11320), whose section order the plant's schedule reproduces (`ureasim.engine.plant`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ureasim.data.engine import DT_S
from ureasim.engine.schedule import (
    Boundary,
    Operator,
    Result,
    Schedule,
    ScheduleError,
    Source,
    State,
    Tear,
    lookup,
)
from ureasim.engine.state import PlantState

__all__ = ["TickReport", "Scheduler"]


@dataclass(frozen=True)
class TickReport:
    """What one tick ran: the tick it committed, every unit's result, and how often each stepped."""

    tick: int
    results: dict
    runs: dict


class Scheduler:
    """Steps a plant through its validated schedule, one fixed tick at a time."""

    def __init__(self, schedule: Schedule, plant: PlantState) -> None:
        self.schedule = schedule
        self.flowsheet = schedule.validate()
        self.plant = plant
        #: The last committed tick's results, by unit; empty before the first tick.
        self.results: dict = {}
        #: The recycle tears the last committed tick read (the plant's own now hold what it wrote),
        #: for the console packet's inflows V1 publishes as read (``m756_prev`` and its kin).
        self.tears_read = plant.tears

    def _resolve(self, src: Source, results: dict) -> Any:
        """The value a source stands for at this point of the tick."""
        if isinstance(src, Result):
            return lookup(results[src.unit], src.field)
        if isinstance(src, State):
            return lookup(self.plant.units[src.unit], src.field)
        if isinstance(src, Tear):
            return getattr(self.plant.tears, src.name)
        if isinstance(src, Operator):
            return self.plant.operator[src.tag]
        if isinstance(src, Boundary):
            return self.plant.boundary[src.name]
        raise ScheduleError(f"{src!r} is not a source")

    def tick(self, dt: float = DT_S) -> TickReport:
        """Advance the plant one physics step and commit it.

        Process utility
        ---------------
        The plant clock's one tick: each unit sees what V1's order lets it see — its upstream
        neighbours' outputs of this tick, its downstream neighbours' states of the tick before —
        and the recycles close one tick late, as on V1, so an exercise replays bit for bit.
        """
        if dt != DT_S:
            raise ValueError(f"the physics step is fixed at {DT_S} s (A-14); got {dt}")
        results: dict = {}
        runs = {unit: 0 for unit in self.schedule.order}
        for step in self.schedule.steps:
            args = {name: self._resolve(src, results) for name, src in step.wiring.items()}
            results[step.unit] = step.run(self.plant, args, dt)
            runs[step.unit] += 1
        if any(n != 1 for n in runs.values()):
            raise ScheduleError(f"a unit did not step exactly once: {runs}")
        writes = {name: lookup(results[src.unit], src.field)
                  for name, src in self.schedule.tear_writes.items()}
        read = self.plant.tears
        self.plant.end_tick(writes)
        self.results = results
        self.tears_read = read
        return TickReport(tick=self.plant.clock.tick, results=results, runs=runs)
