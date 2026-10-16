"""Design constants for 322F001, the HP carbamate ejector.

What the equipment is
---------------------
A liquid-liquid jet pump with no moving parts. Liquid ammonia from the 321P002 A/B triplex
pumps is the motive stream; it entrains the 322E003 HP scrubber's carbamate overflow and
delivers the mixture to 322E002. It is the circulator of the whole HP synthesis loop: nothing
else moves liquid round 322E002 -> 322R001 -> 322E003 -> 322F001.

Sources, in the resolution order of the agent directives §4
------------------------------------------------------------
* `References/Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md` — streams 116 (motive
  ammonia, mass %) and 206 (the scrubber overflow this machine entrains).
* `References/Datasheets/322F001 Design Calculations.pdf` — a 12-page SCAN with no text
  layer. The nozzle and mixing-throat areas CANNOT be read out of it, which is why they are
  back-solved below rather than entered.
* The 322F001 DDS, Remarks 3-5 — the HV-322602 nozzle free-area map, which IS a primary
  source for the one geometric quantity the spindle model needs.
* V1 `backend/main.py`, the `EJ_*` block, for values V1 itself back-solved or reconciled.

What is deliberately not here
------------------------------
V1 carries six constants in this block that nothing in V1 reads: `EJ_SPINDLE_R` (2.1517),
`EJ_STALL_PHI` (0.20), `EJ_STALL_REC` (0.35), `EJ_STALL_EXP` (2.0), `EJ_DES_TOTAL_NAMEPLATE`
(98 320 kg/h) and the `EJ_DES_MASSPCT` table behind it. The first four were the fitted
entrainment and stall law that the constant-area closure replaced; the last two are a
superseded datasheet discharge that V1's own comment records as FALSIFIED — it does not atom-
close against the reconciled stripper-top and reactor-offgas vectors. They are recorded here
as provenance, in this paragraph, rather than carried as live constants nothing reads.

V1 also carries `EJ_T_TAU_S = 120.0`, the thermal time constant of the discharge and suction
carbamate inventory, and applies it to the published TT-322012. The ejector model is a pure
function with no state to hang a lag on — V1's own no-flow branch says so explicitly — so the
constant lives with the display lags (`data.indicator_lags`), whose scheduled step relaxes
TT-322012 on it (`units.synthesis.indicators`, session 41; handoff B-11 closed on it 2026-10-07).
"""

from __future__ import annotations

import math

from ureasim.control import jet_pump
from ureasim.core.stream import MW_COMP
from ureasim.core.units_of_measure import ABSOLUTE_ZERO_C, ATM_BARA, G_ACC
from ureasim.data.unit_322e003 import OVERFLOW_DES_KMOLH
from ureasim.data.unit_321 import (
    BETA_NH3,
    CP_NH3,
    EJ_MOTIVE_NH3_DES,
    ETA_PUMP_HYD,
    NH3_RHO,
    P_SYN_DOWN_BAR,
    SUCTION_LOSS_BAR,
    T_BL_FEED_C,
    TANK_H,
    TANK_LEVEL_SP_FRAC,
    TANK_P_TOP_DES_BARG,
)

# ======================================================================================
# The motive stream
# ======================================================================================

#: Design motive liquid-ammonia flow [kg/h]. Re-exported from `unit_321`, where it is the
#: 321P002 A/B delivery, so the pumps and the ejector cannot disagree about it.
MOTIVE_DES_KGH = EJ_MOTIVE_NH3_DES

#: Motive-stream composition [mass %]. Source: PFD stream 116, "Ammonia L.", liquid row.
#:
#: The motive is NOT pure ammonia, and that matters beyond bookkeeping. The plant ammonia's
#: trace methane, hydrogen, nitrogen and water are the ONLY source of the CH4 and H2 that
#: leave in the 322E003 vent, which PFD 204 puts at 3.84 and 2.03 kmol/h. With a pure motive
#: the reactor recycle tear had to create them out of nothing. The pump and its flow meter
#: see the whole liquid stream, so `MOTIVE_DES_KGH` is the stream mass and this is its split.
#: Source: V1 finding A-2.
#:
#: At the design motive this row delivers 4.00 kmol/h of CH4 and 2.12 of H2, so the inert
#: balance closes to within 4 %. V1's own comment quotes 3.81 and 2.02 for the same row;
#: those are the values at the SUPERSEDED 40 756 kg/h motive and were not updated when the
#: motive was re-pinned to 42 762 kg/h. The row is unchanged — only the flow it multiplies.
MOTIVE_MASS_PCT = {"NH3": 99.67, "CH4": 0.15, "H2": 0.01, "N2": 0.04, "H2O": 0.08}

