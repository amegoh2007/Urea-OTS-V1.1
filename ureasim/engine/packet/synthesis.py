"""The HP synthesis loop in the console packet: ``EJ_322F001``, ``CO2_FEED``, ``STRIP_322E001``,
``HPCC_322E002``, ``REACT_322R001`` and ``SCRUB_322E003``.

Each block is V1's dictionary, key for key and rounding for rounding, read off the port's results
for the loop (`ureasim.engine.plant.synthesis`, `synthesis_loop`) and the lagged indications of
V1's section 6 (`ureasim.units.synthesis.indicators`, step ``322-DISPLAY``). Where the port has
decided a divergence the value is the port's: the stripper's steam on its PFD row (decision 52),
PT-329201's relief through 322R001's certified valves under V1's ``SV_32201`` keys (decision 32).

Two V1 diagnostics are evaluated here, as V1 evaluates them beside its scrubber and read nowhere:
the overhead's free acid CO2 and its pressure-building push (`pressure_building_overhead`).

Source: V1 ``backend/main.py`` 10504-10600 (ejector, CO2 feed, stripper), 11029-11051 (HPCC),
11160-11252 (reactor, scrubber); the diagnostics 8095-8110.
"""

from __future__ import annotations

from ureasim.data.unit_320 import CO2_MASSFRAC_CO2, CO2_T_FEED_C
from ureasim.data.unit_322e003 import CCW_P_IN_BARA, CCW_P_OUT_BARA
from ureasim.engine.packet._common import MW_COMP, Tick, comp_pct, faceplate, th
from ureasim.units.synthesis.stripper import (
    TOP_DES_CO2_FREE_KMOLH,
    TOP_DES_KMOLH_TOTAL,
    TOP_DES_NH3_KMOLH,
)

__all__ = ["ejector", "co2_feed", "stripper", "hpcc", "reactor", "scrubber",
           "pressure_building_overhead"]


def ejector(t: Tick) -> dict:
    """322F001: the motive and the entrained carbamate, HV-322602, the discharge into 322E002."""
    ej, lag = t.r("322F001"), t.r("322-DISPLAY")
    total = ej.total_kgh
    return {
        "motive_kgh": round(t.r("321").motive_nh3_kgh, 1),
        "suction_kgh": round(ej.suction_kgh, 1),
        "HIC_322602": round(t.operator["HIC-322602"], 1),
        "XV_322903": bool(t.operator["XV-322903"]),
        "mu": round(ej.mu, 4),
        "TT_322012": round(lag.tt_322012_c, 1),
        "PI_disch": round(ej.p_bara, 1),
        "TI_322002": round(lag.tt_322002_c, 1),
        "PI_329201": round(t.r("322E003").scrubber.p_overflow_bara, 1),
        "total_kgh": round(total, 1),
        "total_th": round(total / 1000.0, 2),
        "mol_kmolh": round(ej.mol_kmolh, 2),
        "MW": round(ej.mw, 2),
        "rho": round(ej.rho, 1),
        "vol_m3h": round(ej.vol_m3h, 2),
        "comp_pct": {k: (round(ej.comp_kgh[k] / total * 100.0, 3) if total > 0 else 0.0)
                     for k in MW_COMP},
    }


def co2_feed(t: Tick) -> dict:
    """320K002 through XV-322902 to 322E001: FT/FY-322403, the vent PV-322203 and PIC-322203."""
    line, res = t.units["320K002"], t.r("320K002")
    pic = t.loops["320K002"][0]
    return {
        "FT_322403": round(res.ft_322403_nm3h, 0),
        "FY_322403": round(res.fy_322403_th, 2),
        "TI_322017": round(CO2_T_FEED_C, 1),
        "pure_th": round(res.feed_th * CO2_MASSFRAC_CO2, 2),
        "raw_th": round(t.operator["320K002-CO2"], 2),
        "vent_th": round(res.vent_th, 2),
        "Load": round(res.load_pct, 1),
        "XV_322902": bool(line.xv_322902_open),
        "PV_322203": round(res.vent_opening_pct, 1),
        "HIC_322203": round(line.hic_min_pct, 1),
        "PIC_322203": round(pic.pv, 1),
        "PIC_op": round(pic.op, 1),
        "PIC_sp": round(pic.sp, 1),
        "PIC_mode": pic.mode,
    }


