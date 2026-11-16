"""323C003 / 323E002 — unit 323's first stage, the rectifying column and its steam heater: the
design basis, and the column's relief (handoff A-16).

What this equipment is
----------------------
The stripper bottoms (PFD 208) are let down across LV-322501 into 323C003 at 4.1 bar a. The letdown
flash (PFD 301) and the gas 323E002 raises from the column's bottom liquid (PFD 302) leave the top
as PFD 305 for the 323E003 LP carbamate condenser; the bottoms, PFD 314, drain through LV-323501 to
the 323F004 flash. TIC-323007 holds the bottom liquid at 135 C by cascading onto PIC-329202, the
heater's chest pressure, and LIC-323501 holds the level.

When the stripper's bottom seal is lost, LV-322501 passes HP stripper gas as well, and that gas
reaches the column's head space with the letdown flash. Two spring-loaded safety valves on the
column, SV32351 and SV32352, are sized for exactly that case ("Failure of LV 322501", 60 t/h of
carbamate gas).

This module carries the column's feed and bottoms rows, its design flows, holdup and duties,
PT-323201's gas-load law, LV-323501's and PV-329202's trims, the three stage-1 controllers, and what
the relief and the blow-through need. The stage's design basis was moved here out of `unit_323`
unchanged (2026-10-23, the housekeeping split): `unit_323` re-exports every name of it and builds
the stage's species anchor, ``C003_LIQUOR``, beside the section's other two.

Sources
-------
* ``Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md`` — streams 208 and 314, read as MASS %
  (they are liquid rows); the gas loads of streams 301 and 302; stream 305, the column's overhead
  gas: average molar weight 24.92 at 4.1 bar a and 119 C.
* V1 ``backend/main.py``, the unit-323 constant block, and ``c003_pressure_coupling.py``: the
  residence time, set points, floors and the receiving node's pressure. Each carries its provenance.
* Uhde loop summaries for units 323 and 329, UD-MR-323-EC-0001 and UD-MR-329-EC-0001 rev 1, and
  the unit-323 functional diagrams, UD-MR-323-FF-0002 (the vendor archive) — the ranges of
  TT-323007 and PT-329202, and how the temperature master's output is scaled onto its chest
  slave's set point.
* Uhde's design data sheet for 323E002, UD-AU-323-EC-0007 rev 00 (the vendor archive) — the chest
  pressure.
* Flowserve's calculation sheet for LV-323501 (`ureasim.data.control_valves`) and Metso's sizing
  sheet for PV-329202 (`ureasim.data.control_valves_metso`) — their trims and design strokes.
* Uhde's technical specifications UD-RL-323-EC-0001 and -0002 (SV32351, SV32352; P&ID 103/1, line
  GCB4-323201-EG07D): set 5.0 bar g on the sheets' 1.010 bar a, 2.0 bar a back pressure.
* Sempell's orifice selection, UD-RL-G00-DZ-0002-001 page 3: orifice T, 20 106.2 mm2, alpha_w
  0.917, 72 273.6 kg/h certified on carbamate gas of molar mass 25.07, k 1.010, Z 1.00 at 125 C
  and the set pressure plus 10 %; 10 % blowdown.
* The split fractions and the design flow chain live in `ureasim.data.design_point`.

Every relief value is read through `ureasim.data.relief_devices`, which carries the documents.
"""

from __future__ import annotations

import math

from ureasim.core.packet import normalise_solution_mass_fraction as _w_norm
from ureasim.data.control_valves import LV_323501, PV_329202, design_stroke_pct
from ureasim.data.design_point import R323_CP_SOLN, R323_FEED_DES_KGH, R323_M314_DES, R323_PHI_V305
from ureasim.data.relief_devices import RELIEF_DEVICES, RELIEF_SIZING
from ureasim.data.unit_322e001 import T_BOTTOM_DES_C, T_DOWNSTREAM_DES_C
from ureasim.data.unit_329 import P_LP_BARA, STEAM_PFD_KGH
from ureasim.thermo import iapws
from ureasim.thermo.empirical import urea_soln_cp, urea_soln_rho
from ureasim.thermo.urea_liquor import close_urea_on_drain

