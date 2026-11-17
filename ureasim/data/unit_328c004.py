"""328C004 — desorber II: the design basis.

328C004 is the lower section of the desorption tower: twenty-two sieve trays over its own sump,
1250 mm across, under 328C002 on a common skirt. It strips the ammonia the hydrolysed liquor
still carries: 749, the hydrolyser's bottoms after 328E021's hot side, enters at the top at
148 C; LP steam 931 enters at the bottom on FIC-329401, ratioed by FFIC-329401 to the desorbers'
feed. The steam and what it strips leave overhead as 750 to 328C002, where they are the
stripping vapour; the purified condensate leaves the sump as 739 at 143 C through 328E007's hot
side and LV-328505 to the boundary (740); FV-328406 can take it back to 328D003 through 328E001
as 741 instead, from the line ahead of LV-328505 (P&ID sheet 104).

    749 (148 C) + 931 (LP steam) --> 328C004 (143 C, 3.7 bar a) --750--> 328C002
                                          \\--739--> 328E007 (hot) --740--+--> LV-328505 --> boundary
                                                                         \\--> 328E001 --> FV-328406
                                                                                   --741--> 328D003

The train's shared stream table and the three stage anchors are in
`ureasim.data.desorption_train`; this module carries the column's own vessel, holdup, energy
anchor, level valve, and its loops.

Sources
-------
* ``Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md`` — PFD 739, 749, 750 and 931
  (PFD-22), 739's 923.28 kg/m3 at 143 C, and PFD 735's 31.4 m3/h.
* ``References/328P003, 328P006, 328P007, 328C002. 328C003, 328C004, 328E007, 328E001
  Datasheets.md`` — the shell, 1250 mm and 13 030 mm.
* ``References/Master_PID_Tuning_Constants.md`` — LIC-328505 "328C004,CPP" 1.45 / 180 s;
  FIC-329401 "329375,STLS" 0.30 / 100 s. FFIC-329401 has no row.
* Uhde loop summary UD-MR-329-EC-0001 rev 1, loop F 329401, sheets 1/3 and 2/3 (the vendor
  archive, scanned, read from the page images): FT-329401, mass flow, 3930 / 6495 / 12 000 kg/h,
  range 0-12 000 kg/h, LP steam at 3.9 bar a; FV-329401 a butterfly valve, fail closed, 4.4 -> 3.9
  bar a normal.
* Uhde P&ID sheet 104 (``References/Merged_Searchable_PIDs.pdf``, page 7) and functional diagram
  UD-MR-329-FF-0002 page 2: FFIC-329401, a ratio station, sets FIC-329401 to its ratio of
  FIC-328402, which meters PFD 735 — the desorbers' feed (handoffs B-39, B-49). Functional
  diagram UD-MR-328-FF-0002 page 2: LIC-328505 on LV-328505, switched to FIC-328406's remote set
  point, OUTP / 100 x FIC-328406:MAX, while FIC-328406 is external (handoff B-50).
* Flowserve's calculation sheet for LV-328505 (`ureasim.data.control_valves`).
* V1 ``backend/main.py``: the 328C004 constant block (1370-1390), the tray geometry (1412-1463),
  the column pressure (2063-2064), the head and LV-328505 (2083, 2113-2121), the Kremser stage
  table (3149-3175), the design duty (3112-3114) and molar mass (3103), FFIC-329401's ratio
  (1755-1766), and the seeds in ``State.__init__`` (6641, 6853-6855, 6861, 6868, 7035-7058,
  7100-7106). Each value carries its provenance.
"""

from __future__ import annotations

import math

