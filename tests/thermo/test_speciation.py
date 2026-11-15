"""Liquid speciation of NH3-CO2-H2O — `ureasim.thermo.speciation`.

Pinned: whatever the loading and temperature, the solved liquor closes its ammonia, its carbon and
its charge to the solver's tolerance, every molality is positive, and the reported ionic strength
is the molalities' own; an ammonia-rich liquor is alkaline and a CO2-rich one less so, carbamate
growing with the ammonia that is free to take up the carbon.
"""

from __future__ import annotations

import pytest

from ureasim.thermo.speciation import speciate

CHARGE = {"H+": 1, "OH-": -1, "NH4+": 1, "HCO3-": -1, "CO3--": -2, "NH2COO-": -1,
          "NH3(aq)": 0, "CO2(aq)": 0}


@pytest.mark.parametrize("n_tot, c_tot, t_k", [
    (5.0, 2.0, 350.0), (1.0, 0.2, 310.0), (10.0, 4.5, 360.0), (3.0, 2.5, 330.0)])
def test_the_balances_close(n_tot, c_tot, t_k):
    m = speciate(n_tot, c_tot, t_k)
    assert m["resid"] < 1e-9
    assert all(m[s] > 0.0 for s in CHARGE)
    assert m["NH3(aq)"] + m["NH4+"] + m["NH2COO-"] == pytest.approx(n_tot, rel=1e-9)
    assert (m["CO2(aq)"] + m["HCO3-"] + m["CO3--"] + m["NH2COO-"]
            == pytest.approx(c_tot, rel=1e-9))
    assert sum(z * m[s] for s, z in CHARGE.items()) == pytest.approx(0.0, abs=1e-9 * n_tot)
    assert m["I"] == pytest.approx(0.5 * sum(z * z * m[s] for s, z in CHARGE.items()),
                                   rel=1e-12)
    assert 0.0 < m["H2O"] < 1.0


def test_ammonia_rich_liquor_is_alkaline_and_carbon_lowers_the_ph():
    lean = speciate(5.0, 0.5, 330.0)
    rich = speciate(5.0, 2.5, 330.0)
    assert lean["pH"] > rich["pH"] > 7.0
    assert rich["NH2COO-"] > lean["NH2COO-"]
