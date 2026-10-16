"""Unit 323 — LP recirculation and pre-evaporation: the design basis.

What this section is
--------------------
The stripper bottoms leave 322E001 at 144 bar and 172 C carrying about 18 % unreacted
ammonium carbamate and free ammonia. Unit 323 takes that liquor down to near-atmospheric
pressure in three steps, recovering the reactants as gas for the LP carbamate condenser and
concentrating the urea from 56 to 80 wt% for the vacuum evaporators of unit 324, and buffers
the product in an atmospheric tank on the way:

    323C003 / 323E002   rectifying column and its steam heater, 4.1 bar a, 135 C
    323F004             flash tank, 1.13 bar a, 106 C
    323E010 / 323F010   pre-evaporator and its separator, 0.46 bar a, 99 C
    323D002             urea solution tank, two compartments, atmospheric, 99 C

Every stage holds the same six-species liquor, and every stage's species layer is anchored on
its PFD rows through `thermo.urea_liquor`. This module carries those rows, the design flows
and states, and the three stage anchors built from them. The valves, heaters, holdup geometry
and controllers of each stage land with that stage.

Sources
-------
* ``Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md`` — streams 208, 314, 317, 319 and
  331, read as MASS % (they are liquid rows). Checked cell by cell against V1's transcription.
* ``References/323F004 323E010 323F010.md`` — the 1.13 bar a flash (PIC-323203) and the
  0.46 bar a pre-evaporator (PI-323204), which the PFD rounds to 1.1 and 0.5.
* V1 ``backend/main.py``, the unit-323 constant block, for the residence times V1 sized the
  holdups from. Each carries its provenance.
* Uhde loop summary for unit 324, UD-MR-324-EC-0001 rev 1 (the vendor archive) — FT-324401's
  calibrated range.
* Uhde loop summaries for units 323 and 329, UD-MR-323-EC-0001 and UD-MR-329-EC-0001 rev 1, and
  the unit-323 functional diagrams, UD-MR-323-FF-0002 (the vendor archive) — the ranges of
  TT-323007, TT-323012, PT-329202 and PT-329208, and how each temperature master's output is
  scaled onto its chest slave's set point.
* Uhde's design data sheets for 323E002 and 323E010, UD-AU-323-EC-0007 and -0009 rev 00 (the
  vendor archive) — the two chest pressures.
* Flowserve's calculation sheets for LV-323501, LV-323505 and FV-324401
  (`ureasim.data.control_valves`) — their trims, design strokes and pressure-recovery factors.
* The split fractions and the design flow chain live in `ureasim.data.design_point`, which
  the product-line routes were anchored on first; they are imported here, not repeated.
"""

from __future__ import annotations

import math

from ureasim.core.packet import normalise_solution_mass_fraction as _w_norm
from ureasim.data.control_valves import (
    FV_324401,
    LV_323501,
    LV_323505,
    PV_329202,
    PV_329208,
    design_stroke_pct,
)
from ureasim.data.design_point import (
    R323_CP_SOLN,
    R323_D002_RHO,
    R323_FEED_DES_KGH,
    R323_M314_DES,
    R323_M317_DES,
    R323_M319_DES,
    R323_M324_DES,
    R323_PHI_V305,
    R323_PHI_V701,
    R323_PHI_VEVAP,
)
from ureasim.data.unit_322e001 import T_BOTTOM_DES_C, T_DOWNSTREAM_DES_C
from ureasim.data.unit_329 import P_LP_BARA, STEAM_PFD_KGH
from ureasim.thermo import iapws
from ureasim.thermo.empirical import urea_soln_cp, urea_soln_rho
from ureasim.thermo.urea_liquor import (
    close_urea_on_drain,
    liquor_stage,
    reconcile_melt,
    stage_bubble_p,
)

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

#: PFD 319 as tabulated — the 323F004 flash liquid, rounded to two decimals. Kept as the
#: provenance of the reconciled row below, which is the one the balances use.
W_S319_TAB = _w_norm(dict(Urea=71.74, Biuret=0.37, NH3=0.88, CO2=0.66, H2O=26.35))

