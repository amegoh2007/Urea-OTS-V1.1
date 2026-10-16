"""Unit 328's desorption train: the design stream table its three columns share.

The train strips ammonia and carbon dioxide out of the process condensate in three columns:

    738 --> 328C002 (desorber I) --743/746--> 328E021 --> 328C003 (hydrolyser)
              ^  |  737 -> 328E004 -> 328D001 --775 reflux--^          | 747/749
              |  +<----------- 748 (hydrolyser overhead) -------------+
              |                                                         v
              +<------------ 750 (desorber II overhead) ---------- 328C004 (desorber II)
                                                                        | 739 -> 328E007

328C002 and 328C004 are one 25.5 m tower, 328C002 stacked on 328C004 on a common skirt, each
with its own sump (Uhde UD-AU-328-EC-0001 rev 01). The two hot overheads, 748 and 750, are
328C002's stripping vapour; 328C002's own overhead, 737, goes to the reflux drum.

This module carries what the three columns share: the PFD-22 flows and compositions of their
streams, each column's design temperature and pressure, the tower's tray geometry, and the
three stages' design anchors. The anchors CHAIN: 328C002's is struck on the vapours 328C003's
and 328C004's own back-solves deliver, not on the PFD's 748 and 750 rows — the two differ by up
to 0.2 %pt (the PFD's rounding), and anchoring on the tabulated rows while the model feeds the
back-solved ones made the design state a slow leak in V1 (328C002's ammonia crept from 0.63 %
to 1.53 % in twenty minutes). Each column's own constants — vessel, holdup, level valve,
controllers — live with its unit: `ureasim.data.unit_328c002` so far.

Sources
-------
* ``Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md`` — PFD-22 streams 737 to 750, 775,
  911 and 931: flows, temperatures, pressures, compositions (liquids mass %, vapours mole %).
* ``References/328P003, 328P006, 328P007, 328C002. 328C003, 328C004, 328E007, 328E001
  Datasheets.md`` and Uhde UD-AU-328-EC-0001 rev 01 (via V1) — the tower's tray geometry.
* V1 ``backend/main.py``: the 328C002 / 328C003 / 328C004 constant blocks (1309-1390), the tray
  geometry (1412-1433), the AI-328701 constants (180-181) and the F-8 species layer
  (2958-3150). Each value carries its provenance.
"""

from __future__ import annotations

import math

from ureasim.core.packet import normalise_solution_mass_fraction as _w_norm
from ureasim.data.unit_328d003 import M735_DES_KGH
from ureasim.data.unit_328e007 import E007_T738_DES_C
from ureasim.thermo.ammonia_water import desorber_stage_anchor, mass_fractions_from_mole_pct

# ======================================================================================
# The train's liquor
# ======================================================================================

#: The train's aqueous heat capacity at each column's design temperature [kJ/kg K] — the
#: anchor `thermo.empirical.aqueous_cp` departs from. Source: V1 `main.py` R328_CP.
CP_DESORPTION = 4.0

# ======================================================================================
# PFD-22 compositions: liquids in MASS %, vapours in MOLE % (module note in
# `thermo.ammonia_water`)
# ======================================================================================

#: 738, the feed to 328C002 (the 328D003 condensate through 328E007).
W_S738 = _w_norm(dict(CO2=3.71, H2O=90.24, NH3=5.23, Urea=0.82))
#: 775, the reflux from 328D001.
W_S775 = _w_norm(dict(CO2=23.63, H2O=47.10, NH3=29.20, Urea=0.07))
#: 743 = 746, 328C002's bottoms to the hydrolyser.
W_S743 = _w_norm(dict(CO2=0.11, H2O=98.50, NH3=0.63, Urea=0.76))
#: 747 = 749, the hydrolyser's bottoms to 328C004.
W_S747 = _w_norm(dict(CO2=0.02, H2O=99.02, NH3=0.97))
#: 739 = 740, the purified condensate. The PFD tabulates NH3 and urea at 1 ppm and leaves CO2
#: blank — blank because it rounds to 0.00 %, not because it is absent: 6.8 kg/h of CO2 enters
#: 328C004 in 749 and the column has two outlets. Taken as zero, the back-solve pins alpha_CO2 to
#: 0 and the CO2 can never leave; on the licensor's own 1 ppm basis it strips with the ammonia.
W_S739 = _w_norm(dict(H2O=99.9997, NH3=1.0e-4, Urea=1.0e-4, CO2=1.0e-4))
#: 737, 328C002's overhead to 328D001 (vapour).
W_S737 = mass_fractions_from_mole_pct(dict(CO2=12.32, H2O=46.21, NH3=41.47))
#: 748, the hydrolyser's overhead to 328C002 (vapour).
W_S748 = mass_fractions_from_mole_pct(dict(CO2=13.06, H2O=82.37, NH3=4.57))
#: 750, 328C004's overhead to 328C002 (vapour).
W_S750 = mass_fractions_from_mole_pct(dict(CO2=0.03, H2O=94.88, NH3=5.08))
#: 911 and 931, the MP and LP stripping steam.
W_STEAM = _w_norm(dict(H2O=100.0))

