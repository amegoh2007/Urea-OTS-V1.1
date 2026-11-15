"""V1 <-> V1.1 equivalence for 328D001 and 328E004, the reflux drum and its condenser.

What is being proved
--------------------
V1 writes the drum inline in `step_sim`, so its statements are TRANSCRIBED into `_v1_d001`
below, line for line, and declared as such: the aqueous cp (``main.py`` 8831), the tear reads
(8840-8841), the stage itself (9254-9347), the 775 tear write (9671) and TT-329007 (10842-10846).
Everything they call is V1's own code, executed: ``_ctrl_ipd``, ``_fic_flow``, ``_lag1``,
``aqueous_cp`` and ``psat_water_bara`` lifted out of ``main.py`` with every constant they read;
``hydraulics`` loaded as a real module. The state is seeded as ``State.__init__`` seeds it
(6844-6847, 6993-7025, 7066-7081).

The departures
--------------
Ten, each a switch in the transcription: ``decided`` names the ones whose port lines stand in
V1's. Four were decided by the process engineer for this unit on 2026-09-30, and one on
2026-10-01:

  * "relief" — SV32353 vents the head space's vapour between its 6.01 bar a set pressure and its
    5.51 reseat, on its orifice's own area at Sempell's gas coefficient for the orifice, 0.922 (handoffs B-47,
    A-16), the law written out in `decided_relief`; V1 relieves nothing;

  * "B-53" — the vessel's true 5500 l, heads included, and LI-328501 read between LT-328501's
    taps, 220 mm above the bottom tangent and 1510 mm apart; the design holdup what reads the set
    point on them. V1 takes the cylinder alone and reads M / M_des x 50.5 (handoff B-53);

  * "pinch" — 328E004's duty held to what brings the drum to its 30 C cooling water; V1's
    stroke-proportional duty cools the drum without limit (decision 28);
  * "vent" — PV-328202 discharges against 323E011's pressure of the tick before; V1 against
    323E011's design 1.13 bar a (decision 29);
  * "A-15" — the liquid a full 328C002 carries out through its overhead enters the drum at the
    column's bottoms temperature (decision 30).

The other five are classes decided on other units, applied here under §5 rule 7:

  * "vapour" — the liquid loses the vapour 328E004 left uncondensed, which the head space takes;
    V1 takes the vent's flow out of it (decision 24);
  * "heel" — 328P002's 775 and 776 share the liquid above a 1 kg heel, FT-328404 reading the 775
    delivered (decision 11);
  * "overflow" — a full cylinder's excess leaves as a stream (decision 11);
  * "valve" — LV-328501, FV-328404 and PV-328202 on their vendor trims from the strokes their Kvs
    give (decision 23), V1's ``hydraulics`` and ``_fic_flow`` executed on them through
    `decided_valves`;
  * "gains" — PIC-328202 and TIC-328002 on the table's gains per cent of span (decision 10).

Every scenario runs the port against the switched transcription; those where neither limit binds
also run on V1's lines for both limits; each departure runs both ways. Last, the drum is coupled to
V1's 328C002 in V1's order: 737 same-tick, the drum's pressure and 775 tears into the column.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from ureasim.core.flowsheet import Connection, CyclicFlowsheetError, Flowsheet, Tear, Unit
from ureasim.data import control_valves as cvd
from ureasim.data import desorption_train as t
from ureasim.data import unit_328c002 as c2
from ureasim.data import unit_328d001 as d
from ureasim.units.desorption import first_desorber as fd
from ureasim.units.desorption import reflux_drum as rd
from tests.equivalence import decided_relief as dr
from tests.equivalence import decided_valves as dv
from tests.equivalence import test_first_desorber_equivalence as c002_eq
from tests.equivalence.v1_loader import lift, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

D001_NAMES = [
    "R328_D001_M737_DES", "R328_D001_M718A_DES", "R328_D001_IN_DES", "R328_D001_M786_DES",
    "S775_VOL_DES", "R328_D001_M776_DES", "R328_D001_M776_RHO", "R328_D001_M774_DES",
    "R328_D001_T718A", "R328_D001_ID_M", "R328_D001_TT_M", "R328_D001_VOL_M3", "R328_D001_LVL_SP",
    "R328_D001_M_FULL", "R328_D001_M_DES", "R328_D001_AREA_M2", "R328_D001_W786_DES",
    "R328_D001_MW786_DES", "R328_D001_PV_OP_DES", "R328_D001_LV_OP_DES",
    "R328_D001_FIC404_OP_DES", "R328_E004_Q_DES_KW", "R328_E004_TV_OP_DES",
    "R328_E004_CW_T_IN_C", "R328_E004_CW_T_OUT_DES_C", "R328_E004_CW_T_MAX_C", "R328_D001_SENS",
    "R328_D001_LAM737", "RHO_775_KGM3", "R3232_E011_P_BARA", "R3232_E011_M786_DES",
    "R3232_M718A_DES", "R328_D001_OFFGAS_H2O_PFD", "R328_D001_OFFGAS_PHI",
    "R328_D001_OFFGAS_H2O_DES", "_fic_flow", "_lag1",
]

#: V1's namespaces for 328D003, 328E007 and 328C002, built as their own equivalence tests build
#: them.
tank_v1 = c002_eq.tank_v1
e007_v1 = c002_eq.e007_v1
c002_v1 = c002_eq.v1

DT = 0.1

ALL = frozenset({"vapour", "heel", "overflow", "valve", "gains", "pinch", "vent", "A-15",
                 "B-53", "relief"})
V1_VERBATIM = frozenset()
#: The seeded and inert-at-design departures: V1's lines for the three limits.
ON_BOOKS = frozenset({"vapour", "valve", "gains", "vent", "A-15", "B-53"})

#: The three valves as decided, re-derived from the vendor catalogue: design strokes [%], xT.
DECIDED_LV501_OP = dv.design_stroke_pct(cvd.LV_328501, t.C002_M737_DES_KGH + 3561.5 - 276.0
                                        - 1675.0)
DECIDED_FV404_OP = dv.design_stroke_pct(cvd.FV_328404, 1675.0)
DECIDED_PV202_OP = dv.design_stroke_pct(cvd.PV_328202, 276.0)
DECIDED_PV202_XT = cvd.PV_328202.cases[cvd.PV_328202.normal].xt
#: The vessel as decided (B-53), written from the drawing: 5500 l with the heads, the cylinder
#: 1684 mm inside and 1950 mm long, LT-328501's taps 220 mm above the bottom tangent and 1510 mm
#: apart; the design holdup what reads the set point on them — to the last bit, the port's seed.
DECIDED_VOL_M3 = 5.5
DECIDED_AREA_M2 = 3.141592653589793 * 0.25 * 1.684 ** 2
DECIDED_HEAD_M3 = 0.5 * (DECIDED_VOL_M3 - DECIDED_AREA_M2 * 1.950)


def _li_taps(m_kg: float) -> float:
    """LI-328501 between LT-328501's taps (B-53), written from the drawing."""
    h = max(m_kg / 1095.0 - DECIDED_HEAD_M3, 0.0) / DECIDED_AREA_M2
    return min(max((h - 0.220) / 1.510, 0.0), 1.0) * 100.0


