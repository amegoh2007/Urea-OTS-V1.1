"""V1 <-> V1.1 equivalence for 323D002, stage 4 of unit 323.

What is being proved
--------------------
V1 writes the tank inline in `step_sim`, so the statements that wire it are TRANSCRIBED into
`_v1_stage4` below, line for line, and declared as such: the 323F010 -> 323D002 drain packet
and its transport (``main.py`` 8564-8572) and the tank itself (8656-8810). Everything they call
is V1's own code, executed: ``_ctrl_ipd``, ``_lag1``, ``sol_advance``, ``_cq_packet``,
``_w_norm``, ``urea_soln_cp``, ``urea_soln_rho`` and ``clamp`` lifted out of ``main.py``;
``consequence`` loaded as a real module. The tank's state and its two controllers are seeded
inside ``State.__init__`` and are transcribed from ``main.py`` 6615-6616, 6648-6656 and
6692-6704; the three published levels and inventories from the telemetry block, 10663-10669.

``cp_f010``, which V1 evaluates at the top of the tick (``main.py`` 8251), is transcribed onto
the separator state the drain departed at. The LV-324501B recycle is V1's one-tick tear through
``s.tlag``; each scenario writes the three keys before the tick, as unit 324 would have on the
tick before.

The tank is driven on its own through scripted scenarios chosen to take every branch —
the baffle spill, the tie-in spool opened and shut — and then coupled to stage 3, and to
stages 1 to 3 together. Every tick compares every published field, both compartments' state,
the FT-324401 lag and both controllers with ``==``.

The decided divergence (handoffs B-26 and B-27, 2026-09-27)
------------------------------------------------------------
Where V1's tank created or destroyed liquor, the port departs from it on the process engineer's
decision: 323P003 is capped at what the tank holds, a full tank overflows, Compartment II's
blend divides by the holdup before the overflow, and Compartment II has a temperature. Every
scenario above stays bit-exact, which proves each change inert until its limit is reached. At
the limit, the four ``*_decided_divergence`` tests assert both sides — the V1 behaviour on V1's
own transcribed code, and what the port does instead — on the same ticks.

FIC-324401's gain (handoff B-41, 2026-09-30)
--------------------------------------------
The port reads the DCS table's 0.40 per cent of FT-324401's span, 0.316 %/(t/h), where V1 runs
0.40 %/(t/h). FIC-324401 rides LIC-323507 in cascade, so its error is seldom zero and its gain
acts in nearly every scenario. ``_v1_state(decided=True)`` therefore seeds the port's gain into
V1's controller dict — V1's `_ctrl_ipd` runs unchanged — and every scenario compares the port
with V1's code on the port's gain; the gain itself is proved against V1 verbatim in
`test_flow_loop_gains_equivalence.py`.

The product line (handoff B-21, decided 2026-09-30). The port's line delivers the live
departure flow and delays only the liquor's temperature, composition and cp. The transcription
carries the same switch, ``line_decided`` (default True): a property packet on a unit flow
through V1's own FIFO, and the live flow delivered; ``line_decided=False`` is V1 verbatim. A
settled line is the same float either way.

FV-324401 (handoff B-44, decided 2026-09-30). The port runs it on its vendor trim, Valtek's
modified equal percentage, from the 72.36 % stroke its Kvs gives, where V1 runs it linear from
50 %. The switch ``valves_decided`` (default True, on the state) seeds FIC-324401 there and puts
the trim in place of V1's ``op / 100 . flow_span_324``; ``valves_decided=False`` is V1 verbatim.
Both sides are asserted in the last section of this file.
"""

from __future__ import annotations

import pytest

from ureasim.core.packet import normalise_solution_mass_fraction
from ureasim.data import control_valves as cvd
from ureasim.data import design_point as dp
from ureasim.data import unit_323 as d
from ureasim.data.design_point import R323_FEED_DES_KGH as FEED_DES
from ureasim.data.design_point import R323_M317_DES, R323_M319_DES
from ureasim.data.unit_329 import P_LP_BARA
from ureasim.units.recirc import flash_tank as ft
from ureasim.units.recirc import pre_evaporator as pe
from ureasim.units.recirc import rectifying_column as rc
from ureasim.units.recirc import solution_tank as st
from tests.equivalence import routes_switch
from tests.equivalence import decided_valves as dv
from tests.equivalence import test_flash_tank_equivalence as stage2
from tests.equivalence import test_pre_evaporator_equivalence as stage3
from tests.equivalence import test_rectifying_column_equivalence as stage1
from tests.equivalence.v1_loader import v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

#: FV-324401's decided stroke [%] (B-44): where its Kvs passes PFD 324 on the normal case.
DECIDED_FV401_OP = dv.design_stroke_pct(cvd.FV_324401, dp.R323_M324_DES)

