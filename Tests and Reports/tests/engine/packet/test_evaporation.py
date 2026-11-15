"""Unit 324 in the console packet — `ureasim.engine.packet.evaporation`.

Pinned: PY-324201 / AY-324701 are V1's soft sensor (at the design temperature and vacuum they read
the live strength), LV-324501's selector publishes V1's route, selector stream and closure with
unit 335's UF85 dosed live on route A (decided 2026-10-16, decision 123); the computed melt header
(decision 224) publishes PIC-335201's faceplate, FT-335401, the header valves online and HV-335602,
and with LIC-324501 above 50 % LV-324501B recycles beside the forward melt, which keeps its UF85,
the closure counting both and HV-335602's drain; and the vacuum train carries each condenser's
balance with its datasheet geometry.
"""

from __future__ import annotations

import pytest

from ureasim.data.unit_324 import P2_DES_KGH, VACUUM_CONDENSERS
from ureasim.data.unit_335 import LV_324501A_HEADER_OP_DES_PCT
from ureasim.engine.plant import build_plant
from ureasim.engine.scheduler import Scheduler
from tests.engine.packet.conftest import run


def test_the_stages_and_the_soft_sensors_at_design(design):
    e1, e3 = design.packet["EVAP_324"]["E001"], design.packet["EVAP_324"]["E003"]
    assert e1["PY_324201"] == e1["urea_pct"] == 94.3 and e1["PT_324201"] == 0.33
    assert e3["AY_324701"] == e3["urea_pct"] == 97.7 and e3["PT_324204"] == 0.131
    assert e1["HIC_329605"] == e1["HV_329605"] == round(design.plant.operator["HIC-329605"], 1)
    assert e1["motive_kgh"] == 390.0 and e1["TIC_324001"]["mode"] == "AUTO"


def test_the_selector_forwards_609_with_its_uf85(design):
    """Decision 123: the design drain's 75.94 t/h and 617.1 kg/h of UF85 at the PFD's ratio go
    forward as 609, 76.56 t/h at 138.62 C, the selector closing to the bit; FFIC-335406, its
    faceplate's ratio station (decision 160), in AUTO on the PFD's ratio, its output FIC-335405's
    0.617 t/h, FIC-335405 in CAS at 44.5 %."""
    e3 = design.packet["EVAP_324"]["E003"]
    assert (e3["route"], e3["selector_stream"], e3["UF85_interlocked"]) == ("A", "609", False)
    assert e3["route_mass_residual_kgh"] == 0.0 and e3["route_energy_residual_kw"] == 0.0
    assert set(e3["route_species_residual_kgh"].values()) == {0.0}
    assert e3["product_th"] == e3["melt_fwd_th"] == 76.56 and e3["recyc_th"] == 0.0
    assert (e3["selector_feed_th"], e3["selector_feed_T_C"]) == (76.555, 138.62)
    assert (e3["uf85_kgh"], e3["uf85_m3h"]) == (617.1, 0.47)
    assert [e3[k] for k in ("UF85_measured_ratio", "UF85_ratio_command",
                            "UF85_flow_setpoint_th")] == [0.00812599, 0.00812599, 0.617072]
    assert e3["FFIC_335406"] == {"pv": 0.0081, "sp": 0.0081, "op": 0.6171, "mode": "AUTO"}
    assert e3["FIC_335405"] == {"pv": 0.617, "sp": 0.617, "op": 44.5, "mode": "CAS"}


def test_the_melt_header_at_design(design):
    """Decision 224: PIC-335201 in CAS on LIC-324501's E1 at the header's 3.5 bar g, LV-324501A at
    the header's design stroke, 79.1 % (decision 237), and LV-324501B shut; FT-335401 the design drain at LV-324501's density; ten
    of twelve header valves online, HIC-335602 and HV-335602 shut, nothing drained to 335D004."""
    e3 = design.packet["EVAP_324"]["E003"]
    assert e3["PIC_335201"] == {"pv": 3.5, "sp": 3.5, "op": round(LV_324501A_HEADER_OP_DES_PCT, 1),
                                "mode": "CAS"}
    assert (e3["LV_324501A"], e3["LV_324501B"]) == (round(LV_324501A_HEADER_OP_DES_PCT, 1), 0.0)
    assert e3["FT_335401"] == round(P2_DES_KGH / 1221.0, 2)
    assert (e3["HEADERS_ONLINE"], e3["HIC_335602"], e3["HV_335602"]) == (10, 0.0, 0.0)
    assert e3["drain_335D004_th"] == 0.0 and e3["recycle_selected"] is False


