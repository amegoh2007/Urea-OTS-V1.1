"""V1 <-> V1.1 equivalence for 323E010 / 323F010, stage 3 of unit 323.

What is being proved
--------------------
V1 writes stage 3 inline in `step_sim`, so the statements that wire it are TRANSCRIBED into
`_v1_stage3` below, line for line, and declared as such: the 323F004 -> 323F010 drain packet
and its transport (``main.py`` 8460-8469) and the pre-evaporator itself (8509-8654). Everything
they call is V1's own code, executed: ``_ctrl_ipd``, ``_lag1``, ``steam_chest_pressure``,
``tsat_steam``, ``gravity_outflow_323f010``, ``hv323605_flow_kgh``, ``sol_bubble_t_dep``,
``sol_vapour_y_vle``, ``sol_biuret_xi``, ``sol_advance``, ``_cq_packet``, ``urea_soln_cp`` and
``urea_soln_rho`` lifted out of ``main.py``; ``hydraulics`` and ``consequence`` loaded as real
modules. The TIC-323012 / PIC-329208 seeds live inside ``State.__init__`` and are transcribed
from ``main.py`` 6682-6691.

Three cp values V1 evaluates at the top of the tick (``main.py`` 8250-8252) are transcribed onto
the states they read there: ``cp_f004`` on the drum state the drain departs at, ``cp_f010`` on
the separator state before stage 3 runs, and ``cp_331`` on the constant PFD 331.

The design vapour and its molar mass (``main.py`` 2881-2886) are module-level calls that need
the 323F010 volatility memo, which V1 fills with a bare call at 2876; they are lifted in a
second pass after that call, as V1's import order has it.

Stage 3 is driven on its own through scripted scenarios, and then coupled to stage 2 — V1's
stage-2 transcription (`test_flash_tank_equivalence._v1_stage2`) feeding V1's stage 3 while the
ported 323F004 feeds the ported 323F010 — and to stages 1 and 2 together. Every tick compares
every published field, the whole separator state and both controllers with ``==``.

The telemetry writes feed nothing and are not driven.

The product line (handoff B-21, decided 2026-09-30). The port's line delivers the live
departure flow and delays only the liquor's temperature, composition and cp. The transcription
carries the same switch, ``line_decided`` (default True): a property packet on a unit flow
through V1's own FIFO, and the live flow delivered; ``line_decided=False`` is V1 verbatim. A
settled line is the same float either way.

The chest and its cascade (decided 2026-09-30, As-Built §XL.1-2). The port anchors 323E010's
chest on PFD 926's and its datasheet's 2.5 bar a, where V1 anchors on 1.76; runs PIC-329208 on
the DCS table's gain per cent of PT-329208's span, without V1's chest-gain scale; and runs
TIC-323012, which has no table row, on its sibling TIC-323007's row on its own spans. The
transcription carries the switch ``chest_decided`` (default True): V1's own stroke and
conductance expressions (``main.py`` 1098 and 1182) re-executed on 2.5 bar a, and the decided
gains in the controller seeds; ``chest_decided=False`` is V1 verbatim. The last section runs
the two side by side.

The barometric leg's heel (handoff B-29, decided 2026-09-27): ``heel_decided`` (default True)
caps the leg at the liquid above the 1 kg heel net of the evaporation, the port's line;
``heel_decided=False`` is V1's cap. Inert away from the heel.

The held liquor boils (handoff B-24, decided 2026-10-02, B-62's class): ``boil_decided``
(default True) calls the port's `holdup_boil.liquor_boil` on V1's own bubble point,
``sol_bubble_t_dep`` at the trial PT-323204, inside V1's pressure step; its vapour joins the
evaporation in the vapour space, the swell, the drain's cap, the mass and the species, the
pressure step held on the temperature step before the boil, as the port has it.
``boil_decided=False`` is V1 verbatim.
"""

from __future__ import annotations

import math

import pytest

from ureasim.data import unit_323 as d
from ureasim.data.design_point import R323_FEED_DES_KGH as FEED_DES
from ureasim.data.design_point import R323_M314_DES, R323_M317_DES, R323_M319_DES
from ureasim.data.unit_329 import P_LP_BARA
from ureasim.units.evaporation.holdup_boil import liquor_boil
from ureasim.units.recirc import flash_tank as ft
from ureasim.units.recirc import pre_evaporator as pe
from ureasim.units.recirc import rectifying_column as rc
from tests.equivalence import b20_switch, routes_switch
from tests.equivalence import test_flash_tank_equivalence as stage2
from tests.equivalence import test_rectifying_column_equivalence as stage1
from tests.equivalence.v1_loader import lift, load, v1_available, v1_service

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

V1_NAMES = stage2.V1_NAMES + [
    "W_S317", "W_S331", "SOL_F010", "MW_SOL", "SOL_VLE_DOMAIN",
    "R323_CP_F010_DES", "R323_CP_S331_DES", "R323_M331_DES", "R323_M331_T_C",
    "R323_F010_T_SP_C", "R323_F010_M_TAU_S", "R323_F010_LVL_SP", "R323_F010_M_DES",
    "R323_F010_M_FULL", "R323_F010_TBUB_DES", "R323_F010_ID_M", "R323_F010_SHELL_M",
    "R323_F010_VOL_M3", "R323_F010_AREA_M2", "R323_MEVAP_DES", "R323_M317_DES",
    "R323_PHI_VEVAP", "R323_EVAP_LAMBDA", "R323_E010_PCHEST_DES", "R323_E010_OP_DES",
    "R323_E010_Q_DES_KW", "R323_E010_UA_KW", "R323_QEVAP_DES_KW", "R323_D002_RHO",
    "R323_HIC605_DES_PCT", "R323_HV605_CHAR", "R324_F001_P_BARA", "PIC_329208_KC_SCALE",
    "gravity_outflow_323f010", "hv323605_flow_kgh",
]

DT = 0.1

#: The decided chest anchor [bar a] and cascade gains, written from their sources: PFD 926 and
#: 323E010's DDS (UD-AU-323-EC-0009, 2.5 bar a); TIC-323007's table row, 2.00 and 500 s, on
#: TT-323012's 160 K onto PT-329208's 6 bar [bar/K]; the table's 0.20 on PT-329208's 6 bar [%/bar].
DECIDED_E010_PCHEST_BARA = 2.5
DECIDED_TIC_323012_KC = 2.0 * 6.0 / 160.0
DECIDED_TIC_323012_TI_S = 500.0
DECIDED_PIC_329208_KC = 0.2 * 100.0 / 6.0