#: SV32353 as decided (A-16), written from its sheets: set 5.0 bar g on 1.010 bar a (Uhde
#: UD-RL-323-EC-0003), reseating 10 % of set below on gas; orifice K, 1462.20 mm2 (Sempell
#: UD-RL-G00-DZ-0001-001 page 90), at Sempell's gas coefficient for the orifice, 0.922 (decision 130).
SV32353 = dr.Valve.orifice(5.0 + 1.010, 5.0 + 1.010 - 0.1 * 5.0, 1462.20 * 1.0e-6, 0.922)


#: PIC-328202 and TIC-328002 as decided, written from their sources: the table's 2.50 on
#: PT-328202's 0-10 bar g, its 3.00 on TT-328002's 0-160 C.
DECIDED_PIC202_KC = 2.50 * 100.0 / 10.0
DECIDED_TIC002_KC = 3.00 * 100.0 / 160.0
#: FIC-328404 on its faceplate in the plant DCS (decided 2026-10-28): 1.00 on 0-8 m3/h, 200 s.
DECIDED_FIC404_KC, DECIDED_FIC404_TI = 1.00 * 100.0 / 8.0, 200.0
#: TIC-328008 on its faceplate (decided 2026-10-28, B-116 (b)): 1.00 on 0-100 wt% water, 60 s, onto
#: FIC-328404's 0-8 m3/h in mass and the mol% PV by 737's slope, written from the PFD's row.
_M_REST = (12.32 * 44.0098 + 41.47 * 17.0304) / (12.32 + 41.47)
DECIDED_TIC8008_KC = (1.00 * 8.0 * 1095.0 / 100.0 * 18.0152 * _M_REST
                      / (0.4621 * 18.0152 + 0.5379 * _M_REST) ** 2)
DECIDED_TIC8008_TI = 60.0


@pytest.fixture(scope="module")
def v1(c002_v1):
    ns = dict(c002_v1)
    ns.update(lift(D001_NAMES, seed=dict(ns)))
    return ns


def _v1_state(v1, decided=ALL):
    """The V1 plant-state fields 328D001 reads and writes, seeded as `State.__init__` seeds them
    (``main.py`` 6844-6847, 6993-7025, 7066-7081); "valve" and "gains" in `decided` seed the
    port's strokes and gains."""
    g = v1
    s = c002_eq._v1_state(v1)
    s.a328_d001_M = g["R328_D001_M_DES"]
    s.a328_d001_T = g["R328_D001_T"]
    s.a328_d001_P = g["R328_D001_P_BARA"]
    s.a328_d001_T_prev = g["R328_D001_T"]
    lvl, p, tt, h = (g["R328_D001_LVL_SP"], g["R328_C002_P_TOP"], g["R328_D001_T"],
                     g["R328_D001_OFFGAS_H2O_DES"])
    s.LIC_328501 = {"mode": "AUTO", "op": g["R328_D001_LV_OP_DES"], "sp": lvl, "pv": lvl,
                    "pv1": lvl, "pv2": lvl, "Kc": 1.0, "Ti": 300.0, "Td": -1.0, "act": -1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0, "sp_hi": 100.0}
    s.PIC_328202 = {"mode": "AUTO", "op": g["R328_D001_PV_OP_DES"], "sp": p, "pv": p, "pv1": p,
                    "pv2": p, "Kc": 2.5, "Ti": 200.0, "Td": 0.0, "act": -1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 2.5, "sp_hi": 5.0}
    s.TIC_328002 = {"mode": "AUTO", "op": g["R328_E004_TV_OP_DES"], "sp": tt, "pv": tt,
                    "pv1": tt, "pv2": tt, "Kc": 3.0, "Ti": 500.0, "Td": 0.0, "act": -1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 45.0, "sp_hi": 80.0}
    r, v = g["RHO_775_KGM3"], g["R328_D001_M775_DES"] / g["RHO_775_KGM3"]
    s.FIC_328404 = {"mode": "CAS", "op": g["R328_D001_FIC404_OP_DES"], "sp": v, "pv": v,
                    "pv1": v, "pv2": v, "Kc": 0.5 * r, "Ti": 25.0, "Td": 0.0, "act": +1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0, "sp_hi": 4000.0 / r}
    s.TIC_328008 = {"mode": "AUTO", "op": g["R328_D001_M775_DES"], "sp": h, "pv": h, "pv1": h,
                    "pv2": h, "Kc": 240.0, "Ti": 110.0, "Td": 0.0, "act": -1.0,
                    "op_lo": 0.0, "op_hi": 4000.0, "sp_lo": 25.0, "sp_hi": 65.0}
    s.cap_775 = None
    s.sv_32353_lifted = False
    s.r3232_e011_P = g["R3232_E011_P_BARA"]
    if "B-53" in decided:
        s.a328_d001_M = rd.D001_M_SEED_KG
    if "valve" in decided:
        s.LIC_328501["op"] = DECIDED_LV501_OP
        s.PIC_328202["op"] = DECIDED_PV202_OP
        s.FIC_328404["op"] = DECIDED_FV404_OP
    if "gains" in decided:
        s.PIC_328202["Kc"] = DECIDED_PIC202_KC
        s.TIC_328002["Kc"] = DECIDED_TIC002_KC
        s.FIC_328404["Kc"], s.FIC_328404["Ti"] = DECIDED_FIC404_KC, DECIDED_FIC404_TI
        s.TIC_328008["Kc"], s.TIC_328008["Ti"] = DECIDED_TIC8008_KC, DECIDED_TIC8008_TI
    return s


