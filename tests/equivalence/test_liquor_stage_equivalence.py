"""V1 <-> V1.1 equivalence for the urea-liquor stage layer shared by units 323 and 324.

What is being proved
--------------------
Wholly by execution. V1's solution-species block — ``_reconcile_melt``, ``x_water_mol``,
``bubble_T_raoult``, ``_sol_stage_anchor``, ``sol_vapour_y``, ``_sol_model_alpha``,
``sol_bubble_t_dep``, ``sol_vapour_y_vle``, ``sol_biuret_xi`` and ``sol_advance`` — is lifted out
of ``main.py`` and driven side by side with `thermo.urea_liquor` and `units.liquor_stage`, with
``==`` on every float.

Two things about the lift are declared rather than hidden:

  * V1 fills its two design memos with bare module-level CALLS (``_sol_tbub_anchor("C003", ...)``,
    ``_sol_alpha_anchor(...)``). `lift()` executes only definitions, so the fixture makes those
    six calls itself, with V1's exact arguments, transcribed from ``main.py`` 2598-2616 and
    2874-2876.
  * ``sol_biuret_xi`` reads ``SOL_STAGES``, whose 324 entries would pull in the whole unit-324
    constant block. The fixture therefore lifts in two passes and seeds ``SOL_STAGES`` with the
    three 323 entries, built exactly as V1 builds them (``main.py`` 2730-2736). The 324 stages
    are proven when unit 324 is ported.

The flash budget (handoff A-9, decided 2026-09-30). The port's flash runs 60 sweeps where V1's
runs 40, and ``_sol_model_alpha`` refuses an unconverged flash, so the two take different
branches wherever a solve needs 41 to 60 sweeps. V1's ``thermo_service`` is seeded on the port's
budget (`v1_loader.v1_service`), so every comparison runs V1's own code on it; the budget's
own effect is asserted both ways by ``test_the_flash_budget_decided_divergence``.
"""

from __future__ import annotations

import math

import pytest

from ureasim.data import unit_323 as d
from ureasim.data.design_point import R323_FEED_DES_KGH, R323_M314_DES, R323_M317_DES, R323_M319_DES
from ureasim.thermo import urea_liquor as ul
from ureasim.units import liquor_stage as ls
from tests.equivalence import b20_switch
from tests.equivalence.v1_loader import lift, load, v1_available, v1_service

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

V1_NAMES = [
    "_w_norm", "_reconcile_melt", "x_water_mol", "bubble_T_raoult",
    "W_S208", "W_S314", "W_S319_TAB", "W_S319", "W_S331", "W_S317",
    "R323_FEED_DES_KGH", "R323_M305_DES", "R323_M314_DES", "R323_M701_DES", "R323_M319_DES",
    "R323_MEVAP_DES", "R323_M317_DES", "R323_M331_DES", "R323_M331_T_C",
    "R323_C003_M_DES", "R323_F004_M_DES", "R323_F010_M_DES",
    "R323_C003_T_SP_C", "R323_F004_T_SP_C", "R323_F010_T_SP_C",
    "R323_C003_P_BARA", "R323_F004_P_BARA", "R323_F010_P_BARA",
    "R323_C003_M_TAU_S", "R323_F004_M_TAU_S", "R323_F010_M_TAU_S",
    "R323_F010_TBUB_DES",
    "_sol_stage_anchor", "SOL_C003", "SOL_F004", "SOL_F010",
    "sol_vapour_y", "SOL_TBUB_DES", "_sol_tbub_anchor", "sol_bubble_t_dep",
    "SOL_ALPHA_MODEL_DES", "_sol_model_alpha", "_sol_alpha_anchor",
    "SOL_VLE_DOMAIN", "SOL_NONVOLATILE", "sol_vapour_y_vle",
    "sol_advance", "SOL_BIU_EA", "SOL_BIU_ORDER", "STRIP_R_GAS_J",
]

STAGES = {"C003": d.C003_LIQUOR, "F004": d.F004_LIQUOR, "F010": d.F010_LIQUOR}


