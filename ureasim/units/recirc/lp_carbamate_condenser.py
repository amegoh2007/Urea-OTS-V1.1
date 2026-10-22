"""323E003 / 323D001 / 323P001 — the LP carbamate condenser, its level tank and the HP carbamate pump.

What this models
----------------
323E003 condenses the 323C003 overhead, PFD 305 (119 C, 4.1 bar a at the column end), into
lean carbamate from 323D011 (718B) and 328D001 (776) and 328D003's ammonia water (734), with the
inert-laden 797 recycle, against a closed tempered-water circuit (PFD 1102 at 55 C in, 1103 at
65 C out). The liquid collects in 323D001 at 74 C and 3.2 bar a, and 323P001 A/B, plunger pumps on
a Voith scoop-tube drive, return it to the HP synthesis, PFD 308. What does not condense leaves through PV-323202 to the
323E011 node, PFD 321.

    305 (323C003) + 797 --gas--> 323E003 shell ---PV-323202 (321)---> 323E011 node
    718B (323D011) + 776 (328D001) + 734 (328D003) --liquid--^     |
                                                   v
                                                323D001 --323P001 (SIC-323901)--> 308 to HP

The gas envelope and what sets its pressure
-------------------------------------------
Stream 305 has no valve on it, so 323C003's vapour space, the 323E003 shell and 323D001 hold
one gas inventory at one pressure; PT-323201 on the column rides above it through the line's
friction head (`rectifying_column.column_pressure_target_bara`). V1 integrates it on the tank's
volume alone, the documented lower bound, as a gas capacitance C = 10.37 kg/bar:

    dP/dt  = (m_env,in - m_env,cond - m_321) / C                                [kg/h / (kg/bar)]
    m_env,in   = 301 + 302 + 797 + (LV-322501 blow-through) - (LV-323501 blow-through)
    m_env,cond = 24 998 . max(T_dew - T_tw, 0) / 14
    T_dew      = 74 + Tsat(P) - Tsat(3.2)                  [water's slope, frozen offset]
    m_321      = 1323 (h / 25) sqrt( max(P - P_E011, 0) / (3.2 - 1.13) )

with T_tw the mean of the tempered-water supply and return. Unlike 323E011's constant capacity,
the dew point gives this node a restoring force: a higher pressure raises the dew point and
condenses more, about 19 300 kg/h per bar at design, against PV-323202's 320. So the node is
held by the condenser and the water, and PIC-323202 is a trim on top of it. With surplus cooling
the condenser draws on the gas the envelope holds, and the node falls until its dew point has
closed on the water far enough for the capacity to meet the load.

The tempered water
------------------
TV-323013A admits cold make-up and TV-323013B bypasses hot return, one stroke and its opposite.
V1 maps the stroke onto a steady-state supply, lags it by 25 s, and closes the duty on the live
water mean; the return then follows from the duty:

    T_sup,ss = clamp( 65 - 10 (h_A / 50), 20, 65 ),   T_sup = lag(T_sup,ss, 25 s)
    Q        = UA (T - (T_sup + T_ret,prev) / 2),     T_ret = T_sup + 10 Q / 14 000

TIC-323013 acts on the supply, not the shell: its PV is PFD 1102.

The level tank and the pump
---------------------------
    dM/dt      = (305 + 718B + 776 + 797 + d734) - m_321 - m_308,   d734 = 734 - 734_des
    M cp dT/dt = sum m_in cp (T_in - T) + m_cond lambda - Q,    m_cond = 305 + 797 - m_321
    m_308      = 36 835 . (n / 59.93),   n = SIC-323901 in CAS on LIC-323502

The mass balance condenses every kilogram not vented and the energy balance charges it, where
the pressure balance condenses the capacity; they agree only at steady state. The gas the
capacity draws from the envelope's own inventory, at most C = 10.37 kg per bar the node falls,
is not credited to the tank. Each inlet enters at its producer's live temperature as a
departure from the producer's design (decided 2026-10-16, handoff B-31, below).

The liquor's composition (decided 2026-10-22, handoff B-105): V1 carries no species through the
node, the tank or PFD 308, so 322E003 washes with PFD 308's design carbamate whatever the LPCC
takes in. Here the tank is stirred and carries NH3, CO2, H2O and urea as its departure from PFD
308, each liquid inlet at its PFD row's composition and the condensate at the gas's closure on PFD
308 (`data.unit_323e003.W_COND`):

    M dd/dt = S - L d,    S = sum_i (m_i - m_i,des) (w_i - w_308),    w_308,live = w_308 + d

L the liquid entering, stepped backward so it holds at a heel. Every inlet at its design leaves d
exactly zero, the design tank PFD 308 to the bit; ``track_species=False`` is V1's.

Where this unit departs from V1 — decided 2026-09-27 and 2026-10-10 (B-32, B-34, B-35, B-37)
------------------------------------------------------------------------------------------
Four changes, each decided by the process engineer. Three are inert at design, and every V1
scenario that keeps the tank above its heel, the capacity inside the gas that arrives and the
node on its set point runs as V1 runs it; the fourth, PFD 734, adds an inlet V1 lacks.

  * **PIC-323202 runs the DCS gain on its transmitter's span (B-32).** The tuning table's 1.00
    and 100 s on PT-323202's 0-5 bar g span, 20 %/bar, where V1 ran 5.0 %/bar with 40 s, which
    no source gives. TIC-323013 runs the table's 1.00 on TT-323013's 0-100 C span, 1.0 %/K, and
    SIC-323901 the table's 1.10 on ST-323901's 0-145 rpm span, carried in rpm on both sides —
    V1's own numbers. With the node on its set point nothing moves; off it, PIC-323202 has four
    times V1's proportional action and 1.6 times its integral action.
  * **323E003 condenses its whole capacity (B-34).** V1 capped the capacity at the gas that
    arrives, `min(capacity, m_env,in)`. Under surplus cooling the cap bound, the node's balance
    was minus the vent alone, PIC-323202 shut PV-323202, and the node stood wherever it was.
    Without the cap the condenser draws the node down on its dew point until the capacity
    meets the load.
  * **PFD 734 enters the condenser (B-37, decided 2026-10-10).** FIC-323401's ammonia water from
    328D003, which V1 books out of the tank into no unit, is a liquid inlet here, at the PFD's
    56 C: Uhde's loop summary names its service "AW to 323E003 LP Carb. Condenser". The PFD's
    323E003 balance closes without it, so it enters as its departure from the PFD's 1534 kg/h
    (decided 2026-10-14, handoff B-94): nothing at design, where the tank holds the PFD's balance
    to the bit, and the whole of FIC-323401's change off it. With ``m_734_kgh`` None the unit is
    V1's.
  * **323P001 cannot pump 323D001 below its heel (B-35).** The draw is capped at the liquid
    above a 1 kg heel plus what arrives on the tick, net of the vent:

        m_308 <= (M - 1) / dt . 3600 + (m_in - m_321)

    and the loss of suction is flagged. V1 guarded the pump only once the tank was ON its floor,
    so the floor made up one tick's overdraw on the tick the tank reached it. The vent, which V1
    books against the tank, is not capped.
  * **Each inlet at its producer's live temperature (B-31, decided 2026-10-16).** V1 charges 305
    at 119 C, 718B at 45 C, 776 at 61 C and 797 at 46 C whatever 323C003, 323E011, 328D001 and
    322C001 do. Each enters here as its departure from its producer's design,
    ``T_in = T_in,des + (T_producer - T_producer,des)``: 323C003's, 328D001's and 322C001's of
    this tick, 323E011's of the tick before (it steps after this unit). At the design seed each
    is V1's to the bit; ``live_inlets=False`` is V1's, which the plant-level harness keeps.

PIC-323202 drives the one vent, as in V1. The functional diagram gives the controller a second,
split-range output, PV-323202B, but the sources disagree on the valve it drives, and the process
engineer kept V1's single vent (2026-09-27).

The boundaries this unit reads, and when
----------------------------------------
  * 323C003's overhead and its two sources, the flash gas and the heater gas, and both
    blow-throughs (LV-322501 into the column, LV-323501 out of it) — all of this tick, the
    column stepping first;
  * 718B from 323D011, last tick's (a tear, seeded with the design flow);
  * 776 from 328D001, this tick's, and the producers' temperatures of B-31: 323C003's,
    328D001's and 322C001's of this tick, 323E011's of the tick before;
  * 734 from 328D003, this tick's, as its departure from the PFD's row (decided 2026-10-10 and
    2026-10-14, B-37 and B-94);
  * the 323E011 node pressure at the start of the tick, which PV-323202 vents against —
    323E011 steps after this unit.

It publishes the 323D001 node pressure, which 323C003 reads at the start of the next tick; 321
for 323E011 on this tick; 308 for the HP scrubber and synthesis on the next.

Source
------
V1 ``backend/main.py`` step_sim, "Stage 8 : 323E003 + 323D001 LPCC" (lines 9513-9578); the
controller seeds in ``State.__init__`` (6887-6948); the telemetry block (10679-10700). The design
data are in `ureasim.data.unit_323e003`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ureasim.control.process_loop import ProcessLoop
from ureasim.core.numeric import clamp
from ureasim.core.signal import first_order_lag
from ureasim.data.unit_323e003 import (
    D001_LVL_SP_PCT,
    D001_M_DES_KG,
    D001_M_FLOOR_KG,
    D001_M_FULL_KG,
    D001_P_BARA,
    D001_P_FLOOR_BARA,
    E003_LAMC_KJKG,
    E003_M308_DES_KGH,
    E003_M321_DES_KGH,
    E003_M718B_DES_KGH,
    E003_M776_DES_KGH,
    E003_M797_DES_KGH,
    E003_M_COND_DES_KGH,
    E003_PV_OP_DES_PCT,
    E003_Q_DES_KW,
    E003_T305_C,
    E003_M734_DES_KGH,
    E003_T718B_C,
    E003_T734_C,
    E003_T776_C,
    E003_T797_C,
    E003_T_C,
    E003_UA_KW,
    ENV_GAS_C_KG_BAR,
    LIC_323502_KC,
    LIC_323502_TI_S,
    P001_RPM_DES,
    PIC_323202_KC,
    PIC_323202_SP_HI_BARA,
    PIC_323202_SP_LO_BARA,
    PIC_323202_TD_S,
    PIC_323202_TI_S,
    SIC_323901_KC,
    SIC_323901_PV_TAU_S,
    SIC_323901_TI_S,
    TIC_323013_KC,
    TIC_323013_SP_HI_C,
    TIC_323013_SP_LO_C,
    TIC_323013_TI_S,
    TSAT_E003_DES_C,
    TV13_DES_PCT,
    TW_RET_T_C,
    TW_SUP_FLOOR_C,
    TW_SUP_T_C,
    TW_T_C,
    TW_TAU_S,
    LIQUOR_SPECIES,
    W_308,
    W_718B,
    W_734,
    W_776,
    W_COND,
)
from ureasim.data.desorption_train import D001_T_C
from ureasim.data.unit_322c001 import C001_T_C
from ureasim.data.unit_323 import C003_T_SP_C
from ureasim.data.unit_323e011 import CP_LP_CARBAMATE, E011_P_BARA, E011_T_C
from ureasim.thermo import iapws

#: Keys the two lags are stored under. Source: V1 `main.py`, ``_lag1(s.tlag, "S_323901", ...)``
#: and ``_lag1(s.tlag, "R3232_TW_SUP", ...)``.
SPEED_LAG_KEY = "S_323901"
TW_SUPPLY_LAG_KEY = "R3232_TW_SUP"

#: Numerical floors, V1's own literals: the TV-323013A design stroke's divisor and the
#: temperature integration's heat capacity [kJ/K].
STROKE_FLOOR_PCT = 1e-6
HEAT_CAPACITY_FLOOR_KJK = 1e-6

#: Guard on the tick in the pump's heel cap [s], as 323D002's and 323D011's.
DT_FLOOR_S = 1e-9


# ======================================================================================
# The relations
# ======================================================================================

def vent_valve_kgh(stroke_pct: float, p_node_bara: float, p_e011_bara: float) -> float:
    """What PV-323202 passes from 323D001 to the 323E011 node [kg/h], PFD 321.

    Process utility
    ---------------
    The coarse lever on the LPCC pressure: it releases the inerts and the equilibrium vapour
    the condenser cannot take. It rides the live differential to 323E011, so it self-limits — a
    pure stroke feed-forward integrated the node to a rail in V1 (PV-323202 at 50 % drove it to
    the 0.1 bar a floor).

    Equation
    --------
        m_321 = 1323 (h / h_des) sqrt( max(P - P_E011, 0) / (3.2 - 1.13) )

    Exactly PFD 321 at the design stroke and the two design pressures; no flow backwards. The trim
    is Fisher's linear Whisper I and h_des its 36.45 %, where its rated Cv passes PFD 321 on its
    normal case (decided 2026-10-22, decision 150); V1 runs the same line from 25 %.

    Source: V1 `main.py` step_sim, ``m_321``; Fisher UD-MR-G00-DZ-0014, item 021.
    """
    dp = max(p_node_bara - p_e011_bara, 0.0)
    return (E003_M321_DES_KGH * (stroke_pct / E003_PV_OP_DES_PCT)
            * math.sqrt(dp / (D001_P_BARA - E011_P_BARA)))


def tempered_water_supply_ss_c(tv_a_stroke_pct: float) -> float:
    """The supply temperature TV-323013A's stroke settles the circuit at [deg C], PFD 1102.

    Process utility
    ---------------
    The split range's lever on the LPCC: TV-323013A opens to cold make-up as TV-323013B closes
    on the hot bypass, so a wider A cools the supply. The design stroke gives exactly the 55 C
    design supply, and the stroke's 0-100 % spans 65 C (all bypass) to 45 C.

    Equation
    --------
        T_sup,ss = clamp( 65 - (65 - 55) (h_A / 50), 20, 65 )

    Source: V1 `main.py` step_sim, ``T_tw_ss``.
    """
    return clamp(TW_RET_T_C - (TW_RET_T_C - TW_SUP_T_C)
                 * (tv_a_stroke_pct / max(TV13_DES_PCT, STROKE_FLOOR_PCT)),
                 TW_SUP_FLOOR_C, TW_RET_T_C)


def dew_point_c(p_node_bara: float) -> float:
    """The envelope's dew point at the node pressure [deg C].

    Process utility
    ---------------
    Where the node's restoring force comes from: more gas raises the pressure, the dew point
    with it, and the driving force to the tempered water. The liquor is not water, so only the
    SLOPE is water's, and the design point is the anchor — the frozen-offset idiom of the
    bubble points of unit 323.

    Equation
    --------
        T_dew = 74 + Tsat(P) - Tsat(3.2)

    Source: V1 `main.py` step_sim, ``T_dew_env``.
    """
    return E003_T_C + (iapws.tsat_c(p_node_bara) - TSAT_E003_DES_C)


def condensation_capacity_kgh(t_dew_c: float, t_tw_mean_c: float) -> float:
    """What 323E003 condenses out of the envelope [kg/h].

    Process utility
    ---------------
    The condenser's side of the node's gas balance, on the dew point against the water: at
    design 24 998 kg/h on the design 14 K. It is zero when the water is at or above the dew
    point. It is not capped at the gas that arrives, as V1 capped it: with surplus cooling the
    condenser draws on the gas the envelope holds (decided 2026-09-27, handoff B-34).

    Equation
    --------
        cap = 24 998 . max(T_dew - T_tw, 0) / (74 - 60)

    Source: V1 `main.py` step_sim, inside ``m_env_cond``.
    """
    return E003_M_COND_DES_KGH * max(t_dew_c - t_tw_mean_c, 0.0) / (E003_T_C - TW_T_C)


# ======================================================================================
# The four controllers
# ======================================================================================

def pic_323202() -> ProcessLoop:
    """PIC-323202, the 323D001 node. DIRECT acting: a node above set point opens PV-323202.

    Seeded as V1 seeds it, but on the tuning table's gain rescaled to PT-323202's span —
    20 %/bar and 100 s, not V1's 5.0 %/bar and 40 s (decided 2026-09-27, handoff B-32)."""
    return ProcessLoop(
        tag="PIC-323202", Kc=PIC_323202_KC, Ti=PIC_323202_TI_S, Td=PIC_323202_TD_S, act=-1.0,
        op=E003_PV_OP_DES_PCT, sp=D001_P_BARA, pv=D001_P_BARA, pv1=D001_P_BARA,
        pv2=D001_P_BARA, op_lo=0.0, op_hi=100.0, sp_lo=PIC_323202_SP_LO_BARA,
        sp_hi=PIC_323202_SP_HI_BARA)