# ======================================================================================
# The PFD liquor rows [mass fractions]
# ======================================================================================

#: PFD 208, the 322E001 stripper bottoms entering the section [mass %, as the PFD prints it], and
#: normalised to mass fractions.
S208_MASS_PCT = dict(Urea=55.85, Biuret=0.24, NH3=7.92, CO2=10.28, H2O=25.68)
W_S208 = _w_norm(dict(S208_MASS_PCT))

#: PFD 314 as tabulated — the 323C003 bottoms to the 323F004 flash. Kept as the provenance of the
#: closed row below, which is the one the balances use.
W_S314_TAB = _w_norm(dict(Urea=68.74, Biuret=0.36, NH3=2.13, CO2=1.05, H2O=27.72))

#: PFD 314 with its urea closed against the drain (decided 2026-10-10, handoff B-20, project.md
#: decision 101): the table's row leaves 8.16 kg/h of PFD 208's urea, less the biuret 323C003
#: makes, unaccounted — PFD rounding in a 106 t/h column — which V1's back-solve sends overhead as
#: an apparent volatility the runtime zeroes, so the column's design seed was not a fixed point
#: (+0.0033 wt % urea, 6.8 kg/h more to the drain). The urea leaves by the drain, water giving way.
W_S314 = close_urea_on_drain(W_S208, R323_FEED_DES_KGH, R323_M314_DES, W_S314_TAB)

# ======================================================================================
# 323C003 — the rectifying column
# ======================================================================================

#: Column operating pressure [bar a]. PFD 314 at 4.1; the section description gives 4.12.
C003_P_BARA = 4.1

#: Column bottom-liquid temperature [deg C], PFD 314 — the TIC-323007 set point.
C003_T_SP_C = 135.0

#: Bottom-liquid residence time [s], which sizes the design holdup. Source: V1 `main.py`
#: R323_C003_M_TAU_S; V1 notes a measured 86 to 100 s.
C003_M_TAU_S = 120.0

#: Top vapour to the 323E003 LP carbamate condenser at design [kg/h], PFD 305's share of the
#: stripper bottoms applied to the model's own bottoms flow.
M305_DES_KGH = R323_PHI_V305 * R323_FEED_DES_KGH

#: Design liquid holdup [kg].
C003_M_DES_KG = R323_M314_DES / 3600.0 * C003_M_TAU_S

#: Feed temperature at design [deg C] — TT-323001, the stripper bottoms after the LV-322501
#: letdown flash.
FEED_DES_T_C = T_DOWNSTREAM_DES_C

#: Column-bottom sump temperature [deg C], PFD 313 / TT-323002: the 135 C drain less the
#: reboiler's rise. TT-323002 is published as the live column temperature offset by that rise.
C003_T313_C = 121.0

#: LIC-323501 level set point [%]. Source: V1 `main.py` R323_C003_LVL_SP.
C003_LVL_SP_PCT = 60.0

#: LV-323501, the column drain: a Valtek linear trim, Kvs 250 (plug code ...LG). DECIDED
#: 2026-09-30 (handoff B-44): the design stroke is where its Kvs passes PFD 314 on the vendor's
#: normal case, 56.65 %, where V1 anchors on 50 % (R323_LV501_OP_DES); the trim is linear
#: either way. FL is the normal case's, 0.9319, where V1 takes the IEC representative 0.90.
LV501_OP_DES_PCT = design_stroke_pct(LV_323501, R323_M314_DES)
LV501_CHAR = LV_323501.characteristic
LV501_FL = LV_323501.normal_case.fl

#: Holdup at 100 % level [kg], from the design holdup at the level set point.
C003_M_FULL_KG = C003_M_DES_KG / (C003_LVL_SP_PCT / 100.0)

#: Floor on the column holdup [kg], so the temperature integration never divides by zero.
#: Source: V1 `main.py` step_sim, ``max(..., 1.0)``.
C003_M_FLOOR_KG = 1.0

#: PFD 314 effective density [kg/m3], the liquid LV-323501 passes at design.
RHO_S314 = 1106.0


