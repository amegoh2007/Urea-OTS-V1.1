"""The vendor control valves — Flowserve's Valtek globe valves and CCI's Drag valve — as sized.

What this is
------------
The plant's control-valve vendors sized each valve on three operating cases (minimum, normal,
maximum) and chose a trim for it. Those sheets fix what V1 had to assume: the characteristic
of the trim, its rated capacity, and so where on its curve the valve works at design — which
is what sets a control loop's gain away from the design point. V1 ran every valve linear, at a
50 % design stroke, on the ground that no control-valve datasheet existed (handoff B-44).

DECIDED 2026-09-30 (handoff B-44, closed; As-Built §XL.3): every ported valve in these sheets
runs its vendor trim, and its design stroke is the opening at which its rated capacity passes
the PFD design flow on the vendor's own normal sizing case:

    phi_des = C_normal . (Q_des / Q_normal) / C_rated        Q at the vendor's density
    h_des   = the inverse of the trim's characteristic at phi_des

The anchored valve laws keep the design flow exact at h_des; what moves is the loop gain off
design. A valve shut at design is anchored instead on its full-stroke capacity on the normal
case, Q_normal . C_rated / C_normal.

Sources
-------
* Flowserve, "Control Valves", Uhde order STAN 0522419-0 (the vendor archive, scanned, read
  from the page images): the summary of items, UD-MR-G00-DZ-0048-001; the data sheets, -002;
  the calculation sheets, -003 — one page per position, PDF pages 46 to 64 for the positions
  below, giving Kvs, plug code (the sixth letter the characteristic: G modified equal
  percentage, L linear) and, per case, the pressures, temperature, flow, density, the
  calculated Kv, the stroke, and FL (liquid) or xT (gas).
* CCI, Control Valve Data Sheet PV 322203, item 17, UD-MR-G00-DZ-0009-004 sheet 6 (scanned):
  a Drag 28-stage angle valve, rated Cv/Kv 32/27, equal percentage, fail open; normal and
  maximum cases; no FL, xT or stroke printed.

Ported valves use these entries now; the rest are catalogued for their units' ports (§5
rule 7). Where a sheet prints a case's capacity only on its maximum case, the other cases'
capacities are calculated by IEC 60534-2-1 from what the case prints, and say so.
"""

from __future__ import annotations

from dataclasses import dataclass

from ureasim.control.valve import stroke_for_cv_fraction
from ureasim.thermo.iapws import rho_liquid_sat_kgm3

#: Molar volume of an ideal gas at 0 C and 1.01325 bar [m3/kmol], the "normal cubic metre" the
#: CCI sheet quotes its CO2 flow in.
NORMAL_MOLAR_VOLUME_M3_KMOL = 22.414

#: Molar mass of carbon dioxide [kg/kmol], CCI's fluid.
MW_CO2 = 44.0095


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


def _flowserve(pos: int) -> str:
    """The calculation sheet of Flowserve position ``pos``; it is page ``pos`` of the PDF."""
    return f"Flowserve UD-MR-G00-DZ-0048-003, Pos. {pos} (STAN 0522419-0), PDF page {pos}"


# ======================================================================================
# The Valtek modified equal-percentage valves (plug code ...GG)
# ======================================================================================

FV_323401 = VendorValve(
    "FV-323401", 4.0, "mod_equal_pct", "liquid", (
        SizingCase(7.5, 6.0, 56.0, 0.9, 992.4, 0.7321, 43.0, fl=0.9794),
        SizingCase(7.3, 4.2, 56.0, 1.5, 992.4, 0.8488, 48.0, fl=0.9770),
        SizingCase(7.1, 4.2, 56.0, 3.5, 992.4, 2.05, 78.0, fl=0.9732)),
    1, _flowserve(48))

FV_323402 = VendorValve(
    "FV-323402", 4.0, "mod_equal_pct", "liquid", (
        SizingCase(7.5, 1.3, 56.0, 0.36, 992.4, 0.144, 9.0, fl=0.9853),
        SizingCase(7.3, 1.3, 56.0, 1.5, 992.4, 0.6101, 37.0, fl=0.9790),
        SizingCase(7.1, 6.0, 56.0, 2.0, 992.4, 1.9, 75.0, fl=0.9705)),
    1, _flowserve(49))

FV_323418 = VendorValve(
    "FV-323418", 4.0, "mod_equal_pct", "liquid", (
        SizingCase(7.7, 5.0, 45.0, 0.6, 1065.0, 0.3769, 23.0, fl=0.9825),
        SizingCase(7.7, 5.0, 45.0, 3.3, 1065.0, 2.07, 78.0, fl=0.9722),
        SizingCase(7.5, 5.0, 45.0, 3.6, 1065.0, 2.35, 82.0, fl=0.9712)),
    1, _flowserve(50))

