"""322C001 — the LP absorber: the design basis.

What this equipment is
----------------------
322C001 is the urea plant's last ammonia barrier before atmosphere. HV-322604 lets the HP
scrubber's inert vent (PFD 204: nitrogen, oxygen, methane and hydrogen with 8 mol % of ammonia
and 2 % of carbon dioxide) down into it at 3.9 bar a. It is a stepped packed column: a lower bed
in the 922 mm section washed by ammonia water from 328D003's compartment I — 744 through 322P002
and the 322E006 plate cooler, arriving as PFD 755 at 40 C — and an upper bed in the 576 mm section
washed by steam condensate, PFD 954, metered on FT-322404. The washed inerts leave the top through
PV-322201 to atmosphere (PFD 797); the liquor collects in the sump and leaves under LIC-322502
through LV-322502 to 323C005, the atmospheric absorber (PFD 756).

    204 (HV-322604) --gas--> lower bed --> upper bed --> PV-322201 (797) --> atmosphere
    755 (322E006) --wash--^      954 (FT-322404) --wash--^
    sump --LV-322502 (756)--> 323C005

    PIC-322201 (the column)     ->  PV-322201
    LIC-322502 (the sump)       ->  LV-322502

The column has no cooling of its own: the heat of absorption leaves in the liquor, and what
holds the liquor cool is 755's temperature — V1 fixes it at 322E006's 40 C outlet; the rewrite
takes it from 322E006 itself (`ureasim.data.unit_322e006`, handoff B-54).

Sources
-------
* ``Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md`` — streams 204, 755, 756, 797 and
  954 (V1's anchors, provenance kept per value).
* ``References/322P002 322E006 322C001 Datasheets.md`` — the stepped shell, the beds, the
  packing, the nozzles.
* Uhde, 322C001 arrangement drawing UD-AU-322-DZ-0007-001 rev 02 (the vendor archive, scanned,
  read from the page image): the name plate's volume, 3.60 m3; LT-322502's taps N9B and N9A,
  200 and 1000 mm above the bottom tangent line; the formed heads, DIN 28013, crown R 760.
* Uhde loop summaries for unit 322, UD-MR-322-EC-0001 rev 1 (scanned): loop P 322201, sheet 1/2,
  line D07, PT-322201 0 to 28 bar g; loop L 322502, sheet 1/2, line B44, the taps 800 mm apart.
* ``References/Master_PID_Tuning_Constants.md`` — PIC-322201, LIC-322502.
* Flowserve's sizing of LV-322502 and PV-322201 (`ureasim.data.control_valves`); Uhde's and
  Sempell's sheets for SV32253 (`ureasim.data.relief_devices`).
* V1 ``backend/main.py``, the "322C001 LP absorber" block (1648-1735), the species layer
  (2983-3021), the seeds in ``State.__init__`` (6869-6875, 7129-7148); V1
  ``backend/packed_absorber.py`` for the beds and the packing.
"""

from __future__ import annotations

import math

from ureasim.core.packet import normalise_solution_mass_fraction as _w_norm
from ureasim.core.stream import MW_COMP
from ureasim.data.control_valves import LV_322502, PV_322201, design_stroke_pct
from ureasim.data.relief_devices import (
    GAS_KD_ASSUMED,
    RELIEF_DEVICES,
    RELIEF_SIZING,
    gas_reseat_bara,
)
from ureasim.data.unit_322e003 import OFFGAS_DES_KGH
from ureasim.data.unit_323c005 import C005_M756_DES_KGH
from ureasim.data.unit_329 import FO_322457_KGH, FO_329458_KGH, FO_329459_KGH
from ureasim.thermo.urea_liquor import SOLUTION_SPECIES

# ======================================================================================
# The streams at design
# ======================================================================================

#: PFD 755, the ammonia water from 328D003's compartment I through 322P002 and 322E006 [kg/h],
#: 31478, and its density at 40 C [kg/m3], 1005 (PFD-20 col 755; FT-322402's 31.3 m3/h).
C001_M755_DES_KGH = 31478.0
C001_RHO_755_KGM3 = 1005.0

