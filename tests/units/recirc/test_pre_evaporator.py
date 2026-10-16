"""Behaviour of 323E010 / 323F010 — `ureasim.units.recirc.pre_evaporator`.

Equivalence with V1 is proven tick by tick in
`tests/equivalence/test_pre_evaporator_equivalence.py`. This file pins what stage 3 DOES: the
bubble point it relaxes to on the live PT-323204 (handoff B-22, decided 2026-10-15; V1's design
vacuum asserted both ways in the equivalence test), the heel decided on its barometric leg (B-29),
and the held liquor boiling past its bubble point at the live vacuum (B-24, decided 2026-10-02).
Every number here was
measured on the module before it was written down, on the decided chest anchor and cascade gains
(2026-09-30, As-Built §XL.1-2) and on PFD 314 and 319 closed on their urea (B-20, decided
2026-10-10).
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


def _run(seconds: float, dt: float = 1.0, hic: float = d.HIC_323605_DES_PCT,
         p_e002: float = d.P_324E002_DES_BARA, p_lp: float = P_LP_BARA, sp: float = None,
         pic_man: float = None, blow: tuple = NO_BLOW, trace: float = None):
    """Run stage 3 alone on design boundaries; return the last result (and the one at
    `trace` seconds, if asked)."""
    sep = pe.PreEvaporator()
    tic, pic = pe.tic_323012(), pe.pic_329208()
    if sp is not None:
        tic.sp = sp
    if pic_man is not None:
        pic.set_mode("MAN")
        pic.op = pic_man
    r = at = None
    for k in range(1, int(round(seconds / dt)) + 1):
        r = sep.step(tic, pic, R323_M319_DES, d.F004_T_SP_C, dict(d.W_S319), *blow, hic, p_lp,
                     p_e002, dt)
        if trace is not None and abs(k * dt - trace) < 1e-9:
            at = r
    return (r, at) if trace is not None else r


# ======================================================================================
# 1. The design point
# ======================================================================================

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
    hour, while the separator holds 99.0000 C (As-Built §XXX.2) and the urea 79.9998 %, where V1's
    dips to 79.9995 %. On the rows closed on their urea (B-20, decided 2026-10-10) the liquor
    relaxes to its bubble point at the live PT-323204 (B-22, decided 2026-10-15), 0.4600 bar a,
    and boils 0.04 kg/h of its own (0.87 on the design vacuum's bubble point, B-24)."""
    r1 = _run(0.1, dt=0.1)
    assert r1.xi_kmolh == 0.0 and r1.w["Biuret"] > d.W_S317["Biuret"]
    assert r1.m_boil_kgh == 0.0
    r = _run(3600.0)
    assert r.w["Biuret"] * 100.0 == pytest.approx(0.42518, abs=1e-5)
    assert r.w["Urea"] * 100.0 == pytest.approx(79.99980, abs=1e-5)
    assert r.t_c == pytest.approx(99.0001, abs=1e-4)
    assert r.m_boil_kgh == pytest.approx(0.04, abs=0.01)


# ======================================================================================
# 2. The steam chest, solved every tick
# ======================================================================================

@pytest.mark.parametrize("p_lp, t_c, chest, pic_op, boil", [
    (4.5, 99.0435, 2.5069, 29.285, 15.13), (4.0, 99.0999, 2.5166, 31.886, 38.85)])
def test_a_sagging_lp_header_is_answered_by_pv_329208(p_lp, t_c, chest, pic_op, boil):
    """The chest pressure is solved from the valve admission against the wall's condensation
    each tick; TIC-323012 and PIC-329208 open PV-329208 to hold it. Half an hour on, the chest is
    back above its 2.5 bar a anchor and the liquor is coming down off its overshoot — standing
    above its live bubble point, it boils 15 and 39 kg/h of its own (B-24; PV-329208 on its
    vendor trim, decided 2026-10-15 — 76 and 188 on V1's linear valve; the bubble point on the
    live PT-323204, B-22). On V1's anchor,
    gains and 40-sweep flash budget the liquor sat at 99.0414 and 98.8722 C, on a 1.76 bar a
    chest."""
    r = _run(1800.0, p_lp=p_lp)
    assert (r.t_c, r.chest_p_bara, r.pic_op_pct, r.m_boil_kgh) == (
        pytest.approx(t_c, abs=1e-4), pytest.approx(chest, abs=1e-4),
        pytest.approx(pic_op, abs=1e-3), pytest.approx(boil, abs=0.01))


