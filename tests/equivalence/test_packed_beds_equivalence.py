"""V1 <-> V1.1 equivalence for 322C001's packed beds and the thermodynamics under them.

What is being proved
--------------------
V1's ``backend/packed_absorber.py`` is a module, so it is executed, not transcribed: loaded as a
real module on V1's own ``props_nh3co2h2o`` and ``iapws_if97``, and driven beside
`ureasim.units.absorption.packed_beds`, `ureasim.thermo.ammonia_backpressure` and
`ureasim.thermo.transport_properties` with the same arguments. Every comparison is ``==``:

  * the transport properties over the temperatures and pressures the column sees, and beyond;
  * the back-pressure, its slopes and the heats of absorption over liquors from clean condensate
    to a loaded sump, inside the speciation's 10-100 C and on van 't Hoff beyond it;
  * Onda's wetted fraction and transfer units, the liquid residence and Colburn's outlet;
  * the two beds solved over gas loads, compositions, washes, temperatures and pressures, one
    pass and relaxed, with and without the upper bed's uptake handed in;
  * the calibration, in `test_lp_absorber_equivalence.py`, on the design gas.
"""

from __future__ import annotations

import itertools

import pytest

from ureasim.data import unit_322c001 as c
from ureasim.thermo import ammonia_backpressure as bp
from ureasim.thermo import transport_properties as tp
from ureasim.units.absorption import lp_absorber as la
from ureasim.units.absorption import packed_beds as pb
from tests.equivalence.v1_loader import load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)


@pytest.fixture(scope="module")
def pa():
    return load("packed_absorber")


T_K = [273.15, 283.15, 300.0, 316.15, 330.0, 373.15, 420.0]


@pytest.mark.parametrize("t_k", T_K)
def test_the_transport_properties_are_v1s(pa, t_k):
    assert (tp.water_mu_pas(t_k), tp.water_sigma_nm(t_k), tp.gas_mu_pas(t_k)) == (
        pa.water_mu_pas(t_k), pa.water_sigma_nm(t_k), pa.gas_mu_pas(t_k))
    for sp, p in itertools.product(("NH3", "CO2", "N2"), (1.0e5, 3.9e5, 31.0e5)):
        assert tp.diffusivity_m2s(sp, t_k, p) == pa.diffusivity_m2s(sp, t_k, p)
    assert tp.FULLER_VOLUMES == pa._FULLER_V


def test_the_grid_is_v1s(pa):
    assert (bp.GRID_RATIO, bp.GRID_DT, bp.N_FLOOR, bp.C_FLOOR, bp.T_SPEC_LO_K, bp.T_SPEC_HI_K) == (
        pa.GRID_RATIO, pa.GRID_DT, pa.N_FLOOR, pa.C_FLOOR, pa.T_SPEC_LO_K, pa.T_SPEC_HI_K)


LIQUORS = {
    "clean condensate": {"H2O": 1.0},
    "PFD 755": dict(c.W_S755),
    "the design sump": dict(c.W_C001_DES),
    "a loaded sump": {"NH3": 0.09, "CO2": 0.06, "H2O": 0.84, "Urea": 0.01},
    "ammonia-rich": {"NH3": 0.15, "CO2": 0.01, "H2O": 0.84},
    "the upper bed's effluent": {"H2O": 0.98, "NH3": 0.015, "CO2": 0.005},
}


@pytest.mark.parametrize("name", list(LIQUORS))
@pytest.mark.parametrize("t_c", [-5.0, 10.0, 25.0, 43.0, 46.0, 57.3, 99.9, 100.0, 130.0])
def test_the_back_pressure_and_the_heats_are_v1s(pa, name, t_c):
    w = LIQUORS[name]
    assert bp.molalities(w) == pa.molalities(w)
    assert bp.back_pressure(w, t_c) == pa.back_pressure(w, t_c)
    assert bp.heat_of_absorption_j_mol(w, t_c) == pa.heat_of_absorption_j_mol(w, t_c)
    assert bp.henry_nh3_pa(t_c + 273.15) == pa.henry_nh3_pa(t_c + 273.15)