def _drum_and_loops():
    """The port's drum and its loops, TV-328002 on V1's linear law from 50 % (its Neldisc, decided
    2026-10-17, has its own both-ways test in `test_reflux_drum_decided_equivalence.py`) and V1's
    line for 328P002's low-level stop, none (decision 217, its own test there too)."""
    return (rd.RefluxDrum(tv_328002=None, l2_stop=False),
            rd.RefluxDrumLoops(tic_328002=rd.tic_328002(d.E004_TV_OP_DES_PCT)))


def _v1_d001(v1, s, m_737, in_c002, m_793, dt, decided=ALL, m_over=0.0):
    """V1 `main.py` 8831, 8840-8841, 9254-9347 and 9671, stage 6, TRANSCRIBED line for line;
    each departure in `decided` puts the port's lines in V1's. ``m_737`` and ``in_c002`` are stage
    3's, ``m_793`` stage 2's, ``m_over`` 328C002's overflow ("A-15"); 328C002's state,
    compartment II's temperature and 323E011's pressure are read off ``s``. One statement is
    moved: 328E004's uncondensed vapour, ``gen786``, is computed after the heat, where the pinch
    needs it — no statement between reads it."""
    g = v1
    hydraulics = g["hydraulics"]
    cp_328d001 = g["aqueous_cp"](g["R328_CP"], g["R328_D001_T"], s.a328_d001_T)    # 8831
    m775_prev = s.tlag.get("R328_775", g["R328_C002_M775_DES"])                      # 8840
    m718A_prev = s.tlag.get("R3232_718A", g["R3232_M718A_DES"])                      # 8841
    Td001 = s.a328_d001_T
    in_d001 = m_737 + m718A_prev + m_793
    if "A-15" in decided:  # ---- 328C002's overflow into the drum (the port's line) ----
        in_d001 = in_d001 + m_over
    # ---- decision 29: the vent's outlet is 323E011's live pressure (the port's), V1 the design --
    p_e011 = s.r3232_e011_P if "vent" in decided else g["R3232_E011_P_BARA"]
    pic202b_op = g["_ctrl_ipd"](s.PIC_328202, s.a328_c002_P, dt)
    if "valve" in decided:  # ---- PV-328202 on its vendor trim (the port's valve) ----
        m_786_d001 = dv.hydraulics().valve_gas_anchored(
            g["R328_D001_M786_DES"], pic202b_op / 100.0, s.a328_d001_P, p_e011,
            Td001 + 273.15, DECIDED_PV202_OP / 100.0, g["R328_D001_P_BARA"],
            g["R3232_E011_P_BARA"], g["R328_D001_T"] + 273.15, g["R328_D001_MW786_DES"],
            characteristic=dv.MOD_EQUAL_PCT, xt=DECIDED_PV202_XT,
            mw_des=g["R328_D001_MW786_DES"])
    else:
        m_786_d001 = hydraulics.valve_gas_anchored(
            g["R328_D001_M786_DES"], pic202b_op / 100.0, s.a328_d001_P, p_e011,
            Td001 + 273.15, g["R328_D001_PV_OP_DES"] / 100.0, g["R328_D001_P_BARA"],
            g["R3232_E011_P_BARA"], g["R328_D001_T"] + 273.15, g["R328_D001_MW786_DES"],
            characteristic="linear", mw_des=g["R328_D001_MW786_DES"])
    tic002_op = g["_ctrl_ipd"](s.TIC_328002, Td001, dt)
    Q_e004 = g["R328_E004_Q_DES_KW"] * (tic002_op / g["R328_E004_TV_OP_DES"])
    _tau_c002_s = s.a328_c002_M / max(in_c002, 1e-6) * 3600.0
    m775_top = g["_lag1"](s.tlag, "R328_775_TOP", m775_prev, _tau_c002_s, dt)
    dt_top_dynamic = 10.0 + (g["R328_C002_DT_TOP"] - 10.0) * (m775_top / g["R328_D001_M775_DES"])
    T_737 = s.a328_c002_T - dt_top_dynamic
    h2o = (100.0 * g["R328_D001_OFFGAS_PHI"] * g["psat_water_bara"](T_737)
           / max(s.a328_c002_P, 0.1))
    tic8008_op = g["_ctrl_ipd"](s.TIC_328008, h2o, dt)
    if "valve" in decided:  # ---- FV-328404 on its vendor trim; FT-328404 on the delivered ----
        m_775 = dv.fic_flow(g, s.FIC_328404, g["R328_D001_M775_DES"], DECIDED_FV404_OP, s.tlag,
                            "F_328404", dt, rho=g["RHO_775_KGM3"], cas_sp=tic8008_op,
                            cap=s.cap_775)
    else:
        assert s.cap_775 is None, "the heel's transmitter cap rides the decided valve"
        m_775 = g["_fic_flow"](s.FIC_328404, g["R328_D001_M775_DES"],
                               g["R328_D001_FIC404_OP_DES"], s.tlag, "F_328404", dt,
                               rho=g["RHO_775_KGM3"], cas_sp=tic8008_op)
    lvl_d001_328 = s.a328_d001_M / g["R328_D001_M_DES"] * g["R328_D001_LVL_SP"]
    if "B-53" in decided:  # ---- LI-328501 between LT-328501's taps (the port's line) ----
        lvl_d001_328 = _li_taps(s.a328_d001_M)
    lic501_op = g["_ctrl_ipd"](s.LIC_328501, lvl_d001_328, dt)
    lv_op_des = DECIDED_LV501_OP if "valve" in decided else g["R328_D001_LV_OP_DES"]
    m_776 = g["R328_D001_M776_DES"] * (lic501_op / lv_op_des)
    sens_d001 = ((m_737 * (T_737 - Td001)
                  + m718A_prev * (g["R328_D001_T718A"] - Td001)
                  + m_793 * (s.a328_d003_TII - Td001)) / 3600.0 * cp_328d001)
    k_cap_328d001 = (m_737 + m718A_prev + m_793) / 3600.0 * cp_328d001
    if "A-15" in decided:  # ---- the overflow's heat, at 328C002's bottoms (the port's lines) ----
        sens_d001 = ((m_737 * (T_737 - Td001)
                      + m718A_prev * (g["R328_D001_T718A"] - Td001)
                      + m_793 * (s.a328_d003_TII - Td001)
                      + m_over * (s.a328_c002_T - Td001)) / 3600.0 * cp_328d001)
        k_cap_328d001 = (m_737 + m718A_prev + m_793 + m_over) / 3600.0 * cp_328d001
    if "pinch" in decided:  # ---- decision 28: 328E004 held above its cooling water ----
        _cap = max(s.a328_d001_M * cp_328d001 + k_cap_328d001 * dt, 1e-6)
        Q_e004 = min(Q_e004, max(sens_d001 + m_737 / 3600.0 * g["R328_D001_LAM737"]
                                 + (Td001 - g["R328_E004_CW_T_IN_C"]) * _cap / max(dt, 1e-9),
                                 0.0))
    condensation_factor = max(Q_e004 / g["R328_E004_Q_DES_KW"], 0.1)
    gen786 = g["R328_D001_M786_DES"] * (m_737 / g["R328_D001_M737_DES"]) / condensation_factor
    # ---- decision 24: the liquid loses the uncondensed vapour (the port's), V1 the vent ----
    boil = gen786 if "vapour" in decided else m_786_d001
    lost = False
    s.cap_775 = None
    if "heel" in decided:  # ---- the decided heel (the port's lines): 775 and 776 share ----
        avail = max(max(s.a328_d001_M - 1.0, 0.0) / max(dt, 1e-9) * 3600.0 + in_d001 - boil,
                    0.0)
        lost = m_775 + m_776 > avail
        if lost:
            share = avail / (m_775 + m_776)
            m_775, m_776 = m_775 * share, m_776 * share
            s.cap_775 = m_775
    P_d001 = sens_d001 + m_737 / 3600.0 * g["R328_D001_LAM737"] - Q_e004
    M_pre, over, full = s.a328_d001_M, 0.0, g["R328_D001_M_FULL"]
    vol = g["R328_D001_VOL_M3"]
    if "B-53" in decided:  # ---- the vessel's true volume, heads included (the port's) ----
        vol = DECIDED_VOL_M3
        full = DECIDED_VOL_M3 * g["R328_D001_M776_RHO"]
    if "overflow" in decided:  # ---- the decided overflow (the port's lines) ----
        m_new = max(M_pre + (in_d001 - boil - m_775 - m_776) / 3600.0 * dt, 1.0)
        if m_new > full:
            over = (m_new - full) / max(dt, 1e-9) * 3600.0
    _mdot_d001 = (in_d001 - boil - m_775 - m_776 - over) / 3600.0
    _vv_d001 = hydraulics.vapour_volume_m3(vol, s.a328_d001_M, g["R328_D001_M776_RHO"])
    _T_d001_pre = s.a328_d001_T
    MW786 = g["R328_D001_MW786_DES"]
    _p_free = s.a328_d001_P + hydraulics.vessel_dpdt(
        s.a328_d001_P, s.a328_d001_T + 273.15, _vv_d001, MW786,
        gen786 / MW786, m_786_d001 / MW786,
        dtdt_k_s=(s.a328_d001_T - s.a328_d001_T_prev) / dt,
        dvvdt_m3_s=-_mdot_d001 / g["R328_D001_M776_RHO"]) * dt
    relief = 0.0
    if "relief" in decided:  # ---- A-16: SV32353 (the port's lines) ----
        relief, s.sv_32353_lifted = dr.vent(
            g, SV32353, s.a328_d001_P, _p_free, s.a328_d001_T + 273.15, MW786, _vv_d001, dt,
            s.sv_32353_lifted)
        if relief > 0.0:
            _p_free += hydraulics.vessel_dpdt(s.a328_d001_P, s.a328_d001_T + 273.15, _vv_d001,
                                              MW786, 0.0, relief / MW786) * dt
    s.a328_d001_P = max(_p_free, 0.1)
    s.a328_d001_T_prev = _T_d001_pre
    s.a328_d001_T = Td001 + P_d001 * dt / max(s.a328_d001_M * cp_328d001
                                              + k_cap_328d001 * dt, 1e-6)
    s.a328_d001_M = max(s.a328_d001_M + (in_d001 - boil - m_775 - m_776) / 3600.0 * dt, 1.0)
    if over:
        s.a328_d001_M = full
    s.tlag["R328_775"] = m_775                                                        # 9671
    return {"in": in_d001, "pic": pic202b_op, "786": m_786_d001, "tic": tic002_op,
            "Q": Q_e004, "gen": gen786, "T737": T_737, "h2o": h2o, "reflux_sp": tic8008_op,
            "775": m_775, "lvl": lvl_d001_328, "lic": lic501_op, "776": m_776, "lost": lost,
            "over": over, "q_net": P_d001, "relief": relief, "lifted": s.sv_32353_lifted,
            # main.py 10815-10846, the telemetry (unrounded).
            "TT_329007": min(g["R328_E004_CW_T_IN_C"]
                             + (g["R328_E004_CW_T_OUT_DES_C"] - g["R328_E004_CW_T_IN_C"])
                             * (g["R328_E004_TV_OP_DES"] / max(s.TIC_328002["op"], 1.0)),
                             g["R328_E004_CW_T_MAX_C"]),
            "LI_328501": (_li_taps(s.a328_d001_M) if "B-53" in decided
                          else s.a328_d001_M / g["R328_D001_M_DES"] * g["R328_D001_LVL_SP"])}


