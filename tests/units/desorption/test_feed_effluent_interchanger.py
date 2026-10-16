"""Behaviour of 328E007, the desorber heat exchanger —
`ureasim.units.desorption.feed_effluent_interchanger`.

Equivalence with V1 is proven in `tests/equivalence/test_feed_effluent_interchanger_equivalence.py`.
This file pins what the exchanger DOES: the PFD's 114 C and 89 C at design; the feed taking a
fixed two-thirds of the approach; the balance closing on the design shell loss while the hot side
can pay for it; and, where it cannot, the exchanger pinching and the feed taking only what 739
gave (decided 2026-09-27, handoff B-40).
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_328d003 as d
from ureasim.data import unit_328e007 as e
from ureasim.units.desorption.feed_effluent_interchanger import (
    desorber_heat_exchanger,
    interchanger_outlets,
)

CP = 4.0  # V1's R328_CP, the desorption train's aqueous cp [kJ/kg.K]
L = e.E007_LOSS_DT_KGKH


def _design(**over):
    x = {"m_735_kgh": d.M735_DES_KGH, "t_735_c": d.D003_TII_C, "m_739_kgh": d.C004_M739_DES_KGH,
         "t_739_c": e.E007_T739_DES_C}
    x.update(over)
    return desorber_heat_exchanger(**x), x


def _loss_paid(b, x):
    """What the hot side gave and the feed did not take [kg.K/h]: the shell loss paid."""
    return (x["m_739_kgh"] * (x["t_739_c"] - b.t_740_c)
            - x["m_735_kgh"] * (b.t_738_c - x["t_735_c"]))


def test_the_design_point_is_the_pfds():
    b, x = _design()
    assert (b.m_738_kgh, b.t_738_c, b.m_740_kgh, b.t_740_c) == (31114.0, 114.0, 33724.0, 89.0)
    assert not b.hot_outlet_clamped and _loss_paid(b, x) == L
    assert e.E007_EPS_T == 58.0 / 87.0 and L == 16484.0
    # The duty the feed takes, and the shell loss the design state leaves: 2005.1 and 18.3 kW.
    assert (31114.0 * 58.0 * CP / 3600.0, L * CP / 3600.0) == pytest.approx(
        (2005.1244, 18.3156), abs=1e-4)


@pytest.mark.parametrize("t_739", [143.0, 138.0, 120.0, 100.0])
def test_the_feed_takes_two_thirds_of_the_approach(t_739):
    """A cooler 328C004 bottoms preheats the feed less, by exactly eps_T of the lost approach."""
    b, x = _design(t_739_c=t_739)
    assert b.t_738_c == pytest.approx(56.0 + 58.0 / 87.0 * (t_739 - 56.0), rel=1e-15)
    assert not b.hot_outlet_clamped
    assert _loss_paid(b, x) == pytest.approx(L, abs=1e-6)


@pytest.mark.parametrize("m_735, m_739", [(20000.0, 33724.0), (45000.0, 33724.0),
                                          (31114.0, 25000.0), (0.0, 33724.0)])
def test_the_balance_closes_while_739_can_pay(m_735, m_739):
    b, x = _design(m_735_kgh=m_735, m_739_kgh=m_739)
    assert not b.hot_outlet_clamped
    assert _loss_paid(b, x) == pytest.approx(L, abs=1e-6)
    assert 56.0 <= b.t_740_c <= 143.0


def test_no_feed_leaves_the_hot_side_only_its_shell_loss():
    b, _ = _design(m_735_kgh=0.0)
    assert b.t_740_c == pytest.approx(143.0 - 16484.0 / 33724.0, rel=1e-15)


@pytest.mark.parametrize("over, t_738, paid", [({"m_739_kgh": 0.0}, 56.0, 0.0),
                                               ({"m_739_kgh": 0.5 * 33724.0}, 102.6192068, L),
                                               ({"m_735_kgh": 2.0 * 31114.0}, 102.8841036, L)],
                         ids=["739 stopped", "739 halved", "735 doubled"])
def test_the_pinched_exchanger_makes_no_heat(over, t_738, paid):
    """739 cannot give the feed its two-thirds: the hot outlet stands at the feed's 56 C and the
    feed takes what 739 gave, less the shell loss. With 328C004's bottoms stopped the feed passes
    through unheated and no loss is paid. Where V1 made 2023, 393 and 769 kW, nothing is made
    (the decided B-40)."""
    b, x = _design(**over)
    assert b.hot_outlet_clamped and b.t_740_c == 56.0
    assert b.t_738_c == pytest.approx(t_738, abs=1e-7)
    assert _loss_paid(b, x) == pytest.approx(paid, abs=1e-6)


def test_a_trickle_of_feed_is_not_charged_the_shell_loss():
    """100 kg/h of feed and no 739: the design loss would cool it 165 K; the feed passes through."""
    b, x = _design(m_735_kgh=100.0, m_739_kgh=0.0)
    assert b.hot_outlet_clamped and (b.t_738_c, _loss_paid(b, x)) == (56.0, 0.0)


def test_the_hot_flow_floor_only_guards_the_division():
    """V1's 1e-6 kg/h floor: a trickle of 0.5 kg/h is divided by as it is; none at all clamps."""
    assert interchanger_outlets(56.0, 143.0, 0.0, 0.5, e.E007_EPS_T, 1.0,
                                e.E007_HOT_FLOW_FLOOR_KGH)[1:] == (141.0, False)
    assert interchanger_outlets(56.0, 143.0, 0.0, 0.0, e.E007_EPS_T, 1.0,
                                e.E007_HOT_FLOW_FLOOR_KGH)[1:] == (56.0, True)


def test_a_cold_hot_side_cools_the_feed():
    """328C004 colder than the feed (a start-up): the feed is cooled toward it. On a large hot
    flow by two-thirds of the approach; on a small one the hot side is warmed to the feed's
    temperature and the feed gives only that, and the shell loss; on a trickle of feed the loss
    would cool the hot side below its inlet, so it stands there and the feed keeps V1's share."""
    t_738, t_740, clamped = interchanger_outlets(75.0, 30.0, 31114.0, 33724.0, e.E007_EPS_T,
                                                 L, 1e-6)
    assert t_738 == pytest.approx(75.0 - 58.0 / 87.0 * 45.0, rel=1e-15) and not clamped
    t_738, t_740, clamped = interchanger_outlets(75.0, 30.0, 31114.0, 10000.0, e.E007_EPS_T,
                                                 L, 1e-6)
    assert clamped and t_740 == 75.0
    assert t_738 == pytest.approx(75.0 - (10000.0 * 45.0 + 16484.0) / 31114.0, rel=1e-15)
    t_738, t_740, clamped = interchanger_outlets(75.0, 30.0, 100.0, 33724.0, e.E007_EPS_T,
                                                 L, 1e-6)
    assert clamped and t_740 == 30.0
    assert t_738 == pytest.approx(75.0 - 58.0 / 87.0 * 45.0, rel=1e-13)
