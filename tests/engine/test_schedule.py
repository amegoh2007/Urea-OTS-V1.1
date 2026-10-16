"""The schedule's checks — `ureasim.engine.schedule` — and the plant's schedule against them.

A schedule is V1's section order as data (``project.md`` §3.6). These tests pin what the check
REFUSES — a unit twice, a result read before it is made, a later unit's state or a recycle tear
read with no declared tear, a declared tear nothing reads, a tear read with no writer — and that
the plant's own schedule passes: every unit once, every one-tick read declared, and V1's order a
topological order of the plant's flowsheet once its declared tears are cut.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from ureasim.core.flowsheet import CyclicFlowsheetError
from ureasim.engine import plant as P
from ureasim.engine.schedule import (
    Boundary,
    DeclaredTear,
    Operator,
    Result,
    Schedule,
    ScheduleError,
    State,
    Step,
    Tear,
    lookup,
)


def _run(plant, args, dt):
    return None


def _step(unit, **wiring):
    return Step(unit, unit, "000", 0, wiring, _run)


def test_a_legal_schedule_validates_and_cuts_its_tear():
    """A feeds B the same tick; B's state reaches A a tick late, declared: the graph is A -> B with
    the B -> A edge cut, and the order is the schedule's."""
    s = Schedule(steps=(_step("A", p=State("B", "p_bara"), u=Operator("HIC-1")),
                        _step("B", f=Result("A", "flow"), b=Boundary("feed"))),
                 tears=(DeclaredTear(State("B", "p_bara"), "A", "B steps later"),))
    fs = s.validate()
    assert fs.evaluation_order() == ("A", "B")
    assert [t.state_attribute for t in fs.tears] == ["B.p_bara"]


def test_a_unit_twice_is_refused():
    with pytest.raises(ScheduleError, match="twice"):
        Schedule(steps=(_step("A"), _step("A"))).validate()


def test_a_result_read_before_it_is_made_is_refused():
    with pytest.raises(ScheduleError, match="before it is made"):
        Schedule(steps=(_step("A", f=Result("B", "flow")), _step("B"))).validate()
    with pytest.raises(ScheduleError, match="not scheduled"):
        Schedule(steps=(_step("A", f=Result("C", "flow")),)).validate()


def test_reading_the_future_without_a_declared_tear_is_refused():
    """The draft's first proof: a later unit's state, read with no declared tear, stops the
    engine at start-up instead of surfacing as a late transient."""
    with pytest.raises(ScheduleError, match="no declared tear"):
        Schedule(steps=(_step("A", p=State("B", "p_bara")), _step("B"))).validate()


def test_a_unit_reading_its_own_state_through_the_wiring_is_refused():
    with pytest.raises(ScheduleError, match="own unit's state"):
        Schedule(steps=(_step("A", p=State("A", "p_bara")),)).validate()


def test_a_declared_tear_nothing_reads_is_refused():
    with pytest.raises(ScheduleError, match="nothing reads"):
        Schedule(steps=(_step("A"), _step("B")),
                 tears=(DeclaredTear(State("B", "p_bara"), "A", "stale"),)).validate()


def test_a_recycle_tear_needs_a_writer_a_declaration_and_a_reader():
    with pytest.raises(ScheduleError, match="has no writer"):
        Schedule(steps=(_step("A", m=Tear("m_702_kgh")),),
                 tears=(DeclaredTear(Tear("m_702_kgh"), "A", "x"),)).validate()
    with pytest.raises(ScheduleError, match="with no declared tear"):
        Schedule(steps=(_step("A", m=Tear("m_702_kgh")), _step("B")),
                 tear_writes={"m_702_kgh": Result("B", "m")}).validate()
    with pytest.raises(ScheduleError, match="not a recycle tear"):
        Schedule(steps=(_step("A"),), tear_writes={"m_999_kgh": Result("A", "m")}).validate()
    with pytest.raises(ScheduleError, match="never read"):
        Schedule(steps=(_step("A"),), tear_writes={"m_702_kgh": Result("A", "m")}).validate()
    s = Schedule(steps=(_step("A", m=Tear("m_702_kgh")), _step("B")),
                 tears=(DeclaredTear(Tear("m_702_kgh"), "A", "B's vent, a tick late"),),
                 tear_writes={"m_702_kgh": Result("B", "m")})
    assert s.validate().evaluation_order() == ("A", "B")


def test_a_lookup_walks_attributes_and_keys():
    class R:
        streams_kgh = {"708": 462.0}
    assert lookup(R(), "streams_kgh.708") == 462.0


# --------------------------------------------------------------------------------------
# The plant's schedule
# --------------------------------------------------------------------------------------