def build_v1(names: list = None) -> dict:
    """The V1 namespace stages 1 to 3 run on — ``names`` lifted, the stage memos filled — so a
    later stage's test can lift its own names on top of it."""
    coupling = load("c003_pressure_coupling")
    ns = lift(b20_switch.names(V1_NAMES if names is None else names), seed=b20_switch.seed({
        "math": math,
        "iapws_if97": load("iapws_if97"),
        "thermo_service": v1_service(),
        "hydraulics": load("hydraulics"),
        "consequence": load("consequence"),
        "steam_system": load("steam_system"),
        "c003_pressure_target_bara": coupling.c003_pressure_target_bara,
    }))
    # main.py 2615, 2618, 2628, 2874-2876: the three stage design memos (bare calls).
    ns["_sol_tbub_anchor"]("C003", ns["W_S314"], ns["R323_C003_P_BARA"])
    ns["_sol_tbub_anchor"]("F004", ns["W_S319"], ns["R323_F004_P_BARA"])
    ns["_sol_tbub_anchor"]("F010", ns["W_S317"], ns["R323_F010_P_BARA"])
    ns["_sol_alpha_anchor"]("C003", ns["W_S314"], ns["R323_C003_T_SP_C"], ns["R323_C003_P_BARA"])
    ns["_sol_alpha_anchor"]("F004", ns["W_S319"], ns["R323_F004_T_SP_C"], ns["R323_F004_P_BARA"])
    ns["_sol_alpha_anchor"]("F010", ns["W_S317"], ns["R323_F010_T_SP_C"], ns["R323_F010_P_BARA"])
    # main.py 2881-2886, second pass, after the F010 memo exists.
    tear = lift(["SOL_F010_Y_DES", "R323_F010_MW_VAP_DES"], seed=dict(ns))
    ns["SOL_F010_Y_DES"] = tear["SOL_F010_Y_DES"]
    ns["R323_F010_MW_VAP_DES"] = tear["R323_F010_MW_VAP_DES"]
    # main.py 2730-2736, the three unit-323 rows of SOL_STAGES; second pass.
    stages = {
        "C003": {"w": ns["W_S314"], "a": ns["SOL_C003"], "M": ns["R323_C003_M_DES"],
                 "T": ns["R323_C003_T_SP_C"]},
        "F004": {"w": ns["W_S319"], "a": ns["SOL_F004"], "M": ns["R323_F004_M_DES"],
                 "T": ns["R323_F004_T_SP_C"]},
        "F010": {"w": ns["W_S317"], "a": ns["SOL_F010"], "M": ns["R323_F010_M_DES"],
                 "T": ns["R323_F010_T_SP_C"]},
    }
    ns["sol_biuret_xi"] = lift(["sol_biuret_xi"], seed={
        "math": math, "SOL_STAGES": stages, "SOL_BIU_EA": ns["SOL_BIU_EA"],
        "SOL_BIU_ORDER": ns["SOL_BIU_ORDER"], "STRIP_R_GAS_J": ns["STRIP_R_GAS_J"],
    })["sol_biuret_xi"]
    # main.py 6239, 6241 and 6243: V1's own route objects for the three lines.
    # The isometrics' geometry (handoff A-11, decided 2026-10-07): `routes_switch`.
    ns["FEED_ROUTE"] = routes_switch.decided(ns, "322E001_TO_323C003")
    ns["INLET_ROUTE"] = routes_switch.decided(ns, "323C003_TO_323F004")
    ns["F010_ROUTE"] = routes_switch.decided(ns, "323F004_TO_323F010")
    return ns


@pytest.fixture(scope="module")
def v1():
    return build_v1()


def _decided(v1):
    """V1's namespace on the decided 323E010 anchor: ``R323_E010_OP_DES`` and ``R323_E010_UA_KW``
    re-executed from V1's own statements on 2.5 bar a; everything else the same objects."""
    if "__e010_decided__" not in v1:
        derived = ("R323_E010_OP_DES", "R323_E010_UA_KW")
        seed = {k: val for k, val in v1.items() if k not in derived}
        seed["R323_E010_PCHEST_DES"] = DECIDED_E010_PCHEST_BARA
        v1["__e010_decided__"] = lift(list(derived), seed=seed)
    return v1["__e010_decided__"]


def _v1_state(v1, chest_decided: bool = True, valves_decided: bool = True):
    """The V1 plant-state fields stages 1 to 3 read and write, seeded as `State.__init__` seeds
    them (stages 1 and 2 from their own tests, stage 3 from ``main.py`` 6614, 6627, 6645-6647,
    6682-6691, 6767 and 6800, and the 324E002 shell from its design vacuum). `chest_decided`
    seeds both chests' decided anchors and gains; `valves_decided` stages 1 and 2's vendor
    valves (B-44)."""
    g = _decided(v1) if chest_decided else v1
    tic_kc, tic_ti = ((DECIDED_TIC_323012_KC, DECIDED_TIC_323012_TI_S) if chest_decided
                      else (3.6, 1200.0))
    pic_kc = DECIDED_PIC_329208_KC if chest_decided else 0.2 * g["PIC_329208_KC_SCALE"]
    s = stage2._v1_state(v1, chest_decided=chest_decided, valves_decided=valves_decided)
    s.w_f010 = dict(g["W_S317"])
    s.y_evap_f010 = dict(g["SOL_F010_Y_DES"])
    s.r323_f010_M = g["R323_F010_M_DES"]
    s.r323_f010_T = g["R323_F010_T_SP_C"]
    s.r323_f010_P = g["R323_F010_P_BARA"]
    s.r323_e010_chest_P = g["R323_E010_PCHEST_DES"]
    s.HIC_323605 = g["R323_HIC605_DES_PCT"]
    s.r324_f001_P = g["R324_F001_P_BARA"]
    s.TIC_323012 = {"mode": "AUTO", "op": g["R323_E010_PCHEST_DES"],
                    "sp": g["R323_F010_T_SP_C"], "pv": g["R323_F010_T_SP_C"],
                    "pv1": g["R323_F010_T_SP_C"], "pv2": g["R323_F010_T_SP_C"],
                    "Kc": tic_kc, "Ti": tic_ti, "Td": 0.0, "act": +1.0,
                    "op_lo": 0.0, "op_hi": g["R323_P_STEAM_SUP"], "sp_lo": 50.0, "sp_hi": 130.0}
    s.PIC_329208 = {"mode": "CAS", "op": g["R323_E010_OP_DES"],
                    "sp": g["R323_E010_PCHEST_DES"], "pv": g["R323_E010_PCHEST_DES"],
                    "pv1": g["R323_E010_PCHEST_DES"], "pv2": g["R323_E010_PCHEST_DES"],
                    "Kc": pic_kc, "Ti": 60.0, "Td": 0.0, "act": +1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0, "sp_hi": g["R323_P_STEAM_SUP"]}
    return s