#: PFD 756, the liquor drawn to 323C005 [kg/h], 33358.
C001_M756_DES_KGH = C005_M756_DES_KGH

#: PFD 954, the steam condensate on FT-322404 [kg/h], and its temperature [deg C]: 1750 at 46 C.
C001_CPL_DES_KGH = 1750.0
C001_T_CPL_C = 46.0

#: What the column takes up at design [kg/h]: 130, the mass closure 756 - 755 - 954 (V1).
C001_ABS_DES_KGH = C001_M756_DES_KGH - C001_M755_DES_KGH - C001_CPL_DES_KGH

#: The design liquor temperature, 755's (322E006's outlet) [deg C], and the column pressure
#: [bar a]: 43, 40 and 3.9 (PFD 756, 755; PT-322201's normal 2.9 bar g).
C001_T_C = 43.0
C001_T_755_C = 40.0
C001_P_BARA = 3.9

#: PFD 755 and 954 as mass fractions: 755 CO2 3.81, H2O 91.13, NH3 4.17, urea 0.89 mass %
#: (PFD-20 col 755); 954 pure water.
W_S755 = _w_norm(dict(CO2=3.81, H2O=91.13, NH3=4.17, Urea=0.89))
W_CPL = _w_norm(dict(H2O=100.0))

#: The design uptake per species [kg/h], split by the column's own two vapour rows: PFD 204, the
#: gas it receives (64.78 kmol/h; NH3 8.26, CO2 2.22, H2O 0.26 mol %), less PFD 797, the gas it
#: releases (59.32 kmol/h; 0.18, 0.05, 2.28). The gas gives up NH3 and CO2 and picks up water
#: from the wash; normalised to the 130 kg/h closure: NH3 89.33, CO2 62.00, H2O -21.34 (V1).
_Y204_MOLPCT = {"NH3": 8.26, "CO2": 2.22, "H2O": 0.26}
_Y797_MOLPCT = {"NH3": 0.18, "CO2": 0.05, "H2O": 2.28}
_ABS_KGH = {k: (64.78 * _Y204_MOLPCT[k] - 59.32 * _Y797_MOLPCT[k]) / 100.0 * MW_COMP[k]
            for k in _Y204_MOLPCT}
C001_ABS_CO2_DES_KGH = C001_ABS_DES_KGH * _ABS_KGH["CO2"] / sum(_ABS_KGH.values())
C001_ABS_H2O_DES_KGH = C001_ABS_DES_KGH * _ABS_KGH["H2O"] / sum(_ABS_KGH.values())
C001_ABS_NH3_DES_KGH = C001_ABS_DES_KGH - C001_ABS_CO2_DES_KGH - C001_ABS_H2O_DES_KGH

#: The relative volatilities the species advance asks for; nothing boils off the liquor, so
#: they multiply a zero vapour (V1).
C001_ALPHA = {k: 1.0 for k in SOLUTION_SPECIES}


def _liquor_anchor() -> dict:
    """The design liquor, PFD 756: the normalised mix of 755, 954 and the uptake. Because the
    three close on 756 in mass, this is the sump's steady state (V1 ``_c001_liq_anchor``)."""
    m = {k: C001_M755_DES_KGH * W_S755.get(k, 0.0) + C001_CPL_DES_KGH * W_CPL.get(k, 0.0)
         for k in SOLUTION_SPECIES}
    m["CO2"] += C001_ABS_CO2_DES_KGH
    m["NH3"] += C001_ABS_NH3_DES_KGH
    m["H2O"] += C001_ABS_H2O_DES_KGH
    tot = sum(m.values())
    return {k: m[k] / tot for k in SOLUTION_SPECIES}


#: The design liquor's mass fractions.
W_C001_DES = _liquor_anchor()

#: The design vent, PFD 797 [kg/h]: what HV-322604 lets down at design less the uptake, 1578.3
#: (V1 ``A328_VENT_DES``, pinned on the same gas: 322E003's design vent, `OFFGAS_DES_KGH`).
C001_VENT_DES_KGH = OFFGAS_DES_KGH - C001_ABS_DES_KGH

