"""The hand-valve faceplate: one opening, no mode.

What it shows and sends
-----------------------
Every hand station (HIC / HV-322602, -322605, -322604, -329601, -329602, -329605, -329606,
-323605) opens this one faceplate, as in V1: a single entry, prefilled from the valve's live
opening and following it while the operator is not typing, and SET, which sends the station's
command (`ureasim.data.faceplates.HAND_VALVES`). FT-322404's condensate entry (kg/h) and
HIC-322203's minimum opening of PV-322203 share it.

Source: V1 ``frontend/app.js`` 505-552 and 660-672, ``index.html`` (``#hicModal``, ``#hic2Modal``).
"""

from __future__ import annotations

from typing import Any, Mapping

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QWidget

from ureasim.data.faceplates import HAND_VALVES, HandValve
from ureasim.hmi.faceplates.base import Faceplate
from ureasim.hmi.state_access import format_value, get_path

__all__ = ["HandValveFaceplate", "hand_valve_of"]


def hand_valve_of(element: Mapping[str, Any]) -> tuple[str, HandValve] | None:
    """The station an overlay element opens: its own tag, or HIC-322203 for PV-322203's
    minimum-opening route (``face: 'hic2'``)."""
    tag = "HIC-322203" if element.get("face") == "hic2" else str(element.get("tag", ""))
    hv = HAND_VALVES.get(tag)
    return (tag, hv) if hv is not None else None


class HandValveFaceplate(Faceplate):
    """One hand station."""

    def __init__(self, bridge: QObject, element: Mapping[str, Any],
                 parent: QWidget | None = None) -> None:
        tag, hv = hand_valve_of(element)
        super().__init__(bridge, hv.title, parent)
        self.hv = hv
        self.bind = ("CO2_FEED.HIC_322203" if tag == "HIC-322203"
                     else str(element.get("bind", "") or ""))
        label = "Min Opening %" if tag == "HIC-322203" else (
            "Opening %" if hv.unit == "%" else f"Flow ({hv.unit})")
        self.entry = self.add_entry(label)
        self.note.setText(hv.note)
        self.add_button("SET", self.apply, primary=True)

    def refresh(self, state: Mapping[str, Any]) -> None:
        v = get_path(state, self.bind)
        if v is not None:
            self.put(self.entry, format_value(v))

    def apply(self) -> None:
        v = self.number(self.entry)
        if v is None:
            self.say("enter a numeric value", ok=False)
            return
        self.send({"type": self.hv.command, self.hv.field: v})
