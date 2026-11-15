"""Behaviour of the packed-bed transport properties — `ureasim.thermo.transport_properties`.

Equivalence with V1 is proven in `tests/equivalence/test_packed_beds_equivalence.py`. This file
pins that each correlation lands on its textbook value where it is anchored and moves the way
the beds need it to.
"""

from __future__ import annotations

import pytest

from ureasim.thermo import transport_properties as tp


def test_water_at_20_c():
    """Vogel's water at 20 C, 1.002 mPa s; IAPWS R1-76's surface tension, 72.74 mN/m."""
    assert tp.water_mu_pas(293.15) == pytest.approx(1.0017e-3, abs=1e-7)
    assert tp.water_sigma_nm(293.15) == pytest.approx(0.07274, abs=1e-5)


def test_nitrogen_at_its_sutherland_reference():
    assert tp.gas_mu_pas(300.55) == pytest.approx(1.781e-5, rel=1e-15)


def test_a_hotter_wash_is_thinner_and_wets_less_easily():
    assert tp.water_mu_pas(330.0) < tp.water_mu_pas(316.15) < tp.water_mu_pas(300.0)
    assert tp.water_sigma_nm(330.0) < tp.water_sigma_nm(300.0)
    assert tp.water_sigma_nm(700.0) == pytest.approx(0.0, abs=1e-9)


def test_diffusivity_falls_with_pressure_and_rises_with_temperature():
    """NH3 through nitrogen at 43 C and 3.9 bar a, 6.51e-6 m2/s; inversely proportional to the
    pressure, as T^1.75; CO2, the heavier and bulkier, slower."""
    d = tp.diffusivity_m2s("NH3", 316.15, 3.9e5)
    assert d == pytest.approx(6.512e-6, abs=1e-9)
    assert tp.diffusivity_m2s("NH3", 316.15, 7.8e5) == pytest.approx(0.5 * d, rel=1e-12)
    assert tp.diffusivity_m2s("NH3", 2 * 316.15, 3.9e5) == pytest.approx(2 ** 1.75 * d, rel=1e-12)
    assert tp.diffusivity_m2s("CO2", 316.15, 3.9e5) < d
