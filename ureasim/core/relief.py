"""Pressure relief — the spring-loaded safety valves on the plant's nodes.

What this models
----------------
The safety valve every pressure vessel carries: shut below its set pressure, lifting at it,
and passing what its certified orifice can pass until the pressure falls back by its blowdown,
where it reseats. A node whose relief is modelled stops at its set pressure the way the plant
does — the pressure cycles between set and reseat while the cause persists, and the vent rate is
the diagnostic signature — instead of running on to whatever its inventory makes of it. A PSV is
not a control valve and shares no code with one: it has no operator, no stroke and no set point
the DCS can move.

V1 ports the capacity law (``backend/hydraulics.py``, finding D-9 of the Heuristic Eradication
Report) and connects it to no node: V1 relieves nothing. The lift, the blowdown and the node's
vent are the decided divergence of 2026-09-30 (handoff B-47).

Source
------
The capacity law: V1 ``backend/hydraulics.py``, ported verbatim — API 520 Part I §5.6.3.1. The
set pressures: Uhde's technical specifications; the certified capacities, sizing fluids and
blowdowns: Sempell's orifice selections (VdTÜV type test, AD 2000-A2), and the blowdowns again
in Sempell's Series S manual (UD-RL-G00-DZ-0001-003, §3.9: gases close 10 % of the set pressure
below it, liquids 20 %) — all in `ureasim.data.relief_devices`.

The equations
-------------
Capacity, critical vapour flow (API 520 Part I)::

    W = Kd . Kb . Kc . A . P1 . sqrt( (k M) / (Z R T) . (2/(k+1))^((k+1)/(k-1)) )

with the orifice A back-solved from the vendor's certified capacity at its relieving pressure,
so Kd, Kb, Kc, k and the constant cancel and the certified point is reproduced exactly: only
P1, M, T and Z move. A valve rated on liquid has no certified gas capacity; where one sits on a
vapour node, A is its orifice's own flow area and Kd the series' full-lift gas coefficient,
taken as an assumption (decided 2026-10-01, handoff A-16). Liquid, anchored likewise::

    W = W_cert . sqrt( (P - P_b) / (P_rel - P_b) . rho / rho_c )

Lift, the spring valve's pop action::

    shut   -> lifted  at  P >= P_set
    lifted -> shut    at  P <= P_reseat = P_set - blowdown . (P_set - P_atm)

Units
-----
Areas m2, flows kg/h, pressures bar a, temperatures K, molar mass kg/kmol.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ureasim.core.units_of_measure import PA_PER_BAR, R_GAS_J

__all__ = [
    "psv_choked_ratio", "psv_api520_choked_kgh", "psv_area_from_rated_m2",
    "liquid_relief_kgh", "reseat_vent_kgh", "SafetyValve", "GasReliefValve",
]


def psv_choked_ratio(k: float) -> float:
    """Critical (choked) pressure ratio P_crit/P1 for an ideal gas of specific-heat ratio ``k``.

    Process utility
    ---------------
    Decides whether the relief is choked, and therefore whether the capacity equation below
    applies at all. For the vapours this plant relieves (k about 1.3) the ratio is near 0.55,
    so a PSV discharging to a tailpipe near atmospheric is choked for any set pressure above
    roughly 1.9 bar a — which is every relief device on the plant.

    Equation
    --------
        P_crit/P1 = (2/(k+1))^(k/(k-1))
    """
    return (2.0 / (k + 1.0)) ** (k / (k - 1.0))


def psv_api520_choked_kgh(area_m2: float, p1_bara: float, t1_k: float, mw: float,
                          k: float = 1.30, z: float = 1.0,
                          kd: float = 0.975, kb: float = 1.0, kc: float = 1.0) -> float:
    """API 520 Part I critical-flow vapour capacity of a relief orifice [kg/h].

    Process utility
    ---------------
    This is the rate at which the plant loses inventory once a relief lifts, and therefore how
    fast the protected vessel comes back down. It is LINEAR in P1, not in the over-pressure: a
    relief valve is a fixed orifice passing a choked jet, so it pops and flows choked, and does
    not ramp from zero at the set point — the ramp would teach a gentle relief where the plant
    gives a violent one.

    Parameters
    ----------
    area_m2
        Effective orifice area.
    p1_bara
        Relieving pressure, absolute — the ACTUAL upstream pressure, not the set pressure.
    t1_k
        Relieving temperature.
    mw
        Relieving-stream molar mass [kg/kmol].
    k
        Ratio of specific heats.
    z
        Compressibility at the relieving condition.
    kd
        Rated coefficient of discharge (0.975 for a certified vapour PSV, API 520 §5.6.3.1).
    kb
        Back-pressure correction (1.0 for a conventional valve on an atmospheric tailpipe).
    kc
        Combination correction (1.0 with no rupture disc upstream).
    """
    if area_m2 <= 0.0 or p1_bara <= 0.0 or t1_k <= 0.0 or mw <= 0.0:
        return 0.0
    # sqrt(kg.mol/(J.kmol)) — the isentropic choked mass-flux group.
    flux = math.sqrt(max((k * mw) / (z * R_GAS_J * t1_k)
                         * (2.0 / (k + 1.0)) ** ((k + 1.0) / (k - 1.0)), 0.0))
    # p1 in Pa, area in m2 -> kg/s; mw is kg/kmol so the group carries a 1e-3 to reach kg/mol.
    w_kgs = kd * kb * kc * area_m2 * (p1_bara * PA_PER_BAR) * flux * math.sqrt(1.0e-3)
    return w_kgs * 3600.0


def psv_area_from_rated_m2(w_rated_kgh: float, p1_rated_bara: float, t1_rated_k: float,
                           mw_rated: float, k: float = 1.30, z: float = 1.0,
                           kd: float = 0.975, kb: float = 1.0, kc: float = 1.0) -> float:
    """Effective orifice area reproducing a documented rated capacity [m2].

    Process utility
    ---------------
    Anchoring the area on the vendor's certified capacity makes the sizing basis exact and
    leaves only P1, M, T and Z live — the quantities that genuinely move during a relief event.
    The area is obtained by evaluating :func:`psv_api520_choked_kgh` for a unit area at the
    rated relieving condition and scaling, so the forward call and this inverse share one
    expression by construction.
    """
    unit = psv_api520_choked_kgh(1.0, p1_rated_bara, t1_rated_k, mw_rated, k, z, kd, kb, kc)
    return w_rated_kgh / unit if unit > 0.0 else 0.0


def liquid_relief_kgh(p_bara: float, p_back_bara: float, rho_kgm3: float, capacity_kgh: float,
                      p_rel_bara: float, rho_rel_kgm3: float) -> float:
    """What a fully lifted valve passes of a liquid [kg/h].

    Process utility
    ---------------
    A liquid-full vessel or line relieves liquid: the flow follows the square root of the head
    across the orifice and of the density, as through any orifice, anchored on the vendor's
    certified capacity at its relieving pressure.

    Equation
    --------
        W = W_cert . sqrt( (P - P_b) / (P_rel - P_b) . rho / rho_c )
    """
    dp = max(p_bara - p_back_bara, 0.0)
    return capacity_kgh * (dp / (p_rel_bara - p_back_bara) * rho_kgm3 / rho_rel_kgm3) ** 0.5


def reseat_vent_kgh(p_free_bara: float, p_reseat_bara: float, t_k: float, v_v_m3: float,
                    mw: float, dt: float) -> float:
    """The most a lifted valve can vent from a vapour space in one tick [kg/h].

    Process utility
    ---------------
    The valve reseats where the pressure falls to its reseat pressure, inside the tick if that
    is where it gets there. Venting more than the vapour above the reseat pressure would carry
    the node below it, which the valve, shut by then, does not do: this is the moles the
    ideal-gas vapour space holds above the reseat pressure, at the pressure the tick reaches
    before the relief, spread over the tick.

    Equation
    --------
        W_max = (P_free - P_reseat) . V_v / (R T) . M / dt          [the vessel_dpdt molar term]
    """
    if p_free_bara <= p_reseat_bara or v_v_m3 <= 0.0 or t_k <= 0.0:
        return 0.0
    kmol = (p_free_bara - p_reseat_bara) * 1.0e5 * v_v_m3 / (R_GAS_J * t_k) / 1000.0
    return kmol * mw * 3600.0 / dt


@dataclass
class SafetyValve:
    """A spring-loaded safety valve's lift: shut, or lifted until it reseats.

    Process utility
    ---------------
    The blowdown is what makes a lifted valve cycle rather than hover: it lifts at its set
    pressure and stays fully open until the node has fallen by the blowdown, so a persisting
    cause shows on PT as a saw-tooth between the two pressures. Sempell's valves open fully
    within 5 % above set on gas and 10 % on liquid; the lift here is taken full at set.
    """

    tag: str
    set_bara: float
    reseat_bara: float
    lifted: bool = False

    def step(self, p_bara: float) -> bool:
        """Read the node's pressure at the top of the tick; return whether the valve is lifted."""
        if not self.lifted and p_bara >= self.set_bara:
            self.lifted = True
        elif self.lifted and p_bara <= self.reseat_bara:
            self.lifted = False
        return self.lifted


