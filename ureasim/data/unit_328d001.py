"""328D001 and 328E004 — the reflux drum and the reflux condenser: the design basis.

328C002's overhead, 737, is condensed in 328E004, a vertical U-tube exchanger on cooling water,
together with the lean carbamate 718A that 323P008 sends from 323D011 to absorb it, and falls into
328D001, the level tank. What does not condense leaves the drum's top as 786, through PV-328202,
to 323E011, the LP flash condenser; the liquid, lean carbamate, is drawn by 328P002 A/B (774) and
split: 775 back to 328C002 as its reflux on FIC-328404, 776 forward to 323E003, the LP carbamate
condenser, on LV-328501. FV-328405's spare ammonia water, 793, joins 737 ahead of 328E004.

    737 (117 C) + 718A (45 C) + 793 --> 328E004 --> 328D001 (61 C, 2.6 bar a) --786--> PV-328202 --> 323E011
                                                         \\--774--> 328P002 --775--> FV-328404 --> 328C002
                                                                           \\--776--> LV-328501 --> 323E003

    737 + 718A = 786 + 775 + 776:    6665 + 3561.5 = 276 + 1675 + 8275.5 kg/h

Sources
-------
* ``Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md`` — PFD 737, 718A, 774, 775, 776 and
  786 (PFD-22), 786's composition (93.08 / 6.31 / 0.61 wt% NH3 / H2O / CO2) and 776's 1095 kg/m3
  at 61 C; 737's 46.21 mol% water at 117 C and 3.5 bar a.
* ``References/328E004 328D001 328P002 Datasheets.md`` — 328D001, 1684 mm inside and 1950 mm
  tangent to tangent; 328E004's 4357 kW, 212 m2 on 300 U-tubes, cooling water 30 -> 38 C.
* The vendor's as-built assembly drawing UD-AU-328-DZ-0006-003 rev 02 (the vendor archive,
  scanned, read from the page image): outside diameter 1700 mm on an 8 mm shell, 1950 mm tangent
  to tangent; LT-328501's taps N6A / N6B 220 mm inside each tangent line; LLL / NLL / HLL 300 /
  850 / 1400 mm above the bottom tangent; nominal volume 5500 l with the heads, DIN 28013 heads
  (handoff B-53, decided 2026-09-30).
* ``References/Master_PID_Tuning_Constants.md`` — LIC-328501 "328D001,ACA" 1.00 / 300 s;
  PIC-328202 "328D001 GAS OUTLET" 2.50 / 200 s; TIC-328002 "LIQU.OUT REFLUX COND" 3.00 / 500 s.
  FIC-328404 and TIC-328008 have no row.
* Uhde loop summary UD-MR-328-EC-0001 rev 1 (the vendor archive, scanned, read from the page
  images): P 328202 on 328C002 (line 100-AW4-328066, 3.5 bar a), range 0-10 bar g, its PV-328202
  on sheet 103/2; T 328002 on 328P002's suction, 61 C, range 0-160 C; L 328501, a DP cell on
  taps 1510 mm apart, 1095 kg/m3; F 328404, 0.9 / 1.6 / 2.5 m3/h, range 0-5 m3/h, 1077 kg/m3;
  T 328008 (TI, TIC, TY) at 328C002's gas outlet, 117 C, range 0-160 C.
* Uhde P&ID sheet 103/2 (``References/Merged_Searchable_PIDs.pdf``, page 5): PIC-328202's signal
  from sheet 104 onto PV-328202 on the drum's vent; LIC-328501 on LV-328501 in the line to
  323E003; TIC-328002's TV-328002 on the cooling-water return.
* Flowserve's calculation sheets for LV-328501, FV-328404 and PV-328202
  (`ureasim.data.control_valves`).
* V1 ``backend/main.py``: the 328D001 block (1571-1646), RHO_775_KGM3 (5974), the offgas anchor
  (2065-2068), and the seeds in ``State.__init__`` (6840-6847, 6993-7025, 7066-7081). Each value
  carries its provenance.
"""

from __future__ import annotations

import math

