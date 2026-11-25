"""The rehearsal — `ureasim.engine.rehearsal` — the first tick of a plant, run on a copy of it.

Pinned: the plant is exactly as it was after its rehearsal (state, clock, tears); the copy carries the
plant's own clock, at the seed and part-way through a run; the packet built from it is the one the
plant's own next tick builds, to the last bit but its clock; and two rehearsals of one plant agree.
"""

from __future__ import annotations

import json

from ureasim.engine.packet import build_packet
from ureasim.engine.plant import build_plant
from ureasim.engine.rehearsal import Rehearsal, rehearse
from ureasim.engine.scheduler import Scheduler
from ureasim.engine.snapshot import encode_state


def _text(plant) -> str:
    return json.dumps(encode_state(plant), sort_keys=True)


def _packet(plant, results, tears_read) -> dict:
    return build_packet(plant, results, tears_read, sim_mode="x1", t_wall=0.0, health=None)


def _body(packet: dict) -> str:
    return json.dumps({k: v for k, v in packet.items() if k != "t_sim"}, sort_keys=True, default=repr)


def test_the_plant_is_exactly_as_it_was_after_its_rehearsal():
    schedule, plant = build_plant()
    before = _text(plant)
    r = rehearse(schedule, plant)
    assert isinstance(r, Rehearsal) and r.plant is not plant and r.results
    assert _text(plant) == before and plant.clock.tick == 0


def test_the_copy_carries_the_plants_own_clock_at_the_seed_and_part_way_through_a_run():
    schedule, plant = build_plant()
    assert rehearse(schedule, plant).plant.clock.tick == 0
    scheduler = Scheduler(schedule, plant)
    for _ in range(4):
        scheduler.tick()
    r = rehearse(schedule, plant)
    assert plant.clock.tick == 4 and r.plant.clock.tick == 4
    assert _packet(r.plant, r.results, r.tears_read)["t_sim"] == plant.clock.time_s


def test_the_rehearsed_packet_is_the_one_the_plants_own_next_tick_builds():
    """At the seed and 5 ticks in: the same outputs, to the last bit, whichever way they are got."""
    schedule, plant = build_plant()
    scheduler = Scheduler(schedule, plant)
    for ticks in (0, 5):
        for _ in range(ticks):
            scheduler.tick()
        r = rehearse(schedule, plant)
        shown = _packet(r.plant, r.results, r.tears_read)
        scheduler.tick()
        taken = _packet(plant, scheduler.results, scheduler.tears_read)
        assert _body(shown) == _body(taken), ticks
        assert taken["t_sim"] == shown["t_sim"] + 0.1


def test_two_rehearsals_of_one_plant_agree():
    schedule, plant = build_plant()
    a, b = rehearse(schedule, plant), rehearse(schedule, plant)
    assert _body(_packet(a.plant, a.results, a.tears_read)) == _body(_packet(b.plant, b.results, b.tears_read))
