"""Isenthalpic letdown of an inert-bearing NH3-CO2-H2O gas that condenses an ammonium-carbamate
liquor.

What this gives the plant model
-------------------------------
The outlet of a gas letdown whose gas can condense. A letdown valve is adiabatic and does no work,
so it is isenthalpic. While the gas stays above its dew point the outlet is the single-phase SRK
answer (`thermo.real_gas.isenthalpic_letdown`, V1's relation, kept verbatim). Below it, the
ammonia, carbon dioxide and water condense together as an ammonium-carbamate liquor, and the
heat they release holds the outlet up. The outlet then sits a few kelvin under the gas's dew
point, with a liquor flowing on beside the gas, instead of falling to a solver's bracket.

Decided by the process engineer on 2026-10-01 (handoff B-19): "Replace the artificial floor with
the true isenthalpic flash temperature down to the actual downstream pressure." V1's single-phase
solve returns T_in - 150 K whenever the enthalpy has no root inside that bracket, which on a
cooling loss upstream of HV-322604 put -36 C on the purge.

The phases
----------
Vapour: the SRK enthalpy of `real_gas` (the same function as the single-phase answer, so the two
agree where the liquor vanishes); ideal-gas equilibrium, the absorber beds' own basis at these
pressures. Liquor: NH3, CO2 and water on the Extended UNIQUAC speciation and the Henry constants
the LP absorber's beds stand on (`thermo.ammonia_backpressure`):

    y_NH3 P = p_NH3(m_N, m_C, T)
    y_CO2 P = p_CO2(m_N, m_C, T)
    y_H2O P = a_H2O(m_N, m_C, T) . psat(T)

The enthalpy balance, on the H0 elemental datum every stream is published on:

    n h_SRK(y, T_in, P_in) = V h_SRK(y_v, T, P_out)
                             + sum_i l_i h_i^ig(T) - l_NH3 dH_NH3 - l_CO2 dH_CO2 - l_H2O lambda(T)

the liquor priced as the vapour it came from less its differential heats of absorption (the
back-pressure's own van 't Hoff slope, the heats 322C001 charges its beds' uptake at) and water's
latent heat.

Method
------
  1. The single-phase answer T1, V1's.
  2. The dew test, walked down from T_in to T1 in 10 K steps: the incipient liquor whose NH3
     and CO2 pressures equal the gas's. While it holds its water back harder than the gas
     carries it, a_H2O psat > y_H2O P, no liquor forms; dry down to T1, T1 stands — the design
     point is V1's to the bit.
  3. Otherwise the root in T of the two-phase enthalpy less the inlet's, between the last dry
     and the first wet step of the walk, closed by Illinois regula falsi. Each evaluation is
     an isothermal flash, Newton on (ln m_N, ln m_C, ln W), W the liquor's water, from fixed
     starts and the nearest temperature's answer, solved per mole of gas, so the result is a
     function of the composition alone.
  4. An isothermal flash that converges from none of its starts has no liquor within the model's
     range at that temperature: the solve stops there, and the outlet is the single-phase answer
     flagged not converged — as it is when the walk brackets no root (handoff A-18, session 40).
  5. A gas left dry — no liquor in the model's range — that stands above solid ammonium
     carbamate's saturation at its outlet deposits the solid (handoff B-79 (b), decided
     2026-10-14): 2 NH3 + CO2 -> NH2COONH4(s) until p_NH3^2 p_CO2 = Kp(T), the outlet temperature
     and the deposit solved together on the enthalpy balance,

         n h_SRK(y, T_in, P_in) = V h_SRK(y_v, T, P_out) + s h_carbamate(s)(T)
         ln(p_NH3^2 p_CO2) = ln Kp(T),   Kp = (4/27) P_diss^3,   log10 P_diss = 8.2697 - 2741.9 / T

     P_diss Egan, Potts and Potts's dissociation pressure [bar, K], the solid's enthalpy Voskov and
     Voronin's (`thermo.enthalpy`, -645.05 kJ/mol at 298.15 K). The heat the solid releases holds the
     outlet between the dry answer and the temperature the gas would just saturate at.

Scope, stated
-------------
* Solid ammonium carbamate is a phase only for a gas the liquor leaves dry (step 5): below its
  liquor's dew point the aqueous liquor is the answer, as before. Ideal-gas partial pressures, the
  beds' own basis.
* The speciation's parameters are regressed on dilute liquors at 10-100 C; the liquor condensed
  here is 110 to 230 mol NH3 per kg of water. The model is extrapolated, and declared so.
* A CO2-rich purge carrying almost no water — 322E003's vent on a lost motive, 30 to 70 % CO2 and
  0.1 to 0.3 % water — needs a liquor holding its water at a_H2O near 0.1 or below; its incipient
  liquor leaves the model's range (1000 mol per kg of water) before it gets there, no isothermal
  flash converges, the solve stops at step 4, and the outlet is the dry answer, flagged — unless it
  stands above the solid's saturation, when step 5 deposits it; the purge valve raises its
  deposition alarm either way.
* Every node the flash reads is served from the liquid-state store
  (`ammonia_backpressure.build_state_store`), so no call tabulates the grid; without a store the
  first call in a new region tabulates it, seconds once. A call repeated with the same arguments
  (a steady purge) is answered from a cache.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ureasim.thermo import enthalpy as h0
from ureasim.thermo import iapws
from ureasim.thermo import real_gas
from ureasim.thermo.ammonia_backpressure import liquid_state, liquor_heat_of_absorption_j_mol
from ureasim.thermo.domains import MW
from ureasim.thermo.parameters import M_W

#: The species that condense into the liquor.
CONDENSABLE = ("NH3", "CO2", "H2O")

#: Pascals per bar.
_PA = 1.0e5

#: The Newton solves: the residual tolerance on the logarithms of the pressures [-], the
#: iteration cap, the finite-difference step [-], the step-halving cap of the line search, and
#: the bound on a logarithmic unknown, which keeps every exponential finite.
NEWTON_TOL = 1.0e-10
NEWTON_ITERS = 60
FD_STEP = 1.0e-6
LINE_SEARCH_HALVINGS = 40
LN_BOUND = 40.0

#: The lowest temperature water's saturation line is read at [deg C]: its triple point. A liquor
#: below 0 C is held at it, as `real_gas` holds its water-condensation flag.
T_PSAT_MIN_C = 0.01

#: The most concentrated liquor considered [mol/kg water], NH3 or CO2: past it the speciation is
#: asked for a liquor with almost no water, and a gas that would need one is condensing.
MOLAL_MAX = 1000.0

#: The incipient liquor's starting molalities [mol/kg water], NH3 and CO2, tried in turn after
#: the nearest temperature's answer: a cooling-loss purge's first drop runs from 40 to 330 mol of
#: NH3 per kg of water between 90 and 75 C, too wide a span for one start.
DEW_GUESSES_MOLAL = ((20.0, 5.0), (100.0, 40.0), (400.0, 160.0), (5.0, 1.0))

#: The isothermal flash's starting water condensed, as fractions of the water in the gas [-],
#: tried in turn after the nearest temperature's answer.
W_GUESS_FRACTIONS = (1.0e-3, 1.0e-1, 0.5)

#: The outer solve: the temperature tolerance [K] and the iteration cap; the step the bracket is
#: walked down by from the inlet temperature [K] (the outlet sits a few kelvin under the dew
#: point, so the walk is short, and a step above the dew point costs only a dew test), and the
#: most steps taken past the single-phase answer.
T_TOL_K = 1.0e-6
OUTER_ITERS = 100
BRACKET_STEP_K = 10.0
BRACKET_WIDENINGS = 8

#: The most results kept, keyed on the exact call: a steady purge repeats its call every tick.
CACHE_SIZE = 256
_CACHE: dict = {}

#: Solid ammonium carbamate's dissociation pressure [bar] at temperature T [K], over the solid at its
#: own stoichiometry, 2 NH3 + CO2: log10 P = A - B / T. Source: E. P. Egan Jr., J. E. Potts Jr. and
#: G. D. Potts, "Dissociation pressure of ammonium carbamate", Ind. Eng. Chem. 38 (1946) 454-456
#: (1 atm at 58.7 C, 89 Torr at 25 C); admitted by the process engineer on 2026-10-14 (handoff B-79).
CARBAMATE_DISSOC_A = 8.2697
CARBAMATE_DISSOC_B_K = 2741.9

#: Bisection budgets of the solid's two solves: the deposit at a temperature, the temperature.
SOLID_ITERS = 80


@dataclass(frozen=True)
class LetdownFlash:
    """The outlet of one letdown."""

    #: The outlet temperature [deg C].
    t_out_c: float
    #: The gas and the condensed liquor leaving the valve [kmol/h]; the liquor NH3, CO2, H2O.
    vapour_kmolh: dict
    liquor_kmolh: dict
    #: True when a liquor condenses.
    condensing: bool
    #: V1's single-phase answer [deg C], which this replaces below the dew point.
    t_single_phase_c: float
    #: True unless a solve stopped on its cap.
    converged: bool
    #: Solid ammonium carbamate deposited in the line [kmol/h of carbamate] (step 5, B-79 (b)).
    solid_kmolh: float = 0.0


# ======================================================================================
# The numerics
# ======================================================================================

def _solve_linear(a: list, b: list) -> list | None:
    """Gaussian elimination with partial pivoting on a small dense system; None if singular."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(m[r][c]))
        if abs(m[piv][c]) < 1.0e-300:
            return None
        m[c], m[piv] = m[piv], m[c]
        for r in range(n):
            if r != c:
                f = m[r][c] / m[c][c]
                for k in range(c, n + 1):
                    m[r][k] -= f * m[c][k]
    return [m[i][n] / m[i][i] for i in range(n)]


