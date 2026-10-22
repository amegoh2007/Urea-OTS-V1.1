"""Unit 329's valves — the butterflies on V1's anchored law, the globes on their vendor trims.

What this models
----------------
The eleven valves of the steam network:

  * **the butterflies** — PV-329204 (supply -> 329D005), HV-329601 (329D005 -> the silencer),
    PV-329207A (LP header -> atmosphere), PV-329207B (-> turbine 320MT02), PV-329207C and
    HV-329602 (supply -> LP header). V1 runs every one on its ISA-75.01 compressible law
    anchored on each valve's own design node pressures:

        m = K (op / 100) sqrt(dP_des) . Phi(live) / Phi(design)
        Phi = P1 Y sqrt(x M / (T1 Z)),  x = min(dP / P1, F_gamma xT),  Y = 1 - x / (3 F_gamma xT)

    on the IEC globe xT of 0.75 and a linear trim, T1 the upstream header's saturation
    temperature. The min() is the choke: four of them (HV-329601, PV-329207A, PV-329207C,
    HV-329602) run choked whenever open, their flow a function of the upstream pressure alone.
    Since 2026-10-15 (decision 108's class) PV-329204, PV-329207A and PV-329207B run Metso's
    Neldisc trims instead — the same law, anchored on each valve's design flow at its design stroke
    on its printed points and its normal case's xT (`pv_329204_kgs`, `pv_329207a_kgs`,
    `pv_329207b_kgs`). Since 2026-10-22 (decision 150) the other three run the vendor sheets found
    in session 69 — they are globes, not butterflies: HV-329601 and PV-329207C Flowserve Mark Ones,
    HV-329602 a Fisher — each anchored on its full-stroke capacity on its normal case
    (`hv_329601_kgs`, `pv_329207c_kgs`, `hv_329602_kgs`).

  * **the globes** (decision 23, §5 rule 7) — PV-329205A (supply -> 329D009) and PV-329205B
    (329D009 -> LP header) on Flowserve's modified equal-percentage trims and xT; LV-329502
    (329D005 -> 329D009), LV-329503 (329D009 -> 322D001) and LV-329504 (329P001A/B -> 322D001)
    on theirs and their FL, each anchored on its design flow at its design stroke
    (`control.valve.valve_gas_anchored`, `valve_liquid_anchored`). The two drum-to-drum letdowns
    pass saturated condensate and are handed its vapour pressure, their upstream drum's
    (decision 31), so they choke on FL^2 (P1 - FF Pv) as Flowserve sized them.

Source
------
V1 ``backend/steam_system.py`` ``_valve_flow`` (ported verbatim) and its ``_level_loop``'s valve
call; Flowserve's calculation sheets, Pos. 68-70, 74, 75 (`ureasim.data.control_valves`);
As-Built Parts LIII and LIV.
"""

from __future__ import annotations

from ureasim.control.valve import (
    XT_GLOBE,
    compressible_shape,
    valve_gas_anchored,
    valve_liquid_anchored,
)
from ureasim.data.control_valves import (
    HV_329601,
    LV_329502,
    LV_329503,
    LV_329504,
    PV_329204,
    PV_329205A,
    PV_329205B,
    PV_329207A,
    PV_329207B,
    PV_329207C,
)
from ureasim.data.control_valves_fisher import HV_329602
from ureasim.data.unit_329 import (
    P_916_BARA,
    P_ATM_VENT_BARA,
    P_HP_BARA,
    P_LP_BARA,
    P_MP_BARA,
    P_SUP_BARA,
    P_TURBINE_OUT_BARA,
    RHO_916_KGM3,
    STEAM_GAMMA,
    STEAM_MW,
    STEAM_PFD_KGH,
    T_916_C,
)
from ureasim.data.unit_329_network import (
    HV601_FULL_KGS,
    HV601_FULL_P1_BARA,
    HV601_FULL_P2_BARA,
    HV601_XT,
    HV602_FULL_KGS,
    HV602_P1_DES_BARA,
    HV602_P2_DES_BARA,
    HV602_XT,
    LV502_FL,
    LV502_OP_DES_PCT,
    LV503_FL,
    LV503_OP_DES_PCT,
    LV504_FL,
    LV504_OP_DES_PCT,
    M_502_DES_KGS,
    M_503_DES_KGS,
    M_504_DES_KGS,
    M_903_DES_KGS,
    PV205A_OP_DES_PCT,
    PV205A_XT,
    PV205B_FULL_KGS,
    PV205B_P1_DES_BARA,
    PV205B_P2_DES_BARA,
    PV205B_XT,
    PV204_OP_DES_PCT,
    PV204_XT,
    PV207A_FULL_KGS,
    PV207A_P1_DES_BARA,
    PV207A_P2_DES_BARA,
    PV207A_XT,
    PV207B_OP_DES_PCT,
    PV207B_XT,
    PV207C_FULL_KGS,
    PV207C_P1_DES_BARA,
    PV207C_P2_DES_BARA,
    PV207C_XT,
)
from ureasim.thermo.iapws import psat_bara, tsat_c
from ureasim.thermo.water_steam import rho_drum_liquid_kgm3

