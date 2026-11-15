"""V1 <-> V1.1 equivalence for 324E001 / 324F001, stage 1 of unit 324.

What is being proved
--------------------
V1 writes the stage inline in `step_sim`, so its statements are TRANSCRIBED into `_v1_stage1`
line for line and declared as such: the 323D002 -> 324E001 packet and its transport, and the
stage itself (``main.py`` 9693-9890). Everything they call is V1's own code, lifted out of
``main.py`` and executed: ``_ctrl_ipd``, ``_lag1``, ``steam_chest_pressure``, ``tsat_steam``,
``urea_soln_cp``, ``evap_w_eq``, ``evap_thermo_diag``, ``vacuum_inlet_kmolh``,
``_backward_euler_p``, ``sol_vapour_y``, ``sol_biuret_xi``, ``sol_advance``, ``_cq_packet``,
``_w_norm``; ``hydraulics``, ``consequence``, ``vacuum_condenser`` and V1's own UNIQUAC module
loaded as real modules. The controllers' seeds are ``State.__init__``'s (6715-6798).

The departures
--------------
Ten, each a switch in the transcription; ``decided`` names the ones whose port lines stand in
V1's:

  * "B-61" — 324F002's pull off its map, its capacity on PFD 706 (decided 2026-10-01): the
    port's `ejector_map.suction_capacity_kgh` at the motive pressure V1's motive flow gives
    (`nozzle_pressure_bara`) and against 323C005, where V1 pulls its line,
    ``R324_F001_EJPULL_DES x (motive / R324_F002_MOTIVE_DES) x (P / R324_F001_P_BARA)``;
  * "B-62" — the held melt boils past its own boiling point (decided 2026-10-01): the port's
    `holdup_boil` called inside V1's fixed point, its vapour added where V1 adds the feed's;
  * "B-58" — the melt on the PFD's refit and under its ceiling (decided 2026-10-01): the port's
    `thermo.urea_melt` called as the port's lines, where V1 calls ``evap_w_eq``;
  * "chest" — 324E001's chest on its DDS's 3.7 bar a (decision 20): V1's own stroke and
    conductance expressions re-executed on it; V1 anchors on 3.96;
  * "gains" — TIC-324001, PIC-329203 and PIC-324202 on the table per cent of span (decisions 10,
    21), V1 1.5 bar/K, 0.30 x its chest scale, 2.0 %/bar;
  * "valve" — PV-324202 on its vendor trim from 61.07 % (decision 23), V1 linear from 50 %;
  * "heel" — the barometric leg above its 1 kg floor (decision 11's class, B-29);
  * "line" — the inlet line delivers the live departure flow (handoff B-21's class), V1 the
    packet's.
  * "B-28" — LIC-329505 with no deadband (decided 2026-10-09: no loop models the DCS table's
    deadband in a noiseless model), where V1 applies the table's 2 % on this one loop;
  * "B-67" — 324E002's NH3 and CO2 vent on the PFD's partial pressures plus the condensate's
    back-pressure departure (decided 2026-10-02; both design back-pressures below the PFD's
    partial pressures, so B-71 leaves the addition on both): V1's condenser module and specs with
    the switch (`tests.equivalence.b67_switch`), where V1 multiplies by the departure's ratio.

Every scenario runs the port against the switched transcription with ``==`` on every tick;
`test_first_evaporator_decided_equivalence.py` runs each departure both ways.
"""

from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

from ureasim.control.valve import cv_fraction
from ureasim.data import unit_324 as d
from ureasim.data.design_point import R324_FEED_DES
from ureasim.data.unit_323 import MEVAP_DES_KGH, W_S317
from ureasim.data.unit_323c005 import C005_P_BARA
from ureasim.data.unit_329 import P_LP_BARA
from ureasim.thermo import urea_melt as um
from ureasim.thermo.domains import NONVOLATILE
from ureasim.units.evaporation import ejector_map as em
from ureasim.units.evaporation import first_evaporator as fe
from ureasim.units.evaporation.holdup_boil import holdup_boil
from tests.equivalence import routes_switch
from tests.equivalence.b67_switch import switched_module, switched_specs
from tests.equivalence.v1_loader import lift, load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

ALL = frozenset({"B-61", "B-62", "B-58", "chest", "gains", "valve", "heel", "line", "B-67",
                 "B-28"})
DT = 0.1

