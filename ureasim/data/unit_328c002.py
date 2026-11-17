"""328C002 — desorber I: the design basis.

328C002 is the upper section of the desorption tower: fifteen sieve trays over its own sump,
1250 mm across. The ammonia water from 328D003 enters as 738 after 328E007 has heated it, the
reflux 775 comes back from 328D001, and the two hot overheads of the sections below it — 748
from the hydrolyser 328C003 and 750 from desorber II 328C004 — condense in it and are its
stripping vapour. What they strip leaves overhead as 737 to 328E004 and 328D001; the stripped
liquor leaves the sump as 743 through 328P006 and LV-328503 to 328E021 and the hydrolyser.

    738 (114 C) + 775 (61 C) + 748 (188 C) + 750 (140 C) --> 328C002 (139 C bottoms, 3.5 bar a)
                          737 (117 C) --> 328E004 --> 328D001          743 --> 328P006 --> LV-328503

The train's shared stream table and the three stage anchors are in
`ureasim.data.desorption_train`; this module carries the column's own vessel, holdup, energy
anchor, level valve and level controller.

Sources
-------
* ``Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md`` — PFD 737, 738, 743, 748, 750 and
  775 (PFD-22), and 743's 933.0 kg/m3 at 139 C.
* ``References/328P003, 328P006, 328P007, 328C002. 328C003, 328C004, 328E007, 328E001
  Datasheets.md`` — the shell (1250 mm, 10 470 mm) and 328P006A/B: 4.7 bar a suction, 24.4 bar a
  discharge, 19.7 bar differential.
* ``References/Master_PID_Tuning_Constants.md`` — LIC-328503, "328C002,AW": 1.50, 180 s, which
  V1 seeds; a level PV in % is already per cent of span.
* V1 ``backend/main.py``: the 328C002 constant block (1309-1337), its geometry (1424-1462), its
  pressure (2022-2062), LV-328503 (2081-2105), the Kremser stage table (3137-3175), the design
  duty (3109-3111) and molar mass (3101), the level valve's design Pv (3206-3207), and the seeds
  in ``State.__init__`` (6639-6640, 6841-6843, 6859-6869, 7089-7092). Each value carries its
  provenance.
"""

from __future__ import annotations

import math
from ureasim.core.units_of_measure import G_ACC, PA_PER_BAR
from ureasim.data.desorption_train import (
    C002_M738_DES_KGH,
    C002_M743_DES_KGH,
    C002_M748_DES_KGH,
    C002_M750_DES_KGH,
    C002_M775_DES_KGH,
    C002_NTHEO,
    C002_NTRAY,
    C002_P_TOP_BARA,
    C002_T748_C,
    C002_T750_C,
    C002_T738_DES_C,
    C002_T_BOT_C,
    C002_T_TOP_C,
    COL_AREA_M2,
    CP_DESORPTION,
    D001_T_C,
    DES_C002,
    FROTH_PHI,
    KINF,
    TRAY_ACTIVE_M2,
    TRAY_WEIR_M,
    W_S743,
)
from ureasim.data.control_valves import design_stroke_pct
from ureasim.data.control_valves_fisher import LV_328503
from ureasim.data.relief_devices import RELIEF_DEVICES, RELIEF_SIZING
from ureasim.thermo import iapws
from ureasim.thermo.ammonia_water import desorber_stage, liquor_pv_bara, vapour_molar_mass

# ======================================================================================
# The vessel and its holdup
# ======================================================================================

#: Inside diameter and cylindrical shell [m], and the shell volume the vapour space is cut from
#: [m3], 12.849.
C002_ID_M = 1.250
C002_SHELL_M = 10.470
C002_VOL_M3 = math.pi * 0.25 * C002_ID_M ** 2 * C002_SHELL_M

#: The sump's normal liquid level above the tangent line [m] (tray arrangement).
C002_H_NLL_M = 1.150

#: The bottoms' density [kg/m3]: PFD 743 at 139 C. The datasheet's 944.0 at 138 C is the
#: mechanical design value for weights and head; the process model takes the PFD's.
C002_RHO_KGM3 = 933.0

#: The design liquid inventory [kg], ~1588: the aerated holdup on fifteen trays plus the sump
#: at its normal level. Level is M / M_des x 50, so the design reads 50 %.
C002_M_DES_KG = (C002_NTRAY * TRAY_ACTIVE_M2 * TRAY_WEIR_M * FROTH_PHI
                 + COL_AREA_M2 * C002_H_NLL_M) * C002_RHO_KGM3

