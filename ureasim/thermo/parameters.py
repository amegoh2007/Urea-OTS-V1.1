"""Extended UNIQUAC parameter tables for the NH3-CO2-H2O system — data only, verbatim.

What this module is
-------------------
The *transcription layer*. Every number here is copied from a named open publication and
nothing is fitted, regressed, interpolated or guessed. It is kept separate from the code
that uses it so that a reviewer can check the transcription against the source without
reading a line of algebra, and so that a change to a solver can never be mistaken for a
change to a parameter.

Why Extended UNIQUAC for this plant
-----------------------------------
The liquid phase of a urea plant's LP section is a concentrated aqueous electrolyte:
ammonia and CO2 do not simply dissolve, they react to ammonium, bicarbonate, carbonate and
carbamate, and it is the *speciated* free NH3 and free CO2 that set every bubble point,
every desorber duty and every absorber uptake. Four reasons this model and not another:

1. Envelope. Validated 0-150 C, 1-100 bar, to 100 molal NH3 — the exact envelope of the
   Unit-328 desorption train, the Unit-324 vacuum condensers and the LP absorbers.
2. It speciates. A model that lumps total NH3 cannot represent a desorber at all.
3. It supplies excess enthalpy and heat capacity from the *same* parameter set, so the
   energy balance and the phase equilibrium cannot drift apart.
4. Its parameters are published in the open literature and are transcribable verbatim.

Provenance
----------
    u0_ij, uT_ij, r_i, q_i, NH2COO- Cp, fitted formation energies
        V. Darde, PhD thesis "CO2 capture using aqueous ammonia", DTU 2011,
        Tables 2-2, 2-3, 2-4, 2-5, 2-6.
        Published as Darde, van Well, Stenby, Thomsen, Ind. Eng. Chem. Res. 49 (2010) 12663.
    Base-species Helgeson Cp coefficients
        K. Thomsen, PhD thesis "Aqueous Electrolytes - Model Parameters and Process
        Simulation", DTU 1997, Table 5.7.
    dGf, dHf at 298.15 K
        CODATA / NIST aqueous convention (as the model itself uses; Darde sec. 2.2.2).
    Cp0(NH3 aq) = 72.04, Cp0(CO2 aq) = 238.05 J/mol/K
        Correa, Thomsen, Fosbol, Fuel 335 (2023) 126863, Table 1 (open access).
        Entered in the CONSTANT-Cp limit (a = Cp0, b = c = 0), exactly as NH4+ is treated.

Independent cross-check
-----------------------
The r and q transcription was checked against a second, unrelated transcription
(`References/Resolving Simulator Thermodynamics Gaps.docx`, Table 1, 2026-07-29): an exact
match on all nine species.

Ported verbatim from V1 `backend/props_nh3co2h2o.py`.
"""

from __future__ import annotations

import math

# --------------------------------------------------------------------------------------
# Universal constants
# --------------------------------------------------------------------------------------

#: Universal gas constant [J/(mol.K)].
R = 8.314462618

#: The ROUNDED gas constant this plant's FITTED correlations were calibrated against
#: [J/(mol.K)].
#:
#: V1 carries both values and uses each in its own places: `hydraulics`, `consequence` and
#: `machines` take the CODATA figure above, while `reactor.R_GAS` and the biuret Arrhenius
#: term take 8.314. The difference is 5.6e-5 relative, which is nothing on its own and is not
#: nothing inside an `exp(Ea/R . dT)`: the 322R001 dehydration activation energy is derived as
#: `11100 . R + 15500`, and evaluating that derivation with the CODATA constant instead moves
#: the activation energy by 5.1 J/mol and the rate constant by 0.13 %.
#:
#: Every coefficient fitted against 8.314 must keep being evaluated with 8.314, so the value
#: is carried under a name that says why rather than being silently unified. It lives here,
#: beside the universal constant, because `thermo.kinetics` is the lowest layer that needs
#: it; `core.units_of_measure` re-exports it as `R_GAS_FITTED_J` for the layers above.
R_FITTED = 8.314

#: Model reference temperature [K]. Every standard-state property is referenced here and
#: every interaction parameter's temperature term is a departure from it.
T0 = 298.15

LN10 = math.log(10.0)

#: Molar mass of water [kg/mol]. The molality basis is mol per kg of water, so this is what
#: converts between the model's coordinate and a mole-fraction one.
M_W = 0.0180152


