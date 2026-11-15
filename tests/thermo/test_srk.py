"""The SRK vapour fugacity — `ureasim.thermo.srk`.

Pinned: the cubic solver returns the largest real root on both of its branches (three real roots
and one); the pure-component parameters take alpha = 1 at the critical temperature, and at the
critical point the compressibility is SRK's own 1/3; a gas at vanishing pressure is ideal (Z and
every phi go to 1); and the mixture's coefficients obey the van der Waals mixing rule's sum rule,
sum y_i ln phi_i = ln phi of the mixture, the identity every K-value built on them depends on.
"""

from __future__ import annotations

import math

import pytest

from ureasim.thermo.srk import R, SRK_CRIT, cubic_largest_root, srk_ai_bi, srk_phi


def test_the_cubic_returns_its_largest_real_root():
    assert cubic_largest_root(1.0, -6.0, 11.0, -6.0) == pytest.approx(3.0, abs=1e-12)
    assert cubic_largest_root(2.0, -12.0, 22.0, -12.0) == pytest.approx(3.0, abs=1e-12)
    assert cubic_largest_root(1.0, 0.0, 0.0, -8.0) == pytest.approx(2.0, abs=1e-12)
    assert cubic_largest_root(1.0, 0.0, 0.0, 8.0) == pytest.approx(-2.0, abs=1e-12)


@pytest.mark.parametrize("sp", sorted(SRK_CRIT))
def test_alpha_is_one_at_the_critical_temperature(sp):
    tc, pc, _w = SRK_CRIT[sp]
    a, b = srk_ai_bi(sp, tc)
    assert a == pytest.approx(0.42748 * R * R * tc * tc / pc, rel=1e-14)
    assert b == pytest.approx(0.08664 * R * tc / pc, rel=1e-14)
    # Below Tc the attraction grows, as the acentric correction says it must.
    assert srk_ai_bi(sp, 0.8 * tc)[0] > a


def test_the_critical_compressibility_is_one_third():
    tc, pc, _w = SRK_CRIT["CO2"]
    _phi, z = srk_phi({"CO2": 1.0}, tc, pc)
    # A triple root, so the five-figure constants 0.42748 and 0.08664 move it by their error's
    # cube root: 0.327 here.
    assert z == pytest.approx(1.0 / 3.0, rel=0.02)


@pytest.mark.parametrize("y", [{"NH3": 1.0}, {"NH3": 0.6, "CO2": 0.3, "H2O": 0.1},
                               {"N2": 0.2, "NH3": 0.5, "CO2": 0.3}])
def test_a_gas_at_vanishing_pressure_is_ideal(y):
    phi, z = srk_phi(y, 450.0, 1.0)
    assert z == pytest.approx(1.0, abs=1e-6)
    assert all(v == pytest.approx(1.0, abs=1e-5) for v in phi.values())


@pytest.mark.parametrize("t_k, p_pa", [(460.0, 14.4e6), (420.0, 2.0e6), (360.0, 0.4e6)])
def test_the_mixture_sum_rule(t_k, p_pa):
    y = {"NH3": 0.55, "CO2": 0.30, "H2O": 0.05, "N2": 0.07, "O2": 0.03}
    phi, z = srk_phi(y, t_k, p_pa)
    ab = {s: srk_ai_bi(s, t_k) for s in y}
    am = sum(y[s] * math.sqrt(ab[s][0]) for s in y) ** 2
    bm = sum(y[s] * ab[s][1] for s in y)
    a_mix, b_mix = am * p_pa / (R * t_k) ** 2, bm * p_pa / (R * t_k)
    # Z is a root of the mixture's cubic.
    assert z ** 3 - z ** 2 + (a_mix - b_mix - b_mix ** 2) * z - a_mix * b_mix == pytest.approx(
        0.0, abs=1e-12)
    ln_phi_mix = z - 1.0 - math.log(z - b_mix) - (a_mix / b_mix) * math.log(1.0 + b_mix / z)
    assert sum(y[s] * math.log(phi[s]) for s in y) == pytest.approx(ln_phi_mix, abs=1e-13)
    assert set(phi) == set(y)


def test_absent_species_are_left_out():
    phi, _z = srk_phi({"NH3": 0.7, "CO2": 0.3, "H2O": 0.0}, 450.0, 1.0e6)
    assert set(phi) == {"NH3", "CO2"}
