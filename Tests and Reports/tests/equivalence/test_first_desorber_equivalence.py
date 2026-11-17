"""V1 <-> V1.1 equivalence for 328C002, desorber I.

What is being proved
--------------------
V1 writes the column inline in `step_sim`, so its statements are TRANSCRIBED into `_v1_c002`
below, line for line, and declared as such: the aqueous cp (``main.py`` 8828), the three tear
reads (8838-8840) and the stage itself (8965-9060). Everything they call is V1's own code,
executed: ``_ctrl_ipd``, ``aqueous_cp``, ``tsat_steam``, ``liquor_pv_bara``, ``des_alpha_live``
and ``des_advance`` lifted out of ``main.py`` with every constant they read; ``hydraulics``,
``thermo_service`` and ``iapws_if97`` loaded as real modules. V1 completes ``DES_STAGES`` in a
module-level loop, which lifting cannot reach; its four lines are transcribed into the fixture.
The state is seeded as ``State.__init__`` seeds it (6639-6640, 6841-6843, 6859-6869, 7089-7092).

The column is driven alone through scenarios chosen to take every branch — the stripping vapour
lost and raised, the reflux doubled, the feed cut and hotter, the drum and the hydrolyser moved,
LIC-328503 in MAN both ways and on a new set point, a richer hydrolyser overhead, every inlet
lost — and last coupled to V1's 328D003 and 328E007 in V1's order: 738 and its temperature
same-tick, the three recycles tears. Every tick compares every published field, the state, the
species and the controller with ``==``.

The decided divergences
-----------------------
Six departures, each a switch in the transcription: ``decided`` names the departures whose port
lines stand in V1's, and the empty set is V1 verbatim. Three were decided by the process
engineer on 2026-09-30 — the liquid loses what boils where V1 takes the overhead line's flow out
of it (decision 24, decided on 328C003 and retro-fitted here), a negative duty condenses vapour
where V1 clamps the boil-up at zero (handoff B-42), and LV-328503's flash choke reads the liquor
at the bottoms' temperature where V1 reads 328E021's cold outlet (handoff B-43) — and two apply
decision 11's standing rule: 328P006 capped at the heel, and a full shell overflowing; and
"relief", SV32850 and SV32851 venting the head space between their set and reseat pressures
(handoff B-47, decided 2026-09-30), the law written out in `decided_relief`. Every
scenario runs the port against the switched transcription; those that reach none of the last
four also run on V1's lines for them; and each departure runs both ways — bit-exact to the tick
it first acts, then V1's behaviour asserted on V1's side and the port's on the port's.
"""

from __future__ import annotations

import math

import pytest

from ureasim.core.flowsheet import Connection, CyclicFlowsheetError, Flowsheet, Tear, Unit
from ureasim.core.node import vapour_volume_m3
from ureasim.core.units_of_measure import ABSOLUTE_ZERO_C, PA_PER_BAR, R_GAS_J
from ureasim.data import desorption_train as t
from ureasim.data import unit_328c002 as c
from ureasim.data.unit_328c003 import C003_T_C
from ureasim.data import unit_328d003 as d
from ureasim.units.desorption import ammonia_water_tank as awt
from ureasim.units.desorption import feed_effluent_interchanger as fei
from ureasim.thermo.domains import MW
from ureasim.thermo.urea_liquor import SOLUTION_SPECIES
from ureasim.units.desorption import first_desorber as fd
from tests.equivalence import test_ammonia_water_tank_equivalence as tank_eq
from tests.equivalence import decided_relief as dr
from tests.equivalence import decided_valves as dv
from ureasim.data import control_valves_fisher as fv
from tests.equivalence import test_feed_effluent_interchanger_equivalence as e007_eq
from tests.equivalence.v1_loader import lift, load, v1_available, v1_service

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

C002_NAMES = [
    "R328_C002_M738_DES", "R328_C002_M748_DES", "R328_C002_M750_DES", "R328_C002_M775_DES",
    "R328_C002_IN_DES", "R328_C002_PHI737", "R328_C002_M737_DES", "R328_C002_M743_DES",
    "R328_C002_T_BOT_BOT", "R328_C002_T_BOT_TOP", "R328_C002_T_BOT738", "R328_C002_T_BOT748",
    "R328_C002_T_BOT750", "R328_D001_T", "R328_C002_LAM748", "R328_C002_LAM750",
    "R328_C002_SENS", "R328_C002_Q_DES", "R328_C002_ID_M", "R328_C002_SHELL_M",
    "R328_C002_VOL_M3", "R328_C002_NTRAY", "R328_C002_H_NLL", "R328_C002_RHO", "R328_C002_M_DES",
    "R328_C002_DT_TOP", "R328_C002_P_TOP", "R328_C002_DP_COL", "R328_C002_AREA_M2",
    "R328_P006_SUCT_DES_BARA", "R328_P006_DP_PUMP_BAR", "R328_C002_H_DES_M", "R328_P006_Z_DROP_M",
    "R328_LV503_P1_DES", "R328_LV503_OP_DES", "R328_LV_CHAR", "R328_LV503_T_IN_DES",
    "R328_LV503_PV_DES", "R328_E021_EPS_T", "R328_C003_T", "R328_C003_P_BARA",
    "R328_D001_P_BARA", "R328_M737_MW_DES", "R328_CP", "R328_COL_ID", "R328_COL_AREA",
    "R328_TRAY_DC_W", "R328_TRAY_ACTIVE", "R328_TRAY_HWEIR", "R328_FROTH_PHI", "R328_C004_NTRAY",
    "R328_AI701_KINF_C004", "R328_AI701_NTHEO_C004", "R328_TRAY_EO", "R328_NTHEO_C002",
    "R328_C003_M746_DES", "R328_C003_M911_DES", "R328_C003_IN_DES", "R328_C003_PHI748",
    "R328_C003_M748_DES", "R328_C003_M747_DES", "R328_C004_M749_DES", "R328_C004_M931_DES",
    "R328_C004_IN_DES", "R328_C004_PHI750", "R328_C004_M750_DES", "R328_C004_M739_DES",
    "W_S738", "W_S775", "W_S743", "W_S747", "W_S739", "W_S737", "W_S748", "W_S750", "W_STEAM",
    "DES_C003", "DES_C004", "DES_C002", "DES_STAGES", "DES_HYD_NU", "R328_KR_T_LO_C",
    "R328_KR_T_HI_C", "DES_VLE_DOMAIN", "des_alpha_live", "des_advance", "des_rel_vol_ratio",
    "liquor_pv_bara", "tsat_steam", "psat_water_bara", "aqueous_cp", "MW_SOL", "SOL_SPECIES",
    "_ctrl_ipd", "_kremser_resid", "_des_kfac", "_w_from_molepct", "_des_stage_anchor", "_mw_of",
]

#: V1's namespaces for 328D003 and 328E007, built as their own equivalence tests build them.
tank_v1 = tank_eq.v1
e007_v1 = e007_eq.v1

DT = 0.1

#: The departures the transcription can switch on: decision 24, B-42, B-43, decision 11's two
#: limits, B-47's relief and "valve", LV-328503 on Fisher's trim (decision 150).
ALL = frozenset({"vapour", "B-42", "B-43", "heel", "overflow", "relief", "valve"})
V1_VERBATIM = frozenset()
#: Decision 24: V1's lines for B-42 and decision 11's two limits. The liquid's books differ from
#: V1's in every transient, so the inert scenarios run on it — and on the valve, which every
#: transient moves, and on B-43, whose 190 C choke binds V1's line on Fisher's lower FL.
VAPOUR = frozenset({"vapour", "relief", "valve", "B-43"})
#: The three process-engineer decisions on both sides, so a limit's test sees only its own line.
DECIDED_2026_09_30 = frozenset({"vapour", "B-42", "B-43", "relief", "valve"})

