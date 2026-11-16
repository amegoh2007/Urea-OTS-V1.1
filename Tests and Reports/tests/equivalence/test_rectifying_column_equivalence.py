"""V1 <-> V1.1 equivalence for 323C003 / 323E002, stage 1 of unit 323.

What is being proved
--------------------
V1 writes stage 1 inline in `step_sim` (``main.py`` 8219-8409), so the ~60 statements that wire it
are TRANSCRIBED into `_v1_stage1` below, line for line, and declared as such. Everything those
statements call is V1's own code, executed: ``_ctrl_ipd``, ``_lag1``, ``steam_chest_pressure``,
``sol_bubble_t_dep``, ``sol_vapour_y_vle``, ``sol_biuret_xi``, ``sol_advance``, ``_cq_packet``,
``urea_soln_cp`` and ``urea_soln_rho`` lifted out of ``main.py``; ``hydraulics``, ``consequence``,
``steam_system`` and ``c003_pressure_coupling`` loaded as real modules. The three controller
seeds live inside ``State.__init__`` and are transcribed from ``main.py`` 6660-6674.

Two parts of V1's block are not driven here, by design:

  * the 323C003 -> 323F004 drain packet and its TRANSPORT belong to the receiving unit and
    are proven in `test_flash_tank_equivalence.py`; the state the drain departs at — the
    column's temperature and composition before the tick advances them — is compared here;
  * the telemetry writes (``s._debug_*``, ``PROCESS_DIAGNOSTICS``) feed nothing.

Every tick of every scenario compares every published field and the whole column state with
``==``. The feed temperature from the stripper, TT-322004, is passed as 172.0 in every scenario
here, which is exactly what V1's store-key typo reads; the decided divergence is proven from
both sides at the end of the file.

The product line (handoff B-21, decided 2026-09-30). The port's line delivers the live
departure flow and delays only the liquor's temperature, composition and cp. The transcription
carries the same switch, ``line_decided`` (default True): a property packet on a unit flow
through V1's own FIFO, and the live flow delivered; ``line_decided=False`` is V1 verbatim. A
settled line is the same float either way.

The chest and its cascade (decided 2026-09-30, As-Built §XL.1-2). The port anchors 323E002's
chest on its datasheet's 3.9 bar a, where V1 anchors on 3.96, and runs TIC-323007 and PIC-329202
on the DCS table's gains per cent of their transmitters' spans, without the chest-gain scale V1
multiplies PIC-329202 by. The transcription carries the switch ``chest_decided`` (default True):
V1's own stroke and conductance expressions (``main.py`` 1055 and 1171) re-executed on 3.9 bar
a, and the span gains in the controller seeds; ``chest_decided=False`` is V1 verbatim. The last
section runs the two side by side.

LV-323501 (handoff B-44, decided 2026-09-30). The port places the drain valve on its vendor sheet:
linear, as V1 has it, but at the 56.65 % stroke its Kvs gives and on the sheet's FL. The switch
``valves_decided`` (default True, on the state) seeds LIC-323501 there and hands V1's own
``valve_liquid_anchored`` the decided stroke and FL; ``valves_decided=False`` is V1 verbatim.
Both sides are asserted in the last section of this file.

LV-323501 flashes (handoff B-46, decided 2026-09-30). The port hands the valve's IEC 60534 choke
the column liquor's live bubble pressure — the stage's departure bubble point inverted, V1's own
thermo service on V1's own design anchor — and its design value, 4.1 bar a. The switch
``flash_decided`` (default True, on the state) passes both to V1's ``valve_liquid_anchored``;
``flash_decided=False`` is V1 verbatim, which passes none.
"""

from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

from ureasim.data import control_valves as cvd
from ureasim.data import unit_323 as d
from ureasim.data import unit_323c003 as c003
from ureasim.data.design_point import R323_FEED_DES_KGH as FEED_DES
from ureasim.data.unit_329 import P_LP_BARA
from ureasim.units.recirc import rectifying_column as rc
from tests.equivalence import b20_switch, routes_switch
from tests.equivalence import decided_valves as dv
from tests.equivalence.v1_loader import lift, load, v1_available, v1_service

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

V1_NAMES = [
    "_ctrl_ipd", "_pv_ok", "clamp", "_lag1", "tsat_steam", "steam_chest_pressure",
    "_chest_slave_kc_scale", "PIC_329202_KC_SCALE",
    "_w_norm", "_cq_packet", "urea_soln_cp", "urea_soln_rho", "bubble_T_raoult",
    "sol_bubble_t_dep", "sol_vapour_y_vle", "sol_advance",
    "_sol_tbub_anchor", "_sol_alpha_anchor", "SOL_TBUB_DES", "SOL_ALPHA_MODEL_DES",
    "SOL_C003", "SOL_SPECIES", "MW_COMP", "W_S208", "W_S314",
    "_proc_route", "PROC_LINE_ID_MM",
    "R323_CP_SOLN", "R323_CP_S208_DES", "R323_CP_C003_DES", "R323_P_STEAM_SUP",
    "R323_FEED_DES_KGH", "R323_FEED_DES_T_C", "R323_C003_P_BARA", "R323_C003_T_SP_C",
    "R323_C003_T313_C", "R323_PHI_V305", "R323_E002_Q_DES_KW", "R323_E002_PCHEST_DES",
    "R323_E002_OP_DES", "R323_C003_M_TAU_S", "R323_C003_LVL_SP", "R323_LV501_OP_DES",
    "R323_C003_P_TAU_S", "R323_F004_P_BARA", "R323_RHO_S314", "R323_LV_CHAR",
    "R323_M305_DES", "R323_M314_DES", "R323_Q305_DES_KW", "R323_LAMBDA_305",
    "R323_E002_UA_KW", "R323_M_FLASH_GAS_DES_KGH", "R323_M_POOL_VAP_DES_KGH",
    "R323_C003_M_DES", "R323_C003_M_FULL", "R323_RHO_C003_DES", "STRIP_T_BOTTOM_DES_C",
    "SOL_BIU_EA", "SOL_BIU_ORDER", "STRIP_R_GAS_J",
]

DT = 0.1
#: The stripper publishes its bottoms in mass PERCENT; this is PFD 208.
BOTTOMS_PCT = dict(Urea=55.85, Biuret=0.24, NH3=7.92, CO2=10.28, H2O=25.68)

#: The decided chest anchor [bar a] and cascade gains, written from their sources: 323E002's
#: DDS (UD-AU-323-EC-0007, 3.9 bar a); the table's 2.00 on TT-323007's 160 K onto PT-329202's
#: 6 bar [bar/K]; the table's 0.65 on PT-329202's 6 bar [%/bar].
DECIDED_E002_PCHEST_BARA = 3.9
DECIDED_TIC_323007_KC = 2.0 * 6.0 / 160.0
DECIDED_PIC_329202_KC = 0.65 * 100.0 / 6.0

