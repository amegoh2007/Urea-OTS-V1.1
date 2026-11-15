"""V1 <-> V1.1 equivalence for unit 321, the NH3 pumping station.

What is being proved
--------------------
`ureasim.units.feed` is the first unit operation ported, and it sets the pattern for the
seven sections that follow. The evidence standard is therefore worth stating precisely,
because it is a MIXTURE and the mixture is the best available:

  * **executed V1 code** — the pump capacity law, the motor-current proxy, the ammonia
    saturation curve, the transport-time law, the timestamped dead-time FIFO, and the whole
    SIC-321950/951 controller. These are lifted out of `main.py` by AST, or imported from
    `controllers.py`, and RUN. They are most of the arithmetic.
  * **transcribed wiring** — the roughly thirty assignment statements of `step_sim` that glue
    those together, which cannot be lifted because they live inside a 4,100-line function
    reading a plant state that exists only after `main.py` has built a FastAPI application.
    They are copied here line for line into `_v1_feed_block` and checked by eye.

So a defect in a correlation cannot hide — V1's own correlation is running. A defect in the
ORDER things are done in would have to survive a line-for-line copy. That is the same
standard `tests/control/test_interlocks.py` runs at and is tracked by the same open item,
handoff A-12.

Two properties are pinned beyond tick-for-tick equality:

  * **the design fixed point.** At 54.618 t/h of CO2 with pump B at its derived design
    opening, the station must deliver exactly `EJ_MOTIVE_NH3_DES`, the drum level must not
    move at all, and `phi_motive` must be exactly 1.0. That is the boot pin.
  * **the ratio validity gate.** Below 5 % of design CO2 the published N/C must HOLD its last
    good value and raise its bad flag, not divide by a collapsing number.

Handoffs B-6 and B-7, decided 2026-10-07
----------------------------------------
The port converts gauge to absolute on the standard atmosphere, 1.01325 bar, and reads the drum's
head on standard gravity, 9.80665 m/s2, where V1's block writes 1.013 and 9.81. The transcription
carries the switch ``atm_decided`` (default True, on the state): the decided constants in V1's
lines; ``atm_decided=False`` is V1 verbatim. Both sides are asserted in the last section.
"""

from __future__ import annotations

import ast
import math
from types import SimpleNamespace

import pytest

from ureasim.data import unit_321 as d
from ureasim.units.feed.feed_drum import FeedDrum
from ureasim.units.feed.pump import ReciprocatingPump
from ureasim.units.feed.station import FeedStation
from tests.equivalence.v1_loader import V1_BACKEND, load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

DT = 0.1

#: Design CO2 feed to the loop [t/h] — 100 % load.
CO2_DES_TH = d.CO2_DES_KGH / 1000.0


def _v1_module() -> dict:
    """Lift unit 321's pure functions out of V1 `main.py` and execute them there.

    The namespace is seeded with V1's own module constants, computed here the same way V1
    computes them, and with V1's real `hydraulics` module — so `_feed_transport_td_s` calls
    the same `transport_time_s` the engine calls.
    """
    text = (V1_BACKEND / "main.py").read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(text)
    wanted = {"clamp", "pump_flow_m3h", "pump_shaft_power_kW", "pump_current_A",
              "psat_nh3_bara", "mode_tag", "_feed_transport_td_s", "_delay"}
    ns: dict = {
        "math": math,
        "hydraulics": load("hydraulics"),
        "deque": __import__("collections").deque,
        # V1 module constants, derived exactly as V1 derives them.
        "PUMP_V_PER_REV": (math.pi / 4.0) * 0.140 ** 2 * 0.205 * 3,
        "PUMP_ETA_V": 0.980,
        "PUMP_ETA_M": 0.915,
        "PUMP_RATED_RPM": 152.0,
        "PUMP_RATED_I": 51.0,
        "FEED_TD_MAX_S": 3600.0,
    }
    for stmt in tree.body:
        if isinstance(stmt, ast.FunctionDef) and stmt.name in wanted:
            exec(compile(ast.Module([stmt], []), "<v1 main.py>", "exec"), ns)
    missing = wanted - set(ns)
    assert not missing, f"could not lift {sorted(missing)} out of V1 main.py"
    return ns


@pytest.fixture(scope="module")
def v1():
    return _v1_module()


@pytest.fixture(scope="module")
def v1_controllers():
    return load("controllers")


# --------------------------------------------------------------------------------------
# V1's constants, derived here the way V1 derives them
# --------------------------------------------------------------------------------------
#  Quoted from `backend/main.py` rather than imported, because `main.py` cannot be imported.
#  Every one is asserted against the rewrite's copy below, so a transcription slip fails.

V1_NH3_RHO = 604.8
V1_G = 9.81
V1_PUMP_V_PER_REV = (math.pi / 4.0) * 0.140 ** 2 * 0.205 * 3
V1_PUMP_ETA_V = 0.980
V1_PUMP_RATED_RPM = 152.0
V1_TANK_VOL = (math.pi / 4.0) * 0.970 ** 2 * 1.400
V1_TANK_H = 1.400
V1_TANK_LEVEL_SP_FRAC = 0.65
V1_TANK_LIC_KP_TH = 80.0
V1_TANK_BL_MAX_TH = 90.0
V1_P_SYN_DOWN_BAR = 165.0
V1_P_ATM_BAR = 1.013
#: The decided atmosphere and gravity (handoffs B-6, B-7): the port's one of each.
DECIDED_P_ATM_BAR = 1.01325
DECIDED_G = 9.80665
V1_CP_NH3 = 4740.0
V1_BETA_NH3 = 1.9e-3
V1_ETA_PUMP_HYD = 0.85
V1_T_BL_FEED_C = 25.0
V1_M_NH3 = 17.031
V1_M_CO2 = 44.009
V1_NC_FACTOR = V1_M_CO2 / V1_M_NH3
V1_NC_TO_MASS = V1_M_NH3 / V1_M_CO2
V1_CO2_DES_KGH = 54618.0
V1_EJ_MOTIVE_NH3_DES = 42762.05427809782
V1_FEED_TD_S = 345.0
V1_FEED_NH3_LINE_KG = V1_EJ_MOTIVE_NH3_DES / 3600.0 * V1_FEED_TD_S
V1_OPEN_DES_B = ((V1_EJ_MOTIVE_NH3_DES / V1_NH3_RHO)
                 / (V1_PUMP_V_PER_REV * V1_PUMP_ETA_V * 60.0) / V1_PUMP_RATED_RPM * 100.0)
