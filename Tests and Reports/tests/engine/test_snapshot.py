"""Exercise snapshots — `ureasim.engine.snapshot`.

The one property that matters: a plant restored from a snapshot runs, tick for tick, to the bit,
what the saved plant would have run. Pinned here on the assembled plant mid-transient, through
the JSON text and through a file, with the letdown's cache cleared so no hidden memory carries
the answer; then the refusals: a foreign class, a damaged document, a different model, a
reference to an object the save does not hold. A save made before a piece of the model was removed
still loads, its retired state dropped (`data.retired_state`), and so does every shipped exercise; a
save made before the melt header was computed loads, its added state filled from the present model
and its boundary header handed to the computed one (decision 226), LV-324501A opening at the stroke
that passes the save's drain on the header it restores (decision 238).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ureasim.data import unit_335 as u335
from ureasim.data.faceplates import P002_DELIVERY_TAG
from ureasim.data.unit_328d003 import M744_DES_KGH
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


def test_a_save_that_fails_leaves_the_exercise_that_was_there(tmp_path):
    """The file was opened, and so emptied, before the plant was encoded: a refused save
    destroyed the exercise it was to replace."""
    path = tmp_path / "exercise.json"
    _, plant = build_plant()
    snapshot.save(plant, str(path))
    before = path.read_bytes()
    plant.boundary["bad"] = object()
    with pytest.raises(snapshot.SnapshotError):
        snapshot.save(plant, str(path))
    assert path.read_bytes() == before and [p.name for p in tmp_path.iterdir()] == ["exercise.json"]


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


#: The shipped exercises, the intro's LOAD list's fixed half (decision 171).
SCENARIOS = Path(__file__).resolve().parents[3] / "scenarios"
#: A shipped exercise's first tick against the header it adopts [bar]: the header solve's own
#: convergence; measured within 9.7e-11 on all six (As-Built §CXXVI.7).
PASSING_TICK1_BAR = 1e-9

#: The class path a snapshot names for the synthesis trips.
SYNTHESIS_TRIPS = "ureasim.engine.plant.synthesis_loop:SynthesisTrips"


def _objects(data, out):
    """Every tagged object in an encoded state, by its class path."""
    if isinstance(data, dict):
        if "$o" in data:
            out.setdefault(data["$o"], []).append(data)
        for v in data.values():
            _objects(v, out)
    elif isinstance(data, list):
        for v in data:
            _objects(v, out)
    return out


def _ids(data):
    """Every ``$id`` in an encoded state."""
    if isinstance(data, dict):
        own = [data["$id"]] if "$id" in data else []
        return own + [i for v in data.values() for i in _ids(v)]
    if isinstance(data, list):
        return [i for v in data for i in _ids(v)]
    return []


def test_a_save_holding_trip_22_2_loads_without_it():
    """Decision 189: a save made while the model had trip 22.2 — latched, as a save taken over the
    loop's old high-high would hold it — loads, the record dropped, the trips' shape the model's."""
    _, plant = build_plant()
    doc = json.loads(snapshot.dumps(plant))
    (trips,) = _objects(doc["state"], {})[SYNTHESIS_TRIPS]
    trips["a"]["i_22_2"] = {"$o": "ureasim.control.interlocks:BandedInterlock",
                            "$id": max(_ids(doc["state"])) + 1,
                            "a": {"live": True, "latched": True, "trip_at": 155.0,
                                  "reset_below": 148.0}}
    back = snapshot.loads(json.dumps(doc), build_plant()[1])
    syn = back.units["SYN-TRIPS"]
    assert not hasattr(syn, "i_22_2") and set(syn.latched) == {"21_2", "21_8", "21_10"}


#: The class paths a snapshot names for stage 2 and its loops.
SECOND_EVAPORATOR = "ureasim.units.evaporation.second_evaporator:SecondEvaporator"
SECOND_EVAPORATOR_LOOPS = "ureasim.units.evaporation.second_evaporator:SecondEvaporatorLoops"
MELT_HEADER = "ureasim.units.finishing.melt_header:MeltHeader"


def _before_the_header(plant, stroke=75.0, p_barg=3.6):
    """``plant``'s save as the model before decision 224 wrote it: no header valves, HIC-335602,
    header state or PIC-335201; the header a boundary value; LIC-324501's output LV-324501's
    stroke."""
    doc = json.loads(snapshot.dumps(plant))
    state = doc["state"]
    operator = state["a"]["operator"]["$d"]
    for key in ("GRANULATION-HEADERS", "HIC-335602"):
        del operator[key]
    state["a"]["boundary"]["$d"]["PIC-335201.barg"] = p_barg
    objects = _objects(state, {})
    (unit,) = objects[SECOND_EVAPORATOR]
    for key in ("ac4_header", "header"):
        del unit["a"][key]
    (loops,) = objects[SECOND_EVAPORATOR_LOOPS]
    del loops["a"]["header"]
    loops["a"]["level"]["a"]["op"] = stroke
    return json.dumps(doc)