#: LV-328503 as decided (decision 150), re-derived from Fisher's sheet: its design stroke [%] on
#: the IEC 50:1 equal percentage, its trim and FL.
DECIDED_LV503_OP = dv.design_stroke_pct(fv.LV_328503, t.C002_M743_DES_KGH)
DECIDED_LV503_FL = 0.819

#: SV32850 and SV32851 as decided (B-47), written from their sheets: set 5.0 bar g on 1.010 bar a
#: (Uhde UD-RL-328-EC-0001, -0002), reseating 10 % of set below; each 25 000 kg/h of gas, M 18.0
#: and Z 0.99, at 159 C and set plus 10 % (Sempell, UD-RL-G00-DZ-0002-001 page 5); two alike.
SV32850 = dr.Valve(5.0 + 1.010, 5.0 + 1.010 - 0.1 * 5.0, 5.0 + 1.010 + 0.1 * 5.0, 25000.0,
                   159.0 + 273.15, 18.0, 0.99, k=1.310, count=2)


@pytest.fixture(scope="module")
def v1(e007_v1):
    ns = dict(e007_v1)
    seed = {"math": math, "thermo_service": v1_service(),
            "iapws_if97": load("iapws_if97"), "hydraulics": load("hydraulics")}
    ns.update(lift(C002_NAMES, seed=seed))
    # main.py 3168-3175: the module-level loop that completes DES_STAGES, TRANSCRIBED.
    for st in ns["DES_STAGES"].values():
        st["S"] = ns["R328_AI701_KINF_C004"] * (st["V"] / st["L"])
        st["r"] = ns["_kremser_resid"](st["S"], st["N"])
        st["k"] = ns["_des_kfac"](st["L"], st["V"], st["r"])
        st["T_eq"] = ns["tsat_steam"](st["P"])
    return ns


def _v1_state(v1, decided=ALL):
    """The V1 plant-state fields 328C002 reads and writes, seeded as `State.__init__` seeds them
    (``main.py`` 6639-6640, 6841-6843, 6849-6852, 6859-6869, 7089-7092); "valve" in `decided`
    seeds LIC-328503 on the decided stroke."""
    g = v1
    s = tank_eq._v1_state(v1)
    s.y_328_737 = dict(g["DES_C002"]["y"])
    s.a328_c002_T_prev = g["R328_C002_T_BOT_BOT"]
    s.a328_c002_M = g["R328_C002_M_DES"]
    s.a328_c002_T = g["R328_C002_T_BOT_BOT"]
    s.a328_c002_P = g["R328_C002_P_TOP"]
    s.sv_32850_lifted = False
    s.a328_d001_P = g["R328_D001_P_BARA"]
    s.a328_c003_T = g["R328_C003_T"]
    s.a328_c003_P = g["R328_C003_P_BARA"]
    s.w_328c002 = dict(g["W_S743"])
    s.y_328_748 = dict(g["DES_C003"]["y"])
    s.y_328_750 = dict(g["DES_C004"]["y"])
    s.LIC_328503 = {"mode": "AUTO", "op": 50.0, "sp": 50.0, "pv": 50.0, "pv1": 50.0, "pv2": 50.0,
                    "Kc": 1.5, "Ti": 180.0, "Td": 0.0, "act": -1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0, "sp_hi": 100.0}
    if "valve" in decided:
        s.LIC_328503["op"] = DECIDED_LV503_OP
    return s


def _v1_c002(v1, s, m_738, T_738, dt, decided=ALL):
    """V1 `main.py` 8828, 8838-8840 and 8965-9060, stage 3, TRANSCRIBED line for line; each
    departure in `decided` puts the port's lines in V1's: the choke at the bottoms' temperature
    ("B-43"), the unclamped boil-up ("B-42"), the heel and the overflow (decision 11)."""
    g = v1
    hydraulics = g["hydraulics"]
    MW_SOL, SOL_SPECIES = g["MW_SOL"], g["SOL_SPECIES"]
    cp_328c002 = g["aqueous_cp"](g["R328_CP"], g["R328_C002_T_BOT_BOT"], s.a328_c002_T)
    m748_prev = s.tlag.get("R328_748", g["R328_C002_M748_DES"])
    m750_prev = s.tlag.get("R328_750", g["R328_C002_M750_DES"])
    m775_prev = s.tlag.get("R328_775", g["R328_C002_M775_DES"])
    Tc002 = s.a328_c002_T
    in_c002 = m_738 + m748_prev + m750_prev + m775_prev
    lvl_c002 = s.a328_c002_M / g["R328_C002_M_DES"] * 50.0
    _mw737_live = 1.0 / max(sum(s.y_328_737.get(k, 0.0) / MW_SOL[k] for k in SOL_SPECIES), 1e-12)
    lic503_op = g["_ctrl_ipd"](s.LIC_328503, lvl_c002, dt)
    _h_c002 = s.a328_c002_M / (g["R328_C002_RHO"] * g["R328_C002_AREA_M2"])
    _p1_503 = (s.a328_c002_P
               + g["R328_C002_RHO"] * 9.80665 * (_h_c002 + g["R328_P006_Z_DROP_M"]) / 1.0e5
               + g["R328_P006_DP_PUMP_BAR"])
    _t746_in = s.a328_c002_T + g["R328_E021_EPS_T"] * (s.a328_c003_T - s.a328_c002_T)
    pv, pv_des = g["liquor_pv_bara"](s.w_328c002, _t746_in), g["R328_LV503_PV_DES"]
    if "B-43" in decided:  # ---- the liquor at the valve is the bottoms (the port's lines) ----
        pv = g["liquor_pv_bara"](s.w_328c002, s.a328_c002_T)
        pv_des = g["liquor_pv_bara"](g["W_S743"], g["R328_C002_T_BOT_BOT"])
    op_des, char, fl = g["R328_LV503_OP_DES"], g["R328_LV_CHAR"], hydraulics.FL_GLOBE
    if "valve" in decided:  # ---- LV-328503 on Fisher's trim (the port's valve) ----
        op_des, char, fl = DECIDED_LV503_OP, "equal_pct", DECIDED_LV503_FL
    m_743 = hydraulics.valve_liquid_anchored(
        g["R328_C002_M743_DES"], lic503_op / 100.0, _p1_503, s.a328_c003_P, g["R328_C002_RHO"],
        op_des / 100.0, g["R328_LV503_P1_DES"], g["R328_C003_P_BARA"],
        g["R328_C002_RHO"], characteristic=char, fl=fl, pv_bara=pv, pv_des_bara=pv_des)
    sens_c002 = ((m_738 * (T_738 - Tc002)
                  + m775_prev * (g["R328_D001_T"] - Tc002)
                  + m748_prev * (g["R328_C002_T_BOT748"] - Tc002)
                  + m750_prev * (g["R328_C002_T_BOT750"] - Tc002)) / 3600.0 * cp_328c002)
    q_c002 = (sens_c002 + m748_prev / 3600.0 * g["R328_C002_LAM748"]
              + m750_prev / 3600.0 * g["R328_C002_LAM750"])
    gen737 = max(g["R328_C002_M737_DES"] * (q_c002 / g["R328_C002_Q_DES"]), 0.0)
    if "B-42" in decided:  # ---- a negative duty condenses vapour (the port's line) ----
        gen737 = g["R328_C002_M737_DES"] * (q_c002 / g["R328_C002_Q_DES"])
    _t737_k = s.a328_c002_T - g["R328_C002_DT_TOP"] + 273.15
    m_737 = hydraulics.valve_gas_anchored(
        g["R328_C002_M737_DES"], 1.0, s.a328_c002_P, s.a328_d001_P, _t737_k,
        1.0, g["R328_C002_P_TOP"], g["R328_D001_P_BARA"], g["R328_C002_T_BOT_TOP"] + 273.15,
        _mw737_live, characteristic="linear", mw_des=g["R328_M737_MW_DES"])
    # ---- decision 24: the liquid loses what boils (the port's lines), V1's the vent ----
    boil = gen737 if "vapour" in decided else m_737
    lost, over = False, 0.0
    if "heel" in decided:  # ---- the decided heel (the port's lines) ----
        avail = max(max(s.a328_c002_M - 1.0, 0.0) / max(dt, 1e-9) * 3600.0 + in_c002 - boil, 0.0)
        lost = m_743 > avail
        if lost:
            m_743 = avail
    M_c002_pre = s.a328_c002_M
    if "overflow" in decided:  # ---- the decided overflow (the port's lines) ----
        full = g["R328_C002_VOL_M3"] * g["R328_C002_RHO"]
        m_new = max(M_c002_pre + (in_c002 - boil - m_743) / 3600.0 * dt, 1.0)
        if m_new > full:
            over = (m_new - full) / max(dt, 1e-9) * 3600.0
    _vv_c002 = hydraulics.vapour_volume_m3(g["R328_C002_VOL_M3"], M_c002_pre, g["R328_C002_RHO"])
    _dmdt_c002 = (in_c002 - boil - m_743 - over) / 3600.0
    _T_c002_pre = s.a328_c002_T
    _p_free = s.a328_c002_P + hydraulics.vessel_dpdt(
        s.a328_c002_P, s.a328_c002_T + 273.15, _vv_c002, _mw737_live,
        gen737 / _mw737_live, m_737 / _mw737_live,
        dtdt_k_s=(s.a328_c002_T - s.a328_c002_T_prev) / dt,
        dvvdt_m3_s=-_dmdt_c002 / g["R328_C002_RHO"]) * dt
    relief = 0.0
    if "relief" in decided:  # ---- B-47: SV32850 and SV32851 (the port's lines) ----
        relief, s.sv_32850_lifted = dr.vent(
            g, SV32850, s.a328_c002_P, _p_free, s.a328_c002_T + 273.15, _mw737_live, _vv_c002,
            dt, s.sv_32850_lifted)
        if relief > 0.0:
            _p_free += hydraulics.vessel_dpdt(
                s.a328_c002_P, s.a328_c002_T + 273.15, _vv_c002, _mw737_live, 0.0,
                relief / _mw737_live) * dt
    s.a328_c002_P = max(_p_free, 0.1)
    s.a328_c002_T_prev = _T_c002_pre
    s.a328_c002_T = g["tsat_steam"](s.a328_c002_P + g["R328_C002_DP_COL"])
    s.a328_c002_M = max(M_c002_pre + (in_c002 - boil - m_743) / 3600.0 * dt, 1.0)
    if over:
        s.a328_c002_M = full
    a_c002 = g["des_alpha_live"]("C002", s.a328_c002_T, m748_prev + m750_prev, m_743,
                                 s.w_328c002, s.a328_c002_P + g["R328_C002_DP_COL"])
    s.w_328c002, y_737 = g["des_advance"](s.w_328c002, s.a328_c002_M,
                                          [(g["W_S738"], m_738), (g["W_S775"], m775_prev),
                                           (s.y_328_748, m748_prev), (s.y_328_750, m750_prev)],
                                          boil, a_c002, m_743 + over, 0.0, dt)
    s.y_328_737 = y_737
    return {"in": in_c002, "lvl": lvl_c002, "lic": lic503_op, "743": m_743, "lost": lost,
            "over": over, "relief": relief, "lifted": s.sv_32850_lifted,
            "q": q_c002, "gen": gen737, "737": m_737, "domain": g["DES_VLE_DOMAIN"].get("C002"),
            # main.py 10752-10763, the telemetry.
            "TT_328008": s.a328_c002_T - g["R328_C002_DT_TOP"],
            "LI_328503": s.a328_c002_M / g["R328_C002_M_DES"] * 50.0}


