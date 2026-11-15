"""The synthesis loop's displayed indicators — `ureasim.units.synthesis.indicators`.

V1's ten lags are proven ``==`` in `tests/equivalence/test_indicators_equivalence.py`. This file
pins what an operator sees: no boot transient on the design, each indication ramping on its own
time constant after a step, PI-322E002 capped at what the feeds deliver, and AT-322701 reading the
reactor overflow's N/C on an atom basis; and TT-322012 ramping across 322F001's no-flow branch
(handoff B-11, closed 2026-10-07).
"""

from __future__ import annotations

import math

import pytest

from ureasim.data import indicator_lags as lags
from ureasim.data.unit_322r001 import OVERFLOW_DES_KMOLH
from ureasim.units.synthesis.indicators import SynthesisIndicators

DT = 0.1

#: The design inputs, in `SynthesisIndicators.step`'s order.
DESIGN = dict(t_ejector_c=107.6, t_top_c=187.0, tt_323001_c=119.0, t_prod_c=170.0,
              p_bub_bara=144.2, t_overflow_c=165.0, t_offgas_c=114.0, t_purge_c=94.8,
              t_ccw_out_c=95.0, overflow_kmolh=dict(OVERFLOW_DES_KMOLH))


def _run(ind, ticks, **over):
    args = {**DESIGN, **over}
    r = None
    for _ in range(ticks):
        r = ind.step(**args, dt=DT)
    return r


def test_the_design_shows_no_boot_transient():
    """Every lag starts on its process value: the first tick and the thousandth read the same."""
    ind = SynthesisIndicators()
    first = _run(ind, 1)
    assert first == _run(ind, 1000)
    assert first.tt_322010_c == 170.0 and first.pi_322e002_bara == 144.2


@pytest.mark.parametrize("field,arg,tau", [
    ("tt_322012_c", "t_ejector_c", lags.EJ_T_TAU_S),
    ("tt_322010_c", "t_prod_c", lags.HPCC_T_TAU_S),
    ("tt_329125_c", "t_ccw_out_c", lags.CCW_T_TAU_S),
])
def test_a_step_ramps_the_indication_on_its_own_time_constant(field, arg, tau):
    """A 10 K step: after one time constant the indication has covered 1 - 1/e of it, to the
    implicit Euler's discretisation (under 0.1 %)."""
    ind = SynthesisIndicators()
    _run(ind, 1)
    r = _run(ind, round(tau / DT), **{arg: DESIGN[arg] + 10.0})
    covered = (getattr(r, field) - DESIGN[arg]) / 10.0
    assert covered == pytest.approx(1.0 - math.exp(-1.0), abs=1e-3)


def test_pi_322e002_is_capped_at_the_feed_head():
    """A bubble point above 144.2 bar a reads 144.2: 322E002 cannot be pressurised past what its
    feeds deliver."""
    ind = SynthesisIndicators()
    _run(ind, 1)
    r = _run(ind, 3000, p_bub_bara=221.0)
    assert r.pi_322e002_bara == lags.HPCC_P_DISPLAY_MAX_BARA == 144.2


def test_at_322701_reads_the_overflows_atom_ratio():
    """At the design overflow AT-322701 reads 3.0 (V1's 2.99975); a carbon-free overflow pegs
    the analyser at 0, not at infinity."""
    ind = SynthesisIndicators()
    assert _run(ind, 1).at_322701 == pytest.approx(2.99975, abs=5e-4)
    ind = SynthesisIndicators()
    assert _run(ind, 1, overflow_kmolh={"NH3": 10.0}).at_322701 == 0.0


def test_tt_322012_ramps_across_the_ejectors_no_flow_branch():
    """Handoff B-11. At a microgram an hour of motive 322F001 leaves its flowing branch (39.18 C,
    the motive ammonia alone) for its no-flow branch (178.8 C, the stagnant carbamate): a 140 C
    step in the ejector's temperature. TT-322012 reads it through V1's 120 s thermal lag, so the
    screen ramps — 0.12 C on the first tick, 63 % of the step in two minutes — as the thermowell
    comes to equilibrium with what is around it."""
    from ureasim.units.synthesis.ejector import ejector_322f001
    flowing = ejector_322f001(1.1e-6, 28.93, 50.0).t_c
    stagnant = ejector_322f001(1.0e-6, 28.93, 50.0).t_c
    assert (flowing, stagnant) == pytest.approx((39.18, 178.80), abs=0.01)
    ind = SynthesisIndicators()
    _run(ind, 1, t_ejector_c=flowing)
    first = _run(ind, 1, t_ejector_c=stagnant).tt_322012_c
    assert first - flowing == pytest.approx((stagnant - flowing) * DT / (lags.EJ_T_TAU_S + DT),
                                            rel=1e-12)
    later = _run(ind, round(lags.EJ_T_TAU_S / DT) - 1, t_ejector_c=stagnant).tt_322012_c
    assert (later - flowing) / (stagnant - flowing) == pytest.approx(1.0 - math.exp(-1.0),
                                                                    abs=1e-3)
