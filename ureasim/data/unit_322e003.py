"""322E003 — the HP scrubber: design streams, the shell-side duty anchor, the sump, and the
HV-322604 purge letdown off its top.

What this vessel is
-------------------
A vertical falling-film reactive absorber sitting at the top of the synthesis loop. Hot,
inert-rich off-gas from 322R001 rises through the tubes; cold weak carbamate from the LP
recirculation section falls down the tube walls as a film. Ammonia and carbon dioxide cross
into the liquid and react there instantaneously,

    2 NH3(aq) + CO2(aq) <-> NH2COONH4(l)        dH ~ -160 kJ/mol

so the liquid-phase concentrations of both stay near zero and the transfer is gas-film
controlled. The nitrogen, oxygen, methane and hydrogen cannot react and cannot dissolve, so
they pass straight through and leave at the top. Tempered cooling water on the shell carries
the reaction exotherm away, because if the film is allowed to heat up the equilibrium shifts
back and absorption stops.

Why the plant has one
---------------------
The synthesis loop is not closed. Inerts arrive dissolved in the CO2 feed and with the
passivation air, and if they are not purged they blanket the carbamate condenser and the
reactor top. But the gas they have to be purged in is saturated with ammonia. Without this
vessel the plant would vent on the order of 11 t/h of NH3 to recover 60 kmol/h of nitrogen.
322E003 is what makes the purge affordable: it recovers the reactants into a carbamate
stream that goes straight back into the loop through the 322F001 ejector, and it vents
1.7 t/h instead.

It is therefore the loop's recovery boundary in both directions. Everything that leaves the
synthesis section as gas leaves through here, and everything the 322F001 ejector entrains
comes from here.

Sources
-------
* ``Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md`` — stream 204 (the vent, MOL %),
  stream 206 (the overflow), stream 308 (the weak-carbamate wash, MASS %), and streams 1111
  and 1112 (the tempered cooling water supply and return).
* ``References/322E003 HP Scrubber Describtion.md`` — the licensor-level account of the
  reactive-absorption mechanism, the inert boundary layer and the cooling requirement.
* ``References/Urea_NormalOp_29-06-2025_Trends.md`` — the measured TT-322002, TT-322011,
  TIC-329005 and TDY-329125 means, which are quoted against each design pin below.
* V1 ``backend/main.py``, the 322E003 block, for the values V1 itself back-solved: the
  shell-side conductance and the sump inventory scale. Each carries its provenance.

What this module deliberately leaves out
----------------------------------------
V1 defines four constants in this block that nothing in V1 ever reads —
``SCRUB_OFFGAS_MOL_DES`` (the published 64.78 kmol/h, superseded by the derived vent total
below), ``SCRUB_CARB_KMOLH_DES_REF`` (a frozen copy of the wash vector kept as a deviation
datum), and ``SCRUB_CARB_T_C`` / ``SCRUB_CARB_P_BARA`` (the wash inlet state, PFD 308 at
74 C and 140.7 bar a). They are recorded here and not ported, per the reachable-only rule.
The FV-329409 and TV-329005 design openings and the two CCW controller tunings are also
V1's, but they belong to the 329 tempered-water loop rather than to this vessel, and they
land when that loop does.

Two more in the HV-322604 block are left out on the same rule. ``SCRUB_HV604_DP_DES`` (the
136.7 bar design differential) has no reader. ``SCRUB_HV604_RANGE`` is read only by
``_eq_pct``, the incompressible equal-percentage factor the IEC 60534 law replaced, and
``_eq_pct`` itself is no longer called. The trim's rangeability is
`control.valve.EQUAL_PCT_RANGE`, which is the same 50.
"""

from __future__ import annotations

import math

from ureasim.core.stream import MW_COMP, atom_ratio
from ureasim.core.units_of_measure import R_GAS_FITTED_J
from ureasim.data.tube_plugging import PluggedBundle
from ureasim.data.unit_322r001 import (
    C_ATOMS,
    NC_SPAN_MAX,
    N_ATOMS,
    OFFGAS_DES_KMOLH as REACTOR_OFFGAS_DES_KMOLH,
    OVERFLOW_DES_KMOLH as REACTOR_OVERFLOW_DES_KMOLH,
)
from ureasim.thermo.splits import saturated_inert_vent

