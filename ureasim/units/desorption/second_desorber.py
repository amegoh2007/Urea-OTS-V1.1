"""328C004 — desorber II, the lower section of the desorption tower.

What this models
----------------
328C004 strips the ammonia the hydrolysed liquor still carries, so the purified condensate
meets its guarantee. 749 — the hydrolyser's bottoms after 328E021's hot side — enters at the top
at 148 C; LP steam 931 enters at the bottom on FIC-329401, whose set point FFIC-329401 ratios to
the desorbers' feed. The steam and what it strips leave overhead as 750, through a line with no
valve, to 328C002, where they are the stripping vapour; the purified condensate leaves the sump
as 739 through 328E007's hot side and LV-328505, or — FV-328406 open — back to 328D003 as 741
through 328E001, from the line ahead of LV-328505.

    749 + 931 --> 328C004 --750--> 328C002
                         --739--> 328E007 --+--> LV-328505 --> boundary
                                            +--> 328E001 --> FV-328406 --741--> 328D003

The column is one node, as 328C002 is: liquid holdup, pressure, temperature, one species vector.

**The boil-up** is what the net duty can boil, anchored on the design duty:

    q   = m_749 cp (T_749 - T) / 3600 + m_931 dH_931 / 3600
    gen = m_750,des . q / Q_des         (negative: the duty condenses vapour, decision 15)

with cp water's at the live temperature (`aqueous_cp` on 4.0 at 143 C) and dH_931 2136 kJ/kg.

**The overhead** is what the line passes to 328C002 on the IEC 60534 compressible law, the stroke
fixed at 1 (a line, not a throttle), from the live column to 328C002's live pressure, at the live
bottoms' temperature, on the live molar mass of last tick's vapour (V1 report D-2).

**The pressure** integrates boil-up against overhead on the free volume, on the old holdup and the
temperature change of the tick before (V1 report A-6):

    dP/dt = (R T / V_v)(gen - m_750) / M_750 + (P / T) dT/dt - (P / V_v) dV_v/dt   [core.node]

stepped explicitly, as V1 steps it, on every tick whose own linearised gain leaves the step
monotone, and backward (`core.node.stable_pressure_step`) on a tick where it would ring — the
head space of a column filling towards its roof (handoff B-51).

**The temperature** is water's bubble point at the bottom node, the overhead pressure plus a
lumped offset back-solved on the PFD's 143 C: T = T_sat,water(P + dP_col). Losing the LP steam
drops the pressure and the bottoms with it, and collapses the stripping (V1 AUDIT C1).

**The holdup** is the liquid's: dM/dt = m_749 + m_931 - gen - m_739, m_739 = m_LV + m_741
(decision 24).

**The level** is M / M_des x 50. LIC-328505 strokes LV-328505 on the IEC 60534 liquid law from
the live column plus its live head to the 1.0 bar a boundary datum. While FIC-328406 is in
cascade a switch shuts LV-328505 and LIC-328505's output sets FIC-328406's set point instead,
OUTP / 100 x 60 m3/h (FT-328406's span), so the column's level is held on the recycle:

    SP_406 = OUTP_LIC / 100 . 60 m3/h,    LV-328505 at 0 %           (FIC-328406 in CAS)

**The steam.** FFIC-329401 is a ratio station: FIC-329401's set point is the ratio set point
times the desorbers' feed 735, SP_401 = r_sp . V_735 . 1000 kg/t, and FIC-329401 strokes
FV-329401 to it on FT-329401's lagged reading. The achieved ratio — last tick's 931 in t/h over
735 in m3/h — is published beside it, and the ratio set point tracks it while FIC-329401 is not
in cascade. FV-329401 passes the LP header's steam into the column's bottom, so what it passes at
a stroke follows the two pressures (handoff B-73): V1's butterfly law, linear on the IEC globe xT,
anchored on the header's 4.0 bar g and the bottom's design bubble point,

    m_931 = 6495 . (h / 50 %) . Phi(P_LP, P_bot) / Phi(P_LP,des, P_bot,des),   P_bot = P + dP_col

so a falling header opens FIC-329401 until FV-329401 is wide open, and below that the stripping
steam falls with it.

**The species** step implicitly on the stage's live Kremser volatility (`desorber_stage`), the
LP steam its stripping agent; AI-328701 reads their slip as a conductivity.

Where this unit departs from V1
-------------------------------
Each is inert at the design point, and asserted from both sides in the equivalence tests.

Decided by the process engineer on 2026-09-30 for this unit:

  * **FFIC-329401 ratios the LP steam to 735, the desorbers' feed** (handoff B-39). The P&ID
    (sheet 104) and the functional diagram (UD-MR-329-FF-0002) take the ratio's feed from
    FIC-328402, which meters 735 into 328E007. V1 takes it from 744, the 323E003 wash leg, where
    V1 hangs FIC-328402. Here the ratio reads 735's volume flow at PFD 735's density, this tick:
    the tank steps first. FIC-328402 itself meters 735 since 2026-10-09 (B-39 decided).
  * **FFIC-329401 is a ratio station** (handoff B-49), as the functional diagram draws it
    (RATIOSTN). V1 runs a PI on the measured ratio, on its own retune (8.0e5, 40 s; the table
    has no row), which overdrives the slave; here the slave gets ratio x feed on the tick the
    feed moves.
  * **LIC-328505 is FIC-328406's master** (handoff B-50), as UD-MR-328-FF-0002 page 2 draws it:
    in cascade FIC-328406 takes OUTP / 100 x FIC-328406:MAX and LV-328505 is switched shut. The
    recycle leaves the column's bottoms ahead of LV-328505 (P&ID 104, line 100-CPP3-328102 to
    328E001), so it is a draw on this column: 328C004 steps FIC-328406 and publishes 741, which
    328D003 takes next tick. V1 runs FIC-328406 on its own in 328D003's stage, taking 741 out of
    740 after LV-328505, and caps it at 739 — with LV-328505 shut that is nothing. FIC-328406's
    set point reaches FT-328406's 60 m3/h, where V1 stops at 739's design 34.0 m3/h.

Decided by the process engineer on 2026-10-02 (handoff B-73, the Typo Rule): **FV-329401 on the
live LP header.** V1's flow element is a pure gain on the stroke, so 328C004 kept its 6495 kg/h
from a header at any pressure; here the valve's pressure term above throttles it.

Decided by the process engineer on 2026-10-09 (handoff B-51): **the backward pressure step where
the explicit one would ring.** As the column fills towards its roof the head space closes, the
pressure's gain on the overhead line grows as 1 / V_v, and V1's explicit step limit-cycles — 750
alternating shut and wide open, the pressure swinging bar a peak to peak, on V1 and the port
alike. Where dt . df/dP falls below -1 the step is backward Euler on the node's own dP/dt, 750
evaluated at the pressure it settles on; elsewhere it is V1's to the bit.

Classes decided on other units, applied here under §5 rule 7:

  * **The liquid pays what boils** (decision 24): the holdup, the species and the heel cap lose
    the boil-up, not the overhead line's flow; the head space holds the difference.
  * **A negative duty condenses vapour** (decision 15): V1 clamps the boil-up at zero, and with
    749 colder than the column its bottoms would be held up by heat made from nothing.
  * **LV-328505 and FV-328406 cannot drain an empty column, and a full column overflows**
    (decision 11). The recycle is served first — in cascade it is the only draw — and FT-328406
    reads the 741 delivered.
  * **LV-328505 on its vendor trim** (decision 23): Valtek's modified equal percentage, Kvs 63,
    from 90.07 %, FL 0.9471, where V1 runs it linear from 50 %.
  * **FIC-329401 on the table's gain per cent of FT-329401's 0-12 000 kg/h** (decision 10):
    0.0025 %/(kg/h), where V1 applies the table's 0.30 per kg/h.

The functional diagram also blocks LIC-328505's integration for 3 s after FIC-328406 changes
over (a monoflop onto EINTBLK); the block's semantics are not documented, and it is not
modelled.

The boundaries this unit reads, and when
----------------------------------------
  * 749, its temperature and composition — the hydrolyser's 747 and 328E021's hot outlet, this
    tick (`HydrolyserResult`): V1 steps 328C004 right after 328C003;
  * 328C002's pressure — after its step this tick: 750's outlet;
  * 735 — the tank's draw this tick (`AmmoniaWaterTankResult`), the ratio's feed;
  * the LP header's pressure — the steam network's at the top of the tick (B-73).

It publishes 750 and its vapour, which 328C002 takes next tick (V1's tear); 739 and its
temperature, which 328E007 takes next tick; 741, which 328D003 takes next tick; and its
pressure, which the hydrolyser's LV-328504 reads next tick.

Source
------
V1 ``backend/main.py`` step_sim, "Stage 5 : 328C004 Desorber-II" (lines 9169-9253, the 749
temperature at 9181-9183 being 328E021's, in `hydrolyser`), the cp line (8830), the tear reads
(8844-8845) and writes (9670, 9675-9676); AI-328701 (10330); FIC-328406 in 328D003's stage
(8903-8905); the seeds in ``State.__init__`` (6641, 6853-6855, 6861, 6868, 7035-7058,
7100-7106, 7118-7127); the telemetry (10796-10813). The design data are in
`ureasim.data.unit_328c004`, `ureasim.data.unit_328d003` (741) and
`ureasim.data.desorption_train`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ureasim.control.process_loop import FlowLoop, ProcessLoop
from ureasim.control.ratio import RatioStation
from ureasim.control.valve import (
    XT_GLOBE,
    compressible_shape,
    valve_gas_anchored,
    valve_liquid_anchored,
)
from ureasim.core.node import stable_pressure_step, vapour_volume_m3, vessel_dpdt
from ureasim.core.units_of_measure import ABSOLUTE_ZERO_C, G_ACC, PA_PER_BAR
from ureasim.data.desorption_train import (
    C002_P_TOP_BARA,
    C004_M739_DES_KGH,
    C004_M750_DES_KGH,
    C004_M931_DES_KGH,
    C004_P_BARA,
    C004_T_C,
    CP_DESORPTION,
    DES_C004,
    W_S739,
    W_STEAM,
)
from ureasim.data.unit_328c004 import (
    C004_AREA_M2,
    C004_DP_COL_BAR,
    C004_DT_DES_K,
    C004_FULL_KG,
    C004_LEVEL_DES_PCT,
    C004_M931_DH_KJKG,
    C004_M_DES_KG,
    C004_M_FLOOR_KG,
    C004_MW750_DES,
    C004_Q_DES_KW,
    C004_RHO_KGM3,
    C004_STAGE,
    C004_VOL_M3,
    FFIC_329401_FACTOR,
    FFIC_329401_OP_HI_KGH,
    FFIC_329401_RATIO_DES,
    FFIC_329401_SP_HI,
    FIC_329401_KC,
    FIC_329401_OP_DES_PCT,
    FIC_329401_SP_HI_KGH,
    FIC_329401_TI_S,
    FT_329401_TAU_S,
    FV_329401_OP_DES_PCT,
    FV_329401_P1_DES_BARA,
    FV_329401_P2_DES_BARA,
    FV_329401_XT,
    LIC_328505_KC,
    LIC_328505_SP_PCT,
    LIC_328505_TI_S,
    LV505_CHAR,
    LV505_FL,
    LV505_OP_DES_PCT,
    LV505_P1_DES_BARA,
    LV505_P2_BARA,
    LV505_PV_DES_BARA,
    RHO_735_KGM3,
)
from ureasim.data.unit_328d003 import (
    FIC_328406_KC,
    FIC_328406_OP_FULL_PCT,
    FIC_328406_SP_HI_M3H,
    FIC_328406_TI_S,
    FIC_TD_S,
    FT_328406_SPAN_M3H,
    FT_TAU_S,
    FV_328406_CHAR,
    RHO_741_KGM3,
    S741_CAP_KGH,
)
from ureasim.data.control_valves import FV_329401
from ureasim.data.unit_329 import P_LP_BARA, STEAM_GAMMA, STEAM_MW
from ureasim.thermo import iapws
from ureasim.thermo.ammonia_water import condensate_conductivity_us_cm, liquor_pv_bara
from ureasim.thermo.domains import MW
from ureasim.thermo.empirical import aqueous_cp
from ureasim.thermo.urea_liquor import SOLUTION_SPECIES
from ureasim.units.desorption.desorber_stage import advance_species, alpha_live
from ureasim.units.steam_chest import ChestValve

#: Floor on the column pressure [bar a]: V1's ``max(..., 0.1)``.
C004_P_FLOOR_BARA = 0.1

#: Numerical floors, V1's: the vapour's inverse molar mass [kmol/kg], the ratio's feed [m3/h]
#: and the step in the caps [s].
INV_MW_FLOOR = 1e-12
FEED_FLOOR_M3H = 1e-6
DT_FLOOR_S = 1e-9


#: FV-329401 as the port runs it, on its vendor's trim — Metso's Neldisc from 26.0 % and its normal
#: case's xT (decision 108's class, decided 2026-10-15) — and as V1 runs it, linear from 50 % on the
#: IEC globe xT, which the equivalence harness keeps.
FV_329401_TRIM = ChestValve(FV_329401_OP_DES_PCT, FV_329401.characteristic, FV_329401_XT)
V1_FV_329401 = ChestValve(FIC_329401_OP_DES_PCT)


def _fv_329401_shape(p_lp_bara: float, p_bottom_bara: float, xt: float) -> float:
    return compressible_shape(1.0, p_lp_bara, p_bottom_bara,
                              iapws.tsat_c(max(p_lp_bara, 1e-6)) + ABSOLUTE_ZERO_C, STEAM_MW,
                              STEAM_GAMMA, 1.0, "linear", xt)


def fv_329401_pressure_ratio(p_lp_bara: float, p_bottom_bara: float,
                             xt: float = XT_GLOBE) -> float:
    """FV-329401's flow at a stroke over its flow there on the design pressures [-] (B-73).

    Process utility
    ---------------
    What ties 328C004's stripping steam to the LP header: the butterfly passes the header's
    saturated steam into the column's bottom, so a header that falls towards the bottom's
    pressure starves the column. 1.0 exactly on the design pressures; nothing once the bottom
    is at the header's pressure. ``xt`` is the trim's: the vendor's normal case's on the port,
    V1's IEC globe value by default.
    """
    ref = _fv_329401_shape(FV_329401_P1_DES_BARA, FV_329401_P2_DES_BARA, xt)
    return _fv_329401_shape(p_lp_bara, p_bottom_bara, xt) / ref


# ======================================================================================
# The four controllers, seeded as V1 seeds them
# ======================================================================================

def ffic_329401() -> RatioStation:
    """FFIC-329401, the LP-steam-to-feed ratio station [t/m3] (B-49): its output, FIC-329401's
    set point in kg/h, is the ratio set point times the feed."""
    r = FFIC_329401_RATIO_DES
    return RatioStation(
        tag="FFIC-329401", sp=r, op=C004_M931_DES_KGH, pv=r, sp_lo=0.0,
        sp_hi=FFIC_329401_SP_HI, op_lo=0.0, op_hi=FFIC_329401_OP_HI_KGH,
        factor=FFIC_329401_FACTOR)


def fic_329401(valve: ChestValve = FV_329401_TRIM) -> FlowLoop:
    """FIC-329401, the LP steam 931: a MASS loop in CAS under FFIC-329401, on the table's gain
    per cent of FT-329401's span (decision 10); FV-329401 on ``valve``'s trim, seeded at its design
    stroke."""
    loop = ProcessLoop(
        tag="FIC-329401", Kc=FIC_329401_KC, Ti=FIC_329401_TI_S, Td=0.0, act=+1.0, mode="CAS",
        op=valve.op_des_pct, sp=C004_M931_DES_KGH, pv=C004_M931_DES_KGH,
        pv1=C004_M931_DES_KGH, pv2=C004_M931_DES_KGH, op_lo=0.0, op_hi=100.0, sp_lo=0.0,
        sp_hi=FIC_329401_SP_HI_KGH)
    return FlowLoop(loop=loop, design_flow=C004_M931_DES_KGH, op_des=valve.op_des_pct,
                    tau_s=FT_329401_TAU_S, characteristic=valve.characteristic)


def lic_328505() -> ProcessLoop:
    """LIC-328505, the bottoms level. DIRECT acting: a level above set point opens LV-328505,
    seeded at its vendor design stroke (decision 23)."""
    return ProcessLoop(
        tag="LIC-328505", Kc=LIC_328505_KC, Ti=LIC_328505_TI_S, Td=0.0, act=-1.0,
        op=LV505_OP_DES_PCT, sp=LIC_328505_SP_PCT, pv=LIC_328505_SP_PCT, pv1=LIC_328505_SP_PCT,
        pv2=LIC_328505_SP_PCT, op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=100.0)


def fic_328406() -> FlowLoop:
    """FIC-328406, PFD 741, the recycle to 328D003: a VOLUMETRIC loop in m3/h, in MAN and shut
    at design; LIC-328505's slave in cascade (B-50). FV-328406 anchored on its full stroke."""
    loop = ProcessLoop(
        tag="FIC-328406", Kc=FIC_328406_KC, Ti=FIC_328406_TI_S, Td=FIC_TD_S, act=+1.0,
        mode="MAN", op=0.0, sp=0.0, pv=0.0, pv1=0.0, pv2=0.0, op_lo=0.0, op_hi=100.0,
        sp_lo=0.0, sp_hi=FIC_328406_SP_HI_M3H)
    return FlowLoop(loop=loop, design_flow=S741_CAP_KGH, op_des=FIC_328406_OP_FULL_PCT,
                    tau_s=FT_TAU_S, rho_kgm3=RHO_741_KGM3, characteristic=FV_328406_CHAR)