def lic_323502() -> ProcessLoop:
    """LIC-323502, the 323D001 level, master of SIC-323901. DIRECT acting: a level above set
    point asks for more pump speed. Its output is seeded at the design speed. On the plant DCS's
    tuning, 1.2 on SIC-323901's span and 400 s (read back 2026-10-13), not V1's 1.5 rpm per per
    cent and 300 s."""
    return ProcessLoop(
        tag="LIC-323502", Kc=LIC_323502_KC, Ti=LIC_323502_TI_S, Td=0.0, act=-1.0,
        op=P001_RPM_DES, sp=D001_LVL_SP_PCT, pv=D001_LVL_SP_PCT, pv1=D001_LVL_SP_PCT,
        pv2=D001_LVL_SP_PCT, op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=100.0)


def sic_323901() -> ProcessLoop:
    """SIC-323901, 323P001A's speed in rpm, the cascade slave. REVERSE acting."""
    return ProcessLoop(
        tag="SIC-323901", Kc=SIC_323901_KC, Ti=SIC_323901_TI_S, Td=0.0, act=+1.0,
        op=P001_RPM_DES, sp=P001_RPM_DES, pv=P001_RPM_DES, pv1=P001_RPM_DES, pv2=P001_RPM_DES,
        op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=100.0, mode="CAS")