#: The condensate 329P001A/B deliver to LV-329504 boils at [bar a]: 916's 100 C (Flowserve's
#: sheet prints 1 bar on every case).
PV_916_BARA = psat_bara(T_916_C)


def _clamp_pct(op: float) -> float:
    return max(0.0, min(100.0, op))


def steam_valve_kgs(k: float, opening_pct: float, p_up: float, p_down: float,
                    p_up_des: float | None = None, p_down_des: float | None = None) -> float:
    """A butterfly's steam flow [kg/s] on V1's anchored ISA-75.01 law (V1 ``_valve_flow``).

    Process utility
    ---------------
    What a pressure-control butterfly passes between two headers, choking where its pressure
    ratio says it must: a header that depressurises does not pull an unbounded flow through the
    make-up valves. The defaults make the live pressures their own design (a vent), where the
    bracket is exactly 1.0. Equation in the module docstring.
    """
    op = _clamp_pct(opening_pct)
    if op <= 0.0:
        return 0.0
    p1d = p_up if p_up_des is None else p_up_des
    p2d = p_down if p_down_des is None else p_down_des
    dp_des = max(p1d - p2d, 0.0)
    if dp_des <= 0.0:
        return 0.0
    ref = compressible_shape(1.0, p1d, p2d, tsat_c(p1d) + 273.15, STEAM_MW, STEAM_GAMMA, 1.0,
                             "linear", XT_GLOBE)
    if ref <= 0.0:
        return 0.0
    live = compressible_shape(1.0, p_up, p_down, tsat_c(max(p_up, 1e-6)) + 273.15, STEAM_MW,
                              STEAM_GAMMA, 1.0, "linear", XT_GLOBE)
    return k * (op / 100.0) * dp_des ** 0.5 * (live / ref)


def pv_329204_kgs(opening_pct: float, p_sup_bara: float, p_hp_bara: float) -> float:
    """PV-329204's superheated supply into 329D005 [kg/s], on Metso's trim (decided 2026-10-15).

    Process utility
    ---------------
    PIC-329204's valve: the 25 bar a import that holds 329D005, and with it 322E001's shell, at
    19.7 bar a — PFD 902's 57 989 kg/h at its 44.1 % design stroke, more as the stripper draws more.
    """
    return valve_gas_anchored(
        STEAM_PFD_KGH["902"] / 3600.0, _clamp_pct(opening_pct) / 100.0, p_sup_bara, p_hp_bara,
        tsat_c(max(p_sup_bara, 1e-6)) + 273.15, PV204_OP_DES_PCT / 100.0, P_SUP_BARA, P_HP_BARA,
        tsat_c(P_SUP_BARA) + 273.15, STEAM_MW, STEAM_GAMMA,
        characteristic=PV_329204.characteristic, xt=PV204_XT)


def pv_329207a_kgs(opening_pct: float, p_lp_bara: float) -> float:
    """PV-329207A's vent from the LP header to atmosphere [kg/s], on Metso's trim (2026-10-15).

    Process utility
    ---------------
    The trio's top leg, shut at design: it opens above the header's set point plus its dead band
    and dumps what the users do not take. Anchored on its full stroke on its normal case, 165 770
    kg/h from 4.4 bar a, choked against the atmosphere.
    """
    return valve_gas_anchored(
        PV207A_FULL_KGS, _clamp_pct(opening_pct) / 100.0, p_lp_bara, P_ATM_VENT_BARA,
        tsat_c(max(p_lp_bara, 1e-6)) + 273.15, 1.0, PV207A_P1_DES_BARA, PV207A_P2_DES_BARA,
        tsat_c(PV207A_P1_DES_BARA) + 273.15, STEAM_MW, STEAM_GAMMA,
        characteristic=PV_329207A.characteristic, xt=PV207A_XT)