def test_the_melt_header_above_e1s_ceiling_recycles_beside_the_forward_melt():
    """LIC-324501 in MAN at 80 %: E1 stands at its 3.8 bar g ceiling and LV-324501B opens to 60 %,
    returning raw melt to 323D002 while the forward melt keeps its UF85 (AC4 PC35.2, decision
    224); the selector closes on both, the residuals at the rounding, and the published leaves
    within their own rounding (0.0005 t/h on the feed, 0.005 on each flow)."""
    def man(plant):
        level = plant.loops["324E003"][0].level
        level.mode, level.op = "MAN", 80.0
    e3 = run(5, man).packet["EVAP_324"]["E003"]
    assert (e3["route"], e3["UF85_interlocked"], e3["recycle_selected"]) == ("AB", False, True)
    assert e3["PIC_335201"]["sp"] == 3.8 and e3["LV_324501B"] == 60.0
    assert e3["melt_fwd_th"] > 0.0 and e3["recyc_th"] > 0.0 and e3["uf85_kgh"] > 0.0
    assert abs(e3["route_mass_residual_kgh"]) < 1e-6 and abs(e3["route_energy_residual_kw"]) < 1e-6
    assert max(abs(v) for v in e3["route_species_residual_kgh"].values()) < 1e-6
    assert abs(e3["selector_feed_th"] - e3["melt_fwd_th"] - e3["recyc_th"]) <= 0.0105


def test_a_header_valve_brought_online_dips_the_header_before_lv_324501a_answers():
    """Decisions 236 and 237 on the whole plant, LIC-324501 live: the eleventh valve brought online at
    the seed drops the header to 3.2475 bar g on the tick (0.928 of 3.5; 3.388 before decision 236)
    and PIC-335201's output kicks 4.11 %; over the next ten seconds the header recovers one way only,
    to 3.406 bar g, LV-324501A following the output on its positioner and LIC-324501 easing E1 as the
    level falls."""
    sch, plant = build_plant()
    s = Scheduler(sch, plant)
    s.tick()
    before = s.results["324E003"].header
    plant.operator["GRANULATION-HEADERS"] = 11
    after = []
    for _ in range(100):
        s.tick()
        after.append(s.results["324E003"].header)
    assert before.p_barg == 3.5 and after[0].p_barg == pytest.approx(3.2475, abs=1e-4)
    assert after[0].lv_a_pct - before.lv_a_pct == pytest.approx(4.113, abs=1e-3)
    ps = [h.p_barg for h in after]
    assert all(b >= a for a, b in zip(ps, ps[1:])) and ps[-1] == pytest.approx(3.4065, abs=1e-4)
    assert after[-1].lv_a_position_pct < after[-1].lv_a_pct and after[-1].x_pct < 35.0


def test_hv_335602_drains_the_header_to_335d004_on_its_own_leaf():
    """Decision 225: HIC-335602 at 100 % opens HV-335602 in 3 s; five seconds on the header has
    fallen, its drain to 335D004 is published on its own leaf, outside the product, and the selector
    still closes, the drain counted, the published leaves within their own rounding."""
    def open_hv(plant):
        plant.operator["HIC-335602"] = 100.0
    e3 = run(50, open_hv).packet["EVAP_324"]["E003"]
    assert (e3["HIC_335602"], e3["HV_335602"]) == (100.0, 100.0)
    assert e3["drain_335D004_th"] > 0.0 and e3["PIC_335201"]["pv"] < 3.5
    assert abs(e3["route_mass_residual_kgh"]) < 1e-6 and abs(e3["route_energy_residual_kw"]) < 1e-6
    assert max(abs(v) for v in e3["route_species_residual_kgh"].values()) < 1e-6
    assert abs(e3["selector_feed_th"] - e3["melt_fwd_th"] - e3["recyc_th"]
               - e3["drain_335D004_th"]) <= 0.0155


def test_the_vacuum_train_carries_the_datasheets(design):
    vac = design.packet["EVAP_324"]["VAC"]
    for tag, rating in VACUUM_CONDENSERS.items():
        assert (vac[tag]["area_m2"], vac[tag]["tube_count"]) == (rating.area_m2,
                                                                 rating.tube_count)
    assert vac["vent_kgh"] == 31.0 and vac["condensate_th"] == 31.48
