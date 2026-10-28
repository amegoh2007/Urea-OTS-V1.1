"""328C003 — the hydrolyser, and 328E021, its feed/effluent interchanger: the design basis.

328C003 is a liquid-filled trayed column, 1950 mm across and 20 850 mm of shell, run about 60 %
full at 200 C and 16.8 bar a. It destroys the urea the ammonia water carries — NH2CONH2 + H2O ->
2 NH3 + CO2, endothermic — with MP steam (911) injected at the bottom supplying the heat and
stripping the ammonia and carbon dioxide the reaction makes. 328C002's bottoms arrive as 746
through 328E021's cold side (139 -> 190 C); the hydrolysed liquor leaves the bottom as 747
through LV-328504 and 328E021's hot side (200 -> 148 C) to 328C004; the gas leaves overhead as
748 through PV-328203 to 328C002.

    743 --> LV-328503 --> 328E021 (cold) --746--> 328C003 <--911-- FV-329402 (MP steam)
                                                    |  \\--748--> PV-328203 --> 328C002
                             328C004 <--749-- 328E021 (hot) <--747-- LV-328504

Sources
-------
* ``Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md`` — PFD 746, 747, 748 and 911
  (PFD-22), and 746's 908.5 kg/m3 at 190 C and 14.7 bar a.
* ``References/328P003, 328P006, 328P007, 328C002. 328C003, 328C004, 328E007, 328E001
  Datasheets.md`` — the shell, 1950 mm and 20 850 mm, 21.0 bar g and 230 C design.
* ``References/328E021 328E007 328P003 328P006.md`` — 328E021 A/B, two shells in series.
* ``References/Master_PID_Tuning_Constants.md`` — PIC-328203 "328C003,STMH" 1.50 / 50 s;
  FIC-329402 "329302,STMH" 0.40 / 200 s; LIC-328504 "328C003,AW" 0.20 / 300 s.
* Uhde loop summaries (the vendor archive, scanned, read from the page images):
  UD-MR-328-EC-0001 rev 1, loop P 328203, sheet 1/2, line D07 — PT-328203, 0-40 bar g, normal
  16.5 bar a; UD-MR-329-EC-0001 rev 1, loop F 329402, sheet 1/2, line D07 — FT-329402, mass flow,
  0-1800 kg/h, normal 1105 kg/h of MP steam at 25 bar a and 330 C.
* Flowserve's calculation sheet for PV-328203 (`ureasim.data.control_valves`).
* V1 ``backend/main.py``: the 328C003 constant block (1339-1368), 328E021 (1989-2006), the
  overhead offset (2026-2028), the vessel's head and LV-328504 (2082, 2107-2110, 3208), the
  hydrolysis block (3287-3375), the seeds in ``State.__init__`` (6849-6852, 6860, 6867,
  7023-7034, 7083-7087, 7096-7100). Each value carries its provenance.
"""

from __future__ import annotations

import math

from ureasim.core.units_of_measure import G_ACC, PA_PER_BAR, R_GAS_J
from ureasim.data.control_valves import PV_328203, design_stroke_pct
from ureasim.data.control_valves_fisher import LV_328504
from ureasim.data.desorption_train import (
    C002_T748_C,
    C002_T_BOT_C,
    C003_M746_DES_KGH,
    C003_M747_DES_KGH,
    C003_M748_DES_KGH,
    C003_M911_DES_KGH,
    C004_M749_DES_KGH,
    C004_T749_C,
    CP_DESORPTION,
    DES_C003,
    W_S747,
)
from ureasim.data.relief_devices import RELIEF_DEVICES, RELIEF_SIZING
from ureasim.thermo import iapws
from ureasim.thermo.ammonia_water import liquor_pv_bara, vapour_molar_mass
from ureasim.thermo.domains import MW

# ======================================================================================
# The vessel and its holdup
# ======================================================================================

#: The hydrolyser's temperature [deg C] (TT-328013, the bottom) and pressure [bar a] at design.
#: Source: V1 `main.py` R328_C003_T, R328_C003_P_BARA (PFD-22).
C003_T_C = 200.0
C003_P_BARA = 16.8

#: 746's temperature at design [deg C], 328E021's cold outlet (TT-328009). Source: V1 `main.py`
#: R328_C003_T746.
C003_T746_C = 190.0

#: The bottom-to-third-tray differential TIC-328012 reads at design [K]: TT-328013 - TT-328012.
C003_DT_DES_K = C003_T_C - C003_T746_C

