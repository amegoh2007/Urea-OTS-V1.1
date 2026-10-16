"""V1 <-> V1.1 equivalence for 323C005, the atmospheric absorber, and the saturated-gas vent law.

What is being proved
--------------------
V1 writes the absorber inline in `step_sim`, so its statements are TRANSCRIBED into
`_v1_stage1` below, line for line, and declared as such (``main.py`` 8847-8881). Everything
they call is V1's own code, executed: ``c005_vent_kgh``, ``c005_sump_step`` and the sump
geometry lifted out of ``main.py``, ``vacuum_condenser`` and ``iapws_if97`` loaded. The state
is seeded as ``State.__init__`` seeds it (6877-6878).

The saturated-gas law is compared with V1's ``vacuum_condenser`` on its own; the sump and the
vent at many states; then the absorber is driven through scenarios chosen to take every branch
— each gas up and down, the solvent cut until the liquor boils, the solvent warm, 324E002's
inerts moved, the sump emptied and refilled — and last coupled to V1's 323E011 through V1's
``R3232_702`` tear: V1 steps the absorber first in its LP block, so it takes 323E011's vent of
the tick before, and so does the port. Every tick compares every published field and the state
with ``==``.
"""

from __future__ import annotations

import math

import pytest

from ureasim.data import unit_323c005 as c
from ureasim.data import unit_323e011 as e
from ureasim.data.unit_322c001 import C001_T_C
from ureasim.thermo import saturated_vent as sv
from ureasim.units.desorption import atmospheric_absorber as aa
from ureasim.units.recirc import flash_condenser as fc
from tests.equivalence import routes_switch
from tests.equivalence import test_flash_condenser_equivalence as stage9
from tests.equivalence import test_pre_evaporator_equivalence as stage3
from tests.equivalence.v1_loader import lift, load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

C005_NAMES = [
    "A323_C005_M756_DES", "A323_C005_M702_DES", "A323_C005_M708_DES", "A323_C005_VENT_DES",
    "A323_C005_BOT_DES", "A323_C005_T", "A323_C005_ID_M", "A323_C005_HEAD_A_M",
    "A323_C005_N4_ID_M", "A323_C005_RHO", "A323_C005_P_BARA", "A323_C005_CD_ORIF",
    "A323_C005_C_WEIR", "c005_sump_volume_m3", "c005_sump_head_m", "c005_drain_m3s",
    "_c005_design_head_m", "A323_C005_M_DES", "A323_C005_Q_REF", "c005_sump_step",
    "A323_C005_ABS_DES", "A323_C005_SENS_DES", "A323_C005_LAM", "A323_C005_VENT_SPEC",
    "_C005_N702", "_C005_N708", "_C005_CAP", "_E002_INERT_DES", "c005_vent_kgh", "R3232_CP",
    "A328_C001_T", "PFD_324_MASS_PCT", "R3232_E011_MV_DES",
]

DT = 0.1


@pytest.fixture(scope="module")
def v1():
    ns = stage3.build_v1(stage9.V1_NAMES)
    # The isometrics' geometry (handoff A-11, decided 2026-10-07): `routes_switch`.
    ns["D002_ROUTE"] = routes_switch.decided(ns, "323F010_TO_323D002")
    ns["coupling"] = load("c003_pressure_coupling")
    ns["vacuum_condenser"] = load("vacuum_condenser")
    ns.update(lift(C005_NAMES, seed={"math": math, "vacuum_condenser": ns["vacuum_condenser"],
                                     "iapws_if97": load("iapws_if97")}))
    return ns


def _v1_state(v1):
    """The V1 plant-state fields the absorber and 323E011 read and write, seeded as
    `State.__init__` seeds them (323E011 from its own test, the absorber from ``main.py``
    6877-6878, 322C001's temperature from 6872)."""
    s = stage9._v1_state(v1)
    s.a323_c005_M = v1["A323_C005_M_DES"]
    s.a323_c005_T = v1["A323_C005_T"]
    s.a328_c001_T = v1["A328_C001_T"]
    return s


