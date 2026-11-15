"""V1 <-> V1.1 equivalence for the condensing-steam chest shared by the LP-steam heaters.

V1's ``_steam_chest_residual_kw`` and ``steam_chest_pressure`` are lifted out of ``main.py``
and executed against `units.steam_chest`, with ``==``, over the 323E002 chest's whole operating
envelope: stroke, header pressure, process temperature and the previous tick's pressure the
solve starts from — on the port's 3.9 bar a anchor, which both are handed. V1's
``_chest_slave_kc_scale`` is not ported (decided 2026-09-30); the two chest-cascade equivalence
tests assert what it did against what the port does instead.
"""

from __future__ import annotations

import math

import pytest

from ureasim.data import unit_323 as d
from ureasim.data.unit_329 import P_LP_BARA, STEAM_GAMMA, STEAM_MW
from ureasim.units import steam_chest as sc
from tests.equivalence.v1_loader import lift, load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)


@pytest.fixture(scope="module")
def v1():
    return lift(["_steam_chest_residual_kw", "steam_chest_pressure",
                 "STEAM_CHEST_P_MIN_BARA"], seed={
        "math": math,
        "iapws_if97": load("iapws_if97"),
        "hydraulics": load("hydraulics"),
        "steam_system": load("steam_system"),
    })


def test_constants(v1):
    steam = load("steam_system")
    assert sc.STEAM_CHEST_P_MIN_BARA == v1["STEAM_CHEST_P_MIN_BARA"]
    assert (P_LP_BARA, STEAM_GAMMA, STEAM_MW) == (steam.P_LP_BARA, steam.STEAM_GAMMA,
                                                 steam.STEAM_MW)


@pytest.mark.parametrize("stroke", [0.0, 5.0, 40.0, 77.79, 100.0])
@pytest.mark.parametrize("header", [3.0, 4.6, P_LP_BARA, 6.0])
@pytest.mark.parametrize("t_process", [100.0, 135.0, 150.0, 165.0])
@pytest.mark.parametrize("p_prev", [None, 2.0, d.E002_PCHEST_DES_BARA])
def test_chest_pressure(v1, stroke, header, t_process, p_prev):
    args = (stroke, header, d.E002_OP_DES_PCT, d.E002_PCHEST_DES_BARA, d.E002_UA_KW, t_process,
            d.E002_Q_DES_KW, P_LP_BARA, p_prev)
    assert sc.steam_chest_pressure(*args) == v1["steam_chest_pressure"](*args)


@pytest.mark.parametrize("p_chest", [0.02, 1.0, 3.0, 3.9, 5.0])
@pytest.mark.parametrize("stroke", [0.0, 50.0, 100.0])
def test_residual(v1, p_chest, stroke):
    args = (p_chest, stroke, P_LP_BARA, d.E002_OP_DES_PCT, d.E002_PCHEST_DES_BARA, P_LP_BARA,
            d.E002_UA_KW, 135.0, d.E002_Q_DES_KW)
    assert sc.chest_residual_kw(*args) == v1["_steam_chest_residual_kw"](*args)

