"""V1 <-> V1.1 equivalence for unit 335's UF85 dosing — `ureasim.units.finishing.uf85_dosing`.

What is being proved
--------------------
V1 builds the whole dosing — ``step_uf85_cascade``, FFIC-335406 over FIC-335405 with LV-324501B as
its permissive, and ``route_lv324501``, which joins the delivered UF85 to the forward melt — and
never runs it: ``step_sim`` calls the cascade with the recycle permissive forced and the selector
at ``uf_ratio=0.0`` ("UF85 deferred (granulation off)"). The port runs both live (decided
2026-10-16, ``project.md`` decision 123). So both sides are asserted:

  * the port's dosing against V1's two functions as V1 wrote them, the selector on what the pumps
    deliver, ``uf_ratio = m_uf / m_402``: every field ``==``, tick for tick, from V1's seeds,
    through a rate ramp, a recycle and the slave's modes;
  * V1's call as V1 executes it against the port on V1's switch, the permissive forced: ``==``;
  * the divergence at design: V1 doses nothing; the port 617.07 kg/h.

V1's cascade is lifted by AST (`tests.equivalence.test_ratio_equivalence`), the selector with
`v1_loader.lift`; both execute V1's code.
"""

from __future__ import annotations

import math

import pytest

from ureasim.data import unit_324 as d
from ureasim.data import unit_335 as u
from ureasim.units.finishing import uf85_dosing as uf
from tests.equivalence.test_ratio_equivalence import _v1_cascade, _v1_state
from tests.equivalence.v1_loader import lift, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

DT = 0.1
T_402 = 140.3


@pytest.fixture(scope="module")
def v1():
    ns = _v1_cascade()
    ns.update(lift(["route_lv324501", "R324_UF_RATIO", "W_S697", "R324_M402G_PFD",
                    "R324_M697_PFD", "R324_UF85_RHO", "R324_P2_DES", "R324_FIC405_OP_DES",
                    "R324_M_UF_DES"], seed={"math": math}))
    return ns


def test_the_design_data_are_v1s(v1):
    """The PFD's 402G, 697 and its ratio, UF85's fractions and density, the 50 % stroke: ``==``
    V1's; the seed's 617.07 kg/h is that ratio on V1's own design drain."""
    assert (u.PFD_402G_KGH, u.PFD_697_KGH, u.UF_RATIO_DES, u.PFD_697_RHO_KGM3) == (
        v1["R324_M402G_PFD"], v1["R324_M697_PFD"], v1["R324_UF_RATIO"], v1["R324_UF85_RHO"])
    assert u.W_697 == v1["W_S697"] and u.FIC_335405_OP_DES_PCT == v1["R324_FIC405_OP_DES"]
    assert d.P2_DES_KGH == v1["R324_P2_DES"]
    assert u.UF85_DES_KGH == pytest.approx(617.0722, abs=1e-4)


def _drain(k: int) -> tuple[float, bool]:
    """The melt and the route: design, a ramp down 20 % over a minute, LV-324501B for 30 s."""
    m = d.P2_DES_KGH * (1.0 - 0.2 * min(max(k - 300, 0), 600) / 600.0)
    return m, 1500 <= k < 1800


