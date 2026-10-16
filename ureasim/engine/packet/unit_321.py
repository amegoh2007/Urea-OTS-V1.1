"""Unit 321 in the console packet: the NH3 pumping station's flat keys, its pumps, the N/C ratio
block and the two speed controllers' faceplates.

V1 publishes unit 321 at the packet's top level (``FI_321401``, ``TI_top1`` ... ``TI_321020``),
its machines as ``pumpA`` / ``pumpB``, the ratio block as ``ratio`` and SIC-321950 / SIC-321951
under ``controllers``. Each key below is V1's, with V1's rounding, read off the port's
`FeedStation` (`ureasim.units.feed.station`) and its result.

Source: V1 ``backend/main.py`` 10466-10503 (the flat keys), 11305-11318 (``ratio``,
``ext_override``, ``controllers``).
"""

from __future__ import annotations

from ureasim.data.console_packet import (
    LSL_321501_FRAC,
    PI_321003_DES_BARG,
    PI_DISCH_DES_BARG,
    PI_DISCH_IDLE_BARG,
    TT_321002_STRAT_K,
)
from ureasim.data.operator_commands import EXT_OVERRIDE_TAG
from ureasim.engine.packet._common import Tick

__all__ = ["flat_keys", "ratio", "controllers", "ext_override"]


def _pump(pump) -> dict:
    """V1's pump tile: running, speed [rpm], current [A], the SIC's mode letter."""
    return {"on": pump.running, "speed": round(pump.speed_rpm, 1),
            "current": round(pump.current, 1), "mode": pump.mode_letter}


def flat_keys(t: Tick) -> dict:
    """The station's indications at the packet's top level, in V1's order.

    Process utility
    ---------------
    Screen 321-1: the drum's two thermowells, its level and pressure, FQT-321401's delivered
    ammonia, the suction transmitters and the sub-cooling margins the 21.2 trip watches, the two
    machines and the discharge header the loop is fed from.
    """
    st, res = t.units["321"], t.r("321")
    drum = st.drum
    running = st.pump_a.running or st.pump_b.running
    p_disch = (PI_DISCH_IDLE_BARG + (PI_DISCH_DES_BARG - PI_DISCH_IDLE_BARG) * res.phi_forward
               if running else PI_DISCH_IDLE_BARG)
    return {
        "FI_321401": round(res.flow_total_th, 2),
        "TI_top1": round(drum.temperature_c, 1),
        "TI_top2": round(drum.temperature_c - TT_321002_STRAT_K * (1.0 - drum.level_frac), 1),
        "LSL_321501": drum.level_frac < LSL_321501_FRAC,
        "PI_top1": round(drum.top_pressure_barg, 1),
        "PI_top2": round(drum.top_pressure_barg, 1),
        "PI_header": round(PI_321003_DES_BARG * res.phi_forward, 1),
        "LI_321501": round(drum.level_frac * 100.0, 1),
        "totalizer": round(drum.totalizer_t, 2),
        "XV_321901": bool(st.xv_321901_open),
        "XV_322901": bool(st.xv_322901_open),
        "PI_321201": round(res.feed_pressure_barg, 1),
        "PI_321202": round(res.feed_pressure_barg, 1),
        "PI_321201_alarm": bool(st.pump_a.fault),
        "PI_321202_alarm": bool(st.pump_b.fault),
        "PY_321201": round(res.vapour_pressure_bara, 2),
        "PY_321202": round(res.vapour_pressure_bara, 2),
        "PDY_321203": round(res.subcooling_a_bar, 2),
        "PDY_321204": round(res.subcooling_b_bar, 2),
        "PDY_321203_alarm": res.subcooling_a_bar <= 0.0,
        "PDY_321204_alarm": res.subcooling_b_bar <= 0.0,
        "pumpA": _pump(st.pump_a),
        "pumpB": _pump(st.pump_b),
        "PI_disch": round(p_disch, 1),
        "TI_321020": round(res.discharge_t_c, 1),
    }


def ratio(t: Tick) -> dict:
    """FFIC-321404, the N/C ratio block: its set point, the published PV, V1's balance (the PV,
    held while the measurement is bad) and each machine's share."""
    st, res = t.units["321"], t.r("321")
    return {"SP": round(st.ratio_sp, 3), "PV": round(st.ratio_pv, 3),
            "bal": round(st.ratio_pv, 3), "NC_A": round(res.ratio_nc_a, 3),
            "NC_B": round(res.ratio_nc_b, 3)}


def controllers(t: Tick) -> dict:
    """SIC-321950 / SIC-321951, the machines' speed controllers, as their faceplates read them
    (V1's ``Controller.to_packet``)."""
    st = t.units["321"]
    return {"SIC_321950": st.sic_a.as_packet(), "SIC_321951": st.sic_b.as_packet()}


def ext_override(t: Tick) -> bool:
    """EXT. OVERRIDE of 321P002 A/B's run signal."""
    return bool(t.operator[EXT_OVERRIDE_TAG])
