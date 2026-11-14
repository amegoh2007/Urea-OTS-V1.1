"""Unit 324 in the console packet: ``EVAP_324`` — stage 1 (screen 324-1), stage 2 with LV-324501's
selector (screen 324-1B) and the four-condenser vacuum train.

Each block is V1's dictionary, key for key and rounding for rounding, read off the port's unit-324
results and loops (`ureasim.engine.plant.evaporation`). PY-324201 and AY-324701 are V1's soft
sensor, the stage's anchored equilibrium at its live temperature and vacuum
(`ureasim.thermo.urea_melt.melt_concentration_pct`, on the stage's refitted parameter, B-58).

LV-324501's selector, its closure and the UF85 fields are unit 335's dosing step's (decided
2026-10-16, decision 123: the dosing runs live on route A, where V1's call forces its interlock), so
the product is PFD 609, the raw melt with its UF85, and FFIC-335406's and FIC-335405's faceplates
carry their loops. The melt header is computed (decided 2026-11-14, decision 224): PIC-335201 is a
faceplate, FT-335401 LV-324501A's raw melt, the header valves online and HV-335602 with its drain to
335D004 published beside it, and the selector's closure counts that drain.

Source: V1 ``backend/main.py`` 10894-11028; ``route_lv324501`` (2440-2519).
"""

from __future__ import annotations

from ureasim.data.unit_324 import (
    E001_T_DES_C,
    E003_T_DES_C,
    F001_P_DES_BARA,
    F003_P_DES_BARA,
    MELT_A_UREA_WATER_K,
    LV_324501_RHO_KGM3,
    PIC_335201_RELIEF_BARG,
    VACUUM_CONDENSERS,
)
from ureasim.data.faceplates import GRANULATION_HEADERS_TAG
from ureasim.data.unit_335 import PFD_697_RHO_KGM3, PFD_697_T_C, W_697
from ureasim.engine.packet._common import Tick, faceplate, th
from ureasim.thermo.empirical import urea_soln_cp
from ureasim.thermo.urea_melt import melt_concentration_pct

__all__ = ["evap", "route_residuals"]


def _soft_sensor(w_live: float, t_des_c: float, p_des_bara: float, t_c: float,
                 p_bara: float) -> float:
    return melt_concentration_pct(w_live, t_des_c, p_des_bara, t_c, p_bara,
                                  a_urea_water_k=MELT_A_UREA_WATER_K)


def route_residuals(m_402_kgh: float, route) -> tuple[float, dict, float]:
    """LV-324501's selector closure: mass [kg/h], each species [kg/h] and energy [kW] in less out.

    Process utility
    ---------------
    The audit V1 publishes beside the selector: the raw melt and the UF85 in against the forward
    and recycle streams out, the forward stream at the selector's mean heat capacity. Each
    residual is the selector's rounding and nothing else. HV-335602's drain to 335D004 leaves at
    the forward stream's fractions and temperature, and the forward stream's heat capacity is
    LV-324501A's melt with its UF85 (decision 224: LV-324501B's recycle may flow beside it); on
    V1's selector both are V1's, the drain zero and the forward melt the whole drain.

    Source: V1 ``route_lv324501`` (2483-2496).
    """
    m_base = max(m_402_kgh, 0.0)
    m_uf = route.uf85_kgh
    base_w = route.recycle_w
    m_out = route.forward_kgh + route.drain_kgh
    species = {k: (m_base * base_w[k] + m_uf * W_697[k] - m_out * route.forward_w[k]
                   - route.recycle_kgh * base_w[k]) for k in base_w}
    t_c = route.recycle_t_c
    cp = urea_soln_cp(base_w["Urea"], t_c)
    cp_uf = urea_soln_cp(W_697["Urea"], PFD_697_T_C)
    m_forward = route.base_kgh
    m_selector = m_forward + m_uf
    heat_capacity_flow = m_forward * cp + m_uf * cp_uf
    selector_cp = heat_capacity_flow / m_selector if m_selector > 1.0e-15 else cp
    energy_in = (m_base * cp * t_c + m_uf * cp_uf * PFD_697_T_C) / 3600.0
    energy_out = (m_out * selector_cp * route.forward_t_c
                  + route.recycle_kgh * cp * route.recycle_t_c) / 3600.0
    return (m_base + m_uf - route.forward_kgh - route.recycle_kgh - route.drain_kgh, species,
            energy_in - energy_out)


def _node(tag: str, node) -> dict:
    """One vacuum condenser's balance as V1 publishes it, with its datasheet geometry."""
    rating = VACUUM_CONDENSERS[tag]
    return {
        "Q_kW": round(node.q_kw, 1),
        "UA_kW_K": round(node.ua_kw_k, 3),
        "T_vent_C": round(node.t_vent_c, 3),
        "LMTD_K": round(node.lmtd_k, 3),
        "cw_in_th": round(node.cw_flow_kgh / 1000.0, 3),
        "cw_in_C": round(node.cw_in_c, 2),
        "cw_out_C": round(node.cw_out_c, 2),
        "inlet_kgh": round(node.inlet_kgh, 1),
        "condensate_kgh": round(node.condensate_kgh, 1),
        "vent_kgh": round(node.vent_kgh, 1),
        "mass_residual_kgh": round(node.mass_residual_kgh, 6),
        "energy_residual_kW": round(node.energy_residual_kw, 6),
        "area_m2": rating.area_m2,
        "tube_count": rating.tube_count,
    }


