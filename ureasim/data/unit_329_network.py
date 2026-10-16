"""Unit 329's steam network — its drums, its valves, its controllers and its safety valves.

What this is
------------
The equipment `ureasim.units.steam` integrates: the three drums as lumped saturated vapour
capacitances over condensate inventories, the eleven valves between them, the six pressure and
three level controllers, and the drums' certified safety valves. The header pressures, the PFD's
rows, the users and the design closure are `ureasim.data.unit_329`'s.

Decided classes applied at the port (§5 rule 7, As-Built Part LIV)
------------------------------------------------------------------
* **Decision 47**: PV-329204 anchored on PFD 902's 57 989 kg/h, LV-329502 on 904's, where V1
  anchors both on the stripper's 39 400 kW / 1850 kJ/kg.
* **Decision 23**: LV-329502, LV-329503, LV-329504, PV-329205A and PV-329205B on Flowserve's trims,
  their design strokes where their rated capacities pass the design flows on the normal cases
  (PV-329205B, shut at design, on its full-stroke capacity there); the butterflies — PV-329204,
  PV-329207A / B / C, HV-329601, HV-329602 — keep V1's anchored law (no Kvs in the archive).
* **Decision 108's class** (decided 2026-10-15): PV-329204, PV-329207A and PV-329207B on Metso's
  Neldisc trims (`ureasim.data.control_valves`, sheets 28-30), each on its printed points and its
  normal case's xT — PV-329204 and PV-329207B from the strokes where they pass PFD 902 and 932,
  PV-329207A, shut at design, on its full-stroke capacity on its normal case. PV-329207C, HV-329601
  and HV-329602 are on no sheet in the archive and keep V1's law; the harness keeps V1's for all.
* **§4's order** for the four butterflies V1 gives literal coefficients no document carries
  (HV-329601 its own sizing of PV-329204, PV-329207A 3.0, PV-329207C and HV-329602 2.0): each
  wide open passes its loop summary's maximum case. HV-329601 on V1's coefficient vented 288 t/h
  of 19.7 bar a steam through its DN 80 body; its sheet rates 8 t/h. That the maximum case is
  passed at full stroke is an assumption (Open data gaps, with their Kvs).
* **Decision 31**: the two drum-to-drum letdowns handed their saturated condensate's vapour
  pressure, so they choke on FL^2 (P1 - FF Pv) as Flowserve sized them; V1 passes none.
* **Decisions 10 and 21**: PIC-329204 and the PIC-329207 trio on the tuning table per cent of their
  transmitters' spans, V1's retune of the trio dropped; LIC-329503 and LIC-329504 on their rows.
  PIC-329205 and LIC-329502 have no row and keep V1's tuning (handoff B-52's class, Section C).
* **Decision 33**: each drum's inventory over its whole vessel, heads included, its level read
  between its transmitter's taps; **decision 11**: a valve draws at most what its drum holds.
* **Decision 32**: SV32951, SV32952 and SV32978-81 on Sempell's certified capacities.
* **Decisions 26, 27 and 39**: Uhde's functional diagrams for unit 329 (UD-MR-329-FF-0002, read
  from the scans) drawn as built — trip 21.2 resets PIC-329204's set point to 10 bar g and forces
  HV-329601 open above 12 bar g, shut for 3 s below it. Sheet 5 also writes PV-329207A's and
  PV-329207C's outputs under 3 % to their valves as shut; measured on the model that cut-off makes
  PV-329207C chatter shut and open on alternate ticks (0 and 970 kg/h) as its controller settles
  near it, so it is not wired (the classes' "once measured stable"; handoff Section C).

Sources
-------
V1 ``backend/steam_system.py`` (the geometry it read from the vendor drawings, the K values, the
tunings); 329D005's and 329D009's as-built GAs, UD-AU-329-DZ-0001-005 rev 02 and
UD-AU-329-DZ-0003-005 rev 04 (scanned, read: LT-329502 on N10A / N10B 750 mm above and below the
axis, LT-329503 on N10A / N10B 375 mm either side, 2:1 heads — their capacities 13.59 and 7.91 m3
against the GAs' 13.8 and 8); Flowserve's calculation sheets (`ureasim.data.control_valves`);
``References/Master_PID_Tuning_Constants.md``; Uhde's loop summaries UD-MR-329-EC-0001 (PT-329204
0-40 bar g, PT-329207 0-6 bar g); Sempell's orifice selections (`ureasim.data.relief_devices`).
"""