from ureasim.core.stream import MW_COMP
from ureasim.data.control_valves import FV_328404, LV_328501, PV_328202, design_stroke_pct
from ureasim.data.desorption_train import (
    C002_M737_DES_KGH,
    C002_M775_DES_KGH,
    C002_P_TOP_BARA,
    C002_T_TOP_C,
    CP_DESORPTION,
    D001_T_C,
)
from ureasim.data.relief_devices import (
    GAS_KD_ASSUMED,
    RELIEF_DEVICES,
    RELIEF_SIZING,
    gas_reseat_bara,
)
from ureasim.data.unit_323e011 import E011_M786_DES_KGH, E011_P_BARA, M718A_DES_KGH
from ureasim.thermo import iapws

# ======================================================================================
# The streams at design [kg/h]
# ======================================================================================

#: The drum's two inlets: 737, 328C002's overhead, and 718A, the lean carbamate from 323D011.
D001_M737_DES_KGH = C002_M737_DES_KGH
D001_M718A_DES_KGH = M718A_DES_KGH
D001_IN_DES_KGH = D001_M737_DES_KGH + D001_M718A_DES_KGH

#: 786, the vent through PV-328202 to 323E011 — PFD 786, 276.
D001_M786_DES_KGH = E011_M786_DES_KGH

#: 775, the reflux to 328C002 on FIC-328404 — PFD 775, 1675 — and its volume flow [m3/h], the
#: PFD's 1.5, which V1 publishes as FIC-328404's read-only anchor.
D001_M775_DES_KGH = C002_M775_DES_KGH
S775_VOL_DES_M3H = 1.5

#: 776, forward to 323E003 on LV-328501, closing the drum: 8275.5 (PFD 8275). V1 writes it as the
#: remainder, in this operand order.
D001_M776_DES_KGH = D001_IN_DES_KGH - D001_M786_DES_KGH - D001_M775_DES_KGH

#: 774, 328P002's discharge, 775 + 776: 9950.5 (PFD 9950).
D001_M774_DES_KGH = D001_M775_DES_KGH + D001_M776_DES_KGH

#: The lean carbamate's density [kg/m3]: PFD 776 at 61 C (V1 `R328_D001_M776_RHO`), and 775's,
#: the same liquid (V1 `RHO_775_KGM3`).
D001_RHO_KGM3 = 1095.0
RHO_775_KGM3 = 1095.0

#: 718A's temperature [deg C]: 323D011's, V1's literal.
D001_T718A_C = 45.0

# ======================================================================================
# The vessel
# ======================================================================================

#: Inside diameter and tangent-to-tangent cylinder [m], the cross-section [m2], 2.2270, and the
#: cylinder's volume [m3], 4.3435 — the datasheet's and the as-built drawing's. (The datasheet's
#: "19 cubic meters" is out by 4.4 times on its own two dimensions; V1 report A-6.)
D001_ID_M = 1.684
D001_TT_M = 1.950
D001_AREA_M2 = math.pi * 0.25 * D001_ID_M ** 2
D001_VOL_CYL_M3 = math.pi * 0.25 * D001_ID_M ** 2 * D001_TT_M

#: The vessel's volume, heads included [m3]: the as-built drawing's nominal 5500 l (Reuther for
#: Uhde, UD-AU-328-DZ-0006-003 rev 02; weight full of water 7115 kg, empty 1615). Decided
#: 2026-09-30 (handoff B-53): V1 takes the cylinder alone, 4.3435. Each DIN 28013 head holds half
#: the difference, 0.5784, below its tangent line.
D001_VOL_M3 = 5.5
D001_HEAD_VOL_M3 = 0.5 * (D001_VOL_M3 - D001_VOL_CYL_M3)

#: LT-328501, a DP cell across N6B and N6A (the drawing; Uhde's loop summary, loop L 328501): its
#: lower tap 220 mm above the bottom tangent line, its span the 1510 mm between the taps [m].
#: Decided 2026-09-30 (handoff B-53): LI-328501 reads the liquid between the taps, where V1 reads
#: M / M_des x 50.5 on the cylinder.
LT_328501_TAP_LO_M = 0.220
LT_328501_SPAN_M = 1.510

#: LIC-328501's set point [%] (V1), and the design holdup [kg], 3029.7: the liquid that reads it
#: on the taps — the bottom head full and 982.6 mm of the cylinder above its tangent. (V1's,
#: 2401.7, is 50.5 % of the cylinder alone.) The drawing's normal level, 850 mm, reads 41.7 %.
D001_LEVEL_DES_PCT = 50.5
D001_H_DES_M = LT_328501_TAP_LO_M + D001_LEVEL_DES_PCT / 100.0 * LT_328501_SPAN_M
D001_M_DES_KG = (D001_HEAD_VOL_M3 + D001_H_DES_M * D001_AREA_M2) * D001_RHO_KGM3

