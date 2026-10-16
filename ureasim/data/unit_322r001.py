"""322R001 — the HP urea reactor: design point, geometry and calibration anchors.

What this vessel is
-------------------
A 2.95 m bore, 25 m tall vertical column at 144.9 bar a, with eleven sieve trays and no
heating and no cooling of any kind. Two-phase carbamate product from 322E002 enters at the
bottom; liquid urea melt leaves over an internal funnel at the top and goes to the stripper;
uncondensed gas leaves the top separately and goes to 322E003. Everything that happens in
between is done by residence time.

It is the only vessel on the plant where the product is actually made, and the only one whose
behaviour is set by how long the liquid stays inside rather than by a duty or a valve. That
is why so much of this module is geometry: the elevation of four thermowells, the height of a
funnel lip, the bore of the shell. Those numbers ARE the process model.

Sources
-------
* ``Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md`` — stream 207 (the overflow), the
  off-gas vector, the design extents and the operating pressures and temperatures.
* ``References/Datasheets/`` — Reactor Datasheet2 (shell bore, liquid height, nozzle N6 A/B/C/D
  thermowell elevations), UD-AU-322-EC-0006 (nozzle N7, the LT-322504 transmitter geometry),
  drawing UD-AU-322-DZ-0006-010 (the overflow funnel and its downcomer), and the CONVAL valve
  sizing UD-MR-G00-DZ-0042-021 (HV-322605's Kv table).
* ``References/322R001 Description.md`` — the licensor's own account of where the carbamate
  heat is released.
* V1 ``backend/main.py``, the 322R001 block, and ``backend/reactor.py``, for the values V1
  itself back-solved or live-probed. Each of those carries its provenance below.
"""

from __future__ import annotations

import math

from ureasim.core.stream import MW_COMP
from ureasim.thermo.empirical import urea_soln_rho

# ======================================================================================
# The design feed ratios — the three anchors the stripper also reads
# ======================================================================================
#
# These three were published here before the rest of the module existed, because 322E001's
# efficiency penalties are written as deviations from the REACTOR's design feed ratios rather
# than from the stripper's own. The stripper feed includes the CO2 sweep gas, so its N/C and
# H/C are different numbers and would move the penalty off its zero.

#: Design reactor-feed N/C, molar NH3/CO2 [-]. Live-probed from V1's own settled design seed,
#: not taken from a PFD row: the reactor feed is the HPCC product, which is assembled from
#: several live streams, so the design value is whatever the converged flowsheet produces
#: there. Source: V1 `reactor.py` L0_DES.
REACTOR_FEED_NC_DES = 3.072961

#: Design reactor-feed H/C, molar H2O/CO2 [-]. Live-probed at the same seed.
#:
#: V1's note on the re-probe is worth carrying: this was 0.407828 until the 322E003 overflow
#: was corrected to carry PFD stream 206's CO2, which made the HPCC feed drier per unit of
#: carbon. It seeds the recycle H/C lag, so it must be the seed's OWN value or the design
#: point walks over the lag time constant. The re-probed number is also PFD 202+205's H2O/CO2
#: (0.39839), which the superseded one was not — an independent confirmation rather than a fit.
#: Source: V1 `reactor.py` W0_DES.
REACTOR_FEED_HC_DES = 0.39824129577331385

#: Design reactor bulk temperature [deg C], which is also the 322R001 overflow temperature
#: TT-322014 and therefore the stripper's top liquid feed temperature.
#: Source: PFD, V1 `reactor.py` T0_DES_C (= `main.py` REACT_OVERFLOW_T_C).
REACTOR_T_DES_C = 183.0

# ======================================================================================
# The two product streams
# ======================================================================================

#: 322R001 liquid overflow at design [kmol/h] — PFD stream 207, the stripper's top feed.
#:
#: This vector is the reactor's product, so it lives here and `unit_322e001` imports it as its
#: own feed rather than re-entering the figures. Source: PFD stream table, 1750 MTPD, 100 %
#: load; V1 `main.py` STRIP_FEED207_KMOLH, from which V1 derives REACT_OVERFLOW_DES.
OVERFLOW_DES_KMOLH = {"Urea": 1302.6, "Biuret": 2.414, "NH3": 4002.4, "CO2": 897.7,
                      "H2O": 2222.0, "N2": 0.0, "O2": 0.0, "CH4": 0.0, "H2": 0.0}