# ======================================================================================
# Standard-state properties at 298.15 K
# ======================================================================================
# Each entry is  (dGf [kJ/mol], dHf [kJ/mol], cp_coefficients).
#
#   dGf, dHf        Gibbs energy / enthalpy of formation, CODATA/NIST aqueous convention.
#   cp = (a, b, c)  Helgeson (1986) form   Cp0 = a + b*T + c/(T - 200)   [J/(mol.K)], T [K]
#                   (Darde eq. 2.22; base-species a, b, c from Thomsen 1997 Table 5.7).
#   cp is None      the coefficient set is behind a paywall (Thomsen & Rasmussen 1999) and
#                   was NOT invented. Such a species is usable at 298.15 K only, and the
#                   accessor raises above that — see Rule 2, refusal over extrapolation.
#
# Process utility: dGf fixes each reaction's equilibrium constant at 25 C and the Cp
# coefficients carry it to plant temperature. That temperature dependence is what makes a
# desorber respond to steam rate instead of to a lookup table.
STANDARD_STATE = {
    #                dGf(kJ/mol) dHf(kJ/mol)  cp (a, b, c) [J/mol/K]
    "H2O":      (-237.140,   -285.830,   (58.370,  0.03896,  523.88)),      # Thomsen'97 T5.7
    "H+":       (   0.0,        0.0,      (0.0,     0.0,      0.0)),        # reference ion, by definition
    "OH-":      (-157.244,   -230.015,   (1418.2, -3.4446,  -51473.0)),     # Thomsen'97 T5.7
    "NH3(aq)":  ( -26.50,     -80.29,     (72.04,   0.0,      0.0)),        # Cp0: Correa'23 T1 (const-Cp)
    "NH4+":     ( -79.31,    -132.51,     (71.008,  0.0,      0.0)),        # Thomsen'97 T5.7
    "CO2(aq)":  (-385.98,    -413.80,     (238.05,  0.0,      0.0)),        # Cp0: Correa'23 T1 (const-Cp)
    "HCO3-":    (-586.77,    -691.99,     (585.75, -1.3612,  -21374.0)),    # Thomsen'97 T5.7
    "CO3--":    (-527.81,    -677.14,     (850.61, -2.8040,  -21308.0)),    # Thomsen'97 T5.7
    "NH2COO-":  (-379.355,   -502.863,    (-203.9191, 0.082259, 0.55163)),  # Darde'11 T2-3/T2-4 (fitted)
}


# ======================================================================================
# Liquid-phase speciation reactions R1-R5
# ======================================================================================
# Stoichiometry convention: products positive, reactants negative.
# Darde thesis eqs 2.1-2.5.
#
# Process utility: these five reactions ARE the LP section's chemistry. R5 in particular —
# carbamate formation — is why an ammonia-rich liquor holds CO2 that a CO2-rich one cannot,
# and why the heat of absorption charged to CO2 in the LP absorber must be the carbamate
# heat and not the physical solution heat.
REACTIONS = {
    "R1_water":     {"H2O": -1, "H+": +1, "OH-": +1},                        # H2O <-> H+ + OH-
    "R2_ammonium":  {"NH3(aq)": -1, "H+": -1, "NH4+": +1},                   # NH3 + H+ <-> NH4+
    "R3_bicarb":    {"CO2(aq)": -1, "H2O": -1, "HCO3-": +1, "H+": +1},       # CO2 + H2O <-> HCO3- + H+
    "R4_carbonate": {"HCO3-": -1, "CO3--": +1, "H+": +1},                    # HCO3- <-> CO3-- + H+
    "R5_carbamate": {"NH3(aq)": -1, "HCO3-": -1, "NH2COO-": +1, "H2O": +1},  # NH3 + HCO3- <-> NH2COO- + H2O
}


# ======================================================================================
# UNIQUAC structural parameters
# ======================================================================================
# Volume (r) and surface-area (q) parameters.
# Darde thesis Table 2-2 — the refined CO2-NH3-H2O set; supersedes the 1997 base values
# where they differ.
#
# Process utility: r and q drive the COMBINATORIAL part of the activity coefficient, the
# entropic penalty for mixing molecules of different size and shape. In a liquor that is
# 70 wt% urea by mass but only a modest mole fraction, getting these wrong shifts every
# activity in the same direction — which a design anchor would hide and a transient would not.
UNIQUAC_RQ = {
    "H2O":     (0.9200,  1.4000),
    "NH3(aq)": (1.6292,  2.9852),
    "CO2(aq)": (0.7500,  2.4500),
    "NH4+":    (4.8154,  4.6028),
    "H+":      (0.1378,  1.0e-16),
    "OH-":     (9.3973,  8.8171),
    "CO3--":   (10.828,  10.769),
    "HCO3-":   (8.0756,  8.6806),
    "NH2COO-": (4.3022,  4.1348),
}


