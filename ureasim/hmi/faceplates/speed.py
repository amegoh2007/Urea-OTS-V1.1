"""The feed pumps' speed faceplates: SIC-321950 (321P002A) and SIC-321951 (321P002B).

What it shows and sends
-----------------------
V1's two SIC faceplates: the speed PV, SP and MV, the mode (MAN, AUTO, CAS, OOS) and the ratio
master over the pump, FFIC-321404A or B, whose set point is the loop's N/C target. A mode button
sends the mode at once (V1 posted it to its REST controller); SET sends the value the live mode
uses — the output in MAN, the set point in AUTO, and in CAS the master's set point, the same
``ratio_set`` as the home screen's N/C field, because in CAS the speed controller does not own its
set point. A stopped pump is held in MAN by the engine, so only MAN is offered while it is stopped.
The status line carries the loop's flags as the packet publishes them.

Source: V1 ``frontend/app.js`` 861-1165 and ``index.html`` (``#f50``, ``#f51``).
"""

from __future__ import annotations

from typing import Any, Mapping

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from ureasim.data.faceplates import SPEED_CONTROLLERS
from ureasim.hmi.faceplates.base import Faceplate
from ureasim.hmi.state_access import format_value, get_path

__all__ = ["SpeedFaceplate"]


class SpeedFaceplate(Faceplate):
    """SIC-321950 or SIC-321951."""

    MODES = ("MAN", "AUTO", "CAS", "OOS")

    def __init__(self, bridge: QObject, controller: str, parent: QWidget | None = None) -> None:
        sc = SPEED_CONTROLLERS[controller]
        super().__init__(bridge, f"{controller.replace('_', '-')} — {sc.pump} SPEED", parent)
        self.controller, self.spec = controller, sc
        self.pv_field = self.add_value("PV (%)")
        self.sp_field = self.add_entry("SP (%)")
        self.mv_field = self.add_entry("MV (%)")
        self.fsp_field = self.add_entry(f"{sc.master} SP")
        self.fpv_field = self.add_value(f"{sc.master} PV")
        group = QWidget(self)
        row = QHBoxLayout(group)
        row.setContentsMargins(0, 0, 0, 0)
        self.mode_buttons: dict[str, QPushButton] = {}
        for mode in self.MODES:
            b = QPushButton(mode, group)
            b.setAutoDefault(False)
            b.clicked.connect(lambda _c=False, m=mode: self.send_mode(m))
            row.addWidget(b)
            self.mode_buttons[mode] = b
        row.addStretch(1)
        self.add_row("Mode", group)
        self.set_button = self.add_button("SET", self.apply, primary=True)
        self.mode = "MAN"

    def refresh(self, state: Mapping[str, Any]) -> None:
        d = get_path(state, f"controllers.{self.controller}")
        if not isinstance(d, Mapping):
            self.say("waiting for controller data…", ok=False)
            return
        running = bool(get_path(state, f"{self.spec.pump_bind}.on"))
        self.mode = str(d.get("mode", "MAN")).upper()
        self.set_mode_chip(self.mode)
        for m, b in self.mode_buttons.items():
            self.mark(b, m == self.mode)
            b.setEnabled(running or m == "MAN")
        self.sp_field.setEnabled(self.mode == "AUTO")
        self.mv_field.setEnabled(self.mode == "MAN")
        self.fsp_field.setEnabled(self.mode == "CAS")
        self.set_button.setEnabled(self.mode in ("MAN", "AUTO", "CAS"))
        self.pv_field.set_value(d.get("pv"))
        self.put(self.sp_field, format_value(d.get("sp")))
        self.put(self.mv_field, format_value(d.get("mv")))
        ratio = get_path(state, "ratio") or {}
        if ratio.get("SP") is not None:
            self.put(self.fsp_field, format_value(ratio["SP"], 3))
        self.fpv_field.set_value(ratio.get("PV"), format_value(ratio.get("PV"), 3))
        flags = [] if running else ["PUMP STOPPED — MAN"]
        status = d.get("status") or {}
        flags += [text for key, text in (("pv_bad", "PV BAD"), ("mv_hi_clamp", "MV @ HI"),
                                         ("mv_lo_clamp", "MV @ LO")) if status.get(key)]
        self.status.setText("   ".join(flags))

    def send_mode(self, mode: str) -> None:
        """A mode button: the mode, sent at once."""
        self.send({"type": "controller_set", "id": self.controller, "mode": mode})

    def apply(self) -> None:
        """SET: the live mode's value; in CAS, the ratio master's set point."""
        if self.mode == "CAS":
            v = self.number(self.fsp_field)
            if v is None:
                self.say("enter a numeric N/C setpoint", ok=False)
                return
            self.send({"type": "ratio_set", "sp": v}, f"{self.spec.master} SP sent")
            return
        field, key = (self.mv_field, "op") if self.mode == "MAN" else (self.sp_field, "sp")
        v = self.number(field)
        if v is None:
            self.say("enter a numeric value", ok=False)
            return
        self.send({"type": "controller_set", "id": self.controller, "mode": self.mode, key: v})
