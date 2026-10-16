"""The operator's commands — V1's command set applied to the engine's plant, each one accepted or
refused with its reason.

What this is
------------
Every action an operator or instructor takes on a console arrives here as V1's command dictionary
(``{"type": "hic_set", "value": 60}``), after the server has checked the station's role and its
plant sections (`ureasim.net.protocol`). This module is the engine's half (Claude.md §4a): whether
the PLANT will take the command. A latched trip, a valve a trip holds shut, a set point a loop in
MAN does not use, a control the DCS does not have — each is refused, with the process reason,
and the reason travels back to the trainee. A command V1 dropped without a word is answered here:
a silently ignored command teaches a trainee that the plant ignored them.

The command set is V1's, every type and every clamp (`data.operator_commands`), applied to where
the rewrite keeps each state: the hand valves and switches in ``PlantState.operator``, the loops in
``PlantState.loops`` and inside their units, the pumps and block valves on their units. The
decided departures: XV-322915 has no operator open (handoff B-59, decision 40), so an
``xv_toggle`` on it is refused and HS-322915, its OVERRIDE CLOSE keyswitch, is set by
``keyswitch_set``; a command is applied whole or not at all (V1 applied a faceplate's mode and
dropped the set point it could not use in the same message).

The simulator's own controls — pacing, freeze, reset, exercise save and restore — are not plant
equipment and are not applied here (`SIMULATOR_COMMANDS`); the session that owns the clock
answers them.

Source: V1 ``backend/main.py`` ``handle_cmd`` (11413-11787) and its REST controller handler
(11823-11871: a set point needs AUTO, an output MAN, a bias CAS).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from ureasim.control.process_loop import ProcessLoop
from ureasim.control.ratio import RatioStation
from ureasim.data.operator_commands import (
    AUX_PUMP_SEEDS,
    CPL_MAX_FACTOR,
    EXT_OVERRIDE_TAG,
    FACEPLATE_MODES,
    FIC_329409_SP_MAX_FACTOR,
    PIC_335201_OP_MAX_BARG,
    RATIO_SP_MAX,
    RATIO_SP_MIN,
    STEAM_SP_MAX_BARA,
    SYNTHESIS_TRIPS,
    TRIP_21_HAND_SWITCHES,
    TIC_329005_SP_MIN_C,
)
from ureasim.data.unit_321 import PUMP_RATED_RPM
from ureasim.data.unit_322c001 import C001_CPL_DES_KGH
from ureasim.data.unit_322e002 import LEAK_DEFAULT_TH
from ureasim.data.unit_322e003 import CCW_KGH_DES, CCW_T_OUT_DES_C
from ureasim.data.unit_324 import PIC_335201_DES_BARG, PIC_335201_RELIEF_BARG
from ureasim.engine.state import PlantState
from ureasim.units.steam.drums import D001, D005, D009

__all__ = ["CommandResult", "SIMULATOR_COMMANDS", "PLANT_COMMANDS", "apply_command", "faceplates"]

#: Commands that act on the exercise, not the plant: the session answers them.
SIMULATOR_COMMANDS = frozenset({"set_sim_mode", "reset_sim", "freeze", "snapshot_save",
                                "snapshot_load", "assign"})


@dataclass(frozen=True)
class CommandResult:
    """The plant's answer to one command: accepted or not, why not, and what was done."""

    ok: bool
    reason: str = ""
    text: str = ""


class _Refused(Exception):
    """A command the plant will not take; the message is the reason the operator reads."""


# ======================================================================================
# Payload helpers
# ======================================================================================

def _num(cmd: Mapping, key: str, lo: float = -math.inf, hi: float = math.inf) -> float:
    """A finite number from the payload, clamped to [lo, hi] as V1's ``_finite`` and ``clamp``."""
    try:
        v = float(cmd[key])
    except KeyError as exc:
        raise _Refused(f"the command needs {key!r}") from exc
    except (TypeError, ValueError) as exc:
        raise _Refused(f"{key!r} must be a number") from exc
    if not math.isfinite(v):
        raise _Refused(f"{key!r} must be finite")
    return max(lo, min(hi, v))


