"""323E011 / 323D011 — the flash condenser and its level tank: the design basis.

What this equipment is
----------------------
323E011 condenses the flash gas of unit 323's LP stage. Its shell takes four streams: the
323F004 flash vapour (PFD 701), the 328D001 reflux-drum vent (786), the 323D001 vent of the LP
carbamate condenser (321), and an ammonia-water wash from the 328D003 carbamate collector (791),
which absorbs the gas as it condenses. The condensate falls by gravity through the DN 100 N2
nozzle into 323D011, the level tank mounted directly beneath it, and 323P008A/B pump it out as
lean carbamate, PFD 718, split into 718A to 328D001 and 718B to the 323E003 LP carbamate
condenser. What does not condense leaves through PV-323203 to the 323C005 atmospheric absorber,
PFD 702. PIC-323203 on that vent is the only pressure controller of the whole 1.13 bar a gas
space: the 323F004 flash drum, its vapour line, the condenser shell and the level tank.

    PIC-323203 (the node)          ->  PV-323203 (vent 702 to 323C005)
    LIC-323503 (323D011 level)     ->  the total 718 draw demand
    FIC-323418 (718B to 323E003)   ->  FV-323418; 718A is the unmetered remainder

Sources
-------
* ``Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md`` — streams 701, 702, 718, 718A,
  718B, 786, 321 and 791. The PFD closes the condenser exactly: 701 + 786 + 321 + 791 = 7563 =
  718 (7123) + 702 (440) kg/h.
* ``References/323E011 323D011 323P008 Datasheets.md`` — the shell, the bundle and the tank,
  the liquid outlet density, the 3440 kW duty and the 30 / 40 C cooling water.
* ``References/Master_PID_Tuning_Constants.md`` — PIC-323203, LIC-323503 and FIC-323418.
* Uhde loop summaries for unit 323, UD-MR-323-EC-0001 rev 1 (the vendor archive) — PT-323203's
  and FT-323418's calibrated ranges.
* Metso's sizing sheet for PV-323203 (`ureasim.data.control_valves`, item 22) — its Neldisc trim
  and design stroke.
* V1 ``backend/main.py``, the "323E011 + 323D011" constant block (1466-1569), the controller
  seeds in ``State.__init__`` (6831-6835, 6893-6898, 6916-6937, 6981-6990), and
  ``backend/c003_pressure_coupling.py`` for the condensation capacity. Each value carries its
  provenance.
"""

from __future__ import annotations

import math

from ureasim.data.control_valves import FV_323418, LV_323503, PV_323203, design_stroke_pct
from ureasim.data.relief_devices import (
    GAS_KD_FULL_LIFT,
    RELIEF_DEVICES,
    RELIEF_SIZING,
    gas_reseat_bara,
)
from ureasim.data.unit_323 import F004_LVL_SP_PCT, M701_DES_KGH
from ureasim.thermo import iapws

# ======================================================================================
# The design flows [kg/h]
# ======================================================================================

#: PFD 701, the 323F004 flash vapour, as the flash tank's design split delivers it (4426.6;
#: the PFD rounds it to 4430).
E011_M701_DES_KGH = M701_DES_KGH

#: PFD 786, the 328D001 reflux-drum vent through PV-328202.
E011_M786_DES_KGH = 276.0

#: PFD 321, the 323D001 vent through PV-323202. V1 writes it ``R3232_M797_DES*0.0 + 1323.0``.
#: PFD table 20 prints 132.3, a decimal slip: its own molar flow, 50.29 kmol/h at 26.32, is
#: 1323.6 kg/h, and table 21 prints 1323.
E011_M321_DES_KGH = 1323.0

#: PFD 791, the 328D003 Compartment-II ammonia-water wash through FV-323402 — a LIQUID, the
#: absorbent, not gas load.
E011_M402_DES_KGH = 1534.0

#: The condenser's total inlet at design, the PFD's own rounded closure of 701 + 786 + 321 + 791.
E011_IN_DES_KGH = 7563.0

