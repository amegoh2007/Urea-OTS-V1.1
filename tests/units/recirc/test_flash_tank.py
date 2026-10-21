"""Behaviour of 323F004 — `ureasim.units.recirc.flash_tank`.

Equivalence with V1 is proven tick by tick in `tests/equivalence/test_flash_tank_equivalence.py`.
This file pins what stage 2 DOES: the design point, the energy-limited flash, the drum pressure
taken from the 323E011 node one tick late, and LV-323505 answering the vacuum. Every number here
was measured on the module before it was written down, with LV-323505 on its vendor trim (B-44,
decided 2026-09-30), on PFD 314 and 319 closed on their urea (B-20, decided 2026-10-10), and on
the drum's geometry — 1837 kg at LIC-323505's 60 % between LT-323505's taps (B-100, decided
2026-10-17), where V1 holds 5075 kg.
"""

from __future__ import annotations

import math

import pytest

from ureasim.data import unit_323 as d
from ureasim.data.design_point import R323_M314_DES, R323_M319_DES
from ureasim.units.recirc import flash_tank as ft


def _run(seconds: float, dt: float = 0.1, m314: float = R323_M314_DES, t314: float = 135.0,
         p_e011: float = d.F004_P_BARA, p_f010: float = d.F010_P_BARA):
    """Run stage 2 alone on fixed boundaries; return the last result."""
    tank = ft.FlashTank()
    lic = ft.lic_323505()
    w314 = dict(d.W_S314)
    r = None
    for _ in range(int(round(seconds / dt))):
        r = tank.step(lic, m314, t314, w314, p_e011, p_f010, dt)
    return r


# ======================================================================================
# 1. The design point
# ======================================================================================

def test_the_first_design_tick_is_the_pfd():
    r = _run(0.1)
    assert (r.t_c, r.p_bara, r.t_bub_c, r.q_relax_kw) == (d.F004_T_SP_C, d.F004_P_BARA,
                                                        d.F004_T_SP_C, 0.0)
    assert r.q_avail_kw == d.Q701_DES_KW
    assert r.m_701_kgh == d.M701_DES_KGH
    assert r.m_319_kgh == R323_M319_DES
    assert r.m_kg == d.F004_M_DES_KG and r.level_pct == d.F004_LVL_SP_PCT
    assert r.vapour_domain == "electrolyte_gamma_phi"
    assert r.xi_kmolh == 0.0                     # the PFD back-solve gives the drum no biuret


def test_the_design_point_is_a_fixed_point():
    """Unlike 323C003 (handoff B-20), the drum carries no urea remainder: an hour on design
    boundaries moves nothing. The composition is the PFD row to the last bit but one — the
    first tick's renormalisation — and then it does not move at all."""
    r1 = _run(1.0, dt=1.0)
    r = _run(3600.0, dt=1.0)
    assert (r.t_c, r.m_701_kgh, r.m_319_kgh) == (d.F004_T_SP_C, d.M701_DES_KGH, R323_M319_DES)
    assert r.w == r1.w
    assert r.w == pytest.approx(d.W_S319, abs=1e-15)


def test_the_flash_vapour_is_pfd_701():
    """PFD 701 is tabulated in MOLE %: 4.28 CO2, 61.64 H2O, 34.08 NH3. By mass that is about
    10.0 / 59.1 / 30.9, and the drum's anchored vapour is exactly the back-solved split."""
    y = _run(0.1).y_701
    assert (y["Urea"], y["Biuret"], y["HCHO"]) == (0.0, 0.0, 0.0)
    assert y["CO2"] == pytest.approx(0.0999, abs=1e-4)
    assert y["H2O"] == pytest.approx(0.5922, abs=1e-4)
    assert y["NH3"] == pytest.approx(0.3079, abs=1e-4)


# ======================================================================================
# 2. The flash, energy-limited
# ======================================================================================