def _want(cmd: Mapping) -> bool | None:
    """An explicit start / stop (``on``), or None for a toggle."""
    return None if cmd.get("on") is None else bool(cmd["on"])


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _trip(plant: PlantState, key: str):
    trips = plant.units["SYN-TRIPS"]
    try:
        return getattr(trips, f"i_{key}")
    except AttributeError as exc:
        raise _Refused(f"no trip {key!r}") from exc


def _trip_name(key: str) -> str:
    return "trip " + key.replace("_", ".")


# ======================================================================================
# Unit 321 and the synthesis trips
# ======================================================================================

def _pump_toggle(plant: PlantState, cmd: Mapping, _r) -> str:
    """321P002 A/B, start / stop, and 329P006A/B, the tempered-water pumps.

    A 321P002 machine starts only while its AC4 trip flag (21.8 / 21.10, which carries 21.2) is
    healthy and 22.2 is not latched; a refused start names what holds it. A restart acknowledges
    22.2 once its cause has recovered and resolves the machine's own fault (the lube-oil
    abstraction), as V1's faceplate does. Stopping is always allowed.
    """
    pid, want = str(cmd.get("id", "")), _want(cmd)
    if pid in ("329P006A", "329P006B"):
        ccw = plant.loops["322E003"][0]
        attr = "p329p006a" if pid.endswith("A") else "p329p006b"
        setattr(ccw, attr, (not getattr(ccw, attr)) if want is None else want)
        return f"{pid} {'started' if getattr(ccw, attr) else 'stopped'}"
    if pid not in ("A", "B"):
        raise _Refused(f"no pump {pid!r}")
    st = plant.units["321"]
    pump = st.pump_a if pid == "A" else st.pump_b
    own = "21_8" if pid == "A" else "21_10"
    starting = (not pump.running) if want is None else (want and not pump.running)
    acked = []
    if starting:
        trip = _trip(plant, "22_2")
        if trip.latched and trip.reset():
            acked.append(_trip_name("22_2"))
        if _trip(plant, "22_2").latched:
            raise _Refused(f"{pump.tag} cannot start: trip 22.2 latched, its cause still live")
        if _trip(plant, own).latched:
            why = ("trip 21.2's flag is lost — no HP ammonia pump running (HS-321634 bypasses it), "
                   "no 323P001 (HS-323604), no CO2 to the stripper (HS-322606) or a trip hand "
                   "switch turned" if _trip(plant, "21_2").latched else
                   "XV-321901 shut, its suction's sub-cooling below PDY's L2, or within 10 s of "
                   "its stop")
            raise _Refused(f"{pump.tag} cannot start: {_trip_name(own)}'s flag is lost: {why} "
                           "(AC4 PC21)")
        if pump.fault:
            pump.fault = False
            acked.append(f"{pump.tag} fault")
    pump.running = (not pump.running) if want is None else want
    done = f"{pump.tag} {'started' if pump.running else 'stopped'}"
    return done + (f"; acknowledged {', '.join(acked)}" if acked else "")


def _trip_reset(plant: PlantState, cmd: Mapping, _r) -> str:
    """Clear trip 22.2's latch once its cause has recovered. AC4's 21.2, 21.8 and 21.10 hold no
    latch: they clear with their inputs, and the pumps and XV-321901 / XV-322901 are started and
    opened again by hand."""
    key = cmd.get("id")
    if key == "22_1":
        raise _Refused("I 22.1 holds no latch to reset: it releases XV-322915 itself once TT-322015 "
                       "is back below its limit (AC4 PC22.5.1)")
    if key in ("21_2", "21_8", "21_10"):
        raise _Refused(f"{_trip_name(key)} holds no latch to reset: its flag clears with its inputs "
                       "(AC4 PC21); start the pumps and open XV-321901 / XV-322901 again")
    keys = SYNTHESIS_TRIPS if key in (None, "ALL") else (str(key),)
    cleared, live = [], []
    for k in keys:
        trip = _trip(plant, k)
        if not trip.latched or not trip.operator_resettable:
            continue
        if trip.reset():
            cleared.append(_trip_name(k))
        else:
            live.append(_trip_name(k))
    if live:
        raise _Refused(f"{', '.join(live)} not reset: the cause is still live"
                       + (f" ({', '.join(cleared)} reset)" if cleared else ""))
    return f"reset {', '.join(cleared)}" if cleared else "no latched trip to reset"


