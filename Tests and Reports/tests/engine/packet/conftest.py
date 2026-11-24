"""The plant a packet test reads: the design seed after ten ticks, and its packet."""

from __future__ import annotations

import pytest

from ureasim.engine.packet import build_packet
from ureasim.engine.packet._common import Tick
from ureasim.engine.plant import build_plant
from ureasim.engine.scheduler import Scheduler


class Ran:
    """A scheduler after some ticks, with its packet and the packet context."""

    def __init__(self, scheduler: Scheduler) -> None:
        self.scheduler = scheduler
        self.plant = scheduler.plant
        self.results = scheduler.results
        self.tick = Tick(self.plant, self.results, scheduler.tears_read)
        self.packet = build_packet(self.plant, self.results, scheduler.tears_read,
                                   sim_mode="x1", t_wall=1.0e9, health={"ok": True})


def run(ticks: int = 10, setup=None) -> Ran:
    """The design plant, ``setup(plant)`` applied, ``ticks`` ticks on."""
    sch, plant = build_plant()
    if setup is not None:
        setup(plant)
    s = Scheduler(sch, plant)
    for _ in range(ticks):
        s.tick()
    return Ran(s)


@pytest.fixture(scope="session")
def design() -> Ran:
    return run()
