"""Behaviour of 323E010 / 323F010 — `ureasim.units.recirc.pre_evaporator`.

Equivalence with V1 is proven tick by tick in
`tests/equivalence/test_pre_evaporator_equivalence.py`. This file pins what stage 3 DOES: the
bubble point it relaxes to on the live PT-323204 (handoff B-22, decided 2026-10-15; V1's design
vacuum asserted both ways in the equivalence test), the heel decided on its barometric leg (B-29),
and the held liquor boiling past its bubble point at the live vacuum (B-24, decided 2026-10-02).
The scenarios whose numbers were measured on V1's barometric leg, the separator's pressure in its
drive, run on it (``own_head_leg=False``); the drain on the separator's own head (handoff B-119,
option (b), decided 2026-10-30) is pinned on the same scenarios in section 6.
Every number here was
measured on the module before it was written down, on the decided chest anchor and cascade gains
(2026-09-30, As-Built §XL.1-2) and on PFD 314 and 319 closed on their urea (B-20, decided
2026-10-10), with HV-323605 on Metso's Neldisc from its 64.08 % design stroke (decided 2026-10-17).
A pinched or opened HV-323605 is restated as the same fraction of its design capacity V1's strokes
were of its 50 %: what moves is the trim's xT, 0.38, which chokes the valve earlier.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_323 as d
from ureasim.data.design_point import R323_M317_DES, R323_M319_DES
from ureasim.data.unit_329 import P_LP_BARA
from ureasim.control.valve import cv_fraction, stroke_for_cv_fraction
from ureasim.data.control_valves import PV_329208
from ureasim.units import liquor_stage
from ureasim.units.recirc import pre_evaporator as pe

NO_BLOW = (0.0, 0.0, None)

#: PV-329208's stroke at which its vendor trim admits 20 % more steam than at its design stroke.
PV_329208_PLUS_20_PCT = 100.0 * stroke_for_cv_fraction(
    1.2 * cv_fraction(d.PV_329208_OP_DES_PCT / 100.0, PV_329208.characteristic),
    PV_329208.characteristic)


def _tic():
    """TIC-323012 on the tuning these measurements were taken on, the 2026-09-30 stand-in
    (TIC-323007's row, 2.00 and 500 s, on TIC-323012's spans); its own row in the plant DCS,
    1.00 and 300 s (decided 2026-10-28), has its own test."""
    tic = pe.tic_323012()
    tic.Kc, tic.Ti = 2.00 * d.PT_329208_SPAN_BAR / d.TT_323012_SPAN_C, 500.0
    return tic


def _hv(fraction: float) -> float:
    """HV-323605's stroke [%] at which its Neldisc passes ``fraction`` of its design capacity."""
    return 100.0 * stroke_for_cv_fraction(
        fraction * cv_fraction(d.HIC_323605_DES_PCT / 100.0, d.HV605_CHAR), d.HV605_CHAR)


def _run(seconds: float, dt: float = 1.0, hic: float = d.HIC_323605_DES_PCT,
         p_e002: float = d.P_324E002_DES_BARA, p_lp: float = P_LP_BARA, sp: float = None,
         pic_man: float = None, blow: tuple = NO_BLOW, trace: float = None,
         m319: float = R323_M319_DES, own_head_leg: bool = True):
    """Run stage 3 alone on design boundaries; return the last result (and the one at
    `trace` seconds, if asked)."""
    sep = pe.PreEvaporator(own_head_leg=own_head_leg)
    tic, pic = _tic(), pe.pic_329208()
    if sp is not None:
        tic.sp = sp
    if pic_man is not None:
        pic.set_mode("MAN")
        pic.op = pic_man
    r = at = None
    for k in range(1, int(round(seconds / dt)) + 1):
        r = sep.step(tic, pic, m319, d.F004_T_SP_C, dict(d.W_S319), *blow, hic, p_lp,
                     p_e002, dt)
        if trace is not None and abs(k * dt - trace) < 1e-9:
            at = r
    return (r, at) if trace is not None else r


# ======================================================================================
# 1. The design point
# ======================================================================================

