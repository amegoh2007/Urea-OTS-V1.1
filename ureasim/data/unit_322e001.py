"""322E001 — HP stripper design constants, geometry and reaction anchors.

What this covers
----------------
The falling-film CO2 stripper: its design feed and split, the licensor tube geometry, the
hydrodynamic flooding limit, the per-species enthalpy constants the MP-steam header pays for,
and the bottom sump with LIC-322501 and LV-322501.

Source discipline
-----------------
Five provenances appear, and the difference between them is the whole point of this module:

* **PFD / design basis** — the stream-207 reactor overflow, the design split fractions, the
  design duty, the product temperatures and the design bottoms flow. These are the anchor.
* **licensor datasheet** — the tube bundle. Uhde DDS UD-AU-322-DZ-0003-003 rev 00, page 3.
  The DDS is self-consistent: its tabulated surface area confirms its own tube count to
  0.018 %, which is why the geometry can be trusted to carry a hydraulic limit.
* **open literature** — the flooding limit, the carbamate and hydrolysis enthalpies, and the
  biuret activation energy. Each is cited at its constant.
* **field calibration** — LV-322501's opening at design, from a DCS startup trend, which
  disagrees with the datasheet stroke by a factor of 1.8 for a stated reason.
* **derived** — every quantity written as an expression below. Nothing derived is also
  entered, so the two can never disagree.
"""

from __future__ import annotations

import math

from ureasim.core.stream import MW_COMP
from ureasim.core.units_of_measure import R_GAS_FITTED_J
from ureasim.data.unit_320 import (
    CO2_DES_KMOLH,
    CO2_FEED_MOLFRAC,
    SYN_P_DES_BARA,
)
from ureasim.data.unit_322e003 import COND_CHOKE_MIN
from ureasim.data.unit_322r001 import OVERFLOW_DES_KMOLH, REACTOR_T_DES_C
from ureasim.thermo.iapws import tsat_c
from ureasim.thermo.kinetics import (
    BIURET_FORMATION_EA_JMOL,
    CARBAMATE_DH_JMOL,
    DEHYDRATION_DH_JMOL,
)

# ======================================================================================
# The two feeds
# ======================================================================================

#: 322R001 overflow, PFD stream 207 [kmol/h] — the top liquid feed, arriving through
#: HV-322605 and measured by TT-322014.
#:
#: One stream, one home: it is the reactor's product before it is the stripper's feed, so the
#: figures live in `data.unit_322r001` and are read here. The local name is kept because it is
#: what this unit calls the stream. Source: PFD stream 207.
FEED_207_KMOLH = OVERFLOW_DES_KMOLH

#: TT-322014 design overflow temperature [deg C]. The same 183 C the reactor runs at, because
#: the overflow leaves the reactor at bulk temperature. Source: PFD.
FEED_207_T_DES_C = REACTOR_T_DES_C

#: Design stripper feed [kmol/h] — the reactor overflow PLUS the CO2 sweep gas entering at the
#: tube bottom. Derived, because the sweep is the same CO2 stream unit 320 delivers and must
#: not be re-entered here with its own rounding.
FEED_DES_KMOLH = {k: FEED_207_KMOLH.get(k, 0.0)
                  + CO2_FEED_MOLFRAC.get(k, 0.0) * CO2_DES_KMOLH for k in MW_COMP}

#: Design stripper-feed N/C [-], about 1.9045. NOTE this is NOT the reactor-feed N/C: the
#: stripper feed includes the CO2 sweep, so its carbon basis is larger. Published as a
#: diagnostic; the efficiency penalties anchor on the REACTOR's ratios, not these.
FEED_NC_DES = FEED_DES_KMOLH["NH3"] / FEED_DES_KMOLH["CO2"]

#: Design stripper-feed H/C [-], about 1.0610. Same basis note as above.
FEED_HC_DES = FEED_DES_KMOLH["H2O"] / FEED_DES_KMOLH["CO2"]

#: Design urea in the stripper feed [kmol/h], 1302.6 — the biuret rate law's concentration
#: anchor.
FEED_UREA_DES_KMOLH = FEED_DES_KMOLH["Urea"]

#: Design stripper feed mass [kg/h], about 280 797. Derived from the vector above against the
#: atom-consistent molar masses, never entered.
FEED_DES_KGH = sum(FEED_DES_KMOLH[k] * MW_COMP[k] for k in MW_COMP)

# ======================================================================================
# The design split and the design reaction extents
# ======================================================================================