#: The level at the design inventory [%].
C002_LEVEL_DES_PCT = 50.0

#: Floor on the holdup [kg]: V1's ``max(..., 1.0)``.
C002_M_FLOOR_KG = 1.0

#: The liquid the shell holds when full [kg], 11 988: the cylindrical shell at the bottoms'
#: density, the heads excluded as they are for 328D001. V1 has no ceiling, and LI-328503 would
#: read 377 % there. Above it the column overflows (decision 11, applied as a standing rule).
C002_FULL_KG = C002_VOL_M3 * C002_RHO_KGM3

#: LT-328503's taps (decision 243, handoff B-156's fourth unit). Uhde's datasheet UD-AU-328-EC-0001
#: (`References/Datasheets/328C002 328C004 Datasheet.pdf`, scanned, read from the page images):
#: N7B and N7A, the transmitter's pads, at EL 13 330 and 14 530 mm on the principle sketch (p. 6),
#: on the shell above the flat partition at EL 13 030 mm that is 328C002's floor (the tray
#: arrangement, p. 7). The lower tap is 300 mm above the partition, the span 1 200 mm, as Uhde's
#: level sheet UD-MR-G00-EC-0134 p. 6 prints it (set range 110.51 mbar on 923.0 kg/m3, 1.02 times
#: the head). The tray arrangement draws L.L.L. 300 mm, N.L.L. 725 mm and H.L.L. 1 150 mm above the
#: partition; V1's 1.150 m "normal" sump level is the drawing's H.L.L., kept as the design holdup.
LT_328503_TAP_LO_M = 0.300
LT_328503_SPAN_M = 1.200
LT_328503_RHO_KGM3 = 923.0

#: The liquid one span of LT-328503 holds [kg], 1 359: the shell's bore between the taps at the
#: sheet's density.
LT_328503_SPAN_KG = LT_328503_RHO_KGM3 * math.pi * 0.25 * C002_ID_M ** 2 * LT_328503_SPAN_M

#: LT-328503's reading at the design holdup [%], 70.83: the sump's 1.150 m less the lower tap's
#: 0.300 m, over the span. LIC-328503's set point between the taps.
LT_328503_DES_PCT = (C002_H_NLL_M - LT_328503_TAP_LO_M) / LT_328503_SPAN_M * 100.0


def lt_328503_pct(m_kg: float) -> float:
    """LI-328503 [%]: the height of 328C002's sump liquid between LT-328503's taps (decision 243).

    Process utility
    ---------------
    What the board shows, what LIC-328503 holds by LV-328503 and what AC4's L2 stop on 328P006A / B
    reads. A DP cell reads only between its taps: 0 % at 625 kg, the sump about 300 mm deep and the
    trays' froth still on them (V1 reads 19.7 % there), 100 % at the upper pad; the reading moves 2.34
    times as far per kilogram as V1's 50 % over the design holdup, which counts the trays' froth.
    AC4's 5 % L2 stops 328P006A / B at 693 kg, not V1's reading's 159 kg.

    Equation
    --------
        LI = clamp( LI_des + (M - M_des) / (rho A L) . 100, 0, 100 )

    written as the departure from the design holdup, so the design holdup reads its set point
    exactly; the trays' froth is the design's, held in M_des. Source: As-Built §CXXXVI.
    """
    return min(max(LT_328503_DES_PCT + (m_kg - C002_M_DES_KG) / LT_328503_SPAN_KG * 100.0, 0.0),
               100.0)

# ======================================================================================
# The pressure and the bubble point
# ======================================================================================

#: Top-to-bottom design differential [K]: the column top (737, TT-328008) sits 22 K below the
#: bottoms. TT-328008 and the overhead valve's inlet temperature ride the live bottoms on it.
C002_DT_TOP_K = C002_T_BOT_C - C002_T_TOP_C

#: The bottom node's offset on the overhead pressure [bar]: the pressure at which PURE WATER
#: boils at the 139 C bottoms, less the 3.5 bar a overhead — +0.0139 bar on IAPWS-IF97. One
#: lumped offset, back-solved so the water saturation curve at the bottom node reproduces the
#: PFD's bottoms exactly. (V1's comment gives -0.0104 bar, a value of its retired Antoine curve;
#: the expression, which is what runs, is the one here.)
C002_DP_COL_BAR = iapws.psat_bara(C002_T_BOT_C) - C002_P_TOP_BARA

