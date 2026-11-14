"""V1 <-> V1.1 equivalence for 324E003 / 324F003, stage 2 of unit 324.

What is being proved
--------------------
V1 writes the stage inline in `step_sim`, so its statements are TRANSCRIBED into `_v1_stage2`
line for line and declared as such (``main.py`` 9896-10021). Everything they call is V1's own
code, lifted out of ``main.py`` and executed: ``_ctrl_ipd``, ``_lag1``, ``steam_chest_pressure``,
``tsat_steam``, ``urea_soln_cp``, ``evap_w_eq``, ``evap_thermo_diag``, ``vacuum_inlet_kmolh``,
``_backward_euler_p``, ``sol_vapour_y``, ``sol_biuret_xi``, ``sol_advance``, ``route_lv324501``;
``hydraulics``, ``vacuum_condenser`` and V1's own UNIQUAC module loaded as real modules. The
controllers' seeds are ``State.__init__``'s (6750-6800). ``step_uf85_cascade`` is not called: V1
calls it with the recycle permissive forced (UF85 deferred with unit 335), so it touches only
unit 335's own controllers and returns no flow.

The stage's inputs are stage 1's outputs on the same tick, as V1 reads them: the leg's flow, the
strength stage 1 made (``w1_live``), stage 1's solved temperature and its advanced holdup.

The departures
--------------
Ten, each a switch in the transcription; ``decided`` names the ones whose port lines stand in
V1's:

  * "B-61" — 324F004's pull off its map, its capacity on PFD 712 (decided 2026-10-01), at the
    motive pressure V1's HIC-329606 gives (`nozzle_pressure_bara` of PFD 927's 1220 kg/h x HIC /
    50, B-64) and against 324E006; V1 pulls ``R324_F003_EJPULL_DES x (HIC / 50) x (P /
    R324_F003_P_BARA)``;
  * "B-62" — the held melt boils past its own boiling point (decided 2026-10-01), at the trial
    vacuum inside the backward step;
  * "B-63" — the feed's urea at the strength the leg drains, stage 1's holdup's, anchored on the
    design (decided 2026-10-02; the port's `leg_urea_strength`); V1 takes ``w1_live``;
  * "B-58" — the melt on the PFD's refit and under its ceiling (decided 2026-10-01);
  * "chest" — 324E003's chest on its DDS's 5.9 bar a (decision 20): V1's conductance expression
    re-executed on it, its stroke V1's relation inverted; V1 anchors on 8.1;
  * "gains" — TIC-324002, PIC-329212 and PIC-324203 on the table per cent of span (decisions 10,
    21), V1 2.0 bar/K, 0.65 x its chest scale, 2.0 %/bar;
  * "valve" — PV-324203 on its vendor trim from 92.03 % (decision 23), V1 linear from 50 %;
  * "volume" — 324F003 on its drawing's 10.7 m3 (decision 33), V1 the 7.427 m3 cylinder;
  * "heel" — LV-324501 drains only above the 1 kg floor (decision 11's class);
  * "B-67" — 324E005's vent on B-67's and B-71's law (decided 2026-10-02): V1's condenser
    module and specs with the switch (`tests.equivalence.b67_switch`). 324E005's NH3 and CO2
    design back-pressures exceed the PFD's partial pressures, so B-71 keeps V1's ratio on both
    and the switch is the identity on this stage.

Every scenario runs the port against the switched transcription with ``==`` on every tick;
`test_second_evaporator_decided_equivalence.py` runs each departure both ways.
"""

from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

from ureasim.control.valve import cv_fraction
from ureasim.data import unit_324 as d
from ureasim.thermo import urea_melt as um
from ureasim.thermo.domains import NONVOLATILE
from ureasim.units.evaporation import ejector_map as em
from ureasim.units.evaporation import second_evaporator as se
from ureasim.units.evaporation.holdup_boil import holdup_boil
from ureasim.units.evaporation.melt_route import melt_route
from tests.equivalence.b67_switch import switched_module, switched_specs
from tests.equivalence.v1_loader import lift, load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

ALL = frozenset({"B-61", "B-62", "B-63", "B-58", "chest", "gains", "valve", "volume", "heel",
                 "B-67"})
DT = 0.1