# ======================================================================================
# The weak-carbamate wash — PFD stream 308
# ======================================================================================

#: Design weak-carbamate wash [kg/h] delivered by 323P001 A/B. Source: PFD stream 308.
#:
#: This is the recycle arriving from the LP recirculation section, and it is the reason the
#: scrubber can absorb anything: it is cold (74 C against the 183 C off-gas) and it is
#: already carbamate, so it has capacity for more. The pump that delivers it is on the
#: LIC-323502 level cascade, which is why a 323-section upset shows up here as a wash
#: shortfall before it shows up anywhere else.
WASH_KGH_DES = 36915.0

#: Wash composition [mass %]. Source: PFD stream 308. Liquid rows in the PFD stream table
#: are mass per cent — checked against the published 22.81 kg/kmol average molar weight,
#: which the mass basis reproduces and the mole basis does not.
WASH_MASSPCT = {"CO2": 38.49, "H2O": 30.83, "NH3": 30.61, "Urea": 0.07}

#: The same wash as a molar vector [kmol/h], about 1618.5 total against the PFD's 1618.63.
WASH_KMOLH_DES = {k: WASH_MASSPCT.get(k, 0.0) / 100.0 * WASH_KGH_DES / MW_COMP[k]
                  for k in MW_COMP}

# ======================================================================================
# The vent — PFD stream 204, and the closure that produces it
# ======================================================================================

#: Off-gas composition at design [mol %]. Source: PFD stream 204, the vapour row.
#:
#: Nearly 90 % inert, which is the whole point of the vessel: the ammonia that entered the
#: tubes at 665 kmol/h leaves at 5.4. Gas rows in the PFD stream table are MOLE per cent —
#: checked the same way as the wash above, against the published 26.36 kg/kmol.
#:
#: The literal order is the PFD's and is load-bearing: the normalising sum below is a float
#: addition, and reordering these seven terms moves the last bit of every saturation
#: fraction derived from them.
OFFGAS_MOLPCT = {"N2": 68.81, "O2": 11.39, "NH3": 8.26, "CH4": 5.93,
                 "H2": 3.14, "CO2": 2.22, "H2O": 0.26}

#: The species that cannot be absorbed, in the order their total is summed.
#:
#: Structural, not a tuning list. None of these four reacts with carbamate and none has
#: meaningful solubility in it at 140 bar, so every kmol that enters the tubes leaves at the
#: top. That is what fixes the vent RATE.
VENT_INERTS = ("N2", "O2", "CH4", "H2")

#: The species that are absorbed, in the order their saturation is summed.
VENT_CONDENSABLE = ("NH3", "CO2", "H2O")

#: Saturated mole fraction of each condensable in the vent at design [-]:
#: NH3 0.08259, CO2 0.02220, H2O 0.00260. Derived from PFD 204 by normalising the published
#: mol % — which sums to 100.01, so the normalisation is not a no-op.
#:
#: This is the composition the design vent carries, and the live vent rides it through the
#: K-value ratio at PT-329201. It is an anchor in the sense of directive 5.2: the absolute
#: activity model is extrapolated at 140 bar, so only the RATIO is taken from it and the
#: measured saturation is kept.
VENT_Y_DES = {k: OFFGAS_MOLPCT[k] / sum(OFFGAS_MOLPCT.values()) for k in VENT_CONDENSABLE}

#: Cap on the total condensable mole fraction the saturation may reach [-].
#:
#: The inert-basis factor 1/(1 - sum y_c) diverges as the condensables approach filling the
#: gas. That limit is a gas with no inerts left in it, which is not a vent at all — it is
#: the closure being asked a question outside what it describes. Capping the saturation
#: keeps the factor bounded at 20. It is four times the design sum of 0.1074 and does not
#: bind at any normal operating point. Source: V1 `main.py` SCRUB_VENT_Y_MAX.
VENT_Y_MAX = 0.95

# ======================================================================================
# The design streams, closed by construction
# ======================================================================================

