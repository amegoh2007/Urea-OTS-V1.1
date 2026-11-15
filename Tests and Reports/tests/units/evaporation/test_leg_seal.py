"""324F003's barometric leg: the air its lost seal admits (handoff B-107, decided 2026-10-22).

The stage's response, both ways against V1's sealed leg, is
`tests/equivalence/test_second_evaporator_decided_equivalence`.
"""

from __future__ import annotations

import pytest

from ureasim.control.valve import cv_fraction
from ureasim.data import unit_324 as d
from ureasim.units.evaporation.leg_seal import SEAL_AIR_RHO_KGM3, seal_air_kgh


def test_a_sealed_leg_admits_nothing():
    """Exactly zero at any level above the seal's 3 % band, at any stroke and vacuum."""
    for level in (3.0, 10.0, d.F003_LEVEL_SP_PCT, 100.0):
        assert seal_air_kgh(level, 100.0, 0.131) == 0.0


def test_the_air_is_the_atmosphere_s_at_pfd_783():
    """PFD 783's air at one atmosphere and 32 C: 1.152 kg/m3 (the PFD prints 1.15 at 1 bar a)."""
    assert SEAL_AIR_RHO_KGM3 == pytest.approx(1.1522, abs=1e-4)


def test_a_lost_seal_admits_air_choked_on_the_drain_s_trim():
    """Fully uncovered at the design stroke: 732 kg/h, choked below 0.30 bar a, so the same at the
    design vacuum and at 0.2 bar a; it falls as the vacuum breaks toward the atmosphere, and it
    scales with the trim's capacity at the stroke and the uncovered share of the seal's band —
    LV-324501A's equal percentage from 75.35 % (decision 150), V1's line from 75 %."""
    des = d.LV_324501A_OP_DES_PCT
    full = seal_air_kgh(0.0, des, 0.131)
    assert full == pytest.approx(732.15, abs=0.01)
    assert seal_air_kgh(0.0, d.LIC_324501_OP_DES_PCT, 0.131, vendor=False) == full
    assert seal_air_kgh(0.0, des, 0.2) == full
    assert seal_air_kgh(0.0, des, 0.9) < full
    assert seal_air_kgh(0.0, des / 2.0, 0.131) == pytest.approx(
        full * cv_fraction(des / 200.0, "equal_pct") / cv_fraction(des / 100.0, "equal_pct"))
    assert seal_air_kgh(0.0, d.LIC_324501_OP_DES_PCT / 2.0, 0.131, vendor=False) == (
        pytest.approx(full / 2.0))
    assert seal_air_kgh(1.5, des, 0.131) == pytest.approx(full / 2.0)
    assert seal_air_kgh(0.0, 0.0, 0.131) == 0.0