V1_RATIO_DES = 2.0231315310702604
#: B-85's output scale: one per cent of FFIC-321404's output in the SIC's opening, SI-321950's
#: 180 rpm maximum over the rated 152 rpm (UD-MR-321-FF-0002 pages 2-3).
B85_OUT_TO_OPENING = 180.0 / 152.0


def test_every_constant_the_rewrite_carries_is_v1s_own_number():
    """A constant silently retyped is the cheapest way to move a published flow."""
    assert d.NH3_RHO == V1_NH3_RHO
    assert d.PUMP_V_PER_REV == V1_PUMP_V_PER_REV
    assert d.PUMP_ETA_V == V1_PUMP_ETA_V
    assert d.PUMP_ETA_M == 0.915
    assert d.PUMP_RATED_RPM == V1_PUMP_RATED_RPM
    assert d.PUMP_RATED_I == 51.0
    assert d.PUMP_IDLE_I == 0.2
    assert d.TANK_VOL == V1_TANK_VOL
    assert d.TANK_H == V1_TANK_H
    assert d.TANK_LEVEL_SP_FRAC == V1_TANK_LEVEL_SP_FRAC
    assert d.TANK_LIC_KP_TH == V1_TANK_LIC_KP_TH
    assert d.TANK_BL_MAX_TH == V1_TANK_BL_MAX_TH
    assert d.TANK_LEVEL_MIN_FRAC == 0.05
    assert d.SUCTION_LOSS_BAR == 0.15
    assert d.P_SYN_DOWN_BAR == V1_P_SYN_DOWN_BAR
    assert d.CP_NH3 == V1_CP_NH3
    assert d.BETA_NH3 == V1_BETA_NH3
    assert d.ETA_PUMP_HYD == V1_ETA_PUMP_HYD
    assert d.T_BL_FEED_C == V1_T_BL_FEED_C
    assert d.M_NH3 == V1_M_NH3
    assert d.M_CO2 == V1_M_CO2
    assert d.NC_FACTOR == V1_NC_FACTOR
    assert d.NC_TO_MASS == V1_NC_TO_MASS
    assert d.CO2_DES_KGH == V1_CO2_DES_KGH
    assert d.EJ_MOTIVE_NH3_DES == V1_EJ_MOTIVE_NH3_DES
    assert d.FEED_TD_S == V1_FEED_TD_S
    assert d.FEED_NH3_LINE_KG == V1_FEED_NH3_LINE_KG
    assert d.PUMP_OPEN_DES_PCT == V1_OPEN_DES_B
    assert d.RATIO_SP_DES == V1_RATIO_DES


def test_the_port_carries_one_atmosphere_and_one_gravity():
    """V1's suction head uses G = 9.81 and P_ATM_BAR = 1.013; its `consequence.py` standard
    gravity and 1.01325. The port carries one of each, the standard values (handoffs B-6, B-7,
    decided 2026-10-07): the drum's head at the design level is 1.84e-5 bar less than V1's."""
    from ureasim.core.units_of_measure import ATM_BARA, G_ACC
    assert (G_ACC, ATM_BARA) == (DECIDED_G, DECIDED_P_ATM_BAR)
    assert not hasattr(d, "G_SUCTION_HEAD")
    v1_head = V1_NH3_RHO * V1_G * 0.65 * V1_TANK_H / 1e5
    head = V1_NH3_RHO * G_ACC * 0.65 * V1_TANK_H / 1e5
    assert v1_head - head == pytest.approx(1.84e-5, rel=0.05)


# --------------------------------------------------------------------------------------
# The pump laws — V1's own functions, executed
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("rpm", [0.0, -5.0, 37.0, 80.0, 124.0, 131.0, 152.0, 170.0])
def test_pump_capacity_matches_v1(rpm, v1):
    from ureasim.units.feed import pump
    assert pump.flow_m3h(rpm) == v1["pump_flow_m3h"](rpm)


@pytest.mark.parametrize("rpm", [0.0, 80.0, 124.0, 152.0])
@pytest.mark.parametrize("dp_bar", [0.0, 50.0, 152.0, 163.0])
def test_pump_shaft_power_matches_v1(rpm, dp_bar, v1):
    from ureasim.units.feed import pump
    assert pump.shaft_power_kw(rpm, dp_bar) == v1["pump_shaft_power_kW"](rpm, dp_bar)


@pytest.mark.parametrize("rpm", [0.0, -1.0, 1.0, 37.0, 131.0, 152.0, 200.0])
@pytest.mark.parametrize("running", [True, False])
def test_motor_current_matches_v1(rpm, running, v1):
    from ureasim.units.feed import pump
    assert pump.current_a(rpm, running) == v1["pump_current_A"](rpm, running)


def test_a_stopped_machine_reads_the_instruments_live_zero_not_nothing(v1):
    """An ammeter reading exactly 0.000 is a dead instrument, not a stopped pump."""
    from ureasim.units.feed import pump
    assert pump.current_a(0.0, False) == v1["pump_current_A"](0.0, False) == 0.2