def test_tic_323012_on_its_dcs_row_holds_its_set_point():
    """Its faceplate in the plant DCS, 1.00 and 300 s on 0-160 C and PT-329208's 0-6 bar
    (decided 2026-10-28): a set point raised to 101 C is met as the stand-in met it, 99.48 C at ten
    minutes and 100.98 C at two hours — the liquor's own bubble point at the live vacuum (B-24)
    — with no overshoot."""
    tic, pic = pe.tic_323012(), pe.pic_329208()
    assert (tic.Kc, tic.Ti) == (1.00 * 6.0 / 160.0, 300.0)
    tic.sp = 101.0
    sep, temps = pe.PreEvaporator(own_head_leg=False), []
    for _ in range(7200):
        temps.append(sep.step(tic, pic, R323_M319_DES, d.F004_T_SP_C, dict(d.W_S319), *NO_BLOW,
                              d.HIC_323605_DES_PCT, P_LP_BARA, d.P_324E002_DES_BARA, 1.0).t_c)
    assert (temps[599], temps[-1]) == (pytest.approx(99.476, abs=1e-3),
                                       pytest.approx(100.9825, abs=1e-4))
    assert max(temps) < 101.0


def test_the_first_design_tick_is_the_pfd():
    r = _run(0.1, dt=0.1)
    assert (r.t_c, r.p_bara, r.t_bub_c, r.q_relax_kw) == (d.F010_T_SP_C, d.F010_P_BARA,
                                                        d.F010_T_SP_C, 0.0)
    assert (r.chest_p_bara, r.q_e010_kw, r.q_avail_kw) == (d.E010_PCHEST_DES_BARA,
                                                          d.E010_Q_DES_KW, d.QEVAP_DES_KW)
    assert r.m_evap_kgh == d.MEVAP_DES_KGH and r.pull_kgh == d.MEVAP_DES_KGH
    assert r.m_317_kgh == R323_M317_DES
    assert r.level_pct == d.F010_LVL_SP_PCT
    assert r.vapour_domain == "electrolyte_gamma_phi" and r.mw_vap == pe.MW_VAP_DES


def test_pfd_790_carries_its_entrained_liquor():
    """PFD 790 lists 0.14 mol % urea, which cannot evaporate at 99 C: 0.696 % of the overhead
    is the separator's own liquor, 84 kg/h, and the vapour itself carries none. PFD 319 closed on
    its urea (B-20, decided 2026-10-10) brings 6.3 kg/h more urea than the table's row, which the
    carryover closes (0.611 %, 73 kg/h, on the table's rows)."""
    r = _run(0.1, dt=0.1)
    assert r.y_vap["Urea"] == 0.0
    assert d.F010_LIQUOR.anchor.entrain == pytest.approx(0.006959, abs=1e-6)
    assert r.y_790["Urea"] == pytest.approx(d.F010_LIQUOR.anchor.entrain * d.W_S317["Urea"],
                                            rel=1e-12)


def test_the_design_seed_carries_a_biuret_remainder():
    """The PFD rows put 4.85 kg/h more biuret into the stage than out of it, and a negative
    formation extent is refused, so the anchor closes urea alone and the design seed is not a
    fixed point: biuret climbs from the first tick and settles 0.005 points high within an
    hour, while the separator holds 99.0001 C (As-Built §XXX.2) and the urea 80.0004 %, where V1's
    dips to 79.9995 %. On the rows closed on their urea (B-20, decided 2026-10-10) the liquor
    relaxes to its bubble point at the live PT-323204 (B-22, decided 2026-10-15), 0.4599 bar a,
    and boils nothing of its own (0.04 kg/h and 79.9998 % on V1's HV-323605 trim, 0.87 on the
    design vacuum's bubble point, B-24)."""
    r1 = _run(0.1, dt=0.1)
    assert r1.xi_kmolh == 0.0 and r1.w["Biuret"] > d.W_S317["Biuret"]
    assert r1.m_boil_kgh == 0.0
    r = _run(3600.0)
    assert r.w["Biuret"] * 100.0 == pytest.approx(0.42518, abs=1e-5)
    assert r.w["Urea"] * 100.0 == pytest.approx(80.00038, abs=1e-5)
    assert r.t_c == pytest.approx(99.0001, abs=1e-4)
    assert r.m_boil_kgh == pytest.approx(0.0, abs=0.01)


# ======================================================================================
# 2. The steam chest, solved every tick
# ======================================================================================

@pytest.mark.parametrize("p_lp, t_c, chest, pic_op, boil", [
    (4.5, 99.0473, 2.5070, 29.284, 11.65), (4.0, 99.1059, 2.5160, 31.876, 32.14)])