#: 322R001 top off-gas at design [kmol/h] — to 322E003, measured by TT-322009.
#:
#: Almost 1000 kmol/h of it, and two thirds is ammonia. This stream is why the HP scrubber
#: exists: without recovery the plant would vent about 11 t/h of NH3. The inerts (N2, O2, CH4,
#: H2) arrive dissolved in the CO2 feed and have nowhere else to go, so they concentrate in
#: this line and set the purge rate at HV-322604. Source: PFD, V1 `main.py` REACT_OFFGAS_DES.
OFFGAS_DES_KMOLH = {"NH3": 665.73, "CO2": 197.69, "N2": 44.53, "H2O": 42.51,
                    "O2": 7.42, "CH4": 3.86, "H2": 2.02, "Urea": 0.0, "Biuret": 0.0}

#: Vapour/liquid disengagement fraction per component at the reactor top [-], derived.
#:
#:     theta_i = offgas_des,i / (overflow_des,i + offgas_des,i)
#:
#: The fraction of each species' total production that leaves as gas rather than as melt. It
#: is derived from the two published vectors rather than entered, so the design split is
#: bit-exact by construction and cannot drift from them.
#:
#: The guard matters and is not cosmetic. Urea and biuret have zero off-gas, so their theta is
#: exactly 0; the four inerts have zero overflow, so theirs is exactly 1. Those two groups are
#: therefore STRUCTURALLY non-distributing: any live re-flash of this split leaves them alone
#: by arithmetic, not by an exception list. A reactor that dissolved its own nitrogen would be
#: a new claim and there is no datum for one. Source: V1 `main.py` REACT_THETA_OG.
THETA_OFFGAS = {
    k: (OFFGAS_DES_KMOLH.get(k, 0.0)
        / (OVERFLOW_DES_KMOLH.get(k, 0.0) + OFFGAS_DES_KMOLH.get(k, 0.0))
        if (OVERFLOW_DES_KMOLH.get(k, 0.0) + OFFGAS_DES_KMOLH.get(k, 0.0)) > 1e-12
        else (1.0 if OFFGAS_DES_KMOLH.get(k, 0.0) > 0.0 else 0.0))
    for k in MW_COMP}

#: Design overflow mass [kg/h], about 226 177. Derived from the vector against the
#: atom-consistent molar masses, never entered.
OVERFLOW_DES_KGH = sum(OVERFLOW_DES_KMOLH[k] * MW_COMP[k] for k in MW_COMP)

# ======================================================================================
# The two reaction extents at design
# ======================================================================================

#: Urea-formation extent at design [kmol/h]. Against the 2397.7 kmol/h of CO2 in the reactor
#: feed this is a per-pass conversion of 0.543, which is the figure the whole synthesis loop
#: is sized around: a little over half the carbon converts each pass and the rest is stripped
#: out and sent round again. Source: PFD, V1 `main.py` REACT_XI_UREA_DES.
XI_UREA_DES = 1302.27

#: Biuret-formation extent at design [kmol/h]. Three orders of magnitude smaller than the urea
#: extent, and it is still the number that decides whether the product meets specification.
#: Source: PFD, V1 `main.py` REACT_XI_BIU_DES.
XI_BIURET_DES = 2.414

#: As-built design per-pass CO2 conversion [-], xi_urea / CO2_feed = 1302.27 / 2397.7.
#: Carried as the published anchor and used as the design reference for the conversion-deficit
#: slip when the engine has not pinned a live one. Source: V1 `reactor.py` X_DES.
X_DES = 0.543

#: Thermodynamic conversion ceiling [-], the high-NH3 low-water limit.
#:
#: SOLVED rather than asserted: V1's superseded separable correlation fixed it by requiring
#: that correlation to return the design conversion with its other two coefficients held, and
#: the value it produced is kept because the equilibrium constant below is anchored on it.
#: What it means physically is that no residence time and no feed ratio takes this reaction
#: past about 91 % in one pass. Source: V1 `reactor.py` X_INF.
X_INF = 0.9140