from ureasim.core.units_of_measure import G_ACC, PA_PER_BAR
from ureasim.data.control_valves import FV_329401, LV_328505, design_stroke_pct
from ureasim.data.desorption_train import (
    C002_T750_C,
    C004_M739_DES_KGH,
    C004_M749_DES_KGH,
    C004_M931_DES_KGH,
    C004_NTHEO,
    C004_NTRAY,
    C004_P_BARA,
    C004_T749_C,
    C004_T_C,
    COL_AREA_M2,
    CP_DESORPTION,
    DES_C004,
    FROTH_PHI,
    KINF,
    TRAY_ACTIVE_M2,
    TRAY_WEIR_M,
    W_S739,
)
from ureasim.data.unit_328d003 import M735_DES_KGH, RHO_735_KGM3, S735_VOL_DES_M3H
from ureasim.data.unit_328e007 import E007_T740_DES_C
from ureasim.data.unit_329 import P_LP_BARA
from ureasim.thermo import iapws
from ureasim.thermo.ammonia_water import desorber_stage, liquor_pv_bara, vapour_molar_mass

# ======================================================================================
# The vessel and its holdup
# ======================================================================================

#: Inside diameter and cylindrical shell [m], and the shell volume the vapour space is cut from
#: [m3], 15.990.
C004_ID_M = 1.250
C004_SHELL_M = 13.030
C004_VOL_M3 = math.pi * 0.25 * C004_ID_M ** 2 * C004_SHELL_M

#: The sump's normal liquid level above the tangent line [m] (tray arrangement).
C004_H_NLL_M = 0.920

#: The bottoms' density [kg/m3]: PFD 739 at 143 C, 923.28; the datasheet's 923.25 at 143 C
#: agrees to 3e-5 — both are water at 143 C, which a < 1 ppm condensate is.
C004_RHO_KGM3 = 923.28

#: The design liquid inventory [kg], ~1436: the aerated holdup on twenty-two trays plus the sump
#: at its normal level (V1 `_r328_holdup`). Level is M / M_des x 50, so the design reads 50 %.
C004_M_DES_KG = (C004_NTRAY * TRAY_ACTIVE_M2 * TRAY_WEIR_M * FROTH_PHI
                 + COL_AREA_M2 * C004_H_NLL_M) * C004_RHO_KGM3

#: The level at the design inventory [%].
C004_LEVEL_DES_PCT = 50.0

#: Floor on the holdup [kg]: V1's ``max(..., 1.0)``.
C004_M_FLOOR_KG = 1.0

#: The liquid the shell holds when full [kg], 14 763: the cylindrical shell at the bottoms'
#: density, the heads excluded as for 328C002. V1 has no ceiling. Above it the column overflows
#: (decision 11, applied as a standing rule).
C004_FULL_KG = C004_VOL_M3 * C004_RHO_KGM3

#: LT-328505's taps (handoff B-156's fifth unit). Uhde's datasheet UD-AU-328-EC-0001
#: (`References/Datasheets/328C002 328C004 Datasheet.pdf`, scanned, read from the page images):
#: N11B and N11A, the transmitter's pads, at EL 210 and 1 210 mm in the nozzle table of the
#: principle sketch (p. 6), above 328C004's bottom tangent line, the sketch's datum. The span is
#: 1 000 mm, as Uhde's level sheet UD-MR-G00-EC-0134 p. 7 prints it (set range 0-96.5 mbar on
#: 923 kg/m3, 1.066 times the head). The tray arrangement (p. 7) draws L.L.L. 100 mm, N.L.L. 510 mm
#: and H.L.L. 920 mm above the tangent line; V1's 0.920 m "normal" sump level is the drawing's
#: H.L.L., kept as the design holdup.
LT_328505_TAP_LO_M = 0.210
LT_328505_SPAN_M = 1.000
LT_328505_RHO_KGM3 = 923.0

#: The liquid one span of LT-328505 holds [kg], 1 133: the shell's bore between the taps at the
#: sheet's density.
LT_328505_SPAN_KG = LT_328505_RHO_KGM3 * math.pi * 0.25 * C004_ID_M ** 2 * LT_328505_SPAN_M

#: LT-328505's reading at the design holdup [%], 71.00: the sump's 0.920 m less the lower tap's
#: 0.210 m, over the span. LIC-328505's set point between the taps.
LT_328505_DES_PCT = (C004_H_NLL_M - LT_328505_TAP_LO_M) / LT_328505_SPAN_M * 100.0