#: What the rounded closure carries beyond the four modelled inlets (3.39 kg/h). V1 charges it
#: at PFD 701's temperature and keeps it in every tick's inlet, so the design point closes.
E011_RECON_KGH = E011_IN_DES_KGH - (E011_M701_DES_KGH + E011_M786_DES_KGH
                                    + E011_M321_DES_KGH + E011_M402_DES_KGH)

#: PFD 718, the lean carbamate 323P008 draws from 323D011.
D011_M718_DES_KGH = 7123.0

#: PFD 702, the uncondensed gas PV-323203 vents to 323C005.
E011_MV_DES_KGH = 440.0

#: Gas condensed or absorbed in 323E011 at design [kg/h]: the inlet less the wash and the vent.
E011_MCOND_DES_KGH = E011_IN_DES_KGH - E011_M402_DES_KGH - E011_MV_DES_KGH

#: PFD 718A (to 328D001) and 718B (to 323E003), half of 718 each (the PFD prints 3562 twice).
M718A_DES_KGH = 0.5 * D011_M718_DES_KGH
M718B_DES_KGH = 0.5 * D011_M718_DES_KGH

# ======================================================================================
# The condensation capacity
# ======================================================================================

#: Design gas load on 323E011 [kg/h]: 701 + 786 + 321 at their PFD values. Source: V1
#: ``c003_pressure_coupling.E011_GAS_FEED_DES_KGH``.
E011_GAS_FEED_DES_KGH = 6029.0

#: What 323E011 condenses at design [kg/h], and — V1's model — at every other state: the cooling
#: surface is fixed, so the condensation rate is taken as saturated at its design value and
#: every kilogram of gas above it must leave through PV-323203. Source: V1
#: ``c003_pressure_coupling.E011_CONDENSATION_CAPACITY_DES_KGH`` (6029 - 440). Since 2026-10-15
#: (handoff B-30) the port anchors its dew-point capacity on it at the design node, 1.13 bar a and
#: 45 C against the 35 C water; V1's constant is kept for the equivalence harness.
E011_CONDENSATION_CAPACITY_DES_KGH = 5589.0

# ======================================================================================
# The states at design
# ======================================================================================

#: Condensate temperature [deg C], PFD 718 and the datasheet's shell liquid outlet.
E011_T_C = 45.0

#: Inlet temperatures the energy balance charges [deg C]: PFD 701, 786, 321 and 791. V1 holds
#: all four at their design values; the last two are literals in its step (``74.0``, ``56.0``).
E011_T701_C = 106.0
E011_T786_C = 61.0
E011_T321_C = 74.0
E011_T791_C = 56.0

#: Cooling-water temperature the duty is driven against [deg C]: the mean of the datasheet's
#: 30 C supply (stream 1012) and 40 C return (stream 1013). V1's ``(Te011 - 35.0)``.
E011_CW_T_C = 35.0

#: Node pressure at design [bar a], PIC-323203's set point: "maintains the upstream flash tank
#: system at approximately 1.13 bar" (`References/323C005 328V001 Datasheets.md`).
E011_P_BARA = 1.13

#: Water's saturation temperature at the design node [deg C]: the anchor of 323E011's dew point
#: (handoff B-30, decided 2026-10-15), the frozen-offset idiom of 323E003's
#: (`unit_323e003.TSAT_E003_DES_C`).
TSAT_E011_DES_C = iapws.tsat_c(E011_P_BARA)

#: The pressure PV-323203 discharges against [bar a]: 323C005, taken as atmospheric. PFD 702 at
#: 1.0 bar. V1's literal, "C005 is approx 1.0 bar (atmospheric vent node)".
C005_P_BARA = 1.0

# ======================================================================================
# The gas envelope: 323E011's shell and 323D011, one vapour space
# ======================================================================================
# There is no valve between the condenser and the tank beneath it, so the two vapour spaces are
# one gas envelope at one pressure. The shell side is the bore less the bundle it contains.