def sic_323902() -> ProcessLoop:
    """SIC-323902, 323P001B's speed: the standby's faceplate, MAN at 0 % and offering no other
    mode. V1 steps it on its own output each tick (``step_sim`` section 33, "stepped for liveness;
    off the network"), so its PV shows what the operator sets and nothing in the plant reads it.
    Tuned as SIC-323901 (V1's dictionary), which in MAN never acts."""
    return ProcessLoop(
        tag="SIC-323902", Kc=SIC_323901_KC, Ti=SIC_323901_TI_S, Td=0.0, act=+1.0,
        op=0.0, sp=0.0, pv=0.0, pv1=0.0, pv2=0.0,
        op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=100.0, mode="MAN")


def tic_323013() -> ProcessLoop:
    """TIC-323013, the tempered-water supply. DIRECT acting: a supply above set point opens
    TV-323013A to cold make-up. Seeded in CAS, as V1 seeds it; no master drives it, so it holds
    its own set point."""
    return ProcessLoop(
        tag="TIC-323013", Kc=TIC_323013_KC, Ti=TIC_323013_TI_S, Td=0.0, act=-1.0,
        op=TV13_DES_PCT, sp=TW_SUP_T_C, pv=TW_SUP_T_C, pv1=TW_SUP_T_C, pv2=TW_SUP_T_C,
        op_lo=0.0, op_hi=100.0, sp_lo=TIC_323013_SP_LO_C, sp_hi=TIC_323013_SP_HI_C,
        mode="CAS")


