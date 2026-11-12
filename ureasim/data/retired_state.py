"""Retired state — attributes a saved exercise may still carry that the present model no longer has.

What this is
------------
An exercise saved before a piece of the model was removed still holds that piece's state. The
snapshot reader drops the attributes named here before it rebuilds an object, so the save loads
and its shape matches the present model's; every other difference is still refused (`engine.
snapshot`). An entry is removed only when no save in use can hold it.

Source
------
Trip 22.2, the simulator's synthesis high-high pressure trip (``SynthesisTrips.i_22_2``), removed
2026-11-12: no plant document draws it (``project.md`` decision 189; the recheck in
``D:\\Work\\reports\\Trip_22_2_recheck_s105``). Its record held only primitives and nothing else in
a save refers to it.
"""

from __future__ import annotations

from types import MappingProxyType

__all__ = ["RETIRED_ATTRIBUTES"]

#: Attributes dropped on load, by the class path a snapshot names (``module:QualifiedName``).
#: source = decision 189 (trip 22.2 removed, 2026-11-12).
RETIRED_ATTRIBUTES = MappingProxyType({
    "ureasim.engine.plant.synthesis_loop:SynthesisTrips": ("i_22_2",),
})
