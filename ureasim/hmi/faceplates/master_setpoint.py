"""The MASTER SP faceplate: the 4-bar steam header's ON / OFF cascade over PIC-329207A / B / C.

What it shows and sends
-----------------------
V1's faceplate. ON: one master set point fans out to the three legs and locks them (A at SP + 0.1
venting, B at SP on the turbine, C at SP - 0.1 admitting from the battery limit), and only the
master set point is editable. OFF: the three legs are independent, each with its set point, its
mode and, in MAN, its output. ON and OFF are sent at once (``master207_set``), as are a leg's
mode buttons; SET sends the master set point when ON and each leg's set point (and output in MAN)
when OFF. Pressures are shown in bar g and sent in bar a.

Source: V1 ``frontend/app.js`` 1167-1282 and ``index.html`` (``#mspModal``).
"""

from __future__ import annotations

from typing import Any, Mapping

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget

from ureasim.data.faceplates import MASTER_SP_LEGS
from ureasim.hmi import theme
from ureasim.hmi.faceplates.base import Faceplate, ValueField
from ureasim.hmi.state_access import ATM_BAR, format_value, get_path

__all__ = ["MasterSetpointFaceplate"]

_ON_NOTE = ("MASTER ON: A=SP+0.1 (vent) / B=SP (turbine) / C=SP-0.1 (BL admit) — "
            "locked to AUTO.")
_OFF_NOTE = "MASTER OFF: PIC-329207A/B/C independent — set each SP / mode (OP in MAN)."


def _gauge(v: Any) -> Any:
    return v - ATM_BAR if isinstance(v, (int, float)) and not isinstance(v, bool) else v


class MasterSetpointFaceplate(Faceplate):
    """PIC-329207's master and its three legs."""

    def __init__(self, bridge: QObject, parent: QWidget | None = None) -> None:
        super().__init__(bridge, "MASTER SP — 4-bar STEAM HEADER (PIC-329207)", parent)
        self.pv_field = self.add_row("Header PV (barg)", ValueField(self))
        self.sp_field = self.add_entry("MASTER SP (barg)")
        cascade = QWidget(self)
        row = QHBoxLayout(cascade)
        row.setContentsMargins(0, 0, 0, 0)
        self.on_button = QPushButton("ON", cascade)
        self.off_button = QPushButton("OFF", cascade)
        for b, on in ((self.on_button, True), (self.off_button, False)):
            b.setAutoDefault(False)
            b.clicked.connect(lambda _c=False, v=on: self.cascade(v))
            row.addWidget(b)
        row.addStretch(1)
        self.add_row("Cascade", cascade)

        table = QWidget(self)
        grid = QGridLayout(table)
        grid.setContentsMargins(0, 0, 0, 0)
        for c, head in enumerate(("Sub-controller", "SP (barg)", "OP (%)", "Mode")):
            grid.addWidget(QLabel(head, table), 0, c)
        self.legs: dict[str, dict] = {}
        for r, (leg, key, command, caption) in enumerate(MASTER_SP_LEGS, start=1):
            name = QLabel(f"PIC-329207{leg}<br><span style='color:{theme.FP_CAPTION_TEXT}'>"
                          f"{caption}</span>", table)
            sp, op = QLineEdit(table), QLineEdit(table)
            modes = QWidget(table)
            mrow = QHBoxLayout(modes)
            mrow.setContentsMargins(0, 0, 0, 0)
            buttons = {}
            for mode in ("AUTO", "MAN"):
                b = QPushButton(mode, modes)
                b.setAutoDefault(False)
                b.clicked.connect(lambda _c=False, lg=leg, m=mode: self.leg_mode(lg, m))
                mrow.addWidget(b)
                buttons[mode] = b
            for c, w in enumerate((name, sp, op, modes)):
                grid.addWidget(w, r, c)
            self.legs[leg] = {"key": key, "command": command, "sp": sp, "op": op,
                              "buttons": buttons, "mode": "AUTO"}
        self.rows.addWidget(table, self.rows.rowCount(), 0, 1, 2)
        self.note.setStyleSheet(f"color:{theme.FP_CAS_NOTE_TEXT}; font-size:11px;")
        self.add_button("SET", self.apply, primary=True)
        self.master_on = False

    def refresh(self, state: Mapping[str, Any]) -> None:
        ss = get_path(state, "STEAM_SYSTEM")
        if not isinstance(ss, Mapping):
            self.say("waiting for telemetry…", ok=False)
            return
        m = ss.get("MASTER_SP_329207") or {}
        self.master_on = bool(m.get("on"))
        self.pv_field.set_value(_gauge(m.get("pv")), format_value(_gauge(m.get("pv")), 2))
        self.put(self.sp_field, format_value(_gauge(m.get("sp")), 2))
        for leg in self.legs.values():
            d = ss.get(leg["key"]) or {}
            leg["mode"] = str(d.get("mode") or leg["mode"])
            self.put(leg["sp"], format_value(_gauge(d.get("sp")), 2))
            self.put(leg["op"], format_value(d.get("op")))
        self._gate()

    def _gate(self) -> None:
        on = self.master_on
        self.set_mode_chip("ON" if on else "OFF")
        self.mark(self.on_button, on)
        self.mark(self.off_button, not on)
        self.sp_field.setEnabled(on)
        for leg in self.legs.values():
            man = leg["mode"] == "MAN"
            leg["sp"].setEnabled(not on)
            leg["op"].setEnabled(not on and man)
            for mode, b in leg["buttons"].items():
                b.setEnabled(not on)
                self.mark(b, leg["mode"] == mode)
        self.note.setText(_ON_NOTE if on else _OFF_NOTE)

    def cascade(self, on: bool) -> None:
        self.send({"type": "master207_set", "on": on}, "MASTER ON" if on else "MASTER OFF")

    def leg_mode(self, leg: str, mode: str) -> None:
        if self.master_on:
            return
        self.legs[leg]["mode"] = mode
        self.send({"type": self.legs[leg]["command"], "mode": mode})
        self._gate()

    def apply(self) -> None:
        if self.master_on:
            v = self.number(self.sp_field)
            if v is None:
                self.say("enter a numeric MASTER SP", ok=False)
                return
            self.send({"type": "master207_set", "sp": v + ATM_BAR}, "MASTER SP set")
            return
        sent = 0
        for leg in self.legs.values():
            cmd: dict = {"type": leg["command"]}
            sp = self.number(leg["sp"])
            if sp is not None:
                cmd["sp"] = sp + ATM_BAR
            if leg["mode"] == "MAN":
                op = self.number(leg["op"])
                if op is not None:
                    cmd["op"] = op
            if len(cmd) > 1:
                self.send(cmd, "sub-controllers set")
                sent += 1
        if not sent:
            self.say("nothing to set", ok=False)