#: Combined tube feed at design [kmol/h]: the reactor off-gas plus the wash.
FEED_DES_KMOLH = {k: REACTOR_OFFGAS_DES_KMOLH.get(k, 0.0) + WASH_KMOLH_DES[k]
                  for k in MW_COMP}

#: Design vent [kmol/h] — PFD stream 204, DERIVED rather than entered.
#:
#: 64.787 kmol/h and 1708.3 kg/h at 26.368 kg/kmol, against the PFD's published 64.78,
#: 1708 and 26.36. Nothing was fitted to land there: the inerts are whatever the reactor
#: sent, and the condensables are the published saturation.
#:
#: Why this is derived and not pinned (V1 report A-2). The vent used to be solved from the
#: scrubber's own material balance instead, which took it to 214.8 kmol/h at 44 % ammonia —
#: 5901 kg/h against the PFD's 1708 — because a balance with a pinned overflow has to put
#: the surplus somewhere and the vent was the only free stream. Solving the vent from its
#: own physics and taking the overflow by difference puts it back on the PFD row and closes
#: the unit per species by construction.
_VENT_DES = saturated_inert_vent(FEED_DES_KMOLH, VENT_INERTS, VENT_CONDENSABLE,
                                 VENT_Y_DES, VENT_Y_MAX)
OFFGAS_DES_KMOLH = {k: _VENT_DES.get(k, 0.0) for k in MW_COMP}

#: Design bottom overflow [kmol/h] — PFD stream 206, the 322F001 ejector's suction.
#:
#: 2517.49 kmol/h and 57 561.3 kg/h against the PFD's 2517.69 and 57 564, which is 0.005 %.
#: Everything the tubes received that the vent did not take. `unit_322f001` imports this
#: vector as its design suction rather than carrying a literal, so the ejector and the
#: scrubber cannot disagree about one stream.
OVERFLOW_DES_KMOLH = {k: FEED_DES_KMOLH[k] - OFFGAS_DES_KMOLH[k] for k in MW_COMP}

#: Design vent mass [kg/h], 1708.32. The loop's only gas export.
OFFGAS_DES_KGH = sum(OFFGAS_DES_KMOLH[k] * MW_COMP[k] for k in MW_COMP)

#: Design overflow mass [kg/h], 57 561.3.
OVERFLOW_DES_KGH = sum(OVERFLOW_DES_KMOLH[k] * MW_COMP[k] for k in MW_COMP)

#: Design AT-322701 reference [-], the reactor overflow's N/C on an atom basis, 2.99975.
#:
#: The zero of the TT-322011 slip correlation below. It is the REACTOR's overflow and not
#: this vessel's, because AT-322701 sits on the reactor product line; the correlation is
#: written as a deviation from it so that at design the deviation is exactly zero and the
#: published vent temperature is bit-exact. Source: V1 `main.py` SCRUB_OFFGAS_NC_DES.
OFFGAS_NC_DES = atom_ratio(REACTOR_OVERFLOW_DES_KMOLH, N_ATOMS, C_ATOMS, NC_SPAN_MAX)

# ======================================================================================
# Operating point — the published temperatures and pressures
# ======================================================================================

#: TT-322011, the vent-top off-gas temperature at design [deg C]. Source: PFD stream 204.
#:
#: The plant's own DCS reads this tag at a mean of 130.3 C over the 1921-sample normal-
#: operation trend, 16 C above the PFD row. The design basis is the PFD (directive 4), so
#: the pin is 114.0 and the gap is recorded rather than split; the correlation below moves
#: the published value with the loop's ammonia slip, which is the mechanism that would
#: account for it.
OFFGAS_T_DES_C = 114.0

#: TT-322011 sensitivity to loop ammonia slip [deg C per N/C unit].
#:
#: Process utility. At a high feed N/C the loop runs CO2-limited: the excess ammonia has no
#: carbon to form carbamate with, so it slips through the scrubber unabsorbed and its vapour
#: load lifts the uncondensed vent-top temperature. Driven off (AT-322701 - N/C_des), so it
#: is identically zero at design. Calibrated, not measured. Source: V1 SCRUB_OFFGAS_T_GAIN.
OFFGAS_T_GAIN = 120.0