from __future__ import annotations

from ureasim.core.units_of_measure import ATM_BARA, R_GAS_J
from ureasim.data.control_valves import (
    LV_329502,
    LV_329503,
    LV_329504,
    PV_329204,
    PV_329205A,
    PV_329205B,
    PV_329207A,
    PV_329207B,
    design_stroke_pct,
    full_stroke_m3h,
)
from ureasim.data.relief_devices import RELIEF_DEVICES, RELIEF_SIZING
from ureasim.data.unit_329 import (
    M_913_DES_KGH,
    M_916_DES_KGH,
    P_HP_BARA,
    P_LP_BARA,
    P_MP_BARA,
    P_SUP_BARA,
    P_TURBINE_OUT_BARA,
    STEAM_MW,
    STEAM_PFD_KGH,
)
from ureasim.thermo.iapws import psat_bara, v_vapour_sat_m3kg
from ureasim.thermo.water_steam import vapour_capacitance_kg_bar

# ======================================================================================
# The drums
# ======================================================================================

#: 322D001A/B, the LP drums, two vertical vessels on one node: ID 3470 mm, 5300 mm between
#: tangent lines, 2:1 ellipsoidal heads, condensate 919.36 kg/m3 (UD-AU-322-EC-0009 p2); NLL
#: 1050 mm above the bottom tangent line, LICA-329504's taps N8B / N8A at 300 and 1800 mm (GA
#: UD-AU-322-DZ-0009-006 rev 05). V1 writes pi to eight figures. Source: V1 `steam_system.py`.
D001_ID_M = 3.470
D001_CYL_M = 5.300
N_D001 = 2
D001_NLL_M = 1.050
RHO_D001_L = 919.36
D001_TAPS_M = (0.300, 1.800)
A_D001_M2 = 0.78539816 * D001_ID_M ** 2
V_D001_HEAD_M3 = 3.14159265 * D001_ID_M ** 3 / 24.0
V_D001_M3 = A_D001_M2 * D001_CYL_M + 2.0 * V_D001_HEAD_M3

#: 329D005, the HP saturator, horizontal: ID 1760 mm x 5000 mm, 13.8 m3 as built, NLL on the
#: axis; 329D009, the 9-bar drum, horizontal: ID 1776 mm x 2600 mm, 8 m3 on its name plate, NLL on
#: the axis. Their condensate densities [kg/m3]. Source: V1 `steam_system.py` (the DDSs, the GAs).
D005_ID_M, D005_LEN_M, D005_CAP_M3, RHO_D005_L = 1.760, 5.000, 13.80, 850.25
D009_ID_M, D009_LEN_M, D009_CAP_M3, RHO_D009_L = 1.776, 2.600, 8.00, 892.15

#: LT-329502's and LT-329503's taps above and below their drums' axes [m] (the GAs, view A).
D005_TAP_HALF_M = 0.750
D009_TAP_HALF_M = 0.375

#: The vapour spaces the capacitances are on [m3]: 322D001's two drums above their NLL, the
#: horizontal drums half their capacity. Source: V1 `steam_system.py`.
V_D001_VAP_M3 = N_D001 * (V_D001_M3 - (V_D001_HEAD_M3 + A_D001_M2 * D001_NLL_M))
V_D005_VAP_M3 = 0.50 * D005_CAP_M3
V_D009_VAP_M3 = 0.50 * D009_CAP_M3