def evap(t: Tick) -> dict:
    """324E001 / 324F001, 324E003 / 324F003 with LV-324501 and the melt header, and the vacuum
    train."""
    e1, e3, vac, mot = t.r("324E001"), t.r("324E003"), t.r("324E002-E007"), t.r("HV-329605/6")
    header = e3.header
    uf85 = t.r("335")
    route = uf85.route
    recycle = route.route == "B"
    mass_res, species_res, energy_res = route_residuals(e3.m_402_kgh, route)
    sel_t = route.recycle_t_c if recycle else route.forward_t_c
    sel_w = route.recycle_w if recycle else route.forward_w
    return {
        "E001": {
            "TT_324001": round(e1.t_c, 1),
            "PT_324201": round(e1.p_bara, 3),
            "PT_324202": round(e1.p_bara, 3),
            "LI_324F001": round(e1.level_pct, 1),
            "feed_th": th(e1.feed_kgh),
            "vapour_th": th(e1.m_vap_kgh),
            "melt_th": th(e1.melt_kgh),
            "urea_pct": round(e1.w_melt * 100.0, 1),
            "PY_324201": round(_soft_sensor(e1.w_melt, E001_T_DES_C, F001_P_DES_BARA, e1.t_c,
                                            e1.p_bara), 1),
            "p_chest_bara": round(e1.chest_p_bara, 2),
            "Q_kW": round(e1.q_kw, 0),
            "TIC_324001": faceplate(t.loop("TIC-324001"), 1, 2),
            "PIC_329203": faceplate(t.loop("PIC-329203"), 2, 1),
            "PIC_324202": faceplate(t.loop("PIC-324202"), 3, 1),
            "FIC_324401": faceplate(t.loop("FIC-324401"), 2, 1),
            "LI_329505": round(e1.cond_level_pct, 1),
            "cond_kgh": round(e1.steam_kgh, 0),
            "LIC_329505": faceplate(t.loop("LIC-329505")),
            "HIC_329605": round(t.operator["HIC-329605"], 1),
            "HV_329605": round(t.operator["HIC-329605"], 1),
            "motive_kgh": round(mot.m_924_kgh, 0),
            "P_324E002_sh": round(e1.p_bara, 3),
        },
        "E003": {
            "TT_324002": round(e3.t_c, 1),
            "PT_324204": round(e3.p_bara, 3),
            "PT_324203": round(e3.p_bara, 3),
            "LI_324F003": round(e3.level_pct, 1),
            "feed_th": th(e3.feed_kgh),
            "vapour_th": th(e3.m_vap_kgh),
            "melt_fwd_th": th(route.forward_kgh),
            "recyc_th": th(route.recycle_kgh),
            "route": route.route,
            "selector_stream": "402G" if recycle else "609",
            "selector_feed_th": round((route.forward_kgh + route.recycle_kgh
                                       + route.drain_kgh) / 1000.0, 3),
            "selector_feed_T_C": round(sel_t, 3),
            "selector_feed_comp": {k: round(v, 8) for k, v in sel_w.items()},
            "UF85_interlocked": bool(uf85.interlocked),
            "UF85_measured_ratio": round(uf85.measured_ratio, 8),
            "UF85_ratio_command": round(uf85.ratio_command, 8),
            "UF85_flow_setpoint_th": round(uf85.flow_setpoint_th, 6),
            "route_mass_residual_kgh": round(mass_res, 9),
            "route_species_residual_kgh": {k: round(v, 9) for k, v in species_res.items()},
            "route_energy_residual_kw": round(energy_res, 9),
            "LV_324501A": round(e3.lv_a_pct, 1),
            "LV_324501B": round(e3.lv_b_pct, 1),
            "PIC_335201": faceplate(t.loop("PIC-335201"), 2, 1),
            "FT_335401": round(route.base_kgh / LV_324501_RHO_KGM3, 2),
            "HEADERS_ONLINE": int(t.operator[GRANULATION_HEADERS_TAG]),
            "HIC_335602": round(t.operator["HIC-335602"], 1),
            "HV_335602": None if header is None else round(header.hv_pct, 1),
            "drain_335D004_th": th(route.drain_kgh),
            "LVB_relief_barg": PIC_335201_RELIEF_BARG,
            "recycle_selected": bool(e3.recycle_selected),
            "urea_pct": round(e3.w_melt * 100.0, 1),
            "AY_324701": round(_soft_sensor(e3.w_melt, E003_T_DES_C, F003_P_DES_BARA, e3.t_c,
                                            e3.p_bara), 1),
            "product_th": th(route.forward_kgh),
            "uf85_kgh": round(route.uf85_kgh, 1),
            "uf85_m3h": round(route.uf85_kgh / PFD_697_RHO_KGM3, 2),
            "p_chest_bara": round(e3.chest_p_bara, 2),
            "Q_kW": round(e3.q_kw, 0),
            "HIC_329606": round(t.operator["HIC-329606"], 1),
            "HV_329606": round(t.operator["HIC-329606"], 1),
            "P_324E005_sh": round(e3.p_bara, 3),
            "TIC_324002": faceplate(t.loop("TIC-324002"), 1, 2),
            "PIC_329212": faceplate(t.loop("PIC-329212"), 2, 1),
            "PIC_324203": faceplate(t.loop("PIC-324203"), 3, 1),
            "LIC_324501": faceplate(t.loop("LIC-324501")),
            "FFIC_335406": faceplate(t.loop("FFIC-335406"), 4, 4),
            "FIC_335405": faceplate(t.loop("FIC-335405"), 3, 1),
        },
        "VAC": {
            "condensate_th": th(vac.condensate_kgh),
            "vent_kgh": round(vac.streams_kgh["722"], 1),
            "mix703_residual_kgh": round(vac.mixing_residual_703_kgh, 3),
            **{tag: _node(tag, node) for tag, node in vac.nodes.items()},
        },
    }
