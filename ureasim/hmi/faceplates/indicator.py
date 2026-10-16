"""The indicator faceplate: any bound value with no control of its own, read-only.

What it shows
-------------
V1's indicator faceplate: the value, its unit and the packet path it comes from, live while open;
clicking the value shows three decimals, which is the point of opening it. A pressure is shown in
gauge pressure. Every bound indicator, bargraph and valve opening without a faceplate of its own
opens this, so a left-click always opens something.

Source: V1 ``frontend/app.js`` 782-830 and ``index.html`` (``#indicatorModal``).
"""

from __future__ import annotations

from typing import Any, Mapping

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QLineEdit, QWidget

from ureasim.hmi.faceplates.base import Faceplate, ValueField
from ureasim.hmi.state_access import NO_DATA, format_value, get_path, to_display_units

__all__ = ["IndicatorFaceplate"]


class IndicatorFaceplate(Faceplate):
    """One indicator, read-only."""

    def __init__(self, bridge: QObject, element: Mapping[str, Any],
                 parent: QWidget | None = None) -> None:
        super().__init__(bridge, str(element.get("tag", "")), parent)
        self.bind = str(element.get("bind", "") or "")
        self.unit = str(element.get("u", "") or "")
        self.decimals = element.get("dec", 1)
        self.value_field = self.add_row("Value", ValueField(self))
        self.unit_field = self.add_row("Units", QLineEdit(self))
        self.unit_field.setReadOnly(True)
        source = self.add_row("Source", QLineEdit(self.bind or "unbound", self))
        source.setReadOnly(True)
        self.note.setText(str(element.get("note") or "Click the value to show 3 decimal places."))

    def refresh(self, state: Mapping[str, Any]) -> None:
        raw = get_path(state, self.bind)
        value, unit = to_display_units(raw, self.unit)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            self.value_field.set_value(value, format_value(value, self.decimals))
        else:
            self.value_field.set_value(None, NO_DATA if value is None else str(value))
        self.unit_field.setText(unit or "—")
