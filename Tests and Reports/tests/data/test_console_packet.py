"""The console packet's constants — `ureasim.data.console_packet` — against V1's.

Each constant is quoted from V1's packet or its stream registry; this pins that each is V1's to
the bit, read out of ``main.py`` where V1 names it, so a copy cannot drift from its source.
"""

from __future__ import annotations

import pytest

from ureasim.data import console_packet as c
from tests.equivalence.v1_loader import lift, load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)


@pytest.fixture(scope="module")
def v1():
    return lift(["PFD_324_MASS_PCT", "REACT_OVERFLOW_RHO", "REACT_OFFGAS_RHO", "A328_M755_RHO",
                 "P_SYN_DOWN_BAR"], seed={"iapws_if97": load("iapws_if97")})


def test_the_stream_rows_are_v1s(v1):
    """Every PFD row the registry builds on is V1's ``PFD_324_MASS_PCT`` row."""
    for no, row in c.STREAM_PCT.items():
        assert row == v1["PFD_324_MASS_PCT"][no], no


def test_the_densities_and_the_discharge_header_are_v1s(v1):
    assert c.REACT_OVERFLOW_RHO == v1["REACT_OVERFLOW_RHO"]
    assert c.REACT_OFFGAS_RHO == v1["REACT_OFFGAS_RHO"]
    assert c.RHO_755_KGM3 == v1["A328_M755_RHO"]
    assert c.PI_DISCH_DES_BARG == v1["P_SYN_DOWN_BAR"] - 1.0 == 164.0
