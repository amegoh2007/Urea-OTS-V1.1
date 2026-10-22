"""The vendor sizing-sheet record and the design-stroke anchor every catalogued control valve shares.

What this is
------------
A control-valve vendor sizes each valve on its own operating cases and prints, per case, the
pressures, temperature, flow, density, the capacity the case requires and the stroke the trim
takes it at. ``SizingCase`` holds one printed case and ``VendorValve`` one valve as sized: its
rated capacity, its trim's characteristic, its service and its cases. The vendors' catalogues are
built on these records: Flowserve's and CCI's in `control_valves`, Metso's in
`control_valves_metso`, Fisher's in `control_valves_fisher`.

The design stroke (handoff B-44, decided 2026-09-30; As-Built §XL.3) is the opening at which the
rated capacity passes the PFD design flow on the vendor's own normal sizing case:

    phi_des = C_normal . (Q_des / Q_normal) / C_rated        Q at the vendor's density
    h_des   = the inverse of the trim's characteristic at phi_des

A valve shut at design is anchored instead on its full-stroke capacity on the normal case,
Q_normal . C_rated / C_normal.

Moved out of `control_valves` unchanged (2026-10-23, the housekeeping split), so that one vendor's
catalogue imports the records without importing another's; `control_valves` re-exports every name.

Source
------
The fields are the vendors' sheets' own, as each catalogue cites them; the characteristics are
`ureasim.control.valve`'s.
"""

from __future__ import annotations

from dataclasses import dataclass

from ureasim.control.valve import stroke_for_cv_fraction

#: Molar volume of an ideal gas at 0 C and 1.01325 bar [m3/kmol], the "normal cubic metre" the
#: CCI sheet quotes its CO2 flow in.
NORMAL_MOLAR_VOLUME_M3_KMOL = 22.414


@dataclass(frozen=True)
class SizingCase:
    """One of the vendor's sizing cases, as printed."""

    p1_bara: float
    p2_bara: float
    t_c: float
    #: Liquid: m3/h at operating conditions. Gas: Nm3/h.
    flow: float
    #: Liquid: kg/m3 at operating conditions. Gas: kg/Nm3.
    rho: float
    #: The capacity the case requires, in the sheet's unit (Kv for Flowserve, Cv for CCI).
    capacity: float
    #: The stroke the vendor computed for it [%], or None where not printed.
    stroke_pct: float | None
    #: Liquid pressure-recovery factor, or gas pressure-differential ratio factor, at that
    #: stroke; None where not printed.
    fl: float | None = None
    xt: float | None = None


@dataclass(frozen=True)
class VendorValve:
    """A control valve as its vendor sized it."""

    tag: str
    #: The rated capacity, in the same unit as the cases' (Kvs, or rated Cv).
    rated: float
    #: `control.valve.cv_fraction`'s name for the trim, or the vendor's printed points.
    characteristic: str | tuple
    service: str
    cases: tuple
    #: Index of the normal case in ``cases``.
    normal: int
    source: str

    @property
    def normal_case(self) -> SizingCase:
        return self.cases[self.normal]


def design_stroke_pct(valve: VendorValve, m_des_kgh: float) -> float:
    """The stroke [%] at which ``valve`` passes the design mass flow on its normal case.

    Process utility
    ---------------
    Places the design point on the vendor trim's curve, which is where the anchored valve law
    and its controller's seed sit. Equation in the module docstring.
    """
    c = valve.normal_case
    phi = c.capacity * (m_des_kgh / (c.flow * c.rho)) / valve.rated
    return 100.0 * stroke_for_cv_fraction(phi, valve.characteristic)


def full_stroke_m3h(valve: VendorValve) -> float:
    """What ``valve`` passes wide open on its normal case's pressure drop [m3/h, or Nm3/h].

    Process utility
    ---------------
    The capacity anchor of a valve that is shut at design, where no design stroke exists.
    """
    c = valve.normal_case
    return c.flow * valve.rated / c.capacity


__all__ = ["NORMAL_MOLAR_VOLUME_M3_KMOL", "SizingCase", "VendorValve", "design_stroke_pct",
           "full_stroke_m3h"]