#: Fraction of each component leaving overhead at design [-], calibrated to the shared design
#: heat-and-mass balance. Source: PFD streams, V1 `main.py` STRIP_FRAC_DES.
#:
#: The non-volatiles are structurally 0 — urea and biuret do not leave a stripper overhead —
#: and the inerts are near 1. Those two are statements about the components, not calibration,
#: which is why the K-ratio transform leaves them alone.
FRAC_TOP_DES = {"NH3": 0.8546, "CO2": 0.8606, "H2O": 0.1313, "N2": 0.9987, "O2": 0.975,
                "Urea": 0.0, "Biuret": 0.0, "CH4": 0.999, "H2": 0.999}

#: Design urea-hydrolysis extent [kmol/h]. Urea + H2O -> 2 NH3 + CO2.
#: Source: PFD component balance across the unit, V1 `main.py` STRIP_XI_HYD_DES.
#:
#: **This constant is almost certainly not urea hydrolysis alone**, and that is stated rather
#: than hidden. The Inoue-Otsuka rate law evaluated at this stripper's own design state cannot
#: reach it by a factor of five even with the entire vessel flooded with liquid, and 88.1
#: kmol/h is 6.8 % of the urea feed destroyed in 97 seconds where a real CO2 stripper loses
#: well under 1 %. It lumps carbamate decomposition, which is what the stripper is for. So the
#: PFD extent stays the ANCHOR and the rate law supplies only the DEPARTURE — see the stripper
#: module. Predicting it outright would be fitting a rate constant to a different reaction.
XI_HYDROLYSIS_DES = 88.1

#: Design biuret-formation extent [kmol/h]. 2 Urea -> Biuret + NH3.
#: Source: PFD component balance, V1 `main.py` STRIP_XI_BIU_DES.
XI_BIURET_DES = 0.667

# ======================================================================================
# The shell steam side and the duty
# ======================================================================================

#: Design 329D005 MP steam to the shell [kg/h]. Source: PFD, V1 `main.py`.
STEAM_DES_KGH = 75300.0

#: Design MP steam supply pressure [bar a]. Source: PFD, V1 `main.py`.
STEAM_P_DES_BARA = 19.7

#: Saturated-steam shell temperature at the design supply pressure [deg C], 211.6. DERIVED
#: from the shared IAPWS-IF97 saturation line, so the stripper and the 329 steam network
#: cannot hold two different opinions about what 19.7 bar a steam is.
STEAM_T_DES_C = tsat_c(STEAM_P_DES_BARA)

#: Design heat duty [kW]. Source: PFD / licensor datasheet, V1 `main.py`.
DUTY_DES_KW = 39400.0

#: Design tube-side pressure [bar a] — the synthesis loop plus the stripper's own line drop.
#: Source: PFD, V1 `main.py` STRIP_P_DES_BARA.
P_DES_BARA = 144.0

#: Design tube-side pressure drop from the stripper to the loop reference PT-329201 [bar],
#: 3.3. Written as a SUBTRACTION of the two design pressures, per handoff A-13.
DP_TO_LOOP_DES_BAR = P_DES_BARA - SYN_P_DES_BARA

# ======================================================================================
# Design product temperatures
# ======================================================================================

#: TT-322013 design top-gas temperature to 322E002 [deg C]. Source: PFD.
T_TOPGAS_DES_C = 187.0

#: TT-322004 design bottom-solution temperature, before LV-322501 [deg C]. Source: PFD.
T_BOTTOM_DES_C = 172.0

#: The temperature the bottoms asymptote UP to when the stripper floods [deg C], 183.
#:
#: Not a new constant: it is the reactor overflow temperature. A flooded stripper is
#: steam-limited, carbamate decomposition stalls, its endotherm fades, and the already-hot
#: reactor liquor falls through the tubes untouched — so the bottom must approach the liquor
#: it was fed, and can never exceed it by this route.
T_FLOOD_ANCHOR_C = REACTOR_T_DES_C

#: Head-room between the flooded ceiling and the design bottoms [deg C], 11. The span every
#: saturating bottom-temperature term is scaled on, so the two branches share one ceiling.
FLOOD_GAP_DES_C = T_FLOOD_ANCHOR_C - T_BOTTOM_DES_C

#: TT-323001 design temperature downstream of the LV-322501 flash [deg C]. Source: PFD.
T_DOWNSTREAM_DES_C = 119.0

# ======================================================================================
# The shell's duty bound (handoff B-102, decided 2026-10-21)
# ======================================================================================

