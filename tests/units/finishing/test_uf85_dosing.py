"""Behaviour of unit 335's UF85 dosing — `ureasim.units.finishing.uf85_dosing`.

Equivalence with V1's ``step_uf85_cascade`` and ``route_lv324501`` is proven tick by tick in
`tests/equivalence/test_uf85_dosing_equivalence.py`, on V1's PI master. This file pins what the
dosing DOES on the plant's design drain (decided 2026-10-16, decision 123) under FFIC-335406's ratio
station, as its faceplate in the plant DCS shows it (decided 2026-10-28, decision 160): the seed
holds, the set point follows the melt, LV-324501B stops the pumps, a slave out of cascade leaves the
station tracking, and the faceplate's limits bind. Every number was measured on the module before it
was written down.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_324 as d
from ureasim.data import unit_335 as u
from ureasim.units.finishing import uf85_dosing as uf

W, T = d.W_S402, 140.0


def _run(ticks, drain=lambda k: (d.P2_DES_KGH, False), setup=None):
    station, slave = uf.ffic_335406(), uf.fic_335405()
    if setup:
        setup(station, slave)
    out = []
    for k in range(ticks):
        m, recycle = drain(k)
        out.append(uf.uf85_step(station, slave, m, W, T, recycle, 0.1))
    return station, slave, out


def test_the_design_holds():
    """An hour on the design drain: 617.07 kg/h, the PFD's ratio, FIC-335405 at 44.46 %, within
    2e-13 kg/h; 609 forward, 76 555.19 kg/h at 138.62 C. The station's ratio is the PFD's, its
    output FIC-335405's seed in t/h."""
    station, slave, out = _run(36000)
    assert out[-1].delivered_kgh == pytest.approx(u.UF85_DES_KGH, abs=1e-12)
    assert slave.loop.op == pytest.approx(44.457653, abs=1e-6)
    assert station.sp == u.UF_RATIO_DES
    assert station.op == out[-1].flow_setpoint_th == pytest.approx(u.UF85_DES_KGH / 1000.0,
                                                                    rel=1e-15)
    r = out[-1].route
    assert (r.route, r.uf85_kgh) == ("A", out[-1].delivered_kgh)
    assert r.forward_kgh == pytest.approx(76555.19, abs=0.01)
    assert r.forward_t_c == pytest.approx(138.620, abs=1e-3)


def test_the_set_point_follows_the_melt_on_the_ratio():
    """The melt down 20 % at 10 s: the station hands FIC-335405 the ratio times the new melt on the
    tick, 0.49366 t/h, and the pumps follow on their own loop — 523.51 kg/h after 30 s, 494.66 after
    two minutes, against the ratio's 493.66 (V1's PI master leaves them 1.6 % under it)."""
    _, _, out = _run(1200, lambda k: (d.P2_DES_KGH * (0.8 if k >= 100 else 1.0), False))
    assert out[100].flow_setpoint_th == pytest.approx(u.UF_RATIO_DES * d.P2_DES_KGH * 0.8 / 1000.0,
                                                      rel=1e-12)
    assert out[400].delivered_kgh == pytest.approx(523.513, abs=1e-3)
    assert out[-1].delivered_kgh == pytest.approx(494.657, abs=1e-3)


def test_lv_324501b_stops_the_pumps_and_they_restart():
    """Thirty seconds on LV-324501B: no UF85 joins the recycled melt, FT-335405 decays on its 5 s
    lag to 0.0016 t/h, the station's output at OUT L with no melt forward and its ratio standing.
    Back on route A the station asks the ratio again at once: 575.44 kg/h after a minute."""
    station, slave = uf.ffic_335406(), uf.fic_335405()
    out = []
    for k in range(1001):
        out.append(uf.uf85_step(station, slave, d.P2_DES_KGH, W, T, 100 <= k < 400, 0.1))
        if k == 399:
            assert slave.loop.pv == pytest.approx(0.001623, abs=1e-6)
            assert (station.op, station.pv, station.sp) == (0.0, 0.0, u.UF_RATIO_DES)
    assert all(r.interlocked and r.delivered_kgh == 0.0 and r.route.uf85_kgh == 0.0
               for r in out[100:400])
    assert out[399].route.route == "B" and out[399].ratio_command == out[99].ratio_command
    assert out[-1].route.route == "A"
    assert out[-1].delivered_kgh == pytest.approx(575.445, abs=1e-3)


def test_a_slave_out_of_cascade_leaves_the_station_tracking():
    """FIC-335405 in MAN at 60 %: the pumps deliver 832.8 kg/h on their stroke, and the station,
    with no authority, tracks the achieved ratio, 0.010967 — held at its faceplate's RAT H, 0.0080,
    so its output stands at 0.6075 t/h for the return to cascade."""
    def man(station, slave):
        slave.loop.mode, slave.loop.op = "MAN", 60.0
    station, _, out = _run(600, setup=man)
    assert out[-1].delivered_kgh == pytest.approx(832.8, abs=1e-9)
    assert out[-1].measured_ratio == pytest.approx(0.0109668, abs=1e-7)
    assert station.sp == u.FFIC_335406_RAT_HI
    assert station.op == pytest.approx(0.607505, abs=1e-6)


def test_the_faceplates_limits_bind():
    """RAT H and OUT H as the faceplate sets them: a ratio of 0.0100 asked is 0.0080, and on 120 t/h
    of melt the station asks no more than 0.80 t/h — 787.6 kg/h a minute on."""
    station, slave = uf.ffic_335406(), uf.fic_335405()
    station.set_sp(0.0100)
    assert station.sp == u.FFIC_335406_RAT_HI == 0.0080
    out = [uf.uf85_step(station, slave, 120000.0, W, T, False, 0.1) for _ in range(600)]
    assert out[-1].flow_setpoint_th == u.FFIC_335406_OUT_HI_TH == 0.80
    assert out[-1].delivered_kgh == pytest.approx(787.589, abs=1e-3)