#: TT-322011 sensitivity to the HV-322604 opening [deg C per unit of theta/theta_des - 1].
#:
#: Opening the purge valve pulls more uncondensed vapour over the top, so the vent-top
#: thermowell sees hotter gas. Source: V1 SCRUB_OFFGAS_T_VENT_GAIN.
OFFGAS_T_VENT_GAIN = 20.0

#: TT-322002 sensitivity to the same opening [deg C per unit], opposite sign.
#:
#: The other end of the same action: relieving the vessel through the vent cools the bottom
#: carbamate overflow, and closing the valve pressurises and heats it. Source: V1
#: SCRUB_OVERFLOW_T_VENT_GAIN.
OVERFLOW_T_VENT_GAIN = 12.0

#: Off-gas line pressure at design [bar a] — the synthesis loop's own. Source: PFD 204.
OFFGAS_P_BARA = 140.7

#: Off-gas density at design [kg/m3], 114 C and 140.7 bar a. Source: PFD stream 204.
OFFGAS_RHO = 111.0

#: TT-322002, the bottom overflow temperature at design [deg C], 165.
#:
#: DECIDED 2026-10-07 (handoff B-16, the process engineer's re-pin): PFD stream 206 gives 165 C,
#: and the DCS trend reads TT-322002 at a mean of 165.7 C over 1921 samples
#: (`References/Urea_NormalOp_29-06-2025_Trends.md`). V1 pins 178.8 (`main.py`
#: SCRUB_OVERFLOW_T_C), the 322F001 ejector's suction temperature `EJ_T_SUCTION_C`, a
#: pseudo-temperature carrying the carbamate's heat of mixing rather than a thermowell reading.
#: The ejector keeps its 178.8 as its own enthalpy carrier (`unit_322f001.T_SUCTION_DES_C`); the
#: shell-side conductance below, the condensing temperature's anchor and the thermal driving
#: force are anchored on this pin and follow it: the conductance rises from V1's 58.5 to 69.0 kW/K
#: and the overflow sits 20 C under the condensation ceiling where V1's sat 6.2 C under it.
#: Source: PFD stream 206.
OVERFLOW_T_DES_C = 165.0

#: PT-329201, the overflow line pressure at design [bar a]. Source: PFD stream 206.
#:
#: This is the synthesis loop's reference pressure. Every anchored split in the 322 section
#: takes it as the denominator of its K-value ratio, and `unit_320` re-exports it under V1's
#: own alias `SYN_P_DES_BARA` so the CO2 line's tie-in differential is computed against the
#: same float. The DCS mean is 139.6 bar a.
OVERFLOW_P_DES_BARA = 140.7

#: Carbamate-formation exotherm [kJ per mol of CO2 absorbed].
#:
#: Source: `References/322E003 HP Scrubber Describtion.md`, section 3. Used in two places:
#: as the diagnostic absorption duty the unit publishes, and — as an effective enthalpy of
#: condensation — as the Clausius-Clapeyron slope that makes the condensing temperature ride
#: the loop pressure. Source: V1 `main.py` SCRUB_DH_CARB_KJMOL.
DH_CARB_KJMOL = 160.0

#: HIC-322604 design opening [%], the inert purge valve: where its trim passes the design purge.
#:
#: DECIDED 2026-10-10 (handoff B-18, project.md decision 99): 72 %, the stroke the vendor's own
#: trim passes the licensor's normal purge at — IEC 60534-2-1 choked on the CONVAL calculation's
#: Kvs 2.1, xT 0.74 and equal-percentage table (UD-MR-G00-DZ-0042-010, 21.06.2005; the instrument
#: specification UD-MR-G00-DZ-0042-001) needs Kv 0.69 to 0.72 for PFD 204's 1688.0 kg/h, 71.7 to
#: 72.5 % stroke (As-Built §XXVI.6). V1 anchors it at 50 % with no source
#: (``SCRUB_HIC604_DES_PCT``). The anchor is the zero of both vent-opening deviation terms above and
#: the valve's characteristic: the plant's 78.2 % passes 1.27 times the design purge on it, 3.01 on
#: V1's.
HIC604_DES_PCT = 72.0

# ======================================================================================
# HV-322604 — the inert-purge letdown to 322C001
# ======================================================================================

