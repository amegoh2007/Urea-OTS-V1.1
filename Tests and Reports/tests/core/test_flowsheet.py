"""The flowsheet graph: does it order a plant correctly, and does it refuse a bad one?

`ureasim.core.flowsheet` has no V1 counterpart — V1's evaluation order is the order its
4,100 lines happen to be written in — so there is nothing to compare against. What there IS
to test is the property the module exists for: **a recycle without a declared tear must be
refused, not silently ordered.**

The fixture below is the real HP synthesis loop, which is cyclic by construction:

    322F001 -> 322E002 -> 322R001 -> 322E001 -> (bottoms, out of the loop)
                            |            |
                            +--> 322E003 +--> 322E002   (strip gas)
                                   |
                                   +--> 322F001         (carbamate recycle)
"""

from __future__ import annotations

import pytest

from ureasim.core.flowsheet import (
    Connection,
    CyclicFlowsheetError,
    Flowsheet,
    Tear,
    Unit,
)

SYNTHESIS_UNITS = [
    Unit("322F001", "HP carbamate ejector", "322"),
    Unit("322E002", "HP carbamate condenser", "322"),
    Unit("322R001", "Urea reactor", "322"),
    Unit("322E001", "HP CO2 stripper", "322"),
    Unit("322E003", "HP scrubber", "322"),
    Unit("323C003", "Rectifying column", "323"),
]

SYNTHESIS_CONNECTIONS = [
    Connection("ejector discharge", "322F001", "322E002"),
    Connection("condenser product", "322E002", "322R001"),
    Connection("reactor overflow", "322R001", "322E001"),
    Connection("reactor off-gas", "322R001", "322E003"),
    Connection("stripper top gas", "322E001", "322E002"),
    Connection("carbamate recycle", "322E003", "322F001"),
    Connection("stripper bottoms", "322E001", "323C003",
               route="322E001_TO_323C003"),
]


def _loop(with_tears: bool) -> Flowsheet:
    fs = Flowsheet()
    for u in SYNTHESIS_UNITS:
        fs.add_unit(u)
    for c in SYNTHESIS_CONNECTIONS:
        fs.connect(c)
    if with_tears:
        # The synthesis loop is cut at the scrubber overflow and at the stripper top gas:
        # both are the slowest-moving quantities in their cycle, so a one-tick delay on
        # them is the least visible. These correspond to V1's `s.p_syn_bara` and
        # `s.react_T_overflow` tears in docs/step_sim_dataflow.md section 2.
        fs.tear(Tear("scrub_overflow", "322E003", ("322F001",),
                     "carbamate recycle: the loop's largest inventory, slowest to move"))
        fs.tear(Tear("strip_top_gas", "322E001", ("322E002",),
                     "strip gas returns to the condenser inside the same loop"))
    return fs


def test_a_recycle_without_a_declared_tear_is_refused():
    """The defect this module exists to catch. Picking an order here would hide it."""
    with pytest.raises(CyclicFlowsheetError) as exc:
        _loop(with_tears=False).evaluation_order()
    message = str(exc.value)
    for tag in ("322F001", "322E002", "322R001", "322E001", "322E003"):
        assert tag in message


def test_declaring_the_tears_makes_the_loop_orderable():
    order = _loop(with_tears=True).evaluation_order()
    assert set(order) == {u.tag for u in SYNTHESIS_UNITS}
    # Every surviving connection runs forwards in the order.
    index = {tag: i for i, tag in enumerate(order)}
    torn = {("322E003", "322F001"), ("322E001", "322E002")}
    for c in SYNTHESIS_CONNECTIONS:
        if (c.source, c.destination) in torn:
            continue
        assert index[c.source] < index[c.destination], c.name


def test_the_order_is_deterministic():
    """A tick's floating-point result depends on the order its terms are summed in."""
    assert _loop(with_tears=True).evaluation_order() == _loop(with_tears=True).evaluation_order()


def test_a_straight_train_needs_no_tears():
    fs = Flowsheet()
    for tag in ("323C003", "323F004", "323F010", "323D002"):
        fs.add_unit(Unit(tag, tag, "323"))
    fs.connect(Connection("314", "323C003", "323F004", route="323C003_TO_323F004"))
    fs.connect(Connection("319", "323F004", "323F010", route="323F004_TO_323F010"))
    fs.connect(Connection("317", "323F010", "323D002", route="323F010_TO_323D002"))
    assert fs.evaluation_order() == ("323C003", "323F004", "323F010", "323D002")


def test_units_are_grouped_by_section():
    """The graph reports the units of each plant section."""
    fs = _loop(with_tears=True)
    assert {u.tag for u in fs.units_in_section("322")} == {
        "322F001", "322E002", "322R001", "322E001", "322E003"}
    assert {u.tag for u in fs.units_in_section("323")} == {"323C003"}


def test_a_recycle_is_still_a_connection_when_reading_the_flowsheet():
    """Only the ORDERING pretends a torn edge is absent; the topology does not."""
    fs = _loop(with_tears=True)
    assert "322E003" in fs.upstream_of("322F001")
    assert "322F001" in fs.downstream_of("322E003")


def test_a_duplicate_unit_is_a_defect_not_an_update():
    fs = Flowsheet()
    fs.add_unit(Unit("322R001", "Urea reactor", "322"))
    with pytest.raises(ValueError, match="already in the flowsheet"):
        fs.add_unit(Unit("322R001", "Urea reactor (again)", "322"))


def test_connecting_or_tearing_an_unknown_unit_is_refused():
    fs = Flowsheet()
    fs.add_unit(Unit("322R001", "Urea reactor", "322"))
    with pytest.raises(ValueError, match="unknown unit"):
        fs.connect(Connection("nowhere", "322R001", "999X999"))
    with pytest.raises(ValueError, match="unknown unit"):
        fs.tear(Tear("x", "999X999", ("322R001",), "typo"))


def test_every_route_a_connection_names_actually_exists():
    """A missing route would present as a missing dead time, which is silent."""
    from ureasim.data.process_routes import PROCESS_ROUTES
    for c in SYNTHESIS_CONNECTIONS:
        if c.route is not None:
            assert c.route in PROCESS_ROUTES, c.name