def test_the_datasheet_capacities_are_reproduced_at_the_superseded_efficiency():
    """The check that the GEOMETRY is right, at the efficiency the datasheet belongs to.

    67.1 and 82 m3/h are the datasheet's own capacities at 124 and 152 rpm. The swept volume
    reproduces them to 0.3 % at eta_v = 0.95. The field-calibrated 0.980 then deliberately
    departs from them — which is what `PUMP_ETA_V`'s provenance note is about, and why this
    test pins the geometry rather than the delivered flow.
    """
    assert 124.0 * d.PUMP_V_PER_REV * 0.95 * 60.0 == pytest.approx(66.91, abs=0.02)
    assert 152.0 * d.PUMP_V_PER_REV * 0.95 * 60.0 == pytest.approx(82.02, abs=0.02)


# --------------------------------------------------------------------------------------
# The ammonia saturation curve
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("t_c", [-33.3, -10.0, 0.0, 17.6, 25.0, 40.0, 60.0, 98.0])
def test_ammonia_saturation_pressure_matches_v1(t_c, v1):
    from ureasim.thermo.empirical import nh3_psat_bara
    assert nh3_psat_bara(t_c) == v1["psat_nh3_bara"](t_c)


def test_the_saturation_curve_lands_on_the_known_normal_boiling_point():
    """Ammonia boils at -33.3 C at one atmosphere. An Antoine set that misses that is the
    wrong Antoine set, and this one sits directly under a trip."""
    from ureasim.thermo.empirical import nh3_psat_bara
    assert nh3_psat_bara(-33.33) == pytest.approx(1.013, abs=0.03)
    assert nh3_psat_bara(25.0) == pytest.approx(10.0, abs=0.15)
    #  The correlation reads 1.031 bar at the normal boiling point, 1.8 % high. That is the
    #  Antoine set's own accuracy at the bottom of its range, and it is stated rather than
    #  tuned away: the drum runs at 25 C, where it is within 0.6 %, and V1 was proven on
    #  these coefficients.


# --------------------------------------------------------------------------------------
# V1's unit-321 block, transcribed
# --------------------------------------------------------------------------------------
#  Copied line for line from `backend/main.py` step_sim, the block that begins "Cascade
#  opening setpoint (%) from ratio flow demand" and ends at the ratio-PV validity gate.
#  Every correlation it calls is V1's own, executed. Only the assignments are transcribed.

#: SIC-321950 / SIC-321951 as V1's ``State`` seeds them, and as decided on the plant DCS's tuning
#: table (2026-10-08): the table's gain on SI-321950's 0-180 rpm read onto the per cent of the rated
#: 152 rpm the PV carries, its integral time, no derivative.
V1_SIC_TUNING = {"SIC_321950": (2.0, 8.0), "SIC_321951": (2.0, 8.0)}
DECIDED_SIC_TUNING = {"SIC_321950": (4.00 * 152.0 / 180.0, 35.0),
                      "SIC_321951": (1.20 * 152.0 / 180.0, 50.0)}


def _v1_state(v1, v1_controllers, table: bool = True, b85: bool = True):
    """V1's `State` attributes that the unit-321 block touches, seeded as V1 seeds them; `table`
    seeds V1's two SICs on the DCS's tuning (decided 2026-10-08), ``table=False`` is V1's; `b85`
    puts FFIC-321404A / B on the machines (decided 2026-10-09), ``b85=False`` is V1's open-loop
    demand."""
    open_des = V1_OPEN_DES_B
    tune = DECIDED_SIC_TUNING if table else V1_SIC_TUNING
    ffic_b = v1_controllers.Controller("FFIC_321404B", Kc=1.00, Ti=90.0,
                                       sp=V1_RATIO_DES / 4.0 * 100.0,
                                       mv=open_des / B85_OUT_TO_OPENING)
    ffic_b.set_mode("AUTO")
    ffic_b.set_sp(V1_RATIO_DES / 4.0 * 100.0)
    return SimpleNamespace(
        b85=b85,
        FFIC_A=v1_controllers.Controller("FFIC_321404A", Kc=1.00, Ti=100.0,
                                         sp=V1_RATIO_DES / 4.0 * 100.0, mv=0.0),
        FFIC_B=ffic_b,
        pumpA={"on": False, "open_act": 0.0, "speed_act": 0.0, "current": 0.2,
               "mode": "M", "fault": False},
        pumpB={"on": True, "open_act": open_des,
               "speed_act": open_des / 100.0 * V1_PUMP_RATED_RPM,
               "current": v1["pump_current_A"](open_des / 100.0 * V1_PUMP_RATED_RPM, True),
               "mode": "M", "fault": False},
        SIC_321950=v1_controllers.Controller("SIC_321950", Kc=tune["SIC_321950"][0],
                                             Ti=tune["SIC_321950"][1], sp=80.0, mv=0.0),
        SIC_321951=v1_controllers.Controller("SIC_321951", Kc=tune["SIC_321951"][0],
                                             Ti=tune["SIC_321951"][1],
                                             sp=open_des, mv=open_des),
        tank_level_frac=0.65,
        tank_T_C=25.0,
        tank_P_top_barG=12.3,
        F_in_BL_th=42.762,
        totalizer_t=0.0,
        ratio_SP=V1_RATIO_DES,
        ratio_PV=V1_RATIO_DES,
        ratio_bal=V1_RATIO_DES,
        XV_321901=True,
        XV_322901=True,
        flags={"RATIO_PV_BAD": False},
        tlag={},
        atm_decided=True,
    )


