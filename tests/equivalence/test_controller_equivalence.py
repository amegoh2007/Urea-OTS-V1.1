"""V1 <-> V1.1 equivalence for the regulatory controller in `ureasim.control.controller`.

What is being proved
--------------------
A controller is a *stateful* port, which makes it a different risk from a correlation. A
wrong coefficient shows up on the first call; a wrong state update shows up on the
hundredth, after the two implementations have been fed the same inputs and have quietly
diverged. So the tests below do not spot-check the increment — they run both controllers
side by side through whole scenarios and assert the output matches **at every tick**.

The scenarios are the ones an instructor actually sets up: a set-point change, a load
disturbance, a valve driven onto its limit and brought back, a transmitter failing, a
cascade pair with the primary saturating. Each is a thing a trainee is meant to learn to
read, so each is a thing the port must reproduce.

Four behaviours are pinned beyond raw equality, because each could be "tidied" into
something that still passes a casual test:

  * **no reset windup.** The velocity form has no accumulator. A controller held on its
    limit must resume the instant the error reverses, not after an unwinding period.
  * **bumpless transfer.** Into AUTO the set point adopts the PV; into CAS the bias is
    zeroed. Both also clear the PV history.
  * **bad-PV freeze.** A failed transmitter drops the loop to MAN and holds the last good
    output. It does not drive the valve anywhere.
  * **the derivative filter collapses.** As Tf -> 0 the filtered form must become the
    unfiltered one exactly, so that the default is genuinely inert.
"""

from __future__ import annotations

import math

import pytest

from ureasim.control import controller as v11
from tests.equivalence.v1_loader import load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

DT = 0.1


@pytest.fixture(scope="module")
def v1():
    return load("controllers")


def _pair(v1_module, **kwargs):
    """One V1 controller and one V1.1 controller, configured identically."""
    return v1_module.Controller("FIC-322401", **kwargs), v11.Controller("FIC-322401", **kwargs)


def _pv_sequence(n: int) -> list[float]:
    """A deterministic PV trace with a ramp, a step and some ripple.

    Deterministic matters more than realistic here: both implementations must see the
    identical float, so the trace is generated rather than measured.
    """
    trace = []
    for k in range(n):
        base = 40.0 + 0.05 * k
        ripple = 1.5 * math.sin(k * 0.37)
        step = 8.0 if k >= n // 2 else 0.0
        trace.append(base + ripple + step)
    return trace


# --------------------------------------------------------------------------------------
# Configuration constants
# --------------------------------------------------------------------------------------

def test_the_bad_pv_band_and_bias_clamp_are_the_same_numbers(v1):
    assert v11.BAD_PV_LO == v1.BAD_PV_LO
    assert v11.BAD_PV_HI == v1.BAD_PV_HI
    assert v11.CAS_BIAS_LIM == v1.CAS_BIAS_LIM


# --------------------------------------------------------------------------------------
# The increment itself
# --------------------------------------------------------------------------------------

TUNINGS = [
    dict(Kc=2.0, Ti=8.0),                                  # a flow loop, no derivative
    dict(Kc=0.8, Ti=45.0),                                 # a level loop, slow
    dict(Kc=3.5, Ti=12.0, Td=2.0),                         # with derivative, unfiltered
    dict(Kc=3.5, Ti=12.0, Td=2.0, Tf=1.0),                 # with the derivative filter
    dict(Kc=2.0, Ti=8.0, Dz=0.5),                          # with an error deadzone
    dict(Kc=3.5, Ti=12.0, Td=2.0, Tf=1.0, Dz=0.5),         # both
]


@pytest.mark.parametrize("tuning", TUNINGS)
def test_the_pid_increment_matches_v1_at_every_sample(tuning, v1):
    a, b = v1.PID(**tuning), v11.PID(**tuning)
    for pv in _pv_sequence(300):
        assert a.step(50.0, pv, DT) == b.step(50.0, pv, DT)


@pytest.mark.parametrize("tuning", TUNINGS)
def test_a_reset_returns_both_to_the_same_fresh_state(tuning, v1):
    a, b = v1.PID(**tuning), v11.PID(**tuning)
    for pv in _pv_sequence(40):
        a.step(50.0, pv, DT)
        b.step(50.0, pv, DT)
    a.reset()
    b.reset()
    for pv in _pv_sequence(40):
        assert a.step(50.0, pv, DT) == b.step(50.0, pv, DT)


