"""PT-329201 — the HP synthesis loop's pressure, its vapour inventory integrated each tick.

What this models
----------------
The loop's pressure at the foot of V1's ``step_sim``, on the vapour the loop's four vessels hold
(handoff B-77 (b), decided 2026-10-09). The boundary's net flow goes to the liquid the model holds
and to the vapour; the vapour's share, on the gas's compressibility and the reactor liquor's
carbamate buffering, sets the pressure:

    (C_vap + C_buf) dP/dt = (m_in - m_out) - f_loop . s . R_des - m_relief
                            - dM_liq/dt + rho_g . dV_liq/dt,

    C_vap = V_v . MW / (Z_des . R . T),      V_v = V_loop - V_liq,
    C_buf = b_207 . M_R001,

with
    m_in   = the fresh ammonia (321P002 A/B), the CO2 to 322E001 and 323E003's 308 wash;
    m_out  = LV-322501's bottoms, HV-322604's purge, any stripper gas blowing through LV-322501, and
             a 322E002 tube leak into its shell (handoff B-82, zero but in the instructor's fault);
    R_des  = the residual the model's own design pins leave in that boundary, +2024.9 kg/h, credited
             back in proportion to the loop-mass fraction f_loop (the three liquid inventories over
             their normal levels, at most 1) so the design seed holds, and to the CO2 load ratio s
             the reactor scales the boot pin's recycle tear by, its mirror (handoff B-75);
    M_liq, V_liq = the liquid the model holds in the loop: 322R001's holdup (PFD 207's density),
             322E003's sump (PFD 206's), LT-322E002's holdup (its level law's own mass, 322E002's
             liquor's density) and LT-322501's sump between its taps (its datasheet geometry);
    V_loop = 241.7 m3, the four vessels' process sides on the vendor's drawings;
    rho_g  = the reactor top's vapour, P . MW / (Z_des . R . T) on 322R001's live off-gas and
             TT-322009, Z_des the PFD's 113.3 kg/m3 at 141.3 bar a and 183 C on the gas law;
    b_207  = what a kilogram of the reactor's liquor absorbs per bar, 1 / (P_207 . dln P_bub / dm),
             the Extended UNIQUAC bubble pressure of PFD 207 at 183 C (`thermo.vle`) differentiated
             in the design off-gas and lifted onto the stream's 141.3 bar a (V1's anchoring), about
             0.0154 kg/(kg.bar) — 2100 kg/bar on the design holdup (`liquor_saturation`); taken at
             the liquor's saturation fraction f, which falls from 1 as PT-329201 stands below the
             melt's bubble pressure (B-91 (a), decided 2026-10-10): a liquor above its bubble point
             takes up no more gas;
and clamped to [10, 180] bar a. The backlog — what 322E003 failed to condense less what recondenses
on its next pass, dM/dt = m_uncond - cool_frac . M / tau — no longer adds a pseudo-mass: the vapour
it holds is mass 322E003's sump did not receive, which the node already carries.

The loop relieves through 322R001's two certified safety valves SV32251 / SV32252 (decision 32's
class, handoff A-16): pop at set, Sempell's 10 % blowdown, API 520 on their certified capacity, the
reactor top's live vapour; never more in a tick than the node holds above the reseat pressure. V1
relieves through one assumed SV-32201.

Decided by the process engineer on 2026-10-03: the residual credit scales with the load ratio s,
as the recycle tear it mirrors does, so the two cancel at any load (handoff B-75; V1 credits the
design residual whatever the load); the backlog that recondenses returns to 322E003's sump, which
reads it on the next tick (B-76; V1 deletes it); and the node is the vapour inventory above, its
buffering anchored on the design liquor's solubility (B-77 (b), 2026-10-09). V1 integrates the
whole boundary on one lumped 1500 kg/bar with the backlog's pseudo-mass G_ph . m_vap,net, G_ph =
1 - rho_v / rho_l, so it counts every liquid holdup's mass a second time as pressure.

Source: V1 ``backend/main.py`` ``step_sim`` 10345-10445; `data.unit_322_loop`; the vendor's
arrangement drawings (UD-AU-322-DZ-0003/4/5/6-003); PFD stream 207 and the reactor's off-gas.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ureasim.core.numeric import clamp
from ureasim.core.relief import SafetyValve, psv_api520_choked_kgh, psv_area_from_rated_m2
from ureasim.core.stream import MW_COMP
from ureasim.core.units_of_measure import R_GAS_J_KMOL
from ureasim.data.unit_320 import SYN_P_DES_BARA
from ureasim.data.unit_322_loop import (
    LOOP_LEVEL_NLL_SUM_PCT,
    RHO_E002_LIQ,
    SV32251_CAP_KGH,
    SV32251_COUNT,
    SV32251_K,
    SV32251_MW_REL,
    SV32251_P_REL_BARA,
    SV32251_RESEAT_BARA,
    SV32251_SET_BARA,
    SV32251_T_REL_K,
    SV32251_Z_REL,
    SYN_LOOP_RESID_DES_KGH,
    SYN_LOOP_V_M3,
    SYN_P_CEILING_BARA,
    SYN_P_FLOOR_BARA,
    SYN_P_TAU_MIN,
)
from ureasim.data.unit_322e001 import LEVEL_SP_DES_PCT, RHO_BOTTOM
from ureasim.data.unit_322e002 import LEVEL_NLL_PCT as E002_LEVEL_NLL_PCT
from ureasim.data.unit_322e003 import HOLDUP_NLL_KG
from ureasim.data.unit_322f001 import RHO_SUCTION
from ureasim.data.unit_322r001 import (
    OFFGAS_DES_KMOLH,
    OFFGAS_P_DES_BARA,
    OFFGAS_RHO,
    OFFGAS_T_DES_C,
    OVERFLOW_RHO,
)
from ureasim.units.synthesis.condenser_holdup import E002_SPAN_KG
from ureasim.units.synthesis.liquor_saturation import B_207_PER_BAR, liquor_buffering_per_bar
from ureasim.units.synthesis.reactor_inventory import M_LIQ_DES_KG
from ureasim.units.synthesis.stripper_sump import SUMP_SPAN_KG as E001_SPAN_KG

__all__ = ["SV32251_AREA_M2", "R_BAR_M3", "Z_GAS_DES", "B_207_PER_BAR", "gas_mw",
           "liquor_buffering_per_bar", "loop_liquid", "liquid_growth",
           "vapour_capacity_kg_per_bar", "loop_mass_fraction", "LoopPressureResult",
           "LoopPressure"]

#: Each valve's effective orifice [m2], back-solved from its certified capacity on Sempell's
#: relieving state, so the forward law returns that capacity there.
SV32251_AREA_M2 = psv_area_from_rated_m2(SV32251_CAP_KGH, SV32251_P_REL_BARA, SV32251_T_REL_K,
                                         SV32251_MW_REL, k=SV32251_K, z=SV32251_Z_REL)

#: The gas constant in bar.m3/(kmol.K), the CODATA value the engine carries.
R_BAR_M3 = R_GAS_J_KMOL / 1.0e5


def gas_mw(kmolh: dict) -> float:
    """Mean molar mass of a gas [kg/kmol] — the vapour the loop's node holds."""
    return (sum(kmolh.get(k, 0.0) * MW_COMP[k] for k in MW_COMP)
            / sum(kmolh.get(k, 0.0) for k in MW_COMP))