#: PFD 331, the weak urea return from the granulation scrubber, a cold second feed to 323E010.
#: It is the only source of formaldehyde in the whole train.
W_S331 = _w_norm(dict(Urea=44.37, Biuret=0.41, H2O=55.00, HCHO=0.23))

#: PFD 317 (identical to 315), the 80 % product from 323F010 to the 323D002 tank.
W_S317 = _w_norm(dict(Urea=80.00, Biuret=0.42, NH3=0.08, CO2=0.02, H2O=19.47, HCHO=0.00797))

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
# 323F004 — the flash tank
# ======================================================================================

#: Flash pressure at design [bar a]. PIC-323203 holds it — not on the drum, but on the vent of the
#: 323E011 flash condenser downstream, which is one gas space with the drum. The PFD rounds it
#: to 1.1. It is the ANCHOR of the drum's bubble point and of both letdown valves' laws; the
#: live drum pressure is the 323E011 / 323D011 node's. Source:
#: `References/323F004 323E010 323F010.md` §4, "maintained at 1.13 bar by ... PIC323203".
F004_P_BARA = 1.13

#: Flash-liquid temperature [deg C], PFD 319.
F004_T_SP_C = 106.0

#: Liquid residence time [s]. Source: V1 `main.py` R323_F004_M_TAU_S.
F004_M_TAU_S = 180.0

#: Flash vapour to 323E011 at design [kg/h], PFD 701's share of the column bottoms.
M701_DES_KGH = R323_PHI_V701 * R323_M314_DES

#: Design liquid holdup [kg].
F004_M_DES_KG = R323_M319_DES / 3600.0 * F004_M_TAU_S

#: PFD 319 reconciled to atom consistency against its own feed, so the 323F004 back-solve
#: closes without clipping negative vapour (V1 report G3), its urea closed against the drain as
#: 323C003's is (decision 101's class): the closed PFD 314 brings 6.3 kg/h more urea than the
#: table's 319 holds, and urea does not flash.
W_S319 = close_urea_on_drain(W_S314, R323_M314_DES, R323_M319_DES,
                             reconcile_melt(W_S314, R323_M314_DES, R323_M319_DES, W_S319_TAB))

#: LIC-323505 level set point [%]. Source: V1 `main.py` R323_F004_LVL_SP.
F004_LVL_SP_PCT = 60.0

#: LV-323505, the drum's drain to 323F010: a Valtek modified equal-percentage trim, Kvs 355.
#: DECIDED 2026-09-30 (handoff B-44): it runs its vendor trim from the stroke at which its Kvs
#: passes PFD 319 on the vendor's normal case, 67.73 %, where V1 runs it linear from 50 %
#: (R323_LV_CHAR, R323_LV505_OP_DES; V1's reason, "no control valve datasheet covers them",
#: no longer holds). FL is the normal case's, 0.8926, where V1 takes the IEC 0.90.
LV505_OP_DES_PCT = design_stroke_pct(LV_323505, R323_M319_DES)
LV505_CHAR = LV_323505.characteristic
LV505_FL = LV_323505.normal_case.fl

#: Holdup at 100 % level [kg], from the design holdup at the level set point.
F004_M_FULL_KG = F004_M_DES_KG / (F004_LVL_SP_PCT / 100.0)

#: Floor on the drum holdup [kg], so the temperature integration never divides by zero.
#: Source: V1 `main.py` step_sim, ``max(..., 1.0)``.
F004_M_FLOOR_KG = 1.0

#: PFD 319 effective density [kg/m3], the liquid LV-323505 passes at design.
RHO_S319 = 1130.0

#: Design cp and density anchors of the drum liquor, PFD 319 at 106 C, so the live/design
#: ratios are exactly 1.0 at the seed.
CP_F004_DES = urea_soln_cp(W_S319["Urea"], F004_T_SP_C)
RHO_F004_DES = urea_soln_rho(W_S319["Urea"], F004_T_SP_C, RHO_S319)

# --- The drum's energy balance at design ------------------------------------------------

#: Heat the 4.1 -> 1.13 bar a letdown releases at design [kW]: the column bottoms cooling from
#: 135 to 106 C on the lumped design cp. The drum is adiabatic, so this is all it has to flash
#: with. Written as V1 writes it, operand for operand, so the runtime ratio is exactly 1.0 at
#: design.
Q701_DES_KW = (R323_M314_DES / 3600.0 * R323_CP_SOLN
               * (C003_T_SP_C - F004_T_SP_C))