@pytest.mark.parametrize("l_flux", [0.0, 0.01, 0.6, 10.5, 40.0])
@pytest.mark.parametrize("t_k", [300.0, 316.15, 330.0])
def test_onda_and_the_residence_are_v1s(pa, l_flux, t_k):
    assert pb.wetted_fraction(l_flux, t_k) == pa.wetted_fraction(l_flux, t_k)
    for bed, theirs in ((pb.BED_LO, pa.BED_LO), (pb.BED_UP, pa.BED_UP)):
        m_liq = l_flux * 3600.0 * bed.area_m2
        assert bed.area_m2 == pa.area_m2(theirs)
        assert pb.liquid_residence_s(bed, m_liq, t_k) == pa.liquid_residence_s(theirs, m_liq, t_k)
        for sp, (m_gas, n_gas, p) in itertools.product(
                ("NH3", "CO2"), ((1708.3, 64.8, 3.9e5), (0.0, 0.0, 3.9e5), (5000.0, 230.0, 6.0e5))):
            assert pb.onda_ntu(sp, bed, m_liq, m_gas, n_gas, t_k, p) == pa.onda_ntu(
                sp, theirs, m_liq, m_gas, n_gas, t_k, p)


@pytest.mark.parametrize("y_in, y_star, ntu, lam", [
    (0.08, 0.0, 3.0, 0.2), (0.08, 0.01, 0.0, 0.5), (0.08, 0.001, 2.5, 1.0),
    (0.08, 0.001, 2.5, 1.0 + 5e-10), (0.02, 0.03, 4.0, 3.0), (0.5, 0.0, 900.0, 0.1),
])
def test_colburn_is_v1s(pa, y_in, y_star, ntu, lam):
    assert pb.colburn(y_in, y_star, ntu, lam) == pa.colburn(y_in, y_star, ntu, lam)


def _cal(pa):
    pin = la.design_pin()
    return pin, {"NH3": pin.cal.nh3, "CO2": pin.cal.co2, "a_w": pin.cal.a_w,
                 "abs_up": dict(pin.cal.abs_up)}


CASES = list(itertools.product(
    [(1.0, 1.0, 1.0), (0.0, 1.0, 1.0), (1.6, 1.0, 1.0), (1.2, 6.0, 3.0), (1.4, 8.0, 3.5)],
    [(43.0, 3.9, 31478.0, 1750.0), (55.0, 4.4, 18000.0, 1750.0), (43.0, 3.9, 31478.0, 0.0),
     (40.0, 6.0, 0.0, 3500.0), (120.0, 3.9, 31478.0, 1750.0)],
    ["the design sump", "a loaded sump"],
    [1, 200],
))


@pytest.mark.parametrize("gas, wash, liquor, passes", CASES)
def test_the_two_beds_are_v1s(pa, gas, wash, liquor, passes):
    pin, cal = _cal(pa)
    scale, nh3, co2 = gas
    comp = {k: v * scale * (nh3 if k == "NH3" else co2 if k == "CO2" else 1.0)
            for k, v in pin.gas_kmolh.items()}
    t_liq, p, m755, mcpl = wash
    w = LIQUORS[liquor]
    for up_ours, up_theirs in ((None, None), (pin.cal.abs_up, cal["abs_up"])):
        a = pa.solve(comp, t_liq, 46.0, p, m755, c.W_S755, mcpl, w, cal, abs_up=up_theirs,
                     passes=passes)
        b = pb.solve(comp, t_liq, 46.0, p, m755, c.W_S755, mcpl, w, pin.cal, abs_up=up_ours,
                     passes=passes)
        assert (a["absorbed_kmolh"], a["vent_kmolh"], a["ntu"], a["y_star_lo"], a["dT_up"],
                a["abs_up"]) == (b.absorbed_kmolh, b.vent_kmolh, b.ntu, b.y_star_lo, b.dt_up_k,
                                 b.abs_up)
