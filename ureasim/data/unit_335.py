"""Unit 335's design data: the UF85 dosing — FFIC-335406 over FIC-335405 and 335P002A / B — and the
urea melt main header — PIC-335201, the twelve header valves, HV-335602 and 335P001A / B.

What this is for
----------------
The anti-caking additive UF85, a urea-formaldehyde precondensate, is dosed into the urea melt on
its way to the granulator (PFD 697 into 402G, making 609), its flow held in ratio to the melt by
FFIC-335406 trimming FIC-335405, the metering pumps' flow loop (decided 2026-10-16, `project.md`
decision 123: the dosing runs live on LV-324501A's route, where V1 keeps it interlocked).

The PFD's 697 and 402G rows are the granulation section's own design case: 85 405 kg/h of melt is
2 050 t/d, the granulator's 2 000 MTPD (`References/324-1b Equipment Descriprion and Datasheet
3.md`, its introduction), not the urea plant's 1 750. At the plant's design drain, 75 938 kg/h
(V1's reconciled 402), the PFD's ratio doses 617.1 kg/h — the operating manual's 625 kg/h
(`References/Urea_Operating_Manual_Helwan.md` §2.6) — so FIC-335405 is seeded there and the
design holds; the pumps' stroke law stays anchored on the PFD's 694 kg/h at V1's 50 %.

Source: `References/Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md` (streams 402G, 609,
697); V1 ``backend/main.py`` 3404-3411 (the rows, the ratio, the 50 % stroke) and ``State.__init__``
6803-6814 (the two loops' tunings and limits). Neither loop has a row in the plant DCS's tuning
table (`References/Master_PID_Tuning_Constants.md`); Uhde's functional diagrams for unit 335
(UD-MR-335-FF-0002, read from the scans) draw no other structure for them. FFIC-335406's faceplate
in the plant DCS is a ratio station, and the plant runs it as one (decided 2026-10-28, handoff B-116
(a), `project.md` decision 160); FIC-335405 keeps V1's tuning (handoff Open data gaps).
"""

from __future__ import annotations

import math

from ureasim.core.packet import normalise_solution_mass_fraction as _w_norm
from ureasim.data.control_valves import HV_335602
from ureasim.data.unit_324 import (
    LV_324501_P_DOWN_BARA,
    LV_324501_P_UP_BARA,
    LV_324501_RHO_KGM3,
    P2_DES_KGH,
    PIC_335201_DES_BARG,
)
from ureasim.data.valve_sizing import full_stroke_m3h

#: PFD 402G, the raw melt into unit 335 at the granulation case [kg/h].
PFD_402G_KGH = 85405.0

#: PFD 697, UF85 into the melt [kg/h], its temperature [deg C] and density [kg/m3] (1305 at 40 C,
#: the stream's; 1320 is the tank transmitter's SG calibration, V1's note), and its mass fractions,
#: the PFD's 60 % formaldehyde, 25 % urea, 15 % water.
PFD_697_KGH = 694.0
PFD_697_T_C = 40.0
PFD_697_RHO_KGM3 = 1305.0
W_697 = _w_norm(dict(Urea=25.0, H2O=15.0, HCHO=60.0))

#: The dosing ratio, UF85 per kilogram of melt [-]: the PFD's 697 over 402G (V1 ``R324_UF_RATIO``;
#: the DCS ratios on FQI-335401, the melt's flow).
UF_RATIO_DES = PFD_697_KGH / PFD_402G_KGH

#: The UF85 the ratio doses at the plant's design drain [kg/h], 617.1: FIC-335405's seed.
UF85_DES_KGH = UF_RATIO_DES * P2_DES_KGH

#: FIC-335405's stroke at the PFD's 694 kg/h [%] (V1 ``R324_FIC405_OP_DES``): the metering pumps'
#: delivery is linear in it, V1's ``_fic_flow``, the flow transmitter lagged 5 s.
FIC_335405_OP_DES_PCT = 50.0
FT_335405_TAU_S = 5.0

#: FFIC-335406, the ratio master: V1's tuning on the ratio itself, its output the ratio the slave is
#: asked for, 0 to 0.05 (V1 ``State.FFIC_335406``).
FFIC_335406_KC = 0.5
FFIC_335406_TI_S = 60.0
FFIC_335406_RATIO_HI = 0.05

