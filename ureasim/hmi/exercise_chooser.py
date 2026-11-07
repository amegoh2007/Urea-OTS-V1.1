"""The saved-exercise chooser the intro's LOAD button opens: the engine's list, one choice, or none.

Plant equipment modelled
------------------------
None. A dialog: it shows the names of the saved exercises the engine listed (``EngineSession.exercises``,
sent over the protocol's ``exercise_list`` / ``exercises``) and reports which one the operator chose, or that
the operator chose none.

Reference documents
-------------------
* ``project.md`` decision 171: the LOAD button on the start-up intro, the process engineer's request of
  2026-11-05.
* CLAUDE.md section 4a rule 3: like a faceplate and the instructor's panel it is dumb. It renders what the
  engine sent and hands back the operator's answer, nothing else. It reads no file and no folder: the
  exercise directory is the engine's, and the engine restores an exercise by its name.
* ``ureasim/data/intro.py``: ``CHOOSER`` (its texts and size) and ``PALETTE`` (the intro's colours).

Equations
---------
None.

Process utility
---------------
A trainee starts from the plant state an exercise was saved in (a steady state at another load, the moment
before a malfunction) instead of the 1750 MTPD design seed. The chooser stands over the intro while the
engine is still held, so no plant time passes while the operator decides. When the engine has refused the
exercise chosen (a file the present model will not take), the chooser opens again with the engine's reason
in a ``note``, so the operator sees why and chooses another or cancels.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QListWidget, QVBoxLayout, QWidget

from ureasim.data.intro import CHOOSER, PALETTE

__all__ = ["ExerciseChooser", "open_chooser"]


def _style() -> str:
    """The intro's paper, teal and orange on the dialog."""
    return (
        f"QDialog {{ background: {PALETTE.paper_top}; }}"
        f"QLabel {{ color: {PALETTE.teal_deep}; font-size: 11pt; }}"
        f"QLabel#note {{ background: {PALETTE.white}; border-left: 4px solid {PALETTE.orange}; "
        f"padding: 6px; font-weight: bold; }}"
        f"QListWidget {{ background: {PALETTE.white}; color: {PALETTE.teal_deep}; "
        f"border: 1px solid {PALETTE.slate}; font-size: 11pt; }}"
        f"QListWidget::item {{ padding: 4px; }}"
        f"QListWidget::item:selected {{ background: {PALETTE.teal}; color: {PALETTE.white}; }}"
        f"QPushButton {{ background: {PALETTE.teal_deep}; color: {PALETTE.white}; border: none; "
        f"border-radius: 14px; padding: 6px 22px; font-weight: bold; }}"
        f"QPushButton:hover {{ background: {PALETTE.teal}; }}"
        f"QPushButton:default {{ border: 2px solid {PALETTE.orange}; }}"
        f"QPushButton:disabled {{ background: {PALETTE.slate}; }}"
    )


class ExerciseChooser(QDialog):
    """The engine's saved exercises with LOAD and CANCEL; ``done`` receives the name chosen, or None.

    LOAD, Enter and a double-click choose the selected name; CANCEL, Escape and closing the window choose
    none. ``done`` is called once, after the dialog has closed. A ``note`` (the engine's refusal of the
    exercise chosen before) is shown above the list with the hint to choose another or cancel.
    """

    def __init__(self, names: Sequence[str], done: Callable[[str | None], None],
                 parent: QWidget | None = None, note: str = "") -> None:
        super().__init__(parent)
        self._done = done
        self._answered = False
        self.setWindowTitle(CHOOSER.title)
        self.setModal(True)
        self.setMinimumSize(CHOOSER.min_width, CHOOSER.min_height)
        self.setStyleSheet(_style())
        column = QVBoxLayout(self)
        prompt = QLabel(CHOOSER.prompt, self)
        prompt.setWordWrap(True)
        column.addWidget(prompt)
        self.note: QLabel | None = None
        if note:
            self.note = QLabel(f"{note}\n{CHOOSER.retry}", self)
            self.note.setObjectName("note")
            self.note.setWordWrap(True)
            column.addWidget(self.note)
        self.names = QListWidget(self)
        self.names.addItems([str(n) for n in names])
        if self.names.count():
            self.names.setCurrentRow(0)
        self.names.itemDoubleClicked.connect(lambda _item: self.accept())
        column.addWidget(self.names, 1)
        self.buttons = QDialogButtonBox(self)
        self.load_button = self.buttons.addButton(CHOOSER.load, QDialogButtonBox.ButtonRole.AcceptRole)
        self.cancel_button = self.buttons.addButton(CHOOSER.cancel, QDialogButtonBox.ButtonRole.RejectRole)
        self.load_button.setDefault(True)
        self.load_button.setEnabled(self.names.count() > 0)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        column.addWidget(self.buttons)

    def accept(self) -> None:
        """LOAD: the selected exercise, if there is one."""
        item = self.names.currentItem()
        if item is None:
            return
        super().accept()
        self._answer(item.text())

    def reject(self) -> None:
        """CANCEL, Escape or the window closed: no exercise."""
        super().reject()
        self._answer(None)

    def _answer(self, name: str | None) -> None:
        if not self._answered:
            self._answered = True
            self._done(name)


def open_chooser(parent: QWidget | None, names: Sequence[str], done: Callable[[str | None], None],
                 note: str = "") -> ExerciseChooser:
    """Open the chooser over ``parent`` and return at once; ``done`` receives the answer later.

    ``open()``, not ``exec()``: a nested event loop would run the bridge's slots inside it, and the
    start-up controller must keep hearing its link while the operator decides.
    """
    chooser = ExerciseChooser(names, done, parent, note)
    chooser.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
    chooser.open()
    return chooser