#: Each node's capacitance at its design pressure [kg/bar]. Source: V1 C_MP, C_LP, C_9.
C_MP_KG_BAR = vapour_capacitance_kg_bar(V_D005_VAP_M3, P_HP_BARA)
C_LP_KG_BAR = vapour_capacitance_kg_bar(V_D001_VAP_M3, P_LP_BARA)
C_9_KG_BAR = vapour_capacitance_kg_bar(V_D009_VAP_M3, P_MP_BARA)

#: V1's kilograms per 100 % of each level span (the linear chord at mid-level for the two
#: horizontal drums) [kg]. Source: V1 MSPAN_502, MSPAN_503, MSPAN_504.
MSPAN_502_KG = RHO_D005_L * (D005_ID_M * D005_LEN_M) * (2.0 * D005_TAP_HALF_M)
MSPAN_503_KG = RHO_D009_L * (D009_ID_M * D009_LEN_M) * (2.0 * D009_TAP_HALF_M)
MSPAN_504_KG = RHO_D001_L * (N_D001 * A_D001_M2) * (D001_TAPS_M[1] - D001_TAPS_M[0])

#: The inventory floor a level valve leaves in its drum [kg] (decision 11's heel).
DRUM_M_FLOOR_KG = 1.0

# ======================================================================================
# The butterflies, on V1's anchored law [(kg/s) / sqrt(bar)]
# ======================================================================================

#: PV-329204 (supply -> 329D005), sized so its 50 % seed passes PFD 902's 57 989 kg/h at 25 ->
#: 19.7 bar a (decision 47; V1 sizes it on the stripper's 39 400 / 1850 = 21.297 kg/s).
PV204_BIAS_PCT = 50.0
K_902 = (STEAM_PFD_KGH["902"] / 3600.0) / ((PV204_BIAS_PCT / 100.0)
                                         * (P_SUP_BARA - P_HP_BARA) ** 0.5)

#: HV-329601, 329D005's vent to the 329D010 silencer, DN 80: wide open, its loop summary's
#: maximum case, 8000 kg/h from 17.0 to 1.5 bar a (H 329601, UD-MR-329-EC-0001 rev 1, read from the
#: scan: 1500 / 1500 / 8000 kg/h from 25.0 / 19.9 / 17.0 bar a, 1.5 bar a out on every case). V1
#: gives it its own sizing of PV-329204, (39 400 / 1850) / (0.5 sqrt(5.3)), 288 t/h at 19.7 bar a.
HV601_P1_DES_BARA, HV601_P2_DES_BARA = 17.0, 1.5
K_HV601 = (8000.0 / 3600.0) / (HV601_P1_DES_BARA - HV601_P2_DES_BARA) ** 0.5

#: PV-329207C (supply -> LP header, PIC-329207C) and HV-329602 (its parallel hand valve), DN 150,
#: both shut at design: wide open, their loop summaries' maximum case, 32 000 kg/h from 20.0 to 7.0
#: bar a (P 329207C, H 329602). V1: K 2.0 each.
P963_P1_DES_BARA, P963_P2_DES_BARA = 20.0, 7.0
K_963 = (32000.0 / 3600.0) / (P963_P1_DES_BARA - P963_P2_DES_BARA) ** 0.5
K_HV602 = K_963

#: PV-329207A (LP header -> atmosphere), DN 300: wide open, its loop summary's maximum case,
#: 65 000 kg/h from 4.0 to 2.0 bar a (P 329207A). V1: K 3.0, 21.6 t/h wide open from 5.013 bar a.
P207A_P1_DES_BARA, P207A_P2_DES_BARA = 4.0, 2.0
K_207A = (65000.0 / 3600.0) / (P207A_P1_DES_BARA - P207A_P2_DES_BARA) ** 0.5

#: PV-329207B (LP header -> turbine 320MT02, PFD 932), its 50 % seed passing 16 707 kg/h at 5.013
#: -> 3.9 bar a. Source: V1 M_TURBINE_DES, BIAS_207B_PCT, K_207B.
M_TURBINE_DES_KGS = STEAM_PFD_KGH["932"] / 3600.0
BIAS_207B_PCT = 50.0
K_207B = M_TURBINE_DES_KGS / ((BIAS_207B_PCT / 100.0) * (P_LP_BARA - P_TURBINE_OUT_BARA) ** 0.5)