def _newton(f, x0: list) -> tuple[list, bool]:
    """Damped Newton on ``f(x) = 0`` with a forward-difference Jacobian. ``f`` returns None for
    an infeasible point, which the line search backs away from. Returns (x, converged)."""
    x = list(x0)
    fx = f(x)
    if fx is None:
        return x, False
    for _ in range(NEWTON_ITERS):
        norm = max(abs(v) for v in fx)
        if norm < NEWTON_TOL:
            return x, True
        cols = []
        for j in range(len(x)):
            xp = list(x)
            xp[j] += FD_STEP
            fp = f(xp)
            if fp is None:
                xp[j] = x[j] - FD_STEP
                fp = f(xp)
                if fp is None:
                    return x, False
                cols.append([(fx[i] - fp[i]) / FD_STEP for i in range(len(x))])
            else:
                cols.append([(fp[i] - fx[i]) / FD_STEP for i in range(len(x))])
        jac = [[cols[j][i] for j in range(len(x))] for i in range(len(x))]
        dx = _solve_linear(jac, [-v for v in fx])
        if dx is None:
            return x, False
        lam, n0 = 1.0, sum(v * v for v in fx)
        for _ in range(LINE_SEARCH_HALVINGS):
            xn = [min(max(x[i] + lam * dx[i], -LN_BOUND), LN_BOUND) for i in range(len(x))]
            fn = f(xn)
            if fn is not None and sum(v * v for v in fn) < n0:
                break
            lam *= 0.5
        else:
            return x, False
        x, fx = xn, fn
    return x, max(abs(v) for v in fx) < NEWTON_TOL


