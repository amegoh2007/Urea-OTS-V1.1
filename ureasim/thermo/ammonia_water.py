"""The desorption train's liquor: ammonia water, its design anchor, its Kremser volatility.

What this models
----------------
Every stage of unit 328 — 328C002 and 328C004, the two desorbers, and 328C003, the hydrolyser
between them — holds the same dilute liquor: process condensate carrying a few per cent of
ammonia and carbon dioxide, under a per cent of urea, and water. This module is that liquor's
physics, with no plant knowledge in it: how a stage's design point is read off the licensor's
stream table, how a lumped single-stage volatility is made to move with a real tray count, and
what vapour pressure the liquor carries into a letdown valve.

The species balance each stage integrates is the urea liquor's (`thermo.urea_liquor`):

    d(M . w_i)/dt = sum_f m_f . w_f,i - m_liq . w_i - m_vap . y_i + nu_i . xi ,    sum w = sum y = 1

with the vapour ``y_i = alpha_i . w_i / sum_j alpha_j . w_j`` (the C6 summation,
`thermo.urea_liquor.vapour_y`) and the reaction, where there is one, urea HYDROLYSIS

    NH2CONH2 + H2O  ->  2 NH3 + CO2                                          (xi, kmol/h)

rather than biuret formation. What differs from the urea liquor, and lives here:

  * **the PFD's composition units.** Liquid rows are mass %, vapour rows mole %; read all as
    mass % and carbon is not conserved across 328C002 (1658 kg/h of CO2 in, 858 out). The
    "average molar weight" row discriminates: stream 737 reproduces its tabulated 20.81 read as
    mole %, and gives 18.94 read as mass % (V1 AUDIT F-8);
  * **the design back-solve over N feeds** — 328C002 has four inlets — with the hydrolysis
    extent read off the urea that disappears across the stage;
  * **the Kremser correction.** A back-solved alpha is a LUMPED single-stage volatility: it
    makes one well-mixed stage do what a trayed column does. For a trace species leaving a
    stage, ``m_vap . alpha / (m_vap . alpha + m_liq) = 1 - r``, which inverts to

        alpha_eff = (L / V) (1 - r) / r ,      r = (S - 1) / (S^(N+1) - 1) ,   S = K . V / L

    — Kremser's (1930) residual liquid fraction for N theoretical stages. Taken as a RATIO of
    live over design, the correction is an identity of the lumped form and exactly 1 at design;
  * **the rigorous temperature and pressure derivative** of the relative volatility, from
    `thermo.service.k_ratio` on the stage's own liquid, held just inside the 80-210 C envelope
    the parameter set was fitted on so the ratio cannot jump back onto design at the edge;
  * **the liquor's vapour pressure** at a letdown valve — the flash choke of IEC 60534;
  * **the purified condensate's conductivity**, AI-328701's reading: NH3 as a weak base, the
    urea slip partly hydrolysed in the hot line, Kohlrausch's independent ionic conductivities.

Everything is anchored: at the design liquid the vapour is the design vapour and dw/dt is
zero, so this layer cannot move the heat and material balance.

Source
------
Ported from V1 ``backend/main.py``, the "AUDIT F-8 rigorous species layer through the
desorption train" block (2925-3280): ``_w_from_molepct``, ``_des_stage_anchor``, ``_mw_of``,
``_des_kfac``, ``des_rel_vol_ratio``, ``liquor_pv_bara`` and ``DES_HYD_NU``; ``_kremser_resid``
and ``cond_infer_328701`` from the AI-328701 block (180-222). The rows it is anchored on are in
`ureasim.data.desorption_train`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ureasim.thermo import iapws, service
from ureasim.thermo.domains import MW, OutOfDomain
from ureasim.thermo.urea_liquor import ANCHOR_NONVOLATILE, SOLUTION_SPECIES, VAPOUR_FLOOR

#: The volatile pair a desorber strips, each carrying its own Kremser bracket. Water is the
#: reference (alpha 1) and urea does not strip. Source: V1 `main.py` R328_DES_VOLATILE.
VOLATILE = ("NH3", "CO2")

#: The species `thermo.service.k_ratio` is asked for. Source: V1 `main.py` R328_KR_SPECIES.
K_RATIO_SPECIES = ("NH3", "CO2", "H2O")

#: The temperature window the relative-volatility ratio and the liquor's bubble pressure are
#: evaluated in [deg C]: just inside the 80-210 C the parameter set was regressed on. Off-grid
#: `k_ratio` returns 1.0, so a stage crossing an edge would JUMP back onto its design volatility
#: (V1 measured 5.3 % on NH3 at the hydrolyser between 209.9 and 210.1 C); held inside, the ratio
#: is continuous and flat beyond. Source: V1 `main.py` R328_KR_T_LO_C, R328_KR_T_HI_C.
K_RATIO_T_LO_C = 80.05
K_RATIO_T_HI_C = 209.95

#: kg of each species made (+) or used (-) per kmol of urea hydrolysed. CO2 is written as the
#: closer, not as its own molar mass: the NH3 molar mass rounds to 17.0304 where the reaction
#: needs 17.0307, and literal coefficients would leave 6e-4 kg/kmol unbalanced — a mass source,
#: however small. Source: V1 `main.py` DES_HYD_NU.
HYDROLYSIS_NU = {"Urea": -MW["Urea"], "H2O": -MW["H2O"], "NH3": 2.0 * MW["NH3"]}
HYDROLYSIS_NU["CO2"] = -(HYDROLYSIS_NU["Urea"] + HYDROLYSIS_NU["H2O"] + HYDROLYSIS_NU["NH3"])

#: Numerical floors, all V1's own; none binds at a physical state.
MASS_FLOOR = 1e-12          # a species fraction worth a volatility [-]
FLOW_FLOOR = 1e-9           # a stage flow in the L / V ratio [kg/h]
RESIDUAL_FLOOR = 1e-12      # a Kremser residual [-]
S_UNITY_BAND = 1e-9         # |S - 1| inside which Kremser takes its limit [-]


def mass_fractions_from_mole_pct(row: dict) -> dict:
    """A PFD VAPOUR row, in mole %, as mass fractions over the liquor's species.

    Process utility
    ---------------
    The licensor tabulates gas and vapour streams in mole % and liquid streams in mass %.
    Reading an overhead row as mass % silently destroys carbon across every desorber, so each
    vapour row passes through here once, at the boundary.

    Equation
    --------
        w_i = x_i . MW_i / sum_j x_j . MW_j

    Source: V1 `main.py` `_w_from_molepct`.
    """
    m = {k: row.get(k, 0.0) * MW[k] for k in SOLUTION_SPECIES}
    tot = sum(m.values())
    return {k: m[k] / tot for k in SOLUTION_SPECIES}


def vapour_molar_mass(w: dict) -> float:
    """Mean molar mass of a vapour [kg/kmol] from its mass fractions.

    Process utility
    ---------------
    Turns an overhead's kg/h into the kmol/h its pressure node integrates, and carries the
    w ~ sqrt(M) dependence of a compressible valve law: a lighter NH3-rich overhead passes
    fewer kilograms through the same restriction.

    Equation
    --------
        M = 1 / sum_i (w_i / MW_i)          over the species present

    Source: V1 `main.py` `_mw_of`.
    """
    return 1.0 / sum(w[k] / MW[k] for k in w if w.get(k, 0.0) > 0.0)


@dataclass(frozen=True)
class DesorberAnchor:
    """One unit-328 stage's design point, back-solved from its PFD rows."""

    #: Urea hydrolysis extent at design [kmol/h]; zero on a desorber.
    xi: float
    #: Design vapour mass fractions.
    y: dict
    #: Lumped relative volatility against water [-]; water is 1 by definition.
    alpha: dict
    #: Negative vapour that had to be clipped to close the balance [kg/h]. Reported, never hidden.
    resid: float
    #: Largest departure of the back-solved vapour from the PFD's own overhead row [-], where
    #: the PFD tabulates one — an independent check, never fed back.
    dev: float