# ======================================================================================
# The butterflies on Metso's trims (decision 108's class, decided 2026-10-15)
# ======================================================================================

#: PV-329204 (supply -> 329D005, PFD 902): DN 250 balanced Neldisc, FpCv 1604.25 (item 28); its
#: design stroke where it passes PFD 902's 57 989 kg/h on its normal case — the case's own flow, so
#: its printed 44.1 % — anchored on 25 -> 19.7 bar a, and the case's xT. V1: 50 % on K_902.
PV204_OP_DES_PCT = design_stroke_pct(PV_329204, STEAM_PFD_KGH["902"])
PV204_XT = PV_329204.normal_case.xt

#: PV-329207A (LP header -> atmosphere), shut at design: DN 300 balanced Neldisc, Cv 3880 (item 29
#: rev 01); its full stroke passes 165 770 kg/h on its normal case, 22 000 kg/h at 28.7 % from 4.4 to
#: 1.5 bar a, xT 0.57 (decision 23's class, as PV-329205B). V1: K 3.0, 21.6 t/h wide open.
PV207A_FULL_KGS = full_stroke_m3h(PV_329207A) * PV_329207A.normal_case.rho / 3600.0
PV207A_P1_DES_BARA = PV_329207A.normal_case.p1_bara
PV207A_P2_DES_BARA = PV_329207A.normal_case.p2_bara
PV207A_XT = PV_329207A.normal_case.xt

#: PV-329207B (LP header -> turbine 320MT02, PFD 932): DN 250 balanced Neldisc in a DN 300 line,
#: FpCv 2447.16 (item 30); its design stroke where it passes PFD 932's 16 707 kg/h on its normal
#: case (17 707 kg/h at 58 %), anchored on 5.013 -> 3.9 bar a, and the case's xT. V1: 50 % on K_207B.
PV207B_OP_DES_PCT = design_stroke_pct(PV_329207B, STEAM_PFD_KGH["932"])
PV207B_XT = PV_329207B.normal_case.xt

# ======================================================================================
# The vendor globes (decision 23)
# ======================================================================================

#: PV-329205A (supply -> 329D009, PFD 903): Valtek modified equal percentage, Kvs 100, xT 0.662;
#: its design stroke 19.55 % passes 1754 kg/h on Flowserve's normal case. V1: 50 % on its K.
M_903_DES_KGS = STEAM_PFD_KGH["903"] / 3600.0

#: 329D009's water 903's superheat boils at design [kg/s], 275 kg/h, written as V1 writes
#: M_ATTEMPER9_DES (907 - 903 - 906, each in kg/s), so the two agree to the bit.
DS9_DES_KGS = (STEAM_PFD_KGH["907"] / 3600.0 - STEAM_PFD_KGH["903"] / 3600.0
               - STEAM_PFD_KGH["906"] / 3600.0)
PV205A_OP_DES_PCT = design_stroke_pct(PV_329205A, STEAM_PFD_KGH["903"])
PV205A_XT = PV_329205A.normal_case.xt

#: PV-329205B (329D009 -> LP header, PFD 960), shut at design: its full stroke passes 10 486 kg/h
#: on its normal case, 8.9 -> 4.4 bar a at 175 C, xT 0.673. V1: K 2.0 linear.
PV205B_FULL_KGS = full_stroke_m3h(PV_329205B) * PV_329205B.normal_case.rho / 3600.0
PV205B_P1_DES_BARA = PV_329205B.normal_case.p1_bara
PV205B_P2_DES_BARA = PV_329205B.normal_case.p2_bara
PV205B_XT = PV_329205B.normal_case.xt