V1_NAMES = [
    "evap_w_eq", "evap_thermo_diag", "urea_soln_cp", "steam_chest_pressure", "tsat_steam",
    "_ctrl_ipd", "_lag1", "_cq_packet", "_w_norm", "_proc_route", "clamp",
    "vacuum_inlet_kmolh", "VACUUM_CONDENSER_SPECS", "VACUUM_CONDENSERS", "_backward_euler_p",
    "sol_vapour_y", "sol_advance", "SOL_E001", "W_S401", "W_S317", "MW_SOL", "SOL_SPECIES",
    "SOL_BIU_EA", "SOL_BIU_ORDER", "STRIP_R_GAS_J",
    "R323_MEVAP_DES", "R323_P_STEAM_SUP", "R323_D002_RHO", "R324_FEED_DES", "R324_W_IN",
    "R324_W_EV1", "R324_P1_DES", "R324_V1_DES", "R324_E001_T_SP_C", "R324_F001_P_BARA",
    "R324_F001_VOL_M3", "R324_F001_RHO_L", "R324_F001_MW_VAP", "R324_LAM_V1",
    "R324_E001_PCHEST_DES", "R324_E001_OP_DES", "R324_E001_Q_DES_KW", "R324_E001_UA_KW",
    "R324_F001_M_TAU_S", "R324_F001_M_DES", "R324_F001_M_FULL", "R324_F001_FA_DES",
    "R324_PV202_OP_DES", "R324_F001_EJPULL_DES", "R324_E001_LAM_STEAM", "R324_E001_COND_DES",
    "R324_E001_COND_LVL_SP", "R324_E001_COND_M_DES", "R324_E001_COND_M_FULL",
    "R324_LV9505_OP_DES", "R324_LV9505_SPAN", "R324_F002_MOTIVE_DES", "R324_HIC9605_DES_PCT",
    "R324_HV9605_SPAN", "R324_PT_LOOP_TOL", "R324_PT_LOOP_MAXIT", "PIC_329203_KC_SCALE",
]


@pytest.fixture(scope="module")
def v1():
    ns = lift(V1_NAMES, seed={
        "math": math,
        "iapws_if97": load("iapws_if97"),
        "hydraulics": load("hydraulics"),
        "consequence": load("consequence"),
        "steam_system": load("steam_system"),
        "vacuum_condenser": load("vacuum_condenser"),
        "extended_uniquac": load("thermo_extended_uniquac"),
    })
    # main.py 2730-2736: SOL_STAGES's stage-1 row, which `sol_biuret_xi` reads.
    stages = {"E001": {"w": ns["W_S401"], "a": ns["SOL_E001"], "M": ns["R324_F001_M_DES"],
                       "T": ns["R324_E001_T_SP_C"]}}
    ns["sol_biuret_xi"] = lift(["sol_biuret_xi"], seed={
        "math": math, "SOL_STAGES": stages, "SOL_BIU_EA": ns["SOL_BIU_EA"],
        "SOL_BIU_ORDER": ns["SOL_BIU_ORDER"], "STRIP_R_GAS_J": ns["STRIP_R_GAS_J"],
    })["sol_biuret_xi"]
    # main.py 6247: V1's own route object for the line.
    # The isometrics' geometry (handoff A-11, decided 2026-10-07): `routes_switch`.
    ns["E001_ROUTE"] = routes_switch.decided(ns, "323D002_TO_324E001")
    # The decided chest: V1's own two statements re-executed on the DDS's 3.7 bar a.
    derived = ("R324_E001_OP_DES", "R324_E001_UA_KW")
    seed = {k: val for k, val in ns.items() if k not in derived}
    seed["R324_E001_PCHEST_DES"] = d.E001_PCHEST_DES_BARA
    ns["__chest__"] = {**ns, **lift(list(derived), seed=seed),
                       "R324_E001_PCHEST_DES": d.E001_PCHEST_DES_BARA}
    return ns


def _g(v1, decided):
    return v1["__chest__"] if "chest" in decided else v1


def v1_line_pull(v1, motive_kgh: float):
    """V1's 324F002 pull at a motive flow, as a function of the trial pressure (``main.py`` 9827)."""
    def pull(p: float) -> float:
        return v1["R324_F001_EJPULL_DES"] * (motive_kgh / v1["R324_F002_MOTIVE_DES"]) * (
            p / v1["R324_F001_P_BARA"])
    return pull


def map_pull(motive_kgh: float, p_discharge_bara: float):
    """The port's 324F002 pull at a motive flow: its map at the nozzle pressure the flow gives."""
    p_m = em.nozzle_pressure_bara(fe.EJECTOR_TAG, motive_kgh)

    def pull(p: float) -> float:
        return em.suction_capacity_kgh(fe.EJECTOR_TAG, p, p_m, p_discharge_bara)
    return pull


