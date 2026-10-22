"""V1 <-> V1.1 for the synthesis loop's engine glue — `engine.plant.synthesis`, `synthesis_loop`.

What is being proved
--------------------
V1's ``step_sim`` cannot execute (handoff A-12), so the glue V1 writes inline around its synthesis
units — sections 2 to 5, 34, 36 and 37's loop pressure — is TRANSCRIBED below line for line
(`_v1_tick`), and everything it calls that V1 defines at module level is V1's own, EXECUTED out of
``main.py`` through `lift`, on V1's boot pin (`data.synthesis_pin`, itself proven to be V1's cache):
the ejector, the stripper, the condenser, the reactor, the scrubber, ``ej_spindle_phi``,
``react_nc_ratio``, ``tsat_steam``, ``urea_soln_rho``, ``_f_flow``, V1's ``reactor`` module and
``hydraulics``' relief law. Three units the transcription runs as the port's, each proven against V1
by its own equivalence test with its own decided switches: unit 321 and the CO2 line (sections 1-2,
`test_feed_equivalence`, `test_co2_line_equivalence`), the stripper's sump (B-46,
`test_stripper_sump_equivalence`) and HV-322604 (B-19, `test_purge_valve_equivalence`).

The port runs inside the whole plant's scheduler; the transcription runs beside it on the same
tick, handed what the rest of the plant gave the port: 329D005's and 322D001A/B's pressures of the
tick before, 323P001's 308 (the tick before's and this tick's) and 322C001's pressure. With the
switches ``decided`` on, every state the glue integrates is ``==`` the port's on every tick:

  * "A-16" — the loop relieves through 322R001's SV32251 / SV32252 on their certified capacity
    (decision 32); V1 through one assumed SV-32201;
  * "A-17" — HV-322604 discharges against 322C001's pressure of the tick before (decision 29); V1
    against 4.0 bar a;
  * "B-75" — PT-329201's residual credit scales with the reactor's load ratio s; V1's does not;
  * "B-76" — the recondensed backlog returns to 322E003's sump on the next tick; V1 deletes it;
  * "B-77" — PT-329201 is the loop's vapour inventory on the vessels' 241.7 m3 and the reactor
    liquor's buffering, the liquid the model holds no longer pressure and the backlog no
    pseudo-mass (decided 2026-10-09); V1 integrates the whole boundary on 1500 kg/bar with the
    backlog's G_ph . m_vap,net;
  * "B-78" — 322E003's full sump holds its excess back in the scrubber, the forward-carbamate pulse
    is drawn from the sump, the mushy zone throttles the sump's line to 322F001; V1 deletes the
    excess, draws the pulse from nowhere and throttles the overflow into the sump;
  * "B-88" — trip 22.2 trips 320K002 with XV-322902 and takes the boundary's CO2 demand to zero;
    V1 shuts XV-322902 and leaves the machine delivering;
  * "A-12" — trips 21.2, 21.8 and 21.10 as AC4's application software executes them (PC21: live
    flags on the pumps running, 323P001, the CO2 to the stripper, XV-321901 / XV-322901 and the
    sub-cooling; 21.2 resets the two valves, each pump's flag stops its machine), a machine's
    fault stopping it on its own protection (decided 2026-10-09); V1's 21.2 on 321D003 and the
    sub-cooling, 21.4 on the CO2 lost and 21.8 / 21.10 on a pump's fault, latched;
  * "B-91" — the loop's liquor above its bubble point (`liquor_saturation`, decided 2026-10-10):
    PI-322E002 of the tick before against PT-329201 sets the fraction 322E002's melt holds and the
    reactor liquor's buffering; 322E003 condenses on its own sump liquor's bubble pressure of the
    tick before and, at a full sump, no more than drains from it (decided 2026-10-14); V1 condenses
    its split whatever the pressure. With the switch on, 322E002 and 322E003 run as the port's
    (`carbamate_condenser` and `scrubber`, proven V1's at a fraction of 1 by
    `test_carbamate_condenser_equivalence` and `test_scrubber_equivalence`), as unit 321 and the
    stripper's sump do;
  * "B-92" — 322R001's nodes held at the liquor's bubble point at the live loop pressure, the excess
    heat flashing the overflow's volatiles into the off-gas (`reactor_boil.node_boil`), and the
    kinetics' residence time on the larger of the liquid that left the column and the liquid that
    entered its holdup on the tick before (decided 2026-10-14); V1's nodes have no ceiling and its
    residence runs on the outflow alone, so a filling reactor reacts for ever.

The A's are inert at the design and under the scenarios here, the B's act wherever the loop moves;
`test_synthesis_loop_decided_equivalence.py` drives each one where it acts, both ways.
"""

from __future__ import annotations

import importlib.util
import math
from types import SimpleNamespace

import pytest

from ureasim.data import synthesis_pin as pin
from ureasim.data.unit_322f001 import HYDRAULIC_FRAC_MAX
from ureasim.control.interlocks import Unit21TripInputs
from ureasim.data.unit_322_loop import (
    SV32251_COUNT,
    SV32251_K,
    SV32251_RESEAT_BARA,
    SV32251_SET_BARA,
    SV32251_Z_REL,
    TRIP_21_2_FY_L2_FRAC,
    TRIP_21_8_PDY_L2_BAR,
)
from ureasim.engine.plant import build_plant
from ureasim.engine.plant.synthesis import design_feed_station
from ureasim.engine.plant.synthesis_loop import _unit21_trips
from ureasim.engine.scheduler import Scheduler
from ureasim.units.synthesis.ccw_loop import V1_FV_329409, CcwLoop
from ureasim.units.synthesis.co2_line import CO2FeedLine, vent_pressure_loop
from ureasim.units.synthesis.carbamate_condenser import carbamate_condenser_322e002
from ureasim.units.synthesis.condenser_holdup import E002_SPAN_KG
from ureasim.units.synthesis.liquor_saturation import saturation_fraction
from ureasim.units.synthesis.loop_pressure import (
    B_207_PER_BAR,
    R_BAR_M3,
    SV32251_AREA_M2,
    Z_GAS_DES,
    liquid_growth,
    loop_liquid,
    vapour_capacity_kg_per_bar,
)
from ureasim.units.synthesis.purge_valve import purge_valve_322604
from ureasim.units.synthesis.reactor_boil import VOLATILES, node_boil
from ureasim.units.synthesis.scrubber import (
    LIQUOR_DP_DES_BAR,
    liquor_bubble_p_bara,
    scrubber_322e003,
)
from ureasim.units.synthesis.stripper_level import BottomLevelLoop
from ureasim.units.synthesis.stripper_sump import SUMP_SPAN_KG, StripperSump
from tests.equivalence import b6_switch, b9_switch, b16_switch, b18_switch, ccw_tuning_switch
from tests.equivalence.v1_loader import V1_BACKEND, lift, load, v1_available, v1_service

pytestmark = pytest.mark.skipif(not v1_available(), reason="V1 source tree not present")

ALL = frozenset({"A-12", "A-16", "A-17", "B-75", "B-76", "B-77", "B-78", "B-88", "B-91",
                 "B-92"})
DT = 0.1

