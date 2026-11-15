"""V1 <-> V1.1 equivalence for 328D003, the ammonia water tank.

What is being proved
--------------------
V1 writes the tank inline in `step_sim`, so its statements are TRANSCRIBED into `_v1_stage2`
below, line for line, and declared as such (``main.py`` 8832-8833 and 8883-8950). Everything they
call is V1's own code, executed: ``redistribute_communicating_compartments``,
``d003_level_telemetry``, ``aqueous_cp``, ``_fic_flow``, ``_ctrl_ipd`` and ``_lag1`` lifted out of
``main.py``. The state and the loops are seeded as ``State.__init__`` seeds them (6879-6884,
6947-6980, 7107-7127). The decided divergence (decision 11 extended, 2026-09-27) — the heel and
the overflow — is a switch in the transcription: ``decided=True`` carries the port's lines in
place of V1's, and ``decided=False`` is V1 verbatim. Every scenario that keeps the tank between
its heel and full runs verbatim; the two limits are each run both ways — bit-exact to the tick
the limit is reached, then V1's behaviour asserted on V1's side and the port's on the port's —
and the port is compared with the switched transcription on every tick through the limit. The
switch also carries FIC-328402's decided gain and transmitter (B-38), proved both ways in
`test_ammonia_water_tank_fic328402_equivalence.py`, and the other four loops' decided gains
(B-41), seeded into V1's controller dicts — V1's `_ctrl_ipd` runs unchanged — and proved both
ways in `test_flow_loop_gains_equivalence.py`. A loop on its set point has no error, so its gain
is inert: every scenario that moves no set point runs V1 verbatim.

The four valves (handoff B-44, decided 2026-09-30). The port runs them on their vendor trim,
Valtek's modified equal percentage, from the strokes their Kvs give (FV-323401, FV-323402,
FV-328402) or anchored on its full-stroke capacity (FV-328405). The transcription carries the
switch ``valves_decided`` (default True): the loops seeded on the decided strokes and V1's
``_fic_flow`` transcribed with the trim (`decided_valves.fic_flow`); ``valves_decided=False`` is
V1 verbatim. A valve at its design stroke passes its design flow either way, so the two part only
when a stroke moves; the last section runs them side by side.

FIC-328402 (handoff B-39, decided 2026-10-09). The port puts the loop on 735, as the plant meters
it, and 744 is what 322P002 delivers; V1 hangs the loop on 744 and draws 735 in proportion to
compartment II's holdup. The transcription carries the switch ``b39`` (default True): FIC-328402 on
735 at 735's density, its seed, set point limit and V1's own 0.06 per kg/h carried there, and 744
the PFD's while 322P002 runs; ``b39=False`` is V1's structure verbatim. The two are run both ways in
`test_ammonia_water_tank_fic328402_equivalence.py`.

322P002's field-set delivery (handoff B-133, decided 2026-11-15, decision 212). The plant sets
744 by hand in the field, read on FI-322402; V1 has no handle and delivers the PFD's 744 whenever
322P002 runs. The port delivers the instructor's field-set flow, seeded at the PFD's 744, so every
scenario above runs at the seed and is V1's; the last test sets it below design and asserts both
sides.

741 (handoff B-50, decided 2026-09-30). The recycle is a draw on 328C004's bottoms, so the port
steps FIC-328406 with 328C004 and the tank takes 741 as a boundary, a tick late. V1 steps
FIC-328406 here, on its own, and clamps 741 at last tick's 739: the transcription keeps V1's lines
and hands the port the 741 they give, so the tank is proved on whatever 741 arrives. The loop
itself is proved in 328C004's files.

Last, the tank is coupled to 323C005 and 323E011 in V1's order: 343 and 791 same-tick, 702 a tear.
"""

from __future__ import annotations

import math

import pytest

from ureasim.core.flowsheet import Connection, CyclicFlowsheetError, Flowsheet, Tear, Unit
from ureasim.data import control_valves as cvd
from ureasim.data import unit_323c005 as c
from ureasim.data import unit_328d003 as d
from ureasim.units.desorption import ammonia_water_tank as awt
from ureasim.units.desorption import atmospheric_absorber as aa
from ureasim.units.recirc import flash_condenser as fc
from tests.equivalence import routes_switch
from tests.equivalence import test_atmospheric_absorber_equivalence as stage1
from tests.equivalence import test_flash_condenser_equivalence as stage9
from tests.equivalence import decided_valves as dv
from tests.equivalence import test_pre_evaporator_equivalence as stage3
from tests.equivalence.v1_loader import lift, load, v1_available, v1_service

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

D003_NAMES = [
    "A328_CP", "A328_D003_M719", "A328_D003_M719_T", "A328_D003_M720", "A328_D003_M720_T",
    "A328_D003_M721", "A328_D003_M721_T", "A328_D003_M759", "A328_D003_M759_T",
    "A328_D003_VOL_I_M3", "A328_D003_VOL_II_M3", "A328_D003_VOL_III_M3",
    "A328_D003_VOL_TOTAL_M3", "A328_D003_RHO_KGM3", "A328_D003_MI_FULL", "A328_D003_MII_FULL",
    "A328_D003_MIII_FULL", "A328_D003_MI_DES", "A328_D003_MII_DES", "A328_D003_MIII_DES",
    "A328_D003_COMP_I_ROUNDING_KGH", "A328_D003_COMP_II_ROUNDING_KGH", "S793_CAP_KGH",
    "S793_M_DES", "S741_CAP_KGH", "RHO_741_KGM3", "A328_M741_T", "A328_D003_TI",
    "A328_D003_TII", "A328_D003_TIII", "A328_D003_V001_T", "A328_D003_LAM_I",
    "R328_C002_M738_DES", "R3232_E011_M401_DES", "RHO_401_KGM3", "RHO_791_KGM3",
    "R3232_FIC405_OP_DES", "R3232_E003_PHI744", "R3232_E003_M744_DES", "S744_VOL_DES",
    "RHO_744_KGM3", "A328_M756_DES", "R328_C004_M739_DES",
    "redistribute_communicating_compartments", "d003_level_telemetry", "aqueous_cp",
    "_fic_flow", "_ctrl_ipd", "_lag1",
]

DT = 0.1

#: The loops whose gains the port reads per cent of span: FIC-328402 (B-38) and the rest (B-41).
DECIDED_GAINS = ("FIC_323401", "FIC_323402", "FIC_328405", "FIC_328402")