LOOPS = (("PIC_328202", "pic_328202"), ("TIC_328002", "tic_328002"),
         ("TIC_328008", "tic_328008"), ("FIC_328404", "fic_328404"),
         ("LIC_328501", "lic_328501"))


def _loop(loops, name):
    loop = getattr(loops, name)
    return loop.loop if isinstance(loop, rd.FlowLoop) else loop


def _assert_tick(a: dict, b: rd.RefluxDrumResult, s, drum, loops, label):
    assert (a["in"], a["pic"], a["786"], a["tic"], a["Q"], a["gen"], a["TT_329007"]) == (
        b.in_kgh, b.pic_op_pct, b.m_786_kgh, b.tic_op_pct, b.q_e004_kw, b.gen_kgh,
        b.t_cw_return_c), label
    assert (a["T737"], a["h2o"], a["reflux_sp"], a["775"], a["lvl"], a["lic"], a["776"],
            a["lost"], a["over"], a["q_net"]) == (
        b.t_737_c, b.h2o_737_molpct, b.reflux_sp_kgh, b.m_775_kgh, b.lic_pv_pct, b.lic_op_pct,
        b.m_776_kgh, b.suction_lost, b.m_overflow_kgh, b.q_net_kw), label
    assert (a["relief"], a["lifted"]) == (b.m_relief_kgh, b.relief_lifted), label
    assert (s.a328_d001_P, s.a328_d001_T, s.a328_d001_T_prev, s.a328_d001_M) == (
        drum.p_bara, drum.t_c, drum.t_prev_c, drum.m_kg), label
    assert (b.p_bara, b.t_c, b.m_kg, b.level_pct) == (
        drum.p_bara, drum.t_c, drum.m_kg, a["LI_328501"]), label
    assert (s.tlag["R328_775"], s.tlag["R328_775_TOP"], s.tlag["F_328404"], s.cap_775) == (
        drum.m_775_prev_kgh, drum.lag_state[rd.TOP_LAG_KEY], loops.fic_328404.measurement,
        drum.cap_775_kgh), label
    for v1_name, name in LOOPS:
        v1c, loop = getattr(s, v1_name), _loop(loops, name)
        assert (v1c["op"], v1c["sp"], v1c["pv"], v1c["pv1"], v1c["pv2"], v1c["mode"]) == (
            loop.op, loop.sp, loop.pv, loop.pv1, loop.pv2, loop.mode), (label, v1_name)