#: The liquor's heat capacity [kJ/(kg K)] at the design temperature, V1's ``A328_CP``.
CP_C001 = 4.0

#: XV-322915's steam flood: the valve's rated normal flow [kg/h], and the steam's temperature
#: [deg C] and pressure [bar a] at the valve. Uhde's loop summary X 322915 (UD-MR-322-EC-0001,
#: scanned, read from the page image): 1000 kg/h normal, 1200 maximum, saturated LP steam at
#: 9.0 bar a and 175 C in from line 100-STLS4-329722, 7.8 bar a out. Decided 2026-10-01 (handoff
#: B-60, the Typo Rule): V1 floods with 500 kW of latent heat (``A328_QFLOOD_KW``, no source), 854
#: kg/h at its 5.013 bar a header, and puts it in the liquor; the rewrite puts the steam in the
#: vent line, where P&ID 102 injects it (handoff B-55).
C001_FLOOD_STEAM_KGH = 1000.0
C001_FLOOD_STEAM_T_C = 175.0
C001_FLOOD_STEAM_P_BARA = 9.0

#: The trace steam the vent line takes continuously [kg/h], 60: FO-329458 into the line between
#: 322C001's top nozzle and PV-322201, and FO-322457, XV-322915's DN15 bypass, downstream of it
#: (their ratings and sources at `unit_329`, the header they draw on). Decided by the process
#: engineer 2026-10-07: "Model it ... Do not ignore known mass inflows."
C001_TRACE_STEAM_KGH = FO_329458_KGH + FO_322457_KGH

#: FO-329459's steam into SV32253's discharge line to a safe location [kg/h], 30. P&ID 102 ties it
#: in at the safety valve's outlet, not the vent line, so TI-322015 does not see it; it is drawn
#: from the 9-bar header with the other two.
C001_SV_PURGE_STEAM_KGH = FO_329459_KGH

#: Trip 22.1 [deg C]: TT-322015's high-high limit, 110 C — the plant DCS's H2 on the tag
#: (the process engineer's readback of the plant DCS, 13 October 2026, "TT-322015 HH 110", the handwritten
#: note `Urea Simulation Docs/Data/DCS_Extract_2026-10-13.jpg`; the loop's range is 0-200 C, so the
#: unit is the PV's). AC4's PC22.5.1 reads the limit as TT-322015's H2 flag. V1 sets it above 57 C
#: and clears it below 55 C (``main.py`` 10142-10146, no source; kept under decision 90 until the
#: database's value was found). The flag's hysteresis is still a database entry nobody has read:
#: V1's 2 K band is kept below the plant's limit, cleared below 108 C (handoff Open data gaps). V1
#: reads the liquor; the rewrite reads TI-322015 on the vent line (B-55).
TRIP_22_1_HIGH_C = 110.0
TRIP_22_1_CLEAR_C = 108.0

# ======================================================================================
# The vessel
# ======================================================================================

#: The stepped shell [m]: upper part 576 mm inside over a 1900 mm cylinder, lower part 922 mm over
#: 4150 mm (the datasheet), and the two cylinders' volume [m3], 3.2659 — V1's vessel.
C001_ID_UP_M = 0.576
C001_SHELL_UP_M = 1.900
C001_ID_LO_M = 0.922
C001_SHELL_LO_M = 4.150
C001_VOL_UP_M3 = math.pi * 0.25 * C001_ID_UP_M ** 2 * C001_SHELL_UP_M
C001_VOL_LO_M3 = math.pi * 0.25 * C001_ID_LO_M ** 2 * C001_SHELL_LO_M
C001_VOL_CYL_M3 = C001_VOL_UP_M3 + C001_VOL_LO_M3

#: The liquor's density [kg/m3], PFD 755's (V1).
C001_RHO_KGM3 = C001_RHO_755_KGM3

#: The vessel's volume, heads and cone included [m3]: the name plate's 3.60 (UD-AU-322-DZ-0007-001
#: rev 02). Rule 7 class (decision 33, 2026-09-30): V1 takes the two cylinders alone.
C001_VOL_M3 = 3.60

#: The lower part's cross-section [m2], 0.6677.
C001_AREA_LO_M2 = math.pi * 0.25 * C001_ID_LO_M ** 2

