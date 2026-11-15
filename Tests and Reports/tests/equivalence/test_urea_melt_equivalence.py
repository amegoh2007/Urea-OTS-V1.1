"""V1 <-> V1.1 equivalence for the urea melt's anchored equilibrium — `ureasim.thermo.urea_melt`.

V1's ``evap_w_eq``, ``conc_infer_324`` and ``evap_thermo_diag`` are executed from V1's own
``main.py`` (lifted, on V1's own ``thermo_extended_uniquac``) and compared with the port over both
stages' design points, a grid across and beyond the model's window, and non-finite arguments —
the port called on the published parameter (``a_urea_water_k=None``) and no ceiling. Every value
is ``==``. The stages run the parameter refitted to the PFD and the ceiling (handoff B-58, decided
2026-10-01); the last tests run that departure both ways.
"""

from __future__ import annotations

import math

import pytest

from ureasim.data import unit_324 as d
from ureasim.thermo import urea_melt as um
from ureasim.thermo.domains import NONVOLATILE
from tests.equivalence.v1_loader import lift, load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)


@pytest.fixture(scope="module")
def v1():
    return lift(["evap_w_eq", "conc_infer_324", "evap_thermo_diag", "R324_W_EV1", "R324_W_EV2",
                 "R324_E001_T_SP_C", "R324_E003_T_SP_C", "R324_F001_P_BARA", "R324_F003_P_BARA"],
                seed={"math": math, "extended_uniquac": load("thermo_extended_uniquac")})


STAGES = (("324E001", d.E001_W_UREA_DES, d.E001_T_DES_C, d.F001_P_DES_BARA),
          ("324E003", d.E003_W_UREA_DES, d.E003_T_DES_C, d.F003_P_DES_BARA))
TEMPS = (60.0, 99.0, 99.5, 110.0, 125.0, 130.0, 133.7, 140.0, 151.9, 175.0, 199.9, 205.0)
PRESSURES = (0.01, 0.02, 0.05, 0.1, 0.131, 0.2, 0.33, 0.5, 0.9, 1.0, 1.2)


def test_the_design_anchors_are_v1s(v1):
    assert (d.E001_W_UREA_DES, d.E001_T_DES_C, d.F001_P_DES_BARA) == (
        v1["R324_W_EV1"], v1["R324_E001_T_SP_C"], v1["R324_F001_P_BARA"])
    assert (d.E003_W_UREA_DES, d.E003_T_DES_C, d.F003_P_DES_BARA) == (
        v1["R324_W_EV2"], v1["R324_E003_T_SP_C"], v1["R324_F003_P_BARA"])


@pytest.mark.parametrize("tag, w_des, t_des, p_des", STAGES)
def test_the_equilibrium_and_the_soft_sensor_are_v1s(v1, tag, w_des, t_des, p_des):
    """Both stages over 132 states across and beyond the window: ``==``, the design point
    exactly its PFD strength."""
    assert um.equilibrium_urea_fraction(t_des, p_des, w_des, t_des, p_des,
                                        a_urea_water_k=None) == w_des
    for t in TEMPS:
        for p in PRESSURES:
            mine = um.equilibrium_urea_fraction(t, p, w_des, t_des, p_des, a_urea_water_k=None)
            assert mine == v1["evap_w_eq"](t, p, w_des, t_des, p_des), (tag, t, p)
            assert (um.melt_concentration_pct(w_des, t_des, p_des, t, p, a_urea_water_k=None)
                    == v1["conc_infer_324"](w_des, t_des, p_des, t, p)), (tag, t, p)


@pytest.mark.parametrize("t, p", [(math.nan, 0.131), (140.0, math.nan), (math.inf, 0.33),
                                  (-math.inf, 0.33), (130.0, math.inf)])
def test_non_finite_states_are_v1s(v1, t, p):
    for _, w_des, t_des, p_des in STAGES:
        assert (um.equilibrium_urea_fraction(t, p, w_des, t_des, p_des, a_urea_water_k=None)
                == v1["evap_w_eq"](t, p, w_des, t_des, p_des))


