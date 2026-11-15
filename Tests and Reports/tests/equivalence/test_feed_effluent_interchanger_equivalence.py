"""V1 <-> V1.1 equivalence for 328E007, the desorber heat exchanger.

What is being proved
--------------------
V1 writes the exchanger inline in `step_sim`, so its statements are TRANSCRIBED into `_v1_e007`
below, line for line, and declared as such (``main.py`` 8959-8963 and 8967). Its constants are
V1's own, lifted and executed. The exchanger is compared alone over a grid of inlets that crosses
every branch of the clamp, then coupled to 323C005 and 328D003 in V1's order — 735 and
compartment II's temperature same-tick, 739 and 328C004's temperature tears.

The decided divergence (2026-09-27, handoff B-40, decision 14) — where the clamp binds, the feed
takes only what 739 gave — is a switch in the transcription: ``decided=True`` carries the port's
lines, ``decided=False`` is V1 verbatim. The port is its switched transcription everywhere, and
V1 wherever the clamp does not bind; where it binds, V1's made heat and the port's closed
balance are both asserted.
"""

from __future__ import annotations

import itertools
import math
from types import SimpleNamespace

import pytest

from ureasim.core.flowsheet import Connection, CyclicFlowsheetError, Flowsheet, Tear, Unit
from ureasim.data import unit_323c005 as c
from ureasim.data import unit_328d003 as d
from ureasim.data import unit_328e007 as e
from ureasim.units.desorption import ammonia_water_tank as awt
from ureasim.units.desorption import atmospheric_absorber as aa
from ureasim.units.desorption import feed_effluent_interchanger as fei
from tests.equivalence import test_ammonia_water_tank_equivalence as tank_eq
from tests.equivalence import test_atmospheric_absorber_equivalence as stage1
from tests.equivalence.v1_loader import lift, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

E007_NAMES = ["R328_E007_EPS_T", "R328_E007_LOSS_DT", "R328_E007_TC_OUT", "R328_E007_TH_OUT",
              "R328_E007_LOSS", "R328_C004_T", "R328_CP"]

#: V1's namespace for stages 1 and 2, built as the tank's own equivalence test builds it.
tank_v1 = tank_eq.v1

DT = 0.1


@pytest.fixture(scope="module")
def v1(tank_v1):
    ns = dict(tank_v1)
    ns.update(lift(E007_NAMES, seed={"math": math}))
    return ns


def _v1_e007(v1, s, m_735, m739_prev, decided=True):
    """V1 `main.py` 8959-8963 and 8967, TRANSCRIBED line for line; with `decided`, the pinch cap
    stands where the port puts it."""
    g = v1
    T_738 = s.a328_d003_TII + g["R328_E007_EPS_T"] * (s.a328_c004_T - s.a328_d003_TII)
    T740_raw = s.a328_c004_T - (m_735 * (T_738 - s.a328_d003_TII)
                                + g["R328_E007_LOSS_DT"]) / max(m739_prev, 1e-6)
    T_740 = min(max(T740_raw, min(s.a328_d003_TII, s.a328_c004_T)),
                max(s.a328_d003_TII, s.a328_c004_T))
    if decided and T_740 != T740_raw and m_735 > 0.0:  # ---- the decided cap (the port's lines)
        share = m_735 * (T_738 - s.a328_d003_TII)
        given = m739_prev * (s.a328_c004_T - T_740) - g["R328_E007_LOSS_DT"]
        T_738 = s.a328_d003_TII + min(max(given, min(share, 0.0)), max(share, 0.0)) / m_735
    m_738 = m_735
    return {"738": m_738, "T738": T_738, "T740": T_740, "raw": T740_raw}


def _assert_same(a, b, s, m_739, label):
    assert (a["738"], a["T738"], m_739, a["T740"]) == (
        b.m_738_kgh, b.t_738_c, b.m_740_kgh, b.t_740_c), label
    lo, hi = sorted((s.a328_d003_TII, s.a328_c004_T))
    assert b.hot_outlet_clamped == (not lo <= a["raw"] <= hi), label


def _loss_paid(m_735, t_735, m_739, t_739, b):
    """What the hot side gave and the feed did not take [kg.K/h]: the shell loss paid. V1 books
    its design 16 484 whatever happens; negative, the exchanger made heat."""
    return m_739 * (t_739 - b.t_740_c) - m_735 * (b.t_738_c - t_735)


def _made_kw(v1, m_735, t_735, m_739, t_739, b):
    """Heat the exchanger makes [kW] against V1's booked shell loss."""
    return ((v1["R328_E007_LOSS_DT"] - _loss_paid(m_735, t_735, m_739, t_739, b))
            / 3600.0 * v1["R328_CP"])


# --------------------------------------------------------------------------------------
# The design basis
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("ours, theirs", [
    ("E007_T739_DES_C", "R328_C004_T"), ("E007_T738_DES_C", "R328_E007_TC_OUT"),
    ("E007_T740_DES_C", "R328_E007_TH_OUT"), ("E007_EPS_T", "R328_E007_EPS_T"),
    ("E007_LOSS_DT_KGKH", "R328_E007_LOSS_DT"), ("E007_LOSS_KW", "R328_E007_LOSS"),
])
def test_design_basis(v1, ours, theirs):
    assert getattr(e, ours) == v1[theirs]


