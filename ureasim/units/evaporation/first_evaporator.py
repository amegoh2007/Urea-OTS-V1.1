"""324E001 and 324F001 — the first evaporator and its separator, stage 1 of unit 324.

What this models
----------------
323D002's solution, PFD 317 (80 % urea, 99 C), pumped by 323P003 under FIC-324401, climbs the
tubes of 324E001, heated by LP steam on the shell, and boils under the vacuum of the 324F001
separator. The vapour, PFD 705 (14 t/h, nearly all water), joins 323F010's 790 into the
324E002 condenser, whose vent 324F002 pulls; the melt, PFD 401 (94.3 % urea, 130 C), drains
through a barometric leg into 324E003, stage 2.

    TIC-324001 (melt T)  ->  PIC-329203 (324E001 chest P)  ->  PV-329203 (LP steam)
    PIC-324202 (PT-324202, the vacuum)  ->  PV-324202 (false air into 324E002)
    LIC-329505 (the chest's condensate)  ->  LV-329505 (to 329D001)

The separator is a well-mixed melt holdup with mass, energy and species balances, and a vapour
space whose pressure is a molar balance between the condenser's vent and the ejector's pull:

    dM/dt      = m_feed - m_vap - m_boil - m_401
    M cp dT/dt = m_feed cp_feed (T_feed - T) + UA (Tsat(P_chest) - T) - (m_vap + m_boil) . lambda
    m_vap      = clamp( m_feed - m_urea / w_eq(T, P), 0, m_feed )
    dP/dt      = (R T / V_v)(n_vent(P) - n_pull(P))

The feed's boil-off is the water that takes its urea to the melt's equilibrium strength at the
separator's temperature and pressure (`thermo.urea_melt`, V1's TD-016): no fixed ceiling, no
duty relay, so TIC-324001 always has a process gain. The holdup's own boil-off, m_boil, is what
the chest boils out of a melt heated past its own boiling point (`holdup_boil`, handoff B-62);
zero at design. T and P are solved together each tick by Picard to 1e-12 in at most 20
iterations (V1's G7): the melt temperature semi-implicit, T' = T + P_wr dt / (M cp + k_cap dt),
then the holdup boiled back to its boiling point; the pressure stepped backward
(`core.node.backward_euler_pressure`) against 324E002's anchored saturated vent at the trial
pressure, with its cold end held at the last full solve's, and 324F002's pull off its map. The
holdup's boil-off is evaluated at the trial pressure inside that backward step: it answers the
vacuum by thousands of kg/h per mbar, so held at the iterate it would ring the fixed point.

Where this stage departs from V1 — each a decided divergence, run both ways in
`tests/equivalence/test_first_evaporator_equivalence.py`:

  * **The melt** (handoff B-58, decided 2026-10-01): the UNIQUAC parameter refitted to the PFD,
    -85.3 K, and the strength capped at what the feed's biuret and formaldehyde leave.
  * **The pull** (handoffs B-57 and B-61, decided 2026-10-01): 324F002's synthesized map
    (`ejector_map`) on its vendor throats, its capacity anchored on PFD 706's 72 kg/h at 0.33
    bar a, at its live motive and discharge pressures — where V1 pulls a straight line,
    72 kg/h x motive / 390 x P / 0.33, with no break.
  * **The holdup boils** (handoff B-62, decided 2026-10-01): past its own boiling point at the
    vacuum the held melt boils, where V1 boils the feed's water only.
  * **The chest on its datasheet** (decision 20): 3.7 bar a, where V1 anchors on 3.96; the
    stroke and the conductance re-derived by V1's own expressions.
  * **The gains on span** (decisions 10, 21): TIC-324001, PIC-329203, PIC-324202 on the DCS
    table's rows per cent of their transmitters' spans, without V1's chest-gain scale.
  * **PV-324202 on its vendor trim** (decision 23): Flowserve's Pos. 55 from its 61.07 % stroke.
  * **PV-329203 on its vendor trim** (decision 23's class, decided 2026-10-14): Metso's DN 250
    Neldisc, Cv 4870, its printed capacities as its curve, from its 39.31 % design stroke, where
    V1 runs the chest valve linear from 73.80 % (`steam_chest.ChestValve`).
  * **The barometric leg above its heel** (decision 11, handoff B-29's class): the leg drains
    only the melt above the 1 kg floor, net of the boil-off.

Sources
-------
V1 ``backend/main.py`` step_sim, "Stage 1 : Evaporator I" (9706-9890), the 323D002 -> 324E001
line transport; the stage's constants (2141-2327); ``_backward_euler_p``; ``evap_w_eq``,
``evap_thermo_diag``; the species layer (``sol_vapour_y``, ``sol_biuret_xi``, ``sol_advance``).
The design data are in `ureasim.data.unit_324`, each with its source.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ureasim.control.process_loop import ProcessLoop
from ureasim.control.valve import cv_fraction
from ureasim.core.node import backward_euler_pressure, vapour_volume_m3, vessel_dpdt
from ureasim.core.numeric import clamp
from ureasim.core.signal import first_order_lag
from ureasim.core.units_of_measure import ABSOLUTE_ZERO_C
from ureasim.data.design_point import R323_CP_SOLN, R324_W_IN
from ureasim.data.control_valves import LV_329505, PV_329203
from ureasim.data.unit_324 import (
    E001_COND_DES_KGH,
    E001_COND_LEVEL_SP_PCT,
    E001_COND_M_DES_KG,
    E001_COND_M_FLOOR_KG,
    E001_COND_M_FULL_KG,
    E001_LAMBDA_KJKG,
    E001_LAMBDA_STEAM_KJKG,
    E001_LIQUOR,
    E001_OP_DES_PCT,
    PV_329203_OP_DES_PCT,
    PV_329203_XT,
    E001_PCHEST_DES_BARA,
    E001_Q_DES_KW,
    E001_T_DES_C,
    E001_UA_KW,
    E001_W_UREA_DES,
    E002_INLET_DES_KGH,
    F001_FA_DES_KGH,
    F001_M_DES_KG,
    F001_M_FLOOR_KG,
    F001_M_FULL_KG,
    F001_M_TAU_S,
    F001_MW_VAP,
    F001_P_DES_BARA,
    F001_P_MAX_BARA,
    F001_P_MIN_BARA,
    F001_RHO_L,
    F001_VOL_M3,
    F010_VAPOUR_DES_KGH,
    LIC_329505_DZ_PCT,
    LIC_329505_KC,
    LIC_329505_TI_S,
    LV_329505_OP_DES_PCT,
    LV_329505_SPAN_KGH,
    LV_329505_VENDOR_OP_DES_PCT,
    MELT_A_UREA_WATER_K,
    P1_DES_KGH,
    PIC_324202_KC,
    PIC_324202_TI_S,
    PIC_329203_KC,
    PIC_329203_TI_S,
    PT_LOOP_MAXIT,
    PT_LOOP_TOL,
    PV_324202_OP_DES_PCT,
    TIC_324001_KC,
    TIC_324001_TI_S,
    V1_DES_KGH,
)
from ureasim.data.unit_329 import P_LP_BARA
from ureasim.thermo import iapws
from ureasim.thermo.domains import NONVOLATILE
from ureasim.thermo.empirical import urea_soln_cp
from ureasim.thermo.urea_liquor import vapour_y
from ureasim.thermo.urea_melt import equilibrium_urea_fraction, melt_diagnostics, strength_ceiling
from ureasim.units import liquor_stage
from ureasim.units.evaporation.condenser_node import inlet_kmolh
from ureasim.units.evaporation.ejector_map import suction_capacity_kgh
from ureasim.units.evaporation.holdup_boil import holdup_boil
from ureasim.units.evaporation.vacuum_condenser import (
    condensate_back_pressure,
    design_specs,
    vent_kgh_at,
)
from ureasim.units.recirc.liquor_line import receive_liquor
from ureasim.units.steam_chest import ChestValve, steam_chest_pressure

#: The 323D002 -> 324E001 line, which this stage owns as the receiving one (V1
#: ``_transport_process(s, "323D002_TO_324E001", ...)``).
INLET_ROUTE = "323D002_TO_324E001"

#: Key the lagged LP header the chest sees is stored under (V1 ``"324E001_P_LP_thermal"``).
P_LP_LAG_KEY = "324E001_P_LP_thermal"

#: The ejector that pulls this stage's vacuum, through 324E002's vent.
EJECTOR_TAG = "324F002"

#: V1's numerical floors at this stage: the equilibrium strength [-], the heat capacity of the
#: temperature step [kJ/K], a melt flow [kg/h], the step [s].
W_EQ_FLOOR = 1e-6
HEAT_CAPACITY_FLOOR_KJK = 1e-6
FLOW_FLOOR_KGH = 1e-6
DT_FLOOR_S = 1.0e-9

#: The urea fraction the feed is read at when its composition carries none (V1's default).
FEED_W_UREA_DEFAULT = R324_W_IN

#: The feed's cp anchor on the inlet line's packet [kJ/(kg K)]: the lumped design value, so the
#: packet carries V1's own ``urea_soln_cp`` of the departing liquor.
FEED_CP_ANCHOR = R323_CP_SOLN


# ======================================================================================
# The four controllers, seeded as V1 seeds them, on the table's gains per cent of span
# ======================================================================================

def tic_324001() -> ProcessLoop:
    """TIC-324001, the melt-temperature master: its output is the chest-pressure DEMAND [bar a]
    handed to PIC-329203 as a remote set point."""
    return ProcessLoop(
        tag="TIC-324001", Kc=TIC_324001_KC, Ti=TIC_324001_TI_S, Td=0.0, act=+1.0,
        op=E001_PCHEST_DES_BARA, sp=E001_T_DES_C,
        pv=E001_T_DES_C, pv1=E001_T_DES_C, pv2=E001_T_DES_C,
        op_lo=0.0, op_hi=P_LP_BARA, sp_lo=0.0, sp_hi=200.0)


#: PV-329203 as the port runs it, on its vendor's trim (DN 250 Neldisc, Cv 4870, from 39.31 %; decided 2026-10-14),
#: and as V1 runs it, linear from V1's stroke — which the equivalence harness keeps.
PV_329203_CHEST = ChestValve(PV_329203_OP_DES_PCT, PV_329203.characteristic, PV_329203_XT)
V1_CHEST = ChestValve(E001_OP_DES_PCT)


def pic_329203(valve: ChestValve = PV_329203_CHEST) -> ProcessLoop:
    """PIC-329203, the 324E001 chest-pressure slave, in CASCADE under TIC-324001: its output is
    the PV-329203 stroke [%], seeded on ``valve``'s design stroke."""
    return ProcessLoop(
        tag="PIC-329203", Kc=PIC_329203_KC, Ti=PIC_329203_TI_S, Td=-1.0, act=+1.0, mode="CAS",
        op=valve.op_des_pct, sp=E001_PCHEST_DES_BARA,
        pv=E001_PCHEST_DES_BARA, pv1=E001_PCHEST_DES_BARA, pv2=E001_PCHEST_DES_BARA,
        op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=P_LP_BARA)