#: How far the duty the split asks for may stand above the shell's capacity before the
#: capacity binds [-], 5e-4 — and the margin it then binds at, Q_max . (1 + band), so the duty
#: never steps at the band's edge. Not a property of the exchanger: the process engineer's
#: tolerance, the smallest round band above the unperturbed design seed's own drift, which
#: was measured at 1.68e-4 of the design duty over an hour (handoff B-94, session 63), so the
#: seed runs V1's split to the bit. About 20 kW on the 39 400 kW shell.
#: Source: the process engineer's decision of 2026-10-21 on handoff B-102 (session 63).
SHELL_DUTY_BAND = 5.0e-4

# ======================================================================================
# The liquid-side energy balance
# ======================================================================================

#: Mean specific heat of the bottom solution — a urea/carbamate/NH3 melt at about 175 C
#: [kJ/(kg K)]. Source: V1 `main.py` STRIP_CP_BOTTOM.
CP_BOTTOM = 2.93

#: Mean specific heat of the overhead gas [kJ/(kg K)]. The same value the 322E002 balance
#: uses, for the same reason: one mean cp for one gas.
#: Source: V1 `main.py` STRIP_CP_GAS (== HPCC_CP_GAS).
CP_GAS = 2.0

#: Design specific heating the steam delivers to the descending liquid [deg C], about 172.4.
#:
#: DERIVED: duty over feed mass over cp. This is the quantity a feed spike dilutes — more
#: reactor overflow at constant steam duty means less heating per kilogram, so the bottom
#: solution leaves COLDER. The carbamate endotherm is itself proportional to feed and cancels
#: its own per-mass term, which is why this steam-dilution swing is the NET response.
DT_STEAM_DES_C = DUTY_DES_KW * 3600.0 / (FEED_DES_KGH * CP_BOTTOM)

# ======================================================================================
# Tube bundle and the hydrodynamic flooding limit
# ======================================================================================
# Every temperature term above is a THERMAL response: it asks whether the shell steam can
# keep up with the liquid. The block below asks a different and independent question — can
# the tube physically carry the film at all? Once the rising gas core shears the descending
# film off the wall, the film thickens, liquid is dragged upward, residence time collapses
# and stripping stops, however much steam is available.

#: Number of tubes [-]. Source: licensor DDS line 34.
N_TUBES = 2600

#: Tube outside diameter [m], 31 mm. Source: DDS line 36.
TUBE_OD_M = 0.031

#: Tube wall thickness [m], 3.0 mm. Source: DDS line 36.
TUBE_WALL_M = 0.003

#: Tube inside diameter [m], 0.025 — which is 0.984 inch, so the one-inch flooding figure
#: below applies WITHOUT scaling. Derived from the two DDS dimensions.
TUBE_ID_M = TUBE_OD_M - 2.0 * TUBE_WALL_M

#: Effective tube length [m]. Source: DDS line 35, "6000 mm eff."
TUBE_L_EFF_M = 6.000

#: Exchange surface per exchanger [m2]. Source: DDS line 25.
#:
#: Carried as the datasheet's own number and used as the CONSISTENCY CHECK on the geometry:
#: N.pi.d_o.L = 2600 x pi x 0.031 x 6.000 = 1519.27 against the tabulated 1519.00, +0.018 %.
#: That agreement is why the tube count and length can be trusted to carry a hydraulic limit.
SURFACE_DES_M2 = 1519.00

#: Tube-side gas density at operating conditions [kg/m3]. Source: DDS line 14.
RHO_GAS_DES = 10.28

#: Tube-side liquid density in [kg/m3]. Source: DDS line 13.
RHO_LIQ_IN_DES = 989.88

#: Solution per tube at the flooding limit [kg/h]. Source: Brouwer, "How to Solve Stripper
#: Efficiency Issues", UreaKnowHow 2025, citing IFS Proceeding 166 — at 183 C reactor outlet
#: and 140 bar the flooding limit in a 1-inch tube is 145 kg of solution per hour.
#:
#: Three independent facts make the citation applicable here without adjustment: the DDS tube
#: ID is 0.984 inch, so the one-inch figure needs no scaling; the DDS effective length is
#: 6.000 m, which the same paper states is what gives a Stamicarbon CO2 stripper its 80 %
#: design efficiency; and the quoted reference condition is this stripper's own feed
#: temperature at a pressure within 3 % of its tube side.
FLOOD_KGH_PER_TUBE = 145.0

#: Industry operating cap as a fraction of the limit [-]. Source: the same paper, "in practice
#: an upper limit of 70 % of this value is applied". Carried as provenance for the design
#: margin; the model uses the limit itself, not the practice cap.
FLOOD_PRACTICE_FRAC = 0.70