def _tube_leak(plant: PlantState, cmd: Mapping) -> str:
    """The instructor's 322E002 tube leak (handoff B-82): ``rate`` (or ``value``) its rate at the
    design differential [t/h], 10 t/h when the trigger carries none (B-90, decided 2026-10-09);
    ``clear_fault`` stops it."""
    unit = plant.units["322E002"]
    if cmd.get("type") == "clear_fault":
        unit.leak_severity_kgh = 0.0
        return "322E002 tube leak stopped"
    field = "rate" if "rate" in cmd else "value"
    rate_th = _num(cmd, field, 0.0, math.inf) if field in cmd else LEAK_DEFAULT_TH
    unit.leak_severity_kgh = rate_th * 1000.0
    return f"322E002 tube leak {unit.leak_severity_kgh / 1000.0:g} t/h at the design differential"


def _fault(plant: PlantState, cmd: Mapping, _r) -> str:
    """The instructor's equipment faults: 321P002 A or B's (the lube-oil abstraction), which stops
    the machine on its own protection until it is restarted, and 322E002's tube leak (B-82)."""
    if str(cmd.get("id", "")).upper() == "322E002":
        return _tube_leak(plant, cmd)
    key = str(cmd.get("id", "")).upper().replace("PUMP", "").replace("_FAULT", "")
    st = plant.units["321"]
    pump = {"A": st.pump_a, "B": st.pump_b}.get(key)
    if pump is None:
        raise _Refused(f"no equipment fault {cmd.get('id')!r}")
    pump.fault = bool(cmd.get("value", True)) if cmd.get("type") != "clear_fault" else False
    return f"{pump.tag} fault {'set' if pump.fault else 'cleared'}"


def _controller_set(plant: PlantState, cmd: Mapping, _r) -> str:
    """SIC-321950 / SIC-321951, the pumps' speed controllers: mode, output, set point (per cent
    or rpm) and the cascade bias. Entering CAS puts the ratio set point on its live value."""
    cid = str(cmd.get("id", cmd.get("tag", "")))
    st = plant.units["321"]
    ctrl = {"SIC_321950": st.sic_a, "SIC_321951": st.sic_b}.get(cid.replace("-", "_"))
    if ctrl is None:
        raise _Refused(f"no controller {cid!r} on controller_set; the unit 323, 328 and 324 "
                       "faceplates take r323_ctrl_set")
    mode = str(cmd.get("mode", ctrl.mode)).upper()
    if mode not in ("MAN", "AUTO", "CAS", "OOS"):
        raise _Refused(f"no mode {mode!r}")
    _needs(cmd, mode, op="MAN", sp="AUTO", sp_rpm="AUTO", nc="CAS")
    values = {k: _num(cmd, k) for k in ("op", "sp", "sp_rpm", "nc") if k in cmd}
    ctrl.set_mode(mode)
    if mode == "CAS" and "mode" in cmd:
        st.ratio_sp = round(st.ratio_pv, 3)
    if "op" in values:
        ctrl.set_op(values["op"])
    if "sp_rpm" in values:
        ctrl.set_sp(values["sp_rpm"] / PUMP_RATED_RPM * 100.0)
    elif "sp" in values:
        ctrl.set_sp(values["sp"])
    if "nc" in values:
        ctrl.set_bias(values["nc"])
    return f"{ctrl.tag} {ctrl.mode}"


def _needs(cmd: Mapping, mode: str, **fields: str) -> None:
    """Refuse a field the loop does not use in ``mode`` (V1's REST rule: a set point in AUTO, an
    output in MAN, a bias in CAS)."""
    for name, wanted in fields.items():
        if name in cmd and mode != wanted:
            raise _Refused(f"{name!r} is the operator's in {wanted} only; the loop is in {mode}")