#: The liquid the vessel holds when full [kg], 6022.5. V1's cylinder holds 4755.8.
D001_FULL_KG = D001_VOL_M3 * D001_RHO_KGM3

#: Floor on the holdup [kg]: V1's ``max(..., 1.0)``.
D001_M_FLOOR_KG = 1.0

# ======================================================================================
# The vent: 786 through PV-328202 to 323E011
# ======================================================================================

#: 786's composition [mass fraction] (PFD) and molar mass [kg/kmol]. The vent has no live
#: composition state; the vector is carried for the head space's molar accumulation (V1).
W786_DES = {"NH3": 0.9308, "H2O": 0.0631, "CO2": 0.0061}
MW786_DES = 1.0 / sum(W786_DES[k] / MW_COMP[k] for k in W786_DES)

#: The vent's outlet at design [bar a]: 323E011's design pressure, 1.13, the anchor of the vent's
#: law. V1 discharges the vent against this constant; the port against 323E011's live pressure
#: (decided 2026-09-30, decision 29).
PV202_P2_BARA = E011_P_BARA

#: PV-328202 as V1 strokes it: linear from 50 %, on the IEC default xT.
PV202_OP_DES_PCT_V1 = 50.0

#: PV-328202 on its vendor trim (decision 23): Flowserve's modified equal percentage, Kvs 25,
#: from the stroke at which its rated capacity passes the design 786 on the normal case, 60.4 %
#: (the sheet sizes 362 Nm3/h at 61 %), on that case's xT, 0.7743.
PV202_CHAR = PV_328202.characteristic
PV202_OP_DES_PCT = design_stroke_pct(PV_328202, D001_M786_DES_KGH)
PV202_XT = PV_328202.normal_case.xt

# ======================================================================================
# 328E004: the condenser's duty and the drum's energy anchor
# ======================================================================================

#: 328E004's design duty [kW] (datasheet) and TV-328002's design stroke [%] (V1). V1's duty is
#: stroke-proportional, Q = Q_des . op / 50, not a UA on the cooling water.
E004_Q_DES_KW = 4357.0
E004_TV_OP_DES_PCT = 50.0

#: The cooling water [deg C]: supply 30 (PFD 1028), return 38 at design (PFD 1029), and the
#: display ceiling V1 clamps TT-329007 at (the 2.2 bar a return flashes near it). The supply is
#: also the coldest 328E004 can make the drum (decided 2026-09-30, decision 28).
E004_CW_T_IN_C = 30.0
E004_CW_T_OUT_DES_C = 38.0
E004_CW_T_MAX_C = 110.0

#: The drum's design sensible load [kW]: 737 from 328C002's 117 C top and 718A from 45 C onto
#: the drum's 61 C, on the train's 4.0 kJ/kg.K (V1 `R328_D001_SENS`).
D001_SENS_DES_KW = ((D001_M737_DES_KGH * (C002_T_TOP_C - D001_T_C)
                     + D001_M718A_DES_KGH * (D001_T718A_C - D001_T_C))
                    / 3600.0 * CP_DESORPTION)

#: What 737 releases condensing in 328E004 [kJ/kg], ~2163.55, back-solved so the design duty closes
#: the drum at 61 C. 328C002 boils 737 at an implied ~1879: V1's AUDIT C4 ascribes the 526 kW
#: between the two to carbamate forming in the drum — condensation plus formation, rightly larger
#: than a boil-up latent. Ported as V1 anchors it.
D001_LAM737_KJKG = (E004_Q_DES_KW - D001_SENS_DES_KW) / (D001_M737_DES_KGH / 3600.0)

#: Floor on 328E004's condensation factor, Q / Q_des, below which the uncondensed vent stops
#: growing (V1's ``max(..., 0.1)``).
E004_COND_FLOOR = 0.1

# ======================================================================================
# TIC-328008: the inferential water content of 737, and the reflux it asks
# ======================================================================================

