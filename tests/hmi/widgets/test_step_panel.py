"""The step panels — `ureasim.hmi.widgets.step_panel`: 322-1's CO2 FEED (decision 220) and 324-1b's
GRANULATION HEADERS (decision 224).

Pinned: the readout is the packet's demand and nothing the panel keeps; a press on DOWN or UP emits
the engine's ``co2_step`` with its direction, and a press on the panel's body is an ordinary
activation; a button at its published limit is dead, as V1's was; edit-layout mode sends nothing;
the screen relays the command and the console sends it, and the engine's refusal while trip 21.2
is latched reaches the status bar with its reason. The GRANULATION HEADERS panel is the same panel
on its own row of `data.faceplates.STEP_PANELS`: DECREASE and INCREASE, each word inside its button,
send ``granulation_headers``, and are dead at none and at all twelve.
"""

from __future__ import annotations

import pytest
from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt6.QtGui import QFontMetrics, QMouseEvent

from ureasim.data.faceplates import (
    CO2_STEP_COMMAND,
    CO2_STEP_FIELD,
    GRANULATION_STEP_COMMAND,
    GRANULATION_STEP_FIELD,
)
from ureasim.data.screen_layout import OVERLAYS
from ureasim.hmi.widgets import build_widget
from ureasim.hmi.widgets.step_panel import StepPanelWidget

PANEL = next(e for e in OVERLAYS["screen-322-1"] if e["k"] == "co2step")
GRANULATION = next(e for e in OVERLAYS["screen-324-1b"] if e["k"] == "granstep")


def _packet(pct):
    return {"CO2_FEED": {"demand_pct": pct}}


def _click(widget, pos: QPoint) -> None:
    p = QPointF(pos)
    widget.mousePressEvent(QMouseEvent(QEvent.Type.MouseButtonPress, p, p, Qt.MouseButton.LeftButton,
                                       Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
    widget.mouseReleaseEvent(QMouseEvent(QEvent.Type.MouseButtonRelease, p, p,
                                         Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton,
                                         Qt.KeyboardModifier.NoModifier))


@pytest.fixture()
def panel(qapp):
    w = build_widget(PANEL)
    sent, activated = [], []
    w.command_requested.connect(sent.append)
    w.activated.connect(activated.append)
    yield w, sent, activated
    w.deleteLater()


def test_the_registry_builds_the_panel_at_v1s_size(panel):
    w, _sent, _activated = panel
    assert isinstance(w, StepPanelWidget) and (w.width(), w.height()) == (196, 53)
    assert w.button_rect(-1).right() < w.button_rect(+1).left()


def test_the_readout_is_the_packets_and_nothing_kept(panel):
    w, _sent, _activated = panel
    w.update_from(_packet(102.0))
    assert w._value == 102.0
    w.update_from({})
    assert w._value is None and w.enabled(+1) and w.enabled(-1)


def test_down_and_up_send_one_engine_step_each_and_the_body_activates(panel):
    w, sent, activated = panel
    w.update_from(_packet(100.0))
    _click(w, w.button_rect(-1).center())
    _click(w, w.button_rect(+1).center())
    assert sent == [{"type": CO2_STEP_COMMAND, CO2_STEP_FIELD: -1},
                    {"type": CO2_STEP_COMMAND, CO2_STEP_FIELD: 1}] and activated == []
    _click(w, QPoint(w.width() // 2, 4))
    assert len(sent) == 2 and len(activated) == 1


def test_a_button_at_its_published_limit_is_dead(panel):
    w, sent, _activated = panel
    w.update_from(_packet(120.0))
    _click(w, w.button_rect(+1).center())
    assert sent == [] and not w.enabled(+1) and w.enabled(-1)
    w.update_from(_packet(0.0))
    _click(w, w.button_rect(-1).center())
    assert sent == [] and not w.enabled(-1) and w.enabled(+1)


def test_edit_layout_mode_sends_nothing(panel):
    w, sent, _activated = panel
    w.set_editing(True)
    _click(w, w.button_rect(+1).center())
    assert sent == []


def test_a_press_reaches_the_engine_and_its_refusal_the_status_bar(qapp, monkeypatch):
    """The screen relays the panel's command and the console sends it as it is; the engine's own
    answer while trip 21.2 is latched comes back to the status bar with its reason."""
    from ureasim.engine.command import apply_command
    from ureasim.engine.plant import build_plant
    from ureasim.hmi.bridge import EngineBridge
    from ureasim.hmi.main_window import MainWindow

    bridge = EngineBridge("console")
    sent = []
    monkeypatch.setattr(bridge, "send_command", lambda cmd: sent.append(cmd) or len(sent))
    win = MainWindow(bridge)
    view = win._views["screen-322-1"]
    w = next(o for o in view.stage.overlays if o.element["k"] == "co2step")
    _click(w, w.button_rect(+1).center())
    assert sent == [{"type": "co2_step", "dir": 1}]

    plant = build_plant()[1]
    plant.units["SYN-TRIPS"].i_21_2.latched = True
    plant.operator["320K002-CO2"] = 0.0
    answer = apply_command(plant, sent[0])
    assert not answer.ok
    bridge.command_result.emit(1, answer.ok, answer.reason)
    assert win.statusBar().currentMessage() == f"REFUSED: {answer.reason}"
    assert "XV-322902 is held shut by trip 21.2's flag" in answer.reason
    bridge.close()
    win.close()


def test_the_granulation_panel_steps_the_header_valves(qapp):
    w = build_widget(GRANULATION)
    sent = []
    w.command_requested.connect(sent.append)
    assert isinstance(w, StepPanelWidget) and (w.width(), w.height()) == (264, 53)
    metrics = QFontMetrics(w._button_font)
    for direction, word in ((-1, "▼ DECREASE"), (+1, "▲ INCREASE")):
        assert metrics.horizontalAdvance(word) < w.button_rect(direction).width()
    w.update_from({"EVAP_324": {"E003": {"HEADERS_ONLINE": 10}}})
    _click(w, w.button_rect(-1).center())
    _click(w, w.button_rect(+1).center())
    assert sent == [{"type": GRANULATION_STEP_COMMAND, GRANULATION_STEP_FIELD: -1},
                    {"type": GRANULATION_STEP_COMMAND, GRANULATION_STEP_FIELD: 1}]
    w.update_from({"EVAP_324": {"E003": {"HEADERS_ONLINE": 12}}})
    assert not w.enabled(+1) and w.enabled(-1)
    w.update_from({"EVAP_324": {"E003": {"HEADERS_ONLINE": 0}}})
    assert not w.enabled(-1) and w.enabled(+1)
    w.deleteLater()