#: Flooding fraction at design [-], 0.7448. A COMPUTED RESULT, not a tuned constant:
#: 280797 / 2600 / 145, i.e. 108.0 kg/h per tube against a 145 kg/h limit.
#:
#: Two consequences, both load-bearing. The plant-level limit is 377 000 kg/h, so flooding
#: starts at 134 % of design load — the same order as the paper's "110 % when new, 120 % at
#: end of life". And because 0.7448 < 1.0 the flooding term is IDENTICALLY INACTIVE at the
#: design seed: it is a one-sided constraint that does not bind, so it cannot move a single
#: bit of the pinned design state. That is the whole bit-exactness argument for the flooding
#: block — not an anchored ratio, just a constraint the plant genuinely operates below.
FLOOD_DES_FRAC = FEED_DES_KGH / N_TUBES / FLOOD_KGH_PER_TUBE

#: Bottom-temperature ramp per unit of excess over the flooding limit [-], 3.83.
#:
#: FIXED by the source's own observation rather than tuned. Brouwer: "a sudden temperature
#: increase of the stripper bottom temperature, let's say 3-4 C in 15 minutes, is a clear
#: indication for reaching the flooding limit". Requiring 11.0 x (1 - exp(-K x 0.10)) = 3.5 C
#: at 10 % over the limit gives K = 3.83.
FLOOD_T_RAMP_K = 3.83

#: Floor on the hydraulic efficiency knockdown [-]. The hydraulic term alone can never zero
#: the stripper: the thermal collapse is carried separately by g_T, and this term is
#: incremental to it.
FLOOD_ETA_FLOOR = 0.50

# ======================================================================================
# The per-species enthalpy balance — what the MP-steam header actually pays for
# ======================================================================================
# What this replaces: a duty strictly proportional to feed MASS. That said a stripper fed the
# same tonnage of pure water and of carbamate-rich reactor liquor needs the same steam.
# Composition did not enter at all, so the single largest heat sink in the unit was invisible
# to the steam header.
#
# Source for the two reaction enthalpies: Frejacques, quoted in Brouwer, "Thermodynamics of
# the Urea Process", UreaKnowHow Process Paper June 2009, p.12, which gives BOTH reactions at
# PROCESS conditions rather than at the usual 25 C standard state:
#
#     CO2(g) + 2 NH3(g) -> NH2COONH4(l)        dH = -117 kJ/mol at 110 atm and 160 C
#     NH2COONH4(l) -> NH2CONH2(l) + H2O(l)     dH = +15.5 kJ/mol at 160-180 C
#
# Those conditions are close to this stripper's own (144 bar, 172-183 C), which is why the
# process-condition 117 is used and not the 159-160 kJ/mol quoted for SOLID carbamate at
# 1 atm and 25 C. The stripper runs reaction 1 BACKWARDS, so +117 kJ per mol of CO2 released
# from the liquid; urea hydrolysis runs reaction 2 backwards, so -15.5 kJ/mol.

#: Carbamate dissociation [J/mol CO2 liberated], endothermic here. The dominant sink, about
#: 58 % of the design duty. This is 322E002's formation enthalpy run backwards, so the value
#: comes from `thermo.kinetics.CARBAMATE_DH_JMOL` with the sign reversed.
DH_CARBAMATE_JMOL = -CARBAMATE_DH_JMOL

#: Urea hydrolysis, the LIQUID step only [J/mol urea]. Negative — it gives a little heat back.
#: The carbamate this step produces is decomposed by the term above, so counting both is a
#: sum and not a double count. It is 322R001's dehydration step run backwards, so the value
#: comes from `thermo.kinetics.DEHYDRATION_DH_JMOL` with the sign reversed.
DH_HYDROLYSIS_JMOL = -DEHYDRATION_DH_JMOL

#: Desorption of free NH3 out of the melt [J/mol].
#:
#: NH3 is SUPERCRITICAL at stripper temperature (Tc = 132.4 C), so there is no latent heat to
#: look up; what the duty pays is the desorption enthalpy. This is not a new number — it is
#: the value the loop already uses at the other end of the same circuit, the NH3-dominated
#: vaporisation enthalpy fitted to the synthesis bubble point. Restated rather than aliased
#: because the two units are ported at different times; a test asserts they stay equal.
DH_NH3_DESORB_JMOL = 23_000.0

#: Water vaporised overhead [J/mol], 36 900 == 2049 kJ/kg at about 170 C (steam tables). The
#: same value the 322E002 flash balance uses.
DH_H2O_VAP_JMOL = 36_900.0