def test_the_design_point_is_the_pfds(v1):
    s = SimpleNamespace(a328_d003_TII=d.D003_TII_C, a328_c004_T=e.E007_T739_DES_C)
    a = _v1_e007(v1, s, d.M735_DES_KGH, d.C004_M739_DES_KGH)
    b = fei.desorber_heat_exchanger(d.M735_DES_KGH, d.D003_TII_C, d.C004_M739_DES_KGH,
                                    e.E007_T739_DES_C)
    _assert_same(a, b, s, d.C004_M739_DES_KGH, "design")
    assert (b.t_738_c, b.t_740_c, b.hot_outlet_clamped) == (114.0, 89.0, False)


# --------------------------------------------------------------------------------------
# The exchanger alone, across every branch of the clamp
# --------------------------------------------------------------------------------------

GRID = list(itertools.product((56.0, 40.0, 75.0), (143.0, 120.0, 30.0),
                              (31114.0, 0.0, 62228.0), (33724.0, 10000.0, 0.0)))


def test_the_exchanger_on_a_grid_of_inlets(v1):
    """81 inlet sets: the hot side hotter and colder than the feed, each flow at design, zero
    and far off it. Every branch of the clamp is crossed. The port is its switched transcription
    on each; V1 verbatim wherever the clamp does not bind, or no feed flows; and where it binds on
    a feed, V1 makes heat and the port closes its balance on a loss between 0 and the design's."""
    branches = set()
    for t_735, t_739, m_735, m_739 in GRID:
        label = (t_735, t_739, m_735, m_739)
        s = SimpleNamespace(a328_d003_TII=t_735, a328_c004_T=t_739)
        b = fei.desorber_heat_exchanger(m_735, t_735, m_739, t_739)
        _assert_same(_v1_e007(v1, s, m_735, m_739), b, s, m_739, label)
        a = _v1_e007(v1, s, m_735, m_739, decided=False)
        lo, hi = sorted((t_735, t_739))
        branches.add("low" if a["raw"] < lo else "high" if a["raw"] > hi else "open")
        v1_made = _made_kw(v1, m_735, t_735, m_739, t_739, SimpleNamespace(
            t_738_c=a["T738"], t_740_c=a["T740"]))
        if not b.hot_outlet_clamped or m_735 == 0.0:
            _assert_same(a, b, s, m_739, label)
        else:
            assert a["T740"] == b.t_740_c and a["T738"] != b.t_738_c, label
            assert abs(v1_made) > 1.0, label
        paid = _loss_paid(m_735, t_735, m_739, t_739, b)
        if not b.hot_outlet_clamped:
            assert paid == pytest.approx(e.E007_LOSS_DT_KGKH, abs=1e-6), label
        elif m_735 > 0.0:
            assert -1e-6 <= paid <= e.E007_LOSS_DT_KGKH + 1e-6, label
    assert branches == {"low", "high", "open"}


# --------------------------------------------------------------------------------------
# The decided divergence: the pinched exchanger, both sides (handoff B-40)
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("m_735, m_739, made, t_738, paid", [
    (d.M735_DES_KGH, 0.0, 2023.44, 56.0, 0.0),                       # 328C004's bottoms stopped
    (2.0 * d.M735_DES_KGH, d.C004_M739_DES_KGH, 768.58, 102.8841, 16484.0),  # a full tank's 735
    (d.M735_DES_KGH, 0.5 * d.C004_M739_DES_KGH, 393.45, 102.6192, 16484.0),  # the bottoms halved
], ids=["739 stopped", "735 doubled", "739 halved"])
def test_the_pinched_exchanger_decided_divergence(v1, m_735, m_739, made, t_738, paid):
    """V1 heats the feed to 114 C whatever 739 can give: the hot outlet pins at the feed's
    56 C and the rest of the heat is made. The port's hot outlet pins alike, and the feed takes
    only what 739 gave, less the shell loss — with no 739, nothing, and no loss is paid."""
    s = SimpleNamespace(a328_d003_TII=d.D003_TII_C, a328_c004_T=e.E007_T739_DES_C)
    a = _v1_e007(v1, s, m_735, m_739, decided=False)
    assert (a["T738"], a["T740"]) == (114.0, d.D003_TII_C)
    assert _made_kw(v1, m_735, d.D003_TII_C, m_739, e.E007_T739_DES_C, SimpleNamespace(
        t_738_c=a["T738"], t_740_c=a["T740"])) == pytest.approx(made, abs=5e-3)
    b = fei.desorber_heat_exchanger(m_735, d.D003_TII_C, m_739, e.E007_T739_DES_C)
    _assert_same(_v1_e007(v1, s, m_735, m_739), b, s, m_739, "the switched transcription")
    assert b.hot_outlet_clamped and b.t_740_c == d.D003_TII_C
    assert b.t_738_c == pytest.approx(t_738, abs=5e-5)
    assert _loss_paid(m_735, d.D003_TII_C, m_739, e.E007_T739_DES_C, b) == pytest.approx(
        paid, abs=1e-6)


