"""Metso's control valves (Neles Neldisc butterflies), as sized for Uhde.

What this is
------------
Fourteen urea-plant valves are Metso's Neldisc triple-eccentric butterflies, sized on Metso's
NELPROF 3.20 sheets on three cases each (minimum, normal, maximum): the steam valves on the
evaporators' and the desorbers' chests and on the steam network (PV-329202, PV-329203, PV-329204,
PV-329207A / B, PV-329208, PV-329212, FV-329401), the tempered and cooling water (FV-329409,
PV-323202A / B, TV-328002) and two gas lines (HV-323605, PV-323203). Each runs its vendor trim
under decision 23's class: the design stroke is where its rated capacity passes the design flow
on its normal case (`valve_sizing.design_stroke_pct`).

The sheets print each case's capacity at its travel and name no curve, so a Neldisc's
characteristic is anchored on its printed points, from shut to the rated Cv wide open (decision
108, which drew a straight line between them). Every valve keeps every printed point and takes the
shape between them, and from the last to wide open, from the vendor's published table for its
sheet's valve series: the five balanced valves (S-L-ANSI150 and S-L-ANSI300: PV-329204,
PV-329207A / B, PV-329208, PV-329212) from Valmet's S-Disc table (decision 170, 2026-11-06), the nine
conventional ones (L-ANSI150 and L-ANSI300) from Valmet's L-series Cv tables (decision 178,
2026-11-07). A sheet that prints no density
carries IAPWS-IF97's saturated liquid at its rating
temperature (decision 116); a gas the sheet gives as a specific gravity carries kg/Nm3 on air's
normal density; steam carries its mass flow with a unit density, as Flowserve's steam sheets.

Moved out of `control_valves` unchanged (2026-10-23, the housekeeping split); `control_valves`
re-exports every valve and keeps them in ``VENDOR_VALVES``.

Source
------
Metso, NELPROF 3.20 sizing sheets, UD-MR-G00-DZ-0031-009 (items 19-33, rev 00 and 01, 7 February
and 28 July 2005; the vendor archive, scanned, read from the page images 2026-10-15 and
2026-10-16). Each valve cites its item and PDF page. The balanced valves' relative-Cv table is
Valmet (Neles), bulletin 2SL120EN, "Neldisc triple eccentric disc valve with flow balancing trim
S-Disc", 4/2022, Table 2 (https://www.valmet.com/globalassets/sharepoint/imported/2sl120en.pdf;
a public vendor document, not in the plant archive). The conventional valves' table is Valmet's
online Cv table for the series codes the sheets print, "Series L1 high performance triple eccentric
metal seated butterfly valve", L1_LANSI150 and L1_LANSI300
(https://www.valmet.com/globalassets/flow-control/services/, read 2026-11-07; the L2 pages print the
same rows; the pages are archived in D:\\Work\\reports beside the bulletins).
"""

from __future__ import annotations

from ureasim.data.valve_sizing import NORMAL_MOLAR_VOLUME_M3_KMOL, SizingCase, VendorValve
from ureasim.thermo.iapws import rho_liquid_sat_kgm3


def _metso(page: int, item: int) -> str:
    """Metso's NELPROF 3.20 sizing sheet ``item`` (rev 01, 28 July 2005), a scanned page."""
    return (f"Metso UD-MR-G00-DZ-0031-009, item {item}, PDF page {page} (scanned, read from the "
            "page image)")


def _s_disc_source(page: int, item: int, ansi_class: int) -> str:
    """A balanced valve's source: Metso's sheet for the printed points, Valmet's table for the shape."""
    return (_metso(page, item) + f"; shape between the points: Valmet bulletin 2SL120EN (4/2022) "
            f"Table 2, ASME {ansi_class} column (decision 170)")


def _l_series_source(page: int, item: int, ansi_class: int, dn: int) -> str:
    """A conventional valve's source: Metso's sheet for the printed points, Valmet's L-series row for
    the shape."""
    return (_metso(page, item) + f"; shape between the points: Valmet L1_LANSI{ansi_class} Cv table, "
            f"DN {dn} row (decision 178)")


def _neldisc(rated: float, cases: tuple) -> tuple:
    """A Neldisc's characteristic as its sheet prints it: the capacity of each case at its travel,
    from shut to the rated Cv wide open, linear between — the sheet names no curve. FpCv equals Cv
    on both sheets (the rated FpCv is the rated Cv), so the printed capacity is the trim's."""
    return ((0.0, 0.0),) + tuple((c.stroke_pct / 100.0, c.capacity / rated) for c in cases) + (
        (1.0, 1.0),)