# ======================================================================================
# 3. Handoff B-24, decided 2026-10-02: the held liquor boils past its bubble point
# ======================================================================================

def test_less_steam_dilutes_the_product():
    """TIC-323012 at 97 C: less duty, less water off. The smaller overhead lets HV-323605 pull
    PT-323204 down to 0.441 bar a, where 97 C is the liquor's own bubble point: it relaxes to it
    (B-22, decided 2026-10-15) and evaporates 11 116 kg/h on the duty branch, boiling nothing past
    it — 79.24 % urea. (On the design vacuum's bubble point it evaporated 10 962 and boiled 154 kg/h
    past its live one, B-24, to the same 79.24 %; V1 held it at 78.97 %.)"""
    r = _run(7200.0, sp=97.0)
    assert r.m_evap_kgh == pytest.approx(11116.3, abs=0.1)
    assert r.m_boil_kgh == 0.0
    assert r.p_bara == pytest.approx(0.44138, abs=1e-5)
    assert r.t_bub_c == pytest.approx(97.012, abs=1e-3)
    assert r.w["Urea"] * 100.0 == pytest.approx(79.242, abs=1e-3)


@pytest.mark.parametrize("kw, t_c, boil, urea", [
    (dict(sp=101.0), 100.9712, 839.11, 80.722),
    (dict(pic_man=PV_329208_PLUS_20_PCT), 102.1991, 1336.25, 81.162),
])
def test_more_steam_concentrates_the_product_b24(kw, t_c, boil, urea):
    """Handoff B-24, decided 2026-10-02. The cap still holds V1's evaporation at the design
    fraction of the feed, but the surplus no longer superheats the liquor: past its bubble point
    at the live vacuum the holdup boils it off, the product concentrates, and the liquor holds
    within 0.06 K of its bubble point. TIC-323012 at 101 C: 839 kg/h more and 80.72 % urea (V1:
    80.00 %, 3.9 K superheated); PV-329208 in MAN where its vendor trim admits 20 % more steam than
    at its 27.22 % design stroke, 30.47 % (V1's linear valve ten points above its 49.87 %): 1336
    kg/h more, 81.16 % and 102.2 C (V1: 106.5 C, 12.0 K superheated)."""
    r = _run(7200.0, **kw)
    assert r.m_evap_kgh == d.MEVAP_DES_KGH
    assert r.m_boil_kgh == pytest.approx(boil, abs=0.01)
    assert r.w["Urea"] * 100.0 == pytest.approx(urea, abs=1e-3)
    assert r.t_c == pytest.approx(t_c, abs=1e-4)
    assert 0.0 < r.t_c - liquor_stage.bubble_t(d.F010_LIQUOR, r.w, r.p_bara) < 0.06


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
    taken by a feed, boils the held liquor — 9.1 t/h at once, 9.8 at 1 s — and it concentrates
    toward 92 % (B-24) as the leg empties the separator to its 1 kg heel in 12.4 s (V1: 15.1 s,
    the liquor superheating instead); then the leg passes what arrives, PFD 331 less the
    evaporation, and nothing below the heel boils. Nothing is made (V1's leg passed the floor's
    kilogram every tick, 36 t/h at this step)."""
    sep = pe.PreEvaporator()
    tic, pic = pe.tic_323012(), pe.pic_329208()
    sep.m_kg, dt, created, heel_s = 300.0, 0.1, 0.0, None
    for k in range(1, 601):
        m_pre = sep.m_kg
        r = sep.step(tic, pic, 0.0, d.F004_T_SP_C, dict(d.W_S319), *NO_BLOW,
                     d.HIC_323605_DES_PCT, P_LP_BARA, d.P_324E002_DES_BARA, dt)
        created += (sep.m_kg - m_pre) - (r.feed_kgh + r.m_331_kgh - r.m_evap_kgh
                                         - r.m_boil_kgh - r.m_317_kgh) / 3600.0 * dt
        if k == 1:
            assert r.m_boil_kgh == pytest.approx(9099.8, abs=0.1)
        if heel_s is None and sep.m_kg <= d.F010_M_FLOOR_KG + 1e-9:
            heel_s = round(k * dt, 6)
    assert heel_s == 12.4
    assert sep.m_kg == pytest.approx(d.F010_M_FLOOR_KG, abs=1e-9)
    assert r.m_boil_kgh == 0.0
    assert r.m_317_kgh == pytest.approx(r.m_331_kgh - r.m_evap_kgh, rel=1e-9)
    assert abs(created) < 1e-9


def _pinched(hic: float, seconds: float = 7200.0) -> dict:
    """HV-323605 held at ``hic`` from the design: the results at the times the tests read, and the
    lowest level."""
    sep = pe.PreEvaporator()
    tic, pic = pe.tic_323012(), pe.pic_329208()
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
    PT-323204. HV-323605 at 25 %: PT-323204 0.682 bar a after a minute, where the liquor boils at
    110.1 C; it heats from 99 to 101.5 C and evaporates 10.45 t/h, and by 300 s it stands on its
    bubble point, 104.2 C, evaporating 8.5 t/h, TIC-323012 cutting the chest. After two hours the
    separator holds 0.530 bar a and 99.0 C, evaporating 7.65 t/h, 76.43 % urea, the level never
    below 38 %. (On V1's design-vacuum bubble point the liquor stayed at 99.06 C 14 K below its
    boiling point, evaporating 12 t/h, and the leg drained the separator dry.) The plant's manual
    (`References/323F004 323E010 323F010.md` §5) has the steam cut back as the vacuum decays."""
    at, lowest = _pinched(25.0)
    r60, r300, r = at[60], at[300], at[7200]
    assert (r60.p_bara, r60.t_c, r60.t_bub_c) == (pytest.approx(0.6822, abs=1e-4),
                                                  pytest.approx(101.455, abs=1e-3),
                                                  pytest.approx(110.135, abs=1e-3))
    assert r60.m_evap_kgh == pytest.approx(10453.7, abs=0.1)
    assert (r300.t_c, r300.m_evap_kgh) == (pytest.approx(104.161, abs=1e-3),
                                           pytest.approx(8513.0, abs=0.1))
    assert (r.p_bara, r.m_evap_kgh, r.w["Urea"] * 100.0) == (
        pytest.approx(0.5303, abs=1e-4), pytest.approx(7646.2, abs=0.1),
        pytest.approx(76.432, abs=1e-3))
    assert lowest > 38.0


