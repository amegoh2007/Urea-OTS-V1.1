"""328D003 — the ammonia water tank: the design basis.

328D003 is the atmospheric tank that collects the plant's ammonia water. Its three liquid bays
communicate through openings in their baffles:

  * compartment I takes the vacuum train's condensates — PFD 719, 720 and 721 from 324E002,
    324E005 and 324E006, and 759 from 324E007 — and 322P002 draws PFD 744 from it to the LP
    absorber (FI-322402, no control valve);
  * compartment II takes 323C005's bottoms, PFD 343, through 328V001, and the normally closed
    process-condensate recycle 741 (FIC-328406); 328P003 draws from it PFD 735 to 328E007 and
    the desorbers (FIC-328402), 734 (FIC-323401), 791 to 323E011 (FIC-323402) and the spare 793
    (FIC-328405);
  * compartment III has no piped stream of its own: it is the shared surge volume the other two
    level into.

    719 + 720 + 721 + 759 --> I  --744--> 322P002 (FI-322402)
                              |
                             III  (the common accumulation baffle)
                              |
          343 (+ 741)  -----> II --735 (FIC-328402) / 734 / 791 / 793--> 328P003

Sources
-------
* ``Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md`` — streams 343, 719, 720, 721, 734,
  735, 739, 741, 744, 759, 791 and 793: flows, temperatures, densities (PFD-21 / PFD-22).
* ``References/323D003 Datasheets.md``, its approved correction of 2026-07-27 — the owner-approved
  liquid capacities of the three compartments and the stream mapping. The rest of that file is a
  superseded secondary analysis and is not used.
* ``References/Master_PID_Tuning_Constants.md`` — the five loops' gains and integral times. Each
  gain is read per cent of its transmitter's span (decision 10): FIC-328402 decided 2026-09-27
  (handoff B-38), where V1 runs 0.06; FIC-323401, FIC-323402, FIC-328405 and FIC-328406 decided
  2026-09-30 (handoff B-41), where V1 applies the table's number per kg/h.
* Uhde loop summaries UD-MR-328-EC-0001 rev 1 (loops F 328402, F 328405, F 328406) and
  UD-MR-323-EC-0001 rev 1 (loops F 323401, F 323402) — the transmitters' calibrated ranges.
* V1 ``backend/main.py``, the 328D003 constants (1282, 1302-1307, 1938-1986), the loop densities
  (1745-1756, 5966-5973) and the loop seeds (6947-6980, 7107-7127). Each value carries its
  provenance.
* Flowserve's calculation sheets for FV-323401, FV-323402, FV-328402, FV-328405 and FV-328406
  (`ureasim.data.control_valves`) — the five valves' trims, their design strokes and full-stroke
  capacities (handoff B-44, decided 2026-09-30).
"""

from __future__ import annotations

from ureasim.data.control_valves import (
    FV_323401,
    FV_323402,
    FV_328402,
    FV_328405,
    FV_328406,
    design_stroke_pct,
    full_stroke_m3h,
)
from ureasim.data.unit_323c005 import C005_M756_DES_KGH
from ureasim.data.unit_323e011 import E011_M402_DES_KGH

# ======================================================================================
# Compartment I: the vacuum train's condensates [kg/h] and their temperatures [deg C]
# ======================================================================================

#: PFD 719, 324E002's condensate, and 720, 324E005's.
D003_M719_DES_KGH = 26768.0
D003_T719_C = 45.0
D003_M720_DES_KGH = 2758.0
D003_T720_C = 40.0

#: PFD 721, 324E006's condensate.
D003_M721_DES_KGH = 1763.0
D003_T721_C = 41.0

#: PFD 759, 324E007's condensate — the P&ID's "condensed gases in bottom of shell side of
#: 324E007 is discharged to 328D003", and 324E007's own closure 717 = 759 + 722 (V1 AUDIT B10).
D003_M759_DES_KGH = 190.0
D003_T759_C = 55.0

#: PFD 744, 322P002's draw to the LP absorber: V1 writes it as a split of the 756 solvent,
#: 31 478 / 33 358 of it, which evaluates to the PFD's 31 478 exactly.
PHI744 = 31478.0 / C005_M756_DES_KGH
M744_DES_KGH = PHI744 * C005_M756_DES_KGH

