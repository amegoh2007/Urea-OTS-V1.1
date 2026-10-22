"""`units/evaporation/stage_fixed_point.py` — the bracketed temperature where the sweeps never
settle (handoff B-108)."""

from __future__ import annotations

import pytest

from ureasim.units.evaporation.stage_fixed_point import bisected_fixed_point


def _ringing_sweep(t_c, p_bara):
    """A stage whose sweep overshoots its balance: T' = 150 - 3 (T - 150), so Picard from any
    other T doubles its error each sweep; its vacuum relaxes halfway to 0.3 bar a a sweep, and it
    boils 10 kg/h per kelvin above 140 C."""
    return 0.5 * (p_bara + 0.3), 150.0 - 3.0 * (t_c - 150.0), 10.0 * max(t_c - 140.0, 0.0)


def test_the_temperature_is_solved_on_the_balance():
    """The root of T' - T, the vacuum settled at the root, the residual inside the tolerance."""
    root = bisected_fixed_point(_ringing_sweep, 130.0, 170.0, 0.2, 1e-12, 60)
    assert root.t_c == pytest.approx(150.0, abs=1e-10)
    assert root.p_bara == pytest.approx(0.3, abs=1e-12)
    assert root.m_boil_kgh == pytest.approx(100.0, abs=1e-8)
    assert root.residual <= 1e-10


def test_a_bracket_with_no_sign_change_leaves_the_caller_its_sweep():
    """Both ends on the hot side of the balance: ``None``, so the stage keeps V1's last sweep."""
    assert bisected_fixed_point(_ringing_sweep, 155.0, 170.0, 0.2, 1e-12, 60) is None