def _ratio_set(plant: PlantState, cmd: Mapping, _r) -> str:
    st = plant.units["321"]
    st.ratio_sp = _num(cmd, "sp", RATIO_SP_MIN, RATIO_SP_MAX)
    return f"FFIC-321404 set point {st.ratio_sp:g}"


# ======================================================================================
# Hand valves, block valves, switches, pumps
# ======================================================================================

def _operator(tag: str, key: str, lo: float, hi: float, label: str | None = None) -> Callable:
    """A handler writing one operator entry from one payload field, clamped."""
    def handler(plant: PlantState, cmd: Mapping, _r) -> str:
        plant.operator[tag] = _num(cmd, key, lo, hi)
        return f"{label or tag} {plant.operator[tag]:g}"
    return handler


def _co2_set(plant: PlantState, cmd: Mapping, _r) -> str:
    """The CO2 asked of 320K002, the instructor's boundary. Trip 22.2 trips the machine and takes
    the demand to zero (B-88): a demand is refused while it is latched, as XV-322902 is; and while
    21.2's flag is lost, which shuts XV-322902 (decided 2026-10-16, decision 83's class)."""
    value = _num(cmd, "value", 0.0, math.inf)
    if value > 0.0 and _trip(plant, "22_2").latched:
        raise _Refused(f"320K002 is tripped by {_trip_name('22_2')}, latched: reset the trip "
                       "before restoring the CO2 demand")
    if value > 0.0 and _trip(plant, "21_2").latched:
        raise _Refused(f"XV-322902 is held shut by {_trip_name('21_2')}'s flag (AC4 PC21.5.1): "
                       "restore the flag before restoring the CO2 demand")
    plant.operator["320K002-CO2"] = value
    return f"320K002 CO2 demand {value:g}"


def _hic2_set(plant: PlantState, cmd: Mapping, _r) -> str:
    line = plant.units["320K002"]
    line.hic_min_pct = _num(cmd, "value", 0.0, 100.0)
    return f"HIC-322203 {line.hic_min_pct:g} %"


def _xv_toggle(plant: PlantState, cmd: Mapping, _r) -> str:
    """The block valves V1's screens toggle. A valve a latched trip holds shut is refused open
    (the trip would shut it on the next tick); XV-322915 has no operator open at all (B-59)."""
    xv = str(cmd.get("id", ""))
    st = plant.units["321"]
    if xv == "322915":
        raise _Refused("XV-322915 has no operator open on the DCS: I 22.1 opens it, and HS-322915, "
                       "the OVERRIDE CLOSE keyswitch, is its only control (keyswitch_set)")
    # The trips that hold each valve shut: 21.2's flag resets XV-321901's, XV-322901's,
    # XV-322902's and XV-322903's flip-flops (AC4 PC21.5.1, XV-322902 through the Safeguard SG1).
    holding = {"321901": ("21_2",), "322901": ("21_2",), "322902": ("22_2", "21_2"),
               "322903": ("21_2",)}.get(xv, ())
    if xv in ("321901", "322901", "322902"):
        obj, attr = {"321901": (st, "xv_321901_open"), "322901": (st, "xv_322901_open"),
                     "322902": (plant.units["320K002"], "xv_322902_open")}[xv]
        opening = not getattr(obj, attr)
    else:
        obj, attr = None, {"322903": "XV-322903", "323D002TIE": "HV-323D002-TIE"}.get(xv)
        if attr is None:
            raise _Refused(f"no block valve {xv!r}")
        opening = not plant.operator[attr]
    for trip in holding:
        if opening and _trip(plant, trip).latched:
            raise _Refused(f"XV-{xv} is held shut by {_trip_name(trip)}"
                           + ("'s flag (AC4 PC21.5.1)" if trip == "21_2" else ", latched"))
    if obj is None:
        plant.operator[attr] = opening
        return f"{attr} {'opened' if opening else 'closed'}"
    setattr(obj, attr, opening)
    return f"XV-{xv} {'opened' if opening else 'closed'}"


