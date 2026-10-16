"""Behaviour of the back-pressure over ammonia water — `ureasim.thermo.ammonia_backpressure`.

Equivalence with V1 is proven in `tests/equivalence/test_packed_beds_equivalence.py`. This file
pins what 322C001's beds stand on: the design sump's back-pressure, how it moves with loading and
temperature, the heats of absorption the docstring quotes, and the continuity of the van 't Hoff
extension at the speciation's edge.
"""

from __future__ import annotations

import itertools
import math

import pytest

from ureasim.data import unit_322c001 as c
from ureasim.thermo import ammonia_backpressure as bp


def test_the_design_sump_and_its_wash():
    """PFD 756 at 43 C holds back 4815 Pa of NH3 and 829 of CO2; PFD 755 at 40 C, 4102 and 656 —
    against the 32 kPa of NH3 the design purge carries at 3.9 bar a, so the lower bed has a
    driving force."""
    p_n, p_c, _, _ = bp.back_pressure(c.W_C001_DES, 43.0)
    assert (p_n, p_c) == (pytest.approx(4815.1, abs=0.1), pytest.approx(828.7, abs=0.1))
    p_n, p_c, _, _ = bp.back_pressure(c.W_S755, 40.0)
    assert (p_n, p_c) == (pytest.approx(4101.6, abs=0.1), pytest.approx(656.4, abs=0.1))


def test_a_warmer_or_richer_liquor_holds_back_more():
    """The design sump 17 K warmer: NH3 twice, CO2 4.7 times. Clean condensate reads the grid's
    floor, 37.5 Pa of NH3."""
    lo, hi = bp.back_pressure(c.W_C001_DES, 43.0), bp.back_pressure(c.W_C001_DES, 60.0)
    assert hi[0] / lo[0] == pytest.approx(2.008, abs=1e-3)
    assert hi[1] / lo[1] == pytest.approx(4.703, abs=1e-3)
    rich = dict(c.W_C001_DES, NH3=0.08, H2O=c.W_C001_DES["H2O"] - 0.038)
    assert bp.back_pressure(rich, 43.0)[0] > lo[0]
    assert bp.molalities({"H2O": 1.0}) == (bp.N_FLOOR, bp.C_FLOOR)
    assert bp.back_pressure({"H2O": 1.0}, 46.0)[0] == pytest.approx(37.54, abs=0.01)


def test_the_heats_of_absorption_carry_the_carbamate():
    """Over the design sump at 43 C: NH3 36.1 kJ/mol, CO2 79.8 — the carbamate's heat, not CO2's
    16 kJ/mol of physical solution."""
    dh_n, dh_c = bp.heat_of_absorption_j_mol(c.W_C001_DES, 43.0)
    assert (dh_n, dh_c) == (pytest.approx(36058.0, abs=1.0), pytest.approx(79836.0, abs=1.0))


def test_van_t_hoff_carries_on_continuously_past_100_c():
    """At the speciation's 100 C edge the extension meets the grid to 1e-6 of each pressure."""
    below = bp.back_pressure(c.W_C001_DES, 99.99999)
    edge = bp.back_pressure(c.W_C001_DES, 100.0)
    above = bp.back_pressure(c.W_C001_DES, 100.00001)
    for b, e, a in zip(below, edge, above):
        assert b < e < a and (a - b) / e < 2e-6


# ----- the liquid-state store (handoff A-18) -------------------------------------------------

def test_the_liquor_heats_are_v1s_heats_to_the_bit():
    """Read off the liquid-state grid, the heats of absorption equal V1's grid's, inside the
    speciation's range and at its edge, dilute and carbamate-strong."""
    for w in (c.W_C001_DES, {"NH3": 0.30, "CO2": 0.25, "H2O": 0.45},
              {"NH3": 0.62, "CO2": 0.30, "H2O": 0.08}):
        for t in (20.0, 43.0, 75.5, 99.9, 104.0, 140.0):
            assert bp.liquor_heat_of_absorption_j_mol(w, t) == bp.heat_of_absorption_j_mol(w, t)


def test_the_store_covers_every_node_the_letdown_reads():
    """The block reaches the letdown's most concentrated liquor at both ends of the speciation's
    range: 65 x 77 x 92 = 460 460 nodes."""
    from ureasim.thermo.condensing_letdown import MOLAL_MAX
    assert bp.STATE_STORE_MOLAL_MAX == MOLAL_MAX
    for m_n, m_c in ((MOLAL_MAX, MOLAL_MAX), (bp.N_FLOOR, bp.C_FLOOR)):
        fi = math.log(m_n / bp.N_FLOOR) / math.log(bp.GRID_RATIO)
        fj = math.log(m_c / bp.C_FLOOR) / math.log(bp.GRID_RATIO)
        assert bp.STATE_STORE_I[0] <= math.floor(fi) and math.floor(fi) + 1 <= bp.STATE_STORE_I[1]
        assert bp.STATE_STORE_J[0] <= math.floor(fj) and math.floor(fj) + 1 <= bp.STATE_STORE_J[1]
    for t_k in (bp.T_SPEC_LO_K, bp.T_SPEC_HI_K):
        k = math.floor(t_k / bp.GRID_DT)
        assert bp.STATE_STORE_K[0] <= k and k + 1 <= bp.STATE_STORE_K[1]
    n = [hi - lo + 1 for lo, hi in (bp.STATE_STORE_I, bp.STATE_STORE_J, bp.STATE_STORE_K)]
    assert n == [65, 77, 92]


def test_a_stored_node_is_the_lazy_node_to_the_bit(tmp_path):
    """A block built by the store's builder, written and read back, serves the doubles the lazy
    path tabulates; a store under another key is stale and not read."""
    from ureasim.thermo import node_store
    block = ((40, 41), (30, 31), (330, 331))
    built = node_store.build_store(bp.state_node_values, *block, 3, workers=1)
    path = str(tmp_path / "block.bin")
    node_store.write_store(path, built, bp.state_store_key())
    store = node_store.read_store(path, bp.state_store_key())
    for i, j, k in itertools.product(*(range(lo, hi + 1) for lo, hi in block)):
        assert store.get(i, j, k) == bp.state_node_values(i, j, k)
    assert node_store.read_store(path, "another key") is None


def test_the_shipped_stores_are_current_and_bit_for_bit():
    """When the stores beside the module are present, their keys are the present model's and a
    sample of each one's nodes equals the lazy path's."""
    from ureasim.thermo import node_store
    stores = [(node_store.read_store(path, key()), fn) for path, key, fn in (
        (bp.STATE_STORE_PATH, bp.state_store_key, bp.state_node_values),
        (bp.BACK_STORE_PATH, bp.back_store_key, bp.back_pressure_node_values))]
    if any(store is None for store, _ in stores):
        pytest.skip("no current node stores (tools/build_liquid_state_store.py)")
    for store, fn in stores:
        for i, j, k in ((0, 0, 283), (64, 76, 374), (37, 41, 320), (55, 60, 352), (12, 70, 300)):
            assert store.get(i, j, k) == fn(i, j, k)