def _assert_tick(a: dict, b: fd.FirstDesorberResult, s, col, lic, label):
    assert (a["in"], a["lvl"], a["lic"], a["743"], a["lost"], a["q"], a["gen"], a["737"],
            a["over"]) == (b.in_kgh, b.lic_pv_pct, b.lic_op_pct, b.m_743_kgh, b.suction_lost,
                           b.q_kw, b.gen_kgh, b.m_737_kgh, b.m_overflow_kgh), label
    assert (a["relief"], a["lifted"]) == (b.m_relief_kgh, b.relief_lifted), label
    assert (s.a328_c002_P, s.a328_c002_T, s.a328_c002_T_prev, s.a328_c002_M) == (
        col.p_bara, col.t_c, col.t_prev_c, col.m_kg), label
    assert (b.p_bara, b.t_c, b.m_kg, b.t_top_c, b.level_pct) == (
        col.p_bara, col.t_c, col.m_kg, a["TT_328008"], a["LI_328503"]), label
    assert (s.w_328c002, s.y_328_737) == (col.w, col.y_737) == (b.w, b.y_737), label
    assert a["domain"] == b.vle_domain, label
    v1c = s.LIC_328503
    assert (v1c["op"], v1c["sp"], v1c["pv"], v1c["pv1"], v1c["pv2"], v1c["mode"]) == (
        lic.op, lic.sp, lic.pv, lic.pv1, lic.pv2, lic.mode), label