#: 322C001 LP absorber pressure [bar a], the letdown's downstream boundary.
#:
#: Held constant: the absorber is not a pressure node in this model. Against 140.7 bar a the
#: pressure ratio is 0.028, and the IEC 60534 choke threshold is x = F_gamma.xT = 0.696, so
#: the seat is choked at its own design point and stays choked until the absorber side rises
#: above about 42.7 bar a. The flow does not depend on this number anywhere in the operating
#: range; the outlet temperature does. Source: V1 `main.py` SCRUB_HV604_P_OUT, report D-2;
#: `References/HV-322604 description.md` puts the LP absorber at 3 to 5 bar.
HV604_P_OUT_BARA = 4.0

#: Ratio of specific heats of the purge gas [-].
#:
#: V1 chose 1.30 for an NH3/CO2-rich off-gas (NH3 1.31, CO2 1.29, inerts 1.40). The PFD 204
#: vent is in fact 89 mol % inert, for which the ideal-gas mixture value is nearer 1.38. While
#: the seat is choked at both the design point and the live point, the anchored ratio does not
#: depend on this value at all; it sets where choking ends. V1 keeps 1.30, and its SV-32201
#: relief sizing reuses it as the loop gas's ratio. Source: V1 `main.py` SCRUB_HV604_GAMMA.
HV604_GAMMA = 1.30

#: Design molar mass of the purge gas [kg/kmol] — the PFD 204 vent's own, 26.368 against the
#: published 26.36.
#:
#: Passed to the anchored valve law as the DESIGN molar mass, separately from the live one,
#: so the composition does not cancel out of the ratio: a heavier purge puts more kilograms
#: through the same trim, w ~ sqrt(M). The same expression as V1's, summed in the same key
#: order, so it is the same float. V1 guards the divisor with max(., 1e-12); the design vector
#: is a constant 64.8 kmol/h, so the guard cannot bind and is not carried. Source: V1
#: `main.py` SCRUB_HV604_MW_DES.
HV604_MW_DES = OFFGAS_DES_KGH / sum(OFFGAS_DES_KMOLH.values())

#: HV-322604 outlet temperature below which carbamate is flagged as depositing [deg C].
#:
#: The purge line is steam-traced to hold a 60 C baseline. The flag fires only when
#: Joule-Thomson cooling overwhelms the tracing, and it is a fouling warning, not a flow
#: restriction — this is a gas line. Source: V1 `main.py` step_sim, the L3-7
#: CARBAMATE_DEPOSITION flag.
CARBAMATE_DEPOSITION_T_C = 20.0

# ======================================================================================
# The sump — LT-329501 and the 322F001 suction it feeds
# ======================================================================================

#: Sump normal liquid level [%].
#:
#: The design attractor of the inventory balance: at design the condensate the scrubber
#: makes and the mass the ejector entrains are the same number, so the holdup derivative is
#: exactly zero and the level sits here. Source: V1 `main.py` SCRUB_LEVEL_NLL_PCT.
LEVEL_NLL_PCT = 50.0

#: Sump residence time at design throughput [min]. Sets the inventory SCALE.
#:
#: Back-solved by V1 rather than measured: no datasheet in ``References/`` gives the sump
#: volume of this vessel. It only sets how fast the level moves, never where it settles —
#: the design steady state is a zero derivative and is independent of it. Source: V1
#: `main.py` SCRUB_TAU_HOLDUP_MIN.
TAU_HOLDUP_MIN = 4.0

#: Liquid inventory at normal level [kg], about 3837.
HOLDUP_NLL_KG = OVERFLOW_DES_KGH * TAU_HOLDUP_MIN / 60.0

#: Liquid inventory at a full sump [kg], about 7675. The level scale is linear in holdup,
#: so 100 % is the normal-level inventory scaled by 100/NLL.
HOLDUP_MAX_KG = HOLDUP_NLL_KG * 100.0 / LEVEL_NLL_PCT

