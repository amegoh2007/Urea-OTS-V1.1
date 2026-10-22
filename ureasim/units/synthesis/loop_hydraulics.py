"""The HP synthesis loop's line pressures — where each unit sits against PT-329201.

What this models
----------------
The loop has one controlled pressure, PT-329201 on 322E003's overflow line (140.7 bar a at design),
and every unit sits a line's pressure drop away from it: the 322E001 tube side 3.3 bar above it,
322F001's suction 0.7 bar below and its diffuser 3.5 bar above, the reactor off-gas line 0.6 bar
above, the reactor's feed line from 322E002 to 322R001's top 2.9 bar below the condenser's outlet.
Each drop is a Darcy-Weisbach line on its own design point,

    dP = dP_des . (rho_des / rho) . (m / m_des)^2,

so a heavier load or a lighter fluid moves it the way it moves a real line, and at the design state
each factor is exactly 1.0 and the drop is the design differential to the bit. These are not unit
models: they are how the loop's units are told their own pressures, which V1 computes inline in
``step_sim`` between the unit calls.

Equations
---------
    P_strip  = P_syn + dP_strip,des (rho_207,des / rho_207) (m_207 / m_207,des)^2
    T_207    = T_207,des + (T_ovf - T_reactor,des)
    P_suct   = P_syn + (P_suct,des - P_syn,des)          P_disch = P_syn + (P_disch,des - P_syn,des)
    P_R001   = min(P_bub,E002, P_syn + dP_liq,des)
               - (P_E002,des - P_R001,top,des) (rho_feed,des / rho_feed) (m_feed / m_feed,des)^2
               [the cap: handoff B-109; the line on its design: handoff B-112; both 2026-10-22]
    P_og     = P_syn + (P_og,des - P_syn,des) (M_des / M) (T_og / T_og,des) (m_og / m_og,des)^2

The off-gas density ratio is the ideal gas's at the common line pressure. V1 wrote the reactor feed
line's "design differential" with the LIVE loop pressure (``state.p_syn_bara - 144.2``, -3.5 bar
at design) on the condenser's liquid make; the port's is the PFD's 144.2 - 141.3 on the seed's
feed (B-112), V1's kept on a switch. It reaches only the published PT on 322R001.

Source: V1 ``backend/main.py`` ``step_sim`` 7511-7512 (report D-6), 7563-7581 (the stripper's
dead-lever fix), 7743-7771 (the reactor's two lines, the off-gas parity fix).
"""

from __future__ import annotations

from ureasim.core.stream import MW_COMP
from ureasim.core.units_of_measure import ABSOLUTE_ZERO_C
from ureasim.data.unit_320 import SYN_P_DES_BARA
from ureasim.data.unit_322e001 import FEED_207_KMOLH, FEED_207_T_DES_C
from ureasim.data.unit_322e001 import P_DES_BARA as STRIP_P_DES_BARA
from ureasim.data.unit_322_loop import (
    LIQUOR_DP_DES_BAR,
    REACT_FEED_DP_DES_BAR,
    REACT_FEED_RHO_DES_LIVE,
)
from ureasim.data.unit_322e002 import P_DES_BARA as HPCC_P_DES_BARA
from ureasim.data.unit_322f001 import P_DISCHARGE_DES_BARA, P_SUCTION_DES_BARA
from ureasim.data.unit_322r001 import (
    OFFGAS_DES_KMOLH,
    OFFGAS_P_DES_BARA,
    OFFGAS_T_DES_C,
    OVERFLOW_RHO,
    OVERFLOW_RHO_DES_LIVE,
    REACTOR_T_DES_C,
)
from ureasim.data.synthesis_pin import HPCC_LIQ_DES_LIVE_KGH, REACT_ANCHOR_M_FEED_KGH
from ureasim.thermo.empirical import urea_soln_rho

__all__ = [
    "ejector_pressures_bara",
    "stripper_feed_t_c",
    "stripper_tube_bara",
    "reactor_bara",
    "reactor_offgas_bara",
]

#: The 207 run's design mass flow [kg/h] — the reactor overflow the stripper is fed at design.
_M_207_DES_KGH = max(sum(FEED_207_KMOLH.get(k, 0.0) * MW_COMP[k] for k in MW_COMP), 1e-6)
#: The off-gas line's design mass flow [kg/h], molar flow [kmol/h] and molar mass [kg/kmol], on
#: PFD 203, the reactor off-gas it carries.
_M_OG_DES_KGH = max(sum(OFFGAS_DES_KMOLH.get(k, 0.0) * MW_COMP[k] for k in MW_COMP), 1e-6)
_N_OG_DES = max(sum(OFFGAS_DES_KMOLH.get(k, 0.0) for k in MW_COMP), 1e-9)
_MW_OG_DES = sum(OFFGAS_DES_KMOLH.get(k, 0.0) * MW_COMP[k] for k in MW_COMP) / _N_OG_DES


def _mass_kgh(comp_kmolh: dict) -> float:
    return sum(comp_kmolh.get(k, 0.0) * MW_COMP[k] for k in MW_COMP)


def ejector_pressures_bara(p_syn_bara: float) -> tuple[float, float]:
    """322F001's suction and discharge [bar a] on the live loop, each on its design offset.

    Process utility
    ---------------
    The jet's lift is the design 4.2 bar at design and moves only when its two ends move apart; a
    loop excursion reaches the ejector instead of leaving its entrainment frozen (report D-6).
    """
    return (p_syn_bara + (P_SUCTION_DES_BARA - SYN_P_DES_BARA),
            p_syn_bara + (P_DISCHARGE_DES_BARA - SYN_P_DES_BARA))


