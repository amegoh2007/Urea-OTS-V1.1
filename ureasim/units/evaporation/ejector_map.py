"""324F002, 324F004 and 324F005 — the steam-jet ejectors' performance maps.

What this models
----------------
The three steam-jet ejectors that hold unit 324's vacuums: 324F002 pulls 324E002's vent (the
324F001 vacuum and, through 324E002's shell, 323F010's), 324F004 pulls 324E005's (the 324F003
vacuum) into 324E006, and 324F005 pulls 324E006's into 324E007. Each answers three pressures —
the suction it pulls, the motive steam at its nozzle, the discharge it compresses into — with
the gas it can entrain.

Decided 2026-10-01 (handoff B-57, the Typo Rule): V1 pulls each vacuum through a straight line
anchored on the PFD (72 kg/h x motive / 390 x P / 0.33; 584 kg/h x HIC-329606 / 50 x P / 0.131),
with no motive-pressure effect, no break and no stall. The vendor archive holds one duty point
per ejector and no curve (As-Built §XLVIII.2), so each map is synthesized from the 1-D model
(`units.evaporation.ejector_gas_dynamics`) on the ejector's own throats and vendor duty point
(`vendor_map`), then tabulated on suction and motive pressure and interpolated.

Decided 2026-10-01 (handoff B-61, option a): anchored on its vendor duty, each map out-pulls the
PFD's load at the PFD's vacuum (324F004 845 kg/h at 0.131 bar a against 584), so the design
vacuums were part-load points the bleed valves could not reach, where the plant's own trend holds
PT-324201 at the PFD's 0.34 bar a. The capacity is therefore anchored on the PFD's design flow
(`data.unit_324.EJECTOR_DESIGN_LOADS`) at the duty's motive pressure (`ejector_map`): K becomes
0.919 for 324F004 — the in-situ losses of an installed ejector against the loss-free model —
keeping the 1-D shape, the vendor's nozzles and throats and the vendor-anchored break. The vendor
ratings stand as margin.

Equations
---------
The motive nozzle's effective throat, the duty's motive flow choked at the duty's motive state
(324F004: 98.1 % of Körting's 24.7 mm orifice, 324F005: 98.2 % of its 14.5 mm), and the motive
steam it passes:

    A_t      = m_p,duty / m*(P_m,duty, T_m; 1 m2)
    m_p(P_m) = m*(P_m, T_m; A_t)

The critical mode (Huang): the jet, expanded to the suction pressure, fills A_py of the mixing
throat A_3; the gas chokes in the rest:

    A_py     = A_t . A/A*( M(P_m / P_s) )
    C        = K . m*_gas(P_s, T_s, M_s; A_3 - A_py)      while A_3 > A_py and P_m/P_s > P0/P*
             = 0                                          otherwise (no entrainment)

K puts the vendor's map on its duty point, C(duty) = m_s,duty. 324F002 has no throat in the
archive: its mixing throat A_3 is the one that puts the loss-free model (K = 1) on its duty point.
The decided map scales K so the table, read as the plant reads it, gives the design load:

    K_des = K_duty . m_s,des / C_duty,table(P_s,des, P_m,duty)

The motive pressure at the nozzle answers the motive flow on the choked nozzle's law, anchored on
the PFD's design motive (handoff B-64, decided 2026-10-02): P_m = P_m,duty . m_p / m_p,des.

The break. The critical back pressure, the 1-D model's loss-free normal-shock recovery scaled on
the duty point's discharge pressure — the ejector taken as rated to discharge there, critical at
its own duty (an assumption, handoff B-61):

    P_c      = P_d,duty . P_c,1D(P_s, P_m) / P_c,1D(P_s,duty, P_m,duty)

Above it the gas unchokes: the static pressure where it meets the jet rises from its sonic r* P_s
in proportion to the discharge pressure, and the gas passes a subsonic nozzle's flux at that
ratio,

    r    = r* . P_d / P_c,    F = sqrt[ (r^(2/g) - r^((g+1)/g)) / (r*^(2/g) - r*^((g+1)/g)) ]
    pull = C . F               F = 1 up to P_c, 0 from P_c / r* (1.85 P_c)

F is continuous with its slope at P_c, so the break is smooth for a pressure loop to iterate on.

The table. C and P_c on suction pressures 0.010 to 1.200 bar a by 0.005 and motive pressures 0
to 6.00 bar a by 0.05 (the steam chests' 6 bar g design caps the motive), interpolated
bilinearly; outside it the pressures are held at its edges. Every duty point is a node.

Declared: one specific-heat ratio, 1.33, for the motive steam and the gas alike (Huang's; V1's
``GAMMA_STEAM``); the gas's molar mass and temperature held at the duty's (the map does not
follow the vent's composition: Körting's generic molar-mass correction is not applied); the
motive temperature held at the duty's.

Source
------
The duties and throats: `data.unit_324.EJECTOR_DUTIES` (Uhde's vacuum-unit table, Körting's
operating data); the design loads, `EJECTOR_DESIGN_LOADS` (the PFD). The model: V1
``backend/ejector_huang.py``, Huang et al. (1999). The break's closure and the anchoring of P_c
are this module's (As-Built §XLIX.4).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from functools import lru_cache

from ureasim.core.units_of_measure import ABSOLUTE_ZERO_C, PA_PER_BAR, R_GAS_J_KMOL
from ureasim.data.unit_324 import EJECTOR_DESIGN_LOADS, EJECTOR_DUTIES, EjectorDuty
from ureasim.units.evaporation.ejector_gas_dynamics import (
    GAMMA_STEAM,
    R_STEAM,
    choked_mass_flow,
    critical_back_pressure,
    critical_pressure_ratio,
    isentropic_area_ratio,
    mach_from_p0_ratio,
)

#: The table's suction nodes: i / SUCTION_NODES_PER_BAR bar a for i in SUCTION_NODE_RANGE, so
#: 0.010 to 1.200 by 0.005 and every duty's suction pressure is a node.
SUCTION_NODES_PER_BAR = 200
SUCTION_NODE_RANGE = (2, 240)

#: The table's motive nodes: j / MOTIVE_NODES_PER_BAR bar a, 0 to 6.00 by 0.05.
MOTIVE_NODES_PER_BAR = 20
MOTIVE_NODE_RANGE = (0, 120)

#: The choking ratio the break is measured from [-].
R_STAR = critical_pressure_ratio(GAMMA_STEAM)


def _flux(r: float) -> float:
    """sqrt(r^(2/g) - r^((g+1)/g)): an isentropic nozzle's flux at a static-to-stagnation ratio
    r, up to constants; largest at r*."""
    g = GAMMA_STEAM
    return math.sqrt(max(r ** (2.0 / g) - r ** ((g + 1.0) / g), 0.0))


@dataclass(frozen=True)
class EjectorMap:
    """One ejector's synthesized map: its duty, effective motive throat [m2], mixing throat
    [m2], the capacity anchor K [-] and the critical back pressure's scale [-]."""

    duty: EjectorDuty
    throat_m2: float
    mixing_m2: float
    k_capacity: float
    pc_scale: float


