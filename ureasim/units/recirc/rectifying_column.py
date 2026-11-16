"""323C003 and 323E002 — the rectifying column and its steam heater, stage 1 of unit 323.

What this models
----------------
The stripper bottoms arrive from 322E001 through LV-322501, let down from 144 to 4.1 bar a.
Across that valve about a fifth of the liquor flashes, and the gas it releases is the first of
the column's two gas sources. The liquid falls through the packed bed into the bottom, where
the 323E002 heater — shell-side LP steam, tube-side liquor — decomposes the remaining
carbamate; the gas it raises is the second source. Both leave overhead as PFD 305 to the LP
carbamate condenser 323E003. The bottoms, at 135 C and 68.7 % urea, drain through LV-323501
to the 323F004 flash tank.

    TIC-323007 (column T)  ->  PIC-329202 (323E002 chest P)  ->  PV-329202 (LP steam)
    LIC-323501 (column level)  ->  LV-323501 (drain to 323F004)

The column is a well-mixed liquid holdup with a mass, an energy and a species balance, and a
gas space whose pressure PT-323201 follows its two gas sources:

    dM/dt   = m_feed - m_305 - m_314
    M cp dT/dt = q_flash + Q_E002 - m_305 . lambda_305
    d(M w)/dt  = the species balance of `units.liquor_stage`
    dP/dt   = (P_target - P) / tau_P

The pressure has TWO sources, and they are kept apart
------------------------------------------------------
PT-323201 is charged by two physically distinct carbamate gases, which the PFD tabulates
separately at the 4.1 bar a column pressure:

  * **stream 301, from the HP stripper.** The 322E001 bottoms flash as they let down across
    LV-322501. How much flashes is set by how much sensible heat the liquor brings down from
    the stripper: the feed rate times cp times the fall from TT-322004 (the stripper bottom)
    to TT-323001 (after the letdown). A hotter stripper, or more bottoms, charges the column
    harder. This term reads the LIVE TT-322004 (decided 2026-09-26, As-Built §XXVIII.6); V1 read a
    constant 172.0 C through a store-key typo.
  * **stream 302, from the 323E002 heater.** The steam duty, less what the liquor needs to
    reach its bubble point, boils gas off the column bottoms. Pinch PV-329202 and this source
    collapses while the letdown keeps charging the column through the other. The liquor
    circulates through the heater, so with the steam shut the column's OWN pool still flashes
    off whatever it holds above its bubble point, and that gas leaves by the same path (V1
    names the term ``m_pool_vap``). Nothing from 323F004 enters here: the flash tank's vapour
    is PFD 701, and it goes to the 323E011 flash condenser.

Each source is carried as its OWN ratio to its own design rate, and the pressure law weights
them by the PFD's own design volumes, 5064.7 and 2875.7 m3/h:

    Q_equiv  = Q301 . (m_flash / m_flash,des) + Q302 . (m_heater / m_heater,des)
    P_target = sqrt( P_d001^2 + (Q_equiv / C)^2 )

Neither is inferred from the other, and stream 305 — the column's OUTLET, 3.3 % smaller than
301 + 302 because some gas condenses on the bed — is deliberately not used as a driver: it
would make the total feed back on itself. At design both ratios are exactly 1.0 and the
target is exactly 4.1 bar a against the 3.2 bar a downstream node.

The stripper's blow-through and the relief (decided 2026-10-03, handoff A-16)
-----------------------------------------------------------------------------
When the stripper's bottom seal is lost, LV-322501 passes HP stripper gas with the bottoms
(`StripperSumpResult.blowthrough_kgh`). It enters the column's head space with the letdown
flash, so it is a third load on the same line, by its own volume at the head space's state:

    Q_equiv  = Q301 . r_301 + Q302 . r_302 + m_blow / rho_blow(P, T)      [rho ideal gas]

V1 sends that gas straight to 323E003 and its column never sees it: the column cannot reach
the 6.01 bar a its safety valves are set at (2.54 times the design flash gas would). The two
valves, SV32351 and SV32352, sized on exactly this case, read PT-323201 at the top of the tick;
lifted, they relieve the head space's gas — at most what it receives this tick, since the law
holds no gas inventory to draw down — until the pressure falls to their 5.51 bar a reseat. The
law reads only the gas left after the relief, and what is left leaves overhead to 323E003:
every overhead flow is carried on `RectifyingColumnResult.overhead_frac`, exactly 1.0 when the
valves are shut.

LI-323501 reads the holdup **between LT-323501's taps**, N8 and the outlet line 2000 mm below it,
on the column's neck, cone and shell (`data.unit_323c003.lt_323501_pct`; decision 241, handoff
B-156): V1's design holdup reads the plant's 40 %, LIC-323501's set point, and LV-323501's seal is
lost at N5's bottom edge, 29.21 %. ``V1_COLUMN`` and ``lic_323501(taps=False)`` are V1's
M / M_full with the seal at the bottom of the span.

Source
------
V1 ``backend/main.py`` step_sim, "Stage 1: Rectifying Column 323C003 + Recirc Heater 323E002"
(lines 8219-8409), and V1 ``backend/c003_pressure_coupling.py`` (``c003_pressure_target_bara``);
reports F-2 (energy-limited boil-up), TD-014 (the bubble-point relaxation), A-5 (the steam
chest), D-1 (the IEC letdown), F-8 / TD-009 (the species layer) and the D-19..D-21 seal guards.
The design data are in `ureasim.data.unit_323`, each with its source.

The decided divergences from V1
-------------------------------
* The flash term's upstream temperature is the live TT-322004 instead of V1's constant 172.0 C.
  At the design state the sump publishes exactly 172.0, so the design point, the column's
  calibration and the Phase 7 steady-state comparison are all unchanged; the column now
  responds to how hot the stripper actually runs.
* The 323E002 chest is anchored on its datasheet's 3.9 bar a, not V1's 3.96 (2026-09-30); the
  valve's design stroke and the conductance are re-derived on it by V1's own expressions.
* TIC-323007 and PIC-329202 read the DCS table's gains per cent of their transmitters' spans
  (2026-09-30), and PIC-329202 drops the chest-gain scale V1 multiplied it by.
* LV-323501 is placed on its vendor trim (2026-09-30, handoff B-44): a linear Valtek trim, as
  V1 has it, but at the 56.65 % its Kvs gives for the design drain instead of V1's 50 %, and
  on its sheet's FL, 0.9319, instead of the IEC 0.90.
* The stripper's blow-through loads PT-323201 and SV32351 / SV32352 relieve it (2026-10-03,
  handoff A-16). With no blow-through and the valves shut — every V1 scenario below 6.01 bar a —
  the column runs as V1's.

The As-Built reference records each decision and the equivalence test asserts both sides.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ureasim.control.process_loop import ProcessLoop
from ureasim.control.valve import valve_liquid_anchored
from ureasim.core.numeric import clamp
from ureasim.core.packet import normalise_solution_mass_fraction
from ureasim.core.relief import (
    GasReliefValve,
    SafetyValve,
    psv_api520_choked_kgh,
    psv_area_from_rated_m2,
)
from ureasim.core.signal import first_order_lag
from ureasim.core.stream import MW_COMP
from ureasim.core.units_of_measure import ABSOLUTE_ZERO_C
from ureasim.data.design_point import R323_M314_DES, R323_PHI_V305
from ureasim.data.control_valves import PV_329202
from ureasim.data.unit_323c003 import LT_323501_DES_PCT, LT_323501_SEAL_PCT, lt_323501_pct
from ureasim.data.unit_323 import (
    C003_LIQUOR,
    C003_LVL_SP_PCT,
    C003_M_DES_KG,
    C003_M_FLOOR_KG,
    C003_M_FULL_KG,
    C003_M_TAU_S,
    C003_P_BARA,
    C003_P_MAX_BARA,
    C003_P_MIN_BARA,
    C003_P_TAU_S,
    C003_T313_C,
    C003_T_SP_C,
    CP_C003_DES,
    CP_S208_DES,
    E002_OP_DES_PCT,
    PV_329202_OP_DES_PCT,
    PV_329202_XT,
    E002_PCHEST_DES_BARA,
    E002_Q_DES_KW,
    E002_UA_KW,
    F004_P_BARA,
    GAS_LOAD_COEFF_M3H_PER_BAR,
    LAMBDA_305_KJKG,
    LIC_323501_KC,
    LIC_323501_TI_S,
    LV501_CHAR,
    LV501_FL,
    LV501_OP_DES_PCT,
    LV501_PV_DES_BARA,
    M305_DES_KGH,
    M_FLASH_GAS_DES_KGH,
    M_POOL_VAP_DES_KGH,
    PIC_329202_KC,
    PIC_329202_TI_S,
    Q301_DES_M3H,
    Q302_DES_M3H,
    Q305_DES_KW,
    RHO_C003_DES,
    RHO_S314,
    TIC_323007_KC,
    TIC_323007_SP_HI_C,
    TIC_323007_SP_LO_C,
    TIC_323007_TI_S,
    W_S208,
    W_S314,
)
from ureasim.data.unit_323c003 import (
    MW_305,
    SV32351_CAP_KGH,
    SV32351_COUNT,
    SV32351_K,
    SV32351_MW_REL,
    SV32351_P_REL_BARA,
    SV32351_RESEAT_BARA,
    SV32351_SET_BARA,
    SV32351_T_REL_K,
    SV32351_Z_REL,
)
from ureasim.data.unit_329 import P_LP_BARA
from ureasim.thermo import iapws
from ureasim.thermo.empirical import urea_soln_rho
from ureasim.thermo.urea_liquor import stage_bubble_p
from ureasim.units import liquor_stage
from ureasim.units.consequence.seal import blowthrough_kgh, gas_density_ideal, seal_fraction
from ureasim.units.recirc.liquor_line import receive_liquor, stream_cp
from ureasim.units.steam_chest import ChestValve, steam_chest_pressure

#: The 322E001 -> 323C003 line, which this unit owns as the receiving vessel. Source: V1
#: `main.py`, ``_transport_process(s, "322E001_TO_323C003", ...)``.
FEED_ROUTE = "322E001_TO_323C003"

#: Key the lagged LP header pressure the heater sees is stored under. Source: V1 `main.py`,
#: ``_lag1(s.tlag, "323C003_P_LP_thermal", ...)``.
P_LP_LAG_KEY = "323C003_P_LP_thermal"

#: Numerical floors, V1's own: the temperature integration's heat capacity [kJ/K], a design
#: gas rate the pressure ratios divide by [kg/h], and the blow-through gas molar sum [-].
HEAT_CAPACITY_FLOOR_KJK = 1e-6
GAS_RATE_FLOOR_KGH = 1e-6
MOLAR_SUM_FLOOR = 1e-9


# ======================================================================================
# The three controllers, seeded as V1 seeds them, on the table's gains per cent of span
# ======================================================================================

def tic_323007() -> ProcessLoop:
    """TIC-323007, the column-temperature master. Its output is the chest-pressure DEMAND
    [bar a] handed to PIC-329202 as a remote set point. Derivative disabled (Td = -1)."""
    return ProcessLoop(
        tag="TIC-323007", Kc=TIC_323007_KC, Ti=TIC_323007_TI_S, Td=-1.0, act=+1.0,
        op=E002_PCHEST_DES_BARA, sp=C003_T_SP_C,
        pv=C003_T_SP_C, pv1=C003_T_SP_C, pv2=C003_T_SP_C,
        op_lo=0.0, op_hi=P_LP_BARA, sp_lo=TIC_323007_SP_LO_C, sp_hi=TIC_323007_SP_HI_C)


#: PV-329202 as the port runs it, on its vendor's trim (Metso's Neldisc from 32.92 %, decided
#: 2026-10-15), and as V1 runs it, linear from V1's stroke — which the equivalence harness keeps.
PV_329202_CHEST = ChestValve(PV_329202_OP_DES_PCT, PV_329202.characteristic, PV_329202_XT)
V1_CHEST = ChestValve(E002_OP_DES_PCT)
#: The column as V1 builds it, for the equivalence harnesses: V1's chest and its level law.
V1_COLUMN = {"chest": V1_CHEST, "taps": False}


def pic_329202(valve: ChestValve = PV_329202_CHEST) -> ProcessLoop:
    """PIC-329202, the 323E002 chest-pressure slave, in CASCADE under TIC-323007. Its output is
    the PV-329202 stroke [%]."""
    return ProcessLoop(
        tag="PIC-329202", Kc=PIC_329202_KC, Ti=PIC_329202_TI_S,
        Td=0.0, act=+1.0, mode="CAS",
        op=valve.op_des_pct, sp=E002_PCHEST_DES_BARA,
        pv=E002_PCHEST_DES_BARA, pv1=E002_PCHEST_DES_BARA, pv2=E002_PCHEST_DES_BARA,
        op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=P_LP_BARA)


def lic_323501(taps: bool = True) -> ProcessLoop:
    """LIC-323501, the column level. DIRECT acting: a level above set point opens LV-323501.
    Seeded on LT-323501 between its taps, the design holdup's 40 % (decision 241); ``taps=False``
    is V1's 60 %."""
    r = LT_323501_DES_PCT if taps else C003_LVL_SP_PCT
    return ProcessLoop(
        tag="LIC-323501", Kc=LIC_323501_KC, Ti=LIC_323501_TI_S, Td=0.0, act=-1.0,
        op=LV501_OP_DES_PCT, sp=r, pv=r, pv1=r, pv2=r,
        op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=100.0)


