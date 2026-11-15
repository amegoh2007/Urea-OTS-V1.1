"""V1 <-> V1.1 equivalence for 323E003 / 323D001 / 323P001, the LP carbamate condenser.

What is being proved
--------------------
V1 writes the condenser inline in `step_sim`, so its statements are TRANSCRIBED into
`_v1_stage8` below, line for line, and declared as such (``main.py`` 9513-9578). Everything they
call is V1's own code, executed: ``_ctrl_ipd``, ``_lag1``, ``clamp`` and ``tsat_steam`` lifted
out of ``main.py``. The state and the four controllers are seeded inside ``State.__init__`` and
are transcribed from ``main.py`` 6887-6948.

The condenser is driven on its own through scenarios chosen to take every branch — the gas up
and down, the capacity outrunning the gas, the gas gone, each liquid inlet stepped, both
blow-throughs, the 323E011 node it vents to, PIC-323202 in MAN and on a new set point,
TIC-323013 on the tempered water both ways and in MAN, the pump in MAN down to the tank's heel —
then coupled to V1's 323C003, which rides this node one tick later, and to V1's 323E011, which
takes 321 on the tick and returns 718B on the next, and last through V1's stages 1 to 4, 8 and 9
end to end. Every tick compares every published field, the node, the tank, the water, both lags
and all four controllers with ``==``.

The decided divergences (2026-09-27, handoffs B-32, B-34, B-35)
---------------------------------------------------------------
PIC-323202 runs the tuning table's gain on PT-323202's span, 20 %/bar and 100 s, where V1 runs
5.0 %/bar and 40 s. The identity scenarios run the port's PIC-323202 on V1's tuning; the decided
tuning is proved in its own section: bit-exact while the node sits on its set point, and then
both sides asserted. TIC-323013's and SIC-323901's rescaled gains are V1's own numbers and are
compared on every tick.

PFD 734, FIC-323401's ammonia water from 328D003, enters the condenser as its departure from the
PFD's row (B-37 and B-94, decided 2026-10-10 and 2026-10-14); V1 books it into no unit. With
``m_734_kgh`` None, as every identity scenario runs it, or at the design flow, the port is V1's; its
test asserts both sides.

The capacity is no longer capped at the gas that arrives (B-34), and 323P001 is capped at the
tank's heel in place of V1's floor guard (B-35). The transcription carries both decisions as a
switch on exactly those two lines, so the identity scenarios compare the rest of V1's stage 8
tick for tick wherever the two limits are reached; the tests of the two decisions run V1's own
lines and assert both sides.
"""

from __future__ import annotations

import math

import pytest

from ureasim.data import control_valves_fisher as fv
from ureasim.data import unit_323 as d
from ureasim.data import unit_323e003 as e3
from ureasim.data import unit_323e011 as e
from ureasim.data.design_point import R323_FEED_DES_KGH as FEED_DES
from ureasim.data.desorption_train import D001_T_C
from ureasim.data.unit_322c001 import C001_T_C
from ureasim.data.unit_329 import P_LP_BARA
from ureasim.units.recirc import flash_condenser as fc
from ureasim.units.recirc import flash_tank as ft
from ureasim.units.recirc import lp_carbamate_condenser as lp
from ureasim.units.recirc import pre_evaporator as pe
from ureasim.units.recirc import rectifying_column as rc
from ureasim.units.recirc import solution_tank as st
from tests.equivalence import decided_valves as dv
from tests.equivalence import routes_switch
from tests.equivalence import test_flash_condenser_equivalence as stage9
from tests.equivalence import test_flash_tank_equivalence as stage2
from tests.equivalence import test_pre_evaporator_equivalence as stage3
from tests.equivalence import test_rectifying_column_equivalence as stage1
from tests.equivalence import test_solution_tank_equivalence as stage4
from tests.equivalence.v1_loader import load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

E003_NAMES = [
    "R3232_E003_M305_DES", "R3232_E003_M718B_DES", "R3232_E003_M776_DES", "R3232_M797_DES",
    "R3232_M797_T", "R3232_E003_IN_DES", "R3232_E003_PHI321", "R3232_E003_M321_DES",
    "R3232_E003_M308_DES", "R3232_E003_T", "R3232_TW_T", "R3232_E003_T305", "R3232_TW_SUP_T",
    "R3232_TW_RET_T", "R3232_TV13_DES_PCT", "R3232_TW_TAU_S", "R3232_D001_P_BARA",
    "R3232_E003_PV_OP_DES", "R3232_D001_M_FULL", "R3232_D001_LVL_SP", "R3232_D001_M_DES",
    "R3232_E003_Q_DES_KW", "R3232_E003_UA_KW", "R3232_E003_M_COND_DES", "R3232_ENV_GAS_V_M3",
    "R3232_ENV_GAS_RHO_DES", "R3232_ENV_GAS_C_KG_BAR", "_R3232_TSAT_E003_DES",
    "R3232_E003_SENS", "R3232_E003_LAMC", "R3232_P001_RPM_DES", "R328_D001_T",
    "R328_D001_M776_DES", "tsat_steam",
]
V1_NAMES = stage9.V1_NAMES + E003_NAMES

DT = 0.1


@pytest.fixture(scope="module")
def v1():
    ns = stage3.build_v1(V1_NAMES)
    # The isometrics' geometry (handoff A-11, decided 2026-10-07): `routes_switch`.
    ns["D002_ROUTE"] = routes_switch.decided(ns, "323F010_TO_323D002")
    ns["coupling"] = load("c003_pressure_coupling")
    return ns



#: PV-323202 as decided (decision 150), re-derived from Fisher's sheet: the linear trim's design
#: stroke [%] where its rated Cv passes PFD 321 on the normal case.
DECIDED_PV202_OP = dv.design_stroke_pct(fv.PV_323202, e3.E003_M321_DES_KGH)

def _v1_state(v1, vent: bool = True):
    """The V1 plant-state fields stages 1 to 4, 8 and 9 read and write, seeded as
    `State.__init__` seeds them (stages 1 to 4 and 9 from their own tests, the LPCC from
    ``main.py`` 6887-6948); `vent` seeds PIC-323202 on PV-323202's decided stroke."""
    g = v1
    s = stage9._v1_state(v1)
    s.r3232_e003_T = g["R3232_E003_T"]
    s.r3232_d001_M = g["R3232_D001_M_DES"]
    s.r3232_d001_P = g["R3232_D001_P_BARA"]
    P = g["R3232_D001_P_BARA"]
    s.PIC_323202 = {"mode": "AUTO", "op": DECIDED_PV202_OP if vent else g["R3232_E003_PV_OP_DES"],
                    "sp": P, "pv": P, "pv1": P, "pv2": P,
                    "Kc": 5.0, "Ti": 40.0, "Td": 0.0, "act": -1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 2.0, "sp_hi": 5.0}
    L, rpm = g["R3232_D001_LVL_SP"], g["R3232_P001_RPM_DES"]
    s.LIC_323502 = {"mode": "AUTO", "op": rpm, "sp": L, "pv": L, "pv1": L, "pv2": L,
                    "Kc": 1.5, "Ti": 300.0, "Td": 0.0, "act": -1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0, "sp_hi": 100.0}
    s.SIC_323901 = {"mode": "CAS", "op": rpm, "sp": rpm, "pv": rpm, "pv1": rpm, "pv2": rpm,
                    "Kc": 1.1, "Ti": 30.0, "Td": 0.0, "act": +1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0, "sp_hi": 100.0}
    T = g["R3232_TW_SUP_T"]
    s.TIC_323013 = {"mode": "CAS", "op": g["R3232_TV13_DES_PCT"], "sp": T, "pv": T, "pv1": T,
                    "pv2": T, "Kc": 1.0, "Ti": 100.0, "Td": 0.0, "act": -1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 45.0, "sp_hi": g["R3232_TW_RET_T"]}
    return s


