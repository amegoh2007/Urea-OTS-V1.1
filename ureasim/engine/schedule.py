"""The plant's schedule: V1's section order as checked data (``project.md`` §3.6).

What this is
------------
The order the plant's units step in on a tick, and where every argument each of them takes comes
from. V1's ``step_sim`` is one function of 4051 lines whose order is the order its blocks happen to
be written in; a value a block reads before its writer has run that tick is last tick's, and nothing
says so. Here the order is an ordered tuple of steps, one per unit, and each step's wiring names the
source of every argument. There are exactly five kinds of source:

=============================  ==================================================================
``Result(unit, field)``        a same-tick output of an EARLIER step
``State(unit, field)``         a unit's own state as it stands when the reader steps: an earlier
                               unit's after its step this tick; a LATER unit's as it stood at the
                               end of the tick before — a one-tick tear, and it must be declared
``Tear(name)``                 a `TearState` field, written by its producer at the end of the tick
                               before (handoff A-10)
``Operator(tag)``              a hand valve, a hand switch or a set point the operator holds
``Boundary(name)``             a battery-limit or boundary value the plant does not compute
=============================  ==================================================================

The schedule is checked before the engine runs (`Schedule.validate`). Every unit steps exactly once
on a tick; a ``Result`` comes from an earlier step; a ``State`` read of a later unit and every
``Tear`` is declared, with the reason the cut is taken there; and the order is a topological order
of the plant's flowsheet once its declared tears are cut — the graph `core.flowsheet` refuses when a
recycle has no tear. A wiring that reads the future without a declared tear stops the engine at
start-up instead of surfacing as a late transient.

Why the order is V1's and not a sort
------------------------------------
Any topological order of the torn graph is legal, but the set of tears is itself fixed by the order:
a unit that reads a neighbour stepped later reads last tick's value. V1's order is physics — every
one-tick delay in the plant follows from it — so the schedule REPRODUCES it, and the check proves it
is a legal evaluation order of the torn graph (decision 8, handoff A-10).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Union

from ureasim.core.flowsheet import Connection, Flowsheet
from ureasim.core.flowsheet import Tear as FlowsheetTear
from ureasim.core.flowsheet import Unit
from ureasim.engine.state import TEAR_NAMES

__all__ = [
    "Result", "State", "Tear", "Operator", "Boundary", "Source", "Step", "DeclaredTear",
    "Schedule", "ScheduleError", "lookup",
]


class ScheduleError(ValueError):
    """The schedule is not a legal tick: a unit twice, a read of the future, an undeclared tear."""


def lookup(obj: Any, path: str) -> Any:
    """``obj``'s value at a dotted ``path``: an attribute, or a key where the value is a mapping
    (``"streams_kgh.719"``, ``"route.recycle_kgh"``)."""
    for part in path.split("."):
        obj = obj[part] if isinstance(obj, Mapping) else getattr(obj, part)
    return obj


@dataclass(frozen=True)
class Result:
    """A same-tick output of an earlier step: ``unit``'s result object's ``field`` (a dotted path,
    `lookup`)."""

    unit: str
    field: str


@dataclass(frozen=True)
class State:
    """A unit's own state attribute, read when the reader steps."""

    unit: str
    field: str


@dataclass(frozen=True)
class Tear:
    """A `TearState` field: its producer's output on the tick before."""

    name: str


@dataclass(frozen=True)
class Operator:
    """A hand valve, hand switch or set point held in the plant state."""

    tag: str


@dataclass(frozen=True)
class Boundary:
    """A boundary value the plant does not compute."""

    name: str


Source = Union[Result, State, Tear, Operator, Boundary]


@dataclass(frozen=True)
class Step:
    """One unit's step on a tick.

    ``run(plant, args, dt)`` advances the unit and returns its result; ``args`` maps each name in
    ``wiring`` to the value its source resolved to. ``section`` is the plant unit the tag reports
    under (``"323"``), ``v1_section`` the block of V1's ``step_sim`` it reproduces.
    """

    unit: str
    name: str
    section: str
    v1_section: int
    wiring: Mapping[str, Source]
    run: Callable[[Any, Mapping[str, Any], float], Any]


@dataclass(frozen=True)
class DeclaredTear:
    """A read across the tick boundary, and why the cut is taken there.

    ``source`` is a ``State`` of a unit stepped later than ``reader``, or a ``Tear``.
    """

    source: Union[State, Tear]
    reader: str
    reason: str


def _key(source: Union[State, Tear]) -> str:
    return (f"{source.unit}.{source.field}" if isinstance(source, State)
            else f"tear.{source.name}")