#: The decided valves (B-44): the design strokes the three Kvs give [%], and the full-stroke
#: capacity of the valve shut at design [kg/h], re-derived from the vendor catalogue.
DECIDED_OP = {"FIC_323401": dv.design_stroke_pct(cvd.FV_323401, d.M401_DES_KGH),
              "FIC_323402": dv.design_stroke_pct(cvd.FV_323402, d.M402_DES_KGH),
              "FIC_328402": dv.design_stroke_pct(cvd.FV_328402, d.M735_DES_KGH)}

#: FV-328402's design stroke on V1's structure, the loop on 744 (``b39=False``) [%].
STROKE_744 = dv.design_stroke_pct(cvd.FV_328402, d.M744_DES_KGH)


def _full_kgh(valve, rho):
    c_n = valve.cases[valve.normal]
    return c_n.flow * valve.rated / c_n.capacity * rho


DECIDED_CAP_793 = _full_kgh(cvd.FV_328405, d.RHO_401_KGM3)


@pytest.fixture(scope="module")
def v1():
    ns = stage3.build_v1(stage9.V1_NAMES)
    # The isometrics' geometry (handoff A-11, decided 2026-10-07): `routes_switch`.
    ns["D002_ROUTE"] = routes_switch.decided(ns, "323F010_TO_323D002")
    ns["coupling"] = load("c003_pressure_coupling")
    ns["vacuum_condenser"] = load("vacuum_condenser")
    seed = {"math": math, "vacuum_condenser": ns["vacuum_condenser"],
            "iapws_if97": load("iapws_if97"), "steam_system": load("steam_system"),
            "thermo_service": v1_service(), "hydraulics": load("hydraulics")}
    ns.update(lift(stage1.C005_NAMES, seed=seed))
    ns.update(lift(D003_NAMES, seed=seed))
    return ns


def _v1_state(v1, decided=False, valves_decided=True, b39=True):
    """The V1 plant-state fields 323C005, 328D003 and 323E011 read and write, seeded as
    `State.__init__` seeds them: the tank from ``main.py`` 6879-6884, the five loops from
    6951-6980 and 7113-7127, 322P002 from 7144; `decided` gives the four the port keeps the port's
    gains, each the table's read per cent of its transmitter's span (B-38, B-41);
    `valves_decided` seeds the three open loops on their vendor valves' strokes (B-44); `b39` puts
    FIC-328402 on 735 (B-39)."""
    g = v1
    s = stage1._v1_state(v1)
    s.a328_d003_MI, s.a328_d003_MII, s.a328_d003_MIII = (
        g["A328_D003_MI_DES"], g["A328_D003_MII_DES"], g["A328_D003_MIII_DES"])
    s.a328_d003_TI, s.a328_d003_TII, s.a328_d003_TIII = (
        g["A328_D003_TI"], g["A328_D003_TII"], g["A328_D003_TIII"])

    def fic(op, v, kc, ti, sp_hi, mode="AUTO"):
        return {"mode": mode, "op": op, "sp": v, "pv": v, "pv1": v, "pv2": v, "Kc": kc,
                "Ti": ti, "Td": 0.0, "act": +1.0, "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0,
                "sp_hi": sp_hi}

    R401, R791, R741, R744 = (g["RHO_401_KGM3"], g["RHO_791_KGM3"], g["RHO_741_KGM3"],
                              g["RHO_744_KGM3"])
    s.FIC_323401 = fic(50.0, g["R3232_E011_M401_DES"] / R401, 0.1 * R401, 7.0, 2000.0 / R401)
    s.FIC_323402 = fic(50.0, g["R3232_E011_M402_DES"] / R791, 0.1 * R791, 7.0, 6000.0 / R791)
    s.FIC_328405 = fic(g["R3232_FIC405_OP_DES"], g["S793_M_DES"] / R401, 0.2 * R401, 15.0,
                       g["S793_CAP_KGH"] / R401)
    if b39:  # B-39: the loop on 735, V1's own 0.06 per kg/h carried to 735's density
        R735 = d.RHO_735_KGM3
        s.FIC_328402 = fic(50.0, g["R328_C002_M738_DES"] / R735, 0.06 * R735, 60.0,
                           60000.0 / R735)
    else:
        s.FIC_328402 = fic(50.0, g["R3232_E003_M744_DES"] / R744, 0.06 * R744, 60.0,
                           60000.0 / R744)
    s.FIC_328406 = fic(0.0, 0.0, 0.75 * R741, 80.0, g["S741_CAP_KGH"] / R741, mode="MAN")
    if decided:  # B-38 and B-41: the table's gains per cent of the transmitters' spans
        for name in DECIDED_GAINS:
            getattr(s, name)["Kc"] = getattr(d, name + "_KC")
    if valves_decided:  # B-44: the loops seeded on the vendor valves' design strokes
        for name, op in DECIDED_OP.items():
            getattr(s, name)["op"] = op
        if not b39:
            s.FIC_328402["op"] = STROKE_744
    s.valves_decided = valves_decided
    s.b39 = b39
    s.aux_pumps = {"322P002A": {"on": True, "mode": "AUTO"},
                   "322P002B": {"on": False, "mode": "AUTO"}}
    s.cap = {}  # the decided transcription's transmitter caps (the port's `cap_*_kgh`)
    return s


def _fic(g, s, c1, design, op_des, key, dt, rho, cap_key, decided):
    """V1's `_fic_flow`, EXECUTED; with the decided heel's cap on the transmitter, the same four
    lines TRANSCRIBED with the ``min`` `FlowLoop.step(flow_cap=...)` adds; on the decided valves,
    TRANSCRIBED with the vendor trim (`decided_valves.fic_flow`)."""
    cap = s.cap.get(cap_key) if decided else None
    if s.valves_decided:
        return dv.fic_flow(g, c1, design, op_des, s.tlag, key, dt, rho=rho, cap=cap)
    if cap is None:
        return g["_fic_flow"](c1, design, op_des, s.tlag, key, dt, rho=rho)
    pre = min(design * (c1["op"] / op_des), cap)
    pv = g["_lag1"](s.tlag, key, pre, 5.0, dt) / rho
    return design * (g["_ctrl_ipd"](c1, pv, dt, None) / op_des)


