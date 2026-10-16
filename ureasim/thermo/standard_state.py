"""Standard-state thermodynamics of the NH3-CO2-H2O aqueous species.

What this gives the plant model
-------------------------------
The temperature dependence of the five liquid-phase speciation equilibria (R1-R5). That is
what makes a desorber, a hydrolyser or an absorber respond to *heat* rather than to a
lookup table: raise the 328C002 bottoms from 139 C and the carbamate equilibrium R5 shifts,
free NH3 rises, and the column strips harder. A constant set of equilibrium constants would
leave that entire mechanism out.

The chain is:

    Cp0(T)  ->  mu0(T)/RT  ->  ln K_j(T)  ->  speciation  ->  free NH3 / CO2  ->  bubble point

Equations
---------
    Helgeson (1986) heat capacity          Cp0 = a + b T + c/(T - 200)        [Darde eq. 2.22]
    Gibbs-Helmholtz                        d(mu0/RT)/dT = -H(T)/(R T^2)       [Darde eq. 2.21]
    with                                   H(T) = dHf + integral_{T0}^{T} Cp dT'
    equilibrium constant                   ln K_j = -sum_i nu_ij mu0_i/(R T)

The Gibbs-Helmholtz integral is evaluated in CLOSED FORM for the Helgeson Cp shape, not
numerically — a quadrature here would put a tolerance inside every equilibrium constant in
the plant.

Refusal behaviour
-----------------
A species whose Cp coefficients are not in an open source carries ``cp = None`` and this
module RAISES above 298.15 K rather than substituting a neighbour's coefficients. Every
such species is usable at 25 C only. See the As-Built reference, Part 0, Rule 2.

Ported from V1 `backend/props_nh3co2h2o.py` (standard-state block). Numerically identical.
"""

from __future__ import annotations

import math

from ureasim.thermo.parameters import (
    LN10,
    R,
    REACTIONS,
    STANDARD_STATE,
    T0,
)


def cp0(species: str, T: float) -> float:
    """Standard-state heat capacity Cp0 [J/(mol.K)] at T [K].

    Process utility
    ---------------
    Carries each species' formation energy from the 25 C reference to plant temperature.
    The hyperbolic ``c/(T - 200)`` term is what gives aqueous ions their characteristic
    heat-capacity maximum; a constant Cp would put the carbamate equilibrium in the wrong
    place by the time the hydrolyser reaches 200 C.

    Equation
    --------
        Cp0 = a + b T + c / (T - 200)          [Helgeson 1986; Darde eq. 2.22]

    Raises
    ------
    ValueError
        If the species' coefficients are not in an open source. Not fabricated.
    """
    cp = STANDARD_STATE[species][2]
    if cp is None:
        raise ValueError(
            f"Cp0 coefficients for {species} are not in an open source "
            f"(Thomsen & Rasmussen 1999); not fabricated."
        )
    a, b, c = cp
    return a + b * T + c / (T - 200.0)


def reaction_cp_available(reaction: str) -> bool:
    """True when every species in a reaction has open-source Cp coefficients.

    Gate for temperature extrapolation: a reaction whose members do not all carry Helgeson
    coefficients can only be evaluated at the 298.15 K reference, and callers must refuse
    rather than substitute (Rule 2).
    """
    return all(STANDARD_STATE[s][2] is not None for s in REACTIONS[reaction])


def mu0_over_RT(species: str, T: float) -> float:
    """Standard-state chemical potential mu0_i(T) / RT, dimensionless.

    Referenced so that ``mu0(T0)/(R T0) = dGf/(R T0)``.

    Process utility
    ---------------
    This is the quantity that turns a table of 25 C formation energies into a live
    equilibrium constant at the temperature a column actually runs at.

    Equation
    --------
        d(mu0/RT)/dT = -H(T)/(R T^2)                                [Darde eq. 2.21]
        H(T)         = dHf + integral_{T0}^{T} Cp0 dT'              [Darde eq. 2.23]

    With the Helgeson shape Cp0 = a + b T + c/(T - 200) the enthalpy integral is

        H(t) = H0 + a t + (b/2) t^2 + c ln((t - 200)/(T0 - 200)),
        H0   = dHf - a T0 - (b/2) T0^2

    and the outer integral of -H/(R t^2) has the closed form assembled in ``F`` below. The
    ``c`` term is integrated by parts:

        int -ln((t - 200)/K0) / t^2 dt = ln((t - 200)/K0)/t - (1/200) ln((t - 200)/t)
    """
    dGf, dHf, cp = STANDARD_STATE[species]
    g0 = dGf * 1000.0 / (R * T0)                     # mu0(T0)/(R T0), dimensionless
    if T == T0:
        return g0

    a, b, c = cp
    dHf_J = dHf * 1000.0
    A = a
    B = b
    C = c

    def F(t: float) -> float:
        """Antiderivative of -H(t) / (R t^2), assembled term by term."""
        # Constant part of H(t), after absorbing the T0 references of the a and b terms.
        H0 = dHf_J - A * T0 - 0.5 * B * T0 * T0
        # H(t) = H0 + A t + (B/2) t^2 + C ln((t - 200)/(T0 - 200))
        term_const = H0 / (R) * (1.0 / t)                    # int -H0/(R t^2)  = H0/(R t)
        term_A = -A / R * math.log(t)                        # int -A/(R t)
        term_B = -B / (2.0 * R) * t                          # int -(B/2)/R
        K0 = T0 - 200.0
        term_C = (C / R) * (
            math.log((t - 200.0) / K0) / t
            - (1.0 / 200.0) * math.log((t - 200.0) / t)
        )
        return term_const + term_A + term_B + term_C

    return g0 + (F(T) - F(T0))