# ======================================================================================
# The liquor
# ======================================================================================

def _liquor_w(m_n: float, m_c: float) -> dict:
    """Mass fractions of a liquor of molalities ``m_n``, ``m_c`` [mol/kg water]."""
    a, b = m_n * MW["NH3"] / 1000.0, m_c * MW["CO2"] / 1000.0
    tot = 1.0 + a + b
    return {"NH3": a / tot, "CO2": b / tot, "H2O": 1.0 / tot}


def _held_back_pa(m_n: float, m_c: float, t_c: float) -> tuple[float, float, float] | None:
    """(p_NH3, p_CO2, p_H2O) [Pa] the liquor of molalities ``m_n``, ``m_c`` holds back at ``t_c``;
    None past `MOLAL_MAX` or where the speciation has no solution.

    Process utility
    ---------------
    The liquor's side of the equilibrium: what the gas must carry for the liquor to stand.
    """
    if max(m_n, m_c) > MOLAL_MAX:
        return None
    try:
        p_n, p_c, a_w = liquid_state(_liquor_w(m_n, m_c), t_c)
    except (ValueError, ArithmeticError):
        return None
    return p_n, p_c, a_w * iapws.psat_bara(max(t_c, T_PSAT_MIN_C)) * _PA


def incipient_liquor(y: dict, t_c: float, p_bara: float,
                     guess: list | None = None) -> tuple[float, float, float] | None:
    """The first drop a gas of mole fractions ``y`` could condense at ``t_c``: (m_NH3, m_CO2,
    p_H2O held back [Pa]); None when no liquor within `MOLAL_MAX` matches the gas. ``guess``,
    the logarithms of a nearby answer's molalities, is tried before `DEW_GUESSES_MOLAL`.

    Process utility
    ---------------
    The liquor whose NH3 and CO2 pressures equal the gas's. Whether it can stand is the water's
    question: only if it holds its water back no harder than the gas carries it,
    a_H2O psat <= y_H2O P. A gas so far below its dew point that no liquor within `MOLAL_MAX`
    matches it is condensing.

    Equations
    ---------
        p_NH3(m, T) = y_NH3 P,   p_CO2(m, T) = y_CO2 P            Newton on ln m
    """
    ln_tn = math.log(y["NH3"] * p_bara * _PA)
    ln_tc = math.log(y["CO2"] * p_bara * _PA)

    def f(u):
        held = _held_back_pa(math.exp(u[0]), math.exp(u[1]), t_c)
        if held is None:
            return None
        return [math.log(held[0]) - ln_tn, math.log(held[1]) - ln_tc]

    starts = ([guess] if guess else []) + [[math.log(a), math.log(b)]
                                           for a, b in DEW_GUESSES_MOLAL]
    for start in starts:
        u, ok = _newton(f, start)
        if ok:
            m_n, m_c = math.exp(u[0]), math.exp(u[1])
            return m_n, m_c, _held_back_pa(m_n, m_c, t_c)[2]
    return None