# ======================================================================================
# Compartment II: 343 in, the 328P003 header out [kg/h]
# ======================================================================================

#: PFD 735, compartment II to 328E007 and 328C002's feed 738 (V1 ``R328_C002_M738_DES``).
M735_DES_KGH = 31114.0

#: PFD 735's volume flow [m3/h] and the density it implies [kg/m3], 990.9: the desorbers' feed,
#: which FT-328402 meters (handoff B-39).
S735_VOL_DES_M3H = 31.4
RHO_735_KGM3 = M735_DES_KGH / S735_VOL_DES_M3H

#: PFD 734, FIC-323401's leg, and 791, FIC-323402's wash to 323E011 — 1534 kg/h each.
M401_DES_KGH = 1534.0
M402_DES_KGH = E011_M402_DES_KGH

#: PFD 793, FIC-328405's normally closed spare off the same header: 0 kg/h at design.
S793_M_DES_KGH = 0.0

#: PFD 739, 328C004's bottoms, the condensate 741 is diverted from (V1 ``R328_C004_M739_DES``,
#: its 328C004 balance, which evaluates to the PFD's 33 724 exactly).
C004_M739_DES_KGH = 33724.0

#: PFD 741, the purified process-condensate recycle: normally closed (0 kg/h), 40 C.
T741_C = 40.0

# ======================================================================================
# The tank
# ======================================================================================

#: The owner-approved liquid capacities of the three compartments [m3], 490 in all. They
#: supersede the 561 m3 geometric envelope, which includes the roof and headspace.
D003_VOL_I_M3 = 18.0
D003_VOL_II_M3 = 43.0
D003_VOL_III_M3 = 429.0
D003_VOL_TOTAL_M3 = D003_VOL_I_M3 + D003_VOL_II_M3 + D003_VOL_III_M3

#: The ammonia water's density [kg/m3], V1's (PFD 343, 734 and 735 print 992.2 to 992.4).
D003_RHO_KGM3 = 992.0

#: Each compartment full [kg], and at design, half full [kg].
D003_MI_FULL_KG = D003_VOL_I_M3 * D003_RHO_KGM3
D003_MII_FULL_KG = D003_VOL_II_M3 * D003_RHO_KGM3
D003_MIII_FULL_KG = D003_VOL_III_M3 * D003_RHO_KGM3
D003_MI_DES_KG = D003_MI_FULL_KG * 0.50
D003_MII_DES_KG = D003_MII_FULL_KG * 0.50
D003_MIII_DES_KG = D003_MIII_FULL_KG * 0.50

#: V1's floor on an active compartment's holdup [kg], the literal of its ``max(..., 1.0)``.
D003_M_FLOOR_KG = 1.0

#: The PFD's rounding [kg/h], which V1 books so each active compartment closes at design:
#: compartment I takes in 31 479 and gives 31 478; compartment II 34 180 and 34 182.
D003_ROUNDING_I_KGH = 1.0
D003_ROUNDING_II_KGH = 2.0

#: The liquor's heat capacity at design [kJ/(kg K)], V1's ``A328_CP``, the anchor its
#: ``aqueous_cp`` departs from with the live temperature.
D003_CP = 4.0

#: The compartments' design temperatures [deg C]: I at PFD 744's 44 C, II at 343's 56 C, and
#: III, which has no feed of its own, at the holdup-weighted mean of the two, so it brings no
#: heat anchor of its own.
D003_TI_C = 44.0
D003_TII_C = 56.0
D003_TIII_C = ((D003_MI_DES_KG * D003_TI_C + D003_MII_DES_KG * D003_TII_C)
               / (D003_MI_DES_KG + D003_MII_DES_KG))

#: The temperature 343 is charged at [deg C]: 328V001's, which V1 holds at compartment II's
#: design (``A328_D003_V001_T``) whatever 323C005's liquor does (handoff B-31).
D003_T343_C = D003_TII_C