#: Motive mass fractions [-], normalised. The PFD row sums to 99.95, not 100.
MOTIVE_W = {k: MOTIVE_MASS_PCT.get(k, 0.0) / sum(MOTIVE_MASS_PCT.values()) for k in MW_COMP}

#: Real static pressure at the 321P002 suction at the design drum state [bar g], 12.204.
#: Derived from the drum's own design state — top pressure, working level, shell height and
#: the tapping loss — rather than entered, so a change to any of those moves it.
P_SUCTION_DES_BARG = (TANK_P_TOP_DES_BARG
                      + (NH3_RHO * G_ACC * TANK_LEVEL_SP_FRAC * TANK_H) / 1e5
                      - SUCTION_LOSS_BAR)

#: Motive temperature at the ejector nozzle at design [deg C], 28.934 — TI-321020.
#:
#: Reconstructed from the live pump-thermal path at the design drum state rather than taken
#: as a literal, because the number the 322E002 heat balance needs is the temperature the
#: RUNNING loop actually feeds. A pure-ammonia stream at the battery limit is 25 C; the
#: pumps put roughly 4 K into it across 152 bar of differential. Assuming 170 C here — which
#: an earlier version of V1 did — moves the carbamate condenser's mixed feed temperature by
#: tens of degrees and takes the UA back-calculation with it.
#:
#: This duplicates the arithmetic of `units.feed.station.pump_discharge_temperature_c`, which
#: cannot be imported here: `data` sits below `units` and an upward import is a defect. The
#: equivalence suite asserts the two agree to the bit, so they cannot drift apart silently.
MOTIVE_T_DES_C = T_BL_FEED_C + (
    max(0.0, P_SYN_DOWN_BAR - (P_SUCTION_DES_BARG + ATM_BARA)) * 1e5
    / (NH3_RHO * CP_NH3)
    * (BETA_NH3 * (T_BL_FEED_C + ABSOLUTE_ZERO_C) + (1.0 - ETA_PUMP_HYD) / ETA_PUMP_HYD))

# ======================================================================================
# The entrained stream — the 322E003 overflow
# ======================================================================================

#: Design suction composition [kmol/h] — the 322E003 HP scrubber overflow, imported.
#:
#: The scrubber produces this stream, so `unit_322e003` owns it and derives it from the
#: reactor off-gas, the weak-carbamate wash and the saturated inert vent. It landed here as
#: a literal only while 322E003 was unported; the derived vector reproduces that literal to
#: the bit, so nothing about the ejector's design point moved when the two were joined.
#:
#: The number itself is V1 finding A-2, which replaced an earlier literal pair (NH3 1234.5 /
#: CO2 458.4 kmol/h) that had been pushing 89.4 kmol/h of NH3 and 60.7 of CO2 out through
#: the vent in order to close the scrubber against a pure motive.

#: The same stream by mass [kg/h].
SUCTION_DES_KGH = {k: OVERFLOW_DES_KMOLH.get(k, 0.0) * MW_COMP[k] for k in MW_COMP}

#: Design suction total [kg/h], 57 561.3.
SUCTION_DES_TOTAL_KGH = sum(SUCTION_DES_KGH.values())

#: Design suction mass split [-]. The default the entrained stream carries when the live
#: 322E003 sump composition is not supplied.
CARBAMATE_FRAC = {k: SUCTION_DES_KGH[k] / SUCTION_DES_TOTAL_KGH for k in MW_COMP}

#: Carbamate suction temperature [deg C] — the 322E003 overflow.
#:
#: A pseudo-temperature, not a thermowell reading: the carbamate heat of mixing is lumped
#: into it so the ejector's discharge enthalpy comes out right without a separate mixing
#: term. PFD stream 206 is 165 C and the plant's TT-322002 reads a mean of 165.7 C, so this
#: value is 13 C above both and must not be published as an instrument. Since 2026-10-07
#: (handoff B-16, decided) 322E003's TT-322002 is pinned on the PFD's 165 C and this stays the
#: ejector's own enthalpy carrier, read by nothing else.
#:
#: Source: V1 `main.py` EJ_T_SUCTION_C.
T_SUCTION_DES_C = 178.8

# ======================================================================================
# Pressures and densities
# ======================================================================================