# Validation of the constant set: summed over the design streams, with nothing fitted and no
# free parameter, these five terms give 37 831 kW against the licensor's 39 400 kW — 96.0 %.
# The 4 % residue is shell and ambient loss, biuret (whose enthalpy is not published and
# which is 0.667 kmol/h against 88.1 for hydrolysis), and the mean-cp approximation. That
# agreement is the corroboration that this is the right constant set.
#
# How it is used: the licensor duty stays the anchor and only the RATIO of the live balance to
# the design balance is applied, so the 4 % offset CANCELS and never reaches the steam header.

# ======================================================================================
# The CO2 sweep endotherm and the efficiency penalties
# ======================================================================================

#: Maximum forced decomposition/evaporation endotherm as G/L -> infinity [deg C].
#: Source: V1 `main.py` STRIP_STRIPCOOL_MAX.
#:
#: The bottom CO2 sweep is held by the compressor while the reactor liquid feed varies. When
#: the feed collapses at constant CO2 the gas/liquid ratio spikes, forcing carbamate
#: decomposition and NH3/CO2 flash — a strong endotherm that OVERPOWERS the steam heat and
#: pulls the bottom COLDER. It saturates, so there is no pole at zero feed.
STRIPCOOL_MAX_C = 72.0

#: Cooling ramp per unit of excess G/L ratio [-]. Source: V1 `main.py` STRIP_STRIPCOOL_KGL.
STRIPCOOL_RAMP_K = 1.80

#: Attenuation with which the bottom's feed-load thermal swing reaches the overhead [-].
#: The load swing is a liquid/reboiler effect and the top gas feels it only weakly; the G/L
#: strip-cool endotherm, by contrast, couples to the overhead at FULL weight, because the
#: rising vapour is the first thing to carry the sweep flash's latent load.
T_TOP_LOAD_K = 0.5

#: Efficiency penalty per unit of fractional bottom-temperature deficit [-]. A feed-load
#: cooling excursion chokes the strip. Source: V1 `main.py` STRIP_ETA_KT.
ETA_KT = 0.15

#: Efficiency penalty per unit of reactor-feed N/C above design [-]. Excess NH3 chokes the
#: thermal strip: it has to be desorbed before anything else can be. Source: V1 STRIP_ETA_KN.
ETA_KN = 1.50

#: Efficiency penalty per unit of reactor-feed H/C above design [-]. Dilution chokes it the
#: same way. Source: V1 `main.py` STRIP_ETA_KW.
ETA_KW = 1.50

#: Floor on the two composition penalties [-]. Source: V1 `main.py` STRIP_ETA_FLOOR.
ETA_FLOOR = 0.50

#: Overhead NH3/CO2 breakthrough gain per unit of composition choke [-].
#:
#: The N/C and H/C choke does NOT cut the thermal split. A solution that is hard to strip
#: thermally pushes its volatiles overhead as SLIP instead, raising the vapour load back to
#: the carbamate condenser. Source: V1 `main.py` STRIP_SLIP_GAIN.
SLIP_GAIN = 4.0

#: CO2 sweep-gas dilution term floor and ceiling [-], and its intercept. The split fraction
#: responds to how much sweep gas there is per unit of liquid; at half the design CO2 rate the
#: term is 0.75, not 0.5, because the thermal strip does not stop when the sweep does.
#: Source: V1 `main.py`, the `eta_co2` expression.
ETA_CO2_INTERCEPT = 0.5
ETA_CO2_SLOPE = 0.5
ETA_CO2_LO = 0.4
ETA_CO2_HI = 1.05

#: Ceiling on the reported strip efficiency and on the thermal steam term [-].
ETA_T_CEILING = 1.15

#: Ceiling on the combined split modulation before the composition terms are applied [-].
MOD_CEILING = 1.12

#: Ceiling on the split fraction of any single species [-]. A column never strips 100 % of
#: anything, and a fraction of exactly 1 would make the bottoms composition undefined.
FRAC_TOP_MAX = 0.999

# ======================================================================================
# Biuret formation — 2 Urea -> Biuret + NH3
# ======================================================================================

#: Biuret-formation activation energy [J/mol]. Source: V1 `main.py` STRIP_BIU_EA, which V1
#: `reactor.py` then repeats for the reactor column; one reaction, one activation energy, so
#: the value comes from `thermo.kinetics.BIURET_FORMATION_EA_JMOL`. The name is kept because
#: it is this module's own rate law that reads it.
BIURET_EA_JMOL = BIURET_FORMATION_EA_JMOL