#: Effective latent heat of the flash vapour [kJ/kg], back-solved from the adiabatic balance
#: m_314 cp (135 - 106) = m_701 lambda_701: about 1734.8.
LAMBDA_701_KJKG = ((R323_M314_DES / 3600.0 * R323_CP_SOLN * (C003_T_SP_C - F004_T_SP_C))
                   / (M701_DES_KGH / 3600.0))

# --- LIC-323505 -------------------------------------------------------------------------

#: LIC-323505, DIRECT acting: a level above set point opens LV-323505. Source:
#: `References/Master_PID_Tuning_Constants.md` (Kc 1.00, Ti 100 s, Td 0) and V1 `main.py`
#: State.__init__, which agree.
LIC_323505_KC = 1.0
LIC_323505_TI_S = 100.0

# ======================================================================================
# 323E010 / 323F010 — the pre-evaporator and its separator
# ======================================================================================

#: Separator pressure at design [bar a]. Source: `References/323F004 323E010 323F010.md`,
#: PI-323204 "targets 0.46 bar". The live separator pressure is a state of its own vapour
#: space, set by what HV-323605 passes to the 324E002 condenser shell; 0.46 is the ANCHOR of
#: the HV-323605 law, the barometric leg and the flash's bubble point. V1's constant block
#: still calls it a "FIXED vacuum boundary", which predates the live PT-323204 state.
F010_P_BARA = 0.46

#: Product temperature [deg C], PFD 315 / 317 — the TIC-323012 set point.
F010_T_SP_C = 99.0

#: Liquid residence time [s]. Source: V1 `main.py` R323_F010_M_TAU_S.
F010_M_TAU_S = 240.0

#: The granulation return [kg/h] and its temperature [deg C], PFD 331.
M331_DES_KGH = 3270.0
M331_T_C = 40.0

#: Overhead to the vacuum system at design [kg/h], PFD 790: the water boiled off stream 319
#: plus everything stream 331 brings that the product does not keep.
MEVAP_DES_KGH = R323_PHI_VEVAP * R323_M319_DES + M331_DES_KGH

#: Design liquid holdup [kg].
F010_M_DES_KG = R323_M317_DES / 3600.0 * F010_M_TAU_S

#: Level indication span [%]: the design holdup reads 60 % on LI-323F010. The separator has no
#: level CONTROL — it drains freely through its barometric leg — so this sets only the
#: indication. Source: V1 `main.py` R323_F010_LVL_SP.
F010_LVL_SP_PCT = 60.0

#: Holdup at 100 % indicated level [kg].
F010_M_FULL_KG = F010_M_DES_KG / (F010_LVL_SP_PCT / 100.0)

#: Floor on the separator holdup [kg]. Source: V1 `main.py` step_sim, ``max(..., 1.0)``.
F010_M_FLOOR_KG = 1.0

#: Separator geometry [m], from the vessel datasheet narrative, `References/323F004 323E010
#: 323F010.md` §3.2: inside diameter 3478 mm, cylindrical shell 2437 mm. The shell volume is
#: what the separator's vapour-space pressure integrates over, and the bore is the area the
#: liquid head stands on in the barometric-leg drain.
F010_ID_M = 3.478
F010_SHELL_M = 2.437
F010_VOL_M3 = math.pi * 0.25 * F010_ID_M ** 2 * F010_SHELL_M
F010_AREA_M2 = math.pi * 0.25 * F010_ID_M ** 2

#: PT-323204 integration bounds [bar a]. Source: V1 `main.py` step_sim literals.
F010_P_MIN_BARA = 0.05
F010_P_MAX_BARA = 1.0

#: Effective latent heat of the overhead [kJ/kg]: water at 0.46 bar a. Source: V1 `main.py`
#: R323_EVAP_LAMBDA. IAPWS-IF97 gives 2310 at the 79.3 C saturation of 0.46 bar a and 2259
#: at 99 C; 2280 sits between them.
EVAP_LAMBDA_KJKG = 2280.0

