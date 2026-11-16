"""Unit 321 — NH3 pumping station design constants.

What this covers
----------------
321D003, the ammonia feed drum, and 321P002 A/B, the two triplex reciprocating pumps that
put fresh ammonia into the synthesis loop through the 322F001 ejector. Also the N/C feed
ratio constants, because the ratio block lives in this section.

Source discipline
-----------------
Every constant below carries where it came from. Three provenances appear, and they are not
interchangeable:

* **datasheet** — pump bore, stroke, plunger count, drum dimensions. These are measurements
  of hardware.
* **PFD / design basis** — the design motive flow, the design CO2 rate, the design N/C.
* **field calibration** — `PUMP_ETA_V`, fitted to a DCS startup trace. Its own caveat is
  carried with it verbatim, because the fit is degenerate and a future reader has to know.

Nothing here is a "reasonable value".
"""

from __future__ import annotations

import math

# ======================================================================================
# Ammonia at the feed condition
# ======================================================================================

#: Effective density of the ammonia feed [kg/m3] at 25 C.
#: Source: V1 `backend/main.py` NH3_RHO, with its NIST validation note carried verbatim —
#: saturated liquid is 602.96 kg/m3 at 25 C; 604.8 is the COMPRESSED liquid at 25 C and
#: about 29 bar a, which is the pump suction condition. The constant is therefore the
#: compressed-liquid density at design suction, not a transcription error.
NH3_RHO = 604.8

#: Liquid ammonia specific heat [J/(kg.K)] near 25 C. Source: V1 `main.py` CP_NH3.
CP_NH3 = 4740.0

#: Liquid ammonia isobaric expansivity [1/K] near 25 C. Source: V1 `main.py` BETA_NH3.
BETA_NH3 = 1.9e-3

#: Battery-limit ammonia supply temperature to 321D003 [C]. Source: V1 `main.py`
#: T_BL_FEED_C, the design feed temperature.
T_BL_FEED_C = 25.0

# ======================================================================================
# 321P002 A/B — triplex reciprocating (positive-displacement) pumps
# ======================================================================================
# A positive-displacement machine has no head/flow curve: it delivers its swept volume per
# revolution whatever the discharge pressure, up to its relief. That is why this section has
# no compressor-style map and why the flow is a function of SPEED alone.

#: Plunger diameter [m]. Source: datasheet, V1 `main.py` PUMP_D.
PUMP_D = 0.140

#: Stroke length [m]. Source: datasheet, V1 `main.py` PUMP_L.
PUMP_L = 0.205

#: Number of plungers. Triplex. Source: datasheet, V1 `main.py` PUMP_N_PLGR.
PUMP_N_PLGR = 3

#: Volumetric efficiency [-]. **Field-calibrated**, and the caveat matters.
#:
#: Source: V1 `main.py` PUMP_ETA_V, whose note is carried in full here because the fit is
#: degenerate: a DCS startup trace of 3 June 2025, temperature-separated fit, gives
#: 0.980 +/- 0.001 (n = 5, flat across 100-142 bar g, so a design value rather than a
#: low-slip artefact). It superseded an assumed 0.95, which ran 3.2 % under.
#:
#: The degeneracy: FY-321401 was shown to be a fixed-constant DCS compute tag (the 28 June
#: warm-feed slope is -0.07 % against -2.1 % predicted for a live density; ISA-5.1 letter Y),
#: so the fit constrains only the PRODUCT eta_v . rho_cfg = 601.6 kg/m3. Taking 0.980 assumes
#: rho_cfg = rho_sat(17.6 C) = 613.9 kg/m3.
#:
#: It is conservation-neutral either way: eta_v cancels in the closed-loop ratio
#: reconstruction (rpm is back-computed, then mass is rebuilt), so only the SIC-321950 rpm
#: display shifts.
PUMP_ETA_V = 0.980

#: Mechanical efficiency [-], for the shaft-power display. Source: datasheet.
PUMP_ETA_M = 0.915

#: Swept volume per revolution [m3/rev]: (pi/4) D^2 L n_plungers.
#: Derived from the datasheet geometry above, never entered as a literal, so a change to the
#: bore or the stroke cannot leave a stale volume behind.
PUMP_V_PER_REV = (math.pi / 4.0) * PUMP_D ** 2 * PUMP_L * PUMP_N_PLGR

#: Rated speed [rpm]. Source: datasheet.
PUMP_RATED_RPM = 152.0

#: Minimum continuous speed [rpm]. Source: datasheet.
PUMP_MIN_RPM = 37.0