LV_323503 = VendorValve(
    "LV-323503", 25.0, "mod_equal_pct", "liquid", (
        SizingCase(5.1, 3.5, 45.0, 3.0, 1051.0, 2.43, 24.0, fl=0.9594),
        SizingCase(4.9, 3.6, 45.0, 8.0, 1051.0, 7.19, 58.0, fl=0.9457),
        SizingCase(4.7, 4.2, 45.0, 11.0, 1051.0, 15.95, 85.0, fl=0.9314)),
    1, _flowserve(52))

LV_323505 = VendorValve(
    "LV-323505", 355.0, "mod_equal_pct", "liquid", (
        SizingCase(1.9, 1.0, 106.0, 60.0, 1130.0, 67.24, 44.0, fl=0.9138),
        SizingCase(1.8, 1.3, 106.0, 95.0, 1130.0, 142.83, 70.0, fl=0.8926),
        SizingCase(1.8, 1.3, 106.0, 120.0, 1130.0, 180.42, 77.0, fl=0.8847)),
    1, _flowserve(53))

FV_324401 = VendorValve(
    "FV-324401", 160.0, "mod_equal_pct", "liquid", (
        SizingCase(3.9, 2.3, 99.0, 51.11, 1173.94, 43.78, 57.0, fl=0.9627),
        SizingCase(3.7, 2.2, 99.0, 88.7, 1173.94, 78.48, 76.0, fl=0.9571),
        SizingCase(3.5, 2.7, 99.0, 100.0, 1173.94, 121.15, 91.0, fl=0.9499)),
    1, _flowserve(54))

FV_328402 = VendorValve(
    "FV-328402", 63.0, "mod_equal_pct", "liquid", (
        SizingCase(10.1, 9.34, 56.0, 19.1, 986.0, 21.76, 65.0, fl=0.9261),
        SizingCase(9.93, 6.94, 56.0, 31.4, 986.0, 18.03, 58.0, fl=0.9396),
        SizingCase(9.67, 7.1, 56.0, 46.7, 994.0, 29.05, 74.0, fl=0.9309)),
    1, _flowserve(57))

FV_328404 = VendorValve(
    "FV-328404", 10.0, "mod_equal_pct", "liquid", (
        SizingCase(6.76, 4.0, 61.0, 0.9, 1077.0, 0.5623, 14.0, fl=0.9835),
        SizingCase(6.83, 6.48, 61.0, 1.6, 1077.0, 2.81, 58.0, fl=0.9752),
        SizingCase(6.52, 4.01, 61.0, 2.5, 1077.0, 1.64, 40.0, fl=0.9786)),
    1, _flowserve(58))

FV_328405 = VendorValve(
    "FV-328405", 1.6, "mod_equal_pct", "liquid", (
        SizingCase(7.98, 6.13, 63.0, 0.51, 986.0, 0.3724, 51.0, fl=0.9857),
        SizingCase(7.88, 3.86, 63.0, 1.01, 986.0, 0.5002, 61.0, fl=0.9845),
        SizingCase(7.67, 3.98, 63.0, 2.03, 986.0, 1.05, 86.0, fl=0.9808)),
    1, _flowserve(59))

FV_328406 = VendorValve(
    "FV-328406", 100.0, "mod_equal_pct", "liquid", (
        SizingCase(4.69, 2.29, 40.0, 10.08, 992.0, 6.48, 16.0, fl=0.9492),
        SizingCase(2.96, 2.36, 40.0, 36.57, 992.0, 47.03, 75.0, fl=0.9132),
        SizingCase(2.86, 2.4, 40.0, 45.84, 992.0, 67.32, 87.0, fl=0.9033)),
    1, _flowserve(60))

LV_328505 = VendorValve(
    "LV-328505", 63.0, "mod_equal_pct", "liquid", (
        SizingCase(5.12, 2.45, 89.0, 10.9, 962.0, 6.54, 25.0, fl=0.9530),
        SizingCase(3.54, 3.0, 89.0, 18.2, 962.0, 24.29, 68.0, fl=0.9471),
        SizingCase(3.45, 2.9, 89.0, 31.29, 962.0, 41.39, 86.0, fl=0.9290)),
    1, _flowserve(62))

PV_328202 = VendorValve(
    "PV-328202", 25.0, "mod_equal_pct", "gas", (
        SizingCase(6.0, 1.1, 61.0, 217.0, 0.34, 1.2, 12.0, xt=0.8581),
        SizingCase(2.6, 1.3, 61.0, 362.0, 0.78, 7.8, 61.0, xt=0.7743),
        SizingCase(3.0, 2.5, 61.0, 507.0, 0.78, 13.92, 80.0, xt=0.7339)),
    1, _flowserve(63))