#: The overhead's offset below the bulk [K]: 748 leaves at 188 C (PFD-22), so TT-328011 rides the
#: live hydrolyser at 12 K below it. Source: V1 `main.py` R328_C003_DT_748 (AUDIT B6).
C003_DT_748_K = C003_T_C - C002_T748_C

#: PFD 746's density [kg/m3] at 190 C and 14.7 bar a — the liquor's density in the column, its
#: head and its conversion. Source: V1 `main.py` R328_C003_RHO_746_KGM3.
C003_RHO_KGM3 = 908.5

#: Inside diameter and cylindrical shell [m]; the shell volume [m3], 62.269, and the bore [m2].
#: Source: the datasheet file above, via V1 `main.py` R328_C003_ID_M, R328_C003_SHELL_M (A-6).
C003_ID_M = 1.950
C003_SHELL_M = 20.850
C003_VOL_M3 = math.pi * 0.25 * C003_ID_M ** 2 * C003_SHELL_M
C003_AREA_M2 = math.pi * 0.25 * C003_ID_M ** 2

#: Design holdup [kg]: an hour of 747. Source: V1 `main.py` R328_C003_M_DES.
C003_M_DES_KG = C003_M747_DES_KGH / 3600.0 * 3600.0

#: LI-328504 at the design holdup [%]: V1 reads the level as M / M_des x 50.
C003_LEVEL_DES_PCT = 50.0

#: Floor on the holdup [kg]: V1's ``max(..., 1.0)``, and the drain's heel (decision 11).
C003_M_FLOOR_KG = 1.0

#: The liquid the shell holds full [kg], 56 571: above it the column overflows (decision 11).
C003_FULL_KG = C003_VOL_M3 * C003_RHO_KGM3

#: The liquid's depth at design [m], 12.554, and its head [bar], 1.1187. Source: V1 `main.py`
#: R328_C003_H_DES_M, R328_C003_HEAD_DES.
C003_H_DES_M = C003_M_DES_KG / (C003_RHO_KGM3 * C003_AREA_M2)
C003_HEAD_DES_BAR = C003_RHO_KGM3 * G_ACC * C003_H_DES_M / PA_PER_BAR

# ======================================================================================
# The heat balance at design
# ======================================================================================

#: The MP steam's enthalpy drop in the column [kJ/kg]. Source: V1 `main.py` R328_C003_M911_DH.
M911_DH_KJKG = 2235.0

#: The overhead's back-solved latent heat [kJ/kg] — before the hydrolysis endotherm is taken out
#: of it: 746 heated from 190 to 200 C and 911's enthalpy drop, over 748. About 1378. The unit
#: subtracts the design endotherm, as V1 does in a later statement (`main.py` 3373).
#: Source: V1 `main.py` R328_C003_LAM748 (its first definition, 1366-1368).
LAM748_BASE_KJKG = ((C003_M746_DES_KGH / 3600.0 * CP_DESORPTION * (C003_T746_C - C003_T_C)
                     + C003_M911_DES_KGH / 3600.0 * M911_DH_KJKG)
                    / (C003_M748_DES_KGH / 3600.0))

# ======================================================================================
# The hydrolysis
# ======================================================================================

#: The residence the design flow has [s]: an hour. Source: V1 `main.py` R328_AI701_TAU_S.
C003_TAU_DES_S = 3600.0

#: Heat of hydrolysis [kJ/mol]: carbamate formation, -117, and its dehydration to urea, +15.5,
#: reversed. Source: Helwan Fundamentals pp. 1-2, via V1 `main.py` R328_HYD_DH_KJMOL.
HYDROLYSIS_DH_KJMOL = 101.5

# ======================================================================================
# 328E021 A/B, the feed/effluent interchanger (decision 14 applies)
# ======================================================================================

#: The cold side's temperature effectiveness, from the design temperatures: (190 - 139) /
#: (200 - 139) = 51/61. The datasheet's rounded pair would give 190.0021 C; these give 190.0 and
#: reconstruct the datasheet's 1913.6 kW. Source: V1 `main.py` R328_E021_EPS_T.
E021_EPS_T = (C003_T746_C - C002_T_BOT_C) / (C003_T_C - C002_T_BOT_C)

#: The shell loss in flow-temperature units [kg.K/h], 49 005 — the hot duty the cold side does
#: not receive at design, 54.45 kW on 4.0 kJ/(kg K) (the datasheet's 54.4). Source: V1 `main.py`
#: R328_E021_LOSS_DT.
E021_LOSS_DT_KGKH = (C004_M749_DES_KGH * (C003_T_C - C004_T749_C)
                     - C003_M746_DES_KGH * (C003_T746_C - C002_T_BOT_C))