#: Compartment I's heat term [kJ/kg of inflow]: what closes compartment I's balance at PFD 744's
#: 44 C on the four condensates — back-solved so the design holds, as V1 writes it. V1 names it
#: the carbamate-formation exotherm, 2 NH3 + CO2 -> carbamate, but the condensates arrive 0.40 K
#: above 44 C on average (719, at 45 C, dominates), so the back-solve is a sink: -1.593 kJ/kg,
#: 13.9 kW at design.
D003_LAM_I_KJKG = -D003_CP * (
    D003_M719_DES_KGH * (D003_T719_C - D003_TI_C)
    + D003_M720_DES_KGH * (D003_T720_C - D003_TI_C)
    + D003_M721_DES_KGH * (D003_T721_C - D003_TI_C)
    + D003_M759_DES_KGH * (D003_T759_C - D003_TI_C)
    ) / (D003_M719_DES_KGH + D003_M720_DES_KGH + D003_M721_DES_KGH + D003_M759_DES_KGH)

# ======================================================================================
# The five flow loops on the tank's draws: all VOLUMETRIC, in m3/h
# ======================================================================================

#: The flow transmitters' lag [s], V1 ``_fic_flow``'s default, on all five.
FT_TAU_S = 5.0

#: The densities each loop's volume is read on [kg/m3]: 734 and 793 at PFD 734's, 791 at its
#: own row's (both 992.4), 741 at its row's 992.42, 735 at RHO_735_KGM3 above, and 744 —
#: FI-322402's, no loop's since B-39 — back-solved from the PFD's own 31 478 kg/h at 31.4 m3/h,
#: 1002.48 (the row prints 1002).
RHO_401_KGM3 = 992.4
RHO_791_KGM3 = 992.4
RHO_741_KGM3 = 992.42
S744_VOL_DES_M3H = 31.4
RHO_744_KGM3 = M744_DES_KGH / S744_VOL_DES_M3H

#: The two valves shut at design, anchored on what each passes wide open [kg/h] (handoff B-44,
#: decided 2026-09-30): FV-328405, Kvs 1.6, 3.23 m3/h on its normal case; FV-328406, Kvs 100,
#: 77.8 m3/h on its. V1 took one branch's flow, 1534 kg/h, for 793 and the whole of 739,
#: 33 724 kg/h, for 741 — each valve's design ask, not its capacity.
S793_CAP_KGH = full_stroke_m3h(FV_328405) * RHO_401_KGM3
S741_CAP_KGH = full_stroke_m3h(FV_328406) * RHO_741_KGM3

#: The valves' trims — Valtek modified equal percentage, all five (handoff B-44).
FV_323401_CHAR = FV_323401.characteristic
FV_323402_CHAR = FV_323402.characteristic
FV_328402_CHAR = FV_328402.characteristic
FV_328405_CHAR = FV_328405.characteristic
FV_328406_CHAR = FV_328406.characteristic

#: The four loops' gains as the DCS table gives them [% of output per % of span]. V1 applied
#: each per kg/h and carried it to m3/h times the density, 0.10 x 992.4 = 99.24 %/(m3/h) on
#: FIC-323401, and so on; on FIC-328406 that put the discrete loop gain at 4.96, and FV-328406
#: slammed between 0 and 100 % every tick in AUTO (handoff B-41, decided 2026-09-30).
FIC_323401_KC_TABLE = 0.1
FIC_323402_KC_TABLE = 0.1
FIC_328405_KC_TABLE = 0.2
FIC_328406_KC_TABLE = 0.75

#: The transmitters' calibrated ranges [m3/h], each 0 to the value, volume flow. Source: Uhde loop
#: summaries, sheet 1/2, line D07 (vendor archive, scanned, read from the page images):
#: UD-MR-323-EC-0001 rev 1 — F 323401, 0-4 m3/h, "AW to 323E003 LP Carb. Condenser", line
#: 50-AW3-328054, 2.15 m3/h normal; F 323402, 0-3.3 m3/h, "AW to 323E011 Flash Tank Cond.", line
#: 50-AW3-328060, 2.15 m3/h normal. UD-MR-328-EC-0001 rev 1 — F 328405, 0-2.3 m3/h, "AW to 328E004
#: Reflux Condenser", line 80-AW3-328081, 1.02 m3/h normal; F 328406, 0-60 m3/h, "CPP outl.
#: 328E001 Recycle Cooler", line 100-CPP3-328112, 36.6 m3/h normal, 40 C, 992.0 kg/m3.
FT_323401_SPAN_M3H = 4.0
FT_323402_SPAN_M3H = 3.3
FT_328405_SPAN_M3H = 2.3
FT_328406_SPAN_M3H = 60.0