# ======================================================================================
# The unit
# ======================================================================================

@dataclass(frozen=True)
class LpCarbamateCondenserResult:
    """Everything 323E003 / 323D001 / 323P001 publishes on one tick."""

    #: The condenser's physical inlets, 305 + 718B + 776 + 797 and 734's departure [kg/h].
    in_kgh: float
    #: PV-323202's stroke [%] and the vent it passes to 323E011, PFD 321 [kg/h].
    pic_op_pct: float
    m_321_kgh: float
    #: LI-323502 [%] before the tick — the level LIC-323502 acted on — and its speed demand
    #: [rpm]; SIC-323901's measured speed [rpm] and output [rpm]; PFD 308 as delivered [kg/h].
    lic_pv_pct: float
    lic_op_rpm: float
    speed_pv_rpm: float
    sic_op_rpm: float
    m_308_kgh: float
    #: 323P001 has drawn 323D001 to its heel and delivers less than its speed would.
    suction_lost: bool
    #: The tempered water: TV-323013A's stroke the circuit acted on, last tick's [%]; the
    #: supply it settles at and the supply it has reached [deg C]; TIC-323013's new output
    #: [%]; the duty [kW]; the return (TT-323015) [deg C].
    tv_a_op_pct: float
    tw_supply_ss_c: float
    tw_supply_c: float
    tic_op_pct: float
    q_kw: float
    tw_return_c: float
    #: The gas the energy balance condenses [kg/h].
    m_cond_kgh: float
    #: The envelope: the gas that arrives, the dew point, the condenser's capacity and what it
    #: condenses — the whole capacity, drawing on the envelope's gas when it outruns the gas
    #: that arrives [kg/h], [deg C].
    env_in_kgh: float
    t_dew_c: float
    capacity_kgh: float
    env_cond_kgh: float
    #: The state after this tick: the node (PIC-323202's PV) [bar a], TT-323006 [deg C], the
    #: holdup [kg] and LI-323502 on it [%].
    p_bara: float
    t_c: float
    m_kg: float
    level_pct: float
    #: PFD 308's composition as 323P001 delivers it [mass fractions] (B-105): PFD 308's own row
    #: plus the tank's departure, the row itself at design and in V1.
    w_308: dict = field(default_factory=lambda: dict(W_308))