@dataclass
class GasReliefValve:
    """A safety valve, or identical valves in parallel, on a node's vapour space.

    ``area_m2`` is each valve's orifice back-solved from its certified capacity
    (`psv_area_from_rated_m2`), ``k`` the exponent it was back-solved on; ``count`` valves set
    alike lift and reseat together. ``kd`` is the discharge coefficient the area is on: the law's
    0.975 for a back-solved orifice, where it cancels; for a liquid-rated valve on a vapour node,
    which has no certified gas capacity to back-solve, the orifice's own flow area and the gas
    coefficient taken for it (decided 2026-10-01, handoff A-16).
    """

    valve: SafetyValve
    area_m2: float
    k: float = 1.30
    count: int = 1
    kd: float = 0.975

    def vent_kgh(self, p_bara: float, p_free_bara: float, t_k: float, mw: float, v_v_m3: float,
                 dt: float) -> float:
        """What the valves vent this tick [kg/h].

        ``p_bara`` is the node's pressure at the top of the tick, which lifts or reseats the
        valve; ``p_free_bara`` the pressure the tick reaches without the relief; ``t_k``, ``mw``
        and ``v_v_m3`` the vapour space's temperature, molar mass and volume. The head-space
        vapour is the node's ideal gas, Z = 1, in critical flow: every valve this carries
        discharges to atmosphere or a low back pressure, its back-to-inlet ratio below 0.4 over
        its open band, under `psv_choked_ratio` of any exponent from 1.0 to 1.4.
        """
        if not self.valve.step(p_bara):
            return 0.0
        w = self.count * psv_api520_choked_kgh(self.area_m2, p_bara, t_k, mw, k=self.k,
                                               kd=self.kd)
        return min(w, reseat_vent_kgh(p_free_bara, self.valve.reseat_bara, t_k, v_v_m3, mw, dt))