# --------------------------------------------------------------------------------------
# The design basis
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("module, ours, theirs", [
    (t, "C002_M738_DES_KGH", "R328_C002_M738_DES"), (t, "C002_M748_DES_KGH", "R328_C002_M748_DES"),
    (t, "C002_M750_DES_KGH", "R328_C002_M750_DES"), (t, "C002_M775_DES_KGH", "R328_C002_M775_DES"),
    (t, "C002_IN_DES_KGH", "R328_C002_IN_DES"), (t, "C002_PHI737", "R328_C002_PHI737"),
    (t, "C002_M737_DES_KGH", "R328_C002_M737_DES"), (t, "C002_M743_DES_KGH", "R328_C002_M743_DES"),
    (t, "C002_T_BOT_C", "R328_C002_T_BOT_BOT"), (t, "C002_T_TOP_C", "R328_C002_T_BOT_TOP"),
    (t, "C002_T738_DES_C", "R328_C002_T_BOT738"), (t, "C002_T748_C", "R328_C002_T_BOT748"),
    (t, "C002_T750_C", "R328_C002_T_BOT750"), (t, "C002_P_TOP_BARA", "R328_C002_P_TOP"),
    (t, "C003_M746_DES_KGH", "R328_C003_M746_DES"), (t, "C003_M911_DES_KGH", "R328_C003_M911_DES"),
    (t, "C003_IN_DES_KGH", "R328_C003_IN_DES"), (t, "C003_PHI748", "R328_C003_PHI748"),
    (t, "C003_M748_DES_KGH", "R328_C003_M748_DES"), (t, "C003_M747_DES_KGH", "R328_C003_M747_DES"),
    (t, "C003_P_BARA", "R328_C003_P_BARA"), (t, "C004_M749_DES_KGH", "R328_C004_M749_DES"),
    (t, "C004_M931_DES_KGH", "R328_C004_M931_DES"), (t, "C004_IN_DES_KGH", "R328_C004_IN_DES"),
    (t, "C004_PHI750", "R328_C004_PHI750"), (t, "C004_M750_DES_KGH", "R328_C004_M750_DES"),
    (t, "C004_M739_DES_KGH", "R328_C004_M739_DES"), (t, "D001_T_C", "R328_D001_T"),
    (t, "D001_P_BARA", "R328_D001_P_BARA"),
    (t, "COL_ID_M", "R328_COL_ID"), (t, "COL_AREA_M2", "R328_COL_AREA"),
    (t, "TRAY_DC_W_M", "R328_TRAY_DC_W"), (t, "TRAY_ACTIVE_M2", "R328_TRAY_ACTIVE"),
    (t, "TRAY_WEIR_M", "R328_TRAY_HWEIR"), (t, "FROTH_PHI", "R328_FROTH_PHI"),
    (t, "C002_NTRAY", "R328_C002_NTRAY"), (t, "C004_NTRAY", "R328_C004_NTRAY"),
    (t, "KINF", "R328_AI701_KINF_C004"), (t, "C004_NTHEO", "R328_AI701_NTHEO_C004"),
    (t, "TRAY_EO", "R328_TRAY_EO"), (t, "C002_NTHEO", "R328_NTHEO_C002"),
    (t, "CP_DESORPTION", "R328_CP"),
    (t, "W_S738", "W_S738"), (t, "W_S775", "W_S775"), (t, "W_S743", "W_S743"),
    (t, "W_S747", "W_S747"), (t, "W_S739", "W_S739"), (t, "W_S737", "W_S737"),
    (t, "W_S748", "W_S748"), (t, "W_S750", "W_S750"), (t, "W_STEAM", "W_STEAM"),
    (c, "C002_ID_M", "R328_C002_ID_M"), (c, "C002_SHELL_M", "R328_C002_SHELL_M"),
    (c, "C002_VOL_M3", "R328_C002_VOL_M3"), (c, "C002_H_NLL_M", "R328_C002_H_NLL"),
    (c, "C002_RHO_KGM3", "R328_C002_RHO"), (c, "C002_M_DES_KG", "R328_C002_M_DES"),
    (c, "C002_DT_TOP_K", "R328_C002_DT_TOP"), (c, "C002_DP_COL_BAR", "R328_C002_DP_COL"),
    (c, "C002_AREA_M2", "R328_C002_AREA_M2"), (c, "C002_LAM748_KJKG", "R328_C002_LAM748"),
    (c, "C002_LAM750_KJKG", "R328_C002_LAM750"), (c, "C002_SENS_DES_KW", "R328_C002_SENS"),
    (c, "C002_Q_DES_KW", "R328_C002_Q_DES"), (c, "C002_MW737_DES", "R328_M737_MW_DES"),
    (c, "P006_SUCT_DES_BARA", "R328_P006_SUCT_DES_BARA"),
    (c, "P006_DP_PUMP_BAR", "R328_P006_DP_PUMP_BAR"), (c, "C002_H_DES_M", "R328_C002_H_DES_M"),
    (c, "P006_Z_DROP_M", "R328_P006_Z_DROP_M"), (c, "LV503_P1_DES_BARA", "R328_LV503_P1_DES"),
])
def test_design_basis(v1, module, ours, theirs):
    assert getattr(module, ours) == v1[theirs]


def test_lv_328503_on_fishers_trim_decided(v1):
    """Decision 150: V1 runs LV-328503 linear from 50 % on the IEC globe FL 0.90, having no sheet;
    the port runs Fisher's (UD-MR-G00-DZ-0014, item 022): equal percentage, Cv 82.2, FL 0.819,
    from 56.95 %, where the rated Cv passes PFD 743 on the normal case."""
    assert (v1["R328_LV503_OP_DES"], v1["R328_LV_CHAR"], v1["hydraulics"].FL_GLOBE) == (
        50.0, "linear", 0.90)
    assert (c.LV503_OP_DES_PCT, c.LV503_CHARACTERISTIC, c.LV503_FL) == (
        pytest.approx(DECIDED_LV503_OP, rel=1e-12), "equal_pct", DECIDED_LV503_FL)
    assert c.LV503_OP_DES_PCT == pytest.approx(56.946, abs=1e-3)


def test_the_chokes_anchor_is_the_bottoms_decided(v1):
    """B-43, decided: V1 anchors LV-328503's flash choke on the liquor at 328E021's cold outlet,
    190 C and 14.97 bar a; the port on the bottoms, 139 C and 3.93 bar a — V1's own function."""
    assert (v1["R328_LV503_T_IN_DES"], v1["R328_LV503_PV_DES"]) == (
        pytest.approx(190.0, abs=1e-12), pytest.approx(14.9696, abs=1e-4))
    assert c.LV503_T_IN_DES_C == v1["R328_C002_T_BOT_BOT"]
    assert c.LV503_PV_DES_BARA == v1["liquor_pv_bara"](v1["W_S743"], v1["R328_C002_T_BOT_BOT"])
    assert c.LV503_PV_DES_BARA == pytest.approx(3.9349, abs=1e-4)


def test_739_is_the_tanks_own_float():
    assert t.C004_M739_DES_KGH == d.C004_M739_DES_KGH


@pytest.mark.parametrize("ours, theirs", [("DES_C003", "DES_C003"), ("DES_C004", "DES_C004"),
                                          ("DES_C002", "DES_C002")])
def test_the_three_anchors_are_v1s(v1, ours, theirs):
    a, b = getattr(t, ours), v1[theirs]
    assert (a.xi, a.y, a.alpha, a.resid, a.dev) == (b["xi"], b["y"], b["alpha"], b["resid"],
                                                   b["dev"])


def test_the_kremser_stage_is_v1s(v1):
    st, ours = v1["DES_STAGES"]["C002"], c.C002_STAGE
    assert (ours.n_theo, ours.v_kgh, ours.l_kgh, ours.p_bara, ours.s, ours.r, ours.k,
            ours.t_eq_c, ours.k_inf) == (st["N"], st["V"], st["L"], st["P"], st["S"], st["r"],
                                         st["k"], st["T_eq"], v1["R328_AI701_KINF_C004"])
    assert ours.anchor is t.DES_C002 and st["a"] is v1["DES_C002"]


def test_the_state_and_the_controller_are_seeded_as_v1_seeds_them(v1):
    s, col, lic = _v1_state(v1), fd.FirstDesorber(taps=False, l2_stop=False), fd.lic_328503(taps=False)
    assert (s.a328_c002_M, s.a328_c002_T, s.a328_c002_T_prev, s.a328_c002_P, s.w_328c002,
            s.y_328_737) == (col.m_kg, col.t_c, col.t_prev_c, col.p_bara, col.w, col.y_737)
    v1c = s.LIC_328503
    assert (v1c["mode"], v1c["op"], v1c["sp"], v1c["pv"], v1c["pv1"], v1c["pv2"], v1c["Kc"],
            v1c["Ti"], v1c["Td"], v1c["act"], v1c["op_lo"], v1c["op_hi"], v1c["sp_lo"],
            v1c["sp_hi"]) == (lic.mode, lic.op, lic.sp, lic.pv, lic.pv1, lic.pv2, lic.Kc,
                              lic.Ti, lic.Td, lic.act, lic.op_lo, lic.op_hi, lic.sp_lo,
                              lic.sp_hi)


# --------------------------------------------------------------------------------------
# The column on its own, tick by tick
# --------------------------------------------------------------------------------------

#: The hydrolyser's design temperature, V1's R328_C003_T: only V1 reads it, for the 190 C choke
#: the port retires (B-43).
V1_C003_T_C = 200.0


def _design(**over):
    base = {"m738": t.C002_M738_DES_KGH, "t738": t.C002_T738_DES_C,
            "m748": t.C002_M748_DES_KGH, "y748": dict(t.DES_C003.y),
            "m750": t.C002_M750_DES_KGH, "y750": dict(t.DES_C004.y),
            "m775": t.C002_M775_DES_KGH, "tc003": V1_C003_T_C, "pc003": t.C003_P_BARA,
            "pd001": t.D001_P_BARA}
    base.update(over)
    return base


