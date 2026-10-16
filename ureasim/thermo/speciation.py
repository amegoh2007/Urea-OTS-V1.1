"""Liquid-phase speciation of the NH3-CO2-H2O system — the R1-R5 Newton solve.

What this gives the plant model
-------------------------------
Ammonia and CO2 do not simply dissolve in water — they react. Dissolve them together and
you get ammonium, bicarbonate, carbonate and, above all, **carbamate**. Only the *free*
NH3(aq) and CO2(aq) exert a partial pressure; the ionic forms are locked in the liquid.

So the question every LP-section unit really asks is: *of the ammonia in this liquor, how
much is free?* That is what this module answers, and everything downstream follows from it:

    328C002 / 328C004 desorbers   how much strips out for a given steam duty
    322C001 LP absorber           how much a wash liquor can still take up
    323 recirculation stages      the bubble point, hence the flash split
    324 vacuum condensers         the NH3 and CO2 partial pressures in the vent

Without speciation, a liquor's back-pressure would have to be a fitted function of total
loading — which is exactly the frozen-constant failure the rewrite exists to remove.

The system
----------
Eight unknowns (the eight solute molalities) and eight equations:

    3 balances     total N, total C, and electroneutrality
    5 equilibria   R1 water, R2 ammonium, R3 bicarbonate, R4 carbonate, R5 carbamate

Basis conventions
-----------------
Molality (per 1 kg of water), consistent with the molality-scale standard states behind
``lnK``:

    solute activity   a_i = m_i * gamma_i^* * x_w    (Thomsen 2005 eq. 4:
                                                      gamma_i^m = gamma_i^* x_w)
    water activity    a_w = x_w * gamma_w            (symmetric)

Every equilibrium uses the **complete** Extended UNIQUAC activity coefficient
(combinatorial + residual + Debye-Huckel), not the short-range part alone.

Validation carried over from V1: at the solution, all element and charge balances and all
five reaction quotients close to about 1e-10.

Ported from V1 `backend/props_nh3co2h2o.py` (speciation block). Numerically identical.
"""

from __future__ import annotations

import math

from ureasim.thermo.activity import activity_ln_gamma, ionic_strength
from ureasim.thermo.parameters import LN10, N_W_PER_KG, SOLUTES, T0
from ureasim.thermo.standard_state import lnK, reaction_cp_available


def _solve_linear(A, b):
    """Dense linear solve by Gaussian elimination with partial pivoting.

    Eight equations is far too small for a library routine to pay for itself, and keeping
    the solve local means the speciation has no external numerical dependency — which
    matters because this function runs inside the innermost loop of the activity-grid
    build (1215 nodes, each a full Newton solve).
    """
    n = len(b)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-300:
            raise ValueError("singular Jacobian in speciation solve")
        M[col], M[piv] = M[piv], M[col]
        pv = M[col][col]
        for r in range(n):
            if r != col:
                f = M[r][col] / pv
                for c in range(col, n + 1):
                    M[r][c] -= f * M[col][c]
    return [M[i][n] / M[i][i] for i in range(n)]