def _v1_stage8(v1, s, m_305, m718B_prev, m_776, m_flash_gas, m_pool_vap, blow_322501_kgh,
               blow_323501_kgh, dt, decided: bool = True, vent: bool = True):
    """V1 `main.py` 9513-9578, stage 8, TRANSCRIBED line for line.

    With `decided` (the default), V1's two lines the process engineer decided against on
    2026-09-27 are replaced by the decided relations — the capacity uncapped (B-34) and the
    heel cap on 323P001 in place of the floor guard (B-35) — so every scenario still compares
    the rest of V1's statements with the port tick for tick. ``decided=False`` runs V1's own
    lines; the tests of those two decisions use it to assert both sides. `vent` (the default)
    anchors PV-323202's line on its decided design stroke (decision 150), V1's own line from
    Fisher's 36.45 % in place of 25 %."""
    g = v1
    clamp, _lag1, _ctrl_ipd = g["clamp"], g["_lag1"], g["_ctrl_ipd"]
    Te003 = s.r3232_e003_T
    in_e003 = m_305 + m718B_prev + m_776 + g["R3232_M797_DES"]
    pic202_op = _ctrl_ipd(s.PIC_323202, s.r3232_d001_P, dt)
    dP_v202 = max(s.r3232_d001_P - s.r3232_e011_P, 0.0)
    pv202_op_des = DECIDED_PV202_OP if vent else g["R3232_E003_PV_OP_DES"]
    m_321 = (g["R3232_E003_M321_DES"] * (pic202_op / pv202_op_des)
             * math.sqrt(dP_v202 / (g["R3232_D001_P_BARA"] - g["R3232_E011_P_BARA"])))
    lvl_d001_323 = s.r3232_d001_M / g["R3232_D001_M_DES"] * g["R3232_D001_LVL_SP"]
    lic502_op = _ctrl_ipd(s.LIC_323502, lvl_d001_323, dt)
    rpm_pv = _lag1(s.tlag, "S_323901", s.SIC_323901["op"], 3.0, dt)
    sic_op = _ctrl_ipd(s.SIC_323901, rpm_pv, dt, lic502_op)
    m_308 = g["R3232_E003_M308_DES"] * (sic_op / g["R3232_P001_RPM_DES"])
    tva_op = s.TIC_323013["op"]
    RET, SUP = g["R3232_TW_RET_T"], g["R3232_TW_SUP_T"]
    T_tw_ss = clamp(RET - (RET - SUP) * (tva_op / max(g["R3232_TV13_DES_PCT"], 1e-6)), 20.0, RET)
    T_tw_sup = _lag1(s.tlag, "R3232_TW_SUP", T_tw_ss, g["R3232_TW_TAU_S"], dt)
    T_tw_ret = s.tlag.get("R3232_TW_RET", RET)
    tic13_op = _ctrl_ipd(s.TIC_323013, T_tw_sup, dt)
    Q_e003 = g["R3232_E003_UA_KW"] * (Te003 - 0.5 * (T_tw_sup + T_tw_ret))
    T_tw_ret = T_tw_sup + (RET - SUP) * (Q_e003 / g["R3232_E003_Q_DES_KW"])
    s.tlag["R3232_TW_RET"] = T_tw_ret
    m_cond = m_305 + g["R3232_M797_DES"] - m_321
    sens_e003 = ((m_305 * (g["R3232_E003_T305"] - Te003)
                  + m718B_prev * (g["R3232_E011_T"] - Te003)
                  + m_776 * (g["R328_D001_T"] - Te003)
                  + g["R3232_M797_DES"] * (g["R3232_M797_T"] - Te003)) / 3600.0 * g["R3232_CP"])
    P_e003 = sens_e003 + m_cond / 3600.0 * g["R3232_E003_LAMC"] - Q_e003
    m_env_in = (m_flash_gas + m_pool_vap + g["R3232_M797_DES"] + blow_322501_kgh
                - blow_323501_kgh)
    T_dew_env = g["R3232_E003_T"] + (g["tsat_steam"](s.r3232_d001_P) - g["_R3232_TSAT_E003_DES"])
    m_env_cond = min(g["R3232_E003_M_COND_DES"]
                     * max(T_dew_env - 0.5 * (T_tw_sup + T_tw_ret), 0.0)
                     / (g["R3232_E003_T"] - g["R3232_TW_T"]),
                     m_env_in)
    # The capacity inside the min(), evaluated again on its own for the comparison.
    cap = (g["R3232_E003_M_COND_DES"] * max(T_dew_env - 0.5 * (T_tw_sup + T_tw_ret), 0.0)
           / (g["R3232_E003_T"] - g["R3232_TW_T"]))
    if decided:
        m_env_cond = cap  # B-34: the whole capacity
    dM_env = m_env_in - m_env_cond - m_321
    s.r3232_d001_P = max(s.r3232_d001_P + dM_env / g["R3232_ENV_GAS_C_KG_BAR"] / 3600.0 * dt, 0.1)
    k_cap_e003 = ((m_305 + m718B_prev + m_776 + g["R3232_M797_DES"]) / 3600.0 * g["R3232_CP"]
                  + g["R3232_E003_UA_KW"])
    s.r3232_e003_T = Te003 + P_e003 * dt / max(s.r3232_d001_M * g["R3232_CP"] + k_cap_e003 * dt,
                                               1e-6)
    lost = False
    if decided:
        # B-35: the heel cap, in place of V1's guard below.
        avail = max(max(s.r3232_d001_M - 1.0, 0.0) / max(dt, 1e-9) * 3600.0 + in_e003 - m_321,
                    0.0)
        lost = m_308 > avail
        if lost:
            m_308 = avail
    elif s.r3232_d001_M <= 1.0 and m_308 > (in_e003 - m_321):
        m_308 = max(in_e003 - m_321, 0.0)
    s.r3232_d001_M = max(s.r3232_d001_M + (in_e003 - m_321 - m_308) / 3600.0 * dt, 1.0)
    s.tlag["M308_KGH"] = m_308
    return {
        "in": in_e003, "pic": pic202_op, "m321": m_321, "lvl": lvl_d001_323, "lic": lic502_op,
        "rpm_pv": rpm_pv, "sic": sic_op, "m308": m_308, "lost": lost, "tva": tva_op,
        "tw_ss": T_tw_ss,
        "tw_sup": T_tw_sup, "tic": tic13_op, "Q": Q_e003, "tw_ret": T_tw_ret, "cond": m_cond,
        "env_in": m_env_in, "Tdew": T_dew_env, "cap": cap, "env_cond": m_env_cond,
        # main.py 10682, the level the operator reads.
        "LI": s.r3232_d001_M / g["R3232_D001_M_FULL"] * 100.0,
    }


