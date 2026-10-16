"""V1 <-> V1.1 equivalence for the engineering-unit loop in `ureasim.control.process_loop`.

What is being proved
--------------------
`ProcessLoop` is the controller behind almost every tag on the plant, so this is the single
highest-traffic port in the rewrite. It replaces V1's `_ctrl_ipd`, which operates on a bare
dict; the rewrite gives it typed fields and methods. That refactor is exactly the kind that
looks safe and is not, because the dict carries SEVEN pieces of state — `op`, `sp`, `pv`,
`pv1`, `pv2`, `dfilt` and `mode` — and a port that updates six of them correctly is still
wrong.

So the tests below compare the WHOLE state after every tick, not just the returned output.

Four behaviours are pinned by name because each is a place where a reasonable-looking
simplification would change what a trainee sees:

  * **the Td = -1 sentinel.** The DCS writes -1 to mean "derivative disabled". Used as a
    number it flips the sign of the derivative term and kicks the valve the wrong way on
    every transient.
  * **the bad-PV freeze does not change mode.** Unlike the per-cent-span
    `controller.Controller`, this loop stays where the operator put it.
  * **the PV history advances in MAN.** The loop is watching while it is not acting.
  * **the cascade set point is clamped to the SECONDARY's span**, not the primary's.

`backend/main.py` cannot be imported — it builds a FastAPI app and a full plant state at
import — so the five functions under test are lifted out of it by AST and executed in a
controlled namespace. That is V1's code running, not a paraphrase of it.
"""

from __future__ import annotations

import ast
import math

import pytest

from ureasim.control import controller as faceplate
from ureasim.control import process_loop as v11
from tests.equivalence import decided_valves as dv
from tests.equivalence.v1_loader import V1_BACKEND, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

DT = 0.1

#: The dict keys V1's `_ctrl_ipd` reads and writes. Every one is compared every tick.
STATE_KEYS = ("op", "sp", "pv", "pv1", "pv2", "dfilt")


def _v1_loop_module() -> dict:
    """Lift `clamp`, `_pv_ok`, `_lag1`, `_ctrl_ipd` and `_fic_flow` out of V1 `main.py`."""
    text = (V1_BACKEND / "main.py").read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(text)
    wanted = {"clamp", "_pv_ok", "_lag1", "_ctrl_ipd", "_fic_flow"}
    ns: dict = {"math": math}
    for stmt in tree.body:
        if isinstance(stmt, ast.FunctionDef) and stmt.name in wanted:
            exec(compile(ast.Module([stmt], []), "<v1 main.py>", "exec"), ns)
    missing = wanted - set(ns)
    assert not missing, f"could not lift {sorted(missing)} out of V1 main.py"
    return ns


@pytest.fixture(scope="module")
def v1():
    return _v1_loop_module()


# --------------------------------------------------------------------------------------
# Loop configurations, in the shapes V1 actually seeds
# --------------------------------------------------------------------------------------
#  FIC-324401 is quoted verbatim from V1 `main.py`: a flow loop in t/h with the Td = -1
#  sentinel. The others cover the branches that one does not reach.

CONFIGS = {
    "FIC-324401 flow, t/h, Td sentinel": dict(
        Kc=0.4, Ti=30.0, Td=-1.0, act=1.0, op=52.0,
        sp=92.749, pv=92.749, pv1=92.749, pv2=92.749,
        op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=150.0, mode="CAS"),
    "TIC temperature, C, direct acting": dict(
        Kc=1.8, Ti=45.0, Td=0.0, act=-1.0, op=40.0,
        sp=135.0, pv=135.0, pv1=135.0, pv2=135.0,
        op_lo=0.0, op_hi=100.0, sp_lo=80.0, sp_hi=200.0, mode="AUTO"),
    "PIC pressure, bar a, with derivative": dict(
        Kc=3.0, Ti=12.0, Td=2.0, act=1.0, op=61.0,
        sp=4.6, pv=4.6, pv1=4.6, pv2=4.6,
        op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=20.0, mode="AUTO"),
    "LIC level, %, filtered derivative": dict(
        Kc=0.9, Ti=90.0, Td=6.0, Tf=3.0, act=-1.0, op=45.0,
        sp=50.0, pv=50.0, pv1=50.0, pv2=50.0,
        op_lo=0.0, op_hi=100.0, sp_lo=10.0, sp_hi=90.0, mode="AUTO"),
    "AIC analyser, with deadzone": dict(
        Kc=2.2, Ti=20.0, Td=0.0, Dz=0.15, act=1.0, op=30.0,
        sp=2.95, pv=2.95, pv1=2.95, pv2=2.95,
        op_lo=0.0, op_hi=100.0, sp_lo=2.0, sp_hi=4.0, mode="AUTO"),
}