@dataclass(frozen=True)
class Schedule:
    """The tick as data: the steps in order, the declared tears, the tear writes."""

    steps: tuple[Step, ...]
    tears: tuple[DeclaredTear, ...] = ()
    #: Each `TearState` field and the producer output written into it at the end of the tick.
    tear_writes: Mapping[str, Result] = field(default_factory=dict)

    @property
    def order(self) -> tuple[str, ...]:
        """The units in the order they step."""
        return tuple(s.unit for s in self.steps)

    def validate(self) -> Flowsheet:
        """Check the schedule and return the plant's flowsheet with its tears cut.

        Raises `ScheduleError` naming the first defect: a unit scheduled twice; a ``Result`` from
        a step not yet run; a ``State`` of an unknown unit or of the reader itself; a ``State`` of
        a later unit, or a ``Tear``, with no declared tear; a declared tear nothing reads; a
        `TearState` field read with no writer, written by an unscheduled unit, or written and
        never read. A field nothing reads or writes holds its design seed. Then the flowsheet
        built from the wiring must order (`Flowsheet.evaluation_order`), and every connection the
        tears do not cut must run forward in the schedule.
        """
        index: dict[str, int] = {}
        for i, step in enumerate(self.steps):
            if step.unit in index:
                raise ScheduleError(f"unit {step.unit} is scheduled twice: it must step exactly "
                                    "once a tick")
            index[step.unit] = i

        unknown = set(self.tear_writes) - set(TEAR_NAMES)
        if unknown:
            raise ScheduleError(f"not a recycle tear: {sorted(unknown)}")
        for name, src in self.tear_writes.items():
            if src.unit not in index:
                raise ScheduleError(f"tear {name} is written by {src.unit}, which is not scheduled")

        declared = {(_key(t.source), t.reader): t for t in self.tears}
        used: set = set()
        fs = Flowsheet()
        for step in self.steps:
            fs.add_unit(Unit(step.unit, step.name, step.section))
        edges: set = set()
        torn: list = []
        for i, step in enumerate(self.steps):
            for arg, src in step.wiring.items():
                where = f"{step.unit}.{arg}"
                if isinstance(src, Result):
                    j = index.get(src.unit)
                    if j is None:
                        raise ScheduleError(f"{where} reads the result of {src.unit}, which is not "
                                            "scheduled")
                    if j >= i:
                        raise ScheduleError(f"{where} reads {src.unit}'s result before it is made "
                                            "this tick")
                    edges.add((src.unit, step.unit))
                elif isinstance(src, State):
                    j = index.get(src.unit)
                    if j is None:
                        raise ScheduleError(f"{where} reads the state of {src.unit}, which is not "
                                            "scheduled")
                    if j == i:
                        raise ScheduleError(f"{where} reads its own unit's state through the "
                                            "wiring; a unit's own state is its own")
                    if j < i:
                        edges.add((src.unit, step.unit))
                    else:
                        key = (_key(src), step.unit)
                        if key not in declared:
                            raise ScheduleError(
                                f"{where} reads {src.unit}.{src.field}, which steps later this "
                                "tick, with no declared tear")
                        used.add(key)
                        torn.append((src.unit, step.unit, declared[key]))
                elif isinstance(src, Tear):
                    if src.name not in self.tear_writes:
                        raise ScheduleError(f"{where} reads tear {src.name}, which has no writer")
                    key = (_key(src), step.unit)
                    if key not in declared:
                        raise ScheduleError(f"{where} reads tear {src.name} with no declared tear")
                    used.add(key)
                    torn.append((self.tear_writes[src.name].unit, step.unit, declared[key]))
                elif not isinstance(src, (Operator, Boundary)):
                    raise ScheduleError(f"{where}: {src!r} is not a source")

        stale = [f"{k[0]} -> {k[1]}" for k in declared if k not in used]
        if stale:
            raise ScheduleError(f"declared tears nothing reads: {stale}")
        unread = sorted(set(self.tear_writes) - {k[0][len("tear."):] for k in used
                                                  if k[0].startswith("tear.")})
        if unread:
            raise ScheduleError(f"recycle tears written and never read: {unread}")

        cut = set()
        for writer, reader, t in torn:
            fs.connect(Connection(_key(t.source), writer, reader))
            fs.tear(FlowsheetTear(_key(t.source), writer, (reader,), t.reason))
            cut.add((writer, reader))
        for src, dst in sorted(edges):
            fs.connect(Connection(f"{src}->{dst}", src, dst))
        fs.evaluation_order()
        for src, dst in edges:
            if (src, dst) not in cut and index[src] >= index[dst]:
                raise ScheduleError(f"{src} -> {dst} runs backwards without a tear")
        return fs