def stripper_feed_t_c(t_overflow_c: float) -> float:
    """TT-322014 as the stripper's feed temperature [deg C]: the reactor's overflow on the 207
    run's design offset, exactly 183.0 at design (TD-006)."""
    return FEED_207_T_DES_C + (t_overflow_c - REACTOR_T_DES_C)


def stripper_tube_bara(p_syn_bara: float, overflow_kmolh: dict, t_feed_c: float) -> float:
    """322E001's tube-side pressure [bar a]: PT-329201 plus the 207 run's live drop.

    Process utility
    ---------------
    Loop pressure reaches the stripper's split through it: more pressure suppresses carbamate
    dissociation and the stripper visibly loses efficiency (V1's dead-lever fix). Normalised on the
    density the same correlation gives at the design overflow, so the design differential is 3.3
    bar to the bit.
    """
    m_live = max(_mass_kgh(overflow_kmolh), 1e-6)
    w_urea = overflow_kmolh.get("Urea", 0.0) * MW_COMP["Urea"] / m_live
    rho = urea_soln_rho(w_urea, t_feed_c, OVERFLOW_RHO)
    dp = ((STRIP_P_DES_BARA - SYN_P_DES_BARA) * (OVERFLOW_RHO_DES_LIVE / max(rho, 1e-6))
          * (m_live / _M_207_DES_KGH) ** 2)
    return p_syn_bara + dp


def reactor_bara(p_bub_bara: float, p_syn_bara: float, feed_kmolh: dict,
                 t_prod_c: float, flash_cap: bool = True, design_drop: bool = True) -> float:
    """PT on 322R001 [bar a]: 322E002's bubble pressure less the feed line's live drop.

    Process utility
    ---------------
    The reactor's published pressure, which the console and the stream inspector's PFD 207 read;
    no plant unit reads it, and 322R001 carries no transmitter of its own (P&ID 102). The feed
    line from 322E002 to the reactor's top is a Darcy-Weisbach line on its design point: the PFD's
    144.2 bar a less 141.3, 2.9 bar, at the density the same correlation gives at the design seed's
    feed and the seed's feed mass, so every factor is exactly 1.0 at design and the reading is PFD
    203/207's 141.3 (decided 2026-10-22, handoff B-112; decision 70's and A-13's classes). V1 wrote
    the differential as ``p_syn - 144.2`` on the live loop pressure — -3.5 bar at design, positive
    above 144.2 — on the nominal 990 kg/m3 and the condenser's liquid make, a factor of 2.31 at
    design: 136.12 bar a, and 2.31 bar more per bar of PT-329201. ``design_drop=False`` is V1's
    line, which the equivalence harness keeps.

    A melt whose bubble pressure stands above the pressure 322E002 sits at — PT-329201 plus its
    3.5 bar design head, where `liquor_saturation.saturation_fraction` finds it flashing — boils at
    that pressure and does not hold the reactor above it: the base is capped there (decided
    2026-10-22, handoff B-109; decision 70's class), so a CO2-rich melt's 216 bar a stays inside
    the melt's own model. Below the cap the base is the melt's bubble pressure, and at the design
    point, where the melt stands exactly at 322E002's pressure, the cap is its bubble pressure;
    ``flash_cap=False`` is V1's, which the equivalence harness keeps.

        P_R001 = min(P_bub, P_syn + dP_liquor,des)
                 - dP_feed,des (rho_feed,des / rho) (m_feed / m_feed,des)^2
    """
    if flash_cap:
        p_bub_bara = min(p_bub_bara, p_syn_bara + LIQUOR_DP_DES_BAR)
    m_live = max(_mass_kgh(feed_kmolh), 1e-6)
    w_urea = feed_kmolh.get("Urea", 0.0) * MW_COMP["Urea"] / m_live
    rho = urea_soln_rho(w_urea, t_prod_c, OVERFLOW_RHO)
    if design_drop:
        return p_bub_bara - (REACT_FEED_DP_DES_BAR * (REACT_FEED_RHO_DES_LIVE / max(rho, 1e-6))
                             * (m_live / REACT_ANCHOR_M_FEED_KGH) ** 2)
    dp = ((p_syn_bara - HPCC_P_DES_BARA) * (OVERFLOW_RHO / max(rho, 1e-6))
          * (m_live / max(HPCC_LIQ_DES_LIVE_KGH, 1e-6)) ** 2)
    return p_bub_bara + dp


def reactor_offgas_bara(p_syn_bara: float, offgas_kmolh: dict, t_offgas_c: float) -> float:
    """The reactor off-gas line's pressure into 322E003 [bar a].

    Process utility
    ---------------
    A change in the off-gas's composition or temperature moves its line's drop as well as a change
    in its flow (V1's parity fix): the ideal-gas density ratio at the common line pressure.
    """
    m_live = max(_mass_kgh(offgas_kmolh), 1e-6)
    n_live = max(sum(offgas_kmolh.get(k, 0.0) for k in MW_COMP), 1e-9)
    rho_fac = (_MW_OG_DES / max(m_live / n_live, 1e-9)) \
        * ((t_offgas_c + ABSOLUTE_ZERO_C) / (OFFGAS_T_DES_C + ABSOLUTE_ZERO_C))
    return (p_syn_bara + (OFFGAS_P_DES_BARA - SYN_P_DES_BARA) * rho_fac
            * (m_live / _M_OG_DES_KGH) ** 2)
