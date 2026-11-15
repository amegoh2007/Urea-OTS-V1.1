"""The indicator faceplate and the faceplate window — `ureasim.hmi.faceplates.indicator`,
`ureasim.hmi.faceplates.base`.

Pinned: a value with its unit and source, a pressure in gauge, three decimals on a click; ENTER is
the primary button and closes the faceplate; a disconnected console sends nothing and says so.
"""

from __future__ import annotations

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtTest import QTest

from tests.hmi.conftest import FakeBridge
from ureasim.hmi.faceplates.hand_valve import HandValveFaceplate
from ureasim.hmi.faceplates.indicator import IndicatorFaceplate
from ureasim.hmi.state_access import ATM_BAR

HIC602 = {"t": "ind", "tag": "HIC-322602", "face": "hic", "bind": "EJ_322F001.HIC_322602"}


def test_a_value_its_unit_and_three_decimals_on_a_click(bridge):
    face = IndicatorFaceplate(bridge, {"t": "ind", "tag": "PT-323201",
                                       "bind": "RECIRC_323.C003.PIC_329202.pv", "u": "BAR A",
                                       "dec": 2})
    face.show()
    assert face.value_field.text() == f"{3.9 - ATM_BAR:.2f}"
    assert face.unit_field.text() == "BARG"
    QTest.mouseClick(face.value_field, Qt.MouseButton.LeftButton)
    assert face.value_field.expanded and face.value_field.text() == f"{3.9 - ATM_BAR:.3f}"
    face.close()


def test_enter_is_set_and_a_dead_link_sends_nothing(qapp, packet):
    bridge = FakeBridge(packet)
    face = HandValveFaceplate(bridge, HIC602)
    face.show()
    face.entry.setText("70")
    face.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return,
                                 Qt.KeyboardModifier.NoModifier))
    assert bridge.sent == [{"type": "hic_set", "value": 70.0}] and not face.isVisible()
    dead = FakeBridge(packet, connected=False)
    face = HandValveFaceplate(dead, HIC602)
    face.show()
    face.primary.click()
    assert dead.sent == [] and face.message.text() == "not connected — command not sent"
    face.close()
