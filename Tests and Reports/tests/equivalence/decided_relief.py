"""The relief law as decided (handoff B-47, 2026-09-30), transcribed for the V1 harnesses.

V1 ports the API 520 capacity law and connects it to no node, so a harness that puts the port's
relief in V1's lines writes the rest out on V1's side: the pop action with its blowdown, V1's own
``psv_api520_choked_kgh`` on an orifice back-solved by V1's own ``psv_area_from_rated_m2`` from the
certified capacity, and at most the vapour above the reseat pressure in a tick — the port's
`ureasim.core.relief`, line for line. Each harness passes its valve's numbers, written from Uhde's
and Sempell's sheets. A valve rated on liquid alone (handoff A-16, decided 2026-10-01) is built with
`Valve.orifice`: its orifice's own area at the assumed gas coefficient, on V1's own capacity law.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Valve", "vent"]


@dataclass(frozen=True)
class Valve:
    """A valve's sheet numbers: set and reseat [bar a], the relieving pressure [bar a], the
    certified capacity per valve [kg/h] on its sizing gas [K, kg/kmol, -, -], and how many
    alike; or, for a liquid-rated valve, its orifice's flow area [m2] and the gas coefficient
    taken for it."""

    set_bara: float
    reseat_bara: float
    p_rel_bara: float
    capacity_kgh: float
    t_rel_k: float
    mw_rel: float
    z_rel: float
    k: float = 1.30
    count: int = 1
    area_m2: float | None = None
    kd: float = 0.975

    @classmethod
    def orifice(cls, set_bara: float, reseat_bara: float, area_m2: float, kd: float,
                k: float = 1.30) -> "Valve":
        """A valve rated on liquid alone, on a vapour node: no certified gas point to back-solve
        (A-16)."""
        return cls(set_bara, reseat_bara, 0.0, 0.0, 0.0, 0.0, 1.0, k=k, area_m2=area_m2, kd=kd)


def vent(g, sv: Valve, p_bara: float, p_free_bara: float, t_k: float, mw: float, v_v_m3: float,
         dt: float, lifted: bool) -> tuple[float, bool]:
    """The port's `GasReliefValve.vent_kgh`, transcribed: the vent this tick [kg/h] and the lift.
    ``g`` is V1's namespace, for V1's own ``hydraulics``."""
    if not lifted and p_bara >= sv.set_bara:
        lifted = True
    elif lifted and p_bara <= sv.reseat_bara:
        lifted = False
    if not lifted:
        return 0.0, lifted
    hy = g["hydraulics"]
    r = hy.R_GAS
    if sv.area_m2 is None:
        area = hy.psv_area_from_rated_m2(sv.capacity_kgh, sv.p_rel_bara, sv.t_rel_k, sv.mw_rel,
                                         k=sv.k, z=sv.z_rel)
    else:
        area = sv.area_m2
    w = sv.count * hy.psv_api520_choked_kgh(area, p_bara, t_k, mw, k=sv.k, kd=sv.kd)
    cap = 0.0
    if p_free_bara > sv.reseat_bara and v_v_m3 > 0.0 and t_k > 0.0:
        cap = ((p_free_bara - sv.reseat_bara) * 1.0e5 * v_v_m3 / (r * t_k) / 1000.0
               * mw * 3600.0 / dt)
    return min(w, cap), lifted
