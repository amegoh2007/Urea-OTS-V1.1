"""Unified rigorous VLE / flash service — one entry point for every phase boundary.

What this is
------------
The façade the flowsheet calls. It stands on the two activity models the property layer
owns and adds the material balance:

    thermo.vle                Extended UNIQUAC NH3-CO2-H2O electrolyte gamma-phi, with the
                              R1-R5 liquid speciation, Rumpf-Maurer Henry constants and the
                              IAPWS-IF97 water line. Urea and biuret enter as non-volatile
                              diluents.
    thermo.extended_uniquac   Neutral H2O/urea binary UNIQUAC (Voskov-Voronin). The
                              Debye-Huckel term is identically zero for two neutral species,
                              so this IS Extended UNIQUAC in the urea/water limit — and it is
                              the only one of the two that sees urea as a UNIQUAC species
                              rather than a mole-fraction diluent.
    thermo.srk                Soave-Redlich-Kwong vapour fugacity, k_ij = 0.
    thermo.enthalpy           Absolute stream enthalpy on the elements-at-298.15 K datum.
                              This is what makes `flash_ph` possible at all.

Exposed here: `flash`, `flash_ph`, `bubble_p`, `bubble_t`, `dew_t`, `k_values`, `k_ratio`,
`classify` and `domain_report`. The solver is Rachford-Rice on gamma-phi K-values with SRK
vapour fugacity.

Measured, on the engine's own design vectors, bubble pressure against the PFD
------------------------------------------------------------------------------

    stage      T (C)   P_PFD    electrolyte    neutral-hybrid    domain used
    323C003    135     4.10     +7.0 %         --                ELECTROLYTE
    323F004    106     1.13     +17.5 %        --                ELECTROLYTE
    323F010     99     0.46     +1.7 %         --                ELECTROLYTE
    324E001    130     0.330    +30.6 %        see test          NEUTRAL_UREA
    324E003    140     0.131    +65.7 %        +2.2 %            NEUTRAL_UREA

What it refuses, and why that matters more than what it answers
----------------------------------------------------------------
The activity table **clamps** at its edges rather than extrapolating, so an out-of-envelope
call does not fail loudly and does not extrapolate wildly — it silently returns the edge
node, i.e. **a frozen constant behind a call that looks like a solve**. That is strictly
worse than an honest hardcoded split vector, because the heuristic becomes invisible.

So this service refuses instead: `classify` returns None and `flash` raises `OutOfDomain`
whenever the state leaves the tabulated envelope, and callers keep whatever anchored model
they have.

The HP synthesis loop, and what the anchored ratio buys
--------------------------------------------------------
Two things used to put the 322 loop outside every envelope, and both were removed: the
molality **coordinate** (see `thermo.vle_grid`) and the speciation **solver's** basin (see
`thermo.speciation`). The four permanent gases now carry SRK critical constants and IAPWS
G7-04 Henry constants, so they generate real K-values instead of forcing a refusal.

What did **not** change is the **fit**. The Extended UNIQUAC interaction parameters are a
CO2-capture set regressed on dilute aqueous loadings below ~150 C, and at x_H2O = 0.047 and
183 C they are extrapolated hard. The measurement that says so plainly: the model puts the
322R001 overflow's bubble pressure at 40.4 bar a at 183 C, against a loop that actually runs
at 144.2 — a factor of 3.6 low.

Nothing here pretends otherwise, and the engine does not use the absolute number. Every 322
split runs on the anchored ratio

    alpha_live = alpha_PFD * [ alpha_model(live) / alpha_model(reference) ]

(`thermo.kvalues.k_ratio`), so the licensor's absolute split is preserved BIT-EXACTLY at the
design point and the model supplies only the derivative — how the split moves when T, P or
composition move. A systematic offset in an extrapolated activity coefficient cancels in
that ratio. Its SLOPE does not, and the slope is what the frozen split vectors reported as
exactly zero.

Basis conventions
-----------------
* Compositions in and out are MASS fractions, matching the engine's species layer, unless a
  function name says otherwise. Internals work in mole fractions.
* K-values are APPARENT, on a TOTAL-species basis — see `thermo.kvalues`.
* Urea, biuret and HCHO are non-volatile: K = 0 exactly.

Ported from V1 `backend/thermo_service.py` (flash block plus façade). Numerically identical.
"""