def _feed(s, x):
    """Write a tick's boundaries into V1's tears and neighbouring states."""
    s.tlag["R328_748"], s.tlag["R328_750"], s.tlag["R328_775"] = x["m748"], x["m750"], x["m775"]
    s.y_328_748, s.y_328_750 = dict(x["y748"]), dict(x["y750"])
    s.a328_c003_T, s.a328_c003_P, s.a328_d001_P = x["tc003"], x["pc003"], x["pd001"]


def _port(col, lic, x, dt):
    return col.step(lic, x["m738"], x["t738"], x["m748"], dict(x["y748"]), x["m750"],
                    dict(x["y750"]), x["m775"], x["pc003"], x["pd001"], dt)


def _run(v1, script, ticks: int, before=None, decided=ALL):
    """Drive the column alone through `script(k)`, comparing everything every tick."""
    if "valve" not in decided:
        raise ValueError("the port runs LV-328503 on Fisher's trim; run V1's in its divergence")
    s, col, lic = _v1_state(v1, decided), fd.FirstDesorber(taps=False, l2_stop=False), fd.lic_328503(taps=False)
    if before:
        before(s, col, lic)
    b = None
    for k in range(ticks):
        x = script(k)
        _feed(s, x)
        a = _v1_c002(v1, s, x["m738"], x["t738"], DT, decided)
        b = _port(col, lic, x, DT)
        _assert_tick(a, b, s, col, lic, f"tick {k}")
    return s, col, lic, b


def _step(t0: int, **over):
    return lambda k: _design(**(over if k >= t0 else {}))


#: A hydrolyser overhead twice as rich in ammonia, renormalised.
_RICH = dict(t.DES_C003.y)
_RICH["NH3"] *= 2.0
Y748_RICH = {k: v / sum(_RICH.values()) for k, v in _RICH.items()}

SCENARIOS = {
    "design hold": (lambda k: _design(), 600),
    "the stripping vapour lost (748 and 750 stopped)": (_step(10, m748=0.0, m750=0.0), 3000),
    "750 up a fifth": (_step(10, m750=1.2 * t.C002_M750_DES_KGH), 3000),
    "the reflux doubled": (_step(10, m775=2.0 * t.C002_M775_DES_KGH), 3000),
    "the feed cut 30 %": (_step(10, m738=0.7 * t.C002_M738_DES_KGH), 3000),
    "the feed 11 K hotter": (_step(10, t738=125.0), 3000),
    "328D001 0.3 bar lower": (_step(10, pd001=2.3), 3000),
    "the hydrolyser 1.2 bar higher and 5 K hotter": (_step(10, pc003=18.0, tc003=205.0), 3000),
    "a hydrolyser overhead twice as rich in NH3": (_step(10, y748=Y748_RICH), 3000),
    "every inlet lost": (_step(10, m738=0.0, m748=0.0, m750=0.0, m775=0.0), 3000),
    "the hydrolyser depressured to 5 bar a, 750 up a fifth (LV-328503 flashes)": (
        _step(10, pc003=5.0, m750=1.2 * t.C002_M750_DES_KGH), 3000),
}


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_the_column_tick_by_tick(v1, name):
    script, ticks = SCENARIOS[name]
    s, col, lic, b = _run(v1, script, ticks)
    assert not b.suction_lost and b.m_overflow_kgh == 0.0


#: The scenarios where none of the four later departures acts: V1's lines for them, tick by tick,
#: on decision 24's books. B-42 acts where the net duty goes negative, B-43 where V1's choke at
#: 190 C binds — on a doubled reflux, after 100.6 s.
INERT = [name for name in SCENARIOS
         if name not in ("the stripping vapour lost (748 and 750 stopped)", "every inlet lost",
                         "the reflux doubled",
                         "the hydrolyser depressured to 5 bar a, 750 up a fifth "
                         "(LV-328503 flashes)")]


@pytest.mark.parametrize("name", INERT)
def test_the_departures_are_inert_where_they_do_not_act(v1, name):
    script, ticks = SCENARIOS[name]
    _run(v1, script, ticks, decided=VAPOUR)


def _manual(op):
    def before(s, col, lic):
        s.LIC_328503.update(mode="MAN", op=op)
        lic.set_mode("MAN")
        lic.op = op
    return before


def test_lv_328503_held_at_20_percent_fills_the_column(v1):
    s, col, lic, b = _run(v1, lambda k: _design(), 3000, before=_manual(20.0))
    assert b.level_pct > 60.0 and b.m_overflow_kgh == 0.0


def test_lic_328503_on_a_new_set_point(v1):
    def before(s, col, lic):
        s.LIC_328503["sp"] = lic.sp = 60.0
    s, col, lic, b = _run(v1, lambda k: _design(), 3000, before=before)
    assert b.level_pct > 50.5


# --------------------------------------------------------------------------------------
# The decided divergence, decision 11: 328P006 at the heel, both sides
# --------------------------------------------------------------------------------------

def test_the_pump_at_the_heel_the_port_against_its_transcription(v1):
    """LV-328503 held wide open: through the heel and on, the port is its transcription."""
    s, col, lic, b = _run(v1, lambda k: _design(), 6000, before=_manual(100.0))
    assert b.suction_lost and col.m_kg == pytest.approx(c.C002_M_FLOOR_KG, abs=1e-6)


def test_the_pump_at_the_heel_decided_divergence(v1):
    """V1 draws LV-328503's flow from an empty sump and its floor makes the liquid; the port
    caps 328P006 at the heel, flags it, and makes nothing. Decision 24, B-42 and B-43 stand on
    both sides, so the liquid's books are charged what boils."""
    s, col, lic = _v1_state(v1), fd.FirstDesorber(taps=False, l2_stop=False), fd.lic_328503(taps=False)
    _manual(100.0)(s, col, lic)
    made_v1 = made = 0.0
    parted = None
    for k in range(6000):
        x = _design()
        _feed(s, x)
        v1_pre, pre = s.a328_c002_M, col.m_kg
        a = _v1_c002(v1, s, x["m738"], x["t738"], DT, decided=DECIDED_2026_09_30)
        b = _port(col, lic, x, DT)
        if parted is None and not b.suction_lost:
            _assert_tick(a, b, s, col, lic, f"tick {k}")
            continue
        parted = k if parted is None else parted
        made_v1 += s.a328_c002_M - v1_pre - (a["in"] - a["gen"] - a["743"]) * DT / 3600.0
        made += col.m_kg - pre - (b.in_kgh - b.gen_kgh - b.m_743_kgh) * DT / 3600.0
    assert parted is not None
    assert made_v1 > 1.0
    assert abs(made) < 1e-9


def test_328p006s_low_level_stop_decided_divergence(v1):
    """Decision 217. LV-328503 wide open from the design seed, both sides alike until LT-328503
    first reads below its 5 % stand-in L2: there AC4 stops 328P006A and B on the port and 743 is
    nothing, where V1's pair runs on to the heel and its floor makes the liquid. The port runs
    again at 7 % and never reaches the heel."""
    s, col, lic = _v1_state(v1), fd.FirstDesorber(taps=False), fd.lic_328503(taps=False)
    _manual(100.0)(s, col, lic)
    made_v1 = made = 0.0
    parted = restart = None
    for k in range(6000):
        x = _design()
        _feed(s, x)
        v1_pre, pre = s.a328_c002_M, col.m_kg
        a = _v1_c002(v1, s, x["m738"], x["t738"], DT, decided=DECIDED_2026_09_30)
        b = _port(col, lic, x, DT)
        if parted is None and not col.p006_stopped:
            _assert_tick(a, b, s, col, lic, f"tick {k}")
            continue
        if parted is None:
            parted = k
            assert a["743"] > 0.0 and b.m_743_kgh == 0.0
        if restart is None and not col.p006_stopped:
            restart = k
        assert not b.suction_lost, f"tick {k}"
        made_v1 += s.a328_c002_M - v1_pre - (a["in"] - a["gen"] - a["743"]) * DT / 3600.0
        made += col.m_kg - pre - (b.in_kgh - b.gen_kgh - b.m_743_kgh) * DT / 3600.0
    assert (parted, restart) == (349, 421)
    assert made_v1 > 1.0
    assert abs(made) < 1e-9


