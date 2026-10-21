"""Behaviour of `ureasim.core.vessel_geometry`: a vertical vessel's liquid against its height.

Pinned on 323F004 (B-100, decided 2026-10-17): Da 1400 x 8, two DIN 28013 heads, 1800 mm between
tangents. Every number was measured on the module before it was written down.
"""

from __future__ import annotations

import math

import pytest

from ureasim.core.vessel_geometry import VerticalVessel
from ureasim.data.unit_322c001 import torispherical_head_volume_m3

F004 = VerticalVessel(d_in_m=1.384, tt_m=1.800, crown_m=0.8 * 1.400, knuckle_m=0.154 * 1.400)


def test_a_head_holds_what_the_closed_form_gives():
    """The head's volume below its tangent line is 322C001's closed form to 1e-14; its depth is
    DIN 28013's 0.255 Da - 0.635 s to 0.7 mm; the drum holds 3.402 m3, the hydro-test's 3450 kg of
    water less its nozzles' stubs."""
    assert F004.head_volume_m3 == pytest.approx(
        torispherical_head_volume_m3(1.384, 1.12, 0.2156), rel=1e-14)
    assert F004.head_volume_m3 == pytest.approx(0.34714, abs=1e-5)
    assert F004.head_depth_m == pytest.approx(0.255 * 1.400 - 0.635 * 0.008, abs=7e-4)
    assert F004.volume_m3 == pytest.approx(3.40220, abs=1e-5)
    assert F004.volume_m3 == pytest.approx(
        2.0 * F004.head_volume_m3 + math.pi * 0.25 * 1.384 ** 2 * 1.800, rel=1e-15)


@pytest.mark.parametrize("z", [-0.351, -0.30, -0.20, -0.0943, -0.05, 0.0, 0.874, 1.80, 1.90,
                               2.0334, 2.15])
def test_the_height_inverts_the_volume(z):
    """Through the bottom head, the cylinder and the top head the height a volume puts the surface
    at is the height it was taken at."""
    assert F004.height_m(F004.volume_below_m3(z)) == pytest.approx(z, abs=1e-9)


def test_the_volume_is_continuous_and_bounded():
    """Continuous at the knuckle's junction with the crown and at both tangent lines; nothing below
    the head's lowest point, the whole vessel above its top."""
    d_j = F004._d_j
    assert F004._head_below_depth_m3(d_j - 1e-9) == pytest.approx(
        F004._head_below_depth_m3(d_j + 1e-9), abs=1e-8)
    assert F004.volume_below_m3(-1e-12) == pytest.approx(F004.volume_below_m3(1e-12), abs=1e-10)
    assert F004.volume_below_m3(1.8 - 1e-12) == pytest.approx(F004.volume_below_m3(1.8 + 1e-12),
                                                              abs=1e-10)
    assert F004.volume_below_m3(-0.5) == 0.0
    assert F004.volume_below_m3(3.0) == pytest.approx(F004.volume_m3, rel=1e-14)
    assert F004.height_m(-1.0) == -F004.head_depth_m
    assert F004.height_m(10.0) == F004.tt_m + F004.head_depth_m


def test_a_head_nozzles_tap():
    """N7, 500 mm off the axis on the top head: its tap 233.4 mm above the tangent line, on the
    crown. On the axis the surface is the head's depth, at the shell nothing."""
    assert F004.head_surface_m(0.500) == pytest.approx(0.23344, abs=1e-5)
    assert F004.head_surface_m(0.0) == pytest.approx(F004.head_depth_m, abs=1e-12)
    assert F004.head_surface_m(0.692) == pytest.approx(0.0, abs=1e-12)