def test_the_clamp_binds_below_62_per_cent_of_739_and_above_162_per_cent_of_735():
    """The two thresholds at design temperatures: the hot flow that just gives the design feed
    its duty down to the pinch, and the draw that just takes all the design hot flow can give."""
    m739_min = (d.M735_DES_KGH * 58.0 + e.E007_LOSS_DT_KGKH) / 87.0
    m735_max = (d.C004_M739_DES_KGH * 87.0 - e.E007_LOSS_DT_KGKH) / 58.0
    assert (m739_min, m735_max) == pytest.approx((20932.14, 50301.79), abs=5e-3)
    for m_739, clamped in ((m739_min * 1.0001, False), (m739_min * 0.9999, True)):
        b = fei.desorber_heat_exchanger(d.M735_DES_KGH, d.D003_TII_C, m_739, e.E007_T739_DES_C)
        assert b.hot_outlet_clamped is clamped
    for m_735, clamped in ((m735_max * 0.9999, False), (m735_max * 1.0001, True)):
        b = fei.desorber_heat_exchanger(m_735, d.D003_TII_C, d.C004_M739_DES_KGH,
                                        e.E007_T739_DES_C)
        assert b.hot_outlet_clamped is clamped


# --------------------------------------------------------------------------------------
# Coupled: 323C005 -> 328D003 -> 328E007 as V1 steps them
# --------------------------------------------------------------------------------------

def test_the_flowsheet_order_is_v1s():
    """735 runs forward from the tank on the same tick; 739 comes back from 328C004 as a tear,
    with 328C004's temperature, and 750 from 328C004 to 328C002 likewise. Cut there, the order
    is V1's: the absorber, the tank, the exchanger, then the three columns."""
    fs = Flowsheet()
    for tag in ("323C005", "328D003", "328E007", "328C002", "328C003", "328C004"):
        fs.add_unit(Unit(tag, tag, tag[:3]))
    for name, src, dst in (("343", "323C005", "328D003"), ("735", "328D003", "328E007"),
                           ("738", "328E007", "328C002"), ("743", "328C002", "328C003"),
                           ("749", "328C003", "328C004"), ("739", "328C004", "328E007"),
                           ("750", "328C004", "328C002")):
        fs.connect(Connection(name, src, dst))
    with pytest.raises(CyclicFlowsheetError):
        fs.evaluation_order()
    fs.tear(Tear("R328_739", "328C004", ("328E007",),
                 "V1 reads 328C004's bottoms and temperature a tick late"))
    fs.tear(Tear("R328_750", "328C004", ("328C002",), "V1 reads the desorber-II vapour late"))
    assert fs.evaluation_order() == ("323C005", "328D003", "328E007", "328C002", "328C003",
                                     "328C004")


def test_the_exchanger_takes_the_tanks_735_on_the_same_tick(v1):
    """V1's stage 1, stage 2 and the exchanger in V1's order against the ported absorber, tank
    and exchanger. 323C005's solvent halved moves 343; 741 opened moves compartment II's
    temperature and 735; 328C004's temperature and bottoms, the tears, are stepped by hand."""
    s = tank_eq._v1_state(v1)
    absorber, tank, loops = aa.AtmosphericAbsorber(), awt.AmmoniaWaterTank(), awt.TankLoops()
    open_741 = tank_eq._man("FIC_328406", None, 50.0, t0=1000)
    seen = set()
    for k in range(3000):
        open_741(k, s, loops)
        m756 = c.C005_M756_DES_KGH * (0.5 if k >= 10 else 1.0)
        s.tlag["R322_756"] = m756
        m_739 = d.C004_M739_DES_KGH * (0.8 if k >= 2500 else 1.0)
        s.a328_c004_T = t_739 = e.E007_T739_DES_C - (5.0 if k >= 2000 else 0.0)
        x = tank_eq._design(m739=m_739)
        tank_eq._feed(s, x)
        a1 = stage1._v1_stage1(v1, s, DT)
        a2 = tank_eq._v1_stage2(v1, s, a1["343"], DT, decided=False)
        a7 = _v1_e007(v1, s, a2["735"], m_739, decided=False)
        b1 = absorber.step(c.C005_M702_DES_KGH, m756, c.C005_M708_DES_KGH,
                           dict(c.E002_INERT_DES_KMOLH), c.C005_T756_C, DT)
        b2 = tank_eq._port(tank, loops, {**x, "m343": b1.m_343_kgh, "m741": a2["741"]}, DT)
        b7 = fei.desorber_heat_exchanger(b2.m_735_kgh, b2.t_ii_c, m_739, t_739)
        tank_eq._assert_tick(a2, b2, s, tank, loops, f"stage 2, tick {k}")
        _assert_same(a7, b7, s, m_739, f"328E007, tick {k}")
        seen.add(b7.t_738_c)
    assert len(seen) > 1000 and not b7.hot_outlet_clamped