PV_328203 = VendorValve(
    "PV-328203", 10.0, "mod_equal_pct", "gas", (
        SizingCase(22.0, 6.0, 188.0, 514.9, 0.944, 1.59, 39.0, xt=0.8496),
        SizingCase(14.5, 3.5, 188.0, 858.1, 0.944, 4.13, 70.0, xt=0.8047),
        SizingCase(14.49, 3.5, 188.0, 1027.2, 0.944, 4.79, 75.0, xt=0.7961)),
    1, _flowserve(64))

LV_322502 = VendorValve(
    "LV-322502", 100.0, "mod_equal_pct", "liquid", (
        SizingCase(3.7, 2.0, 43.0, 33.3, 998.0, 25.52, 54.0, fl=0.9325),
        SizingCase(2.8, 2.3, 43.0, 40.0, 998.0, 56.52, 81.0, fl=0.9147)),
    0, _flowserve(46))

PV_322201 = VendorValve(
    "PV-322201", 63.0, "mod_equal_pct", "gas", (
        SizingCase(3.9, 1.0, 45.0, 1000.0, 1.19, 16.25, 55.0, xt=0.7881),
        SizingCase(3.9, 1.0, 45.0, 1314.24, 1.19, 21.58, 64.0, xt=0.7707),
        SizingCase(3.9, 1.0, 45.0, 1500.0, 1.19, 24.77, 69.0, xt=0.7616)),
    1, _flowserve(47))

# Unit 324's vacuum: the false-air bleeds and the ejectors' motive steam. These four sheets print
# the "weight of flow" [kg/h] and the upstream specific volume, not a normal volume: each case
# carries the printed mass flow with a unit density, so flow x rho is the mass flow as for every
# other entry. PV-324202 and PV-324203 admit air at 0.9 bar a and 32 C, the case printed once;
# PV-324203's is choked ("***DB***"). HV-329605 and HV-329606 pass LP steam at 4.1 bar a and 146 C.

PV_324202 = VendorValve(
    "PV-324202", 4.0, "mod_equal_pct", "gas", (
        SizingCase(0.9, 0.3, 32.0, 46.0, 1.0, 2.73, 87.0, xt=0.8097),),
    0, _flowserve(55))

PV_324203 = VendorValve(
    "PV-324203", 1.6, "mod_equal_pct", "gas", (
        SizingCase(0.9, 0.14, 32.0, 23.0, 1.0, 1.38, 95.0, xt=0.8000),),
    0, _flowserve(56))

HV_329605 = VendorValve(
    "HV-329605", 40.0, "mod_equal_pct", "gas", (
        SizingCase(4.1, 3.8, 146.0, 233.0, 1.0, 9.45, 52.0, xt=0.8119),
        SizingCase(4.1, 3.8, 146.0, 390.0, 1.0, 15.83, 69.0, xt=0.7828),
        SizingCase(4.1, 3.8, 146.0, 429.0, 1.0, 17.42, 72.0, xt=0.7769)),
    1, _flowserve(66))

HV_329606 = VendorValve(
    "HV-329606", 125.0, "mod_equal_pct", "gas", (
        SizingCase(4.1, 4.0, 146.0, 800.0, 1.0, 55.05, 73.0, xt=0.7230),
        SizingCase(4.1, 3.9, 146.0, 1427.0, 1.0, 70.33, 81.0, xt=0.7028),
        SizingCase(4.1, 3.8, 146.0, 1600.0, 1.0, 65.17, 78.0, xt=0.7092)),
    1, _flowserve(67))

# Unit 329's steam network (session 37). The two drum-to-drum letdowns and 322D001's make-up pass
# condensate; PV-329205A admits superheated 25 bar a steam to 329D009 and PV-329205B lets 329D009's
# steam down to the LP header, both sheets printing the "weight of flow" [kg/h] with a unit density,
# as for the motive valves above. LV-329502's liquor is saturated: Flowserve sized it flashing, its
# printed capacities the IEC 60534-2-1 choke FL^2 (P1 - FF Pv) at the printed vapour pressure.
# LV-329504 prints its capacity on the maximum case only; its minimum and normal capacities below
# are CALCULATED, not printed, by IEC 60534-2-1 from the case's own printed pressures, flow, density,
# vapour pressure (1 bar), critical pressure (220 bar) and FL (0.99): Kv = Q (rho / 1000 / dP_eff)^0.5,
# dP_eff = min(dP, FL^2 (P1 - FF Pv)), FF = 0.96 - 0.28 (Pv / Pc)^0.5. The same calculation gives
# 20.665 on the maximum case where Flowserve prints 20.67, and LV-329502's 15.245 / 42.542 / 37.354
# where it prints 15.25 / 42.55 / 37.36. The stroke is None where none is printed.