#: Valmet bulletin 2SL120EN (4/2022), Table 2: the balanced Neldisc's Cv / Cv_max at 10, 20 ... 100 %
#: of its 80 degree travel, by ANSI class (the sheet's valve series prints the class). The table
#: starts at 10 %: that it is shut at 0 % is an assumption, as for every printed-point trim here. The
#: table's FL, Z and xT columns are not adopted; the sheets print their own FL and xT.
S_DISC_RELATIVE_CV = {
    150: (0.040, 0.086, 0.140, 0.208, 0.295, 0.401, 0.538, 0.688, 0.872, 1.000),
    300: (0.061, 0.126, 0.202, 0.292, 0.405, 0.531, 0.667, 0.788, 0.899, 1.000),
}

#: Valmet's online Cv tables for the conventional Neldisc (series L1, the L2 pages printing the same
#: rows): Cv at 10, 20 ... 100 % relative opening, by (ASME class, DN), for the sizes the nine
#: conventional sheets name. Each row's 100 % value is the sheet's maximum Cv: DN 200 3050, DN 250 4870,
#: DN 300 7300, DN 400 13700, and at ASME 300 DN 150 1240; PV-323203's 840 is the DN 125 row, whose xT
#: (0.53 to 40 %, 0.52 at 50 %) is the xT its sheet prints at 20.4 and 44.6 %. At the sheets' printed
#: travels the rows, linear between their 10 % nodes, give the printed capacities within 1.5 %, all but
#: PV-323203's 44.6 % point within 0.4 % (PV-323203 on its Cv). The pages'
#: FL, xT and Fd tables are not adopted: the sheets print their own. Source: Valmet, L1_LANSI150.html
#: and L1_LANSI300.html (module docstring), read 2026-11-07. Decision 178.
L_SERIES_CV = {
    (150, 125): (25.0, 54.6, 92.0, 140.0, 202.0, 284.0, 394.0, 542.0, 757.0, 840.0),
    (150, 200): (76.8, 168.0, 283.0, 432.0, 622.0, 874.0, 1212.0, 1668.0, 2268.0, 3050.0),
    (150, 250): (123.0, 269.0, 453.0, 691.0, 995.0, 1398.0, 1939.0, 2669.0, 3622.0, 4870.0),
    (150, 300): (184.0, 403.0, 680.0, 1037.0, 1492.0, 2097.0, 2909.0, 4003.0, 5429.0, 7300.0),
    (150, 400): (346.0, 756.0, 1274.0, 1944.0, 2797.0, 3931.0, 5454.0, 7506.0, 10189.0, 13700.0),
    (300, 150): (42.0, 87.0, 144.0, 213.0, 304.0, 422.0, 576.0, 757.0, 1013.0, 1240.0),
}

#: Nodes closer than this to a printed point are the printed point (a travel and a table node that
#: coincide, as PV-329207B's 10.0 %).
_NODE_TOL = 1e-9


def _s_disc(rated: float, cases: tuple, ansi_class: int) -> tuple:
    """A balanced Neldisc's characteristic: every printed point of its sheet, and between them (and
    from the last to wide open) the shape of Valmet's S-Disc table (`_through_table`).

    Process utility
    ---------------
    A control valve's gain between two sizing cases decides how the steam header answers the
    controller away from the design point. The sheet prints three capacities and no curve; the
    straight line between them overstates a balanced valve's capacity by up to 30 % between widely
    spaced points (PV-329207B at 30 % travel) and understates it near full travel.

    Source: Valmet 2SL120EN Table 2; the Metso sheets for the anchors. Decision 170.
    """
    return _through_table(rated, cases, S_DISC_RELATIVE_CV[ansi_class])


def _l_series(rated: float, cases: tuple, ansi_class: int, dn: int) -> tuple:
    """A conventional Neldisc's characteristic: every printed point of its sheet, and between them
    (and from the last to wide open) the shape of Valmet's L-series Cv row for its class and size.

    Process utility
    ---------------
    The nine conventional valves' sheets print two or three capacities, the last at 44.6 to 90.5 %
    travel; the straight line from there to the rated Cv passes up to 28 % more than the vendor's
    characteristic (FV-329401 and PV-329202 at 70 %), so a controller driving the valve past its last
    sizing case sees too much gain. The row is the table the sheet was sized from, reproduced at the
    printed points within 1.5 %; anchored on them, the sheet is kept where it prints and a
    design stroke placed on a printed case is untouched.

    PV-323203's rated 634.57 is the FpCv of its 200 x 150 installation; its points are FpCv
    fractions on that, and the affine map takes only the row's shape, so the DN 125 row (Cv 840)
    serves it as it is.

    Source: Valmet L1_LANSI150 / L1_LANSI300 (`L_SERIES_CV`); the Metso sheets for the anchors.
    Decision 178.
    """
    row = L_SERIES_CV[(ansi_class, dn)]
    return _through_table(rated, cases, tuple(cv / row[-1] for cv in row))


