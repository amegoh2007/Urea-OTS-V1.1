"""The LP recirculation as `engine/plant/recirc.py` builds it: 323D001's level on the plant's seed.

What this pins
--------------
LI-323502 reads between LT-323502's taps (decision 219, As-Built §CXXXI.7), and ``taps = False`` is
V1's holdup over the drum's. The design holdup reads 50 % on both, so the plant's first tick from its
seed is the same to the bit on either law. After it the seed's own drift (B-94) reads 1.56 times as
large between the taps, and the plant parts from V1's law within decision 230's bound by 600 s.
"""

from __future__ import annotations

import dataclasses
import math
import re

import pytest

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


#: Decision 230 (2026-11-16, the process engineer's choice on B-156): how far the plant may part
#: from V1's law by 600 s from its seed, relative, on every state and flow above 1 in magnitude;
#: the two boil-off flows at their measured ceiling.
SEED_BOUND_600S, SEED_BOUND_BOIL_600S = 6e-5, 2e-3

#: The names that carry a rate of change, a residual, a relaxation, a lag, a controller's memory or a
#: closure: values that sit near zero, where a relative move says nothing (As-Built §CXXXI.7).
NEAR_ZERO = re.compile(r"dm_|residual|relax|_net|uncond|q_net|closure|err|integral|\.pv1|\.pv2|lag", re.I)
#: The two boil-off flows, a few kg/h, held to their own bound (decision 230).
BOIL = re.compile(r"boil", re.I)


def _floats(obj, path: str, out: dict, depth: int = 0) -> None:
    """Every finite number reachable from a unit or a result, unrounded, keyed by its path."""
    if depth > 6 or obj is None or isinstance(obj, (bool, str)):
        return
    if isinstance(obj, (int, float)):
        if math.isfinite(obj):
            out[path] = float(obj)
        return
    if isinstance(obj, dict):
        items = obj.items()
    elif isinstance(obj, (list, tuple)):
        items = enumerate(obj)
    elif dataclasses.is_dataclass(obj):
        items = ((f.name, getattr(obj, f.name)) for f in dataclasses.fields(obj))
    else:
        items = getattr(obj, "__dict__", {}).items()
    for key, value in items:
        _floats(value, f"{path}.{key}", out, depth + 1)


def _state(s: Scheduler) -> dict:
    out: dict = {}
    for name, unit in s.plant.units.items():
        _floats(unit, f"unit.{name}", out)
    for name, result in s.results.items():
        _floats(result, f"result.{name}", out)
    return out


def test_the_seed_parts_from_v1s_law_by_decision_230s_bound_in_ten_minutes():
    """Process utility: the seed is not a fixed point (B-94); 323D001's holdup drifts on its own and
    LIC-323502 reads that drift 1.56 times as large between the taps, so the plant parts from V1's law
    after its first tick. Decision 230 bounds the part at 600 s: 6e-5 relative on every state and flow
    above 1 in magnitude, the near-zero names left out, and 2e-3 on the two boil-off flows. Measured:
    5.7e-5 (323F004's holdup and its 319), 1.9e-3 (324E001's boil-off)."""
    taps, v1 = Scheduler(*build_plant()), Scheduler(*build_plant())
    v1.plant.units["323E003"].taps = False
    for _ in range(6000):
        taps.tick()
        v1.tick()
    a, b = _state(taps), _state(v1)
    rel = {k: abs(a[k] - b[k]) / abs(b[k]) for k in a
           if k in b and abs(b[k]) > 1.0 and not NEAR_ZERO.search(k)}
    flows = {k: r for k, r in rel.items() if not BOIL.search(k)}
    boils = {k: r for k, r in rel.items() if BOIL.search(k)}
    assert max(flows.values()) <= SEED_BOUND_600S, max(flows, key=flows.get)
    assert max(boils.values()) <= SEED_BOUND_BOIL_600S, max(boils, key=boils.get)
    assert max(flows.values()) == pytest.approx(5.69e-5, abs=0.01e-5)
    m_taps, m_v1 = taps.plant.units["323E003"].m_kg, v1.plant.units["323E003"].m_kg
    assert m_taps - m_v1 == pytest.approx(0.0240, abs=1e-4)
