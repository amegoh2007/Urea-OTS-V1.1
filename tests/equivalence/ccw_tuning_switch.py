"""Decision 10's class on FIC-329409 and TIC-329005, on the V1 side of the synthesis-loop equivalence.

What this is
------------
Applied 2026-10-07, once Uhde's loop summaries gave the two transmitters' spans (handoff, Open data
gaps; As-Built §LXI.9): FIC-329409 runs the DCS table's 0.60 and 250 s on FT-329409's 0-500 m3/h,
TIC-329005 the table's 1.50 and 300 s on TT-329005's 0-200 C (`data.unit_329_ccw`), where V1 runs
0.08 %/(t/h) and 6 s, and 1.0 %/K and 15 s.

How the switch is made
----------------------
V1 writes the four as module-level constants of ``main.py``, read by the 322E003 block of
``step_sim`` the harness transcribes. `names` drops them from the names a harness lifts and `seed`
hands them the decided values, so every line executed or transcribed is V1's on the decided tunings.
`V1_NAMES` are the four, for a harness that lifts V1 verbatim to assert the departure both ways.
"""

from __future__ import annotations

from ureasim.data import unit_329_ccw as ccw

#: V1's names for the two loops' gains and integral times, and the decided values.
DECIDED = {
    "FIC_329409_KC": ccw.FIC_329409_KC, "FIC_329409_TI": ccw.FIC_329409_TI_S,
    "TIC_329005_KC": ccw.TIC_329005_KC, "TIC_329005_TI": ccw.TIC_329005_TI_S,
}
V1_NAMES = list(DECIDED)


def names(v1_names) -> list:
    """`v1_names` without the four, so the lifter takes them from the seed."""
    return [n for n in v1_names if n not in DECIDED]


def seed(v1_seed: dict) -> dict:
    """`v1_seed` with the decided tunings."""
    return {**v1_seed, **DECIDED}


__all__ = ["DECIDED", "V1_NAMES", "names", "seed"]
