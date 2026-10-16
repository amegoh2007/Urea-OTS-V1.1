"""Neutral H2O/urea binary UNIQUAC — the evaporator melt.

Equipment modelled
------------------
    324E001 / 324F001   Evaporator I,  0.330 bar a, 130 C, ~95 wt% urea
    324E003 / 324F003   Evaporator II, 0.131 bar a, 140 C, ~99.7 wt% urea

Why a SECOND liquid model exists
--------------------------------
The electrolyte package (`thermo.properties`) does not carry urea as a UNIQUAC species —
urea is not in its parameter set, so it can only enter as a mole-fraction diluent. At
68-80 wt% urea through the 323 recirculation train that is acceptable. At 94-99.7 wt% it
fails hard:

    stage     T (C)   P_PFD (bar a)   electrolyte error   this model
    324E001   130     0.330           +30.6 %             used instead
    324E003   140     0.131           +65.7 %             +2.2 %

Urea and water are both **neutral**, so the Debye-Huckel term of Extended UNIQUAC is
identically zero and the liquid activity model reduces to ordinary UNIQUAC. This therefore
*is* Extended UNIQUAC in the urea/water limit — and it is the only one of the two models
that sees urea as a species with its own volume, surface and interaction energy rather than
as an inert diluent.

Process utility
---------------
What the evaporators actually need is the inverse problem: given the vacuum a stage holds
and the temperature its steam chest delivers, **what urea concentration does the melt reach
at equilibrium?** That is `solve_urea_mass_fraction`, and it is the number the whole
finishing section is specified on — product concentration, biuret formation and the melt's
freezing margin all follow from it.

Provenance
----------
Equations, structural parameters and the interaction convention are transcribed from the
open supplementary implementation of

    A. L. Voskov and G. F. Voronin, "Thermodynamic model of the urea synthesis process",
    DOI 10.1021/acs.jced.6b00557 (files ``GRT_UNIQUAC.m``, ``liquid_hc.m``,
    ``liquid6comp.cpp``; X11/MIT licence, (c) 2008-2016 Voskov and Voronin).

Binary parameters: H2O->urea ``(a0, a1) = (0, 0)``; urea->H2O
``(-211.9567785927018 K, 0)``.

Declared extrapolation — not hidden
-----------------------------------
The publication's full-model validation envelope is 408.15-503.15 K and 35-450 bar a. Unit
324 runs 372.15-473.15 K at 0.02-1.00 bar a, so the vacuum stages are **outside the
validated pressure range**. `validity_status` returns that fact as a machine-readable
string, so a numerically converged activity solve cannot be mistaken for a validated one.

Water fugacity comes from the shared IAPWS-IF97 saturation line, not a private Antoine
correlation, so there is one pure-water reference state across the whole plant. The former
Antoine form is retained only as a comparison oracle.

This module provides no electrolyte speciation, no gas equation of state, no Poynting
correction and no absolute enthalpy.

Conventions
-----------
Compositions are true fractions, never percentages. Temperatures are kelvin and pressures
bar absolute.

Ported from V1 `backend/thermo_extended_uniquac.py`. Numerically identical.
"""

from __future__ import annotations

import math
from functools import lru_cache

from ureasim.thermo import iapws

MODEL_NAME = "Extended UNIQUAC neutral H2O/urea limit (Voskov-Voronin)"

#: Guarded application range — the Unit-324 operating envelope, not a claim about the fit.
VALID_TEMPERATURE_K = (372.15, 473.15)
VALID_PRESSURE_BARA = (0.02, 1.00)

#: The publication's own full-model validation envelope. Unit 324 sits outside it in
#: pressure, which is why `validity_status` exists.
SOURCE_VALID_TEMPERATURE_K = (408.15, 503.15)
SOURCE_VALID_PRESSURE_BARA = (35.0, 450.0)

MOLAR_MASS_WATER_G_MOL = 18.01528
MOLAR_MASS_UREA_G_MOL = 60.05526