def test_a_sagging_lp_header_is_answered_by_pv_329208(p_lp, t_c, chest, pic_op, boil):
    """The chest pressure is solved from the valve admission against the wall's condensation
    each tick; TIC-323012 and PIC-329208 open PV-329208 to hold it. Half an hour on, the chest is
    back above its 2.5 bar a anchor and the liquor is coming down off its overshoot — standing
    above its live bubble point, it boils 12 and 32 kg/h of its own (B-24; PV-329208 on its
    vendor trim, decided 2026-10-15 — 76 and 188 on V1's linear valve; 15 and 39 with HV-323605 on
    V1's trim; the bubble point on the live PT-323204, B-22). On V1's anchor,
    gains and 40-sweep flash budget the liquor sat at 99.0414 and 98.8722 C, on a 1.76 bar a
    chest."""
    r = _run(1800.0, p_lp=p_lp, own_head_leg=False)
    assert (r.t_c, r.chest_p_bara, r.pic_op_pct, r.m_boil_kgh) == (
        pytest.approx(t_c, abs=1e-4), pytest.approx(chest, abs=1e-4),
        pytest.approx(pic_op, abs=1e-3), pytest.approx(boil, abs=0.01))


# ======================================================================================
# 3. Handoff B-24, decided 2026-10-02: the held liquor boils past its bubble point
# ======================================================================================

def test_less_steam_dilutes_the_product():
    """TIC-323012 at 97 C: less duty, less water off. The smaller overhead lets HV-323605 pull
    PT-323204 down to 0.439 bar a, where 97 C is the liquor's own bubble point: it relaxes to it
    (B-22, decided 2026-10-15) and evaporates 11 266 kg/h on the duty branch, boiling nothing past
    it — 79.37 % urea (0.441 bar a, 11 116 kg/h and 79.24 % with HV-323605 on V1's trim). (On the
    design vacuum's bubble point it evaporated 10 962 and boiled 154 kg/h past its live one, B-24,
    to 79.24 %; V1 held it at 78.97 %.)"""
    r = _run(7200.0, sp=97.0, own_head_leg=False)
    assert r.m_evap_kgh == pytest.approx(11266.1, abs=0.1)
    assert r.m_boil_kgh == 0.0
    assert r.p_bara == pytest.approx(0.43911, abs=1e-5)
    assert r.t_bub_c == pytest.approx(97.018, abs=1e-3)
    assert r.w["Urea"] * 100.0 == pytest.approx(79.369, abs=1e-3)


@pytest.mark.parametrize("kw, t_c, boil, urea", [
    (dict(sp=101.0), 100.9825, 673.71, 80.580),
    (dict(pic_man=PV_329208_PLUS_20_PCT), 102.7601, 1213.51, 81.054),
])
def test_more_steam_concentrates_the_product_b24(kw, t_c, boil, urea):
    """Handoff B-24, decided 2026-10-02. The cap still holds V1's evaporation at the design
    fraction of the feed, but the surplus no longer superheats the liquor: past its bubble point
    at the live vacuum the holdup boils it off, the product concentrates, and the liquor holds
    within 0.08 K of its bubble point. TIC-323012 at 101 C: 674 kg/h more and 80.58 % urea (V1:
    80.00 %, 3.9 K superheated); PV-329208 in MAN where its vendor trim admits 20 % more steam than
    at its 27.22 % design stroke, 30.47 % (V1's linear valve ten points above its 49.87 %): 1214
    kg/h more, 81.05 % and 102.8 C (V1: 106.5 C, 12.0 K superheated). On the Neldisc HV-323605's
    pull grows less with the separator's pressure than on V1's trim (839 and 1336 kg/h there), so
    the extra vapour raises PT-323204, and the bubble point with it, further."""
    r = _run(7200.0, own_head_leg=False, **kw)
    assert r.m_evap_kgh == d.MEVAP_DES_KGH
    assert r.m_boil_kgh == pytest.approx(boil, abs=0.01)
    assert r.w["Urea"] * 100.0 == pytest.approx(urea, abs=1e-3)
    assert r.t_c == pytest.approx(t_c, abs=1e-4)
    assert 0.0 < r.t_c - liquor_stage.bubble_t(d.F010_LIQUOR, r.w, r.p_bara) < 0.08


# ======================================================================================
# 4. The vacuum: PT-323204 solved, and the bubble point on it (handoff B-22, decided 2026-10-15)
# ======================================================================================