V1_NAMES = [
    "evap_w_eq", "evap_thermo_diag", "urea_soln_cp", "steam_chest_pressure", "tsat_steam",
    "_ctrl_ipd", "_lag1", "_w_norm", "clamp", "vacuum_inlet_kmolh", "VACUUM_CONDENSER_SPECS",
    "VACUUM_CONDENSERS", "_backward_euler_p", "sol_vapour_y", "sol_advance", "SOL_E003",
    "W_S401", "W_S402", "W_S697", "MW_SOL", "SOL_SPECIES", "SOL_BIU_EA", "SOL_BIU_ORDER",
    "STRIP_R_GAS_J", "route_lv324501", "R324_UF_RATIO",
    "R324_W_EV1", "R324_W_EV2", "R324_P1_DES", "R324_P2_DES", "R324_V2_DES", "R324_E001_T_SP_C",
    "R324_E003_T_SP_C", "R324_F003_P_BARA", "R324_LAM_V2", "R324_E003_OP_DES",
    "R324_E003_PCHEST_DES", "R324_E003_Q_DES_KW", "R324_E003_UA_KW", "R324_E003_LAM_STEAM",
    "R324_F003_M_TAU_S", "R324_F003_LVL_SP", "R324_F003_M_DES", "R324_F003_M_FULL",
    "R324_F003_VOL_M3", "R324_F003_RHO_L", "R324_F003_MW_VAP", "R324_F003_FA_DES",
    "R324_PV203_OP_DES", "R324_F003_EJPULL_DES", "R324_HIC9606_DES_PCT", "R324_LIC501_OP_DES",
    "R324_LVA_SPAN", "R335_LVB_RELIEF_BARG", "R335_PIC201_DES_BARG", "R324_PT_LOOP_TOL",
    "R324_PT_LOOP_MAXIT", "PIC_329212_KC_SCALE",
]


@pytest.fixture(scope="module")
def v1():
    steam = load("steam_system")
    ns = lift(V1_NAMES, seed={
        "math": math,
        "iapws_if97": load("iapws_if97"),
        "hydraulics": load("hydraulics"),
        "steam_system": steam,
        "vacuum_condenser": load("vacuum_condenser"),
        "extended_uniquac": load("thermo_extended_uniquac"),
    })
    ns["steam_system"] = steam
    ns["hydraulics"] = load("hydraulics")
    ns["vacuum_condenser"] = load("vacuum_condenser")
    # main.py 2730-2736: SOL_STAGES's stage-2 row, which `sol_biuret_xi` reads.
    stages = {"E003": {"w": ns["W_S402"], "a": ns["SOL_E003"], "M": ns["R324_F003_M_DES"],
                       "T": ns["R324_E003_T_SP_C"]}}
    ns["sol_biuret_xi"] = lift(["sol_biuret_xi"], seed={
        "math": math, "SOL_STAGES": stages, "SOL_BIU_EA": ns["SOL_BIU_EA"],
        "SOL_BIU_ORDER": ns["SOL_BIU_ORDER"], "STRIP_R_GAS_J": ns["STRIP_R_GAS_J"],
    })["sol_biuret_xi"]
    # The decided chest: the DDS's 5.9 bar a, the stroke V1's relation inverted, and V1's own
    # conductance statement re-executed on it.
    seed = {k: val for k, val in ns.items() if k != "R324_E003_UA_KW"}
    seed["R324_E003_PCHEST_DES"] = d.E003_PCHEST_DES_BARA
    ns["__chest__"] = {**ns, **lift(["R324_E003_UA_KW"], seed=seed),
                       "R324_E003_PCHEST_DES": d.E003_PCHEST_DES_BARA,
                       "R324_E003_OP_DES": d.E003_OP_DES_PCT}
    return ns


def _g(v1, decided):
    return v1["__chest__"] if "chest" in decided else v1


def v1_line_pull(v1, hic_pct: float):
    """V1's 324F004 pull at HIC-329606, as a function of the trial pressure (``main.py`` 9955)."""
    def pull(p: float) -> float:
        return v1["R324_F003_EJPULL_DES"] * (hic_pct / v1["R324_HIC9606_DES_PCT"]) * (
            p / v1["R324_F003_P_BARA"])
    return pull