V1_NAMES = stage3.V1_NAMES + [
    "R323_D002_VOL_I_M3", "R323_D002_VOL_II_M3", "R323_D002_LVL_SP", "R323_FV401_OP_DES",
    "R323_D002_M_I_FULL", "R323_D002_M_I_DES", "R323_M324_DES", "R324_W_IN", "R324_W_EV2",
    "R324_E003_T_SP_C",
]

DT = 0.1


@pytest.fixture(scope="module")
def v1():
    ns = stage3.build_v1(V1_NAMES)
    # main.py 6245: V1's own route object for the 323F010 -> 323D002 line.
    # The isometrics' geometry (handoff A-11, decided 2026-10-07): `routes_switch`.
    ns["D002_ROUTE"] = routes_switch.decided(ns, "323F010_TO_323D002")
    return ns


#: PFD 402, the Evaporator II melt the LV-324501B recycle carries.
W402 = normalise_solution_mass_fraction(dict(Urea=97.71, Biuret=0.85, NH3=0.04, H2O=1.39,
                                             HCHO=0.0099))
#: The separator product at design, and a weaker, ammonia-richer one.
W317 = dict(d.W_S317)
W317_WEAK = dict(W317)
W317_WEAK["Urea"] = W317["Urea"] - 0.02
W317_WEAK["NH3"] = W317["NH3"] + 0.002
W317_WEAK["H2O"] = W317["H2O"] + 0.018
NO_RECYCLE = (0.0, 140.0, W402)


def _v1_state(v1, decided: bool = True, valves_decided: bool = True):
    """The V1 plant-state fields stages 1 to 4 read and write, seeded as `State.__init__` seeds
    them (stages 1 to 3 from their own tests, the tank from ``main.py`` 6615-6616, 6648-6656 and
    6692-6704); `decided` gives FIC-324401 the port's gain (B-41); `valves_decided` the vendor
    valves' strokes, FV-324401's among them (B-44)."""
    g = v1
    s = stage3._v1_state(v1, valves_decided=valves_decided)
    s.w_d002 = dict(g["W_S317"])
    s.w_d002_II = dict(g["W_S317"])
    s.r323_d002_M_I = g["R323_D002_M_I_DES"]
    s.r323_d002_M_II = 0.0
    s.r323_d002_T = g["R323_F010_T_SP_C"]
    s.HV_323D002_TIE = False
    s.w_e003 = dict(W402)
    s.LIC_323507 = {"mode": "AUTO", "op": g["R323_M324_DES"] / 1000.0,
                    "sp": g["R323_D002_LVL_SP"], "pv": g["R323_D002_LVL_SP"],
                    "pv1": g["R323_D002_LVL_SP"], "pv2": g["R323_D002_LVL_SP"],
                    "Kc": 1.0, "Ti": 4030.0, "Td": 0.0, "act": -1.0,
                    "op_lo": 0.0, "op_hi": 150.0, "sp_lo": 0.0, "sp_hi": 100.0}
    s.FIC_324401 = {"mode": "CAS", "op": g["R323_FV401_OP_DES"],
                    "sp": g["R323_M324_DES"] / 1000.0, "pv": g["R323_M324_DES"] / 1000.0,
                    "pv1": g["R323_M324_DES"] / 1000.0, "pv2": g["R323_M324_DES"] / 1000.0,
                    "Kc": 0.4, "Ti": 30.0, "Td": -1.0, "act": +1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0, "sp_hi": 150.0}
    if decided:
        s.FIC_324401["Kc"] = d.FIC_324401_KC
    if valves_decided:
        s.FIC_324401["op"] = DECIDED_FV401_OP
    s.valves_decided = valves_decided
    return s