def _v1_stage1(v1, s, dt):
    """V1 `main.py` 8835-8837 and 8847-8881, the absorber's tears and stage 1, TRANSCRIBED line
    for line; the 706 inerts read as 8854 reads them."""
    g = v1
    m702_prev = s.tlag.get("R3232_702", g["A323_C005_M702_DES"])
    m756_prev = s.tlag.get("R322_756", g["A323_C005_M756_DES"])
    m708_prev = s.tlag.get("R324_708", g["A323_C005_M708_DES"])
    Tc005 = s.a323_c005_T
    gas_c005 = m702_prev + m708_prev
    m_341 = min(g["c005_vent_kgh"](m702_prev,
                                   s.tlag.get("R324_706_INERT", g["_E002_INERT_DES"]),
                                   s.a328_c001_T),
                gas_c005)
    abs_c005 = max(gas_c005 - m_341, 0.0)
    in_c005 = m756_prev + gas_c005
    CP, LAM = g["R3232_CP"], g["A323_C005_LAM"]
    P_c005 = ((m756_prev / 3600.0 * CP * (g["A328_C001_T"] - Tc005)
               + m702_prev / 3600.0 * CP * (45.0 - Tc005)
               + m708_prev / 3600.0 * CP * (121.0 - Tc005))
              + abs_c005 / 3600.0 * LAM)
    k_cap_c005 = (m756_prev + m702_prev + m708_prev) / 3600.0 * CP
    _den_c005 = s.a323_c005_M * CP + k_cap_c005 * dt
    _tbp_c005 = g["iapws_if97"].tsat_c(g["A323_C005_P_BARA"])
    lim = False
    if abs_c005 > 0.0 and Tc005 + P_c005 * dt / max(_den_c005, 1e-6) > _tbp_c005:
        _abs_cap = max(((_tbp_c005 - Tc005) * _den_c005 / dt
                        - (P_c005 - abs_c005 / 3600.0 * LAM)) * 3600.0 / LAM, 0.0)
        if _abs_cap < abs_c005:
            P_c005 -= (abs_c005 - _abs_cap) / 3600.0 * LAM
            abs_c005 = _abs_cap
            m_341 = gas_c005 - abs_c005
            lim = True  # (the port's flag; V1 raises none)
    m_c005_next, bot_c005 = g["c005_sump_step"](s.a323_c005_M, m756_prev + abs_c005, dt)
    s.a323_c005_T = Tc005 + P_c005 * dt / max(_den_c005, 1e-6)
    s.a323_c005_M = m_c005_next
    return {"gas": gas_c005, "in": in_c005, "341": m_341, "abs": abs_c005, "lim": lim,
            "343": bot_c005,
            # main.py 10729, the head the telemetry reads.
            "head": g["c005_sump_head_m"](s.a323_c005_M)}


def _assert_tick(a: dict, b: aa.AtmosphericAbsorberResult, s, unit, label):
    assert (a["gas"], a["in"], a["341"], a["abs"], a["lim"], a["343"]) == (
        b.gas_kgh, b.in_kgh, b.m_341_kgh, b.abs_kgh, b.boil_limited, b.m_343_kgh), label
    assert (s.a323_c005_T, s.a323_c005_M, a["head"]) == (b.t_c, b.m_kg, b.sump_head_m), label
    assert (b.t_c, b.m_kg) == (unit.t_c, unit.m_kg), label


# --------------------------------------------------------------------------------------
# The design basis
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("ours, theirs", [
    ("C005_M756_DES_KGH", "A323_C005_M756_DES"), ("C005_M702_DES_KGH", "A323_C005_M702_DES"),
    ("C005_M702_DES_KGH", "R3232_E011_MV_DES"), ("C005_M708_DES_KGH", "A323_C005_M708_DES"),
    ("C005_VENT_DES_KGH", "A323_C005_VENT_DES"), ("C005_BOT_DES_KGH", "A323_C005_BOT_DES"),
    ("C005_T_C", "A323_C005_T"), ("C005_T756_C", "A328_C001_T"), ("C005_CP", "R3232_CP"),
    ("C005_ID_M", "A323_C005_ID_M"), ("C005_HEAD_A_M", "A323_C005_HEAD_A_M"),
    ("C005_N4_ID_M", "A323_C005_N4_ID_M"), ("C005_RHO_KGM3", "A323_C005_RHO"),
    ("C005_P_BARA", "A323_C005_P_BARA"), ("C005_CD_ORIFICE", "A323_C005_CD_ORIF"),
    ("C005_C_WEIR", "A323_C005_C_WEIR"), ("C005_ABS_DES_KGH", "A323_C005_ABS_DES"),
    ("C005_SENS_DES_KW", "A323_C005_SENS_DES"), ("C005_LAM_KJKG", "A323_C005_LAM"),
    ("C005_N702_KMOLH", "_C005_N702"), ("C005_N708_KMOLH", "_C005_N708"),
    ("C005_CAP_KMOLH", "_C005_CAP"), ("E002_INERT_DES_KMOLH", "_E002_INERT_DES"),
])
def test_design_basis(v1, ours, theirs):
    assert getattr(c, ours) == v1[theirs]


