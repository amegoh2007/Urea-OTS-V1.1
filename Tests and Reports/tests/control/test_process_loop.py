"""`ureasim.control.process_loop.ProcessLoop` on a bad measurement and its recovery (handoff B-130).

What this pins
--------------
A bad PV freezes the loop's output and leaves its mode, as V1's ``_ctrl_ipd`` does. On the first good
sample after it V1 resumes on the PV history of before the outage, so its proportional term steps the
output by Kc times the PV's whole move through the outage. Decided 2026-11-11 (decision 186): the history
through a bad PV is unknown, and the first good sample reseeds it, so the loop acts on its integral alone
on that tick. ``ProcessLoop.reseed_after_bad = False`` is V1's side, which the equivalence harness keeps
(`tests/equivalence/test_process_loop_equivalence.py`). Without a bad PV the two are the same to the bit.
"""

from __future__ import annotations

import math

import pytest

from ureasim.control.process_loop import ProcessLoop

DT = 0.1


def _loop() -> ProcessLoop:
    """A reverse-acting pressure loop at its seed, PV on its set point."""
    return ProcessLoop(tag="PIC-TEST", Kc=2.0, Ti=60.0, Td=-1.0, act=1.0, op=50.0, sp=10.0,
                       pv=10.0, pv1=10.0, pv2=10.0, sp_lo=0.0, sp_hi=200.0)


def _outage(loop: ProcessLoop) -> list:
    """Five good ticks on the set point, fifty bad, then the PV back 2 bar above it."""
    ops = [loop.step(10.0, DT) for _ in range(5)]
    ops += [loop.step(math.nan, DT) for _ in range(50)]
    ops.append(loop.step(12.0, DT))
    return ops


def test_the_first_good_sample_reseeds_the_history_and_v1_kicks(monkeypatch):
    ours = _loop()
    ops = _outage(ours)
    assert ops[:55] == [50.0] * 55                      # frozen through the outage, both sides
    integral = 2.0 * (DT / 60.0) * (10.0 - 12.0)
    assert ops[-1] == pytest.approx(50.0 + integral, abs=1e-12)
    assert (ours.pv1, ours.pv2, ours.mode) == (12.0, 12.0, "AUTO")
    monkeypatch.setattr(ProcessLoop, "reseed_after_bad", False)
    v1 = _loop()
    ops = _outage(v1)
    assert ops[-1] == pytest.approx(50.0 + 2.0 * (-(12.0 - 10.0)) + integral, abs=1e-12)
    assert (v1.pv1, v1.pv2) == (12.0, 10.0)


def test_through_an_outage_the_history_is_unknown():
    loop = _loop()
    loop.step(10.0, DT)
    loop.step(math.nan, DT)
    assert math.isnan(loop.pv1) and math.isnan(loop.pv2) and loop.pv == 10.0


def test_without_a_bad_pv_the_two_sides_are_the_same_to_the_bit(monkeypatch):
    trace = [10.0 + 0.3 * math.sin(0.05 * k) for k in range(400)]
    ours = _loop()
    a = [ours.step(pv, DT) for pv in trace]
    monkeypatch.setattr(ProcessLoop, "reseed_after_bad", False)
    v1 = _loop()
    assert [v1.step(pv, DT) for pv in trace] == a


def test_a_clamp_holds_the_output_in_any_mode_and_the_loop_resumes_from_it():
    """AC4's CLAMP (decision 228, PC35's LIC-324501 at 100 %): the output stands on the clamp
    reference in AUTO and in MAN, the PV history stays current, and released the loop acts from the
    reference on that history: no proportional kick, one integral step."""
    loop = _loop()
    for mode in ("AUTO", "MAN"):
        loop.set_mode(mode)
        assert loop.step(12.0, DT, hold=100.0) == 100.0 == loop.op
    assert (loop.pv, loop.pv1, loop.pv2) == (12.0, 12.0, 12.0)
    loop.set_mode("AUTO")
    assert loop.step(12.0, DT) == pytest.approx(100.0 + 2.0 * DT / 60.0 * (10.0 - 12.0), abs=1e-12)