#: FFIC-335406 on its faceplate in the plant DCS (photograph of 24 October 2026, `References/Gaps
#: Closure/Gaps/20261024_034014.jpg`, "UF/US RATIO CTRL."): a ratio station with no PI of its own,
#: OUT = RAT . MV + BIAS — the UF85 FIC-335405 is asked for [t/h] on the urea solution's flow [t/h]
#: — RAT 0.0000 to 0.0080, OUT 0.00 to 0.80 t/h, BIAS 0.0 (decided 2026-10-28, handoff B-116 (a),
#: decision 26's class). The photograph's RAT, 0.0032 on 89.9 t/h, is that night's setting; the
#: model seeds RAT on its design ratio, 0.008126, which stands 1.6 % above RAT H — the PFD's
#: granulation case doses more than the faceplate lets an operator set — until an operator moves
#: the ratio or the station tracks.
FFIC_335406_RAT_LO = 0.0
FFIC_335406_RAT_HI = 0.0080
FFIC_335406_OUT_LO_TH = 0.0
FFIC_335406_OUT_HI_TH = 0.80

#: FIC-335405, the slave: V1's tuning on its PV in t/h, set point 0 to 1 t/h, output 0 to 100 %
#: (V1 ``State.FIC_335405``).
FIC_335405_KC = 100.0
FIC_335405_TI_S = 15.0
FIC_335405_SP_HI_TH = 1.0

# ======================================================================================
# The urea melt main header, 80-US12-335114 (decided 2026-11-14, decision 224)
# ======================================================================================

#: The header valves: twelve DN25 three-way valves, each feeding two of the granulator's 24
#: injection headers (P&ID 130, UD-VT-335-FB-0004, "12x2 HEADERS"; Operating Manual III pages 1-92
#: to 1-94), and the count online at the design seed, ten: on the plant's coefficient ten valves pass
#: the design drain at 3.5 bar g, and the 7 November 2026 live row ran ten at 63.5 m3/h (As-Built
#: §CXVI.5; the process engineer's seed, 2026-11-14).
HEADER_VALVES_MAX = 12
HEADER_VALVES_DES = 10

#: The design header [bar g] (V1's approved G12 datum, ``unit_324.PIC_335201_DES_BARG``) and the
#: design melt in it, PFD 402 at the loop summary's 1221 kg/m3 [m3/h], 62.19.
HEADER_P_DES_BARG = PIC_335201_DES_BARG
HEADER_Q_DES_M3H = P2_DES_KGH / LV_324501_RHO_KGM3

#: PT-335201, the header's transmitter: 0 to 4 bar g (UD-MR-335-EC-0001 rev 01, P 335201, PDF page
#: 159, read on the image).
PT_335201_SPAN_BAR = 4.0

#: PIC-335201 on the DCS tuning table's row (`References/Master_PID_Tuning_Constants.md`: 0.65,
#: 40.0 s, TD 0.0 s, DZ 2.0 %), the gain per cent of PT-335201's span (decisions 10 and 21): 0.65 x
#: 100 / 4 = 16.25 % per bar. Reverse acting (AC4 PC35.2, PIDCON65, REVACT 1): a header above its set
#: point closes LV-324501A. The table's 2 % deadband is not modelled (decision 93's class).
PIC_335201_KC = 0.65 * 100.0 / PT_335201_SPAN_BAR
PIC_335201_TI_S = 40.0
PIC_335201_TD_S = 0.0
PIC_335201_DZ_BAR = 0.0

#: AC4 PC35.2.2 (UD-MR-G00-FF-0004, 02-Mar-2008, PDF pages 249 to 252): LIC-324501's output X feeds
#: two FUNG-1V characterisers on one X table. Element .3's Y table, then .9 (divide by 100) and .10
#: (add 2.8), give PIC-335201's external set point, E1 = 2.8 + min(X / 50, 1) bar g; element .6's
#: gives LV-324501B's stroke, 2 (X - 50) on X 50 to 100. The application software is the
#: as-configured value; the functional diagram UD-MR-324-FF-0002 draws 0.8 in place of 2.8
#: (As-Built §CXX.4).
PC35_XTAB = (0.0, 50.0, 100.0, 100.0)
PC35_E1_YTAB = (0.0, 100.0, 100.0, 100.0)
PC35_E1_DIVISOR = 100.0
PC35_E1_BIAS_BARG = 2.8
PC35_LVB_YTAB = (0.0, 0.0, 100.0, 100.0)

