"""V1 <-> V1.1 equivalence for unit 329's steam network — `ureasim.units.steam`.

What is being proved
--------------------
V1's ``backend/steam_system.py`` is a real module, loaded and EXECUTED. Its ``step_steam`` is also
TRANSCRIBED below line for line (`_v1_steam`, handoff A-12) with a switch for each decided
departure; with every switch off the transcription is ``==`` V1's executed ``step_steam`` on every
field of V1's ``SteamState`` on every tick, and with every switch on it is ``==`` the port's
`SteamNetwork` on every tick. ``decided`` names the switches whose port lines stand in V1's:

  * "B-68" — every simulated user's live draw on its header, the rest at their PFD rows (decided
    2026-10-02): the scenario driver hands the transcription the live LP users, where V1 holds
    ``M_USERS_LP``, the design raising less the turbine's export, set at boot;
  * "47" — the PFD's basis (decision 47's class): PV-329204 seeded on 902's 57 989 kg/h, LV-329502's
    design on 904's, the flash fraction 4658 / 57 989, the stripper's and the HPCC's draws on their
    PFD closures; V1 anchors on the stripper's 39 400 kW / 1850 kJ/kg and the HPCC's 2120 kJ/kg;
  * "B-70" — the waters the drums pay (decided 2026-10-02): 902's superheat boils 329D005's water,
    V1's 275 kg/h of 903's comes out of 329D009's, 960's and 963's boil 322D001's; 913 flashes
    into the LP header; 959 blows down; no letdown water from nowhere and no 3.5 bar a floor;
    LV-329503 and LV-329504 at the tick's starting pressures;
  * "taps" — each drum's water over its whole vessel and its level between its taps (decision
    33), its valves drawing at most what it holds (decision 11): the port's `drums`;
  * "trim" — PV-329205A / B and LV-329502 / 503 / 504 on Flowserve's trims from their design
    strokes (decision 23), the letdowns on their condensate's vapour pressure (decision 31): the
    port's `steam_valves`; V1 linear from 50 %, PV-329205B on K 2.0;
  * "loopsum" — HV-329601, PV-329207A, PV-329207C and HV-329602 wide open on their loop summaries'
    maximum cases (§4); V1's literal coefficients;
  * "gains" — PIC-329204 and the PIC-329207 trio on the table per cent of span, LIC-329503 and
    LIC-329504 on their rows (decisions 10, 21); V1's 1.8 %/bar, its 24 %/bar retune, 2.5 / 90 s;
  * "trip" — trip 21.2's set point on PIC-329204 and HV-329601's forcing, as Uhde's functional
    diagram draws them (decisions 26, 27, 39): the port's `header_control`; V1 has neither;
  * "relief" — the drums' certified safety valves (decision 32); V1 has none;
  * "917" — the LP header downstream of 322D001A/B (the process engineer's topology note,
    2026-10-02; PFD 26, P&ID 107/1): 960 joins the header past the drums, so its superheat boils
    no drum water, and the drums' balance is written on their discharge 917, what the header's
    users and valves take less 960; V1 and B-70 put 960 into 322D001's steam space.

`test_steam_network_decided_equivalence.py` runs each departure both ways.
"""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from ureasim.control.valve import valve_liquid_anchored
from ureasim.data import control_valves as cvd
from ureasim.data import unit_329 as d
from ureasim.data import unit_329_network as n
from ureasim.thermo import water_steam as ws
from ureasim.units.steam import steam_valves as sv
from ureasim.units.steam.drums import D001, D005, D009
from ureasim.units.steam.header_control import Hv329601, Pic329204, supply_seed_pct
from ureasim.units.steam.steam_network import (
    SteamDraws,
    SteamNetwork,
    _relief_valve,
    v1_butterflies,
)
from tests.equivalence.v1_loader import load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

ALL = frozenset({"B-68", "47", "B-70", "taps", "trim", "loopsum", "gains", "trip", "relief",
                 "917"})
DT = 0.1
DRUMS = (("329D005", D005, "m_d005"), ("329D009", D009, "m_d009"), ("322D001", D001, "m_d001"))


@pytest.fixture(scope="module")
def v1():
    return load("steam_system")


# ======================================================================================
# The design inputs each combination of switches closes on [kg/s]
# ======================================================================================

def basis_913_kgh(v1, decided) -> float:
    """LV-329503's design flow on a combination's basis [kg/h]: 905 less what B-70's drum water
    takes, on the PFD's 904 ("47") or V1's 39 400 / 1850."""
    m904 = d.STEAM_PFD_KGH["904"] if "47" in decided else v1.M_STRIP_DES * 3600.0
    return m904 - d.STEAM_PFD_KGH["906"] - (d.DS9_DES_KGH if "B-70" in decided else 0.0)


