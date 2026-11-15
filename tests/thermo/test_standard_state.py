"""The aqueous standard state — `ureasim.thermo.standard_state`.

Pinned: the chain reproduces the textbook aqueous constants it is validated on — pKw 14.00, the
ammonium protonation 9.25, carbonic acid's pKa1 6.37 and pKa2 10.33 at 25 C, and the heats its
docstring states (water ionisation +55.8, ammonium protonation -52.2, the carbonate step about
+14.7 kJ/mol); its two independent paths agree, the van 't Hoff slope of `lnK` equalling the
Cp-integrated `dH_reaction` at plant temperature; and at 25 C the enthalpy is the formation
enthalpy and the chemical potential the formation Gibbs energy, exactly.
"""

from __future__ import annotations

import math

import pytest

from ureasim.thermo.parameters import R, REACTIONS, STANDARD_STATE, T0
from ureasim.thermo.standard_state import (cp0, dH_reaction, h0, lnK, mu0_over_RT, pK,
                                           reaction_cp_available)


@pytest.mark.parametrize("reaction, textbook", [
    ("R1_water", 14.00), ("R2_ammonium", -9.25), ("R3_bicarb", 6.37), ("R4_carbonate", 10.33)])
def test_the_textbook_constants_at_25_c(reaction, textbook):
    assert pK(reaction) == pytest.approx(textbook, abs=0.01)
    assert pK(reaction) == pytest.approx(-lnK(reaction, T0) / math.log(10.0), rel=1e-15)


@pytest.mark.parametrize("reaction, textbook", [
    ("R1_water", 55.8), ("R2_ammonium", -52.2), ("R4_carbonate", 14.7)])
def test_the_textbook_heats_at_25_c(reaction, textbook):
    assert dH_reaction(reaction) == pytest.approx(textbook, abs=0.2)


@pytest.mark.parametrize("reaction", sorted(REACTIONS))
@pytest.mark.parametrize("t_k", [330.0, 380.0, 420.0])
def test_van_t_hoff_ties_the_two_paths_together(reaction, t_k):
    """d lnK / dT = dH / (R T^2): `lnK` integrates Gibbs-Helmholtz, `dH_reaction` integrates Cp."""
    h = 1e-3
    slope = (lnK(reaction, t_k + h) - lnK(reaction, t_k - h)) / (2.0 * h)
    assert slope * R * t_k * t_k / 1000.0 == pytest.approx(dH_reaction(reaction, t_k), rel=1e-6,
                                                          abs=1e-6)
    assert reaction_cp_available(reaction)


@pytest.mark.parametrize("species", sorted(STANDARD_STATE))
def test_at_25_c_the_formation_values_return_exactly(species):
    d_gf, d_hf, _cp = STANDARD_STATE[species]
    assert h0(species, T0) == pytest.approx(d_hf * 1000.0, abs=1e-9)
    assert mu0_over_RT(species, T0) == d_gf * 1000.0 / (R * T0)
    assert math.isfinite(cp0(species, 350.0))