def lt_328505_pct(m_kg: float) -> float:
    """LI-328505 [%]: the height of 328C004's sump liquid between LT-328505's taps.

    Process utility
    ---------------
    What the board shows, what LIC-328505 holds by LV-328505 (or FIC-328406 in cascade) and what
    AC4's L2 stop on 328P007A / B reads. A DP cell reads only between its taps: 0 % at 632 kg, the
    sump 210 mm deep and the trays' froth still on them (V1 reads 22.0 % there), 100 % at the upper
    pad; the reading moves 2.54 times as far per kilogram as V1's 50 % over the design holdup, which
    counts the trays' froth. AC4's 5 % L2 stops 328P007A / B at 689 kg, not V1's reading's 144 kg.

    Equation
    --------
        LI = clamp( LI_des + (M - M_des) / (rho A L) . 100, 0, 100 )

    written as the departure from the design holdup, so the design holdup reads its set point
    exactly; the trays' froth is the design's, held in M_des. Source: As-Built §CXXXVII.
    """
    return min(max(LT_328505_DES_PCT + (m_kg - C004_M_DES_KG) / LT_328505_SPAN_KG * 100.0, 0.0),
               100.0)

# ======================================================================================
# The pressure and the bubble point
# ======================================================================================

#: Bottom-to-top-tray design differential [K], 3: the top tray (TT-328004) sits at 750's 140 C,
#: 3 K below the 143 C bottoms, and rides the live bottoms on it.
C004_DT_DES_K = C004_T_C - C002_T750_C

#: The bottom node's offset on the overhead pressure [bar]: the pressure at which PURE WATER
#: boils at the 143 C bottoms, less the 3.7 bar a overhead — +0.2325 bar on IAPWS-IF97: 22
#: trays of head, a static column. Back-solved so the saturation curve reproduces the PFD's
#: bottoms. (V1's comment gives +0.204 bar, a value of its retired Antoine curve; the
#: expression, which is what runs, is the one here.)
C004_DP_COL_BAR = iapws.psat_bara(C004_T_C) - C004_P_BARA

#: The column's cross-section [m2], written as V1 writes it for the liquid head.
C004_AREA_M2 = math.pi * 0.25 * C004_ID_M ** 2

# ======================================================================================
# The energy anchor: what the LP steam and the sensible net can boil
# ======================================================================================

#: The LP steam's enthalpy drop condensing in the column [kJ/kg]. V1's literal, no source.
C004_M931_DH_KJKG = 2136.0

#: The design duty that boils 750 [kW] — 749's sensible heat onto the 143 C bottoms plus the LP
#: steam's — in the runtime's operand order, so the live ratio is exactly 1.0 at the seed.
C004_Q_DES_KW = (C004_M749_DES_KGH / 3600.0 * CP_DESORPTION * (C004_T749_C - C004_T_C)
                 + C004_M931_DES_KGH / 3600.0 * C004_M931_DH_KJKG)

#: The design molar mass of 750 [kg/kmol], off the back-solved vapour the column seeds on — the
#: w ~ sqrt(M) anchor of the overhead line's gas law.
C004_MW750_DES = vapour_molar_mass(DES_C004.y)

# ======================================================================================
# LV-328505: the bottoms through 328E007 to the boundary
# ======================================================================================

#: The outlet datum [bar a]: 328P003's 1.0 bar a suction. 328E007 sits between and its line
#: pressure drop is not published, so the whole drop is lumped on the valve — a stated choice
#: that sets only the datum; the law runs on the ratio (V1).
LV505_P2_BARA = 1.0

#: The sump depth at the design holdup [m], 1.268, its head [bar], 0.1148, and the valve's
#: design inlet pressure [bar a].
C004_H_DES_M = C004_M_DES_KG / (C004_RHO_KGM3 * C004_AREA_M2)
C004_HEAD_DES_BAR = C004_RHO_KGM3 * G_ACC * C004_H_DES_M / PA_PER_BAR
LV505_P1_DES_BARA = C004_P_BARA + C004_HEAD_DES_BAR