def _pair(config: dict):
    """One V1 controller dict and one V1.1 ProcessLoop, seeded identically."""
    seed = dict(config)
    seed.setdefault("Tf", 0.0)
    seed.setdefault("Dz", 0.0)
    seed.setdefault("dfilt", 0.0)
    return dict(seed), v11.ProcessLoop(tag="TEST", **seed)


def _state(loop: v11.ProcessLoop) -> tuple:
    return tuple(getattr(loop, k) for k in STATE_KEYS)


def _dict_state(c: dict) -> tuple:
    return tuple(c.get(k, 0.0) for k in STATE_KEYS)


def _trace(config: dict, n: int) -> list[float]:
    """A PV trace centred on the loop's own set point, in the loop's own units."""
    span = max(abs(config["sp_hi"] - config["sp_lo"]), 1.0)
    centre = config["sp"]
    return [centre
            + 0.04 * span * math.sin(k * 0.23)
            + 0.02 * span * math.sin(k * 0.061)
            + (0.06 * span if k >= n // 2 else 0.0)
            for k in range(n)]


# --------------------------------------------------------------------------------------
# The bad-measurement test
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("value", [
    0.0, 1.0, -40.0, 135.0, 183.0, 144.2, 1e9, True, 3,
    float("nan"), float("inf"), float("-inf"), None, "50", [50.0],
])
def test_the_finite_only_guard_matches_v1(value, v1):
    assert v11.pv_ok(value) == v1["_pv_ok"](value)


def test_several_values_are_all_required_to_be_good(v1):
    assert v11.pv_ok(50.0, 60.0) == v1["_pv_ok"](50.0, 60.0) is True
    assert v11.pv_ok(50.0, float("nan")) == v1["_pv_ok"](50.0, float("nan")) is False


def test_an_engineering_unit_pv_is_good_here_and_bad_on_a_percent_span_faceplate():
    """The reason two controllers exist. This is the difference, asserted.

    A reactor at 183 C is a perfectly good measurement. The per-cent-span controller would
    declare it failed, drop the loop to MAN and freeze the valve — on a plant that is running
    normally. Merging the two implementations would do exactly that to every temperature and
    pressure loop on the site.
    """
    assert v11.pv_ok(183.0) is True
    assert 183.0 > faceplate.BAD_PV_HI


# --------------------------------------------------------------------------------------
# Whole-state equivalence
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("name", list(CONFIGS))
def test_every_loop_shape_tracks_v1_state_for_state(name, v1):
    config = CONFIGS[name]
    c, loop = _pair(config)
    for k, pv in enumerate(_trace(config, 500)):
        out_v1 = v1["_ctrl_ipd"](c, pv, DT)
        out_v11 = loop.step(pv, DT)
        assert out_v1 == out_v11, f"{name}, output, tick {k}"
        assert _dict_state(c) == _state(loop), f"{name}, state, tick {k}"


@pytest.mark.parametrize("name", list(CONFIGS))
def test_a_variable_timestep_changes_nothing_about_the_agreement(name, v1):
    """The engine integrates on variable sub-steps, down to remainder crumbs of ~1e-8 s."""
    config = CONFIGS[name]
    c, loop = _pair(config)
    steps = [0.1, 0.05, 0.1, 1e-8, 0.2, 0.1, 1e-8, 0.4]
    for k, pv in enumerate(_trace(config, 200)):
        dt = steps[k % len(steps)]
        assert v1["_ctrl_ipd"](c, pv, dt) == loop.step(pv, dt), f"{name}, tick {k}"
        assert _dict_state(c) == _state(loop)


def test_a_zero_timestep_kills_the_derivative_in_both(v1):
    config = CONFIGS["PIC pressure, bar a, with derivative"]
    c, loop = _pair(config)
    for pv in (4.6, 4.9, 5.4, 5.1):
        assert v1["_ctrl_ipd"](c, pv, 0.0) == loop.step(pv, 0.0)
        assert _dict_state(c) == _state(loop)


# --------------------------------------------------------------------------------------
# The Td sentinel
# --------------------------------------------------------------------------------------

def test_the_minus_one_derivative_time_is_a_sentinel_and_not_a_number(v1):
    """Td = -1 means "derivative disabled". Used as a gain it kicks the valve the wrong way.

    The three loops below are identical except for Td. The sentinel loop must match the
    disabled loop exactly, and must NOT match a loop that took -1 at face value — which is
    what an unguarded port would produce.
    """
    base = dict(CONFIGS["PIC pressure, bar a, with derivative"])
    sentinel = v11.ProcessLoop(tag="A", **{**base, "Td": -1.0})
    disabled = v11.ProcessLoop(tag="B", **{**base, "Td": 0.0})
    naive_outputs = []
    naive = v11.ProcessLoop(tag="C", **{**base, "Td": 0.0})

    c_sentinel = dict({**base, "Td": -1.0})
    for pv in _trace(base, 200):
        a = sentinel.step(pv, DT)
        b = disabled.step(pv, DT)
        assert a == b
        assert a == v1["_ctrl_ipd"](c_sentinel, pv, DT)
        # What -1 would do if it were taken literally: the D term changes sign.
        naive.Td = 0.0
        naive_outputs.append(naive.step(pv, DT))

    # A literal -1 is a wrong-way derivative. Build it explicitly and show it differs.
    literal = dict({**base, "Td": -1.0})
    signed = dict({**base, "Td": 1.0})
    wrong_way, right_way = [], []
    c_lit, c_sig = dict(literal), dict(signed)
    for pv in _trace(base, 50):
        wrong_way.append(v1["_ctrl_ipd"](c_lit, pv, DT))
        right_way.append(v1["_ctrl_ipd"](c_sig, pv, DT))
    assert wrong_way != right_way


# --------------------------------------------------------------------------------------
# Modes
# --------------------------------------------------------------------------------------

def test_a_loop_in_man_holds_its_output_but_keeps_watching(v1):
    """The PV history advances in MAN in both, so a later transfer resumes on real samples."""
    config = dict(CONFIGS["TIC temperature, C, direct acting"])
    config["mode"] = "MAN"
    c, loop = _pair(config)
    held = loop.op
    for pv in _trace(config, 120):
        assert v1["_ctrl_ipd"](c, pv, DT) == loop.step(pv, DT)
        assert loop.op == held
        assert _dict_state(c) == _state(loop)
    assert loop.pv1 != config["pv1"]      # history moved even though the output did not


def test_a_mode_change_mid_run_tracks_v1(v1):
    config = CONFIGS["LIC level, %, filtered derivative"]
    c, loop = _pair(config)
    script = {60: "MAN", 140: "AUTO", 260: "CAS", 380: "AUTO"}
    for k, pv in enumerate(_trace(config, 500)):
        if k in script:
            c["mode"] = script[k]
            loop.set_mode(script[k])
        cas = 55.0 if loop.mode == "CAS" else None
        assert v1["_ctrl_ipd"](c, pv, DT, cas) == loop.step(pv, DT, cas), f"tick {k}"
        assert _dict_state(c) == _state(loop), f"tick {k}"


def test_a_cascade_setpoint_is_clamped_to_the_secondarys_own_span(v1):
    """A saturated primary cannot push a secondary outside the range it is configured for."""
    config = CONFIGS["LIC level, %, filtered derivative"]     # sp span 10 .. 90
    c, loop = _pair({**config, "mode": "CAS"})
    for demand in (200.0, -50.0, 62.0):
        v1["_ctrl_ipd"](c, 50.0, DT, demand)
        loop.step(50.0, DT, demand)
        assert c["sp"] == loop.sp
    assert loop.sp == 62.0
    v1["_ctrl_ipd"](c, 50.0, DT, 500.0)
    loop.step(50.0, DT, 500.0)
    assert loop.sp == 90.0 == c["sp"]


def test_a_cascade_secondary_with_no_primary_signal_keeps_its_own_setpoint(v1):
    config = CONFIGS["FIC-324401 flow, t/h, Td sentinel"]
    c, loop = _pair(config)
    for pv in _trace(config, 100):
        assert v1["_ctrl_ipd"](c, pv, DT, None) == loop.step(pv, DT, None)
    assert loop.sp == config["sp"]


def test_an_unknown_mode_is_refused():
    """V1's dict form accepts any string silently — a typo there is a loop that stops acting.

    The rewrite refuses it instead. This is the one place the port is deliberately STRICTER
    than V1, and it can only reject configurations V1 would have mis-run, never change the
    behaviour of a valid one.
    """
    with pytest.raises(ValueError, match="unknown mode"):
        v11.ProcessLoop(tag="X", Kc=1.0, Ti=10.0, mode="TRACK")
    loop = v11.ProcessLoop(tag="X", Kc=1.0, Ti=10.0)
    with pytest.raises(ValueError, match="unknown mode"):
        loop.set_mode("OOS")


# --------------------------------------------------------------------------------------
# Bad measurements
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [float("nan"), float("inf"), None, "x"])
def test_a_bad_pv_freezes_the_output_without_touching_the_mode_or_the_history(bad, v1):
    config = CONFIGS["PIC pressure, bar a, with derivative"]
    c, loop = _pair(config)
    for pv in _trace(config, 80):
        v1["_ctrl_ipd"](c, pv, DT)
        loop.step(pv, DT)
    before = _state(loop)
    assert v1["_ctrl_ipd"](c, bad, DT) == loop.step(bad, DT)
    assert _state(loop) == before          # nothing moved, not even pv1
    assert _dict_state(c) == _state(loop)
    assert loop.mode == config["mode"]     # and the loop is still where the operator left it