def _keyswitch_set(plant: PlantState, cmd: Mapping, _r) -> str:
    """A maintained hand switch: HS-322915, XV-322915's OVERRIDE CLOSE keyswitch (B-59), and AC4
    PC21.5.1's on trip 21.2 — HS-321634, HS-323604 and HS-322606 its start-up bypasses, HS-321603
    and HS-321604 its trip switches (handoff A-12)."""
    hs = str(cmd.get("id", ""))
    if hs != "HS-322915" and hs not in {f"HS-{t}" for t in TRIP_21_HAND_SWITCHES}:
        raise _Refused(f"no keyswitch {cmd.get('id')!r}")
    if "on" not in cmd:
        raise _Refused("the command needs 'on'")
    plant.operator[hs] = bool(cmd["on"])
    return f"{hs} {'turned' if plant.operator[hs] else 'released'}"


def _aux_pump_toggle(plant: PlantState, cmd: Mapping, _r) -> str:
    """A running / standby auxiliary pump: its mode and its run. 322P002 runs while either of
    its pair does."""
    pid = str(cmd.get("id", ""))
    if pid not in AUX_PUMP_SEEDS:
        raise _Refused(f"no auxiliary pump {pid!r}")
    pump = plant.operator[pid]
    if "mode" in cmd:
        mode = str(cmd["mode"]).upper()
        if mode not in ("AUTO", "MAN"):
            raise _Refused(f"no mode {mode!r} for {pid}")
        pump["mode"] = mode
    pump["on"] = bool(cmd["on"]) if "on" in cmd else not pump["on"]
    if pid.startswith("322P002"):
        plant.operator["322P002"] = plant.operator["322P002A"]["on"] or plant.operator["322P002B"]["on"]
    return f"{pid} {'running' if pump['on'] else 'stopped'}, {pump['mode']}"


def _ext_override(plant: PlantState, cmd: Mapping, _r) -> str:
    plant.operator[EXT_OVERRIDE_TAG] = bool(cmd["value"])
    return f"321P002 EXT. OVERRIDE {'on' if plant.operator[EXT_OVERRIDE_TAG] else 'off'}"


def _pic335201_set(plant: PlantState, cmd: Mapping, _r) -> str:
    plant.boundary["PIC-335201.barg"] = _num(cmd, "op", 0.0, PIC_335201_OP_MAX_BARG)
    return f"PIC-335201 {plant.boundary['PIC-335201.barg']:g} bar g"


def _lv324501_route_set(plant: PlantState, cmd: Mapping, _r) -> str:
    """V1's retired route switch: B puts the 335 header over LV-324501B's relief, A restores it."""
    if "route" in cmd:
        route = str(cmd["route"]).strip().upper()
        if route not in ("A", "B"):
            raise _Refused("LV-324501's route is A or B")
        relief = route == "B"
    else:
        relief = bool(cmd.get("recycle", False))
    plant.boundary["PIC-335201.barg"] = (PIC_335201_RELIEF_BARG + 0.5 if relief
                                         else PIC_335201_DES_BARG)
    return f"LV-324501 route {'B' if relief else 'A'}"


# ======================================================================================
# The dictionary loops V1 sets field by field, and the inline faceplates
# ======================================================================================

def _loop_fields(cmd: Mapping, loop: Any, prefix: str, sp_lo: float, sp_hi: float,
                 label: str) -> str:
    """V1's dictionary-loop handler (``pic_set``, ``lic_set``, ``fic_set``, ``tic_set``): a
    mode, bumpless into AUTO (the set point takes the PV); the output in MAN; the set point in
    any mode."""
    get = lambda f: getattr(loop, prefix + f)   # noqa: E731
    mode = str(cmd.get("mode", get("mode"))).upper()
    if mode not in ("MAN", "AUTO"):
        raise _Refused(f"{label} offers AUTO and MAN, not {mode}")
    _needs(cmd, mode, op="MAN")
    values = {k: _num(cmd, k) for k in ("op", "sp") if k in cmd}
    if mode == "AUTO" and get("mode") != "AUTO":
        setattr(loop, prefix + "sp", _clamp(get("pv"), sp_lo, sp_hi))
    setattr(loop, prefix + "mode", mode)
    if "op" in values:
        setattr(loop, prefix + "op", _clamp(values["op"], 0.0, 100.0))
    if "sp" in values:
        setattr(loop, prefix + "sp", _clamp(values["sp"], sp_lo, sp_hi))
    return f"{label} {mode}"


