"""Fisher's control valves (Emerson Process Management), as sized for Uhde.

What this is
------------
Four urea-plant valves the Flowserve and Metso files do not carry are Fisher globe valves, sized on
three cases each (minimum, normal, maximum): LV-328503 and LV-328504 (the desorbers' bottoms
letdowns), HV-329602 (the hand valve beside PV-329207C on the supply to the LP header) and the
323D001 vent the port calls PV-323202 — tagged TV-323013 on Fisher's sheet as on P&ID 103/1, its
three cases the loop summary P 323202's (600 / 1200 / 4000 Nm3/h from 3.2 bar a). Each runs its
vendor trim under decision 23's class (`project.md` decision 150): the design stroke is where its
rated Cv passes the design flow on its normal case (`control_valves.design_stroke_pct`).

The sheets name each trim's curve ("Equal %", "Linear"): the port runs its own equal-percentage
law on the IEC representative 50:1, as for CCI's PV-322203, and its linear law. The travels Fisher
prints ("% Open") sit off those curves — two to six points below them on the two letdowns and
HV-329602, and far from the line on TV-323013's Whisper I cage (8 / 19 / 90 % for 10 / 39 / 97 % of
its Cv) — Fisher's own characterised trims; they are kept in each case's ``stroke_pct`` as printed.

Fisher prints liquids' specific gravity, which the cases carry times IEC 60534's reference water,
1000 kg/m3; gases' specific gravity to air, carried as kg/Nm3 on air's normal density (as
HV-323605's Metso sheet); steam's mass flow with a unit density, as Flowserve's steam sheets.

Source
------
Fisher, "Valve Specifications" UD-MR-G00-DZ-0014-001 (items 021-025, PDF pages 19-23) and "Sizing
Calculations" -002 (the same items, PDF pages 19-23), quote 097L057181 rev A0, 23 March 2005; the
vendor archive's file 10, scanned, read from the page images 2026-10-22.
"""

from __future__ import annotations

from ureasim.data.control_valves import NORMAL_MOLAR_VOLUME_M3_KMOL, SizingCase, VendorValve

#: IEC 60534's reference density of water [kg/m3], what Fisher's liquid specific gravity is to.
RHO_WATER_REF_KGM3 = 1000.0

#: Air's molar mass [kg/kmol], what a gas specific gravity is to.
MW_AIR = 28.9647


def _fisher(item: int, page: int) -> str:
    """Fisher's specification and sizing sheet of ``item``."""
    return (f"Fisher UD-MR-G00-DZ-0014-001 / -002, item {item:03d}, PDF page {page} "
            "(scanned, read from the page images)")


#: LV-328503, 328P006's discharge to 328E021 and the hydrolyser: DN 100 x 50 EWT globe, trim 1,
#: port 2 5/16 in, equal percentage, rated Cv 82.2, fail closed; ammonia water at 138 C, SG 0.933,
#: vapour pressure 3.7 bar a, FL 0.819.
_RHO_503 = 0.933 * RHO_WATER_REF_KGM3
LV_328503 = VendorValve(
    "LV-328503", 82.2, "equal_pct", "liquid", (
        SizingCase(24.1, 22.86, 138.0, 23.4, _RHO_503, 23.466, 63.0, fl=0.819),
        SizingCase(24.0, 16.98, 138.0, 38.9, _RHO_503, 16.395, 54.0, fl=0.819),
        SizingCase(23.89, 17.12, 138.0, 51.3, _RHO_503, 22.017, 62.0, fl=0.819)),
    1, _fisher(22, 20))

#: LV-328504, the hydrolyser's bottoms to 328C004: the same DN 100 x 50 EWT body, trim 29, equal
#: percentage, rated Cv 82.2, fail closed; ammonia water at 147 C, SG 0.925, vapour pressure 4.5
#: bar a, FL 0.819.
_RHO_504 = 0.925 * RHO_WATER_REF_KGM3
LV_328504 = VendorValve(
    "LV-328504", 82.2, "equal_pct", "liquid", (
        SizingCase(14.22, 3.81, 147.0, 23.8, _RHO_504, 10.164, 42.0, fl=0.819),
        SizingCase(14.16, 3.81, 147.0, 39.6, _RHO_504, 16.963, 55.0, fl=0.819),
        SizingCase(14.08, 3.81, 147.0, 52.2, _RHO_504, 22.450, 62.0, fl=0.819)),
    1, _fisher(23, 21))

#: HV-329602, PV-329207C's parallel hand valve on the supply to the LP header: DN 150 ED globe,
#: Whisper III / B3 cage, linear, rated Cv 228, fail closed; steam, F_k 0.921, xT 0.532.
HV_329602 = VendorValve(
    "HV-329602", 228.0, "linear", "gas", (
        SizingCase(27.0, 3.0, 400.0, 5000.0, 1.0, 25.130, 15.0, xt=0.532),
        SizingCase(22.0, 4.4, 330.0, 20000.0, 1.0, 116.228, 48.0, xt=0.532),
        SizingCase(20.0, 7.0, 330.0, 32000.0, 1.0, 204.932, 87.0, xt=0.532)),
    1, _fisher(25, 23))

#: TV-323013 on Fisher's sheet, the 323D001 vent the port calls PV-323202: DN 80 ET globe, Whisper I
#: cage, linear, rated Cv 99.1, fail open; "carbonate gas" at 74 C, SG 0.909 to air, F_k 0.929.
_RHO_VENT_KGNM3 = 0.909 * MW_AIR / NORMAL_MOLAR_VOLUME_M3_KMOL
PV_323202 = VendorValve(
    "PV-323202", 99.1, "linear", "gas", (
        SizingCase(5.0, 1.1, 74.0, 600.0, _RHO_VENT_KGNM3, 10.179, 8.0, xt=0.685),
        SizingCase(3.2, 1.3, 74.0, 1200.2, _RHO_VENT_KGNM3, 38.489, 19.0, xt=0.470),
        SizingCase(3.2, 1.3, 74.0, 4000.0, _RHO_VENT_KGNM3, 95.738, 90.0, xt=0.967)),
    1, _fisher(21, 19))

#: Fisher's valves, by tag.
FISHER_VALVES = {v.tag: v for v in (LV_328503, LV_328504, HV_329602, PV_323202)}

__all__ = ["RHO_WATER_REF_KGM3", "MW_AIR", "LV_328503", "LV_328504", "HV_329602", "PV_323202",
           "FISHER_VALVES"]