#: Design specific heats [kJ/(kg.K)] of the separator liquor (PFD 317 at 99 C, 2.49997) and of
#: the granulation return (PFD 331 at 40 C, 3.248), so the live/design brackets are exactly 0.0
#: at the seed.
CP_F010_DES = urea_soln_cp(W_S317["Urea"], F010_T_SP_C)
CP_S331_DES = urea_soln_cp(W_S331["Urea"], M331_T_C)

#: Effective density of the separator liquor at design [kg/m3], PFD 315 / 317 — the anchor of
#: the live density that sets the separator's vapour-space volume.
RHO_F010_ANCHOR = R323_D002_RHO

# --- 323E010, the pre-evaporator heater --------------------------------------------------

#: Design chest pressure [bar a], Tsat 127.4 C against the 99 C boil. PFD 926, the LP steam to
#: 323E010, gives 2.5 bar a, 139 C, 1.35 kg/m3, 11 230 kg/h; the heater's DDS, UD-AU-323-EC-0009
#: rev 00, page 2 (a scan, read from the page image), gives shell side "LP Steam - saturated",
#: 2.5 bar a, 139 C in and out, 1.29 kg/m3. The 139 C is the PFD 917 header steam (saturated,
#: 4.4 bar a) let down isenthalpically to 2.5 bar a — 139.28 C on IAPWS-IF97 — superheat the
#: chest law ignores, as V1's does; both densities are 2.5 bar a's. The PT-329208 loop summary (UD-MR-329-EC-0001 rev 1,
#: loop P 329208, sheet 1/2, line D01) alone gives the normal as 3.5 bar a (2.5 bar g), which
#: is 139 C's saturation pressure: it is outvoted by the design basis and its own heater's DDS.
#: DECIDED DIVERGENCE, 2026-09-30 (handoff B-23, closed): V1 anchors on 1.76 bar a, a 40 %
#: stroke on a 4.4 bar a header it has since retired (0.40 x 4.4); the port anchors on PFD
#: 926's 2.5, and the stroke and the conductance below are re-derived on it by V1's own
#: expressions.
E010_PCHEST_DES_BARA = 2.5

#: PV-329208 design stroke [%], derived from the chest pressure against the live LP header so
#: the seeded valve admits exactly the design chest pressure.
E010_OP_DES_PCT = E010_PCHEST_DES_BARA / P_LP_BARA * 100.0

#: PV-329208 on its vendor's trim (decision 108's class, applied 2026-10-15): Metso's DN 250 balanced
#: Neldisc, maximum Cv 2580 (`data.control_valves.PV_329208`), its design stroke where it passes PFD
#: 926's 11 230 kg/h on its normal case, 27.22 %, and that case's xT. V1 runs it linear from
#: E010_OP_DES_PCT above, which the equivalence harness keeps.
PV_329208_OP_DES_PCT = design_stroke_pct(PV_329208, STEAM_PFD_KGH["926"])
PV_329208_XT = PV_329208.normal_case.xt

#: Design heater duty [kW], back-solved from the stage's energy balance with TWO feeds:
#: the evaporation's latent heat, less the sensible surplus of PFD 319 (106 -> 99 C), less the
#: sensible DEFICIT of PFD 331 (40 -> 99 C) — the cold granulation return is a heat sink the
#: heater also pays for. 7249 kW; `References/Mapping of the steam system.md` gives
#: 7.05 MW for the same consumer. Written as V1 writes it, operand for operand.
E010_Q_DES_KW = (MEVAP_DES_KGH / 3600.0 * EVAP_LAMBDA_KJKG
                 - R323_M319_DES / 3600.0 * R323_CP_SOLN * (F004_T_SP_C - F010_T_SP_C)
                 - M331_DES_KGH / 3600.0 * R323_CP_SOLN * (M331_T_C - F010_T_SP_C))

#: Heater conductance [kW/K], back-solved so the design duty crosses the design approach.
E010_UA_KW = E010_Q_DES_KW / (iapws.tsat_c(E010_PCHEST_DES_BARA) - F010_T_SP_C)