def motive_bara(hic_pct: float) -> float:
    """324F004's nozzle pressure at HIC-329606: V1's linear motive, PFD 927's 1220 kg/h at 50 %."""
    return em.nozzle_pressure_bara(se.EJECTOR_TAG,
                                   d.EJECTOR_DESIGN_LOADS[se.EJECTOR_TAG].motive_kgh
                                   * hic_pct / 50.0)


def map_pull(hic_pct: float, p_discharge_bara: float):
    p_m = motive_bara(hic_pct)

    def pull(p: float) -> float:
        return em.suction_capacity_kgh(se.EJECTOR_TAG, p, p_m, p_discharge_bara)
    return pull


def _v1_state(v1, decided=ALL):
    """The V1 plant-state fields stage 2 reads and writes, seeded as ``State.__init__`` seeds them
    (``main.py`` 6750-6800, 6819-6821); the decided gains and strokes where switched."""
    g = _g(v1, decided)
    gains = "gains" in decided
    p_mp = g["steam_system"].P_MP_BARA
    s = SimpleNamespace(tlag={}, steam=SimpleNamespace(P_9=p_mp))
    s.w_e003 = dict(g["W_S402"])
    s.r324_e003_T = g["R324_E003_T_SP_C"]
    s.r324_f003_M = g["R324_F003_M_DES"]
    s.r324_f003_P = g["R324_F003_P_BARA"]
    s.r324_e003_chest_P = g["R324_E003_PCHEST_DES"]
    s.TIC_324002 = {"mode": "AUTO", "op": g["R324_E003_PCHEST_DES"],
                    "sp": g["R324_E003_T_SP_C"], "pv": g["R324_E003_T_SP_C"],
                    "pv1": g["R324_E003_T_SP_C"], "pv2": g["R324_E003_T_SP_C"],
                    "Kc": d.TIC_324002_KC if gains else 2.0, "Ti": 300.0, "Td": 0.0,
                    "act": +1.0, "op_lo": 0.0, "op_hi": p_mp, "sp_lo": 0.0, "sp_hi": 200.0}
    s.PIC_329212 = {"mode": "CAS", "op": g["R324_E003_OP_DES"],
                    "sp": g["R324_E003_PCHEST_DES"], "pv": g["R324_E003_PCHEST_DES"],
                    "pv1": g["R324_E003_PCHEST_DES"], "pv2": g["R324_E003_PCHEST_DES"],
                    "Kc": d.PIC_329212_KC if gains else 0.65 * g["PIC_329212_KC_SCALE"],
                    "Ti": 130.0, "Td": -1.0, "act": +1.0, "op_lo": 0.0, "op_hi": 100.0,
                    "sp_lo": 0.0, "sp_hi": p_mp}
    s.PIC_324203 = {"mode": "AUTO",
                    "op": d.PV_324203_OP_DES_PCT if "valve" in decided else g["R324_PV203_OP_DES"],
                    "sp": g["R324_F003_P_BARA"], "pv": g["R324_F003_P_BARA"],
                    "pv1": g["R324_F003_P_BARA"], "pv2": g["R324_F003_P_BARA"],
                    "Kc": d.PIC_324203_KC if gains else 2.0, "Ti": 200.0, "Td": -1.0,
                    "act": +1.0, "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0, "sp_hi": 1.0}
    s.LIC_324501 = {"mode": "AUTO", "op": g["R324_LIC501_OP_DES"],
                    "sp": g["R324_F003_LVL_SP"], "pv": g["R324_F003_LVL_SP"],
                    "pv1": g["R324_F003_LVL_SP"], "pv2": g["R324_F003_LVL_SP"],
                    "Kc": 0.85, "Ti": 200.0, "Td": -1.0, "act": -1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0, "sp_hi": 100.0}
    return s


def _v1_stage2(v1, s, m_p1, w1_live, T_e001, w_e001, hic, p_d, tv_e005, p335, dt,
               decided=ALL) -> dict:
    """V1 `main.py` 9896-10021, stage 2, TRANSCRIBED line for line (handoff A-12); the switches
    in the module docstring."""
    g = _g(v1, decided)
    clamp = g["clamp"]
    pull = map_pull(hic, p_d) if "B-61" in decided else v1_line_pull(v1, hic)
    vol = d.F003_VOL_M3 if "volume" in decided else g["R324_F003_VOL_M3"]
    feed2_m = m_p1
    if "B-63" in decided:       # ---- the leg's strength, anchored (the port's line) ----
        w1_live = clamp(g["R324_W_EV1"] + (w_e001.get("Urea", 0.0) - g["W_S401"]["Urea"]),
                        0.0, 1.0)
    cp_feed2 = g["urea_soln_cp"](w1_live, T_e001)
    cp_hold2 = g["urea_soln_cp"](s.w_e003.get('Urea', g["R324_W_EV2"]), s.r324_e003_T)
    urea2_in = w1_live * feed2_m
    w_max = um.strength_ceiling(w_e001.get("Urea", 0.0),
                                sum(w_e001.get(k, 0.0) for k in NONVOLATILE if k != "Urea"))

    def w_eq_of(t, p):
        if "B-58" in decided:   # ---- the melt on the refit, under its ceiling (the port's) ----
            return um.equilibrium_urea_fraction(t, p, g["R324_W_EV2"], g["R324_E003_T_SP_C"],
                                                g["R324_F003_P_BARA"],
                                                a_urea_water_k=d.MELT_A_UREA_WATER_K,
                                                w_max=w_max)
        return g["evap_w_eq"](t, p, g["R324_W_EV2"], g["R324_E003_T_SP_C"],
                              g["R324_F003_P_BARA"])

    tic2_op = g["_ctrl_ipd"](s.TIC_324002, s.r324_e003_T, dt)
    pic212_pv = s.r324_e003_chest_P
    pic212_op = g["_ctrl_ipd"](s.PIC_329212, pic212_pv, dt, cas_sp=tic2_op)
    p_9_lagged_e003 = g["_lag1"](s.tlag, "324E003_P_9_thermal", s.steam.P_9,
                                 g["R324_F003_M_TAU_S"], dt)
    p_chest_e003 = g["steam_chest_pressure"](pic212_op, p_9_lagged_e003, g["R324_E003_OP_DES"],
                                             g["R324_E003_PCHEST_DES"], g["R324_E003_UA_KW"],
                                             s.r324_e003_T, g["R324_E003_Q_DES_KW"],
                                             g["steam_system"].P_MP_BARA, s.r324_e003_chest_P)
    s.r324_e003_chest_P = p_chest_e003
    if "valve" in decided:      # ---- PV-324203 on its vendor trim (the port's line) ----
        fa203_m = g["R324_F003_FA_DES"] * (
            cv_fraction(s.PIC_324203["op"] / 100.0, "mod_equal_pct")
            / cv_fraction(d.PV_324203_OP_DES_PCT / 100.0, "mod_equal_pct"))
    else:
        fa203_m = g["R324_F003_FA_DES"] * (s.PIC_324203["op"] / max(g["R324_PV203_OP_DES"],
                                                                   1e-6))
    vac_op = g["_ctrl_ipd"](s.PIC_324203, s.r324_f003_P, dt)
    M_f003_pre = s.r324_f003_M
    _vv_f003 = g["hydraulics"].vapour_volume_m3(vol, M_f003_pre, g["R324_F003_RHO_L"])
    t2_old = s.r324_e003_T
    t2_solved = t2_old
    p2_old = s.r324_f003_P
    p2_solved = p2_old
    _tv_e005 = tv_e005
    t2_fp_residual = math.inf
    t2_fp_converged = False
    t2_fp_iterations = 0
    if "B-67" in decided:       # ---- the vent on B-67's departure (V1's module, switched) ----
        spec, vc = switched_specs()["324E005"], switched_module()
    else:
        spec, vc = g["VACUUM_CONDENSER_SPECS"]["324E005"], g["vacuum_condenser"]
    hb = 0.0
    for t2_fp_iterations in range(1, g["R324_PT_LOOP_MAXIT"] + 1):
        Q_e003_kw = max(g["R324_E003_UA_KW"] * (g["tsat_steam"](p_chest_e003) - t2_solved), 0.0)
        w_eq2 = w_eq_of(t2_solved, p2_solved)
        v2_m = clamp(feed2_m - urea2_in / max(w_eq2, 1e-6), 0.0, feed2_m)
        pwr2 = (feed2_m / 3600.0 * cp_feed2 * (T_e001 - t2_solved)
                + Q_e003_kw - v2_m / 3600.0 * g["R324_LAM_V2"])
        k_cap2 = (feed2_m / 3600.0 * cp_feed2
                  + (g["R324_E003_UA_KW"] if Q_e003_kw > 0.0 else 0.0))
        t2_next = t2_old + pwr2 * dt / max(M_f003_pre * cp_hold2 + k_cap2 * dt, 1e-6)
        m709_fp = (g["VACUUM_CONDENSERS"]["324E005"]["inlet_kgh"]
                   + (v2_m - g["R324_V2_DES"]) + (fa203_m - g["R324_F003_FA_DES"]))
        boil_at = None
        if "B-62" in decided:   # ---- the held melt boils at the trial vacuum (the port's call) --
            def _boil(p, t_step=t2_next, c_step=max(M_f003_pre * cp_hold2 + k_cap2 * dt, 1e-6)):
                return holdup_boil(
                    t_step, p, M_f003_pre, s.w_e003, c_step, g["R324_LAM_V2"],
                    g["sol_vapour_y"](s.w_e003, g["SOL_E003"]["alpha"]).get("Urea", 0.0), 1.0,
                    dt, w_des=g["W_S402"]["Urea"], t_des_c=g["R324_E003_T_SP_C"],
                    p_des_bara=g["R324_F003_P_BARA"], a_urea_water_k=d.MELT_A_UREA_WATER_K)

            boil_at = _boil

            def n709_at(p, m=m709_fp, boil_at=boil_at):
                return g["vacuum_inlet_kmolh"]("324E005", m + boil_at(p)[0], fa203_m,
                                               g["R324_F003_FA_DES"])
            _n709 = n709_at(p2_solved)
        else:
            _n709 = g["vacuum_inlet_kmolh"]("324E005", m709_fp, fa203_m, g["R324_F003_FA_DES"])
        _bp709 = vc.condensate_back_pressure(_n709, _tv_e005)

        def _dpdt_f003(p):
            n = n709_at(p) if boil_at is not None else _n709
            vent = vc.vent_kgh_at(spec, p, _tv_e005, n, _bp709)
            return g["hydraulics"].vessel_dpdt(p, t2_solved + 273.15, _vv_f003,
                                               g["R324_F003_MW_VAP"],
                                               vent / g["R324_F003_MW_VAP"],
                                               pull(p) / g["R324_F003_MW_VAP"])

        p2_next = g["_backward_euler_p"](p2_old, dt, _dpdt_f003, 0.02, 1.0)
        if boil_at is not None:
            hb, t2_next = boil_at(p2_next)
        t2_fp_residual = max(abs(p2_next - p2_solved), abs(t2_next - t2_solved))
        if t2_fp_residual <= g["R324_PT_LOOP_TOL"]:
            p2_solved = p2_next
            t2_solved = t2_next
            t2_fp_converged = True
            break
        p2_solved = p2_next
        t2_solved = t2_next
    s.r324_e003_T = t2_solved
    s.r324_f003_P = p2_solved
    w_eq2 = w_eq_of(s.r324_e003_T, s.r324_f003_P)
    v2_m = clamp(feed2_m - urea2_in / max(w_eq2, 1e-6), 0.0, feed2_m)
    Q_e003_kw = max(g["R324_E003_UA_KW"] * (g["tsat_steam"](p_chest_e003) - s.r324_e003_T), 0.0)
    steam = Q_e003_kw / g["R324_E003_LAM_STEAM"] * 3600.0     # s.steam.m_users9's term, per hour
    if "B-58" in decided:
        diag = um.melt_diagnostics(s.r324_e003_T, s.r324_f003_P, w_eq2,
                                   a_urea_water_k=d.MELT_A_UREA_WATER_K)
    else:
        diag = g["evap_thermo_diag"](s.r324_e003_T, s.r324_f003_P, w_eq2)
    p2_gen = max(feed2_m - v2_m, 0.0)
    w2_live = clamp(urea2_in / max(p2_gen, 1e-6), 0.0, 1.0)
    lvl_f003 = clamp(s.r324_f003_M / g["R324_F003_M_FULL"] * 100.0, 0.0, 100.0)
    lic501_op = g["_ctrl_ipd"](s.LIC_324501, lvl_f003, dt)
    routed_op = clamp(lic501_op, 0.0, 100.0)
    recycle_selected = p335 > g["R335_LVB_RELIEF_BARG"]
    lva_stroke = 0.0 if recycle_selected else routed_op
    lvb_stroke = routed_op if recycle_selected else 0.0
    m_402g = routed_op / 100.0 * g["R324_LVA_SPAN"]
    if "heel" in decided:       # ---- the drain above its floor (the port's lines) ----
        _avail = (max(M_f003_pre - 1.0, 0.0) / max(dt, 1.0e-9) * 3600.0
                  + feed2_m - v2_m - hb)
        if m_402g > _avail:
            m_402g = _avail
    route501 = g["route_lv324501"](m_402g, s.w_e003, s.r324_e003_T, recycle_selected,
                                   uf_ratio=0.0)
    m_f003_out = m_402g
    s.r324_f003_M = max(M_f003_pre + (feed2_m - v2_m - hb - m_f003_out) / 3600.0 * dt, 1.0)
    w_pre = s.w_e003
    y_v2 = g["sol_vapour_y"](s.w_e003, g["SOL_E003"]["alpha"])
    xi_e003 = g["sol_biuret_xi"]("E003", M_f003_pre, s.w_e003, s.r324_e003_T)
    s.w_e003 = g["sol_advance"](s.w_e003, M_f003_pre, s.r324_f003_M, feed2_m, w_e001,
                                v2_m + hb, y_v2, m_f003_out, xi_e003, dt)   # pin: identity
    m709 = (g["VACUUM_CONDENSERS"]["324E005"]["inlet_kgh"] + (v2_m + hb - g["R324_V2_DES"])
            + (fa203_m - g["R324_F003_FA_DES"]))
    return {
        "feed": (feed2_m, T_e001, urea2_in, cp_feed2),
        "ctl": (tic2_op, pic212_op, p_chest_e003, Q_e003_kw, steam, fa203_m, vac_op),
        "melt": (w_max if "B-58" in decided else None, w_eq2, v2_m, hb, m709),
        "fp": (t2_fp_iterations, t2_fp_residual, t2_fp_converged, diag),
        "out": (p2_gen, w2_live, lvl_f003, lic501_op, recycle_selected, lva_stroke, lvb_stroke,
                m_402g, y_v2, xi_e003),
        "route": route501,
        "w_pre": w_pre,
    }


def _assert_tick(a, b: se.SecondEvaporatorResult, s, unit, loops, label):
    assert a["feed"] == (b.feed_kgh, b.feed_t_c, b.feed_urea_kgh, b.feed_cp), label
    assert a["ctl"] == (b.tic_op_bara, b.pic_op_pct, b.chest_p_bara, b.q_kw, b.steam_kgh,
                        b.false_air_kgh, b.vacuum_op_pct), label
    assert a["melt"][1:] == (b.w_eq, b.m_vap_kgh, b.m_boil_kgh, b.m_709_kgh), label
    if a["melt"][0] is not None:
        assert a["melt"][0] == b.w_max, label
    assert a["fp"] == (b.iterations, b.residual, b.converged,
                       (b.thermo_validity, b.thermo_px_residual_bara)), label
    assert a["out"] == (b.melt_kgh, b.w_melt, b.level_pct, b.level_op_pct, b.recycle_selected,
                        b.lv_a_pct, b.lv_b_pct, b.m_402_kgh, b.y_vap, b.xi_kmolh), label
    r = a["route"]
    assert (r["route"], r["forward_kgh"], r["forward_comp"], r["forward_T_C"], r["recycle_kgh"],
            r["recycle_comp"], r["recycle_T_C"]) == (
        b.route.route, b.route.forward_kgh, b.route.forward_w, b.route.forward_t_c,
        b.route.recycle_kgh, b.route.recycle_w, b.route.recycle_t_c), label
    assert (s.r324_f003_M, s.r324_e003_T, s.r324_f003_P, s.w_e003, s.r324_e003_chest_P) == (
        unit.m_kg, unit.t_c, unit.p_bara, unit.w, unit.chest_p_bara), label
    for v1c, loop in ((s.TIC_324002, loops.tic), (s.PIC_329212, loops.pic),
                      (s.PIC_324203, loops.vacuum), (s.LIC_324501, loops.level)):
        assert (v1c["op"], v1c["sp"], v1c["pv"], v1c["pv1"], v1c["pv2"], v1c["mode"]) == (
            loop.op, loop.sp, loop.pv, loop.pv1, loop.pv2, loop.mode), (label, loop.tag)


#: Stage 1's melt at design, and a weaker one.
W401 = dict(d.W_S401)
W401_WEAK = dict(W401)
W401_WEAK["Urea"] = W401["Urea"] - 0.01
W401_WEAK["H2O"] = W401["H2O"] + 0.01


def _design(v1, **over):
    base = {"m": d.P1_DES_KGH, "w_live": d.E001_W_UREA_DES, "t1": d.E001_T_DES_C, "w1": W401,
            "p9": 9.0, "hic": 50.0, "pd": d.E006_P_DES_BARA, "p335": d.PIC_335201_DES_BARG,
            "tv": switched_specs()["324E005"]["t_v_solved_des"]}
    base.update(over)
    return base


def port_step(unit, loops, x):
    """The port's tick on a scenario's inputs: 324F004's motive pressure from HIC-329606, and the
    granulator's header valves online where the scenario names them (AC4's header, decision 224;
    V1 has none)."""
    return unit.step(loops, x["m"], x["t1"], x["w1"], x["p9"], motive_bara(x["hic"]), x["pd"],
                     x["tv"], x["p335"], DT,
                     **({"headers_online": x["headers"]} if "headers" in x else {}))


def _run(v1, script, n_ticks, decided=ALL, check=True, setup=None):
    """Drive V1's transcription and the port side by side; `script(k)` gives tick k's inputs."""
    s = _v1_state(v1, decided)
    # V1's linear chest valve and drain: PV-329212's and LV-324501's vendor trims are proved in
    # their decided tests.
    unit = se.SecondEvaporator(chest=se.V1_CHEST, backward_species=False, seal_air=False,
                               bisect_fixed_point=False, vendor_drain=False,
                               ac4_header=False)
    loops = se.SecondEvaporatorLoops(pic=se.pic_329212(se.V1_CHEST),
                                     level=se.lic_324501(vendor=False))
    if setup:
        setup(s, loops)
    b = None
    for k in range(n_ticks):
        x = script(k)
        s.steam.P_9 = x["p9"]
        a = _v1_stage2(v1, s, x["m"], x["w_live"], x["t1"], x["w1"], x["hic"], x["pd"], x["tv"],
                       x["p335"], DT, decided)
        b = port_step(unit, loops, x)
        if check:
            _assert_tick(a, b, s, unit, loops, k)
    return s, unit, loops, b


def _step(v1, k0, **over):
    return lambda k: _design(v1, **(over if k >= k0 else {}))


def test_the_port_uses_v1s_design_basis(v1):
    """The stage's design numbers, ``==`` V1's: the separator, the duty on V1's own anchor (the
    decided chest re-derives the conductance), the drain, the species anchor."""
    assert (d.P2_DES_KGH, d.V2_DES_KGH, d.F003_M_DES_KG, d.F003_M_FULL_KG, d.E003_Q_DES_KW) == (
        v1["R324_P2_DES"], v1["R324_V2_DES"], v1["R324_F003_M_DES"], v1["R324_F003_M_FULL"],
        v1["R324_E003_Q_DES_KW"])
    assert (d.F003_RHO_L, d.F003_MW_VAP, d.E003_LAMBDA_KJKG, d.E003_LAMBDA_STEAM_KJKG) == (
        v1["R324_F003_RHO_L"], v1["R324_F003_MW_VAP"], v1["R324_LAM_V2"],
        v1["R324_E003_LAM_STEAM"])
    assert (d.LIC_324501_OP_DES_PCT, d.LV_324501_SPAN_KGH, d.PIC_335201_RELIEF_BARG,
            d.PIC_335201_DES_BARG) == (v1["R324_LIC501_OP_DES"], v1["R324_LVA_SPAN"],
                                       v1["R335_LVB_RELIEF_BARG"], v1["R335_PIC201_DES_BARG"])
    c = v1["__chest__"]
    assert d.E003_UA_KW == c["R324_E003_UA_KW"]
    assert (v1["R324_E003_PCHEST_DES"], v1["R324_E003_OP_DES"]) == (8.1, 90.0)
    assert v1["R324_E003_OP_DES"] / 100.0 * v1["steam_system"].P_MP_BARA == pytest.approx(
        v1["R324_E003_PCHEST_DES"], rel=1e-15)
    assert (d.W_S401, d.W_S402, d.E001_W_UREA_DES) == (v1["W_S401"], v1["W_S402"],
                                                        v1["R324_W_EV1"])
    a = d.E003_LIQUOR.anchor
    assert (a.xi, a.y, a.alpha, a.resid, a.entrain) == (
        v1["SOL_E003"]["xi"], v1["SOL_E003"]["y"], v1["SOL_E003"]["alpha"],
        v1["SOL_E003"]["resid"], v1["SOL_E003"]["entrain"])


@pytest.mark.parametrize("name, n, over", [
    ("design", 300, {}),
    ("feed -10 %", 3000, {"m": 0.9 * d.P1_DES_KGH}),
    ("feed 5 K colder", 3000, {"t1": 125.0}),
    ("9-bar header -10 %", 3000, {"p9": 8.1}),
    ("weaker feed", 3000, {"w_live": 0.9331, "w1": W401_WEAK}),
    ("motive halved", 3000, {"hic": 25.0}),
    ("cold end +3 K", 2000, {"tv": None}),
    ("335 header backs up", 1000, {"p335": 4.0}),
    ("feed lost", 3000, {"m": 0.0}),
])
def test_stage_2_is_v1s_tick_by_tick(v1, name, n, over):
    """Each scenario stepped in at tick 5 and held: every published field, the separator's whole
    state, the route and the four controllers ``==`` on every tick."""
    if "tv" in over:
        over = {"tv": switched_specs()["324E005"]["t_v_solved_des"] + 3.0}
    _run(v1, _step(v1, 5, **over), n)


def test_a_feed_loss_with_the_drain_wide_open_stops_at_the_heel(v1):
    """LIC-324501 in MAN at 100 % with the feed lost: the drain empties 324F003 to its 1 kg floor
    and no further."""
    def setup(s, loops):
        s.LIC_324501["mode"], s.LIC_324501["op"] = "MAN", 100.0
        loops.level.mode, loops.level.op = "MAN", 100.0
    _, unit, _, b = _run(v1, _step(v1, 5, m=0.0), 2000, setup=setup)
    assert unit.m_kg == pytest.approx(1.0, abs=1e-9) and b.m_402_kgh >= 0.0


def test_set_point_steps_are_v1s(v1):
    """TIC-324002 to 142 C and PIC-324203 to 0.12 bar a at tick 5, 3000 ticks."""
    s = _v1_state(v1)
    # V1's linear chest valve and drain: PV-329212's and LV-324501's vendor trims are proved in
    # their decided tests.
    unit = se.SecondEvaporator(chest=se.V1_CHEST, backward_species=False, seal_air=False,
                               bisect_fixed_point=False, vendor_drain=False,
                               ac4_header=False)
    loops = se.SecondEvaporatorLoops(pic=se.pic_329212(se.V1_CHEST),
                                     level=se.lic_324501(vendor=False))
    for k in range(3000):
        if k == 5:
            for c, loop, sp in ((s.TIC_324002, loops.tic, 142.0),
                                (s.PIC_324203, loops.vacuum, 0.12)):
                c["sp"] = sp
                loop.sp = sp
        x = _design(v1)
        a = _v1_stage2(v1, s, x["m"], x["w_live"], x["t1"], x["w1"], x["hic"], x["pd"], x["tv"],
                       x["p335"], DT)
        b = port_step(unit, loops, x)
        _assert_tick(a, b, s, unit, loops, k)


@pytest.mark.parametrize("m, recycle", [(75938.1, False), (75938.1, True), (0.0, False)])
def test_the_selector_is_v1s(v1, m, recycle):
    """`melt_route` against V1's ``route_lv324501`` at ``uf_ratio=0``: both routes and an empty
    drain, every field ``==``."""
    for w in (d.W_S402, {k: 2.0 * v for k, v in d.W_S402.items()}):
        r = v1["route_lv324501"](m, w, 140.3, recycle, uf_ratio=0.0)
        p = melt_route(m, w, 140.3, recycle)
        assert (r["route"], r["forward_kgh"], r["forward_comp"], r["forward_T_C"],
                r["recycle_kgh"], r["recycle_comp"], r["recycle_T_C"], r["uf85_kgh"]) == (
            p.route, p.forward_kgh, p.forward_w, p.forward_t_c, p.recycle_kgh, p.recycle_w,
            p.recycle_t_c, 0.0)