#: Normal operating speed [rpm]. Source: datasheet.
#:
#: On the datasheet's own capacities — 67.1 m3/h here and 82 m3/h at rated — the swept volume
#: above reproduces 66.91 and 82.02 at eta_v = 0.95. That agreement is the check that the
#: GEOMETRY is right, and it belongs to the superseded efficiency. At the field-calibrated
#: eta_v = 0.980 the model passes 69.03 and 84.61 instead: the calibration deliberately
#: departs from the datasheet capacity, which is what `PUMP_ETA_V`'s note is about.
PUMP_NORMAL_RPM = 124.0

#: Rated motor current [A], a display proxy. Source: V1 `main.py` PUMP_RATED_I, anchored on
#: the DCS reading of 43.9 A at 131 rpm (86 % of rated).
PUMP_RATED_I = 51.0

#: Idle current drawn by a stopped machine [A] — the instrument's own live zero, not a
#: physical draw. Source: V1 `main.py` `pump_current_A`.
PUMP_IDLE_I = 0.2

#: Time constant of the VOITH torque-converter scoop [s]. The controller commands an
#: opening; the converter takes about this long to get there. Source: V1 `main.py`, the
#: `alpha = min(1.0, dt / 2.0)` first-order approach in the pump loop.
PUMP_SCOOP_TAU_S = 2.0

#: SI-321950 / SI-321951 range [rpm]: 0-180 on Uhde's loop summaries, UD-MR-321-EC-0001 rev 1, line
#: D07 (S 321950 PDF page 70, S 321951 page 72), and on both DCS faceplates. The speed controllers'
#: PV in the model is the machine's opening, per cent of the rated 152 rpm, so the span is 118.4 %
#: of it.
SI_321950_SPAN_RPM = 180.0

#: SIC-321950 / SIC-321951, the speed controllers, on the plant DCS's tuning table
#: (`References/Master_PID_Tuning_Constants.md`, read again from the faceplate photographs, 321-1
#: faceplates, 10 July 2026): 321P002A 4.00 and 35 s, 321P002B 1.20 and 50 s, Td -1 on both — the
#: DCS's sentinel for derivative off, written 0 here because the per-cent-of-span `Controller` form
#: uses a derivative time as given. Decided 2026-10-08 (decision 10's class, a gain per cent of its
#: transmitter's span): the table's gain, on 0-180 rpm, read onto the PV the model carries, per
#: cent of the rated speed — 3.378 and 1.013. V1 seeds both at 2.0 and 8 s (``State``), no source.
SIC_321950_KC_TABLE = 4.00
SIC_321950_TI_S = 35.0
SIC_321951_KC_TABLE = 1.20
SIC_321951_TI_S = 50.0
SIC_TD_S = 0.0
SIC_321950_KC = SIC_321950_KC_TABLE * PUMP_RATED_RPM / SI_321950_SPAN_RPM
SIC_321951_KC = SIC_321951_KC_TABLE * PUMP_RATED_RPM / SI_321950_SPAN_RPM

#: Hydraulic efficiency used for the discharge temperature rise [-].
#: Source: V1 `main.py` ETA_PUMP_HYD.
ETA_PUMP_HYD = 0.85

# ======================================================================================
# 321D003 — ammonia feed drum
# ======================================================================================

#: Internal diameter [m]. Source: datasheet, V1 `main.py` TANK_ID.
TANK_ID = 0.970

#: Cylindrical height [m]. Source: datasheet, V1 `main.py` TANK_H.
TANK_H = 1.400

#: Shell volume [m3], (pi/4) D^2 H. Derived, not entered.
TANK_VOL = (math.pi / 4.0) * TANK_ID ** 2 * TANK_H

#: LIC-321501 working-level set point [fraction of shell].
#: Source: V1 `main.py` TANK_LEVEL_SP_FRAC, the design working level.
TANK_LEVEL_SP_FRAC = 0.65

#: Feed-drum makeup level gain [t/h per unit level fraction].
#: Source: V1 `main.py` TANK_LIC_KP_TH.
TANK_LIC_KP_TH = 80.0

#: Battery-limit import line capacity [t/h], the makeup valve fully open.
#: Source: V1 `main.py` TANK_BL_MAX_TH.
TANK_BL_MAX_TH = 90.0

#: Drum top operating pressure [bar g] at the design state. Source: V1 `main.py` state seed
#: `tank_P_top_barG`. At 25 C the ammonia saturation pressure is about 10.0 bar a, so this
#: is roughly 3 bar of sub-cooling margin before PDYI-321203/204 approach their trip.
TANK_P_TOP_DES_BARG = 12.3

#: Static loss between the drum tapping and the pump suction [bar].
#: Source: V1 `main.py`, the `- 0.15` term in the suction-pressure expression.
SUCTION_LOSS_BAR = 0.15

