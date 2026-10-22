"""328C003 — the hydrolyser — and 328E021, its feed/effluent interchanger.

What this models
----------------
328C003 destroys the urea the process condensate still carries, NH2CONH2 + H2O -> 2 NH3 + CO2,
so the purified condensate meets its 1 ppm guarantee. It is a liquid-filled trayed column at
200 C and 16.8 bar a; MP steam (911) injected at the bottom carries the reaction's heat and
strips the gas it makes, which leaves overhead as 748 through PV-328203 to 328C002. The feed,
328C002's bottoms (743), reaches it as 746 through 328E021's cold side; the hydrolysed liquor
leaves as 747 through LV-328504 and 328E021's hot side to 328C004.

The column is one node: liquid holdup, temperature, pressure and one species vector.

**The conversion** is a second-order plug-flow integral (Inoue & Otsuka's rate constant,
`thermo.kinetics`), the residence scaling inversely with the live feed:

    tau = tau_des . m_746,des / m_746
    X   = H0 (1 - e) / (H0 - U0 e),   e = exp(-k(T)(H0 - U0) tau)      (U0, H0 of 746, kmol/m3)
    xi  = m_746 . w_urea / M_urea . X                                       [kmol/h]

**The overhead generation** is the reaction's gas plus what the steam strips:

    gen_748 = xi (2 M_NH3 + M_CO2) + gas_strip,des . m_911 / m_911,des

**The overhead** is what PV-328203 passes on the IEC 60534 compressible law, from the live
column to 328C002's live pressure, anchored on the design overhead, on the live molar mass of
last tick's vapour. PIC-328203 strokes it on the column pressure.

**The pressure** integrates generation against overhead on the free volume (V1 report A-6):

    dP/dt = (R T / V_v)(gen_748 - m_748) / M_748 + (P / T) dT/dt - (P / V_v) dV_v/dt   [core.node]

**The heat balance** is semi-implicit in the 746 feed (V1's form):

    M cp dT/dt = m_746 cp (T_746 - T) + m_911 dH_911 - gen_748 lambda_748 - xi dH_hyd

with lambda_748 back-solved so the design holds, the design endotherm taken out of it.

**The holdup:** dM/dt = m_746 + m_911 - gen_748 - m_747. The liquid loses, and pays the latent
of, everything that boils; what the valve does not pass stays in the head space, where the
pressure integral carries it (decision 24).

**The level** is M / M_des x 50. LIC-328504 strokes LV-328504 on the IEC 60534 liquid law, from
the live column plus its live head to 328C004's pressure, its choke on the liquor's bubble
pressure at 328E021's hot outlet of the tick before (V1: it flashes at design).

**328E021** heats 746 by a temperature effectiveness back-solved on the design temperatures and
cools 747 by the energy balance, less the design shell loss (`interchanger_outlets`, shared with
328E007). Its hot outlet, 749, is published for 328C004 and for LV-328504's choke next tick.

**TIC-328012** reads the bottom-to-third-tray differential, T - T_746, for its faceplate; its
output drives nothing (V1). The P&ID cascades it onto FIC-329402's set point; on V1's PV the
drawn cascade runs away, so it is kept unwired until a tray temperature exists (decided
2026-09-30, handoff B-48, deferred to Phase 7).

Where this unit departs from V1
-------------------------------
Each is inert at the design point. The first was decided on this unit; the rest are classes the
process engineer decided on another unit, applied here under §5 rule 7.

  * **The liquid pays what boils** (decision 24, 2026-09-30). V1 takes the overhead out of the
    liquid and charges its latent heat on what PV-328203 vents, while the pressure integral
    fills the head space with what the column generates: vapour held back by a throttled valve
    is made twice. With PV-328203 at 20 % for an hour V1 creates 554 kg and runs 3.1 K hot;
    here the liquid loses and pays for the generation, and mass closes within a kilogram.

  * **328E021 never makes heat** (decision 14). Below 85 % of its design hot flow — 29 037 kg/h
    of 747 against design 746 — the hot side cannot give V1's cold-side duty; V1 clamps 749 at
    the feed's temperature and heats 746 to 190 C anyway. Here the cold side takes what the hot
    side gave, less the shell loss, bounded by V1's share; the binding is flagged.
  * **PIC-328203 and FIC-329402 read the table on span** (decision 10): 3.75 %/bar on PT-328203's
    0-40 bar, where V1 runs 1.50; 0.0222 %/(kg/h) on FT-329402's 0-1800 kg/h, where V1 runs 0.40.
  * **PV-328203 runs its vendor trim** (decision 23): Valtek's modified equal percentage from
    70.56 %, xT 0.8047, where V1 runs it linear from 50 % on the IEC 0.75.
  * **LV-328504 runs Fisher's trim** (decision 150, 2026-10-22; decision 23's class): equal
    percentage, rated Cv 82.2, FL 0.819, from the stroke where its rated Cv passes 747 on the
    normal case (UD-MR-G00-DZ-0014, item 023), where V1 runs it linear from 50 % on FL 0.90.
  * **LV-328504 cannot drain an empty column** (decision 11, the class of B-29). V1 lets the
    letdown pass its pressure-driven flow whatever the column holds and its 1 kg floor makes up
    the difference. Here 747 is capped at the liquid above a 1 kg heel plus what arrives on the
    tick, net of what boils, and the loss is flagged.
  * **A full column overflows** (decision 11). Above the shell's 56 571 kg the excess leaves as a
    published stream at the bottoms' state; its destination is not yet named (handoff A-15,
    Phase 5).

The boundaries this unit reads, and when
----------------------------------------
  * 746 and its composition, 328C002's bottoms, and 328C002's temperature and pressure — this
    tick's (`FirstDesorberResult`): V1 steps the hydrolyser right after 328C002;
  * 328C004's pressure — last tick's (V1 ``s.a328_c004_P``): 328C004 steps after this unit.

It publishes 748 and its vapour, which 328C002 takes the next tick (V1's tear); 747 and 749's
temperature, which 328C004 takes the same tick; and its pressure, which 328C002 reads next tick.

Source
------
V1 ``backend/main.py`` step_sim, "Stage 4 : 328C003 Hydrolyser" (lines 9062-9165), 328E021's hot
outlet in "Stage 5" (9181-9183), TIC-328012 (10080), the cp line (8829), ``hydrolysis_x_328c003``
(3328-3353); the seeds in ``State.__init__`` (6849-6852, 6860, 6867, 7023-7034, 7083-7087,
7096-7100); the telemetry block (10767-10790). The design data are in `ureasim.data.unit_328c003`
and `ureasim.data.desorption_train`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ureasim.control.process_loop import FlowLoop, ProcessLoop
from ureasim.control.valve import valve_gas_anchored, valve_liquid_anchored
from ureasim.core.node import vapour_volume_m3, vessel_dpdt
from ureasim.core.relief import GasReliefValve, SafetyValve, psv_area_from_rated_m2
from ureasim.core.units_of_measure import ABSOLUTE_ZERO_C, G_ACC, PA_PER_BAR
from ureasim.data.desorption_train import (
    C002_P_TOP_BARA,
    C003_M746_DES_KGH,
    C003_M747_DES_KGH,
    C003_M748_DES_KGH,
    C003_M911_DES_KGH,
    C004_P_BARA,
    C004_T749_C,
    CP_DESORPTION,
    DES_C003,
    W_S743,
    W_S747,
    W_STEAM,
)
from ureasim.data.unit_328c003 import (
    C003_AREA_M2,
    C003_DT_748_K,
    C003_DT_DES_K,
    C003_FULL_KG,
    C003_LEVEL_DES_PCT,
    C003_M_DES_KG,
    C003_M_FLOOR_KG,
    C003_P_BARA,
    C003_RHO_KGM3,
    C003_T_C,
    C003_TAU_DES_S,
    C003_VOL_M3,
    E021_EPS_T,
    E021_HOT_FLOW_FLOOR_KGH,
    E021_LOSS_DT_KGKH,
    FIC_329402_KC,
    FIC_329402_OP_DES_PCT,
    FIC_329402_SP_HI_KGH,
    FIC_329402_TI_S,
    FT_329402_TAU_S,
    HYDROLYSIS_DH_KJMOL,
    LAM748_BASE_KJKG,
    LIC_328504_KC,
    LIC_328504_TI_S,
    LV504_CHAR,
    LV504_FL,
    LV504_OP_DES_PCT,
    LV504_P1_DES_BARA,
    LV504_PV_DES_BARA,
    M911_DH_KJKG,
    MW748_DES,
    PIC_328203_KC,
    PIC_328203_SP_HI_BARA,
    PIC_328203_SP_LO_BARA,
    PIC_328203_TI_S,
    PV328203_CHAR,
    PV328203_OP_DES_PCT,
    PV328203_XT,
    SV32852_CAP_KGH,
    SV32852_MW_REL,
    SV32852_P_REL_BARA,
    SV32852_RESEAT_BARA,
    SV32852_SET_BARA,
    SV32852_T_REL_K,
    SV32852_Z_REL,
    TIC_328012_KC,
    TIC_328012_SP_HI_K,
    TIC_328012_TI_S,
)
from ureasim.thermo.ammonia_water import VOLATILE, liquor_pv_bara, relative_volatility_ratio
from ureasim.thermo.domains import MW
from ureasim.thermo.empirical import aqueous_cp
from ureasim.thermo.kinetics import urea_hydrolysis_k_m3_kmol_h
from ureasim.thermo.urea_liquor import SOLUTION_SPECIES
from ureasim.units.desorption.desorber_stage import advance_species
from ureasim.units.desorption.feed_effluent_interchanger import interchanger_outlets

#: Floor on the column pressure [bar a]: V1's ``max(..., 0.1)``.
C003_P_FLOOR_BARA = 0.1

#: Numerical floors, V1's: the vapour's inverse molar mass [kmol/kg], a flow the residence and
#: the ppm divide by [kg/h], the heat capacity [kJ/K], the step in the caps [s], the exponent
#: floor of the conversion integral, and the band inside which H0 = U0.
INV_MW_FLOOR = 1e-12
FLOW_FLOOR_KGH = 1e-6
HEAT_CAPACITY_FLOOR_KJK = 1e-6
DT_FLOOR_S = 1e-9
EXP_FLOOR = -700.0
EQUAL_MOLARITY_BAND = 1e-12

#: The gas one kmol of urea makes [kg/kmol]: 2 NH3 + CO2, 78.07. Source: V1 `main.py`
#: R328_HYD_GAS_MW.
HYD_GAS_MW = 2.0 * MW["NH3"] + MW["CO2"]


def hydrolysis_conversion(t_c: float, m_746_kgh: float, w_urea: float, w_h2o: float,
                          rho_kgm3: float = C003_RHO_KGM3) -> float:
    """The fraction of the feed's urea the hydrolyser destroys [-].

    Process utility
    ---------------
    What decides whether the purified condensate meets its 1 ppm urea guarantee: the
    hydrolyser is a trayed column, plug flow, so an hour at 200 C destroys all but a trace; a
    colder column or a heavier feed (less residence) lets urea through to 328C004 and the
    cooling tower.

    Equation
    --------
        dX/dt = k (U0 - X)(H0 - X)                  second order, U0 urea and H0 water [kmol/m3]
        X/U0  = H0 (1 - e) / (H0 - U0 e),   e = exp(-k (H0 - U0) tau)
        X/U0  = k U0 tau / (1 + k U0 tau)            where H0 = U0
        tau   = tau_des . m_746,des / m_746          [h]

    Source: V1 `main.py` `hydrolysis_x_328c003`.
    """
    u0 = max(rho_kgm3 * w_urea / MW["Urea"], 0.0)
    h0 = max(rho_kgm3 * w_h2o / MW["H2O"], 0.0)
    if u0 <= 0.0 or h0 <= 0.0:
        return 0.0
    tau_h = (C003_TAU_DES_S / 3600.0) * (C003_M746_DES_KGH / max(m_746_kgh, FLOW_FLOOR_KGH))
    k_h = urea_hydrolysis_k_m3_kmol_h(t_c)
    delta = h0 - u0
    if abs(delta) <= EQUAL_MOLARITY_BAND:
        conversion = k_h * u0 * tau_h / (1.0 + k_h * u0 * tau_h)
    else:
        e_minus = math.exp(max(-k_h * delta * tau_h, EXP_FLOOR))
        conversion = h0 * (1.0 - e_minus) / (h0 - u0 * e_minus)
    return max(0.0, min(1.0, conversion))


#: The design conversion, 0.99999…, the urea it destroys [kmol/h], the gas that makes and what
#: the steam strips beside it [kg/h] — the two parts of the 812 kg/h of 748 — and the design
#: endotherm [kW]. Source: V1 `main.py` R328_C003_X_DES ... R328_C003_QHYD_DES_KW.
C003_X_DES = hydrolysis_conversion(C003_T_C, C003_M746_DES_KGH, W_S743["Urea"], W_S743["H2O"])
C003_UREA_DES_KGH = C003_M746_DES_KGH * W_S743["Urea"]
C003_XI_DES_KMOLH = C003_UREA_DES_KGH / MW["Urea"] * C003_X_DES
C003_GASHYD_DES_KGH = C003_XI_DES_KMOLH * HYD_GAS_MW
C003_GASSTR_DES_KGH = C003_M748_DES_KGH - C003_GASHYD_DES_KGH
C003_QHYD_DES_KW = C003_XI_DES_KMOLH * HYDROLYSIS_DH_KJMOL * 1000.0 / 3600.0

#: The overhead's latent heat [kJ/kg] with the design endotherm taken out, so the explicit
#: xi . dH term puts the design temperature back to the bit. Source: V1 `main.py` 3373,
#: ``R328_C003_LAM748 -= R328_C003_QHYD_DES_KW / (R328_C003_M748_DES / 3600.0)``.
C003_LAM748_KJKG = LAM748_BASE_KJKG - C003_QHYD_DES_KW / (C003_M748_DES_KGH / 3600.0)


# ======================================================================================
# The four controllers, seeded as V1 seeds them
# ======================================================================================

def pic_328203() -> ProcessLoop:
    """PIC-328203, the hydrolyser's pressure. DIRECT acting: a pressure above set point opens
    PV-328203. On the table's gain per cent of PT-328203's span (decision 10)."""
    return ProcessLoop(
        tag="PIC-328203", Kc=PIC_328203_KC, Ti=PIC_328203_TI_S, Td=-1.0, act=-1.0,
        op=PV328203_OP_DES_PCT, sp=C003_P_BARA, pv=C003_P_BARA, pv1=C003_P_BARA,
        pv2=C003_P_BARA, op_lo=0.0, op_hi=100.0, sp_lo=PIC_328203_SP_LO_BARA,
        sp_hi=PIC_328203_SP_HI_BARA)


def fic_329402() -> FlowLoop:
    """FIC-329402, the MP steam 911: a MASS loop, in CAS with no remote set point wired (V1),
    on the table's gain per cent of FT-329402's span (decision 10)."""
    loop = ProcessLoop(
        tag="FIC-329402", Kc=FIC_329402_KC, Ti=FIC_329402_TI_S, Td=-1.0, act=+1.0, mode="CAS",
        op=FIC_329402_OP_DES_PCT, sp=C003_M911_DES_KGH, pv=C003_M911_DES_KGH,
        pv1=C003_M911_DES_KGH, pv2=C003_M911_DES_KGH, op_lo=0.0, op_hi=100.0, sp_lo=0.0,
        sp_hi=FIC_329402_SP_HI_KGH)
    return FlowLoop(loop=loop, design_flow=C003_M911_DES_KGH, op_des=FIC_329402_OP_DES_PCT,
                    tau_s=FT_329402_TAU_S)


def lic_328504() -> ProcessLoop:
    """LIC-328504, the level. DIRECT acting: a level above set point opens LV-328504."""
    return ProcessLoop(
        tag="LIC-328504", Kc=LIC_328504_KC, Ti=LIC_328504_TI_S, Td=0.0, act=-1.0,
        op=LV504_OP_DES_PCT, sp=C003_LEVEL_DES_PCT, pv=C003_LEVEL_DES_PCT,
        pv1=C003_LEVEL_DES_PCT, pv2=C003_LEVEL_DES_PCT, op_lo=0.0, op_hi=100.0, sp_lo=0.0,
        sp_hi=100.0)


def tic_328012() -> ProcessLoop:
    """TIC-328012, the bottom-to-third-tray differential — for its faceplate: V1 wires its
    output to nothing."""
    return ProcessLoop(
        tag="TIC-328012", Kc=TIC_328012_KC, Ti=TIC_328012_TI_S, Td=0.0, act=-1.0,
        op=50.0, sp=C003_DT_DES_K, pv=C003_DT_DES_K, pv1=C003_DT_DES_K, pv2=C003_DT_DES_K,
        op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=TIC_328012_SP_HI_K)


def sv_32852() -> GasReliefValve:
    """SV32852, the column's safety valve, shut: set 24.01 bar a, reseating at 21.71, its orifice
    back-solved from its certified 24 897 kg/h of steam at 26.31 bar a (B-47). The sheet prints
    no exponent for steam: the law's 1.30 is taken on both sides of the back-solve."""
    return GasReliefValve(
        valve=SafetyValve("SV32852", SV32852_SET_BARA, SV32852_RESEAT_BARA),
        area_m2=psv_area_from_rated_m2(SV32852_CAP_KGH, SV32852_P_REL_BARA, SV32852_T_REL_K,
                                       SV32852_MW_REL, z=SV32852_Z_REL))


