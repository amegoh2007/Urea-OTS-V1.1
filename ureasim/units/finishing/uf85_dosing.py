"""Unit 335's UF85 dosing — FFIC-335406 over FIC-335405 and the metering pumps 335P002A / B.

What this models
----------------
The anti-caking additive UF85 dosed into the urea melt ahead of the granulator, in ratio to the
melt LV-324501A sends forward. FFIC-335406, the ratio master, reads the achieved ratio — the UF85
FT-335405 measures over the melt's flow (FQI-335401) — and asks FIC-335405, the metering pumps'
flow loop, for the ratio times the melt. LV-324501B selected, or no melt, is the hard permissive:
the pumps stop whatever the controllers say, the master freezes and FT-335405 decays to zero.

    melt 402G --LV-324501A--> selector --> 609 to 335
                                 ^
    335D007 --335P002A/B (FIC-335405) <-- ratio x melt -- FFIC-335406 <-- FT-335405 / FQI-335401

Equations (V1's ``step_uf85_cascade``):

    ratio_PV = 1000 . PV_405 / m_402                     (0 on route B or with no melt)
    SP_405   = max(OP_406 . m_402, 0) / 1000            [t/h], with FIC-335405 in CAS
    m_uf     = 694 . OP_405 / 50                          [kg/h], FT-335405 lagged 5 s

the master tracking the achieved ratio while its slave is out of cascade (`control.ratio`). The
delivered UF85 joins the forward melt at LV-324501's selector, ``uf_ratio = m_uf / m_402``
(`melt_route.melt_route`): 609 = 402G + 697, at the sensible-heat-weighted temperature.

On the plant FFIC-335406 is the ratio station its faceplate in the plant DCS shows (decided
2026-10-28, handoff B-116 (a), `project.md` decision 160): no controller, FIC-335405's set point
the ratio set point times the melt,

    SP_405   = clamp(RAT . m_402 / 1000, OUT L, OUT H)      [t/h], RAT within RAT L to RAT H

its ratio set point tracking the achieved ratio while FIC-335405 is out of cascade
(`control.ratio.RatioStation`). V1's PI master on the ratio is ``ffic_335406(station=False)``,
which the equivalence harness keeps.

Where this unit departs from V1 — decided 2026-10-16 (`project.md` decision 123)
-----------------------------------------------------------------------------------
V1 ports the whole cascade and its selector but never runs them: its ``step_sim`` calls
``step_uf85_cascade(s, m_402g, True, dt)``, the recycle permissive forced, and
``route_lv324501(..., uf_ratio=0.0)`` ("UF85 deferred (granulation off)"), so FIC-335405 sits at 0 %
and the product is the raw melt. The port runs the cascade on the live route, LV-324501B its only
interlock, and the selector on what the pumps deliver. FIC-335405 is seeded at the ratio on the
plant's design drain, 617.1 kg/h at 44.46 % (`data.unit_335.UF85_DES_KGH`), where V1 seeds the
granulation case's 694 kg/h at 50 %, so the design holds; ``Uf85Dosing(m_uf_kgh=694.0)`` is V1's
seed.

Source
------
V1 ``backend/main.py`` ``step_uf85_cascade`` (6008-6074), ``route_lv324501`` (2436-2516), its call
(10006-10032), the seeds in ``State.__init__`` (6803-6814). The design data are in
`ureasim.data.unit_335`.
"""

from __future__ import annotations

from dataclasses import dataclass

from ureasim.control.process_loop import FlowLoop, ProcessLoop
from ureasim.control.ratio import BASE_FLOW_FLOOR, RatioMaster, RatioStation
from ureasim.data.unit_335 import (
    FFIC_335406_KC,
    FFIC_335406_OUT_HI_TH,
    FFIC_335406_OUT_LO_TH,
    FFIC_335406_RAT_HI,
    FFIC_335406_RAT_LO,
    FFIC_335406_RATIO_HI,
    FFIC_335406_TI_S,
    FIC_335405_KC,
    FIC_335405_OP_DES_PCT,
    FIC_335405_SP_HI_TH,
    FIC_335405_TI_S,
    FT_335405_TAU_S,
    PFD_697_KGH,
    UF85_DES_KGH,
    UF_RATIO_DES,
)
from ureasim.units.evaporation.melt_route import MeltRoute, melt_route

#: kg/h per t/h: FIC-335405 runs in t/h, as V1's loop does.
KG_PER_T = 1000.0


@dataclass(frozen=True)
class Uf85Result:
    """One tick of the dosing, in the fields V1's cascade returns, and the selector it feeds."""

    #: The achieved ratio FFIC-335406 read [-], the ratio it commands [-] and FIC-335405's set
    #: point [t/h].
    measured_ratio: float
    ratio_command: float
    flow_setpoint_th: float
    #: What the metering pumps delivered [kg/h], PFD 697.
    delivered_kgh: float
    #: True when LV-324501B or no melt has stopped the pumps.
    interlocked: bool
    #: LV-324501's selector with the UF85 joined: 609 forward on route A.
    route: MeltRoute