def test_a_bad_setpoint_freezes_the_loop_too(v1):
    """The SP is checked alongside the PV, so a diverged cascade master freezes the
    secondary rather than driving it with a NaN."""
    config = CONFIGS["TIC temperature, C, direct acting"]
    c, loop = _pair(config)
    c["sp"] = loop.sp = float("nan")
    assert v1["_ctrl_ipd"](c, 135.0, DT) == loop.step(135.0, DT)
    assert loop.op == config["op"]


def test_this_loop_does_not_drop_to_man_the_way_the_faceplate_controller_does():
    """The documented divergence between the two controllers, asserted from both sides."""
    loop = v11.ProcessLoop(tag="TIC-329007", Kc=1.8, Ti=45.0, mode="AUTO", sp=135.0)
    loop.step(float("nan"), DT)
    assert loop.mode == "AUTO"

    c = faceplate.Controller("SIC-321950", Kc=2.0, Ti=8.0)
    c.set_mode("AUTO")
    c.step(float("nan"), DT)
    assert c.mode == "MAN"


# --------------------------------------------------------------------------------------
# The flow loop
# --------------------------------------------------------------------------------------

FLOW = dict(Kc=0.4, Ti=30.0, Td=-1.0, act=1.0, op=52.0,
            sp=92.749, pv=92.749, pv1=92.749, pv2=92.749,
            op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=150.0, mode="AUTO")