def design_inputs(v1, decided) -> dict:
    """The stripper's draw, the HPCC's raising, the 9-bar users and the LP users at design
    [kg/h]; both sides divide them by 3600 as the port does."""
    b70, p47 = "B-70" in decided, "47" in decided
    if p47:
        strip = d.STRIP_DES_KGH if b70 else d.STEAM_PFD_KGH["902"]
    else:
        m902 = 39400.0 / 1850.0 * 3600.0
        strip = m902 + (m902 * ws.superheat_water_ratio(d.H_902_KJKG, d.P_HP_BARA)
                        if b70 else 0.0)
    if b70:
        flash4 = (d.FLASH4_DES_KGH if p47 else basis_913_kgh(v1, decided)
                  * ws.flash_fraction(d.P_MP_BARA, d.P_LP_BARA))
    else:
        flash4 = 0.0
    turbine = d.STEAM_PFD_KGH["932"]
    if "B-68" in decided:
        users_lp = d.LP_USERS_DES_KGH
        raise_ = users_lp + turbine - flash4
    else:
        raise_ = d.RAISE_DES_KGH if p47 else 106270.8997007087
        users_lp = raise_ + flash4 - turbine
    return {"strip": strip, "raise": raise_, "users_9": d.MP9_USERS_DES_KGH,
            "users_lp": users_lp}


# ======================================================================================
# The transcription
# ======================================================================================

def _v1_state(v1, decided, inputs):
    """V1's ``SteamState()`` with what the switches seed differently, and the transcription's own
    fields (the drums' water, trip 21.2's logic, the safety valves)."""
    s = SimpleNamespace(**vars(v1.SteamState()))
    if "47" in decided:
        s.valve_supply_pct = supply_seed_pct()
    if "trim" in decided:
        s.valve_admit9_pct = n.PV205A_OP_DES_PCT
        s.lic502_op, s.lic503_op, s.lic504_op = (n.LV502_OP_DES_PCT, n.LV503_OP_DES_PCT,
                                                 n.LV504_OP_DES_PCT)
    for _, drum, attr in DRUMS:
        setattr(s, attr, drum.mass_at_level_kg(50.0))
    s.pic204 = Pic329204(op_pct=s.valve_supply_pct)
    s.hv601 = Hv329601()
    s.svs = (_relief_valve("SV32951", n.SV_329D005), _relief_valve("SV32952", n.SV_329D009),
             _relief_valve("SV32978", n.SV_322D001, n.N_SV_322D001))
    s.m_users_lp = inputs["users_lp"]
    s.raise_des = inputs["raise"] / 3600.0
    return s


def _lic(v1, tag, s, prefix, direct, dt, decided, level):
    """V1 ``_level_loop``'s control, TRANSCRIBED; "gains" its table row."""
    kc, ti = n.LIC_TUNING[tag] if ("gains" in decided and tag != "LIC-329502") else (
        v1.LIC_KC, v1.LIC_TI)
    sp, op, ep, mode = (getattr(s, prefix + k) for k in ("_sp", "_op", "_ep", "_mode"))
    e = (level - sp) if direct else (sp - level)
    if mode == "AUTO":
        op = max(0.0, min(100.0, op + kc * ((e - ep) + (dt / ti) * e)))
    setattr(s, prefix + "_op", op)
    setattr(s, prefix + "_ep", e)
    return op


def _lv_v1(v1, op, m_des, p_up, p_dn, p_up_des, p_dn_des, rho, rho_des):
    """V1 ``_level_loop``'s valve, TRANSCRIBED."""
    return v1.hydraulics.valve_liquid_anchored(
        m_des, max(0.0, min(100.0, op)) / 100.0, p_up, p_dn, rho, v1.LV_OPEN_DES / 100.0,
        p_up_des, p_dn_des, rho_des, characteristic=v1.LV_CHAR, pv_bara=0.0)


#: "trim": each level valve's vendor trim, FL and design stroke, its vapour pressure (decision 31)
#: its upstream drum's for the two letdowns, 916's for the make-up — the port's lines.
_TRIM = {"LV-329502": (cvd.LV_329502, n.LV502_OP_DES_PCT, n.LV502_FL, d.P_HP_BARA, d.P_MP_BARA),
         "LV-329503": (cvd.LV_329503, n.LV503_OP_DES_PCT, n.LV503_FL, d.P_MP_BARA, d.P_LP_BARA),
         "LV-329504": (cvd.LV_329504, n.LV504_OP_DES_PCT, n.LV504_FL, d.P_916_BARA, d.P_LP_BARA)}


def _lv_trim(tag, op, m_des, p_up, p_dn):
    """A level valve on its vendor trim, anchored on the combination's design flow."""
    valve, h_des, fl, p_up_des, p_dn_des = _TRIM[tag]
    if tag == "LV-329504":
        rho = rho_des = d.RHO_916_KGM3
        pv = pv_des = sv.PV_916_BARA
    else:
        rho, rho_des = ws.rho_drum_liquid_kgm3(p_up), ws.rho_drum_liquid_kgm3(p_up_des)
        pv, pv_des = p_up, p_up_des
    return valve_liquid_anchored(m_des, max(0.0, min(100.0, op)) / 100.0, p_up, p_dn, rho,
                                 h_des / 100.0, p_up_des, p_dn_des, rho_des,
                                 characteristic=valve.characteristic, fl=fl, pv_bara=pv,
                                 pv_des_bara=pv_des)