@pytest.mark.parametrize("row", ["341", "702", "708", "703"])
def test_the_pfd_vapour_rows(v1, row):
    assert getattr(c, f"PFD_{row}_MOL_PCT") == v1["PFD_324_MASS_PCT"][row]


def test_the_vent_spec_and_the_sump_anchors(v1):
    theirs = v1["A323_C005_VENT_SPEC"]
    ours = c.C005_VENT_SPEC
    assert (ours.p_des, ours.t_v_des, ours.psat_v_des, ours.y_des, ours.split) == (
        theirs["p_des"], theirs["t_v_des"], theirs["psat_v_des"], theirs["y_des"],
        theirs["split"])
    assert (aa.SUMP_M_DES_KG, aa.SUMP_Q_REF_M3S) == (v1["A323_C005_M_DES"], v1["A323_C005_Q_REF"])
    assert aa.T_BOIL_C == v1["iapws_if97"].tsat_c(v1["A323_C005_P_BARA"])
    # The design state is exact: 80 kg/h of vent and 34 180 of bottoms.
    assert aa.vent_kgh(c.C005_M702_DES_KGH, c.E002_INERT_DES_KMOLH, c.C005_T756_C) == 80.0
    assert aa.sump_step(aa.SUMP_M_DES_KG, c.C005_M756_DES_KGH + c.C005_ABS_DES_KGH, DT) == (
        aa.SUMP_M_DES_KG, c.C005_BOT_DES_KGH)


# --------------------------------------------------------------------------------------
# The saturated-gas law against V1's vacuum_condenser
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("row, total", [("341", 2.91), ("702", 24.99), ("708", 24.64),
                                        ("703", 1454.67), ("706", 17.3)])
def test_moles_from_mole_pct(v1, row, total):
    pct = v1["PFD_324_MASS_PCT"][row]
    assert sv.moles_from_mole_pct(total, pct) == v1["vacuum_condenser"].moles_from_mole_pct(
        total, pct)


@pytest.mark.parametrize("row, p, t", [("341", 1.0, 43.0), ("706", 0.33, 45.0),
                                       ("722", 1.0, 55.0), ("712", 0.131, 40.0)])
def test_saturated_gas_spec(v1, row, p, t):
    theirs = v1["vacuum_condenser"].saturated_gas_spec(v1["PFD_324_MASS_PCT"][row], p, t)
    ours = sv.saturated_gas_spec(v1["PFD_324_MASS_PCT"][row], p, t)
    assert (ours.p_des, ours.t_v_des, ours.psat_v_des, ours.y_des, ours.split) == (
        theirs["p_des"], theirs["t_v_des"], theirs["psat_v_des"], theirs["y_des"],
        theirs["split"])


@pytest.mark.parametrize("p, t, scale_inert, scale_cond", [
    (1.0, 43.0, 1.0, 1.0), (1.0, 60.0, 1.0, 1.0), (1.0, 20.0, 2.0, 0.5), (0.5, 43.0, 1.0, 1.0),
    (0.1, 80.0, 1.0, 1.0), (1.0, 99.0, 3.0, 1.0), (2.0, 43.0, 0.0, 1.0), (1.0, 43.0, 1.0, 0.0),
    (0.0, 43.0, 1.0, 1.0), (1.0, 105.0, 1.0, 1.0),
])
def test_vent_moles_and_mass(v1, p, t, scale_inert, scale_cond):
    vc = v1["vacuum_condenser"]
    n = {k: v * (scale_inert if k in sv.INERT else scale_cond)
         for k, v in c.C005_N702_KMOLH.items()}
    theirs = vc.vent_moles(v1["A323_C005_VENT_SPEC"], p, t, n)
    ours = sv.vent_moles(c.C005_VENT_SPEC, p, t, n)
    assert ours == theirs
    assert sv.vent_mass_kgh(ours) == vc.vent_mass_kgh(theirs)


