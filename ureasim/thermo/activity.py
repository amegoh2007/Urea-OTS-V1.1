"""Complete Extended UNIQUAC activity coefficients for the NH3-CO2-H2O liquid phase.

What this gives the plant model
-------------------------------
The non-ideality of the liquor. A urea-plant recirculation liquor is 70 wt% urea carrying
a reacting ammonia/CO2/carbamate electrolyte: nothing in it behaves ideally, and the
departure from ideality is not a small correction — it is the difference between a column
that strips and one that does not.

The activity coefficient enters everywhere:

    partial pressure over the liquor   p_i = x_i gamma_i H_i(T)      -> bubble point
    reaction quotient                  K_j = prod (m_i gamma_i)^nu   -> speciation
    equilibrium line slope             m = dp_NH3/dx                 -> absorber NTU

Model structure
---------------
    ln gamma_i = ln gamma_i^C  +  ln gamma_i^R  +  ln gamma_i^DH
                 combinatorial    residual        long-range electrostatic

  * **Combinatorial** (Flory-Huggins + Staverman-Guggenheim) — the entropic penalty for
    mixing molecules of different size and shape, from the r and q parameters.
  * **Residual** — the enthalpic term, from the binary interaction energies u_ij(T). This
    is the part that carries temperature dependence, so it is the part that makes a liquor
    strip differently at 99 C and 143 C.
  * **Debye-Huckel** — the long-range electrostatic term. It acts only on charged species
    and on the solvent. In a carbamate liquor at several molal ionic strength this is not
    a refinement; omit it and the ionic activities are wrong by orders of magnitude.

Reference conventions (Thomsen 2005 eqs 17-18)
----------------------------------------------
    water   symmetric   (gamma -> 1 as x_w -> 1)
    solutes unsymmetric (gamma* -> 1 at infinite dilution in water)

The unsymmetric normalisation is what makes the solute activity compatible with a Henry's
constant, which is itself an infinite-dilution quantity. Mixing the two conventions is a
silent order-of-magnitude error, so the infinite-dilution limits are subtracted in closed
form rather than numerically.

Provenance
----------
    Kaj Thomsen, "Modeling electrolyte solutions with the extended universal quasichemical
    (UNIQUAC) model", Pure Appl. Chem. 77 (2005) 531-542 (IUPAC,
    doi 10.1351/pac200577030531). Equation numbers below refer to that paper.
    Debye-Huckel A(T) is Thomsen 2005 eq. 6 — the Sander et al. (1986) fit to the density
    and relative permittivity of water, valid to 500 K.

Thomsen (2005) also confirms verbatim that the residual (eq. 16) and combinatorial (eq. 12)
forms are exactly Thomsen's — an independent second source for the short-range code.

Validation carried over from V1: Gibbs-Duhem closes to 1e-9; the pure-component limit is
identically zero; the infinite-dilution limit matches the closed forms; Debye-Huckel
reproduces the limiting law.

Ported from V1 `backend/props_nh3co2h2o.py` (activity block). Numerically identical.
"""

from __future__ import annotations

import math

from ureasim.thermo.parameters import (
    B_DH,
    CHARGE,
    M_W,
    R,
    UNIQUAC_RQ,
    u_ij,
)


# ======================================================================================
# Combinatorial term — size and shape
# ======================================================================================

def uniquac_combinatorial_ln_gamma(x: dict) -> dict:
    """Combinatorial ``ln gamma`` for a liquid mole-fraction map, symmetric convention.

    Process utility
    ---------------
    In these liquors the species range from water (r = 0.92) to carbonate (r = 10.8) — an
    order of magnitude in molecular volume. The combinatorial term is the entropic cost of
    packing them together, and it is the part that does not vanish even at high dilution.

    Equation (Thomsen 2005 eq. 12)
    ------------------------------
        ln gamma_i^C = ln(phi_i/x_i) + 1 - phi_i/x_i
                       - 5 q_i [ ln(phi_i/theta_i) + 1 - phi_i/theta_i ]

    with volume fraction phi_i = x_i r_i / sum_k x_k r_k and area fraction
    theta_i = x_i q_i / sum_k x_k q_k. The ratios phi/x and phi/theta are formed directly
    so the expression stays finite as x_i -> 0.
    """
    sp = [s for s in x if x[s] > 0.0]
    r = {s: UNIQUAC_RQ[s][0] for s in sp}
    q = {s: UNIQUAC_RQ[s][1] for s in sp}
    rsum = sum(x[s] * r[s] for s in sp)
    qsum = sum(x[s] * q[s] for s in sp)
    out = {}
    for s in sp:
        phi = r[s] / rsum                      # phi_i / x_i
        theta = q[s] / qsum                    # theta_i / x_i
        pt = phi / theta                       # phi_i / theta_i
        out[s] = math.log(phi) + 1.0 - phi - 5.0 * q[s] * (math.log(pt) + 1.0 - pt)
    return out


