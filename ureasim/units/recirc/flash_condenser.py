"""323E011 / 323D011 — the flash condenser and its level tank, on the LP flash gas node.

What this models
----------------
323E011 is a cooling-water condenser on the gas the LP stage of unit 323 flashes off. Its shell
takes the 323F004 flash vapour (PFD 701), the 328D001 reflux-drum vent (786) and the 323D001
vent of the LP carbamate condenser (321), and an ammonia-water wash from 328D003 (791) that
absorbs them as they condense. The condensate falls by gravity into 323D011 beneath it, and
323P008 pumps it out as lean carbamate, PFD 718: 718B to 323E003 on FIC-323418, 718A to 328D001
as the unmetered remainder of LIC-323503's draw. What does not condense leaves through PV-323203
to 323C005, PFD 702.

    701 + 786 + 321 --gas--> 323E011 shell ----PV-323203 (702)----> 323C005
               791 --wash--^      |  gravity, DN 100 N2
                                  v
                               323D011 --323P008--> 718B (FIC-323418) --> 323E003
                                                +-> 718A (the remainder) --> 328D001

The pressure: one gas node, and what sets it
--------------------------------------------
There is no valve between 323F004 and 323E011, nor between 323E011 and 323D011, so the drum,
the vapour line, the condenser shell and the tank are ONE gas space, and PV-323203 on its vent is
the only thing that controls it. The node integrates its moles on the free volume of the
envelope — the condenser shell less its bundle, plus the tank above its liquid (V1 report A-6) —
and, since 2026-10-07, 323F004's own vapour space above its level set point (below):

    dP/dt = (R T / V_v) (n_gen - n_vent) + (P / T) dT/dt - (P / V_v) dV_v/dt       [core.node]

    n_gen  = gen / MW_702,     gen    = G - C(P)
    n_vent = m_702 / MW_702,   m_702  = 440 (phi(h) / phi(21.64)) sqrt( max(P - 1.0, 0) / 0.13 )
    C(P)   = 5589 max(T_dew - 35, 0) / 10,    T_dew = 45 + Tsat(P) - Tsat(1.13)

with G = 701 + 786 + 321 + 3.4 the gas load [kg/h], C the condensation capacity on the node's dew
point against the 35 C cooling-water mean, h the PV-323203 stroke [%] (decided 2026-10-15,
handoff B-30; below) and phi its Neldisc trim (decided 2026-10-17; below). The node settles where
the condenser leaves what the valve passes, G - C(P) = m_702(P): at design G - C = 440 and
h = 21.64 %, so P* = 1.13 bar a. The capacity rises
about 14 100 kg/h per bar about the design, against the vent's 1700 and 323F004's flash, which
takes this pressure one tick later (a lower node flashes more PFD 701), 2800: the condenser
holds the node. A shut vent stands where the condenser takes the whole gas, 1.16 bar a at
design; the gas gone, the node falls only until the dew point meets the water, 0.79 bar a.

The gas envelope's time constant is under a second at design, so the node follows G and h almost
at once. Where the capacity's slope would make the explicit step ring — a full envelope's small
free volume, a long tick — the pressure takes the backward step (`core.node.stable_pressure_step`,
decision 78's class), the vent and the condensation then at the pressure it settles on.

The level tank
--------------
    dM/dt      = (G + 3.4 + m_791) - m_702 - m_718A - m_718B
    M cp dT/dt = sum m_in cp (T_in - T) + m_cond lambda - UA (T - 35)
    m_cond     = max(G + 3.4 - m_702, 0)

Every kilogram not vented lands in the tank as condensate; the pressure balance condenses C(P),
and the two differ only by the gas the node gains or loses, a few kilograms per bar. Each inlet
enters at its producer's live temperature as a departure from the producer's design (B-31,
below); the cooling water stays at its 35 C mean, a utility with no circuit.
LIC-323503 sets the total 718 demand; FIC-323418 meters 718B by volume; 718A is the demand less
718B's SET POINT (a feed-forward, not its measured flow, which rang), through a line lag whose
time constant is the line's inventory over the live flow (V1 report D-8).

No species are carried: the node, the tank and PFD 718 have no composition in V1.

Where this unit departs from V1 — decided 2026-09-27 (handoffs B-32, B-33)
---------------------------------------------------------------------------
Two changes, each decided by the process engineer. Every V1 scenario that keeps the tank above
its heel and the node on its set point runs as V1 runs it.

  * **PIC-323203 runs the DCS gain on its transmitter's span (B-32).** The tuning table's 0.60
    is per cent of output per per cent of PT-323203's 0-1 bar g range, so the loop carries
    60 %/bar where V1 carries 0.60 %/bar. With the node on its set point the error is zero and
    nothing moves; off it, PIC-323203 now holds the node instead of trimming it over hours.
  * **323P008 cannot pump an empty 323D011 (B-33).** The 718B + 718A draw is capped at the
    liquid above a 1 kg heel plus what arrives on the tick, the net of the condenser's inlet
    and the vent:

        m_718A + m_718B <= (M - 1) / dt . 3600 + (m_in - m_702)

    718B, the metered leg, is served first and 718A takes what is left. The loss of suction is
    flagged, FT-323418 reads the flow delivered, and the 718A line carries only what was
    delivered. V1 draws FIC-323418's flow whatever the tank holds and its 1 kg floor makes up
    the difference. The heel keeps that floor out of the pumpable liquid, so it is never
    drained and never restored. The vent, which V1 books against the tank, is not capped: a
    node venting more than everything that arrives still reached the floor on V1's constant
    capacity (handoff B-30).

A sixth, decided 2026-10-15 (handoff B-30, options (b) and (c)): **323E011 condenses on its dew
point, and its vent never runs backwards.** V1 takes the condensation as a constant 5589 kg/h and
generates gas only above it, ``max(G - 5589, 0)``: below it the node has no equilibrium and the
vent law's ``max(P - 1.0, 0.001)`` walks it to the 0.1 bar a floor, and a shut vent has no
ceiling. The port takes 323E003's form (V1's, with its cap at the gas that arrives removed,
handoff B-34) anchored on V1's 5589 kg/h at 1.13 bar a and 45 C against the 35 C water, and the
vent's differential floored at zero (decision 80's class): PV-323203 passes nothing out of a node
at or below the absorber it discharges to. At the design node both are V1's to the bit;
``FlashCondenser(**V1_CONDENSER)`` is V1's, which the equivalence harness keeps.

An eighth, decided 2026-10-17 (decision 23's class): **PV-323203 on Metso's Neldisc**, its printed
capacities as its curve, from the 21.64 % where its sheet passes PFD 702; V1 runs it linear from
25 %. PIC-323203 is seeded there, so the design point is exact on either.

A seventh, decided 2026-10-16 (handoff B-31): **each inlet at its producer's live temperature.**
V1 charges 701 at 106 C, 786 at 61 C, 321 at 74 C and 791 at 56 C whatever 323F004, 328D001,
323E003 and 328D003's compartment II do. The port charges each as its departure from its
producer's design,

    T_in = T_in,des + (T_producer - T_producer,des)

each producer of this tick (323F004, 328D001, 323E003 and 328D003 step before this unit), so at
the design seed every inlet is V1's to the bit and an upstream thermal upset reaches the
condenser's balance. ``live_inlets=False`` is V1's, which the plant-level harness keeps.

A fifth, decided 2026-10-14 (handoff B-93): **AC4 stops 323P008A and B while LT-323503 stands
below its L2**, 5 % (PC23.1.9 / 1.10: the motor blocks' interlock IC2 on "LT-323503:VALUE<L2"; the
value the plant DCS's). As decision 39 builds an interlock, no latch or reset the sheets do not
draw: the pumps deliver nothing below the limit and run again once the level is back above it by
the limit's hysteresis, 2 % (decided 2026-10-15, handoff B-96; a stated stand-in, the database's own
hysteresis not in the archive). V1 has no such trip.

A third, decided 2026-09-30 (handoff B-44): LV-323503 and FV-323418 run their vendor trims,
Valtek's modified equal percentage, from the strokes their Kvs give — 52.86 and 78.45 % — where
V1 runs both linear from 50 %. At their design strokes they pass the design flows either way.

A fourth, decided 2026-10-01 (handoffs B-47, A-16): **the node relieves through SV32357** on
323D011, `core.relief`'s law. V1 relieves nothing, and on its constant capacity a shut PV-323203
runs the node past the valve's 6.01 bar a set pressure with no ceiling (B-30; on the dew point the
condenser now holds a shut vent at 1.16 bar a). The valve is rated on liquid alone, so it
relieves the vapour on its orifice's own area and its orifice's gas coefficient, 0.922, Sempell's
for orifice F in gas service (decision 130); it reseats on the gas blowdown at 5.51 bar a. Like the vent, what it passes is gas
that does not land in the tank as condensate, so it is booked against the tank and does not
condense in the energy balance. Its share of the tank's swell is left out of the pressure step,
so the reseat cap holds exactly; it is a thousandth of the molar term.

328D001's overflow, and the envelope's (decided 2026-10-03, handoff A-15)
--------------------------------------------------------------------------
A full 328D001 overflows up its vent line into the shell (the process engineer's routing). Like
the 791 wash it is liquid, not gas load: it adds to the feed and lands in the tank with its
sensible heat at the drum's temperature, and no latent heat. With LIC-323503's draw saturated the
envelope can then fill, and above its 4.375 m3 of liquid the excess leaves as a published
overflow (decision 11's class); V1, which has neither stream, fills the vapour space to its 2 %
floor. The overflow leaves through PV-323203's vent line, the envelope's only outlet above its
liquid, to 323C005, which takes it into its sump a tick later (decided 2026-10-03, handoff A-20).

A full 323F004 overflows up its vapour line into the shell the same way (decided 2026-10-17,
handoff A-22): liquid, not gas load, landing in the tank with its sensible heat at the drum's
temperature of this tick. V1 has no such stream. The tank carries no composition, so the urea
liquor it brings is booked as liquid mass like the drum overflow's ammonia water.

323F004's vapour space in the node (decided 2026-10-07, handoff B-51)
---------------------------------------------------------------------
V1's node volume is the envelope's alone, although the drum is part of the same gas space. With
the envelope full, its free volume falls to V1's 2 % floor, 0.0875 m3, and the node limit-cycles:
323F004 answers the pressure one tick late, its flash crosses the condenser's constant capacity,
and on so small a volume each tick's generation moves the node a tenth of a bar. The process
engineer decided (the "Typo Rule") that the drum's vapour space is part of the node: 1.083 m3,
its shell above LIC-323505's 60 % set point (`unit_323e011.F004_VAPOUR_M3`), added to the
envelope's free volume as a constant, the floor applying to the envelope alone. The node's
capacitance at the design level rises by a third, 3.14 to 4.22 m3, so its transients are slower
than V1's; at a steady pressure nothing changes. SV32357 relieves the same gas space.

The boundaries this unit reads, and when
----------------------------------------
  * 323F004's flash vapour, less what LV-323505 blows through to 323F010 and plus what
    LV-323501 blows through from 323C003 — all of this tick;
  * 786 and 321, the vents of 328D001 and 323D001, and 791, FIC-323402's wash from 328D003 —
    of this tick, those units stepping before this one in V1's order.

It publishes the node pressure, which 323F004 and 323D001's PV-323202 read at the start of the
next tick; 702 for 323C005, 718A for 328D001 and 718B for 323E003, all read one tick later.

Source
------
V1 ``backend/main.py`` step_sim, "Stage 9 : 323E011 + 323D011" (lines 9580-9663); the
controller seeds in ``State.__init__`` (6831-6835, 6893-6898, 6916-6937, 6981-6990); the
telemetry block (10707-10714); ``backend/c003_pressure_coupling.py``
``e011_vent_generation_kgh``. The design data are in `ureasim.data.unit_323e011`. The node's four
gas relations live in `flash_gas_node` (split 2026-10-16) and are re-exported here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ureasim.control.process_loop import FlowLoop, ProcessLoop
from ureasim.control.valve import cv_fraction
from ureasim.core.node import stable_pressure_step, vapour_volume_m3, vessel_dpdt
from ureasim.core.relief import GasReliefValve, SafetyValve
from ureasim.core.signal import first_order_lag
from ureasim.core.transport import line_residence_time_s
from ureasim.core.units_of_measure import ABSOLUTE_ZERO_C
from ureasim.data.desorption_train import D001_T_C
from ureasim.data.unit_323 import F004_T_SP_C
from ureasim.data.unit_323e003 import E003_T_C
from ureasim.data.unit_328d003 import D003_TII_C
from ureasim.data.unit_323e011 import (
    CP_LP_CARBAMATE,
    D011_LVL_SP_PCT,
    D011_M718_DES_KGH,
    D011_M_DES_KG,
    D011_M_FLOOR_KG,
    LT_323503_L2_HYST_PCT,
    LT_323503_L2_PCT,
    E011_CW_T_C,
    E011_FULL_KG,
    E011_IN_DES_KGH,
    E011_LAMV_KJKG,
    E011_M321_DES_KGH,
    E011_M402_DES_KGH,
    E011_M701_DES_KGH,
    E011_M786_DES_KGH,
    E011_MW_VAP,
    E011_P_BARA,
    E011_P_FLOOR_BARA,
    E011_RECON_KGH,
    E011_RHO_L_KGM3,
    E011_T321_C,
    E011_T701_C,
    E011_T786_C,
    E011_T791_C,
    E011_T_C,
    E011_UA_KW,
    E011_VOL_M3,
    F004_VAPOUR_M3,
    FIC418_OP_DES_PCT,
    FV418_CHAR,
    FIC_323418_KC,
    FIC_323418_SP_HI_M3H,
    FIC_323418_TD_S,
    FIC_323418_TI_S,
    FT_323418_TAU_S,
    LIC_323503_KC,
    LIC_323503_TI_S,
    LV503_CHAR,
    LV503_OP_DES_PCT,
    M718A_LINE_KG,
    M718A_TAU_MAX_S,
    M718B_DES_KGH,
    PIC_323203_KC,
    PIC_323203_SP_HI_BARA,
    PIC_323203_SP_LO_BARA,
    PIC_323203_TD_S,
    PIC_323203_TI_S,
    RHO_718_KGM3,
    SV32357_AREA_M2,
    SV32357_KD,
    SV32357_RESEAT_BARA,
    SV32357_SET_BARA,
    VENT_DP_FLOOR_BAR,
    VENT_DP_MIN_BAR,
)
from ureasim.units.recirc.flash_gas_node import (
    PV_323203_TRIM,
    condensation_capacity_kgh,
    dew_point_c,
    vent_generation_kgh,
    vent_valve_kgh,
)

#: Key the 718A leg's lag is stored under. Source: V1 `main.py`, ``_lag1(s.tlag, "F_718A", ...)``.
LINE_718A_LAG_KEY = "F_718A"

#: Numerical floor on the temperature integration's heat capacity [kJ/K], V1's literal.
HEAT_CAPACITY_FLOOR_KJK = 1e-6

#: Guard on the tick in the pump's heel cap [s], as 323D002's.
DT_FLOOR_S = 1e-9

#: 323E011 as V1 runs it — the constant capacity and the reverse vent — which the equivalence
#: harness keeps (handoff B-30, decided 2026-10-15): ``FlashCondenser(**V1_CONDENSER)``.
V1_CONDENSER = {"dew_capacity": False, "vent_dp_floor_bar": VENT_DP_FLOOR_BAR, "pv_323203": None}


# ======================================================================================
# The three controllers, seeded exactly as V1 seeds them
# ======================================================================================

def pic_323203(op_des_pct: float = PV_323203_TRIM[0]) -> ProcessLoop:
    """PIC-323203, the node pressure. DIRECT acting: a node above set point opens PV-323203.

    Seeded as V1 seeds it, but at PV-323203's vendor design stroke (V1's 25 % is
    ``E011_PV_OP_DES_PCT``) and with the table's gain rescaled to PT-323203's span — 60 %/bar,
    not V1's 0.60 (decided 2026-09-27, handoff B-32)."""
    return ProcessLoop(
        tag="PIC-323203", Kc=PIC_323203_KC, Ti=PIC_323203_TI_S, Td=PIC_323203_TD_S, act=-1.0,
        op=op_des_pct, sp=E011_P_BARA, pv=E011_P_BARA, pv1=E011_P_BARA, pv2=E011_P_BARA,
        op_lo=0.0, op_hi=100.0, sp_lo=PIC_323203_SP_LO_BARA, sp_hi=PIC_323203_SP_HI_BARA)


