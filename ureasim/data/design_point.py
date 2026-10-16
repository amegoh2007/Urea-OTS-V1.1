"""Design-basis anchors — the numbers the simulator is pinned to.

Strict source
-------------
`References/Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md`, 100 % load. Every
constant here carries the row, regression or datasheet it came from. Nothing is a
"reasonable value".

Why anchors exist at all
------------------------
The simulator must reproduce the licensor's heat and mass balance **bit-exactly** at
100 % load, or every downstream initialisation drifts. So wherever a correlation supplies a
*trend*, it is wrapped in a departure form anchored on one of these numbers:

    phi_live = phi_anchor + [ phi_raw(live) - phi_raw(design) ]      additive
    phi_live = phi_anchor * [ phi_raw(live) / phi_raw(design) ]      multiplicative

At the design state the bracket is exactly 0 (or 1), so the published value is preserved to
the bit and only the off-design response comes from the model.

See the As-Built Mathematical Reference, Part 0, Rule 1.
"""

from __future__ import annotations

# ======================================================================================
# Unit 323 — LP recirculation solution properties
# ======================================================================================

#: Lumped urea-solution specific heat [kJ/(kg.K)].
#: Source: the 323 design seed; it is the anchor `urea_soln_cp` departs from.
R323_CP_SOLN = 2.5

# --------------------------------------------------------------------------------------
# C10 audit — urea-solution density regression
# --------------------------------------------------------------------------------------
# A linear regression of the PFD's own published urea-solution density rows. It is used
# ONLY as a departure: at the design composition and temperature the departure term is a
# literal 0.0 (same function, same inputs), and `anchor + 0.0 == anchor` bit-exactly in
# IEEE-754. So every design value the licensor published is preserved to the bit, and only
# the off-design response changes.
#
#     rho_raw(w, T) = A + B w + C (T - 100)

#: Regression intercept [kg/m3].
C10_RHO_A = 972.0821
#: Slope per unit urea mass fraction [kg/m3].
C10_RHO_B = 255.9536
#: Temperature slope [kg/(m3.K)].
C10_RHO_C = -0.465942

#: Design anchor composition — stream 315/317, ex 323D002 [mass fraction urea].
C10_W_DES = 0.80
#: Design anchor temperature [deg C].
C10_T_DES = 99.0


# ======================================================================================
# Unit 323 — recirculation design flow chain
# ======================================================================================
# Every downstream design flow in the 323/324 train is derived from ONE measured number,
# the stripper bottoms flow, through the licensor's own published split fractions. Written
# as a chain rather than as five independent constants so the balance closes by
# construction: a change to the feed propagates, and no stage can be edited into
# disagreement with its neighbours.
#
# The splits are the PFD's own stream flows put over their parent stream, so each carries
# its provenance in the arithmetic rather than in a comment alone.

#: Design bottom-solution flow out of the HP stripper 322E001 [kg/h].
#: Source: PFD stream 313 / the model design bottom. V1 `STRIP_BOT_DES_KGH`.
STRIP_BOT_DES_KGH = 130482.0

#: Vapour split to the LP carbamate condenser at the top of 323C003 [-]: stream 305 over
#: the column feed. 0.188249.
R323_PHI_V305 = 24582.0 / 130582.0

#: Flash-vapour split at 323F004 [-]: stream 701 over the column bottoms. 0.041792.
R323_PHI_V701 = 4430.0 / 106000.0

#: Water boiled off stream 319 in the pre-evaporator 323F010 [-]. 0.086147.
R323_PHI_VEVAP = 8750.0 / 101570.0

#: 323C003 design feed [kg/h] — the stripper bottoms, live value is the drain flow.
R323_FEED_DES_KGH = STRIP_BOT_DES_KGH

#: 323C003 bottoms to the 323F004 flash tank [kg/h] (stream 314).
R323_M314_DES = (1.0 - R323_PHI_V305) * R323_FEED_DES_KGH

#: 323F004 liquid to the 323F010 pre-evaporator [kg/h] (stream 319).
R323_M319_DES = (1.0 - R323_PHI_V701) * R323_M314_DES

#: 323F010 product to the 323D002 solution tank [kg/h] (stream 317).
R323_M317_DES = (1.0 - R323_PHI_VEVAP) * R323_M319_DES

#: 323D002 throughput on to unit 324 [kg/h] — the same stream, renamed at the boundary.
R323_M324_DES = R323_M317_DES

#: Unit 324 evaporation feed [kg/h]. Identical to the tank throughput by definition; kept
#: as its own name because unit 324 is specified against it.
R324_FEED_DES = R323_M324_DES

#: Effective density of the 80 % urea product at 99 deg C [kg/m3].
#: Source: PFD streams 315 / 317. V1 `R323_D002_RHO`.
R323_D002_RHO = 1151.0


# ======================================================================================
# Unit 324 — the strengths unit 323 reads
# ======================================================================================

#: Evaporator I feed strength [mass fraction urea], PFD 315 / 317 at 80.00 %. Source: V1
#: `R324_W_IN`. Unit 323 reads it as the fallback of 323D002's urea lookups.
R324_W_IN = 0.80

#: Evaporator II product strength [mass fraction urea], PFD 402 at 97.71 %. Source: V1
#: `R324_W_EV2` ("HARD; HMB 324, was 0.986"). Unit 323 reads it as the fallback of the
#: LV-324501B melt recycle's urea lookup at 323D002.
R324_W_EV2 = 0.9771


__all__ = [
    "R323_CP_SOLN",
    "C10_RHO_A", "C10_RHO_B", "C10_RHO_C",
    "C10_W_DES", "C10_T_DES",
    "STRIP_BOT_DES_KGH",
    "R323_PHI_V305", "R323_PHI_V701", "R323_PHI_VEVAP",
    "R323_FEED_DES_KGH", "R323_M314_DES", "R323_M319_DES", "R323_M317_DES",
    "R323_M324_DES", "R324_FEED_DES", "R323_D002_RHO",
    "R324_W_IN", "R324_W_EV2",
]
