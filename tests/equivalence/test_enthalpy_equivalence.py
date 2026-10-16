"""V1 <-> V1.1 equivalence for the H0 elemental-datum stream enthalpy.

Gate: exact agreement, plus the module's own first-principles oracles — the ones that do
not need plant data and therefore prove the datum rather than the calibration.
"""

from __future__ import annotations

import pytest

from ureasim.thermo import enthalpy as new
from tests.equivalence.v1_loader import load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

TEMPERATURES_K = [298.15, 318.15, 372.15, 403.15, 413.15, 456.15, 473.15]

PHASE_KEYS = [
    ("Urea", "liquid"), ("Urea", "solid"),
    ("Biuret", "liquid"), ("Biuret", "solid"),
    ("Carbamate", "liquid"), ("Carbamate", "solid"),
    ("H2O", "liquid"), ("H2O", "gas"),
    ("NH3", "aqueous"), ("NH3", "gas"),
    ("CO2", "aqueous"), ("CO2", "gas"),
    ("HCHO", "gas"), ("N2", "gas"), ("O2", "gas"),
    ("H2", "gas"), ("CH4", "gas"), ("Ar", "gas"),
]

#: Real PFD streams, so the comparison exercises the shapes the plant actually produces.
STREAMS = [
    # PFD 402 — the final urea melt leaving 324E003 at 140 C.
    (74721.0, {"Urea": 97.71, "Biuret": 0.85, "NH3": 0.04, "H2O": 1.39, "HCHO": 0.0099},
     140.0, "liquid"),
    # 323C003 bottoms liquor at 135 C.
    (120000.0, {"Urea": 68.74, "Biuret": 0.36, "NH3": 2.13, "CO2": 1.05, "H2O": 27.72},
     135.0, "liquid"),
    # PFD 204 — the HV-322604 inert purge, as a vapour.
    (900.0, {"N2": 55.0, "O2": 10.4, "CH4": 3.1, "H2": 0.2, "NH3": 25.0, "CO2": 6.3},
     114.0, "vapour"),
    # Same composition labelled 'gas' — must reach the vapour column, not the liquid one.
    (900.0, {"N2": 55.0, "O2": 10.4, "CH4": 3.1, "H2": 0.2, "NH3": 25.0, "CO2": 6.3},
     114.0, "gas"),
]


@pytest.fixture(scope="module")
def v1():
    return load("gap_g6_h0_enthalpy")


def test_tables_identical(v1):
    assert new.MOLAR_MASS == v1.MOLAR_MASS
    assert set(new.PURE_COMPONENT) == set(v1.PURE_COMPONENT)
    for key in new.PURE_COMPONENT:
        assert new.PURE_COMPONENT[key][0] == v1.PURE_COMPONENT[key][0], key


def test_basis_flag_values_identical(v1):
    assert new.EnthalpyBasis.H0.value == v1.EnthalpyBasis.H0.value
    assert new.EnthalpyBasis.H1.value == v1.EnthalpyBasis.H1.value
    assert new.EnthalpyBasis.H2.value == v1.EnthalpyBasis.H2.value


@pytest.mark.parametrize("T", TEMPERATURES_K)
@pytest.mark.parametrize("sp,phase", PHASE_KEYS)
def test_h_species_bit_exact(v1, sp, phase, T):
    assert new.h_species(sp, phase, T) == v1.h_species(sp, phase, T)


@pytest.mark.parametrize("mass,pct,t_c,phase", STREAMS)
def test_h0_stream_bit_exact(v1, mass, pct, t_c, phase):
    a = new.h0_stream_mass_pct(mass, pct, t_c, phase)
    b = v1.h0_stream_mass_pct(mass, pct, t_c, phase)
    assert a == b


def test_gas_and_vapour_labels_agree():
    """A 'gas' label must reach the vapour column.

    If it fell through to the liquid column, NH3 and CO2 would be priced as aqueous —
    a 35-44 kJ/mol shift with no error raised. See `_phase_map`.
    """
    comp = {"N2": 55.0, "NH3": 25.0, "CO2": 6.3}
    a = new.h0_stream_mass_pct(900.0, comp, 114.0, "gas")
    b = new.h0_stream_mass_pct(900.0, comp, 114.0, "vapour")
    c = new.h0_stream_mass_pct(900.0, comp, 114.0, "vapor")
    assert a == b == c
    d = new.h0_stream_mass_pct(900.0, comp, 114.0, "liquid")
    assert d["enthalpy_kJkg"] != a["enthalpy_kJkg"]


def test_unsupported_species_reported_not_raised():
    assert new.unsupported_species(["Urea", "NH3", "H2O"]) == set()
    assert "Xe" in new.unsupported_species(["Urea", "Xe"])


# --------------------------------------------------------------------------------------
# First-principles oracles — these prove the datum, not the calibration
# --------------------------------------------------------------------------------------

def test_datum_check_water_at_reference():
    """Liquid water at 25 C is exactly its formation enthalpy on this datum."""
    assert new.h_species("H2O", "liquid", new.T0) == pytest.approx(-285830.0, abs=1e-6)


def test_water_sensible_heat_25_to_130():
    """~75.7 J/(mol.K) over 105 K gives ~7950 J/mol."""
    dh = new.h_species("H2O", "liquid", 403.15) - new.h_species("H2O", "liquid", new.T0)
    assert 7600.0 < dh < 8300.0


def test_standard_vaporisation_enthalpy():
    """H2O(g) - H2O(l) at 25 C = 44.0 kJ/mol (literature standard vaporisation enthalpy)."""
    dvap = new.h_species("H2O", "gas", new.T0) - new.h_species("H2O", "liquid", new.T0)
    assert dvap == pytest.approx(44004.0, abs=50.0)


def test_urea_fusion_enthalpy():
    """Tischer's solid/liquid pair reproduces the measured fusion enthalpy, 13.9 kJ/mol."""
    dfus = new.h_species("Urea", "liquid", new.T0) - new.h_species("Urea", "solid", new.T0)
    assert dfus == pytest.approx(13899.0, abs=1.0)


def test_reaction_consistency_carbamate_step():
    """2 NH3(g) + CO2(g) -> carbamate(s) must land near the plant manual's -159 kJ/mol.

    This is what "reaction-consistent" means: the datum reproduces the licensor's own
    reaction enthalpy without being told it.
    """
    dh = (new.h_species("Carbamate", "solid", new.T0)
          - 2.0 * new.h_species("NH3", "gas", new.T0)
          - new.h_species("CO2", "gas", new.T0))
    assert -170000.0 < dh < -150000.0


def test_reaction_consistency_urea_step():
    """carbamate(l) -> urea(l) + H2O(l), endothermic; plant manual says +15.5 kJ/mol."""
    dh = (new.h_species("Urea", "liquid", new.T0)
          + new.h_species("H2O", "liquid", new.T0)
          - new.h_species("Carbamate", "liquid", new.T0))
    assert 12000.0 < dh < 20000.0


def test_real_melt_stream_is_finite_and_negative():
    """PFD 402 at 140 C: a finite, negative specific enthalpy on the elements datum."""
    s = new.h0_stream_mass_pct(
        74721.0,
        {"Urea": 97.71, "Biuret": 0.85, "NH3": 0.04, "H2O": 1.39, "HCHO": 0.0099},
        140.0, phase="liquid",
    )
    assert s["enthalpy_basis"] == "H0_formation_sensible_ideal"
    assert s["enthalpy_kJkg"] < 0.0