#: LT-329501 two-phase swell at total loss of condensation [% of span].
#:
#: Process utility — this is an operator trap, and it is modelled on purpose. LT-329501 is a
#: differential-pressure cell, and a DP cell does not read mass: it reads the hydrostatic
#: head of whatever column stands between its taps. Stop condensing and the sump boils, the
#: mixture density collapses with the void fraction, and the column swells upward to hold the
#: same mass. Over a fast transient the swell beats the density loss, so **the indication
#: rises while the vessel is actually draining** — the drain to 322F001 keeps pulling long
#: after the condensate make has stopped. Scaled by the condensation deficit, so it is
#: identically zero whenever the shell is condensing normally. Source: V1 SCRUB_SWELL_PCT_MAX.
SWELL_PCT_MAX = 18.0

#: Amplitude of the swell's hunt [+/- % of span at total loss of condensation].
#:
#: The reading is not merely high, it is unsteady: a DP cell straddling a frothing column
#: sees the head fluctuate as slugs and bubbles pass its taps. Half of why an operator learns
#: to mistrust this indication is that it hunts at exactly the moment it matters.
#: Source: V1 `main.py` SCRUB_SWELL_NOISE_PCT.
SWELL_NOISE_PCT = 2.0

#: The two hunt periods [s] — the slug scale and the bubble scale.
#:
#: Incommensurate on purpose, and driven off the simulation clock rather than a random
#: number generator: a training simulator must replay the same excursion the same way every
#: time an instructor runs it. Source: V1 SCRUB_SWELL_NOISE_T1_S / _T2_S.
SWELL_NOISE_T1_S = 17.0
SWELL_NOISE_T2_S = 7.3

#: The carbamate overflow's crystallisation solidus [deg C]: below it plus the mushy band the
#: overflow to 322F001 is throttled (L3-5). Source: V1's literal 60.0 in ``step_sim`` 8116,
#: ``_f_flow(scrub["T_overflow"], 60.0)``.
OVERFLOW_T_CRYST_C = 60.0

# ======================================================================================
# The shell side — tempered cooling water, PFD streams 1111 and 1112
# ======================================================================================
#
# A closed tempered-water loop, not once-through cooling water: 329P006 A/B circulates it
# through the shell, FIC-329409 sets the rate, TIC-329005 sets the supply temperature, and
# the heat is rejected downstream through 329E002 and 329E004. It is tempered because the
# scrubber must not be cooled too hard either — carbamate crystallises at about 60 C, and a
# solidified overflow line is worse than a warm one.

#: Design circulation [kg/h], 306 t/h. Source: PFD streams 1111 and 1112.
CCW_KGH_DES = 306000.0

#: Specific heat of the tempered water [kJ/kg.K]. Source: V1 `main.py` SCRUB_CCW_CP.
CCW_CP_KJKGK = 4.18

#: TIC-329005 supply temperature into the shell at design [deg C]. Source: PFD stream 1111.
#: The DCS trend mean is 84.5 C.
CCW_T_IN_DES_C = 80.0

#: TT-329125 return temperature out of the shell at design [deg C]. Source: PFD stream 1112.
#: The DCS trend puts the measured rise TDY-329125 at 20.1 K against this 15.0 K design.
CCW_T_OUT_DES_C = 95.0

#: Supply and return line pressures [bar a]. Source: PFD streams 1111 and 1112.
CCW_P_IN_BARA = 9.0
CCW_P_OUT_BARA = 8.0

#: Water density at the supply and return temperatures [kg/m3]. For the published stream
#: records only. Source: V1 `main.py` SCRUB_CCW_RHO_IN / _OUT.
CCW_RHO_IN = 971.8
CCW_RHO_OUT = 961.9

#: Design shell duty [kW], 5329.5 — the carbamate-condensation exotherm the loop removes.
#:
#:     Q = m_ccw . cp . (T_out - T_in) / 3600
#:
#: Derived from the three PFD rows above, never entered, so the duty and the cooling-water
#: stream can never disagree.
Q_CCW_DES_KW = CCW_KGH_DES * CCW_CP_KJKGK * (CCW_T_OUT_DES_C - CCW_T_IN_DES_C) / 3600.0

#: Heat-capacity rate of the design circulation [kW/K], 355.3.
_C_CCW_DES_KWK = CCW_KGH_DES * CCW_CP_KJKGK / 3600.0