# ======================================================================================
# 328C002, desorber I: 738 + 748 + 750 + 775 = 737 + 743 [kg/h]
# ======================================================================================

#: The four inlets: 738 (= 735 through 328E007), the two hot overheads that condense in it, 748
#: from the hydrolyser and 750 from 328C004, and 775, the reflux.
C002_M738_DES_KGH = M735_DES_KGH
C002_M748_DES_KGH = 812.0
C002_M750_DES_KGH = 6833.0
C002_M775_DES_KGH = 1675.0
C002_IN_DES_KGH = (C002_M738_DES_KGH + C002_M748_DES_KGH
                   + C002_M750_DES_KGH + C002_M775_DES_KGH)

#: The overhead split, 737 over the inflow, as V1 writes it, and the two outlets: 737 to
#: 328D001 (6665) and 743 to the hydrolyser (33 769).
C002_PHI737 = 6665.0 / 40434.0
C002_M737_DES_KGH = C002_PHI737 * C002_IN_DES_KGH
C002_M743_DES_KGH = C002_IN_DES_KGH - C002_M737_DES_KGH

#: Bottoms and top at design [deg C] (TT-328007, TT-328008), and the three inlet temperatures V1
#: charges: 738 at 328E007's design outlet, 748 at 188 C and 750 at 140 C.
C002_T_BOT_C = 139.0
C002_T_TOP_C = 117.0
C002_T738_DES_C = E007_T738_DES_C
C002_T748_C = 188.0
C002_T750_C = 140.0

#: The column's overhead pressure at the VLE node [bar a], PFD 737 / 738.
C002_P_TOP_BARA = 3.5

# ======================================================================================
# 328C003, the hydrolyser: 746 + 911 = 747 + 748 [kg/h]
# ======================================================================================

#: 746 (= 743 through 328E021) and 911, the MP stripping steam (FIC-329402).
C003_M746_DES_KGH = C002_M743_DES_KGH
C003_M911_DES_KGH = 1105.0
C003_IN_DES_KGH = C003_M746_DES_KGH + C003_M911_DES_KGH

#: The overhead split and the two outlets: 748 to 328C002 (812) and 747 to 328C004 (34 062).
C003_PHI748 = 812.0 / 34874.0
C003_M748_DES_KGH = C003_PHI748 * C003_IN_DES_KGH
C003_M747_DES_KGH = C003_IN_DES_KGH - C003_M748_DES_KGH

#: The hydrolyser's pressure at design [bar a]: 328C002's level valve lets down into it.
C003_P_BARA = 16.8

# ======================================================================================
# 328C004, desorber II: 749 + 931 = 739 + 750 [kg/h]
# ======================================================================================

#: 749 (= 747 through 328E021) and 931, the LP stripping steam (FIC-329401).
C004_M749_DES_KGH = C003_M747_DES_KGH
C004_M931_DES_KGH = 6495.0
C004_IN_DES_KGH = C004_M749_DES_KGH + C004_M931_DES_KGH

#: The overhead split and the two outlets: 750 to 328C002 (6833) and 739 to 328E007 (33 724 —
#: the same float as `unit_328d003.C004_M739_DES_KGH`).
C004_PHI750 = 6833.0 / 40557.0
C004_M750_DES_KGH = C004_PHI750 * C004_IN_DES_KGH
C004_M739_DES_KGH = C004_IN_DES_KGH - C004_M750_DES_KGH

#: 328C004's bottoms temperature [deg C] and overhead pressure [bar a] at design (PFD-22 750 /
#: 779 / 780), and 749's temperature after 328E021's hot side [deg C]. Source: V1 `main.py`
#: R328_C004_T, R328_C004_P_BARA, R328_C004_T749.
C004_T_C = 143.0
C004_P_BARA = 3.7
C004_T749_C = 148.0

# ======================================================================================
# 328D001, the reflux drum 328C002's overhead goes to
# ======================================================================================

#: The drum's design temperature [deg C] — the temperature V1 charges the 775 reflux at — and
#: its pressure [bar a], the far end of 328C002's overhead line.
D001_T_C = 61.0
D001_P_BARA = 2.6

# ======================================================================================
# The tower: tray geometry shared by 328C002 and 328C004 (UD-AU-328-EC-0001, via V1)
# ======================================================================================

#: Shell inside diameter [m], both sections (DDS line 27), and its cross-section [m2].
COL_ID_M = 1.250
COL_AREA_M2 = math.pi / 4.0 * COL_ID_M ** 2