def _v1_stage4(v1, s, m_317: float, T_dep_317: float, w_dep_317: dict, dt: float,
               line_decided: bool = True) -> dict:
    """V1 `main.py` 8564-8572 and 8656-8810, stage 4, TRANSCRIBED line for line.
    `line_decided` puts the port's inlet line in V1's (handoff B-21)."""
    g = v1
    clamp = g["clamp"]
    SOL_SPECIES = g["SOL_SPECIES"]
    R324_W_IN, R324_W_EV2 = g["R324_W_IN"], g["R324_W_EV2"]
    _cp = lambda w, T, des: g["R323_CP_SOLN"] + (g["urea_soln_cp"](w, T) - des)  # noqa: E731
    # main.py 8251, on the separator state the drain departed at (module docstring).
    cp_f010 = _cp(w_dep_317.get("Urea", 0.0), T_dep_317, g["R323_CP_F010_DES"])
    # main.py 8564-8572, the 323F010 -> 323D002 line. _transport_process, less its telemetry:
    # B-21, decided 2026-09-30: with `line_decided`, the port's lines — a property packet on the
    # unit flow through V1's own FIFO, and the live departure flow delivered.
    _pkt_dep_317 = g["_cq_packet"](1.0 if line_decided else m_317, T_dep_317, w_dep_317,
                                   cp_f010)
    _pkt_arr_317 = g["consequence"].transport_process_packet(
        s.tlag, "PROCESS_323F010_TO_323D002", _pkt_dep_317, g["D002_ROUTE"], m_317, dt)
    if _pkt_arr_317 == _pkt_dep_317:
        m_317_in, T_317_in, w_317_in = m_317, T_dep_317, w_dep_317
    else:
        m_317_in = m_317 if line_decided else _pkt_arr_317.mass_kgh
        T_317_in = _pkt_arr_317.temperature_c
        w_317_in = g["_w_norm"](_pkt_arr_317.mass_fraction, w_dep_317)
    # main.py 8672-8810, the tank.
    flow_span_324 = g["R323_M324_DES"] / 1000.0 / (g["R323_FV401_OP_DES"] / 100.0)

    def fv401_th(op):
        """FV-324401's flow [t/h]: V1's ``op / 100 . flow_span_324``, or on the state's
        ``valves_decided`` the vendor trim from the decided stroke (B-44)."""
        if s.valves_decided:
            return g["R323_M324_DES"] / 1000.0 * (dv.trim(op / 100.0)
                                                  / dv.trim(DECIDED_FV401_OP / 100.0))
        return op / 100.0 * flow_span_324
    tie_open = bool(s.HV_323D002_TIE)
    d002_recyc = max(s.tlag.get("R324_recyc", 0.0), 0.0)
    d002_recyc_T = s.tlag.get("R324_recyc_T", g["R324_E003_T_SP_C"])
    d002_recyc_w = s.tlag.get("R324_recyc_comp", s.w_e003)
    M_I_pre = s.r323_d002_M_I
    M_II_pre = s.r323_d002_M_II
    rho_d002 = g["urea_soln_rho"](s.w_d002.get("Urea", R324_W_IN), s.r323_d002_T,
                                  g["R323_D002_RHO"])
    v_I_full = g["R323_D002_VOL_I_M3"] * rho_d002
    v_II_full = g["R323_D002_VOL_II_M3"] * rho_d002
    v_tie_full = v_I_full + v_II_full
    lvl_d002_I = clamp(((M_I_pre + M_II_pre) / v_tie_full if tie_open
                        else M_I_pre / v_I_full) * 100.0, 0.0, 100.0)
    lic07_op = g["_ctrl_ipd"](s.LIC_323507, lvl_d002_I, dt)
    prior_flow_324 = fv401_th(s.FIC_324401["op"])
    fic01_pv = g["_lag1"](s.tlag, "R323_FIC324", prior_flow_324, 5.0, dt)
    fic01_op = g["_ctrl_ipd"](s.FIC_324401, fic01_pv, dt, cas_sp=lic07_op)
    m_324 = max(fv401_th(fic01_op), 0.0) * 1000.0
    d002_overflow = 0.0
    if tie_open:
        M_tot = clamp(M_I_pre + M_II_pre + (m_317_in + d002_recyc - m_324) / 3600.0 * dt,
                      1.0, v_tie_full)
        frac = M_tot / v_tie_full
        M_I_new = frac * v_I_full
        M_II_new = frac * v_II_full
    else:
        M_I_new = M_I_pre + (m_317_in + d002_recyc - m_324) / 3600.0 * dt
        if M_I_new > v_I_full:
            d002_overflow = M_I_new - v_I_full
            M_I_new = v_I_full
        M_II_new = clamp(M_II_pre + d002_overflow, 0.0, v_II_full)
    s.r323_d002_M_I = max(M_I_new, 1.0)
    s.r323_d002_M_II = max(M_II_new, 0.0)
    cp_d002_in = g["urea_soln_cp"](w_317_in.get("Urea", R324_W_IN), T_317_in)
    cp_d002_recyc = g["urea_soln_cp"](d002_recyc_w.get("Urea", R324_W_EV2), d002_recyc_T)
    cp_d002 = g["urea_soln_cp"](s.w_d002.get("Urea", R324_W_IN), s.r323_d002_T)
    M_d002_T = (M_I_pre + M_II_pre) if tie_open else M_I_pre
    k_cap_d002 = (m_317_in / 3600.0 * cp_d002_in + d002_recyc / 3600.0 * cp_d002_recyc)
    s.r323_d002_T = s.r323_d002_T + (
        m_317_in / 3600.0 * cp_d002_in * (T_317_in - s.r323_d002_T)
        + d002_recyc / 3600.0 * cp_d002_recyc * (d002_recyc_T - s.r323_d002_T)
    ) * dt / max(M_d002_T * cp_d002 + k_cap_d002 * dt, 1e-6)
    if tie_open:
        M_pool_pre = M_I_pre + M_II_pre
        w_pool = ({k: (M_I_pre * s.w_d002.get(k, 0.0) + M_II_pre * s.w_d002_II.get(k, 0.0))
                   / M_pool_pre for k in SOL_SPECIES}
                  if M_pool_pre > 1e-9 else dict(s.w_d002))
        w_pool = g["sol_advance"](w_pool, M_pool_pre, s.r323_d002_M_I + s.r323_d002_M_II,
                                  m_317_in, w_317_in, 0.0, w_pool, m_324, 0.0, dt,
                                  m_in2=d002_recyc, w_in2=d002_recyc_w)
        s.w_d002 = w_pool
        s.w_d002_II = dict(w_pool)
    else:
        w_I_new = g["sol_advance"](s.w_d002, M_I_pre, s.r323_d002_M_I, m_317_in, w_317_in,
                                   0.0, s.w_d002, m_324 + d002_overflow * 3600.0 / max(dt, 1e-9),
                                   0.0, dt, m_in2=d002_recyc, w_in2=d002_recyc_w)
        if d002_overflow > 0.0 and s.r323_d002_M_II > 1e-9:
            s.w_d002_II = {k: (M_II_pre * s.w_d002_II.get(k, 0.0)
                               + d002_overflow * s.w_d002.get(k, 0.0)) / s.r323_d002_M_II
                           for k in SOL_SPECIES}
        s.w_d002 = w_I_new
    return {
        "feed": (m_317_in, T_317_in, w_317_in), "cp_in": cp_d002_in, "recyc": d002_recyc,
        "rho": rho_d002, "lvl": lvl_d002_I, "lic": lic07_op, "fic_pv": fic01_pv,
        "fic": fic01_op, "m324": m_324, "spill": d002_overflow,
        # main.py 10664, 10668-10669, the telemetry the operator reads.
        "LI_323504": s.r323_d002_M_II / v_II_full * 100.0,
        "m3_comp1": s.r323_d002_M_I / rho_d002, "m3_comp2": s.r323_d002_M_II / rho_d002,
    }


