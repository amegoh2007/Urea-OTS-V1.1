"""Bubble points and partial pressures of the NH3-CO2-H2O-urea liquors.

Equipment served
----------------
Every stage in the plant where a liquor decides what temperature it boils at:

    323C003 / 323F004 / 323F010   the LP recirculation and flash train
    328C002 / 328C003 / 328C004   desorption and hydrolysis
    322C001                       the LP absorber's equilibrium line
    324 vacuum condensers         the NH3 and CO2 partial pressures in each vent

What this replaced, and the size of the error
---------------------------------------------
The live engine used ``tsat_steam(P)`` — a **pure-water** saturation line with a frozen
offset — for the 323C003 and 323F004 bubble points, with a comment conceding the point in
writing.

At the 323C003 design state the pure-water saturation temperature at 4.1 bar a is 144 C;
the column actually runs at 135 C. The 9 C gap is the NH3 and CO2 partial pressure a
water-only model cannot see.

Worse than the offset — which the departure form absorbs — is the **slope**. A water-only
anchor makes the bubble point respond *only to pressure*, so a change in the liquor's NH3
or CO2 loading, which is what every stripping, absorption and recycle upset in this plant
does, moved the bubble point by **exactly zero**.

The equation
------------
    P_bub(T) = f_dil [ a_NH3 H_NH3(T) + a_CO2 H_CO2(T) + a_H2O Psat_H2O(T) ]
               + sum_j x_j H_j(T)                                  j over the inerts

    a_i    activities from the full Extended UNIQUAC gamma on the R1-R5 speciation,
           interpolated from `thermo.vle_grid`
    H_i    Rumpf & Maurer for NH3 and CO2; IAPWS G7-04 for N2, O2, CH4, H2
    Psat   IAPWS-IF97, evaluated ANALYTICALLY at the live temperature
    f_dil  urea and biuret are non-volatile and are not in the electrolyte parameter set,
           so they enter the only way they physically can at this concentration: as a
           mole-fraction diluent on every partial pressure

``f_dil`` is the same Raoult-on-the-non-volatiles term the empirical bubble point uses for
the urea-only stages, so **the two models agree in the limit where the volatiles vanish** —
the consistency check that matters at the boundary between the 323 and 324 domains.

Validation — no fitted parameter anywhere in the chain
-------------------------------------------------------
Evaluated on the engine's own composition vectors, through the tabulated path the engine
actually calls:

    stage     liquor (PFD mass %)                    T (C)   P_model   P_PFD   error
    323C003   68.74 U / 0.36 B / 2.13 N / 1.05 C     135     4.3516    4.10    +6.1 %
    323F004   71.74 U / 0.37 B / 0.88 N / 0.66 C     106     1.2993    1.13    +15.0 %
    323F010   80.00 U / 0.42 B / 0.08 N / 0.02 C      99     0.4683    0.46    +1.8 %

323F004 is the loosest because it is the stage where the CO2 term dominates, and CO2 is
where this model is weakest: at 0.66 wt% CO2 the carbamate equilibrium is steep, and urea —
72 % of the liquor — is a diluent here rather than a UNIQUAC species, so it dilutes the
volatiles without shifting their activity coefficients. Tracked as `handoff.md` B-2.

Why those offsets are acceptable: every call site uses the **departure form**
``T_des + [T_bub(live) - T_bub(design)]``, so the residual cancels identically at the
design point and the model supplies only the slope. For comparison the pure-water anchor
gives 103.3 C at 323F004's 1.13 bar against an actual 106 C — and responds to composition
with a derivative of exactly zero.

Honest limitation
-----------------
``in_grid`` reports whether a state was actually **solved** rather than clamped. The
interpolator clamps at the envelope edges rather than extrapolating, so an out-of-envelope
call silently returns an edge node. Callers that would otherwise mistake that for a solve
must check the flag; `thermo.service` refuses on it.

Ported from V1 `backend/vle_nh3co2h2o.py` (physics half). Numerically identical.
"""

from __future__ import annotations