def _v1_stage3(v1, s, m_319: float, T_dep_319: float, w_dep_319: dict, blow: tuple,
               dt: float, line_decided: bool = True, chest_decided: bool = True,
               heel_decided: bool = True, boil_decided: bool = True) -> dict:
    """V1 `main.py` 8460-8469 and 8509-8654, stage 3, TRANSCRIBED line for line.
    `line_decided` puts the port's inlet line in V1's (handoff B-21); `chest_decided` the port's
    chest anchor; `heel_decided` the port's drain cap (B-29); `boil_decided` the held liquor's
    boil-off (B-24)."""
    g = _decided(v1) if chest_decided else v1
    clamp = g["clamp"]
    _cp = lambda w, T, des: g["R323_CP_SOLN"] + (g["urea_soln_cp"](w, T) - des)  # noqa: E731
    blow_323505_kgh, n_blow_323505, y_blow_323505 = blow
    # main.py 8250-8252, on the states they read at the top of the tick (module docstring).
    cp_f004 = _cp(w_dep_319.get("Urea", 0.0), T_dep_319, g["R323_CP_F004_DES"])
    cp_f010 = _cp(s.w_f010.get("Urea", 0.0), s.r323_f010_T, g["R323_CP_F010_DES"])
    cp_331 = _cp(g["W_S331"]["Urea"], g["R323_M331_T_C"], g["R323_CP_S331_DES"])
    # main.py 8460-8469, the 323F004 -> 323F010 line. _transport_process, less its telemetry:
    # B-21, decided 2026-09-30: with `line_decided`, the port's lines — a property packet on the
    # unit flow through V1's own FIFO, and the live departure flow delivered.
    _pkt_dep_319 = g["_cq_packet"](1.0 if line_decided else m_319, T_dep_319, w_dep_319,
                                   cp_f004)
    _pkt_arr_319 = g["consequence"].transport_process_packet(
        s.tlag, "PROCESS_323F004_TO_323F010", _pkt_dep_319, g["F010_ROUTE"], m_319, dt)
    if _pkt_arr_319 == _pkt_dep_319:
        m_319_in, T_319_in, w_319_in, cp_319_in = m_319, T_dep_319, w_dep_319, cp_f004
    else:
        m_319_in = m_319 if line_decided else _pkt_arr_319.mass_kgh
        T_319_in = _pkt_arr_319.temperature_c
        w_319_in = g["_w_norm"](_pkt_arr_319.mass_fraction, w_dep_319)
        cp_319_in = _cp(w_319_in.get("Urea", 0.0), T_319_in, g["R323_CP_F004_DES"])
    # main.py 8517-8654, the pre-evaporator.
    m_331 = g["R323_M331_DES"]
    tic12_op = g["_ctrl_ipd"](s.TIC_323012, s.r323_f010_T, dt)
    pic08_pv = s.r323_e010_chest_P
    pic08_op = g["_ctrl_ipd"](s.PIC_329208, pic08_pv, dt, cas_sp=tic12_op)
    p_lp_lagged_f010 = g["_lag1"](s.tlag, "323F010_P_LP_thermal", s.steam.P_LP,
                                  g["R323_F010_M_TAU_S"], dt)
    p_chest_e010 = g["steam_chest_pressure"](pic08_op, p_lp_lagged_f010, g["R323_E010_OP_DES"],
                                             g["R323_E010_PCHEST_DES"], g["R323_E010_UA_KW"],
                                             s.r323_f010_T, g["R323_E010_Q_DES_KW"],
                                             g["R323_P_STEAM_SUP"], s.r323_e010_chest_P)
    s.r323_e010_chest_P = p_chest_e010
    Q_e010_kw = max(g["R323_E010_UA_KW"] * (g["tsat_steam"](p_chest_e010) - s.r323_f010_T), 0.0)
    qevap_avail_kw = (m_319_in / 3600.0 * cp_319_in * (T_319_in - s.r323_f010_T)
                      + m_331 / 3600.0 * cp_331 * (g["R323_M331_T_C"] - s.r323_f010_T)
                      + Q_e010_kw)
    T_bub_f010 = g["sol_bubble_t_dep"]("F010", s.w_f010, g["R323_F010_P_BARA"],
                                       g["R323_F010_T_SP_C"], g["R323_F010_TBUB_DES"])
    qevap_relax_kw = (s.r323_f010_M * cp_f010 * (T_bub_f010 - s.r323_f010_T)
                      / g["R323_F010_M_TAU_S"])
    m_evap = min(g["R323_MEVAP_DES"] * ((m_319_in + m_331)
                                        / (g["R323_M319_DES"] + g["R323_M331_DES"])),
                 max(g["R323_MEVAP_DES"] * ((qevap_avail_kw - qevap_relax_kw)
                                            / g["R323_QEVAP_DES_KW"]), 0.0))
    m_317 = g["gravity_outflow_323f010"](s.r323_f010_M, s.r323_f010_P)
    if heel_decided:            # ---- B-29: the liquid above the heel (the port's line) ----
        _m317_avail = (max(s.r323_f010_M - 1.0, 0.0) / max(dt, 1.0e-9) * 3600.0
                       + m_319_in + m_331 - m_evap)
    else:
        _m317_avail = s.r323_f010_M / max(dt, 1.0e-9) * 3600.0 + m_319_in + m_331
    if m_317 > _m317_avail:
        m_317 = _m317_avail
    dep317 = (s.r323_f010_T, s.w_f010)          # _cq_packet(m_317, s.r323_f010_T, s.w_f010, ...)
    P_f010 = (m_319_in / 3600.0 * cp_319_in * (T_319_in - s.r323_f010_T)
              + m_331 / 3600.0 * cp_331 * (g["R323_M331_T_C"] - s.r323_f010_T)
              + Q_e010_kw - m_evap / 3600.0 * g["R323_EVAP_LAMBDA"])
    M_f010_pre = s.r323_f010_M
    k_cap_f010 = (m_319_in / 3600.0 * cp_319_in + m_331 / 3600.0 * cp_331
                  + (g["R323_E010_UA_KW"] if Q_e010_kw > 0.0 else 0.0))
    _w_pre = s.w_f010
    _c_step = max(M_f010_pre * cp_f010 + k_cap_f010 * dt, 1e-6)
    s.r323_f010_T = s.r323_f010_T + P_f010 * dt / max(M_f010_pre * cp_f010 + k_cap_f010 * dt,
                                                      1e-6)
    _t_step = s.r323_f010_T
    if not boil_decided:
        s.r323_f010_M = max(M_f010_pre + (m_319_in + m_331 - m_evap - m_317) / 3600.0 * dt,
                            1.0)
    _y_tear = s.y_evap_f010
    _mw_evap = 1.0 / max(sum(_y_tear.get(k, 0.0) / g["MW_SOL"][k] for k in g["SOL_SPECIES"]),
                         1e-12)
    _rho_f010 = g["urea_soln_rho"](s.w_f010.get("Urea", 0.0), s.r323_f010_T, g["R323_D002_RHO"])
    _vv_f010 = g["hydraulics"].vapour_volume_m3(g["R323_F010_VOL_M3"], M_f010_pre, _rho_f010)
    _dmdt_f010 = (m_319_in + m_331 - m_evap - m_317) / 3600.0
    _dtdt_f010 = P_f010 / max(M_f010_pre * cp_f010, 1e-6)
    _dvvdt_f010 = -_dmdt_f010 / max(_rho_f010, 1e-6)
    _p_e002 = s.r324_f001_P
    _f_ent_f010 = g["SOL_F010"]["entrain"]

    def _boil_at(p):            # ---- B-24: the port's call on V1's bubble point ----
        if not boil_decided:
            return 0.0, _t_step
        y = {k: (1.0 - _f_ent_f010) * _y_tear.get(k, 0.0) + _f_ent_f010 * _w_pre.get(k, 0.0)
             for k in g["SOL_SPECIES"]}
        return liquor_boil(
            _t_step, M_f010_pre, _w_pre, _c_step, g["R323_EVAP_LAMBDA"], y, 1.0, dt,
            lambda w: g["sol_bubble_t_dep"]("F010", w, p, g["R323_F010_T_SP_C"],
                                            g["R323_F010_TBUB_DES"]))

    def _dpdt_f010(p):
        pull = g["hv323605_flow_kgh"](s.HIC_323605, p, _p_e002, s.r323_f010_T, _mw_evap)
        if boil_decided:
            hb_p = _boil_at(p)[0]
            return g["hydraulics"].vessel_dpdt(
                p, s.r323_f010_T + 273.15, _vv_f010, _mw_evap,
                (m_evap + hb_p) / _mw_evap + n_blow_323505, pull / _mw_evap,
                dtdt_k_s=_dtdt_f010, dvvdt_m3_s=-(_dmdt_f010 - hb_p / 3600.0) / max(_rho_f010,
                                                                                    1e-6))
        return g["hydraulics"].vessel_dpdt(
            p, s.r323_f010_T + 273.15, _vv_f010, _mw_evap,
            m_evap / _mw_evap + n_blow_323505, pull / _mw_evap,
            dtdt_k_s=_dtdt_f010, dvvdt_m3_s=_dvvdt_f010)

    _p_f010_old = s.r323_f010_P
    _f_f010 = _dpdt_f010(_p_f010_old)
    _jac_f010 = min((_dpdt_f010(_p_f010_old + 1.0e-6) - _f_f010) / 1.0e-6, 0.0)
    s.r323_f010_P = clamp(_p_f010_old + _f_f010 * dt / (1.0 - _jac_f010 * dt), 0.05, 1.0)
    pull_f010 = g["hv323605_flow_kgh"](s.HIC_323605, s.r323_f010_P, _p_e002, s.r323_f010_T,
                                       _mw_evap)
    hb = 0.0
    if boil_decided:            # ---- B-24: the boil at the pressure the step ended on ----
        hb, s.r323_f010_T = _boil_at(s.r323_f010_P)
        if m_317 > _m317_avail - hb:
            m_317 = _m317_avail - hb
        s.r323_f010_M = max(M_f010_pre + (m_319_in + m_331 - m_evap - hb - m_317) / 3600.0
                            * dt, 1.0)
    sub_703 = None
    if y_blow_323505 is not None and blow_323505_kgh > 0.0:
        sub_703 = (pull_f010 * blow_323505_kgh / max(m_evap + hb + blow_323505_kgh, 1e-9),
                   y_blow_323505)
    y_evap = g["sol_vapour_y_vle"]("F010", s.w_f010, s.r323_f010_T, s.r323_f010_P,
                                   g["SOL_F010"]["alpha"])
    s.y_evap_f010 = y_evap
    y_790 = {k: (1.0 - _f_ent_f010) * y_evap.get(k, 0.0) + _f_ent_f010 * s.w_f010.get(k, 0.0)
             for k in g["SOL_SPECIES"]}
    xi_f010 = g["sol_biuret_xi"]("F010", M_f010_pre, s.w_f010, s.r323_f010_T)
    s.w_f010 = g["sol_advance"](s.w_f010, M_f010_pre, s.r323_f010_M, m_319_in, w_319_in,
                                m_evap + hb, y_790, m_317, xi_f010, dt, m_in2=m_331,
                                w_in2=g["W_S331"])
    return {
        "feed": (m_319_in, T_319_in, w_319_in, cp_319_in), "m331": m_331,
        "tic": tic12_op, "pic": pic08_op, "chest": p_chest_e010, "Q": Q_e010_kw,
        "avail": qevap_avail_kw, "Tbub": T_bub_f010, "relax": qevap_relax_kw,
        "evap": m_evap, "boil": hb, "m317": m_317, "dep317": dep317, "mw": _mw_evap,
        "pull": pull_f010,
        "sub703": sub_703, "y": y_evap, "domain": g["SOL_VLE_DOMAIN"].get("F010"),
        "y790": y_790, "xi": xi_f010,
        "LI": s.r323_f010_M / g["R323_F010_M_FULL"] * 100.0,
    }