def motive_kgh(m: EjectorMap, p_motive_bara: float) -> float:
    """The motive steam the nozzle passes at a motive pressure [kg/h].

    Process utility: what the ejector draws from the LP header, and what it adds to the gas it
    discharges into the next condenser — proportional to the motive pressure, the choked
    nozzle's law (Uhde's 1061 and 366 kg/h at 4.1 bar a, by construction).
    """
    if p_motive_bara <= 0.0:
        return 0.0
    return choked_mass_flow(p_motive_bara * PA_PER_BAR, m.duty.t_motive_c + ABSOLUTE_ZERO_C,
                            m.throat_m2) * 3600.0


def _primary_area_m2(m: EjectorMap, p_suction_bara: float, p_motive_bara: float) -> float | None:
    """The jet's area at the mixing throat [m2], or None while it cannot run supersonic."""
    ratio = p_motive_bara / p_suction_bara
    if ratio <= 1.0 / R_STAR:
        return None
    return m.throat_m2 * isentropic_area_ratio(mach_from_p0_ratio(ratio, GAMMA_STEAM),
                                               GAMMA_STEAM)


def _gas_capacity_1d(duty: EjectorDuty, p_suction_bara: float, area_m2: float) -> float:
    """The gas the annulus passes choked [kg/h], loss-free."""
    r_gas = R_GAS_J_KMOL / duty.mw_suction
    return choked_mass_flow(p_suction_bara * PA_PER_BAR, duty.t_suction_c + ABSOLUTE_ZERO_C,
                            area_m2, GAMMA_STEAM, r_gas) * 3600.0