import math

from ureasim.thermo import iapws
from ureasim.thermo import properties as props
from ureasim.thermo import vle_grid
from ureasim.thermo.vle_grid import _clamp, in_box, interp, sf_to_loadings

#: Molar masses of every species the engine's liquor vectors carry [g/mol].
MW = {"Urea": 60.056, "Biuret": 103.081, "NH3": 17.0304,
      "CO2": 44.0095, "H2O": 18.0153, "HCHO": 30.026,
      "N2": 28.0134, "O2": 31.9988, "CH4": 16.0425, "H2": 2.01588}

#: Species with no vapour pressure at these conditions. They dilute, and nothing else.
NONVOLATILE = ("Urea", "Biuret", "HCHO")

#: The synthesis loop's four permanent gases.
INERTS = ("N2", "O2", "CH4", "H2")

MODEL_NAME = ("Extended UNIQUAC NH3-CO2-H2O electrolyte gamma-phi VLE "
              "(Thomsen-Rasmussen / Darde) + non-volatile urea dilution "
              "+ IAPWS G7-04 Henry inerts")

#: Pressure range this module is usable over. There is deliberately NO pressure AXIS on
#: the table — see `thermo.vle_grid`. This bound is a statement about the VAPOUR side:
#:   * the SRK fugacity is an equation of state and is valid across the whole band
#:     (Z = 0.80 and phi_N2 = 1.31 at 144 bar a, so it is doing real work up there);
#:   * the missing Poynting term is ~+15 % on an NH3 or CO2 partial pressure at 144 bar and
#:     very nearly constant across the loop's band, so the anchored ratio form absorbs it.
#:     It does NOT cancel for an absolute bubble pressure, which is one more reason no
#:     absolute HP-loop number reaches the engine.
VALID_PRESSURE_BARA = (0.02, 180.0)


# ======================================================================================
# Coordinates and envelope
# ======================================================================================

def loadings(w: dict) -> tuple[float, float]:
    """Total NH3 and CO2 loading of a liquor, mol per kg of **water**.

    Retained as the diagnostic that names the old failure: for the 322E003 feed it returns
    869 and 258 against a table that used to stop at 16 and 7. Nothing in the interpolation
    path calls it any more — `coords` does — but the domain report still uses it, because
    "N = 54x the top node" is a far more legible way to say "no water left" than "s = 0.953".

    ``w`` is a mass-fraction vector, in 0-1 **or** in per cent; both are accepted because
    the ratios below are scale-free.
    """
    w_h2o = max(w.get("H2O", 0.0), 1e-9)
    n_load = (w.get("NH3", 0.0) / MW["NH3"]) / (w_h2o / MW["H2O"]) * (1000.0 / MW["H2O"])
    c_load = (w.get("CO2", 0.0) / MW["CO2"]) / (w_h2o / MW["H2O"]) * (1000.0 / MW["H2O"])
    return n_load, c_load


def coords(w: dict) -> tuple[float, float]:
    """Grid coordinates ``(s, f)`` of a liquor from its mass fractions.

    Computed from the MOLE COUNTS directly rather than through `loadings`, so a liquor with
    no water at all returns ``s = 1.0`` instead of dividing by zero. That state is off the
    top of the grid and `in_grid` says so — but it says so by comparing 1.0 with 0.98,
    rather than by propagating an infinity.
    """
    n_n = max(w.get("NH3", 0.0), 0.0) / MW["NH3"]
    n_c = max(w.get("CO2", 0.0), 0.0) / MW["CO2"]
    n_w = max(w.get("H2O", 0.0), 0.0) / MW["H2O"]
    tot = n_n + n_c + n_w
    if tot <= 0.0:
        return 0.0, 0.0
    return (n_n + n_c) / tot, (n_c / (n_n + n_c)) if (n_n + n_c) > 0.0 else 0.0


