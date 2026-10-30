"""V1 <-> V1.1 equivalence for 323E011 / 323D011, the flash condenser on the LP flash gas node.

What is being proved
--------------------
V1 writes the condenser inline in `step_sim`, so its statements are TRANSCRIBED into
`_v1_stage9` below, line for line, and declared as such (``main.py`` 9580-9663). Everything they
call is V1's own code, executed: ``_ctrl_ipd``, ``_fic_flow``, ``_lag1`` and
``_feed_transport_td_s`` lifted out of ``main.py``; ``hydraulics`` and ``c003_pressure_coupling``
loaded as real modules. The state and the three controllers are seeded inside ``State.__init__``
and are transcribed from ``main.py`` 6831-6835, 6893-6898, 6933-6937 and 6986-6990.

The condenser is driven on its own through scenarios chosen to take every branch — a gas load
above and below the condensation capacity, the vent law's floor and the node's 0.1 bar a
floor, each inlet stepped, both blow-throughs, PIC-323203 in MAN and on a new set point, the
718 split with FIC-323418 in AUTO and MAN, LIC-323503 in MAN, a drum pumped to its floor — then
coupled to V1's 323F004, which rides the node one tick later, and last through V1's stages 1 to 4
into the condenser. Every tick compares every published field, the node, the tank, both lags and
all three controllers with ``==``.

The two decided divergences (2026-09-27)
----------------------------------------
* **B-32, PIC-323203's gain.** The port runs the table's gain on PT-323203's span, 60 %/bar,
  where V1 runs 0.60 %/bar. The equation-identity scenarios above run the port's PIC-323203 at
  V1's gain, so that the rest of the unit is proved against V1 on every tick; the decided gain
  is proved on its own, against V1, in the section of decided divergences: bit-exact while the
  node sits on its set point, and then both sides asserted.
* **B-33, 323P008's heel.** Inert above the heel, so every other scenario runs it; a test in
  the same section takes the tank to its floor and asserts both sides — V1 drawing
  FIC-323418's flow and making it up at the floor, the port capped at what the tank holds.

FIC-323418's gain (handoff B-41, 2026-09-30)
--------------------------------------------
The port reads the DCS table's 1.00 per cent of FT-323418's 0-10 m3/h span, 10 %/(m3/h), where V1
runs 1.00 per kg/h, 1065 %/(m3/h). ``_v1_state(decided=True)`` seeds the port's gain into V1's
controller dict — V1's `_ctrl_ipd` runs unchanged — so every scenario compares the port with V1's
code on the port's gain (and stage 4's FIC-324401 on its own, B-41); on its set point the loop has
no error and the gain is inert. The gain itself is proved against V1 verbatim in
`test_flow_loop_gains_equivalence.py`.

LV-323503 and FV-323418 (handoff B-44, 2026-09-30)
--------------------------------------------------
The port runs both on their vendor trim from the strokes their Kvs give. The transcription
carries the switch ``valves_decided`` (default True, on the state): the two loops seeded on the
decided strokes, LIC-323503's demand through the trim, and V1's ``_fic_flow`` transcribed with
it (`decided_valves`); ``valves_decided=False`` is V1 verbatim. Both sides are asserted in
the last section of this file.

PV-323203 (decided 2026-10-17, decision 23's class)
--------------------------------------------------
The port runs it on Metso's Neldisc from its 21.64 % design stroke. ``V1_CONDENSER`` runs it on
V1's linear law from 25 % and `_loops` seeds PIC-323203 there, so every scenario compares the port
with V1's valve; both sides are asserted in `test_pv_323203_on_its_vendor_trim_decided_divergence`.

SV32357 (handoffs B-47, A-16, decided 2026-10-01)
-------------------------------------------------
The port relieves the node through SV32357 on 323D011, which V1 does not have. The transcription
carries the switch ``relief_decided`` (default True, on the state): the valve's lift and vent
written out on V1's side (`decided_relief`, on V1's own API 520 law), booked against the tank as
the vent is; ``relief_decided=False`` is V1 verbatim. Inert below 6.01 bar a; both sides are
asserted in the last section.

323F004's vapour space in the node (handoff B-51, decided 2026-10-07)
---------------------------------------------------------------------
The port integrates the node on the envelope's free volume plus 323F004's vapour space, 1.083 m3,
where V1 integrates it on the envelope alone. The transcription carries the switch
``volume_decided`` (default True, on the state): the drum's vapour space added to V1's free volume
(`_v1_stage9`); ``volume_decided=False`` is V1 verbatim. Inert while the node holds its pressure;
both sides are asserted in the last section.
"""

from __future__ import annotations

import math

import pytest

from ureasim.data import control_valves as cvd
from ureasim.data import unit_323 as d
from ureasim.data import unit_323e011 as e
from ureasim.data.desorption_train import D001_T_C
from ureasim.data.unit_323e003 import E003_T_C
from ureasim.data.unit_328d003 import D003_TII_C
from ureasim.data.design_point import R323_FEED_DES_KGH as FEED_DES
from ureasim.data.design_point import R323_M314_DES
from ureasim.data.unit_329 import P_LP_BARA
from ureasim.units.recirc import flash_condenser as fc
from ureasim.units.recirc import flash_tank as ft
from ureasim.units.recirc import pre_evaporator as pe
from ureasim.units.recirc import rectifying_column as rc
from ureasim.units.recirc import solution_tank as st
from tests.equivalence import routes_switch
from tests.equivalence import decided_relief as dr
from tests.equivalence import decided_valves as dv
from tests.equivalence import test_flash_tank_equivalence as stage2
from tests.equivalence import test_pre_evaporator_equivalence as stage3
from tests.equivalence import test_rectifying_column_equivalence as stage1
from tests.equivalence import test_solution_tank_equivalence as stage4
from tests.equivalence.v1_loader import load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

E011_NAMES = [
    "R3232_E011_IN_DES", "R3232_E011_M701_DES", "R3232_E011_M786_DES", "R3232_E011_M321_DES",
    "R3232_E011_M402_DES", "R3232_E011_MV_DES", "R3232_E011_P_BARA", "R3232_E011_PV_OP_DES",
    "R3232_D011_M718_DES", "R3232_D011_M_DES", "R3232_D011_M_TAU_S", "R3232_D011_LVL_SP",
    "R3232_LV503_OP_DES", "R3232_M718B_DES", "R3232_M718A_DES", "R3232_FIC418_OP_DES",
    "RHO_718_KGM3", "R3232_M718A_LINE_KG", "R3232_M718A_TAU_S", "R3232_E011_UA_KW",
    "R3232_E011_Q_DES_KW", "R3232_E011_T", "R3232_E011_RECON_KGH", "R3232_E011_T701",
    "R3232_E011_T786", "R3232_CP", "R3232_E011_LAMV", "R3232_E011_SENS",
    "R3232_E011_MCOND_DES", "R3232_E011_PHIV", "R3232_E011_VOL_M3", "R3232_E011_SHELL_ID_M",
    "R3232_E011_TUBE_L_M", "R3232_E011_N_TUBES", "R3232_E011_TUBE_OD_M", "R3232_D011_ID_M",
    "R3232_D011_SHELL_M", "R3232_E011_RHO_L", "R3232_E011_MW_VAP", "FEED_TD_MAX_S",
    "_fic_flow", "_feed_transport_td_s",
]
V1_NAMES = stage4.V1_NAMES + E011_NAMES

DT = 0.1

#: The decided strokes [%] (B-44): LV-323503 on the whole of PFD 718, FV-323418 on 718B.
DECIDED_LV503_OP = dv.design_stroke_pct(cvd.LV_323503, e.D011_M718_DES_KGH)
DECIDED_FIC418_OP = dv.design_stroke_pct(cvd.FV_323418, e.M718B_DES_KGH)