#: The three level valves' design strokes [%], flows [kg/s] and FL. LV-329502 passes 904 on
#: Valtek's modified equal percentage (86.87 %), LV-329503 913 linear (58.88 %), LV-329504 916
#: modified equal percentage (48.26 %). V1: linear from 50 %.
M_502_DES_KGS = STEAM_PFD_KGH["904"] / 3600.0
M_503_DES_KGS = M_913_DES_KGH / 3600.0
M_504_DES_KGS = M_916_DES_KGH / 3600.0
LV502_OP_DES_PCT = design_stroke_pct(LV_329502, STEAM_PFD_KGH["904"])
LV503_OP_DES_PCT = design_stroke_pct(LV_329503, M_913_DES_KGH)
LV504_OP_DES_PCT = design_stroke_pct(LV_329504, M_916_DES_KGH)
LV502_FL = LV_329502.normal_case.fl
LV503_FL = LV_329503.normal_case.fl
LV504_FL = LV_329504.normal_case.fl

# ======================================================================================
# The controllers
# ======================================================================================

#: PT-329204's and PT-329207's spans [bar] (UD-MR-329-EC-0001: 0-40 and 0-6 bar g).
PT_329204_SPAN_BAR = 40.0
PT_329207_SPAN_BAR = 6.0

#: PIC-329204 on 329D005 (direct PI about its seed): the table's 1.80 and 100 s on PT-329204's
#: span (decision 10), 4.5 %/bar; V1 takes the 1.80 in %/bar. The integral holds at most 50 %
#: either side (V1 I204_CLAMP).
PIC_329204_KC_TABLE = 1.80
PIC_329204_TI_S = 100.0
PIC_329204_KC = PIC_329204_KC_TABLE * 100.0 / PT_329204_SPAN_BAR
PIC_329204_KI = PIC_329204_KC / PIC_329204_TI_S
PIC_329204_I_AUTHORITY_PCT = 50.0

#: Trip 21.2 (UD-MR-329-FF-0002 sheet 3): PIC-329204's set point to 10 bar g; HV-329601 forced
#: open above 12 bar g and shut for 3 s when 329D005 falls below it, then the operator's [bar a,
#: s]. The functional diagram writes PT-329204's range unit, bar g; on the standard atmosphere
#: (handoff B-6, decided 2026-10-07).
TRIP_212_SP_BARA = 10.0 + ATM_BARA
HV601_FORCE_BARA = 12.0 + ATM_BARA
HV601_SHUT_PULSE_S = 3.0

#: PIC-329205's split range on 329D009: proportional, 40 % per bar about the set point, PV-329205A
#: closing first, PV-329205B opening once A is shut — Uhde's two characteristics about OUTP 50 %
#: (sheet 4). No table row: V1's gain (handoff Section C, B-52's class).
P_9_SP_BARA = P_MP_BARA
K_PIC_9 = 40.0

#: The PIC-329207 trio on the LP header (sheet 5): B on the master set point exporting to the
#: turbine, A venting at master + 0.1 bar, C admitting at master - 0.1. The table's gains on
#: PT-329207's span (decisions 10, 21): A 6.00 and 150 s, B 4.00 and 150 s, C 4.00 and 200 s; V1
#: runs all three at its own 24 %/bar and 0.28.
DB_LP_BAR = 0.1
PIC_329207_KC_TABLE = {"A": 6.00, "B": 4.00, "C": 4.00}
PIC_329207_TI_S = {"A": 150.0, "B": 150.0, "C": 200.0}
PIC_329207_KC = {k: v * 100.0 / PT_329207_SPAN_BAR for k, v in PIC_329207_KC_TABLE.items()}
PIC_329207_KI = {k: PIC_329207_KC[k] / PIC_329207_TI_S[k] for k in PIC_329207_KC}

#: The level loops, velocity PI on per cent of level: LIC-329503 2.00 and 200 s, LIC-329504 2.50
#: and 500 s (the table); LIC-329502 has no row and keeps V1's 2.5 and 90 s. The design level, 50 %.
LEVEL_SP_DES_PCT = 50.0
LIC_TUNING = {"LIC-329502": (2.5, 90.0), "LIC-329503": (2.00, 200.0), "LIC-329504": (2.50, 500.0)}

# ======================================================================================
# The safety valves (decision 32)
# ======================================================================================


