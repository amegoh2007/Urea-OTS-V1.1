"""V1 <-> V1.1 equivalence for 322C001, the LP absorber.

What is being proved
--------------------
V1 writes the absorber inline in `step_sim`, so its statements are TRANSCRIBED into `_v1_c001`
below, line for line, and declared as such: the aqueous cp (``main.py`` 8834) and the stage
itself (9405-9511). Everything they call is V1's own code, executed: ``packed_absorber`` and
``hydraulics`` loaded as real modules; ``_ctrl_ipd``, ``_lag1``, ``aqueous_cp``, ``des_advance``
and ``c001_offgas_heat_kw`` lifted out of ``main.py``. The boot pin that fixes the beds'
calibration, the design vent and the heat residual (12333-12353) is transcribed in the fixture,
on the gas the port pins on: 322E003's design vent through HV-322604 at its design opening, the
chain whose every field the purge valve's harness proves `==` V1's. The state is seeded as
``State.__init__`` seeds it (6869-6875, 7129-7148). V1's pre-pin branch, which runs only through
its boot settles, is not reachable at runtime and is not ported.

The departures
--------------
Nine, each a switch in the transcription: ``decided`` names the ones whose port lines stand in
V1's. Four were decided by the process engineer on 2026-10-01:

  * "relief" — SV32253 vents the column's gas between its 6.013 bar a certified set pressure and
    its 5.513 reseat, on its orifice M at the assumed gas coefficient 0.917 (handoffs B-47,
    A-16), the law written out in `decided_relief`; V1 sets it at 31.013 bar a and ramps it
    linearly to 60 t/h over 10 % accumulation.
  * "B-54" — 755 arrives at 322E006's outlet temperature, an argument; V1 holds 40 C.
  * "B-55" — XV-322915's 500 kW leave the liquor's balance for the vent line, which takes the
    valve's rated steam (B-60), and TI-322015 reads the line (the port's `vent_line`, which has no
    V1 counterpart: called here as the port's lines); V1 adds them to the liquor.
  * "B-19" — the carbamate liquor HV-322604's purge condenses in its line joins the sump, its
    mass, species and sensible heat; V1's purge is all gas.

The other five are classes decided on other units, applied under §5 rule 7:

  * "B-53" — the name plate's 3.60 m3, and LI-322502 between LT-322502's taps, the design
    holdup what reads 50 % on them (decision 33); V1 takes the cylinders' 3.27 m3 and reads
    M / M_des x 50 on half the lower cylinder;
  * "heel" — LV-322502 draws only the liquor above a 1 kg heel plus what arrives (decision 11);
  * "overflow" — a full column's excess leaves as a stream (decision 11);
  * "valve" — PV-322201 and LV-322502 on their vendor trims from the strokes their Kvs give
    (decision 23), V1 linear from 67.8 % and 50 %;
  * "gains" — PIC-322201 on PT-322201's 0-28 bar g span, 21.43 %/bar (decision 10), V1 6.0.

Every scenario runs the port against the switched transcription with ``==`` on every tick; each
departure runs both ways in `test_lp_absorber_decided_equivalence.py`.
"""

from __future__ import annotations

import math

import pytest

from ureasim.data import control_valves as cvd
from ureasim.data import unit_322c001 as c
from ureasim.data import unit_322e003 as sc
from ureasim.units.absorption import lp_absorber as la
from ureasim.units.absorption import packed_beds as pb
from ureasim.units.absorption import vent_line as vl
from ureasim.units.synthesis import purge_valve as pv
from tests.equivalence import decided_relief as dr
from tests.equivalence import decided_valves as dv
from tests.equivalence.v1_loader import lift, load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

C001_NAMES = [
    "A328_M755_DES", "A328_M755_RHO", "A328_M756_DES", "A328_CPL_DES", "A328_CPL_T",
    "A328_ABS_DES", "A328_C001_T", "A328_M755_T", "A328_C001_P_BARA", "A328_C001_ID_UP_M",
    "A328_C001_SHELL_UP_M", "A328_C001_ID_LO_M", "A328_C001_SHELL_LO_M", "A328_C001_VOL_UP_M3",
    "A328_C001_VOL_LO_M3", "A328_C001_VOL_M3", "A328_C001_RHO_L", "A328_C001_MW_VENT_DES",
    "A328_PIC_OP_DES", "A328_C001_SV_SET_BARA", "A328_C001_SV_ACCUM_BAR", "A328_C001_SV_CAP_KGH",
    "A328_LIC_OP_DES", "A328_C001_LVL_SP_PCT", "A328_C001_M_DES", "A328_QFLOOD_KW", "A328_CP",
    "W_S755", "W_CPL", "W_C001_DES", "A328_ABS_CO2_DES", "A328_ABS_H2O_DES", "A328_ABS_NH3_DES",
    "A328_C001_ALPHA", "MW_COMP", "c001_offgas_heat_kw", "aqueous_cp", "des_advance",
    "_ctrl_ipd", "_lag1",
]

DT = 0.1

