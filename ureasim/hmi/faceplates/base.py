"""The faceplate window every control on a process screen opens.

What a faceplate is
-------------------
A small non-modal window on one instrument, as V1's ``.modal`` cards were: a title with the loop's
live mode, labelled rows, a note, the outcome of the last command, and the buttons. It is a dumb
renderer and a command emitter (`CLAUDE.md` §4a): it shows the packet the engine published,
refreshed on every packet while it is open, and it sends the operator's entry through the bridge as
one of the engine's commands. It computes nothing, keeps nothing between packets, and never decides
whether the plant will take a command — the server answers for the role and the engine for the
process, and the answer is shown here with its reason.

Two V1 behaviours are kept because operators rely on them:

* a field the operator is typing in is not overwritten by the next packet;
* ENTER in a field is the primary button (SET), and closes the faceplate.

A read-only value can be clicked to show three decimals, as V1's ``fpx`` fields did.

Source: V1 ``frontend/index.html`` (``.modal``, 171-199) and ``app.js`` (the faceplates, 183-1282).
"""

from __future__ import annotations

import math
from typing import Any, Mapping

from PyQt6.QtCore import QObject, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ureasim.hmi import theme
from ureasim.hmi.state_access import NO_DATA, format_value

__all__ = ["Faceplate", "ValueField", "faceplate_style"]


def faceplate_style() -> str:
    """The faceplate stylesheet: V1's modal card, its fields and its buttons."""
    return (
        f"QDialog, QWidget#fpCard {{ background:{theme.FP_BG}; color:{theme.FP_TEXT}; "
        f"font-size:{theme.FP_FONT_PX}px; }}"
        f"QLabel {{ color:{theme.FP_TEXT}; }}"
        f"QLineEdit {{ background:{theme.FP_FIELD_BG}; color:{theme.FP_FIELD_TEXT}; "
        f"border:1px solid {theme.FP_BORDER}; padding:3px 6px; "
        f"font-family:{theme.value_font_stack()}; min-width:120px; }}"
        f"QLineEdit[readOnly=\"true\"] {{ background:{theme.FP_READONLY_BG}; "
        f"color:{theme.FP_READONLY_TEXT}; }}"
        f"QLineEdit:disabled {{ background:{theme.FP_READONLY_BG}; color:{theme.FP_DISABLED_TEXT}; "
        f"border-color:{theme.FP_DISABLED_BORDER}; }}"
        f"QPushButton {{ background:{theme.FP_BUTTON_BG}; color:{theme.FP_TEXT}; "
        f"border:1px solid {theme.FP_BUTTON_BORDER}; padding:4px 12px; font-size:12px; }}"
        f"QPushButton[primary=\"true\"] {{ background:{theme.FP_PRIMARY_BG}; }}"
        f"QPushButton[active=\"true\"] {{ background:{theme.FP_PRIMARY_BG}; "
        f"border-color:{theme.FP_ACTIVE_BORDER}; }}"
        f"QPushButton:disabled {{ background:transparent; color:{theme.FP_DEAD_TEXT}; "
        f"border-color:{theme.FP_DEAD_BORDER}; }}"
    )