V1_NAMES = [
    "ejector_322f001", "ej_spindle_phi", "stripper_322e001", "hpcc_322e002", "react_322r001",
    "scrub_322e003", "react_nc_ratio", "scrub_cond_t_c", "_f_flow", "urea_soln_rho", "tsat_steam",
    "_rederive_react_bulk_anchors",
    "EJ_P_SUCTION_BARA", "EJ_P_DISCH_BARA", "SYN_P_DES_BARA", "SCRUB_LEVEL_NLL_PCT",
    "STRIP_FEED207_T_C", "STRIP_P_DES_BARA", "STRIP_FEED207_KMOLH", "REACT_OVERFLOW_RHO",
    "REACT_OVERFLOW_RHO_DES_LIVE", "MW_COMP", "REACT_TAU_REC_MIN", "REACT_NC_LOOP_GAIN",
    "RATIO_PV_DES", "REACT_FRESH_FRAC", "HPCC_P_DES_BARA", "HPCC_LIQ_DES_KGH",
    "REACT_OFFGAS_P_BARA", "REACT_OFFGAS_DES", "REACT_OFFGAS_T_C", "REACT_TAU_NODE_MIN",
    "REACT_OFFGAS_GAMMA", "REACT_LIQ_H_M", "_react_mdot_kgh", "REACT_HIC605_DES_PCT",
    "REACT_WEIR_CREST_M", "REACT_WEIR_CW", "REACT_FWD_TAU_MIN", "REACT_FWD_GAIN",
    "_react_area_m2", "REACT_LEVEL_NLL_PCT", "REACT_LEVEL_DES_M", "REACT_LT_SPAN_M",
    "HPCC_LEVEL_NLL_PCT", "HPCC_TAU_FILL_MIN", "SCRUB_CCW_KGH_DES", "SCRUB_FV409_DES_PCT",
    "FIC_329409_TAU_S", "FIC_329409_KC", "FIC_329409_TI", "SCRUB_TV005_DES_PCT",
    "SCRUB_CCW_T_IN_DES", "TIC_329005_LOAD_GAIN", "SCRUB_CCW_T_OUT_DES", "TIC_329005_TAU_S",
    "TIC_329005_KC", "TIC_329005_TI", "SCRUB_OVERFLOW_T_C", "SCRUB_HOLDUP_NLL_KG",
    "SCRUB_HOLDUP_MAX_KG", "SCRUB_SWELL_PCT_MAX", "SCRUB_SWELL_NOISE_PCT",
    "SCRUB_SWELL_NOISE_T1_S", "SCRUB_SWELL_NOISE_T2_S", "R3232_E003_M308_DES", "SYN_P_TAU_MIN",
    "SYN_LOOP_C_KG_PER_BAR", "SYN_P_PHASE_GAIN", "SYN_LOOP_RESID_DES_KGH", "STRIP_LEVEL_SP_DES",
    "SYN_PSV_SET_BARA", "SYN_PSV_RESEAT_BARA", "SYN_PSV_AREA_M2", "SYN_PSV_T_REL_K",
    "SCRUB_HV604_MW_DES", "SCRUB_HV604_P_OUT", "SYN_PSV_K_GAMMA", "SYN_PSV_Z", "SYN_PSV_KD",
    "SYN_PSV_KB", "SYN_PSV_KC", "SYN_P_TRIP_BARA", "SYN_P_TRIP_RESET_BARA", "CO2_DES_KGH",
    "HPCC_T_PROD_DES_C", "HPCC_FRAC_GAS_DES", "EJ_CARB_FRAC", "REACT_OVERFLOW_DES",
    "STRIP_STEAM_T_DES_C", "STRIP_P_DES_BARA", "EJ_MOTIVE_NH3_DES", "EJ_MOTIVE_T_DES_C",
    "EJ_OPEN_DES", "HPCC_CP_GAS", "HPCC_STEAM_TSAT_C",
    "REACT_OVERFLOW_T_C", "REACT_KIN_CAL",
]


