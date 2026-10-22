"""Design constants for 322E002, the HP carbamate condenser.

What the equipment is
---------------------
A vertical falling-film shell-and-tube condenser, and the place where urea synthesis actually
begins. Tube side: the 322E001 stripper's top gas (TT-322013) and the 322F001 ejector's
carbamate discharge (TT-322012) enter the top channel together and flow co-current downward.
NH3 and CO2 condense into the falling film and react to ammonium carbamate, and a two-phase
product leaves for the reactor 322R001 (TT-322010). Shell side: boiler feed water from
322D001 A/B boils and raises the plant's own 4.4 bar a LP steam.

The carbamate reaction is strongly exothermic — about 160 kJ per mole of CO2 absorbed — and
that heat is not waste. It is the largest single LP-steam source on the plant, which is why
the condenser and the steam header are coupled tightly enough to have their own stability
problem; see the disturbance gate in the unit module.

Sources, in the resolution order of the agent directives §4
------------------------------------------------------------
* `References/Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md` — the design heat and
  mass balance, which fixes the split calibration below.
* `References/HPCC description.md`, Sections 5.2-5.3 — the statement that this unit is
  INTERFACIAL MASS-TRANSFER limited, which is what the film relaxation models.
* Open literature for the carbamate dissociation slope: Bennett (1953), Ramachandran (1998).
* V1 `backend/main.py`, the `HPCC_*` block, for the values V1 back-solved or calibrated.
"""

from __future__ import annotations

from ureasim.core.units_of_measure import R_GAS_FITTED_J
from ureasim.data.unit_320 import SYN_P_DES_BARA
from ureasim.data.unit_329 import P_LP_BARA
from ureasim.thermo.iapws import tsat_c

# ======================================================================================
# The calibrated split
# ======================================================================================

#: Design gas fraction of each tube-side feed component [-] — the calibration this whole
#: unit is anchored on. Source: the licensor design HMB.
#:
#: The design balance shows urea unchanged across 322E002, so at the calibration point the
#: unit is a pure component phase split: a fraction phi_i of each combined-feed component
#: leaves as gas and (1 - phi_i) as liquid, with the carbamate reaction implicit in the
#: numbers rather than modelled as an extent.
#:
#: Four of the nine are structurally non-distributing and stay OUT of the flash below: O2,
#: CH4 and H2 never condense at these conditions and are exactly 1.0; urea and biuret never
#: boil and are exactly 0.0. Only CO2, NH3, H2O and N2 distribute.
FRAC_GAS_DES = {
    "CO2": 0.2036, "NH3": 0.2977, "H2O": 0.0450,
    "N2": 0.982, "O2": 1.0, "CH4": 1.0, "H2": 1.0,
    "Urea": 0.0, "Biuret": 0.0,
}

# ======================================================================================
# The design state
# ======================================================================================

#: Two-phase outlet temperature at design [deg C] — TT-322010, gas and liquid together.
T_PROD_DES_C = 170.0

#: Synthesis-loop pressure at the condenser outlet at design [bar a]. Source: PFD.
P_DES_BARA = 144.2

#: Shell-side LP steam pressure [bar a] — 4.0 bar g.
STEAM_P_BARA = 5.01325

#: The licensor's own rounded shell saturation indicator [deg C], retained as provenance.
#: The balances use the thermodynamic value below, not this one.
STEAM_TSAT_PFD_C = 146.3

#: Shell saturation temperature [deg C], 151.94 — the thermodynamic state the duty and the
#: NTU quench are both written against. From the shared IAPWS-IF97 Region 4 boundary, so the
#: condenser, every other steam-heated shell and the 329 header network agree by construction.
STEAM_TSAT_C = tsat_c(STEAM_P_BARA)

# ======================================================================================
# The heat balance
# ======================================================================================

#: Carbamate formation exotherm [kJ per mol of CO2 absorbed]:
#: 2 NH3 + CO2 -> NH2COONH4. Source: open literature; the same figure is the dissociation
#: enthalpy the flash slope below is derived from.
DH_CARB_KJMOL = 160.0