#: LV-323501 as decided (B-44): the stroke its Kvs gives for PFD 314 [%], and its sheet's FL.
DECIDED_LV501_OP = dv.design_stroke_pct(cvd.LV_323501, d.R323_M314_DES)
DECIDED_LV501_FL = cvd.LV_323501.cases[cvd.LV_323501.normal].fl


def _v1_namespace(drain_closed: bool = True):
    """V1's 323C003 block. With `drain_closed`, PFD 314 and 319 on their decided rows (B-20,
    `b20_switch`); without, V1 verbatim."""
    coupling = load("c003_pressure_coupling")
    seed = {
        "math": math,
        "iapws_if97": load("iapws_if97"),
        "thermo_service": v1_service(),
        "hydraulics": load("hydraulics"),
        "consequence": load("consequence"),
        "steam_system": load("steam_system"),
        "c003_pressure_target_bara": coupling.c003_pressure_target_bara,
    }
    ns = (lift(b20_switch.names(V1_NAMES), seed=b20_switch.seed(seed)) if drain_closed
          else lift(V1_NAMES, seed=seed))
    # main.py 2615 and 2874: the 323C003 design memos (bare module-level calls).
    ns["_sol_tbub_anchor"]("C003", ns["W_S314"], ns["R323_C003_P_BARA"])
    ns["_sol_alpha_anchor"]("C003", ns["W_S314"], ns["R323_C003_T_SP_C"], ns["R323_C003_P_BARA"])
    # main.py 2730-2736, the 323C003 row of SOL_STAGES; second pass for sol_biuret_xi.
    stages = {"C003": {"w": ns["W_S314"], "a": ns["SOL_C003"], "M": ns["R323_C003_M_DES"],
                       "T": ns["R323_C003_T_SP_C"]}}
    ns["sol_biuret_xi"] = lift(["sol_biuret_xi"], seed={
        "math": math, "SOL_STAGES": stages, "SOL_BIU_EA": ns["SOL_BIU_EA"],
        "SOL_BIU_ORDER": ns["SOL_BIU_ORDER"], "STRIP_R_GAS_J": ns["STRIP_R_GAS_J"],
    })["sol_biuret_xi"]
    # main.py 6239: V1's own route object for the feed line.
    # The isometrics' geometry (handoff A-11, decided 2026-10-07): `routes_switch`.
    ns["FEED_ROUTE"] = routes_switch.decided(ns, "322E001_TO_323C003")
    return ns


@pytest.fixture(scope="module")
def v1():
    return _v1_namespace()


@pytest.fixture(scope="module")
def v1_verbatim():
    """V1's rows untouched, for B-20 both ways."""
    return _v1_namespace(drain_closed=False)


def _decided(v1):
    """V1's namespace on the decided chest anchor: ``R323_E002_OP_DES`` and ``R323_E002_UA_KW``
    re-executed from V1's own statements on 3.9 bar a; everything else the same objects."""
    if "__chest_decided__" not in v1:
        derived = ("R323_E002_OP_DES", "R323_E002_UA_KW")
        seed = {k: val for k, val in v1.items() if k not in derived}
        seed["R323_E002_PCHEST_DES"] = DECIDED_E002_PCHEST_BARA
        v1["__chest_decided__"] = lift(list(derived), seed=seed)
    return v1["__chest_decided__"]


def _v1_stage_pv(g, key: str, w: dict, t_c: float, p_bara: float, t_sp_c: float) -> float:
    """B-46, the port's line (`thermo.urea_liquor.stage_bubble_p`) written on V1's own thermo
    service and design anchor: a stage liquor's bubble pressure at its temperature, the inverse of
    V1's departure bubble point, at most the stage's pressure; the stage's pressure off the
    rigorous surface."""
    tb = g["SOL_TBUB_DES"].get(key)
    if tb is None:
        return p_bara
    try:
        return min(g["thermo_service"].bubble_p(w, t_c - (t_sp_c - tb)), p_bara)
    except Exception:  # noqa: BLE001 — V1's own OutOfDomain, ValueError, ZeroDivisionError
        return p_bara


def _v1_state(v1, chest_decided: bool = True, valves_decided: bool = True,
              flash_decided: bool = True):
    """The V1 plant-state fields stage 1 reads and writes, seeded as `State.__init__` seeds them;
    `chest_decided` seeds the decided anchor and gains, `valves_decided` LV-323501's stroke,
    `flash_decided` (B-46) switches its choke on."""
    g = _decided(v1) if chest_decided else v1
    tic_kc = DECIDED_TIC_323007_KC if chest_decided else 2.0
    pic_kc = DECIDED_PIC_329202_KC if chest_decided else 0.65 * g["PIC_329202_KC_SCALE"]
    s = SimpleNamespace(
        w_c003=dict(g["W_S314"]),
        r323_c003_M=g["R323_C003_M_DES"],
        r323_c003_T=g["R323_C003_T_SP_C"],
        r323_c003_P=g["R323_C003_P_BARA"],
        r323_e002_chest_P=g["R323_E002_PCHEST_DES"],
        TIC_323007={"mode": "AUTO", "op": g["R323_E002_PCHEST_DES"],
                    "sp": g["R323_C003_T_SP_C"], "pv": g["R323_C003_T_SP_C"],
                    "pv1": g["R323_C003_T_SP_C"], "pv2": g["R323_C003_T_SP_C"],
                    "Kc": tic_kc, "Ti": 500.0, "Td": -1.0, "act": +1.0,
                    "op_lo": 0.0, "op_hi": g["R323_P_STEAM_SUP"], "sp_lo": 50.0, "sp_hi": 160.0},
        PIC_329202={"mode": "CAS", "op": g["R323_E002_OP_DES"],
                    "sp": g["R323_E002_PCHEST_DES"], "pv": g["R323_E002_PCHEST_DES"],
                    "pv1": g["R323_E002_PCHEST_DES"], "pv2": g["R323_E002_PCHEST_DES"],
                    "Kc": pic_kc, "Ti": 30.0, "Td": 0.0, "act": +1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0, "sp_hi": g["R323_P_STEAM_SUP"]},
        LIC_323501={"mode": "AUTO", "op": g["R323_LV501_OP_DES"],
                    "sp": g["R323_C003_LVL_SP"], "pv": g["R323_C003_LVL_SP"],
                    "pv1": g["R323_C003_LVL_SP"], "pv2": g["R323_C003_LVL_SP"],
                    "Kc": 1.2, "Ti": 100.0, "Td": 0.0, "act": -1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0, "sp_hi": 100.0},
        tlag={}, flags={},
        steam=SimpleNamespace(P_LP=g["R323_P_STEAM_SUP"]),
        r323_f004_P=g["R323_F004_P_BARA"],
        r3232_d001_P=3.2,
    )
    if valves_decided:
        s.LIC_323501["op"] = DECIDED_LV501_OP
    s.valves_decided = valves_decided
    s.flash_decided = flash_decided
    return s


