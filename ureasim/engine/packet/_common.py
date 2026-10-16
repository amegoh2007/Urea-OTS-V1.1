"""What every block of the console packet is built from, and V1's number formats.

`Tick` is the plant after a tick with that tick's results: the units' objects (their state), the
controllers, the operator's positions, each unit's result by tag, and the recycle tears it read.
The helpers reproduce V1's packet idioms — ``round(x, n)``, the ``{"pv", "sp", "op", "mode"}``
faceplate dictionary, a flow in t/h from kg/h — so each block reads like the dictionary literal it
ports.

Source: V1 ``backend/main.py`` ``step_sim``'s return statement (10445-11320).
"""

from __future__ import annotations

from typing import Any, Mapping

from ureasim.control.process_loop import ProcessLoop
from ureasim.core.stream import MW_COMP
from ureasim.engine.state import PlantState

__all__ = ["Tick", "th", "faceplate", "comp_pct", "MW_COMP"]


class Tick:
    """The plant after one tick, as the packet reads it."""

    def __init__(self, plant: PlantState, results: Mapping[str, Any], tears_read: Any) -> None:
        self.plant = plant
        self.results = results
        #: The recycle tears the tick read (``Scheduler.tears_read``); the plant's hold the next's.
        self.tears_read = tears_read
        self.units = plant.units
        self.loops = plant.loops
        self.operator = plant.operator

    def r(self, unit: str) -> Any:
        """The unit's result on this tick."""
        return self.results[unit]

    def loop(self, tag: str) -> ProcessLoop | None:
        """An inline faceplate's loop by its tag (``"TIC-323007"``), wherever its unit keeps it;
        None when the model has no such loop."""
        return _faceplates_of(self.plant).get(tag)


#: The last plant's faceplates, by tag: a walk of the whole plant, made once per plant object (a
#: reset or a restored exercise is a new one).
_FACEPLATES: list = [None, {}]


def _faceplates_of(plant: PlantState) -> dict:
    if _FACEPLATES[0] is not plant:
        from ureasim.engine.command import faceplates
        _FACEPLATES[:] = [plant, faceplates(plant)]
    return _FACEPLATES[1]


def th(kgh: float, n: int = 2) -> float:
    """A flow in t/h from kg/h, rounded as V1 rounds it: ``round(m / 1000.0, n)``."""
    return round(kgh / 1000.0, n)


def faceplate(loop: Any, pv: int = 1, op: int = 1, *, prefix: str = "") -> dict:
    """V1's faceplate dictionary: ``{"pv", "sp", "op", "mode"}``, the PV and SP to ``pv`` places
    and the output to ``op``. ``prefix`` reads a loop V1 kept as fields of a larger object
    (``fic_pv`` on the tempered-water loop). A loop the model does not have keeps V1's keys, each
    None, so every path a console binds still resolves."""
    if loop is None:
        return {"pv": None, "sp": None, "op": None, "mode": None}
    get = lambda f: getattr(loop, prefix + f)   # noqa: E731
    return {"pv": round(get("pv"), pv), "sp": round(get("sp"), pv), "op": round(get("op"), op),
            "mode": get("mode")}


def comp_pct(comp: Mapping[str, float], n: int) -> dict:
    """A composition already in per cent, rounded per species over V1's species list."""
    return {k: round(comp[k], n) for k in MW_COMP}