def desorber_stage_anchor(feeds, w_out: dict, m_liq: float, m_vap: float,
                          hydrolyse: bool = False, y_pfd: dict | None = None) -> DesorberAnchor:
    """Back-solve a unit-328 stage's design vapour and lumped volatilities from its PFD rows.

    Process utility
    ---------------
    Makes a stage close EXACTLY on the licensor's stream table, over as many feeds as it has:
    whatever comes in, plus what hydrolysis makes, less the liquid out, is the vapour — water
    closing the balance — and the vapour against the liquid is the volatility. The back-solve,
    not the PFD's overhead row, is what the stage then carries: it is what makes the design
    state a fixed point of the species balance.

    Equations
    ---------
        xi      = max( (sum_f m_f . w_f,U - m_liq . w_U) / MW_U , 0 )      (hydrolyse only)
        vap_i   = sum_f m_f . w_f,i + nu_i . xi - m_liq . w_i               (clipped at 0)
        vap_H2O = m_vap - sum_(i != H2O) vap_i
        y_i     = vap_i / m_vap
        alpha_i = (y_i / w_i) / (y_H2O / w_H2O)

    ``feeds`` is a sequence of (w, kg/h) pairs.

    Source: V1 `main.py` `_des_stage_anchor`.
    """
    m_i = {k: 0.0 for k in SOLUTION_SPECIES}
    for w, m in feeds:
        for k in SOLUTION_SPECIES:
            m_i[k] += m * w[k]
    xi = max((m_i["Urea"] - m_liq * w_out["Urea"]) / MW["Urea"], 0.0) if hydrolyse else 0.0
    gen = {k: 0.0 for k in SOLUTION_SPECIES}
    gen["Urea"] = -xi * MW["Urea"]
    gen["H2O"] = -xi * MW["H2O"]
    gen["NH3"] = +xi * 2.0 * MW["NH3"]
    gen["CO2"] = +xi * MW["CO2"]
    vap = {k: m_i[k] + gen[k] - m_liq * w_out[k] for k in SOLUTION_SPECIES}
    resid = sum(v for v in vap.values() if v < 0.0)
    for k in SOLUTION_SPECIES:
        if k in ANCHOR_NONVOLATILE or vap[k] < 0.0:
            vap[k] = 0.0
    vap["H2O"] += m_vap - sum(vap.values())     # water closes the balance (reference species)
    y = {k: vap[k] / m_vap for k in SOLUTION_SPECIES} if m_vap > VAPOUR_FLOOR else dict(w_out)
    aw = y["H2O"] / w_out["H2O"]
    alpha = {k: ((y[k] / w_out[k]) / aw if (w_out[k] > MASS_FLOOR and k not in ANCHOR_NONVOLATILE)
                 else 0.0)
             for k in SOLUTION_SPECIES}
    alpha["H2O"] = 1.0                          # reference species, by definition
    dev = max(abs(y[k] - y_pfd[k]) for k in SOLUTION_SPECIES) if y_pfd else 0.0
    return DesorberAnchor(xi=xi, y=y, alpha=alpha, resid=resid, dev=dev)


