"""V1 <-> V1.1 equivalence for the anchored bulk-property layer.

These correlations run on every tick at every node, so they are the ones most likely to be
"tidied" by a future edit. The gate is exact agreement with V1, plus the three properties
that make the anchoring work at all:

  * a departure form returns its anchor **bit-exactly** at the design state;
  * the multiplicative form's parentheses are load-bearing;
  * the back-solved molten-urea c_p lands in the published physical band.

V1 keeps these in `main.py`, which imports FastAPI and starts a simulation on import, so
they are compared against a re-derivation from V1's own published constants rather than by
importing that module. The constants themselves are asserted against V1's source text.
"""

from __future__ import annotations

import math
import re

import pytest

from ureasim.data import design_point as dp
from ureasim.thermo import empirical as new
from tests.equivalence.v1_loader import V1_BACKEND, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

#: Temperatures spanning every aqueous stream in the plant: 40 C absorber liquor to 212 C
#: utility condensate.
TEMPERATURES_C = [0.0, 25.0, 40.0, 60.0, 88.0, 99.0, 106.0, 135.0, 143.0,
                  190.0, 200.0, 212.0]

#: Urea mass fractions from the recirculation feed to the finished melt.
UREA_FRACTIONS = [0.0, 0.30, 0.6874, 0.7174, 0.80, 0.943, 0.9771, 1.0]


def _v1_constant(name: str) -> float:
    """Read a top-level constant out of V1's `main.py` source without importing it.

    `main.py` builds a FastAPI app and a full plant state at import, so importing it here
    would start a simulation to check a number.
    """
    text = (V1_BACKEND / "main.py").read_text(encoding="utf-8", errors="replace")
    m = re.search(rf"^{re.escape(name)}\s*=\s*([-\d.eE+]+)", text, re.MULTILINE)
    assert m, f"{name} not found in V1 main.py"
    return float(m.group(1))


# --------------------------------------------------------------------------------------
# The design anchors themselves
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("name,value", [
    ("R323_CP_SOLN", dp.R323_CP_SOLN),
    ("C10_RHO_A", dp.C10_RHO_A),
    ("C10_RHO_B", dp.C10_RHO_B),
    ("C10_RHO_C", dp.C10_RHO_C),
    ("C10_W_DES", dp.C10_W_DES),
    ("C10_T_DES", dp.C10_T_DES),
])
def test_design_anchors_match_v1(name, value):
    assert value == _v1_constant(name)


# --------------------------------------------------------------------------------------
# Water
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("t_c", TEMPERATURES_C)
def test_water_cp_matches_the_v1_polynomial(t_c):
    expected = (4.21143048 - 0.0010464288 * t_c
                + 0.000008708461 * t_c * t_c + 0.00000001809921 * t_c ** 3)
    assert new.cp_water_kjkgk(t_c) == expected


@pytest.mark.parametrize("t_c", TEMPERATURES_C)
def test_water_cp_tracks_iapws(t_c):
    """The fit's own gate: 0.21 % worst residual against IF97 over 0-212 C.

    Compared against the independent IF97 implementation in `thermo.iapws`, by finite
    difference of the saturated-liquid enthalpy — so this is not the polynomial checking
    itself.
    """
    from ureasim.thermo import iapws
    h = 0.5
    lo, hi = max(t_c - h, 0.05), min(t_c + h, 220.0)
    cp_if97 = (iapws.h_liquid_sat_kjkg(hi) - iapws.h_liquid_sat_kjkg(lo)) / (hi - lo)
    assert new.cp_water_kjkgk(t_c) == pytest.approx(cp_if97, rel=0.01)


@pytest.mark.parametrize("t_c", TEMPERATURES_C)
def test_water_density_tracks_iapws(t_c):
    """Wagner & Pruss against IF97 Region 1: the published claim is 0.0047 % over 0-220 C."""
    from ureasim.thermo import iapws
    assert new.water_rho_sat(t_c) == pytest.approx(
        iapws.rho_liquid_sat_kgm3(max(t_c, 0.05)), rel=1e-4)


def test_water_density_at_the_critical_point():
    assert new.water_rho_sat(new.WATER_TC_K - 273.15) == new.WATER_RHOC


# --------------------------------------------------------------------------------------
# Urea solutions
# --------------------------------------------------------------------------------------

def test_molten_urea_cp_is_back_solved_into_the_published_band():
    """About 2.072 against a published 2.0-2.1 for molten urea.

    It is derived from the anchor rather than typed in, so it cannot drift out of step with
    `cp_water_kjkgk`; this test is the independent corroboration that the derivation lands
    somewhere physical.
    """
    assert 2.0 <= new.CP_UREA_MELT <= 2.1
    expected = ((dp.R323_CP_SOLN - (1.0 - dp.C10_W_DES)
                 * new.cp_water_kjkgk(dp.C10_T_DES)) / dp.C10_W_DES)
    assert new.CP_UREA_MELT == expected


def test_solution_cp_returns_the_anchor_bit_exactly_at_design():
    """The whole point of the departure form. Not approx — the same float."""
    assert new.urea_soln_cp(dp.C10_W_DES, dp.C10_T_DES) == dp.R323_CP_SOLN


def test_solution_density_returns_the_anchor_bit_exactly_at_design():
    for anchor in (1180.0, 1249.5, 1333.0):
        assert new.urea_soln_rho(dp.C10_W_DES, dp.C10_T_DES, anchor) == anchor


