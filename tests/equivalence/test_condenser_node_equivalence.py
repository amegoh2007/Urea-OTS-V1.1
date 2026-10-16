"""V1 <-> V1.1 equivalence for a unit 324 condenser as a flowsheet node.

V1's ``vacuum_inlet_kmolh`` and ``vacuum_condenser_node`` are lifted out of ``main.py`` and
executed on V1's own ``vacuum_condenser`` module and design specs, against
`ureasim.units.evaporation.condenser_node`: the live inlet over loads, false air and a
blow-through part of known composition; the node over shell pressures, cooling water, a lost
condenser and a lagged cold end — every field ``==``, and V1's lagged cold end the port's
``t_vent_c``. V1's module runs with handoff B-67's and B-71's switch (`tests.equivalence.b67_switch`).
"""

from __future__ import annotations

import math

import pytest

from ureasim.units.evaporation import condenser_node as cn
from tests.equivalence.b67_switch import switched_module
from tests.equivalence.v1_loader import lift, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

TAGS = ("324E002", "324E005", "324E006", "324E007")
FIELDS = ("tag", "inlet_kgh", "condensate_kgh", "vent_kgh", "q_kw", "lmtd_k", "ua_kw_k",
          "cw_flow_kgh", "cw_in_c", "cw_out_c", "hot_in_c", "hot_out_c", "t_vent_c", "p_bara",
          "vent_kmolh", "mass_residual_kgh", "energy_residual_kw")
#: The false air at design on the two first-stage condensers, PFD 784 and 783 (V1
#: ``R324_F001_FA_DES``, ``R324_F003_FA_DES``).
AIR_DES = {"324E002": 21.0, "324E005": 21.0}
BLOW_THROUGH = (850.0, {"NH3": 0.55, "CO2": 0.30, "H2O": 0.15})


@pytest.fixture(scope="module")
def v1():
    return lift(["vacuum_inlet_kmolh", "vacuum_condenser_node", "VACUUM_CONDENSER_SPECS",
                 "R324_F001_FA_DES", "R324_F003_FA_DES"],
                seed={"math": math, "vacuum_condenser": switched_module()})


def test_the_design_false_air_is_v1s(v1):
    assert AIR_DES == {"324E002": v1["R324_F001_FA_DES"], "324E005": v1["R324_F003_FA_DES"]}


@pytest.mark.parametrize("tag", ("324E002", "324E005"))
@pytest.mark.parametrize("scale", (0.0, 0.5, 1.0, 1.3))
@pytest.mark.parametrize("air", (0.0, 1.0, 2.5))
def test_the_live_inlet_is_v1s(v1, tag, scale, air):
    spec = v1["VACUUM_CONDENSER_SPECS"][tag]
    m_air = AIR_DES[tag] * air
    m_in = (spec["inlet_kgh"] - AIR_DES[tag]) * scale + m_air
    for sub in (None, (0.0, {}), BLOW_THROUGH):
        mine = cn.inlet_kmolh(tag, m_in, m_air, AIR_DES[tag], sub)
        assert mine == v1["vacuum_inlet_kmolh"](tag, m_in, m_air, AIR_DES[tag], sub), sub


@pytest.mark.parametrize("tag", TAGS)
@pytest.mark.parametrize("p_factor", (0.8, 1.0, 1.25))
@pytest.mark.parametrize("cw", ((None, None), (0.5, None), (0.0, None), (1.0, 35.0)))
def test_the_node_is_v1s(v1, tag, p_factor, cw):
    spec = v1["VACUUM_CONDENSER_SPECS"][tag]
    n_in = {k: v * 1.1 for k, v in spec["n_in_des"].items()}
    cw_flow = None if cw[0] is None else spec["cw_flow_kgh"] * cw[0]
    for lagged in (None, spec["t_v_solved_des"] + 3.0):
        tv = None if lagged is None else {tag + "_T_VENT": lagged}
        theirs = v1["vacuum_condenser_node"](tag, spec["inlet_kgh"] * 1.1, n_in,
                                             spec["p_des"] * p_factor, cw_flow, cw[1], tv)
        mine = cn.condenser_node(tag, spec["inlet_kgh"] * 1.1, n_in, spec["p_des"] * p_factor,
                                 cw_flow, cw[1], lagged)
        for name in FIELDS:
            assert getattr(mine, name) == theirs[name], (name, lagged)
        if tv is not None:
            assert tv[tag + "_T_VENT"] == mine.t_vent_c
