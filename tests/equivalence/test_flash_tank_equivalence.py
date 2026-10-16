"""V1 <-> V1.1 equivalence for 323F004, stage 2 of unit 323.

What is being proved
--------------------
V1 writes stage 2 inline in `step_sim`, so the statements that wire it are TRANSCRIBED into
`_v1_stage2` below, line for line, and declared as such: the 323C003 -> 323F004 drain packet and
its transport (``main.py`` 8363-8375) and the flash tank itself (8410-8507). Everything they call
is V1's own code, executed: ``_ctrl_ipd``, ``sol_bubble_t_dep``, ``sol_vapour_y_vle``,
``sol_biuret_xi``, ``sol_advance``, ``_cq_packet``, ``urea_soln_cp`` and ``urea_soln_rho`` lifted
out of ``main.py``; ``hydraulics`` and ``consequence`` loaded as real modules. The LIC-323505 seed
lives inside ``State.__init__`` and is transcribed from ``main.py`` 6676-6680.

Two cp values V1 evaluates at the top of the tick (``main.py`` 8249-8250) are transcribed onto
the states they read there: ``cp_c003`` on the column state the drain departs at, and
``cp_f004`` on the drum state before stage 2 runs. Stage 1 does not touch the drum, so both are
the values V1 uses.

Stage 2 is driven on its own through twelve scripted scenarios, and then coupled to stage 1:
V1's stage-1 transcription (`test_rectifying_column_equivalence._v1_stage1`) feeds V1's stage 2
while the ported 323C003 feeds the ported 323F004, which proves the drain interface between the
two units end to end. Every tick compares every published field, the whole drum state and
LIC-323505 with ``==``.

The telemetry writes (``PROCESS_DIAGNOSTICS``) feed nothing and are not driven.

The product line (handoff B-21, decided 2026-09-30). The port's line delivers the live
departure flow and delays only the liquor's temperature, composition and cp. The transcription
carries the same switch, ``line_decided`` (default True): a property packet on a unit flow
through V1's own FIFO, and the live flow delivered; ``line_decided=False`` is V1 verbatim. A
settled line is the same float either way.

LV-323505 (handoff B-44, decided 2026-09-30). The port runs the drum's drain on its vendor trim,
Valtek's modified equal percentage, from the 67.73 % stroke its Kvs gives, on the sheet's FL,
and its blow-through on the trim's capacity ratio. The switch ``valves_decided`` (default True,
on the state) seeds LIC-323505 there and runs V1's own ``valve_liquid_anchored`` through
`decided_valves.hydraulics`, whose ``cv_fraction`` knows the trim; ``valves_decided=False`` is
V1 verbatim. Both sides are asserted in
the last section of this file.

LV-323505 flashes (handoff B-46, decided 2026-09-30): the state's ``flash_decided`` (default True)
hands its choke the drum liquor's live bubble pressure and its design value, 1.13 bar a, written
on V1's own thermo service and design anchor; ``flash_decided=False`` is V1 verbatim.
"""

from __future__ import annotations

import math

import pytest

from ureasim.data import control_valves as cvd
from ureasim.data import unit_323 as d
from ureasim.data.design_point import R323_FEED_DES_KGH as FEED_DES
from ureasim.data.design_point import R323_M314_DES, R323_M319_DES
from ureasim.data.unit_329 import P_LP_BARA
from ureasim.units.recirc import flash_tank as ft
from ureasim.units.recirc import rectifying_column as rc
from tests.equivalence import b20_switch, routes_switch
from tests.equivalence import decided_valves as dv
from tests.equivalence import test_rectifying_column_equivalence as stage1
from tests.equivalence.v1_loader import lift, load, v1_available, v1_service

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

V1_NAMES = stage1.V1_NAMES + [
    "W_S319", "SOL_F004", "R323_CP_F004_DES", "R323_F004_T_SP_C", "R323_F004_M_TAU_S",
    "R323_F004_LVL_SP", "R323_LV505_OP_DES", "R323_M701_DES", "R323_M319_DES",
    "R323_Q701_DES_KW", "R323_LAMBDA_701", "R323_F004_M_DES", "R323_F004_M_FULL",
    "R323_RHO_S319", "R323_RHO_F004_DES", "R323_F010_P_BARA", "R323_PHI_V701",
]

