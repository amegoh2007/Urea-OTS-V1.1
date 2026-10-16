"""V1 <-> V1.1 equivalence for the ejectors' 1-D gas dynamics — `units.evaporation.ejector_gas_dynamics`.

V1's ``ejector_huang.py`` (never wired in V1) is loaded as a module and executed against the port
over the ranges the unit 324 maps evaluate it on: choking ratios, the isentropic relations, the
choked flux, the normal shock and the critical back pressure (V1's call carries temperatures and
areas it never reads; they are passed and ignored). Every value is ``==``. Then the standard
gas-dynamics table values V1's own module docstring cites.
"""

from __future__ import annotations

import pytest

from ureasim.units.evaporation import ejector_gas_dynamics as gd
from tests.equivalence.v1_loader import load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

GAMMAS = (1.3, 1.33, 1.4)
MACHS = (1.0001, 1.2, 1.5, 2.0, 2.9, 3.5, 4.3, 6.0)


@pytest.fixture(scope="module")
def eh():
    return load("ejector_huang")


def test_the_constants_are_v1s(eh):
    assert (gd.R_STEAM, gd.GAMMA_STEAM) == (eh.R_STEAM, eh.GAMMA_STEAM)


def test_the_isentropic_relations_are_v1s(eh):
    for g in GAMMAS:
        assert gd.critical_pressure_ratio(g) == eh.critical_pressure_ratio(g)
        for m in MACHS + (0.3, 0.7):
            assert gd.isentropic_p0_over_p(m, g) == eh.isentropic_p0_over_p(m, g)
            assert gd.isentropic_area_ratio(m, g) == eh.isentropic_area_ratio(m, g)
        for ratio in (1.9, 3.03, 7.45, 20.5, 31.3, 34.2, 280.0, 410.0):
            assert gd.mach_from_p0_ratio(ratio, g) == eh._mach_from_p0_ratio(ratio, g)


def test_the_choked_flux_and_the_shock_are_v1s(eh):
    for p0, t0, area in ((4.1e5, 419.15, 4.79e-4), (0.12e5, 313.15, 8.9e-3), (1.0, 300.0, 1.0)):
        assert gd.choked_mass_flow(p0, t0, area) == eh.choked_mass_flow(p0, t0, area)
        assert (gd.choked_mass_flow(p0, t0, area, 1.33, 384.7)
                == eh.choked_mass_flow(p0, t0, area, 1.33, 384.7))
    for g in GAMMAS:
        for m in MACHS:
            assert gd.normal_shock(m, g) == eh.normal_shock(m, g)


def test_the_critical_back_pressure_is_v1s(eh):
    for p_p in (1.0e5, 2.46e5, 3.9e5, 4.1e5):
        for p_s in (0.012e5, 0.12e5, 0.131e5, 0.2e5, 0.33e5):
            assert (gd.critical_back_pressure(p_p, p_s)
                    == eh.critical_backpressure(p_p, 419.15, p_s, 313.15, 1.0, 2.0))


def test_v1s_table_values_hold():
    """V1's docstring: gamma 1.4, P*/P0 0.5283, A/A* at Mach 2 1.6875, a Mach 2 shock to 0.5774
    with p2/p1 4.5 and p02/p01 0.7209."""
    assert gd.critical_pressure_ratio(1.4) == pytest.approx(0.5283, abs=1e-4)
    assert gd.isentropic_area_ratio(2.0, 1.4) == pytest.approx(1.6875, abs=1e-4)
    shock = gd.normal_shock(2.0, 1.4)
    assert (shock["M2"], shock["p2_p1"], shock["p02_p01"]) == (
        pytest.approx(0.5774, abs=1e-4), pytest.approx(4.5, abs=1e-12),
        pytest.approx(0.7209, abs=1e-4))