def critical_capacity_kgh(m: EjectorMap, p_suction_bara: float, p_motive_bara: float) -> float:
    """The map's critical-mode suction capacity [kg/h] — the points the table is made of.

    Process utility: the most gas the ejector can entrain at a suction and a motive pressure
    while it discharges below its critical back pressure. It rises with the suction pressure
    (a denser gas), and falls slowly with more motive (a wider jet), so the ejector pulls a
    vessel down until its own capacity meets the load; zero once the jet fills the mixing throat
    — the deepest vacuum the ejector can reach.
    """
    if p_suction_bara <= 0.0 or p_motive_bara <= 0.0:
        return 0.0
    a_py = _primary_area_m2(m, p_suction_bara, p_motive_bara)
    if a_py is None or a_py >= m.mixing_m2:
        return 0.0
    return m.k_capacity * _gas_capacity_1d(m.duty, p_suction_bara, m.mixing_m2 - a_py)


def critical_back_pressure_bara(m: EjectorMap, p_suction_bara: float,
                                p_motive_bara: float) -> float:
    """The map's critical back pressure [bar a], zero where the ejector entrains nothing.

    Process utility: the discharge pressure past which the ejector breaks — what a motive sag,
    or a downstream condenser losing its water, pushes it into.
    """
    if critical_capacity_kgh(m, p_suction_bara, p_motive_bara) <= 0.0:
        return 0.0
    return m.pc_scale * critical_back_pressure(p_motive_bara * PA_PER_BAR,
                                               p_suction_bara * PA_PER_BAR) / PA_PER_BAR


def unchoked_fraction(p_discharge_bara: float, p_crit_bara: float) -> float:
    """F, the share of its critical capacity the ejector keeps at a discharge pressure [-].

    Process utility: the break — 1 up to the critical back pressure, then falling smoothly to 0
    at P_c / r*, where the gas no longer passes the jet at all. Equation in the module docstring.
    """
    if p_discharge_bara <= p_crit_bara:
        return 1.0
    if p_crit_bara <= 0.0:
        return 0.0
    r = R_STAR * p_discharge_bara / p_crit_bara
    if r >= 1.0:
        return 0.0
    return _flux(r) / _flux(R_STAR)


@lru_cache(maxsize=None)
def vendor_map(tag: str) -> EjectorMap:
    """The ejector's map on its vendor duty point (equations in the module docstring).

    Process utility: the one place each ejector's vendor rating becomes a model — its effective
    nozzle from the motive it passes, its mixing throat from the drawing (or, for 324F002, from
    its duty), and the two anchors that put the 1-D model on the vendor's point. The plant runs
    the design-anchored `ejector_map`; this one is the vendor's margin, and handoff B-61's
    measurement.
    """
    duty = EJECTOR_DUTIES[tag]
    t_m = duty.t_motive_c + ABSOLUTE_ZERO_C
    throat = duty.motive_kgh / 3600.0 / choked_mass_flow(duty.p_motive_bara * PA_PER_BAR, t_m,
                                                        1.0, GAMMA_STEAM, R_STEAM)
    probe = EjectorMap(duty, throat, 0.0, 1.0, 1.0)
    a_py = _primary_area_m2(probe, duty.p_suction_bara, duty.p_motive_bara)
    if duty.diffuser_mm is None:
        mixing = a_py + duty.suction_kgh / _gas_capacity_1d(duty, duty.p_suction_bara, 1.0)
        k = 1.0
    else:
        mixing = math.pi / 4.0 * (duty.diffuser_mm / 1000.0) ** 2
        k = duty.suction_kgh / _gas_capacity_1d(duty, duty.p_suction_bara, mixing - a_py)
    pc_1d = critical_back_pressure(duty.p_motive_bara * PA_PER_BAR,
                                   duty.p_suction_bara * PA_PER_BAR) / PA_PER_BAR
    return EjectorMap(duty, throat, mixing, k, duty.p_discharge_bara / pc_1d)