DT = 0.1


@pytest.fixture(scope="module")
def v1():
    coupling = load("c003_pressure_coupling")
    ns = lift(b20_switch.names(V1_NAMES), seed=b20_switch.seed({
        "math": math,
        "iapws_if97": load("iapws_if97"),
        "thermo_service": v1_service(),
        "hydraulics": load("hydraulics"),
        "consequence": load("consequence"),
        "steam_system": load("steam_system"),
        "c003_pressure_target_bara": coupling.c003_pressure_target_bara,
    }))
    # main.py 2615, 2628, 2874, 2875: the 323C003 and 323F004 design memos (bare calls).
    ns["_sol_tbub_anchor"]("C003", ns["W_S314"], ns["R323_C003_P_BARA"])
    ns["_sol_tbub_anchor"]("F004", ns["W_S319"], ns["R323_F004_P_BARA"])
    ns["_sol_alpha_anchor"]("C003", ns["W_S314"], ns["R323_C003_T_SP_C"], ns["R323_C003_P_BARA"])
    ns["_sol_alpha_anchor"]("F004", ns["W_S319"], ns["R323_F004_T_SP_C"], ns["R323_F004_P_BARA"])
    # main.py 2730-2736, the 323C003 and 323F004 rows of SOL_STAGES; second pass.
    stages = {
        "C003": {"w": ns["W_S314"], "a": ns["SOL_C003"], "M": ns["R323_C003_M_DES"],
                 "T": ns["R323_C003_T_SP_C"]},
        "F004": {"w": ns["W_S319"], "a": ns["SOL_F004"], "M": ns["R323_F004_M_DES"],
                 "T": ns["R323_F004_T_SP_C"]},
    }
    ns["sol_biuret_xi"] = lift(["sol_biuret_xi"], seed={
        "math": math, "SOL_STAGES": stages, "SOL_BIU_EA": ns["SOL_BIU_EA"],
        "SOL_BIU_ORDER": ns["SOL_BIU_ORDER"], "STRIP_R_GAS_J": ns["STRIP_R_GAS_J"],
    })["sol_biuret_xi"]
    # main.py 6239 and 6241: V1's own route objects for the two lines.
    # The isometrics' geometry (handoff A-11, decided 2026-10-07): `routes_switch`.
    ns["FEED_ROUTE"] = routes_switch.decided(ns, "322E001_TO_323C003")
    ns["INLET_ROUTE"] = routes_switch.decided(ns, "323C003_TO_323F004")
    return ns


#: LV-323505 as decided (B-44): the stroke its Kvs gives for PFD 319 [%], and its sheet's FL.
DECIDED_LV505_OP = dv.design_stroke_pct(cvd.LV_323505, R323_M319_DES)
DECIDED_LV505_FL = cvd.LV_323505.cases[cvd.LV_323505.normal].fl

def _v1_state(v1, chest_decided: bool = True, valves_decided: bool = True,
              flash_decided: bool = True):
    """The V1 plant-state fields stages 1 and 2 read and write, seeded as `State.__init__`
    seeds them (stage 1's from the 323C003 test, stage 2's from ``main.py`` 6613, 6642-6644
    and 6676-6680). `chest_decided` is stage 1's switch (As-Built §XL.1-2); `valves_decided`
    seeds both stages' vendor valves (B-44), `flash_decided` both letdowns' chokes (B-46)."""
    g = v1
    s = stage1._v1_state(v1, chest_decided=chest_decided, valves_decided=valves_decided,
                         flash_decided=flash_decided)
    s.w_f004 = dict(g["W_S319"])
    s.r323_f004_M = g["R323_F004_M_DES"]
    s.r323_f004_T = g["R323_F004_T_SP_C"]
    s.r323_f004_P = g["R323_F004_P_BARA"]
    s.r323_f010_P = g["R323_F010_P_BARA"]
    s.r3232_e011_P = g["R323_F004_P_BARA"]
    s.LIC_323505 = {"mode": "AUTO", "op": g["R323_LV505_OP_DES"],
                    "sp": g["R323_F004_LVL_SP"], "pv": g["R323_F004_LVL_SP"],
                    "pv1": g["R323_F004_LVL_SP"], "pv2": g["R323_F004_LVL_SP"],
                    "Kc": 1.0, "Ti": 100.0, "Td": 0.0, "act": -1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0, "sp_hi": 100.0}
    if valves_decided:
        s.LIC_323505["op"] = DECIDED_LV505_OP
    return s