#: Total heat available to evaporate at design [kW]: the two feeds' sensible terms plus the
#: heater. The same expression, in the same float operation order, as the runtime q_avail, so
#: the duty ratio is exactly 1.0 at the seed.
QEVAP_DES_KW = (R323_M319_DES / 3600.0 * R323_CP_SOLN * (F004_T_SP_C - F010_T_SP_C)
                + M331_DES_KGH / 3600.0 * R323_CP_SOLN * (M331_T_C - F010_T_SP_C)
                + E010_Q_DES_KW)

# --- HV-323605, the separator's vapour outlet ----------------------------------------------

#: HIC-323605 design opening [%]. Source: V1 `main.py` R323_HIC605_DES_PCT.
HIC_323605_DES_PCT = 50.0

#: HV-323605 trim. No datasheet exists in `References/` or in the vendor archive, whose TOC
#: indexes only package-unit valves, so this is a stated choice: LINEAR keeps the per-cent-of-
#: stroke gain the retired ``pull . HIC/50`` law gave the operator. Source: V1 `main.py`
#: R323_HV605_CHAR.
HV605_CHAR = "linear"

#: The 324E002 condenser shell at design [bar a] — the pressure HV-323605 discharges into.
#: V1 takes the 324F001 separator vacuum, R324_F001_P_BARA, which the 324E002 shell shares;
#: PFD 703, the combined condenser inlet, is tabulated at 0.3 bar a. Source: V1 `main.py`
#: R324_F001_P_BARA.
P_324E002_DES_BARA = 0.33

# --- The stage-3 controllers ------------------------------------------------------------
# TIC-323012 (separator temperature, master) -> PIC-329208 (323E010 chest pressure, slave) ->
# PV-329208. Source: V1 `main.py` State.__init__, and the DCS tuning table. Both read their
# gains per cent of span, as the stage-1 cascade does (see there).

#: TT-323012's calibrated range [K of span]: 0 to 160 C. Source: UD-MR-323-EC-0001 rev 1, loop
#: T 323012, sheet 1/2, line D07 (scanned, read from the page image).
TT_323012_SPAN_C = 160.0

#: PT-329208's calibrated range [bar of span]: 0 to 6 bar g. Source: UD-MR-329-EC-0001 rev 1,
#: loop P 329208, sheet 1/2, line D07 (scanned, read from the page image). The same sheet gives
#: the normal as 3.5 bar a (2.5 bar g), against the design chest above.
PT_329208_SPAN_BAR = 6.0

#: TIC-323012: output is the chest-pressure demand [bar a], 0 to the LP header. The loop has no
#: row in the plant DCS table. V1 ran its own retune, 3.6 bar/K and 1200 s
#: (`Master_PID_Tuning_Constants.md` Appendix C, 2026-09-04, G-VLE-4), which was stable only
#: behind V1's slow PIC-329208 (a closed loop of about 6000 s): behind the slave on span it
#: limit-cycles, +/- 0.5 K with a 50-minute period after a 2 K set-point step. DECIDED
#: 2026-09-30 (As-Built §XL.2): TIC-323012 runs its sibling's table row — TIC-323007's, 2.00 and
#: 500 s, the same cascade on the same unit — on its own spans, 2.00 x 6 bar / 160 K =
#: 0.075 bar/K. A stated tuning, not a table value; Phase 7 re-measures it against the trends.
TIC_323012_KC_TABLE = TIC_323007_KC_TABLE
TIC_323012_KC = TIC_323012_KC_TABLE * PT_329208_SPAN_BAR / TT_323012_SPAN_C
TIC_323012_TI_S = TIC_323007_TI_S
TIC_323012_SP_LO_C = 50.0
TIC_323012_SP_HI_C = 130.0

#: PIC-329208: output is the PV-329208 stroke [%]. The table's row, "PIC-329208 | 329433,STLS",
#: 0.20 and 60 s, derivative off; on span, 0.20 x 100 / 6 bar = 3.33 %/bar, where V1 ran 0.20 x
#: its chest scale (0.372 %/bar on V1's 1.76 bar a anchor).
PIC_329208_KC_TABLE = 0.2
PIC_329208_KC = PIC_329208_KC_TABLE * 100.0 / PT_329208_SPAN_BAR
PIC_329208_TI_S = 60.0

# ======================================================================================
# 323D002 — the urea solution tank, stage 4
# ======================================================================================

