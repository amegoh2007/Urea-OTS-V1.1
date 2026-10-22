"""The flowsheet graph — which unit feeds which, and in what order they may be solved.

What this is, and what it is NOT
--------------------------------
It is the *topology*: a set of units, the connections between them, and the recycles that
have been explicitly declared as one-tick tears. It computes a legal evaluation order and
refuses an illegal one.

It contains **no physics whatsoever**. It does not call a unit, it does not hold a state,
and it does not know what a reactor is. V1 has no counterpart to this module, because V1's
`step_sim()` encoded its evaluation order implicitly — in the order the 4,100 lines happen
to be written. That works exactly until someone inserts a block in the wrong place.

Process utility
---------------
A urea synthesis loop is a recycle, so its flowsheet is cyclic by construction: the
322E003 scrubber overflow returns to the 322F001 ejector, which feeds the 322E002
condenser, which feeds the 322R001 reactor, whose off-gas returns to 322E003. A cyclic
graph has no evaluation order, so every simulator of a recycle plant must CUT the loop
somewhere — the "tear" — and accept the torn value from the previous tick.

That cut is a modelling decision with real consequences. It sets which quantity carries a
one-tick delay, and therefore where a fast transient is slightly late. Making the cuts
explicit and checkable is the entire point of this module:

  * a cycle that HAS a declared tear is fine — the tear is the cut, and the delay is
    documented in `docs/step_sim_dataflow.md` section 2;
  * a cycle that does NOT have one is a defect, and `evaluation_order` raises rather than
    picking an arbitrary order that would silently work on a developer's machine and be
    wrong on the plant.

The 39 tears V1 actually uses are listed in `docs/step_sim_dataflow.md` section 2, and each
one becomes a `Tear` registered here as its unit is ported.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Unit", "Connection", "Tear", "Flowsheet", "CyclicFlowsheetError"]


class CyclicFlowsheetError(ValueError):
    """A recycle exists in the graph with no declared tear to cut it.

    Raised rather than resolved. Choosing a cut automatically would hide the modelling
    decision that the choice represents.
    """


@dataclass(frozen=True)
class Unit:
    """One piece of equipment, or one closely coupled group that is solved together.

    ``tag`` is the plant identifier verbatim (``322E002``, ``323C003``) because that is what
    the operator, the datasheet and the P&ID all call it. ``section`` is the plant unit
    number it is reported under (``322``, ``323``, ...).
    """

    tag: str
    name: str
    section: str


@dataclass(frozen=True)
class Connection:
    """A stream from one unit to another.

    ``route`` optionally names an entry in `ureasim.data.process_routes`, which is what
    gives the connection its plug-flow dead time. A connection with no route is a short
    nozzle-to-nozzle tie where the transit time is below the integration step and modelling
    it would add state without adding behaviour.
    """

    name: str
    source: str
    destination: str
    route: str | None = None


@dataclass(frozen=True)
class Tear:
    """A recycle cut: a value written on one tick and read on the next.

    Process utility
    ---------------
    ``state_attribute`` is the engine-state field that carries the value across the tick
    boundary. ``reason`` records WHY this edge was chosen as the cut rather than another
    one in the same loop — usually because the value is the slowest-moving quantity in the
    cycle, so a one-tick delay on it is the least visible.
    """

    state_attribute: str
    written_by: str
    read_by: tuple[str, ...]
    reason: str


class Flowsheet:
    """A registry of units, connections and tears, with a checked evaluation order."""

    def __init__(self) -> None:
        self._units: dict[str, Unit] = {}
        self._connections: list[Connection] = []
        self._tears: list[Tear] = []

    # ---------------------------------------------------------------- registration ----
    def add_unit(self, unit: Unit) -> Unit:
        """Register one unit. A duplicate tag is a defect, not an update."""
        if unit.tag in self._units:
            raise ValueError(f"unit {unit.tag} is already in the flowsheet")
        self._units[unit.tag] = unit
        return unit

    def connect(self, connection: Connection) -> Connection:
        """Register one stream. Both ends must already be units."""
        for end in (connection.source, connection.destination):
            if end not in self._units:
                raise ValueError(
                    f"connection {connection.name!r} names unknown unit {end!r}")
        self._connections.append(connection)
        return connection

    def tear(self, tear: Tear) -> Tear:
        """Declare a recycle cut. The writer and every reader must already be units."""
        for end in (tear.written_by, *tear.read_by):
            if end not in self._units:
                raise ValueError(f"tear {tear.state_attribute!r} names unknown unit {end!r}")
        self._tears.append(tear)
        return tear

    # ------------------------------------------------------------------- inspection ----
    @property
    def units(self) -> tuple[Unit, ...]:
        return tuple(self._units.values())

    @property
    def connections(self) -> tuple[Connection, ...]:
        return tuple(self._connections)

    @property
    def tears(self) -> tuple[Tear, ...]:
        return tuple(self._tears)

    def units_in_section(self, section: str) -> tuple[Unit, ...]:
        """Every unit reported under one plant section."""
        return tuple(u for u in self._units.values() if u.section == section)

    # --------------------------------------------------------------------- ordering ----
    def _torn_edges(self) -> set[tuple[str, str]]:
        """Directed edges removed from the graph because a tear carries them.

        A tear from ``written_by`` to each of its ``read_by`` units is exactly the edge the
        one-tick delay replaces, so it is deleted before the ordering is computed.
        """
        return {(t.written_by, reader) for t in self._tears for reader in t.read_by}

    def evaluation_order(self) -> tuple[str, ...]:
        """Unit tags in a legal solve order, upstream first.

        Kahn's algorithm on the connection graph with the torn edges removed. Ties are
        broken by registration order, so the result is deterministic — two runs of the same
        flowsheet give the same order, which matters because the floating-point result of a
        tick depends on the order its terms are summed in.

        Raises `CyclicFlowsheetError` naming the units still in a cycle when the tears do
        not cut every loop.
        """
        torn = self._torn_edges()
        successors: dict[str, list[str]] = {tag: [] for tag in self._units}
        indegree: dict[str, int] = {tag: 0 for tag in self._units}
        for c in self._connections:
            if (c.source, c.destination) in torn or c.source == c.destination:
                continue
            successors[c.source].append(c.destination)
            indegree[c.destination] += 1

        ready = [tag for tag in self._units if indegree[tag] == 0]
        order: list[str] = []
        while ready:
            tag = ready.pop(0)
            order.append(tag)
            for nxt in successors[tag]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    ready.append(nxt)

        if len(order) != len(self._units):
            stuck = sorted(tag for tag in self._units if tag not in set(order))
            raise CyclicFlowsheetError(
                "recycle with no declared tear; these units cannot be ordered: "
                + ", ".join(stuck)
            )
        return tuple(order)

    def upstream_of(self, tag: str) -> tuple[str, ...]:
        """Units that feed ``tag`` directly, torn edges included.

        Torn edges are included here deliberately: for reading the flowsheet, a recycle IS
        a connection. It is only the ORDERING that has to pretend otherwise.
        """
        return tuple(sorted({c.source for c in self._connections if c.destination == tag}))

    def downstream_of(self, tag: str) -> tuple[str, ...]:
        """Units that ``tag`` feeds directly, torn edges included."""
        return tuple(sorted({c.destination for c in self._connections if c.source == tag}))
