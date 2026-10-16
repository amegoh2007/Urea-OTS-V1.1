"""Unit 324's vacuum train — 324E002, 324E005, 324E006, 324E007 in series with their ejectors.

What this models
----------------
The two evaporation stages' overheads and what condenses out of them. Stage 1's overhead (PFD
705) and the pre-evaporator's (790, what HV-323605 passes) condense in 324E002 under stage 1's
vacuum; 324F002 pulls the vent (706) and discharges it with its motive steam (924) to 323C005 as
708. Stage 2's overhead (709) condenses in 324E005 under stage 2's vacuum; 324F004 pulls the vent
(712) into 324E006 with its motive steam (927) as 714; 324F005 pulls 324E006's vent (715) into
324E007 with its motive steam (929) as 717; 324E007's vent (722) goes to atmosphere. The four
condensates (719, 720, 721, 759) go to 328D003's compartment I.

    705 + 790 --703--> 324E002 --706--> 324F002 (+924) --708--> 323C005
    709 --> 324E005 --712--> 324F004 (+927) --714--> 324E006 --715--> 324F005 (+929) --717-->
            324E007 --722--> atmosphere

The ejectors here are mixing nodes: what pulls each vacuum is its stage's pressure balance, on the
ejector's map (`ejector_map`, handoff B-61). The train hands the stages back their condensers'
cold ends (the tears their pressure balances read) and publishes what reaches 323C005, 328D003
and the atmosphere.

Equations
---------
Each first-stage inlet is the PFD row moved by the live vapour and false air (V1's departures):

    m_705 = 14799 + (m_v1 - m_v1,des) + (m_fa1 - 21)        m_790 = 12040 + (m_f010 - 12013.3)
    m_709 = 3342 + (m_v2 - m_v2,des) + (m_fa2 - 21)         m_703 = 26840 + (m_705 - 14799)
                                                                    + (m_790 - 12040)

its species `condenser_node.inlet_kmolh`'s. The second and third condensers take the upstream
condenser's LIVE vent species and the ejector's motive steam, as departures from their design
inlet rows, so the design reproduces the PFD and a change at 324E005 reaches 324E006 and 324E007
by composition, not only by mass:

    n_k,714 = n_k,714,des + (n_k,712 - n_k,712,des) + [k = H2O] (m_927 - 1220) / M_H2O
    n_k,717 = n_k,717,des + (n_k,715 - n_k,715,des) + [k = H2O] (m_929 - 180) / M_H2O

Each condenser is `condenser_node` at its shell pressure: 324E002 and 324E005 at their stages'
live vacuums, 324E006 at the PFD's 0.3 bar a and 324E007 at 1.0, V1's constants (`vacuum_train`).

324E006's shell is a vacuum node (`VacuumTrain`; handoff B-66, decided 2026-10-02, the Typo
Rule): 324F004 discharges into it, 324E006 condenses what it can, and 324F005 pulls the rest on
its map into 324E007 — the stages' own balance, on the shell's nameplate volume:

    dP_6/dt = (R T_6 / V_6) (n_vent(P_6) - n_pull(P_6)),    V_6 = 0.542 m3

n_vent 324E006's anchored saturated vent at the trial pressure, its cold end held, at most what
arrives (714); n_pull 324F005's map at its live motive against 324E007's 1.0 bar a; stepped backward
(`core.node.backward_euler_pressure`) between the map's lowest suction node and 324E007's shell,
where 324F005's body passes what arrives. A lost 324E006 drives the shell to 324E007's pressure,
324F004 breaks against it, and stage 2's vacuum is lost — where V1's 0.3 bar a hides it.

The cold ends the vacuum balances read — 324E002's and 324E005's for the stages, 324E006's for its
shell — are lagged on their condensers' tube-side water residence (handoff B-65, decided
2026-10-02):

    T_v,lag' = T_v,lag + dt / (tau + dt) (T_v - T_v,lag),    tau = V_tubes / Q_cw,des

V_tubes the datasheet's tubes, n pi d_i^2 L / 4, Q_cw the PFD's cooling water at its mean
temperature's density: 324E002 11.54 s, 324E005 7.67 s, 324E006 3.12 s. V1 hands the stages the
last solve's cold end one tick late, and the held melt's boil-off (B-62), which answers the vacuum
by thousands of kg/h per mbar, pulses on that tear through a trip.

The motive steam (decision 23's class, §5 rule 7; handoff B-73, decided 2026-10-02, the Typo
Rule). HV-329605 and HV-329606 run their Flowserve trims, anchored at the strokes where they pass
the PFD's design motive (69.06 and 80.16 %), between the LP header and the nozzles they feed. A
choked nozzle passes a flow in proportion to its pressure (`ejector_map.nozzle_pressure_bara`), so
the valve's outlet is where its flow and the nozzle's agree:

    m = m_des . Phi(h, P_LP, P_n) / Phi(h_des, P_LP,des, P_n,des),    P_n = P_n,des . m / m_des
    Phi = f(h) P1 Y sqrt(x M / T1),  x = min(dP / P1, F_gamma xT),  T1 = T_sat(P_LP)

solved for m by bisection on [0, m_des P_LP / P_n,des]; P_LP,des the header's 4.0 bar g (B-69),
P_n,des the duties' 4.1 bar a, xT Flowserve's on the normal case (0.7828, 0.7028), f the modified
equal-percentage characteristic. At the design stroke on the design header the answer is the
design motive to the bit. One valve feeds 324F004 and 324F005, their nozzles at one pressure, split
as the PFD splits it (handoff B-64, decided 2026-10-02: the train condenses the PFD's 1220 and
180 kg/h). V1 runs both valves linear from 50 %, blind to the header; a header that falls now
starves the ejectors with it.

708's temperature (handoff B-97, decided 2026-10-16). V1's train carries 708's mass only and V1's
323C005 charges it at the PFD's 121 C. The port publishes 324F002's discharge on the ejector's
energy balance — 706 at 324E002's cold end and 924 at the LP header's saturated steam enthalpy
(HV-329605 throttles it isenthalpically), mixed adiabatically at 323C005's 1.0 bar a
(`thermo.steam_gas_mixing`) — as its departure from the same mix at design:

    T_708 = 121 + (T_mix(n_706, T_706, m_924, h_g(P_LP)) - T_mix,des)

T_mix,des 125.62 C on the design solve's 706, the design 390 kg/h and the header's design 4.0 bar
g. At the design the answer is 121 C to the bit; a closed HIC-329605 takes it to 63.0 C, 706's
water condensing at the mixing point.

Source
------
V1 ``backend/main.py`` ``vacuum_train_324`` (3987-4048), executed at run time through
``core/vacuum.py`` ``VacuumTrain324.solve``, and its call (10036-10063): the motive lines, the
shells, the tears. Ported verbatim. ``VacuumTrain324.solve`` passes neither ``tv_prev`` nor the
cooling water (its ``cw_factors`` is empty), so every condenser solves on its design cooling water
with its back-pressure bracket centred on its design cold end — as here. 324E006's shell volume:
Uhde's name plate, UD-AU-324-DZ-0005-008 (`data.unit_324_train.E006_SHELL_VOL_M3`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache

from ureasim.control.valve import compressible_shape
from ureasim.core.node import backward_euler_pressure, vessel_dpdt
from ureasim.core.signal import first_order_lag
from ureasim.core.units_of_measure import ABSOLUTE_ZERO_C
from ureasim.data.unit_324 import (
    E006_P_DES_BARA,
    E007_P_DES_BARA,
    F001_FA_DES_KGH,
    F001_P_DES_BARA,
    F002_MOTIVE_DES_KGH,
    F003_FA_DES_KGH,
    F003_P_DES_BARA,
    F004_MOTIVE_DES_KGH,
    F005_MOTIVE_DES_KGH,
    V1_DES_KGH,
    V2_DES_KGH,
    VACUUM_CONDENSERS,
)
from ureasim.data.unit_323 import MEVAP_DES_KGH
from ureasim.data.unit_323c005 import C005_P_BARA, C005_T708_C
from ureasim.data.unit_329 import P_LP_BARA, STEAM_GAMMA, STEAM_MW
from ureasim.data.unit_324_train import (
    E006_SHELL_VOL_M3,
    HV_329605_OP_DES_PCT,
    HV_329605_XT,
    HV_329606_OP_DES_PCT,
    HV_329606_XT,
    MOTIVE_P1_DES_BARA,
    MOTIVE_P2_DES_BARA,
    PFD_703_KGH,
    PFD_705_KGH,
    PFD_709_KGH,
    PFD_790_KGH,
)
from ureasim.thermo import iapws
from ureasim.thermo.saturated_vent import INERT, MW, SPECIES
from ureasim.thermo.steam_gas_mixing import mix_temperature_c
from ureasim.units.evaporation.condenser_node import CondenserNode, condenser_node, inlet_kmolh
from ureasim.units.evaporation.ejector_map import (
    SUCTION_NODE_RANGE,
    SUCTION_NODES_PER_BAR,
    nozzle_pressure_bara,
    suction_capacity_kgh,
)
from ureasim.units.evaporation.vacuum_condenser import (
    condensate_back_pressure,
    design_specs,
    vent_kgh_at,
    vent_moles,
)

#: The motive valves' trim, Flowserve's plug code ...GG (Pos. 66, 67).
MOTIVE_TRIM = "mod_equal_pct"

#: The condensers whose cold ends a vacuum balance reads, lagged on their tube-side water
#: (handoff B-65): 324E002's and 324E005's for the two stages, 324E006's for its own shell.
LAGGED_COLD_ENDS = ("324E002", "324E005", "324E006")

#: 324E006's shell between its bracket's ends [bar a]: the deepest suction 324F005's map is
#: tabulated on, and 324E007's shell, past which 324F005's body passes what arrives.
E006_P_MIN_BARA = SUCTION_NODE_RANGE[0] / SUCTION_NODES_PER_BAR
E006_P_MAX_BARA = E007_P_DES_BARA


@dataclass(frozen=True)
class MotiveSteam:
    """What the two motive-steam hand valves pass to the three ejectors [kg/h]: PFD 924
    (HV-329605 to 324F002), 927 and 929 (HV-329606 to 324F004 and 324F005)."""

    m_924_kgh: float
    m_927_kgh: float
    m_929_kgh: float


def motive_ratio(hic_pct: float, op_des_pct: float, xt: float, p_lp_bara: float) -> float:
    """What a motive valve passes against the nozzles it feeds, over its design motive [-].

    Process utility
    ---------------
    The coupling handoff B-73 adds: the valve's flow sets the nozzle's pressure and the nozzle's
    pressure throttles the valve, both against the LP header's live pressure. Opening the valve
    raises the nozzle's pressure, so the flow grows less than the trim's curve alone says; a
    header that falls takes the motive down with it. Equations in the module docstring; the
    bisection runs until its bracket stops shrinking, and the design stroke on the design header
    returns 1.0 before it starts.
    """
    h = hic_pct / 100.0
    if h <= 0.0 or p_lp_bara <= 0.0:
        return 0.0
    ref = compressible_shape(op_des_pct / 100.0, MOTIVE_P1_DES_BARA, MOTIVE_P2_DES_BARA,
                             iapws.tsat_c(MOTIVE_P1_DES_BARA) + ABSOLUTE_ZERO_C, STEAM_MW,
                             STEAM_GAMMA, 1.0, MOTIVE_TRIM, xt)
    t1_k = iapws.tsat_c(p_lp_bara) + ABSOLUTE_ZERO_C

    def excess(r: float) -> float:
        # The valve's flow at the nozzle pressure r carries, less r [-]: falls through zero once.
        return compressible_shape(h, p_lp_bara, MOTIVE_P2_DES_BARA * r, t1_k, STEAM_MW,
                                  STEAM_GAMMA, 1.0, MOTIVE_TRIM, xt) / ref - r

    if excess(1.0) == 0.0:
        return 1.0
    lo, hi = 0.0, p_lp_bara / MOTIVE_P2_DES_BARA
    while True:
        mid = 0.5 * (lo + hi)
        if mid == lo or mid == hi:
            return mid
        if excess(mid) > 0.0:
            lo = mid
        else:
            hi = mid


def motive_steam(hic_329605_pct: float, hic_329606_pct: float,
                 p_lp_bara: float = P_LP_BARA) -> MotiveSteam:
    """The motive steam HIC-329605 and HIC-329606 admit off the LP header [kg/h].

    Process utility
    ---------------
    The operator's two levers on the vacuums: more motive steam drives the ejectors harder and
    pulls stage 1 (HIC-329605) or stage 2 (HIC-329606) deeper, and every kilogram of it is a
    kilogram the next condenser has to condense. ``p_lp_bara`` is the LP header's pressure the
    valves see (handoff B-73); its default is the header's design. Equations in the module
    docstring.
    """
    r_605 = motive_ratio(hic_329605_pct, HV_329605_OP_DES_PCT, HV_329605_XT, p_lp_bara)
    r_606 = motive_ratio(hic_329606_pct, HV_329606_OP_DES_PCT, HV_329606_XT, p_lp_bara)
    return MotiveSteam(F002_MOTIVE_DES_KGH * r_605, F004_MOTIVE_DES_KGH * r_606,
                       F005_MOTIVE_DES_KGH * r_606)


@lru_cache(maxsize=None)
def _vent_des_kmolh(tag: str) -> dict:
    """A condenser's model vent at its design state [kmol/h], the departure's reference (V1's
    ``up_des``, re-evaluated on every call there; a pure function of the design)."""
    spec = design_specs()[tag]
    return vent_moles(spec, spec.p_des, spec.t_v_solved_des, spec.n_in_des)


def cascade_inlet_kmolh(tag: str, upstream: CondenserNode, upstream_tag: str,
                        motive_kgh: float, motive_des_kgh: float) -> dict:
    """The species arriving at 324E006 or 324E007 [kmol/h]: its design row moved by what the
    upstream condenser vents and by the ejector's motive steam.

    Process utility
    ---------------
    Carries a change at the stage-2 condenser down the train by composition: more ammonia left
    in 324E005's vent is more ammonia 324E006 must condense and 324E007 must stop.
    """
    n_des = design_specs()[tag].n_in_des
    up_des = _vent_des_kmolh(upstream_tag)
    d_mot = (motive_kgh - motive_des_kgh) / MW["H2O"]
    return {k: n_des[k] + (upstream.vent_kmolh[k] - up_des[k]) + (d_mot if k == "H2O" else 0.0)
            for k in SPECIES}


@dataclass(frozen=True)
class VacuumTrainResult:
    """The train on one tick."""

    #: Every stream the train writes, by PFD number [kg/h]: 703, 705, 706, 708, 709, 712, 714,
    #: 715, 717, 719, 720, 721, 722, 759, 790, and the motive steams 924, 927, 929.
    streams_kgh: dict
    #: The four condensers' books, by tag.
    nodes: dict
    #: 703 - 705 - 790 [kg/h]: the PFD's own rounding, 26840 - 14799 - 12040 = 1 kg/h, at every
    #: state (V1 publishes it).
    mixing_residual_703_kgh: float
    #: The condensates to 328D003's compartment I [kg/h]: 719 + 720 + 721 + 759.
    condensate_kgh: float
    #: 324E002's vent inerts [kmol/h], what 708 carries to 323C005's vent.
    inert_706_kmolh: dict = field(default_factory=dict)
    #: 324E006's shell [bar a], what 324F004 discharges into (PI-324257): V1's 0.3 bar a, or the
    #: live node's (handoff B-66).
    p_324e006_bara: float = E006_P_DES_BARA
    #: 708's temperature into 323C005 [deg C], 324F002's discharge as its departure from the
    #: design mix (handoff B-97); V1 has none and charges the PFD's 121 C.
    t_708_c: float = C005_T708_C


def _node(tag: str, inlet: float, n_in: dict, p: float, cw_flow_kgh: dict,
          cw_in_c: dict) -> CondenserNode:
    """One condenser on the tick's cooling water (a tag absent takes its design)."""
    return condenser_node(tag, inlet, n_in, p, cw_flow_kgh.get(tag), cw_in_c.get(tag))