LV_329502 = VendorValve(
    "LV-329502", 63.0, "mod_equal_pct", "liquid", (
        SizingCase(25.0, 10.0, 223.0, 29.9, 851.0, 15.25, 53.0, fl=0.9441),
        SizingCase(19.7, 11.8, 211.0, 68.2, 851.0, 42.55, 87.0, fl=0.9244),
        SizingCase(19.7, 13.6, 211.0, 81.4, 851.0, 37.36, 83.0, fl=0.9273)),
    1, _flowserve(68))

#: LV-329505, 324E001's chest condensate to 329D001 (Pos. 71, PDF page 71, read from the scan
#: 2026-10-15): DN 100, Kvs 100, plug PODP1GG (modified equal percentage), LP condensate at
#: 143 / 140 / 140 C, flashing. Flowserve prints the capacity on its maximum case only, Kv 46.57 at
#: 74 %; the minimum and normal capacities, 11.969 and 32.366, are CALCULATED, not printed, by the
#: IEC 60534-2-1 relation above from each case's printed pressures, flow, density, vapour pressure
#: (3.93 / 3.61 bar a), critical pressure (221 bar) and FL (0.99), the relation giving 46.548 on
#: the maximum case where Flowserve prints 46.57 (decided 2026-10-15, session 37's method).
LV_329505 = VendorValve(
    "LV-329505", 100.0, "mod_equal_pct", "liquid", (
        SizingCase(4.1, 1.2, 143.0, 8.5, 921.0, 11.969, None, fl=0.99),
        SizingCase(3.7, 1.8, 140.0, 20.1, 924.0, 32.366, None, fl=0.99),
        SizingCase(3.7, 2.2, 140.0, 27.1, 924.0, 46.57, 74.0, fl=0.9281)),
    1, _flowserve(71))

LV_329504 = VendorValve(
    "LV-329504", 40.0, "mod_equal_pct", "liquid", (
        SizingCase(10.8, 4.6, 100.0, 7.3, 959.0, 2.871, None, fl=0.99),
        SizingCase(10.5, 5.0, 100.0, 20.9, 959.0, 8.727, None, fl=0.99),
        SizingCase(10.0, 7.8, 100.0, 31.3, 959.0, 20.67, 78.0, fl=0.9267)),
    1, _flowserve(70))

PV_329205A = VendorValve(
    "PV-329205A", 100.0, "mod_equal_pct", "gas", (
        SizingCase(27.0, 11.0, 330.0, 1500.0, 1.0, 5.38, 13.0, xt=0.662),
        SizingCase(21.5, 9.0, 330.0, 1763.0, 1.0, 8.0, 20.0, xt=0.662),
        SizingCase(20.0, 9.5, 330.0, 13000.0, 1.0, 64.14, 85.0, xt=0.662)),
    1, _flowserve(74))

PV_329205B = VendorValve(
    "PV-329205B", 100.0, "mod_equal_pct", "gas", (
        SizingCase(8.9, 4.4, 175.0, 2200.0, 1.0, 20.98, 48.0, xt=0.673),
        SizingCase(8.9, 4.4, 175.0, 2200.0, 1.0, 20.98, 48.0, xt=0.673),
        SizingCase(8.8, 5.5, 175.0, 6000.0, 1.0, 61.44, 84.0, xt=0.673)),
    1, _flowserve(75))

# ======================================================================================
# The Valtek linear valves (plug code ...LG)
# ======================================================================================

LV_323501 = VendorValve(
    "LV-323501", 250.0, "linear", "liquid", (
        SizingCase(6.0, 1.6, 135.0, 60.0, 1105.53, 44.39, 20.0, fl=0.9408),
        SizingCase(4.3, 1.6, 135.0, 100.0, 1105.53, 147.82, 60.0, fl=0.9319),
        SizingCase(4.3, 1.6, 135.0, 120.0, 1105.53, 181.58, 73.0, fl=0.9104)),
    1, _flowserve(51))

LV_328501 = VendorValve(
    "LV-328501", 16.0, "linear", "liquid", (
        SizingCase(7.37, 4.2, 57.0, 6.57, 1077.0, 3.83, 26.0, fl=0.9570),
        SizingCase(7.23, 4.35, 57.0, 10.95, 1077.0, 6.7, 44.0, fl=0.9495),
        SizingCase(7.13, 4.71, 57.0, 17.7, 1077.0, 11.81, 75.0, fl=0.9403)),
    1, _flowserve(61))

