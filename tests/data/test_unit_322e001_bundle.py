"""322E001's two tube bundles (decision 154): the replacement the plant runs and V1's.

Pinned: each bundle's geometry as its drawings print it, its surface reproduced by N . pi . d_o .
L; the replacement's flooding limit per tube scaled from V1's on Wallis's D^2.5; its shell's
capacity the two process datasheets' U.A ratio, the coefficient per square metre agreeing to 1 %;
and V1's bundle returning V1's own derived volumes to the bit.
"""

from __future__ import annotations

import math

import pytest

from ureasim.data.unit_322e001_bundle import (
    BUNDLE,
    BUNDLE_2950,
    BUNDLE_V1,
    UA_2950_KW_K,
    UA_V1_KW_K,
)


def test_the_plant_runs_the_replacement():
    assert BUNDLE is BUNDLE_2950


@pytest.mark.parametrize("bundle, n, od, wall, bore, surface, tube_side", [
    (BUNDLE_V1, 2600, 0.031, 0.003, 0.025, 1519.00, 24.7),
    (BUNDLE_2950, 2950, 0.031, 0.0025, 0.026, 1724.0, 28.83),
])
def test_each_bundle_is_its_drawings(bundle, n, od, wall, bore, surface, tube_side):
    assert (bundle.n_tubes, bundle.tube_od_m, bundle.tube_wall_m) == (n, od, wall)
    assert bundle.tube_id_m == pytest.approx(bore, abs=1e-12)
    assert bundle.tube_l_eff_m == 6.000 and bundle.level_span_m == 1.5
    assert (bundle.surface_m2, bundle.tube_side_m3) == (surface, tube_side)
    computed = bundle.n_tubes * math.pi * bundle.tube_od_m * bundle.tube_l_eff_m
    assert computed == pytest.approx(bundle.surface_m2, rel=2.0e-4)


def test_v1s_bundle_is_v1s_bytes():
    """V1 `main.py` STRIP_V_TUBES_M3 and STRIP_V_SUMP_M3, written as V1 writes them."""
    assert BUNDLE_V1.v_tubes_m3 == 2600 * math.pi * 0.25 * (0.031 - 2.0 * 0.003) ** 2 * 6.000
    assert BUNDLE_V1.v_sump_m3 == 4.638 * 1.5
    assert (BUNDLE_V1.flood_kgh_per_tube, BUNDLE_V1.shell_capacity) == (145.0, 1.0)


def test_the_replacement_floods_on_wallis_and_holds_more():
    """159.9 kg/h per tube, 145 x (26/25)^2.5; 9.397 m3 of tubes and a 2,425 mm channel."""
    assert BUNDLE_2950.flood_kgh_per_tube == pytest.approx(159.938, abs=1e-3)
    assert BUNDLE_2950.v_tubes_m3 == pytest.approx(9.3974, abs=1e-4)
    assert BUNDLE_2950.sump_area_m2 == pytest.approx(4.6186, abs=1e-4)


def test_the_replacements_shell_on_the_two_datasheets():
    """1 160.5 kW/K for V1's bundle (39 400 kW, 214 C steam, 187 -> 172 C), 1 325.7 for the
    replacement (41 738 kW, 212 C, 187 -> 173 C): 1.142 times; per square metre 0.764 and 0.769."""
    assert UA_V1_KW_K == pytest.approx(1160.55, abs=0.01)
    assert UA_2950_KW_K == pytest.approx(1325.74, abs=0.01)
    assert BUNDLE_2950.shell_capacity == pytest.approx(1.14234, abs=1e-5)
    per_m2 = (UA_V1_KW_K / BUNDLE_V1.surface_m2, UA_2950_KW_K / BUNDLE_2950.surface_m2)
    assert per_m2[1] / per_m2[0] == pytest.approx(1.0065, abs=1e-4)
