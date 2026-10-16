"""Henry's-law constants — the gas side of every liquor bubble point.

What this gives the plant model
-------------------------------
The back-pressure a liquor exerts. Multiply a species' Henry constant by its *activity*
(from the Extended UNIQUAC speciation) and you have its partial pressure over the liquid;
sum those over NH3, CO2, water and the four permanent gases and you have the bubble point
that sets a flash tank's temperature, a desorber's pressure and a condenser's vent rate.

Two families, on the same basis
-------------------------------
    NH3, CO2          Rumpf & Maurer (1993), as reproduced in Darde eqs 2.12-2.13.
                      These are the two volatiles the Extended UNIQUAC parameter set
                      actually speciates, so their Henry constants are the ones consistent
                      with the activity coefficients they multiply.
    N2, O2, CH4, H2   IAPWS Guideline G7-04 (2004).

Both are on the MOLE-FRACTION scale (k_H = lim f_2/x_2), so the six rows drop into the same
partial-pressure sum with no basis conversion.

Why G7-04 for the permanent gases and not a van 't Hoff fit
-----------------------------------------------------------
Permanent-gas solubility in water passes through a MINIMUM near 80-100 C and rises again
above it. A two-parameter van 't Hoff extrapolated from 25 C data has solubility falling
monotonically and is badly wrong by 183 C — the synthesis loop's own operating temperature.
G7-04's three-term form reproduces the turning point, which is the whole reason it exists.

    ln(k_H / p1*) = A/T_R + B (1 - T_R)^0.355 / T_R + C exp(1 - T_R) T_R^(-0.41)

with T_R = T/647.096 and p1* the vapour pressure of water on its own saturation line (taken
from the shared IAPWS-IF97 module, so there is one water line in the whole project).

Declared valid 273.15 K to within ~15 K of the water critical point — covering the whole
80-210 C envelope of the activity grid.

Validation (neither check circular)
-----------------------------------
  * At 25 C the G7-04 rows return 85 598 / 43 640 / 39 479 / 70 960 bar for N2 / O2 / CH4 /
    H2 against textbook mole-fraction values 86 500 / 44 000 / 41 300 / 71 200 — errors of
    1.0 %, 0.8 %, 4.4 %, 0.3 %.
  * Run for CO2, whose constants are in the SAME published table, G7-04 agrees with the
    independent Rumpf & Maurer correlation to 0.2 % at 25 C, 2.3 % at 140 C and 5.0 % at
    183 C. Two unrelated fits agreeing to 5 % at the synthesis temperature is what licenses
    the four inert rows AT that temperature, where this repository holds no direct datum.

The CO2 row is carried for exactly that cross-check and is **not** used for the CO2 partial
pressure — `henry_co2_MPa` is.

Ported from V1 `backend/props_nh3co2h2o.py` (Henry block). Numerically identical.
"""

from __future__ import annotations

import math

from ureasim.thermo import iapws
from ureasim.thermo.parameters import M_W


def henry_nh3_MPa(T: float) -> float:
    """Henry's constant for NH3 in water [MPa, mole-fraction scale]. Valid 273.15-433.15 K.

    Process utility
    ---------------
    Sets how hard ammonia wants to leave a liquor. This single correlation drives the LP
    absorber's uptake, the desorber's stripping duty and the ammonia partial pressure in
    every vacuum condenser vent.

    Equation (Darde eq. 2.12)
    -------------------------
        ln(k_H / (MPa.kg/mol)) = 3.932 - 1879.02/T - 355134.1/T^2
        H* = k_H / M_w                              (to the mole-fraction scale)
    """
    kH = math.exp(3.932 - 1879.02 / T - 355134.1 / (T * T))     # MPa . kg/mol
    return kH / M_W


def henry_co2_MPa(T: float) -> float:
    """Henry's constant for CO2 in water [MPa, mole-fraction scale]. Valid 273.15-473.15 K.

    Process utility
    ---------------
    The CO2 back-pressure over a carbamate liquor. Together with the R5 carbamate
    equilibrium it decides how much CO2 a recirculation stage releases when it is let down
    — which is the gas load that charges PT-323201 (see `units/recirc/column_pressure.py`).

    Equation (Darde eq. 2.13)
    -------------------------
        ln(k_H / (MPa.kg/mol)) = 192.876 - 9624.4/T - 28.749 ln(T) + 0.01441 T
        H* = k_H / M_w
    """
    kH = math.exp(192.876 - 9624.4 / T - 28.749 * math.log(T) + 0.01441 * T)
    return kH / M_W


# --------------------------------------------------------------------------------------
# Permanent gases — IAPWS G7-04
# --------------------------------------------------------------------------------------
#: species -> (A, B, C) of IAPWS Guideline G7-04 eq. 1.
HENRY_G704 = {
    "N2":  (-9.67578, 4.72162, 11.70585),
    "O2":  (-9.44833, 4.43822, 11.42005),
    "CH4": (-10.44708, 4.66491, 12.12986),
    "H2":  (-4.73284, 6.08954, 6.06066),
    "CO2": (-8.55445, 4.01195, 9.52345),      # cross-check row only — see the module docstring
}

#: Declared validity window of G7-04 [K].
G704_VALID_T_K = (273.15, 633.0)


def henry_inert_MPa(species: str, T: float) -> float:
    """Henry's constant of a permanent gas in water [MPa, mole-fraction scale], IAPWS G7-04.

    Process utility
    ---------------
    The synthesis loop carries N2, O2, CH4 and H2 as passivation air and CO2-feed inerts.
    Without solubility data they had to be treated as perfectly insoluble, which forced the
    flash service to refuse the whole loop. With these rows they generate real K-values, so
    inert accumulation — the mechanism behind the HV-322604 purge and the trainee's
    "loop is going soft" scenario — is modelled instead of scripted.

    Equation (G7-04 eq. 1)
    ----------------------
        ln(k_H / p1*) = A/T_R + B (1 - T_R)^0.355 / T_R + C exp(1 - T_R) T_R^(-0.41)
        T_R = T / 647.096,   p1* = IAPWS-IF97 water saturation pressure at T

    Raises
    ------
    KeyError
        For a species with no published row. A neighbour's constants are NOT substituted.
    """
    A, B, C = HENRY_G704[species]
    t_r = T / 647.096
    p1_MPa = iapws.psat_bara(T - 273.15) / 10.0
    return p1_MPa * math.exp(
        A / t_r
        + B * (1.0 - t_r) ** 0.355 / t_r
        + C * math.exp(1.0 - t_r) * t_r ** -0.41
    )


__all__ = [
    "henry_nh3_MPa",
    "henry_co2_MPa",
    "HENRY_G704",
    "G704_VALID_T_K",
    "henry_inert_MPa",
]
