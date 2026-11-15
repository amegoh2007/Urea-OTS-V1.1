"""V1 <-> V1.1 equivalence for the IAPWS-IF97 water boundary.

Gate: every public entry point must agree with V1 **exactly** (bit-for-bit), because the
port changed only documentation and layout — the coefficient tables and the evaluation
order are unchanged. Any difference at all means a transcription error.

The states swept are the ones the plant actually sits at, not a generic grid:

    4.4  bar a   LP steam drums 322D001 A/B     -> HPCC 322E002 shell
    9.0  bar a   MP drum 329D009                -> 9-bar header
    19.7 bar a   HP saturator 329D005           -> HP stripper 322E001 shell
    25.0 bar a   battery-limit supply, stream 901
    1.013 bar a  atmospheric vents
    0.33 / 0.131 / 0.46 bar a   the 324 and 323 vacuum stages
"""

from __future__ import annotations

import pytest

from ureasim.thermo import iapws as new
from tests.equivalence.v1_loader import load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

#: Plant pressures [bar a] that a steam or vacuum node actually occupies.
PLANT_PRESSURES_BARA = [0.131, 0.33, 0.46, 1.013, 4.4, 9.0, 19.7, 25.0]

#: Plant temperatures [deg C] spanning cold condensate to battery-limit steam.
PLANT_TEMPERATURES_C = [40.0, 45.0, 55.0, 99.0, 106.0, 130.0, 135.0, 140.0,
                        147.9, 175.4, 200.0, 211.1, 223.9]


@pytest.fixture(scope="module")
def v1():
    return load("iapws_if97")


def test_constants_match(v1):
    assert new.R_KJ_KGK == v1.R_KJ_KGK
    assert new.T_MIN_K == v1.T_MIN_K
    assert new.T_CRIT_K == v1.T_CRIT_K
    assert new.P_CRIT_MPA == v1.P_CRIT_MPA
    assert new.REGION1_T_MAX_K == v1.REGION1_T_MAX_K


@pytest.mark.parametrize("p_bara", PLANT_PRESSURES_BARA)
def test_tsat_bit_exact(v1, p_bara):
    """Tsat(P) is the single most load-bearing steam call — see iapws.tsat_k docstring."""
    assert new.tsat_c(p_bara) == v1.tsat_c(p_bara)


@pytest.mark.parametrize("t_c", PLANT_TEMPERATURES_C)
def test_psat_bit_exact(v1, t_c):
    assert new.psat_bara(t_c) == v1.psat_bara(t_c)


@pytest.mark.parametrize("t_c", PLANT_TEMPERATURES_C)
def test_saturated_enthalpies_bit_exact(v1, t_c):
    assert new.h_liquid_sat_kjkg(t_c) == v1.h_liquid_sat_kjkg(t_c)
    assert new.h_vapour_sat_kjkg(t_c) == v1.h_vapour_sat_kjkg(t_c)
    assert new.hvap_kjkg(t_c) == v1.hvap_kjkg(t_c)


@pytest.mark.parametrize("t_c", PLANT_TEMPERATURES_C)
def test_volumes_and_density_bit_exact(v1, t_c):
    assert new.v_liquid_sat_m3kg(t_c) == v1.v_liquid_sat_m3kg(t_c)
    assert new.v_vapour_sat_m3kg(t_c) == v1.v_vapour_sat_m3kg(t_c)
    assert new.rho_liquid_sat_kgm3(t_c) == v1.rho_liquid_sat_kgm3(t_c)


@pytest.mark.parametrize("t_c", [40.0, 106.0, 175.4, 223.9])
@pytest.mark.parametrize("p_bara", [1.013, 4.4, 19.7, 25.0])
def test_single_phase_enthalpies_bit_exact(v1, t_c, p_bara):
    assert new.h_liquid_kjkg(t_c, p_bara) == v1.h_liquid_kjkg(t_c, p_bara)
    assert new.h_vapour_kjkg(t_c, p_bara) == v1.h_vapour_kjkg(t_c, p_bara)


def test_out_of_range_refuses_in_both(v1):
    """Refusal is a feature (As-Built Part 0, Rule 2) — it must survive the port."""
    with pytest.raises(new.OutOfRange):
        new.psat_mpa(700.0)
    with pytest.raises(v1.OutOfRange):
        v1.psat_mpa(700.0)

    with pytest.raises(new.OutOfRange):
        new.tsat_k(30.0)
    with pytest.raises(v1.OutOfRange):
        v1.tsat_k(30.0)

    with pytest.raises(new.OutOfRange):
        new.h_liquid_sat_kjkg(360.0)      # above the Region 1 ceiling
    with pytest.raises(v1.OutOfRange):
        v1.h_liquid_sat_kjkg(360.0)