def _v1_state(v1, decided=ALL):
    """The V1 plant-state fields stage 1 reads and writes, seeded as ``State.__init__`` seeds them
    (``main.py`` 6617, 6715-6750, 6768, 6772-6776, 6792-6799, 6815-6818); the decided gains and
    strokes where switched."""
    g = _g(v1, decided)
    gains = "gains" in decided
    s = SimpleNamespace(tlag={}, steam=SimpleNamespace(P_LP=P_LP_BARA))
    s.w_e001 = dict(g["W_S401"])
    s.r324_e001_T = g["R324_E001_T_SP_C"]
    s.r324_f001_M = g["R324_F001_M_DES"]
    s.r324_f001_P = g["R324_F001_P_BARA"]
    s.r324_e001_chest_P = g["R324_E001_PCHEST_DES"]
    s.r324_e001_cond_M = g["R324_E001_COND_M_DES"]
    s.TIC_324001 = {"mode": "AUTO", "op": g["R324_E001_PCHEST_DES"],
                    "sp": g["R324_E001_T_SP_C"], "pv": g["R324_E001_T_SP_C"],
                    "pv1": g["R324_E001_T_SP_C"], "pv2": g["R324_E001_T_SP_C"],
                    "Kc": d.TIC_324001_KC if gains else 1.5, "Ti": 320.0, "Td": 0.0,
                    "act": +1.0, "op_lo": 0.0, "op_hi": g["R323_P_STEAM_SUP"],
                    "sp_lo": 0.0, "sp_hi": 200.0}
    s.PIC_329203 = {"mode": "CAS", "op": g["R324_E001_OP_DES"],
                    "sp": g["R324_E001_PCHEST_DES"], "pv": g["R324_E001_PCHEST_DES"],
                    "pv1": g["R324_E001_PCHEST_DES"], "pv2": g["R324_E001_PCHEST_DES"],
                    "Kc": d.PIC_329203_KC if gains else 0.3 * g["PIC_329203_KC_SCALE"],
                    "Ti": 75.0, "Td": -1.0, "act": +1.0, "op_lo": 0.0, "op_hi": 100.0,
                    "sp_lo": 0.0, "sp_hi": g["R323_P_STEAM_SUP"]}
    s.PIC_324202 = {"mode": "AUTO",
                    "op": d.PV_324202_OP_DES_PCT if "valve" in decided else g["R324_PV202_OP_DES"],
                    "sp": g["R324_F001_P_BARA"], "pv": g["R324_F001_P_BARA"],
                    "pv1": g["R324_F001_P_BARA"], "pv2": g["R324_F001_P_BARA"],
                    "Kc": d.PIC_324202_KC if gains else 2.0, "Ti": 200.0, "Td": -1.0,
                    "act": +1.0, "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0, "sp_hi": 1.0}
    s.LIC_329505 = {"mode": "AUTO", "op": g["R324_LV9505_OP_DES"],
                    "sp": g["R324_E001_COND_LVL_SP"], "pv": g["R324_E001_COND_LVL_SP"],
                    "pv1": g["R324_E001_COND_LVL_SP"], "pv2": g["R324_E001_COND_LVL_SP"],
                    "Kc": 2.5, "Ti": 60.0, "Td": 0.0, "Tf": 0.0,
                    "Dz": 0.0 if "B-28" in decided else 2.0, "act": -1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0, "sp_hi": 100.0}
    return s


def _v1_stage1(v1, s, m_324, T_d002, w_d002, pull_f010, sub_703, motive, p_d, tv_e002, dt,
               decided=ALL) -> dict:
    """V1 `main.py` 9693-9890, stage 1, TRANSCRIBED line for line (handoff A-12); the switches
    in the module docstring."""
    g = _g(v1, decided)
    clamp = g["clamp"]
    pull = map_pull(motive, p_d) if "B-61" in decided else v1_line_pull(v1, motive)
    # main.py 9697-9706, the 323D002 -> 324E001 line. _transport_process, less its telemetry.
    _m_dep_324 = max(m_324, 0.0)
    _pkt_dep_324 = g["_cq_packet"](1.0 if "line" in decided else _m_dep_324, T_d002, w_d002,
                                   g["urea_soln_cp"](w_d002.get("Urea", g["R324_W_IN"]), T_d002))
    _pkt_arr_324 = g["consequence"].transport_process_packet(
        s.tlag, "PROCESS_323D002_TO_324E001", _pkt_dep_324, g["E001_ROUTE"], _m_dep_324, dt)
    if _pkt_arr_324 == _pkt_dep_324:
        feed1_m, T_feed1, w_arr_324 = _m_dep_324, T_d002, w_d002
    else:
        feed1_m = _m_dep_324 if "line" in decided else _pkt_arr_324.mass_kgh
        T_feed1 = _pkt_arr_324.temperature_c
        w_arr_324 = g["_w_norm"](_pkt_arr_324.mass_fraction, w_d002)
    w_tank = w_arr_324.get("Urea", g["R324_W_IN"])
    urea1_in = w_tank * feed1_m
    w_feed1 = w_tank
    cp_feed1 = g["urea_soln_cp"](w_feed1, T_feed1)
    cp_hold1 = g["urea_soln_cp"](s.w_e001.get("Urea", g["R324_W_EV1"]), s.r324_e001_T)
    tic1_op = g["_ctrl_ipd"](s.TIC_324001, s.r324_e001_T, dt)
    pic203_pv = s.r324_e001_chest_P
    pic203_op = g["_ctrl_ipd"](s.PIC_329203, pic203_pv, dt, cas_sp=tic1_op)
    p_lp_lagged = g["_lag1"](s.tlag, "324E001_P_LP_thermal", s.steam.P_LP,
                             g["R324_F001_M_TAU_S"], dt)
    p_chest_e001 = g["steam_chest_pressure"](pic203_op, p_lp_lagged, g["R324_E001_OP_DES"],
                                             g["R324_E001_PCHEST_DES"], g["R324_E001_UA_KW"],
                                             s.r324_e001_T, g["R324_E001_Q_DES_KW"],
                                             g["R323_P_STEAM_SUP"], s.r324_e001_chest_P)
    s.r324_e001_chest_P = p_chest_e001
    w_max = um.strength_ceiling(w_feed1, sum(w_arr_324.get(k, 0.0) for k in NONVOLATILE
                                             if k != "Urea"))

    def w_eq_of(t, p):
        if "B-58" in decided:   # ---- the melt on the refit, under its ceiling (the port's) ----
            return um.equilibrium_urea_fraction(t, p, g["R324_W_EV1"], g["R324_E001_T_SP_C"],
                                                g["R324_F001_P_BARA"],
                                                a_urea_water_k=d.MELT_A_UREA_WATER_K,
                                                w_max=w_max)
        return g["evap_w_eq"](t, p, g["R324_W_EV1"], g["R324_E001_T_SP_C"],
                              g["R324_F001_P_BARA"])

    if "valve" in decided:      # ---- PV-324202 on its vendor trim (the port's line) ----
        fa202_m = g["R324_F001_FA_DES"] * (
            cv_fraction(s.PIC_324202["op"] / 100.0, "mod_equal_pct")
            / cv_fraction(d.PV_324202_OP_DES_PCT / 100.0, "mod_equal_pct"))
    else:
        fa202_m = g["R324_F001_FA_DES"] * (s.PIC_324202["op"] / max(g["R324_PV202_OP_DES"],
                                                                   1e-6))
    vac_op = g["_ctrl_ipd"](s.PIC_324202, s.r324_f001_P, dt)
    M_f001_pre = s.r324_f001_M
    t1_old = s.r324_e001_T
    t1_solved = t1_old
    p1_old = s.r324_f001_P
    p1_solved = p1_old
    _tv_e002 = tv_e002
    t1_fp_residual = math.inf
    t1_fp_converged = False
    t1_fp_iterations = 0
    if "B-67" in decided:       # ---- the vent on B-67's departure (V1's module, switched) ----
        spec, vc = switched_specs()["324E002"], switched_module()
    else:
        spec, vc = g["VACUUM_CONDENSER_SPECS"]["324E002"], g["vacuum_condenser"]
    hb = 0.0
    for t1_fp_iterations in range(1, g["R324_PT_LOOP_MAXIT"] + 1):
        Q_e001_kw = max(g["R324_E001_UA_KW"] * (g["tsat_steam"](p_chest_e001) - t1_solved), 0.0)
        w_eq1 = w_eq_of(t1_solved, p1_solved)
        v1_m = clamp(feed1_m - urea1_in / max(w_eq1, 1e-6), 0.0, feed1_m)
        pwr1 = (feed1_m / 3600.0 * cp_feed1 * (T_feed1 - t1_solved)
                + Q_e001_kw - v1_m / 3600.0 * g["R324_LAM_V1"])
        k_cap1 = (feed1_m / 3600.0 * cp_feed1
                  + (g["R324_E001_UA_KW"] if Q_e001_kw > 0.0 else 0.0))
        t1_next = t1_old + pwr1 * dt / max(M_f001_pre * cp_hold1 + k_cap1 * dt, 1e-6)
        m703_fp = (g["VACUUM_CONDENSERS"]["324E002"]["inlet_kgh"]
                   + (pull_f010 - g["R323_MEVAP_DES"]) + (v1_m - g["R324_V1_DES"])
                   + (fa202_m - g["R324_F001_FA_DES"]))
        boil_at = None
        if "B-62" in decided:   # ---- the held melt boils at the trial vacuum (the port's call) --
            def _boil(p, t_step=t1_next, c_step=max(M_f001_pre * cp_hold1 + k_cap1 * dt, 1e-6)):
                return holdup_boil(
                    t_step, p, M_f001_pre, s.w_e001, c_step, g["R324_LAM_V1"],
                    g["sol_vapour_y"](s.w_e001, g["SOL_E001"]["alpha"]).get("Urea", 0.0), 1.0,
                    dt, w_des=g["W_S401"]["Urea"], t_des_c=g["R324_E001_T_SP_C"],
                    p_des_bara=g["R324_F001_P_BARA"], a_urea_water_k=d.MELT_A_UREA_WATER_K)

            boil_at = _boil

            def n703_at(p, m=m703_fp, boil_at=boil_at):
                return g["vacuum_inlet_kmolh"]("324E002", m + boil_at(p)[0], fa202_m,
                                               g["R324_F001_FA_DES"], sub_703)
            _n703 = n703_at(p1_solved)
        else:
            _n703 = g["vacuum_inlet_kmolh"]("324E002", m703_fp, fa202_m, g["R324_F001_FA_DES"],
                                            sub_703)
        _bp703 = vc.condensate_back_pressure(_n703, _tv_e002)
        _vv_f001 = g["hydraulics"].vapour_volume_m3(g["R324_F001_VOL_M3"], M_f001_pre,
                                                    g["R324_F001_RHO_L"])

        def _dpdt_f001(p):
            n = n703_at(p) if boil_at is not None else _n703
            vent = vc.vent_kgh_at(spec, p, _tv_e002, n, _bp703)
            return g["hydraulics"].vessel_dpdt(p1_old, t1_solved + 273.15, _vv_f001,
                                               g["R324_F001_MW_VAP"],
                                               vent / g["R324_F001_MW_VAP"],
                                               pull(p) / g["R324_F001_MW_VAP"])

        p1_next = g["_backward_euler_p"](p1_old, dt, _dpdt_f001, 0.05, 1.0)
        if boil_at is not None:
            hb, t1_next = boil_at(p1_next)
        t1_fp_residual = max(abs(p1_next - p1_solved), abs(t1_next - t1_solved))
        if t1_fp_residual <= g["R324_PT_LOOP_TOL"]:
            p1_solved = p1_next
            t1_solved = t1_next
            t1_fp_converged = True
            break
        p1_solved = p1_next
        t1_solved = t1_next
    s.r324_e001_T = t1_solved
    s.r324_f001_P = p1_solved
    w_eq1 = w_eq_of(s.r324_e001_T, s.r324_f001_P)
    v1_m = clamp(feed1_m - urea1_in / max(w_eq1, 1e-6), 0.0, feed1_m)
    Q_e001_kw = max(g["R324_E001_UA_KW"] * (g["tsat_steam"](p_chest_e001) - s.r324_e001_T), 0.0)
    if "B-58" in decided:
        diag = um.melt_diagnostics(s.r324_e001_T, s.r324_f001_P, w_eq1,
                                   a_urea_water_k=d.MELT_A_UREA_WATER_K)
    else:
        diag = g["evap_thermo_diag"](s.r324_e001_T, s.r324_f001_P, w_eq1)
    p1_m = max(feed1_m - v1_m, 0.0)
    w1_live = clamp(urea1_in / max(p1_m, 1e-6), 0.0, 1.0)
    m_p1 = g["R324_P1_DES"] * math.sqrt(max(M_f001_pre / g["R324_F001_M_DES"], 0.0))
    if "heel" in decided:       # ---- the leg drains above its floor (the port's lines) ----
        _avail = max(M_f001_pre - 1.0, 0.0) / max(dt, 1.0e-9) * 3600.0 + feed1_m - v1_m - hb
        if m_p1 > _avail:
            m_p1 = _avail
    s.r324_f001_M = max(M_f001_pre + (feed1_m - v1_m - hb - m_p1) / 3600.0 * dt, 1.0)
    feed1_w = dict(w_arr_324)
    w_pre = s.w_e001
    y_v1 = g["sol_vapour_y"](s.w_e001, g["SOL_E001"]["alpha"])
    xi_e001 = g["sol_biuret_xi"]("E001", M_f001_pre, s.w_e001, s.r324_e001_T)
    s.w_e001 = g["sol_advance"](s.w_e001, M_f001_pre, s.r324_f001_M, feed1_m, feed1_w,
                                v1_m + hb, y_v1, m_p1, xi_e001, dt)   # sol_pin_strength: identity
    cond_gen = Q_e001_kw / g["R324_E001_LAM_STEAM"] * 3600.0
    lvl_e001c = clamp(s.r324_e001_cond_M / g["R324_E001_COND_M_FULL"] * 100.0, 0.0, 100.0)
    lic9505_op = g["_ctrl_ipd"](s.LIC_329505, lvl_e001c, dt)
    lv9505_m = lic9505_op / 100.0 * g["R324_LV9505_SPAN"]
    s.r324_e001_cond_M = max(s.r324_e001_cond_M + (cond_gen - lv9505_m) / 3600.0 * dt, 0.01)
    m703 = (g["VACUUM_CONDENSERS"]["324E002"]["inlet_kgh"] + (pull_f010 - g["R323_MEVAP_DES"])
            + (v1_m + hb - g["R324_V1_DES"]) + (fa202_m - g["R324_F001_FA_DES"]))
    return {
        "feed": (feed1_m, T_feed1, w_arr_324, urea1_in, cp_feed1),
        "ctl": (tic1_op, pic203_op, p_chest_e001, Q_e001_kw, fa202_m, vac_op),
        "melt": (w_max if "B-58" in decided else None, w_eq1, v1_m, hb, m703),
        "fp": (t1_fp_iterations, t1_fp_residual, t1_fp_converged, diag),
        "out": (p1_m, w1_live, m_p1, t1_old, w_pre, y_v1, xi_e001),
        "trap": (cond_gen, lvl_e001c, lic9505_op, lv9505_m),
        "LI": s.r324_f001_M / g["R324_F001_M_FULL"] * 100.0,
    }


def _assert_tick(a, b: fe.FirstEvaporatorResult, s, unit, loops, label):
    assert a["feed"] == (b.feed_kgh, b.feed_t_c, b.feed_w, b.feed_urea_kgh, b.feed_cp), label
    assert a["ctl"] == (b.tic_op_bara, b.pic_op_pct, b.chest_p_bara, b.q_kw, b.false_air_kgh,
                        b.vacuum_op_pct), label
    assert a["melt"][1:] == (b.w_eq, b.m_vap_kgh, b.m_boil_kgh, b.m_703_kgh), label
    if a["melt"][0] is not None:
        assert a["melt"][0] == b.w_max, label
    assert a["fp"] == (b.iterations, b.residual, b.converged,
                       (b.thermo_validity, b.thermo_px_residual_bara)), label
    assert a["out"] == (b.melt_kgh, b.w_melt, b.m_401_kgh, b.drain_t_c, b.drain_w, b.y_vap,
                        b.xi_kmolh), label
    assert a["trap"] == (b.steam_kgh, b.cond_level_pct, b.trap_op_pct, b.m_cond_out_kgh), label
    assert a["LI"] == b.level_pct, label
    assert (s.r324_f001_M, s.r324_e001_T, s.r324_f001_P, s.w_e001, s.r324_e001_chest_P,
            s.r324_e001_cond_M) == (unit.m_kg, unit.t_c, unit.p_bara, unit.w, unit.chest_p_bara,
                                    unit.cond_m_kg), label
    for v1c, loop in ((s.TIC_324001, loops.tic), (s.PIC_329203, loops.pic),
                      (s.PIC_324202, loops.vacuum), (s.LIC_329505, loops.trap)):
        assert (v1c["op"], v1c["sp"], v1c["pv"], v1c["pv1"], v1c["pv2"], v1c["mode"]) == (
            loop.op, loop.sp, loop.pv, loop.pv1, loop.pv2, loop.mode), (label, loop.tag)


#: 323D002's liquor at design, and a weaker, ammonia-richer one.
W317 = dict(W_S317)
W317_WEAK = dict(W317)
W317_WEAK["Urea"] = W317["Urea"] - 0.02
W317_WEAK["NH3"] = W317["NH3"] + 0.002
W317_WEAK["H2O"] = W317["H2O"] + 0.018
BLOW = (900.0, {"NH3": 0.55, "CO2": 0.30, "H2O": 0.15})
TV_DES = None   # filled from V1's spec in the fixture-dependent helper


def _design(v1, **over):
    base = {"m324": R324_FEED_DES, "t": 99.0, "w": W317, "f010": MEVAP_DES_KGH, "sub": None,
            "p_lp": P_LP_BARA, "motive": 390.0, "pd": C005_P_BARA,
            "tv": switched_specs()["324E002"]["t_v_solved_des"]}
    base.update(over)
    return base


def _run(v1, script, n_ticks, decided=ALL, check=True):
    """Drive V1's transcription and the port side by side; `script(k)` gives tick k's inputs.
    Returns the V1 state, the port's unit and loops, and the last result."""
    s = _v1_state(v1, decided)
    # V1's linear chest valve: PV-329203's vendor trim is proved in its decided test.
    unit = fe.FirstEvaporator(chest=fe.V1_CHEST, lv_329505=None)
    loops = fe.FirstEvaporatorLoops(pic=fe.pic_329203(fe.V1_CHEST),
                                    trap=fe.lic_329505(fe.V1_TRAP_OP_DES_PCT))
    b = None
    for k in range(n_ticks):
        x = script(k)
        s.steam.P_LP = x["p_lp"]
        a = _v1_stage1(v1, s, x["m324"], x["t"], x["w"], x["f010"], x["sub"], x["motive"],
                       x["pd"], x["tv"], DT, decided)
        b = port_step(unit, loops, x)
        if check:
            _assert_tick(a, b, s, unit, loops, k)
    return s, unit, loops, b


def port_step(unit, loops, x):
    """The port's tick on a scenario's inputs: 324F002's motive pressure from V1's motive flow."""
    return unit.step(loops, x["m324"], x["t"], x["w"], x["p_lp"],
                     em.nozzle_pressure_bara(fe.EJECTOR_TAG, x["motive"]), x["pd"], x["f010"],
                     x["sub"], x["tv"], DT)


def _step(v1, k0, **over):
    return lambda k: _design(v1, **(over if k >= k0 else {}))


def test_the_port_uses_v1s_design_basis(v1):
    """The stage's design numbers, ``==`` V1's: the balance, the separator, the duty on V1's own
    anchor (the decided chest re-derives two of them), the trap, the species anchor."""
    assert (d.P1_DES_KGH, d.V1_DES_KGH, d.F001_M_DES_KG, d.F001_MW_VAP, d.E001_Q_DES_KW) == (
        v1["R324_P1_DES"], v1["R324_V1_DES"], v1["R324_F001_M_DES"], v1["R324_F001_MW_VAP"],
        v1["R324_E001_Q_DES_KW"])
    assert (d.F001_VOL_M3, d.F001_RHO_L, d.E001_LAMBDA_KJKG, d.F001_M_FULL_KG) == (
        v1["R324_F001_VOL_M3"], v1["R324_F001_RHO_L"], v1["R324_LAM_V1"], v1["R324_F001_M_FULL"])
    assert (d.E001_COND_DES_KGH, d.E001_COND_M_DES_KG, d.E001_COND_M_FULL_KG,
            d.LV_329505_SPAN_KGH) == (v1["R324_E001_COND_DES"], v1["R324_E001_COND_M_DES"],
                                      v1["R324_E001_COND_M_FULL"], v1["R324_LV9505_SPAN"])
    c = v1["__chest__"]
    assert (d.E001_OP_DES_PCT, d.E001_UA_KW) == (c["R324_E001_OP_DES"], c["R324_E001_UA_KW"])
    assert (v1["R324_E001_PCHEST_DES"], d.E001_PCHEST_DES_BARA) == (3.96, 3.7)
    assert d.W_S401 == v1["W_S401"]
    a = d.E001_LIQUOR.anchor
    assert (a.xi, a.y, a.alpha, a.resid, a.entrain) == (
        v1["SOL_E001"]["xi"], v1["SOL_E001"]["y"], v1["SOL_E001"]["alpha"],
        v1["SOL_E001"]["resid"], v1["SOL_E001"]["entrain"])
    assert (d.PT_LOOP_TOL, d.PT_LOOP_MAXIT) == (v1["R324_PT_LOOP_TOL"], v1["R324_PT_LOOP_MAXIT"])


@pytest.mark.parametrize("name, n, over", [
    ("design", 300, {}),
    ("feed -10 %", 3000, {"m324": 0.9 * R324_FEED_DES}),
    ("feed 10 K colder", 3000, {"t": 89.0}),
    ("LP header -10 %", 3000, {"p_lp": 0.9 * P_LP_BARA}),
    ("weaker feed", 3000, {"w": W317_WEAK}),
    ("323F010 +15 %", 2000, {"f010": 1.15 * MEVAP_DES_KGH}),
    ("blow-through", 2000, {"sub": BLOW}),
    ("motive halved", 3000, {"motive": 195.0}),
    ("cold end +3 K", 2000, {"tv": None}),
])
def test_stage_1_is_v1s_tick_by_tick(v1, name, n, over):
    """Each scenario stepped in at tick 5 and held: every published field, the separator's whole
    state and the four controllers ``==`` on every tick."""
    if "tv" in over:
        over = {"tv": switched_specs()["324E002"]["t_v_solved_des"] + 3.0}
    _run(v1, _step(v1, 5, **over), n)


def test_a_feed_cut_drains_the_separator_to_its_heel(v1):
    """323P003 stops: the held melt boils as the leg drains the separator to its 1 kg floor and
    no further."""
    _, unit, _, b = _run(v1, _step(v1, 5, m324=0.0), 6000)
    assert unit.m_kg == pytest.approx(1.0, abs=1e-9) and b.m_401_kgh >= 0.0


def test_set_point_steps_are_v1s(v1):
    """TIC-324001 to 132 C and PIC-324202 to 0.30 bar a at tick 5, 3000 ticks."""
    s = _v1_state(v1)
    # V1's linear chest valve: PV-329203's vendor trim is proved in its decided test.
    unit = fe.FirstEvaporator(chest=fe.V1_CHEST, lv_329505=None)
    loops = fe.FirstEvaporatorLoops(pic=fe.pic_329203(fe.V1_CHEST),
                                    trap=fe.lic_329505(fe.V1_TRAP_OP_DES_PCT))
    for k in range(3000):
        if k == 5:
            for c, loop, sp in ((s.TIC_324001, loops.tic, 132.0),
                                (s.PIC_324202, loops.vacuum, 0.30)):
                c["sp"] = sp
                loop.sp = sp
        x = _design(v1)
        a = _v1_stage1(v1, s, x["m324"], x["t"], x["w"], x["f010"], x["sub"], x["motive"],
                       x["pd"], x["tv"], DT)
        b = port_step(unit, loops, x)
        _assert_tick(a, b, s, unit, loops, k)


def test_lic_329505_without_the_deadband_decided_divergence(v1):
    """B-28, decided 2026-10-09: no loop models the DCS table's deadband. LIC-329505's set point
    from 50 to 51 % at tick 5, both ways on V1's transcription: V1's 2 % deadband never moves the
    condensate level (50.0 % after ten minutes, the error inside the band); without it the level
    is at 51.0003 %. The port's loop is the switched side (`test_set_point_steps_are_v1s` and the
    scenarios compare it tick by tick)."""
    assert fe.lic_329505().Dz == 0.0
    ends = {}
    for dec in (ALL - {"B-28"}, ALL):
        s = _v1_state(v1, dec)
        for k in range(6000):
            if k == 5:
                s.LIC_329505["sp"] = 51.0
            x = _design(v1)
            _v1_stage1(v1, s, x["m324"], x["t"], x["w"], x["f010"], x["sub"], x["motive"],
                       x["pd"], x["tv"], DT, dec)
        ends["B-28" in dec] = s.LIC_329505["pv"]
    assert ends[False] == pytest.approx(50.0, abs=1e-6)
    assert ends[True] == pytest.approx(51.0003, abs=1e-4)


@pytest.mark.parametrize("p_old, slope, offset", [
    (0.33, -0.05, 0.0), (0.33, -0.05, 1e-3), (0.131, -18.0, -2e-3), (0.2, -0.5, 0.4),
    (0.05, -3.0, -1.0), (0.99, -1.0, 2.0),
])
def test_the_backward_step_is_v1s(v1, p_old, slope, offset):
    """`core.node.backward_euler_pressure` against V1's ``_backward_euler_p`` on a node whose
    dP/dt is steep and curved in its own pressure, a stationary one, and both brackets' edges."""
    from ureasim.core.node import backward_euler_pressure

    def dpdt(p):
        return offset + slope * (p - p_old) - 0.3 * (p - p_old) ** 2

    for dt in (0.1, 1.0, 2.0):
        assert backward_euler_pressure(p_old, dt, dpdt, 0.05, 1.0) == v1["_backward_euler_p"](
            p_old, dt, dpdt, 0.05, 1.0)
