"""The stream registry in the console packet: ``STREAMS``, what the stream inspector pops up.

Every record is V1's, built by the port's `ureasim.core.stream` constructors (V1's ``make_stream``
and its PFD-row variants, ported verbatim) on this tick's flows: the synthesis loop's streams on
their units' live vectors, the numbered streams on their PFD rows scaled to the live flow, the
vacuum condensers' vents on their live compositions and their cooling water on their live flows.
V1's literals — each stream's temperature, pressure and density where the registry fixes them —
are `ureasim.data.console_packet`'s. Two V1 choices are kept as V1 made them: 797 is published at
its design flow, and the cooling-water mains at the PFD's.

Source: V1 ``backend/main.py`` 10181-10331.
"""

from __future__ import annotations

from ureasim.core.stream import (
    make_stream,
    make_stream_mass_pct,
    make_stream_mole_pct,
    vent_mole_pct,
)
from ureasim.data.console_packet import (
    CW_MAIN,
    CW_RETURN_P_BARA,
    CW_SUPPLY_P_BARA,
    REACT_OFFGAS_RHO,
    REACT_OVERFLOW_RHO,
    STREAM_PCT,
    STREAM_STATES,
)
from ureasim.data.unit_320 import CO2_T_FEED_C
from ureasim.data.unit_321 import NH3_RHO, P_SYN_DOWN_BAR
from ureasim.data.unit_322e002 import STEAM_P_BARA as HPCC_STEAM_P_BARA
from ureasim.data.unit_322e002 import STEAM_TSAT_C as HPCC_STEAM_TSAT_C
from ureasim.data.unit_322e003 import (
    CCW_P_IN_BARA,
    CCW_P_OUT_BARA,
    CCW_RHO_IN,
    CCW_RHO_OUT,
)
from ureasim.data.unit_322e003 import OFFGAS_RHO as SCRUB_OFFGAS_RHO
from ureasim.data.unit_322f001 import MOTIVE_W
from ureasim.data.unit_323e003 import E003_M797_DES_KGH
from ureasim.data.unit_323e011 import E011_MV_DES_KGH
from ureasim.engine.packet._common import MW_COMP, Tick

__all__ = ["streams"]

_H2O = MW_COMP["H2O"]


def _water(kgh: float) -> dict:
    return {"H2O": kgh / _H2O}


def _numbered(no: str, kgh: float, name: str, src: str, dst: str, phase: str) -> dict:
    """A numbered stream on its PFD row, scaled to the live flow: a vapour row on a mole basis,
    a liquid row on a mass basis (V1's convention)."""
    t_c, p_bara, rho = STREAM_STATES[no]
    make = make_stream_mole_pct if phase == "vapor" else make_stream_mass_pct
    return make(kgh, STREAM_PCT[no], t_c, p_bara, f"{no} {name}", src, dst, phase,
                rho=rho).as_packet()


def _vent(no: str, kgh: float, node, name: str, src: str, dst: str) -> dict:
    """A vacuum condenser's vent on its live composition and temperature."""
    return make_stream_mole_pct(kgh, vent_mole_pct(node.vent_kmolh), node.t_vent_c,
                                STREAM_STATES[no][1], f"{no} {name}", src, dst,
                                "vapor").as_packet()