def _assert_tick(a: dict, b: st.SolutionTankResult, s, tank, lic, fic, label):
    assert a["feed"] == (b.feed_kgh, b.feed_t_c, b.feed_w), label
    assert (a["cp_in"], a["recyc"], a["rho"], a["lvl"]) == (
        b.feed_cp, b.recycle_kgh, b.rho_kgm3, b.lic_pv_pct), label
    assert (a["lic"], a["fic_pv"], a["fic"], a["m324"], a["spill"]) == (
        b.lic_op_th, b.fic_pv_th, b.fic_op_pct, b.m_324_kgh, b.spill_kg), label
    assert (a["LI_323504"], a["m3_comp1"], a["m3_comp2"]) == (
        b.li_323504_pct, b.comp_i_m3, b.comp_ii_m3), label
    assert (s.r323_d002_M_I, s.r323_d002_M_II, s.r323_d002_T, s.w_d002, s.w_d002_II) == (
        tank.m_i_kg, tank.m_ii_kg, tank.t_c, tank.w, tank.w_ii), label
    assert (b.m_i_kg, b.m_ii_kg, b.t_c, b.w, b.w_ii) == (
        tank.m_i_kg, tank.m_ii_kg, tank.t_c, tank.w, tank.w_ii), label
    assert s.tlag["R323_FIC324"] == tank.lag_state[st.FT_324401_LAG_KEY], label
    for v1c, loop in ((s.LIC_323507, lic), (s.FIC_324401, fic)):
        assert (v1c["op"], v1c["sp"], v1c["pv"], v1c["pv1"], v1c["pv2"], v1c["mode"]) == (
            loop.op, loop.sp, loop.pv, loop.pv1, loop.pv2, loop.mode), (label, loop.tag)
    # The decided divergence is inert: no loss of suction, no overflow.
    assert (b.suction_lost, b.overflow_kgh, tank.suction_cap_th) == (False, 0.0, None), label


def _v1_total(s) -> float:
    return s.r323_d002_M_I + s.r323_d002_M_II


def _design(**over):
    base = {"m317": R323_M317_DES, "t317": d.F010_T_SP_C, "w317": W317, "rec": NO_RECYCLE,
            "tie": False}
    base.update(over)
    return base


def _run(v1, script, ticks: int, dt: float = DT, before=None):
    """Drive the tank alone through `script(k)`, comparing everything every tick."""
    s = _v1_state(v1)
    tank, lic, fic = st.SolutionTank(backward_species=False), st.lic_323507(), st.fic_324401()
    if before:
        before(s, tank, lic, fic)
    b = None
    for k in range(ticks):
        x = script(k)
        s.HV_323D002_TIE = x["tie"]
        s.tlag["R324_recyc"], s.tlag["R324_recyc_T"], s.tlag["R324_recyc_comp"] = x["rec"]
        a = _v1_stage4(v1, s, x["m317"], x["t317"], x["w317"], dt)
        b = tank.step(lic, fic, x["m317"], x["t317"], x["w317"], *x["rec"], x["tie"], dt)
        _assert_tick(a, b, s, tank, lic, fic, f"tick {k}")
    return s, tank, (lic, fic), b