def kremser_residual(s: float, n_theo: float) -> float:
    """Kremser's residual liquid fraction x_out / x_in of a stripping section [-].

    Process utility
    ---------------
    How much of a volatile a trayed stripper leaves in its bottoms. It is what makes a 15-tray
    column and a single flash degrade differently when the stripping vapour falls away.

    Equation
    --------
        r = (S - 1) / (S^(N+1) - 1) ,    S = K . V / L          (r = 1 / (N + 1) at S = 1)

    Source: V1 `main.py` `_kremser_resid` (Kremser, 1930).
    """
    if abs(s - 1.0) < S_UNITY_BAND:
        return 1.0 / (n_theo + 1.0)
    return (s - 1.0) / (s ** (n_theo + 1.0) - 1.0)


def kremser_volatility(m_liq: float, m_vap: float, r: float) -> float:
    """The single-stage-equivalent volatility that reproduces a Kremser residual [-].

    Process utility
    ---------------
    Converts a trayed column's residual into the lumped alpha one well-mixed stage needs to
    strip the same fraction — the bridge between the column's tray count and the lumped form.

    Equation
    --------
        alpha_eff = (L / V) (1 - r) / r

    Source: V1 `main.py` `_des_kfac`.
    """
    return (m_liq / max(m_vap, FLOW_FLOOR)) * (1.0 - r) / max(r, RESIDUAL_FLOOR)