#: UNIQUAC volume (r) and surface (q) parameters, ordered (H2O, urea).
_R = (0.92, 2.1408)
_Q = (1.40, 2.4860)

#: Interaction energies a_ij, indexed [source][destination] to match the Voskov source.
#: Only urea->H2O is non-zero: that single number is the whole binary fit.
_A0 = (
    (0.0, 0.0),
    (-211.9567785927018, 0.0),
)
_A1 = (
    (0.0, 0.0),
    (0.0, 0.0),
)

#: Lattice coordination number z, the standard UNIQUAC value.
_COORDINATION_NUMBER = 10.0


class UnsupportedThermodynamicDomain(ValueError):
    """Raised when a call lies outside this model's stated range.

    Refusal rather than extrapolation — see the As-Built reference, Part 0, Rule 2.
    """


# ======================================================================================
# Domain guards
# ======================================================================================

def validity_status(temperature_k: float, pressure_bara: float) -> str:
    """``'VALIDATED'`` or ``'DESIGN_ANCHORED_EXTRAPOLATION'``.

    Process utility
    ---------------
    The Unit-324 vacuum application is outside the publication's validation *pressure*
    range. Keeping that status machine-readable prevents a numerically converged activity
    solve from being mistaken for a validated one — the exact failure mode that lets an
    extrapolation quietly become a design basis.
    """
    _validate_temperature(temperature_k)
    _validate_pressure(pressure_bara)
    t_low, t_high = SOURCE_VALID_TEMPERATURE_K
    p_low, p_high = SOURCE_VALID_PRESSURE_BARA
    if t_low <= temperature_k <= t_high and p_low <= pressure_bara <= p_high:
        return "VALIDATED"
    return "DESIGN_ANCHORED_EXTRAPOLATION"


def _validate_temperature(temperature_k: float) -> None:
    low, high = VALID_TEMPERATURE_K
    if not math.isfinite(temperature_k) or not low <= temperature_k <= high:
        raise UnsupportedThermodynamicDomain(
            f"temperature must be finite and within {low}-{high} K"
        )


def _validate_pressure(pressure_bara: float) -> None:
    low, high = VALID_PRESSURE_BARA
    if not math.isfinite(pressure_bara) or not low <= pressure_bara <= high:
        raise UnsupportedThermodynamicDomain(
            f"pressure must be finite and within {low}-{high} bar(a)"
        )


def _validate_urea_mass_fraction(urea_mass_fraction: float) -> None:
    if (not math.isfinite(urea_mass_fraction)
            or not 0.0 <= urea_mass_fraction <= 1.0):
        raise ValueError("urea mass fraction must be finite and within [0, 1]")


# ======================================================================================
# Composition
# ======================================================================================

def mole_fractions_from_urea_mass_fraction(
    urea_mass_fraction: float,
) -> tuple[float, float]:
    """``(x_water, x_urea)`` from a binary urea mass fraction.

    The engine's species layer carries mass fractions; UNIQUAC wants mole fractions. The
    conversion matters here more than usual: urea is 3.3x the molar mass of water, so a
    97.7 wt% melt is only about 59 mol% urea.
    """
    _validate_urea_mass_fraction(urea_mass_fraction)
    moles_water = (1.0 - urea_mass_fraction) / MOLAR_MASS_WATER_G_MOL
    moles_urea = urea_mass_fraction / MOLAR_MASS_UREA_G_MOL
    total_moles = moles_water + moles_urea
    return moles_water / total_moles, moles_urea / total_moles


# ======================================================================================
# Activity model
# ======================================================================================

def _interactions(a_urea_water_k: float | None) -> tuple:
    """The a0 matrix: Voskov-Voronin's, or the same with its one urea->H2O energy replaced.

    Process utility: a refit of the binary's single parameter to a plant's own design rows
    (unit 324's melt, handoff B-58) without disturbing the published model the other
    callers use.
    """
    if a_urea_water_k is None:
        return _A0
    return ((0.0, 0.0), (a_urea_water_k, 0.0))