def _assert_tick(a: dict, b: lp.LpCarbamateCondenserResult, s, lpcc, loops, label):
    pic, lic, sic, tic = loops
    assert (a["in"], a["pic"], a["m321"]) == (b.in_kgh, b.pic_op_pct, b.m_321_kgh), label
    assert (a["lvl"], a["lic"], a["rpm_pv"], a["sic"], a["m308"], a["lost"]) == (
        b.lic_pv_pct, b.lic_op_rpm, b.speed_pv_rpm, b.sic_op_rpm, b.m_308_kgh,
        b.suction_lost), label
    assert (a["tva"], a["tw_ss"], a["tw_sup"], a["tic"], a["Q"], a["tw_ret"]) == (
        b.tv_a_op_pct, b.tw_supply_ss_c, b.tw_supply_c, b.tic_op_pct, b.q_kw,
        b.tw_return_c), label
    assert (a["cond"], a["env_in"], a["Tdew"], a["cap"], a["env_cond"]) == (
        b.m_cond_kgh, b.env_in_kgh, b.t_dew_c, b.capacity_kgh, b.env_cond_kgh), label
    assert (s.r3232_d001_P, s.r3232_e003_T, s.r3232_d001_M, s.tlag["R3232_TW_RET"]) == (
        lpcc.p_bara, lpcc.t_c, lpcc.m_kg, lpcc.tw_return_c), label
    assert (b.p_bara, b.t_c, b.m_kg, b.level_pct) == (lpcc.p_bara, lpcc.t_c, lpcc.m_kg,
                                                      a["LI"]), label
    assert (s.tlag["S_323901"], s.tlag["R3232_TW_SUP"]) == (
        lpcc.lag_state[lp.SPEED_LAG_KEY], lpcc.lag_state[lp.TW_SUPPLY_LAG_KEY]), label
    for v1c, loop in ((s.PIC_323202, pic), (s.LIC_323502, lic), (s.SIC_323901, sic),
                      (s.TIC_323013, tic)):
        assert (v1c["op"], v1c["sp"], v1c["pv"], v1c["pv1"], v1c["pv2"], v1c["mode"]) == (
            loop.op, loop.sp, loop.pv, loop.pv1, loop.pv2, loop.mode), (label, loop.tag)


#: V1's own PIC-323202 tuning, 5.0 %/bar and 40 s (`main.py` 6888-6892), which no source gives.
V1_PIC_323202_KC, V1_PIC_323202_TI_S = 5.0, 40.0

#: V1's own LIC-323502 tuning, 1.5 rpm per per cent and 300 s (`main.py` 6899-6903); the port runs
#: the plant DCS's 1.2 on SIC-323901's span and 400 s (read back 2026-10-13).
V1_LIC_323502_KC, V1_LIC_323502_TI_S = 1.5, 300.0


def _loops(v1_gain: bool = True):
    """The port's four controllers. With `v1_gain`, PIC-323202 runs V1's tuning in place of the
    decided 20 %/bar and 100 s (B-32) and LIC-323502 V1's in place of the plant DCS's 1.74 rpm
    per per cent and 400 s, so the rest of the unit can be compared tick for tick."""
    pic, lic = lp.pic_323202(), lp.lic_323502()
    if v1_gain:
        pic.Kc, pic.Ti = V1_PIC_323202_KC, V1_PIC_323202_TI_S
        lic.Kc, lic.Ti = V1_LIC_323502_KC, V1_LIC_323502_TI_S
    return pic, lic, lp.sic_323901(), lp.tic_323013()


# --------------------------------------------------------------------------------------
# The design basis
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("ours, theirs", [
    ("E003_M305_DES_KGH", "R3232_E003_M305_DES"), ("E003_M718B_DES_KGH", "R3232_E003_M718B_DES"),
    ("E003_M776_DES_KGH", "R3232_E003_M776_DES"), ("E003_M776_DES_KGH", "R328_D001_M776_DES"),
    ("E003_M797_DES_KGH", "R3232_M797_DES"), ("E003_T797_C", "R3232_M797_T"),
    ("E003_IN_DES_KGH", "R3232_E003_IN_DES"), ("E003_PHI321", "R3232_E003_PHI321"),
    ("E003_M321_DES_KGH", "R3232_E003_M321_DES"), ("E003_M308_DES_KGH", "R3232_E003_M308_DES"),
    ("E003_M_COND_DES_KGH", "R3232_E003_M_COND_DES"), ("E003_T_C", "R3232_E003_T"),
    ("TW_T_C", "R3232_TW_T"), ("E003_T305_C", "R3232_E003_T305"), ("E003_T776_C", "R328_D001_T"),
    ("E003_T718B_C", "R3232_E011_T"), ("TW_SUP_T_C", "R3232_TW_SUP_T"),
    ("TW_RET_T_C", "R3232_TW_RET_T"), ("TV13_DES_PCT", "R3232_TV13_DES_PCT"),
    ("TW_TAU_S", "R3232_TW_TAU_S"), ("D001_P_BARA", "R3232_D001_P_BARA"),
    ("D001_M_FULL_KG", "R3232_D001_M_FULL"),
    ("D001_LVL_SP_PCT", "R3232_D001_LVL_SP"), ("D001_M_DES_KG", "R3232_D001_M_DES"),
    ("E003_Q_DES_KW", "R3232_E003_Q_DES_KW"), ("E003_UA_KW", "R3232_E003_UA_KW"),
    ("D001_VOL_M3", "R3232_ENV_GAS_V_M3"), ("ENV_GAS_RHO_DES_KGM3", "R3232_ENV_GAS_RHO_DES"),
    ("ENV_GAS_C_KG_BAR", "R3232_ENV_GAS_C_KG_BAR"), ("TSAT_E003_DES_C", "_R3232_TSAT_E003_DES"),
    ("E003_SENS_KW", "R3232_E003_SENS"), ("E003_LAMC_KJKG", "R3232_E003_LAMC"),
    ("P001_RPM_DES", "R3232_P001_RPM_DES"),
])
def test_design_basis(v1, ours, theirs):
    assert getattr(e3, ours) == v1[theirs]


@pytest.mark.parametrize("stroke, p, p_e011", [
    (25.0, 3.2, 1.13), (50.0, 3.2, 1.13), (0.0, 3.2, 1.13), (25.0, 3.5, 1.13),
    (25.0, 1.0, 1.13), (25.0, 1.13, 1.13), (100.0, 4.1, 0.1), (10.0, 3.0, 1.8),
])
def test_pv_323202s_law(v1, stroke, p, p_e011):
    """V1's line, anchored on the decided design stroke (decision 150)."""
    g = v1
    theirs = (g["R3232_E003_M321_DES"] * (stroke / DECIDED_PV202_OP)
              * math.sqrt(max(p - p_e011, 0.0) / (g["R3232_D001_P_BARA"]
                                                  - g["R3232_E011_P_BARA"])))
    assert lp.vent_valve_kgh(stroke, p, p_e011) == pytest.approx(theirs, rel=1e-14)


