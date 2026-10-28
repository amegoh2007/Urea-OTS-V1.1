"""328D001 and 328E004 — the reflux drum and its condenser, where the desorbers' overhead returns.

What this models
----------------
328C002's overhead, 737 — ammonia, carbon dioxide and water stripped from the process condensate —
is condensed in 328E004 on cooling water, absorbed into the lean carbamate 718A that 323P008 sends
from 323D011 for the purpose, and falls into 328D001. What does not condense leaves the drum's top
as 786 through PV-328202 to 323E011, the LP flash condenser; the liquid is pumped by 328P002 and
split, 775 back to 328C002 as its reflux and 776 forward to 323E003, the LP carbamate condenser.
So this is where the desorption train hands its recovered ammonia and carbon dioxide back to the
LP section: as liquid to 323E003, as vapour to 323E011.

    737 + 718A + 793 --> 328E004 --> 328D001 --786--> PV-328202 --> 323E011
    (+ a full 328C002's overflow)       \\--774--> 328P002 --775--> FV-328404 --> 328C002
                                                          \\--776--> LV-328501 --> 323E003

The drum is one node: liquid holdup, pressure and temperature. It carries no species; its streams
leave on their PFD compositions.

**The condenser.** TIC-328002 holds the drum at 61 C on TV-328002, the cooling-water return, and
328E004's duty is proportional to the water the valve passes (V1's form, on the vendor's trim since
2026-10-17), held to what brings the drum to its 30 C cooling water on the tick (decision 28):

    Q = min(Q_des . phi(op) / phi(55.04),  max(q_sens + q_737 + (T - 30) C / dt, 0))

with C the temperature step's capacity and phi TV-328002's Neldisc curve; V1 has op / 50. The less it condenses, the more of 737 reaches the drum
as vapour:

    gen = m_786,des . (m_737 / m_737,des) / max(Q / Q_des, 0.1)

**The vent.** PIC-328202 reads 328C002's pressure — its transmitter is on the column (V1 AUDIT B5,
the loop summary) — and strokes PV-328202 on the IEC 60534 compressible law from the live drum to
323E011's live pressure of the tick before (decision 29), anchored on 2.6 -> 1.13 bar a, on
786's molar mass (V1 report D-2).

**The pressure** integrates the uncondensed vapour against the vent on the free volume, on the
old holdup and the tick before's temperature change (V1 report A-6):

    dP/dt = (R T / V_v)(gen - m_786) / M_786 + (P / T) dT/dt - (P / V_v) dV_v/dt   [core.node]

**The temperature** balances 737's sensible heat from the live column top, 718A's from 45 C,
793's from compartment II and 328C002's overflow from its bottoms, 737's condensation and
carbamate formation at a back-solved 2163.6 kJ/kg, and 328E004's duty, semi-implicit on the
inlets' capacity:

    M cp dT/dt = cp [m_737 (T_737 - T) + m_718A (45 - T) + m_793 (T_793 - T)
                     + m_over (T_C002 - T)] / 3600 + m_737 lambda_737 / 3600 - Q

**The reflux.** TIC-328008 controls an inferential of 737's water content — 100 . phi .
p_sat,water(T_737) / P_C002, phi back-solved to the PFD's 46.21 mol% — on FIC-328404's set point
(its output in kg/h, V1's); T_737 is 328C002's bottoms less a top offset that moves from 10 K
without reflux to the design 22 K with it, on the reflux lagged over 328C002's residence.

**The draw.** LIC-328501 strokes LV-328501, a pure gain: 776 = 776_des . op / op_des.

**The holdup:** dM/dt = m_737 + m_718A + m_793 + m_over - gen - m_775 - m_776 (decision 24).

Where this unit departs from V1
-------------------------------
Each is inert at the design point, and asserted from both sides in the equivalence tests.

Decided by the process engineer on 2026-09-30 for this unit:

  * **328E004 cannot cool the drum below its cooling water** (decision 28). V1's duty follows
    TV-328002's stroke alone: with 737 lost and TV-328002 held at 50 % its drum passes 30 C in
    66.5 s and absolute zero in 791.5 s. Here the duty is capped at what brings the drum to the
    30 C supply; inert above 30 C.
  * **The vent discharges against 323E011's live pressure** (decision 29), where V1 holds it on
    323E011's design 1.13 bar a — the route by which the drum's vapour reaches the LP section.
    323E011 steps after the drum, so it is the tick before's.
  * **A full 328C002's overflow enters the drum** (decision 30; handoff A-15): what the column
    carries out through its overhead reaches 328E004 and the drum as liquid, at the column's
    bottoms temperature. V1 has no such stream.

Decided on 2026-10-01 (handoffs B-47, A-16):

  * **The drum relieves through SV32353** (decision 32's law, `core.relief`). V1 relieves
    nothing. The valve is rated on liquid alone, so it relieves the head space's vapour on its
    orifice's own area and its orifice's gas coefficient, 0.922 (Sempell's); it lifts at
    6.01 bar a and reseats on the gas blowdown at 5.51. The liquid already paid for the vapour
    (decision 24), so the relief comes out of the head space alone.

Classes decided on other units, applied here under §5 rule 7:

  * **The liquid pays what forms the vapour** (decision 24): V1 takes the vent's flow out of the
    liquid while the pressure integral fills the head space with the uncondensed vapour; here the
    liquid loses the uncondensed vapour and the head space holds the difference.
  * **328P002 cannot drain an empty drum, and a full drum overflows** (decision 11): 775 and 776
    share what the drum can give, FT-328404 reads the 775 delivered, and above the full cylinder
    the excess leaves as a published stream.
  * **The four valves on their vendor trims** (decision 23): LV-328501 linear, Kvs 16, from 29.4 %
    (V1 50 %); FV-328404 modified equal percentage, Kvs 10, from 56.7 % (V1 linear from 30.2 %);
    PV-328202 modified equal percentage, Kvs 25, from 60.4 %, xT 0.7743 (V1 linear from 50 %);
    TV-328002 on Metso's DN 200 Neldisc, its printed capacities as its curve, from 55.04 %, where
    its sheet passes PFD 1028's 408 t/h (decided 2026-10-17; V1 linear from 50 %): 328E004's duty
    and TT-329007 read the trim's water against its design stroke's in place of op / 50.
    ``RefluxDrum(tv_328002=None)`` with TIC-328002 seeded at 50 % is V1's, which the
    equivalence harness keeps.
  * **PIC-328202 and TIC-328002 on the table's gains per cent of span** (decision 10): 25 %/bar on
    PT-328202's 0-10 bar g and 1.875 %/K on TT-328002's 0-160 C, where V1 applies 2.5 and 3.0.

The boundaries this unit reads, and when
----------------------------------------
  * 737, 328C002's overflow, and its pressure, bottoms temperature, holdup and inflow — after its
    step this tick (`FirstDesorberResult`): V1 steps the drum after the three columns;
  * 718A — 323D011's draw on the tick before (V1's tear ``R3232_718A``);
  * 793 and compartment II's temperature — the tank's this tick (V1 AUDIT B2);
  * 323E011's pressure — on the tick before, the vent's outlet.

It publishes 786 to 323E011 and 776 to 323E003, both same-tick in V1's order; 775 and its own
pressure, which 328C002 takes next tick (V1's tears).

Source
------
V1 ``backend/main.py`` step_sim, "Stage 6 : 328D001 Desorber-I reflux drum" (lines 9254-9347),
the cp line (8831), the tear reads (8840-8841) and write (9671); the seeds in ``State.__init__``
(6840-6847, 6993-7025, 7066-7081); the telemetry (10815-10846). The design data are in
`ureasim.data.unit_328d001` and `ureasim.data.desorption_train`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ureasim.control.process_loop import FlowLoop, ProcessLoop
from ureasim.control.valve import cv_fraction, valve_gas_anchored
from ureasim.core.node import vapour_volume_m3, vessel_dpdt
from ureasim.core.relief import GasReliefValve, SafetyValve
from ureasim.core.signal import first_order_lag
from ureasim.core.units_of_measure import ABSOLUTE_ZERO_C
from ureasim.data.desorption_train import (
    C002_P_TOP_BARA,
    CP_DESORPTION,
    D001_P_BARA,
    D001_T_C,
)
from ureasim.data.unit_328c002 import C002_DT_TOP_K
from ureasim.data.unit_328d001 import (
    C002_DT_TOP_NO_REFLUX_K,
    C002_OFFGAS_H2O_DES_MOLPCT,
    C002_OFFGAS_PHI,
    D001_AREA_M2,
    D001_FULL_KG,
    D001_HEAD_VOL_M3,
    D001_LAM737_KJKG,
    D001_LEVEL_DES_PCT,
    D001_M737_DES_KGH,
    D001_M775_DES_KGH,
    D001_M776_DES_KGH,
    D001_M786_DES_KGH,
    D001_M_DES_KG,
    D001_M_FLOOR_KG,
    D001_RHO_KGM3,
    D001_T718A_C,
    D001_VOL_M3,
    E004_COND_FLOOR,
    E004_CW_T_IN_C,
    E004_CW_T_MAX_C,
    E004_CW_T_OUT_DES_C,
    E004_Q_DES_KW,
    E004_TV_OP_DES_PCT,
    LT_328501_SPAN_M,
    LT_328501_TAP_LO_M,
    FIC_328404_KC,
    FIC_328404_SP_HI_M3H,
    FIC_328404_TI_S,
    FT_328404_TAU_S,
    FV404_CHAR,
    FV404_OP_DES_PCT,
    LIC_328501_KC,
    LIC_328501_TD_S,
    LIC_328501_TI_S,
    LV501_OP_DES_PCT,
    MW786_DES,
    PIC_328202_KC,
    PIC_328202_SP_HI_BARA,
    PIC_328202_SP_LO_BARA,
    PIC_328202_TI_S,
    PV202_CHAR,
    PV202_OP_DES_PCT,
    PV202_P2_BARA,
    PV202_XT,
    RHO_775_KGM3,
    SV32353_AREA_M2,
    SV32353_KD,
    SV32353_RESEAT_BARA,
    SV32353_SET_BARA,
    TIC_328002_KC,
    TIC_328002_SP_HI_C,
    TIC_328002_SP_LO_C,
    TIC_328002_TI_S,
    TIC_328008_KC,
    TIC_328008_OP_HI_KGH,
    TIC_328008_SP_HI,
    TIC_328008_SP_LO,
    TIC_328008_TI_S,
    TV_328002_CHAR,
    TV_328002_OP_DES_PCT,
)
from ureasim.thermo import iapws
from ureasim.thermo.empirical import aqueous_cp

#: Floor on the drum pressure [bar a], and on 328C002's pressure in the inferential [bar a]:
#: V1's ``max(..., 0.1)``.
D001_P_FLOOR_BARA = 0.1
C002_P_FLOOR_BARA = 0.1

#: Numerical floors, V1's: the column's inflow in its residence [kg/h], the step in the caps [s],
#: the temperature step's capacity [kJ/K] and TV-328002's stroke in TT-329007 [%].
IN_FLOOR_KGH = 1e-6
DT_FLOOR_S = 1e-9
CAPACITY_FLOOR_KJK = 1e-6
TV_FLOOR_PCT = 1.0

#: The key the column top's reflux lag is kept under (V1's ``R328_775_TOP``).
TOP_LAG_KEY = "R328_775_TOP"

#: TV-328002 as the port runs it, on its vendor's trim: the design stroke [%] and Metso's printed
#: Neldisc curve (decided 2026-10-17, decision 23's class). None is V1's linear law from 50 %.
TV_328002_TRIM = (TV_328002_OP_DES_PCT, TV_328002_CHAR)


# ======================================================================================
# LI-328501: the liquid between LT-328501's taps
# ======================================================================================

def lt_328501_pct(m_kg: float) -> float:
    """LI-328501 [%]: the height of the liquid between LT-328501's taps, on the vessel's true
    volume (decided 2026-09-30, handoff B-53).

    Process utility
    ---------------
    What the board shows and LIC-328501 controls on. The bottom head fills first, below the
    tangent line; above it every m3 lifts the level by 1 / A. A DP cell reads only between its
    taps, so the reading saturates at 0 % below the lower tap, 220 mm above the tangent, and at
    100 % above the upper, 1510 mm higher — a drum running dry or full shows 0 or 100 %, not a
    number past them.

    Equation
    --------
        h  = max(M / rho - V_head, 0) / A                  [m above the bottom tangent]
        LI = clamp((h - 0.220) / 1.510, 0, 1) . 100
    """
    h = max(m_kg / D001_RHO_KGM3 - D001_HEAD_VOL_M3, 0.0) / D001_AREA_M2
    return min(max((h - LT_328501_TAP_LO_M) / LT_328501_SPAN_M, 0.0), 1.0) * 100.0


def _design_holdup_kg() -> float:
    """The design holdup to the last bit [kg]: the float nearest `D001_M_DES_KG` that LI-328501
    reads as its set point exactly.

    Process utility
    ---------------
    The drum is seeded at rest: LIC-328501's set point, PV and history all 50.5 %, so the first
    tick computes du == 0 and the design point holds bit-exact. The taps' reading of the design
    holdup comes back from the geometry one ulp high; stepping the holdup by ulps toward the set
    point finds the float that reads it exactly (one step, 4.5e-13 kg).
    """
    m = D001_M_DES_KG
    for _ in range(64):
        reading = lt_328501_pct(m)
        if reading == D001_LEVEL_DES_PCT:
            return m
        m = math.nextafter(m, -math.inf if reading > D001_LEVEL_DES_PCT else math.inf)
    raise ValueError("no holdup reads LIC-328501's set point exactly")


#: The drum's seed [kg]: the design holdup, reading LIC-328501's 50.5 % exactly.
D001_M_SEED_KG = _design_holdup_kg()


# ======================================================================================
# The five controllers, seeded as V1 seeds them
# ======================================================================================

def pic_328202() -> ProcessLoop:
    """PIC-328202, 328C002's pressure on PV-328202, the drum's vent. DIRECT acting: a column
    above set point opens the vent. On the table's gain per cent of span (decision 10), seeded
    at PV-328202's vendor design stroke (decision 23)."""
    p = C002_P_TOP_BARA
    return ProcessLoop(
        tag="PIC-328202", Kc=PIC_328202_KC, Ti=PIC_328202_TI_S, Td=0.0, act=-1.0,
        op=PV202_OP_DES_PCT, sp=p, pv=p, pv1=p, pv2=p, op_lo=0.0, op_hi=100.0,
        sp_lo=PIC_328202_SP_LO_BARA, sp_hi=PIC_328202_SP_HI_BARA)


