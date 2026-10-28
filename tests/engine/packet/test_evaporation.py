"""Unit 324 in the console packet — `ureasim.engine.packet.evaporation`.

Pinned: PY-324201 / AY-324701 are V1's soft sensor (at the design temperature and vacuum they read
the live strength), LV-324501's selector publishes V1's route, selector stream and closure with
unit 335's UF85 dosed live on route A (decided 2026-10-16, decision 123) and interlocked off on route
B, when PIC-335201 passes its relief setting, and the vacuum train carries each condenser's balance
with its datasheet geometry.
"""

from __future__ import annotations

from ureasim.data.unit_324 import VACUUM_CONDENSERS
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


def test_the_melt_header_over_its_relief_setting_recycles():
    """PIC-335201 at 4.0 bar g, above LV-324501B's 3.8: the melt returns to 323D002 raw, the
    metering pumps stopped and FT-335405 at zero, FFIC-335406's ratio standing and its output at
    OUT L with no melt forward."""
    def back_up(plant):
        plant.boundary["PIC-335201.barg"] = 4.0
    e3 = run(5, back_up).packet["EVAP_324"]["E003"]
    assert (e3["route"], e3["selector_stream"], e3["UF85_interlocked"]) == ("B", "402G", True)
    assert e3["recycle_selected"] is True and e3["melt_fwd_th"] == 0.0 and e3["recyc_th"] > 0.0
    assert (e3["uf85_kgh"], e3["UF85_measured_ratio"], e3["UF85_flow_setpoint_th"]) == (0.0, 0.0,
                                                                                      0.0)
    assert e3["FFIC_335406"] == {"pv": 0.0, "sp": 0.0081, "op": 0.0, "mode": "AUTO"}
    assert e3["FIC_335405"] == {"pv": 0.0, "sp": 0.617, "op": 0.0, "mode": "CAS"}


def test_the_vacuum_train_carries_the_datasheets(design):
    vac = design.packet["EVAP_324"]["VAC"]
    for tag, rating in VACUUM_CONDENSERS.items():
        assert (vac[tag]["area_m2"], vac[tag]["tube_count"]) == (rating.area_m2,
                                                                 rating.tube_count)
    assert vac["vent_kgh"] == 31.0 and vac["condensate_th"] == 31.48