# --------------------------------------------------------------------------------------
# The sump and the vent at many states
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("h", [0.0, 1e-4, 0.049, 0.1, 0.295, 0.3, 0.5, 2.0, -0.1])
def test_the_sump_geometry_and_drain(v1, h):
    assert aa.sump_volume_m3(h) == v1["c005_sump_volume_m3"](h)
    assert aa.sump_drain_m3s(h) == v1["c005_drain_m3s"](h)


@pytest.mark.parametrize("m", [0.0, 1e-3, 8.07, 50.0, 300.0, 322.6, 1000.0, 5000.0, -1.0])
def test_the_sump_head(v1, m):
    assert aa.sump_head_m(m) == v1["c005_sump_head_m"](m)


@pytest.mark.parametrize("m, m_in, dt", [
    (8.069798271204863, 34180.0, 0.1), (8.0, 34180.0, 0.1), (8.0, 0.0, 0.1), (0.0, 0.0, 0.1),
    (0.0, 34180.0, 0.1), (50.0, 34180.0, 1.0), (8.0, 90000.0, 0.1), (400.0, 0.0, 1.0),
    (8.0, 34180.0, 0.0), (8.0, -10.0, 0.1),
])
def test_the_sump_step(v1, m, m_in, dt):
    assert aa.sump_step(m, m_in, dt) == v1["c005_sump_step"](m, m_in, dt)


@pytest.mark.parametrize("m702, f706, t", [
    (440.0, 1.0, 43.0), (880.0, 1.0, 43.0), (0.0, 1.0, 43.0), (440.0, 2.0, 43.0),
    (440.0, 0.0, 43.0), (440.0, 1.0, 55.0), (440.0, 1.0, 20.0), (1320.0, 0.5, 70.0),
    (0.0, 0.0, 43.0),
])
def test_the_vent(v1, m702, f706, t):
    inert = {k: v * f706 for k, v in c.E002_INERT_DES_KMOLH.items()}
    assert aa.vent_kgh(m702, inert, t) == v1["c005_vent_kgh"](m702, dict(inert), t)


# --------------------------------------------------------------------------------------
# The absorber on its own, tick by tick
# --------------------------------------------------------------------------------------

M702, M756, M708 = c.C005_M702_DES_KGH, c.C005_M756_DES_KGH, c.C005_M708_DES_KGH


def _design(**over):
    base = {"m702": M702, "m756": M756, "m708": M708, "f706": 1.0, "t_solvent": c.C005_T756_C}
    base.update(over)
    return base


def _run(v1, script, ticks: int, dt: float = DT):
    """Drive the absorber alone through `script(k)`, comparing everything every tick, on V1's
    inlet temperatures: 756 at the solvent's live one (B-31) has its own test."""
    s = _v1_state(v1)
    unit = aa.AtmosphericAbsorber(live_inlets=False)
    b = None
    for k in range(ticks):
        x = script(k)
        inert = {q: v * x["f706"] for q, v in c.E002_INERT_DES_KMOLH.items()}
        s.tlag["R3232_702"], s.tlag["R322_756"], s.tlag["R324_708"] = (x["m702"], x["m756"],
                                                                       x["m708"])
        s.tlag["R324_706_INERT"] = dict(inert)
        s.a328_c001_T = x["t_solvent"]
        a = _v1_stage1(v1, s, dt)
        b = unit.step(x["m702"], x["m756"], x["m708"], inert, x["t_solvent"], dt)
        _assert_tick(a, b, s, unit, f"tick {k}")
    return s, unit, b


def _step(t0: int, **over):
    return lambda k: _design(**(over if k >= t0 else {}))


SCENARIOS = {
    "design hold": (lambda k: _design(), 600, DT),
    "an NH3 surge on 702, three times its flow": (_step(10, m702=3.0 * M702), 1200, 0.5),
    "702 gone (PV-323203 shut)": (_step(10, m702=0.0), 1200, 0.5),
    "708 up half": (_step(10, m708=1.5 * M708), 1200, 0.5),
    "the solvent halved": (_step(10, m756=0.5 * M756), 1200, 0.5),
    "the solvent cut: the liquor boils": (_step(10, m756=0.0), 1200, 0.5),
    "the solvent cut at the engine's step": (_step(10, m756=0.0), 3000, DT),
    "the solvent warm, 55 C": (_step(10, t_solvent=55.0), 1200, 0.5),
    "324E002's inerts doubled": (_step(10, f706=2.0), 600, 0.5),
    "everything gone: the sump drains empty": (
        _step(10, m702=0.0, m756=0.0, m708=0.0, f706=0.0), 600, DT),
    "the solvent back after a cut": (
        lambda k: _design(m756=(0.0 if 10 <= k < 300 else M756)), 1200, 0.5),
}


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_the_absorber_tick_by_tick(v1, name):
    script, ticks, dt = SCENARIOS[name]
    s, unit, b = _run(v1, script, ticks, dt)
    if name.startswith("the solvent cut"):
        assert b.boil_limited and b.t_c == pytest.approx(aa.T_BOIL_C, abs=1e-6)
    if name.startswith("everything gone"):
        assert b.m_343_kgh < 1.0 and unit.m_kg < 0.01


