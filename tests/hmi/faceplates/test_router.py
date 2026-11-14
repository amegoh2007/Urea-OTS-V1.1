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
    # None: 67 navigation hotspots, the 16 pumps the overlays bind to nothing (inert, as in V1),
    # and 11 of unit 335's instruments, which bind nothing. The 2 analysers and 12 stream hotspots
    # open the stream inspector. Decision 98 adds trip 21.2's five keyswitches and AI-329701's
    # indicator; decision 220 adds 322-1's CO2 FEED panel, whose body opens the demand's indicator;
    # decision 222 gives six auxiliary pump icons, 322P002A / B, 323P001A / B and 328P003A / B,
    # the START / STOP faceplate. Decision 224 binds four of unit 335's instruments: FT-335401's
    # indicator, HIC-335602's and HV-335602's hand station (HIC-335602 opened a controller unbound),
    # retires LV-324501's route switch, LV-324501A and B opening their indicators, and adds 324-1b's
    # GRANULATION HEADERS panel, whose body opens the count's indicator.
    assert opened == {
        None: 67 + 16 + 9, "StreamInspector": 2 + 12,
        "IndicatorFaceplate": 139 + 1 + 1 + 1 + 2 + 1, "ControllerFaceplate": 81,
        "HandValveFaceplate": 22 + 2, "BlockValveFaceplate": 10, "PumpFaceplate": 4 + 6,
        "SpeedFaceplate": 8, "MasterSetpointFaceplate": 5, "KeyswitchFaceplate": 1 + 5,
    }


def test_one_faceplate_per_instrument():
    assert faceplate_key({"tag": "FFIC-321404A", "fp": "SIC_321950"}) == "SIC_321950"
    assert faceplate_key({"tag": "FFIC-329401 SP", "ctl": "FFIC-329401"}) == "FFIC-329401"
    assert faceplate_key({"tag": "PV-322203", "face": "hic2"}) == "HIC-322203"
    assert faceplate_key({"tag": "LIC-323501"}) == "LIC-323501"