def _v1_level(v1, s, prefix, m_span, dm, dt):
    lvl = getattr(s, prefix + "_lvl")
    setattr(s, prefix + "_lvl", max(0.0, min(100.0, lvl + dm * dt / m_span * 100.0)))


def _cap(m, inflow, outflow, dt):
    available = (m - n.DRUM_M_FLOOR_KG) / dt + inflow
    if outflow <= available or outflow <= 0.0:
        return 1.0
    return max(available, 0.0) / outflow


def _v1_steam(v1, s, dt, inputs, decided, trip=False):
    """V1 ``step_steam`` (``steam_system.py`` 473-680), TRANSCRIBED line for line (handoff A-12);
    the switches in the module docstring."""
    g = v1
    p47, b70, taps, trim = "47" in decided, "B-70" in decided, "taps" in decided, "trim" in decided
    hdr = "917" in decided
    early = b70 or taps
    m_strip, m_hpcc = inputs["strip"] / 3600.0, inputs["raise"] / 3600.0
    m_9_users, users_lp = inputs["users_9"] / 3600.0, s.m_users_lp / 3600.0
    K_902 = n.K_902 if p47 else g.K_902
    m502_des = n.M_502_DES_KGS if p47 else g.M_502_DES
    flash9_frac = d.FLASH9_FRACTION if p47 else g.FLASH9_FRACTION
    if p47 and b70:
        m503_des, m504_des = n.M_503_DES_KGS, n.M_504_DES_KGS
    elif b70:
        m503_des = basis_913_kgh(v1, decided) / 3600.0
        m504_des = (s.raise_des + d.BLOWDOWN_KGH / 3600.0
                    - m503_des * (1.0 - ws.flash_fraction(d.P_MP_BARA, d.P_LP_BARA)))
    else:
        m503_des = m502_des - g.M_FLASH9_DES if p47 else g.M_503_DES
        m504_des = s.raise_des - m503_des
    loopsum = "loopsum" in decided
    k_601, p601 = (n.K_HV601, (n.HV601_P1_DES_BARA, n.HV601_P2_DES_BARA)) if loopsum else (
        g.K_902, (g.P_HP_BARA, 1.01325))
    k_963, k_602, p963 = ((n.K_963, n.K_HV602, (n.P963_P1_DES_BARA, n.P963_P2_DES_BARA))
                          if loopsum else (g.K_963, g.K_HV602, (g.P_SUP_BARA, g.P_LP_BARA)))
    k_207a, p207a = ((n.K_207A, (n.P207A_P1_DES_BARA, n.P207A_P2_DES_BARA)) if loopsum
                     else (g.K_207A, (g.P_LP_BARA, 1.01325)))
    if "gains" in decided:
        k204, ki204, i204_clamp = n.PIC_329204_KC, n.PIC_329204_KI, 50.0 / n.PIC_329204_KI
        kc7, ki7 = n.PIC_329207_KC, n.PIC_329207_KI
    else:
        k204, ki204, i204_clamp = g.K_PIC_204, g.KI_PIC_204, g.I204_CLAMP
        kc7 = dict.fromkeys("ABC", g.K_PIC_207)
        ki7 = dict.fromkeys("ABC", g.KI_PIC_207)
    bias204 = supply_seed_pct() if p47 else g._SUPPLY_BIAS
    bias205 = n.PV205A_OP_DES_PCT if trim else g.PV205A_BIAS_PCT

    s.P_SUP = g.P_SUP_BARA

    # -- LV-329502 (main 488-496) --
    lvl502 = D005.level_pct(s.m_d005) if taps else s.lic502_lvl
    op502 = _lic(v1, "LIC-329502", s, "lic502", True, dt, decided, lvl502)
    if trim:
        m_lv502 = _lv_trim("LV-329502", op502, m502_des, s.P_MP, s.P_9)
    else:
        m_lv502 = _lv_v1(v1, op502, m502_des, s.P_MP, s.P_9, g.P_HP_BARA, g.P_MP_BARA,
                         g._rho_drum_liquid(s.P_MP), g.rho_liquid_sat_kgm3(g.tsat_c(g.P_HP_BARA)))

    # -- PIC-329204 (498-504); "trip": the port's, its set point loaded by trip 21.2 --
    if "trip" in decided:
        s.pic204.mode, s.pic204.sp_bara, s.pic204.i_bar_s, s.pic204.op_pct = (
            s.pic204_mode, s.pic204_sp, s.i_204, s.valve_supply_pct)
        if trip and not s.pic204.trip_prev:
            s.pic204.sp_pulse_s = 2.0
        s.pic204.trip_prev = trip
        if s.pic204.sp_pulse_s > 0.0:
            s.pic204.sp_bara = n.TRIP_212_SP_BARA
            s.pic204.sp_pulse_s = max(s.pic204.sp_pulse_s - dt, 0.0)
        s.pic204_sp = s.pic204.sp_bara
    if s.pic204_mode == "AUTO":
        e204 = s.pic204_sp - s.P_MP
        s.i_204 = max(-i204_clamp, min(i204_clamp, s.i_204 + e204 * dt))
        s.valve_supply_pct = max(0.0, min(100.0, bias204 + k204 * e204 + ki204 * s.i_204))
    m_supply = g._valve_flow(K_902, s.valve_supply_pct, s.P_SUP, s.P_MP,
                             g.P_SUP_BARA, g.P_HP_BARA)
    if "trip" in decided:
        s.hv_vent_hp_pct = s.hv601.step(s.P_MP, trip, dt)
    m_vent_hp = g._valve_flow(k_601, s.hv_vent_hp_pct, s.P_MP, 1.01325, *p601)
    ds5 = m_supply * ws.superheat_water_ratio(d.H_902_KJKG, s.P_MP) if b70 else 0.0
    f5 = _cap(s.m_d005, m_strip, ds5 + m_lv502, dt) if taps else 1.0
    ds5, m_lv502 = ds5 * f5, m_lv502 * f5
    m_flash9 = flash9_frac * m_lv502

    # -- PIC-329205 split range (518-531) --
    if s.pic205_mode == "AUTO":
        err9 = s.P_9 - s.pic205_sp
        split = bias205 - g.K_PIC_9 * err9
        if split >= 0.0:
            s.valve_admit9_pct = min(100.0, split)
            s.valve_letdown_pct = 0.0
        else:
            s.valve_admit9_pct = 0.0
            s.valve_letdown_pct = min(100.0, -split)
    if trim:
        m_903 = sv.pv_329205a_kgs(s.valve_admit9_pct, s.P_SUP, s.P_9)
        m_ld9 = sv.pv_329205b_kgs(s.valve_letdown_pct, s.P_9, s.P_LP)
    else:
        m_903 = g._valve_flow(g.K_903, s.valve_admit9_pct, s.P_SUP, s.P_9, g.P_SUP_BARA,
                              g.P_MP_BARA)
        m_ld9 = g._valve_flow(g.K_LD9, s.valve_letdown_pct, s.P_9, s.P_LP, g.P_MP_BARA,
                              g.P_LP_BARA)
    m_attemper9 = g.M_ATTEMPER9_DES * (m_903 / max(g.M_903_DES, 1e-12))
    m_water = 0.0 if b70 else m_ld9 * (g.H_G_MP - g.H_G_LP) / (g.H_G_LP - g.H_W)

    # -- the trio (542-591) --
    if s.master207_on:
        s.pic207a_sp = s.master207_sp + g.DB_LP
        s.pic207_sp = s.master207_sp
        s.pic207c_sp = s.master207_sp - g.DB_LP
        s.pic207a_mode = s.pic207_mode = s.pic207c_mode = "AUTO"
    if s.pic207a_mode == "AUTO":
        eA = s.P_LP - s.pic207a_sp
        s.i_207a = max(0.0, min(100.0 / ki7["A"], s.i_207a + eA * dt))
        s.pv207a_pct = max(0.0, min(100.0, kc7["A"] * eA + ki7["A"] * s.i_207a))
    m_vent = g._valve_flow(k_207a, s.pv207a_pct, s.P_LP, 1.01325, *p207a)
    if s.pic207_mode == "AUTO":
        eB = s.P_LP - s.pic207_sp
        clamp_b = 100.0 / ki7["B"]
        s.i_pic = max(-clamp_b, min(clamp_b, s.i_pic + eB * dt))
        s.pv207b_pct = max(0.0, min(100.0, g.BIAS_207B_PCT + kc7["B"] * eB + ki7["B"] * s.i_pic))
    m_turbine = g._valve_flow(g.K_207B, s.pv207b_pct, s.P_LP, g.P_TURBINE_OUT_BARA,
                              g.P_LP_BARA, g.P_TURBINE_OUT_BARA)
    if s.pic207c_mode == "AUTO":
        eC = s.pic207c_sp - s.P_LP
        s.i_207c = max(0.0, min(100.0 / ki7["C"], s.i_207c + eC * dt))
        s.valve_963_pct = max(0.0, min(100.0, kc7["C"] * eC + ki7["C"] * s.i_207c))
    m_963 = (g._valve_flow(k_963, s.valve_963_pct, s.P_SUP, s.P_LP, *p963)
             + g._valve_flow(k_602, s.hv_329602_pct, s.P_SUP, s.P_LP, *p963))
    m_pic = m_vent + m_turbine

    def ds_lp_at(p, ld, m963):
        if not b70:
            return 0.0
        if hdr:     # 917: 960 joins the header past the drums and boils no drum water
            return m963 * ws.superheat_water_ratio(d.H_963_KJKG, p)
        return (ld * ws.superheat_water_ratio(ws.h_vapour_sat_at_kjkg(s.P_9), p)
                + m963 * ws.superheat_water_ratio(d.H_963_KJKG, p))

    ds_lp = ds_lp_at(s.P_LP, m_ld9, m_963)
    blow = d.BLOWDOWN_KGH / 3600.0 if b70 else 0.0
    ds9 = m_attemper9 if b70 else 0.0
    m_lv503 = m_lv504 = m_flash4 = 0.0
    f9 = f1 = 1.0
    if early:   # B-70 / taps: LV-329503 and LV-329504 at the starting pressures
        lvl503 = D009.level_pct(s.m_d009) if taps else s.lic503_lvl
        op503 = _lic(v1, "LIC-329503", s, "lic503", True, dt, decided, lvl503)
        lvl504 = D001.level_pct(s.m_d001) if taps else s.lic504_lvl
        op504 = _lic(v1, "LIC-329504", s, "lic504", False, dt, decided, lvl504)
        if trim:
            m_lv503 = _lv_trim("LV-329503", op503, m503_des, s.P_9, s.P_LP)
            m_lv504 = _lv_trim("LV-329504", op504, m504_des, g.P_916_BARA, s.P_LP)
        else:
            m_lv503 = _lv_v1(v1, op503, m503_des, s.P_9, s.P_LP, g.P_MP_BARA, g.P_LP_BARA,
                             g._rho_drum_liquid(s.P_9),
                             g.rho_liquid_sat_kgm3(g.tsat_c(g.P_MP_BARA)))
            m_lv504 = _lv_v1(v1, op504, m504_des, g.P_916_BARA, s.P_LP, g.P_916_BARA,
                             g.P_LP_BARA, g.RHO_916, g.RHO_916)
        if taps:
            f9 = _cap(s.m_d009, m_lv502 - m_flash9, ds9 + m_lv503, dt)
            ds9, m_lv503 = ds9 * f9, m_lv503 * f9
            m_attemper9 = ds9
        m_flash4 = m_lv503 * ws.flash_fraction(s.P_9, s.P_LP) if b70 else 0.0
        if taps:
            f1 = _cap(s.m_d001, m_lv503 - m_flash4 + m_lv504, m_hpcc + ds_lp + blow, dt)
            m_hpcc, ds_lp, blow = m_hpcc * f1, ds_lp * f1, blow * f1

    # -- node balances (596-606) --
    residual_d005 = m_supply + ds5 - m_strip - m_vent_hp
    residual_d009 = m_903 + m_flash9 + m_attemper9 - m_9_users - m_ld9
    if hdr:     # 917: the drums' balance on their discharge to the header
        m_917 = users_lp + m_vent + m_turbine - m_ld9
        residual_lp = m_hpcc + m_water + m_963 + ds_lp + m_flash4 - m_917
    else:
        residual_lp = (m_hpcc + m_ld9 + m_water + m_963 + ds_lp + m_flash4 - users_lp - m_vent
                       - m_turbine)

    def _res_mp(p):
        m = g._valve_flow(K_902, s.valve_supply_pct, s.P_SUP, p, g.P_SUP_BARA, g.P_HP_BARA)
        ds = m * ws.superheat_water_ratio(d.H_902_KJKG, p) * f5 if b70 else 0.0
        return m + ds - m_strip - g._valve_flow(k_601, s.hv_vent_hp_pct, p, 1.01325, *p601)

    def _res_9(p):
        if trim:
            m903_p = sv.pv_329205a_kgs(s.valve_admit9_pct, s.P_SUP, p)
            mld_p = sv.pv_329205b_kgs(s.valve_letdown_pct, p, s.P_LP)
        else:
            m903_p = g._valve_flow(g.K_903, s.valve_admit9_pct, s.P_SUP, p, g.P_SUP_BARA,
                                   g.P_MP_BARA)
            mld_p = g._valve_flow(g.K_LD9, s.valve_letdown_pct, p, s.P_LP, g.P_MP_BARA,
                                  g.P_LP_BARA)
        att_p = g.M_ATTEMPER9_DES * (m903_p / max(g.M_903_DES, 1e-12)) * f9
        return m903_p + m_flash9 + att_p - m_9_users - mld_p

    def _res_lp(p):
        if trim:
            mld_p = sv.pv_329205b_kgs(s.valve_letdown_pct, s.P_9, p)
        else:
            mld_p = g._valve_flow(g.K_LD9, s.valve_letdown_pct, s.P_9, p, g.P_MP_BARA,
                                  g.P_LP_BARA)
        water_p = 0.0 if b70 else mld_p * (g.H_G_MP - g.H_G_LP) / (g.H_G_LP - g.H_W)
        m963_p = (g._valve_flow(k_963, s.valve_963_pct, s.P_SUP, p, *p963)
                  + g._valve_flow(k_602, s.hv_329602_pct, s.P_SUP, p, *p963))
        vent_p = g._valve_flow(k_207a, s.pv207a_pct, p, 1.01325, *p207a)
        turb_p = g._valve_flow(g.K_207B, s.pv207b_pct, p, g.P_TURBINE_OUT_BARA,
                               g.P_LP_BARA, g.P_TURBINE_OUT_BARA)
        flash_p = m_lv503 * ws.flash_fraction(s.P_9, p) if b70 else 0.0
        if hdr:
            m917_p = users_lp + vent_p + turb_p - mld_p
            return m_hpcc + water_p + m963_p + ds_lp_at(p, mld_p, m963_p) * f1 + flash_p - m917_p
        return (m_hpcc + mld_p + water_p + m963_p + ds_lp_at(p, mld_p, m963_p) * f1 + flash_p
                - users_lp - vent_p - turb_p)

    relief = {}
    floor_lp = 0.0 if b70 else g.P_LP_MIN_BARA
    for tag, attr, res, fn, cap, k, v_vap, floor in (
            ("SV32951", "P_MP", residual_d005, _res_mp, g.C_MP, 0, n.V_D005_VAP_M3, 0.0),
            ("SV32952", "P_9", residual_d009, _res_9, g.C_9, 1, n.V_D009_VAP_M3, 0.0),
            ("SV32978", "P_LP", residual_lp, _res_lp, g.C_LP, 2, n.V_D001_VAP_M3, floor_lp)):
        p = getattr(s, attr)        # V1 updates the three in turn: the LP step reads the new P_9
        gcond = (res - fn(p + 1.0e-3)) / 1.0e-3
        den = cap + max(gcond, 0.0) * dt
        w = 0.0
        if "relief" in decided:
            w = s.svs[k].vent_kgh(p, p + res * dt / den, ws.tsat_c(p) + 273.15, d.STEAM_MW,
                                  v_vap, dt)
        relief[tag] = w
        setattr(s, attr, max(floor, p + (res - w / 3600.0) * dt / den))

    s.m_supply, s.m_903, s.m_ld = m_supply, m_903, m_ld9
    s.m_flash9, s.m_attemper9, s.m_users9 = m_flash9, m_attemper9, m_9_users
    s.m_963, s.m_water, s.m_vent_hp, s.m_pic = m_963, m_water, m_vent_hp, m_pic
    s.m_vent, s.m_turbine = m_vent, m_turbine

    if not early:   # V1: the two level loops after the pressure step (662-672)
        op503 = _lic(v1, "LIC-329503", s, "lic503", True, dt, decided, s.lic503_lvl)
        m_lv503 = _lv_v1(v1, op503, m503_des, s.P_9, s.P_LP, g.P_MP_BARA, g.P_LP_BARA,
                         g._rho_drum_liquid(s.P_9), g.rho_liquid_sat_kgm3(g.tsat_c(g.P_MP_BARA)))
        op504 = _lic(v1, "LIC-329504", s, "lic504", False, dt, decided, s.lic504_lvl)
        m_lv504 = _lv_v1(v1, op504, m504_des, g.P_916_BARA, s.P_LP, g.P_916_BARA, g.P_LP_BARA,
                         g.RHO_916, g.RHO_916)
        if trim:
            m_lv503 = _lv_trim("LV-329503", op503, m503_des, s.P_9, s.P_LP)
            m_lv504 = _lv_trim("LV-329504", op504, m504_des, g.P_916_BARA, s.P_LP)

    water = {"329D005": m_strip - ds5 - m_lv502,
             "329D009": m_lv502 - m_flash9 - ds9 - m_lv503,
             "322D001": m_lv503 - m_flash4 + m_lv504 - m_hpcc - ds_lp - blow}
    if taps:
        for tag, drum, attr in DRUMS:
            setattr(s, attr, min(getattr(s, attr) + water[tag] * dt, drum.full_kg))
    else:
        _v1_level(v1, s, "lic502", g.MSPAN_502, water["329D005"], dt)
        _v1_level(v1, s, "lic503", g.MSPAN_503, water["329D009"], dt)
        _v1_level(v1, s, "lic504", g.MSPAN_504, water["322D001"], dt)
    s.mass_residual_d005_vapor = residual_d005
    s.mass_residual_d009_vapor = residual_d009
    s.mass_residual_lp_vapor = residual_lp
    s.mass_residual_d005_liquid = water["329D005"]
    s.mass_residual_d009_liquid = water["329D009"]
    s.mass_residual_lp_liquid = water["322D001"]
    s.relief = relief
    return s


