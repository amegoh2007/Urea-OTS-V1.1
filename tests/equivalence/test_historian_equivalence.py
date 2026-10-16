"""V1 <-> V1.1 for the process historian — `ureasim.engine.historian`.

V1's ``historian.py`` is a module of its own, so it is executed as it stands and driven with the
same packets as the port: a run of plant time at two speeds, a path that appears mid-run, a path
that drops out, a spike between output points, a wrapped ring and a scrolled-back window. Every
query answers ``==``. The port's one extension — the walk over result objects and the omission of
composition vectors — is pinned in `tests/engine/test_historian.py`.
"""

from __future__ import annotations

import math

import pytest

from tests.equivalence.v1_loader import load, v1_available
from ureasim.engine import historian as port

pytestmark = pytest.mark.skipif(not v1_available(), reason="V1 source tree not present")

#: Small rings so a run wraps them: 1 s x 120 and 10 s x 60.
RINGS = (("fast", 1.0, 120), ("slow", 10.0, 60))


@pytest.fixture(scope="module")
def v1():
    return load("historian")


def _packet(k: int) -> dict:
    """A packet at step k: a level, a flag, a nested controller, a path that appears at step 150
    and one that drops out at step 400, and a one-step spike at 333."""
    pkt = {"LT_322504": 80.0 + math.sin(k / 37.0), "trip_22_2": k % 97 == 0,
           "controllers": {"FIC_329409": {"pv": 75.0 + 0.01 * k, "op": 50.0, "mode_auto": True}},
           "STREAMS": {"204": {"NH3": 1.0}}}
    if k >= 150:
        pkt["PT_329201"] = 140.7 + 1e-4 * k
    if k < 400:
        pkt["TT_322014"] = 183.0 - 1e-3 * k
    if k == 333:
        pkt["LT_322504"] = 999.0
    return pkt


def _drive(module, steps: int, dt: float) -> object:
    hist = module.Historian(RINGS)
    for k in range(steps):
        hist.maybe_sample(_packet(k), k * dt, 1000.0 + 0.1 * k)
    return hist


def _same(a: dict, b: dict) -> None:
    assert a.keys() == b.keys()
    for key in a:
        if key == "series":
            assert a[key].keys() == b[key].keys()
            for p in a[key]:
                assert a[key][p] == b[key][p], p
        else:
            assert a[key] == b[key], key


@pytest.mark.parametrize("dt", [0.1, 6.0])
def test_every_query_is_v1s(v1, dt):
    """At 1x (0.1 s steps) and at FAST's 60x (6 s), every window both rings serve is V1's."""
    mine, theirs = _drive(port, 2000, dt), _drive(v1, 2000, dt)
    paths = ["LT_322504", "trip_22_2", "controllers.FIC_329409.pv",
             "controllers.FIC_329409.mode_auto", "PT_329201", "TT_322014", "STREAMS.204.NH3",
             "never_logged"]
    newest = 1999 * dt
    for span, end in ((60.0, None), (120.0, None), (600.0, None), (3600.0, None),
                      (60.0, newest - 90.0), (300.0, newest - 400.0)):
        for max_points in (800, 20, 7):
            _same(mine.query(paths, span, max_points, end), theirs.query(paths, span, max_points, end))
    assert mine.paths() == theirs.paths()
    assert mine.stats() == theirs.stats()
    assert port.flatten(_packet(500)) == v1.flatten(_packet(500))


def test_the_constants_are_v1s(v1):
    assert port.RINGS == v1.RINGS and port.PATH_EXCLUDE == v1.PATH_EXCLUDE