def test_pv_323202_on_fishers_sheet_decided(v1):
    """Decision 150: V1 anchors PV-323202's linear line at 25 %; Fisher's sheet (item 021, the
    loop summary P 323202's cases, tagged TV-323013) puts the design at 36.45 %, where the rated
    Cv 99.1 passes PFD 321 on the normal case. The trim is linear on both sides, so only the anchor
    moves: at design both pass PFD 321, and wide open the port passes 2.74 times it where V1's 4.0."""
    assert v1["R3232_E003_PV_OP_DES"] == 25.0
    assert e3.E003_PV_OP_DES_PCT == pytest.approx(DECIDED_PV202_OP, rel=1e-12)
    assert DECIDED_PV202_OP == pytest.approx(36.446, abs=1e-3)
    p, p11 = e3.D001_P_BARA, e.E011_P_BARA
    assert lp.vent_valve_kgh(e3.E003_PV_OP_DES_PCT, p, p11) == pytest.approx(
        e3.E003_M321_DES_KGH, rel=1e-12)
    assert lp.vent_valve_kgh(100.0, p, p11) / e3.E003_M321_DES_KGH == pytest.approx(2.744,
                                                                                    abs=1e-3)


@pytest.mark.parametrize("stroke", [0.0, 12.5, 50.0, 77.7, 100.0, -20.0, 400.0])
def test_the_tempered_water_supply(v1, stroke):
    g = v1
    RET, SUP = g["R3232_TW_RET_T"], g["R3232_TW_SUP_T"]
    assert lp.tempered_water_supply_ss_c(stroke) == g["clamp"](
        RET - (RET - SUP) * (stroke / max(g["R3232_TV13_DES_PCT"], 1e-6)), 20.0, RET)


@pytest.mark.parametrize("p, t_tw", [(3.2, 60.0), (2.725, 50.0), (3.84, 65.0), (0.1, 20.0),
                                     (1.0, 120.0), (6.0, 45.0)])
def test_the_dew_point_and_the_capacity(v1, p, t_tw):
    g = v1
    t_dew = g["R3232_E003_T"] + (g["tsat_steam"](p) - g["_R3232_TSAT_E003_DES"])
    assert lp.dew_point_c(p) == t_dew
    assert lp.condensation_capacity_kgh(t_dew, t_tw) == (
        g["R3232_E003_M_COND_DES"] * max(t_dew - t_tw, 0.0)
        / (g["R3232_E003_T"] - g["R3232_TW_T"]))


def test_the_state_and_controllers_are_seeded_as_v1_seeds_them(v1):
    """Every seed V1's, but PIC-323202's tuning: V1's 5.0 %/bar and 40 s, the port's 20 %/bar
    and 100 s, the table's 1.00 on PT-323202's 5 bar span (B-32). TIC-323013's rescaled gain
    is the table's own, V1's number, and so is SIC-323901's, whose measured speed and output
    are both carried in rpm on ST-323901's 0-145 rpm span."""
    s = _v1_state(v1)
    pic, lic, sic, tic = _loops(v1_gain=False)
    assert (s.PIC_323202["Kc"], s.PIC_323202["Ti"]) == (V1_PIC_323202_KC, V1_PIC_323202_TI_S)
    assert (pic.Kc, pic.Ti) == (20.0, 100.0)
    assert (s.LIC_323502["Kc"], s.LIC_323502["Ti"]) == (V1_LIC_323502_KC, V1_LIC_323502_TI_S)
    assert (lic.Kc, lic.Ti) == (pytest.approx(1.74, rel=1e-12), 400.0)
    assert lic.Kc == e3.LIC_323502_KC_TABLE * e3.ST_323901_SPAN_RPM / 100.0
    assert tic.Kc == s.TIC_323013["Kc"] == e3.TIC_323013_KC_TABLE * 100.0 / e3.TT_323013_SPAN_C
    assert sic.Kc == s.SIC_323901["Kc"] == e3.SIC_323901_KC_TABLE
    assert e3.ST_323901_SPAN_RPM == 145.0
    for v1c, loop in ((s.PIC_323202, pic), (s.LIC_323502, lic), (s.SIC_323901, sic),
                      (s.TIC_323013, tic)):
        kc, ti = (loop.Kc, loop.Ti) if loop in (pic, lic) else (v1c["Kc"], v1c["Ti"])
        assert (v1c["mode"], v1c["op"], v1c["sp"], v1c["pv"], v1c["pv1"], v1c["pv2"],
                kc, ti, v1c["Td"], v1c["act"], v1c["op_lo"], v1c["op_hi"],
                v1c["sp_lo"], v1c["sp_hi"]) == (
            loop.mode, loop.op, loop.sp, loop.pv, loop.pv1, loop.pv2, loop.Kc, loop.Ti,
            loop.Td, loop.act, loop.op_lo, loop.op_hi, loop.sp_lo, loop.sp_hi), loop.tag
    lpcc = lp.LpCarbamateCondenser()
    assert (s.r3232_d001_M, s.r3232_e003_T, s.r3232_d001_P) == (lpcc.m_kg, lpcc.t_c,
                                                                lpcc.p_bara)
    assert lpcc.tw_return_c == v1["R3232_TW_RET_T"] and "R3232_TW_RET" not in s.tlag


# --------------------------------------------------------------------------------------
# The condenser on its own, tick by tick
# --------------------------------------------------------------------------------------

M305, FLASH, POOL = e3.E003_M305_DES_KGH, d.M_FLASH_GAS_DES_KGH, d.M_POOL_VAP_DES_KGH


def _design(**over):
    base = {"m305": M305, "flash": FLASH, "pool": POOL, "b322501": 0.0, "b323501": 0.0,
            "m718b": e3.E003_M718B_DES_KGH, "m776": e3.E003_M776_DES_KGH,
            "p_e011": e.E011_P_BARA}
    base.update(over)
    return base


def _gas(f: float, **over):
    return _design(m305=M305 * f, flash=FLASH * f, pool=POOL * f, **over)


def _run(v1, script, ticks: int, dt: float = DT, before=None, v1_gain: bool = True):
    """Drive the condenser alone through `script(k)`, comparing everything every tick with V1's
    stage 8 on the decided relations (B-34, B-35)."""
    s = _v1_state(v1)
    lpcc, loops = lp.LpCarbamateCondenser(), _loops(v1_gain)
    if before:
        before(s, lpcc, loops)
    b = None
    for k in range(ticks):
        x = script(k)
        s.r3232_e011_P = x["p_e011"]
        a = _v1_stage8(v1, s, x["m305"], x["m718b"], x["m776"], x["flash"], x["pool"],
                       x["b322501"], x["b323501"], dt)
        b = lpcc.step(*loops, x["m305"], x["flash"], x["pool"], x["b322501"], x["b323501"],
                      x["m718b"], x["m776"], x["p_e011"], dt)
        _assert_tick(a, b, s, lpcc, loops, f"tick {k}")
    return s, lpcc, loops, b