def test_hic_323605_nearly_shut_pins_the_pressure_at_its_clamp_until_the_evaporation_falls():
    """At 10 % the valve cannot pass the overhead: PT-323204 sits on its 1.0 bar a clamp, the
    vapour the separator makes beyond the valve's 6.31 t/h lost there, while the liquor heats
    toward its 121 C bubble point and its evaporation falls — 8.97 t/h after a minute. Within five
    minutes the evaporation is under what the valve passes and the pressure leaves the clamp,
    0.813 bar a at 300 s; after two hours 0.614 bar a, 3.80 t/h, 73.54 % urea and the level at 6.6 %.
    (On V1's design-vacuum bubble point the evaporation held 12 t/h at the clamp.)"""
    at, lowest = _pinched(10.0)
    r60, r300, r = at[60], at[300], at[7200]
    assert r60.p_bara == d.F010_P_MAX_BARA
    assert (r60.pull_kgh, r60.m_evap_kgh) == (pytest.approx(6310.6, abs=0.1),
                                              pytest.approx(8974.2, abs=0.1))
    assert r300.p_bara == pytest.approx(0.8132, abs=1e-4)
    assert (r.p_bara, r.m_evap_kgh, r.w["Urea"] * 100.0) == (
        pytest.approx(0.6139, abs=1e-4), pytest.approx(3799.4, abs=0.1),
        pytest.approx(73.540, abs=1e-3))
    assert r.level_pct == pytest.approx(6.61, abs=0.01) and lowest > 6.0