# --------------------------------------------------------------------------------------
# UNIQUAC interaction energies
# --------------------------------------------------------------------------------------
# u_ij(T) = u0_ij + uT_ij * (T - 298.15), symmetric (u_ij == u_ji).
# Darde thesis Table 2-5 (u0) and Table 2-6 (uT). The species order below matches the
# thesis tables exactly, so the transcription can be checked row by row.
#
# The 1.0e9 entries against H+ are the published way of saying "this pair does not
# interact" — an interaction energy so large that the pair's contribution vanishes. They
# are NOT a placeholder and must not be replaced by a finite number.
_UORDER = ["H2O", "NH3(aq)", "CO2(aq)", "NH4+", "H+", "OH-", "CO3--", "HCO3-", "NH2COO-"]

# Lower-triangular rows of u0 [K], Darde Table 2-5.
_U0_TRI = [
    [0.0],
    [594.72, 1090.8],
    [8.8383, 2500.0, 302.25],
    [52.7305, 785.98, -424.01, 0.0],
    [10000.0, 1.0e9, 1.0e9, 1.0e9, 0.0],
    [600.50, 1733.9, 2500.0, 1877.9, 1.0e9, 1562.9],
    [361.39, 524.13, 2500.0, 226.60, 1.0e9, 1588.0, 1458.3],
    [577.05, 534.01, 526.305, 505.55, 1.0e9, 2500.0, 800.01, 771.04],
    [28.2779, 498.15, 2500.0, 44.849, 1.0e9, 2500.0, 2500.0, 613.25, 3343.1],
]

# Lower-triangular rows of uT [dimensionless], Darde Table 2-6.
_UT_TRI = [
    [0.0],
    [7.1827, 7.0912],
    [0.86293, 0.0, 0.35870],
    [0.50922, 6.1271, 8.6951, 0.0],
    [0.0, 0.0, 0.0, 0.0, 0.0],
    [8.5455, 0.1364, 0.0, 0.34921, 0.0, 5.6169],
    [3.3516, 4.9305, 0.0, 4.0555, 0.0, 2.7496, -1.3448],
    [-0.38795, 5.3111, -3.7340, -0.00795, 0.0, 0.0, 1.7241, -0.01981],
    [8.0238, 6.6532, 0.0, 12.047, 0.0, 0.0, 0.0, 3.0580, -15.920],
]


def _sym(tri: list[list[float]]) -> dict[tuple[str, str], float]:
    """Expand a lower-triangular table into a full symmetric ``(species, species)`` map."""
    n = len(tri)
    m: dict[tuple[str, str], float] = {}
    for i in range(n):
        for j in range(i + 1):
            a, b = _UORDER[i], _UORDER[j]
            m[(a, b)] = m[(b, a)] = tri[i][j]
    return m


#: Symmetric u0 map, keyed by species pair [K].
U0 = _sym(_U0_TRI)
#: Symmetric uT map, keyed by species pair [dimensionless].
UT = _sym(_UT_TRI)


def u_ij(a: str, b: str, T: float) -> float:
    """UNIQUAC interaction energy u_ij at temperature T [K].

    Process utility
    ---------------
    The temperature slope uT is what makes the activity coefficients — and therefore the
    liquor's NH3 and CO2 back-pressure — move when a heater or a desorber changes duty. A
    temperature-independent interaction set would give a liquor that strips the same amount
    at 99 C and at 143 C, which is the behaviour a frozen split vector already had.

    Equation
    --------
        u_ij(T) = u0_ij + uT_ij * (T - 298.15)      [K]
    """
    return U0[(a, b)] + UT[(a, b)] * (T - T0)


#: Charge number per species. Drives the Debye-Huckel term and the charge balance.
CHARGE = {
    "H2O": 0, "NH3(aq)": 0, "CO2(aq)": 0,
    "H+": +1, "NH4+": +1,
    "OH-": -1, "HCO3-": -1, "NH2COO-": -1,
    "CO3--": -2,
}

#: Debye-Huckel closest-approach constant b [(kg/mol)^0.5]. Thomsen (2005) eqs 5 and 9.
B_DH = 1.5

#: The eight charged and neutral solutes, in the order the speciation solver uses.
SOLUTES = ["H+", "OH-", "NH3(aq)", "NH4+", "CO2(aq)", "HCO3-", "CO3--", "NH2COO-"]

#: Moles of water per kilogram of water = 55.508. The molality-to-mole-fraction bridge.
N_W_PER_KG = 1000.0 / (M_W * 1000.0)


__all__ = [
    "R", "R_FITTED", "T0", "LN10", "M_W",
    "STANDARD_STATE", "REACTIONS", "UNIQUAC_RQ",
    "U0", "UT", "u_ij",
    "CHARGE", "B_DH", "SOLUTES", "N_W_PER_KG",
]
