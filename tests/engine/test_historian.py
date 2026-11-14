"""The process historian on the assembled plant — `ureasim.engine.historian`.

V1's rings, sampling and queries are proven ``==`` in `tests/equivalence/test_historian_
equivalence.py`. This file pins what V1.1 adds: the walk over a tick's result objects, the
omission of composition vectors, and sampling on the plant clock whatever the pacing.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from ureasim.engine.historian import Historian, flatten
from ureasim.engine.plant import build_plant
from ureasim.engine.scheduler import Scheduler


@dataclass(frozen=True)
class _Inner:
    level_pct: float
    tripped: bool


@dataclass(frozen=True)
class _Result:
    p_bara: float
    nodes: tuple
    inner: _Inner
    comp_kmolh: dict
    label: str


def test_a_result_object_flattens_by_field_and_index():
    """Fields and tuple elements become paths, booleans 0 / 1, text is not a trend; a mapping
    keyed by species is a stream table and is left out."""
    r = _Result(140.7, (183.0, 182.5), _Inner(80.0, True), {"NH3": 1.0, "CO2": 2.0}, "x")
    assert flatten({"PT-329201": r}) == {
        "PT-329201.p_bara": 140.7, "PT-329201.nodes.0": 183.0, "PT-329201.nodes.1": 182.5,
        "PT-329201.inner.level_pct": 80.0, "PT-329201.inner.tripped": 1.0}


def test_the_plant_is_sampled_on_plant_time():
    """Two minutes of the assembled plant: the fast ring takes one sample a plant second, 120 of
    them, 760 paths each once the composition vectors are left out (801 with B-90's analysers, 831
    with unit 335's dosing and 708's temperature, session 55, 865 with the computed melt header,
    decision 224); PT-329201 trends at its
    design. A mapping that mixes species with anything else — 322C001's bed uptakes and their
    temperature rise — is an instrument and is kept."""
    sch, plant = build_plant()
    s = Scheduler(sch, plant)
    hist = Historian()
    for _ in range(1200):
        rep = s.tick()
        hist.maybe_sample(rep.results, plant.clock.time_s, 0.0)
    fast = hist.stats()["fast"]
    assert fast["samples"] == 120 and 700 <= fast["paths"] <= 900
    q = hist.query(["PT-329201.p_syn_bara", "322E003.sump.held_kg"], 120.0)
    assert q["missing"] == [] and q["ring"] == "fast"
    assert q["series"]["PT-329201.p_syn_bara"][-1] == pytest.approx(140.7, abs=1e-3)
    assert set(q["series"]["322E003.sump.held_kg"]) == {0.0}
    assert "323C003.w.NH3" not in hist.paths() and "322C001.beds.abs_up.dT" in hist.paths()