from __future__ import annotations

from ureasim.thermo import enthalpy as h0
from ureasim.thermo import extended_uniquac as neutral
from ureasim.thermo import memo
from ureasim.thermo import vle

# --- re-exported layers ----------------------------------------------------------------
from ureasim.thermo.domains import (
    DISTRIBUTING,
    DOMAIN_ELECTROLYTE,
    DOMAIN_NEUTRAL_UREA,
    INERTS,
    MODEL_NAME,
    MW,
    NONVOLATILE,
    SPECIES,
    UREA_NEUTRAL_THRESHOLD,
    VOLATILE,
    VOLATILE_TRACE_LOADING,
    OutOfDomain,
    classify,
    domain_report,
    mass_to_mole,
    mole_to_mass,
    norm_mass,
)
from ureasim.thermo.kvalues import (
    bubble_p,
    bubble_t,
    dew_t,
    k_ratio,
    k_values,
    partial_pressures,
    vapour_fugacity,
)
from ureasim.thermo.memo import bubble_t_cache_stats, flash_cache_stats
from ureasim.thermo.splits import (
    anchored_split,
    ratio_shift_frac,
    saturated_inert_vent,
)

#: Mixing factor for the gamma-phi successive-substitution loop — see `_flash_solve`.
_SS_DAMPING = 0.5

#: Convergence tolerance on the liquid mass fraction. MEASURED cost/accuracy at 323C003:
#:
#:     tol      iters     ms     max |dy| vs a 1e-12 solve
#:     1e-9      16      14.0     4.1e-09
#:     1e-7      11       8.6     5.3e-07
#:     1e-5       6       5.1     6.8e-05
#:
#: 1e-7 is seven orders below the model's OWN residual against the PFD (+1.7 to +17.5 % on
#: bubble pressure) and below any composition analyser in the plant, so tightening it
#: further buys nothing physical and costs 60 % more solve time on every miss.
FLASH_TOL = 1.0e-7

#: The successive-substitution budget [sweeps]. V1 runs 40; a dilute, hot 328-type liquor (0.8 wt%
#: urea, 1.4 NH3, 0.9 CO2 at 143 C and 3.5 bar a) reaches a residual of 1.09e-7 against the
#: 1e-7 tolerance at sweep 40 and converges at sweep 41, so V1 flags a good solve unconverged.
#: Raised to 60 by the process engineer's decision of 2026-09-30 (handoff A-9, closed): the fixed
#: point is unchanged and every solve that converged within 40 sweeps returns the same floats; a
#: solve V1 abandoned between sweeps 41 and 60 now finishes and is flagged converged. That moves
#: physics: the 323 stages' rigorous vapour departure refuses an unconverged flash, so at those
#: states it now takes the rigorous branch where V1 fell back to the anchored vector (As-Built
#: §XXXIX.1).
FLASH_OUTER_ITERS = 60


class FlashResult:
    """One converged isothermal flash. Mass fractions out, to match the species layer."""

    __slots__ = ("psi_mole", "psi_mass", "x", "y", "k", "t_c", "p_bara", "domain",
                 "iterations", "residual", "converged")

    def __init__(self, psi_mole, psi_mass, x, y, k, t_c, p_bara, domain,
                 iterations, residual, converged):
        self.psi_mole = psi_mole
        self.psi_mass = psi_mass
        self.x = x
        self.y = y
        self.k = k
        self.t_c = t_c
        self.p_bara = p_bara
        self.domain = domain
        self.iterations = iterations
        self.residual = residual
        self.converged = converged

    def as_dict(self) -> dict:
        return {"psi_mole": self.psi_mole, "psi_mass": self.psi_mass,
                "x": dict(self.x), "y": dict(self.y), "k": dict(self.k),
                "T_C": self.t_c, "P_bara": self.p_bara, "domain": self.domain,
                "iterations": self.iterations, "residual": self.residual,
                "converged": self.converged, "model": MODEL_NAME}