def _v1_feed_block(s, v1, co2_feed_th: float, dt: float) -> dict:
    """V1's unit-321 block, transcribed. See the note above this function. On the state's
    ``atm_decided``, the standard atmosphere and gravity (handoffs B-6, B-7)."""
    clamp = v1["clamp"]
    g_acc = DECIDED_G if s.atm_decided else V1_G
    p_atm = DECIDED_P_ATM_BAR if s.atm_decided else V1_P_ATM_BAR
    suct_open = bool(s.XV_321901) and (s.tank_level_frac > 0.05)
    disch_open = bool(s.XV_322901)
    s.F_CO2_th = co2_feed_th

    # Cascade opening setpoint (%) from ratio flow demand.
    F_NH3_sp_th = s.ratio_SP * V1_NC_TO_MASS * s.F_CO2_th
    Q_total_sp_m3h = F_NH3_sp_th * 1000.0 / V1_NH3_RHO
    n_active = (1 if s.pumpA["on"] else 0) + (1 if s.pumpB["on"] else 0)
    Q_per_pump = Q_total_sp_m3h / max(n_active, 1)
    rpm_req = Q_per_pump / (V1_PUMP_V_PER_REV * V1_PUMP_ETA_V * 60.0)
    open_cas = clamp(rpm_req / V1_PUMP_RATED_RPM * 100.0, 0.0, 100.0)

    # B-85 (decided 2026-10-09): FFIC-321404A / B, PI on FY-321404 per cent of its 0-4 range, the
    # output per cent of the SIC's 180 rpm maximum, the balance on the SIC's working set point
    # while it is not in CAS (UD-MR-321-FF-0002 pages 2-3), held below the 5 % gate. Off == V1.
    cas = {"A": open_cas, "B": open_cas}
    if s.b85:
        valid = s.F_CO2_th >= 0.05 * (V1_CO2_DES_KGH / 1000.0)
        for key, ffic, ctrl in (("A", s.FFIC_A, s.SIC_321950), ("B", s.FFIC_B, s.SIC_321951)):
            if ctrl.mode != "CAS":
                if ffic.mode != "MAN":
                    ffic.set_mode("MAN")
                pump = s.pumpA if key == "A" else s.pumpB
                ffic.set_op((ctrl.sp if ctrl.mode == "AUTO" else pump["open_act"])
                            / B85_OUT_TO_OPENING)
            else:
                if ffic.mode != "AUTO":
                    ffic.set_mode("AUTO")
                ffic.set_sp(s.ratio_SP / 4.0 * 100.0)
                if valid:
                    ffic.step(s.ratio_PV / 4.0 * 100.0, dt)
            cas[key] = ffic.mv * B85_OUT_TO_OPENING

    # Drive each pump's converter opening toward controller output
    for key, p, ctrl in [("A", s.pumpA, s.SIC_321950), ("B", s.pumpB, s.SIC_321951)]:
        if (not p["on"]) and ctrl.mode != "MAN":
            ctrl.set_mode("MAN")
            ctrl.set_op(0.0)
        ctrl.step(p["open_act"], dt, cas_sp=cas[key])
        if (not p["on"]) or (not suct_open) or (not disch_open):
            target = 0.0
        else:
            target = ctrl.mv
        alpha = min(1.0, dt / 2.0)
        p["open_act"] += (target - p["open_act"]) * alpha
        p["open_act"] = clamp(p["open_act"], 0.0, 100.0)
        p["speed_act"] = p["open_act"] / 100.0 * V1_PUMP_RATED_RPM
        p["current"] = v1["pump_current_A"](p["speed_act"], p["on"])
        p["mode"] = v1["mode_tag"](ctrl)

    # Pump flows
    Q_A_m3h = v1["pump_flow_m3h"](s.pumpA["speed_act"]) if s.pumpA["on"] else 0.0
    Q_B_m3h = v1["pump_flow_m3h"](s.pumpB["speed_act"]) if s.pumpB["on"] else 0.0
    F_A_th = Q_A_m3h * V1_NH3_RHO / 1000.0
    F_B_th = Q_B_m3h * V1_NH3_RHO / 1000.0
    F_pump_total_th = F_A_th + F_B_th

    # LIC-321501 feed-drum makeup
    s.F_in_BL_th = clamp(
        F_pump_total_th + V1_TANK_LIC_KP_TH * (V1_TANK_LEVEL_SP_FRAC - s.tank_level_frac),
        0.0, V1_TANK_BL_MAX_TH)
    dm_kg = (s.F_in_BL_th - F_pump_total_th) * 1000.0 / 3600.0 * dt
    V_new = clamp(s.tank_level_frac * V1_TANK_VOL + dm_kg / V1_NH3_RHO, 0.0, V1_TANK_VOL)
    s.tank_level_frac = V_new / V1_TANK_VOL
    s.totalizer_t += F_pump_total_th * dt / 3600.0

    # 321D003 energy balance
    M_tank_kg = s.tank_level_frac * V1_TANK_VOL * V1_NH3_RHO
    F_in_kgs = s.F_in_BL_th * 1000.0 / 3600.0
    if M_tank_kg > 1.0:
        s.tank_T_C += (F_in_kgs * (V1_T_BL_FEED_C - s.tank_T_C) / M_tank_kg) * dt

    # PT / PY / PDY
    P_suct_barG = (s.tank_P_top_barG
                   + (V1_NH3_RHO * g_acc * s.tank_level_frac * V1_TANK_H) / 1e5
                   - 0.15)
    if not suct_open:
        P_suct_barG = 0.0
    PT_A = PT_B = s.tank_P_top_barG
    PY = v1["psat_nh3_bara"](s.tank_T_C)
    PDY_A = (PT_A + p_atm) - PY
    PDY_B = (PT_B + p_atm) - PY

    # TI-321020
    if (s.pumpA["on"] or s.pumpB["on"]) and disch_open:
        dP_pa = max(0.0, V1_P_SYN_DOWN_BAR - (P_suct_barG + p_atm)) * 1e5
        T_K = s.tank_T_C + 273.15
        dT_pump = dP_pa / (V1_NH3_RHO * V1_CP_NH3) * (
            V1_BETA_NH3 * T_K + (1.0 - V1_ETA_PUMP_HYD) / V1_ETA_PUMP_HYD)
    else:
        dT_pump = 0.0
    TI_321020 = s.tank_T_C + dT_pump

    # Motive stream and its BL transit
    motive_nh3_kgh = (F_pump_total_th * 1000.0) if disch_open else 0.0
    motive_nh3_kgh = v1["_delay"](s.tlag, "FEED_NH3", motive_nh3_kgh,
                                  v1["_feed_transport_td_s"](V1_FEED_NH3_LINE_KG,
                                                             motive_nh3_kgh), dt)
    phi_m = clamp(motive_nh3_kgh / V1_EJ_MOTIVE_NH3_DES, 0.0, 1.5)
    phi_fwd = phi_m * phi_m

    # Ratio block PV, with the L3-3 validity gate
    NC_A = NC_B = 0.5 * s.ratio_PV
    if s.F_CO2_th < 0.05 * (V1_CO2_DES_KGH / 1000.0):
        s.flags["RATIO_PV_BAD"] = True
    else:
        s.flags["RATIO_PV_BAD"] = False
        m_CO2 = max(s.F_CO2_th, 1e-6)
        NC_A = (F_A_th / m_CO2) * V1_NC_FACTOR
        NC_B = (F_B_th / m_CO2) * V1_NC_FACTOR
        s.ratio_PV = NC_A + NC_B
        s.ratio_bal = s.ratio_PV

    return {"F_A_th": F_A_th, "F_B_th": F_B_th, "F_pump_total_th": F_pump_total_th,
            "motive": motive_nh3_kgh, "phi_m": phi_m, "phi_fwd": phi_fwd,
            "TI_321020": TI_321020, "P_suct_barG": P_suct_barG,
            "PT_A": PT_A, "PY": PY, "PDY_A": PDY_A, "PDY_B": PDY_B,
            "ratio_PV": s.ratio_PV, "NC_A": NC_A, "NC_B": NC_B,
            "ratio_bad": s.flags["RATIO_PV_BAD"],
            "F_in_BL_th": s.F_in_BL_th, "open_cas": open_cas,
            "cas_A": cas["A"], "cas_B": cas["B"]}