# ======================================================================================
# The relations
# ======================================================================================

def column_pressure_target_bara(flash_gas_ratio: float, heater_gas_ratio: float,
                                downstream_bara: float, blow_m3h: float = 0.0) -> float:
    """PT-323201's target [bar a] from its two gas sources and the node it discharges to.

    Process utility
    ---------------
    The column pressure the operator reads, and the pressure the bottoms bubble point rides:
    more gas -> higher pressure -> higher boiling temperature, which is what gives TIC-323007
    a correctly signed plant. The two sources move it independently:

      * ``flash_gas_ratio`` — PFD 301, the stripper bottoms flashing across LV-322501, over
        its design rate. Opening LV-322501, or a hotter stripper bottom, raises it.
      * ``heater_gas_ratio`` — PFD 302, the gas the 323E002 heater raises, over its design
        rate. More steam duty raises it; pinching PV-329202 collapses it while the letdown
        keeps charging the column.
      * ``blow_m3h`` — the stripper gas an uncovered LV-322501 blows into the head space, by its
        own volume [m3/h] (decided 2026-10-03, handoff A-16; V1 has no such term). Zero adds
        nothing, so the law is V1's whenever the stripper's seal holds.

    Equation
    --------
        Q_equiv  = Q301,des . r_301 + Q302,des . r_302 + Q_blow     [m3/h]
        P_target = sqrt( P_down^2 + (Q_equiv / C)^2 )               [bar a]

    the friction head of the one flowing line between the column overhead and the 323E003 /
    323D001 node, so inverting it gives back Q = C . sqrt(P^2 - P_down^2). Nothing is added
    outside the root, which keeps the two pressures on one node. At design (both ratios 1.0,
    downstream 3.2 bar a) it returns exactly 4.1 bar a.

    Raises ValueError on a non-finite input, a negative ratio or a non-positive downstream
    pressure, as V1 does: each is a defect upstream, not a state to carry on from.

    Source: V1 `c003_pressure_coupling.py` `c003_pressure_target_bara`.
    """
    values = (flash_gas_ratio, heater_gas_ratio, downstream_bara, blow_m3h)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("pressure-coupling inputs must be finite")
    if flash_gas_ratio < 0.0 or heater_gas_ratio < 0.0 or blow_m3h < 0.0:
        raise ValueError("gas-load flow ratios must be nonnegative")
    if downstream_bara <= 0.0:
        raise ValueError("downstream absolute pressure must be positive")
    equivalent_gas_load_m3h = (Q301_DES_M3H * flash_gas_ratio      # from the HP stripper
                               + Q302_DES_M3H * heater_gas_ratio    # from the 323E002 heater
                               + blow_m3h)                          # blown through LV-322501
    return math.sqrt(downstream_bara ** 2
                     + (equivalent_gas_load_m3h / GAS_LOAD_COEFF_M3H_PER_BAR) ** 2)


