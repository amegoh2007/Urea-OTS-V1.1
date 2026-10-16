"""Unit 329 in the console packet: ``STEAM_SYSTEM`` — the 25-bar main, 329D005's MP header,
329D009's 9-bar drum, the LP header on 322D001A/B, and their faceplates (screen 329-1).

V1's block is its lumped ``steam_system`` state; the port's network (`ureasim.units.steam`) is the
decided one — every user live on its header (B-68), the LP header at 4.0 bar g (B-69), superheat
boiling drum water (B-70), the letdown carrying its superheat (decision 58). Each V1 key is read off
the network's result and controllers as below; a V1 flow is the port's stream:

====================  ===================================  ==================================
V1                    what it is                           the port's
====================  ===================================  ==================================
``m_supply``          PV-329204 into 329D005               ``flows_kgh["902"]``
``m_903``             PV-329205A into 329D009              ``flows_kgh["903"]``
``m_flash9``          904's flash in 329D009               ``flows_kgh["906"]``
``m_users9``          the 9-bar users                      ``flows_kgh["users_9"]``
``m_ld``              PV-329205B, 9 -> 4 bar               ``flows_kgh["960"]``
``m_water``           water desuperheating into the LP     ``flows_kgh["ds_322D001"]``, the
                      header                               drums' water 963's superheat boils
``m_vent_hp``         HV-329601                            ``flows_kgh["HV-329601"]``
``m_963``             PV-329207C and HV-329602             ``flows_kgh["963"]``
``m_turbine``         PV-329207B to 320MT02                ``flows_kgh["932"]``
``m_pic``             PV-329207A's vent and the turbine    ``PV-329207A`` + ``932``
FT-329403             stream 901                           ``flows_kgh["901"]``
====================  ===================================  ==================================

``ANALYSERS``, a block V1 does not publish (decided 2026-10-09, handoff B-90): ``AI_329701``, the
LP condensate's conductivity in 329D001 on its 0-10 uS/cm range, and ``AI_329701_over``, past that
range — the instrument that shows a 322E002 tube leak (`units.steam.condensate_analyser`);
``D001_solids_ppm``, the solids the leak leaves in 322D001A/B's water, which no plant instrument
reads (a laboratory sample's value).

Source: V1 ``backend/main.py`` 11052-11159; ``steam_system.py`` (the state's fields, 410-430).
"""

from __future__ import annotations

from ureasim.core.units_of_measure import ATM_BARA
from ureasim.data.unit_329 import P_SUP_BARA, STEAM_PFD_KGH
from ureasim.engine.packet._common import Tick
from ureasim.thermo.iapws import tsat_c

__all__ = ["steam", "analysers"]


def _level(loop, level_pct: float) -> dict:
    return {"pv": round(level_pct, 1), "sp": round(loop.sp_pct, 1), "op": round(loop.op_pct, 1),
            "mode": loop.mode}


