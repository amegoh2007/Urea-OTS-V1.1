"""A unit 324 vacuum condenser as a flowsheet node — its live inlet and its closed books.

What this models
----------------
324E002, 324E005, 324E006 and 324E007 as the evaporation train sees them: what arrives (the PFD
inlet row scaled on the live vapour, plus the live false air the vacuum controllers admit), and
what leaves (the anchored saturated vent of `vacuum_condenser`, and the condensate as everything
else, so the node closes its mass exactly).

Equations
---------
The inlet, on the row's air-free mass:

    r     = (m_in - m_air) / (m_in,des - m_air,des)
    n_k   = n_k,des . r + y_air,k (m_air - m_air,des) / M_air + y_air,k (m_air,des / M_air)(1 - r)

so at design (r = 1, m_air = m_air,des) every term but the first is a literal zero. A part of the
inlet whose composition is known and is not the row's (LV-323505's blow-through gas in 324E002's)
replaces the same mass of the row's condensable and carried species. The node:

    vent       = min(vent_PFD . vent_model / vent_model,des, m_in)    while the condenser duty > 0
               = m_in                                                 otherwise
    condensate = m_in - vent

the cold end solved at the live shell pressure, the vapour charged at its design inlet temperature
(handoff B-31, a Phase 7 calibration deferral).

Source
------
V1 ``backend/main.py`` ``vacuum_inlet_kmolh`` (3933-3955) and ``vacuum_condenser_node``
(3958-3984), reports A-13, B-9, B-13. Ported verbatim; V1's dictionary of lagged cold ends is the
caller's to keep (``t_v_prev`` in, ``t_vent_c`` out).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ureasim.data.unit_324 import VAC_AIR_FRAC, VAC_AIR_MW
from ureasim.thermo.saturated_vent import CARRIED, CONDENSABLE, MW, SPECIES
from ureasim.units.evaporation.vacuum_condenser import design_specs, solve, vent_kgh


def inlet_kmolh(tag: str, inlet_kgh: float, air_kgh: float, air_des_kgh: float,
                sub: tuple | None = None) -> dict:
    """The species arriving at a first-stage condenser [kmol/h].

    Process utility
    ---------------
    What the condenser has to condense and what its vent has to carry: more evaporation brings
    more of the row's vapour, more false air more inert gas — the load that sets how much vapour
    the vent holds and how hard the ejector behind it must pull.

    Arguments
    ---------
    tag
        The condenser.
    inlet_kgh, air_kgh, air_des_kgh
        The live inlet [kg/h], the live false air in it [kg/h], and that false air at design.
    sub
        (kg/h, mass fractions) of a part of the inlet whose composition is known and is not the
        row's; the inert gas comes from the false air alone either way.
    """
    spec = design_specs()[tag]
    r = (inlet_kgh - air_kgh) / (spec.inlet_kgh - air_des_kgh)
    d_air = (air_kgh - air_des_kgh) / VAC_AIR_MW
    a_des = air_des_kgh / VAC_AIR_MW
    n = {k: spec.n_in_des[k] * r
            + VAC_AIR_FRAC.get(k, 0.0) * d_air + VAC_AIR_FRAC.get(k, 0.0) * a_des * (1.0 - r)
         for k in SPECIES}
    if sub is not None and sub[0] > 0.0:
        m_sub, y_sub = sub
        cond = CONDENSABLE + CARRIED
        f = m_sub / sum(spec.n_in_des[k] * MW[k] for k in cond)
        for k in cond:
            n[k] = max(n[k] + m_sub * y_sub.get(k, 0.0) / MW[k] - spec.n_in_des[k] * f, 0.0)
    return n


@dataclass(frozen=True)
class CondenserNode:
    """One condenser on one tick: its books [kg/h], its duty [kW], its water and its cold end."""

    tag: str
    inlet_kgh: float
    condensate_kgh: float
    vent_kgh: float
    q_kw: float
    lmtd_k: float
    ua_kw_k: float
    cw_flow_kgh: float
    cw_in_c: float
    cw_out_c: float
    hot_in_c: float
    hot_out_c: float
    #: The cold end [deg C]: the vent's temperature, and the next solve's bracket centre.
    t_vent_c: float
    p_bara: float
    vent_kmolh: dict = field(default_factory=dict)
    #: inlet - condensate - vent [kg/h]: zero by construction.
    mass_residual_kgh: float = 0.0
    #: The cold end's Q_bal - UA . LMTD [kW], the solve's own residual.
    energy_residual_kw: float = 0.0


def condenser_node(tag: str, inlet_kgh: float, n_in_kmolh: dict, p_bara: float,
                   cw_flow_kgh: float | None = None, cw_in_c: float | None = None,
                   t_v_prev: float | None = None) -> CondenserNode:
    """One condenser at its live shell pressure (reports A-13, B-9, B-13).

    Process utility
    ---------------
    What the vacuum train hands on: the vent to the ejector, the condensate to 328D003, the duty
    to the cooling water. A condenser that condenses nothing (no water, or a shell too hot) vents
    its whole inlet; the vent never exceeds what arrives and is never negative
    (`vacuum_condenser.vent_moles`, handoff B-87), so the node closes its mass and condenses no
    more than it receives.

    Arguments
    ---------
    tag, inlet_kgh, n_in_kmolh, p_bara
        The condenser, its live inlet [kg/h] and species [kmol/h] (`inlet_kmolh`), its shell
        pressure [bar a].
    cw_flow_kgh, cw_in_c
        Its cooling water [kg/h, deg C]; None for the design's.
    t_v_prev
        The cold end it settled at last time [deg C], the back-pressure bracket's centre; None
        for the design outlet.
    """
    spec = design_specs()[tag]
    cw_flow = spec.cw_flow_kgh if cw_flow_kgh is None else max(cw_flow_kgh, 0.0)
    cw_in = spec.cw_in_c if cw_in_c is None else cw_in_c
    inlet = max(inlet_kgh, 0.0)
    res = solve(spec, p_bara, n_in_kmolh, spec.t_in_des, cw_flow, cw_in, t_v_prev=t_v_prev)
    vent = min(vent_kgh(spec, res), inlet) if res.q_kw > 0.0 else inlet
    condensate = inlet - vent
    return CondenserNode(
        tag=tag, inlet_kgh=inlet, condensate_kgh=condensate, vent_kgh=vent, q_kw=res.q_kw,
        lmtd_k=res.lmtd_k, ua_kw_k=spec.ua_kw_k, cw_flow_kgh=cw_flow, cw_in_c=cw_in,
        cw_out_c=res.cw_out_c, hot_in_c=spec.t_in_des, hot_out_c=res.t_vent_c,
        t_vent_c=res.t_vent_c, p_bara=p_bara, vent_kmolh=res.vent_kmolh,
        mass_residual_kgh=inlet - condensate - vent, energy_residual_kw=res.q_kw - res.q_ua_kw)


__all__ = ["inlet_kmolh", "CondenserNode", "condenser_node"]
