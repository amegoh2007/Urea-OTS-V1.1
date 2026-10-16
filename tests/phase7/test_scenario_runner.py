"""Smoke tests of the Phase 7 runner — the scenarios, the drivers, the comparison.

Pinned: every scenario is well formed and every path it samples resolves in the rewrite's packet;
the rewrite's driver runs a shortened procedure, holds the design and returns a whole record; the
ringing watch flags a ring and passes a ramp; Smith's two-point method recovers a known
first-order-plus-dead-time step; the comparison pairs two records by time; and V1's driver runs in
its own process through the command line when V1's source tree is on this machine.
"""

from __future__ import annotations

import dataclasses
import json
import math
import subprocess
import sys

import pytest

from tests.equivalence.v1_loader import v1_available
from tests.phase7 import compare as cmpmod
from tests.phase7.drivers import COLD_P0_BARA, _Watch, flatten, run_port, smith_foptd
from tests.phase7.run import ROOT
from tests.phase7.scenarios import CORE_TAGS, DT, SCENARIOS, WATCHES, disturbance_at


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_every_scenario_is_well_formed(name):
    sc = SCENARIOS[name]
    assert sc.name == name and sc.sample_s >= DT
    assert sc.tags or name == "steady_state"            # empty: every leaf of the packet
    assert all(0.0 <= t < sc.duration_s for t, _ in sc.script)
    times = [t for t, _ in sc.disturbance or ()]
    assert times == sorted(times)


def test_the_disturbance_is_a_step_schedule():
    sc = SCENARIOS["hpcc_rupture"]
    assert disturbance_at(sc, 0.0) == 0.0
    assert disturbance_at(sc, 599.9) == 0.0
    assert disturbance_at(sc, 600.0) == 2500.0
    assert disturbance_at(sc, 3599.0) == 40000.0


def test_every_sampled_path_resolves_in_the_rewrites_packet():
    from ureasim.engine.packet import build_packet
    from ureasim.engine.plant import build_plant
    from ureasim.engine.scheduler import Scheduler
    sched = Scheduler(*build_plant())
    sched.tick()
    flat = flatten(build_packet(sched.plant, sched.results, sched.tears_read, sim_mode="SLOW",
                                t_wall=0.0))
    assert [p for p in CORE_TAGS if p not in flat] == []


def test_the_rewrites_driver_holds_the_design_through_a_short_procedure():
    sc = dataclasses.replace(SCENARIOS["vacuum_break"], duration_s=3.0, sample_s=1.0)
    rec = run_port(sc)
    assert rec["side"] == "port" and rec["t"] == [1.0, 2.0, 3.0]
    assert rec["values"][cmpmod.PT_329201] == [140.7, 140.7, 140.7]
    assert rec["trips"] == {} and rec["commands"] == []
    assert set(rec["watch"]) == set(WATCHES)
    assert rec["stopped"] == {"why": "duration", "t_s": 3.0}


def test_the_steady_state_samples_every_leaf_of_the_packet():
    """An empty tag list records every numeric and boolean leaf, each aligned with the times."""
    sc = dataclasses.replace(SCENARIOS["steady_state"], duration_s=2.0, sample_s=1.0)
    rec = run_port(sc)
    assert len(rec["values"]) > 1000 and set(CORE_TAGS) <= set(rec["values"])
    assert all(len(v) == 2 for v in rec["values"].values())
    assert rec["values"][cmpmod.PT_329201] == [140.7, 140.7]