def uniquac_combinatorial_ln_gamma_inf(species: str, solvent: str = "H2O") -> float:
    """Combinatorial ``ln gamma`` at infinite dilution in pure solvent — closed form.

    Needed to renormalise a solute from the symmetric to the unsymmetric reference. Taking
    this limit numerically (by evaluating at a tiny mole fraction) would inject a tolerance
    into every activity in the plant, so it is taken analytically:

        x_i -> 0, x_w -> 1  =>  phi_i/x_i -> r_i/r_w,
                                theta_i/x_i -> q_i/q_w,
                                phi_i/theta_i -> (r_i q_w)/(r_w q_i)
    """
    ri, qi = UNIQUAC_RQ[species]
    rw, qw = UNIQUAC_RQ[solvent]
    phi = ri / rw
    pt = (ri * qw) / (rw * qi)
    return math.log(phi) + 1.0 - phi - 5.0 * qi * (math.log(pt) + 1.0 - pt)


# ======================================================================================
# Residual term — energetic interaction, and the temperature dependence
# ======================================================================================

def uniquac_residual_ln_gamma(x: dict, T: float) -> dict:
    """Residual (short-range, enthalpic) ``ln gamma`` at T [K], symmetric convention.

    Process utility
    ---------------
    This is the temperature-carrying term. The Boltzmann factors psi_ki depend on T
    through u_ij(T) = u0 + uT (T - 298.15), so a liquor's ammonia back-pressure rises with
    temperature by the right amount rather than by a fitted slope. Every desorber,
    hydrolyser and recirculation heater response passes through here.

    Equation (Thomsen 2005 eq. 16)
    ------------------------------
        ln g_i^R = q_i [ 1 - ln( sum_k th_k psi_ki )
                           - sum_k ( th_k psi_ik / sum_l th_l psi_lk ) ]

        th_k    = x_k q_k / sum_l x_l q_l          surface-area fraction
        psi_ki  = exp( -(u_ki - u_ii) / T )        Boltzmann factor, u in kelvin
    """
    sp = [s for s in x if x[s] > 0.0]
    q = {s: UNIQUAC_RQ[s][1] for s in sp}
    qsum = sum(x[s] * q[s] for s in sp)
    th = {s: x[s] * q[s] / qsum for s in sp}

    # Boltzmann factors psi[(k, i)] = exp(-(u_ki - u_ii)/T).
    psi = {}
    for i in sp:
        uii = u_ij(i, i, T)
        for k in sp:
            psi[(k, i)] = math.exp(-(u_ij(k, i, T) - uii) / T)

    # denom[k] = sum_l th_l psi_lk, computed once and reused in both sums.
    denom = {k: sum(th[l] * psi[(l, k)] for l in sp) for k in sp}

    out = {}
    for i in sp:
        s1 = math.log(denom[i])                                   # ln( sum_k th_k psi_ki )
        s2 = sum(th[k] * psi[(i, k)] / denom[k] for k in sp)
        out[i] = q[i] * (1.0 - s1 - s2)
    return out


def uniquac_residual_ln_gamma_inf(species: str, T: float, solvent: str = "H2O") -> float:
    """Residual ``ln gamma`` at infinite dilution in pure solvent — closed form.

    Limit of `uniquac_residual_ln_gamma` as th_solvent -> 1 and all other th -> 0:

        ln g_i^{R,inf} = q_i [ 1 - ln(psi_wi) - psi_iw ],   w = solvent
    """
    psi_wi = math.exp(-(u_ij(solvent, species, T) - u_ij(species, species, T)) / T)
    psi_iw = math.exp(-(u_ij(species, solvent, T) - u_ij(solvent, solvent, T)) / T)
    return UNIQUAC_RQ[species][1] * (1.0 - math.log(psi_wi) - psi_iw)