def _v1_stage2(v1, s, m_314: float, T_dep_314: float, w_dep_314: dict, dt: float,
               line_decided: bool = True) -> dict:
    """V1 `main.py` 8363-8375 and 8410-8507, stage 2, TRANSCRIBED line for line.
    `line_decided` puts the port's inlet line in V1's (handoff B-21)."""
    g = v1
    clamp = g["clamp"]
    _cp = lambda w, T, des: g["R323_CP_SOLN"] + (g["urea_soln_cp"](w, T) - des)  # noqa: E731
    # main.py 8249-8250, on the states they read at the top of the tick (module docstring).
    cp_c003 = _cp(w_dep_314.get("Urea", 0.0), T_dep_314, g["R323_CP_C003_DES"])
    cp_f004 = _cp(s.w_f004.get("Urea", 0.0), s.r323_f004_T, g["R323_CP_F004_DES"])
    # main.py 8363-8375, the 323C003 -> 323F004 line. _transport_process, less its telemetry:
    # B-21, decided 2026-09-30: with `line_decided`, the port's lines — a property packet on the
    # unit flow through V1's own FIFO, and the live departure flow delivered.
    _pkt_dep_314 = g["_cq_packet"](1.0 if line_decided else m_314, T_dep_314, w_dep_314,
                                   cp_c003)
    _pkt_arr_314 = g["consequence"].transport_process_packet(
        s.tlag, "PROCESS_323C003_TO_323F004", _pkt_dep_314, g["INLET_ROUTE"], m_314, dt)
    if _pkt_arr_314 == _pkt_dep_314:
        m_314_in, T_314_in, w_314_in, cp_314_in = m_314, T_dep_314, w_dep_314, cp_c003
    else:
        m_314_in = m_314 if line_decided else _pkt_arr_314.mass_kgh
        T_314_in = _pkt_arr_314.temperature_c
        w_314_in = g["_w_norm"](_pkt_arr_314.mass_fraction, w_dep_314)
        cp_314_in = _cp(w_314_in.get("Urea", 0.0), T_314_in, g["R323_CP_C003_DES"])
    # main.py 8420-8507, the flash tank.
    T_sat_f004 = g["sol_bubble_t_dep"]("F004", s.w_f004, s.r323_f004_P, g["R323_F004_T_SP_C"],
                                       g["bubble_T_raoult"](g["R323_F004_P_BARA"], g["W_S319"]))
    q701_relax_kw = (s.r323_f004_M * cp_f004 * (T_sat_f004 - s.r323_f004_T)
                     / g["R323_F004_M_TAU_S"])
    q701_avail_kw = m_314_in / 3600.0 * cp_314_in * (T_314_in - s.r323_f004_T)
    m_701 = max(g["R323_M701_DES"] * ((q701_avail_kw - q701_relax_kw) / g["R323_Q701_DES_KW"]),
                0.0)
    lvl_f004 = clamp(s.r323_f004_M / g["R323_F004_M_FULL"] * 100.0, 0.0, 100.0)
    lv505_op = g["_ctrl_ipd"](s.LIC_323505, lvl_f004, dt)
    # B-46: with the state's `flash_decided`, the port's lines — the liquor's live bubble
    # pressure and its design value handed to the choke.
    lv505_pv = {}
    if s.flash_decided:
        lv505_pv = {"pv_bara": stage1._v1_stage_pv(g, "F004", s.w_f004, s.r323_f004_T,
                                                   s.r323_f004_P, g["R323_F004_T_SP_C"]),
                    "pv_des_bara": stage1._v1_stage_pv(g, "F004", g["W_S319"],
                                                       g["R323_F004_T_SP_C"],
                                                       g["R323_F004_P_BARA"],
                                                       g["R323_F004_T_SP_C"])}
    if s.valves_decided:  # B-44: V1's own law, on the vendor trim, stroke and FL
        m_319 = dv.hydraulics().valve_liquid_anchored(
            g["R323_M319_DES"], lv505_op / 100.0, s.r323_f004_P, s.r323_f010_P,
            g["urea_soln_rho"](s.w_f004.get("Urea", 0.0), s.r323_f004_T, g["R323_RHO_S319"]),
            DECIDED_LV505_OP / 100.0, g["R323_F004_P_BARA"], g["R323_F010_P_BARA"],
            g["R323_RHO_F004_DES"], characteristic=dv.MOD_EQUAL_PCT, fl=DECIDED_LV505_FL,
            **lv505_pv)
        theta_505 = dv.trim(lv505_op / 100.0) / dv.trim(DECIDED_LV505_OP / 100.0)
    else:
        m_319 = g["hydraulics"].valve_liquid_anchored(
            g["R323_M319_DES"], lv505_op / 100.0, s.r323_f004_P, s.r323_f010_P,
            g["urea_soln_rho"](s.w_f004.get("Urea", 0.0), s.r323_f004_T, g["R323_RHO_S319"]),
            g["R323_LV505_OP_DES"] / 100.0, g["R323_F004_P_BARA"], g["R323_F010_P_BARA"],
            g["R323_RHO_F004_DES"], characteristic=g["R323_LV_CHAR"], **lv505_pv)
        theta_505 = lv505_op / g["R323_LV505_OP_DES"]
    seal_323505 = g["consequence"].seal_fraction(lvl_f004)
    m_319 *= seal_323505
    blow_323505_kgh = 0.0
    n_blow_323505 = 0.0
    y_blow_323505 = None
    if seal_323505 < 1.0:
        _y_f004_gas = g["sol_vapour_y_vle"]("F004", s.w_f004, s.r323_f004_T, s.r323_f004_P,
                                            g["SOL_F004"]["alpha"])
        _mw_f004_gas = 1.0 / max(sum(v / g["MW_COMP"][k] for k, v in _y_f004_gas.items()
                                     if v > 0.0), 1e-9)
        blow_323505_kgh = g["consequence"].blowthrough_kgh(
            g["R323_M319_DES"], g["R323_RHO_F004_DES"],
            g["R323_F004_P_BARA"] - g["R323_F010_P_BARA"],
            theta_505,
            g["consequence"].gas_density_ideal(s.r323_f004_P, s.r323_f004_T, _mw_f004_gas),
            s.r323_f004_P, max(s.r323_f004_P - s.r323_f010_P, 0.0), seal_323505)
        n_blow_323505 = blow_323505_kgh / _mw_f004_gas
        y_blow_323505 = _y_f004_gas
    s.flags["LV323505_BLOWTHROUGH"] = blow_323505_kgh > 0.0
    dep319 = (s.r323_f004_T, s.w_f004)            # _cq_packet(m_319, s.r323_f004_T, s.w_f004, ...)
    P_f004 = (m_314_in / 3600.0 * cp_314_in * (T_314_in - s.r323_f004_T)
              - m_701 / 3600.0 * g["R323_LAMBDA_701"])
    M_f004_pre = s.r323_f004_M
    k_cap_f004 = m_314_in / 3600.0 * cp_314_in
    s.r323_f004_T = s.r323_f004_T + P_f004 * dt / max(M_f004_pre * cp_f004 + k_cap_f004 * dt,
                                                      1e-6)
    s.r323_f004_M = max(M_f004_pre + (m_314_in - m_701 - m_319) / 3600.0 * dt, 1.0)
    y_701 = g["sol_vapour_y_vle"]("F004", s.w_f004, s.r323_f004_T, s.r323_f004_P,
                                  g["SOL_F004"]["alpha"])
    xi_f004 = g["sol_biuret_xi"]("F004", M_f004_pre, s.w_f004, s.r323_f004_T)
    s.w_f004 = g["sol_advance"](s.w_f004, M_f004_pre, s.r323_f004_M, m_314_in, w_314_in,
                                m_701, y_701, m_319, xi_f004, dt)
    s.r323_f004_P = s.r3232_e011_P
    return {
        "feed": (m_314_in, T_314_in, w_314_in, cp_314_in), "Tsat": T_sat_f004,
        "relax": q701_relax_kw, "avail": q701_avail_kw, "m701": m_701, "y701": y_701,
        "lvl": lvl_f004, "lv": lv505_op, "m319": m_319, "seal": seal_323505,
        "blow": (blow_323505_kgh, n_blow_323505, y_blow_323505), "dep319": dep319,
        "xi": xi_f004,
    }