#: Gas constant used by the biuret Arrhenius term [J/(mol K)].
#:
#: V1 carries 8.314 here, not the CODATA 8.314462618 that `core.units_of_measure.R_GAS_J`
#: holds. The difference is 5.6e-5 relative, which reaches the biuret extent through
#: exp(Ea/R . dT) and would move a published number. Carried as V1's own so the port is exact.
#: The name is kept because it is what this rate law's coefficient was fitted with; the value
#: comes from `core.units_of_measure.R_GAS_FITTED_J`, which is its one home.
BIURET_R_GAS_J = R_GAS_FITTED_J

#: Arrhenius reference temperature for biuret [K], 445.15 — the design bottom temperature.
BIURET_T_DES_K = T_BOTTOM_DES_C + 273.15

# ======================================================================================
# Holdup volumes — what the second-order rate laws integrate over
# ======================================================================================

#: Tube-bundle liquid volume [m3], 7.658. Derived from the DDS geometry above.
V_TUBES_M3 = N_TUBES * math.pi * 0.25 * TUBE_ID_M ** 2 * TUBE_L_EFF_M

#: Bottom-head cross-section [m2], pi/4 x 2.43^2. Source: datasheet, bottom head ID 2430 mm.
SUMP_AREA_M2 = 4.638

#: Liquid band spanned by LT-322501, 0 to 100 % [m]. Source: instrument datasheet.
LEVEL_SPAN_M = 1.5

#: Sump volume between the two transmitter limits [m3].
V_SUMP_M3 = SUMP_AREA_M2 * LEVEL_SPAN_M

#: LIC-322501 design level set point [%]. Source: PFD / DCS.
LEVEL_SP_DES_PCT = 50.0

#: Design liquid holdup the rate laws see [m3] — the whole bundle plus the sump at its design
#: level. The live value tracks the LIVE level, so holdup is a real state and not a constant.
V_LIQ_DES_M3 = V_TUBES_M3 + V_SUMP_M3 * (LEVEL_SP_DES_PCT / 100.0)

#: Design liquid volumetric throughput [m3/h], about 283.7. Derived from the design feed mass
#: and the DDS inlet liquid density.
VDOT_DES_M3H = FEED_DES_KGH / RHO_LIQ_IN_DES

#: Temperature at which the hydrolysis rate group is anchored [deg C] — the design bottoms.
HYDROLYSIS_T_DES_C = T_BOTTOM_DES_C

# ======================================================================================
# The bottom sump, LIC-322501 and LV-322501
# ======================================================================================

#: Design bottom-solution flow [kg/h]. Source: PFD, V1 `main.py` STRIP_BOT_DES_KGH.
BOTTOMS_DES_KGH = 130482.0

#: Bottom-solution density at the LV inlet, 172 C [kg/m3]. Source: PFD.
RHO_BOTTOM = 1134.64

#: Design bottoms transit from the tube exit to the LT-322501 sump [s]. The constant the
#: superseded flat FIFO carried, kept as the DESIGN transit exactly as the two feed lines are.
BOTTOMS_TD_DES_S = 60.0

#: Bottoms line volume [m3], 1.917. Back-solved from the design transit at the design flow,
#: so the live dead time is rho.V/m_dot and a stripper running at half rate takes twice as
#: long to deliver its bottoms. Same constraint argument as the CO2 and NH3 feed lines.
BOTTOMS_LINE_M3 = (BOTTOMS_DES_KGH / 3600.0 * BOTTOMS_TD_DES_S) / RHO_BOTTOM

#: The liquor the tube bundle holds standing full [kg], 8 689: the bundle's liquid volume at the
#: bottoms' density. The ceiling on what a full LT-322501 sump holds back in the tubes above it;
#: past it 322R001 keeps the excess (decided 2026-10-22, handoff B-104).
TUBES_FULL_KG = V_TUBES_M3 * RHO_BOTTOM

#: What a fully submerged bundle still transfers, as a fraction of its shell's capacity [-],
#: 0.30: 322E003's flooded-surface floor (`unit_322e003.COND_CHOKE_MIN`, V1's
#: SCRUB_COND_CHOKE_MIN), the same law on the same kind of surface. Source: the process
#: engineer's decision of 2026-10-22 on handoff B-104.
SUBMERGED_DUTY_FLOOR = COND_CHOKE_MIN

