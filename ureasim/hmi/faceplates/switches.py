"""The switch faceplates: a block valve and its hand switch, HS-322915's keyswitch, LV-324501's route.

What they show and send
-----------------------
* **A block valve or its hand switch** (XV-321901, -322901, -322902, -322903 and their HS): the
  valve's state and one button, OPEN while it is shut and CLOSE while it is open, which sends V1's
  ``xv_toggle``. V1 toggled a valve on a click of its symbol; here the symbol opens the faceplate,
  as V1's hand switches did, so a stray click moves nothing. A valve with no operator command —
  XV-322915, which I 22.1 opens and HS-322915 alone overrides (decision 40) — opens it read-only.
* **A maintained keyswitch**: HS-322915, XV-322915's OVERRIDE CLOSE, beside the valve's state and I
  22.1's live limit; and trip 21.2's five (decision 98) — HS-321634, HS-323604 and HS-322606, its
  start-up bypasses, HS-321603 and HS-321604, its trip switches — beside the key's position, which
  the packet's ``HAND_SWITCHES`` carries, and 21.2's flag. TURN and RELEASE, each an explicit
  ``keyswitch_set``; both are offered and either is idempotent.
* **LV-324501's route** (V1's retired switch, kept as V1 kept it): ROUTE A and ROUTE B, each a
  ``lv324501_route_set``.

Source: V1 ``frontend/app.js`` 600-625 and ``overlays.js`` ``activate`` (723-778),
``lv324501_route.js``; the overlay's decided edits (`tools/convert_overlays.py`, B-59).
"""

from __future__ import annotations

from typing import Any, Mapping

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QLineEdit, QWidget

from ureasim.hmi.faceplates.base import Faceplate
from ureasim.hmi.state_access import get_path

__all__ = ["BlockValveFaceplate", "KeyswitchFaceplate", "RouteFaceplate"]

#: LV-324501's two routes and their captions. Source: V1 ``lv324501_route.js``.
ROUTES = (("A", "A - FORWARD: mixed Stream 609 (402G + UF85) to Unit 335"),
          ("B", "B - RECYCLE: raw Stream 402G to 323D002; UF85 OFF"))


def _readonly(face: Faceplate, label: str, text: str = "") -> QLineEdit:
    field = face.add_row(label, QLineEdit(text, face))
    field.setReadOnly(True)
    return field


class BlockValveFaceplate(Faceplate):
    """A block valve, from its symbol or its hand switch."""

    def __init__(self, bridge: QObject, element: Mapping[str, Any],
                 parent: QWidget | None = None) -> None:
        super().__init__(bridge, str(element.get("tag", "")), parent)
        self.state_path = str(element.get("xv") or element.get("bind") or "")
        self.cmd_id = element.get("cmd")
        valve = self.state_path.rsplit(".", 1)[-1].replace("_", "-")
        _readonly(self, "Valve", valve)
        self.status_field = _readonly(self, "Status")
        self.toggle = self.add_button("OPEN", self.apply, primary=True)
        if self.cmd_id is None:
            self.toggle.setEnabled(False)
            self.note.setText(f"{valve} takes no operator command on the DCS.")

    def refresh(self, state: Mapping[str, Any]) -> None:
        is_open = get_path(state, self.state_path)
        self.status_field.setText("--" if is_open is None else ("OPEN" if is_open else "CLOSED"))
        self.toggle.setText("CLOSE" if is_open else "OPEN")

    def apply(self) -> None:
        if self.cmd_id is not None:
            self.send({"type": "xv_toggle", "id": str(self.cmd_id)})


class KeyswitchFaceplate(Faceplate):
    """A maintained keyswitch: HS-322915 over XV-322915, or one of trip 21.2's five."""

    def __init__(self, bridge: QObject, element: Mapping[str, Any],
                 parent: QWidget | None = None) -> None:
        super().__init__(bridge, str(element.get("tag", "")), parent)
        self.switch = str(element.get("cmd", ""))
        self.xv_path, self.latch = str(element.get("xv", "")), str(element.get("latch", ""))
        # What the key acts on: XV-322915, or, on a trip 21.2 switch, the key itself.
        self.is_key = self.xv_path.startswith("HAND_SWITCHES.")
        self.valve_field = _readonly(
            self, self.xv_path.rsplit(".", 1)[-1].replace("_", "-") if self.xv_path else "")
        self.limit_field = _readonly(self, f"I {self.latch.replace('_', '.')}")
        self.note.setText(str(element.get("note", "")))
        self.add_button("RELEASE", lambda: self.turn(False))
        self.add_button("TURN", lambda: self.turn(True))

    def refresh(self, state: Mapping[str, Any]) -> None:
        on = get_path(state, self.xv_path)
        words = ("TURNED", "RELEASED") if self.is_key else ("OPEN", "CLOSED")
        self.valve_field.setText("--" if on is None else words[0 if on else 1])
        live = get_path(state, f"trips.{self.latch}")
        # I 22.1 is a limit; trip 21.2's flag is lost while its inputs are.
        words = ("OVER LIMIT", "NORMAL") if self.latch == "22_1" else ("FLAG LOST", "HEALTHY")
        self.limit_field.setText("--" if live is None else words[0 if live else 1])

    def turn(self, on: bool) -> None:
        self.send({"type": "keyswitch_set", "id": self.switch, "on": on})


class RouteFaceplate(Faceplate):
    """LV-324501's route switch."""

    def __init__(self, bridge: QObject, element: Mapping[str, Any],
                 parent: QWidget | None = None) -> None:
        super().__init__(bridge, "LV-324501 ROUTE", parent)
        self.fields = {}
        for route, caption in ROUTES:
            self.fields[route] = _readonly(self, f"LV-324501{route} (%)")
            self.add_button(f"ROUTE {route}", lambda r=route: self.route(r))
        self.note.setText("\n".join(caption for _, caption in ROUTES))

    def refresh(self, state: Mapping[str, Any]) -> None:
        for route, field in self.fields.items():
            v = get_path(state, f"EVAP_324.E003.LV_324501{route}")
            field.setText("--" if v is None else f"{float(v):.1f}")

    def route(self, route: str) -> None:
        self.send({"type": "lv324501_route_set", "route": route})