#: Level below which the suction is treated as lost [fraction].
#: Source: V1 `main.py`, `suct_open = XV_321901 and tank_level_frac > 0.05`. It is also one
#: of the 21.2 main-trip initiators.
TANK_LEVEL_MIN_FRAC = 0.05

# ======================================================================================
# The N/C feed ratio
# ======================================================================================
# N/C is moles of nitrogen per mole of carbon. Each NH3 carries one N and each CO2 one C, so
#
#     N/C = (m_NH3 / m_CO2) . (M_CO2 / M_NH3)
#
# and the cascade inverts it. Both directions are named, because writing one and dividing by
# it at the call site is how a factor ends up applied the wrong way round.

#: Ammonia molar mass [g/mol] as the ratio block uses it. Source: V1 `main.py` M_NH3.
#: NOTE this is 17.031, while `core.stream.MW_COMP["NH3"]` is 17.0304 — V1 carries both, and
#: the two are NOT interchanged: the ratio block uses this one, the reactor couples use the
#: atom-consistent one. Substituting either would move a published number.
M_NH3 = 17.031

#: Carbon dioxide molar mass [g/mol] as the ratio block uses it. Source: V1 `main.py` M_CO2.
#: Same note as `M_NH3`: `core.stream.MW_COMP["CO2"]` is 44.0098.
M_CO2 = 44.009

#: Mass ratio to molar N/C: N/C = (m_NH3/m_CO2) . NC_FACTOR. Equals 2.584.
NC_FACTOR = M_CO2 / M_NH3

#: Molar N/C to mass demand: m_NH3 = (N/C) . NC_TO_MASS . m_CO2. The exact reciprocal.
NC_TO_MASS = M_NH3 / M_CO2

#: Design molar N/C set point and PV. Source: V1 `main.py` RATIO_SP_DES / RATIO_PV_DES, the
#: live-probed settled ratio at the Cluster-2023 design point (fresh N/C >= 2.0).
RATIO_SP_DES = 2.0231315310702604

#: Design total CO2 feed [kg/h] — 100 % load. Source: PFD, V1 `main.py` CO2_DES_KGH.
CO2_DES_KGH = 54618.0

#: Fraction of design CO2 feed below which the molar N/C is declared meaningless.
#: Source: V1 `main.py`, the L3-3 measurement-validity gate. Below this the divisor collapses
#: and the ratio is numerically garbage, so the last good value is held and the cascade is
#: frozen rather than fed a number that means nothing.
RATIO_PV_MIN_LOAD_FRAC = 0.05

# ======================================================================================
# The pump discharge and the BL transit
# ======================================================================================

#: Design motive liquid-ammonia stream to the 322F001 ejector [kg/h].
#: Source: V1 `main.py` EJ_MOTIVE_NH3_DES, re-pinned to the physical Cluster-2023 design
#: point as `RATIO_PV_DES . NC_TO_MASS . CO2_DES_KGH`. It is carried as the literal V1
#: carries, so the boot pin does not depend on the product re-associating identically.
EJ_MOTIVE_NH3_DES = 42762.05427809782

#: Nominal downstream synthesis pressure [bar a] — the 321P002 discharge header.
#: Source: V1 `main.py` P_SYN_DOWN_BAR.
P_SYN_DOWN_BAR = 165.0

#: Design NH3 feed (suction) pressure [bar a], datasheet normal. Source: V1 `main.py`
#: PT_FEED_DESIGN_BARA.
PT_FEED_DESIGN_BARA = 20.0

#: Battery-limit to synthesis-loop transport dead time AT DESIGN FLOW [s].
#: Source: V1 `main.py` FEED_TD_S — a MEASUREMENT, not a fudge: the PT-329201 FOPTD fit from
#: the 3 June 2025 DCS anchor set, R2 = 0.9888, bracketed at or below 572 s. What V1's
#: predecessor had wrong was not the number but that it did not MOVE with flow.
FEED_TD_S = 345.0

#: Cap on a feed-line dead time [s], so a near-zero flow gives a long-but-finite delay.
#: Source: V1 `main.py` FEED_TD_MAX_S.
FEED_TD_MAX_S = 3600.0

#: Ammonia inventory of the battery-limit line [kg], BACK-SOLVED from the measured dead time
#: at the design flow: `m_des . td_des / 3600`. Derived rather than entered, so the line
#: inventory and the measured dead time cannot disagree.
FEED_NH3_LINE_KG = EJ_MOTIVE_NH3_DES / 3600.0 * FEED_TD_S

