"""Unit 323 in the console packet: ``RECIRC_323`` (the liquor train, screens 323-1 / 323-1B) and
``LPCC_3232`` (the LP condensers and 323C005, screen 323-2).

Each block is V1's dictionary, key for key and rounding for rounding, read off the port's unit-323
results and loops (`ureasim.engine.plant.recirc`) and, for the flows V1 shows on these screens
from other units, those units' results: 322C001's 756, 328D003's 744, 735 (FIC-328402's, handoff
B-39), 734, 791 and 793. A level is
the port's (the transmitter between its taps, decision 33), not V1's mass over a full vessel.
323C005's inflows are the recycle tears the tick read (V1's ``m756_prev`` and its kin).

Source: V1 ``backend/main.py`` 10601-10728.
"""

from __future__ import annotations

from ureasim.data.unit_323e011 import RHO_718_KGM3
from ureasim.data.unit_328d003 import RHO_401_KGM3, RHO_735_KGM3, RHO_791_KGM3
from ureasim.engine.packet._common import Tick, faceplate, th

__all__ = ["recirc", "lpcc", "flow_loop"]


def recirc(t: Tick) -> dict:
    """323C003 with 323E002, 323F004, 323F010 with 323E010, and 323D002."""
    c3, f4, f10, d2 = t.r("323C003"), t.r("323F004"), t.r("323F010"), t.r("323D002")
    return {
        "C003": {
            "TT_323002": round(c3.tt_323002_c, 1),
            "P_bara": round(c3.p_bara, 2),
            "LI_323501": round(c3.level_pct, 1),
            "feed_th": th(c3.feed_kgh),
            "feed_T": round(c3.feed_t_c, 1),
            "v305_th": th(c3.m_305_kgh),
            "drain314_th": th(c3.m_314_kgh),
            "blow501_th": th(c3.blowthrough_kgh),
            "Q_kW": round(c3.q_e002_kw, 0),
            "TIC_323007": faceplate(t.loop("TIC-323007"), 1, 2),
            "PIC_329202": faceplate(t.loop("PIC-329202"), 2, 1),
            "LIC_323501": faceplate(t.loop("LIC-323501")),
        },
        "F004": {
            "TT_323005": round(f4.t_c, 1),
            "P_bara": round(f4.p_bara, 2),
            "LI_323505": round(f4.level_pct, 1),
            "v701_th": th(f4.m_701_kgh),
            "blow505_th": th(f4.blowthrough_kgh),
            "drain319_th": th(f4.m_319_kgh),
            "LIC_323505": faceplate(t.loop("LIC-323505")),
        },
        "F010": {
            "TT_323010": round(f10.t_c, 1),
            "P_bara": round(f10.p_bara, 3),
            "HV_323605": round(t.operator["HIC-323605"], 1),
            "LI_323F010": round(f10.level_pct, 1),
            "feed331_th": th(f10.m_331_kgh),
            "evap_th": th(f10.m_evap_kgh),
            "product317_th": th(f10.m_317_kgh),
            "Q_kW": round(f10.q_e010_kw, 0),
            "TIC_323012": faceplate(t.loop("TIC-323012"), 1, 2),
            "PIC_329208": faceplate(t.loop("PIC-329208"), 2, 1),
        },
        "D002": {
            "T_C": round(d2.t_c, 1),
            "TI_323008": round(d2.t_c, 1),
            "LI_323507": round(d2.lic_pv_pct, 1),
            "LI_323504": round(d2.li_323504_pct, 1),
            "LI_comp2": round(d2.li_323504_pct, 1),
            "HV_tie": bool(t.operator["HV-323D002-TIE"]),
            "rho_kgm3": round(d2.rho_kgm3, 1),
            "m3_comp1": round(d2.comp_i_m3, 1),
            "m3_comp2": round(d2.comp_ii_m3, 1),
            "urea_pct": round(d2.w.get("Urea", 0.0) * 100.0, 2),
            "product324_th": th(d2.m_324_kgh),
            "LIC_323507": faceplate(t.loop("LIC-323507")),
            "FIC_324401": faceplate(t.loop("FIC-324401")),
        },
    }


