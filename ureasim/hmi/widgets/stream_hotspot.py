"""The stream inspector — what a stream hotspot or an analyser opens.

A trainee clicks a drawn process line (a ``strm`` hotspot) or an AE-* analyser (``ae``) and asks
what is flowing there. The inspector shows the stream's record exactly as the engine publishes it
in the packet's ``STREAMS`` registry (`ureasim.engine.packet.streams`): the route and phase, the
temperature and pressure, the mass, molar and volumetric flows, the molar mass, the density, the
enthalpy and its basis, and the composition on both bases. An analyser shows the composition alone.

It computes nothing. Every number is a field of the published record, formatted as V1 formatted it
— the mass flow in t/h and kg/h are both published fields, not a conversion here — and a field the
engine leaves out reads "—". A stream the packet does not carry is not opened, as V1 opened none.

One departure from V1: V1 filled its popup once, when it opened, so its numbers went stale while it
stayed open. The inspector is a faceplate (`ureasim.hmi.faceplates.base.Faceplate`) and redraws
from every packet, as every faceplate does.

Source: V1 ``frontend/app.js`` ``COMP_LBL``, ``fStrm``, ``renderStream`` and ``openStreamPopup``
(379-417); ``frontend/overlays.js`` 739-743 (an ``ae`` opens the composition only, a ``strm`` the
whole record); ``frontend/index.html`` ``#streamModal``.
"""

from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Mapping

from PyQt6.QtCore import QObject, Qt
from PyQt6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem, QWidget

from ureasim.hmi import theme
from ureasim.hmi.faceplates.base import Faceplate
from ureasim.hmi.state_access import get_path

#: The components V1's inspector lists, in its order, with its labels.
COMP_LBL = (
    ("CO2", "CO₂"), ("CH4", "CH₄"), ("H2", "H₂"), ("H2O", "H₂O"),
    ("N2", "N₂"), ("NH3", "NH₃"), ("O2", "O₂"), ("Urea", "Urea"),
    ("Biuret", "Biuret"),
)

#: What a field the record leaves out reads.
MISSING = "—"

#: The enthalpy bases V1 names, by the tier the record's basis starts with.
_BASIS = (("H0", "H0 (ideal solution)"), ("H1", "H1 (with mixing)"))


def _fmt(value: Any, decimals: int) -> str:
    """V1's ``fStrm``: the number to ``decimals`` places as JavaScript's ``toFixed`` writes it, or
    "—" when there is none. ``toFixed`` rounds a tie away from zero on the double's exact value,
    where Python's format rounds it to even (3342.5 kg/h reads 3343, not 3342), prints no sign on a
    negative zero, and spells the non-finite values its own way."""
    if value is None:
        return MISSING
    x = float(value)
    if not math.isfinite(x):
        return "NaN" if math.isnan(x) else ("Infinity" if x > 0.0 else "-Infinity")
    if x == 0.0:
        x = 0.0
    return str(Decimal(x).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP))


def _composition(record: Mapping[str, Any]) -> list[tuple[str, str]]:
    """The composition rows: each listed component present on either basis."""
    mol = record.get("mol_pct") or {}
    mass = record.get("mass_pct") or {}
    rows = [("Composition", "mol %  |  mass %")]
    for key, label in COMP_LBL:
        mo, ma = mol.get(key) or 0.0, mass.get(key) or 0.0
        if mo > 0.0 or ma > 0.0:
            rows.append((label, f"{_fmt(mo, 3)}  |  {_fmt(ma, 3)}"))
    return rows


def stream_rows(record: Mapping[str, Any], composition_only: bool = False) -> list[tuple[str, str]]:
    """The inspector's rows for one published stream record, as V1's ``renderStream`` built them."""
    if composition_only:
        return _composition(record)
    basis = record.get("enthalpy_basis")
    basis_text = MISSING
    if basis:
        basis_text = next((text for tier, text in _BASIS if str(basis).startswith(tier)),
                          "H2 (plant reconciled)")
    h, h_flow = record.get("enthalpy_kJkg"), record.get("enthalpy_flow_kW")
    rho, vol = record.get("rho"), record.get("vol_m3h")
    rows = [
        ("Route", f"{record.get('src')} → {record.get('dst')}"),
        ("Phase", str(record.get("phase"))),
        ("Temperature", f"{_fmt(record.get('T_C'), 1)} °C"),
        ("Pressure", f"{_fmt(record.get('P_bara'), 1)} bar a"),
        ("Mass flow", f"{_fmt(record.get('mass_th'), 2)} t/h "
                      f"({_fmt(record.get('mass_kgh'), 0)} kg/h)"),
        ("Molar flow", f"{_fmt(record.get('mol_kmolh'), 1)} kmol/h"),
        ("Avg MW", f"{_fmt(record.get('MW'), 2)} kg/kmol"),
        ("Specific enthalpy",
         f"{_fmt(h, 2)} kJ/kg" if h is not None else f"{MISSING} (not modelled)"),
        ("Enthalpy flow",
         f"{_fmt(h_flow, 2)} kW" if h_flow is not None else f"{MISSING} (not modelled)"),
        ("Enthalpy basis", basis_text),
        ("Density", f"{_fmt(rho, 1)} kg/m³" if rho is not None else MISSING),
        ("Volum. flow", f"{_fmt(vol, 1)} m³/h" if vol is not None else MISSING),
        ("", ""),
    ]
    return rows + _composition(record)


def published_stream(state: Mapping[str, Any] | None, stream_id: str) -> Mapping[str, Any] | None:
    """The packet's record for `stream_id`, or None when the packet carries none."""
    record = get_path(state, "STREAMS")
    if isinstance(record, Mapping):
        record = record.get(stream_id)
    return record if isinstance(record, Mapping) else None


class StreamInspector(Faceplate):
    """One stream's inspector: the record's rows in V1's two-column table, redrawn per packet."""

    def __init__(self, bridge: QObject, element: Mapping[str, Any],
                 parent: QWidget | None = None) -> None:
        self.stream_id = str(element.get("stream") or "")
        self.composition_only = element.get("t") == "ae"
        super().__init__(bridge, str(element.get("tag") or self.stream_id), parent)
        self.table = QTableWidget(0, 2, self)
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setStyleSheet(
            f"QTableWidget {{ background:{theme.FP_BG}; color:{theme.FP_TEXT}; "
            f"gridline-color:{theme.SI_CELL_BORDER}; border:1px solid {theme.SI_CELL_BORDER}; "
            f"font-family:{theme.value_font_stack()}; }}")
        self.table.setMinimumWidth(420)
        self.rows.addWidget(self.table, 0, 0, 1, 2)

    def refresh(self, state: Mapping[str, Any]) -> None:
        record = published_stream(state, self.stream_id)
        if record is None:
            self.status.setText("NOT PUBLISHED")
            self.table.setRowCount(0)
            return
        self.status.setText("")
        self.title_label.setText(str(record.get("name") or self.stream_id))
        rows = stream_rows(record, self.composition_only)
        self.table.setRowCount(len(rows))
        for r, (label, value) in enumerate(rows):
            for c, text in enumerate((label, value)):
                item = self.table.item(r, c)
                if item is None:
                    item = QTableWidgetItem()
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    self.table.setItem(r, c, item)
                item.setText(text)
        # Every row in view, as V1's modal shows its whole table.
        self.table.resizeRowsToContents()
        height = sum(self.table.rowHeight(r) for r in range(len(rows)))
        self.table.setFixedHeight(height + 2 * self.table.frameWidth())


__all__ = ["COMP_LBL", "MISSING", "stream_rows", "published_stream", "StreamInspector"]