def stripper(t: Tick) -> dict:
    """322E001: its feed and products, the reactions, LT-322501 / LV-322501 and the MP shell."""
    step, lag = t.r("322E001"), t.r("322-DISPLAY")
    st, sump = step.stripper, step.sump
    return {
        "TT_322014": round(t.r("322R001").t_overflow_c, 1),
        "TT_322013": round(lag.tt_322013_c, 1),
        "TT_322004": round(sump.tt_322004_c, 1),
        "TT_323001": round(lag.tt_323001_c, 1),
        "top_th": round(st.top_th, 2),
        "top_MW": round(st.top_mw, 2),
        "top_mol_pct": comp_pct(st.top_comp_pct, 3),
        "bot_th": round(st.bot_th, 2),
        "bot_MW": round(st.bot_mw, 2),
        "bot_mass_pct": comp_pct(st.bot_mass_pct, 3),
        "xi_hyd": round(st.xi_hydrolysis, 2),
        "xi_biu": round(st.xi_biuret, 3),
        "eta_T": round(st.eta_t, 4),
        "g_NC": round(st.g_nc, 4),
        "g_HC": round(st.g_hc, 4),
        "L_strip": round(st.feed_nc, 4),
        "W_strip": round(st.feed_hc, 4),
        "LI_322501": round(sump.level_pct, 1),
        "LV_322501": round(sump.lv_opening_pct, 1),
        "drain_th": th(sump.drain_kgh),
        "blowthrough_th": th(sump.blowthrough_kgh),
        "LIC_322501": faceplate(t.loops["322E001"][0]),
        "steam": {
            "TI_shell": round(st.t_steam, 1),
            "P_bara": round(t.r("329").p_hp_bara, 1),
            "kgh": round(step.strip_kgh, 0),
            "duty_kW": round(step.duty_kw, 0),
        },
    }


def hpcc(t: Tick) -> dict:
    """322E002: its two feeds' and its product's lagged temperatures, the split it condenses, the
    level, PI-322E002 and the LP steam its shell raises."""
    step, lag = t.r("322E002"), t.r("322-DISPLAY")
    c = step.holdup.condenser
    return {
        "TT_322012": round(lag.tt_322012_c, 1),
        "TT_322013": round(lag.tt_322013_c, 1),
        "TT_322010": round(lag.tt_322010_c, 1),
        "TT_329001": round(step.t_shell_c, 1),
        "gas_th": round(c.gas_th, 2),
        "gas_MW": round(c.gas_mw, 2),
        "gas_mol_pct": comp_pct(c.gas_mol_pct, 3),
        "liq_th": round(c.liq_th, 2),
        "liq_MW": round(c.liq_mw, 2),
        "liq_mass_pct": comp_pct(c.liq_mass_pct, 3),
        "phi_gas": {k: c.phi_gas[k] for k in MW_COMP},
        "LT_322E002": round(step.holdup.level_pct, 1),
        "P_bara": round(lag.pi_322e002_bara, 1),
        "steam": {
            "TI_shell": round(step.t_shell_c, 1),
            "P_bara": round(t.r("329").p_lp_bara, 1),
            "kgh": round(c.steam_kgh, 0),
            "duty_kW": round(c.duty_kw, 0),
        },
    }


def reactor(t: Tick) -> dict:
    """322R001: the four node temperatures up the column, the off-gas, LT-322504, AT-322701,
    HV-322605 and the reaction's diagnostics."""
    r = t.r("322R001")
    rx = r.reaction
    nodes = r.t_nodes_c
    return {
        "TT_322005": round(nodes[3], 1),
        "TT_322006": round(nodes[2], 1),
        "TT_322007": round(nodes[1], 1),
        "TT_322008": round(nodes[0], 1),
        "TT_322009": round(r.t_offgas_c, 1),
        "LT_322504": round(r.lt_322504_pct, 1),
        "AT_322701": round(t.r("322-DISPLAY").at_322701, 3),
        "HIC_322605": round(t.operator["HIC-322605"], 1),
        "HV_322605": round(t.operator["HIC-322605"], 1),
        "P_bara": round(r.p_bara, 1),
        "P_offgas": round(r.p_offgas_bara, 1),
        "closure_resid": round(rx.closure_resid, 2),
        "X_conv": round(rx.x_conv * 100.0, 2),
        "L_feed": round(rx.l_feed, 3),
        "W_feed": round(rx.w_feed, 4),
        "xi_urea": round(rx.xi_urea, 2),
    }


def pressure_building_overhead(top_kmolh: dict, rho_cond: float) -> tuple[float, float]:
    """The stripper overhead's free acid CO2 [kmol/h] and its pressure-building push [-].

    Process utility
    ---------------
    Of 322E001's overhead only the CO2 unpaired by ammonia (2 NH3 + CO2 -> carbamate) and the
    ammonia beyond what the scrubber can condense build synthesis pressure; the rest condenses.
    V1 publishes both as diagnostics beside the scrubber; nothing reads them back (V1's own
    forward push on PT-329201 was removed).

    Equations
    ---------
        CO2_free = max(n_CO2 - n_NH3 / 2, 0)
        NH3_slip = max(1 - rho_cond, 0) . max(n_NH3 - n_NH3,des, 0)
        push     = (CO2_free + NH3_slip - CO2_free,des) / n_total,des

    Source: V1 ``backend/main.py`` 8095-8099.
    """
    co2_free = max(top_kmolh["CO2"] - 0.5 * top_kmolh["NH3"], 0.0)
    nh3_slip = max(1.0 - rho_cond, 0.0) * max(top_kmolh["NH3"] - TOP_DES_NH3_KMOLH, 0.0)
    push = ((co2_free + nh3_slip - TOP_DES_CO2_FREE_KMOLH) / TOP_DES_KMOLH_TOTAL
            if TOP_DES_KMOLH_TOTAL else 0.0)
    return co2_free, push