ALL = frozenset({"relief", "B-53", "heel", "overflow", "valve", "gains", "B-54", "B-55", "B-19"})
V1_VERBATIM = frozenset()

#: SV32253 as decided (A-16), written from its sheets: set 5.0 bar g on 1.013 bar a (Uhde
#: UD-RL-322-EC-0003), reseating 10 % of set below on gas; orifice M, 2827.43 mm2 (Sempell
#: UD-RL-G00-DZ-0002-001 page 2), at the series' gas coefficient 0.917 (page 3).
SV32253 = dr.Valve.orifice(5.0 + 1.013, 5.0 + 1.013 - 0.1 * 5.0, 2827.43 * 1.0e-6, 0.917)

#: The two valves as decided, re-derived from the vendor catalogue: design strokes [%].
DECIDED_PV201_OP = dv.design_stroke_pct(cvd.PV_322201, c.C001_VENT_DES_KGH)
DECIDED_LV502_OP = dv.design_stroke_pct(cvd.LV_322502, 33358.0)
#: PIC-322201 as decided, written from its sources: the table's 6.00 on PT-322201's 28 bar.
DECIDED_PIC201_KC = 6.00 * 100.0 / 28.0
#: The vessel as decided (decision 33), written from the drawing: the name plate's 3.60 m3; the
#: bottom head DIN 28013 on 950 mm outside (crown R 760, knuckle 0.154 Da, inside radii), 922 mm
#: inside; LT-322502's taps 200 mm above the bottom tangent and 800 mm apart.
DECIDED_VOL_M3 = 3.60
DECIDED_AREA_M2 = math.pi * 0.25 * 0.922 ** 2


def _head_m3() -> float:
    """The DIN 28013 bottom head's volume below its tangent line, by integrating its profile —
    the port's closed form checked numerically."""
    a, r_c, r_k = 0.461, 0.8 * 0.950, 0.154 * 0.950
    cc = a - r_k
    z_c = math.sqrt((r_c - r_k) ** 2 - cc ** 2)
    h, z_j = r_c - z_c, -r_k * z_c / (r_c - r_k)
    n, v = 20000, 0.0
    for i in range(n):
        z = -h + (i + 0.5) * h / n
        rho = math.sqrt(r_c ** 2 - (z - z_c) ** 2) if z < z_j else cc + math.sqrt(r_k ** 2 - z * z)
        v += math.pi * rho * rho * h / n
    return v


def _li_taps(m_kg: float) -> float:
    """LI-322502 between LT-322502's taps (decision 33), written from the drawing."""
    m_lo = (c.C001_HEAD_VOL_M3 + 0.200 * DECIDED_AREA_M2) * 1005.0
    m_span = 0.800 * DECIDED_AREA_M2 * 1005.0
    return min(max((m_kg - m_lo) / m_span, 0.0), 1.0) * 100.0


@pytest.fixture(scope="module")
def v1():
    pa, hy = load("packed_absorber"), load("hydraulics")
    seed = {"math": math, "packed_absorber": pa, "hydraulics": hy,
            "h0_enthalpy": load("gap_g6_h0_enthalpy"), "iapws_if97": load("iapws_if97")}
    ns = lift(C001_NAMES, seed=seed)
    ns.update(packed_absorber=pa, hydraulics=hy)
    # ---- the boot pin, main.py 12333-12353, TRANSCRIBED, on the port's design gas ----
    r = pv.purge_valve_322604(sc.OFFGAS_DES_KMOLH, sc.OFFGAS_T_DES_C, sc.HIC604_DES_PCT,
                              sc.OVERFLOW_P_DES_BARA)
    caphv = {"m": r.mass_kgh, "T": r.t_out_c,
             "comp": {k: v for k, v in r.comp_kmolh.items() if v > 0.0}}
    g, mw = ns, ns["MW_COMP"]
    sens_pin = ((g["A328_M755_DES"] * (g["A328_M755_T"] - g["A328_C001_T"])
                 + g["A328_CPL_DES"] * (g["A328_CPL_T"] - g["A328_C001_T"])) / 3600.0
                * g["A328_CP"])
    args = (caphv["comp"], g["A328_C001_T"], g["A328_CPL_T"], g["A328_C001_P_BARA"],
            g["A328_M755_DES"], g["W_S755"], g["A328_CPL_DES"], g["W_C001_DES"])
    cal = pa.calibrate(*args, {"NH3": g["A328_ABS_NH3_DES"] / mw["NH3"],
                               "CO2": g["A328_ABS_CO2_DES"] / mw["CO2"],
                               "H2O": g["A328_ABS_H2O_DES"] / mw["H2O"]})
    ab_pin = pa.solve(*args, cal, abs_up=cal["abs_up"])
    ns["A328_GCB_DES"], ns["A328_GCB_T"] = caphv["m"], caphv["T"]
    ns["A328_C001_CAL"] = cal
    ns["A328_VENT_DES"] = caphv["m"] - g["A328_ABS_DES"]
    ns["A328_C001_Q_RES_KW"] = -(sens_pin + g["c001_offgas_heat_kw"](
        caphv["comp"], caphv["T"], g["A328_C001_T"], ab_pin["absorbed_kmolh"], g["W_C001_DES"]))
    ns["HV604_DES"] = caphv
    return ns


