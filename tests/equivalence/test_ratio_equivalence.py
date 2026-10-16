"""V1 <-> V1.1 equivalence for the ratio master in `ureasim.control.ratio`.

What is being proved
--------------------
`ureasim.control.ratio` is an EXTRACTION, not a transcription: V1's ratio block lives inside
`step_uf85_cascade`, a function that also knows about t/h scalings, the LV-324501B recycle
permissive and unit 335's design constants. The rewrite keeps the control block here and
leaves those with the unit that owns them.

An extraction is the most dangerous kind of port, because the code no longer looks like its
source and "equivalent" becomes a judgement. So it is not judged. The test below rebuilds
V1's whole cascade — master, slave and the t/h conversions around them — out of the V1.1
pieces, drives it and V1's own function with the same inputs, and asserts that every
published number agrees tick for tick.

The three behaviours that make the block worth having are pinned by name:

  * **external-reset feedback** while the slave is off cascade,
  * **the permissive freeze**, which must not wind the master up,
  * **a MAN master keeps the operator's number** even while its history advances.

`backend/main.py` cannot be imported — it builds a FastAPI app and a full plant state at
import — so `step_uf85_cascade` and its four helpers are lifted out by AST and executed in a
controlled namespace against a stub state object carrying only the three attributes the
function touches. That is V1's code running, not a paraphrase of it.
"""

from __future__ import annotations

import ast
import math
from types import SimpleNamespace

import pytest

from ureasim.control.process_loop import FlowLoop, ProcessLoop
from ureasim.control.ratio import RatioMaster, ratio_demand
from tests.equivalence.v1_loader import V1_BACKEND, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

DT = 0.1

#: Unit 335 design constants, quoted from V1 `main.py` with their own comments.
M402G_PFD = 85_405.0        # kg/h raw melt, stream 402G
M_UF_DES = 694.0            # kg/h UF85, stream 697
UF_RATIO = M_UF_DES / M402G_PFD     # UF85 / raw-melt ratio; DCS source FQI-335401
FIC405_OP_DES = 50.0        # % FIC-335405 slave design stroke


def _v1_cascade():
    """Lift `step_uf85_cascade` and its helpers out of V1 `main.py`."""
    text = (V1_BACKEND / "main.py").read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(text)
    wanted = {"clamp", "_pv_ok", "_lag1", "_ctrl_ipd", "_fic_flow", "step_uf85_cascade"}
    ns: dict = {"math": math,
                "R324_M_UF_DES": M_UF_DES,
                "R324_FIC405_OP_DES": FIC405_OP_DES}
    for stmt in tree.body:
        if isinstance(stmt, ast.FunctionDef) and stmt.name in wanted:
            exec(compile(ast.Module([stmt], []), "<v1 main.py>", "exec"), ns)
    missing = wanted - set(ns)
    assert not missing, f"could not lift {sorted(missing)} out of V1 main.py"
    return ns


@pytest.fixture(scope="module")
def v1():
    return _v1_cascade()


def _v1_state():
    """The three attributes `step_uf85_cascade` touches, seeded as V1 seeds them."""
    return SimpleNamespace(
        FFIC_335406={"mode": "AUTO", "op": UF_RATIO,
                     "sp": UF_RATIO, "pv": UF_RATIO,
                     "pv1": UF_RATIO, "pv2": UF_RATIO,
                     "Kc": 0.5, "Ti": 60.0, "Td": 0.0, "act": +1.0,
                     "op_lo": 0.0, "op_hi": 0.05, "sp_lo": 0.0, "sp_hi": 0.05},
        FIC_335405={"mode": "CAS", "op": FIC405_OP_DES,
                    "sp": M_UF_DES / 1000.0, "pv": M_UF_DES / 1000.0,
                    "pv1": M_UF_DES / 1000.0, "pv2": M_UF_DES / 1000.0,
                    "Kc": 100.0, "Ti": 15.0, "Td": 0.0, "act": +1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0, "sp_hi": 1.0},
        tlag={},
    )