# ======================================================================================
# The drivers
# ======================================================================================

V1_FIELDS = ("P_SUP", "P_MP", "P_9", "P_LP", "valve_supply_pct", "valve_admit9_pct",
             "valve_letdown_pct", "valve_963_pct", "hv_329602_pct", "hv_vent_hp_pct", "m_supply",
             "m_903", "m_flash9", "m_attemper9", "m_users9", "m_ld", "m_963", "m_water",
             "m_vent_hp", "m_pic", "i_pic", "pic204_mode", "pic204_sp", "i_204", "pic205_mode",
             "pic205_sp", "pic207_mode", "pic207_sp", "master207_on", "master207_sp",
             "pic207a_mode", "pic207a_sp", "pic207c_mode", "pic207c_sp", "pv207a_pct",
             "pv207b_pct", "i_207a", "i_207c", "m_vent", "m_turbine", "lic502_mode", "lic502_sp",
             "lic502_lvl", "lic502_op", "lic502_ep", "lic503_mode", "lic503_sp", "lic503_lvl",
             "lic503_op", "lic503_ep", "lic504_mode", "lic504_sp", "lic504_lvl", "lic504_op",
             "lic504_ep", "mass_residual_d005_vapor", "mass_residual_d009_vapor",
             "mass_residual_lp_vapor", "mass_residual_d005_liquid", "mass_residual_d009_liquid",
             "mass_residual_lp_liquid")