#: SV32357 as decided (A-16), written from its sheets: set 5.0 bar g on 1.010 bar a (Uhde
#: UD-RL-323-EC-0006), reseating 10 % of set below on gas; orifice F, 240.53 mm2 (Sempell
#: UD-RL-G00-DZ-0001-001 page 91), at Sempell's gas coefficient for the orifice, 0.922 (decision 130).
SV32357 = dr.Valve.orifice(5.0 + 1.010, 5.0 + 1.010 - 0.1 * 5.0, 240.53 * 1.0e-6, 0.922)


@pytest.fixture(scope="module")
def v1():
    ns = stage3.build_v1(V1_NAMES)
    # The isometrics' geometry (handoff A-11, decided 2026-10-07): `routes_switch`.
    ns["D002_ROUTE"] = routes_switch.decided(ns, "323F010_TO_323D002")
    ns["coupling"] = load("c003_pressure_coupling")
    return ns


def _v1_state(v1, decided: bool = True, valves_decided: bool = True,
              relief_decided: bool = True, volume_decided: bool = True):
    """The V1 plant-state fields stages 1 to 4 and 9 read and write, seeded as `State.__init__`
    seeds them (stages 1 to 4 from their own tests, the condenser from ``main.py`` 6831-6835,
    6893-6898, 6933-6937 and 6986-6990); `decided` gives FIC-323418 and FIC-324401 the port's
    gains (B-41); `valves_decided` the vendor valves' strokes (B-44); `relief_decided` SV32357
    (A-16); `volume_decided` 323F004's vapour space in the node (B-51)."""
    g = v1
    s = stage4._v1_state(v1, decided, valves_decided=valves_decided)
    s.r3232_e011_M = g["R3232_D011_M_DES"]
    s.r3232_e011_T = g["R3232_E011_T"]
    s.r3232_e011_T_prev = g["R3232_E011_T"]
    s.r3232_e011_P = g["R3232_E011_P_BARA"]
    P = g["R3232_E011_P_BARA"]
    s.PIC_323203 = {"mode": "AUTO", "op": g["R3232_E011_PV_OP_DES"],
                    "sp": P, "pv": P, "pv1": P, "pv2": P,
                    "Kc": 0.6, "Ti": 100.0, "Td": -1.0, "act": -1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.5, "sp_hi": 2.0}
    L = g["R3232_D011_LVL_SP"]
    s.LIC_323503 = {"mode": "AUTO", "op": g["R3232_LV503_OP_DES"],
                    "sp": L, "pv": L, "pv1": L, "pv2": L,
                    "Kc": 1.8, "Ti": 120.0, "Td": 0.0, "act": -1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0, "sp_hi": 100.0}
    RHO = g["RHO_718_KGM3"]
    V = g["R3232_M718B_DES"] / RHO
    s.FIC_323418 = {"mode": "AUTO", "op": g["R3232_FIC418_OP_DES"],
                    "sp": V, "pv": V, "pv1": V, "pv2": V,
                    "Kc": 1.0 * RHO, "Ti": 100.0, "Td": -1.0, "act": +1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0, "sp_hi": 8000.0 / RHO}
    if decided:
        s.FIC_323418["Kc"] = e.FIC_323418_KC
    if valves_decided:
        s.LIC_323503["op"] = DECIDED_LV503_OP
        s.FIC_323418["op"] = DECIDED_FIC418_OP
    s.valves_decided = valves_decided
    s.relief_decided = relief_decided
    s.volume_decided = volume_decided
    s.sv_32357_lifted = False
    return s


def _v1_stage9(v1, s, m_701, blow_323505_kgh, blow_323501_kgh, m_786_d001, m_321, m_402, dt):
    """V1 `main.py` 9580-9663, stage 9, TRANSCRIBED line for line; on the state's
    ``valves_decided``, LV-323503 and FV-323418 on the vendor trim (B-44); on its
    ``relief_decided``, SV32357 (A-16); on its ``volume_decided``, 323F004's vapour space in the
    node (B-51)."""
    g = v1
    hydraulics = g["hydraulics"]
    vd = s.valves_decided
    Te011 = s.r3232_e011_T
    m_701_e011 = m_701 - blow_323505_kgh + blow_323501_kgh
    in_e011 = (g["R3232_E011_IN_DES"] + (m_701_e011 - g["R3232_E011_M701_DES"])
               + (m_786_d001 - g["R3232_E011_M786_DES"])
               + (m_321 - g["R3232_E011_M321_DES"])
               + (m_402 - g["R3232_E011_M402_DES"]))
    pic203_op = g["_ctrl_ipd"](s.PIC_323203, s.r3232_e011_P, dt)
    dP_v011 = max(s.r3232_e011_P - 1.0, 0.001)
    m_v011 = (g["R3232_E011_MV_DES"] * (pic203_op / g["R3232_E011_PV_OP_DES"])
              * math.sqrt(dP_v011 / (g["R3232_E011_P_BARA"] - 1.0)))
    gen_v011 = g["coupling"].e011_vent_generation_kgh(max(in_e011 - m_402, 0.0))
    lvl_d011 = s.r3232_e011_M / g["R3232_D011_M_DES"] * g["R3232_D011_LVL_SP"]
    lic503_op = g["_ctrl_ipd"](s.LIC_323503, lvl_d011, dt)
    if vd:
        m718_dmd = g["R3232_D011_M718_DES"] * (dv.trim(lic503_op / 100.0)
                                               / dv.trim(DECIDED_LV503_OP / 100.0))
        m_718B = dv.fic_flow(g, s.FIC_323418, g["R3232_M718B_DES"], DECIDED_FIC418_OP, s.tlag,
                             "F_323418", dt, tau_s=45.0, rho=g["RHO_718_KGM3"])
    else:
        m718_dmd = g["R3232_D011_M718_DES"] * (lic503_op / g["R3232_LV503_OP_DES"])
        m_718B = g["_fic_flow"](s.FIC_323418, g["R3232_M718B_DES"], g["R3232_FIC418_OP_DES"],
                                s.tlag, "F_323418", dt, tau_s=45.0, rho=g["RHO_718_KGM3"])
    if s.FIC_323418["mode"] in ("AUTO", "CAS"):
        m718B_ff = s.FIC_323418["sp"] * g["RHO_718_KGM3"]
    else:
        m718B_ff = m_718B
    m718A_dmd = max(m718_dmd - m718B_ff, 0.0)
    _tau_718A = g["_feed_transport_td_s"](g["R3232_M718A_LINE_KG"], m718A_dmd)
    m_718A = g["_lag1"](s.tlag, "F_718A", m718A_dmd, _tau_718A, dt)
    Q_e011 = g["R3232_E011_UA_KW"] * (Te011 - 35.0)
    sens_e011 = (((max(m_701_e011, 0.0) + g["R3232_E011_RECON_KGH"])
                  * (g["R3232_E011_T701"] - Te011)
                  + m_786_d001 * (g["R3232_E011_T786"] - Te011)
                  + m_321 * (74.0 - Te011)
                  + m_402 * (56.0 - Te011)) / 3600.0 * g["R3232_CP"])
    m_cond_e011 = max(in_e011 - m_402 - m_v011, 0.0)
    P_e011 = sens_e011 + m_cond_e011 / 3600.0 * g["R3232_E011_LAMV"] - Q_e011
    _vv_e011 = hydraulics.vapour_volume_m3(g["R3232_E011_VOL_M3"], s.r3232_e011_M,
                                           g["R3232_E011_RHO_L"])
    if s.volume_decided:  # ---- B-51: 323F004's vapour space in the node (the port's line) ----
        _vv_e011 += e.F004_VAPOUR_M3
    _T_e011_pre = s.r3232_e011_T
    MW = g["R3232_E011_MW_VAP"]
    _p_free = s.r3232_e011_P + hydraulics.vessel_dpdt(
        s.r3232_e011_P, s.r3232_e011_T + 273.15, _vv_e011, MW,
        gen_v011 / MW, m_v011 / MW,
        dtdt_k_s=(s.r3232_e011_T - s.r3232_e011_T_prev) / dt,
        dvvdt_m3_s=-((in_e011 - m_v011 - m_718A - m_718B) / 3600.0) / g["R3232_E011_RHO_L"]) * dt
    relief = 0.0
    if s.relief_decided:  # ---- A-16: SV32357 (the port's lines) ----
        relief, s.sv_32357_lifted = dr.vent(
            g, SV32357, s.r3232_e011_P, _p_free, s.r3232_e011_T + 273.15, MW, _vv_e011, dt,
            s.sv_32357_lifted)
        if relief > 0.0:
            _p_free += hydraulics.vessel_dpdt(s.r3232_e011_P, s.r3232_e011_T + 273.15, _vv_e011,
                                              MW, 0.0, relief / MW) * dt
            m_cond_e011 = max(in_e011 - m_402 - m_v011 - relief, 0.0)
            P_e011 = sens_e011 + m_cond_e011 / 3600.0 * g["R3232_E011_LAMV"] - Q_e011
    s.r3232_e011_P = max(_p_free, 0.1)
    s.r3232_e011_T_prev = _T_e011_pre
    k_cap_e011 = ((max(m_701_e011, 0.0) + g["R3232_E011_RECON_KGH"] + m_786_d001 + m_321 + m_402)
                  / 3600.0 * g["R3232_CP"] + g["R3232_E011_UA_KW"])
    s.r3232_e011_T = Te011 + P_e011 * dt / max(s.r3232_e011_M * g["R3232_CP"] + k_cap_e011 * dt,
                                               1e-6)
    _m_net = in_e011 - m_v011 - m_718A - m_718B
    if relief > 0.0:
        _m_net -= relief
    s.r3232_e011_M = max(s.r3232_e011_M + _m_net / 3600.0 * dt, 1.0)
    return {
        "m701": m_701_e011, "in": in_e011, "pic": pic203_op, "vent": m_v011, "gen": gen_v011,
        "lvl": lvl_d011, "lic": lic503_op, "dmd": m718_dmd, "718A": m_718A, "718B": m_718B,
        "Q": Q_e011, "cond": m_cond_e011, "relief": relief, "lifted": s.sv_32357_lifted,
        # main.py 10710, the level the operator reads.
        "LI": s.r3232_e011_M / g["R3232_D011_M_DES"] * g["R3232_D011_LVL_SP"],
    }