#: 737's design water content [mol%], PFD 46.21 at 117 C and 3.5 bar a, and the activity
#: coefficient back-solved to it on water's saturation pressure, 0.8960 on IAPWS-IF97 (V1's
#: comment gives 0.898328, a value of its retired Antoine curve; the design content is exact).
C002_OFFGAS_H2O_PFD_MOLPCT = 46.21
C002_OFFGAS_PHI = ((C002_OFFGAS_H2O_PFD_MOLPCT / 100.0) * C002_P_TOP_BARA
                   / iapws.psat_bara(C002_T_TOP_C))
C002_OFFGAS_H2O_DES_MOLPCT = (100.0 * C002_OFFGAS_PHI * iapws.psat_bara(C002_T_TOP_C)
                              / C002_P_TOP_BARA)

#: The column top's temperature floor on the reflux [K]: V1 moves the top-to-bottom offset from 10
#: K (no reflux) to the design 22 K (the design reflux), on the reflux lagged over 328C002's
#: residence.
C002_DT_TOP_NO_REFLUX_K = 10.0

#: TIC-328008 (V1's own tuning; the table has no row): 240 kg/h of reflux per mol%, 110 s, DIRECT;
#: set point 25-65 mol%, output 0-4000 kg/h — FIC-328404's set point in mass.
TIC_328008_KC = 240.0
TIC_328008_TI_S = 110.0
TIC_328008_SP_LO = 25.0
TIC_328008_SP_HI = 65.0
TIC_328008_OP_HI_KGH = 4000.0

# ======================================================================================
# The loops
# ======================================================================================

#: LIC-328501: DIRECT acting on the level; the table's 1.00 (a level is per cent of span
#: already), 300 s, Td -1 (the DCS sentinel).
LIC_328501_KC = 1.0
LIC_328501_TI_S = 300.0
LIC_328501_TD_S = -1.0

#: LV-328501 as V1 strokes it — a pure gain, 776 = 776_des . op / 50 — and on its vendor trim
#: (decision 23): Flowserve's linear, Kvs 16, from the stroke at which its rated capacity passes
#: the design 776 on the normal case, 29.4 % (the sheet sizes 10.95 m3/h at 44 %).
LV501_OP_DES_PCT_V1 = 50.0
LV501_CHAR = LV_328501.characteristic
LV501_OP_DES_PCT = design_stroke_pct(LV_328501, D001_M776_DES_KGH)

#: PT-328202's calibrated span [bar] and PIC-328202 on the table's gain per cent of it (decision
#: 10): 2.5 x 100 / 10 = 25 %/bar. V1 applies 2.5 per bar. 200 s; DIRECT; set point 2.5-5.0
#: bar a. The transmitter is on 328C002 (the loop summary, and V1 AUDIT B5).
PT_328202_SPAN_BAR = 10.0
PIC_328202_KC_TABLE = 2.5
PIC_328202_KC = PIC_328202_KC_TABLE * 100.0 / PT_328202_SPAN_BAR
PIC_328202_TI_S = 200.0
PIC_328202_SP_LO_BARA = 2.5
PIC_328202_SP_HI_BARA = 5.0

#: TT-328002's calibrated span [K] and TIC-328002 on the table's gain per cent of it (decision
#: 10): 3.0 x 100 / 160 = 1.875 %/K. V1 applies 3.0 per K. 500 s; DIRECT (more cooling as the
#: drum warms); set point 45-80 C.
TT_328002_SPAN_K = 160.0
TIC_328002_KC_TABLE = 3.0
TIC_328002_KC = TIC_328002_KC_TABLE * 100.0 / TT_328002_SPAN_K
TIC_328002_TI_S = 500.0
TIC_328002_SP_LO_C = 45.0
TIC_328002_SP_HI_C = 80.0

#: FIC-328404, 775: a VOLUMETRIC loop in CAS under TIC-328008, on V1's own tuning (the table has
#: no row) — 0.5 per kg/h carried to m3/h by the density, 25 s — its set point to V1's 4000 kg/h.
#: FT-328404's span is 0-5 m3/h (the loop summary).
FIC_328404_KC = 0.5 * RHO_775_KGM3
FIC_328404_TI_S = 25.0
FIC_328404_SP_HI_M3H = 4000.0 / RHO_775_KGM3
FT_328404_SPAN_M3H = 5.0
FT_328404_TAU_S = 5.0