def _seed(s, tank, m_i: float = None, m_ii: float = None, w_ii: dict = None):
    """Start both sides from the same off-design holdups."""
    if m_i is not None:
        s.r323_d002_M_I = tank.m_i_kg = m_i
    if m_ii is not None:
        s.r323_d002_M_II = tank.m_ii_kg = m_ii
    if w_ii is not None:
        s.w_d002_II, tank.w_ii = dict(w_ii), dict(w_ii)


def _manual(s, loop, key: str, op: float):
    getattr(s, key)["mode"] = "MAN"
    getattr(s, key)["op"] = op
    loop.set_mode("MAN")
    loop.op = op


# --------------------------------------------------------------------------------------
# The design basis
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("ours, theirs", [
    ("D002_VOL_I_M3", "R323_D002_VOL_I_M3"), ("D002_VOL_II_M3", "R323_D002_VOL_II_M3"),
    ("D002_LVL_SP_PCT", "R323_D002_LVL_SP"),
    ("D002_M_I_FULL_KG", "R323_D002_M_I_FULL"), ("D002_M_I_DES_KG", "R323_D002_M_I_DES"),
])
def test_design_basis(v1, ours, theirs):
    assert getattr(d, ours) == v1[theirs]


def test_the_unit_324_strengths_and_the_flow_span(v1):
    assert (dp.R323_M324_DES, dp.R324_W_IN, dp.R324_W_EV2) == (
        v1["R323_M324_DES"], v1["R324_W_IN"], v1["R324_W_EV2"])
    # FV-324401 passes PFD 324 at its design stroke: V1's at 50 %, the port's at the decided one.
    assert st.fv_324401_th(DECIDED_FV401_OP) == pytest.approx(v1["R323_M324_DES"] / 1000.0,
                                                              rel=1e-15)
    assert v1["R323_FV401_OP_DES"] == 50.0


def test_the_controllers_are_seeded_as_v1_seeds_them(v1):
    """Every seed V1's; FIC-324401's gain the table's 0.40 per t/h in V1, per cent of FT-324401's
    0-110 m3/h span in the port (B-41), which the decided transcription carries."""
    assert _v1_state(v1, decided=False).FIC_324401["Kc"] == d.FIC_324401_KC_TABLE
    assert d.FIC_324401_KC == d.FIC_324401_KC_TABLE * 100.0 / (110.0 * dp.R323_D002_RHO / 1000.0)
    s = _v1_state(v1)
    for v1c, loop in ((s.LIC_323507, st.lic_323507()), (s.FIC_324401, st.fic_324401())):
        assert (v1c["mode"], v1c["op"], v1c["sp"], v1c["pv"], v1c["pv1"], v1c["pv2"],
                v1c["Kc"], v1c["Ti"], v1c["Td"], v1c["act"], v1c["op_lo"], v1c["op_hi"],
                v1c["sp_lo"], v1c["sp_hi"]) == (
            loop.mode, loop.op, loop.sp, loop.pv, loop.pv1, loop.pv2, loop.Kc, loop.Ti,
            loop.Td, loop.act, loop.op_lo, loop.op_hi, loop.sp_lo, loop.sp_hi), loop.tag
    tank = st.SolutionTank(backward_species=False)
    assert (s.r323_d002_M_I, s.r323_d002_M_II, s.r323_d002_T, s.w_d002, s.w_d002_II,
            s.HV_323D002_TIE) == (tank.m_i_kg, tank.m_ii_kg, tank.t_c, tank.w, tank.w_ii, False)


# --------------------------------------------------------------------------------------
# The tank on its own, tick by tick
# --------------------------------------------------------------------------------------

#: 20 t/h of Evaporator II melt back through LV-324501B.
RECYCLE = (20000.0, 140.0, W402)

SCENARIOS = {
    "design hold": (lambda k: _design(), 300, DT),
    "separator drain up 10 % (the line's dead time shows)": (
        lambda k: _design(m317=R323_M317_DES * (1.1 if k >= 10 else 1.0)), 600, 0.5),
    "separator drain cut 30 %": (
        lambda k: _design(m317=R323_M317_DES * (0.7 if k >= 10 else 1.0)), 600, 0.5),
    "hotter product": (lambda k: _design(t317=(104.0 if k >= 10 else 99.0)), 400, 0.5),
    "colder product": (lambda k: _design(t317=(90.0 if k >= 10 else 99.0)), 400, 0.5),
    "weaker, ammonia-richer product": (
        lambda k: _design(w317=(W317_WEAK if k >= 10 else W317)), 400, 0.5),
    "LV-324501B melt recycle": (lambda k: _design(rec=(RECYCLE if k >= 10 else NO_RECYCLE)),
                                600, 0.5),
    "a negative recycle tear is read as none": (lambda k: _design(rec=(-50.0, 140.0, W402)),
                                                100, DT),
    "tie-in spool opened against a dry Compartment II": (
        lambda k: _design(tie=(k >= 10)), 600, 0.5),
    "tie-in spool opened, then shut again": (lambda k: _design(tie=(10 <= k < 200)), 600, 0.5),
}


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_stage_four_tick_by_tick(v1, name):
    script, ticks, dt = SCENARIOS[name]
    _run(v1, script, ticks, dt)