def test_the_barometric_leg():
    """The design drain at the design state; losing the vacuum raises it 43 %; half the level
    lowers it 3 %. The leg can hold the design drain up to 0.524 bar a with the separator
    empty — above that nothing in the separator can stop it draining."""
    assert pe.barometric_leg_kgh(d.F010_M_DES_KG, d.F010_P_BARA) == R323_M317_DES
    assert pe.barometric_leg_kgh(d.F010_M_DES_KG, 1.01325) / R323_M317_DES == \
        pytest.approx(1.4339, abs=1e-4)
    assert pe.barometric_leg_kgh(0.5 * d.F010_M_DES_KG, d.F010_P_BARA) / R323_M317_DES == \
        pytest.approx(0.9691, abs=1e-4)
    assert pe.barometric_leg_kgh(0.0, 0.5238) == pytest.approx(R323_M317_DES, rel=1e-4)


def test_a_stopped_drain_takes_the_separator_to_its_heel_and_makes_nothing():
    """Handoff B-29, decided: the 323F004 drain stopped on 300 kg. The chest's heat, no longer
    taken by a feed, boils the held liquor — 9.1 t/h at once, 9.9 at 1 s — and it concentrates
    toward 92 % (B-24) as the leg empties the separator to its 1 kg heel in 12.5 s (V1: 15.1 s,
    the liquor superheating instead); then the leg passes what arrives, PFD 331 less the
    evaporation, and nothing below the heel boils. Nothing is made (V1's leg passed the floor's
    kilogram every tick, 36 t/h at this step)."""
    sep = pe.PreEvaporator(own_head_leg=False)
    tic, pic = _tic(), pe.pic_329208()
    sep.m_kg, dt, created, heel_s = 300.0, 0.1, 0.0, None
    for k in range(1, 601):
        m_pre = sep.m_kg
        r = sep.step(tic, pic, 0.0, d.F004_T_SP_C, dict(d.W_S319), *NO_BLOW,
                     d.HIC_323605_DES_PCT, P_LP_BARA, d.P_324E002_DES_BARA, dt)
        created += (sep.m_kg - m_pre) - (r.feed_kgh + r.m_331_kgh - r.m_evap_kgh
                                         - r.m_boil_kgh - r.m_317_kgh) / 3600.0 * dt
        if k == 1:
            assert r.m_boil_kgh == pytest.approx(9120.0, abs=0.1)
        if heel_s is None and sep.m_kg <= d.F010_M_FLOOR_KG + 1e-9:
            heel_s = round(k * dt, 6)
    assert heel_s == 12.5
    assert sep.m_kg == pytest.approx(d.F010_M_FLOOR_KG, abs=1e-9)
    assert r.m_boil_kgh == 0.0
    assert r.m_317_kgh == pytest.approx(r.m_331_kgh - r.m_evap_kgh, rel=1e-9)
    assert abs(created) < 1e-9


def _pinched(hic: float, seconds: float = 7200.0, own_head_leg: bool = True) -> dict:
    """HV-323605 held at ``hic`` from the design: the results at the times the tests read, and the
    lowest level."""
    sep = pe.PreEvaporator(own_head_leg=own_head_leg)
    tic, pic = _tic(), pe.pic_329208()
    at, lowest = {}, 100.0
    for k in range(1, int(seconds) + 1):
        r = sep.step(tic, pic, R323_M319_DES, d.F004_T_SP_C, dict(d.W_S319), *NO_BLOW, hic,
                     P_LP_BARA, d.P_324E002_DES_BARA, 1.0)
        lowest = min(lowest, r.level_pct)
        if k in (60, 300, int(seconds)):
            at[k] = r
    return at, lowest


def test_pinching_hic_323605_raises_the_boiling_point_and_cuts_the_evaporation():
    """Handoff B-22, decided 2026-10-15: the liquor relaxes to its bubble point at the live
    PT-323204. HV-323605 at half its design capacity, 32.04 % on the Neldisc (V1's 25 %): PT-323204
    0.758 bar a after a minute, where the liquor boils at 113.3 C; it heats from 99 to 102.1 C and
    evaporates 10.03 t/h, and by 300 s it stands on its bubble point, 104.9 C, evaporating 7.8 t/h,
    TIC-323012 cutting the chest. After two hours the separator holds 0.538 bar a and 99.0 C,
    evaporating 7.21 t/h, 76.09 % urea, the level never below 34.9 %. (On V1's trim: 0.682 bar a
    and 101.5 C after a minute, 0.530 bar a, 7.65 t/h and 76.43 % after two hours, the level above
    38 %; on V1's design-vacuum bubble point the liquor stayed at 99.06 C 14 K below its boiling
    point, evaporating 12 t/h, and the leg drained the separator dry.) The plant's manual
    (`References/323F004 323E010 323F010.md` §5) has the steam cut back as the vacuum decays."""
    at, lowest = _pinched(_hv(0.5), own_head_leg=False)
    r60, r300, r = at[60], at[300], at[7200]
    assert (r60.p_bara, r60.t_c, r60.t_bub_c) == (pytest.approx(0.7581, abs=1e-4),
                                                  pytest.approx(102.129, abs=1e-3),
                                                  pytest.approx(113.277, abs=1e-3))
    assert r60.m_evap_kgh == pytest.approx(10030.9, abs=0.1)
    assert (r300.t_c, r300.m_evap_kgh) == (pytest.approx(104.892, abs=1e-3),
                                           pytest.approx(7797.2, abs=0.1))
    assert (r.p_bara, r.m_evap_kgh, r.w["Urea"] * 100.0) == (
        pytest.approx(0.5381, abs=1e-4), pytest.approx(7206.0, abs=0.1),
        pytest.approx(76.089, abs=1e-3))
    assert lowest > 34.9


