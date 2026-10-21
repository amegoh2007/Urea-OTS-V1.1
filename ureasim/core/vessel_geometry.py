"""A vertical vessel's liquid volume against its height: a cylinder between two torispherical heads.

What this models
----------------
The liquid a vertical drum holds when its surface stands at a height, and the height a holdup puts
it at, through the bottom head, the cylinder and the top head — so that a level transmitter whose
taps straddle a head reads what the vessel holds, not a holdup scaled onto a span (decision 33's
class: a vessel's volume with its heads, a level read between its transmitter's taps).

Heights are measured from the bottom tangent line, negative into the bottom head. Each head is a
torisphere — a crown sphere of radius R tangent to a knuckle torus of radius r — on the vessel's
inside diameter D, the standard dished head of DIN 28011 / 28013. Its profile, at a depth d below
its tangent line:

    c   = D/2 - r,   z_c = sqrt((R - r)^2 - c^2),   h = R - z_c,   d_j = r z_c / (R - r)
    x(d) = c + sqrt(r^2 - d^2)                d <= d_j      (the knuckle)
    x(d) = sqrt(R^2 - (z_c + d)^2)            d_j < d <= h  (the crown)

and the liquid below a depth d, pi times the integral of x^2 from d to h, in closed form:

    V_crown(a, h)    = pi [ R^2 (h - a) - ((z_c + h)^3 - (z_c + a)^3) / 3 ]
    V_knuckle(d, d_j) = pi [ (c^2 + r^2)(d_j - d) - (d_j^3 - d^3) / 3
                             + c (t sqrt(r^2 - t^2) + r^2 asin(t / r)) |_d^d_j ]

Source: DIN 28013's proportions as `data.unit_322c001.torispherical_head_volume_m3` takes them; the
vessel's own drawing gives D, the heads and the tangent-to-tangent length.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

__all__ = ["VerticalVessel"]

#: Bisection steps for a height in a head [-]: 2^-60 of the head's depth, far below a millimetre.
HEAD_BISECTION_STEPS = 60


@dataclass(frozen=True)
class VerticalVessel:
    """A vertical cylinder of inside diameter ``d_in_m`` and tangent-to-tangent length ``tt_m``
    between two torispherical heads of inside crown radius ``crown_m`` and knuckle ``knuckle_m``."""

    d_in_m: float
    tt_m: float
    crown_m: float
    knuckle_m: float

    # ----- the head's profile ---------------------------------------------------------------
    @property
    def _c(self) -> float:
        return 0.5 * self.d_in_m - self.knuckle_m

    @property
    def _z_c(self) -> float:
        return math.sqrt((self.crown_m - self.knuckle_m) ** 2 - self._c ** 2)

    @property
    def head_depth_m(self) -> float:
        """The head's dished depth below its tangent line [m]."""
        return self.crown_m - self._z_c

    @property
    def _d_j(self) -> float:
        return self.knuckle_m * self._z_c / (self.crown_m - self.knuckle_m)

    @property
    def area_m2(self) -> float:
        """The cylinder's cross-section [m2]."""
        return math.pi * 0.25 * self.d_in_m ** 2

    def _head_below_depth_m3(self, d: float) -> float:
        """The head's liquid between its lowest point and a depth ``d`` below its tangent line."""
        r, big_r, c, z_c, h, d_j = (self.knuckle_m, self.crown_m, self._c, self._z_c,
                                    self.head_depth_m, self._d_j)
        d = min(max(d, 0.0), h)
        a = max(d, d_j)
        v = big_r ** 2 * (h - a) - ((z_c + h) ** 3 - (z_c + a) ** 3) / 3.0
        if d < d_j:
            def prim(t: float) -> float:
                return t * math.sqrt(max(r * r - t * t, 0.0)) + r * r * math.asin(min(t / r, 1.0))
            v += ((c * c + r * r) * (d_j - d) - (d_j ** 3 - d ** 3) / 3.0
                  + c * (prim(d_j) - prim(d)))
        return math.pi * v

    @property
    def head_volume_m3(self) -> float:
        """One head's volume below its tangent line [m3]."""
        return self._head_below_depth_m3(0.0)

    @property
    def volume_m3(self) -> float:
        """The vessel's volume, both heads included [m3]."""
        return 2.0 * self.head_volume_m3 + self.area_m2 * self.tt_m

    # ----- the liquid against its height ---------------------------------------------------
    def volume_below_m3(self, z_m: float) -> float:
        """The liquid the vessel holds with its surface at ``z_m`` above the bottom tangent [m3].

        Process utility
        ---------------
        What a level transmitter's reading stands for in mass: through the bottom head the litres
        per millimetre grow from nothing, in the cylinder they are constant, and in the top head
        they fall away again.
        """
        h = self.head_depth_m
        if z_m <= -h:
            return 0.0
        if z_m <= 0.0:
            return self._head_below_depth_m3(-z_m)
        v_head = self.head_volume_m3
        if z_m <= self.tt_m:
            return v_head + self.area_m2 * z_m
        top = min(z_m - self.tt_m, h)
        return v_head + self.area_m2 * self.tt_m + (v_head - self._head_below_depth_m3(top))

    def height_m(self, v_m3: float) -> float:
        """The surface's height above the bottom tangent [m] for a liquid volume [m3]: the inverse
        of `volume_below_m3`, clamped to the vessel."""
        h = self.head_depth_m
        v_head = self.head_volume_m3
        if v_m3 <= 0.0:
            return -h
        if v_head <= v_m3 <= v_head + self.area_m2 * self.tt_m:
            return (v_m3 - v_head) / self.area_m2
        if v_m3 >= self.volume_m3:
            return self.tt_m + h
        lo, hi = (-h, 0.0) if v_m3 < v_head else (self.tt_m, self.tt_m + h)
        for _ in range(HEAD_BISECTION_STEPS):
            mid = 0.5 * (lo + hi)
            if self.volume_below_m3(mid) < v_m3:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    def head_surface_m(self, x_m: float) -> float:
        """How far the head's inside surface stands from its tangent line at ``x_m`` off the
        axis [m] — where a nozzle on the head taps it."""
        r, big_r, c, z_c, d_j = (self.knuckle_m, self.crown_m, self._c, self._z_c, self._d_j)
        x_j = c + math.sqrt(max(r * r - d_j * d_j, 0.0))
        if x_m >= x_j:
            return math.sqrt(max(r * r - (x_m - c) ** 2, 0.0))
        return math.sqrt(big_r * big_r - x_m * x_m) - z_c