@dataclass
class HydrolyserLoops:
    """The four controllers on 328C003, each seeded as V1 seeds it."""

    pic_328203: ProcessLoop = field(default_factory=pic_328203)
    fic_329402: FlowLoop = field(default_factory=fic_329402)
    lic_328504: ProcessLoop = field(default_factory=lic_328504)
    tic_328012: ProcessLoop = field(default_factory=tic_328012)


@dataclass(frozen=True)
class HydrolyserResult:
    """Everything 328C003 and 328E021 publish on one tick."""

    #: 328E021: 746 into the column [deg C] (TT-328009), 749 out of the hot side [deg C], and
    #: True where the hot side could not give V1's cold-side duty (decision 14).
    t_746_c: float
    t_749_c: float
    e021_pinched: bool
    #: 911, the MP steam FIC-329402 passes [kg/h].
    m_911_kgh: float
    #: PIC-328203's output [%] and 748, the overhead PV-328203 passes to 328C002 [kg/h].
    pic_op_pct: float
    m_748_kgh: float
    #: The overhead generation [kg/h] and its two parts, the reaction's gas and the stripped.
    gen_748_kgh: float
    gas_hyd_kgh: float
    gas_strip_kgh: float
    #: The conversion [-], the urea fed [kg/h], the extent [kmol/h] and the urea slipping to
    #: 328C004 (AI-328701) [ppm].
    x_hyd: float
    urea_in_kgh: float
    xi_kmolh: float
    urea_747_ppm: float
    #: LI-328504 before the tick [%], LIC-328504's output [%], 747 [kg/h], and True where 747
    #: was capped at the heel (decision 11).
    lic_pv_pct: float
    lic_op_pct: float
    m_747_kgh: float
    drain_lost: bool
    #: The net heat [kW] the temperature integrated, and the hydrolysis endotherm in it [kW].
    q_net_kw: float
    q_hyd_kw: float
    #: The liquid above the full shell [kg/h], zero until the column is full (decision 11).
    m_overflow_kgh: float
    #: What SV32852 vents of the column's vapour, at y_748, to atmosphere [kg/h], and True while
    #: it is lifted (B-47).
    m_relief_kgh: float
    relief_lifted: bool
    #: The state after the tick: pressure [bar a], temperature (TT-328013) [deg C], the
    #: overhead (TT-328011) [deg C], holdup [kg] and LI-328504 [%].
    p_bara: float
    t_c: float
    t_748_c: float
    m_kg: float
    level_pct: float
    #: The liquid's and the overhead's compositions after the tick [mass fraction], and the VLE
    #: domain the live volatility was evaluated in.
    w: dict
    y_748: dict
    vle_domain: str | None
    #: TIC-328012's PV, T - T_746 after the tick [K], and its output [%].
    tic_pv_k: float
    tic_op_pct: float