# --------------------------------------------------------------------------------------
# The design basis
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("ours, theirs", [
    ("D001_M737_DES_KGH", "R328_D001_M737_DES"), ("D001_M718A_DES_KGH", "R328_D001_M718A_DES"),
    ("D001_IN_DES_KGH", "R328_D001_IN_DES"), ("D001_M786_DES_KGH", "R328_D001_M786_DES"),
    ("D001_M775_DES_KGH", "R328_C002_M775_DES"), ("S775_VOL_DES_M3H", "S775_VOL_DES"),
    ("D001_M776_DES_KGH", "R328_D001_M776_DES"), ("D001_M774_DES_KGH", "R328_D001_M774_DES"),
    ("D001_RHO_KGM3", "R328_D001_M776_RHO"), ("RHO_775_KGM3", "RHO_775_KGM3"),
    ("D001_T718A_C", "R328_D001_T718A"), ("D001_ID_M", "R328_D001_ID_M"),
    ("D001_TT_M", "R328_D001_TT_M"), ("D001_VOL_CYL_M3", "R328_D001_VOL_M3"),
    ("D001_LEVEL_DES_PCT", "R328_D001_LVL_SP"), ("D001_AREA_M2", "R328_D001_AREA_M2"),
    ("W786_DES", "R328_D001_W786_DES"), ("MW786_DES", "R328_D001_MW786_DES"),
    ("PV202_P2_BARA", "R3232_E011_P_BARA"), ("PV202_OP_DES_PCT_V1", "R328_D001_PV_OP_DES"),
    ("LV501_OP_DES_PCT_V1", "R328_D001_LV_OP_DES"),
    ("FV404_OP_DES_PCT_V1", "R328_D001_FIC404_OP_DES"), ("E004_Q_DES_KW", "R328_E004_Q_DES_KW"),
    ("E004_TV_OP_DES_PCT", "R328_E004_TV_OP_DES"), ("E004_CW_T_IN_C", "R328_E004_CW_T_IN_C"),
    ("E004_CW_T_OUT_DES_C", "R328_E004_CW_T_OUT_DES_C"),
    ("E004_CW_T_MAX_C", "R328_E004_CW_T_MAX_C"), ("D001_SENS_DES_KW", "R328_D001_SENS"),
    ("D001_LAM737_KJKG", "R328_D001_LAM737"),
    ("C002_OFFGAS_H2O_PFD_MOLPCT", "R328_D001_OFFGAS_H2O_PFD"),
    ("C002_OFFGAS_PHI", "R328_D001_OFFGAS_PHI"),
    ("C002_OFFGAS_H2O_DES_MOLPCT", "R328_D001_OFFGAS_H2O_DES"),
])
def test_design_basis(v1, ours, theirs):
    assert getattr(d, ours) == v1[theirs]