def test_a_save_made_before_the_melt_header_loads_on_the_computed_one():
    """Decision 226: the save's load, its drain on V1's selector at the save's 75 % stroke, 98.65 %
    of PFD 402, brings ten valves online, whose header passing it stands at 3.406 bar g,
    PIC-335201's history on it; LIC-324501's output is the 30.31 % whose E1 is that header;
    HIC-335602 takes its seed and the boundary header is gone. Decision 238: PIC-335201's output and
    LV-324501A's position stand at the 78.21 % that passes the load at that header (the save's 75 %
    before it), and the header holds on the first tick; the plant then runs."""
    _, plant = build_plant()
    back = snapshot.loads(_before_the_header(plant), build_plant()[1])
    loops, unit = back.loops["324E003"][0], back.units["324E003"]
    p = pytest.approx(3.4063, abs=1e-4)
    assert loops.header.op == pytest.approx(78.2055, abs=1e-4)
    assert loops.level.op == pytest.approx(30.3138, abs=1e-4)
    assert unit.header.lv_a_position_pct == loops.header.op
    assert (loops.header.pv, loops.header.pv1, loops.header.pv2, unit.header.p_barg) == (p, p, p, p)
    assert loops.header.sp == p and unit.ac4_header is True and loops.header.mode == "CAS"
    assert (back.operator["GRANULATION-HEADERS"], back.operator["HIC-335602"]) == (10, 0.0)
    assert "PIC-335201.barg" not in back.boundary
    adopted = unit.header.p_barg
    sch, _ = build_plant()
    s = Scheduler(sch, back)
    assert s.tick().results["324E003"].header.p_barg == pytest.approx(adopted, abs=1e-9)
    for _ in range(9):
        s.tick()


def _before_the_positioner(plant, op=77.0, mode=None, pumps=True):
    """``plant``'s save as decision 224's model wrote it: PIC-335201's output ``op``, no position."""
    doc = json.loads(snapshot.dumps(plant))
    doc["state"]["a"]["operator"]["$d"]["335P001"] = pumps
    objects = _objects(doc["state"], {})
    (header,) = objects[MELT_HEADER]
    del header["a"]["lv_a_position_pct"]
    (loops,) = objects[SECOND_EVAPORATOR_LOOPS]
    loops["a"]["header"]["a"]["op"] = op
    if mode is not None:
        loops["a"]["header"]["a"]["mode"] = mode
    return json.dumps(doc)


def test_a_save_made_before_the_positioner_opens_the_valve_on_the_headers_drain():
    """Decisions 236 and 238: a save made on decision 224's header holds PIC-335201's output, here
    77 %, and no position for LV-324501A, and is refused as it stands; on load PIC-335201's output
    and the position stand at the stroke that passes what the ten valves take at the saved 3.5 bar g,
    the design's 79.09 % to the bit, and the header holds on the first tick (before decision 238 the
    valve stood on the save's 77 %)."""
    _, plant = build_plant()
    text = _before_the_positioner(plant)
    with pytest.raises(snapshot.SnapshotError):
        snapshot.check_compatible(snapshot.decode_state(json.loads(text)["state"]), build_plant()[1])
    back = snapshot.loads(text, build_plant()[1])
    assert (back.units["324E003"].header.lv_a_position_pct, back.loops["324E003"][0].header.op) == (
        u335.LV_324501A_HEADER_OP_DES_PCT, u335.LV_324501A_HEADER_OP_DES_PCT)
    sch, _ = build_plant()
    s = Scheduler(sch, back)
    assert s.tick().results["324E003"].header.p_barg == pytest.approx(3.5, abs=1e-9)
    for _ in range(9):
        s.tick()


def test_a_save_made_before_the_positioner_in_man_keeps_its_output():
    """Decision 238: PIC-335201 in MAN in the save, its 77 % the operator's: LV-324501A stands on it
    as saved, PIC-335201 still in MAN."""
    _, plant = build_plant()
    back = snapshot.loads(_before_the_positioner(plant, mode="MAN"), build_plant()[1])
    loops = back.loops["324E003"][0]
    assert back.units["324E003"].header.lv_a_position_pct == 77.0 == loops.header.op
    assert loops.header.mode == "MAN"


def test_a_save_made_before_the_positioner_with_both_pumps_stopped_keeps_its_output():
    """Decision 238: 335P001A and B both stopped in the save, PIC-335201's 77 % the loop's own, not a
    drain: LV-324501A stands on it as saved."""
    _, plant = build_plant()
    back = snapshot.loads(_before_the_positioner(plant, pumps=False), build_plant()[1])
    assert back.operator["335P001"] is False
    assert back.units["324E003"].header.lv_a_position_pct == 77.0 == back.loops["324E003"][0].header.op


