"""The tabulated Extended UNIQUAC activity grid — `ureasim.thermo.vle_grid`.

Pinned on the store's own fixed points: a node solved afresh from the solver's default start (the
build marches by continuation, which the far corners need) reproduces the stored node's
activities and substance count to the solver's tolerance, so the cached table is the model and
not a stale copy of it; interpolation at a node returns that node; the (s, f) and (N, C) coordinates
are exact inverses, CO2-free liquor included; the envelope test admits the axes' own corners and
nothing outside them; and the cached table is complete (1 215 nodes, none failed).
"""

from __future__ import annotations

import pytest

from ureasim.thermo import vle_grid as grid


@pytest.fixture(scope="module")
def axes():
    grid.ensure_table()
    return grid.nodes()


@pytest.mark.parametrize("i, j, k", [(3, 4, 5), (7, 11, 2), (0, 0, 0), (5, 9, 6)])
def test_a_node_solved_afresh_is_the_stored_node(axes, i, j, k):
    t, s, f = axes[0][i], axes[1][j], axes[2][k]
    fresh = grid._node_activities(t, s, f)
    stored = grid._TABLE[i][j][k]
    assert fresh[4] is True and stored[4] == 1.0
    assert fresh[:4] == pytest.approx(stored[:4], rel=1e-9)
    assert grid.interp(t, s, f)[:4] == pytest.approx(stored[:4], rel=1e-12)


def test_the_coordinates_invert_exactly():
    for s, f in ((0.3, 0.4), (1e-4, 0.0), (0.97, 0.77), (0.5, 0.002)):
        assert grid.loadings_to_sf(*grid.sf_to_loadings(s, f)) == pytest.approx((s, f),
                                                                                 abs=1e-14)
    n, c = grid.sf_to_loadings(0.2, 0.0)
    assert c == 0.0 and n > 0.0


def test_the_envelope_and_the_build(axes):
    t, s, f = axes
    assert grid.in_box(t[0], s[0], f[0]) and grid.in_box(t[-1], s[-1], f[-1])
    assert not grid.in_box(t[0] - 1.0, s[0], f[0])
    assert not grid.in_box(t[0], s[0], f[-1] + 0.01)
    stats = grid.build_stats()
    assert stats["nodes"] == len(t) * len(s) * len(f) == 1215 and stats["failed"] == 0
