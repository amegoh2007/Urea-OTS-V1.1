"""Behaviour of the six-species urea liquor — `ureasim.thermo.urea_liquor`.

Equivalence with V1 is proven in `tests/equivalence/test_liquor_stage_equivalence.py`. This file
pins what the liquor physics DOES, and every number in it was measured before it was written.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_323 as d
from ureasim.data.design_point import R323_FEED_DES_KGH, R323_M314_DES, R323_M319_DES
from ureasim.thermo import iapws
from ureasim.thermo import urea_liquor as ul
from ureasim.thermo.domains import OutOfDomain

STAGES = {"C003": d.C003_LIQUOR, "F004": d.F004_LIQUOR, "F010": d.F010_LIQUOR}


# ======================================================================================
# The bubble point
# ======================================================================================

def test_pure_water_boils_at_its_saturation_temperature():
    assert ul.bubble_t_raoult(1.01325, {"H2O": 1.0}) == iapws.tsat_c(1.01325)


def test_dissolved_urea_raises_the_boiling_point_by_dilution_alone():
    """At 0.46 bar a water boils at about 80 C; the 80 % product boils at 100.5 C."""
    assert iapws.tsat_c(0.46) < 80.0
    assert ul.bubble_t_raoult(0.46, d.W_S317) == pytest.approx(100.46, abs=0.01)
    richer = dict(d.W_S317, Urea=0.85, H2O=d.W_S317["H2O"] - 0.05)
    assert ul.bubble_t_raoult(0.46, richer) > ul.bubble_t_raoult(0.46, d.W_S317)


def test_raoult_overshoots_where_the_liquor_carries_volatiles():
    """Why 323C003 and 323F004 use Raoult only as a matched departure: water alone would boil
    their liquors 33 and 16 C above the PFD temperature, because it ignores NH3 and CO2."""
    assert ul.bubble_t_raoult(d.C003_P_BARA, d.W_S314) - d.C003_T_SP_C == pytest.approx(
        33.06, abs=0.01)
    assert ul.bubble_t_raoult(d.F004_P_BARA, d.W_S319) - d.F004_T_SP_C == pytest.approx(
        15.87, abs=0.01)


def test_a_waterless_liquor_holds_the_critical_temperature():
    assert ul.bubble_t_raoult(4.1, {"Urea": 1.0}) == iapws.tsat_c(220.64)


def test_the_rigorous_surface_sits_below_the_pfd_temperatures():
    """The model's absolute bubble point is 0.6 to 3.3 C under each PFD temperature, which is
    why every caller takes the departure from it rather than the value itself."""
    assert d.C003_LIQUOR.tbub_des_c == pytest.approx(133.03, abs=0.01)
    assert d.F004_LIQUOR.tbub_des_c == pytest.approx(102.66, abs=0.01)
    assert d.F010_LIQUOR.tbub_des_c == pytest.approx(98.41, abs=0.01)


# ======================================================================================
# The vapour
# ======================================================================================

def test_the_vapour_always_sums_to_one():
    for st in STAGES.values():
        assert sum(ul.vapour_y(d.W_S208, st.anchor.alpha).values()) == pytest.approx(1.0,
                                                                                    abs=1e-15)


@pytest.mark.parametrize("key", list(STAGES))
def test_the_design_liquid_gives_back_the_design_vapour(key):
    st = STAGES[key]
    y = ul.vapour_y(st.w_des, st.anchor.alpha)
    for k in ul.SOLUTION_SPECIES:
        assert y[k] == pytest.approx(st.anchor.y[k], abs=2e-16)


def test_a_liquor_with_nothing_volatile_boils_off_water():
    y = ul.vapour_y({"Biuret": 1.0}, d.C003_LIQUOR.anchor.alpha)
    assert y["H2O"] == 1.0 and sum(y.values()) == 1.0


def test_323c003s_anchor_gives_urea_no_volatility():
    """PFD 314 closed on its urea against the drain (handoff B-20, decided 2026-10-10): the
    back-solve sends no urea overhead, so even the frozen-vector fallback boils none. On the table's
    row it left urea an apparent volatility of 7.92e-4 (PFD rounding), which the fallback boiled —
    V1's behaviour, asserted both ways in `test_liquor_stage_equivalence`."""
    assert d.C003_LIQUOR.anchor.alpha["Urea"] == 0.0
    assert ul.close_urea_on_drain(d.W_S208, R323_FEED_DES_KGH, R323_M314_DES,
                                  d.W_S314_TAB) == d.W_S314
    assert d.F010_LIQUOR.anchor.alpha["Urea"] == 0.0


def test_the_model_refuses_rather_than_extrapolates():
    """323F004's own liquor, 10 C above its flash temperature: the flash does not converge in
    its 60 sweeps, and the refusal is what sends the stage to its anchored vector. At 114 C it
    converges on sweep 41 — V1's 40-sweep budget refused it there (handoff A-9, decided
    2026-09-30)."""
    with pytest.raises(OutOfDomain):
        ul.model_alpha(d.W_S319, 116.0, d.F004_P_BARA)
    alpha, domain = ul.model_alpha(d.W_S319, 114.0, d.F004_P_BARA)
    assert domain == "electrolyte_gamma_phi"


# ======================================================================================
# The design back-solve
# ======================================================================================

@pytest.mark.parametrize("key", list(STAGES))
def test_every_stage_closes_without_clipping(key):
    assert STAGES[key].anchor.resid == 0


def test_the_biuret_extents_the_pfd_implies():
    assert d.C003_LIQUOR.anchor.xi == pytest.approx(0.660, abs=0.001)
    assert d.F004_LIQUOR.anchor.xi == 0.0
    #  323F010's biuret rows leave no room for formation; the carryover closes urea alone.
    assert d.F010_LIQUOR.anchor.xi == 0.0


def test_the_urea_in_323f010s_overhead_is_entrained_liquor():
    """PFD 790 lists 0.14 mol % urea, which cannot evaporate at 99 C: 0.696 % of the overhead is
    entrained liquor (0.611 % before PFD 319 was closed on its urea, B-20)."""
    assert d.F010_LIQUOR.anchor.entrain == pytest.approx(0.00696, abs=1e-5)
    assert d.F010_LIQUOR.anchor.y["Urea"] == 0.0
    assert d.C003_LIQUOR.anchor.entrain == 0.0


def test_the_column_recovers_eight_tonnes_of_ammonia():
    """PFD 305: what 323C003 sends to the LP carbamate condenser."""
    assert d.C003_LIQUOR.anchor.y["NH3"] * d.M305_DES_KGH == pytest.approx(8092.4, abs=0.1)


def test_the_reconciled_flash_liquid_is_conservative():
    w = d.W_S319
    for k in ("Urea", "NH3", "CO2"):
        assert w[k] <= R323_M314_DES * d.W_S314[k] / R323_M319_DES * (1 + 1e-15)
    #  Biuret is conserved exactly, then renormalised with the rest of the row.
    assert w["Biuret"] == pytest.approx(R323_M314_DES * d.W_S314["Biuret"] / R323_M319_DES,
                                        rel=1e-3)
    assert sum(w.values()) == pytest.approx(1.0, abs=1e-15)
