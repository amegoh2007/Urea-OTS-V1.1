"""Behaviour of the liquid-full line — `ureasim.core.transport.transport_process_properties`.

The FIFO itself is proven against V1's `consequence.py` in `tests/equivalence/test_core_equivalence.py`.
This file pins what the decided property transport adds (handoff B-21, 2026-09-30): the packet is a
pure function of what the liquor IS, so a flow change neither enters the FIFO nor unsettles a
settled line, while the dead time still follows the live flow.
"""

from __future__ import annotations

import pytest

from ureasim.core.transport import (
    PROPERTY_CARRIER_KGH,
    ConsequenceRoute,
    property_packet,
    transport_process_properties,
)

W = {"Urea": 0.6, "Biuret": 0.005, "NH3": 0.1, "CO2": 0.08, "H2O": 0.215, "HCHO": 0.0}
ROUTE = ConsequenceRoute("A", "B", design_carrier_kgh=100000.0, design_dead_time_s=16.0)


def test_a_property_packet_is_carried_on_the_unit_flow():
    pkt = property_packet(135.0, W, 2.5)
    assert pkt.mass_kgh == pytest.approx(PROPERTY_CARRIER_KGH, abs=1e-15)
    assert pkt.temperature_c == 135.0 and pkt.cp_kj_kgk == 2.5


def test_a_flow_change_leaves_a_settled_line_settled():
    """Four flows through one line: the arrived packet is the departed one on every tick, and the
    FIFO keeps a single sample."""
    store, pkt = {}, property_packet(135.0, W, 2.5)
    for k, flow in enumerate([100000.0] * 50 + [75000.0] * 50 + [0.0] * 50 + [120000.0] * 50):
        assert transport_process_properties(store, "line", pkt, ROUTE, flow, 0.1) == pkt, k
    assert len(store["line"]["buffer"]) == 1


def test_the_properties_wait_on_the_live_flow():
    """A temperature step at 1 s arrives one residence later on the flow of the moment: 16 s at
    design, 32 s at half flow."""
    for flow, residence in ((100000.0, 16.0), (50000.0, 32.0)):
        store, cold, hot = {}, property_packet(135.0, W, 2.5), property_packet(140.0, W, 2.5)
        arrived = []
        for k in range(1, 501):
            target = hot if k * 0.1 > 1.0 else cold
            arrived.append(transport_process_properties(store, "line", target, ROUTE, flow, 0.1))
        first = next(k for k, a in enumerate(arrived, start=1) if a == hot)
        assert first * 0.1 == pytest.approx(1.1 + residence, abs=0.1)