#: 323E011 shell inside diameter, effective tube length, tube count and tube OD [m, -].
#: Source: the datasheet, "inner diameter of 800 mm ... 382 individual BC.09 tubes ... outer
#: diameter of 25 mm ... effective length of 5,900 mm".
E011_SHELL_ID_M = 0.800
E011_TUBE_L_M = 5.900
E011_N_TUBES = 382
E011_TUBE_OD_M = 0.025

#: 323D011 inside diameter and straight shell height [m]. Source: the datasheet, "internal
#: diameter of 1,334 mm and a straight cylindrical shell height of 1,800 mm".
D011_ID_M = 1.334
D011_SHELL_M = 1.800

#: The envelope's volume [m3], 4.375: the condenser shell less its bundle, plus the tank.
#: Written as V1 writes it, operand for operand.
E011_VOL_M3 = (math.pi * 0.25 * E011_SHELL_ID_M ** 2 * E011_TUBE_L_M
               - E011_N_TUBES * math.pi * 0.25 * E011_TUBE_OD_M ** 2 * E011_TUBE_L_M
               + math.pi * 0.25 * D011_ID_M ** 2 * D011_SHELL_M)

#: 323F004 inside diameter and cylindrical shell height [m]. Source: `References/323F004 323E010
#: 323F010.md` §3.1, "an inside diameter of 1384 mm and a cylindrical shell height of 1800 mm".
F004_ID_M = 1.384
F004_SHELL_M = 1.800

#: 323F004's vapour space [m3], 1.083: its cylindrical shell above LIC-323505's 60 % level set
#: point, the heads left out. DECIDED 2026-10-07 (handoff B-51, the 323E011 instance; the "Typo
#: Rule"): the drum, the vapour line, the shell and the tank are one gas space, and V1's node
#: volume leaves the drum's out. It is added to the envelope's free volume as a constant — the
#: drum's own level does not move it — and it is not part of the envelope's liquid capacity
#: (323F004's liquor is its own unit's). V1 integrates the node on the envelope alone.
F004_VAPOUR_M3 = (math.pi * 0.25 * F004_ID_M ** 2 * F004_SHELL_M
                  * (1.0 - F004_LVL_SP_PCT / 100.0))

#: Condensate density [kg/m3], the datasheet's shell liquid outlet at 45 C.
E011_RHO_L_KGM3 = 961.00

#: The envelope full of liquid [kg], 4204: its volume at the condensate's density. Above it the
#: excess leaves as a published overflow (decision 11, applied 2026-10-03: a full 328D001 now
#: overflows into the shell, handoff A-15, and floods the envelope when LIC-323503's draw is
#: saturated; V1 has no ceiling and fills the node's vapour space to its floor).
E011_FULL_KG = E011_VOL_M3 * E011_RHO_L_KGM3

#: Vent molar mass [kg/kmol], PFD 702: 89.4 wt% NH3, 6.35 H2O, 3.3 N2, 0.81 O2, 0.14 CO2.
E011_MW_VAP = 17.395

# ======================================================================================
# PV-323203 and the floors of the node
# ======================================================================================

#: PV-323203 stroke at design as V1 runs it [%], linear on the stroke; the equivalence harness
#: keeps it. Source: V1 `main.py` R3232_E011_PV_OP_DES.
E011_PV_OP_DES_PCT = 25.0

#: PV-323203 on its vendor's trim (decision 23's class, decided 2026-10-17): Metso's DN 200 x 150
#: Neldisc, FpCv 634.57 (`data.control_valves.PV_323203`, item 22), its printed capacities as its
#: curve, its design stroke where it passes PFD 702's 440 kg/h on its normal case, 21.64 %.
#: PIC-323203 is seeded there.
PV_323203_OP_DES_PCT = design_stroke_pct(PV_323203, E011_MV_DES_KGH)
PV_323203_CHAR = PV_323203.characteristic

#: The smallest differential the vent law takes [bar]: V1's ``max(P - 1.0, 0.001)``. Below
#: 1.001 bar a the vent still passes the flow of this differential. The equivalence harness keeps it.
VENT_DP_FLOOR_BAR = 0.001