def test_the_first_increment_is_pure_integral_in_both(v1):
    """P and D are seeded to zero so a cold start is a warm-up, not a kick."""
    a, b = v1.PID(Kc=2.0, Ti=8.0, Td=2.0), v11.PID(Kc=2.0, Ti=8.0, Td=2.0)
    first = b.step(50.0, 40.0, DT)
    assert first == a.step(50.0, 40.0, DT)
    assert first == pytest.approx(2.0 * (DT / 8.0) * 10.0, rel=1e-12)


def test_a_zero_or_negative_timestep_kills_the_derivative_in_both(v1):
    a, b = v1.PID(Kc=2.0, Ti=8.0, Td=2.0), v11.PID(Kc=2.0, Ti=8.0, Td=2.0)
    for pv in (40.0, 41.0, 43.0):
        assert a.step(50.0, pv, 0.0) == b.step(50.0, pv, 0.0)


def test_the_derivative_filter_collapses_to_the_unfiltered_form_as_tf_falls():
    """The default Tf = 0 must be genuinely inert, not merely small.

    V1's comment claims the filtered form "collapses EXACTLY to the legacy term as Tf -> 0".
    That claim is what makes it safe to leave the filter in the code path of every loop on
    the plant, so it is asserted rather than trusted.
    """
    def worst_gap(tf: float) -> tuple[float, float]:
        """Largest absolute disagreement over the trace, and the trace's own scale.

        The gap is measured against the LARGEST increment in the run, not against each
        tick's own increment. On the tick after a step change the unfiltered increment
        passes through nearly zero while the filter state is still large, so a per-tick
        ratio there reports a big relative error on a physically negligible number.
        """
        plain = v11.PID(Kc=3.5, Ti=12.0, Td=2.0, Tf=0.0)
        filtered = v11.PID(Kc=3.5, Ti=12.0, Td=2.0, Tf=tf)
        gap = scale = 0.0
        for pv in _pv_sequence(120):
            a = plain.step(50.0, pv, DT)
            b = filtered.step(50.0, pv, DT)
            gap = max(gap, abs(a - b))
            scale = max(scale, abs(a))
        return gap, scale

    # The two forms differ by O(Tf/dt), so at Tf = 1e-9 s against a 0.1 s tick the
    # increments agree to seven significant figures of the signal.
    tiny_gap, scale = worst_gap(1e-9)
    assert tiny_gap / scale < 1e-7
    # And the collapse is first order: a thousand times more filter, a thousand times more
    # gap. That is what makes "exactly as Tf -> 0" a convergence statement rather than a
    # coincidence at one arbitrary value.
    bigger_gap, _ = worst_gap(1e-6)
    assert bigger_gap / tiny_gap == pytest.approx(1000.0, rel=1e-3)


def test_the_deadzone_suppresses_integral_action_inside_the_band_in_both(v1):
    """Inside the band the loop stops chasing; outside it, nothing has changed."""
    a, b = v1.PID(Kc=2.0, Ti=8.0, Dz=1.0), v11.PID(Kc=2.0, Ti=8.0, Dz=1.0)
    a.step(50.0, 50.0, DT)
    b.step(50.0, 50.0, DT)
    inside = b.step(50.0, 50.4, DT)
    assert inside == a.step(50.0, 50.4, DT)
    # Only the proportional term survives inside the band: -(50.4 - 50.0) * Kc.
    assert inside == pytest.approx(2.0 * -(50.4 - 50.0), rel=1e-12)


# --------------------------------------------------------------------------------------
# Whole-loop scenarios
# --------------------------------------------------------------------------------------

def test_an_auto_loop_tracks_v1_tick_for_tick(v1):
    a, b = _pair(v1, Kc=2.0, Ti=8.0, action="REVERSE", rate=10.0)
    a.set_mode("AUTO")
    b.set_mode("AUTO")
    a.set_sp(50.0)
    b.set_sp(50.0)
    for pv in _pv_sequence(600):
        assert a.step(pv, DT) == b.step(pv, DT)


