"""Retired and added state — what a saved exercise may carry that the present model no longer has,
and what it may lack that the present model added.

What this is
------------
An exercise saved before a piece of the model was removed still holds that piece's state. The
snapshot reader drops the attributes named here before it rebuilds an object, so the save loads
and its shape matches the present model's; every other difference is still refused (`engine.
snapshot`). A save made before a piece of state was added lacks it: the reader fills each added
operator entry and attribute named here from the present model's fresh plant, at the same path, and
hands a retired boundary value to the engine's adopter (decided 2026-11-14, decision 226). An entry
is removed only when no save in use can hold it.

Source
------
Trip 22.2, the simulator's synthesis high-high pressure trip (``SynthesisTrips.i_22_2``), removed
2026-11-12: no plant document draws it (``project.md`` decision 189; the recheck in
``D:\\Work\\reports\\Trip_22_2_recheck_s105``). Its record held only primitives and nothing else in
a save refers to it.

The 335 melt header, computed since 2026-11-14 (decision 224): PIC-335201's boundary pressure
retired, the granulator's header valves and HIC-335602 added to what the operator holds, and stage
2's header state and PIC-335201's loop added to its unit and its loops (decision 226). LV-324501A's
positioner, added to the header's state on 2026-11-15 (decision 236). AC4 PC35's trips, added as a
unit of their own with their four override switches on 2026-11-15 (decision 228).
"""

from __future__ import annotations

from types import MappingProxyType

__all__ = ["RETIRED_ATTRIBUTES", "RETIRED_BOUNDARY", "ADDED_OPERATOR", "ADDED_ATTRIBUTES",
           "ADDED_UNITS"]

#: Attributes dropped on load, by the class path a snapshot names (``module:QualifiedName``).
#: source = decision 189 (trip 22.2 removed, 2026-11-12).
RETIRED_ATTRIBUTES = MappingProxyType({
    "ureasim.engine.plant.synthesis_loop:SynthesisTrips": ("i_22_2",),
})

#: Boundary values the plant now computes, dropped on load and handed to the engine's adopter
#: (`engine.snapshot`). source = decision 224 (the melt header computed, 2026-11-14).
RETIRED_BOUNDARY = ("PIC-335201.barg",)

#: Operator entries a save made before they existed lacks, seeded from the present model.
#: source = decision 224 (the granulator's header valves and HIC-335602, 2026-11-14) and
#: decision 227 (each pump pair given a run state: its flag and its two machines) and decision 212
#: (322P002's field-set delivery, 2026-11-15) and decision 228 (PC35's override switches).
ADDED_OPERATOR = ("GRANULATION-HEADERS", "HIC-335602", "335P002", "335P002A", "335P002B", "329P003",
                  "329P003A", "329P003B", "328P007", "328P007A", "328P007B", "328P006", "328P006A",
                  "328P006B", "328P002", "328P002A", "328P002B", "323P008", "323P008A", "323P008B",
                  "323P003", "323P003A", "323P003B", "335P001", "335P001A", "335P001B",
                  "322P002-DELIVERY", "HS-335201A", "HS-335201B", "HS-335602", "HS-335620")

#: Units a save made before they existed lacks, seeded from the present model's fresh plant.
#: source = decision 228 (AC4 PC35's trips 35.1, 35.3 and 35.4, 2026-11-15).
ADDED_UNITS = ("335-TRIPS",)

#: Attributes a save made before they existed lacks, by the class path a snapshot names, filled
#: from the present model's object at the same path. source = decision 224 (2026-11-14),
#: decision 236 (LV-324501A's positioner, 2026-11-15; the engine then opens the valve at the stroke
#: that passes the save's drain, decision 238) and decision 217 (the four low-level stops, 2026-11-15).
ADDED_ATTRIBUTES = MappingProxyType({
    "ureasim.units.evaporation.second_evaporator:SecondEvaporatorLoops": ("header",),
    "ureasim.units.evaporation.second_evaporator:SecondEvaporator": ("ac4_header", "header",
                                                                     "l2_stop", "p001_stopped"),
    "ureasim.units.finishing.melt_header:MeltHeader": ("lv_a_position_pct",),
    "ureasim.units.desorption.reflux_drum:RefluxDrum": ("l2_stop", "p002_stopped"),
    "ureasim.units.desorption.first_desorber:FirstDesorber": ("l2_stop", "p006_stopped"),
    "ureasim.units.desorption.second_desorber:SecondDesorber": ("l2_stop", "p007_stopped"),
})