# --- LT-323501, read between its taps (decision 241, handoff B-156's third unit) -----------
#
# Heights are taken from R.L., the girth flange between 323C003 and 323E002 (EL +15.703 m: the
# as-built isometrics' N4 at EL +18.429 m, UD-RL-100-MB-0137, and N5 at EL +16.147 m,
# UD-RL-100-MB-0148, against Glatt's arrangement drawing UD-AU-323-DZ-0001-001 rev 01).

#: The column's bottom [m]: a neck of 323E002's bore, 1160 mm, from R.L. to 185 mm, then a cone
#: at 75 degrees to the horizontal to the 1600 mm shell (Uhde's DDS UD-AU-323-EC-0001 p. 2, line
#: 27) at 1005 mm (DZ-0001-001: 185 + 820 mm; 820 tan 15 deg = 220 mm a side). Below R.L. stand
#: 323E002's 1520 tubes, 19 x 2 mm (UD-AU-323-EC-0007 p. 2, lines 34 and 36).
C003_NECK_D_M, C003_NECK_TOP_M = 1.160, 0.185
C003_SHELL_D_M, C003_CONE_TOP_M = 1.600, 1.005
E002_TUBES_AREA_M2 = 1520 * math.pi * 0.25 * 0.015 ** 2
C003_NECK_AREA_M2 = math.pi * 0.25 * C003_NECK_D_M ** 2
C003_SHELL_AREA_M2 = math.pi * 0.25 * C003_SHELL_D_M ** 2
#: The cone's diameter gain per metre of height [-] and the volumes of the neck and the cone [m3].
C003_CONE_K = (C003_SHELL_D_M - C003_NECK_D_M) / (C003_CONE_TOP_M - C003_NECK_TOP_M)
C003_NECK_M3 = C003_NECK_AREA_M2 * C003_NECK_TOP_M
C003_CONE_M3 = math.pi / (12.0 * C003_CONE_K) * (C003_SHELL_D_M ** 3 - C003_NECK_D_M ** 3)

#: LT-323501, a DP cell between N8 on the shell, 1750 mm above R.L. (Uhde's principle sketch,
#: EC-0001 p. 5; DZ-0001-001), and a seal on the outlet line 400-US14-323266 (P&ID 103/1;
#: MB-0148, the pad flange Z_2304Z): 2000 mm apart, 1106 kg/m3, 0 to 230 mbar (Uhde's
#: UD-MR-G00-EC-0134, sheet p. 4) [m]. The isometric puts the line seal at EL +15.380 m, 2.07 m
#: below N8; the sheet's nozzle distance is taken (As-Built §CXXXV.1).
LT_323501_LO_M = -0.250
LT_323501_SPAN_M = 2.000
LT_323501_RHO_KGM3 = RHO_S314

#: LIC-323501's reading at the design holdup [%]: the plant's, LIC-323501's PV over Book2's two
#: months, 40.0 (38.8 to 40.4, 5279 samples; `References/DCS Trends/Book2.xlsx`). Decided
#: 2026-11-16 (decision 241): V1's 3531 kg reads it, where V1 reads 60 % of M_full. Its height
#: above R.L. [m], 0.550, its diameter on the cone [m] and the volume below it to R.L. [m3].
LT_323501_DES_PCT = 40.0
LT_323501_DES_H_M = LT_323501_LO_M + LT_323501_DES_PCT / 100.0 * LT_323501_SPAN_M
LT_323501_DES_D_M = C003_NECK_D_M + C003_CONE_K * (LT_323501_DES_H_M - C003_NECK_TOP_M)
C003_V_DES_M3 = C003_NECK_M3 + math.pi / (12.0 * C003_CONE_K) * (LT_323501_DES_D_M ** 3
                                                                  - C003_NECK_D_M ** 3)