def _assert_tick(a: dict, b: pe.PreEvaporatorResult, s, sep, tic, pic, label):
    assert a["feed"] == (b.feed_kgh, b.feed_t_c, b.feed_w, b.feed_cp), label
    assert (a["m331"], a["tic"], a["pic"], a["chest"], a["Q"]) == (
        b.m_331_kgh, b.tic_op_bara, b.pic_op_pct, b.chest_p_bara, b.q_e010_kw), label
    assert (a["avail"], a["Tbub"], a["relax"], a["evap"], a["boil"], a["m317"]) == (
        b.q_avail_kw, b.t_bub_c, b.q_relax_kw, b.m_evap_kgh, b.m_boil_kgh, b.m_317_kgh), label
    assert a["dep317"] == (b.drain_t_c, b.drain_w), label
    assert (a["mw"], a["pull"], a["sub703"]) == (b.mw_vap, b.pull_kgh, b.blowthrough_share), label
    assert (a["y"], a["y790"], a["xi"], a["LI"]) == (b.y_vap, b.y_790, b.xi_kmolh, b.level_pct), \
        label
    assert a["domain"] == b.vapour_domain, label
    assert (s.r323_f010_M, s.r323_f010_T, s.r323_f010_P, s.w_f010, s.r323_e010_chest_P,
            s.y_evap_f010) == (sep.m_kg, sep.t_c, sep.p_bara, sep.w, sep.chest_p_bara,
                               sep.y_vap), label
    assert (b.m_kg, b.t_c, b.p_bara, b.w) == (sep.m_kg, sep.t_c, sep.p_bara, sep.w), label
    for v1c, loop in ((s.TIC_323012, tic), (s.PIC_329208, pic)):
        assert (v1c["op"], v1c["sp"], v1c["pv"], v1c["pv1"], v1c["pv2"], v1c["mode"]) == (
            loop.op, loop.sp, loop.pv, loop.pv1, loop.pv2, loop.mode), (label, loop.tag)


