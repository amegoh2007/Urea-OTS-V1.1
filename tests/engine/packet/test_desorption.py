"""Units 328 and 322C001 in the console packet — `ureasim.engine.packet.desorption`.

Pinned: TT-322015 reads TI-322015 where the P&ID draws it (decision 37), 328D003's PFD rounding
residuals are V1's sums over the flows the tick read and drew, FFIC-329401 is the port's ratio
station, FT-328401 reads 776 on its density, the unit-328 energy ledger V1 audited publishes
None, and XV-322915 follows I 22.1.
"""

from __future__ import annotations

from ureasim.data.unit_328d001 import D001_RHO_KGM3
from ureasim.data.unit_328d003 import D003_VOL_I_M3


def test_the_absorber_at_design(design):
    c1 = design.packet["ABSORB_328"]["C001"]
    res = design.results["322C001"]
    assert c1["TT_322015"] == round(res.t_ti_322015_c, 1) == 53.7      # the trace steam on 46 C
    assert c1["gcb_th"] == round(res.m_gas_kgh / 1000.0, 2) and c1["XV_322915"] is False
    assert c1["cpl_kgh"] == 1750.0 and c1["SV_32253_open"] is False
    assert c1["ntu_lower_nh3"] == round(res.beds.ntu["lo_NH3"], 2)
    assert c1["vent_nh3_kgh"] == round(res.m_vent_kgh * res.y_vent["NH3"], 1)


def test_328d003s_rounding_residuals_and_the_ledger(design):
    d3 = design.packet["ABSORB_328"]["D003"]
    read, res = design.scheduler.tears_read, design.results["328D003"]
    assert d3["compI_pfd_rounding_kgh"] == round(
        read.m_719_kgh + read.m_720_kgh + read.m_721_kgh + read.m_759_kgh - res.m_744_kgh, 3)
    assert d3["capacities_m3"]["I"] == D003_VOL_I_M3
    assert d3["LT_328507_open_loop"] == d3["LI_328I"] and d3["flow755_m3h"] == 31.32
    assert [d3[k] for k in ("Q328_in_kW", "Q328_out_kW", "Q328_react_kW", "Q328_resid_kW")] == [
        None] * 4
    assert d3["P002A"] == {"on": True, "mode": "AUTO"}


def test_the_desorbers_at_design(design):
    d = design.packet["DESORB_328"]
    assert d["C002"]["TT_328008"] == 117.0 and d["C003"]["TT_328011"] == 188.0
    ffic = d["C004"]["FFIC_329401"]
    station = design.plant.loops["328C004"][0].ffic_329401
    assert ffic == {"pv": round(station.pv, 4), "sp": round(station.sp, 4),
                    "op": round(station.op, 1), "mode": station.mode}
    d1 = d["D001"]
    assert d1["flow776_m3h"] == round(design.results["328D001"].m_776_kgh / D001_RHO_KGM3, 2)
    assert d1["TT_329007"] == 38.0 and d1["FIC_328404"]["m_kgh"] == 1675.0