def letdown_kgh(stroke_pct: float, p_column_bara: float, p_flash_bara: float, w_urea: float,
                t_c: float, pv_bara: float) -> float:
    """LV-323501 liquid flow to 323F004 [kg/h], on the anchored IEC 60534 liquid law.

    Process utility
    ---------------
    The column's drain. It follows the stroke, the live pressure difference between the
    column and the flash tank, and the live density of what it passes — so a column pressure
    rising, or the flash tank backing up, moves it. V1's earlier ``design . stroke/stroke_des``
    had no pressure term at all (report D-1).

    The liquor reaches the valve at its bubble point and flashes in it, as Flowserve sized it
    (vapour pressure 4.1 bar a): its flow chokes on FL^2 (P1 - FF . Pv), ``pv_bara`` the column
    liquor's live bubble pressure (decided 2026-09-30, handoff B-46). At the design state the
    choke binds: the drain answers the column's pressure and temperature, not 323F004's.
    """
    return valve_liquid_anchored(
        R323_M314_DES, stroke_pct / 100.0, p_column_bara, p_flash_bara,
        urea_soln_rho(w_urea, t_c, RHO_S314),
        LV501_OP_DES_PCT / 100.0, C003_P_BARA, F004_P_BARA, RHO_C003_DES,
        characteristic=LV501_CHAR, fl=LV501_FL, pv_bara=pv_bara, pv_des_bara=LV501_PV_DES_BARA)