def test_fic_324401_in_auto_on_its_own_set_point(v1):
    def before(s, tank, lic, fic):
        s.FIC_324401["mode"] = "AUTO"; s.FIC_324401["sp"] = 80.0
        fic.set_mode("AUTO"); fic.sp = 80.0
    _run(v1, lambda k: _design(), 400, dt=0.5, before=before)


def test_compartment_one_overtops_the_baffle(v1):
    """The pump stopped with Compartment I nearly full: the tank spills over the baffle within
    seconds, and Compartment II takes Compartment I's liquor — then a weaker product, so the two
    compartments' compositions part."""
    def before(s, tank, lic, fic):
        _manual(s, fic, "FIC_324401", 0.0)
        _seed(s, tank, m_i=0.99 * d.D002_M_I_FULL_KG)
    s, tank, loops, b = _run(v1, lambda k: _design(w317=(W317_WEAK if k >= 40 else W317)),
                             500, dt=0.5, before=before)
    assert b.spill_kg > 0.0 and tank.m_ii_kg > 0.0 and tank.w_ii != tank.w


def test_the_tie_opened_on_a_part_filled_compartment_two(v1):
    """Compartment II holding 40 t of a different liquor at Compartment I's temperature:
    opening the spool blends the two inventories into one pool, which the pump then draws.
    With the two temperatures equal the enthalpy start of B-27 is exactly V1's."""
    def before(s, tank, lic, fic):
        _seed(s, tank, m_ii=40000.0, w_ii=W317_WEAK)
    _run(v1, lambda k: _design(tie=(k >= 10)), 600, dt=0.5, before=before)


# --------------------------------------------------------------------------------------
# The decided divergence, handoffs B-26 and B-27: both sides asserted
# --------------------------------------------------------------------------------------

def _diverge(v1, script, ticks: int, dt: float, before, limit_reached):
    """Drive both sides bit-exact until `limit_reached(k, b)` first holds, then keep driving
    both and hand back every later tick as (V1 result, V1 total holdup before and after, the
    port's total holdup before, port result)."""
    s = _v1_state(v1)
    tank, lic, fic = st.SolutionTank(backward_species=False), st.lic_323507(), st.fic_324401()
    before(s, tank, lic, fic)
    after, reached = [], False
    for k in range(ticks):
        x = script(k)
        s.HV_323D002_TIE = x["tie"]
        s.tlag["R324_recyc"], s.tlag["R324_recyc_T"], s.tlag["R324_recyc_comp"] = x["rec"]
        m_v1_pre, m_pre = _v1_total(s), tank.m_i_kg + tank.m_ii_kg
        a = _v1_stage4(v1, s, x["m317"], x["t317"], x["w317"], dt)
        b = tank.step(lic, fic, x["m317"], x["t317"], x["w317"], *x["rec"], x["tie"], dt)
        reached = reached or limit_reached(k, b)
        if not reached:
            _assert_tick(a, b, s, tank, lic, fic, f"tick {k}")
        else:
            after.append((a, m_v1_pre, _v1_total(s), m_pre, b))
    assert after, "the limit was never reached"
    return s, tank, after


def test_the_pump_runs_compartment_one_dry_decided_divergence(v1):
    """B-26. FV-324401 held at 85 % draws more than arrives. V1 floors Compartment I at 1 kg
    and keeps pumping at the valve's flow, creating the difference; the port caps the pump at
    what the tank holds, flags the loss of suction, and FT-324401 reads the flow delivered."""
    def before(s, tank, lic, fic):
        _manual(s, fic, "FIC_324401", 85.0)
        _seed(s, tank, m_i=2000.0)
    s, tank, after = _diverge(v1, lambda k: _design(), 600, 1.0, before,
                              lambda k, b: b.suction_lost)
    valve_kgh = max(st.fv_324401_th(85.0), 0.0) * 1000.0
    for a, v1_pre, v1_post, m_pre, b in after:
        # V1: the valve's flow, whatever the tank holds, and liquor made up at the floor.
        assert a["m324"] == valve_kgh
        v1_created = (v1_post - v1_pre) - (a["feed"][0] - a["m324"]) / 3600.0
        assert v1_created > 0.0
        # The port: never more than the tank holds, and nothing made up.
        assert b.suction_lost and b.m_324_kgh < a["m324"]
        ours_created = (b.m_i_kg + b.m_ii_kg - m_pre) - (b.feed_kgh - b.m_324_kgh) / 3600.0
        assert abs(ours_created) < 1e-9
    a, _, _, _, b = after[-1]
    assert s.r323_d002_M_I == d.D002_M_I_FLOOR_KG
    assert b.m_324_kgh == pytest.approx(b.feed_kgh, rel=1e-12)
    # FT-324401: V1's reads the valve; the port's has lagged down to the flow delivered.
    assert a["fic_pv"] == pytest.approx(valve_kgh / 1000.0, rel=1e-9)
    assert b.fic_pv_th == pytest.approx(b.feed_kgh / 1000.0, rel=1e-6)