def pic_324202() -> ProcessLoop:
    """PIC-324202, the 324F001 vacuum: reverse acting, a pressure under its set point admits
    more false air. Its output is the PV-324202 stroke [%]."""
    return ProcessLoop(
        tag="PIC-324202", Kc=PIC_324202_KC, Ti=PIC_324202_TI_S, Td=-1.0, act=+1.0,
        op=PV_324202_OP_DES_PCT, sp=F001_P_DES_BARA,
        pv=F001_P_DES_BARA, pv1=F001_P_DES_BARA, pv2=F001_P_DES_BARA,
        op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=1.0)


#: LV-329505 as the port runs it — Flowserve's Pos. 71, modified equal percentage, from its
#: 62.19 % design stroke (decided 2026-10-15) — as (design stroke [%], trim); V1's is None, linear
#: on its span from 50 %, which the equivalence harness keeps.
LV_329505_TRIM = (LV_329505_VENDOR_OP_DES_PCT, LV_329505.characteristic)
V1_TRAP_OP_DES_PCT = LV_329505_OP_DES_PCT


def lic_329505(op_des_pct: float = LV_329505_VENDOR_OP_DES_PCT) -> ProcessLoop:
    """LIC-329505, the chest's condensate level: direct acting, its output the LV-329505
    stroke [%], seeded on the trap's design stroke (no deadband: the table's 2 %, which V1
    applies on this loop, is not modelled, B-28 decided 2026-10-09)."""
    return ProcessLoop(
        tag="LIC-329505", Kc=LIC_329505_KC, Ti=LIC_329505_TI_S, Td=0.0, Tf=0.0,
        Dz=LIC_329505_DZ_PCT, act=-1.0,
        op=op_des_pct, sp=E001_COND_LEVEL_SP_PCT,
        pv=E001_COND_LEVEL_SP_PCT, pv1=E001_COND_LEVEL_SP_PCT, pv2=E001_COND_LEVEL_SP_PCT,
        op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=100.0)