def _v1_stage1(v1, s, drain_kgh: float, TT_323001: float, bot_mass_pct: dict, dt: float,
               line_decided: bool = True, chest_decided: bool = True) -> dict:
    """V1 `main.py` 8219-8409, stage 1, TRANSCRIBED line for line. See the module docstring.
    `line_decided` puts the port's feed line in V1's (handoff B-21); `chest_decided` the port's
    chest anchor."""
    g = _decided(v1) if chest_decided else v1
    clamp = g["clamp"]
    _cp = lambda w, T, des: g["R323_CP_SOLN"] + (g["urea_soln_cp"](w, T) - des)  # noqa: E731
    m_dep_323 = max(drain_kgh, 0.0)
    T_dep_323 = TT_323001
    w_dep_323 = g["_w_norm"]({k: bot_mass_pct.get(k, 0.0) for k in g["SOL_SPECIES"]}, g["W_S208"])
    # B-21, decided 2026-09-30: with `line_decided`, the port's lines — a property packet on the
    # unit flow through V1's own FIFO, and the live departure flow delivered.
    _pkt_dep_323 = g["_cq_packet"](1.0 if line_decided else m_dep_323, T_dep_323, w_dep_323,
                                   _cp(w_dep_323.get("Urea", 0.0), T_dep_323, g["R323_CP_S208_DES"]))
    # _transport_process(s, "322E001_TO_323C003", ...), less its telemetry writes:
    _pkt_arr_323 = g["consequence"].transport_process_packet(
        s.tlag, "PROCESS_322E001_TO_323C003", _pkt_dep_323, g["FEED_ROUTE"], m_dep_323, dt)
    if _pkt_arr_323 == _pkt_dep_323:
        m_feed_323, T_feed_323, w_feed_323 = m_dep_323, T_dep_323, w_dep_323
    else:
        m_feed_323 = m_dep_323 if line_decided else _pkt_arr_323.mass_kgh
        T_feed_323 = _pkt_arr_323.temperature_c
        w_feed_323 = g["_w_norm"](_pkt_arr_323.mass_fraction, w_dep_323)
    cp_feed323 = _cp(w_feed_323.get("Urea", 0.0), T_feed_323, g["R323_CP_S208_DES"])
    cp_c003 = _cp(s.w_c003.get("Urea", 0.0), s.r323_c003_T, g["R323_CP_C003_DES"])

    tic07_op = g["_ctrl_ipd"](s.TIC_323007, s.r323_c003_T, dt)
    pic02_pv = s.r323_e002_chest_P
    pic02_op = g["_ctrl_ipd"](s.PIC_329202, pic02_pv, dt, cas_sp=tic07_op)
    p_lp_lagged_c003 = g["_lag1"](s.tlag, "323C003_P_LP_thermal", s.steam.P_LP,
                                  g["R323_C003_M_TAU_S"], dt)
    p_chest_e002 = g["steam_chest_pressure"](pic02_op, p_lp_lagged_c003, g["R323_E002_OP_DES"],
                                             g["R323_E002_PCHEST_DES"], g["R323_E002_UA_KW"],
                                             s.r323_c003_T, g["R323_E002_Q_DES_KW"],
                                             g["R323_P_STEAM_SUP"], s.r323_e002_chest_P)
    s.r323_e002_chest_P = p_chest_e002
    Q_e002_kw = max(g["R323_E002_UA_KW"] * (g["tsat_steam"](p_chest_e002) - s.r323_c003_T), 0.0)
    T_bub_c003 = g["sol_bubble_t_dep"]("C003", s.w_c003, s.r323_c003_P, g["R323_C003_T_SP_C"],
                                       g["bubble_T_raoult"](g["R323_C003_P_BARA"], g["W_S314"]))
    q305_relax_kw = (s.r323_c003_M * cp_c003 * (T_bub_c003 - s.r323_c003_T)
                     / g["R323_C003_M_TAU_S"])
    T_strip_bot = s.tlag.get("TT_322004", g["STRIP_T_BOTTOM_DES_C"])
    T_flash_sat = TT_323001
    q_flash_avail_kw = (m_feed_323 / 3600.0 * cp_feed323 * (T_strip_bot - T_flash_sat))
    m_flash_gas = max(g["R323_M305_DES"] * (q_flash_avail_kw / g["R323_Q305_DES_KW"]), 0.0)
    m_pool_vap = max(g["R323_M305_DES"] * ((Q_e002_kw - q305_relax_kw) / g["R323_Q305_DES_KW"]),
                     0.0)
    m_305 = min(g["R323_PHI_V305"] * m_feed_323, m_flash_gas + m_pool_vap)
    q305_avail_kw = q_flash_avail_kw + Q_e002_kw
    lvl_c003 = clamp(s.r323_c003_M / g["R323_C003_M_FULL"] * 100.0, 0.0, 100.0)
    lv501_op = g["_ctrl_ipd"](s.LIC_323501, lvl_c003, dt)
    # B-44: with the state's `valves_decided`, V1's own law at the decided stroke and FL.
    lv501_des = DECIDED_LV501_OP if s.valves_decided else g["R323_LV501_OP_DES"]
    lv501_fl = {"fl": DECIDED_LV501_FL} if s.valves_decided else {}
    # B-46: with the state's `flash_decided`, the port's lines — the liquor's live bubble
    # pressure and its design value handed to the choke.
    if s.flash_decided:
        lv501_fl["pv_bara"] = _v1_stage_pv(g, "C003", s.w_c003, s.r323_c003_T, s.r323_c003_P,
                                           g["R323_C003_T_SP_C"])
        lv501_fl["pv_des_bara"] = _v1_stage_pv(g, "C003", g["W_S314"], g["R323_C003_T_SP_C"],
                                               g["R323_C003_P_BARA"], g["R323_C003_T_SP_C"])
    m_314 = g["hydraulics"].valve_liquid_anchored(
        g["R323_M314_DES"], lv501_op / 100.0, s.r323_c003_P, s.r323_f004_P,
        g["urea_soln_rho"](s.w_c003.get("Urea", 0.0), s.r323_c003_T, g["R323_RHO_S314"]),
        lv501_des / 100.0, g["R323_C003_P_BARA"], g["R323_F004_P_BARA"],
        g["R323_RHO_C003_DES"], characteristic=g["R323_LV_CHAR"], **lv501_fl)
    seal_323501 = g["consequence"].seal_fraction(lvl_c003)
    m_314 *= seal_323501
    blow_323501_kgh = 0.0
    if seal_323501 < 1.0:
        _y_c003_gas = g["sol_vapour_y_vle"]("C003", s.w_c003, s.r323_c003_T, s.r323_c003_P,
                                            g["SOL_C003"]["alpha"])
        _mw_c003_gas = 1.0 / max(sum(v / g["MW_COMP"][k] for k, v in _y_c003_gas.items()
                                     if v > 0.0), 1e-9)
        blow_323501_kgh = g["consequence"].blowthrough_kgh(
            g["R323_M314_DES"], g["R323_RHO_C003_DES"], g["R323_C003_P_BARA"] - g["R323_F004_P_BARA"],
            lv501_op / lv501_des,
            g["consequence"].gas_density_ideal(s.r323_c003_P, s.r323_c003_T, _mw_c003_gas),
            s.r323_c003_P, max(s.r323_c003_P - s.r323_f004_P, 0.0), seal_323501)
    s.flags["LV323501_BLOWTHROUGH"] = blow_323501_kgh > 0.0
    P_c003 = (q305_avail_kw - m_305 / 3600.0 * g["R323_LAMBDA_305"])
    M_c003_pre = s.r323_c003_M
    T_dep_314 = s.r323_c003_T
    w_dep_314 = s.w_c003
    s.r323_c003_T = s.r323_c003_T + P_c003 * dt / max(M_c003_pre * cp_c003, 1e-6)
    s.r323_c003_M = max(M_c003_pre + (m_feed_323 - m_305 - m_314) / 3600.0 * dt, 1.0)
    y_305 = g["sol_vapour_y_vle"]("C003", s.w_c003, s.r323_c003_T, s.r323_c003_P,
                                  g["SOL_C003"]["alpha"])
    xi_c003 = g["sol_biuret_xi"]("C003", M_c003_pre, s.w_c003, s.r323_c003_T)
    s.w_c003 = g["sol_advance"](s.w_c003, M_c003_pre, s.r323_c003_M, m_feed_323, w_feed_323,
                                m_305, y_305, m_314, xi_c003, dt)
    r_flash_c003 = m_flash_gas / max(g["R323_M_FLASH_GAS_DES_KGH"], 1e-6)
    r_e002_c003 = m_pool_vap / max(g["R323_M_POOL_VAP_DES_KGH"], 1e-6)
    p_c003_tgt = g["c003_pressure_target_bara"](r_flash_c003, r_e002_c003, s.r3232_d001_P)
    s.r323_c003_P = clamp(
        s.r323_c003_P + (p_c003_tgt - s.r323_c003_P) / g["R323_C003_P_TAU_S"] * dt, 1.0, 12.0)
    return {
        "feed": (m_feed_323, T_feed_323, w_feed_323), "tic": tic07_op, "pic": pic02_op,
        "chest": p_chest_e002, "Q": Q_e002_kw, "Tbub": T_bub_c003, "relax": q305_relax_kw,
        "qflash": q_flash_avail_kw, "flash": m_flash_gas, "pool": m_pool_vap, "m305": m_305,
        "y305": y_305, "lvl": lvl_c003, "lv": lv501_op, "m314": m_314, "seal": seal_323501,
        "blow": blow_323501_kgh, "dep314": (T_dep_314, w_dep_314), "xi": xi_c003,
        "rf": r_flash_c003, "re": r_e002_c003, "ptgt": p_c003_tgt,
        "TT323002": s.r323_c003_T - (g["R323_C003_T_SP_C"] - g["R323_C003_T313_C"]),
    }


