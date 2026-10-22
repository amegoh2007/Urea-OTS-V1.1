"""LV-324501's selector node — where stage 2's melt goes: forward to granulation or back to 323D002.

What this models
----------------
324F003's drain, PFD 402, leaves down its barometric leg to 335P001 and LIC-324501's demand goes
one way only: LV-324501A forward to the 335 melt header, with unit 335's UF85 dosed into it at the
selector, or — when the header backs up past PIC-335201's relief setting — LV-324501B back to
323D002, with no UF85.

Equations (V1's ``route_lv324501``)
-----------------------------------
    w_402      the raw melt's mass fractions, normalised
    m_uf       = r . m_402                                       route A only
    w_609      = (m_402 w_402 + m_uf w_697) / (m_402 + m_uf)
    T_609      = (m_402 cp_402 T + m_uf cp_697 T_697) / (m_402 cp_402 + m_uf cp_697)

Source: V1 ``backend/main.py`` ``route_lv324501`` (2436-2516), moved out of `second_evaporator`
unchanged so that module keeps one unit operation.
"""

from __future__ import annotations

from dataclasses import dataclass

from ureasim.core.packet import SOLUTION_SPECIES
from ureasim.data.unit_335 import PFD_697_T_C, W_697
from ureasim.thermo.empirical import urea_soln_cp

__all__ = ["ROUTE_W_FLOOR", "ROUTE_NORMALISED_TOL", "ROUTE_FLOW_FLOOR_KGH", "MeltRoute",
           "melt_route"]

#: V1's floors at the selector: the composition a stream must carry, the tolerance on its
#: normalisation, and its flows, before they count [-], [-], [kg/h] (``route_lv324501``).
ROUTE_W_FLOOR = 1.0e-15
ROUTE_NORMALISED_TOL = 1.0e-12
ROUTE_FLOW_FLOOR_KGH = 1.0e-15


@dataclass(frozen=True)
class MeltRoute:
    """What LV-324501's selector sends where: the forward melt to 335 and the recycle to 323D002
    [kg/h], each with its mass fractions and temperature [deg C]."""

    route: str
    forward_kgh: float
    forward_w: dict
    forward_t_c: float
    recycle_kgh: float
    recycle_w: dict
    recycle_t_c: float
    #: The UF85 joined to the forward melt [kg/h], PFD 697: none on route B.
    uf85_kgh: float = 0.0


def melt_route(m_402_kgh: float, w_402: dict, t_c: float, recycle: bool,
               uf_ratio: float = 0.0) -> MeltRoute:
    """LV-324501's selector node (V1 ``route_lv324501``).

    Process utility
    ---------------
    The melt goes one way only: forward through LV-324501A to granulation, or — when the 335
    melt header backs up past PIC-335201's relief setting — back through LV-324501B to 323D002.
    UF85 joins the forward melt at the selector, ``uf_ratio`` kilograms per kilogram of melt
    (unit 335's dosing, `units.finishing.uf85_dosing`; decided 2026-10-16, decision 123), and is
    interlocked off on route B. Stage 2 routes its own drain with none, V1's live call.

    Equations (V1's): the raw melt's fractions normalised; m_uf = r m on route A; the selector
    stream (m w + m_uf w_697) / (m + m_uf) at its sensible-heat-weighted temperature
    (m cp T + m_uf cp_697 40) / (m cp + m_uf cp_697) goes forward; on route B the raw melt returns
    at T.
    """
    m_base = max(float(m_402_kgh), 0.0)
    total_w = sum(max(float(w_402.get(k, 0.0)), 0.0) for k in SOLUTION_SPECIES)
    if total_w <= ROUTE_W_FLOOR:
        raise ValueError("LV-324501 stream 402G composition is empty")
    if abs(total_w - 1.0) <= ROUTE_NORMALISED_TOL:
        base_w = {k: float(w_402.get(k, 0.0)) for k in SOLUTION_SPECIES}
    else:
        base_w = {k: max(float(w_402.get(k, 0.0)), 0.0) / total_w for k in SOLUTION_SPECIES}
    m_uf = 0.0 if recycle else max(float(uf_ratio), 0.0) * m_base
    m_selector = m_base + m_uf
    if m_selector > ROUTE_FLOW_FLOOR_KGH:
        selector_w = {k: (m_base * base_w[k] + m_uf * W_697[k]) / m_selector
                      for k in SOLUTION_SPECIES}
    else:
        selector_w = dict(base_w)
    cp_base = urea_soln_cp(base_w["Urea"], t_c)
    cp_uf = urea_soln_cp(W_697["Urea"], PFD_697_T_C)
    heat_capacity_flow = m_base * cp_base + m_uf * cp_uf
    selector_t = ((m_base * cp_base * t_c + m_uf * cp_uf * PFD_697_T_C) / heat_capacity_flow
                  if heat_capacity_flow > ROUTE_FLOW_FLOOR_KGH else float(t_c))
    if recycle:
        return MeltRoute("B", 0.0, dict(base_w), float(t_c), m_base, dict(base_w), float(t_c))
    return MeltRoute("A", m_selector, dict(selector_w), selector_t, 0.0, dict(base_w), float(t_c),
                     m_uf)