def ln_gamma(x_water: float, x_urea: float,
             temperature_k: float, *,
             a_urea_water_k: float | None = None) -> tuple[float, float]:
    """``(ln gamma_water, ln gamma_urea)`` from binary UNIQUAC.

    Process utility
    ---------------
    The water activity coefficient is what makes a urea melt hold on to its last percent of
    water. An ideal-solution melt would give up water far too readily, so the evaporators
    would appear to reach product concentration at a vacuum they cannot actually hold.

    Equations
    --------
        combinatorial:
            ln g_i^C = ln(phi_i/x_i) + (z/2) q_i ln(theta_i/phi_i)
                       + l_i - (phi_i/x_i) sum_j x_j l_j
            l_i      = (z/2)(r_i - q_i) - (r_i - 1)

        residual:
            ln g_i^R = q_i [ 1 - ln(sum_j theta_j tau_ji)
                               - sum_j theta_j tau_ij / sum_k theta_k tau_kj ]
            tau_ij   = exp(-a0_ij / T - a1_ij)

    The interaction matrix is ordered by source species (row) and destination species
    (column), matching ``a_ij`` and ``tau_ij`` in the Voskov source.

    Exact zero mole fractions are accepted, so the pure-component limits can be evaluated
    without arbitrary composition clipping. ``a_urea_water_k`` replaces the urea->H2O energy
    [K]; None is the published fit.
    """
    _validate_temperature(temperature_k)
    if (not math.isfinite(x_water) or not math.isfinite(x_urea)
            or x_water < 0.0 or x_urea < 0.0
            or not math.isclose(x_water + x_urea, 1.0, rel_tol=0.0, abs_tol=1.0e-12)):
        raise ValueError("mole fractions must be finite, nonnegative, and sum to one")

    total = x_water + x_urea
    x = (x_water / total, x_urea / total)
    r_sum = sum(x_i * r_i for x_i, r_i in zip(x, _R))
    q_sum = sum(x_i * q_i for x_i, q_i in zip(x, _Q))
    theta = tuple(x[i] * _Q[i] / q_sum for i in range(2))

    z = _COORDINATION_NUMBER
    ell = tuple(z / 2.0 * (_R[i] - _Q[i]) - (_R[i] - 1.0) for i in range(2))
    sum_x_ell = sum(x[i] * ell[i] for i in range(2))
    a0 = _interactions(a_urea_water_k)
    tau = tuple(
        tuple(math.exp(-a0[i][j] / temperature_k - _A1[i][j]) for j in range(2))
        for i in range(2)
    )
    theta_tau = tuple(sum(theta[j] * tau[j][i] for j in range(2)) for i in range(2))

    result = []
    for i in range(2):
        # Ratios are formed directly (phi/x, theta/phi) so the expression stays finite as
        # a mole fraction goes to zero.
        phi_over_x = _R[i] / r_sum
        theta_over_phi = (_Q[i] / q_sum) / phi_over_x
        combinatorial = (
            math.log(phi_over_x)
            + z / 2.0 * _Q[i] * math.log(theta_over_phi)
            + ell[i]
            - phi_over_x * sum_x_ell
        )
        residual = _Q[i] * (
            1.0
            - math.log(theta_tau[i])
            - sum(theta[j] * tau[i][j] / theta_tau[j] for j in range(2))
        )
        result.append(combinatorial + residual)
    return result[0], result[1]


def water_activity(urea_mass_fraction: float, temperature_k: float, *,
                   a_urea_water_k: float | None = None) -> float:
    """Liquid water activity ``a_w = x_w gamma_w``.

    Process utility: multiplied by the pure-water saturation pressure, this is the vapour
    pressure the melt exerts — which is what a vacuum stage has to pull against.
    """
    _validate_temperature(temperature_k)
    _validate_urea_mass_fraction(urea_mass_fraction)
    if urea_mass_fraction == 0.0:
        return 1.0
    if urea_mass_fraction == 1.0:
        return 0.0
    x_water, x_urea = mole_fractions_from_urea_mass_fraction(urea_mass_fraction)
    ln_gamma_water, _ = ln_gamma(x_water, x_urea, temperature_k,
                                 a_urea_water_k=a_urea_water_k)
    return x_water * math.exp(ln_gamma_water)