def _v11_station() -> FeedStation:
    """The same station built out of the rewrite's blocks, seeded identically."""
    from ureasim.control.controller import Controller
    open_des = d.PUMP_OPEN_DES_PCT
    from ureasim.units.feed.pump import current_a
    return FeedStation(
        pump_a=ReciprocatingPump("321P002A", running=False, opening_pct=0.0,
                                 speed_rpm=0.0, current=d.PUMP_IDLE_I),
        pump_b=ReciprocatingPump("321P002B", running=True, opening_pct=open_des,
                                 speed_rpm=open_des / 100.0 * d.PUMP_RATED_RPM,
                                 current=current_a(open_des / 100.0 * d.PUMP_RATED_RPM,
                                                   True)),
        sic_a=Controller("SIC_321950", Kc=d.SIC_321950_KC, Ti=d.SIC_321950_TI_S,
                         Td=d.SIC_TD_S, sp=80.0, mv=0.0),
        sic_b=Controller("SIC_321951", Kc=d.SIC_321951_KC, Ti=d.SIC_321951_TI_S,
                         Td=d.SIC_TD_S, sp=open_des, mv=open_des),
        drum=FeedDrum(level_frac=0.65, temperature_c=25.0, top_pressure_barg=12.3,
                      makeup_th=42.762, totalizer_t=0.0),
        ratio_sp=V1_RATIO_DES, ratio_pv=V1_RATIO_DES,
    )


def _compare(v1, v1_controllers, script, ticks: int):
    """Drive both stations through `script(k) -> co2_feed_th` and compare every field.

    Every field is compared for EXACT equality. There is no tolerance in this function,
    because there is no approximation in the port: the correlations are V1's own, executed,
    and the constants are V1's own numbers, the atmosphere and gravity on the decided switch
    (handoffs B-6, B-7).
    """
    s = _v1_state(v1, v1_controllers)
    station = _v11_station()
    for k in range(ticks):
        co2 = script(k)
        a = _v1_feed_block(s, v1, co2, DT)
        b = station.step(co2, DT)

        assert a["cas_A"] == b.cascade_opening_a_pct, f"tick {k}"
        assert a["cas_B"] == b.cascade_opening_b_pct, f"tick {k}"
        assert a["F_A_th"] == b.flow_a_th, f"tick {k}"
        assert a["F_B_th"] == b.flow_b_th, f"tick {k}"
        assert a["F_pump_total_th"] == b.flow_total_th, f"tick {k}"
        assert a["motive"] == b.motive_nh3_kgh, f"tick {k}"
        assert a["phi_m"] == b.phi_motive, f"tick {k}"
        assert a["phi_fwd"] == b.phi_forward, f"tick {k}"
        assert a["F_in_BL_th"] == b.makeup_th, f"tick {k}"
        assert a["PT_A"] == b.feed_pressure_barg, f"tick {k}"
        assert a["PY"] == b.vapour_pressure_bara, f"tick {k}"
        assert a["PDY_A"] == b.subcooling_a_bar, f"tick {k}"
        assert a["PDY_B"] == b.subcooling_b_bar, f"tick {k}"
        assert a["ratio_PV"] == b.ratio_pv, f"tick {k}"
        assert a["NC_A"] == b.ratio_nc_a, f"tick {k}"
        assert a["NC_B"] == b.ratio_nc_b, f"tick {k}"
        assert a["ratio_bad"] == b.ratio_pv_bad, f"tick {k}"
        assert s.tank_level_frac == station.drum.level_frac, f"tick {k}"
        assert s.totalizer_t == station.drum.totalizer_t, f"tick {k}"
        assert s.pumpA["open_act"] == station.pump_a.opening_pct, f"tick {k}"
        assert s.pumpB["open_act"] == station.pump_b.opening_pct, f"tick {k}"
        assert s.pumpB["current"] == station.pump_b.current, f"tick {k}"
        assert s.pumpB["mode"] == station.pump_b.mode_letter, f"tick {k}"

        assert a["P_suct_barG"] == b.suction_barg, f"tick {k}"
        assert a["TI_321020"] == b.discharge_t_c, f"tick {k}"
        assert s.tank_T_C == station.drum.temperature_c, f"tick {k}"
    return s, station


