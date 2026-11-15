"""V1 <-> V1.1 equivalence for the flow loops' gains — the decided divergence of handoff B-41.

What is being proved
--------------------
Decision 10 reads the DCS tuning table's gains per cent of output per cent of the transmitter's
span. V1 applied the table's number to six flow loops per kg/h (per t/h on FIC-324401), carrying
it to m3/h times the density on the volumetric ones. On 2026-09-30 the process engineer decided
the port reads them per cent of span, each span from Uhde's loop summaries:

    loop         table   span              V1 runs            the port runs
    FIC-323401   0.10    0-4 m3/h          99.24 %/(m3/h)     2.5 %/(m3/h)
    FIC-323402   0.10    0-3.3 m3/h        99.24 %/(m3/h)     3.03 %/(m3/h)
    FIC-328405   0.20    0-2.3 m3/h        198.48 %/(m3/h)    8.70 %/(m3/h)
    FIC-328406   0.75    0-60 m3/h         744.3 %/(m3/h)     1.25 %/(m3/h)
    FIC-323418   1.00    0-10 m3/h         1065 %/(m3/h)      10 %/(m3/h)
    FIC-324401   0.40    0-110 m3/h        0.40 %/(t/h)       0.316 %/(t/h)

Each unit's own equivalence test carries the decided gains in its transcription (seeded into
V1's controller dicts; V1's `_ctrl_ipd` executed unchanged) and compares the port with it on
every tick. Here V1 verbatim runs against the port: bit-exact until the loop first sees an
error, then each side's behaviour asserted — at the engine's 0.1 s step. FIC-328402's gain,
decided earlier (B-38), has its own file.

Both sides run the valves on their vendor trims from the strokes their Kvs give (handoff B-44,
decided 2026-09-30): the transcriptions' ``valves_decided`` switch stays on, so what parts the
two sides here is the gain alone. The valves are proved both ways in the units' own files.
FIC-328406 is 328C004's in the port (handoff B-50): V1's, in 328D003's stage, runs against the
port's loop stepped on its own.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_323 as d323
from ureasim.data import unit_323e011 as e
from ureasim.data import unit_328d003 as d
from ureasim.data.design_point import R323_D002_RHO
from ureasim.units.desorption import ammonia_water_tank as awt
from ureasim.units.desorption import second_desorber as sd
from ureasim.units.recirc import flash_condenser as fc
from ureasim.units.recirc import solution_tank as st
from tests.equivalence import test_ammonia_water_tank_equivalence as tank_eq
from tests.equivalence import test_flash_condenser_equivalence as fc_eq
from tests.equivalence import test_solution_tank_equivalence as st_eq
from tests.equivalence.v1_loader import v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

#: V1's namespaces, built as the units' own equivalence tests build them; the flash condenser's
#: carries stage 4, 323D002, as well.
tank_v1 = tank_eq.v1
recirc_v1 = fc_eq.v1

DT = 0.1


def _within_1pct(k: int, pv: float, target: float, first: dict, side: str) -> None:
    if abs(pv - target) <= 0.01 * target:
        first.setdefault(side, k)


def _toward(prev: float, now: float, target: float) -> bool:
    """A step that does not move away from the target."""
    return (now - prev) * (target - prev) >= -1e-12


# --------------------------------------------------------------------------------------
# The gains
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("name, ratio", [
    ("FIC_323401", 39.696), ("FIC_323402", 32.7492), ("FIC_328405", 22.8252),
    ("FIC_328406", 595.4520),
])
def test_the_tank_loops_gains_are_the_tables_per_cent_of_span(tank_v1, name, ratio):
    """V1 seeds the table's number times the density; the port the table's number per cent of
    the transmitter's span. FIC-328406 is 328C004's (B-50)."""
    s = tank_eq._v1_state(tank_v1)
    loops = sd.SecondDesorberLoops() if name == "FIC_328406" else awt.TankLoops()
    port = getattr(loops, name.lower()).loop
    table = getattr(d, name + "_KC_TABLE")
    assert s.__dict__[name]["Kc"] != port.Kc
    assert port.Kc == table * 100.0 / getattr(d, "FT_" + name[4:] + "_SPAN_M3H")
    assert s.__dict__[name]["Kc"] / port.Kc == pytest.approx(ratio, abs=1e-4)


def test_fic_323418s_and_fic_324401s_gains_are_the_tables_per_cent_of_span(recirc_v1):
    s = fc_eq._v1_state(recirc_v1, decided=False)
    assert (s.FIC_323418["Kc"], fc.fic_323418().loop.Kc) == (1065.0, 10.0)
    assert e.FT_323418_SPAN_M3H == 10.0
    assert (s.FIC_324401["Kc"], st.fic_324401().Kc) == (0.4, d323.FIC_324401_KC)
    assert d323.FIC_324401_KC == 0.4 * 100.0 / (110.0 * R323_D002_RHO / 1000.0)
    assert s.FIC_324401["Kc"] / st.fic_324401().Kc == pytest.approx(1.26610, abs=1e-5)


# --------------------------------------------------------------------------------------
# 328D003's four loops: V1 verbatim against the port
# --------------------------------------------------------------------------------------

def _tank_both(v1, act, ticks):
    """V1 verbatim, on its own gains, and the port side by side, one tick at a time."""
    s = tank_eq._v1_state(v1)
    tank, loops = awt.AmmoniaWaterTank(), awt.TankLoops()
    for k in range(ticks):
        act(k, s, loops)
        x = tank_eq._design()
        tank_eq._feed(s, x)
        a = tank_eq._v1_stage2(v1, s, x["m343"], DT, decided=False)
        b = tank_eq._port(tank, loops, tank_eq._beside(x, a), DT)
        yield k, s, a, b, tank, loops


@pytest.mark.parametrize("name, target, ticks, times", [
    ("FIC_323401", 2.0, 3200, (24.2, 169.4)),
    ("FIC_323402", 2.0, 2700, (24.2, 141.9)),
    ("FIC_328405", 1.0, 6000, (81.2, 407.8)),
], ids=["FIC-323401 to 2.0 m3/h", "FIC-323402 to 2.0 m3/h", "FIC-328405 opened to 1.0 m3/h"])
def test_a_set_point_move_decided_divergence(tank_v1, name, target, ticks, times):
    """Bit-exact until the move, which parts the controllers on its own tick; then both loops
    move monotonically to the new set point, the port's five to seven times more slowly."""
    act = tank_eq._sp(name, name.lower(), target)
    first, last = {}, {}
    for k, s, a, b, tank, loops in _tank_both(tank_v1, act, ticks):
        if k < 10:
            tank_eq._assert_tick(a, b, s, tank, loops, f"tick {k}")
            continue
        if k == 10:
            assert s.__dict__[name]["op"] != getattr(loops, name.lower()).loop.op
        pv = {"v1": s.__dict__[name]["pv"], "port": getattr(loops, name.lower()).loop.pv}
        for side, value in pv.items():
            if side in last:
                assert _toward(last[side], value, target), (side, k)
            last[side] = value
            _within_1pct(k, value, target, first, side)
    assert ((first["v1"] - 10) * DT, (first["port"] - 10) * DT) == pytest.approx(times, abs=1e-9)