def test_the_decided_valves_and_gains(v1):
    """The three vendor strokes re-derived from the catalogue, and the two gains written from the
    table and the loop summary's spans; V1 strokes the valves from 50, 50 and 30.2 %."""
    assert (d.LV501_OP_DES_PCT, d.FV404_OP_DES_PCT, d.PV202_OP_DES_PCT, d.PV202_XT) == (
        DECIDED_LV501_OP, DECIDED_FV404_OP, DECIDED_PV202_OP, DECIDED_PV202_XT)
    assert (d.LV501_OP_DES_PCT, d.FV404_OP_DES_PCT, d.PV202_OP_DES_PCT) == (
        pytest.approx(29.385, abs=1e-3), pytest.approx(56.679, abs=1e-3),
        pytest.approx(60.359, abs=1e-3))
    assert (d.LV501_CHAR, d.FV404_CHAR, d.PV202_CHAR) == ("linear", dv.MOD_EQUAL_PCT,
                                                          dv.MOD_EQUAL_PCT)
    assert (d.PIC_328202_KC, d.TIC_328002_KC) == (DECIDED_PIC202_KC, DECIDED_TIC002_KC) == (
        25.0, 1.875)
    assert d.C002_DT_TOP_NO_REFLUX_K + 12.0 == c2.C002_DT_TOP_K == v1["R328_C002_DT_TOP"]


def test_the_vessel_and_its_level_as_decided(v1):
    """B-53: the drawing's 5500 l against V1's cylinder of 4.343 m3 — each head 0.578 m3 — and the
    design holdup that reads 50.5 % between the taps, 3029.7 kg against V1's 2401.7; the drawing's
    normal level, 850 mm, reads 41.7 %; the full vessel 6022.5 kg against V1's 4755.8."""
    assert (d.D001_VOL_M3, d.D001_HEAD_VOL_M3) == (DECIDED_VOL_M3,
                                                  pytest.approx(DECIDED_HEAD_M3, rel=1e-12))
    assert d.D001_VOL_CYL_M3 == v1["R328_D001_VOL_M3"] and d.D001_HEAD_VOL_M3 == pytest.approx(
        0.5784, abs=1e-4)
    assert rd.lt_328501_pct(rd.D001_M_SEED_KG) == 50.5 == _li_taps(rd.D001_M_SEED_KG)
    assert rd.D001_M_SEED_KG == pytest.approx(d.D001_M_DES_KG, abs=1e-9)
    assert (rd.D001_M_SEED_KG, v1["R328_D001_M_DES"]) == (pytest.approx(3029.66, abs=0.01),
                                                          pytest.approx(2401.67, abs=0.01))
    nll = (d.D001_HEAD_VOL_M3 + 0.850 * d.D001_AREA_M2) * d.D001_RHO_KGM3
    assert rd.lt_328501_pct(nll) == pytest.approx(41.722, abs=1e-3)
    assert (d.D001_FULL_KG, v1["R328_D001_M_FULL"]) == (6022.5, pytest.approx(4755.79, abs=0.01))
    for m in (0.0, 500.0, d.D001_FULL_KG):
        assert rd.lt_328501_pct(m) == _li_taps(m)
    assert (rd.lt_328501_pct(500.0), rd.lt_328501_pct(d.D001_FULL_KG)) == (0.0, 100.0)


