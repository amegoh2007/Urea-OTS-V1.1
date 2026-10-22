"""324E003 and 324F003 — the second evaporator and its separator, stage 2 of unit 324.

What this models
----------------
Stage 1's melt, PFD 401 (94.3 % urea, 130 C), drops down 324F001's barometric leg into the
tubes of 324E003, heated by 9-bar steam on the shell, and boils under the deep vacuum of the
324F003 separator. The vapour, PFD 709, goes to the 324E005 condenser, whose vent 324F004 pulls;
the melt, PFD 402 (97.7 % urea, 140 C), drains down a barometric leg to 335P001, and LV-324501A
sends it on to granulation — or, when the 335 melt header backs up past its relief setting,
LV-324501B returns it to 323D002.

    TIC-324002 (melt T)  ->  PIC-329212 (324E003 chest P)  ->  PV-329212 (9-bar steam)
    PIC-324203 (PT-324203, the vacuum at 324E005)  ->  PV-324203 (false air into 324E005)
    LIC-324501 (LT-324501)  ->  LV-324501A (forward) or LV-324501B (recycle, PIC-335201 > 3.8 bar g)

The separator is stage 1's: a well-mixed melt holdup with mass, energy and species balances, and
a vapour space whose pressure is a molar balance between the condenser's vent and the pull:

    dM/dt      = m_feed - m_vap - m_boil - m_402
    M cp dT/dt = m_feed cp_feed (T_feed - T) + UA (Tsat(P_chest) - T) - (m_vap + m_boil) . lambda
    m_vap      = clamp( m_feed - m_urea / w_eq(T, P), 0, m_feed )
    dP/dt      = (R T / V_v)(n_vent(P) - n_pull(P))

the feed's boil-off the water that takes its urea to the melt's equilibrium strength
(`thermo.urea_melt`, V1's TD-016), the holdup's own boil-off what the chest boils out of a melt
heated past its own boiling point (`holdup_boil`); T and P solved together by Picard to 1e-12 in
at most 20 iterations (V1's G7), the melt temperature semi-implicit and the pressure stepped
backward (`core.node.backward_euler_pressure`) against 324E005's anchored saturated vent, its cold
end held at the last full condenser solve's. The holdup's boil-off is evaluated at the trial
pressure inside that backward step — it answers the vacuum by thousands of kg/h per mbar, so
held at the iterate it would ring the fixed point.

The feed is what stage 1's leg delivers this tick, at stage 1's solved temperature and its
holdup's advanced composition, its urea at the strength the leg drains (`leg_urea_strength`).

Where this stage departs from V1 — each a decided divergence, run both ways in
`tests/equivalence/test_second_evaporator_decided_equivalence.py`:

  * **The pull** (handoffs B-57, B-61): 324F004's synthesized map, its capacity anchored on
    PFD 712's 584 kg/h at 0.131 bar a, at its live motive and discharge pressures — where V1 pulls
    584 kg/h x HIC-329606 / 50 x P / 0.131.
  * **The holdup boils** (handoff B-62): past its own boiling point at the vacuum.
  * **The feed's strength is the leg's** (handoff B-63, decided 2026-10-02): the urea basis of
    the feed's boil-off is the strength of the melt stage 1's leg drains, its holdup's, anchored
    on the design — where V1 takes the strength stage 1 made on the tick (``w1_live``), 0 on a
    323P003 trip while the leg still drains 96 % melt, so stage 2 boiled its whole feed as water
    and fell to -83 C in a minute.
  * **The melt** (handoff B-58): the UNIQUAC parameter refitted to the PFD, -85.3 K, the strength
    capped at what the feed's biuret and formaldehyde leave.
  * **The chest on its datasheet** (decision 20): 5.9 bar a, where V1 anchors on 8.1; the stroke
    and the conductance re-derived by V1's own expressions.
  * **The gains on span** (decisions 10, 21): TIC-324002, PIC-329212, PIC-324203 on the DCS
    table's rows per cent of their transmitters' spans, without V1's chest-gain scale.
  * **PV-324203 on its vendor trim** (decision 23): Flowserve's Pos. 56 from its 92.03 % stroke.
  * **The separator's volume with its heads** (decision 33): the drawing's 10.7 m3, where V1
    takes the 7.427 m3 cylinder.
  * **The drain above its heel** (decision 11): LV-324501 drains only the melt above the 1 kg
    floor.
  * **The lost seal admits air** (handoff B-107, decided 2026-10-22): once LT-324501's barometric
    leg uncovers its seal, atmospheric air enters 324F003's vacuum through the drain's trim on the
    blow-through law (`leg_seal`), choked, into 324E005 with the false air — where V1's empty leg
    admits nothing and the vacuum holds.
  * **The fixed point on the energy balance** (handoff B-108, decided 2026-10-22): where V1's
    sweeps never settle — the 1 kg heel under a broken vacuum — the temperature is bracketed and
    solved on the stage's energy balance (`stage_fixed_point`), where V1 leaves the last sweep.

PV-329212 runs on its vendor trim (decision 23's class, decided 2026-10-14): Metso's DN 80
balanced Neldisc, Cv 150, its printed capacities as its curve, from its 54.68 % design stroke, where
V1 runs the chest valve linear from 65.56 % (`steam_chest.ChestValve`).

Sources
-------
V1 ``backend/main.py`` step_sim, "Stage 2 : Evaporator II" (9896-10021), the LV-324501 selector
``route_lv324501`` (2436-2516); the stage's constants (2287-2328, 3388-3402); the species layer.
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
from ureasim.data.control_valves import PV_329212
from ureasim.data.unit_324 import (
    E001_W_UREA_DES,
    E003_LAMBDA_KJKG,
    E003_LAMBDA_STEAM_KJKG,
    E003_LIQUOR,
    E003_OP_DES_PCT,
    PV_329212_OP_DES_PCT,
    PV_329212_XT,
    E003_PCHEST_DES_BARA,
    E003_Q_DES_KW,
    E003_T_DES_C,
    E003_UA_KW,
    E003_W_UREA_DES,
    E005_INLET_DES_KGH,
    F003_FA_DES_KGH,
    F003_LEVEL_SP_PCT,
    F003_M_DES_KG,
    F003_M_FLOOR_KG,
    F003_M_FULL_KG,
    F003_M_TAU_S,
    F003_MW_VAP,
    F003_P_DES_BARA,
    F003_P_MAX_BARA,
    F003_P_MIN_BARA,
    F003_RHO_L,
    F003_VOL_M3,
    LIC_324501_KC,
    LIC_324501_OP_DES_PCT,
    LIC_324501_TI_S,
    LV_324501_SPAN_KGH,
    MELT_A_UREA_WATER_K,
    PIC_324203_KC,
    PIC_324203_TI_S,
    PIC_329212_KC,
    PIC_329212_TI_S,
    PIC_335201_RELIEF_BARG,
    PT_LOOP_MAXIT,
    PT_LOOP_TOL,
    PV_324203_OP_DES_PCT,
    TIC_324002_KC,
    TIC_324002_TI_S,
    V2_DES_KGH,
    W_S401,
)
from ureasim.data.unit_329 import P_MP_BARA
from ureasim.thermo import iapws
from ureasim.thermo.domains import NONVOLATILE
from ureasim.thermo.empirical import urea_soln_cp
from ureasim.thermo.urea_liquor import vapour_y
from ureasim.thermo.urea_melt import equilibrium_urea_fraction, melt_diagnostics, strength_ceiling
from ureasim.units import liquor_stage
from ureasim.units.evaporation.condenser_node import inlet_kmolh
from ureasim.units.evaporation.ejector_map import suction_capacity_kgh
from ureasim.units.evaporation.holdup_boil import holdup_boil
from ureasim.units.evaporation.leg_seal import seal_air_kgh
from ureasim.units.evaporation.melt_route import MeltRoute, melt_route
from ureasim.units.evaporation.stage_fixed_point import bisected_fixed_point
from ureasim.units.evaporation.vacuum_condenser import (
    condensate_back_pressure,
    design_specs,
    vent_kgh_at,
)
from ureasim.units.steam_chest import ChestValve, steam_chest_pressure

#: Key the lagged 9-bar header the chest sees is stored under (V1 ``"324E003_P_9_thermal"``).
P_MP_LAG_KEY = "324E003_P_9_thermal"

#: The ejector that pulls this stage's vacuum, through 324E005's vent.
EJECTOR_TAG = "324F004"

#: V1's numerical floors at this stage: the equilibrium strength [-], the heat capacity of the
#: temperature step [kJ/K], a melt flow [kg/h], the step [s].
W_EQ_FLOOR = 1e-6
HEAT_CAPACITY_FLOOR_KJK = 1e-6
FLOW_FLOOR_KGH = 1e-6
DT_FLOOR_S = 1.0e-9


# ======================================================================================
# The four controllers, seeded as V1 seeds them, on the table's gains per cent of span
# ======================================================================================

def tic_324002() -> ProcessLoop:
    """TIC-324002, the melt-temperature master: its output is the chest-pressure DEMAND [bar a]
    handed to PIC-329212 as a remote set point."""
    return ProcessLoop(
        tag="TIC-324002", Kc=TIC_324002_KC, Ti=TIC_324002_TI_S, Td=0.0, act=+1.0,
        op=E003_PCHEST_DES_BARA, sp=E003_T_DES_C,
        pv=E003_T_DES_C, pv1=E003_T_DES_C, pv2=E003_T_DES_C,
        op_lo=0.0, op_hi=P_MP_BARA, sp_lo=0.0, sp_hi=200.0)


#: PV-329212 as the port runs it, on its vendor's trim (DN 80 balanced Neldisc, Cv 150, from 54.68 %; decided 2026-10-14),
#: and as V1 runs it, linear from V1's stroke — which the equivalence harness keeps.
PV_329212_CHEST = ChestValve(PV_329212_OP_DES_PCT, PV_329212.characteristic, PV_329212_XT)
V1_CHEST = ChestValve(E003_OP_DES_PCT)


def pic_329212(valve: ChestValve = PV_329212_CHEST) -> ProcessLoop:
    """PIC-329212, the 324E003 chest-pressure slave, in CASCADE under TIC-324002: its output is
    the PV-329212 stroke [%], seeded on ``valve``'s design stroke."""
    return ProcessLoop(
        tag="PIC-329212", Kc=PIC_329212_KC, Ti=PIC_329212_TI_S, Td=-1.0, act=+1.0, mode="CAS",
        op=valve.op_des_pct, sp=E003_PCHEST_DES_BARA,
        pv=E003_PCHEST_DES_BARA, pv1=E003_PCHEST_DES_BARA, pv2=E003_PCHEST_DES_BARA,
        op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=P_MP_BARA)


