"""Fisher's control valves — `ureasim.data.control_valves_fisher` (decision 150, 2026-10-22).

Pins the four sheets as read from UD-MR-G00-DZ-0014-001 / -002 (items 021-025): the rated Cv and
named curve, each case's printed pressures, flow and capacity, and the densities the cases carry.
"""

from __future__ import annotations

import pytest

from ureasim.data import control_valves_fisher as fv
from ureasim.data.control_valves import NORMAL_MOLAR_VOLUME_M3_KMOL


@pytest.mark.parametrize("valve, rated, char, flows, caps, strokes", [
    (fv.LV_328503, 82.2, "equal_pct", (23.4, 38.9, 51.3), (23.466, 16.395, 22.017), (63, 54, 62)),
    (fv.LV_328504, 82.2, "equal_pct", (23.8, 39.6, 52.2), (10.164, 16.963, 22.450), (42, 55, 62)),
    (fv.HV_329602, 228.0, "linear", (5000.0, 20000.0, 32000.0), (25.130, 116.228, 204.932),
     (15, 48, 87)),
    (fv.PV_323202, 99.1, "linear", (600.0, 1200.2, 4000.0), (10.179, 38.489, 95.738),
     (8, 19, 90)),
])
def test_the_sheets_as_read(valve, rated, char, flows, caps, strokes):
    """Rated Cv, the named curve, three cases each with the normal case second."""
    assert (valve.rated, valve.characteristic, valve.normal) == (rated, char, 1)
    assert tuple(c.flow for c in valve.cases) == flows
    assert tuple(c.capacity for c in valve.cases) == caps
    assert tuple(c.stroke_pct for c in valve.cases) == strokes


def test_the_letdowns_cases():
    """LV-328503 at 138 C from 24.1 / 24.0 / 23.89 bar a less 1.24 / 7.02 / 6.77 bar; LV-328504 at
    147 C from 14.22 / 14.16 / 14.08 less 10.41 / 10.35 / 10.27; FL 0.819 on both; the specific
    gravities 0.933 and 0.925 on IEC 60534's 1000 kg/m3."""
    assert [(c.p1_bara, round(c.p1_bara - c.p2_bara, 2)) for c in fv.LV_328503.cases] == [
        (24.1, 1.24), (24.0, 7.02), (23.89, 6.77)]
    assert [(c.p1_bara, round(c.p1_bara - c.p2_bara, 2)) for c in fv.LV_328504.cases] == [
        (14.22, 10.41), (14.16, 10.35), (14.08, 10.27)]
    assert {c.fl for v in (fv.LV_328503, fv.LV_328504) for c in v.cases} == {0.819}
    assert (fv.LV_328503.normal_case.rho, fv.LV_328504.normal_case.rho) == (933.0, 925.0)


def test_the_gases_cases():
    """HV-329602's steam from 27 / 22 / 20 bar a to 3.0 / 4.4 / 7.0, xT 0.532, the mass flow on a
    unit density; the vent's carbonate gas from 5.0 / 3.2 / 3.2 to 1.1 / 1.3 / 1.3, SG 0.909 to air
    as 1.1747 kg/Nm3, so the normal case is 1410 kg/h against PFD 321's 1323."""
    assert [(c.p1_bara, c.p2_bara, c.xt) for c in fv.HV_329602.cases] == [
        (27.0, 3.0, 0.532), (22.0, 4.4, 0.532), (20.0, 7.0, 0.532)]
    assert {c.rho for c in fv.HV_329602.cases} == {1.0}
    assert [(c.p1_bara, c.p2_bara, c.xt) for c in fv.PV_323202.cases] == [
        (5.0, 1.1, 0.685), (3.2, 1.3, 0.470), (3.2, 1.3, 0.967)]
    rho_n = 0.909 * fv.MW_AIR / NORMAL_MOLAR_VOLUME_M3_KMOL
    assert fv.PV_323202.normal_case.rho == rho_n == pytest.approx(1.1747, abs=1e-4)
    c = fv.PV_323202.normal_case
    assert c.flow * c.rho == pytest.approx(1409.83, abs=0.01)


def test_the_catalogue():
    assert set(fv.FISHER_VALVES) == {"LV-328503", "LV-328504", "HV-329602", "PV-323202"}
    assert all("UD-MR-G00-DZ-0014" in v.source for v in fv.FISHER_VALVES.values())