def sv_32351() -> GasReliefValve:
    """SV32351 and SV32352, the column's two safety valves, shut: set 6.01 bar a, reseating at
    5.51, each orifice back-solved from its certified 72 273.6 kg/h at 6.51 bar a (A-16)."""
    return GasReliefValve(
        valve=SafetyValve("SV32351/52", SV32351_SET_BARA, SV32351_RESEAT_BARA),
        area_m2=psv_area_from_rated_m2(SV32351_CAP_KGH, SV32351_P_REL_BARA, SV32351_T_REL_K,
                                       SV32351_MW_REL, k=SV32351_K, z=SV32351_Z_REL),
        k=SV32351_K, count=SV32351_COUNT)


def head_space_relief_kgh(sv: GasReliefValve, p_bara: float, t_c: float, m_305_kgh: float,
                          blow_kgh: float, blow_mw: float) -> float:
    """What SV32351 / SV32352 relieve of the column's head space this tick [kg/h].

    Process utility
    ---------------
    The column's protection against the HP stripper gas a failed LV-322501 passes. The valves
    read PT-323201 at the top of the tick and pop at their set pressure; lifted, they pass the
    API 520 critical flow of the head space's gas — the column's own overhead at PFD 305's molar
    mass and the stripper's gas at its own — until the pressure falls to their reseat. The
    pressure law holds no gas inventory, so the valves pass at most what the head space receives
    on the tick.

    Equation
    --------
        M_head = (m_305 + m_blow) / (m_305 / M_305 + m_blow / M_blow)
        W      = min( n . W_API520(A, P, T, M_head), m_305 + m_blow )    when lifted, else 0
    """
    gas_kgh = m_305_kgh + blow_kgh
    if not sv.valve.step(p_bara) or gas_kgh <= 0.0:
        return 0.0
    mw_head = gas_kgh / (m_305_kgh / MW_305 + blow_kgh / blow_mw)
    return min(sv.count * psv_api520_choked_kgh(sv.area_m2, p_bara, t_c + ABSOLUTE_ZERO_C,
                                                 mw_head, k=sv.k, kd=sv.kd), gas_kgh)