# --------------------------------------------------------------------------------------
# Coupled: the absorber takes 323E011's vent one tick later, through V1's R3232_702 tear
# --------------------------------------------------------------------------------------

def test_the_absorber_takes_323e011s_vent_one_tick_later(v1):
    """V1's stage 1 at the top of the tick, V1's stage 9 after it, and the tear write at the end
    of V1's block (``main.py`` 9667), against the ported absorber and condenser in the same
    order: the absorber reads 323E011's vent of the tick before — V1's own one-tick tear, and no
    other delay. PFD 701 up 10 % moves 702, and 702 moves the absorber's vent and bottoms."""
    s = _v1_state(v1)
    unit = aa.AtmosphericAbsorber()
    cond, loops9 = fc.FlashCondenser(**fc.V1_CONDENSER), stage9._loops()
    m702_prev = c.C005_M702_DES_KGH
    inert = dict(c.E002_INERT_DES_KMOLH)
    moved = False
    for k in range(3000):
        x = stage9._design(m701=stage9.M701 * (1.1 if k >= 10 else 1.0))
        a1 = _v1_stage1(v1, s, DT)
        a9 = stage9._v1_stage9(v1, s, x["m701"], x["b505"], x["b501"], x["m786"], x["m321"],
                               x["m402"], DT)
        s.tlag["R3232_702"] = a9["vent"]
        b1 = unit.step(m702_prev, M756, M708, inert, c.C005_T756_C, DT)
        b9 = cond.step(*loops9, x["m701"], x["b505"], x["b501"], x["m786"], x["m321"],
                       x["m402"], DT)
        m702_prev = b9.m_702_kgh
        _assert_tick(a1, b1, s, unit, f"stage 1, tick {k}")
        stage9._assert_tick(a9, b9, s, cond, loops9, f"stage 9, tick {k}")
        moved = moved or b1.m_341_kgh != c.C005_VENT_DES_KGH
    assert moved and b9.m_702_kgh > e.E011_MV_DES_KGH


# --------------------------------------------------------------------------------------
# Decided divergence: 323E011's overflow (2026-10-03, handoff A-20)
# --------------------------------------------------------------------------------------

def test_a20_323e011s_overflow_reaches_the_sump_where_v1_has_none(v1):
    """Asserted both ways. V1's stage 1 has no inlet for 323E011's overflow — V1's envelope has no
    ceiling, so it never overflows — and V1's column holds its design on the three streams. The
    port's, handed 8.2 t/h at 46 C through PV-323203's vent line, keeps V1's vent and absorption
    to the bit and passes the overflow through its sump: V1's bottoms plus the overflow, and a
    cooler liquor. Handed none, it is V1's on every tick (every scenario above). On V1's inlet
    temperatures: 702 at the condensate's live 46 C (B-31) has its own test."""
    s = _v1_state(v1)
    unit = aa.AtmosphericAbsorber(live_inlets=False)
    inert = dict(c.E002_INERT_DES_KMOLH)
    for k in range(3000):
        a = _v1_stage1(v1, s, DT)
        b = unit.step(M702, M756, M708, inert, c.C005_T756_C, DT,
                      m_e011_over_kgh=8200.0, t_e011_over_c=46.0)
        assert (a["gas"], a["in"], a["341"], a["abs"], a["lim"]) == (
            b.gas_kgh, b.in_kgh, b.m_341_kgh, b.abs_kgh, b.boil_limited), f"tick {k}"
    assert (a["343"], s.a323_c005_T) == (c.C005_BOT_DES_KGH, c.C005_T_C)
    assert b.m_343_kgh == pytest.approx(a["343"] + 8200.0, rel=1e-9)
    assert b.e011_over_kgh == 8200.0 and b.t_c == pytest.approx(53.26, abs=0.01)