#: Compartment volumes [m3]. Compartment I is the active flow-through zone: the 323F010 drain,
#: the 323P003A/B suction and the LV-324501B melt recycle all land in it. Compartment II is the
#: passive buffer behind the internal baffle, dry in normal operation, with no nozzle of its
#: own. Source: `References/323D002.md` §3.2 and §3.3; V1 `main.py` R323_D002_VOL_I_M3 and
#: R323_D002_VOL_II_M3.
D002_VOL_I_M3 = 80.0
D002_VOL_II_M3 = 300.0

#: LIC-323507 set point [%]. Deliberately low: the licensor holds Compartment I at about 10 %
#: so the active residence stays near six minutes (8 m3 against 80.6 m3/h), because the
#: ammonia that suppresses biuret formation has already been flashed off at 80 % urea and
#: 99 C. Source: `References/323D002.md` §3.2; V1 `main.py` R323_D002_LVL_SP.
D002_LVL_SP_PCT = 10.0

#: FV-324401, the solution to the evaporators: a Valtek modified equal-percentage trim, Kvs 160.
#: DECIDED 2026-09-30 (handoff B-44): it runs its vendor trim from the stroke at which its Kvs
#: passes PFD 324 on the vendor's normal case, 72.36 %, where V1 runs it linear from 50 %
#: (R323_FV401_OP_DES).
FV401_OP_DES_PCT = design_stroke_pct(FV_324401, R323_M324_DES)
FV401_CHAR = FV_324401.characteristic

#: Compartment I at 100 % and at its set point [kg], on the PFD density. The live spans are
#: taken on the live density at run time; these fix only the design seed.
D002_M_I_FULL_KG = D002_VOL_I_M3 * R323_D002_RHO
D002_M_I_DES_KG = D002_M_I_FULL_KG * (D002_LVL_SP_PCT / 100.0)

#: Floor on the Compartment I holdup [kg]. Source: V1 `main.py` step_sim, ``max(..., 1.0)``.
D002_M_I_FLOOR_KG = 1.0

# --- The stage-4 controllers ------------------------------------------------------------
# LIC-323507 (Compartment I level, master) -> FIC-324401 (product flow, slave) -> FV-324401.
# Source: V1 `main.py` State.__init__.

#: LIC-323507: DIRECT acting; output is the product-flow demand [t/h], 0 to 150. The loop has
#: no row in the plant DCS table. V1's note: "faceplate missing: Ti = hydraulic settling time
#: V_I/Q = 80/(92.75/1.3) ~ 4030 s" — Compartment I's full volume over the design flow, on the
#: retired 1300 kg/m3 density; 3574 s on the PFD's 1151.
LIC_323507_KC = 1.0
LIC_323507_TI_S = 4030.0
LIC_323507_OP_HI_TH = 150.0

#: FIC-324401's gain as the DCS table gives it [% of output per % of span]: 0.40, with Ti 30 s,
#: Td -1 s, Tf 0. Source: `References/Master_PID_Tuning_Constants.md`; V1 `main.py`
#: State.__init__ seeds the same numbers but applies the gain per t/h. The table's 2 % deadband
#: is not carried by V1 (handoff B-28).
FIC_324401_KC_TABLE = 0.4

#: FT-324401's calibrated range: 0 to 110 m3/h, volume flow, a magnetic inductive meter on
#: 323P003A/B's discharge. Source: Uhde loop summary UD-MR-324-EC-0001 rev 1, loop F 324401, sheet
#: 1/2, line D07 (vendor archive, scanned, read from the page image): "Disch. 323P003A/B US Pump",
#: line 150-US9-323255, 51.1 / 80.5 / 100.0 m3/h, 99 C. The loop runs in t/h, so the span is carried
#: to mass on the liquor's design density, PFD 317's 1151 kg/m3 — the density this port converts
#: the stream with; the sheet's own 1174.0 kg/m3 does not reproduce its 80.5 m3/h normal flow from
#: the PFD's.
FT_324401_SPAN_M3H = 110.0
FT_324401_SPAN_TH = FT_324401_SPAN_M3H * R323_D002_RHO / 1000.0