def scenario(v1, decided, k0=5, n_ticks=1200, **over):
    """Inputs per tick: the design until ``k0``, then ``over`` (factors on ``strip``,
    ``raise``, ``users_9``, ``users_lp``; ``trip``)."""
    base = design_inputs(v1, decided)
    step = dict(base)
    for key in ("strip", "raise", "users_9", "users_lp"):
        if key in over:
            step[key] = base[key] * over[key]
    trip = over.get("trip", False)
    return [(dict(step), trip) if k >= k0 else (dict(base), False) for k in range(n_ticks)]


def port_draws(x) -> SteamDraws:
    """The port's draws for a tick's inputs: the users as one sum per header."""
    return replace(SteamDraws(), strip_kgh=x["strip"], raise_kgh=x["raise"],
                   users_9_kgh={"all": x["users_9"]}, users_lp_kgh={"all": x["users_lp"]})


def _assert_port(s, net, k):
    """The port's state ``==`` the transcription's, on tick ``k``."""
    pairs = [(s.P_MP, net.p_hp_bara), (s.P_9, net.p_9_bara), (s.P_LP, net.p_lp_bara),
             (s.valve_supply_pct, net.pic_329204.op_pct), (s.i_204, net.pic_329204.i_bar_s),
             (s.pic204_sp, net.pic_329204.sp_bara), (s.hv_vent_hp_pct, net.hv_329601.hic_pct),
             (s.valve_admit9_pct, net.pic_329205.op_a_pct),
             (s.valve_letdown_pct, net.pic_329205.op_b_pct),
             (s.pv207a_pct, net.pic_329207.legs["A"].op_pct), (s.i_207a,
                                                                net.pic_329207.legs["A"].i_bar_s),
             (s.pv207b_pct, net.pic_329207.legs["B"].op_pct), (s.i_pic,
                                                               net.pic_329207.legs["B"].i_bar_s),
             (s.valve_963_pct, net.pic_329207.legs["C"].op_pct),
             (s.i_207c, net.pic_329207.legs["C"].i_bar_s),
             (s.lic502_op, net.lic_329502.op_pct), (s.lic502_ep, net.lic_329502.e_prev),
             (s.lic503_op, net.lic_329503.op_pct), (s.lic503_ep, net.lic_329503.e_prev),
             (s.lic504_op, net.lic_329504.op_pct), (s.lic504_ep, net.lic_329504.e_prev),
             (s.m_d005, net.m_d005_kg), (s.m_d009, net.m_d009_kg), (s.m_d001, net.m_d001_kg)]
    for i, (a, b) in enumerate(pairs):
        assert a == b, (k, i, a, b)