#: LV-329503, 329D009's drain to 322D001 (session 37): its liquor saturated, sized flashing; the
#: capacity printed on the maximum case only — the minimum and normal capacities are CALCULATED by
#: IEC 60534-2-1 as for LV-329504 above (FL 0.99, Pc 222 bar, the printed vapour pressures 9.9 and
#: 8.93 bar), the calculation giving 61.094 on the maximum case where Flowserve prints 61.11.
LV_329503 = VendorValve(
    "LV-329503", 100.0, "linear", "liquid", (
        SizingCase(10.7, 4.8, 184.0, 28.3, 883.0, 20.126, None, fl=0.99),
        SizingCase(9.0, 5.2, 175.3, 59.5, 892.0, 58.902, None, fl=0.99),
        SizingCase(8.7, 7.2, 175.0, 72.9, 892.0, 61.11, 62.0, fl=0.9154)),
    1, _flowserve(69))

# ======================================================================================
# CCI's Drag valve
# ======================================================================================

#: PV-322203, the CO2 gas bypass to the LP safe header. The sheet gives the flow in Nm3/h of
#: carbon dioxide; its normal density is the molar mass over the normal molar volume. The
#: characteristic is "Equal Percentage" with no rangeability printed, so the trim runs on
#: `control.valve.EQUAL_PCT_RANGE`, the IEC representative 50:1 — a stated choice.
PV_322203 = VendorValve(
    "PV-322203", 32.0, "equal_pct", "gas", (
        SizingCase(145.0, 3.0, 120.0, 28021.0, MW_CO2 / NORMAL_MOLAR_VOLUME_M3_KMOL, 14.36,
                   None),
        SizingCase(145.0, 3.0, 120.0, 31051.0, MW_CO2 / NORMAL_MOLAR_VOLUME_M3_KMOL, 15.91,
                   None)),
    0, "CCI Control Valve Data Sheet PV 322203, item 17, UD-MR-G00-DZ-0009-004 sheet 6")

# ======================================================================================
# Metso's Neldisc butterflies on the evaporators' steam chests
# ======================================================================================

def _metso(page: int, item: int) -> str:
    """Metso's NELPROF 3.20 sizing sheet ``item`` (rev 01, 28 July 2005), a scanned page."""
    return (f"Metso UD-MR-G00-DZ-0031-009, item {item}, PDF page {page} (scanned, read from the "
            "page image)")


def _neldisc(rated: float, cases: tuple) -> tuple:
    """A Neldisc's characteristic as its sheet prints it: the capacity of each case at its travel,
    from shut to the rated Cv wide open, linear between — the sheet names no curve. FpCv equals Cv
    on both sheets (the rated FpCv is the rated Cv), so the printed capacity is the trim's."""
    return ((0.0, 0.0),) + tuple((c.stroke_pct / 100.0, c.capacity / rated) for c in cases) + (
        (1.0, 1.0),)


# Spring-to-open metal-seated butterflies passing saturated steam. Each case prints the mass flow
# [kg/h], carried with a unit density as for the motive valves above, the capacity FpCv, the travel
# and xT; ratio of specific heats 1.3.
_PV_329203_CASES = (
    SizingCase(4.4, 3.5, 147.5, 7786.0, 1.0, 226.97, 17.1, xt=0.53),
    SizingCase(4.4, 3.9, 147.5, 18539.0, 1.0, 677.41, 39.4, xt=0.52),
    SizingCase(4.0, 3.8, 144.0, 25000.0, 1.0, 1454.62, 61.0, xt=0.43))
_PV_329212_CASES = (
    SizingCase(9.0, 5.9, 176.0, 2000.0, 1.0, 24.65, 33.4, xt=0.57),
    SizingCase(8.9, 5.9, 175.0, 4160.0, 1.0, 52.05, 54.7, xt=0.57),
    SizingCase(8.0, 5.9, 171.0, 5500.0, 1.0, 82.14, 70.5, xt=0.56))

#: PV-329203, 324E001's LP steam: DN 250 Neldisc (L-ANSI150), maximum Cv 4870.
PV_329203 = VendorValve(
    "PV-329203", 4870.0, _neldisc(4870.0, _PV_329203_CASES), "gas", _PV_329203_CASES, 1,
    _metso(28, 27))

#: PV-329212, 324E003's 9-bar steam: DN 80 balanced Neldisc (S-L-ANSI150), maximum Cv 150.
PV_329212 = VendorValve(
    "PV-329212", 150.0, _neldisc(150.0, _PV_329212_CASES), "gas", _PV_329212_CASES, 1,
    _metso(33, 32))

