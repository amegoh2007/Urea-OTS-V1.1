"""K-values, the anchored ratio, and the bubble and dew points.

What this layer is
------------------
Everything between "which model owns this state" (`thermo.domains`) and "solve the material
balance" (`thermo.service`). It turns a liquid composition into the vapour it is in
equilibrium with:

    K_i = p_i / (phi_i^V P x_i)

on the **apparent, total-species** basis. The electrolyte model speciates ammonia into
NH3(aq)/NH4+/NH2COO- and CO2 into CO2(aq)/HCO3-/CO3--, but the flowsheet's mass balance
tracks total NH3 and total CO2, so that ratio is what the flowsheet needs and what these
functions return. Urea, biuret and HCHO are non-volatile: K = 0 **exactly**.

The anchored ratio
------------------
The 322 synthesis loop does not take an absolute number from here. It takes only the
*movement* — see `k_ratio`, which is the most important function in this module and the
reason an extrapolated activity model is still worth having.

Ported from V1 `backend/thermo_service.py` (K-value and bubble/dew block).
Numerically identical.
"""

from __future__ import annotations

import math

from ureasim.thermo import extended_uniquac as neutral
from ureasim.thermo import memo
from ureasim.thermo import properties as props
from ureasim.thermo import vle
from ureasim.thermo.domains import (
    DISTRIBUTING,
    DOMAIN_NEUTRAL_UREA,
    NONVOLATILE,
    SPECIES,
    VOLATILE,
    OutOfDomain,
    classify,
    domain_report,
    mass_to_mole,
    mole_to_mass,
    norm_mass,
)

#: Species the SRK parameter set covers: H2O, NH3, CO2 and the four inerts.
_SRK_SPECIES = tuple(props.SRK_CRIT)


# ======================================================================================
# Partial pressures and vapour fugacity
# ======================================================================================

def partial_pressures(w: dict, t_c: float, domain: str = None) -> dict:
    """Volatile partial pressures [bar a] over a liquid of mass fractions ``w`` at ``t_c``.

    ELECTROLYTE
        All three from the Extended UNIQUAC table plus Henry and IAPWS-IF97.
    NEUTRAL_UREA
        Water from the neutral urea/water binary (``a_w Psat``); NH3 and CO2 from the
        electrolyte dilute limit. This is the hybrid `thermo.domains` justifies.
    """
    w = norm_mass(w)
    if domain is None:
        domain = classify(w, t_c)
    if domain is None:
        raise OutOfDomain(f"no fitted model owns this state: {domain_report(w, t_c)}")

    p = vle.partial_pressures_bara(w, t_c)
    out = {s: p[s] for s in DISTRIBUTING}

    if domain == DOMAIN_NEUTRAL_UREA:
        t_k = t_c + 273.15
        # The urea/water binary on a water-free-of-volatiles basis: the traces do not shift
        # the binary, so they are excluded from its composition rather than distorting it.
        w_urea = w.get("Urea", 0.0)
        w_pair = w_urea + w.get("H2O", 0.0)
        if w_pair > 1e-12:
            a_w = neutral.water_activity(
                min(max(w_urea / w_pair, 0.0), 0.999999), t_k)
            out["H2O"] = a_w * neutral.water_psat_bara(t_k)
    return out


def vapour_fugacity(y_mole: dict, t_c: float, p_bara: float) -> dict:
    """SRK vapour fugacity coefficients for the volatile vapour, k_ij = 0.

    Process utility
    ---------------
    Not cosmetic in this loop: at 144.2 bar a and 183 C the light gases come out at
    phi_N2 = 1.22 and phi_H2 = 1.29 — 20-30 % from ideal, in the direction that makes them
    LESS soluble, and every one of those per cent lands directly on an inert K-value.

    HCHO has no critical constants here and is non-volatile anyway, so it returns ideal.
    A failed cubic returns ideal rather than raising: a fugacity coefficient is a
    correction, and losing it degrades an answer where propagating an exception would lose
    the tick.
    """
    y = {s: max(y_mole.get(s, 0.0), 0.0) for s in _SRK_SPECIES}
    tot = sum(y.values())
    phi = {s: 1.0 for s in SPECIES}
    if tot <= 1e-12 or p_bara <= 0.0:
        return phi
    y = {s: v / tot for s, v in y.items()}
    try:
        phi_srk, _z = props.srk_phi(y, t_c + 273.15, p_bara * 1.0e5)
    except (ValueError, ZeroDivisionError, OverflowError):
        return phi
    for s in _SRK_SPECIES:
        v = phi_srk.get(s)
        if v is not None and math.isfinite(v) and v > 0.0:
            phi[s] = v
    return phi


