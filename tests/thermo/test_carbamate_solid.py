"""Solid ammonium carbamate's saturation — `ureasim.thermo.carbamate_solid` (split from
`condensing_letdown`, 2026-10-23).

Pins the equilibrium constant on Egan, Potts and Potts's two quoted points, the deposit that brings
a supersaturated gas back onto it, and the re-export through `condensing_letdown`. The letdown's
deposit on its enthalpy balance is pinned in `test_condensing_letdown.py`.
"""

from __future__ import annotations

import math

import pytest

from ureasim.thermo import carbamate_solid as cs
from ureasim.thermo import condensing_letdown as cl

#: A dry gas at 1 bar a, half ammonia, a third carbon dioxide [mole fractions].
GAS = {"NH3": 0.5, "CO2": 0.3, "N2": 0.2}


def test_the_dissociation_pressure():
    """1 atm at 58.7 C and 89 Torr at 25 C (Egan, Potts and Potts, 1946); Kp = (4/27) P^3."""
    p = lambda t: (cs.carbamate_kp_bar3(t) * 27.0 / 4.0) ** (1.0 / 3.0)
    assert p(58.7) == pytest.approx(1.01325, abs=0.004)
    assert p(25.0) * 750.06 == pytest.approx(89.0, abs=0.5)
    assert cs.carbamate_kp_bar3(25.0) == pytest.approx(2.45846e-4, rel=1e-5)


def test_a_gas_below_saturation_lays_nothing_down():
    """At 100 C this gas stands below Kp: no deposit."""
    assert cs._supersaturation(GAS, 0.0, 100.0, 1.0) < 0.0
    assert cs._deposit_at(GAS, 100.0, 1.0) == 0.0


def test_a_supersaturated_gas_deposits_onto_its_saturation():
    """At 25 C the gas lays down 0.2455 mol of solid per mol, and what is left stands on Kp: two
    NH3 and one CO2 per mole of solid, the gas shrinking by three."""
    s = cs._deposit_at(GAS, 25.0, 1.0)
    assert s == pytest.approx(0.245456, abs=1e-6)
    left = cs._less_deposit(GAS, s)
    assert left["NH3"] == pytest.approx((0.5 - 2.0 * s) / (1.0 - 3.0 * s), rel=1e-12)
    assert left["CO2"] == pytest.approx((0.3 - s) / (1.0 - 3.0 * s), rel=1e-12)
    assert math.log(left["NH3"] ** 2 * left["CO2"]) == pytest.approx(
        math.log(cs.carbamate_kp_bar3(25.0)), abs=1e-9)


def test_condensing_letdown_re_exports_every_name():
    for name in cs.__all__ + ["_deposit_at", "_less_deposit", "_supersaturation"]:
        assert getattr(cl, name) is getattr(cs, name), name
    assert set(cs.__all__) <= set(cl.__all__)