def run_both(v1, script, decided=ALL, check=True, act=None):
    """The transcription and the port side by side; returns both and per tick (transcription's
    state, port's result). ``act(k, s, net)`` acts on both before tick ``k``. Without "B-68" the
    transcription's LP users stay V1's boot constant whatever the script draws."""
    s = _v1_state(v1, decided, script[0][0])
    net = SteamNetwork(**v1_butterflies())
    out = []
    for k, (x, trip) in enumerate(script):
        if act is not None:
            act(k, s, net)
        if "B-68" in decided:
            s.m_users_lp = x["users_lp"]
        _v1_steam(v1, s, DT, x, decided, trip)
        r = net.step(port_draws(x), DT, trip)
        out.append((dict(vars(s)), r))
        if check:
            _assert_port(s, net, k)
    return s, net, out


# ======================================================================================
# The tests
# ======================================================================================

def test_the_valve_law_and_the_drum_relations_are_v1s(v1):
    for args in ((13.99, 50.0, 25.0, 19.7, 25.0, 19.7), (18.5, 100.0, 19.7, 1.01325),
                 (2.0, 37.0, 25.0, 3.1, 25.0, 5.01325), (3.0, 0.0, 5.0, 1.01325),
                 (13.1, 61.0, 6.2, 3.9, 5.01325, 3.9), (2.0, 120.0, 9.0, 9.5, 9.0, 5.01325)):
        assert sv.steam_valve_kgs(*args) == v1._valve_flow(*args), args
    for p in (0.001, 0.5, 4.4, 5.01325, 9.0, 19.7, 25.0):
        assert ws.rho_drum_liquid_kgm3(p) == v1._rho_drum_liquid(p)
    for p in (1.0, 4.4, 5.01325, 9.0, 19.7):
        assert ws.rho_vapour_sat_kgm3(p) == v1._rho_vapour_sat(p)
        assert ws.vapour_capacitance_kg_bar(7.3, p) == v1._header_capacitance(7.3, p)