@dataclass
class LpCarbamateCondenser:
    """323E003, 323D001 and 323P001 as one object: the gas node, the tank and the step."""

    #: 323D001 holdup [kg], the shell liquid temperature [deg C] and the node [bar a].
    m_kg: float = D001_M_DES_KG
    t_c: float = E003_T_C
    p_bara: float = D001_P_BARA
    #: The tempered-water return of the tick before [deg C] — the duty's algebraic-loop tear.
    tw_return_c: float = TW_RET_T_C
    #: The speed transmitter's and the water supply's lags.
    lag_state: dict = field(default_factory=dict)
    #: Each inlet at its producer's live temperature, as its departure from the producer's design
    #: (decided 2026-10-16, handoff B-31); False is V1's design temperatures.
    live_inlets: bool = True
    #: The tank liquor's departure from PFD 308's composition [mass fractions] (handoff B-105).
    dw: dict = field(default_factory=lambda: {k: 0.0 for k in LIQUOR_SPECIES})
    #: The liquor's composition carried through the tank into 308 (decided 2026-10-22, handoff
    #: B-105); False is V1's mass-only LPCC, which the plant-level harnesses keep.
    track_species: bool = True

    def step(self, pic: ProcessLoop, lic: ProcessLoop, sic: ProcessLoop, tic: ProcessLoop,
             m_305_kgh: float, m_flash_gas_kgh: float, m_heater_gas_kgh: float,
             blow_322501_kgh: float, blow_323501_kgh: float,
             m_718b_kgh: float, m_776_kgh: float, p_e011_bara: float,
             dt: float, m_734_kgh: float | None = None, *, t_c003_c: float = C003_T_SP_C,
             t_e011_c: float = E011_T_C, t_d001_c: float = D001_T_C,
             t_c001_c: float = C001_T_C) -> LpCarbamateCondenserResult:
        """Advance 323E003 / 323D001 / 323P001 by one tick.

        Arguments
        ---------
        m_305_kgh, m_flash_gas_kgh, m_heater_gas_kgh
            The 323C003 overhead and its two sources, PFD 301 and 302
            (`RectifyingColumnResult.m_305_kgh`, `.m_flash_gas_kgh`, `.m_heater_gas_kgh`).
        blow_322501_kgh, blow_323501_kgh
            Stripper gas blowing through an uncovered LV-322501 into the column, and column gas
            blowing through an uncovered LV-323501 out of it (`RectifyingColumnResult.
            blowthrough_kgh`).
        m_718b_kgh
            718B from 323D011, LAST tick's (`FlashCondenserResult.m_718b_kgh`), a tear.
        m_776_kgh
            776 from 328D001.
        m_734_kgh
            734, FIC-323401's ammonia water from 328D003 (handoff B-37), entering as its departure
            from PFD 734's 1534 kg/h (B-94); None by default, V1's, which takes no 734.
        p_e011_bara
            The 323E011 node at the start of the tick (`FlashCondenser.p_bara`).
        t_c003_c, t_e011_c, t_d001_c, t_c001_c
            The producers' live temperatures (decided 2026-10-16, handoff B-31): 323C003's for
            305, 323E011's of the tick before for 718B, 328D001's for 776 and 322C001's for 797.
            Each defaults to its producer's design, so an inlet at design is V1's.

        The order is V1's: the controllers act on the state at the top of the tick; the vent,
        the draw and the water follow; the duty closes on the water mean with last tick's
        return; the node steps on the condensation; the temperature and the holdup advance
        last, the draw capped at the tank's heel.
        """
        t_pre = self.t_c
        # PFD 734 as its departure from the PFD's row, which the design inlets already balance:
        # exactly zero at design (B-94), its whole change off it.
        d734 = 0.0 if m_734_kgh is None else m_734_kgh - E003_M734_DES_KGH
        in_kgh = m_305_kgh + m_718b_kgh + m_776_kgh + E003_M797_DES_KGH + d734

        # ----- PIC-323202 -> PV-323202, venting against the 323E011 node --------------------
        pic_op = pic.step(self.p_bara, dt)
        m_321 = vent_valve_kgh(pic_op, self.p_bara, p_e011_bara)

        # ----- LIC-323502 -> SIC-323901 -> 323P001 -----------------------------------------
        level = self.m_kg / D001_M_DES_KG * D001_LVL_SP_PCT
        lic_op = lic.step(level, dt)
        # The speed transmitter reads the scoop tube's last setting through its own lag.
        speed_pv = first_order_lag(self.lag_state, SPEED_LAG_KEY, sic.op,
                                   SIC_323901_PV_TAU_S, dt)
        sic_op = sic.step(speed_pv, dt, lic_op)
        # A plunger pump: the flow is the speed's, whatever the discharge pressure.
        m_308 = E003_M308_DES_KGH * (sic_op / P001_RPM_DES)

        # ----- the tempered water: TV-323013A/B -> the supply -> the duty -> the return -----
        tv_a_op = tic.op
        tw_ss = tempered_water_supply_ss_c(tv_a_op)
        tw_sup = first_order_lag(self.lag_state, TW_SUPPLY_LAG_KEY, tw_ss, TW_TAU_S, dt)
        # TIC-323013's PV is the SUPPLY, not the shell.
        tic_op = tic.step(tw_sup, dt)
        # The duty on the live water mean, with last tick's return — which breaks the loop
        # between the duty and the return it sets.
        q = E003_UA_KW * (t_pre - 0.5 * (tw_sup + self.tw_return_c))
        self.tw_return_c = tw_sup + (TW_RET_T_C - TW_SUP_T_C) * (q / E003_Q_DES_KW)

        # ----- the energy balance: the inlets' sensible heat, the latent heat of what is not
        # vented, the tempered water ---------------------------------------------------------
        m_cond = m_305_kgh + E003_M797_DES_KGH - m_321
        # Each inlet at its producer's live temperature, as its departure from the producer's
        # design: zero at design, so V1's to the bit there (decided 2026-10-16, handoff B-31).
        if self.live_inlets:
            t_305 = E003_T305_C + (t_c003_c - C003_T_SP_C)
            t_718b = E003_T718B_C + (t_e011_c - E011_T_C)
            t_776 = E003_T776_C + (t_d001_c - D001_T_C)
            t_797 = E003_T797_C + (t_c001_c - C001_T_C)
        else:
            t_305, t_718b, t_776, t_797 = E003_T305_C, E003_T718B_C, E003_T776_C, E003_T797_C
        sens = ((m_305_kgh * (t_305 - t_pre)
                 + m_718b_kgh * (t_718b - t_pre)
                 + m_776_kgh * (t_776 - t_pre)
                 + E003_M797_DES_KGH * (t_797 - t_pre)
                 + d734 * (E003_T734_C - t_pre)) / 3600.0 * CP_LP_CARBAMATE)
        p_net = sens + m_cond / 3600.0 * E003_LAMC_KJKG - q

        # ----- the gas envelope: in - condensed - vented -----------------------------------
        # A gas crosses the letdown line in well under a tick, so LV-322501's blow-through
        # arrives with the flash gas, undelayed (V1 report D-20).
        env_in = (m_flash_gas_kgh + m_heater_gas_kgh + E003_M797_DES_KGH + blow_322501_kgh
                  - blow_323501_kgh)
        t_dew = dew_point_c(self.p_bara)
        capacity = condensation_capacity_kgh(t_dew, 0.5 * (tw_sup + self.tw_return_c))
        # The whole capacity, not V1's min(capacity, env_in): a condenser with surplus cooling
        # draws the node down on its dew point (decided 2026-09-27, handoff B-34).
        env_cond = capacity
        self.p_bara = max(self.p_bara + (env_in - env_cond - m_321) / ENV_GAS_C_KG_BAR
                          / 3600.0 * dt, D001_P_FLOOR_BARA)

        # ----- TT-323006 and the tank ------------------------------------------------------
        # SEMI-IMPLICIT in the inlets and in the water, whose duty is a temperature-driven wall.
        k_cap = ((m_305_kgh + m_718b_kgh + m_776_kgh + E003_M797_DES_KGH + d734) / 3600.0
                 * CP_LP_CARBAMATE + E003_UA_KW)
        self.t_c = t_pre + p_net * dt / max(self.m_kg * CP_LP_CARBAMATE + k_cap * dt,
                                            HEAT_CAPACITY_FLOOR_KJK)
        # 323P001 can take the liquid above the 1 kg heel and what arrives on the tick, net of
        # the vent, and no more: it loses suction there (decided 2026-09-27, handoff B-35).
        m_308_avail = max(max(self.m_kg - D001_M_FLOOR_KG, 0.0) / max(dt, DT_FLOOR_S) * 3600.0
                          + in_kgh - m_321, 0.0)
        suction_lost = m_308 > m_308_avail
        if suction_lost:
            m_308 = m_308_avail
        # The liquor's composition (B-105): the stirred tank's departure from PFD 308 on what its
        # inlets bring off their designs, stepped backward on the holdup before the tick.
        if self.track_species:
            gain = dt / 3600.0
            liquid_in = max(in_kgh - m_321, 0.0) * gain
            for k in LIQUOR_SPECIES:
                src = ((m_cond - E003_M_COND_DES_KGH) * (W_COND[k] - W_308[k])
                       + (m_718b_kgh - E003_M718B_DES_KGH) * (W_718B[k] - W_308[k])
                       + (m_776_kgh - E003_M776_DES_KGH) * (W_776[k] - W_308[k])
                       + d734 * (W_734[k] - W_308[k]))
                self.dw[k] = (self.m_kg * self.dw[k] + src * gain) / (self.m_kg + liquid_in)
        self.m_kg = max(self.m_kg + (in_kgh - m_321 - m_308) / 3600.0 * dt, D001_M_FLOOR_KG)

        return LpCarbamateCondenserResult(
            in_kgh=in_kgh, pic_op_pct=pic_op, m_321_kgh=m_321,
            lic_pv_pct=level, lic_op_rpm=lic_op, speed_pv_rpm=speed_pv, sic_op_rpm=sic_op,
            m_308_kgh=m_308, suction_lost=suction_lost, tv_a_op_pct=tv_a_op, tw_supply_ss_c=tw_ss, tw_supply_c=tw_sup,
            tic_op_pct=tic_op, q_kw=q, tw_return_c=self.tw_return_c, m_cond_kgh=m_cond,
            env_in_kgh=env_in, t_dew_c=t_dew, capacity_kgh=capacity, env_cond_kgh=env_cond,
            p_bara=self.p_bara, t_c=self.t_c, m_kg=self.m_kg,
            level_pct=self.m_kg / D001_M_FULL_KG * 100.0,
            w_308={k: W_308[k] + self.dw[k] for k in LIQUOR_SPECIES},
        )


__all__ = [
    "SPEED_LAG_KEY", "TW_SUPPLY_LAG_KEY", "STROKE_FLOOR_PCT", "HEAT_CAPACITY_FLOOR_KJK",
    "DT_FLOOR_S",
    "vent_valve_kgh", "tempered_water_supply_ss_c", "dew_point_c", "condensation_capacity_kgh",
    "pic_323202", "lic_323502", "sic_323901", "tic_323013",
    "LpCarbamateCondenserResult", "LpCarbamateCondenser",
]
