"""Pressure relief — `ureasim.core.relief`.

The capacity law is V1's, ported verbatim and proved `==` in
`tests/equivalence/test_valve_equivalence.py`. This file pins what the decided relief adds
(handoff B-47): an orifice back-solved from a vendor's certified capacity returns that capacity
at the certified state, and the flow goes linear in the pressure and as sqrt(M / (Z T)); the
liquid flow goes as the square root of the head; the valve lifts at its set pressure, holds open
through its blowdown and reseats below it; and a tick never vents the vapour space below the
reseat pressure.
"""

from __future__ import annotations

import pytest

from ureasim.core.node import vessel_dpdt
from ureasim.core.relief import (
    GasReliefValve,
    SafetyValve,
    liquid_relief_kgh,
    psv_api520_choked_kgh,
    psv_area_from_rated_m2,
    reseat_vent_kgh,
)
from ureasim.data.relief_devices import GAS_KD_ASSUMED, RELIEF_DEVICES, RELIEF_SIZING


def _sv32351():
    """SV32351/52's orifice back-solved from 72 273.6 kg/h of M 25.07, k 1.010, Z 1.00 gas at
    125 C and 6.51 bar a."""
    sz = RELIEF_SIZING["SV32351"]
    p_rel = sz.relieving_bara(RELIEF_DEVICES["SV32351"])
    t_rel = sz.t_c + 273.15
    return sz, p_rel, t_rel, psv_area_from_rated_m2(sz.capacity_kgh, p_rel, t_rel, sz.mw, k=sz.k,
                                                    z=sz.z)


def test_the_back_solved_orifice_returns_the_certified_capacity_at_the_certified_state():
    sz, p_rel, t_rel, area = _sv32351()
    assert psv_api520_choked_kgh(area, p_rel, t_rel, sz.mw, k=sz.k, z=sz.z) \
        == pytest.approx(72273.6, rel=1e-12)


def test_the_gas_flow_is_linear_in_the_pressure_and_goes_as_root_m_over_z_t():
    """Critical flow: half the pressure, half the flow; a vapour four times as heavy passes
    twice the mass; four times as hot, half."""
    sz, p_rel, t_rel, area = _sv32351()
    base = psv_api520_choked_kgh(area, p_rel, t_rel, sz.mw, k=sz.k)
    assert psv_api520_choked_kgh(area, p_rel / 2.0, t_rel, sz.mw, k=sz.k) \
        == pytest.approx(base / 2.0, rel=1e-12)
    assert psv_api520_choked_kgh(area, p_rel, t_rel, 4.0 * sz.mw, k=sz.k) \
        == pytest.approx(2.0 * base, rel=1e-12)
    assert psv_api520_choked_kgh(area, p_rel, 4.0 * t_rel, sz.mw, k=sz.k) \
        == pytest.approx(base / 2.0, rel=1e-12)


def test_the_liquid_law_goes_as_the_square_root_of_the_head():
    """SV32357: 18 340.5 kg/h of 976 kg/m3 liquid at 6.51 bar a against 1.01; a quarter of the
    head passes half."""
    sz = RELIEF_SIZING["SV32357"]
    dev = RELIEF_DEVICES["SV32357"]
    p_rel = sz.relieving_bara(dev)
    full = liquid_relief_kgh(p_rel, dev.back_bara, 976.0, sz.capacity_kgh, p_rel, 976.0)
    assert full == pytest.approx(18340.5, rel=1e-12)
    quarter = dev.back_bara + (p_rel - dev.back_bara) / 4.0
    assert liquid_relief_kgh(quarter, dev.back_bara, 976.0, sz.capacity_kgh, p_rel, 976.0) \
        == pytest.approx(full / 2.0, rel=1e-12)
    assert liquid_relief_kgh(0.5, dev.back_bara, 976.0, sz.capacity_kgh, p_rel, 976.0) == 0.0


@pytest.mark.parametrize("tag, blowdown", [("SV32852", 0.10), ("SV32850", 0.10),
                                           ("SV32351", 0.10), ("SV32251", 0.10),
                                           ("SV32353", 0.20), ("SV32357", 0.20),
                                           ("SV32253", 0.20), ("SV32355", 0.20)])
