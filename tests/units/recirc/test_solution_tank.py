"""Behaviour of 323D002 — `ureasim.units.recirc.solution_tank`.

Equivalence with V1 is proven tick by tick in
`tests/equivalence/test_solution_tank_equivalence.py`. This file pins what stage 4 DOES: how
its two compartments mix and turn over, and how it keeps its books at the limits where V1's
tank created or destroyed liquor — the divergence decided on 2026-09-27 (handoffs B-26, B-27).
Every number here was measured on the module before it was written down, with FV-324401 on its
vendor trim (B-44, decided 2026-09-30).
"""

from __future__ import annotations

import pytest

from ureasim.core.packet import normalise_solution_mass_fraction
from ureasim.data import unit_323 as d
from ureasim.data.design_point import R323_D002_RHO, R323_M317_DES
from ureasim.units.recirc import solution_tank as st

W317 = dict(d.W_S317)
#: PFD 402, the Evaporator II melt the LV-324501B recycle carries.
W402 = normalise_solution_mass_fraction(dict(Urea=97.71, Biuret=0.85, NH3=0.04, H2O=1.39,
                                             HCHO=0.0099))
NO_RECYCLE = (0.0, 140.0, W402)


def _run(seconds: float, dt: float = 1.0, t317=None, recycle=None, tie=None,
         fic_man: float = None, m_i: float = None, m_ii: float = None, trace: tuple = ()):
    """Run the tank alone on the design separator drain. Returns the last result, the results
    at the `trace` times, and the mass the tank created (+) or destroyed (-) over the run —
    the holdup change less what arrived, what the pump delivered and what overflowed."""
    tank, lic, fic = st.SolutionTank(), st.lic_323507(), st.fic_324401()
    if fic_man is not None:
        fic.set_mode("MAN")
        fic.op = fic_man
    if m_i is not None:
        tank.m_i_kg = m_i
    if m_ii is not None:
        tank.m_ii_kg = m_ii
    r, at, created = None, {}, 0.0
    for k in range(1, int(round(seconds / dt)) + 1):
        t = k * dt
        m_before = tank.m_i_kg + tank.m_ii_kg
        r = tank.step(lic, fic, R323_M317_DES, t317(t) if t317 else d.F010_T_SP_C, W317,
                      *(recycle(t) if recycle else NO_RECYCLE), tie(t) if tie else False, dt)
        created += ((r.m_i_kg + r.m_ii_kg - m_before)
                    - (r.feed_kgh + r.recycle_kgh - r.m_324_kgh - r.overflow_kgh) / 3600.0 * dt)
        if t in trace:
            at[t] = r
    return r, at, created


# ======================================================================================
# 1. The design point, and where the residence time comes from
# ======================================================================================

def test_the_design_seed_is_held_to_a_few_hundredths_of_a_kilogram():
    """The live density is anchored on 80.00 % urea, and the normalised PFD row carries
    80.0016 %, so the seed reads 1151.0042 kg/m3 and LIC-323507 sees 9.99996 %, not 10. The
    loop takes back 0.03 kg over the next hours; the temperature does not move. V1 is
    identical (As-Built §XXXI.2)."""
    r1, _, _ = _run(0.1, dt=0.1)
    assert r1.rho_kgm3 == pytest.approx(1151.00416, abs=1e-5)
    assert r1.lic_pv_pct == pytest.approx(9.9999639, abs=1e-7)
    assert r1.t_c == d.F010_T_SP_C and r1.m_ii_kg == 0.0
    r, _, _ = _run(6 * 3600.0)
    assert r.m_i_kg - d.D002_M_I_DES_KG == pytest.approx(0.0321, abs=1e-4)
    assert r.m_324_kgh == pytest.approx(R323_M317_DES, abs=1e-3)


def test_compartment_one_turns_over_in_six_minutes_at_its_set_point():
    """No residence time is configured anywhere: Compartment I's is its holdup over its flow,
    357 s at the 10 % set point, and TI-323008 follows a colder product on that time
    constant — a perfectly mixed vessel. (Behind the 30.5 s line from 323F010, the isometrics'
    geometry, handoff A-11: 93.621 and 90.407 C; 93.683 and 90.414 on V1's 36.9 s.)"""
    assert d.D002_M_I_DES_KG / R323_M317_DES * 3600.0 == pytest.approx(357.40, abs=0.01)
    r, at, _ = _run(1200.0, t317=lambda t: 90.0 if t > 60.0 else 99.0, trace=(417.0,))
    assert at[417.0].t_c == pytest.approx(93.621, abs=1e-3)
    assert r.t_c == pytest.approx(90.407, abs=1e-3)


