"""The hand-valve faceplate — `ureasim.hmi.faceplates.hand_valve`.

Pinned: the entry starts at the valve's live opening and SET sends the station's command, which
the engine takes; PV-322203's route opens HIC-322203's minimum opening.
"""

from __future__ import annotations

from ureasim.engine.command import apply_command
from ureasim.engine.plant import build_plant
from ureasim.hmi.faceplates.hand_valve import HandValveFaceplate

HIC604 = {"t": "ind", "tag": "HIC-322604", "bind": "SCRUB_322E003.HIC_322604", "u": "%",
          "face": "hic"}


def test_the_live_opening_and_the_stations_command(bridge, packet):
    face = HandValveFaceplate(bridge, HIC604)
    face.show()
    assert face.entry.text() == f"{packet['SCRUB_322E003']['HIC_322604']:.1f}"
    face.entry.setText("55")
    face.primary.click()
    assert bridge.sent[-1] == {"type": "hic604_set", "op": 55.0}
    assert apply_command(build_plant()[1], bridge.sent[-1]).ok
    face.close()


def test_pv_322203_opens_hic_322203(bridge):
    face = HandValveFaceplate(bridge, {"t": "ind", "tag": "PV-322203", "face": "hic2",
                                       "bind": "CO2_FEED.PV_322203"})
    face.show()
    assert face.windowTitle() == "HIC-322203 → PV-322203 MIN OPENING"
    face.entry.setText("5")
    face.primary.click()
    assert bridge.sent[-1] == {"type": "hic2_set", "value": 5.0}
    face.close()