def _v1_stage2(v1, s, bot_c005, dt, decided=True):
    """V1 `main.py` 8832-8833, 8845 and 8883-8950, stage 2, TRANSCRIBED line for line. With
    `decided`, the heel caps and the overflow of the decided divergence stand in the places the
    port puts them; without, V1 verbatim."""
    g = v1
    cp_328d3i = g["aqueous_cp"](g["A328_CP"], g["A328_D003_TI"], s.a328_d003_TI)
    cp_328d3ii = g["aqueous_cp"](g["A328_CP"], g["A328_D003_TII"], s.a328_d003_TII)
    m739_prev = s.tlag.get("R328_739", g["R328_C004_M739_DES"])
    TI = s.a328_d003_TI
    vd = s.valves_decided
    op_des = DECIDED_OP if vd else {k: 50.0 for k in DECIDED_OP}
    m_401 = _fic(g, s, s.FIC_323401, g["R3232_E011_M401_DES"], op_des["FIC_323401"], "F_323401",
                 dt, g["RHO_401_KGM3"], "734", decided)
    m_402 = _fic(g, s, s.FIC_323402, g["R3232_E011_M402_DES"], op_des["FIC_323402"], "F_323402",
                 dt, g["RHO_791_KGM3"], "791", decided)
    m_793 = _fic(g, s, s.FIC_328405, DECIDED_CAP_793 if vd else g["S793_CAP_KGH"], 100.0,
                 "F_328405", dt, g["RHO_401_KGM3"], "793", decided)
    # V1's FIC-328406, verbatim: the 741 the port's tank is handed (B-50).
    m_741_raw = g["_fic_flow"](s.FIC_328406, g["S741_CAP_KGH"], 100.0, s.tlag, "F_328406", dt,
                               rho=g["RHO_741_KGM3"])
    m_741 = min(m_741_raw, m739_prev)
    run_p002 = s.aux_pumps["322P002A"]["on"] or s.aux_pumps["322P002B"]["on"]
    if s.b39:  # ---- B-39: FIC-328402 on 735; 322P002 delivers 744 (the port's lines) ----
        m_735 = _fic(g, s, s.FIC_328402, g["R328_C002_M738_DES"], op_des["FIC_328402"],
                     "F_328402", dt, d.RHO_735_KGM3, "735", decided)
        m_744 = g["R3232_E003_M744_DES"] * (1.0 if run_p002 else 0.0)
    else:
        m_744_cmd = _fic(g, s, s.FIC_328402, g["R3232_E003_M744_DES"],
                         STROKE_744 if vd else 50.0, "F_328402", dt, g["RHO_744_KGM3"], "744",
                         decided)
        m_744 = m_744_cmd * (1.0 if run_p002 else 0.0)
        m_735 = g["R328_C002_M738_DES"] * (s.a328_d003_MII / g["A328_D003_MII_DES"])
    m_719 = s.tlag.get("R324_719", g["A328_D003_M719"])
    m_720 = s.tlag.get("R324_720", g["A328_D003_M720"])
    m_721 = s.tlag.get("R324_721", g["A328_D003_M721"])
    m_759 = s.tlag.get("R324_759", g["A328_D003_M759"])
    in_compI = m_719 + m_720 + m_721 + m_759 - g["A328_D003_COMP_I_ROUNDING_KGH"]
    in_compII = bot_c005 + m_741 + g["A328_D003_COMP_II_ROUNDING_KGH"]
    lost_i = lost_ii = False
    if decided:  # ---- the decided heel (the port's lines) ----
        rate = 3600.0 / max(dt, 1e-9)
        avail_i = max(max(s.a328_d003_MI - awt.HEEL_I_KG, 0.0) * rate + in_compI, 0.0)
        lost_i = m_744 > avail_i
        if lost_i:
            m_744 = avail_i
        avail_ii = max(max(s.a328_d003_MII - awt.HEEL_II_KG, 0.0) * rate + in_compII, 0.0)
        header = m_735 + m_401 + m_402 + m_793
        lost_ii = header > avail_ii
        if lost_ii:
            share = avail_ii / header
            m_735, m_401, m_402, m_793 = m_735 * share, m_401 * share, m_402 * share, m_793 * share
        if s.b39:
            s.cap = {"735": m_735, "734": m_401, "791": m_402, "793": m_793} if lost_ii else {}
        else:
            s.cap = {"744": m_744} if lost_i or not run_p002 else {}  # B-38: 322P002 stopped
            if lost_ii:
                s.cap.update({"734": m_401, "791": m_402, "793": m_793})
    elif vd:
        s.cap = {}
    out_compI = m_744
    P_compI = ((m_719 * (g["A328_D003_M719_T"] - TI)
                + m_720 * (g["A328_D003_M720_T"] - TI)
                + m_721 * (g["A328_D003_M721_T"] - TI)
                + m_759 * (g["A328_D003_M759_T"] - TI)) / 3600.0 * cp_328d3i
               + (m_719 + m_720 + m_721 + m_759) / 3600.0 * g["A328_D003_LAM_I"])
    k_cap_d3i = (m_719 + m_720 + m_721 + m_759) / 3600.0 * cp_328d3i
    TI_raw = TI + P_compI * dt / max(s.a328_d003_MI * cp_328d3i + k_cap_d3i * dt, 1e-6)
    MI_raw = max(s.a328_d003_MI + (in_compI - out_compI) / 3600.0 * dt, 1.0)
    TII = s.a328_d003_TII
    out_compII = m_735 + m_401 + m_402 + m_793
    P_compII = ((bot_c005 * (g["A328_D003_V001_T"] - TII)
                 + m_741 * (g["A328_M741_T"] - TII)) / 3600.0 * cp_328d3ii)
    k_cap_d3ii = (bot_c005 + m_741) / 3600.0 * cp_328d3ii
    TII_raw = TII + P_compII * dt / max(s.a328_d003_MII * cp_328d3ii + k_cap_d3ii * dt, 1e-6)
    MII_raw = max(s.a328_d003_MII + (in_compII - out_compII) / 3600.0 * dt, 1.0)
    full = (g["A328_D003_MI_FULL"], g["A328_D003_MII_FULL"], g["A328_D003_MIII_FULL"])
    masses, temps = g["redistribute_communicating_compartments"](
        (MI_raw, MII_raw, s.a328_d003_MIII), (TI_raw, TII_raw, s.a328_d003_TIII), full)
    over, t_over = 0.0, None
    if decided:  # ---- the decided overflow (the port's lines) ----
        excess = [max(m - f, 0.0) for m, f in zip(masses, full)]
        if sum(excess) > 0.0:
            masses = tuple(m - x for m, x in zip(masses, excess))
            t_over = sum(x * t for x, t in zip(excess, temps)) / sum(excess)
        over = sum(excess) * 3600.0 / dt
    s.a328_d003_MI, s.a328_d003_MII, s.a328_d003_MIII = masses
    s.a328_d003_TI, s.a328_d003_TII, s.a328_d003_TIII = temps
    return {"735": m_735, "734": m_401, "791": m_402, "793": m_793, "741": m_741, "744": m_744,
            "in_i": in_compI, "out_i": out_compI, "in_ii": in_compII, "out_ii": out_compII,
            "lost_i": lost_i, "lost_ii": lost_ii, "over": over, "t_over": t_over,
            "LI": g["d003_level_telemetry"](s)}