def lnK(reaction: str, T: float) -> float:
    """Natural logarithm of the activity-basis equilibrium constant K_j(T).

    Process utility
    ---------------
    R2 and R5 between them decide how much of a liquor's ammonia is *free* — available to
    be stripped, absorbed or boiled off — and how much is locked as ammonium or carbamate.
    Every LP-section duty follows from that split.

    Equation
    --------
        ln K = -dG_rxn/(R T) = -sum_i nu_i mu0_i/(R T)

    Raises
    ------
    ValueError
        Off 298.15 K, if any species in the reaction lacks open-source Cp coefficients.
    """
    stoich = REACTIONS[reaction]
    if T != T0 and not reaction_cp_available(reaction):
        raise ValueError(
            f"{reaction} has a species with no open-source Cp; T-extrapolation "
            f"unavailable (298.15 K only). Not fabricated."
        )
    return -sum(nu * mu0_over_RT(sp, T) for sp, nu in stoich.items())


def pK(reaction: str, T: float = T0) -> float:
    """``-log10(K)`` for a reaction at T [K].

    Kept because the textbook aqueous pKa1 / pKa2 / pKw are the validation oracle for the
    whole standard-state chain: reproducing them, and their temperature dependence, from
    these parameters alone is what proves the transcription.
    """
    return -lnK(reaction, T) / LN10


# ======================================================================================
# Standard-state enthalpy and explicit heats of reaction
# ======================================================================================

def h0(species: str, T: float) -> float:
    """Standard-state molar enthalpy H_i(T) [J/mol].

    Process utility
    ---------------
    Supplies the enthalpy of each aqueous species to the stream-enthalpy layer
    (`thermo.enthalpy`), so a reacting node's energy balance closes on formation energies
    rather than on a sensible-heat approximation. A sensible-only enthalpy creates or
    destroys energy across a reaction; this does not.

    Equation
    --------
        H_i(T) = dHf + integral_{T0}^{T} Cp0 dT'
               = dHf + a (T - T0) + (b/2)(T^2 - T0^2) + c ln((T - 200)/(T0 - 200))

    At T0 this is simply dHf, which is always available.

    Raises
    ------
    ValueError
        Off 298.15 K without open-source Cp coefficients. Not fabricated.
    """
    dGf, dHf, cp = STANDARD_STATE[species]
    H = dHf * 1000.0
    if T == T0:
        return H
    if cp is None:
        raise ValueError(
            f"H0({species}) off 298.15 K needs its Cp (Thomsen & Rasmussen 1999, "
            f"paywalled); not fabricated."
        )
    a, b, c = cp
    H += (a * (T - T0)
          + 0.5 * b * (T * T - T0 * T0)
          + c * math.log((T - 200.0) / (T0 - 200.0)))
    return H


def dH_reaction(reaction: str, T: float = T0) -> float:
    """Standard enthalpy of reaction dH_rxn(T) [kJ/mol]; products +, reactants -.

    Process utility
    ---------------
    The explicit heat of reaction, from formation enthalpies alone. This is the
    first-principles replacement for a back-solved latent duty: the heat an absorber
    releases when it takes up CO2 as carbamate is R5's enthalpy, not a fitted kJ/kg.

    Validation: reproduces the textbook aqueous values — water ionisation +55.8, NH4+
    protonation -52.2, HCO3-/CO3-- +14.7 kJ/mol.
    """
    stoich = REACTIONS[reaction]
    return sum(nu * h0(sp, T) for sp, nu in stoich.items()) / 1000.0


__all__ = ["cp0", "reaction_cp_available", "mu0_over_RT", "lnK", "pK",
           "h0", "dH_reaction"]