# ======================================================================================
# Operating point
# ======================================================================================

#: Reactor operating pressure [bar a]. Source: PFD, V1 `main.py` REACT_P_BARA.
P_DES_BARA = 144.9

#: Off-gas line pressure to 322E003 [bar a]. Source: PFD, V1 `main.py` REACT_OFFGAS_P_BARA.
OFFGAS_P_DES_BARA = 141.3

#: TT-322014 design overflow temperature [deg C]. The same value as the bulk temperature
#: above, restated under the tag the operator actually reads.
OVERFLOW_T_DES_C = REACTOR_T_DES_C

#: TT-322009 design off-gas temperature [deg C]. Source: PFD, V1 `main.py` REACT_OFFGAS_T_C.
OFFGAS_T_DES_C = 183.0

#: Off-gas temperature blend factor [-]: T_offgas = T_top + gamma . (T_overflow - T_top).
#: The gas leaving the top disengages from liquid that is between the top thermowell and the
#: overflow lip, so it sits between the two. Source: V1 `main.py` REACT_OFFGAS_GAMMA.
OFFGAS_GAMMA = 0.6

#: HV-322605 design opening [% stroke] — Kv_required over Kvs on the linear trim.
#: Source: V1 `main.py` REACT_HIC605_DES_PCT.
HIC605_DES_PCT = 60.0

#: Nominal urea-solution density [kg/m3] used as the volumetric-flow basis and as the melt
#: density reference. Source: PFD, V1 `main.py` REACT_OVERFLOW_RHO.
OVERFLOW_RHO = 990.0

#: Off-gas density at design [kg/m3]. Source: PFD, V1 `main.py` REACT_OFFGAS_RHO.
OFFGAS_RHO = 113.30

#: The SAME density correlation evaluated at the design stream-207 state (34.6 % urea by mass,
#: 183 deg C) [kg/m3], about 834.6.
#:
#: This — not the nominal 990 above — is the datum the Darcy-Weisbach pressure drop to the
#: stripper is normalised by, so that ratio is exactly 1.0 at design. `urea_soln_rho` is a
#: departure model about one global reference state, so it returns its `anchor` argument ONLY
#: at that reference, which stream 207 is a long way from. Source: V1 `main.py`
#: REACT_OVERFLOW_RHO_DES_LIVE.
_OVERFLOW_W_UREA_DES = OVERFLOW_DES_KMOLH["Urea"] * MW_COMP["Urea"] / OVERFLOW_DES_KGH
OVERFLOW_RHO_DES_LIVE = urea_soln_rho(_OVERFLOW_W_UREA_DES, OVERFLOW_T_DES_C, OVERFLOW_RHO)

#: Design volumetric throughput [m3/h], about 228.5. The residence-time basis: overflow mass
#: over the nominal solution density. Source: V1 `main.py` _react_vdot_m3h.
VDOT_DES_M3H = OVERFLOW_DES_KGH / OVERFLOW_RHO

# ======================================================================================
# Shell geometry and the four thermowells
# ======================================================================================

#: Reactor inside diameter [mm]. Source: Reactor Datasheet2, shell 2950 ID.
ID_MM = 2950.0

#: Liquid height, bottom tangent line to top tangent line [mm] — the overflow zone, and the
#: span LT-322504's physical head is measured over. Source: Reactor Datasheet2.
LIQ_H_MM = 25000.0

#: The same height in metres, which is what every hydraulic relation uses.
LIQ_H_M = LIQ_H_MM / 1000.0

#: Liquid cross-sectional area [m2], about 6.835. Derived from the bore.
AREA_M2 = (math.pi / 4.0) * (ID_MM / 1000.0) ** 2

#: Volume of the measured liquid span [m3], about 170.9 — LT-322504's 0 to 100 %.
V_SPAN_M3 = AREA_M2 * LIQ_H_M

#: Thermowell elevations above the bottom tangent line [mm], traced from nozzles N6 A/B/C/D.
#: Source: Reactor Datasheet2.
TT_EL_MM = {"TT_322005": 21700.0, "TT_322006": 14800.0,    # N6 A (top), N6 B
            "TT_322007": 7900.0,  "TT_322008": 1000.0}     # N6 C, N6 D (bottom)