#: Mean strip-gas specific heat for the sensible duty [kJ/kg.K]. The stripper carries the
#: same value for the same reason — one mean cp for the NH3 / CO2 / H2O overhead.
CP_GAS = 2.0

#: Latent heat of the 4.4 bar a LP steam this unit raises [kJ/kg].
LATENT_4BAR = 2120.0

# ======================================================================================
# The isothermal flash
# ======================================================================================
# The calibration above was measured at ONE point, 170 C and 144.2 bar a. Frozen, it makes
# the condenser thermodynamically INERT: raising the LP-steam pressure changes the shell duty
# and the outlet temperature but not one mole of condensate, and a synthesis-pressure
# excursion moves nothing at all. The flash binds a real isothermal (T, P) departure on top
# of the calibration without discarding it — see `units.synthesis.carbamate_condenser`.
#
# The physics: NH3 / CO2 "condensation" here is not physical condensation, it is the
# carbamate equilibrium
#
#     NH2COONH4 (l)  <->  2 NH3 (g) + CO2 (g),        Kp = p_NH3^2 . p_CO2
#
# whose dissociation enthalpy is about 160 kJ/mol — DH_CARB_KJMOL, already above. Because Kp
# is a THIRD-order product, the measured temperature coefficient of the dissociation PRESSURE
# is one third of the reaction enthalpy, about 53.5 kJ/mol. With y_NH3 ~ 2 y_CO2 the gas mole
# fraction of each partner scales as y_i ~ Kp(T)^(1/3)/P, so
#
#     K_i(T, P) = K_i,des . exp[(dH/R)(1/T_des - 1/T)] . (P_des/P)
#
# H2O is ordinary Raoult condensation on its own latent heat, same 1/P. N2 is a permanent gas
# held by Henry's law: no temperature slope, still 1/P.

#: Clausius-Clapeyron slope of each distributing K-value [J/mol].
FLASH_DH = {
    "CO2": DH_CARB_KJMOL * 1000.0 / 3.0,   # the carbamate cube-root slope, 53 333 J/mol
    "NH3": DH_CARB_KJMOL * 1000.0 / 3.0,
    "H2O": 36900.0,                        # 2049 kJ/kg x 18.015 g/mol, water latent at 170 C
    "N2": 0.0,                             # permanent gas: Henry's law, no temperature slope
}

#: Gas constant the flash slope is evaluated with [J/(mol.K)]. V1's rounded value, not CODATA
#: — see `core.units_of_measure.R_GAS_FITTED_J` for why the two are kept apart.
FLASH_R_GAS_J = R_GAS_FITTED_J

#: Bisection sweeps on the Rachford-Rice residual.
#:
#: Bisection and not Newton, and a fixed count rather than a tolerance. The residual is
#: strictly decreasing on [0, 1], so a fixed 60-sweep bracket is exact to 2^-60 with BOUNDED
#: cost and no possible convergence failure. An OTS tick must never miss its deadline, which
#: is the same argument that keeps the flowsheet sequential-modular.
FLASH_ITERS = 60

#: Reference temperature of the flash and bubble-point slopes [K], 443.15 — the design
#: product temperature.
FLASH_T0_K = T_PROD_DES_C + 273.15

# ======================================================================================
# The melt bubble pressure — PI-322E002 telemetry
# ======================================================================================

#: Effective NH3-dominated vaporisation enthalpy of the carbamate melt [J/mol], the
#: Clausius-Clapeyron slope of its bubble pressure. The stripper's free-NH3 desorption
#: enthalpy is the same number for the same reason.
BUB_DHVAP_JMOL = 23_000.0

#: Bubble-pressure sensitivity to the melt N/C [1/(N/C)] — free-ammonia volatility. CALIBRATED.
BUB_KN = 0.18

#: Bubble-pressure sensitivity to the melt H/C [1/(H/C)] — water dilution. CALIBRATED, and
#: negative: adding water to the melt lowers its bubble pressure.
BUB_KW = -0.25