def _assert_tick(a: dict, b: ft.FlashTankResult, s, tank, lic, label):
    assert a["feed"] == (b.feed_kgh, b.feed_t_c, b.feed_w, b.feed_cp), label
    assert (a["Tsat"], a["relax"], a["avail"], a["m701"]) == (
        b.t_bub_c, b.q_relax_kw, b.q_avail_kw, b.m_701_kgh), label
    assert a["y701"] == b.y_701, label
    assert (a["lvl"], a["lv"], a["m319"], a["seal"]) == (
        b.level_pct, b.lv505_op_pct, b.m_319_kgh, b.seal_fraction), label
    assert a["blow"] == (b.blowthrough_kgh, b.blowthrough_kmolh, b.blowthrough_y), label
    assert s.flags["LV323505_BLOWTHROUGH"] is b.lv505_blowthrough, label
    assert a["dep319"] == (b.drain_t_c, b.drain_w), label
    assert a["xi"] == b.xi_kmolh, label
    assert (s.r323_f004_M, s.r323_f004_T, s.r323_f004_P, s.w_f004) == (
        tank.m_kg, tank.t_c, tank.p_bara, tank.w), label
    assert (b.m_kg, b.t_c, b.p_bara, b.w) == (tank.m_kg, tank.t_c, tank.p_bara, tank.w), label
    c = s.LIC_323505
    assert (c["op"], c["sp"], c["pv"], c["pv1"], c["pv2"], c["mode"]) == (
        lic.op, lic.sp, lic.pv, lic.pv1, lic.pv2, lic.mode), label