@pytest.mark.parametrize("tie", [False, True], ids=["compartment II full", "the pool full"])
def test_a_full_tank_decided_divergence(v1, tie):
    """B-27. Both compartments full and the pump stopped. V1 clamps the holdup and destroys what
    arrives; the port holds the SAME holdups and books the excess to the overflow stream, tick
    for tick. With the tie shut V1's Compartment II blend then stops summing to one; the port's
    does not."""
    def before(s, tank, lic, fic):
        _manual(s, fic, "FIC_324401", 0.0)
        _seed(s, tank, m_i=d.D002_M_I_FULL_KG, m_ii=0.999 * d.D002_VOL_II_M3 * dp.R323_D002_RHO)
    s, tank, after = _diverge(v1, lambda k: _design(tie=tie), 300, 1.0, before,
                              lambda k, b: b.overflow_kgh > 0.0)
    for a, v1_pre, v1_post, _, b in after:
        v1_destroyed = (v1_pre + a["feed"][0] / 3600.0) - v1_post
        assert v1_destroyed > 0.0
        assert b.overflow_kgh / 3600.0 == pytest.approx(v1_destroyed, rel=1e-9)
        # Everything V1 publishes about the holdups and Compartment I is unchanged.
        assert (a["m324"], a["spill"], a["LI_323504"], a["m3_comp1"], a["m3_comp2"]) == (
            b.m_324_kgh, b.spill_kg, b.li_323504_pct, b.comp_i_m3, b.comp_ii_m3)
    assert (s.r323_d002_M_I, s.r323_d002_M_II, s.r323_d002_T) == (
        tank.m_i_kg, tank.m_ii_kg, tank.t_c)
    if tie:
        assert s.w_d002 == pytest.approx(tank.w, abs=1e-15)
        assert b.overflow_t_c == tank.t_c and b.overflow_w == tank.w
    else:
        assert s.w_d002 == tank.w
        assert sum(s.w_d002_II.values()) > 1.0 + 1e-3
        assert sum(tank.w_ii.values()) == pytest.approx(1.0, abs=1e-12)
        assert b.overflow_t_c == tank.t_ii_c and b.overflow_w == tank.w_ii


def test_the_tie_opened_on_a_colder_compartment_two_decided_divergence(v1):
    """B-27. 40 t stranded in Compartment II at 92 C: V1 pools at Compartment I's 99 C; the port
    starts the pool from the two compartments' enthalpy balance. Bit-exact until the spool
    opens; on that tick the holdups and compositions still agree and the temperature does not."""
    def before(s, tank, lic, fic):
        _seed(s, tank, m_ii=40000.0, w_ii=W317_WEAK)
        tank.t_ii_c = 92.0
    s, tank, after = _diverge(v1, lambda k: _design(tie=(k >= 10)), 11, 0.5, before,
                              lambda k, b: k >= 10)
    assert (s.r323_d002_M_I, s.r323_d002_M_II, s.w_d002) == (tank.m_i_kg, tank.m_ii_kg, tank.w)
    assert s.r323_d002_T == pytest.approx(99.0, abs=1e-12)
    assert tank.t_c == pytest.approx(93.2941, abs=1e-4)


# --------------------------------------------------------------------------------------
# Stages 3 and 4 coupled, and all four: the drain interface, end to end
# --------------------------------------------------------------------------------------

def test_stages_three_and_four_coupled_through_a_drain_step(v1):
    """V1's stage 3 feeds V1's stage 4; the ported 323F010 feeds the ported 323D002."""
    s = _v1_state(v1)
    sep, tic, pic = pe.PreEvaporator(chest=pe.V1_CHEST, vent=pe.V1_VENT, live_bubble=False), pe.tic_323012(), pe.pic_329208(pe.V1_CHEST)
    tank, lic, fic = st.SolutionTank(backward_species=False), st.lic_323507(), st.fic_324401()
    for k in range(600):
        m319 = R323_M319_DES * (0.8 if k >= 20 else 1.0)
        s.tlag["R324_recyc"], s.tlag["R324_recyc_T"], s.tlag["R324_recyc_comp"] = NO_RECYCLE
        a3 = stage3._v1_stage3(v1, s, m319, d.F004_T_SP_C, stage3.W319, stage3.NO_BLOW, DT)
        a4 = _v1_stage4(v1, s, a3["m317"], a3["dep317"][0], a3["dep317"][1], DT)
        b3 = sep.step(tic, pic, m319, d.F004_T_SP_C, stage3.W319, *stage3.NO_BLOW,
                      d.HIC_323605_DES_PCT_V1, P_LP_BARA, d.P_324E002_DES_BARA, DT)
        b4 = tank.step(lic, fic, b3.m_317_kgh, b3.drain_t_c, b3.drain_w, *NO_RECYCLE, False, DT)
        stage3._assert_tick(a3, b3, s, sep, tic, pic, f"stage 3, tick {k}")
        _assert_tick(a4, b4, s, tank, lic, fic, f"stage 4, tick {k}")