def lt_323501_pct(m_kg: float) -> float:
    """LI-323501 [%]: the height of 323C003's liquid between LT-323501's taps (decision 241).

    Process utility
    ---------------
    What the board shows, LIC-323501 holds by LV-323501's drain, and the seal on N5 reads. A DP
    cell reads only between its taps: V1's design holdup reads the plant's 40 % with 0.55 m over
    R.L. on the cone, 0 % with 2737 kg still in the column and heater, 100 % at 6053 kg; on the
    cone a kilogram moves it 1.84 times as far as V1's M / M_full at the design.

    Equation
    --------
        V = V_des + (M - M_des) / rho          the liquid above R.L. [m3]
        cone:   D = D_des (1 + 12 k (V - V_des) / (pi D_des^3))^(1/3),  h = h_des + (D - D_des) / k
        below the cone, the neck's or the tubes' bore; above it, the shell's
        LI = clamp( LI_des + (h - h_des) / L . 100, 0, 100 )

    written as the departure from the design holdup, so it reads its set point exactly. Below
    N5's bore the line drains and the plant's reading follows the line; the vessel's own bore is
    carried on (shortcut: the column's level never stands there with LV-323501 sealed). Source:
    As-Built §CXXXV.
    """
    v = C003_V_DES_M3 + (m_kg - C003_M_DES_KG) / LT_323501_RHO_KGM3
    if v < 0.0:
        h = v / E002_TUBES_AREA_M2
    elif v < C003_NECK_M3:
        h = v / C003_NECK_AREA_M2
    elif v < C003_NECK_M3 + C003_CONE_M3:
        d = LT_323501_DES_D_M * (1.0 + 12.0 * C003_CONE_K * (v - C003_V_DES_M3)
                                 / (math.pi * LT_323501_DES_D_M ** 3)) ** (1.0 / 3.0)
        h = LT_323501_DES_H_M + (d - LT_323501_DES_D_M) / C003_CONE_K
    else:
        h = C003_CONE_TOP_M + (v - C003_NECK_M3 - C003_CONE_M3) / C003_SHELL_AREA_M2
    return min(max(LT_323501_DES_PCT + (h - LT_323501_DES_H_M) / LT_323501_SPAN_M * 100.0, 0.0),
               100.0)


#: The reading at which LV-323501's seal is fully lost [%], 29.21: N5's bottom edge. N5, DN 400
#: (406.4 x 5.6 pipe, MB-0148), stands normal to the cone, its axis meeting the wall 525 mm over
#: R.L. (DZ-0001-001), so its bore spans 0.3952 cos 15 deg = 0.382 m of height. Decided 2026-11-16
#: (decision 241, decision 138's class): V1's seal sits at the bottom of the span.
LT_323501_SEAL_PCT = ((0.525 - 0.5 * 0.3952 * math.cos(math.radians(15.0)) - LT_323501_LO_M)
                      / LT_323501_SPAN_M * 100.0)


# --- 323E002, the rectifying heater ---------------------------------------------------

#: Design heater duty [kW]. Source: `References/323C003 323E002.md` (5858 kW on 535 m2).
E002_Q_DES_KW = 5858.0

#: Design chest pressure [bar a], Tsat 142.7 C. Three Uhde sources agree on 3.9: the heater's
#: DDS, UD-AU-323-EC-0007 rev 00, page 2 (shell side "LP Steam - saturated", 3.900 bar a in and
#: out, 145 C in and 142 C out — the steam arrives with the few kelvin of superheat the letdown
#: from the LP header leaves it, which the chest law ignores, as V1's does); PFD 918, the LP
#: steam to 323E002, 3.9 bar a and 145 C; and the Uhde loop summary for unit 329,
#: UD-MR-329-EC-0001 rev 1, loop P 329202, sheet 1/2, line D01, normal 3.9 bar a (2.9 bar g).
#: The DDS and the loop summary are scans, read from the page image.
#: DECIDED DIVERGENCE, 2026-09-30 (handoff Open data gaps, closed): V1 anchors on 3.96 bar a,
#: 0.90 x a 4.4 bar a header it has since retired (`main_backup.py` 854-855), and back-solves
#: the conductance on that; the port anchors on the sourced 3.9, and the stroke and the
#: conductance below are re-derived on it by V1's own expressions.
E002_PCHEST_DES_BARA = 3.9

#: PV-329202 design stroke [%], derived from the chest pressure against the live LP header so
#: the seeded valve admits exactly the datasheet chest pressure.
E002_OP_DES_PCT = E002_PCHEST_DES_BARA / P_LP_BARA * 100.0