def _v1_state(v1, decided=ALL):
    """The V1 plant-state fields 322C001 reads and writes, seeded as `State.__init__` seeds them
    (``main.py`` 6869-6875, 7129-7148); "B-53", "valve" and "gains" in `decided` seed the port's
    holdup, strokes and gain."""
    g = v1
    s = type("S", (), {})()
    s.a328_c001_M = g["A328_C001_M_DES"]
    s.a328_c001_T_prev = s.a328_c001_T = g["A328_C001_T"]
    s.a328_c001_P = g["A328_C001_P_BARA"]
    s.a328_c001_w = dict(g["W_C001_DES"])
    s.cpl_flow_kgh = g["A328_CPL_DES"]
    p, lvl = g["A328_C001_P_BARA"], 50.0
    s.PIC_322201 = {"mode": "AUTO", "op": g["A328_PIC_OP_DES"], "sp": p, "pv": p, "pv1": p,
                    "pv2": p, "Kc": 6.0, "Ti": 30.0, "Td": 0.0, "act": -1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 2.5, "sp_hi": 5.5}
    s.LIC_322502 = {"mode": "AUTO", "op": g["A328_LIC_OP_DES"], "sp": lvl, "pv": lvl,
                    "pv1": lvl, "pv2": lvl, "Kc": 1.0, "Ti": 100.0, "Td": 0.0, "act": -1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0, "sp_hi": 100.0}
    s.XV_322915 = False
    s.tlag, s.flags = {}, {}
    s.sv_32253_lifted = False
    if "B-53" in decided:
        s.a328_c001_M = la.C001_M_SEED_KG
    if "valve" in decided:
        s.PIC_322201["op"] = DECIDED_PV201_OP
        s.LIC_322502["op"] = DECIDED_LV502_OP
    if "gains" in decided:
        s.PIC_322201["Kc"] = DECIDED_PIC201_KC
    return s


