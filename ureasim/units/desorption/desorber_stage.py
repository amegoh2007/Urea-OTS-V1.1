"""A desorption-train stage's species balance: its live volatility and its implicit step.

What this models
----------------
Each unit-328 column — 328C002 and 328C004, and the hydrolyser 328C003 between them — carries
its liquid as a species vector over the liquor's six species, stepped from its own total-mass
balance. This module is the part the three share:

  * **the live lumped volatility.** A column's back-solved alpha makes one well-mixed stage
    strip what the column's trays strip at design. Off design the stripping factor moves with
    the vapour-to-liquid ratio and with the rigorous model's temperature and pressure
    derivative of each volatile's relative volatility, and the lumped alpha moves with the
    Kremser single-stage equivalent of the column's real stage count:

        S_i     = K_inf . [alpha_i,model(T, P) / alpha_i,model(design)] . V / L       i = NH3, CO2
        alpha_i = alpha_i,des . k(S_i, N) / k(S_des, N) ,   k(S, N) = (L/V)(1 - r)/r

    Every factor is exactly 1.0 at the design seed, so the design alphas come back to the bit;

  * **the implicit species step.** The trace species are violently stiff: 328C004 holds
    1436 kg of liquid at 1 ppm ammonia — 1.4 g of NH3 — while 330 kg/h of it flows through,
    a time constant near 0.015 s. Explicit Euler overshoots, hits the non-negativity clamp and
    walks the train off its design point (V1 measured 328C002's ammonia creeping from 0.63 %
    to 2.2 % in four hours). With the summation's denominator lagged one step, the vapour is
    LINEAR in each species holdup — y_i = c_i . w_i, c_i = alpha_i / sum_j alpha_j w_j — so
    the implicit step closes in one line, is unconditionally stable, cannot go negative, and
    is exactly stationary where source equals sink:

        m_i,new = (M . w_i + src_i . h) / (1 + sink_i . h) ,    h = dt / 3600
        src_i   = sum_f m_f . w_f,i + nu_i . xi                 [kg/h]
        sink_i  = (m_vap . c_i + m_liq) / M                     [1/h]
        w_new   = m_new / sum m_new ,   y_new = vapour_y(w_new, alpha)

    M is the stage's NEW total holdup, from its own mass balance, so this layer cannot move the
    heat and material balance.

Source
------
V1 ``backend/main.py``, ``des_alpha_live`` and ``des_advance`` (3211-3280), with the reports
they cite (F-8, the Kremser correction; the implicit step). The design terms are built by
`thermo.ammonia_water.desorber_stage`; each column's are in its data module.
"""

from __future__ import annotations

from ureasim.core.numeric import clamp
from ureasim.thermo.ammonia_water import (
    FLOW_FLOOR,
    HYDROLYSIS_NU,
    VOLATILE,
    DesorberStage,
    kremser_residual,
    kremser_volatility,
    relative_volatility_ratio,
)
from ureasim.thermo.urea_liquor import MOLE_FLOOR, SOLUTION_SPECIES, vapour_y

#: Anti-overflow bounds on a live stripping factor and on the volatility's correction [-].
#: S^(N+1) with N near 14 goes infinite on a cold-start transient; both bounds are orders of
#: magnitude outside anything the plant reaches, so the design seed passes through untouched.
#: Source: V1 `main.py` `des_alpha_live`.
S_BOUNDS = (1e-6, 1e6)
K_RATIO_BOUNDS = (1e-6, 1e6)

#: Floors in the implicit step: the alpha-weighted sum and the stage holdup [kg]. V1's.
DENOMINATOR_FLOOR = MOLE_FLOOR
HOLDUP_FLOOR_KG = 1.0
TOTAL_FLOOR = 1e-12


def alpha_live(stage: DesorberStage, t_c: float, m_vap_kgh: float, m_liq_kgh: float,
               w: dict, p_bara: float) -> tuple[dict, str | None]:
    """A stage's live lumped volatilities, and the VLE domain they were evaluated in.

    Process utility
    ---------------
    What makes a column strip less when its stripping vapour falls away, and differently at a
    different pressure: a steam cut on 328C004 raises the ammonia in the purified condensate,
    and a desorber held higher boils hotter and strips its ammonia less well. ``t_c`` and
    ``p_bara`` are the bottom node, where the bubble point is written; ``m_vap_kgh`` is the
    stage's stripping vapour and ``m_liq_kgh`` its bottoms.

    Source: V1 `main.py` `des_alpha_live`.
    """
    a_rel, domain = relative_volatility_ratio(w, t_c, p_bara, stage.t_eq_c, stage.p_bara)
    vl = m_vap_kgh / max(m_liq_kgh, FLOW_FLOOR)
    out = dict(stage.anchor.alpha)
    for k in VOLATILE:
        s_live = clamp(stage.k_inf * a_rel[k] * vl, *S_BOUNDS)
        k_live = kremser_volatility(m_liq_kgh, m_vap_kgh, kremser_residual(s_live, stage.n_theo))
        out[k] = out[k] * clamp(k_live / stage.k, *K_RATIO_BOUNDS)
    return out, domain


def advance_species(w: dict, m_new_kg: float, feeds, m_vap_kgh: float, alpha: dict,
                    m_liq_kgh: float, xi_kmolh: float, dt: float) -> tuple[dict, dict]:
    """Step a stage's species holdup implicitly and return its new liquid and its vapour.

    Process utility
    ---------------
    Carries the ammonia, carbon dioxide and urea through the train as tracked quantities, so
    the hydrolyser's urea load and the purified condensate's ppm are mass-balance results,
    not constants. ``feeds`` is a sequence of (w, kg/h) pairs; ``xi_kmolh`` the hydrolysis
    extent (zero on a desorber). A stage with nothing left keeps its liquid.

    Source: V1 `main.py` `des_advance`.
    """
    den = sum(alpha.get(k, 0.0) * w.get(k, 0.0) for k in SOLUTION_SPECIES)
    c = ({k: alpha.get(k, 0.0) / den for k in SOLUTION_SPECIES} if den > DENOMINATOR_FLOOR
         else {k: 0.0 for k in SOLUTION_SPECIES})          # y_k = c_k . w_k
    m = max(m_new_kg, HOLDUP_FLOOR_KG)
    h = dt / 3600.0
    out = {}
    for k in SOLUTION_SPECIES:
        f_in = 0.0
        for w_f, m_f in feeds:
            f_in += m_f * w_f.get(k, 0.0)
        src = f_in + HYDROLYSIS_NU.get(k, 0.0) * xi_kmolh   # kg/h into the liquid
        sink = (m_vap_kgh * c[k] + m_liq_kgh) / m          # 1/h, the coefficient on m_k
        out[k] = max((m * w.get(k, 0.0) + src * h) / (1.0 + sink * h), 0.0)
    tot = sum(out.values())
    if tot <= TOTAL_FLOOR:
        return dict(w), vapour_y(w, alpha)
    w_new = {k: out[k] / tot for k in SOLUTION_SPECIES}   # C6: renormalise to sum w == 1
    return w_new, vapour_y(w_new, alpha)


__all__ = [
    "S_BOUNDS", "K_RATIO_BOUNDS", "DENOMINATOR_FLOOR", "HOLDUP_FLOOR_KG", "TOTAL_FLOOR",
    "alpha_live", "advance_species",
]