#: The bottom head's proportions, DIN 28013 (the drawing's list of material) on the lower part's
#: 950 mm outside diameter: inside crown radius 0.8 Da (the drawing's R 760) and knuckle radius
#: 0.154 Da [m]. Their dished height, 233.1 mm, is the standard's 0.255 Da - 0.635 s, 233.4 mm.
C001_DA_LO_M = 0.950
C001_HEAD_CROWN_M = 0.8 * C001_DA_LO_M
C001_HEAD_KNUCKLE_M = 0.154 * C001_DA_LO_M


def torispherical_head_volume_m3(d_in_m: float, crown_m: float, knuckle_m: float) -> float:
    """The liquid a torispherical head holds below its tangent line [m3], from its inside
    diameter and its inside crown and knuckle radii.

    Process utility
    ---------------
    The sump's first litres fill the bottom head, below the cylinder; a level read on the
    cylinder alone misplaces every kilogram by the head's volume. Calculated from the drawing's
    dimensions, not printed on it.

    Equation
    --------
    The knuckle (a torus of radius r about the circle of radius c = D/2 - r) meets the crown
    (a sphere of radius R centred on the axis z_c above the tangent line) tangentially:

        z_c = sqrt((R - r)^2 - c^2),   h = R - z_c,   z_j = -r z_c / (R - r)
        V   = pi [ (c^2 + r^2)(-z_j) - c (z_j sqrt(r^2 - z_j^2) + r^2 asin(z_j / r)) + z_j^3/3 ]
            + pi [ R^2 (z_j + h) - ((z_j - z_c)^3 + R^3) / 3 ]
    """
    c = 0.5 * d_in_m - knuckle_m
    z_c = math.sqrt((crown_m - knuckle_m) ** 2 - c ** 2)
    h = crown_m - z_c
    z_j = -knuckle_m * z_c / (crown_m - knuckle_m)
    v_knuckle = ((c ** 2 + knuckle_m ** 2) * (-z_j)
                 - c * (z_j * math.sqrt(knuckle_m ** 2 - z_j ** 2)
                        + knuckle_m ** 2 * math.asin(z_j / knuckle_m))
                 + z_j ** 3 / 3.0)
    v_crown = crown_m ** 2 * (z_j + h) - ((z_j - z_c) ** 3 + crown_m ** 3) / 3.0
    return math.pi * (v_knuckle + v_crown)


#: The bottom head's volume below its tangent line [m3], 0.1029.
C001_HEAD_VOL_M3 = torispherical_head_volume_m3(C001_ID_LO_M, C001_HEAD_CROWN_M,
                                                C001_HEAD_KNUCKLE_M)

#: LT-322502, a DP cell across N9B and N9A (the drawing; the loop summary's 800 mm): its lower
#: tap 200 mm above the bottom tangent line, its span the 800 mm between the taps [m]. Rule 7 class
#: (decision 33): LI-322502 reads the liquid between the taps, where V1 reads M / M_des x 50.
LT_322502_TAP_LO_M = 0.200
LT_322502_SPAN_M = 0.800

#: The liquor at LT-322502's lower tap — the bottom head full and 200 mm of the lower part — and
#: between its taps [kg]: 237.6 and 536.8. Both taps stand on the lower cylinder, so the reading
#: is linear in the liquor between them.
C001_M_TAP_LO_KG = (C001_HEAD_VOL_M3 + LT_322502_TAP_LO_M * C001_AREA_LO_M2) * C001_RHO_KGM3
C001_M_SPAN_KG = LT_322502_SPAN_M * C001_AREA_LO_M2 * C001_RHO_KGM3

#: LIC-322502's set point [%] (the datasheet, the DCS), and the design holdup [kg], 506.0: the
#: liquid that reads it on the taps — the bottom head full and 600 mm of the lower part. V1's,
#: 1392.3, is half the lower cylinder.
C001_LEVEL_DES_PCT = 50.0
C001_M_DES_KG = C001_M_TAP_LO_KG + C001_LEVEL_DES_PCT / 100.0 * C001_M_SPAN_KG
C001_M_DES_KG_V1 = C001_VOL_LO_M3 * (C001_LEVEL_DES_PCT / 100.0) * C001_RHO_KGM3