def _v11_cascade():
    """The same pair built out of the rewrite's blocks."""
    master = RatioMaster(loop=ProcessLoop(
        tag="FFIC-335406", Kc=0.5, Ti=60.0, Td=0.0, act=+1.0, mode="AUTO",
        op=UF_RATIO, sp=UF_RATIO, pv=UF_RATIO, pv1=UF_RATIO, pv2=UF_RATIO,
        op_lo=0.0, op_hi=0.05, sp_lo=0.0, sp_hi=0.05))
    slave = FlowLoop(
        loop=ProcessLoop(
            tag="FIC-335405", Kc=100.0, Ti=15.0, Td=0.0, act=+1.0, mode="CAS",
            op=FIC405_OP_DES, sp=M_UF_DES / 1000.0, pv=M_UF_DES / 1000.0,
            pv1=M_UF_DES / 1000.0, pv2=M_UF_DES / 1000.0,
            op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=1.0),
        design_flow=M_UF_DES / 1000.0, op_des=FIC405_OP_DES, tau_s=5.0)
    return master, slave


def _v11_step(master: RatioMaster, slave: FlowLoop, melt_kgh: float, recycle: bool,
              dt: float) -> dict:
    """Unit 335's wiring of the two blocks, in the shape V1 publishes.

    Everything here that is not a call into the control layer is a UNIT conversion — the
    t/h <-> kg/h scalings V1 does inline. Keeping them in the caller is the whole point of
    the extraction: the ratio block works in one consistent unit and does not care which.
    """
    measured_uf_kgh = max(slave.loop.pv * 1000.0, 0.0)
    result = master.step(measured_uf_kgh, melt_kgh, dt,
                         slave_in_cascade=slave.loop.mode == "CAS",
                         permissive_ok=not recycle)
    if result.interlocked:
        # The hard permissive: the dosing pump is zeroed whatever the controller says, and
        # the slave's measurement decays on its own transmitter.
        slave.loop.op = 0.0
        pv_zero = slave.force_measurement(0.0, dt)
        slave.loop.observe(pv_zero)
        return {"measured_ratio": 0.0, "ratio_command": master.loop.op,
                "flow_setpoint_th": 0.0, "delivered_kgh": 0.0, "interlocked": True}

    flow_setpoint_th = max(result.demand / 1000.0, 0.0)
    delivered_th = slave.step(dt, cas_sp=flow_setpoint_th)
    return {"measured_ratio": result.measured, "ratio_command": result.command,
            "flow_setpoint_th": flow_setpoint_th,
            "delivered_kgh": max(delivered_th * 1000.0, 0.0), "interlocked": False}


def _compare(v1, script, ticks: int = 400):
    """Drive both cascades through `script(k) -> (melt_kgh, recycle)` and compare."""
    s = _v1_state()
    master, slave = _v11_cascade()
    for k in range(ticks):
        melt, recycle = script(k)
        if isinstance(recycle, tuple):          # a mode change rides along with the inputs
            recycle, mode = recycle
            s.FIC_335405["mode"] = mode
            slave.loop.set_mode(mode)
        a = v1["step_uf85_cascade"](s, melt, recycle, DT)
        b = _v11_step(master, slave, melt, recycle, DT)
        assert a == b, f"tick {k}: {a} != {b}"
        assert s.FFIC_335406["pv"] == master.loop.pv, f"tick {k}"
        assert s.FFIC_335406["pv1"] == master.loop.pv1, f"tick {k}"
        assert s.FFIC_335406["pv2"] == master.loop.pv2, f"tick {k}"
        assert s.FIC_335405["op"] == slave.loop.op, f"tick {k}"
    return s, master, slave


# --------------------------------------------------------------------------------------
# The open-loop ratio demand
# --------------------------------------------------------------------------------------

def test_the_ratio_demand_is_the_product_it_claims_to_be():
    """N/C: a MOLAR ratio commanding a MASS flow has to cross the molar-mass bridge."""
    nc_factor = 44.0098 / 17.0304
    assert ratio_demand(2.0231315310702604, 30000.0, nc_factor) == pytest.approx(
        2.0231315310702604 * nc_factor * 30000.0, rel=1e-15)
    assert ratio_demand(UF_RATIO, M402G_PFD) == pytest.approx(M_UF_DES, rel=1e-12)


# --------------------------------------------------------------------------------------
# The whole cascade, against V1
# --------------------------------------------------------------------------------------

def test_the_cascade_holds_its_design_ratio_and_matches_v1(v1):
    """At design the achieved ratio is the set point, so the master makes no move at all."""
    s, master, slave = _compare(v1, lambda k: (M402G_PFD, False), ticks=600)
    assert master.loop.op == pytest.approx(UF_RATIO, rel=1e-9)
    assert slave.loop.op == pytest.approx(FIC405_OP_DES, rel=1e-6)


