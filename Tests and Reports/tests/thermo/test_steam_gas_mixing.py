"""Behaviour of the adiabatic steam-gas mix — `ureasim.thermo.steam_gas_mixing`.

New with handoff B-97 (decided 2026-10-16): no V1 relation to prove against. The mix is pinned on
the first law it states, on IAPWS-IF97 for a steam alone, and on 324E002's design vent, the gas
324F002 entrains.
"""

from __future__ import annotations

import pytest

from ureasim.thermo import iapws
from ureasim.thermo import steam_gas_mixing as sg

#: Saturated steam off the LP header's design 4.0 bar g [kJ/kg].
H_LP = iapws.h_vapour_sat_kjkg(iapws.tsat_c(5.01325))

#: 324E002's design vent, PFD 706 [kmol/h]: its water saturated vapour at its 45 C cold end.
VENT_706 = {"H2O": 0.87429, "NH3": 0.53278, "CO2": 0.11334, "N2": 1.163736, "O2": 0.290934}


def test_a_steam_alone_throttles_onto_if97():
    """No gas: the LP header's saturated steam let down to 1.0 bar a leaves superheated at
    135.753 C, where IF97's vapour holds the header's enthalpy."""
    t = sg.mix_temperature_c({}, 50.0, 390.0, H_LP, 1.0)
    assert t == pytest.approx(135.753, abs=1e-3)
    assert iapws.h_vapour_kjkg(t, 1.0) == pytest.approx(H_LP, abs=1e-7)


def test_the_mix_holds_the_inlets_enthalpy():
    """The first law: at the answer the mix carries what arrived, 706 and 390 kg/h of steam
    mixed at 125.62 C, the water all vapour."""
    t = sg.mix_temperature_c(VENT_706, 45.0, 390.0, H_LP, 1.0)
    gas = {k: n for k, n in VENT_706.items() if k != "H2O"}
    n_w = VENT_706["H2O"] + 390.0 / sg.M_H2O
    h_in = (sg.mixture_kjh(gas, 0.0, 45.0, 1.0) + 390.0 * H_LP
            + sg.M_H2O * VENT_706["H2O"] * iapws.h_vapour_sat_kjkg(45.0))
    assert t == pytest.approx(125.6215, abs=1e-4)
    assert sg.mixture_kjh(gas, n_w, t, 1.0) == pytest.approx(h_in, rel=1e-12)


def test_more_steam_runs_the_mix_hotter():
    """Half the steam 117.54 C, a fifth more 127.15 C: the mix between the gas and the steam."""
    temps = [sg.mix_temperature_c(VENT_706, 45.0, m, H_LP, 1.0) for m in (195.0, 390.0, 468.0)]
    assert temps == [pytest.approx(117.5386, abs=1e-4), pytest.approx(125.6215, abs=1e-4),
                     pytest.approx(127.1489, abs=1e-4)]


def test_without_steam_the_gas_condenses_its_water_at_the_mixing_point():
    """No steam, 706 alone at 1.0 bar a: its water's partial pressure, 0.29 bar, is above
    saturation at 45 C, so part of it condenses and its latent heat holds the mix at 67.66 C,
    on its dew point. A dry gas leaves at its own temperature."""
    t = sg.mix_temperature_c(VENT_706, 45.0, 0.0, H_LP, 1.0)
    n_all = sum(VENT_706.values())
    assert t == pytest.approx(67.662, abs=1e-3)
    assert iapws.psat_bara(t) < VENT_706["H2O"] / n_all
    assert sg.mix_temperature_c({"N2": 1.0}, 50.0, 0.0, H_LP, 1.0) == pytest.approx(50.0,
                                                                                   abs=1e-9)


def test_nothing_arriving_has_no_temperature():
    with pytest.raises(ValueError):
        sg.mix_temperature_c({"N2": 0.0}, 45.0, 0.0, H_LP, 1.0)
