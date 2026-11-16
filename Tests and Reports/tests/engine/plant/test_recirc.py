"""The LP recirculation as `engine/plant/recirc.py` builds it: 323D001's level on the plant's seed.

What this pins
--------------
LI-323502 reads between LT-323502's taps (decision 219, As-Built §CXXXI.7), and ``taps = False`` is
V1's holdup over the drum's. The design holdup reads 50 % on both, so the plant's first tick from its
seed is the same to the bit on either law. After it the seed's own drift (B-94) reads 1.56 times as
large between the taps, and the plant parts from V1's law by the bound handoff B-156 holds open.
"""

from __future__ import annotations

from ureasim.data.unit_323e003 import D001_M_DES_KG
from ureasim.engine.historian import flatten
from ureasim.engine.packet import build_packet
from ureasim.engine.plant import build_plant
from ureasim.engine.scheduler import Scheduler


def _packet(s: Scheduler) -> dict:
    return flatten(build_packet(s.plant, s.results, s.tears_read, sim_mode="SLOW", t_wall=0.0))


def test_the_seeds_first_tick_is_the_same_on_either_law():
    """Process utility: a trainee who starts the plant from its seed sees the same first tick
    whichever law LI-323502 reads by, because the design holdup is half the vessel, at the taps'
    mid-point; only the seed's later drift tells the two apart."""
    taps, v1 = Scheduler(*build_plant()), Scheduler(*build_plant())
    v1.plant.units["323E003"].taps = False
    assert taps.plant.units["323E003"].taps
    taps.tick()
    v1.tick()
    assert _packet(taps) == _packet(v1)
    assert taps.results == v1.results
    assert taps.plant.units["323E003"].m_kg == v1.plant.units["323E003"].m_kg == D001_M_DES_KG
    assert taps.results["323E003"].level_pct == v1.results["323E003"].level_pct == 50.0