def ffic_335406(station: bool = True) -> RatioStation | RatioMaster:
    """FFIC-335406, the UF85-to-melt ratio, in AUTO on the PFD's ratio (V1's seed): the ratio
    station of its faceplate in the plant DCS, FIC-335405's set point its output in t/h (decided
    2026-10-28, handoff B-116 (a)); ``station`` False is V1's PI master on the ratio."""
    r = UF_RATIO_DES
    if station:
        return RatioStation(
            tag="FFIC-335406", sp=r, op=UF85_DES_KGH / KG_PER_T, pv=r, sp_lo=FFIC_335406_RAT_LO,
            sp_hi=FFIC_335406_RAT_HI, op_lo=FFIC_335406_OUT_LO_TH, op_hi=FFIC_335406_OUT_HI_TH,
            factor=1.0 / KG_PER_T)
    return RatioMaster(loop=ProcessLoop(
        tag="FFIC-335406", Kc=FFIC_335406_KC, Ti=FFIC_335406_TI_S, Td=0.0, act=+1.0,
        mode="AUTO", op=r, sp=r, pv=r, pv1=r, pv2=r, op_lo=0.0, op_hi=FFIC_335406_RATIO_HI,
        sp_lo=0.0, sp_hi=FFIC_335406_RATIO_HI))


def fic_335405(m_uf_kgh: float = UF85_DES_KGH) -> FlowLoop:
    """FIC-335405, the metering pumps' flow loop, in CAS, seeded delivering ``m_uf_kgh``: the
    ratio on the plant's design drain by default, the PFD's 694 kg/h at 50 % for V1's seed."""
    v = m_uf_kgh / KG_PER_T
    loop = ProcessLoop(
        tag="FIC-335405", Kc=FIC_335405_KC, Ti=FIC_335405_TI_S, Td=0.0, act=+1.0, mode="CAS",
        op=FIC_335405_OP_DES_PCT * m_uf_kgh / PFD_697_KGH, sp=v, pv=v, pv1=v, pv2=v,
        op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=FIC_335405_SP_HI_TH)
    return FlowLoop(loop=loop, design_flow=PFD_697_KGH / KG_PER_T,
                    op_des=FIC_335405_OP_DES_PCT, tau_s=FT_335405_TAU_S)


def uf85_step(master: RatioStation | RatioMaster, slave: FlowLoop, m_402_kgh: float,
              w_402: dict, t_402_c: float, recycle: bool, dt: float) -> Uf85Result:
    """Advance the dosing one tick and join what it delivers to the forward melt.

    Process utility
    ---------------
    Holds the additive in proportion to the melt as the plant's rate moves: the operator sets
    the ratio, not the flow. A melt header backing up onto LV-324501B stops the pumps at once,
    so no UF85 is dosed into melt returning to 323D002.

    Arguments
    ---------
    m_402_kgh, w_402, t_402_c
        Stage 2's drain this tick, its holdup's fractions and temperature
        (`SecondEvaporatorResult.m_402_kgh`, `.route.recycle_w`, `.route.recycle_t_c`).
    recycle
        LV-324501B selected (`SecondEvaporatorResult.recycle_selected`).
    """
    m_base = max(m_402_kgh, 0.0)
    if isinstance(master, RatioStation):
        return _station_step(master, slave, m_base, m_402_kgh, w_402, t_402_c, recycle, dt)
    result = master.step(max(slave.loop.pv * KG_PER_T, 0.0), m_base, dt,
                         slave_in_cascade=slave.loop.mode == "CAS", permissive_ok=not recycle)
    if result.interlocked:
        # The hard permissive: the pumps stop whatever the controllers say, and FT-335405
        # decays to zero on its own lag.
        slave.loop.op = 0.0
        slave.loop.observe(slave.force_measurement(0.0, dt))
        return Uf85Result(0.0, master.loop.op, 0.0, 0.0, True,
                          melt_route(m_402_kgh, w_402, t_402_c, recycle))
    flow_setpoint_th = max(result.demand / KG_PER_T, 0.0)
    delivered_kgh = max(slave.step(dt, cas_sp=flow_setpoint_th) * KG_PER_T, 0.0)
    ratio = delivered_kgh / m_base if m_base > BASE_FLOW_FLOOR else 0.0
    return Uf85Result(result.measured, result.command, flow_setpoint_th, delivered_kgh, False,
                      melt_route(m_402_kgh, w_402, t_402_c, recycle, ratio))


def _station_step(station: RatioStation, slave: FlowLoop, m_base: float, m_402_kgh: float,
                  w_402: dict, t_402_c: float, recycle: bool, dt: float) -> Uf85Result:
    """One tick of the dosing under FFIC-335406's ratio station (decided 2026-10-28, B-116 (a)).

    Process utility
    ---------------
    The plant's DCS multiplies rather than integrates: FIC-335405 is handed the ratio times the
    melt the moment the melt moves, and the metering pumps' own loop alone sets how fast the
    UF85 follows. LV-324501B selected, or no melt, stops the pumps as under V1's master; the
    station's base flow is then gone, so its output in AUTO is OUT L and its ratio set point
    stands.
    """
    if recycle or m_base <= BASE_FLOW_FLOOR:
        station.pv = 0.0
        if station.mode == "AUTO":
            station.op = station.op_lo
        slave.loop.op = 0.0
        slave.loop.observe(slave.force_measurement(0.0, dt))
        return Uf85Result(0.0, station.sp, 0.0, 0.0, True,
                          melt_route(m_402_kgh, w_402, t_402_c, recycle))
    measured = max(slave.loop.pv * KG_PER_T, 0.0) / m_base
    flow_setpoint_th = station.step(measured, m_base, slave_in_cascade=slave.loop.mode == "CAS")
    delivered_kgh = max(slave.step(dt, cas_sp=flow_setpoint_th) * KG_PER_T, 0.0)
    return Uf85Result(measured, station.sp, flow_setpoint_th, delivered_kgh, False,
                      melt_route(m_402_kgh, w_402, t_402_c, recycle, delivered_kgh / m_base))


__all__ = ["KG_PER_T", "Uf85Result", "ffic_335406", "fic_335405", "uf85_step"]
