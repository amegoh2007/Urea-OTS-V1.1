"""The trend window's pen table: one row a pen, its readings, its range and its rulers.

Each row shows a pen's tag, its live value, MIN / MAX / AVG over the view, the range it is drawn
on (auto-scaled or the operator's), its value under every ruler, its unit, and LOW / HIGH fields
that fix its range (blank to auto-scale). A click on a row marks its pen — thickened and drawn on
top while the others fade — and its tick box does the same; the x empties the slot; a screen
element dropped on a row trends in that pen. The table renders what the window hands it and
reports what the operator does.

Source: V1 ``frontend/trend.js`` ``buildWindow`` (the table), ``renderRows``, ``commitRange``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QAbstractItemView, QHeaderView, QLineEdit, QTableWidget, QTableWidgetItem

from ureasim.data.trend import RULERS_MAX
from ureasim.hmi import theme
from ureasim.hmi.trend.plot import TAG_MIME

#: Columns before the ruler columns, and after them.
HEAD = ("#", "✓", "", "TAG", "VALUE", "MIN", "MAX", "AVG", "RANGE")
TAIL = ("UNIT", "LOW", "HIGH", "")
C_MARK, C_KEY, C_TAG, C_VALUE, C_MIN, C_MAX, C_AVG, C_RANGE = 1, 2, 3, 4, 5, 6, 7, 8
C_RULER = len(HEAD)
C_UNIT = C_RULER + RULERS_MAX
C_LOW, C_HIGH, C_REMOVE = C_UNIT + 1, C_UNIT + 2, C_UNIT + 3

#: What an empty slot asks for.
EMPTY_PROMPT = "-- drop indicator here --"


@dataclass(frozen=True)
class RowView:
    """One row as it is to be shown; an empty slot has ``tag`` empty."""

    tag: str = ""
    value: str = ""
    stats: tuple[str, str, str] = ("", "", "")
    range_text: str = ""
    auto: bool = True
    rulers: tuple[str, ...] = field(default_factory=tuple)
    unit: str = ""
    low: str = ""
    high: str = ""
    marked: bool = False


class PenTable(QTableWidget):
    """The ten rows.

    Signals
    -------
    mark_toggled(slot, on)
        The row clicked or its tick box changed.
    remove_clicked(slot)
        The x clicked.
    range_committed(slot, which, text)
        LOW or HIGH entered (``which`` is ``"lo"`` or ``"hi"``); blank text asks for auto-scale.
    tag_dropped(tag, slot)
        A screen element dropped on a row.
    """

    mark_toggled = pyqtSignal(int, bool)
    remove_clicked = pyqtSignal(int)
    range_committed = pyqtSignal(int, str, str)
    tag_dropped = pyqtSignal(str, int)

    def __init__(self, slots: int, pens: tuple[str, ...], parent=None):
        headers = list(HEAD) + [f"R{i + 1}" for i in range(RULERS_MAX)] + list(TAIL)
        super().__init__(slots, len(headers), parent)
        self.setHorizontalHeaderLabels(headers)
        self.verticalHeader().setVisible(False)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(C_TAG, QHeaderView.ResizeMode.Stretch)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        font = QFont()
        font.setFamilies(theme.VALUE_FONT_FAMILIES)
        font.setPixelSize(11)
        self.setFont(font)
        self.setStyleSheet(
            f"QTableWidget {{ background:{theme.TW_BG}; color:{theme.IND_TEXT}; "
            f"gridline-color:{theme.TW_BORDER}; border:none; }}"
            f"QHeaderView::section {{ background:{theme.TW_BAR_BG}; color:{theme.TW_LABEL}; "
            f"border:none; border-bottom:1px solid {theme.TW_BORDER}; padding:3px 6px; }}"
            f"QLineEdit {{ background:{theme.IND_BG}; color:{theme.IND_TEXT}; "
            f"border:1px solid {theme.TW_BORDER}; }}")
        self._edits: list[tuple[QLineEdit, QLineEdit]] = []
        self._loading = False
        for row in range(slots):
            self._build_row(row, pens[row])
        self.set_ruler_columns(0)
        self.cellClicked.connect(self._on_cell_clicked)
        self.itemChanged.connect(self._on_item_changed)

    def _build_row(self, row: int, pen: str) -> None:
        for col in range(self.columnCount()):
            item = QTableWidgetItem("")
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.setItem(row, col, item)
        self.item(row, 0).setText(str(row + 1))
        self.item(row, 0).setForeground(QColor(theme.TW_LABEL))
        self.item(row, C_MARK).setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        self.item(row, C_MARK).setCheckState(Qt.CheckState.Unchecked)
        self.item(row, C_KEY).setBackground(QColor(pen))
        for col, colour in ((C_VALUE, theme.TW_VALUE_TEXT), (C_MIN, theme.TW_MIN_TEXT),
                            (C_MAX, theme.TW_MAX_TEXT), (C_AVG, theme.TW_AVG_TEXT)):
            self.item(row, col).setForeground(QColor(colour))
            self.item(row, col).setTextAlignment(Qt.AlignmentFlag.AlignRight
                                                 | Qt.AlignmentFlag.AlignVCenter)
        self.item(row, C_REMOVE).setForeground(QColor(theme.TW_REMOVE_TEXT))
        pair = []
        for col, which in ((C_LOW, "lo"), (C_HIGH, "hi")):
            edit = QLineEdit(self)
            edit.setAlignment(Qt.AlignmentFlag.AlignRight)
            edit.setToolTip(f"Display {'LOW' if which == 'lo' else 'HIGH'} — blank to auto-scale")
            edit.editingFinished.connect(
                lambda r=row, w=which, e=edit: self.range_committed.emit(r, w, e.text()))
            self.setCellWidget(row, col, edit)
            pair.append(edit)
        self._edits.append((pair[0], pair[1]))

    # ---- rendering -----------------------------------------------------------------

    def set_ruler_columns(self, count: int, colours: tuple[str, ...] = ()) -> None:
        """Show one value column for each ruler placed, headed in its colour."""
        for r in range(RULERS_MAX):
            self.setColumnHidden(C_RULER + r, r >= count)
            if r < count and r < len(colours):
                self.horizontalHeaderItem(C_RULER + r).setForeground(QColor(colours[r]))

    def show_row(self, row: int, view: RowView, ruler_colours: tuple[str, ...]) -> None:
        """Fill one row from its view."""
        self._loading = True
        filled = bool(view.tag)
        text = {C_TAG: view.tag or EMPTY_PROMPT, C_VALUE: view.value, C_MIN: view.stats[0],
                C_MAX: view.stats[1], C_AVG: view.stats[2],
                C_RANGE: view.range_text + (" A" if filled and view.auto else ""),
                C_UNIT: view.unit, C_REMOVE: "x" if filled else ""}
        for col, value in text.items():
            self.item(row, col).setText(value)
        self.item(row, C_TAG).setForeground(QColor(theme.IND_TEXT if filled
                                                   else theme.TW_EMPTY_TEXT))
        for r in range(RULERS_MAX):
            item = self.item(row, C_RULER + r)
            item.setText(view.rulers[r] if r < len(view.rulers) else "")
            if r < len(ruler_colours):
                item.setForeground(QColor(ruler_colours[r]))
        mark = self.item(row, C_MARK)
        mark.setCheckState(Qt.CheckState.Checked if view.marked else Qt.CheckState.Unchecked)
        mark.setFlags((Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable) if filled
                      else Qt.ItemFlag.NoItemFlags)
        background = QColor(theme.TW_ROW_MARKED_BG if view.marked else theme.TW_BG)
        for col in range(self.columnCount()):
            if col != C_KEY:
                self.item(row, col).setBackground(background)
        for edit, value in zip(self._edits[row], (view.low, view.high)):
            edit.setEnabled(filled)
            if not edit.hasFocus():
                edit.setText(value)
        self._loading = False

    # ---- operator ------------------------------------------------------------------

    def _on_cell_clicked(self, row: int, col: int) -> None:
        if col == C_REMOVE:
            self.remove_clicked.emit(row)
        elif col not in (C_MARK, C_LOW, C_HIGH):
            self.mark_toggled.emit(row, self.item(row, C_MARK).checkState()
                                   != Qt.CheckState.Checked)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if not self._loading and item.column() == C_MARK:
            self.mark_toggled.emit(item.row(), item.checkState() == Qt.CheckState.Checked)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat(TAG_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasFormat(TAG_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        if not event.mimeData().hasFormat(TAG_MIME):
            return
        row = self.rowAt(int(event.position().y()))
        if row >= 0:
            self.tag_dropped.emit(bytes(event.mimeData().data(TAG_MIME)).decode("utf-8"), row)
            event.acceptProposedAction()


__all__ = ["PenTable", "RowView", "EMPTY_PROMPT"]