def _first_condensers(m_790_kgh: float, vapour1_kgh: float, vapour2_kgh: float,
                      false_air1_kgh: float, false_air2_kgh: float, motive: MotiveSteam,
                      p_324e002_bara: float, p_324e005_bara: float, sub_703: tuple | None,
                      cw_flow_kgh: dict,
                      cw_in_c: dict) -> tuple[dict, CondenserNode, CondenserNode]:
    """The rows into the train and the two stages' condensers, 324E002 and 324E005: (streams,
    324E002, 324E005). Equations in the module docstring."""
    s = {
        "705": PFD_705_KGH + (vapour1_kgh - V1_DES_KGH) + (false_air1_kgh - F001_FA_DES_KGH),
        "790": PFD_790_KGH + (m_790_kgh - MEVAP_DES_KGH),
        "709": PFD_709_KGH + (vapour2_kgh - V2_DES_KGH) + (false_air2_kgh - F003_FA_DES_KGH),
        "924": motive.m_924_kgh, "927": motive.m_927_kgh, "929": motive.m_929_kgh,
    }
    s["703"] = PFD_703_KGH + (s["705"] - PFD_705_KGH) + (s["790"] - PFD_790_KGH)

    # ----- stage 1: 324E002 and 324F002 -------------------------------------------------
    e002 = _node("324E002", s["703"],
                 inlet_kmolh("324E002", s["703"], false_air1_kgh, F001_FA_DES_KGH, sub_703),
                 p_324e002_bara, cw_flow_kgh, cw_in_c)
    s["719"], s["706"] = e002.condensate_kgh, e002.vent_kgh
    s["708"] = s["706"] + s["924"]

    # ----- stage 2: 324E005 and 324F004 -------------------------------------------------
    e005 = _node("324E005", s["709"],
                 inlet_kmolh("324E005", s["709"], false_air2_kgh, F003_FA_DES_KGH),
                 p_324e005_bara, cw_flow_kgh, cw_in_c)
    s["720"], s["712"] = e005.condensate_kgh, e005.vent_kgh
    s["714"] = s["712"] + s["927"]
    return s, e002, e005