def test_gas_valves_reseat_ten_percent_and_liquid_valves_twenty_percent_below_set(tag, blowdown):
    """Sempell's blowdowns: 10 % of the set pressure on every gas and steam valve, 20 % on every
    liquid one."""
    sz, dev = RELIEF_SIZING[tag], RELIEF_DEVICES[tag]
    assert sz.blowdown == blowdown
    assert (sz.service == "liquid") == (blowdown == 0.20)
    assert dev.set_bara - sz.reseat_bara(dev) == pytest.approx(blowdown * dev.set_barg, rel=1e-12)
    assert sz.relieving_bara(dev) == pytest.approx(dev.relieving_bara, abs=0.015)


def test_the_valve_lifts_at_set_holds_through_its_blowdown_and_reseats():
    """The pop action: shut below set; at set it lifts, and it stays lifted on the way down until
    the reseat pressure, where it shuts; the band between is hysteresis, not a modulation."""
    sv = SafetyValve("SV", set_bara=24.01, reseat_bara=21.71)
    trace = [sv.step(p) for p in (20.0, 24.0, 24.01, 23.0, 21.72, 21.71, 22.0, 24.0, 24.02)]
    assert trace == [False, False, True, True, True, False, False, False, True]


def test_a_tick_never_vents_below_the_reseat_pressure():
    """The cap is the moles above the reseat pressure: venting it lands the vapour space on the
    reseat pressure to the last bits."""
    p_free, p_reseat, t_k, v_v, mw, dt = 24.3, 21.71, 473.15, 0.8, 20.0, 0.1
    w = reseat_vent_kgh(p_free, p_reseat, t_k, v_v, mw, dt)
    assert p_free + vessel_dpdt(p_free, t_k, v_v, mw, 0.0, w / mw) * dt \
        == pytest.approx(p_reseat, abs=1e-12)
    assert reseat_vent_kgh(21.0, p_reseat, t_k, v_v, mw, dt) == 0.0


def test_a_relief_valve_vents_nothing_shut_and_its_count_of_capacity_lifted():
    """Below set nothing; at set the valves' capacity on the node's vapour, until the cap
    binds."""
    area = psv_area_from_rated_m2(25000.0, 6.51, 432.15, 18.0, k=1.31, z=0.99)
    rv = GasReliefValve(valve=SafetyValve("SV", 6.01, 5.51), area_m2=area, k=1.31, count=2)
    assert rv.vent_kgh(6.0, 6.2, 432.15, 18.0, 50.0, 0.1) == 0.0
    w = rv.vent_kgh(6.02, 6.03, 432.15, 18.0, 50.0, 0.1)
    assert w == pytest.approx(2 * 25000.0 * 6.02 / 6.51 * 0.99 ** 0.5, rel=1e-12)
    assert rv.valve.lifted
    tiny = rv.vent_kgh(6.02, 5.52, 432.15, 18.0, 0.01, 0.1)
    assert tiny == pytest.approx(reseat_vent_kgh(5.52, 5.51, 432.15, 0.01, 18.0, 0.1), rel=1e-12)


def test_a_liquid_rated_valve_relieves_gas_on_its_orifice_at_the_assumed_coefficient():
    """A-16, decided 2026-10-01. SV32357's orifice F, 240.53 mm2, at the series' gas coefficient
    0.917: at its 6.61 bar a relieving pressure, 881.6 kg/h of the 323E011 node's M 17.4 vapour at
    57 C — the law's output, linear in Kd, so 0.917 / 0.975 of what the law's default gives."""
    sz = RELIEF_SIZING["SV32357"]
    rv = GasReliefValve(valve=SafetyValve("SV32357", 6.01, 5.51), area_m2=sz.area_mm2 * 1.0e-6,
                        kd=GAS_KD_ASSUMED)
    w = rv.vent_kgh(6.61, 99.0, 330.15, 17.395, 1.0e3, 0.1)
    assert w == psv_api520_choked_kgh(240.53e-6, 6.61, 330.15, 17.395, kd=0.917)
    assert w == pytest.approx(881.6, abs=0.1)
    assert w / psv_api520_choked_kgh(240.53e-6, 6.61, 330.15, 17.395) == pytest.approx(
        0.917 / 0.975, rel=1e-12)