#: The liquor the column holds when full [kg], 3618. Rule 7 class (decision 11): the excess leaves
#: as a published overflow.
C001_FULL_KG = C001_VOL_M3 * C001_RHO_KGM3

#: Floors: the holdup [kg] and the pressure [bar a], V1's ``max(..., 1.0)`` and ``0.1``.
C001_M_FLOOR_KG = 1.0
C001_P_FLOOR_BARA = 0.1

#: The vent's molar mass when the vent has gone to zero [kg/kmol]: the datasheet's emission
#: figures (N2 75.15, O2 12.44, Ar 9.90, H2O 2.28, NH3 0.18, CO2 0.05 mol %), 29.45 — air.
C001_MW_VENT_DES = 29.45

# ======================================================================================
# The packed beds
# ======================================================================================

#: The packing, 25 mm metal Pall rings (Raflux 25-10): specific surface [m2/m3] and nominal size
#: [m] (Rauschert's packing datasheet, UD-AU-322-DZ-0008-001), and Onda's critical surface tension
#: for steel [N/m].
PACKING_AREA_M2M3 = 250.0
PACKING_SIZE_M = 0.025
PACKING_SIGMA_C_NM = 0.075

#: The two beds [m]: the lower, 1500 mm of packing in the 922 mm part, washed through sprayer N4
#: by 755 and by the 954 leaving the bed above; the upper, 1000 mm in the 576 mm part, washed
#: through N5 by 954 (UD-AU-322-EC-0007, the column datasheet; UD-AU-322-DZ-0007-001).
BED_LO_HEIGHT_M, BED_LO_ID_M = 1.5, C001_ID_LO_M
BED_UP_HEIGHT_M, BED_UP_ID_M = 1.0, C001_ID_UP_M

#: The washes' density [kg/m3] (PFD 755), and the heat capacities the upper bed's warming is taken
#: on [kJ/(kg K)]: the dilute wash's and the nitrogen-rich gas's (V1 ``packed_absorber``).
BED_RHO_LIQ_KGM3 = 1005.0
BED_CP_LIQ = 4.18
BED_CP_GAS = 1.05

# ======================================================================================
# The valves
# ======================================================================================

#: PV-322201's and LV-322502's design strokes in V1 [%]: 67.8 (the DCS) and 50.
PV201_OP_DES_PCT_V1 = 67.8
LV502_OP_DES_PCT_V1 = 50.0

#: PV-322201, Flowserve's modified equal percentage, Kvs 63, from the stroke at which its rated
#: capacity passes the design vent on its normal case, 64.5 %; LV-322502, modified equal
#: percentage, Kvs 100, from 54.5 % on 756. Rule 7 class (decision 23).
PV201_CHAR = PV_322201.characteristic
PV201_OP_DES_PCT = design_stroke_pct(PV_322201, C001_VENT_DES_KGH)
LV502_CHAR = LV_322502.characteristic
LV502_OP_DES_PCT = design_stroke_pct(LV_322502, C001_M756_DES_KGH)

# ======================================================================================
# The controllers
# ======================================================================================

#: PIC-322201: the table's 6.00 per cent of PT-322201's 0-28 bar g span, 21.43 %/bar; V1 applies
#: 6.0 per bar. Rule 7 class (decision 10).
PIC_322201_KC_TABLE = 6.00
PT_322201_SPAN_BAR = 28.0
PIC_322201_KC = PIC_322201_KC_TABLE * 100.0 / PT_322201_SPAN_BAR
PIC_322201_TI_S = 30.0
PIC_322201_SP_LO_BARA = 2.5
PIC_322201_SP_HI_BARA = 5.5

#: LIC-322502 on the level in per cent: the table's 1.00, 100 s.
LIC_322502_KC = 1.00
LIC_322502_TI_S = 100.0

# ======================================================================================
# SV32253, the column's relief (decided 2026-10-01, handoffs B-47, A-16)
# ======================================================================================