@pytest.fixture(scope="module")
def v1():
    ns = lift(b20_switch.names(V1_NAMES), seed=b20_switch.seed({
        "math": math,
        "iapws_if97": load("iapws_if97"),
        "thermo_service": v1_service(),
    }))
    # main.py 2598, 2615-2616: the design bubble-point memos.
    ns["_sol_tbub_anchor"]("F010", ns["W_S317"], ns["R323_F010_P_BARA"])
    ns["_sol_tbub_anchor"]("C003", ns["W_S314"], ns["R323_C003_P_BARA"])
    ns["_sol_tbub_anchor"]("F004", ns["W_S319"], ns["R323_F004_P_BARA"])
    # main.py 2874-2876: the design model-volatility memos.
    ns["_sol_alpha_anchor"]("C003", ns["W_S314"], ns["R323_C003_T_SP_C"], ns["R323_C003_P_BARA"])
    ns["_sol_alpha_anchor"]("F004", ns["W_S319"], ns["R323_F004_T_SP_C"], ns["R323_F004_P_BARA"])
    ns["_sol_alpha_anchor"]("F010", ns["W_S317"], ns["R323_F010_T_SP_C"], ns["R323_F010_P_BARA"])
    # main.py 2730-2736, the 323 rows of SOL_STAGES; second pass for sol_biuret_xi.
    stages = {
        "C003": {"w": ns["W_S314"], "a": ns["SOL_C003"], "M": ns["R323_C003_M_DES"],
                 "T": ns["R323_C003_T_SP_C"]},
        "F004": {"w": ns["W_S319"], "a": ns["SOL_F004"], "M": ns["R323_F004_M_DES"],
                 "T": ns["R323_F004_T_SP_C"]},
        "F010": {"w": ns["W_S317"], "a": ns["SOL_F010"], "M": ns["R323_F010_M_DES"],
                 "T": ns["R323_F010_T_SP_C"]},
    }
    second = lift(["sol_biuret_xi"], seed={
        "math": math, "SOL_STAGES": stages, "SOL_BIU_EA": ns["SOL_BIU_EA"],
        "SOL_BIU_ORDER": ns["SOL_BIU_ORDER"], "STRIP_R_GAS_J": ns["STRIP_R_GAS_J"],
    })
    ns["sol_biuret_xi"] = second["sol_biuret_xi"]
    return ns


def _blend(a: dict, b: dict, f: float) -> dict:
    """(1 - f) of liquor a with f of liquor b, by mass."""
    return {k: (1.0 - f) * a.get(k, 0.0) + f * b.get(k, 0.0) for k in ul.SOLUTION_SPECIES}


def _liquors(key: str) -> dict:
    """The design liquor of a stage and four departures from it, all physically reachable."""
    lean = {"C003": d.W_S208, "F004": d.W_S314, "F010": d.W_S319}[key]
    w_des = STAGES[key].w_des
    rich = dict(w_des)
    rich["Urea"] += 0.03
    rich["H2O"] -= 0.03
    return {
        "design": w_des,
        "quarter back to the feed": _blend(w_des, lean, 0.25),
        "half back to the feed": _blend(w_des, lean, 0.5),
        "three points richer in urea": rich,
        "nearly dry": {"Urea": 0.95, "Biuret": 0.01, "NH3": 0.0, "CO2": 0.0, "H2O": 0.04,
                       "HCHO": 0.0},
    }


LIQUOR_NAMES = ["design", "quarter back to the feed", "half back to the feed",
                "three points richer in urea", "nearly dry"]


# --------------------------------------------------------------------------------------
# The design basis
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("ours, theirs", [
    ("W_S208", "W_S208"), ("W_S314", "W_S314"), ("W_S319_TAB", "W_S319_TAB"),
    ("W_S319", "W_S319"), ("W_S331", "W_S331"), ("W_S317", "W_S317"),
    ("M305_DES_KGH", "R323_M305_DES"), ("M701_DES_KGH", "R323_M701_DES"),
    ("MEVAP_DES_KGH", "R323_MEVAP_DES"), ("M331_DES_KGH", "R323_M331_DES"),
    ("M331_T_C", "R323_M331_T_C"),
    ("C003_M_DES_KG", "R323_C003_M_DES"), ("F004_M_DES_KG", "R323_F004_M_DES"),
    ("F010_M_DES_KG", "R323_F010_M_DES"),
    ("C003_T_SP_C", "R323_C003_T_SP_C"), ("F004_T_SP_C", "R323_F004_T_SP_C"),
    ("F010_T_SP_C", "R323_F010_T_SP_C"),
    ("C003_P_BARA", "R323_C003_P_BARA"), ("F004_P_BARA", "R323_F004_P_BARA"),
    ("F010_P_BARA", "R323_F010_P_BARA"),
    ("C003_M_TAU_S", "R323_C003_M_TAU_S"), ("F004_M_TAU_S", "R323_F004_M_TAU_S"),
    ("F010_M_TAU_S", "R323_F010_M_TAU_S"),
    ("BIURET_ORDER", "SOL_BIU_ORDER"),
])
def test_design_basis(v1, ours, theirs):
    assert getattr(d, ours) == v1[theirs]