def short_range_ln_gamma(x: dict, T: float,
                         unsymmetric_species=None, solvent: str = "H2O") -> dict:
    """Short-range ``ln gamma`` = combinatorial + residual, at T [K].

    By default the symmetric (rational) convention for every species. Pass a set of
    `unsymmetric_species` — typically the ions and dissolved gases — to renormalise those
    to the unsymmetric reference:

        ln gamma_i^* = ln gamma_i(x) - ln gamma_i^{inf}

    The solvent is always left symmetric.

    .. warning::
       This is the SHORT-RANGE part only. The complete electrolyte activity coefficient
       also carries the long-range Debye-Huckel term. Use `activity_ln_gamma` for the full
       model; this function exists for validation against the short-range literature and
       for the two neutral species where the electrostatic term vanishes anyway.
    """
    comb = uniquac_combinatorial_ln_gamma(x)
    res = uniquac_residual_ln_gamma(x, T)
    unsym = unsymmetric_species or set()
    out = {}
    for s in comb:
        g = comb[s] + res[s]
        if s in unsym and s != solvent:
            g -= (uniquac_combinatorial_ln_gamma_inf(s, solvent)
                  + uniquac_residual_ln_gamma_inf(s, T, solvent))
        out[s] = g
    return out


# ======================================================================================
# Long-range electrostatics — the Debye-Huckel term
# ======================================================================================

def debye_huckel_A(T: float) -> float:
    """Debye-Huckel parameter A(T) [(kg/mol)^0.5] — Thomsen 2005 eq. 6.

    Carries the whole temperature dependence of water's permittivity and density (Sander
    et al. 1986 fit, valid to 500 K). The fit's reference temperature is 273.15 K.

        A = 1.131 + 1.335e-3 t + 1.164e-5 t^2,   t = T - 273.15 [deg C]

    Anchor check: A(298.15 K) = 1.1717, matching the literature Debye-Huckel slope ~1.174.
    """
    t = T - 273.15
    return 1.131 + 1.335e-3 * t + 1.164e-5 * t * t


def ionic_strength(x: dict) -> float:
    """Ionic strength I [mol/kg water] from a mole-fraction map — Thomsen 2005 eq. 7.

    Process utility
    ---------------
    A desorber bottoms liquor sits at several molal ionic strength. I is what sets how
    strongly the ions screen one another, and therefore how much of the ammonia is held as
    ammonium rather than released as free NH3.

    Equation
    --------
        I = 0.5 sum_i x_i z_i^2 / (x_w M_w)
    """
    xw = x.get("H2O", 0.0)
    if xw <= 0.0:
        raise ValueError("ionic_strength requires water (solvent) to be present")
    s = sum(x[sp] * CHARGE[sp] ** 2 for sp in x if x[sp] > 0.0)
    return 0.5 * s / (xw * M_W)


def debye_huckel_ln_gamma(x: dict, T: float) -> dict:
    """Long-range electrostatic contribution to ``ln gamma`` — Thomsen 2005 eqs. 8 and 9.

    Equations
    ---------
        ion i (unsymmetric):
            ln g_i^DH = -z_i^2 A sqrt(I) / (1 + b sqrt(I))

        water (symmetric):
            ln g_w^DH = M_w (2A/b^3) [ 1 + b sqrt(I) - 1/(1 + b sqrt(I))
                                       - 2 ln(1 + b sqrt(I)) ]

    Neutral solutes (z = 0) get zero from eq. 8, which is correct — the electrostatic term
    acts only on charged species and on the solvent.

    The ion form is **already** unsymmetric (it tends to zero as I -> 0), so it is added
    directly to the unsymmetric solute activity coefficient in eq. 17 with no
    infinite-dilution subtraction. Subtracting one would double-count.
    """
    A = debye_huckel_A(T)
    I = ionic_strength(x)
    sI = math.sqrt(I)
    b = B_DH
    out = {}
    for sp in x:
        if x[sp] <= 0.0:
            continue
        if sp == "H2O":
            out[sp] = M_W * (2.0 * A / b ** 3) * (
                1.0 + b * sI - 1.0 / (1.0 + b * sI) - 2.0 * math.log(1.0 + b * sI))
        else:
            z = CHARGE[sp]
            out[sp] = -(z * z) * A * sI / (1.0 + b * sI)
    return out