@dataclass(frozen=True)
class DesorberStage:
    """One desorber section's lumped volatility and the Kremser terms it is carried on."""

    #: The design back-solve: vapour and lumped alphas.
    anchor: DesorberAnchor
    #: Theoretical stages [-], the stripping vapour and the bottoms at design [kg/h], and the
    #: bottom node's pressure [bar a] and water's bubble point there [deg C] at design.
    n_theo: float
    v_kgh: float
    l_kgh: float
    p_bara: float
    t_eq_c: float
    #: The stripping-factor coefficient [-], and at design the stripping factor, the Kremser
    #: residual and the single-stage volatility.
    k_inf: float
    s: float
    r: float
    k: float


def desorber_stage(anchor: DesorberAnchor, n_theo: float, v_kgh: float, l_kgh: float,
                   p_bara: float, k_inf: float) -> DesorberStage:
    """A desorber section's Kremser terms at design, in V1's order.

    Process utility
    ---------------
    Fixes the reference the live volatility is taken against. The reference temperature is the
    expression the tick writes — water's bubble point at the bottom node — so at the seed
    pressure the live and reference arguments are the same floats and every ratio is 1.

    Equations
    ---------
        S = K_inf . V / L ,   r = kremser_residual(S, N) ,   k = (L / V)(1 - r) / r ,
        T_eq = T_sat,water(P)

    Source: V1 `main.py`, ``DES_STAGES`` and the loop over it (3147-3175).
    """
    s = k_inf * (v_kgh / l_kgh)
    r = kremser_residual(s, n_theo)
    return DesorberStage(anchor=anchor, n_theo=n_theo, v_kgh=v_kgh, l_kgh=l_kgh, p_bara=p_bara,
                         t_eq_c=iapws.tsat_c(p_bara), k_inf=k_inf, s=s, r=r,
                         k=kremser_volatility(l_kgh, v_kgh, r))


def relative_volatility_ratio(w: dict, t_c: float, p_bara: float,
                              t_ref_c: float, p_ref_bara: float) -> tuple[dict, str | None]:
    """alpha_i(live) / alpha_i(design) for NH3 and CO2, relative to water, and the VLE domain.

    Process utility
    ---------------
    The rigorous model's TEMPERATURE and PRESSURE derivative of a desorber's volatility, on the
    stage's own liquid. It carries the sign a van't Hoff factor got wrong: a desorber held
    higher boils hotter, and NH3's relative volatility FALLS (water's vapour pressure climbs
    faster than NH3's Henry constant), while CO2's rises (carbamate re-speciation). Exactly 1.0
    at the reference state; the domain string is published as telemetry.

    Equation
    --------
        ratio_i = [K_i(T, P) / K_H2O(T, P)] / [K_i(T_ref, P_ref) / K_H2O(T_ref, P_ref)]

    on the live composition, T held inside [80.05, 209.95] C.

    Source: V1 `main.py` `des_rel_vol_ratio` (which also records the domain for telemetry).
    """
    t_eval = min(max(t_c, K_RATIO_T_LO_C), K_RATIO_T_HI_C)
    kr = service.k_ratio(w, t_eval, p_bara, t_ref_c, p_ref_bara, species=K_RATIO_SPECIES)
    domain = service.classify(w, t_eval, p_bara)
    return {k: kr[k] / kr["H2O"] for k in VOLATILE}, domain


def liquor_pv_bara(w: dict, t_c: float) -> float:
    """The vapour pressure a unit-328 liquor carries into its level valve [bar a].

    Process utility
    ---------------
    The Pv of the IEC 60534 choke: where a letdown drops the liquor below it, the valve
    flashes and stops passing more. The liquor's own gamma-phi bubble pressure, not water's —
    0.63 % NH3 lifts stream 746 from 12.55 to 14.97 bar a at 190 C.

    Equation
    --------
        Pv = P_bubble(w, T)                                  inside [80.05, 209.95] C
        Pv = P_bubble(w, T_edge) . Psat_w(T) / Psat_w(T_edge)  beyond, carried on the water line

    Off the fitted domain, water's saturation pressure is returned.

    Source: V1 `main.py` `liquor_pv_bara`.
    """
    t_eval = min(max(t_c, K_RATIO_T_LO_C), K_RATIO_T_HI_C)
    try:
        pb = service.bubble_p(w, t_eval)
    except (OutOfDomain, ValueError, ZeroDivisionError):
        return iapws.psat_bara(t_c)
    return pb if t_eval == t_c else pb * iapws.psat_bara(t_c) / iapws.psat_bara(t_eval)