def _assert_tick(a: dict, b: fc.FlashCondenserResult, s, cond, loops, label):
    pic, lic, fic418 = loops
    assert (a["m701"], a["in"], a["pic"], a["vent"], a["gen"]) == (
        b.m_701_kgh, b.in_kgh, b.pic_op_pct, b.m_702_kgh, b.gen_kgh), label
    assert (a["lvl"], a["lic"], a["dmd"], a["718A"], a["718B"], a["Q"], a["cond"]) == (
        b.lic_pv_pct, b.lic_op_pct, b.m_718_demand_kgh, b.m_718a_kgh, b.m_718b_kgh, b.q_kw,
        b.m_cond_kgh), label
    assert (a["relief"], a["lifted"]) == (b.m_relief_kgh, b.relief_lifted), label
    assert (s.r3232_e011_P, s.r3232_e011_T, s.r3232_e011_T_prev, s.r3232_e011_M) == (
        cond.p_bara, cond.t_c, cond.t_prev_c, cond.m_kg), label
    assert (b.p_bara, b.t_c, b.m_kg, b.level_pct) == (
        cond.p_bara, cond.t_c, cond.m_kg, a["LI"]), label
    assert s.tlag["F_718A"] == cond.lag_state[fc.LINE_718A_LAG_KEY], label
    assert s.tlag["F_323418"] == fic418.measurement, label
    # The heel cap (B-33) is inert on every tick compared here.
    assert (b.suction_lost, cond.suction_cap_kgh) == (False, None), label
    for v1c, loop in ((s.PIC_323203, pic), (s.LIC_323503, lic), (s.FIC_323418, fic418.loop)):
        assert (v1c["op"], v1c["sp"], v1c["pv"], v1c["pv1"], v1c["pv2"], v1c["mode"]) == (
            loop.op, loop.sp, loop.pv, loop.pv1, loop.pv2, loop.mode), (label, loop.tag)


def _loops(v1_gain: bool = True):
    """The port's three controllers. With `v1_gain`, PIC-323203 runs V1's 0.60 %/bar in place
    of the decided 60 %/bar (B-32), so the rest of the unit can be compared with V1 tick for
    tick."""
    pic = fc.pic_323203(e.E011_PV_OP_DES_PCT)
    if v1_gain:
        pic.Kc = e.PIC_323203_KC_TABLE
    return pic, fc.lic_323503(), fc.fic_323418()


# --------------------------------------------------------------------------------------
# The design basis
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("ours, theirs", [
    ("E011_M701_DES_KGH", "R3232_E011_M701_DES"), ("E011_M786_DES_KGH", "R3232_E011_M786_DES"),
    ("E011_M321_DES_KGH", "R3232_E011_M321_DES"), ("E011_M402_DES_KGH", "R3232_E011_M402_DES"),
    ("E011_IN_DES_KGH", "R3232_E011_IN_DES"), ("E011_RECON_KGH", "R3232_E011_RECON_KGH"),
    ("D011_M718_DES_KGH", "R3232_D011_M718_DES"), ("E011_MV_DES_KGH", "R3232_E011_MV_DES"),
    ("E011_MCOND_DES_KGH", "R3232_E011_MCOND_DES"), ("M718A_DES_KGH", "R3232_M718A_DES"),
    ("M718B_DES_KGH", "R3232_M718B_DES"), ("E011_T_C", "R3232_E011_T"),
    ("E011_T701_C", "R3232_E011_T701"), ("E011_T786_C", "R3232_E011_T786"),
    ("E011_P_BARA", "R3232_E011_P_BARA"), ("E011_SHELL_ID_M", "R3232_E011_SHELL_ID_M"),
    ("E011_TUBE_L_M", "R3232_E011_TUBE_L_M"), ("E011_N_TUBES", "R3232_E011_N_TUBES"),
    ("E011_TUBE_OD_M", "R3232_E011_TUBE_OD_M"), ("D011_ID_M", "R3232_D011_ID_M"),
    ("D011_SHELL_M", "R3232_D011_SHELL_M"), ("E011_VOL_M3", "R3232_E011_VOL_M3"),
    ("E011_RHO_L_KGM3", "R3232_E011_RHO_L"), ("E011_MW_VAP", "R3232_E011_MW_VAP"),
    ("E011_PV_OP_DES_PCT", "R3232_E011_PV_OP_DES"), ("D011_M_TAU_S", "R3232_D011_M_TAU_S"),
    ("D011_M_DES_KG", "R3232_D011_M_DES"), ("D011_LVL_SP_PCT", "R3232_D011_LVL_SP"),
    ("RHO_718_KGM3", "RHO_718_KGM3"), ("M718A_TAU_S", "R3232_M718A_TAU_S"),
    ("M718A_LINE_KG", "R3232_M718A_LINE_KG"), ("M718A_TAU_MAX_S", "FEED_TD_MAX_S"),
    ("CP_LP_CARBAMATE", "R3232_CP"), ("E011_Q_DES_KW", "R3232_E011_Q_DES_KW"),
    ("E011_UA_KW", "R3232_E011_UA_KW"), ("E011_SENS_KW", "R3232_E011_SENS"),
    ("E011_LAMV_KJKG", "R3232_E011_LAMV"),
])
def test_design_basis(v1, ours, theirs):
    assert getattr(e, ours) == v1[theirs]