#: Effective conductance at design [kW/K], 62.70 — the duty over the design approach (V1's
#: 53.94 on its 178.8 C pin, handoff B-16).
_UA_EFF_DES_KWK = Q_CCW_DES_KW / (OVERFLOW_T_DES_C - CCW_T_IN_DES_C)

#: Shell-side conductance [kW/K], 68.99. BACK-SOLVED, and the back-solve is the anchor.
#:
#:     eps_des = UA_eff,des / C_ccw,des = 0.17647            single-stream effectiveness
#:     UA      = -C_ccw,des . ln(1 - eps_des) = 68.99 kW/K    (V1's 58.505 on 178.8 C, B-16)
#:
#: Process utility. The conductance is constant and the EFFECTIVENESS floats with the water
#: rate, which is what makes the unit behave correctly when FIC-329409 is throttled: less
#: water is a hotter return AND a hotter process side, and in the limit of no water at all
#: both asymptote to the condensation ceiling instead of dividing by zero. Inverting the
#: effectiveness-NTU relation at the design point is what makes the two published design
#: temperatures — 165 C overflow and 95.0 C return — come out exactly, from one number.
#: Source: V1 `main.py` SCRUB_UA_KWK.
UA_KWK = -_C_CCW_DES_KWK * math.log(1.0 - _UA_EFF_DES_KWK / _C_CCW_DES_KWK)

#: Carbamate condensation ceiling [deg C] — the highest temperature the shell side can
#: reach.
#:
#: The asymptote the effectiveness-NTU bridge runs into when the cooling water stops, rather
#: than the infinity a raw duty-over-conductance would give. Above 185 C the carbamate the
#: shell is meant to be condensing is not condensing at all, so the model stops there and
#: says so. Set above the 165 C design overflow (V1's 178.8, handoff B-16) to leave the loop
#: pressure room to move.
#: Source: V1 `main.py` SCRUB_T_PROC_C.
T_PROC_C = 185.0

#: Residual condensation duty at a completely flooded sump [-].
#:
#: Process utility. A sump filling above normal level progressively floods the shell-side
#: condensation surface from the bottom, so the duty falls as the level rises. The derate is
#: linear from 1.0 at normal level to this floor at 100 %, and it is a FLOOR rather than a
#: zero because the upper tubes stay wetted and keep condensing. Source: V1
#: `main.py` SCRUB_COND_CHOKE_MIN.
COND_CHOKE_MIN = 0.30

#: Condensation-duty sensitivity to the 322F001 ejector spindle [-].
#:
#: Process utility. The motive jet sets how hard the off-gas is drawn down through the
#: bottom condensation zone. Closing HV-322602 makes the jet stronger and the suction deeper,
#: so more gas is condensed per unit time and the duty rises; opening it does the reverse.
#: Driven off the same (1 - 1/phi_spindle) term the reactor's forward-carbamate coupling
#: uses, so it is identically zero at the design opening. Source: V1 SCRUB_COND_SPINDLE_GAIN.
COND_SPINDLE_GAIN = 0.25

#: Dead band on the condensation-capacity gate [-].
#:
#: Not a tolerance on the physics, a tolerance on a controller's own residual. The capacity
#: ratio is built from live controller process variables, and TIC-329005 settles on
#: 80.00000005 C rather than a bit-exact 80.0, which leaves the ratio at 1 - 5.3e-10. A
#: deficit four orders below any instrument resolution is not a deficit, and treating it as
#: one would make the uncondensed mass non-zero at design and take the swell overlay and the
#: loop-pressure phase term with it. Source: V1 `main.py` SCRUB_COOL_FRAC_EPS.
COOL_FRAC_EPS = 1.0e-6

# --- the condensing temperature's pressure dependence ---------------------------------
#
# The shell condenses carbamate, so its condensing temperature RIDES the loop pressure, by
# Clausius-Clapeyron on the carbamate exotherm:
#
#     1/T_cond(P) = 1/T_des - (R / dH_carb) . ln(P / P_des)
#
# The slope at the anchor is R.T^2/(dH.P) = 0.0709 K/bar on the 165 C pin (0.0754 on V1's 178.8,
# handoff B-16). That is small, and the sign is the
# reason it is here at all: V1's previous formulation divided the condensation capacity by
# the pressure ratio instead, which asserts that a HIGHER loop pressure makes the condenser
# WEAKER. With the sign wrong the loop fed back on itself — capacity fell, off-gas went
# uncondensed, the retained vapour raised the pressure, and the capacity fell further.