def test_the_diagnostics_are_v1s(v1):
    """Validity status and P-x residual inside the window, the refusal outside it."""
    for t in TEMPS:
        for p in PRESSURES:
            w = um.equilibrium_urea_fraction(t, p, d.E003_W_UREA_DES, d.E003_T_DES_C,
                                             d.F003_P_DES_BARA, a_urea_water_k=None)
            assert (um.melt_diagnostics(t, p, w, a_urea_water_k=None)
                    == v1["evap_thermo_diag"](t, p, w)), (t, p)


def _slopes(f, t, p):
    """d(wt%)/dK and d(wt%) per 0.01 bar, central differences of 1 K and 1 %."""
    return ((f(t + 1.0, p) - f(t - 1.0, p)) / 2.0 * 100.0,
            (f(t, p * 1.01) - f(t, p * 0.99)) / (0.02 * p) * 100.0 * 0.01)


@pytest.mark.parametrize("tag, w_des, t_des, p_des, v1_slopes, port_slopes", [
    ("324E001", 0.9431, 130.0, 0.33, (0.2489, -0.2400), (0.1745, -0.1732)),
    ("324E003", 0.9771, 140.0, 0.131, (0.0692, -0.1765), (0.0451, -0.1190)),
])
def test_the_melt_on_the_refit_decided_divergence(v1, tag, w_des, t_des, p_des, v1_slopes,
                                                  port_slopes):
    """B-58. Both hold the PFD melt to the bit at design. V1's strength (the published -211.96 K)
    moves +0.249 and +0.069 wt% per kelvin; the port's (refitted to the PFD, -85.3 K) +0.175 and
    +0.045 — TIC-324001's process gain 30 % lower, on the plant's."""
    def port(t, p):
        return um.equilibrium_urea_fraction(t, p, w_des, t_des, p_des,
                                            a_urea_water_k=d.MELT_A_UREA_WATER_K)

    def mine_v1(t, p):
        return v1["evap_w_eq"](t, p, w_des, t_des, p_des)

    assert port(t_des, p_des) == mine_v1(t_des, p_des) == w_des
    assert _slopes(mine_v1, t_des, p_des) == pytest.approx(v1_slopes, abs=1e-4)
    assert _slopes(port, t_des, p_des) == pytest.approx(port_slopes, abs=1e-4)


def test_the_melt_under_its_ceiling_decided_divergence(v1):
    """B-58. Stage 2 fed PFD 401's melt (biuret 0.69, formaldehyde 0.0095 wt%). V1 has no ceiling:
    at 140 C and 0.03 bar a its strength is 99.49 %, past what its biuret leaves — it would boil
    the biuret as water. The port holds the melt at the ceiling, 99.26 % for 401's own feed; on
    the refit the strength there is 98.90 %, under it."""
    w_401 = {"Urea": 94.31, "Biuret": 0.69, "HCHO": 0.00948}
    ceiling = um.strength_ceiling(w_401["Urea"], sum(w_401[k] for k in NONVOLATILE
                                                    if k != "Urea"))
    assert ceiling == pytest.approx(0.992638, abs=1e-6)
    w_v1 = v1["evap_w_eq"](140.0, 0.03, 0.9771, 140.0, 0.131)
    assert w_v1 == pytest.approx(0.994942, abs=1e-6) and w_v1 > ceiling
    assert um.equilibrium_urea_fraction(140.0, 0.03, 0.9771, 140.0, 0.131, a_urea_water_k=None,
                                        w_max=ceiling) == ceiling
    on_refit = um.equilibrium_urea_fraction(140.0, 0.03, 0.9771, 140.0, 0.131,
                                            a_urea_water_k=d.MELT_A_UREA_WATER_K, w_max=ceiling)
    assert on_refit == pytest.approx(0.988971, abs=1e-6) and on_refit < ceiling