def test_all_four_stages_coupled_through_a_stripper_feed_cut(v1):
    """V1's stages 1 to 4 against the ported 323C003 -> 323F004 -> 323F010 -> 323D002."""
    s = _v1_state(v1)
    col = rc.RectifyingColumn(chest=rc.V1_CHEST)
    loops1 = (rc.tic_323007(), rc.pic_329202(rc.V1_CHEST), rc.lic_323501())
    drum, lic5 = ft.FlashTank(**ft.V1_DRUM), ft.lic_323505()
    sep, tic, pic = pe.PreEvaporator(chest=pe.V1_CHEST, vent=pe.V1_VENT, live_bubble=False), pe.tic_323012(), pe.pic_329208(pe.V1_CHEST)
    tank, lic, fic = st.SolutionTank(backward_species=False), st.lic_323507(), st.fic_324401()
    for k in range(500):
        drain = FEED_DES * (0.85 if k >= 20 else 1.0)
        s.tlag["R324_recyc"], s.tlag["R324_recyc_T"], s.tlag["R324_recyc_comp"] = NO_RECYCLE
        a1 = stage1._v1_stage1(v1, s, drain, 119.0, stage1.BOTTOMS_PCT, DT)
        a2 = stage2._v1_stage2(v1, s, a1["m314"], a1["dep314"][0], a1["dep314"][1], DT)
        a3 = stage3._v1_stage3(v1, s, a2["m319"], a2["dep319"][0], a2["dep319"][1], a2["blow"],
                               DT)
        a4 = _v1_stage4(v1, s, a3["m317"], a3["dep317"][0], a3["dep317"][1], DT)
        b1 = col.step(*loops1, drain, 119.0, stage1.BOTTOMS_PCT, 172.0, P_LP_BARA,
                      drum.p_bara, d.E003_P_DES_BARA, DT)
        b2 = drum.step(lic5, b1.m_314_kgh, b1.drain_t_c, b1.drain_w, d.F004_P_BARA, sep.p_bara,
                       DT)
        b3 = sep.step(tic, pic, b2.m_319_kgh, b2.drain_t_c, b2.drain_w, b2.blowthrough_kgh,
                      b2.blowthrough_kmolh, b2.blowthrough_y, d.HIC_323605_DES_PCT_V1, P_LP_BARA,
                      d.P_324E002_DES_BARA, DT)
        b4 = tank.step(lic, fic, b3.m_317_kgh, b3.drain_t_c, b3.drain_w, *NO_RECYCLE, False, DT)
        stage1._assert_tick(a1, b1, s, col, loops1, f"stage 1, tick {k}")
        stage2._assert_tick(a2, b2, s, drum, lic5, f"stage 2, tick {k}")
        stage3._assert_tick(a3, b3, s, sep, tic, pic, f"stage 3, tick {k}")
        _assert_tick(a4, b4, s, tank, lic, fic, f"stage 4, tick {k}")


# --------------------------------------------------------------------------------------
# The decided divergence: FV-324401 (handoff B-44), both sides
# --------------------------------------------------------------------------------------

def test_the_vendor_valve_decided_divergence(v1):
    """V1 verbatim against the port, FIC-324401 in MAN at 85 %. At design both deliver PFD 324;
    stroked, V1's linear trim from 50 % passes 1.70 times it, the vendor's modified equal
    percentage from 72.36 % 1.46 times."""
    s = _v1_state(v1, valves_decided=False)
    tank, lic, fic = st.SolutionTank(backward_species=False), st.lic_323507(), st.fic_324401()
    assert (s.FIC_324401["op"], fic.op) == (50.0, DECIDED_FV401_OP)
    _manual(s, fic, "FIC_324401", 85.0)
    x = _design()
    a = _v1_stage4(v1, s, x["m317"], x["t317"], x["w317"], 1.0)
    b = tank.step(lic, fic, x["m317"], x["t317"], x["w317"], *x["rec"], x["tie"], 1.0)
    assert a["m324"] == pytest.approx(1.7 * dp.R323_M324_DES, rel=1e-12)
    assert b.m_324_kgh / dp.R323_M324_DES == pytest.approx(1.4604, abs=1e-4)