def k_values(w_liq: dict, t_c: float, p_bara: float,
             y_mole: dict = None, domain: str = None) -> dict:
    """Apparent ``K_i = y_i / x_i`` on the total-species basis.

        K_i = p_i / (phi_i^V P x_i)

    Non-volatiles return exactly 0.0. ``y_mole`` seeds the SRK mixture; ``None`` means
    ideal vapour, which is correct as the **first pass** of the flash's successive
    substitution — the loop then feeds the converged vapour back in.
    """
    w_liq = norm_mass(w_liq)
    if domain is None:
        domain = classify(w_liq, t_c, p_bara)
    p_i = partial_pressures(w_liq, t_c, domain)
    x = mass_to_mole(w_liq)
    phi = vapour_fugacity(y_mole, t_c, p_bara) if y_mole else {s: 1.0 for s in SPECIES}
    k = {s: 0.0 for s in SPECIES}
    for s in DISTRIBUTING:
        xs = x.get(s, 0.0)
        if xs <= 1e-14:
            continue
        k[s] = max(p_i[s] / (max(phi[s], 1e-9) * max(p_bara, 1e-9) * xs), 0.0)
    return k


def _k_srk(w: dict, t_c: float, p_bara: float, domain: str) -> dict:
    """K-values with the SRK vapour fugacity actually applied, in ONE pass.

    `k_values(..., y_mole=None)` returns phi = 1.0 — documented, and correct as the first
    pass of a flash. `k_ratio` has no such loop, so calling `k_values` bare would have
    silently made the pressure leg of the ratio the naive ``P_ref/P``: measured, it
    reproduced 144.2/130 to the last bit, i.e. the SRK term was not present at all. It
    matters here more than anywhere, because at 144 bar a and 183 C the light species are
    20-30 % from ideal.

    So the vapour is seeded from the partial pressures themselves (``y_i`` proportional to
    ``p_i``, the ideal-vapour composition — the same seed `bubble_p` uses) and the fugacity
    taken once on it. One pass, not a loop: the vapour composition barely moves under phi,
    and a ratio of two single-pass evaluations is what is wanted, not two separately
    converged fixed points.
    """
    p_i = partial_pressures(w, t_c, domain)
    x = mass_to_mole(w)
    tot = sum(p_i[s] for s in DISTRIBUTING)
    y = {s: p_i[s] / tot for s in DISTRIBUTING} if tot > 0.0 else None
    phi = vapour_fugacity(y, t_c, p_bara) if y else {s: 1.0 for s in SPECIES}
    k = {}
    for s in DISTRIBUTING:
        xs = x.get(s, 0.0)
        k[s] = (max(p_i[s] / (max(phi[s], 1e-9) * max(p_bara, 1e-9) * xs), 0.0)
                if xs > 1e-14 else 0.0)
    return k


# ======================================================================================
# The anchored ratio the HP loop runs on
# ======================================================================================