SCENARIOS = {
    "design hold": (lambda k: _design(), 600, DT),
    "the gas up 10 %": (lambda k: _gas(1.1 if k >= 10 else 1.0), 2400, 0.5),
    "the gas down 30 % (the capacity outruns the gas)": (
        lambda k: _gas(0.7 if k >= 10 else 1.0), 2400, 0.5),
    "the gas gone": (lambda k: _gas(0.0 if k >= 10 else 1.0), 1200, 0.5),
    "718B cut to half": (
        lambda k: _design(m718b=e3.E003_M718B_DES_KGH * (0.5 if k >= 10 else 1.0)), 1200, 0.5),
    "776 up 20 %": (
        lambda k: _design(m776=e3.E003_M776_DES_KGH * (1.2 if k >= 10 else 1.0)), 1200, 0.5),
    "LV-322501 blowing stripper gas into the column": (
        lambda k: _design(b322501=(2000.0 if 10 <= k < 400 else 0.0)), 1200, 0.5),
    "LV-323501 blowing column gas to 323F004": (
        lambda k: _design(b323501=(1500.0 if 10 <= k < 400 else 0.0)), 1200, 0.5),
    "the 323E011 node up to 1.8 bar a": (
        lambda k: _design(p_e011=(1.8 if k >= 10 else e.E011_P_BARA)), 1200, 0.5),
    "the 323E011 node above this one": (
        lambda k: _design(p_e011=(3.5 if 10 <= k < 200 else e.E011_P_BARA)), 800, 0.5),
}


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_the_condenser_tick_by_tick(v1, name):
    script, ticks, dt = SCENARIOS[name]
    _run(v1, script, ticks, dt)


def _manual(v1c: dict, loop, op: float):
    v1c["mode"] = "MAN"
    v1c["op"] = op
    loop.set_mode("MAN")
    loop.op = op


def _tic_sp(tic_sp: float):
    def before(s, lpcc, loops):
        s.TIC_323013["mode"] = "AUTO"
        loops[3].set_mode("AUTO")
        s.TIC_323013["sp"] = loops[3].sp = tic_sp
    return before


@pytest.mark.parametrize("tic_sp", [45.0, 65.0])
def test_tic_323013_on_a_new_supply_set_point(v1, tic_sp):
    """45 C: the capacity outruns the gas, PIC-323202 shuts PV-323202, and the condenser draws
    the node down until the capacity meets the load (B-34, decided). 65 C: the dew point
    carries the node up and PV-323202 opens fully. Both sides take every branch on the same
    ticks."""
    s, lpcc, loops, b = _run(v1, lambda k: _design(), 3600, 1.0, before=_tic_sp(tic_sp))
    if tic_sp == 45.0:
        assert (b.pic_op_pct, b.m_321_kgh) == (0.0, 0.0)
        assert b.env_cond_kgh == pytest.approx(b.env_in_kgh, abs=0.2)
        assert b.p_bara == pytest.approx(2.458, abs=1e-3)
    else:
        assert b.pic_op_pct == 100.0 and b.p_bara > 3.8


def test_tic_323013_in_manual(v1):
    def before(s, lpcc, loops):
        _manual(s.TIC_323013, loops[3], 80.0)
    _run(v1, lambda k: _design(), 1800, 1.0, before=before)


def test_pv_323202_held_in_manual(v1):
    def before(s, lpcc, loops):
        _manual(s.PIC_323202, loops[0], 50.0)
    _run(v1, lambda k: _design(), 1800, 1.0, before=before)


def test_pic_323202_on_a_new_set_point(v1):
    def before(s, lpcc, loops):
        s.PIC_323202["sp"] = loops[0].sp = 3.5
    _run(v1, lambda k: _design(), 1800, 1.0, before=before)


def test_lic_323502_in_manual_slows_the_pump(v1):
    def before(s, lpcc, loops):
        _manual(s.LIC_323502, loops[1], 40.0)
    s, lpcc, loops, b = _run(v1, lambda k: _design(), 1200, 1.0, before=before)
    assert b.level_pct > e3.D001_LVL_SP_PCT


def _sic_man(s, lpcc, loops):
    _manual(s.SIC_323901, loops[2], 100.0)


def test_the_pump_runs_the_tank_to_its_heel(v1):
    """SIC-323901 in MAN at 100 rpm draws 61 t/h against 38 t/h arriving: the tank reaches its
    1 kg heel and 323P001 loses suction, held at what arrives (B-35, decided). Both sides take
    the heel on the same ticks."""
    s, lpcc, loops, b = _run(v1, lambda k: _design(), 1500, 1.0, before=_sic_man)
    assert b.m_kg == e3.D001_M_FLOOR_KG and b.suction_lost
    assert b.m_308_kgh == b.in_kgh - b.m_321_kgh


# --------------------------------------------------------------------------------------
# The decided divergence (2026-09-27): PIC-323202 on its transmitter's span
# --------------------------------------------------------------------------------------

def test_the_decided_tuning_is_inert_on_the_set_point(v1):
    """B-32. With the node on its set point PIC-323202's error is zero whatever its tuning."""
    _run(v1, lambda k: _design(), 600, v1_gain=False)


def test_pv_323202_on_fishers_anchor_decided_divergence(v1):
    """Decision 150, both sides, PIC-323202 on V1's 5.0 %/bar and 40 s on both so the valve is the
    only difference: V1's vent linear from 25 %, the port's from Fisher's 36.45 %. Both pass PFD
    321 on the seed tick, the strokes differing. The gas up 10 %: an hour on, V1's node holds
    3.2340 bar a with the vent at 62.45 % passing 3332 kg/h; the port's, whose vent passes less
    per per cent of stroke, holds 3.2554 with it at 82.19 % passing 3023 — the dew point
    condensing the rest."""
    s = _v1_state(v1, vent=False)
    lpcc, loops = lp.LpCarbamateCondenser(), _loops(v1_gain=True)
    for k in range(7200):
        x = _gas(1.1 if k >= 10 else 1.0)
        s.r3232_e011_P = x["p_e011"]
        a = _v1_stage8(v1, s, x["m305"], x["m718b"], x["m776"], x["flash"], x["pool"],
                       x["b322501"], x["b323501"], 0.5, vent=False)
        b = lpcc.step(*loops, x["m305"], x["flash"], x["pool"], x["b322501"], x["b323501"],
                      x["m718b"], x["m776"], x["p_e011"], 0.5)
        if k == 0:
            assert a["m321"] == b.m_321_kgh == pytest.approx(e3.E003_M321_DES_KGH, rel=1e-12)
            assert (a["pic"], b.pic_op_pct) == (25.0, pytest.approx(DECIDED_PV202_OP, rel=1e-12))
    assert (s.r3232_d001_P, lpcc.p_bara) == (pytest.approx(3.2340, abs=1e-4),
                                             pytest.approx(3.2554, abs=1e-4))
    assert (a["pic"], b.pic_op_pct) == (pytest.approx(62.45, abs=0.01),
                                        pytest.approx(82.19, abs=0.01))
    assert (a["m321"], b.m_321_kgh) == (pytest.approx(3331.6, abs=0.1),
                                        pytest.approx(3023.2, abs=0.1))