# ======================================================================================
# AI-328701: the purified condensate's conductivity
# ======================================================================================

#: The fraction of the urea slip that hydrolyses in the hot condensate line before the analyser,
#: adding to both ion pools [-]. V1's value, no source (`main.py` R328_AI701_UREA_PHI).
AI701_UREA_PHI = 0.05
#: NH3's base dissociation constant at 25 C [mol/L], and the limiting molar ionic
#: conductivities of NH4+, OH- and HCO3- at 25 C [S cm2/mol]. Source: CRC Handbook, via V1
#: `main.py` R328_AI701_KB_NH3, R328_AI701_L0_NH4, R328_AI701_L0_OH, R328_AI701_L0_HCO3.
AI701_KB_NH3 = 1.8e-5
AI701_L0_NH4 = 73.5
AI701_L0_OH = 198.0
AI701_L0_HCO3 = 44.5
#: The molar masses the analyser's inference is written on [kg/kmol] — V1's own three literals,
#: 17.0304, 60.056 and 44.01, not the property table's (`main.py` _R328_MW_*).
AI701_MW_NH3 = 17.0304
AI701_MW_UREA = 60.056
AI701_MW_CO2 = 44.01


def condensate_conductivity_us_cm(nh3_ppm: float, urea_ppm: float, co2_ppm: float) -> float:
    """The purified condensate's conductivity, temperature-compensated to 25 C [uS/cm].

    Process utility
    ---------------
    AI-328701 on stream 740 is how the operator sees the desorption train's slip: ammonia a
    stripping loss lets through ionises and lifts the reading, so a cut in 328C004's LP steam
    shows here before it shows in a laboratory result. Urea is non-ionic, but the part that
    hydrolyses in the hot line adds to both ion pools, so a hydrolyser upset moves it too.

    Equation
    --------
        c_hyd = c_urea . phi
        c_NH3 = nh3 / M_NH3 + 2 c_hyd,   c_CO2 = co2 / M_CO2 + c_hyd        [mol/L]
        [OH-] = (-Kb + sqrt(Kb^2 + 4 Kb c_NH3)) / 2                          weak base
        [HCO3-] = c_CO2,   [NH4+] = [OH-] + [HCO3-]                           charge balance
        kappa = ([NH4+] L_NH4 + [OH-] L_OH + [HCO3-] L_HCO3) / 1000 . 1e6     Kohlrausch

    Source: V1 `main.py` `cond_infer_328701`.
    """
    c_urea = max(urea_ppm, 0.0) * 1e-3 / AI701_MW_UREA
    hyd = c_urea * AI701_UREA_PHI
    c_nh3 = max(nh3_ppm, 0.0) * 1e-3 / AI701_MW_NH3 + 2.0 * hyd
    c_co2 = max(co2_ppm, 0.0) * 1e-3 / AI701_MW_CO2 + hyd
    kb = AI701_KB_NH3
    oh = (-kb + math.sqrt(kb * kb + 4.0 * kb * c_nh3)) / 2.0
    hco3 = c_co2
    nh4 = oh + hco3
    return (nh4 * AI701_L0_NH4 + oh * AI701_L0_OH + hco3 * AI701_L0_HCO3) / 1000.0 * 1e6


__all__ = [
    "VOLATILE", "K_RATIO_SPECIES", "K_RATIO_T_LO_C", "K_RATIO_T_HI_C", "HYDROLYSIS_NU",
    "MASS_FLOOR", "FLOW_FLOOR", "RESIDUAL_FLOOR", "S_UNITY_BAND",
    "mass_fractions_from_mole_pct", "vapour_molar_mass", "DesorberAnchor",
    "desorber_stage_anchor", "kremser_residual", "kremser_volatility", "DesorberStage",
    "desorber_stage",
    "relative_volatility_ratio", "liquor_pv_bara",
    "AI701_UREA_PHI", "AI701_KB_NH3", "AI701_L0_NH4", "AI701_L0_OH", "AI701_L0_HCO3",
    "AI701_MW_NH3", "AI701_MW_UREA", "AI701_MW_CO2", "condensate_conductivity_us_cm",
]