#: The port's: no reverse differential (handoff B-30, decided 2026-10-15; decision 80's class) —
#: PV-323203 passes nothing at or below the 1.0 bar a of 323C005, which it discharges to.
VENT_DP_MIN_BAR = 0.0

#: Floor on the node pressure [bar a]: V1's ``max(..., 0.1)``.
E011_P_FLOOR_BARA = 0.1

# ======================================================================================
# 323D011, the level tank, and the 718 draw
# ======================================================================================

#: Liquid residence time at the design draw [s]. Source: V1 `main.py` R3232_D011_M_TAU_S.
D011_M_TAU_S = 600.0

#: Design holdup [kg], 1187.2: the design draw over the residence time.
D011_M_DES_KG = D011_M718_DES_KGH / 3600.0 * D011_M_TAU_S

#: V1's reading of 323D011 at the design holdup [%], M / M_des x 50: LIC-323503's set point on V1's
#: law (``taps=False``); the OEM "maintains the flash tank condenser level tank at 50% capacity"
#: (`References/328E021 328E007 328P003 328P006.md`). Between LT-323503's taps the design holdup
#: reads `LT_323503_DES_PCT` (decision 233).
D011_LVL_SP_PCT = 50.0

#: 323D011's nominal volume [m3], 3.15 (Uhde's datasheet UD-AU-323-EC-0006 rev 00; NSF's as-built
#: drawing UD-AU-323-DZ-0006-005 rev 02 prints 3.277), the basis decision 219 takes, and its bore
#: [m2]. Each 2:1 head holds half of what the shell between its tangent lines does not.
D011_NOMINAL_M3 = 3.15
D011_AREA_M2 = math.pi * 0.25 * D011_ID_M ** 2
D011_HEAD_M3 = 0.5 * (D011_NOMINAL_M3 - D011_AREA_M2 * D011_SHELL_M)

#: LT-323503, a DP cell across N2B and N2A (the datasheet's principle sketch, p. 5): N2B 220 mm
#: above the bottom tangent line, N2A 270 mm below the top one, 1310 mm apart (Uhde's
#: UD-MR-G00-EC-0134, sheet p. 4, nozzle distance 1310 mm, 1065 kg/m3, 0 to 135.28 mbar) [m].
#: Decided 2026-11-16 (decision 233, handoff B-156): LI-323503 reads the liquid between the taps,
#: where V1 reads M / M_des x 50.
LT_323503_LO_M = 0.220
LT_323503_SPAN_M = 1.310

#: The sheet's density [kg/m3], PFD 718's (`RHO_718_KGM3`); the holdup at N2B [kg], 665.2, and per
#: 100 % between the taps [kg], 1950.0.
LT_323503_RHO_KGM3 = 1065.0
D011_M_LO_KG = LT_323503_RHO_KGM3 * (D011_HEAD_M3 + LT_323503_LO_M * D011_AREA_M2)
LT_323503_SPAN_KG = LT_323503_RHO_KGM3 * D011_AREA_M2 * LT_323503_SPAN_M

#: LT-323503's reading at the design holdup [%], 26.77: LIC-323503's set point between the taps,
#: 571 mm above the bottom tangent line, inside the sketch's L.L.L. (300 mm, 6.1 %) and H.L.L.
#: (1250 mm, 78.6 %).
LT_323503_DES_PCT = (D011_M_DES_KG - D011_M_LO_KG) / LT_323503_SPAN_KG * 100.0


def lt_323503_pct(m_kg: float) -> float:
    """LI-323503 [%]: the height of 323D011's liquid between LT-323503's taps (decision 233).

    Process utility
    ---------------
    What the board shows and LIC-323503 holds by LV-323503's draw, and what AC4's L2 stop on
    323P008A / B reads. A DP cell reads only between its taps: 0 % with 665 kg still in the tank
    (V1 reads 28.0 % there), 100 % at 2615 kg; the reading moves 1.22 times as far per kilogram as
    V1's 50 % over the design holdup.

    Equation
    --------
        LI = clamp( LI_des + (M - M_des) / (rho A L) . 100, 0, 100 )

    written as the departure from the design holdup, so the design holdup reads its set point
    exactly. Source: As-Built §CXXXIV.
    """
    return min(max(LT_323503_DES_PCT + (m_kg - D011_M_DES_KG) / LT_323503_SPAN_KG * 100.0, 0.0),
               100.0)


