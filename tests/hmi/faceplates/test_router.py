"""Which faceplate a click opens — `ureasim.hmi.faceplates.faceplate_for` — on every screen element.

Pinned: V1's routing over the 393 elements of the ten screens (V1's 387 and decision 98's six:
trip 21.2's five keyswitches and AI-329701) — the pumps the engine models open
the pump faceplate and the others nothing; every block valve and hand switch the valve faceplate;
the keyswitch, the route, the hand stations, the speed controllers, the MASTER SP, every loop and
every other bound value theirs; analysers and stream hotspots the stream inspector (every one's stream
is published); navigation none. One faceplate per instrument: an element's key is its loop or station.
"""

from __future__ import annotations

from collections import Counter

from ureasim.data.screen_layout import OVERLAYS
from ureasim.hmi.faceplates import faceplate_for, faceplate_key
from ureasim.hmi.state_access import BindMap


def test_every_element_opens_v1s_faceplate(bridge):
    bind_map = BindMap(OVERLAYS)
    opened = Counter()
    for elements in OVERLAYS.values():
        for el in elements:
            face = faceplate_for(bind_map.effective(el), bridge)
            opened[type(face).__name__ if face else None] += 1
            if face is not None:
                face.deleteLater()
    # None: 67 navigation hotspots, the 22 pumps the overlays bind to nothing (inert, as in V1),
    # and 11 of unit 335's instruments, which bind nothing. The 2 analysers and 12 stream hotspots
    # open the stream inspector. Decision 98 adds trip 21.2's five keyswitches and AI-329701's
    # indicator; decision 220 adds 322-1's CO2 FEED panel, whose body opens the demand's indicator.
    assert opened == {
        None: 67 + 22 + 11, "StreamInspector": 2 + 12,
        "IndicatorFaceplate": 139 + 1 + 1, "ControllerFaceplate": 82,
        "HandValveFaceplate": 22, "BlockValveFaceplate": 10, "PumpFaceplate": 4,
        "SpeedFaceplate": 8, "MasterSetpointFaceplate": 5, "KeyswitchFaceplate": 1 + 5,
        "RouteFaceplate": 2,
    }


def test_one_faceplate_per_instrument():
    assert faceplate_key({"tag": "FFIC-321404A", "fp": "SIC_321950"}) == "SIC_321950"
    assert faceplate_key({"tag": "FFIC-329401 SP", "ctl": "FFIC-329401"}) == "FFIC-329401"
    assert faceplate_key({"tag": "PV-322203", "face": "hic2"}) == "HIC-322203"
    assert faceplate_key({"tag": "LIC-323501"}) == "LIC-323501"