#: LIC-322501's tuning [% output per % level, s]. DIRECT acting on a fail-closed, air-to-open
#: valve, which is correct negative feedback: level up, output up, valve opens, drain up, level
#: down. Source: the plant DCS's tuning table, `References/Master_PID_Tuning_Constants.md`, read
#: again from the faceplate photograph (322 faceplates, 10 July 2026): gain 0.20, TI 280 s, TD
#: 1.0 s, TF 1.0 s (the derivative's filter), DZ 1.0 % (handoff B-28, not modelled). The level is
#: per cent of LT-322501's span, so the gain is the table's as it stands (decision 10's class).
#: Decided 2026-10-08; V1 runs 2.5 and 90 s with no derivative (`main.py` LIC_322501_KC / _TI).
LIC_322501_KC = 0.20
LIC_322501_TI = 280.0
LIC_322501_TD_S = 1.0
LIC_322501_TF_S = 1.0

#: LV-322501 flow coefficient at full open [m3/h]. Datasheet reference value, carried as
#: provenance. DN-90 angle body, parabolic plug single seat, linear characteristic,
#: fail-closed, air-to-open. Source: valve datasheet.
LV_322501_KVS = 36.0

#: LV-322501 opening at the design bottoms flow [%] — FIELD CALIBRATED, and deliberately not
#: the datasheet value. Source: DCS 28-06-2025 startup anchors.
#:
#: At 97 % urea load the valve held 45.4 % and was stable between 42 and 45.4 % over three
#: hours. Corrected to design pressure drop (x 0.9853) and to design load (/0.97) that is
#: 46.1 %, cross-checking at 46.4 % and 44.2 % on two other hours. The datasheet predicts an
#: 82 % stroke, over-stating the required travel by 1.8x for this installed flashing service,
#: where the textbook Kv method over-predicts by about 3x. Field reality governs.
#:
#: Pin-safe: the constant enters only as the boot seed and as the ratio normaliser
#: (op / OPEN_DES), so the design steady state is bit-identical either way.
LV_322501_OPEN_DES_PCT = 46.1

#: LV-322501 flashes (decided 2026-09-30, handoff B-46). Uhde's CONVAL sizing of the valve,
#: UD-MR-G00-DZ-0042-032 (21.06.2005; the vendor archive, scanned, read from the page images):
#: urea solution at 173 C let down from 143.7 to 4.2 bar a, "Flashing!" on every operating point;
#: its boiling pressure pv1 99.0 bar a; at the mean flow, 130 010 kg/h, a critical differential of
#: 56.8 bar, FL^2 0.845 and a 43.86 % stroke. Kvs 36, linear, flow to open, DN 90 angle body.
LV_322501_FL = math.sqrt(0.845)
LV_322501_PV_CONVAL_BARA = 99.0
LV_322501_T_CONVAL_C = 173.0

#: Pressure immediately downstream of LV-322501 [bar a]. Source: PFD.
P_DOWNSTREAM_BARA = 4.2

#: Design pressure drop across LV-322501 [bar], 139.8: the shell less the line downstream, written
#: as the subtraction of the two design pressures (handoff A-13). Datasheet operating point.
LV_322501_DP_DES_BAR = P_DES_BARA - P_DOWNSTREAM_BARA

#: LP-loop downstream reference used for the live drain head [bar a]. The drain is a pressure
#: letdown driven by the LIVE synthesis pressure, so as the loop depressurises on a black
#: start the head collapses and the drain goes to zero — no spurious letdown from an empty
#: vessel. Source: V1 `main.py` LV322501_P_DOWN_BARA.
LV_322501_P_DOWN_BARA = 4.0

#: Design sump heat loss between the falling-film tube exit and the LV-322501 drain [deg C].
#: Source: V1 `main.py` STRIP_SUMP_DT_LOSS_DES_C.
SUMP_DT_LOSS_DES_C = 4.0

#: Urea-melt crystallisation floor [deg C], and the sink temperature the sump heat loss runs
#: to. A throttled sump with a long residence time asymptotes here, which is the physical
#: reason a stripper bottom can plug. Source: V1 `main.py` STRIP_BOT_T_CRYST_C.
T_CRYSTALLISATION_C = 132.7

#: Design sump heat-loss NTU [-], about 0.1018, i.e. UA/(m_des.cp). Derived from the design
#: loss and the temperature difference it runs against, so the closed-form sump outlet
#: temperature returns the design bottoms exactly at the design drain rate.
SUMP_NTU_DES = SUMP_DT_LOSS_DES_C / (T_BOTTOM_DES_C - T_CRYSTALLISATION_C)