#: The reactor top's vapour compressibility at design [-], about 0.76: the PFD's 113.3 kg/m3 at
#: 141.3 bar a and 183 C on the ideal gas law. Held for the live gas, so its density is the gas law
#: on the design's departure from ideality (V1's anchoring).
Z_GAS_DES = (OFFGAS_P_DES_BARA * gas_mw(OFFGAS_DES_KMOLH)
             / (R_BAR_M3 * (OFFGAS_T_DES_C + 273.15) * OFFGAS_RHO))


def loop_liquid(m_reactor_kg: float, m_scrubber_kg: float, condenser_level_pct: float,
                sump_level_pct: float, sump_span_kg: float = E001_SPAN_KG) -> tuple[float, float]:
    """The liquid the model holds in the loop's vessels: (mass [kg], volume [m3]).

    Process utility
    ---------------
    What the vapour does not occupy, and the mass the boundary's flow put into liquid rather than
    into pressure: 322R001's holdup, 322E003's sump with what the scrubber holds back, LT-322E002's
    and LT-322501's holdups, each at its PFD liquor's density. The stripper's falling film and the
    sump below LT-322501's lower tap are in no model state and are left in the vapour space.
    """
    m_e002 = condenser_level_pct / 100.0 * E002_SPAN_KG
    m_e001 = sump_level_pct / 100.0 * sump_span_kg
    m = m_reactor_kg + m_scrubber_kg + m_e002 + m_e001
    v = (m_reactor_kg / OVERFLOW_RHO + m_scrubber_kg / RHO_SUCTION + m_e002 / RHO_E002_LIQ
         + m_e001 / RHO_BOTTOM)
    return m, v


def liquid_growth(dm_reactor_kgh: float, dm_scrubber_kgh: float, dm_condenser_kgh: float,
                  dm_sump_kgh: float) -> tuple[float, float]:
    """What the loop's liquid gained this tick: (mass [kg/h], volume [m3/h]).

    Process utility
    ---------------
    The boundary's flow that went into liquid rather than into the vapour, each unit's holdup's
    own growth over its own step — so an initial condition written into a holdup between ticks is
    not mistaken for a flow — and the volume it took from the vapour.
    """
    dm = dm_reactor_kgh + dm_scrubber_kgh + dm_condenser_kgh + dm_sump_kgh
    dv = (dm_reactor_kgh / OVERFLOW_RHO + dm_scrubber_kgh / RHO_SUCTION
          + dm_condenser_kgh / RHO_E002_LIQ + dm_sump_kgh / RHO_BOTTOM)
    return dm, dv