def steam(t: Tick) -> dict:
    """The steam system's headers, flows, residuals and faceplates."""
    net, r = t.units["329"], t.r("329")
    f, stroke, lvl = r.flows_kgh, r.strokes_pct, r.levels_pct
    trio = net.pic_329207
    leg_a, leg_b, leg_c = trio.legs["A"], trio.legs["B"], trio.legs["C"]
    t_shell = t.r("322E002").t_shell_c
    p_lp = r.p_lp_bara
    vap, water = r.vapour_residual_kgh, r.water_residual_kgh
    return {
        "FT_329403_th": round(f["901"] / 1000.0, 2),
        "FT_329407_th": round(f["932"] / 1000.0, 2),
        "FT_329407_design_th": round(STEAM_PFD_KGH["932"] / 1000.0, 2),
        "MP": {
            "P_bara": round(r.p_hp_bara, 2),
            "TI_sat": round(r.t_hp_c, 1),
            "supply_pct": round(stroke["PV-329204"], 1),
            "m_supply_th": round(f["902"] / 1000.0, 1),
        },
        "LP": {
            "P_bara": round(r.p_lp_start_bara, 2),
            "P_next_bara": round(p_lp, 2),
            "TI_sat": round(t_shell, 1),
            "TI_HPCC_shell": round(t_shell, 1),
            "letdown_pct": round(stroke["PV-329205B"], 1),
            "m_ld_th": round(f["960"] / 1000.0, 1),
            "m_water_th": round(f["ds_322D001"] / 1000.0, 1),
        },
        "SUPPLY_25BAR": {
            "P_bara": round(P_SUP_BARA, 2),
            "TI_sat": round(tsat_c(P_SUP_BARA), 1),
        },
        "DRUM_9BAR": {
            "P_bara": round(r.p_9_bara, 2),
            "TI_sat": round(r.t_9_c, 1),
            "admit_pct": round(stroke["PV-329205A"], 1),
            "letdown_pct": round(stroke["PV-329205B"], 1),
            "m_903_th": round(f["903"] / 1000.0, 2),
            "m_flash_th": round(f["906"] / 1000.0, 2),
            "m_users_th": round(f["users_9"] / 1000.0, 2),
            "m_ld_th": round(f["960"] / 1000.0, 2),
        },
        "HP_VENT": {
            "pct": round(stroke["HV-329601"], 1),
            "m_th": round(f["HV-329601"] / 1000.0, 2),
        },
        "LP_MAKEUP": {
            "PV_329207C": round(stroke["PV-329207C"], 1),
            "HV_329602": round(stroke["HV-329602"], 1),
            "m_963_th": round(f["963"] / 1000.0, 2),
            "m_pic_th": round((f["PV-329207A"] + f["932"]) / 1000.0, 2),
        },
        "mass_residual_kg_s": {
            "d005_vapor": vap["329D005"] / 3600.0,
            "d009_vapor": vap["329D009"] / 3600.0,
            "lp_vapor": vap["322D001"] / 3600.0,
            "d005_liquid": water["329D005"] / 3600.0,
            "d009_liquid": water["329D009"] / 3600.0,
            "lp_liquid": water["322D001"] / 3600.0,
        },
        "PIC_329204": {
            "pv": round(r.p_hp_bara, 2),
            "sp": round(net.pic_329204.sp_bara, 2),
            "op": round(stroke["PV-329204"], 1),
            "mode": net.pic_329204.mode,
        },
        "PIC_329205": {
            "pv": round(r.p_9_bara, 2),
            "sp": round(net.pic_329205.sp_bara, 2),
            "op": round(stroke["PV-329205A"] - stroke["PV-329205B"], 1),
            "mode": net.pic_329205.mode,
        },
        "PIC_329207": {
            "pv": round(p_lp, 2),
            "sp": round(leg_b.sp_bara, 2),
            "op": round((f["PV-329207A"] + f["932"]) / 1000.0, 2),
            "mode": leg_b.mode,
            "pv_barg": round(p_lp - ATM_BARA, 2),
            "sp_barg": round(trio.master_sp_bara - ATM_BARA, 2),
        },
        "MASTER_SP_329207": {
            "on": trio.master_on,
            "sp": round(trio.master_sp_bara, 2),
            "pv": round(p_lp, 2),
        },
        "PIC_329207A": {
            "pv": round(p_lp, 2), "sp": round(leg_a.sp_bara, 2),
            "op": round(stroke["PV-329207A"], 1), "mode": leg_a.mode,
        },
        "PIC_329207B": {
            "pv": round(p_lp, 2), "sp": round(leg_b.sp_bara, 2),
            "op": round(stroke["PV-329207B"], 1),
            "m_turbine_th": round(f["932"] / 1000.0, 2), "mode": leg_b.mode,
        },
        "PIC_329207C": {
            "pv": round(p_lp, 2), "sp": round(leg_c.sp_bara, 2),
            "op": round(stroke["PV-329207C"], 1), "mode": leg_c.mode,
        },
        "LIC_329502": _level(net.lic_329502, lvl["LIC-329502"]),
        "LIC_329503": _level(net.lic_329503, lvl["LIC-329503"]),
        "LIC_329504": _level(net.lic_329504, lvl["LIC-329504"]),
    }


def analysers(t: Tick) -> dict:
    """The port's analysers block (B-90): AI-329701 and the drums' solids."""
    users, r = t.r("329-USERS"), t.r("329")
    return {"AI_329701": round(users.ai_329701_us_cm, 3),
            "AI_329701_over": users.ai_329701_over,
            "AI_329701_H1": users.ai_329701_h1, "AI_329701_H2": users.ai_329701_h2,
            "D001_solids_ppm": round(r.d001_solids_ppm, 1)}
