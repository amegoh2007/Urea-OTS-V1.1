"""The switch faceplates — `ureasim.hmi.faceplates.switches`.

Pinned: a block valve's state and its one button, which sends V1's toggle; XV-322915 read-only;
HS-322915's TURN and RELEASE, each explicit, beside the valve and I 22.1's limit; LV-324501's two
routes; trip 21.2's keyswitches (decision 98) beside the key's position and 21.2's flag. Every
command is one the engine takes, but XV-322915's, which none sends.
"""

from __future__ import annotations

from ureasim.engine.command import apply_command
from ureasim.engine.plant import build_plant
from ureasim.hmi.faceplates.switches import (
    BlockValveFaceplate,
    KeyswitchFaceplate,
    RouteFaceplate,
)


def test_a_block_valve_and_its_toggle(bridge):
    face = BlockValveFaceplate(bridge, {"t": "xv", "tag": "XV-321901", "bind": "XV_321901",
                                        "cmd": "321901"})
    face.show()
    assert face.status_field.text() == "OPEN" and face.toggle.text() == "CLOSE"
    face.toggle.click()
    assert bridge.sent[-1] == {"type": "xv_toggle", "id": "321901"}
    assert apply_command(build_plant()[1], bridge.sent[-1]).ok
    face.close()


def test_xv_322915_has_no_operator_command(bridge):
    face = BlockValveFaceplate(bridge, {"t": "xv", "tag": "XV-322915",
                                        "bind": "ABSORB_328.C001.XV_322915"})
    face.show()
    assert face.status_field.text() == "CLOSED" and not face.toggle.isEnabled()
    face.toggle.click()
    assert bridge.sent == []
    face.close()


def test_the_keyswitch_and_the_route(bridge):
    key = KeyswitchFaceplate(bridge, {"t": "ovrd", "tag": "HS-322915", "cmd": "HS-322915",
                                      "xv": "ABSORB_328.C001.XV_322915", "latch": "22_1"})
    key.show()
    assert (key.valve_field.text(), key.limit_field.text()) == ("CLOSED", "NORMAL")
    key.turn(True)
    key.turn(False)
    route = RouteFaceplate(bridge, {"t": "ind", "tag": "LV-324501B", "route": "B"})
    route.show()
    assert route.fields["A"].text() == "75.0"
    route.route("B")
    assert bridge.sent == [{"type": "keyswitch_set", "id": "HS-322915", "on": True},
                           {"type": "keyswitch_set", "id": "HS-322915", "on": False},
                           {"type": "lv324501_route_set", "route": "B"}]
    plant = build_plant()[1]
    assert all(apply_command(plant, c).ok for c in bridge.sent)
    key.close()
    route.close()


def test_a_trip_21_2_keyswitch(bridge):
    """HS-321634 from its screen element (decision 98): the key's position and 21.2's flag, TURN and
    RELEASE each a ``keyswitch_set`` the engine takes."""
    from ureasim.data.screen_layout import OVERLAYS
    el = next(e for e in OVERLAYS["screen-321-1"] if e["k"] == "ovrhs321634")
    key = KeyswitchFaceplate(bridge, el)
    key.show()
    assert (key.valve_field.text(), key.limit_field.text()) == ("RELEASED", "HEALTHY")
    key.turn(True)
    assert bridge.sent == [{"type": "keyswitch_set", "id": "HS-321634", "on": True}]
    plant = build_plant()[1]
    assert apply_command(plant, bridge.sent[-1]).ok and plant.operator["HS-321634"] is True
    key.close()
