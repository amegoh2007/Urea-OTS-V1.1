"""The loop faceplate: PV, SP, output and mode of one controller.

What it shows and sends
-----------------------
V1's generic controller faceplate, and its PIC-322203 sibling: the loop's PV read-only, its set
point and output, MAN / AUTO (and CAS on a cascade slave — one the overlay marks, as in V1, or one
whose modes include it, so FIC-328406's decided cascade is offered). The mode buttons choose the mode the SET
sends; MAN makes the output the operator's, AUTO the set point (clicking AUTO from MAN puts the PV
in the set point field, bumpless, as the engine does), CAS gives the set point to the master, which
the note names. SET sends the loop's command (`ureasim.data.faceplates.loop_command`) with the mode
and the one value that mode uses.

Every value comes from the loop's block in the packet (``{pv, sp, op, mode}``). A loop the packet
carries no block for is not on this model: the faceplate says so and sends nothing, where V1 kept a
private mode, set point and output in the browser (a console owns nothing, `CLAUDE.md` §4a).

A pressure loop is shown in gauge pressure, as every pressure on these screens, and its set point is
sent in absolute pressure, as the engine works.

Source: V1 ``frontend/app.js`` 627-778 and ``index.html`` (``#picModal``, ``#ctlModal``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from ureasim.data.faceplates import CAS_MASTERS, CAS_UNWIRED, loop_command
from ureasim.data.operator_commands import FACEPLATE_MODES
from ureasim.hmi.faceplates.base import Faceplate
from ureasim.hmi.state_access import ATM_BAR, format_value, get_path, to_display_units

__all__ = ["LoopSpec", "loop_spec", "ControllerFaceplate"]


@dataclass(frozen=True)
class LoopSpec:
    """Where a loop's values are in the packet, how they are shown, what SET sends."""

    tag: str
    pv: str | None
    sp: str | None
    op: str | None
    mode: str | None
    unit: str = ""
    command: str | None = None
    cas: bool = False
    note: str = ""


def loop_spec(element: Mapping[str, Any]) -> LoopSpec:
    """The faceplate of an overlay element: a loop block wherever its binding ends in ``.pv``,
    PIC-322203's own fields for its overlay (``face: 'pic'``)."""
    tag = str(element.get("tag", ""))
    unit = str(element.get("u", "") or "")
    note = str(element.get("note", "") or "")
    if element.get("face") == "pic":
        return LoopSpec(tag, "CO2_FEED.PIC_322203", "CO2_FEED.PIC_sp", "CO2_FEED.PIC_op",
                        "CO2_FEED.PIC_mode", unit, loop_command(tag), False, note)
    bind = str(element.get("bind", "") or "")
    # CAS is offered on a cascade slave: the overlay marks it, or the loop's modes include it.
    cas = bool(element.get("cas")) or "CAS" in FACEPLATE_MODES.get(tag, ())
    if bind.endswith(".pv"):
        block = bind[:-3]
        return LoopSpec(tag, bind, f"{block}.sp", f"{block}.op", f"{block}.mode", unit,
                        loop_command(tag), cas, note)
    return LoopSpec(tag, bind or None, None, None, None, unit, None, cas, note)