def lic_323503() -> ProcessLoop:
    """LIC-323503, the 323D011 level. DIRECT acting: a level above set point raises the total
    718 draw demand."""
    return ProcessLoop(
        tag="LIC-323503", Kc=LIC_323503_KC, Ti=LIC_323503_TI_S, Td=0.0, act=-1.0,
        op=LV503_OP_DES_PCT, sp=D011_LVL_SP_PCT, pv=D011_LVL_SP_PCT, pv1=D011_LVL_SP_PCT,
        pv2=D011_LVL_SP_PCT, op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=100.0)


def fic_323418() -> FlowLoop:
    """FIC-323418, the 718B lean-carbamate leg to 323E003 — a VOLUMETRIC loop in m3/h."""
    v = M718B_DES_KGH / RHO_718_KGM3
    loop = ProcessLoop(
        tag="FIC-323418", Kc=FIC_323418_KC, Ti=FIC_323418_TI_S, Td=FIC_323418_TD_S, act=+1.0,
        op=FIC418_OP_DES_PCT, sp=v, pv=v, pv1=v, pv2=v,
        op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=FIC_323418_SP_HI_M3H)
    return FlowLoop(loop=loop, design_flow=M718B_DES_KGH, op_des=FIC418_OP_DES_PCT,
                    tau_s=FT_323418_TAU_S, rho_kgm3=RHO_718_KGM3, characteristic=FV418_CHAR)


