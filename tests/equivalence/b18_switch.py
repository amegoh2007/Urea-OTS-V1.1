"""Handoff B-18's switch on the V1 side of the HV-322604 and 322E003 equivalences.

What this is
------------
Decided 2026-10-10 (handoff B-18, closed; As-Built Part LXVI): HV-322604's characteristic is
anchored at the 72 % stroke the vendor's trim passes the licensor's normal purge at, where V1
anchors it at 50 % with no source. V1 reads the anchor in three places, all from the one
module-level constant ``SCRUB_HIC604_DES_PCT``: the valve law's design opening, 322E003's two
vent-opening deviation terms, and the seed of HIC-322604 itself.

How the switch is made
----------------------
`names` drops the constant from the names a harness lifts and `seed` hands it the decided value,
so `v1_loader.lift` never runs V1's assignment of it and every line V1 executes reads 72 %. A
harness lifted without the switch is V1 verbatim, for the tests that assert the departure both
ways.
"""

from __future__ import annotations

from ureasim.data.unit_322e003 import HIC604_DES_PCT as DECIDED_HIC604_DES_PCT

#: The V1 constant the switch replaces.
NAME = "SCRUB_HIC604_DES_PCT"


def names(v1_names) -> list:
    """`v1_names` without V1's anchor, so the lifter takes it from the seed."""
    return [n for n in v1_names if n != NAME]


def seed(v1_seed: dict) -> dict:
    """`v1_seed` with the decided anchor."""
    return {**v1_seed, NAME: DECIDED_HIC604_DES_PCT}


__all__ = ["NAME", "DECIDED_HIC604_DES_PCT", "names", "seed"]
