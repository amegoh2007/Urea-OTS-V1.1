"""The fixed-step simulator — `ureasim.engine.simulator`.

Pins the law decided under handoff A-14: the plant advances in whole steps of exactly 0.1 s;
the wall clock, times the pacing, decides only how many; the remainder carries exactly; a pass
owes at most V1's 0.5 s. And the replay test the item closes on: the same exercise run at x1 and
x10, on irregular wall-clock passes, is the same sequence of plant states, bit for bit — here on
328C003 with its overhead shut, SV32852 cycling, the stiffest transient the ported plant has.
"""

from __future__ import annotations

import pytest

from ureasim.data import desorption_train as t
from ureasim.data.engine import DT_NS, DT_S, MAX_PASS_NS, SIM_SPEED
from ureasim.engine.simulator import Simulator
from ureasim.units.desorption import hydrolyser as hy

MS = 1_000_000


def _counter():
    seen = []
    return seen, (lambda dt: seen.append(dt))


def test_slow_pays_a_step_per_tenth_of_a_wall_clock_second():
    seen, step = _counter()
    sim = Simulator(step)
    assert [sim.advance(100 * MS) for _ in range(3)] == [1, 1, 1]
    assert [sim.advance(50 * MS) for _ in range(4)] == [0, 1, 0, 1]
    assert seen == [DT_S] * 5 and sim.steps == 5 and sim.owed_ns == 0


def test_each_pacing_pays_its_factor_in_steps_for_the_same_tenth():
    """x1 to x10 in steps of one (decision 321): a tenth of a wall-clock second pays n steps of
    0.1 s at xn, never a larger step."""
    assert list(SIM_SPEED) == [f"x{n}" for n in range(1, 11)]
    assert Simulator(_counter()[1]).pacing == "x1"
    for n in range(1, 11):
        seen, step = _counter()
        sim = Simulator(step, pacing=f"x{n}")
        assert sim.advance(100 * MS) == n
        assert set(seen) == {DT_S}


def test_a_late_pass_runs_more_steps_never_larger_ones_up_to_half_a_second():
    """A stalled machine catches up with more steps — five, not one of 0.5 s — and owes no more
    than V1's 0.5 s per pass."""
    seen, step = _counter()
    sim = Simulator(step)
    assert sim.advance(10_000 * MS) == MAX_PASS_NS // DT_NS == 5
    assert Simulator(_counter()[1], pacing="x10").advance(10_000 * MS) == 50
    assert set(seen) == {DT_S}


def test_the_remainder_carries_exactly():
    """Integer nanoseconds: three passes of a third of a step and two nanoseconds pay one step
    and carry the rest — no step is lost or made by rounding."""
    sim = Simulator(_counter()[1])
    third = DT_NS // 3 + 1
    assert [sim.advance(third) for _ in range(3)] == [0, 0, 1]
    assert sim.owed_ns == 3 * third - DT_NS
    sim.set_pacing("x10")
    assert sim.owed_ns == 3 * third - DT_NS


def test_an_unknown_pacing_and_a_backward_clock_are_refused():
    with pytest.raises(ValueError):
        Simulator(_counter()[1], pacing="TURBO")
    with pytest.raises(ValueError):
        Simulator(_counter()[1], pacing="FAST")              # V1's modes are retired (decision 321)
    with pytest.raises(ValueError):
        Simulator(_counter()[1]).advance(-1)


def test_a_faulted_step_freezes_the_pass_and_the_next_pass_tries_again():
    """A physics step that raises stops the pass and drops what it owed, as V1 does; the fault
    is held for the server, and cleared by the next good step."""
    calls = []

    def step(dt):
        calls.append(dt)
        if len(calls) == 3:
            raise FloatingPointError("the plant blew up")

    sim = Simulator(step, pacing="x10")
    assert sim.advance(100 * MS) == 2
    assert isinstance(sim.fault, FloatingPointError) and sim.owed_ns == 0
    assert sim.advance(100 * MS) == 10 and sim.fault is None


def _shut_overhead():
    """328C003 with PV-328203 shut on fixed boundaries: one plant, one step function."""
    col, loops = hy.Hydrolyser(), hy.HydrolyserLoops()
    loops.pic_328203.set_mode("MAN")
    loops.pic_328203.op = 0.0
    trace = []

    def step(dt):
        r = col.step(loops, t.C003_M746_DES_KGH, dict(t.W_S743), t.C002_T_BOT_C,
                     t.C002_P_TOP_BARA, t.C004_P_BARA, dt)
        trace.append((r.p_bara, r.t_c, r.m_kg, r.m_relief_kgh, r.relief_lifted,
                      tuple(r.w.items())))

    return step, trace


def test_an_exercise_replays_bit_for_bit_slow_or_fast_whatever_the_wall_clock():
    """The A-14 replay: x1 on irregular passes, and x10 on others, run the same steps — the
    same plant states to the bit, through SV32852's first lifts. Only the steps per real second
    differ."""
    slow_step, slow = _shut_overhead()
    sim = Simulator(slow_step)
    passes = [97, 103, 250, 31, 500, 66, 180]
    while sim.steps < 12_000:
        sim.advance(passes[sim.steps % len(passes)] * MS)
    fast_step, fast = _shut_overhead()
    sim = Simulator(fast_step, pacing="x10")
    passes = [16, 17, 9, 40]
    while sim.steps < 12_000:
        sim.advance(passes[sim.steps % len(passes)] * MS)
    n = min(len(slow), len(fast))
    assert n >= 12_000
    assert slow[:n] == fast[:n]
    assert any(state[4] for state in slow[:n])            # SV32852 lifted inside the run