#: Floor on the hot flow the balance divides by [kg/h]. Source: V1 `main.py`, ``max(m_749,
#: 1e-6)``.
E021_HOT_FLOW_FLOOR_KGH = 1e-6

# ======================================================================================
# PV-328203, the overhead to 328C002
# ======================================================================================

#: The overhead's design molar mass [kg/kmol]: the back-solved vapour's. Source: V1 `main.py`
#: R328_M748_MW_DES.
MW748_DES = vapour_molar_mass(DES_C003.y)

#: PV-328203's trim, design stroke [%] and xT. DECIDED 2026-09-30 (§5 rule 7, the class of
#: handoff B-44): Flowserve's Pos. 64, Kvs 10, Valtek modified equal percentage, passing PFD 748
#: at 70.56 % on its normal case, xT 0.8047 there. V1 runs it linear from 50 % on the IEC 0.75
#: (``R328_C003_PV_OP_DES``, ``characteristic="linear"``).
PV328203_CHAR = PV_328203.characteristic
PV328203_OP_DES_PCT = design_stroke_pct(PV_328203, C003_M748_DES_KGH)
PV328203_XT = PV_328203.normal_case.xt

# ======================================================================================
# LV-328504, the bottoms letdown to 328C004
# ======================================================================================

#: LV-328504 on Fisher's trim (decided 2026-10-22, decision 150; decision 23's class): equal
#: percentage, rated Cv 82.2, FL 0.819, its design stroke where the rated Cv passes 747 on the
#: normal case (UD-MR-G00-DZ-0014, item 023, found in session 69). V1 runs it linear from 50 %
#: (`main.py` R328_LV504_OP_DES, R328_LV_CHAR), no vendor set having been found.
LV504_OP_DES_PCT = design_stroke_pct(LV_328504, C003_M747_DES_KGH)
LV504_CHAR = LV_328504.characteristic
LV504_FL = LV_328504.normal_case.fl

#: The liquor's bubble pressure at the valve's design inlet [bar a], 5.06: 749 at 148 C, after
#: 328E021's hot side. Source: V1 `main.py` R328_LV504_PV_DES.
LV504_PV_DES_BARA = liquor_pv_bara(W_S747, C004_T749_C)

#: LV-328504's design inlet [bar a]: the column plus its design head. Source: V1 `main.py`.
LV504_P1_DES_BARA = C003_P_BARA + C003_HEAD_DES_BAR

# ======================================================================================
# The four controllers
# ======================================================================================

#: PT-328203's calibrated range [bar of span]: 0 to 40 bar g. Source: UD-MR-328-EC-0001 rev 1,
#: loop P 328203, sheet 1/2, line D07.
PT_328203_SPAN_BAR = 40.0

#: PIC-328203, the hydrolyser's pressure: DIRECT acting on PV-328203. The table's 1.50 and 50 s,
#: derivative off, on PT-328203's span: 3.75 %/bar (decision 10, §5 rule 7). V1 runs 1.50 %/bar.
#: The set-point range [bar a] is V1's.
PIC_328203_KC_TABLE = 1.5
PIC_328203_KC = PIC_328203_KC_TABLE * 100.0 / PT_328203_SPAN_BAR
PIC_328203_TI_S = 50.0
PIC_328203_SP_LO_BARA = 12.0
PIC_328203_SP_HI_BARA = 20.0

#: FT-329402's calibrated range [kg/h of span]: 0 to 1800, mass flow. Source: UD-MR-329-EC-0001
#: rev 1, loop F 329402, sheet 1/2, line D07.
FT_329402_SPAN_KGH = 1800.0

#: FIC-329402, the MP steam 911: a MASS loop, in CAS with no remote set point wired (V1). The
#: table's 0.40 and 200 s, derivative off, on FT-329402's span: 0.0222 %/(kg/h) (decision 10,
#: §5 rule 7). V1 runs 0.40 %/(kg/h). Design stroke 50 %, the set point up to 3000 kg/h, V1's.
FIC_329402_KC_TABLE = 0.4
FIC_329402_KC = FIC_329402_KC_TABLE * 100.0 / FT_329402_SPAN_KGH
FIC_329402_TI_S = 200.0
FIC_329402_OP_DES_PCT = 50.0
FIC_329402_SP_HI_KGH = 3000.0

#: FT-329402's lag [s], V1 ``_fic_flow``'s default.
FT_329402_TAU_S = 5.0

#: LIC-328504, the level: DIRECT acting on LV-328504. The table's 0.20 and 300 s; a level PV in
#: % is already per cent of span, so V1's number stands.
LIC_328504_KC = 0.2
LIC_328504_TI_S = 300.0