@dataclass
class Hydrolyser:
    """328C003 as one node, with 328E021: holdup, temperature, pressure, species and the step."""

    #: Liquid holdup [kg], temperature [deg C] and the temperature on the tick before — the
    #: pressure step's thermal term, a tear, zero at the seed — and pressure [bar a].
    m_kg: float = C003_M_DES_KG
    t_c: float = C003_T_C
    t_prev_c: float = C003_T_C
    p_bara: float = C003_P_BARA
    #: The liquid's composition, seeded on PFD 747, and the overhead's, on the back-solved design
    #: vapour — the gas law carries sqrt(M), so the first tick needs the design vapour.
    w: dict = field(default_factory=lambda: dict(W_S747))
    y_748: dict = field(default_factory=lambda: dict(DES_C003.y))
    #: 749's temperature on the tick before [deg C]: LV-328504's inlet, where its choke is read.
    t_749_c: float = C004_T749_C
    #: SV32852 and its lift (B-47).
    sv_32852: GasReliefValve = field(default_factory=sv_32852)

    def step(self, loops: HydrolyserLoops, m_746_kgh: float, w_746: dict, t_c002_c: float,
             p_c002_bara: float, p_c004_bara: float, dt: float) -> HydrolyserResult:
        """Advance 328C003 and 328E021 by one tick.

        Arguments
        ---------
        m_746_kgh, w_746
            328C002's bottoms through LV-328503 and their composition, this tick.
        t_c002_c, p_c002_bara
            328C002's temperature — 328E021's cold inlet — and pressure — PV-328203's outlet —
            after its step this tick.
        p_c004_bara
            328C004's pressure at the top of the tick — LV-328504's outlet.

        The order is V1's: the steam and the pressure loop, the overhead, the reaction, the
        level loop and the letdown; 328E021; the pressure on the OLD holdup and the tick
        before's temperature change; the temperature and the holdup; the species; TIC-328012.
        """
        t_pre = self.t_c
        cp = aqueous_cp(CP_DESORPTION, C003_T_C, t_pre)
        m_911 = loops.fic_329402.step(dt)
        m_in = m_746_kgh + m_911
        pic_op = loops.pic_328203.step(self.p_bara, dt)
        # The overhead's live molar mass, off last tick's vapour: a tear, closed at the end.
        mw_748 = 1.0 / max(sum(self.y_748.get(k, 0.0) / MW[k] for k in SOLUTION_SPECIES),
                           INV_MW_FLOOR)

        # ----- 748: PV-328203 to 328C002, on its vendor trim (decision 23) -----------------
        m_748 = valve_gas_anchored(
            C003_M748_DES_KGH, pic_op / 100.0, self.p_bara, p_c002_bara,
            t_pre + ABSOLUTE_ZERO_C, PV328203_OP_DES_PCT / 100.0, C003_P_BARA, C002_P_TOP_BARA,
            C003_T_C + ABSOLUTE_ZERO_C, mw_748, characteristic=PV328203_CHAR, xt=PV328203_XT,
            mw_des=MW748_DES)

        # ----- the reaction and the strip: the overhead the column generates ---------------
        x_hyd = hydrolysis_conversion(t_pre, m_746_kgh,
                                      w_746.get("Urea", W_S743["Urea"]),
                                      w_746.get("H2O", W_S743["H2O"]))
        urea_in = m_746_kgh * w_746["Urea"]
        xi = urea_in / MW["Urea"] * x_hyd
        gas_hyd = xi * HYD_GAS_MW
        gas_str = C003_GASSTR_DES_KGH * (m_911 / C003_M911_DES_KGH)
        gen_748 = gas_hyd + gas_str

        # ----- LIC-328504 -> LV-328504, the letdown to 328C004 ----------------------------
        level = self.m_kg / C003_M_DES_KG * C003_LEVEL_DES_PCT
        lic_op = loops.lic_328504.step(level, dt)
        head_m = self.m_kg / (C003_RHO_KGM3 * C003_AREA_M2)
        p1 = self.p_bara + C003_RHO_KGM3 * G_ACC * head_m / PA_PER_BAR
        # The liquor reaches the valve after 328E021's hot side: its choke is last tick's 749.
        m_747 = valve_liquid_anchored(
            C003_M747_DES_KGH, lic_op / 100.0, p1, p_c004_bara, C003_RHO_KGM3,
            LV504_OP_DES_PCT / 100.0, LV504_P1_DES_BARA, C004_P_BARA, C003_RHO_KGM3,
            characteristic=LV504_CHAR, fl=LV504_FL, pv_bara=liquor_pv_bara(self.w, self.t_749_c),
            pv_des_bara=LV504_PV_DES_BARA)
        # The letdown drains only the liquid above the heel plus what arrives, net of what
        # boils (decisions 11, 24). Inert at every normal state.
        m_747_avail = max(max(self.m_kg - C003_M_FLOOR_KG, 0.0) / max(dt, DT_FLOOR_S) * 3600.0
                          + m_in - gen_748, 0.0)
        drain_lost = m_747 > m_747_avail
        if drain_lost:
            m_747 = m_747_avail
        ppm_747 = urea_in * (1.0 - x_hyd) / max(m_747, FLOW_FLOOR_KGH) * 1e6

        # ----- 328E021: the cold side takes only what the hot side gave (decision 14) -------
        t_746, t_749, pinched = interchanger_outlets(
            t_c002_c, t_pre, m_746_kgh, m_747, E021_EPS_T, E021_LOSS_DT_KGKH,
            E021_HOT_FLOW_FLOOR_KGH)

        # ----- the heat balance: the liquid pays the latent of what boils (decision 24) ------
        sens = m_746_kgh / 3600.0 * cp * (t_746 - t_pre)
        q_hyd = xi * HYDROLYSIS_DH_KJMOL * 1000.0 / 3600.0
        q_net = (sens + m_911 / 3600.0 * M911_DH_KJKG
                 - gen_748 / 3600.0 * C003_LAM748_KJKG - q_hyd)

        # ----- the holdup, less what boils (decision 24), and what a full shell cannot hold
        # (decision 11) -----------------------------------------------------------------------
        m_pre = self.m_kg
        m_new = max(m_pre + (m_in - gen_748 - m_747) / 3600.0 * dt, C003_M_FLOOR_KG)
        m_overflow = 0.0
        if m_new > C003_FULL_KG:
            m_overflow = (m_new - C003_FULL_KG) / max(dt, DT_FLOOR_S) * 3600.0
            m_new = C003_FULL_KG

        # ----- the pressure: moles on the free volume, on the OLD holdup (V1 report A-6) -----
        v_v = vapour_volume_m3(C003_VOL_M3, m_pre, C003_RHO_KGM3)
        dmdt = (m_in - gen_748 - m_747 - m_overflow) / 3600.0
        t_k = t_pre + ABSOLUTE_ZERO_C
        p_free = self.p_bara + vessel_dpdt(
            self.p_bara, t_k, v_v, mw_748, gen_748 / mw_748, m_748 / mw_748,
            dtdt_k_s=(t_pre - self.t_prev_c) / dt, dvvdt_m3_s=-dmdt / C003_RHO_KGM3) * dt
        # ----- SV32852: lifted at its set pressure, it vents the head space's vapour to
        # atmosphere until the column falls to its reseat pressure (B-47) -------------------
        m_relief = self.sv_32852.vent_kgh(self.p_bara, p_free, t_k, mw_748, v_v, dt)
        if m_relief > 0.0:
            p_free += vessel_dpdt(self.p_bara, t_k, v_v, mw_748, 0.0, m_relief / mw_748) * dt
        self.p_bara = max(p_free, C003_P_FLOOR_BARA)
        self.t_prev_c = t_pre

        # ----- the temperature, semi-implicit in the 746 feed, and the holdup --------------
        k_cap = m_746_kgh / 3600.0 * cp
        self.t_c = t_pre + q_net * dt / max(m_pre * cp + k_cap * dt, HEAT_CAPACITY_FLOOR_KJK)
        self.m_kg = m_new

        # ----- the species: a liquid-filled column, so no Kremser stage correction ---------
        a_rel, domain = relative_volatility_ratio(self.w, self.t_c, self.p_bara, C003_T_C,
                                                  C003_P_BARA)
        alpha = {k: (v * a_rel[k] if k in VOLATILE else v)
                 for k, v in DES_C003.alpha.items()}
        self.w, self.y_748 = advance_species(
            self.w, self.m_kg, [(w_746, m_746_kgh), (W_STEAM, m_911)],
            gen_748, alpha, m_747 + m_overflow, xi, dt)
        self.t_749_c = t_749

        # ----- TIC-328012, on the faceplate only (V1) --------------------------------------
        tic_pv = self.t_c - t_746
        tic_op = loops.tic_328012.step(tic_pv, dt)

        return HydrolyserResult(
            t_746_c=t_746, t_749_c=t_749, e021_pinched=pinched, m_911_kgh=m_911,
            pic_op_pct=pic_op, m_748_kgh=m_748, gen_748_kgh=gen_748, gas_hyd_kgh=gas_hyd,
            gas_strip_kgh=gas_str, x_hyd=x_hyd, urea_in_kgh=urea_in, xi_kmolh=xi,
            urea_747_ppm=ppm_747, lic_pv_pct=level, lic_op_pct=lic_op, m_747_kgh=m_747,
            drain_lost=drain_lost, q_net_kw=q_net, q_hyd_kw=q_hyd, m_overflow_kgh=m_overflow,
            m_relief_kgh=m_relief, relief_lifted=self.sv_32852.valve.lifted,
            p_bara=self.p_bara, t_c=self.t_c, t_748_c=self.t_c - C003_DT_748_K, m_kg=self.m_kg,
            level_pct=self.m_kg / C003_M_DES_KG * C003_LEVEL_DES_PCT,
            w=dict(self.w), y_748=dict(self.y_748), vle_domain=domain,
            tic_pv_k=tic_pv, tic_op_pct=tic_op,
        )


__all__ = [
    "C003_P_FLOOR_BARA", "INV_MW_FLOOR", "FLOW_FLOOR_KGH", "HEAT_CAPACITY_FLOOR_KJK",
    "DT_FLOOR_S", "EXP_FLOOR", "EQUAL_MOLARITY_BAND", "HYD_GAS_MW", "hydrolysis_conversion",
    "C003_X_DES", "C003_UREA_DES_KGH", "C003_XI_DES_KMOLH", "C003_GASHYD_DES_KGH",
    "C003_GASSTR_DES_KGH", "C003_QHYD_DES_KW", "C003_LAM748_KJKG",
    "sv_32852", "pic_328203", "fic_329402", "lic_328504", "tic_328012", "HydrolyserLoops",
    "HydrolyserResult", "Hydrolyser",
]