@dataclass
class FirstEvaporatorLoops:
    """Stage 1's four controllers."""

    tic: ProcessLoop = field(default_factory=tic_324001)
    pic: ProcessLoop = field(default_factory=pic_329203)
    vacuum: ProcessLoop = field(default_factory=pic_324202)
    trap: ProcessLoop = field(default_factory=lic_329505)


# ======================================================================================
# The relations
# ======================================================================================

def false_air_kgh(stroke_pct: float) -> float:
    """The false air PV-324202 admits into 324E002 [kg/h].

    Process utility
    ---------------
    PIC-324202's lever: air blanketing the condenser cuts what it condenses and holds the shell
    — and 324F001 behind it — up at its set point against an ejector sized with margin.

    Equation
    --------
        m = m_des . f(h) / f(h_des)      f the vendor's modified equal-percentage trim

    anchored on PFD 784's 21 kg/h at the design stroke Flowserve's Pos. 55 gives it, 61.07 %
    (decision 23's class; V1 ``R324_F001_FA_DES x op / 50``).
    """
    return F001_FA_DES_KGH * (cv_fraction(stroke_pct / 100.0, "mod_equal_pct")
                              / cv_fraction(PV_324202_OP_DES_PCT / 100.0, "mod_equal_pct"))


def barometric_leg_kgh(holdup_kg: float) -> float:
    """The melt 324F001 drains to 324E003 through its barometric leg [kg/h] (V1 AUDIT C3).

    Process utility
    ---------------
    PFD 401 to stage 2. The leg is hydraulic: what drains rises with the liquid standing over
    it, so the separator can surge, drain and flood where an outlet := inlet - vapour identity
    could not move its level at all.

    Equation
    --------
        m_401 = m_401,des . sqrt(M / M_des)

    Exactly the design melt at the design holdup.
    """
    return P1_DES_KGH * math.sqrt(max(holdup_kg / F001_M_DES_KG, 0.0))


