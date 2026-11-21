"""322R001's liquor at its bubble point — `ureasim.units.synthesis.reactor_boil`.

Pinned (handoff B-92, decided 2026-10-14): the bubble line on the melt's own law, exactly the pinned
183 C at the design pressure and 0.53 K per bar about it, and the ceiling 3.5 K above it (decision
301, handoff A-63's candidate (b)); nothing flashes at the design seed, nor on a 5 bar fall; a node
above the ceiling is held on it and its excess heat flashes the overflow's volatiles in their own
proportions; a liquor with no volatile boils nothing and its excess is published.
"""

from __future__ import annotations

import pytest

from ureasim.core.stream import MW_COMP
from ureasim.data.synthesis_pin import REACT_CP_MELT_KJKGK, REACT_NODE_SS_DES_C
from ureasim.data.unit_320 import SYN_P_DES_BARA
from ureasim.data.unit_322r001 import OVERFLOW_DES_KMOLH, TAU_NODE_MIN
from ureasim.units.synthesis import reactor_boil
from ureasim.units.synthesis.reactor_boil import (
    BOIL_CAP_MARGIN_K,
    BOIL_DP_DES_BAR,
    BOIL_T_DES_C,
    liquor_bubble_t_c,
    node_boil,
    volatile_enthalpy_kjh,
)

DT = 0.1
TAUS = [t * 60.0 for t in TAU_NODE_MIN]
MCP = sum(OVERFLOW_DES_KMOLH[k] * MW_COMP[k] for k in MW_COMP) * REACT_CP_MELT_KJKGK


def test_the_design_pressure_returns_the_pinned_top_node_plus_the_margin(monkeypatch):
    """The line: 183 C under the off-gas line's 141.3 bar a, 0.6 bar over PT-329201's 140.7, to the
    bit; the ceiling 3.5 K above it, 186.5 C (decision 301). With the margin at zero the ceiling is
    the line as built before decision 301, the design top itself."""
    assert BOIL_DP_DES_BAR == pytest.approx(0.6, abs=1e-12)
    assert BOIL_CAP_MARGIN_K == 3.5
    assert liquor_bubble_t_c(SYN_P_DES_BARA) == BOIL_T_DES_C + BOIL_CAP_MARGIN_K
    assert liquor_bubble_t_c(SYN_P_DES_BARA) == pytest.approx(186.5, abs=1e-12)
    monkeypatch.setattr(reactor_boil, "BOIL_CAP_MARGIN_K", 0.0)
    assert liquor_bubble_t_c(SYN_P_DES_BARA) == BOIL_T_DES_C == REACT_NODE_SS_DES_C[-1]


@pytest.mark.parametrize("p_syn, t_bub", [(9.4, 47.854), (50.0, 120.445), (100.0, 162.303),
                                          (139.7, 185.966), (141.7, 187.031), (155.0, 193.868)])
def test_the_bubble_temperature_rides_the_loop_pressure(p_syn, t_bub):
    """PI-322E002's Clausius-Clapeyron slope, 23 kJ/mol: 0.53 K per bar at design, 44 C at the
    cold start's 9.4 bar a on the line, each 3.5 K higher on the ceiling (44.354, 116.945,
    158.803, 182.466, 183.531 and 190.368 C before decision 301)."""
    assert liquor_bubble_t_c(p_syn) == pytest.approx(t_bub, abs=1e-3)


def test_nothing_flashes_at_the_design_seed():
    """The top node 3.5 K under the ceiling; and after a 5 bar fall, which on the line would put the
    ceiling 2.69 K under the top, the ceiling still stands 0.81 K over it."""
    b = node_boil(REACT_NODE_SS_DES_C, SYN_P_DES_BARA, MCP, TAUS, OVERFLOW_DES_KMOLH, DT)
    assert b.frac == 0.0 and b.m_kgh == 0.0 and b.q_unpaid_kjh == 0.0
    assert b.t_nodes_c == tuple(REACT_NODE_SS_DES_C)
    assert b.t_bub_c - REACT_NODE_SS_DES_C[-1] == pytest.approx(3.5, abs=1e-9)
    b = node_boil(REACT_NODE_SS_DES_C, SYN_P_DES_BARA - 5.0, MCP, TAUS, OVERFLOW_DES_KMOLH, DT)
    assert b.t_bub_c == pytest.approx(183.8063, abs=1e-4) and b.frac == 0.0 and b.m_kgh == 0.0


def test_a_node_above_its_bubble_point_flashes_its_excess():
    """The top node 1e-4 K over the ceiling: held at 186.5 C; its excess, 0.797 GJ/h on the node's own
    thermal mass, flashes 0.335 % of the overflow's volatiles, 495 kg/h, in the overflow's
    proportions — the design overflow's volatiles pay 237.8 GJ/h in all."""
    t = list(REACT_NODE_SS_DES_C)
    t[3] = liquor_bubble_t_c(SYN_P_DES_BARA) + 1.0e-4
    b = node_boil(t, SYN_P_DES_BARA, MCP, TAUS, OVERFLOW_DES_KMOLH, DT)
    assert volatile_enthalpy_kjh(OVERFLOW_DES_KMOLH) == pytest.approx(237.7837e6, rel=1e-6)
    assert b.t_nodes_c[3] == liquor_bubble_t_c(SYN_P_DES_BARA) and b.t_nodes_c[:3] == tuple(t[:3])
    assert b.q_kjh == pytest.approx(MCP * TAUS[3] * 1.0e-4 / DT, rel=1e-6)
    assert b.frac == pytest.approx(0.0033511, abs=1e-7)
    assert b.m_kgh == pytest.approx(494.96, abs=0.01)
    for k in ("NH3", "CO2", "H2O"):
        assert b.flash_kmolh[k] == pytest.approx(b.frac * OVERFLOW_DES_KMOLH[k], rel=1e-12)
    assert b.q_unpaid_kjh == 0.0


def test_a_sudden_deficit_flashes_every_volatile_and_publishes_the_rest():
    """PT-329201 stepped 12 bar down in one tick: the ceiling falls 3.08 K under the top node (on
    the line before decision 301 a 5 bar step did this, to 180.3063 C), more than a tick of the
    overflow's volatiles can pay; all 147.7 t/h of them flash, the node is held on the ceiling and
    the unpaid excess is published."""
    b = node_boil(REACT_NODE_SS_DES_C, SYN_P_DES_BARA - 12.0, MCP, TAUS, OVERFLOW_DES_KMOLH, DT)
    assert b.t_bub_c == pytest.approx(179.9211, abs=1e-4)
    assert b.t_nodes_c[3] == b.t_bub_c and b.t_nodes_c[2] == REACT_NODE_SS_DES_C[2]
    assert b.frac == 1.0 and b.m_kgh == pytest.approx(147699.8, abs=0.1)
    assert b.q_unpaid_kjh > 0.0


def test_a_liquor_with_no_volatile_boils_nothing():
    b = node_boil(REACT_NODE_SS_DES_C, 100.0, MCP, TAUS, {"Urea": 1000.0, "Biuret": 5.0}, DT)
    assert b.frac == 0.0 and b.m_kgh == 0.0
    assert all(t == b.t_bub_c for t in b.t_nodes_c) and b.q_unpaid_kjh > 0.0