#: The four thermowells in ASCENDING elevation — node 1 at the bottom to node 4 at the top.
#: The list order IS the axial march order, so it is fixed here rather than sorted at use.
NODE_TAGS = ["TT_322008", "TT_322007", "TT_322006", "TT_322005"]

#: Dimensionless node elevations [-], each thermowell's height over the liquid span.
ZETA_NODES = [TT_EL_MM[t] / LIQ_H_MM for t in NODE_TAGS]

#: Total liquid residence time at design [min], about 44.9 — the span volume over the design
#: volumetric throughput. This single number is why the reactor is the slowest thing on the
#: plant: an operator changing the feed ratio waits three quarters of an hour to see all of it.
TAU_TOT_MIN = (AREA_M2 * LIQ_H_M / VDOT_DES_M3H) * 60.0

#: Per-node residence time at design [min], each node's share of the span.
_ZETA_PREV = [0.0] + ZETA_NODES[:-1]
TAU_NODE_MIN = [(z - zp) * TAU_TOT_MIN for z, zp in zip(ZETA_NODES, _ZETA_PREV)]

#: Carbamate-exotherm thermal time constant [min], used only to shape the SEED profile the
#: energy balance is then solved from. Source: V1 `main.py` REACT_THERM_TAU_MIN.
THERM_TAU_MIN = 8.0

#: Damkohler shape parameter for the seed profile [-], about 5.61 — the column residence time
#: over the exotherm time constant. See `reactor_column.node_profile_ss` for what survives of
#: the shape it came from. Source: V1 `main.py` REACT_BETA_DAMK.
BETA_DAMKOHLER = TAU_TOT_MIN / THERM_TAU_MIN

#: Design column temperature rise [deg C] — the 13 C between the 322E002 product at 170 and
#: the overflow at 183. It is the PFD anchor the melt heat capacity is back-solved against,
#: not a term in any rate law. Source: PFD, V1 `main.py` REACT_DT_COL_DES.
DT_COL_DES_C = 13.0

# ======================================================================================
# Liquid inventory, the overflow funnel and LT-322504
# ======================================================================================

#: LT-322504 top normal liquid level [% of the 25 m span] at the design valve opening.
#: Source: PFD / operating data, V1 `main.py` REACT_LEVEL_NLL_PCT.
LEVEL_NLL_PCT = 80.0

#: Design liquid level [m], 20.0 — the head the discharge line is referenced to.
LEVEL_DES_M = LEVEL_NLL_PCT / 100.0 * LIQ_H_M

#: LT-322504 measuring span [m]. Source: datasheet UD-AU-322-EC-0006 p6, "1500".
LT_SPAN_M = 1.5

#: LT-322504 upper range value elevation above the overflow line [m].
#: Source: the same datasheet p14, "1000 TO OVERFLOW PIPE".
LT_ABOVE_OVF_M = 1.0

#: Overflow funnel lip elevation in the engine's level frame [m], 19.3.
#:
#: N7 is a stilling-well transmitter at the reactor top, NOT a full-height gauge: its 0 to
#: 100 % maps a 1.5 m band whose top tap sits 1.0 m above the overflow line. So the lip is
#: PLACED from the transmitter geometry rather than entered — NLL minus (1.0 - 1.5 . 0.2) —
#: which puts the design level 0.7 m above it. The drawings put NLL itself at 21.6 m above the
#: tangent line; the engine's holdup frame is 1.6 m lower and the relative placement absorbs
#: that. Source: V1 `main.py` REACT_WEIR_CREST_M.
WEIR_CREST_M = LEVEL_DES_M - (LT_ABOVE_OVF_M - LT_SPAN_M * (1.0 - LEVEL_NLL_PCT / 100.0))

#: Overflow funnel mouth inside diameter [m]. Source: drawing UD-AU-322-DZ-0006-010.
FUNNEL_ID_M = 1.044

#: Lumped Francis weir coefficient [m3/h per m^1.5], about 21 726 — 1.84 . pi . D in SI,
#: converted to per hour. Free overflow over the funnel's whole circumference, so the head at
#: the design 228 m3/h is only 0.048 m. Source: V1 `main.py` REACT_WEIR_CW.
WEIR_CW = 1.84 * math.pi * FUNNEL_ID_M * 3600.0