def test_the_state_and_the_controllers_are_seeded_as_v1_seeds_them(v1):
    s, (drum, loops) = _v1_state(v1), _drum_and_loops()
    assert (s.a328_d001_M, s.a328_d001_T, s.a328_d001_T_prev, s.a328_d001_P) == (
        drum.m_kg, drum.t_c, drum.t_prev_c, drum.p_bara)
    for v1_name, name in LOOPS:
        v1c, loop = getattr(s, v1_name), _loop(loops, name)
        assert (v1c["mode"], v1c["op"], v1c["sp"], v1c["pv"], v1c["pv1"], v1c["pv2"], v1c["Kc"],
                v1c["Ti"], v1c["Td"], v1c["act"], v1c["op_lo"], v1c["op_hi"], v1c["sp_lo"],
                v1c["sp_hi"]) == (loop.mode, loop.op, loop.sp, loop.pv, loop.pv1, loop.pv2,
                                  loop.Kc, loop.Ti, loop.Td, loop.act, loop.op_lo, loop.op_hi,
                                  loop.sp_lo, loop.sp_hi), v1_name
    fic = loops.fic_328404
    assert (fic.design_flow, fic.op_des, fic.rho_kgm3, fic.tau_s) == (
        1675.0, DECIDED_FV404_OP, 1095.0, 5.0)


# --------------------------------------------------------------------------------------
# The drum on its own, tick by tick
# --------------------------------------------------------------------------------------

def _design(**over):
    """A tick's boundaries: 328C002 after its step, 718A, and the tank's 793 and compartment II."""
    base = {"m737": t.C002_M737_DES_KGH, "tc002": t.C002_T_BOT_C, "pc002": t.C002_P_TOP_BARA,
            "mc002": c2.C002_M_DES_KG, "inc002": t.C002_IN_DES_KGH, "mover": 0.0,
            "m718a": d.D001_M718A_DES_KGH, "m793": 0.0, "t793": 56.0, "pe011": d.PV202_P2_BARA}
    base.update(over)
    return base


def _feed(s, x):
    """Write a tick's boundaries into V1's tears and neighbouring states."""
    s.a328_c002_T, s.a328_c002_P, s.a328_c002_M = x["tc002"], x["pc002"], x["mc002"]
    s.tlag["R3232_718A"] = x["m718a"]
    s.a328_d003_TII, s.r3232_e011_P = x["t793"], x["pe011"]


def _port(drum, loops, x, dt):
    return drum.step(loops, x["m737"], x["tc002"], x["pc002"], x["mc002"], x["inc002"],
                     x["mover"], x["m718a"], x["m793"], x["t793"], x["pe011"], dt)


def _run(v1, script, ticks: int, dt: float = DT, before=None, decided=ALL):
    """Drive the drum alone through `script(k)`, comparing everything every tick."""
    if not {"valve", "gains", "B-53"} <= decided:
        raise ValueError("the port's seeds are the decided ones; run V1's in the divergences")
    s, (drum, loops) = _v1_state(v1, decided), _drum_and_loops()
    if before:
        before(s, drum, loops)
    b = None
    for k in range(ticks):
        x = script(k)
        _feed(s, x)
        a = _v1_d001(v1, s, x["m737"], x["inc002"], x["m793"], dt, decided, x["mover"])
        b = _port(drum, loops, x, dt)
        _assert_tick(a, b, s, drum, loops, f"tick {k}")
    return s, drum, loops, b


def _step(t0: int, **over):
    return lambda k: _design(**(over if k >= t0 else {}))


def _manual(v1_name, name, op):
    def before(s, drum, loops):
        getattr(s, v1_name).update(mode="MAN", op=op)
        loop = _loop(loops, name)
        loop.set_mode("MAN")
        loop.op = op
    return before


def _set_point(v1_name, name, sp):
    def before(s, drum, loops):
        getattr(s, v1_name)["sp"] = sp
        _loop(loops, name).sp = sp
    return before


SCENARIOS = {
    "design hold": (lambda k: _design(), 600, DT, None),
    "737 cut a fifth": (_step(10, m737=0.8 * t.C002_M737_DES_KGH), 1200, 0.5, None),
    "737 up a fifth": (_step(10, m737=1.2 * t.C002_M737_DES_KGH), 1200, 0.5, None),
    "328C002 0.3 bar higher": (_step(10, pc002=t.C002_P_TOP_BARA + 0.3), 1200, 0.5, None),
    "328C002 3 K hotter": (_step(10, tc002=t.C002_T_BOT_C + 3.0), 1200, 0.5, None),
    "718A cut by half": (_step(10, m718a=0.5 * d.D001_M718A_DES_KGH), 1200, 0.5, None),
    "793 opened, 1534 kg/h at 56 C": (_step(10, m793=1534.0), 1200, 0.5, None),
    "TIC-328002 to 55 C": (lambda k: _design(), 1200, 0.5,
                           _set_point("TIC_328002", "tic_328002", 55.0)),
    "TV-328002 in MAN at 30 %": (lambda k: _design(), 1200, 0.5,
                                 _manual("TIC_328002", "tic_328002", 30.0)),
    "TIC-328008 to 50 mol%": (lambda k: _design(), 1200, 0.5,
                              _set_point("TIC_328008", "tic_328008", 50.0)),
    "PV-328202 in MAN at 80 %": (lambda k: _design(), 1200, 0.5,
                                 _manual("PIC_328202", "pic_328202", 80.0)),
    "LV-328501 wide open: the heel": (lambda k: _design(), 1200, 0.5,
                                      _manual("LIC_328501", "lic_328501", 100.0)),
    "LV-328501 shut: the drum fills": (lambda k: _design(), 1200, 0.5,
                                       _manual("LIC_328501", "lic_328501", 0.0)),
}


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_the_drum_tick_by_tick(v1, name):
    script, ticks, dt, before = SCENARIOS[name]
    _run(v1, script, ticks, dt, before)