def test_hic_323605_nearly_shut_pins_the_pressure_at_its_clamp_until_the_evaporation_falls():
    """At a fifth of its design capacity, 12.82 % on the Neldisc (V1's 10 %), the valve cannot
    pass the overhead: PT-323204 sits on its 1.0 bar a clamp, the vapour the separator makes beyond
    the valve's 5.30 t/h lost there — choked, where V1's trim passed 6.31 — while the liquor heats
    toward its 121 C bubble point and its evaporation falls, 8.97 t/h after a minute. Within five
    minutes the evaporation is under what the valve passes and the pressure leaves the clamp,
    0.863 bar a at 300 s; after an hour 0.628 bar a, 3.44 t/h, 73.28 % urea and the level at 2.4 %,
    still falling: the choked valve holds the separator above its design vacuum, and the leg drains
    it to its heel at about 5000 s (V1's trim settles at 0.614 bar a, 3.80 t/h, the level at
    6.5 %). (On V1's design-vacuum bubble point the evaporation held 12 t/h at the clamp.) At the
    heel the species step is not stable — handoff B-98."""
    at, lowest = _pinched(_hv(0.2), 3600.0, own_head_leg=False)
    r60, r300, r = at[60], at[300], at[3600]
    assert r60.p_bara == d.F010_P_MAX_BARA
    assert (r60.pull_kgh, r60.m_evap_kgh) == (pytest.approx(5301.8, abs=0.1),
                                              pytest.approx(8972.1, abs=0.1))
    assert r300.p_bara == pytest.approx(0.8632, abs=1e-4)
    assert (r.p_bara, r.m_evap_kgh, r.w["Urea"] * 100.0) == (
        pytest.approx(0.6282, abs=1e-4), pytest.approx(3442.7, abs=0.1),
        pytest.approx(73.283, abs=1e-3))
    assert r.level_pct == pytest.approx(2.40, abs=0.01) == lowest


def _heel(seconds: int, backward: bool, monkeypatch,
          own_head_leg: bool = False) -> tuple[int, dict]:
    """HV-323605 at a fifth of its design capacity, on the port's species step or V1's explicit
    one: the first tick at the 1 kg heel, and the results at 5280, 5400, 7199 and 7200 s."""
    if not backward:
        explicit = liquor_stage.advance_species
        monkeypatch.setattr(pe.liquor_stage, "advance_species",
                            lambda *a, **k: explicit(*a, **k, backward=False))
    sep = pe.PreEvaporator(own_head_leg=own_head_leg)
    tic, pic = _tic(), pe.pic_329208()
    heel, at = None, {}
    for k in range(1, seconds + 1):
        r = sep.step(tic, pic, R323_M319_DES, d.F004_T_SP_C, dict(d.W_S319), *NO_BLOW, _hv(0.2),
                     P_LP_BARA, d.P_324E002_DES_BARA, 1.0)
        if heel is None and r.m_kg < d.F010_M_FLOOR_KG + 1e-9:
            heel = k
        if k in (5280, 5400, 7199, 7200):
            at[k] = r
    monkeypatch.undo()
    return heel, at


