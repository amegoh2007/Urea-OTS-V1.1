"""Solid ammonium carbamate's saturation over a dry NH3-CO2 gas.

What this gives the plant model
-------------------------------
The line a dry ammonia-carbon dioxide gas crosses when it starts to lay solid ammonium carbamate on
a cold pipe wall, and how much it lays down there: 2 NH3 + CO2 -> NH2COONH4(s) until the gas's
p_NH3^2 p_CO2 falls to the solid's equilibrium constant. `condensing_letdown` deposits the solid
from a letdown's gas the liquor leaves dry (its method step 5, handoff B-79 (b), decided
2026-10-14) and solves the outlet temperature with it on the enthalpy balance.

Equations
---------
    Kp = (4/27) P_diss^3,   log10 P_diss[bar] = 8.2697 - 2741.9 / T[K]
    S(s) = ln(p_NH3(s)^2 p_CO2(s) / Kp(T))      the gas left after s mol of solid per mol of gas
    s* : S(s*) = 0, by bisection on [0, min(y_NH3 / 2, y_CO2)]

P_diss the dissociation pressure over the solid at its own stoichiometry, its gas 2/3 NH3 and
1/3 CO2. Ideal-gas partial pressures, the absorber beds' own basis.

Moved out of `condensing_letdown` unchanged (2026-10-23, the housekeeping split);
`condensing_letdown` re-exports every name.

Source: E. P. Egan Jr., J. E. Potts Jr. and G. D. Potts, "Dissociation pressure of ammonium
carbamate", Ind. Eng. Chem. 38 (1946) 454-456; admitted by the process engineer on 2026-10-14
(handoff B-79).
"""

from __future__ import annotations

import math

#: Solid ammonium carbamate's dissociation pressure [bar] at temperature T [K], over the solid at its
#: own stoichiometry, 2 NH3 + CO2: log10 P = A - B / T. Source: E. P. Egan Jr., J. E. Potts Jr. and
#: G. D. Potts, "Dissociation pressure of ammonium carbamate", Ind. Eng. Chem. 38 (1946) 454-456
#: (1 atm at 58.7 C, 89 Torr at 25 C); admitted by the process engineer on 2026-10-14 (handoff B-79).
CARBAMATE_DISSOC_A = 8.2697
CARBAMATE_DISSOC_B_K = 2741.9

#: Bisection budgets of the solid's two solves: the deposit at a temperature, the temperature.
SOLID_ITERS = 80


def carbamate_kp_bar3(t_c: float) -> float:
    """Solid ammonium carbamate's equilibrium constant, p_NH3^2 p_CO2 [bar^3], at ``t_c``.

    Process utility
    ---------------
    The line a dry NH3-CO2 gas crosses when it starts to lay solid carbamate on a cold pipe wall —
    the fouling HV-322604's purge line is traced against.

    Equation
    --------
        Kp = (4/27) P^3,   log10 P[bar] = 8.2697 - 2741.9 / T[K]

    P the dissociation pressure over the solid, its gas 2/3 NH3 and 1/3 CO2 (Egan, Potts and Potts).
    """
    p = 10.0 ** (CARBAMATE_DISSOC_A - CARBAMATE_DISSOC_B_K / (t_c + 273.15))
    return 4.0 / 27.0 * p ** 3


def _less_deposit(y: dict, s: float) -> dict:
    """The gas left after ``s`` moles of solid per mole of gas, as mole fractions."""
    v = 1.0 - 3.0 * s
    out = dict(y)
    out["NH3"] = y["NH3"] - 2.0 * s
    out["CO2"] = y["CO2"] - s
    return {k: max(val, 0.0) / v for k, val in out.items()}


def _supersaturation(y: dict, s: float, t_c: float, p_bara: float) -> float:
    """ln(p_NH3^2 p_CO2 / Kp) of the gas left after ``s`` deposited [-]; positive deposits more."""
    g = _less_deposit(y, s)
    if g["NH3"] <= 0.0 or g["CO2"] <= 0.0:
        return -math.inf
    return (2.0 * math.log(g["NH3"] * p_bara) + math.log(g["CO2"] * p_bara)
            - math.log(carbamate_kp_bar3(t_c)))


def _deposit_at(y: dict, t_c: float, p_bara: float) -> float:
    """The solid a gas lays down at ``t_c`` to stand on its saturation [mol per mol of gas]."""
    if _supersaturation(y, 0.0, t_c, p_bara) <= 0.0:
        return 0.0
    lo, hi = 0.0, min(y["NH3"] / 2.0, y["CO2"])
    for _ in range(SOLID_ITERS):
        mid = 0.5 * (lo + hi)
        if _supersaturation(y, mid, t_c, p_bara) > 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)

__all__ = ["CARBAMATE_DISSOC_A", "CARBAMATE_DISSOC_B_K", "SOLID_ITERS", "carbamate_kp_bar3"]