def test_fic_328406_in_auto_decided_divergence(tank_v1):
    """FIC-328406, seeded in MAN and shut, put in AUTO on 10 m3/h of 741 at 1 s. V1's discrete
    loop gain on the 5 s transmitter is about 5: FV-328406 slams between 0 and 100 % on every tick
    and 741 never settles. The port's — 328C004's loop, stepped on its own; the column's 33 724
    kg/h of bottoms never binds it — brings 741 to 10 m3/h monotonically, within 1 % 1286.2 s after
    the switch, FV-328406 at 31.3 % on its trim's linear foot."""
    fic = sd.fic_328406()
    first, last, v1_ops = {}, None, []

    def auto(k, s, loops):
        if k == 10:
            s.FIC_328406.update(mode="AUTO", sp=10.0)
            fic.loop.mode, fic.loop.sp = "AUTO", 10.0

    for k, s, a, b, tank, loops in _tank_both(tank_v1, auto, 13000):
        m_741 = fic.step(DT)
        if k < 10:
            assert (s.FIC_328406["op"], s.FIC_328406["pv"], a["741"]) == (
                fic.loop.op, fic.loop.pv, m_741) == (0.0, 0.0, 0.0)
            continue
        if k >= 200:
            v1_ops.append(s.FIC_328406["op"])
        pv = fic.loop.pv
        if last is not None:
            assert _toward(last, pv, 10.0), k
        last = pv
        _within_1pct(k, pv, 10.0, first, "port")
    assert set(v1_ops) == {0.0, 100.0}
    assert all(x != y for x, y in zip(v1_ops, v1_ops[1:]))
    assert (first["port"] - 10) * DT == pytest.approx(1286.2, abs=1e-9)
    assert fic.loop.pv == pytest.approx(10.0, abs=0.1)
    assert fic.loop.op == pytest.approx(31.29, abs=0.01)


