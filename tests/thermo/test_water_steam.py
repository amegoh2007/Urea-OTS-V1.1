"""Behaviour of the drum water-steam relations — `ureasim.thermo.water_steam`.

Equivalence of the three V1 relations is proven in
`tests/equivalence/test_steam_network_equivalence.py`; this file pins the flash and the
desuperheat the steam network balances on (handoff B-70), on the PFD's own closures.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_329 as d
from ureasim.thermo import water_steam as ws


def test_913_flashes_into_the_lp_header():
    """329D009's saturated condensate let down to 322D001: 4.84 % flashes at the 4.0 bar g
    header (2570 of 53 056 kg/h), 5.80 % at the PFD's 4.4 bar a (3076 kg/h, the PFD's 915 3062);
    LV-329502's into 329D009, 8.00 % (4639 of 57 989, the PFD's 906 4658). Nothing flashes into a
    drum no lower."""
    assert ws.flash_fraction(9.0, 5.01325) == pytest.approx(0.048447, abs=1e-6)
    assert ws.flash_fraction(9.0, 4.4) * 53056.0 == pytest.approx(3076.0, abs=0.5)
    assert ws.flash_fraction(19.7, 9.0) * 57989.0 == pytest.approx(4638.7, abs=0.1)
    assert ws.flash_fraction(5.0, 9.0) == 0.0


def test_the_superheats_boil_their_drums_water():
    """902 at the PFD's 328 C into 329D005: 0.1537 kg of water per kg, 8913 kg/h at design; 903
    at 317 C into 329D009: 274 kg/h of its 1754, the PFD's 275 "saturation water"; 963 at 312 C
    into 322D001, 0.163; 9-bar steam let down to the LP header, 0.0118; a saturated steam,
    nothing."""
    assert ws.superheat_water_ratio(d.H_902_KJKG, 19.7) * 57989.0 == pytest.approx(8912.66,
                                                                                  abs=0.01)
    assert ws.superheat_water_ratio(d.H_903_KJKG, 9.0) * 1754.0 == pytest.approx(274.16,
                                                                                abs=0.01)
    assert ws.superheat_water_ratio(d.H_963_KJKG, 5.01325) == pytest.approx(0.16254, abs=1e-5)
    assert ws.superheat_water_ratio(ws.h_vapour_sat_at_kjkg(9.0), 5.01325) == pytest.approx(
        0.011773, abs=1e-6)
    assert ws.superheat_water_ratio(ws.h_vapour_sat_at_kjkg(9.0), 9.0) == 0.0


def test_a_header_below_the_triple_point_is_held_there():
    """A collapsed header does not take the property line out of its range: every relation is
    read at the triple point below it."""
    assert ws.rho_drum_liquid_kgm3(0.0) == pytest.approx(999.79, abs=0.01)
    assert ws.flash_fraction(9.0, 0.0) == ws.flash_fraction(9.0, ws.P_TRIPLE_BARA)
    assert ws.superheat_water_ratio(d.H_963_KJKG, 0.0) == pytest.approx(0.23587, abs=1e-5)


def test_the_lp_drums_capacitance():
    """322D001A/B's 91.3 m3 of steam space gains 45.9 kg per bar at 4.0 bar g."""
    assert ws.vapour_capacitance_kg_bar(91.322, 5.01325) == pytest.approx(45.92, abs=0.01)