def pv_329207b_kgs(opening_pct: float, p_lp_bara: float) -> float:
    """PV-329207B's export from the LP header to turbine 320MT02 [kg/s], PFD 932, on Metso's trim.

    Process utility
    ---------------
    The trio's middle leg, the header's working pressure control: 16 707 kg/h at its design stroke
    (decided 2026-10-15), more as the header rises.
    """
    return valve_gas_anchored(
        STEAM_PFD_KGH["932"] / 3600.0, _clamp_pct(opening_pct) / 100.0, p_lp_bara,
        P_TURBINE_OUT_BARA, tsat_c(max(p_lp_bara, 1e-6)) + 273.15, PV207B_OP_DES_PCT / 100.0,
        P_LP_BARA, P_TURBINE_OUT_BARA, tsat_c(P_LP_BARA) + 273.15, STEAM_MW, STEAM_GAMMA,
        characteristic=PV_329207B.characteristic, xt=PV207B_XT)


def hv_329601_kgs(opening_pct: float, p_hp_bara: float) -> float:
    """HV-329601's vent from 329D005 to the 329D010 silencer [kg/s], on Flowserve's Mark One sheet
    (decided 2026-10-22, decision 150).

    Process utility
    ---------------
    329D005's blow-off, shut at design: trip 21.2 forces it open to bring the HP saturator, and
    322E001's shell with it, down fast. Equal percentage, Kv 64, anchored on its full stroke on
    its normal case — 16 151 kg/h from 19.9 bar a, choked against the silencer.
    """
    return valve_gas_anchored(
        HV601_FULL_KGS, _clamp_pct(opening_pct) / 100.0, p_hp_bara, P_ATM_VENT_BARA,
        tsat_c(max(p_hp_bara, 1e-6)) + 273.15, 1.0, HV601_FULL_P1_BARA, HV601_FULL_P2_BARA,
        tsat_c(HV601_FULL_P1_BARA) + 273.15, STEAM_MW, STEAM_GAMMA,
        characteristic=HV_329601.characteristic, xt=HV601_XT)


def pv_329207c_kgs(opening_pct: float, p_lp_bara: float) -> float:
    """PV-329207C's admission from the supply to the LP header [kg/s], PFD 963, on Flowserve's Mark
    One MegaStream sheet (decided 2026-10-22, decision 150).

    Process utility
    ---------------
    The trio's bottom leg, shut at design: it makes up the header from the 25 bar a supply when
    the header falls below its set point. Linear, Kv 172, anchored on its full stroke on its
    normal case — 34 882 kg/h from 22.0 to 4.4 bar a.
    """
    return valve_gas_anchored(
        PV207C_FULL_KGS, _clamp_pct(opening_pct) / 100.0, P_SUP_BARA, p_lp_bara,
        tsat_c(P_SUP_BARA) + 273.15, 1.0, PV207C_P1_DES_BARA, PV207C_P2_DES_BARA,
        tsat_c(PV207C_P1_DES_BARA) + 273.15, STEAM_MW, STEAM_GAMMA,
        characteristic=PV_329207C.characteristic, xt=PV207C_XT)


def hv_329602_kgs(opening_pct: float, p_lp_bara: float) -> float:
    """HV-329602's admission from the supply to the LP header [kg/s], beside PV-329207C, on Fisher's
    sheet (decided 2026-10-22, decision 150).

    Process utility
    ---------------
    The make-up's hand valve, shut at design. Linear, Cv 228, xT 0.532, anchored on its full stroke
    on its normal case — 39 233 kg/h from 22.0 to 4.4 bar a.
    """
    return valve_gas_anchored(
        HV602_FULL_KGS, _clamp_pct(opening_pct) / 100.0, P_SUP_BARA, p_lp_bara,
        tsat_c(P_SUP_BARA) + 273.15, 1.0, HV602_P1_DES_BARA, HV602_P2_DES_BARA,
        tsat_c(HV602_P1_DES_BARA) + 273.15, STEAM_MW, STEAM_GAMMA,
        characteristic=HV_329602.characteristic, xt=HV602_XT)


def pv_329205a_kgs(opening_pct: float, p_sup_bara: float, p_9_bara: float) -> float:
    """PV-329205A's superheated steam into 329D009 [kg/s], on its vendor trim.

    Process utility
    ---------------
    PIC-329205's first leg: the 25 bar a make-up that holds the 9-bar header when its users
    draw more than LV-329502's flash supplies — 1754 kg/h at design (PFD 903), at 19.55 %.
    """
    return valve_gas_anchored(
        M_903_DES_KGS, _clamp_pct(opening_pct) / 100.0, p_sup_bara, p_9_bara,
        tsat_c(max(p_sup_bara, 1e-6)) + 273.15, PV205A_OP_DES_PCT / 100.0, P_SUP_BARA,
        P_MP_BARA, tsat_c(P_SUP_BARA) + 273.15, STEAM_MW, STEAM_GAMMA,
        characteristic=PV_329205A.characteristic, xt=PV205A_XT)