#: 321P002 discharge header [bar a], the motive pressure. Re-exported from `unit_321`.
#:
#: It enters the geometry BACK-SOLVE only, where it sizes the nozzle. The running model never
#: uses it, because a positive-displacement pump fixes the motive MASS flow and the nozzle
#: area then fixes the jet velocity outright.
P_MOTIVE_DES_BARA = P_SYN_DOWN_BAR

#: 322E003 overflow into the suction-B line [bar a] — PI-329201.
#:
#: **Not** the scrubber's own published overflow pressure, which `unit_322e003` gives as
#: 140.7 bar a. The 0.7 bar between them is the static head and line loss
#: down the seal leg from the sump to the suction-B nozzle, and it is carried separately
#: because the ejector's entrainment ratio is a function of the pressure AT ITS NOZZLE.
#: Source: V1 `main.py` EJ_P_SUCTION_BARA. Once the engine wires the loop this becomes the
#: live line pressure, which is the same subtraction against a moving PT-329201.
P_SUCTION_DES_BARA = 140.0

#: Diffuser pressure recovery at design [bar a]. Source: PFD.
P_DISCHARGE_DES_BARA = 144.2

#: 322E003 overflow density [kg/m3]. Source: PFD stream 206 at 140.7 bar a and 165 C. The
#: synthesis liquid-phase density uses the same number — one value, one source.
RHO_SUCTION = 1133.0

#: Discharge effective density [kg/m3] at design. Composition-invariant in this model.
RHO_DISCHARGE = 877.9

# ======================================================================================
# The HV-322602 spindle
# ======================================================================================

#: HIC-322602 design opening [%].
OPEN_DES_PCT = 74.0

#: Nozzle free area at the design opening, as a per cent of full [-], 84.4.
#:
#: The 322F001 DDS states the nozzle free area directly: variable over 40-100 % on a LINEAR
#: instrument map ``a(theta) = 40 + 0.6 theta``. That is a primary source for exactly the
#: quantity the model needs, and it is used unchanged:
#:
#:     A_t(theta) = A_T_DES . (40 + 0.6 theta) / (40 + 0.6 . OPEN_DES_PCT)
#:
#: The direction it produces is the one V1's superseded law ASSERTED, and it is now derived:
#: closing the spindle RAISES entrainment, because a smaller area at constant motive mass
#: raises the jet momentum ``m_p^2/(rho A_t)`` and therefore the head the pump can develop.
#: The motive is fed by positive-displacement pumps, so the mass flow is set by pump speed
#: and not by the valve — which is why the law runs the opposite way to a throttle.
SPINDLE_A_FULL_PCT = 40.0 + 0.6 * OPEN_DES_PCT

#: Minimum effective spindle opening [%]. Below this the model holds the stroke: the nozzle
#: free-area map is stated by the DDS over 40-100 % of area, i.e. 0-100 % of travel, and the
#: closure is not evidence for anything outside it. Source: V1 `main.py`,
#: `clamp(hv_open_pct, 10.0, 100.0)`.
OPEN_MIN_PCT = 10.0

# ======================================================================================
# Geometry, back-solved from the licensor's design duty
# ======================================================================================
# The vendor calculation is a scan, so the two areas are derived from the design point
# through the same equations the model runs forward — the identical treatment every control
# valve in this engine gets, and for the identical reason: it keeps the design point exact
# and it invents nothing.

#: Nozzle and mixing-throat geometry, back-solved. `a_t_m2` is the nozzle exit area at the
#: 74 % design spindle opening and `a_m_m2` the constant mixing-throat area.
GEOMETRY = jet_pump.solve_geometry(
    MOTIVE_DES_KGH, SUCTION_DES_TOTAL_KGH, P_MOTIVE_DES_BARA, P_SUCTION_DES_BARA,
    P_DISCHARGE_DES_BARA, NH3_RHO, RHO_SUCTION, RHO_DISCHARGE)

#: Motive-nozzle exit area at the design spindle opening [m2] — a 16.72 mm bore.
A_T_DES_M2 = GEOMETRY["a_t_m2"]

#: Constant mixing-throat area [m2] — a 50.23 mm bore.
A_M_M2 = GEOMETRY["a_m_m2"]

# MONOTONICITY IS ASSERTED, NOT ASSUMED. The previous constant-area attempt was abandoned
# because its m_s^2 coefficient went net positive and the closure became bistable. The bound
# in `jet_pump.monotonicity_margin` is a sufficient condition for that coefficient to be
# non-positive at EVERY area ratio, i.e. at every spindle position, and at these densities it
# holds with a factor of 1.79. Asserting it at import means a future change to either density
# that would re-open the degeneracy fails here instead of shipping a step characteristic.
assert jet_pump.monotonicity_margin(RHO_SUCTION, RHO_DISCHARGE) > 1.0, \
    "322F001 closure is not monotonic at these densities"

