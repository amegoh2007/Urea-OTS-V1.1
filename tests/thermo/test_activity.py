"""The Extended UNIQUAC activity model — `ureasim.thermo.activity`.

Pinned: pure water is its own reference (ln gamma 0, no excess enthalpy); the closed-form
infinite-dilution terms are the limits of the general ones, so a molecular solute renormalised to
the unsymmetric reference has ln gamma 0 at infinite dilution and an ion keeps only its
Debye-Hueckel term; the short-range terms obey Gibbs-Duhem, as terms derived from one excess Gibbs
energy must; the ionic strength is the molal one; and the Debye-Hueckel A is 1.17 (kg/mol)^0.5 at
25 C, the natural-log value of Thomsen's correlation.
"""

from __future__ import annotations

import math

import pytest

from ureasim.thermo.activity import (activity_ln_gamma, debye_huckel_A, debye_huckel_ln_gamma,
                                     excess_enthalpy, ionic_strength,
                                     uniquac_combinatorial_ln_gamma,
                                     uniquac_combinatorial_ln_gamma_inf,
                                     uniquac_residual_ln_gamma, uniquac_residual_ln_gamma_inf)
from ureasim.thermo.parameters import M_W

EPS = 1e-9


def test_pure_water_is_its_own_reference():
    assert activity_ln_gamma({"H2O": 1.0}, 350.0) == {"H2O": 0.0}
    assert excess_enthalpy({"H2O": 1.0}, 350.0) == 0.0


@pytest.mark.parametrize("sp", ["NH3(aq)", "CO2(aq)", "NH4+", "HCO3-", "NH2COO-"])
@pytest.mark.parametrize("t_k", [300.0, 350.0, 420.0])
def test_the_closed_forms_are_the_dilute_limits(sp, t_k):
    x = {"H2O": 1.0 - EPS, sp: EPS}
    comb = uniquac_combinatorial_ln_gamma(x)[sp]
    res = uniquac_residual_ln_gamma(x, t_k)[sp]
    assert comb == pytest.approx(uniquac_combinatorial_ln_gamma_inf(sp), abs=1e-7)
    assert res == pytest.approx(uniquac_residual_ln_gamma_inf(sp, t_k), abs=1e-7)


@pytest.mark.parametrize("sp", ["NH3(aq)", "CO2(aq)"])
def test_a_dilute_molecular_solute_has_unit_activity_coefficient(sp):
    ln_g = activity_ln_gamma({"H2O": 1.0 - EPS, sp: EPS}, 350.0, solutes={sp})[sp]
    assert ln_g == pytest.approx(0.0, abs=1e-7)


def test_a_dilute_ion_keeps_only_its_debye_hueckel_term():
    x = {"H2O": 1.0 - 2.0 * EPS, "NH4+": EPS, "HCO3-": EPS}
    ln_g = activity_ln_gamma(x, 350.0)
    dh = debye_huckel_ln_gamma(x, 350.0)
    assert ln_g["NH4+"] == pytest.approx(dh["NH4+"], abs=1e-7)
    assert dh["NH4+"] < 0.0


@pytest.mark.parametrize("sp", ["NH3(aq)", "CO2(aq)"])
def test_the_short_range_terms_obey_gibbs_duhem(sp):
    """x_w d ln g_w + x_s d ln g_s = 0 along a binary, for each symmetric term."""
    t_k, x_s, h = 360.0, 0.15, 1e-6

    def terms(xs: float) -> tuple[dict, dict]:
        x = {"H2O": 1.0 - xs, sp: xs}
        return uniquac_combinatorial_ln_gamma(x), uniquac_residual_ln_gamma(x, t_k)

    (c_hi, r_hi), (c_lo, r_lo) = terms(x_s + h), terms(x_s - h)
    for hi, lo in ((c_hi, c_lo), (r_hi, r_lo)):
        slope = {k: (hi[k] - lo[k]) / (2.0 * h) for k in ("H2O", sp)}
        assert (1.0 - x_s) * slope["H2O"] + x_s * slope[sp] == pytest.approx(0.0, abs=1e-6)


def test_the_ionic_strength_is_molal():
    x = {"H2O": 0.9, "NH4+": 0.03, "HCO3-": 0.02, "CO3--": 0.005, "NH3(aq)": 0.045}
    molal = {k: v / (x["H2O"] * M_W) for k, v in x.items() if k != "H2O"}
    expected = 0.5 * (molal["NH4+"] + molal["HCO3-"] + 4.0 * molal["CO3--"])
    assert ionic_strength(x) == pytest.approx(expected, rel=1e-12)
    assert ionic_strength({"H2O": 0.95, "NH3(aq)": 0.05}) == 0.0


def test_the_debye_hueckel_a_at_25_c():
    assert debye_huckel_A(298.15) == pytest.approx(1.17, abs=0.005)
    assert debye_huckel_A(400.0) > debye_huckel_A(298.15)
    assert math.isfinite(excess_enthalpy({"H2O": 0.8, "NH3(aq)": 0.15, "CO2(aq)": 0.05}, 350.0))
