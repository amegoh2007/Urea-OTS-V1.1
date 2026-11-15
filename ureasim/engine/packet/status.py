"""The plant's annunciation in the console packet: ``flags``, ``trips`` and ``trip_latched``.

``flags`` are V1's fourteen phase-boundary and consequence alarms, each read off the unit that
raises it in the port; ``trips`` are the interlocks' live initiators and ``trip_latched`` their
latches, the six V1 publishes. I 22.1 holds no latch on the DCS (decision 39): its "latched" state
is its live limit, as the port's interlock carries it.

``BOUNDARY_SINKS`` is the port's, not V1's: the overflows that leave the plant by decision (handoff
A-15, 2026-10-03), each vessel's flow and the temperature it leaves at, so an instructor sees what a
flooded vessel loses. V1 has no such streams.

``HAND_SWITCHES`` is the port's too: the maintained keyswitches' positions — HS-322915 and trip
21.2's five (AC4 PC21) — which the screens' keyswitches show (decided 2026-10-10, decision 98). V1
has none of the five and does not publish HS-322915's.

``PUMPS`` is the port's: the run state and mode of the auxiliary pumps a screen draws whose state V1
held and never published, 323P001A / B and 328P003A / B, which their START / STOP faceplates show
(decided 2026-11-13, decision 222). 322P002's pair stays at V1's own path, under ``ABSORB_328``.

Source: V1 ``backend/main.py`` ``State`` 7157-7174 (the keys and their order), ``step_sim``'s flag
writes (7379-10414) and 11302-11318.
"""

from __future__ import annotations

from ureasim.data.operator_commands import TRIP_21_HAND_SWITCHES, TRIP_35_HAND_SWITCHES
from ureasim.engine.packet._common import Tick
from ureasim.engine.plant.boundary import BOUNDARY_SINKS

__all__ = ["flags", "trips", "trip_latched", "boundary_sinks", "hand_switches", "pumps"]

#: The auxiliary pumps a screen draws whose run state V1 kept and did not publish (decision 222).
_PUMPS = ("323P001A", "323P001B", "328P003A", "328P003B", "335P002A", "335P002B", "329P003A", "329P003B",
           "328P007A", "328P007B", "328P006A", "328P006B", "328P002A", "328P002B", "323P008A",
           "323P008B", "323P003A", "323P003B", "335P001A", "335P001B")

#: The pairs an AC4 motor-control interlock holds, by pair: the unit that holds it and its state —
#: the low-level stops (decision 217) and 335P002's trip 35.3 (decision 228).
_HELD = {"328P002": ("328D001", "p002_stopped"), "328P006": ("328C002", "p006_stopped"),
         "328P007": ("328C004", "p007_stopped"), "335P001": ("324E003", "p001_stopped"),
         "323P008": ("323E011", "p008_tripped"), "335P002": ("335-TRIPS", "p002_held")}


def flags(t: Tick) -> dict:
    """V1's flags, in V1's order: the twelve its ``State`` seeds, then the ejector's stall its
    first tick adds. V1's first tick adds 320K002's surge and stonewall too; the machine is a
    boundary feed that does neither (decided 2026-10-08), so they are not published."""
    loop = t.r("PT-329201")
    c1 = t.r("322C001")
    return {
        "SCRUBBER_SOLIDIFICATION": bool(t.r("322E003").sump.solidification),
        "STRIPPER_SOLIDIFICATION": bool(t.r("322E001").sump.solidification),
        "LV322501_EROSION": bool(t.r("322E001").sump.lv_erosion),
        "LV323505_BLOWTHROUGH": bool(t.r("323F004").lv505_blowthrough),
        "LV323501_BLOWTHROUGH": bool(t.r("323C003").lv501_blowthrough),
        "CARBAMATE_DEPOSITION": bool(t.r("HV-322604").valve.carbamate_deposition),
        "RATIO_PV_BAD": bool(t.r("321").ratio_pv_bad),
        "SYN_PSV_LIFT": bool(loop.relief_lifted),
        "TOXIC_RELEASE": loop.m_relief_kgh > 0.0,
        "LP_ABSORBER_OVERLOAD": bool(c1.overloaded),
        "LP_ABSORBER_RELIEF": bool(c1.relief_lifted),
        "EJECTOR_STALL": bool(t.r("322F001").stalled),
    }


def _interlocks(t: Tick) -> dict:
    syn, t35 = t.units["SYN-TRIPS"], t.units["335-TRIPS"]
    return {"21_2": syn.i_21_2, "21_8": syn.i_21_8, "21_10": syn.i_21_10,
            "22_1": t.units["TRIPS"].i_22_1, "35_1": t35.flag_35_1, "35_4": t35.flag_35_4}


def trips(t: Tick) -> dict:
    """Each interlock's live initiator."""
    return {k: bool(i.live) for k, i in _interlocks(t).items()}


def trip_latched(t: Tick) -> dict:
    """Each interlock's latch."""
    return {k: bool(i.latched) for k, i in _interlocks(t).items()}


def boundary_sinks(t: Tick) -> dict:
    """Each boundary sink's flow [kg/h] and temperature [deg C] (handoff A-15)."""
    out = {}
    for unit, (flow, temp) in BOUNDARY_SINKS.items():
        r = t.r(unit)
        out[unit] = {"m_kgh": round(getattr(r, flow), 1), "t_c": round(getattr(r, temp), 2)}
    return out


def pumps(t: Tick) -> dict:
    """Each auxiliary pump's run state, its run command and mode under its tag (decision 222).
    ``on`` is the machine's run feedback, which the icon and the trend show: off while AC4's
    low-level stop holds the pair (decision 217), or trip 35.3 335P002 (decision 228), its command
    still on. ``cmd`` is the operator's command, which the START / STOP faceplate's live button
    follows."""
    out = {}
    for tag in _PUMPS:
        unit, held = _HELD.get(tag[:-1], (None, ""))
        cmd = bool(t.operator[tag]["on"])
        out[tag] = {"on": cmd and not (unit and getattr(t.units[unit], held)), "cmd": cmd,
                    "mode": t.operator[tag]["mode"]}
    return out


def hand_switches(t: Tick) -> dict:
    """Each maintained keyswitch's position, True turned, under its tag's key (decision 98)."""
    return {f"HS_{tag}": bool(t.operator[f"HS-{tag}"])
            for tag in ("322915",) + TRIP_21_HAND_SWITCHES + TRIP_35_HAND_SWITCHES}