def _v1_c001(v1, s, hv604, m_755, dt, decided=ALL, t_755=40.0):
    """V1 `main.py` 8834 and 9405-9511, stage 7, TRANSCRIBED line for line (V1's post-pin
    branch); each departure in `decided` puts the port's lines in V1's. ``hv604`` is HV-322604's
    diagnostics {comp_kmolh, mass_kgh, T_out} and, decided, its condensed ``liquor``; ``m_755``
    is 744 this tick and ``t_755`` 322E006's outlet."""
    g = v1
    m755_t = t_755 if "B-54" in decided else g["A328_M755_T"]
    liq_i = {k: max((hv604.get("liquor") or {}).get(k, 0.0), 0.0) * g["MW_COMP"][k]
             for k in g["MW_COMP"]} if "B-19" in decided else {}
    m_liq = sum(liq_i.values())
    hydraulics, packed_absorber, MW_COMP = g["hydraulics"], g["packed_absorber"], g["MW_COMP"]
    cp_322c001 = g["aqueous_cp"](g["A328_CP"], g["A328_C001_T"], s.a328_c001_T)       # 8834
    Tc001 = s.a328_c001_T
    gcb_m = hv604["mass_kgh"]
    gcb_T = hv604["T_out"]
    pic201_op = g["_ctrl_ipd"](s.PIC_322201, s.a328_c001_P, dt)
    lvl_c001 = s.a328_c001_M / g["A328_C001_M_DES"] * 50.0
    if "B-53" in decided:  # ---- LI-322502 between LT-322502's taps (the port's line) ----
        lvl_c001 = _li_taps(s.a328_c001_M)
    lic502c_op = g["_ctrl_ipd"](s.LIC_322502, lvl_c001, dt)
    if "valve" in decided:  # ---- LV-322502 on its vendor trim (the port's line) ----
        m_756 = g["A328_M756_DES"] * (dv.trim(lic502c_op / 100.0)
                                      / dv.trim(DECIDED_LV502_OP / 100.0))
    else:
        m_756 = g["A328_M756_DES"] * (lic502c_op / g["A328_LIC_OP_DES"])
    Q_flood = g["A328_QFLOOD_KW"] if s.XV_322915 else 0.0
    if "B-55" in decided:  # ---- the flood in the vent line, not the liquor (the port's) ----
        Q_flood = 0.0
    _cal_up = g["A328_C001_CAL"]["abs_up"]
    _up_in = {"NH3": s.tlag.get("C001_UP_NH3", _cal_up["NH3"]),
              "CO2": s.tlag.get("C001_UP_CO2", _cal_up["CO2"]),
              "dT": s.tlag.get("C001_UP_DT", _cal_up["dT"])}
    ab_c001 = packed_absorber.solve(
        {k: max(v, 0.0) for k, v in hv604["comp_kmolh"].items()}, s.a328_c001_T, g["A328_CPL_T"],
        s.a328_c001_P, m_755, g["W_S755"], s.cpl_flow_kgh, s.a328_c001_w, g["A328_C001_CAL"],
        abs_up=_up_in)
    _tau_up = packed_absorber.liquid_residence_s(packed_absorber.BED_UP, s.cpl_flow_kgh,
                                                 g["A328_CPL_T"] + 273.15)
    for _sp, _key in (("NH3", "C001_UP_NH3"), ("CO2", "C001_UP_CO2"), ("dT", "C001_UP_DT")):
        g["_lag1"](s.tlag, _key, ab_c001["abs_up"][_sp], _tau_up, dt)
    abs_nh3 = ab_c001["absorbed_kmolh"].get("NH3", 0.0) * MW_COMP["NH3"]
    abs_co2 = ab_c001["absorbed_kmolh"].get("CO2", 0.0) * MW_COMP["CO2"]
    abs_h2o = ab_c001["absorbed_kmolh"].get("H2O", 0.0) * MW_COMP["H2O"]
    abs_c001 = abs_nh3 + abs_co2 + abs_h2o
    vent_full = g["A328_VENT_DES"] * (100.0 / g["A328_PIC_OP_DES"])
    if "valve" in decided:  # ---- PV-322201 on its vendor trim (the port's lines) ----
        _phi = dv.trim(DECIDED_PV201_OP / 100.0)
        vent_c001 = g["A328_VENT_DES"] * (dv.trim(pic201_op / 100.0) / _phi)
        vent_full = g["A328_VENT_DES"] * (dv.trim(1.0) / _phi)
    else:
        vent_c001 = g["A328_VENT_DES"] * (pic201_op / g["A328_PIC_OP_DES"])
    m_sv253 = 0.0
    if "relief" not in decided:  # ---- V1's SV-32253: linear over 10 % accumulation ----
        sv253_over = max(s.a328_c001_P - g["A328_C001_SV_SET_BARA"], 0.0)
        m_sv253 = g["A328_C001_SV_CAP_KGH"] * min(sv253_over / g["A328_C001_SV_ACCUM_BAR"], 1.0)
        vent_c001 += m_sv253
    s.flags["LP_ABSORBER_OVERLOAD"] = (gcb_m - abs_c001) > vent_full
    gcb_i = {k: hv604["comp_kmolh"].get(k, 0.0) * MW_COMP[k] for k in MW_COMP}
    vent_i = dict(gcb_i)
    vent_i["CO2"] -= abs_co2
    vent_i["NH3"] -= abs_nh3
    vent_i["H2O"] -= abs_h2o
    _vt = sum(v for v in vent_i.values() if v > 0.0)
    y_vent = {k: max(vent_i[k], 0.0) / _vt for k in MW_COMP} if _vt > 1e-9 else None
    _n_vent = sum(max(vent_i.get(k, 0.0), 0.0) / MW_COMP[k] for k in MW_COMP)
    _mw_vent = ((_vt / _n_vent) if (_vt > 1e-9 and _n_vent > 1e-12)
                else g["A328_C001_MW_VENT_DES"])
    # V1 has no full column; without the decided vessel the overflow fills V1's cylinders.
    vol, lost, over = g["A328_C001_VOL_M3"], False, 0.0
    full = g["A328_C001_VOL_M3"] * g["A328_C001_RHO_L"]
    if "B-53" in decided:  # ---- the name plate's volume (the port's) ----
        vol, full = DECIDED_VOL_M3, DECIDED_VOL_M3 * 1005.0
    m_in = m_755 + s.cpl_flow_kgh + abs_c001 + m_liq
    if "heel" in decided:  # ---- the decided heel (the port's lines) ----
        avail = max(max(s.a328_c001_M - 1.0, 0.0) / max(dt, 1e-9) * 3600.0 + m_in, 0.0)
        lost = m_756 > avail
        if lost:
            m_756 = avail
    if "overflow" in decided:  # ---- the decided overflow (the port's lines) ----
        m_new = max(s.a328_c001_M + (m_in - m_756) / 3600.0 * dt, 1.0)
        if m_new > full:
            over = (m_new - full) / max(dt, 1e-9) * 3600.0
    _vv_c001 = hydraulics.vapour_volume_m3(vol, s.a328_c001_M, g["A328_C001_RHO_L"])
    _T_c001_pre = s.a328_c001_T
    _p_free = s.a328_c001_P + hydraulics.vessel_dpdt(
        s.a328_c001_P, s.a328_c001_T + 273.15, _vv_c001, _mw_vent,
        (gcb_m - abs_c001) / _mw_vent, vent_c001 / _mw_vent,
        dtdt_k_s=(s.a328_c001_T - s.a328_c001_T_prev) / dt,
        dvvdt_m3_s=-((m_755 + s.cpl_flow_kgh + abs_c001 + m_liq - m_756 - over) / 3600.0)
        / g["A328_C001_RHO_L"]) * dt
    relief = 0.0
    if "relief" in decided:  # ---- B-47, A-16: SV32253 (the port's lines) ----
        relief, s.sv_32253_lifted = dr.vent(
            g, SV32253, s.a328_c001_P, _p_free, s.a328_c001_T + 273.15, _mw_vent, _vv_c001, dt,
            s.sv_32253_lifted)
        if relief > 0.0:
            _p_free += hydraulics.vessel_dpdt(s.a328_c001_P, s.a328_c001_T + 273.15, _vv_c001,
                                              _mw_vent, 0.0, relief / _mw_vent) * dt
    s.a328_c001_P = max(_p_free, 0.1)
    s.a328_c001_T_prev = _T_c001_pre
    sens_c001 = ((m_755 * (m755_t - Tc001) + s.cpl_flow_kgh * (g["A328_CPL_T"] - Tc001)
                  + m_liq * (gcb_T - Tc001)) / 3600.0 * cp_322c001)
    q_gas_c001 = g["c001_offgas_heat_kw"]({k: max(v, 0.0) for k, v in hv604["comp_kmolh"].items()},
                                          gcb_T, Tc001, ab_c001["absorbed_kmolh"], s.a328_c001_w)
    P_c001 = sens_c001 + q_gas_c001 + g["A328_C001_Q_RES_KW"] + Q_flood
    k_cap_322c001 = ((m_755 + s.cpl_flow_kgh + m_liq) * cp_322c001
                     + gcb_m * packed_absorber.CP_GAS) / 3600.0
    s.a328_c001_T = Tc001 + P_c001 * dt / max(s.a328_c001_M * cp_322c001 + k_cap_322c001 * dt,
                                              1e-6)
    s.a328_c001_M = max(s.a328_c001_M + (m_755 + s.cpl_flow_kgh + abs_c001 + m_liq - m_756)
                        / 3600.0 * dt, 1.0)
    if over:
        s.a328_c001_M = full
    w_abs = {"CO2": (abs_co2 / abs_c001 if abs_c001 > 1e-9 else 0.0),
             "NH3": (abs_nh3 / abs_c001 if abs_c001 > 1e-9 else 0.0),
             "H2O": (abs_h2o / abs_c001 if abs_c001 > 1e-9 else 0.0)}
    feeds = [(g["W_S755"], m_755), (g["W_CPL"], s.cpl_flow_kgh), (w_abs, abs_c001)]
    if m_liq > 1e-9:  # ---- B-19: the purge's condensate (the port's line) ----
        feeds.append(({k: v / m_liq for k, v in liq_i.items() if v > 0.0}, m_liq))
    s.a328_c001_w, _ = g["des_advance"](
        s.a328_c001_w, s.a328_c001_M, feeds, 0.0, g["A328_C001_ALPHA"], m_756 + over, 0.0, dt)
    vent = {}
    if "B-55" in decided:  # ---- the vent line and TI-322015 (the port's, no V1 counterpart) ----
        top = vl.column_top_c(la_beds(ab_c001), {k: max(v, 0.0) for k, v in
                                                 hv604["comp_kmolh"].items()},
                              s.cpl_flow_kgh, g["A328_CPL_T"], Tc001)
        line = vl.vent_line(vent_c001 - m_sv253, y_vent, top, s.XV_322915)
        vent = {"top": line.t_top_c, "steam": line.m_steam_kgh, "ti": line.t_ti_322015_c}
    return {"pic": pic201_op, "lvl": lvl_c001, "lic": lic502c_op, "756": m_756, "lost": lost,
            "abs": (abs_nh3, abs_co2, abs_h2o, abs_c001), "ab": ab_c001, "vent": vent_c001,
            "sv253": m_sv253, "y_vent": y_vent, "mw_vent": _mw_vent,
            "overload": s.flags["LP_ABSORBER_OVERLOAD"], "relief": relief,
            "lifted": s.sv_32253_lifted, "over": over, "sens": sens_c001, "q_gas": q_gas_c001,
            "flood": Q_flood, "q_net": P_c001, "liq": m_liq, "vent_line": vent,
            # main.py 10852, the level the operator reads.
            "LI": (_li_taps(s.a328_c001_M) if "B-53" in decided
                   else s.a328_c001_M / g["A328_C001_M_DES"] * 50.0)}


