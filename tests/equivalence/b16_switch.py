"""Handoff B-16's switch on the V1 side of the 322E003 equivalences.

What this is
------------
Decided 2026-10-07 (handoff B-16, closed; As-Built §LXI.3): TT-322002, 322E003's overflow at
design, is pinned on the 165 C that PFD stream 206 and the plant's DCS both give, where V1 pins
178.8 C — the 322F001 ejector's suction pseudo-temperature, which carries the carbamate's heat of
mixing. Everything V1 anchors on the pin follows it: the shell-side conductance back-solved on the
design approach, the condensing temperature's Clausius-Clapeyron anchor and the thermal driving
force's denominator. The ejector keeps its own 178.8 C (`EJ_T_SUCTION_C`, a separate literal in
V1), so its discharge balance does not move.

How the switch is made
----------------------
V1 derives every one of those from the one module-level constant ``SCRUB_OVERFLOW_T_C``. `names`
drops it from the names a harness lifts and `seed` hands it the decided value, so `v1_loader.lift`
never runs V1's assignment of it and V1's own statements derive the conductance, the anchor and the
driving force from 165 C: every line executed is V1's. A harness lifted without the switch is V1
verbatim, for the tests that assert the departure both ways.
"""

from __future__ import annotations

from ureasim.data.unit_322e003 import OVERFLOW_T_DES_C as DECIDED_OVERFLOW_T_C

#: The V1 constant the switch replaces.
NAME = "SCRUB_OVERFLOW_T_C"


def names(v1_names) -> list:
    """`v1_names` without V1's pin, so the lifter takes it from the seed."""
    return [n for n in v1_names if n != NAME]


def seed(v1_seed: dict) -> dict:
    """`v1_seed` with the decided pin."""
    return {**v1_seed, NAME: DECIDED_OVERFLOW_T_C}


__all__ = ["NAME", "DECIDED_OVERFLOW_T_C", "names", "seed"]
