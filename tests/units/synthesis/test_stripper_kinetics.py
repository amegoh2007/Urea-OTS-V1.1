"""322E001's side reactions: urea hydrolysis and biuret in the falling film.

What the module does, without a V1 tree: both extents land on the PFD's at the design state, move
with temperature, throughput and holdup in the directions the plant shows, and never consume more
than the reagents present. The rate group against V1's is `tests/equivalence/test_stripper_equivalence`.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_322e001 as d
from ureasim.units.synthesis.stripper_kinetics import (
    HYDROLYSIS_GROUP_DES,
    biuret_extent,
    hydrolysis_extent,
    hydrolysis_rate_group,
)

FEED = d.FEED_DES_KMOLH
T_DES_K = d.T_BOTTOM_DES_C + 273.15


def _hydrolysis(t_c=d.T_BOTTOM_DES_C, urea=FEED["Urea"], h2o=FEED["H2O"],
                vdot=d.VDOT_DES_M3H, v_liq=d.V_LIQ_DES_M3):
    return hydrolysis_extent(t_c, urea, h2o, vdot, v_liq)


def test_the_design_state_gives_the_pfd_extents():
    """The rate laws are departures on the PFD's extents: exactly those at the design state."""
    assert hydrolysis_rate_group(d.HYDROLYSIS_T_DES_C, FEED["Urea"], FEED["H2O"],
                                 d.VDOT_DES_M3H, d.V_LIQ_DES_M3) == HYDROLYSIS_GROUP_DES
    assert _hydrolysis() == pytest.approx(d.XI_HYDROLYSIS_DES, rel=1e-12)
    xi_hyd = _hydrolysis()
    assert biuret_extent(T_DES_K, FEED["Urea"], d.VDOT_DES_M3H, d.V_LIQ_DES_M3,
                         FEED["Urea"] - xi_hyd) == pytest.approx(d.XI_BIURET_DES, rel=1e-12)


def test_hotter_slower_and_fuller_all_hydrolyse_more():
    """Arrhenius in the bottoms, and a longer residence: a hotter film, a turndown and a fuller
    sump each raise the extent."""
    base = _hydrolysis()
    assert _hydrolysis(t_c=d.T_BOTTOM_DES_C + 5.0) > base
    assert _hydrolysis(vdot=0.5 * d.VDOT_DES_M3H) > base
    assert _hydrolysis(v_liq=d.V_TUBES_M3 + d.V_SUMP_M3) > base


def test_the_extents_never_exceed_their_reagents():
    """An extent capped by the urea and water present, biuret by half the urea left; an empty tube
    reacts nothing."""
    assert _hydrolysis(urea=1.0, vdot=1.0) == 1.0
    assert _hydrolysis(vdot=0.0) == 0.0
    assert biuret_extent(T_DES_K, FEED["Urea"], 1.0, d.V_LIQ_DES_M3, 2.0) == 1.0