def pic_324203() -> ProcessLoop:
    """PIC-324203, the 324F003 vacuum: reverse acting, a pressure under its set point admits
    more false air. Its output is the PV-324203 stroke [%]."""
    return ProcessLoop(
        tag="PIC-324203", Kc=PIC_324203_KC, Ti=PIC_324203_TI_S, Td=-1.0, act=+1.0,
        op=PV_324203_OP_DES_PCT, sp=F003_P_DES_BARA,
        pv=F003_P_DES_BARA, pv1=F003_P_DES_BARA, pv2=F003_P_DES_BARA,
        op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=1.0)


def lic_324501() -> ProcessLoop:
    """LIC-324501, the melt level: direct acting, its output the stroke [%] the route selector
    hands to LV-324501A or LV-324501B."""
    return ProcessLoop(
        tag="LIC-324501", Kc=LIC_324501_KC, Ti=LIC_324501_TI_S, Td=-1.0, act=-1.0,
        op=LIC_324501_OP_DES_PCT, sp=F003_LEVEL_SP_PCT,
        pv=F003_LEVEL_SP_PCT, pv1=F003_LEVEL_SP_PCT, pv2=F003_LEVEL_SP_PCT,
        op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=100.0)


@dataclass
class SecondEvaporatorLoops:
    """Stage 2's four controllers."""

    tic: ProcessLoop = field(default_factory=tic_324002)
    pic: ProcessLoop = field(default_factory=pic_329212)
    vacuum: ProcessLoop = field(default_factory=pic_324203)
    level: ProcessLoop = field(default_factory=lic_324501)


