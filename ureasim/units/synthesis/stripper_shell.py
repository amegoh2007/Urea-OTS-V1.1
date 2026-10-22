"""322E001's shell — what the split asks of the MP steam, and what the shell can give.

What this models
----------------
The shell side of the HP stripper: 329D005's MP steam condensing on 1 519 m2 of tubes whose
liquor runs from TT-322013's temperature at the top to TT-322004's at the bottom. Two questions
are answered here, and `stripper.stripper_322e001` asks both on every tick:

1. **What the split costs** — the per-species enthalpy balance of what the tube side lifts
   overhead and heats (V1's ``duty_raw_kw``): carbamate dissociated, free ammonia desorbed,
   water vaporised, urea hydrolysed and the two products' sensible heat.
2. **What the shell can give** (handoff B-102, decided 2026-10-21, option (b)) — the duty its
   area transfers at the live steam's temperature difference, on the design duty's anchor:

       Q_max = Q_des . LMTD(T_steam, T_top,des, T_bot,des) / LMTD_des

   When the split asks for more than Q_max . (1 + band) (`SHELL_DUTY_BAND`), the part of each of
   NH3, CO2 and H2O lifted overhead beyond what the CO2 sweep brings in as gas is scaled by
   lambda in [0, 1], solved so the balance equals Q_max . (1 + band); what is not lifted stays in
   the bottoms and leaves through LV-322501 to 323C003. V1 books whatever the split asks of the
   header — up to 78 MW of the 39.4 MW shell on a wide-open HV-322605 (As-Built §LXXVIII).
3. **What the tubes standing full take away** (handoff B-104, decided 2026-10-22) — a full
   LT-322501 sump holds its excess in the tubes above it (B-103); the submerged length runs no
   falling film, so the shell's capacity falls with the share of the bundle standing full, to
   322E003's flooded-surface floor, and the bottoms cool toward the crystallisation floor by the
   same factor:

       sigma = clamp(M_held / M_tubes, 0, 1),   f_sub = 1 - (1 - 0.30) . sigma
       Q_max' = f_sub . Q_max,   T_bot' = T_cryst + f_sub . (T_bot - T_cryst)

Why the design duty is the anchor
---------------------------------
322E001's process datasheet (UD-AU-322-EC-0003 page 4) prints 39 400 kW, saturated MP steam at
214 C and 20.5 bar a, the tube side 187 -> 172 C and 1 519 m2, and leaves the corrected mean
temperature difference and the heat-transfer coefficient blank; the vendor archive's 322E001 file
holds no thermal rating (handoff, open data gap). A U.A calculated from the datasheet's terminal
temperatures, 1 160.5 kW/K, would give 36.6 MW on the model's 19.7 bar a design steam — below the
design duty, so it would bind the seed. The bound is therefore the design duty scaled by the LMTD
over the design's, both on the model's own temperatures (211.62, 187 and 172 C): exactly the design
duty at the seed, and the band holds the seed's own drift unbound.

Why the tube side is held at its design profile
-----------------------------------------------
Only the steam's saturation is live (decided 2026-10-21, session 63). The stripper's TT-322004 and
TT-322013 are V1's load relations, not a heat balance, and they assume the shell delivered its
duty: a turndown spreads the duty over less liquor and heats the bottoms toward the steam, an
overload leaves them unstripped and as hot as the liquor fed, so both rise on either side of the
design. An LMTD on them peaks at the design and falls either way — measured on the unit, a 95 %
load kept 84 % of its lift and an 80 % load 42 %: a turndown starved by a shell that V1's own
temperatures say delivered in full. On the design tube profile the shell's capacity moves with
329D005's saturation alone, and the bound binds where the split asks more than that steam can
give: an overload, a wide-open HV-322605, a sagging header.

Source: As-Built Part LXXVIII (the prototype, session 62), Part LXXIX and Part LXXX; handoffs B-102
and B-104; V1 ``backend/main.py`` `stripper_322e001` for the balance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ureasim.core.numeric import clamp
from ureasim.core.stream import MW_COMP
from ureasim.data.unit_322e001 import (
    CP_BOTTOM,
    CP_GAS,
    DH_CARBAMATE_JMOL,
    DH_H2O_VAP_JMOL,
    DH_HYDROLYSIS_JMOL,
    DH_NH3_DESORB_JMOL,
    STEAM_T_DES_C,
    SUBMERGED_DUTY_FLOOR,
    T_BOTTOM_DES_C,
    T_CRYSTALLISATION_C,
    T_TOPGAS_DES_C,
    TUBES_FULL_KG,
)

__all__ = ["EnthalpyBalance", "enthalpy_balance", "shell_lmtd_k", "LMTD_DES_K",
           "shell_capacity_ratio", "submerged_fraction", "unsubmerged_factor",
           "submerged_bottoms_c", "LIFTED", "lifted_split", "bounded_split"]

#: The species the shell lifts overhead and the bound scales back: the two volatiles and the
#: water that vaporises with them. The inerts and the non-volatiles are not the shell's to lift.
LIFTED = ("NH3", "CO2", "H2O")

#: Bisection steps on lambda: 60 halvings of [0, 1] reach the float's resolution.
_BISECTION_STEPS = 60


# ======================================================================================
# What the split costs
# ======================================================================================

@dataclass(frozen=True)
class EnthalpyBalance:
    """The five terms of the duty a split asks of the MP header [kW], their sum, and the two
    desorbed molar flows the first two are charged on [kmol/h]."""

    q_carbamate_kw: float
    q_nh3_kw: float
    q_h2o_kw: float
    q_hydrolysis_kw: float
    q_sensible_kw: float
    total_kw: float
    n_co2_desorbed: float
    n_nh3_free: float


def enthalpy_balance(top: dict, bot: dict, sweep: dict, xi_hyd: float, t_bot_c: float,
                     t_top_c: float, t_feed_c: float) -> EnthalpyBalance:
    """The per-species enthalpy balance of a split — what the MP header has to pay for [kW].

    Process utility
    ---------------
    Five terms, every constant sourced. Unlike a feed-proportional stand-in this responds to
    COMPOSITION: a feed richer in carbamate costs more steam at the same tonnage.

      q_carb  carbamate dissociation, the dominant sink, about 58 % of the design duty
      q_nh3   desorption of the NH3 that was not carbamate-bound (supercritical: no latent)
      q_h2o   the small water fraction that vaporises overhead, about 7 %
      q_hyd   urea hydrolysis, liquid step only — NEGATIVE, it gives a little heat back
      q_sens  sensible heat of the two products relative to the feed temperature

    Each term subtracts the sweep gas, which arrives already hot and already gaseous and so is
    not something this unit has to pay to liberate. The NH3 pairing is 2:1 because that is the
    carbamate stoichiometry.

    Source: V1 ``backend/main.py`` `stripper_322e001`, its enthalpy block, term for term.
    """
    top_m = sum(top[k] * MW_COMP[k] for k in MW_COMP)
    bot_m = sum(bot[k] * MW_COMP[k] for k in MW_COMP)
    n_co2_desorb = max(top["CO2"] - sweep["CO2"], 0.0)
    n_nh3_free = max(top["NH3"] - sweep["NH3"] - 2.0 * n_co2_desorb, 0.0)
    q_carb_kw = n_co2_desorb * DH_CARBAMATE_JMOL / 3600.0
    q_nh3_kw = n_nh3_free * DH_NH3_DESORB_JMOL / 3600.0
    q_h2o_kw = max(top["H2O"] - sweep["H2O"], 0.0) * DH_H2O_VAP_JMOL / 3600.0
    q_hyd_kw = xi_hyd * DH_HYDROLYSIS_JMOL / 3600.0
    q_sens_kw = (bot_m * CP_BOTTOM * (t_bot_c - t_feed_c)
                 + top_m * CP_GAS * (t_top_c - t_feed_c)) / 3600.0
    return EnthalpyBalance(
        q_carbamate_kw=q_carb_kw, q_nh3_kw=q_nh3_kw, q_h2o_kw=q_h2o_kw,
        q_hydrolysis_kw=q_hyd_kw, q_sensible_kw=q_sens_kw,
        total_kw=q_carb_kw + q_nh3_kw + q_h2o_kw + q_hyd_kw + q_sens_kw,
        n_co2_desorbed=n_co2_desorb, n_nh3_free=n_nh3_free)


# ======================================================================================
# What the shell can give
# ======================================================================================

def shell_lmtd_k(t_steam_c: float, t_top_c: float, t_bot_c: float) -> float:
    """Log-mean temperature difference between the condensing shell and the tube side [K].

    Process utility
    ---------------
    The driving force the shell's area transfers its duty on. The steam condenses at one
    temperature, 329D005's saturation; the tube side runs from the top-gas temperature, where the
    liquor enters, to the bottoms'. A sagging MP header shrinks it, and with it the duty the shell
    can give, whatever the split asks.

    Equation
    --------
        dT_top = T_steam - T_top ,   dT_bot = T_steam - T_bot
        LMTD = (dT_bot - dT_top) / ln(dT_bot / dT_top)      (dT_top where the two are equal)

    Each end floored at 1e-6 K: a tube side at the shell's temperature transfers nothing, and the
    floor keeps the logarithm finite there rather than letting it divide by zero.
    """
    d_top = max(t_steam_c - t_top_c, 1e-6)
    d_bot = max(t_steam_c - t_bot_c, 1e-6)
    if abs(d_bot - d_top) < 1e-9:
        return d_top
    return (d_bot - d_top) / math.log(d_bot / d_top)


#: The design LMTD [K], 31.53 — on the model's own design temperatures, so the capacity ratio
#: is exactly 1.0 at the design seed. Derived, never entered.
LMTD_DES_K = shell_lmtd_k(STEAM_T_DES_C, T_TOPGAS_DES_C, T_BOTTOM_DES_C)


def shell_capacity_ratio(t_steam_c: float) -> float:
    """The duty the shell can transfer over its design duty, Q_max / Q_des [-].

    Process utility
    ---------------
    The shell's area and its coefficient are fixed, so what it can give moves with the driving
    force alone, the live steam's against the tube side's design profile (the module note):

        Q_max / Q_des = LMTD(T_steam, T_top,des, T_bot,des) / LMTD_des

    exactly 1.0 at the design steam (B-102). A header sagging from 19.7 to 18.9 bar a takes it to
    0.93; one raised to 20.5 bar a to 1.07.
    """
    return shell_lmtd_k(t_steam_c, T_TOPGAS_DES_C, T_BOTTOM_DES_C) / LMTD_DES_K


# ======================================================================================
# The tubes standing full (handoff B-104, decided 2026-10-22)
# ======================================================================================

def submerged_fraction(held_kg: float) -> float:
    """The share of the tube bundle standing full of liquor [-], sigma.

    Process utility
    ---------------
    How far a full sump has backed up into the tubes: the liquor LT-322501's sump holds back above
    it (B-103) over what the bundle holds standing full, 8 689 kg. Zero while the sump has room,
    one when the tubes are full to their top and the reactor's liquor backs up behind them.
    """
    return clamp(held_kg / TUBES_FULL_KG, 0.0, 1.0)


def unsubmerged_factor(held_kg: float) -> float:
    """What a partly submerged bundle still does, as a fraction of a dry one's [-], f_sub.

    Process utility
    ---------------
    A submerged tube runs no falling film: the steam still condenses on it, but the liquor
    standing in it is not spread into a film for the CO2 to strip. The shell's capacity falls
    linearly with the submerged share to 322E003's flooded-surface floor, the upper tubes still
    stripping:

        f_sub = 1 - (1 - 0.30) . sigma

    exactly 1.0 with nothing held back, so a sump with room is B-102's to the bit.
    """
    return 1.0 - (1.0 - SUBMERGED_DUTY_FLOOR) * submerged_fraction(held_kg)


def submerged_bottoms_c(t_bot_c: float, f_sub: float) -> float:
    """TT-322004 off a partly submerged bundle [deg C].

    Process utility
    ---------------
    The bottoms leave a flooded stripper colder: liquor standing in the lower tubes is not
    reheated as a film, and the sump below it cools toward the crystallisation floor, the floor
    its heat-loss law already tends to. The same factor that takes the shell's capacity scales the
    bottoms' excess over the floor:

        T_bot' = T_cryst + f_sub . (T_bot - T_cryst)

    Unchanged at f_sub = 1 and at or below the floor, which this never warms.
    """
    if f_sub >= 1.0 or t_bot_c <= T_CRYSTALLISATION_C:
        return t_bot_c
    return T_CRYSTALLISATION_C + f_sub * (t_bot_c - T_CRYSTALLISATION_C)


def lifted_split(top: dict, bot: dict, sweep: dict, lam: float) -> tuple[dict, dict]:
    """The split with what the tube side lifts overhead scaled by ``lam`` [kmol/h].

    Process utility
    ---------------
    A shell that cannot supply the heat cannot dissociate the carbamate or desorb the ammonia
    the calibrated split asks it to: those volatiles stay in the falling film and leave in the
    bottoms through LV-322501, to be decomposed in the LP section instead. The CO2 sweep arrives
    as gas and leaves overhead whatever the shell does, so only what is lifted beyond it scales:

        top_k' = b_k + lam . (top_k - b_k),  b_k = min(top_k, sweep_k),
        bot_k' = bot_k + (top_k - top_k')                         for NH3, CO2 and H2O

    Every other species, and every species' total, is untouched: the bound moves mass between
    the two products and creates none.
    """
    top_b, bot_b = dict(top), dict(bot)
    for k in LIFTED:
        base = min(top[k], sweep.get(k, 0.0))
        lifted = base + lam * (top[k] - base)
        bot_b[k] = bot[k] + (top[k] - lifted)
        top_b[k] = lifted
    return top_b, bot_b


def bounded_split(top: dict, bot: dict, sweep: dict, xi_hyd: float, t_bot_c: float,
                  t_top_c: float, t_feed_c: float, target_kw: float) -> tuple[float, dict, dict]:
    """The split whose enthalpy balance meets the shell's capacity: (lambda, top, bot).

    Process utility
    ---------------
    Solves for how much of the calibrated split the shell can actually pay for. The balance
    rises with lambda — every desorption term grows with what is lifted, and the sensible term
    moves only by the small difference between the two products' heat capacities — so a
    bisection on [0, 1] finds the lambda whose balance equals ``target_kw``, in the balance's own
    units. Where even lambda = 0, the sweep alone, costs more than the target, nothing beyond
    the sweep is lifted.
    """
    def cost(lam: float) -> float:
        t, b = lifted_split(top, bot, sweep, lam)
        return enthalpy_balance(t, b, sweep, xi_hyd, t_bot_c, t_top_c, t_feed_c).total_kw

    if cost(0.0) >= target_kw:
        lam = 0.0
    else:
        lo, hi = 0.0, 1.0
        for _ in range(_BISECTION_STEPS):
            mid = 0.5 * (lo + hi)
            if cost(mid) > target_kw:
                hi = mid
            else:
                lo = mid
        lam = lo
    top_b, bot_b = lifted_split(top, bot, sweep, lam)
    return lam, top_b, bot_b