def tic_328002(op_des_pct: float = TV_328002_OP_DES_PCT) -> ProcessLoop:
    """TIC-328002, the drum's temperature on TV-328002, 328E004's cooling water. DIRECT acting:
    a warmer drum opens the water. On the table's gain per cent of span (decision 10), seeded at
    TV-328002's vendor design stroke (V1's 50 % is ``E004_TV_OP_DES_PCT``)."""
    t = D001_T_C
    return ProcessLoop(
        tag="TIC-328002", Kc=TIC_328002_KC, Ti=TIC_328002_TI_S, Td=0.0, act=-1.0,
        op=op_des_pct, sp=t, pv=t, pv1=t, pv2=t, op_lo=0.0, op_hi=100.0,
        sp_lo=TIC_328002_SP_LO_C, sp_hi=TIC_328002_SP_HI_C)


def tic_328008() -> ProcessLoop:
    """TIC-328008, the inferential water content of 737 [mol%], on FIC-328404's set point in
    kg/h. DIRECT acting: a wetter overhead asks more reflux. Its faceplate's row in the plant DCS,
    carried onto the mol% PV (decided 2026-10-28, handoff B-116 (b)); V1's 240 and 110 s are the
    harnesses'."""
    h = C002_OFFGAS_H2O_DES_MOLPCT
    return ProcessLoop(
        tag="TIC-328008", Kc=TIC_328008_KC, Ti=TIC_328008_TI_S, Td=0.0, act=-1.0,
        op=D001_M775_DES_KGH, sp=h, pv=h, pv1=h, pv2=h, op_lo=0.0, op_hi=TIC_328008_OP_HI_KGH,
        sp_lo=TIC_328008_SP_LO, sp_hi=TIC_328008_SP_HI)