def test_a_direct_acting_loop_tracks_v1_tick_for_tick(v1):
    """Direction is configuration, and a sign error diverges rather than detunes."""
    a, b = _pair(v1, Kc=1.2, Ti=30.0, action="DIRECT", rate=5.0)
    a.set_mode("AUTO")
    b.set_mode("AUTO")
    a.set_sp(50.0)
    b.set_sp(50.0)
    for pv in _pv_sequence(600):
        assert a.step(pv, DT) == b.step(pv, DT)


def test_an_operator_session_of_mode_and_setpoint_changes_tracks_v1(v1):
    """The commands a trainee actually issues, interleaved with the plant moving."""
    a, b = _pair(v1, Kc=2.5, Ti=10.0, Td=1.0, rate=8.0)
    script = {
        20: ("mode", "AUTO"),
        90: ("sp", 55.0),
        180: ("mode", "MAN"),
        200: ("op", 62.0),
        260: ("mode", "AUTO"),
        340: ("sp", 44.0),
        420: ("tuning", dict(Kc=4.0, Ti=6.0)),
        500: ("mode", "OOS"),
    }
    for k, pv in enumerate(_pv_sequence(600)):
        if k in script:
            what, value = script[k]
            for c in (a, b):
                if what == "mode":
                    c.set_mode(value)
                elif what == "sp":
                    c.set_sp(value)
                elif what == "op":
                    c.set_op(value)
                elif what == "tuning":
                    c.set_tuning(**value)
        assert a.step(pv, DT) == b.step(pv, DT), f"tick {k}"


def test_a_cascade_pair_tracks_v1_including_the_bias(v1):
    """Primary on level, secondary on flow — the arrangement on every drum on the plant."""
    prim_a, prim_b = _pair(v1, Kc=0.8, Ti=60.0, rate=4.0)
    sec_a = v1.Controller("FIC-323502", Kc=2.0, Ti=6.0, rate=20.0)
    sec_b = v11.Controller("FIC-323502", Kc=2.0, Ti=6.0, rate=20.0)
    for c in (prim_a, prim_b):
        c.set_mode("AUTO")
        c.set_sp(50.0)
    for c in (sec_a, sec_b):
        c.set_mode("CAS")

    level = _pv_sequence(400)
    flow = _pv_sequence(400)[::-1]
    for k in range(400):
        if k == 150:
            sec_a.set_bias(6.0)
            sec_b.set_bias(6.0)
        if k == 300:
            sec_a.set_bias(-4.0)
            sec_b.set_bias(-4.0)
        cas_a = prim_a.step(level[k], DT)
        cas_b = prim_b.step(level[k], DT)
        assert cas_a == cas_b, f"primary, tick {k}"
        assert sec_a.step(flow[k], DT, cas_a) == sec_b.step(flow[k], DT, cas_b), f"tick {k}"
        assert sec_a.sp == sec_b.sp


def test_a_cascade_secondary_with_no_primary_signal_holds_its_setpoint(v1):
    """`cas_sp=None` is a primary that has not published yet, not a command to go to zero."""
    a, b = _pair(v1, Kc=2.0, Ti=8.0)
    a.set_mode("CAS")
    b.set_mode("CAS")
    a.set_sp(47.0)
    b.set_sp(47.0)
    for pv in _pv_sequence(120):
        assert a.step(pv, DT, None) == b.step(pv, DT, None)
    assert b.sp == 47.0


# --------------------------------------------------------------------------------------
# Limits, windup and failure
# --------------------------------------------------------------------------------------

def test_a_loop_driven_onto_its_output_limit_tracks_v1_and_reports_the_clamp(v1):
    a, b = _pair(v1, Kc=6.0, Ti=3.0, rate=50.0, op_lo=0.0, op_hi=100.0)
    a.set_mode("AUTO")
    b.set_mode("AUTO")
    a.set_sp(95.0)
    b.set_sp(95.0)
    for _ in range(300):
        assert a.step(10.0, DT) == b.step(10.0, DT)
    assert b.mv == 100.0
    assert b.as_packet()["status"]["mv_hi_clamp"] is True
    assert a.to_packet()["status"] == b.as_packet()["status"]


def test_a_clamped_loop_resumes_immediately_because_there_is_nothing_to_unwind():
    """The property the velocity form exists for.

    A positional controller saturated for 30 s carries 30 s of accumulated integral and
    cannot move off its limit until that has unwound. This one leaves the limit on the first
    tick the error reverses. An operator taught on the wrong one waits for a recovery that
    is already available.
    """
    c = v11.Controller("FIC-322401", Kc=6.0, Ti=3.0, rate=50.0)
    c.set_mode("AUTO")
    c.set_sp(95.0)
    for _ in range(300):        # 30 s hard against the high limit
        c.step(10.0, DT)
    assert c.mv == 100.0
    first_move = c.step(99.0, DT)   # error reverses
    assert first_move < 100.0