def _run(v1, script, ticks: int, dt: float = DT, before=None):
    """Drive stage 2 alone through `script(k)`, comparing everything every tick."""
    s = _v1_state(v1)
    tank = ft.FlashTank()
    lic = ft.lic_323505()
    if before:
        before(s, tank, lic)
    for k in range(ticks):
        x = script(k)
        s.r3232_e011_P = x["p_e011"]
        s.r323_f010_P = x["p_f010"]
        a = _v1_stage2(v1, s, x["m314"], x["t314"], x["w314"], dt)
        b = tank.step(lic, x["m314"], x["t314"], x["w314"], x["p_e011"], x["p_f010"], dt)
        _assert_tick(a, b, s, tank, lic, f"tick {k}")
    return s, tank, lic, b


#: The 323C003 bottoms as the column publishes them at design.
W314 = dict(d.W_S314)
#: Column bottoms carrying twice the design ammonia, as a starved heater leaves them.
W314_NH3 = {k: v for k, v in W314.items()}
W314_NH3["NH3"] = 2.0 * W314["NH3"]
W314_NH3["H2O"] = W314["H2O"] - W314["NH3"]


def _design(**over):
    base = {"m314": R323_M314_DES, "t314": d.C003_T_SP_C, "w314": W314,
            "p_e011": d.F004_P_BARA, "p_f010": d.F010_P_BARA}
    base.update(over)
    return base


# --------------------------------------------------------------------------------------
# The design basis
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("ours, theirs", [
    ("F004_P_BARA", "R323_F004_P_BARA"), ("F004_T_SP_C", "R323_F004_T_SP_C"),
    ("F004_M_TAU_S", "R323_F004_M_TAU_S"), ("M701_DES_KGH", "R323_M701_DES"),
    ("F004_M_DES_KG", "R323_F004_M_DES"), ("F004_LVL_SP_PCT", "R323_F004_LVL_SP"),
    ("F004_M_FULL_KG", "R323_F004_M_FULL"),
    ("RHO_S319", "R323_RHO_S319"), ("CP_F004_DES", "R323_CP_F004_DES"),
    ("RHO_F004_DES", "R323_RHO_F004_DES"), ("Q701_DES_KW", "R323_Q701_DES_KW"),
    ("LAMBDA_701_KJKG", "R323_LAMBDA_701"), ("F010_P_BARA", "R323_F010_P_BARA"),
    ("W_S319", "W_S319"),
])
def test_design_basis(v1, ours, theirs):
    assert getattr(d, ours) == v1[theirs]