#: Melt density reference [kg/m3] at the design bulk temperature. The same 990 as the nominal
#: urea-solution density above, restated as the reference of the thermal-expansion law so that
#: law's anchor is explicit. Source: V1 `reactor.py` RHO_REF.
MELT_RHO_REF = OVERFLOW_RHO

#: Volumetric thermal-expansion coefficient of the melt [1/K]. Cooling contracts the liquid,
#: so a fixed holdup mass reads a LOWER level — the mechanism that pulls a stagnant reactor's
#: surface below the funnel lip as it cools. Source: V1 `reactor.py` BETA_THERMAL.
MELT_BETA_THERMAL = 7.0e-4

#: Holdup floor [kg]. Guards the level calculation against a divide by an emptied vessel.
#: Source: V1 `reactor.py` M_HOLDUP_MIN.
M_HOLDUP_MIN = 1.0

#: Ambient temperature the reactor shell sees [deg C]. Source: V1 `reactor.py` T_AMBIENT_C.
T_AMBIENT_C = 40.0

#: Bulk wall-loss time constant [s], 6 hours — m.cp/(U.A) for an insulated HP shell. It is
#: gated to zero at design flow, so it changes nothing in normal operation; its whole purpose
#: is that a reactor with no flow through it relaxes toward ambient instead of freezing at
#: whatever temperature it stopped at. Source: V1 `reactor.py` TAU_LOSS_S.
TAU_LOSS_S = 21600.0

# ======================================================================================
# HV-322605, the liquid discharge valve
# ======================================================================================

#: HV-322605 inherent characteristic, stroke [%] to Kv [m3/h].
#:
#: The "Characteristics values table" of the vendor CONVAL sizing: DN 200 angle valve,
#: parabolic single-seat plug, linear trim, Kvs 600, Kv0/Kvs 2 %. Between the table points the
#: trim is linear, Kv = 12 + 5.88.s; the shut end is the class-IV seat (0), not that line's
#: 12 m3/h intercept, which is why the first pair is (0, 0) and not (0, 12).
#: Source: UD-MR-G00-DZ-0042-021 p.3, via V1 `reactor.py` HV322605_KV_TABLE.
HV322605_KV_TABLE = ((0.0, 0.0), (5.0, 41.4), (25.0, 159.0), (50.0, 306.0), (75.0, 453.0),
                     (98.53, 591.4), (100.0, 600.0))

# ======================================================================================
# Loop-coupling gains
# ======================================================================================
#
# Every one of these is exactly zero-effect at the design point, which is deliberate: the
# published design state must be reproduced bit-exactly, so a coupling may only act on a
# DEVIATION from it. They are carried with V1's own values and V1's own reasoning.

#: f_L loop N/C gain [-]: how much of an EXOGENOUS fresh-feed N/C deviation reaches the
#: reactor-feed N/C that drives conversion.
#:
#: The reduced model pins the recycle overflow, so the endogenous feed N/C is dominated by an
#: atom-conserving ripple — convert more, consume 2 NH3 per CO2, feed N/C falls — which is a
#: strong NEGATIVE loop that cannot be amplified. Driving off the fresh-feed ratio instead,
#: which the pump speeds set and no feedback touches, restores the loop NH3-enrichment the
#: pinned recycle suppresses. Source: V1 `main.py` REACT_NC_LOOP_GAIN.
NC_LOOP_GAIN = 0.50

#: AT-322701 excess-NH3 partition gain [-]: the fraction of the design overflow ammonia moved
#: between the overflow and the off-gas per unit of feed-N/C deviation.
#:
#: NH3-only, so total nitrogen and total carbon are both held and the shift is conservative by
#: construction. Without it the reactor-to-stripper N/C is atom-pinned and the analyser cannot
#: respond to a ratio change at all. Source: V1 `main.py` REACT_NC_OVERFLOW_GAIN.
NC_OVERFLOW_GAIN = 0.5