class ValueField(QLineEdit):
    """A read-only value that shows three decimals while clicked (V1's ``fpx`` field)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self._value: Any = None
        self._shown = NO_DATA
        self._suffix = ""
        self._expanded = False

    def set_value(self, value: Any, shown: str | None = None, suffix: str = "") -> None:
        """Show ``value`` as ``shown`` (its faceplate rounding), or at 3 dp while expanded."""
        self._value, self._suffix = value, suffix
        self._shown = shown if shown is not None else format_value(value)
        self._paint()

    @property
    def expanded(self) -> bool:
        return self._expanded

    def mousePressEvent(self, event) -> None:
        if isinstance(self._value, (int, float)) and not isinstance(self._value, bool):
            self._expanded = not self._expanded
            self._paint()
        super().mousePressEvent(event)

    def _paint(self) -> None:
        number = isinstance(self._value, (int, float)) and not isinstance(self._value, bool)
        if self._expanded and number:
            self.setText(format_value(self._value, 3) + self._suffix)
            self.setStyleSheet(f"color:{theme.FP_EXPANDED_TEXT};")
        else:
            self._expanded = self._expanded and number
            self.setText(self._shown + (self._suffix if self._shown != NO_DATA else ""))
            self.setStyleSheet("")


class Faceplate(QDialog):
    """One instrument's faceplate, attached to the console's bridge.

    ``bridge`` is the console's `EngineBridge` (or anything with its ``snapshot`` and
    ``command_result`` signals, ``latest`` and ``send_command``). Subclasses build their rows in
    ``__init__`` and render a packet in `refresh`.
    """

    def __init__(self, bridge: QObject, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.bridge = bridge
        self._pending: set[int] = set()
        self.setWindowTitle(title)
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setStyleSheet(faceplate_style())

        column = QVBoxLayout(self)
        column.setContentsMargins(14, 14, 14, 14)
        header = QHBoxLayout()
        self.title_label = QLabel(title, self)
        font = QFont()
        font.setPixelSize(theme.FP_TITLE_PX)
        font.setBold(True)
        self.title_label.setFont(font)
        self.mode_chip = QLabel("", self)
        chip_font = QFont(font)
        chip_font.setFamilies(theme.VALUE_FONT_FAMILIES)
        self.mode_chip.setFont(chip_font)
        header.addWidget(self.title_label)
        header.addWidget(self.mode_chip)
        header.addStretch(1)
        column.addLayout(header)

        self.rows = QGridLayout()
        self.rows.setHorizontalSpacing(10)
        column.addLayout(self.rows)

        self.note = QLabel("", self)
        self.note.setWordWrap(True)
        self.note.setStyleSheet(f"color:{theme.FP_NOTE_TEXT}; font-size:11px;")
        column.addWidget(self.note)
        self.status = QLabel("", self)
        self.status.setStyleSheet(f"color:{theme.FP_STATUS_TEXT}; font-size:11px;")
        column.addWidget(self.status)
        self.message = QLabel("", self)
        self.message.setWordWrap(True)
        column.addWidget(self.message)

        self.buttons = QHBoxLayout()
        self.buttons.addStretch(1)
        column.addLayout(self.buttons)
        self.primary: QPushButton | None = None
        self.close_button = self.add_button("Close", self.close)

        bridge.snapshot.connect(self._on_snapshot)
        bridge.command_result.connect(self._on_result)

    # ---- building ----

    def add_row(self, label: str, widget: QWidget) -> QWidget:
        """A labelled row."""
        r = self.rows.rowCount()
        self.rows.addWidget(QLabel(label, self), r, 0)
        self.rows.addWidget(widget, r, 1)
        return widget

    def add_entry(self, label: str) -> QLineEdit:
        """A row the operator types a number in."""
        return self.add_row(label, QLineEdit(self))

    def add_value(self, label: str) -> ValueField:
        """A read-only row."""
        return self.add_row(label, ValueField(self))

    def add_button(self, text: str, slot, primary: bool = False) -> QPushButton:
        """A button on the bottom row; the primary one answers ENTER."""
        button = QPushButton(text, self)
        button.setAutoDefault(False)
        button.clicked.connect(lambda _checked=False: slot())
        if primary:
            button.setProperty("primary", True)
            self.primary = button
        self.buttons.addWidget(button)
        return button

    @staticmethod
    def mark(button: QPushButton, on: bool, prop: str = "active") -> None:
        """Set a button's styled flag (the active mode, the live primary)."""
        button.setProperty(prop, on)
        button.style().unpolish(button)
        button.style().polish(button)

    def set_mode_chip(self, mode: str | None) -> None:
        """The loop's live mode on the title, coloured as V1 colours it."""
        text = str(mode or "")
        self.mode_chip.setText(text)
        colour = theme.FP_MODE_COLOURS.get(text.upper(), theme.FP_TEXT)
        self.mode_chip.setStyleSheet(f"color:{colour};")

    @staticmethod
    def put(field: QLineEdit, text: str) -> None:
        """Write a field unless the operator is typing in it (V1's focus rule)."""
        if not field.hasFocus():
            field.setText(text)

    @staticmethod
    def number(field: QLineEdit) -> float | None:
        """The finite number typed in a field, or None: NaN and infinity cannot cross the bridge."""
        try:
            v = float(field.text().strip())
        except ValueError:
            return None
        return v if math.isfinite(v) else None

    # ---- commands ----

    def send(self, cmd: Mapping[str, Any], sent: str = "sent") -> int:
        """Send a command; its answer arrives on the bridge and is shown here."""
        cmd_id = self.bridge.send_command(dict(cmd))
        if not cmd_id:
            self.say("not connected — command not sent", ok=False)
            return 0
        self._pending.add(cmd_id)
        self.say(sent, ok=True)
        return cmd_id

    def say(self, text: str, ok: bool = True) -> None:
        self.message.setText(text)
        self.message.setStyleSheet(
            f"color:{theme.FP_MSG_OK if ok else theme.FP_MSG_FAULT}; font-size:11px;")

    def _on_result(self, cmd_id: int, ok: bool, reason: str) -> None:
        if cmd_id in self._pending:
            self._pending.discard(cmd_id)
            self.say("OK" if ok else f"REFUSED: {reason}", ok=ok)

    # ---- rendering ----

    def _on_snapshot(self, state: Mapping[str, Any]) -> None:
        if self.isVisible():
            self.refresh(state)

    def showEvent(self, event) -> None:
        self.refresh(self.bridge.latest)
        super().showEvent(event)

    def refresh(self, state: Mapping[str, Any]) -> None:
        """Render the packet. Overridden by every faceplate."""

    def keyPressEvent(self, event) -> None:
        """ENTER is the primary button, and closes the faceplate (V1)."""
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.primary is not None and self.primary.isEnabled():
                self.primary.click()
                self.close()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        for signal, slot in ((self.bridge.snapshot, self._on_snapshot),
                             (self.bridge.command_result, self._on_result)):
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        super().closeEvent(event)