#: The column's cross-section [m2], written as V1 writes it for the liquid head (the tray
#: geometry's `COL_AREA_M2` is the same circle written the other way).
C002_AREA_M2 = math.pi * 0.25 * C002_ID_M ** 2

# ======================================================================================
# The energy anchor: what the two hot overheads and the sensible net can boil
# ======================================================================================

#: The condensing latent heats of 748 and 750 in the column [kJ/kg]. V1's literals, no source.
C002_LAM748_KJKG = 2000.0
C002_LAM750_KJKG = 2100.0

#: The sensible net of the four inlets onto the 139 C bottoms at design [kW].
C002_SENS_DES_KW = ((C002_M738_DES_KGH * (C002_T738_DES_C - C002_T_BOT_C)
                     + C002_M775_DES_KGH * (D001_T_C - C002_T_BOT_C)
                     + C002_M748_DES_KGH * (C002_T748_C - C002_T_BOT_C)
                     + C002_M750_DES_KGH * (C002_T750_C - C002_T_BOT_C))
                    / 3600.0 * CP_DESORPTION)

#: The design duty that boils 737 [kW], in the runtime's operand order so the live ratio is
#: exactly 1.0 at the seed. Its implied latent, Q / (737 / 3600), is ~1879 kJ/kg.
C002_Q_DES_KW = (C002_SENS_DES_KW
                 + C002_M748_DES_KGH / 3600.0 * C002_LAM748_KJKG
                 + C002_M750_DES_KGH / 3600.0 * C002_LAM750_KJKG)

#: The design molar mass of 737 [kg/kmol], off the back-solved vapour the column seeds on —
#: the w ~ sqrt(M) anchor of the overhead line's gas law.
C002_MW737_DES = vapour_molar_mass(DES_C002.y)

# ======================================================================================
# LV-328503: 328P006's discharge to 328E021 and the hydrolyser
# ======================================================================================

#: 328P006A/B: design suction [bar a] and rated differential [bar] (datasheet: 4.7 -> 24.4 bar
#: a, 215 m at 36 m3/h normal). One point on the curve, no shape: the differential is held.
P006_SUCT_DES_BARA = 4.7
P006_DP_PUMP_BAR = 19.7

#: The sump depth at the design holdup [m], 1.387, and the fixed drop from the bottom nozzle to
#: the pump centreline [m], 11.727, back-solved so the design suction reads the datasheet's 4.7.
C002_H_DES_M = C002_M_DES_KG / (C002_RHO_KGM3 * C002_AREA_M2)
P006_Z_DROP_M = ((P006_SUCT_DES_BARA - C002_P_TOP_BARA) * PA_PER_BAR
                 / (C002_RHO_KGM3 * G_ACC)) - C002_H_DES_M

#: LV-328503's design inlet pressure [bar a], 24.4.
LV503_P1_DES_BARA = P006_SUCT_DES_BARA + P006_DP_PUMP_BAR

#: LV-328503 on Fisher's trim (decided 2026-10-22, decision 150; decision 23's class): equal
#: percentage, rated Cv 82.2, FL 0.819, its design stroke where the rated Cv passes PFD 743 on the
#: normal case, 56.95 %. V1 runs it linear from 50 % ("no control-valve datasheet exists"); Fisher's
#: sheet was found in session 69 (`data.control_valves_fisher`). LIC-328503 is seeded there.
LV503_OP_DES_PCT = design_stroke_pct(LV_328503, C002_M743_DES_KGH)
LV503_CHARACTERISTIC = LV_328503.characteristic
LV503_FL = LV_328503.normal_case.fl

#: The liquor's design temperature at the valve [deg C] — the bottoms', 139 C: 328P006 lifts it
#: from the sump to LV-328503, and 328E021 heats it only downstream — and its bubble pressure
#: there [bar a], 3.93: the flash choke's anchor. Source: Uhde loop summary UD-MR-328-EC-0001
#: rev 1, loop L 328503, sheet 2/2 (vendor archive, scanned, read from the page image): LV-328503
#: on line 100-AW7-328180, inlet 24.0 bar a and 140 C normal, outlet 16.98 bar a, 37.2 m3/h,
#: design temperature 170 C. V1 reads the liquor at 328E021's cold outlet, 190 C (14.97 bar a); the
#: port departs from it by decision of 2026-09-30 (handoff B-43).
LV503_T_IN_DES_C = C002_T_BOT_C
LV503_PV_DES_BARA = liquor_pv_bara(W_S743, LV503_T_IN_DES_C)