def envelope() -> dict:
    """The tabulated envelope, as bounds a caller can test or report without the nodes."""
    t_nodes, s_nodes, f_nodes = vle_grid.nodes()
    return {"t_c": (t_nodes[0], t_nodes[-1]),
            "s": (s_nodes[0], s_nodes[-1]),
            "f": (f_nodes[0], f_nodes[-1]),
            "p_bara": VALID_PRESSURE_BARA,
            "n_load_at_s_max": sf_to_loadings(s_nodes[-1], f_nodes[0])[0],
            "c_load_at_s_max": sf_to_loadings(s_nodes[-1], f_nodes[-1])[1]}


def in_grid(w: dict, t_c: float) -> bool:
    """Is this state actually SOLVED here, or would it be clamped?

    The same test `partial_pressures_bara` reports, but without the Henry constants and the
    IF97 saturation line — the coordinates and the corner flags are all it needs. The flash
    service calls this once per K-value evaluation, so paying for a full partial-pressure
    vector to answer a yes/no question showed up directly in the tick budget: 35 us against
    9 us, four times per tick per wired unit.
    """
    s, f = coords(w)
    if not in_box(t_c, s, f):
        return False
    return interp(t_c, s, f)[4]


# ======================================================================================
# Partial pressures and bubble point
# ======================================================================================

def partial_pressures_bara(w: dict, t_c: float) -> dict:
    """Per-volatile partial pressures [bar a] of a liquor at ``t_c``.

    Process utility
    ---------------
    Splitting the bubble point into its species terms is what lets a flash form per-species
    K-values (``K_i = p_i / (x_i P)``) rather than only a bubble point. `bubble_p_bara` is
    the sum of this vector and therefore cannot drift from it.

    Returns
    -------
    dict
        ``{"NH3": p, "CO2": p, "H2O": p, "N2": p, ..., "f_dil": f, "in_grid": bool}``.
        Each partial pressure already carries the non-volatile dilution factor, so their
        sum is exactly the bubble pressure.

        ``in_grid`` reports whether this state was actually solved rather than clamped —
        see the module docstring.
    """
    s, f = coords(w)
    inside = in_box(t_c, s, f)
    a_nh3, a_co2, a_h2o, n_sub_per_kgw, corners_ok = interp(t_c, s, f)

    w_h2o = max(w.get("H2O", 0.0), 1e-9)
    # Sub-system moles carried by this liquor's water, and everything alongside them that
    # is NOT in the electrolyte sub-system: the non-volatiles and the four permanent gases.
    n_sub = n_sub_per_kgw * (w_h2o / MW["H2O"]) * (MW["H2O"] / 1000.0)
    n_nv = sum(max(w.get(k, 0.0), 0.0) / MW[k] for k in NONVOLATILE)
    n_in = {k: max(w.get(k, 0.0), 0.0) / MW[k] for k in INERTS}
    n_in_tot = sum(n_in.values())
    n_all = max(n_sub + n_nv + n_in_tot, 1e-12)
    f_dil = n_sub / n_all

    t_k = t_c + 273.15
    out = {
        "NH3": f_dil * a_nh3 * props.henry_nh3_MPa(t_k) * 10.0,        # MPa -> bar
        "CO2": f_dil * a_co2 * props.henry_co2_MPa(t_k) * 10.0,
        "H2O": f_dil * a_h2o * iapws.psat_bara(_clamp(t_c, 0.05, 370.0)),
        "f_dil": f_dil,
        "in_grid": bool(inside and corners_ok),
    }

    # Permanent gases: Henry's law on an infinite-dilution reference, gamma* = 1. They are
    # not UNIQUAC species and there is no parameter row to give them an activity
    # coefficient; gamma* = 1 IS the standard state, not a stand-in for a missing number.
    # x_j is on the TOTAL liquid mole basis, the same basis f_dil puts the three volatiles on.
    t_lo, t_hi = props.G704_VALID_T_K
    t_h = _clamp(t_k, t_lo, t_hi)
    for k in INERTS:
        out[k] = (n_in[k] / n_all) * props.henry_inert_MPa(k, t_h) * 10.0
    return out