def la_beds(ab: dict) -> pb.BedsResult:
    """V1's beds' dictionary as the port's result, for the port's vent-line lines."""
    return pb.BedsResult(absorbed_kmolh=ab["absorbed_kmolh"], vent_kmolh=ab["vent_kmolh"],
                         ntu=ab["ntu"], y_star_lo=ab["y_star_lo"], dt_up_k=ab["dT_up"],
                         abs_up=ab["abs_up"])


def _assert_tick(a: dict, b: la.LpAbsorberResult, s, unit, loops, label):
    assert (a["pic"], a["lvl"], a["lic"], a["756"], a["lost"]) == (
        b.pic_op_pct, b.lic_pv_pct, b.lic_op_pct, b.m_756_kgh, b.drained), label
    assert a["abs"] == (b.m_abs_nh3_kgh, b.m_abs_co2_kgh, b.m_abs_h2o_kgh, b.m_abs_kgh), label
    ab = a["ab"]
    assert (ab["absorbed_kmolh"], ab["vent_kmolh"], ab["ntu"], ab["y_star_lo"], ab["dT_up"],
            ab["abs_up"]) == (b.beds.absorbed_kmolh, b.beds.vent_kmolh, b.beds.ntu,
                              b.beds.y_star_lo, b.beds.dt_up_k, b.beds.abs_up), label
    assert (a["vent"] - a["sv253"], a["y_vent"], a["mw_vent"], a["overload"]) == (
        b.m_vent_kgh, b.y_vent, b.mw_vent, b.overloaded), label
    assert (a["relief"], a["lifted"], a["over"]) == (
        b.m_relief_kgh, b.relief_lifted, b.m_overflow_kgh), label
    assert (a["sens"], a["q_gas"], a["q_net"], a["liq"]) == (
        b.q_sens_kw, b.q_gas_kw, b.q_net_kw, b.m_liquor_kgh), label
    if a["vent_line"]:
        assert (a["vent_line"]["top"], a["vent_line"]["steam"], a["vent_line"]["ti"]) == (
            b.t_top_c, b.m_flood_kgh, b.t_ti_322015_c), label
    assert (s.a328_c001_P, s.a328_c001_T, s.a328_c001_T_prev, s.a328_c001_M, s.a328_c001_w) == (
        unit.p_bara, unit.t_c, unit.t_prev_c, unit.m_kg, unit.w), label
    assert (b.p_bara, b.t_c, b.m_kg, b.level_pct) == (unit.p_bara, unit.t_c, unit.m_kg,
                                                      a["LI"]), label
    assert s.tlag == {key: unit.lag_state[key] for _, key in la.UP_LAG_KEYS}, label
    for v1c, loop in ((s.PIC_322201, loops.pic_322201), (s.LIC_322502, loops.lic_322502)):
        assert (v1c["op"], v1c["sp"], v1c["pv"], v1c["pv1"], v1c["pv2"], v1c["mode"]) == (
            loop.op, loop.sp, loop.pv, loop.pv1, loop.pv2, loop.mode), (label, loop.tag)