LOOPS = (("FIC_323401", "fic_323401", "F_323401"), ("FIC_323402", "fic_323402", "F_323402"),
         ("FIC_328405", "fic_328405", "F_328405"), ("FIC_328402", "fic_328402", "F_328402"))


def _assert_tick(a: dict, b: awt.AmmoniaWaterTankResult, s, tank, loops, label):
    assert (a["735"], a["734"], a["791"], a["793"], a["741"], a["744"]) == (
        b.m_735_kgh, b.m_734_kgh, b.m_791_kgh, b.m_793_kgh, b.m_741_kgh, b.m_744_kgh), label
    assert (a["in_i"], a["out_i"], a["in_ii"], a["out_ii"], a["lost_i"], a["lost_ii"],
            a["over"]) == (b.in_i_kgh, b.out_i_kgh, b.in_ii_kgh, b.out_ii_kgh,
                           b.suction_lost_i, b.suction_lost_ii, b.m_overflow_kgh), label
    if a["t_over"] is not None:
        assert a["t_over"] == b.t_overflow_c, label
    assert (s.a328_d003_MI, s.a328_d003_MII, s.a328_d003_MIII, s.a328_d003_TI, s.a328_d003_TII,
            s.a328_d003_TIII) == (tank.m_i_kg, tank.m_ii_kg, tank.m_iii_kg, tank.t_i_c,
                                  tank.t_ii_c, tank.t_iii_c), label
    assert (b.m_i_kg, b.m_ii_kg, b.m_iii_kg, b.t_i_c, b.t_ii_c, b.t_iii_c) == (
        tank.m_i_kg, tank.m_ii_kg, tank.m_iii_kg, tank.t_i_c, tank.t_ii_c, tank.t_iii_c), label
    # main.py 3774-3783: the telemetry rounds the levels the port publishes.
    assert (a["LI"]["LI_328I"], a["LI"]["LI_328II"], a["LI"]["LI_328III"]) == (
        round(b.level_i_pct, 1), round(b.level_ii_pct, 1), round(b.level_iii_pct, 1)), label
    for v1_name, port_name, key in LOOPS:
        v1c, loop = getattr(s, v1_name), getattr(loops, port_name)
        assert (v1c["op"], v1c["sp"], v1c["pv"], v1c["pv1"], v1c["pv2"], v1c["mode"]) == (
            loop.loop.op, loop.loop.sp, loop.loop.pv, loop.loop.pv1, loop.loop.pv2,
            loop.loop.mode), (label, v1_name)
        assert s.tlag[key] == loop.measurement, (label, key)


# --------------------------------------------------------------------------------------
# The design basis
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("ours, theirs", [
    ("D003_M719_DES_KGH", "A328_D003_M719"), ("D003_T719_C", "A328_D003_M719_T"),
    ("D003_M720_DES_KGH", "A328_D003_M720"), ("D003_T720_C", "A328_D003_M720_T"),
    ("D003_M721_DES_KGH", "A328_D003_M721"), ("D003_T721_C", "A328_D003_M721_T"),
    ("D003_M759_DES_KGH", "A328_D003_M759"), ("D003_T759_C", "A328_D003_M759_T"),
    ("PHI744", "R3232_E003_PHI744"), ("M744_DES_KGH", "R3232_E003_M744_DES"),
    ("M735_DES_KGH", "R328_C002_M738_DES"), ("M401_DES_KGH", "R3232_E011_M401_DES"),
    ("M402_DES_KGH", "R3232_E011_M402_DES"), ("S793_M_DES_KGH", "S793_M_DES"),
    ("C004_M739_DES_KGH", "R328_C004_M739_DES"), ("T741_C", "A328_M741_T"),
    ("D003_VOL_I_M3", "A328_D003_VOL_I_M3"), ("D003_VOL_II_M3", "A328_D003_VOL_II_M3"),
    ("D003_VOL_III_M3", "A328_D003_VOL_III_M3"), ("D003_VOL_TOTAL_M3", "A328_D003_VOL_TOTAL_M3"),
    ("D003_RHO_KGM3", "A328_D003_RHO_KGM3"), ("D003_MI_FULL_KG", "A328_D003_MI_FULL"),
    ("D003_MII_FULL_KG", "A328_D003_MII_FULL"), ("D003_MIII_FULL_KG", "A328_D003_MIII_FULL"),
    ("D003_MI_DES_KG", "A328_D003_MI_DES"), ("D003_MII_DES_KG", "A328_D003_MII_DES"),
    ("D003_MIII_DES_KG", "A328_D003_MIII_DES"),
    ("D003_ROUNDING_I_KGH", "A328_D003_COMP_I_ROUNDING_KGH"),
    ("D003_ROUNDING_II_KGH", "A328_D003_COMP_II_ROUNDING_KGH"), ("D003_CP", "A328_CP"),
    ("D003_TI_C", "A328_D003_TI"), ("D003_TII_C", "A328_D003_TII"),
    ("D003_TIII_C", "A328_D003_TIII"), ("D003_T343_C", "A328_D003_V001_T"),
    ("D003_LAM_I_KJKG", "A328_D003_LAM_I"), ("RHO_401_KGM3", "RHO_401_KGM3"),
    ("RHO_791_KGM3", "RHO_791_KGM3"), ("RHO_741_KGM3", "RHO_741_KGM3"),
    ("S744_VOL_DES_M3H", "S744_VOL_DES"), ("RHO_744_KGM3", "RHO_744_KGM3"),
    ("FIC_328405_OP_DES_PCT", "R3232_FIC405_OP_DES"),
])
def test_design_basis(v1, ours, theirs):
    assert getattr(d, ours) == v1[theirs]


def test_the_744_solvent_split_reads_the_same_756(v1):
    assert c.C005_M756_DES_KGH == v1["A328_M756_DES"]


