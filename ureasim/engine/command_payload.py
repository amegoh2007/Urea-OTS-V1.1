"""The command handlers' shared helpers: reading a payload, and refusing a command.

What this is
------------
The checks every handler in `engine.command` and `engine.command_steam` makes on V1's command
dictionary before it touches the plant: a finite number clamped to its range, as V1's ``_finite``
and ``clamp``; an explicit start or stop; a field the loop does not use in the mode it is in (V1's
REST rule: a set point needs AUTO, an output MAN, a bias CAS); a synthesis trip by its key. A
refusal is ``_Refused``, its message the reason the operator reads. The names stay private: they
are the two command modules' helpers, not an interface of the engine.

Moved out of `engine.command` unchanged (2026-10-23, the housekeeping split).

Source: V1 ``backend/main.py`` ``handle_cmd`` (11413-11787) and its REST controller handler
(11823-11871).
"""

from __future__ import annotations

import math
from typing import Mapping

from ureasim.data.unit_322_loop import trip_label
from ureasim.engine.state import PlantState


class _Refused(Exception):
    """A command the plant will not take; the message is the reason the operator reads."""


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
    """A synthesis trip as a refusal names it: "trip 21.2"."""
    return "trip " + trip_label(key)


def _needs(cmd: Mapping, mode: str, **fields: str) -> None:
    """Refuse a field the loop does not use in ``mode`` (V1's REST rule: a set point in AUTO, an
    output in MAN, a bias in CAS)."""
    for name, wanted in fields.items():
        if name in cmd and mode != wanted:
            raise _Refused(f"{name!r} is the operator's in {wanted} only; the loop is in {mode}")
