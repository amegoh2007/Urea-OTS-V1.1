"""322E002 — the HP carbamate condenser: a calibrated split with a real flash on top.

What this models
----------------
The stripper's top gas and the ejector's carbamate discharge meet in the top channel of a
vertical falling-film condenser and run down together. NH3 and CO2 condense into the film and
react to ammonium carbamate; a two-phase product leaves for the reactor. On the shell,
322D001 boiler feed water boils and raises the plant's own 4.4 bar a LP steam.

This is where urea synthesis begins, and it is the largest LP-steam source on the plant.

Source
------
Ported from V1 `backend/main.py` `hpcc_322e002`, `_hpcc_flash_split` and `bubble_p_322e002`,
with findings AUDIT F-6 / TD-007 and the Option-1 disturbance gate.

The four layers, and why each one is there
-------------------------------------------
1. **A calibrated split.** The licensor balance fixes what fraction of each feed component
   leaves as gas at the design point. Urea is unchanged across the unit, so at calibration it
   is a pure phase split with the carbamate reaction implicit in the numbers.

2. **An isothermal flash on top of it.** Frozen, the calibration makes the condenser
   thermodynamically INERT — raising the LP-steam pressure would change the shell duty and the
   outlet temperature but not one mole of condensate, and a synthesis-pressure excursion would
   move nothing at all. `hpcc_flash_split` binds a real (T, P) Rachford-Rice flash on top,
   with the calibration as its anchor: K_i,des is back-solved from the measured split against
   the LIVE feed composition every tick, so the activity coefficients of this strongly
   non-ideal electrolyte melt stay baked into the K-values exactly as measured, and only the
   DEPARTURE from the calibration is model-driven.

3. **A film relaxation, which makes the split a dynamic state.** A pure equilibrium split is
   far too stiff for this vessel: the distributing K-values are tightly clustered, so a common
   factor moves the whole mixture together and a plus-or-minus 10 C excursion alone drives the
   CO2 split from 0.001 to 1.0. That is not how a falling-film condenser behaves.
   `References/HPCC description.md` §5.2-5.3 is explicit that 322E002 is INTERFACIAL
   MASS-TRANSFER limited — the gas has to diffuse to the film, cross the interface and react,
   so the achievable split LAGS equilibrium by the film's own residence time. The flash is the
   equilibrium TARGET; the split relaxes toward it over the condenser holdup constant. This is
   the audit's "missing equation" for this tag: the condenser had no composition dynamics at
   all.

4. **An effectiveness-NTU quench**, which turns the reaction exotherm into an outlet
   temperature against the boiling shell.

Between the split and the quench, the melt's saturation (handoff B-91 (a), decided 2026-10-10): a
melt above its bubble point for the loop's pressure holds only the fraction ``sat_frac`` of the
volatiles the split would condense (`liquor_saturation.saturation_fraction`); the rest leaves as
gas and releases no carbamate heat. 1 at and above the bubble pressure, where the split is V1's.

The disturbance gate
--------------------
Two of this unit's couplings are exactly their design value at the published operating point
and have loop gain above 1 around it:

    P_LP up -> T_shell up -> T_prod up -> reactor up -> duty up -> more steam -> P_LP up
    conversion up -> T_adb up -> T_prod up -> reactor inlet up -> conversion up

so a fresh seed — which is not the dynamic fixed point — self-excites a thermal runaway with
no operator action at all. V1's Option-1 fix gates BOTH coupling deltas by a genuine-
disturbance factor in [0, 1], computed from the exogenous operator and feed handles: zero when
every handle sits at its design value, so the couplings are pinned to design and the balance
is bit-exact, and one as soon as any handle moves, so the full off-design response is back.

`gate` arrives here as an argument; 0 returns the calibration bit-exactly, 1 the full response.
DECIDED 2026-10-09 (handoff B-13): the plant runs it at 1.0 permanently — the film dynamics, the
flash and the NTU quench live at every operating point, and no handle vector is read
(`condenser_holdup` passes 1.0). V1's ``step_sim`` does the same (``g_dist = 1.0``, ``main.py``
7692-7701, its header pressure propagated through the shell); its ``_disturbance_gate`` is defined
and never called.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ureasim.core.numeric import clamp
from ureasim.core.stream import MW_COMP
from ureasim.data.unit_320 import SYN_P_DES_BARA
from ureasim.data.unit_322e002 import (
    BUB_DHVAP_JMOL,
    BUB_KN,
    BUB_KW,
    BUB_RATIO_HI_FRAC,
    BUB_RATIO_LO_FRAC,
    CP_GAS,
    DH_CARB_KJMOL,
    FLASH_DH,
    FLASH_ITERS,
    FLASH_R_GAS_J,
    FLASH_T0_K,
    FRAC_GAS_DES,
    LATENT_4BAR,
    P_DES_BARA,
    STEAM_TSAT_C,
    T_PROD_DES_C,
    TAU_FILL_MIN,
)
from ureasim.data.unit_322r001 import REACTOR_FEED_HC_DES, REACTOR_FEED_NC_DES
from ureasim.units.synthesis.ejector import DESIGN as _EJECTOR_DES
from ureasim.units.synthesis.stripper import TOP_DES_KMOLH, TOP_DES_T_C

#: Sentinel for "use the module's design-pinned shell conductance". Passing ``None`` instead
#: means the opposite — hold the outlet at its design pin, which is the state the conductance
#: is back-calculated in and the only time that branch is wanted.
_PINNED = object()


# ======================================================================================
# The isothermal flash
# ======================================================================================

def hpcc_flash_split(feed_kmolh: dict, t_c: float, p_loop_bara: float) -> dict:
    """Isothermal (T, P) flash of the tube-side feed. Returns the gas fraction per component.

    Process utility
    ---------------
    This is what makes the condenser respond to anything. It says how much of each component
    the vessel can hold in the liquid at the temperature and pressure it is actually at,
    rather than at the one point where it was measured.

    How the calibration survives
    ----------------------------
    K_i,des is back-solved from the measured split against the LIVE feed composition, so the
    electrolyte melt's activity coefficients stay in the K-values exactly as measured. Only
    the departure is model-driven, through the carbamate-equilibrium, Raoult and Henry slopes:

        psi_des = sum_i z_i . phi_i,des                     the split the calibration gives
        K_i,des = phi_i,des (1 - psi_des) / (psi_des (1 - phi_i,des))
        K_i     = K_i,des . exp[(dH_i/R)(1/T_des - 1/T)] . (P_des/P)

    and the flash is then the standard Rachford-Rice solve:

        g(psi) = sum_i z_i (K_i - 1) / (1 + psi (K_i - 1)) = 0
        phi_i  = K_i psi / (1 + psi (K_i - 1))

    Why bisection
    -------------
    ``g`` is strictly decreasing on [0, 1], so a fixed 60-sweep bracket is exact to 2^-60 with
    BOUNDED cost and no possible convergence failure. An OTS tick must never miss its
    deadline, and that is worth more here than the iterations Newton would save.

    Which components flash
    ----------------------
    Only those whose calibrated split lies strictly between 0 and 1. A component calibrated at
    exactly 1 never condenses and one at exactly 0 never boils; both are structurally
    non-distributing and are returned untouched.

    Guards, and what is NOT a guard
    -------------------------------
    The two early returns each protect a division on the very next line — by the distributing
    feed total, and by ``psi(1 - phi)``. With no distributing feed, or a feed already single
    phase, there is no flash to solve, so returning the design vector is a degenerate-input
    answer rather than a bypass of the maths.

    What V1 REMOVED, and why it matters (finding A-15): there used to be a third branch that
    returned the design vector whenever the pressure ratio was exactly 1 and the temperature
    exactly the design one. At the calibration point the routine now runs the same solve it
    runs everywhere else and lands on the design split by CONVERGING to it — so the residual
    of the K-value model at that point is no longer invisible.
    """
    p_rat = SYN_P_DES_BARA / max(p_loop_bara, 1e-6)
    t_k = t_c + 273.15

    dist = [k for k in MW_COMP if 0.0 < FRAC_GAS_DES.get(k, 0.0) < 1.0]
    f_d = sum(feed_kmolh.get(k, 0.0) for k in dist)
    if f_d <= 1e-12:
        return dict(FRAC_GAS_DES)                 # no distributing feed: nothing to flash
    z = {k: feed_kmolh.get(k, 0.0) / f_d for k in dist}
    psi_des = sum(z[k] * FRAC_GAS_DES[k] for k in dist)
    if not (1e-9 < psi_des < 1.0 - 1e-9):
        return dict(FRAC_GAS_DES)                 # already single phase: hold the design split

    k_values = {}
    for k in dist:
        phi_d = FRAC_GAS_DES[k]
        k_des = phi_d * (1.0 - psi_des) / (psi_des * (1.0 - phi_d))
        # The 0.0 default is Henry's law — no temperature slope. A distributing species with
        # no listed slope still flashes on pressure rather than raising if the vector is
        # ever edited.
        k_values[k] = max(
            k_des * math.exp((FLASH_DH.get(k, 0.0) / FLASH_R_GAS_J)
                             * (1.0 / FLASH_T0_K - 1.0 / t_k)) * p_rat, 0.0)

    def residual(psi: float) -> float:
        """Rachford-Rice, strictly decreasing in psi."""
        return sum(z[k] * (k_values[k] - 1.0) / (1.0 + psi * (k_values[k] - 1.0))
                   for k in dist)

    lo, hi = 1e-12, 1.0 - 1e-12
    if residual(hi) >= 0.0:
        psi = hi                                  # above the dew point: everything is gas
    elif residual(lo) <= 0.0:
        psi = lo                                  # below the bubble point: everything condenses
    else:
        for _ in range(FLASH_ITERS):
            mid = 0.5 * (lo + hi)
            if residual(mid) > 0.0:
                lo = mid
            else:
                hi = mid
        psi = 0.5 * (lo + hi)

    out = dict(FRAC_GAS_DES)
    for k in dist:
        out[k] = clamp(k_values[k] * psi / (1.0 + psi * (k_values[k] - 1.0)), 0.0, 1.0)
    return out


# ======================================================================================
# The melt bubble pressure
# ======================================================================================

def bubble_p_322e002(t_c: float, nc: float, hc: float,
                     nc_anchor: float = REACTOR_FEED_NC_DES) -> float:
    """Bubble-point pressure of the combined carbamate melt [bar a] — PI-322E002.

    Process utility
    ---------------
    What pressure this melt would sit at if it were left to its own devices. It is TELEMETRY:
    the operator reads it beside the measured loop pressure, and the gap between the two says
    whether the loop is holding the melt down or the melt is holding the loop up. It does not
    enter the pressure target, so it adds no loop.

    Equation
    --------
        P = P_des . exp[(dHvap/R)(1/T_des - 1/T)] . max(fN, 0) . max(fW, 0)
        fN = 1 + K_N (N/C - N/C_anchor)        free-ammonia volatility lift
        fW = 1 + K_W (H/C - H/C_des)           water dilution

    Monotone in all three: dP/dT > 0, dP/d(N/C) > 0, dP/d(H/C) < 0.

    The N/C anchor
    --------------
    The melt is NH3-richer than the reactor FEED, because all the fresh ammonia enters as
    ejector motive and passes through here first. So the fN anchor is the design MELT N/C,
    about 3.123, not the controlled reactor-feed value of 3.073 — and V1 captures the melt
    figure from a settled boot rather than deriving it. Until it is captured, V1 falls back to
    the reactor-feed constant, which is the default here. The H/C anchor stays the reactor's,
    because the melt's H/C settles at exactly that value.

    With the fallback anchor the design indication is 144.35 bar a rather than the 144.2 the
    constant carries — a 0.1 % offset, because the melt at the synthetic design feed is
    marginally NH3-richer than the reactor feed (N/C 3.0786 against 3.0730). Capturing the
    settled melt N/C removes the offset at the SETTLED state instead, which is the state V1
    cares about. Both readings are pinned in the unit test so the choice is visible.
    """
    cc = math.exp((BUB_DHVAP_JMOL / FLASH_R_GAS_J) * (1.0 / FLASH_T0_K - 1.0 / (t_c + 273.15)))
    f_n = 1.0 + BUB_KN * (nc - nc_anchor)
    f_w = 1.0 + BUB_KW * (hc - REACTOR_FEED_HC_DES)
    return P_DES_BARA * cc * max(f_n, 0.0) * max(f_w, 0.0)


# ======================================================================================
# The published result
# ======================================================================================

@dataclass(frozen=True)
class CondenserResult:
    """One evaluation of 322E002, as 322R001, the steam header and the screens read it."""

    # ---- the split ---------------------------------------------------------------------
    #: Gas fraction per component actually applied [-], after the film lag and the gate.
    phi_gas: dict
    #: The film's own state before gating, and the equilibrium target it is relaxing toward.
    phi_film: dict
    phi_eq: dict

    # ---- the streams [kmol/h] -----------------------------------------------------------
    #: Combined tube-side feed: stripper top gas plus ejector discharge.
    feed_kmolh: dict
    #: Two-phase product to 322R001.
    gas_kmolh: dict
    liq_kmolh: dict

    # ---- stream totals -------------------------------------------------------------------
    gas_kgh: float
    liq_kgh: float
    gas_th: float
    liq_th: float
    gas_mol: float
    liq_mol: float
    gas_mw: float
    liq_mw: float
    #: Gas as mole per cent and liquid as mass per cent — each screen's own convention.
    gas_mol_pct: dict
    liq_mass_pct: dict

    # ---- temperatures [deg C] --------------------------------------------------------------
    #: TT-322010, the two-phase outlet.
    t_prod: float
    #: Mass-weighted mix of the two tube-side feeds, before any reaction heat.
    t_feed_mix: float
    #: Adiabatic temperature the exotherm alone would reach.
    t_adb: float

    # ---- duty --------------------------------------------------------------------------
    #: Total process duty released [kW], and the part of it that reaches the shell as steam.
    duty_kw: float
    q_steam_kw: float
    #: LP steam the duty corresponds to [kg/h].
    steam_kgh: float
    #: Total tube-side throughput [kg/h].
    m_dot_kgh: float

    # ---- telemetry -----------------------------------------------------------------------
    #: PI-322E002 melt bubble pressure [bar a], and the two ratios behind it.
    p_bub_bara: float
    melt_nc: float
    melt_hc: float


# ======================================================================================
# The unit
# ======================================================================================

def carbamate_condenser_322e002(gas_feed_kmolh: dict, gas_feed_t_c: float,
                                liq_feed_kgh: dict, liq_feed_t_c: float,
                                t_shell_c: float = STEAM_TSAT_C,
                                gate: float = 1.0,
                                t_prod_prev_c: float = T_PROD_DES_C,
                                p_loop_bara: float = SYN_P_DES_BARA,
                                phi_prev: dict = None,
                                dt: float = 0.0,
                                ua_kjhk=_PINNED,
                                nc_anchor: float = REACTOR_FEED_NC_DES,
                                sat_frac: float = 1.0) -> CondenserResult:
    """Evaluate the HP carbamate condenser for one tick.

    Parameters
    ----------
    gas_feed_kmolh, gas_feed_t_c
        The 322E001 top gas and TT-322013.
    liq_feed_kgh, liq_feed_t_c
        The 322F001 ejector discharge and TT-322012.
    t_shell_c
        Shell saturation temperature, from the live LP header.
    gate
        The Option-1 disturbance factor, 0 at the published operating point and 1 off it.
    t_prod_prev_c
        TT-322010 from the PREVIOUS tick. The split depends on the temperature and the
        temperature depends on the split, so the algebraic loop is torn here — the same
        sequential-modular discipline every other recycle in this flowsheet uses. It is safe
        because the tick is far shorter than the film constant and because the coupling is
        NEGATIVE feedback: T up, K up, phi up, less CO2 absorbed, exotherm down, T down.
    phi_prev, dt
        The film's split from the previous tick and the step. ``dt = 0`` holds the split
        exactly where it was, which is what the boot and the conductance back-calculation need.
    ua_kjhk
        Shell conductance. Omit it to use the design-pinned value; pass ``None`` to hold the
        outlet at its design temperature, which is the state the conductance is derived in.
    nc_anchor
        The melt N/C the bubble pressure is anchored on.
    sat_frac
        The melt's saturation fraction [-] (`liquor_saturation.saturation_fraction`): the share of
        the condensing volatiles it can hold at the loop's pressure, 1 by default.
    """
    # ----- 1. the combined tube-side feed ---------------------------------------------------
    feed = {k: gas_feed_kmolh.get(k, 0.0) + liq_feed_kgh.get(k, 0.0) / MW_COMP[k]
            for k in MW_COMP}

    # ----- 2. the split: equilibrium target, film lag, then the gate -------------------------
    # The flash is the TARGET, not the answer. The film relaxes toward it over the condenser
    # holdup, which makes the split a genuine dynamic state instead of an instantaneous
    # algebraic map. Gated exactly like the temperature below, so a gate of 0 returns the
    # calibration BIT-EXACT and the design balance is untouched.
    phi_eq = hpcc_flash_split(feed, t_prod_prev_c, p_loop_bara)
    base = phi_prev if phi_prev is not None else FRAC_GAS_DES
    a_phi = clamp(dt / (TAU_FILL_MIN * 60.0), 0.0, 1.0)
    phi_film = {k: base.get(k, FRAC_GAS_DES.get(k, 0.0))
                + a_phi * (phi_eq[k] - base.get(k, FRAC_GAS_DES.get(k, 0.0)))
                for k in MW_COMP}
    phi_gas = {k: FRAC_GAS_DES.get(k, 0.0)
               + gate * (phi_film[k] - FRAC_GAS_DES.get(k, 0.0)) for k in MW_COMP}
    if sat_frac < 1.0:
        # Above its bubble point the melt holds only sat_frac of each distributing species' liquid
        # (B-91 (a)); urea and biuret never boil and the permanent gases never condense.
        phi_gas = {k: (1.0 - sat_frac * (1.0 - phi_gas[k])
                       if 0.0 < FRAC_GAS_DES.get(k, 0.0) < 1.0 else phi_gas[k]) for k in MW_COMP}

    gas = {k: feed[k] * phi_gas[k] for k in MW_COMP}
    liq = {k: feed[k] - gas[k] for k in MW_COMP}
    gas_kgh = {k: gas[k] * MW_COMP[k] for k in MW_COMP}
    liq_kgh = {k: liq[k] * MW_COMP[k] for k in MW_COMP}
    gas_n = sum(gas.values())
    liq_n = sum(liq.values())
    gas_m = sum(gas_kgh.values())
    liq_m = sum(liq_kgh.values())

    # ----- 3. shell-side duty and the LP steam it raises ------------------------------------
    # Carbamate exotherm on the NET CO2 absorbed, plus the sensible cooling of the gas.
    #
    # An intended emergent behaviour, and not a defect: the CO2 absorbed is MINIMISED at the
    # design N/C, because the CO2 recycle is smallest at the balanced operating point and
    # moving off it either way sheds more CO2 into the loop. That minimum propagates through
    # the steam header as a positive-feedback V-trough in TT-322010 — less exotherm, less LP
    # steam, more MP-to-LP letdown, a lower MP header, a cooler stripper, a cooler feed here.
    # The vertex is sharp but CONTINUOUS. A coarse N/C sweep makes it look like a 30 C jump;
    # a fine one walks through it. Do not smooth this in the chemistry: the legitimate lever
    # is the steam-header feedback gain.
    co2_absorbed = max(gas_feed_kmolh.get("CO2", 0.0) - gas["CO2"], 0.0)
    q_carb_kw = co2_absorbed * 1000.0 * DH_CARB_KJMOL / 3600.0
    q_sens_kw = gas_m * CP_GAS * max(gas_feed_t_c - T_PROD_DES_C, 0.0) / 3600.0
    duty_kw = q_carb_kw + q_sens_kw
    steam_kgh = duty_kw * 3600.0 / LATENT_4BAR

    # ----- 4. the exotherm spike, then the NTU quench ----------------------------------------
    #     T_adb  = T_feed_mix + q_carb . 3600 / (m_dot . cp)
    #     T_prod = T_shell + (T_adb - T_shell) . exp(-UA / (m_dot . cp))
    #
    # The mixed feed is cold — 155.2 C at design, because the ejector discharge is 107.6 C — and
    # the carbamate exotherm lifts it above the 170 C pin; the shell then quenches it back
    # down. Both q_carb and m_dot scale with throughput, so the spike is INTENSIVE and roughly
    # constant against flow, which keeps the asymptotes physical: flow to zero gives an
    # infinite NTU and full quench to the shell, flow to infinity gives no NTU and the full
    # adiabatic reaction temperature.
    m_gas_in = sum(gas_feed_kmolh.get(k, 0.0) * MW_COMP[k] for k in MW_COMP)
    m_liq_in = sum(liq_feed_kgh.get(k, 0.0) for k in MW_COMP)
    m_dot = m_gas_in + m_liq_in
    t_feed_mix = ((m_gas_in * gas_feed_t_c + m_liq_in * liq_feed_t_c) / m_dot
                  if m_dot > 1e-9 else t_shell_c)
    t_adb = t_feed_mix + q_carb_kw * 3600.0 / max(m_dot * CP_GAS, 1e-9)

    ua = UA_KJHK if ua_kjhk is _PINNED else ua_kjhk
    if ua is None:
        t_prod = T_PROD_DES_C
    else:
        t_prod_live = t_shell_c + (t_adb - t_shell_c) \
            * math.exp(-ua / max(m_dot * CP_GAS, 1e-9))
        # Gate the off-design EXCESS above the design pin, which is what kills the loop-tear
        # self-excitation without suppressing the genuine response.
        t_prod = T_PROD_DES_C + gate * (t_prod_live - T_PROD_DES_C)

    # LP steam actually RAISED on the shell is the process duty MINUS the extra sensible heat
    # carried out in the product above the design pin. At design the two are bit-identical,
    # and it is that shell back-pressure which stabilises the LP header. Floored at zero,
    # which is the full-quench limit.
    q_steam_kw = max(duty_kw - m_dot * CP_GAS * (t_prod - T_PROD_DES_C) / 3600.0, 0.0)

    # ----- 5. the melt bubble pressure, PI-322E002 --------------------------------------------
    # Evaluated at the LIVE melt temperature: a bubble pressure taken at a fixed temperature is
    # not a bubble pressure. Both ratios are clamped to a physical band about design, because
    # they are NH3/CO2 and H2O/CO2 and a CO2-feed cut drives them to infinity on the way
    # through zero.
    co2 = feed.get("CO2", 0.0)
    melt_nc = (clamp(feed.get("NH3", 0.0) / co2,
                     BUB_RATIO_LO_FRAC * REACTOR_FEED_NC_DES,
                     BUB_RATIO_HI_FRAC * REACTOR_FEED_NC_DES)
               if co2 > 1e-9 else REACTOR_FEED_NC_DES)
    melt_hc = (clamp(feed.get("H2O", 0.0) / co2,
                     BUB_RATIO_LO_FRAC * REACTOR_FEED_HC_DES,
                     BUB_RATIO_HI_FRAC * REACTOR_FEED_HC_DES)
               if co2 > 1e-9 else REACTOR_FEED_HC_DES)
    p_bub = bubble_p_322e002(t_prod, melt_nc, melt_hc, nc_anchor)

    return CondenserResult(
        phi_gas=phi_gas, phi_film=phi_film, phi_eq=phi_eq,
        feed_kmolh=feed, gas_kmolh=gas, liq_kmolh=liq,
        gas_kgh=gas_m, liq_kgh=liq_m,
        gas_th=gas_m / 1000.0, liq_th=liq_m / 1000.0,
        gas_mol=gas_n, liq_mol=liq_n,
        gas_mw=(gas_m / gas_n if gas_n else 0.0),
        liq_mw=(liq_m / liq_n if liq_n else 0.0),
        gas_mol_pct={k: (gas[k] / gas_n * 100.0 if gas_n else 0.0) for k in MW_COMP},
        liq_mass_pct={k: (liq_kgh[k] / liq_m * 100.0 if liq_m else 0.0) for k in MW_COMP},
        t_prod=t_prod, t_feed_mix=t_feed_mix, t_adb=t_adb,
        duty_kw=duty_kw, q_steam_kw=q_steam_kw, steam_kgh=steam_kgh, m_dot_kgh=m_dot,
        p_bub_bara=p_bub, melt_nc=melt_nc, melt_hc=melt_hc,
    )


# ======================================================================================
# The design pin
# ======================================================================================
# The shell conductance is the one number in this unit that is back-calculated rather than
# sourced, and it is back-calculated so that the outlet lands on the licensor's 170.0 C at
# the design throughput. Inverting the NTU quench:
#
#     UA = -m_dot . cp . ln[ (T_prod_des - T_shell) / (T_adb - T_shell) ]
#
# Both inputs — the throughput and the adiabatic temperature — are properties of the FEED and
# are independent of UA and of the gate, so the whole thing resolves in one pass here. V1
# reaches the same line through an 18 000-tick settle, but its own comment is explicit that
# the settle is not what the UA expression uses: a SYNTHETIC single call at the reconciled
# design feed is, because the settled attractor has drifted off the reconciled N/C and H/C
# and pinning on it lands the design quench high.
#
# The `ua_kjhk=None` argument is what asks for that pass: it holds the outlet at the design
# pin, which is the only state in which the inversion is well posed.

_SYNTHETIC = carbamate_condenser_322e002(
    TOP_DES_KMOLH, TOP_DES_T_C, _EJECTOR_DES.comp_kgh, _EJECTOR_DES.t_c,
    gate=1.0, ua_kjhk=None)

assert _SYNTHETIC.t_adb > T_PROD_DES_C > STEAM_TSAT_C, \
    "322E002 conductance back-calc is outside its domain: the design feed must arrive " \
    "adiabatically hotter than the design outlet, which must be hotter than the shell"

#: Shell conductance [kJ/h.K], design-pinned. Derived, never entered.
UA_KJHK = -_SYNTHETIC.m_dot_kgh * CP_GAS * math.log(
    (T_PROD_DES_C - STEAM_TSAT_C) / (_SYNTHETIC.t_adb - STEAM_TSAT_C))

#: The design evaluation, with the conductance in place.
DESIGN = carbamate_condenser_322e002(
    TOP_DES_KMOLH, TOP_DES_T_C, _EJECTOR_DES.comp_kgh, _EJECTOR_DES.t_c)

#: Design carbamate make to 322R001 [kg/h] — the liquid the reactor is fed on.
LIQ_DES_KGH = DESIGN.liq_kgh

#: Design tube-side feed [kmol/h]. The reactor's kinetics are calibrated against it, so it is
#: published here rather than recomputed there.
FEED_DES_KMOLH = DESIGN.feed_kmolh


__all__ = [
    "hpcc_flash_split",
    "bubble_p_322e002",
    "CondenserResult",
    "carbamate_condenser_322e002",
    "UA_KJHK",
    "DESIGN",
    "LIQ_DES_KGH",
    "FEED_DES_KMOLH",
]
