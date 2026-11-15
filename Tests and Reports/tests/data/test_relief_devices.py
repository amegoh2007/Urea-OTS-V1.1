"""The urea plant's relief devices — `ureasim.data.relief_devices`.

Pins the catalogue as read from Uhde's specifications, and checks every entry against the rule
the sheets were written on — relieving pressure is the set pressure plus 10 % accumulation — so a
misread digit shows. The two set-pressure certificates cross-checked against the sheets are pinned
by name.
"""

from __future__ import annotations

import pytest

from ureasim.data import relief_devices as rd

DEVICES = list(rd.RELIEF_DEVICES.values())


def test_the_catalogue():
    """61 safety valves and 3 rupture discs across units 320 to 335."""
    assert len(DEVICES) == 64
    kinds = [d.kind for d in DEVICES]
    assert (kinds.count("safety valve"), kinds.count("rupture disc")) == (61, 3)
    assert {d.unit for d in DEVICES} == {"320", "321", "322", "323", "328", "329", "335"}


@pytest.mark.parametrize("device", [d for d in DEVICES if d.tag != "SV32261"],
                         ids=lambda d: d.tag)
def test_each_relieving_pressure_is_the_set_pressure_plus_ten_percent(device):
    assert device.relieving_bara == pytest.approx(1.1 * device.set_barg + device.atm_bara,
                                                  abs=0.015)


@pytest.mark.parametrize("device", DEVICES, ids=lambda d: d.tag)
def test_each_device_opens_between_its_operating_and_its_design_pressure(device):
    assert device.operating_bara < device.set_bara
    assert device.set_barg < device.design_bara


def test_the_hydrolysers_valve():
    """328C003 is protected by SV32852 on its MP steam inlet: set 23.0 bar g, 24.01 bar a,
    against the column's 16.8 bar a operating and 28.5 bar a design; sized for 16 t/h of MP steam
    or 83 t/h of liquid, blocked outlet. Sempell certified the setting at 23.0 bar g."""
    (sv,) = rd.relief_devices_on("328C003")
    assert (sv.tag, sv.line, sv.set_barg, sv.set_bara) == (
        "SV32852", "STMH2-329302-EG13E", 23.0, pytest.approx(24.01, abs=1e-12))
    assert (sv.operating_bara, sv.design_bara, sv.relieving_bara) == (16.80, 28.50, 26.30)
    assert [c.flow_kgh for c in sv.cases] == [16000.0, 83000.0]


def test_the_desorbers_and_the_lp_section():
    """328C002 carries SV32850 and SV32851 at 5.0 bar g; 323C003 SV32351 and SV32352 at 5.0;
    323D011 SV32357 at 5.0; the reactor SV32251 and SV32252 at 159.0; 328E021's four thermal
    valves 25.0 and 28.0."""
    assert [d.tag for d in rd.relief_devices_on("328C002")] == ["SV32850", "SV32851"]
    assert {d.set_barg for d in rd.relief_devices_on("328C002")} == {5.0}
    assert [d.tag for d in rd.relief_devices_on("323C003")] == ["SV32351", "SV32352"]
    assert rd.RELIEF_DEVICES["SV32357"].set_barg == 5.0
    assert {rd.RELIEF_DEVICES[t].set_barg for t in ("SV32251", "SV32252")} == {159.0}
    assert sorted(d.set_barg for d in DEVICES if d.protects.startswith("328E021")) == [
        25.0, 25.0, 28.0, 28.0]


def test_the_liquid_rated_valves_relieve_gas_on_the_series_coefficient_and_the_gas_blowdown():
    """Decision 130 (2026-10-16; A-16's option b took 0.917): the valves Sempell rated on liquid
    alone relieve gas on the full-lift gas coefficient Sempell prints for their orifices F, K and M
    in the same file (SV38107, SV30909, SV30203: 0.922); SV32351/52 keep their own 0.917. They
    reseat 10 % of set below on gas, not the 20 % of their liquid sizing."""
    assert rd.GAS_KD_FULL_LIFT == 0.922 and rd.RELIEF_SIZING["SV32351"].kd == 0.917
    for tag in ("SV32253", "SV32353", "SV32357"):
        sz, dev = rd.RELIEF_SIZING[tag], rd.RELIEF_DEVICES[tag]
        assert sz.service == "liquid" and sz.blowdown == 0.20
        assert rd.gas_reseat_bara(dev) == pytest.approx(dev.set_bara - 0.1 * dev.set_barg,
                                                        rel=1e-15)
    assert rd.gas_reseat_bara(rd.RELIEF_DEVICES["SV32253"]) == pytest.approx(5.513, abs=1e-12)


def test_sv32064_on_the_co2_line_session_47():
    """Sempell's orifice selection for SV32064 (UD-RL-G00-DZ-0001-001 page 72, read from the
    scan): orifice H, 615.75 mm2, lift-limited to 5.26 mm; CO2 gas at 140 C, M 43.370, k 1.510,
    Z 0.74; 74 444.40 kg/h at alpha_w 0.654 and 10 % overpressure, 67 000 kg/h required; set
    160 bar g, reseating 10 % of set below (handoff B-83)."""
    sz, dev = rd.RELIEF_SIZING["SV32064"], rd.RELIEF_DEVICES["SV32064"]
    assert (sz.orifice, sz.area_mm2, sz.service, sz.t_c, sz.mw, sz.k, sz.z) == (
        "H", 615.75, "gas", 140.0, 43.370, 1.510, 0.74)
    assert (sz.kd, sz.capacity_kgh, sz.overpressure, sz.blowdown) == (0.654, 74444.40, 0.10, 0.10)
    assert dev.set_barg == 160.0 and dev.cases[0].flow_kgh == 67000.0
    assert sz.reseat_bara(dev) == pytest.approx(145.013, abs=1e-12)
    assert sz.relieving_bara(dev) == pytest.approx(dev.relieving_bara, abs=0.015)


def test_unit_329s_drum_valves_session_37():
    """Sempell's orifice selections for the steam drums (UD-RL-G00-DZ-0001-001 pages 103, 104,
    114-117, read from the scans): SV32951 on 329D005, lift-limited orifice R, 138 889 kg/h at
    alpha_w 0.813, set 24.0 bar g; SV32952 on 329D009, orifice Q, 53 030 kg/h at 0.922, set 11.0;
    SV32978-81 on 322D001A/B, orifice T, 73 384 kg/h each at 0.922, set 6.0. Each sized on steam
    at its set pressure's saturation temperature, reseating 10 % of set below it."""
    for tag, orifice, cap, kd, t_c, set_barg in (
            ("SV32951", "R", 138889.0, 0.813, 224.0, 24.0),
            ("SV32952", "Q", 53030.3, 0.922, 188.0, 11.0),
            ("SV32978", "T", 73383.5, 0.922, 165.0, 6.0),
            ("SV32981", "T", 73383.5, 0.922, 165.0, 6.0)):
        sz, dev = rd.RELIEF_SIZING[tag], rd.RELIEF_DEVICES[tag]
        assert (sz.orifice, sz.capacity_kgh, sz.kd, sz.t_c, sz.service, sz.blowdown) == (
            orifice, cap, kd, t_c, "steam", 0.10)
        assert dev.set_barg == set_barg
    assert rd.RELIEF_SIZING["SV32951"].reseat_bara(rd.RELIEF_DEVICES["SV32951"]) ==         pytest.approx(22.613, abs=1e-12)