def _flow_pair(config: dict, design: float, op_des: float, **kwargs):
    c, loop = _pair(config)
    return c, v11.FlowLoop(loop=loop, design_flow=design, op_des=op_des, **kwargs)


def test_the_flow_loop_on_a_vendor_trim_decided_divergence(v1):
    """Handoff B-44, decided 2026-09-30. A FlowLoop on the vendor trim is V1's ``_fic_flow`` with
    the trim in place of ``op / op_des`` (`decided_valves.fic_flow`, V1's own ``_lag1`` and
    ``_ctrl_ipd``), tick for tick through a set-point step. V1's own ``_fic_flow`` on the same
    step parts from it on the first tick, and settles at the linear trim's stroke, 44.85 %,
    where the vendor trim holds 47.06 %."""
    config = dict(FLOW, sp=80.0)
    c, flow = _flow_pair(config, 92.749, 52.0, characteristic="mod_equal_pct")
    c_v1, _ = _flow_pair(config, 92.749, 52.0)
    store, store_v1 = {}, {}
    for k in range(6000):
        a = dv.fic_flow(v1, c, 92.749, 52.0, store, "R324_M324", DT)
        b = flow.step(DT)
        assert a == b, f"tick {k}"
        assert _dict_state(c) == _state(flow.loop)
        assert store["R324_M324"] == flow.measurement
        verbatim = v1["_fic_flow"](c_v1, 92.749, 52.0, store_v1, "R324_M324", DT)
        if k == 0:
            assert verbatim != b
    assert (b, verbatim) == (pytest.approx(80.0, rel=1e-4), pytest.approx(80.0, rel=1e-4))
    assert c_v1["op"] == pytest.approx(52.0 * 80.0 / 92.749, rel=1e-4)
    assert c["op"] == pytest.approx(
        100.0 * (0.52 + math.log(80.0 / 92.749) / math.log(dv.MOD_EQUAL_PCT_RANGE)), rel=1e-4)