def fic_328404() -> FlowLoop:
    """FIC-328404, the reflux 775: a VOLUMETRIC loop in m3/h, in CAS under TIC-328008, on V1's
    own tuning; FV-328404 on its vendor trim (decision 23)."""
    v = D001_M775_DES_KGH / RHO_775_KGM3
    loop = ProcessLoop(
        tag="FIC-328404", Kc=FIC_328404_KC, Ti=FIC_328404_TI_S, Td=0.0, act=+1.0, mode="CAS",
        op=FV404_OP_DES_PCT, sp=v, pv=v, pv1=v, pv2=v, op_lo=0.0, op_hi=100.0, sp_lo=0.0,
        sp_hi=FIC_328404_SP_HI_M3H)
    return FlowLoop(loop=loop, design_flow=D001_M775_DES_KGH, op_des=FV404_OP_DES_PCT,
                    tau_s=FT_328404_TAU_S, rho_kgm3=RHO_775_KGM3, characteristic=FV404_CHAR)


def lic_328501() -> ProcessLoop:
    """LIC-328501, the drum's level on LV-328501, 776 to 323E003. DIRECT acting: a level above
    set point opens the draw. Seeded at LV-328501's vendor design stroke (decision 23)."""
    lvl = D001_LEVEL_DES_PCT
    return ProcessLoop(
        tag="LIC-328501", Kc=LIC_328501_KC, Ti=LIC_328501_TI_S, Td=LIC_328501_TD_S, act=-1.0,
        op=LV501_OP_DES_PCT, sp=lvl, pv=lvl, pv1=lvl, pv2=lvl, op_lo=0.0, op_hi=100.0,
        sp_lo=0.0, sp_hi=100.0)