#: The 323F004 drain as the drum publishes it at design.
W319 = dict(d.W_S319)
#: Drum liquor carrying twice the design ammonia, as a poor flash leaves it.
W319_NH3 = dict(W319)
W319_NH3["NH3"] = 2.0 * W319["NH3"]
W319_NH3["H2O"] = W319["H2O"] - W319["NH3"]
NO_BLOW = (0.0, 0.0, None)


def _design(**over):
    base = {"m319": R323_M319_DES, "t319": d.F004_T_SP_C, "w319": W319, "blow": NO_BLOW,
            "hic": d.HIC_323605_DES_PCT, "p_lp": P_LP_BARA, "p_e002": d.P_324E002_DES_BARA}
    base.update(over)
    return base


def _run(v1, script, ticks: int, dt: float = DT, before=None):
    """Drive stage 3 alone through `script(k)`, comparing everything every tick."""
    s = _v1_state(v1)
    sep = pe.PreEvaporator(chest=pe.V1_CHEST, live_bubble=False)
    tic, pic = pe.tic_323012(), pe.pic_329208(pe.V1_CHEST)
    if before:
        before(s, sep, tic, pic)
    for k in range(ticks):
        x = script(k)
        s.HIC_323605 = x["hic"]
        s.steam.P_LP = x["p_lp"]
        s.r324_f001_P = x["p_e002"]
        a = _v1_stage3(v1, s, x["m319"], x["t319"], x["w319"], x["blow"], dt)
        b = sep.step(tic, pic, x["m319"], x["t319"], x["w319"], *x["blow"], x["hic"],
                     x["p_lp"], x["p_e002"], dt)
        _assert_tick(a, b, s, sep, tic, pic, f"tick {k}")
    return s, sep, (tic, pic), b


# --------------------------------------------------------------------------------------
# The design basis
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("ours, theirs", [
    ("W_S317", "W_S317"), ("W_S331", "W_S331"), ("F010_T_SP_C", "R323_F010_T_SP_C"),
    ("F010_M_TAU_S", "R323_F010_M_TAU_S"), ("F010_LVL_SP_PCT", "R323_F010_LVL_SP"),
    ("F010_M_DES_KG", "R323_F010_M_DES"), ("F010_M_FULL_KG", "R323_F010_M_FULL"),
    ("F010_ID_M", "R323_F010_ID_M"), ("F010_SHELL_M", "R323_F010_SHELL_M"),
    ("F010_VOL_M3", "R323_F010_VOL_M3"), ("F010_AREA_M2", "R323_F010_AREA_M2"),
    ("M331_DES_KGH", "R323_M331_DES"), ("M331_T_C", "R323_M331_T_C"),
    ("MEVAP_DES_KGH", "R323_MEVAP_DES"), ("EVAP_LAMBDA_KJKG", "R323_EVAP_LAMBDA"),
    ("CP_F010_DES", "R323_CP_F010_DES"), ("CP_S331_DES", "R323_CP_S331_DES"),
    ("RHO_F010_ANCHOR", "R323_D002_RHO"), ("E010_PCHEST_DES_BARA", "R323_E010_PCHEST_DES"),
    ("E010_OP_DES_PCT", "R323_E010_OP_DES"), ("E010_Q_DES_KW", "R323_E010_Q_DES_KW"),
    ("E010_UA_KW", "R323_E010_UA_KW"), ("QEVAP_DES_KW", "R323_QEVAP_DES_KW"),
    ("HIC_323605_DES_PCT", "R323_HIC605_DES_PCT"), ("HV605_CHAR", "R323_HV605_CHAR"),
    ("P_324E002_DES_BARA", "R324_F001_P_BARA"),
])
def test_design_basis(v1, ours, theirs):
    """Every design constant is V1's, the chest's three on the decided anchor by V1's own
    expressions."""
    assert getattr(d, ours) == _decided(v1)[theirs]


def test_the_chest_anchor_decided_divergence(v1):
    """V1 anchors on 1.76 bar a (35.11 %, 421.0 kW/K); the port on PFD 926's 2.5 (49.87 %,
    255.1 kW/K). The design duty is the same 7249 kW on either."""
    assert v1["R323_E010_PCHEST_DES"] == 1.76
    assert d.E010_PCHEST_DES_BARA == DECIDED_E010_PCHEST_BARA
    assert v1["R323_E010_OP_DES"] == pytest.approx(35.107, abs=1e-3)
    assert d.E010_OP_DES_PCT == pytest.approx(49.868, abs=1e-3)
    assert v1["R323_E010_UA_KW"] == pytest.approx(421.04, abs=0.01)
    assert d.E010_UA_KW == pytest.approx(255.13, abs=0.01)


def test_the_cascade_gains_decided_divergence(v1):
    """V1: TIC-323012 on its own retune, 3.6 bar/K and 1200 s; PIC-329208 on the table's 0.20
    times its chest scale. The port: TIC-323007's table row on TT-323012's span, and the table's
    0.20 per cent of PT-329208's span."""
    assert v1["PIC_329208_KC_SCALE"] == pytest.approx(1.8594, abs=1e-4)
    s = _v1_state(v1, chest_decided=False)
    tic, pic = pe.tic_323012(), pe.pic_329208(pe.V1_CHEST)
    assert (s.TIC_323012["Kc"], s.TIC_323012["Ti"], s.PIC_329208["Kc"]) == (
        3.6, 1200.0, 0.2 * v1["PIC_329208_KC_SCALE"])
    assert (tic.Kc, tic.Ti, pic.Kc) == (DECIDED_TIC_323012_KC, DECIDED_TIC_323012_TI_S,
                                        DECIDED_PIC_329208_KC)
    assert (tic.Kc, pic.Kc) == (d.TIC_323012_KC, d.PIC_329208_KC)


def test_the_design_flows_vapour_and_liquor(v1):
    assert R323_M317_DES == v1["R323_M317_DES"]
    assert pe.Y_VAP_DES == v1["SOL_F010_Y_DES"]
    assert pe.MW_VAP_DES == v1["R323_F010_MW_VAP_DES"]
    assert d.F010_LIQUOR.anchor.entrain == v1["SOL_F010"]["entrain"]
    assert d.F010_LIQUOR.tbub_raoult_des_c == v1["R323_F010_TBUB_DES"]