def test_li_328503_between_its_taps_decided_divergence(v1):
    """Decision 243 (handoff B-156's fourth unit), both sides. V1 reads LI-328503 as M / M_des x 50
    and holds 50 %; the port reads LT-328503 between N7B and N7A, 300 and 1500 mm above the
    partition (Uhde UD-AU-328-EC-0001 p. 6; EC-0134 p. 6), and holds the design holdup's 70.83 %.
    The design tick is V1's in everything but the reading; 738 cut 25 % at 1 s, each side reads its
    own law on its own holdup every tick, and each brings its holdup back to the design's."""
    s, col, lic = _v1_state(v1), fd.FirstDesorber(l2_stop=False), fd.lic_328503()
    dips = [col.m_kg, s.a328_c002_M]
    for k in range(18000):
        x = _design(m738=0.75 * t.C002_M738_DES_KGH) if k >= 10 else _design()
        _feed(s, x)
        a = _v1_c002(v1, s, x["m738"], x["t738"], DT, decided=ALL)
        b = _port(col, lic, x, DT)
        assert a["LI_328503"] == s.a328_c002_M / c.C002_M_DES_KG * 50.0, f"tick {k}"
        assert b.level_pct == c.lt_328503_pct(col.m_kg), f"tick {k}"
        if k == 0:
            assert (a["in"], a["743"], a["gen"], a["737"], a["q"]) == (
                b.in_kgh, b.m_743_kgh, b.gen_kgh, b.m_737_kgh, b.q_kw)
            assert (s.a328_c002_M, s.a328_c002_P, s.a328_c002_T) == (col.m_kg, col.p_bara, col.t_c)
            assert (a["lvl"], b.lic_pv_pct) == (50.0, c.LT_328503_DES_PCT)
        dips = [min(dips[0], col.m_kg), min(dips[1], s.a328_c002_M)]
    assert b.level_pct == pytest.approx(c.LT_328503_DES_PCT, abs=0.01)
    assert a["LI_328503"] == pytest.approx(50.0, abs=0.01)
    assert c.C002_M_DES_KG - dips[0] == pytest.approx(50.9, abs=0.1)
    assert c.C002_M_DES_KG - dips[1] == pytest.approx(103.0, abs=0.1)


# --------------------------------------------------------------------------------------
# Coupled: 328D003 -> 328E007 -> 328C002 as V1 steps them
# --------------------------------------------------------------------------------------

def test_738_is_same_tick_and_the_three_recycles_are_tears():
    """V1's order is legal only because 738 and 743 run forward. The recycles 748, 750 and 775
    close through columns V1 steps later, and are the declared tears."""
    fs = Flowsheet()
    for tag in ("328D003", "328E007", "328C002", "328C003", "328C004", "328D001"):
        fs.add_unit(Unit(tag, tag, tag[:3]))
    fs.connect(Connection("735", "328D003", "328E007"))
    fs.connect(Connection("738", "328E007", "328C002"))
    fs.connect(Connection("743", "328C002", "328C003"))
    fs.connect(Connection("747", "328C003", "328C004"))
    fs.connect(Connection("737", "328C002", "328D001"))
    fs.connect(Connection("748", "328C003", "328C002"))
    fs.connect(Connection("750", "328C004", "328C002"))
    fs.connect(Connection("775", "328D001", "328C002"))
    fs.connect(Connection("739", "328C004", "328E007"))
    with pytest.raises(CyclicFlowsheetError):
        fs.evaluation_order()
    for name, src, dst in (("R328_748", "328C003", "328C002"), ("R328_750", "328C004", "328C002"),
                           ("R328_775", "328D001", "328C002"), ("R328_739", "328C004", "328E007")):
        fs.tear(Tear(name, src, (dst,), "V1 steps the consumer first; read a tick late"))
    # V1's order, 328D003 -> 328E007 -> 328C002 -> 328C003 -> 328C004 -> 328D001, is one of the
    # orders the same-tick edges allow; 328D001 needs only 737.
    pos = {tag: i for i, tag in enumerate(fs.evaluation_order())}
    for up, down in (("328D003", "328E007"), ("328E007", "328C002"), ("328C002", "328C003"),
                     ("328C003", "328C004"), ("328C002", "328D001")):
        assert pos[up] < pos[down], (up, down)


def test_the_column_takes_738_on_the_same_tick(v1):
    """V1's 328D003, 328E007 and 328C002 in V1's order against the ported tank, exchanger and
    column: the column takes the exchanger's 738 and its temperature of THIS tick. The tank's
    condensates cut move 735; 328C004's temperature stepped moves 738's."""
    s = _v1_state(v1)
    tank, loops = awt.AmmoniaWaterTank(), awt.TankLoops()
    col, lic = fd.FirstDesorber(taps=False, l2_stop=False), fd.lic_328503(taps=False)
    t_c004 = d.D003_TII_C + 87.0
    for k in range(3000):
        if k == 1500:
            t_c004 = 139.0
        s.a328_c004_T = t_c004
        x2 = tank_eq._design(m719=0.8 * d.D003_M719_DES_KGH if k >= 10 else d.D003_M719_DES_KGH)
        tank_eq._feed(s, x2)
        a2 = tank_eq._v1_stage2(v1, s, x2["m343"], DT, decided=False)
        ae = e007_eq._v1_e007(v1, s, a2["735"], d.C004_M739_DES_KGH)
        x3 = _design(m738=ae["738"], t738=ae["T738"])
        _feed(s, x3)
        a3 = _v1_c002(v1, s, x3["m738"], x3["t738"], DT)
        b2 = tank_eq._port(tank, loops, x2, DT)
        be = fei.desorber_heat_exchanger(b2.m_735_kgh, b2.t_ii_c, d.C004_M739_DES_KGH, t_c004)
        b3 = _port(col, lic, _design(m738=be.m_738_kgh, t738=be.t_738_c), DT)
        tank_eq._assert_tick(a2, b2, s, tank, loops, f"328D003, tick {k}")
        assert (ae["738"], ae["T738"]) == (be.m_738_kgh, be.t_738_c), f"328E007, tick {k}"
        _assert_tick(a3, b3, s, col, lic, f"328C002, tick {k}")
    assert col.t_c != c.C002_STAGE.t_eq_c


# --------------------------------------------------------------------------------------
# The decided divergence, decision 11: a full shell, both sides
# --------------------------------------------------------------------------------------

def test_the_full_shell_the_port_against_its_transcription(v1):
    """LV-328503 held at 20 %: through the full shell and on, the port is its transcription."""
    s, col, lic, b = _run(v1, lambda k: _design(), 20000, before=_manual(20.0))
    assert b.m_overflow_kgh > 0.0 and col.m_kg == c.C002_FULL_KG