@dataclass
class SecondDesorberLoops:
    """The four controllers on 328C004, each seeded as V1 seeds it."""

    ffic_329401: RatioStation = field(default_factory=ffic_329401)
    fic_329401: FlowLoop = field(default_factory=fic_329401)
    lic_328505: ProcessLoop = field(default_factory=lic_328505)
    fic_328406: FlowLoop = field(default_factory=fic_328406)


@dataclass(frozen=True)
class SecondDesorberResult:
    """Everything 328C004 publishes on one tick."""

    #: FFIC-329401's measured ratio (FFY-329401) [t/m3] and its output, FIC-329401's set point
    #: [kg/h]; 931, the LP steam FV-329401 passes [kg/h].
    ffic_pv: float
    ffic_op_kgh: float
    m_931_kgh: float
    #: The column's whole inflow [kg/h]: 749 + 931.
    in_kgh: float
    #: LI-328505 before the tick [%], LIC-328505's output [%] and LV-328505's stroke [%] — shut
    #: while FIC-328406 is in cascade.
    lic_pv_pct: float
    lic_op_pct: float
    lv_op_pct: float
    #: The bottoms [kg/h]: 739, all of it, to 328E007's hot side; what LV-328505 passes to the
    #: boundary; and 741, what FV-328406 takes back to 328D003. True when the draws were capped
    #: at the heel (decision 11).
    m_739_kgh: float
    m_export_kgh: float
    m_741_kgh: float
    drain_lost: bool
    #: The net duty [kW], the boil-up it raises [kg/h] — negative where it condenses vapour —
    #: and 750, the overhead the line passes to 328C002 [kg/h].
    q_kw: float
    gen_kgh: float
    m_750_kgh: float
    #: The liquid above the full shell [kg/h], zero until the column is full (decision 11).
    m_overflow_kgh: float
    #: The state after the tick: pressure [bar a], bottoms (TT-328005) [deg C], top tray
    #: (TT-328004) [deg C], holdup [kg] and LI-328505 [%].
    p_bara: float
    t_c: float
    t_top_c: float
    m_kg: float
    level_pct: float
    #: The bottoms' and the overhead's compositions after the tick [mass fraction], the VLE
    #: domain the live volatility was evaluated in, and AI-328701 [uS/cm at 25 C].
    w: dict
    y_750: dict
    vle_domain: str | None
    ai_328701_us_cm: float
    #: True on a tick whose pressure took the backward step (B-51).
    pressure_backward: bool = False


