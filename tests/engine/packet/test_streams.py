"""The stream registry in the console packet — `ureasim.engine.packet.streams`.

Pinned: V1's 55 streams in V1's order, each a record of V1's shape; the synthesis loop's records
on their units' live vectors, a numbered stream on its PFD row at the live flow, a vacuum vent on
its condenser's live composition, and 797 at V1's design flow.
"""

from __future__ import annotations

import pytest

from ureasim.core.stream import MW_COMP

#: V1's registry, in V1's order (``main.py`` 10183-10331).
V1_ORDER = (
    ["NH3_FEED", "PUMP_SUCT", "HP_DISCH", "CARB_RECYCLE", "EJ_DISCH", "CO2_FEED", "STRIP_TOP",
     "STRIP_BOT", "HPCC_PROD", "HPCC_STEAM", "HPCC_COND", "REACT_OVERFLOW", "REACT_OFFGAS",
     "SCRUB_OFFGAS", "SCRUB_OFFGAS_LP", "CCW_SUPPLY", "CCW_RETURN"]
    + ["S0" + n for n in ("204", "341", "343", "702", "703", "705", "706", "708", "709", "712",
                          "714", "715", "717", "719", "720", "721", "722", "744", "755", "756",
                          "759", "783", "784", "797", "924", "927", "929", "954")]
    + ["S" + n for n in ("1014", "1015", "1016", "1017", "1018", "1019", "1020", "1021",
                         "1001", "1051")])

RECORD_KEYS = ["name", "src", "dst", "phase", "T_C", "P_bara", "mass_kgh", "mass_th",
               "mol_kmolh", "MW", "rho", "vol_m3h", "enthalpy_kJkg", "enthalpy_flow_kW",
               "enthalpy_basis", "component_kmolh", "component_kgh", "mol_pct", "mass_pct"]


def test_v1s_streams_in_v1s_order(design):
    streams = design.packet["STREAMS"]
    assert list(streams) == V1_ORDER and len(V1_ORDER) == 55
    assert all(list(rec) == RECORD_KEYS for rec in streams.values())


def test_the_records_read_the_plant(design):
    streams, res = design.packet["STREAMS"], design.results
    off = res["322E003"].scrubber.offgas_kmolh
    assert streams["SCRUB_OFFGAS"]["mass_kgh"] == round(
        sum(off.get(k, 0.0) * MW_COMP[k] for k in MW_COMP), 1)
    assert streams["S0341"]["mass_kgh"] == round(res["323C005"].m_341_kgh, 1)
    vent = res["324E002-E007"].nodes["324E007"]
    assert streams["S0722"]["T_C"] == round(vent.t_vent_c, 1)
    assert streams["S0797"]["mass_kgh"] == 1758.0
    assert streams["S0954"]["mass_kgh"] == 1750.0 and streams["S1001"]["T_C"] == 30.0
    assert streams["HP_DISCH"]["P_bara"] == 165.0
    assert streams["HPCC_PROD"]["P_bara"] == 144.2
    assert streams["S0755"]["vol_m3h"] == pytest.approx(31.32, abs=0.01)
