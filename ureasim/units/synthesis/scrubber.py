"""322E003 — the HP scrubber: the loop's recovery boundary and its inert purge.

What this module models
-----------------------
The vessel that decides how much ammonia the plant throws away. Inert-rich off-gas from the
reactor top meets cold weak carbamate falling down the tube walls; the ammonia and carbon
dioxide react into carbamate in the liquid film and go back into the loop through the
322F001 ejector, and the nitrogen, oxygen, methane and hydrogen leave through HV-322604 to
the LP absorber carrying whatever the cold top could not hold onto.

The equations, in the order the unit evaluates them
---------------------------------------------------
    feed     = reactor off-gas + weak-carbamate wash
    vent     = saturated_inert_vent(feed, K ratio at PT-329201)      to HV-322604
    overflow = feed - vent                                            to 322F001

    Q        = Q_des . s . nu . chi_spindle . chi_choke               shell-side duty
    eps      = 1 - exp(-UA / C_ccw)                                   effectiveness-NTU
    T_cond   = min(T_ccw,in + Q / (eps . C_ccw), T_proc)              TT-322002 before vent
    T_ccw,out= T_ccw,in + (T_cond - T_ccw,in) . eps                   TT-329125

plus two correlations for the published thermowells and a cooling-limited condensation
gate that moves mass back from the liquid to the vapour when the shell cannot keep up.

Two decided limits on that gate (handoff B-91, decided 2026-10-14):

  * **its own liquor's saturation.** The sump's carbamate condenses no more gas than its bubble
    pressure at its temperature allows at the live loop pressure: the model's law for the loop's
    melt (`carbamate_condenser.bubble_p_322e002`'s Clausius-Clapeyron slope and N/C, H/C lifts)
    anchored on PFD 206 at 165 C and the overflow line's 140.7 bar a (`liquor_bubble_p_bara`), read
    by `liquor_saturation.saturation_fraction` on the tick after;
  * **a full sump.** A sump that cannot take more liquid condenses no more than leaves it: the
    condensate is capped at the room the sump has this tick, net of the wash, the carryover and
    the recondensed backlog it takes in any case, and the rest stays in the vapour.

Why the vent is solved and the overflow taken by difference
------------------------------------------------------------
This is the single most important structural decision in the unit, and it is V1 finding A-2.

The obvious way round — pin the overflow on its PFD row and let the vent absorb the
balance — cannot work, because the loop's design flows do not close to better than a
couple of tonnes an hour and the vent is the smallest stream in the section. V1 tried it:
the vent came out at 214.8 kmol/h and 44 mol % ammonia, 5901 kg/h against the PFD's 1708.
That is a three-and-a-half-fold error on the one stream whose whole purpose is to be small,
and it made the modelled plant look as though it was throwing away four tonnes an hour of
ammonia it is not throwing away.

Solving the vent from its own physics instead — every inert that entered leaves, carrying
the condensables' saturation at the cold top — puts it back on the published row to 0.01 %,
and the overflow by difference then closes the unit per species BY CONSTRUCTION. The
residual this module publishes is a diagnostic that should read machine zero, never a
correction that is injected anywhere.

What is deliberately NOT here
-----------------------------
The sump inventory is a true state: its holdup integrates the condensate make against what
the ejector entrains, and at design those are the same number so the derivative is exactly
zero. The integration is the engine's, as the reactor's node temperatures are. Every
right-hand side it needs is in this module — `sump_level_pct`, `lt_329501_indication`,
`condensation_capacity` — so Phase 5 wires rather than derives.

HV-322604 itself is the next unit, not this one. This module publishes the off-gas at the
scrubber nozzle; the valve decides how much of it actually passes.

Source: V1 `backend/main.py` `scrub_322e003`, `scrub_vent_kmolh`, `scrub_cond_t_c`, and the
condensation-capacity and LT-329501 blocks of `step_sim`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ureasim.core.numeric import clamp
from ureasim.core.stream import MW_COMP
from ureasim.data.unit_320 import SYN_P_DES_BARA
from ureasim.data.unit_322e003 import (
    CCW_CP_KJKGK,
    CCW_KGH_DES,
    CCW_T_IN_DES_C,
    COND_CHOKE_MIN,
    COND_DH_JMOL,
    COND_P_DES_BARA,
    COND_R_JMOLK,
    COND_SPINDLE_GAIN,
    COND_T_DES_K,
    COOL_FRAC_EPS,
    DH_CARB_KJMOL,
    HIC604_DES_PCT,
    HOLDUP_NLL_KG,
    LEVEL_NLL_PCT,
    OFFGAS_NC_DES,
    OFFGAS_P_BARA,
    OFFGAS_T_DES_C,
    OFFGAS_T_GAIN,
    OFFGAS_T_VENT_GAIN,
    OVERFLOW_P_DES_BARA,
    OVERFLOW_T_DES_C,
    OVERFLOW_T_VENT_GAIN,
    Q_CCW_DES_KW,
    SWELL_NOISE_PCT,
    SWELL_NOISE_T1_S,
    SWELL_NOISE_T2_S,
    SWELL_PCT_MAX,
    T_PROC_C,
    UA_KWK,
    VENT_CONDENSABLE,
    VENT_INERTS,
    VENT_Y_DES,
    VENT_Y_MAX,
    WASH_KMOLH_DES,
)
from ureasim.data.unit_322e002 import (
    BUB_DHVAP_JMOL,
    BUB_KN,
    BUB_KW,
    BUB_RATIO_HI_FRAC,
    BUB_RATIO_LO_FRAC,
    FLASH_R_GAS_J,
)
from ureasim.data.unit_322r001 import OFFGAS_DES_KMOLH as REACTOR_OFFGAS_DES_KMOLH
from ureasim.thermo.service import saturated_inert_vent
from ureasim.units.synthesis.hp_split import hp_k_ratio

#: Floor on the heat-capacity rate of the cooling water [kW/K].
#:
#: Not a physical limit — a pole. FIC-329409 can be shut, and the effectiveness-NTU bridge
#: divides by this rate twice. Flooring it at 1e-6 lets the water rate go to zero and takes
#: the effectiveness to 1, which is the correct limit: with no water the process side and
#: the "return" temperature both walk up to the condensation ceiling. Source: V1 `main.py`.
C_CCW_FLOOR_KWK = 1.0e-6

#: Floor on the effective conductance [kW/K], for the same division.
UA_EFF_FLOOR_KWK = 1.0e-6

#: Floor on the ejector-spindle intensity ratio [-], guarding its reciprocal.
SPINDLE_PHI_FLOOR = 1.0e-6

#: Floor on the pressure the Clausius-Clapeyron relation takes a logarithm of [bar a].
COND_P_FLOOR_BARA = 1.0e-6

#: Reciprocal of the condensing-temperature anchor [1/K], held so that a call at the design
#: pressure produces a literal ``log(1.0) == 0.0`` and an identical reciprocal.
_COND_INV_DES = 1.0 / COND_T_DES_K


@dataclass(frozen=True)
class ScrubberResult:
    """One evaluation of 322E003, as the ejector, HV-322604 and the screens read it."""

    # ---- the streams [kmol/h] -------------------------------------------------------------
    #: Combined tube feed: reactor off-gas plus wash, plus any flood carryover.
    feed_kmolh: dict
    #: The weak-carbamate wash alone, at the live delivery ratio.
    carb_kmolh: dict
    #: Vent off the top to HV-322604 and the LP absorber — PFD stream 204 at design.
    offgas_kmolh: dict
    #: Bottom overflow to the 322F001 ejector — PFD stream 206 at design.
    overflow_kmolh: dict

    # ---- absorption and duty -----------------------------------------------------------
    #: CO2 taken out of the gas and turned into carbamate [kmol/h].
    co2_abs: float
    #: Absorption exotherm at the full reaction enthalpy [kW]. Diagnostic.
    q_carb_kw: float
    #: Shell-side condensation duty actually realised [kW], after every derate.
    q_ccw_kw: float

    # ---- the cooling water ---------------------------------------------------------------
    #: TIC-329005 supply and TT-329125 return temperatures [deg C], and their difference,
    #: which is the TDY-329125 condensation-quality indicator.
    t_ccw_in_c: float
    t_ccw_out_c: float
    dt_ccw_c: float
    #: Circulation the duty was carried on [kg/h].
    m_ccw_kgh: float
    #: Single-stream effectiveness [-] and the effective conductance it implies [kW/K].
    eps_ht: float
    ua_eff_kwk: float

    # ---- the condensation gate ------------------------------------------------------------
    #: Condensation capacity as a fraction of demand [-], 1.0 at and above full capacity.
    cool_frac: float
    #: What the shell failed to condense and handed back to the vapour [kmol/h] and [kg/h].
    uncond_kmolh: float
    uncond_kgh: float

    # ---- operating point ---------------------------------------------------------------------
    #: TT-322011 vent-top and TT-322002 bottom-overflow temperatures [deg C].
    t_offgas_c: float
    t_overflow_c: float
    #: Off-gas and overflow line pressures [bar a].
    p_offgas_bara: float
    p_overflow_bara: float
    #: CO2 throughput ratio and synthesis-vent load ratio the duty was scaled by [-].
    co2_scale: float
    vent_ratio: float

    #: Total-mole closure residual [kmol/h]. A diagnostic, never injected.
    closure_resid: float = field(default=0.0)
    #: The share of its condensate a full sump took [-], 1 below full (B-91, decided 2026-10-14).
    sump_frac: float = 1.0


def vent_kmolh(feed_kmolh: dict, ratio: dict = None) -> dict:
    """The 322E003 vent [kmol/h] — this vessel's own saturated-inert closure.

    Process utility
    ---------------
    What leaves the cold top. Every inert in the tube feed, because nothing in the vessel
    can absorb one, saturated with the ammonia, carbon dioxide and water the top can hold at
    the loop pressure. That is the whole inert purge, and it is the plant's only deliberate
    ammonia loss.

    The saturation vector and the cap are 322E003's own, from PFD stream 204; the closure
    itself is `thermo.splits.saturated_inert_vent`, which the 324 vacuum condensers use as
    well. Passing no ratio is the design K, and a ratio of exactly 1.0 multiplies the design
    saturation by a literal 1.0 — so a design call and a live call at the design pressure
    are the same arithmetic and produce the same float.

    Returned over the full component vector, with zeros for urea and biuret, because every
    consumer of this stream subtracts it from a feed written on that vector.

    Source: V1 `main.py` `scrub_vent_kmolh`, report A-2.
    """
    v = saturated_inert_vent(feed_kmolh, VENT_INERTS, VENT_CONDENSABLE,
                             VENT_Y_DES, VENT_Y_MAX, ratio)
    return {k: v.get(k, 0.0) for k in MW_COMP}


def condensing_temperature_c(p_bara: float) -> float:
    """Temperature the shell condenses carbamate at, at the live loop pressure [deg C].

    Process utility
    ---------------
    The driving force the cooling water works against is the gap between the condensing
    temperature and the water, and the condensing temperature is not a constant: it rides
    the loop pressure, because that is what a condensing vapour does. A loop drifting up in
    pressure condenses MORE readily, not less.

    That sign is the reason this function exists. V1's earlier form held the condensing
    temperature at its design anchor and divided the whole capacity by the pressure ratio
    instead, which asserts the opposite — and with the sign wrong the loop fed back on
    itself: capacity fell, off-gas went uncondensed, the retained vapour pushed the pressure
    higher, and capacity fell further. Six of the eight design-seed inertness gaps in the
    cooling-water chain were that one loop.

    Equation
    --------
        1/T_cond(P) = 1/T_des - (R / dH_carb) . ln(P / P_des)

    Written as an INCREMENT on the design temperature, so at the design pressure the
    logarithm is a literal 0.0, the reciprocal is identical, and the bracket is exactly 0.0.
    The design point cannot move. The slope at the anchor is R.T^2/(dH.P) = 0.0709 K/bar, so
    the 0.7 bar the loop drifts over an hour is worth 0.05 C of driving force.

    Source: V1 `main.py` `scrub_cond_t_c`.
    """
    inv = _COND_INV_DES - (COND_R_JMOLK / COND_DH_JMOL) * math.log(
        max(p_bara, COND_P_FLOOR_BARA) / COND_P_DES_BARA)
    return OVERFLOW_T_DES_C + (1.0 / inv - 1.0 / _COND_INV_DES)


def condensation_capacity(m_ccw_kgh: float, ccw_pump_frac: float, t_ccw_in_c: float,
                          p_loop_bara: float, co2_scale: float) -> float:
    """Condensation capacity as a fraction of the demand on it [-].

    Process utility
    ---------------
    The one number that decides whether this vessel is doing its job. Above 1.0 the shell
    condenses everything the loop sends it and the unit behaves as designed. Below 1.0 the
    shortfall stays in the vapour, leaves with the vent instead of the overflow, and — since
    322E003 is INSIDE the loop and nothing has crossed a boundary — shows up as rising
    synthesis pressure rather than as a mass imbalance. It is the entry point of the
    loss-of-cooling scenario.

    Equation
    --------
        f_th = (T_cond(P) - T_ccw,in) / (T_cond,des - T_ccw,in,des)    thermal driving force
        rho  = (m_ccw / m_ccw,des) . pump_frac . max(f_th, 0) / s      capacity over demand

    Three independent ways to lose it, which is what makes the scenario teachable: throttle
    the water (the flow term), lose the temper (the driving-force term), or stop the pumps
    (the pump term). All three are exactly 1.0 at design, so the product is too.

    Why the pump fraction is separate from the flow
    -------------------------------------------------
    The flow term reads the FT-329409 transmitter, which carries a 25 s plant lag. The
    circulation itself stops with the pumps, immediately, because their discharge check
    valves shut. Reading the capacity off the lagged indication alone left 0.33 % of design
    condensation alive long after both 329P006 machines had been stopped.

    Source: V1 `main.py` `step_sim`, the rho_cond block.
    """
    t_cond = condensing_temperature_c(p_loop_bara)
    f_th = (t_cond - t_ccw_in_c) / max(OVERFLOW_T_DES_C - CCW_T_IN_DES_C, 1e-6)
    return ((m_ccw_kgh / CCW_KGH_DES) * ccw_pump_frac
            * max(f_th, 0.0) / max(co2_scale, 1e-6))


def sump_level_pct(holdup_kg: float) -> float:
    """True sump inventory as a level [%], from the holdup the engine integrates.

    Process utility
    ---------------
    The level the physics reads — the condensation choke above and the ejector's suction
    head both key off this, not off the transmitter. Linear in holdup, because the sump is
    a constant cross-section, and scaled so the design inventory reads normal level exactly.

    Source: V1 `main.py` `step_sim`, the 322E003 inventory block.
    """
    return clamp(holdup_kg / HOLDUP_NLL_KG * LEVEL_NLL_PCT, 0.0, 100.0)


def lt_329501_indication(level_pct: float, cool_frac: float, sim_t_s: float) -> float:
    """What the LT-329501 transmitter READS [%], which is not the level.

    Process utility
    ---------------
    This is an operator trap and it is modelled deliberately. LT-329501 is a differential-
    pressure cell: it reads the hydrostatic head of the column between its taps, not the
    mass in the vessel. Stop condensing and the sump boils; the mixture density collapses
    with the void fraction and the column swells upward to hold the same mass. Over a fast
    transient the swell beats the density loss, so **the cell reads HIGH while the vessel is
    actually draining** — the drain to 322F001 keeps pulling after the condensate make has
    stopped.

    And it hunts as well as reading high: a DP cell straddling a frothing column sees the
    head fluctuate as slugs and bubbles cross its taps. Two incommensurate periods off the
    simulation clock, not a random number, so an instructor replays the same excursion the
    same way every time.

    Both terms scale with the condensation deficit, so at design they are identically zero
    and the indication IS the level, bit-exact.

    Source: V1 `main.py` `step_sim`, the LT-329501 swell overlay.
    """
    return clamp(level_pct + lt_329501_swell(cool_frac) + lt_329501_noise(cool_frac, sim_t_s),
                 0.0, 100.0)


def lt_329501_swell(cool_frac: float) -> float:
    """The two-phase swell LT-329501's indication carries [% of span], zero while the shell
    condenses in full. V1 publishes it beside the indication. Source: V1 `main.py`
    ``scrub_swell_pct``."""
    return SWELL_PCT_MAX * (1.0 - cool_frac)


def lt_329501_noise(cool_frac: float, sim_t_s: float) -> float:
    """The froth's hunt on LT-329501's head [+/- % of span], off the plant clock. V1 publishes it
    beside the indication. Source: V1 `main.py` ``scrub_swell_noise``."""
    return SWELL_NOISE_PCT * (1.0 - cool_frac) * (
        math.sin(2.0 * math.pi * sim_t_s / SWELL_NOISE_T1_S)
        + 0.6 * math.sin(2.0 * math.pi * sim_t_s / SWELL_NOISE_T2_S)) / 1.6


def scrubber_322e003(offgas_feed_kmolh: dict, co2_scale: float, t_ccw_in_c: float,
                     m_ccw_kgh: float, p_loop_bara: float = OVERFLOW_P_DES_BARA,
                     vent_ratio: float = 1.0, nc_act: float = None,
                     hic604_pct: float = None,
                     liq_carry_kmolh: dict = None, t_carry_c: float = None,
                     choke_level_pct: float = None, spindle_phi: float = 1.0,
                     cool_frac: float = 1.0, wash_ratio: float = None,
                     sump_room_kgh: float = None) -> ScrubberResult:
    """Solve 322E003 for one tick.

    Parameters
    ----------
    offgas_feed_kmolh
        Live reactor off-gas into the bottom channel [kmol/h], TT-322009.
    co2_scale
        CO2 throughput against design [-]. Scales both the wash (when no live delivery is
        given) and the shell duty.
    t_ccw_in_c, m_ccw_kgh
        TIC-329005 supply temperature [deg C] and FIC-329409 circulation [kg/h].
    p_loop_bara
        PT-329201 [bar a]. The ONE live state the vent saturation rides — see below.
    vent_ratio
        Synthesis-vent load against design [-], PT-329201 over its design value. A loop at
        higher pressure pushes more uncondensed vapour into the scrubber, so the
        carbamate-condensation duty scales with it.
    nc_act
        AT-322701, the loop N/C [-]. Drives the published vent-top temperature.
    hic604_pct
        HIC-322604 opening [%]. Couples the purge valve into both published temperatures.
    liq_carry_kmolh, t_carry_c
        Entrained reactor melt on a flood [kmol/h] and its temperature [deg C].
    choke_level_pct
        Prior-tick LT-329501 [%], for the flooded-surface derate.
    spindle_phi
        322F001 spindle intensity [-], 1.0 at the design HV-322602 opening.
    cool_frac
        Condensation capacity over demand [-], from `condensation_capacity`.
    wash_ratio
        Live 323P001 delivery against design [-]. Defaults to the CO2 throughput ratio.
    sump_room_kgh
        What the sump can take this tick [kg/h]: its drains, less the backlog it recondenses, and
        the room up to full over the tick. None, V1's, is no limit.

    Every optional argument is at its design value when omitted, and every term it drives is
    written as a deviation that is exactly zero there — so the design call reproduces the
    published streams and temperatures to the bit.

    Why the saturation rides the PRESSURE and not the temperature
    ---------------------------------------------------------------
    The vent's K-value ratio is evaluated at the design temperature on both sides and at the
    live pressure on one, so temperature deliberately does not enter. The published vent-top
    temperature in this model is a CORRELATION — a design pin plus two fitted deviation
    gains — and feeding a fitted gain into a rigorous thermodynamic ratio measured badly: it
    took the 322C001 liquor stationarity from 8e-9 to 4e-4. PT-329201 is a measurement, and
    it is the right thing to ride.

    The feedback is small and it is dominated. The condensables are about 11 mol % of the
    vent, so the ratio moves the vented total by -0.072 % per bar (-1.1 kg/h/bar), against
    HV-322604's choked law at +12.1 kg/h/bar in the opposite direction.

    Source: V1 `main.py` `scrub_322e003`.
    """
    s = co2_scale

    # ---- the two tube feeds --------------------------------------------------------------
    # The wash is what 323P001 A/B actually delivers. Scaling it by CO2 throughput instead is
    # the unit-test path and V1's older behaviour; it left the loop boundary short whenever
    # the LIC-323502 cascade sagged, because the scrubber went on condensing a design wash
    # the pump was not sending.
    wash = s if wash_ratio is None else wash_ratio
    carb = {k: WASH_KMOLH_DES.get(k, 0.0) * wash for k in MW_COMP}
    feed = {k: offgas_feed_kmolh.get(k, 0.0) + carb[k] for k in MW_COMP}

    # ---- the vent, and the overflow by difference -----------------------------------------
    # Evaluated at the design temperature on both sides of the ratio, so only the pressure
    # deviation survives; at the design pressure the ratio is exactly 1.0 and the two design
    # vectors come back bit-exact.
    ratio = hp_k_ratio(feed, OFFGAS_T_DES_C, p_loop_bara,
                       OFFGAS_T_DES_C, SYN_P_DES_BARA)
    offgas = vent_kmolh(feed, ratio)
    overflow = {k: feed[k] - offgas[k] for k in MW_COMP}

    # ---- reactor off-gas-line liquid carryover on a flood ----------------------------------
    # With the reactor holdup at the physical vessel-full limit the melt that cannot pass the
    # overflow funnel spills into the off-gas line and arrives here as entrained liquid. It
    # enters the tube feed AND leaves with the bottom overflow, so the two additions cancel
    # in the closure and the unit stays balanced. Below the flood lip there is no carryover
    # and every term below is identically unchanged.
    carry_mass_kgh = 0.0
    if liq_carry_kmolh:
        for k in MW_COMP:
            c = liq_carry_kmolh.get(k, 0.0)
            feed[k] += c
            overflow[k] += c
            carry_mass_kgh += c * MW_COMP[k]

    # ---- cooling-limited condensation ------------------------------------------------------
    # Carbamate formation is strongly exothermic, so the rate at which the shell can put
    # NH3 and CO2 into the liquid is limited by the rate at which the water can carry the
    # exotherm away. Below full capacity the shell cannot hold the film temperature down,
    # solubility collapses, and the fraction (1 - cool_frac) of what would have condensed
    # simply stays as vapour.
    #
    # Mass-conserving by construction: every kmol taken off the overflow is added to the
    # off-gas, so the closure residual is untouched. Only the CONDENSED part can flash back —
    # the wash arrived as liquid and stays liquid however hot the shell gets.
    cf = 1.0 if cool_frac >= 1.0 - COOL_FRAC_EPS else clamp(cool_frac, 0.0, 1.0)
    uncond_kmolh = 0.0
    uncond_kgh = 0.0
    if cf < 1.0:
        for k in MW_COMP:
            back = (1.0 - cf) * max(overflow[k] - carb[k], 0.0)
            overflow[k] -= back
            offgas[k] += back
            uncond_kmolh += back
            uncond_kgh += back * MW_COMP[k]

    # ---- a full sump condenses no more than leaves it ------------------------------------------
    # Decided 2026-10-14 (handoff B-91): the condensate is liquid the sump has to take, and a sump
    # at its top takes only what drains from it. The wash, the carryover and the backlog's
    # recondensate run in whatever happens; the condensate gets the room left, and what it cannot
    # take stays in the vapour, as above. Below a full sump the room is the whole tick's volume and
    # nothing binds — the design point.
    g_sump = 1.0
    if sump_room_kgh is not None:
        carry = liq_carry_kmolh or {}
        cond = {k: max(overflow[k] - carb[k] - carry.get(k, 0.0), 0.0) for k in MW_COMP}
        m_cond = sum(cond[k] * MW_COMP[k] for k in MW_COMP)
        m_cap = max(sump_room_kgh - sum(carb[k] * MW_COMP[k] for k in MW_COMP)
                    - carry_mass_kgh, 0.0)
        if m_cond > m_cap:
            g_sump = m_cap / m_cond
            for k in MW_COMP:
                back = (1.0 - g_sump) * cond[k]
                overflow[k] -= back
                offgas[k] += back
                uncond_kmolh += back
                uncond_kgh += back * MW_COMP[k]
            cf *= g_sump

    # Diagnostic only. The vent is solved and the overflow is a difference, so this is zero
    # by construction and a non-zero reading means the arithmetic above has been changed.
    closure_resid = sum(feed.values()) - sum(offgas.values()) - sum(overflow.values())

    # ---- the absorption duty ----------------------------------------------------------------
    # What the gas lost, not what the liquid gained: the wash brings its own CO2 in and that
    # carbon was never absorbed here.
    co2_abs = max(offgas_feed_kmolh.get("CO2", 0.0) - offgas["CO2"], 0.0)
    q_carb_kw = co2_abs * 1000.0 * DH_CARB_KJMOL / 3600.0

    # ---- the shell-side duty and its three derates -------------------------------------------
    # The base duty is the design condensation load scaled by throughput and by the
    # synthesis-vent load: in a closed loop a rise in reactor-top pressure lifts the
    # uncondensed vent load into this vessel, so the exotherm it has to remove rises with it.
    q_ccw_kw = Q_CCW_DES_KW * s * vent_ratio

    # HV-322602 spindle intensity. The motive jet sets how hard the off-gas is drawn down
    # through the bottom condensation zone: a stronger jet condenses more per unit time.
    # Exactly 1.0 at the design opening, so the published temperatures stay pinned; keyed on
    # the spindle rather than on the level so it is independent of the steady sump inventory.
    chi_sp = 1.0 + COND_SPINDLE_GAIN * (1.0 - 1.0 / max(spindle_phi, SPINDLE_PHI_FLOOR))
    q_ccw_kw *= max(chi_sp, COND_CHOKE_MIN)

    # Flooded-surface derate. A sump filling above normal level floods the condensation
    # surface from the bottom, so the duty falls linearly to its floor at a full sump. At or
    # below normal level the factor is exactly 1.0. The signature is worth knowing: above
    # normal level the CCW rise TDY-329125 FALLS, because less is being condensed.
    if choke_level_pct is not None:
        chi_choke = 1.0 - (1.0 - COND_CHOKE_MIN) \
            * max(choke_level_pct - LEVEL_NLL_PCT, 0.0) / max(100.0 - LEVEL_NLL_PCT, 1e-6)
        q_ccw_kw *= clamp(chi_choke, COND_CHOKE_MIN, 1.0)

    # ---- the effectiveness-NTU bridge ---------------------------------------------------------
    # Bounds BOTH the cooling-water outlet and the process overflow against the condensation
    # ceiling, and removes the divide-by-zero a shut FIC-329409 used to produce — the raw
    # sensible rise and the raw duty-over-conductance both went to about 1e9 C.
    #
    # The design point falls out of the algebra rather than being asserted: the effective
    # conductance was back-solved so that the design duty over it IS the design approach, so
    # the effectiveness times that approach is the design duty over the heat-capacity rate,
    # which is the published 15.0 K rise exactly. Anchoring the water's gradient to the LIVE
    # condensing temperature rather than to the ceiling is what preserves it — against the
    # raw ceiling the return drifts to 95.9 C.
    c_ccw_kwk = max(m_ccw_kgh * CCW_CP_KJKGK / 3600.0, C_CCW_FLOOR_KWK)
    eps_ht = 1.0 - math.exp(-UA_KWK / c_ccw_kwk)
    ua_eff_kwk = max(eps_ht * c_ccw_kwk, UA_EFF_FLOOR_KWK)

    # HV-322604 opening deviation, two-sided and exactly zero at the design opening.
    theta_dev = (hic604_pct if hic604_pct is not None
                 else HIC604_DES_PCT) / HIC604_DES_PCT - 1.0

    t_overflow_cond = min(t_ccw_in_c + q_ccw_kw / ua_eff_kwk, T_PROC_C)
    t_ccw_out_c = t_ccw_in_c + (t_overflow_cond - t_ccw_in_c) * eps_ht

    # TT-322002. Opening the purge relieves the vessel and cools the bottom carbamate;
    # closing it pressurises and heats it toward the condensation ceiling. Bounded below by
    # the cooling water — the overflow cannot be colder than what is cooling it.
    t_overflow_c = min(max(t_overflow_cond - OVERFLOW_T_VENT_GAIN * theta_dev, t_ccw_in_c),
                       T_PROC_C)

    # Entrained hot reactor melt lifts the bottom temperature, as an enthalpy mass-blend over
    # the post-carryover overflow. Zero weight below the flood lip, so the pin holds.
    if carry_mass_kgh > 0.0 and t_carry_c is not None:
        m_ov_tot = sum(overflow[k] * MW_COMP[k] for k in MW_COMP)
        if m_ov_tot > 0.0:
            w_carry = carry_mass_kgh / m_ov_tot
            t_overflow_c = min(t_overflow_c + w_carry * (t_carry_c - t_overflow_c), T_PROC_C)

    # TT-322011. At a higher loop N/C the synthesis runs CO2-limited, the excess ammonia has
    # no carbon to form carbamate with, and it slips through unabsorbed — a bigger vapour
    # load over the top and a hotter vent thermowell. Bounded by the same two physical rails
    # as the overflow. At design the analyser sits on its reference and the deviation is 0.
    nc = nc_act if nc_act is not None else OFFGAS_NC_DES
    t_offgas_c = min(max(OFFGAS_T_DES_C + OFFGAS_T_GAIN * (nc - OFFGAS_NC_DES)
                         + OFFGAS_T_VENT_GAIN * theta_dev,
                         t_ccw_in_c), T_PROC_C)

    return ScrubberResult(
        feed_kmolh=feed, carb_kmolh=carb,
        offgas_kmolh=offgas, overflow_kmolh=overflow,
        co2_abs=co2_abs, q_carb_kw=q_carb_kw, q_ccw_kw=q_ccw_kw,
        t_ccw_in_c=t_ccw_in_c, t_ccw_out_c=t_ccw_out_c,
        dt_ccw_c=t_ccw_out_c - t_ccw_in_c, m_ccw_kgh=m_ccw_kgh,
        eps_ht=eps_ht, ua_eff_kwk=ua_eff_kwk,
        cool_frac=cf, uncond_kmolh=uncond_kmolh, uncond_kgh=uncond_kgh, sump_frac=g_sump,
        t_offgas_c=t_offgas_c, t_overflow_c=t_overflow_c,
        # The design line pressures. The engine overwrites both with the live PT-329201,
        # which is the same tap: the vent line and the overflow line are one vessel.
        p_offgas_bara=OFFGAS_P_BARA, p_overflow_bara=OVERFLOW_P_DES_BARA,
        co2_scale=s, vent_ratio=vent_ratio,
        closure_resid=closure_resid)


#: The published design point, evaluated at import from the design vectors alone.
#:
#: Reproduces PFD streams 204 and 206, the 165 C overflow and the 95.0 C cooling-water
#: return with every optional argument at its default — which is the statement that none of
#: the deviation terms above is doing any work at the design state.
DESIGN = scrubber_322e003(REACTOR_OFFGAS_DES_KMOLH, 1.0, CCW_T_IN_DES_C, CCW_KGH_DES)


#: PFD 206's NH3/CO2 and H2O/CO2 [-], the sump liquor's bubble-pressure anchors: 2.550 and 1.299.
LIQUOR_NC_DES = DESIGN.overflow_kmolh["NH3"] / DESIGN.overflow_kmolh["CO2"]
LIQUOR_HC_DES = DESIGN.overflow_kmolh["H2O"] / DESIGN.overflow_kmolh["CO2"]

#: The sump liquor's design head over PT-329201 [bar], a subtraction of the two design pressures
#: (A-13): PFD 206 leaves at the loop's own 140.7 bar a, so zero — the design liquor stands at its
#: bubble point.
LIQUOR_DP_DES_BAR = OVERFLOW_P_DES_BARA - SYN_P_DES_BARA

#: The reciprocal of the liquor's anchor temperature [1/K].
_LIQUOR_INV_T_DES = 1.0 / (OVERFLOW_T_DES_C + 273.15)


def liquor_bubble_p_bara(overflow_kmolh: dict, t_c: float) -> float:
    """Bubble pressure of 322E003's sump liquor [bar a] — what its carbamate would boil at.

    Process utility
    ---------------
    The scrubber's condensate is a carbamate liquor in contact with the loop's gas. It takes up
    NH3 and CO2 only while the loop stands above the pressure it would boil at: a hot, ammonia-rich
    sump on a low loop pressure condenses nothing more, and the gas stays in the vapour and builds
    the pressure (handoff B-91, decided 2026-10-14, option (a)).

    Equation
    --------
        P = P_206 . exp[(dH/R)(1/T_206 - 1/T)] . max(fN, 0) . max(fW, 0)
        fN = 1 + K_N (N/C - N/C_206),   fW = 1 + K_W (H/C - H/C_206)

    the model's own law for the loop's melt (PI-322E002: dH 23 kJ/mol, K_N 0.18, K_W -0.25), its
    ratios clamped to the same band about design, anchored on PFD 206 at 165 C and the overflow
    line's 140.7 bar a. No document gives the scrubber liquor's own law, and the Extended UNIQUAC
    model returns a negative slope on PFD 206 (handoff, Open data gaps), so the melt's law carries
    it. The design liquor returns the anchor exactly.
    """
    co2 = overflow_kmolh.get("CO2", 0.0)
    nc = (clamp(overflow_kmolh.get("NH3", 0.0) / co2, BUB_RATIO_LO_FRAC * LIQUOR_NC_DES,
                BUB_RATIO_HI_FRAC * LIQUOR_NC_DES) if co2 > 1e-9 else LIQUOR_NC_DES)
    hc = (clamp(overflow_kmolh.get("H2O", 0.0) / co2, BUB_RATIO_LO_FRAC * LIQUOR_HC_DES,
                BUB_RATIO_HI_FRAC * LIQUOR_HC_DES) if co2 > 1e-9 else LIQUOR_HC_DES)
    cc = math.exp((BUB_DHVAP_JMOL / FLASH_R_GAS_J) * (_LIQUOR_INV_T_DES - 1.0 / (t_c + 273.15)))
    return (OVERFLOW_P_DES_BARA * cc * max(1.0 + BUB_KN * (nc - LIQUOR_NC_DES), 0.0)
            * max(1.0 + BUB_KW * (hc - LIQUOR_HC_DES), 0.0))