# The other steam butterflies on the same sheets (pages 25-32, read 2026-10-15). Where the valve is
# smaller than its line (PV-329204, PV-329207B) the sheet's capacities are FpCv and its rated FpCv is
# below the rated Cv: the catalogue rates them on the FpCv, the unit their cases print in.
_FV_329401_CASES = (
    SizingCase(4.4, 3.5, 147.5, 3930.0, 1.0, 114.56, 14.1, xt=0.53),
    SizingCase(4.4, 3.9, 147.5, 6495.0, 1.0, 237.08, 26.0, xt=0.53),
    SizingCase(4.0, 3.8, 144.0, 12000.0, 1.0, 695.16, 52.9, xt=0.47))
_PV_329202_CASES = (
    SizingCase(4.4, 3.5, 147.5, 6000.0, 1.0, 174.91, 20.6, xt=0.53),
    SizingCase(4.4, 3.9, 147.5, 9500.0, 1.0, 346.95, 34.3, xt=0.53),
    SizingCase(4.0, 3.8, 144.0, 12000.0, 1.0, 695.16, 52.9, xt=0.47))
_PV_329204_CASES = (
    SizingCase(27.0, 11.0, 330.0, 25000.0, 1.0, 113.25, 11.2, xt=0.57),
    SizingCase(22.0, 20.0, 330.0, 57989.0, 1.0, 553.69, 44.1, xt=0.57),
    SizingCase(20.0, 19.3, 330.0, 75000.0, 1.0, 1230.02, 77.7, xt=0.51))
_PV_329207A_CASES = (
    SizingCase(4.4, 1.5, 147.5, 17000.0, 1.0, 397.89, 23.1, xt=0.57),
    SizingCase(4.4, 1.5, 147.5, 22000.0, 1.0, 514.92, 28.7, xt=0.57),
    SizingCase(4.0, 2.0, 144.0, 65000.0, 1.0, 1777.57, 64.2, xt=0.51))
_PV_329207B_CASES = (
    SizingCase(7.0, 3.5, 165.0, 7000.0, 1.0, 104.47, 10.0, xt=0.57),
    SizingCase(4.4, 4.2, 147.5, 17707.0, 1.0, 972.53, 58.0, xt=0.55),
    SizingCase(4.0, 3.8, 144.0, 19700.0, 1.0, 1137.87, 63.3, xt=0.52))
_PV_329208_CASES = (
    SizingCase(4.4, 3.4, 147.5, 5000.0, 1.0, 139.02, 12.9, xt=0.57),
    SizingCase(4.4, 3.5, 147.5, 11488.0, 1.0, 331.15, 27.8, xt=0.57),
    SizingCase(4.0, 3.8, 144.0, 17000.0, 1.0, 979.31, 58.0, xt=0.55))

#: FV-329401, 328C004's LP stripping steam: DN 200 Neldisc, maximum Cv 3050 (item 24, rev 00).
FV_329401 = VendorValve(
    "FV-329401", 3050.0, _neldisc(3050.0, _FV_329401_CASES), "gas", _FV_329401_CASES, 1,
    _metso(25, 24))

#: PV-329202, 323E002's chest: DN 200 Neldisc, maximum Cv 3050 (item 26, rev 00).
PV_329202 = VendorValve(
    "PV-329202", 3050.0, _neldisc(3050.0, _PV_329202_CASES), "gas", _PV_329202_CASES, 1,
    _metso(27, 26))

#: PV-329204, superheated MP steam to 329D005: DN 250 balanced Neldisc in a DN 300 line, Cv 1640,
#: FpCv 1604.25 (item 28, rev 00).
PV_329204 = VendorValve(
    "PV-329204", 1604.25, _neldisc(1604.25, _PV_329204_CASES), "gas", _PV_329204_CASES, 1,
    _metso(29, 28))

#: PV-329207A, the LP header to atmosphere: DN 300 balanced Neldisc, maximum Cv 3880 (item 29,
#: rev 01).
PV_329207A = VendorValve(
    "PV-329207A", 3880.0, _neldisc(3880.0, _PV_329207A_CASES), "gas", _PV_329207A_CASES, 1,
    _metso(30, 29))

#: PV-329207B: DN 250 balanced Neldisc in a DN 300 line, Cv 2580, FpCv 2447.16 (item 30, rev 00).
PV_329207B = VendorValve(
    "PV-329207B", 2447.16, _neldisc(2447.16, _PV_329207B_CASES), "gas", _PV_329207B_CASES, 1,
    _metso(31, 30))

#: PV-329208, 323E010's chest: DN 250 balanced Neldisc, maximum Cv 2580 (item 31, rev 00).
PV_329208 = VendorValve(
    "PV-329208", 2580.0, _neldisc(2580.0, _PV_329208_CASES), "gas", _PV_329208_CASES, 1,
    _metso(32, 31))

