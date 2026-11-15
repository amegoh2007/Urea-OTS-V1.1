"""Behaviour of the urea-liquor stage layer — `ureasim.units.liquor_stage`.

Equivalence with V1 is proven in `tests/equivalence/test_liquor_stage_equivalence.py`. This file
pins what the layer does at and around each 323 stage's design point, 323C003's seed a fixed
point on PFD 314 closed on its urea (B-20, decided 2026-10-10). Every number was measured before it
was written.
"""

from __future__ import annotations

import dataclasses
import math

import pytest

from ureasim.data import unit_323 as d
from ureasim.data.design_point import R323_FEED_DES_KGH, R323_M314_DES, R323_M319_DES
from ureasim.data.unit_322e001 import BIURET_EA_JMOL, BIURET_R_GAS_J
from ureasim.thermo import urea_liquor as ul
from ureasim.thermo.domains import MW
from ureasim.units import liquor_stage as ls

STAGES = {"C003": d.C003_LIQUOR, "F004": d.F004_LIQUOR, "F010": d.F010_LIQUOR}


# ======================================================================================
# The bubble point
# ======================================================================================

@pytest.mark.parametrize("key", list(STAGES))
def test_each_stage_boils_at_its_set_point_at_design(key):
    st = STAGES[key]
    assert ls.bubble_t(st, st.w_des, st.p_des_bara) == st.t_des_c


def test_the_column_bubble_point_rides_its_pressure():
    """The genuine plant TIC-323007 needs: more duty, more vapour, more pressure, hotter."""
    st = d.C003_LIQUOR
    assert ls.bubble_t(st, st.w_des, st.p_des_bara * 0.85) == pytest.approx(130.72, abs=0.01)
    assert ls.bubble_t(st, st.w_des, st.p_des_bara * 1.15) == pytest.approx(138.71, abs=0.01)


def test_off_the_rigorous_surface_the_raoult_pair_is_still_anchored():
    fallback = dataclasses.replace(d.C003_LIQUOR, tbub_des_c=None)
    assert ls.bubble_t(fallback, fallback.w_des, fallback.p_des_bara) == fallback.t_des_c
    #  Water-only, so steeper with pressure than the rigorous surface.
    assert ls.bubble_t(fallback, fallback.w_des, fallback.p_des_bara * 1.15) == pytest.approx(
        140.81, abs=0.01)


# ======================================================================================
# The vapour
# ======================================================================================

@pytest.mark.parametrize("key", list(STAGES))
def test_each_design_state_stands_on_the_rigorous_surface(key):
    st = STAGES[key]
    _, domain = ls.vapour(st, st.w_des, st.t_des_c, st.p_des_bara)
    assert domain == "electrolyte_gamma_phi"


def test_off_the_envelope_the_stage_falls_back_visibly():
    """323F004's liquor 10 C above its flash temperature does not converge in 60 sweeps. At
    114 C it converges on sweep 41, where V1's 40-sweep budget fell back (handoff A-9)."""
    st = d.F004_LIQUOR
    y, domain = ls.vapour(st, st.w_des, 116.0, st.p_des_bara)
    assert domain is None
    assert y == ul.vapour_y(st.w_des, st.anchor.alpha)
    _, domain = ls.vapour(st, st.w_des, 114.0, st.p_des_bara)
    assert domain == "electrolyte_gamma_phi"


def test_urea_never_leaves_as_vapour():
    for st in STAGES.values():
        y, _ = ls.vapour(st, st.w_des, st.t_des_c + 5.0, st.p_des_bara)
        assert y["Urea"] == y["Biuret"] == y["HCHO"] == 0.0