def vapour_capacity_kg_per_bar(v_liq_m3: float, mw: float, t_gas_c: float,
                               vessels_m3: float = SYN_LOOP_V_M3) -> float:
    """The loop vapour's own capacity [kg/bar], V_v . MW / (Z_des . R . T).

    Process utility
    ---------------
    How much gas one bar puts into the vessels' free volume: about 80 kg/bar on the design holdups,
    some 200 kg/bar in an empty loop. The liquid the loop fills with takes the volume away.
    ``vessels_m3`` is the vessels' volume: the plant's by default, 322E001's replacement and the
    plugged tubes' bores out (decisions 154, 155).
    """
    return (vessels_m3 - v_liq_m3) * mw / (Z_GAS_DES * R_BAR_M3 * (t_gas_c + 273.15))



def loop_mass_fraction(reactor_level_pct: float, condenser_level_pct: float,
                       sump_level_pct: float) -> float:
    """The loop's liquid inventory over its normal [-], at most 1.

    Process utility
    ---------------
    How full the loop is: the residual credit rides on it, so a design-full loop holds PT-329201
    and an empty one integrates its raw balance — zero feeds create nothing (V1's G4 rule).
    """
    return clamp((reactor_level_pct + condenser_level_pct + sump_level_pct)
                 / LOOP_LEVEL_NLL_SUM_PCT, 0.0, 1.0)


@dataclass(frozen=True)
class LoopPressureResult:
    """One tick of PT-329201 [bar a, kg/h]."""

    p_syn_bara: float
    m_in_kgh: float
    m_out_kgh: float
    #: The residual credited this tick, f_loop . R_des.
    resid_credit_kgh: float
    #: The backlog's net growth and its recondensation [kg/h]; the backlog [kg].
    m_vap_net_kgh: float
    m_recond_kgh: float
    vap_excess_kg: float
    #: SV32251 / SV32252: lifted, relieved [kg/h], of which ammonia [kg/h].
    relief_lifted: bool
    m_relief_kgh: float
    m_relief_nh3_kgh: float
    #: The net rate the node integrated into its vapour and its liquors' buffering [kg/h].
    m_net_kgh: float
    loop_mass_frac: float
    #: The liquid the model holds in the loop [kg, m3]; what it gained this tick less the vapour it
    #: displaced [kg/h].
    m_liq_kg: float
    v_liq_m3: float
    dm_liq_kgh: float
    #: The node's capacity [kg/bar]: the vapour's and the reactor liquor's buffering.
    c_vap_kg_per_bar: float
    c_buf_kg_per_bar: float