# ======================================================================================
# The relations
# ======================================================================================

def leg_urea_strength(w_leg: dict) -> float:
    """The urea strength stage 2's feed arrives at [-]: the strength stage 1's leg drains.

    Process utility
    ---------------
    The urea the feed brings, the basis of the water the stage must boil to take it to its
    melt's equilibrium. The leg drains stage 1's held melt, so the feed is at the holdup's
    strength — through a 323P003 trip too, when stage 1 makes nothing and its leg drains the
    96 % melt it holds for ten minutes, which stage 2 then finishes without boiling it as water.

    Equation
    --------
        w_feed = w_401,des + ( w_leg,Urea - w_leg,Urea,des )

    a departure from the design, so the design and every fed steady state stay V1's: stage 1's
    reconciled holdup, 94.3011 % urea, gives the 94.31 % anchor exactly. Clamped to [0, 1] as
    V1 clamps the strength it made.

    Decided 2026-10-02 (handoff B-63, option a). V1 takes ``w1_live``, the feed's urea over the
    melt stage 1 made on the tick (``main.py`` 9855).
    """
    return clamp(E001_W_UREA_DES + (w_leg.get("Urea", 0.0) - W_S401["Urea"]), 0.0, 1.0)


def false_air_kgh(stroke_pct: float) -> float:
    """The false air PV-324203 admits into 324E005 [kg/h].

    Process utility
    ---------------
    PIC-324203's lever: air blanketing the condenser cuts what it condenses and holds the shell
    — and 324F003 behind it — up at its set point against an ejector sized with margin.

    Equation
    --------
        m = m_des . f(h) / f(h_des)      f the vendor's modified equal-percentage trim

    anchored on PFD 783's 21 kg/h at the design stroke Flowserve's Pos. 56 gives it, 92.03 %
    (decision 23's class; V1 ``R324_F003_FA_DES x op / 50``).
    """
    return F003_FA_DES_KGH * (cv_fraction(stroke_pct / 100.0, "mod_equal_pct")
                              / cv_fraction(PV_324203_OP_DES_PCT / 100.0, "mod_equal_pct"))