def test_at_its_heel_the_separator_holds_the_liquor_that_passes_it_b98_b101(monkeypatch):
    """Handoffs B-98 and B-101, decided 2026-10-17. HV-323605 at a fifth of its design capacity:
    the leg drains 323F010 to its 1 kg heel at 5290 s, where 99 t/h passes the heel, 27.5 kg on
    each 1 s tick. V1's explicit species step drains each species at the old holdup's fraction and
    floors water and urea at zero: the liquor reads 0.000 % urea and a 372.5 C bubble point. The
    backward step, taken where the drain and the vapour pass more than the stage holds — from
    5281 s, the same to the bit until then — draws both at the step's end composition: 73.31 % urea
    at 5400 s, and at two hours 79.77 / 80.03 % on alternate ticks, the throughflow's own 80.07 %
    within 0.3 points. (The drain alone backward rang 74.53 / 75.88 %; what alternates now is the
    vapour's composition, which the stage evaluates on the liquor at the start of the tick.)"""
    heel, ours = _heel(7200, True, monkeypatch)
    v1_heel, theirs = _heel(5400, False, monkeypatch)
    assert heel == v1_heel == 5290
    assert ours[5280] == theirs[5280]
    assert theirs[5400].w["Urea"] == 0.0
    assert theirs[5400].t_bub_c == pytest.approx(372.48, abs=0.01)
    r = ours[5400]
    assert (r.w["Urea"] * 100.0, r.m_317_kgh) == (pytest.approx(73.309, abs=1e-3),
                                                 pytest.approx(99049.3, abs=0.1))
    assert (ours[7199].w["Urea"] * 100.0, ours[7200].w["Urea"] * 100.0) == (
        pytest.approx(80.031, abs=1e-3), pytest.approx(79.767, abs=1e-3))
    assert ours[7200].m_317_kgh == pytest.approx(92748.9, abs=0.1)
    assert ours[7200].p_bara == d.F010_P_MAX_BARA


def test_a_deeper_vacuum_boils_the_liquor_down_to_its_live_bubble_point_b24():
    """HV-323605 opened to 1.6 times its design capacity, 79.09 % on the Neldisc (V1's 80 %):
    PT-323204 falls, and the liquor, standing above its bubble point at the deeper vacuum, boils
    (handoff B-24, decided 2026-10-02) — 1522 kg/h after a minute, at 94.85 C and 0.385 bar a.
    TIC-323012 brings it back to 99 C, which at the vacuum the boil-off holds, 0.404 bar a, is the
    bubble point of an 82.91 % liquor: after two hours the holdup boils 3288 kg/h of its own and the
    level sits at 78 % (on V1's trim 1325 kg/h at 95.38 C after a minute; 0.410 bar a, 2936 kg/h,
    82.58 % and 75.6 % after two hours). V1 (B-22's design-vacuum bubble point and B-24's cap) held
    the overhead at the design split, the liquor 3.8 K superheated at 0.3825 bar a, and the level
    climbed past its span to 121.5 %."""
    r, r60 = _run(7200.0, hic=_hv(1.6), trace=60.0, own_head_leg=False)
    assert (r60.t_c, r60.p_bara, r60.m_boil_kgh) == (
        pytest.approx(94.848, abs=1e-3), pytest.approx(0.3849, abs=1e-4),
        pytest.approx(1522.0, abs=0.1))
    assert r.p_bara == pytest.approx(0.40424, abs=1e-5)
    assert r.level_pct == pytest.approx(77.73, abs=0.01)
    assert r.m_evap_kgh == d.MEVAP_DES_KGH
    assert r.m_boil_kgh == pytest.approx(3287.54, abs=0.01)
    assert r.w["Urea"] * 100.0 == pytest.approx(82.914, abs=1e-3)
    assert 0.0 < r.t_c - liquor_stage.bubble_t(d.F010_LIQUOR, r.w, r.p_bara) < 0.05


# ======================================================================================
# 5. LV-323505 blowing through
# ======================================================================================

def test_lv323505_gas_adds_to_the_vapour_space_and_is_passed_on_by_share():
    """323F004 vapour through an uncovered LV-323505 enters this dome: the pressure rises to
    pass it, and the share of HV-323605's flow that is that gas goes to 324E002 with its own
    composition."""
    blow = (300.0, 300.0 / 22.0, dict(d.F004_LIQUOR.anchor.y))
    r1 = _run(0.1, dt=0.1, blow=blow)
    kgh, y = r1.blowthrough_share
    assert kgh == r1.pull_kgh * 300.0 / (r1.m_evap_kgh + 300.0) and y is blow[2]
    r = _run(60.0, blow=blow)
    assert r.p_bara == pytest.approx(0.46560, abs=1e-5)
    assert r.pull_kgh == pytest.approx(12149.7, abs=0.1)


