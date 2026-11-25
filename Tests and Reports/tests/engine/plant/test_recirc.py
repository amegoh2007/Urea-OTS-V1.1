"""The LP recirculation as `engine/plant/recirc.py` builds it: 323D001's, 323D011's and 323C003's levels on the
plant's seed.

What this pins
--------------
LI-323502 reads between LT-323502's taps (decision 219, As-Built §CXXXI.7), and ``taps = False`` is
V1's holdup over the drum's. The design holdup reads 50 % on both, so the plant's first tick from its
seed is the same to the bit on either law. After it the seed's own drift (B-94) reads 1.56 times as
large between the taps, and the plant parts from V1's law within decision 230's bound by 600 s.

LI-323503 reads between LT-323503's taps (decision 233, As-Built §CXXXIV), 26.77 % at the design
holdup, and LIC-323503 is seeded on that reading, so the first tick is again the same to the bit
whichever law the tank reads by. Its drift reads 1.22 times as large, and decision 233 bounds the
part at 600 s at its own measured values.

LI-323501 reads between LT-323501's taps (decision 241, As-Built §CXXXV), the plant's 40 % at the
design holdup, and LIC-323501 is seeded there: the first tick differs from V1's law only in the
column's reading. Its drift reads 1.84 times as large, and decision 241 bounds the part at 600 s at
its own measured values.

LI-328503 reads between LT-328503's taps (decision 243, As-Built §CXXXVI), 70.83 % at V1's design
holdup, and LIC-328503 is seeded there: the first tick differs from V1's law only in 328C002's
reading and its loop's. Its drift reads 2.34 times as large, and the part at 600 s is within
decision 230's own bound.
"""

from __future__ import annotations

import dataclasses
import math
import re

import pytest

from ureasim.data.unit_323e003 import D001_M_DES_KG
from ureasim.data.unit_323c003 import C003_M_DES_KG, LT_323501_DES_PCT
from ureasim.data.unit_323e011 import D011_M_DES_KG, LT_323503_DES_PCT
from ureasim.data.unit_328c002 import C002_M_DES_KG, LT_328503_DES_PCT
from ureasim.data import unit_328c003 as hydrolyser_data
from ureasim.data.unit_328c004 import C004_M_DES_KG, LT_328505_DES_PCT
from ureasim.engine.historian import flatten
from ureasim.engine.packet import build_packet
from ureasim.engine.plant import build_plant
from ureasim.engine.scheduler import Scheduler
from ureasim.units.desorption.first_desorber import lic_328503
from ureasim.units.desorption.second_desorber import lic_328505
from ureasim.units.recirc.flash_condenser import lic_323503
from ureasim.units.recirc.rectifying_column import lic_323501