def test_the_four_loops_are_seeded_as_v1_seeds_them(v1):
    """Every seed V1's but the gain: V1 carries the table's number per kg/h into m3/h (FIC-328402
    its own 0.06), the port the table's number per cent of the transmitter's span. FIC-328406,
    V1's fifth, is 328C004's (B-50)."""
    s, loops = _v1_state(v1), awt.TankLoops()
    assert not hasattr(loops, "fic_328406")
    rho = {"FIC_323401": d.RHO_401_KGM3, "FIC_323402": d.RHO_791_KGM3,
           "FIC_328405": d.RHO_401_KGM3}
    for name, r in rho.items():
        assert s.__dict__[name]["Kc"] == getattr(d, name + "_KC_TABLE") * r
        span = getattr(d, "FT_" + name[4:] + "_SPAN_M3H")
        assert getattr(d, name + "_KC") == getattr(d, name + "_KC_TABLE") * 100.0 / span
    for v1_name, port_name, _ in LOOPS:
        v1c, loop = getattr(s, v1_name), getattr(loops, port_name).loop
        kc = getattr(d, v1_name + "_KC")  # B-38, B-41, decided
        assert (v1c["mode"], v1c["op"], v1c["sp"], v1c["pv"], v1c["pv1"], v1c["pv2"], kc,
                v1c["Ti"], v1c["Td"], v1c["act"], v1c["op_lo"], v1c["op_hi"], v1c["sp_lo"],
                v1c["sp_hi"]) == (loop.mode, loop.op, loop.sp, loop.pv, loop.pv1, loop.pv2,
                                  loop.Kc, loop.Ti, loop.Td, loop.act, loop.op_lo, loop.op_hi,
                                  loop.sp_lo, loop.sp_hi), v1_name


# --------------------------------------------------------------------------------------
# The openings, V1's function executed
# --------------------------------------------------------------------------------------

FULL = awt.FULL_KG


@pytest.mark.parametrize("masses, temps", [
    ((8928.0, 21328.0, 212784.0), (44.0, 56.0, 52.459016393442624)),
    ((12000.0, 21328.0, 212784.0), (44.0, 56.0, 52.5)),
    ((8928.0, 1.0, 212784.0), (44.0, 56.0, 52.5)),
    ((1.0, 1.0, 0.0), (44.0, 56.0, 52.5)),
    ((1.0, 1.0, 25.0), (60.0, 20.0, 40.0)),
    ((20000.0, 50000.0, 430000.0), (44.0, 56.0, 52.5)),
    ((0.0, 0.0, 0.0), (44.0, 56.0, 52.5)),
    ((0.0, 0.0, 5.0), (44.0, 56.0, 52.5)),
    ((17856.0, 0.0, 0.0), (90.0, 10.0, 30.0)),
])
def test_the_openings(v1, masses, temps):
    assert awt.redistribute_communicating_compartments(masses, temps, FULL) == \
        v1["redistribute_communicating_compartments"](masses, temps, FULL)


@pytest.mark.parametrize("masses, temps, full", [
    ((1.0, 1.0), (44.0, 56.0), (1.0, 2.0)),
    ((1.0, math.nan, 1.0), (44.0, 56.0, 50.0), FULL),
    ((1.0, 1.0, 1.0), (44.0, math.inf, 50.0), FULL),
    ((1.0, -1.0, 1.0), (44.0, 56.0, 50.0), FULL),
    ((1.0, 1.0, 1.0), (44.0, 56.0, 50.0), (1.0, 0.0, 1.0)),
])
def test_the_openings_refuse_what_v1_refuses(v1, masses, temps, full):
    with pytest.raises(ValueError) as theirs:
        v1["redistribute_communicating_compartments"](masses, temps, full)
    with pytest.raises(ValueError, match=str(theirs.value)):
        awt.redistribute_communicating_compartments(masses, temps, full)


# --------------------------------------------------------------------------------------
# The tank on its own, tick by tick
# --------------------------------------------------------------------------------------

M343 = c.C005_BOT_DES_KGH
COND = {"m719": d.D003_M719_DES_KGH, "m720": d.D003_M720_DES_KGH,
        "m721": d.D003_M721_DES_KGH, "m759": d.D003_M759_DES_KGH}


def _design(**over):
    """A tick's boundaries: ``m739`` feeds V1's clamp on its own 741, ``m741`` the port's tank
    when it runs alone — beside V1 it takes V1's 741 (`_run`)."""
    base = {"m343": M343, **COND, "m739": d.C004_M739_DES_KGH, "m741": 0.0, "p002": True}
    base.update(over)
    return base


def _feed(s, x):
    """Write a tick's boundaries into V1's tears and 322P002's state."""
    for k in ("719", "720", "721", "759"):
        s.tlag["R324_" + k] = x["m" + k]
    s.tlag["R328_739"] = x["m739"]
    s.aux_pumps["322P002A"]["on"] = x["p002"]


def _port(tank, loops, x, dt):
    return tank.step(loops, x["m343"], x["m719"], x["m720"], x["m721"], x["m759"], x["m741"],
                     x["p002"], dt)


def _beside(x, a):
    """The port's boundaries beside V1's tick: the 741 V1's own FIC-328406 gave."""
    return {**x, "m741": a["741"]}


def _set_state(s, tank, masses, temps):
    s.a328_d003_MI, s.a328_d003_MII, s.a328_d003_MIII = masses
    s.a328_d003_TI, s.a328_d003_TII, s.a328_d003_TIII = temps
    tank.m_i_kg, tank.m_ii_kg, tank.m_iii_kg = masses
    tank.t_i_c, tank.t_ii_c, tank.t_iii_c = temps


def _run(v1, script, ticks: int, dt: float = DT, act=None, start=None, decided=True):
    """Drive the tank alone through `script(k)`, comparing everything every tick. `act(k, s,
    loops)` moves both sides' controllers before tick k; `start` is an initial (masses, temps)."""
    s = _v1_state(v1, decided)
    tank, loops = awt.AmmoniaWaterTank(), awt.TankLoops()
    if start:
        _set_state(s, tank, *start)
    b = None
    for k in range(ticks):
        if act:
            act(k, s, loops)
        x = script(k)
        _feed(s, x)
        a = _v1_stage2(v1, s, x["m343"], dt, decided)
        b = _port(tank, loops, _beside(x, a), dt)
        _assert_tick(a, b, s, tank, loops, f"tick {k}")
    return s, tank, loops, b


def _step(t0: int, **over):
    return lambda k: _design(**(over if k >= t0 else {}))


def _sp(v1_name, port_name, value, t0=10):
    """An operator's set point [m3/h] on one loop, on both sides, from tick t0."""
    def act(k, s, loops):
        if k == t0:
            getattr(s, v1_name)["sp"] = value
            getattr(loops, port_name).loop.sp = value
    return act