# --------------------------------------------------------------------------------------
# Whole-section equivalence
# --------------------------------------------------------------------------------------

def test_the_section_holds_its_design_point_and_matches_v1(v1, v1_controllers):
    s, station = _compare(v1, v1_controllers, lambda k: CO2_DES_TH, ticks=600)
    assert station.pump_b.opening_pct == pytest.approx(d.PUMP_OPEN_DES_PCT, rel=1e-12)


def test_the_design_fixed_point_is_exact():
    """The boot pin for this section, asserted on the rewrite alone.

    Pump B at its derived design opening delivers exactly the design motive flow, so the
    ratio cascade asks for the opening it already has, the drum's import equals its draw and
    the level does not move at all, and `phi_motive` is a literal 1.0.
    """
    station = _v11_station()
    level_before = station.drum.level_frac
    result = station.step(CO2_DES_TH, DT)

    assert result.flow_total_th * 1000.0 == pytest.approx(d.EJ_MOTIVE_NH3_DES, rel=1e-12)
    assert result.phi_motive == pytest.approx(1.0, rel=1e-12)
    assert result.phi_forward == pytest.approx(1.0, rel=1e-12)
    assert result.makeup_th == pytest.approx(result.flow_total_th, rel=1e-12)
    assert station.drum.level_frac == level_before
    assert result.ratio_pv == pytest.approx(V1_RATIO_DES, rel=1e-9)
    assert result.ratio_pv_bad is False
    # And the ratio controller asks for the opening the machine is already at.
    assert result.cascade_opening_b_pct == pytest.approx(d.PUMP_OPEN_DES_PCT, rel=1e-12)


def test_a_moving_plant_rate_tracks_v1(v1, v1_controllers):
    """The CO2 feed swings +/-25 % and the ratio cascade follows it."""
    def script(k):
        return CO2_DES_TH * (1.0 + 0.25 * math.sin(k * 0.01))
    _compare(v1, v1_controllers, script, ticks=900)


def test_the_cascade_moves_the_pump_when_the_operator_moves_the_ratio(v1, v1_controllers):
    """An N/C set-point change is the operator action this whole section exists for. On
    FFIC-321404B (1.00 and 90 s on FY-321404's 0-4, decided 2026-10-09, B-85) over SIC-321951 (1.20
    and 50 s) the ratio comes inside 0.02 of the operator's 2.20 at 398.7 s, without overshoot
    (2.1808 at most), and 400 s after the 1.90 is asked for it is at 1.9330. Before B-85 V1's
    open-loop demand settled the 1.90 at 294 s and never reached the 2.20 in 50 s (2.093)."""
    s = _v1_state(v1, v1_controllers)
    station = _v11_station()
    s.SIC_321951.set_mode("CAS")
    station.sic_b.set_mode("CAS")
    peak, t_in = 0.0, None
    for k in range(8200):
        if k == 200:
            s.ratio_SP = 2.20
            station.ratio_sp = 2.20
        if k == 4200:
            s.ratio_SP = 1.90
            station.ratio_sp = 1.90
        a = _v1_feed_block(s, v1, CO2_DES_TH, DT)
        b = station.step(CO2_DES_TH, DT)
        assert a["F_pump_total_th"] == b.flow_total_th, f"tick {k}"
        assert a["ratio_PV"] == b.ratio_pv, f"tick {k}"
        assert s.pumpB["open_act"] == station.pump_b.opening_pct, f"tick {k}"
        peak = max(peak, b.ratio_pv)
        if t_in is None and 200 < k < 4200 and abs(b.ratio_pv - 2.20) < 0.02:
            t_in = (k - 200) * DT
    # The loop moves where it was asked to go, on the ratio controller's integral.
    assert t_in == pytest.approx(398.7, abs=0.05)
    assert peak == pytest.approx(2.1808, abs=1e-4)
    assert station.ratio_pv == pytest.approx(1.9330, abs=1e-4)


def test_starting_the_standby_pump_tracks_v1(v1, v1_controllers):
    """Starting 321P002A as the plant does it with a ratio controller on each machine (B-85,
    decided 2026-10-09): the machine run up on its SIC in AUTO to 40 %, then put on cascade. While
    it comes up FFIC-321404B takes 321P002B down against the rising N/C, which peaks at 2.584; once
    SIC-321950 is on cascade both ratio controllers integrate the same error, and the N/C is back
    inside 0.02 of the design 349.2 s later, the duty split 37.23 / 46.35 % where the two machines
    were when the error closed. Before B-85 V1's demand halved each machine's opening at once and
    the DCS tunings overshot the N/C to 2.310."""
    s = _v1_state(v1, v1_controllers)
    station = _v11_station()
    s.SIC_321951.set_mode("CAS")
    station.sic_b.set_mode("CAS")
    peak, t_in = 0.0, None
    for k in range(9000):
        if k == 300:
            s.pumpA["on"] = True
            station.pump_a.running = True
            for ctrl in (s.SIC_321950, station.sic_a):
                ctrl.set_mode("AUTO")
                ctrl.set_sp(40.0)
        if k == 1500:
            s.SIC_321950.set_mode("CAS")
            station.sic_a.set_mode("CAS")
        a = _v1_feed_block(s, v1, CO2_DES_TH, DT)
        b = station.step(CO2_DES_TH, DT)
        assert a["F_A_th"] == b.flow_a_th, f"tick {k}"
        assert a["F_B_th"] == b.flow_b_th, f"tick {k}"
        assert a["cas_A"] == b.cascade_opening_a_pct, f"tick {k}"
        assert a["cas_B"] == b.cascade_opening_b_pct, f"tick {k}"
        peak = max(peak, b.ratio_pv)
        if t_in is None and k > 1500 and abs(b.ratio_pv - V1_RATIO_DES) < 0.02:
            t_in = (k - 1500) * DT
    assert station.pump_a.running and station.pump_b.running
    assert peak == pytest.approx(2.5839, abs=1e-4)
    assert t_in == pytest.approx(349.2, abs=0.05)
    assert station.pump_a.opening_pct == pytest.approx(37.23, abs=0.01)
    assert station.pump_b.opening_pct == pytest.approx(46.35, abs=0.01)