#: FIC-323401, 734: the table's 0.10 on its 0-4 m3/h span, 2.5 %/(m3/h), and 7 s; the set point
#: up to 2000 kg/h.
FIC_323401_KC = FIC_323401_KC_TABLE * 100.0 / FT_323401_SPAN_M3H
FIC_323401_TI_S = 7.0
FIC_323401_SP_HI_M3H = 2000.0 / RHO_401_KGM3

#: FV-323401's design stroke [%]: where its Kvs 4 passes PFD 734 on its normal case, 49.26
#: (handoff B-44). V1's 50.
FIC_323401_OP_DES_PCT = design_stroke_pct(FV_323401, M401_DES_KGH)

#: FIC-323402, 791: the table's 0.10 on 0-3.3 m3/h, 3.03 %/(m3/h), and 7 s; the set point up to
#: 6000 kg/h.
FIC_323402_KC = FIC_323402_KC_TABLE * 100.0 / FT_323402_SPAN_M3H
FIC_323402_TI_S = 7.0
FIC_323402_SP_HI_M3H = 6000.0 / RHO_791_KGM3

#: FV-323402's design stroke [%], its Kvs 4 on PFD 791, 38.23 (handoff B-44). V1's 50.
FIC_323402_OP_DES_PCT = design_stroke_pct(FV_323402, M402_DES_KGH)

#: FIC-328405, 793: the table's 0.20 on 0-2.3 m3/h, 8.70 %/(m3/h), and 15 s; shut at design,
#: anchored on its full-stroke capacity. The set point up to one branch's flow, V1's limit.
FIC_328405_KC = FIC_328405_KC_TABLE * 100.0 / FT_328405_SPAN_M3H
FIC_328405_TI_S = 15.0
FIC_328405_SP_HI_M3H = M402_DES_KGH / RHO_401_KGM3
FIC_328405_OP_DES_PCT = 0.0
FIC_328405_OP_FULL_PCT = 100.0

#: FIC-328406, 741: the table's 0.75 on 0-60 m3/h, 1.25 %/(m3/h), and 80 s; in MAN and shut at
#: design. 328C004 steps it: 741 leaves the column's bottoms ahead of LV-328505 (handoff B-50).
#: The set point up to FT-328406's span, FIC-328406:MAX, onto which LIC-328505's output is scaled
#: in cascade (decided 2026-09-30, B-50): V1's limit, the whole of 739 (34.0 m3/h), would hold the
#: recycle below the column's design bottoms.
FIC_328406_KC = FIC_328406_KC_TABLE * 100.0 / FT_328406_SPAN_M3H
FIC_328406_TI_S = 80.0
FIC_328406_SP_HI_M3H = FT_328406_SPAN_M3H
FIC_328406_OP_FULL_PCT = 100.0

#: FIC-328402's gain as the DCS table gives it [% of output per % of span], 0.75, 60 s. V1
#: applied it per kg/h, found that unstable and ran 0.06 instead (its AUDIT G16).
FIC_328402_KC_TABLE = 0.75
FIC_328402_TI_S = 60.0

#: FT-328402's calibrated range [m3/h]: 0 to 70, volume flow, a vortex meter. Source: Uhde loop
#: summary UD-MR-328-EC-0001 rev 1, loop F 328402, sheet 1/2, line D07 (vendor archive, scanned,
#: read from the page image). The same sheet puts the loop on 328P003's discharge, line
#: 100-AW3-328062, at 56 C and 32.0 m3/h normal — PFD 735's service, not 744's (handoff B-39).
FT_328402_SPAN_M3H = 70.0