def test_a_deeper_vacuum_boils_the_liquor_down_to_its_live_bubble_point_b24():
    """HV-323605 at 80 %: PT-323204 falls, and the liquor, standing above its bubble point at
    the deeper vacuum, boils (handoff B-24, decided 2026-10-02) — 1042 kg/h after a minute, at
    95.15 C and 0.391 bar a. TIC-323012 brings it back to 99 C, which at the vacuum the boil-off
    holds, 0.411 bar a, is the bubble point of an 82.59 % liquor: after two hours the holdup boils
    2920 kg/h of its own and the level sits at 75 %. V1 (B-22's design-vacuum bubble point and
    B-24's cap) held the overhead at the design split, the liquor 3.8 K superheated at 0.3825
    bar a, and the level climbed past its span to 121.5 %."""
    r, r60 = _run(7200.0, hic=80.0, trace=60.0)
    assert (r60.t_c, r60.p_bara, r60.m_boil_kgh) == (
        pytest.approx(95.381, abs=1e-3), pytest.approx(0.3938, abs=1e-4),
        pytest.approx(1325.0, abs=0.1))
    assert r.p_bara == pytest.approx(0.41049, abs=1e-5)
    assert r.level_pct == pytest.approx(75.55, abs=0.01)
    assert r.m_evap_kgh == d.MEVAP_DES_KGH
    assert r.m_boil_kgh == pytest.approx(2936.38, abs=0.01)
    assert r.w["Urea"] * 100.0 == pytest.approx(82.582, abs=1e-3)
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
    assert r.p_bara == pytest.approx(0.46369, abs=1e-5)
    assert r.pull_kgh == pytest.approx(12217.0, abs=0.1)


def test_pv_329208_on_its_vendor_trim_holds_the_chest_on_a_falling_header():
    """Decision 108's class, applied 2026-10-15: PV-329208 on Metso's DN 250 balanced Neldisc from
    its 27.22 % design stroke, where V1 runs it linear from 49.87 % (the harness proves V1's ==).
    The LP header 10 % down for five minutes: V1's valve opens to 54.4 %, the chest at 2.3934 bar a
    and the separator at 98.258 C; the Neldisc, at 29.3 %, holds the chest at 2.5039 and the
    separator at 98.878 C (both on the live PT-323204's bubble point, B-22)."""
    def run(chest):
        sep = pe.PreEvaporator(chest=chest)
        tic, pic = pe.tic_323012(), pe.pic_329208(chest)
        for _ in range(300):
            sep.step(tic, pic, R323_M319_DES, d.F004_T_SP_C, dict(d.W_S319), *NO_BLOW,
                     d.HIC_323605_DES_PCT, 0.9 * P_LP_BARA, d.P_324E002_DES_BARA, 1.0)
        return sep.chest_p_bara, sep.t_c, pic.op
    assert run(pe.V1_CHEST) == (pytest.approx(2.3934, abs=1e-4), pytest.approx(98.258, abs=1e-3),
                                pytest.approx(54.42, abs=0.01))
    assert run(pe.PV_329208_CHEST) == (pytest.approx(2.5039, abs=1e-4),
                                       pytest.approx(98.878, abs=1e-3),
                                       pytest.approx(29.31, abs=0.01))