def _water_psat_antoine(temperature_k: float) -> float:
    """Antoine pure-water Psat — retained ONLY as a comparison oracle.

    Superseded by IAPWS-IF97. Kept so the migration away from it stays measurable; nothing
    in the running model calls it.
    """
    temperature_c = temperature_k - 273.15
    pressure_mmhg = 10.0 ** (8.14019 - 1810.94 / (244.485 + temperature_c))
    return pressure_mmhg / 750.0616827


def water_psat_bara(temperature_k: float) -> float:
    """Pure-water saturation pressure [bar a] via IAPWS-IF97.

    The pure-water fugacity reference for this neutral VLE comes from the shared IF97
    Region-4 line — the same boundary the 329 steam network uses — so there is a single
    pure-water reference state across the plant. The activity model itself is unchanged
    UNIQUAC.
    """
    _validate_temperature(temperature_k)
    return iapws.psat_bara(temperature_k - 273.15)


# ======================================================================================
# The P-x equilibrium and its solve
# ======================================================================================

def px_equilibrium_residual(urea_mass_fraction: float, temperature_k: float,
                            pressure_bara: float, *,
                            a_urea_water_k: float | None = None) -> float:
    """Pure-water-vapour P-x residual [bar].

    Equation
    --------
        residual = a_water(w, T) * Psat_water(T) - P

    Zero therefore denotes a liquid in equilibrium with a vapour whose pressure is
    attributed entirely to water — which is what a urea-melt evaporator's overhead
    actually is (see `handoff.md` B-1 for the trace NH3/CO2 that this deliberately omits).
    """
    _validate_temperature(temperature_k)
    _validate_pressure(pressure_bara)
    _validate_urea_mass_fraction(urea_mass_fraction)
    return (water_activity(urea_mass_fraction, temperature_k, a_urea_water_k=a_urea_water_k)
            * water_psat_bara(temperature_k)
            - pressure_bara)