class ControllerFaceplate(Faceplate):
    """One loop's faceplate."""

    MODES = ("MAN", "AUTO", "CAS")

    def __init__(self, bridge: QObject, spec: LoopSpec, parent: QWidget | None = None) -> None:
        super().__init__(bridge, spec.tag, parent)
        self.spec = spec
        shown_unit = to_display_units(0.0, spec.unit)[1] or ""
        self._gauge = spec.unit == "BAR A"
        self.pv_field = self.add_value(f"PV ({shown_unit})" if shown_unit else "PV")
        self.sp_field = self.add_entry(f"SP ({shown_unit})" if shown_unit else "SP")
        self.op_field = self.add_entry("Output (%)")
        group = QWidget(self)
        row = QHBoxLayout(group)
        row.setContentsMargins(0, 0, 0, 0)
        self.mode_buttons: dict[str, QPushButton] = {}
        for mode in self.MODES:
            b = QPushButton(mode, group)
            b.setAutoDefault(False)
            b.clicked.connect(lambda _c=False, m=mode: self.choose(m))
            b.setVisible(mode != "CAS" or spec.cas)
            row.addWidget(b)
            self.mode_buttons[mode] = b
        row.addStretch(1)
        self.add_row("Mode", group)
        self.set_button = self.add_button("SET", self.apply, primary=True)
        self.mode = "AUTO"
        self._pv: float | None = None
        self._modelled = spec.sp is not None
        self._seen_mode: str | None = None

    # ---- rendering ----

    def refresh(self, state: Mapping[str, Any]) -> None:
        s = self.spec
        pv = get_path(state, s.pv)
        pv_shown, unit = to_display_units(pv, s.unit)
        self._pv = pv_shown if isinstance(pv_shown, (int, float)) else None
        self.pv_field.set_value(pv_shown, suffix=f" {unit}" if unit else "")
        mode = get_path(state, s.mode) if self._modelled else None
        if not self._modelled or mode is None:
            self.set_mode_chip("")
            self._unmodelled()
            return
        mode = str(mode).upper()
        self.set_mode_chip(mode)
        sp = to_display_units(get_path(state, s.sp), s.unit)[0]
        op = get_path(state, s.op)
        moved = mode != self._seen_mode      # the engine moved the mode (or the first render)
        # The field the chosen mode makes the operator's is left as typed; the other follows
        # the plant.
        if moved or self.sp_field.isReadOnly():
            self.put(self.sp_field, format_value(sp, 3) if sp is not None else "")
        if moved or self.op_field.isReadOnly():
            self.put(self.op_field, format_value(op, 3) if op is not None else "")
        if moved:
            self._seen_mode = mode
            self.choose(mode, from_engine=True)

    def _unmodelled(self) -> None:
        for w in (self.sp_field, self.op_field, *self.mode_buttons.values(), self.set_button):
            w.setEnabled(False)
        self.note.setText(f"{self.spec.tag} is not on this model: the plant publishes no set "
                          "point, output or mode for it.")

    # ---- the operator ----

    def choose(self, mode: str, from_engine: bool = False) -> None:
        """Select the mode SET sends; the fields it does not use go read-only."""
        if (not from_engine and mode == "AUTO" and self.mode != "AUTO"
                and self._pv is not None):
            self.sp_field.setText(format_value(self._pv, 3))      # bumpless, as the engine
        self.mode = mode
        for m, b in self.mode_buttons.items():
            self.mark(b, m == mode)
        self.op_field.setReadOnly(mode != "MAN")
        self.sp_field.setReadOnly(mode != "AUTO")
        self.set_button.setEnabled(self.spec.command is not None)
        self.note.setText(self._note(mode))

    def _note(self, mode: str) -> str:
        tag = self.spec.tag
        if self.spec.command is None:
            text = f"{tag} takes no operator command on this model."
        elif mode == "MAN":
            text = "MAN — operator sets valve opening directly."
        elif mode == "AUTO":
            text = "AUTO — controller drives opening to hold SP."
        elif tag in CAS_MASTERS:
            text = (f"CAS — SP is written by {CAS_MASTERS[tag]}. To change it, open the "
                    f"{CAS_MASTERS[tag]} faceplate; this field is read-only.")
        elif tag in CAS_UNWIRED:
            text = (f"CAS — inactive here: {CAS_UNWIRED[tag]}, so CAS just holds the seeded SP "
                    "(behaves as AUTO).")
        else:
            text = "CAS — opening driven by a linked (cascade) parameter."
        return f"{text}  ·  {self.spec.note}" if self.spec.note else text

    def apply(self) -> None:
        """SET: the mode, and the output in MAN or the set point in AUTO."""
        if self.spec.command is None:
            return
        cmd: dict = {"type": self.spec.command, "id": self.spec.tag, "mode": self.mode}
        op, sp = self.number(self.op_field), self.number(self.sp_field)
        if self.mode == "MAN" and op is not None:
            cmd["op"] = op
        if self.mode == "AUTO" and sp is not None:
            cmd["sp"] = sp + ATM_BAR if self._gauge else sp
        self.send(cmd)
