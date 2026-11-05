"""The first tick of a plant, rehearsed on a twin, so a console has a packet to show before the plant steps.

Plant equipment modelled
------------------------
None. The module steps nothing of the plant's own; it runs the scheduler once on a copy of it.

Reference documents
-------------------
* ``project.md`` decision 169 (handoff A-27): a reset or an exercise load made while the plant is held
  leaves the console a packet to show.
* ``ureasim/engine/scheduler.py`` (the tick), ``ureasim/engine/snapshot.py`` (the plant's state as
  data, which is how the twin is made) and ``ureasim/engine/packet`` (what a console draws).
* CLAUDE.md section 4a: the engine owns the plant and publishes it; a console renders what it is sent.

Equations
---------
None.

Process utility
---------------
A packet is built from the results of a tick: the outputs of every unit, which a restored or freshly
seeded plant has not produced yet. Until its first tick the engine would publish nothing, and a console
that gets nothing for five seconds is right to read the link as dead (`ureasim.hmi.bridge`). So an
instructor who resets the plant, or loads an exercise, while it is frozen would see every indicator go
to ``--`` and the link drop, with the plant sitting exactly where the instructor put it.

The rehearsal gives the console that first look without moving the plant. The plant's state is copied
(encoded and decoded, as an exercise save and restore do), the scheduler ticks the copy once, and the
copy's clock is put back to the plant's, so the packet carries the plant's own time. The plant itself is
never ticked: its clock, its tears, its controllers and its historian are as they were, and the tick the
operator releases later is the very computation the rehearsal ran, so the packet it publishes is the
rehearsal's own to the last bit (a test holds the two equal). What the console shows is therefore the
plant's first tick, one step ahead of its state, labelled with the plant's time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ureasim.engine.schedule import Schedule
from ureasim.engine.scheduler import Scheduler
from ureasim.engine.snapshot import decode_state, encode_state
from ureasim.engine.state import PlantState

__all__ = ["Rehearsal", "rehearse"]


@dataclass(frozen=True)
class Rehearsal:
    """What a packet is built from: a plant state, the results of the tick that made it and the tears
    that tick read. ``plant`` is the twin after its one tick, its clock put back to the real plant's."""

    plant: PlantState
    results: dict
    tears_read: Any


def rehearse(schedule: Schedule, plant: PlantState) -> Rehearsal:
    """Tick a copy of ``plant`` once and return what a packet needs, leaving ``plant`` as it was.

    Process utility
    ---------------
    The console's first look at a plant that has not stepped since it was reset or restored. The copy
    is made the way an exercise is restored, so it differs from the plant in nothing the tick reads.
    """
    twin = decode_state(encode_state(plant))
    scheduler = Scheduler(schedule, twin)
    scheduler.tick()
    twin.clock.tick = plant.clock.tick          # the plant has not moved: it shows its own time
    return Rehearsal(twin, scheduler.results, scheduler.tears_read)