def test_the_steady_table_sorts_agreement_from_difference():
    v1 = _record({"a": [1.0, 2.0, 100.0], "b": [5.0, 5.0, 5.0], "z": [0.0, 0.0, 0.0],
                  "f": [True, True, True], "only": [1.0, 1.0, 1.0]}, {}, "v1")
    port = _record({"a": [1.0, 2.0, 100.5], "b": [5.0, 5.0, 5.2], "z": [0.0, 0.0, 0.0005],
                    "f": [True, True, False], "new": [1.0, 1.0, 1.0]}, {}, "port")
    st = cmpmod.compare("steady_state", v1, port)["steady"]
    rows = {r["path"]: r for r in st["rows"]}
    assert rows["a"]["agree"] and rows["z"]["agree"] and not rows["b"]["agree"]
    assert rows["b"]["rel"] == pytest.approx(0.04) and rows["b"]["port_drift"] == pytest.approx(0.2)
    assert st["flags"] == [{"path": "f", "v1": True, "port": False}]
    assert (st["v1_only"], st["port_only"], st["n_agree"], st["n_compared"]) == (
        ["only"], ["new"], 2, 3)
    assert "| b | 5.0000 | 5.2000 |" in cmpmod.report_markdown(
        cmpmod.compare("steady_state", v1, port))


def test_the_watch_flags_a_ring_and_passes_a_ramp():
    ring, ramp = _Watch(), _Watch()
    for k in range(300):
        ring.add(3.7 + (0.05 if k % 2 else -0.05))
        ramp.add(3.7 + 0.002 * k)
    assert ring.result()["ringing_windows"] == 3 and ring.result()["first_ringing_s"] == 0.0
    assert ramp.result()["ringing_windows"] == 0 and ramp.result()["first_ringing_s"] is None


def test_smiths_method_recovers_a_known_step():
    tau, td, span = 3200.0, 400.0, 135.0
    t = [30.0 * i for i in range(1, 801)]
    p = [COLD_P0_BARA + (span * (1.0 - math.exp(-(ti - td) / tau)) if ti > td else 0.0)
         for ti in t]
    fit = smith_foptd(t, p, COLD_P0_BARA)
    assert fit["tau_s"] == pytest.approx(tau, rel=0.02)
    assert fit["td_s"] == pytest.approx(td, abs=40.0)
    assert fit["p_final"] == pytest.approx(COLD_P0_BARA + span, rel=1e-3)


def _record(values, trips, side):
    w = {"env": [], "max_reversals_10s": 0, "p2p_at_max": 0.0, "max_p2p_10s": 0.0,
         "ringing_windows": 0, "first_ringing_s": None}
    return {"side": side, "t": [1.0, 2.0, 3.0], "values": values, "trips": trips,
            "commands": [], "watch": {"PT-329201 [bar a]": w},
            "stopped": {"why": "duration", "t_s": 3.0}, "ms_per_tick": 1.0}


def test_the_comparison_pairs_the_two_records_by_time():
    v1 = _record({"a": [1.0, 2.0, 3.0], "f": [False, True, True]}, {"22_2": 2.0}, "v1")
    port = _record({"a": [1.0, 2.5, 3.0], "f": [False, False, True]}, {"22_2": 2.5}, "port")
    out = cmpmod.compare("trip_22_2", v1, port)
    a = next(r for r in out["paths"] if r["path"] == "a")
    assert (a["max_gap"], a["max_gap_t_s"], a["v1_last"], a["port_last"]) == (0.5, 2.0, 3.0, 3.0)
    f = next(r for r in out["paths"] if r["path"] == "f")
    assert f["disagree_samples"] == 1
    t22 = next(r for r in out["trips"] if r["trip"] == "22_2")
    assert t22["port_minus_v1_s"] == 0.5
    assert "| 22_2 | 2.0 | 2.5 | 0.5 |" in cmpmod.report_markdown(out)


@pytest.mark.skipif(not v1_available(), reason="V1 source tree not present on this machine")
def test_v1s_driver_runs_in_its_own_process(tmp_path):
    subprocess.run([sys.executable, "-m", "tests.phase7.run", "vacuum_break", "--side", "v1",
                    "--duration", "1", "--out", str(tmp_path)], cwd=ROOT, check=True,
                   capture_output=True, timeout=600)
    rec = json.loads((tmp_path / "vacuum_break_v1.json").read_text(encoding="utf-8"))
    assert rec["side"] == "v1" and len(rec["t"]) == 0      # 1 s, sampled every 5 s
    assert rec["stopped"] == {"why": "duration", "t_s": 1.0}
    assert set(rec["watch"]) == set(WATCHES)