def _private_reactor():
    """V1's ``reactor.py`` as a module of this test's own, so pinning its kinetics touches no
    other test's copy."""
    spec = importlib.util.spec_from_file_location("v1_reactor_pinned", V1_BACKEND / "reactor.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def v1():
    """V1's synthesis units and constants, executed out of ``main.py``, on V1's boot pin."""
    return pinned_v1()


def pinned_v1() -> dict:
    """V1's synthesis units and constants on V1's boot pin (``_apply_pin``, ``main.py``
    12410-12460)."""
    rmod = _private_reactor()
    # TT-322002 on 165 C (B-16), HV-322604 anchored at 72 % (B-18), the standard atmosphere and
    # gravity (B-6, B-7) and the tempered water's loops on the DCS table's rows (decision 10's
    # class), all decided: V1's statements derive what is anchored on them from the seed.
    switches = (b16_switch, b18_switch, b6_switch, ccw_tuning_switch)
    names, seed = list(V1_NAMES), {
        "math": math, "reactor": rmod, "jet_pump": load("jet_pump"),
        "h0_enthalpy": load("gap_g6_h0_enthalpy"), "thermo_service": v1_service(),
        "iapws_if97": load("iapws_if97"), "hydraulics": load("hydraulics"),
        "state": SimpleNamespace(p_syn_bara=140.7)}
    for switch in switches:
        names, seed = switch.names(names), switch.seed(seed)
    ns = lift(names, seed=seed)
    b9_switch.switch(ns)                      # 322E001's one flood ceiling (B-9, decided)
    # 322E002's UA: V1's boot line, its synthetic design call, on the switched namespace — the
    # cache's value (``pin.HPCC_UA_KJHK``) was solved on V1's 1.013 bar and 9.81 (B-6, B-7).
    gas = ns["stripper_322e001"](ns["CO2_DES_KGH"] / 1000.0, ns["STRIP_STEAM_T_DES_C"],
                                 ns["STRIP_P_DES_BARA"])
    liq = ns["ejector_322f001"](ns["EJ_MOTIVE_NH3_DES"], ns["EJ_MOTIVE_T_DES_C"],
                                ns["EJ_OPEN_DES"])
    synthetic = ns["hpcc_322e002"](gas, liq, gate=1.0)
    ns["HPCC_UA"] = -synthetic["m_dot"] * ns["HPCC_CP_GAS"] * math.log(
        (ns["HPCC_T_PROD_DES_C"] - ns["HPCC_STEAM_TSAT_C"])
        / (synthetic["T_adb"] - ns["HPCC_STEAM_TSAT_C"]))
    ns["HPCC_LIQ_DES_LIVE"] = pin.HPCC_LIQ_DES_LIVE_KGH
    ns["HPCC_NC_DES_LIVE"] = pin.HPCC_NC_DES_LIVE
    ns["REACT_TEAR_DES"] = {k: pin.REACT_TEAR_DES_KMOLH.get(k, 0.0) for k in ns["MW_COMP"]}
    ns["REACT_L_FEED_DES"] = pin.REACT_L_FEED_DES
    ns["REACT_X_DES"] = pin.REACT_X_DES
    ns["REACT_KIN_ANCHOR"] = {"T_node": list(pin.REACT_ANCHOR_T_NODES_C),
                              "lvl": pin.REACT_ANCHOR_LEVEL_FRAC,
                              "vdot": pin.REACT_ANCHOR_VDOT_M3H,
                              "m_feed": pin.REACT_ANCHOR_M_FEED_KGH}
    ns["REACT_CP_MELT"] = pin.REACT_CP_MELT_KJKGK
    ns["REACT_NODE_SS_DES"] = list(pin.REACT_NODE_SS_DES_C)
    ns["_rederive_react_bulk_anchors"]()
    rmod.A2_PRE = pin.REACT_A2_PRE_PER_H
    rmod.KEQ_OV_REF = pin.REACT_KEQ_OV_REF
    rmod.T_REF_K = pin.REACT_T_REF_K
    rmod.BIU_A_PRE = pin.REACT_BIURET_A
    ns["REACT_KIN_CAL"] = {"A2": rmod.A2_PRE, "Keq_ov_ref": rmod.KEQ_OV_REF,
                           "T_ref_K": rmod.T_REF_K, "biu_A": rmod.BIU_A_PRE}
    return ns


# ======================================================================================
# The transcription
# ======================================================================================

def _v1_state(v1):
    """V1's ``State`` for the loop (``main.py`` 6413-6590), with the port's units for sections 1-2,
    the sump and HV-322604."""
    r = v1["reactor"]
    return SimpleNamespace(
        line=CO2FeedLine(), pic=vent_pressure_loop(),
        station=design_feed_station(), sump=StripperSump(hold_full=False), lic=BottomLevelLoop(),
        co2_raw_th=v1["CO2_DES_KGH"] / 1000.0,
        HIC_322602=74.0, HIC_322605=v1["REACT_HIC605_DES_PCT"],
        HIC_322604=v1["SCRUB_HIC604_DES_PCT"],
        XV_322903=True, P329P006A=True, P329P006B=False,
        p_syn=v1["SYN_P_DES_BARA"], syn_vap_excess_kg=0.0, syn_psv_open=False,
        react_overflow_kmolh=dict(v1["REACT_OVERFLOW_DES"]), react_L_feed=r.L0_DES,
        react_W_feed=r.W0_DES, react_T_node=list(v1["REACT_NODE_SS_DES"]),
        react_T_overflow=v1["REACT_OVERFLOW_T_C"], react_T_offgas=v1["REACT_OFFGAS_T_C"],
        react_L_rec=r.L0_DES, react_W_rec=r.W0_DES, react_level_pct=v1["REACT_LEVEL_NLL_PCT"],
        react_lt322504_pct=v1["REACT_LEVEL_NLL_PCT"], react_m_liq=v1["REACT_M_LIQ_DES"],
        react_m_in_lag=0.0, react_fwd_wash=0.0, react_m_in_prev=v1["_react_mdot_kgh"],
        hpcc_level_pct=v1["HPCC_LEVEL_NLL_PCT"],
        hpcc_phi=dict(v1["HPCC_FRAC_GAS_DES"]), hpcc_tprod=v1["HPCC_T_PROD_DES_C"],
        hpcc_pbub=v1["HPCC_P_DES_BARA"],
        scrub_holdup_kg=v1["SCRUB_HOLDUP_NLL_KG"], scrub_level_pct=v1["SCRUB_LEVEL_NLL_PCT"],
        y_scrub_ovf=dict(v1["EJ_CARB_FRAC"]), scrub_held_kg=0.0, scrub_mushy=1.0, recond_kgh=0.0,
        scrub_pbub=v1["SYN_P_DES_BARA"],
        FIC={"mode": "AUTO", "op": v1["SCRUB_FV409_DES_PCT"], "sp": v1["SCRUB_CCW_KGH_DES"] / 1e3,
             "pv": v1["SCRUB_CCW_KGH_DES"] / 1000.0, "pv_prev": v1["SCRUB_CCW_KGH_DES"] / 1000.0},
        TIC={"mode": "AUTO", "op": v1["SCRUB_TV005_DES_PCT"], "sp": v1["SCRUB_CCW_T_IN_DES"],
             "pv": v1["SCRUB_CCW_T_IN_DES"], "pv_prev": v1["SCRUB_CCW_T_IN_DES"]},
        ac4=_unit21_trips(),
        trips={"21_2": False, "21_4": False, "21_8": False, "21_10": False, "22_2": False},
        latched={"21_2": False, "21_4": False, "21_8": False, "21_10": False, "22_2": False})


def _v1_tick(v1, s, x, decided):
    """One tick of V1's synthesis glue (``main.py`` 7281-8182, 10086-10171, 10345-10445)."""
    dt, r, mw = DT, v1["reactor"], v1["MW_COMP"]
    liq_0 = (s.react_m_liq, s.scrub_holdup_kg + s.scrub_held_kg, s.hpcc_level_pct,
             s.sump.level_pct)
    v1["state"].p_syn_bara = s.p_syn
    # ----- sections 1-2: the CO2 line and unit 321, the port's (their own tests) -----------
    line = s.line.step(s.pic, s.co2_raw_th, s.p_syn, dt)
    feed = s.station.step(line.feed_th, dt)
    F_CO2_syn_th, motive = line.feed_to_loop_th, feed.motive_nh3_kgh
    disch_open = bool(s.station.xv_322901_open)
    # ----- 322F001 (7504-7521) ------------------------------------------------------------
    scrub_lvl_frac = s.scrub_level_pct / v1["SCRUB_LEVEL_NLL_PCT"]
    if "B-78" in decided:       # the mushy zone on the sump's line to the suction
        scrub_lvl_frac = min(max(scrub_lvl_frac, 0.0), HYDRAULIC_FRAC_MAX) * s.scrub_mushy
    _ej_p_suct = s.p_syn + (v1["EJ_P_SUCTION_BARA"] - v1["SYN_P_DES_BARA"])
    _ej_p_disch = s.p_syn + (v1["EJ_P_DISCH_BARA"] - v1["SYN_P_DES_BARA"])
    ej = v1["ejector_322f001"](motive, feed.discharge_t_c, s.HIC_322602,
                               scrub_level_frac=scrub_lvl_frac, xv903_open=bool(s.XV_322903),
                               carb_frac=s.y_scrub_ovf, p_suct_bara=_ej_p_suct,
                               p_disch_bara=_ej_p_disch)
    phi_fwd = feed.phi_forward
    # ----- 322E001 (7542-7586) and its sump (the port's) ----------------------------------
    T_steam_live = v1["tsat_steam"](x["p_mp"])
    T_feed_live = v1["STRIP_FEED207_T_C"] + (s.react_T_overflow - r.T0_DES_C)
    dP_des_strip = v1["STRIP_P_DES_BARA"] - v1["SYN_P_DES_BARA"]
    m_strip_live = max(sum(s.react_overflow_kmolh.get(k, 0.0) * mw[k] for k in mw), 1e-6)
    m_strip_des = max(sum(v1["STRIP_FEED207_KMOLH"].get(k, 0.0) * mw[k] for k in mw), 1e-6)
    w_urea_strip = (s.react_overflow_kmolh.get("Urea", 0.0) * mw["Urea"]) / m_strip_live
    rho_live_strip = v1["urea_soln_rho"](w_urea_strip, T_feed_live, v1["REACT_OVERFLOW_RHO"])
    dP_strip_live = dP_des_strip * (v1["REACT_OVERFLOW_RHO_DES_LIVE"]
                                    / max(rho_live_strip, 1e-6)) * (m_strip_live / m_strip_des) ** 2
    P_strip_live = s.p_syn + dP_strip_live
    strip = v1["stripper_322e001"](F_CO2_syn_th, T_steam_live, P_strip_live,
                                   overflow_kmolh=s.react_overflow_kmolh, L_feed=s.react_L_feed,
                                   W_feed=s.react_W_feed, T_feed_C=T_feed_live,
                                   strip_level_pct=s.sump.level_pct)
    sump = s.sump.step(s.lic, strip["bot_kgh"], strip["T_bot"], strip["T_steam"],
                       strip["top_kmolh"], strip["top_MW"], s.p_syn, strip["bot_mass_pct"], dt)
    # ----- 322E002 (7695-7705) -------------------------------------------------------------
    T_shell_lp = v1["tsat_steam"](x["p_lp"])
    sat = saturation_fraction(s.hpcc_pbub, s.p_syn) if "B-91" in decided else 1.0
    if sat < 1.0:   # the melt above its bubble point (B-91): the port's condenser
        hpcc = _hpcc_port(strip, ej, T_shell_lp, s, sat)
    else:
        hpcc = v1["hpcc_322e002"](strip, ej, t_shell=T_shell_lp, gate=1.0,
                                  t_prod_prev=s.hpcc_tprod, p_loop=s.p_syn, phi_prev=s.hpcc_phi,
                                  dt=dt)
    s.hpcc_tprod = hpcc["T_prod"]
    s.hpcc_phi = hpcc["phi_film"]
    s.hpcc_pbub = hpcc["P_bub"]
    # ----- 322R001 (7722-7821) --------------------------------------------------------------
    a_rec = dt / (v1["REACT_TAU_REC_MIN"] * 60.0)
    L_fresh = r.L0_DES * (1.0 + v1["REACT_NC_LOOP_GAIN"] * (feed.ratio_pv / v1["RATIO_PV_DES"]
                                                             - 1.0))
    co2_fd = hpcc["feed_kmolh"].get("CO2", 0.0)
    W_inst = (hpcc["feed_kmolh"].get("H2O", 0.0) / co2_fd) if co2_fd > 0.0 else r.W0_DES
    s.react_L_rec += a_rec * (L_fresh - s.react_L_rec)
    s.react_W_rec += a_rec * (W_inst - s.react_W_rec)
    L_blend = v1["REACT_FRESH_FRAC"] * L_fresh + (1.0 - v1["REACT_FRESH_FRAC"]) * s.react_L_rec
    W_blend = v1["REACT_FRESH_FRAC"] * W_inst + (1.0 - v1["REACT_FRESH_FRAC"]) * s.react_W_rec
    _m_through = sum(s.react_overflow_kmolh.get(k, 0.0) * mw[k] for k in mw)
    if "B-92" in decided:   # the liquid entering a filling reactor (`reactor_inventory`)
        _m_through = max(_m_through, s.react_m_in_prev)
    _react_vdot_live = max(_m_through / max(r.liquid_density(sum(s.react_T_node) / 4.0), 1e-6),
                           1e-6)
    react = v1["react_322r001"](hpcc, F_CO2_syn_th, s.HIC_322605, L_drive=L_blend,
                                W_drive=W_blend, t_nodes_c=s.react_T_node,
                                level_frac=s.react_level_pct / 100.0, vdot_m3h=_react_vdot_live)
    dP_des_react = s.p_syn - v1["HPCC_P_DES_BARA"]
    m_react_live = max(sum(react["feed_kmolh"].get(k, 0.0) * mw[k] for k in mw), 1e-6)
    m_react_des = v1["HPCC_LIQ_DES_LIVE"] if v1["HPCC_LIQ_DES_LIVE"] else v1["HPCC_LIQ_DES_KGH"]
    w_urea_react = (react["feed_kmolh"].get("Urea", 0.0) * mw["Urea"]) / m_react_live
    rho_live_react = v1["urea_soln_rho"](w_urea_react, hpcc["T_prod"], v1["REACT_OVERFLOW_RHO"])
    dP_react_live = dP_des_react * (v1["REACT_OVERFLOW_RHO"] / max(rho_live_react, 1e-6)) \
        * (m_react_live / max(m_react_des, 1e-6)) ** 2
    react["P_bara"] = hpcc["P_bub"] + dP_react_live
    dP_des_og = v1["REACT_OFFGAS_P_BARA"] - v1["SYN_P_DES_BARA"]
    m_og_live = max(sum(react["offgas_kmolh"].get(k, 0.0) * mw[k] for k in mw), 1e-6)
    m_og_des = max(sum(v1["REACT_OFFGAS_DES"].get(k, 0.0) * mw[k] for k in mw), 1e-6)
    _n_og_live = max(sum(react["offgas_kmolh"].get(k, 0.0) for k in mw), 1e-9)
    _n_og_des = max(sum(v1["REACT_OFFGAS_DES"].get(k, 0.0) for k in mw), 1e-9)
    _mw_og_live = m_og_live / _n_og_live
    _mw_og_des = sum(v1["REACT_OFFGAS_DES"].get(k, 0.0) * mw[k] for k in mw) / _n_og_des
    _rho_fac_og = (_mw_og_des / max(_mw_og_live, 1e-9)) \
        * ((s.react_T_offgas + 273.15) / (v1["REACT_OFFGAS_T_C"] + 273.15))
    react["P_offgas"] = s.p_syn + dP_des_og * _rho_fac_og * (m_og_live / m_og_des) ** 2
    s.react_L_feed = react["L_feed"]
    s.react_W_feed = react["W_feed"]
    conv_fac = react["X_conv"] / v1["REACT_X_DES"]
    _m_ov_live = max(sum(react["overflow_kmolh"].get(k, 0.0) * mw[k] for k in mw), 1.0e-6)
    _mcp_live = _m_ov_live * v1["REACT_CP_MELT"]
    dT_rxn = [q / _mcp_live for q in react["q_nodes_kjh"]]
    T_old = list(s.react_T_node)
    T_up = hpcc["T_prod"]
    flow_frac = max(min(max(react["co2_scale"], 0.0), 1.0), 1.0e-3)
    new_T, taus = [], []
    for n in range(4):
        tau_n = (v1["REACT_TAU_NODE_MIN"][n] * 60.0 / flow_frac) if flow_frac > 1.0e-9 \
            else float("inf")
        new_T.append(T_old[n] + r.node_dTdt(T_old[n], T_up, dT_rxn[n], tau_n, flow_frac) * dt)
        taus.append(tau_n)
        T_up = T_old[n]
    if "B-92" in decided:   # the liquor at its bubble point (`reactor_boil`, decided 2026-10-14)
        boil = node_boil(new_T, s.p_syn, _mcp_live, taus, react["overflow_kmolh"], dt)
        if boil.frac > 0.0:
            for k in VOLATILES:
                react["overflow_kmolh"][k] = (react["overflow_kmolh"].get(k, 0.0)
                                              - boil.flash_kmolh[k])
                react["offgas_kmolh"][k] = (react["offgas_kmolh"].get(k, 0.0)
                                            + boil.flash_kmolh[k])
        new_T = list(boil.t_nodes_c)
    s.react_T_node = new_T
    s.react_T_overflow = new_T[3]
    s.react_T_offgas = new_T[3] + v1["REACT_OFFGAS_GAMMA"] * (s.react_T_overflow - new_T[3])
    # ----- section 4: the holdup (7869-7959), LT-322E002 (7970-7987) ------------------------
    T_bulk_react = sum(new_T) / 4.0
    level_m_react = v1["REACT_LIQ_H_M"] * s.react_level_pct / 100.0
    m_ov_split_kgh = sum(react["overflow_kmolh"][k] * mw[k] for k in react["overflow_kmolh"])
    m_surge_kgh = m_ov_split_kgh - v1["_react_mdot_kgh"]
    s.react_m_in_lag += a_rec * (m_surge_kgh - s.react_m_in_lag)
    m_in_kgh = (v1["_react_mdot_kgh"] + v1["REACT_FRESH_FRAC"] * m_surge_kgh
                + (1.0 - v1["REACT_FRESH_FRAC"]) * s.react_m_in_lag)
    m_out_kgh = r.outlet_line_outflow_kgph(level_m_react, v1["_react_mdot_kgh"], s.HIC_322605,
                                           v1["REACT_HIC605_DES_PCT"], v1["REACT_WEIR_CREST_M"],
                                           v1["REACT_WEIR_CW"], T_bulk_react)
    _phi_sp_theta = max(v1["ej_spindle_phi"](s.HIC_322602), 1e-6)
    _fwd_drive_kgh = ej["suction_kgh"] * (1.0 - 1.0 / _phi_sp_theta)
    _a_fwd = dt / (v1["REACT_FWD_TAU_MIN"] * 60.0)
    s.react_fwd_wash += _a_fwd * (_fwd_drive_kgh - s.react_fwd_wash)
    m_fwd_carb_kgh = v1["REACT_FWD_GAIN"] * (_fwd_drive_kgh - s.react_fwd_wash)
    if "B-78" in decided:       # the pulse drawn from 322E003's sump
        m_fwd_carb_kgh = min(m_fwd_carb_kgh, max(s.scrub_holdup_kg, 0.0) * (3600.0 / dt))
    s.react_m_in_prev = m_in_kgh
    s.react_m_liq += (m_in_kgh - m_out_kgh + m_fwd_carb_kgh) * (dt / 3600.0)
    s.react_m_liq = max(s.react_m_liq, r.M_HOLDUP_MIN)
    f_strip = (m_out_kgh / m_ov_split_kgh) if m_ov_split_kgh > 1.0e-9 else 1.0
    s.react_overflow_kmolh = {k: react["overflow_kmolh"][k] * f_strip
                              for k in react["overflow_kmolh"]}
    M_full_react = r.liquid_density(T_bulk_react) * v1["_react_area_m2"] * v1["REACT_LIQ_H_M"]
    react_carry_kgh = max(s.react_m_liq - M_full_react, 0.0) * (3600.0 / dt)
    s.react_m_liq = min(s.react_m_liq, M_full_react)
    s.react_level_pct = min(max(r.level_from_holdup(s.react_m_liq, T_bulk_react,
                                                    area_m2=v1["_react_area_m2"])
                                / v1["REACT_LIQ_H_M"] * 100.0, 0.0), 100.0)
    _H_liq_react = v1["REACT_LIQ_H_M"] * s.react_level_pct / 100.0
    s.react_lt322504_pct = min(max(v1["REACT_LEVEL_NLL_PCT"] + (_H_liq_react
                                                                - v1["REACT_LEVEL_DES_M"])
                                   / v1["REACT_LT_SPAN_M"] * 100.0, 0.0), 100.0)
    _ov_mass_kgh = sum(react["overflow_kmolh"][k] * mw[k] for k in react["overflow_kmolh"])
    react_carry_kmolh = ({k: react["overflow_kmolh"][k] * (react_carry_kgh / _ov_mass_kgh)
                          for k in react["overflow_kmolh"]}
                         if (react_carry_kgh > 0.0 and _ov_mass_kgh > 0.0) else None)
    _hpcc_liq_des = v1["HPCC_LIQ_DES_LIVE"] or v1["HPCC_LIQ_DES_KGH"]
    phi_in_hpcc = (hpcc["liq_kgh"] / _hpcc_liq_des) if _hpcc_liq_des else phi_fwd
    phi_out_hpcc = phi_fwd * (s.hpcc_level_pct / v1["HPCC_LEVEL_NLL_PCT"])
    dL_hpcc = (phi_in_hpcc - phi_out_hpcc) * 100.0 * dt / (v1["HPCC_TAU_FILL_MIN"] * 60.0)
    s.hpcc_level_pct = min(max(s.hpcc_level_pct + dL_hpcc, 0.0), 100.0)
    # ----- section 5: 322E003 (7992-8160) ---------------------------------------------------
    fic, tic = s.FIC, s.TIC
    ccw_pump_frac = 1.0 if (s.P329P006A or s.P329P006B) else 0.0
    flow_ss = (v1["SCRUB_CCW_KGH_DES"] / 1000.0) * (fic["op"] / max(v1["SCRUB_FV409_DES_PCT"],
                                                                    1e-6)) * ccw_pump_frac
    pv_prev = fic["pv_prev"]
    fic["pv"] += (dt / v1["FIC_329409_TAU_S"]) * (flow_ss - fic["pv"])
    if fic["mode"] == "AUTO":
        fic["op"] = min(max(fic["op"] + v1["FIC_329409_KC"] * (
            -(fic["pv"] - pv_prev) + (dt / v1["FIC_329409_TI"]) * (fic["sp"] - fic["pv"])),
            0.0), 100.0)
    fic["pv_prev"] = fic["pv"]
    t_load = v1["TIC_329005_LOAD_GAIN"] * ((react["co2_scale"] - 1.0) + react["delta_X"])
    T_ss = min(max(v1["SCRUB_CCW_T_OUT_DES"] - (v1["SCRUB_CCW_T_OUT_DES"]
                                                - v1["SCRUB_CCW_T_IN_DES"])
                   * (tic["op"] / max(v1["SCRUB_TV005_DES_PCT"], 1e-6)) + t_load, 20.0),
               v1["SCRUB_CCW_T_OUT_DES"])
    pv_prev = tic["pv_prev"]
    tic["pv"] += (dt / v1["TIC_329005_TAU_S"]) * (T_ss - tic["pv"])
    if tic["mode"] == "AUTO":
        tic["op"] = min(max(tic["op"] + v1["TIC_329005_KC"] * (
            (tic["pv"] - pv_prev) + (dt / v1["TIC_329005_TI"]) * (tic["pv"] - tic["sp"])),
            0.0), 100.0)
    tic["pv_prev"] = tic["pv"]
    m_ccw_kgh = max(fic["pv"], 1e-6) * 1000.0
    nu = s.p_syn / v1["SYN_P_DES_BARA"]
    t_cond_live = v1["scrub_cond_t_c"](s.p_syn)
    f_th = (t_cond_live - tic["pv"]) / max(v1["SCRUB_OVERFLOW_T_C"] - v1["SCRUB_CCW_T_IN_DES"],
                                           1e-6)
    rho_cond = ((m_ccw_kgh / v1["SCRUB_CCW_KGH_DES"]) * ccw_pump_frac
                * max(f_th, 0.0) / max(react["co2_scale"], 1e-6))
    if "B-91" in decided:   # 322E003 on its own liquor and its sump's room (`scrubber`)
        sat3 = saturation_fraction(s.scrub_pbub, s.p_syn, LIQUOR_DP_DES_BAR)
        room = (ej["suction_kgh"] + m_fwd_carb_kgh - s.recond_kgh
                + (v1["SCRUB_HOLDUP_MAX_KG"] - s.scrub_holdup_kg - s.scrub_held_kg)
                * (3600.0 / dt))
        r = scrubber_322e003(
            react["offgas_kmolh"], react["co2_scale"], tic["pv"], m_ccw_kgh, p_loop_bara=s.p_syn,
            vent_ratio=nu, nc_act=v1["react_nc_ratio"](react["overflow_kmolh"]),
            hic604_pct=s.HIC_322604, liq_carry_kmolh=react_carry_kmolh,
            t_carry_c=s.react_T_overflow, choke_level_pct=s.scrub_level_pct,
            spindle_phi=_phi_sp_theta,
            cool_frac=rho_cond if sat3 >= 1.0 else min(rho_cond, sat3),
            wash_ratio=x["m308_prev"] / v1["R3232_E003_M308_DES"], sump_room_kgh=room)
        scrub = {"overflow_kmolh": dict(r.overflow_kmolh), "offgas_kmolh": dict(r.offgas_kmolh),
                 "T_overflow": r.t_overflow_c, "T_offgas": r.t_offgas_c,
                 "cool_frac": r.cool_frac, "uncond_kgh": r.uncond_kgh}
    else:
        scrub = v1["scrub_322e003"](
            react["offgas_kmolh"], react["co2_scale"], tic["pv"], m_ccw_kgh, vent_ratio=nu,
            nc_act=v1["react_nc_ratio"](react["overflow_kmolh"]), hic604_pct=s.HIC_322604,
            liq_carry_kmolh=react_carry_kmolh, t_carry_c=s.react_T_overflow,
            choke_level_pct=s.scrub_level_pct, spindle_phi=_phi_sp_theta, cool_frac=rho_cond,
            wash_ratio=x["m308_prev"] / v1["R3232_E003_M308_DES"])
    m_loop_frac = min(max((s.react_level_pct + s.hpcc_level_pct + s.sump.level_pct)
                          / (v1["REACT_LEVEL_NLL_PCT"] + v1["HPCC_LEVEL_NLL_PCT"]
                             + v1["STRIP_LEVEL_SP_DES"]), 0.0), 1.0)
    f_ovf = v1["_f_flow"](scrub["T_overflow"], 60.0)
    if "B-78" in decided:
        s.scrub_mushy = f_ovf
    else:
        scrub["overflow_kmolh"] = {k: v * f_ovf for k, v in scrub["overflow_kmolh"].items()}
    m_cond_in = sum(scrub["overflow_kmolh"][k] * mw[k] for k in scrub["overflow_kmolh"])
    if m_cond_in > 1.0:
        s.y_scrub_ovf = {k: scrub["overflow_kmolh"].get(k, 0.0) * mw[k] / m_cond_in for k in mw}
        if "B-91" in decided:
            s.scrub_pbub = liquor_bubble_p_bara(scrub["overflow_kmolh"], scrub["T_overflow"])
    if "B-76" in decided:
        m_cond_in = m_cond_in + s.recond_kgh
    if s.scrub_level_pct <= 0.0 and ej["suction_kgh"] > m_cond_in:
        ej["suction_kgh"] = max(m_cond_in, 0.0)
    if "B-78" in decided:
        _m = s.scrub_holdup_kg + s.scrub_held_kg + (m_cond_in - ej["suction_kgh"]
                                                    - m_fwd_carb_kgh) * (dt / 3600.0)
        s.scrub_held_kg = max(_m - v1["SCRUB_HOLDUP_MAX_KG"], 0.0)
        s.scrub_holdup_kg = min(max(_m, 0.0), v1["SCRUB_HOLDUP_MAX_KG"])
    else:
        s.scrub_holdup_kg = min(max(s.scrub_holdup_kg + (m_cond_in - ej["suction_kgh"])
                                    * (dt / 3600.0), 0.0), v1["SCRUB_HOLDUP_MAX_KG"])
    s.scrub_level_pct = min(max(s.scrub_holdup_kg / v1["SCRUB_HOLDUP_NLL_KG"]
                                * v1["SCRUB_LEVEL_NLL_PCT"], 0.0), 100.0)
    _void = 1.0 - scrub["cool_frac"]
    lt_329501 = min(max(s.scrub_level_pct + v1["SCRUB_SWELL_PCT_MAX"] * _void
                        + v1["SCRUB_SWELL_NOISE_PCT"] * _void * (
                            math.sin(2.0 * math.pi * x["sim_t"] / v1["SCRUB_SWELL_NOISE_T1_S"])
                            + 0.6 * math.sin(2.0 * math.pi * x["sim_t"]
                                             / v1["SCRUB_SWELL_NOISE_T2_S"])) / 1.6,
                        0.0), 100.0)
    vent_cap = max(sum(scrub["offgas_kmolh"][k] * mw[k] for k in mw) - scrub["uncond_kgh"], 0.0)
    hv604 = purge_valve_322604(scrub["offgas_kmolh"], scrub["T_offgas"], s.HIC_322604, s.p_syn,
                               vent_cap_kgh=vent_cap,
                               p_out_bara=x["p_c001"] if "A-17" in decided
                               else v1["SCRUB_HV604_P_OUT"])
    # ----- sections 34 and 36: the trips --------------------------------------------------
    st = s.station
    if "A-12" in decided:   # AC4 PC21's flags (`control.interlocks`, decided 2026-10-09)
        t2, t8, t10 = s.ac4.step(Unit21TripInputs(
            p002a_running=st.pump_a.running, p002b_running=st.pump_b.running,
            p001_running=True, xv_322902_open=s.line.xv_322902_open,
            xv_321901_closed=not st.xv_321901_open, xv_322901_open=st.xv_322901_open,
            fy_322403_low=line.feed_th < TRIP_21_2_FY_L2_FRAC * (v1["CO2_DES_KGH"] / 1000.0),
            pdy_321203_low=feed.subcooling_a_bar < TRIP_21_8_PDY_L2_BAR,
            pdy_321204_low=feed.subcooling_b_bar < TRIP_21_8_PDY_L2_BAR), dt)
        s.trips.update({"21_2": t2, "21_8": t8, "21_10": t10})
        s.latched.update({"21_2": t2, "21_8": t8, "21_10": t10})
        if s.latched["22_2"]:
            s.trips["22_2"] = s.p_syn >= v1["SYN_P_TRIP_RESET_BARA"]
        else:
            s.trips["22_2"] = s.p_syn >= v1["SYN_P_TRIP_BARA"]
            if s.trips["22_2"]:
                s.latched["22_2"] = True

        def _stop(which="AB"):
            for pid, pump, sic in (("A", st.pump_a, st.sic_a), ("B", st.pump_b, st.sic_b)):
                if pid in which:
                    pump.running = False
                    sic.set_mode("MAN")
                    sic.set_op(0.0)
        if t2:   # PC21.5.1 .12-.15: XV-322902 through the Safeguard SG1 (decided 2026-10-16)
            st.xv_321901_open = st.xv_322901_open = False
            s.line.xv_322902_open = s.XV_322903 = False
            if "B-88" in decided:   # decision 83's class: the boundary's demand to zero
                s.co2_raw_th = 0.0
        if t8:
            _stop("A")
        if t10:
            _stop("B")
        if s.latched["22_2"]:
            s.line.xv_322902_open = False
            if "B-88" in decided:
                s.co2_raw_th = 0.0
            _stop()
        for pump in (st.pump_a, st.pump_b):
            if pump.fault:
                pump.running = False
    else:
        s.trips["21_2"] = (st.drum.level_frac < 0.05) or (feed.subcooling_a_bar < 0.1) \
            or (feed.subcooling_b_bar < 0.1)
        s.trips["21_8"] = st.pump_a.running and st.pump_a.fault
        s.trips["21_10"] = st.pump_b.running and st.pump_b.fault
        co2_lost = line.feed_th < 0.05 * (v1["CO2_DES_KGH"] / 1000.0)
        s.trips["21_4"] = co2_lost
        if co2_lost and disch_open and (st.pump_a.running or st.pump_b.running):
            s.latched["21_4"] = True
        for tk in ("21_2", "21_8", "21_10"):
            if s.trips[tk]:
                s.latched[tk] = True
        if s.latched["22_2"]:
            s.trips["22_2"] = s.p_syn >= v1["SYN_P_TRIP_RESET_BARA"]
        else:
            s.trips["22_2"] = s.p_syn >= v1["SYN_P_TRIP_BARA"]
            if s.trips["22_2"]:
                s.latched["22_2"] = True
        # The actions, at the foot of the tick as V1 sets them (10112-10133, 10164-10169).
        def _stop():
            st.pump_a.running = st.pump_b.running = False
            for sic in (st.sic_a, st.sic_b):
                sic.set_mode("MAN")
                sic.set_op(0.0)
        if s.latched["21_2"]:
            _stop()
            st.xv_321901_open = st.xv_322901_open = False
        if s.latched["21_4"]:
            _stop()
        if s.latched["21_8"]:
            st.pump_a.running = False
        if s.latched["21_10"]:
            st.pump_b.running = False
        if s.latched["22_2"]:
            s.line.xv_322902_open = False
            if "B-88" in decided:   # 320K002 tripped with it: the boundary's demand to zero
                s.co2_raw_th = 0.0
            _stop()
    # ----- section 37: PT-329201 (10345-10445) ---------------------------------------------
    _tau_vap_s = v1["SYN_P_TAU_MIN"] * 60.0
    m_recond_kgh = scrub["cool_frac"] * s.syn_vap_excess_kg / _tau_vap_s * 3600.0
    m_vap_net = scrub["uncond_kgh"] - m_recond_kgh
    s.syn_vap_excess_kg = max(s.syn_vap_excess_kg + m_vap_net * (dt / 3600.0), 0.0)
    s.recond_kgh = m_recond_kgh
    C_loop = v1["SYN_LOOP_C_KG_PER_BAR"]
    m_in_loop = (feed.flow_total_th * 1000.0) + line.feed_kgh + x["m308_now"]
    m_out_loop = sump.drain_kgh + hv604.mass_kgh + sump.blowthrough_kgh
    m_phase_shift = v1["SYN_P_PHASE_GAIN"] * m_vap_net
    credit = (m_loop_frac * react["co2_scale"] * v1["SYN_LOOP_RESID_DES_KGH"] if "B-75" in decided
              else m_loop_frac * v1["SYN_LOOP_RESID_DES_KGH"])
    if "B-77" in decided:   # the vapour inventory (`loop_pressure`, decided 2026-10-09)
        mw_og = _offgas_mw(react, v1)
        m_liq, v_liq = loop_liquid(s.react_m_liq, s.scrub_holdup_kg + s.scrub_held_kg,
                                   s.hpcc_level_pct, s.sump.level_pct)
        rho_g = s.p_syn * mw_og / (Z_GAS_DES * R_BAR_M3 * (s.react_T_offgas + 273.15))
        dm, dv = liquid_growth(
            (s.react_m_liq - liq_0[0]) * (3600.0 / dt),
            (s.scrub_holdup_kg + s.scrub_held_kg - liq_0[1]) * (3600.0 / dt),
            (s.hpcc_level_pct - liq_0[2]) / 100.0 * E002_SPAN_KG * (3600.0 / dt),
            (s.sump.level_pct - liq_0[3]) / 100.0 * SUMP_SPAN_KG * (3600.0 / dt))
        dm_liq_kgh = dm - rho_g * dv
        c_buf = B_207_PER_BAR * s.react_m_liq
        if sat < 1.0:   # B-91: a liquor above its bubble point takes up no more gas
            c_buf *= sat
        C_loop = vapour_capacity_kg_per_bar(v_liq, mw_og, s.react_T_offgas) + c_buf
        m_phase_shift = -dm_liq_kgh
    if "A-16" in decided:
        m_psv_kgh = _sv32251_kgh(s, react, m_in_loop, m_out_loop, credit, v1, m_phase_shift,
                                 C_loop)
    else:
        if s.syn_psv_open:
            s.syn_psv_open = s.p_syn > v1["SYN_PSV_RESEAT_BARA"]
        else:
            s.syn_psv_open = s.p_syn >= v1["SYN_PSV_SET_BARA"]
        m_psv_kgh = (v1["hydraulics"].psv_api520_choked_kgh(
            v1["SYN_PSV_AREA_M2"], s.p_syn, v1["SYN_PSV_T_REL_K"], v1["SCRUB_HV604_MW_DES"],
            k=v1["SYN_PSV_K_GAMMA"], z=v1["SYN_PSV_Z"], kd=v1["SYN_PSV_KD"], kb=v1["SYN_PSV_KB"],
            kc=v1["SYN_PSV_KC"]) if s.syn_psv_open else 0.0)
    m_net_loop = (m_in_loop - m_out_loop) - credit + m_phase_shift - m_psv_kgh
    s.p_syn = min(max(s.p_syn + m_net_loop / C_loop * (dt / 3600.0), 10.0), 180.0)
    return SimpleNamespace(ej=ej, strip=strip, sump=sump, hpcc=hpcc, react=react,
                           scrub=scrub, hv604=hv604, lt_329501=lt_329501, m_psv=m_psv_kgh,
                           conv_fac=conv_fac, rho_cond=rho_cond)


def _hpcc_port(strip, ej, t_shell, s, sat):
    """B-91: 322E002 as the port runs it (`carbamate_condenser`), on V1's two feeds and V1's
    states, its result in V1's dictionary — the keys V1's ``react_322r001`` and the glue read."""
    r = carbamate_condenser_322e002(
        strip["top_kmolh"], strip["T_top"], ej["comp"], ej["T_C"], t_shell_c=t_shell, gate=1.0,
        t_prod_prev_c=s.hpcc_tprod, p_loop_bara=s.p_syn, phi_prev=s.hpcc_phi, dt=DT,
        nc_anchor=pin.HPCC_NC_DES_LIVE, sat_frac=sat, low_nc=False)
    return {"phi_gas": r.phi_gas, "phi_film": r.phi_film, "phi_eq": r.phi_eq,
            "feed_kmolh": r.feed_kmolh, "gas_kmolh": r.gas_kmolh, "liq_kmolh": r.liq_kmolh,
            "gas_kgh": r.gas_kgh, "liq_kgh": r.liq_kgh, "gas_th": r.gas_th, "liq_th": r.liq_th,
            "gas_mol": r.gas_mol, "liq_mol": r.liq_mol, "gas_MW": r.gas_mw, "liq_MW": r.liq_mw,
            "gas_mol_pct": r.gas_mol_pct, "liq_mass_pct": r.liq_mass_pct, "T_prod": r.t_prod,
            "T_feed_mix": r.t_feed_mix, "T_adb": r.t_adb, "m_dot": r.m_dot_kgh,
            "P_bara": r.p_bub_bara, "P_bub": r.p_bub_bara, "L_hpcc": r.melt_nc,
            "W_hpcc": r.melt_hc, "duty_kw": r.duty_kw, "steam_kgh": r.steam_kgh,
            "q_steam_kw": r.q_steam_kw}


def _offgas_mw(react, v1):
    """The reactor top's vapour's molar mass, as `loop_pressure` takes it [kg/kmol]."""
    mw_c = v1["MW_COMP"]
    og = react["offgas_kmolh"]
    n = sum(og.get(k, 0.0) for k in mw_c)
    m = sum(og.get(k, 0.0) * mw_c[k] for k in mw_c)
    return m / n if (m > 1.0 and n > 0.0) else pin_mw()


def _sv32251_kgh(s, react, m_in, m_out, credit, v1, m_phase, c_loop):
    """A-16: SV32251 / SV32252 on the reactor top (`loop_pressure`), the port's lines."""
    from ureasim.core.relief import psv_api520_choked_kgh
    if not s.syn_psv_open and s.p_syn >= SV32251_SET_BARA:
        s.syn_psv_open = True
    elif s.syn_psv_open and s.p_syn <= SV32251_RESEAT_BARA:
        s.syn_psv_open = False
    if not s.syn_psv_open:
        return 0.0
    mw = _offgas_mw(react, v1)
    p_free = s.p_syn + ((m_in - m_out) - credit + m_phase) / c_loop * (DT / 3600.0)
    w = SV32251_COUNT * psv_api520_choked_kgh(SV32251_AREA_M2, s.p_syn,
                                              s.react_T_offgas + 273.15, mw, k=SV32251_K,
                                              z=SV32251_Z_REL)
    return min(w, max(p_free - SV32251_RESEAT_BARA, 0.0) * c_loop * 3600.0 / DT)


def pin_mw():
    from ureasim.data.unit_322_loop import SV32251_MW_REL
    return SV32251_MW_REL


# ======================================================================================
# The drivers
# ======================================================================================

def _assert_same(s, plant, out, k):
    """Every state the glue integrates, the port's against the transcription's, on tick ``k``."""
    u = plant.units
    rx, hc, sc, lp = u["322R001"], u["322E002"], u["322E003"], u["PT-329201"]
    (ccw,) = plant.loops["322E003"]
    pairs = [
        ("p_syn", s.p_syn, lp.p_syn_bara), ("vap", s.syn_vap_excess_kg, lp.vap_excess_kg),
        ("T_node", s.react_T_node, rx.t_nodes_c), ("T_ovf", s.react_T_overflow, rx.t_overflow_c),
        ("T_og", s.react_T_offgas, rx.t_offgas_c), ("L_rec", s.react_L_rec, rx.l_rec),
        ("W_rec", s.react_W_rec, rx.w_rec), ("m_liq", s.react_m_liq, rx.m_liq_kg),
        ("lvl", s.react_level_pct, rx.level_pct), ("lt504", s.react_lt322504_pct,
                                                   rx.lt_322504_pct),
        ("lag", s.react_m_in_lag, rx.m_in_lag_kgh), ("wash", s.react_fwd_wash, rx.fwd_wash_kgh),
        ("m_in_prev", s.react_m_in_prev, rx.m_in_prev_kgh),
        ("ovf", s.react_overflow_kmolh, rx.overflow_kmolh), ("L_feed", s.react_L_feed, rx.l_feed),
        ("W_feed", s.react_W_feed, rx.w_feed),
        ("hpcc_lvl", s.hpcc_level_pct, hc.level_pct), ("t_prod", s.hpcc_tprod, hc.t_prod_prev_c),
        ("p_bub", s.hpcc_pbub, hc.p_bub_prev_bara),
        ("phi", s.hpcc_phi, hc.phi),
        ("scrub_m", s.scrub_holdup_kg, sc.holdup_kg), ("scrub_lvl", s.scrub_level_pct,
                                                      sc.level_pct),
        ("y_ovf", s.y_scrub_ovf, sc.y_overflow), ("held", s.scrub_held_kg, sc.held_kg),
        ("mushy", s.scrub_mushy, sc.mushy_factor), ("recond", s.recond_kgh, lp.m_recond_kgh),
        ("p_bub3", s.scrub_pbub, sc.p_bub_bara),
        ("fic", (s.FIC["op"], s.FIC["pv"]), (ccw.fic_op, ccw.fic_pv)),
        ("tic", (s.TIC["op"], s.TIC["pv"]), (ccw.tic_op, ccw.tic_pv)),
        ("strip_lvl", s.sump.level_pct, u["322E001"].level_pct),
        ("line", s.line.pressure_bara, u["320K002"].pressure_bara),
        ("lt329501", out.lt_329501, None),
    ]
    for name, a, b in pairs:
        if b is None:
            continue
        assert a == b, (k, name, a, b)


def harness_plant():
    """The port's plant on the harness's switches — every departure with its own tests on V1's
    side of it — and its scheduler."""
    sch, plant = build_plant()
    # V1's linear FV-329409 from 60 %: its Metso trim has its own tests (decided 2026-10-15).
    plant.loops["322E003"] = (CcwLoop(**V1_FV_329409),)
    # B-91's fraction read a tick late, as the transcription reads it: its solution on the tick
    # (A-21, decided 2026-10-17) has its own tests.
    plant.units["322E002"].implicit_saturation = False
    # V1's linear flow law for 322E003's capacity: its effectiveness (B-99, decided 2026-10-17)
    # has its own tests.
    plant.units["322E003"].effectiveness_capacity = False
    # V1's unbounded stripper split and its clamped sump: 322E001's shell bound (B-102) and the
    # full sump's held-back excess (B-103), decided 2026-10-21, have their own tests.
    plant.units["322E001"].shell_bound = False
    plant.units["322E001"].hold_full = False
    # V1's sealed tubes, its K_N line below N/C 3.0 and its mass-only LPCC: the tubes' ceiling
    # (B-104), the azeotropic rise (B-106), 308's composition (B-105) and its line (B-110), decided
    # 2026-10-22, have their own tests.
    plant.units["322E001"].tube_ceiling = False
    plant.units["322E002"].low_nc_branch = False
    plant.units["323E003"].track_species = False
    plant.units["322E003"].wash_line = False
    # V1's reactor PT on the melt's bubble pressure and its feed line on the live loop: its cap at
    # 322E002's pressure (B-109) and its line on the PFD's design drop (B-112), decided 2026-10-22,
    # have their own tests.
    plant.units["322R001"].flash_cap = False
    plant.units["322R001"].design_drop = False
    return Scheduler(sch, plant), plant


def run_both(v1, ticks, act=None, decided=ALL, check=True):
    """The plant through the scheduler and the transcription beside it. ``act(k, plant, s)`` acts
    on both before tick ``k``. Returns the transcription's per-tick outputs and the scheduler.
    ``check`` asserts every tick ``==``; off, the two sides are only recorded (a departure's both
    ways)."""
    sched, plant = harness_plant()
    s = _v1_state(v1)
    hist = []
    for k in range(ticks):
        if act is not None:
            act(k, plant, s)
        x = {"p_mp": plant.units["329"].p_hp_bara, "p_lp": plant.units["329"].p_lp_bara,
             "m308_prev": plant.tears.m_308_kgh, "p_c001": plant.units["322C001"].p_bara,
             "sim_t": (plant.clock.tick + 1) * DT}
        rep = sched.tick()
        x["m308_now"] = rep.results["323E003"].m_308_kgh
        out = _v1_tick(v1, s, x, decided)
        if check:
            assert out.lt_329501 == rep.results["322E003"].sump.lt_329501_pct, k
            assert out.hv604.mass_kgh == rep.results["HV-322604"].valve.mass_kgh, k
            _assert_same(s, plant, out, k)
        hist.append((out, rep.results, s.p_syn))
    return hist, sched, s


# ======================================================================================
# The tests
# ======================================================================================

def test_the_design_seed_is_v1s(v1):
    """Ten ticks from the seed: the glue ``==`` V1's; the reactor makes the PFD's urea."""
    hist, _, _ = run_both(v1, 10)
    out, res, _ = hist[0]
    assert out.react["xi_urea"] == res["322R001"].reaction.xi_urea
    assert res["322R001"].reaction.xi_urea == pytest.approx(1302.27, abs=1e-6)


def test_hv_322605_throttled(v1):
    """HV-322605 from 60 to 45 %: the reactor floods, the stripper starves, two minutes."""
    def act(k, plant, s):
        if k == 5:
            plant.operator["HIC-322605"] = s.HIC_322605 = 45.0
    run_both(v1, 1200, act)


def test_the_spindle_moved(v1):
    """HV-322602 from 74 to 60 %: the forward-carbamate pulse, two minutes."""
    def act(k, plant, s):
        if k == 5:
            plant.operator["HIC-322602"] = s.HIC_322602 = 60.0
    run_both(v1, 1200, act)


def test_the_tempered_water_lost(v1):
    """329P006A stopped: 322E003 loses its condensation, PT-329201 climbs 0.35 bar in two minutes;
    the backlog recondensing returns to the sump (B-76). (141.0434 bar a with 323E011 on its dew point,
    323F010 on its live vacuum and the steam butterflies on their trims, 2026-10-15, session 53;
    141.0460 with PV-329202 and PV-329208 on
    their vendor trims, 2026-10-15, through 323E003's 308; 141.0451 with 322E003 on its own
    liquor and its sump, B-91, decided 2026-10-14; 141.0452 with B-91 (a) and B-92,
    decided 2026-10-10 and 2026-10-14; 141.0418 on the loop's vapour
    inventory, B-77 (b), with B-81's lines and AC4's trips, decided 2026-10-09; 141.3424 with
    FFIC-321404A / B, decided 2026-10-09, B-85; 141.3496 before, with 320K002 a boundary feed and
    LIC-322501, SIC-321950 and SIC-321951 on the DCS's table, decided 2026-10-08; 141.1734 before
    the tunings, 141.1733 on 320K002's vendor curves.)"""
    def act(k, plant, s):
        if k == 5:
            plant.loops["322E003"][0].p329p006a = s.P329P006A = False
    hist, _, s = run_both(v1, 1200, act)
    assert s.p_syn == pytest.approx(141.0434, abs=1e-4)


def test_the_ratio_raised(v1):
    """The N/C set point +5 %: the motive, the recycle lags, the reactor, two minutes."""
    def act(k, plant, s):
        if k == 5:
            plant.units["321"].ratio_sp *= 1.05
            s.station.ratio_sp = plant.units["321"].ratio_sp
    run_both(v1, 1200, act)


def test_the_constants_are_v1s(v1):
    """The loop node's, the trips' and the tempered water's numbers ``==`` V1's; V1's lumped
    capacity and phase gain are gone with B-77 (b), the vapour inventory decided 2026-10-09."""
    from ureasim.data import unit_322_loop as lp
    from ureasim.data import unit_329_ccw as cw
    assert (lp.SYN_LOOP_RESID_DES_KGH, lp.SYN_P_TAU_MIN) == (v1["SYN_LOOP_RESID_DES_KGH"],
                                                            v1["SYN_P_TAU_MIN"])
    assert not hasattr(lp, "SYN_LOOP_C_KG_PER_BAR") and not hasattr(lp, "SYN_P_PHASE_GAIN")
    assert (lp.TRIP_22_2_BARA, lp.TRIP_22_2_RESET_BARA) == (v1["SYN_P_TRIP_BARA"],
                                                             v1["SYN_P_TRIP_RESET_BARA"])
    assert (cw.FV_329409_OP_DES_PCT, cw.TV_329005_OP_DES_PCT, cw.FIC_329409_TAU_S,
            cw.FIC_329409_KC, cw.FIC_329409_TI_S, cw.TIC_329005_TAU_S, cw.TIC_329005_KC,
            cw.TIC_329005_TI_S, cw.TIC_329005_LOAD_GAIN_K) == (
        v1["SCRUB_FV409_DES_PCT"], v1["SCRUB_TV005_DES_PCT"], v1["FIC_329409_TAU_S"],
        v1["FIC_329409_KC"], v1["FIC_329409_TI"], v1["TIC_329005_TAU_S"], v1["TIC_329005_KC"],
        v1["TIC_329005_TI"], v1["TIC_329005_LOAD_GAIN"])
    # V1's SV-32201, which A-16 replaces: an assumed 200 t/h valve set at 161.01 bar a — 161.013
    # on V1's 1.013 bar atmosphere, 161.01325 on the standard one the switch seeds (B-6).
    assert v1["SYN_PSV_SET_BARA"] == pytest.approx(161.01325, abs=1e-9)


def test_trip_22_2_cuts_the_feeds_from_the_next_tick(v1):
    """The loop put at 155.5 bar a: trip 22.2 latches on its first tick and both sides cut the CO2
    and the ammonia from the next — V1 at the foot of its tick, the port at the head of the next —
    and the glue stays ``==`` for a minute of the trip."""
    def act(k, plant, s):
        if k == 0:
            plant.units["PT-329201"].p_syn_bara = s.p_syn = 155.5
    hist, sched, s = run_both(v1, 600, act)
    assert s.latched["22_2"] and sched.plant.units["SYN-TRIPS"].latched["22_2"]
    assert not s.line.xv_322902_open and not sched.plant.units["320K002"].xv_322902_open
    assert hist[-1][1]["321"].flow_total_th == 0.0


# --------------------------------------------------------------------------------------
# Decision 10's class on FIC-329409 and TIC-329005 (applied 2026-10-07), both sides
# --------------------------------------------------------------------------------------

def test_the_tempered_water_on_the_tables_rows_decided_divergence(monkeypatch):
    """The CCW loops' algorithm is V1's, proven ``==`` above on the decided tunings; here the
    tunings alone are swapped for V1's, lifted verbatim. A 10 % cut in FIC-329409's set point:
    V1's 0.08 %/(t/h) and 6 s settle it in two minutes (275.45 t/h at 120 s); the table's 0.60
    and 250 s on FT-329409's 0-500 m3/h take an hour (294.68 at 300 s, 275.52 at 3600 s). A 5 K
    rise in TIC-329005's: V1's 1.0 %/K and 15 s in five minutes (85.00 C at 300 s); the table's
    1.50 and 300 s on TT-329005's 0-200 C 84.46 C after an hour."""
    from ureasim.units.synthesis import ccw_loop
    v1_tuning = lift(ccw_tuning_switch.V1_NAMES)
    assert (v1_tuning["FIC_329409_KC"], v1_tuning["FIC_329409_TI"], v1_tuning["TIC_329005_KC"],
            v1_tuning["TIC_329005_TI"]) == (0.08, 6.0, 1.0, 15.0)

    def responses():
        # V1's linear FV-329409, the tunings alone the subject here.
        fic, tic = (ccw_loop.CcwLoop(**ccw_loop.V1_FV_329409),
                    ccw_loop.CcwLoop(**ccw_loop.V1_FV_329409))
        fic.fic_sp, tic.tic_sp = 306.0 * 0.9, 85.0
        seen = {}
        for k in range(1, 36001):
            fic.step(1.0, 0.0, 0.1)
            tic.step(1.0, 0.0, 0.1)
            if k in (1200, 3000, 36000):
                seen[k] = (fic.fic_pv, tic.tic_pv)
        return seen

    port = responses()
    for name, v1_name in (("FIC_329409_KC", "FIC_329409_KC"), ("FIC_329409_TI_S", "FIC_329409_TI"),
                          ("TIC_329005_KC", "TIC_329005_KC"), ("TIC_329005_TI_S", "TIC_329005_TI")):
        monkeypatch.setattr(ccw_loop, name, v1_tuning[v1_name])
    v1 = responses()
    assert v1[1200][0] == pytest.approx(275.45, abs=0.01)
    assert v1[3000][1] == pytest.approx(85.00, abs=0.01)
    assert port[3000][0] == pytest.approx(294.68, abs=0.01)
    assert port[36000] == pytest.approx((275.52, 84.46), abs=0.01)
