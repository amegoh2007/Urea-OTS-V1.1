"""The instructor's panel — running the exercise, never the plant.

What it is
----------
A window on the instructor console with the controls that are not plant equipment
(`ureasim.net.protocol.INSTRUCTOR_ONLY_COMMANDS`):

* **Simulation** — the pacing (SLOW / FAST, `ureasim.data.engine.SIM_SPEED`), FREEZE and RUN,
  and RESET to the design seed after a confirmation;
* **Malfunctions** — every equipment fault the engine can inject, armed and cleared
  (`ureasim.data.faceplates.MALFUNCTIONS`);
* **Exercises** — save the plant under a name with a note, and restore a saved one after a
  confirmation, from the list the server holds;
* **Stations** — the consoles connected, their roles and plant, and the assignment of a trainee
  station's plant sections (`ureasim.data.tags.SECTIONS`), or its release to the whole plant.

Like a faceplate it is a dumb renderer and an emitter: the pacing it shows is the packet's, the
roster and the exercises are the server's lists, and every button sends one command whose answer
— the server's for the role, the engine's for the exercise — is shown with its reason.

Source: V1 ``frontend/app.js`` (the reset button, 120-160); the rest is the multi-station
design's (`project.md` §3.5, handoff A-2).
"""

from __future__ import annotations

from typing import Any, Mapping

from PyQt6.QtCore import QObject, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ureasim.data.engine import SIM_SPEED
from ureasim.data.faceplates import MALFUNCTIONS
from ureasim.data.tags import SECTIONS
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
        column.addWidget(self._exercises())
        column.addWidget(self._stations())
        self.message = QLabel("", self)
        self.message.setWordWrap(True)
        column.addWidget(self.message)

        bridge.snapshot.connect(self.refresh)
        bridge.command_result.connect(self._on_result)
        bridge.roster_changed.connect(self.show_roster)
        bridge.exercises_received.connect(self.show_exercises)

    # ---- building ----

    def _button(self, text: str, slot, parent: QWidget) -> QPushButton:
        b = QPushButton(text, parent)
        b.setAutoDefault(False)
        b.clicked.connect(lambda _c=False: slot())
        return b

    def _simulation(self) -> QGroupBox:
        box = QGroupBox("Simulation", self)
        row = QHBoxLayout(box)
        self.pacing_buttons = {}
        for mode in SIM_SPEED:
            b = self._button(mode, lambda m=mode: self.pacing(m), box)
            self.pacing_buttons[mode] = b
            row.addWidget(b)
        row.addSpacing(12)
        row.addWidget(self._button("FREEZE", lambda: self.freeze(True), box))
        row.addWidget(self._button("RUN", lambda: self.freeze(False), box))
        row.addSpacing(12)
        row.addWidget(self._button("RESET", self.reset, box))
        row.addStretch(1)
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

    def _stations(self) -> QGroupBox:
        box = QGroupBox("Stations", self)
        column = QVBoxLayout(box)
        self.roster_table = QTableWidget(0, 3, box)
        self.roster_table.setHorizontalHeaderLabels(["Station", "Role", "Plant"])
        self.roster_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.roster_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.roster_table.itemSelectionChanged.connect(self._load_assignment)
        column.addWidget(self.roster_table)
        sections = QHBoxLayout()
        self.section_boxes = {}
        for sid, sec in SECTIONS.items():
            cb = QCheckBox(sid, box)
            cb.setToolTip(sec["name"])
            self.section_boxes[sid] = cb
            sections.addWidget(cb)
        sections.addStretch(1)
        column.addLayout(sections)
        actions = QHBoxLayout()
        actions.addWidget(self._button("ASSIGN", self.assign, box))
        actions.addWidget(self._button("WHOLE PLANT", self.release, box))
        actions.addStretch(1)
        column.addLayout(actions)
        self._roster: list[dict] = []
        return box

    # ---- rendering ----

    def refresh(self, state: Mapping[str, Any]) -> None:
        """The pacing the plant runs at, from the packet."""
        mode = get_path(state, "sim_mode")
        for m, b in self.pacing_buttons.items():
            b.setProperty("active", m == mode)
            b.style().unpolish(b)
            b.style().polish(b)

    def show_roster(self, stations) -> None:
        """The server's roster: each station, its role, its plant."""
        self._roster = [dict(s) for s in stations]
        self.roster_table.setRowCount(len(self._roster))
        for r, s in enumerate(self._roster):
            plant = ("whole plant" if s.get("sections") is None
                     else " ".join(s["sections"]) or "none")
            for c, text in enumerate((s.get("station", ""), s.get("role", ""), plant)):
                item = QTableWidgetItem(str(text))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.roster_table.setItem(r, c, item)

    def show_exercises(self, names, reason: str) -> None:
        """The server's saved exercises."""
        self.exercise_list.clear()
        self.exercise_list.addItems([str(n) for n in names])
        if reason:
            self.say(reason, ok=False)

    def _selected_station(self) -> dict | None:
        rows = self.roster_table.selectionModel().selectedRows()
        return self._roster[rows[0].row()] if rows else None

    def _load_assignment(self) -> None:
        s = self._selected_station()
        held = set((s or {}).get("sections") or [])
        for sid, cb in self.section_boxes.items():
            cb.setChecked(sid in held)

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

    def assign(self) -> None:
        s = self._selected_station()
        if s is None:
            self.say("choose a station", ok=False)
            return
        sections = sorted(sid for sid, cb in self.section_boxes.items() if cb.isChecked())
        self._send({"type": "assign", "station": s["station"], "sections": sections},
                   f"assign {s['station']}")

    def release(self) -> None:
        s = self._selected_station()
        if s is None:
            self.say("choose a station", ok=False)
            return
        self._send({"type": "assign", "station": s["station"], "sections": None},
                   f"whole plant to {s['station']}")

    def _ask(self, title: str, text: str) -> bool:
        answer = QMessageBox.question(self, title, text, QMessageBox.StandardButton.Yes
                                      | QMessageBox.StandardButton.No)
        return answer == QMessageBox.StandardButton.Yes