def scrubber(t: Tick, streams: dict) -> dict:
    """322E003: its off-gas and overflow (from the stream registry, as V1 reads them), HV-322604,
    LT-329501 with its swell and hunt, and the tempered-water circuit with PT-329201's relief."""
    step, lag, purge = t.r("322E003"), t.r("322-DISPLAY"), t.r("HV-322604")
    sc, sump = step.scrubber, step.sump
    ccw = t.loops["322E003"][0]
    loop = t.r("PT-329201")
    co2_free, pb_push = pressure_building_overhead(t.r("322E001").stripper.top_kmolh,
                                                   step.rho_cond)
    off, ov = streams["SCRUB_OFFGAS"], streams["CARB_RECYCLE"]
    return {
        "TT_322009": round(t.r("322R001").t_offgas_c, 1),
        "TT_322011": round(lag.tt_322011_c, 1),
        "off_th": off["mass_th"],
        "off_mol": off["mol_kmolh"],
        "off_MW": off["MW"],
        "off_mol_pct": off["mol_pct"],
        "ov_th": ov["mass_th"],
        "ov_mol": ov["mol_kmolh"],
        "ov_MW": ov["MW"],
        "ov_mass_pct": ov["mass_pct"],
        "carb_th": round(sum(sc.carb_kmolh[k] * MW_COMP[k] for k in MW_COMP) / 1000.0, 3),
        "closure_resid": round(sc.closure_resid, 2),
        "HV_322604": round(t.operator["HIC-322604"], 1),
        "HIC_322604": round(t.operator["HIC-322604"], 1),
        "TT_322011_lp": round(lag.tt_322011_lp_c, 1),
        "og_lp_th": round(purge.valve.mass_kgh / 1000.0, 3),
        "vent_frac": round(purge.vent_frac, 4),
        "P_offgas": round(sc.p_offgas_bara, 1),
        "P_overflow": round(sc.p_overflow_bara, 1),
        "TT_322002": round(lag.tt_322002_c, 1),
        "LT_329501": round(sump.lt_329501_pct, 1),
        "LT_329501_true": round(sump.level_pct, 1),
        "LT_329501_swell": round(sump.lt_329501_swell_pct, 1),
        "LT_329501_noise": round(sump.lt_329501_noise_pct, 2),
        "ccw": {
            "TT_329125": round(lag.tt_329125_c, 2),
            "TDY_329125": round(sc.t_ccw_out_c - ccw.tic_pv, 2),
            "vent_ratio": round(sc.vent_ratio, 4),
            "rho_cond": round(step.rho_cond, 4),
            "cool_frac": round(sc.cool_frac, 4),
            "uncond_th": round(sc.uncond_kgh / 1000.0, 3),
            "vap_excess_kg": round(loop.vap_excess_kg, 1),
            "dP_phase": round(loop.m_vap_net_kgh
                              / (loop.c_vap_kg_per_bar + loop.c_buf_kg_per_bar), 4),
            "SV_32201_th": round(loop.m_relief_kgh / 1000.0, 3),
            "SV_32201_nh3_kgh": round(loop.m_relief_nh3_kgh, 1),
            "SV_32201_open": bool(loop.relief_lifted),
            "co2_free": round(co2_free, 1),
            "pb_push": round(pb_push, 5),
            "PI_322E002": round(lag.pi_322e002_bara, 1),
            "Q_ccw_kW": round(sc.q_ccw_kw, 0),
            "Q_carb_kW": round(sc.q_carb_kw, 0),
            "co2_abs": round(sc.co2_abs, 2),
            "FIC_329409": faceplate(ccw, 1, 1, prefix="fic_"),
            "TIC_329005": faceplate(ccw, 1, 1, prefix="tic_"),
            "P329P006A": {"on": bool(ccw.p329p006a)},
            "P329P006B": {"on": bool(ccw.p329p006b)},
            "P329P006_in": round(CCW_P_OUT_BARA, 1),
            "P329P006_out": round(CCW_P_IN_BARA, 1),
            "E004_duty_kW": round(sc.q_ccw_kw, 0),
        },
    }