def sv_32357() -> GasReliefValve:
    """SV32357, the node's safety valve on 323D011, shut: set 6.01 bar a, reseating at 5.51 on
    the gas blowdown; orifice F, 240.53 mm2, at its orifice's gas coefficient 0.922 and the law's
    exponent 1.30 (decided 2026-10-01, handoff A-16)."""
    return GasReliefValve(valve=SafetyValve("SV32357", SV32357_SET_BARA, SV32357_RESEAT_BARA),
                          area_m2=SV32357_AREA_M2, kd=SV32357_KD)


# ======================================================================================
# The unit
# ======================================================================================

@dataclass(frozen=True)
class FlashCondenserResult:
    """Everything 323E011 / 323D011 publishes on one tick."""

    #: The 323F004 flash vapour the condenser receives — PFD 701 less LV-323505's blow-through
    #: plus LV-323501's [kg/h] — and the condenser's whole inlet, gas and wash [kg/h].
    m_701_kgh: float
    in_kgh: float
    #: PV-323203's stroke [%] and the vent it passes, PFD 702 [kg/h].
    pic_op_pct: float
    m_702_kgh: float
    #: The gas the condenser could not condense, generated into the vapour space [kg/h].
    gen_kgh: float
    #: LT-323503 [%] before the tick — the level LIC-323503 acted on — its output [%], and the
    #: total 718 draw demand it sets [kg/h].
    lic_pv_pct: float
    lic_op_pct: float
    m_718_demand_kgh: float
    #: 718A to 328D001 and 718B to 323E003 [kg/h], as delivered.
    m_718a_kgh: float
    m_718b_kgh: float
    #: True when 323P008 could not deliver the draw and was capped at the tank's heel (B-33).
    suction_lost: bool
    #: The condenser duty to cooling water [kW] and the gas the energy balance condenses [kg/h].
    q_kw: float
    m_cond_kgh: float
    #: What SV32357 vents of the node's vapour to atmosphere [kg/h], and True while it is lifted
    #: (A-16).
    m_relief_kgh: float
    relief_lifted: bool
    #: The liquid above a full envelope, leaving it through PV-323203's vent line to 323C005
    #: [kg/h] (decision 11; handoffs A-15, A-20).
    m_overflow_kgh: float
    #: The state after this tick: the node pressure [bar a], the condensate temperature
    #: (TT-323011) [deg C], the tank holdup [kg] and LT-323503 on it [%].
    p_bara: float
    t_c: float
    m_kg: float
    level_pct: float
    #: True while AC4 holds 323P008A / B stopped on LT-323503's L2 (B-93, decided 2026-10-14).
    p008_tripped: bool = False