def _run(v1, script, ticks, forced=False, modes=None):
    """V1's cascade and selector and the port's dosing on the same drain, compared every tick."""
    s = _v1_state()
    master, slave = uf.ffic_335406(), uf.fic_335405(u.PFD_697_KGH)
    w = dict(d.W_S402)
    out = []
    for k in range(ticks):
        m, recycle = script(k)
        if modes and k in modes:
            s.FIC_335405["mode"] = slave.loop.mode = modes[k]
        a = v1["step_uf85_cascade"](s, m, True if forced else recycle, DT)
        ratio = 0.0 if forced or m <= 1e-12 else a["delivered_kgh"] / m
        ra = v1["route_lv324501"](m, w, T_402, recycle, uf_ratio=ratio)
        b = uf.uf85_step(master, slave, m, w, T_402, True if forced else recycle, DT)
        assert (a["measured_ratio"], a["ratio_command"], a["flow_setpoint_th"],
                a["delivered_kgh"], a["interlocked"]) == (
            b.measured_ratio, b.ratio_command, b.flow_setpoint_th, b.delivered_kgh,
            b.interlocked), k
        for c, loop in ((s.FFIC_335406, master.loop), (s.FIC_335405, slave.loop)):
            assert (c["pv"], c["pv1"], c["pv2"], c["op"], c["sp"]) == (
                loop.pv, loop.pv1, loop.pv2, loop.op, loop.sp), (k, loop.tag)
        if not forced:
            r = b.route
            assert (ra["route"], ra["forward_kgh"], ra["forward_comp"], ra["forward_T_C"],
                    ra["recycle_kgh"], ra["recycle_comp"], ra["recycle_T_C"], ra["uf85_kgh"]) == (
                r.route, r.forward_kgh, r.forward_w, r.forward_t_c, r.recycle_kgh, r.recycle_w,
                r.recycle_t_c, r.uf85_kgh), k
        out.append((a, ra, b))
    return out


def test_the_dosing_is_v1s_cascade_and_selector(v1):
    """From V1's seeds, 694 kg/h at 50 %: the ratio master trims the slave down toward the ratio
    on the design drain, 620.3 kg/h after 30 s; a 20 % ramp leaves it 482.7 kg/h a minute later,
    2.2 % under the ratio's 493.7 — V1's master, 0.5 on the ratio and 60 s, is slow; LV-324501B
    stops the pumps and they restart — every field of the cascade, both loops' histories and the
    selector ``==`` V1's functions on every tick."""
    out = _run(v1, _drain, 2400)
    assert out[299][2].delivered_kgh == pytest.approx(620.323, abs=1e-3)
    assert out[1499][2].delivered_kgh == pytest.approx(482.747, abs=1e-3)
    assert out[1700][2].interlocked and out[1700][2].route.uf85_kgh == 0.0


def test_the_slaves_modes_are_v1s(v1):
    """FIC-335405 out of cascade and back: the master tracks the achieved ratio, then trims again
    bumplessly — ``==`` V1's."""
    _run(v1, lambda k: (d.P2_DES_KGH, False), 1200, modes={200: "AUTO", 600: "CAS", 800: "MAN",
                                                             1000: "CAS"})


def test_the_live_dosing_decided_divergence(v1):
    """Decision 123, 2026-10-16: V1's ``step_sim`` forces the permissive, so FIC-335405 goes to 0 %,
    FT-335405 reads nothing and the forward melt is the raw 75 938 kg/h; on that switch the port is
    V1's on every tick. Live, at the design drain the port doses 617.07 kg/h and sends 609 forward,
    76 555.19 kg/h at 138.916 C from a 140.3 C melt, 0.493 % formaldehyde (the PFD's 0.49)."""
    out = _run(v1, lambda k: (d.P2_DES_KGH, False), 600, forced=True)
    a, _, b = out[-1]
    assert (a["delivered_kgh"], b.delivered_kgh, b.interlocked) == (0.0, 0.0, True)
    ra = v1["route_lv324501"](d.P2_DES_KGH, d.W_S402, T_402, False, uf_ratio=0.0)
    assert ra["forward_kgh"] == d.P2_DES_KGH and ra["uf85_kgh"] == 0.0
    master, slave = uf.ffic_335406(), uf.fic_335405()
    for _ in range(600):
        r = uf.uf85_step(master, slave, d.P2_DES_KGH, d.W_S402, T_402, False, DT)
    assert r.delivered_kgh == pytest.approx(u.UF85_DES_KGH, rel=1e-12)
    assert r.route.forward_kgh == pytest.approx(76555.19, abs=0.01)
    assert r.route.forward_t_c == pytest.approx(138.916, abs=1e-3)
    assert r.route.forward_w["HCHO"] == pytest.approx(0.00493, abs=1e-5)