#: The closure evaluated at the design duty — the denominator of the anchored forward call.
#: Its entrainment is the design suction to the last bit, which is what makes the design
#: point bit-exact rather than nearly so.
_REFERENCE = jet_pump.entrainment_kgh(
    MOTIVE_DES_KGH, P_SUCTION_DES_BARA, P_DISCHARGE_DES_BARA, A_T_DES_M2, A_M_M2,
    NH3_RHO, RHO_SUCTION, RHO_DISCHARGE)

#: Shutoff head at the design motive flow [bar], 5.106 — the rise the jet develops at zero
#: entrainment, and the ceiling on what it can lift.
SHUTOFF_DES_BAR = _REFERENCE["c0_bar"]

#: Motive fraction at which the machine can no longer make the design lift [-], 0.907.
#:
#: A DIAGNOSTIC, computed rather than asserted: the jet's shutoff head scales with the square
#: of the motive mass flow, so the stall point is ``sqrt(lift / C0_des)``. It is published
#: because a training scenario should be able to read it rather than discover it.
#:
#: It is also a FINDING. V1's superseded law put the stall knee at a motive fraction of
#: 0.20-0.35 and treated anything above that as healthy. The closure says this machine runs
#: within 10 % of its own shutoff head at the design point, so a 9 % motive loss stalls it.
#: The two statements are not close, and the second is the one that follows from the momentum
#: balance. See `handoff.md`.
STALL_PHI_MOTIVE = math.sqrt(
    (P_DISCHARGE_DES_BARA - P_SUCTION_DES_BARA) / SHUTOFF_DES_BAR)

# ======================================================================================
# Hydraulics and the discharge heat balance
# ======================================================================================

#: Throat-choke ceiling on the suction-head multiplier [-].
#:
#: A real jet ejector chokes: above a finite suction head the throat reaches its maximum mass
#: capacity and entrainment stops rising with head. Being above 1.0, it never engages at
#: design, where the scrubber sump sits at its normal level and the multiplier is a literal
#: 1.0 — so every design pin is untouched. 25 % of head over-capacity is the typical hydraulic
#: margin for an HP jet ejector.
#:
#: What it prevents: on a 322E003 flood the raw multiplier wants 2.0 (level 100 % against a
#: 50 % normal level), and without the ceiling the un-pumpable excess would be recirculated
#: into the discharge, through 322E002 and into the reactor loop, where the conversion
#: self-loop re-amplifies it. With the ceiling the excess backs up in the sump instead, which
#: is what a choked throat actually does. Source: V1 finding D-19.
HYDRAULIC_FRAC_MAX = 1.25

#: Mean specific heats [kJ/kg.K] of the motive ammonia, the entrained carbamate and the mixed
#: discharge. Source: V1 `main.py` EJ_CP_N / EJ_CP_C / EJ_CP_D.
#:
#: The discharge value is CALIBRATED — it is the one number in the heat balance that is
#: back-solved, and it is back-solved to hold the design TT-322012 exactly. The balance is
#: written cp-weighted on both sides for a reason recorded in V1: the literal mass-only
#: denominator ``(m_mot + m_suc)`` is dimensionally an enthalpy rather than a temperature,
#: and it breaks the design pin.
CP_MOTIVE = 4.74
CP_CARBAMATE = 3.10
CP_DISCHARGE = 3.50


__all__ = [
    "MOTIVE_DES_KGH", "MOTIVE_MASS_PCT", "MOTIVE_W",
    "P_SUCTION_DES_BARG", "MOTIVE_T_DES_C",
    "OVERFLOW_DES_KMOLH", "SUCTION_DES_KGH", "SUCTION_DES_TOTAL_KGH",
    "CARBAMATE_FRAC", "T_SUCTION_DES_C",
    "P_MOTIVE_DES_BARA", "P_SUCTION_DES_BARA", "P_DISCHARGE_DES_BARA",
    "RHO_SUCTION", "RHO_DISCHARGE",
    "OPEN_DES_PCT", "SPINDLE_A_FULL_PCT", "OPEN_MIN_PCT",
    "GEOMETRY", "A_T_DES_M2", "A_M_M2", "SHUTOFF_DES_BAR", "STALL_PHI_MOTIVE",
    "HYDRAULIC_FRAC_MAX",
    "CP_MOTIVE", "CP_CARBAMATE", "CP_DISCHARGE",
]