def test_the_ratio_controllers_decided_divergence(v1, v1_controllers):
    """FFIC-321404A / B as Uhde draws them (B-85, decided 2026-10-09), both ways on V1's executed
    controller code: the CO2 feed stepped down 10 % with 321P002B on cascade. V1's open-loop demand
    moves the machine's set point with the CO2 at once; the ratio controller corrects the N/C it
    measures over its integral. Both jump 0.2248 with the CO2 (the ammonia lags it by the scoop and
    the SIC), and the N/C is back within 0.005 of the design at 375.3 s on V1's demand, 539.8 s on
    the ratio controller."""
    back = {}
    for b85 in (False, True):
        s = _v1_state(v1, v1_controllers, b85=b85)
        s.SIC_321951.set_mode("CAS")
        dev, t_back = 0.0, None
        for k in range(9000):
            co2 = CO2_DES_TH * (0.9 if k >= 100 else 1.0)
            err = abs(_v1_feed_block(s, v1, co2, DT)["ratio_PV"] - V1_RATIO_DES)
            dev = max(dev, err)
            if k > 100 and t_back is None and dev > 0.02 and err < 0.005:
                t_back = (k - 100) * DT
        assert dev == pytest.approx(0.2248, abs=1e-4)
        back[b85] = t_back
    assert back[False] == pytest.approx(375.3, abs=0.05)
    assert back[True] == pytest.approx(539.8, abs=0.05)


def test_shutting_the_isolation_valves_tracks_v1(v1, v1_controllers):
    """XV-321901 and XV-322901 drive the scoop closed, not the flow to zero."""
    s = _v1_state(v1, v1_controllers)
    station = _v11_station()
    for k in range(900):
        if k == 200:
            s.XV_322901 = False
            station.xv_322901_open = False
        if k == 500:
            s.XV_322901 = True
            station.xv_322901_open = True
        if k == 700:
            s.XV_321901 = False
            station.xv_321901_open = False
        a = _v1_feed_block(s, v1, CO2_DES_TH, DT)
        b = station.step(CO2_DES_TH, DT)
        assert a["F_pump_total_th"] == b.flow_total_th, f"tick {k}"
        assert a["motive"] == b.motive_nh3_kgh, f"tick {k}"
        assert a["P_suct_barG"] == b.suction_barg, f"tick {k}"


def test_stopping_both_pumps_tracks_v1_and_drains_nothing(v1, v1_controllers):
    """A stopped machine forces its SIC to MAN; the drum then fills to its own set point."""
    s = _v1_state(v1, v1_controllers)
    station = _v11_station()
    s.SIC_321951.set_mode("CAS")
    station.sic_b.set_mode("CAS")
    for k in range(600):
        if k == 100:
            s.pumpB["on"] = False
            station.pump_b.running = False
        a = _v1_feed_block(s, v1, CO2_DES_TH, DT)
        b = station.step(CO2_DES_TH, DT)
        assert a["F_pump_total_th"] == b.flow_total_th, f"tick {k}"
        assert s.pumpB["open_act"] == station.pump_b.opening_pct, f"tick {k}"
    assert station.sic_b.mode == "MAN" == s.SIC_321951.mode
    #  With no draw and the level already at set point, LIC-321501 imports NOTHING: the
    #  feed-forward term is zero and the proportional term is zero. The drum simply sits
    #  where it is, which is the correct answer and not a stalled integrator.
    assert station.drum.level_frac == 0.65
    assert station.drum.makeup_th == 0.0


def test_a_variable_substep_changes_nothing_about_the_agreement(v1, v1_controllers):
    """The engine integrates on variable sub-steps down to crumbs of about 1e-8 s."""
    s = _v1_state(v1, v1_controllers)
    station = _v11_station()
    steps = [0.1, 0.05, 0.25, 1e-8, 0.2, 0.1, 1e-8, 0.15]
    for k in range(400):
        dt = steps[k % len(steps)]
        a = _v1_feed_block(s, v1, CO2_DES_TH, dt)
        b = station.step(CO2_DES_TH, dt)
        assert a["F_pump_total_th"] == b.flow_total_th, f"tick {k}"
        assert a["motive"] == b.motive_nh3_kgh, f"tick {k}"
        assert s.tank_level_frac == station.drum.level_frac, f"tick {k}"


# --------------------------------------------------------------------------------------
# The ratio validity gate
# --------------------------------------------------------------------------------------

def test_the_ratio_holds_its_last_good_value_below_five_per_cent_load(v1, v1_controllers):
    """A molar N/C against a collapsing CO2 feed is a number that means nothing.

    Holding it and raising the bad flag is what freezes the cascade instead of propagating
    garbage into a set point — the behaviour on a black start and on a CO2-feed loss.
    """
    s, station = _compare(v1, v1_controllers, lambda k: CO2_DES_TH, ticks=50)
    good = station.ratio_pv

    for k in range(50):
        a = _v1_feed_block(s, v1, 0.01, DT)
        b = station.step(0.01, DT)
        assert a["ratio_bad"] is b.ratio_pv_bad is True, f"tick {k}"
        assert a["ratio_PV"] == b.ratio_pv, f"tick {k}"
        assert a["NC_A"] == b.ratio_nc_a and a["NC_B"] == b.ratio_nc_b, f"tick {k}"
    assert station.ratio_pv == good           # held, not recomputed
    assert b.ratio_nc_a == b.ratio_nc_b == 0.5 * good