@pytest.mark.parametrize("t314, m701, t_drum", [(130.0, 3766.55, 105.29), (140.0, 5079.81, 106.77)])
def test_a_hotter_drain_flashes_more(t314, m701, t_drum):
    r = _run(1800.0, dt=1.0, t314=t314)
    assert r.m_701_kgh == pytest.approx(m701, abs=0.01)
    assert r.t_c == pytest.approx(t_drum, abs=0.01)


def test_the_flash_scales_with_the_drain():
    r = _run(1800.0, dt=1.0, m314=1.2 * R323_M314_DES)
    assert r.m_701_kgh / d.M701_DES_KGH == pytest.approx(1.2, rel=1e-12)
    assert r.t_c == d.F004_T_SP_C


def test_a_drain_colder_than_the_drum_flashes_nothing():
    """A letdown with no sensible surplus boils nothing; its heat only moves the temperature,
    and the drum sits below its bubble point."""
    assert _run(0.1, t314=100.0).m_701_kgh == 0.0
    r = _run(600.0, dt=1.0, t314=100.0)
    assert r.m_701_kgh == 0.0
    assert r.t_c == pytest.approx(100.0004, abs=1e-4)
    assert r.t_c < r.t_bub_c


# ======================================================================================
# 3. The pressure: the 323E011 / 323D011 node's, adopted one tick late
# ======================================================================================

def test_the_drum_adopts_the_node_pressure_at_the_end_of_the_tick():
    """The first tick still flashes on the pressure the drum held; the second sees the node."""
    tank = ft.FlashTank()
    lic = ft.lic_323505()
    w314 = dict(d.W_S314)
    first = tank.step(lic, R323_M314_DES, 135.0, w314, 1.30, d.F010_P_BARA, 0.1)
    assert first.p_bara == 1.30
    assert (first.t_bub_c, first.m_701_kgh) == (d.F004_T_SP_C, d.M701_DES_KGH)
    second = tank.step(lic, R323_M314_DES, 135.0, w314, 1.30, d.F010_P_BARA, 0.1)
    assert second.t_bub_c == pytest.approx(109.1984, abs=1e-4)


@pytest.mark.parametrize("p_e011, t_drum, m701", [
    (1.00, 103.2700, 4843.25),
    (1.13, 106.0000, 4426.61),
    (1.30, 109.1300, 3948.84),
])
def test_back_pressure_raises_the_bubble_point_and_shrinks_the_flash(p_e011, t_drum, m701):
    """The loop the plant has: a higher node pressure raises the bubble point, the drum
    relaxes up to it, and less of the letdown's heat is left to flash."""
    r = _run(1800.0, dt=1.0, p_e011=p_e011)
    assert r.t_c == pytest.approx(t_drum, abs=1e-4)
    assert r.m_701_kgh == pytest.approx(m701, abs=0.01)


# ======================================================================================
# 4. LV-323505 and the vacuum downstream
# ======================================================================================

def test_the_vacuum_reaches_the_drum_only_past_the_choke():
    """LV-323505 flashes (handoff B-46, decided 2026-09-30). The drum liquor reaches it at its
    bubble point, 1.13 bar a, so its flow chokes on FL^2 (P1 - FF . Pv) = 0.054 bar, not on the
    0.67 bar across it: 323F010 at 0.90 bar a instead of 0.46 moves nothing. The vacuum reaches
    the drum only once 323F010 climbs past the choke point, 1.076 bar a. At 1.10 bar a the drain
    falls to 74.5 % at once, and the level loop strokes the valve from 67.73 % to 77.56 % to put
    it back, the drain PFD 319's again by half an hour. (Unchoked, before B-46: 0.90 bar a cut the drain to 59 465 kg/h at once, and
    LIC-323505 answered at 85.58 %.)"""
    assert _run(0.1, p_f010=0.90).m_319_kgh == R323_M319_DES
    ff = 0.96 - 0.28 * math.sqrt(d.LV505_PV_DES_BARA / 220.64)
    choke = d.F004_P_BARA - ft.LV505_FL ** 2 * (d.F004_P_BARA - ff * d.LV505_PV_DES_BARA)
    assert choke == pytest.approx(1.0759, abs=1e-4)
    assert _run(0.1, p_f010=1.10).m_319_kgh == pytest.approx(75610.8, abs=0.1)
    r = _run(1800.0, dt=1.0, p_f010=1.10)
    assert r.lv505_op_pct == pytest.approx(77.56, abs=0.01)
    assert r.m_319_kgh == pytest.approx(101492.2, abs=0.1)