# ======================================================================================
# Rachford-Rice
# ======================================================================================

def rachford_rice(z_mole: dict, k: dict, iters: int = 80) -> float:
    """Vapour mole fraction psi solving ``sum_i z_i(K_i-1)/(1+psi(K_i-1)) = 0``.

    Bisection on the strictly decreasing residual: bounded cost, no convergence failure.
    An OTS tick must never miss its deadline.

    Every species with ``z_i > 0`` enters the sum, **including the non-volatiles at
    K_i = 0**. Their term is ``-z_i/(1-psi)``, which diverges as psi -> 1 and is the only
    thing bounding the vapour fraction below total vaporisation. Dropping them — the
    obvious filter, since K = 0 contributes nothing at psi = 0 — let a liquor that is
    69 wt% urea flash to ``psi_mass = 1.0``. Urea cannot leave, so the true psi is pinned
    well below 1 by that term alone.
    """
    dist = [s for s in SPECIES if z_mole.get(s, 0.0) > 0.0]
    if not dist or all(k.get(s, 0.0) <= 0.0 for s in dist):
        return 0.0

    def g(p):
        return sum(z_mole[s] * (k[s] - 1.0) / (1.0 + p * (k[s] - 1.0)) for s in dist)

    # psi is capped strictly below 1 whenever a non-volatile is present: at psi = 1 the
    # liquid vanishes and a non-volatile has nowhere to be, so the residual is singular.
    z_nv = sum(z_mole.get(s, 0.0) for s in NONVOLATILE)
    hi_cap = (1.0 - 1.0e-9) if z_nv <= 0.0 else (1.0 - max(z_nv * 1.0e-6, 1.0e-9))
    lo, hi = 1.0e-12, hi_cap
    if g(hi) >= 0.0:
        return hi
    if g(lo) <= 0.0:
        return lo
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if g(mid) > 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ======================================================================================
# Isothermal flash
# ======================================================================================

def flash(z_mass: dict, t_c: float, p_bara: float,
          outer_iters: int = FLASH_OUTER_ITERS, tol: float = FLASH_TOL) -> FlashResult:
    """Memoised isothermal (T, P) flash. See `_flash_solve` for the solver itself.

    The memo is quantised and each entry is solved at its bin's **canonical point**, then
    re-evaluated for the caller's own feed by `_flash_at`. `thermo.memo` documents why both
    halves of that are necessary.
    """
    if memo.FLASH_CACHE_SIZE <= 0:
        return _flash_solve(z_mass, t_c, p_bara, outer_iters, tol)

    z = norm_mass(z_mass)
    key = (round(t_c / memo.T_QUANTUM_C), round(p_bara / memo.P_QUANTUM_BARA),
           tuple(round(z[s] / memo.W_QUANTUM) for s in SPECIES))
    canon = memo.flash_cache.get(key)
    if canon is not None:
        memo.record_flash(True)
    else:
        memo.record_flash(False)
        # Solve at the bin's CANONICAL point, from a COLD start, so the stored K is a pure
        # function of the key.
        p_q, z_q = memo.canonical_point(key[1], key[2])
        canon = _flash_solve(norm_mass(z_q), key[0] * memo.T_QUANTUM_C, p_q,
                             outer_iters, tol, warm=False)
        if len(memo.flash_cache) >= memo.FLASH_CACHE_SIZE:
            memo.flash_cache.clear()      # harmless: an entry is a pure function of its key
        memo.flash_cache[key] = canon
    return _flash_at(z, t_c, p_bara, canon)