#: FV-329409, 322E003's tempered water on FIC-329409: DN 150 Neldisc, maximum Cv 1240 (item 25,
#: rev 00, page 26, read from the scan 2026-10-15): circulating water at 95 C, 52 / 312 / 478 m3/h
#: from 13.0 / 12.6 / 12.2 to 10.6 / 10.9 / 10.9 bar a, vapour pressure 0.85 bar a, FL 0.86 / 0.80 /
#: 0.75. The sheet prints no density; the cases carry IAPWS-IF97's saturated liquid at its 95 C,
#: 961.89 kg/m3 (decided 2026-10-15; compressed to the cases' 12-13 bar a it is 0.06 % denser).
_FV_329409_RHO_KGM3 = rho_liquid_sat_kgm3(95.0)
_FV_329409_CASES = (
    SizingCase(13.0, 10.6, 95.0, 52.0, _FV_329409_RHO_KGM3, 38.11, 9.1, fl=0.86),
    SizingCase(12.6, 10.9, 95.0, 312.0, _FV_329409_RHO_KGM3, 271.69, 46.4, fl=0.80),
    SizingCase(12.2, 10.9, 95.0, 478.0, _FV_329409_RHO_KGM3, 476.0, 63.5, fl=0.75))
FV_329409 = VendorValve(
    "FV-329409", 1240.0, _neldisc(1240.0, _FV_329409_CASES), "liquid", _FV_329409_CASES, 1,
    _metso(26, 25))

# Read 2026-10-16 (handoff Open data gaps, "valves no vendor set lists"; Metso's pages 20-24, items
# 19-23, rev 00, 7 February 2005): five more Neldisc butterflies. Catalogued for their units' ports
# (§5 rule 7); not yet wired, their units still run V1's laws.

#: HV-323605, 323F010's vapour to 324E002: DN 400 Neldisc (L-ANSI150), maximum Cv 13700 (item 19,
#: page 20). "Vapours", specific gravity 0.641 (to air), k 1.4: 14734 / 21870 Nm3/h at 99 C from 0.5
#: to 0.47 bar a, xT 0.38 / 0.29. The sheet prints no density: the cases carry 0.641 times air's
#: normal density, 28.9647 / 22.414 kg/Nm3 — 0.8283 kg/Nm3, so case 1 is 12 205 kg/h against PFD
#: 790's 12 040: case 1 is the normal case.
_HV_323605_RHO_KGNM3 = 0.641 * 28.9647 / NORMAL_MOLAR_VOLUME_M3_KMOL
_HV_323605_CASES = (
    SizingCase(0.5, 0.47, 99.0, 14734.0, _HV_323605_RHO_KGNM3, 4704.52, 65.1, xt=0.38),
    SizingCase(0.5, 0.47, 99.0, 21870.0, _HV_323605_RHO_KGNM3, 7110.53, 78.1, xt=0.29))
HV_323605 = VendorValve(
    "HV-323605", 13700.0, _neldisc(13700.0, _HV_323605_CASES), "gas", _HV_323605_CASES, 0,
    _metso(20, 19))

#: PV-323203, the LP flash gas node's vent to 323C005: a DN 200 x 150 Neldisc (L4K, PN 10), maximum
#: Cv 840, FpCv 634.57 (item 22, page 23), rated on the FpCv as PV-329204 is. "Carbamate gas", k 1.4:
#: 540 / 1600 Nm3/h at 45 C from 1.1 to 1.0 bar a, inlet density 0.69 kg/m3, xT 0.53 / 0.52. In
#: normal cubic metres that density is 0.69 . (1.01325 / 1.1) . (318.15 / 273.15) = 0.740 kg/Nm3
#: (the ideal gas law, calculated): case 1 is 400 kg/h against PFD 702's 440, the normal case.
_PV_323203_RHO_KGNM3 = 0.69 * (1.01325 / 1.1) * (318.15 / 273.15)
_PV_323203_CASES = (
    SizingCase(1.1, 1.0, 45.0, 540.0, _PV_323203_RHO_KGNM3, 55.92, 20.4, xt=0.53),
    SizingCase(1.1, 1.0, 45.0, 1600.0, _PV_323203_RHO_KGNM3, 166.05, 44.6, xt=0.52))
PV_323203 = VendorValve(
    "PV-323203", 634.57, _neldisc(634.57, _PV_323203_CASES), "gas", _PV_323203_CASES, 0,
    _metso(23, 22))