def isothermal_liquor(z: dict, t_c: float, p_bara: float,
                      guesses: list) -> tuple[dict, list, bool]:
    """The liquor a gas of feed ``z`` [kmol/h] condenses at ``t_c`` and ``p_bara`` [kmol/h],
    Newton from each of ``guesses`` in turn until one converges.

    Process utility
    ---------------
    How much ammonia, carbon dioxide and water the line holds as liquor at a given temperature,
    every gas species not in `CONDENSABLE` staying in the vapour.

    Equations
    ---------
    Unknowns ln m_NH3, ln m_CO2, ln W (W the liquor's water, kmol/h):

        l_NH3 = m_NH3 W M_w,   l_CO2 = m_CO2 W M_w,   l_H2O = W,   v_i = z_i - l_i
        ln(v_i P / V) = ln p_i(m, T)                                   i = NH3, CO2, H2O

    Returns (liquor, unknowns, converged).
    """
    inert = sum(v for k, v in z.items() if k not in CONDENSABLE)
    p_pa = p_bara * _PA

    def liquor(u):
        mn, mc, wat = math.exp(u[0]), math.exp(u[1]), math.exp(u[2])
        return mn, mc, {"NH3": mn * wat * M_W, "CO2": mc * wat * M_W, "H2O": wat}

    def f(u):
        mn, mc, liq = liquor(u)
        v = {k: z.get(k, 0.0) - liq[k] for k in CONDENSABLE}
        if min(v.values()) <= 0.0:
            return None
        held = _held_back_pa(mn, mc, t_c)
        if held is None:
            return None
        vap = inert + sum(v.values())
        return [math.log(v[k] * p_pa / vap) - math.log(held[i])
                for i, k in enumerate(CONDENSABLE)]

    u, ok = guesses[0], False
    for start in guesses:
        u, ok = _newton(f, start)
        if ok:
            break
    return liquor(u)[2], u, ok