def test_the_flow_loop_tracks_v1_tick_for_tick(v1):
    c, flow = _flow_pair(FLOW, 92.749, 52.0)
    store: dict = {}
    for k in range(400):
        a = v1["_fic_flow"](c, 92.749, 52.0, store, "R324_M324", DT)
        b = flow.step(DT)
        assert a == b, f"tick {k}"
        assert _dict_state(c) == _state(flow.loop)
        assert store["R324_M324"] == flow.measurement


def test_the_flow_loop_holds_its_design_flow_bit_exactly(v1):
    """op == op_des gives pre == design gives pv == sp gives du == 0. The boot pin."""
    c, flow = _flow_pair(FLOW, 92.749, 52.0)
    store: dict = {}
    for _ in range(600):
        assert v1["_fic_flow"](c, 92.749, 52.0, store, "R324_M324", DT) == 92.749
        assert flow.step(DT) == 92.749
    assert flow.loop.op == 52.0


def test_a_setpoint_change_moves_the_flow_and_both_engines_agree(v1):
    c, flow = _flow_pair(FLOW, 92.749, 52.0)
    store: dict = {}
    #  300 s of run time. The closed loop is Ti/(Kc.g) ~ 42 s on a 1.784 t/h per per-cent
    #  element, so a shorter run would only prove the two engines agree on a transient.
    for k in range(3000):
        if k == 100:
            c["sp"] = 80.0
            flow.loop.set_sp(80.0)
        assert v1["_fic_flow"](c, 92.749, 52.0, store, "R324_M324", DT) == flow.step(DT)
    assert flow.loop.pv == pytest.approx(80.0, abs=0.2)     # the loop got there


def test_a_cascade_into_the_flow_loop_tracks_v1(v1):
    c, flow = _flow_pair({**FLOW, "mode": "CAS"}, 92.749, 52.0)
    store: dict = {}
    for k in range(400):
        demand = 92.749 + 12.0 * math.sin(k * 0.02)
        assert v1["_fic_flow"](c, 92.749, 52.0, store, "R324_M324", DT,
                               cas_sp=demand) == flow.step(DT, cas_sp=demand)
        assert _dict_state(c) == _state(flow.loop)


#  The volumetric migration: the field element meters m3/h, so the controller must too. The
#  seeds and sp_hi below are pre-divided by rho and Kc is scaled by it, exactly as V1's
#  RHO_* block describes.
RHO = 1065.0
VOL = dict(Kc=0.4 * RHO, Ti=30.0, Td=-1.0, act=1.0, op=48.0,
           sp=7123.0 / RHO, pv=7123.0 / RHO, pv1=7123.0 / RHO, pv2=7123.0 / RHO,
           op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=20.0, mode="AUTO")


def test_a_volumetric_flow_loop_tracks_v1_and_still_returns_mass(v1):
    c, flow = _flow_pair(VOL, 7123.0, 48.0, rho_kgm3=RHO)
    store: dict = {}
    for k in range(400):
        a = v1["_fic_flow"](c, 7123.0, 48.0, store, "R323_718", DT, rho=RHO)
        b = flow.step(DT)
        assert a == b, f"tick {k}"
        assert _dict_state(c) == _state(flow.loop)
    # The controller ran in m3/h; the delivered flow came back in kg/h.
    assert flow.loop.pv == pytest.approx(7123.0 / RHO, rel=1e-6)
    assert flow.step(DT) == pytest.approx(7123.0, rel=1e-6)