#: PV-329202 on its vendor's trim (decision 108's class, applied 2026-10-15): Metso's DN 200 Neldisc,
#: maximum Cv 3050 (`data.control_valves.PV_329202`), its design stroke where it passes PFD 918's
#: 9027 kg/h on its normal case, 32.92 %, and that case's xT. V1 runs it linear from
#: E002_OP_DES_PCT above, which the equivalence harness keeps.
PV_329202_OP_DES_PCT = design_stroke_pct(PV_329202, STEAM_PFD_KGH["918"])
PV_329202_XT = PV_329202.normal_case.xt

#: Heater conductance [kW/K], back-solved so the design duty crosses the design approach.
E002_UA_KW = E002_Q_DES_KW / (iapws.tsat_c(E002_PCHEST_DES_BARA) - C003_T_SP_C)

# --- The column's energy balance at design -------------------------------------------

#: Heat released by the LV-322501 letdown flash [kW]: the stripper bottoms cooling from the
#: 172 C TT-322004 to the 119 C TT-323001 on the lumped design cp.
Q_FLASH_DES_KW = (R323_FEED_DES_KGH / 3600.0 * R323_CP_SOLN
                  * (T_BOTTOM_DES_C - T_DOWNSTREAM_DES_C))

#: Total latent duty available to raise PFD 305 at design [kW] — the flash plus the heater.
#: Written as V1 writes it, operand for operand, so the runtime ratio is exactly 1.0 at design.
Q305_DES_KW = (R323_FEED_DES_KGH / 3600.0 * R323_CP_SOLN * (T_BOTTOM_DES_C - T_DOWNSTREAM_DES_C)
               + E002_Q_DES_KW)

#: Effective latent heat of the overhead [kJ/kg], back-solved: 1562.4 (V1's comment says 645.6,
#: from an earlier duty; the expression is what is ported).
LAMBDA_305_KJKG = Q305_DES_KW / (M305_DES_KGH / 3600.0)

#: The design overhead apportioned to its two sources by the duty that raises each, so the two
#: sum to PFD 305 exactly and both pressure-path ratios are exactly 1.0 at design [kg/h].
#: Stream 301 is the flash of the stripper bottoms across LV-322501; stream 302 is the gas the
#: 323E002 heater raises. The PFD's own mass rows put them at about 17.2 and 7.5 t/h; this
#: apportionment gives 11.1 and 13.5. Only their ratios to these design values are ever used,
#: and the pressure law weights the two by the PFD's own volumes, so the pressure sensitivity
#: to each source is the PFD's.
M_FLASH_GAS_DES_KGH = M305_DES_KGH * (Q_FLASH_DES_KW / Q305_DES_KW)
M_POOL_VAP_DES_KGH = M305_DES_KGH * (E002_Q_DES_KW / Q305_DES_KW)

#: Design cp and density anchors, the same functions evaluated at each stream's design
#: composition and temperature, so every live/design ratio is exactly 1.0 at the seed.
CP_S208_DES = urea_soln_cp(W_S208["Urea"], FEED_DES_T_C)
CP_C003_DES = urea_soln_cp(W_S314["Urea"], C003_T_SP_C)
RHO_C003_DES = urea_soln_rho(W_S314["Urea"], C003_T_SP_C, RHO_S314)

# --- PT-323201: the column pressure and its two gas sources -----------------------------

#: PFD volumetric gas loads at 4.1 bar a [m3/h]: stream 301, the LV-322501 letdown flash gas
#: (119 C, MW 26.39), and stream 302, the 323E002 heater gas returned below the bed (135 C,
#: MW 21.14). Their sum, 7940.4, exceeds the 7677.1 m3/h of stream 305 by what condenses on
#: the packed bed, which is why 305 — the column's OUTLET — is not used as a driver.
#: Source: the PFD, checked; V1 `c003_pressure_coupling.py`.
Q301_DES_M3H = 5064.7
Q302_DES_M3H = 2875.7

#: Design pressure of the receiving 323E003 / 323D001 node [bar a]. Source: V1
#: `c003_pressure_coupling.py` E003_P_DES_BARA.
E003_P_DES_BARA = 3.2