@pytest.mark.parametrize("w", UREA_FRACTIONS)
@pytest.mark.parametrize("t_c", [99.0, 130.0, 140.0])
def test_solution_properties_match_the_v1_form(w, t_c):
    cp_raw = (min(max(w, 0.0), 1.0) * new.CP_UREA_MELT
              + (1.0 - min(max(w, 0.0), 1.0)) * new.cp_water_kjkgk(t_c))
    cp_raw_des = (dp.C10_W_DES * new.CP_UREA_MELT
                  + (1.0 - dp.C10_W_DES) * new.cp_water_kjkgk(dp.C10_T_DES))
    assert new.urea_soln_cp(w, t_c) == dp.R323_CP_SOLN + (cp_raw - cp_raw_des)

    rho_raw = (dp.C10_RHO_A + dp.C10_RHO_B * min(max(w, 0.0), 1.0)
               + dp.C10_RHO_C * (t_c - 100.0))
    rho_raw_des = (dp.C10_RHO_A + dp.C10_RHO_B * dp.C10_W_DES
                   + dp.C10_RHO_C * (dp.C10_T_DES - 100.0))
    assert new.urea_soln_rho(w, t_c, 1249.5) == 1249.5 + (rho_raw - rho_raw_des)


def test_concentrating_a_solution_raises_density_and_lowers_cp():
    """The physical direction the constant c_p could not represent.

    Through the recirculation and evaporation train a liquor goes from 68 % to 99.7 % urea.
    Its c_p must fall and its density must rise; a single constant gets both wrong in the
    same direction at every stage.
    """
    cp_weak = new.urea_soln_cp(0.6874, 106.0)
    cp_melt = new.urea_soln_cp(0.9771, 140.0)
    assert cp_melt < cp_weak

    rho_weak = new.urea_soln_rho(0.6874, 106.0, 1249.5)
    rho_melt = new.urea_soln_rho(0.9771, 106.0, 1249.5)
    assert rho_melt > rho_weak


# --------------------------------------------------------------------------------------
# Aqueous departures
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("t_des,t_c", [(139.0, 139.0), (143.0, 143.0), (56.0, 56.0)])
def test_aqueous_forms_return_their_anchor_bit_exactly(t_des, t_c):
    for anchor in (933.0, 923.28, 4.0, 3.0):
        assert new.aqueous_rho(anchor, t_des, t_c) == anchor
        assert new.aqueous_cp(anchor, t_des, t_c) == anchor


def test_the_parentheses_in_aqueous_rho_are_load_bearing():
    """`anchor * (r/r)` is exact; `anchor * r / r` is not, for about 10 % of operands.

    The design anchor depends on this, so it is pinned rather than trusted to survive a
    tidy-up.
    """
    mismatches = 0
    trials = 0
    for anchor in (933.0, 923.28, 1249.5, 1010.7, 872.31):
        for t in (44.0, 88.0, 139.0, 190.0, 212.0):
            trials += 1
            r_num = new.water_rho_sat(t)
            left_to_right = anchor * r_num / r_num
            if left_to_right != anchor:
                mismatches += 1
            # The shipped form must be exact for every one of them.
            assert new.aqueous_rho(anchor, t, t) == anchor
    assert mismatches > 0, (
        "the hazard this guard exists for did not reproduce on these operands; "
        "the guard is still correct, but pick operands that demonstrate it"
    )


def test_aqueous_density_falls_with_temperature():
    assert new.aqueous_rho(933.0, 139.0, 190.0) < 933.0
    assert new.aqueous_rho(933.0, 139.0, 88.0) > 933.0


def test_the_pfd_amm_water_rows_above_150c_are_the_impossible_ones():
    """The measurement that licensed departing from the PFD density row.

    Streams 746 (190 C, tabulated 908.5) and 747 (200 C, tabulated 897.7) sit ~3.7-3.8 %
    above real water. The engine anchors on 933.0 at 139 C and 923.28 at 143 C instead,
    which are within 0.7 % of water — so the fix never has to anchor on a bad number.
    """
    assert new.water_rho_sat(190.0) == pytest.approx(876.08, abs=0.5)
    assert new.water_rho_sat(200.0) == pytest.approx(864.67, abs=0.5)
    assert 908.5 / new.water_rho_sat(190.0) - 1.0 == pytest.approx(0.037, abs=0.002)
    assert 897.7 / new.water_rho_sat(200.0) - 1.0 == pytest.approx(0.038, abs=0.002)
    # The anchors actually used are sound.
    assert abs(933.0 / new.water_rho_sat(139.0) - 1.0) < 0.01
    assert abs(923.28 / new.water_rho_sat(143.0) - 1.0) < 0.01


# --------------------------------------------------------------------------------------
# Transport
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("t_c", TEMPERATURES_C)
def test_viscosities_match_the_v1_form(t_c):
    t_k = t_c + 273.15
    assert new.viscosity_liq_pas(t_c) == max(1.2e-5 * math.exp(2200.0 / t_k), 1e-4)
    assert new.viscosity_gas_pas(t_c) == 1.5e-5 * (t_k / 450.0) ** 0.8


def test_liquid_viscosity_is_in_the_documented_band():
    """1.0-3.0 cP in the synthesis loop."""
    for t_c in (165.0, 183.0, 190.0):
        assert 0.0005 < new.viscosity_liq_pas(t_c) < 0.004


def test_gas_viscosity_is_in_the_documented_band():
    for t_c in (100.0, 183.0):
        assert 1.0e-5 < new.viscosity_gas_pas(t_c) < 2.5e-5