# --------------------------------------------------------------------------------------
# FIC-323418 on 323E011 and FIC-324401 on 323D002: V1 verbatim against the port
# --------------------------------------------------------------------------------------

def test_fic_323418_set_point_decided_divergence(recirc_v1):
    """718B from 3.34 to 4.5 m3/h at 1 s: bit-exact until the move; both loops monotone, V1's
    within 1 % in 326.4 s, the port's in 536.6 s. LIC-323503 takes 718A down against either, and
    323D011 stays within 1 % of its 50 % set point on both sides."""
    s = fc_eq._v1_state(recirc_v1, decided=False)
    cond, loops = fc.FlashCondenser(**fc.V1_CONDENSER), fc_eq._loops()
    first, last, levels = {}, {}, []
    for k in range(7500):
        if k == 10:
            s.FIC_323418["sp"] = loops[2].loop.sp = 4.5
        x = fc_eq._design()
        a = fc_eq._v1_stage9(recirc_v1, s, x["m701"], x["b505"], x["b501"], x["m786"],
                             x["m321"], x["m402"], DT)
        b = cond.step(*loops, x["m701"], x["b505"], x["b501"], x["m786"], x["m321"],
                      x["m402"], DT)
        if k < 10:
            fc_eq._assert_tick(a, b, s, cond, loops, f"tick {k}")
            continue
        if k == 10:
            assert s.FIC_323418["op"] != loops[2].loop.op
        pv = {"v1": s.FIC_323418["pv"], "port": loops[2].loop.pv}
        for side, value in pv.items():
            if side in last:
                assert _toward(last[side], value, 4.5), (side, k)
            last[side] = value
            _within_1pct(k, value, 4.5, first, side)
        levels += [a["LI"], b.level_pct]
    assert ((first["v1"] - 10) * DT, (first["port"] - 10) * DT) == pytest.approx(
        (326.4, 536.6), abs=1e-9)
    assert 49.0 < min(levels) and max(levels) < 51.0


def test_fic_324401_in_auto_decided_divergence(recirc_v1):
    """FIC-324401 out of cascade, in AUTO on 80 t/h from its 92.7 t/h seed: the controllers part
    on the first tick; both come down monotonically, V1's within 1 % in 160.9 s, the port's in
    182.3 s."""
    s = st_eq._v1_state(recirc_v1, decided=False)
    tank, lic, fic = st.SolutionTank(backward_species=False), st.lic_323507(), st.fic_324401()
    s.FIC_324401["mode"] = "AUTO"
    s.FIC_324401["sp"] = fic.sp = 80.0
    fic.set_mode("AUTO")
    first, last = {}, {}
    for k in range(2300):
        x = st_eq._design()
        s.HV_323D002_TIE = x["tie"]
        s.tlag["R324_recyc"], s.tlag["R324_recyc_T"], s.tlag["R324_recyc_comp"] = x["rec"]
        a = st_eq._v1_stage4(recirc_v1, s, x["m317"], x["t317"], x["w317"], DT)
        b = tank.step(lic, fic, x["m317"], x["t317"], x["w317"], *x["rec"], x["tie"], DT)
        if k == 0:
            assert a["fic_pv"] == b.fic_pv_th and a["fic"] != b.fic_op_pct
        pv = {"v1": a["fic_pv"], "port": b.fic_pv_th}
        for side, value in pv.items():
            if side in last:
                assert _toward(last[side], value, 80.0), (side, k)
            last[side] = value
            _within_1pct(k, value, 80.0, first, side)
    assert (first["v1"] * DT, first["port"] * DT) == pytest.approx((160.9, 182.3), abs=1e-9)