def _flash_at(z: dict, t_c: float, p_bara: float, canon: FlashResult) -> FlashResult:
    """The caller's flash from the bin's canonical K: Rachford-Rice at the caller's OWN feed.

    ``K = y/x`` is the part of a gamma-phi flash that varies slowly with feed composition;
    x, y and the vapour fraction are not — ``y_i`` of a trace volatile is close to
    proportional to its own feed fraction. Serving the canonical point's x and y to every
    caller in the bin handed a stage the vapour of a DIFFERENT liquor: at 323F004 the bin is
    1.5 % wide in CO2, and a consumer taking ``alpha_i = y_i / w_i`` off it saw that 1.5 %
    as a step.

    Re-solving the material balance with the stored K costs one bisection — no activity
    model, no fugacity — and makes x, y and psi exact for the caller's feed, consistent with
    its mass balance, and continuous across the bin.
    """
    k = canon.k
    z_mole = mass_to_mole(z)
    psi = rachford_rice(z_mole, k)
    x_mole, y_mole = {}, {}
    for s in SPECIES:
        denom = 1.0 + psi * (k[s] - 1.0)
        xs = z_mole[s] / denom if denom > 1e-12 else z_mole[s]
        x_mole[s] = max(xs, 0.0)
        y_mole[s] = max(k[s] * xs, 0.0)
    sx, sy = sum(x_mole.values()), sum(y_mole.values())
    if sx > 0.0:
        x_mole = {s: v / sx for s, v in x_mole.items()}
    if sy > 0.0:
        y_mole = {s: v / sy for s, v in y_mole.items()}
    x, y = mole_to_mass(x_mole), mole_to_mass(y_mole)
    mw_x = sum(x_mole[s] * MW[s] for s in SPECIES)
    mw_y = sum(y_mole[s] * MW[s] for s in SPECIES)
    denom = (1.0 - psi) * mw_x + psi * mw_y
    psi_mass = (psi * mw_y / denom) if denom > 0.0 else 0.0
    return FlashResult(psi, psi_mass, x, y, k, t_c, p_bara, canon.domain,
                       canon.iterations, canon.residual, canon.converged)


