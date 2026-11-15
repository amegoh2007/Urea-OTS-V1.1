"""The pump faceplate — `ureasim.hmi.faceplates.pump`.

Pinned: exactly one of START and STOP is live; each sends an explicit run, with the command the
pump's row names (decision 222: the auxiliary pairs send ``aux_pump_toggle`` with the tag as their
id, and every icon that opens the faceplate drives its machine on the engine); the interlock line
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


def test_an_auxiliary_pair_sends_its_own_command_and_reads_n_a(bridge):
    """Decision 222: 323P001A's faceplate shows the packet's PUMPS state and sends V1's
    ``aux_pump_toggle`` with no mode; the interlock line reads n/a, as V1's did."""
    pump = {"t": "pump", "tag": "323P001A", "bind": "PUMPS.323P001A", "id": "323P001A"}
    face = PumpFaceplate(bridge, pump)
    face.show()
    assert face.status_field.text() == "RUNNING" and face.interlock_field.text() == "n/a"
    face.stop_button.click()
    assert bridge.sent[-1] == {"type": "aux_pump_toggle", "id": "323P001A", "on": False}
    face.close()


def test_a_pair_held_by_its_low_level_stop_reads_stopped_and_can_still_be_stopped(bridge):
    """Decision 217: AC4 holds 328P002A off with its command on. The status reads the
    feedback; STOP stays live, so the operator can keep the pair from running again."""
    pump = {"t": "pump", "tag": "328P002A", "bind": "PUMPS.328P002A", "id": "328P002A"}
    face = PumpFaceplate(bridge, pump)
    bridge.publish({**bridge.latest, "PUMPS": {"328P002A": {"on": False, "cmd": True, "mode": "AUTO"}}})
    face.show()
    assert face.status_field.text() == "STOPPED (INTERLOCK)"
    assert face.stop_button.isEnabled() and not face.start_button.isEnabled()
    face.close()


def test_every_icon_that_opens_the_faceplate_drives_its_machine():
    """Each bound pump icon's command, sent with its id, stops and starts the machine on the
    engine, and the packet path the icon reads follows it."""
    from ureasim.data.faceplates import PUMP_COMMANDS
    from ureasim.data.screen_layout import OVERLAYS
    from ureasim.engine.command import apply_command
    from ureasim.engine.packet import build_packet
    from ureasim.engine.plant import build_plant
    from ureasim.engine.scheduler import Scheduler
    from ureasim.hmi.state_access import get_path

    icons = [e for els in OVERLAYS.values() for e in els
             if e["t"] == "pump" and e.get("bind") and e.get("id")]
    assert sorted(e["tag"] for e in icons) == sorted(PUMP_COMMANDS)
    sch, plant = build_plant()
    s = Scheduler(sch, plant)
    s.tick()
    for e in icons:
        for on in (False, True):
            assert apply_command(plant, {"type": PUMP_COMMANDS[e["tag"]], "id": e["id"],
                                         "on": on}).ok, e["tag"]
            pkt = build_packet(plant, s.results, s.tears_read, sim_mode="SLOW", t_wall=0.0)
            assert bool(get_path(pkt, e["bind"])["on"]) is on, (e["tag"], on)