#: TIC-328012, the bottom-to-third-tray differential, 10 K. V1 steps it for its faceplate only:
#: its output drives nothing; set point 0-30 K. Its faceplate in the plant DCS (photograph of 24
#: October 2026, `References/Gaps Closure/Gaps/20261024_033945.jpg`): gain 0.20, TI 3000 s, TD and
#: TF 0, range 0-200; on span, 0.20 x 100 % / 200 K = 0.10 % per K (decided 2026-10-28, decisions 76
#: and 77's class). V1 runs Kc 3.0 and Ti 250 s (`main.py` State.__init__ 7083-7087).
TIC_328012_KC = 0.20 * 100.0 / 200.0
TIC_328012_TI_S = 3000.0
TIC_328012_SP_HI_K = 30.0

# ======================================================================================
# SV32852, the column's relief (decided 2026-09-30, handoff B-47)
# ======================================================================================

#: SV32852 on the MP steam inlet STMH2-329302-EG13E (P&ID 104): set 23.0 bar g, 24.01 bar a, on
#: the sheet's 1.010 bar a (Uhde UD-RL-328-EC-0003; Sempell's certificate, 23.0 bar g). It
#: reseats 10 % of set below, at 21.71 bar a (Sempell UD-RL-G00-DZ-0001-001 page 92).
SV32852_SET_BARA = RELIEF_DEVICES["SV32852"].set_bara
SV32852_RESEAT_BARA = RELIEF_SIZING["SV32852"].reseat_bara(RELIEF_DEVICES["SV32852"])

#: Its certified capacity [kg/h], 24 897.4, on orifice L (2206.18 mm2, alpha_w 0.922): superheated
#: steam at 330 C and 26.31 bar a, the set pressure plus 10 % [bar a]. The steam's molar mass and
#: its compressibility there, Z = P v M / (R T) = 0.9448 on IAPWS-IF97 region 2, back-solve the
#: orifice the column's vapour is vented through.
SV32852_CAP_KGH = RELIEF_SIZING["SV32852"].capacity_kgh
SV32852_P_REL_BARA = RELIEF_SIZING["SV32852"].relieving_bara(RELIEF_DEVICES["SV32852"])
SV32852_T_REL_K = RELIEF_SIZING["SV32852"].t_c + 273.15
SV32852_MW_REL = MW["H2O"]
SV32852_Z_REL = (SV32852_P_REL_BARA * 1.0e5 * iapws.v_vapour_m3kg(
    RELIEF_SIZING["SV32852"].t_c, SV32852_P_REL_BARA) * SV32852_MW_REL / 1000.0
                 / (R_GAS_J * SV32852_T_REL_K))

__all__ = [
    "C003_T_C", "C003_P_BARA", "C003_T746_C", "C003_DT_DES_K", "C003_DT_748_K", "C003_RHO_KGM3",
    "C003_ID_M", "C003_SHELL_M", "C003_VOL_M3", "C003_AREA_M2", "C003_M_DES_KG",
    "C003_LEVEL_DES_PCT", "C003_M_FLOOR_KG", "C003_FULL_KG", "C003_H_DES_M", "C003_HEAD_DES_BAR",
    "M911_DH_KJKG", "LAM748_BASE_KJKG", "C003_TAU_DES_S", "HYDROLYSIS_DH_KJMOL",
    "E021_EPS_T", "E021_LOSS_DT_KGKH", "E021_HOT_FLOW_FLOOR_KGH",
    "MW748_DES", "PV328203_CHAR", "PV328203_OP_DES_PCT", "PV328203_XT",
    "LV504_OP_DES_PCT", "LV504_CHAR", "LV504_FL", "LV504_PV_DES_BARA", "LV504_P1_DES_BARA",
    "PT_328203_SPAN_BAR", "PIC_328203_KC_TABLE", "PIC_328203_KC", "PIC_328203_TI_S",
    "PIC_328203_SP_LO_BARA", "PIC_328203_SP_HI_BARA", "FT_329402_SPAN_KGH",
    "FIC_329402_KC_TABLE", "FIC_329402_KC", "FIC_329402_TI_S", "FIC_329402_OP_DES_PCT",
    "FIC_329402_SP_HI_KGH", "FT_329402_TAU_S", "LIC_328504_KC", "LIC_328504_TI_S",
    "TIC_328012_KC", "TIC_328012_TI_S", "TIC_328012_SP_HI_K", "SV32852_SET_BARA",
    "SV32852_RESEAT_BARA", "SV32852_CAP_KGH", "SV32852_P_REL_BARA", "SV32852_T_REL_K",
    "SV32852_MW_REL", "SV32852_Z_REL",
]