def _man(v1_name, port_name, op, t0=10):
    """A loop put in MAN at a stroke, on both sides, from tick t0; V1's alone where the port
    has no such loop here (FIC-328406, 328C004's)."""
    def act(k, s, loops):
        if k == t0:
            getattr(s, v1_name).update(mode="MAN", op=op)
            if port_name is not None:
                getattr(loops, port_name).loop.mode = "MAN"
                getattr(loops, port_name).loop.op = op
    return act


HOT_II = ((d.D003_MI_DES_KG, d.D003_MII_DES_KG, d.D003_MIII_DES_KG),
          (d.D003_TI_C, d.D003_TII_C + 10.0, d.D003_TIII_C))
UNLEVEL = ((0.5 * d.D003_MI_DES_KG, 1.5 * d.D003_MII_DES_KG, d.D003_MIII_DES_KG),
           (60.0, 30.0, d.D003_TIII_C))

SCENARIOS = {
    "design hold": (lambda k: _design(), 600, DT, None, None),
    "343 gone (323C005's solvent lost)": (_step(10, m343=0.0), 1200, 0.5, None, None),
    "343 up a fifth": (_step(10, m343=1.2 * M343), 1200, 0.5, None, None),
    "the vacuum train's condensates gone": (
        _step(10, m719=0.0, m720=0.0, m721=0.0, m759=0.0), 1200, 0.5, None, None),
    "the condensates up 30 %": (
        _step(10, **{k: 1.3 * v for k, v in COND.items()}), 1200, 0.5, None, None),
    "FIC-323402 to 2.0 m3/h": (lambda k: _design(), 600, DT,
                               _sp("FIC_323402", "fic_323402", 2.0), None),
    "FIC-323401 in MAN at 80 %": (lambda k: _design(), 600, DT,
                                  _man("FIC_323401", "fic_323401", 80.0), None),
    "FIC-328405 opened to 1.0 m3/h": (lambda k: _design(), 1200, 0.5,
                                      _sp("FIC_328405", "fic_328405", 1.0), None),
    "741 back to compartment II at 16.9 t/h": (
        lambda k: _design(), 1200, 0.5, _man("FIC_328406", None, 50.0), None),
    "compartment II starts 10 K hot": (lambda k: _design(), 1200, 0.5, None, HOT_II),
    "the bays start unlevelled": (lambda k: _design(), 600, DT, None, UNLEVEL),
}


#: The scenarios that move a set point, where a loop's gain acts: run on the decided gains (B-41).
ON_THE_DECIDED_GAINS = ("FIC-323402 to 2.0 m3/h", "FIC-328405 opened to 1.0 m3/h")


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_the_tank_tick_by_tick(v1, name):
    script, ticks, dt, act, start = SCENARIOS[name]
    s, tank, loops, b = _run(v1, script, ticks, dt, act, start,
                             decided=name in ON_THE_DECIDED_GAINS)
    # Every one stays between the heel and full, where the decided lines are inert.
    assert not (b.suction_lost_i or b.suction_lost_ii) and b.m_overflow_kgh == 0.0
    if name == "the bays start unlevelled":
        assert b.level_i_pct == pytest.approx(b.level_ii_pct, rel=1e-12)
        assert b.level_i_pct == pytest.approx(b.level_iii_pct, rel=1e-12)
    if name == "741 back to compartment II at 16.9 t/h":
        assert b.m_741_kgh == pytest.approx(16862.0, rel=1e-12)


# --------------------------------------------------------------------------------------
# The decided divergence: the heel and the overflow, both sides
# --------------------------------------------------------------------------------------

def _books(b, before_kg, dt):
    """The liquid the tick made (+) or lost (-) against its own streams and overflow [kg]."""
    after = b.m_i_kg + b.m_ii_kg + b.m_iii_kg
    return after - before_kg - (b.in_i_kgh + b.in_ii_kgh - b.out_i_kgh - b.out_ii_kgh
                                - b.m_overflow_kgh) * dt / 3600.0


def _diverge(v1, script, ticks, dt, start, act=None):
    """V1 verbatim against the port: the tick the port's limit first binds, V1's state, and the
    port's result; bit-exact before that tick."""
    s = _v1_state(v1)
    tank, loops = awt.AmmoniaWaterTank(), awt.TankLoops()
    _set_state(s, tank, *start)
    for k in range(ticks):
        if act:
            act(k, s, loops)
        x = script(k)
        _feed(s, x)
        a = _v1_stage2(v1, s, x["m343"], dt, decided=False)
        b = _port(tank, loops, _beside(x, a), dt)
        if b.suction_lost_i or b.suction_lost_ii or b.m_overflow_kgh > 0.0:
            return k, s, a, b, tank, loops
        _assert_tick(a, b, s, tank, loops, f"tick {k}")
    raise AssertionError("the limit was never reached")


def EMPTY(k):
    """Nothing arrives: 323C005 and the vacuum train both lost."""
    return _design(m343=0.0, m719=0.0, m720=0.0, m721=0.0, m759=0.0)


NEAR_EMPTY = (tuple(300.0 * f / sum(FULL) for f in FULL), (d.D003_TI_C, d.D003_TII_C, 50.0))
NEAR_FULL = (tuple(0.9995 * f for f in FULL), (d.D003_TI_C, d.D003_TII_C, 50.0))
OPEN_741 = _man("FIC_328406", None, 100.0, t0=0)


def test_the_pumps_at_the_heel_the_port_against_its_transcription(v1):
    """Through the heel and on for a minute, the port is its transcription, tick by tick."""
    s, tank, loops, b = _run(v1, EMPTY, 1200, DT, start=NEAR_EMPTY)
    assert b.suction_lost_i and b.suction_lost_ii
    assert (b.m_i_kg, b.m_ii_kg) == pytest.approx((awt.HEEL_I_KG, awt.HEEL_II_KG), abs=1e-9)


