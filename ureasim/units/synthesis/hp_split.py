"""The anchored thermodynamic ratio every HP synthesis split runs on.

What this is for
----------------
Four units in the 322 loop — the stripper, the carbamate condenser, the reactor's vapour
disengagement and the scrubber — each own a component split that the licensor calibrated at
one operating point. Frozen, those vectors have a derivative of exactly zero: raising the loop
pressure or the shell steam would move temperatures and duties but not one mole of product,
which is wrong in a way a trainee would notice immediately.

This module is how they are allowed to move.

Why only a RATIO is ever used
-----------------------------
The Extended UNIQUAC parameter set is EXTRAPOLATED in the synthesis loop. Its activity table
is indexed in moles per kilogram of water and the HP loop has almost none, and it puts the
322R001 overflow's bubble pressure at about 40 bar a against a loop that runs at 144. So the
ABSOLUTE number is never used anywhere in this section.

What survives the extrapolation is the DERIVATIVE. A systematic offset in an activity
coefficient divides out of a ratio; a slope does not. So every split in the loop keeps the
licensor's calibrated vector and multiplies it by a ratio of the model to itself:

    alpha_live,i = alpha_PFD,i  x  [ K_i(live) / K_i(reference) ]

With the reference evaluated on the SAME composition as the live point, every argument of the
two calls is identical at the design state, the two K-values are the same float, and the ratio
is exactly 1.0 — by the arithmetic, not by a short-circuit and not within a tolerance.

Source
------
Ported from V1 ``backend/main.py``, the G-VLE-3 block and `_hp_k_ratio`.
"""

from __future__ import annotations

from ureasim.core.stream import mass_fractions_from_kmolh
from ureasim.thermo.service import k_ratio


def hp_k_ratio(feed_kmolh: dict, t_c: float, p_bara: float,
               t_ref_c: float, p_ref_bara: float) -> dict:
    """Per-species K-value ratio for an HP-loop stream, from its live molar feed.

    Process utility
    ---------------
    Turns an operator's action on the loop — opening the vent, raising the steam, letting the
    pressure drift — into movement of the component splits, which is what the trainee is
    meant to see. Without it the 322 loop is thermodynamically inert.

    Why the OVERALL feed and not the equilibrium liquid
    ----------------------------------------------------
    The composition handed to the service is the overall molar feed rather than a solved
    equilibrium liquid. That is what a first-pass flash uses anyway, and it is also why the
    choice is safe here: the same vector goes into the live call and the reference call, so a
    basis error is common to numerator and denominator and cancels in the ratio, exactly as
    the activity-coefficient offset does.

    Failure behaviour
    -----------------
    `k_ratio` bounds each species to [0.02, 50] and falls back to 1.0 — the licensor's own
    split — on any refusal, non-convergence or non-finite value. So an extreme transient
    degrades to the calibrated vector rather than freezing the tick or publishing a NaN. A
    training simulator that stops is worse than one that briefly runs on its design split.
    """
    return k_ratio(mass_fractions_from_kmolh(feed_kmolh), t_c, p_bara, t_ref_c, p_ref_bara)


__all__ = ["hp_k_ratio"]