def _assert_tick(a: dict, b: rc.RectifyingColumnResult, s, col, loops, label):
    tic, pic, lic = loops
    assert a["feed"] == (b.feed_kgh, b.feed_t_c, b.feed_w), label
    assert (a["tic"], a["pic"], a["chest"], a["Q"]) == (
        b.tic_op_bara, b.pic_op_pct, b.chest_p_bara, b.q_e002_kw), label
    assert (a["Tbub"], a["relax"], a["qflash"], a["flash"], a["pool"], a["m305"]) == (
        b.t_bub_c, b.q_relax_kw, b.q_flash_kw, b.m_flash_gas_kgh, b.m_heater_gas_kgh,
        b.m_305_kgh), label
    assert a["y305"] == b.y_305, label
    assert (a["lvl"], a["lv"], a["m314"], a["seal"], a["blow"]) == (
        b.level_pct, b.lv501_op_pct, b.m_314_kgh, b.seal_fraction, b.blowthrough_kgh), label
    assert s.flags["LV323501_BLOWTHROUGH"] is b.lv501_blowthrough, label
    assert a["dep314"] == (b.drain_t_c, b.drain_w), label
    assert (a["xi"], a["rf"], a["re"], a["ptgt"], a["TT323002"]) == (
        b.xi_kmolh, b.flash_gas_ratio, b.heater_gas_ratio, b.p_target_bara, b.tt_323002_c), label
    assert (s.r323_c003_M, s.r323_c003_T, s.r323_c003_P, s.w_c003, s.r323_e002_chest_P) == (
        col.m_kg, col.t_c, col.p_bara, col.w, col.chest_p_bara), label
    for v1c, loop in ((s.TIC_323007, tic), (s.PIC_329202, pic), (s.LIC_323501, lic)):
        assert (v1c["op"], v1c["sp"], v1c["pv"], v1c["pv1"], v1c["pv2"], v1c["mode"]) == (
            loop.op, loop.sp, loop.pv, loop.pv1, loop.pv2, loop.mode), (label, loop.tag)


def _run(v1, script, ticks: int, dt: float = DT, before=None):
    """Drive both through `script(k)`, comparing everything every tick."""
    s = _v1_state(v1)
    col = rc.RectifyingColumn(**rc.V1_COLUMN)
    loops = (rc.tic_323007(), rc.pic_329202(rc.V1_CHEST), rc.lic_323501(taps=False))
    if before:
        before(s, col, loops)
    for k in range(ticks):
        x = script(k)
        s.steam.P_LP = x["p_lp"]
        s.r323_f004_P = x["p_f004"]
        s.r3232_d001_P = x["p_d001"]
        a = _v1_stage1(v1, s, x["drain"], x["tt323001"], x["pct"], dt)
        b = col.step(*loops, x["drain"], x["tt323001"], x["pct"], 172.0, x["p_lp"],
                     x["p_f004"], x["p_d001"], dt)
        _assert_tick(a, b, s, col, loops, f"tick {k}")
    return s, col, loops, b