def _pic_set(plant: PlantState, cmd: Mapping, _r) -> str:
    loop = plant.loops["320K002"][0]
    return _loop_fields(cmd, loop, "", loop.sp_lo, loop.sp_hi, "PIC-322203")


def _lic_set(plant: PlantState, cmd: Mapping, _r) -> str:
    return _loop_fields(cmd, plant.loops["322E001"][0], "", 0.0, 100.0, "LIC-322501")


def _fic_set(plant: PlantState, cmd: Mapping, _r) -> str:
    return _loop_fields(cmd, plant.loops["322E003"][0], "fic_", 0.0,
                        FIC_329409_SP_MAX_FACTOR * CCW_KGH_DES / 1000.0, "FIC-329409")


def _tic_set(plant: PlantState, cmd: Mapping, _r) -> str:
    return _loop_fields(cmd, plant.loops["322E003"][0], "tic_", TIC_329005_SP_MIN_C,
                        CCW_T_OUT_DES_C, "TIC-329005")


def faceplates(plant: PlantState) -> dict:
    """Every inline faceplate's loop on this plant, by tag, wherever its unit keeps it: the
    process loops and the ratio stations (FFIC-329401)."""
    found: dict = {}
    seen: set = set()

    def walk(obj: Any) -> None:
        if id(obj) in seen or isinstance(obj, (int, float, str, bool, type(None))):
            return
        seen.add(id(obj))
        if isinstance(obj, (ProcessLoop, RatioStation)):
            found.setdefault(obj.tag, obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                walk(v)
        elif isinstance(obj, (list, tuple)):
            for v in obj:
                walk(v)
        elif type(obj).__module__.startswith("ureasim") and hasattr(obj, "__dict__"):
            for v in vars(obj).values():
                walk(v)

    walk(plant.loops)
    walk(plant.units)
    return found


def _r323_ctrl_set(plant: PlantState, cmd: Mapping, _r) -> str:
    """An inline faceplate on units 323, 328 and 324: a mode among those it offers, bumpless into
    AUTO; the set point in AUTO; the output in MAN."""
    tag = str(cmd.get("id", "")).replace("_", "-", 1)
    if tag not in FACEPLATE_MODES:
        raise _Refused(f"no faceplate {cmd.get('id')!r}")
    loop = faceplates(plant).get(tag)
    if loop is None:
        raise _Refused(f"{tag} is not on this model")
    mode = str(cmd.get("mode", loop.mode)).upper()
    if mode not in FACEPLATE_MODES[tag]:
        raise _Refused(f"{tag} offers {', '.join(FACEPLATE_MODES[tag])}, not {mode}")
    _needs(cmd, mode, op="MAN", sp="AUTO")
    values = {k: _num(cmd, k) for k in ("op", "sp") if k in cmd}
    if mode == "AUTO" and loop.mode != "AUTO":
        loop.sp = _clamp(loop.pv, loop.sp_lo, loop.sp_hi)
    loop.mode = mode
    if "sp" in values:
        loop.sp = _clamp(values["sp"], loop.sp_lo, loop.sp_hi)
    if "op" in values:
        loop.op = _clamp(values["op"], loop.op_lo, loop.op_hi)
    return f"{tag} {mode}"


# ======================================================================================
# Unit 329
# ======================================================================================

def _steam_valve(attr_path: tuple, label: str) -> Callable:
    """A steam valve's stroke written by hand; a controller in AUTO moves it again next tick, as
    on V1."""
    def handler(plant: PlantState, cmd: Mapping, _r) -> str:
        obj = plant.units["329"]
        for part in attr_path[:-1]:
            obj = obj[part] if isinstance(obj, dict) else getattr(obj, part)
        value = _num(cmd, "op", 0.0, 100.0)
        if label == "HV-329601" and plant.units["329"].hv_329601.blocked:
            raise _Refused("HV-329601 is forced by trip 21.2; its hand controller follows")
        setattr(obj, attr_path[-1], value)
        return f"{label} {value:g} %"
    return handler


def _pic329204_set(plant: PlantState, cmd: Mapping, _r) -> str:
    pic = plant.units["329"].pic_329204
    mode = _two_modes(cmd, pic.mode, "PIC-329204")
    _needs(cmd, mode, op="MAN")
    values = {k: _num(cmd, k) for k in ("op", "sp") if k in cmd}
    pic.mode = mode
    if "sp" in values:
        pic.sp_bara = _clamp(values["sp"], 0.0, STEAM_SP_MAX_BARA)
    if "op" in values:
        pic.op_pct = _clamp(values["op"], 0.0, 100.0)
    return f"PIC-329204 {mode}"


def _pic329205_set(plant: PlantState, cmd: Mapping, _r) -> str:
    """The split range: one output, 0-50 % PV-329205A admitting, 50-100 % PV-329205B letting
    down."""
    pic = plant.units["329"].pic_329205
    mode = _two_modes(cmd, pic.mode, "PIC-329205")
    _needs(cmd, mode, op="MAN")
    values = {k: _num(cmd, k) for k in ("op", "sp") if k in cmd}
    pic.mode = mode
    if "sp" in values:
        pic.sp_bara = _clamp(values["sp"], 0.0, STEAM_SP_MAX_BARA)
    if "op" in values:
        op = _clamp(values["op"], 0.0, 100.0)
        pic.op_a_pct, pic.op_b_pct = (op * 2.0, 0.0) if op <= 50.0 else (0.0, (op - 50.0) * 2.0)
    return f"PIC-329205 {mode}"


def _two_modes(cmd: Mapping, current: str, label: str) -> str:
    mode = str(cmd.get("mode", current)).upper()
    if mode not in ("AUTO", "MAN"):
        raise _Refused(f"{label} offers AUTO and MAN, not {mode}")
    return mode


def _level_set(tag: str, drum) -> Callable:
    """LIC-329502 / 503 / 504: bumpless into AUTO on the level the transmitter reads."""
    def handler(plant: PlantState, cmd: Mapping, _r) -> str:
        st = plant.units["329"]
        loop = getattr(st, tag.lower().replace("-", "_"))
        mode = _two_modes(cmd, loop.mode, tag)
        _needs(cmd, mode, op="MAN")
        values = {k: _num(cmd, k) for k in ("op", "sp") if k in cmd}
        if mode == "AUTO" and loop.mode != "AUTO":
            loop.sp_pct = _clamp(drum[0].level_pct(getattr(st, drum[1])), 0.0, 100.0)
        loop.mode = mode
        if "sp" in values:
            loop.sp_pct = _clamp(values["sp"], 0.0, 100.0)
        if "op" in values:
            loop.op_pct = _clamp(values["op"], 0.0, 100.0)
        return f"{tag} {mode}"
    return handler


def _master207_set(plant: PlantState, cmd: Mapping, _r) -> str:
    trio = plant.units["329"].pic_329207
    if "on" in cmd:
        trio.master_on = bool(cmd["on"])
    if "sp" in cmd:
        trio.master_sp_bara = _num(cmd, "sp", 0.0, STEAM_SP_MAX_BARA)
    return f"MASTER-329207 {'ON' if trio.master_on else 'OFF'}, {trio.master_sp_bara:g} bar a"


def _leg_set(leg: str) -> Callable:
    """One leg of the PIC-329207 trio, honoured only with the master OFF (ON locks the trio)."""
    def handler(plant: PlantState, cmd: Mapping, _r) -> str:
        trio = plant.units["329"].pic_329207
        if trio.master_on:
            raise _Refused(f"PIC-329207{leg} follows MASTER-329207 while it is ON")
        loop = trio.legs[leg]
        mode = _two_modes(cmd, loop.mode, f"PIC-329207{leg}")
        _needs(cmd, mode, op="MAN")
        values = {k: _num(cmd, k) for k in ("op", "sp") if k in cmd}
        loop.mode = mode
        if "sp" in values:
            loop.sp_bara = _clamp(values["sp"], 0.0, STEAM_SP_MAX_BARA)
        if "op" in values:
            loop.op_pct = _clamp(values["op"], 0.0, 100.0)
        return f"PIC-329207{leg} {mode}"
    return handler


# ======================================================================================
# Dispatch
# ======================================================================================

#: The plant's command types and their handlers.
PLANT_COMMANDS: dict = {
    "pump_toggle": _pump_toggle,
    "trip_reset": _trip_reset,
    "trigger_fault": _fault,
    "clear_fault": _fault,
    "controller_set": _controller_set,
    "ratio_set": _ratio_set,
    "co2_set": _co2_set,
    "cpl_set": _operator("FIC-322404", "value", 0.0, CPL_MAX_FACTOR * C001_CPL_DES_KGH,
                         "FT-322404"),
    "hic_set": _operator("HIC-322602", "value", 0.0, 100.0),
    "hic2_set": _hic2_set,
    "hic605_set": _operator("HIC-322605", "op", 0.0, 100.0),
    "hic604_set": _operator("HIC-322604", "op", 0.0, 100.0),
    "hic9605_set": _operator("HIC-329605", "op", 0.0, 100.0),
    "hic9606_set": _operator("HIC-329606", "op", 0.0, 100.0),
    "hic323605_set": _operator("HIC-323605", "op", 0.0, 100.0),
    "xv_toggle": _xv_toggle,
    "keyswitch_set": _keyswitch_set,
    "aux_pump_toggle": _aux_pump_toggle,
    "ext_override": _ext_override,
    "pic_set": _pic_set,
    "lic_set": _lic_set,
    "fic_set": _fic_set,
    "tic_set": _tic_set,
    "r323_ctrl_set": _r323_ctrl_set,
    "pic335201_set": _pic335201_set,
    "lv324501_route_set": _lv324501_route_set,
    "steam_supply_set": _steam_valve(("pic_329204", "op_pct"), "PV-329204"),
    "steam_letdown_set": _steam_valve(("pic_329205", "op_b_pct"), "PV-329205B"),
    "steam_hpvent_set": _steam_valve(("hv_329601", "hic_pct"), "HV-329601"),
    "steam_963_set": _steam_valve(("pic_329207", "legs", "C", "op_pct"), "PV-329207C"),
    "hic329602_set": _steam_valve(("hv_329602_pct",), "HV-329602"),
    "pic329204_set": _pic329204_set,
    "pic329205_set": _pic329205_set,
    "lic329502_set": _level_set("LIC-329502", (D005, "m_d005_kg")),
    "lic329503_set": _level_set("LIC-329503", (D009, "m_d009_kg")),
    "lic329504_set": _level_set("LIC-329504", (D001, "m_d001_kg")),
    "pic329207_set": _leg_set("B"),
    "master207_set": _master207_set,
    "pic329207a_set": _leg_set("A"),
    "pic329207b_set": _leg_set("B"),
    "pic329207c_set": _leg_set("C"),
}


def apply_command(plant: PlantState, cmd: Mapping, results: Mapping | None = None) -> CommandResult:
    """Apply one operator command to the plant, between ticks; the answer carries the reason.

    Process utility
    ---------------
    The console's hand on the plant. ``results`` is the last tick's results, for a handler that
    needs what the faceplate showed.
    """
    kind = str(cmd.get("type", ""))
    handler = PLANT_COMMANDS.get(kind)
    if kind == "set" and str(cmd.get("id", "")).lower().endswith("_fault"):
        handler = _fault
    if handler is None:
        if kind in SIMULATOR_COMMANDS:
            return CommandResult(False, f"{kind} is the simulator's control, not the plant's")
        return CommandResult(False, f"unknown command {kind!r}")
    try:
        text = handler(plant, cmd, results or {})
    except _Refused as exc:
        return CommandResult(False, str(exc))
    return CommandResult(True, "", text)