# --------------------------------------------------------------------------------------
# The design basis and the pin
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("ours, theirs", [
    ("C001_M755_DES_KGH", "A328_M755_DES"), ("C001_RHO_755_KGM3", "A328_M755_RHO"),
    ("C001_M756_DES_KGH", "A328_M756_DES"), ("C001_CPL_DES_KGH", "A328_CPL_DES"),
    ("C001_T_CPL_C", "A328_CPL_T"), ("C001_ABS_DES_KGH", "A328_ABS_DES"),
    ("C001_T_C", "A328_C001_T"), ("C001_T_755_C", "A328_M755_T"),
    ("C001_P_BARA", "A328_C001_P_BARA"), ("C001_ID_UP_M", "A328_C001_ID_UP_M"),
    ("C001_SHELL_UP_M", "A328_C001_SHELL_UP_M"), ("C001_ID_LO_M", "A328_C001_ID_LO_M"),
    ("C001_SHELL_LO_M", "A328_C001_SHELL_LO_M"), ("C001_VOL_UP_M3", "A328_C001_VOL_UP_M3"),
    ("C001_VOL_LO_M3", "A328_C001_VOL_LO_M3"), ("C001_VOL_CYL_M3", "A328_C001_VOL_M3"),
    ("C001_RHO_KGM3", "A328_C001_RHO_L"), ("C001_MW_VENT_DES", "A328_C001_MW_VENT_DES"),
    ("PV201_OP_DES_PCT_V1", "A328_PIC_OP_DES"), ("LV502_OP_DES_PCT_V1", "A328_LIC_OP_DES"),
    ("C001_LEVEL_DES_PCT", "A328_C001_LVL_SP_PCT"), ("C001_M_DES_KG_V1", "A328_C001_M_DES"),
    ("CP_C001", "A328_CP"), ("W_S755", "W_S755"),
    ("W_CPL", "W_CPL"), ("W_C001_DES", "W_C001_DES"), ("C001_ABS_CO2_DES_KGH", "A328_ABS_CO2_DES"),
    ("C001_ABS_H2O_DES_KGH", "A328_ABS_H2O_DES"), ("C001_ABS_NH3_DES_KGH", "A328_ABS_NH3_DES"),
    ("C001_ALPHA", "A328_C001_ALPHA"), ("C001_VENT_DES_KGH", "A328_VENT_DES"),
])
def test_design_basis(v1, ours, theirs):
    assert getattr(c, ours) == v1[theirs]


def test_the_packing_and_the_beds_are_v1s(v1):
    pa = v1["packed_absorber"]
    assert (c.PACKING_AREA_M2M3, c.PACKING_SIZE_M, c.PACKING_SIGMA_C_NM) == (
        pa.A_PACK, pa.D_PACK, pa.SIGMA_C_STEEL)
    assert ((pb.BED_LO.height_m, pb.BED_LO.id_m), (pb.BED_UP.height_m, pb.BED_UP.id_m)) == (
        (pa.BED_LO["Z"], pa.BED_LO["ID"]), (pa.BED_UP["Z"], pa.BED_UP["ID"]))
    assert (c.BED_RHO_LIQ_KGM3, c.BED_CP_LIQ, c.BED_CP_GAS) == (pa.RHO_LIQ, pa.CP_LIQ, pa.CP_GAS)


