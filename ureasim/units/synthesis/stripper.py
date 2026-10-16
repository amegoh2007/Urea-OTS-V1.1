"""322E001 — the HP CO2 stripper, as a component split with real rate laws on top.

What this models
----------------
A vertical falling-film shell-and-tube exchanger: 2600 tubes, 6 m effective, OD 31 x 3,
1519 m2, 39.4 MW. Reactor liquor enters the tube top and runs down the wall as a film; CO2
sweep gas enters the tube bottom and rises through it; 19.7 bar a MP steam condenses on the
shell. What leaves the top is the gas that goes to the carbamate condenser 322E002, and what
leaves the bottom is the urea solution that goes through LV-322501 to LP recirculation.

The stripper is the reason a CO2-stripping plant is a CO2-stripping plant. Everything the
reactor failed to convert has to come back, and this unit is what sends it back at loop
pressure instead of letting it down and paying to re-compress it.

Source
------
Ported from V1 ``backend/main.py``, `stripper_322e001` and its constant block.

Why a calibrated split and not a rate-based column
---------------------------------------------------
Because the split is MEASURED and a rate model of it would not be. The licensor's heat and
mass balance fixes what fraction of each component leaves overhead at the design point, and
that vector closes the plant balance to better than 0.1 %. A rate-based column would replace
a measurement with a set of mass-transfer coefficients nobody has for this service.

So the calibration is the anchor and everything in this module is a DEPARTURE from it:

* the thermal response comes from the live shell steam temperature;
* the pressure response comes from the per-species K-value ratio (`hp_split.hp_k_ratio`);
* the sweep response comes from the live CO2 rate;
* the composition response is a penalty on the REACTOR's feed ratios, which drives volatile
  breakthrough rather than cutting the thermal split;
* the hydraulic response is a flooding limit from the licensor tube geometry;
* the two reactions are on real second-order rate laws, anchored on the PFD extents.

Every one of those is exactly 1.0, or exactly 0.0, at the design state — several of them
structurally rather than by tuning — so the licensor's balance is reproduced bit-exact.

The four temperatures and what drives each
-------------------------------------------
    T_bot   TT-322004    steam heat + the larger of feed-load dilution and flood rise
                         + G/L strip-cool (decided 2026-10-07, handoff B-9: one ceiling)
    T_top   TT-322013    steam heat + ATTENUATED feed load + FULL G/L strip-cool
    T_feed  TT-322014    the reactor overflow, an input
    T_steam              the shell, from the live MP header pressure

The asymmetry between the top and the bottom is physical: the feed-load swing is a
liquid-side reboiler effect that the rising vapour feels only weakly, while the sweep-gas
flash endotherm is carried first by that same rising vapour.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ureasim.core.numeric import clamp
from ureasim.core.stream import MW_COMP
from ureasim.data.unit_320 import CO2_DES_KMOLH, CO2_FEED_MOLFRAC
from ureasim.data.unit_321 import CO2_DES_KGH
from ureasim.data.unit_322e001 import (
    BIURET_EA_JMOL,
    BIURET_R_GAS_J,
    BIURET_T_DES_K,
    CP_BOTTOM,
    CP_GAS,
    DH_CARBAMATE_JMOL,
    DH_H2O_VAP_JMOL,
    DH_HYDROLYSIS_JMOL,
    DH_NH3_DESORB_JMOL,
    DT_STEAM_DES_C,
    ETA_CO2_HI,
    ETA_CO2_INTERCEPT,
    ETA_CO2_LO,
    ETA_CO2_SLOPE,
    ETA_FLOOR,
    ETA_KN,
    ETA_KT,
    ETA_KW,
    ETA_T_CEILING,
    FEED_207_KMOLH,
    FEED_207_T_DES_C,
    FEED_DES_KGH,
    FEED_HC_DES,
    FEED_NC_DES,
    FEED_UREA_DES_KMOLH,
    FLOOD_ETA_FLOOR,
    FLOOD_GAP_DES_C,
    FLOOD_KGH_PER_TUBE,
    FLOOD_T_RAMP_K,
    FRAC_TOP_DES,
    FRAC_TOP_MAX,
    HYDROLYSIS_T_DES_C,
    LEVEL_SP_DES_PCT,
    MOD_CEILING,
    N_TUBES,
    P_DES_BARA,
    RHO_LIQ_IN_DES,
    SLIP_GAIN,
    STEAM_T_DES_C,
    STRIPCOOL_MAX_C,
    STRIPCOOL_RAMP_K,
    T_BOTTOM_DES_C,
    T_TOPGAS_DES_C,
    T_TOP_LOAD_K,
    V_LIQ_DES_M3,
    V_SUMP_M3,
    V_TUBES_M3,
    VDOT_DES_M3H,
    XI_BIURET_DES,
    XI_HYDROLYSIS_DES,
)
from ureasim.data.unit_322e001 import FEED_DES_KMOLH as _FEED_DES_KMOLH
from ureasim.data.unit_322r001 import REACTOR_FEED_HC_DES, REACTOR_FEED_NC_DES
from ureasim.thermo.kinetics import urea_hydrolysis_k_m3_kmol_h
from ureasim.thermo.service import ratio_shift_frac
from ureasim.units.synthesis.hp_split import hp_k_ratio


# ======================================================================================
# The hydrolysis rate group
# ======================================================================================

def hydrolysis_rate_group(t_c: float, urea_kmolh: float, h2o_kmolh: float,
                          vdot_m3h: float, v_liq_m3: float) -> float:
    """Second-order Inoue-Otsuka group ``k(T) . C_urea . C_H2O . V_liq`` [kmol/h].

    Process utility
    ---------------
    This is the part of the stripper's urea loss that CAN be predicted from first principles:
    how the extent moves with temperature, with how concentrated the melt is, and with how
    much liquid is being held. It is used as a RATIO against its own design value, so the
    units and any common factor cancel and only that movement survives.

    Why a ratio and not an absolute extent
    ---------------------------------------
    Evaluated at this stripper's own design state the law returns about 12 kmol/h over the
    whole bundle, or 17.5 kmol/h with the sump flooded as well, against a PFD extent of 88.1.
    It would need a liquid fraction of 7.3 where the physical maximum is 1. The PFD constant
    therefore is not urea hydrolysis alone — it almost certainly lumps carbamate
    decomposition, which is what the stripper is for — so predicting it from a hydrolysis rate
    law would be fitting a rate constant to a different reaction. The PFD extent stays the
    anchor and this supplies the departure.

    Concentrations are per unit of VOLUMETRIC throughput, which is the falling film's own
    basis. A zero or negative throughput returns 0.0 rather than dividing: an empty tube
    hydrolyses nothing.
    """
    if vdot_m3h <= 1e-9 or v_liq_m3 <= 0.0:
        return 0.0
    c_urea = max(urea_kmolh, 0.0) / vdot_m3h
    c_h2o = max(h2o_kmolh, 0.0) / vdot_m3h
    return urea_hydrolysis_k_m3_kmol_h(t_c) * c_urea * c_h2o * v_liq_m3


#: The rate group at the design state [kmol/h] — the denominator that makes the departure
#: exactly 1.0 there. Derived from the design constants, never entered.
HYDROLYSIS_GROUP_DES = hydrolysis_rate_group(
    HYDROLYSIS_T_DES_C, _FEED_DES_KMOLH["Urea"], _FEED_DES_KMOLH["H2O"],
    VDOT_DES_M3H, V_LIQ_DES_M3)


# ======================================================================================
# The published result
# ======================================================================================

@dataclass(frozen=True)
class StripperResult:
    """One evaluation of 322E001, as every downstream consumer and screen reads it."""

    # ---- the three molar vectors [kmol/h] --------------------------------------------
    #: Combined tube-side feed: reactor overflow plus CO2 sweep gas.
    feed_kmolh: dict
    #: The sweep gas alone, kept separately because several balances must subtract it.
    co2_feed_kmolh: dict
    #: Top gas to 322E002.
    top_kmolh: dict
    #: Bottom solution to LV-322501.
    bot_kmolh: dict

    # ---- stream totals ----------------------------------------------------------------
    top_kgh: float
    bot_kgh: float
    top_th: float
    bot_th: float
    top_kmolh_total: float
    bot_kmolh_total: float
    top_mw: float
    bot_mw: float
    #: Top gas as mole per cent, bottom solution as mass per cent — each the convention the
    #: corresponding V1 screen already used.
    top_comp_pct: dict
    bot_mass_pct: dict

    # ---- temperatures [deg C] ---------------------------------------------------------
    t_top: float
    t_bot: float
    t_feed: float
    t_steam: float

    # ---- reactions [kmol/h] -----------------------------------------------------------
    xi_hydrolysis: float
    xi_biuret: float

    # ---- efficiency diagnostics [-] ---------------------------------------------------
    #: Reported strip efficiency. A DIAGNOSTIC only since the reactions went on real rate
    #: laws — it no longer drives any extent.
    eta_t: float
    eta_t_steam: float
    g_nc: float
    g_hc: float
    g_t: float
    slip: float
    #: Stripper-feed N/C and H/C, published for the operator; not the penalty basis.
    feed_nc: float
    feed_hc: float

    # ---- thermal diagnostics [deg C] and the G/L ratio --------------------------------
    dt_load: float
    dt_bot: float
    dt_strip: float
    r_gl: float
    feed_kgh: float

    # ---- hydrodynamic flooding --------------------------------------------------------
    flood_frac: float
    flood_excess: float
    g_flood: float
    dt_flood: float
    flood_kgh_per_tube: float

    # ---- the per-species enthalpy balance [kW] ----------------------------------------
    duty_raw_kw: float
    q_carbamate_kw: float
    q_nh3_kw: float
    q_h2o_kw: float
    q_hydrolysis_kw: float
    q_sensible_kw: float
    n_co2_desorbed: float
    n_nh3_free: float


# ======================================================================================
# The unit
# ======================================================================================

def stripper_322e001(co2_feed_th: float, t_steam_c: float, p_bara: float,
                     overflow_kmolh: dict = None, feed_nc: float = None,
                     feed_hc: float = None, t_feed_c: float = None,
                     level_pct: float = LEVEL_SP_DES_PCT) -> StripperResult:
    """Evaluate the HP stripper for one set of inlet conditions.

    Parameters
    ----------
    co2_feed_th
        Live CO2 sweep gas to the tube bottom [t/h], from the 320K002 discharge node.
    t_steam_c
        Shell saturation temperature [deg C], from the live MP header pressure.
    p_bara
        Live tube-side pressure [bar a].
    overflow_kmolh
        322R001 overflow, the top liquid feed [kmol/h]. Defaults to the frozen design vector,
        which is what a caller without a reactor gets.
    feed_nc, feed_hc
        The REACTOR's feed N/C and H/C, one tick old. Not the stripper's own — see below.
    t_feed_c
        Live reactor-overflow temperature [deg C], TT-322014.
    level_pct
        Live LT-322501 sump level [%], which sets the liquid holdup the rate laws integrate
        over. A real state, not a constant.

    This function is PURE: it reads nothing and writes nothing. The sump inventory, the level
    controller and the drain valve are dynamics and live in :mod:`.stripper_sump`.
    """
    # ==================================================================================
    # 1. The combined tube-side feed
    # ==================================================================================
    # The reactor overflow is a RECYCLE TEAR — it is last tick's value, because the reactor
    # is downstream of the carbamate condenser which is downstream of this unit. At design it
    # equals the frozen design vector, so the tear costs nothing at the pin.
    if overflow_kmolh is None:
        overflow_kmolh = FEED_207_KMOLH
    if t_feed_c is None:
        t_feed_c = FEED_207_T_DES_C

    # The sweep gas is the SAME CO2 unit 320 delivers, scaled off its design rate so its
    # composition — including the inerts that eventually leave through the 322E003 vent —
    # travels with it rather than being re-entered here.
    co2_scale = co2_feed_th / (CO2_DES_KGH / 1000.0)                      # 1.0 at design
    co2_kmolh = {k: CO2_FEED_MOLFRAC.get(k, 0.0) * CO2_DES_KMOLH * co2_scale
                 for k in MW_COMP}
    feed = {k: overflow_kmolh.get(k, 0.0) + co2_kmolh.get(k, 0.0) for k in MW_COMP}

    # ==================================================================================
    # 2. Stripping efficiency: steam heat, penalised by the REACTOR's feed ratios
    # ==================================================================================
    # Excess NH3 (high N/C) and dilution (high H/C) both make a solution harder to strip
    # thermally: the ammonia has to be desorbed before anything else can happen, and the water
    # carries heat away without releasing CO2.
    #
    # The penalty anchors on the REACTOR-feed ratios and not this unit's own, for a reason
    # that is a modelling constraint rather than a preference. The reduced reactor PINS its
    # overflow N/C through an atom-conserving ripple, so the stripper's own feed ratio barely
    # moves and would carry no disturbance. The reactor-feed ratios are the ones that actually
    # drop conversion and load this stripper, and they arrive one tick old for the same tear
    # reason as the overflow vector.
    d_t_steam = t_steam_c - STEAM_T_DES_C
    eta_t_steam = clamp(t_steam_c / STEAM_T_DES_C, 0.0, ETA_T_CEILING)     # 1.0 at design

    # --- the liquid-side energy balance ----------------------------------------------
    # The reboiler delivers a roughly fixed duty. Spread over the LIVE feed mass, the specific
    # heating available to the descending liquid is Q/(m.cp). Open the reactor overflow valve
    # at constant steam and the heating per kilogram falls, so the bottom leaves COLDER:
    #
    #     raw_load = dT_steam,des . (m_des/m_live - 1)      = 0 at design, < 0 on a feed spike
    feed_kgh = sum(feed[k] * MW_COMP[k] for k in MW_COMP)
    raw_load = DT_STEAM_DES_C * (FEED_DES_KGH / max(feed_kgh, 1e-6) - 1.0)

    # THERMAL CEILING. The bottom liquid can never out-heat the condensing shell, so the raw
    # 1/m_feed pole must not diverge as the feed goes to zero. The head-room below steam
    # saturation is the cap, and the low-feed (heating) branch saturates exponentially onto
    # it while staying slope-1 near design.
    #
    # The HIGH-feed branch is deliberately left as the RAW negative load, because dT_load is
    # also the efficiency driver: on a flood the split must keep closing, which is what holds
    # the unstripped volatiles in the BOTTOMS where they leave through LV-322501 rather than
    # overhead.
    cap = max(STEAM_T_DES_C - T_BOTTOM_DES_C + 0.3 * d_t_steam, 1e-6)
    dt_load = cap * (1.0 - math.exp(-raw_load / cap)) if raw_load > 0.0 else raw_load
    g_t = clamp(1.0 + ETA_KT * dt_load / T_BOTTOM_DES_C, ETA_FLOOR, 1.05)

    # --- the bottom temperature has its OWN driver ------------------------------------
    # dT_bot is separate from dT_load, and the separation fixes a real defect. Feeding the raw
    # linear load straight into the bottom temperature drove it DOWN without bound on a feed
    # spike — an infinite feed gave a bottom temperature of about -0.4 C, absurd and the wrong
    # sign as well.
    #
    # The physics is the opposite. A flooded stripper is STEAM-LIMITED: carbamate
    # decomposition stalls, its endotherm fades, and the already-hot reactor liquor falls
    # through the tubes untouched. So the bottom must RISE and asymptote UP to the reactor
    # overflow temperature, never crash. The low-feed branch keeps dT_load, which heats toward
    # steam saturation. g_t above is untouched and still rides the raw load, so a flood gives
    # HOT but UNSTRIPPED bottoms — classic NH3 slip to the LP section.
    flood_gap = max(FLOOD_GAP_DES_C, 1e-6)
    dt_bot = (dt_load if raw_load > 0.0
              else flood_gap * (1.0 - math.exp(raw_load / flood_gap)))

    # --- the hydrodynamic flooding limit ----------------------------------------------
    # Everything above is thermal: can the shell steam keep up with the liquid? This asks the
    # independent question of whether the tube can physically carry the film at all.
    #
    # flood_excess is EXACTLY 0.0 at design because max() returns the literal 0.0 for a
    # negative argument, and the design fraction is 0.7448. Every term below is therefore an
    # exact identity at the seed — 1 - exp(0) is 0.0 — so the pin cannot move.
    flood_frac = feed_kgh / N_TUBES / FLOOD_KGH_PER_TUBE
    flood_excess = max(flood_frac - 1.0, 0.0)
    dt_flood = flood_gap * (1.0 - math.exp(-FLOOD_T_RAMP_K * flood_excess))
    # Both rises describe one end state, unstripped liquor falling through untouched, so they
    # share the 11 C gap: the bottoms tend to the 183 C fed (DECIDED 2026-10-07, handoff B-9;
    # V1 adds them and tends to 194 C). Both are exactly 0.0 at design and never negative.
    dt_bot = max(dt_bot, dt_flood)

    # --- the CO2 sweep endotherm ------------------------------------------------------
    # The sweep is held by the compressor while the liquid feed varies, so a feed collapse at
    # constant CO2 spikes the gas/liquid ratio. The excess gas forces carbamate decomposition
    # and NH3/CO2 flash, which is strongly endothermic and OVERPOWERS the steam-heating spike
    # of the low-feed branch: the bottom goes COLDER, not toward steam saturation.
    #
    # Only the feed-lean / CO2-rich side cools. The feed-spike side is left untouched because
    # its own branch already describes it. Saturating, so no pole at zero feed.
    r_gl = co2_scale * FEED_DES_KGH / max(feed_kgh, 1e-6) - 1.0
    dt_strip = -STRIPCOOL_MAX_C * (1.0 - math.exp(-STRIPCOOL_RAMP_K * max(r_gl, 0.0)))

    # --- the two composition penalties ------------------------------------------------
    nc_react = REACTOR_FEED_NC_DES if feed_nc is None else feed_nc
    hc_react = REACTOR_FEED_HC_DES if feed_hc is None else feed_hc
    g_nc = clamp(1.0 - ETA_KN * (nc_react - REACTOR_FEED_NC_DES), ETA_FLOOR, 1.05)
    g_hc = clamp(1.0 - ETA_KW * (hc_react - REACTOR_FEED_HC_DES), ETA_FLOOR, 1.05)
    eta_t = clamp(eta_t_steam * g_nc * g_hc * g_t, 0.0, ETA_T_CEILING)

    # Published for the operator, not used as a penalty basis — see the note in section 2.
    nc_strip = (feed["NH3"] / feed["CO2"]) if feed["CO2"] else FEED_NC_DES
    hc_strip = (feed["H2O"] / feed["CO2"]) if feed["CO2"] else FEED_HC_DES

    # ==================================================================================
    # 3. The two product temperatures, then the reactions
    # ==================================================================================
    # TT-322004. Steam heat plus the larger of the load swing and the flood rise (B-9) plus
    # the sweep endotherm, and never above the condensing shell.
    t_bot_c = min(T_BOTTOM_DES_C + 0.7 * d_t_steam + dt_bot + dt_strip, t_steam_c)
    t_bot_k = t_bot_c + 273.15

    # TT-322013. The load swing reaches the overhead ATTENUATED because it is a liquid-side
    # reboiler effect; the sweep endotherm reaches it at FULL weight because the rising vapour
    # is what carries that flash's latent load.
    t_top_c = min(T_TOPGAS_DES_C + 0.6 * d_t_steam + T_TOP_LOAD_K * dt_bot + dt_strip,
                  t_steam_c)

    # --- urea hydrolysis, anchored extent times the rate-law departure -----------------
    # The holdup tracks the LIVE sump level, so a level or throughput excursion moves the
    # extent. The extent can never exceed either reagent that is actually present.
    vdot_m3h = max(feed_kgh / RHO_LIQ_IN_DES, 1e-9)
    v_liq_m3 = V_TUBES_M3 + V_SUMP_M3 * clamp(level_pct / 100.0, 0.0, 1.0)
    group = hydrolysis_rate_group(t_bot_c, feed["Urea"], feed["H2O"], vdot_m3h, v_liq_m3)
    xi_hyd_raw = XI_HYDROLYSIS_DES * (group / HYDROLYSIS_GROUP_DES
                                      if HYDROLYSIS_GROUP_DES > 0.0 else 1.0)
    xi_hyd = max(min(xi_hyd_raw, feed["Urea"], feed["H2O"]), 0.0)
    urea_after_hyd = max(feed["Urea"] - xi_hyd, 0.0)

    # --- biuret formation, 2 Urea -> Biuret + NH3 --------------------------------------
    # SECOND order in urea, because that is the stoichiometry, and integrated over the same
    # live liquid volume. A deep turndown — more urea-rich melt sitting longer — raises it,
    # which is exactly what happens on the plant and is why biuret is a turndown problem.
    # The extent can never consume more than the urea left after hydrolysis, at 2 per biuret.
    xi_biu_raw = (XI_BIURET_DES
                  * math.exp((BIURET_EA_JMOL / BIURET_R_GAS_J)
                             * (1.0 / BIURET_T_DES_K - 1.0 / t_bot_k))
                  * (feed["Urea"] / FEED_UREA_DES_KMOLH) ** 2
                  * (VDOT_DES_M3H / vdot_m3h) * (v_liq_m3 / V_LIQ_DES_M3))
    xi_biu = max(min(xi_biu_raw, 0.5 * urea_after_hyd), 0.0)

    # --- what is available to split, after the reactions --------------------------------
    avail = dict(feed)
    avail["Urea"] -= (xi_hyd + 2.0 * xi_biu)
    avail["Biuret"] += xi_biu
    avail["NH3"] += (2.0 * xi_hyd + xi_biu)
    avail["CO2"] += xi_hyd
    avail["H2O"] -= xi_hyd

    # ==================================================================================
    # 3b. The hydraulic efficiency knockdown, DERIVED from the bottom-temperature rise
    # ==================================================================================
    # The bottom running hotter and the stripping being lost are THE SAME EVENT measured two
    # ways: the bottom is hot precisely because the carbamate dissociation did not happen, so
    # the heat that should have been absorbed by dissociation shows up as sensible heat in the
    # liquid instead. Nothing new is fitted —
    #
    #     Q_deficit = m_feed . cp . dT_flood                     heat not absorbed
    #     g_flood   = 1 - Q_deficit / (n_carbamate . dH_carb)    fraction of stripping lost
    #
    # The carbamate available excludes the CO2 SWEEP, which arrives already as gas and needs
    # no dissociation heat — so there is no circular dependence on the split this drives. The
    # balance is charged against the carbamate endotherm alone rather than the full endotherm
    # sum: that is both the simpler and the conservative choice (a smaller denominator gives a
    # LARGER knockdown), and it is what the source describes, since it is the falling film
    # that facilitates the dissociation.
    #
    # At design dT_flood is exactly 0.0, so g_flood is exactly 1.0.
    n_carb_avail = max(avail["CO2"] - co2_kmolh["CO2"], 1e-9)
    q_carb_avail = n_carb_avail * DH_CARBAMATE_JMOL                   # kJ/h
    q_flood_deficit = feed_kgh * CP_BOTTOM * dt_flood                 # kJ/h, 0.0 at design
    g_flood = clamp(1.0 - q_flood_deficit / q_carb_avail, FLOOD_ETA_FLOOR, 1.0)

    # ==================================================================================
    # 4. The split
    # ==================================================================================
    # Thermal steam heat x sweep-gas dilution, then the feed-load choke and the hydraulic
    # knockdown. All four are exactly 1.0 at design.
    eta_co2 = clamp(ETA_CO2_INTERCEPT + ETA_CO2_SLOPE * co2_scale, ETA_CO2_LO, ETA_CO2_HI)

    # The pressure response is the per-species K-value ratio at the live tube-side pressure.
    # ONLY the pressure moves in this ratio: the thermal response of the split is already
    # carried, and carried better, by the steam terms above. The stripper is a steam-driven
    # contactor, not an adiabatic flash, and its bottoms temperature is an OUTPUT of that
    # duty — putting the live temperature into the ratio as well would count the same steam
    # heat twice. So the reference temperature IS the live temperature, the T terms of the two
    # K-values cancel identically, and the pressure derivative is left alone.
    split_ratio = hp_k_ratio(avail, FEED_207_T_DES_C, p_bara,
                             FEED_207_T_DES_C, P_DES_BARA)

    # min(g_t, 1.0) keeps the feed-lean branch, which is already rewarded through eta_t, and
    # keeps the design point bit-exact. The feed-load choke CUTS the split: steam-limited
    # stripping leaves the volatiles in the BOTTOMS and slips them to LP through LV-322501; it
    # does not lift them overhead.
    #
    # g_flood multiplies the SPLIT only. Flooding does not suppress hydrolysis — a flooded
    # tube's liquid residence time INCREASES, so hydrolysis and biuret go UP, and that rise is
    # already carried explicitly through the live holdup and the raised bottom temperature in
    # the Arrhenius term. Folding g_flood into the extents would cut them, i.e. the wrong sign.
    mod = clamp(eta_t_steam * eta_co2, 0.0, MOD_CEILING) * min(g_t, 1.0) * g_flood
    slip = max(1.0 - g_nc, 0.0) + max(1.0 - g_hc, 0.0)

    top = {}
    bot = {}
    for k in MW_COMP:
        # The pressure ratio is applied through `ratio_shift_frac`, which maps [0,1] onto
        # [0,1] for any ratio. A bare multiply cannot: it would ask the column to strip more
        # nitrogen than it was fed and let a clamp silently truncate the excess.
        f = clamp(ratio_shift_frac(FRAC_TOP_DES.get(k, 0.0) * mod, split_ratio.get(k, 1.0)),
                  0.0, FRAC_TOP_MAX)
        if k in ("NH3", "CO2"):
            # Volatile breakthrough. A composition choke does not cut the thermal split — it
            # pushes NH3 and CO2 overhead as slip, raising the vapour load back to the
            # carbamate condenser. slip is exactly 0.0 at design.
            f = clamp(f + SLIP_GAIN * slip * (1.0 - f), 0.0, FRAC_TOP_MAX)
        top[k] = avail[k] * f
        bot[k] = avail[k] * (1.0 - f)

    # ==================================================================================
    # 5. Stream totals and intensive properties
    # ==================================================================================
    top_kgh_by_species = {k: top[k] * MW_COMP[k] for k in MW_COMP}
    bot_kgh_by_species = {k: bot[k] * MW_COMP[k] for k in MW_COMP}
    top_m = sum(top_kgh_by_species.values())
    top_n = sum(top.values())
    bot_m = sum(bot_kgh_by_species.values())
    bot_n = sum(bot.values())

    # ==================================================================================
    # 6. The per-species enthalpy balance — what the MP header actually has to pay for
    # ==================================================================================
    # Five terms, every constant sourced. Unlike a feed-proportional stand-in this responds to
    # COMPOSITION: a feed richer in carbamate costs more steam at the same tonnage.
    #
    #   q_carb  carbamate dissociation, the dominant sink, about 58 % of the design duty
    #   q_nh3   desorption of the NH3 that was not carbamate-bound (supercritical: no latent)
    #   q_h2o   the small water fraction that vaporises overhead, about 7 %
    #   q_hyd   urea hydrolysis, liquid step only — NEGATIVE, it gives a little heat back
    #   q_sens  sensible heat of the two products relative to the feed temperature
    #
    # Each term subtracts the sweep gas, which arrives already hot and already gaseous and so
    # is not something this unit has to pay to liberate. The NH3 pairing is 2:1 because that
    # is the carbamate stoichiometry.
    n_co2_desorb = max(top["CO2"] - co2_kmolh["CO2"], 0.0)
    n_nh3_free = max(top["NH3"] - co2_kmolh["NH3"] - 2.0 * n_co2_desorb, 0.0)
    q_carb_kw = n_co2_desorb * DH_CARBAMATE_JMOL / 3600.0
    q_nh3_kw = n_nh3_free * DH_NH3_DESORB_JMOL / 3600.0
    q_h2o_kw = max(top["H2O"] - co2_kmolh["H2O"], 0.0) * DH_H2O_VAP_JMOL / 3600.0
    q_hyd_kw = xi_hyd * DH_HYDROLYSIS_JMOL / 3600.0
    q_sens_kw = (bot_m * CP_BOTTOM * (t_bot_c - t_feed_c)
                 + top_m * CP_GAS * (t_top_c - t_feed_c)) / 3600.0
    duty_raw_kw = q_carb_kw + q_nh3_kw + q_h2o_kw + q_hyd_kw + q_sens_kw

    return StripperResult(
        feed_kmolh=feed, co2_feed_kmolh=co2_kmolh, top_kmolh=top, bot_kmolh=bot,
        top_kgh=top_m, bot_kgh=bot_m, top_th=top_m / 1000.0, bot_th=bot_m / 1000.0,
        top_kmolh_total=top_n, bot_kmolh_total=bot_n,
        top_mw=(top_m / top_n if top_n else 0.0),
        bot_mw=(bot_m / bot_n if bot_n else 0.0),
        top_comp_pct={k: (top[k] / top_n * 100.0 if top_n else 0.0) for k in MW_COMP},
        bot_mass_pct={k: (bot_kgh_by_species[k] / bot_m * 100.0 if bot_m else 0.0)
                      for k in MW_COMP},
        t_top=t_top_c, t_bot=t_bot_c, t_feed=t_feed_c, t_steam=t_steam_c,
        xi_hydrolysis=xi_hyd, xi_biuret=xi_biu,
        eta_t=eta_t, eta_t_steam=eta_t_steam, g_nc=g_nc, g_hc=g_hc, g_t=g_t, slip=slip,
        feed_nc=nc_strip, feed_hc=hc_strip,
        dt_load=dt_load, dt_bot=dt_bot, dt_strip=dt_strip, r_gl=r_gl, feed_kgh=feed_kgh,
        flood_frac=flood_frac, flood_excess=flood_excess, g_flood=g_flood,
        dt_flood=dt_flood, flood_kgh_per_tube=feed_kgh / N_TUBES,
        duty_raw_kw=duty_raw_kw, q_carbamate_kw=q_carb_kw, q_nh3_kw=q_nh3_kw,
        q_h2o_kw=q_h2o_kw, q_hydrolysis_kw=q_hyd_kw, q_sensible_kw=q_sens_kw,
        n_co2_desorbed=n_co2_desorb, n_nh3_free=n_nh3_free,
    )


# ======================================================================================
# The design-point self-call, and the anchors that fall out of it
# ======================================================================================
# Evaluating the unit at its own design condition is how the downstream anchors are obtained,
# rather than entering them as literals that could drift from the model that produces them.

#: The whole design evaluation, kept so a test can assert against every field of it.
_DESIGN = stripper_322e001(CO2_DES_KGH / 1000.0, STEAM_T_DES_C, P_DES_BARA)

#: Design top-gas vector [kmol/h] — 322E002's design feed.
TOP_DES_KMOLH = _DESIGN.top_kmolh

#: Design total overhead [kmol/h], 5789.4.
TOP_DES_KMOLH_TOTAL = _DESIGN.top_kmolh_total

#: Design top-gas temperature [deg C], 187.0 — TT-322013, the carbamate condenser's hot feed.
TOP_DES_T_C = _DESIGN.t_top

#: Design overhead NH3 [kmol/h], 3571.6 — the condensable the carbamate condenser is sized on.
TOP_DES_NH3_KMOLH = _DESIGN.top_kmolh["NH3"]

#: Design FREE CO2 overhead [kmol/h], 98.6 — the CO2 not paired into carbamate at 2 NH3 per
#: CO2. This is the PRESSURE-BUILDING acid: carbamate condenses and takes its partial pressure
#: with it, but unpaired CO2 stays in the vapour and is what actually pushes PT-329201 up.
TOP_DES_CO2_FREE_KMOLH = max(_DESIGN.top_kmolh["CO2"] - 0.5 * _DESIGN.top_kmolh["NH3"], 0.0)

#: Design value of the per-species enthalpy balance [kW], about 37 831.
#: This is the DENOMINATOR that makes the live duty ratio exactly 1.0 at design. It is 96 % of
#: the licensor's 39 400 kW, and that offset CANCELS in the ratio and never reaches the steam
#: header — the design duty the plant is scheduled on stays the PFD value, not a computed one.
DUTY_RAW_DES_KW = _DESIGN.duty_raw_kw


__all__ = [
    "hydrolysis_rate_group",
    "HYDROLYSIS_GROUP_DES",
    "StripperResult",
    "stripper_322e001",
    "TOP_DES_KMOLH",
    "TOP_DES_KMOLH_TOTAL",
    "TOP_DES_T_C",
    "TOP_DES_NH3_KMOLH",
    "TOP_DES_CO2_FREE_KMOLH",
    "DUTY_RAW_DES_KW",
]
