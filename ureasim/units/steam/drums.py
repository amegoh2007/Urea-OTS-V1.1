"""Unit 329's drums — each condensate inventory over its whole vessel, its level between its taps.

What this models
----------------
The water in 329D005 and 329D009 (horizontal) and 322D001A/B (two vertical drums on one level
loop), as a mass over the whole vessel with its 2:1 ellipsoidal heads, and the level its
transmitter reads between its taps (decision 33's class, §5 rule 7). V1 integrates each level as
a percentage on a constant mass per per cent and clamps it at 0 and 100 %, so a drum's water
appears or vanishes at the ends of the span; here the water below the lower tap and above the
upper one is still water, and the level reading alone stops at the ends.

Equations (h the liquid's height above the vessel's bottom, R the bore's radius)
------------------------------------------------------------------------------
  horizontal, L between tangent lines:
      V(h) = L [R^2 acos((R - h) / R) - (R - h) sqrt(h (2R - h))] + pi h^2 (3R - h) / 6
      (the cylinder's segment, and the two heads: a half spheroid of depth R / 2 each)
  vertical, n drums, a = D / 4 the heads' depth, L the cylinder:
      V(h) = n pi R^2 h^2 (3a - h) / (3 a^2)                       h <= a
           = n [2 pi R^2 a / 3 + pi R^2 (h - a)]                   a <= h <= a + L
           = n V_full - V_vertical(a + L + a - h)                   above
  the level, per cent of the taps' span:  100 (h - h_lo) / (h_hi - h_lo), held in [0, 100]

The height is the volume's inverse, by bisection to the last bit.

Source
------
322D001's geometry V1 read from the vendor drawings (`ureasim.data.unit_329_network`); 329D005's
and 329D009's taps from their as-built GAs (UD-AU-329-DZ-0001-005, -0003-005, read in session 37).
As-Built Part LIV.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ureasim.data.unit_329_network import (
    D001_CYL_M,
    D001_ID_M,
    D001_TAPS_M,
    D005_ID_M,
    D005_LEN_M,
    D005_TAP_HALF_M,
    D009_ID_M,
    D009_LEN_M,
    D009_TAP_HALF_M,
    N_D001,
    RHO_D001_L,
    RHO_D005_L,
    RHO_D009_L,
)

#: The height bisection's iteration cap: it runs until the bracket stops shrinking in floating
#: point, so a design inventory reads its design level to the last bits.
HEIGHT_ITERS = 200


@dataclass(frozen=True)
class Drum:
    """A drum's water: its geometry, its density and its level transmitter's taps.

    ``kind`` is "horizontal" (one drum, ``length_m`` between tangent lines) or "vertical"
    (``count`` drums, ``length_m`` of cylinder); ``taps_m`` the taps' heights above the vessel's
    bottom [m].
    """

    tag: str
    kind: str
    id_m: float
    length_m: float
    rho_kgm3: float
    taps_m: tuple
    count: int = 1

    @property
    def height_m(self) -> float:
        """The vessel's inside height [m]."""
        if self.kind == "horizontal":
            return self.id_m
        return self.length_m + self.id_m / 2.0

    def volume_m3(self, h_m: float) -> float:
        """The water's volume at a height above the vessel's bottom [m3] (module docstring)."""
        r = self.id_m / 2.0
        h = min(max(h_m, 0.0), self.height_m)
        if self.kind == "horizontal":
            seg = r * r * math.acos((r - h) / r) - (r - h) * math.sqrt(max(h * (2.0 * r - h), 0.0))
            return self.length_m * seg + math.pi * h * h * (3.0 * r - h) / 6.0
        return self.count * _vertical_one(r, self.length_m, h)

    @property
    def full_m3(self) -> float:
        """The vessel's volume [m3]."""
        return self.volume_m3(self.height_m)

    def height_at_m(self, v_m3: float) -> float:
        """The height a volume of water stands at [m], the volume's inverse by bisection."""
        if v_m3 <= 0.0:
            return 0.0
        if v_m3 >= self.full_m3:
            return self.height_m
        lo, hi = 0.0, self.height_m
        for _ in range(HEIGHT_ITERS):
            mid = 0.5 * (lo + hi)
            if mid <= lo or mid >= hi:
                break
            if self.volume_m3(mid) < v_m3:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    def level_pct(self, m_kg: float) -> float:
        """What the level transmitter reads for a water inventory [%].

        Process utility
        ---------------
        LIC-329502/503/504's measurement: the water between the taps, held at 0 and 100 %
        outside them while the inventory itself goes on.
        """
        h = self.height_at_m(m_kg / self.rho_kgm3)
        lo, hi = self.taps_m
        return max(0.0, min(100.0, 100.0 * (h - lo) / (hi - lo)))

    def mass_at_level_kg(self, level_pct: float) -> float:
        """The water inventory a level reading inside the span stands for [kg]."""
        lo, hi = self.taps_m
        return self.rho_kgm3 * self.volume_m3(lo + level_pct / 100.0 * (hi - lo))

    @property
    def full_kg(self) -> float:
        """The vessel full of water [kg]."""
        return self.rho_kgm3 * self.full_m3


def _vertical_one(r: float, cyl_m: float, h: float) -> float:
    """One vertical drum's water at a height above its bottom [m3]: heads of depth D / 4."""
    a = r / 2.0
    head = 2.0 * math.pi * r * r * a / 3.0
    if h <= a:
        return math.pi * r * r * h * h * (3.0 * a - h) / (3.0 * a * a)
    if h <= a + cyl_m:
        return head + math.pi * r * r * (h - a)
    return 2.0 * head + math.pi * r * r * cyl_m - _vertical_one(r, cyl_m, 2.0 * a + cyl_m - h)


#: 329D005: LT-329502's taps 750 mm either side of the axis.
D005 = Drum("329D005", "horizontal", D005_ID_M, D005_LEN_M, RHO_D005_L,
            (D005_ID_M / 2.0 - D005_TAP_HALF_M, D005_ID_M / 2.0 + D005_TAP_HALF_M))

#: 329D009: LT-329503's taps 375 mm either side of the axis.
D009 = Drum("329D009", "horizontal", D009_ID_M, D009_LEN_M, RHO_D009_L,
            (D009_ID_M / 2.0 - D009_TAP_HALF_M, D009_ID_M / 2.0 + D009_TAP_HALF_M))

#: 322D001A/B: LICA-329504's taps N8B / N8A 300 and 1800 mm above the bottom tangent line.
D001 = Drum("322D001", "vertical", D001_ID_M, D001_CYL_M, RHO_D001_L,
            (D001_ID_M / 4.0 + D001_TAPS_M[0], D001_ID_M / 4.0 + D001_TAPS_M[1]), count=N_D001)


__all__ = ["HEIGHT_ITERS", "Drum", "D005", "D009", "D001"]