def _design(**over):
    base = {"drain": FEED_DES, "tt323001": 119.0, "pct": BOTTOMS_PCT, "p_lp": P_LP_BARA,
            "p_f004": d.F004_P_BARA, "p_d001": d.E003_P_DES_BARA}
    base.update(over)
    return base


# --------------------------------------------------------------------------------------
# The design basis
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("ours, theirs", [
    ("FEED_DES_T_C", "R323_FEED_DES_T_C"), ("C003_T313_C", "R323_C003_T313_C"),
    ("C003_LVL_SP_PCT", "R323_C003_LVL_SP"),
    ("C003_M_FULL_KG", "R323_C003_M_FULL"), ("RHO_S314", "R323_RHO_S314"),
    ("LV501_CHAR", "R323_LV_CHAR"), ("E002_Q_DES_KW", "R323_E002_Q_DES_KW"),
    ("E002_PCHEST_DES_BARA", "R323_E002_PCHEST_DES"), ("E002_OP_DES_PCT", "R323_E002_OP_DES"),
    ("E002_UA_KW", "R323_E002_UA_KW"), ("Q305_DES_KW", "R323_Q305_DES_KW"),
    ("LAMBDA_305_KJKG", "R323_LAMBDA_305"), ("M_FLASH_GAS_DES_KGH", "R323_M_FLASH_GAS_DES_KGH"),
    ("M_POOL_VAP_DES_KGH", "R323_M_POOL_VAP_DES_KGH"), ("CP_S208_DES", "R323_CP_S208_DES"),
    ("CP_C003_DES", "R323_CP_C003_DES"), ("RHO_C003_DES", "R323_RHO_C003_DES"),
    ("C003_P_TAU_S", "R323_C003_P_TAU_S"),
])
def test_design_basis(v1, ours, theirs):
    """Every design constant is V1's, the chest's three on the decided anchor by V1's own
    expressions."""
    assert getattr(d, ours) == _decided(v1)[theirs]


def test_the_chest_anchor_decided_divergence(v1):
    """V1 anchors on 3.96 bar a (78.99 %, 710.0 kW/K); the port on the datasheet's 3.9 (77.79 %,
    760.6 kW/K). The design duty is the same 5858 kW on either."""
    assert v1["R323_E002_PCHEST_DES"] == 3.96
    assert d.E002_PCHEST_DES_BARA == DECIDED_E002_PCHEST_BARA
    assert v1["R323_E002_OP_DES"] == pytest.approx(78.9907, abs=1e-4)
    assert d.E002_OP_DES_PCT == pytest.approx(77.7938, abs=1e-4)
    assert v1["R323_E002_UA_KW"] == pytest.approx(710.01, abs=0.01)
    assert d.E002_UA_KW == pytest.approx(760.57, abs=0.01)


def test_the_steam_header_and_the_cascade_gains_decided_divergence(v1):
    """V1 runs the table's numbers in engineering units, PIC-329202's times its chest scale;
    the port runs them per cent of span."""
    assert P_LP_BARA == v1["R323_P_STEAM_SUP"]
    assert v1["PIC_329202_KC_SCALE"] == pytest.approx(5.8716, abs=1e-4)
    v1_state = _v1_state(v1, chest_decided=False)
    port = (rc.tic_323007(), rc.pic_329202(rc.V1_CHEST))
    assert (v1_state.TIC_323007["Kc"], v1_state.PIC_329202["Kc"]) == (
        2.0, 0.65 * v1["PIC_329202_KC_SCALE"])
    assert (port[0].Kc, port[1].Kc) == (DECIDED_TIC_323007_KC, DECIDED_PIC_329202_KC)
    assert (port[0].Kc, port[1].Kc) == (d.TIC_323007_KC, d.PIC_329202_KC)
    assert (d.TIC_323007_KC, d.PIC_329202_KC) == (0.075, pytest.approx(10.8333, abs=1e-4))


def test_the_pressure_coupling_constants_are_v1s():
    coupling = load("c003_pressure_coupling")
    assert (d.Q301_DES_M3H, d.Q302_DES_M3H, d.E003_P_DES_BARA, d.C003_P_BARA) == (
        coupling.C003_Q301_DES_M3H, coupling.C003_Q302_DES_M3H, coupling.E003_P_DES_BARA,
        coupling.C003_P_DES_BARA)
    assert d.GAS_LOAD_COEFF_M3H_PER_BAR == coupling.C003_GAS_LOAD_COEFF_M3H_PER_BAR


@pytest.mark.parametrize("r_flash", [0.0, 0.5, 1.0, 1.3])
@pytest.mark.parametrize("r_heater", [0.0, 0.7, 1.0, 1.6])
@pytest.mark.parametrize("p_down", [1.0, 3.2, 3.9])
def test_the_two_source_pressure_law(r_flash, r_heater, p_down):
    coupling = load("c003_pressure_coupling")
    assert rc.column_pressure_target_bara(r_flash, r_heater, p_down) == \
        coupling.c003_pressure_target_bara(r_flash, r_heater, p_down)


@pytest.mark.parametrize("bad", [(math.nan, 1.0, 3.2), (-0.1, 1.0, 3.2), (1.0, -0.1, 3.2),
                                 (1.0, 1.0, 0.0)])
def test_the_pressure_law_refuses_what_v1_refuses(bad):
    coupling = load("c003_pressure_coupling")
    with pytest.raises(ValueError):
        coupling.c003_pressure_target_bara(*bad)
    with pytest.raises(ValueError):
        rc.column_pressure_target_bara(*bad)


# --------------------------------------------------------------------------------------
# The column, tick by tick
# --------------------------------------------------------------------------------------

NH3_RICH_PCT = dict(Urea=53.0, Biuret=0.24, NH3=10.5, CO2=11.5, H2O=24.76)