def sv_32353() -> GasReliefValve:
    """SV32353, the drum's safety valve, shut: set 6.01 bar a, reseating at 5.51 on the gas
    blowdown; orifice K, 1462.20 mm2, at its orifice's gas coefficient 0.922 and the law's exponent
    1.30 (decided 2026-10-01, handoff A-16)."""
    return GasReliefValve(valve=SafetyValve("SV32353", SV32353_SET_BARA, SV32353_RESEAT_BARA),
                          area_m2=SV32353_AREA_M2, kd=SV32353_KD)


@dataclass
class RefluxDrumLoops:
    """The five controllers on 328D001 and 328E004, each seeded as V1 seeds it."""

    pic_328202: ProcessLoop = field(default_factory=pic_328202)
    tic_328002: ProcessLoop = field(default_factory=tic_328002)
    tic_328008: ProcessLoop = field(default_factory=tic_328008)
    fic_328404: FlowLoop = field(default_factory=fic_328404)
    lic_328501: ProcessLoop = field(default_factory=lic_328501)


@dataclass(frozen=True)
class RefluxDrumResult:
    """Everything 328D001 publishes on one tick."""

    #: The drum's liquid inflow as V1 books it [kg/h]: 737 + 718A + 793, and 328C002's
    #: overflow.
    in_kgh: float
    #: PIC-328202's output [%] and 786, the vent PV-328202 passes to 323E011 [kg/h].
    pic_op_pct: float
    m_786_kgh: float
    #: TIC-328002's output, TV-328002's stroke [%]; 328E004's duty, held above the cooling water
    #: [kW]; the vapour 328E004 left uncondensed, which the head space takes [kg/h]; TT-329007,
    #: the cooling-water return [deg C].
    tic_op_pct: float
    q_e004_kw: float
    gen_kgh: float
    t_cw_return_c: float
    #: 328C002's top (TT-328008) on the reflux [deg C], TIC-328008's PV, the inferential water
    #: content of 737 [mol%], and its output, FIC-328404's set point [kg/h]; 775, the reflux
    #: FV-328404 passes [kg/h].
    t_737_c: float
    h2o_737_molpct: float
    reflux_sp_kgh: float
    m_775_kgh: float
    #: LI-328501 before the tick [%], LIC-328501's output [%] and 776, what LV-328501 passes to
    #: 323E003 [kg/h]. True when 328P002 was capped at the heel (decision 11).
    lic_pv_pct: float
    lic_op_pct: float
    m_776_kgh: float
    suction_lost: bool
    #: The liquid above the full cylinder [kg/h], zero until the drum is full (decision 11).
    m_overflow_kgh: float
    #: The net heat on the liquid [kW].
    q_net_kw: float
    #: What SV32353 vents of the head space's vapour to atmosphere [kg/h], and True while it is
    #: lifted (A-16).
    m_relief_kgh: float
    relief_lifted: bool
    #: The state after the tick: pressure [bar a], temperature [deg C], holdup [kg], LI-328501
    #: [%].
    p_bara: float
    t_c: float
    m_kg: float
    level_pct: float