#: The scenarios where neither limit binds, run on V1's lines for both.
INERT = [n for n in SCENARIOS if "heel" not in n and "fills" not in n]


@pytest.mark.parametrize("name", INERT)
def test_the_limits_are_inert_where_they_do_not_act(v1, name):
    script, ticks, dt, before = SCENARIOS[name]
    s, drum, loops, b = _run(v1, script, ticks, dt, before, decided=ON_BOOKS)
    assert not b.suction_lost and b.m_overflow_kgh == 0.0


# --------------------------------------------------------------------------------------
# The flowsheet: 737 same-tick from 328C002; the drum's pressure and 775 back as tears
# --------------------------------------------------------------------------------------

def test_737_is_same_tick_and_775_and_the_pressure_the_tears():
    fs = Flowsheet()
    for tag in ("328C002", "328D001", "323E011", "323E003"):
        fs.add_unit(Unit(tag, tag, tag[:3]))
    fs.connect(Connection("737", "328C002", "328D001"))
    fs.connect(Connection("775", "328D001", "328C002"))
    fs.connect(Connection("786", "328D001", "323E011"))
    fs.connect(Connection("776", "328D001", "323E003"))
    with pytest.raises(CyclicFlowsheetError):
        fs.evaluation_order()
    fs.tear(Tear("R328_775", "328D001", ("328C002",), "V1 steps the column first; a tick late"))
    assert fs.evaluation_order() == ("328C002", "328D001", "323E011", "323E003")


def test_the_drum_takes_737_on_the_same_tick(v1):
    """V1's 328C002 and 328D001 in V1's order against the ported column and drum: the drum takes
    this tick's 737 and the column's state after its step; the column takes 775 and the drum's
    pressure a tick late. A feed cut and then a reflux set-point step move every hand-off."""
    s = _v1_state(v1)
    col2, lic2 = fd.FirstDesorber(l2_stop=False), fd.lic_328503()
    drum, loops = _drum_and_loops()
    seen = set()
    for k in range(3000):
        m738 = t.C002_M738_DES_KGH * (0.85 if k >= 10 else 1.0)
        if k == 1500:
            s.TIC_328008["sp"] = loops.tic_328008.sp = 48.0
        x2 = c002_eq._design(m738=m738, m775=s.tlag.get("R328_775", t.C002_M775_DES_KGH),
                             pd001=s.a328_d001_P)
        c002_eq._feed(s, x2)
        a2 = c002_eq._v1_c002(v1, s, x2["m738"], x2["t738"], DT)
        b2 = col2.step(lic2, x2["m738"], x2["t738"], x2["m748"], dict(x2["y748"]), x2["m750"],
                       dict(x2["y750"]), drum.m_775_prev_kgh, x2["pc003"], drum.p_bara, DT)
        c002_eq._assert_tick(a2, b2, s, col2, lic2, f"328C002, tick {k}")
        s.tlag["R3232_718A"], s.a328_d003_TII = d.D001_M718A_DES_KGH, 56.0
        a = _v1_d001(v1, s, a2["737"], a2["in"], 0.0, DT, m_over=a2["over"])
        b = drum.step(loops, b2.m_737_kgh, b2.t_c, b2.p_bara, b2.m_kg, b2.in_kgh,
                      b2.m_overflow_kgh, d.D001_M718A_DES_KGH, 0.0, 56.0, d.PV202_P2_BARA, DT)
        _assert_tick(a, b, s, drum, loops, f"328D001, tick {k}")
        seen.add(b.m_775_kgh)
    assert len(seen) > 100


# --------------------------------------------------------------------------------------
# The departures, both sides
# --------------------------------------------------------------------------------------

def _both(v1, script, ticks, dt, before, v1_decided, port=None):
    """V1 with `v1_decided` against the port — `port`'s drum and loops, or `_drum_and_loops` —:
    the tick they part, the tick each of the port's flags first rises, each side's liquid books on
    what reaches the liquid, and both sides at the end."""
    s = _v1_state(v1, v1_decided)
    drum, loops = port or _drum_and_loops()
    if before:
        before(s, drum, loops)
    out = SimpleNamespace(parted=None, first={}, made_v1=0.0, made=0.0, s=s, drum=drum, a=None,
                          b=None, loops=loops)
    for k in range(ticks):
        x = script(k)
        _feed(s, x)
        v1_pre, pre = s.a328_d001_M, drum.m_kg
        a = _v1_d001(v1, s, x["m737"], x["inc002"], x["m793"], dt, v1_decided, x["mover"])
        b = _port(drum, loops, x, dt)
        out.made_v1 += s.a328_d001_M - v1_pre - (a["in"] - a["gen"] - a["775"] - a["776"]
                                                 - a["over"]) * dt / 3600.0
        out.made += drum.m_kg - pre - (b.in_kgh - b.gen_kgh - b.m_775_kgh - b.m_776_kgh
                                       - b.m_overflow_kgh) * dt / 3600.0
        if out.parted is None:
            try:
                _assert_tick(a, b, s, drum, loops, f"tick {k}")
            except AssertionError:
                out.parted = k
        for key, flag in (("lost", b.suction_lost), ("over", b.m_overflow_kgh > 0.0)):
            if flag:
                out.first.setdefault(key, k)
        out.a, out.b = a, b
    return out