@lru_cache(maxsize=None)
def ejector_map(tag: str) -> EjectorMap:
    """The ejector's map as the plant runs it: the vendor's, its capacity anchored on the PFD's
    design load (handoff B-61, decided 2026-10-01).

    Process utility
    ---------------
    Holds each vacuum at its design point with the bleed at its design stroke — the PFD's 72, 584
    and 41 kg/h pulled at 0.33, 0.131 and 0.3 bar a on the duty's motive — while the curve keeps
    the 1-D model's shape on the vendor's throats and breaks where the vendor's rating puts it.

    Equation
    --------
        K_des = K_duty . m_s,des / C_duty,table(P_s,des, P_m,duty)

    read off the vendor map's table, so the decided table gives the design load at the design
    point to rounding.
    """
    m = vendor_map(tag)
    load = EJECTOR_DESIGN_LOADS[tag]
    read = _read(lambda p_s, p_m: critical_capacity_kgh(m, p_s, p_m), load.p_suction_bara,
                 m.duty.p_motive_bara)
    return replace(m, k_capacity=m.k_capacity * load.suction_kgh / read)


def nozzle_pressure_bara(tag: str, motive_kgh: float) -> float:
    """The motive pressure at the ejector's nozzle [bar a] that passes a motive flow.

    Process utility: turns what the motive valve delivers (HIC-329605, HIC-329606) into the
    pressure the map reads. A choked nozzle passes a flow proportional to its pressure, anchored
    so the design motive is the duty's 4.1 bar a:

        P_m = P_m,duty . m_p / m_p,des

    The design motive is the PFD's for all three ejectors (handoff B-64, decided 2026-10-02,
    option a): PFD 924's 390 kg/h for 324F002, where Körting's 650 sized the nozzle; PFD 927's
    1220 and 929's 180 for 324F004 and 324F005, where Uhde's 1061 and 366 sized theirs. The
    nozzles keep their vendor rating (`motive_kgh`), and the PFD's flow puts the nozzle at the
    duty's 4.1 bar a — the flow the train condenses.
    """
    m = vendor_map(tag)
    return m.duty.p_motive_bara * max(motive_kgh, 0.0) / EJECTOR_DESIGN_LOADS[tag].motive_kgh


def _node(i: int, per_bar: int) -> float:
    """A table node's pressure [bar a], as the table writes it."""
    return i / per_bar


def _read(f, p_suction_bara: float, p_motive_bara: float) -> float:
    """f read as the table reads it: f at the four nodes round the point, blended bilinearly."""
    i, fs = _cell(p_suction_bara, SUCTION_NODES_PER_BAR, SUCTION_NODE_RANGE)
    j, fm = _cell(p_motive_bara, MOTIVE_NODES_PER_BAR, MOTIVE_NODE_RANGE)
    i += SUCTION_NODE_RANGE[0]
    j += MOTIVE_NODE_RANGE[0]
    s0, s1 = _node(i, SUCTION_NODES_PER_BAR), _node(i + 1, SUCTION_NODES_PER_BAR)
    m0, m1 = _node(j, MOTIVE_NODES_PER_BAR), _node(j + 1, MOTIVE_NODES_PER_BAR)
    return _blend(f(s0, m0), f(s0, m1), f(s1, m0), f(s1, m1), fs, fm)


