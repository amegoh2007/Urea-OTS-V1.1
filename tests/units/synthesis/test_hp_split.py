"""The HP loop's anchored K-value ratio — `ureasim.units.synthesis.hp_split`.

Pinned: at the reference state the ratio is exactly 1.0 for every species, by the arithmetic, so a
split built on it reproduces the licensor's vector at the design; the ratio is the thermo service's
`k_ratio` on the stream's mass fractions and nothing else; a hotter, lower-pressure loop raises
ammonia's and water's volatility and a colder, higher-pressure one lowers it; every ratio stays in
the service's [0.02, 50] band.
"""

from __future__ import annotations

from ureasim.core.stream import mass_fractions_from_kmolh
from ureasim.thermo.kvalues import k_ratio
from ureasim.units.synthesis.hp_split import hp_k_ratio

#: A reactor-overflow-like molar feed [kmol/h].
FEED = {"NH3": 2200.0, "CO2": 700.0, "H2O": 1100.0, "UREA": 1100.0}
T_REF, P_REF = 183.0, 144.0


def test_the_reference_state_returns_exactly_one():
    out = hp_k_ratio(FEED, T_REF, P_REF, T_REF, P_REF)
    assert out and all(v == 1.0 for v in out.values())


def test_it_is_the_service_ratio_on_the_mass_fractions():
    assert hp_k_ratio(FEED, 188.0, 140.0, T_REF, P_REF) == k_ratio(
        mass_fractions_from_kmolh(FEED), 188.0, 140.0, T_REF, P_REF)


def test_the_loop_state_moves_the_volatility():
    hot = hp_k_ratio(FEED, 188.0, 140.0, T_REF, P_REF)
    cold = hp_k_ratio(FEED, 170.0, 150.0, T_REF, P_REF)
    assert hot["NH3"] > 1.0 and hot["H2O"] > 1.0
    assert cold["NH3"] < 1.0 and cold["H2O"] < 1.0
    for out in (hot, cold):
        assert all(0.02 <= v <= 50.0 for v in out.values())
