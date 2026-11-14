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
  the calculation sheets, -003 — one page per position, PDF pages 46 to 76 and 148-149 for the
  positions below, giving Kvs, plug code (the sixth letter the characteristic: G modified equal
  percentage, L linear, R equal percentage) and, per case, the pressures, temperature, flow,
  density, the calculated Kv, the stroke, and FL (liquid) or xT (gas).
* Fisher's sheets (Emerson, UD-MR-G00-DZ-0014) are catalogued in `control_valves_fisher`.
* Metso's NELPROF sheets (UD-MR-G00-DZ-0031-009) are catalogued in `control_valves_metso`, and the
  sizing records and the design-stroke anchor live in `valve_sizing` (split out 2026-10-23); this
  module re-exports both, and ``VENDOR_VALVES`` holds Flowserve's, CCI's and Metso's valves.
* CCI, Control Valve Data Sheet PV 322203, item 17, UD-MR-G00-DZ-0009-004 sheet 6 (scanned):
  a Drag 28-stage angle valve, rated Cv/Kv 32/27, equal percentage, fail open; normal and
  maximum cases; no FL, xT or stroke printed.

Ported valves use these entries now; the rest are catalogued for their units' ports (§5
rule 7). Where a sheet prints a case's capacity only on its maximum case, the other cases'
capacities are calculated by IEC 60534-2-1 from what the case prints, and say so.
"""

from __future__ import annotations

from ureasim.data.control_valves_metso import (
    FV_329401,
    FV_329409,
    HV_323605,
    PV_323202A,
    PV_323202B,
    PV_323203,
    PV_329202,
    PV_329203,
    PV_329204,
    PV_329207A,
    PV_329207B,
    PV_329208,
    PV_329212,
    TV_328002,
)
from ureasim.data.valve_sizing import (
    NORMAL_MOLAR_VOLUME_M3_KMOL,
    SizingCase,
    VendorValve,
    design_stroke_pct,
    full_stroke_m3h,
)

#: Molar mass of carbon dioxide [kg/kmol], CCI's fluid.
MW_CO2 = 44.0095


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
# The Mark One and 0310 sheets found in session 69 (Pos. 65, 76, 148, 149)
# ======================================================================================

# Flowserve's summary of items lists HV 329601 (Pos. 65), PV 329207C (Pos. 76) and LV 324501A twice
# (Pos. 148 and 149, the second sheet tagged LV 324501B); their calculation sheets are pages 65, 76,
# 148 and 149 of -003 (read from the scans 2026-10-22). Each names its curve "Equal Percent" or
# "Linear" (plug codes ...RG and ...LG): the trims run the port's equal-percentage law on the IEC
# representative 50:1, which LV-324501A / B's sheets print as their rangeability, and its linear law.
# The two Mark One steam sheets print no xT; their choke drop is printed, and each case's xT below is
# CALCULATED from it, xT = dP_choke / (F_gamma P1), F_gamma = 1.30 / 1.40 on the port's steam.
_F_GAMMA_STEAM = 1.30 / 1.40


def _xt_steam(dp_choke_bar: float, p1_bara: float) -> float:
    """A Mark One sheet's xT, from its printed choke drop on steam."""
    return dp_choke_bar / (_F_GAMMA_STEAM * p1_bara)


#: HV-329601, 329D005's vent to the 329D010 silencer: a DN 80 Mark One globe, Kv 64, equal
#: percentage, fail closed, "with throttle disc in sandwich design"; steam, the mass flow with a
#: unit density as for the motive valves.
HV_329601 = VendorValve(
    "HV-329601", 64.0, "equal_pct", "gas", (
        SizingCase(25.0, 1.5, 225.0, 1500.0, 1.0, 4.715, 24.0, xt=_xt_steam(19.126, 25.0)),
        SizingCase(19.9, 1.5, 213.0, 1500.0, 1.0, 5.944, 31.0, xt=_xt_steam(15.086, 19.9)),
        SizingCase(17.1, 1.5, 205.0, 8000.0, 1.0, 38.442, 82.0, xt=_xt_steam(12.021, 17.1))),
    1, _flowserve(65))