def _blend(t00: float, t01: float, t10: float, t11: float, fs: float, fm: float) -> float:
    """Bilinear blend of a cell's four corners, suction first."""
    lo = t00 + fm * (t01 - t00)
    hi = t10 + fm * (t11 - t10)
    return lo + fs * (hi - lo)


@lru_cache(maxsize=None)
def _table(tag: str) -> tuple:
    """The map tabulated: (capacity rows, critical back pressure rows), each row one suction
    node over the motive nodes."""
    m = ejector_map(tag)
    caps, pcs = [], []
    for i in range(SUCTION_NODE_RANGE[0], SUCTION_NODE_RANGE[1] + 1):
        p_s = _node(i, SUCTION_NODES_PER_BAR)
        cap_row, pc_row = [], []
        for j in range(MOTIVE_NODE_RANGE[0], MOTIVE_NODE_RANGE[1] + 1):
            p_m = _node(j, MOTIVE_NODES_PER_BAR)
            cap_row.append(critical_capacity_kgh(m, p_s, p_m))
            pc_row.append(critical_back_pressure_bara(m, p_s, p_m))
        caps.append(cap_row)
        pcs.append(pc_row)
    return caps, pcs


def _cell(p: float, per_bar: int, node_range: tuple) -> tuple[int, float]:
    """The table cell a pressure falls in, held at the table's edges: (lower index, fraction)."""
    lo, hi = node_range
    x = min(max(p * per_bar, float(lo)), float(hi))
    k = min(int(math.floor(x)), hi - 1)
    return k - lo, x - k


def interpolated(tag: str, p_suction_bara: float, p_motive_bara: float) -> tuple[float, float]:
    """(critical capacity [kg/h], critical back pressure [bar a]) off the table, bilinear.

    Process utility: the decided interpolation (handoff B-57) — the vendor-anchored map read
    at the live suction and motive pressures, cheap enough to sit inside a vacuum's pressure
    loop.
    """
    caps, pcs = _table(tag)
    i, fs = _cell(p_suction_bara, SUCTION_NODES_PER_BAR, SUCTION_NODE_RANGE)
    j, fm = _cell(p_motive_bara, MOTIVE_NODES_PER_BAR, MOTIVE_NODE_RANGE)

    def bilinear(t):
        return _blend(t[i][j], t[i][j + 1], t[i + 1][j], t[i + 1][j + 1], fs, fm)

    return bilinear(caps), bilinear(pcs)


def suction_capacity_kgh(tag: str, p_suction_bara: float, p_motive_bara: float,
                         p_discharge_bara: float) -> float:
    """What the ejector pulls from its suction [kg/h] — the vacuum balance's outflow.

    Process utility
    ---------------
    The pull that holds a vacuum: up with the suction pressure, so a vessel settles where the
    ejector's capacity meets its condenser's vent; zero with no motive; cut back, smoothly, once
    the discharge pressure passes the critical back pressure, which a motive sag lowers — the
    stall V1's straight line cannot show.

    Equation: pull = C(P_s, P_m) . F(P_d / P_c(P_s, P_m)), C and P_c off the table.
    """
    cap, p_crit = interpolated(tag, p_suction_bara, p_motive_bara)
    return cap * unchoked_fraction(p_discharge_bara, p_crit)


__all__ = [
    "SUCTION_NODES_PER_BAR", "SUCTION_NODE_RANGE", "MOTIVE_NODES_PER_BAR", "MOTIVE_NODE_RANGE",
    "R_STAR", "EjectorMap", "motive_kgh", "critical_capacity_kgh", "critical_back_pressure_bara",
    "unchoked_fraction", "vendor_map", "ejector_map", "nozzle_pressure_bara", "interpolated",
    "suction_capacity_kgh",
]