def test_the_323c003_design_seed_holds_its_urea():
    """PFD 314 closed on its urea against the drain (handoff B-20, decided 2026-10-10): the
    back-solve sends no urea overhead and the runtime boils none, so the urea the feed brings less
    what the biuret takes leaves by the drain to the bit, and an hour on the seed has moved 8e-8 of
    a mass fraction. On the table's row 8.164 kg/h of urea the anchor sent overhead stayed in the
    column and the seed gained 0.00231 in the hour (V1's, asserted in the equivalence)."""
    st = d.C003_LIQUOR
    y, _ = ls.vapour(st, st.w_des, st.t_des_c, st.p_des_bara)
    assert st.anchor.y["Urea"] == 0.0 and y["Urea"] == 0.0
    urea_in = R323_FEED_DES_KGH * d.W_S208["Urea"]
    urea_out = (R323_M314_DES * st.w_des["Urea"] + d.M305_DES_KGH * y["Urea"]
                + 2.0 * MW["Urea"] * st.anchor.xi)
    assert urea_in - urea_out == pytest.approx(0.0, abs=1e-9)
    one_hour = ls.advance_species(st.w_des, st.m_des_kg, st.m_des_kg, R323_FEED_DES_KGH,
                                  d.W_S208, d.M305_DES_KGH, y, R323_M314_DES,
                                  st.anchor.xi, 3600.0)
    assert max(abs(one_hour[k] - st.w_des[k]) for k in one_hour) < 1e-7


def test_the_flash_design_seed_is_stationary():
    st = d.F004_LIQUOR
    y, _ = ls.vapour(st, st.w_des, st.t_des_c, st.p_des_bara)
    one_hour = ls.advance_species(st.w_des, st.m_des_kg, st.m_des_kg, R323_M314_DES,
                                  d.W_S314, d.M701_DES_KGH, y, R323_M319_DES, 0.0, 3600.0)
    for k in ul.SOLUTION_SPECIES:
        assert one_hour[k] == pytest.approx(st.w_des[k], abs=1e-15)


# ======================================================================================
# Biuret
# ======================================================================================

@pytest.mark.parametrize("key", list(STAGES))
def test_the_design_extent_at_the_design_state(key):
    st = STAGES[key]
    assert ls.biuret_extent(st, st.m_des_kg, st.w_des, st.t_des_c) == st.anchor.xi


def test_biuret_follows_holdup_urea_and_temperature():
    st = d.C003_LIQUOR
    xi = st.anchor.xi
    assert ls.biuret_extent(st, 2.0 * st.m_des_kg, st.w_des, st.t_des_c) == 2.0 * xi
    w = dict(st.w_des, Urea=st.w_des["Urea"] * 1.1)
    assert ls.biuret_extent(st, st.m_des_kg, w, st.t_des_c) == pytest.approx(1.21 * xi,
                                                                            rel=1e-15)
    t = st.t_des_c + 10.0
    arrhenius = math.exp(BIURET_EA_JMOL / BIURET_R_GAS_J
                         * (1.0 / (st.t_des_c + 273.15) - 1.0 / (t + 273.15)))
    assert ls.biuret_extent(st, st.m_des_kg, st.w_des, t) / xi == pytest.approx(arrhenius,
                                                                              rel=1e-15)
    assert arrhenius == pytest.approx(1.820, abs=0.001)          # +10 C: 82 % more biuret


def test_a_stage_with_no_design_extent_never_makes_biuret():
    st = d.F004_LIQUOR
    assert ls.biuret_extent(st, 2.0 * st.m_des_kg, st.w_des, 150.0) == 0.0


# ======================================================================================
# The species advance
# ======================================================================================

def test_the_advance_keeps_the_composition_a_composition():
    st = d.C003_LIQUOR
    w = ls.advance_species(st.w_des, st.m_des_kg, st.m_des_kg, 1.3 * R323_FEED_DES_KGH,
                           d.W_S208, 0.0, st.anchor.y, 0.5 * R323_M314_DES, st.anchor.xi, 60.0)
    assert sum(w.values()) == pytest.approx(1.0, abs=1e-15)
    assert all(v >= 0.0 for v in w.values())
    #  Boil-up lost: the column keeps its ammonia and moves toward the feed.
    assert w["NH3"] > st.w_des["NH3"]


def test_an_empty_stage_keeps_its_last_composition():
    st = d.C003_LIQUOR
    w = ls.advance_species(st.w_des, st.m_des_kg, 0.0, 0.0, d.W_S208, 0.0, st.anchor.y,
                           0.0, 0.0, 1.0)
    assert w == st.w_des
