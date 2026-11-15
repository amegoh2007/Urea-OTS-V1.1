"""Handoff B-20's switch on the V1 side of the unit 323 liquor-stage equivalences.

What this is
------------
Decided 2026-10-10 (handoff B-20; As-Built Part LXVI): PFD 314, 323C003's bottoms, is closed on its
urea against the drain — the 8.16 kg/h of PFD 208's urea the table's row leaves unaccounted, which
V1's back-solve sends overhead as an apparent volatility its runtime then zeroes, leaves by the
drain, water giving way — and PFD 319 is closed the same way against the closed 314
(`thermo.urea_liquor.close_urea_on_drain`). Everything V1 anchors on the two rows follows them:
323C003's and 323F004's back-solves, bubble points and volatilities, the column's heat capacity and
density, the letdown's vapour pressure and the stages' seeds.

How the switch is made
----------------------
V1 derives every one of those from its two module-level rows ``W_S314`` and ``W_S319``. `names`
drops them from the names a harness lifts and `seed` hands them the decided rows, so `v1_loader.lift`
never runs V1's assignments of them and V1's own statements derive the rest: every line executed is
V1's. A harness lifted without the switch is V1 verbatim, for the tests that assert the departure
both ways.
"""

from __future__ import annotations

from ureasim.data.unit_323 import W_S314, W_S319

#: The V1 constants the switch replaces.
NAMES = ("W_S314", "W_S319")


def names(v1_names) -> list:
    """`v1_names` without V1's two rows, so the lifter takes them from the seed."""
    return [n for n in v1_names if n not in NAMES]


def seed(v1_seed: dict) -> dict:
    """`v1_seed` with the decided rows."""
    return {**v1_seed, "W_S314": dict(W_S314), "W_S319": dict(W_S319)}


__all__ = ["NAMES", "names", "seed"]