#: Conversion-deficit slip amplifier [-]: how much unconverted NH3 and CO2 move from the
#: liquid overflow to the off-gas per unit of fractional conversion shortfall. Also
#: conservative — a re-partition, never a source. Source: V1 `main.py`
#: REACT_OFFGAS_DEFICIT_GAIN.
OFFGAS_DEFICIT_GAIN = 1.0

#: Dimensionless synthesis-pressure forcing per unit conversion deficit [-].
#: Source: V1 `main.py` REACT_PI_KAPPA.
PI_KAPPA = 2.0

#: HP synthesis-loop recycle inventory lag [min]. What the loop's own holdup does to a
#: composition disturbance before it comes back round. Source: V1 `main.py` REACT_TAU_REC_MIN.
TAU_REC_MIN = 5.0

#: Fresh make-up fraction of the reactor feed [-]; the remaining 70 % is lagged recycle.
#: Source: V1 `main.py` REACT_FRESH_FRAC.
FRESH_FRAC = 0.30

#: Forward-carbamate coupling gain [-]: the fraction of a TRANSIENT ejector draw that is
#: pumped forward through 322E002 into this vessel's holdup. Source: V1 `main.py`
#: REACT_FWD_GAIN.
FWD_GAIN = 1.0

#: Forward-carbamate washout time constant [min], about the 322E003 sump redistribution time.
#: Only the high-pass residue of the driver is injected, so a steady valve position contributes
#: nothing and the coupling cannot invent mass. Source: V1 `main.py` REACT_FWD_TAU_MIN.
FWD_TAU_MIN = 8.0

# ======================================================================================
# AT-322701, the overflow N/C analyser
# ======================================================================================

#: Nitrogen atoms per molecule, for the analyser's atom-count ratio.
N_ATOMS = {"NH3": 1, "Urea": 2, "Biuret": 3, "N2": 2}

#: Carbon atoms per molecule, same basis.
C_ATOMS = {"CO2": 1, "Urea": 1, "Biuret": 2, "CH4": 1}

#: Analyser span ceiling [-]; the indication reads over-range above this.
#: Source: V1 `main.py` REACT_NC_SPAN_MAX.
NC_SPAN_MAX = 99.99


__all__ = [
    "REACTOR_FEED_NC_DES",
    "REACTOR_FEED_HC_DES",
    "REACTOR_T_DES_C",
    "OVERFLOW_DES_KMOLH",
    "OFFGAS_DES_KMOLH",
    "THETA_OFFGAS",
    "OVERFLOW_DES_KGH",
    "XI_UREA_DES",
    "XI_BIURET_DES",
    "X_DES",
    "X_INF",
    "P_DES_BARA",
    "OFFGAS_P_DES_BARA",
    "OVERFLOW_T_DES_C",
    "OFFGAS_T_DES_C",
    "OFFGAS_GAMMA",
    "HIC605_DES_PCT",
    "OVERFLOW_RHO",
    "OFFGAS_RHO",
    "OVERFLOW_RHO_DES_LIVE",
    "VDOT_DES_M3H",
    "ID_MM",
    "LIQ_H_MM",
    "LIQ_H_M",
    "AREA_M2",
    "V_SPAN_M3",
    "TT_EL_MM",
    "NODE_TAGS",
    "ZETA_NODES",
    "TAU_TOT_MIN",
    "TAU_NODE_MIN",
    "THERM_TAU_MIN",
    "BETA_DAMKOHLER",
    "DT_COL_DES_C",
    "LEVEL_NLL_PCT",
    "LEVEL_DES_M",
    "LT_SPAN_M",
    "LT_ABOVE_OVF_M",
    "WEIR_CREST_M",
    "FUNNEL_ID_M",
    "WEIR_CW",
    "MELT_RHO_REF",
    "MELT_BETA_THERMAL",
    "M_HOLDUP_MIN",
    "T_AMBIENT_C",
    "TAU_LOSS_S",
    "HV322605_KV_TABLE",
    "NC_LOOP_GAIN",
    "NC_OVERFLOW_GAIN",
    "OFFGAS_DEFICIT_GAIN",
    "PI_KAPPA",
    "TAU_REC_MIN",
    "FRESH_FRAC",
    "FWD_GAIN",
    "FWD_TAU_MIN",
    "N_ATOMS",
    "C_ATOMS",
    "NC_SPAN_MAX",
]