def test_the_shared_flow_chain_is_v1s(v1):
    assert (R323_FEED_DES_KGH, R323_M314_DES, R323_M319_DES, R323_M317_DES) == (
        v1["R323_FEED_DES_KGH"], v1["R323_M314_DES"], v1["R323_M319_DES"], v1["R323_M317_DES"])


@pytest.mark.parametrize("key", list(STAGES))
def test_stage_anchor(v1, key):
    theirs = v1[f"SOL_{key}"]
    a = STAGES[key].anchor
    assert (a.xi, a.y, a.alpha, a.resid, a.entrain) == (
        theirs["xi"], theirs["y"], theirs["alpha"], theirs["resid"], theirs["entrain"])


@pytest.mark.parametrize("key", list(STAGES))
def test_stage_design_memos(v1, key):
    st = STAGES[key]
    assert st.tbub_des_c == v1["SOL_TBUB_DES"][key]
    ref = v1["SOL_ALPHA_MODEL_DES"][key]
    if ref is None:
        assert st.alpha_model_des is None
    else:
        assert st.alpha_model_des == {k: ref[k] for k in ul.SOLUTION_SPECIES}
    raoult = {"C003": v1["bubble_T_raoult"](v1["R323_C003_P_BARA"], v1["W_S314"]),
              "F004": v1["bubble_T_raoult"](v1["R323_F004_P_BARA"], v1["W_S319"]),
              "F010": v1["R323_F010_TBUB_DES"]}[key]
    assert st.tbub_raoult_des_c == raoult


# --------------------------------------------------------------------------------------
# The liquor's own physics
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("key", list(STAGES))
@pytest.mark.parametrize("liquor", LIQUOR_NAMES)
def test_water_mole_fraction_and_raoult(v1, key, liquor):
    w = _liquors(key)[liquor]
    assert ul.x_water_mol(w) == v1["x_water_mol"](w)
    for p in (0.131, 0.46, 1.13, 4.1, 12.0):
        assert ul.bubble_t_raoult(p, w) == v1["bubble_T_raoult"](p, w), p


def test_a_waterless_liquor_holds_the_critical_temperature(v1):
    dry = {"Urea": 1.0}
    assert ul.bubble_t_raoult(4.1, dry) == v1["bubble_T_raoult"](4.1, dry)
    assert ul.x_water_mol({}) == v1["x_water_mol"]({}) == 1.0


@pytest.mark.parametrize("key", list(STAGES))
@pytest.mark.parametrize("liquor", LIQUOR_NAMES)
def test_vapour_by_relative_volatility(v1, key, liquor):
    w = _liquors(key)[liquor]
    alpha = STAGES[key].anchor.alpha
    assert ul.vapour_y(w, alpha) == v1["sol_vapour_y"](w, alpha)


def test_vapour_of_a_liquor_with_nothing_volatile(v1):
    alpha = d.C003_LIQUOR.anchor.alpha
    assert ul.vapour_y({}, alpha) == v1["sol_vapour_y"]({}, alpha)


@pytest.mark.parametrize("case", [
    ("W_S314", "R323_M314_DES", "R323_M319_DES", "W_S319_TAB"),
    ("W_S208", "R323_FEED_DES_KGH", "R323_M314_DES", "W_S314"),
    ("W_S319", "R323_M319_DES", "R323_M317_DES", "W_S317"),
])
def test_melt_reconciliation(v1, case):
    w_in, m_in, m_out, w_tab = (v1[n] for n in case)
    assert ul.reconcile_melt(w_in, m_in, m_out, w_tab) == v1["_reconcile_melt"](
        w_in, m_in, m_out, w_tab)


