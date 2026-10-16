"""Behaviour of unit 335's UF85 dosing — `ureasim.units.finishing.uf85_dosing`.

Equivalence with V1's ``step_uf85_cascade`` and ``route_lv324501`` is proven tick by tick in
`tests/equivalence/test_uf85_dosing_equivalence.py`. This file pins what the dosing DOES on the
plant's design drain (decided 2026-10-16, decision 123): the seed holds, the ratio follows the melt,
LV-324501B stops the pumps, and a slave out of cascade leaves the master tracking. Every number was
measured on the module before it was written down.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_324 as d
from ureasim.data import unit_335 as u
from ureasim.units.finishing import uf85_dosing as uf

W, T = d.W_S402, 140.0


def _run(ticks, drain=lambda k: (d.P2_DES_KGH, False), setup=None):
    master, slave = uf.ffic_335406(), uf.fic_335405()
    if setup:
        setup(master, slave)
    out = []
    for k in range(ticks):
        m, recycle = drain(k)
        out.append(uf.uf85_step(master, slave, m, W, T, recycle, 0.1))
    return master, slave, out


def test_the_design_holds():
    """An hour on the design drain: 617.07 kg/h, the PFD's ratio, FIC-335405 at 44.46 %, within
    2e-13 kg/h; 609 forward, 76 555.19 kg/h at 138.62 C."""
    master, slave, out = _run(36000)
    assert out[-1].delivered_kgh == pytest.approx(u.UF85_DES_KGH, abs=1e-12)
    assert slave.loop.op == pytest.approx(44.457653, abs=1e-6)
    assert master.loop.op == pytest.approx(u.UF_RATIO_DES, rel=1e-12)
    r = out[-1].route
    assert (r.route, r.uf85_kgh) == ("A", out[-1].delivered_kgh)
    assert r.forward_kgh == pytest.approx(76555.19, abs=0.01)
    assert r.forward_t_c == pytest.approx(138.620, abs=1e-3)


def test_the_dosing_follows_the_melt_on_v1s_slow_master():
    """The melt down 20 % at 10 s: the measured ratio jumps and the master's proportional kick on
    it takes the flow below the ratio, 498.77 kg/h after 30 s, then 485.72 after two minutes,
    1.6 % under the ratio's 493.66 — V1's tuning, 0.5 on the ratio and 60 s, which the DCS table
    has no row to replace."""
    _, _, out = _run(1200, lambda k: (d.P2_DES_KGH * (0.8 if k >= 100 else 1.0), False))
    assert out[400].delivered_kgh == pytest.approx(498.769, abs=1e-3)
    assert out[-1].delivered_kgh == pytest.approx(485.723, abs=1e-3)


def test_lv_324501b_stops_the_pumps_and_they_restart():
    """Thirty seconds on LV-324501B: no UF85 joins the recycled melt, FT-335405 decays on its 5 s
    lag to 0.0016 t/h, FFIC-335406 frozen on its ratio. Back on route A the pumps restart, 489.1
    kg/h after a minute, the master's kick on the restart's ratio leaving them short of 617.1."""
    master, slave = uf.ffic_335406(), uf.fic_335405()
    out = []
    for k in range(1001):
        out.append(uf.uf85_step(master, slave, d.P2_DES_KGH, W, T, 100 <= k < 400, 0.1))
        if k == 399:
            assert slave.loop.pv == pytest.approx(0.001623, abs=1e-6)
    assert all(r.interlocked and r.delivered_kgh == 0.0 and r.route.uf85_kgh == 0.0
               for r in out[100:400])
    assert out[399].route.route == "B" and out[399].ratio_command == out[99].ratio_command
    assert out[-1].route.route == "A"
    assert out[-1].delivered_kgh == pytest.approx(489.119, abs=1e-3)


def test_a_slave_out_of_cascade_leaves_the_master_tracking():
    """FIC-335405 in MAN at 60 %: the pumps deliver 832.8 kg/h on their stroke, and the master,
    with no authority, tracks the achieved ratio, 0.010967."""
    def man(master, slave):
        slave.loop.mode, slave.loop.op = "MAN", 60.0
    master, _, out = _run(600, setup=man)
    assert out[-1].delivered_kgh == pytest.approx(832.8, abs=1e-9)
    assert master.loop.op == out[-1].measured_ratio == pytest.approx(0.0109668, abs=1e-7)