#: Torque-converter opening [%] that delivers the design motive flow. DERIVED from the
#: constants above — never a literal — so it stays consistent with `PUMP_ETA_V` by
#: construction. Source: V1 `main.py` `_OPEN_DES_B`. At eta_v = 0.980 it is 83.561 %.
PUMP_OPEN_DES_PCT = ((EJ_MOTIVE_NH3_DES / NH3_RHO)
                     / (PUMP_V_PER_REV * PUMP_ETA_V * 60.0) / PUMP_RATED_RPM * 100.0)

#: FY-321404's range [molar N/C]: 0-4 "Ratio" on Uhde's loop summaries, UD-MR-321-EC-0001 rev 1,
#: line D07 (F 321404A PDF page 8, F 321404B page 9). FFIC-321404A / B read their PV and set point
#: per cent of it.
FY_321404_SPAN = 4.0

#: FY-321404 on the DCS's formula over the engine's ratio [-], 1.0317 at design: the DCS divides FT-321401
#: by the feed gas less the passivation air, x 44 / 17 (Uhde's functional diagram UD-MR-321-FF-0002 rev 00,
#: PDF page 4; closes on `References/DCS Trends/Book2.xlsx` to a median of 0.0001), where the engine's
#: ratio is molar on the CO2 alone; the air is 2.97 % of the gas mass and 44 / 17 against 44.009 / 17.031
#: is 1.0016 (As-Built §CXXX.4 and §CXXX.6; `Tests and Reports/reports/Session 120 research B-127 B-128
#: B-135.md`). The engine publishes FFIC-321404 times it and takes its set point divided by it, so the
#: trainee reads the plant's number. Decided 2026-11-16 (decision 235, handoff B-128 (b)).
#: shortcut: a fixed design factor, about 1.4 % low at 70 % load where the plant's constant air inflates
#: its display; modelling the air needs FIC-320402 at the boundary, which decision 73 keeps out of scope.
FY_321404_DCS_FACTOR = 1.0317

#: FFIC-321404A / B, the N/C ratio controllers, one per machine, on the plant DCS's tuning table
#: (`References/Master_PID_Tuning_Constants.md`, "FFIC FOR 321P002A / B"): 1.00 and 100 s, 1.00 and
#: 90 s, Td -1 (off, written 0 here), filter 0 s; the table's 2 % deadband is not modelled (B-28,
#: decided 2026-10-09: no measurement noise). Uhde's functional diagram UD-MR-321-FF-0002 pages 2-3
#: draws each as a PI controller on FY-321404 whose output, per cent of SIC-321950's / SIC-321951's
#: maximum (SI 0-180 rpm), is its speed controller's external set point, and whose balance follows
#: the speed controller's working set point. Decided 2026-10-09 (B-85): built as drawn, where V1
#: computes the machines' opening from the ratio set point open loop.
FFIC_321404A_KC = 1.00
FFIC_321404A_TI_S = 100.0
FFIC_321404B_KC = 1.00
FFIC_321404B_TI_S = 90.0


__all__ = [
    "NH3_RHO", "CP_NH3", "BETA_NH3", "T_BL_FEED_C",
    "PUMP_D", "PUMP_L", "PUMP_N_PLGR", "PUMP_ETA_V", "PUMP_ETA_M", "PUMP_V_PER_REV",
    "PUMP_RATED_RPM", "PUMP_MIN_RPM", "PUMP_NORMAL_RPM", "PUMP_RATED_I", "PUMP_IDLE_I",
    "PUMP_SCOOP_TAU_S", "SI_321950_SPAN_RPM", "SIC_321950_KC_TABLE", "SIC_321950_TI_S",
    "SIC_321951_KC_TABLE", "SIC_321951_TI_S", "SIC_TD_S", "SIC_321950_KC", "SIC_321951_KC",
    "ETA_PUMP_HYD", "PUMP_OPEN_DES_PCT", "FY_321404_SPAN", "FY_321404_DCS_FACTOR", "FFIC_321404A_KC",
    "FFIC_321404A_TI_S", "FFIC_321404B_KC", "FFIC_321404B_TI_S",
    "TANK_ID", "TANK_H", "TANK_VOL", "TANK_LEVEL_SP_FRAC", "TANK_LIC_KP_TH",
    "TANK_BL_MAX_TH", "TANK_P_TOP_DES_BARG", "SUCTION_LOSS_BAR", "TANK_LEVEL_MIN_FRAC",
    "M_NH3", "M_CO2", "NC_FACTOR", "NC_TO_MASS", "RATIO_SP_DES", "CO2_DES_KGH",
    "RATIO_PV_MIN_LOAD_FRAC",
    "EJ_MOTIVE_NH3_DES", "P_SYN_DOWN_BAR", "PT_FEED_DESIGN_BARA",
    "FEED_TD_S", "FEED_TD_MAX_S", "FEED_NH3_LINE_KG",
]