def flow_loop(loop, m_kgh: float, rho: float, mass_key: str) -> dict:
    """A volumetric flow loop's faceplate (m3/h, two places) with the raw stream V1 shows beside
    it: its volume at the stream's density and its delivered mass."""
    return {**faceplate(loop, 2, 1), "vol_m3h": round(m_kgh / rho, 2), mass_key: round(m_kgh, 1)}


def lpcc(t: Tick) -> dict:
    """323E003 / 323D001 on tempered water, 323E011 / 323D011, and 323C005."""
    e3, e11, c5, d3 = t.r("323E003"), t.r("323E011"), t.r("323C005"), t.r("328D003")
    read = t.tears_read
    m_756, m_702, m_708 = read.m_756_kgh, read.m_702_kgh, read.m_708_kgh
    return {
        "E003": {
            "TT_323006": round(e3.t_c, 1),
            "P_bara": round(e3.p_bara, 2),
            "LI_323502": round(e3.level_pct, 1),
            "in305_th": th(t.r("323C003").m_305_kgh),
            "carbamate308_th": th(e3.m_308_kgh),
            "vent321_th": th(e3.m_321_kgh),
            "wash744_th": th(d3.m_744_kgh),
            "liquor756_th": th(t.r("322C001").m_756_kgh),
            "PIC_323202": faceplate(t.loop("PIC-323202"), 2, 1),
            "LIC_323502": faceplate(t.loop("LIC-323502")),
            "SIC_323901": faceplate(t.loop("SIC-323901")),
            "SIC_323902": faceplate(t.loop("SIC-323902")),
            "TIC_323013": faceplate(t.loop("TIC-323013"), 1, 2),
            "TV_323013A": round(e3.tv_a_op_pct, 1),
            "TV_323013B": round(100.0 - e3.tv_a_op_pct, 1),
            "TT_323015": round(e3.tw_return_c, 1),
            # V1's key, under 323E003 where V1 hangs the loop on 744; it meters 735 (B-39).
            "FIC_328402": flow_loop(t.loop("FIC-328402"), d3.m_735_kgh, RHO_735_KGM3, "kgh"),
        },
        "E011": {
            "TT_323011": round(e11.t_c, 1),
            "P_bara": round(e11.p_bara, 2),
            "LI_323D011": round(e11.level_pct, 1),
            "in701_th": th(e11.m_701_kgh),
            "vap011_th": th(e11.m_702_kgh),
            "carb718A_th": th(e11.m_718a_kgh),
            "carb718B_th": th(e11.m_718b_kgh),
            "PIC_323203": faceplate(t.loop("PIC-323203"), 2, 1),
            "FIC_323401": flow_loop(t.loop("FIC-323401"), d3.m_734_kgh, RHO_401_KGM3, "m_kgh"),
            "FIC_323402": flow_loop(t.loop("FIC-323402"), d3.m_791_kgh, RHO_791_KGM3, "m_kgh"),
        },
        "C005": {
            "TT_323C005": round(c5.t_c, 1),
            "sump_head_mm": round(c5.sump_head_m * 1000.0, 1),
            "bot_th": th(c5.m_343_kgh),
            "in756_kgh": round(m_756, 1),
            "in702_kgh": round(m_702, 1),
            "in708_kgh": round(m_708, 1),
            "out343_kgh": round(c5.m_343_kgh, 1),
            "out341_kgh": round(c5.m_341_kgh, 1),
            "closure_kgh": round(m_756 + m_702 + m_708 - c5.m_343_kgh - c5.m_341_kgh, 6),
            "FIC_323418": flow_loop(t.loop("FIC-323418"), e11.m_718b_kgh, RHO_718_KGM3, "m_kgh"),
            "FIC_328405": flow_loop(t.loop("FIC-328405"), d3.m_793_kgh, RHO_401_KGM3, "m_kgh"),
            "LIC_323503": faceplate(t.loop("LIC-323503")),
        },
    }