# ======================================================================================
# The unit
# ======================================================================================

@dataclass(frozen=True)
class FirstEvaporatorResult:
    """Everything stage 1 publishes on one tick."""

    #: The feed as it arrived through the 323D002 -> 324E001 line [kg/h], [deg C], [-], and its
    #: urea [kg/h] and specific heat [kJ/(kg K)].
    feed_kgh: float
    feed_t_c: float
    feed_w: dict
    feed_urea_kgh: float
    feed_cp: float
    #: TIC-324001's chest-pressure demand [bar a], PV-329203's stroke [%], the chest [bar a] and
    #: the duty [kW].
    tic_op_bara: float
    pic_op_pct: float
    chest_p_bara: float
    q_kw: float
    #: The false air PV-324202 admitted [kg/h] and PIC-324202's new stroke [%].
    false_air_kgh: float
    vacuum_op_pct: float
    #: The melt's ceiling and equilibrium strength [-], the feed's water boiled off [kg/h], and the
    #: holdup's own boil-off (handoff B-62) [kg/h]: PFD 705 is the two together.
    w_max: float
    w_eq: float
    m_vap_kgh: float
    m_boil_kgh: float
    #: 324E002's trial inlet at the solved state [kg/h].
    m_703_kgh: float
    #: The P-T fixed point: iterations, final residual, converged.
    iterations: int
    residual: float
    converged: bool
    #: The model's validity status and P-x residual [bar] at the solved state.
    thermo_validity: str
    thermo_px_residual_bara: float | None
    #: The melt made [kg/h] and its live urea strength [-]; PFD 401 down the barometric leg
    #: [kg/h].
    melt_kgh: float
    w_melt: float
    m_401_kgh: float
    #: The state the melt departed at — the separator before this tick advanced it — for
    #: 324E003's inlet.
    drain_t_c: float
    drain_w: dict
    #: The vapour's mass fractions and the biuret formed [kmol/h].
    y_vap: dict
    xi_kmolh: float
    #: The chest: steam condensed [kg/h] — the LP steam the stage draws — LI-329505 [%],
    #: LV-329505's stroke [%] and drain [kg/h].
    steam_kgh: float
    cond_level_pct: float
    trap_op_pct: float
    m_cond_out_kgh: float
    #: The holdup as a share of the indicative full separator [%].
    level_pct: float
    #: The state after this tick.
    m_kg: float
    t_c: float
    p_bara: float
    w: dict