# ======================================================================================
# The unit
# ======================================================================================

@dataclass(frozen=True)
class SecondEvaporatorResult:
    """Everything stage 2 publishes on one tick."""

    #: The feed — stage 1's leg — [kg/h], [deg C], its urea [kg/h] and specific heat
    #: [kJ/(kg K)].
    feed_kgh: float
    feed_t_c: float
    feed_urea_kgh: float
    feed_cp: float
    #: TIC-324002's chest-pressure demand [bar a], PV-329212's stroke [%], the chest [bar a], the
    #: duty [kW] and the 9-bar steam it condenses [kg/h].
    tic_op_bara: float
    pic_op_pct: float
    chest_p_bara: float
    q_kw: float
    steam_kgh: float
    #: The false air PV-324203 admitted [kg/h] and PIC-324203's new stroke [%].
    false_air_kgh: float
    vacuum_op_pct: float
    #: The melt's ceiling and equilibrium strength [-], the feed's water boiled off and the
    #: holdup's own boil-off (handoff B-62) [kg/h]: PFD 709 is the two together.
    w_max: float
    w_eq: float
    m_vap_kgh: float
    m_boil_kgh: float
    #: 324E005's trial inlet at the solved state [kg/h].
    m_709_kgh: float
    #: The P-T fixed point: iterations, final residual, converged.
    iterations: int
    residual: float
    converged: bool
    #: The model's validity status and P-x residual [bar] at the solved state.
    thermo_validity: str
    thermo_px_residual_bara: float | None
    #: The melt made [kg/h] and its live urea strength [-] — the final product's.
    melt_kgh: float
    w_melt: float
    #: LI-324501 [%], LIC-324501's stroke [%], the route and the two valves' strokes [%].
    level_pct: float
    level_op_pct: float
    recycle_selected: bool
    lv_a_pct: float
    lv_b_pct: float
    #: PFD 402 drained [kg/h] and where it went.
    m_402_kgh: float
    route: MeltRoute
    #: The vapour's mass fractions and the biuret formed [kmol/h].
    y_vap: dict
    xi_kmolh: float
    #: The state after this tick.
    m_kg: float
    t_c: float
    p_bara: float
    w: dict
    #: The air the lost seal admitted [kg/h] (B-107) and all the air into 324E005, the false air
    #: and the seal's [kg/h]; the seal's exactly zero while it holds.
    seal_air_kgh: float = 0.0
    air_in_kgh: float = 0.0
    #: The fixed point solved on the energy balance where the sweeps never settled (B-108).
    bisected: bool = False


