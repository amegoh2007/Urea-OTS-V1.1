"""The instructor's panel — running the exercise, never the plant.

What it is
----------
A window on the console with the controls that are not plant equipment, kept off the process
screens so they stay true to the DCS (`project.md` decision 149):

* **Simulation** — the pacing, x1 to x10 in steps of one (`ureasim.data.engine.SIM_SPEED`,
  decision 321), FREEZE and RUN, and RESET to the design seed after a confirmation; the pacing the
  plant runs at, and FREEZE or RUN as the plant clock is held or running (the packet's
  ``sim_frozen``), are lit;
* **Malfunctions** — every equipment fault the engine can inject, armed and cleared
  (`ureasim.data.faceplates.MALFUNCTIONS`);
* **Boundary** — the CO2 asked of 320K002 (``co2_set``), the battery-limit rate: a boundary
  condition outside the simulated plant (decision 73), which 322-1's CO2 FEED panel also steps
  (decision 220), offered from none to V1's 120 % of the design feed
  (`ureasim.data.faceplates.CO2_DEMAND_MAX_FRAC`);
* **Field** — 322P002's delivery to the LP absorber, which the plant's field operator sets by
  hand and reads on FI-322402 (decision 212): no DCS move exists, so it is the instructor's, from
  none to the indicator's range (`ureasim.data.faceplates.P002_DELIVERY_MAX_M3H`, decision 234);
* **Exercises** — save the plant under a name with a note, and restore a saved one after a
  confirmation, from the list the engine's side holds.

Like a faceplate it is a dumb renderer and an emitter: the pacing, the freeze, the CO2 demand and
322P002's delivery it shows are the packet's, the exercises the engine's list, and every button sends one command whose answer —
the engine's — is shown with its reason.

Source: V1 ``frontend/app.js`` (the reset button, 120-160) and ``frontend/co2_compressor.js`` (the
CO2 demand's range); the rest is the port's (`project.md` §3.5).
"""

from __future__ import annotations

from typing import Any, Mapping

from PyQt6.QtCore import QObject, Qt
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ureasim.data.engine import SIM_SPEED
from ureasim.data.faceplates import (
    CO2_DEMAND_MAX_FRAC,
    MALFUNCTIONS,
    P002_DELIVERY_COMMAND,
    P002_DELIVERY_DES_M3H,
    P002_DELIVERY_MAX_M3H,
)
from ureasim.data.unit_321 import CO2_DES_KGH
from ureasim.hmi import theme
from ureasim.hmi.faceplates.base import faceplate_style
from ureasim.hmi.state_access import get_path

__all__ = ["InstructorPanel"]