def test_the_constants_are_v1s(v1):
    """The geometry, the capacitances, the spans and the anchors the port keeps, ``==`` V1's;
    the ones it decides, both values."""
    assert (n.C_MP_KG_BAR, n.C_LP_KG_BAR, n.C_9_KG_BAR) == (v1.C_MP, v1.C_LP, v1.C_9)
    assert (n.MSPAN_502_KG, n.MSPAN_503_KG, n.MSPAN_504_KG) == (v1.MSPAN_502, v1.MSPAN_503,
                                                                 v1.MSPAN_504)
    assert (n.V_D001_VAP_M3, n.V_D005_VAP_M3, n.V_D009_VAP_M3) == (
        v1.V_D001_VAP_M3, v1.V_D005_VAP_M3, v1.V_D009_VAP_M3)
    assert (n.K_207B, n.M_TURBINE_DES_KGS, n.BIAS_207B_PCT, n.DB_LP_BAR, n.K_PIC_9) == (
        v1.K_207B, v1.M_TURBINE_DES, v1.BIAS_207B_PCT, v1.DB_LP, v1.K_PIC_9)
    assert (d.P_HP_BARA, d.P_MP_BARA, d.P_LP_BARA, d.P_SUP_BARA, d.P_TURBINE_OUT_BARA) == (
        v1.P_HP_BARA, v1.P_MP_BARA, v1.P_LP_BARA, v1.P_SUP_BARA, v1.P_TURBINE_OUT_BARA)
    assert (d.P_916_BARA, d.RHO_916_KGM3, d.STEAM_MW, d.STEAM_GAMMA) == (
        v1.P_916_BARA, v1.RHO_916, v1.STEAM_MW, v1.STEAM_GAMMA)
    assert d.DS9_DES_KGH / 3600.0 == pytest.approx(v1.M_ATTEMPER9_DES, rel=1e-15)
    assert (n.K_902, v1.K_902) == (pytest.approx(13.9938, abs=1e-4),
                                   pytest.approx(18.5019, abs=1e-4))
    assert (n.K_HV601, v1.K_902) == (pytest.approx(0.5644, abs=1e-4),
                                     pytest.approx(18.5019, abs=1e-4))
    assert (n.K_963, v1.K_963, n.K_207A, v1.K_207A) == (
        pytest.approx(2.4653, abs=1e-4), 2.0, pytest.approx(12.7672, abs=1e-4), 3.0)
    assert (d.FLASH9_FRACTION, v1.FLASH9_FRACTION) == (pytest.approx(0.080326, abs=1e-6),
                                                       pytest.approx(0.060754, abs=1e-6))