#: LV-328505 on its vendor trim (decision 23): Valtek's modified equal percentage, Kvs 63, from
#: the stroke at which its rated capacity passes the design 739 on the normal case (68 % at
#: 18.2 m3/h), on that case's FL. V1: linear from 50 %.
LV505_CHAR = LV_328505.characteristic
LV505_OP_DES_PCT = design_stroke_pct(LV_328505, C004_M739_DES_KGH)
LV505_FL = LV_328505.normal_case.fl

#: LV-328505 flashes where its liquor warrants it (decided 2026-09-30, handoff B-46). The valve
#: stands on 740, after 328E007's hot side (P&ID sheet 104): its liquor arrives at 89 C, boiling
#: at 0.68 bar a, and Flowserve's sheet lets it down from 3.54 to 3.0 bar a, far above.
#: On the model's datum, the whole drop to 1.0 bar a lumped on the valve, the choke
#: FL^2 (P1 - FF . Pv), 2.85 bar, does not bind on the design 2.81 bar; it binds when 328E007
#: loses its cold side and 740 reaches the valve at the column's temperature, boiling at the
#: column's pressure. V1 passes no vapour pressure. The design 740 temperature [deg C] and its
#: vapour pressure [bar a]:
LV505_T_IN_DES_C = E007_T740_DES_C
LV505_PV_DES_BARA = liquor_pv_bara(W_S739, LV505_T_IN_DES_C)

# ======================================================================================
# The loops (FIC-328406's data, 741's, are with 328D003's, `unit_328d003`)
# ======================================================================================

#: LIC-328505: DIRECT acting on the level; 1.45, 180 s, set point 50 %. It strokes LV-328505, or,
#: while FIC-328406 is in cascade, sets FIC-328406's set point with LV-328505 shut (decided
#: 2026-09-30, handoff B-50; UD-MR-328-FF-0002 page 2).
LIC_328505_KC = 1.45
LIC_328505_TI_S = 180.0
LIC_328505_SP_PCT = 50.0

#: FT-329401's calibrated span [kg/h] and FIC-329401 on the table's gain per cent of it
#: (decision 10): 0.30 x 100 / 12 000 = 0.0025 %/(kg/h). V1 applies 0.30 per kg/h, the table's
#: number on an engineering-unit basis (the class of B-41).
FT_329401_SPAN_KGH = 12000.0
FIC_329401_KC_TABLE = 0.30
FIC_329401_KC = FIC_329401_KC_TABLE * 100.0 / FT_329401_SPAN_KGH
FIC_329401_TI_S = 100.0
#: Its set-point ceiling [kg/h] (V1, the transmitter's span), V1's design stroke [%] — V1 runs
#: FV-329401 linear from 50 %, which the equivalence harness keeps — and the transmitter's lag [s]
#: (V1 `_fic_flow`).
FIC_329401_SP_HI_KGH = 12000.0
FIC_329401_OP_DES_PCT = 50.0
FT_329401_TAU_S = 5.0

#: FV-329401 on its vendor's trim (decision 108's class, decided 2026-10-15): Metso's DN 200
#: Neldisc, maximum Cv 3050 (`data.control_valves.FV_329401`, item 24), its design stroke where it
#: passes PFD 931's 6495 kg/h on its normal case — the case's own flow, so its printed 26.0 % — and
#: that case's xT, 0.53, in the butterfly's pressure term.
FV_329401_OP_DES_PCT = design_stroke_pct(FV_329401, C004_M931_DES_KGH)
FV_329401_XT = FV_329401.normal_case.xt

#: FV-329401's design pressures [bar a] (handoff B-73, decided 2026-10-02, the Typo Rule): upstream
#: the LP header the operators run, 4.0 bar g (handoff B-69); downstream 328C004's bottom, where
#: 931 enters, at the column's design bubble point. The loop summary rates the butterfly 4.4 ->
#: 3.9 bar a normal; on these pressures V1's butterfly law (`units.steam.steam_valves`) passes the
#: design steam at the design stroke.
FV_329401_P1_DES_BARA = P_LP_BARA
FV_329401_P2_DES_BARA = C004_P_BARA + C004_DP_COL_BAR

