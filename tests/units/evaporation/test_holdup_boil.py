"""Behaviour of the held liquor's own boil-off — `ureasim.units.evaporation.holdup_boil`.

Handoff B-62, decided 2026-10-01: the separator's holdup boils past its own boiling point at the
vacuum; handoff B-24, decided 2026-10-02: 323F010's liquor past its bubble point. The stages' use
of it is run both ways in the stages' decided-equivalence tests; this file pins the relations
themselves: nothing at the design state or below it, the boiled holdup on its equilibrium or its
bubble point with its latent heat paid, the ceiling and the floor.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_324 as d
from ureasim.thermo.urea_melt import equilibrium_urea_fraction, strength_ceiling
from ureasim.units.evaporation.holdup_boil import holdup_boil

W = dict(d.W_S401)
M = d.F001_M_DES_KG
C = 15000.0
LAM = d.E001_LAMBDA_KJKG
Y_U = 0.0006


def _boil(t_c, p=d.F001_P_DES_BARA, m=M, w=W, floor=1.0):
    return holdup_boil(t_c, p, m, w, C, LAM, Y_U, floor, 0.1, w_des=W["Urea"],
                       t_des_c=d.E001_T_DES_C, p_des_bara=d.F001_P_DES_BARA,
                       a_urea_water_k=d.MELT_A_UREA_WATER_K)


def test_the_design_holdup_sits_at_its_boiling_point():
    """PFD 401 at 130 C and 0.33 bar a boils nothing; cooler, or under a weaker vacuum, nothing."""
    assert _boil(130.0) == (0.0, 130.0)
    assert _boil(129.0) == (0.0, 129.0)
    assert _boil(130.0, p=0.36) == (0.0, 130.0)


def test_a_superheated_holdup_boils_to_its_equilibrium():
    """At 131 C the design holdup boils 3.52 kg in one tick: the latent heat brings it back to
    130.489 C, where its strengthened melt is its equilibrium to 1e-14."""
    kgh, t = _boil(131.0)
    x = kgh * 0.1 / 3600.0
    assert x == pytest.approx(3.5248, abs=1e-4)
    assert t == pytest.approx(131.0 - x * LAM / C, abs=1e-12)
    w_after = (W["Urea"] * M - Y_U * x) / (M - x)
    w_max = strength_ceiling(W["Urea"], W["Biuret"] + W["HCHO"])
    assert equilibrium_urea_fraction(t, d.F001_P_DES_BARA, W["Urea"], d.E001_T_DES_C,
                                     d.F001_P_DES_BARA, a_urea_water_k=d.MELT_A_UREA_WATER_K,
                                     w_max=w_max) == pytest.approx(w_after, abs=1e-14)


def test_a_dry_melt_and_the_floor_boil_nothing_more():
    """A holdup at its ceiling — its water gone — has nothing to boil; one at its floor neither;
    a 90 % melt 50 g above it boils those 50 g and no more. (A 50 % liquor half a kilogram above
    it boiled that half kilogram until B-86, decided 2026-10-09: its boiling point at 0.33 bar a is
    below the melt model's 99 C window, so it does not boil.)"""
    dry = {"Urea": 0.99, "Biuret": 0.01}
    assert _boil(160.0, w=dry) == (0.0, 160.0)
    assert _boil(160.0, m=1.0) == (0.0, 160.0)
    assert _boil(135.0, m=1.5, w={"Urea": 0.5, "H2O": 0.5}) == (0.0, 135.0)
    kgh, t = _boil(135.0, m=1.05, w={"Urea": 0.9, "H2O": 0.1})
    assert kgh * 0.1 / 3600.0 == pytest.approx(0.05, rel=1e-12)
    assert t == pytest.approx(135.0 - 0.05 * LAM / C, rel=1e-12)


# ======================================================================================
# 323F010's liquor (handoff B-24, decided 2026-10-02): the bubble point of its composition
# ======================================================================================

def _liquor(t_c, p=0.46, m=None, c=None, floor=1.0):
    from ureasim.data import unit_323 as d3
    from ureasim.units import liquor_stage
    from ureasim.units.evaporation.holdup_boil import liquor_boil
    from ureasim.units.recirc import pre_evaporator as pe
    w = dict(d3.W_S317)
    m = d3.F010_M_DES_KG if m is None else m
    c = m * d3.CP_F010_DES + 50.0 if c is None else c
    f = d3.F010_LIQUOR.anchor.entrain
    y = {k: (1.0 - f) * pe.Y_VAP_DES.get(k, 0.0) + f * w.get(k, 0.0) for k in w}

    def bubble(x):
        return liquor_stage.bubble_t(d3.F010_LIQUOR, x, p)
    kgh, t = liquor_boil(t_c, m, w, c, d3.EVAP_LAMBDA_KJKG, y, floor, 0.1, bubble)
    x = kgh * 0.1 / 3600.0
    after = {k: (w[k] * m - y.get(k, 0.0) * x) / (m - x) for k in w}
    return kgh, t, x, bubble(after), after, d3.EVAP_LAMBDA_KJKG


def test_a_melt_whose_vapour_is_urea_does_not_boil():
    """Phase 7's cold start (As-Built §LXII.4): 324F001 held dry on its floor, 84.25 % urea with
    the rest biuret and no water, so the vapour by relative volatility is pure urea, above the
    85.51 % ceiling. x_max's denominator, w_max - y_u, turned the bound negative and the stage
    condensed 85.7 kg a tick of vapour it did not hold, its latent heat driving the melt to 1600 C.
    Such a melt does not boil."""
    w = {k: 0.0 for k in W}
    w.update({"Urea": 0.8425233648385348, "Biuret": 1.0 - 0.8425233648385348})
    out = holdup_boil(103.53126869051943, 0.3511132547577057, 986.6293385225069, w,
                      2479.6528301277276, 2174.0, 1.0, 1.5, 0.1, w_des=W["Urea"],
                      t_des_c=d.E001_T_DES_C, p_des_bara=d.F001_P_DES_BARA,
                      a_urea_water_k=d.MELT_A_UREA_WATER_K)
    assert out == (0.0, 103.53126869051943)


def test_a_melt_below_the_models_window_does_not_boil():
    """Phase 7's cold start (As-Built §LXII.4): 324F003 at 0.17 bar a, 90.97 % urea, a hair weaker
    than the 91.01 % the melt model holds at its window's 99 C edge, read as superheated at any
    temperature and boiled itself down to -770 C. Below the window the melt does not boil.

    Handoff B-86, decided 2026-10-09 (option c): nor does it boil above the window while its
    boiling point at the live vacuum lies below 99 C — at 99.5 C and at 120 C it holds its
    temperature, V1's closure alone, where session 46's bound boiled it down to the edge. At
    0.2879 bar a the edge's strength is 84.77 %, so the cold start's 89.49 % melt at 108.9 C has
    its boiling point inside the window and still boils, 462.18 kg/h, to 108.8969 C."""
    from ureasim.units.evaporation.holdup_boil import T_WINDOW_LO_C
    w = {k: 0.0 for k in W}
    w.update({"Urea": 0.9097, "H2O": 0.0903})
    args = dict(w_des=d.E003_W_UREA_DES, t_des_c=d.E003_T_DES_C, p_des_bara=d.F003_P_DES_BARA,
                a_urea_water_k=d.MELT_A_UREA_WATER_K)
    assert T_WINDOW_LO_C == pytest.approx(99.0, abs=1e-12)
    assert holdup_boil(3.0, 0.1735, 4471.0, w, 9000.0, LAM, Y_U, 1.0, 0.1, **args) == (0.0, 3.0)
    assert holdup_boil(99.5, 0.1735, 4471.0, w, 9000.0, LAM, Y_U, 1.0, 0.1, **args) == (0.0, 99.5)
    assert holdup_boil(120.0, 0.1735, 4471.0, w, 9000.0, LAM, Y_U, 1.0, 0.1, **args) == (
        0.0, 120.0)
    w.update({"Urea": 0.8949, "H2O": 0.1051})
    kgh, t = holdup_boil(108.9, 0.2879, 4471.0, w, 9000.0, LAM, Y_U, 1.0, 0.1, **args)
    assert (kgh, t) == (pytest.approx(462.184, abs=1e-3), pytest.approx(108.8969, abs=1e-4))


def test_the_design_liquor_sits_at_its_bubble_point():
    """PFD 317 at 99 C and 0.46 bar a boils nothing; cooler, nothing."""
    assert _liquor(99.0)[:2] == (0.0, 99.0)
    assert _liquor(98.0)[:2] == (0.0, 98.0)


@pytest.mark.parametrize("t_c, p, x_kg, t_after, urea", [
    (100.0, 0.46, 4.7726, 99.2983, 0.800630),
    (99.0, 0.40, 20.1471, 96.0379, 0.802613),
])
def test_a_superheated_liquor_boils_to_its_bubble_point(t_c, p, x_kg, t_after, urea):
    """One kelvin above its bubble point, the design liquor boils 4.77 kg in a tick and comes back
    to its strengthened bubble point, 99.298 C; under a 0.40 bar a vacuum at 99 C it boils 20.1 kg
    down to 96.04 C. The latent heat is paid out of the step and the liquor ends on its bubble
    point to 1e-9 K. (Re-measured on PFD 319 closed on its urea, B-20, decided 2026-10-10.)"""
    kgh, t, x, t_bub, after, lam = _liquor(t_c, p=p)
    assert x == pytest.approx(x_kg, abs=1e-4) and t == pytest.approx(t_after, abs=1e-4)
    assert abs(t - t_bub) < 1e-9
    assert after["Urea"] == pytest.approx(urea, abs=1e-6)
    assert sum(after.values()) == pytest.approx(1.0, abs=1e-12)


def test_nothing_below_the_liquors_floor_boils():
    """Half a gram above its 1 kg floor, a liquor 20 K superheated boils that half gram and no
    more."""
    kgh, t, x, _, _, lam = _liquor(120.0, m=1.0005, c=100.0)
    assert x == pytest.approx(0.0005, rel=1e-9)
    assert t == pytest.approx(120.0 - 0.0005 * lam / 100.0, rel=1e-12)
