"""The pump faceplate: START / STOP, one live button.

What it shows and sends
-----------------------
No pump starts or stops on a click of its symbol: the click opens this, and the command is issued
from here (V1). Exactly one button is live — START while the pump is stopped, STOP while it runs —
and the other is dead, so the operator cannot command the state the plant is already in; the
buttons send an explicit ``on`` rather than a toggle, so a faceplate a packet behind the engine
cannot invert the intent. For the feed pumps the interlock line reads the synthesis trips that
hold the pump: a trip whose cause is live blocks the start, a latch whose cause has recovered is
acknowledged by the START itself (the engine does it; this only says so).

Which command the buttons send is the pump's row in `ureasim.data.faceplates.PUMP_COMMANDS`: the
feed and tempered-water pumps V1's faceplate drove, and the auxiliary pairs whose run state the
engine holds (decision 222). No AUTO / MAN is shown or sent, as in V1.

Source: V1 ``frontend/app.js`` 554-598 and ``index.html`` (``#pumpModal``).
"""

from __future__ import annotations

from typing import Any, Mapping

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QLineEdit, QWidget

from ureasim.data.faceplates import PUMP_COMMANDS, PUMP_TRIPS
from ureasim.data.unit_322_loop import trip_label
from ureasim.hmi.faceplates.base import Faceplate
from ureasim.hmi.state_access import get_path

__all__ = ["PumpFaceplate", "interlock_text"]


def interlock_text(state: Mapping[str, Any], pump_id: str) -> str:
    """What holds a feed pump, as V1's faceplate words it; ``n/a`` for a pump with no trips. AC4's
    flags read the trip in both ``trips`` and ``trip_latched`` and hold no latch of their own, so
    V1's "LATCHED (clears on START)", trip 22.2's, has no trip left to show (decision 189)."""
    keys = PUMP_TRIPS.get(pump_id)
    if keys is None:
        return "n/a"
    latched = get_path(state, "trip_latched") or {}
    live = get_path(state, "trips") or {}
    active = [k for k in keys if latched.get(k) and live.get(k)]
    if active:
        return "TRIP " + ", ".join(trip_label(k) for k in active) + " ACTIVE"
    return "CLEAR"


class PumpFaceplate(Faceplate):
    """A pump whose run state the engine holds: 321P002A / B, 329P006A / B, and the auxiliary
    pairs 322P002A / B, 323P001A / B and 328P003A / B."""

    def __init__(self, bridge: QObject, element: Mapping[str, Any],
                 parent: QWidget | None = None) -> None:
        tag = str(element.get("tag", element.get("id", "PUMP")))
        super().__init__(bridge, tag, parent)
        self.pump_id, self.bind = str(element["id"]), str(element["bind"])
        self.command_type = PUMP_COMMANDS[tag]
        tag_field = self.add_row("Pump", QLineEdit(tag, self))
        tag_field.setReadOnly(True)
        self.status_field = self.add_row("Status", QLineEdit(self))
        self.status_field.setReadOnly(True)
        self.interlock_field = self.add_row("Interlock", QLineEdit(self))
        self.interlock_field.setReadOnly(True)
        self.interlock_field.setMinimumWidth(220)
        self.stop_button = self.add_button("STOP", lambda: self.command(False))
        self.start_button = self.add_button("START", lambda: self.command(True))

    def refresh(self, state: Mapping[str, Any]) -> None:
        on = bool(get_path(state, f"{self.bind}.on"))
        # The buttons follow the run command where the engine publishes one apart from the
        # feedback (PUMPS: an AC4 stop holds the pair with its command on), else the run state.
        cmd = get_path(state, f"{self.bind}.cmd")
        cmd = on if cmd is None else bool(cmd)
        self.status_field.setText("RUNNING" if on else "STOPPED (INTERLOCK)" if cmd else "STOPPED")
        self.interlock_field.setText(interlock_text(state, self.pump_id))
        self.start_button.setEnabled(not cmd)
        self.stop_button.setEnabled(cmd)
        self.mark(self.start_button, not cmd, "primary")
        self.mark(self.stop_button, cmd, "primary")

    def command(self, on: bool) -> None:
        self.send({"type": self.command_type, "id": self.pump_id, "on": on})
