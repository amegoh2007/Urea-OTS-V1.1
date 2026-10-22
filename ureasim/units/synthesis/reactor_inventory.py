"""322R001 stepped — its recycle lags, its four node temperatures and its liquid holdup.

What this models
----------------
The reactor's dynamic states, which V1 integrates inline in ``step_sim`` around the pure reaction
function (`reactor.reactor_322r001`):

  1. **The reactor-feed drivers.** The fresh-feed N/C the pumps set (FFIC's ratio PV) is the
     disturbance; the recycle leg chases it through a first-order lag of the loop's inventory,
     tau_rec = 5 min, and the reactor sees the fresh fraction's blend, 30 % prompt and 70 % lagged.
     The feed's H/C blends the same way off the live 322E002 feed. The residence time the
     kinetics run on is the wetted volume over the liquid passing through it: the larger of what
     left the column and what entered its holdup on the tick before (handoff B-92, decided
     2026-10-14). V1 takes what left alone, so a reactor that fills without discharging has an
     endless residence and converts its whole feed, at any temperature.
  2. **The node temperatures.** Four nodes at the thermowells, each a lumped energy balance on the
     reaction heat its own extents release, dT_rxn = Q_n / (m_dot c_p), its upstream neighbour of
     the tick before, and a residence that stretches as the flow falls (`reactor_hydraulics
     .node_dtdt`), explicit Euler. The top node is TT-322014 and the off-gas temperature. No node
     stands above the liquor's bubble point at the live loop pressure: the excess heat flashes the
     overflow's volatiles into the off-gas (`reactor_boil`, handoff B-92, decided 2026-10-14; V1
     has no ceiling, and its nodes run away on a start-up).
  3. **The holdup.** d(m_liq)/dt = m_in - m_out + m_fwd. The production above design returns as a
     prompt fresh part and a recycle part lagged on the same tau_rec; HV-322605 and the funnel lip
     set m_out (`outlet_line_outflow_kgh`); a move of HV-322602 pumps a transient pulse of the
     scrubber's carbamate forward, the high-pass of the spindle's draw on an 8 min washout, drawn
     from 322E003's sump (handoff B-78 item 2, decided 2026-10-03; V1 draws it from nowhere). The
     production surge's recycle part is a lag with no inventory behind it, kept as V1 writes it
     (B-78 item 4, a Calibration Deferral). Liquid
     above the full vessel spills into the off-gas line to 322E003 (the carryover); the level is the
     holdup over its density; LT-322504 reads the head across its 1.5 m narrow band. A stripper whose
     tubes stand full of liquor takes only what it can pass (handoff B-104, decided 2026-10-22):
     m_out is capped at that, and what its tubes hand back past their ceiling returns to the holdup.
  4. **The stripper's feed.** What leaves through m_out is the 322E001 liquid feed of the next tick,
     the overflow composition scaled to that mass.

At the design seed every lag sits at its design, every surge and pulse is exactly zero and the
holdup is stationary, so the PFD state is reproduced to the bit.

Source
------
V1 ``backend/main.py`` ``step_sim`` 7722-7741 (Fix-3, the blended drivers), 7773-7821 (Fix-1, the
node profile; report A-8, the energy balance), 7869-7959 (the DOMINO inventory, Fix-2b, Fix-4,
the carryover, LT-322504's display); `data.synthesis_pin` for the boot-pinned anchors.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

from ureasim.core.numeric import clamp
from ureasim.core.stream import MW_COMP
from ureasim.data.synthesis_pin import (
    REACT_A2_PRE_PER_H,
    REACT_ANCHOR_LEVEL_FRAC,
    REACT_ANCHOR_M_FEED_KGH,
    REACT_ANCHOR_T_NODES_C,
    REACT_ANCHOR_VDOT_M3H,
    REACT_BIURET_A,
    REACT_CP_MELT_KJKGK,
    REACT_KEQ_OV_REF,
    REACT_L_FEED_DES,
    REACT_NODE_SS_DES_C,
    REACT_T_REF_K,
    REACT_TEAR_DES_KMOLH,
    REACT_X_DES,
)
from ureasim.data.unit_321 import RATIO_SP_DES
from ureasim.data.unit_322r001 import (
    AREA_M2,
    FRESH_FRAC,
    FWD_GAIN,
    FWD_TAU_MIN,
    HIC605_DES_PCT,
    LEVEL_DES_M,
    LEVEL_NLL_PCT,
    LIQ_H_M,
    LT_SPAN_M,
    M_HOLDUP_MIN,
    NC_LOOP_GAIN,
    OFFGAS_GAMMA,
    OFFGAS_P_DES_BARA,
    OVERFLOW_DES_KMOLH,
    OVERFLOW_T_DES_C,
    OFFGAS_T_DES_C,
    REACTOR_FEED_HC_DES,
    REACTOR_FEED_NC_DES,
    TAU_NODE_MIN,
    TAU_REC_MIN,
    WEIR_CREST_M,
    WEIR_CW,
)
from ureasim.units.synthesis.ejector import spindle_phi
from ureasim.units.synthesis.loop_hydraulics import reactor_bara, reactor_offgas_bara
from ureasim.units.synthesis.reactor import ColumnAnchor, ReactorResult, reactor_322r001
from ureasim.units.synthesis.reactor_boil import VOLATILES, node_boil
from ureasim.units.synthesis.reactor_column import ColumnKinetics
from ureasim.units.synthesis.reactor_hydraulics import (
    level_from_holdup,
    melt_density,
    node_dtdt,
    outlet_line_outflow_kgh,
)

__all__ = [
    "PINNED_KINETICS",
    "PINNED_ANCHOR",
    "M_LIQ_DES_KG",
    "M_OVERFLOW_DES_KGH",
    "ReactorStepResult",
    "ReactorInventory",
]

#: The rate laws on the boot pin's calibration (`data.synthesis_pin`).
PINNED_KINETICS = ColumnKinetics(a2_pre_per_h=REACT_A2_PRE_PER_H, keq_ov_ref=REACT_KEQ_OV_REF,
                                 t_ref_k=REACT_T_REF_K, biuret_a=REACT_BIURET_A)

#: The column state the pinned calibration was solved at.
PINNED_ANCHOR = ColumnAnchor(t_nodes_c=list(REACT_ANCHOR_T_NODES_C),
                             level_frac=REACT_ANCHOR_LEVEL_FRAC,
                             vdot_m3h=REACT_ANCHOR_VDOT_M3H, m_feed_kgh=REACT_ANCHOR_M_FEED_KGH)

#: The design production [kg/h]: the overflow vector's mass, HV-322605's design flow.
M_OVERFLOW_DES_KGH = sum(OVERFLOW_DES_KMOLH[k] * MW_COMP[k] for k in MW_COMP)

#: The design holdup [kg], on the pinned node profile's bulk temperature, so the seeded holdup and
#: the seeded profile are the same design point (V1 ``_rederive_react_bulk_anchors``).
M_LIQ_DES_KG = (melt_density(sum(REACT_NODE_SS_DES_C) / len(REACT_NODE_SS_DES_C)) * AREA_M2
                * (LEVEL_NLL_PCT / 100.0 * LIQ_H_M))


def _mass_kgh(comp_kmolh: dict, keys=None) -> float:
    """A stream's mass [kg/h], over its own species or, given ``keys``, over those (V1 sums some
    over ``MW_COMP`` and some over the stream's keys; the order is kept, so the bits are V1's)."""
    if keys is None:
        return sum(comp_kmolh[k] * MW_COMP[k] for k in comp_kmolh)
    return sum(comp_kmolh.get(k, 0.0) * MW_COMP[k] for k in keys)


@dataclass(frozen=True)
class ReactorStepResult:
    """One tick of 322R001: the reaction, the profile, the holdup and what leaves [kg/h, deg C]."""

    #: The pure reaction's result on this tick's drivers.
    reaction: ReactorResult
    #: The blended reactor-feed N/C and H/C the conversion ran on [-].
    l_blend: float
    w_blend: float
    #: The four node temperatures after the step (TT-322008 ... TT-322005), TT-322014 and the
    #: off-gas line's TT-322009 [deg C].
    t_nodes_c: tuple
    t_overflow_c: float
    t_offgas_c: float
    #: The live per-pass conversion over the pinned design's [-].
    conv_fac: float
    #: PT on 322R001 and on its off-gas line [bar a].
    p_bara: float
    p_offgas_bara: float
    #: The holdup's terms: the production in, HV-322605 / the lip out, the forward pulse.
    m_in_kgh: float
    m_out_kgh: float
    m_fwd_kgh: float
    #: Liquid spilled into the off-gas line to 322E003 [kg/h, kmol/h by species or None].
    carry_kgh: float
    carry_kmolh: dict | None
    #: The holdup [kg], its physical level and LT-322504's indication [%].
    m_liq_kg: float
    level_pct: float
    lt_322504_pct: float
    #: The stripper's liquid feed on the next tick [kmol/h] and its mass [kg/h].
    overflow_kmolh: dict
    overflow_kgh: float
    #: What the holdup gained this tick [kg/h], the liquid PT-329201's vapour does not count.
    dm_liq_kgh: float = 0.0
    #: The liquor's bubble temperature at the live pressure [deg C]; what the nodes' excess heat
    #: flashed off the overflow [kg/h]; the excess its volatiles could not pay [kJ/h] (B-92).
    t_bub_c: float = OFFGAS_T_DES_C
    boil_kgh: float = 0.0
    q_boil_unpaid_kjh: float = 0.0


@dataclass
class ReactorInventory:
    """322R001's states, seeded on the design (V1 ``State``)."""

    #: The lagged recycle N/C and H/C [-].
    l_rec: float = REACTOR_FEED_NC_DES
    w_rec: float = REACTOR_FEED_HC_DES
    #: The four node temperatures [deg C], the pinned design profile.
    t_nodes_c: list = field(default_factory=lambda: list(REACT_NODE_SS_DES_C))
    #: TT-322014 and TT-322009 [deg C].
    t_overflow_c: float = OVERFLOW_T_DES_C
    t_offgas_c: float = OFFGAS_T_DES_C
    #: The holdup [kg] and its level [% of the 25 m column]; LT-322504 [%].
    m_liq_kg: float = M_LIQ_DES_KG
    level_pct: float = LEVEL_NLL_PCT
    lt_322504_pct: float = LEVEL_NLL_PCT
    #: The production surge's lagged recycle leg [kg/h] and the forward pulse's washout [kg/h].
    m_in_lag_kgh: float = 0.0
    fwd_wash_kgh: float = 0.0
    #: The liquid that entered the holdup on the tick before [kg/h], the residence time's
    #: throughput while the reactor fills (B-92).
    m_in_prev_kgh: float = M_OVERFLOW_DES_KGH
    #: What leaves for the stripper, read by 322E001 on the next tick [kmol/h].
    overflow_kmolh: dict = field(default_factory=lambda: dict(OVERFLOW_DES_KMOLH))
    #: The reaction's feed N/C and H/C, read by 322E001's efficiency penalty next tick [-].
    l_feed: float = REACTOR_FEED_NC_DES
    w_feed: float = REACTOR_FEED_HC_DES
    #: PT on 322R001 on a melt flashing at 322E002's pressure, its base capped there (decided
    #: 2026-10-22, handoff B-109); False is V1's bubble pressure, which the harness keeps.
    flash_cap: bool = True
    #: Its feed line on the PFD's 144.2 - 141.3 at the seed's feed, 141.3 bar a at design (decided
    #: 2026-10-22, handoff B-112); False is V1's ``p_syn - 144.2`` line, which the harness keeps.
    design_drop: bool = True

    def step(self, hpcc, co2_feed_th: float, ratio_pv: float, hic605_pct: float,
             hic602_pct: float, suction_kgh: float, p_syn_bara: float,
             dt: float, sump_holdup_kg: float | None = None,
             m_out_cap_kgh: float | None = None, backup_kgh: float = 0.0) -> ReactorStepResult:
        """Advance the reactor one tick (module docstring, steps 1 to 4).

        ``hpcc`` is this tick's `carbamate_condenser.CondenserResult`; ``co2_feed_th`` the CO2 the
        loop receives after its line transit; ``ratio_pv`` this tick's fresh-feed N/C;
        ``suction_kgh`` 322F001's entrainment this tick; ``p_syn_bara`` PT-329201 of the tick
        before (the loop's declared tear); ``sump_holdup_kg`` 322E003's sump of the tick before,
        which the forward-carbamate pulse is drawn from (handoff B-78 item 2), or None for V1's
        pulse from nowhere; ``m_out_cap_kgh`` what 322E001's tubes can take of HV-322605's
        discharge this tick and ``backup_kgh`` what they handed back past their ceiling (handoff
        B-104), None and 0.0 for a stripper with room, V1's.
        """
        # ----- 1. the drivers: fresh N/C prompt, recycle lagged on the loop inventory ---------
        a_rec = dt / (TAU_REC_MIN * 60.0)
        l_fresh = REACTOR_FEED_NC_DES * (1.0 + NC_LOOP_GAIN * (ratio_pv / RATIO_SP_DES - 1.0))
        co2_fd = hpcc.feed_kmolh.get("CO2", 0.0)
        w_inst = (hpcc.feed_kmolh.get("H2O", 0.0) / co2_fd) if co2_fd > 0.0 \
            else REACTOR_FEED_HC_DES
        self.l_rec += a_rec * (l_fresh - self.l_rec)
        self.w_rec += a_rec * (w_inst - self.w_rec)
        l_blend = FRESH_FRAC * l_fresh + (1.0 - FRESH_FRAC) * self.l_rec
        w_blend = FRESH_FRAC * w_inst + (1.0 - FRESH_FRAC) * self.w_rec
        # The live throughput the residence time runs on, at the bulk density: the last overflow,
        # or, while the reactor fills, the liquid that entered its holdup (B-92).
        vdot = max(max(_mass_kgh(self.overflow_kmolh, MW_COMP), self.m_in_prev_kgh)
                   / max(melt_density(sum(self.t_nodes_c) / 4.0), 1e-6), 1e-6)

        react = reactor_322r001(
            hpcc.feed_kmolh, hpcc.gas_kmolh.get("CO2", 0.0), co2_feed_th, hic605_pct,
            p_syn_bara, PINNED_KINETICS, l_drive=l_blend, w_drive=w_blend,
            t_nodes_c=self.t_nodes_c, level_frac=self.level_pct / 100.0, vdot_m3h=vdot,
            anchor=PINNED_ANCHOR, tear_des_kmolh=dict(REACT_TEAR_DES_KMOLH),
            l_feed_des=REACT_L_FEED_DES, x_des_live=REACT_X_DES)

        # The published line pressures; the off-gas line reads TT-322009 of the tick before.
        p_r001 = reactor_bara(hpcc.p_bub_bara, p_syn_bara, react.feed_kmolh, hpcc.t_prod,
                              flash_cap=self.flash_cap, design_drop=self.design_drop)
        p_og = reactor_offgas_bara(p_syn_bara, react.offgas_kmolh, self.t_offgas_c)
        self.l_feed, self.w_feed = react.l_feed, react.w_feed

        # ----- 2. the node temperatures, each on its own reaction heat ------------------------
        conv_fac = react.x_conv / REACT_X_DES
        mcp_live = max(_mass_kgh(react.overflow_kmolh, MW_COMP), 1.0e-6) * REACT_CP_MELT_KJKGK
        dt_rxn = [q / mcp_live for q in react.q_nodes_kjh]
        t_old = list(self.t_nodes_c)
        t_og_prev = self.t_offgas_c
        t_up = hpcc.t_prod                     # node 0's upstream: the 322E002 product
        flow_frac = max(clamp(react.co2_scale, 0.0, 1.0), 1.0e-3)
        new_t, taus = [], []
        for n in range(4):
            # Residence stretches as the flow falls; the anchor-gated wall loss takes a stagnant
            # reactor to ambient instead of freezing it.
            tau_n = (TAU_NODE_MIN[n] * 60.0 / flow_frac) if flow_frac > 1.0e-9 else math.inf
            new_t.append(t_old[n] + node_dtdt(t_old[n], t_up, dt_rxn[n], tau_n, flow_frac) * dt)
            taus.append(tau_n)
            t_up = t_old[n]                    # the next node reads this one's previous tick
        # No node above the liquor's bubble point: the excess heat flashes the overflow's
        # volatiles into the off-gas (B-92). Nothing flashes at or below it — the design seed.
        boil = node_boil(new_t, p_syn_bara, mcp_live, taus, react.overflow_kmolh, dt)
        if boil.frac > 0.0:
            overflow = dict(react.overflow_kmolh)
            offgas = dict(react.offgas_kmolh)
            for k in VOLATILES:
                overflow[k] = overflow.get(k, 0.0) - boil.flash_kmolh[k]
                offgas[k] = offgas.get(k, 0.0) + boil.flash_kmolh[k]
            n_og = sum(offgas.values())
            react = replace(
                react, overflow_kmolh=overflow, offgas_kmolh=offgas,
                p_nh3_offgas_bara=offgas.get("NH3", 0.0) / n_og * OFFGAS_P_DES_BARA,
                p_co2_offgas_bara=offgas.get("CO2", 0.0) / n_og * OFFGAS_P_DES_BARA)
            p_og = reactor_offgas_bara(p_syn_bara, react.offgas_kmolh, t_og_prev)
        new_t = list(boil.t_nodes_c)
        self.t_nodes_c = new_t
        self.t_overflow_c = new_t[3]
        self.t_offgas_c = new_t[3] + OFFGAS_GAMMA * (self.t_overflow_c - new_t[3])

        # ----- 3. the holdup -------------------------------------------------------------------
        t_bulk = sum(new_t) / 4.0
        level_m = LIQ_H_M * self.level_pct / 100.0     # the head of the tick before
        m_ov_split = _mass_kgh(react.overflow_kmolh)
        # The production above design: its fresh part arrives at once, its recycle part through
        # the loop inventory on tau_rec, so HV-322605 keeps prompt authority over the level.
        m_surge = m_ov_split - M_OVERFLOW_DES_KGH
        self.m_in_lag_kgh += a_rec * (m_surge - self.m_in_lag_kgh)
        m_in = (M_OVERFLOW_DES_KGH + FRESH_FRAC * m_surge
                + (1.0 - FRESH_FRAC) * self.m_in_lag_kgh)
        m_out = outlet_line_outflow_kgh(level_m, M_OVERFLOW_DES_KGH, hic605_pct, HIC605_DES_PCT,
                                        WEIR_CREST_M, WEIR_CW, t_bulk)
        if m_out_cap_kgh is not None:
            # 322E001's tubes standing full take no more than they pass (B-104): the reactor keeps
            # the rest, and its level rises.
            m_out = min(m_out, max(m_out_cap_kgh, 0.0))
        # The forward-carbamate pulse: the spindle-attributable draw's high-pass residue, zero at
        # the design opening and at any steady one (Fix-4).
        phi_sp = max(spindle_phi(hic602_pct), 1e-6)
        fwd_drive = suction_kgh * (1.0 - 1.0 / phi_sp)
        self.fwd_wash_kgh += dt / (FWD_TAU_MIN * 60.0) * (fwd_drive - self.fwd_wash_kgh)
        m_fwd = FWD_GAIN * (fwd_drive - self.fwd_wash_kgh)
        if sump_holdup_kg is not None:
            # Drawn from 322E003's sump (decided 2026-10-03), so never more than it holds.
            m_fwd = min(m_fwd, max(sump_holdup_kg, 0.0) * (3600.0 / dt))
        m_liq_0 = self.m_liq_kg
        self.m_in_prev_kgh = m_in
        self.m_liq_kg += (m_in - m_out + m_fwd + backup_kgh) * (dt / 3600.0)
        self.m_liq_kg = max(self.m_liq_kg, M_HOLDUP_MIN)

        # ----- 4. the stripper's feed: what m_out carries, at the overflow's composition --------
        f_strip = (m_out / m_ov_split) if m_ov_split > 1.0e-9 else 1.0
        self.overflow_kmolh = {k: react.overflow_kmolh[k] * f_strip
                               for k in react.overflow_kmolh}

        # Above the full vessel the melt spills into the off-gas line to 322E003.
        m_full = melt_density(t_bulk) * AREA_M2 * LIQ_H_M
        carry_kgh = max(self.m_liq_kg - m_full, 0.0) * (3600.0 / dt)
        self.m_liq_kg = min(self.m_liq_kg, m_full)
        self.level_pct = clamp(level_from_holdup(self.m_liq_kg, t_bulk, AREA_M2) / LIQ_H_M
                               * 100.0, 0.0, 100.0)
        head_m = LIQ_H_M * self.level_pct / 100.0
        self.lt_322504_pct = clamp(LEVEL_NLL_PCT + (head_m - LEVEL_DES_M) / LT_SPAN_M * 100.0,
                                   0.0, 100.0)
        carry_kmolh = ({k: react.overflow_kmolh[k] * (carry_kgh / m_ov_split)
                        for k in react.overflow_kmolh}
                       if (carry_kgh > 0.0 and m_ov_split > 0.0) else None)

        return ReactorStepResult(
            reaction=react, l_blend=l_blend, w_blend=w_blend, t_nodes_c=tuple(new_t),
            t_overflow_c=self.t_overflow_c, t_offgas_c=self.t_offgas_c, conv_fac=conv_fac,
            p_bara=p_r001, p_offgas_bara=p_og, m_in_kgh=m_in, m_out_kgh=m_out, m_fwd_kgh=m_fwd,
            carry_kgh=carry_kgh, carry_kmolh=carry_kmolh, m_liq_kg=self.m_liq_kg,
            level_pct=self.level_pct, lt_322504_pct=self.lt_322504_pct,
            overflow_kmolh=dict(self.overflow_kmolh), overflow_kgh=m_out,
            dm_liq_kgh=(self.m_liq_kg - m_liq_0) * (3600.0 / dt),
            t_bub_c=boil.t_bub_c, boil_kgh=boil.m_kgh, q_boil_unpaid_kjh=boil.q_unpaid_kjh)