# ======================================================================================
# The unit
# ======================================================================================

@dataclass(frozen=True)
class RectifyingColumnResult:
    """Everything stage 1 publishes on one tick."""

    #: The feed as it arrived through the 322E001 -> 323C003 line [kg/h], [deg C], [-].
    feed_kgh: float
    feed_t_c: float
    feed_w: dict
    #: TIC-323007's chest-pressure demand [bar a] and PV-329202's stroke [%].
    tic_op_bara: float
    pic_op_pct: float
    #: 323E002 chest pressure [bar a] and duty [kW].
    chest_p_bara: float
    q_e002_kw: float
    #: The bubble point the holdup relaxes toward [deg C], and the duty retained to get there.
    t_bub_c: float
    q_relax_kw: float
    #: The upstream temperature the flash term used [deg C] — the live TT-322004.
    t_strip_bottom_c: float
    #: Heat the letdown flash releases [kW], and the two gas sources [kg/h].
    q_flash_kw: float
    m_flash_gas_kgh: float
    m_heater_gas_kgh: float
    #: PFD 305 overhead to 323E003 [kg/h], its composition, and the surface it came off.
    m_305_kgh: float
    y_305: dict
    vapour_domain: str | None
    #: LIC-323501's input and output [%], the drain [kg/h], and the seal on its nozzle.
    level_pct: float
    lv501_op_pct: float
    m_314_kgh: float
    seal_fraction: float
    #: Column gas passing an uncovered LV-323501 into the 323F004 gas space [kg/h].
    blowthrough_kgh: float
    lv501_blowthrough: bool
    #: The state the drain departed at — the column's temperature [deg C] and composition
    #: BEFORE this tick advanced them. 323F004 carries it down its inlet line.
    drain_t_c: float
    drain_w: dict
    #: Biuret formed [kmol/h].
    xi_kmolh: float
    #: The two pressure-path ratios and the target they give [-, -, bar a].
    flash_gas_ratio: float
    heater_gas_ratio: float
    p_target_bara: float
    #: The stripper gas an uncovered LV-322501 blew into the head space [kg/h], what SV32351 /
    #: SV32352 relieved of the head space [kg/h], whether they are lifted, and the fraction of
    #: the head space's gas that left overhead to 323E003 [-], exactly 1.0 with the valves shut.
    blow_in_kgh: float
    relief_kgh: float
    relief_lifted: bool
    overhead_frac: float
    #: The state after this tick.
    m_kg: float
    t_c: float
    p_bara: float
    w: dict
    #: TT-323002, the column sump (PFD 313) [deg C].
    tt_323002_c: float


