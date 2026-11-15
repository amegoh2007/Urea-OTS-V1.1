"""V1 <-> V1.1 equivalence for the recycle tears — `ureasim.engine.state`.

What is being proved
--------------------
Handoff A-10: V1 reads its inter-section recycles as ``s.tlag.get(key, design_default)``,
written at the end of a tick for the next to read. The port holds them as named fields of a
frozen `TearState`, committed at the end of the tick. Two things are asserted:

  * the seeds are V1's boot defaults, `==`, the eight fields and the two tears the producing
    units hold themselves (328D001's 775, 328C004's 931);
  * the delay is V1's: 328C002, 328C003 and 328C004 coupled in V1's order, 748 and 750 read from
    the plant state's tears and committed at the end of each tick, the overheads' vapours from
    their producers' state at the top of the tick, against V1's three stages coupled through
    ``s.tlag`` — every published field, every state and every controller `==` for 3000 ticks,
    through a feed cut and an MP steam step.
"""

from __future__ import annotations

import pytest

from ureasim.data import desorption_train as t
from ureasim.data.unit_328d003 import M735_DES_KGH
from ureasim.engine.state import PlantState, TearState
from ureasim.units.desorption import first_desorber as fd
from ureasim.units.desorption import hydrolyser as hy
from ureasim.units.desorption import reflux_drum as rd
from ureasim.units.desorption import second_desorber as sd
from tests.equivalence import test_first_desorber_equivalence as c002_eq
from tests.equivalence import test_hydrolyser_equivalence as c003_eq
from tests.equivalence import test_second_desorber_equivalence as c004_eq
from tests.equivalence.v1_loader import lift, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

#: V1's namespaces for the desorption train, built as 328C004's own equivalence test builds them.
tank_v1 = c004_eq.tank_v1
e007_v1 = c004_eq.e007_v1
c002_v1 = c004_eq.c002_v1
c003_v1 = c004_eq.c003_v1
v1 = c004_eq.v1

DT = 0.1

#: Each tear's field and V1's boot default, ``main.py`` 8835-8845.
SEEDS = [
    ("m_702_kgh", "A323_C005_M702_DES"), ("m_756_kgh", "A323_C005_M756_DES"),
    ("m_708_kgh", "A323_C005_M708_DES"), ("m_748_kgh", "R328_C002_M748_DES"),
    ("m_750_kgh", "R328_C002_M750_DES"), ("m_718a_kgh", "R3232_M718A_DES"),
    ("m_718b_kgh", "R3232_M718B_DES"), ("m_739_kgh", "R328_C004_M739_DES"),
]


@pytest.fixture(scope="module")
def v1_seeds():
    return lift([name for _, name in SEEDS] + ["R328_C002_M775_DES", "R328_C004_M931_DES"])


@pytest.mark.parametrize("ours, theirs", SEEDS)
def test_each_tear_is_seeded_on_v1s_boot_default(v1_seeds, ours, theirs):
    assert getattr(TearState(), ours) == v1_seeds[theirs]


def test_the_two_tears_their_producers_hold_are_seeded_on_v1s_too(v1_seeds):
    """775 is 328D001's own top lag's input as well as 328C002's reflux; 931 is FFIC-329401's
    own PV: each producer reads it, so it is the producer's state."""
    assert rd.RefluxDrum().m_775_prev_kgh == v1_seeds["R328_C002_M775_DES"]
    assert sd.SecondDesorber(fv_329401=sd.V1_FV_329401).m_931_prev_kgh == v1_seeds["R328_C004_M931_DES"]


def test_the_desorbers_recycles_through_the_plant_state_are_v1s(v1):
    """V1's 328C002, 328C003 and 328C004 against the ported three in V1's order, the overheads
    748 and 750 carried by `PlantState.tears`: the delay is V1's, tick for tick."""
    s = c004_eq._v1_state(v1)
    state = PlantState()
    col2, lic2 = fd.FirstDesorber(), fd.lic_328503()
    col3, loops3 = hy.Hydrolyser(), hy.HydrolyserLoops()
    col4, loops4 = sd.SecondDesorber(fv_329401=sd.V1_FV_329401), sd.SecondDesorberLoops(fic_329401=sd.fic_329401(sd.V1_FV_329401))
    moved = set()
    for k in range(3000):
        m738 = t.C002_M738_DES_KGH * (0.85 if k >= 10 else 1.0)
        if k == 1500:
            s.FIC_329402["sp"] = loops3.fic_329402.loop.sp = 900.0
        # The tears as the tick reads them: 748 and 750 off the plant state, the vapours off
        # their producers' state at the top of the tick.
        tears = state.tears
        x2 = c002_eq._design(m738=m738, m748=tears.m_748_kgh, y748=dict(col3.y_748),
                             m750=tears.m_750_kgh, y750=dict(col4.y_750),
                             tc003=s.a328_c003_T, pc003=s.a328_c003_P)
        s.tlag["R328_775"], s.a328_d001_P = x2["m775"], x2["pd001"]
        a2 = c002_eq._v1_c002(v1, s, x2["m738"], x2["t738"], DT)
        a3 = c003_eq._v1_c003(v1, s, a2["743"], DT)
        a4 = c004_eq._v1_c004(v1, s, a3["747"], a3["749T"], DT)
        b2 = col2.step(lic2, x2["m738"], x2["t738"], tears.m_748_kgh, dict(col3.y_748),
                       tears.m_750_kgh, dict(col4.y_750), x2["m775"], col3.p_bara,
                       x2["pd001"], DT)
        b3 = col3.step(loops3, b2.m_743_kgh, b2.w, b2.t_c, b2.p_bara, col4.p_bara, DT)
        b4 = col4.step(loops4, b3.m_747_kgh, b3.t_749_c, b3.w, M735_DES_KGH, b2.p_bara,
                       c004_eq.DECIDED_T740_DES, DT)
        c002_eq._assert_tick(a2, b2, s, col2, lic2, f"328C002, tick {k}")
        c003_eq._assert_tick(a3, b3, s, col3, loops3, f"328C003, tick {k}")
        c004_eq._assert_tick(a4, b4, s, col4, loops4, f"328C004, tick {k}")
        # V1's tear writes, sections 25: what the next tick reads.
        assert (s.tlag["R328_748"], s.tlag["R328_750"]) == (b3.m_748_kgh, b4.m_750_kgh)
        state.end_tick({"m_748_kgh": b3.m_748_kgh, "m_750_kgh": b4.m_750_kgh,
                        "m_739_kgh": b4.m_739_kgh})
        moved.add(state.tears.m_750_kgh)
    assert state.clock.tick == 3000 and len(moved) > 100
