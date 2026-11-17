"""V1 <-> V1.1 equivalence for 328C003, the hydrolyser, and 328E021, its interchanger.

What is being proved
--------------------
V1 writes the hydrolyser inline in `step_sim`, so its statements are TRANSCRIBED into `_v1_c003`
below, line for line, and declared as such: the aqueous cp (``main.py`` 8829), the stage itself
(9062-9165), 328E021's hot outlet from stage 5 (9181-9183), the 748 tear write (9669) and
TIC-328012 (10080). Everything they call is V1's own code, executed: ``_ctrl_ipd``, ``_fic_flow``,
``aqueous_cp``, ``liquor_pv_bara``, ``hydrolysis_x_328c003``, ``des_rel_vol_ratio`` and
``des_advance`` lifted out of ``main.py`` with every constant they read; ``hydraulics`` loaded as
a real module. Two statements are not plain assignments, and lifting cannot see them: V1 takes
the design endotherm out of the overhead's latent heat with an augmented assignment (3373), and
closes the hydrolysis vector's CO2 with a subscript assignment (3285); both are transcribed into
the fixture. The state is seeded as ``State.__init__`` seeds it.

The departures
--------------
Seven, each a switch in the transcription: ``decided`` names the ones whose port lines stand in
V1's. The first the process engineer decided on this unit; the other five are classes decided on
another unit and applied here under §5 rule 7.

  * "vapour" — the liquid loses, and pays the latent heat of, what boils; V1 charges it what
    PV-328203 vents (decision 24);
  * "E021" — 328E021's cold side takes only what the hot side gave (decision 14);
  * "heel" — LV-328504 drains only the liquid above a 1 kg heel (decision 11);
  * "overflow" — a full shell's excess leaves as a stream (decision 11);
  * "valve" — PV-328203 on Flowserve's trim from 70.56 %, xT 0.8047 (decision 23), V1's
    ``valve_gas_anchored`` executed on it through `decided_valves.hydraulics`;
  * "gains" — PIC-328203 and FIC-329402 on the table's gains per cent of span (decision 10),
    seeded into V1's controller dicts;
  * "relief" — SV32852 lifts at its set pressure and vents the head space to its reseat
    pressure (handoff B-47, decided 2026-09-30); V1 relieves nothing. The law is written below
    from Uhde's and Sempell's sheets, on V1's own ``vessel_dpdt`` and IAPWS-IF97;
  * "lv504" — LV-328504 on Fisher's trim (decision 150): equal percentage, FL 0.819, from its
    design stroke, seeded into LIC-328504, on V1's own ``valve_liquid_anchored``.

Every scenario runs the port against the switched transcription; those where E021, the heel and
the overflow never act also run on V1's own lines for those three; and each departure runs both
ways — bit-exact to the tick it first acts, or from the first tick where it is a seed, then V1's
behaviour asserted on V1's side and the port's on the port's. Last, the hydrolyser is coupled to
V1's 328C002 in V1's order: 746 same-tick, 748 a tear.
"""

from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

from ureasim.core.flowsheet import Connection, CyclicFlowsheetError, Flowsheet, Tear, Unit
from ureasim.data import control_valves as cvd
from ureasim.data import control_valves_fisher as fv
from ureasim.data import desorption_train as t
from ureasim.data import unit_328c003 as c
from ureasim.units.desorption import first_desorber as fd
from ureasim.units.desorption import hydrolyser as hy
from tests.equivalence import decided_relief as dr
from tests.equivalence import decided_valves as dv
from tests.equivalence import test_first_desorber_equivalence as c002_eq
from tests.equivalence.v1_loader import lift, load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

C003_NAMES = [
    "R328_C003_T", "R328_C003_T746", "R328_C003_DT_DES", "R328_C003_DT_748",
    "R328_C003_RHO_746_KGM3", "R328_C003_P_BARA", "R328_C003_ID_M", "R328_C003_SHELL_M",
    "R328_C003_VOL_M3", "R328_C003_AREA_M2", "R328_C003_PV_OP_DES", "R328_C003_M_DES",
    "R328_C003_M911_DH", "R328_C003_LAM748", "R328_AI701_TAU_S", "R328_C003_W_UREA_746",
    "R328_C003_UREA_DES", "R328_HYD_K_LN_A", "R328_HYD_K_B_K", "urea_hydrolysis_k_m3_kmol_h",
    "hydrolysis_x_328c003", "R328_C003_X_DES", "R328_C003_XI_DES", "R328_HYD_GAS_MW",
    "R328_C003_GASHYD_DES", "R328_C003_GASSTR_DES", "R328_HYD_DH_KJMOL",
    "R328_C003_QHYD_DES_KW", "R328_E021_LOSS_DT", "R328_C004_T", "R328_C004_T749",
    "R328_C004_P_BARA", "R328_C003_H_DES_M", "R328_C003_HEAD_DES", "R328_LV504_OP_DES",
    "R328_LV504_PV_DES", "R328_M748_MW_DES", "R328_DES_VOLATILE", "_fic_flow", "_lag1",
]

#: V1's namespaces for 328D003, 328E007 and 328C002, built as their own equivalence tests build
#: them.
tank_v1 = c002_eq.tank_v1
e007_v1 = c002_eq.e007_v1
c002_v1 = c002_eq.v1

DT = 0.1

ALL = frozenset({"vapour", "E021", "heel", "overflow", "valve", "gains", "relief", "lv504"})
V1_VERBATIM = frozenset()
#: The seeded classes alone.
SEEDED = frozenset({"valve", "gains", "lv504"})
#: The seeded classes on decision 24's books: V1's lines for the exchanger and the two limits.
#: The liquid's books differ from V1's in every transient, so the inert scenarios run on them.
ON_BOOKS = SEEDED | {"vapour", "relief"}

def _sv32852(g) -> dr.Valve:
    """SV32852 as decided (B-47), written from its sheets: set 23.0 bar g on 1.010 bar a (Uhde
    UD-RL-328-EC-0003), reseating 10 % of set below; 24 897.4 kg/h of steam at 330 C and set plus
    10 % (Sempell, UD-RL-G00-DZ-0001-001 page 92), the steam's Z on V1's IAPWS-IF97 region 2."""
    p_set = 23.0 + 1.010
    p_rel, t_rel, mw_rel = p_set + 0.1 * 23.0, 330.0 + 273.15, g["MW_SOL"]["H2O"]
    v_rel = load("iapws_if97")._region2(t_rel, p_rel * 0.1)[1]
    z_rel = p_rel * 1.0e5 * v_rel * mw_rel / 1000.0 / (g["hydraulics"].R_GAS * t_rel)
    return dr.Valve(p_set, p_set - 0.1 * 23.0, p_rel, 24897.4, t_rel, mw_rel, z_rel)