def two_phase_enthalpy(z: dict, liq: dict, t_c: float, p_bara: float) -> float:
    """The enthalpy of feed ``z`` [kmol/h] as gas and liquor ``liq`` at ``t_c`` [J/mol x kmol/h].

    Process utility
    ---------------
    The left side of the letdown's balance once a liquor stands: the gas on SRK, the liquor as
    the vapour it condensed from less its heats of absorption and water's latent heat.
    """
    t_k = t_c + 273.15
    vap = {k: z.get(k, 0.0) - liq.get(k, 0.0) for k in z}
    n_v = sum(v for v in vap.values() if v > 0.0)
    h = real_gas.h_molar({k: v / n_v for k, v in vap.items() if v > 0.0}, t_k,
                         p_bara * _PA) * n_v
    m_l = {k: liq[k] * MW[k] for k in CONDENSABLE}
    m_tot = sum(m_l.values())
    if m_tot <= 0.0:
        return h
    dh_n, dh_c = liquor_heat_of_absorption_j_mol({k: v / m_tot for k, v in m_l.items()}, t_c)
    lat_w = h0.h_species("H2O", "gas", t_k) - h0.h_species("H2O", "liquid", t_k)
    for k in CONDENSABLE:
        h += liq[k] * h0.h_species(k, h0.reference_phase(k, "vapour"), t_k)
    return h - liq["NH3"] * dh_n - liq["CO2"] * dh_c - liq["H2O"] * lat_w


# ======================================================================================
# The letdown
# ======================================================================================

def _no_liquor() -> dict:
    return {k: 0.0 for k in CONDENSABLE}


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


def solid_deposit(comp: dict, t_in_c: float, p_in_bara: float, p_out_bara: float,
                  t_dry_c: float) -> tuple[float, float] | None:
    """A dry gas's outlet above solid carbamate's saturation: (outlet [deg C], solid [kmol/h]).

    Process utility
    ---------------
    A CO2-rich purge the liquor leaves dry — 322E003's vent on a lost motive — lays solid carbamate
    in HV-322604's line, and the heat it releases holds the outlet up (handoff B-79 (b), decided
    2026-10-14). None when the dry outlet ``t_dry_c`` stands at or below the solid's saturation.

    Equation in the module docstring (step 5): bisection in T between the dry outlet, where the
    deposit's heat leaves the balance short, and the temperature the gas just saturates at, where
    nothing deposits; at each T the deposit that brings the gas onto Kp(T), by bisection.
    """
    n = sum(comp.values())
    if n <= 0.0 or comp.get("NH3", 0.0) <= 0.0 or comp.get("CO2", 0.0) <= 0.0:
        return None
    y = {k: v / n for k, v in comp.items()}
    if _supersaturation(y, 0.0, t_dry_c, p_out_bara) <= 0.0:
        return None
    h_in = real_gas.h_molar(y, t_in_c + 273.15, p_in_bara * _PA)

    def short(t_c: float) -> float:
        s = _deposit_at(y, t_c, p_out_bara)
        t_k = t_c + 273.15
        return h_in - ((1.0 - 3.0 * s) * real_gas.h_molar(_less_deposit(y, s), t_k,
                                                           p_out_bara * _PA)
                       + s * h0.h_species("Carbamate", "solid", t_k))

    lo, hi = t_dry_c, t_dry_c
    while _supersaturation(y, 0.0, hi, p_out_bara) > 0.0:
        hi += BRACKET_STEP_K
    for _ in range(SOLID_ITERS):
        mid = 0.5 * (lo + hi)
        if short(mid) > 0.0:
            lo = mid
        else:
            hi = mid
        if hi - lo <= T_TOL_K:
            break
    t_out = 0.5 * (lo + hi)
    return t_out, _deposit_at(y, t_out, p_out_bara) * n


class _NoLiquor(Exception):
    """An isothermal flash found no liquor within the model's range (method step 4)."""


