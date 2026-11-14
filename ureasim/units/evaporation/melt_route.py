"""LV-324501's node — where stage 2's melt goes: forward to granulation, back to 323D002, or both.

What this models
----------------
324F003's drain, PFD 402, leaves down its barometric leg to 335P001A / B. Through LV-324501A it goes
forward up the 335 melt header, unit 335's UF85 dosed into it (PFD 697 into 402G, making 609), and
HV-335602 at the header's end may drain a share of 609 to 335D004; through LV-324501B it returns raw
to 323D002, with no UF85. AC4 PC35.2 as configured opens both valves at once (`melt_split`; decided
2026-11-14, decision 224); V1's selector sends LIC-324501's demand one way only (`selector_drain`,
`melt_route`), the equivalence harness's side.

Equations (V1's ``route_lv324501``, the forward and recycle streams carried together)
-----------------------------------------------------------------------------------
    w_402      the raw melt's mass fractions, normalised
    m_uf       = r . m_402G                                  on LV-324501A's flow only
    w_609      = (m_402G w_402 + m_uf w_697) / (m_402G + m_uf)
    T_609      = (m_402G cp_402 T + m_uf cp_697 T_697) / (m_402G cp_402 + m_uf cp_697)
    m_drain    = s_hv (m_402G + m_uf),  m_forward = m_402G + m_uf - m_drain      s_hv HV-335602's share

Source: V1 ``backend/main.py`` ``route_lv324501`` (2436-2516) and the selector in its Stage 2
(9896-10021), moved out of `second_evaporator` unchanged so that module keeps one unit operation.
"""

from __future__ import annotations

from dataclasses import dataclass

from ureasim.control.valve import cv_fraction
from ureasim.core.numeric import clamp
from ureasim.core.packet import SOLUTION_SPECIES
from ureasim.data.unit_324 import (
    LV_324501A_OP_DES_PCT,
    LV_324501B_FULL_KGH,
    LV_324501_CHAR,
    LV_324501_SPAN_KGH,
    P2_DES_KGH,
    PIC_335201_RELIEF_BARG,
)
from ureasim.data.unit_335 import PFD_697_T_C, W_697
from ureasim.thermo.empirical import urea_soln_cp

__all__ = ["ROUTE_W_FLOOR", "ROUTE_NORMALISED_TOL", "ROUTE_FLOW_FLOOR_KGH", "MeltRoute",
           "melt_split", "melt_route", "selector_drain"]

#: V1's floors at the selector: the composition a stream must carry, the tolerance on its
#: normalisation, and its flows, before they count [-], [-], [kg/h] (``route_lv324501``).
ROUTE_W_FLOOR = 1.0e-15
ROUTE_NORMALISED_TOL = 1.0e-12
ROUTE_FLOW_FLOOR_KGH = 1.0e-15


@dataclass(frozen=True)
class MeltRoute:
    """Where stage 2's melt goes: the forward melt to the granulator and the recycle to 323D002
    [kg/h], each with its mass fractions and temperature [deg C]."""

    route: str
    forward_kgh: float
    forward_w: dict
    forward_t_c: float
    recycle_kgh: float
    recycle_w: dict
    recycle_t_c: float
    #: The UF85 joined to the forward melt [kg/h], PFD 697: none on the recycle.
    uf85_kgh: float = 0.0
    #: The raw melt LV-324501A sends forward [kg/h], 402G (FT-335401's), the ratio station's base.
    base_kgh: float = 0.0
    #: What HV-335602 drains of 609 to 335D004 [kg/h], at the forward stream's fractions and
    #: temperature, and its share of 609 [-]: a boundary outflow (decision 225).
    drain_kgh: float = 0.0
    hv_share: float = 0.0