@pytest.mark.parametrize("m_kg, p_bara", [
    (d.F010_M_DES_KG, d.F010_P_BARA), (0.5 * d.F010_M_DES_KG, 0.46), (d.F010_M_DES_KG, 0.90),
    (0.0, 0.46), (1.5 * d.F010_M_DES_KG, 0.20),
])
def test_the_barometric_leg(v1, m_kg, p_bara):
    assert pe.barometric_leg_kgh(m_kg, p_bara) == v1["gravity_outflow_323f010"](m_kg, p_bara)


@pytest.mark.parametrize("stroke, p1, p2, t_c", [
    (50.0, 0.46, 0.33, 99.0), (80.0, 0.46, 0.33, 99.0), (20.0, 0.60, 0.33, 101.0),
    (50.0, 0.30, 0.33, 99.0), (0.0, 0.46, 0.33, 99.0), (100.0, 0.90, 0.10, 95.0),
])
def test_hv323605(v1, stroke, p1, p2, t_c):
    assert pe.vapour_outlet_kgh(stroke, p1, p2, t_c, pe.MW_VAP_DES) == \
        v1["hv323605_flow_kgh"](stroke, p1, p2, t_c, v1["R323_F010_MW_VAP_DES"])


# --------------------------------------------------------------------------------------
# The pre-evaporator on its own, tick by tick
# --------------------------------------------------------------------------------------

#: 323F004 vapour blowing through an uncovered LV-323505: 300 kg/h of the drum's design vapour.
BLOW = (300.0, 300.0 / 22.0, dict(d.F004_LIQUOR.anchor.y))

SCENARIOS = {
    "design hold": (lambda k: _design(), 300),
    "drain cut 25 % (the line's dead time shows)": (
        lambda k: _design(m319=R323_M319_DES * (0.75 if k >= 20 else 1.0)), 500),
    "drain up 20 %": (lambda k: _design(m319=R323_M319_DES * (1.2 if k >= 10 else 1.0)), 400),
    "hotter drum liquor": (lambda k: _design(t319=(110.0 if k >= 10 else 106.0)), 400),
    "drum liquor colder than the boil": (
        lambda k: _design(t319=(95.0 if k >= 10 else 106.0)), 400),
    "ammonia-rich drum liquor": (lambda k: _design(w319=(W319_NH3 if k >= 10 else W319)), 400),
    "LP header sags": (lambda k: _design(p_lp=(4.5 if k >= 10 else P_LP_BARA)), 400),
    "HIC-323605 pinched": (lambda k: _design(hic=(25.0 if k >= 10 else 50.0)), 400),
    "HIC-323605 opened": (lambda k: _design(hic=(80.0 if k >= 10 else 50.0)), 400),
    "324E002 vacuum lost": (
        lambda k: _design(p_e002=(0.70 if k >= 10 else d.P_324E002_DES_BARA)), 500),
    "LV-323505 blowing through": (lambda k: _design(blow=(BLOW if k >= 10 else NO_BLOW)), 300),
    "everything at once": (
        lambda k: _design(m319=R323_M319_DES * (1.1 if k >= 5 else 1.0), t319=108.0,
                          w319=W319_NH3, hic=40.0, p_lp=4.8, p_e002=0.36, blow=BLOW), 500),
}


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_stage_three_tick_by_tick(v1, name):
    script, ticks = SCENARIOS[name]
    _run(v1, script, ticks)


def test_a_temperature_set_point_step(v1):
    def before(s, sep, tic, pic):
        s.TIC_323012["sp"] = 101.0
        tic.sp = 101.0
    _run(v1, lambda k: _design(), 400, dt=0.5, before=before)


def test_pic_329208_in_manual_with_more_steam(v1):
    def before(s, sep, tic, pic):
        s.PIC_329208["mode"] = "MAN"; s.PIC_329208["op"] = 45.0
        pic.set_mode("MAN"); pic.op = 45.0
    _run(v1, lambda k: _design(), 400, dt=0.5, before=before)


def test_hic_323605_nearly_shut_drives_pt_323204_to_its_clamp_in_both(v1):
    """At 10 % HV-323605 cannot pass the overhead: PT-323204 reaches its 1.0 bar a clamp in
    seconds and stays there while the separator keeps evaporating — handoff B-22. Both sides
    take the clamp branch on the same ticks."""
    s, sep, loops, b = _run(v1, lambda k: _design(hic=(10.0 if k >= 4 else 50.0)), 400, dt=0.5)
    assert b.p_bara == d.F010_P_MAX_BARA and b.pull_kgh < b.m_evap_kgh


def test_the_barometric_leg_at_the_heel_decided_divergence(v1):
    """B-29, decided 2026-09-27. The 323F004 drain stopped on a separator holding 300 kg: PFD
    331 still arrives, the chest boils the held liquor (B-24, on both sides here) and the leg
    drains the rest. Bit-exact until the leg's cap first binds, in the 13th second. From then
    on V1's cap counts the floor's kilogram as drainable, so its leg passes that kilogram every
    tick on top of PFD 331 — 39 270 kg/h at the 0.1 s step — and the floor restores it, 480 kg
    in the next 48 s; the port's leg passes the liquid above the heel plus what arrives net of
    the evaporation, and nothing is made. (Without B-24 the cap first bound in the 16th second
    and V1 made 452 kg.)"""
    s = _v1_state(v1)
    sep = pe.PreEvaporator(chest=pe.V1_CHEST, live_bubble=False)
    tic, pic = pe.tic_323012(), pe.pic_329208(pe.V1_CHEST)
    s.r323_f010_M = sep.m_kg = 300.0
    x = _design(m319=0.0)
    s.HIC_323605, s.steam.P_LP, s.r324_f001_P = x["hic"], x["p_lp"], x["p_e002"]
    parted, v1_total = None, 0.0
    for k in range(600):
        m_v1_pre, m_pre = s.r323_f010_M, sep.m_kg
        a = _v1_stage3(v1, s, x["m319"], x["t319"], x["w319"], x["blow"], DT,
                       heel_decided=False)
        b = sep.step(tic, pic, x["m319"], x["t319"], x["w319"], *x["blow"], x["hic"],
                     x["p_lp"], x["p_e002"], DT)
        if parted is None and a["m317"] != b.m_317_kgh:
            parted = k
        if parted is None:
            _assert_tick(a, b, s, sep, tic, pic, f"tick {k}")
            continue
        # V1: the floor's kilogram drained every tick and restored by the floor.
        v1_created = (s.r323_f010_M - m_v1_pre) - (a["feed"][0] + a["m331"] - a["evap"]
                                                   - a["boil"] - a["m317"]) / 3600.0 * DT
        assert v1_created >= 0.0 and s.r323_f010_M == d.F010_M_FLOOR_KG
        v1_total += v1_created
        # The port: the heel is never drained, and nothing is made.
        ours_created = (sep.m_kg - m_pre) - (b.feed_kgh + b.m_331_kgh - b.m_evap_kgh
                                             - b.m_boil_kgh - b.m_317_kgh) / 3600.0 * DT
        assert abs(ours_created) < 1e-9 and sep.m_kg >= d.F010_M_FLOOR_KG
    assert parted == 123
    assert a["m317"] == pytest.approx(d.F010_M_FLOOR_KG / DT * 3600.0 + d.M331_DES_KGH,
                                      rel=1e-12)
    assert b.m_317_kgh == pytest.approx(b.m_331_kgh - b.m_evap_kgh, rel=1e-9)
    assert v1_total == pytest.approx(479.8, abs=0.1)


