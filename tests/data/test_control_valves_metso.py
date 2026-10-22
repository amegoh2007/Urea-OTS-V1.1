"""Metso's control valves — `ureasim.data.control_valves_metso` (split from `control_valves`,
2026-10-23).

Pins the catalogue's make-up as moved: fourteen Neldiscs on Metso's NELPROF sheets, each on its
printed points (decision 108), the densities the sheets do not print (decision 116), and the
re-export through `control_valves`. The sheets' values themselves are pinned in
`test_control_valves.py`.
"""

from __future__ import annotations

import pytest

from ureasim.data import control_valves as cvd
from ureasim.data import control_valves_metso as mv
from ureasim.data.valve_sizing import NORMAL_MOLAR_VOLUME_M3_KMOL
from ureasim.thermo.iapws import rho_liquid_sat_kgm3


def test_the_catalogue():
    """Fourteen valves: eight steam butterflies, four on water, two on gas; three cases each with
    the normal case second, but HV-323605's and PV-323203's two, the first their normal case."""
    assert set(mv.METSO_VALVES) == {
        "PV-329203", "PV-329212", "FV-329401", "PV-329202", "PV-329204", "PV-329207A",
        "PV-329207B", "PV-329208", "FV-329409", "HV-323605", "PV-323203", "PV-323202A",
        "PV-323202B", "TV-328002"}
    services = {t: v.service for t, v in mv.METSO_VALVES.items()}
    assert sorted(t for t, s in services.items() if s == "liquid") == [
        "FV-329409", "PV-323202A", "PV-323202B", "TV-328002"]
    for tag, valve in mv.METSO_VALVES.items():
        two = tag in ("HV-323605", "PV-323203")
        assert (len(valve.cases), valve.normal) == ((2, 0) if two else (3, 1)), tag
        assert "UD-MR-G00-DZ-0031-009" in valve.source, tag


@pytest.mark.parametrize("valve", list(mv.METSO_VALVES.values()), ids=lambda v: v.tag)
def test_each_trim_is_its_printed_points(valve):
    """Shut to the rated capacity wide open, through every printed (travel, capacity), never
    falling (decision 108)."""
    points = valve.characteristic
    assert points[0] == (0.0, 0.0) and points[-1] == (1.0, 1.0)
    assert list(points[1:-1]) == [(c.stroke_pct / 100.0, c.capacity / valve.rated)
                                  for c in valve.cases]
    assert all(b[0] >= a[0] and b[1] >= a[1] for a, b in zip(points, points[1:]))


def test_the_densities_the_sheets_do_not_print():
    """Water at IAPWS-IF97's saturated liquid at each sheet's temperature (decision 116): 961.89,
    980.53 and 992.93 kg/m3 at 95, 65 and 38 C; HV-323605's vapour at its SG 0.641 on air's
    normal density, 0.8283 kg/Nm3; PV-323203's inlet 0.69 kg/m3 taken to normal conditions,
    0.7403 kg/Nm3; steam a unit density."""
    assert mv.FV_329409.normal_case.rho == rho_liquid_sat_kgm3(95.0) == pytest.approx(961.8873,
                                                                                    abs=1e-4)
    assert mv.PV_323202A.normal_case.rho == mv.PV_323202B.normal_case.rho == rho_liquid_sat_kgm3(
        65.0)
    assert mv.TV_328002.normal_case.rho == pytest.approx(992.9316, abs=1e-4)
    assert mv.HV_323605.normal_case.rho == 0.641 * 28.9647 / NORMAL_MOLAR_VOLUME_M3_KMOL
    assert mv.HV_323605.normal_case.rho == pytest.approx(0.8283, abs=1e-4)
    assert mv.PV_323203.normal_case.rho == pytest.approx(0.7403, abs=1e-4)
    steam = [v for v in mv.METSO_VALVES.values() if v.service == "gas"
             and v.tag not in ("HV-323605", "PV-323203")]
    assert len(steam) == 8 and {c.rho for v in steam for c in v.cases} == {1.0}


def test_control_valves_re_exports_every_valve():
    """Every caller that imports a Metso valve from `control_valves` gets the same object, and
    ``VENDOR_VALVES`` still holds all fourteen."""
    for tag, valve in mv.METSO_VALVES.items():
        assert getattr(cvd, tag.replace("-", "_")) is valve
        assert cvd.VENDOR_VALVES[tag] is valve
