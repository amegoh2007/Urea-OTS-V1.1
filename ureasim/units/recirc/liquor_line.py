"""The liquor lines between the unit-323 stages, and the specific heat every liquor carries.

What this models
----------------
Each unit-323 stage drains into the next through a pipe with real volume:

    322E001 --LV-322501--> 323C003 --LV-323501--> 323F004 --LV-323505--> 323E010 / 323F010

The line is full of liquor, and liquor is incompressible: what leaves the stage upstream
reaches the next one on the same tick, and what reaches it is the liquor that left one line
residence ago — its temperature, composition and cp — at the live flow (decided 2026-09-30,
handoff B-21; V1 delays the flow with them, so its lines made and destroyed liquor on every flow
change). The RECEIVING stage owns its inlet line — it is the stage whose balances consume what
arrives — and the upstream stage publishes only the state its drain departed at.

Every liquor stream also carries its own specific heat. cp falls as the liquor concentrates,
from 3.03 kJ/(kg.K) in the stripper bottoms to 2.50 in the 80 % product, so one lumped
value would be wrong in both directions at once. Each stream's cp departs from the lumped
anchor by its own live-minus-design difference, which keeps every back-solved latent heat
and conductance exactly valid at design.

Source
------
V1 ``backend/main.py`` step_sim: the ``_cp`` lambda (AUDIT C10) and the four
``_transport_process(s, "..._TO_...")`` blocks with their settled-line reuse (323C003 feed,
323F004 inlet, 323F010 inlet, 323D002 inlet). The line geometry is `ureasim.data.process_routes`.
"""

from __future__ import annotations

from dataclasses import dataclass

from ureasim.core.packet import normalise_solution_mass_fraction
from ureasim.core.transport import property_packet, transport_process_properties
from ureasim.data.design_point import R323_CP_SOLN
from ureasim.data.process_routes import PROCESS_ROUTES
from ureasim.thermo.empirical import urea_soln_cp

#: Prefix of a process line's key in the packet store. Source: V1 `main.py`
#: ``_transport_process``, which stores every process line under ``"PROCESS_" + route``.
LINE_KEY_PREFIX = "PROCESS_"


def stream_cp(w_urea: float, t_c: float, cp_des: float) -> float:
    """A liquor stream's specific heat [kJ/(kg.K)], as a departure from the lumped anchor.

    Process utility
    ---------------
    The heat a unit-323 liquor brings into a stage, or holds, per degree. Molten urea is
    about 2.07 against water's 4.2, so the stripper bottoms, the column bottoms, the flash
    liquid and the product each carry their own; departing from each stream's own design
    value keeps every latent heat and conductance back-solved on the lumped 2.5 exactly
    valid at design.

    Equation
    --------
        cp = 2.5 + [ cp(w, T) - cp(w_des, T_des) ]

    Source: V1 `main.py` step_sim, the ``_cp`` lambda (AUDIT C10).
    """
    return R323_CP_SOLN + (urea_soln_cp(w_urea, t_c) - cp_des)


@dataclass(frozen=True)
class ArrivedLiquor:
    """What the inlet line delivers to a stage on one tick."""

    #: Flow [kg/h], temperature [deg C], composition [mass fractions] and cp [kJ/(kg.K)].
    m_kgh: float
    t_c: float
    w: dict
    cp_kj_kgk: float


def receive_liquor(line_state: dict, route: str, m_kgh: float, t_c: float, w: dict,
                   cp_des: float, dt: float) -> ArrivedLiquor:
    """Deliver one tick of an upstream stage's drain through the receiving stage's inlet line.

    Process utility
    ---------------
    Gives a stage its real inlet: a step in the column's drain temperature or ammonia reaches
    the flash tank only after the 323C003 -> 323F004 line has turned over, while a step in the
    drain RATE reaches it at once, as it does on a liquid-full pipe. Without the delay a
    composition upset would propagate through the train instantly and the dead time an
    operator sees on the plant would be missing; with the flow delayed too, a stopped line kept
    delivering for half an hour (handoff B-21).

    Arguments
    ---------
    m_kgh, t_c, w
        The drain as it departed: flow, and the upstream stage's temperature and composition
        BEFORE that stage advanced on this tick — the state of the liquor actually leaving.
    cp_des
        The upstream stage's design cp, the anchor of `stream_cp` for this liquor.

    The flow delivered is ``m_kgh``, the live departure (B-21). A settled line — the arrived
    property packet equal by value to the departed one — hands back the ORIGINAL scalars, so no
    renormalisation epsilon can move a pinned design seed. Otherwise the arrival is the
    packet's temperature and composition, with the cp re-evaluated on what arrived.

    Source: V1 `main.py` step_sim, the ``_cq_packet`` / ``_transport_process`` pair and the
    ``if _pkt_arr == _pkt_dep`` reuse, at each of the unit-323 inlets.
    """
    cp_dep = stream_cp(w.get("Urea", 0.0), t_c, cp_des)
    pkt_dep = property_packet(t_c, w, cp_dep)
    pkt_arr = transport_process_properties(line_state, LINE_KEY_PREFIX + route, pkt_dep,
                                           PROCESS_ROUTES[route], m_kgh, dt)
    if pkt_arr == pkt_dep:
        return ArrivedLiquor(m_kgh, t_c, w, cp_dep)
    w_arr = normalise_solution_mass_fraction(pkt_arr.mass_fraction, w)
    return ArrivedLiquor(m_kgh, pkt_arr.temperature_c, w_arr,
                         stream_cp(w_arr.get("Urea", 0.0), pkt_arr.temperature_c, cp_des))


__all__ = ["LINE_KEY_PREFIX", "stream_cp", "ArrivedLiquor", "receive_liquor"]
