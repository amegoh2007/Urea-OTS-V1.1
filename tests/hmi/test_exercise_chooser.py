"""The saved-exercise chooser of the intro's LOAD button — `ureasim.hmi.exercise_chooser`.

Pinned:
* it lists the engine's names in the engine's order, the first selected and LOAD the default;
* LOAD, a double-click and Enter answer the selected name; CANCEL, Escape and closing the window answer
  None; the answer is given once;
* with nothing to choose LOAD is disabled;
* reopened after a refusal, it shows the engine's reason and the way on (choose another, or CANCEL);
* ``open_chooser`` returns at once (no nested event loop), the dialog modal over its parent;
* it is dumb (CLAUDE.md section 4a rule 3): it opens no file dialog and reads no folder.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QWidget

from ureasim.data.intro import CHOOSER
from ureasim.hmi import exercise_chooser
from ureasim.hmi.exercise_chooser import ExerciseChooser, open_chooser

_NAMES = ["load095_steam", "load100_conversion", "load100_steam"]


class _Answers:
    def __init__(self) -> None:
        self.got: list[str | None] = []

    def __call__(self, name: str | None) -> None:
        self.got.append(name)


@pytest.fixture()
def answers() -> _Answers:
    return _Answers()


def test_the_engines_names_are_listed_in_its_order_the_first_selected(qapp, answers) -> None:
    chooser = ExerciseChooser(_NAMES, answers)
    assert [chooser.names.item(i).text() for i in range(chooser.names.count())] == _NAMES
    assert chooser.names.currentRow() == 0
    assert chooser.load_button.isDefault() and chooser.load_button.isEnabled()
    assert chooser.windowTitle() == CHOOSER.title and chooser.isModal()
    assert chooser.load_button.text() == CHOOSER.load and chooser.cancel_button.text() == CHOOSER.cancel


def test_load_answers_the_selected_exercise_once(qapp, answers) -> None:
    chooser = ExerciseChooser(_NAMES, answers)
    chooser.show()
    chooser.names.setCurrentRow(2)
    chooser.load_button.click()
    assert answers.got == ["load100_steam"] and not chooser.isVisible()
    chooser.reject()                                          # a late close is not a second answer
    assert answers.got == ["load100_steam"]


def test_a_double_click_answers_the_name_under_it(qapp, answers) -> None:
    chooser = ExerciseChooser(_NAMES, answers)
    chooser.show()
    item = chooser.names.item(1)
    chooser.names.setCurrentItem(item)
    chooser.names.itemDoubleClicked.emit(item)
    assert answers.got == ["load100_conversion"]


def test_enter_answers_the_selected_exercise(qapp, answers) -> None:
    chooser = ExerciseChooser(_NAMES, answers)
    chooser.show()
    QTest.qWaitForWindowExposed(chooser)
    chooser.names.setFocus()
    QTest.keyClick(chooser.names, Qt.Key.Key_Return)
    assert answers.got == ["load095_steam"]


@pytest.mark.parametrize("how", ["cancel", "escape", "close"])
def test_cancel_escape_and_closing_answer_none(qapp, answers, how) -> None:
    chooser = ExerciseChooser(_NAMES, answers)
    chooser.show()
    QTest.qWaitForWindowExposed(chooser)
    if how == "cancel":
        chooser.cancel_button.click()
    elif how == "escape":
        QTest.keyClick(chooser, Qt.Key.Key_Escape)
    else:
        chooser.close()
    assert answers.got == [None] and not chooser.isVisible()


def test_without_a_note_there_is_no_refusal_line(qapp, answers) -> None:
    assert ExerciseChooser(_NAMES, answers).note is None


def test_a_note_shows_the_engines_refusal_and_the_way_on(qapp, answers) -> None:
    """Reopened after the engine refused an exercise: the reason, then 'choose another, or CANCEL'."""
    note = "The engine refused exercise load100_steam: not a ureasim exercise snapshot"
    chooser = ExerciseChooser(_NAMES, answers, note=note)
    chooser.show()
    assert chooser.note is not None and chooser.note.isVisible()
    assert chooser.note.text() == f"{note}\n{CHOOSER.retry}"
    assert chooser.names.count() == len(_NAMES) and chooser.load_button.isEnabled()
    chooser.load_button.click()
    assert answers.got == ["load095_steam"]


def test_with_nothing_to_choose_load_is_disabled_and_cancel_still_answers(qapp, answers) -> None:
    chooser = ExerciseChooser([], answers)
    assert not chooser.load_button.isEnabled()
    chooser.accept()                                          # no selection: nothing to answer
    assert answers.got == []
    chooser.reject()
    assert answers.got == [None]


def test_open_chooser_returns_at_once_with_the_dialog_modal_over_its_parent(qapp, answers) -> None:
    parent = QWidget()
    parent.show()
    chooser = open_chooser(parent, _NAMES, answers, "a note")  # a nested exec() would not return here
    assert chooser.isVisible() and chooser.parent() is parent and chooser.note is not None
    assert chooser.windowModality() is not Qt.WindowModality.NonModal
    assert answers.got == []
    chooser.load_button.click()
    assert answers.got == ["load095_steam"]
    parent.close()


def test_the_chooser_opens_no_file_dialog_and_reads_no_folder() -> None:
    """The exercise directory is the engine's; the console offers only the names the engine sent."""
    tree = ast.parse(Path(exercise_chooser.__file__).read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
            names.update(a.name for a in node.names)
    assert not names & {"os", "pathlib", "glob", "QFileDialog", "ureasim.engine", "ureasim.engine.session"}