#: Carbamate exotherm on a molar-J basis [J/mol], for the Clausius-Clapeyron slope.
COND_DH_JMOL = DH_CARB_KJMOL * 1000.0

#: The reciprocal-temperature anchor [K] and pressure anchor [bar a] of that relation.
COND_T_DES_K = OVERFLOW_T_DES_C + 273.15
COND_P_DES_BARA = OVERFLOW_P_DES_BARA

#: Gas constant used in the Clausius-Clapeyron slope [J/mol.K].
#:
#: The FITTED 8.314, not CODATA. V1 uses its own rounded constant throughout the synthesis
#: correlations and the anchored form means the choice only affects the slope, but the
#: slope is the relation. See `thermo.parameters` for why the two are kept apart.
COND_R_JMOLK = R_GAS_FITTED_J

#: 322E003's bundle: 525 tubes 25 x 2.5 mm, 2,170 mm effective, 38 mm pitch at 30 deg, 89.50 m2
#: (N.pi.d_o.L = 89.47). Source: Uhde DDS UD-AU-322-EC-0005 rev 00, page 3, lines 25 and 34 to 38
#: (the vendor archive's "322E003 HP Scrubber Datasheet.pdf", a scan, read from the page image).
#: 16 tubes plugged at the last turnaround (decided 2026-10-28, decision 155): 0.96952 of the
#: bundle in service, 86.77 m2; the plugged bores hold 0.011 m3. ``UA_KWK`` holds on the tubes in
#: service, re-anchored at a coefficient 1 / f_tubes above the clean bundle's (handoff B-113 (b)).
TUBES = PluggedBundle(n_total=525, n_plugged=16, tube_od_m=0.025, tube_wall_m=0.0025,
                      tube_l_eff_m=2.170, surface_m2=89.50)


__all__ = [
    "TUBES",
    "WASH_KGH_DES", "WASH_MASSPCT", "WASH_KMOLH_DES",
    "OFFGAS_MOLPCT", "VENT_INERTS", "VENT_CONDENSABLE", "VENT_Y_DES", "VENT_Y_MAX",
    "FEED_DES_KMOLH", "OFFGAS_DES_KMOLH", "OVERFLOW_DES_KMOLH",
    "OFFGAS_DES_KGH", "OVERFLOW_DES_KGH", "OFFGAS_NC_DES",
    "OFFGAS_T_DES_C", "OFFGAS_T_GAIN", "OFFGAS_T_VENT_GAIN", "OVERFLOW_T_VENT_GAIN",
    "OFFGAS_P_BARA", "OFFGAS_RHO", "OVERFLOW_T_DES_C", "OVERFLOW_P_DES_BARA",
    "DH_CARB_KJMOL", "HIC604_DES_PCT",
    "HV604_P_OUT_BARA", "HV604_GAMMA", "HV604_MW_DES", "CARBAMATE_DEPOSITION_T_C",
    "LEVEL_NLL_PCT", "TAU_HOLDUP_MIN", "HOLDUP_NLL_KG", "HOLDUP_MAX_KG",
    "SWELL_PCT_MAX", "SWELL_NOISE_PCT", "SWELL_NOISE_T1_S", "SWELL_NOISE_T2_S", "OVERFLOW_T_CRYST_C",
    "CCW_KGH_DES", "CCW_CP_KJKGK", "CCW_T_IN_DES_C", "CCW_T_OUT_DES_C",
    "CCW_P_IN_BARA", "CCW_P_OUT_BARA", "CCW_RHO_IN", "CCW_RHO_OUT",
    "Q_CCW_DES_KW", "UA_KWK", "T_PROC_C",
    "COND_CHOKE_MIN", "COND_SPINDLE_GAIN", "COOL_FRAC_EPS",
    "COND_DH_JMOL", "COND_T_DES_K", "COND_P_DES_BARA", "COND_R_JMOLK",
]