def k_ratio(z_mass: dict, t_c: float, p_bara: float,
            t_ref_c: float, p_ref_bara: float, z_ref_mass: dict = None,
            species=None, lo: float = 0.02, hi: float = 50.0) -> dict:
    """Per-species K-value RATIO ``K_i(live) / K_i(reference)``.

    Process utility
    ---------------
    This is the **only** way the 322 synthesis loop is allowed to touch this service, and
    the reason is measured rather than asserted. The Extended UNIQUAC parameter set is
    extrapolated in the synthesis loop and puts the 322R001 overflow's bubble pressure 3.6x
    low in ABSOLUTE terms. Its **derivatives** survive that extrapolation, because a
    systematic offset in an activity coefficient divides out of a ratio and a slope does
    not. So the engine keeps the licensor's absolute split and takes only the movement:

        alpha_live,i = alpha_PFD,i * k_ratio_i

    Bit-exactness at design
    -----------------------
    With ``z_ref_mass = None`` the reference is evaluated on the SAME composition as the
    live point, so at ``t_c == t_ref_c`` and ``p_bara == p_ref_bara`` every argument of the
    two calls is identical, the two K-values are the same float, and the ratio is exactly
    1.0 — not 1.0 within a tolerance, and with no identity short-circuit hiding a residual.

    That is why it is the default: the HP splits are anchored to design vectors calibrated
    at a stated (T, P), and their design *composition* is assembled from live streams and is
    not constant anywhere. Passing an explicit ``z_ref_mass`` adds the composition
    derivative too, and is used only where the caller genuinely owns a constant design
    composition to anchor against.

    Safety
    ------
    Off-envelope, non-convergent or non-finite, a species falls back to 1.0 — the
    licensor's own split. The state is never frozen and the ratio is never NaN. ``lo`` and
    ``hi`` bound the excursion: a ratio outside them is the model leaving its useful range,
    not a real 50x move in a condenser split, and the anchored vector is the better answer
    there.

    Why this is deliberately NOT memoised
    --------------------------------------
    This is the one place in this layer where the quantised memo `flash` and `bubble_t` use
    is the WRONG answer. It was written, measured (9.6 us warm against 176 us cold, a 6.7 %
    tick saving across the four wired sites) and then **removed**, because it is a
    correctness hazard specific to a ratio:

    every one of these calls has a reference point that must return exactly 1.0, and the
    engine spends thousands of ticks NEAR that point — the entire boot settle does. On the
    quantisation grid (0.02 C, 1e-4 bar, 100 ppm) a settle tick 60 ppm away in composition
    keys IDENTICALLY to the design state, so whichever of the two ran first answered for
    both. Measured: it moved the pinned 322E003 vent vector by 1.1e-4 kmol/h, and it did so
    ONLY when the boot-pin cache missed and the full settle ran — i.e. it was invisible on a
    warm tree and appeared on a cold one. A memo that silently breaks a design pin
    depending on whether a cache file exists is worse than 700 us a tick.

    If this ever needs to be fast, the correct fix is an EXACT-argument key — which hits
    every tick at a fixed point and misses honestly during a transient — not a finer
    quantum. A finer quantum shrinks the window without closing it.
    """
    keys = tuple(species) if species is not None else DISTRIBUTING
    out = {s: 1.0 for s in keys}
    try:
        z = norm_mass(z_mass)
        z_r = z if z_ref_mass is None else norm_mass(z_ref_mass)
        # Classify ONCE per composition and hand the answer to both K-value calls.
        # `k_values` otherwise re-derives the domain, and each derivation is a full grid
        # interpolation — this is a ratio, so it would pay for four where two will do.
        dom = classify(z, t_c, p_bara)
        if dom is None:
            return out
        # The reference shares the live classification only when it shares the ARGUMENTS.
        # It usually does not — the reference temperature is the design temperature — and
        # the envelope is bounded in T, so reusing `dom` there would let an off-envelope
        # reference borrow the live point's domain.
        dom_r = (dom if (z_ref_mass is None and t_ref_c == t_c)
                 else classify(z_r, t_ref_c, p_ref_bara))
        if dom_r is None:
            return out
        k_live = _k_srk(z, t_c, p_bara, dom)
        k_ref = _k_srk(z_r, t_ref_c, p_ref_bara, dom_r)
    except (OutOfDomain, ValueError, ZeroDivisionError, OverflowError, KeyError):
        return out

    for s in keys:
        a, b = k_live.get(s, 0.0), k_ref.get(s, 0.0)
        if b <= 0.0 or a <= 0.0 or not (math.isfinite(a) and math.isfinite(b)):
            continue
        r = a / b
        out[s] = r if lo <= r <= hi else (lo if r < lo else hi)
    return out


# ======================================================================================
# Bubble point
# ======================================================================================

def bubble_p(w: dict, t_c: float, srk: bool = True, iters: int = 30) -> float:
    """Bubble-point pressure [bar a] of liquid ``w`` at ``t_c``.

    Full gamma-phi definition — the pressure at which ``sum_i y_i = 1`` with
    ``y_i phi_i P = p_i``:

        P = sum_i p_i / phi_i(y, T, P)

    solved by fixed-point iteration on y. Passing ``srk=False`` returns the ideal-vapour
    sum, which is what `thermo.vle.bubble_p_bara` computes and what the PFD comparison in
    that module was measured against.

    The phi correction is **not** cosmetic: with phi = 1 here and phi applied inside
    `k_values`, the bubble point and the flash sat on two different surfaces, and a flash
    AT the computed bubble temperature returned psi = 1.5e-3 instead of ~0. Both entry
    points now use the same phi.
    """
    p = partial_pressures(w, t_c)
    p_ideal = max(sum(p[s] for s in DISTRIBUTING), 1.0e-9)
    if not srk:
        return p_ideal
    p_bub = p_ideal
    phi = {s: 1.0 for s in SPECIES}
    for _ in range(iters):
        # y_i is proportional to p_i/phi_i, NOT to p_i: with per-species phi the vapour
        # composition itself shifts, so it has to be recomputed each sweep alongside the
        # pressure. (p_i are already mole-basis, so no molar-mass conversion enters here.)
        num = {s: p[s] / max(phi[s], 1e-9) for s in DISTRIBUTING}
        tot = sum(num.values())
        y_mole = {s: (num[s] / tot if tot > 0.0 else 0.0) for s in DISTRIBUTING}
        phi = vapour_fugacity(y_mole, t_c, p_bub)
        p_new = sum(p[s] / max(phi[s], 1e-9) for s in DISTRIBUTING)
        if abs(p_new - p_bub) <= 1e-12 * max(p_new, 1.0):
            p_bub = p_new
            break
        p_bub = p_new
    return max(p_bub, 1.0e-9)