def _speciation_residuals(m, N_tot: float, C_tot: float, T: float):
    """The eight speciation residuals for molality vector ``m`` (order `SOLUTES`).

    Rows
    ----
        0   total nitrogen balance     NH3(aq) + NH4+ + NH2COO-  = N_tot
        1   total carbon balance       CO2(aq) + HCO3- + CO3-- + NH2COO- = C_tot
        2   electroneutrality          sum(+) = sum(-)
        3   R1  ln a_H+ + ln a_OH- - ln a_w                     = ln K1
        4   R2  ln a_NH4+ - ln a_NH3 - ln a_H+                   = ln K2
        5   R3  ln a_HCO3- + ln a_H+ - ln a_CO2 - ln a_w         = ln K3
        6   R4  ln a_CO3-- + ln a_H+ - ln a_HCO3-                = ln K4
        7   R5  ln a_NH2COO- + ln a_w - ln a_NH3 - ln a_HCO3-    = ln K5

    Rows 0-2 are on an absolute molality scale and rows 3-7 on a log scale. That mixed
    scaling is deliberate — it keeps the balances exactly satisfied while letting the
    equilibria be solved in the log domain where they are nearly linear — and it is why the
    convergence norm reported by `speciate` is on that same mixed basis.
    """
    md = dict(zip(SOLUTES, m))
    ntot = N_W_PER_KG + sum(m)
    x = {"H2O": N_W_PER_KG / ntot}
    for s in SOLUTES:
        x[s] = md[s] / ntot
    lng = activity_ln_gamma(x, T)                       # complete Extended UNIQUAC ln gamma
    ln_xw = math.log(x["H2O"])

    def ln_a(sp: str) -> float:
        """Solute activity on the molality scale: a = m * gamma* * x_w."""
        return math.log(md[sp]) + lng[sp] + ln_xw

    ln_aw = ln_xw + lng["H2O"]

    res = [0.0] * 8
    res[0] = (md["NH3(aq)"] + md["NH4+"] + md["NH2COO-"]) - N_tot
    res[1] = (md["CO2(aq)"] + md["HCO3-"] + md["CO3--"] + md["NH2COO-"]) - C_tot
    res[2] = ((md["H+"] + md["NH4+"])
              - (md["OH-"] + md["HCO3-"] + 2.0 * md["CO3--"] + md["NH2COO-"]))
    res[3] = (ln_a("H+") + ln_a("OH-") - ln_aw) - lnK("R1_water", T)
    res[4] = (ln_a("NH4+") - ln_a("NH3(aq)") - ln_a("H+")) - lnK("R2_ammonium", T)
    res[5] = (ln_a("HCO3-") + ln_a("H+") - ln_a("CO2(aq)") - ln_aw) - lnK("R3_bicarb", T)
    res[6] = (ln_a("CO3--") + ln_a("H+") - ln_a("HCO3-")) - lnK("R4_carbonate", T)
    res[7] = (ln_a("NH2COO-") + ln_aw - ln_a("NH3(aq)") - ln_a("HCO3-")) - lnK("R5_carbamate", T)
    return res