#: FIC-324401: output is the FV-324401 stroke [%]; set-point span 0 to 150 t/h. The table's gain
#: rescaled to t/h, 0.40 %/% on 126.6 t/h, 0.316 %/(t/h); V1 runs 0.40, and the port departs from
#: it by decision of 2026-09-30 (handoff B-41).
FIC_324401_KC = FIC_324401_KC_TABLE * 100.0 / FT_324401_SPAN_TH
FIC_324401_TI_S = 30.0
FIC_324401_TD_S = -1.0
FIC_324401_SP_HI_TH = 150.0

#: FT-324401 time constant [s]: the transmitter plus the valve's stroke dynamics. The valve is a
#: pure gain of 1.855 t/h per %, and an UNLAGGED velocity-form PV puts a loop pole at -Kc . G.
#: V1's note gives |z| = 2.78, which is Kc 1.5 — an earlier tuning — and would diverge; at V1's
#: Kc 0.4 the pole is -0.74, and at the port's 0.316 -0.59, stable but ringing tick to tick. The
#: lag removes it. Source:
#: V1 `main.py` step_sim, ``_lag1(..., 5.0, dt)``.
FT_324401_TAU_S = 5.0

# ======================================================================================
# The biuret reaction in the liquor
# ======================================================================================

#: Reaction order of 2 Urea -> Biuret + NH3 in the urea fraction [-]. Its activation energy is
#: the stripper's, `data.unit_322e001.BIURET_EA_JMOL`: one reaction, one Ea. Source: V1
#: `main.py` SOL_BIU_ORDER.
BIURET_ORDER = 2.0

# ======================================================================================
# The three stage anchors
# ======================================================================================

#: 323C003: stripper bottoms in, PFD 305 up, PFD 314 down.
C003_LIQUOR = liquor_stage(W_S208, W_S314, R323_FEED_DES_KGH, M305_DES_KGH, R323_M314_DES,
                           C003_M_DES_KG, C003_T_SP_C, C003_P_BARA)

#: 323F004: PFD 314 in, PFD 701 up, PFD 319 down.
F004_LIQUOR = liquor_stage(W_S314, W_S319, R323_M314_DES, M701_DES_KGH, R323_M319_DES,
                           F004_M_DES_KG, F004_T_SP_C, F004_P_BARA)

#: 323F010: PFD 319 and 331 in, PFD 790 up, PFD 317 down. Stream 790 lists 0.14 mol % urea —
#: 54 kg/h in 12 t/h — which cannot evaporate at 99 C, so it is closed as entrained liquor:
#: 0.611 % of the overhead.
F010_LIQUOR = liquor_stage(W_S319, W_S317, R323_M319_DES, MEVAP_DES_KGH, R323_M317_DES,
                           F010_M_DES_KG, F010_T_SP_C, F010_P_BARA,
                           w_in2=W_S331, m_in2=M331_DES_KGH, entrain=True)

# ======================================================================================
# The letdowns flash (decided 2026-09-30, handoff B-46)
# ======================================================================================

#: The design vapour pressure each letdown's liquor carries [bar a]: its stage's bubble pressure
#: at the design state, at most the stage's pressure, 4.1 bar a at 323C003 — Flowserve's LV-323501 sheet prints 4.1 on every
#: case — and 1.13 at 323F004 (the LV-323505 sheet prints 0.68, the degassed liquor's; the
#: model's liquor at the drum carries its ammonia and CO2 to the valve). Below this pressure the
#: valve flashes and chokes on FL^2 (P1 - FF . Pv). V1 passes no vapour pressure, so neither
#: valve can choke.
LV501_PV_DES_BARA = stage_bubble_p(C003_LIQUOR, W_S314, C003_T_SP_C, C003_P_BARA)
LV505_PV_DES_BARA = stage_bubble_p(F004_LIQUOR, W_S319, F004_T_SP_C, F004_P_BARA)


