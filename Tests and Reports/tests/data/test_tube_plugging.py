"""The plugged tubes of the last turnaround (decision 155): each bundle's record against its sheet.

Pinned: the three bundles' counts, tubes and surfaces as their Uhde design data sheets print them,
each surface reproduced by N . pi . d_o . L; the share of tubes in service, the active surface and
the plugged bores' volume; the coefficient the conductance re-anchored on the tubes in service
carries (handoff B-113 (b)); and the synthesis loop's vessels less the two HP exchangers' plugged
bores.
"""

from __future__ import annotations

import math

import pytest

from ureasim.data import unit_322_loop as loop
from ureasim.data.tube_plugging import PluggedBundle
from ureasim.data.unit_322e002 import TUBES as E002
from ureasim.data.unit_322e003 import TUBES as E003
from ureasim.data.unit_323 import E010_TUBES as E010


@pytest.mark.parametrize("bundle, n, plugged, surface, f, active, v_plugged", [
    (E002, 2929, 60, 2579.00, 0.979515, 2526.17, 0.21127),
    (E003, 525, 16, 89.50, 0.969524, 86.772, 0.010908),
    (E010, 1087, 15, 316.00, 0.986201, 311.64, 0.020716),
])
def test_each_bundle_is_its_sheet_and_its_plugs(bundle, n, plugged, surface, f, active,
                                                 v_plugged):
    assert (bundle.n_total, bundle.n_plugged, bundle.surface_m2) == (n, plugged, surface)
    computed = bundle.n_total * math.pi * bundle.tube_od_m * bundle.tube_l_eff_m
    assert computed == pytest.approx(bundle.surface_m2, rel=1e-3)
    assert bundle.f_tubes == pytest.approx(f, abs=1e-6)
    assert bundle.area_active_m2 == pytest.approx(active, abs=0.01)
    assert bundle.v_plugged_m3 == pytest.approx(v_plugged, abs=1e-5)


@pytest.mark.parametrize("bundle", [E002, E003, E010])
def test_the_conductance_is_re_anchored_on_the_tubes_in_service(bundle):
    """B-113 (b), decided 2026-10-28: the tubes still open carry 1 / f_tubes of the clean bundle's
    coefficient, so the conductance on the active surface is the design's."""
    u_des = 1.0 / bundle.surface_m2
    assert bundle.u_service_ratio == 1.0 / bundle.f_tubes
    assert u_des * bundle.u_service_ratio * bundle.area_active_m2 == pytest.approx(1.0, rel=1e-12)


def test_a_bundle_with_nothing_plugged_is_whole():
    clean = PluggedBundle(n_total=100, n_plugged=0, tube_od_m=0.025, tube_wall_m=0.0025,
                          tube_l_eff_m=2.0, surface_m2=15.7)
    assert (clean.f_tubes, clean.area_active_m2, clean.v_plugged_m3) == (1.0, 15.7, 0.0)
    assert clean.u_service_ratio == 1.0


def test_the_loop_loses_the_plugged_bores():
    """322E002's 21.6 m3 and 322E003's 10.0 less their plugged bores; with 322E001's replacement
    (28.83 m3, decision 154) the loop's vessels hold 245.61 m3."""
    assert loop.V_E002_M3 == pytest.approx(21.6 - 0.21127, abs=1e-5)
    assert loop.V_E003_M3 == pytest.approx(10.0 - 0.010908, abs=1e-6)
    assert loop.SYN_LOOP_V_M3 == pytest.approx(245.6078, abs=1e-4)