def test_the_melt_recycle_heats_and_concentrates_compartment_one():
    """20 t/h of 140 C Evaporator II melt through LV-324501B: an hour later the tank is at
    105.3 C and 83.1 % urea, and LIC-323507 has raised the draw to 110 t/h."""
    r, _, _ = _run(3600.0, recycle=lambda t: (20000.0, 140.0, W402) if t > 60.0 else NO_RECYCLE)
    assert r.t_c == pytest.approx(105.341, abs=1e-3)
    assert r.w["Urea"] * 100.0 == pytest.approx(83.141, abs=1e-3)
    assert r.m_324_kgh == pytest.approx(110224.8, abs=0.1)  # 110 221.4 on V1's gain (B-41)


def test_a_recycle_that_is_not_flowing_moves_nothing():
    """The LV-324501B tear's temperature and composition enter only multiplied by its flow, so
    at zero flow no seed of them can move any output, to the bit."""
    tank_a, lic_a, fic_a = st.SolutionTank(), st.lic_323507(), st.fic_324401()
    tank_b, lic_b, fic_b = st.SolutionTank(), st.lic_323507(), st.fic_324401()
    for _ in range(50):
        a = tank_a.step(lic_a, fic_a, R323_M317_DES, 99.0, W317, 0.0, 140.0, W402, False, 1.0)
        b = tank_b.step(lic_b, fic_b, R323_M317_DES, 99.0, W317, 0.0, 20.0, W317, False, 1.0)
    assert a == b


# ======================================================================================
# 2. The baffle and Compartment II
# ======================================================================================

def test_a_stopped_pump_fills_compartment_one_then_spills_into_compartment_two():
    """FV-324401 shut: Compartment I overtops the baffle at 3217 s and LI-323504 climbs at the
    feed rate, 13.4 points an hour; Compartment II is full at 16 620 s."""
    r, at, created = _run(3 * 3600.0, fic_man=0.0, trace=(3216.0, 3217.0, 7200.0))
    assert at[3216.0].spill_kg == 0.0 and at[3217.0].spill_kg > 0.0
    assert at[7200.0].lic_pv_pct == 100.0
    assert at[7200.0].li_323504_pct == pytest.approx(29.721, abs=1e-3)
    assert created == pytest.approx(0.0, abs=1e-6)


def test_a_full_tank_overflows_what_arrives_and_compartment_two_sums_to_one():
    """Handoff B-27, decided 2026-09-27. With both compartments full from 16 620 s the whole
    separator drain leaves as the overflow stream — 128.3 t in the 83 minutes after, exactly
    what V1 destroyed — at Compartment II's temperature and composition, which still sums to
    one. The books close to rounding over six hours."""
    r, at, created = _run(6 * 3600.0, fic_man=0.0, trace=(16619.0, 16620.0))
    assert at[16619.0].overflow_kgh == 0.0 and at[16620.0].overflow_kgh > 0.0
    assert r.li_323504_pct == pytest.approx(100.0, abs=1e-9)
    assert r.overflow_kgh == pytest.approx(R323_M317_DES, rel=1e-9)
    assert (r.overflow_t_c, r.overflow_w) == (r.t_ii_c, r.w_ii)
    assert sum(r.w_ii.values()) == pytest.approx(1.0, abs=1e-12)
    assert created == pytest.approx(0.0, abs=1e-6)


def test_a_full_pool_overflows_with_the_tie_open():
    """The same with the tie open: the pooled 380 m3 overflows at the pool's state."""
    r, at, created = _run(1200.0, fic_man=0.0, m_i=d.D002_M_I_FULL_KG,
                          m_ii=0.999 * d.D002_VOL_II_M3 * R323_D002_RHO, tie=lambda t: True,
                          trace=(13.0, 14.0))
    assert at[13.0].overflow_kgh == 0.0 and at[14.0].overflow_kgh > 0.0
    assert (r.overflow_t_c, r.overflow_w) == (r.t_c, r.w)
    assert created == pytest.approx(0.0, abs=1e-6)


def test_opening_the_tie_on_a_dry_compartment_two_collapses_the_level():
    """The two compartments equalise in one tick: a 10 % Compartment I level becomes 2.1 % of
    the pooled 380 m3, and LIC-323507 cuts the draw to 80 t/h, recovering 7.2 % in two hours.
    On V1's FIC-324401 gain and linear trim the level would stand at 7.1595 % and the draw at
    80 039.8 kg/h (B-41, B-44)."""
    r, at, created = _run(7200.0, tie=lambda t: t > 60.0, trace=(61.0,))
    assert at[61.0].lic_pv_pct == pytest.approx(2.1053, abs=1e-4)
    assert at[61.0].m_ii_kg / at[61.0].m_i_kg == pytest.approx(300.0 / 80.0, rel=1e-12)
    assert r.lic_pv_pct == pytest.approx(7.1607, abs=1e-4)
    assert r.m_324_kgh == pytest.approx(80044.6, abs=0.1)
    assert created == pytest.approx(0.0, abs=1e-6)