def letdown(comp_kmolh: dict, t_in_c: float, p_in_bara: float, p_out_bara: float) -> LetdownFlash:
    """The outlet of an isenthalpic letdown from (``t_in_c``, ``p_in_bara``) to ``p_out_bara``.

    Process utility
    ---------------
    HV-322604's outlet: the temperature the purge reaches 322C001 at, and the carbamate liquor
    the line carries there when the purge turns ammonia-rich on a cooling loss in 322E003.

    Method in the module docstring. A gas without both NH3 and CO2 builds no carbamate liquor,
    and its outlet is the single-phase answer.
    """
    comp = {k: v for k, v in comp_kmolh.items() if k in real_gas.SPECIES and v > 0.0}
    key = (tuple(sorted(comp.items())), t_in_c, p_in_bara, p_out_bara)
    hit = _CACHE.get(key)
    if hit is not None:
        return hit

    t1 = real_gas.isenthalpic_letdown(comp, t_in_c, p_in_bara, p_out_bara)["t_out_c"]
    result = LetdownFlash(t_out_c=t1, vapour_kmolh=dict(comp), liquor_kmolh=_no_liquor(),
                          condensing=False, t_single_phase_c=t1, converged=True)
    n = sum(comp.values())
    if n > 0.0 and p_out_bara < p_in_bara and "NH3" in comp and "CO2" in comp:
        y = {k: v / n for k, v in comp.items()}
        # The dew search: down from the inlet temperature in steps, warm-started down the walk,
        # to the first temperature the gas condenses at; dry down to T1, T1 stands. Walking from
        # the top never asks the speciation about a liquor colder than the gas condenses.
        p_w = y.get("H2O", 0.0) * p_out_bara * _PA
        t, t_dry, near = max(t_in_c, t1), None, None
        while True:
            drop = incipient_liquor(y, t, p_out_bara, near)
            if drop is None or drop[2] <= p_w:
                # Solved per mole of gas, so the outlet is a function of the composition alone.
                t_out, liq, ok = _two_phase(y, t_in_c, p_in_bara, p_out_bara, t, t_dry)
                if liq is None:
                    result = _dry(comp, t_in_c, p_in_bara, p_out_bara, t1, converged=False)
                else:
                    liquor = {k: v * n for k, v in liq.items()}
                    result = LetdownFlash(
                        t_out_c=t_out,
                        vapour_kmolh={k: v - liquor.get(k, 0.0) for k, v in comp.items()},
                        liquor_kmolh=liquor, condensing=any(v > 0.0 for v in liquor.values()),
                        t_single_phase_c=t1, converged=ok)
                break
            if t <= t1:
                result = _dry(comp, t_in_c, p_in_bara, p_out_bara, t1, converged=True)
                break
            near = [math.log(drop[0]), math.log(drop[1])]
            t_dry, t = t, max(t - BRACKET_STEP_K, t1)

    if len(_CACHE) >= CACHE_SIZE:
        _CACHE.clear()
    _CACHE[key] = result
    return result


def _dry(comp: dict, t_in_c: float, p_in_bara: float, p_out_bara: float, t1: float,
         converged: bool) -> LetdownFlash:
    """A gas no liquor condenses from: the single-phase answer, or the solid it deposits (step 5)."""
    solid = solid_deposit(comp, t_in_c, p_in_bara, p_out_bara, t1)
    if solid is None:
        return LetdownFlash(t_out_c=t1, vapour_kmolh=dict(comp), liquor_kmolh=_no_liquor(),
                            condensing=False, t_single_phase_c=t1, converged=converged)
    t_out, s = solid
    vapour = dict(comp)
    vapour["NH3"] -= 2.0 * s
    vapour["CO2"] -= s
    return LetdownFlash(t_out_c=t_out, vapour_kmolh=vapour, liquor_kmolh=_no_liquor(),
                        condensing=False, t_single_phase_c=t1, converged=True, solid_kmolh=s)