#: Floor on the tank holdup [kg]: V1's ``max(..., 1.0)``.
D011_M_FLOOR_KG = 1.0

#: LT-323503's low limit L2 [%], below which AC4 stops 323P008A and B: the motor blocks' interlock
#: IC2 on "LT-323503:VALUE<L2" (Uhde's application software UD-MR-G00-FF-0004, PC23.1.9 and
#: PC23.1.10, sheets 13 and 14, PDF pages 71-72, read from the scans). The archive holds no limit
#: value; 5 % is the plant DCS's, read back by the process engineer on 2026-10-13 (decision 103).
#: Decided 2026-10-14 (handoff B-93). V1 has no such trip.
LT_323503_L2_PCT = 5.0

#: The L2 limit's hysteresis [% of span]: the pumps stopped below 5 % run again at 7 %. A STATED
#: STAND-IN — the limit's hysteresis is a DCS database value the archive does not hold — the
#: 2-unit convention TT-322015's H2 keeps (V1's 2 K), decided by the process engineer on
#: 2026-10-15 (handoff B-96, logged in Open data gaps).
LT_323503_L2_HYST_PCT = 2.0

#: LV-323503 and FV-323418 strokes at design [%], and their trims. DECIDED 2026-09-30 (handoff
#: B-44): both are Valtek modified equal-percentage valves, placed where their Kvs pass the
#: design flows on the vendor's normal cases (`ureasim.data.control_valves`) — LV-323503, Kvs 25,
#: the whole of PFD 718 at 52.86 %; FV-323418, Kvs 4, the 718B leg at 78.45 %. V1 runs both
#: linear from 50 % (``R3232_LV503_OP_DES``, ``R3232_FIC418_OP_DES``).
LV503_OP_DES_PCT = design_stroke_pct(LV_323503, D011_M718_DES_KGH)
FIC418_OP_DES_PCT = design_stroke_pct(FV_323418, M718B_DES_KGH)
LV503_CHAR = LV_323503.characteristic
FV418_CHAR = FV_323418.characteristic

#: PFD 718 effective density [kg/m3], the lean carbamate FIC-323418 meters by volume.
RHO_718_KGM3 = 1065.0

#: FT-323418's time constant [s]. Source: V1 `main.py`, ``_fic_flow(..., tau_s=45.0, ...)``.
FT_323418_TAU_S = 45.0

#: The 718A leg's transport lag AT THE DESIGN FLOW [s], and the line inventory it implies
#: [kg]; the live lag is that inventory over the live flow (V1 report D-8).
M718A_TAU_S = 45.0
M718A_LINE_KG = M718A_DES_KGH * M718A_TAU_S / 3600.0

#: Ceiling on the 718A lag [s]. Source: V1 `main.py` FEED_TD_MAX_S, through
#: ``_feed_transport_td_s``.
M718A_TAU_MAX_S = 3600.0

# ======================================================================================
# The energy balance at design
# ======================================================================================

#: Specific heat of the LP carbamate liquor [kJ/(kg.K)]. V1's R3232_CP, "UN-SOURCED on purpose":
#: no single equation holds for the reactive liquor, the frozen band for the solution is 3.2 to
#: 3.8, and 3.0 is a lean-liquor value above the pure salt's 2.1. LOCKED in V1: the back-solved
#: latent heats below are struck on it.
CP_LP_CARBAMATE = 3.0

#: Condenser duty at design [kW], the datasheet's 3440.
E011_Q_DES_KW = 3440.0

#: Duty per kelvin of shell-to-cooling-water difference [kW/K], 344.
E011_UA_KW = E011_Q_DES_KW / (E011_T_C - E011_CW_T_C)