def test_the_gate_reopens_when_the_feed_comes_back(v1, v1_controllers):
    s = _v1_state(v1, v1_controllers)
    station = _v11_station()
    for k in range(200):
        co2 = 0.01 if k < 100 else CO2_DES_TH
        a = _v1_feed_block(s, v1, co2, DT)
        b = station.step(co2, DT)
        assert a["ratio_bad"] is b.ratio_pv_bad, f"tick {k}"
        assert a["ratio_PV"] == b.ratio_pv, f"tick {k}"
    assert station.ratio_pv == pytest.approx(V1_RATIO_DES, abs=0.05)


def test_the_gate_threshold_is_five_per_cent_of_the_design_feed():
    """One number decides whether the cascade is frozen; it is worth asserting directly."""
    station = _v11_station()
    just_above = station.step(0.0501 * CO2_DES_TH, DT)
    assert just_above.ratio_pv_bad is False
    just_below = station.step(0.0499 * CO2_DES_TH, DT)
    assert just_below.ratio_pv_bad is True


# --------------------------------------------------------------------------------------
# The cascade law and the drum, on their own
# --------------------------------------------------------------------------------------

def test_the_design_ratio_inverts_the_delivery_law_exactly():
    """At design the ratio the machine delivers is the set point: `NC_FACTOR . NC_TO_MASS == 1`,
    so FFIC-321404B's error is zero and its increment is zero."""
    assert d.NC_FACTOR * d.NC_TO_MASS == pytest.approx(1.0, rel=1e-15)


def test_the_makeup_equals_the_draw_at_the_level_setpoint():
    """Feed-forward, stated as the property it exists for: zero offset at set point."""
    from ureasim.units.feed.feed_drum import makeup_flow_th
    assert makeup_flow_th(42.762, d.TANK_LEVEL_SP_FRAC) == 42.762


def test_the_makeup_is_bounded_by_the_import_line_capacity():
    from ureasim.units.feed.feed_drum import makeup_flow_th
    assert makeup_flow_th(42.762, 0.0) == d.TANK_BL_MAX_TH
    assert makeup_flow_th(0.0, 1.0) == 0.0


def test_the_drum_holds_about_a_minute_of_inventory():
    """Why LIC-321501 feeds the draw forward instead of chasing a level."""
    drum = FeedDrum()
    minutes = drum.inventory_kg / (42762.05 / 60.0)
    assert 0.5 < minutes < 1.5


def test_losing_the_level_loses_the_suction():
    drum = FeedDrum(level_frac=0.04)
    assert drum.suction_available(True) is False
    assert FeedDrum(level_frac=0.06).suction_available(True) is True
    assert FeedDrum(level_frac=0.65).suction_available(False) is False


def test_the_subcooling_margin_falls_as_the_drum_warms():
    """Two upsets destroy the margin and one equation catches both. This is the warm one."""
    cold = FeedDrum(temperature_c=25.0).subcooling_margin_bar()
    warm = FeedDrum(temperature_c=40.0).subcooling_margin_bar()
    assert cold > warm
    assert warm < 1.0                 # already inside the band the 21.2 trip watches
    assert cold > 3.0


# --------------------------------------------------------------------------------------
# The decided divergence: one atmosphere and one gravity (handoffs B-6, B-7), both sides
# --------------------------------------------------------------------------------------

def test_the_standard_atmosphere_and_gravity_decided_divergence(v1, v1_controllers):
    """V1 verbatim against the port at the design point. The flows, the pumps, the drum and the
    ratio are V1's to the bit: neither constant reaches them. The suction reads 1.84e-5 bar less
    head on standard gravity; PDY-321203/204's subcooling and the 321P002 differential behind
    TI-321020 move by the 0.25 mbar between the two atmospheres."""
    s = _v1_state(v1, v1_controllers)
    s.atm_decided = False
    station = _v11_station()
    a = _v1_feed_block(s, v1, CO2_DES_TH, DT)
    b = station.step(CO2_DES_TH, DT)
    assert (a["F_pump_total_th"], a["motive"], a["F_in_BL_th"], a["ratio_PV"]) == (
        b.flow_total_th, b.motive_nh3_kgh, b.makeup_th, b.ratio_pv)
    assert s.tank_level_frac == station.drum.level_frac
    assert a["P_suct_barG"] - b.suction_barg == pytest.approx(1.84e-5, rel=0.05)
    assert b.subcooling_a_bar - a["PDY_A"] == pytest.approx(DECIDED_P_ATM_BAR - V1_P_ATM_BAR,
                                                            rel=1e-6)
    assert a["TI_321020"] != b.discharge_t_c
    assert abs(a["TI_321020"] - b.discharge_t_c) < 1e-3


def test_the_speed_controllers_on_the_dcs_tuning_decided_divergence(v1, v1_controllers):
    """SIC-321950 and SIC-321951 on the plant DCS's table (decided 2026-10-08), both ways: the
    standby start of 321P002A with both SICs in CAS. V1's 2.0 and 8 s hand the duty over without
    moving the N/C; the table's 4.00 / 35 s and 1.20 / 50 s, on SI-321950's 0-180 rpm, overshoot
    it to 2.310. V1's controller code executes both."""
    assert (d.SIC_321950_KC, d.SIC_321950_TI_S) == DECIDED_SIC_TUNING["SIC_321950"]
    assert (d.SIC_321951_KC, d.SIC_321951_TI_S) == DECIDED_SIC_TUNING["SIC_321951"]
    peaks = {}
    for table in (False, True):
        s = _v1_state(v1, v1_controllers, table=table, b85=False)
        peak = 0.0
        for k in range(1200):
            if k == 300:
                s.pumpA["on"] = True
                s.SIC_321950.set_mode("CAS")
                s.SIC_321951.set_mode("CAS")
            peak = max(peak, _v1_feed_block(s, v1, CO2_DES_TH, DT)["ratio_PV"])
        peaks[table] = peak
    assert peaks[False] == pytest.approx(V1_RATIO_DES, abs=1e-4)
    assert peaks[True] == pytest.approx(2.310, abs=1e-3)