def _boil_both(v1, before, n):
    """V1 verbatim on the held liquor (no B-24) against the port, design boundaries."""
    s = _v1_state(v1)
    sep = pe.PreEvaporator(chest=pe.V1_CHEST, live_bubble=False)
    tic, pic = pe.tic_323012(), pe.pic_329208(pe.V1_CHEST)
    before(s, tic, pic)
    x = _design()
    for _ in range(n):
        a = _v1_stage3(v1, s, x["m319"], x["t319"], x["w319"], x["blow"], DT,
                       boil_decided=False)
        b = sep.step(tic, pic, x["m319"], x["t319"], x["w319"], *x["blow"], x["hic"],
                     x["p_lp"], x["p_e002"], DT)
    tb_v1 = v1["sol_bubble_t_dep"]("F010", s.w_f010, s.r323_f010_P, v1["R323_F010_T_SP_C"],
                                   v1["R323_F010_TBUB_DES"])
    tb = v1["sol_bubble_t_dep"]("F010", sep.w, sep.p_bara, v1["R323_F010_T_SP_C"],
                                v1["R323_F010_TBUB_DES"])
    return s, sep, a, b, tb_v1, tb


def test_the_held_liquor_boils_decided_divergence(v1):
    """B-24, decided 2026-10-02 (B-62's class). TIC-323012 to 101 C. V1's overhead is capped at
    the design split, so after 20 minutes its liquor is at 100.29 C, 2.57 K above its bubble
    point at the live PT-323204, and the product is still 80.00 % urea. The port's holdup boils
    416 kg/h past its bubble point: the liquor holds there, 99.88 C, and the product has
    concentrated to 80.28 %."""
    def before(s, tic, pic):
        s.TIC_323012["sp"] = tic.sp = 101.0
    s, sep, a, b, tb_v1, tb = _boil_both(v1, before, 12001)
    assert (a["evap"], a["boil"], b.m_evap_kgh) == (d.MEVAP_DES_KGH, 0.0, d.MEVAP_DES_KGH)
    assert b.m_boil_kgh == pytest.approx(416.46, abs=0.01)
    assert (s.r323_f010_T, sep.t_c) == (pytest.approx(100.2894, abs=1e-4),
                                        pytest.approx(99.8779, abs=1e-4))
    assert s.r323_f010_T - tb_v1 == pytest.approx(2.571, abs=1e-3)
    assert 0.0 < sep.t_c - tb < 0.01
    assert (s.w_f010["Urea"], sep.w["Urea"]) == (pytest.approx(0.800016, abs=1e-6),
                                                 pytest.approx(0.802848, abs=1e-6))


def test_more_steam_concentrates_instead_of_superheating_decided_divergence(v1):
    """B-24. PV-329208 in MAN at 60 %, ten points above its design stroke. After ten minutes V1's
    liquor is at 106.47 C, 11.8 K above its live bubble point, the product 80.00 %; the port's
    boils 1176 kg/h of its own, holds at 101.70 C and has concentrated to 80.95 % (1179 kg/h and
    101.71 C before PFD 314 and 319 were closed on their urea, B-20)."""
    def before(s, tic, pic):
        s.PIC_329208["mode"] = "MAN"; s.PIC_329208["op"] = 60.0
        pic.set_mode("MAN"); pic.op = 60.0
    s, sep, a, b, tb_v1, tb = _boil_both(v1, before, 6001)
    assert b.m_boil_kgh == pytest.approx(1176.10, abs=0.01)
    assert (s.r323_f010_T, sep.t_c) == (pytest.approx(106.4677, abs=1e-4),
                                        pytest.approx(101.7046, abs=1e-4))
    assert s.r323_f010_T - tb_v1 == pytest.approx(11.830, abs=1e-3)
    assert 0.0 < sep.t_c - tb < 0.01
    assert (s.w_f010["Urea"], sep.w["Urea"]) == (pytest.approx(0.800016, abs=1e-6),
                                                 pytest.approx(0.809497, abs=1e-6))


# --------------------------------------------------------------------------------------
# Stages 2 and 3 coupled, and all three: the drain interface, end to end
# --------------------------------------------------------------------------------------

def _run_coupled(v1, script, ticks: int, dt: float = DT, before=None):
    """V1's stage 2 feeds V1's stage 3; the ported 323F004 feeds the ported 323F010. The drum
    reads the separator pressure as it stood at the top of the tick, as V1 does."""
    s = _v1_state(v1)
    tank, lic = ft.FlashTank(), ft.lic_323505()
    sep = pe.PreEvaporator(chest=pe.V1_CHEST, live_bubble=False)
    tic, pic = pe.tic_323012(), pe.pic_329208(pe.V1_CHEST)
    if before:
        before(s, tank, lic, sep, tic, pic)
    for k in range(ticks):
        x = script(k)
        s.HIC_323605 = x["hic"]
        a2 = stage2._v1_stage2(v1, s, x["m314"], d.C003_T_SP_C, stage2.W314, dt)
        a3 = _v1_stage3(v1, s, a2["m319"], a2["dep319"][0], a2["dep319"][1], a2["blow"], dt)
        b2 = tank.step(lic, x["m314"], d.C003_T_SP_C, stage2.W314, d.F004_P_BARA, sep.p_bara,
                       dt)
        b3 = sep.step(tic, pic, b2.m_319_kgh, b2.drain_t_c, b2.drain_w, b2.blowthrough_kgh,
                      b2.blowthrough_kmolh, b2.blowthrough_y, x["hic"], P_LP_BARA,
                      d.P_324E002_DES_BARA, dt)
        stage2._assert_tick(a2, b2, s, tank, lic, f"stage 2, tick {k}")
        _assert_tick(a3, b3, s, sep, tic, pic, f"stage 3, tick {k}")
    return b2, b3