def _through_table(rated: float, cases: tuple, relative: tuple) -> tuple:
    """A Neldisc's characteristic through its sheet's printed points with the shape of a vendor table.

    Process utility
    ---------------
    The vendor's own table gives the curve's shape, and the sheet's points anchor it, so the sheet is
    reproduced exactly where it prints and the design point, placed on the sheet's normal case, is
    untouched (decisions 170 and 178).

    Equation
    --------
    With T(h) the table (``relative``: Cv / Cv_max at 10, 20 ... 100 % opening), linear between its
    nodes and zero at h = 0, and two neighbouring anchors (h_a, y_a) and (h_b, y_b) among shut, the
    printed points and wide open:

        y(h) = y_a + (T(h) - T(h_a)) . (y_b - y_a) / (T(h_b) - T(h_a))      h_a <= h <= h_b

    an affine map of the table onto the segment, so y is continuous, passes every anchor and is a
    straight line wherever the table is one. The table's 10 % nodes are added as points.
    """
    nodes = tuple(((i + 1) / 10.0, f) for i, f in enumerate(relative))
    knots = ((0.0, 0.0),) + nodes

    def table(h: float) -> float:
        for (h0, f0), (h1, f1) in zip(knots, knots[1:]):
            if h <= h1:
                return f0 + (f1 - f0) * (h - h0) / (h1 - h0)
        return knots[-1][1]

    anchors = _neldisc(rated, cases)
    points = [anchors[0]]
    for (h_a, y_a), (h_b, y_b) in zip(anchors, anchors[1:]):
        scale = (y_b - y_a) / (table(h_b) - table(h_a))
        for h_n, _ in nodes:
            if h_a + _NODE_TOL < h_n < h_b - _NODE_TOL:
                points.append((h_n, y_a + (table(h_n) - table(h_a)) * scale))
        points.append((h_b, y_b))
    return tuple(points)


# Spring-to-open metal-seated butterflies passing saturated steam. Each case prints the mass flow
# [kg/h], carried with a unit density as for Flowserve's motive valves, the capacity FpCv, the
# travel and xT; ratio of specific heats 1.3.
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
    "PV-329203", 4870.0, _l_series(4870.0, _PV_329203_CASES, 150, 250), "gas", _PV_329203_CASES, 1,
    _l_series_source(28, 27, 150, 250))

#: PV-329212, 324E003's 9-bar steam: DN 80 balanced Neldisc (S-L-ANSI150), maximum Cv 150.
#: The five balanced valves take Valmet's S-Disc shape through their printed points (decision 170).
PV_329212 = VendorValve(
    "PV-329212", 150.0, _s_disc(150.0, _PV_329212_CASES, 150), "gas", _PV_329212_CASES, 1,
    _s_disc_source(33, 32, 150))

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
    "FV-329401", 3050.0, _l_series(3050.0, _FV_329401_CASES, 150, 200), "gas", _FV_329401_CASES, 1,
    _l_series_source(25, 24, 150, 200))

#: PV-329202, 323E002's chest: DN 200 Neldisc, maximum Cv 3050 (item 26, rev 00).
PV_329202 = VendorValve(
    "PV-329202", 3050.0, _l_series(3050.0, _PV_329202_CASES, 150, 200), "gas", _PV_329202_CASES, 1,
    _l_series_source(27, 26, 150, 200))

#: PV-329204, superheated MP steam to 329D005: DN 250 balanced Neldisc in a DN 300 line, Cv 1640,
#: FpCv 1604.25 (item 28, rev 00).
PV_329204 = VendorValve(
    "PV-329204", 1604.25, _s_disc(1604.25, _PV_329204_CASES, 300), "gas", _PV_329204_CASES, 1,
    _s_disc_source(29, 28, 300))

