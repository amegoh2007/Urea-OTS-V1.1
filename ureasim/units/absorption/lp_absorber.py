"""322C001 — the LP absorber: its pressure, its sump, its heat and its liquor.

What this models
----------------
HV-322604's let-down purge (PFD 204) enters 322C001 at 3.9 bar a and climbs its two packed beds
(`packed_beds`): the lower washed by 755 from 322E006 (`feed_cooler`), the upper by 954 steam
condensate on FT-322404. What the beds take up joins the washes in the sump, with any carbamate
liquor the purge condensed in its letdown line; what they do not take up leaves the top through
PV-322201 to atmosphere (797, `vent_line`). LIC-322502 draws the sump's liquor through LV-322502
to 323C005 (756).

    204 --> beds --797--> PV-322201 --> atmosphere          PIC-322201 on the column
    755 + 954 + uptake --> sump --756--> LV-322502 --> 323C005    LIC-322502 on the sump

**The column has no cooling of its own.** The heat of absorption leaves in the liquor as
sensible heat against 755, which arrives at 322E006's outlet: 40 C at design, warmer as 322E006
loses its cooling water or 744 warms. The liquor runs 3 K above it at design.

**The pressure** integrates the gas the beds do not take up against the vent, on the free volume
above the sump, its molar mass the live vent's (V1 report A-6):

    dP/dt = (R T / V_v)(m_gas - m_abs - m_797) / M_vent + (P/T) dT/dt - (P/V_v) dV_v/dt

    m_797 = m_797,des . phi(h) / phi(h_des)                [PV-322201, a stroke gain]

**The heat**, every term an enthalpy (V1 Phase 5m), semi-implicit in the washes and the gas:

    M cp dT/dt = cp [m_755 (T_755 - T) + m_954 (46 - T) + m_liq (T_gas - T)] / 3600
                 + Q_gas + Q_res
    Q_gas = sum n_i (h_i(T_gas) - h_i(T)) + n_NH3 dH_NH3 + n_CO2 dH_CO2 + n_H2O (h_v - h_l)(T)

the gas brought to the liquor's temperature on the H0 datum, the uptake released at its
differential heats of absorption over the live liquor, the water the vent picks up at its latent
heat; m_liq, the carbamate liquor the purge condensed in its line, brought to the sump's
temperature (its heat of absorption already released in the line); Q_res, the design residual
(a few kW: the PFD's rounded 40 / 43 / 46 C).

**The sump:** dM/dt = m_755 + m_954 + m_liq + m_abs - m_756, m_756 = m_756,des . phi(h) /
phi(h_des); its species a plain multi-feed mix (V1 ``des_advance`` with nothing boiling).

Where this unit departs from V1
-------------------------------
Each is inert at the design point and asserted from both sides in the equivalence tests.

Decided by the process engineer on 2026-10-01:

  * **755 from 322E006** (handoff B-54): its temperature an argument, 322E006's live outlet
    (`feed_cooler`), where V1 holds 40 C.
  * **XV-322915's flood in the vent line** (handoff B-55): V1's 500 kW leaves the liquor's
    balance, and the vent line takes the valve's rated 1000 kg/h of 9.0 bar a steam (B-60); trip
    22.1 reads TI-322015 there (`vent_line`), where V1 heats the liquor with no steam and trips on
    its temperature.
  * **HV-322604's condensate** (handoff B-19): below its dew point the purge reaches the column
    as gas and carbamate liquor (`thermo.condensing_letdown`); the gas climbs the beds, the
    liquor joins the sump. V1's purge is all gas, at its solver's floor.
  * **The column relieves through SV32253** (handoffs B-47, A-16; decision 32's law,
    `core.relief`), certified at 5.0 bar g, 6.013 bar a, where V1 sets it at the vessel's
    30 bar g design pressure and ramps it linearly to 60 t/h. Rated on liquid, it relieves the gas on its orifice M at the series' gas
    coefficient 0.917, taken as an assumption, and reseats on the gas blowdown at 5.513.

Classes decided on other units, applied here under §5 rule 7:

  * **A vessel with its heads, a level between its taps** (decision 33): the name plate's
    3.60 m3 where V1 takes the two cylinders' 3.27; LI-322502 the liquid between LT-322502's
    taps, 200 mm above the bottom tangent and 800 mm apart, where V1 reads M / M_des x 50; the
    design holdup the 506 kg that reads 50 % on them, where V1's is 1392.
  * **The draw cannot empty the sump, and a full column overflows** (decision 11): 756 is held
    to the liquor above a 1 kg heel plus what arrives; above the full column the excess leaves
    as a published stream.
  * **The valves on their vendor trims** (decision 23): PV-322201 modified equal percentage,
    Kvs 63, from 64.5 % (V1 linear from 67.8 %); LV-322502 modified equal percentage, Kvs 100,
    from 54.5 % (V1 linear from 50 %).
  * **PIC-322201 on its transmitter's span** (decision 10): the table's 6.00 per cent of
    PT-322201's 0-28 bar g, 21.43 %/bar, where V1 applies 6.0.

The boundaries this unit reads, and when
----------------------------------------
  * HV-322604's purge — its gas, its liquor, its mass and outlet temperature — of this tick
    (`PurgeValveResult`), V1's ``hv604``;
  * 744, 328D003's draw through 322P002, of this tick, as 755 (V1 aliases them), at 322E006's
    outlet temperature of this tick (`FeedCoolerResult`);
  * FT-322404's 954, the operator's set flow;
  * XV-322915, as I 22.1 left it at the end of the tick before (`vent_line.xv_322915_open`).

It publishes 756 to 323C005 (a tear) and its temperature, which 323C005 reads for 756's, and
TI-322015, trip 22.1's process value (`trip_22_1`).

Source
------
V1 ``backend/main.py`` step_sim, "Stage 7 : 322C001 LP absorber" (9405-9511), the cp line (8834),
``c001_offgas_heat_kw`` (1712-1735), the boot pin (12333-12353), the seeds in ``State.__init__``
(6869-6875, 7129-7148), the telemetry (10848-10875). The design data are in
`ureasim.data.unit_322c001`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache

from ureasim.control.process_loop import ProcessLoop
from ureasim.control.valve import cv_fraction
from ureasim.core.node import vapour_volume_m3, vessel_dpdt
from ureasim.core.relief import GasReliefValve, SafetyValve
from ureasim.core.signal import first_order_lag
from ureasim.core.stream import MW_COMP
from ureasim.core.units_of_measure import ABSOLUTE_ZERO_C
from ureasim.data.unit_322c001 import (
    C001_ABS_CO2_DES_KGH,
    C001_ABS_H2O_DES_KGH,
    C001_ABS_NH3_DES_KGH,
    BED_CP_GAS,
    C001_ALPHA,
    C001_CPL_DES_KGH,
    C001_FULL_KG,
    C001_LEVEL_DES_PCT,
    C001_M755_DES_KGH,
    C001_M756_DES_KGH,
    C001_M_DES_KG,
    C001_M_FLOOR_KG,
    C001_M_SPAN_KG,
    C001_M_TAP_LO_KG,
    C001_MW_VENT_DES,
    C001_P_BARA,
    C001_P_FLOOR_BARA,
    C001_RHO_KGM3,
    C001_T_755_C,
    C001_T_C,
    C001_T_CPL_C,
    C001_VENT_DES_KGH,
    C001_VOL_M3,
    CP_C001,
    LIC_322502_KC,
    LIC_322502_TI_S,
    LV502_CHAR,
    LV502_OP_DES_PCT,
    PIC_322201_KC,
    PIC_322201_SP_HI_BARA,
    PIC_322201_SP_LO_BARA,
    PIC_322201_TI_S,
    PV201_CHAR,
    PV201_OP_DES_PCT,
    SV32253_AREA_M2,
    SV32253_KD,
    SV32253_RESEAT_BARA,
    SV32253_SET_BARA,
    W_C001_DES,
    W_CPL,
    W_S755,
)
from ureasim.data.unit_322e003 import HIC604_DES_PCT, OFFGAS_DES_KMOLH, OFFGAS_T_DES_C
from ureasim.data.unit_322e003 import OVERFLOW_P_DES_BARA
from ureasim.thermo import enthalpy as h0
from ureasim.thermo.ammonia_backpressure import heat_of_absorption_j_mol
from ureasim.thermo.empirical import aqueous_cp
from ureasim.units.absorption import packed_beds as beds
from ureasim.units.absorption.vent_line import (
    FLOOD_STEAM_P_BARA,
    column_top_c,
    sv_purge_steam_kgh,
    vent_line,
)
from ureasim.units.desorption.desorber_stage import advance_species
from ureasim.units.synthesis.purge_valve import purge_valve_322604

#: The keys the upper bed's uptake is lagged under, as the lower bed sees it (V1's tears
#: ``C001_UP_NH3``, ``C001_UP_CO2``, ``C001_UP_DT``).
UP_LAG_KEYS = (("NH3", "C001_UP_NH3"), ("CO2", "C001_UP_CO2"), ("dT", "C001_UP_DT"))

#: Numerical floors, V1's: the temperature step's capacity [kJ/K], the tick in the caps [s], a
#: flow that counts in a fraction [kg/h], and the vent's moles [kmol/h].
CAPACITY_FLOOR_KJK = 1e-6
DT_FLOOR_S = 1e-9
FLOW_FLOOR_KGH = 1e-9
MOLE_FLOOR_KMOLH = 1e-12


# ======================================================================================
# The relations
# ======================================================================================

def offgas_heat_kw(comp_kmolh: dict, t_gas_c: float, t_liq_c: float, absorbed_kmolh: dict,
                   w_liq: dict) -> float:
    """The heat HV-322604's purge puts into 322C001's liquor [kW].

    Process utility
    ---------------
    The absorber's heat load. The gas is brought from its let-down temperature to the liquor's
    on the H0 datum every stream is published on, and what the beds take out of it is released
    there: NH3 and CO2 at their differential heats of absorption over the live liquor (carbamate
    formation included), and the water the vent picks up at its latent heat. On a cooling loss
    upstream the beds take up tonnes an hour, and this is what heats the liquor and caps them.

    Equation in the module docstring; kmol/h x J/mol / 3600 is kW.
    """
    tg, tl = t_gas_c + 273.15, t_liq_c + 273.15
    q = 0.0
    for k, n in comp_kmolh.items():
        if n > 0.0:
            ph = h0.reference_phase(k, "vapour")
            q += n * (h0.h_species(k, ph, tg) - h0.h_species(k, ph, tl))
    dh_n, dh_c = heat_of_absorption_j_mol(w_liq, t_liq_c)
    lat_w = h0.h_species("H2O", "gas", tl) - h0.h_species("H2O", "liquid", tl)
    q += (absorbed_kmolh.get("NH3", 0.0) * dh_n + absorbed_kmolh.get("CO2", 0.0) * dh_c
          + absorbed_kmolh.get("H2O", 0.0) * lat_w)
    return q / 3600.0


def lt_322502_pct(m_kg: float) -> float:
    """LI-322502 [%]: the liquor between LT-322502's taps (rule 7 class, decision 33).

    Process utility
    ---------------
    What the board shows and LIC-322502 holds. The bottom head fills first; above its tangent
    every m3 lifts the level by 1 / A. The DP cell reads only between N9B and N9A, so a sump
    running dry or full reads 0 or 100 %, not a number past them. Both taps stand on the lower
    cylinder, so between them the reading is linear in the liquor:

    Equation
    --------
        h  = (M / rho - V_head) / A                        [m above the bottom tangent]
        LI = clamp((h - 0.200) / 0.800, 0, 1) . 100 = clamp((M - M_lo) / M_span, 0, 1) . 100
        M_lo = rho (V_head + 0.200 A),   M_span = rho . 0.800 A
    """
    return min(max((m_kg - C001_M_TAP_LO_KG) / C001_M_SPAN_KG, 0.0), 1.0) * 100.0


def _design_holdup_kg() -> float:
    """The float nearest `C001_M_DES_KG` that LI-322502 reads as its set point exactly, so the
    sump is seeded at rest and the design point holds to the bit."""
    m = C001_M_DES_KG
    for _ in range(64):
        reading = lt_322502_pct(m)
        if reading == C001_LEVEL_DES_PCT:
            return m
        m = math.nextafter(m, -math.inf if reading > C001_LEVEL_DES_PCT else math.inf)
    raise ValueError("no holdup reads LIC-322502's set point exactly")


#: The sump's seed [kg]: the design holdup, reading LIC-322502's 50 % exactly.
C001_M_SEED_KG = _design_holdup_kg()


@dataclass(frozen=True)
class DesignPin:
    """The design point the beds and the heat balance are pinned on: HV-322604's purge at
    design, the beds' calibration on it, and the heat balance's residual."""

    gas_kmolh: dict
    gas_kgh: float
    t_gas_c: float
    cal: beds.BedCalibration
    q_res_kw: float


@lru_cache(maxsize=1)
def design_pin() -> DesignPin:
    """Pin the absorber on HV-322604's design purge, once (about 4 s).

    Process utility
    ---------------
    V1's boot pin, on the same gas: the first tick of the design seed — 322E003's design vent
    through HV-322604 at its design opening and the design loop pressure, PFD 204. The beds'
    two transfer factors and the vent's water activity are solved so the design uptake is the
    PFD's 204 -> 797 split, and the heat balance's residual so the liquor holds 43 C.
    """
    pv = purge_valve_322604(OFFGAS_DES_KMOLH, OFFGAS_T_DES_C, HIC604_DES_PCT, OVERFLOW_P_DES_BARA)
    comp = {k: v for k, v in pv.comp_kmolh.items() if v > 0.0}
    cal = beds.calibrate(
        comp, C001_T_C, C001_T_CPL_C, C001_P_BARA, C001_M755_DES_KGH, W_S755, C001_CPL_DES_KGH,
        W_C001_DES, {"NH3": C001_ABS_NH3_DES_KGH / MW_COMP["NH3"],
                     "CO2": C001_ABS_CO2_DES_KGH / MW_COMP["CO2"],
                     "H2O": C001_ABS_H2O_DES_KGH / MW_COMP["H2O"]})
    sens = ((C001_M755_DES_KGH * (C001_T_755_C - C001_T_C)
             + C001_CPL_DES_KGH * (C001_T_CPL_C - C001_T_C)) / 3600.0 * CP_C001)
    pin = beds.solve(comp, C001_T_C, C001_T_CPL_C, C001_P_BARA, C001_M755_DES_KGH, W_S755,
                     C001_CPL_DES_KGH, W_C001_DES, cal, abs_up=cal.abs_up)
    q_res = -(sens + offgas_heat_kw(comp, pv.t_out_c, C001_T_C, pin.absorbed_kmolh, W_C001_DES))
    return DesignPin(gas_kmolh=comp, gas_kgh=pv.mass_kgh, t_gas_c=pv.t_out_c, cal=cal,
                     q_res_kw=q_res)


# ======================================================================================
# The controllers and the relief, seeded as V1 seeds them
# ======================================================================================

def pic_322201() -> ProcessLoop:
    """PIC-322201, the column on PV-322201, its vent. DIRECT acting: a column above set point
    opens the vent. On its transmitter's span (decision 10), seeded at the vendor stroke
    (decision 23)."""
    p = C001_P_BARA
    return ProcessLoop(
        tag="PIC-322201", Kc=PIC_322201_KC, Ti=PIC_322201_TI_S, Td=0.0, act=-1.0,
        op=PV201_OP_DES_PCT, sp=p, pv=p, pv1=p, pv2=p, op_lo=0.0, op_hi=100.0,
        sp_lo=PIC_322201_SP_LO_BARA, sp_hi=PIC_322201_SP_HI_BARA)


def lic_322502() -> ProcessLoop:
    """LIC-322502, the sump on LV-322502, 756 to 323C005. DIRECT acting: a level above set point
    opens the draw. Seeded at the vendor stroke (decision 23)."""
    lvl = C001_LEVEL_DES_PCT
    return ProcessLoop(
        tag="LIC-322502", Kc=LIC_322502_KC, Ti=LIC_322502_TI_S, Td=0.0, act=-1.0,
        op=LV502_OP_DES_PCT, sp=lvl, pv=lvl, pv1=lvl, pv2=lvl, op_lo=0.0, op_hi=100.0,
        sp_lo=0.0, sp_hi=100.0)


def sv_32253() -> GasReliefValve:
    """SV32253, the column's safety valve, shut: set 6.013 bar a, reseating at 5.513 on the gas
    blowdown; orifice M, 2827.43 mm2, at the assumed gas coefficient 0.917 and the law's
    exponent 1.30 (decided 2026-10-01, handoffs B-47, A-16)."""
    return GasReliefValve(valve=SafetyValve("SV32253", SV32253_SET_BARA, SV32253_RESEAT_BARA),
                          area_m2=SV32253_AREA_M2, kd=SV32253_KD)


@dataclass
class LpAbsorberLoops:
    """The two controllers on 322C001, each seeded as V1 seeds it."""

    pic_322201: ProcessLoop = field(default_factory=pic_322201)
    lic_322502: ProcessLoop = field(default_factory=lic_322502)


# ======================================================================================
# The unit
# ======================================================================================

@dataclass(frozen=True)
class LpAbsorberResult:
    """Everything 322C001 publishes on one tick."""

    #: HV-322604's purge as gas in [kg/h] and its let-down temperature [deg C]; the carbamate
    #: liquor it condensed in its line, into the sump [kg/h] (B-19); 755's temperature [deg C].
    m_gas_kgh: float
    t_gas_c: float
    m_liquor_kgh: float
    t_755_c: float
    #: PIC-322201's output [%]; LI-322502 before the tick and LIC-322502's output [%].
    pic_op_pct: float
    lic_pv_pct: float
    lic_op_pct: float
    #: 756, what LV-322502 draws to 323C005 [kg/h]; True when the heel held it (decision 11).
    m_756_kgh: float
    drained: bool
    #: What the beds took up [kg/h], per species and in all (water < 0: the vent leaves wetter).
    m_abs_nh3_kgh: float
    m_abs_co2_kgh: float
    m_abs_h2o_kgh: float
    m_abs_kgh: float
    #: The beds' pass: transfer units, the lower bed's equilibrium, the upper bed's rise.
    beds: beds.BedsResult
    #: 797, what PV-322201 vents [kg/h]; its mass fractions and molar mass [kg/kmol].
    m_vent_kgh: float
    y_vent: dict | None
    mw_vent: float
    #: True when the column takes more un-absorbed gas than PV-322201 passes wide open.
    overloaded: bool
    #: What SV32253 vents of the column's gas to atmosphere [kg/h], and True while it is lifted.
    m_relief_kgh: float
    relief_lifted: bool
    #: The liquor above the full column [kg/h], zero until it is full (decision 11).
    m_overflow_kgh: float
    #: The heat [kW]: the washes' and the liquor's sensible, the gas's, and the net.
    q_sens_kw: float
    q_gas_kw: float
    q_net_kw: float
    #: The vent line (B-55): the beds' top [deg C], XV-322915's steam [kg/h], TI-322015 [deg C].
    t_top_c: float
    m_flood_kgh: float
    #: The three restriction orifices' steam off the 9-bar header [kg/h]: FO-329458 and FO-322457
    #: into the vent line, FO-329459 into SV32253's discharge.
    m_trace_kgh: float
    t_ti_322015_c: float
    #: The state after the tick: pressure [bar a], the liquor [deg C], holdup [kg], LI-322502 [%].
    p_bara: float
    t_c: float
    m_kg: float
    level_pct: float


@dataclass
class LpAbsorber:
    """322C001 as one node: holdup, pressure, temperature, liquor and the step."""

    #: Liquor holdup [kg], temperature [deg C] and the temperature on the tick before — the
    #: pressure step's thermal term, a tear, zero at the seed — and pressure [bar a].
    m_kg: float = C001_M_SEED_KG
    t_c: float = C001_T_C
    t_prev_c: float = C001_T_C
    p_bara: float = C001_P_BARA
    #: The liquor's mass fractions, PFD 756 at the seed.
    w: dict = field(default_factory=lambda: dict(W_C001_DES))
    #: The upper bed's uptake as the lower bed sees it, lagged over its liquid residence.
    lag_state: dict = field(default_factory=dict)
    #: SV32253 and its lift.
    sv_32253: GasReliefValve = field(default_factory=sv_32253)

    def step(self, loops: LpAbsorberLoops, gas_kmolh: dict, m_gas_kgh: float, t_gas_c: float,
             m_755_kgh: float, t_755_c: float, m_cpl_kgh: float, xv_322915_open: bool,
             dt: float, liquor_kmolh: dict | None = None,
             p_9_bara: float = FLOOD_STEAM_P_BARA) -> LpAbsorberResult:
        """Advance 322C001 by one tick.

        Arguments
        ---------
        gas_kmolh, m_gas_kgh, t_gas_c
            HV-322604's purge this tick as gas: per species [kmol/h], in all [kg/h], and its
            let-down temperature [deg C] (`PurgeValveResult.vapour_kmolh`).
        m_755_kgh, t_755_c
            744, 328D003's draw through 322P002, this tick, and 322E006's outlet temperature.
        m_cpl_kgh
            954, FT-322404's set flow.
        xv_322915_open
            XV-322915, as I 22.1 left it at the end of the tick before.
        liquor_kmolh
            The carbamate liquor HV-322604's purge condensed in its line [kmol/h], at
            ``t_gas_c`` (`PurgeValveResult.liquor_kmolh`); None or empty above its dew point.
        p_9_bara
            329D009's header, which XV-322915's flood draws from (handoff B-73); its default the
            header's design.

        The order is V1's: the two controllers; the beds and their coupling's lag; the vent and
        the relief; the pressure on the OLD holdup and the tick before's temperature change;
        the heat, semi-implicit; the holdup; the liquor.
        """
        pin = design_pin()
        t_pre = self.t_c
        cp = aqueous_cp(CP_C001, C001_T_C, t_pre)

        # ----- PIC-322201 and LIC-322502 -> PV-322201 and LV-322502 on their vendor trims ------
        pic_op = loops.pic_322201.step(self.p_bara, dt)
        level = lt_322502_pct(self.m_kg)
        lic_op = loops.lic_322502.step(level, dt)
        m_756 = C001_M756_DES_KGH * (cv_fraction(lic_op / 100.0, LV502_CHAR)
                                     / cv_fraction(LV502_OP_DES_PCT / 100.0, LV502_CHAR))
        # HV-322604's condensate (B-19): it joins the sump, not the beds.
        liq_i = {k: max((liquor_kmolh or {}).get(k, 0.0), 0.0) * MW_COMP[k] for k in MW_COMP}
        m_liq = sum(liq_i.values())

        # ----- the beds: one pass against the upper bed's uptake as the lower bed sees it, one
        # liquid residence late ------------------------------------------------------------------
        up_in = {sp: self.lag_state.get(key, pin.cal.abs_up[sp]) for sp, key in UP_LAG_KEYS}
        ab = beds.solve({k: max(v, 0.0) for k, v in gas_kmolh.items()}, t_pre, C001_T_CPL_C,
                        self.p_bara, m_755_kgh, W_S755, m_cpl_kgh, self.w, pin.cal, abs_up=up_in)
        tau_up = beds.liquid_residence_s(beds.BED_UP, m_cpl_kgh, C001_T_CPL_C + 273.15)
        for sp, key in UP_LAG_KEYS:
            first_order_lag(self.lag_state, key, ab.abs_up[sp], tau_up, dt)
        abs_nh3 = ab.absorbed_kmolh.get("NH3", 0.0) * MW_COMP["NH3"]
        abs_co2 = ab.absorbed_kmolh.get("CO2", 0.0) * MW_COMP["CO2"]
        abs_h2o = ab.absorbed_kmolh.get("H2O", 0.0) * MW_COMP["H2O"]      # < 0: leaves wetter
        m_abs = abs_nh3 + abs_co2 + abs_h2o

        # ----- PV-322201's vent; overload: more un-absorbed gas than it passes wide open ------
        phi_des = cv_fraction(PV201_OP_DES_PCT / 100.0, PV201_CHAR)
        m_vent = C001_VENT_DES_KGH * (cv_fraction(pic_op / 100.0, PV201_CHAR) / phi_des)
        overloaded = (m_gas_kgh - m_abs) > C001_VENT_DES_KGH * (cv_fraction(1.0, PV201_CHAR)
                                                                / phi_des)
        # The vent's composition: the purge less the uptake, as mass fractions, and its molar
        # mass — the live one: on a cooling loss upstream it is ammonia, not air.
        vent_i = {k: gas_kmolh.get(k, 0.0) * MW_COMP[k] for k in MW_COMP}
        vent_i["CO2"] -= abs_co2
        vent_i["NH3"] -= abs_nh3
        vent_i["H2O"] -= abs_h2o
        v_tot = sum(v for v in vent_i.values() if v > 0.0)
        y_vent = ({k: max(vent_i[k], 0.0) / v_tot for k in MW_COMP}
                  if v_tot > FLOW_FLOOR_KGH else None)
        n_vent = sum(max(vent_i.get(k, 0.0), 0.0) / MW_COMP[k] for k in MW_COMP)
        mw_vent = (v_tot / n_vent if (v_tot > FLOW_FLOOR_KGH and n_vent > MOLE_FLOOR_KMOLH)
                   else C001_MW_VENT_DES)

        # ----- the vent line: the beds' top, XV-322915's steam, TI-322015 (B-55) -------------
        t_top = column_top_c(ab, gas_kmolh, m_cpl_kgh, C001_T_CPL_C, t_pre)
        line = vent_line(m_vent, y_vent, t_top, xv_322915_open, p_9_bara)

        # ----- LV-322502 cannot draw the sump below its heel (decision 11) --------------------
        m_in = m_755_kgh + m_cpl_kgh + m_liq + m_abs
        avail = max(max(self.m_kg - C001_M_FLOOR_KG, 0.0) / max(dt, DT_FLOOR_S) * 3600.0 + m_in,
                    0.0)
        drained = m_756 > avail
        if drained:
            m_756 = avail
        # ----- the holdup, and what a full column cannot hold (decision 11) -------------------
        m_pre = self.m_kg
        m_new = max(m_pre + (m_in - m_756) / 3600.0 * dt, C001_M_FLOOR_KG)
        m_overflow = 0.0
        if m_new > C001_FULL_KG:
            m_overflow = (m_new - C001_FULL_KG) / max(dt, DT_FLOOR_S) * 3600.0
            m_new = C001_FULL_KG

        # ----- the pressure: moles on the free volume, on the OLD holdup (V1 report A-6) -------
        v_v = vapour_volume_m3(C001_VOL_M3, m_pre, C001_RHO_KGM3)
        t_k = t_pre + ABSOLUTE_ZERO_C
        p_free = self.p_bara + vessel_dpdt(
            self.p_bara, t_k, v_v, mw_vent, (m_gas_kgh - m_abs) / mw_vent, m_vent / mw_vent,
            dtdt_k_s=(t_pre - self.t_prev_c) / dt,
            dvvdt_m3_s=-((m_in - m_756 - m_overflow) / 3600.0) / C001_RHO_KGM3) * dt
        # ----- SV32253: lifted at its set pressure, it vents the column's gas to atmosphere
        # until the column falls to its reseat pressure (B-47, A-16) ------------------------
        m_relief = self.sv_32253.vent_kgh(self.p_bara, p_free, t_k, mw_vent, v_v, dt)
        if m_relief > 0.0:
            p_free += vessel_dpdt(self.p_bara, t_k, v_v, mw_vent, 0.0, m_relief / mw_vent) * dt
        self.p_bara = max(p_free, C001_P_FLOOR_BARA)
        self.t_prev_c = t_pre

        # ----- the heat, every term an enthalpy; semi-implicit in the washes and the gas ------
        sens = ((m_755_kgh * (t_755_c - t_pre) + m_cpl_kgh * (C001_T_CPL_C - t_pre)
                 + m_liq * (t_gas_c - t_pre)) / 3600.0 * cp)
        q_gas = offgas_heat_kw({k: max(v, 0.0) for k, v in gas_kmolh.items()}, t_gas_c, t_pre,
                               ab.absorbed_kmolh, self.w)
        q_net = sens + q_gas + pin.q_res_kw
        k_cap = ((m_755_kgh + m_cpl_kgh + m_liq) * cp + m_gas_kgh * BED_CP_GAS) / 3600.0
        self.t_c = t_pre + q_net * dt / max(m_pre * cp + k_cap * dt, CAPACITY_FLOOR_KJK)
        self.m_kg = m_new

        # ----- the liquor: 755, 954, the purge's condensate and the uptake in, 756 and any
        # overflow out, nothing boils ------------------------------------------------------
        w_abs = {sp: (m / m_abs if m_abs > FLOW_FLOOR_KGH else 0.0)
                 for sp, m in (("CO2", abs_co2), ("NH3", abs_nh3), ("H2O", abs_h2o))}
        feeds = [(W_S755, m_755_kgh), (W_CPL, m_cpl_kgh), (w_abs, m_abs)]
        if m_liq > FLOW_FLOOR_KGH:
            feeds.append(({k: v / m_liq for k, v in liq_i.items() if v > 0.0}, m_liq))
        self.w, _ = advance_species(self.w, self.m_kg, feeds, 0.0, C001_ALPHA,
                                    m_756 + m_overflow, 0.0, dt)

        return LpAbsorberResult(
            m_gas_kgh=m_gas_kgh, t_gas_c=t_gas_c, m_liquor_kgh=m_liq, t_755_c=t_755_c,
            pic_op_pct=pic_op, lic_pv_pct=level,
            lic_op_pct=lic_op, m_756_kgh=m_756, drained=drained, m_abs_nh3_kgh=abs_nh3,
            m_abs_co2_kgh=abs_co2, m_abs_h2o_kgh=abs_h2o, m_abs_kgh=m_abs, beds=ab,
            m_vent_kgh=m_vent, y_vent=y_vent, mw_vent=mw_vent, overloaded=overloaded,
            m_relief_kgh=m_relief, relief_lifted=self.sv_32253.valve.lifted,
            m_overflow_kgh=m_overflow, q_sens_kw=sens, q_gas_kw=q_gas, q_net_kw=q_net,
            t_top_c=line.t_top_c, m_flood_kgh=line.m_steam_kgh,
            m_trace_kgh=line.m_trace_kgh + sv_purge_steam_kgh(p_9_bara),
            t_ti_322015_c=line.t_ti_322015_c, p_bara=self.p_bara, t_c=self.t_c, m_kg=self.m_kg,
            level_pct=lt_322502_pct(self.m_kg),
        )


__all__ = [
    "UP_LAG_KEYS", "CAPACITY_FLOOR_KJK", "DT_FLOOR_S", "FLOW_FLOOR_KGH", "MOLE_FLOOR_KMOLH",
    "offgas_heat_kw", "lt_322502_pct", "C001_M_SEED_KG", "DesignPin", "design_pin",
    "pic_322201", "lic_322502", "sv_32253", "LpAbsorberLoops", "LpAbsorberResult", "LpAbsorber",
]