def pv_329205b_kgs(opening_pct: float, p_9_bara: float, p_lp_bara: float) -> float:
    """PV-329205B's letdown from 329D009 to the LP header [kg/s], on its vendor trim.

    Process utility
    ---------------
    PIC-329205's second leg, shut at design (PFD 960): once PV-329205A is shut, a 9-bar header
    with more steam than users spills it to the LP header. Anchored on its full stroke on
    Flowserve's normal case, 10 486 kg/h at 8.9 -> 4.4 bar a.
    """
    return valve_gas_anchored(
        PV205B_FULL_KGS, _clamp_pct(opening_pct) / 100.0, p_9_bara, p_lp_bara,
        tsat_c(max(p_9_bara, 1e-6)) + 273.15, 1.0, PV205B_P1_DES_BARA, PV205B_P2_DES_BARA,
        tsat_c(PV205B_P1_DES_BARA) + 273.15, STEAM_MW, STEAM_GAMMA,
        characteristic=PV_329205B.characteristic, xt=PV205B_XT)


def lv_329502_kgs(opening_pct: float, p_hp_bara: float, p_9_bara: float) -> float:
    """LV-329502's condensate from 329D005 to 329D009 [kg/s], on its vendor trim.

    Process utility
    ---------------
    LIC-329502's drain of the stripper's returning condensate (PFD 904). The liquor is saturated
    at 329D005's pressure, so it flashes in the trim and chokes on FL^2 (P1 - FF Pv): its flow
    follows 329D005's pressure, not 329D009's, as long as it stays choked.
    """
    return valve_liquid_anchored(
        M_502_DES_KGS, _clamp_pct(opening_pct) / 100.0, p_hp_bara, p_9_bara,
        rho_drum_liquid_kgm3(p_hp_bara), LV502_OP_DES_PCT / 100.0, P_HP_BARA, P_MP_BARA,
        rho_drum_liquid_kgm3(P_HP_BARA), characteristic=LV_329502.characteristic, fl=LV502_FL,
        pv_bara=p_hp_bara, pv_des_bara=P_HP_BARA)


def lv_329503_kgs(opening_pct: float, p_9_bara: float, p_lp_bara: float) -> float:
    """LV-329503's condensate from 329D009 to 322D001 [kg/s], on its vendor trim.

    Process utility
    ---------------
    LIC-329503's drain (PFD 913), saturated at 329D009's pressure and choking as it flashes.
    """
    return valve_liquid_anchored(
        M_503_DES_KGS, _clamp_pct(opening_pct) / 100.0, p_9_bara, p_lp_bara,
        rho_drum_liquid_kgm3(p_9_bara), LV503_OP_DES_PCT / 100.0, P_MP_BARA, P_LP_BARA,
        rho_drum_liquid_kgm3(P_MP_BARA), characteristic=LV_329503.characteristic, fl=LV503_FL,
        pv_bara=p_9_bara, pv_des_bara=P_MP_BARA)


def lv_329504_kgs(opening_pct: float, p_lp_bara: float) -> float:
    """LV-329504's make-up from 329P001A/B into 322D001 [kg/s], on its vendor trim.

    Process utility
    ---------------
    LIC-329504's make-up (PFD 916): 100 C condensate from the pumps' discharge, held at 9.0 bar
    a (the pumps are not modelled), replacing what 322E002 raises and 959 blows down.
    """
    return valve_liquid_anchored(
        M_504_DES_KGS, _clamp_pct(opening_pct) / 100.0, P_916_BARA, p_lp_bara, RHO_916_KGM3,
        LV504_OP_DES_PCT / 100.0, P_916_BARA, P_LP_BARA, RHO_916_KGM3,
        characteristic=LV_329504.characteristic, fl=LV504_FL, pv_bara=PV_916_BARA)


__all__ = [
    "PV_916_BARA", "steam_valve_kgs", "pv_329204_kgs", "pv_329207a_kgs", "pv_329207b_kgs",
    "hv_329601_kgs", "pv_329207c_kgs", "hv_329602_kgs",
    "pv_329205a_kgs", "pv_329205b_kgs", "lv_329502_kgs",
    "lv_329503_kgs", "lv_329504_kgs",
]