def bubble_t(w: dict, p_bara: float, t_lo: float = None, t_hi: float = None,
             tol: float = 1.0e-6) -> float:
    """Memoised bubble-point temperature [deg C].

    A bubble temperature is 60 bisection steps, each a full gamma-phi `bubble_p`, so it
    costs about 8 ms against a flash's 9 ms. The engine calls it once per stage per tick,
    which is far more often than the composition can actually move, so it is quantised on
    the same grid as the flash memo.

    Each bin stores a **first-order expansion** about its canonical point and returns it
    evaluated at the caller's own (w, P), so the answer is continuous across bin edges and
    does not depend on which point filled the bin — see `thermo.memo`.

    Explicit brackets bypass the memo, because they change the answer.
    """
    if memo.BUBT_CACHE_SIZE <= 0 or t_lo is not None or t_hi is not None:
        return _bubble_t_solve(w, p_bara, t_lo, t_hi, tol)

    z = norm_mass(w)
    key = (round(p_bara / memo.P_QUANTUM_BARA), round(tol / 1.0e-9),
           tuple(round(z[s] / memo.W_QUANTUM) for s in SPECIES))
    lin = memo.bubble_t_cache.get(key)
    if lin is not None:
        memo.record_bubble_t(True)
    else:
        memo.record_bubble_t(False)
        lin = _bubble_t_linearisation(key, tol)
        if len(memo.bubble_t_cache) >= memo.BUBT_CACHE_SIZE:
            # Harmless: an entry is a pure function of its key.
            memo.bubble_t_cache.clear()
        memo.bubble_t_cache[key] = lin

    t_c, p_c, z_c, grad, dp_dt = lin
    if dp_dt <= 0.0:
        return t_c
    dp_comp = sum(g * (z[s] - z_c[s]) for s, g in grad.items())
    return t_c + ((p_bara - p_c) - dp_comp) / dp_dt


def _bubble_t_linearisation(key: tuple, tol: float):
    """``(T_c, P_c, z_c, dP/dz_s, dP/dT)`` at a memo bin's canonical point.

    The bubble point returned for ANY caller in the bin is the first-order expansion about
    that point, from the implicit function ``P_bub(z, T) = P``:

        T = T_c + [ (P - P_c) - sum_s g_s (z_s - z_c,s) ] / (dP_bub/dT)

    with ``g_s`` the derivative of P_bub along a NORMALISED perturbation of species s,
    ``g_s = grad(P_bub) . (e_s - z_c)``. Because both z and z_c sum to one,
    ``sum_s g_s dz_s`` equals ``grad(P_bub) . dz`` exactly, so no renormalisation term is
    missing.

    Only species present at the canonical point carry a derivative: a species that rounds
    to zero is below half a quantum, and differentiating from zero would risk flipping the
    owning activity model mid-difference.

    Cost on a miss: the bisection (~3 ms) plus one `bubble_p` per present species and two
    for dP/dT (~0.1 ms each). A derivative that cannot be taken — the canonical point sits
    on an envelope edge — degrades to the canonical value alone, flagged by dP/dT = 0.
    """
    p_c, z_q = memo.canonical_point(key[0], key[2])
    z_c = norm_mass(z_q)
    t_c = _bubble_t_solve(z_c, p_c, None, None, key[1] * 1.0e-9)
    grad = {}
    try:
        h_t = 0.01
        dp_dt = (bubble_p(z_c, t_c + h_t) - bubble_p(z_c, t_c - h_t)) / (2.0 * h_t)
        p_at = bubble_p(z_c, t_c)
        h = 1.0e-6
        for s in SPECIES:
            if z_c[s] <= 0.0:
                continue
            zp = {k: z_c[k] / (1.0 + h) for k in SPECIES}
            zp[s] += h / (1.0 + h)
            grad[s] = (bubble_p(zp, t_c) - p_at) * (1.0 + h) / h
    except (OutOfDomain, ValueError, ZeroDivisionError):
        grad, dp_dt = {}, 0.0
    return t_c, p_c, z_c, grad, dp_dt