def _mix_708_c(e002: CondenserNode, m_924_kgh: float, p_lp_bara: float) -> float:
    """324F002's adiabatic mix of 706 and 924 at 323C005's pressure [deg C]."""
    return mix_temperature_c(e002.vent_kmolh, e002.t_vent_c, m_924_kgh,
                             iapws.h_vapour_sat_kjkg(iapws.tsat_c(p_lp_bara)), C005_P_BARA)


@lru_cache(maxsize=None)
def _mix_708_des_c() -> float:
    """The mix on the design: 324E002 solved on the design rows, 390 kg/h off the design header
    (V1's ``up_des``'s kind, a pure function of the design)."""
    e002 = condenser_node("324E002", PFD_703_KGH,
                          inlet_kmolh("324E002", PFD_703_KGH, F001_FA_DES_KGH, F001_FA_DES_KGH,
                                      None),
                          F001_P_DES_BARA, None, None)
    return _mix_708_c(e002, F002_MOTIVE_DES_KGH, P_LP_BARA)


def discharge_708_c(e002: CondenserNode, m_924_kgh: float, p_lp_bara: float = P_LP_BARA) -> float:
    """PFD 708's temperature into 323C005 [deg C] (handoff B-97, decided 2026-10-16).

    Process utility
    ---------------
    What 324F002 hands the atmospheric absorber besides mass: its discharge carries the motive
    steam's enthalpy, so less motive steam, a colder 324E002 or a lower LP header sends 708
    cooler, and 323C005's liquor follows. Anchored on the PFD's 121 C by the departure from the
    design mix (equation in the module docstring); nothing arriving is the design's 121 C, whose
    flow then carries no heat.
    """
    if m_924_kgh + e002.vent_kgh <= 0.0:
        return C005_T708_C
    return C005_T708_C + (_mix_708_c(e002, m_924_kgh, p_lp_bara) - _mix_708_des_c())