def test_a_moving_plant_rate_tracks_v1(v1):
    """The point of ratio control: the additive follows the rate without an operator move."""
    def script(k):
        return M402G_PFD * (1.0 + 0.25 * math.sin(k * 0.01)), False
    _compare(v1, script, ticks=600)


def test_the_recycle_permissive_zeroes_everything_and_matches_v1(v1):
    """LV-324501B forces the dosing pump to zero whatever the controllers are doing."""
    def script(k):
        return M402G_PFD, 150 <= k < 400
    s, master, slave = _compare(v1, script, ticks=600)
    assert s.FIC_335405["op"] == slave.loop.op


def test_the_master_does_not_wind_up_behind_the_permissive(v1):
    """The freeze, stated as the property it exists for.

    Held interlocked for 100 s with a zero measured ratio, an integrating master would ramp
    to its limit and dump that output onto the plant when the permissive cleared.
    """
    s, master, slave = _compare(v1, lambda k: (M402G_PFD, True), ticks=1000)
    assert master.loop.op == pytest.approx(UF_RATIO, rel=1e-12)
    assert master.loop.op < master.loop.op_hi


def test_a_zero_plant_rate_is_treated_as_no_base_flow_in_both(v1):
    """A ratio against a base flow of nothing is arithmetic, not a measurement."""
    _compare(v1, lambda k: (0.0, False), ticks=200)


def test_taking_the_slave_off_cascade_makes_the_master_track_and_matches_v1(v1):
    """External-reset feedback. The master follows the ratio the plant is actually making."""
    def script(k):
        mode = "AUTO" if 200 <= k < 500 else "CAS"
        return M402G_PFD * 0.8, (False, mode)
    s, master, slave = _compare(v1, script, ticks=800)
    assert s.FFIC_335406["op"] == master.loop.op


def test_the_transfer_back_into_cascade_is_bumpless_because_of_the_tracking():
    """What the tracking buys, measured on the rewrite alone.

    While the slave is off cascade the master's output equals the achieved ratio, so the
    demand it hands over on re-entry is the flow the plant is already making.
    """
    master, slave = _v11_cascade()
    slave.loop.set_mode("AUTO")
    slave.loop.set_sp(0.5)                       # the operator holds the slave locally
    for _ in range(599):
        _v11_step(master, slave, M402G_PFD, False, DT)
    #  The master reads the measurement at the TOP of a tick, so the ratio it adopts on the
    #  next one is built from the flow standing now.
    achieved = slave.loop.pv * 1000.0 / M402G_PFD
    _v11_step(master, slave, M402G_PFD, False, DT)
    assert master.loop.op == pytest.approx(achieved, rel=1e-12)

    slave.loop.set_mode("CAS")
    handover = _v11_step(master, slave, M402G_PFD, False, DT)
    assert handover["flow_setpoint_th"] == pytest.approx(slave.loop.pv, rel=1e-3)


def test_a_master_left_in_man_keeps_the_operators_number(v1):
    """Tracking is for an AUTO master. A deliberate MAN command is not overwritten."""
    s = _v1_state()
    master, slave = _v11_cascade()
    s.FFIC_335406["mode"] = "MAN"
    s.FFIC_335406["op"] = 0.02
    master.loop.set_mode("MAN")
    master.loop.op = 0.02
    #  Hold the slave locally at 0.5 t/h, which is NOT the design UF85 flow, so the achieved
    #  ratio moves away from design and the master's history is visibly current.
    s.FIC_335405["mode"] = "AUTO"
    s.FIC_335405["sp"] = 0.5
    slave.loop.set_mode("AUTO")
    slave.loop.set_sp(0.5)
    for k in range(300):
        a = v1["step_uf85_cascade"](s, M402G_PFD, False, DT)
        b = _v11_step(master, slave, M402G_PFD, False, DT)
        assert a == b, f"tick {k}"
    assert master.loop.op == 0.02
    assert master.loop.pv != UF_RATIO        # but it kept watching


def test_a_negative_or_absent_measurement_cannot_make_a_negative_ratio():
    """Floors, not clamps applied afterwards: the ratio is built out of non-negative flows."""
    master, _ = _v11_cascade()
    result = master.step(-500.0, M402G_PFD, DT, slave_in_cascade=True)
    assert result.measured == 0.0
    assert result.demand >= 0.0
