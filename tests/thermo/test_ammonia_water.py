"""Behaviour of the desorption train's liquor — `ureasim.thermo.ammonia_water`.

Equivalence with V1 is proven in `tests/equivalence/test_first_desorber_equivalence.py` (the
three anchors, the Kremser stage, and every tick of 328C002). This file pins what the layer
DOES: vapour rows read as mole % close carbon and reproduce the PFD's molar mass; each anchor
closes its stage per species; Kremser's residual and its single-stage inverse; the rigorous
volatility ratio exactly 1 at its reference and flat beyond the fitted window; the liquor's
bubble pressure above water's, carried on the water line beyond the window.
"""

from __future__ import annotations

import pytest

from ureasim.data import desorption_train as t
from ureasim.thermo import ammonia_water as aw
from ureasim.thermo import iapws
from ureasim.thermo.urea_liquor import SOLUTION_SPECIES, vapour_y


def test_a_vapour_row_is_mole_percent():
    """PFD 737 read as mole % gives the PFD's own 20.81 kg/kmol; read as mass %, 18.94."""
    assert aw.vapour_molar_mass(t.W_S737) == pytest.approx(20.8093, abs=1e-4)
    assert sum(t.W_S737.values()) == pytest.approx(1.0, abs=1e-15)
    as_mass = {"CO2": 0.1232, "H2O": 0.4621, "NH3": 0.4147}
    assert aw.vapour_molar_mass(as_mass) == pytest.approx(18.9392, abs=1e-4)


#: The back-solve's own hydrolysis coefficients [kg/kmol]: CO2 at its molar mass, where the
#: runtime's `HYDROLYSIS_NU` writes CO2 as the closer (V1 `_des_stage_anchor` and `DES_HYD_NU`).
ANCHOR_NU = {"Urea": -60.056, "H2O": -18.0152, "NH3": 2.0 * 17.0304, "CO2": 44.0098}


def test_the_hydrolyser_anchor_closes_every_species():
    """328C003: 4.2734 kmol/h of urea hydrolysed, and every species closes on the back-solve's
    own stoichiometry — but water, which closes the overhead's TOTAL and so carries the 6e-4
    kg/kmol that stoichiometry loses: 0.0026 kg/h at the design extent. The runtime's
    `HYDROLYSIS_NU` writes CO2 as the closer, 6e-4 kg/kmol heavier, and conserves it; both are
    V1's."""
    a = t.DES_C003
    assert a.xi == pytest.approx(4.27342, abs=1e-5) and a.resid == 0.0
    feeds = [(t.W_S743, t.C003_M746_DES_KGH), (t.W_STEAM, t.C003_M911_DES_KGH)]
    excess = sum(ANCHOR_NU.values()) * a.xi
    for k in SOLUTION_SPECIES:
        m_in = sum(m * w[k] for w, m in feeds)
        gap = (m_in + ANCHOR_NU.get(k, 0.0) * a.xi - t.C003_M747_DES_KGH * t.W_S747[k]
               - t.C003_M748_DES_KGH * a.y[k])
        assert gap == pytest.approx(excess if k == "H2O" else 0.0, abs=1e-9), k
    assert (aw.HYDROLYSIS_NU["CO2"] - ANCHOR_NU["CO2"]) * a.xi == pytest.approx(0.002564, abs=1e-6)


def test_328c002s_anchor_clips_the_urea_the_rows_cannot_close():
    """328C002: the feed rows bring 0.34 kg/h less urea than 743 carries — inside their rounding.
    The negative vapour is clipped and reported, never hidden; the back-solved overhead sits
    within 2.3e-4 of PFD 737."""
    a = t.DES_C002
    assert a.xi == 0.0 and a.resid == pytest.approx(-0.3371, abs=1e-4)
    assert a.y["Urea"] == 0.0 and a.alpha["Urea"] == 0.0 and a.alpha["H2O"] == 1.0
    assert a.dev == pytest.approx(2.343e-4, abs=1e-7)


def test_the_hydrolysis_stoichiometry_makes_no_mass():
    assert abs(sum(aw.HYDROLYSIS_NU.values())) < 1e-12


def test_the_back_solved_alpha_returns_the_design_vapour():
    assert vapour_y(t.W_S743, t.DES_C002.alpha) == pytest.approx(t.DES_C002.y, abs=1e-15)