class InstructorPanel(QWidget):
    """The instructor's exercise controls, attached to the console's bridge."""

    def __init__(self, bridge: QObject, parent: QWidget | None = None,
                 confirm=None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.bridge = bridge
        #: Asks the instructor to confirm a step that discards the running plant; a test hands
        #: in its own answer.
        self.confirm = confirm or self._ask
        self._pending: dict[int, str] = {}
        self.setWindowTitle("Instructor")
        self.setStyleSheet(faceplate_style())
        column = QVBoxLayout(self)
        column.addWidget(self._simulation())
        column.addWidget(self._malfunctions())
        column.addWidget(self._boundary())
        column.addWidget(self._field())
        column.addWidget(self._exercises())
        self.message = QLabel("", self)
        self.message.setWordWrap(True)
        column.addWidget(self.message)

        bridge.snapshot.connect(self.refresh)
        bridge.command_result.connect(self._on_result)
        bridge.exercises_received.connect(self.show_exercises)

    # ---- building ----

    def _button(self, text: str, slot, parent: QWidget) -> QPushButton:
        b = QPushButton(text, parent)
        b.setAutoDefault(False)
        b.clicked.connect(lambda _c=False: slot())
        return b

    def _simulation(self) -> QGroupBox:
        box = QGroupBox("Simulation", self)
        column = QVBoxLayout(box)
        speeds = QHBoxLayout()
        speeds.addWidget(QLabel("Speed", box))
        self.pacing_buttons = {}
        for mode in SIM_SPEED:
            b = self._button(mode, lambda m=mode: self.pacing(m), box)
            self.pacing_buttons[mode] = b
            speeds.addWidget(b)
        speeds.addStretch(1)
        column.addLayout(speeds)
        clock = QHBoxLayout()
        self.freeze_button = self._button("FREEZE", lambda: self.freeze(True), box)
        self.run_button = self._button("RUN", lambda: self.freeze(False), box)
        clock.addWidget(self.freeze_button)
        clock.addWidget(self.run_button)
        clock.addSpacing(12)
        clock.addWidget(self._button("RESET", self.reset, box))
        clock.addStretch(1)
        column.addLayout(clock)
        return box

    def _malfunctions(self) -> QGroupBox:
        box = QGroupBox("Malfunctions", self)
        grid = QGridLayout(box)
        self.fault_rates: dict[str, QDoubleSpinBox] = {}
        for r, m in enumerate(MALFUNCTIONS):
            grid.addWidget(QLabel(m.label, box), r, 0)
            if m.rate_unit is not None:
                rate = QDoubleSpinBox(box)
                rate.setRange(0.0, 1000.0)
                rate.setDecimals(1)
                rate.setSuffix(f" {m.rate_unit}")
                rate.setValue(m.rate_default)
                self.fault_rates[m.fault_id] = rate
                grid.addWidget(rate, r, 1)
            grid.addWidget(self._button("TRIGGER", lambda f=m: self.fault(f.fault_id, True), box),
                           r, 2)
            grid.addWidget(self._button("CLEAR", lambda f=m: self.fault(f.fault_id, False), box),
                           r, 3)
        return box

    def _boundary(self) -> QGroupBox:
        box = QGroupBox("Boundary", self)
        row = QHBoxLayout(box)
        row.addWidget(QLabel("320K002 CO2 demand", box))
        self.co2_demand = QDoubleSpinBox(box)
        self.co2_demand.setRange(0.0, CO2_DES_KGH / 1000.0 * CO2_DEMAND_MAX_FRAC)
        self.co2_demand.setDecimals(3)
        self.co2_demand.setSuffix(" t/h")
        self.co2_demand.setValue(CO2_DES_KGH / 1000.0)
        row.addWidget(self.co2_demand)
        row.addWidget(self._button("SET", self.co2, box))
        self.co2_now = QLabel("", box)
        row.addWidget(self.co2_now)
        row.addStretch(1)
        return box

    def _field(self) -> QGroupBox:
        box = QGroupBox("Field", self)
        row = QHBoxLayout(box)
        row.addWidget(QLabel("322P002 delivery, hand valve (FI-322402)", box))
        self.p002_delivery = QDoubleSpinBox(box)
        # Four places hold the start value to PFD 744 within 0.01 kg/h (two would send 31.32
        # m3/h, 1.4 kg/h short of it).
        self.p002_delivery.setDecimals(4)
        self.p002_delivery.setRange(0.0, P002_DELIVERY_MAX_M3H)
        self.p002_delivery.setSuffix(" m3/h")
        self.p002_delivery.setValue(P002_DELIVERY_DES_M3H)
        row.addWidget(self.p002_delivery)
        row.addWidget(self._button("SET", self.p002, box))
        self.p002_now = QLabel("", box)
        row.addWidget(self.p002_now)
        return box

    def _exercises(self) -> QGroupBox:
        box = QGroupBox("Exercises", self)
        grid = QGridLayout(box)
        self.name_field, self.note_field = QLineEdit(box), QLineEdit(box)
        grid.addWidget(QLabel("Name", box), 0, 0)
        grid.addWidget(self.name_field, 0, 1)
        grid.addWidget(QLabel("Note", box), 1, 0)
        grid.addWidget(self.note_field, 1, 1)
        grid.addWidget(self._button("SAVE", self.save, box), 0, 2)
        self.exercise_list = QListWidget(box)
        grid.addWidget(self.exercise_list, 2, 0, 1, 2)
        side = QVBoxLayout()
        side.addWidget(self._button("REFRESH", self.bridge.request_exercises, box))
        side.addWidget(self._button("RESTORE", self.restore, box))
        side.addStretch(1)
        grid.addLayout(side, 2, 2)
        return box

    # ---- rendering ----

    def refresh(self, state: Mapping[str, Any]) -> None:
        """The pacing the plant runs at, whether its clock is held, the CO2 demand on 320K002 and
        322P002's delivery, from the packet."""
        mode = get_path(state, "sim_mode")
        for m, b in self.pacing_buttons.items():
            self._light(b, m == mode)
        frozen = get_path(state, "sim_frozen")
        self._light(self.freeze_button, frozen is True)
        self._light(self.run_button, frozen is False)
        demand = get_path(state, "CO2_FEED.raw_th")
        self.co2_now.setText("--" if demand is None else f"now {demand:.2f} t/h")
        set_m3h = get_path(state, "ABSORB_328.D003.P002_delivery_set_m3h")
        read_m3h = get_path(state, "ABSORB_328.D003.flow755_m3h")
        self.p002_now.setText("--" if set_m3h is None or read_m3h is None
                              else f"set {set_m3h:.2f}, FI-322402 {read_m3h:.2f} m3/h")

    @staticmethod
    def _light(button: QPushButton, on: bool) -> None:
        """Light a button as the state the packet reports (the faceplates' active style)."""
        button.setProperty("active", on)
        button.style().unpolish(button)
        button.style().polish(button)

    def show_exercises(self, names, reason: str) -> None:
        """The saved exercises."""
        self.exercise_list.clear()
        self.exercise_list.addItems([str(n) for n in names])
        if reason:
            self.say(reason, ok=False)

    # ---- commands ----

    def _send(self, cmd: Mapping[str, Any], what: str) -> int:
        cmd_id = self.bridge.send_command(dict(cmd))
        if not cmd_id:
            self.say("not connected — command not sent", ok=False)
            return 0
        self._pending[cmd_id] = what
        self.say(f"{what}: sent")
        return cmd_id

    def _on_result(self, cmd_id: int, ok: bool, reason: str) -> None:
        what = self._pending.pop(cmd_id, None)
        if what is not None:
            self.say(f"{what}: OK" if ok else f"{what}: REFUSED — {reason}", ok=ok)
            if ok and what.startswith("save"):
                self.bridge.request_exercises()

    def say(self, text: str, ok: bool = True) -> None:
        self.message.setText(text)
        self.message.setStyleSheet(f"color:{theme.FP_MSG_OK if ok else theme.FP_MSG_FAULT};")

    def pacing(self, mode: str) -> None:
        self._send({"type": "set_sim_mode", "mode": mode}, f"pacing {mode}")

    def freeze(self, on: bool) -> None:
        self._send({"type": "freeze", "on": on}, "freeze" if on else "run")

    def reset(self) -> None:
        if self.confirm("Reset the simulation?",
                        "The plant returns to its design seed and the trends restart."):
            self._send({"type": "reset_sim"}, "reset")

    def fault(self, fault_id: str, on: bool) -> None:
        kind = "trigger_fault" if on else "clear_fault"
        cmd = {"type": kind, "id": fault_id}
        if on and fault_id in self.fault_rates:
            cmd["rate"] = self.fault_rates[fault_id].value()
        self._send(cmd, f"{kind} {fault_id}")

    def co2(self) -> None:
        value = self.co2_demand.value()
        self._send({"type": "co2_set", "value": value}, f"CO2 demand {value:g} t/h")

    def p002(self) -> None:
        value = self.p002_delivery.value()
        self._send({"type": P002_DELIVERY_COMMAND, "value": value},
                   f"322P002 delivery {value:g} m3/h")

    def save(self) -> None:
        name = self.name_field.text().strip()
        self._send({"type": "snapshot_save", "name": name, "note": self.note_field.text()},
                   f"save {name}")

    def restore(self) -> None:
        item = self.exercise_list.currentItem()
        if item is None:
            self.say("choose an exercise to restore", ok=False)
            return
        name = item.text()
        if self.confirm(f"Restore {name}?", "The running plant is replaced by the saved one."):
            self._send({"type": "snapshot_load", "name": name}, f"restore {name}")

    def _ask(self, title: str, text: str) -> bool:
        answer = QMessageBox.question(self, title, text, QMessageBox.StandardButton.Yes
                                      | QMessageBox.StandardButton.No)
        return answer == QMessageBox.StandardButton.Yes
