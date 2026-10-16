"""Exercise snapshots — `ureasim.engine.snapshot`.

The one property that matters: a plant restored from a snapshot runs, tick for tick, to the bit,
what the saved plant would have run. Pinned here on the assembled plant mid-transient, through
the JSON text and through a file, with the letdown's cache cleared so no hidden memory carries
the answer; then the refusals: a foreign class, a damaged document, a different model.
"""

from __future__ import annotations

import json

import pytest

from ureasim.engine import snapshot
from ureasim.engine.historian import flatten
from ureasim.engine.plant import build_plant
from ureasim.engine.scheduler import Scheduler
from ureasim.thermo import condensing_letdown


def _disturbed(ticks: int):
    """The plant, HV-322605 throttled and 329P006A stopped, ``ticks`` into the transient."""
    sch, plant = build_plant()
    s = Scheduler(sch, plant)
    plant.operator["HIC-322605"] = 45.0
    plant.loops["322E003"][0].p329p006a = False
    for _ in range(ticks):
        s.tick()
    return sch, s


def _run(sch, plant, ticks: int) -> list:
    s = Scheduler(sch, plant)
    return [flatten(s.tick().results) for _ in range(ticks)]


def test_a_restored_plant_replays_to_the_bit(tmp_path):
    """Saved 30 s into a transient, the plant and its restored copy then run 30 s more: every
    published value equal on every tick, through the text and through a file."""
    sch, s = _disturbed(300)
    text = snapshot.dumps(s.plant, note="HV-322605 45 %, tempered water lost")
    path = tmp_path / "exercise.json"
    snapshot.save(s.plant, str(path))
    original = _run(sch, s.plant, 300)
    for restored in (snapshot.loads(text, build_plant()[1]),
                     snapshot.load(str(path), build_plant()[1])):
        condensing_letdown._CACHE.clear()
        assert restored.clock.tick == 300
        assert _run(sch, restored, 300) == original


def test_shared_objects_stay_shared_and_values_exact():
    """An object reached twice comes back once; tuples, mapping proxies, non-text keys and
    non-finite floats come back as themselves."""
    _, plant = build_plant()
    plant.boundary["probe"] = {"inf": float("inf"), "t": (1.0, 2.5), (1, 2): "k"}
    plant.boundary["same"] = plant.boundary["probe"]
    back = snapshot.loads(snapshot.dumps(plant))
    assert back.boundary["same"] is back.boundary["probe"]
    assert back.boundary["probe"] == {"inf": float("inf"), "t": (1.0, 2.5), (1, 2): "k"}
    assert type(back.tears.inert_706_kmolh) is type(plant.tears.inert_706_kmolh)
    assert back.units["322R001"].t_nodes_c == plant.units["322R001"].t_nodes_c


def test_a_foreign_object_is_refused_on_save():
    _, plant = build_plant()
    plant.boundary["bad"] = object()
    with pytest.raises(snapshot.SnapshotError, match="cannot be saved"):
        snapshot.dumps(plant)


def test_a_damaged_or_foreign_document_is_refused():
    _, plant = build_plant()
    doc = json.loads(snapshot.dumps(plant))
    with pytest.raises(snapshot.SnapshotError, match="not a snapshot"):
        snapshot.loads("{not json")
    with pytest.raises(snapshot.SnapshotError, match="version"):
        snapshot.loads(json.dumps({**doc, "version": 99}))
    doc["state"]["a"]["clock"] = {"$o": "os:system", "$id": 999999, "a": {}}
    with pytest.raises(snapshot.SnapshotError, match="not a ureasim class"):
        snapshot.loads(json.dumps(doc))


def test_a_snapshot_from_a_different_model_is_refused_with_the_difference():
    """A unit the present model lacks, or an attribute renamed, names the first difference."""
    _, plant = build_plant()
    del plant.units["322E003"]
    with pytest.raises(snapshot.SnapshotError, match=r"plant\.units"):
        snapshot.loads(snapshot.dumps(plant), build_plant()[1])
    _, plant = build_plant()
    lp = plant.units["PT-329201"]
    object.__setattr__(lp, "p_old_bara", lp.p_syn_bara)
    with pytest.raises(snapshot.SnapshotError, match="PT-329201"):
        snapshot.loads(snapshot.dumps(plant), build_plant()[1])
