"""Units 328 and 322C001 in the console packet: ``DESORB_328`` (desorption and hydrolysis,
screen 328-1) and ``ABSORB_328`` (322C001 and 328D003, screen 328-2).

Each block is V1's dictionary, key for key and rounding for rounding, read off the port's results
and loops (`ureasim.engine.plant.desorption`, `absorption`). Where the port has decided a divergence
the value is the port's: TI-322015 where the P&ID draws it (decision 37), 328E004's cooling-water
return on its held duty (decision 28), each level between its transmitter's taps (decision 33),
FFIC-329401 as Uhde's ratio station (decision 26); 328D003's block adds 322P002's field-set
delivery, the instructor's field action (decision 212). V1's unit-328 energy-closure ledger
(``Q328_*_kW``, its AUDIT C4 diagnostic) is not ported and publishes None.

Source: V1 ``backend/main.py`` 10729-10893.
"""

from __future__ import annotations

from ureasim.data.unit_328d001 import D001_RHO_KGM3, RHO_775_KGM3
from ureasim.data.console_packet import RHO_755_KGM3
from ureasim.data.faceplates import P002_DELIVERY_TAG
from ureasim.data.unit_328d003 import D003_VOL_I_M3, D003_VOL_II_M3, D003_VOL_III_M3, RHO_741_KGM3
from ureasim.engine.packet._common import Tick, faceplate, th
from ureasim.engine.packet.recirculation import flow_loop

__all__ = ["desorb", "absorb"]


def desorb(t: Tick) -> dict:
    """328C002, 328C003 with 328E021, 328C004 with FFIC-329401, and 328D001 with 328E004."""
    c2, c3, c4, d1, e7 = (t.r("328C002"), t.r("328C003"), t.r("328C004"), t.r("328D001"),
                          t.r("328E007"))
    c4_loops = t.loops["328C004"][0]
    ffic = c4_loops.ffic_329401
    return {
        "C002": {
            "R328_C002_T_BOT_BOT": round(c2.t_c, 1),
            "TT_328007": round(c2.t_c, 1),
            "TT_328008": round(c2.t_top_c, 1),
            "P_bara": round(c2.p_bara, 2),
            "TT_328010": round(e7.t_738_c, 1),
            "LI_328503": round(c2.level_pct, 1),
            "feed738_th": th(e7.m_738_kgh),
            "ovhd737_th": th(c2.m_737_kgh),
            "bot743_th": th(c2.m_743_kgh),
            "LIC_328503": faceplate(t.loop("LIC-328503")),
        },
        "C003": {
            "TT_328C003": round(c3.t_c, 1),
            "TT_328012": round(c3.t_746_c, 1),
            "TT_328011": round(c3.t_748_c, 1),
            "TT_328009": round(c3.t_746_c, 1),
            "P_bara": round(c3.p_bara, 2),
            "LI_328504": round(c3.level_pct, 1),
            "steam911_th": th(c3.m_911_kgh),
            "ovhd748_th": th(c3.m_748_kgh),
            "bot747_th": th(c3.m_747_kgh),
            "X_hydrolysis": round(c3.x_hyd * 100.0, 4),
            "xi_urea_kmolh": round(c3.xi_kmolh, 4),
            "urea_in_kgh": round(c3.urea_in_kgh, 1),
            "urea_slip_ppm": round(c3.urea_747_ppm, 3),
            "gas_hyd_kgh": round(c3.gas_hyd_kgh, 1),
            "gas_strip_kgh": round(c3.gas_strip_kgh, 1),
            "PIC_328203": faceplate(t.loop("PIC-328203"), 2, 1),
            "LIC_328504": faceplate(t.loop("LIC-328504")),
            "FIC_329402": faceplate(t.loop("FIC-329402")),
            "TIC_328012": faceplate(t.loop("TIC-328012"), 1, 2),
        },
        "C004": {
            "R328_C004_T": round(c4.t_c, 1),
            "TT_328005": round(c4.t_c, 1),
            "TT_328004": round(c4.t_top_c, 1),
            "P_bara": round(c4.p_bara, 2),
            "LI_328505": round(c4.level_pct, 1),
            "steam931_th": th(c4.m_931_kgh),
            "ovhd750_th": th(c4.m_750_kgh),
            "bot739_th": th(c4.m_739_kgh),
            "recyc741_th": th(c4.m_741_kgh),
            "export740_th": th(max(c4.m_739_kgh - c4.m_741_kgh, 0.0)),
            "TT_328006": round(e7.t_740_c, 1),
            "AI_328701": round(c4.ai_328701_us_cm, 2),
            "nh3_740_ppm": round(c4.w["NH3"] * 1e6, 3),
            "urea_740_ppm": round(c4.w["Urea"] * 1e6, 3),
            "FFIC_329401": faceplate(ffic, 4, 1),
            "FIC_329401": faceplate(t.loop("FIC-329401")),
            "LIC_328505": faceplate(t.loop("LIC-328505")),
        },
        "D001": {
            "TT_328D001": round(d1.t_c, 1),
            "P_bara": round(d1.p_bara, 2),
            "LI_328501": round(d1.level_pct, 1),
            "vent786_th": th(d1.m_786_kgh),
            "reflux775_th": th(d1.m_775_kgh),
            "draw776_th": th(d1.m_776_kgh),
            "flow776_m3h": round(d1.m_776_kgh / D001_RHO_KGM3, 2),
            "PIC_328202": faceplate(t.loop("PIC-328202"), 2, 1),
            "LIC_328501": faceplate(t.loop("LIC-328501")),
            "FIC_328404": flow_loop(t.loop("FIC-328404"), d1.m_775_kgh, RHO_775_KGM3, "m_kgh"),
            "TIC_328002": faceplate(t.loop("TIC-328002"), 1, 2),
            "TT_329007": round(d1.t_cw_return_c, 1),
            "TIC_328008": faceplate(t.loop("TIC-328008"), 1, 2),
        },
    }