@dataclass
class FirstEvaporator:
    """324E001 and 324F001 as one object: the separator's state and its step."""

    #: The melt holdup [kg], TT-324001 [deg C], PT-324201 [bar a] and composition.
    m_kg: float = F001_M_DES_KG
    t_c: float = E001_T_DES_C
    p_bara: float = F001_P_DES_BARA
    w: dict = field(default_factory=lambda: dict(E001_LIQUOR.w_des))
    #: The chest [bar a], the tick before — PIC-329203's PV — and its condensate [kg].
    chest_p_bara: float = E001_PCHEST_DES_BARA
    #: PV-329203's trim (decision 23's class, decided 2026-10-14).
    chest: ChestValve = PV_329203_CHEST
    #: LV-329505's (design stroke, trim), or None for V1's linear span (decided 2026-10-15).
    lv_329505: tuple | None = LV_329505_TRIM
    cond_m_kg: float = E001_COND_M_DES_KG
    #: The inlet line's packet FIFO and the LP-header lag.
    line_state: dict = field(default_factory=dict)
    lag_state: dict = field(default_factory=dict)

    def step(self, loops: FirstEvaporatorLoops, drain_kgh: float, drain_t_c: float,
             drain_w: dict, p_lp_bara: float, p_motive_bara: float, p_discharge_bara: float,
             f010_vapour_kgh: float, sub_703: tuple | None, t_vent_324e002_c: float,
             dt: float) -> FirstEvaporatorResult:
        """Advance stage 1 by one tick.

        Arguments
        ---------
        drain_kgh, drain_t_c, drain_w
            323P003's discharge, m_324, and 323D002's temperature and composition it left at
            (`SolutionTankResult.m_324_kgh`, `.t_c`, `.w`).
        p_lp_bara
            The live LP header [bar a].
        p_motive_bara, p_discharge_bara
            324F002's motive steam at its nozzle (HV-329605's, `ejector_map.nozzle_pressure_bara`
            of its flow; 4.1 bar a at design) and what it discharges into, 323C005 [bar a]: its
            map's pull at a trial 324E002 pressure is the vacuum's outflow (handoff B-61).
        f010_vapour_kgh, sub_703
            What HV-323605 passed to 324E002 this tick, and the share of it that is LV-323505's
            blow-through gas (`PreEvaporatorResult.pull_kgh`, `.blowthrough_share`).
        t_vent_324e002_c
            324E002's cold end from the last full condenser solve — a tear: the cold end moves
            on the exchanger's thermal time scale, not on the pressure's. The plant hands it
            lagged on the tubes' water (`VacuumTrain.cold_end_c`, handoff B-65).

        The order is V1's: the feed arrives; the cascade acts on the state at the top of the
        tick and the chest is solved; the false air is the vacuum stroke the tick before, and
        PIC-324202 then steps on the old pressure; T and P are solved together, the holdup
        boiling back to its boiling point inside the solve; the melt drains, the holdup and the
        species advance; the chest's condensate last.
        """
        feed = receive_liquor(self.line_state, INLET_ROUTE, drain_kgh, drain_t_c, drain_w,
                              FEED_CP_ANCHOR, dt)
        w_feed = feed.w.get("Urea", FEED_W_UREA_DEFAULT)
        urea_in = w_feed * feed.m_kgh
        cp_feed = urea_soln_cp(w_feed, feed.t_c)
        cp_hold = urea_soln_cp(self.w.get("Urea", E001_W_UREA_DES), self.t_c)
        # The melt can carry no more urea than the feed's non-volatiles leave room for (B-58).
        w_max = strength_ceiling(w_feed, sum(feed.w.get(k, 0.0) for k in NONVOLATILE
                                             if k != "Urea"))

        # ----- 324E001: TIC-324001 -> PIC-329203 -> the steam chest ---------------------
        tic_op = loops.tic.step(self.t_c, dt)
        pic_op = loops.pic.step(self.chest_p_bara, dt, cas_sp=tic_op)
        # The header moves in a second; the melt on its own 180 s residence (V1 THERMO-3).
        p_lp_lagged = first_order_lag(self.lag_state, P_LP_LAG_KEY, p_lp_bara, F001_M_TAU_S, dt)
        self.chest_p_bara = steam_chest_pressure(
            pic_op, p_lp_lagged, self.chest.op_des_pct, E001_PCHEST_DES_BARA, E001_UA_KW, self.t_c,
            E001_Q_DES_KW, P_LP_BARA, self.chest_p_bara, characteristic=self.chest.characteristic,
            xt=self.chest.xt)
        t_chest = iapws.tsat_c(self.chest_p_bara)

        # ----- the vacuum: the false air on last tick's stroke, then PIC-324202 ----------
        fa = false_air_kgh(loops.vacuum.op)
        vac_op = loops.vacuum.step(self.p_bara, dt)

        # ----- T and P together (V1 G7) -----------------------------------------------
        m_pre, t_old, p_old, w_pre = self.m_kg, self.t_c, self.p_bara, self.w
        t_sol, p_sol = t_old, p_old
        v_v = vapour_volume_m3(F001_VOL_M3, m_pre, F001_RHO_L)
        spec = design_specs()["324E002"]
        y_vap = vapour_y(w_pre, E001_LIQUOR.anchor.alpha)
        residual, converged, iterations, m_boil = math.inf, False, 0, 0.0
        for iterations in range(1, PT_LOOP_MAXIT + 1):
            q = max(E001_UA_KW * (t_chest - t_sol), 0.0)
            w_eq = equilibrium_urea_fraction(t_sol, p_sol, E001_W_UREA_DES, E001_T_DES_C,
                                             F001_P_DES_BARA, a_urea_water_k=MELT_A_UREA_WATER_K,
                                             w_max=w_max)
            m_vap = clamp(feed.m_kgh - urea_in / max(w_eq, W_EQ_FLOOR), 0.0, feed.m_kgh)
            p_wr = (feed.m_kgh / 3600.0 * cp_feed * (feed.t_c - t_sol)
                    + q - m_vap / 3600.0 * E001_LAMBDA_KJKG)
            # SEMI-IMPLICIT in the T-dependent terms whose capacity rate belongs to a flow or to
            # the chest wall while it still drives in (V1 STIFFNESS): exact at the seed.
            k_cap = feed.m_kgh / 3600.0 * cp_feed + (E001_UA_KW if q > 0.0 else 0.0)
            c_step = max(m_pre * cp_hold + k_cap * dt, HEAT_CAPACITY_FLOOR_KJK)
            t_step = t_old + p_wr * dt / c_step
            # 324E002's trial inlet before the holdup boils: the design row moved by what the feed
            # and 323F010 boil, and by the false air.
            m_703_feed = (E002_INLET_DES_KGH + (f010_vapour_kgh - F010_VAPOUR_DES_KGH)
                          + (m_vap - V1_DES_KGH) + (fa - F001_FA_DES_KGH))

            def boil_at(p: float) -> tuple[float, float]:
                # The held melt boils back to its own boiling point at a trial vacuum (B-62).
                return holdup_boil(
                    t_step, p, m_pre, w_pre, c_step, E001_LAMBDA_KJKG, y_vap.get("Urea", 0.0),
                    F001_M_FLOOR_KG, dt, w_des=E001_LIQUOR.w_des["Urea"], t_des_c=E001_T_DES_C,
                    p_des_bara=F001_P_DES_BARA, a_urea_water_k=MELT_A_UREA_WATER_K)

            n_703 = inlet_kmolh("324E002", m_703_feed + boil_at(p_sol)[0], fa, F001_FA_DES_KGH,
                                sub_703)
            bp_703 = condensate_back_pressure(n_703, t_vent_324e002_c)
            t_k = t_sol + ABSOLUTE_ZERO_C

            def dpdt(p: float) -> float:
                # The holdup's boil-off answers the trial pressure inside the implicit step.
                n = inlet_kmolh("324E002", m_703_feed + boil_at(p)[0], fa, F001_FA_DES_KGH,
                                sub_703)
                vent = vent_kgh_at(spec, p, t_vent_324e002_c, n, bp_703)
                pull = suction_capacity_kgh(EJECTOR_TAG, p, p_motive_bara, p_discharge_bara)
                return vessel_dpdt(p_old, t_k, v_v, F001_MW_VAP, vent / F001_MW_VAP,
                                   pull / F001_MW_VAP)

            p_next = backward_euler_pressure(p_old, dt, dpdt, F001_P_MIN_BARA, F001_P_MAX_BARA)
            m_boil, t_next = boil_at(p_next)
            residual = max(abs(p_next - p_sol), abs(t_next - t_sol))
            p_sol, t_sol = p_next, t_next
            if residual <= PT_LOOP_TOL:
                converged = True
                break
        self.t_c, self.p_bara = t_sol, p_sol

        # ----- the solved state ---------------------------------------------------------
        w_eq = equilibrium_urea_fraction(self.t_c, self.p_bara, E001_W_UREA_DES, E001_T_DES_C,
                                         F001_P_DES_BARA, a_urea_water_k=MELT_A_UREA_WATER_K,
                                         w_max=w_max)
        m_vap = clamp(feed.m_kgh - urea_in / max(w_eq, W_EQ_FLOOR), 0.0, feed.m_kgh)
        q = max(E001_UA_KW * (t_chest - self.t_c), 0.0)
        validity, px_resid = melt_diagnostics(self.t_c, self.p_bara, w_eq,
                                              a_urea_water_k=MELT_A_UREA_WATER_K)
        melt = max(feed.m_kgh - m_vap, 0.0)
        w_melt = clamp(urea_in / max(melt, FLOW_FLOOR_KGH), 0.0, 1.0)
        m_703 = (E002_INLET_DES_KGH + (f010_vapour_kgh - F010_VAPOUR_DES_KGH)
                 + (m_vap + m_boil - V1_DES_KGH) + (fa - F001_FA_DES_KGH))

        # ----- the barometric leg, above its heel (decision 11's class, B-29) -----------
        m_401 = barometric_leg_kgh(m_pre)
        m_401_avail = (max(m_pre - F001_M_FLOOR_KG, 0.0) / max(dt, DT_FLOOR_S) * 3600.0
                       + feed.m_kgh - m_vap - m_boil)
        if m_401 > m_401_avail:
            m_401 = m_401_avail
        self.m_kg = max(m_pre + (feed.m_kgh - m_vap - m_boil - m_401) / 3600.0 * dt,
                        F001_M_FLOOR_KG)

        # ----- the species (V1 F-8 / TD-009): the feed's and the holdup's vapour alike ----
        xi = liquor_stage.biuret_extent(E001_LIQUOR, m_pre, w_pre, self.t_c)
        self.w = liquor_stage.advance_species(w_pre, m_pre, self.m_kg, feed.m_kgh, feed.w,
                                              m_vap + m_boil, y_vap, m_401, xi, dt)

        # ----- the chest's condensate: LIC-329505's active steam trap -------------------
        steam = q / E001_LAMBDA_STEAM_KJKG * 3600.0
        cond_level = clamp(self.cond_m_kg / E001_COND_M_FULL_KG * 100.0, 0.0, 100.0)
        trap_op = loops.trap.step(cond_level, dt)
        if self.lv_329505 is None:
            cond_out = trap_op / 100.0 * LV_329505_SPAN_KGH
        else:
            # On Flowserve's trim, anchored on the design condensate at its design stroke.
            op_des, trim = self.lv_329505
            cond_out = (E001_COND_DES_KGH * cv_fraction(trap_op / 100.0, trim)
                        / cv_fraction(op_des / 100.0, trim))
        self.cond_m_kg = max(self.cond_m_kg + (steam - cond_out) / 3600.0 * dt,
                             E001_COND_M_FLOOR_KG)

        return FirstEvaporatorResult(
            feed_kgh=feed.m_kgh, feed_t_c=feed.t_c, feed_w=feed.w, feed_urea_kgh=urea_in,
            feed_cp=cp_feed, tic_op_bara=tic_op, pic_op_pct=pic_op,
            chest_p_bara=self.chest_p_bara, q_kw=q, false_air_kgh=fa, vacuum_op_pct=vac_op,
            w_max=w_max, w_eq=w_eq, m_vap_kgh=m_vap, m_boil_kgh=m_boil, m_703_kgh=m_703,
            iterations=iterations, residual=residual, converged=converged,
            thermo_validity=validity, thermo_px_residual_bara=px_resid,
            melt_kgh=melt, w_melt=w_melt, m_401_kgh=m_401,
            drain_t_c=t_old, drain_w=w_pre, y_vap=y_vap, xi_kmolh=xi,
            steam_kgh=steam, cond_level_pct=cond_level, trap_op_pct=trap_op,
            m_cond_out_kgh=cond_out, level_pct=self.m_kg / F001_M_FULL_KG * 100.0,
            m_kg=self.m_kg, t_c=self.t_c, p_bara=self.p_bara, w=self.w,
        )


__all__ = [
    "INLET_ROUTE", "P_LP_LAG_KEY", "EJECTOR_TAG", "W_EQ_FLOOR", "HEAT_CAPACITY_FLOOR_KJK", "FLOW_FLOOR_KGH",
    "DT_FLOOR_S", "FEED_W_UREA_DEFAULT", "FEED_CP_ANCHOR",
    "tic_324001", "pic_329203", "pic_324202", "lic_329505", "FirstEvaporatorLoops",
    "false_air_kgh", "barometric_leg_kgh", "FirstEvaporatorResult", "FirstEvaporator",
]