def test_the_design_pin_is_v1s_boot_pin(v1):
    """The calibration, the design vent and the heat residual `==` V1's boot pin on the same gas;
    the gas is 322E003's design vent, PFD 204, let down at 94.8 C."""
    pin, cap = la.design_pin(), v1["HV604_DES"]
    assert (pin.gas_kmolh, pin.gas_kgh, pin.t_gas_c) == (cap["comp"], cap["m"], cap["T"])
    assert pin.gas_kgh == sc.OFFGAS_DES_KGH and pin.t_gas_c == 94.8
    cal = v1["A328_C001_CAL"]
    assert (pin.cal.nh3, pin.cal.co2, pin.cal.a_w, pin.cal.abs_up) == (
        cal["NH3"], cal["CO2"], cal["a_w"], cal["abs_up"])
    assert pin.q_res_kw == v1["A328_C001_Q_RES_KW"]
    assert (pin.cal.nh3, pin.cal.co2, pin.cal.a_w) == pytest.approx((0.8004, 0.8379, 0.8808),
                                                                    abs=1e-4)
    assert pin.q_res_kw == pytest.approx(1.3304, abs=1e-4)


def test_the_vessel_as_decided(v1):
    """Decision 33's class: the name plate's 3.60 m3; the head's closed form against its profile
    integrated, 0.1029 m3; the seed holdup reading LIC-322502's 50 % exactly on the taps, 506.0 kg
    against V1's 1392.3 on half the lower cylinder."""
    assert c.C001_HEAD_VOL_M3 == pytest.approx(_head_m3(), rel=1e-8)
    assert c.C001_HEAD_VOL_M3 == pytest.approx(0.1029, abs=1e-4)
    assert la.lt_322502_pct(la.C001_M_SEED_KG) == 50.0 == _li_taps(la.C001_M_SEED_KG)
    assert la.C001_M_SEED_KG == pytest.approx(506.026, abs=1e-3)
    assert v1["A328_C001_M_DES"] == pytest.approx(1392.31, abs=0.01)


def test_the_state_and_controllers_are_seeded_as_v1_seeds_them(v1):
    s, unit, loops = _v1_state(v1), la.LpAbsorber(), la.LpAbsorberLoops()
    assert (s.a328_c001_M, s.a328_c001_T, s.a328_c001_T_prev, s.a328_c001_P, s.a328_c001_w) == (
        unit.m_kg, unit.t_c, unit.t_prev_c, unit.p_bara, unit.w)
    for v1c, loop in ((s.PIC_322201, loops.pic_322201), (s.LIC_322502, loops.lic_322502)):
        assert (v1c["mode"], v1c["op"], v1c["sp"], v1c["pv"], v1c["pv1"], v1c["pv2"], v1c["Kc"],
                v1c["Ti"], v1c["Td"], v1c["act"], v1c["op_lo"], v1c["op_hi"], v1c["sp_lo"],
                v1c["sp_hi"]) == (
            loop.mode, loop.op, loop.sp, loop.pv, loop.pv1, loop.pv2, loop.Kc, loop.Ti, loop.Td,
            loop.act, loop.op_lo, loop.op_hi, loop.sp_lo, loop.sp_hi), loop.tag
    assert (DECIDED_PV201_OP, DECIDED_LV502_OP) == (c.PV201_OP_DES_PCT, c.LV502_OP_DES_PCT)


def test_the_offgas_heat_executes_v1s_function(v1):
    pin = la.design_pin()
    for t_gas, t_liq, scale in ((94.8, 43.0, 1.0), (-36.0, 50.0, 3.0), (120.0, 25.0, 0.5)):
        comp = {k: v * scale for k, v in pin.gas_kmolh.items()}
        absorbed = {"NH3": 4.0 * scale, "CO2": 1.2 * scale, "H2O": -1.1}
        assert la.offgas_heat_kw(comp, t_gas, t_liq, absorbed, c.W_C001_DES) == (
            v1["c001_offgas_heat_kw"](comp, t_gas, t_liq, absorbed, v1["W_C001_DES"]))


# --------------------------------------------------------------------------------------
# The absorber on its own, tick by tick
# --------------------------------------------------------------------------------------

def _gas(scale: float = 1.0, nh3: float = 1.0, co2: float = 1.0, t_gas: float | None = None):
    """HV-322604's purge as V1's ``hv604``: the design gas scaled, its NH3 and CO2 further."""
    pin = la.design_pin()
    comp = {k: v * scale * (nh3 if k == "NH3" else co2 if k == "CO2" else 1.0)
            for k, v in pin.gas_kmolh.items()}
    return {"comp_kmolh": comp, "mass_kgh": sum(v * pb.MW_COMP[k] for k, v in comp.items()),
            "T_out": pin.t_gas_c if t_gas is None else t_gas}


