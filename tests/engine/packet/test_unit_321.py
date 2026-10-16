"""Unit 321 in the console packet — `ureasim.engine.packet.unit_321`.

Pinned on the design seed and with both machines stopped: the flat keys V1 publishes at the
packet's top level read the port's station, with V1's display relations (TT-321002's
stratification, PI-321003's affinity head, the discharge header's idle reading) and roundings.
"""

from __future__ import annotations

import pytest

from tests.engine.packet.conftest import run


def test_the_station_at_design(design):
    p, res = design.packet, design.results["321"]
    st = design.plant.units["321"]
    assert p["FI_321401"] == round(res.flow_total_th, 2) == 42.76
    assert p["TI_top1"] == 25.0 and p["TI_top2"] == round(25.0 - 0.8 * (1.0 - 0.65), 1) == 24.7
    assert p["LI_321501"] == 65.0 and p["LSL_321501"] is False
    assert p["PI_header"] == 7.3 and p["PI_disch"] == 164.0
    assert p["PI_321201"] == p["PI_321202"] == 12.3
    assert p["PDY_321203"] == round(res.subcooling_a_bar, 2) and p["PDY_321203_alarm"] is False
    assert p["pumpA"] == {"on": False, "speed": 0.0, "current": round(st.pump_a.current, 1),
                          "mode": st.pump_a.mode_letter}
    assert p["pumpB"]["on"] is True and p["XV_321901"] is True
    assert p["ratio"]["SP"] == p["ratio"]["PV"] == p["ratio"]["bal"] == pytest.approx(2.023)
    assert set(p["controllers"]) == {"SIC_321950", "SIC_321951"}
    assert p["controllers"]["SIC_321951"]["mode"] == "CAS"
    assert p["ext_override"] is False


def test_both_machines_stopped_read_the_idle_header():
    def stop(plant):
        plant.units["321"].pump_b.running = False
    p = run(setup=stop).packet
    assert p["PI_disch"] == 7.5 and p["pumpB"]["on"] is False