@dataclass
class SecondDesorber:
    """328C004 as one node: holdup, pressure, temperature, species and the step."""

    #: Liquid holdup [kg], bottoms temperature [deg C] and the temperature on the tick before —
    #: the pressure step's thermal term, a tear, zero at the seed — and pressure [bar a].
    m_kg: float = C004_M_DES_KG
    t_c: float = C004_T_C
    t_prev_c: float = C004_T_C
    p_bara: float = C004_P_BARA
    #: The bottoms' composition, seeded on PFD 739, and the overhead's, on the back-solved
    #: design vapour.
    w: dict = field(default_factory=lambda: dict(W_S739))
    y_750: dict = field(default_factory=lambda: dict(DES_C004.y))
    #: 931 on the tick before [kg/h]: the ratio's numerator, V1's tear ``R328_M931``.
    m_931_prev_kgh: float = C004_M931_DES_KGH
    #: The 741 delivered on the last tick the heel capped it below FV-328406's ask, which
    #: FT-328406 reads on the next — None otherwise (decision 11).
    cap_741_kgh: float | None = None
    #: FV-329401's trim (decision 108's class, decided 2026-10-15); ``V1_FV_329401`` is V1's. Its
    #: xT enters the pressure term; FIC-329401's FlowLoop carries its curve and design stroke.
    fv_329401: ChestValve = FV_329401_TRIM

    def step(self, loops: SecondDesorberLoops, m_749_kgh: float, t_749_c: float, w_749: dict,
             m_735_kgh: float, p_c002_bara: float, t_740_c: float,
             dt: float, p_lp_bara: float = P_LP_BARA) -> SecondDesorberResult:
        """Advance 328C004 by one tick.

        Arguments
        ---------
        m_749_kgh, t_749_c, w_749
            The hydrolyser's bottoms after 328E021's hot side, this tick.
        m_735_kgh
            The desorbers' feed, the tank's draw this tick — FFIC-329401's base.
        p_c002_bara
            328C002's pressure after its step this tick — the overhead line's outlet.
        t_740_c
            328E007's hot outlet this tick (TT-328006): the temperature the bottoms reach
            LV-328505 at, so their vapour pressure there (B-46).
        p_lp_bara
            The LP header's pressure FV-329401 draws from (B-73); its default the header's design.

        The order is V1's: the ratio and the steam; the level loop, the recycle (V1 steps
        FIC-328406 in 328D003's stage) and the letdown; the duty, the boil-up and the overhead;
        the pressure on the OLD holdup and the tick before's temperature change; the bubble
        point, the holdup and the species.
        """
        t_pre = self.t_c
        cp = aqueous_cp(CP_DESORPTION, C004_T_C, t_pre)

        # ----- FFIC-329401, a ratio station on the desorbers' feed (B-39, B-49) -> FIC-329401 -
        # The achieved ratio, FFY-329401: V1 lags it with tau 0, the identity.
        feed_m3h = m_735_kgh / RHO_735_KGM3
        ffic_pv = (self.m_931_prev_kgh / 1000.0) / max(feed_m3h, FEED_FLOOR_M3H)
        ffic_op = loops.ffic_329401.step(
            ffic_pv, feed_m3h, slave_in_cascade=loops.fic_329401.loop.mode == "CAS")
        m_931 = loops.fic_329401.step(
            dt, cas_sp=ffic_op,
            pressure_ratio=fv_329401_pressure_ratio(p_lp_bara, self.p_bara + C004_DP_COL_BAR,
                                                    self.fv_329401.xt))
        m_in = m_749_kgh + m_931

        # ----- the duty and the boil-up: anchored on the design duty; a negative duty condenses
        # vapour (decision 15) -------------------------------------------------------------------
        sens = m_749_kgh / 3600.0 * cp * (t_749_c - t_pre)
        q = sens + m_931 / 3600.0 * C004_M931_DH_KJKG
        gen = C004_M750_DES_KGH * (q / C004_Q_DES_KW)

        # ----- LIC-328505 -> LV-328505 on its vendor trim (decision 23), or -> FIC-328406 ------
        level = self.m_kg / C004_M_DES_KG * C004_LEVEL_DES_PCT
        lic_op = loops.lic_328505.step(level, dt)
        # While FIC-328406 is external its set point is LIC-328505's output on FT-328406's span,
        # and a switch shuts LV-328505 (B-50, UD-MR-328-FF-0002 page 2). FT-328406 reads the
        # 741 delivered when the heel held it back (decision 11).
        recycle_cas = loops.fic_328406.loop.mode == "CAS"
        sp_741 = lic_op / 100.0 * FT_328406_SPAN_M3H * RHO_741_KGM3 if recycle_cas else None
        m_741 = loops.fic_328406.step(dt, cas_sp=sp_741, flow_cap=self.cap_741_kgh)
        lv_op = 0.0 if recycle_cas else lic_op
        head_m = self.m_kg / (C004_RHO_KGM3 * C004_AREA_M2)
        p1 = self.p_bara + C004_RHO_KGM3 * G_ACC * head_m / PA_PER_BAR
        # LV-328505 flashes where 740 boils above what the valve lets it down to (B-46): the
        # bottoms at 328E007's hot outlet, as liquid at most saturated at the valve's inlet.
        pv_740 = min(liquor_pv_bara(self.w, t_740_c), p1)
        m_export = valve_liquid_anchored(
            C004_M739_DES_KGH, lv_op / 100.0, p1, LV505_P2_BARA, C004_RHO_KGM3,
            LV505_OP_DES_PCT / 100.0, LV505_P1_DES_BARA, LV505_P2_BARA, C004_RHO_KGM3,
            characteristic=LV505_CHAR, fl=LV505_FL, pv_bara=pv_740,
            pv_des_bara=LV505_PV_DES_BARA)
        # The draws take only the liquid above the heel plus what arrives, net of what boils
        # (decisions 11, 24): the recycle first — in cascade the only draw — then the letdown.
        # Inert at every normal state.
        m_739_avail = max(max(self.m_kg - C004_M_FLOOR_KG, 0.0) / max(dt, DT_FLOOR_S) * 3600.0
                          + m_in - gen, 0.0)
        drain_lost = m_741 + m_export > m_739_avail
        self.cap_741_kgh = None
        if drain_lost:
            if m_741 > m_739_avail:
                m_741 = self.cap_741_kgh = m_739_avail
            m_export = min(m_export, m_739_avail - m_741)
        m_739 = m_export + m_741

        # ----- 750: what the overhead line passes to 328C002 (V1 report D-2) ------------------
        mw_750 = 1.0 / max(sum(self.y_750.get(k, 0.0) / MW[k] for k in SOLUTION_SPECIES),
                           INV_MW_FLOOR)

        def m_750_at(p_bara: float) -> float:
            """750 with the column at ``p_bara``: the line's compressible law, stroke fixed."""
            return valve_gas_anchored(
                C004_M750_DES_KGH, 1.0, p_bara, p_c002_bara, t_pre + ABSOLUTE_ZERO_C,
                1.0, C004_P_BARA, C002_P_TOP_BARA, C004_T_C + ABSOLUTE_ZERO_C, mw_750,
                characteristic="linear", mw_des=C004_MW750_DES)
        m_750 = m_750_at(self.p_bara)

        # ----- the holdup, less what boils (decision 24), and what a full shell cannot hold
        # (decision 11) -----------------------------------------------------------------------
        m_pre = self.m_kg
        m_new = max(m_pre + (m_in - gen - m_739) / 3600.0 * dt, C004_M_FLOOR_KG)
        m_overflow = 0.0
        if m_new > C004_FULL_KG:
            m_overflow = (m_new - C004_FULL_KG) / max(dt, DT_FLOOR_S) * 3600.0
            m_new = C004_FULL_KG

        # ----- the pressure: moles on the free volume, on the OLD holdup (V1 report A-6); the
        # backward step on a tick where the explicit one would ring (B-51) -------------------
        v_v = vapour_volume_m3(C004_VOL_M3, m_pre, C004_RHO_KGM3)
        dmdt = (m_in - gen - m_739 - m_overflow) / 3600.0
        dtdt = (t_pre - self.t_prev_c) / dt

        def dpdt(p_bara: float) -> float:
            """The column's dP/dt with the column at ``p_bara``, 750 with it."""
            return vessel_dpdt(
                p_bara, t_pre + ABSOLUTE_ZERO_C, v_v, mw_750,
                gen / mw_750, m_750_at(p_bara) / mw_750,
                dtdt_k_s=dtdt, dvvdt_m3_s=-dmdt / C004_RHO_KGM3)
        p_new, backward = stable_pressure_step(self.p_bara, dt, dpdt, C004_P_FLOOR_BARA)
        if backward:
            # 750 is what the line passes at the pressure the step settled on, so the moles the
            # head space lost are the moles 328C002 receives.
            m_750 = m_750_at(p_new)
        self.p_bara = max(p_new, C004_P_FLOOR_BARA)
        self.t_prev_c = t_pre

        # ----- the bubble point at the bottom node, and the holdup --------------------------
        self.t_c = iapws.tsat_c(self.p_bara + C004_DP_COL_BAR)
        self.m_kg = m_new

        # ----- the species: the LP steam the stripping agent ---------------------------------
        alpha, domain = alpha_live(C004_STAGE, self.t_c, m_931, m_739, self.w,
                                   self.p_bara + C004_DP_COL_BAR)
        self.w, self.y_750 = advance_species(
            self.w, self.m_kg, [(w_749, m_749_kgh), (W_STEAM, m_931)],
            gen, alpha, m_739 + m_overflow, 0.0, dt)
        self.m_931_prev_kgh = m_931

        # ----- AI-328701 on 740: CO2 left out, PFD 739 tabulates none (V1) -------------------
        ai = condensate_conductivity_us_cm(self.w["NH3"] * 1e6, self.w["Urea"] * 1e6, 0.0)

        return SecondDesorberResult(
            ffic_pv=ffic_pv, ffic_op_kgh=ffic_op, m_931_kgh=m_931, in_kgh=m_in,
            lic_pv_pct=level, lic_op_pct=lic_op, lv_op_pct=lv_op, m_739_kgh=m_739,
            m_export_kgh=m_export, m_741_kgh=m_741, drain_lost=drain_lost,
            q_kw=q, gen_kgh=gen, m_750_kgh=m_750, m_overflow_kgh=m_overflow,
            p_bara=self.p_bara, t_c=self.t_c, t_top_c=self.t_c - C004_DT_DES_K, m_kg=self.m_kg,
            level_pct=self.m_kg / C004_M_DES_KG * C004_LEVEL_DES_PCT,
            w=dict(self.w), y_750=dict(self.y_750), vle_domain=domain, ai_328701_us_cm=ai,
            pressure_backward=backward,
        )


__all__ = [
    "C004_P_FLOOR_BARA", "INV_MW_FLOOR", "FEED_FLOOR_M3H", "DT_FLOOR_S", "FV_329401_TRIM",
    "V1_FV_329401", "fv_329401_pressure_ratio",
    "ffic_329401", "fic_329401", "lic_328505", "fic_328406", "SecondDesorberLoops",
    "SecondDesorberResult", "SecondDesorber",
]