#: PV-323202A and PV-323202B, "circulating water" at 65 C: DN 300 (Cv 7300) and DN 250 (Cv 4870)
#: Neldiscs, 305.8 / 917.8 / 1233.4 m3/h each (items 20, 21, pages 21-22). They are the tempered-
#: water valves at cooler 329E002 that P&IDs 103/1 and 109 tag PV-323202A / B and the loop summary
#: T 323013 tags TV-323013A (DN 300, FC, 917.8 m3/h) and TV-323013B (DN 250, FO) — the second column
#: of handoff B-36's table (As-Built §XXXIII.5), not the gas vent the port calls PV-323202. The
#: sheets print no density: IAPWS-IF97's saturated liquid at 65 C (decision 116's class).
_TW_65_RHO_KGM3 = rho_liquid_sat_kgm3(65.0)
_PV_323202A_CASES = (
    SizingCase(6.0, 4.1, 65.0, 305.8, _TW_65_RHO_KGM3, 254.18, 13.2, fl=0.87),
    SizingCase(5.3, 4.1, 65.0, 917.8, _TW_65_RHO_KGM3, 959.92, 37.8, fl=0.82),
    SizingCase(4.4, 4.1, 65.0, 1233.4, _TW_65_RHO_KGM3, 2580.01, 65.9, fl=0.71))
PV_323202A = VendorValve(
    "PV-323202A", 7300.0, _neldisc(7300.0, _PV_323202A_CASES), "liquid", _PV_323202A_CASES, 1,
    _metso(21, 20))
_PV_323202B_CASES = (
    SizingCase(6.0, 3.4, 65.0, 305.8, _TW_65_RHO_KGM3, 217.28, 16.5, fl=0.86),
    SizingCase(5.3, 3.4, 65.0, 917.8, _TW_65_RHO_KGM3, 762.87, 42.4, fl=0.81),
    SizingCase(4.4, 3.4, 65.0, 1233.4, _TW_65_RHO_KGM3, 1413.13, 60.3, fl=0.74))
PV_323202B = VendorValve(
    "PV-323202B", 4870.0, _neldisc(4870.0, _PV_323202B_CASES), "liquid", _PV_323202B_CASES, 1,
    _metso(22, 21))

#: TV-328002, 328E004's cooling-water return on TIC-328002: DN 200 Neldisc, maximum Cv 3050 (item
#: 23, page 24): "circulating water" at 38 C, 150 / 410 / 530 m3/h from 2.9 / 2.4 / 2.07 to 2.0 bar a,
#: FL 0.85 / 0.77 / 0.54. No density printed: IAPWS-IF97's saturated liquid at 38 C.
_TV_328002_RHO_KGM3 = rho_liquid_sat_kgm3(38.0)
_TV_328002_CASES = (
    SizingCase(2.9, 2.0, 38.0, 150.0, _TV_328002_RHO_KGM3, 182.24, 21.2, fl=0.85),
    SizingCase(2.4, 2.0, 38.0, 410.0, _TV_328002_RHO_KGM3, 747.18, 55.0, fl=0.77),
    SizingCase(2.07, 2.0, 38.0, 530.0, _TV_328002_RHO_KGM3, 2308.86, 90.5, fl=0.54))
TV_328002 = VendorValve(
    "TV-328002", 3050.0, _neldisc(3050.0, _TV_328002_CASES), "liquid", _TV_328002_CASES, 1,
    _metso(24, 23))

#: Every catalogued valve, by tag.
VENDOR_VALVES = {v.tag: v for v in (
    FV_323401, FV_323402, FV_323418, LV_323503, LV_323505, FV_324401, FV_328402, FV_328404,
    FV_328405, FV_328406, LV_328505, PV_328202, PV_328203, LV_322502, PV_322201, LV_323501,
    LV_328501, PV_322203, PV_324202, PV_324203, HV_329605, HV_329606, LV_329502, LV_329503,
    LV_329504, PV_329205A, PV_329205B, PV_329203, PV_329212, FV_329401, PV_329202, PV_329204,
    PV_329207A, PV_329207B, PV_329208, LV_329505, FV_329409, HV_323605, PV_323203, PV_323202A,
    PV_323202B, TV_328002)}

__all__ = [
    "NORMAL_MOLAR_VOLUME_M3_KMOL", "MW_CO2", "SizingCase", "VendorValve", "design_stroke_pct",
    "full_stroke_m3h", "FV_323401", "FV_323402", "FV_323418", "LV_323503", "LV_323505",
    "FV_324401", "FV_328402", "FV_328404", "FV_328405", "FV_328406", "LV_328505", "PV_328202",
    "PV_328203",
    "LV_322502", "PV_322201", "LV_323501", "LV_328501", "PV_322203", "PV_324202", "PV_324203",
    "HV_329605", "HV_329606", "LV_329502", "LV_329503", "LV_329504", "PV_329205A",
    "PV_329205B", "PV_329203", "PV_329212", "FV_329401", "PV_329202", "PV_329204", "PV_329207A",
    "PV_329207B", "PV_329208", "LV_329505", "FV_329409", "HV_323605", "PV_323203", "PV_323202A",
    "PV_323202B", "TV_328002", "VENDOR_VALVES",
]