def melt_split(base_kgh: float, recycle_kgh: float, w_402: dict, t_c: float,
               uf_ratio: float = 0.0, hv_share: float = 0.0,
               letter: str | None = None) -> MeltRoute:
    """LV-324501's node with both valves open (AC4 PC35.2; decision 224).

    Process utility
    ---------------
    LV-324501A sends ``base_kgh`` of the raw melt up the header and UF85 joins it, ``uf_ratio``
    kilograms per kilogram (unit 335's dosing, `units.finishing.uf85_dosing`); HV-335602 drains
    ``hv_share`` of the dosed stream to 335D004 and the rest reaches the granulator. LV-324501B
    returns ``recycle_kgh`` of the raw melt to 323D002 beside it. The route reads "A" with the
    recycle shut, "B" with nothing forward, "AB" with both, unless ``letter`` names V1's.

    Equations: the module docstring's.
    """
    m_base = max(float(base_kgh), 0.0)
    m_recycle = max(float(recycle_kgh), 0.0)
    total_w = sum(max(float(w_402.get(k, 0.0)), 0.0) for k in SOLUTION_SPECIES)
    if total_w <= ROUTE_W_FLOOR:
        raise ValueError("LV-324501 stream 402G composition is empty")
    if abs(total_w - 1.0) <= ROUTE_NORMALISED_TOL:
        base_w = {k: float(w_402.get(k, 0.0)) for k in SOLUTION_SPECIES}
    else:
        base_w = {k: max(float(w_402.get(k, 0.0)), 0.0) / total_w for k in SOLUTION_SPECIES}
    m_uf = max(float(uf_ratio), 0.0) * m_base
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
    share = clamp(float(hv_share), 0.0, 1.0)
    drain = share * m_selector
    if letter is None:
        forward_on, recycle_on = m_base > ROUTE_FLOW_FLOOR_KGH, m_recycle > ROUTE_FLOW_FLOOR_KGH
        letter = "AB" if forward_on and recycle_on else ("B" if recycle_on else "A")
    return MeltRoute(letter, m_selector - drain, dict(selector_w), selector_t, m_recycle,
                     dict(base_w), float(t_c), m_uf, m_base, drain, share)


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
    at T. `melt_split` with one of its two flows zero, which reproduces it.
    """
    m_base = max(float(m_402_kgh), 0.0)
    if recycle:
        return melt_split(0.0, m_base, w_402, t_c, letter="B")
    return melt_split(m_base, 0.0, w_402, t_c, uf_ratio, letter="A")


def selector_drain(level_op_pct: float, p_335201_barg: float, vendor_drain: bool,
                   m_402_avail_kgh: float) -> tuple[float, bool, float, float]:
    """V1's LV-324501A / B selector: the drain [kg/h], the recycle selected, and the two strokes [%].

    Process utility
    ---------------
    LIC-324501's stroke goes to one valve: LV-324501A, unless the 335 melt header stands above
    PIC-335201's relief setting, when it goes to LV-324501B. The equivalence harness's side of
    decision 224; the drain takes only the melt above 324F003's 1 kg floor (decision 11's class).

    Equations: LV-324501A anchored on the design drain at its design stroke on its vendor trim,
    LV-324501B on its full stroke (decision 150); with ``vendor_drain`` False V1's linear span law.
    """
    routed_op = clamp(level_op_pct, 0.0, 100.0)
    recycle = p_335201_barg > PIC_335201_RELIEF_BARG
    lv_a, lv_b = (0.0, routed_op) if recycle else (routed_op, 0.0)
    if not vendor_drain:
        m_402 = routed_op / 100.0 * LV_324501_SPAN_KGH
    elif recycle:   # LV-324501B, shut at design, on its full stroke
        m_402 = LV_324501B_FULL_KGH * cv_fraction(routed_op / 100.0, LV_324501_CHAR)
    else:           # LV-324501A, anchored on the design drain at its design stroke
        m_402 = P2_DES_KGH * (cv_fraction(routed_op / 100.0, LV_324501_CHAR)
                              / cv_fraction(LV_324501A_OP_DES_PCT / 100.0, LV_324501_CHAR))
    if m_402 > m_402_avail_kgh:
        m_402 = m_402_avail_kgh
    return m_402, recycle, lv_a, lv_b