def test_the_pumps_at_the_heel_decided_divergence(v1):
    """V1's pumps run on at their full flow from an empty tank, its floors making the liquid; the
    port's are capped at the heel, flagged, and their transmitters read what they deliver."""
    k0, s, a, b, tank, loops = _diverge(v1, EMPTY, 3000, DT, NEAR_EMPTY)
    assert 100 < k0 < 400
    # The port on the first capped tick: 322P002 gives only the liquid above compartment I's heel.
    assert b.suction_lost_i and b.m_744_kgh < a["744"] == d.M744_DES_KGH
    # V1 over the next minute: both pumps at their set flows; the tank makes their liquid.
    made_v1 = 0.0
    for _ in range(600):
        before = s.a328_d003_MI + s.a328_d003_MII + s.a328_d003_MIII
        x = EMPTY(0)
        _feed(s, x)
        a = _v1_stage2(v1, s, 0.0, DT, decided=False)
        after = s.a328_d003_MI + s.a328_d003_MII + s.a328_d003_MIII
        made_v1 += after - before - (a["in_i"] + a["in_ii"] - a["out_i"] - a["out_ii"]) * DT / 3600
    assert a["744"] == pytest.approx(d.M744_DES_KGH, rel=1e-6)
    assert made_v1 > 50.0
    # The port over the same minute: capped, and the only liquid it makes is V1's -1 kg/h
    # rounding, restored by the floor at compartment I's heel.
    made = 0.0
    for _ in range(600):
        before = tank.m_i_kg + tank.m_ii_kg + tank.m_iii_kg
        b = _port(tank, loops, EMPTY(0), DT)
        made += _books(b, before, DT)
    assert b.suction_lost_i and b.suction_lost_ii and b.m_744_kgh == 0.0
    # FT-328402 on 735 (B-39) reads what 328P003 delivers: 735's share of compartment II's 2 kg/h.
    assert loops.fic_328402.measurement < 1.0 + d.D003_ROUNDING_II_KGH
    assert 0.0 <= made <= 60.0 * d.D003_ROUNDING_I_KGH / 3600.0 + 1e-9


def test_the_full_tank_the_port_against_its_transcription(v1):
    """Through the first overflow and on for ten minutes, the port is its transcription."""
    s, tank, loops, b = _run(v1, lambda k: _design(), 1200, 0.5, act=OPEN_741, start=NEAR_FULL)
    assert b.m_overflow_kgh > 0.0
    assert max(b.level_i_pct, b.level_ii_pct, b.level_iii_pct) <= 100.0 + 1e-9


def test_the_full_tank_decided_divergence(v1):
    """V1's bays level above their capacity with 741 open; the port's overflow at 100 %."""
    k0, s, a, b, _, _ = _diverge(v1, lambda k: _design(), 3000, 0.5, NEAR_FULL, act=OPEN_741)
    assert k0 > 10
    assert b.m_overflow_kgh > 0.0 and b.level_ii_pct <= 100.0 + 1e-9
    assert a["LI"]["LI_328II"] >= 100.0
    assert s.a328_d003_MII > d.D003_MII_FULL_KG
    # What V1 holds above full is what the port lets go, on this first tick.
    v1_above = sum(m - f for m, f in zip((s.a328_d003_MI, s.a328_d003_MII, s.a328_d003_MIII),
                                          FULL))
    assert b.m_overflow_kgh * 0.5 / 3600.0 == pytest.approx(v1_above, rel=1e-9)


# --------------------------------------------------------------------------------------
# Coupled: 323C005 -> 328D003 -> 323E011 as V1 steps them
# --------------------------------------------------------------------------------------

def test_343_and_791_are_same_tick_and_702_the_one_tear():
    """V1's order is legal only because 343 and 791 run forward: 323C005 before 328D003 before
    323E011. The cycle closes through 702, and 702 is the declared tear."""
    fs = Flowsheet()
    for tag in ("323C005", "328D003", "323E011"):
        fs.add_unit(Unit(tag, tag, tag[:3]))
    fs.connect(Connection("343", "323C005", "328D003"))
    fs.connect(Connection("791", "328D003", "323E011"))
    fs.connect(Connection("702", "323E011", "323C005"))
    with pytest.raises(CyclicFlowsheetError):
        fs.evaluation_order()
    fs.tear(Tear("R3232_702", "323E011", ("323C005",),
                 "V1 steps the absorber first; the vent is read a tick late"))
    assert fs.evaluation_order() == ("323C005", "328D003", "323E011")


def test_the_tank_takes_343_on_the_same_tick(v1):
    """V1's stage 1, stage 2 and stage 9 in V1's order, and the tear write at the end of V1's
    block, against the ported absorber, tank and condenser in the same order: the tank takes the
    absorber's 343 of THIS tick and the condenser the tank's 791 of this tick. 323C005's solvent
    halved, and FIC-323402 moved, move both hand-offs; the move runs on the decided gains."""
    s = _v1_state(v1, decided=True)
    absorber, tank, loops = aa.AtmosphericAbsorber(), awt.AmmoniaWaterTank(), awt.TankLoops()
    cond, loops9 = fc.FlashCondenser(**fc.V1_CONDENSER), stage9._loops()
    m702_prev = c.C005_M702_DES_KGH
    inert = dict(c.E002_INERT_DES_KMOLH)
    seen_343 = set()
    for k in range(3000):
        m756 = c.C005_M756_DES_KGH * (0.5 if k >= 10 else 1.0)
        if k == 1500:
            s.FIC_323402["sp"] = loops.fic_323402.loop.sp = 1.2
        s.tlag["R322_756"] = m756
        x9 = stage9._design(m701=stage9.M701)
        a1 = stage1._v1_stage1(v1, s, DT)
        a2 = _v1_stage2(v1, s, a1["343"], DT, decided=True)
        a9 = stage9._v1_stage9(v1, s, x9["m701"], x9["b505"], x9["b501"], x9["m786"],
                               x9["m321"], a2["791"], DT)
        s.tlag["R3232_702"] = a9["vent"]
        b1 = absorber.step(m702_prev, m756, c.C005_M708_DES_KGH, inert, c.C005_T756_C, DT)
        b2 = _port(tank, loops, _beside(_design(m343=b1.m_343_kgh), a2), DT)
        b9 = cond.step(*loops9, x9["m701"], x9["b505"], x9["b501"], x9["m786"], x9["m321"],
                       b2.m_791_kgh, DT)
        m702_prev = b9.m_702_kgh
        stage1._assert_tick(a1, b1, s, absorber, f"stage 1, tick {k}")
        _assert_tick(a2, b2, s, tank, loops, f"stage 2, tick {k}")
        stage9._assert_tick(a9, b9, s, cond, loops9, f"stage 9, tick {k}")
        seen_343.add(b1.m_343_kgh)
    assert len(seen_343) > 100 and b2.m_791_kgh != d.M402_DES_KGH