def _two_phase(y: dict, t_in_c: float, p_in_bara: float, p_out_bara: float, t_wet: float,
               t_dry: float | None) -> tuple[float, dict | None, bool]:
    """The outlet of one mole of gas ``y`` once the dew search has found it condensing at
    ``t_wet`` and dry at ``t_dry`` (None when it condenses at the inlet temperature already):
    (temperature, liquor per mole of gas or None when no root is bracketed or a flash finds no
    liquor, converged)."""
    try:
        return _two_phase_root(y, t_in_c, p_in_bara, p_out_bara, t_wet, t_dry)
    except _NoLiquor:
        return t_wet, None, False


def _two_phase_root(y: dict, t_in_c: float, p_in_bara: float, p_out_bara: float, t_wet: float,
                    t_dry: float | None) -> tuple[float, dict | None, bool]:
    """`_two_phase`'s bracket and regula falsi; raises `_NoLiquor` at a flash with no answer."""
    h_in = real_gas.h_molar(y, t_in_c + 273.15, p_in_bara * _PA)
    w_logs = [math.log(max(y.get("H2O", 0.0), 1.0e-12) * f) for f in W_GUESS_FRACTIONS]
    state = {"u": None}

    def g(t_c: float) -> tuple[float, dict]:
        """The two-phase enthalpy less the inlet's at ``t_c``, and the liquor there."""
        near = state["u"][:2] if state["u"] is not None else None
        drop = incipient_liquor(y, t_c, p_out_bara, near)
        if drop is not None and drop[2] > y.get("H2O", 0.0) * p_out_bara * _PA:
            return real_gas.h_molar(y, t_c + 273.15, p_out_bara * _PA) - h_in, _no_liquor()
        guesses = [state["u"]] if state["u"] is not None else []
        mol = ([[math.log(drop[0]), math.log(drop[1])]] if drop is not None else []) + [
            [math.log(a), math.log(b)] for a, b in DEW_GUESSES_MOLAL]
        guesses += [m + [w] for m in mol for w in w_logs]
        liq, u, ok = isothermal_liquor(y, t_c, p_out_bara, guesses)
        if not ok:
            raise _NoLiquor
        state["u"] = u
        return two_phase_enthalpy(y, liq, t_c, p_out_bara) - h_in, liq

    # The bracket: the dry end above (raised in steps while it falls short), the wet end walked
    # down in steps until the two-phase enthalpy falls short of the inlet's.
    hi = t_wet + BRACKET_STEP_K if t_dry is None else t_dry
    f_hi, _ = g(hi)
    for _ in range(BRACKET_WIDENINGS):
        if f_hi > 0.0:
            break
        hi += BRACKET_STEP_K
        f_hi, _ = g(hi)
    lo = t_wet
    f_lo, liq = g(lo)
    for _ in range(BRACKET_WIDENINGS):
        if f_lo < 0.0:
            break
        hi, f_hi = lo, f_lo
        lo -= BRACKET_STEP_K
        f_lo, liq = g(lo)
    if f_lo >= 0.0 or f_hi <= 0.0:
        return t_wet, None, False

    # Illinois regula falsi, as `real_gas.isenthalpic_letdown` solves the single-phase answer.
    side, t, t_prev = 0, lo, hi
    for _ in range(OUTER_ITERS):
        t = (lo * f_hi - hi * f_lo) / (f_hi - f_lo)
        r, liq = g(t)
        if r == 0.0 or abs(t - t_prev) <= T_TOL_K:
            break
        t_prev = t
        if r < 0.0:
            lo, f_lo = t, r
            if side == 1:
                f_hi *= 0.5
            side = 1
        else:
            hi, f_hi = t, r
            if side == -1:
                f_lo *= 0.5
            side = -1
    return t, dict(liq), True


__all__ = [
    "CONDENSABLE", "T_PSAT_MIN_C", "NEWTON_TOL", "NEWTON_ITERS", "FD_STEP",
    "LINE_SEARCH_HALVINGS", "LN_BOUND", "MOLAL_MAX", "DEW_GUESSES_MOLAL", "W_GUESS_FRACTIONS",
    "T_TOL_K", "OUTER_ITERS", "BRACKET_STEP_K", "BRACKET_WIDENINGS", "CACHE_SIZE",
    "LetdownFlash", "incipient_liquor", "isothermal_liquor", "two_phase_enthalpy",
    "letdown",
]
