"""The sizing records and the design-stroke anchor — `ureasim.data.valve_sizing` (split from
`control_valves`, 2026-10-23).

Pins the anchor's arithmetic on a valve built for the test, where the answer is known in closed
form, and the re-export through `control_valves`. The catalogued valves' strokes are pinned in
`test_control_valves.py`.
"""

from __future__ import annotations

import pytest

from ureasim.control.valve import cv_fraction
from ureasim.data import control_valves as cvd
from ureasim.data import valve_sizing as vs

#: A linear trim rated Kv 100, its normal case 40 m3/h at 800 kg/m3 needing Kv 50.
CASES = (vs.SizingCase(10.0, 6.0, 120.0, 20.0, 800.0, 25.0, None),
         vs.SizingCase(10.0, 6.0, 120.0, 40.0, 800.0, 50.0, 50.0, fl=0.9),
         vs.SizingCase(10.0, 6.0, 120.0, 60.0, 800.0, 75.0, None))
LINEAR = vs.VendorValve("XV-TEST", 100.0, "linear", "liquid", CASES, 1, "built for the test")


def test_the_normal_case():
    assert LINEAR.normal_case is CASES[1]
    assert (LINEAR.normal_case.fl, LINEAR.normal_case.xt) == (0.9, None)


def test_the_design_stroke_on_a_linear_trim():
    """phi = C_n (m / (Q_n rho_n)) / C_rated: the normal case's own mass flow, 32 t/h, needs the
    normal case's Kv 50 of 100, half stroke; half that flow, a quarter."""
    assert vs.design_stroke_pct(LINEAR, 40.0 * 800.0) == pytest.approx(50.0, abs=1e-12)
    assert vs.design_stroke_pct(LINEAR, 20.0 * 800.0) == pytest.approx(25.0, abs=1e-12)


def test_the_design_stroke_inverts_the_characteristic():
    """On an equal-percentage trim the stroke returned passes the required fraction exactly."""
    valve = vs.VendorValve("XV-TEST", 100.0, "equal_pct", "liquid", CASES, 1, "built for the test")
    h = vs.design_stroke_pct(valve, 40.0 * 800.0)
    assert cv_fraction(h / 100.0, "equal_pct") == pytest.approx(0.5, rel=1e-12)


def test_the_full_stroke_capacity():
    """Q_n C_rated / C_n: 40 m3/h at Kv 50 is 80 m3/h at the rated Kv 100."""
    assert vs.full_stroke_m3h(LINEAR) == pytest.approx(80.0, abs=1e-12)


def test_control_valves_re_exports_the_records():
    for name in vs.__all__:
        assert getattr(cvd, name) is getattr(vs, name)