def test_pic_323202_on_its_transmitter_span_decided_divergence(v1):
    """B-32. The gas up 10 %: bit-exact until PIC-323202 first sees the node off its set point,
    then V1's 5.0 %/bar and 40 s and the port's 20 %/bar and 100 s part. An hour on, the dew
    point holds both near 3.2 bar a — the condenser, not the vent, sets this node — and the
    port's vent has taken more of the excess."""
    s = _v1_state(v1)
    lpcc, loops = lp.LpCarbamateCondenser(), _loops(v1_gain=False)
    parted = None
    for k in range(7200):
        x = _gas(1.1 if k >= 10 else 1.0)
        s.r3232_e011_P = x["p_e011"]
        a = _v1_stage8(v1, s, x["m305"], x["m718b"], x["m776"], x["flash"], x["pool"],
                       x["b322501"], x["b323501"], 0.5)
        b = lpcc.step(*loops, x["m305"], x["flash"], x["pool"], x["b322501"], x["b323501"],
                      x["m718b"], x["m776"], x["p_e011"], 0.5)
        if parted is None and a["pic"] != b.pic_op_pct:
            parted = k
        if parted is None:
            _assert_tick(a, b, s, lpcc, loops, f"tick {k}")
    assert parted == 11
    assert s.r3232_d001_P == pytest.approx(3.2554, abs=1e-4)
    assert lpcc.p_bara == pytest.approx(3.2298, abs=1e-4)
    assert b.m_321_kgh > a["m321"]


# --------------------------------------------------------------------------------------
# The decided divergences (2026-09-27): the uncapped capacity and 323P001's heel
# --------------------------------------------------------------------------------------

def _diverge(v1, script, ticks: int, dt: float, before, limit_reached):
    """V1's own stage 8 (``decided=False``) against the port: bit-exact until
    `limit_reached(k, a, b)` first holds, then both driven on and every later tick handed back
    as (V1 result, V1 holdup before and after, the port's holdup before, port result)."""
    s = _v1_state(v1)
    lpcc, loops = lp.LpCarbamateCondenser(), _loops()
    if before:
        before(s, lpcc, loops)
    after, parted = [], None
    for k in range(ticks):
        x = script(k)
        s.r3232_e011_P = x["p_e011"]
        m_v1_pre, m_pre = s.r3232_d001_M, lpcc.m_kg
        a = _v1_stage8(v1, s, x["m305"], x["m718b"], x["m776"], x["flash"], x["pool"],
                       x["b322501"], x["b323501"], dt, decided=False)
        b = lpcc.step(*loops, x["m305"], x["flash"], x["pool"], x["b322501"], x["b323501"],
                      x["m718b"], x["m776"], x["p_e011"], dt)
        if parted is None and limit_reached(k, a, b):
            parted = k
        if parted is None:
            _assert_tick(a, b, s, lpcc, loops, f"tick {k}")
        else:
            after.append((a, m_v1_pre, s.r3232_d001_M, m_pre, b))
    assert after, "the limit was never reached"
    return s, lpcc, loops, parted, after


UNCAPPED = {
    "TIC-323013 at 45 C": (lambda k: _design(), 3600, 1.0, _tic_sp(45.0)),
    "the gas down 30 %": (lambda k: _gas(0.7 if k >= 10 else 1.0), 2400, 0.5, None),
    "the gas gone": (lambda k: _gas(0.0 if k >= 10 else 1.0), 1200, 0.5, None),
}


@pytest.mark.parametrize("name", list(UNCAPPED))
def test_the_uncapped_condensation_decided_divergence(v1, name):
    """B-34. Bit-exact until V1's capacity first outruns the gas that arrives, where V1 caps it
    and the port does not. Under surplus cooling V1's node then stands still once PV-323202 has
    shut, at 2.658 bar a with 4623 kg/h of capacity unused an hour on; the port's falls to
    2.458, where the capacity meets the load. After a cut in the gas the two meet again: V1's
    node creeps back as the water warms, to the port's 2.797 bar a (30 % down) and 1.867
    (gone)."""
    script, ticks, dt, before = UNCAPPED[name]
    s, lpcc, loops, parted, after = _diverge(v1, script, ticks, dt, before,
                                             lambda k, a, b: a["cap"] > a["env_in"])
    # On the tick they part V1 condenses the gas that arrives, the port its capacity.
    a0, _, _, _, b0 = after[0]
    assert a0["env_cond"] == a0["env_in"] < a0["cap"] == b0.capacity_kgh == b0.env_cond_kgh
    a, _, _, _, b = after[-1]
    if name == "TIC-323013 at 45 C":
        assert parted == 796
        assert (a["pic"], b.pic_op_pct) == (0.0, 0.0)
        assert s.r3232_d001_P == pytest.approx(2.6577, abs=1e-4)
        assert a["cap"] - a["env_in"] == pytest.approx(4623.2, abs=0.1)
        assert lpcc.p_bara == pytest.approx(2.4576, abs=1e-4)
        assert b.capacity_kgh == pytest.approx(b.env_in_kgh, abs=0.2)
    else:
        assert parted == 10
        assert lpcc.p_bara == pytest.approx(s.r3232_d001_P, abs=1e-4)
        assert lpcc.p_bara == pytest.approx(2.7968 if name == "the gas down 30 %" else 1.8672,
                                            abs=1e-4)


def test_the_pump_at_the_heel_decided_divergence(v1):
    """B-35. SIC-323901 in MAN at 100 rpm: bit-exact until the tick 323P001 reaches the tank's
    heel, in the 989th second. On it V1 draws its full 61.5 t/h, the holdup goes below the 1 kg
    floor and the floor makes up 6.2 kg; the port delivers the liquid above the heel and what
    arrives, flags the loss of suction and makes up nothing. From then on both hold the pump at
    what arrives."""
    s, lpcc, loops, parted, after = _diverge(v1, lambda k: _design(), 1500, 1.0, _sic_man,
                                             lambda k, a, b: b.suction_lost)
    assert parted == 988
    a, v1_pre, v1_post, m_pre, b = after[0]
    assert v1_post - v1_pre - (a["in"] - a["m321"] - a["m308"]) / 3600.0 == pytest.approx(
        6.16, abs=0.01)
    assert a["m308"] == e3.E003_M308_DES_KGH * (100.0 / e3.P001_RPM_DES) > b.m_308_kgh
    assert abs(b.m_kg - m_pre - (b.in_kgh - b.m_321_kgh - b.m_308_kgh) / 3600.0) < 1e-9
    for a, v1_pre, v1_post, m_pre, b in after[1:]:
        assert v1_post == v1_pre == e3.D001_M_FLOOR_KG and b.suction_lost
        assert b.m_308_kgh == pytest.approx(a["m308"], rel=1e-12)


# --------------------------------------------------------------------------------------
# Coupled: 323C003 rides the node one tick later; 323E011 takes 321 and returns 718B
# --------------------------------------------------------------------------------------