@pytest.mark.parametrize("s, r", [(1.0, 0.1), (1.0 + 1e-10, 0.1), (2.0, 1.0 / 1023.0),
                                  (0.5, 0.5 / (1.0 - 0.5 ** 10))])
def test_kremsers_residual(s, r):
    """r = (S - 1)/(S^(N+1) - 1) at N = 9, and 1/(N + 1) at S = 1."""
    assert aw.kremser_residual(s, 9.0) == pytest.approx(r, rel=1e-8)


def test_the_single_stage_volatility_strips_what_the_column_strips():
    """One well-mixed stage on alpha_eff leaves overhead exactly 1 - r of a trace species."""
    r = aw.kremser_residual(2.15, 9.53)
    k = aw.kremser_volatility(33769.0, 7645.0, r)
    assert 7645.0 * k / (7645.0 * k + 33769.0) == pytest.approx(1.0 - r, rel=1e-14)


def test_the_volatility_ratio_is_one_at_its_reference():
    ratio, domain = aw.relative_volatility_ratio(t.W_S743, 139.0, 3.5139, 139.0, 3.5139)
    assert ratio == {"NH3": 1.0, "CO2": 1.0} and domain == "electrolyte_gamma_phi"


def test_a_hotter_column_strips_its_ammonia_less_and_its_co2_more():
    """Six degrees hotter at 4.2 bar a: NH3's relative volatility falls 4 %, CO2's rises 16 %."""
    ratio, _ = aw.relative_volatility_ratio(t.W_S743, 145.0, 4.2, 139.0, 3.5139)
    assert ratio["NH3"] == pytest.approx(0.95772, abs=1e-5)
    assert ratio["CO2"] == pytest.approx(1.16335, abs=1e-5)


def test_the_ratio_is_flat_beyond_the_fitted_window():
    beyond, _ = aw.relative_volatility_ratio(t.W_S743, 300.0, 4.2, 139.0, 3.5139)
    edge, _ = aw.relative_volatility_ratio(t.W_S743, aw.K_RATIO_T_HI_C, 4.2, 139.0, 3.5139)
    assert beyond == edge


def test_the_liquors_vapour_pressure():
    """743's 0.63 % NH3 lifts its bubble pressure over water's: 3.93 against 3.51 bar a at 139 C,
    14.97 against 12.55 at 190 C. Beyond 209.95 C it follows the water line from the edge."""
    assert aw.liquor_pv_bara(t.W_S743, 139.0) == pytest.approx(3.9349, abs=1e-4)
    assert aw.liquor_pv_bara(t.W_S743, 190.0) == pytest.approx(14.9696, abs=1e-4)
    edge = aw.liquor_pv_bara(t.W_S743, aw.K_RATIO_T_HI_C)
    assert aw.liquor_pv_bara(t.W_S743, 230.0) == pytest.approx(
        edge * iapws.psat_bara(230.0) / iapws.psat_bara(aw.K_RATIO_T_HI_C), rel=1e-14)


def test_the_stage_builder_is_exact_at_its_reference():
    st = aw.desorber_stage(t.DES_C002, 9.5, 7645.0, 33769.0, 3.5139, 9.5)
    assert st.s == 9.5 * (7645.0 / 33769.0)
    assert st.k == aw.kremser_volatility(33769.0, 7645.0, aw.kremser_residual(st.s, 9.5))
    assert st.t_eq_c == iapws.tsat_c(3.5139)


def test_the_condensate_conductivity():
    """AI-328701: pure water reads zero; 1 ppm of ammonia and 1 ppm of urea, 6.93 uS/cm; the
    reading rises with the ammonia, weakly (a weak base), and the urea's hydrolysed part adds."""
    assert aw.condensate_conductivity_us_cm(0.0, 0.0, 0.0) == 0.0
    assert aw.condensate_conductivity_us_cm(1.0, 1.0, 0.0) == pytest.approx(6.9332, abs=1e-4)
    one, ten = (aw.condensate_conductivity_us_cm(n, 0.0, 0.0) for n in (1.0, 10.0))
    assert one < ten < 10.0 * one
    assert aw.condensate_conductivity_us_cm(1.0, 5.0, 0.0) > aw.condensate_conductivity_us_cm(
        1.0, 0.0, 0.0)