def streams(t: Tick) -> dict:
    """Every stream V1's inspector can show, by V1's id, in V1's order."""
    res321, drum = t.r("321"), t.units["321"].drum
    ej, strip_step = t.r("322F001"), t.r("322E001")
    st = strip_step.stripper
    hpcc, react = t.r("322E002"), t.r("322R001")
    c = hpcc.holdup.condenser
    sc_step, purge = t.r("322E003"), t.r("HV-322604").valve
    sc, ccw = sc_step.scrubber, t.loops["322E003"][0]
    lag = t.r("322-DISPLAY")
    vac = t.r("324E002-E007")
    v, nodes = vac.streams_kgh, vac.nodes
    feed_kmolh = {k: res321.flow_total_th * 1000.0 * MOTIVE_W[k] / MW_COMP[k] for k in MW_COMP}
    motive_kmolh = {k: res321.motive_nh3_kgh * MOTIVE_W[k] / MW_COMP[k] for k in MW_COMP}
    p_strip = strip_step.p_tube_bara
    m_ccw = t.r("322E003").ccw.m_ccw_kgh
    out = {
        "NH3_FEED": make_stream(feed_kmolh, drum.temperature_c, drum.top_pressure_barg + 1.0,
                                "NH3 ex 309E005", "309E005", "321D003", "liquid", rho=NH3_RHO),
        "PUMP_SUCT": make_stream(feed_kmolh, drum.temperature_c, res321.feed_pressure_barg + 1.0,
                                 "NH3 pump suction header", "321D003", "321P002 A/B", "liquid",
                                 rho=NH3_RHO),
        "HP_DISCH": make_stream(motive_kmolh, res321.discharge_t_c, P_SYN_DOWN_BAR,
                                "HP NH3 discharge (motive)", "321P002 A/B", "322F001", "liquid",
                                rho=NH3_RHO),
        "CARB_RECYCLE": make_stream(sc.overflow_kmolh, sc.t_overflow_c, sc.p_overflow_bara,
                                    "Carbamate recycle (322E003 overflow)", "322E003",
                                    "322F001", "liquid"),
        "EJ_DISCH": make_stream({k: ej.comp_kgh[k] / MW_COMP[k] for k in MW_COMP}, ej.t_c,
                                ej.p_bara, "Ejector discharge (carbamate liq.)", "322F001",
                                "322E002", "liquid", rho=ej.rho),
        "CO2_FEED": make_stream(st.co2_feed_kmolh, CO2_T_FEED_C, t.r("320K002").line_bara,
                                "CO2 feed gas", "320K002", "322E001", "gas"),
        "STRIP_TOP": make_stream(st.top_kmolh, st.t_top, p_strip, "Stripper top gas", "322E001",
                                 "322E002", "gas"),
        "STRIP_BOT": make_stream(st.bot_kmolh, st.t_bot, p_strip, "Stripper bottom solution",
                                 "322E001", "LV-322501", "liquid"),
        "HPCC_PROD": make_stream(c.feed_kmolh, c.t_prod, lag.pi_322e002_bara,
                                 "HPCC two-phase product", "322E002", "322R001", "two-phase"),
        "HPCC_STEAM": make_stream(_water(c.steam_kgh), HPCC_STEAM_TSAT_C, HPCC_STEAM_P_BARA,
                                  "LP steam (shell side)", "322E002 shell", "LP header", "vapor"),
        "HPCC_COND": make_stream(_water(c.steam_kgh), HPCC_STEAM_TSAT_C, HPCC_STEAM_P_BARA,
                                 "BFW/condensate feed", "322D001 A/B", "322E002 shell", "liquid"),
        "REACT_OVERFLOW": make_stream(react.overflow_kmolh, react.t_overflow_c, react.p_bara,
                                      "Reactor overflow (urea soln.)", "322R001", "322E001",
                                      "liquid", rho=REACT_OVERFLOW_RHO),
        "REACT_OFFGAS": make_stream(react.reaction.offgas_kmolh, react.t_offgas_c,
                                    react.p_offgas_bara, "Reactor off-gas", "322R001", "322E003",
                                    "vapor", rho=REACT_OFFGAS_RHO),
        "SCRUB_OFFGAS": make_stream(sc.offgas_kmolh, sc.t_offgas_c, sc.p_offgas_bara,
                                    "HP scrubber off-gas (to HV-322604)", "322E003", "HV-322604",
                                    "vapor", rho=SCRUB_OFFGAS_RHO),
        "SCRUB_OFFGAS_LP": make_stream(purge.comp_kmolh, purge.t_out_c, purge.p_out_bara,
                                       "HP scrubber off-gas (LP, JT-cooled)", "HV-322604",
                                       "322C001", "vapor"),
        "CCW_SUPPLY": make_stream(_water(m_ccw), ccw.tic_pv, CCW_P_IN_BARA,
                                  "CCW supply (shell side, cold)", "329P006 A/B", "322E003",
                                  "liquid", rho=CCW_RHO_IN),
        "CCW_RETURN": make_stream(_water(m_ccw), sc.t_ccw_out_c, CCW_P_OUT_BARA,
                                  "CCW return (shell side, warm)", "322E003", "329P006 A/B",
                                  "liquid", rho=CCW_RHO_OUT),
    }
    out = {k: rec.as_packet() for k, rec in out.items()}
    c5, d3 = t.r("323C005"), t.r("328D003")
    m_702 = E011_MV_DES_KGH + (t.r("323E011").m_702_kgh - E011_MV_DES_KGH)
    out.update({
        "S0204": make_stream(purge.comp_kmolh, purge.t_out_c, purge.p_out_bara,
                             "204 HP off-gas", "HV-322604", "322C001", "vapor").as_packet(),
        "S0341": _numbered("341", c5.m_341_kgh, "absorber vent", "323C005", "328V001", "vapor"),
        "S0343": _numbered("343", c5.m_343_kgh, "ammonia water", "323C005", "328D003 Comp II",
                           "liquid"),
        "S0702": _numbered("702", m_702, "flash-condenser gas", "323D011", "323C005", "vapor"),
        "S0703": _numbered("703", v["703"], "condenser-I inlet", "705 + 790", "324E002", "vapor"),
        "S0705": _numbered("705", v["705"], "evaporator-I vapor", "324F001", "324E002", "vapor"),
        "S0706": _vent("706", v["706"], nodes["324E002"], "condenser-I gas", "324E002",
                       "324F002"),
        "S0708": _numbered("708", v["708"], "ejector-I discharge", "324F002", "323C005", "vapor"),
        "S0709": _numbered("709", v["709"], "condenser-II inlet", "324F003", "324E005", "vapor"),
        "S0712": _vent("712", v["712"], nodes["324E005"], "condenser-II gas", "324E005",
                       "324F004"),
        "S0714": _numbered("714", v["714"], "ejector-II discharge", "324F004", "324E006",
                           "vapor"),
        "S0715": _vent("715", v["715"], nodes["324E006"], "condenser-III gas", "324E006",
                       "324F005"),
        "S0717": _numbered("717", v["717"], "ejector-III discharge", "324F005", "324E007",
                           "vapor"),
        "S0719": _numbered("719", v["719"], "condenser-I condensate", "324E002",
                           "328D003 Comp I", "liquid"),
        "S0720": _numbered("720", v["720"], "condenser-II condensate", "324E005",
                           "328D003 Comp I", "liquid"),
        "S0721": _numbered("721", v["721"], "condenser-III condensate", "324E006",
                           "328D003 Comp I", "liquid"),
        "S0722": _vent("722", v["722"], nodes["324E007"], "final vacuum vent", "324E007",
                       "atmosphere"),
        "S0744": _numbered("744", d3.m_744_kgh, "absorber-pump suction", "328D003 Comp I",
                           "322P002", "liquid"),
        "S0755": _numbered("755", d3.m_744_kgh, "cooled absorber feed", "322E006", "322C001",
                           "liquid"),
        "S0756": _numbered("756", t.r("322C001").m_756_kgh, "LP-absorber solution", "322C001",
                           "323C005", "liquid"),
        "S0759": _numbered("759", v["759"], "condenser-IV condensate", "324E007",
                           "328D003 Comp I", "liquid"),
        "S0783": _numbered("783", t.r("324E003").false_air_kgh, "stage-II false air",
                           "atmosphere", "PV-324203", "vapor"),
        "S0784": _numbered("784", t.r("324E001").false_air_kgh, "stage-I false air",
                           "atmosphere", "PV-324202", "vapor"),
        "S0797": _numbered("797", E003_M797_DES_KGH, "LP-absorber vent", "322C001",
                           "PV-322201", "vapor"),
    })
    for no, dst in (("924", "324F002"), ("927", "324F004"), ("929", "324F005")):
        t_c, p_bara, _ = STREAM_STATES[no]
        out["S0" + no] = make_stream(_water(v[no]), t_c, p_bara, f"{no} ejector motive",
                                     "LP steam", dst, "vapor").as_packet()
    t_c, p_bara, rho = STREAM_STATES["954"]
    out["S0954"] = make_stream(_water(t.operator["FIC-322404"]), t_c, p_bara,
                               "954 process condensate", "process-condensate header", "322C001",
                               "liquid", rho=rho).as_packet()
    for tag, supply, ret in (("324E002", "1014", "1015"), ("324E005", "1016", "1017"),
                             ("324E006", "1018", "1019"), ("324E007", "1020", "1021")):
        node = nodes[tag]
        out["S" + supply] = make_stream(_water(node.cw_flow_kgh), node.cw_in_c, CW_SUPPLY_P_BARA,
                                        supply + " cooling-water supply", "1001 header", tag,
                                        "liquid").as_packet()
        out["S" + ret] = make_stream(_water(node.cw_flow_kgh), node.cw_out_c, CW_RETURN_P_BARA,
                                     ret + " cooling-water return", tag, "1051 header",
                                     "liquid").as_packet()
    for no, name, src, dst in (("1001", "main CW supply", "cooling towers", "CW consumers"),
                               ("1051", "main CW return", "CW consumers", "cooling towers")):
        kgh, t_c, p_bara = CW_MAIN[no]
        out["S" + no] = make_stream(_water(kgh), t_c, p_bara, f"{no} {name}", src, dst,
                                    "liquid").as_packet()
    return out