@lru_cache(maxsize=16384)
def solve_urea_mass_fraction(
    temperature_k: float,
    pressure_bara: float,
    *,
    mass_fraction_tolerance: float = 1.0e-12,
    pressure_tolerance_bara: float = 1.0e-12,
    max_iterations: int = 100,
    a_urea_water_k: float | None = None,
) -> float:
    """Urea mass fraction a melt reaches at (T, P) — the evaporator's answer.

    Process utility
    ---------------
    This is the number Unit 324 is specified on. Given the vacuum a stage holds and the
    temperature its steam chest delivers, it returns the equilibrium melt concentration,
    from which product spec, biuret formation and the freezing margin all follow.

    Method
    ------
    Safeguarded Newton on the P-x residual. Pure water and pure urea provide a guaranteed
    physical bracket throughout the applicable part of the guarded range; a Newton step is
    accepted only **inside** that bracket and the method bisects otherwise. That keeps
    deterministic bounds while avoiding dozens of bisections per simulation tick.

    The first estimate comes from inverting the *ideal* water activity; the activity
    coefficients then supply the non-ideal correction, which is typically one or two Newton
    steps rather than a full bisection sweep.

    Raises
    ------
    UnsupportedThermodynamicDomain
        When no boiling root exists in [0, 1] — the state is not a two-phase melt.
    RuntimeError
        On non-convergence, reporting the final bracket residuals rather than returning a
        plausible-looking wrong answer.
    """
    _validate_temperature(temperature_k)
    _validate_pressure(pressure_bara)
    if not math.isfinite(mass_fraction_tolerance) or mass_fraction_tolerance <= 0.0:
        raise ValueError("mass fraction tolerance must be finite and positive")
    if not math.isfinite(pressure_tolerance_bara) or pressure_tolerance_bara <= 0.0:
        raise ValueError("pressure tolerance must be finite and positive")
    if not isinstance(max_iterations, int) or max_iterations <= 0:
        raise ValueError("max iterations must be a positive integer")

    low = 0.0
    high = 1.0
    a = a_urea_water_k
    residual_low = px_equilibrium_residual(low, temperature_k, pressure_bara, a_urea_water_k=a)
    residual_high = px_equilibrium_residual(high, temperature_k, pressure_bara, a_urea_water_k=a)
    if abs(residual_low) <= pressure_tolerance_bara:
        return low
    if abs(residual_high) <= pressure_tolerance_bara:
        return high
    if residual_low * residual_high > 0.0:
        raise UnsupportedThermodynamicDomain(
            "water-vapour equilibrium has no root within urea mass fraction [0, 1]"
        )

    # Ideal-water-activity inversion: x_w ~ P / Psat, converted back to a mass fraction.
    x_water_ideal = min(max(pressure_bara / water_psat_bara(temperature_k), 0.0), 1.0)
    denominator = ((1.0 - x_water_ideal) * MOLAR_MASS_UREA_G_MOL
                   + x_water_ideal * MOLAR_MASS_WATER_G_MOL)
    estimate = ((1.0 - x_water_ideal) * MOLAR_MASS_UREA_G_MOL / denominator
                if denominator > 0.0 else 0.5)
    estimate = min(max(estimate, low), high)

    for _ in range(max_iterations):
        residual_estimate = px_equilibrium_residual(
            estimate, temperature_k, pressure_bara, a_urea_water_k=a)
        if abs(residual_estimate) <= pressure_tolerance_bara:
            return estimate

        # Keep the bracket around the root, whichever side the estimate landed on.
        if residual_low * residual_estimate > 0.0:
            low = estimate
            residual_low = residual_estimate
        else:
            high = estimate
            residual_high = residual_estimate
        if high - low <= mass_fraction_tolerance:
            return (low + high) / 2.0

        # Numerical derivative, taken inside the bracket so it cannot step out of it.
        derivative_step = min(1.0e-4, 0.25 * (high - low))
        left = max(low, estimate - derivative_step)
        right = min(high, estimate + derivative_step)
        derivative = None
        if right > left:
            derivative = (
                px_equilibrium_residual(right, temperature_k, pressure_bara, a_urea_water_k=a)
                - px_equilibrium_residual(left, temperature_k, pressure_bara, a_urea_water_k=a)
            ) / (right - left)
        # The residual falls with urea fraction, so only a NEGATIVE derivative is physical;
        # anything else means the local slope is noise and bisection is safer.
        newton = (estimate - residual_estimate / derivative
                  if derivative is not None and derivative < 0.0 else math.nan)
        estimate = newton if low < newton < high else (low + high) / 2.0

    raise RuntimeError(
        "urea-water P-x solve did not converge within "
        f"{max_iterations} iterations; final bracket residuals "
        f"{residual_low:.6g}, {residual_high:.6g} bar"
    )


# ======================================================================================
# Fast path — a lazily populated grid over the exact solve
# ======================================================================================

#: Grid cell size. 0.05 K x 0.00025 bar is fine enough that bilinear interpolation across a
#: cell is well below the model's own uncertainty, and coarse enough that a dynamic
#: trajectory revisits cells instead of solving every tick.
_FAST_T_STEP_K = 0.05
_FAST_P_STEP_BARA = 0.00025


@lru_cache(maxsize=32768)
def _fast_grid_node(temperature_index: int, pressure_index: int,
                    a_urea_water_k: float | None = None) -> float:
    """One exact solve at a grid corner, cached for reuse."""
    temperature_k = VALID_TEMPERATURE_K[0] + temperature_index * _FAST_T_STEP_K
    pressure_bara = VALID_PRESSURE_BARA[0] + pressure_index * _FAST_P_STEP_BARA
    if a_urea_water_k is None:
        return solve_urea_mass_fraction(temperature_k, pressure_bara)
    return solve_urea_mass_fraction(temperature_k, pressure_bara, a_urea_water_k=a_urea_water_k)


