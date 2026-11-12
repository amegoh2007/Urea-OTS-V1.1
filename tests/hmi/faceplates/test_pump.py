"""The pump faceplate — `ureasim.hmi.faceplates.pump`.

Pinned: exactly one of START and STOP is live; each sends an explicit run; the interlock line
reads the trips that hold the feed pump as V1 words them; a pump with no trips reads n/a. V1's
trip 22.2, which decision 174 named as the simulator's own, is in no plant document and is gone
(decision 189), and with it the one latch the line showed apart from its trip.
"""

from __future__ import annotations

from ureasim.hmi.faceplates.pump import PumpFaceplate, interlock_text

A = {"t": "pump", "tag": "321P002A", "bind": "pumpA", "id": "A"}


def test_one_live_button_and_an_explicit_run(bridge):
    face = PumpFaceplate(bridge, A)
    face.show()
    assert face.status_field.text() == "STOPPED" and face.interlock_field.text() == "CLEAR"
    assert face.start_button.isEnabled() and not face.stop_button.isEnabled()
    face.start_button.click()
    assert bridge.sent[-1] == {"type": "pump_toggle", "id": "A", "on": True}
    bridge.publish({**bridge.latest, "pumpA": {"on": True}})
    assert face.stop_button.isEnabled() and not face.start_button.isEnabled()
    face.close()


def test_the_interlock_line():
    """AC4's flags publish the same in ``trips`` and ``trip_latched``."""
    live = {"trips": {"21_8": True, "21_2": False}, "trip_latched": {"21_8": True, "21_2": False}}
    assert interlock_text(live, "A") == "TRIP 21.8 ACTIVE"
    both = {"trips": {"21_2": True, "21_10": True}, "trip_latched": {"21_2": True, "21_10": True}}
    assert interlock_text(both, "B") == "TRIP 21.2, 21.10 ACTIVE"
    assert interlock_text({"trips": {}, "trip_latched": {}}, "A") == "CLEAR"
    assert interlock_text(both, "329P006A") == "n/a"


def test_v1s_trip_22_2_is_not_shown():
    """Decision 189: a packet carrying V1's 22.2 key holds no pump."""
    stray = {"trips": {"22_2": True}, "trip_latched": {"22_2": True}}
    assert interlock_text(stray, "A") == "CLEAR"