def test_the_condensation_capacity_and_the_vent_split(v1):
    c = v1["coupling"]
    assert (e.E011_GAS_FEED_DES_KGH, e.E011_CONDENSATION_CAPACITY_DES_KGH) == (
        c.E011_GAS_FEED_DES_KGH, c.E011_CONDENSATION_CAPACITY_DES_KGH)
    assert e.E011_MV_DES_KGH / e.E011_IN_DES_KGH == v1["R3232_E011_PHIV"]


@pytest.mark.parametrize("gas", [0.0, 1.0, 3000.0, 5588.999, 5589.0, 5589.001, 6029.0, 6500.0,
                                 9000.0, 1e6])
def test_the_vent_generation_executes_v1s_function(v1, gas):
    assert fc.vent_generation_kgh(gas) == v1["coupling"].e011_vent_generation_kgh(gas)


@pytest.mark.parametrize("bad", [-1.0, -1e-12, math.nan, math.inf])
def test_the_vent_generation_refuses_what_v1_refuses(v1, bad):
    with pytest.raises(ValueError) as ours:
        fc.vent_generation_kgh(bad)
    with pytest.raises(ValueError) as theirs:
        v1["coupling"].e011_vent_generation_kgh(bad)
    assert str(ours.value) == str(theirs.value)


def test_the_state_and_controllers_are_seeded_as_v1_seeds_them(v1):
    """Every seed V1's, but two gains: PIC-323203's, the table's 0.60 in V1, per bar, the same
    0.60 on PT-323203's 1 bar span in the port, 60 %/bar (B-32); and FIC-323418's, the table's
    1.00 per kg/h in V1, 1065 %/(m3/h), on FT-323418's 0-10 m3/h span in the port, 10 %/(m3/h)
    (B-41), which the decided transcription carries."""
    assert _v1_state(v1, decided=False).FIC_323418["Kc"] == (
        e.FIC_323418_KC_TABLE * v1["RHO_718_KGM3"])
    assert e.FIC_323418_KC == e.FIC_323418_KC_TABLE * 100.0 / e.FT_323418_SPAN_M3H == 10.0
    s = _v1_state(v1)
    pic, lic, fic418 = _loops(v1_gain=False)
    assert (s.PIC_323203["Kc"], pic.Kc) == (e.PIC_323203_KC_TABLE, 60.0)
    assert pic.Kc == e.PIC_323203_KC_TABLE * 100.0 / e.PT_323203_SPAN_BAR
    for v1c, loop in ((s.PIC_323203, pic), (s.LIC_323503, lic), (s.FIC_323418, fic418.loop)):
        kc = v1c["Kc"] * (100.0 / e.PT_323203_SPAN_BAR if loop is pic else 1.0)
        assert (v1c["mode"], v1c["op"], v1c["sp"], v1c["pv"], v1c["pv1"], v1c["pv2"],
                kc, v1c["Ti"], v1c["Td"], v1c["act"], v1c["op_lo"], v1c["op_hi"],
                v1c["sp_lo"], v1c["sp_hi"]) == (
            loop.mode, loop.op, loop.sp, loop.pv, loop.pv1, loop.pv2, loop.Kc, loop.Ti,
            loop.Td, loop.act, loop.op_lo, loop.op_hi, loop.sp_lo, loop.sp_hi), loop.tag
    assert (fic418.design_flow, fic418.op_des, fic418.tau_s, fic418.rho_kgm3) == (
        v1["R3232_M718B_DES"], DECIDED_FIC418_OP, 45.0, v1["RHO_718_KGM3"])
    cond = fc.FlashCondenser(**fc.V1_CONDENSER)
    assert (s.r3232_e011_M, s.r3232_e011_T, s.r3232_e011_T_prev, s.r3232_e011_P) == (
        cond.m_kg, cond.t_c, cond.t_prev_c, cond.p_bara)


# --------------------------------------------------------------------------------------
# The condenser on its own, tick by tick
# --------------------------------------------------------------------------------------

M701 = e.E011_M701_DES_KGH


def _design(**over):
    base = {"m701": M701, "b505": 0.0, "b501": 0.0, "m786": e.E011_M786_DES_KGH,
            "m321": e.E011_M321_DES_KGH, "m402": e.E011_M402_DES_KGH}
    base.update(over)
    return base


def _run(v1, script, ticks: int, dt: float = DT, before=None, v1_gain: bool = True):
    """Drive the condenser alone through `script(k)`, comparing everything every tick."""
    s = _v1_state(v1)
    cond, loops = fc.FlashCondenser(**fc.V1_CONDENSER), _loops(v1_gain)
    if before:
        before(s, cond, loops)
    b = None
    for k in range(ticks):
        x = script(k)
        a = _v1_stage9(v1, s, x["m701"], x["b505"], x["b501"], x["m786"], x["m321"], x["m402"],
                       dt)
        b = cond.step(*loops, x["m701"], x["b505"], x["b501"], x["m786"], x["m321"], x["m402"],
                      dt)
        _assert_tick(a, b, s, cond, loops, f"tick {k}")
    return s, cond, loops, b


def _step(k0, before, after):
    return lambda k: after if k >= k0 else before


