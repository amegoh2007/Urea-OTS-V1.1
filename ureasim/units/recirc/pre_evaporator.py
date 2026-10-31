"""323E010 and 323F010 — the pre-evaporator and its separator, stage 3 of unit 323.

What this models
----------------
The 323F004 flash liquid, PFD 319 (106 C, 71.7 % urea), lets down through LV-323505 and is
joined by PFD 331, the cold weak urea return from the granulation scrubber (40 C, 44 % urea).
Together they climb the tubes of 323E010, heated by LP steam on the shell, and boil under the
vacuum of the 323F010 separator. The vapour, PFD 790 (12 t/h, nearly all water), leaves the
separator dome through HV-323605 for the 324E002 condenser. The liquid, PFD 317 (99 C, 80 %
urea), drains through a barometric leg into Compartment I of the 323D002 tank.

    TIC-323012 (separator T)  ->  PIC-329208 (323E010 chest P)  ->  PV-329208 (LP steam)
    HIC-323605 (hand valve)   ->  HV-323605 (vapour to 324E002)

The separator has no level control and no controller on its pressure: the level is whatever
the barometric leg leaves, and the pressure is whatever HV-323605 passes against the 324E002
shell. It is a well-mixed liquid holdup with a mass, an energy and a species balance, and a
vapour space with a pressure state of its own:

    dM/dt      = m_319 + m_331 - m_evap - m_boil - m_317
    M cp dT/dt = m_319 cp_319 (T_319 - T) + m_331 cp_331 (40 - T) + Q_E010
                 - (m_evap + m_boil) . lambda
    d(M w)/dt  = the species balance of `units.liquor_stage`, with PFD 331 as a second feed
    dP/dt      = (R T / V_v)(n_evap + n_boil + n_blow - n_pull) + (P / T) dT/dt - (P / V_v) dV_v/dt

The evaporation, energy-limited and capped
------------------------------------------
    q_avail = m_319 cp_319 (T_319 - T) + m_331 cp_331 (40 - T) + Q_E010
    q_relax = M cp (T_bub(w, PT-323204) - T) / tau        [V1: T_bub(w, 0.46), handoff B-22]
    m_evap  = min( m_evap,des . (m_319 + m_331) / (m_319,des + m_331,des),
                   max( m_evap,des . (q_avail - q_relax) / q_evap,des , 0 ) )

On the duty branch the energy balance reduces exactly to M cp dT/dt = q_relax: the liquor
relaxes to its bubble point over its 240 s residence, and the heater's duty turns into vapour
(V1 report TD-014). The first argument caps the overhead at the design fraction of the feed.
At design the two branches are bit-identical and the min() ties. Away from design the cap is
one-sided: less duty evaporates less and dilutes the product, but more duty — or a deeper
vacuum — cannot evaporate more than the design split, so in V1 the surplus heats the liquor
above its own bubble point and the product never passes 80.00 %.

The held liquor boils — decided 2026-10-02 (handoff B-24, B-62's class)
-----------------------------------------------------------------------
Past the bubble point of its own composition at the live PT-323204, the holdup boils: the excess
sensible heat of the temperature step is paid as latent heat, the overhead's composition leaves,
and the liquor holds at its bubble point while it concentrates (`holdup_boil.liquor_boil`). It is
evaluated at the trial pressure inside the pressure step, as the evaporators' is, and its vapour
joins the evaporation in the vapour space, the swell, the drain's heel cap and the species. V1's
two branches are untouched, so at design and below it the stage is V1's; above the design split,
or under a vacuum deeper than the design's, the product concentrates.

On a tick where the holdup boils, at the old pressure, the Jacobian's probe or the linearised
step, the backward step is solved itself (`core.node.backward_euler_pressure`), decided 2026-10-30
(handoff B-122, decision 78's class). The boil-off is zero above the pressure that brings the liquor
to its bubble point and steep below it, and its root can sit on a memo bin's edge, where it stops
answering the pressure: the linearisation carries neither, and its overshoot booked single-tick
flashes of 9-21 t/h in a blow-through surge. A settled state is untouched: there f(P) is 0 and both
steps return P. ``PreEvaporator(exact_boil_step=False)`` is the linearised step on every tick, which
the synthesis loop's harness keeps.

The steam chest and the vacuum: what each is solved on
-----------------------------------------------------
Three pressures meet in this stage, and V1 treats them differently:

  * **The 323E010 chest pressure is solved.** PV-329208 admits steam on the header-to-chest
    law and the tube wall condenses UA . (Tsat(P_chest) - T); `units.steam_chest` finds the
    chest pressure at which the two agree, every tick (V1 report A-5). The chest sees the
    separator only through the liquor temperature T. Its design anchor is PFD 926's and the
    heater datasheet's 2.5 bar a, where V1 anchors on 1.76, a leftover of a retired header —
    decided 2026-09-30 (handoff B-23, closed); the design point is exact on either.
  * **The separator pressure PT-323204 is solved.** It is the vapour-space ODE above,
    integrated on the datasheet's 23.15 m3 shell less the liquid (17.78 m3 of vapour space at
    design), with the vapour leaving on HV-323605's IEC 60534 compressible flow into the
    324E002 shell. The step is backward Euler, linearised about the current pressure — the
    valve pull gives the node a 0.78 s time constant, so an explicit step would ring on a
    1 s tick (V1 reports A-6, D-12).
  * **The bubble point is solved on the live PT-323204 (decided 2026-10-15, handoff B-22).** V1
    evaluates it at the design 0.46 bar a, always, on purpose (its TD-016): feeding the live
    pressure into the bubble point reopened a pressure-evaporation oscillation it had closed on
    unit 324. Since 324E002's cold end is lagged on its tube-side water residence (decision 49,
    B-65) the process engineer decided the live pressure: the liquor relaxes to its bubble point
    at the separator's own vacuum, so a lost vacuum raises the temperature it boils at, closes
    the chest's driving difference and evaporates less, as the plant manual describes. At the
    seed the pressure is the design's, so the design point is V1's to the bit;
    ``PreEvaporator.live_bubble`` False is V1's, which the equivalence harness keeps.

So the live PT-323204 reaches the vapour composition, HV-323605's pull, 323F004's LV-323505
and the temperature the liquor relaxes to, and on V1's leg the drain. Since B-24 the liquor also
boils down to its bubble point at the live pressure when it stands above it — a deeper vacuum.

Where this stage departs from V1 — decided 2026-09-27 (handoff B-29)
--------------------------------------------------------------------
V1 caps the barometric leg at the liquid present plus what arrives (its report A-17), and then
floors the holdup at 1 kg; the cap counts that kilogram as drainable, so a separator on its
floor drains it every tick and the floor restores it — 36 t/h at the 0.1 s step. The port caps
the leg at the liquid above the heel, net of the evaporation:

    m_317 <= (M - 1) / dt . 3600 + m_319 + m_331 - m_evap

so the floor is never drained. The cap binds only within one tick's drain of the heel, so
every V1 scenario above it runs as V1 runs it.

The drain on the separator's own head, decided 2026-10-30 (handoff B-119, option (b)): the
leg's isometric puts N2 1.01 m above the column a full vacuum holds, so the separator drains
through N2 on its own liquid head and its pressure has no part in the drive
(`units.recirc.barometric_leg`); ``PreEvaporator(own_head_leg=False)`` is V1's leg, which the
equivalence harness keeps.

Three more, decided 2026-09-30: the chest's 2.5 bar a anchor above; PIC-329208 on the DCS
table's gain per cent of PT-329208's span, without the chest-gain scale V1 multiplied it by;
and TIC-323012, which has no table row, on its sibling TIC-323007's row on its own spans — V1's
own retune limit-cycles behind the faster slave (As-Built §XL.2).

Two valves on their vendors' trims (decision 23's class): PV-329208 on Metso's Neldisc from
27.22 % (decided 2026-10-15), and HV-323605 on Metso's DN 400 Neldisc from 64.08 %, its printed
capacities as its curve and its normal case's xT 0.38 (decided 2026-10-17), where V1 runs both
linear — HV-323605 from 50 % on the globe valve's xT. HIC-323605 is seeded at its design stroke.
``PreEvaporator(chest=V1_CHEST, vent=V1_VENT)`` is V1's, which the equivalence harness keeps.

The boundaries this stage reads, and when
-----------------------------------------
  * the 323F004 drain, carried down the 323F004 -> 323F010 line, which this stage owns;
  * 323F004's vapour blowing through an uncovered LV-323505, which adds moles to the vapour
    space; the share of HV-323605's flow that is that gas is published for 324E002;
  * the LP header, lagged through the liquor's 240 s residence before it becomes a duty;
  * the 324E002 shell pressure at the start of the tick — an explicit tear, unit 324 advancing
    later in the tick;
  * the previous tick's vapour composition, which sets the vapour molar mass the pressure
    step integrates on — the A-6 tear, seeded with the design vapour.

Source
------
V1 ``backend/main.py`` step_sim, "Stage 3: Pre-evaporator 323F010 + Heater 323E010" (lines
8509-8654), the 323F004 -> 323F010 line transport (8460-8469), ``gravity_outflow_323f010``
and ``hv323605_flow_kgh`` (3657-3716); reports F-11 (the second feed), F-3 (the duty limit),
TD-014 and A-11 (the bubble point), A-5 (the chest), A-6 and D-12 (the vacuum), A-17 (the
barometric leg), F-8 / TD-009 (the species layer). The design data are in
`ureasim.data.unit_323`, each with its source.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ureasim.control.process_loop import ProcessLoop
from ureasim.control.valve import valve_gas_anchored
from ureasim.core.node import backward_euler_pressure, vapour_volume_m3, vessel_dpdt
from ureasim.core.numeric import clamp
from ureasim.core.signal import first_order_lag
from ureasim.core.units_of_measure import ABSOLUTE_ZERO_C
from ureasim.data.design_point import R323_M317_DES, R323_M319_DES
from ureasim.data.control_valves import PV_329208
from ureasim.data.unit_323 import (
    CP_F004_DES,
    CP_F010_DES,
    CP_S331_DES,
    E010_OP_DES_PCT,
    PV_329208_OP_DES_PCT,
    PV_329208_XT,
    E010_PCHEST_DES_BARA,
    E010_Q_DES_KW,
    E010_UA_KW,
    EVAP_LAMBDA_KJKG,
    F010_LIQUOR,
    F010_M_DES_KG,
    F010_M_FLOOR_KG,
    F010_M_FULL_KG,
    F010_M_TAU_S,
    F010_P_BARA,
    F010_P_MAX_BARA,
    F010_P_MIN_BARA,
    F010_T_SP_C,
    F010_VOL_M3,
    HIC_323605_DES_PCT,
    HIC_323605_DES_PCT_V1,
    HV605_CHAR,
    HV605_CHAR_V1,
    HV605_XT,
    M331_DES_KGH,
    M331_T_C,
    MEVAP_DES_KGH,
    P_324E002_DES_BARA,
    PIC_329208_KC,
    PIC_329208_TI_S,
    QEVAP_DES_KW,
    RHO_F010_ANCHOR,
    TIC_323012_KC,
    TIC_323012_SP_HI_C,
    TIC_323012_SP_LO_C,
    TIC_323012_TI_S,
    W_S317,
    W_S331,
)
from ureasim.data.unit_329 import P_LP_BARA
from ureasim.thermo import iapws
from ureasim.thermo.domains import MW
from ureasim.thermo.empirical import urea_soln_rho
from ureasim.thermo.urea_liquor import SOLUTION_SPECIES
from ureasim.units import liquor_stage
from ureasim.units.evaporation.holdup_boil import liquor_boil
from ureasim.units.recirc.barometric_leg import barometric_leg_kgh, own_head_leg_kgh
from ureasim.units.recirc.liquor_line import receive_liquor, stream_cp
from ureasim.units.steam_chest import ChestValve, steam_chest_pressure

#: The 323F004 -> 323F010 line, which this unit owns as the receiving vessel. Source: V1
#: `main.py`, ``_transport_process(s, "323F004_TO_323F010", ...)``.
INLET_ROUTE = "323F004_TO_323F010"

#: Key the lagged LP header pressure the heater sees is stored under. Source: V1 `main.py`,
#: ``_lag1(s.tlag, "323F010_P_LP_thermal", ...)``.
P_LP_LAG_KEY = "323F010_P_LP_thermal"

#: Numerical floors and steps, V1's own literals at this stage: the temperature integration's
#: heat capacity [kJ/K], the liquor density the swell term divides by [kg/m3], the vapour
#: molar sum [-], the time step the drain cap divides by [s], the evaporation the blow-through
#: share divides by [kg/h], and the pressure perturbation of the numerical Jacobian [bar].
HEAT_CAPACITY_FLOOR_KJK = 1e-6
DENSITY_FLOOR_KGM3 = 1e-6
MOLAR_SUM_FLOOR = 1e-12
DT_FLOOR_S = 1.0e-9
VAPOUR_RATE_FLOOR_KGH = 1e-9
JACOBIAN_STEP_BARA = 1.0e-6

#: The design vapour, PFD 790 less its entrained liquor, as the separator's own vapour relation
#: gives it at the design state, and its molar mass [kg/kmol]. Written as the SAME expression
#: the tick evaluates on its pressure tear, so HV-323605's anchor sees an identical float at
#: the seed. Source: V1 `main.py` SOL_F010_Y_DES and R323_F010_MW_VAP_DES.
Y_VAP_DES, _ = liquor_stage.vapour(F010_LIQUOR, W_S317, F010_T_SP_C, F010_P_BARA)
MW_VAP_DES = 1.0 / max(sum(Y_VAP_DES.get(k, 0.0) / MW[k] for k in SOLUTION_SPECIES),
                       MOLAR_SUM_FLOOR)


# ======================================================================================
# The two controllers, seeded as V1 seeds them, on the table's gains per cent of span
# ======================================================================================

def tic_323012() -> ProcessLoop:
    """TIC-323012, the separator-temperature master. Its output is the chest-pressure DEMAND
    [bar a] handed to PIC-329208 as a remote set point."""
    return ProcessLoop(
        tag="TIC-323012", Kc=TIC_323012_KC, Ti=TIC_323012_TI_S, Td=0.0, act=+1.0,
        op=E010_PCHEST_DES_BARA, sp=F010_T_SP_C,
        pv=F010_T_SP_C, pv1=F010_T_SP_C, pv2=F010_T_SP_C,
        op_lo=0.0, op_hi=P_LP_BARA, sp_lo=TIC_323012_SP_LO_C, sp_hi=TIC_323012_SP_HI_C)


#: PV-329208 as the port runs it, on its vendor's trim (Metso's Neldisc from 27.22 %, decided
#: 2026-10-15), and as V1 runs it, linear from V1's stroke — which the equivalence harness keeps.
PV_329208_CHEST = ChestValve(PV_329208_OP_DES_PCT, PV_329208.characteristic, PV_329208_XT)
V1_CHEST = ChestValve(E010_OP_DES_PCT)

#: HV-323605 as the port runs it, on its vendor's trim (Metso's Neldisc from 64.08 %, xT 0.38,
#: decided 2026-10-17), and as V1 runs it, linear from 50 % on the globe valve's xT.
HV_323605_VENT = ChestValve(HIC_323605_DES_PCT, HV605_CHAR, HV605_XT)
V1_VENT = ChestValve(HIC_323605_DES_PCT_V1, HV605_CHAR_V1)


def pic_329208(valve: ChestValve = PV_329208_CHEST) -> ProcessLoop:
    """PIC-329208, the 323E010 chest-pressure slave, in CASCADE under TIC-323012. Its output
    is the PV-329208 stroke [%]."""
    return ProcessLoop(
        tag="PIC-329208", Kc=PIC_329208_KC, Ti=PIC_329208_TI_S,
        Td=0.0, act=+1.0, mode="CAS",
        op=valve.op_des_pct, sp=E010_PCHEST_DES_BARA,
        pv=E010_PCHEST_DES_BARA, pv1=E010_PCHEST_DES_BARA, pv2=E010_PCHEST_DES_BARA,
        op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=P_LP_BARA)


# ======================================================================================
# The relations
# ======================================================================================

def vapour_outlet_kgh(stroke_pct: float, p_separator_bara: float, p_324e002_bara: float,
                      t_c: float, mw_vap: float, valve: ChestValve = HV_323605_VENT) -> float:
    """What HV-323605 passes from the separator dome to the 324E002 shell [kg/h], report D-12.

    Process utility
    ---------------
    The pull on the separator, and therefore what holds its vacuum. 324E002 condenses 99.4 %
    of this flow; the 324F002 ejector moves only the 0.6 % of it that does not condense, and
    reaches the separator only through the shell pressure it holds. So opening HIC-323605, or
    a deeper vacuum in 324E002, drops PT-323204 — the two levers the operator has, and the
    node needs no controller because the pull rises with the separator's own pressure.

    Equation
    --------
    The IEC 60534 compressible law, anchored on PFD 790 at the design stroke across the
    0.46 -> 0.33 bar a design differential, short of the choke:

        w = w_des . Phi(h, P1, P2, T1, M) / Phi(h_des, P1_des, P2_des, T1_des, M_des)

    on ``valve``'s trim: the vendor's Neldisc from 64.08 %, its normal case's xT 0.38 (decision
    23's class), which chokes once the 324E002 shell falls below about 0.30 bar a at the design
    separator; V1's linear trim from 50 % on the globe valve's xT (`V1_VENT`). A reverse
    differential passes nothing. Exactly the design overhead at the design state on either.

    Source: V1 `main.py` `hv323605_flow_kgh`.
    """
    return valve_gas_anchored(
        MEVAP_DES_KGH, stroke_pct / 100.0, p_separator_bara, p_324e002_bara,
        t_c + ABSOLUTE_ZERO_C,
        valve.op_des_pct / 100.0, F010_P_BARA, P_324E002_DES_BARA,
        F010_T_SP_C + ABSOLUTE_ZERO_C,
        mw_vap, characteristic=valve.characteristic, xt=valve.xt, mw_des=MW_VAP_DES)


# ======================================================================================
# The unit
# ======================================================================================

@dataclass(frozen=True)
class PreEvaporatorResult:
    """Everything stage 3 publishes on one tick."""

    #: The 323F004 drain as it arrived through the 323F004 -> 323F010 line
    #: [kg/h], [deg C], [-], [kJ/(kg.K)].
    feed_kgh: float
    feed_t_c: float
    feed_w: dict
    feed_cp: float
    #: PFD 331, the granulation return [kg/h] — a battery-limit constant.
    m_331_kgh: float
    #: TIC-323012's chest-pressure demand [bar a] and PV-329208's stroke [%].
    tic_op_bara: float
    pic_op_pct: float
    #: 323E010 chest pressure [bar a] and duty [kW].
    chest_p_bara: float
    q_e010_kw: float
    #: Heat available to evaporate [kW], the bubble point the holdup relaxes toward [deg C] —
    #: on the DESIGN vacuum — and the duty retained to get there [kW].
    q_avail_kw: float
    t_bub_c: float
    q_relax_kw: float
    #: PFD 790 as generated in the separator [kg/h] — V1's evaporation, and the held liquor's own
    #: boil-off past its bubble point at the live vacuum (handoff B-24) — and PFD 317 down the
    #: barometric leg [kg/h].
    m_evap_kgh: float
    m_boil_kgh: float
    m_317_kgh: float
    #: The state the product departed at — the separator's temperature [deg C] and composition
    #: BEFORE this tick advanced them. 323D002 carries it down its inlet line.
    drain_t_c: float
    drain_w: dict
    #: The vapour molar mass the pressure step integrated on [kg/kmol] — last tick's vapour.
    mw_vap: float
    #: What HV-323605 passed to the 324E002 shell at the pressure the step ended on [kg/h].
    pull_kgh: float
    #: The part of that flow which is LV-323505's blow-through gas, with the gas's mass
    #: fractions, for 324E002's inlet; None while LV-323505 is sealed.
    blowthrough_share: tuple | None
    #: The vapour's mass fractions and the surface they came off; PFD 790 with its entrained
    #: liquor, which is what leaves the species balance.
    y_vap: dict
    vapour_domain: str | None
    y_790: dict
    #: Biuret formed [kmol/h].
    xi_kmolh: float
    #: LI-323F010 [%], on the holdup after this tick. Indication only.
    level_pct: float
    #: The state after this tick.
    m_kg: float
    t_c: float
    p_bara: float
    w: dict


@dataclass
class PreEvaporator:
    """323E010 and 323F010 as one object: the separator's state and its step."""

    #: Liquid holdup [kg], temperature (TT-323010) [deg C], PT-323204 [bar a] and composition.
    m_kg: float = F010_M_DES_KG
    t_c: float = F010_T_SP_C
    p_bara: float = F010_P_BARA
    w: dict = field(default_factory=lambda: dict(W_S317))
    #: 323E010 chest pressure [bar a], the previous tick's — PIC-329208's PV.
    chest_p_bara: float = E010_PCHEST_DES_BARA
    #: PV-329208's trim (decision 108's class, applied 2026-10-15), and HV-323605's (decided
    #: 2026-10-17).
    chest: ChestValve = PV_329208_CHEST
    vent: ChestValve = HV_323605_VENT
    #: The previous tick's vapour mass fractions — the pressure step's molar-mass tear.
    y_vap: dict = field(default_factory=lambda: dict(Y_VAP_DES))
    #: The inlet line's packet FIFO and the LP-header lag.
    line_state: dict = field(default_factory=dict)
    lag_state: dict = field(default_factory=dict)
    #: The bubble point on the live PT-323204 (B-22, decided 2026-10-15); False is V1's, on the
    #: design 0.46 bar a, which the equivalence harness keeps.
    live_bubble: bool = True
    #: The drain on the separator's own head (B-119 (b), decided 2026-10-30); False is V1's
    #: barometric leg, which the equivalence harness keeps.
    own_head_leg: bool = True
    #: The backward step solved itself on a tick where the holdup boils (B-122 (b), decided
    #: 2026-10-30); False is the linearised step on every tick, which the synthesis loop's
    #: harness keeps.
    exact_boil_step: bool = True

    def step(self, tic: ProcessLoop, pic: ProcessLoop,
             drain_kgh: float, drain_t_c: float, drain_w: dict,
             blow_kgh: float, blow_kmolh: float, blow_y: dict | None,
             hic_323605_pct: float, p_lp_bara: float, p_324e002_bara: float,
             dt: float) -> PreEvaporatorResult:
        """Advance stage 3 by one tick.

        Arguments
        ---------
        drain_kgh, drain_t_c, drain_w
            323F004's drain through LV-323505 as it departed on this tick: the flow [kg/h] and
            the drum's temperature [deg C] and composition before the drum advanced
            (`FlashTankResult.m_319_kgh`, `.drain_t_c`, `.drain_w`).
        blow_kgh, blow_kmolh, blow_y
            323F004's vapour blowing through an uncovered LV-323505 into this vapour space
            (`FlashTankResult.blowthrough_kgh`, `.blowthrough_kmolh`, `.blowthrough_y`).
        hic_323605_pct
            HIC-323605, the HV-323605 hand-valve opening [%].
        p_lp_bara
            The live LP steam header [bar a].
        p_324e002_bara
            The 324E002 shell pressure at the start of the tick [bar a] — an explicit tear,
            advanced by unit 324 later in the tick.

        The order is V1's and it is not interchangeable: the controllers, the chest, the
        evaporation and the drain act on the state at the top of the tick; the temperature and
        the holdup advance; the pressure step then sees the NEW temperature, the OLD holdup
        and composition, and last tick's vapour; the vapour composition and the biuret extent
        see the new temperature and pressure and the old composition; the composition
        advances last.
        """
        m_331 = M331_DES_KGH
        cp_331 = stream_cp(W_S331["Urea"], M331_T_C, CP_S331_DES)
        cp_sep = stream_cp(self.w.get("Urea", 0.0), self.t_c, CP_F010_DES)
        # ----- the inlet: one closed packet down the 323F004 -> 323F010 line -----------
        feed = receive_liquor(self.line_state, INLET_ROUTE, drain_kgh, drain_t_c, drain_w,
                              CP_F004_DES, dt)

        # ----- 323E010: TIC-323012 -> PIC-329208 -> the steam chest ---------------------
        tic_op = tic.step(self.t_c, dt)
        pic_op = pic.step(self.chest_p_bara, dt, cas_sp=tic_op)
        # The header responds in a second; the liquor moves on its own 240 s residence, so
        # the heater sees the header through that lag (V1 AUDIT THERMO-3).
        p_lp_lagged = first_order_lag(self.lag_state, P_LP_LAG_KEY, p_lp_bara,
                                      F010_M_TAU_S, dt)
        self.chest_p_bara = steam_chest_pressure(
            pic_op, p_lp_lagged, self.chest.op_des_pct, E010_PCHEST_DES_BARA, E010_UA_KW,
            self.t_c, E010_Q_DES_KW, P_LP_BARA, self.chest_p_bara,
            characteristic=self.chest.characteristic, xt=self.chest.xt)
        # A condensing chest can only ADD heat (report F-10).
        q_e010 = max(E010_UA_KW * (iapws.tsat_c(self.chest_p_bara) - self.t_c), 0.0)

        # ----- the evaporation: energy-limited, capped at the design split --------------
        # The two feeds' sensible terms and the heater. PFD 331 arrives at 40 C against a
        # 99 C boil, so it is a heat SINK the heater also pays for.
        q_avail = (feed.m_kgh / 3600.0 * feed.cp_kj_kgk * (feed.t_c - self.t_c)
                   + m_331 / 3600.0 * cp_331 * (M331_T_C - self.t_c)
                   + q_e010)
        # The bubble point on the live PT-323204 (decided 2026-10-15, handoff B-22); V1's on the
        # design vacuum (its TD-016) where ``live_bubble`` is off.
        t_bub = liquor_stage.bubble_t(F010_LIQUOR, self.w,
                                      self.p_bara if self.live_bubble else F010_P_BARA)
        q_relax = self.m_kg * cp_sep * (t_bub - self.t_c) / F010_M_TAU_S
        m_evap = min(MEVAP_DES_KGH * ((feed.m_kgh + m_331) / (R323_M319_DES + M331_DES_KGH)),
                     max(MEVAP_DES_KGH * ((q_avail - q_relax) / QEVAP_DES_KW), 0.0))

        # ----- the barometric leg --------------------------------------------------------
        m_317 = (own_head_leg_kgh(self.m_kg) if self.own_head_leg
                 else barometric_leg_kgh(self.m_kg, self.p_bara))
        # At M = 0 V1's leg is still driven by the separator's own pressure, and the engine
        # has no two-phase leg: cap the drain at the liquid above the 1 kg heel plus what
        # arrives this tick, net of the evaporation (decided divergence, handoff B-29). V1
        # counted the floor's kilogram as drainable, so the floor restored it every tick. The
        # evaporation never exceeds the design fraction of the feed, so the cap is never
        # negative. Inert at every normal state, including the seed.
        m_317_avail = (max(self.m_kg - F010_M_FLOOR_KG, 0.0) / max(dt, DT_FLOOR_S) * 3600.0
                       + feed.m_kgh + m_331 - m_evap)
        if m_317 > m_317_avail:
            m_317 = m_317_avail

        # ----- the balances ------------------------------------------------------------
        p_net = q_avail - m_evap / 3600.0 * EVAP_LAMBDA_KJKG
        m_pre, t_pre, w_pre = self.m_kg, self.t_c, self.w
        # SEMI-IMPLICIT in the T-dependent terms whose heat-capacity rate belongs to a FLOW or
        # to the heater wall — the two feeds, and the chest while it is still driving in — so
        # they keep their grip after the inventory has gone. Exactly the explicit step at the
        # seed, where p_net is 0.
        k_cap = (feed.m_kgh / 3600.0 * feed.cp_kj_kgk + m_331 / 3600.0 * cp_331
                 + (E010_UA_KW if q_e010 > 0.0 else 0.0))
        c_step = max(m_pre * cp_sep + k_cap * dt, HEAT_CAPACITY_FLOOR_KJK)
        self.t_c = t_pre + p_net * dt / c_step
        t_step = self.t_c

        # ----- PT-323204: the separator's vapour space ----------------------------------
        # Moles, not mass (1 kg/s of steam and of CO2 are not the same dP/dt), the thermal
        # term, and level swell on the datasheet shell. The molar mass is last tick's vapour.
        mw_vap = 1.0 / max(sum(self.y_vap.get(k, 0.0) / MW[k] for k in SOLUTION_SPECIES),
                           MOLAR_SUM_FLOOR)
        rho = urea_soln_rho(w_pre.get("Urea", 0.0), self.t_c, RHO_F010_ANCHOR)
        v_v = vapour_volume_m3(F010_VOL_M3, m_pre, rho)
        dmdt = (feed.m_kgh + m_331 - m_evap - m_317) / 3600.0
        dtdt = p_net / max(m_pre * cp_sep, HEAT_CAPACITY_FLOOR_KJK)
        t_k = self.t_c + ABSOLUTE_ZERO_C
        # The held liquor boils past its own bubble point at a trial vacuum (handoff B-24),
        # leaving at last tick's overhead composition — the vapour tear, with its entrainment.
        f_ent = F010_LIQUOR.anchor.entrain
        y_boil = {k: (1.0 - f_ent) * self.y_vap.get(k, 0.0) + f_ent * w_pre.get(k, 0.0)
                  for k in SOLUTION_SPECIES}

        def boil_at(p: float) -> tuple[float, float]:
            return liquor_boil(t_step, m_pre, w_pre, c_step, EVAP_LAMBDA_KJKG, y_boil,
                               F010_M_FLOOR_KG, dt,
                               lambda w: liquor_stage.bubble_t(F010_LIQUOR, w, p))

        def dpdt(p: float) -> float:
            # A deeper trial vacuum boils more, and the vapour fills the space it leaves.
            boil = boil_at(p)[0]
            pull_p = vapour_outlet_kgh(hic_323605_pct, p, p_324e002_bara, self.t_c, mw_vap,
                                       self.vent)
            return vessel_dpdt(p, t_k, v_v, mw_vap,
                               (m_evap + boil) / mw_vap + blow_kmolh, pull_p / mw_vap,
                               dtdt_k_s=dtdt,
                               dvvdt_m3_s=-(dmdt - boil / 3600.0) / max(rho, DENSITY_FLOOR_KGM3))

        # Backward Euler, linearised about the current pressure: P' = P + f dt / (1 - J dt),
        # J = df/dP taken numerically on the same valve law. 1/(1 - J dt) is in (0, 1] for any
        # dt; a positive J is non-physical and is clipped to 0, the explicit step. f is a
        # literal 0.0 at the seed, so the design pressure cannot move.
        p_old = self.p_bara
        f_old = dpdt(p_old)
        jac = min((dpdt(p_old + JACOBIAN_STEP_BARA) - f_old) / JACOBIAN_STEP_BARA, 0.0)
        p_new = p_old + f_old * dt / (1.0 - jac * dt)
        # Where the holdup boils the linearisation cannot carry the boil's kink at the bubble
        # point, nor a root pinned on a memo bin's edge: solve the backward step itself, between
        # the old pressure and the explicit step, where a falling f puts its root (B-122).
        if self.exact_boil_step and any(boil_at(p)[0] > 0.0
                                        for p in (p_old, p_old + JACOBIAN_STEP_BARA, p_new)):
            p_exp = p_old + f_old * dt
            p_new = backward_euler_pressure(
                p_old, dt, dpdt, clamp(min(p_old, p_exp), F010_P_MIN_BARA, F010_P_MAX_BARA),
                clamp(max(p_old, p_exp), F010_P_MIN_BARA, F010_P_MAX_BARA))
        self.p_bara = clamp(p_new, F010_P_MIN_BARA, F010_P_MAX_BARA)
        # The flow the step actually passed, at the pressure it ended on: what 324E002 takes.
        pull = vapour_outlet_kgh(hic_323605_pct, self.p_bara, p_324e002_bara, self.t_c, mw_vap,
                                 self.vent)
        # The holdup boils at the pressure the step ended on; the drain takes only the liquor
        # above the heel that the boil-off leaves (decision 11's class).
        m_boil, self.t_c = boil_at(self.p_bara)
        if m_317 > m_317_avail - m_boil:
            m_317 = m_317_avail - m_boil
        self.m_kg = max(m_pre + (feed.m_kgh + m_331 - m_evap - m_boil - m_317) / 3600.0 * dt,
                        F010_M_FLOOR_KG)
        # The share of it that is LV-323505's blow-through gas — the dome mixes on a
        # sub-second time constant, so the share is by mass rate.
        share = None
        if blow_y is not None and blow_kgh > 0.0:
            share = (pull * blow_kgh / max(m_evap + m_boil + blow_kgh, VAPOUR_RATE_FLOOR_KGH),
                     blow_y)

        # ----- the vapour and the species ------------------------------------------------
        y_vap, domain = liquor_stage.vapour(F010_LIQUOR, w_pre, self.t_c, self.p_bara)
        self.y_vap = y_vap
        # PFD 790 is vapour PLUS entrained liquor at the vessel's own composition (its 0.14
        # mol % urea), a fixed fraction of the overhead. Its latent heat is charged on the
        # whole of m_evap above: 0.61 % of the overhead, inside the uncertainty of lambda.
        y_790 = {k: (1.0 - f_ent) * y_vap.get(k, 0.0) + f_ent * w_pre.get(k, 0.0)
                 for k in SOLUTION_SPECIES}
        xi = liquor_stage.biuret_extent(F010_LIQUOR, m_pre, w_pre, self.t_c)
        self.w = liquor_stage.advance_species(w_pre, m_pre, self.m_kg, feed.m_kgh, feed.w,
                                              m_evap + m_boil, y_790, m_317, xi, dt,
                                              m_in2_kgh=m_331, w_in2=W_S331)

        return PreEvaporatorResult(
            feed_kgh=feed.m_kgh, feed_t_c=feed.t_c, feed_w=feed.w, feed_cp=feed.cp_kj_kgk,
            m_331_kgh=m_331, tic_op_bara=tic_op, pic_op_pct=pic_op,
            chest_p_bara=self.chest_p_bara, q_e010_kw=q_e010,
            q_avail_kw=q_avail, t_bub_c=t_bub, q_relax_kw=q_relax,
            m_evap_kgh=m_evap, m_boil_kgh=m_boil, m_317_kgh=m_317, drain_t_c=t_pre,
            drain_w=w_pre,
            mw_vap=mw_vap, pull_kgh=pull, blowthrough_share=share,
            y_vap=y_vap, vapour_domain=domain, y_790=y_790, xi_kmolh=xi,
            level_pct=self.m_kg / F010_M_FULL_KG * 100.0,
            m_kg=self.m_kg, t_c=self.t_c, p_bara=self.p_bara, w=self.w,
        )


__all__ = [
    "INLET_ROUTE", "P_LP_LAG_KEY",
    "HEAT_CAPACITY_FLOOR_KJK", "DENSITY_FLOOR_KGM3", "MOLAR_SUM_FLOOR", "DT_FLOOR_S",
    "VAPOUR_RATE_FLOOR_KGH", "JACOBIAN_STEP_BARA",
    "Y_VAP_DES", "MW_VAP_DES", "HV_323605_VENT", "V1_VENT",
    "tic_323012", "pic_329208",
    "barometric_leg_kgh", "vapour_outlet_kgh",
    "PreEvaporatorResult", "PreEvaporator",
]