@dataclass
class LoopPressure:
    """PT-329201 and the uncondensed backlog, seeded on the design (V1 ``State``)."""

    p_syn_bara: float = SYN_P_DES_BARA
    vap_excess_kg: float = 0.0
    sv_32251: SafetyValve = field(
        default_factory=lambda: SafetyValve("SV32251", SV32251_SET_BARA, SV32251_RESEAT_BARA))
    #: What the backlog recondensed on the last tick [kg/h], which 322E003's sump takes on the
    #: next (B-76).
    m_recond_kgh: float = 0.0
    #: The vessels open to the loop's gas [m3]: the plant's (decisions 154, 155); the harnesses
    #: run V1's plant's, ``SYN_LOOP_V_V1_M3``.
    vessels_m3: float = SYN_LOOP_V_M3
    #: LT-322501's sump over its span [kg], the stripper bundle's the plant runs (decision 154);
    #: the harnesses run V1's bundle's.
    e001_span_kg: float = E001_SPAN_KG

    def step(self, m_nh3_kgh: float, m_co2_kgh: float, m_308_kgh: float, m_drain_kgh: float,
             m_purge_kgh: float, m_blow_kgh: float, uncond_kgh: float, cool_frac: float,
             loop_frac: float, offgas_kmolh: dict, t_offgas_c: float, dt: float,
             load_ratio: float = 1.0, m_leak_kgh: float = 0.0,
             m_reactor_kg: float = M_LIQ_DES_KG, m_scrubber_kg: float = HOLDUP_NLL_KG,
             condenser_level_pct: float = E002_LEVEL_NLL_PCT,
             sump_level_pct: float = LEVEL_SP_DES_PCT,
             dm_liquid: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0),
             sat_frac: float = 1.0) -> LoopPressureResult:
        """Integrate the node one tick on this tick's boundary flows (module docstring).

        ``offgas_kmolh`` / ``t_offgas_c`` are 322R001's off-gas and TT-322009 this tick, the vapour
        the node holds and its safety valves would relieve; ``load_ratio`` the reactor's CO2 load
        ratio s this tick, 1.0 at design; ``m_leak_kgh`` 322E002's tube leak this tick
        (`tube_leak`); ``m_reactor_kg``, ``m_scrubber_kg``, ``condenser_level_pct`` and
        ``sump_level_pct`` the liquid the loop holds this tick, at the design by default, and
        ``dm_liquid`` what the reactor's, the scrubber's, the condenser's and the stripper sump's
        holdups gained over their own steps this tick [kg/h], none by default; ``sat_frac`` the
        liquor's saturation fraction this tick (`liquor_saturation.saturation_fraction`), 1 by
        default.
        """
        # The backlog: what failed to condense, less what condenses on its next pass.
        m_recond = cool_frac * self.vap_excess_kg / (SYN_P_TAU_MIN * 60.0) * 3600.0
        m_vap_net = uncond_kgh - m_recond
        self.vap_excess_kg = max(self.vap_excess_kg + m_vap_net * (dt / 3600.0), 0.0)
        self.m_recond_kgh = m_recond

        m_in = m_nh3_kgh + m_co2_kgh + m_308_kgh
        m_out = m_drain_kgh + m_purge_kgh + m_blow_kgh + m_leak_kgh
        credit = loop_frac * load_ratio * SYN_LOOP_RESID_DES_KGH

        # The vapour the loop holds: 322R001's live off-gas, or, a loop whose feed is cut, the
        # NH3-rich vapour space it still holds.
        p = self.p_syn_bara
        n_og = sum(offgas_kmolh.get(k, 0.0) for k in MW_COMP)
        m_og = sum(offgas_kmolh.get(k, 0.0) * MW_COMP[k] for k in MW_COMP)
        if m_og > 1.0 and n_og > 0.0:
            mw, y_nh3 = m_og / n_og, offgas_kmolh.get("NH3", 0.0) * MW_COMP["NH3"] / m_og
        else:
            m_des = sum(OFFGAS_DES_KMOLH[k] * MW_COMP[k] for k in OFFGAS_DES_KMOLH)
            mw = SV32251_MW_REL
            y_nh3 = OFFGAS_DES_KMOLH.get("NH3", 0.0) * MW_COMP["NH3"] / m_des

        # The liquid the boundary's flow went into this tick, and the volume it took from the
        # vapour, which compresses the gas it displaced.
        m_liq, v_liq = loop_liquid(m_reactor_kg, m_scrubber_kg, condenser_level_pct,
                                   sump_level_pct, self.e001_span_kg)
        rho_g = p * mw / (Z_GAS_DES * R_BAR_M3 * (t_offgas_c + 273.15))
        dm, dv = liquid_growth(*dm_liquid)
        dm_liq_kgh = dm - rho_g * dv
        c_vap = vapour_capacity_kg_per_bar(v_liq, mw, t_offgas_c, self.vessels_m3)
        c_buf = B_207_PER_BAR * m_reactor_kg
        if sat_frac < 1.0:
            c_buf *= sat_frac
        c = c_vap + c_buf

        # SV32251 / SV32252 on the reactor top, on its live vapour.
        m_relief = 0.0
        if self.sv_32251.step(p):
            p_free = p + ((m_in - m_out) - credit - dm_liq_kgh) / c * (dt / 3600.0)
            w = SV32251_COUNT * psv_api520_choked_kgh(SV32251_AREA_M2, p, t_offgas_c + 273.15, mw,
                                                      k=SV32251_K, z=SV32251_Z_REL)
            m_relief = min(w, max(p_free - SV32251_RESEAT_BARA, 0.0) * c * 3600.0 / dt)

        m_net = (m_in - m_out) - credit - dm_liq_kgh - m_relief
        self.p_syn_bara = clamp(p + m_net / c * (dt / 3600.0), SYN_P_FLOOR_BARA,
                                SYN_P_CEILING_BARA)
        return LoopPressureResult(
            p_syn_bara=self.p_syn_bara, m_in_kgh=m_in, m_out_kgh=m_out, resid_credit_kgh=credit,
            m_vap_net_kgh=m_vap_net, m_recond_kgh=m_recond, vap_excess_kg=self.vap_excess_kg,
            relief_lifted=self.sv_32251.lifted, m_relief_kgh=m_relief,
            m_relief_nh3_kgh=m_relief * y_nh3, m_net_kgh=m_net, loop_mass_frac=loop_frac,
            m_liq_kg=m_liq, v_liq_m3=v_liq, dm_liq_kgh=dm_liq_kgh, c_vap_kg_per_bar=c_vap,
            c_buf_kg_per_bar=c_buf)