@dataclass
class RefluxDrum:
    """328D001 and 328E004 as one node: holdup, pressure, temperature and the step."""

    #: Liquid holdup [kg], temperature [deg C] and the temperature on the tick before — the
    #: pressure step's thermal term, a tear, zero at the seed — and pressure [bar a].
    m_kg: float = D001_M_SEED_KG
    t_c: float = D001_T_C
    t_prev_c: float = D001_T_C
    p_bara: float = D001_P_BARA
    #: 775 on the tick before [kg/h]: what 328C002 took this tick (V1's tear ``R328_775``), which
    #: the column top's lag reads.
    m_775_prev_kgh: float = D001_M775_DES_KGH
    #: The 775 delivered on the last tick the heel capped it, which FT-328404 reads on the next —
    #: None otherwise (decision 11).
    cap_775_kgh: float | None = None
    #: The column top's reflux lag, lazily seeded on its target.
    lag_state: dict = field(default_factory=dict)
    #: SV32353 and its lift (A-16).
    sv_32353: GasReliefValve = field(default_factory=sv_32353)
    #: TV-328002's trim (decided 2026-10-17); None is V1's linear law from 50 %.
    tv_328002: tuple | None = TV_328002_TRIM

    def step(self, loops: RefluxDrumLoops, m_737_kgh: float, t_c002_c: float,
             p_c002_bara: float, m_c002_kg: float, in_c002_kgh: float, m_c002_over_kgh: float,
             m_718a_kgh: float, m_793_kgh: float, t_793_c: float, p_e011_bara: float,
             dt: float) -> RefluxDrumResult:
        """Advance 328D001 and 328E004 by one tick.

        Arguments
        ---------
        m_737_kgh, t_c002_c, p_c002_bara, m_c002_kg, in_c002_kgh
            328C002's overhead, bottoms temperature, pressure, holdup and inflow, after its step
            this tick.
        m_c002_over_kgh
            The liquid a full 328C002 carried out through its overhead this tick, at its bottoms'
            temperature (decision 30).
        m_718a_kgh
            323D011's 718A on the tick before.
        m_793_kgh, t_793_c
            FV-328405's spare ammonia water and compartment II's temperature, the tank's this
            tick.
        p_e011_bara
            323E011's pressure on the tick before, the vent's outlet (decision 29).

        The order is V1's: the vent on PIC-328202; the condenser on TIC-328002; the column top,
        TIC-328008 and the reflux; the level and the draw; the heat, 328E004's duty held above
        the cooling water, and the vapour it leaves uncondensed; the pressure on the OLD holdup
        and the tick before's temperature change, SV32353 venting what lifts it; the
        temperature, semi-implicit; the holdup.
        """
        t_pre = self.t_c
        cp = aqueous_cp(CP_DESORPTION, D001_T_C, t_pre)
        m_in = m_737_kgh + m_718a_kgh + m_793_kgh + m_c002_over_kgh

        # ----- PIC-328202 on 328C002 -> PV-328202, the vent to 323E011's live pressure (V1 report
        # D-2; decision 29) ----------------------------------------------------------------------
        pic_op = loops.pic_328202.step(p_c002_bara, dt)
        m_786 = valve_gas_anchored(
            D001_M786_DES_KGH, pic_op / 100.0, self.p_bara, p_e011_bara,
            t_pre + ABSOLUTE_ZERO_C, PV202_OP_DES_PCT / 100.0, D001_P_BARA, PV202_P2_BARA,
            D001_T_C + ABSOLUTE_ZERO_C, MW786_DES, characteristic=PV202_CHAR, xt=PV202_XT,
            mw_des=MW786_DES)

        # ----- TIC-328002 -> TV-328002: 328E004's duty on the water the trim passes -----------
        tic_op = loops.tic_328002.step(t_pre, dt)
        if self.tv_328002 is None:
            q_e004 = E004_Q_DES_KW * (tic_op / E004_TV_OP_DES_PCT)
        else:
            op_des, trim = self.tv_328002
            phi_des = cv_fraction(op_des / 100.0, trim)
            q_e004 = E004_Q_DES_KW * (cv_fraction(tic_op / 100.0, trim) / phi_des)

        # ----- TIC-328008: the column top answers the reflux over 328C002's residence --------
        tau_c002 = m_c002_kg / max(in_c002_kgh, IN_FLOOR_KGH) * 3600.0
        m_775_top = first_order_lag(self.lag_state, TOP_LAG_KEY, self.m_775_prev_kgh,
                                    tau_c002, dt)
        dt_top = (C002_DT_TOP_NO_REFLUX_K
                  + (C002_DT_TOP_K - C002_DT_TOP_NO_REFLUX_K) * (m_775_top / D001_M775_DES_KGH))
        t_737 = t_c002_c - dt_top
        h2o = (100.0 * C002_OFFGAS_PHI * iapws.psat_bara(t_737)
               / max(p_c002_bara, C002_P_FLOOR_BARA))
        reflux_sp = loops.tic_328008.step(h2o, dt)
        # FT-328404 reads the 775 delivered when the heel held it back (decision 11).
        m_775 = loops.fic_328404.step(dt, cas_sp=reflux_sp, flow_cap=self.cap_775_kgh)

        # ----- LIC-328501 -> LV-328501, a pure gain on its linear trim (decision 23) -----------
        level = lt_328501_pct(self.m_kg)
        lic_op = loops.lic_328501.step(level, dt)
        m_776 = D001_M776_DES_KGH * (lic_op / LV501_OP_DES_PCT)

        # ----- the heat: the inlets' sensible, 737's condensation and formation, 328E004 -------
        m_pre = self.m_kg
        sens = ((m_737_kgh * (t_737 - t_pre) + m_718a_kgh * (D001_T718A_C - t_pre)
                 + m_793_kgh * (t_793_c - t_pre) + m_c002_over_kgh * (t_c002_c - t_pre))
                / 3600.0 * cp)
        latent = m_737_kgh / 3600.0 * D001_LAM737_KJKG
        k_cap = (m_737_kgh + m_718a_kgh + m_793_kgh + m_c002_over_kgh) / 3600.0 * cp
        capacity = max(m_pre * cp + k_cap * dt, CAPACITY_FLOOR_KJK)
        # 328E004 cannot cool the drum below its cooling water (decision 28): its duty is held
        # to what brings the liquid to the 30 C supply this tick. Inert above 30 C.
        q_e004 = min(q_e004, max(sens + latent + (t_pre - E004_CW_T_IN_C) * capacity
                                 / max(dt, DT_FLOOR_S), 0.0))
        q_net = sens + latent - q_e004

        # ----- what 328E004 leaves uncondensed: the less it condenses, the more reaches the drum
        # as vapour -----------------------------------------------------------------------------
        cond = max(q_e004 / E004_Q_DES_KW, E004_COND_FLOOR)
        gen = D001_M786_DES_KGH * (m_737_kgh / D001_M737_DES_KGH) / cond

        # ----- 328P002 draws only the liquid above the heel plus what arrives, net of what stays
        # vapour (decisions 11, 24): 775 and 776 share it. Inert at every normal state. -------
        avail = max(max(self.m_kg - D001_M_FLOOR_KG, 0.0) / max(dt, DT_FLOOR_S) * 3600.0
                    + m_in - gen, 0.0)
        suction_lost = m_775 + m_776 > avail
        self.cap_775_kgh = None
        if suction_lost:
            share = avail / (m_775 + m_776)
            m_775, m_776 = m_775 * share, m_776 * share
            self.cap_775_kgh = m_775

        # ----- the holdup, less what stays vapour (decision 24), and what a full cylinder cannot
        # hold (decision 11) ------------------------------------------------------------------
        m_new = max(m_pre + (m_in - gen - m_775 - m_776) / 3600.0 * dt, D001_M_FLOOR_KG)
        m_overflow = 0.0
        if m_new > D001_FULL_KG:
            m_overflow = (m_new - D001_FULL_KG) / max(dt, DT_FLOOR_S) * 3600.0
            m_new = D001_FULL_KG

        # ----- the pressure: moles on the free volume, on the OLD holdup (V1 report A-6) -------
        v_v = vapour_volume_m3(D001_VOL_M3, m_pre, D001_RHO_KGM3)
        dmdt = (m_in - gen - m_775 - m_776 - m_overflow) / 3600.0
        t_k = t_pre + ABSOLUTE_ZERO_C
        p_free = self.p_bara + vessel_dpdt(
            self.p_bara, t_k, v_v, MW786_DES, gen / MW786_DES, m_786 / MW786_DES,
            dtdt_k_s=(t_pre - self.t_prev_c) / dt, dvvdt_m3_s=-dmdt / D001_RHO_KGM3) * dt
        # ----- SV32353: lifted at its set pressure, it vents the head space's vapour to
        # atmosphere until the drum falls to its reseat pressure (A-16) ---------------------
        m_relief = self.sv_32353.vent_kgh(self.p_bara, p_free, t_k, MW786_DES, v_v, dt)
        if m_relief > 0.0:
            p_free += vessel_dpdt(self.p_bara, t_k, v_v, MW786_DES, 0.0,
                                  m_relief / MW786_DES) * dt
        self.p_bara = max(p_free, D001_P_FLOOR_BARA)
        self.t_prev_c = t_pre

        # ----- the temperature, semi-implicit on the inlets' capacity: 328E004's duty is a stroke,
        # not a UA, so it is not in the capacity (V1) -------------------------------------------
        self.t_c = t_pre + q_net * dt / capacity
        self.m_kg = m_new
        self.m_775_prev_kgh = m_775

        # ----- TT-329007, the cooling-water return: inverse in TV-328002's water (V1's form) ---
        if self.tv_328002 is None:
            rise = E004_TV_OP_DES_PCT / max(tic_op, TV_FLOOR_PCT)
        else:
            rise = phi_des / cv_fraction(max(tic_op, TV_FLOOR_PCT) / 100.0, trim)
        t_cw = min(E004_CW_T_IN_C + (E004_CW_T_OUT_DES_C - E004_CW_T_IN_C) * rise,
                   E004_CW_T_MAX_C)

        return RefluxDrumResult(
            in_kgh=m_in, pic_op_pct=pic_op, m_786_kgh=m_786, tic_op_pct=tic_op,
            q_e004_kw=q_e004, gen_kgh=gen, t_cw_return_c=t_cw, t_737_c=t_737,
            h2o_737_molpct=h2o, reflux_sp_kgh=reflux_sp, m_775_kgh=m_775, lic_pv_pct=level,
            lic_op_pct=lic_op, m_776_kgh=m_776, suction_lost=suction_lost,
            m_overflow_kgh=m_overflow, q_net_kw=q_net, m_relief_kgh=m_relief,
            relief_lifted=self.sv_32353.valve.lifted, p_bara=self.p_bara, t_c=self.t_c,
            m_kg=self.m_kg, level_pct=lt_328501_pct(self.m_kg),
        )


__all__ = [
    "D001_P_FLOOR_BARA", "C002_P_FLOOR_BARA", "IN_FLOOR_KGH", "DT_FLOOR_S", "CAPACITY_FLOOR_KJK",
    "TV_FLOOR_PCT", "TOP_LAG_KEY", "TV_328002_TRIM", "lt_328501_pct", "D001_M_SEED_KG", "pic_328202", "tic_328002",
    "tic_328008", "fic_328404", "lic_328501", "sv_32353", "RefluxDrumLoops", "RefluxDrumResult",
    "RefluxDrum",
]