#: PV-329207C, the supply to the LP header: a DN 150 two-stage Mark One MegaStream globe, Kv 172,
#: linear, fail closed.
PV_329207C = VendorValve(
    "PV-329207C", 172.0, "linear", "gas", (
        SizingCase(27.0, 3.0, 400.0, 5000.0, 1.0, 25.331, 8.0, xt=_xt_steam(9.747, 27.0)),
        SizingCase(22.0, 4.4, 330.0, 20000.0, 1.0, 98.618, 50.0, xt=_xt_steam(11.171, 22.0)),
        SizingCase(20.0, 7.0, 330.0, 32000.0, 1.0, 153.897, 84.0, xt=_xt_steam(13.080, 20.0))),
    1, _flowserve(76))

#: LV-324501A (to the granulation's melt header, fail closed, quick closing under 3 s) and
#: LV-324501B (the recycle to 323D002, fail open): DN 100 0310 angle valves, Kvs 100, equal
#: percentage 50:1, urea solution at 140 C on the sheets' SG 0.751 — which is not the melt's
#: 1221 kg/m3 (loop summary L 324501); the sheets' FL is not printed.
LV_324501A = VendorValve(
    "LV-324501A", 100.0, "equal_pct", "liquid", (
        SizingCase(8.0, 3.6, 140.0, 8.0, 751.0, 3.278, 11.0),
        SizingCase(6.9, 3.7, 140.0, 70.5, 751.0, 33.889, 71.0),
        SizingCase(4.9, 4.7, 140.0, 82.0, 751.0, 158.332, 100.0)),
    1, _flowserve(148))

LV_324501B = VendorValve(
    "LV-324501B", 100.0, "equal_pct", "liquid", (
        SizingCase(8.0, 1.0, 140.0, 8.0, 751.0, 2.599, 8.0),
        SizingCase(6.9, 1.8, 140.0, 70.5, 751.0, 26.839, 65.0),
        SizingCase(4.8, 2.0, 140.0, 82.0, 751.0, 42.150, 76.0)),
    1, _flowserve(149))

#: HV-335602, the urea melt main header's end drain to 335D004 (P&ID 130, UD-VT-335-FB-0004: fail
#: open, air to close, "FAST OPEN / SLOW CLOSE"): DN 50 0310 globe, seat 32, Kvs 25, equal percentage
#: 50:1; its one case, urea solution at 140 C on the sheet's SG 0.751 (not the melt's 1221 kg/m3),
#: 24 m3/h across 5.1 -> 1.1 bar a at Kv 10.314 and an estimated 77 % (read from the scanned sheet).
HV_335602 = VendorValve(
    "HV-335602", 25.0, "equal_pct", "liquid", (
        SizingCase(5.1, 1.1, 140.0, 24.0, 751.0, 10.314, 77.0),),
    0, _flowserve(150))

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

#: Every catalogued valve, by tag.
VENDOR_VALVES = {v.tag: v for v in (
    FV_323401, FV_323402, FV_323418, LV_323503, LV_323505, FV_324401, FV_328402, FV_328404,
    FV_328405, FV_328406, LV_328505, PV_328202, PV_328203, LV_322502, PV_322201, LV_323501,
    LV_328501, PV_322203, PV_324202, PV_324203, HV_329605, HV_329606, LV_329502, LV_329503,
    LV_329504, PV_329205A, PV_329205B, PV_329203, PV_329212, FV_329401, PV_329202, PV_329204,
    PV_329207A, PV_329207B, PV_329208, LV_329505, FV_329409, HV_323605, PV_323203, PV_323202A,
    PV_323202B, TV_328002, HV_329601, PV_329207C, LV_324501A, LV_324501B, HV_335602)}

__all__ = [
    "NORMAL_MOLAR_VOLUME_M3_KMOL", "MW_CO2", "SizingCase", "VendorValve", "design_stroke_pct",
    "full_stroke_m3h", "FV_323401", "FV_323402", "FV_323418", "LV_323503", "LV_323505",
    "FV_324401", "FV_328402", "FV_328404", "FV_328405", "FV_328406", "LV_328505", "PV_328202",
    "PV_328203",
    "LV_322502", "PV_322201", "LV_323501", "LV_328501", "PV_322203", "PV_324202", "PV_324203",
    "HV_329605", "HV_329606", "LV_329502", "LV_329503", "LV_329504", "PV_329205A",
    "PV_329205B", "PV_329203", "PV_329212", "FV_329401", "PV_329202", "PV_329204", "PV_329207A",
    "PV_329207B", "PV_329208", "LV_329505", "FV_329409", "HV_323605", "PV_323203", "PV_323202A",
    "PV_323202B", "TV_328002", "HV_329601", "PV_329207C", "LV_324501A", "LV_324501B",
    "HV_335602", "VENDOR_VALVES",
]