def speciate(N_tot: float, C_tot: float, T: float = T0,
             tol: float = 1e-11, maxiter: int = 200, m_guess=None) -> dict:
    """Solve the liquid-phase speciation of an aqueous NH3-CO2 solution.

    Parameters
    ----------
    N_tot, C_tot
        Total ammonia and total CO2 [mol per kg of water].
    T
        Temperature [K]. Defaults to 298.15 K.
    m_guess
        Molalities from a converged neighbouring state, used to seed the Newton iteration.
        See "Why m_guess exists" below — this parameter is what puts the HP synthesis loop
        inside the model's reach.

    Returns
    -------
    dict
        Molalities [mol/kg water] for each species in `SOLUTES`, plus:
        ``'H2O'`` water mole fraction, ``'I'`` ionic strength, ``'pH'`` = -log10(a_H), and
        ``'resid'`` the achieved residual infinity-norm.

    Method
    ------
    Damped log-space Newton with a numerical Jacobian. Solving in ``ln m`` rather than
    ``m`` enforces positivity structurally: no molality can go negative and force a
    restart, which is what makes the iteration robust from a poor starting point.

    The damping caps the maximum log-step at 2 (a factor of about 7.4 per iteration),
    which prevents the first step from overshooting into a region where the activity model
    is ill-conditioned.

    Why ``m_guess`` exists
    ----------------------
    The stock initial guess is a dilute-solution ansatz, and it was the **only** thing
    limiting this solver's reach. Measured at 183 C on the N/C = 4.46 ray, the damped
    log-Newton converges to a residual of ~1e-13 up to N = 40 mol/kg water and then stops
    converging at all: at N = 50 it lands on a residual of 9.9 and STAYS there — 200, 2000
    and 20 000 iterations return the identical non-solution. That is a basin-of-attraction
    failure, not a tolerance or an iteration budget.

    That ceiling is what put the whole 322 synthesis loop (N = 100 at the reactor overflow,
    N = 869 at the 322E003 feed) outside this module. Seeded from a converged neighbour
    instead, the **same** solver reaches N = 869 / C = 195 at 183 C in five Newton steps at
    a residual of 8.5e-14. So the grid builder marches, seeding each node from its
    neighbour; nothing about the equations, the damping or the tolerance changes, and an
    unseeded call behaves exactly as it did before.

    What IS extrapolated at those loadings is the **parameter set**, not the solve — see
    the envelope note in `thermo.vle`.

    Raises
    ------
    ValueError
        Off 298.15 K when the NH3(aq)/CO2(aq) Cp rows needed by R2, R3 and R5 are
        unavailable. Refused rather than fabricated.
    """
    if T != T0:
        # R2 / R3 / R5 need the NH3(aq) and CO2(aq) Cp rows for their K(T).
        for rx in ("R2_ammonium", "R3_bicarb", "R5_carbamate"):
            if not reaction_cp_available(rx):
                raise ValueError(
                    "speciate() off 298.15 K needs the NH3(aq)/CO2(aq) Cp rows "
                    "(Thomsen & Rasmussen 1999, paywalled); not fabricated."
                )

    # Physically-motivated initial guess. It does not need to be accurate — Newton enforces
    # the balances — only to land in the right basin. About 45 % of the ammonia as
    # ammonium and a tenth of the limiting reagent as carbamate is what a dilute aqueous
    # NH3/CO2 solution actually looks like at room temperature.
    carb = 0.1 * min(N_tot, C_tot)
    m = {
        "H+": 1e-7, "OH-": 1e-7,
        "NH4+": 0.45 * N_tot, "NH2COO-": carb,
        "NH3(aq)": max(1e-9, N_tot - 0.45 * N_tot - carb),
        "HCO3-": max(1e-9, 0.7 * (C_tot - carb)),
        "CO3--": max(1e-9, 0.05 * (C_tot - carb)),
        "CO2(aq)": max(1e-9, 0.25 * (C_tot - carb)),
    }
    if m_guess is not None:
        m = {s: max(float(m_guess.get(s, m[s])), 1e-300) for s in SOLUTES}

    v = [math.log(m[s]) for s in SOLUTES]              # log-molality variables (positivity)
    for _ in range(maxiter):
        mv = [math.exp(vi) for vi in v]
        r = _speciation_residuals(mv, N_tot, C_tot, T)
        if max(abs(ri) for ri in r) < tol:
            break
        # Numerical Jacobian dr/dv. Analytic would be faster but the activity model's
        # derivatives are not separable, and an error in a hand-differentiated Jacobian is
        # silent — it degrades convergence rather than failing.
        J = [[0.0] * 8 for _ in range(8)]
        for k in range(8):
            dvk = 1e-6 * max(1.0, abs(v[k]))
            vp = list(v)
            vp[k] += dvk
            rp = _speciation_residuals([math.exp(vi) for vi in vp], N_tot, C_tot, T)
            for i in range(8):
                J[i][k] = (rp[i] - r[i]) / dvk
        dv = _solve_linear(J, [-ri for ri in r])
        step = max(1.0, max(abs(d) for d in dv) / 2.0)  # damp: cap max log-step at 2
        v = [v[i] + dv[i] / step for i in range(8)]

    mv = [math.exp(vi) for vi in v]
    md = dict(zip(SOLUTES, mv))

    # The caller cannot otherwise tell convergence from the return value — the loop exits on
    # `maxiter` exactly as it exits on `tol` — so the achieved residual is reported. Same
    # infinity norm the loop tests, on the same mixed scaling (absolute molality balances in
    # rows 0-2, log-K residuals in rows 3-7). The grid builder uses this to CLEAR the
    # converged flag on a node, so the interpolator refuses cells touching it.
    md["resid"] = max(abs(ri) for ri in _speciation_residuals(mv, N_tot, C_tot, T))

    ntot = N_W_PER_KG + sum(mv)
    x = {"H2O": N_W_PER_KG / ntot}
    for s in SOLUTES:
        x[s] = md[s] / ntot
    lng = activity_ln_gamma(x, T)
    md["H2O"] = x["H2O"]
    md["I"] = ionic_strength(x)
    md["pH"] = -(math.log(md["H+"]) + lng["H+"] + math.log(x["H2O"])) / LN10   # -log10 a_H
    return md


__all__ = ["speciate"]