SCENARIOS = {
    "design hold": (lambda k: _design(), 300),
    "feed cut 25 % (the line's dead time shows)": (
        lambda k: _design(drain=FEED_DES * (0.75 if k >= 20 else 1.0)), 400),
    "ammonia-rich bottoms": (lambda k: _design(pct=NH3_RICH_PCT if k >= 10 else BOTTOMS_PCT), 400),
    "letdown flashes colder": (lambda k: _design(tt323001=(114.0 if k >= 10 else 119.0)), 300),
    "LP header sags": (lambda k: _design(p_lp=(4.6 if k >= 10 else P_LP_BARA)), 400),
    "323E003 backs up": (lambda k: _design(p_d001=(3.6 if k >= 10 else 3.2)), 200),
    "flash tank pressure rises": (lambda k: _design(p_f004=(1.6 if k >= 10 else d.F004_P_BARA)), 200),
    "stripper stops producing bottoms": (lambda k: _design(drain=(0.0 if k >= 10 else FEED_DES)), 300),
    "everything at once": (
        lambda k: _design(drain=FEED_DES * (1.1 if k >= 5 else 1.0), tt323001=121.0,
                          pct=NH3_RICH_PCT, p_lp=4.8, p_d001=3.4, p_f004=1.25), 400),
}


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_stage_one_tick_by_tick(v1, name):
    script, ticks = SCENARIOS[name]
    _run(v1, script, ticks)


def test_a_temperature_set_point_step(v1):
    def before(s, col, loops):
        s.TIC_323007["sp"] = 140.0
        loops[0].sp = 140.0
    _run(v1, lambda k: _design(), 400, before=before)


def test_the_heater_steam_valve_shut(v1):
    """PV-329202 in MAN at 0 %: the chest falls to the column's own saturation, so the duty
    goes to zero within the chest solve's 1e-9 relative tolerance, and never negative."""
    def before(s, col, loops):
        for c, loop in ((s.PIC_329202, loops[1]),):
            c["mode"] = "MAN"; c["op"] = 0.0
            loop.set_mode("MAN"); loop.op = 0.0
    s, col, loops, b = _run(v1, lambda k: _design(), 300, before=before)
    assert 0.0 <= b.q_e002_kw < 1e-3            # under a watt


def test_the_column_drained_until_the_seal_breaks(v1):
    """LV-323501 forced wide open: the level falls through the nozzle seal and the column gas
    blows through into 323F004, both paths executed."""
    def before(s, col, loops):
        s.LIC_323501["mode"] = "MAN"; s.LIC_323501["op"] = 100.0
        loops[2].set_mode("MAN"); loops[2].op = 100.0
    s, col, loops, b = _run(v1, lambda k: _design(), 700, dt=0.5, before=before)
    assert b.seal_fraction < 1.0 and b.blowthrough_kgh > 0.0 and b.lv501_blowthrough


# --------------------------------------------------------------------------------------
# The decided divergence: the live TT-322004 (As-Built §XXVIII.6, formerly handoff B-10)
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("tt_322004", [160.0, 180.0])
def test_the_column_reads_the_live_stripper_bottom_and_v1_does_not(v1, tt_322004):
    """V1 reads a constant 172.0 through a store-key typo; the port reads TT-322004 live.

    Both sides are asserted: V1's flash source is the design one whatever the stripper does,
    the port's moves with it, and at 172.0 the two are the same float.
    """
    s = _v1_state(v1)
    col = rc.RectifyingColumn(**rc.V1_COLUMN)
    loops = (rc.tic_323007(), rc.pic_329202(rc.V1_CHEST), rc.lic_323501(taps=False))
    x = _design()
    a = _v1_stage1(v1, s, x["drain"], x["tt323001"], x["pct"], DT)
    b = col.step(*loops, x["drain"], x["tt323001"], x["pct"], tt_322004, x["p_lp"],
                 x["p_f004"], x["p_d001"], DT)
    assert a["rf"] == 1.0                                  # V1: blind to the stripper
    expected = (tt_322004 - 119.0) / (172.0 - 119.0)
    assert b.flash_gas_ratio == pytest.approx(expected, rel=1e-12)
    assert b.t_strip_bottom_c == tt_322004
    assert (b.flash_gas_ratio > a["rf"]) is (tt_322004 > 172.0)


# --------------------------------------------------------------------------------------
# The decided divergence: the chest anchor and the cascade gains (As-Built §XL.1-2)
# --------------------------------------------------------------------------------------

def test_a_sagging_header_saturates_v1s_steam_valve_and_not_the_ports(v1):
    """The LP header sags to 4.6 bar a. On V1's 3.96 bar a anchor PV-329202 needs more than
    its full stroke to hold the chest: it pins at 100 % and the column settles 0.12 K low. On
    the datasheet's 3.9 the valve keeps its margin and the column comes back.

    V1 verbatim and the port run side by side; the design duty is the same on both anchors.
    """
    s = _v1_state(v1, chest_decided=False)
    col = rc.RectifyingColumn(**rc.V1_COLUMN)
    loops = (rc.tic_323007(), rc.pic_329202(rc.V1_CHEST), rc.lic_323501(taps=False))
    v1_op, port_op = [], []
    for k in range(9000):
        x = _design(p_lp=(4.6 if k >= 10 else P_LP_BARA))
        s.steam.P_LP = x["p_lp"]
        a = _v1_stage1(v1, s, x["drain"], x["tt323001"], x["pct"], DT, chest_decided=False)
        b = col.step(*loops, x["drain"], x["tt323001"], x["pct"], 172.0, x["p_lp"],
                     x["p_f004"], x["p_d001"], DT)
        if k == 0:
            assert (a["chest"], b.chest_p_bara) == (3.96, 3.9)
            assert a["Q"] == pytest.approx(b.q_e002_kw, abs=1e-6)
        v1_op.append(a["pic"])
        port_op.append(b.pic_op_pct)
    assert v1_op[-1] == 100.0 and v1_op.index(100.0) * DT < 480.0
    assert s.r323_c003_T == pytest.approx(134.885, abs=1e-3)
    assert max(port_op) < 99.4
    assert abs(col.t_c - d.C003_T_SP_C) < 0.16


def test_a_set_point_step_moves_the_ports_column_more_slowly(v1):
    """TIC-323007 to 137 C. V1's 2.0 bar/K master drives the chest to 4.16 bar a in 20 minutes;
    the table's 2.00 on span, 0.075 bar/K, to 4.04. Both are heading for 137 C."""
    s = _v1_state(v1, chest_decided=False)
    col = rc.RectifyingColumn(**rc.V1_COLUMN)
    loops = (rc.tic_323007(), rc.pic_329202(rc.V1_CHEST), rc.lic_323501(taps=False))
    s.TIC_323007["sp"] = 137.0
    loops[0].sp = 137.0
    for _ in range(12000):
        x = _design()
        a = _v1_stage1(v1, s, x["drain"], x["tt323001"], x["pct"], DT, chest_decided=False)
        b = col.step(*loops, x["drain"], x["tt323001"], x["pct"], 172.0, x["p_lp"],
                     x["p_f004"], x["p_d001"], DT)
    assert a["chest"] == pytest.approx(4.163, abs=1e-3)
    assert b.chest_p_bara == pytest.approx(4.037, abs=1e-3)
    assert 136.23 < col.t_c < s.r323_c003_T < 137.0