def test_the_full_shell_decided_divergence(v1):
    """V1's column goes on filling past its 12.85 m3 shell; the port's holds 11 988 kg and lets
    the rest go overhead as the overflow — bit-exact until the shell is full, at 1462.4 s (LV-328503
    held at 20 % on Fisher's equal percentage, decision 150), and
    on every tick after it the port's books close while V1 holds more than the shell.
    Decision 24, B-42 and B-43 stand on both sides."""
    s, col, lic = _v1_state(v1), fd.FirstDesorber(taps=False, l2_stop=False), fd.lic_328503(taps=False)
    _manual(20.0)(s, col, lic)
    parted = None
    for k in range(20000):
        x = _design()
        _feed(s, x)
        pre = col.m_kg
        a = _v1_c002(v1, s, x["m738"], x["t738"], DT, decided=DECIDED_2026_09_30)
        b = _port(col, lic, x, DT)
        if parted is None and b.m_overflow_kgh == 0.0:
            _assert_tick(a, b, s, col, lic, f"tick {k}")
            continue
        parted = k if parted is None else parted
        assert s.a328_c002_M > c.C002_FULL_KG and col.m_kg == c.C002_FULL_KG
        booked = col.m_kg - pre - (b.in_kgh - b.gen_kgh - b.m_743_kgh
                                   - b.m_overflow_kgh) * DT / 3600.0
        assert abs(booked) < 1e-9
    assert parted * DT == pytest.approx(1462.4, abs=1e-9)
    assert s.a328_c002_M / (c.C002_RHO_KGM3 * c.C002_VOL_M3) > 1.03


# --------------------------------------------------------------------------------------
# The decided divergences of 2026-09-30, B-42 and B-43: both sides
# --------------------------------------------------------------------------------------

def _both(v1, script, ticks, v1_decided):
    """V1 with `v1_decided` against the port: the tick they part, then both sides at the end."""
    s, col, lic = _v1_state(v1, v1_decided), fd.FirstDesorber(taps=False, l2_stop=False), fd.lic_328503(taps=False)
    parted = a = b = None
    for k in range(ticks):
        x = script(k)
        _feed(s, x)
        a = _v1_c002(v1, s, x["m738"], x["t738"], DT, decided=v1_decided)
        b = _port(col, lic, x, DT)
        if parted is None:
            try:
                _assert_tick(a, b, s, col, lic, f"tick {k}")
            except AssertionError:
                parted = k
    return parted, s, a, b


def test_lv_328503_on_fishers_trim_decided_divergence(v1):
    """Decision 150, both sides: V1's LV-328503 linear from 50 % on FL 0.90, the port's on Fisher's
    equal percentage from 56.95 % on FL 0.819. Both pass PFD 743 at their design strokes, so on the
    seed tick the flows agree to the bit and only the strokes differ. The feed cut 30 %: ten
    minutes on, V1's LIC-328503 has closed to 34.35 % passing 23 416 kg/h, the port's to 47.85 %
    passing 23 879 kg/h — the equal-percentage trim's lower gain at design closes it further for
    the same flow — and the levels stand at 50.12 and 50.08 %."""
    s, col, lic = _v1_state(v1, ALL - {"valve"}), fd.FirstDesorber(taps=False, l2_stop=False), fd.lic_328503(taps=False)
    script = _step(10, m738=0.7 * t.C002_M738_DES_KGH)
    for k in range(6000):
        x = script(k)
        _feed(s, x)
        a = _v1_c002(v1, s, x["m738"], x["t738"], DT, decided=ALL - {"valve"})
        b = _port(col, lic, x, DT)
        if k == 0:
            assert a["743"] == b.m_743_kgh == pytest.approx(c.C002_M743_DES_KGH, rel=1e-9)
            assert (a["lic"], b.lic_op_pct) == (50.0, pytest.approx(DECIDED_LV503_OP, abs=1e-9))
    assert (a["lic"], b.lic_op_pct) == (pytest.approx(34.35, abs=0.01),
                                        pytest.approx(47.85, abs=0.01))
    assert (a["743"], b.m_743_kgh) == (pytest.approx(23416.4, abs=0.1),
                                       pytest.approx(23879.4, abs=0.1))
    assert (a["LI_328503"], b.level_pct) == (pytest.approx(50.12, abs=0.01),
                                             pytest.approx(50.08, abs=0.01))


def test_a_negative_duty_decided_divergence(v1):
    """B-42. 748 and 750 stopped at 1 s: the columns part on that tick, the net duty going
    negative. Five minutes on, V1 has clamped its boil-up at zero and holds 128.86 C at 328D001's
    pressure, discarding 636.4 kW; the port has condensed its vapour down to 1.482 bar a and its
    bottoms to 111.28 C — the two liquid feeds' mixing temperature, 111.29 C — its duty within
    0.6 kW of zero."""
    parted, s, a, b = _both(v1, _step(10, m748=0.0, m750=0.0), 3000,
                            ALL - {"B-42"})
    assert parted == 10
    assert a["gen"] == 0.0 and a["q"] == pytest.approx(-636.44, abs=0.01)
    assert (s.a328_c002_T, s.a328_c002_P) == (pytest.approx(128.8623, abs=1e-4),
                                              pytest.approx(2.59800, abs=1e-5))
    assert (b.t_c, b.p_bara) == (pytest.approx(111.2794, abs=1e-4),
                                 pytest.approx(1.48257, abs=1e-5))
    assert abs(b.q_kw) < 0.6


@pytest.mark.parametrize("name, script, ticks, parts, v1_level, level", [
    ("750 halved", _step(10, m750=0.5 * t.C002_M750_DES_KGH), 6000, 1, 145.40, 50.01),
    ("the reflux doubled", _step(10, m775=2.0 * t.C002_M775_DES_KGH), 3000, 1, 51.31, 50.27),
])
def test_the_choke_at_the_bottoms_decided_divergence(v1, name, script, ticks, parts, v1_level,
                                                     level):
    """B-43. V1's choke at 190 C binds as the bottoms' ammonia rises; the port's, at the bottoms'
    139 C, does not. On Fisher's FL 0.819 (decision 150) V1's choke binds from the first tick.
    750 halved: ten minutes on V1's LV-328503 is wide open passing 14.9 t/h while its level climbs
    through 145 %; the port's holds 50 %. The reflux doubled: V1 carries a level 1.0 point
    higher. Decision 24 and the valve stand on both sides."""
    parted, s, a, b = _both(v1, script, ticks, ALL - {"B-43"})
    assert parted == parts
    assert (a["LI_328503"], b.level_pct) == (pytest.approx(v1_level, abs=0.01),
                                             pytest.approx(level, abs=0.01))
    if name == "750 halved":
        assert a["lic"] == 100.0 and a["743"] == pytest.approx(14870.2, abs=0.1)
        assert b.m_743_kgh == pytest.approx(33635.2, abs=0.1)


def test_sv32850_relieves_a_blocked_overhead_decided_divergence(v1):
    """B-47, decided 2026-09-30. 328D001 at 7.0 bar a, above the column, from 1 s: 737 stops.
    V1 relieves nothing, and ten minutes on stands at 7.14 bar a and 165.8 C, past SV32850's
    6.01 bar a. The port's column reaches the set pressure 10.9 s after the drum's rises; both
    valves lift, vent the head space at 52 t/h down to their reseat pressure, 5.51 bar a, in
    three ticks, and reseat — every 2.7 s, 218 lifts in the ten minutes, venting 817 kg: the
    4.96 t/h the column boils at 158.4 C. They part on the tick the valves lift; the liquid's
    books close on both sides."""
    s, col, lic = _v1_state(v1), fd.FirstDesorber(taps=False, l2_stop=False), fd.lic_328503(taps=False)
    parted, lifts, vented, p_hi, lifted = None, 0, 0.0, 0.0, False
    for k in range(6000):
        x = _step(10, pd001=7.0)(k)
        _feed(s, x)
        a = _v1_c002(v1, s, x["m738"], x["t738"], DT, decided=ALL - {"relief"})
        b = _port(col, lic, x, DT)
        if parted is None:
            try:
                _assert_tick(a, b, s, col, lic, f"tick {k}")
            except AssertionError:
                parted = k
        lifts += b.relief_lifted and not lifted
        lifted = b.relief_lifted
        vented += b.m_relief_kgh * DT / 3600.0
        p_hi = max(p_hi, b.p_bara)
    assert parted == 119
    assert (s.a328_c002_P, s.a328_c002_T) == (pytest.approx(7.1351, abs=1e-4),
                                              pytest.approx(165.804, abs=1e-3))
    assert p_hi == pytest.approx(6.0265, abs=1e-4) and p_hi < c.SV32850_SET_BARA + 0.02
    assert (lifts, col.t_c) == (218, pytest.approx(158.395, abs=1e-3))
    assert vented == pytest.approx(816.56, abs=0.01)
    assert b.gen_kgh == pytest.approx(4962.0, abs=0.1)