@pytest.mark.parametrize("name, over", [
    ("design", {}),
    ("stripper -20 %", {"strip": 0.8}),
    ("HPCC raising -20 %", {"raise": 0.8}),
    ("9-bar users -40 %", {"users_9": 0.6}),
    ("everything", {"strip": 1.1, "raise": 0.9, "users_9": 1.2, "users_lp": 1.05}),
])
def test_the_transcription_is_v1s_executed_step(v1, name, over):
    """Every switch off: the transcription ``==`` V1's executed ``step_steam`` on every field of
    its state, on every tick for two minutes (V1's ``M_USERS_LP`` and ``M_504_DES`` set as its
    boot sets them, ``main.py`` 12329-12331)."""
    script = scenario(v1, frozenset(), **over)
    st = v1.SteamState()
    v1.M_USERS_LP = script[0][0]["users_lp"] / 3600.0
    v1.M_504_DES = max(script[0][0]["raise"] / 3600.0 - v1.M_503_DES, 0.0)
    s = _v1_state(v1, frozenset(), script[0][0])
    for k, (x, _) in enumerate(script):
        v1.step_steam(st, DT, x["strip"] / 3600.0, x["raise"] / 3600.0, x["users_9"] / 3600.0)
        _v1_steam(v1, s, DT, x, frozenset())
        for f in V1_FIELDS:
            assert getattr(s, f) == getattr(st, f), (name, k, f)


@pytest.mark.parametrize("name, n_ticks, over", [
    ("design", 600, {}),
    ("stripper -20 %", 1800, {"strip": 0.8}),
    ("HPCC raising -20 %", 1800, {"raise": 0.8}),
    ("LP users +10 %", 1800, {"users_lp": 1.10}),
    ("9-bar users lost", 1200, {"users_9": 0.0}),
    ("trip 21.2", 1800, {"strip": 0.0, "raise": 0.6, "users_lp": 0.7, "trip": True}),
])
def test_the_port_is_the_switched_transcription(v1, name, n_ticks, over):
    """Every switch on: the port's state ``==`` the transcription's on every tick."""
    run_both(v1, scenario(v1, ALL, n_ticks=n_ticks, **over))


def test_master_and_hand_valve_steps_are_the_transcriptions(v1):
    """The master set point to 4.4 bar a, then HV-329602 opened by hand to 20 %."""
    script = scenario(v1, ALL, n_ticks=1500)
    s = _v1_state(v1, ALL, script[0][0])
    net = SteamNetwork(**v1_butterflies())
    for k, (x, trip) in enumerate(script):
        if k == 5:
            s.master207_sp = net.pic_329207.master_sp_bara = 4.4
        if k == 700:
            s.hv_329602_pct = net.hv_329602_pct = 20.0
        s.m_users_lp = x["users_lp"]
        _v1_steam(v1, s, DT, x, ALL, trip)
        net.step(port_draws(x), DT, trip)
        _assert_port(s, net, k)