def _bubble_t_solve(w: dict, p_bara: float, t_lo: float = None, t_hi: float = None,
                    tol: float = 1.0e-6) -> float:
    """Bubble-point temperature [deg C] by bisection on ``bubble_p - P``.

    Brackets default to the owning model's own envelope, so the answer can never be
    reported from outside the fitted range.
    """
    w = norm_mass(w)
    dom = classify(w, 0.5 * sum(vle.envelope()["t_c"]), p_bara)
    if dom == DOMAIN_NEUTRAL_UREA:
        lo_d, hi_d = (neutral.VALID_TEMPERATURE_K[0] - 273.15,
                      neutral.VALID_TEMPERATURE_K[1] - 273.15)
    else:
        lo_d, hi_d = vle.envelope()["t_c"][0], vle.envelope()["t_c"][1]
    lo = lo_d if t_lo is None else max(t_lo, lo_d)
    hi = hi_d if t_hi is None else min(t_hi, hi_d)
    if lo >= hi:
        raise OutOfDomain(f"empty bracket for bubble_t: {domain_report(w, lo, p_bara)}")

    # REFUSE, never clamp. These two used to return the edge of the fitted temperature grid
    # as though it were a converged bubble point — the exact failure this service exists to
    # avoid, and it bit: a 323F010 liquor that had accumulated 1.6 wt% NH3 has a real
    # bubble point BELOW the 80 C grid edge at 0.46 bar a, and a clamped 80.0 came back
    # looking like an answer. An unbracketed root means the state is off-envelope.
    if bubble_p(w, lo) >= p_bara:
        raise OutOfDomain(f"bubble point below the fitted grid ({lo} C): P_bub({lo} C) = "
                          f"{bubble_p(w, lo):.6g} >= {p_bara} bar a")
    if bubble_p(w, hi) <= p_bara:
        raise OutOfDomain(f"bubble point above the fitted grid ({hi} C): P_bub({hi} C) = "
                          f"{bubble_p(w, hi):.6g} <= {p_bara} bar a")

    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if bubble_p(w, mid) < p_bara:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)


# ======================================================================================
# Dew point
# ======================================================================================

def dew_t(y_mass: dict, p_bara: float, tol: float = 1.0e-5) -> float:
    """Dew-point temperature [deg C] of vapour ``y_mass`` at ``p_bara``.

    Process utility
    ---------------
    Where a vapour first wets. It is what decides whether a line or an exchanger inlet is
    running dry or is already two-phase — which changes both its pressure drop and its heat
    transfer.

    Method
    ------
    The temperature at which a flash of this overall composition first produces liquid:
    ``sum_i z_i / K_i(T) = 1`` with the liquid taken as the incipient drop. Bisection on the
    residual keeps it inside the owning model's envelope, as `bubble_t` does.

    Non-volatiles are all in the liquid at the dew point, so they are placed there in full
    rather than distributed — at an incipient drop they are the drop.
    """
    z = norm_mass(y_mass)
    lo, hi = vle.envelope()["t_c"]

    def _resid(t_c):
        # Incipient liquid: iterate x until self-consistent at vapour fraction -> 1.
        x = dict(z)
        for _ in range(40):
            k = k_values(x, t_c, p_bara, y_mole=mass_to_mole(z))
            zz = mass_to_mole(z)
            denom = sum(zz[s] / k[s] for s in VOLATILE if k[s] > 1e-12)
            if denom <= 0.0:
                return -1.0
            x_new_mole = {s: (zz[s] / k[s] / denom if k[s] > 1e-12 else 0.0)
                          for s in VOLATILE}
            for s in NONVOLATILE:
                x_new_mole[s] = 0.0
            nv = sum(zz[s] for s in NONVOLATILE)
            if nv > 0.0:
                for s in NONVOLATILE:
                    x_new_mole[s] = zz[s]
                tot = sum(x_new_mole.values())
                x_new_mole = {s: v / tot for s, v in x_new_mole.items()}
            x_new = mole_to_mass(x_new_mole)
            if max(abs(x_new[s] - x[s]) for s in SPECIES) < 1e-10:
                x = x_new
                break
            x = x_new
        return denom - 1.0

    r_lo, r_hi = _resid(lo), _resid(hi)
    if r_lo * r_hi > 0.0:
        raise OutOfDomain(f"dew point not bracketed in [{lo}, {hi}] C at {p_bara} bar a")
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if _resid(mid) * r_lo > 0.0:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)


__all__ = [
    "partial_pressures", "vapour_fugacity", "k_values", "k_ratio",
    "bubble_p", "bubble_t", "dew_t",
]