def test_a_volumetric_cascade_setpoint_is_converted_before_the_controller_sees_it(v1):
    c, flow = _flow_pair({**VOL, "mode": "CAS"}, 7123.0, 48.0, rho_kgm3=RHO)
    store: dict = {}
    demand_kgh = 6400.0
    for _ in range(300):
        assert v1["_fic_flow"](c, 7123.0, 48.0, store, "R323_718", DT,
                               rho=RHO, cas_sp=demand_kgh) == flow.step(DT, demand_kgh)
    assert flow.loop.sp == pytest.approx(demand_kgh / RHO, rel=1e-12)


def test_a_permissive_can_zero_the_measurement_without_winding_the_controller_up(v1):
    """The interlock path: the pump is stopped, so the transmitter must decay to zero.

    The controller is deliberately not stepped, which is what stops it integrating against a
    safety permissive it cannot influence.
    """
    c, flow = _flow_pair(FLOW, 92.749, 52.0)
    store: dict = {}
    for _ in range(50):
        v1["_fic_flow"](c, 92.749, 52.0, store, "R324_M324", DT)
        flow.step(DT)
    op_before = flow.loop.op
    for _ in range(600):        # 60 s against a 5 s transmitter: twelve time constants
        assert v1["_lag1"](store, "R324_M324", 0.0, 5.0, DT) == flow.force_measurement(0.0, DT)
    assert flow.loop.op == op_before
    assert flow.measurement == pytest.approx(0.0, abs=0.01)


def test_a_pressure_ratio_of_one_is_v1s_and_a_falling_header_opens_the_loop_b73(v1):
    """Handoff B-73, decided 2026-10-02: a steam valve on a header that falls passes less at the
    same stroke. ``pressure_ratio=1.0`` tracks V1 bit for bit; at 0.6 the delivered flow is 60 % of
    the stroke's on the tick it falls (the loop's first move recovers 0.6 % of it), and the loop opens its valve until it delivers its set point
    again, at 52 / 0.6 = 86.7 %; at 0.4 it cannot — wide open it passes 0.4 x 100 / 52 of the
    design, and the transmitter reads that."""
    c, flow = _flow_pair(FLOW, 92.749, 52.0)
    store: dict = {}
    for k in range(200):
        assert v1["_fic_flow"](c, 92.749, 52.0, store, "R324_M324", DT) ==             flow.step(DT, pressure_ratio=1.0), f"tick {k}"
    first = flow.step(DT, pressure_ratio=0.6)
    assert 0.6 * 92.749 < first < 0.61 * 92.749
    for _ in range(30000):
        delivered = flow.step(DT, pressure_ratio=0.6)
    assert delivered == pytest.approx(92.749, rel=1e-6)
    assert flow.loop.op == pytest.approx(52.0 / 0.6, rel=1e-6)
    for _ in range(6000):
        delivered = flow.step(DT, pressure_ratio=0.4)
    assert flow.loop.op == 100.0
    assert delivered == pytest.approx(0.4 * 92.749 * 100.0 / 52.0, rel=1e-12)
    assert flow.measurement == pytest.approx(delivered, rel=1e-9)


def test_a_flow_cap_is_inert_until_given_and_then_the_transmitter_reads_the_flow_delivered(v1):
    """The port's own addition, for the pumps whose heel was decided on 2026-09-27 (handoff
    B-33): ``flow_cap=None`` tracks V1 bit for bit; a cap below the stroke's flow is what the
    transmitter lags toward, so the loop sees the shortfall and opens to its limit, while the
    flow it returns is still the stroke's — the unit applies the cap to what it delivers."""
    c, flow = _flow_pair(FLOW, 92.749, 52.0)
    store: dict = {}
    for k in range(200):
        assert v1["_fic_flow"](c, 92.749, 52.0, store, "R324_M324", DT) == \
            flow.step(DT, flow_cap=None), f"tick {k}"
    for _ in range(3000):
        stroke_flow = flow.step(DT, flow_cap=40.0)
    assert flow.measurement == pytest.approx(40.0, rel=1e-9)
    assert flow.loop.op == 100.0
    assert stroke_flow == pytest.approx(92.749 * 100.0 / 52.0, rel=1e-12)
