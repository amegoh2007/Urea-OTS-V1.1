"""The synthesis loop in the console packet — `ureasim.engine.packet.synthesis`.

Pinned: the lagged indications are the ``322-DISPLAY`` step's, the stripper's steam is the port's
PFD-basis draw with the licensor's duty, the scrubber's off-gas and overflow are the stream
registry's, the overhead's pressure-building push is zero at design, a lost tempered-water pump
shows on LT-329501 as V1's swell over the true level, and PT-329201 reads the live loop pressure.
"""

from __future__ import annotations

import pytest

from ureasim.data.unit_322e001 import DUTY_DES_KW
from ureasim.engine.packet.synthesis import pressure_building_overhead
from ureasim.units.synthesis.stripper import TOP_DES_KMOLH
from tests.engine.packet.conftest import run


def test_the_lagged_indications_are_the_display_steps(design):
    p, lag = design.packet, design.results["322-DISPLAY"]
    assert p["EJ_322F001"]["TT_322012"] == p["HPCC_322E002"]["TT_322012"] == round(
        lag.tt_322012_c, 1)
    assert p["HPCC_322E002"]["P_bara"] == p["SCRUB_322E003"]["ccw"]["PI_322E002"] == 144.2
    assert p["REACT_322R001"]["AT_322701"] == round(lag.at_322701, 3) == 3.0
    assert p["STRIP_322E001"]["TT_323001"] == 119.0 and p["STRIP_322E001"]["TT_322004"] == 172.0


def test_the_feeds_and_the_stripper_at_design(design):
    p = design.packet
    ej = p["EJ_322F001"]
    assert sum(ej["comp_pct"].values()) == pytest.approx(100.0, abs=0.01)
    assert ej["HIC_322602"] == 74.0 and ej["XV_322903"] is True
    co2 = p["CO2_FEED"]
    assert co2["Load"] == 100.0 and co2["XV_322902"] is True and co2["PIC_mode"] == "AUTO"
    steam = p["STRIP_322E001"]["steam"]
    # 39 399 kW after the tenth tick: the reactor's top node stands on its bubble point at the seed
    # and flashes some 30 kg/h of its liquor (handoff B-92), which the stripper's feed carries.
    assert DUTY_DES_KW == 39400.0 and steam["duty_kW"] == pytest.approx(DUTY_DES_KW, abs=1.0)
    assert steam["kgh"] == round(design.results["322E001"].strip_kgh, 0)
    assert p["STRIP_322E001"]["LIC_322501"]["mode"] in ("AUTO", "MAN", "CAS")


def test_the_scrubber_reads_the_stream_registry(design):
    p = design.packet
    sc, off = p["SCRUB_322E003"], p["STREAMS"]["SCRUB_OFFGAS"]
    assert (sc["off_th"], sc["off_MW"]) == (off["mass_th"], off["MW"])
    assert sc["ov_th"] == p["STREAMS"]["CARB_RECYCLE"]["mass_th"]
    assert sc["vent_frac"] == 1.0 and sc["P_overflow"] == 140.7
    ccw = sc["ccw"]
    assert (ccw["P329P006_in"], ccw["P329P006_out"]) == (8.0, 9.0)
    assert ccw["TDY_329125"] == 15.0 and ccw["E004_duty_kW"] == ccw["Q_ccw_kW"]
    assert ccw["P329P006A"] == {"on": True} and ccw["FIC_329409"]["mode"] == "AUTO"
    assert (sc["LT_329501_swell"], sc["LT_329501_noise"]) == (0.0, 0.0)


def test_the_overhead_builds_no_pressure_at_design():
    co2_free, push = pressure_building_overhead(TOP_DES_KMOLH, 1.0)
    assert co2_free == pytest.approx(98.6, abs=0.05) and push == 0.0


def test_a_lost_tempered_water_pump_swells_lt_329501():
    """329P006A stopped for a minute: the shell condenses less, and LT-329501 reads its swell
    above the true level, V1's operator trap."""
    def stop(plant):
        plant.loops["322E003"][0].p329p006a = False
    sc = run(600, stop).packet["SCRUB_322E003"]
    assert sc["ccw"]["cool_frac"] < 1.0 and sc["LT_329501_swell"] > 0.0
    assert sc["LT_329501"] > sc["LT_329501_true"]


def test_pt_329201_and_the_off_gas_line_read_the_live_loop_pressure():
    """V1 `main.py` 8105-8106: the scrubber's overflow and off-gas lines ride PT-329201, the live
    loop pressure the tick read, where `scrubber_322e003` returns their design pins. The console's
    PT-329201 (``EJ_322F001.PI_329201``) and 322E003's ``P_overflow`` / ``P_offgas`` follow it;
    the port published the pins until session 46, so its PT-329201 read 140.7 bar a whatever the
    loop did."""
    def up(plant):
        plant.units["PT-329201"].p_syn_bara = 146.0
    r = run(1, up)
    sc = r.results["322E003"].scrubber
    assert (sc.p_overflow_bara, sc.p_offgas_bara) == (146.0, 146.0)
    assert r.packet["EJ_322F001"]["PI_329201"] == 146.0
    assert r.packet["SCRUB_322E003"]["P_overflow"] == r.packet["SCRUB_322E003"]["P_offgas"] == 146.0