# ======================================================================================
# 5. Handoff A-22, decided 2026-10-17: a full drum overflows into 323E011
# ======================================================================================

def _pinched(seconds: float, ceiling: bool = True):
    """LV-323505 in MAN at 30 % on design boundaries: the drum, the first overflowing second and
    the mass that overflowed [kg]."""
    tank, lic = ft.FlashTank(ceiling=ceiling), ft.lic_323505()
    lic.set_mode("MAN")
    lic.op = 30.0
    first, spilt = None, 0.0
    for k in range(1, int(round(seconds / 0.1)) + 1):
        r = tank.step(lic, R323_M314_DES, d.C003_T_SP_C, d.W_S314, d.F004_P_BARA,
                      d.F010_P_BARA, 0.1)
        spilt += r.m_overflow_kgh * 0.1 / 3600.0
        if first is None and r.m_overflow_kgh > 0.0:
            first = round(k * 0.1, 1)
    return r, first, spilt


def test_a_full_drum_overflows_its_excess():
    """LV-323505 pinched to 30 % passes 32.6 t/h of PFD 319's 101.5: the drum is full, 3761.5 kg on
    its 3.402 m3, at 100.6 s and holds there, LI-323505 at 100 %, the excess — what arrives less the
    flash and the drain, 68.9 t/h — overflowing at the drum's composition. With no ceiling the
    holdup keeps growing, 7578 kg at five minutes: the capped drum plus what overflowed, to 1e-12;
    the flash and the drain are the uncapped drum's to the last bits."""
    r, first, spilt = _pinched(300.0)
    v1, _, none = _pinched(300.0, ceiling=False)
    assert first == 100.6 and none == 0.0 and v1.m_overflow_kgh == 0.0
    assert (r.m_kg, r.level_pct) == (d.F004_M_FULL_KG, 100.0)
    assert d.F004_M_FULL_KG == pytest.approx(3761.51, abs=0.01)
    assert r.m_overflow_kgh == pytest.approx(r.feed_kgh - r.m_701_kgh - r.m_319_kgh, rel=1e-12)
    assert r.m_overflow_kgh == pytest.approx(68901.07, abs=0.01)
    assert v1.m_kg == pytest.approx(7578.34, abs=0.01)
    assert r.m_kg + spilt == pytest.approx(v1.m_kg, rel=1e-12)
    assert (r.t_c, r.m_701_kgh, r.m_319_kgh) == pytest.approx(
        (v1.t_c, v1.m_701_kgh, v1.m_319_kgh), rel=1e-12)
    assert r.w == pytest.approx(v1.w, abs=1e-12)


def test_below_a_full_drum_the_ceiling_is_inert():
    """On design boundaries an hour with the ceiling is an hour without it, to the bit."""
    a, b = ft.FlashTank(), ft.FlashTank(ceiling=False)
    la, lb = ft.lic_323505(), ft.lic_323505()
    for _ in range(3600):
        ra = a.step(la, R323_M314_DES, d.C003_T_SP_C, d.W_S314, d.F004_P_BARA, d.F010_P_BARA,
                    1.0)
        rb = b.step(lb, R323_M314_DES, d.C003_T_SP_C, d.W_S314, d.F004_P_BARA, d.F010_P_BARA,
                    1.0)
    assert ra == rb and ra.m_overflow_kgh == 0.0