@pytest.mark.parametrize("entrain", [False, True])
@pytest.mark.parametrize("m_vap_scale", [0.5, 1.0, 1.5])
def test_the_back_solve_off_its_design_rows(v1, entrain, m_vap_scale):
    """The same back-solve on rows it was not built for, including the entrainment branch."""
    args = (v1["W_S208"], v1["W_S314"], v1["R323_FEED_DES_KGH"],
            v1["R323_M305_DES"] * m_vap_scale, v1["R323_M314_DES"])
    mine = ul.stage_anchor(*args, entrain=entrain)
    theirs = v1["_sol_stage_anchor"](*args, entrain=entrain)
    assert (mine.xi, mine.y, mine.alpha, mine.resid, mine.entrain) == (
        theirs["xi"], theirs["y"], theirs["alpha"], theirs["resid"], theirs["entrain"])


# --------------------------------------------------------------------------------------
# The stage layer at runtime
# --------------------------------------------------------------------------------------

def _states(key):
    st = STAGES[key]
    return [(st.t_des_c + dt, st.p_des_bara * fp)
            for dt in (-10.0, 0.0, 8.0) for fp in (0.85, 1.0, 1.15)]


@pytest.mark.parametrize("key", list(STAGES))
@pytest.mark.parametrize("liquor", LIQUOR_NAMES)
def test_model_volatility(v1, key, liquor):
    w = _liquors(key)[liquor]
    for t, p in _states(key):
        try:
            theirs = v1["_sol_model_alpha"](w, t, p)
        except ul.RIGOROUS_FAILURES as exc:
            # Both refuse; each raises its own package's OutOfDomain class.
            with pytest.raises(ul.RIGOROUS_FAILURES) as mine:
                ul.model_alpha(w, t, p)
            assert type(mine.value).__name__ == type(exc).__name__, (t, p)
            continue
        alpha, domain = ul.model_alpha(w, t, p)
        assert alpha == {k: theirs[k] for k in ul.SOLUTION_SPECIES}, (t, p)
        assert domain == theirs["_domain"], (t, p)


#: States on the grid where a solve needs 41 to 60 sweeps: V1's 40-sweep budget refuses there and
#: the stage falls back to its anchored vector; the port's 60-sweep budget converges.
BUDGET_STATES = [("F004", "design"), ("C003", "quarter back to the feed"),
                 ("C003", "half back to the feed")]


@pytest.mark.parametrize("key, liquor", BUDGET_STATES)
def test_the_flash_budget_decided_divergence(v1, key, liquor):
    """A-9, both sides: at least one state of each liquor's grid is refused by V1 on its own
    40 sweeps and converged by the port on 60 — to V1's own floats on the same budget."""
    w = _liquors(key)[liquor]
    fn = v1["_sol_model_alpha"]
    saved = fn.__globals__["thermo_service"]
    parted = 0
    try:
        for t_c, p in _states(key):
            fn.__globals__["thermo_service"] = v1_service(40)
            try:
                fn(w, t_c, p)
                continue
            except ul.RIGOROUS_FAILURES:
                pass
            fn.__globals__["thermo_service"] = saved
            try:
                ours, _ = ul.model_alpha(w, t_c, p)
            except ul.RIGOROUS_FAILURES:
                continue
            theirs = fn(w, t_c, p)
            assert ours == {k: theirs[k] for k in ul.SOLUTION_SPECIES}, (t_c, p)
            parted += 1
    finally:
        fn.__globals__["thermo_service"] = saved
    assert parted >= 1


@pytest.mark.parametrize("key", list(STAGES))
@pytest.mark.parametrize("liquor", LIQUOR_NAMES)
def test_bubble_point_departure(v1, key, liquor):
    st = STAGES[key]
    w = _liquors(key)[liquor]
    for _, p in _states(key):
        assert ls.bubble_t(st, w, p) == v1["sol_bubble_t_dep"](
            key, w, p, st.t_des_c, st.tbub_raoult_des_c), p


@pytest.mark.parametrize("key", list(STAGES))
@pytest.mark.parametrize("liquor", LIQUOR_NAMES)
def test_vapour_departure_and_its_domain(v1, key, liquor):
    st = STAGES[key]
    w = _liquors(key)[liquor]
    for t, p in _states(key):
        theirs = v1["sol_vapour_y_vle"](key, w, t, p, st.anchor.alpha)
        y, domain = ls.vapour(st, w, t, p)
        assert y == theirs, (t, p)
        assert domain == v1["SOL_VLE_DOMAIN"][key], (t, p)