def test_v1s_closed_loop_limit_cycle_and_the_ports_settled_column(v1, v1_verbatim):
    """Handoff B-20's closed loop, both sides. V1 verbatim, TIC-323007 at 2.0 bar/K: the loop
    reaches for 135.000 C faster than the composition cap lets the overhead follow, winds against
    the cap and cycles, 134.9896 to 135.0085 C with PV-329202 between 78.825 and 79.027 % and a
    267-268 s period. Its urea closed on the drain (decided 2026-10-10) V1's own loop holds
    135.000 C to 1e-7 K at 78.991 %, and so does the port, on the table's gains per cent of span,
    its overhead never above the cap. Run at dt = 1 s (the second hour on)."""
    s = _v1_state(v1_verbatim, chest_decided=False)
    sc = _v1_state(v1, chest_decided=False)
    col = rc.RectifyingColumn(**rc.V1_COLUMN)
    loops = (rc.tic_323007(), rc.pic_329202(rc.V1_CHEST), rc.lic_323501(taps=False))
    x = _design()
    v1_t, v1_pv, v1_m305, t, m305, tc, pvc = [], [], [], [], [], [], []
    for k in range(1, 10801):
        a = _v1_stage1(v1_verbatim, s, x["drain"], x["tt323001"], x["pct"], 1.0,
                       chest_decided=False)
        ac = _v1_stage1(v1, sc, x["drain"], x["tt323001"], x["pct"], 1.0, chest_decided=False)
        b = col.step(*loops, x["drain"], x["tt323001"], x["pct"], 172.0, x["p_lp"],
                     x["p_f004"], x["p_d001"], 1.0)
        if k > 5400:
            v1_t.append(s.r323_c003_T); v1_pv.append(a["pic"]); v1_m305.append(a["m305"])
            tc.append(sc.r323_c003_T); pvc.append(ac["pic"])
            t.append(col.t_c); m305.append(b.m_305_kgh)
    assert min(v1_t) == pytest.approx(134.9896, abs=1e-4)
    assert max(v1_t) == pytest.approx(135.0085, abs=1e-4)
    assert (min(v1_pv), max(v1_pv)) == (pytest.approx(78.825, abs=1e-3),
                                        pytest.approx(79.027, abs=1e-3))
    assert max(v1_m305) == d.M305_DES_KGH
    mean = sum(v1_t) / len(v1_t)
    ups = [i for i in range(1, len(v1_t)) if v1_t[i - 1] <= mean < v1_t[i]]
    periods = [q - p for p, q in zip(ups, ups[1:])]
    assert 267 <= min(periods) and max(periods) <= 268
    assert abs(min(tc) - 135.0) < 1e-6 and abs(max(tc) - 135.0) < 1e-6
    assert max(pvc) - min(pvc) < 1e-5 and min(pvc) == pytest.approx(78.991, abs=1e-3)
    assert abs(min(t) - 135.0) < 1e-6 and abs(max(t) - 135.0) < 1e-6
    assert max(m305) <= d.M305_DES_KGH


# --------------------------------------------------------------------------------------
# The decided divergence: LV-323501 (handoff B-44), both sides
# --------------------------------------------------------------------------------------

def test_the_vendor_valve_decided_divergence(v1):
    """V1 verbatim against the port, LIC-323501 in MAN at 75 %. Both trims are linear; the
    design drain sits at V1's 50 % and at the port's 56.65 %, so 75 % passes 1.50 times PFD 314
    in V1 and 1.32 times in the port."""
    s = _v1_state(v1, chest_decided=False, valves_decided=False)
    col = rc.RectifyingColumn(**rc.V1_COLUMN)
    loops = (rc.tic_323007(), rc.pic_329202(rc.V1_CHEST), rc.lic_323501(taps=False))
    assert (s.LIC_323501["op"], loops[2].op) == (50.0, DECIDED_LV501_OP)
    s.LIC_323501.update(mode="MAN", op=75.0)
    loops[2].set_mode("MAN")
    loops[2].op = 75.0
    x = _design()
    a = _v1_stage1(v1, s, x["drain"], x["tt323001"], x["pct"], DT, chest_decided=False)
    b = col.step(*loops, x["drain"], x["tt323001"], x["pct"], 172.0, x["p_lp"], x["p_f004"],
                 x["p_d001"], DT)
    assert a["m314"] == pytest.approx(1.5 * d.R323_M314_DES, rel=1e-12)
    assert b.m_314_kgh / d.R323_M314_DES == pytest.approx(75.0 / DECIDED_LV501_OP, rel=1e-12)


# --------------------------------------------------------------------------------------
# The decided divergence: LV-323501 flashes (handoff B-46), both sides
# --------------------------------------------------------------------------------------

def test_the_flashing_letdown_decided_divergence(v1):
    """B-46, decided 2026-09-30. 323F004 backs up to 2.0 bar a. The column liquor reaches
    LV-323501 at its bubble point, 4.1 bar a, and flashes: the port's drain chokes on
    FL^2 (P1 - FF . Pv), 0.28 bar of the 2.97 across the valve, so the drum's pressure does not
    reach it and the drain holds what it passed at 1.13 bar a. V1's law, with no vapour
    pressure, runs on the full differential and loses 16 % on the tick the drum's pressure
    moves."""
    def script(k):
        return _design(p_f004=2.0 if k >= 10 else d.F004_P_BARA)
    _, _, _, b = _run(v1, script, 11)
    _, _, _, held = _run(v1, lambda k: _design(), 11)
    assert b.m_314_kgh == held.m_314_kgh
    assert b.m_314_kgh == pytest.approx(d.R323_M314_DES, rel=1e-4)
    s = _v1_state(v1, flash_decided=False)
    for k in range(11):
        x = script(k)
        s.r323_f004_P = x["p_f004"]
        a = _v1_stage1(v1, s, x["drain"], x["tt323001"], x["pct"], DT)
    assert a["m314"] / d.R323_M314_DES == pytest.approx(
        ((d.C003_P_BARA - 2.0) / (d.C003_P_BARA - d.F004_P_BARA)) ** 0.5, rel=1e-6)
    assert a["m314"] / d.R323_M314_DES == pytest.approx(0.8409, abs=1e-4)



# --------------------------------------------------------------------------------------
# The decided divergence: the stripper's blow-through reaches the column (handoff A-16)
# --------------------------------------------------------------------------------------