@dataclass
class RectifyingColumn:
    """323C003 and 323E002 as one object: the column's state and its step."""

    #: Liquid holdup [kg], temperature [deg C], PT-323201 [bar a] and composition.
    m_kg: float = C003_M_DES_KG
    t_c: float = C003_T_SP_C
    p_bara: float = C003_P_BARA
    w: dict = field(default_factory=lambda: dict(W_S314))
    #: 323E002 chest pressure [bar a], the previous tick's — PIC-329202's PV.
    chest_p_bara: float = E002_PCHEST_DES_BARA
    #: PV-329202's trim (decision 108's class, applied 2026-10-15).
    chest: ChestValve = PV_329202_CHEST
    #: The feed line's packet FIFO and the LP-header lag.
    line_state: dict = field(default_factory=dict)
    lag_state: dict = field(default_factory=dict)
    #: SV32351 and SV32352 (handoff A-16).
    sv_32351: GasReliefValve = field(default_factory=sv_32351)
    #: LT-323501 between its taps (decided 2026-11-16, decision 241); False is V1's M / M_full.
    taps: bool = True

    def step(self, tic: ProcessLoop, pic: ProcessLoop, lic: ProcessLoop,
             drain_kgh: float, tt_323001_c: float, bottoms_mass_pct: dict,
             tt_322004_c: float, p_lp_bara: float, p_f004_bara: float, p_d001_bara: float,
             dt: float, *, blow_in_kgh: float = 0.0,
             blow_mw: float = MW_305) -> RectifyingColumnResult:
        """Advance stage 1 by one tick.

        Arguments
        ---------
        drain_kgh, tt_323001_c, bottoms_mass_pct
            What leaves the 322E001 sump through LV-322501: the flow [kg/h], its temperature
            after the letdown flash [deg C], and its composition on any scale.
        tt_322004_c
            The LIVE stripper bottom temperature [deg C] (As-Built §XXVIII.6).
        p_lp_bara
            The live LP steam header [bar a].
        p_f004_bara, p_d001_bara
            The 323F004 and 323E003/323D001 pressures at the start of the tick [bar a] — both
            explicit tears, advanced by their own units later in the tick.
        blow_in_kgh, blow_mw
            The stripper gas an uncovered LV-322501 passes this tick [kg/h] and its molar mass
            [kg/kmol], the stripper top vapour's (handoff A-16).

        The order is V1's and it is not interchangeable: the controllers act on the state at
        the top of the tick; the temperature advances before the vapour composition and the
        biuret extent are evaluated, which therefore see the NEW temperature and the OLD
        composition and pressure; the pressure advances last.
        """
        # ----- the feed: one closed packet down the 322E001 -> 323C003 line ------------
        # Mass, temperature and composition leave together and arrive together after
        # rho . V / m_dot. A stripper that has stopped making bottoms can still be drained,
        # and then the departure needs a composition: the PFD 208 row is the placeholder.
        w_dep = normalise_solution_mass_fraction(bottoms_mass_pct, W_S208)
        feed = receive_liquor(self.line_state, FEED_ROUTE, max(drain_kgh, 0.0), tt_323001_c,
                              w_dep, CP_S208_DES, dt)
        m_feed, t_feed, w_feed, cp_feed = feed.m_kgh, feed.t_c, feed.w, feed.cp_kj_kgk
        cp_col = stream_cp(self.w.get("Urea", 0.0), self.t_c, CP_C003_DES)

        # ----- 323E002: TIC-323007 -> PIC-329202 -> the steam chest ---------------------
        tic_op = tic.step(self.t_c, dt)
        pic_op = pic.step(self.chest_p_bara, dt, cas_sp=tic_op)
        # The header responds in a second, but the column liquid moves on its own
        # residence time, so the heater sees the header through that lag, not the 1 s one.
        p_lp_lagged = first_order_lag(self.lag_state, P_LP_LAG_KEY, p_lp_bara,
                                      C003_M_TAU_S, dt)
        self.chest_p_bara = steam_chest_pressure(
            pic_op, p_lp_lagged, self.chest.op_des_pct, E002_PCHEST_DES_BARA, E002_UA_KW,
            self.t_c, E002_Q_DES_KW, P_LP_BARA, self.chest_p_bara,
            characteristic=self.chest.characteristic, xt=self.chest.xt)
        # A condensing chest can only ADD heat: shut the valve and it stops condensing, it
        # does not refrigerate the column (report F-10).
        q_e002 = max(E002_UA_KW * (iapws.tsat_c(self.chest_p_bara) - self.t_c), 0.0)

        # ----- the two gas sources and the energy-limited boil-up ----------------------
        # The liquid sits at its bubble point: the duty not spent boiling walks the holdup
        # toward it over its own residence time, so dT/dt = (T_bub - T)/tau (report TD-014).
        t_bub = liquor_stage.bubble_t(C003_LIQUOR, self.w, self.p_bara)
        q_relax = self.m_kg * cp_col * (t_bub - self.t_c) / C003_M_TAU_S
        # Source 1 — stream 301, from the HP stripper: the sensible heat the bottoms bring
        # down from the LIVE TT-322004, released as they flash to TT-323001.
        t_strip_bottom = tt_322004_c
        q_flash = m_feed / 3600.0 * cp_feed * (t_strip_bottom - tt_323001_c)
        m_flash_gas = max(M305_DES_KGH * (q_flash / Q305_DES_KW), 0.0)
        # Source 2 — stream 302, from 323E002: the heater duty left after the relaxation.
        m_heater_gas = max(M305_DES_KGH * ((q_e002 - q_relax) / Q305_DES_KW), 0.0)
        # The overhead cannot exceed what the composition allows off the feed (report F-2).
        m_305 = min(R323_PHI_V305 * m_feed, m_flash_gas + m_heater_gas)
        q305_avail = q_flash + q_e002

        # ----- LIC-323501 -> LV-323501, and the seal on its nozzle --------------------
        level = (lt_323501_pct(self.m_kg) if self.taps
                 else clamp(self.m_kg / C003_M_FULL_KG * 100.0, 0.0, 100.0))
        lv501_op = lic.step(level, dt)
        m_314 = letdown_kgh(lv501_op, self.p_bara, p_f004_bara, self.w.get("Urea", 0.0), self.t_c,
                            stage_bubble_p(C003_LIQUOR, self.w, self.t_c, self.p_bara))
        # 4.1 -> 1.13 bar a is past the choke, so an uncovered trim passes column gas at a
        # flow the column's own pressure sets. Sealed, the gas is exactly 0.0.
        seal = seal_fraction(level, LT_323501_SEAL_PCT if self.taps else 0.0)
        m_314 *= seal
        blow = 0.0
        if seal < 1.0:
            y_gas, _ = liquor_stage.vapour(C003_LIQUOR, self.w, self.t_c, self.p_bara)
            mw_gas = 1.0 / max(sum(v / MW_COMP[k] for k, v in y_gas.items() if v > 0.0),
                               MOLAR_SUM_FLOOR)
            blow = blowthrough_kgh(
                R323_M314_DES, RHO_C003_DES, C003_P_BARA - F004_P_BARA,
                lv501_op / LV501_OP_DES_PCT, gas_density_ideal(self.p_bara, self.t_c, mw_gas),
                self.p_bara, max(self.p_bara - p_f004_bara, 0.0), seal)
        p_net = q305_avail - m_305 / 3600.0 * LAMBDA_305_KJKG

        # ----- the balances ------------------------------------------------------------
        m_pre, t_pre, w_pre = self.m_kg, self.t_c, self.w
        # Explicit, and unconditionally stable here: the only temperature dependence is the
        # relaxation, whose derivative scales WITH the holdup, so dt/tau stays dt/tau_res
        # however far the column drains.
        self.t_c = t_pre + p_net * dt / max(m_pre * cp_col, HEAT_CAPACITY_FLOOR_KJK)
        self.m_kg = max(m_pre + (m_feed - m_305 - m_314) / 3600.0 * dt, C003_M_FLOOR_KG)
        y_305, domain = liquor_stage.vapour(C003_LIQUOR, w_pre, self.t_c, self.p_bara)
        xi = liquor_stage.biuret_extent(C003_LIQUOR, m_pre, w_pre, self.t_c)
        self.w = liquor_stage.advance_species(w_pre, m_pre, self.m_kg, m_feed, w_feed,
                                              m_305, y_305, m_314, xi, dt)

        # ----- SV32351 / SV32352 on the head space, and what leaves overhead (A-16) --------
        # The stripper's gas is a load on the overhead line by its own volume at the head
        # space's state; with the valves shut and no blow-through every factor is exactly 1.0
        # and every added term exactly 0.0, which leaves V1's law.
        blow_in = max(blow_in_kgh, 0.0)
        relief = head_space_relief_kgh(self.sv_32351, self.p_bara, self.t_c, m_305, blow_in,
                                       blow_mw)
        overhead = 1.0 - relief / (m_305 + blow_in) if relief > 0.0 else 1.0
        blow_m3h = (blow_in * overhead / gas_density_ideal(self.p_bara, self.t_c, blow_mw)
                    if blow_in > 0.0 else 0.0)

        # ----- PT-323201, from its gas sources, net of the relief ----------------------
        r_flash = m_flash_gas * overhead / max(M_FLASH_GAS_DES_KGH, GAS_RATE_FLOOR_KGH)
        r_heater = m_heater_gas * overhead / max(M_POOL_VAP_DES_KGH, GAS_RATE_FLOOR_KGH)
        p_target = column_pressure_target_bara(r_flash, r_heater, p_d001_bara, blow_m3h)
        self.p_bara = clamp(self.p_bara + (p_target - self.p_bara) / C003_P_TAU_S * dt,
                            C003_P_MIN_BARA, C003_P_MAX_BARA)

        return RectifyingColumnResult(
            feed_kgh=m_feed, feed_t_c=t_feed, feed_w=w_feed,
            tic_op_bara=tic_op, pic_op_pct=pic_op,
            chest_p_bara=self.chest_p_bara, q_e002_kw=q_e002,
            t_bub_c=t_bub, q_relax_kw=q_relax, t_strip_bottom_c=t_strip_bottom,
            q_flash_kw=q_flash, m_flash_gas_kgh=m_flash_gas, m_heater_gas_kgh=m_heater_gas,
            m_305_kgh=m_305, y_305=y_305, vapour_domain=domain,
            level_pct=level, lv501_op_pct=lv501_op, m_314_kgh=m_314, seal_fraction=seal,
            blowthrough_kgh=blow, lv501_blowthrough=bool(blow > 0.0),
            drain_t_c=t_pre, drain_w=w_pre, xi_kmolh=xi,
            flash_gas_ratio=r_flash, heater_gas_ratio=r_heater, p_target_bara=p_target,
            blow_in_kgh=blow_in, relief_kgh=relief, relief_lifted=self.sv_32351.valve.lifted,
            overhead_frac=overhead, m_kg=self.m_kg, t_c=self.t_c, p_bara=self.p_bara, w=self.w,
            tt_323002_c=self.t_c - (C003_T_SP_C - C003_T313_C),
        )


__all__ = [
    "FEED_ROUTE", "P_LP_LAG_KEY",
    "HEAT_CAPACITY_FLOOR_KJK", "GAS_RATE_FLOOR_KGH", "MOLAR_SUM_FLOOR",
    "V1_COLUMN", "tic_323007", "pic_329202", "lic_323501", "sv_32351",
    "column_pressure_target_bara", "letdown_kgh", "head_space_relief_kgh",
    "RectifyingColumnResult", "RectifyingColumn",
]
