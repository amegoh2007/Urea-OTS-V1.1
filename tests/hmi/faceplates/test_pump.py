"""The pump faceplate — `ureasim.hmi.faceplates.pump`.

Pinned: exactly one of START and STOP is live; each sends an explicit run; the interlock line
reads the trips that hold the feed pump as V1 words them; a pump with no trips reads n/a.
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
    live = {"trips": {"21_8": True, "21_2": False}, "trip_latched": {"21_8": True, "21_2": True}}
    assert interlock_text(live, "A") == "TRIP 21.8 ACTIVE"
    held = {"trips": {}, "trip_latched": {"21_2": True}}
    assert interlock_text(held, "B") == "TRIP 21.2 LATCHED (clears on START)"
    assert interlock_text(held, "329P006A") == "n/a"