def _flash_solve(z_mass: dict, t_c: float, p_bara: float,
                 outer_iters: int = FLASH_OUTER_ITERS, tol: float = FLASH_TOL,
                 warm: bool = True) -> FlashResult:
    """Isothermal (T, P) flash of overall mass composition ``z_mass``.

    gamma-phi outer loop: K depends on the liquid composition through the activity model
    and on the vapour composition through SRK, so the Rachford-Rice solve is wrapped in a
    successive-substitution loop on (x, y) until both are stationary.
    """
    z = norm_mass(z_mass)
    domain = classify(z, t_c, p_bara)
    if domain is None:
        raise OutOfDomain(
            f"no fitted model owns this state: {domain_report(z, t_c, p_bara)}")

    if domain == DOMAIN_NEUTRAL_UREA:
        # The neutral binary owns WATER activity in a urea melt and nothing else — it has
        # no NH3 or CO2 at all. Their partial pressures would have to come from the
        # electrolyte path, and in a 97.7 wt% urea / 1.4 wt% water melt that path is not in
        # its dilute limit: the loading basis is mol per kg of WATER, so 0.04 wt% NH3 reads
        # as 1.69 mol/kg and the flash returns an NH3 vapour mole fraction of 0.24 for a
        # melt whose vapour is essentially pure steam.
        #
        # bubble_p / bubble_t stay available here (water-only duty, +2.2 % at 324E003); a
        # VOLATILE SPLIT does not, so 324E001/E003 keep their anchored vapour vector until
        # a urea-melt NH3/CO2 solubility source exists. See handoff.md B-1.
        raise OutOfDomain(
            "flash() is not defined on DOMAIN_NEUTRAL_UREA: the neutral binary carries no "
            "NH3/CO2 and the electrolyte path is outside its dilute limit in a urea melt. "
            f"bubble_p/bubble_t remain valid here. {domain_report(z, t_c, p_bara)}")

    z_mole = mass_to_mole(z)

    # WARM START. Successive substitution from x = z needs ~22 damped sweeps; from a nearby
    # converged liquid it needs 2-4. The engine calls each stage every tick with a
    # composition that has barely moved, so the previous answer for that stage is an
    # excellent guess. The warm cache is keyed on a COARSE (T, P) bucket, which separates
    # the stages from one another without the call site carrying any state. It changes
    # iteration count only — the fixed point of the map is unchanged.
    warm_key = (round(t_c / memo.WARM_T_BUCKET_C),
                round(p_bara / memo.WARM_P_BUCKET_BARA))
    # The MEMOISED path passes warm=False. A warm start changes where successive
    # substitution stops inside `tol`, and it is keyed on whatever that coarse bucket
    # converged last — so a memo entry solved from it would depend on call history, which
    # is exactly what the canonical point exists to remove.
    x = dict((memo.warm_start.get(warm_key) if warm else None) or z)
    if abs(sum(x.values()) - 1.0) > 1.0e-6:            # guard a corrupt warm entry
        x = dict(z)

    y_mole = None
    psi = 0.0
    psi_prev = float("inf")
    resid = float("inf")
    prev_resid = float("inf")
    damping = _SS_DAMPING
    it = 0
    k = {s: 0.0 for s in SPECIES}

    for it in range(1, outer_iters + 1):
        k = k_values(x, t_c, p_bara, y_mole=y_mole, domain=domain)
        psi = rachford_rice(z_mole, k)
        x_mole = {}
        y_mole_new = {}
        for s in SPECIES:
            denom = 1.0 + psi * (k[s] - 1.0)
            xs = z_mole[s] / denom if denom > 1e-12 else z_mole[s]
            x_mole[s] = max(xs, 0.0)
            y_mole_new[s] = max(k[s] * xs, 0.0)
        sx = sum(x_mole.values())
        sy = sum(y_mole_new.values())
        if sx > 0.0:
            x_mole = {s: v / sx for s, v in x_mole.items()}
        if sy > 0.0:
            y_mole_new = {s: v / sy for s, v in y_mole_new.items()}
        x_new = mole_to_mass(x_mole)

        # The residual must include PSI, not only the liquid. Near the bubble point psi is
        # tiny, so x ~= z and an x-only criterion is satisfied while psi is still moving —
        # measured psi = 1.4e-4 at a state whose true value is ~1e-10. x alone converges;
        # the pair does not until the vapour fraction has settled too.
        resid = max(max(abs(x_new[s] - x[s]) for s in SPECIES), abs(psi - psi_prev))
        psi_prev = psi

        # ADAPTIVE damping. K depends on x through a speciating electrolyte model whose
        # a_CO2 spans four decades, so the UNDAMPED map oscillates instead of contracting —
        # measured non-convergent in 40 sweeps at both 323C003 and 323F004. But a FIXED 0.5
        # factor caps the contraction rate at 0.5 per sweep, which costs ~30 sweeps to
        # reach tol and dominates the runtime. So: take the full step while the residual is
        # falling, and halve the factor only on a sweep that made it worse, relaxing back
        # toward 1 afterwards. The fixed point of the map is untouched either way — this
        # changes iteration count, not the answer.
        if resid > prev_resid:
            damping = max(damping * 0.5, 0.05)
        else:
            damping = min(damping * 1.5, 1.0)
        prev_resid = resid

        x = {s: x[s] + damping * (x_new[s] - x[s]) for s in SPECIES}
        y_mole = y_mole_new
        if resid < tol:
            break

    if resid < tol and warm:
        memo.warm_start[warm_key] = dict(x)            # only cache a CONVERGED liquid

    y = mole_to_mass(y_mole) if y_mole else {s: 0.0 for s in SPECIES}
    mw_x = sum(mass_to_mole(x)[s] * MW[s] for s in SPECIES)
    mw_y = sum((y_mole or {}).get(s, 0.0) * MW[s] for s in SPECIES)
    denom = (1.0 - psi) * mw_x + psi * mw_y
    psi_mass = (psi * mw_y / denom) if denom > 0.0 else 0.0
    return FlashResult(psi, psi_mass, x, y, k, t_c, p_bara, domain, it, resid, resid < tol)


# ======================================================================================
# Isenthalpic (P, H) flash
# ======================================================================================

def stream_enthalpy_kj_per_kg(w_mass: dict, t_c: float, phase: str) -> float:
    """Absolute specific enthalpy [kJ/kg] on the elements-at-298.15 K datum."""
    w = norm_mass(w_mass)
    # 1 kg basis: kmol/h numerically equals kmol per kg here, and `h0_stream` returns an
    # INTENSIVE kJ/kg, so the arbitrary basis cancels exactly.
    n = {k: w[k] / MW[k] for k in SPECIES if w[k] > 0.0}
    if not n:
        return 0.0
    res = h0.h0_stream(n, t_c, phase)
    h = res.get("enthalpy_kJkg")
    return float(h) if h is not None else 0.0