def _back_condensers(s: dict, e002: CondenserNode, e005: CondenserNode, p_324e006_bara: float,
                     cw_flow_kgh: dict, cw_in_c: dict, t_708_c: float) -> VacuumTrainResult:
    """324E006, 324F005 and 324E007 behind stage 2's condenser, and the train's books."""
    e006 = _node("324E006", s["714"],
                 cascade_inlet_kmolh("324E006", e005, "324E005", s["927"], F004_MOTIVE_DES_KGH),
                 p_324e006_bara, cw_flow_kgh, cw_in_c)
    s["721"], s["715"] = e006.condensate_kgh, e006.vent_kgh
    s["717"] = s["715"] + s["929"]
    e007 = _node("324E007", s["717"],
                 cascade_inlet_kmolh("324E007", e006, "324E006", s["929"], F005_MOTIVE_DES_KGH),
                 E007_P_DES_BARA, cw_flow_kgh, cw_in_c)
    s["759"], s["722"] = e007.condensate_kgh, e007.vent_kgh

    return VacuumTrainResult(
        streams_kgh=s,
        nodes={"324E002": e002, "324E005": e005, "324E006": e006, "324E007": e007},
        mixing_residual_703_kgh=s["703"] - s["705"] - s["790"],
        condensate_kgh=s["719"] + s["720"] + s["721"] + s["759"],
        inert_706_kmolh={k: e002.vent_kmolh[k] for k in INERT},
        p_324e006_bara=p_324e006_bara, t_708_c=t_708_c)


