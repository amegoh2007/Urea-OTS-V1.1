"""The CO2 discharge line — a pressure node with volume, a check valve and a vent.

What this models
----------------
Everything between the 320K002 discharge and the 322E001 tie-in: the line itself, which holds
5234 kg of CO2 in 21.6 m3 and behaves exactly like a small vessel; the XV-322902 isolation and
the non-return valve at the tie-in; and PV-322203, the line vent to the LP safe header, under
PIC-322203.

Source
------
Ported from V1 ``backend/main.py``, the "CO2 feed line" and "320K002 ... CAPACITIVE pressure
NODE" blocks of `step_sim` (report D-5).

What this replaces, and why it matters
---------------------------------------
V1's own note is worth keeping in front of anyone who edits this file. The predecessor made
two assertions about the process OUTCOME and called them a model:

  * ``P_line = min(P_syn + dP_des, P_ceiling)`` — "the compressor always delivers exactly the
    design feed differential, until it cannot". No flow argument, so no operating point.
  * ``f_to_HP = g_HP / (g_HP + g_vent)`` with ``g = sqrt(dP)`` — a normalised conductance
    ratio, which forces the two branch flows to sum to the raw feed BY CONSTRUCTION. It cannot
    represent a vent wide open while the loop also draws hard, and it cannot let the node
    pressure fall below the loop pressure and shut the tie-in on its own.

Four statements replace them, and none is an assertion about the answer:

  1. **the machine is a boundary feed** (:mod:`.co2_compressor`): it pushes the demanded CO2
     into the node at whatever pressure the node presents (decided 2026-10-08; V1's machine ran
     a fitted map under an integral governor);
  2. **the branches meet at a node, and the node has a VOLUME.** Its mass balance is
     integrated, so machine delivery, HP draw and vent draw close on their own time constant
     instead of being forced to agree instantaneously;
  3. **the tie-in is a CHECK VALVE** — sqrt(dP) forward with no ceiling, hard zero below the
     crack pressure, hard zero in reverse;
  4. **the vent is a real compressible valve** on the anchored IEC 60534 law, so it chokes
     when it should.

Why the node is INTEGRATED and not solved
------------------------------------------
V1 first wrote the algebraic form — `machines.solve_node_pressure` on this node — and measured
it **diverging**: 140.70 to 135.16 bar a over 16,000 s, monotonic and accelerating. The
diagnosis was that a MASSLESS node has to satisfy its mass balance instantaneously, which
makes the branch far stiffer than the plant and hands the synthesis loop's own pressure
integrator a slow one-way term.

A real discharge line is not massless. So the node is integrated, through the same
:func:`ureasim.core.node.vessel_dpdt` every vessel in the plant uses — one equation, so a line
node and a vessel node cannot drift apart in convention:

    dP/dt = (R.T_line / V_line) . (n_machine - n_check - n_vent)

T_line is the aftercooled feed temperature and is a boundary, so its dT/dt term is a literal
0.0; the line holds no liquid, so the swell term is a literal 0.0 as well.

The steady state this settles on is the same statement the algebraic float used to ASSERT —
the check valve passes the machine's delivery when the differential is the design one, so
P_line tracks p_syn + 3.5 bar — but it is now an OUTCOME of a mass balance rather than an
axiom. Three behaviours the axiom could not produce come with it: the line lags (about 13 s on
the check valve's own gain), the tie-in SHUTS on reversal instead of merely passing zero, and a
line with no draw packs up until PIC-322203 vents it, rather than stopping at a `min()` against a
process design pressure. That last one matters for the loss-of-condensation chain, which used to
self-choke its own CO2 feed and could never reach the high-high trip.

**SV32064 relieves the node** (decided by the process engineer on 2026-10-09, handoff B-83,
option a). The line's certified safety valve, on CO02-320202 at the machine's discharge, lifts at
its set, 161.013 bar a, and vents the line's gas to atmosphere through its orifice — back-solved
from Sempell's certified 74 444 kg/h of CO2 at 177.013 bar a — until the node falls to its reseat,
145.013 bar a (decision 32's law, `core.relief`). V1 relieves nothing. PIC-322203's set point,
V1's 168.01 bar a, sits above the valve's set and is kept (option b was not taken), so with
XV-322902 shut the valve, not the vent, holds the line. At the design feed it stays lifted, the
line settling at 147.55 bar a where its orifice passes the whole 54.6 t/h — above its reseat, where
it would pass only 53.7; at a smaller feed it cycles between reseat and set (30 t/h: 17 lifts in
2,000 s).

Design closure is exact and by construction. At P_line = 144.2 and p_syn = 140.7 the check
valve sees exactly `CO2_DP_HP_DES`, so its ratio is a literal 1.0 and it passes `CO2_DES_KGH`;
the vent at zero opening passes exactly 0; the boundary delivers the design demand,
`CO2_DES_KGH`. The node imbalance is a literal 0.0 and so is dP/dt.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ureasim.control.process_loop import ProcessLoop
from ureasim.control.valve import check_valve_kgh, valve_gas_anchored
from ureasim.core.node import vessel_dpdt
from ureasim.core.numeric import clamp
from ureasim.core.relief import GasReliefValve, SafetyValve, psv_area_from_rated_m2
from ureasim.core.signal import dead_time
from ureasim.core.transport import line_residence_time_s
from ureasim.core.units_of_measure import NM3_PER_KMOL
from ureasim.data.unit_320 import (
    CO2_CHECK_CRACK_BAR,
    CO2_DP_HP_DES,
    CO2_FEED_MW,
    CO2_K_GAMMA,
    CO2_K_SUCT_P_BARA,
    CO2_LINE_V_M3,
    CO2_P_DES_BARA,
    CO2_T_FEED_C,
    CO2_VENT_MW_DES,
    CO2_VENT_P_BARA,
    CO2_VENT_T_DES_K,
    FEED_CO2_LINE_KG,
    PIC_322203_KC,
    PIC_322203_SP_HI_BARA,
    PIC_322203_SP_LO_BARA,
    PIC_322203_TI,
    PV_322203_CHAR,
    PV_322203_OP_DES_PCT,
    SV32064_CAP_KGH,
    SV32064_K,
    SV32064_MW_REL,
    SV32064_P_REL_BARA,
    SV32064_RESEAT_BARA,
    SV32064_SET_BARA,
    SV32064_T_REL_K,
    SV32064_Z_REL,
    SYN_PSV_SET_BARA,
    SYN_P_DES_BARA,
)
from ureasim.data.unit_321 import CO2_DES_KGH, FEED_TD_MAX_S
from ureasim.units.synthesis.co2_compressor import delivery_kgh

#: Key the battery-limit CO2 line's dead-time FIFO is stored under.
#: Source: V1 `main.py`, `_delay(s.tlag, "FEED_CO2", ...)`.
CO2_LINE_KEY = "FEED_CO2"

#: PIC-322203's design set point [bar a], about 168 — the PSV set plus twice the design
#: tie-in differential. Source: V1 `main.py`, the PIC-322203 state seed. It sits well above
#: the operating line pressure, so the vent is shut at design and the loop only acts on a
#: genuine line over-pressure.
PIC_322203_SP_DES_BARA = SYN_PSV_SET_BARA + 2.0 * (CO2_P_DES_BARA - SYN_P_DES_BARA)


def vent_pressure_loop() -> ProcessLoop:
    """PIC-322203 — the CO2 line vent controller, seeded at the design point.

    Process utility
    ---------------
    Direct acting: a rising line pressure opens the vent, which bleeds CO2 to a safe location
    so the feed to 322E001 falls and the N/C ratio and plant load follow it down. It is the
    line's first protection layer, below the relief.

    Equation
    --------
    V1 writes this loop inline in `step_sim` as

        du = Kc . [ (PV - PV_prev) + (dt/Ti)(PV - SP) ]
        op = clamp(op + du, 0, 100)

    which is `ProcessLoop` with ``act = -1`` and no derivative, term for term: negating the
    gain and both terms is exact in IEEE arithmetic, so on every finite measurement the two
    agree to the bit, and the equivalence test drives them side by side to show it.

    The one deliberate divergence from V1
    -------------------------------------
    V1 guards the increment against a non-finite PV but advances ``PV_prev`` regardless, so a
    single bad line-pressure sample poisons the next tick's proportional term and V1's
    limiter turns the NaN into its upper rail: the vent latches wide open one tick after the
    measurement recovers. `ProcessLoop` freezes the output AND the history on a bad sample,
    so a bad measurement costs one tick of control action and nothing else. The loop stays
    in the mode the operator left it in; it is not demoted to MAN. The process engineer
    chose this form; the As-Built reference, §XVII.5, records the decision.

    The measurement is one tick old
    -------------------------------
    The PV is written at the END of a tick from that tick's settled line pressure and read at
    the TOP of the next one (see `CO2FeedLine.step`). That is a declared tear, not a
    scheduling accident.
    """
    return ProcessLoop(
        tag="PIC-322203", Kc=PIC_322203_KC, Ti=PIC_322203_TI, act=-1.0,
        op=0.0, sp=PIC_322203_SP_DES_BARA,
        pv=CO2_P_DES_BARA, pv1=CO2_P_DES_BARA, pv2=CO2_P_DES_BARA,
        sp_lo=PIC_322203_SP_LO_BARA, sp_hi=PIC_322203_SP_HI_BARA)


def vent_flow_kgh(node_bara: float, opening_pct: float) -> float:
    """PV-322203 vent flow [kg/h], on the anchored IEC 60534 compressible law.

    Process utility
    ---------------
    A real compressible valve, so it chokes when it should — which matters here because the
    vent lets gas down from about 144 bar a to a 5 bar a header, a pressure ratio of 0.035,
    deeply choked at any meaningful opening.

    The anchor is CCI's own sizing: the design CO2 rate at the design line pressure, at the
    79.33 % stroke where the valve's rated Cv 32 passes it on its equal-percentage trim, so wide
    open it takes 2.2 times the feed — what makes it a protection layer rather than a trim
    (handoff B-44, decided 2026-09-30). V1 anchored the feed wide open on a linear trim.
    """
    return valve_gas_anchored(
        CO2_DES_KGH, opening_pct / 100.0, node_bara, CO2_VENT_P_BARA, CO2_VENT_T_DES_K,
        PV_322203_OP_DES_PCT / 100.0, CO2_P_DES_BARA, CO2_VENT_P_BARA, CO2_VENT_T_DES_K,
        CO2_VENT_MW_DES, gamma=CO2_K_GAMMA, characteristic=PV_322203_CHAR,
        mw_des=CO2_VENT_MW_DES)


def tie_in_flow_kgh(node_bara: float, syn_bara: float, feed_factor: float) -> float:
    """CO2 through the XV-322902 tie-in into 322E001 [kg/h].

    Process utility
    ---------------
    The non-return valve at the tie-in, anchored on the design differential. Forward it is a
    fixed resistance following sqrt(dP) with NO ceiling — a line pushing harder than design
    really does pass more. Below the crack pressure and in reverse it is exactly zero, because
    the disc is on its seat: when the synthesis loop over-pressures past the CO2 line, the
    feed stops rather than reversing into the compressor.

    ``feed_factor`` is XV-322902: 1.0 open, 0.0 shut. It multiplies rather than gating, so an
    isolated line still integrates its own pressure correctly with no draw.
    """
    return feed_factor * check_valve_kgh(
        CO2_DES_KGH, node_bara, syn_bara, CO2_DP_HP_DES, CO2_CHECK_CRACK_BAR)


def sv_32064() -> GasReliefValve:
    """SV32064, the line's safety valve, shut: set 161.013 bar a, reseating at 145.013, its
    orifice back-solved from its certified 74 444 kg/h of CO2 at 177.013 bar a (B-83).

    Process utility
    ---------------
    The last layer on the discharge line: a line with no way out — the tie-in shut, PV-322203
    held shut — stops at the valve's set instead of packing without limit, and the vent rate is
    what the field sees at the stack.
    """
    return GasReliefValve(
        valve=SafetyValve("SV32064", SV32064_SET_BARA, SV32064_RESEAT_BARA),
        area_m2=psv_area_from_rated_m2(SV32064_CAP_KGH, SV32064_P_REL_BARA, SV32064_T_REL_K,
                                       SV32064_MW_REL, k=SV32064_K, z=SV32064_Z_REL),
        k=SV32064_K)


@dataclass(frozen=True)
class CO2LineResult:
    """One tick of the CO2 feed line, as every downstream consumer reads it."""

    #: Settled line node pressure [bar a]. PIC-322203's PV.
    line_bara: float
    #: CO2 the machine pushed into the node this tick [kg/h].
    delivered_kgh: float
    #: CO2 through the tie-in to 322E001 [t/h] — what the ratio block divides by.
    feed_th: float
    #: The same feed [kg/h], as PT-329201's boundary balance counts it (V1 ``F_CO2_feed_kgh``).
    feed_kgh: float
    #: CO2 out of PV-322203 to the safe header [t/h].
    vent_th: float
    #: The same feed, delayed by the battery-limit transit [t/h]. What the LOOP receives.
    feed_to_loop_th: float
    #: Transit time currently applied to that stream [s].
    feed_dead_time_s: float
    #: FT-322403 normal-volume indication [Nm3/h] and FY-322403 mass indication [t/h].
    ft_322403_nm3h: float
    fy_322403_th: float
    #: Plant load as a per cent of the design CO2 rate.
    load_pct: float
    #: Effective PV-322203 opening [%] — the greater of the HIC minimum and the PIC output.
    vent_opening_pct: float
    #: Differentials the screens read [bar].
    dp_tie_in_bar: float
    dp_vent_bar: float
    #: What SV32064 vents of the line's gas to atmosphere [kg/h], the temperature it leaves at
    #: [deg C] — the line's — and True while it is lifted (B-83).
    relief_kgh: float = 0.0
    relief_t_c: float = CO2_T_FEED_C
    relief_lifted: bool = False


@dataclass
class CO2FeedLine:
    """The discharge line as one object: node, tie-in, vent and the boundary feeding it."""

    #: Line node pressure [bar a]. The state this module exists for.
    pressure_bara: float = CO2_P_DES_BARA
    #: HIC-322203 minimum vent opening [%], an operator hand station.
    hic_min_pct: float = 0.0
    #: XV-322902, the CO2 feed isolation to 322E001.
    xv_322902_open: bool = True
    #: Dead-time FIFO for the battery-limit CO2 line.
    line_state: dict = field(default_factory=dict)
    #: SV32064, the line's certified relief (B-83).
    sv_32064: GasReliefValve = field(default_factory=sv_32064)

    def step(self, pic: ProcessLoop, raw_demand_th: float,
             syn_bara: float, dt: float) -> CO2LineResult:
        """Advance the vent loop, the boundary feed and the node by one tick.

        The order is the plant's own and is not interchangeable. In particular the two branch
        flows are evaluated TWICE and for different purposes: once at the PREVIOUS pressure to
        form the node's mass balance, and once at the SETTLED pressure to report what actually
        went where. Using the settled pressure in the balance would make the integration
        implicit in its own result; using the previous pressure in the report would publish a
        flow the line did not pass.
        """
        # ----- PV-322203 effective opening ------------------------------------------------
        # The greater of the operator's hand-station minimum and the controller's output, so
        # HIC-322203 can force a vent open but cannot force one shut.
        pic.step(pic.pv, dt)
        vent_opening = clamp(max(self.hic_min_pct, pic.op), 0.0, 100.0)
        feed_factor = 1.0 if self.xv_322902_open else 0.0

        # ----- the boundary feed: 320K002's hardwired governor holds the demand -----------
        delivered_kgh = delivery_kgh(raw_demand_th * 1000.0)
        previous_bara = self.pressure_bara

        # ----- the node's own mass balance ------------------------------------------------
        # Molar, because dP/dt needs MOLES: the line and every vessel on the plant use the
        # same equation so their conventions cannot drift apart.
        into_node = delivered_kgh
        out_of_node = (tie_in_flow_kgh(previous_bara, syn_bara, feed_factor)
                       + vent_flow_kgh(previous_bara, vent_opening))
        p_free = previous_bara + vessel_dpdt(
            previous_bara, CO2_VENT_T_DES_K, CO2_LINE_V_M3, CO2_FEED_MW,
            into_node / CO2_FEED_MW, out_of_node / CO2_FEED_MW) * dt
        # ----- SV32064: lifted at its set pressure, it vents the line's gas to atmosphere
        # until the node falls to its reseat pressure (B-83) ------------------------------
        relief_kgh = self.sv_32064.vent_kgh(previous_bara, p_free, CO2_VENT_T_DES_K,
                                            CO2_FEED_MW, CO2_LINE_V_M3, dt)
        if relief_kgh > 0.0:
            p_free += vessel_dpdt(previous_bara, CO2_VENT_T_DES_K, CO2_LINE_V_M3, CO2_FEED_MW,
                                  0.0, relief_kgh / CO2_FEED_MW) * dt
        self.pressure_bara = max(p_free, CO2_K_SUCT_P_BARA)
        line_bara = self.pressure_bara

        # ----- what actually went where, at the settled pressure --------------------------
        feed_kgh = tie_in_flow_kgh(line_bara, syn_bara, feed_factor)
        vent_kgh = vent_flow_kgh(line_bara, vent_opening)
        feed_th = feed_kgh / 1000.0

        # ----- the battery-limit transit --------------------------------------------------
        # The CO2 the loop receives NOW left the battery-limit meter up to 345 s ago. The
        # indications below read the LIVE meter, which is why they are computed before this.
        td_s = line_residence_time_s(FEED_CO2_LINE_KG, 1.0, feed_kgh, t_max_s=FEED_TD_MAX_S)
        feed_to_loop_th = dead_time(self.line_state, CO2_LINE_KEY, feed_th, td_s, dt)

        pic.pv = line_bara              # the reading PIC-322203 acts on next tick

        return CO2LineResult(
            line_bara=line_bara,
            delivered_kgh=delivered_kgh,
            feed_th=feed_th,
            feed_kgh=feed_kgh,
            vent_th=vent_kgh / 1000.0,
            feed_to_loop_th=feed_to_loop_th,
            feed_dead_time_s=td_s,
            ft_322403_nm3h=feed_kgh / CO2_FEED_MW * NM3_PER_KMOL,
            fy_322403_th=feed_th,
            load_pct=feed_th / (CO2_DES_KGH / 1000.0) * 100.0,
            vent_opening_pct=vent_opening,
            dp_tie_in_bar=max(line_bara - syn_bara, 0.0),
            dp_vent_bar=max(line_bara - CO2_VENT_P_BARA, 0.0),
            relief_kgh=relief_kgh,
            relief_lifted=self.sv_32064.valve.lifted,
        )



__all__ = [
    "CO2_LINE_KEY",
    "PIC_322203_SP_DES_BARA",
    "vent_pressure_loop",
    "vent_flow_kgh",
    "tie_in_flow_kgh",
    "sv_32064",
    "CO2LineResult",
    "CO2FeedLine",
]