# --------------------------------------------------------------------------------------
# The decided divergence, decision 24: the liquid pays what boils, both sides
# --------------------------------------------------------------------------------------

def head_space_kg(p_bara: float, t_c: float, m_kg: float, vol_m3: float, rho_kgm3: float,
                  mw: float) -> float:
    """The head space's vapour [kg] at molar mass `mw`: the gas law on the free volume, the moles
    the pressure integral carries."""
    return (p_bara * PA_PER_BAR * vapour_volume_m3(vol_m3, m_kg, rho_kgm3)
            / (R_GAS_J * (t_c + ABSOLUTE_ZERO_C)) / 1000.0 * mw)


def vapour_mw(y: dict) -> float:
    """The molar mass of a vapour [kg/kmol], as the column reads it."""
    return 1.0 / sum(y.get(k, 0.0) / MW[k] for k in SOLUTION_SPECIES)


def _c002_books(p_bara, t_c, m_kg, y):
    """328C002's holdup, the head space's moles as mass at the tick's molar mass, and that molar
    mass: the state the next tick's books are kept against."""
    mw = vapour_mw(y)
    return m_kg, head_space_kg(p_bara, t_c, m_kg, c.C002_VOL_M3, c.C002_RHO_KGM3, 1.0), mw


def _made(pre, m_kg, p_bara, t_c, vol_m3, rho_kgm3, net_kgh, dt):
    """The mass a tick made [kg]: the liquid's change plus the head space's, its moles priced at
    the molar mass the tick ran on, less what crossed the boundary."""
    m0, n0, mw = pre
    return (m_kg - m0 + (head_space_kg(p_bara, t_c, m_kg, vol_m3, rho_kgm3, 1.0) - n0) * mw
            - net_kgh * dt / 3600.0)


@pytest.mark.parametrize("name, script, v1_made", [
    ("the stripping vapour lost", _step(10, m748=0.0, m750=0.0), -16.16),
    ("328D001 1 bar higher", _step(10, pd001=t.D001_P_BARA + 1.0), 4.49),
])
def test_the_liquid_pays_what_boils_decided_divergence(v1, name, script, v1_made):
    """Decision 24. V1's liquid loses what the overhead line passes, while the pressure integral
    fills the head space with the boil-up: whatever the head space gains or loses is counted
    twice. The books — the liquid plus the head space's vapour, read off the pressure state at
    the molar mass each tick ran on, against what crossed the boundary — are kept on both sides
    for five minutes. With the stripping vapour lost the condensate of the negative boil-up
    vanishes from V1's books, 16.2 kg; with 328D001 a bar higher V1 makes the 4.5 kg its head
    space holds back — each exactly V1's integral of boil-up less overhead. The port's books
    close within 10 g."""
    s, col, lic = _v1_state(v1), fd.FirstDesorber(taps=False, l2_stop=False), fd.lic_328503(taps=False)
    made_v1 = made = held_back = 0.0
    for k in range(3000):
        x = script(k)
        _feed(s, x)
        pre_v1 = _c002_books(s.a328_c002_P, s.a328_c002_T, s.a328_c002_M, s.y_328_737)
        pre = _c002_books(col.p_bara, col.t_c, col.m_kg, col.y_737)
        a = _v1_c002(v1, s, x["m738"], x["t738"], DT, decided=ALL - {"vapour"})
        b = _port(col, lic, x, DT)
        if k == 0:
            _assert_tick(a, b, s, col, lic, "the seed tick")
        made_v1 += _made(pre_v1, s.a328_c002_M, s.a328_c002_P, s.a328_c002_T, c.C002_VOL_M3,
                         c.C002_RHO_KGM3, a["in"] - a["737"] - a["743"] - a["over"], DT)
        made += _made(pre, col.m_kg, col.p_bara, col.t_c, c.C002_VOL_M3, c.C002_RHO_KGM3,
                      b.in_kgh - b.m_737_kgh - b.m_743_kgh - b.m_overflow_kgh, DT)
        held_back += (a["gen"] - a["737"]) * DT / 3600.0
    assert made_v1 == pytest.approx(v1_made, abs=0.01)
    assert made_v1 == pytest.approx(held_back, abs=0.05)
    assert abs(made) < 0.01


#: B-31's producers on their designs — 328D001's, the hydrolyser's and 328C004's — and the same
#: five kelvin hot.
B31_DES = {"t_d001_c": t.D001_T_C, "t_c003_c": C003_T_C, "t_c004_c": t.C004_T_C}
B31_HOT = {k: v + 5.0 for k, v in B31_DES.items()}


def test_the_inlets_at_their_producers_temperatures_decided_divergence(v1):
    """B-31, decided 2026-10-16: 328C002 charges 775, 748 and 750 at 328D001's, the hydrolyser's
    and 328C004's live temperatures, each as its departure from its producer's design; V1 at 61,
    188 and 140 C whatever they do, so with the latent heats constant their temperatures set the
    boil-up. With every producer on its design the port is V1's on every tick, and so it is with
    every producer 5 K hot on V1's switch. Live, the first tick's duty is 51.78 kW higher and its
    boil-up 99.18 kg/h; after ten minutes the column stands at 139.224 C and 3.5225 bar a against
    V1's 139.0 C and 3.5 bar a, its overhead 6744.6 kg/h against 6665.0."""
    def run(kw, live, ticks, check):
        s, col, lic = _v1_state(v1), fd.FirstDesorber(taps=False, live_inlets=live, l2_stop=False), fd.lic_328503(taps=False)
        first = None
        for k in range(ticks):
            x = _design()
            _feed(s, x)
            a = _v1_c002(v1, s, x["m738"], x["t738"], DT)
            b = col.step(lic, x["m738"], x["t738"], x["m748"], dict(x["y748"]), x["m750"],
                         dict(x["y750"]), x["m775"], x["pc003"], x["pd001"], DT, **kw)
            if check:
                _assert_tick(a, b, s, col, lic, f"live {live}, tick {k}")
            if first is None:
                first = (b.q_kw - a["q"], b.gen_kgh - a["gen"])
        return s, col, a, b, first
    run(B31_DES, True, 600, True)
    run(B31_HOT, False, 600, True)
    s, col, a, b, first = run(B31_HOT, True, 6000, False)
    assert first == (pytest.approx(51.778, abs=1e-3), pytest.approx(99.184, abs=1e-3))
    assert (s.a328_c002_T, s.a328_c002_P, a["737"]) == (
        pytest.approx(139.0, abs=1e-6), pytest.approx(3.5, abs=1e-6), pytest.approx(6665.0, abs=1e-4))
    assert (col.t_c, col.p_bara, b.m_737_kgh) == (
        pytest.approx(139.2244, abs=1e-4), pytest.approx(3.52248, abs=1e-5),
        pytest.approx(6744.64, abs=0.01))