#: PV-329207A, the LP header to atmosphere: DN 300 balanced Neldisc, maximum Cv 3880 (item 29,
#: rev 01).
PV_329207A = VendorValve(
    "PV-329207A", 3880.0, _s_disc(3880.0, _PV_329207A_CASES, 150), "gas", _PV_329207A_CASES, 1,
    _s_disc_source(30, 29, 150))

#: PV-329207B: DN 250 balanced Neldisc in a DN 300 line, Cv 2580, FpCv 2447.16 (item 30, rev 00).
PV_329207B = VendorValve(
    "PV-329207B", 2447.16, _s_disc(2447.16, _PV_329207B_CASES, 150), "gas", _PV_329207B_CASES, 1,
    _s_disc_source(31, 30, 150))

#: PV-329208, 323E010's chest: DN 250 balanced Neldisc, maximum Cv 2580 (item 31, rev 00).
PV_329208 = VendorValve(
    "PV-329208", 2580.0, _s_disc(2580.0, _PV_329208_CASES, 150), "gas", _PV_329208_CASES, 1,
    _s_disc_source(32, 31, 150))

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
    "FV-329409", 1240.0, _l_series(1240.0, _FV_329409_CASES, 300, 150), "liquid", _FV_329409_CASES, 1,
    _l_series_source(26, 25, 300, 150))

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
    "HV-323605", 13700.0, _l_series(13700.0, _HV_323605_CASES, 150, 400), "gas", _HV_323605_CASES, 0,
    _l_series_source(20, 19, 150, 400))

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
    "PV-323203", 634.57, _l_series(634.57, _PV_323203_CASES, 150, 125), "gas", _PV_323203_CASES, 0,
    _l_series_source(23, 22, 150, 125))

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
    "PV-323202A", 7300.0, _l_series(7300.0, _PV_323202A_CASES, 150, 300), "liquid", _PV_323202A_CASES, 1,
    _l_series_source(21, 20, 150, 300))
_PV_323202B_CASES = (
    SizingCase(6.0, 3.4, 65.0, 305.8, _TW_65_RHO_KGM3, 217.28, 16.5, fl=0.86),
    SizingCase(5.3, 3.4, 65.0, 917.8, _TW_65_RHO_KGM3, 762.87, 42.4, fl=0.81),
    SizingCase(4.4, 3.4, 65.0, 1233.4, _TW_65_RHO_KGM3, 1413.13, 60.3, fl=0.74))
PV_323202B = VendorValve(
    "PV-323202B", 4870.0, _l_series(4870.0, _PV_323202B_CASES, 150, 250), "liquid", _PV_323202B_CASES, 1,
    _l_series_source(22, 21, 150, 250))

#: TV-328002, 328E004's cooling-water return on TIC-328002: DN 200 Neldisc, maximum Cv 3050 (item
#: 23, page 24): "circulating water" at 38 C, 150 / 410 / 530 m3/h from 2.9 / 2.4 / 2.07 to 2.0 bar a,
#: FL 0.85 / 0.77 / 0.54. No density printed: IAPWS-IF97's saturated liquid at 38 C.
_TV_328002_RHO_KGM3 = rho_liquid_sat_kgm3(38.0)
_TV_328002_CASES = (
    SizingCase(2.9, 2.0, 38.0, 150.0, _TV_328002_RHO_KGM3, 182.24, 21.2, fl=0.85),
    SizingCase(2.4, 2.0, 38.0, 410.0, _TV_328002_RHO_KGM3, 747.18, 55.0, fl=0.77),
    SizingCase(2.07, 2.0, 38.0, 530.0, _TV_328002_RHO_KGM3, 2308.86, 90.5, fl=0.54))
TV_328002 = VendorValve(
    "TV-328002", 3050.0, _l_series(3050.0, _TV_328002_CASES, 150, 200), "liquid", _TV_328002_CASES, 1,
    _l_series_source(24, 23, 150, 200))

#: Metso's valves, by tag.
METSO_VALVES = {v.tag: v for v in (
    PV_329203, PV_329212, FV_329401, PV_329202, PV_329204, PV_329207A, PV_329207B, PV_329208,
    FV_329409, HV_323605, PV_323203, PV_323202A, PV_323202B, TV_328002)}

__all__ = [
    "PV_329203", "PV_329212", "FV_329401", "PV_329202", "PV_329204", "PV_329207A", "PV_329207B",
    "PV_329208", "FV_329409", "HV_323605", "PV_323203", "PV_323202A", "PV_323202B", "TV_328002",
    "METSO_VALVES", "S_DISC_RELATIVE_CV", "L_SERIES_CV",
]