def test_a_save_made_while_lv_324501a_travels_keeps_its_position_and_replays():
    """Decision 236: saved 0.5 s after an eleventh header valve came online, LV-324501A stands
    1.31 % behind PIC-335201's output; restored, the position and the output come back as saved,
    and the header then replays the saved plant's to the bit."""
    sch, plant = build_plant()
    s = Scheduler(sch, plant)
    s.tick()
    plant.operator["GRANULATION-HEADERS"] = 11
    for _ in range(5):
        s.tick()
    saved = (plant.units["324E003"].header.lv_a_position_pct, plant.loops["324E003"][0].header.op)
    assert saved[1] - saved[0] == pytest.approx(1.3109, abs=1e-4)
    back = snapshot.loads(snapshot.dumps(plant), build_plant()[1])
    assert (back.units["324E003"].header.lv_a_position_pct,
            back.loops["324E003"][0].header.op) == saved
    runs = []
    for p in (plant, back):
        condensing_letdown._CACHE.clear()
        sc = Scheduler(sch, p)
        runs.append([vars(sc.tick().results["324E003"].header).copy() for _ in range(100)])
    assert runs[0] == runs[1]


def test_a_restored_exercise_stops_on_the_limit_the_model_holds_now(monkeypatch):
    """Decision 217: the four AC4 low-level stops read their L2 from `data.low_level_stops` on every
    tick, so a save carries each stop's switch, not its stand-in. Restored after the limit changes
    (here LT-328501's raised to 99 %, above the drum's design level), 328P002 stops on the new
    limit on the first tick; the others, at their stand-in, run on."""
    from ureasim.units.desorption import reflux_drum
    sch, plant = build_plant()
    text = snapshot.dumps(plant)
    monkeypatch.setattr(reflux_drum, "L2_PCT", {"LT-328501": 99.0})
    back = snapshot.loads(text, build_plant()[1])
    Scheduler(sch, back).tick()
    assert back.units["328D001"].p002_stopped
    assert not (back.units["328C002"].p006_stopped or back.units["328C004"].p007_stopped
                or back.units["324E003"].p001_stopped)


def test_a_reference_to_an_object_the_save_does_not_hold_is_refused():
    _, plant = build_plant()
    doc = json.loads(snapshot.dumps(plant))
    doc["state"]["a"]["clock"] = {"$r": 999999}
    with pytest.raises(snapshot.SnapshotError, match="refers to object 999999"):
        snapshot.loads(json.dumps(doc))


@pytest.mark.parametrize("path", sorted(SCENARIOS.glob("*.json")), ids=lambda p: p.stem)
def test_every_shipped_exercise_loads_and_holds_no_retired_state(path):
    """The six shipped exercises carry no trip 22.2 record (cut from them on 2026-11-12) and load on
    the present model. Saved before decision 212, each lacks 322P002's field-set delivery and loads it
    from the seed, the PFD's 744; saved before decision 228, each lacks PC35's trips and loads them
    healthy."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    (trips,) = _objects(doc["state"], {})[SYNTHESIS_TRIPS]
    assert "i_22_2" not in trips["a"]
    assert P002_DELIVERY_TAG not in path.read_text(encoding="utf-8")
    back = snapshot.load(str(path), build_plant()[1])
    assert set(back.units["SYN-TRIPS"].latched) == {"21_2", "21_8", "21_10"}
    assert back.operator[P002_DELIVERY_TAG] == M744_DES_KGH
    assert back.units["335-TRIPS"].actions.p002_permit and not back.operator["HS-335201A"]


@pytest.mark.parametrize("path", sorted(SCENARIOS.glob("*.json")), ids=lambda p: p.stem)
def test_every_shipped_exercise_runs_trip_21_2_on_the_sheets_timers(path):
    """Decision 229: a save carries its timers, so the six shipped exercises were moved onto PC21.5.1's
    5:0 and 15:0 with the seed; each restores them settled and holds 21.2's flag on its first tick."""
    from ureasim.data.unit_322_loop import TRIP_21_2_P001_TD_S, TRIP_21_2_PUMPS_TD_S
    back = snapshot.load(str(path), build_plant()[1])
    u = back.units["SYN-TRIPS"].unit21
    assert (TRIP_21_2_PUMPS_TD_S, TRIP_21_2_P001_TD_S) == (300.0, 900.0)
    assert ((u.td_pumps_s, u.t_pumps.td_s, u.t_pumps.elapsed_s, u.td_p001_s, u.t_p001.td_s,
             u.t_p001.elapsed_s) == (300.0,) * 3 + (900.0,) * 3)
    Scheduler(build_plant()[0], back).tick()
    assert not back.units["SYN-TRIPS"].trip_21_2


@pytest.mark.parametrize("path", sorted(SCENARIOS.glob("*.json")), ids=lambda p: p.stem)
def test_every_shipped_exercise_opens_on_the_header_it_restores(path):
    """Decision 238: each shipped exercise, saved before decision 224, opens LV-324501A at the stroke
    that passes its drain at the header it adopts, and the first tick's header stands on that header
    (decision 226's kept stroke dipped it 0.10 to 0.45 bar, As-Built §CXXVI.4)."""
    back = snapshot.load(str(path), build_plant()[1])
    adopted = back.units["324E003"].header.p_barg
    sch, _ = build_plant()
    s = Scheduler(sch, back)
    assert s.tick().results["324E003"].header.p_barg == pytest.approx(adopted, abs=PASSING_TICK1_BAR)