#: FFIC-329401's design ratio [t/m3]: LP steam in t/h per m3/h of the desorbers' feed, 735 —
#: 6.495 / 31.4 = 0.2068. Decided 2026-09-30 by the process engineer: the ratio is on 735, as the
#: P&ID and the functional diagram draw it (FFIC-329401 on FIC-328402, which meters 735). V1
#: writes it on 744, where it hangs FIC-328402. Written in the runtime's operand order so the
#: design ratio is exact.
FFIC_329401_RATIO_DES = (C004_M931_DES_KGH / 1000.0) / (M735_DES_KGH / RHO_735_KGM3)

#: FFIC-329401 is a ratio station (UD-MR-329-FF-0002 page 2, RATIOSTN; decided 2026-09-30,
#: handoff B-49): its output, FIC-329401's set point [kg/h], is the ratio set point [t/m3] times
#: the feed [m3/h] times 1000 kg/t. V1 runs a PI on the measured ratio (8.0e5 and 40 s, its own
#: retune). The output 0-12 000 kg/h (FT-329401's span) and the set point 0-0.5 t/m3 are V1's.
FFIC_329401_FACTOR = 1000.0
FFIC_329401_OP_HI_KGH = 12000.0
FFIC_329401_SP_HI = 0.5

# ======================================================================================
# The Kremser stage: how the column's lumped volatility moves with its stripping steam
# ======================================================================================

#: 328C004's stage: 13.98 theoretical stages (O'Connell's 0.635 on 22 trays); its stripping
#: agent the LP steam, its liquid the bottoms; its node the bottom, at the overhead pressure plus
#: the lumped offset.
C004_STAGE = desorber_stage(DES_C004, C004_NTHEO, C004_M931_DES_KGH, C004_M739_DES_KGH,
                            C004_P_BARA + C004_DP_COL_BAR, KINF)

__all__ = [
    "C004_ID_M", "C004_SHELL_M", "C004_VOL_M3", "C004_H_NLL_M", "C004_RHO_KGM3",
    "C004_M_DES_KG", "C004_LEVEL_DES_PCT", "C004_M_FLOOR_KG", "C004_FULL_KG", "C004_DT_DES_K",
    "LT_328505_TAP_LO_M", "LT_328505_SPAN_M", "LT_328505_RHO_KGM3", "LT_328505_SPAN_KG",
    "LT_328505_DES_PCT", "lt_328505_pct",
    "C004_DP_COL_BAR", "C004_AREA_M2", "C004_M931_DH_KJKG", "C004_Q_DES_KW", "C004_MW750_DES",
    "LV505_P2_BARA", "C004_H_DES_M", "C004_HEAD_DES_BAR", "LV505_P1_DES_BARA", "LV505_CHAR",
    "FV_329401_P1_DES_BARA", "FV_329401_P2_DES_BARA",
    "LV505_OP_DES_PCT", "LV505_FL", "LV505_T_IN_DES_C", "LV505_PV_DES_BARA", "LIC_328505_KC", "LIC_328505_TI_S", "LIC_328505_SP_PCT",
    "FT_329401_SPAN_KGH", "FIC_329401_KC_TABLE", "FIC_329401_KC", "FIC_329401_TI_S",
    "FIC_329401_SP_HI_KGH", "FIC_329401_OP_DES_PCT", "FV_329401_OP_DES_PCT", "FV_329401_XT", "FT_329401_TAU_S", "S735_VOL_DES_M3H",
    "RHO_735_KGM3", "FFIC_329401_RATIO_DES", "FFIC_329401_FACTOR", "FFIC_329401_OP_HI_KGH",
    "FFIC_329401_SP_HI", "C004_STAGE",
]