#: SV32253 on nozzle N11, line GCB7-322C001-EG13EA (P&ID 102): set 5.0 bar g, 6.013 bar a, on the
#: sheet's 1.013 bar a (Uhde UD-RL-322-EC-0003; Sempell's certificate). Sized on liquid and gas
#: blowing together, rated on the liquid; relieving the column's gas it reseats on the gas
#: blowdown, 10 % of set below, at 5.513 bar a. V1 sets it at the vessel's 30 bar g design
#: pressure, 31.013 bar a, and ramps it linearly to 60 t/h over 10 % accumulation.
SV32253_SET_BARA = RELIEF_DEVICES["SV32253"].set_bara
SV32253_RESEAT_BARA = gas_reseat_bara(RELIEF_DEVICES["SV32253"])

#: Its orifice M, 2827.43 mm2 [m2] (Sempell UD-RL-G00-DZ-0002-001 page 2, rated on liquid at
#: alpha_w 0.644), and the gas coefficient taken for it, 0.917 — an assumption (A-16, option b).
SV32253_AREA_M2 = RELIEF_SIZING["SV32253"].area_mm2 * 1.0e-6
SV32253_KD = GAS_KD_ASSUMED

__all__ = [
    "C001_M755_DES_KGH", "C001_RHO_755_KGM3", "C001_M756_DES_KGH", "C001_CPL_DES_KGH",
    "C001_T_CPL_C", "C001_ABS_DES_KGH", "C001_T_C", "C001_T_755_C", "C001_P_BARA", "W_S755",
    "W_CPL", "C001_ABS_CO2_DES_KGH", "C001_ABS_H2O_DES_KGH", "C001_ABS_NH3_DES_KGH",
    "C001_ALPHA", "W_C001_DES", "C001_VENT_DES_KGH", "CP_C001", "C001_FLOOD_STEAM_KGH",
    "C001_FLOOD_STEAM_T_C", "C001_FLOOD_STEAM_P_BARA", "C001_TRACE_STEAM_KGH",
    "C001_SV_PURGE_STEAM_KGH", "TRIP_22_1_HIGH_C", "TRIP_22_1_CLEAR_C",
    "C001_ID_UP_M", "C001_SHELL_UP_M", "C001_ID_LO_M", "C001_SHELL_LO_M", "C001_VOL_UP_M3",
    "C001_VOL_LO_M3", "C001_VOL_CYL_M3", "C001_RHO_KGM3", "C001_VOL_M3", "C001_AREA_LO_M2",
    "C001_DA_LO_M", "C001_HEAD_CROWN_M", "C001_HEAD_KNUCKLE_M", "torispherical_head_volume_m3",
    "C001_HEAD_VOL_M3", "LT_322502_TAP_LO_M", "LT_322502_SPAN_M", "C001_LEVEL_DES_PCT",
    "C001_M_TAP_LO_KG", "C001_M_SPAN_KG", "C001_M_DES_KG", "C001_M_DES_KG_V1", "C001_FULL_KG",
    "C001_M_FLOOR_KG",
    "C001_P_FLOOR_BARA", "C001_MW_VENT_DES", "PV201_OP_DES_PCT_V1", "LV502_OP_DES_PCT_V1",
    "PV201_CHAR", "PV201_OP_DES_PCT", "LV502_CHAR", "LV502_OP_DES_PCT", "PIC_322201_KC_TABLE",
    "PT_322201_SPAN_BAR", "PIC_322201_KC", "PIC_322201_TI_S", "PIC_322201_SP_LO_BARA",
    "PIC_322201_SP_HI_BARA", "LIC_322502_KC", "LIC_322502_TI_S", "SV32253_SET_BARA",
    "SV32253_RESEAT_BARA", "SV32253_AREA_M2", "SV32253_KD", "PACKING_AREA_M2M3",
    "PACKING_SIZE_M", "PACKING_SIGMA_C_NM", "BED_LO_HEIGHT_M", "BED_LO_ID_M", "BED_UP_HEIGHT_M",
    "BED_UP_ID_M", "BED_RHO_LIQ_KGM3", "BED_CP_LIQ", "BED_CP_GAS",
]