#: FIC-328402, 735 (decided 2026-10-09, handoff B-39; V1 hangs it on 744): the table's gain
#: rescaled to the m3/h the loop runs in, 0.75 %/% on a 70 m3/h span, 1.071 %/(m3/h). V1 runs
#: 0.06 x 1002.48 = 60.15 %/(m3/h), 56 times stronger; the port departs from it by decision of
#: 2026-09-27 (handoff B-38, As-Built §XXXV.9). The set point up to V1's 60 000 kg/h, on 735.
FIC_328402_KC = FIC_328402_KC_TABLE * 100.0 / FT_328402_SPAN_M3H
FIC_328402_SP_HI_M3H = 60000.0 / RHO_735_KGM3

#: FV-328402's design stroke [%], its Kvs 63 on PFD 735 (handoff B-44, B-39) — the service
#: Flowserve's sheet sizes it for, 31.4 m3/h at 56 C. V1's 50.
FIC_328402_OP_DES_PCT = design_stroke_pct(FV_328402, M735_DES_KGH)

#: All five loops: no derivative (Td 0), REVERSE action on the flow.
FIC_TD_S = 0.0

__all__ = [
    "D003_M719_DES_KGH", "D003_T719_C", "D003_M720_DES_KGH", "D003_T720_C",
    "D003_M721_DES_KGH", "D003_T721_C", "D003_M759_DES_KGH", "D003_T759_C", "PHI744",
    "M744_DES_KGH", "M735_DES_KGH", "S735_VOL_DES_M3H", "RHO_735_KGM3", "M401_DES_KGH", "M402_DES_KGH", "S793_M_DES_KGH",
    "S793_CAP_KGH", "C004_M739_DES_KGH", "S741_CAP_KGH", "T741_C", "FV_323401_CHAR",
    "FV_323402_CHAR", "FV_328402_CHAR", "FV_328405_CHAR", "FV_328406_CHAR",
    "D003_VOL_I_M3", "D003_VOL_II_M3", "D003_VOL_III_M3", "D003_VOL_TOTAL_M3", "D003_RHO_KGM3",
    "D003_MI_FULL_KG", "D003_MII_FULL_KG", "D003_MIII_FULL_KG", "D003_MI_DES_KG",
    "D003_MII_DES_KG", "D003_MIII_DES_KG", "D003_M_FLOOR_KG", "D003_ROUNDING_I_KGH",
    "D003_ROUNDING_II_KGH", "D003_CP", "D003_TI_C", "D003_TII_C", "D003_TIII_C", "D003_T343_C",
    "D003_LAM_I_KJKG", "FT_TAU_S", "RHO_401_KGM3", "RHO_791_KGM3", "RHO_741_KGM3",
    "S744_VOL_DES_M3H", "RHO_744_KGM3", "FIC_323401_KC_TABLE", "FIC_323402_KC_TABLE",
    "FIC_328405_KC_TABLE", "FIC_328406_KC_TABLE", "FT_323401_SPAN_M3H", "FT_323402_SPAN_M3H",
    "FT_328405_SPAN_M3H", "FT_328406_SPAN_M3H", "FIC_323401_KC", "FIC_323401_TI_S",
    "FIC_323401_SP_HI_M3H", "FIC_323401_OP_DES_PCT", "FIC_323402_KC", "FIC_323402_TI_S",
    "FIC_323402_SP_HI_M3H", "FIC_323402_OP_DES_PCT", "FIC_328405_KC", "FIC_328405_TI_S",
    "FIC_328405_SP_HI_M3H", "FIC_328405_OP_DES_PCT", "FIC_328405_OP_FULL_PCT", "FIC_328406_KC",
    "FIC_328406_TI_S", "FIC_328406_SP_HI_M3H", "FIC_328406_OP_FULL_PCT", "FIC_328402_KC_TABLE",
    "FT_328402_SPAN_M3H", "FIC_328402_KC", "FIC_328402_TI_S", "FIC_328402_SP_HI_M3H",
    "FIC_328402_OP_DES_PCT", "FIC_TD_S",
]
