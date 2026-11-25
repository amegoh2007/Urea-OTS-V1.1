"""Smoke tests of the process-deviation survey — `tests.phase7.deviations` and its runner.

Pinned: every deviation is well formed, every path it reads resolves in the port's packet, and the
engine accepts every command it applies, on the design seed; the verdict reads a departure from the
control at the end or at its extreme, and a departure inside the tolerance as none; and the runner
puts one short deviation to the plant end to end. The whole survey runs through the command line
(`python -m tests.phase7.run_deviations OUT_DIR`), its results in As-Built §LXXV.2-3.
"""

from __future__ import annotations

import pytest

from tests.phase7 import run_deviations as rd
from tests.phase7.deviations import DEVIATIONS, Deviation, Expect


def test_every_deviation_is_well_formed():
    keys = [d.key for d in DEVIATIONS]
    assert len(keys) == len(set(keys))
    for d in DEVIATIONS:
        assert d.commands and d.expects and d.duration_s > 0.0, d.key
        assert all(e.sign in (-1, 1) and e.measure in ("end", "peak") for e in d.expects), d.key
        assert d.source.startswith(("Scenarios.md", "Scenarios2.md", "Scenarios3.md",
                                    "Scenarios4.md")), d.key


@pytest.fixture(scope="module")
def seed_packet():
    from ureasim.engine.packet import build_packet
    from ureasim.engine.plant import build_plant
    from ureasim.engine.scheduler import Scheduler
    from tests.phase7.drivers import flatten
    sched = Scheduler(*build_plant())
    sched.tick()
    return flatten(build_packet(sched.plant, sched.results, sched.tears_read, sim_mode="x1",
                                t_wall=0.0))


def test_every_path_resolves_in_the_ports_packet(seed_packet):
    missing = [(d.key, e.path) for d in DEVIATIONS for e in d.expects if e.path not in seed_packet]
    assert missing == []


@pytest.mark.parametrize("dev", DEVIATIONS, ids=[d.key for d in DEVIATIONS])
def test_the_engine_accepts_every_command(dev):
    from ureasim.engine.command import apply_command
    from ureasim.engine.plant import build_plant
    from ureasim.engine.scheduler import Scheduler
    sched = Scheduler(*build_plant())
    for cmd in dev.commands:
        r = apply_command(sched.plant, cmd, sched.results)
        assert r.ok, (dev.key, cmd, r.reason)


def _rec(values: dict) -> dict:
    return {"t": list(range(len(next(iter(values.values()))))), "values": values, "commands": []}


def test_the_verdict_reads_the_departure_from_the_control():
    dev = Deviation("x", "Scenarios.md §0", "t", "h", (), (
        Expect("a", +1, "rises"), Expect("b", -1, "dips on the way", "peak"),
        Expect("c", +1, "rises"), Expect("d", -1, "falls")))
    control = _rec({"a": [10.0, 10.0, 10.0], "b": [5.0, 5.0, 5.0], "c": [100.0, 100.0, 100.0],
                    "d": [1.0, 1.0, 1.0]})
    run = _rec({"a": [10.0, 10.5, 11.0], "b": [5.0, 4.0, 5.0], "c": [100.0, 100.0, 100.005],
                "d": [1.0, 1.1, 1.2]})
    rows = {r["path"]: r for r in rd.verdicts(dev, run, control)}
    assert (rows["a"]["departure"], rows["a"]["measured"], rows["a"]["agrees"]) == (1.0, 1, True)
    assert (rows["b"]["departure"], rows["b"]["agrees"]) == (-1.0, True)
    assert (rows["c"]["measured"], rows["c"]["agrees"]) == (0, False)      # inside 1e-4 of 100
    assert (rows["d"]["measured"], rows["d"]["agrees"]) == (1, False)


def test_one_deviation_end_to_end():
    """LV-322501 stepped open to 90 % for two minutes: the stripper's level falls against the
    control, as Scenarios2.md §2.3 claims."""
    dev = next(d for d in DEVIATIONS if d.key == "S2-2.3a")
    paths = ["STRIP_322E001.LI_322501"]
    run = rd.run_plant(dev, 120.0, paths)
    control = rd.run_plant(None, 120.0, paths)
    assert all(ok for _, ok, _ in run["commands"])
    row = rd.verdicts(Deviation(dev.key, dev.source, dev.title, dev.helwan, dev.commands,
                                (dev.expects[0],)), run, control)[0]
    assert row["measured"] == -1 and row["agrees"]