#: Line gas-load coefficient [m3/h per bar], anchored so the design load between the design
#: column and design downstream pressures reproduces itself.
GAS_LOAD_COEFF_M3H_PER_BAR = ((Q301_DES_M3H + Q302_DES_M3H)
                              / math.sqrt(C003_P_BARA ** 2 - E003_P_DES_BARA ** 2))

#: Gas-space time constant of PT-323201 [s] — the small overhead's compressibility only; the
#: liquid thermal lag is C003_M_TAU_S. Source: V1 `main.py` R323_C003_P_TAU_S.
C003_P_TAU_S = 1.0

#: PT-323201 integration bounds [bar a]. Source: V1 `main.py` step_sim literals.
C003_P_MIN_BARA = 1.0
C003_P_MAX_BARA = 12.0

# --- The three stage-1 controllers ----------------------------------------------------
# TIC-323007 (column temperature, master) -> PIC-329202 (323E002 chest pressure, slave) ->
# PV-329202; LIC-323501 -> LV-323501. Source: V1 `main.py` State.__init__, and the DCS tuning
# table, `References/Master_PID_Tuning_Constants.md`.
#
# Both chest cascades read their table gains per cent of span (decided 2026-09-30, the rule of
# handoff B-41 extended; As-Built §XL.2). The functional diagram scales the master's output onto
# the slave's range, SP = OUTP / 100 . PIC:MAX (UD-MR-323-FF-0002, sheets 4 and 5), so a master
# moves its slave's set point by the slave transmitter's span per 100 % of output. V1 applied
# the table's numbers in engineering units — the master in bar per kelvin, the slave in per
# cent per bar times a chest-gain scale V1 derived to hold that basis (``chest_slave_kc_scale``,
# its report A-5). The port runs the table on span and drops the scale.

#: TT-323007's calibrated range [K of span]: 0 to 160 C. Source: UD-MR-323-EC-0001 rev 1, loop
#: T 323007, sheet 1/2, line D07 (scanned, read from the page image).
TT_323007_SPAN_C = 160.0

#: PT-329202's calibrated range [bar of span]: 0 to 6 bar g, normal 3.9 bar a. Source:
#: UD-MR-329-EC-0001 rev 1, loop P 329202, sheet 1/2, line D07 (scanned, read from the image).
PT_329202_SPAN_BAR = 6.0

#: TIC-323007: output is the chest-pressure demand [bar a], 0 to the LP header. The table's row,
#: "TIC-323007 | 323266,US", 2.00 and 500 s, derivative off; on span, 2.00 x 6 bar / 160 K =
#: 0.075 bar/K, where V1 ran 2.0 bar/K.
TIC_323007_KC_TABLE = 2.0
TIC_323007_KC = TIC_323007_KC_TABLE * PT_329202_SPAN_BAR / TT_323007_SPAN_C
TIC_323007_TI_S = 500.0
TIC_323007_SP_LO_C = 50.0
TIC_323007_SP_HI_C = 160.0

#: PIC-329202: output is the PV-329202 stroke [%]. The table's row, "PIC-329202 | 329358,STLS",
#: 0.65 and 30 s; on span, 0.65 x 100 / 6 bar = 10.83 %/bar, where V1 ran 0.65 x its chest
#: scale (3.82 %/bar on V1's 3.96 bar a anchor).
PIC_329202_KC_TABLE = 0.65
PIC_329202_KC = PIC_329202_KC_TABLE * 100.0 / PT_329202_SPAN_BAR
PIC_329202_TI_S = 30.0

#: LIC-323501: DIRECT acting — a level above set point opens LV-323501.
LIC_323501_KC = 1.2
LIC_323501_TI_S = 100.0

# ======================================================================================
# SV32351 and SV32352, the column's relief (decided 2026-10-03, handoff A-16)
# ======================================================================================

#: SV32351 and SV32352, alike: set 5.0 bar g, 6.01 bar a, on the sheets' 1.010 bar a. They reseat
#: 10 % of set below, at 5.51 bar a (Sempell UD-RL-G00-DZ-0002-001 page 3).
SV32351_SET_BARA = RELIEF_DEVICES["SV32351"].set_bara
SV32351_RESEAT_BARA = RELIEF_SIZING["SV32351"].reseat_bara(RELIEF_DEVICES["SV32351"])