#: The N/C below which the melt's bubble pressure rises toward its azeotrope [-], 3.0. Above it
#: the calibrated K_N line holds, so the design and every high-N/C pin keep V1's law; below it
#: the N/C factor follows the Extended UNIQUAC model's own rise (`thermo.vle.bubble_p_bara`),
#: which climbs from 44.4 bar a at 3.0 to 53.8 at 2.8 and 82.4 at 2.6 on the design melt at
#: 170 C, where the linear K_N line falls. Source: the process engineer's decision of
#: 2026-10-22 on handoff B-106 (session 64).
BUB_AZEOTROPE_NC = 3.0

#: Clamp band on the melt N/C and H/C, as a multiple of their design references [-].
#:
#: These ratios are NH3/CO2 and H2O/CO2, so as a CO2-feed cut drives CO2 toward zero they
#: diverge. Unclamped, the bubble pressure impulses to about 330 bar a for a single tick on
#: the way through — an N/C-to-infinity artefact, not a synthesis pressure. Clamping both to
#: half and twice their design values keeps the published indication inside a bounded
#: physical range; the design melt sits well inside the band, so the design point is untouched.
BUB_RATIO_LO_FRAC = 0.5
BUB_RATIO_HI_FRAC = 2.0

# ======================================================================================
# The liquid inventory
# ======================================================================================

#: LT-322E002 design normal liquid level [% of sump span].
LEVEL_NLL_PCT = 50.0

#: Carbamate-condenser liquid holdup time [min].
#:
#: It does double duty, and deliberately so: it is the level fill constant AND the relaxation
#: time of the film composition. Both are the same physical quantity — how long liquid stays
#: in this vessel — so they are one number rather than two that could drift apart.
TAU_FILL_MIN = 6.0

# ======================================================================================
# The tube leak (handoff B-82, decided 2026-10-09)
# ======================================================================================

#: The differential the instructor's leak rate is set at [bar]: the tube side at the loop's
#: design pressure (PT-329201, 140.7 bar a, the PFD's) against the shell at 322D001A/B's design
#: steam space (the LP header's 4.0 bar g, 5.01 bar a, handoff B-69). Written as a subtraction of
#: the two design pressures (A-13).
LEAK_DP_DES_BAR = SYN_P_DES_BARA - P_LP_BARA

#: What leaves the leak in the boiling shell as vapour, with the LP steam: the volatiles and the
#: inerts. Water, urea and biuret join 322D001A/B's water. At the shell's 147 C and 5 bar a the
#: boiling water strips ammonia and CO2 and decomposes carbamate — the stripping principle of the
#: process itself — so the split is complete, an assumption no plant document measures.
LEAK_VOLATILE = ("NH3", "CO2", "N2", "O2", "H2", "CH4")

#: The tube leak's rate at the design differential when the instructor triggers it with no rate
#: [t/h]. Decided 2026-10-09 (handoff B-90): a bare trigger leaks 10 t/h, so the panel's button
#: works at once.
LEAK_DEFAULT_TH = 10.0


__all__ = [
    "FRAC_GAS_DES",
    "T_PROD_DES_C", "P_DES_BARA",
    "STEAM_P_BARA", "STEAM_TSAT_PFD_C", "STEAM_TSAT_C",
    "DH_CARB_KJMOL", "CP_GAS", "LATENT_4BAR",
    "FLASH_DH", "FLASH_R_GAS_J", "FLASH_ITERS", "FLASH_T0_K",
    "BUB_DHVAP_JMOL", "BUB_KN", "BUB_KW", "BUB_AZEOTROPE_NC",
    "BUB_RATIO_LO_FRAC", "BUB_RATIO_HI_FRAC",
    "LEVEL_NLL_PCT", "TAU_FILL_MIN", "LEAK_DP_DES_BAR", "LEAK_VOLATILE",
    "LEAK_DEFAULT_TH",
]
