"""Tube plugging — the share of an exchanger's bundle still in service after a turnaround.

What this covers
----------------
A shell-and-tube exchanger whose leaking tubes were plugged at both tubesheets: the plugged tubes
carry no process fluid and transfer no heat, so the bundle's active surface falls with the share of
tubes still open, and the plugged tubes' bores leave the process side's volume:

    f_tubes = (N_total - N_plugged) / N_total
    A_active = A_datasheet . f_tubes
    V_plugged = N_plugged . pi / 4 . d_i^2 . L_eff

The conductance is re-anchored on the tubes in service (decided 2026-10-28, handoff B-113 (b)).
Each of these exchangers' conductances is back-solved on the PFD's design point, and the plant
runs that design point with these tubes plugged, so the anchor holds on the bundle in service: the
tubes still open carry a coefficient 1 / f_tubes above the clean bundle's, and the conductance on
the active surface is the design's to the bit,

    U_service = UA_des / A_active = U_des / f_tubes,    U_service . A_active = UA_des

The clean surface's share the PFD does not need is the plugging's margin. One record per exchanger
lives with that exchanger's design data (`unit_322e002`, `unit_322e003`, `unit_323`).

Source: the plant's record of the last turnaround, given by the process engineer 2026-10-28
(session 72, `project.md` decision 155): 60 tubes plugged in 322E002, 16 in 322E003, 15 in
323E010. Each bundle's tubes, length and surface from its Uhde design data sheet. Session 72 first
carried the conductance at the clean coefficient, UA . f_tubes, and the plant left the PFD's seed
(322E002's product 171.2 C, 322E003 condensing 0.972 of its demand, 323E010's chest 2.528 bar a);
the re-anchoring replaced it (`project.md` decision 157).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

__all__ = ["PluggedBundle"]


@dataclass(frozen=True)
class PluggedBundle:
    """An exchanger's tube bundle and the tubes plugged in it."""

    #: Tubes in the bundle as built [-].
    n_total: int
    #: Tubes plugged at both tubesheets [-].
    n_plugged: int
    #: Tube outside diameter [m].
    tube_od_m: float
    #: Tube wall thickness [m].
    tube_wall_m: float
    #: Effective tube length [m].
    tube_l_eff_m: float
    #: Exchange surface as built, the datasheet's [m2].
    surface_m2: float

    @property
    def f_tubes(self) -> float:
        """The share of the tubes still in service [-]: what the active surface is scaled by."""
        return (self.n_total - self.n_plugged) / self.n_total

    @property
    def u_service_ratio(self) -> float:
        """The coefficient the tubes in service carry over the clean bundle's [-], 1 / f_tubes: what
        holds the design conductance on the active surface (handoff B-113 (b))."""
        return 1.0 / self.f_tubes

    @property
    def area_active_m2(self) -> float:
        """The exchange surface still in service [m2]."""
        return self.surface_m2 * self.f_tubes

    @property
    def v_plugged_m3(self) -> float:
        """The plugged tubes' bores over their effective length [m3]: process volume lost."""
        tube_id_m = self.tube_od_m - 2.0 * self.tube_wall_m
        return self.n_plugged * math.pi * 0.25 * tube_id_m ** 2 * self.tube_l_eff_m
