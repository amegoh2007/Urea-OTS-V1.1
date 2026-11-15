"""K-values, bubble and dew points — `ureasim.thermo.kvalues`.

Pinned: without the vapour correction the bubble pressure is the sum of the volatile partial
pressures; the rigorous bubble temperature inverts the bubble pressure, and the memoised one the
plant calls stays within 0.05 C of it; the K-value ratio is exactly 1.0 at its reference, rises
for every volatile when the liquor is heated at a fixed pressure, and falls back to 1.0 (the
licensor's split) for a state no fitted model owns; a state outside every domain raises
`OutOfDomain` rather than returning a number.
"""

from __future__ import annotations

import pytest

from ureasim.thermo import kvalues as kv
from ureasim.thermo.domains import OutOfDomain

#: A dilute LP liquor [mass fractions].
LIQUOR = {"NH3": 0.10, "CO2": 0.05, "H2O": 0.85}


@pytest.mark.parametrize("t_c", [85.0, 100.0, 120.0])
def test_the_ideal_bubble_pressure_is_the_sum_of_the_partial_pressures(t_c):
    pp = kv.partial_pressures(LIQUOR, t_c)
    assert kv.bubble_p(LIQUOR, t_c, srk=False) == pytest.approx(sum(pp.values()), rel=1e-12)
    assert pp["NH3"] > 0.0 and pp["CO2"] > 0.0 and pp["H2O"] > 0.0


@pytest.mark.parametrize("p_bara", [1.5, 2.0, 3.5])
def test_the_bubble_temperature_inverts_the_bubble_pressure(p_bara):
    t_rigorous = kv._bubble_t_solve(LIQUOR, p_bara)
    assert kv.bubble_p(LIQUOR, t_rigorous) == pytest.approx(p_bara, rel=1e-6)
    assert kv.bubble_t(LIQUOR, p_bara) == pytest.approx(t_rigorous, abs=0.05)


def test_the_ratio_is_one_at_its_reference_and_rises_with_heat():
    assert set(kv.k_ratio(LIQUOR, 90.0, 2.0, 90.0, 2.0).values()) == {1.0}
    hot = kv.k_ratio(LIQUOR, 95.0, 2.0, 90.0, 2.0)
    assert hot["NH3"] > 1.0 and hot["CO2"] > 1.0 and hot["H2O"] > 1.0
    assert hot["N2"] == 1.0                                  # absent from the liquor


def test_an_unowned_state_falls_back_to_the_licensors_split():
    assert set(kv.k_ratio({"CO2": 1.0}, 95.0, 2.0, 90.0, 2.0).values()) == {1.0}
    with pytest.raises(OutOfDomain):
        kv.partial_pressures({"NH3": 0.05, "CO2": 0.50, "H2O": 0.45}, 80.0)