def test_a_failed_transmitter_drops_the_loop_to_man_and_freezes_the_output(v1):
    a, b = _pair(v1, Kc=2.0, Ti=8.0, rate=10.0)
    a.set_mode("AUTO")
    b.set_mode("AUTO")
    a.set_sp(50.0)
    b.set_sp(50.0)
    for pv in _pv_sequence(100):
        a.step(pv, DT)
        b.step(pv, DT)
    held = b.mv
    for bad in (None, float("nan"), -7.0, 130.0):
        assert a.step(bad, DT) == b.step(bad, DT)
        assert b.mv == held
        assert b.mode == "MAN"
        assert b.as_packet()["status"]["pv_bad"] is True


def test_the_loop_does_not_climb_back_into_auto_by_itself(v1):
    """A recovered transmitter clears the bad flag; it does not re-close the loop.

    Putting the loop back in AUTO is the operator's decision and the operator's action. A
    controller that restored itself would hide the event that the trainee is supposed to
    notice.
    """
    a, b = _pair(v1, Kc=2.0, Ti=8.0)
    a.set_mode("AUTO")
    b.set_mode("AUTO")
    a.step(50.0, DT)
    b.step(50.0, DT)
    a.step(float("nan"), DT)
    b.step(float("nan"), DT)
    assert a.step(50.0, DT) == b.step(50.0, DT)
    assert b.mode == "MAN"
    assert b.as_packet()["status"]["pv_bad"] is False


@pytest.mark.parametrize("fail_action,expected", [("FC", 0.0), ("FO", 100.0)])
def test_an_out_of_service_loop_ramps_to_its_fail_position_as_v1_does(fail_action, expected,
                                                                     v1):
    a, b = _pair(v1, rate=10.0, fail_action=fail_action, mv=50.0)
    a.set_mode("OOS")
    b.set_mode("OOS")
    for _ in range(200):
        assert a.step(50.0, DT) == b.step(50.0, DT)
    assert b.mv == expected


def test_a_fail_last_loop_stays_where_it_was(v1):
    a, b = _pair(v1, rate=10.0, fail_action="FL", mv=37.0)
    a.set_mode("OOS")
    b.set_mode("OOS")
    for _ in range(50):
        assert a.step(50.0, DT) == b.step(50.0, DT)
    assert b.mv == 37.0


def test_the_slew_limit_bounds_the_output_move_per_tick(v1):
    """What stops a large increment slamming a valve — and what makes a loop look sluggish
    when it is set too low. Both are plant behaviours, so the limiter is not a safety net."""
    a, b = _pair(v1, Kc=50.0, Ti=1.0, rate=2.0, mv=50.0)
    a.set_mode("AUTO")
    b.set_mode("AUTO")
    a.set_sp(100.0)
    b.set_sp(100.0)
    previous = b.mv
    for _ in range(50):
        assert a.step(20.0, DT) == b.step(20.0, DT)
        assert abs(b.mv - previous) <= 2.0 * DT + 1e-12
        previous = b.mv


# --------------------------------------------------------------------------------------
# Bumpless transfer
# --------------------------------------------------------------------------------------

def test_entering_auto_adopts_the_current_pv_as_the_setpoint(v1):
    a, b = _pair(v1, Kc=2.0, Ti=8.0, sp=90.0)
    a.step(43.5, DT)
    b.step(43.5, DT)
    a.set_mode("AUTO")
    b.set_mode("AUTO")
    assert a.sp == b.sp == 43.5
    # And the first AUTO tick therefore moves the output by almost nothing.
    assert abs(b.step(43.5, DT) - b.mv) < 1e-12


def test_entering_auto_respects_the_setpoint_range(v1):
    """A PV outside the configured SP span cannot become a set point outside it."""
    a, b = _pair(v1, sp_lo=20.0, sp_hi=80.0)
    a.step(95.0, DT)
    b.step(95.0, DT)
    a.set_mode("AUTO")
    b.set_mode("AUTO")
    assert a.sp == b.sp == 80.0


