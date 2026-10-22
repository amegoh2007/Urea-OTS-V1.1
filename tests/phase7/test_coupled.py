"""Smoke tests of the coupled-transient survey — `tests.phase7.coupled` and its runner.

Pinned: every case is well formed, every path it reads resolves in the port's packet or in the
runner's result indicators, and the engine accepts every command it applies, on the design seed;
the verdict reads the largest departure of the first wave, the mean of the second and their
difference for a reversal, and a departure inside the tolerance as none. The whole survey runs
through the command line (`python -m tests.phase7.run_coupled OUT_DIR`), its results in As-Built
Part LXXIX (session 63) and Part LXXX (session 65: fourteen cases, S5-W on FV-323401 in MAN at
100 % and S5-6c at the CO2 boundary +20 %, on B-104 to B-107).
"""

from __future__ import annotations

import pytest

from tests.phase7 import run_coupled as rc
from tests.phase7.coupled import COUPLED, NOT_PUT, Claim, Coupled


def test_every_case_is_well_formed():
    keys = [c.key for c in COUPLED]
    assert len(keys) == len(set(keys)) and not set(keys) & set(NOT_PUT)
    for c in COUPLED:
        assert c.commands and c.claims and c.duration_s >= 2700.0, c.key
        assert c.source.startswith("Scenarios5.md"), c.key
        assert all(x.sign in (-1, 1) and x.wave in ("W1", "W2", "REV") for x in c.claims), c.key


def test_every_path_resolves():
    from ureasim.engine.packet import build_packet
    from ureasim.engine.plant import build_plant
    from ureasim.engine.scheduler import Scheduler
    from tests.phase7.drivers import flatten
    sched = Scheduler(*build_plant())
    sched.tick()
    flat = flatten(build_packet(sched.plant, sched.results, sched.tears_read, sim_mode="SLOW",
                                t_wall=0.0))
    missing = [(c.key, x.path) for c in COUPLED for x in c.claims
               if x.path not in (rc.EXTRA if x.path.startswith("x.") else flat)]
    assert missing == []
    assert {k: f(sched.results) is not None for k, f in rc.EXTRA.items()} == {
        k: True for k in rc.EXTRA}


@pytest.mark.parametrize("case", COUPLED, ids=[c.key for c in COUPLED])
def test_the_engine_accepts_every_command(case):
    from ureasim.engine.command import apply_command
    from ureasim.engine.plant import build_plant
    from ureasim.engine.scheduler import Scheduler
    sched = Scheduler(*build_plant())
    for cmd in case.commands:
        r = apply_command(sched.plant, cmd, sched.results)
        assert r.ok, (case.key, cmd, r.reason)


def _rec(values: dict) -> dict:
    n = len(next(iter(values.values())))
    return {"t": [i * 100.0 for i in range(n)], "values": values, "commands": []}


def test_the_verdict_reads_each_wave():
    """Samples every 100 s: W1 is (0, 300], W2 [900, 2700]."""
    case = Coupled("x", "Scenarios5.md §0", "t", "h", (), (
        Claim("1", "a", +1, "W1", "rises at once"), Claim("1", "a", -1, "REV", "then drops back"),
        Claim("2", "b", -1, "W2", "falls later"), Claim("3", "c", +1, "W1", "inside the band")))
    flat = [10.0] * 28
    control = _rec({"a": list(flat), "b": list(flat), "c": [100.0] * 28})
    a = [10.0, 11.0, 12.0, 11.5] + [10.5] * 24        # up 2 in the first wave, back to +0.5
    b = [10.0] * 9 + [9.0] * 19                        # down 1 from 900 s
    c = [100.0, 100.005] + [100.0] * 26                # under 1e-4 of 100
    rows = rc.verdicts(case, _rec({"a": a, "b": b, "c": c}), control)
    assert (rows[0]["w1"], rows[0]["agrees"]) == (2.0, True)
    assert rows[1]["rev"] == pytest.approx(-1.5) and rows[1]["agrees"]
    assert (rows[2]["w2"], rows[2]["agrees"]) == (-1.0, True)
    assert (rows[3]["measured"], rows[3]["agrees"]) == (0, False)
