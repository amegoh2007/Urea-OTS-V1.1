"""NH3-CO2-H2O Extended UNIQUAC property basis — the package facade.

This module is a **facade**, not an implementation. It re-exports the five modules the
electrolyte property basis is split across, so that downstream code (VLE, flash service,
absorber, vacuum condensers) has one import instead of five, and so that the split can be
refactored without touching a single call site.

    parameters      verbatim published tables — data only, no algebra
    standard_state  Helgeson Cp, Gibbs-Helmholtz, ln K, standard-state enthalpy
    henry           Rumpf & Maurer (NH3, CO2) and IAPWS G7-04 (N2, O2, CH4, H2)
    activity        complete Extended UNIQUAC gamma, and the excess enthalpy
    srk             Soave-Redlich-Kwong vapour fugacity, k_ij = 0
    speciation      the R1-R5 damped log-space Newton solve

Why the split
-------------
V1 held all of this in one 778-line file, which put a verbatim transcription of published
parameter tables in the same file as a Newton solver. A reviewer checking the Darde tables
had to read past the solver, and a change to either looked the same in a diff. The house
standard (`Claude.md` §1) caps a module at 600 lines and asks for one concept per module;
this is that split, with no numerical change.

See the As-Built Mathematical Reference, Part I.2.2 and Part II.2, for the model-selection
rationale and the equation set.
"""

from __future__ import annotations

# --- verbatim parameter tables ---------------------------------------------------------
from ureasim.thermo.parameters import (
    B_DH,
    CHARGE,
    LN10,
    M_W,
    N_W_PER_KG,
    R,
    REACTIONS,
    SOLUTES,
    STANDARD_STATE,
    T0,
    U0,
    UNIQUAC_RQ,
    UT,
    u_ij,
)

# --- standard-state thermodynamics -----------------------------------------------------
from ureasim.thermo.standard_state import (
    cp0,
    dH_reaction,
    h0,
    lnK,
    mu0_over_RT,
    pK,
    reaction_cp_available,
)

# --- Henry's law -----------------------------------------------------------------------
from ureasim.thermo.henry import (
    G704_VALID_T_K,
    HENRY_G704,
    henry_co2_MPa,
    henry_inert_MPa,
    henry_nh3_MPa,
)

# --- activity coefficients -------------------------------------------------------------
from ureasim.thermo.activity import (
    activity_ln_gamma,
    debye_huckel_A,
    debye_huckel_ln_gamma,
    excess_enthalpy,
    ionic_strength,
    short_range_ln_gamma,
    uniquac_combinatorial_ln_gamma,
    uniquac_combinatorial_ln_gamma_inf,
    uniquac_residual_ln_gamma,
    uniquac_residual_ln_gamma_inf,
)

# --- vapour-phase fugacity -------------------------------------------------------------
from ureasim.thermo.srk import (
    SRK_CRIT,
    cubic_largest_root,
    srk_ai_bi,
    srk_phi,
)

# --- liquid speciation -----------------------------------------------------------------
from ureasim.thermo.speciation import speciate

__all__ = [
    # parameters
    "R", "T0", "LN10", "M_W", "N_W_PER_KG",
    "STANDARD_STATE", "REACTIONS", "UNIQUAC_RQ", "U0", "UT", "u_ij",
    "CHARGE", "B_DH", "SOLUTES",
    # standard state
    "cp0", "reaction_cp_available", "mu0_over_RT", "lnK", "pK", "h0", "dH_reaction",
    # Henry
    "henry_nh3_MPa", "henry_co2_MPa", "henry_inert_MPa",
    "HENRY_G704", "G704_VALID_T_K",
    # activity
    "uniquac_combinatorial_ln_gamma", "uniquac_combinatorial_ln_gamma_inf",
    "uniquac_residual_ln_gamma", "uniquac_residual_ln_gamma_inf",
    "short_range_ln_gamma", "debye_huckel_A", "ionic_strength",
    "debye_huckel_ln_gamma", "activity_ln_gamma", "excess_enthalpy",
    # SRK
    "SRK_CRIT", "srk_ai_bi", "cubic_largest_root", "srk_phi",
    # speciation
    "speciate",
]