def _packet(s: Scheduler) -> dict:
    return flatten(build_packet(s.plant, s.results, s.tears_read, sim_mode="x1", t_wall=0.0))


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
#: the two boil-off flows at their measured ceiling, restated with the reactor ceiling's margin (decision 304,
#: measured 4.384e-3 on 323F010's; 2e-3 before decision 301), and again on decision 322's ejectors (measured
#: 4.438e-3 on 323F010's, a flow of a few kg/h; 4.4e-3 before).
SEED_BOUND_600S, SEED_BOUND_BOIL_600S = 6e-5, 4.5e-3

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
    above 1 in magnitude, the near-zero names left out, and 2e-3 on the two boil-off flows (4.4e-3 since decision 304,
    4.5e-3 since decision 322, 323F010's measured at 4.438e-3). Measured
    with 323D011, 323C003 and 328C002 between their taps on both sides: 4.88e-5, the holdup 0.0185 kg
    above V1's law (4.93e-5 before decision 243, 328C002 on V1's reading; 4.7e-5 and 0.0181 kg before
    decision 241, 323C003 on V1's reading; 5.7e-5, 1.9e-3 and 0.0240 kg
    before decision 233, 323D011 on V1's reading). With 328C003 between its taps (decision 246): 1.99e-5 (4.79e-5 before decision 301)
    and 0.0237 (0.0182 before decision 301) kg."""
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
    assert max(flows.values()) == pytest.approx(1.99e-5, abs=0.01e-5)
    m_taps, m_v1 = taps.plant.units["323E003"].m_kg, v1.plant.units["323E003"].m_kg
    assert m_taps - m_v1 == pytest.approx(0.0237, abs=1e-4)


def _v1_tank(s: Scheduler) -> Scheduler:
    """323D011 on V1's reading: the unit's law and LIC-323503 seeded on V1's 50 %."""
    s.plant.units["323E011"].taps = False
    pic, _, fic = s.plant.loops["323E011"]
    s.plant.loops["323E011"] = (pic, lic_323503(taps=False), fic)
    return s


def test_323d011s_first_tick_is_the_same_on_either_law():
    """Process utility: LIC-323503's set point is the design holdup's tap reading, 26.77 %, and its
    history is seeded there, so a trainee who starts from the seed sees the same first tick whichever
    law LI-323503 reads by; only the two readings of the one holdup differ."""
    taps, v1 = Scheduler(*build_plant()), _v1_tank(Scheduler(*build_plant()))
    taps.tick()
    v1.tick()
    assert taps.plant.units["323E011"].m_kg == v1.plant.units["323E011"].m_kg == D011_M_DES_KG
    assert taps.results["323E011"].level_pct == LT_323503_DES_PCT
    assert v1.results["323E011"].level_pct == 50.0
    mine, theirs = _state(taps), _state(v1)
    assert {k for k in mine if mine[k] != theirs.get(k)} == {
        "result.323E011.level_pct", "result.323E011.lic_pv_pct"}


#: Decision 233 (2026-11-16): 323D011's part from V1's law by 600 s, at its measured values; the boil-off's
#: restated at its value with 323C003 between its taps on both sides (decision 241; 4.2e-3 before),
#: and again with 328C003 between its taps (decision 246, measured 4.330e-3; 4.3e-3 before); the flows' restated
#: with the reactor ceiling's margin (decision 304, measured 3.292e-4 on 323E011's 718A; 3.2e-4 before decision 301).
D011_BOUND_600S, D011_BOUND_BOIL_600S = 3.3e-4, 4.4e-3


def test_323d011_parts_from_v1s_law_by_decision_233s_bound_in_ten_minutes():
    """Process utility: the seed's own drift (B-94) moves 323D011's holdup, LIC-323503 reads it 1.22
    times as large between the taps, and the draw it sets reaches 328D001 and 323E003. Decision 233
    bounds the part at 600 s as decision 230 scores it, the tank's two readings left out. Measured with
    323C003 between its taps on both sides: 3.01e-4, 4.24e-3 (324E001's boil-off), the holdup 0.0600 kg
    below V1's law (3.15e-4 (323E011's 718A), 4.16e-3 and 0.0595 kg before decision 241; 3.292e-4 (3.009e-4 before decision 301) and
    4.330e-3 with 328C003 between its taps, decision 246); with the reactor ceiling's margin
    (decision 301), 3.651e-3 on the boil-off and the holdup 0.0845 kg below V1's law."""
    taps, v1 = Scheduler(*build_plant()), _v1_tank(Scheduler(*build_plant()))
    for _ in range(6000):
        taps.tick()
        v1.tick()
    a, b = _state(taps), _state(v1)
    own = ("result.323E011.level_pct", "result.323E011.lic_pv_pct")
    rel = {k: abs(a[k] - b[k]) / abs(b[k]) for k in a
           if k in b and abs(b[k]) > 1.0 and not NEAR_ZERO.search(k) and k not in own}
    flows = {k: r for k, r in rel.items() if not BOIL.search(k)}
    boils = {k: r for k, r in rel.items() if BOIL.search(k)}
    assert max(flows.values()) <= D011_BOUND_600S, max(flows, key=flows.get)
    assert max(boils.values()) <= D011_BOUND_BOIL_600S, max(boils, key=boils.get)
    assert max(flows.values()) == pytest.approx(3.292e-4, abs=0.001e-4)
    m_taps, m_v1 = taps.plant.units["323E011"].m_kg, v1.plant.units["323E011"].m_kg
    assert m_taps - m_v1 == pytest.approx(-0.0845, abs=1e-4)


def _v1_column(s: Scheduler) -> Scheduler:
    """323C003 on V1's reading: the unit's law and LIC-323501 seeded on V1's 60 %."""
    s.plant.units["323C003"].taps = False
    tic, pic, _ = s.plant.loops["323C003"]
    s.plant.loops["323C003"] = (tic, pic, lic_323501(taps=False))
    return s


def test_323c003s_first_tick_is_the_same_on_either_law():
    """Process utility: LIC-323501's set point is the design holdup's tap reading, the plant's 40 %, and
    its history is seeded there, so a trainee who starts from the seed sees the same first tick whichever
    law LI-323501 reads by; only the column's reading differs."""
    taps, v1 = Scheduler(*build_plant()), _v1_column(Scheduler(*build_plant()))
    taps.tick()
    v1.tick()
    assert taps.plant.units["323C003"].m_kg == v1.plant.units["323C003"].m_kg == C003_M_DES_KG
    assert (taps.results["323C003"].level_pct, v1.results["323C003"].level_pct) == (
        LT_323501_DES_PCT, 60.0)
    mine, theirs = _state(taps), _state(v1)
    assert {k for k in mine if mine[k] != theirs.get(k)} == {"result.323C003.level_pct"}


#: Decision 241 (2026-11-16): 323C003's part from V1's law by 600 s, at its measured values: decision
#: 230's own bound on the flows, and 324E001's boil-off at its measured ceiling, restated with the reactor
#: ceiling's margin (decision 304, measured 2.406e-2; 1.6e-2 before decision 301).
C003_BOUND_600S, C003_BOUND_BOIL_600S = 6e-5, 2.5e-2


def test_323c003_parts_from_v1s_law_by_decision_241s_bound_in_ten_minutes():
    """Process utility: the seed's own drift (B-94) moves 323C003's holdup, LIC-323501 reads it 1.84
    times as large between the taps, and the drain it sets reaches 323F004 and on down the train.
    Decision 241 bounds the part at 600 s as decision 230 scores it, the column's reading left out.
    Measured with 328C002 between its taps on both sides: 4.843e-5 (323E011's 702), 1.582e-2 (324E001's
    boil-off), the holdup 0.0337 kg below V1's law (4.864e-5 and 1.579e-2 before decision 243). With
    328C003 between its taps (decision 246): 5.136e-5 (4.896e-5 before decision 301) and 2.406e-2 (1.587e-2 before decision 301), the
    holdup 0.0257 kg below (0.0337 before decision 301)."""
    taps, v1 = Scheduler(*build_plant()), _v1_column(Scheduler(*build_plant()))
    for _ in range(6000):
        taps.tick()
        v1.tick()
    a, b = _state(taps), _state(v1)
    rel = {k: abs(a[k] - b[k]) / abs(b[k]) for k in a
           if k in b and abs(b[k]) > 1.0 and not NEAR_ZERO.search(k)
           and k != "result.323C003.level_pct"}
    flows = {k: r for k, r in rel.items() if not BOIL.search(k)}
    boils = {k: r for k, r in rel.items() if BOIL.search(k)}
    assert max(flows.values()) <= C003_BOUND_600S, max(flows, key=flows.get)
    assert max(boils.values()) <= C003_BOUND_BOIL_600S, max(boils, key=boils.get)
    assert max(flows.values()) == pytest.approx(5.134e-5, abs=0.001e-5)   # 5.136e-5 before decision 322
    assert max(boils.values()) == pytest.approx(2.422e-2, abs=0.001e-2)   # 2.406e-2 before decision 322
    m_taps, m_v1 = taps.plant.units["323C003"].m_kg, v1.plant.units["323C003"].m_kg
    assert m_taps - m_v1 == pytest.approx(-0.0257, abs=1e-4)


def _v1_desorber(s: Scheduler) -> Scheduler:
    """328C002 on V1's reading: the unit's law and LIC-328503 seeded on V1's 50 %."""
    s.plant.units["328C002"].taps = False
    s.plant.loops["328C002"] = (lic_328503(taps=False),)
    return s


def test_328c002s_first_tick_is_the_same_on_either_law():
    """Process utility: LIC-328503's set point is V1's design holdup read between LT-328503's taps,
    70.83 %, and its history is seeded there, so a trainee who starts from the seed sees the same first
    tick whichever law LI-328503 reads by; only 328C002's reading and its loop's differ."""
    taps, v1 = Scheduler(*build_plant()), _v1_desorber(Scheduler(*build_plant()))
    taps.tick()
    v1.tick()
    assert taps.plant.units["328C002"].m_kg == v1.plant.units["328C002"].m_kg == C002_M_DES_KG
    assert (taps.results["328C002"].level_pct, v1.results["328C002"].level_pct) == (
        pytest.approx(LT_328503_DES_PCT, abs=1e-9), pytest.approx(50.0, abs=1e-9))
    mine, theirs = _state(taps), _state(v1)
    assert {k for k in mine if mine[k] != theirs.get(k)} == {
        "result.328C002.level_pct", "result.328C002.lic_pv_pct"}


def test_328c002_parts_from_v1s_law_by_decision_230s_bound_in_ten_minutes():
    """Process utility: the seed's own drift (B-94) moves 328C002's holdup, LIC-328503 reads it 2.34
    times as large between the taps, and the bottoms it sets reach 328C003 and 328C004. Decision 243
    keeps decision 230's bound at 600 s, 328C002's two readings left out. Measured with 328C004 between
    its taps on both sides: 1.688e-5 (AI-328701's conductivity), 6.44e-5 (324E001's boil-off), the
    holdup 0.0023 kg below V1's law (1.958e-5 and 6.63e-5 before decision 244); with 328C003 between its
    taps too (decision 246), 2.154e-5 (2.270e-5 before decision 301) and 2.84e-5 (9.96e-5 before decision 301), the holdup
    0.0017 kg below (0.0023 before decision 301)."""
    taps, v1 = Scheduler(*build_plant()), _v1_desorber(Scheduler(*build_plant()))
    for _ in range(6000):
        taps.tick()
        v1.tick()
    a, b = _state(taps), _state(v1)
    own = ("result.328C002.level_pct", "result.328C002.lic_pv_pct")
    rel = {k: abs(a[k] - b[k]) / abs(b[k]) for k in a
           if k in b and abs(b[k]) > 1.0 and not NEAR_ZERO.search(k) and k not in own}
    flows = {k: r for k, r in rel.items() if not BOIL.search(k)}
    boils = {k: r for k, r in rel.items() if BOIL.search(k)}
    assert max(flows.values()) <= SEED_BOUND_600S, max(flows, key=flows.get)
    assert max(boils.values()) <= SEED_BOUND_BOIL_600S, max(boils, key=boils.get)
    assert max(flows.values()) == pytest.approx(2.154e-5, abs=0.001e-5)
    assert max(boils.values()) == pytest.approx(2.05e-5, abs=0.01e-5)   # 2.84e-5 before decision 322
    m_taps, m_v1 = taps.plant.units["328C002"].m_kg, v1.plant.units["328C002"].m_kg
    assert m_taps - m_v1 == pytest.approx(-0.0017, abs=1e-4)


def _v1_second_desorber(s: Scheduler) -> Scheduler:
    """328C004 on V1's reading: the unit's law and LIC-328505 seeded on V1's 50 %."""
    s.plant.units["328C004"].taps = False
    s.plant.loops["328C004"][0].lic_328505 = lic_328505(taps=False)
    return s


def test_328c004s_first_tick_is_the_same_on_either_law():
    """Process utility: LIC-328505's set point is V1's design holdup read between LT-328505's taps,
    71.00 %, and its history is seeded there, so a trainee who starts from the seed sees the same first
    tick whichever law LI-328505 reads by; only 328C004's reading and its loop's differ."""
    taps, v1 = Scheduler(*build_plant()), _v1_second_desorber(Scheduler(*build_plant()))
    taps.tick()
    v1.tick()
    assert taps.plant.units["328C004"].m_kg == v1.plant.units["328C004"].m_kg == C004_M_DES_KG
    assert (taps.results["328C004"].level_pct, v1.results["328C004"].level_pct) == (
        pytest.approx(LT_328505_DES_PCT, abs=1e-9), pytest.approx(50.0, abs=1e-9))
    mine, theirs = _state(taps), _state(v1)
    assert {k for k in mine if mine[k] != theirs.get(k)} == {
        "result.328C004.level_pct", "result.328C004.lic_pv_pct"}


def test_328c004_parts_from_v1s_law_by_decision_230s_bound_in_ten_minutes():
    """Process utility: the seed's own drift (B-94) moves 328C004's holdup, LIC-328505 reads it 2.54
    times as large between the taps, and the bottoms it lets down reach 328E007. Decision 244 keeps
    decision 230's bound at 600 s, 328C004's two readings left out. Measured: 2.357e-5 (AI-328701's
    conductivity), 5.13e-7 (324E001's boil-off), the holdup 0.0005 kg below V1's law; with 328C003
    between its taps (decision 246) 2.309e-5 (1.815e-5 before decision 301), 2.77e-7 (1.26e-7 before decision 301) and 0.0024 kg (0.0037 before decision 301)."""
    taps, v1 = Scheduler(*build_plant()), _v1_second_desorber(Scheduler(*build_plant()))
    for _ in range(6000):
        taps.tick()
        v1.tick()
    a, b = _state(taps), _state(v1)
    own = ("result.328C004.level_pct", "result.328C004.lic_pv_pct")
    rel = {k: abs(a[k] - b[k]) / abs(b[k]) for k in a
           if k in b and abs(b[k]) > 1.0 and not NEAR_ZERO.search(k) and k not in own}
    flows = {k: r for k, r in rel.items() if not BOIL.search(k)}
    boils = {k: r for k, r in rel.items() if BOIL.search(k)}
    assert max(flows.values()) <= SEED_BOUND_600S, max(flows, key=flows.get)
    assert max(boils.values()) <= SEED_BOUND_BOIL_600S, max(boils, key=boils.get)
    assert max(flows.values()) == pytest.approx(2.309e-5, abs=0.001e-5)
    assert max(boils.values()) == pytest.approx(6.75e-6, abs=0.01e-6)   # 2.77e-7 before decision 322
    m_taps, m_v1 = taps.plant.units["328C004"].m_kg, v1.plant.units["328C004"].m_kg
    assert m_taps - m_v1 == pytest.approx(-0.0024, abs=1e-4)


#: Decision 246's bound on 328C003's part at 600 s, restated by the process engineer for the unit on
#: its measured value (2026-11-17), as decisions 233 and 241 did: AI-328701's conductivity, the
#: largest part, at 1.87e-4; every other state and flow inside decision 230's 6e-5.
SEED_BOUND_C003_600S = 2.0e-4


def _v1_hydrolyser(s: Scheduler) -> Scheduler:
    """328C003 on V1's reading. LIC-328504's seed is the same on either law (50 %)."""
    s.plant.units["328C003"].taps = False
    return s


def test_328c003s_first_tick_is_the_same_on_either_law():
    """Process utility: V1's design holdup is read as the drawing's N.L.L., mid-span between N5B and
    N5A, 50 %, V1's own reading, so the first tick differs only in the reading of the holdup the tick
    leaves, which LT-328504 shows 25.1 times as large."""
    taps, v1 = Scheduler(*build_plant()), _v1_hydrolyser(Scheduler(*build_plant()))
    taps.tick()
    v1.tick()
    assert taps.plant.units["328C003"].m_kg == v1.plant.units["328C003"].m_kg
    assert taps.results["328C003"].lic_pv_pct == v1.results["328C003"].lic_pv_pct == 50.0
    mine, theirs = _state(taps), _state(v1)
    assert {k for k in mine if mine[k] != theirs.get(k)} == {"result.328C003.level_pct"}


def test_328c003_parts_from_v1s_law_by_decision_246s_bound_in_ten_minutes():
    """Process utility: the seed's own drift (B-94) moves 328C003's holdup, LIC-328504 reads it 25.1
    times as large between the taps, and the letdown it strokes carries the change to 328C004 and
    328E007. Measured at 600 s, 328C003's reading left out: 1.894e-4 (1.867e-4 before decision 301) (AI-328701's conductivity, inside
    decision 246's 2e-4), 2.56e-5 the largest flow (747), 8.27e-5 (2.42e-4 before decision 301) (324E001's boil-off), the holdup
    0.071 kg below V1's law (0.070 before decision 301)."""
    taps, v1 = Scheduler(*build_plant()), _v1_hydrolyser(Scheduler(*build_plant()))
    for _ in range(6000):
        taps.tick()
        v1.tick()
    a, b = _state(taps), _state(v1)
    own = ("result.328C003.level_pct", "result.328C003.lic_pv_pct")
    rel = {k: abs(a[k] - b[k]) / abs(b[k]) for k in a
           if k in b and abs(b[k]) > 1.0 and not NEAR_ZERO.search(k) and k not in own}
    flows = {k: r for k, r in rel.items() if not BOIL.search(k)}
    boils = {k: r for k, r in rel.items() if BOIL.search(k)}
    ai = "result.328C004.ai_328701_us_cm"
    assert flows[ai] <= SEED_BOUND_C003_600S
    assert max(r for k, r in flows.items() if k != ai) <= SEED_BOUND_600S
    assert max(boils.values()) <= SEED_BOUND_BOIL_600S, max(boils, key=boils.get)
    assert flows[ai] == pytest.approx(1.894e-4, abs=0.001e-4)
    assert max(boils.values()) == pytest.approx(1.14e-4, abs=0.01e-4)   # 8.27e-5 before decision 322
    m_taps, m_v1 = taps.plant.units["328C003"].m_kg, v1.plant.units["328C003"].m_kg
    assert m_taps - m_v1 == pytest.approx(-0.071, abs=1e-3)
    assert hydrolyser_data.lt_328504_pct(m_v1) - 50.0 == pytest.approx(
        (m_v1 - hydrolyser_data.C003_M_DES_KG) / hydrolyser_data.LT_328504_SPAN_KG * 100.0, abs=1e-9)