def test_entering_cascade_zeroes_a_stale_bias(v1):
    a, b = _pair(v1, Kc=2.0, Ti=8.0)
    a.set_mode("CAS")
    b.set_mode("CAS")
    a.set_bias(15.0)
    b.set_bias(15.0)
    a.set_mode("MAN")
    b.set_mode("MAN")
    a.set_mode("CAS")
    b.set_mode("CAS")
    assert a.bias == b.bias == 0.0


def test_the_cascade_bias_cannot_saturate_the_secondary_setpoint(v1):
    """V1 finding P1-1. An unbounded bias is a loop that never comes back."""
    a, b = _pair(v1)
    a.set_mode("CAS")
    b.set_mode("CAS")
    a.set_bias(1e6)
    b.set_bias(1e6)
    assert a.bias == b.bias == v11.CAS_BIAS_LIM
    a.set_bias(-1e6)
    b.set_bias(-1e6)
    assert a.bias == b.bias == -v11.CAS_BIAS_LIM


def test_retuning_does_not_move_the_output(v1):
    """The velocity form multiplies an INCREMENT, so a gain change is bumpless by
    construction. A positional controller would step the moment Kc changed."""
    a, b = _pair(v1, Kc=2.0, Ti=8.0, rate=10.0)
    a.set_mode("AUTO")
    b.set_mode("AUTO")
    for pv in _pv_sequence(100):
        a.step(pv, DT)
        b.step(pv, DT)
    before = b.mv
    a.set_tuning(Kc=9.0, Ti=2.0)
    b.set_tuning(Kc=9.0, Ti=2.0)
    assert b.mv == before
    assert a.Kc == b.Kc == 9.0
    assert a.Ti == b.Ti == 2.0


def test_a_setpoint_change_does_not_kick_the_valve_but_a_load_change_does():
    """The I-PD arrangement, stated as the behaviour a trainee reads off the trend.

    A set-point step moves only the integral term, so the first output move is small. The
    same size of step in the PV moves the proportional term too, so the first output move is
    large. If the port had put P on error, the two would look alike and the distinction
    would be untrainable.
    """
    def settled() -> v11.Controller:
        c = v11.Controller("FIC-322401", Kc=4.0, Ti=20.0, rate=100.0, mv=50.0)
        c.step(50.0, DT)        # publish a PV for the bumpless AUTO transfer to adopt
        c.set_mode("AUTO")
        for _ in range(50):
            c.step(50.0, DT)    # sitting at zero error, output stationary
        return c

    on_sp = settled()
    before = on_sp.mv
    on_sp.set_sp(60.0)
    on_sp.step(50.0, DT)
    sp_kick = abs(on_sp.mv - before)

    on_pv = settled()
    before = on_pv.mv
    on_pv.step(40.0, DT)        # the same 10-unit change, in the measurement instead
    pv_kick = abs(on_pv.mv - before)

    # A set-point step moves the integral term alone: Kc . (dt/Ti) . 10.
    assert sp_kick == pytest.approx(4.0 * (DT / 20.0) * 10.0, rel=1e-12)
    assert pv_kick > 10.0 * sp_kick


# --------------------------------------------------------------------------------------
# The published faceplate record
# --------------------------------------------------------------------------------------

def test_the_faceplate_packet_is_identical_to_v1s(v1):
    """The HMI renders this dictionary. A renamed key is a blank field on a live console."""
    a, b = _pair(v1, Kc=2.5, Ti=10.0, Td=1.0, Tf=0.5, Dz=0.2,
                 action="DIRECT", op_lo=5.0, op_hi=95.0, sp_lo=10.0, sp_hi=90.0,
                 rate=7.5, fail_action="FO")
    a.set_mode("AUTO")
    b.set_mode("AUTO")
    a.set_sp(60.0)
    b.set_sp(60.0)
    for pv in _pv_sequence(150):
        a.step(pv, DT, 61.0)
        b.step(pv, DT, 61.0)
    assert a.to_packet() == b.as_packet()
    assert list(a.to_packet()) == list(b.as_packet())


def test_an_unknown_mode_is_refused_by_both(v1):
    a, b = _pair(v1)
    with pytest.raises(ValueError):
        a.set_mode("TRACK")
    with pytest.raises(ValueError):
        b.set_mode("TRACK")