def vacuum_train(m_790_kgh: float, vapour1_kgh: float, vapour2_kgh: float,
                 false_air1_kgh: float, false_air2_kgh: float, motive: MotiveSteam,
                 p_324e002_bara: float = F001_P_DES_BARA,
                 p_324e005_bara: float = F003_P_DES_BARA,
                 sub_703: tuple | None = None, cw_flow_kgh: dict | None = None,
                 cw_in_c: dict | None = None,
                 p_324e006_bara: float = E006_P_DES_BARA,
                 p_lp_bara: float = P_LP_BARA) -> VacuumTrainResult:
    """The four condensers and three ejector mixing nodes on one tick (reports A-13, B-9, B-13).

    Process utility
    ---------------
    Where the evaporators' water goes: condensed to 328D003, or carried with the inerts to
    323C005 and the atmosphere. The cold ends of 324E002 and 324E005 are the tears the two
    stages' pressure balances read on the next tick. The plant runs it through `VacuumTrain`,
    which keeps 324E006's shell and the lagged cold ends; called alone it is V1's train.

    Arguments
    ---------
    m_790_kgh
        What HV-323605 passed from 323F010 (`PreEvaporatorResult.pull_kgh`).
    vapour1_kgh, vapour2_kgh
        The two stages' overheads: the feed's boil-off and the held melt's (handoff B-62), as each
        stage books them (`FirstEvaporatorResult.m_vap_kgh + .m_boil_kgh`; the same on
        `SecondEvaporatorResult`).
    false_air1_kgh, false_air2_kgh
        PV-324202's and PV-324203's false air (PFD 784, 783).
    motive
        The motive steam (`motive_steam`).
    p_324e002_bara, p_324e005_bara
        The two stages' vacuums, the first two condensers' shells.
    sub_703
        LV-323505's blow-through share of 790 (`PreEvaporatorResult.blowthrough_share`), or None.
    cw_flow_kgh, cw_in_c
        Cooling water by condenser tag [kg/h, deg C]; a tag absent takes its design.
    p_324e006_bara
        324E006's shell [bar a]: V1's 0.3 by default, the live node's in `VacuumTrain`.
    p_lp_bara
        The LP header the motive steam is drawn from [bar a], 924's enthalpy (B-97).
    """
    cw_flow_kgh = cw_flow_kgh or {}
    cw_in_c = cw_in_c or {}
    s, e002, e005 = _first_condensers(m_790_kgh, vapour1_kgh, vapour2_kgh, false_air1_kgh,
                                      false_air2_kgh, motive, p_324e002_bara, p_324e005_bara,
                                      sub_703, cw_flow_kgh, cw_in_c)
    return _back_condensers(s, e002, e005, p_324e006_bara, cw_flow_kgh, cw_in_c,
                            discharge_708_c(e002, s["924"], p_lp_bara))