#: PV-328203 as decided, re-derived from the vendor catalogue: design stroke [%], xT.
DECIDED_PV203_OP = dv.design_stroke_pct(cvd.PV_328203, t.C003_M748_DES_KGH)
DECIDED_PV203_XT = cvd.PV_328203.cases[cvd.PV_328203.normal].xt
#: LV-328504 as decided (decision 150), re-derived from Fisher's sheet: design stroke [%] and FL.
DECIDED_LV504_OP = dv.design_stroke_pct(fv.LV_328504, t.C003_M747_DES_KGH)
DECIDED_LV504_FL = 0.819
#: The stroke at which LV-328504 passes 80 % of its design flow at design pressures — 52.10 % on
#: the 50:1 equal percentage, where V1's linear trim passes it at 40 %.
LV504_AT_80_PCT = DECIDED_LV504_OP + 100.0 * math.log(0.8) / math.log(50.0)
#: The two gains as decided, written from their sources: the table on PT-328203's 40 bar and on
#: FT-329402's 1800 kg/h.
DECIDED_PIC203_KC = 1.5 * 100.0 / 40.0
DECIDED_FIC402_KC = 0.4 * 100.0 / 1800.0


@pytest.fixture(scope="module")
def v1(c002_v1):
    ns = dict(c002_v1)
    ns.update(lift(C003_NAMES, seed=dict(ns)))
    # main.py 3373, an augmented assignment lifting cannot see, TRANSCRIBED.
    ns["R328_C003_LAM748"] -= ns["R328_C003_QHYD_DES_KW"] / (ns["R328_C003_M748_DES"] / 3600.0)
    # main.py 3285, a subscript assignment lifting cannot see either, TRANSCRIBED: the CO2 closer
    # of the hydrolysis vector ``des_advance`` reads. 328C002 runs it at xi = 0, so only here does
    # its absence show.
    nu = ns["DES_HYD_NU"]
    nu["CO2"] = -(nu["Urea"] + nu["H2O"] + nu["NH3"])
    return ns


