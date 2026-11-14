"""The operator's command set — V1's faceplate whitelist, its auxiliary pumps and its limits.

What this is
------------
The numbers and lists `ureasim.engine.command` applies an operator's command with: which modes
each unit-323 / 328 / 324 faceplate offers, the running / standby auxiliary pumps the overlays
toggle, and the limits V1's handler clamps an entry to. Every one is V1's, with its line.

Source: V1 ``backend/main.py`` ``R323_CTRL_MODES`` (11328-11384), ``AUX_PUMPS`` and the roster
(11387-11388, 7143-7146), ``handle_cmd`` (11413-11787).
"""

from __future__ import annotations

from types import MappingProxyType

__all__ = [
    "FACEPLATE_MODES", "AUX_PUMP_SEEDS", "RUN_STATE_PAIRS", "TRIP_21_HAND_SWITCHES", "RATIO_SP_MIN",
    "RATIO_SP_MAX",
    "STEAM_SP_MAX_BARA", "CPL_MAX_FACTOR", "FIC_329409_SP_MAX_FACTOR",
    "TIC_329005_SP_MIN_C", "EXT_OVERRIDE_TAG",
]

#: Each inline faceplate's tag and the modes it offers. A cascade slave adds CAS; a standby
#: spare is MAN only. V1 keys the dictionary with underscores; the DCS tag is dashed. Source: V1
#: ``R323_CTRL_MODES``, but FIC-328406, which a decided cascade made a slave (B-50).
FACEPLATE_MODES = MappingProxyType({
    # 323-1 (recirculation and pre-evaporation)
    "TIC-323007": ("MAN", "AUTO"),
    "PIC-329202": ("MAN", "AUTO", "CAS"),
    "LIC-323501": ("MAN", "AUTO"),
    "LIC-323505": ("MAN", "AUTO"),
    "TIC-323012": ("MAN", "AUTO"),
    "PIC-329208": ("MAN", "AUTO", "CAS"),
    "LIC-323507": ("MAN", "AUTO"),
    "FIC-324401": ("MAN", "AUTO", "CAS"),
    # 323-2 (LP recirculation)
    "PIC-323202": ("MAN", "AUTO"),
    "PIC-323203": ("MAN", "AUTO"),
    "LIC-323502": ("MAN", "AUTO"),
    "SIC-323901": ("MAN", "AUTO", "CAS"),
    "SIC-323902": ("MAN",),
    "LIC-323503": ("MAN", "AUTO"),
    "TIC-323013": ("MAN", "AUTO", "CAS"),
    "FIC-323401": ("MAN", "AUTO"),
    "FIC-323402": ("MAN", "AUTO"),
    "FIC-328405": ("MAN", "AUTO"),
    "FIC-323418": ("MAN", "AUTO"),
    # 328-1 (desorption and hydrolysis)
    "LIC-328501": ("MAN", "AUTO"),
    "PIC-328202": ("MAN", "AUTO"),
    "TIC-328002": ("MAN", "AUTO"),
    "FIC-328404": ("MAN", "AUTO", "CAS"),
    "FIC-329402": ("MAN", "AUTO", "CAS"),
    "PIC-328203": ("MAN", "AUTO"),
    "FFIC-329401": ("MAN", "AUTO"),
    "FIC-329401": ("MAN", "AUTO", "CAS"),
    "TIC-328008": ("MAN", "AUTO"),
    "TIC-328012": ("MAN", "AUTO"),
    "LIC-328503": ("MAN", "AUTO"),
    "LIC-328504": ("MAN", "AUTO"),
    "LIC-328505": ("MAN", "AUTO"),
    "FIC-328402": ("MAN", "AUTO"),
    # V1's MAN alone; LIC-328505's slave in cascade on the plant (decided 2026-09-30, B-50), so the
    # faceplate offers what the decided structure needs (2026-10-03).
    "FIC-328406": ("MAN", "AUTO", "CAS"),
    # 328-2 (LP absorber)
    "PIC-322201": ("MAN", "AUTO"),
    "LIC-322502": ("MAN", "AUTO"),
    # 324-1, 324-1b and 335 (evaporation and finishing)
    "TIC-324001": ("MAN", "AUTO"),
    "PIC-329203": ("MAN", "AUTO", "CAS"),
    "PIC-324202": ("MAN", "AUTO"),
    "TIC-324002": ("MAN", "AUTO"),
    "PIC-329212": ("MAN", "AUTO", "CAS"),
    "PIC-324203": ("MAN", "AUTO"),
    "LIC-324501": ("MAN", "AUTO"),
    "PIC-335201": ("MAN", "AUTO", "CAS"),
    "FFIC-335406": ("MAN", "AUTO"),
    "FIC-335405": ("MAN", "AUTO", "CAS"),
})