def test_pv_329208_on_its_vendor_trim_holds_the_chest_on_a_falling_header():
    """Decision 108's class, applied 2026-10-15: PV-329208 on Metso's DN 250 balanced Neldisc from
    its 27.22 % design stroke, where V1 runs it linear from 49.87 % (the harness proves V1's ==).
    The LP header 10 % down for five minutes: V1's valve opens to 54.7 %, the chest at 2.3971 bar a
    and the separator at 98.188 C; the Neldisc, at 29.3 %, holds the chest at 2.5122 and the
    separator at 98.944 C (both on the live PT-323204's bubble point, B-22, and HV-323605 on its
    Neldisc; 2.3934 / 98.258 and 2.5039 / 98.878 with HV-323605 on V1's trim)."""
    def run(chest):
        sep = pe.PreEvaporator(chest=chest, own_head_leg=False)
        tic, pic = _tic(), pe.pic_329208(chest)
        for _ in range(300):
            sep.step(tic, pic, R323_M319_DES, d.F004_T_SP_C, dict(d.W_S319), *NO_BLOW,
                     d.HIC_323605_DES_PCT, 0.9 * P_LP_BARA, d.P_324E002_DES_BARA, 1.0)
        return sep.chest_p_bara, sep.t_c, pic.op
    assert run(pe.V1_CHEST) == (pytest.approx(2.3971, abs=1e-4), pytest.approx(98.188, abs=1e-3),
                                pytest.approx(54.68, abs=0.01))
    assert run(pe.PV_329208_CHEST) == (pytest.approx(2.5122, abs=1e-4),
                                       pytest.approx(98.944, abs=1e-3),
                                       pytest.approx(29.35, abs=0.01))


def test_hv_323605_on_its_vendor_trim():
    """Decision 23's class, decided 2026-10-17: HV-323605 on Metso's DN 400 Neldisc passes the
    design overhead at 64.08 % and on its normal case's xT 0.38; V1's linear trim at 50 % on the
    globe valve's xT. Both pass it exactly at the design state. With the 324E002 shell at 0.25 bar a
    the Neldisc is choked — below 0.298 bar a at the design separator — and passes 1.016 times the
    design overhead, where V1's passes 1.149; the separator at 0.60 bar a, 1.326 and 1.493 times."""
    t, mw = d.F010_T_SP_C, pe.MW_VAP_DES
    des = pe.vapour_outlet_kgh(d.HIC_323605_DES_PCT, d.F010_P_BARA, d.P_324E002_DES_BARA, t, mw)
    v1 = pe.vapour_outlet_kgh(d.HIC_323605_DES_PCT_V1, d.F010_P_BARA, d.P_324E002_DES_BARA, t, mw,
                              pe.V1_VENT)
    assert des == pytest.approx(d.MEVAP_DES_KGH, rel=1e-12) and v1 == pytest.approx(des, rel=1e-12)
    assert d.HIC_323605_DES_PCT == pytest.approx(64.079, abs=1e-3) and d.HV605_XT == 0.38
    deep = (pe.vapour_outlet_kgh(d.HIC_323605_DES_PCT, d.F010_P_BARA, 0.25, t, mw),
            pe.vapour_outlet_kgh(d.HIC_323605_DES_PCT_V1, d.F010_P_BARA, 0.25, t, mw, pe.V1_VENT))
    assert [x / d.MEVAP_DES_KGH for x in deep] == [pytest.approx(1.016, abs=1e-3),
                                                   pytest.approx(1.149, abs=1e-3)]
    high = (pe.vapour_outlet_kgh(d.HIC_323605_DES_PCT, 0.60, d.P_324E002_DES_BARA, t, mw),
            pe.vapour_outlet_kgh(d.HIC_323605_DES_PCT_V1, 0.60, d.P_324E002_DES_BARA, t, mw,
                                 pe.V1_VENT))
    assert [x / d.MEVAP_DES_KGH for x in high] == [pytest.approx(1.326, abs=1e-3),
                                                   pytest.approx(1.493, abs=1e-3)]


# ======================================================================================
# 6. The drain on the separator's own head (handoff B-119, option (b), decided 2026-10-30)
# ======================================================================================

