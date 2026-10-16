"""V1 <-> V1.1 equivalence for the neutral H2O/urea UNIQUAC and the SRK letdown.

Gate: exact agreement. Both ports changed layout and documentation only.

States swept are the plant's own:

    324E001   0.330 bar a, 130 C, ~95 wt% urea
    324E003   0.131 bar a, 140 C, ~99.7 wt% urea
    HV-322604 140.7 -> 4.0 bar a on PFD stream 204
"""

from __future__ import annotations

import pytest

from ureasim.thermo import extended_uniquac as new_uq
from ureasim.thermo import real_gas as new_rg
from tests.equivalence.v1_loader import load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

#: (T [K], P [bar a]) inside the guarded Unit-324 envelope.
EVAP_STATES = [
    (403.15, 0.330),      # 324E001 design
    (413.15, 0.131),      # 324E003 design
    (393.15, 0.20),
    (433.15, 0.50),
    (455.15, 0.95),
    (375.15, 0.03),
]

UREA_FRACTIONS = [0.0, 0.10, 0.50, 0.6874, 0.80, 0.95, 0.9771, 0.999, 1.0]

TEMPERATURES_K = [372.15, 393.15, 403.15, 413.15, 433.15, 473.15]


@pytest.fixture(scope="module")
def v1_uq():
    return load("thermo_extended_uniquac")


@pytest.fixture(scope="module")
def v1_rg():
    return load("real_gas")


# --------------------------------------------------------------------------------------
# Neutral H2O/urea UNIQUAC
# --------------------------------------------------------------------------------------

def test_constants_and_envelopes_match(v1_uq):
    assert new_uq.MODEL_NAME == v1_uq.MODEL_NAME
    assert new_uq.VALID_TEMPERATURE_K == v1_uq.VALID_TEMPERATURE_K
    assert new_uq.VALID_PRESSURE_BARA == v1_uq.VALID_PRESSURE_BARA
    assert new_uq.SOURCE_VALID_TEMPERATURE_K == v1_uq.SOURCE_VALID_TEMPERATURE_K
    assert new_uq.SOURCE_VALID_PRESSURE_BARA == v1_uq.SOURCE_VALID_PRESSURE_BARA


@pytest.mark.parametrize("w", UREA_FRACTIONS)
def test_mole_fractions_bit_exact(v1_uq, w):
    assert (new_uq.mole_fractions_from_urea_mass_fraction(w)
            == v1_uq.mole_fractions_from_urea_mass_fraction(w))


@pytest.mark.parametrize("T", TEMPERATURES_K)
@pytest.mark.parametrize("w", UREA_FRACTIONS)
def test_ln_gamma_and_activity_bit_exact(v1_uq, w, T):
    xw, xu = new_uq.mole_fractions_from_urea_mass_fraction(w)
    assert new_uq.ln_gamma(xw, xu, T) == v1_uq.ln_gamma(xw, xu, T)
    assert new_uq.water_activity(w, T) == v1_uq.water_activity(w, T)


@pytest.mark.parametrize("T", TEMPERATURES_K)
def test_water_psat_bit_exact(v1_uq, T):
    assert new_uq.water_psat_bara(T) == v1_uq.water_psat_bara(T)


@pytest.mark.parametrize("T,P", EVAP_STATES)
def test_px_residual_and_solve_bit_exact(v1_uq, T, P):
    for w in (0.5, 0.9, 0.99):
        assert (new_uq.px_equilibrium_residual(w, T, P)
                == v1_uq.px_equilibrium_residual(w, T, P))
    assert new_uq.solve_urea_mass_fraction(T, P) == v1_uq.solve_urea_mass_fraction(T, P)


@pytest.mark.parametrize("T,P", EVAP_STATES)
def test_fast_path_bit_exact(v1_uq, T, P):
    assert (new_uq.solve_urea_mass_fraction_fast(T, P)
            == v1_uq.solve_urea_mass_fraction_fast(T, P))


@pytest.mark.parametrize("T,P", EVAP_STATES)
def test_validity_status_matches(v1_uq, T, P):
    assert new_uq.validity_status(T, P) == v1_uq.validity_status(T, P)


def test_unit_324_is_declared_an_extrapolation():
    """Not a claim of validation. Both evaporator design points sit outside the
    publication's pressure range, and the model says so rather than hiding it."""
    assert new_uq.validity_status(403.15, 0.330) == "DESIGN_ANCHORED_EXTRAPOLATION"
    assert new_uq.validity_status(413.15, 0.131) == "DESIGN_ANCHORED_EXTRAPOLATION"


@pytest.mark.parametrize("T,P", [
    (300.0, 0.3),        # below the temperature floor
    (500.0, 0.3),        # above the temperature ceiling
    (403.15, 5.0),       # above the pressure ceiling
    (403.15, 0.001),     # below the pressure floor
])
def test_out_of_envelope_refuses_in_both(v1_uq, T, P):
    """Refusal is a feature, and it must survive the port identically."""
    with pytest.raises(new_uq.UnsupportedThermodynamicDomain):
        new_uq.solve_urea_mass_fraction(T, P)
    with pytest.raises(v1_uq.UnsupportedThermodynamicDomain):
        v1_uq.solve_urea_mass_fraction(T, P)


@pytest.mark.parametrize("T", [300.0, 500.0])
def test_activity_refuses_outside_the_temperature_envelope(v1_uq, T):
    with pytest.raises(new_uq.UnsupportedThermodynamicDomain):
        new_uq.water_activity(0.9, T)
    with pytest.raises(v1_uq.UnsupportedThermodynamicDomain):
        v1_uq.water_activity(0.9, T)