def test_the_design_flows(v1):
    assert R323_M319_DES == v1["R323_M319_DES"]
    assert R323_M314_DES == v1["R323_M314_DES"]


# --------------------------------------------------------------------------------------
# The flash tank on its own, tick by tick
# --------------------------------------------------------------------------------------

SCENARIOS = {
    "design hold": (lambda k: _design(), 300),
    "drain cut 25 % (the line's dead time shows)": (
        lambda k: _design(m314=R323_M314_DES * (0.75 if k >= 20 else 1.0)), 500),
    "drain up 20 %": (lambda k: _design(m314=R323_M314_DES * (1.2 if k >= 10 else 1.0)), 400),
    "hotter column bottoms": (lambda k: _design(t314=(140.0 if k >= 10 else 135.0)), 400),
    "column bottoms colder than the drum": (
        lambda k: _design(t314=(100.0 if k >= 10 else 135.0)), 400),
    "ammonia-rich column bottoms": (lambda k: _design(w314=(W314_NH3 if k >= 10 else W314)), 400),
    "flash condenser pressure rises": (
        lambda k: _design(p_e011=(1.30 if k >= 10 else d.F004_P_BARA)), 400),
    "flash condenser pressure falls": (
        lambda k: _design(p_e011=(1.00 if k >= 10 else d.F004_P_BARA)), 400),
    "pre-evaporator vacuum lost": (
        lambda k: _design(p_f010=(0.90 if k >= 10 else d.F010_P_BARA)), 400),
    "everything at once": (
        lambda k: _design(m314=R323_M314_DES * (1.1 if k >= 5 else 1.0), t314=138.0,
                          w314=W314_NH3, p_e011=1.2, p_f010=0.55), 500),
}


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_stage_two_tick_by_tick(v1, name):
    script, ticks = SCENARIOS[name]
    _run(v1, script, ticks)


def test_a_level_set_point_step(v1):
    def before(s, tank, lic):
        s.LIC_323505["sp"] = 40.0
        lic.sp = 40.0
    _run(v1, lambda k: _design(), 400, before=before)


def test_a_stopped_column_drain_the_port_against_its_transcription(v1):
    """323C003 stops draining: on the decided line the drum receives nothing from that tick."""
    s, tank, lic, b = _run(v1, lambda k: _design(m314=(0.0 if k >= 10 else R323_M314_DES)),
                           1200, dt=DT)
    assert b.feed_kgh == 0.0


def test_a_stopped_column_drain_decided_divergence(v1):
    """Handoff B-21, decided 2026-09-30, both sides. 323C003 stops draining at 1 s. V1's line
    goes on delivering the design drain — a stopped carrier takes the dead time to its 1800 s
    cap and the FIFO holds the last arrived packet — so its drum flashes liquor that was never
    sent; the port's receives nothing from the stop. Bit-exact until the stop; two minutes on,
    V1 has taken in 3.5 t the column never sent."""
    s, tank, lic = _v1_state(v1), ft.FlashTank(), ft.lic_323505()
    v1_in = port_in = 0.0
    for k in range(1210):
        x = _design(m314=(0.0 if k >= 10 else R323_M314_DES))
        s.r3232_e011_P, s.r323_f010_P = x["p_e011"], x["p_f010"]
        a = _v1_stage2(v1, s, x["m314"], x["t314"], x["w314"], DT, line_decided=False)
        b = tank.step(lic, x["m314"], x["t314"], x["w314"], x["p_e011"], x["p_f010"], DT)
        if k < 10:
            _assert_tick(a, b, s, tank, lic, f"tick {k}")
            continue
        assert a["feed"][0] == pytest.approx(R323_M314_DES, rel=1e-12) and b.feed_kgh == 0.0
        v1_in += a["feed"][0] * DT / 3600.0
        port_in += b.feed_kgh * DT / 3600.0
    assert port_in == 0.0 and v1_in == pytest.approx(R323_M314_DES * 120.0 / 3600.0, rel=1e-9)