def mixture_enthalpy_kj_per_kg(fr: FlashResult) -> float:
    """Two-phase specific enthalpy of a converged flash, mass-weighted across the phases."""
    h_l = stream_enthalpy_kj_per_kg(fr.x, fr.t_c, "liquid")
    h_v = stream_enthalpy_kj_per_kg(fr.y, fr.t_c, "vapor") if fr.psi_mass > 0.0 else 0.0
    return (1.0 - fr.psi_mass) * h_l + fr.psi_mass * h_v


def flash_ph(z_mass: dict, h_kj_per_kg: float, p_bara: float,
             t_lo: float = None, t_hi: float = None,
             tol: float = 1.0e-4) -> FlashResult:
    """Isenthalpic (P, H) flash: find T at which the two-phase enthalpy equals ``h``.

    Process utility
    ---------------
    This is the letdown-valve boundary — ``h_in(T1,P1) = h_out(T2,P2)`` — and the
    replacement for every constant Joule-Thomson coefficient in the engine. Enthalpy is on
    the H0 tier, the same datum every published stream enthalpy uses, so a PH flash and a
    published stream enthalpy cannot disagree.

    Bisection on ``h(T) - h``, which is monotone increasing in T.
    """
    z = norm_mass(z_mass)
    dom_mid = classify(z, 0.5 * sum(vle.envelope()["t_c"]), p_bara)
    if dom_mid == DOMAIN_NEUTRAL_UREA:
        lo_d, hi_d = (neutral.VALID_TEMPERATURE_K[0] - 273.15,
                      neutral.VALID_TEMPERATURE_K[1] - 273.15)
    else:
        lo_d, hi_d = vle.envelope()["t_c"][0], vle.envelope()["t_c"][1]
    lo = lo_d if t_lo is None else max(t_lo, lo_d)
    hi = hi_d if t_hi is None else min(t_hi, hi_d)
    if lo >= hi:
        raise OutOfDomain(f"empty bracket for flash_ph: {domain_report(z, lo, p_bara)}")

    def _h(t_c):
        return mixture_enthalpy_kj_per_kg(flash(z, t_c, p_bara))

    h_lo, h_hi = _h(lo), _h(hi)
    if h_kj_per_kg <= h_lo:
        return flash(z, lo, p_bara)
    if h_kj_per_kg >= h_hi:
        return flash(z, hi, p_bara)
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if _h(mid) < h_kj_per_kg:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return flash(z, 0.5 * (lo + hi), p_bara)


# ======================================================================================
# Lifecycle
# ======================================================================================

def flash_cache_clear() -> None:
    """Drop every memoised solve. Safe at any time — see `thermo.memo`."""
    memo.clear()


def prime() -> str:
    """Build or load the electrolyte table now, so the first engine tick is not charged."""
    vle.prime()
    return MODEL_NAME


__all__ = [
    "MODEL_NAME", "MW", "SPECIES", "NONVOLATILE", "VOLATILE", "INERTS", "DISTRIBUTING",
    "DOMAIN_ELECTROLYTE", "DOMAIN_NEUTRAL_UREA",
    "UREA_NEUTRAL_THRESHOLD", "VOLATILE_TRACE_LOADING", "FLASH_TOL", "FLASH_OUTER_ITERS",
    "OutOfDomain", "FlashResult",
    "norm_mass", "mass_to_mole", "mole_to_mass",
    "classify", "domain_report",
    "partial_pressures", "vapour_fugacity", "k_values", "k_ratio",
    "bubble_p", "bubble_t", "dew_t",
    "ratio_shift_frac", "anchored_split", "saturated_inert_vent",
    "rachford_rice", "flash", "flash_ph",
    "stream_enthalpy_kj_per_kg", "mixture_enthalpy_kj_per_kg",
    "flash_cache_stats", "bubble_t_cache_stats", "flash_cache_clear", "prime",
]