#: LIC-324501's output at the design seed [%]: the X at which E1 is the design header,
#: (3.5 - 2.8) x 50 = 35.0 (`units.finishing.melt_header` checks E1(X) == 3.5 to the bit at import).
LIC_324501_X_DES_PCT = round((HEADER_P_DES_BARG - PC35_E1_BIAS_BARG) * PC35_XTAB[1]
                             * PC35_E1_DIVISOR / PC35_E1_YTAB[1], 9)

#: 335P001A / B, the melt pumps (KSB, UD-AU-335-EC-0039): the head curve as read on the scanned
#: datasheet, H = H0 - c (Q / Q_ref)^2 [m, m3/h] — shut-off about 71 m, the duty marker about 80 m3/h
#: and 65 m on the middle of the three curves; the impeller legend is unreadable (As-Built §CXIX.4;
#: open data gap). Only the curve's droop enters the header: LV-324501A's inlet is the design's, the
#: loop summary's 3.2 bar differential on the 3.5 bar g header, moved by the head the flow costs.
P001_H0_M = 71.0
P001_DROOP_M = 5.0
P001_Q_REF_M3H = 80.0
LV_324501A_DP_DES_BAR = LV_324501_P_UP_BARA - LV_324501_P_DOWN_BARA

#: HV-335602 on Flowserve's Pos. 150 (``control_valves.HV_335602``): its downstream pressure [bar a]
#: and differential [bar] on its one case, and what it passes wide open across that differential at
#: the melt's density [kg/h], m = Kv sqrt(rho dP) moved from the sheet's SG 0.751 to 1221 kg/m3 as
#: LV-324501B's capacity is (``unit_324.LV_324501B_FULL_KGH``). Its stroke times [s]: "Fast Open
#: 3 sec., Slow Close 25 sec." (UD-MR-335-EC-0001, H 335602, pages 79 and 80; the sheet's Herion
#: regulating valve for slow closing).
HV_335602_P_DOWN_BARA = HV_335602.normal_case.p2_bara
HV_335602_DP_CASE_BAR = HV_335602.normal_case.p1_bara - HV_335602.normal_case.p2_bara
HV_335602_FULL_KGH = full_stroke_m3h(HV_335602) * math.sqrt(
    HV_335602.normal_case.rho * LV_324501_RHO_KGM3)
HV_335602_OPEN_S = 3.0
HV_335602_CLOSE_S = 25.0

#: HIC-335602's seed [%]: shut, as the 5 November 2026 trends hold it in every steady window from
#: 13:36 (DCS legend, Group D, As-Built §CXVI.5).
HIC_335602_DES_PCT = 0.0

__all__ = [
    "HEADER_VALVES_MAX", "HEADER_VALVES_DES", "HEADER_P_DES_BARG", "HEADER_Q_DES_M3H",
    "PT_335201_SPAN_BAR", "PIC_335201_KC", "PIC_335201_TI_S", "PIC_335201_TD_S",
    "PIC_335201_DZ_BAR", "PC35_XTAB", "PC35_E1_YTAB", "PC35_E1_DIVISOR", "PC35_E1_BIAS_BARG",
    "PC35_LVB_YTAB", "LIC_324501_X_DES_PCT", "P001_H0_M", "P001_DROOP_M", "P001_Q_REF_M3H",
    "LV_324501A_DP_DES_BAR", "HV_335602_P_DOWN_BARA", "HV_335602_DP_CASE_BAR",
    "HV_335602_FULL_KGH", "HV_335602_OPEN_S", "HV_335602_CLOSE_S", "HIC_335602_DES_PCT",
    "PFD_402G_KGH", "PFD_697_KGH", "PFD_697_T_C", "PFD_697_RHO_KGM3", "W_697", "UF_RATIO_DES",
    "UF85_DES_KGH", "FIC_335405_OP_DES_PCT", "FT_335405_TAU_S", "FFIC_335406_KC",
    "FFIC_335406_TI_S", "FFIC_335406_RATIO_HI", "FFIC_335406_RAT_LO", "FFIC_335406_RAT_HI",
    "FFIC_335406_OUT_LO_TH", "FFIC_335406_OUT_HI_TH", "FIC_335405_KC", "FIC_335405_TI_S",
    "FIC_335405_SP_HI_TH",
]