def test_lv323505_forced_open_until_the_seal_breaks(v1):
    """LV-323505 in MAN at 100 %: the level falls through the nozzle seal and the drum's
    vapour blows through to 323F010, both paths executed."""
    def before(s, tank, lic):
        s.LIC_323505["mode"] = "MAN"; s.LIC_323505["op"] = 100.0
        lic.set_mode("MAN"); lic.op = 100.0
    s, tank, lic, b = _run(v1, lambda k: _design(), 700, dt=0.5, before=before)
    assert b.seal_fraction < 1.0 and b.blowthrough_kgh > 0.0 and b.lv505_blowthrough
    assert b.blowthrough_y is not None and b.blowthrough_kmolh > 0.0


# --------------------------------------------------------------------------------------
# Stages 1 and 2 coupled: the drain interface, end to end
# --------------------------------------------------------------------------------------

def _run_coupled(v1, script, ticks: int, dt: float = DT, before=None):
    """V1's stage 1 feeds V1's stage 2; the ported 323C003 feeds the ported 323F004. Stage 1
    reads the drum pressure as it stood at the top of the tick, as V1 does."""
    s = _v1_state(v1)
    col = rc.RectifyingColumn(chest=rc.V1_CHEST)
    loops = (rc.tic_323007(), rc.pic_329202(rc.V1_CHEST), rc.lic_323501())
    tank = ft.FlashTank()
    lic = ft.lic_323505()
    if before:
        before(s, col, loops, tank, lic)
    for k in range(ticks):
        x = script(k)
        s.r3232_e011_P = x["p_e011"]
        a1 = stage1._v1_stage1(v1, s, x["drain"], 119.0, stage1.BOTTOMS_PCT, dt)
        a2 = _v1_stage2(v1, s, a1["m314"], a1["dep314"][0], a1["dep314"][1], dt)
        b1 = col.step(*loops, x["drain"], 119.0, stage1.BOTTOMS_PCT, 172.0, P_LP_BARA,
                      tank.p_bara, d.E003_P_DES_BARA, dt)
        b2 = tank.step(lic, b1.m_314_kgh, b1.drain_t_c, b1.drain_w, x["p_e011"],
                       d.F010_P_BARA, dt)
        stage1._assert_tick(a1, b1, s, col, loops, f"stage 1, tick {k}")
        _assert_tick(a2, b2, s, tank, lic, f"stage 2, tick {k}")
    return b1, b2


def test_the_two_stages_coupled_through_a_feed_cut(v1):
    _run_coupled(v1, lambda k: {"drain": FEED_DES * (0.8 if k >= 20 else 1.0),
                                "p_e011": d.F004_P_BARA}, 600)


def test_the_two_stages_coupled_through_a_flash_condenser_upset(v1):
    """The node pressure steps; the drum adopts it a tick later and 323C003's LV-323501 reads
    it a tick after that, exactly as V1 orders the reads."""
    _run_coupled(v1, lambda k: {"drain": FEED_DES,
                                "p_e011": (1.35 if k >= 10 else d.F004_P_BARA)}, 400)


# --------------------------------------------------------------------------------------
# The decided divergence: LV-323505 (handoff B-44), both sides
# --------------------------------------------------------------------------------------

def test_the_vendor_valve_decided_divergence(v1):
    """V1 verbatim against the port, LIC-323505 in MAN at 85 % on design boundaries. At design
    both drain PFD 319; stroked, V1's linear trim from 50 % passes 1.70 times it, the vendor's
    modified equal percentage from 67.73 % 1.68 times."""
    s = _v1_state(v1, valves_decided=False)
    tank, lic = ft.FlashTank(), ft.lic_323505()
    assert (s.LIC_323505["op"], lic.op) == (50.0, DECIDED_LV505_OP)
    s.LIC_323505.update(mode="MAN", op=85.0)
    lic.set_mode("MAN")
    lic.op = 85.0
    x = _design()
    a = _v1_stage2(v1, s, x["m314"], x["t314"], x["w314"], DT)
    b = tank.step(lic, x["m314"], x["t314"], x["w314"], x["p_e011"], x["p_f010"], DT)
    assert a["m319"] == pytest.approx(1.7 * R323_M319_DES, rel=1e-12)
    assert b.m_319_kgh / R323_M319_DES == pytest.approx(1.6774, abs=1e-4)