@dataclass
class SecondEvaporator:
    """324E003 and 324F003 as one object: the separator's state and its step."""

    #: The melt holdup [kg], TT-324002 [deg C], PT-324203 [bar a] and composition.
    m_kg: float = F003_M_DES_KG
    t_c: float = E003_T_DES_C
    p_bara: float = F003_P_DES_BARA
    w: dict = field(default_factory=lambda: dict(E003_LIQUOR.w_des))
    #: The chest [bar a], the tick before — PIC-329212's PV.
    chest_p_bara: float = E003_PCHEST_DES_BARA
    #: PV-329212's trim (decision 23's class, decided 2026-10-14).
    chest: ChestValve = PV_329212_CHEST
    #: The 9-bar header's lag.
    lag_state: dict = field(default_factory=dict)
    #: The backward species step at a heel (decided 2026-10-17, handoff B-98); False is V1's
    #: explicit step, which the equivalence harnesses keep.
    backward_species: bool = True
    #: Atmospheric air through the lost barometric seal (decided 2026-10-22, handoff B-107); False
    #: is V1's sealed leg, which the equivalence harnesses keep.
    seal_air: bool = True
    #: The temperature on the energy balance where the sweeps never settle (decided 2026-10-22,
    #: handoff B-108); False is V1's last sweep, which the equivalence harnesses keep.
    bisect_fixed_point: bool = True

    def step(self, loops: SecondEvaporatorLoops, feed_kgh: float, feed_t_c: float,
             feed_w: dict, p_mp_bara: float, p_motive_bara: float, p_discharge_bara: float,
             t_vent_324e005_c: float, p_335201_barg: float, dt: float) -> SecondEvaporatorResult:
        """Advance stage 2 by one tick.

        Arguments
        ---------
        feed_kgh, feed_t_c, feed_w
            Stage 1's barometric leg this tick, PFD 401: the flow [kg/h], stage 1's solved
            temperature [deg C] and its holdup's advanced composition
            (`FirstEvaporatorResult.m_401_kgh`, `.t_c`, `.w`); the urea strength is the leg's
            (`leg_urea_strength`, handoff B-63).
        p_mp_bara
            The live 9-bar header [bar a].
        p_motive_bara, p_discharge_bara
            324F004's motive steam at its nozzle (HV-329606's, `ejector_map.nozzle_pressure_bara`;
            4.1 bar a at design) and what it discharges into, 324E006's shell [bar a] (handoff
            B-61; `VacuumTrain.p_324e006_bara`, handoff B-66).
        t_vent_324e005_c
            324E005's cold end from the last full condenser solve — a tear, lagged on the
            tubes' water (`VacuumTrain.cold_end_c`, handoff B-65).
        p_335201_barg
            The 335 melt header [bar g], a battery-limit input: above PIC-335201's relief setting
            LIC-324501's demand goes to LV-324501B.

        The order is V1's: the cascade acts on the state at the top of the tick and the chest is
        solved; the false air is the vacuum stroke the tick before, and PIC-324203 then steps on
        the old pressure; T and P are solved together, the holdup boiling back to its boiling
        point inside the solve; LIC-324501 strokes the drain on the old holdup and the selector
        routes it; the holdup and the species advance.
        """
        feed_w_urea = leg_urea_strength(feed_w)
        urea_in = feed_w_urea * feed_kgh
        cp_feed = urea_soln_cp(feed_w_urea, feed_t_c)
        cp_hold = urea_soln_cp(self.w.get("Urea", E003_W_UREA_DES), self.t_c)
        # The melt can carry no more urea than the feed's non-volatiles leave room for (B-58).
        w_max = strength_ceiling(feed_w.get("Urea", 0.0),
                                 sum(feed_w.get(k, 0.0) for k in NONVOLATILE if k != "Urea"))

        # ----- 324E003: TIC-324002 -> PIC-329212 -> the steam chest ---------------------
        tic_op = loops.tic.step(self.t_c, dt)
        pic_op = loops.pic.step(self.chest_p_bara, dt, cas_sp=tic_op)
        # The header moves in a second; the melt on its own 180 s residence (V1 THERMO-3).
        p_mp_lagged = first_order_lag(self.lag_state, P_MP_LAG_KEY, p_mp_bara, F003_M_TAU_S, dt)
        self.chest_p_bara = steam_chest_pressure(
            pic_op, p_mp_lagged, self.chest.op_des_pct, E003_PCHEST_DES_BARA, E003_UA_KW, self.t_c,
            E003_Q_DES_KW, P_MP_BARA, self.chest_p_bara, characteristic=self.chest.characteristic,
            xt=self.chest.xt)
        t_chest = iapws.tsat_c(self.chest_p_bara)

        # ----- the vacuum: the false air on last tick's stroke, then PIC-324203 ----------
        fa = false_air_kgh(loops.vacuum.op)
        # The lost seal's air (B-107) on the level and LIC-324501's stroke of the tick before,
        # against the vacuum it enters; it reaches 324E005 with the false air.
        air = (seal_air_kgh(self.m_kg / F003_M_FULL_KG * 100.0, loops.level.op, self.p_bara)
               if self.seal_air else 0.0)
        air_in = fa + air
        vac_op = loops.vacuum.step(self.p_bara, dt)

        # ----- T and P together (V1 G7) -----------------------------------------------
        m_pre, t_old, p_old, w_pre = self.m_kg, self.t_c, self.p_bara, self.w
        t_sol, p_sol = t_old, p_old
        v_v = vapour_volume_m3(F003_VOL_M3, m_pre, F003_RHO_L)
        spec = design_specs()["324E005"]
        y_vap = vapour_y(w_pre, E003_LIQUOR.anchor.alpha)
        residual, converged, iterations, m_boil = math.inf, False, 0, 0.0

        def sweep(t_sol: float, p_sol: float) -> tuple[float, float, float]:
            # One G7 sweep from the iterate (T, P): the vacuum's backward step, the temperature
            # the melt boils back to, and the holdup's boil-off.
            q = max(E003_UA_KW * (t_chest - t_sol), 0.0)
            w_eq = equilibrium_urea_fraction(t_sol, p_sol, E003_W_UREA_DES, E003_T_DES_C,
                                             F003_P_DES_BARA, a_urea_water_k=MELT_A_UREA_WATER_K,
                                             w_max=w_max)
            m_vap = clamp(feed_kgh - urea_in / max(w_eq, W_EQ_FLOOR), 0.0, feed_kgh)
            p_wr = (feed_kgh / 3600.0 * cp_feed * (feed_t_c - t_sol)
                    + q - m_vap / 3600.0 * E003_LAMBDA_KJKG)
            # SEMI-IMPLICIT as stage 1 (V1 STIFFNESS): exact at the seed.
            k_cap = feed_kgh / 3600.0 * cp_feed + (E003_UA_KW if q > 0.0 else 0.0)
            c_step = max(m_pre * cp_hold + k_cap * dt, HEAT_CAPACITY_FLOOR_KJK)
            t_step = t_old + p_wr * dt / c_step
            # 324E005's trial inlet before the holdup boils: the design row moved by what the feed
            # boils and by the false air.
            m_709_feed = E005_INLET_DES_KGH + (m_vap - V2_DES_KGH) + (air_in - F003_FA_DES_KGH)

            def boil_at(p: float) -> tuple[float, float]:
                # The held melt boils back to its own boiling point at a trial vacuum (B-62).
                return holdup_boil(
                    t_step, p, m_pre, w_pre, c_step, E003_LAMBDA_KJKG, y_vap.get("Urea", 0.0),
                    F003_M_FLOOR_KG, dt, w_des=E003_LIQUOR.w_des["Urea"], t_des_c=E003_T_DES_C,
                    p_des_bara=F003_P_DES_BARA, a_urea_water_k=MELT_A_UREA_WATER_K)

            n_709 = inlet_kmolh("324E005", m_709_feed + boil_at(p_sol)[0], air_in,
                                F003_FA_DES_KGH)
            bp_709 = condensate_back_pressure(n_709, t_vent_324e005_c)
            t_k = t_sol + ABSOLUTE_ZERO_C

            def dpdt(p: float) -> float:
                # The holdup's boil-off answers the trial pressure inside the implicit step: a
                # deeper vacuum boils more, and more vapour loads the condenser's vent.
                n = inlet_kmolh("324E005", m_709_feed + boil_at(p)[0], air_in, F003_FA_DES_KGH)
                vent = vent_kgh_at(spec, p, t_vent_324e005_c, n, bp_709)
                pull = suction_capacity_kgh(EJECTOR_TAG, p, p_motive_bara, p_discharge_bara)
                return vessel_dpdt(p, t_k, v_v, F003_MW_VAP, vent / F003_MW_VAP,
                                   pull / F003_MW_VAP)

            p_next = backward_euler_pressure(p_old, dt, dpdt, F003_P_MIN_BARA, F003_P_MAX_BARA)
            m_boil, t_next = boil_at(p_next)
            return p_next, t_next, m_boil

        for iterations in range(1, PT_LOOP_MAXIT + 1):
            p_next, t_next, m_boil = sweep(t_sol, p_sol)
            residual = max(abs(p_next - p_sol), abs(t_next - t_sol))
            p_sol, t_sol = p_next, t_next
            if residual <= PT_LOOP_TOL:
                converged = True
                break
        # Sweeps that never settle — the 1 kg heel under a broken vacuum (B-108): the temperature
        # on the stage's energy balance between the coldest of the feed and the melt and the
        # hottest of the chest and the melt.
        bisected = False
        if not converged and self.bisect_fixed_point:
            root = bisected_fixed_point(sweep, min(feed_t_c, t_old), max(t_chest, t_old), p_sol,
                                        PT_LOOP_TOL, PT_LOOP_MAXIT)
            if root is not None:
                p_sol, t_sol, m_boil, residual = (root.p_bara, root.t_c, root.m_boil_kgh,
                                                  root.residual)
                bisected = True
        self.t_c, self.p_bara = t_sol, p_sol

        # ----- the solved state ---------------------------------------------------------
        w_eq = equilibrium_urea_fraction(self.t_c, self.p_bara, E003_W_UREA_DES, E003_T_DES_C,
                                         F003_P_DES_BARA, a_urea_water_k=MELT_A_UREA_WATER_K,
                                         w_max=w_max)
        m_vap = clamp(feed_kgh - urea_in / max(w_eq, W_EQ_FLOOR), 0.0, feed_kgh)
        q = max(E003_UA_KW * (t_chest - self.t_c), 0.0)
        steam = q / E003_LAMBDA_STEAM_KJKG * 3600.0
        validity, px_resid = melt_diagnostics(self.t_c, self.p_bara, w_eq,
                                              a_urea_water_k=MELT_A_UREA_WATER_K)
        melt = max(feed_kgh - m_vap, 0.0)
        w_melt = clamp(urea_in / max(melt, FLOW_FLOOR_KGH), 0.0, 1.0)
        m_709 = E005_INLET_DES_KGH + (m_vap + m_boil - V2_DES_KGH) + (air_in - F003_FA_DES_KGH)

        # ----- LIC-324501 and the LV-324501A / B selector ----------------------------------
        level = clamp(m_pre / F003_M_FULL_KG * 100.0, 0.0, 100.0)
        level_op = loops.level.step(level, dt)
        routed_op = clamp(level_op, 0.0, 100.0)
        recycle = p_335201_barg > PIC_335201_RELIEF_BARG
        lv_a, lv_b = (0.0, routed_op) if recycle else (routed_op, 0.0)
        m_402 = routed_op / 100.0 * LV_324501_SPAN_KGH
        # The drain takes only the melt above the 1 kg floor (decision 11's class).
        m_402_avail = (max(m_pre - F003_M_FLOOR_KG, 0.0) / max(dt, DT_FLOOR_S) * 3600.0
                       + feed_kgh - m_vap - m_boil)
        if m_402 > m_402_avail:
            m_402 = m_402_avail
        route = melt_route(m_402, w_pre, self.t_c, recycle)
        self.m_kg = max(m_pre + (feed_kgh - m_vap - m_boil - m_402) / 3600.0 * dt,
                        F003_M_FLOOR_KG)

        # ----- the species (V1 F-8 / TD-009): the feed's and the holdup's vapour alike ----
        xi = liquor_stage.biuret_extent(E003_LIQUOR, m_pre, w_pre, self.t_c)
        self.w = liquor_stage.advance_species(w_pre, m_pre, self.m_kg, feed_kgh, feed_w,
                                              m_vap + m_boil, y_vap, m_402, xi, dt,
                                              backward=self.backward_species)

        return SecondEvaporatorResult(
            feed_kgh=feed_kgh, feed_t_c=feed_t_c, feed_urea_kgh=urea_in, feed_cp=cp_feed,
            tic_op_bara=tic_op, pic_op_pct=pic_op, chest_p_bara=self.chest_p_bara, q_kw=q,
            steam_kgh=steam, false_air_kgh=fa, vacuum_op_pct=vac_op,
            w_max=w_max, w_eq=w_eq, m_vap_kgh=m_vap, m_boil_kgh=m_boil, m_709_kgh=m_709,
            iterations=iterations, residual=residual, converged=converged,
            thermo_validity=validity, thermo_px_residual_bara=px_resid,
            melt_kgh=melt, w_melt=w_melt, level_pct=level, level_op_pct=level_op,
            recycle_selected=recycle, lv_a_pct=lv_a, lv_b_pct=lv_b, m_402_kgh=m_402, route=route,
            y_vap=y_vap, xi_kmolh=xi, m_kg=self.m_kg, t_c=self.t_c, p_bara=self.p_bara,
            w=self.w, seal_air_kgh=air, air_in_kgh=air_in, bisected=bisected,
        )


__all__ = [
    "P_MP_LAG_KEY", "EJECTOR_TAG", "W_EQ_FLOOR", "HEAT_CAPACITY_FLOOR_KJK", "FLOW_FLOOR_KGH",
    "DT_FLOOR_S",
    "tic_324002", "pic_329212", "pic_324203", "lic_324501", "SecondEvaporatorLoops",
    "leg_urea_strength", "false_air_kgh", "SecondEvaporatorResult",
    "SecondEvaporator",
]
