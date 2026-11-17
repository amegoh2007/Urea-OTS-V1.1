"""V1 <-> V1.1 equivalence for 328C004, desorber II.

What is being proved
--------------------
V1 writes the column inline in `step_sim`, so its statements are TRANSCRIBED into `_v1_c004`
below, line for line, and declared as such: the aqueous cp (``main.py`` 8830), the tear reads
(8842, 8844), the stage itself (9169-9253, less 328E021's hot outlet 9181-9183, which the
hydrolyser's transcription carries), the tear writes (9670, 9675-9676) and AI-328701 (10330).
Everything they call is V1's own code, executed: ``_ctrl_ipd``, ``_fic_flow``, ``_lag1``,
``aqueous_cp``, ``tsat_steam``, ``des_alpha_live``, ``des_advance`` and ``cond_infer_328701``
lifted out of ``main.py`` with every constant they read; ``hydraulics`` loaded as a real module.
The state is seeded as ``State.__init__`` seeds it.

The departures
--------------
Twelve, each a switch in the transcription: ``decided`` names the ones whose port lines stand in
V1's. Three were decided by the process engineer for this unit on 2026-09-30, one on 2026-10-02
and one on 2026-10-09:

  * "735" — FFIC-329401 ratios the LP steam to 735, the desorbers' feed, where V1 reads 744
    (handoff B-39), its design ratio seeded into V1's controller;
  * "station" — FFIC-329401 is a ratio station, where V1 runs a PI on the measured ratio
    (handoff B-49): the slave's set point is the ratio set point times the feed, written from
    the functional diagram;
  * "recycle" — LIC-328505 is FIC-328406's master and 741 a draw on this column (handoff B-50):
    FIC-328406 stepped here on the vendor trim (`decided_valves.fic_flow`), LV-328505 switched
    shut while it is in cascade, both draws under the heel cap. V1 steps FIC-328406 in 328D003's
    stage on its own, 741 out of 740 — the tank's file carries V1's lines;
  * "B-73" — FV-329401 passes the live LP header's steam into the column's bottom (handoff B-73,
    the Typo Rule): ``_fic_flow`` transcribed with its flow element times the valve's pressure
    term, V1's butterfly law executed through V1's own ``valve_gas_anchored``; the header's
    pressure is a tick boundary;
  * "B-51" — the pressure takes the backward step on a tick where the explicit one would ring
    (handoff B-51): `core.node.stable_pressure_step` on V1's own ``vessel_dpdt`` and 750 law,
    750 evaluated at the pressure the step settles on — so it is switched in with "vapour"
    only: on V1's books the liquid pays 750 at the old pressure;

and seven are classes decided on other units, applied under §5 rule 7:

  * "vapour" — the liquid loses what boils (decision 24);
  * "B-42" — a negative duty condenses vapour (decision 15);
  * "heel" — LV-328505 drains only the liquid above a 1 kg heel (decision 11);
  * "overflow" — a full shell's excess leaves as a stream (decision 11);
  * "valve" — LV-328505 on Flowserve's trim from 90.07 %, FL 0.9471 (decision 23), V1's
    ``valve_liquid_anchored`` executed on it through `decided_valves.hydraulics`;
  * "gains" — FIC-329401 on the table's gain per cent of FT-329401's span (decision 10), seeded;
  * "flash" — LV-328505's choke handed 740's vapour pressure at 328E007's hot outlet, at most
    the valve's inlet pressure (B-46, decided 2026-09-30 for every letdown), V1's own
    ``liquor_pv_bara`` on V1's own valve law; the tick's 740 temperature is a boundary.

Every scenario runs the port against the switched transcription; those where neither limit binds
and the duty stays positive also run on V1's lines for B-42, the heel and the overflow; each
departure runs both ways in `test_second_desorber_decided_equivalence.py`, on `_both` here. Last, 328C004 is coupled to V1's 328C002 and 328C003 in V1's order: 749
same-tick, 750 a tear into 328C002, the column's pressure a tear into LV-328504. The two control
structures, B-49 and B-50, are proved both ways in `test_second_desorber_control_equivalence.py`.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from ureasim.core.flowsheet import Connection, CyclicFlowsheetError, Flowsheet, Tear, Unit
from ureasim.core.node import stable_pressure_step
from ureasim.data import control_valves as cvd
from ureasim.data import desorption_train as t
from ureasim.data import unit_328c004 as c
from ureasim.data.unit_328d003 import M735_DES_KGH
from ureasim.data.unit_329 import P_LP_BARA
from ureasim.thermo import ammonia_water as aw
from ureasim.units.desorption import first_desorber as fd
from ureasim.units.desorption import hydrolyser as hy
from ureasim.units.desorption import second_desorber as sd
from tests.equivalence import decided_valves as dv
from tests.equivalence import test_first_desorber_equivalence as c002_eq
from tests.equivalence import test_hydrolyser_equivalence as c003_eq
from tests.equivalence.v1_loader import lift, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

C004_NAMES = [
    "R328_C004_T", "R328_C004_T749", "R328_C004_P_BARA", "R328_C004_DT_DES", "R328_C004_ID_M",
    "R328_C004_SHELL_M", "R328_C004_VOL_M3", "R328_C004_H_NLL", "R328_C004_RHO",
    "R328_C004_M_DES", "R328_C004_DP_COL", "R328_C004_AREA_M2", "R328_C004_M931_DH",
    "R328_C004_Q_DES", "R328_M750_MW_DES", "R328_LV505_P2_BARA", "R328_C004_H_DES_M",
    "R328_C004_HEAD_DES", "R328_LV505_OP_DES", "R328_LV_CHAR", "R3232_E003_M744_DES",
    "RHO_744_KGM3", "S744_VOL_DES", "R328_FFIC_RATIO_DES", "R328_AI701_UREA_PHI",
    "R328_AI701_KB_NH3", "R328_AI701_L0_NH4", "R328_AI701_L0_OH", "R328_AI701_L0_HCO3",
    "_R328_MW_NH3", "cond_infer_328701", "tsat_steam", "_fic_flow", "_lag1", "RHO_741_KGM3",
    "S741_CAP_KGH",
]

#: V1's namespaces for the units upstream, built as their own equivalence tests build them.
tank_v1 = c003_eq.tank_v1
e007_v1 = c003_eq.e007_v1
c002_v1 = c003_eq.c002_v1
c003_v1 = c003_eq.v1

DT = 0.1

ALL = frozenset({"735", "station", "recycle", "vapour", "B-42", "heel", "overflow", "valve",
                 "gains", "flash", "B-73", "B-51"})
V1_VERBATIM = frozenset()
#: The seeded and structural departures, on decision 24's books: V1's lines for B-42 and the two
#: limits.
ON_BOOKS = frozenset({"735", "station", "recycle", "valve", "gains", "vapour", "flash", "B-73"})

#: LV-328505 as decided, re-derived from the vendor catalogue: design stroke [%], FL.
DECIDED_LV505_OP = dv.design_stroke_pct(cvd.LV_328505, t.C004_M739_DES_KGH)
DECIDED_LV505_FL = cvd.LV_328505.cases[cvd.LV_328505.normal].fl
#: 740 at LV-328505, the PFD's 89 C after 328E007 (B-46).
DECIDED_T740_DES = 89.0
#: FIC-329401 as decided, written from its sources: the table's 0.30 on FT-329401's 12 000 kg/h.
DECIDED_FIC401_KC = 0.30 * 100.0 / 12000.0
#: FFIC-329401 on 735, written from its sources: 6.495 t/h over PFD 735's 31.4 m3/h, at the
#: density PFD 735's own two numbers imply.
DECIDED_RHO_735 = 31114.0 / 31.4
DECIDED_FFIC_RATIO = (6495.0 / 1000.0) / (31114.0 / DECIDED_RHO_735)
#: FIC-328406 as decided, written from its sources: the table's 0.75 on FT-328406's 60 m3/h
#: (decision 10), its set point to the span (B-50), FV-328406 on its full-stroke capacity (B-44),
#: and FIC-328406:MAX, onto which LIC-328505's output is scaled.
DECIDED_FIC406_KC = 0.75 * 100.0 / 60.0
FT_328406_MAX_M3H = 60.0
DECIDED_CAP_741 = (cvd.FV_328406.cases[cvd.FV_328406.normal].flow * cvd.FV_328406.rated
                   / cvd.FV_328406.cases[cvd.FV_328406.normal].capacity * 992.42)
#: FV-329401 as decided (B-73), written from its sources: the LP header's 4.0 bar g (B-69) to the
#: column's bottom at its design bubble point, V1's butterfly law (xT 0.75, linear, steam's MW and
#: gamma, V1 `steam_system.py`).
DECIDED_FV401_P1 = 4.0 + 1.01325
STEAM_MW_V1, STEAM_GAMMA_V1 = 18.01528, 1.30


def _fv_401_ratio(g, p_lp, p_bottom):
    """FV-329401's pressure term on V1's own ``valve_gas_anchored`` (B-73, the port's lines)."""
    p2_des = g["R328_C004_P_BARA"] + g["R328_C004_DP_COL"]
    return g["hydraulics"].valve_gas_anchored(
        1.0, 1.0, p_lp, p_bottom, g["tsat_steam"](max(p_lp, 1e-6)) + 273.15, 1.0,
        DECIDED_FV401_P1, p2_des, g["tsat_steam"](DECIDED_FV401_P1) + 273.15, STEAM_MW_V1,
        STEAM_GAMMA_V1, characteristic="linear", xt=0.75)


def _fic_flow_b73(g, c, design, op_des, store, key, dt, ratio, cas_sp=None):
    """V1 ``_fic_flow`` TRANSCRIBED, its flow element times FV-329401's pressure term (B-73)."""
    pre = design * (c["op"] / op_des) * ratio
    pv = g["_lag1"](store, key, pre, 5.0, dt)
    op = g["_ctrl_ipd"](c, pv, dt, cas_sp)
    return design * (op / op_des) * ratio


@pytest.fixture(scope="module")
def v1(c003_v1):
    ns = dict(c003_v1)
    ns.update(lift(C004_NAMES, seed=dict(ns)))
    return ns


def _v1_state(v1, decided=ALL):
    """The V1 plant-state fields 328C004 reads and writes, seeded as `State.__init__` seeds them
    (``main.py`` 6641, 6853-6855, 6861, 6868, 7035-7058, 7100-7106); "735", "valve" and "gains"
    in `decided` seed the port's ratio, LV-328505 stroke and FIC-329401 gain."""
    g = v1
    s = c003_eq._v1_state(v1)
    s.a328_c004_M = g["R328_C004_M_DES"]
    s.a328_c004_T = g["R328_C004_T"]
    s.a328_c004_T_prev = g["R328_C004_T"]
    s.a328_c004_P = g["R328_C004_P_BARA"]
    s.w_328c004 = dict(g["W_S739"])
    s.T_740 = DECIDED_T740_DES
    s.y_328_750 = dict(g["DES_C004"]["y"])
    s.m_735 = M735_DES_KGH
    r = g["R328_FFIC_RATIO_DES"]
    s.FFIC_329401 = {"mode": "AUTO", "op": g["R328_C004_M931_DES"], "sp": r, "pv": r, "pv1": r,
                     "pv2": r, "Kc": 8.0e5, "Ti": 40.0, "Td": 0.0, "act": +1.0,
                     "op_lo": 0.0, "op_hi": 12000.0, "sp_lo": 0.0, "sp_hi": 0.5}
    M931 = g["R328_C004_M931_DES"]
    s.FIC_329401 = {"mode": "CAS", "op": 50.0, "sp": M931, "pv": M931, "pv1": M931, "pv2": M931,
                    "Kc": 0.3, "Ti": 100.0, "Td": 0.0, "act": +1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0, "sp_hi": 12000.0}
    s.LIC_328505 = {"mode": "AUTO", "op": 50.0, "sp": 50.0, "pv": 50.0, "pv1": 50.0,
                    "pv2": 50.0, "Kc": 1.45, "Ti": 180.0, "Td": 0.0, "act": -1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0, "sp_hi": 100.0}
    # FIC-328406, seeded as `State.__init__` seeds it (7124-7127) in 328D003's stage.
    R741 = g["RHO_741_KGM3"]
    s.FIC_328406 = {"mode": "MAN", "op": 0.0, "sp": 0.0, "pv": 0.0, "pv1": 0.0, "pv2": 0.0,
                    "Kc": 0.75 * R741, "Ti": 80.0, "Td": 0.0, "act": +1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0, "sp_hi": g["S741_CAP_KGH"] / R741}
    s.cap_741 = None
    s.p_lp = P_LP_BARA
    if "735" in decided:
        s.FFIC_329401.update(sp=DECIDED_FFIC_RATIO, pv=DECIDED_FFIC_RATIO,
                             pv1=DECIDED_FFIC_RATIO, pv2=DECIDED_FFIC_RATIO)
    if "valve" in decided:
        s.LIC_328505["op"] = DECIDED_LV505_OP
    if "gains" in decided:
        s.FIC_329401["Kc"] = DECIDED_FIC401_KC
    if "recycle" in decided:
        s.FIC_328406.update(Kc=DECIDED_FIC406_KC, sp_hi=FT_328406_MAX_M3H)
    return s


def _v1_c004(v1, s, m_749, T_749, dt, decided=ALL):
    """V1 `main.py` 8830, 8842, 8844, 9169-9253 (less 9181-9183), 9670, 9675-9676 and 10330,
    TRANSCRIBED line for line; each departure in `decided` puts the port's lines in V1's.
    ``m_749`` and ``T_749`` are stage 4's ``m_747`` and ``T_749``, 749's composition
    ``s.w_328c003`` after stage 4."""
    g = v1
    MW_SOL, SOL_SPECIES = g["MW_SOL"], g["SOL_SPECIES"]
    cp_328c004 = g["aqueous_cp"](g["R328_CP"], g["R328_C004_T"], s.a328_c004_T)      # 8830
    m744_prev = s.tlag.get("R3232_744", g["R3232_E003_M744_DES"])                   # 8842
    m931_prev = s.tlag.get("R328_M931", g["R328_C004_M931_DES"])                    # 8844
    Tc004 = s.a328_c004_T
    ratio = (m931_prev / 1000.0) / max(m744_prev / g["RHO_744_KGM3"], 1e-6)
    if "735" in decided:  # ---- the ratio on the desorbers' feed (the port's lines) ----
        ratio = (m931_prev / 1000.0) / max(s.m_735 / DECIDED_RHO_735, 1e-6)
    ffic_pv = g["_lag1"](s.tlag, "FF_ratio", ratio, 0.0, dt)
    if "station" in decided:  # ---- a ratio station (the port's lines), on the ratio's feed ----
        feed = (s.m_735 / DECIDED_RHO_735 if "735" in decided
                else m744_prev / g["RHO_744_KGM3"])
        st = s.FFIC_329401
        if st["mode"] == "AUTO":
            if s.FIC_329401["mode"] != "CAS":  # the slave not listening: the ratio tracks
                st["sp"] = min(max(ffic_pv, st["sp_lo"]), st["sp_hi"])
            st["op"] = min(max(st["sp"] * feed * 1000.0, st["op_lo"]), st["op_hi"])
        st["pv"] = ffic_pv
        ffic_op = st["op"]
    else:
        ffic_op = g["_ctrl_ipd"](s.FFIC_329401, ffic_pv, dt)
    if "B-73" in decided:  # ---- FV-329401 on the live LP header (the port's lines) ----
        m_931 = _fic_flow_b73(g, s.FIC_329401, g["R328_C004_M931_DES"], 50.0, s.tlag, "F_329401",
                              dt, _fv_401_ratio(g, s.p_lp, s.a328_c004_P + g["R328_C004_DP_COL"]),
                              cas_sp=ffic_op)
    else:
        m_931 = g["_fic_flow"](s.FIC_329401, g["R328_C004_M931_DES"], 50.0, s.tlag, "F_329401",
                               dt, cas_sp=ffic_op)
    in_c004 = m_749 + m_931
    lvl_c004 = s.a328_c004_M / g["R328_C004_M_DES"] * 50.0
    lic505_op = g["_ctrl_ipd"](s.LIC_328505, lvl_c004, dt)
    lv_op, m_741 = lic505_op, 0.0
    if "recycle" in decided:  # ---- FIC-328406 on LIC-328505, LV-328505 switched (the port's) ----
        cas = s.FIC_328406["mode"] == "CAS"
        m_741 = dv.fic_flow(g, s.FIC_328406, DECIDED_CAP_741, 100.0, s.tlag, "F_328406", dt,
                            cas_sp=(lic505_op / 100.0 * FT_328406_MAX_M3H * g["RHO_741_KGM3"]
                                    if cas else None),
                            rho=g["RHO_741_KGM3"], cap=s.cap_741)
        if cas:
            lv_op = 0.0
    _h_c004 = s.a328_c004_M / (g["R328_C004_RHO"] * g["R328_C004_AREA_M2"])
    _p1_505 = s.a328_c004_P + g["R328_C004_RHO"] * 9.80665 * _h_c004 / 1.0e5
    lv505_pv = {}
    if "flash" in decided:  # ---- B-46: 740's vapour pressure into the choke (the port's) ----
        lv505_pv = {"pv_bara": min(g["liquor_pv_bara"](s.w_328c004, s.T_740), _p1_505),
                    "pv_des_bara": g["liquor_pv_bara"](g["W_S739"], DECIDED_T740_DES)}
    if "valve" in decided:  # ---- LV-328505 on its vendor trim (the port's valve) ----
        m_739 = dv.hydraulics().valve_liquid_anchored(
            g["R328_C004_M739_DES"], lv_op / 100.0, _p1_505, g["R328_LV505_P2_BARA"],
            g["R328_C004_RHO"], DECIDED_LV505_OP / 100.0,
            g["R328_C004_P_BARA"] + g["R328_C004_HEAD_DES"], g["R328_LV505_P2_BARA"],
            g["R328_C004_RHO"], characteristic=dv.MOD_EQUAL_PCT, fl=DECIDED_LV505_FL,
            **lv505_pv)
    else:
        m_739 = g["hydraulics"].valve_liquid_anchored(
            g["R328_C004_M739_DES"], lv_op / 100.0, _p1_505, g["R328_LV505_P2_BARA"],
            g["R328_C004_RHO"], g["R328_LV505_OP_DES"] / 100.0,
            g["R328_C004_P_BARA"] + g["R328_C004_HEAD_DES"], g["R328_LV505_P2_BARA"],
            g["R328_C004_RHO"], characteristic=g["R328_LV_CHAR"], **lv505_pv)
    sens_c004 = m_749 / 3600.0 * cp_328c004 * (T_749 - Tc004)
    q_c004 = sens_c004 + m_931 / 3600.0 * g["R328_C004_M931_DH"]
    gen750 = max(g["R328_C004_M750_DES"] * (q_c004 / g["R328_C004_Q_DES"]), 0.0)
    if "B-42" in decided:  # ---- a negative duty condenses vapour (the port's line) ----
        gen750 = g["R328_C004_M750_DES"] * (q_c004 / g["R328_C004_Q_DES"])
    _mw750_live = 1.0 / max(sum(s.y_328_750.get(k, 0.0) / MW_SOL[k] for k in SOL_SPECIES), 1e-12)
    m_750 = g["hydraulics"].valve_gas_anchored(
        g["R328_C004_M750_DES"], 1.0, s.a328_c004_P, s.a328_c002_P, Tc004 + 273.15,
        1.0, g["R328_C004_P_BARA"], g["R328_C002_P_TOP"], g["R328_C004_T"] + 273.15,
        _mw750_live, characteristic="linear", mw_des=g["R328_M750_MW_DES"])
    # ---- decision 24: the liquid loses what boils (the port's lines), V1's the overhead ----
    boil = gen750 if "vapour" in decided else m_750
    lost = False
    s.cap_741 = None
    if "heel" in decided:  # ---- the decided heel (the port's lines): the recycle first ----
        avail = max(max(s.a328_c004_M - 1.0, 0.0) / max(dt, 1e-9) * 3600.0 + in_c004 - boil,
                    0.0)
        lost = m_741 + m_739 > avail
        if lost:
            if m_741 > avail:
                m_741 = s.cap_741 = avail
            m_739 = min(m_739, avail - m_741)
    m_export = m_739
    m_739 = m_export + m_741  # the bottoms, both routes
    M_c004_pre = s.a328_c004_M
    over, full = 0.0, g["R328_C004_VOL_M3"] * g["R328_C004_RHO"]
    if "overflow" in decided:  # ---- the decided overflow (the port's lines) ----
        m_new = max(M_c004_pre + (in_c004 - boil - m_739) / 3600.0 * dt, 1.0)
        if m_new > full:
            over = (m_new - full) / max(dt, 1e-9) * 3600.0
    _vv_c004 = g["hydraulics"].vapour_volume_m3(g["R328_C004_VOL_M3"], M_c004_pre,
                                                g["R328_C004_RHO"])
    _dmdt_c004 = (in_c004 - boil - m_739 - over) / 3600.0
    _T_c004_pre = s.a328_c004_T
    if "B-51" in decided:  # ---- the backward step where the explicit one rings (the port's) ----
        if "vapour" not in decided:
            raise ValueError("B-51's 750 at the settled pressure presupposes decision 24's books")
        def _m750_at(p):
            return g["hydraulics"].valve_gas_anchored(
                g["R328_C004_M750_DES"], 1.0, p, s.a328_c002_P, Tc004 + 273.15,
                1.0, g["R328_C004_P_BARA"], g["R328_C002_P_TOP"], g["R328_C004_T"] + 273.15,
                _mw750_live, characteristic="linear", mw_des=g["R328_M750_MW_DES"])

        def _dpdt(p):
            return g["hydraulics"].vessel_dpdt(
                p, s.a328_c004_T + 273.15, _vv_c004, _mw750_live,
                gen750 / _mw750_live, _m750_at(p) / _mw750_live,
                dtdt_k_s=(s.a328_c004_T - s.a328_c004_T_prev) / dt,
                dvvdt_m3_s=-_dmdt_c004 / g["R328_C004_RHO"])
        p_new, backward = stable_pressure_step(s.a328_c004_P, dt, _dpdt, 0.1)
        if backward:
            m_750 = _m750_at(p_new)
        s.a328_c004_P = max(p_new, 0.1)
    else:
        s.a328_c004_P = max(
            s.a328_c004_P + g["hydraulics"].vessel_dpdt(
                s.a328_c004_P, s.a328_c004_T + 273.15, _vv_c004, _mw750_live,
                gen750 / _mw750_live, m_750 / _mw750_live,
                dtdt_k_s=(s.a328_c004_T - s.a328_c004_T_prev) / dt,
                dvvdt_m3_s=-_dmdt_c004 / g["R328_C004_RHO"]) * dt,
            0.1)
    s.a328_c004_T_prev = _T_c004_pre
    s.a328_c004_T = g["tsat_steam"](s.a328_c004_P + g["R328_C004_DP_COL"])
    s.a328_c004_M = max(M_c004_pre + (in_c004 - boil - m_739) / 3600.0 * dt, 1.0)
    if over:
        s.a328_c004_M = full
    a_c004 = g["des_alpha_live"]("C004", s.a328_c004_T, m_931, m_739,
                                 s.w_328c004, s.a328_c004_P + g["R328_C004_DP_COL"])
    s.w_328c004, y_750 = g["des_advance"](s.w_328c004, s.a328_c004_M,
                                          [(s.w_328c003, m_749), (g["W_STEAM"], m_931)],
                                          boil, a_c004, m_739 + over, 0.0, dt)
    s.y_328_750 = y_750
    s.tlag["R328_750"] = m_750                        # main.py 9670
    s.tlag["R328_M931"] = m_931                       # 9675
    s.tlag["R328_739"] = m_739                        # 9676
    ai = g["cond_infer_328701"](s.w_328c004["NH3"] * 1e6, s.w_328c004["Urea"] * 1e6, 0.0)
    return {"ffic_pv": ffic_pv, "ffic_op": ffic_op, "931": m_931, "in": in_c004,
            "lvl": lvl_c004, "lic": lic505_op, "lv": lv_op, "739": m_739, "export": m_export,
            "741": m_741, "lost": lost, "q": q_c004,
            "gen": gen750, "750": m_750, "over": over,
            "domain": g["DES_VLE_DOMAIN"].get("C004"), "AI": ai,
            # main.py 10797-10801, the telemetry.
            "TT_328004": s.a328_c004_T - g["R328_C004_DT_DES"],
            "LI_328505": s.a328_c004_M / g["R328_C004_M_DES"] * 50.0}


#: The PI loops, and the ratio station, whose state is its mode, set point, PV and output.
LOOPS = (("FIC_329401", "fic_329401"), ("LIC_328505", "lic_328505"),
         ("FIC_328406", "fic_328406"))
STATION = ("FFIC_329401", "ffic_329401")


def _loop(loops, name):
    loop = getattr(loops, name)
    return loop.loop if isinstance(loop, sd.FlowLoop) else loop


def _assert_tick(a: dict, b: sd.SecondDesorberResult, s, col, loops, label):
    assert (a["ffic_pv"], a["ffic_op"], a["931"], a["in"], a["lvl"], a["lic"], a["lv"],
            a["739"], a["export"], a["741"], a["lost"]) == (
        b.ffic_pv, b.ffic_op_kgh, b.m_931_kgh, b.in_kgh, b.lic_pv_pct, b.lic_op_pct,
        b.lv_op_pct, b.m_739_kgh, b.m_export_kgh, b.m_741_kgh, b.drain_lost), label
    assert (a["q"], a["gen"], a["750"], a["over"]) == (b.q_kw, b.gen_kgh, b.m_750_kgh,
                                                       b.m_overflow_kgh), label
    assert (s.a328_c004_P, s.a328_c004_T, s.a328_c004_T_prev, s.a328_c004_M) == (
        col.p_bara, col.t_c, col.t_prev_c, col.m_kg), label
    assert (b.p_bara, b.t_c, b.m_kg, b.t_top_c, b.level_pct) == (
        col.p_bara, col.t_c, col.m_kg, a["TT_328004"], a["LI_328505"]), label
    assert (s.w_328c004, s.y_328_750) == (col.w, col.y_750) == (b.w, b.y_750), label
    assert (a["domain"], a["AI"]) == (b.vle_domain, b.ai_328701_us_cm), label
    assert (s.tlag["R328_M931"], s.tlag["F_329401"], s.tlag.get("F_328406", 0.0),
            s.cap_741) == (col.m_931_prev_kgh, loops.fic_329401.measurement,
                           loops.fic_328406.measurement, col.cap_741_kgh), label
    for v1_name, name in LOOPS:
        v1c, loop = getattr(s, v1_name), _loop(loops, name)
        assert (v1c["op"], v1c["sp"], v1c["pv"], v1c["pv1"], v1c["pv2"], v1c["mode"]) == (
            loop.op, loop.sp, loop.pv, loop.pv1, loop.pv2, loop.mode), (label, v1_name)
    v1c, st = getattr(s, STATION[0]), getattr(loops, STATION[1])
    assert (v1c["op"], v1c["sp"], v1c["pv"], v1c["mode"]) == (st.op, st.sp, st.pv, st.mode), (
        label, STATION[0])


# --------------------------------------------------------------------------------------
# The design basis
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("ours, theirs", [
    ("C004_ID_M", "R328_C004_ID_M"), ("C004_SHELL_M", "R328_C004_SHELL_M"),
    ("C004_VOL_M3", "R328_C004_VOL_M3"), ("C004_H_NLL_M", "R328_C004_H_NLL"),
    ("C004_RHO_KGM3", "R328_C004_RHO"), ("C004_M_DES_KG", "R328_C004_M_DES"),
    ("C004_DT_DES_K", "R328_C004_DT_DES"), ("C004_DP_COL_BAR", "R328_C004_DP_COL"),
    ("C004_AREA_M2", "R328_C004_AREA_M2"), ("C004_M931_DH_KJKG", "R328_C004_M931_DH"),
    ("C004_Q_DES_KW", "R328_C004_Q_DES"), ("C004_MW750_DES", "R328_M750_MW_DES"),
    ("LV505_P2_BARA", "R328_LV505_P2_BARA"), ("C004_H_DES_M", "R328_C004_H_DES_M"),
    ("C004_HEAD_DES_BAR", "R328_C004_HEAD_DES"),
])
def test_design_basis(v1, ours, theirs):
    assert getattr(c, ours) == v1[theirs]


def test_the_kremser_stage_is_v1s(v1):
    st, ours = v1["DES_STAGES"]["C004"], c.C004_STAGE
    assert (ours.n_theo, ours.v_kgh, ours.l_kgh, ours.p_bara, ours.s, ours.r, ours.k,
            ours.t_eq_c, ours.k_inf) == (st["N"], st["V"], st["L"], st["P"], st["S"], st["r"],
                                         st["k"], st["T_eq"], v1["R328_AI701_KINF_C004"])


def test_the_letdown_anchor_and_the_decided_seeds(v1):
    """LV-328505's design inlet is V1's; V1 strokes it linear from 50 %, the port on Flowserve's
    trim from 90.07 %; FIC-329401 on 0.0025 %/(kg/h) where V1 runs 0.30; FFIC-329401's design
    ratio on 735, 0.20685 t/m3 — V1's on 744 is the same number to the last few bits."""
    assert c.LV505_P1_DES_BARA == v1["R328_C004_P_BARA"] + v1["R328_C004_HEAD_DES"]
    assert v1["R328_LV505_OP_DES"] == 50.0 and v1["R328_LV_CHAR"] == "linear"
    assert (c.LV505_OP_DES_PCT, c.LV505_FL, c.LV505_CHAR) == (
        DECIDED_LV505_OP, DECIDED_LV505_FL, "mod_equal_pct")
    assert DECIDED_LV505_OP == pytest.approx(90.068, abs=1e-3)
    assert c.FIC_329401_KC == DECIDED_FIC401_KC == 0.0025
    assert c.FFIC_329401_RATIO_DES == DECIDED_FFIC_RATIO
    assert DECIDED_FFIC_RATIO == pytest.approx(v1["R328_FFIC_RATIO_DES"], rel=1e-14)


@pytest.mark.parametrize("nh3, urea, co2", [(1.0, 1.0, 0.0), (0.0, 0.0, 0.0), (5.0, 0.2, 0.0),
                                            (100.0, 10.0, 3.0), (0.01, 50.0, 0.0)])
def test_the_conductivity_executes_v1s(v1, nh3, urea, co2):
    assert aw.condensate_conductivity_us_cm(nh3, urea, co2) == v1["cond_infer_328701"](
        nh3, urea, co2)


def test_the_state_and_the_controllers_are_seeded_as_v1_seeds_them(v1):
    """Every seed V1's, but the decided: FIC-329401's and FIC-328406's gains on span, FIC-328406's
    set point to FT-328406's 60 m3/h (B-50), and FFIC-329401 a ratio station (B-49) on V1's ratio,
    output and limits."""
    s, col, loops = _v1_state(v1), sd.SecondDesorber(taps=False, fv_329401=sd.V1_FV_329401, l2_stop=False), sd.SecondDesorberLoops(fic_329401=sd.fic_329401(sd.V1_FV_329401),
                                         lic_328505=sd.lic_328505(taps=False))
    assert (s.a328_c004_M, s.a328_c004_T, s.a328_c004_T_prev, s.a328_c004_P, s.w_328c004,
            s.y_328_750) == (col.m_kg, col.t_c, col.t_prev_c, col.p_bara, col.w, col.y_750)
    v1c, st = s.FFIC_329401, loops.ffic_329401
    assert (v1c["mode"], v1c["op"], v1c["sp"], v1c["pv"], v1c["op_lo"], v1c["op_hi"],
            v1c["sp_lo"], v1c["sp_hi"]) == (st.mode, st.op, st.sp, st.pv, st.op_lo, st.op_hi,
                                            st.sp_lo, st.sp_hi)
    assert st.factor == 1000.0 and not hasattr(st, "Kc")
    for v1_name, name in LOOPS:
        v1c, loop = getattr(s, v1_name), _loop(loops, name)
        assert (v1c["mode"], v1c["op"], v1c["sp"], v1c["pv"], v1c["pv1"], v1c["pv2"], v1c["Kc"],
                v1c["Ti"], v1c["Td"], v1c["act"], v1c["op_lo"], v1c["op_hi"], v1c["sp_lo"],
                v1c["sp_hi"]) == (loop.mode, loop.op, loop.sp, loop.pv, loop.pv1, loop.pv2,
                                  loop.Kc, loop.Ti, loop.Td, loop.act, loop.op_lo, loop.op_hi,
                                  loop.sp_lo, loop.sp_hi), v1_name
    s0 = _v1_state(v1, V1_VERBATIM)
    assert (s0.FFIC_329401["sp"], s0.LIC_328505["op"], s0.FIC_329401["Kc"]) == (
        v1["R328_FFIC_RATIO_DES"], 50.0, 0.3)
    assert (s0.FIC_328406["Kc"], s0.FIC_328406["sp_hi"]) == (
        0.75 * 992.42, pytest.approx(33.98, abs=0.01))
    assert (loops.fic_328406.design_flow, loops.fic_328406.op_des) == (DECIDED_CAP_741, 100.0)


# --------------------------------------------------------------------------------------
# The column on its own, tick by tick
# --------------------------------------------------------------------------------------

def _design(**over):
    base = {"m749": t.C004_M749_DES_KGH, "t749": t.C004_T749_C, "w749": dict(t.W_S747),
            "m735": M735_DES_KGH, "pc002": t.C002_P_TOP_BARA, "t740": DECIDED_T740_DES,
            "plp": P_LP_BARA}
    base.update(over)
    return base


def _feed(s, x):
    """Write a tick's boundaries into V1's neighbouring states."""
    s.w_328c003 = dict(x["w749"])
    s.a328_c002_P, s.m_735, s.T_740, s.p_lp = x["pc002"], x["m735"], x["t740"], x["plp"]


def _port(col, loops, x, dt):
    return col.step(loops, x["m749"], x["t749"], dict(x["w749"]), x["m735"], x["pc002"],
                    x["t740"], dt, p_lp_bara=x["plp"])


def _run(v1, script, ticks: int, dt: float = DT, before=None, decided=ALL):
    """Drive the column alone through `script(k)`, comparing everything every tick."""
    if not {"735", "station", "recycle", "valve", "gains"} <= decided:
        raise ValueError("the port's seeds are the decided ones; run V1's in the divergences")
    s, col, loops = _v1_state(v1, decided), sd.SecondDesorber(taps=False, fv_329401=sd.V1_FV_329401, l2_stop=False), sd.SecondDesorberLoops(fic_329401=sd.fic_329401(sd.V1_FV_329401),
                                         lic_328505=sd.lic_328505(taps=False))
    if before:
        before(s, col, loops)
    b = None
    for k in range(ticks):
        x = script(k)
        _feed(s, x)
        a = _v1_c004(v1, s, x["m749"], x["t749"], dt, decided)
        b = _port(col, loops, x, dt)
        _assert_tick(a, b, s, col, loops, f"tick {k}")
    return s, col, loops, b


def _step(t0: int, **over):
    return lambda k: _design(**(over if k >= t0 else {}))


def _manual(v1_name, name, op):
    def before(s, col, loops):
        getattr(s, v1_name).update(mode="MAN", op=op)
        loop = _loop(loops, name)
        loop.set_mode("MAN")
        loop.op = op
    return before


def _set_point(v1_name, name, sp):
    def before(s, col, loops):
        getattr(s, v1_name)["sp"] = sp
        _loop(loops, name).sp = sp
    return before


def _both_manual(*pairs):
    def before(s, col, loops):
        for p in pairs:
            _manual(*p)(s, col, loops)
    return before


RICH_749 = dict(t.W_S747)
RICH_749["NH3"] = 2.0 * t.W_S747["NH3"]
RICH_749["H2O"] = t.W_S747["H2O"] - t.W_S747["NH3"]

STEAM_LOST = (("FFIC_329401", "ffic_329401", 0.0), ("FIC_329401", "fic_329401", 0.0))

SCENARIOS = {
    "design hold": (lambda k: _design(), 600, DT, None),
    "749 cut a fifth": (_step(10, m749=0.8 * t.C004_M749_DES_KGH), 1200, 0.5, None),
    "749 5 K colder": (_step(10, t749=t.C004_T749_C - 5.0), 1200, 0.5, None),
    "735 cut a fifth: the steam follows": (_step(10, m735=0.8 * M735_DES_KGH), 1200, 0.5, None),
    "328C002 at 4.2 bar a": (_step(10, pc002=4.2), 1200, 0.5, None),
    "FFIC-329401 to 0.25 t/m3": (lambda k: _design(), 1200, 0.5,
                                 _set_point("FFIC_329401", "ffic_329401", 0.25)),
    "FV-329401 in MAN at 30 %": (lambda k: _design(), 1200, 0.5,
                                 _manual("FIC_329401", "fic_329401", 30.0)),
    "LV-328505 in MAN at 80 %": (lambda k: _design(), 1200, 0.5,
                                 _manual("LIC_328505", "lic_328505", 80.0)),
    "a 749 twice as rich in NH3": (_step(10, w749=RICH_749), 1200, 0.5, None),
    "the LP header at 4.5 bar a": (_step(10, plp=4.5), 1200, 0.5, None),
    "the LP header at 4.1 bar a": (_step(10, plp=4.1), 1200, 0.5, None),
    "the LP steam lost, 749 at 130 C": (_step(10, t749=130.0), 1200, 0.5,
                                        _both_manual(*STEAM_LOST)),
    "LV-328505 wide open: the heel": (lambda k: _design(), 1200, 0.5,
                                      _manual("LIC_328505", "lic_328505", 100.0)),
    "every inlet lost": (_step(10, m749=0.0), 1200, 0.5, _both_manual(*STEAM_LOST)),
}


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_the_column_tick_by_tick(v1, name):
    script, ticks, dt, before = SCENARIOS[name]
    _run(v1, script, ticks, dt, before)


#: The scenarios where the duty stays positive and neither limit binds, run on V1's lines for
#: B-42 and both limits, on decision 24's books: the three switches are inert there.
INERT = ["design hold", "749 cut a fifth", "749 5 K colder", "735 cut a fifth: the steam follows",
         "328C002 at 4.2 bar a", "FFIC-329401 to 0.25 t/m3", "FV-329401 in MAN at 30 %",
         "LV-328505 in MAN at 80 %", "a 749 twice as rich in NH3"]


@pytest.mark.parametrize("name", INERT)
def test_the_three_departures_are_inert_where_they_do_not_act(v1, name):
    script, ticks, dt, before = SCENARIOS[name]
    s, col, loops, b = _run(v1, script, ticks, dt, before, decided=ON_BOOKS)
    assert not b.drain_lost and b.m_overflow_kgh == 0.0 and b.gen_kgh > 0.0


# --------------------------------------------------------------------------------------
# The flowsheet: 749 same-tick from 328C003, 750 back to 328C002 as a tear
# --------------------------------------------------------------------------------------

def test_749_is_same_tick_and_750_and_739_the_tears():
    fs = Flowsheet()
    for tag in ("328D003", "328E007", "328C002", "328C003", "328C004"):
        fs.add_unit(Unit(tag, tag, tag[:3]))
    fs.connect(Connection("735", "328D003", "328E007"))
    fs.connect(Connection("738", "328E007", "328C002"))
    fs.connect(Connection("743", "328C002", "328C003"))
    fs.connect(Connection("749", "328C003", "328C004"))
    fs.connect(Connection("750", "328C004", "328C002"))
    fs.connect(Connection("739", "328C004", "328E007"))
    with pytest.raises(CyclicFlowsheetError):
        fs.evaluation_order()
    for name, src, dst in (("R328_750", "328C004", "328C002"), ("R328_739", "328C004", "328E007")):
        fs.tear(Tear(name, src, (dst,), "V1 steps the consumer first; read a tick late"))
    assert fs.evaluation_order() == ("328D003", "328E007", "328C002", "328C003", "328C004")


def test_the_desorber_takes_749_on_the_same_tick(v1):
    """V1's 328C002, 328C003 and 328C004 in V1's order against the three ported columns: the
    desorber takes the hydrolyser's 747 and 328E021's 749 of THIS tick; 328C002 takes 750 and
    748 a tick late, the hydrolyser 328C004's pressure a tick late. A feed cut and then an MP
    steam step move every hand-off."""
    s = _v1_state(v1)
    col2, lic2 = fd.FirstDesorber(taps=False, l2_stop=False), fd.lic_328503(taps=False)
    col3, loops3 = hy.Hydrolyser(), hy.HydrolyserLoops()
    col4, loops4 = sd.SecondDesorber(taps=False, fv_329401=sd.V1_FV_329401, l2_stop=False), sd.SecondDesorberLoops(fic_329401=sd.fic_329401(sd.V1_FV_329401),
                                         lic_328505=sd.lic_328505(taps=False))
    m748, y748 = t.C002_M748_DES_KGH, dict(t.DES_C003.y)
    m750, y750 = t.C002_M750_DES_KGH, dict(t.DES_C004.y)
    seen = set()
    for k in range(3000):
        m738 = t.C002_M738_DES_KGH * (0.85 if k >= 10 else 1.0)
        if k == 1500:
            s.FIC_329402["sp"] = loops3.fic_329402.loop.sp = 900.0
        x2 = c002_eq._design(m738=m738, m748=m748, y748=y748, m750=m750, y750=y750,
                             tc003=s.a328_c003_T, pc003=s.a328_c003_P)
        s.tlag["R328_775"], s.a328_d001_P = x2["m775"], x2["pd001"]
        a2 = c002_eq._v1_c002(v1, s, x2["m738"], x2["t738"], DT)
        a3 = c003_eq._v1_c003(v1, s, a2["743"], DT)
        a4 = _v1_c004(v1, s, a3["747"], a3["749T"], DT)
        b2 = col2.step(lic2, x2["m738"], x2["t738"], m748, dict(y748), m750, dict(y750),
                       x2["m775"], col3.p_bara, x2["pd001"], DT)
        b3 = col3.step(loops3, b2.m_743_kgh, b2.w, b2.t_c, b2.p_bara, col4.p_bara, DT)
        b4 = col4.step(loops4, b3.m_747_kgh, b3.t_749_c, b3.w, M735_DES_KGH, b2.p_bara,
                       DECIDED_T740_DES, DT)
        m748, y748 = b3.m_748_kgh, dict(b3.y_748)
        m750, y750 = b4.m_750_kgh, dict(b4.y_750)
        c002_eq._assert_tick(a2, b2, s, col2, lic2, f"328C002, tick {k}")
        c003_eq._assert_tick(a3, b3, s, col3, loops3, f"328C003, tick {k}")
        _assert_tick(a4, b4, s, col4, loops4, f"328C004, tick {k}")
        seen.add(b4.m_750_kgh)
    assert len(seen) > 100


# --------------------------------------------------------------------------------------
# The departures, both sides
# --------------------------------------------------------------------------------------

def _both(v1, script, ticks, dt, before, v1_decided):
    """V1 with `v1_decided` against the port: the tick they part, the tick each of the port's
    flags first rises, each side's liquid books on what boils, and both sides at the end."""
    s = _v1_state(v1, v1_decided)
    col, loops = sd.SecondDesorber(taps=False, fv_329401=sd.V1_FV_329401, l2_stop=False), sd.SecondDesorberLoops(fic_329401=sd.fic_329401(sd.V1_FV_329401),
                                         lic_328505=sd.lic_328505(taps=False))
    if before:
        before(s, col, loops)
    out = SimpleNamespace(parted=None, first={}, made_v1=0.0, made=0.0, s=s, col=col, a=None,
                          b=None, loops=loops)
    for k in range(ticks):
        x = script(k)
        _feed(s, x)
        v1_pre, pre = s.a328_c004_M, col.m_kg
        a = _v1_c004(v1, s, x["m749"], x["t749"], dt, v1_decided)
        b = _port(col, loops, x, dt)
        out.made_v1 += s.a328_c004_M - v1_pre - (a["in"] - a["gen"] - a["739"]
                                                 - a["over"]) * dt / 3600.0
        out.made += col.m_kg - pre - (b.in_kgh - b.gen_kgh - b.m_739_kgh
                                      - b.m_overflow_kgh) * dt / 3600.0
        if out.parted is None:
            try:
                _assert_tick(a, b, s, col, loops, f"tick {k}")
            except AssertionError:
                out.parted = k
        for key, flag in (("lost", b.drain_lost), ("over", b.m_overflow_kgh > 0.0),
                          ("condensing", b.gen_kgh < 0.0)):
            if flag:
                out.first.setdefault(key, k)
        out.a, out.b = a, b
    return out
