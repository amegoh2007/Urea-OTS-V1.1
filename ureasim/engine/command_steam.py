"""The operator's commands on unit 329's steam system, applied to the plant.

What this is
------------
The handlers `engine.command` dispatches for the steam network's hand valves and controllers: a
steam valve's stroke written by hand (PV-329204, PV-329205B, HV-329601, PV-329207C, HV-329602),
PIC-329204, PIC-329205's split range, the drum levels LIC-329502 / 503 / 504 taken bumplessly
into AUTO, MASTER-329207 and the three legs of the PIC-329207 trio. Each is accepted or refused
with its process reason, as every command is (`engine.command`).

Moved out of `engine.command` unchanged (2026-10-23, the housekeeping split); `engine.command`
builds its dispatch table on these handlers.

Source: V1 ``backend/main.py`` ``handle_cmd`` (11413-11787), the unit-329 commands.
"""

from __future__ import annotations

from typing import Callable, Mapping

from ureasim.data.operator_commands import STEAM_SP_MAX_BARA
from ureasim.engine.command_payload import _Refused, _clamp, _needs, _num
from ureasim.engine.state import PlantState


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