__all__ = [
    "S208_MASS_PCT",
    "W_S208", "W_S314_TAB", "W_S314", "W_S319_TAB", "W_S319", "W_S331", "W_S317",
    "C003_P_BARA", "C003_T_SP_C", "C003_M_TAU_S", "M305_DES_KGH", "C003_M_DES_KG",
    "FEED_DES_T_C", "C003_T313_C", "C003_LVL_SP_PCT", "LV501_OP_DES_PCT", "C003_M_FULL_KG",
    "C003_M_FLOOR_KG", "RHO_S314", "LV501_CHAR", "LV501_FL", "LV501_PV_DES_BARA",
    "LV505_PV_DES_BARA",
    "E002_Q_DES_KW", "E002_PCHEST_DES_BARA", "E002_OP_DES_PCT", "PV_329202_OP_DES_PCT", "PV_329202_XT", "E002_UA_KW",
    "Q_FLASH_DES_KW", "Q305_DES_KW", "LAMBDA_305_KJKG", "M_FLASH_GAS_DES_KGH",
    "M_POOL_VAP_DES_KGH", "CP_S208_DES", "CP_C003_DES", "RHO_C003_DES",
    "Q301_DES_M3H", "Q302_DES_M3H", "E003_P_DES_BARA", "GAS_LOAD_COEFF_M3H_PER_BAR",
    "C003_P_TAU_S", "C003_P_MIN_BARA", "C003_P_MAX_BARA",
    "TT_323007_SPAN_C", "PT_329202_SPAN_BAR", "TIC_323007_KC_TABLE",
    "TIC_323007_KC", "TIC_323007_TI_S", "TIC_323007_SP_LO_C", "TIC_323007_SP_HI_C",
    "PIC_329202_KC_TABLE", "PIC_329202_KC", "PIC_329202_TI_S", "LIC_323501_KC", "LIC_323501_TI_S",
    "F004_P_BARA", "F004_T_SP_C", "F004_M_TAU_S", "M701_DES_KGH", "F004_M_DES_KG",
    "F004_LVL_SP_PCT", "LV505_OP_DES_PCT", "LV505_CHAR", "LV505_FL", "F004_M_FULL_KG", "F004_M_FLOOR_KG", "RHO_S319",
    "CP_F004_DES", "RHO_F004_DES", "Q701_DES_KW", "LAMBDA_701_KJKG",
    "LIC_323505_KC", "LIC_323505_TI_S",
    "F010_P_BARA", "F010_T_SP_C", "F010_M_TAU_S", "M331_DES_KGH", "M331_T_C",
    "MEVAP_DES_KGH", "F010_M_DES_KG", "F010_LVL_SP_PCT", "F010_M_FULL_KG", "F010_M_FLOOR_KG",
    "F010_ID_M", "F010_SHELL_M", "F010_VOL_M3", "F010_AREA_M2",
    "F010_P_MIN_BARA", "F010_P_MAX_BARA", "EVAP_LAMBDA_KJKG", "CP_F010_DES", "CP_S331_DES",
    "RHO_F010_ANCHOR", "E010_PCHEST_DES_BARA", "E010_OP_DES_PCT", "PV_329208_OP_DES_PCT", "PV_329208_XT", "E010_Q_DES_KW",
    "E010_UA_KW", "QEVAP_DES_KW", "HIC_323605_DES_PCT", "HV605_CHAR", "P_324E002_DES_BARA",
    "TT_323012_SPAN_C", "PT_329208_SPAN_BAR", "TIC_323012_KC_TABLE",
    "TIC_323012_KC", "TIC_323012_TI_S", "TIC_323012_SP_LO_C", "TIC_323012_SP_HI_C",
    "PIC_329208_KC_TABLE", "PIC_329208_KC", "PIC_329208_TI_S",
    "D002_VOL_I_M3", "D002_VOL_II_M3", "D002_LVL_SP_PCT", "FV401_OP_DES_PCT",
    "FV401_CHAR",
    "D002_M_I_FULL_KG", "D002_M_I_DES_KG", "D002_M_I_FLOOR_KG",
    "LIC_323507_KC", "LIC_323507_TI_S", "LIC_323507_OP_HI_TH",
    "FIC_324401_KC_TABLE", "FT_324401_SPAN_M3H", "FT_324401_SPAN_TH",
    "FIC_324401_KC", "FIC_324401_TI_S", "FIC_324401_TD_S", "FIC_324401_SP_HI_TH",
    "FT_324401_TAU_S",
    "BIURET_ORDER",
    "C003_LIQUOR", "F004_LIQUOR", "F010_LIQUOR",
]