#: The inlets' sensible heat onto the 45 C condensate at design [kW], 274.9, and the latent heat
#: of the condensed gas that closes the balance on the design duty [kJ/kg], 2038.7. Written as
#: V1 writes them, operand for operand.
E011_SENS_KW = (((E011_M701_DES_KGH + E011_RECON_KGH) * (E011_T701_C - E011_T_C)
                 + E011_M786_DES_KGH * (E011_T786_C - E011_T_C)
                 + E011_M321_DES_KGH * (E011_T321_C - E011_T_C)
                 + E011_M402_DES_KGH * (E011_T791_C - E011_T_C))
                / 3600.0 * CP_LP_CARBAMATE)
E011_LAMV_KJKG = ((E011_Q_DES_KW - E011_SENS_KW) / (E011_MCOND_DES_KGH / 3600.0))

# ======================================================================================
# The three controllers, as V1 seeds them
# ======================================================================================

#: PIC-323203's gain as the DCS table gives it [% of output per % of span], 0.60, 100 s,
#: derivative off. V1 applies this number per bar.
PIC_323203_KC_TABLE = 0.6

#: PT-323203's calibrated range [bar]: 0 to 1 bar g, gauge pressure, mounted on 323F004 (PIC
#: with a high alarm, normal 1.1 bar a). Source: Uhde loop summary UD-MR-323-EC-0001 rev 1,
#: loop P 323203, sheet 1/2, line D07 (vendor archive, scanned, read from the page image).
PT_323203_SPAN_BAR = 1.0

#: PIC-323203: DIRECT acting — a node above set point opens the vent. The table's gain rescaled
#: to the engineering units the loop runs in: 0.60 %/% on a 1 bar span is 60 %/bar. V1 runs
#: 0.60 %/bar, a hundred times weaker; the port departs from it by decision of 2026-09-27
#: (handoff B-32, As-Built §XXXII.4).
PIC_323203_KC = PIC_323203_KC_TABLE * 100.0 / PT_323203_SPAN_BAR
PIC_323203_TI_S = 100.0
PIC_323203_TD_S = -1.0
PIC_323203_SP_LO_BARA = 0.5
PIC_323203_SP_HI_BARA = 2.0

#: LIC-323503: DIRECT acting on the total 718 draw demand. The DCS pair, "323D011,ACA": a level
#: PV in % is already per cent of span, so the table's gain applies unscaled.
LIC_323503_KC = 1.8
LIC_323503_TI_S = 120.0

#: FIC-323418's gain as the DCS table gives it [% of output per % of span], "ACA FROM 323P8A/B",
#: 1.00, 100 s. V1 applies it per kg/h, carried to m3/h times the density: 1065 %/(m3/h).
FIC_323418_KC_TABLE = 1.0

#: FT-323418's calibrated range [m3/h]: 0 to 10, volume flow, a magnetic inductive meter. Source:
#: Uhde loop summary UD-MR-323-EC-0001 rev 1, loop F 323418, sheet 1/2, line D07 (vendor archive,
#: scanned, read from the page image): "ACA fr 323P008A/B Lean Carb. Pump", line 25-ACA4-323011,
#: 0.6 / 3.3 / 8.0 m3/h, 45 C, 1065.0 kg/m3.
FT_323418_SPAN_M3H = 10.0

#: FIC-323418: a VOLUMETRIC loop in m3/h. The table's gain rescaled to the loop's engineering
#: units, 1.00 %/% on a 10 m3/h span, 10 %/(m3/h); V1 runs 1065, and the port departs from it by
#: decision of 2026-09-30 (handoff B-41).
FIC_323418_KC = FIC_323418_KC_TABLE * 100.0 / FT_323418_SPAN_M3H
FIC_323418_TI_S = 100.0
FIC_323418_TD_S = -1.0
FIC_323418_SP_HI_M3H = 8000.0 / RHO_718_KGM3

# ======================================================================================
# SV32357, the node's relief (decided 2026-10-01, handoff A-16)
# ======================================================================================