def solve_urea_mass_fraction_fast(temperature_k: float,
                                  pressure_bara: float, *,
                                  a_urea_water_k: float | None = None) -> float:
    """Cached local bilinear interpolation of the exact UNIQUAC root.

    Process utility
    ---------------
    The evaporator model evaluates this inside a Picard loop on every tick. Cells are
    populated lazily from the exact solver, so a trajectory entering a new cell pays for
    four solves and every repeat is a table lookup.

    If a cell corner has no boiling root, the **exact** query is used instead of
    interpolating through the gap — so a phase-domain error stays explicit rather than
    being smoothed into a plausible number. A refitted ``a_urea_water_k`` has its own grid.
    """
    _validate_temperature(temperature_k)
    _validate_pressure(pressure_bara)
    t_low, t_high = VALID_TEMPERATURE_K
    p_low, p_high = VALID_PRESSURE_BARA
    t_index = int(math.floor((temperature_k - t_low) / _FAST_T_STEP_K))
    p_index = int(math.floor((pressure_bara - p_low) / _FAST_P_STEP_BARA))
    # At the exact top of the range the floor lands on the last corner, which has no
    # neighbour above it; step back one cell so the interpolation still has four corners.
    if temperature_k >= t_high:
        t_index -= 1
    if pressure_bara >= p_high:
        p_index -= 1
    t_index = max(t_index, 0)
    p_index = max(p_index, 0)
    t0 = t_low + t_index * _FAST_T_STEP_K
    p0 = p_low + p_index * _FAST_P_STEP_BARA
    ft = min(max((temperature_k - t0) / _FAST_T_STEP_K, 0.0), 1.0)
    fp = min(max((pressure_bara - p0) / _FAST_P_STEP_BARA, 0.0), 1.0)
    a = a_urea_water_k
    try:
        if a is None:
            w00 = _fast_grid_node(t_index, p_index)
            w10 = _fast_grid_node(t_index + 1, p_index)
            w01 = _fast_grid_node(t_index, p_index + 1)
            w11 = _fast_grid_node(t_index + 1, p_index + 1)
        else:
            w00 = _fast_grid_node(t_index, p_index, a)
            w10 = _fast_grid_node(t_index + 1, p_index, a)
            w01 = _fast_grid_node(t_index, p_index + 1, a)
            w11 = _fast_grid_node(t_index + 1, p_index + 1, a)
    except UnsupportedThermodynamicDomain:
        if a is None:
            return solve_urea_mass_fraction(temperature_k, pressure_bara)
        return solve_urea_mass_fraction(temperature_k, pressure_bara, a_urea_water_k=a)
    w0 = w00 + ft * (w10 - w00)
    w1 = w01 + ft * (w11 - w01)
    return w0 + fp * (w1 - w0)


def fast_solver_cache_clear() -> None:
    """Drop the grid. Used when a scenario resets the plant."""
    _fast_grid_node.cache_clear()


def fast_solver_cache_info():
    """`functools` cache statistics for the grid, for diagnostics."""
    return _fast_grid_node.cache_info()


__all__ = [
    "MODEL_NAME",
    "VALID_PRESSURE_BARA",
    "VALID_TEMPERATURE_K",
    "SOURCE_VALID_PRESSURE_BARA",
    "SOURCE_VALID_TEMPERATURE_K",
    "MOLAR_MASS_WATER_G_MOL",
    "MOLAR_MASS_UREA_G_MOL",
    "UnsupportedThermodynamicDomain",
    "ln_gamma",
    "mole_fractions_from_urea_mass_fraction",
    "px_equilibrium_residual",
    "fast_solver_cache_clear",
    "fast_solver_cache_info",
    "solve_urea_mass_fraction",
    "solve_urea_mass_fraction_fast",
    "validity_status",
    "water_activity",
    "water_psat_bara",
]