def test_a_heavier_feed_raises_the_level_to_where_its_throughput_puts_it_b119():
    """PFD 319 10 % above its design. On its own head the separator drains what it receives at the
    level its product puts it, 60 % x (m_317 / m_317,des)^2: 72.95 % at half an hour and 73.32 % at
    two hours, the product 10.55 % above its design. V1's leg, its pressure in the drive, passes
    1.5 % less than arrives after two hours, and the separator stands at 141.5 % and rising."""
    r, r30 = _run(7200.0, m319=1.1 * R323_M319_DES, trace=1800.0)
    assert r.m_317_kgh == pytest.approx(r.feed_kgh + r.m_331_kgh - r.m_evap_kgh - r.m_boil_kgh,
                                        rel=1e-5)
    assert r.m_317_kgh / R323_M317_DES == pytest.approx(1.10547, abs=1e-5)
    assert (r30.level_pct, r.level_pct) == (pytest.approx(72.950, abs=1e-3),
                                            pytest.approx(73.324, abs=1e-3))
    assert r.level_pct == pytest.approx(
        d.F010_LVL_SP_PCT * (r.m_317_kgh / R323_M317_DES) ** 2, abs=1e-3)
    v1 = _run(7200.0, m319=1.1 * R323_M319_DES, own_head_leg=False)
    assert v1.level_pct == pytest.approx(141.519, abs=1e-3)
    assert v1.m_317_kgh < v1.feed_kgh + v1.m_331_kgh - v1.m_evap_kgh - v1.m_boil_kgh - 1000.0


def test_a_pinched_vent_raises_the_separators_pressure_but_not_its_drain_b119():
    """HV-323605 at a fifth of its design capacity, the case V1's leg drains to its heel (section
    4): PT-323204 on its 1.0 bar a clamp at a minute, 0.853 bar a at 300 s and 0.628 bar a at an
    hour, but the leg's column takes the pressure. The separator never falls below its 60 %, and as
    its evaporation falls to 3.44 t/h its larger product lifts it to 71.6 %."""
    at, lowest = _pinched(_hv(0.2), 3600.0)
    r60, r300, r = at[60], at[300], at[3600]
    assert r60.p_bara == d.F010_P_MAX_BARA
    assert (r300.p_bara, r.p_bara) == (pytest.approx(0.8534, abs=1e-4),
                                       pytest.approx(0.6281, abs=1e-4))
    assert r.m_evap_kgh == pytest.approx(3437.5, abs=0.1)
    assert (r.level_pct, lowest) == (pytest.approx(71.562, abs=1e-3),
                                     pytest.approx(60.0, abs=1e-3))


def test_a_deeper_vacuum_lowers_the_level_with_the_product_it_boils_off_b119():
    """HV-323605 at 1.6 times its design capacity, section 5's B-24 case: the holdup boils 3281
    kg/h of its own at 0.404 bar a, and the separator stands at 55.8 %, where its smaller product
    puts it. V1's leg, the separator's pressure lower, held it at 77.7 %."""
    r = _run(7200.0, hic=_hv(1.6))
    assert r.p_bara == pytest.approx(0.40420, abs=1e-5)
    assert r.m_boil_kgh == pytest.approx(3281.07, abs=0.01)
    assert r.level_pct == pytest.approx(55.839, abs=1e-3)
    assert r.level_pct == pytest.approx(
        d.F010_LVL_SP_PCT * (r.m_317_kgh / R323_M317_DES) ** 2, abs=1e-3)


def test_a_stopped_feed_drains_the_separator_to_what_pfd_331_keeps_b119():
    """Section 4's B-29 case on the decided drain: the 323F004 drain stopped on 300 kg. The chest
    boils 9.11 t/h of the held liquor at once, and the separator drains on its own head, 213 kg at
    12.5 s and 56 kg at a minute, toward the holdup that passes what still arrives: PFD 331 less
    the evaporation and the boil-off, 1.69 t/h on 2.04 kg at ten minutes, above its 1 kg heel.
    Nothing is made."""
    sep = pe.PreEvaporator()
    tic, pic = _tic(), pe.pic_329208()
    sep.m_kg, dt, created = 300.0, 0.1, 0.0
    for k in range(1, 6001):
        m_pre = sep.m_kg
        r = sep.step(tic, pic, 0.0, d.F004_T_SP_C, dict(d.W_S319), *NO_BLOW,
                     d.HIC_323605_DES_PCT, P_LP_BARA, d.P_324E002_DES_BARA, dt)
        created += (sep.m_kg - m_pre) - (r.feed_kgh + r.m_331_kgh - r.m_evap_kgh
                                         - r.m_boil_kgh - r.m_317_kgh) / 3600.0 * dt
        if k == 1:
            assert r.m_boil_kgh == pytest.approx(9112.2, abs=0.1)
        if k == 125:
            assert sep.m_kg == pytest.approx(212.655, abs=1e-3)
    assert sep.m_kg == pytest.approx(2.043, abs=1e-3) and sep.m_kg > d.F010_M_FLOOR_KG
    assert r.m_317_kgh == pytest.approx(r.m_331_kgh - r.m_evap_kgh - r.m_boil_kgh, abs=1.0)
    assert abs(created) < 1e-9