def test_compartment_two_keeps_the_temperature_of_its_spills():
    """Handoff B-27, decided 2026-09-27. 30 t spilt at 99 C and stranded while Compartment I
    cools to 92.4 C: Compartment II still holds 99 C, and the pool the tie makes starts from the
    cp-weighted enthalpy balance, 94.0 C. V1 pooled at 92.4 C. (On the isometrics' line from
    323F010, handoff A-11: 92.3728 and 93.9981 C; 92.3768 and 94.0011 on V1's.)"""
    tank, lic, fic = st.SolutionTank(), st.lic_323507(), st.fic_324401()
    tank.m_i_kg = 0.99 * d.D002_M_I_FULL_KG
    lic.set_mode("MAN")
    fic.set_mode("MAN")
    fic.op = 0.0
    dt = 2.0
    for k in range(1, 3002):
        t = k * dt
        if t == 1200.0:
            fic.op = d.FV401_OP_DES_PCT
        if t == 6002.0:
            m_ii, t_i, t_ii = tank.m_ii_kg, tank.t_c, tank.t_ii_c
        tank.step(lic, fic, R323_M317_DES, 99.0 if t <= 1200.0 else 90.0, W317, *NO_RECYCLE,
                  t > 6000.0, dt)
    assert m_ii == pytest.approx(29943.6, abs=0.1) and t_i == pytest.approx(92.3728, abs=1e-4)
    assert t_ii == 99.0
    assert tank.t_c == pytest.approx(93.9981, abs=1e-4)
    assert tank.t_ii_c == tank.t_c


# ======================================================================================
# 3. Handoff B-26, decided 2026-09-27: 323P003 delivers only what the tank holds
# ======================================================================================

def test_the_pump_loses_suction_instead_of_creating_liquor():
    """FV-324401 held at 85 %: on its trim the pump draws 135.4 t/h against 92.7 arriving, and
    Compartment I reaches its 1 kg heel at 777 s. From then on the pump delivers what arrives,
    the loss of suction is flagged, FT-324401 reads the 92.7 t/h delivered, and nothing is
    created. (V1, its linear trim held at 60 %, kept delivering 111.3 t/h and created 9.3 t in
    the hour.)"""
    assert st.fv_324401_th(85.0) == pytest.approx(135.449, abs=1e-3)
    r, at, created = _run(3600.0, fic_man=85.0, trace=(776.0, 777.0))
    assert not at[776.0].suction_lost and at[776.0].m_i_kg > d.D002_M_I_FLOOR_KG
    assert at[777.0].suction_lost
    assert at[777.0].m_i_kg == pytest.approx(d.D002_M_I_FLOOR_KG, abs=1e-12)
    assert r.suction_lost and r.fic_op_pct == 85.0
    assert r.m_324_kgh == pytest.approx(R323_M317_DES, rel=1e-12)
    assert r.fic_pv_th == pytest.approx(R323_M317_DES / 1000.0, rel=1e-9)
    assert created == pytest.approx(0.0, abs=1e-9)


def test_the_cascade_pulls_back_before_the_pump_loses_suction():
    """With LIC-323507 -> FIC-324401 in cascade the loop cuts the draw first: from 500 kg the
    level bottoms at 0.54 % and the cap never binds."""
    r, at, created = _run(3600.0, m_i=500.0, trace=tuple(float(k) for k in range(1, 3601)))
    assert not any(x.suction_lost for x in at.values())
    assert min(x.lic_pv_pct for x in at.values()) == pytest.approx(0.5430, abs=1e-4)
    assert created == pytest.approx(0.0, abs=1e-9)


def test_the_pooled_heel_is_made_up_once():
    """The one liquor the tank still makes: the tie opened on a Compartment I at its 1 kg heel
    with a dry Compartment II. The heel is 1 kg of Compartment I's share of the pool — 4.75 kg
    in all — and the missing 3.75 kg is made up once, whatever the pump asks for."""
    tank, lic, fic = st.SolutionTank(), st.lic_323507(), st.fic_324401()
    fic.set_mode("MAN")
    fic.op = 100.0
    tank.m_i_kg = d.D002_M_I_FLOOR_KG
    created = 0.0
    for k in range(1, 601):
        m_before = tank.m_i_kg + tank.m_ii_kg
        r = tank.step(lic, fic, 0.0, 99.0, W317, *NO_RECYCLE, k > 10, 1.0)
        created += ((r.m_i_kg + r.m_ii_kg - m_before)
                    - (r.feed_kgh + r.recycle_kgh - r.m_324_kgh - r.overflow_kgh) / 3600.0)
    assert created == pytest.approx(3.75, abs=1e-12)
    assert tank.m_i_kg == pytest.approx(d.D002_M_I_FLOOR_KG, abs=1e-12)
    assert r.suction_lost and r.m_324_kgh == 0.0
