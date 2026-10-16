"""Behaviour of unit 329's drums — `ureasim.units.steam.drums` (decision 33's class)."""

from __future__ import annotations

import pytest

from ureasim.data import unit_329_network as n
from ureasim.units.steam.drums import D001, D005, D009


def test_the_vessels_hold_their_drawings_capacities():
    """329D005 13.59 m3 against its GA's 13.8, 329D009 7.91 against its name plate's 8, the two
    322D001s 61.06 m3 each against their GA's 62 — each a cylinder with 2:1 ellipsoidal heads."""
    assert (D005.full_m3, D009.full_m3, D001.full_m3 / 2.0) == (
        pytest.approx(13.592, abs=1e-3), pytest.approx(7.907, abs=1e-3),
        pytest.approx(61.06, abs=1e-2))
    assert D001.full_m3 / 2.0 == pytest.approx(n.V_D001_M3, rel=1e-7)


def test_the_design_level_is_at_the_axis_and_the_nll():
    """50 % is mid-span: the horizontal drums' axes (their GAs' NLL), 322D001's 1050 mm above its
    bottom tangent line."""
    for drum in (D005, D009):
        assert drum.mass_at_level_kg(50.0) == pytest.approx(
            drum.rho_kgm3 * drum.full_m3 / 2.0, rel=1e-12)
    assert sum(D001.taps_m) / 2.0 == pytest.approx(D001.id_m / 4.0 + n.D001_NLL_M, abs=1e-12)
    for drum in (D005, D009, D001):
        assert drum.level_pct(drum.mass_at_level_kg(50.0)) == pytest.approx(50.0, abs=1e-12)
        assert drum.level_pct(drum.mass_at_level_kg(37.3)) == pytest.approx(37.3, abs=1e-12)


def test_the_water_between_the_taps():
    """329D005 holds 10 829 kg between LT-329502's taps where V1's mid-chord takes 11 223;
    329D009 3775 where V1 takes 3090 (its heads, half its span); 322D001's taps lie in its
    cylinder, so its 26 083 kg are V1's (to V1's eight-figure pi)."""
    span = [d.mass_at_level_kg(100.0) - d.mass_at_level_kg(0.0) for d in (D005, D009, D001)]
    assert span == [pytest.approx(10829.3, abs=0.1), pytest.approx(3774.76, abs=0.01),
                    pytest.approx(n.MSPAN_504_KG, rel=1e-8)]
    assert (n.MSPAN_502_KG, n.MSPAN_503_KG) == (pytest.approx(11223.3, abs=0.1),
                                                 pytest.approx(3089.69, abs=0.01))


def test_the_reading_stops_at_the_taps_the_water_does_not():
    """Below the lower tap the transmitter reads 0 % with 363 kg still in 329D005; full, 100 %."""
    assert D005.mass_at_level_kg(0.0) == pytest.approx(363.44, abs=0.01)
    assert D005.level_pct(D005.mass_at_level_kg(0.0) / 2.0) == 0.0
    assert D005.level_pct(D005.full_kg) == 100.0
    assert D005.height_at_m(0.0) == 0.0 and D005.height_at_m(1.0e9) == D005.id_m