def test_the_plants_schedule_is_v1s_order_every_unit_once():
    """35 steps in V1's ``step_sim`` order: the synthesis loop's feeds and units (sections 1-3),
    the network (4), 322E003 and HV-322604 (5), the loop's displayed indicators (6), the liquor
    train (7-13), unit 328 (14-20), 322C001 (22), the two LP condensers (23, 24), unit 324 (26-31) with unit
    335's UF85 dosing (30),
    the steam users' meter, 323P001B's standby faceplate (33), the trips (34-36) and PT-329201
    (37)."""
    s = P.schedule()
    assert s.order == P.ORDER and len(set(s.order)) == len(s.order) == 35
    assert [st.v1_section for st in s.steps] == sorted(st.v1_section for st in s.steps)


def test_the_plants_order_is_a_topological_order_of_its_torn_flowsheet():
    """Every same-tick read runs forward; with the declared tears cut the flowsheet orders, and
    without them it does not — the plant's recycles are real."""
    s = P.schedule()
    fs = s.validate()
    order = fs.evaluation_order()
    assert set(order) == set(P.ORDER)
    index = {u: i for i, u in enumerate(s.order)}
    torn = {(t.written_by, r) for t in fs.tears for r in t.read_by}
    for c in fs.connections:
        if (c.source, c.destination) not in torn:
            assert index[c.source] < index[c.destination], c
    for t in fs.tears:
        assert all(index[t.written_by] >= index[r] or t.state_attribute.startswith("tear.")
                   for r in t.read_by), t
    uncut = type(fs)()
    for u in fs.units:
        uncut.add_unit(u)
    for c in fs.connections:
        uncut.connect(c)
    with pytest.raises(CyclicFlowsheetError):
        uncut.evaluation_order()


def test_every_one_tick_read_of_the_plant_is_declared_with_a_reason():
    """79 declared tears, each read: the V1 recycles and their kin, every downstream
    pressure a unit reads before its owner steps, the steam users' draws, the trips' output; the
    synthesis loop's 29 — PT-329201 to the six units that read it, the trips' latches to the feeds
    (21.2's to 320K002 too, decided 2026-10-16: its flag shuts XV-322902) and the network, 322E003's sump to 322F001 (its mushy zone too) and to 322R001's pulse, the
    backlog PT-329201 recondensed to the sump, the reactor's overflow to 322E001, the steam
    network's saturations to the two shells and its LP pressure to 322E002's tube leak (B-82),
    323P001's 308 and 322C001's pressure; 323E011's envelope overflow and its temperature to
    323C005 (A-20); and B-31's eight (decided 2026-10-16): 323E011's temperature to 323E003, unit
    324's four cold ends to 328D003, 328D001's, 328C003's and 328C004's temperatures to 328C002;
    and B-97's (decided 2026-10-16), 324F002's discharge temperature to 323C005."""
    s = P.schedule()
    assert len(s.tears) == 79 and all(t.reason for t in s.tears)
    assert set(s.tear_writes) == set(P.TEAR_WRITES)


def test_moving_a_unit_ahead_of_its_feed_is_refused():
    """323F004 stepped before 323C003, whose drain it takes the same tick: refused."""
    s = P.schedule()
    steps = list(s.steps)
    i, j = s.order.index("323C003"), s.order.index("323F004")
    steps[i], steps[j] = steps[j], steps[i]
    with pytest.raises(ScheduleError):
        replace(s, steps=tuple(steps)).validate()


def _readers(s, unit: str, field: str) -> set:
    """The steps that read ``unit``'s result field ``field`` this tick."""
    return {st.unit for st in s.steps for src in st.wiring.values()
            if isinstance(src, Result) and (src.unit, src.field) == (unit, field)}


def test_the_decided_routings_are_wired_and_the_sinks_read_by_no_unit():
    """Handoffs A-15 and A-16, decided 2026-10-03. The stripper's blow-through reaches 323C003,
    which passes what its valves leave to 323E003; a full 328D001 overflows into 323E011, the
    same tick; and the overflows of 328C003, 328C004 and 322C001 are boundary sinks — published,
    and read by no step."""
    s = P.schedule()
    # PT-329201 books it as the loop's loss; 323C003 receives it, 323E003 no longer does.
    assert _readers(s, "322E001", "sump.blowthrough_kgh") == {"323C003", "PT-329201"}
    assert _readers(s, "323C003", "blow_in_kgh") == _readers(s, "323C003", "overhead_frac") == {
        "323E003"}
    assert _readers(s, "328D001", "m_overflow_kgh") == {"323E011"}
    assert s.order.index("328D001") < s.order.index("323E011")
    for unit, (flow, temp) in P.boundary.BOUNDARY_SINKS.items():
        assert _readers(s, unit, flow) == set(), unit