#: The auxiliary running / standby pump pairs the 323-2 and 328 overlays toggle, as V1 seeds them:
#: the A machine running, the B machine its spare, both in AUTO. Only 322P002's pair moves the
#: process (either machine running feeds 328D003's wash); the others are status. Source: V1
#: ``State.aux_pumps``.
AUX_PUMP_SEEDS = MappingProxyType({
    "323P001A": (True, "AUTO"), "323P001B": (False, "AUTO"),
    "322P002A": (True, "AUTO"), "322P002B": (False, "AUTO"),
    "328P001A": (True, "AUTO"), "328P001B": (False, "AUTO"),
    "328P003A": (True, "AUTO"), "328P003B": (False, "AUTO"),
    # Decided 2026-11-14 (decision 227, handoff A-41): the pairs session 111 gives a run state,
    # seeded as V1 seeds its own pairs. Source: the process engineer's instruction I-4.
    "335P002A": (True, "AUTO"), "335P002B": (False, "AUTO"),
    "329P003A": (True, "AUTO"), "329P003B": (False, "AUTO"),
})

#: The pairs whose flow follows their run state: the engine holds the pair's flag, True while
#: either machine runs, and the pair's unit reads it (decision 227; 322P002 as V1 holds it).
#: Source: V1 ``State.aux_pumps`` for 322P002; the process engineer's instruction I-4 for the rest.
RUN_STATE_PAIRS = (
    "322P002",
    "335P002",
    "329P003",
)

#: AC4 PC21.5.1's hand switches on TRIP_21_2_FLAG1 (UD-MR-G00-FF-0004 page 20), maintained,
#: released at the seed: HS-321634, HS-323604 and HS-322606 bypass the HP ammonia pumps', 323P001's
#: and the CO2's inputs for a start-up; HS-321603 and HS-321604, turned, take the flag's inputs 5
#: and 6 away. The loop summaries (UD-MR-321/322/323-EC-0001, read 2026-10-16) type the three
#: bypasses as control-room keyswitches and HS-321603 / HS-321604 as emergency shut-off switches,
#: control-room and local, each held until released — all five maintained, as built.
TRIP_21_HAND_SWITCHES = ("321634", "323604", "322606", "321603", "321604")

#: The ammonia-to-CO2 ratio set point's limits [-]. Source: V1 ``ratio_set``.
RATIO_SP_MIN, RATIO_SP_MAX = 2.0, 5.0

#: The steam headers' set points' ceiling [bar a]. Source: V1 ``pic329204_set`` and its siblings.
STEAM_SP_MAX_BARA = 25.0

#: FT-322404's condensate entry ceiling as a multiple of its design [-]. Source: V1 ``cpl_set``.
CPL_MAX_FACTOR = 2.0

#: FIC-329409's set point ceiling as a multiple of the design circulation [-], and TIC-329005's
#: set point floor [deg C]. Source: V1 ``fic_set``, ``tic_set``.
FIC_329409_SP_MAX_FACTOR = 2.0
TIC_329005_SP_MIN_C = 20.0

#: The operator entry holding 321P002 A/B's EXT. OVERRIDE run signal (V1 ``ext_override``: stored
#: and displayed; nothing in the process reads it).
EXT_OVERRIDE_TAG = "321P002-EXT-OVERRIDE"