def absorb(t: Tick) -> dict:
    """322C001, the LP off-gas absorber on HV-322604's purge, and 328D003's three bays."""
    c1, d3, c5 = t.r("322C001"), t.r("328D003"), t.r("323C005")
    w = t.units["322C001"].w
    y, beds = c1.y_vent, c1.beds
    read = t.tears_read
    m_744 = d3.m_744_kgh
    return {
        "C001": {
            "TT_322015": round(c1.t_ti_322015_c, 1),
            "P_bara": round(c1.p_bara, 2),
            "LI_322502": round(c1.level_pct, 1),
            "gcb_th": th(c1.m_gas_kgh),
            "gcb_T": round(c1.t_gas_c, 1),
            "abs_th": th(c1.m_abs_kgh),
            "vent_th": th(c1.m_vent_kgh),
            "vent_nh3_kgh": round(c1.m_vent_kgh * (y["NH3"] if y else 0.0), 1),
            "vent_nh3_pct": round((y["NH3"] if y else 0.0) * 100.0, 2),
            "vent_co2_pct": round((y["CO2"] if y else 0.0) * 100.0, 2),
            "ntu_lower_nh3": round(beds.ntu.get("lo_NH3", 0.0), 2) if beds else None,
            "ntu_upper_nh3": round(beds.ntu.get("up_NH3", 0.0), 2) if beds else None,
            "ystar_lower_nh3_pct": round(beds.y_star_lo["NH3"] * 100.0, 3) if beds else None,
            "dT_upper_bed": round(beds.dt_up_k, 2) if beds else None,
            "liq_nh3_pct": round(w.get("NH3", 0.0) * 100.0, 2),
            "liq_co2_pct": round(w.get("CO2", 0.0) * 100.0, 2),
            "liquor756_th": th(c1.m_756_kgh),
            "cpl_kgh": round(t.operator["FIC-322404"], 1),
            "make_conc_pct": round(c1.m_abs_kgh / max(c1.m_756_kgh, 1e-6) * 100.0, 2),
            "XV_322915": bool(t.units["TRIPS"].xv_322915_open),
            "SV_32253_th": round(c1.m_relief_kgh / 1000.0, 3),
            "SV_32253_open": bool(c1.relief_lifted),
            "overloaded": bool(c1.overloaded),
            "PIC_322201": faceplate(t.loop("PIC-322201"), 2, 1),
            "LIC_322502": faceplate(t.loop("LIC-322502")),
        },
        "D003": {
            "TT_328I": round(d3.t_i_c, 1),
            "TT_328II": round(d3.t_ii_c, 1),
            "TT_328III": round(d3.t_iii_c, 1),
            "LI_328I": round(d3.level_i_pct, 1),
            "LI_328II": round(d3.level_ii_pct, 1),
            "LI_328III": round(d3.level_iii_pct, 1),
            "LT_328507_open_loop": round(d3.level_i_pct, 1),
            "LT_328508_open_loop": round(d3.level_ii_pct, 1),
            "capacities_m3": {"I": D003_VOL_I_M3, "II": D003_VOL_II_M3, "III": D003_VOL_III_M3},
            "form735_th": th(d3.m_735_kgh),
            "collect755_th": th(m_744),
            "flow755_m3h": round(m_744 / RHO_755_KGM3, 2),
            "compI_pfd_rounding_kgh": round(
                (read.m_719_kgh + read.m_720_kgh + read.m_721_kgh + read.m_759_kgh) - m_744, 3),
            "compII_pfd_rounding_kgh": round(
                (c5.m_343_kgh + d3.m_741_kgh)
                - (d3.m_735_kgh + d3.m_734_kgh + d3.m_791_kgh + d3.m_793_kgh), 3),
            "FIC_328406": flow_loop(t.loop("FIC-328406"), d3.m_741_kgh, RHO_741_KGM3, "m_kgh"),
            "Q328_in_kW": None,
            "Q328_out_kW": None,
            "Q328_react_kW": None,
            "Q328_resid_kW": None,
            "P002A": {"on": t.operator["322P002A"]["on"], "mode": t.operator["322P002A"]["mode"]},
            "P002B": {"on": t.operator["322P002B"]["on"], "mode": t.operator["322P002B"]["mode"]},
            # 322P002's delivery as the field operator set it, in FI-322402's m3/h (decision 212).
            "P002_delivery_set_m3h": round(t.operator[P002_DELIVERY_TAG] / RHO_755_KGM3, 2),
        },
    }