def _purge(cool_frac: float):
    """HV-322604's purge on a cooling loss in 322E003, as the port's valve lets it down: its gas,
    and the carbamate liquor it condenses in its line (B-19)."""
    r = pv.purge_valve_322604(*_scrubber_vent(cool_frac), sc.HIC604_DES_PCT, sc.OFFGAS_P_BARA)
    return {"comp_kmolh": {k: v for k, v in r.vapour_kmolh.items() if v > 0.0},
            "mass_kgh": sum(v * pb.MW_COMP[k] for k, v in r.vapour_kmolh.items()),
            "T_out": r.t_out_c, "liquor": dict(r.liquor_kmolh)}


def _purge_step(cool_frac: float, k0: int = 10):
    """The design purge, then from tick `k0` the purge of a cooling loss — let down once, when the
    scenario first reaches it."""
    held = {}

    def script(k):
        if k < k0:
            return _design()
        if "gas" not in held:
            held["gas"] = _purge(cool_frac)
        return _design(gas=held["gas"])
    return script


def _scrubber_vent(cool_frac: float):
    from ureasim.data.unit_322r001 import OFFGAS_DES_KMOLH
    from ureasim.units.synthesis.scrubber import scrubber_322e003
    r = scrubber_322e003(OFFGAS_DES_KMOLH, 1.0, sc.CCW_T_IN_DES_C, sc.CCW_KGH_DES,
                         cool_frac=cool_frac)
    return r.offgas_kmolh, r.t_offgas_c


def _design(**over):
    base = {"gas": _gas(), "m755": c.C001_M755_DES_KGH, "t755": c.C001_T_755_C,
            "cpl": c.C001_CPL_DES_KGH, "xv": False}
    base.update(over)
    return base


def _run(v1, script, ticks: int, dt: float = DT, before=None, decided=ALL):
    """Drive the absorber alone through `script(k)`, comparing everything every tick."""
    s, unit, loops = _v1_state(v1, decided), la.LpAbsorber(), la.LpAbsorberLoops()
    if before:
        before(s, unit, loops)
    b = None
    for k in range(ticks):
        x = script(k)
        s.cpl_flow_kgh, s.XV_322915 = x["cpl"], x["xv"]
        a = _v1_c001(v1, s, x["gas"], x["m755"], dt, decided, x["t755"])
        gas = x["gas"]
        b = unit.step(loops, gas["comp_kmolh"], gas["mass_kgh"], gas["T_out"], x["m755"],
                      x["t755"], x["cpl"], x["xv"], dt, liquor_kmolh=gas.get("liquor"))
        _assert_tick(a, b, s, unit, loops, f"tick {k}")
    return s, unit, loops, b


def _step(k0, **after):
    return lambda k: _design(**after) if k >= k0 else _design()


def _manual(v1_name, name, op):
    def before(s, unit, loops):
        getattr(s, v1_name).update(mode="MAN", op=op)
        loop = getattr(loops, name)
        loop.set_mode("MAN")
        loop.op = op
    return before


SCENARIOS = {
    "design hold": (lambda k: _design(), 600, DT, None),
    "the purge up half": (_step(10, gas=_gas(1.5)), 1200, 0.5, None),
    "an ammonia-rich purge (a cooling loss upstream)": (
        _step(10, gas=_gas(1.2, nh3=6.0, co2=3.0, t_gas=26.0)), 1200, 0.5, None),
    "a -36 C purge, V1's let-down floor": (
        _step(10, gas=_gas(1.4, nh3=8.0, co2=3.5, t_gas=-36.0)), 1200, 0.5, None),
    "a purge condensing in its line (B-19)": (_purge_step(0.9), 1200, 0.5, None),
    "755 at 44 C (322E006's cooling water lost)": (_step(10, t755=44.0), 1200, 0.5, None),
    "755 cut to 60 %": (_step(10, m755=0.6 * c.C001_M755_DES_KGH), 1200, 0.5, None),
    "755 lost (322P002 tripped)": (_step(10, m755=0.0), 600, 0.5, None),
    "954 doubled": (_step(10, cpl=2.0 * c.C001_CPL_DES_KGH), 800, 0.5, None),
    "954 lost": (_step(10, cpl=0.0), 800, 0.5, None),
    "XV-322915 open (trip 22.1's flood)": (_step(10, xv=True), 1200, 0.5, None),
    "HV-322604 shut": (_step(10, gas=_gas(0.0)), 800, 0.5, None),
    "PIC-322201 on 4.5 bar a": (lambda k: _design(), 1200, 0.5, None),
    "PV-322201 held at 30 %": (lambda k: _design(), 1200, 0.5,
                               _manual("PIC_322201", "pic_322201", 30.0)),
    "LV-322502 held at 40 %": (lambda k: _design(), 800, 0.5,
                               _manual("LIC_322502", "lic_322502", 40.0)),
}


def _sp45(s, unit, loops):
    s.PIC_322201["sp"] = loops.pic_322201.sp = 4.5


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_the_absorber_tick_by_tick(v1, name):
    script, ticks, dt, before = SCENARIOS[name]
    if name == "PIC-322201 on 4.5 bar a":
        before = _sp45
    _run(v1, script, ticks, dt, before)