#: Each one's certified capacity [kg/h], 72 273.6, on orifice T: carbamate gas of molar mass
#: 25.07, k 1.010 and Z 1.00 at 125 C and 6.51 bar a, the set pressure plus 10 % [bar a]. Two
#: valves, set alike, lift and reseat together.
SV32351_CAP_KGH = RELIEF_SIZING["SV32351"].capacity_kgh
SV32351_P_REL_BARA = RELIEF_SIZING["SV32351"].relieving_bara(RELIEF_DEVICES["SV32351"])
SV32351_T_REL_K = RELIEF_SIZING["SV32351"].t_c + 273.15
SV32351_MW_REL = RELIEF_SIZING["SV32351"].mw
SV32351_Z_REL = RELIEF_SIZING["SV32351"].z
SV32351_K = RELIEF_SIZING["SV32351"].k
SV32351_COUNT = 2

# ======================================================================================
# The gas the column's head space holds
# ======================================================================================

#: Molar mass of the column's own overhead gas [kg/kmol]: PFD 305, average molar weight 24.92.
#: What the valves relieve of the gas the column raises itself; the stripper's blow-through is
#: relieved at the stripper top vapour's own live molar mass.
MW_305 = 24.92

__all__ = [
    "S208_MASS_PCT", "W_S208", "W_S314_TAB", "W_S314", "C003_P_BARA", "C003_T_SP_C",
    "C003_M_TAU_S", "M305_DES_KGH", "C003_M_DES_KG", "FEED_DES_T_C", "C003_T313_C",
    "C003_LVL_SP_PCT", "LV501_OP_DES_PCT", "LV501_CHAR", "LV501_FL", "C003_M_FULL_KG",
    "C003_M_FLOOR_KG", "RHO_S314", "C003_NECK_D_M", "C003_NECK_TOP_M", "C003_SHELL_D_M",
    "C003_CONE_TOP_M", "E002_TUBES_AREA_M2", "C003_NECK_AREA_M2", "C003_SHELL_AREA_M2",
    "C003_CONE_K", "C003_NECK_M3", "C003_CONE_M3", "LT_323501_LO_M", "LT_323501_SPAN_M",
    "LT_323501_RHO_KGM3", "LT_323501_DES_PCT", "LT_323501_DES_H_M", "LT_323501_DES_D_M",
    "C003_V_DES_M3", "lt_323501_pct", "LT_323501_SEAL_PCT", "E002_Q_DES_KW", "E002_PCHEST_DES_BARA", "E002_OP_DES_PCT",
    "PV_329202_OP_DES_PCT", "PV_329202_XT", "E002_UA_KW", "Q_FLASH_DES_KW", "Q305_DES_KW",
    "LAMBDA_305_KJKG", "M_FLASH_GAS_DES_KGH", "M_POOL_VAP_DES_KGH", "CP_S208_DES", "CP_C003_DES",
    "RHO_C003_DES", "Q301_DES_M3H", "Q302_DES_M3H", "E003_P_DES_BARA",
    "GAS_LOAD_COEFF_M3H_PER_BAR", "C003_P_TAU_S", "C003_P_MIN_BARA", "C003_P_MAX_BARA",
    "TT_323007_SPAN_C", "PT_329202_SPAN_BAR", "TIC_323007_KC_TABLE", "TIC_323007_KC",
    "TIC_323007_TI_S", "TIC_323007_SP_LO_C", "TIC_323007_SP_HI_C", "PIC_329202_KC_TABLE",
    "PIC_329202_KC", "PIC_329202_TI_S", "LIC_323501_KC", "LIC_323501_TI_S",
    "SV32351_SET_BARA", "SV32351_RESEAT_BARA", "SV32351_CAP_KGH", "SV32351_P_REL_BARA",
    "SV32351_T_REL_K", "SV32351_MW_REL", "SV32351_Z_REL", "SV32351_K", "SV32351_COUNT", "MW_305",
]