def _relief(tag: str) -> dict:
    """A drum's safety valve: set, reseat [bar a], certified capacity [kg/h], its relieving
    pressure [bar a] and temperature [K], and the steam's compressibility there [-] — the sheet's
    temperature is the set pressure's saturation, so on the saturated-vapour line."""
    dev, siz = RELIEF_DEVICES[tag], RELIEF_SIZING[tag]
    t_k = siz.t_c + 273.15
    z = (psat_bara(siz.t_c) * 1.0e5 * v_vapour_sat_m3kg(siz.t_c) * STEAM_MW / 1000.0
         / (R_GAS_J * t_k))
    return {"set": dev.set_bara, "reseat": siz.reseat_bara(dev), "cap": siz.capacity_kgh,
            "p_rel": siz.relieving_bara(dev), "t_rel_k": t_k, "z": z}


#: SV32951 on 329D005, SV32952 on 329D009, SV32978-81 on 322D001A/B (four alike on the node).
SV_329D005 = _relief("SV32951")
SV_329D009 = _relief("SV32952")
SV_322D001 = _relief("SV32978")
N_SV_322D001 = 4


__all__ = [
    "D001_ID_M", "D001_CYL_M", "N_D001", "D001_NLL_M", "RHO_D001_L", "D001_TAPS_M", "A_D001_M2",
    "V_D001_HEAD_M3", "V_D001_M3", "D005_ID_M", "D005_LEN_M", "D005_CAP_M3", "RHO_D005_L",
    "D009_ID_M", "D009_LEN_M", "D009_CAP_M3", "RHO_D009_L", "D005_TAP_HALF_M", "D009_TAP_HALF_M",
    "V_D001_VAP_M3", "V_D005_VAP_M3", "V_D009_VAP_M3", "C_MP_KG_BAR", "C_LP_KG_BAR", "C_9_KG_BAR",
    "MSPAN_502_KG", "MSPAN_503_KG", "MSPAN_504_KG", "DRUM_M_FLOOR_KG", "PV204_BIAS_PCT", "K_902",
    "HV601_P1_DES_BARA", "HV601_P2_DES_BARA", "K_HV601", "P963_P1_DES_BARA", "P963_P2_DES_BARA",
    "K_963", "K_HV602", "P207A_P1_DES_BARA", "P207A_P2_DES_BARA", "K_207A", "M_TURBINE_DES_KGS", "BIAS_207B_PCT", "K_207B", "PV204_OP_DES_PCT", "PV204_XT",
    "PV207A_FULL_KGS", "PV207A_P1_DES_BARA", "PV207A_P2_DES_BARA", "PV207A_XT", "PV207B_OP_DES_PCT",
    "PV207B_XT",
    "M_903_DES_KGS", "DS9_DES_KGS", "PV205A_OP_DES_PCT", "PV205A_XT", "PV205B_FULL_KGS", "PV205B_P1_DES_BARA",
    "PV205B_P2_DES_BARA", "PV205B_XT", "M_502_DES_KGS", "M_503_DES_KGS", "M_504_DES_KGS",
    "LV502_OP_DES_PCT", "LV503_OP_DES_PCT", "LV504_OP_DES_PCT", "LV502_FL", "LV503_FL",
    "LV504_FL", "PT_329204_SPAN_BAR", "PT_329207_SPAN_BAR", "PIC_329204_KC_TABLE",
    "PIC_329204_TI_S", "PIC_329204_KC", "PIC_329204_KI", "PIC_329204_I_AUTHORITY_PCT",
    "TRIP_212_SP_BARA", "HV601_FORCE_BARA", "HV601_SHUT_PULSE_S", "P_9_SP_BARA", "K_PIC_9",
    "DB_LP_BAR", "PIC_329207_KC_TABLE", "PIC_329207_TI_S", "PIC_329207_KC", "PIC_329207_KI",
    "LEVEL_SP_DES_PCT", "LIC_TUNING", "SV_329D005", "SV_329D009",
    "SV_322D001", "N_SV_322D001",
]
