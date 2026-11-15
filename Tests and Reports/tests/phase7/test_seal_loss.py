"""Smoke tests of the stripper-level-loss survey — `tests.phase7.seal_loss` and its runner.

Pinned: every case is well formed, every path it reads resolves in the port's packet or in the
runner's result indicators, and the engine accepts every command it applies, on the design seed;
the score counts the claims as claimed, the claims read and the claims put. The whole survey runs
through the command line (`python -m tests.phase7.run_seal_loss OUT_DIR`), its results in As-Built
Part LXXXVII (session 72).
"""

from __future__ import annotations

import pytest

from tests.phase7 import run_seal_loss as rs
from tests.phase7.seal_loss import NOT_PUT, SEAL_LOSS


def test_every_case_is_well_formed():
    keys = [c.key for c in SEAL_LOSS]
    assert len(keys) == len(set(keys)) and not set(keys) & set(NOT_PUT)
    for c in SEAL_LOSS:
        assert c.commands and c.claims and c.duration_s >= 2700.0, c.key
        assert c.source.startswith("Scenarios6.docx"), c.key
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
    peak = rs.ReliefPeak()
    extra = rs.extra(peak)
    missing = [(c.key, x.path) for c in SEAL_LOSS for x in c.claims
               if x.path not in (extra if x.path.startswith("x.") else flat)]
    assert missing == []
    peak.watch(sched.results)
    assert extra["x.c003_relief_th"](sched.results) == 0.0


def test_the_relief_indicator_keeps_the_peak_between_samples():
    """A lift shorter than the 5 s sample still reads: the most relieved since the last sample,
    then nothing until the valves lift again (B-114, session 73)."""
    class R:
        def __init__(self, kgh):
            self.relief_kgh = kgh
    peak = rs.ReliefPeak()
    for kgh in (0.0, 51410.0, 20000.0, 0.0):
        peak.watch({"323C003": R(kgh)})
    assert (peak.take(None), peak.take(None)) == (51.41, 0.0)


@pytest.mark.parametrize("case", SEAL_LOSS, ids=[c.key for c in SEAL_LOSS])
def test_the_engine_accepts_every_command(case):
    from ureasim.engine.command import apply_command
    from ureasim.engine.plant import build_plant
    from ureasim.engine.scheduler import Scheduler
    sched = Scheduler(*build_plant())
    for cmd in case.commands:
        r = apply_command(sched.plant, cmd, sched.results)
        assert r.ok, (case.key, cmd, r.reason)


def test_the_score_counts_what_was_claimed_read_and_put():
    rows = [{"agrees": True}, {"agrees": False}, {"agrees": None}]
    assert rs.score([(None, rows, None), (None, [{"agrees": True}], None)]) == (2, 3, 4)