@pytest.mark.parametrize("key", list(STAGES))
@pytest.mark.parametrize("liquor", LIQUOR_NAMES)
def test_biuret_extent(v1, key, liquor):
    st = STAGES[key]
    w = _liquors(key)[liquor]
    for m_scale in (0.0, 0.5, 1.0, 1.4):
        m = st.m_des_kg * m_scale
        for dt in (-20.0, 0.0, 15.0):
            t = st.t_des_c + dt
            assert ls.biuret_extent(st, m, w, t) == v1["sol_biuret_xi"](key, m, w, t), (m, t)


ADVANCE_CASES = {
    "steady design": dict(scale_in=1.0, scale_vap=1.0, scale_liq=1.0, second=False),
    "feed surge": dict(scale_in=1.3, scale_vap=1.0, scale_liq=0.9, second=False),
    "boil-up lost": dict(scale_in=1.0, scale_vap=0.0, scale_liq=1.0, second=False),
    "drain shut": dict(scale_in=1.0, scale_vap=1.0, scale_liq=0.0, second=False),
    "second feed": dict(scale_in=1.0, scale_vap=1.0, scale_liq=1.0, second=True),
    "everything off": dict(scale_in=0.0, scale_vap=0.0, scale_liq=0.0, second=False),
}


@pytest.mark.parametrize("key", list(STAGES))
@pytest.mark.parametrize("case", list(ADVANCE_CASES))
def test_species_advance(v1, key, case):
    c = ADVANCE_CASES[case]
    st = STAGES[key]
    w_in = {"C003": d.W_S208, "F004": d.W_S314, "F010": d.W_S319}[key]
    m_in = {"C003": R323_FEED_DES_KGH, "F004": R323_M314_DES, "F010": R323_M319_DES}[key]
    m_liq = {"C003": R323_M314_DES, "F004": R323_M319_DES, "F010": R323_M317_DES}[key]
    m_vap = {"C003": d.M305_DES_KGH, "F004": d.M701_DES_KGH, "F010": d.MEVAP_DES_KGH}[key]
    ours_second = {"m_in2_kgh": d.M331_DES_KGH, "w_in2": d.W_S331} if c["second"] else {}
    v1_second = {"m_in2": d.M331_DES_KGH, "w_in2": d.W_S331} if c["second"] else {}
    for dt in (0.1, 1.0):
        for m_new in (st.m_des_kg, 0.0):
            args = (st.w_des, st.m_des_kg, m_new, m_in * c["scale_in"], w_in,
                    m_vap * c["scale_vap"], st.anchor.y, m_liq * c["scale_liq"],
                    st.anchor.xi, dt)
            assert ls.advance_species(*args, **ours_second) == \
                v1["sol_advance"](*args, **v1_second), (dt, m_new)


def test_323c003s_urea_on_the_drain_decided_divergence():
    """B-20, decided 2026-10-10: PFD 314 closed on its urea against the drain. V1's row, the
    table's, leaves 8.16 kg/h of PFD 208's urea for its back-solve to send overhead, an apparent
    volatility of 7.92e-4 its runtime zeroes; on the port's row the urea leaves by the drain and the
    anchor's vapour carries none. V1's PFD 314 is the port's table row, so the two differ only in
    the urea and the water that give way to it (+0.00771 points)."""
    ns = lift(V1_NAMES, seed={"math": math, "iapws_if97": load("iapws_if97"),
                              "thermo_service": v1_service()})
    assert ns["W_S314"] == pytest.approx(d.W_S314_TAB, rel=1e-15)
    m305 = ns["R323_M305_DES"]
    assert ns["SOL_C003"]["y"]["Urea"] * m305 == pytest.approx(8.164, abs=1e-3)
    assert ns["SOL_C003"]["alpha"]["Urea"] == pytest.approx(7.92e-4, abs=1e-6)
    assert d.C003_LIQUOR.anchor.y["Urea"] == 0.0 and d.C003_LIQUOR.anchor.alpha["Urea"] == 0.0
    assert (d.W_S314["Urea"] - d.W_S314_TAB["Urea"]) * 100.0 == pytest.approx(0.00771, abs=1e-5)
    assert d.W_S314["Urea"] + d.W_S314["H2O"] == pytest.approx(
        d.W_S314_TAB["Urea"] + d.W_S314_TAB["H2O"], rel=1e-14)
