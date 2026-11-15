"""`ureasim.core.units_of_measure` — the conventions and their constants.

Handoffs B-6 and B-7, decided 2026-10-07: one atmosphere, 1.01325 bar, and one gravity, standard,
everywhere — in every process relation and on every display.
"""

from __future__ import annotations

import pytest

from ureasim.core import units_of_measure as u
from ureasim.data import unit_320, unit_329, unit_329_network
from ureasim.hmi import state_access
from ureasim.units.absorption import vent_line


def test_one_atmosphere_and_one_gravity():
    assert u.ATM_BARA == 1.01325
    assert u.G_ACC == 9.80665
    for gone in ("ATM_PROCESS_BAR", "ATM_DISPLAY_BARA"):
        assert not hasattr(u, gone)


def test_every_atmosphere_the_plant_converts_on_is_the_one():
    """SV-32201's set, trip 21.2's two pressures, the 322C001 vent line, the steam vents and the
    consoles' gauge readings all on 1.01325 (V1 wrote 1.013 in the first four)."""
    assert unit_320.SYN_PSV_SET_BARA == 160.0 + 1.01325
    assert unit_329_network.TRIP_212_SP_BARA == 10.0 + 1.01325
    assert unit_329_network.HV601_FORCE_BARA == 12.0 + 1.01325
    assert vent_line.VENT_LINE_P_BARA == unit_329.P_ATM_VENT_BARA == state_access.ATM_BAR == 1.01325


def test_the_gauge_conversions_round_trip():
    assert u.bara_to_barg(161.01325) == pytest.approx(160.0, abs=1e-12)
    assert u.barg_to_bara(u.bara_to_barg(0.343)) == pytest.approx(0.343, abs=1e-15)