#: Downcomer chord width off the wall [m] (section X-X), and the bubbling area it leaves [m2]:
#: the cross-section less the two segments, 0.9700 m2.
TRAY_DC_W_M = 0.202
_R_M = COL_ID_M / 2.0
_SEGMENT_M2 = (_R_M ** 2 * math.acos((_R_M - TRAY_DC_W_M) / _R_M)
               - (_R_M - TRAY_DC_W_M) * math.sqrt(2.0 * _R_M * TRAY_DC_W_M - TRAY_DC_W_M ** 2))
TRAY_ACTIVE_M2 = COL_AREA_M2 - 2.0 * _SEGMENT_M2

#: Outlet weir height [m] (section C-C), and the clear-liquid height over the weir on an aerated
#: tray [-].
TRAY_WEIR_M = 0.040
FROTH_PHI = 0.5

#: Executed trays (DDS line 35).
C002_NTRAY = 15
C004_NTRAY = 22

# ======================================================================================
# The Kremser stage counts (V1's AI-328701 block)
# ======================================================================================

#: The dilute NH3-water stripping factor K_inf derived at 143 C for desorber II [-], and its
#: theoretical stage count, E_o 0.635 x 22 trays (O'Connell). Source: V1 `main.py`
#: R328_AI701_KINF_C004, R328_AI701_NTHEO_C004.
KINF = 9.5
C004_NTHEO = 13.98

#: The overall tray efficiency [-], 13.98 / 22, and 328C002's theoretical stages: 9.525.
TRAY_EO = C004_NTHEO / C004_NTRAY
C002_NTHEO = TRAY_EO * C002_NTRAY

# ======================================================================================
# The three stage anchors, in V1's order: 328C003 and 328C004 first, 328C002 on their vapours
# ======================================================================================

#: 328C003: 746 + 911 in, 747 down, 748 up, with the hydrolysis extent back-solved from the urea
#: that disappears (4.2734 kmol/h; 747 tabulates no urea).
DES_C003 = desorber_stage_anchor(
    [(W_S743, C003_M746_DES_KGH), (W_STEAM, C003_M911_DES_KGH)],
    W_S747, C003_M747_DES_KGH, C003_M748_DES_KGH, hydrolyse=True, y_pfd=W_S748)
#: 328C004: 749 + 931 in, 739 down, 750 up.
DES_C004 = desorber_stage_anchor(
    [(W_S747, C004_M749_DES_KGH), (W_STEAM, C004_M931_DES_KGH)],
    W_S739, C004_M739_DES_KGH, C004_M750_DES_KGH, y_pfd=W_S750)
#: 328C002: 738 + 775 + 748 + 750 in, the last two on the back-solved vapours; 743 down, 737 up.
DES_C002 = desorber_stage_anchor(
    [(W_S738, C002_M738_DES_KGH), (W_S775, C002_M775_DES_KGH),
     (DES_C003.y, C002_M748_DES_KGH), (DES_C004.y, C002_M750_DES_KGH)],
    W_S743, C002_M743_DES_KGH, C002_M737_DES_KGH, y_pfd=W_S737)

__all__ = [
    "CP_DESORPTION", "W_S738", "W_S775", "W_S743", "W_S747", "W_S739", "W_S737", "W_S748",
    "W_S750", "W_STEAM",
    "C002_M738_DES_KGH", "C002_M748_DES_KGH", "C002_M750_DES_KGH", "C002_M775_DES_KGH",
    "C002_IN_DES_KGH", "C002_PHI737", "C002_M737_DES_KGH", "C002_M743_DES_KGH",
    "C002_T_BOT_C", "C002_T_TOP_C", "C002_T738_DES_C", "C002_T748_C", "C002_T750_C",
    "C002_P_TOP_BARA",
    "C003_M746_DES_KGH", "C003_M911_DES_KGH", "C003_IN_DES_KGH", "C003_PHI748",
    "C003_M748_DES_KGH", "C003_M747_DES_KGH", "C003_P_BARA",
    "C004_M749_DES_KGH", "C004_M931_DES_KGH", "C004_IN_DES_KGH", "C004_PHI750",
    "C004_T_C", "C004_P_BARA", "C004_T749_C",
    "C004_M750_DES_KGH", "C004_M739_DES_KGH",
    "D001_T_C", "D001_P_BARA",
    "COL_ID_M", "COL_AREA_M2", "TRAY_DC_W_M", "TRAY_ACTIVE_M2", "TRAY_WEIR_M", "FROTH_PHI",
    "C002_NTRAY", "C004_NTRAY", "KINF", "C004_NTHEO", "TRAY_EO", "C002_NTHEO",
    "DES_C003", "DES_C004", "DES_C002",
]