#: FV-328404 as V1 strokes it — linear from 30.2 % — and on its vendor trim (decision 23):
#: Flowserve's modified equal percentage, Kvs 10, from the stroke at which its rated capacity
#: passes the design 775 on the normal case, 56.7 % (the sheet sizes 1.6 m3/h at 58 %).
FV404_OP_DES_PCT_V1 = 30.2
FV404_CHAR = FV_328404.characteristic
FV404_OP_DES_PCT = design_stroke_pct(FV_328404, D001_M775_DES_KGH)

# ======================================================================================
# SV32353, the drum's relief (decided 2026-10-01, handoff A-16)
# ======================================================================================

#: SV32353 on 328D001's nozzle N2, line ACA4-323207-EG07D (P&ID 103/2): set 5.0 bar g, 6.01 bar a,
#: on the sheet's 1.010 bar a (Uhde UD-RL-323-EC-0003, sized on LV-323503 failing open). Sized on
#: liquid, it relieves the drum's vapour here, so it reseats on the gas blowdown, 10 % of set
#: below, at 5.51 bar a.
SV32353_SET_BARA = RELIEF_DEVICES["SV32353"].set_bara
SV32353_RESEAT_BARA = gas_reseat_bara(RELIEF_DEVICES["SV32353"])

#: Its orifice K, 1462.20 mm2 [m2] (Sempell UD-RL-G00-DZ-0001-001 page 90, rated on liquid at
#: alpha_w 0.644), and the gas coefficient taken for it, 0.917 — an assumption (A-16, option b).
SV32353_AREA_M2 = RELIEF_SIZING["SV32353"].area_mm2 * 1.0e-6
SV32353_KD = GAS_KD_ASSUMED

__all__ = [
    "D001_M737_DES_KGH", "D001_M718A_DES_KGH", "D001_IN_DES_KGH", "D001_M786_DES_KGH",
    "D001_M775_DES_KGH", "S775_VOL_DES_M3H", "D001_M776_DES_KGH", "D001_M774_DES_KGH",
    "D001_RHO_KGM3", "RHO_775_KGM3", "D001_T718A_C", "D001_ID_M", "D001_TT_M", "D001_AREA_M2",
    "D001_VOL_CYL_M3", "D001_VOL_M3", "D001_HEAD_VOL_M3", "LT_328501_TAP_LO_M", "LT_328501_SPAN_M",
    "D001_LEVEL_DES_PCT", "D001_H_DES_M", "D001_M_DES_KG", "D001_FULL_KG", "D001_M_FLOOR_KG",
    "W786_DES", "MW786_DES", "PV202_P2_BARA", "PV202_OP_DES_PCT_V1", "PV202_CHAR",
    "PV202_OP_DES_PCT", "PV202_XT", "E004_Q_DES_KW", "E004_TV_OP_DES_PCT", "E004_CW_T_IN_C",
    "E004_CW_T_OUT_DES_C", "E004_CW_T_MAX_C", "D001_SENS_DES_KW", "D001_LAM737_KJKG",
    "E004_COND_FLOOR", "C002_OFFGAS_H2O_PFD_MOLPCT", "C002_OFFGAS_PHI",
    "C002_OFFGAS_H2O_DES_MOLPCT", "C002_DT_TOP_NO_REFLUX_K", "TIC_328008_KC", "TIC_328008_TI_S",
    "TIC_328008_SP_LO", "TIC_328008_SP_HI", "TIC_328008_OP_HI_KGH", "LIC_328501_KC",
    "LIC_328501_TI_S", "LIC_328501_TD_S", "LV501_OP_DES_PCT_V1", "LV501_CHAR", "LV501_OP_DES_PCT",
    "PT_328202_SPAN_BAR", "PIC_328202_KC_TABLE", "PIC_328202_KC", "PIC_328202_TI_S",
    "PIC_328202_SP_LO_BARA", "PIC_328202_SP_HI_BARA", "TT_328002_SPAN_K", "TIC_328002_KC_TABLE",
    "TIC_328002_KC", "TIC_328002_TI_S", "TIC_328002_SP_LO_C", "TIC_328002_SP_HI_C",
    "FIC_328404_KC", "FIC_328404_TI_S", "FIC_328404_SP_HI_M3H", "FT_328404_SPAN_M3H",
    "FT_328404_TAU_S", "FV404_OP_DES_PCT_V1", "FV404_CHAR", "FV404_OP_DES_PCT",
    "SV32353_SET_BARA", "SV32353_RESEAT_BARA", "SV32353_AREA_M2", "SV32353_KD",
]
