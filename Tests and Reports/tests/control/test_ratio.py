"""Behaviour of the ratio station — `ureasim.control.ratio.RatioStation`.

The ratio controller's equivalence with V1 is proven in
`tests/equivalence/test_ratio_equivalence.py`; the station, which V1 does not have (handoff B-49,
decided 2026-09-30), is proven on 328C004 in
`tests/equivalence/test_second_desorber_control_equivalence.py`. This file pins what the station
DOES on its own: its output is the ratio set point times the base flow on the tick, clamped; it
tracks the achieved ratio while its slave is not in cascade; it hands the operator the output in
MAN; and it refuses a mode it does not have.
"""

from __future__ import annotations

import pytest

from ureasim.control.ratio import STATION_MODES, RatioStation


def _station(**over) -> RatioStation:
    base = dict(tag="FFIC-TEST", sp=0.2, op=6000.0, pv=0.2, sp_lo=0.0, sp_hi=0.5, op_lo=0.0,
                op_hi=12000.0, factor=1000.0)
    base.update(over)
    return RatioStation(**base)


def test_the_output_is_the_ratio_times_the_base_flow_on_the_tick():
    st = _station()
    assert st.step(0.19, 30.0, slave_in_cascade=True) == 0.2 * 30.0 * 1000.0
    assert st.step(0.19, 24.0, slave_in_cascade=True) == 0.2 * 24.0 * 1000.0
    assert (st.sp, st.pv) == (0.2, 0.19)


def test_a_ratio_set_point_move_reaches_the_output_on_the_tick_and_is_clamped():
    st = _station()
    st.set_sp(0.25)
    assert st.step(0.2, 30.0, slave_in_cascade=True) == 7500.0
    st.set_sp(0.9)
    assert st.sp == 0.5 and st.step(0.2, 30.0, slave_in_cascade=True) == 12000.0
    st.set_sp(-1.0)
    assert st.sp == 0.0 and st.step(0.2, 30.0, slave_in_cascade=True) == 0.0


def test_the_ratio_tracks_while_the_slave_is_not_in_cascade():
    """The station hands the slave, on its return, the flow it already has: nothing winds up."""
    st = _station()
    for measured in (0.12, 0.13, 0.9):
        st.step(measured, 30.0, slave_in_cascade=False)
        assert st.sp == min(measured, 0.5)
    st.step(0.13, 30.0, slave_in_cascade=False)
    assert st.step(0.13, 30.0, slave_in_cascade=True) == pytest.approx(0.13 * 30.0 * 1000.0)


def test_in_man_the_operator_sets_the_output():
    st = _station()
    st.set_mode("MAN")
    st.set_op(4000.0)
    assert st.step(0.3, 30.0, slave_in_cascade=True) == 4000.0
    assert st.step(0.3, 30.0, slave_in_cascade=False) == 4000.0
    assert (st.sp, st.pv) == (0.2, 0.3)
    st.set_op(20000.0)
    assert st.op == 12000.0
    assert st.as_packet() == {"mode": "MAN", "pv": 0.3, "sp": 0.2, "op": 12000.0}


def test_a_mode_the_station_does_not_have_is_refused():
    assert STATION_MODES == ("MAN", "AUTO")
    with pytest.raises(ValueError):
        _station(mode="CAS")
    with pytest.raises(ValueError):
        _station().set_mode("CAS")