def _v1_state(v1, decided=ALL):
    """The V1 plant-state fields 328C003 reads and writes, seeded as `State.__init__` seeds them
    (``main.py`` 6849-6852, 6860, 6867, 7023-7034, 7083-7087, 7096-7100); "valve" and "gains"
    in `decided` seed the port's PV-328203 stroke and the two span gains."""
    g = v1
    s = c002_eq._v1_state(v1)
    s.a328_c003_M = g["R328_C003_M_DES"]
    s.a328_c003_T = g["R328_C003_T"]
    s.a328_c003_T_prev = g["R328_C003_T"]
    s.a328_c003_P = g["R328_C003_P_BARA"]
    s.sv_32852_lifted = False
    s.a328_c004_P = g["R328_C004_P_BARA"]
    s.w_328c003 = dict(g["W_S747"])
    s.y_328_748 = dict(g["DES_C003"]["y"])
    s.FIC_329402 = {"mode": "CAS", "op": 50.0, "sp": g["R328_C003_M911_DES"],
                    "pv": g["R328_C003_M911_DES"], "pv1": g["R328_C003_M911_DES"],
                    "pv2": g["R328_C003_M911_DES"], "Kc": 0.4, "Ti": 200.0, "Td": -1.0,
                    "act": +1.0, "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0, "sp_hi": 3000.0}
    P = g["R328_C003_P_BARA"]
    s.PIC_328203 = {"mode": "AUTO", "op": g["R328_C003_PV_OP_DES"], "sp": P, "pv": P, "pv1": P,
                    "pv2": P, "Kc": 1.5, "Ti": 50.0, "Td": -1.0, "act": -1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 12.0, "sp_hi": 20.0}
    s.LIC_328504 = {"mode": "AUTO", "op": 50.0, "sp": 50.0, "pv": 50.0, "pv1": 50.0,
                    "pv2": 50.0, "Kc": 0.2, "Ti": 300.0, "Td": 0.0, "act": -1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0, "sp_hi": 100.0}
    D = g["R328_C003_DT_DES"]
    s.TIC_328012 = {"mode": "AUTO", "op": 50.0, "sp": D, "pv": D, "pv1": D, "pv2": D,
                    "Kc": 3.0, "Ti": 250.0, "Td": 0.0, "act": -1.0,
                    "op_lo": 0.0, "op_hi": 100.0, "sp_lo": 0.0, "sp_hi": 30.0}
    if "valve" in decided:
        s.PIC_328203["op"] = DECIDED_PV203_OP
    if "lv504" in decided:
        s.LIC_328504["op"] = DECIDED_LV504_OP
    if "gains" in decided:
        s.PIC_328203["Kc"] = DECIDED_PIC203_KC
        s.FIC_329402["Kc"] = DECIDED_FIC402_KC
        # TIC-328012 on its faceplate in the plant DCS (decided 2026-10-28): 0.20 on 0-200, 3000 s.
        s.TIC_328012["Kc"], s.TIC_328012["Ti"] = 0.20 * 100.0 / 200.0, 3000.0
    return s


def _v1_c003(v1, s, m_743, dt, decided=ALL):
    """V1 `main.py` 8829, 9062-9165, 9181-9183, 9669 and 10080, TRANSCRIBED line for line; each
    departure in `decided` puts the port's lines in V1's."""
    g = v1
    MW_SOL, SOL_SPECIES = g["MW_SOL"], g["SOL_SPECIES"]
    cp_328c003 = g["aqueous_cp"](g["R328_CP"], g["R328_C003_T"], s.a328_c003_T)
    Tc003 = s.a328_c003_T
    m_746 = m_743
    T_746 = s.a328_c002_T + g["R328_E021_EPS_T"] * (Tc003 - s.a328_c002_T)
    m_911 = g["_fic_flow"](s.FIC_329402, g["R328_C003_M911_DES"], 50.0, s.tlag, "F_329402", dt)
    in_c003 = m_746 + m_911
    pic203b_op = g["_ctrl_ipd"](s.PIC_328203, s.a328_c003_P, dt)
    _mw748_live = 1.0 / max(sum(s.y_328_748.get(k, 0.0) / MW_SOL[k] for k in SOL_SPECIES), 1e-12)
    if "valve" in decided:  # ---- PV-328203 on its vendor trim (the port's valve) ----
        m_748 = dv.hydraulics().valve_gas_anchored(
            g["R328_C003_M748_DES"], pic203b_op / 100.0, s.a328_c003_P, s.a328_c002_P,
            Tc003 + 273.15, DECIDED_PV203_OP / 100.0, g["R328_C003_P_BARA"],
            g["R328_C002_P_TOP"], g["R328_C003_T"] + 273.15, _mw748_live,
            characteristic=dv.MOD_EQUAL_PCT, xt=DECIDED_PV203_XT, mw_des=g["R328_M748_MW_DES"])
    else:
        m_748 = g["hydraulics"].valve_gas_anchored(
            g["R328_C003_M748_DES"], pic203b_op / 100.0, s.a328_c003_P, s.a328_c002_P,
            Tc003 + 273.15, g["R328_C003_PV_OP_DES"] / 100.0, g["R328_C003_P_BARA"],
            g["R328_C002_P_TOP"], g["R328_C003_T"] + 273.15, _mw748_live,
            characteristic="linear", mw_des=g["R328_M748_MW_DES"])
    x_hyd_328 = g["hydrolysis_x_328c003"](
        Tc003, m_746, w_urea=s.w_328c002.get("Urea", g["R328_C003_W_UREA_746"]),
        w_h2o=s.w_328c002.get("H2O", g["W_S743"]["H2O"]))
    urea_in_328 = m_746 * s.w_328c002["Urea"]
    xi_hyd_328 = urea_in_328 / MW_SOL["Urea"] * x_hyd_328
    gas_hyd = xi_hyd_328 * g["R328_HYD_GAS_MW"]
    gas_str = g["R328_C003_GASSTR_DES"] * (m_911 / g["R328_C003_M911_DES"])
    gen748 = gas_hyd + gas_str
    # ---- decision 24: the liquid loses what boils (the port's lines), V1's the vent ----
    boil = gen748 if "vapour" in decided else m_748
    lvl_c003 = s.a328_c003_M / g["R328_C003_M_DES"] * 50.0
    lic504_op = g["_ctrl_ipd"](s.LIC_328504, lvl_c003, dt)
    _h_c003 = s.a328_c003_M / (g["R328_C003_RHO_746_KGM3"] * g["R328_C003_AREA_M2"])
    _p1_504 = s.a328_c003_P + g["R328_C003_RHO_746_KGM3"] * 9.80665 * _h_c003 / 1.0e5
    op_des, char, fl = g["R328_LV504_OP_DES"], g["R328_LV_CHAR"], g["hydraulics"].FL_GLOBE
    if "lv504" in decided:  # ---- LV-328504 on Fisher's trim (the port's valve) ----
        op_des, char, fl = DECIDED_LV504_OP, "equal_pct", DECIDED_LV504_FL
    m_747 = g["hydraulics"].valve_liquid_anchored(
        g["R328_C003_M747_DES"], lic504_op / 100.0, _p1_504, s.a328_c004_P,
        g["R328_C003_RHO_746_KGM3"], op_des / 100.0,
        g["R328_C003_P_BARA"] + g["R328_C003_HEAD_DES"], g["R328_C004_P_BARA"],
        g["R328_C003_RHO_746_KGM3"], characteristic=char, fl=fl,
        pv_bara=g["liquor_pv_bara"](s.w_328c003, s.tlag.get("T_749", g["R328_C004_T749"])),
        pv_des_bara=g["R328_LV504_PV_DES"])
    lost = False
    if "heel" in decided:  # ---- the decided heel (the port's lines) ----
        avail = max(max(s.a328_c003_M - 1.0, 0.0) / max(dt, 1e-9) * 3600.0 + in_c003 - boil,
                    0.0)
        lost = m_747 > avail
        if lost:
            m_747 = avail
    ppm_urea_747 = urea_in_328 * (1.0 - x_hyd_328) / max(m_747, 1e-6) * 1e6
    # main.py 9181-9183, 328E021's hot outlet (stage 5), on this stage's m_747 = m_749.
    T749_raw = Tc003 - (m_746 * (T_746 - s.a328_c002_T) + g["R328_E021_LOSS_DT"]) / max(m_747,
                                                                                          1e-6)
    lo, hi = min(s.a328_c002_T, Tc003), max(s.a328_c002_T, Tc003)
    T_749 = min(max(T749_raw, lo), hi)
    pinched = not lo <= T749_raw <= hi
    if "E021" in decided and pinched and m_746 > 0.0:  # ---- decision 14 (the port's lines) ----
        share = m_746 * (T_746 - s.a328_c002_T)
        given = m_747 * (Tc003 - T_749) - g["R328_E021_LOSS_DT"]
        taken = min(max(given, min(share, 0.0)), max(share, 0.0))
        T_746 = s.a328_c002_T + taken / m_746
    sens_c003 = m_746 / 3600.0 * cp_328c003 * (T_746 - Tc003)
    q_hyd_328 = xi_hyd_328 * g["R328_HYD_DH_KJMOL"] * 1000.0 / 3600.0
    P_c003 = (sens_c003 + m_911 / 3600.0 * g["R328_C003_M911_DH"]
              - boil / 3600.0 * g["R328_C003_LAM748"] - q_hyd_328)
    M_c003_pre = s.a328_c003_M
    over, full = 0.0, g["R328_C003_VOL_M3"] * g["R328_C003_RHO_746_KGM3"]
    if "overflow" in decided:  # ---- the decided overflow (the port's lines) ----
        m_new = max(M_c003_pre + (in_c003 - boil - m_747) / 3600.0 * dt, 1.0)
        if m_new > full:
            over = (m_new - full) / max(dt, 1e-9) * 3600.0
    _vv_c003 = g["hydraulics"].vapour_volume_m3(g["R328_C003_VOL_M3"], M_c003_pre,
                                                g["R328_C003_RHO_746_KGM3"])
    _T_c003_pre = s.a328_c003_T
    _p_free = s.a328_c003_P + g["hydraulics"].vessel_dpdt(
        s.a328_c003_P, s.a328_c003_T + 273.15, _vv_c003, _mw748_live,
        gen748 / _mw748_live, m_748 / _mw748_live,
        dtdt_k_s=(s.a328_c003_T - s.a328_c003_T_prev) / dt,
        dvvdt_m3_s=-((in_c003 - boil - m_747 - over) / 3600.0)
        / g["R328_C003_RHO_746_KGM3"]) * dt
    relief = 0.0
    if "relief" in decided:  # ---- B-47: SV32852 (the port's lines) ----
        relief, s.sv_32852_lifted = dr.vent(
            g, _sv32852(g), s.a328_c003_P, _p_free, s.a328_c003_T + 273.15, _mw748_live,
            _vv_c003, dt, s.sv_32852_lifted)
        if relief > 0.0:
            _p_free += g["hydraulics"].vessel_dpdt(
                s.a328_c003_P, s.a328_c003_T + 273.15, _vv_c003, _mw748_live, 0.0,
                relief / _mw748_live) * dt
    s.a328_c003_P = max(_p_free, 0.1)
    s.a328_c003_T_prev = _T_c003_pre
    k_cap_328c003 = m_746 / 3600.0 * cp_328c003
    s.a328_c003_T = Tc003 + P_c003 * dt / max(M_c003_pre * cp_328c003 + k_cap_328c003 * dt, 1e-6)
    s.a328_c003_M = max(M_c003_pre + (in_c003 - boil - m_747) / 3600.0 * dt, 1.0)
    if over:
        s.a328_c003_M = full
    _a_rel_c003 = g["des_rel_vol_ratio"]("C003", s.w_328c003, s.a328_c003_T, s.a328_c003_P,
                                         g["R328_C003_T"], g["R328_C003_P_BARA"])
    a_c003 = {k: (v * _a_rel_c003[k] if k in g["R328_DES_VOLATILE"] else v)
              for k, v in g["DES_C003"]["alpha"].items()}
    s.w_328c003, y_748 = g["des_advance"](s.w_328c003, s.a328_c003_M,
                                          [(s.w_328c002, m_746), (g["W_STEAM"], m_911)],
                                          boil, a_c003, m_747 + over, xi_hyd_328, dt)
    s.y_328_748 = y_748
    s.tlag["T_749"] = T_749
    s.tlag["R328_748"] = m_748                       # main.py 9669, the tear 328C002 reads
    tic_op = g["_ctrl_ipd"](s.TIC_328012, s.a328_c003_T - T_746, dt)   # main.py 10080
    return {"746T": T_746, "749T": T_749, "pinched": pinched, "911": m_911, "pic": pic203b_op,
            "748": m_748, "gen": gen748, "hyd": gas_hyd, "str": gas_str, "x": x_hyd_328,
            "urea": urea_in_328, "xi": xi_hyd_328, "ppm": ppm_urea_747, "lvl": lvl_c003,
            "lic": lic504_op, "747": m_747, "lost": lost, "P": P_c003, "qhyd": q_hyd_328,
            "over": over, "tic": tic_op, "domain": g["DES_VLE_DOMAIN"].get("C003"),
            "relief": relief, "lifted": s.sv_32852_lifted,
            # main.py 10768-10776, the telemetry.
            "TT_328011": s.a328_c003_T - g["R328_C003_DT_748"],
            "LI_328504": s.a328_c003_M / g["R328_C003_M_DES"] * 50.0}


LOOPS = (("FIC_329402", "fic_329402"), ("PIC_328203", "pic_328203"),
         ("LIC_328504", "lic_328504"), ("TIC_328012", "tic_328012"))


def _loop(loops, name):
    loop = getattr(loops, name)
    return loop.loop if isinstance(loop, hy.FlowLoop) else loop


def _assert_tick(a: dict, b: hy.HydrolyserResult, s, col, loops, label):
    assert (a["746T"], a["749T"], a["pinched"], a["911"], a["pic"], a["748"]) == (
        b.t_746_c, b.t_749_c, b.e021_pinched, b.m_911_kgh, b.pic_op_pct, b.m_748_kgh), label
    assert (a["gen"], a["hyd"], a["str"], a["x"], a["urea"], a["xi"], a["ppm"]) == (
        b.gen_748_kgh, b.gas_hyd_kgh, b.gas_strip_kgh, b.x_hyd, b.urea_in_kgh, b.xi_kmolh,
        b.urea_747_ppm), label
    assert (a["lvl"], a["lic"], a["747"], a["lost"], a["P"], a["qhyd"], a["over"]) == (
        b.lic_pv_pct, b.lic_op_pct, b.m_747_kgh, b.drain_lost, b.q_net_kw, b.q_hyd_kw,
        b.m_overflow_kgh), label
    assert (a["relief"], a["lifted"]) == (b.m_relief_kgh, b.relief_lifted), label
    assert (s.a328_c003_P, s.a328_c003_T, s.a328_c003_T_prev, s.a328_c003_M) == (
        col.p_bara, col.t_c, col.t_prev_c, col.m_kg), label
    assert (b.p_bara, b.t_c, b.m_kg, b.t_748_c, b.level_pct) == (
        col.p_bara, col.t_c, col.m_kg, a["TT_328011"], a["LI_328504"]), label
    assert (s.w_328c003, s.y_328_748) == (col.w, col.y_748) == (b.w, b.y_748), label
    assert (s.tlag["T_749"], a["domain"], a["tic"]) == (col.t_749_c, b.vle_domain,
                                                         b.tic_op_pct), label
    assert s.tlag["F_329402"] == loops.fic_329402.measurement, label
    for v1_name, name in LOOPS:
        v1c, loop = getattr(s, v1_name), _loop(loops, name)
        assert (v1c["op"], v1c["sp"], v1c["pv"], v1c["pv1"], v1c["pv2"], v1c["mode"]) == (
            loop.op, loop.sp, loop.pv, loop.pv1, loop.pv2, loop.mode), (label, v1_name)


# --------------------------------------------------------------------------------------
# The design basis
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("module, ours, theirs", [
    (c, "C003_T_C", "R328_C003_T"), (c, "C003_P_BARA", "R328_C003_P_BARA"),
    (c, "C003_T746_C", "R328_C003_T746"), (c, "C003_DT_DES_K", "R328_C003_DT_DES"),
    (c, "C003_DT_748_K", "R328_C003_DT_748"), (c, "C003_RHO_KGM3", "R328_C003_RHO_746_KGM3"),
    (c, "C003_ID_M", "R328_C003_ID_M"), (c, "C003_SHELL_M", "R328_C003_SHELL_M"),
    (c, "C003_VOL_M3", "R328_C003_VOL_M3"), (c, "C003_AREA_M2", "R328_C003_AREA_M2"),
    (c, "C003_M_DES_KG", "R328_C003_M_DES"), (c, "C003_H_DES_M", "R328_C003_H_DES_M"),
    (c, "C003_HEAD_DES_BAR", "R328_C003_HEAD_DES"), (c, "M911_DH_KJKG", "R328_C003_M911_DH"),
    (c, "C003_TAU_DES_S", "R328_AI701_TAU_S"), (c, "HYDROLYSIS_DH_KJMOL", "R328_HYD_DH_KJMOL"),
    (c, "E021_EPS_T", "R328_E021_EPS_T"), (c, "E021_LOSS_DT_KGKH", "R328_E021_LOSS_DT"),
    (c, "MW748_DES", "R328_M748_MW_DES"), (c, "LV504_PV_DES_BARA", "R328_LV504_PV_DES"),
    (t, "C004_T_C", "R328_C004_T"), (t, "C004_T749_C", "R328_C004_T749"),
    (t, "C004_P_BARA", "R328_C004_P_BARA"),
    (hy, "HYD_GAS_MW", "R328_HYD_GAS_MW"), (hy, "C003_X_DES", "R328_C003_X_DES"),
    (hy, "C003_UREA_DES_KGH", "R328_C003_UREA_DES"), (hy, "C003_XI_DES_KMOLH", "R328_C003_XI_DES"),
    (hy, "C003_GASHYD_DES_KGH", "R328_C003_GASHYD_DES"),
    (hy, "C003_GASSTR_DES_KGH", "R328_C003_GASSTR_DES"),
    (hy, "C003_QHYD_DES_KW", "R328_C003_QHYD_DES_KW"), (hy, "C003_LAM748_KJKG", "R328_C003_LAM748"),
])
def test_design_basis(v1, module, ours, theirs):
    assert getattr(module, ours) == v1[theirs]


def test_the_lifted_latent_carries_v1s_second_statement(v1):
    """The overhead's latent heat is 1377.97 kJ/kg as first assigned, 843.84 once V1 takes the
    design endotherm out of it — the value the stage runs on."""
    assert c.LAM748_BASE_KJKG == pytest.approx(1377.974, abs=1e-3)
    assert v1["R328_C003_LAM748"] == hy.C003_LAM748_KJKG == pytest.approx(843.84, abs=0.01)


def test_the_head_and_the_letdown_anchor(v1):
    assert c.LV504_P1_DES_BARA == v1["R328_C003_P_BARA"] + v1["R328_C003_HEAD_DES"]
    assert c.C003_FULL_KG == v1["R328_C003_VOL_M3"] * v1["R328_C003_RHO_746_KGM3"]


@pytest.mark.parametrize("t_c", [150.0, 180.0, 200.0, 210.0])
@pytest.mark.parametrize("m_746", [0.0, 5000.0, t.C003_M746_DES_KGH, 50000.0])
@pytest.mark.parametrize("w_urea, w_h2o", [(0.0076, 0.97), (0.02, 0.95), (0.0, 0.97),
                                           (0.5, 0.5 * 60.056 / 18.0153)])
def test_the_conversion_integral_executes_v1s(v1, t_c, m_746, w_urea, w_h2o):
    assert hy.hydrolysis_conversion(t_c, m_746, w_urea, w_h2o) == \
        v1["hydrolysis_x_328c003"](t_c, m_746, w_urea=w_urea, w_h2o=w_h2o)


def test_the_state_and_the_controllers_are_seeded_as_v1_seeds_them(v1):
    """Every seed V1's, but PV-328203's stroke and the two span gains, which the decided seeds
    carry; V1's own are 50 %, 1.50 %/bar and 0.40 %/(kg/h)."""
    s, col, loops = _v1_state(v1), hy.Hydrolyser(taps=False), hy.HydrolyserLoops()
    assert (s.a328_c003_M, s.a328_c003_T, s.a328_c003_T_prev, s.a328_c003_P, s.w_328c003,
            s.y_328_748) == (col.m_kg, col.t_c, col.t_prev_c, col.p_bara, col.w, col.y_748)
    assert col.t_749_c == v1["R328_C004_T749"]
    for v1_name, name in LOOPS:
        v1c, loop = getattr(s, v1_name), _loop(loops, name)
        assert (v1c["mode"], v1c["op"], v1c["sp"], v1c["pv"], v1c["pv1"], v1c["pv2"], v1c["Kc"],
                v1c["Ti"], v1c["Td"], v1c["act"], v1c["op_lo"], v1c["op_hi"], v1c["sp_lo"],
                v1c["sp_hi"]) == (loop.mode, loop.op, loop.sp, loop.pv, loop.pv1, loop.pv2,
                                  loop.Kc, loop.Ti, loop.Td, loop.act, loop.op_lo, loop.op_hi,
                                  loop.sp_lo, loop.sp_hi), v1_name
    s0 = _v1_state(v1, V1_VERBATIM)
    assert (s0.PIC_328203["op"], s0.PIC_328203["Kc"], s0.FIC_329402["Kc"]) == (50.0, 1.5, 0.4)
    assert s0.LIC_328504["op"] == 50.0
    assert (v1["R328_LV504_OP_DES"], v1["R328_LV_CHAR"]) == (50.0, "linear")
    assert (c.LV504_OP_DES_PCT, c.LV504_CHAR, c.LV504_FL) == (
        pytest.approx(DECIDED_LV504_OP, rel=1e-12), "equal_pct", DECIDED_LV504_FL)
    assert DECIDED_LV504_OP == pytest.approx(57.802, abs=1e-3)
    assert (DECIDED_PV203_OP, DECIDED_PIC203_KC, DECIDED_FIC402_KC) == (
        pytest.approx(70.5615, abs=1e-4), 3.75, pytest.approx(0.02222, abs=1e-5))


# --------------------------------------------------------------------------------------
# The column on its own, tick by tick
# --------------------------------------------------------------------------------------

def _design(**over):
    base = {"m746": t.C003_M746_DES_KGH, "w746": dict(t.W_S743), "tc002": t.C002_T_BOT_C,
            "pc002": t.C002_P_TOP_BARA, "pc004": t.C004_P_BARA}
    base.update(over)
    return base


def _feed(s, x):
    """Write a tick's boundaries into V1's neighbouring states."""
    s.w_328c002 = dict(x["w746"])
    s.a328_c002_T, s.a328_c002_P, s.a328_c004_P = x["tc002"], x["pc002"], x["pc004"]


def _port(col, loops, x, dt):
    return col.step(loops, x["m746"], dict(x["w746"]), x["tc002"], x["pc002"], x["pc004"], dt)


def _run(v1, script, ticks: int, dt: float = DT, before=None, decided=ALL):
    """Drive the hydrolyser alone through `script(k)`, comparing everything every tick."""
    s, col, loops = _v1_state(v1, decided), hy.Hydrolyser(taps=False), hy.HydrolyserLoops()
    if not {"valve", "gains"} <= decided:
        raise ValueError("the port's seeds are the decided ones; run V1's in the divergences")
    if before:
        before(s, col, loops)
    b = None
    for k in range(ticks):
        x = script(k)
        _feed(s, x)
        a = _v1_c003(v1, s, x["m746"], dt, decided)
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


UREA_RICH = dict(t.W_S743)
UREA_RICH["Urea"] = 2.0 * t.W_S743["Urea"]
UREA_RICH["H2O"] = t.W_S743["H2O"] - t.W_S743["Urea"]

SCENARIOS = {
    "design hold": (lambda k: _design(), 600, DT, None),
    "746 cut a fifth": (_step(10, m746=0.8 * t.C003_M746_DES_KGH), 1200, 0.5, None),
    "746 up a fifth: 328E021 pinches": (_step(10, m746=1.2 * t.C003_M746_DES_KGH), 1200, 0.5,
                                        None),
    "328C002 5 K colder": (_step(10, tc002=t.C002_T_BOT_C - 5.0), 1200, 0.5, None),
    "328C002 at 4.5 bar a": (_step(10, pc002=4.5), 600, DT, None),
    "328C004 at 5.0 bar a": (_step(10, pc004=5.0), 1200, 0.5, None),
    "twice the urea": (_step(10, w746=UREA_RICH), 1200, 0.5, None),
    "FIC-329402 to 800 kg/h": (lambda k: _design(), 1200, 0.5,
                               _set_point("FIC_329402", "fic_329402", 800.0)),
    "PIC-328203 to 17.5 bar a": (lambda k: _design(), 1200, 0.5,
                                 _set_point("PIC_328203", "pic_328203", 17.5)),
    "PV-328203 in MAN at 20 %": (lambda k: _design(), 600, DT,
                                 _manual("PIC_328203", "pic_328203", 20.0)),
    "LV-328504 in MAN at 40 %": (lambda k: _design(), 1200, 0.5,
                                 _manual("LIC_328504", "lic_328504", 40.0)),
    "the MP steam lost": (lambda k: _design(), 1200, 0.5,
                          _manual("FIC_329402", "fic_329402", 0.0)),
}


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_the_hydrolyser_tick_by_tick(v1, name):
    script, ticks, dt, before = SCENARIOS[name]
    _run(v1, script, ticks, dt, before)


#: The scenarios where 328E021 never pinches and neither limit binds, run on V1's lines for all
#: three, on decision 24's books: the three switches are inert there.
INERT = ["design hold", "746 cut a fifth", "328C002 5 K colder", "328C002 at 4.5 bar a",
         "328C004 at 5.0 bar a", "twice the urea", "FIC-329402 to 800 kg/h",
         "PIC-328203 to 17.5 bar a", "PV-328203 in MAN at 20 %"]


@pytest.mark.parametrize("name", INERT)
def test_the_three_departures_are_inert_where_they_do_not_act(v1, name):
    script, ticks, dt, before = SCENARIOS[name]
    s, col, loops, b = _run(v1, script, ticks, dt, before, decided=ON_BOOKS)
    assert not (b.e021_pinched or b.drain_lost) and b.m_overflow_kgh == 0.0


# --------------------------------------------------------------------------------------
# The flowsheet: 746 same-tick from 328C002, 748 back as a tear
# --------------------------------------------------------------------------------------

def test_746_is_same_tick_and_748_the_tear():
    fs = Flowsheet()
    for tag in ("328C002", "328C003", "328C004"):
        fs.add_unit(Unit(tag, tag, tag[:3]))
    fs.connect(Connection("743", "328C002", "328C003"))
    fs.connect(Connection("748", "328C003", "328C002"))
    fs.connect(Connection("747", "328C003", "328C004"))
    with pytest.raises(CyclicFlowsheetError):
        fs.evaluation_order()
    fs.tear(Tear("R328_748", "328C003", ("328C002",), "V1 steps 328C002 first; read a tick late"))
    assert fs.evaluation_order() == ("328C002", "328C003", "328C004")


def test_the_hydrolyser_takes_746_on_the_same_tick(v1):
    """V1's 328C002 and 328C003 in V1's order against the two ported columns: the hydrolyser
    takes 743 and 328C002's state of THIS tick, 328C002 the hydrolyser's 748 a tick late. The
    feed cut, and then the MP steam cut, move both hand-offs."""
    s = _v1_state(v1)
    col2, lic2 = fd.FirstDesorber(taps=False), fd.lic_328503(taps=False)
    col3, loops3 = hy.Hydrolyser(taps=False), hy.HydrolyserLoops()
    m748, y748 = t.C002_M748_DES_KGH, dict(t.DES_C003.y)
    seen = set()
    for k in range(3000):
        m738 = t.C002_M738_DES_KGH * (0.85 if k >= 10 else 1.0)
        if k == 1500:
            s.FIC_329402["sp"] = loops3.fic_329402.loop.sp = 900.0
        x2 = c002_eq._design(m738=m738, m748=m748, y748=y748,
                             tc003=s.a328_c003_T, pc003=s.a328_c003_P)
        s.tlag["R328_750"], s.tlag["R328_775"] = x2["m750"], x2["m775"]
        s.y_328_750, s.a328_d001_P = dict(x2["y750"]), x2["pd001"]
        a2 = c002_eq._v1_c002(v1, s, x2["m738"], x2["t738"], DT)
        a3 = _v1_c003(v1, s, a2["743"], DT)
        b2 = c002_eq._port(col2, lic2, x2, DT)
        b3 = col3.step(loops3, b2.m_743_kgh, b2.w, b2.t_c, b2.p_bara, t.C004_P_BARA, DT)
        m748, y748 = b3.m_748_kgh, dict(b3.y_748)
        c002_eq._assert_tick(a2, b2, s, col2, lic2, f"328C002, tick {k}")
        _assert_tick(a3, b3, s, col3, loops3, f"328C003, tick {k}")
        seen.add(b3.m_748_kgh)
    assert len(seen) > 100


# --------------------------------------------------------------------------------------
# The decided divergence, decision 24: the liquid pays what boils, both sides
# --------------------------------------------------------------------------------------

def _c003_books(p_bara, t_c, m_kg, y):
    """328C003's holdup, the head space's moles, and the tick's molar mass (as 328C002's)."""
    return (m_kg, c002_eq.head_space_kg(p_bara, t_c, m_kg, c.C003_VOL_M3, c.C003_RHO_KGM3, 1.0),
            c002_eq.vapour_mw(y))


@pytest.mark.parametrize("name, before, v1_made, v1_t, v1_p, p", [
    ("PV-328203 in MAN at 20 %", _manual("PIC_328203", "pic_328203", 20.0), 500.25, 203.019,
     37.954, 23.180),
    ("PV-328203 shut", _manual("PIC_328203", "pic_328203", 0.0), 812.03, 205.022, 44.933, 23.330),
    ("PIC-328203 to 17.5 bar a", _set_point("PIC_328203", "pic_328203", 17.5), 12.82, 200.068,
     17.501, 17.503),
])
def test_the_liquid_pays_what_boils_decided_divergence(v1, name, before, v1_made, v1_t, v1_p, p):
    """Decision 24. V1's liquid loses what PV-328203 vents and pays its latent heat, while the
    pressure integral fills the head space with what the column generates: vapour a throttled
    valve holds back is made, and boiled for nothing. The books — the liquid plus the head
    space's vapour, read off the pressure state at the molar mass each tick ran on, against what
    crossed the boundary — are kept on both sides for an hour at 0.5 s. With the valve at 20 % V1
    makes 500 kg, exactly its integral of generation less overhead, and runs 3.0 K hot on the
    latent heat it never charged; shut, 812 kg and 5.0 K; a set point 0.7 bar up, 13 kg. The
    port's books — SV32852's vent among what crosses the boundary (B-47) — close within 50 g
    and the column holds 200 C, its pressure rising on the vapour it now keeps until SV32852 holds
    it between 21.71 and 24.01 bar a. V1 runs without the relief here, as it is."""
    dt = 0.5
    s, col, loops = _v1_state(v1), hy.Hydrolyser(taps=False), hy.HydrolyserLoops()
    before(s, col, loops)
    made_v1 = made = held_back = 0.0
    for k in range(7200):
        x = _design()
        _feed(s, x)
        pre_v1 = _c003_books(s.a328_c003_P, s.a328_c003_T, s.a328_c003_M, s.y_328_748)
        pre = _c003_books(col.p_bara, col.t_c, col.m_kg, col.y_748)
        a = _v1_c003(v1, s, x["m746"], dt, ALL - {"vapour", "relief"})
        b = _port(col, loops, x, dt)
        made_v1 += c002_eq._made(pre_v1, s.a328_c003_M, s.a328_c003_P, s.a328_c003_T,
                                 c.C003_VOL_M3, c.C003_RHO_KGM3,
                                 x["m746"] + a["911"] - a["748"] - a["747"] - a["over"], dt)
        made += c002_eq._made(pre, col.m_kg, col.p_bara, col.t_c, c.C003_VOL_M3, c.C003_RHO_KGM3,
                              x["m746"] + b.m_911_kgh - b.m_748_kgh - b.m_747_kgh
                              - b.m_overflow_kgh - b.m_relief_kgh, dt)
        held_back += (a["gen"] - a["748"]) * dt / 3600.0
    assert made_v1 == pytest.approx(v1_made, abs=0.01)
    assert made_v1 == pytest.approx(held_back, rel=1e-3)
    assert abs(made) < 0.05
    assert (s.a328_c003_T, s.a328_c003_P) == (pytest.approx(v1_t, abs=1e-3),
                                              pytest.approx(v1_p, abs=1e-3))
    assert (col.t_c, col.p_bara) == (pytest.approx(hy.C003_T_C, abs=1e-6),
                                     pytest.approx(p, abs=1e-3))


# --------------------------------------------------------------------------------------
# The five classes applied under rule 7: both sides
# --------------------------------------------------------------------------------------

def _both(v1, script, ticks, dt, before, v1_decided):
    """V1 with `v1_decided` against the port: the tick they part, the tick each of the port's
    flags first rises, each side's liquid books on what boils, the temperature each side
    started the last tick on, and both sides at the end."""
    s = _v1_state(v1, v1_decided)
    col, loops = hy.Hydrolyser(taps=False), hy.HydrolyserLoops()
    if before:
        before(s, col, loops)
    out = SimpleNamespace(parted=None, first={}, made_v1=0.0, made=0.0, s=s, col=col,
                          vented=0.0, lifts=0, p_hi=0.0, p_lo=None)
    for k in range(ticks):
        x = script(k)
        _feed(s, x)
        v1_pre, pre = s.a328_c003_M, col.m_kg
        out.t_pre_v1, out.t_pre = s.a328_c003_T, col.t_c
        a = _v1_c003(v1, s, x["m746"], dt, v1_decided)
        b = _port(col, loops, x, dt)
        out.made_v1 += s.a328_c003_M - v1_pre - (x["m746"] + a["911"] - a["gen"] - a["747"]
                                                 - a["over"]) * dt / 3600.0
        out.made += col.m_kg - pre - (x["m746"] + b.m_911_kgh - b.gen_748_kgh - b.m_747_kgh
                                      - b.m_overflow_kgh) * dt / 3600.0
        if out.parted is None:
            try:
                _assert_tick(a, b, s, col, loops, f"tick {k}")
            except AssertionError:
                out.parted = k
        for key, flag in (("pinched", b.e021_pinched), ("lost", b.drain_lost),
                          ("over", b.m_overflow_kgh > 0.0), ("relief", b.relief_lifted)):
            if flag:
                out.first.setdefault(key, k)
        # SV32852's record: what it vents, how often it lifts, and the band it holds.
        out.lifts += b.relief_lifted and not getattr(out, "lifted", False)
        out.lifted = b.relief_lifted
        out.vented += b.m_relief_kgh * dt / 3600.0
        out.p_hi = max(out.p_hi, b.p_bara)
        if "relief" in out.first:
            out.p_lo = b.p_bara if out.p_lo is None else min(out.p_lo, b.p_bara)
    out.a, out.b = a, b
    return out


def test_sv32852_relieves_the_shut_overhead_decided_divergence(v1):
    """B-47, decided 2026-09-30. PV-328203 shut. V1 relieves nothing: on the liquid's decided
    books it stands at 57.32 bar a an hour on, past the column's 28.5 bar a design. The port's
    column reaches SV32852's set, 24.01 bar a, at 459 s; the valve lifts, vents the head space at
    27 t/h for 5 s down to its reseat pressure, 21.71 bar a, and reseats — and the cycle repeats,
    20 lifts in the hour, venting 694 kg: what the column generated and could not pass. They part on the tick the valve lifts, and the liquid's books close on both sides."""
    r = _both(v1, lambda k: _design(), 7200, 0.5, _manual("PIC_328203", "pic_328203", 0.0),
              ALL - {"relief"})
    assert r.parted == r.first["relief"] == 918
    assert r.s.a328_c003_P == pytest.approx(57.317, abs=1e-3)
    assert r.p_hi == pytest.approx(24.0173, abs=1e-4) and r.p_hi < c.SV32852_SET_BARA + 0.01
    assert r.p_lo == pytest.approx(c.SV32852_RESEAT_BARA, abs=1e-9)
    assert r.lifts == 20 and r.vented == pytest.approx(693.71, abs=0.01)
    assert abs(r.made_v1) < 1e-6 and abs(r.made) < 1e-6


def test_328e021_never_makes_heat_decided_divergence(v1):
    """Decision 14. LV-328504 held where it passes 80 % of its design flow (52.10 % on Fisher's
    trim, decision 150; V1's 40 %): 747 falls below 85 % of the feed and 328E021 pinches on the
    first tick. V1 heats 746 to 190 C whatever the hot side gave — its 749
    clamped at 139 C, the cold side taking 36 000 kg.K/h more than the hot side gave, some 43 kW
    made — and holds 200 C and 0.73 ppm. The port's feed takes what the hot side gave: 188.06 C
    an hour on, the column 1.03 K colder and its condensate at 1.16 ppm."""
    r = _both(v1, lambda k: _design(), 7200, 0.5,
              _manual("LIC_328504", "lic_328504", LV504_AT_80_PCT), ALL - {"E021"})
    a, b, s, col = r.a, r.b, r.s, r.col
    assert r.parted == r.first["pinched"] == 0
    assert a["pinched"] and a["746T"] == pytest.approx(190.0, abs=1e-9)
    loss = c.E021_LOSS_DT_KGKH
    m_746 = t.C003_M746_DES_KGH
    assert m_746 * (a["746T"] - t.C002_T_BOT_C) - (
        a["747"] * (r.t_pre_v1 - a["749T"]) - loss) == pytest.approx(36085.0, abs=5.0)
    assert m_746 * (b.t_746_c - t.C002_T_BOT_C) == pytest.approx(
        b.m_747_kgh * (r.t_pre - b.t_749_c) - loss, rel=1e-12)
    assert (s.a328_c003_T, a["ppm"]) == (pytest.approx(200.0, abs=1e-4),
                                         pytest.approx(0.7263, abs=1e-4))
    assert (b.t_746_c, col.t_c, b.urea_747_ppm) == (pytest.approx(188.061, abs=1e-3),
                                                    pytest.approx(198.966, abs=1e-3),
                                                    pytest.approx(1.164, abs=1e-3))


def test_lv_328504_at_the_heel_decided_divergence(v1):
    """Decision 11. LV-328504 held wide open drains 101 t/h on Fisher's trim (decision 150) against
    35 t/h arriving: the column reaches its heel at 1628.5 s. V1's letdown goes on passing 101 t/h
    and its 1 kg floor makes the difference — 171.1 t of liquid in the three hours; the port's passes what arrives less
    what boils, flagged, and makes none."""
    r = _both(v1, lambda k: _design(), 21600, 0.5, _manual("LIC_328504", "lic_328504", 100.0),
              ALL - {"heel"})
    a, b = r.a, r.b
    assert r.parted == r.first["lost"] == 3257
    assert r.made_v1 == pytest.approx(171084.7, abs=0.1) and abs(r.made) < 1e-6
    assert a["747"] == pytest.approx(100572.5, abs=0.1)
    assert b.drain_lost and b.m_747_kgh == pytest.approx(
        t.C003_M746_DES_KGH + b.m_911_kgh - b.gen_748_kgh, rel=1e-9)


def test_a_full_hydrolyser_overflows_decided_divergence(v1):
    """Decision 11. LV-328504 shut: the column fills at 35 t/h and is full at 2378.5 s. V1 goes
    on filling past its 62.3 m3 shell — 68.1 t in it an hour on, 120 % of what it holds; the
    port's holds 56 570 kg and lets the rest go as the overflow, its books closed."""
    r = _both(v1, lambda k: _design(), 7200, 0.5, _manual("LIC_328504", "lic_328504", 0.0),
              ALL - {"overflow"})
    s, col, b = r.s, r.col, r.b
    assert r.parted == r.first["over"] == 4757
    assert s.a328_c003_M == pytest.approx(68132.8, abs=0.1)
    assert s.a328_c003_M / c.C003_FULL_KG > 1.2
    assert col.m_kg == c.C003_FULL_KG and b.m_overflow_kgh == pytest.approx(34090.5, abs=0.1)
    assert abs(r.made_v1) < 1e-6 and abs(r.made) < 1e-6


def test_pv_328203_on_its_vendor_trim_decided_divergence(v1):
    """Decision 23. PV-328203 held at 20 %: on V1's linear trim from 50 % it passes 324.8 kg/h
    on the first tick, on Valtek's modified equal percentage from 70.56 % 159.7 — half. Ten
    minutes on the port's column stands 2.0 bar higher."""
    s0 = _v1_state(v1, ALL - {"valve"})
    assert s0.PIC_328203["op"] == 50.0
    r = _both(v1, lambda k: _design(), 1, 0.5, _manual("PIC_328203", "pic_328203", 20.0),
              ALL - {"valve"})
    assert r.parted == 0
    assert (r.a["748"], r.b.m_748_kgh) == (pytest.approx(324.8, abs=0.1),
                                           pytest.approx(159.7, abs=0.1))
    r = _both(v1, lambda k: _design(), 1200, 0.5, _manual("PIC_328203", "pic_328203", 20.0),
              ALL - {"valve"})
    assert (r.s.a328_c003_P, r.col.p_bara) == (pytest.approx(21.787, abs=1e-3),
                                               pytest.approx(23.830, abs=1e-3))
    assert (r.a["748"], r.b.m_748_kgh) == (pytest.approx(420.9, abs=0.1),
                                           pytest.approx(226.3, abs=0.1))


def test_lv_328504_on_fishers_trim_decided_divergence(v1):
    """Decision 150. LV-328504 on Fisher's equal percentage from 57.80 % on FL 0.819; V1's linear
    from 50 % on FL 0.90. Both pass 747's 34 062 kg/h at their design strokes: on the seed tick the
    flows agree to the bit, the strokes differ. 746 cut a fifth: an hour on V1 has drawn its level
    down to 45.00 % passing 28 046 kg/h; the port, its trim's gain lower at design, to 46.48 %
    passing 26 182."""
    r = _both(v1, lambda k: _design(), 1, 0.5, None, ALL - {"lv504"})
    assert r.parted == 0
    assert r.a["747"] == r.b.m_747_kgh == t.C003_M747_DES_KGH
    assert (r.a["lic"], r.b.lic_op_pct) == (50.0, pytest.approx(DECIDED_LV504_OP, abs=1e-9))
    r = _both(v1, _step(10, m746=0.8 * t.C003_M746_DES_KGH), 7200, 0.5, None, ALL - {"lv504"})
    assert (r.a["747"], r.b.m_747_kgh) == (pytest.approx(28046.4, abs=0.1),
                                           pytest.approx(26181.8, abs=0.1))
    assert (r.a["LI_328504"], r.b.level_pct) == (pytest.approx(45.00, abs=0.01),
                                                 pytest.approx(46.48, abs=0.01))


@pytest.mark.parametrize("name, before, field, v1_end, end", [
    ("PIC-328203 to 17.5 bar a", _set_point("PIC_328203", "pic_328203", 17.5), "P", 17.624,
     17.394),
    ("FIC-329402 to 800 kg/h", _set_point("FIC_329402", "fic_329402", 800.0), "911", 801.35,
     841.67),
])
def test_the_two_gains_on_span_decided_divergence(v1, name, before, field, v1_end, end):
    """Decision 10. PIC-328203 on 3.75 %/bar where V1 runs 1.50, FIC-329402 on 0.0222 %/(kg/h)
    where V1 runs 0.40, each twenty minutes after a set-point step. The pressure loop is faster on
    span and swings through its set point; the steam loop, eighteen times softer, is 42 kg/h
    short of its new set point where V1's is 1."""
    r = _both(v1, lambda k: _design(), 2400, 0.5, before, ALL - {"gains"})
    assert r.parted == 0
    ours = r.col.p_bara if field == "P" else r.b.m_911_kgh
    theirs = r.s.a328_c003_P if field == "P" else r.a["911"]
    assert (theirs, ours) == (pytest.approx(v1_end, abs=0.01), pytest.approx(end, abs=0.01))


def test_li_328504_between_its_taps_decided_divergence(v1):
    """Decision 246 (handoff B-156's sixth unit), both sides. V1 reads LI-328504 as M / M_des x 50;
    the port reads LT-328504 between N5B and N5A, 1 475 and 475 mm below the top tangent line (Uhde
    UD-AU-328-EC-0003 p. 5; EC-0134 p. 6), V1's design holdup read as the drawing's N.L.L. at
    mid-span. Both hold 50 % at design, so the design tick is V1's to the bit; 746 cut 25 % at 1 s,
    each side reads its own law on its own holdup every tick, and the port's loop, 25.1 times as
    stiff per kilogram, dips 435 kg in the half hour where V1's dips 2 566 kg and is still
    falling."""
    s, col, loops = _v1_state(v1), hy.Hydrolyser(), hy.HydrolyserLoops()
    assert c.LT_328504_DES_PCT == c.C003_LEVEL_DES_PCT == 50.0
    assert c.C003_M_DES_KG / c.LT_328504_SPAN_KG * 2.0 == pytest.approx(25.12, abs=0.01)
    dips = [col.m_kg, s.a328_c003_M]
    for k in range(18000):
        x = _design(m746=0.75 * t.C003_M746_DES_KGH) if k >= 10 else _design()
        _feed(s, x)
        m_v1 = s.a328_c003_M
        a = _v1_c003(v1, s, x["m746"], DT, ALL)
        b = _port(col, loops, x, DT)
        assert a["lvl"] == m_v1 / c.C003_M_DES_KG * 50.0, f"tick {k}"
        assert b.level_pct == c.lt_328504_pct(col.m_kg), f"tick {k}"
        if k == 0:
            _assert_tick(a, b, s, col, loops, "tick 0")
        dips = [min(dips[0], col.m_kg), min(dips[1], s.a328_c003_M)]
    assert c.C003_M_DES_KG - dips[0] == pytest.approx(434.9, abs=0.5)
    assert c.C003_M_DES_KG - dips[1] == pytest.approx(2566.0, abs=0.5)