def bubble_p_bara(w: dict, t_c: float) -> float:
    """Bubble-point pressure [bar a] of a liquor at temperature ``t_c``.

    Process utility
    ---------------
    The pressure a stage must be held below for it to boil. Every flash split in the LP
    train is the answer to this compared against the pressure the stage is actually at.

    The terms come from `partial_pressures_bara`, so the bubble point and the flash
    K-values cannot disagree.
    """
    p = partial_pressures_bara(w, t_c)
    tot = p["NH3"] + p["CO2"] + p["H2O"] + sum(p[k] for k in INERTS)
    return max(tot, 1e-6)


#: Warm-start acceptance band, on ln P. A guess whose bubble pressure is within this
#: relative tolerance is returned UNCHANGED, which is what makes the design point
#: bit-exact: the design anchors are computed by cold bisection to 1e-7 K, so on a
#: design-state tick the residual is ~2e-9 and the solver hands back the anchor itself —
#: departure identically 0.0. 1e-6 in pressure is ~5e-5 K in temperature, far below
#: anything the engine or an operator resolves.
WARM_LNP_TOL = 1.0e-6


def bubble_t_c(w: dict, p_bara: float, t_guess: float = None,
               t_lo: float = 40.0, t_hi: float = 240.0, tol: float = 1e-7) -> float:
    """Bubble-point TEMPERATURE [deg C] of the liquor at pressure ``p_bara``.

    Process utility
    ---------------
    The temperature a stage settles at, given the vacuum or pressure it is held at. This is
    the number a recirculation heater is rated on approach to: too close and the downstream
    pump cavitates, too far and the carbamate does not decompose.

    Method
    ------
    `bubble_p_bara` is strictly increasing in T — every one of its terms is — so the root is
    unique. Two solvers share this entry point:

      * **Warm start.** Pass last tick's answer as ``t_guess`` and the root is found by
        Newton on ln P. The bubble pressure is very nearly exponential in T, so ln P is
        nearly linear and Newton converges in two or three steps: about 10 us. This is the
        path the engine takes every tick.
      * **Cold start.** With no guess, bisect. Used at import to establish the design
        anchors, where 40 halvings at ~0.7 ms is irrelevant.
    """
    if t_guess is not None and t_lo < t_guess < t_hi:
        t = _clamp(t_guess, t_lo, t_hi)
        ln_target = math.log(max(p_bara, 1e-9))
        for _ in range(6):
            p0 = bubble_p_bara(w, t)
            f = math.log(max(p0, 1e-12)) - ln_target
            if abs(f) < WARM_LNP_TOL:
                return t
            h = 0.25
            p1 = bubble_p_bara(w, min(t + h, t_hi))
            slope = (math.log(max(p1, 1e-12)) - math.log(max(p0, 1e-12))) / h
            if slope <= 1.0e-9:
                break                      # flat: Newton has nothing to work with, bisect
            t_new = _clamp(t - f / slope, t_lo, t_hi)
            if abs(t_new - t) < 1.0e-6:
                return t_new
            t = t_new
        else:
            return t

    lo, hi = t_lo, t_hi
    if bubble_p_bara(w, lo) >= p_bara:
        return lo
    if bubble_p_bara(w, hi) <= p_bara:
        return hi
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if bubble_p_bara(w, mid) < p_bara:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)


def prime() -> str:
    """Force the activity table to be built or loaded now.

    Called at engine start so the first simulation tick is fast rather than paying for a
    20 s table build while an operator watches.
    """
    vle_grid.ensure_table()
    return MODEL_NAME


def build_stats() -> dict:
    """Activity-table build statistics — for the boot report and for tests."""
    return vle_grid.build_stats()


__all__ = [
    "MW", "NONVOLATILE", "INERTS", "MODEL_NAME", "VALID_PRESSURE_BARA", "WARM_LNP_TOL",
    "loadings", "coords", "envelope", "in_grid",
    "partial_pressures_bara", "bubble_p_bara", "bubble_t_c",
    "prime", "build_stats",
]