def test_the_column_rides_the_lpcc_node(v1):
    """V1's stage 1 into V1's stage 8 against the ported 323C003 into the ported LPCC: the
    column reads the node of the tick before, and the node takes the column's overhead and its
    two sources on the tick."""
    s = _v1_state(v1)
    col = rc.RectifyingColumn(chest=rc.V1_CHEST)
    loops1 = (rc.tic_323007(), rc.pic_329202(rc.V1_CHEST), rc.lic_323501())
    lpcc, loops8 = lp.LpCarbamateCondenser(), _loops()
    for k in range(1500):
        drain = FEED_DES * (0.85 if k >= 20 else 1.0)
        a1 = stage1._v1_stage1(v1, s, drain, 119.0, stage1.BOTTOMS_PCT, DT)
        a8 = _v1_stage8(v1, s, a1["m305"], e3.E003_M718B_DES_KGH, e3.E003_M776_DES_KGH,
                        a1["flash"], a1["pool"], 0.0, a1["blow"], DT)
        b1 = col.step(*loops1, drain, 119.0, stage1.BOTTOMS_PCT, 172.0, P_LP_BARA,
                      d.F004_P_BARA, lpcc.p_bara, DT)
        b8 = lpcc.step(*loops8, b1.m_305_kgh, b1.m_flash_gas_kgh, b1.m_heater_gas_kgh, 0.0,
                       b1.blowthrough_kgh, e3.E003_M718B_DES_KGH, e3.E003_M776_DES_KGH,
                       e.E011_P_BARA, DT)
        stage1._assert_tick(a1, b1, s, col, loops1, f"stage 1, tick {k}")
        _assert_tick(a8, b8, s, lpcc, loops8, f"stage 8, tick {k}")
    assert lpcc.p_bara < e3.D001_P_BARA and col.p_bara < d.C003_P_BARA


def test_the_two_lp_condensers_through_321_and_718b(v1):
    """V1's stage 8 into V1's stage 9 against the ported pair: 323E011 takes PV-323202's vent on
    the tick and vents against its own node; 323E003 takes 718B on the next tick — V1's
    ``R3232_718B`` tear, seeded with the design flow."""
    s = _v1_state(v1)
    lpcc, loops8 = lp.LpCarbamateCondenser(), _loops()
    cond, loops9 = fc.FlashCondenser(**fc.V1_CONDENSER), stage9._loops()
    m718b_prev = e3.E003_M718B_DES_KGH
    for k in range(3000):
        x = _gas(1.1 if k >= 10 else 1.0)
        v1_718b_prev = s.tlag.get("R3232_718B", v1["R3232_M718B_DES"])
        a8 = _v1_stage8(v1, s, x["m305"], v1_718b_prev, x["m776"], x["flash"], x["pool"],
                        0.0, 0.0, DT)
        a9 = stage9._v1_stage9(v1, s, e.E011_M701_DES_KGH, 0.0, 0.0, e.E011_M786_DES_KGH,
                               a8["m321"], e.E011_M402_DES_KGH, DT)
        s.tlag["R3232_718B"] = a9["718B"]
        b8 = lpcc.step(*loops8, x["m305"], x["flash"], x["pool"], 0.0, 0.0, m718b_prev,
                       x["m776"], cond.p_bara, DT)
        b9 = cond.step(*loops9, e.E011_M701_DES_KGH, 0.0, 0.0, e.E011_M786_DES_KGH,
                       b8.m_321_kgh, e.E011_M402_DES_KGH, DT)
        m718b_prev = b9.m_718b_kgh
        _assert_tick(a8, b8, s, lpcc, loops8, f"stage 8, tick {k}")
        stage9._assert_tick(a9, b9, s, cond, loops9, f"stage 9, tick {k}")
    assert cond.p_bara > e.E011_P_BARA and b8.m_321_kgh > e3.E003_M321_DES_KGH


def test_the_recirculation_end_to_end_through_a_stripper_feed_cut(v1):
    """V1's stages 1 to 4, 8 and 9 against the ported 323C003 -> 323F004 -> 323F010 -> 323D002
    with 323E003 / 323D001 closing the column's node and 323E011 / 323D011 the flash gas node:
    the column rides the LPCC, the drum rides 323E011, 321 crosses on the tick and 718B on the
    next."""
    s = _v1_state(v1)
    col = rc.RectifyingColumn(chest=rc.V1_CHEST)
    loops1 = (rc.tic_323007(), rc.pic_329202(rc.V1_CHEST), rc.lic_323501())
    drum, lic5 = ft.FlashTank(**ft.V1_DRUM), ft.lic_323505()
    sep, tic, pic = pe.PreEvaporator(chest=pe.V1_CHEST, vent=pe.V1_VENT, live_bubble=False, own_head_leg=False), pe.tic_323012(), pe.pic_329208(pe.V1_CHEST)
    tank, lic, fic = st.SolutionTank(backward_species=False), st.lic_323507(), st.fic_324401()
    lpcc, loops8 = lp.LpCarbamateCondenser(), _loops()
    cond, loops9 = fc.FlashCondenser(**fc.V1_CONDENSER), stage9._loops()
    m718b_prev = e3.E003_M718B_DES_KGH
    for k in range(800):
        drain = FEED_DES * (0.85 if k >= 20 else 1.0)
        s.tlag["R324_recyc"], s.tlag["R324_recyc_T"], s.tlag["R324_recyc_comp"] = stage4.NO_RECYCLE
        v1_718b_prev = s.tlag.get("R3232_718B", v1["R3232_M718B_DES"])
        a1 = stage1._v1_stage1(v1, s, drain, 119.0, stage1.BOTTOMS_PCT, DT)
        a2 = stage2._v1_stage2(v1, s, a1["m314"], a1["dep314"][0], a1["dep314"][1], DT)
        a3 = stage3._v1_stage3(v1, s, a2["m319"], a2["dep319"][0], a2["dep319"][1], a2["blow"],
                               DT)
        a4 = stage4._v1_stage4(v1, s, a3["m317"], a3["dep317"][0], a3["dep317"][1], DT)
        a8 = _v1_stage8(v1, s, a1["m305"], v1_718b_prev, e3.E003_M776_DES_KGH, a1["flash"],
                        a1["pool"], 0.0, a1["blow"], DT)
        a9 = stage9._v1_stage9(v1, s, a2["m701"], a2["blow"][0], a1["blow"],
                               e.E011_M786_DES_KGH, a8["m321"], e.E011_M402_DES_KGH, DT)
        s.tlag["R3232_718B"] = a9["718B"]
        p_d001, p_e011 = lpcc.p_bara, cond.p_bara
        b1 = col.step(*loops1, drain, 119.0, stage1.BOTTOMS_PCT, 172.0, P_LP_BARA,
                      drum.p_bara, p_d001, DT)
        b2 = drum.step(lic5, b1.m_314_kgh, b1.drain_t_c, b1.drain_w, p_e011, sep.p_bara, DT)
        b3 = sep.step(tic, pic, b2.m_319_kgh, b2.drain_t_c, b2.drain_w, b2.blowthrough_kgh,
                      b2.blowthrough_kmolh, b2.blowthrough_y, d.HIC_323605_DES_PCT_V1, P_LP_BARA,
                      d.P_324E002_DES_BARA, DT)
        b4 = tank.step(lic, fic, b3.m_317_kgh, b3.drain_t_c, b3.drain_w, *stage4.NO_RECYCLE,
                       False, DT)
        b8 = lpcc.step(*loops8, b1.m_305_kgh, b1.m_flash_gas_kgh, b1.m_heater_gas_kgh, 0.0,
                       b1.blowthrough_kgh, m718b_prev, e3.E003_M776_DES_KGH, p_e011, DT)
        b9 = cond.step(*loops9, b2.m_701_kgh, b2.blowthrough_kgh, b1.blowthrough_kgh,
                       e.E011_M786_DES_KGH, b8.m_321_kgh, e.E011_M402_DES_KGH, DT)
        m718b_prev = b9.m_718b_kgh
        stage1._assert_tick(a1, b1, s, col, loops1, f"stage 1, tick {k}")
        stage2._assert_tick(a2, b2, s, drum, lic5, f"stage 2, tick {k}")
        stage3._assert_tick(a3, b3, s, sep, tic, pic, f"stage 3, tick {k}")
        stage4._assert_tick(a4, b4, s, tank, lic, fic, f"stage 4, tick {k}")
        _assert_tick(a8, b8, s, lpcc, loops8, f"stage 8, tick {k}")
        stage9._assert_tick(a9, b9, s, cond, loops9, f"stage 9, tick {k}")
    assert lpcc.p_bara < e3.D001_P_BARA and cond.p_bara < e.E011_P_BARA