#: SV32357 on 323D011's nozzle N6, line AW3-323208-EG07D (P&ID 103/2): set 5.0 bar g, 6.01 bar a,
#: on the sheet's 1.010 bar a (Uhde UD-RL-323-EC-0006). Sized on liquid, it relieves the node's
#: vapour here, so it reseats on the gas blowdown, 10 % of set below, at 5.51 bar a.
SV32357_SET_BARA = RELIEF_DEVICES["SV32357"].set_bara
SV32357_RESEAT_BARA = gas_reseat_bara(RELIEF_DEVICES["SV32357"])

#: Its orifice F, 240.53 mm2 [m2] (Sempell UD-RL-G00-DZ-0001-001 page 91, rated on liquid at
#: alpha_w 0.644), and its orifice's gas coefficient, 0.922, Sempell's for it in gas service
#: (decision 130; 0.917 assumed until 2026-10-16, A-16 option b).
SV32357_AREA_M2 = RELIEF_SIZING["SV32357"].area_mm2 * 1.0e-6
SV32357_KD = GAS_KD_FULL_LIFT

__all__ = [
    "E011_M701_DES_KGH", "E011_M786_DES_KGH", "E011_M321_DES_KGH", "E011_M402_DES_KGH",
    "E011_IN_DES_KGH", "E011_RECON_KGH", "D011_M718_DES_KGH", "E011_MV_DES_KGH",
    "E011_MCOND_DES_KGH", "M718A_DES_KGH", "M718B_DES_KGH",
    "E011_GAS_FEED_DES_KGH", "E011_CONDENSATION_CAPACITY_DES_KGH",
    "E011_T_C", "E011_T701_C", "E011_T786_C", "E011_T321_C", "E011_T791_C", "E011_CW_T_C",
    "E011_P_BARA", "TSAT_E011_DES_C", "C005_P_BARA",
    "E011_SHELL_ID_M", "E011_TUBE_L_M", "E011_N_TUBES", "E011_TUBE_OD_M", "D011_ID_M",
    "D011_SHELL_M", "E011_VOL_M3", "F004_ID_M", "F004_SHELL_M", "F004_VAPOUR_M3",
    "E011_RHO_L_KGM3", "E011_FULL_KG", "E011_MW_VAP",
    "E011_PV_OP_DES_PCT", "PV_323203_OP_DES_PCT", "PV_323203_CHAR", "VENT_DP_FLOOR_BAR", "VENT_DP_MIN_BAR", "E011_P_FLOOR_BARA",
    "D011_M_TAU_S", "D011_M_DES_KG", "D011_LVL_SP_PCT", "D011_M_FLOOR_KG", "LT_323503_L2_PCT", "LT_323503_L2_HYST_PCT",
    "D011_NOMINAL_M3", "D011_AREA_M2", "D011_HEAD_M3", "LT_323503_LO_M", "LT_323503_SPAN_M",
    "LT_323503_RHO_KGM3", "D011_M_LO_KG", "LT_323503_SPAN_KG", "LT_323503_DES_PCT", "lt_323503_pct",
    "LV503_OP_DES_PCT", "FIC418_OP_DES_PCT", "LV503_CHAR", "FV418_CHAR", "RHO_718_KGM3", "FT_323418_TAU_S",
    "M718A_TAU_S", "M718A_LINE_KG", "M718A_TAU_MAX_S",
    "CP_LP_CARBAMATE", "E011_Q_DES_KW", "E011_UA_KW", "E011_SENS_KW", "E011_LAMV_KJKG",
    "PIC_323203_KC_TABLE", "PT_323203_SPAN_BAR", "PIC_323203_KC", "PIC_323203_TI_S", "PIC_323203_TD_S", "PIC_323203_SP_LO_BARA",
    "PIC_323203_SP_HI_BARA", "LIC_323503_KC", "LIC_323503_TI_S",
    "FIC_323418_KC_TABLE", "FT_323418_SPAN_M3H", "FIC_323418_KC", "FIC_323418_TI_S",
    "FIC_323418_TD_S", "FIC_323418_SP_HI_M3H", "SV32357_SET_BARA", "SV32357_RESEAT_BARA",
    "SV32357_AREA_M2", "SV32357_KD",
]