# ======================================================================================
# The complete activity coefficient
# ======================================================================================

def activity_ln_gamma(x: dict, T: float, solutes=None, solvent: str = "H2O") -> dict:
    """Complete Extended UNIQUAC ``ln gamma`` at T [K] — the model the solvers consume.

    Process utility
    ---------------
    This is the single function that makes every liquor in the LP section behave like a
    real solution. The speciation solver calls it inside its Newton loop; the bubble-point
    routine multiplies its output by a Henry constant; the absorber differentiates it to
    get the equilibrium-line slope.

    Equations (Thomsen 2005 eqs. 17 and 18)
    ---------------------------------------
        water:      ln g_w   = ln g_w^C + ln g_w^R + ln g_w^DH
        solute i:   ln g_i^* = (ln g_i^C - ln g_i^{C,inf})
                             + (ln g_i^R - ln g_i^{R,inf})
                             + ln g_i^DH

    Parameters
    ----------
    solutes
        Species on the unsymmetric (infinite-dilution-in-water) reference. Defaults to
        every non-solvent species present.
    """
    comb = uniquac_combinatorial_ln_gamma(x)
    res = uniquac_residual_ln_gamma(x, T)
    dh = debye_huckel_ln_gamma(x, T)
    if solutes is None:
        solutes = set(sp for sp in x if sp != solvent and x[sp] > 0.0)
    out = {}
    for sp in comb:
        if sp == solvent:
            out[sp] = comb[sp] + res[sp] + dh[sp]
        elif sp in solutes:
            out[sp] = ((comb[sp] - uniquac_combinatorial_ln_gamma_inf(sp, solvent))
                       + (res[sp] - uniquac_residual_ln_gamma_inf(sp, T, solvent))
                       + dh[sp])
        else:
            out[sp] = comb[sp] + res[sp] + dh[sp]
    return out


# ======================================================================================
# Excess (mixing) enthalpy — the H1 tier of the stream-enthalpy scheme
# ======================================================================================

def excess_enthalpy(x: dict, T: float, dT: float = 0.01) -> float:
    """Molar excess (mixing) enthalpy h^E [J/mol] of the liquid.

    Process utility
    ---------------
    The heat released or absorbed purely by *mixing* — separate from any reaction. In a
    concentrated carbamate liquor this is not negligible, and it is the term that upgrades
    a stream enthalpy from the H0 tier (ideal solution) to the H1 tier. Publishing it
    separately is what lets each stream declare honestly which tier it is on.

    Equation
    --------
        h^E = -R T^2 sum_i x_i d(ln gamma_i)/dT

    evaluated by central difference in T.

    The combinatorial part is temperature-independent (Thomsen 2005, after eq. 18), so it
    contributes nothing — h^E is driven entirely by the residual and electrostatic terms,
    exactly as the reference states. It is nevertheless evaluated inside the difference so
    the expression stays a literal transcription of the definition.

    Note
    ----
    This is the mixing part only. The absolute sensible enthalpy additionally needs the
    pure-component Cp integrals, which live in `thermo.standard_state.h0`.
    """
    def sum_x_lng(TT: float) -> float:
        comb = uniquac_combinatorial_ln_gamma(x)
        res = uniquac_residual_ln_gamma(x, TT)
        dh = debye_huckel_ln_gamma(x, TT)
        return sum(x[s] * (comb[s] + res[s] + dh[s]) for s in comb)

    dlng_dT = (sum_x_lng(T + dT) - sum_x_lng(T - dT)) / (2.0 * dT)
    return -R * T * T * dlng_dT


__all__ = [
    "excess_enthalpy",
    "uniquac_combinatorial_ln_gamma",
    "uniquac_combinatorial_ln_gamma_inf",
    "uniquac_residual_ln_gamma",
    "uniquac_residual_ln_gamma_inf",
    "short_range_ln_gamma",
    "debye_huckel_A",
    "ionic_strength",
    "debye_huckel_ln_gamma",
    "activity_ln_gamma",
]