# ======================================================================================
# LIC-328503 -> LV-328503, the bottoms level
# ======================================================================================

#: LIC-328503: DIRECT acting on the level; 1.50, 180 s, set point 50 %.
LIC_328503_KC = 1.5
LIC_328503_TI_S = 180.0
LIC_328503_SP_PCT = 50.0

# ======================================================================================
# The Kremser stage: how the column's lumped volatility moves with its stripping vapour
# ======================================================================================

#: 328C002's stage: 9.525 theoretical stages; its stripping vapour the two hot overheads; its
#: node the bottom, at the overhead pressure plus the lumped offset.
C002_STAGE = desorber_stage(DES_C002, C002_NTHEO, C002_M748_DES_KGH + C002_M750_DES_KGH,
                            C002_M743_DES_KGH, C002_P_TOP_BARA + C002_DP_COL_BAR, KINF)

# ======================================================================================
# SV32850 and SV32851, the column's relief (decided 2026-09-30, handoff B-47)
# ======================================================================================

#: SV32850 and SV32851 on line AW4-328066-EC08D (P&ID 104), alike: set 5.0 bar g, 6.01 bar a, on
#: the sheets' 1.010 bar a (Uhde UD-RL-328-EC-0001 and -0002; Sempell's certificates, as
#: specified). They reseat 10 % of set below, at 5.51 bar a (Sempell UD-RL-G00-DZ-0002-001
#: page 5).
SV32850_SET_BARA = RELIEF_DEVICES["SV32850"].set_bara
SV32850_RESEAT_BARA = RELIEF_SIZING["SV32850"].reseat_bara(RELIEF_DEVICES["SV32850"])

#: Each one's certified capacity [kg/h], 25 000, on orifice T (20 106.2 mm2) lift-limited to
#: 16.23 mm, alpha_w 0.353: gas of molar mass 18.0, k 1.310 and Z 0.99 at 159 C and 6.51 bar a,
#: the set pressure plus 10 % [bar a]. Two valves, set alike, lift and reseat together.
SV32850_CAP_KGH = RELIEF_SIZING["SV32850"].capacity_kgh
SV32850_P_REL_BARA = RELIEF_SIZING["SV32850"].relieving_bara(RELIEF_DEVICES["SV32850"])
SV32850_T_REL_K = RELIEF_SIZING["SV32850"].t_c + 273.15
SV32850_MW_REL = RELIEF_SIZING["SV32850"].mw
SV32850_Z_REL = RELIEF_SIZING["SV32850"].z
SV32850_K = RELIEF_SIZING["SV32850"].k
SV32850_COUNT = 2

__all__ = [
    "C002_ID_M", "C002_SHELL_M", "C002_VOL_M3", "C002_H_NLL_M", "C002_RHO_KGM3",
    "C002_M_DES_KG", "C002_LEVEL_DES_PCT", "C002_M_FLOOR_KG", "C002_FULL_KG",
    "LT_328503_TAP_LO_M", "LT_328503_SPAN_M", "LT_328503_RHO_KGM3", "LT_328503_SPAN_KG",
    "LT_328503_DES_PCT", "lt_328503_pct",
    "C002_DT_TOP_K",
    "C002_DP_COL_BAR", "C002_AREA_M2", "C002_LAM748_KJKG", "C002_LAM750_KJKG",
    "C002_SENS_DES_KW", "C002_Q_DES_KW", "C002_MW737_DES",
    "P006_SUCT_DES_BARA", "P006_DP_PUMP_BAR", "C002_H_DES_M", "P006_Z_DROP_M",
    "LV503_P1_DES_BARA", "LV503_OP_DES_PCT", "LV503_CHARACTERISTIC", "LV503_FL", "LV503_T_IN_DES_C",
    "LV503_PV_DES_BARA", "LIC_328503_KC", "LIC_328503_TI_S", "LIC_328503_SP_PCT",
    "C002_STAGE", "SV32850_SET_BARA", "SV32850_RESEAT_BARA", "SV32850_CAP_KGH",
    "SV32850_P_REL_BARA", "SV32850_T_REL_K", "SV32850_MW_REL", "SV32850_Z_REL", "SV32850_K",
    "SV32850_COUNT",
]
