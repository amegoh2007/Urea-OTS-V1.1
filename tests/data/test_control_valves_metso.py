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


#: The five balanced Neldiscs (the sheets' valve series S-L-ANSI150 / S-L-ANSI300), on Valmet's S-Disc
#: table between their printed points since decision 170 (2026-11-06); the other nine keep the chord.
BALANCED = {"PV-329204": 300, "PV-329207A": 150, "PV-329207B": 150, "PV-329208": 150,
            "PV-329212": 150}


@pytest.mark.parametrize("valve", [v for t, v in mv.METSO_VALVES.items() if t not in BALANCED],
                         ids=lambda v: v.tag)
def test_each_conventional_trim_is_its_printed_points(valve):
    """Shut to the rated capacity wide open, through every printed (travel, capacity), linear
    between, never falling (decision 108): the nine conventional Neldiscs, for which no table is
    published, are unchanged."""
    points = valve.characteristic
    assert points == mv._neldisc(valve.rated, valve.cases)
    assert points[0] == (0.0, 0.0) and points[-1] == (1.0, 1.0)
    assert list(points[1:-1]) == [(c.stroke_pct / 100.0, c.capacity / valve.rated)
                                  for c in valve.cases]
    assert all(b[0] >= a[0] and b[1] >= a[1] for a, b in zip(points, points[1:]))


@pytest.mark.parametrize("tag", sorted(BALANCED))
def test_a_balanced_trim_keeps_every_printed_point(tag):
    """Decision 170: shut to wide open, through every printed (travel, capacity) to the bit, with
    the table's 10 % nodes added between them, and strictly rising in travel and capacity (the
    inverse divides by both steps)."""
    valve = mv.METSO_VALVES[tag]
    points = valve.characteristic
    assert points[0] == (0.0, 0.0) and points[-1] == (1.0, 1.0)
    printed = [(c.stroke_pct / 100.0, c.capacity / valve.rated) for c in valve.cases]
    assert all(p in points for p in printed)
    assert all(b[0] > a[0] and b[1] > a[1] for a, b in zip(points, points[1:]))
    assert len(points) > len(valve.cases) + 2


def _table_two(ansi_class, h):
    """Valmet 2SL120EN Table 2's Cv / Cv_max at fractional opening ``h``, linear between nodes."""
    knots = [(0.0, 0.0)] + [((i + 1) / 10.0, f)
                            for i, f in enumerate(mv.S_DISC_RELATIVE_CV[ansi_class])]
    for (h0, f0), (h1, f1) in zip(knots, knots[1:]):
        if h <= h1:
            return f0 + (f1 - f0) * (h - h0) / (h1 - h0)
    return 1.0


def test_table_two_is_what_the_sheets_print():
    """The evidence for decision 170: at the three printed travels of each balanced valve, Valmet's
    Table 2 (the sheet's ANSI class) is within 1.3 % of the sheet's capacity, on the catalogue Cv for
    the two valves installed in a larger line (PV-329204 Cv 1640, PV-329207B Cv 2580; their rated
    FpCv is 2.2 and 5.4 % lower, and the trim is anchored on the printed points, so the rated FpCv
    stays the full-open capacity)."""
    catalogue_cv = {"PV-329204": 1640.0, "PV-329207B": 2580.0}
    worst = 0.0
    for tag, ansi_class in BALANCED.items():
        valve = mv.METSO_VALVES[tag]
        cv = catalogue_cv.get(tag, valve.rated)
        for c in valve.cases:
            deviation = (c.capacity / cv) / _table_two(ansi_class, c.stroke_pct / 100.0) - 1.0
            worst = max(worst, abs(deviation))
    assert worst < 0.014


#: Both sides of decision 170 (2026-11-06), at travels 0.2, 0.3, 0.5, 0.7, 0.9: the capacity fraction
#: of the chord that decision 108 built (the old trim, rebuilt through `_neldisc`) and of the
#: S-Disc trim that replaced it, and the design stroke each puts on the PFD's flow (None where the
#: valve is anchored on its full-stroke capacity, PV-329207A).
TRAVELS = (0.2, 0.3, 0.5, 0.7, 0.9)
BOTH_SIDES = {
    "PV-329204": ((0.144028, 0.227477, 0.419168, 0.670112, 0.895393),
                  (0.128858, 0.206272, 0.411769, 0.673612, 0.901761), (57989.0, 44.1, 44.1)),
    "PV-329207A": ((0.088787, 0.144628, 0.327966, 0.545925, 0.848642),
                   (0.085840, 0.139728, 0.294664, 0.537656, 0.871905), None),
    "PV-329207B": ((0.116591, 0.190491, 0.338291, 0.562650, 0.854217),
                   (0.090710, 0.147082, 0.308888, 0.553655, 0.876337), (16707.0, 54.9630, 55.9717)),
    "PV-329208": ((0.089369, 0.146654, 0.313028, 0.556841, 0.852280),
                  (0.086408, 0.140211, 0.294931, 0.537834, 0.871954), (11230.0, 27.2232, 27.2640)),
    "PV-329212": ((0.098403, 0.147605, 0.306693, 0.541252, 0.846644),
                  (0.086640, 0.141041, 0.296915, 0.540103, 0.872591), (4158.0, 54.6805, 54.6843)),
}


@pytest.mark.parametrize("tag", sorted(BOTH_SIDES))
def test_decision_170_both_sides(tag):
    """The chord is the old trim, to the bit, and it passes the same printed points; the S-Disc
    trim moves the capacity between them by up to 0.046 of rated (PV-329207B at 40 %: the chord
    is 0.264 where the table gives 0.218) and the design stroke of PV-329207B by +1.0 stroke-%;
    flows at every printed point and at the design are unchanged."""
    import dataclasses

    from ureasim.control.valve import cv_fraction
    valve = mv.METSO_VALVES[tag]
    chord_fractions, new_fractions, design = BOTH_SIDES[tag]
    chord = dataclasses.replace(valve, characteristic=mv._neldisc(valve.rated, valve.cases))
    assert [cv_fraction(h, chord.characteristic) for h in TRAVELS] == pytest.approx(
        chord_fractions, abs=1e-6)
    assert [cv_fraction(h, valve.characteristic) for h in TRAVELS] == pytest.approx(
        new_fractions, abs=1e-6)
    for c in valve.cases:
        h = c.stroke_pct / 100.0
        assert cv_fraction(h, valve.characteristic) == pytest.approx(
            cv_fraction(h, chord.characteristic), abs=1e-12)
    if design is not None:
        from ureasim.data.valve_sizing import design_stroke_pct
        flow, old, new = design
        assert design_stroke_pct(chord, flow) == pytest.approx(old, abs=1e-4)
        assert design_stroke_pct(valve, flow) == pytest.approx(new, abs=1e-4)


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
