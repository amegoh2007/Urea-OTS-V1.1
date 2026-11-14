"""328C002 — desorber I, the upper section of the desorption tower.

What this models
----------------
328C002 strips the ammonia and carbon dioxide out of the ammonia water 328D003 sends it. Four
streams enter: the feed 738, which 328E007 has heated to 114 C; the reflux 775 from 328D001;
and the two hot overheads of the sections below it, 748 from the hydrolyser and 750 from
328C004, which condense in it and are its stripping vapour. What they strip leaves overhead as
737, through 328E004 to the reflux drum; the stripped liquor leaves the sump as 743 through
328P006 and LV-328503 toward 328E021 and the hydrolyser.

    738 + 775 + 748 + 750 --> 328C002 --737--> 328E004 --> 328D001
                                 |
                                 +--743--> 328P006 --> LV-328503 --> 328E021 --> 328C003

The column is one node: one liquid holdup, one pressure, one temperature, one species vector.

**The boil-up** is what the net duty can boil, an anchored ratio on the design duty:

    q    = sum_in m cp (T_in - T) / 3600 + m_748 lambda_748 / 3600 + m_750 lambda_750 / 3600
    gen  = m_737,des . q / Q_des                  (negative: the duty condenses vapour, B-42)

with cp water's at the live temperature (`aqueous_cp` on 4.0 at 139 C), the two latent heats
2000 and 2100 kJ/kg, and the reflux, 748 and 750 charged at their producers' live temperatures
as departures from the producers' designs, 61, 188 and 140 C at design (handoff B-31, below). 738
comes at 328E007's live outlet.

**The overhead** is not the boil-up. 737 is what the overhead line passes to 328D001 on the
IEC 60534 compressible law, anchored on the design duty, with the stroke fixed at 1 (a line,
not a throttle), the inlet at the live column top — the bottoms less the design 22 K — and the
live molar mass of last tick's vapour:

    m_737 = valve_gas_anchored(m_737,des, 1, P, P_D001, T - 22 + 273.15, ... , M_737)

**The pressure** integrates the imbalance on the free volume, on the old holdup and the
temperature change of the tick before (a tear, zero at the seed) (V1 report A-6):

    dP/dt = (R T / V_v)(gen - m_737) / M_737 + (P / T) dT/dt - (P / V_v) dV_v/dt   [core.node]

**The temperature** is water's bubble point at the bottom node, the overhead pressure plus a
lumped offset back-solved on the PFD's 139 C bottoms:

    T = T_sat,water(P + dP_col)

So duty sets boil-up, boil-up sets pressure, and pressure sets temperature: a stripping-vapour
loss lowers the column's pressure and its temperature with it (V1 AUDIT C1). The column carries
no energy balance of its own.

**The holdup** is the liquid's: it loses what boils, and gains what a negative boil-up
condenses; what the overhead line does not pass stays in the head space, where the pressure
integral carries it (decision 24):

    dM/dt = m_738 + m_748 + m_750 + m_775 - gen - m_743

**The level** is M / M_des x 50. LIC-328503 strokes LV-328503 on the IEC 60534 liquid law: its
inlet is 328P006's discharge — the live column pressure, the live liquid head over the fixed
11.73 m drop to the pump, and the pump's rated 19.7 bar — and its outlet the hydrolyser's live
pressure; its choke the liquor's own bubble pressure at the bottoms' temperature (B-43).

**The species** step implicitly on the stage's live Kremser volatility (`desorber_stage`), with
738 and 775 at their PFD rows (328D003 and 328D001 carry no species) and 748 and 750 at the
vapours the two sections below delivered last tick.

Where this unit departs from V1
-------------------------------
Five changes, each inert at the design point; every V1 scenario that reaches none of the last
four runs as V1 runs it with the first.

Decided by the process engineer on 2026-09-30:

  * **The liquid pays what boils (decision 24).** V1 takes the overhead line's flow out of the
    liquid while the pressure integral fills the head space with the boil-up: in any transient
    where the two differ, vapour is counted twice or not at all. Here the liquid loses the
    boil-up — and gains the condensate of a negative one — and the head space holds the
    difference; liquid and vapour close together. Decided on 328C003, retro-fitted here.
  * **A negative duty condenses vapour (handoff B-42).** V1 clamps the boil-up at zero. With
    748 and 750 lost the net duty goes negative, the overhead empties the vapour space to
    328D001's pressure, and the bottoms stay at water's bubble point there, 128.5 C — where the
    two liquid feeds mix at 111.3 C: 622.5 kW made, every hour. Here the negative boil-up
    condenses vapour, and the pressure and its bubble point fall until the duty balances —
    111.3 C at 1.48 bar a within five minutes. The overhead line passes nothing backwards, so
    328D001 does not feed the column below its pressure.
  * **LV-328503's flash choke reads the liquor at the valve (handoff B-43).** V1 reads the
    liquor's bubble pressure at 328E021's cold OUTLET, 190 C. Uhde's loop summary puts the valve
    upstream of the exchanger, its inlet at 140 C and its design temperature 170 C, so the choke
    here reads the bottoms. On V1, halving 750 doubles the bottoms' ammonia in 30 s, the bubble
    pressure at 190 C passes the pump's discharge, the valve chokes, and the column fills to
    613 % in an hour; here the level holds 50 %.

Applied as decision 11's standing rule:

  * **328P006 cannot pump an empty column.** V1 draws LV-328503's flow whatever the sump holds
    and its 1 kg floor makes up the difference. Here 743 is capped at the liquid above a 1 kg
    heel plus what arrives on the tick, net of what boils:

        m_743 <= (M - 1) / dt . 3600 + (m_in - gen)

    and the loss of suction is flagged. The boil-up is not capped: a column that boils more
    than everything that arrives still reaches the floor, as the flash condenser's vent does
    (handoff B-30).
  * **A full column overflows.** V1's holdup has no ceiling: with LV-328503 held at 20 % the
    shell is full after 1886 s and V1 goes on filling past it (on V1's choke, B-43, halving 750
    put 19.5 t into the 12.8 m3 shell in an hour, LI-328503 reading 613 %). Here the liquid
    above the shell's capacity, 11 988 kg, leaves as an overflow stream at the bottoms' state —
    on the plant, the liquid a flooded column carries out through its overhead line to 328E004
    and 328D001, which takes it (`reflux_drum`, decided 2026-09-30, decision 30). The pressure's
    swell term sees the holdup the overflow leaves.

A sixth, decided 2026-10-16 (handoff B-31): **the reflux and the two overheads at their producers'
live temperatures.** V1 charges 775 at 61 C, 748 at 188 C and 750 at 140 C whatever 328D001,
328C003 and 328C004 do, with the latent heats constant, so their temperatures set the boil-up.
Each is charged here as its departure from its producer's design,

    T_in = T_in,des + (T_producer - T_producer,des)

on the drum's, the hydrolyser's and 328C004's temperatures of the tick before (all three step
after this unit). At the design seed each is V1's to the bit; ``live_inlets=False`` is V1's, which
the plant-level harness keeps.

A seventh, decided 2026-10-22 (decision 150, decision 23's class): **LV-328503 on Fisher's trim**
(UD-MR-G00-DZ-0014, item 022) — equal percentage, rated Cv 82.2, FL 0.819, from 56.95 %, where its
rated Cv passes PFD 743 on the normal case; V1 runs it linear from 50 % on the IEC FL 0.90, the
sheet not having been found. Exactly PFD 743 at the design stroke either way.

The boundaries this unit reads, and when
----------------------------------------
  * 738 and its temperature, from 328E007 — this tick's (`DesorberHeatExchangerResult`);
  * 748 and 750 with their vapours, and 775 — one tick late, the tears ``R328_748``,
    ``R328_750`` and ``R328_775``: 328C003, 328C004 and 328D001 step after this unit;
  * the hydrolyser's pressure and 328D001's pressure — their states at the top of the tick, for
    the same reason. (V1 also reads the hydrolyser's temperature, for the 190 C choke B-43
    retires.) The drum's, the hydrolyser's and 328C004's temperatures, likewise (B-31).

It publishes 743, which 328C003 takes the same tick; 737 and its vapour, which 328D001 takes the
same tick; and its pressure and temperature, which 328D001, 328C003 and 328C004 read.

Source
------
V1 ``backend/main.py`` step_sim, "Stage 3 : 328C002 Desorber-I" (lines 8965-9060), the
aqueous cp (8828) and the tear reads (8838-8840); the seeds in ``State.__init__`` (6639-6640,
6841-6843, 6859-6869, 7089-7092); the telemetry block (10750-10766). The design data are in
`ureasim.data.unit_328c002` and `ureasim.data.desorption_train`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ureasim.control.process_loop import ProcessLoop
from ureasim.control.valve import valve_gas_anchored, valve_liquid_anchored
from ureasim.core.node import vapour_volume_m3, vessel_dpdt
from ureasim.core.relief import GasReliefValve, SafetyValve, psv_area_from_rated_m2
from ureasim.core.units_of_measure import ABSOLUTE_ZERO_C, G_ACC, PA_PER_BAR
from ureasim.data.desorption_train import (
    C002_M737_DES_KGH,
    C002_M743_DES_KGH,
    C002_P_TOP_BARA,
    C002_T748_C,
    C002_T750_C,
    C002_T_BOT_C,
    C002_T_TOP_C,
    C003_P_BARA,
    C004_T_C,
    CP_DESORPTION,
    D001_P_BARA,
    D001_T_C,
    DES_C002,
    W_S738,
    W_S743,
    W_S775,
)
from ureasim.data.unit_328c002 import (
    C002_AREA_M2,
    C002_DP_COL_BAR,
    C002_DT_TOP_K,
    C002_FULL_KG,
    C002_LAM748_KJKG,
    C002_LAM750_KJKG,
    C002_LEVEL_DES_PCT,
    C002_M_DES_KG,
    C002_M_FLOOR_KG,
    C002_MW737_DES,
    C002_Q_DES_KW,
    C002_RHO_KGM3,
    C002_STAGE,
    C002_VOL_M3,
    LIC_328503_KC,
    LIC_328503_SP_PCT,
    LIC_328503_TI_S,
    LV503_CHARACTERISTIC,
    LV503_FL,
    LV503_OP_DES_PCT,
    LV503_P1_DES_BARA,
    LV503_PV_DES_BARA,
    P006_DP_PUMP_BAR,
    P006_Z_DROP_M,
    SV32850_CAP_KGH,
    SV32850_COUNT,
    SV32850_K,
    SV32850_MW_REL,
    SV32850_P_REL_BARA,
    SV32850_RESEAT_BARA,
    SV32850_SET_BARA,
    SV32850_T_REL_K,
    SV32850_Z_REL,
)
from ureasim.data.unit_328c003 import C003_T_C
from ureasim.thermo import iapws
from ureasim.thermo.ammonia_water import liquor_pv_bara
from ureasim.thermo.domains import MW
from ureasim.thermo.empirical import aqueous_cp
from ureasim.thermo.urea_liquor import SOLUTION_SPECIES
from ureasim.units.desorption.desorber_stage import advance_species, alpha_live

#: Floor on the column pressure [bar a]: V1's ``max(..., 0.1)``.
C002_P_FLOOR_BARA = 0.1

#: Floors on the vapour's inverse molar mass [kmol/kg] and on the step in the heel cap [s]. V1's.
INV_MW_FLOOR = 1e-12
DT_FLOOR_S = 1e-9


def lic_328503() -> ProcessLoop:
    """LIC-328503, the bottoms level. DIRECT acting: a level above set point opens LV-328503."""
    return ProcessLoop(
        tag="LIC-328503", Kc=LIC_328503_KC, Ti=LIC_328503_TI_S, Td=0.0, act=-1.0,
        op=LV503_OP_DES_PCT, sp=LIC_328503_SP_PCT, pv=LIC_328503_SP_PCT,
        pv1=LIC_328503_SP_PCT, pv2=LIC_328503_SP_PCT,
        op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=100.0)


def sv_32850() -> GasReliefValve:
    """SV32850 and SV32851, the column's two safety valves, shut: set 6.01 bar a, reseating at
    5.51, each orifice back-solved from its certified 25 000 kg/h at 6.51 bar a (B-47)."""
    return GasReliefValve(
        valve=SafetyValve("SV32850/51", SV32850_SET_BARA, SV32850_RESEAT_BARA),
        area_m2=psv_area_from_rated_m2(SV32850_CAP_KGH, SV32850_P_REL_BARA, SV32850_T_REL_K,
                                       SV32850_MW_REL, k=SV32850_K, z=SV32850_Z_REL),
        k=SV32850_K, count=SV32850_COUNT)


@dataclass(frozen=True)
class FirstDesorberResult:
    """Everything 328C002 publishes on one tick."""

    #: The column's whole inflow [kg/h]: 738 + 748 + 750 + 775.
    in_kgh: float
    #: LI-328503 before the tick — the level LIC-328503 acted on [%] — and its output [%].
    lic_pv_pct: float
    lic_op_pct: float
    #: 743, the bottoms 328P006 delivers to the hydrolyser [kg/h], and True when it was capped
    #: at the heel (decision 11).
    m_743_kgh: float
    suction_lost: bool
    #: The net duty [kW], the boil-up it can raise [kg/h] — negative where the duty condenses
    #: vapour — and 737, the overhead the line passes to 328D001 [kg/h].
    q_kw: float
    gen_kgh: float
    m_737_kgh: float
    #: The liquid above the full shell, carried out overhead [kg/h], at the bottoms' temperature
    #: and composition after the tick (decision 11); zero until the column is full.
    m_overflow_kgh: float
    #: What SV32850 and SV32851 vent of the column's vapour, at y_737, to atmosphere [kg/h], and
    #: True while they are lifted (B-47).
    m_relief_kgh: float
    relief_lifted: bool
    #: The state after this tick: pressure [bar a], bottoms temperature (TT-328007) [deg C],
    #: the column top (TT-328008) [deg C], holdup [kg] and LI-328503 on it [%].
    p_bara: float
    t_c: float
    t_top_c: float
    m_kg: float
    level_pct: float
    #: The bottoms' and the overhead's compositions after this tick [mass fraction].
    w: dict
    y_737: dict
    #: The VLE domain the live volatility was evaluated in, or None off the fitted surface.
    vle_domain: str | None


@dataclass
class FirstDesorber:
    """328C002 as one node: holdup, pressure, temperature, species and the step."""

    #: Liquid holdup [kg], bottoms temperature [deg C] and the temperature on the tick before —
    #: the pressure step's thermal term, a tear, zero at the seed — and the column pressure
    #: [bar a].
    m_kg: float = C002_M_DES_KG
    t_c: float = C002_T_BOT_C
    t_prev_c: float = C002_T_BOT_C
    p_bara: float = C002_P_TOP_BARA
    #: The bottoms' composition, seeded on PFD 743, and the overhead's, seeded on the back-solved
    #: design vapour — the gas law carries sqrt(M), so the first tick needs the design vapour.
    w: dict = field(default_factory=lambda: dict(W_S743))
    y_737: dict = field(default_factory=lambda: dict(DES_C002.y))
    #: SV32850 and SV32851 and their lift (B-47).
    sv_32850: GasReliefValve = field(default_factory=sv_32850)
    #: The reflux and the two overheads at their producers' live temperatures, as departures from
    #: the producers' designs (decided 2026-10-16, handoff B-31); False is V1's design values.
    live_inlets: bool = True

    def step(self, lic: ProcessLoop, m_738_kgh: float, t_738_c: float,
             m_748_kgh: float, y_748: dict, m_750_kgh: float, y_750: dict, m_775_kgh: float,
             p_c003_bara: float, p_d001_bara: float, dt: float, *, t_d001_c: float = D001_T_C,
             t_c003_c: float = C003_T_C, t_c004_c: float = C004_T_C,
             pump_running: bool = True) -> FirstDesorberResult:
        """Advance 328C002 by one tick.

        Arguments
        ---------
        m_738_kgh, t_738_c
            The feed and its temperature, from 328E007 on this tick.
        m_748_kgh, y_748, m_750_kgh, y_750, m_775_kgh
            The hydrolyser's and 328C004's overheads with their vapours, and the reflux —
            each as its unit delivered it on the tick before.
        p_c003_bara, p_d001_bara
            The hydrolyser's pressure and 328D001's, at the top of the tick.
        t_d001_c, t_c003_c, t_c004_c
            328D001's, the hydrolyser's and 328C004's temperatures at the top of the tick, the
            producers of 775, 748 and 750 (decided 2026-10-16, handoff B-31). Each defaults to
            its producer's design, so an inlet at design is V1's.

        The order is V1's: the level loop acts on the state at the top of the tick; the
        bottoms, the duty, the boil-up and the overhead follow; the pressure steps on the OLD
        holdup and on the temperature change of the tick BEFORE; the temperature, the holdup
        and the species advance last.
        """
        t_pre = self.t_c
        cp = aqueous_cp(CP_DESORPTION, C002_T_BOT_C, t_pre)
        m_in = m_738_kgh + m_748_kgh + m_750_kgh + m_775_kgh
        level = self.m_kg / C002_M_DES_KG * C002_LEVEL_DES_PCT
        # The overhead's live molar mass, off last tick's vapour: a tear, closed at the end.
        mw_737 = 1.0 / max(sum(self.y_737.get(k, 0.0) / MW[k] for k in SOLUTION_SPECIES),
                           INV_MW_FLOOR)

        # ----- LIC-328503 -> LV-328503, on 328P006's discharge ---------------------------
        lic_op = lic.step(level, dt)
        head_m = self.m_kg / (C002_RHO_KGM3 * C002_AREA_M2)
        p1 = (self.p_bara
              + C002_RHO_KGM3 * G_ACC * (head_m + P006_Z_DROP_M) / PA_PER_BAR
              + P006_DP_PUMP_BAR)
        # The liquor reaches the valve at the bottoms' temperature: 328E021 heats it downstream
        # (decided divergence, handoff B-43; V1 reads 328E021's cold outlet). The valve runs
        # Fisher's equal-percentage trim and FL (decision 150; V1 linear from 50 %).
        m_743 = valve_liquid_anchored(
            C002_M743_DES_KGH, lic_op / 100.0, p1, p_c003_bara, C002_RHO_KGM3,
            LV503_OP_DES_PCT / 100.0, LV503_P1_DES_BARA, C003_P_BARA, C002_RHO_KGM3,
            characteristic=LV503_CHARACTERISTIC, fl=LV503_FL,
            pv_bara=liquor_pv_bara(self.w, t_pre), pv_des_bara=LV503_PV_DES_BARA)
        # 328P006A and B both stopped: LV-328503 has no pump head and passes nothing (decision 227).
        m_743 *= 1.0 if pump_running else 0.0

        # ----- the duty and the boil-up: energy-limited, anchored on the design duty. A
        # negative duty condenses vapour (decided divergence, handoff B-42; V1 clamps at 0) -----
        # 775, 748 and 750 at their producers' live temperatures, as departures from the
        # producers' designs: zero at design, so V1's to the bit there (B-31, 2026-10-16).
        if self.live_inlets:
            t_775 = D001_T_C + (t_d001_c - D001_T_C)
            t_748 = C002_T748_C + (t_c003_c - C003_T_C)
            t_750 = C002_T750_C + (t_c004_c - C004_T_C)
        else:
            t_775, t_748, t_750 = D001_T_C, C002_T748_C, C002_T750_C
        sens = ((m_738_kgh * (t_738_c - t_pre)
                 + m_775_kgh * (t_775 - t_pre)
                 + m_748_kgh * (t_748 - t_pre)
                 + m_750_kgh * (t_750 - t_pre)) / 3600.0 * cp)
        q = (sens + m_748_kgh / 3600.0 * C002_LAM748_KJKG
             + m_750_kgh / 3600.0 * C002_LAM750_KJKG)
        gen = C002_M737_DES_KGH * (q / C002_Q_DES_KW)

        # ----- 737: what the overhead line passes to 328D001 (V1 report D-2) ---------------
        m_737 = valve_gas_anchored(
            C002_M737_DES_KGH, 1.0, self.p_bara, p_d001_bara,
            t_pre - C002_DT_TOP_K + ABSOLUTE_ZERO_C,
            1.0, C002_P_TOP_BARA, D001_P_BARA, C002_T_TOP_C + ABSOLUTE_ZERO_C,
            mw_737, characteristic="linear", mw_des=C002_MW737_DES)

        # 328P006 can deliver only the liquid above the heel plus what arrives on the tick, net
        # of what boils (decisions 11, 24). The heel keeps the 1 kg floor out of the pump's
        # reach, so the floor never makes up what the pump took. Inert at every normal state.
        m_743_avail = max(max(self.m_kg - C002_M_FLOOR_KG, 0.0) / max(dt, DT_FLOOR_S) * 3600.0
                          + m_in - gen, 0.0)
        suction_lost = m_743 > m_743_avail
        if suction_lost:
            m_743 = m_743_avail

        # ----- the holdup, less what boils (decision 24), and what a full shell cannot hold
        # (decision 11) ---------------------------------------------------------------------
        m_pre = self.m_kg
        m_new = max(m_pre + (m_in - gen - m_743) / 3600.0 * dt, C002_M_FLOOR_KG)
        m_overflow = 0.0
        if m_new > C002_FULL_KG:
            m_overflow = (m_new - C002_FULL_KG) / max(dt, DT_FLOOR_S) * 3600.0
            m_new = C002_FULL_KG

        # ----- the pressure: moles on the free volume, on the OLD holdup (V1 report A-6) -----
        v_v = vapour_volume_m3(C002_VOL_M3, m_pre, C002_RHO_KGM3)
        dmdt = (m_in - gen - m_743 - m_overflow) / 3600.0
        t_k = t_pre + ABSOLUTE_ZERO_C
        p_free = self.p_bara + vessel_dpdt(
            self.p_bara, t_k, v_v, mw_737, gen / mw_737, m_737 / mw_737,
            dtdt_k_s=(t_pre - self.t_prev_c) / dt, dvvdt_m3_s=-dmdt / C002_RHO_KGM3) * dt
        # ----- SV32850 and SV32851: lifted at their set pressure, they vent the head space's
        # vapour to atmosphere until the column falls to their reseat pressure (B-47) -------
        m_relief = self.sv_32850.vent_kgh(self.p_bara, p_free, t_k, mw_737, v_v, dt)
        if m_relief > 0.0:
            p_free += vessel_dpdt(self.p_bara, t_k, v_v, mw_737, 0.0, m_relief / mw_737) * dt
        self.p_bara = max(p_free, C002_P_FLOOR_BARA)
        self.t_prev_c = t_pre

        # ----- the bubble point at the bottom node, and the holdup ------------------------
        self.t_c = iapws.tsat_c(self.p_bara + C002_DP_COL_BAR)
        self.m_kg = m_new

        # ----- the species: four inlets, the two vapour recycles on last tick's vapours -----
        alpha, domain = alpha_live(C002_STAGE, self.t_c, m_748_kgh + m_750_kgh, m_743, self.w,
                                   self.p_bara + C002_DP_COL_BAR)
        self.w, self.y_737 = advance_species(
            self.w, self.m_kg,
            [(W_S738, m_738_kgh), (W_S775, m_775_kgh), (y_748, m_748_kgh), (y_750, m_750_kgh)],
            gen, alpha, m_743 + m_overflow, 0.0, dt)

        return FirstDesorberResult(
            in_kgh=m_in, lic_pv_pct=level, lic_op_pct=lic_op, m_743_kgh=m_743,
            suction_lost=suction_lost, q_kw=q, gen_kgh=gen, m_737_kgh=m_737,
            m_overflow_kgh=m_overflow, m_relief_kgh=m_relief,
            relief_lifted=self.sv_32850.valve.lifted,
            p_bara=self.p_bara, t_c=self.t_c, t_top_c=self.t_c - C002_DT_TOP_K, m_kg=self.m_kg,
            level_pct=self.m_kg / C002_M_DES_KG * C002_LEVEL_DES_PCT,
            w=dict(self.w), y_737=dict(self.y_737), vle_domain=domain,
        )


__all__ = [
    "C002_P_FLOOR_BARA", "INV_MW_FLOOR", "DT_FLOOR_S", "sv_32850", "lic_328503",
    "FirstDesorberResult", "FirstDesorber",
]