def test_pfd_734_decided_divergence(v1):
    """B-37 and B-94, decided 2026-10-10 and 2026-10-14: V1's 323E003 takes no PFD 734; the port's
    takes FIC-323401's ammonia water as its departure from the PFD's 1534 kg/h, which the PFD's
    323E003 balance closes without. At the design flow the port is V1's on every tick; at 2000
    kg/h, after half an hour, 323P001 returns 37 292.0 kg/h against V1's 36 835.2 and the tank
    closes on the five inlets, so the ammonia water reaches the synthesis instead of leaving the
    plant."""
    s = _v1_state(v1)
    lpcc, loops = lp.LpCarbamateCondenser(), _loops()
    x = _design()
    for k in range(600):
        s.r3232_e011_P = x["p_e011"]
        a = _v1_stage8(v1, s, x["m305"], x["m718b"], x["m776"], x["flash"], x["pool"],
                       x["b322501"], x["b323501"], 1.0)
        b = lpcc.step(*loops, x["m305"], x["flash"], x["pool"], x["b322501"], x["b323501"],
                      x["m718b"], x["m776"], x["p_e011"], 1.0, m_734_kgh=1534.0)
        _assert_tick(a, b, s, lpcc, loops, f"PFD 734 at design, tick {k}")
    s = _v1_state(v1)
    lpcc, loops = lp.LpCarbamateCondenser(), _loops()
    for _ in range(1800):
        s.r3232_e011_P = x["p_e011"]
        m_pre = lpcc.m_kg
        a = _v1_stage8(v1, s, x["m305"], x["m718b"], x["m776"], x["flash"], x["pool"],
                       x["b322501"], x["b323501"], 1.0)
        b = lpcc.step(*loops, x["m305"], x["flash"], x["pool"], x["b322501"], x["b323501"],
                      x["m718b"], x["m776"], x["p_e011"], 1.0, m_734_kgh=2000.0)
        assert lpcc.m_kg - m_pre == pytest.approx(
            (b.in_kgh - b.m_321_kgh - b.m_308_kgh) / 3600.0, abs=1e-9)
    assert a["m308"] == pytest.approx(e3.E003_M308_DES_KGH, rel=1e-12)
    assert s.r3232_d001_M == pytest.approx(e3.D001_M_DES_KG, rel=1e-12)
    assert b.m_308_kgh == pytest.approx(37292.0, abs=0.1)
    assert b.in_kgh - a["in"] == pytest.approx(466.0, abs=1e-6)


#: B-31's producers on their designs — 323C003's, 323E011's, 328D001's and 322C001's — and the
#: same five kelvin hot.
B31_DES = {"t_c003_c": d.C003_T_SP_C, "t_e011_c": e.E011_T_C, "t_d001_c": D001_T_C,
           "t_c001_c": C001_T_C}
B31_HOT = {k: v + 5.0 for k, v in B31_DES.items()}


def test_the_inlets_at_their_producers_temperatures_decided_divergence(v1):
    """B-31, decided 2026-10-16: 323E003 charges 305, 718B, 776 and 797 at 323C003's, 323E011's,
    328D001's and 322C001's live temperatures, each as its departure from its producer's design;
    V1 at 119, 45, 61 and 46 C whatever they do. With every producer on its design the port is
    V1's on every tick, and so it is with every producer 5 K hot on V1's switch. Live, the first
    tick parts 0.0075 K hotter; after half an hour the shell stands at 74.185 C against V1's 74 C,
    the duty at 14 136.3 kW against 14 000, the node at 3.2029 bar a and 323P001 returning
    36 800.5 kg/h against 36 835.2."""
    x = _design()
    for kw, live in ((B31_DES, True), (B31_HOT, False)):
        s = _v1_state(v1)
        lpcc, loops = lp.LpCarbamateCondenser(live_inlets=live), _loops()
        for k in range(600):
            s.r3232_e011_P = x["p_e011"]
            a = _v1_stage8(v1, s, x["m305"], x["m718b"], x["m776"], x["flash"], x["pool"],
                           x["b322501"], x["b323501"], DT)
            b = lpcc.step(*loops, x["m305"], x["flash"], x["pool"], x["b322501"],
                          x["b323501"], x["m718b"], x["m776"], x["p_e011"], DT, **kw)
            _assert_tick(a, b, s, lpcc, loops, f"live {live}, tick {k}")
    s = _v1_state(v1)
    lpcc, loops = lp.LpCarbamateCondenser(), _loops()
    for k in range(1800):
        s.r3232_e011_P = x["p_e011"]
        a = _v1_stage8(v1, s, x["m305"], x["m718b"], x["m776"], x["flash"], x["pool"],
                       x["b322501"], x["b323501"], 1.0)
        b = lpcc.step(*loops, x["m305"], x["flash"], x["pool"], x["b322501"], x["b323501"],
                      x["m718b"], x["m776"], x["p_e011"], 1.0, **B31_HOT)
        if k == 0:
            first = lpcc.t_c - s.r3232_e003_T
    assert first == pytest.approx(0.007460, abs=1e-6)
    assert (s.r3232_e003_T, s.r3232_d001_P, a["Q"]) == (74.0, 3.2, 14000.0)
    assert (lpcc.t_c, lpcc.p_bara, b.q_kw, b.m_308_kgh) == (
        pytest.approx(74.1850, abs=1e-4), pytest.approx(3.20286, abs=1e-5),
        pytest.approx(14136.3, abs=0.1), pytest.approx(36800.50, abs=0.01))
