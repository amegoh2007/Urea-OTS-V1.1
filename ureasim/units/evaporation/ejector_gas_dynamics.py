"""The 1-D compressible flow of a steam-jet ejector — the core of 324F002, 324F004 and 324F005.

What this models
----------------
The gas dynamics a steam-jet vacuum ejector rests on (Huang, Chang, Wang and Petrenko, "A 1-D
analysis of ejector performance", Int. J. Refrigeration 22 (1999) 354-364): the motive steam
expands isentropically through its choked nozzle; the entrained gas chokes in the annulus the
expanded jet leaves in the mixing section; a normal shock and a subsonic diffuser recover the
discharge pressure. Each stream is an ideal gas of constant specific-heat ratio, 1.33 for
low-pressure steam (Huang's assumption).

Equations
---------
    P*/P0       = (2 / (g + 1))^(g / (g - 1))                         choking ratio
    P0/P        = (1 + (g - 1)/2 M^2)^(g / (g - 1))                    isentropic
    A/A*        = (1/M) [ (2/(g + 1)) (1 + (g - 1)/2 M^2) ]^((g + 1) / (2 (g - 1)))
    m*          = P0 A sqrt(g / (R T0)) (2/(g + 1))^((g + 1) / (2 (g - 1)))    choked throat
    M2^2        = (1 + (g - 1)/2 M1^2) / (g M1^2 - (g - 1)/2)           normal shock
    p2/p1       = 1 + 2 g / (g + 1) (M1^2 - 1)
    P_crit      = P_s . p2/p1(M_y) . P0/P(M2)                           critical back pressure

with M_y the primary jet's Mach number expanded from the motive pressure to the suction
pressure. The critical back pressure is the loss-free one: the static pressure a subsonic
diffuser recovers behind a normal shock standing at the mixing section; above it the shock is
pushed into the mixing section and the entrained flow unchokes.

Source
------
V1 ``backend/ejector_huang.py`` (gap C40; not wired in V1): ``critical_pressure_ratio``,
``isentropic_p0_over_p``, ``isentropic_area_ratio``, ``choked_mass_flow``, ``normal_shock``,
``critical_backpressure`` (whose temperatures and areas V1 never reads, so they are not
arguments here) and ``_mach_from_p0_ratio``, ported verbatim. Built into the performance maps
of `units.evaporation.ejector_map` (handoff B-57, decided 2026-10-01).
"""

from __future__ import annotations

import math

#: The specific gas constant of water vapour [J/(kg K)] and the specific-heat ratio of
#: low-pressure steam (V1 ``R_STEAM``, ``GAMMA_STEAM``; Huang's ideal-gas assumption).
R_STEAM = 461.52
GAMMA_STEAM = 1.33


def critical_pressure_ratio(gamma: float) -> float:
    """P*/P0 at a choked throat.

    Process utility: below this ratio of suction to motive pressure the motive nozzle runs
    supersonic and the ejector can entrain at all; above it the motive steam cannot expand past
    sonic and the jet has no momentum to spare.
    """
    return (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))


def isentropic_p0_over_p(mach: float, gamma: float) -> float:
    """P0/P at Mach ``mach``, isentropic.

    Process utility: the pressure a subsonic diffuser recovers from a stream's velocity.
    """
    return (1.0 + 0.5 * (gamma - 1.0) * mach * mach) ** (gamma / (gamma - 1.0))


def isentropic_area_ratio(mach: float, gamma: float) -> float:
    """A/A* at Mach ``mach``, isentropic.

    Process utility: how far the motive jet spreads when it expands to the suction pressure —
    the share of the mixing section it takes from the gas it is to entrain.
    """
    g = gamma
    return (1.0 / mach) * ((2.0 / (g + 1.0)) * (1.0 + 0.5 * (g - 1.0) * mach * mach)) ** (
        (g + 1.0) / (2.0 * (g - 1.0)))


def choked_mass_flow(p0_pa: float, t0_k: float, area_m2: float, gamma: float = GAMMA_STEAM,
                     r_gas: float = R_STEAM) -> float:
    """Mass flow [kg/s] through a choked throat of ``area_m2`` from stagnation (P0, T0).

    Process utility: the motive steam a nozzle passes — proportional to its inlet pressure, so a
    sagging header starves the ejector of the momentum it compresses with — and the most gas the
    annulus beside the jet can carry.
    """
    g = gamma
    return (p0_pa * area_m2 * math.sqrt(g / (r_gas * t0_k))
            * (2.0 / (g + 1.0)) ** ((g + 1.0) / (2.0 * (g - 1.0))))


def normal_shock(mach_1: float, gamma: float) -> dict:
    """The normal-shock jump for an upstream Mach number above 1: downstream Mach ``M2``, and the
    static pressure, static temperature and stagnation pressure ratios ``p2_p1``, ``t2_t1``,
    ``p02_p01``.

    Process utility: where the mixed jet's velocity turns into the discharge pressure the next
    condenser stands at.
    """
    g = gamma
    m1sq = mach_1 * mach_1
    mach_2 = math.sqrt((1.0 + 0.5 * (g - 1.0) * m1sq) / (g * m1sq - 0.5 * (g - 1.0)))
    p2_p1 = 1.0 + 2.0 * g / (g + 1.0) * (m1sq - 1.0)
    t2_t1 = ((1.0 + 0.5 * (g - 1.0) * m1sq) * (2.0 * g * m1sq - (g - 1.0))
             / ((g + 1.0) ** 2 / 2.0 * m1sq))
    p02_p01 = (((g + 1.0) * m1sq / (2.0 + (g - 1.0) * m1sq)) ** (g / (g - 1.0))
               * ((g + 1.0) / (2.0 * g * m1sq - (g - 1.0))) ** (1.0 / (g - 1.0)))
    return {"M2": mach_2, "p2_p1": p2_p1, "t2_t1": t2_t1, "p02_p01": p02_p01}


def mach_from_p0_ratio(p0_over_p: float, gamma: float) -> float:
    """The supersonic Mach number of an isentropic expansion through P0/P.

    Process utility: how fast the motive jet leaves its nozzle for a given motive-to-suction
    pressure ratio — a deeper vacuum or a stronger motive drives it faster and wider.
    """
    g = gamma
    return math.sqrt(2.0 / (g - 1.0) * (p0_over_p ** ((g - 1.0) / g) - 1.0))


def critical_back_pressure(p_motive_pa: float, p_suction_pa: float,
                           gamma: float = GAMMA_STEAM) -> float:
    """The loss-free critical (breakdown) discharge pressure [Pa].

    Process utility
    ---------------
    The highest pressure the ejector can discharge into and still entrain at full capacity.
    Above it the shock moves into the mixing section, the entrained gas unchokes and the vacuum
    is lost — the break a motive-steam sag or a flooded after-condenser brings on.

    Equation in the module docstring: a normal shock at the primary jet's Mach number in the
    mixing section, the subsonic diffuser recovering its stagnation pressure. V1
    ``critical_backpressure``.
    """
    mach_mix = mach_from_p0_ratio(p_motive_pa / p_suction_pa, gamma)
    shock = normal_shock(mach_mix, gamma)
    return p_suction_pa * shock["p2_p1"] * isentropic_p0_over_p(shock["M2"], gamma)


__all__ = [
    "R_STEAM", "GAMMA_STEAM", "critical_pressure_ratio", "isentropic_p0_over_p",
    "isentropic_area_ratio", "choked_mass_flow", "normal_shock", "mach_from_p0_ratio",
    "critical_back_pressure",
]