@dataclass
class FlashCondenser:
    """323E011 and 323D011 as one object: the gas node, the tank and the step."""

    #: 323D011 holdup [kg], the condensate temperature [deg C], and the temperature on the tick
    #: before — the pressure step's thermal term, a tear, zero at the seed.
    m_kg: float = D011_M_DES_KG
    t_c: float = E011_T_C
    t_prev_c: float = E011_T_C
    #: The node pressure [bar a], shared by 323E011, 323D011 and 323F004.
    p_bara: float = E011_P_BARA
    #: The 718A line lag.
    lag_state: dict = field(default_factory=dict)
    #: The 718B flow delivered on the last tick when 323P008 lost suction [kg/h], which
    #: FT-323418 reads on this one; None while the pump delivers its stroke's flow.
    suction_cap_kgh: float | None = None
    #: LT-323503's L2 [%], below which AC4 stops 323P008A / B (B-93); None, V1's, is no trip.
    l2_pct: float | None = LT_323503_L2_PCT
    #: The limit's hysteresis [% of span] (B-96, a stated stand-in), and the trip as it stands.
    l2_hyst_pct: float = LT_323503_L2_HYST_PCT
    p008_tripped: bool = False
    #: SV32357 and its lift (A-16).
    sv_32357: GasReliefValve = field(default_factory=sv_32357)
    #: 323E011 condensing on its dew point (B-30, decided 2026-10-15); False is V1's constant
    #: 5589 kg/h, which the equivalence harness keeps.
    dew_capacity: bool = True
    #: PV-323203's differential floor [bar]: zero, no reverse vent (B-30); V1's 0.001
    #: (`data.unit_323e011.VENT_DP_FLOOR_BAR`) in the harness.
    vent_dp_floor_bar: float = VENT_DP_MIN_BAR
    #: PV-323203's trim (decided 2026-10-17); None is V1's linear law from 25 %.
    pv_323203: tuple | None = PV_323203_TRIM
    #: Each inlet at its producer's live temperature, as its departure from the producer's design
    #: (decided 2026-10-16, handoff B-31); False is V1's design temperatures.
    live_inlets: bool = True

    def step(self, pic: ProcessLoop, lic: ProcessLoop, fic418: FlowLoop,
             m_701_kgh: float, blow_505_kgh: float, blow_501_kgh: float,
             m_786_kgh: float, m_321_kgh: float, m_402_kgh: float,
             dt: float, *, m_d001_over_kgh: float = 0.0,
             t_d001_over_c: float = E011_T786_C, m_f004_over_kgh: float = 0.0,
             t_f004_c: float = F004_T_SP_C,
             t_e003_c: float = E003_T_C,
             t_d003_ii_c: float = D003_TII_C, pump_running: bool = True) -> FlashCondenserResult:
        """Advance 323E011 / 323D011 by one tick.

        Arguments
        ---------
        m_701_kgh
            323F004's flash vapour on this tick (`FlashTankResult.m_701_kgh`).
        blow_505_kgh, blow_501_kgh
            The drum vapour LV-323505 blows through to 323F010 (`FlashTankResult.
            blowthrough_kgh`), and the column gas LV-323501 blows through into the drum
            (`RectifyingColumnResult.blowthrough_kgh`).
        m_786_kgh, m_321_kgh, m_402_kgh
            The 328D001 vent, the 323D001 vent and FIC-323402's 791 wash.
        m_d001_over_kgh, t_d001_over_c
            The liquid a full 328D001 overflows up its vent line into the shell, and the drum's
            temperature it leaves at (decided 2026-10-03, handoff A-15). Like the 791 wash it is
            liquid, not gas load: it lands in 323D011 with its sensible heat. The drum's
            temperature is also 786's (B-31).
        m_f004_over_kgh
            The liquor a full 323F004 overflows up its vapour line into the shell (decided
            2026-10-17, handoff A-22), at ``t_f004_c``: liquid, like 328D001's overflow.
        t_f004_c, t_e003_c, t_d003_ii_c
            The producers' live temperatures of this tick: 323F004's for 701, 323E003's for 321
            and 328D003's compartment II's for 791 (decided 2026-10-16, handoff B-31). Each
            defaults to its producer's design, so an inlet at design is V1's.
        pump_running
            Either of 323P008A / B running (decision 227). False: nothing is drawn, as AC4's stop on
            LT-323503's L2 draws nothing; the trip's own state is left as it is.

        The order is V1's: the controllers act on the state at the top of the tick; the vent,
        the generation and the draws follow; the pressure steps on the OLD holdup and on the
        temperature change of the tick BEFORE, SV32357 venting what lifts it; the temperature
        and the holdup advance last.
        """
        t_pre = self.t_c
        # ----- the inlet: the flash vapour as it reaches the node, and the whole feed -----
        m_701 = m_701_kgh - blow_505_kgh + blow_501_kgh
        m_in = (E011_IN_DES_KGH + (m_701 - E011_M701_DES_KGH)
                + (m_786_kgh - E011_M786_DES_KGH)
                + (m_321_kgh - E011_M321_DES_KGH)
                + (m_402_kgh - E011_M402_DES_KGH)) + m_d001_over_kgh + m_f004_over_kgh

        # ----- PIC-323203 -> PV-323203, and what the condenser cannot take --------------
        pic_op = pic.step(self.p_bara, dt)
        m_702 = vent_valve_kgh(pic_op, self.p_bara, self.vent_dp_floor_bar, self.pv_323203)
        # The 791 wash is liquid absorbent, not gas load; nor are 328D001's and 323F004's
        # overflows.
        gas = max(m_in - m_402_kgh - m_d001_over_kgh - m_f004_over_kgh, 0.0)
        if self.dew_capacity:
            # The condenser on its dew point, uncapped: below its capacity it draws on the gas
            # the node holds (decided 2026-10-15, handoff B-30; 323E003's form, B-34).
            gen = gas - condensation_capacity_kgh(self.p_bara)
        else:
            gen = vent_generation_kgh(gas)

        # ----- LIC-323503 -> the 718 draw: FIC-323418 on 718B, 718A the remainder --------
        level = self.m_kg / D011_M_DES_KG * D011_LVL_SP_PCT
        lic_op = lic.step(level, dt)
        # LV-323503 on its vendor trim (handoff B-44, decided 2026-09-30).
        m_718_dmd = D011_M718_DES_KGH * (cv_fraction(lic_op / 100.0, LV503_CHAR)
                                         / cv_fraction(LV503_OP_DES_PCT / 100.0, LV503_CHAR))
        m_718b = fic418.step(dt, flow_cap=self.suction_cap_kgh)
        # 718A takes the demand less 718B's SET POINT, not its measured flow: chasing the
        # lagged flow coupled the two legs into a two-tick limit cycle. In MAN the stroke is
        # the operator's, so the flow itself is safe to use.
        if fic418.loop.mode in ("AUTO", "CAS"):
            m_718b_ff = fic418.loop.sp * RHO_718_KGM3
        else:
            m_718b_ff = m_718b
        m_718a_dmd = max(m_718_dmd - m_718b_ff, 0.0)
        # A mixed line of inventory M passing m: tau = M / m, so a half-rate leg lags twice as
        # long (V1 report D-8).
        tau_718a = line_residence_time_s(M718A_LINE_KG, 1.0, m_718a_dmd,
                                         t_max_s=M718A_TAU_MAX_S)
        m_718a = first_order_lag(self.lag_state, LINE_718A_LAG_KEY, m_718a_dmd, tau_718a, dt)
        # AC4 stops 323P008A / B while LT-323503 stands below its L2 (PC23.1.9 / 1.10; decided
        # 2026-10-14, handoff B-93): the motor blocks' interlock, with no latch the sheets do not
        # draw — nothing is drawn, and the pumps run again once the level clears the limit by its
        # hysteresis (B-96, decided 2026-10-15).
        if self.l2_pct is None:
            self.p008_tripped = False
        elif self.p008_tripped:
            self.p008_tripped = level < self.l2_pct + self.l2_hyst_pct
        else:
            self.p008_tripped = level < self.l2_pct
        tripped = self.p008_tripped
        if tripped or not pump_running:
            m_718a = m_718b = 0.0
            self.lag_state[LINE_718A_LAG_KEY] = 0.0
        # 323P008 can deliver only the liquid above the heel plus what arrives on the tick
        # (decided divergence, handoff B-33). The heel keeps the 1 kg floor out of the
        # pumpable liquid, so the floor is never drained and never has to restore it. 718B is
        # served first; the 718A line carries only what was delivered.
        m_718_avail = max(max(self.m_kg - D011_M_FLOOR_KG, 0.0) / max(dt, DT_FLOOR_S) * 3600.0
                          + m_in - m_702, 0.0)
        suction_lost = m_718a + m_718b > m_718_avail
        if suction_lost:
            m_718b = min(m_718b, m_718_avail)
            m_718a = m_718_avail - m_718b
            self.lag_state[LINE_718A_LAG_KEY] = m_718a
        self.suction_cap_kgh = 0.0 if tripped else (m_718b if suction_lost else None)

        # ----- the inlets' sensible heat and the cooling water ------------------------------
        # Each inlet at its producer's live temperature, as its departure from the producer's
        # design: zero at design, so V1's to the bit there (decided 2026-10-16, handoff B-31).
        if self.live_inlets:
            t_701 = E011_T701_C + (t_f004_c - F004_T_SP_C)
            t_786 = E011_T786_C + (t_d001_over_c - D001_T_C)
            t_321 = E011_T321_C + (t_e003_c - E003_T_C)
            t_791 = E011_T791_C + (t_d003_ii_c - D003_TII_C)
        else:
            t_701, t_786, t_321, t_791 = E011_T701_C, E011_T786_C, E011_T321_C, E011_T791_C
        q = E011_UA_KW * (t_pre - E011_CW_T_C)
        sens = (((max(m_701, 0.0) + E011_RECON_KGH) * (t_701 - t_pre)
                 + m_786_kgh * (t_786 - t_pre)
                 + m_321_kgh * (t_321 - t_pre)
                 + m_402_kgh * (t_791 - t_pre)
                 + m_d001_over_kgh * (t_d001_over_c - t_pre)
                 + m_f004_over_kgh * (t_f004_c - t_pre)) / 3600.0 * CP_LP_CARBAMATE)

        # ----- the node: moles on the free volume, on the OLD holdup (V1 report A-6), and
        # 323F004's vapour space, one gas space with it (decided 2026-10-07, handoff B-51) -----
        v_v = vapour_volume_m3(E011_VOL_M3, self.m_kg, E011_RHO_L_KGM3) + F004_VAPOUR_M3

        def tank_net_kgh(m_vent_kgh: float) -> tuple[float, float]:
            """The tank's net inflow and the overflow above a full envelope at a vent [kg/h]: a
            full envelope publishes its excess (decision 11), and the vapour space it would have
            taken is not taken."""
            net = m_in - m_vent_kgh - m_718a - m_718b
            over = max((self.m_kg + net / 3600.0 * dt - E011_FULL_KG)
                       / max(dt, DT_FLOOR_S) * 3600.0, 0.0)
            return net - over, over

        m_net, m_overflow = tank_net_kgh(m_702)
        t_k = self.t_c + ABSOLUTE_ZERO_C
        dtdt = (self.t_c - self.t_prev_c) / dt
        if self.dew_capacity:
            # The capacity's slope on the pressure makes the node stiff: the backward step on a
            # tick where the explicit one would ring (decision 78's class, B-30), the vent and the
            # condensation then at the pressure it settles on.
            def dpdt(p_bara: float) -> float:
                """The node's dP/dt at ``p_bara``, the vent and the condensation with it."""
                return vessel_dpdt(
                    p_bara, t_k, v_v, E011_MW_VAP,
                    (gas - condensation_capacity_kgh(p_bara)) / E011_MW_VAP,
                    vent_valve_kgh(pic_op, p_bara, self.vent_dp_floor_bar,
                                   self.pv_323203) / E011_MW_VAP,
                    dtdt_k_s=dtdt, dvvdt_m3_s=-(m_net / 3600.0) / E011_RHO_L_KGM3)
            p_free, backward = stable_pressure_step(self.p_bara, dt, dpdt, E011_P_FLOOR_BARA)
            if backward:
                m_702 = vent_valve_kgh(pic_op, p_free, self.vent_dp_floor_bar, self.pv_323203)
                gen = gas - condensation_capacity_kgh(p_free)
                m_net, m_overflow = tank_net_kgh(m_702)
        else:
            p_free = self.p_bara + vessel_dpdt(
                self.p_bara, t_k, v_v, E011_MW_VAP, gen / E011_MW_VAP, m_702 / E011_MW_VAP,
                dtdt_k_s=dtdt, dvvdt_m3_s=-(m_net / 3600.0) / E011_RHO_L_KGM3) * dt
        # ----- SV32357: lifted at its set pressure, it vents the node's vapour to atmosphere
        # until the node falls to its reseat pressure (A-16). What it vents, like the vent, is gas
        # that does not land in the tank ----------------------------------------------------
        m_relief = self.sv_32357.vent_kgh(self.p_bara, p_free, t_k, E011_MW_VAP, v_v, dt)
        if m_relief > 0.0:
            p_free += vessel_dpdt(self.p_bara, t_k, v_v, E011_MW_VAP, 0.0,
                                  m_relief / E011_MW_VAP) * dt
            m_net -= m_relief
        self.p_bara = max(p_free, E011_P_FLOOR_BARA)
        self.t_prev_c = t_pre

        # ----- the energy balance: the latent heat of what does not leave as vent or relief --
        m_cond = max(m_in - m_402_kgh - m_d001_over_kgh - m_f004_over_kgh - m_702 - m_relief,
                     0.0)
        p_net = sens + m_cond / 3600.0 * E011_LAMV_KJKG - q

        # ----- TT-323011 and the tank --------------------------------------------------
        # SEMI-IMPLICIT in the inlets and in the cooling water, whose heat-capacity rates are
        # flows or a temperature-driven wall.
        k_cap = ((max(m_701, 0.0) + E011_RECON_KGH + m_786_kgh + m_321_kgh + m_402_kgh
                  + m_d001_over_kgh + m_f004_over_kgh) / 3600.0 * CP_LP_CARBAMATE + E011_UA_KW)
        self.t_c = t_pre + p_net * dt / max(self.m_kg * CP_LP_CARBAMATE + k_cap * dt,
                                            HEAT_CAPACITY_FLOOR_KJK)
        self.m_kg = max(self.m_kg + m_net / 3600.0 * dt, D011_M_FLOOR_KG)

        return FlashCondenserResult(
            m_701_kgh=m_701, in_kgh=m_in, pic_op_pct=pic_op, m_702_kgh=m_702, gen_kgh=gen,
            lic_pv_pct=level, lic_op_pct=lic_op, m_718_demand_kgh=m_718_dmd,
            m_718a_kgh=m_718a, m_718b_kgh=m_718b, suction_lost=suction_lost, q_kw=q,
            m_cond_kgh=m_cond, m_relief_kgh=m_relief, relief_lifted=self.sv_32357.valve.lifted,
            m_overflow_kgh=m_overflow,
            p_bara=self.p_bara, t_c=self.t_c, m_kg=self.m_kg,
            level_pct=self.m_kg / D011_M_DES_KG * D011_LVL_SP_PCT, p008_tripped=tripped,
        )


__all__ = [
    "LINE_718A_LAG_KEY", "HEAT_CAPACITY_FLOOR_KJK", "DT_FLOOR_S", "V1_CONDENSER",
    "vent_generation_kgh", "dew_point_c", "condensation_capacity_kgh", "vent_valve_kgh",
    "pic_323203", "lic_323503", "fic_323418", "sv_32357",
    "FlashCondenserResult", "FlashCondenser",
]