def test_last_ticks_343_is_not_v1s(v1):
    """The control: fed 343 one tick late, as a tear would feed it, the tank leaves V1 on the
    tick after the absorber's bottoms first move."""
    s = _v1_state(v1)
    absorber, tank, loops = aa.AtmosphericAbsorber(), awt.AmmoniaWaterTank(), awt.TankLoops()
    m343_prev = c.C005_BOT_DES_KGH
    for k in range(40):
        s.tlag["R322_756"] = m756 = c.C005_M756_DES_KGH * (0.5 if k >= 10 else 1.0)
        a1 = stage1._v1_stage1(v1, s, DT)
        _v1_stage2(v1, s, a1["343"], DT, decided=False)
        b1 = absorber.step(c.C005_M702_DES_KGH, m756, c.C005_M708_DES_KGH,
                           dict(c.E002_INERT_DES_KMOLH), c.C005_T756_C, DT)
        _port(tank, loops, _design(m343=m343_prev), DT)
        m343_prev = b1.m_343_kgh
        if tank.t_ii_c != s.a328_d003_TII or tank.m_ii_kg != s.a328_d003_MII:
            assert k == 10
            return
    raise AssertionError("a one-tick-late 343 never left V1")


# --------------------------------------------------------------------------------------
# The decided divergence: the vendor valves (handoff B-44), both sides
# --------------------------------------------------------------------------------------

def test_the_vendor_valves_decided_divergence(v1):
    """V1 verbatim against the port. At design every draw is its design flow on both — each
    valve is anchored at its own design stroke, V1's 50 %, the port's where its Kvs passes the
    flow. Stroked by hand they part: FV-323401 at 80 % passes 1.60 times its design on V1's
    linear trim and 2.51 times on the vendor's. (FV-328406 is 328C004's, B-50.)"""
    s = _v1_state(v1, valves_decided=False)
    tank, loops = awt.AmmoniaWaterTank(), awt.TankLoops()
    x = _design()
    _feed(s, x)
    a, b = _v1_stage2(v1, s, x["m343"], DT, decided=False), _port(tank, loops, x, DT)
    assert (a["734"], a["791"], a["744"]) == (b.m_734_kgh, b.m_791_kgh, b.m_744_kgh) == (
        d.M401_DES_KGH, d.M402_DES_KGH, d.M744_DES_KGH)
    assert (s.FIC_323401["op"], s.FIC_328402["op"]) == (50.0, 50.0)
    assert (loops.fic_323401.loop.op, loops.fic_328402.loop.op) == (
        DECIDED_OP["FIC_323401"], DECIDED_OP["FIC_328402"])
    _man("FIC_323401", "fic_323401", 80.0, t0=1)(1, s, loops)
    _feed(s, x)
    a, b = _v1_stage2(v1, s, x["m343"], DT, decided=False), _port(tank, loops, x, DT)
    assert a["734"] == pytest.approx(1.6 * d.M401_DES_KGH, rel=1e-12)
    assert b.m_734_kgh / d.M401_DES_KGH == pytest.approx(2.5118, abs=1e-4)


def test_the_inlets_at_their_producers_temperatures_decided_divergence(v1):
    """B-31, decided 2026-10-16: 328D003 charges 343 at 323C005's live temperature and the
    condensates 719, 720, 721 and 759 at their condensers' live cold ends, each as its departure
    from its producer's design; V1 at 56, 45, 40, 41 and 55 C whatever they do. With every
    producer on its design the port is V1's on every tick, and so it is with every producer 5 K
    hot on V1's switch. Live, compartment I parts 0.0049 K hotter on the first one-second tick and
    II 0.0022 K; after half an hour I stands at 48.142 C and II at 58.756 C against V1's 44 and
    56 C, compartment III, which no stream reaches while the levels stand together, unmoved."""
    des = {"t_c005_c": c.C005_T_C, "t_cold_ends_c": dict(awt.T_COLD_END_DES_C)}
    hot = {"t_c005_c": c.C005_T_C + 5.0,
           "t_cold_ends_c": {k: v + 5.0 for k, v in awt.T_COLD_END_DES_C.items()}}

    def run(kw, live, ticks, dt, check):
        s = _v1_state(v1)
        tank, loops = awt.AmmoniaWaterTank(live_inlets=live), awt.TankLoops()
        first = None
        for k in range(ticks):
            x = _design()
            _feed(s, x)
            a = _v1_stage2(v1, s, x["m343"], dt)
            y = _beside(x, a)
            b = tank.step(loops, y["m343"], y["m719"], y["m720"], y["m721"], y["m759"],
                          y["m741"], y["p002"], dt, **kw)
            if check:
                _assert_tick(a, b, s, tank, loops, f"live {live}, tick {k}")
            if first is None:
                first = (tank.t_i_c - s.a328_d003_TI, tank.t_ii_c - s.a328_d003_TII)
        return s, tank, first
    run(des, True, 600, DT, True)
    run(hot, False, 600, DT, True)
    s, tank, first = run(hot, True, 1800, 1.0, False)
    assert first == (pytest.approx(0.004892, abs=1e-6), pytest.approx(0.002225, abs=1e-6))
    assert (s.a328_d003_TI, s.a328_d003_TII) == (44.0, 56.0)
    assert (tank.t_i_c, tank.t_ii_c, tank.t_iii_c) == (
        pytest.approx(48.1415, abs=1e-4), pytest.approx(58.7559, abs=1e-4), s.a328_d003_TIII)


def test_322p002s_field_set_delivery_decided_divergence(v1):
    """Decision 212 (B-133): with 322P002 running V1 delivers the PFD's 744 whatever the field
    operator would set; the port delivers what is set, here 15 m3/h on FI-322402's density, and
    compartment I keeps the rest of its condensates. At the seed both deliver the PFD's 744."""
    s = _v1_state(v1, True)
    tank, loops = awt.AmmoniaWaterTank(), awt.TankLoops()
    x = _design()
    _feed(s, x)
    a = _v1_stage2(v1, s, x["m343"], DT, True)
    y = _beside(x, a)
    set_kgh = 15.0 * 1005.0
    b = tank.step(loops, y["m343"], y["m719"], y["m720"], y["m721"], y["m759"], y["m741"],
                  y["p002"], DT, m_744_set_kgh=set_kgh)
    assert a["744"] == v1["R3232_E003_M744_DES"] == d.M744_DES_KGH
    assert b.m_744_kgh == set_kgh < a["744"]
    assert b.in_i_kgh - b.out_i_kgh == pytest.approx(a["744"] - set_kgh)
    seeded = awt.AmmoniaWaterTank().step(awt.TankLoops(), y["m343"], y["m719"], y["m720"],
                                          y["m721"], y["m759"], y["m741"], y["p002"], DT,
                                          m_744_set_kgh=d.M744_DES_KGH)
    assert seeded.m_744_kgh == a["744"]