def test_the_inlets_at_their_producers_temperatures_decided_divergence(v1):
    """B-31, decided 2026-10-16: 323C005 charges 756 and 702 at 322C001's and 323E011's live
    temperatures, each as its departure from its producer's design; V1 at 43 and 45 C whatever
    they do, though its vent reads the same solvent's live temperature. 708 stays at 121 C. With
    both producers on their designs the port is V1's on every tick, and so it is with both 5 K hot
    on V1's switch. Live, the sump's few kilograms follow the solvent: 2.67 K hotter on the first
    one-second tick, and after half an hour 59.893 C against V1's 54.960 C, the vent and the
    bottoms unmoved (both sides' vent reads the same solvent)."""
    def run(t_solvent, t_e011, live, ticks, dt, check):
        s = _v1_state(v1)
        unit = aa.AtmosphericAbsorber(live_inlets=live)
        x = _design(t_solvent=t_solvent)
        inert = dict(c.E002_INERT_DES_KMOLH)
        first = None
        for k in range(ticks):
            s.tlag["R3232_702"], s.tlag["R322_756"], s.tlag["R324_708"] = (x["m702"], x["m756"],
                                                                           x["m708"])
            s.tlag["R324_706_INERT"] = dict(inert)
            s.a328_c001_T = x["t_solvent"]
            a = _v1_stage1(v1, s, dt)
            b = unit.step(x["m702"], x["m756"], x["m708"], inert, x["t_solvent"], dt,
                          t_e011_over_c=t_e011)
            if check:
                _assert_tick(a, b, s, unit, f"live {live}, tick {k}")
            if first is None:
                first = unit.t_c - s.a323_c005_T
        return s, unit, a, b, first
    run(C001_T_C, e.E011_T_C, True, 600, DT, True)
    run(C001_T_C + 5.0, e.E011_T_C + 5.0, False, 600, DT, True)
    s, unit, a, b, first = run(C001_T_C + 5.0, e.E011_T_C + 5.0, True, 1800, 1.0, False)
    assert first == pytest.approx(2.6692, abs=1e-4)
    assert (s.a323_c005_T, unit.t_c) == (pytest.approx(54.9604, abs=1e-4),
                                         pytest.approx(59.8930, abs=1e-4))
    assert (a["341"], a["343"]) == (b.m_341_kgh, b.m_343_kgh)


def test_708_at_324f002s_discharge_decided_divergence(v1):
    """B-97, decided 2026-10-16: 323C005 charges 708 at 324F002's discharge temperature, the
    vacuum train's adiabatic mix as its departure from the design mix; V1 at 121 C, its train
    publishing no temperature. At the design's 121 C the port is V1's on every tick, and so it is
    with 708 at the 63.04 C a shut HIC-329605 sends on V1's switch. Live at 63.04 C the liquor
    runs cooler: 0.4230 K on the first one-second tick, after half an hour 54.2184 C against V1's
    55.0, the vent and the bottoms unmoved."""
    def run(t_708, live, ticks, dt, check):
        s = _v1_state(v1)
        unit = aa.AtmosphericAbsorber(live_inlets=live)
        x = _design()
        inert = dict(c.E002_INERT_DES_KMOLH)
        first = None
        for k in range(ticks):
            s.tlag["R3232_702"], s.tlag["R322_756"], s.tlag["R324_708"] = (x["m702"], x["m756"],
                                                                           x["m708"])
            s.tlag["R324_706_INERT"] = dict(inert)
            s.a328_c001_T = x["t_solvent"]
            a = _v1_stage1(v1, s, dt)
            b = unit.step(x["m702"], x["m756"], x["m708"], inert, x["t_solvent"], dt,
                          t_708_c=t_708)
            if check:
                _assert_tick(a, b, s, unit, f"live {live}, tick {k}")
            if first is None:
                first = s.a323_c005_T - unit.t_c
        return s, unit, a, b, first
    run(c.C005_T708_C, True, 600, DT, True)
    run(63.04, False, 600, DT, True)
    s, unit, a, b, first = run(63.04, True, 1800, 1.0, False)
    assert first == pytest.approx(0.4230, abs=1e-4)
    assert (s.a323_c005_T, unit.t_c) == (pytest.approx(55.0, abs=1e-9),
                                         pytest.approx(54.2184, abs=1e-4))
    assert (a["341"], a["343"]) == (b.m_341_kgh, b.m_343_kgh)