def test_fast_path_tracks_the_exact_solve():
    """The grid is an optimisation, not a different model.

    It must agree with the exact solve to far better than the model's own uncertainty,
    otherwise the evaporator's answer depends on which entry point was called.
    """
    for T, P in EVAP_STATES:
        exact = new_uq.solve_urea_mass_fraction(T, P)
        fast = new_uq.solve_urea_mass_fraction_fast(T, P)
        assert abs(fast - exact) < 1.0e-6, (T, P, exact, fast)


def test_pure_component_limits():
    """Pure water has unit activity; pure urea has none. No clipping needed."""
    assert new_uq.water_activity(0.0, 403.15) == 1.0
    assert new_uq.water_activity(1.0, 403.15) == 0.0


def test_melt_holds_water_more_tightly_than_an_ideal_solution():
    """The whole reason a non-ideal model is needed at 97.7 wt%.

    An ideal melt would give up its last water far too readily, so the evaporators would
    appear to reach product concentration at a vacuum they cannot hold.
    """
    w = 0.9771
    xw, _ = new_uq.mole_fractions_from_urea_mass_fraction(w)
    assert new_uq.water_activity(w, 413.15) < xw


# --------------------------------------------------------------------------------------
# SRK isenthalpic letdown
# --------------------------------------------------------------------------------------

#: PFD stream 204 — the HV-322604 inert purge, in kmol/h.
STREAM_204 = {"N2": 68.8, "O2": 11.4, "CH4": 5.9, "H2": 3.1,
              "NH3": 8.3, "CO2": 2.2, "H2O": 0.3}

#: An NH3/CO2-rich HP gas, for contrast.
HP_GAS = {"NH3": 70.0, "CO2": 22.0, "H2O": 8.0}


def test_species_set_matches(v1_rg):
    assert set(new_rg.SPECIES) == set(v1_rg.SPECIES)


@pytest.mark.parametrize("comp", [STREAM_204, HP_GAS])
def test_mole_fractions_bit_exact_rg(v1_rg, comp):
    assert new_rg.mole_fractions(comp) == v1_rg.mole_fractions(comp)


@pytest.mark.parametrize("comp", [STREAM_204, HP_GAS])
@pytest.mark.parametrize("t_c,p_bara", [(114.0, 140.7), (183.0, 144.2), (94.8, 4.0)])
def test_z_factor_and_residual_bit_exact(v1_rg, comp, t_c, p_bara):
    assert new_rg.z_factor(comp, t_c, p_bara) == v1_rg.z_factor(comp, t_c, p_bara)
    y = new_rg.mole_fractions(comp)
    t_k = t_c + 273.15
    p_pa = p_bara * 1.0e5
    assert new_rg.h_residual(y, t_k, p_pa) == v1_rg.h_residual(y, t_k, p_pa)
    assert new_rg.h_molar(y, t_k, p_pa) == v1_rg.h_molar(y, t_k, p_pa)


@pytest.mark.parametrize("comp", [STREAM_204, HP_GAS])
@pytest.mark.parametrize("p_out", [4.0, 1.5, 20.0])
def test_isenthalpic_letdown_bit_exact(v1_rg, comp, p_out):
    assert (new_rg.isenthalpic_letdown(comp, 114.0, 140.7, p_out)
            == v1_rg.isenthalpic_letdown(comp, 114.0, 140.7, p_out))


def test_empty_or_reverse_letdown_is_a_no_op(v1_rg):
    """A shut valve, or a collapsed loop pressure, must not invent a temperature change."""
    assert new_rg.isenthalpic_letdown({}, 114.0, 140.7, 4.0)["t_out_c"] == 114.0
    assert new_rg.isenthalpic_letdown(STREAM_204, 114.0, 4.0, 140.7)["t_out_c"] == 114.0
    assert new_rg.z_factor({}, 114.0, 140.7) == 1.0


def test_nitrogen_rich_purge_cools_far_less_than_the_constant_it_replaced():
    """The measurement that condemned the 0.55 K/bar constant.

    PFD 204 is 68.8 mol% N2. The real coefficient is about a quarter of the constant, which
    is what a mostly-nitrogen gas does, and the outlet lands near 95 C rather than 39 C.
    """
    result = new_rg.isenthalpic_letdown(STREAM_204, 114.0, 140.7, 4.0)
    assert 85.0 < result["t_out_c"] < 105.0
    assert 0.08 < result["mu_jt_k_bar"] < 0.25
    assert result["t_out_c"] > 114.0 - 0.55 * (140.7 - 4.0) + 40.0


def test_ammonia_rich_gas_cools_much_more_than_the_purge():
    """The composition dependence a constant coefficient could not represent at all."""
    purge = new_rg.isenthalpic_letdown(STREAM_204, 114.0, 140.7, 4.0)
    rich = new_rg.isenthalpic_letdown(HP_GAS, 114.0, 140.7, 4.0)
    assert rich["mu_jt_k_bar"] > purge["mu_jt_k_bar"] * 1.5


def test_hp_loop_compressibility_is_well_below_ideal():
    """At 140 bar a an ideal-gas density would be badly wrong, which is why LV-322501's
    blow-through takes Z from here."""
    assert new_rg.z_factor(HP_GAS, 183.0, 144.2) < 0.85
