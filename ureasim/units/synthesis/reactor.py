"""322R001 — the HP urea reactor: component balance, vapour disengagement, analysers.

What this models
----------------
The vessel where the product is made. Two-phase carbamate arrives from 322E002 at the bottom
nozzle, spends three quarters of an hour rising through eleven sieve trays, and leaves as two
streams: liquid melt over an internal funnel to the 322E001 stripper, and uncondensed gas off
the top to the 322E003 scrubber. Nothing is heated and nothing is cooled.

What this module owns, and what is next door
---------------------------------------------
This module is the STREAMS: the tear-corrected feed, the two reactions applied to it as exact
stoichiometry, the vapour/liquid disengagement at the top, the two conservative composition
shifts that let the analysers respond, and the telemetry the screens read.

    `reactor_column`       the axial march — what the reactions actually do, node by node
    `reactor_calibration`  the two back-solves that tie the march to the plant
    `reactor_hydraulics`   the level, the funnel, HV-322605, the node energy RHS
    `thermo.kinetics`      the rate laws and the reaction enthalpies

Conservation, and why it is worth a paragraph
-----------------------------------------------
Every stream operation below is written so that atoms and mass are conserved by construction
rather than by correction. The two reactions are applied through one stoichiometric vector
each; the two composition shifts move species BETWEEN the overflow and the off-gas and never
create or destroy any; `closure_resid` is computed and published as a diagnostic and is never
injected back into a stream. An earlier version of this unit multiplied the off-gas by a gain
to model conversion slip, which made mass, and the loop it fed drifted.

Design anchoring
----------------
At the design state the live extents equal the pinned ones and the feed equals the design
feed, so the two product vectors come out as the published PFD ones to the last bit. Both
composition shifts are written on DEVIATIONS — from the design feed N/C and from the design
per-pass conversion — so both are identically zero there, by the arithmetic.

Source
------
Ported from V1 ``backend/main.py`` `react_322r001` and `_react_delta`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ureasim.core.stream import MW_COMP
from ureasim.data.unit_321 import CO2_DES_KGH
from ureasim.data.unit_320 import SYN_P_DES_BARA
from ureasim.data.unit_322r001 import (
    AREA_M2,
    BETA_DAMKOHLER,
    DT_COL_DES_C,
    HIC605_DES_PCT,
    LEVEL_NLL_PCT,
    LIQ_H_M,
    OFFGAS_DES_KMOLH,
    OFFGAS_DEFICIT_GAIN,
    OFFGAS_P_DES_BARA,
    OFFGAS_T_DES_C,
    OVERFLOW_DES_KGH,
    OVERFLOW_DES_KMOLH,
    OVERFLOW_T_DES_C,
    NC_OVERFLOW_GAIN,
    REACTOR_FEED_HC_DES,
    REACTOR_FEED_NC_DES,
    THETA_OFFGAS,
    VDOT_DES_M3H,
    X_DES,
    X_INF,
    XI_BIURET_DES,
    XI_UREA_DES,
    ZETA_NODES,
)
from ureasim.thermo.kinetics import CARBAMATE_DH_JMOL, DEHYDRATION_DH_JMOL
from ureasim.thermo.service import anchored_split
from ureasim.units.synthesis.carbamate_condenser import DESIGN as _HPCC_DES
from ureasim.units.synthesis.hp_split import hp_k_ratio
from ureasim.units.synthesis.reactor_calibration import (
    calibrate_kinetics,
    thermal_kinetic_fixed_point,
)
from ureasim.units.synthesis.reactor_column import (
    ColumnKinetics,
    biuret_extent,
    carbamate_node_extents,
    node_heat_kjh,
    node_liquid_volumes,
    node_profile_ss,
    urea_extent_pfr,
)
from ureasim.units.synthesis.reactor_hydraulics import melt_density

#: Design temperature of the 322E002 two-phase product entering at the bottom [deg C]. It is
#: the reactor's inlet temperature and therefore node 0 of the axial profile.
FEED_T_DES_C = _HPCC_DES.t_prod


@dataclass(frozen=True)
class ColumnAnchor:
    """The live column state the kinetics were last calibrated at.

    V1 captures this at boot, after settling the plant, and `react_322r001` defaults to it so
    that calling the unit with the design feed and no extra arguments reproduces the design
    extent exactly. It is carried as an argument here for the same reason the condenser's
    design melt N/C is: it is a property of a settled PLANT, which is the engine's to know,
    not a property of this vessel.

    Three of its four fields are computable at module scope and are published below as
    `ANCHOR_SEED`; only `m_feed_kgh` needs a settled plant. Passing nothing takes V1's own
    pre-pin path, which is the design profile at normal level and the design throughput.
    """

    #: Node temperatures the calibration was solved at [deg C].
    t_nodes_c: list
    #: Level as a fraction of the liquid span [-].
    level_frac: float
    #: Volumetric throughput [m3/h].
    vdot_m3h: float
    #: Feed mass [kg/h] the throughput above corresponds to. A caller that gives no live
    #: throughput gets the anchor's scaled by its feed mass against this, so turning the
    #: plant down turns the residence time down with it instead of diluting the column.
    m_feed_kgh: float


@dataclass(frozen=True)
class ReactorResult:
    """One evaluation of 322R001, as the stripper, the scrubber and the screens read it."""

    # ---- the streams [kmol/h] -------------------------------------------------------------
    #: Liquid melt over the funnel to 322E001 — PFD stream 207 at design.
    overflow_kmolh: dict
    #: Uncondensed gas off the top to 322E003.
    offgas_kmolh: dict
    #: The 322E002 two-phase product as received.
    feed_kmolh: dict
    #: The same feed with the pinned recycle tear removed — what the balance is written on.
    feed_corrected_kmolh: dict

    # ---- the reactions [kmol/h] ------------------------------------------------------------
    #: Urea-formation extent actually realised, after the feasibility clamp.
    xi_urea: float
    #: Biuret-formation extent, same basis.
    xi_biuret: float
    #: Carbamate-formation extent, from the STREAM balance rather than a rate law.
    xi_carbamate: float
    #: Per-node urea extents, for the column energy balance.
    xi_nodes: list
    #: Net heat released in each node [kJ/h].
    q_nodes_kjh: list

    # ---- conversion and the feed ratios ------------------------------------------------------
    #: Absolute per-pass CO2 conversion [-], xi_urea / CO2 fed. 0.543 at design.
    x_conv: float
    #: Fractional conversion shortfall below the design reference [-], floored at zero.
    delta_x: float
    #: Reactor-feed N/C and H/C the conversion was driven off [-].
    l_feed: float
    w_feed: float

    # ---- operating point ---------------------------------------------------------------------
    #: TT-322014 overflow and TT-322009 off-gas temperatures [deg C].
    t_overflow_c: float
    t_offgas_c: float
    #: Loop pressure as the reactor reports it and the off-gas line pressure [bar a].
    p_bara: float
    p_offgas_bara: float
    #: HV-322605 opening as a fraction, and its design value.
    phi: float
    phi_des: float
    #: CO2 throughput ratio against design [-].
    co2_scale: float

    # ---- telemetry ----------------------------------------------------------------------------
    #: Dalton partial pressures in the off-gas line [bar a].
    p_nh3_offgas_bara: float
    p_co2_offgas_bara: float
    #: Mass the pinned tear removed from the feed [kg/h].
    tear_mass_kgh: float
    #: Total-mole closure residual [kmol/h]. A diagnostic, never injected.
    closure_resid: float = field(default=0.0)


def apply_reaction_extents(feed_corrected_kmolh: dict, xi_urea: float,
                           xi_biuret: float) -> dict:
    """Apply both reactions to a feed vector as exact stoichiometry [kmol/h].

    Process utility
    ---------------
    Turns two extents into the composition that actually leaves the vessel. Writing it as one
    stoichiometric vector per reaction is what makes the atom balance exact rather than
    approximately right: nitrogen and carbon cannot drift, because no line here touches them
    except through a reaction that conserves them.

    Equations
    ---------
        Urea    CO2 + 2 NH3 -> Urea + H2O        dN = dC = 0,  d(total moles) = -1
        Biuret  2 Urea -> Biuret + NH3           dN = dC = 0,  d(total moles) =  0

    The urea step consumes two moles of gas-forming reagent and makes one of melt plus one of
    water, which is the mole contraction the loop pressure responds to. Biuret is mole-neutral
    and matters only to product quality.
    """
    out = {k: feed_corrected_kmolh.get(k, 0.0) for k in MW_COMP}
    out["CO2"] -= xi_urea
    out["NH3"] -= 2.0 * xi_urea
    out["Urea"] += xi_urea
    out["H2O"] += xi_urea
    out["Urea"] -= 2.0 * xi_biuret
    out["Biuret"] += xi_biuret
    out["NH3"] += xi_biuret
    return out


def reactor_322r001(feed_kmolh: dict, gas_co2_in_kmolh: float, co2_feed_th: float,
                    hic605_pct: float, p_loop_bara: float, kinetics: ColumnKinetics,
                    l_drive: float = None, w_drive: float = None,
                    t_nodes_c=None, level_frac: float = None, vdot_m3h: float = None,
                    anchor: ColumnAnchor = None, tear_des_kmolh: dict = None,
                    l_feed_des: float = None, x_des_live: float = None) -> ReactorResult:
    """322R001 HP urea reactor — rigorous component mole balance with exact atom conservation.

    Process utility
    ---------------
    The plant's whole purpose in one call. The stripper's feed, the scrubber's feed, the
    per-pass conversion an operator is judged on, and the biuret that decides whether the
    product ships all come out of here.

    Parameters that are TEARS
    -------------------------
    The synthesis loop is cyclic — 322F001 to 322E002 to 322R001 to 322E003 and back — so it
    cannot be evaluated in an order without cutting it. Three of the arguments are the cut
    ends and all three carry the PREVIOUS tick's value:

        ``t_nodes_c``    the axial profile, which the reactions set and which sets the
                         reactions. One of the two has to be torn and this is it.
        ``level_frac``   the live level, which sets the wetted volume and hence the residence
                         time, and which the discharge integrated over the last tick.
        ``vdot_m3h``     the live volumetric throughput, from the overflow the last pass made.

    Passing none of them takes the anchor, and passing no anchor takes the design state, which
    is what makes the design self-call below reproduce the published point.

    Parameters that are BOOT PINS
    -----------------------------
    ``anchor``, ``tear_des_kmolh``, ``l_feed_des`` and ``x_des_live`` are captured from a
    settled plant, which is the engine's business and not this vessel's. Each one defaults to
    V1's own pre-pin fallback, and each is the reference of a term that is zero at design, so
    the defaults change the design point by nothing.

    What the tear is for
    --------------------
    The reduced flowsheet pins the recycle, so the feed this unit receives contains the
    recycle's contribution twice over unless it is removed once. ``tear_des_kmolh`` is that
    explicit correction, scaled with load. It is subtracted BEFORE the reactions, so every
    subsequent balance is written on a feed that closes.

    Why the two composition shifts exist
    ------------------------------------
    Both let an analyser respond to something it must respond to, without creating mass.

    * **AT-322701.** With a pinned recycle the reactor-to-stripper N/C is atom-locked: the
      operator can move the feed ratio and the analyser will not move. The shift moves ammonia
      between the overflow and the off-gas in proportion to the feed-N/C deviation, so total
      nitrogen and total carbon are both held and only the PARTITION moves.
    * **Conversion slip.** When the reactor converts less than design, the ammonia and CO2 it
      failed to convert leave as gas rather than as melt. One-sided, floored at zero, so a
      reactor running at or above design shifts nothing.

    Both are bounded by what the donating stream holds, so neither can drive a component
    negative.

    Why the vapour disengagement is RE-FLASHED
    -------------------------------------------
    The licensor's split vector is calibrated at one point, and frozen it has a derivative of
    exactly zero — the reactor could run 20 C hot or 10 bar low and not one mole would move
    between the melt and the off-gas, which is the wrong answer for a vessel whose whole job
    is holding NH3 and CO2 in the liquid. `anchored_split` re-solves it at the live pressure
    against the same design pair it was calibrated at, so the ratio is exactly 1.0 there.

    Source: V1 `main.py` react_322r001.
    """
    s = co2_feed_th / (CO2_DES_KGH / 1000.0)             # CO2 throughput ratio, 1.0 at design
    phi = hic605_pct / 100.0
    phi_des = HIC605_DES_PCT / 100.0

    # ---- the ratios the conversion is driven off --------------------------------------
    # The raw feed ratios are the unit-test path. The engine supplies blended, lagged drivers
    # instead, because the endogenous feed N/C is dominated by an atom-conserving ripple —
    # convert more, consume two NH3 per CO2, feed N/C falls — which is a strong negative loop
    # that cannot be amplified into the response an operator actually sees.
    feed_co2 = feed_kmolh.get("CO2", 0.0)
    l_feed = (feed_kmolh.get("NH3", 0.0) / feed_co2) if feed_co2 > 0.0 else REACTOR_FEED_NC_DES
    w_feed = (feed_kmolh.get("H2O", 0.0) / feed_co2) if feed_co2 > 0.0 else REACTOR_FEED_HC_DES
    if l_drive is not None:
        l_feed = l_drive
    if w_drive is not None:
        w_feed = w_drive

    # ---- resolve the column state the march runs on -----------------------------------
    nodes = list(t_nodes_c) if t_nodes_c is not None else list(
        anchor.t_nodes_c if anchor else NODE_PROFILE_DES)
    level = level_frac if level_frac is not None else (
        anchor.level_frac if anchor else LEVEL_NLL_PCT / 100.0)
    if vdot_m3h is not None and vdot_m3h > 1e-9:
        vdot = vdot_m3h
    elif anchor:
        # No live throughput given: scale the anchor's with the FEED MASS rather than freezing
        # it. A caller that scales the feed down is turning the plant DOWN, not diluting it,
        # and a frozen throughput turns a turndown into a concentration rise — which made
        # conversion climb as load fell, the wrong sign. At design the ratio is exactly 1.0.
        m_feed = sum(feed_kmolh.get(k, 0.0) * MW_COMP[k] for k in MW_COMP)
        vdot = anchor.vdot_m3h * (m_feed / max(anchor.m_feed_kgh or m_feed, 1e-9))
    else:
        vdot = VDOT_DES_M3H

    # ---- the reactions ------------------------------------------------------------------
    xi_urea, xi_nodes = urea_extent_pfr(feed_kmolh, nodes, ZETA_NODES, AREA_M2, LIQ_H_M,
                                        level, vdot, kinetics)
    # Per-pass conversion is read off the UNCLAMPED extent against the raw feed carbon: it is
    # what the column achieved, before the tear-corrected balance bounds what can be realised.
    x_conv = xi_urea / feed_co2 if feed_co2 > 0.0 else 0.0

    s_tear = s if tear_des_kmolh is not None else 0.0
    corrected = {k: feed_kmolh.get(k, 0.0)
                 - (tear_des_kmolh.get(k, 0.0) if tear_des_kmolh else 0.0) * s_tear
                 for k in MW_COMP}

    # Biuret forms from the urea ACTUALLY in the column — the feed urea plus what this pass
    # just made. Scaling a design constant by load instead leaves the concentration at s/s and
    # the extent comes out load-invariant, which is a frozen number wearing an Arrhenius coat.
    urea_in_column = max(corrected.get("Urea", 0.0), 0.0) + max(xi_urea, 0.0)
    xi_biuret = biuret_extent(nodes, ZETA_NODES, AREA_M2, LIQ_H_M, level, vdot,
                              urea_in_column, kinetics)

    # Feasibility clamps: non-binding at and near design, so the pin is bit-exact; they bind
    # under reagent starvation, where an unbounded extent would take a component negative.
    xi_urea = max(min(xi_urea, corrected.get("CO2", 0.0), 0.5 * corrected.get("NH3", 0.0)), 0.0)
    xi_biuret = max(min(xi_biuret, 0.5 * (corrected.get("Urea", 0.0) + xi_urea)), 0.0)
    out_total = apply_reaction_extents(corrected, xi_urea, xi_biuret)

    # ---- vapour disengagement at the reactor top -----------------------------------------
    split_ratio = hp_k_ratio(out_total, OVERFLOW_T_DES_C, p_loop_bara,
                             OVERFLOW_T_DES_C, SYN_P_DES_BARA)
    theta = anchored_split(THETA_OFFGAS, out_total, split_ratio)
    overflow = {k: out_total[k] * (1.0 - theta[k]) for k in MW_COMP}
    offgas = {k: out_total[k] * theta[k] for k in MW_COMP}

    # ---- AT-322701 excess-ammonia partition ------------------------------------------------
    l_ref = l_feed_des if l_feed_des is not None else REACTOR_FEED_NC_DES
    nh3_shift = NC_OVERFLOW_GAIN * (l_feed / l_ref - 1.0) * OVERFLOW_DES_KMOLH["NH3"] * s
    nh3_shift = max(min(nh3_shift, 0.9 * offgas.get("NH3", 0.0)),
                    -0.5 * overflow.get("NH3", 0.0))
    overflow["NH3"] = overflow.get("NH3", 0.0) + nh3_shift   # NH3-rich melt at high feed N/C
    offgas["NH3"] = offgas.get("NH3", 0.0) - nh3_shift       # conserved: total NH3 unchanged

    # ---- conversion-deficit slip --------------------------------------------------------
    x_ref = x_des_live if x_des_live is not None else X_DES
    delta_x = max(1.0 - x_conv / x_ref, 0.0)
    slip_gain = OFFGAS_DEFICIT_GAIN * delta_x
    for k in ("NH3", "CO2"):
        shift = min(slip_gain * offgas.get(k, 0.0), overflow.get(k, 0.0))
        offgas[k] = offgas.get(k, 0.0) + shift
        overflow[k] = overflow.get(k, 0.0) - shift

    # ---- telemetry -----------------------------------------------------------------------
    offgas_total = sum(offgas.values())
    p_nh3_og = (offgas.get("NH3", 0.0) / offgas_total) * OFFGAS_P_DES_BARA \
        if offgas_total > 0.0 else 0.0
    p_co2_og = (offgas.get("CO2", 0.0) / offgas_total) * OFFGAS_P_DES_BARA \
        if offgas_total > 0.0 else 0.0

    # Total-mole closure. The urea step is the only one that changes the mole count, by -1 per
    # extent, so this is the whole balance and it should read machine zero. Reported only.
    closure_resid = (sum(corrected.values()) - xi_urea
                     - (sum(overflow.values()) + sum(offgas.values())))
    tear_mass = sum((tear_des_kmolh.get(k, 0.0) if tear_des_kmolh else 0.0) * MW_COMP[k]
                    for k in MW_COMP) * s_tear

    # ---- the column exotherm, for the energy balance -------------------------------------
    # xi_carb is a STREAM balance, not a second kinetic prediction: the free CO2 322E002 did
    # not condense, minus the CO2 that leaves in the off-gas, is by definition what formed
    # carbamate in this vessel. Taking it from the streams keeps it consistent with the split
    # instead of letting two mechanisms disagree about one quantity.
    xi_carbamate = max(gas_co2_in_kmolh - offgas.get("CO2", 0.0), 0.0)
    q_nodes = node_heat_kjh(
        carbamate_node_extents(
            xi_carbamate, node_liquid_volumes(ZETA_NODES, AREA_M2, LIQ_H_M, level)),
        xi_nodes)

    return ReactorResult(
        overflow_kmolh=overflow, offgas_kmolh=offgas, feed_kmolh=feed_kmolh,
        feed_corrected_kmolh=corrected,
        xi_urea=xi_urea, xi_biuret=xi_biuret, xi_carbamate=xi_carbamate,
        xi_nodes=xi_nodes, q_nodes_kjh=q_nodes,
        x_conv=x_conv, delta_x=delta_x, l_feed=l_feed, w_feed=w_feed,
        # The design values, which the engine overwrites with the live node profile once it
        # has integrated it. The unit publishes the anchor so a standalone call is complete.
        t_overflow_c=OVERFLOW_T_DES_C, t_offgas_c=OFFGAS_T_DES_C,
        # Rounded to two decimals as the screens show it; the engine replaces this with the
        # Darcy-Weisbach line pressure before it reaches a faceplate.
        p_bara=round(p_loop_bara, 2), p_offgas_bara=OFFGAS_P_DES_BARA,
        phi=phi, phi_des=phi_des, co2_scale=s,
        p_nh3_offgas_bara=p_nh3_og, p_co2_offgas_bara=p_co2_og,
        tear_mass_kgh=tear_mass, closure_resid=closure_resid)


# ======================================================================================
# The design pins
# ======================================================================================
#
# Everything below runs once, at import, and resolves entirely from source-anchored design
# vectors: the 322E002 design feed and gas, the published off-gas vector, the published
# overflow mass and the two published extents. No settled plant is needed for any of it,
# which is why it is here rather than in the engine's boot.

#: The residence-time SEED profile the calibration's reference temperature is taken from
#: [deg C]. Superseded as a model by the energy balance below; kept because the equilibrium
#: constant is quoted at its node mean and moving that reference would move the constant.
_SEED_PROFILE_C = node_profile_ss(FEED_T_DES_C, OVERFLOW_T_DES_C, ZETA_NODES, BETA_DAMKOHLER)

#: Kinetics at the seed profile. Its pre-exponential is superseded immediately below; its
#: equilibrium constant, reference temperature and biuret pre-exponential are final.
_SEED_KINETICS = calibrate_kinetics(
    _HPCC_DES.feed_kmolh, _SEED_PROFILE_C, ZETA_NODES, AREA_M2, LIQ_H_M,
    LEVEL_NLL_PCT / 100.0, VDOT_DES_M3H, XI_UREA_DES, XI_BIURET_DES, X_INF,
    OVERFLOW_DES_KMOLH["Urea"])

#: Design carbamate-formation extent [kmol/h], about 291.7. From the PFD streams: the free CO2
#: 322E002 hands over as GAS, minus the CO2 that leaves in the published off-gas vector. Both
#: are source quantities, neither is a fit.
XI_CARBAMATE_DES = max(_HPCC_DES.gas_kmolh["CO2"] - OFFGAS_DES_KMOLH.get("CO2", 0.0), 0.0)

#: Net column exotherm at design [kJ/h], about 13.94 million — 3.87 MW. The carbamate term is
#: 34.1 MW and the dehydration term takes 5.6 MW of it back; what reaches the liquid is the
#: difference, and it is 87 % of what the two raw numbers would suggest it is not.
Q_COL_DES_KJH = (XI_CARBAMATE_DES * (-CARBAMATE_DH_JMOL)
                 - XI_UREA_DES * DEHYDRATION_DH_JMOL)

#: Melt heat capacity [kJ/(kg.K)], about 4.741. BACK-SOLVED from the PFD column rise, and the
#: one constant in the energy balance that is.
#:
#: The repository has no heat capacity for a 140 bar a ammoniacal carbamate/urea melt.
#: `urea_soln_cp` is anchored on an AQUEOUS urea-solution value from the evaporation section
#: and gives 3.6096 here, which lands the column rise at 15.30 C against the PFD's 13.0. So
#: c_p is fixed by the column rise, and it is the right quantity to fix that way: it is a
#: genuine physical property, it is the one the repository is missing, and 4.7 kJ/(kg.K) is
#: entirely ordinary for a melt that is about 29 % ammonia by mass — liquid NH3 alone runs
#: above 5 at these conditions. The alternatives were worse: fixing a wall-loss coefficient
#: instead would have implied 18 W/(m2.K) on an insulated HP shell, which is not credible.
#:
#: It is not a free parameter fighting the other anchors. Once the pre-exponential is
#: calibrated so the extent is the PFD's, the duty is fully determined by the two anchored
#: extents and c_p = Q/(m.dT) closes on itself — the joint solve below converges straight back
#: to this value. Source: V1 `main.py` REACT_CP_MELT.
CP_MELT_KJKGK = Q_COL_DES_KJH / (OVERFLOW_DES_KGH * DT_COL_DES_C)

#: The design axial profile and the final kinetics, solved together against their two plant
#: anchors. This profile — not the seed above — is what the plant runs and what every dynamic
#: temperature state is seeded from.
NODE_PROFILE_DES, KINETICS = thermal_kinetic_fixed_point(
    _HPCC_DES.feed_kmolh, ZETA_NODES, AREA_M2, LIQ_H_M, LEVEL_NLL_PCT / 100.0,
    VDOT_DES_M3H, FEED_T_DES_C, OVERFLOW_T_DES_C, XI_CARBAMATE_DES, OVERFLOW_DES_KGH,
    CP_MELT_KJKGK, XI_UREA_DES, _SEED_KINETICS)

#: Design bulk melt temperature [deg C], the node mean of the profile above.
#:
#: Derived AFTER the fixed point, deliberately. V1 computed the bulk anchors against the seed
#: profile because the holdup has to exist before the energy balance can be solved, then
#: replaced the profile twice and never re-solved them — so its seeded holdup and its seeded
#: profile were two different design points, about 0.9 C of bulk temperature apart, and the
#: level stepped 0.156 % of span on the first tick reconciling them. That step propagated
#: straight into the conversion and from there into the steam header. V1 fixed it with a
#: re-derive pass; here the order is simply correct, which needs no pass.
T_BULK_DES_C = sum(NODE_PROFILE_DES) / len(NODE_PROFILE_DES)

#: Design bulk melt density [kg/m3].
RHO_BULK_DES = melt_density(T_BULK_DES_C)

#: Design liquid holdup [kg], about 135 904 — 137 m3 of melt.
M_LIQ_DES_KG = RHO_BULK_DES * AREA_M2 * (LEVEL_NLL_PCT / 100.0 * LIQ_H_M)

#: The three anchor fields that do not need a settled plant. The engine completes this with
#: the live design feed mass; see `ColumnAnchor`. The throughput here divides the design
#: overflow by the density of the melt at its own bulk temperature, which is a different basis
#: from `VDOT_DES_M3H` — that one divides by the constant PFD solution density. The two differ
#: by about 0.15 %, and V1 records that calibrating against one while the seed step runs at
#: the other left the design overflow CO2 1.29 kmol/h off its PFD value.
ANCHOR_SEED = {
    "t_nodes_c": list(NODE_PROFILE_DES),
    "level_frac": LEVEL_NLL_PCT / 100.0,
    "vdot_m3h": max(OVERFLOW_DES_KGH / max(RHO_BULK_DES, 1e-6), 1e-6),
}

#: The design evaluation — no tear, no boot pins, the published operating point.
DESIGN = reactor_322r001(
    _HPCC_DES.feed_kmolh, _HPCC_DES.gas_kmolh["CO2"], CO2_DES_KGH / 1000.0,
    HIC605_DES_PCT, SYN_P_DES_BARA, KINETICS)


__all__ = [
    "FEED_T_DES_C",
    "ColumnAnchor",
    "ReactorResult",
    "apply_reaction_extents",
    "reactor_322r001",
    "XI_CARBAMATE_DES",
    "Q_COL_DES_KJH",
    "CP_MELT_KJKGK",
    "NODE_PROFILE_DES",
    "KINETICS",
    "T_BULK_DES_C",
    "RHO_BULK_DES",
    "M_LIQ_DES_KG",
    "ANCHOR_SEED",
    "DESIGN",
]