SCENARIOS = {
    "design hold": (lambda k: _design(), 600, DT),
    "flash vapour up 10 % (above capacity: PV-323203 takes it)": (
        lambda k: _design(m701=M701 * (1.1 if k >= 10 else 1.0)), 1200, 0.5),
    "flash vapour down 10 % (below capacity: the node empties to its floor)": (
        lambda k: _design(m701=M701 * (0.9 if k >= 10 else 1.0)), 1200, 0.5),
    "328D001 vent doubled": (lambda k: _design(m786=(552.0 if k >= 10 else 276.0)), 800, 0.5),
    "323D001 vent up 30 %": (
        lambda k: _design(m321=e.E011_M321_DES_KGH * (1.3 if k >= 10 else 1.0)), 800, 0.5),
    "791 wash cut to half": (
        lambda k: _design(m402=e.E011_M402_DES_KGH * (0.5 if k >= 10 else 1.0)), 800, 0.5),
    "LV-323505 blowing drum vapour to 323F010": (
        lambda k: _design(b505=(300.0 if 10 <= k < 300 else 0.0)), 800, 0.5),
    "LV-323501 blowing column gas into the drum": (
        lambda k: _design(b501=(900.0 if 10 <= k < 300 else 0.0)), 800, 0.5),
    "the flash vapour gone": (lambda k: _design(m701=(0.0 if k >= 10 else M701)), 1200, 1.0),
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


@pytest.mark.parametrize("stroke", [10.0, 50.0, 0.0])
def test_pv_323203_held_in_manual(v1, stroke):
    """The node settles where the valve passes the excess: 1.81 bar a at 10 %, 1.03 at 50 %;
    shut, it climbs on the design excess until SV32357 lifts at 6.01 bar a and holds it between
    there and 5.51 (A-16), on V1's lines with the decided relief written out."""
    def before(s, cond, loops):
        _manual(s.PIC_323203, loops[0], stroke)
    _run(v1, lambda k: _design(), 800, 0.5, before=before)


def test_pic_323203_on_a_new_set_point(v1):
    def before(s, cond, loops):
        s.PIC_323203["sp"] = 1.30
        loops[0].sp = 1.30
    _run(v1, lambda k: _design(), 1200, 0.5, before=before)


def test_fic_323418_on_a_new_set_point_and_in_manual(v1):
    """718B moves; 718A takes the rest of LIC-323503's demand off 718B's set point in AUTO and
    off its flow in MAN."""
    def script(k):
        return _design()

    def before(s, cond, loops):
        s.FIC_323418["sp"] = loops[2].loop.sp = 4.5
    _run(v1, script, 1500, 0.5, before=before)

    def before_man(s, cond, loops):
        _manual(s.FIC_323418, loops[2].loop, 70.0)
    _run(v1, script, 1500, 0.5, before=before_man)


def test_lic_323503_in_manual_fills_the_tank(v1):
    def before(s, cond, loops):
        _manual(s.LIC_323503, loops[1], 20.0)
    s, cond, loops, b = _run(v1, lambda k: _design(), 900, 1.0, before=before)
    assert b.level_pct > 60.0


# --------------------------------------------------------------------------------------
# The decided divergences (2026-09-27): both sides asserted
# --------------------------------------------------------------------------------------

def _diverge(v1, script, ticks: int, dt: float, before, limit_reached, v1_gain: bool):
    """Drive both sides bit-exact until `limit_reached(k, a, b)` first holds, then keep driving
    both and hand back every later tick as (V1 result, V1 holdup before and after, the port's
    holdup before, port result)."""
    s = _v1_state(v1)
    cond, loops = fc.FlashCondenser(**fc.V1_CONDENSER), _loops(v1_gain)
    if before:
        before(s, cond, loops)
    after, parted = [], None
    for k in range(ticks):
        x = script(k)
        m_v1_pre, m_pre = s.r3232_e011_M, cond.m_kg
        a = _v1_stage9(v1, s, x["m701"], x["b505"], x["b501"], x["m786"], x["m321"], x["m402"],
                       dt)
        b = cond.step(*loops, x["m701"], x["b505"], x["b501"], x["m786"], x["m321"], x["m402"],
                      dt)
        if parted is None and limit_reached(k, a, b):
            parted = k
        if parted is None:
            _assert_tick(a, b, s, cond, loops, f"tick {k}")
        else:
            after.append((a, m_v1_pre, s.r3232_e011_M, m_pre, b))
    assert after, "the limit was never reached"
    return s, cond, loops, parted, after


def test_323p008_trips_at_lt_323503s_l2_decided_divergence(v1):
    """B-93, decided 2026-10-14: AC4 stops 323P008A / B while LT-323503 stands below its L2, 5 %
    (PC23.1.9 / 1.10). The flash vapour and the 791 wash stopped from 200 kg: bit-exact until
    the level falls below 5 %, in the 147th second; there V1 draws FIC-323418's 3561.5 kg/h on, and
    the port's pumps stop, 718A and 718B nothing."""
    def before(s, cond, loops):
        s.r3232_e011_M = cond.m_kg = 200.0
    s, cond, loops, parted, after = _diverge(
        v1, lambda k: _design(m701=0.0, m402=0.0), 300, 1.0, before,
        lambda k, a, b: b.p008_tripped, v1_gain=True)
    assert parted == 146
    a, _, _, _, b = after[0]
    assert a["718B"] == e.M718B_DES_KGH and (b.m_718a_kgh, b.m_718b_kgh) == (0.0, 0.0)
    assert b.p008_tripped and not b.suction_lost


def test_323e011_condenses_on_its_dew_point_decided_divergence(v1):
    """B-30, decided 2026-10-15: 323E011 condenses on its dew point, anchored on V1's 5589 kg/h at
    1.13 bar a and 45 C against the 35 C water, and PV-323203 passes nothing at or below 1.0 bar a.
    701 down 10 % at tick 100, PV-323203 held at 25 %: bit-exact until the cut. V1 then generates
    nothing, its vent runs backwards on the 0.001 bar floor and its node reaches 0.1 bar a; the
    port's node falls only until the condenser leaves what the vent passes: after five minutes
    V1 stands at 0.1 bar a still venting 38.6 kg/h, the port at 1.1024 bar a venting 390.6 kg/h,
    never below 1.1023."""
    def before(s, cond, loops):
        _manual(s.PIC_323203, loops[0], 25.0)
        cond.dew_capacity, cond.vent_dp_floor_bar = True, e.VENT_DP_MIN_BAR
    s, cond, loops, parted, after = _diverge(
        v1, lambda k: _design(m701=M701 * (0.9 if k >= 100 else 1.0)), 3000, DT, before,
        lambda k, a, b: b.gen_kgh != a["gen"], v1_gain=True)
    assert parted == 100
    a, _, _, _, b = after[0]
    assert a["gen"] == 0.0 and b.gen_kgh == pytest.approx(-2.661, abs=1e-3)
    a, _, _, _, b = after[-1]
    assert s.r3232_e011_P == e.E011_P_FLOOR_BARA and a["vent"] == pytest.approx(38.59, abs=0.01)
    assert (cond.p_bara, b.m_702_kgh) == (pytest.approx(1.10244, abs=1e-5),
                                          pytest.approx(390.59, abs=0.01))
    assert min(x[4].p_bara for x in after) == pytest.approx(1.10233, abs=1e-5)


def test_the_decided_gain_is_inert_on_the_set_point(v1):
    """B-32. With the node on its set point PIC-323203's error is zero whatever its gain: the
    decided 60 %/bar holds the design point bit-exact with V1's 0.60 %/bar."""
    _run(v1, lambda k: _design(), 600, v1_gain=False)


@pytest.mark.parametrize("name", ["flash vapour up 10 %", "set point 1.30 bar a"])
def test_pic_323203_on_its_transmitter_span_decided_divergence(v1, name):
    """B-32. Bit-exact until the node leaves its set point; from then on V1's 0.60 %/bar trims
    it over hours and the port's 60 %/bar holds it. An hour on: PFD 701 up 10 %, V1 still at
    1.338 bar a and the port back on 1.130; a set point of 1.30, V1 at 1.171 and the port on it."""
    if name == "flash vapour up 10 %":
        script, before, sp = (lambda k: _design(m701=M701 * (1.1 if k >= 10 else 1.0)),
                              None, e.E011_P_BARA)
    else:
        def before(s, cond, loops):
            s.PIC_323203["sp"] = loops[0].sp = 1.30
        script, sp = (lambda k: _design()), 1.30
    s, cond, loops, parted, after = _diverge(
        v1, script, 7200, 0.5, before, lambda k, a, b: a["pic"] != b.pic_op_pct, v1_gain=False)
    # The controllers part on the first tick PIC-323203 sees the node off its set point.
    assert parted == (11 if before is None else 0)
    a, _, _, _, b = after[-1]
    if before is None:
        assert s.r3232_e011_P == pytest.approx(1.3379, abs=1e-4)
        assert (a["pic"], b.pic_op_pct) == (pytest.approx(31.11, abs=0.01),
                                            pytest.approx(50.15, abs=0.01))
    else:
        assert s.r3232_e011_P == pytest.approx(1.1711, abs=1e-4)
    assert cond.p_bara == pytest.approx(sp, abs=1e-4)


def test_pv_323203_on_its_vendor_trim_decided_divergence(v1):
    """Decision 23's class, decided 2026-10-17: PV-323203 on Metso's Neldisc, its printed capacities
    as its curve, from its 21.64 % design stroke, where V1 runs it linear from 25 %; PIC-323203 on
    V1's 0.60 %/bar on both sides, so the valve is the only difference. PFD 701 up 10 % at tick 10:
    bit-exact until PIC-323203 first moves the stroke, tick 11; the Neldisc's steeper gain about its
    design stroke then holds the node lower — an hour on, V1 at 1.3380 bar a on 31.11 %, the port at
    1.2784 on 26.66 %, both venting the 883 kg/h the constant capacity leaves."""
    s = _v1_state(v1)
    cond = fc.FlashCondenser(**{**fc.V1_CONDENSER, "pv_323203": fc.PV_323203_TRIM})
    loops = (fc.pic_323203(), fc.lic_323503(), fc.fic_323418())
    loops[0].Kc = e.PIC_323203_KC_TABLE
    parted = None
    for k in range(7200):
        x = _design(m701=M701 * (1.1 if k >= 10 else 1.0))
        a = _v1_stage9(v1, s, x["m701"], x["b505"], x["b501"], x["m786"], x["m321"], x["m402"],
                       0.5)
        b = cond.step(*loops, x["m701"], x["b505"], x["b501"], x["m786"], x["m321"], x["m402"],
                      0.5)
        if parted is None and (s.r3232_e011_P, a["vent"]) != (cond.p_bara, b.m_702_kgh):
            parted = k
    assert parted == 11
    assert (s.r3232_e011_P, cond.p_bara) == (pytest.approx(1.3380, abs=1e-4),
                                             pytest.approx(1.2784, abs=1e-4))
    assert (a["pic"], b.pic_op_pct) == (pytest.approx(31.11, abs=0.01),
                                        pytest.approx(26.66, abs=0.01))
    assert (a["vent"], b.m_702_kgh) == (pytest.approx(882.93, abs=0.01),
                                        pytest.approx(882.92, abs=0.01))


def test_the_tank_pumped_to_its_floor_decided_divergence(v1):
    """B-33. The flash vapour and the 791 wash both stopped: 1602 kg/h still arrives and
    FIC-323418 draws its 3561.5 kg/h set point. Bit-exact until 323P008 reaches the heel, in
    the 359th second. From then on V1 floors the tank at 1 kg and keeps drawing 3561.5 kg/h, making up the
    difference — 300 kg in the next nine minutes; the port delivers only what arrives, flags
    the loss of suction, makes up nothing, and FT-323418 reads the flow delivered, so
    FIC-323418 opens to 100 %."""
    def before(s, cond, loops):
        s.r3232_e011_M = cond.m_kg = 200.0
        cond.l2_pct = None      # 323P008's low-level trip (B-93) has its own test
    s, cond, loops, parted, after = _diverge(
        v1, lambda k: _design(m701=0.0, m402=0.0), 900, 1.0, before,
        lambda k, a, b: b.suction_lost, v1_gain=True)
    assert parted == 358
    v1_total = 0.0
    for a, v1_pre, v1_post, m_pre, b in after:
        # V1: FIC-323418's set point, whatever the tank holds, made up at the floor.
        assert a["718B"] == e.M718B_DES_KGH
        v1_created = (v1_post - v1_pre) - (a["in"] - a["vent"] - a["718A"] - a["718B"]) / 3600.0
        assert v1_created > 0.0
        v1_total += v1_created
        # The port: never more than the tank holds, and nothing made up.
        assert b.suction_lost and b.m_718b_kgh < a["718B"] and b.m_kg >= e.D011_M_FLOOR_KG
        ours_created = (b.m_kg - m_pre) - (b.in_kgh - b.m_702_kgh - b.m_718a_kgh
                                           - b.m_718b_kgh) / 3600.0
        assert abs(ours_created) < 1e-9
    # 299.6 kg on the envelope's volume alone; 323F004's vapour space in the node (B-51).
    assert v1_total == pytest.approx(299.76, abs=0.01)
    a, _, _, _, b = after[-1]
    assert s.r3232_e011_M == e.D011_M_FLOOR_KG
    assert b.m_718b_kgh + b.m_718a_kgh == pytest.approx(b.in_kgh - b.m_702_kgh, rel=1e-9)
    # FT-323418: V1's reads the set point it draws; the port's has lagged down to the flow
    # delivered, and FIC-323418 has opened fully against it.
    assert s.tlag["F_323418"] == pytest.approx(e.M718B_DES_KGH, rel=1e-12)
    assert loops[2].measurement == pytest.approx(b.m_718b_kgh, rel=1e-3)
    assert loops[2].loop.op == 100.0


# --------------------------------------------------------------------------------------
# Coupled: 323F004 rides the node, one tick later
# --------------------------------------------------------------------------------------

def _coupled(v1, script, ticks: int, before=None):
    """V1's stage 2 into V1's stage 9 against the ported 323F004 into the ported condenser. V1's
    drum adopts ``s.r3232_e011_P`` at the end of its stage, before stage 9 advances it; the
    ported drum is handed the condenser's pressure at the top of the tick — the same tear."""
    s = _v1_state(v1)
    drum, lic5 = ft.FlashTank(**ft.V1_DRUM), ft.lic_323505()
    cond, loops = fc.FlashCondenser(**fc.V1_CONDENSER), _loops()
    if before:
        before(s, cond, loops)
    for k in range(ticks):
        x = script(k)
        a2 = stage2._v1_stage2(v1, s, x["m314"], x["t314"], d.W_S314, DT)
        a9 = _v1_stage9(v1, s, a2["m701"], a2["blow"][0], 0.0, e.E011_M786_DES_KGH,
                        e.E011_M321_DES_KGH, e.E011_M402_DES_KGH, DT)
        b2 = drum.step(lic5, x["m314"], x["t314"], d.W_S314, cond.p_bara, d.F010_P_BARA, DT)
        b9 = cond.step(*loops, b2.m_701_kgh, b2.blowthrough_kgh, 0.0, e.E011_M786_DES_KGH,
                       e.E011_M321_DES_KGH, e.E011_M402_DES_KGH, DT)
        stage2._assert_tick(a2, b2, s, drum, lic5, f"323F004, tick {k}")
        _assert_tick(a9, b9, s, cond, loops, f"323E011, tick {k}")
    return s, drum, cond


@pytest.mark.parametrize("name, script", [
    ("a 10 % cut in the column bottoms",
     lambda k: {"m314": R323_M314_DES * (0.9 if k >= 10 else 1.0), "t314": d.C003_T_SP_C}),
    ("a 10 % rise in the column bottoms",
     lambda k: {"m314": R323_M314_DES * (1.1 if k >= 10 else 1.0), "t314": d.C003_T_SP_C}),
    ("the column bottoms 3 C colder",
     lambda k: {"m314": R323_M314_DES, "t314": d.C003_T_SP_C - (3.0 if k >= 10 else 0.0)}),
])
def test_the_flash_tank_rides_the_node(v1, name, script):
    s, drum, cond = _coupled(v1, script, 3000)
    assert drum.p_bara != e.E011_P_BARA


def test_the_flash_tank_under_pv_323203_held_open(v1):
    def before(s, cond, loops):
        _manual(s.PIC_323203, loops[0], 50.0)
    _coupled(v1, lambda k: {"m314": R323_M314_DES, "t314": d.C003_T_SP_C}, 3000, before=before)


# --------------------------------------------------------------------------------------
# Stages 1 to 4 and the condenser: the flash gas node end to end
# --------------------------------------------------------------------------------------

def test_the_liquor_train_and_its_flash_condenser_through_a_stripper_feed_cut(v1):
    """V1's stages 1 to 4 and 9 against the ported 323C003 -> 323F004 -> 323F010 -> 323D002
    with 323E011 / 323D011 closing the flash gas node: both blow-throughs reach the condenser,
    and 323F004 rides its live pressure."""
    s = _v1_state(v1)
    col = rc.RectifyingColumn(chest=rc.V1_CHEST)
    loops1 = (rc.tic_323007(), rc.pic_329202(rc.V1_CHEST), rc.lic_323501())
    drum, lic5 = ft.FlashTank(**ft.V1_DRUM), ft.lic_323505()
    sep, tic, pic = pe.PreEvaporator(chest=pe.V1_CHEST, vent=pe.V1_VENT, live_bubble=False, own_head_leg=False), pe.tic_323012(), pe.pic_329208(pe.V1_CHEST)
    tank, lic, fic = st.SolutionTank(backward_species=False), st.lic_323507(), st.fic_324401()
    cond, loops9 = fc.FlashCondenser(**fc.V1_CONDENSER), _loops()
    for k in range(800):
        drain = FEED_DES * (0.85 if k >= 20 else 1.0)
        s.tlag["R324_recyc"], s.tlag["R324_recyc_T"], s.tlag["R324_recyc_comp"] = stage4.NO_RECYCLE
        a1 = stage1._v1_stage1(v1, s, drain, 119.0, stage1.BOTTOMS_PCT, DT)
        a2 = stage2._v1_stage2(v1, s, a1["m314"], a1["dep314"][0], a1["dep314"][1], DT)
        a3 = stage3._v1_stage3(v1, s, a2["m319"], a2["dep319"][0], a2["dep319"][1], a2["blow"],
                               DT)
        a4 = stage4._v1_stage4(v1, s, a3["m317"], a3["dep317"][0], a3["dep317"][1], DT)
        a9 = _v1_stage9(v1, s, a2["m701"], a2["blow"][0], a1["blow"], e.E011_M786_DES_KGH,
                        e.E011_M321_DES_KGH, e.E011_M402_DES_KGH, DT)
        p_node = cond.p_bara
        b1 = col.step(*loops1, drain, 119.0, stage1.BOTTOMS_PCT, 172.0, P_LP_BARA,
                      drum.p_bara, d.E003_P_DES_BARA, DT)
        b2 = drum.step(lic5, b1.m_314_kgh, b1.drain_t_c, b1.drain_w, p_node, sep.p_bara, DT)
        b3 = sep.step(tic, pic, b2.m_319_kgh, b2.drain_t_c, b2.drain_w, b2.blowthrough_kgh,
                      b2.blowthrough_kmolh, b2.blowthrough_y, d.HIC_323605_DES_PCT_V1, P_LP_BARA,
                      d.P_324E002_DES_BARA, DT)
        b4 = tank.step(lic, fic, b3.m_317_kgh, b3.drain_t_c, b3.drain_w, *stage4.NO_RECYCLE,
                       False, DT)
        b9 = cond.step(*loops9, b2.m_701_kgh, b2.blowthrough_kgh, b1.blowthrough_kgh,
                       e.E011_M786_DES_KGH, e.E011_M321_DES_KGH, e.E011_M402_DES_KGH, DT)
        stage1._assert_tick(a1, b1, s, col, loops1, f"stage 1, tick {k}")
        stage2._assert_tick(a2, b2, s, drum, lic5, f"stage 2, tick {k}")
        stage3._assert_tick(a3, b3, s, sep, tic, pic, f"stage 3, tick {k}")
        stage4._assert_tick(a4, b4, s, tank, lic, fic, f"stage 4, tick {k}")
        _assert_tick(a9, b9, s, cond, loops9, f"stage 9, tick {k}")
    assert cond.p_bara < e.E011_P_BARA


# --------------------------------------------------------------------------------------
# The decided divergence: LV-323503 and FV-323418 (handoff B-44), both sides
# --------------------------------------------------------------------------------------

def test_the_vendor_valves_decided_divergence(v1):
    """V1 verbatim against the port, LIC-323503 in MAN at 70 % and FIC-323418 at 90 %. At
    design both pass PFD 718 and 718B; stroked, V1's linear trims from 50 % ask 1.40 and 1.80
    times their design flows, the vendor's trims from 52.86 and 78.45 % 1.67 and 1.41 times."""
    s = _v1_state(v1, valves_decided=False)
    cond, loops = fc.FlashCondenser(**fc.V1_CONDENSER), _loops()
    assert (s.LIC_323503["op"], s.FIC_323418["op"]) == (50.0, 50.0)
    assert (loops[1].op, loops[2].loop.op) == (DECIDED_LV503_OP, DECIDED_FIC418_OP)
    for v1c, loop, op in ((s.LIC_323503, loops[1], 70.0), (s.FIC_323418, loops[2].loop, 90.0)):
        v1c.update(mode="MAN", op=op)
        loop.set_mode("MAN")
        loop.op = op
    x = _design()
    a = _v1_stage9(v1, s, x["m701"], x["b505"], x["b501"], x["m786"], x["m321"], x["m402"], DT)
    b = cond.step(*loops, x["m701"], x["b505"], x["b501"], x["m786"], x["m321"], x["m402"], DT)
    assert a["dmd"] == pytest.approx(1.4 * e.D011_M718_DES_KGH, rel=1e-12)
    assert b.m_718_demand_kgh / e.D011_M718_DES_KGH == pytest.approx(1.6708, abs=1e-4)
    assert a["718B"] == pytest.approx(1.8 * e.M718B_DES_KGH, rel=1e-12)
    assert b.m_718b_kgh / e.M718B_DES_KGH == pytest.approx(1.4132, abs=1e-4)


# --------------------------------------------------------------------------------------
# The decided divergence: SV32357 (handoffs B-47, A-16, decided 2026-10-01), both sides
# --------------------------------------------------------------------------------------

def test_sv32357_relieves_a_shut_vent_decided_divergence(v1):
    """PV-323203 shut on the design excess, V1's lines (with 323F004's vapour space in the node,
    B-51) against the port. Bit-exact until the node reaches SV32357's 6.01 bar a, 110.2 s on.
    From then on V1 has no ceiling (B-30): 18.804 bar a at 400 s. The port lifts there, falls to
    5.51 bar a and lifts again every 25.4 s, 12 times in 400 s, peaking at 6.0125 bar a. (On the
    envelope's volume alone: 82.1 s, 24.912 bar a, 17 lifts every 19.1 s.) Both tanks close their
    books: V1's on the vent, the port's on the vent and the relief."""
    def before(s, cond, loops):
        _manual(s.PIC_323203, loops[0], 0.0)
        s.relief_decided = False

    def lifted(k, a, b):
        return b.relief_lifted
    s, cond, loops, parted, after = _diverge(v1, lambda k: _design(), 4000, DT, before, lifted,
                                             v1_gain=True)
    assert parted == 1102
    lifts, was, p_hi, p_lo = 0, False, 0.0, 99.0
    for k, (a, v1_pre, v1_post, m_pre, b) in enumerate(after, start=parted):
        assert a["relief"] == 0.0 and not a["lifted"]
        lifts += b.relief_lifted and not was
        was = b.relief_lifted
        p_hi, p_lo = max(p_hi, b.p_bara), min(p_lo, b.p_bara)
        booked = (b.in_kgh - b.m_702_kgh - b.m_relief_kgh - b.m_718a_kgh - b.m_718b_kgh) / 3600.0
        assert (b.m_kg - m_pre) == pytest.approx(booked * DT, abs=1e-9)
        assert (v1_post - v1_pre) == pytest.approx(
            (a["in"] - a["vent"] - a["718A"] - a["718B"]) / 3600.0 * DT, abs=1e-9)
    assert lifts == 12
    assert p_hi == pytest.approx(6.0125, abs=1e-4) and p_lo == 5.51
    assert s.r3232_e011_P == pytest.approx(18.804, abs=1e-3)


# --------------------------------------------------------------------------------------
# The decided divergence: a full 328D001 overflows into 323E011 (handoff A-15, 2026-10-03)
# --------------------------------------------------------------------------------------

def test_328d001s_overflow_reaches_the_port_and_not_v1(v1):
    """V1's condenser has no inlet for 328D001's overflow — V1's drum has no ceiling to spill
    from — so V1's tick is the port's with no overflow, to the bit (every test above). With 30
    t/h overflowing, the port's feed carries it as liquid, like the 791 wash: the gas load and
    the condensation are V1's, and the tank takes the overflow whole."""
    s = _v1_state(v1)
    cond, loops = fc.FlashCondenser(**fc.V1_CONDENSER), _loops(True)
    x = _design()
    a = _v1_stage9(v1, s, x["m701"], x["b505"], x["b501"], x["m786"], x["m321"], x["m402"], DT)
    m0 = cond.m_kg
    b = cond.step(*loops, x["m701"], x["b505"], x["b501"], x["m786"], x["m321"], x["m402"], DT,
                  m_d001_over_kgh=30000.0, t_d001_over_c=61.0)
    assert b.in_kgh == a["in"] + 30000.0
    assert (b.gen_kgh, b.m_cond_kgh, b.m_702_kgh) == (a["gen"], a["cond"], a["vent"])
    assert cond.m_kg - s.r3232_e011_M == pytest.approx(30000.0 / 3600.0 * DT, rel=1e-9)
    assert cond.m_kg > m0


def test_a_full_envelope_overflows_in_the_port_and_v1_fills_its_vapour_space(v1):
    """Decision 11's class on 323D011 (applied 2026-10-03, A-15). Both start a kilogram short of
    the envelope's 4204 kg of liquid with 323P008's draw shut: V1 keeps filling the node's vapour
    space, 4.9 kg past full in 3 s; the port holds the envelope full and publishes the excess as an overflow, its tank
    still closing its books."""
    def before(s, cond, loops):
        _manual(s.LIC_323503, loops[1], 0.0)
        _manual(s.FIC_323418, loops[2].loop, 0.0)
        s.r3232_e011_M = cond.m_kg = e.E011_FULL_KG - 1.0
    s, cond, loops = _v1_state(v1), fc.FlashCondenser(**fc.V1_CONDENSER), _loops(True)
    before(s, cond, loops)
    x = _design()
    for _ in range(30):
        m_pre = cond.m_kg
        a = _v1_stage9(v1, s, x["m701"], x["b505"], x["b501"], x["m786"], x["m321"], x["m402"],
                       DT)
        b = cond.step(*loops, x["m701"], x["b505"], x["b501"], x["m786"], x["m321"], x["m402"],
                      DT)
        booked = (b.in_kgh - b.m_702_kgh - b.m_relief_kgh - b.m_718a_kgh - b.m_718b_kgh
                  - b.m_overflow_kgh) / 3600.0 * DT
        assert cond.m_kg - m_pre == pytest.approx(booked, abs=1e-9)
    assert cond.m_kg == pytest.approx(e.E011_FULL_KG, abs=1e-9) and b.m_overflow_kgh > 0.0
    assert s.r3232_e011_M == pytest.approx(e.E011_FULL_KG + 4.93, abs=0.01)
    assert a["718A"] + a["718B"] == 0.0


# --------------------------------------------------------------------------------------
# The decided divergence: 323F004's vapour space in the node (handoff B-51, 2026-10-07)
# --------------------------------------------------------------------------------------

def test_323f004s_vapour_space_in_the_node_decided_divergence(v1):
    """V1 verbatim against the port, the flash vapour up 10 % with PV-323203 held at 25 %. While
    the node holds its pressure the free volume is inert and the two are bit-exact. On the first
    tick it moves, the step is the same moles on a larger volume: V1's 3.140 m3 of envelope
    against the port's 4.223, so the port's first step is 0.7435 of V1's, to the last bits. Both
    settle where PV-323203 passes the doubled excess, 1.5232 bar a, the port the slower: 1.416
    against 1.452 bar a after 13.4 s."""
    s = _v1_state(v1, volume_decided=False)
    cond, loops = fc.FlashCondenser(**fc.V1_CONDENSER), _loops(True)
    _manual(s.PIC_323203, loops[0], 25.0)
    parted, ratio = None, None
    for k in range(18000):
        x = _design(m701=M701 * (1.1 if k >= 10 else 1.0))
        p_pre, m_pre = cond.p_bara, cond.m_kg
        a = _v1_stage9(v1, s, x["m701"], x["b505"], x["b501"], x["m786"], x["m321"], x["m402"],
                       DT)
        b = cond.step(*loops, x["m701"], x["b505"], x["b501"], x["m786"], x["m321"], x["m402"],
                      DT)
        if parted is None and s.r3232_e011_P == cond.p_bara:
            _assert_tick(a, b, s, cond, loops, f"tick {k}")
        elif parted is None:
            parted = k
            v_env = e.E011_VOL_M3 - m_pre / e.E011_RHO_L_KGM3
            ratio = (cond.p_bara - p_pre) / (s.r3232_e011_P - p_pre)
            assert ratio == pytest.approx(v_env / (v_env + e.F004_VAPOUR_M3), rel=1e-12)
        if k == 143:
            assert (s.r3232_e011_P, cond.p_bara) == pytest.approx((1.4524, 1.4163), abs=1e-4)
    assert parted == 10 and ratio == pytest.approx(0.7435, abs=1e-4)
    assert cond.p_bara == pytest.approx(s.r3232_e011_P, abs=1e-6)
    assert cond.p_bara == pytest.approx(1.0 + 0.13 * (b.gen_kgh / 440.0) ** 2, abs=1e-5)


#: B-31's producers on their designs — 323F004's, 323E003's, 328D003's compartment II's and
#: 328D001's — and the same five kelvin hot.
B31_DES = {"t_f004_c": d.F004_T_SP_C, "t_e003_c": E003_T_C, "t_d003_ii_c": D003_TII_C,
           "t_d001_over_c": D001_T_C}
B31_HOT = {k: v + 5.0 for k, v in B31_DES.items()}


def test_the_inlets_at_their_producers_temperatures_decided_divergence(v1):
    """B-31, decided 2026-10-16: 323E011 charges 701, 321, 791 and 786 at 323F004's, 323E003's,
    328D003's compartment II's and 328D001's live temperatures, each as its departure from its
    producer's design; V1 at 106, 74, 56 and 61 C whatever they do. With every producer on its
    design the port is V1's on every tick, and so it is with every producer 5 K hot on V1's
    switch. Live, the first tick parts on the condensate, 0.0081 K hotter; after half an hour it
    stands at 45.090 C against V1's 45 C and the duty at 3470.9 kW against 3440, the node on its
    set point either way."""
    x = _design()
    for kw, live in ((B31_DES, True), (B31_HOT, False)):
        s = _v1_state(v1)
        cond, loops = fc.FlashCondenser(**fc.V1_CONDENSER, live_inlets=live), _loops()
        for k in range(600):
            a = _v1_stage9(v1, s, x["m701"], x["b505"], x["b501"], x["m786"], x["m321"],
                           x["m402"], DT)
            b = cond.step(*loops, x["m701"], x["b505"], x["b501"], x["m786"], x["m321"],
                          x["m402"], DT, **kw)
            _assert_tick(a, b, s, cond, loops, f"live {live}, tick {k}")
    s = _v1_state(v1)
    cond, loops = fc.FlashCondenser(**fc.V1_CONDENSER), _loops()
    for k in range(1800):
        a = _v1_stage9(v1, s, x["m701"], x["b505"], x["b501"], x["m786"], x["m321"], x["m402"],
                       1.0)
        b = cond.step(*loops, x["m701"], x["b505"], x["b501"], x["m786"], x["m321"], x["m402"],
                      1.0, **B31_HOT)
        if k == 0:
            first = cond.t_c - s.r3232_e011_T
    assert first == pytest.approx(0.008056, abs=1e-6)
    assert (s.r3232_e011_T, a["Q"]) == (45.0, 3440.0)
    assert (cond.t_c, b.q_kw) == (pytest.approx(45.0900, abs=1e-4), pytest.approx(3470.9, abs=0.1))
    assert cond.p_bara == pytest.approx(e.E011_P_BARA, abs=1e-6)