# ======================================================================================
# The train as the plant runs it: 324E006's shell live, the cold ends lagged
# ======================================================================================

@lru_cache(maxsize=None)
def cold_end_tau_s(tag: str) -> float:
    """The residence of a condenser's cooling water in its tubes [s] (handoff B-65).

    Process utility
    ---------------
    How fast a condenser's cold end can follow its load: the water in the tubes must be replaced
    before the cold end settles where the new load puts it, so a burst of vapour warms the cold
    end over seconds, not within a tick. Equation in the module docstring: the datasheet's tubes,
    the PFD's cooling water, the water's density at its mean temperature (IAPWS). The channels'
    water exchanges no heat and is left out (the name plate's tube-side volume includes it).
    """
    r = VACUUM_CONDENSERS[tag]
    d_i_m = (r.tube_od_mm - 2.0 * r.tube_wall_mm) / 1000.0
    v_tubes_m3 = r.tube_count * math.pi / 4.0 * d_i_m * d_i_m * r.tube_length_mm / 1000.0
    rho_kgm3 = iapws.rho_liquid_sat_kgm3(0.5 * (r.cw_in_c + r.cw_out_c))
    return v_tubes_m3 * rho_kgm3 / (r.cw_flow_kgh / 3600.0)


class VacuumTrain:
    """Unit 324's vacuum train with its state: 324E006's shell (handoff B-66) and the three cold
    ends the vacuum balances read, lagged on their tube-side water (handoff B-65).

    Process utility
    ---------------
    What the scheduler steps after the two stages. The stages read `cold_end_c` ("324E002" for
    stage 1, "324E005" for stage 2) and 324F004 discharges against `p_324e006_bara` — each as the
    train left it on the tick before. Seeded on the design: 0.3 bar a and the design solves'
    cold ends, so the design holds.
    """

    def __init__(self) -> None:
        specs = design_specs()
        #: The lagged cold ends [deg C], by condenser tag.
        self.lag_state: dict = {tag: specs[tag].t_v_solved_des for tag in LAGGED_COLD_ENDS}
        #: 324E006's shell [bar a].
        self.p_324e006_bara: float = E006_P_DES_BARA

    def cold_end_c(self, tag: str) -> float:
        """The cold end a vacuum balance reads [deg C]: the condenser's, lagged."""
        return self.lag_state[tag]

    def _shell_pressure(self, s: dict, e005: CondenserNode, dt: float) -> float:
        """324E006's shell one tick on [bar a]: 324F004's discharge in, 324E006 condensing it at
        its lagged cold end, 324F005 pulling the rest (equation in the module docstring)."""
        spec = design_specs()["324E006"]
        n_714 = cascade_inlet_kmolh("324E006", e005, "324E005", s["927"], F004_MOTIVE_DES_KGH)
        t_v = self.cold_end_c("324E006")
        p_old = self.p_324e006_bara
        bp = condensate_back_pressure(n_714, t_v)
        vent0 = vent_moles(spec, p_old, t_v, n_714, bp)
        n_vent0 = sum(vent0.values())
        mw = sum(vent0[k] * MW[k] for k in SPECIES) / n_vent0 if n_vent0 > 0.0 else MW["H2O"]
        p_motive = nozzle_pressure_bara("324F005", s["929"])
        t_k = t_v + ABSOLUTE_ZERO_C

        def dpdt(p: float) -> float:
            # What the shell cannot condense at a trial pressure, at most what arrives, against
            # what 324F005 entrains from it into 324E007.
            vent = min(vent_kgh_at(spec, p, t_v, n_714, bp), s["714"])
            pull = suction_capacity_kgh("324F005", p, p_motive, E007_P_DES_BARA)
            return vessel_dpdt(p, t_k, E006_SHELL_VOL_M3, mw, vent / mw, pull / mw)

        return backward_euler_pressure(p_old, dt, dpdt, E006_P_MIN_BARA, E006_P_MAX_BARA)

    def step(self, m_790_kgh: float, vapour1_kgh: float, vapour2_kgh: float,
             false_air1_kgh: float, false_air2_kgh: float, motive: MotiveSteam,
             p_324e002_bara: float, p_324e005_bara: float, dt: float,
             sub_703: tuple | None = None, cw_flow_kgh: dict | None = None,
             cw_in_c: dict | None = None, p_lp_bara: float = P_LP_BARA) -> VacuumTrainResult:
        """Advance the train one tick: arguments as `vacuum_train`'s.

        The order: the rows and the stages' condensers at the stages' solved vacuums; 324E006's
        shell stepped on what 324F004 now discharges; 324E006 and 324E007 solved at the new
        shell; the three cold ends lagged toward the solves'.
        """
        cw_flow_kgh = cw_flow_kgh or {}
        cw_in_c = cw_in_c or {}
        s, e002, e005 = _first_condensers(m_790_kgh, vapour1_kgh, vapour2_kgh, false_air1_kgh,
                                          false_air2_kgh, motive, p_324e002_bara,
                                          p_324e005_bara, sub_703, cw_flow_kgh, cw_in_c)
        self.p_324e006_bara = self._shell_pressure(s, e005, dt)
        result = _back_condensers(s, e002, e005, self.p_324e006_bara, cw_flow_kgh, cw_in_c,
                                  discharge_708_c(e002, s["924"], p_lp_bara))
        for tag in LAGGED_COLD_ENDS:
            first_order_lag(self.lag_state, tag, result.nodes[tag].t_vent_c, cold_end_tau_s(tag),
                            dt)
        return result


__all__ = [
    "MOTIVE_TRIM", "LAGGED_COLD_ENDS", "E006_P_MIN_BARA", "E006_P_MAX_BARA", "MotiveSteam",
    "motive_ratio", "motive_steam", "cascade_inlet_kmolh", "discharge_708_c", "VacuumTrainResult",
    "vacuum_train", "cold_end_tau_s",
    "VacuumTrain",
]