def test_stages_two_and_three_coupled_through_a_feed_cut(v1):
    _run_coupled(v1, lambda k: {"m314": R323_M314_DES * (0.8 if k >= 20 else 1.0),
                                "hic": d.HIC_323605_DES_PCT}, 600)


def test_a_pinched_hic_323605_reaches_the_drum_only_unchoked(v1):
    """HIC-323605 to 20 %: the separator pressure rises to 0.94 bar a. V1 verbatim, 323F004's
    drain feels the smaller drop across LV-323505 one tick later and LIC-323505 answers. The
    port (handoff B-46, decided 2026-09-30): LV-323505 flashes and chokes on 0.054 bar while
    323F010 stays under its choke point, 1.076 bar a, so the drum feels nothing and LIC-323505
    holds its stroke."""
    def hic(k):
        return 20.0 if k >= 10 else 50.0
    b2, b3 = _run_coupled(v1, lambda k: {"m314": R323_M314_DES, "hic": hic(k)}, 400, dt=0.5)
    assert b3.p_bara == pytest.approx(0.9445, abs=1e-4)
    assert (b2.lv505_op_pct, b2.m_319_kgh) == (d.LV505_OP_DES_PCT, R323_M319_DES)
    s = _v1_state(v1)
    s.flash_decided = False                                   # V1 verbatim: nothing chokes
    for k in range(400):
        s.HIC_323605 = hic(k)
        a2 = stage2._v1_stage2(v1, s, R323_M314_DES, d.C003_T_SP_C, stage2.W314, 0.5)
        _v1_stage3(v1, s, a2["m319"], a2["dep319"][0], a2["dep319"][1], a2["blow"], 0.5)
    assert s.r323_f010_P > d.F010_P_BARA and a2["lv"] > d.LV505_OP_DES_PCT


def test_lv323505_blowing_through_into_the_separator_coupled(v1):
    def before(s, tank, lic, sep, tic, pic):
        s.LIC_323505["mode"] = "MAN"; s.LIC_323505["op"] = 100.0
        lic.set_mode("MAN"); lic.op = 100.0
    b2, b3 = _run_coupled(v1, lambda k: {"m314": R323_M314_DES, "hic": 50.0}, 700, dt=0.5,
                          before=before)
    assert b2.blowthrough_kgh > 0.0 and b3.blowthrough_share is not None


def test_all_three_stages_coupled_through_a_stripper_feed_cut(v1):
    """V1's stages 1 to 3 against the ported 323C003 -> 323F004 -> 323F010, each reading its
    downstream neighbour's pressure as it stood at the top of the tick."""
    s = _v1_state(v1)
    col = rc.RectifyingColumn(chest=rc.V1_CHEST)
    loops1 = (rc.tic_323007(), rc.pic_329202(rc.V1_CHEST), rc.lic_323501())
    tank, lic = ft.FlashTank(), ft.lic_323505()
    sep = pe.PreEvaporator(chest=pe.V1_CHEST, live_bubble=False)
    tic, pic = pe.tic_323012(), pe.pic_329208(pe.V1_CHEST)
    for k in range(500):
        drain = FEED_DES * (0.85 if k >= 20 else 1.0)
        a1 = stage1._v1_stage1(v1, s, drain, 119.0, stage1.BOTTOMS_PCT, DT)
        a2 = stage2._v1_stage2(v1, s, a1["m314"], a1["dep314"][0], a1["dep314"][1], DT)
        a3 = _v1_stage3(v1, s, a2["m319"], a2["dep319"][0], a2["dep319"][1], a2["blow"], DT)
        b1 = col.step(*loops1, drain, 119.0, stage1.BOTTOMS_PCT, 172.0, P_LP_BARA,
                      tank.p_bara, d.E003_P_DES_BARA, DT)
        b2 = tank.step(lic, b1.m_314_kgh, b1.drain_t_c, b1.drain_w, d.F004_P_BARA, sep.p_bara,
                       DT)
        b3 = sep.step(tic, pic, b2.m_319_kgh, b2.drain_t_c, b2.drain_w, b2.blowthrough_kgh,
                      b2.blowthrough_kmolh, b2.blowthrough_y, d.HIC_323605_DES_PCT, P_LP_BARA,
                      d.P_324E002_DES_BARA, DT)
        stage1._assert_tick(a1, b1, s, col, loops1, f"stage 1, tick {k}")
        stage2._assert_tick(a2, b2, s, tank, lic, f"stage 2, tick {k}")
        _assert_tick(a3, b3, s, sep, tic, pic, f"stage 3, tick {k}")


# --------------------------------------------------------------------------------------
# The decided divergence: the chest anchor and the cascade gains (As-Built §XL.1-2)
# --------------------------------------------------------------------------------------

def test_a_set_point_step_on_the_decided_chest_and_gains(v1):
    """TIC-323012 to 97 C, V1's chest and gains and the port's side by side, the held liquor
    boiling on both (B-24). V1 works its chest from 1.76 bar a, on its 3.6 bar/K retune; the port
    from PFD 926's 2.5, on TIC-323007's table row on span, 0.075 bar/K. The design duty is the
    same on both anchors; after 20 minutes V1's separator is 1.27 K down and the port's 0.91 K,
    both heading for 97 C (without B-24: 1.23 and 0.78 K)."""
    s = _v1_state(v1, chest_decided=False)
    sep = pe.PreEvaporator(chest=pe.V1_CHEST, live_bubble=False)
    tic, pic = pe.tic_323012(), pe.pic_329208(pe.V1_CHEST)
    s.TIC_323012["sp"] = tic.sp = 97.0
    x = _design()
    for k in range(12000):
        a = _v1_stage3(v1, s, x["m319"], x["t319"], x["w319"], x["blow"], DT,
                       chest_decided=False)
        b = sep.step(tic, pic, x["m319"], x["t319"], x["w319"], *x["blow"], x["hic"],
                     x["p_lp"], x["p_e002"], DT)
        if k == 0:
            assert (s.r323_e010_chest_P, b.chest_p_bara) == (
                pytest.approx(1.76, abs=0.01), pytest.approx(2.5, abs=0.01))
            assert a["Q"] == pytest.approx(b.q_e010_kw, rel=1e-3)
    assert s.r323_f010_T == pytest.approx(97.73, abs=0.01)
    assert sep.t_c == pytest.approx(98.09, abs=0.01)
    assert s.r323_e010_chest_P == pytest.approx(1.63, abs=0.01)
    assert b.chest_p_bara == pytest.approx(2.33, abs=0.01)