#: Width of the mushy zone above the crystallisation solidus [deg C]. Flow ramps linearly
#: from fully molten at T_cryst + this, to zero at the solidus.
#: Source: V1 `main.py` `_f_flow` default.
MUSHY_BAND_C = 5.0

#: Thermal time constant of the whole stripper as TT-322004 sees it [s]. This is the liquid
#: holdup of the falling film plus the bottom sump, plus the HP shell metal — process inertia
#: rather than transmitter damping, which is why it is carried with the equipment and not
#: with the instrument. Source: V1 `main.py` STRIP_T_TAU_S.
T_STRIPPER_TAU_S = 180.0

#: Fraction of a bottoms-temperature swing that survives the LV-322501 letdown flash [-].
#: TT-323001, immediately downstream of the valve, moves 0.7 deg C for every 1 deg C at
#: TT-322004: the flash itself absorbs the rest, because a hotter feed flashes off more
#: vapour and the extra latent load pulls the remaining liquid back toward the same
#: saturation temperature. Anchored so that TT-323001 is exactly 119.0 deg C at design.
#: Source: V1 `main.py`, the TT_323001 expression in `step_sim`.
TT_323001_GAIN = 0.7


__all__ = [
    "FEED_207_KMOLH", "FEED_207_T_DES_C", "FEED_DES_KMOLH",
    "FEED_NC_DES", "FEED_HC_DES", "FEED_UREA_DES_KMOLH", "FEED_DES_KGH",
    "FRAC_TOP_DES", "XI_HYDROLYSIS_DES", "XI_BIURET_DES",
    "STEAM_DES_KGH", "STEAM_P_DES_BARA", "STEAM_T_DES_C", "DUTY_DES_KW",
    "P_DES_BARA", "DP_TO_LOOP_DES_BAR",
    "T_TOPGAS_DES_C", "T_BOTTOM_DES_C", "T_FLOOD_ANCHOR_C", "FLOOD_GAP_DES_C",
    "T_DOWNSTREAM_DES_C", "SHELL_DUTY_BAND",
    "CP_BOTTOM", "CP_GAS", "DT_STEAM_DES_C",
    "N_TUBES", "TUBE_OD_M", "TUBE_WALL_M", "TUBE_ID_M", "TUBE_L_EFF_M",
    "SURFACE_DES_M2", "RHO_GAS_DES", "RHO_LIQ_IN_DES",
    "FLOOD_KGH_PER_TUBE", "FLOOD_PRACTICE_FRAC", "FLOOD_DES_FRAC",
    "FLOOD_T_RAMP_K", "FLOOD_ETA_FLOOR",
    "DH_CARBAMATE_JMOL", "DH_HYDROLYSIS_JMOL", "DH_NH3_DESORB_JMOL", "DH_H2O_VAP_JMOL",
    "STRIPCOOL_MAX_C", "STRIPCOOL_RAMP_K", "T_TOP_LOAD_K",
    "ETA_KT", "ETA_KN", "ETA_KW", "ETA_FLOOR", "SLIP_GAIN",
    "ETA_CO2_INTERCEPT", "ETA_CO2_SLOPE", "ETA_CO2_LO", "ETA_CO2_HI",
    "ETA_T_CEILING", "MOD_CEILING", "FRAC_TOP_MAX",
    "BIURET_EA_JMOL", "BIURET_R_GAS_J", "BIURET_T_DES_K",
    "V_TUBES_M3", "SUMP_AREA_M2", "LEVEL_SPAN_M", "V_SUMP_M3",
    "LEVEL_SP_DES_PCT", "V_LIQ_DES_M3", "VDOT_DES_M3H", "HYDROLYSIS_T_DES_C",
    "BOTTOMS_DES_KGH", "RHO_BOTTOM", "BOTTOMS_TD_DES_S", "BOTTOMS_LINE_M3",
    "TUBES_FULL_KG", "SUBMERGED_DUTY_FLOOR",
    "LIC_322501_KC", "LIC_322501_TI", "LIC_322501_TD_S", "LIC_322501_TF_S",
    "LV_322501_KVS", "LV_322501_OPEN_DES_PCT", "LV_322501_DP_DES_BAR", "LV_322501_FL",
    "LV_322501_PV_CONVAL_BARA", "LV_322501_T_CONVAL_C",
    "P_DOWNSTREAM_BARA", "LV_322501_P_DOWN_BARA",
    "SUMP_DT_LOSS_DES_C", "T_CRYSTALLISATION_C", "SUMP_NTU_DES", "MUSHY_BAND_C",
    "T_STRIPPER_TAU_S", "TT_323001_GAIN",
]
