"""Handoffs B-6's and B-7's switch on the V1 side of the equivalences that lift `main.py`.

What this is
------------
Decided 2026-10-07 (handoffs B-6 and B-7, closed; As-Built §LXI.4): the engine converts gauge to
absolute on the standard atmosphere, 1.01325 bar, and every static head is on standard gravity,
9.80665 m/s2 (`core.units_of_measure.ATM_BARA`, ``G_ACC``). V1's ``main.py`` writes
``P_ATM_BAR = 1.013`` and ``G = 9.81``, and derives from them the SV-32201 set pressure
(``SYN_PSV_SET_BARA``), 322F001's design suction and differential (``_EJ_P_SUCT_DES``,
``_EJ_DP_DES_PA``) and, inside ``step_sim``, the unit-321 suction head and subcooling.

How the switch is made
----------------------
`names` drops the two constants from the names a harness lifts and `seed` hands them the decided
values, so `v1_loader.lift` never runs V1's assignments of them and V1's own statements derive
everything else from the standard values: every line executed is V1's. A harness lifted without
the switch is V1 verbatim, for the tests that assert the departure both ways.
"""

from __future__ import annotations

from ureasim.core.units_of_measure import ATM_BARA, G_ACC

#: V1's names for the two constants, and the decided values the switch seeds them with.
DECIDED = {"P_ATM_BAR": ATM_BARA, "G": G_ACC}


def names(v1_names) -> list:
    """`v1_names` without V1's two constants, so the lifter takes them from the seed."""
    return [n for n in v1_names if n not in DECIDED]


def seed(v1_seed: dict) -> dict:
    """`v1_seed` with the decided atmosphere and gravity."""
    return {**v1_seed, **DECIDED}


__all__ = ["DECIDED", "names", "seed"]