def test_the_column_takes_the_stripper_blowthrough_and_v1_does_not(v1):
    """V1's section 23 hands the gas an uncovered LV-322501 passes to 323E003, so V1's column is
    the port's with no blow-through, to the bit (every test above). With 30 t/h blowing through,
    the port's column is V1's but for its pressure: the gas's own volume loads the line, and the
    target rises from V1's 4.1 bar a."""
    s = _v1_state(v1)
    col = rc.RectifyingColumn(**rc.V1_COLUMN)
    loops = (rc.tic_323007(), rc.pic_329202(rc.V1_CHEST), rc.lic_323501(taps=False))
    x = _design()
    a = _v1_stage1(v1, s, x["drain"], x["tt323001"], x["pct"], DT)
    b = col.step(*loops, x["drain"], x["tt323001"], x["pct"], 172.0, x["p_lp"], x["p_f004"],
                 x["p_d001"], DT, blow_in_kgh=30000.0, blow_mw=30.0)
    assert (a["flash"], a["pool"], a["m305"], a["rf"], a["re"]) == (
        b.m_flash_gas_kgh, b.m_heater_gas_kgh, b.m_305_kgh, b.flash_gas_ratio,
        b.heater_gas_ratio)
    assert (s.r323_c003_M, s.r323_c003_T) == (col.m_kg, col.t_c)
    assert a["ptgt"] == pytest.approx(d.C003_P_BARA, abs=1e-12)
    blow_m3h = 30000.0 / rc.gas_density_ideal(d.C003_P_BARA, col.t_c, 30.0)
    assert b.p_target_bara == rc.column_pressure_target_bara(b.flash_gas_ratio,
                                                             b.heater_gas_ratio, x["p_d001"],
                                                             blow_m3h)
    assert b.p_target_bara > a["ptgt"] + 2.0 and not b.relief_lifted


# --------------------------------------------------------------------------------------
# The decided divergence: LI-323501 between LT-323501's taps (decision 241, handoff B-156)
# --------------------------------------------------------------------------------------

def _taps_against_v1(v1, script, ticks: int, dt: float, before=None):
    """V1's stage 1, V1's column on every tick (``V1_COLUMN``), and the port's column between its
    taps on the same boundaries; returns, by tick, V1's result and the port's, with the port's
    holdup before its step."""
    s = _v1_state(v1)
    old = rc.RectifyingColumn(**rc.V1_COLUMN)
    loops_old = (rc.tic_323007(), rc.pic_329202(rc.V1_CHEST), rc.lic_323501(taps=False))
    new = rc.RectifyingColumn(chest=rc.V1_CHEST)
    loops_new = (rc.tic_323007(), rc.pic_329202(rc.V1_CHEST), rc.lic_323501())
    if before:
        before(s, loops_old, loops_new)
    out = []
    for k in range(ticks):
        x = script(k)
        s.steam.P_LP, s.r323_f004_P, s.r3232_d001_P = x["p_lp"], x["p_f004"], x["p_d001"]
        args = (x["drain"], x["tt323001"], x["pct"], 172.0, x["p_lp"], x["p_f004"], x["p_d001"], dt)
        a = _v1_stage1(v1, s, x["drain"], x["tt323001"], x["pct"], dt)
        m_pre = new.m_kg
        b, c = old.step(*loops_old, *args), new.step(*loops_new, *args)
        _assert_tick(a, b, s, old, loops_old, f"V1's column, tick {k}")
        assert c.level_pct == c003.lt_323501_pct(m_pre), k
        out.append((a, c, m_pre, s.r323_c003_M))
    return out


def test_li_323501_between_its_taps_decided_divergence(v1):
    """Decision 241, 2026-11-16 (handoff B-156): V1 reads 323C003's level as its holdup over a full
    holdup, x 100, and holds it at 60 %; the port reads it between LT-323501's taps, 2000 mm apart
    across the neck, the cone and the shell, and holds the design holdup's tap reading, the plant's
    40 %. On V1's switch the port is V1's on every tick. Between the taps the first two ticks are
    V1's, and LIC-323501 parts once the level moves: a kilogram moves the reading 1.84 times as far,
    so a 25 % cut of the bottoms at 10 s dips the holdup 199 kg (to 3331.6 kg at 86 s) where V1's
    dips 325 kg (3205.6 kg at 127 s). At dt = 0.5 s."""
    out = _taps_against_v1(v1, lambda k: _design(drain=FEED_DES * (0.75 if k >= 20 else 1.0)),
                           600, 0.5)
    parted = next(k for k, (a, c, _, _) in enumerate(out) if (c.lv501_op_pct, c.m_314_kgh) != (
        a["lv"], a["m314"]))
    assert parted == 2
    assert all((a["lvl"], c.level_pct) == (60.0, 40.0) for a, c, _, _ in out[:2])
    lo_v1 = min((m_v1, k) for k, (_, _, _, m_v1) in enumerate(out))
    lo_taps = min((m, k) for k, (_, _, m, _) in enumerate(out))
    assert (lo_v1[0], lo_v1[1]) == (pytest.approx(3205.580, abs=1e-3), 253)
    assert (lo_taps[0], lo_taps[1]) == (pytest.approx(3331.591, abs=1e-3), 173)
    assert (out[254][0]["lvl"], out[173][1].level_pct) == (pytest.approx(54.4761, abs=1e-4),
                                                           pytest.approx(33.4325, abs=1e-4))


def test_lv_323501s_seal_is_lost_at_n5_decided_divergence(v1):
    """Decision 241: with LV-323501 forced wide open, V1's seal goes at the bottom of its span, at
    3 % of its full holdup: tick 297, 162.6 kg left in the column. The port's goes 3 % of span above
    N5's lower edge on the tap reading, 32.21 %: tick 21, at 3294.2 kg, 236 kg below the design,
    where the drain leaves the column for 323F004. At dt = 0.5 s."""
    def wide(s, loops_old, loops_new):
        s.LIC_323501["mode"] = "MAN"; s.LIC_323501["op"] = 100.0
        for loops in (loops_old, loops_new):
            loops[2].set_mode("MAN"); loops[2].op = 100.0
    out = _taps_against_v1(v1, lambda k: _design(), 300, 0.5, before=wide)
    k_v1 = next(k for k, (a, _, _, _) in enumerate(out) if a["seal"] < 1.0)
    k_taps = next(k for k, (_, c, _, _) in enumerate(out) if c.seal_fraction < 1.0)
    assert (k_v1, k_taps) == (297, 21)
    assert out[k_v1][0]["lvl"] == pytest.approx(2.9470, abs=1e-4)
    assert (out[k_taps][2], out[k_taps][1].level_pct) == (pytest.approx(3294.221, abs=1e-3),
                                                          pytest.approx(32.1161, abs=1e-4))
    assert d.C003_M_DES_KG - out[k_taps][2] == pytest.approx(236.4, abs=0.1)
