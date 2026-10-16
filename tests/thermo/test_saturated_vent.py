"""Behaviour of the saturated-gas vent law — `ureasim.thermo.saturated_vent`.

Equivalence with V1's ``vacuum_condenser`` is proven in
`tests/equivalence/test_atmospheric_absorber_equivalence.py`. This file pins what the law DOES:
the PFD vent row reproduced at its design state, the vapour a gas holds rising with the
temperature and falling with the pressure, and the two bounds — no condensable in excess of
what arrives, every inert out.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_323c005 as c
from ureasim.thermo import saturated_vent as sv

ROW_341 = c.PFD_341_MOL_PCT


def _inlet(inert: float = 1.0, cond: float = 1.0) -> dict:
    return {k: v * (inert if k in sv.INERT else cond) for k, v in c.C005_N702_KMOLH.items()}


def test_the_design_state_gives_back_the_pfd_vent_row():
    """At its design pressure and temperature the law carries exactly the row's condensable
    fraction on the inerts, split as the row splits it."""
    spec = sv.saturated_gas_spec(ROW_341, 1.0, 43.0)
    n_i = 10.0
    vent = sv.vent_moles(spec, 1.0, 43.0, {"N2": n_i, "O2": 0.0, "H2O": 99.0, "NH3": 99.0,
                                           "CO2": 99.0})
    y = sum(vent[k] for k in sv.CONDENSABLE) / (sum(vent[k] for k in sv.CONDENSABLE) + n_i)
    assert y == pytest.approx((1.17 + 8.21 + 5.05) / 100.0, rel=1e-12)
    for k in sv.CONDENSABLE:
        assert vent[k] / sum(vent[q] for q in sv.CONDENSABLE) == pytest.approx(
            ROW_341[k] / (1.17 + 8.21 + 5.05), rel=1e-12)


def test_a_warmer_outlet_or_a_lower_pressure_carries_more_vapour():
    spec = c.C005_VENT_SPEC
    base = sv.vent_mass_kgh(sv.vent_moles(spec, 1.0, 43.0, _inlet()))
    assert sv.vent_mass_kgh(sv.vent_moles(spec, 1.0, 55.0, _inlet())) > base
    assert sv.vent_mass_kgh(sv.vent_moles(spec, 0.8, 43.0, _inlet())) > base
    assert sv.vent_mass_kgh(sv.vent_moles(spec, 1.0, 30.0, _inlet())) < base


def test_the_vent_never_releases_more_than_arrives_and_keeps_no_inert():
    """At a pressure near the outlet's vapour pressure the saturated gas could hold without
    bound; the vent is then the whole inlet, and with no inert gas nothing condensable leaves."""
    spec = c.C005_VENT_SPEC
    n = _inlet()
    vent = sv.vent_moles(spec, 0.01, 99.0, n)
    assert all(vent[k] == n[k] for k in sv.CONDENSABLE + sv.INERT)
    assert vent["Urea"] == 0.0
    dry = sv.vent_moles(spec, 1.0, 43.0, _inlet(inert=0.0))
    assert all(dry[k] == 0.0 for k in sv.CONDENSABLE + sv.INERT)
