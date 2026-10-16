"""Unit 320 — CO2 feed compressor and discharge line design constants.

What this covers
----------------
320K002, the CO2 feed compressor — a boundary feed outside the simulator's scope (decided
2026-10-08), so only the suction it floors its discharge line on — and the discharge line that
carries its delivery to the XV-322902 tie-in at 322E001. The PV-322203 line vent and its PIC live here too, because the
vent takes its mass out of the same node.

Source discipline
-----------------
Four provenances appear and they are not interchangeable:

* **PFD / design basis** — the design CO2 rate and composition, the feed-line pressure,
  temperature and density. These are the anchor.
* **the PFD's suction** — stream 105, 1.3 bar a (V1's 1.6 bar a carried no source).
* **DCS measurement** — the 345 s feed dead time, from which the line inventory is
  back-solved.
* **stated assumption** — the check valve's crack pressure. No check-valve datasheet exists in
  `References/Datasheets`; a representative value applied openly, in the same class as
  `FL_GLOBE` and `XT_GLOBE`. Recorded in `handoff.md` §Open data gaps.
"""

from __future__ import annotations

from ureasim.core.stream import MW_COMP
from ureasim.core.units_of_measure import ATM_BARA
from ureasim.data.control_valves import PV_322203, design_stroke_pct
from ureasim.data.relief_devices import RELIEF_DEVICES, RELIEF_SIZING
from ureasim.data.unit_321 import CO2_DES_KGH, FEED_TD_S
from ureasim.data.unit_322e003 import OVERFLOW_P_DES_BARA

# ======================================================================================
# The CO2 feed stream
# ======================================================================================

#: Feed composition [mole fraction]. Source: PFD, V1 `main.py` CO2_FEED_MOLFRAC. The stream
#: is not pure CO2 — the inerts here are the ONLY source of the N2 and O2 that later leave in
#: the 322E003 vent, so dropping them would force the reactor recycle tear to create them.
CO2_FEED_MOLFRAC = {"CO2": 0.9524, "H2O": 0.0061, "N2": 0.0355, "O2": 0.0060}

#: Mean molar mass of the feed [kg/kmol], 43.21. Derived from the composition above against
#: the atom-consistent `core.stream.MW_COMP`, never entered as a literal.
CO2_FEED_MW = sum(CO2_FEED_MOLFRAC[k] * MW_COMP[k] for k in CO2_FEED_MOLFRAC)

#: Mass fraction of true CO2 in the feed [-], about 0.970.
CO2_MASSFRAC_CO2 = CO2_FEED_MOLFRAC["CO2"] * MW_COMP["CO2"] / CO2_FEED_MW

#: Design total molar flow [kmol/h]. Source: PFD, V1 `main.py` CO2_DES_KMOLH.
CO2_DES_KMOLH = 1264.0

#: TI-322017 design feed temperature [C], after the aftercooler.
#: Source: PFD, V1 `main.py` CO2_T_FEED_C.
CO2_T_FEED_C = 120.0

#: Design CO2 feed-line pressure [bar a] — PIC-322203's PV at design.
#: Source: PFD, V1 `main.py` CO2_P_DES_BARA.
CO2_P_DES_BARA = 144.2

# ======================================================================================
# 320K002 — the compressor
# ======================================================================================

#: Suction pressure [bar a], the floor of the discharge line's node: a line with no feed and
#: its vent open falls no lower than the machine it is open to. Source: PFD 20 (1750 t/d), stream
#: 105, the CO2 and its passivation air entering 320K002 (As-Built §LXII.1); V1's 1.6 bar a had
#: no source.
CO2_K_SUCT_P_BARA = 1.3

#: Ratio of specific heats of the CO2 line gas [-], for PV-322203's vent sizing.
#: Source: V1 `main.py` CO2_K_GAMMA.
CO2_K_GAMMA = 1.29

# ======================================================================================
# PV-322203 — the line vent
# ======================================================================================

#: PV-322203 discharge back pressure [bar a], the LP safe header.
#: Source: V1 `main.py` CO2_VENT_P_BARA.
CO2_VENT_P_BARA = 5.0

#: Vent design temperature [K] — the feed temperature, since the vent takes line gas.
CO2_VENT_T_DES_K = CO2_T_FEED_C + 273.15

#: Vent design molar mass [kg/kmol] — likewise the line's own.
CO2_VENT_MW_DES = CO2_FEED_MW

#: PV-322203's trim and design stroke [%]. CCI's data sheet (`ureasim.data.control_valves`)
#: gives a Drag 28-stage angle valve, equal percentage, rated Cv 32, passing the whole CO2 feed
#: — 28 021 Nm3/h at 145 -> 3 bar a — at Cv 14.36. DECIDED 2026-09-30 (handoff B-44): the vent
#: runs that trim, anchored where its rated Cv passes the design CO2, 79.33 % — so wide open it
#: passes 2.2 times the feed. V1 anchored the whole feed at 100 % on a linear trim ("the valve
#: is sized to be able to take the whole feed"), which is half the valve's capacity.
PV_322203_CHAR = PV_322203.characteristic
PV_322203_OP_DES_PCT = design_stroke_pct(PV_322203, CO2_DES_KGH)

#: PIC-322203 proportional gain [% output per bar]. DIRECT acting: a rising line pressure
#: opens the vent. Source: V1 `main.py` PIC_322203_KC.
PIC_322203_KC = 1.0

#: PIC-322203 integral time [s]. Kc/Ti = 0.5 preserves the gain of the integral-only form it
#: replaced. Source: V1 `main.py` PIC_322203_TI.
PIC_322203_TI = 2.0

#: PIC-322203 set-point span [bar a]. The operator cannot enter a set point outside it, and
#: the bumpless set-point-to-PV transfer on entering AUTO is clamped to it as well. Source:
#: V1 `main.py` `handle_cmd`, the "pic_set" branch, which clamps both paths to [120, 175].
PIC_322203_SP_LO_BARA = 120.0
PIC_322203_SP_HI_BARA = 175.0

# ======================================================================================
# The discharge line, its tie-in, and the synthesis anchor it works against
# ======================================================================================

#: 322E003 overflow-line pressure [bar a] — PT-329201 at design. This is the synthesis loop
#: pressure the CO2 line works against, and it is the reference pressure of every anchored
#: split in the 322 section.
#:
#: The scrubber's overflow line is where the tag physically sits, so `unit_322e003` owns the
#: number and this is V1's own alias for it — `main.py` writes exactly the same assignment,
#: `SYN_P_DES_BARA = SCRUB_OVERFLOW_P_BARA`. Keeping the alias rather than a second literal
#: is what makes the tie-in differential below a bit-exact subtraction of the same float.
SYN_P_DES_BARA = OVERFLOW_P_DES_BARA

#: 322E003 / 322R001 mechanical design pressure [bar g]. Source: datasheet.
SYN_P_MECH_DESIGN_BARG = 160.0

#: SV-32201 set pressure [bar a], 161.01325, on the standard atmosphere (decided 2026-10-07,
#: handoff B-6; V1's 161.013 on its 1.013 bar) — see `core.units_of_measure`.
SYN_PSV_SET_BARA = SYN_P_MECH_DESIGN_BARG + ATM_BARA

#: Design differential across the XV-322902 tie-in [bar], 3.5.
#:
#: **Derived as a subtraction of the two design pressures, never as a rounded decimal.** That
#: is the rule handoff A-13 states: the check valve's anchor is bit-exact only when the live
#: differential evaluates to the same float as this one, and `144.2 - 140.7` does not equal a
#: literal `3.5` in IEEE 754. V1 already writes it this way; the rule exists so the next site
#: does too.
CO2_DP_HP_DES = CO2_P_DES_BARA - SYN_P_DES_BARA

#: Check-valve crack pressure [bar], 2 % of the design tie-in differential.
#: **Stated assumption** — no check-valve datasheet exists. Expressed as a fraction of the
#: licensor's own design differential so it scales with the site rather than being a bare
#: number. Same class as `FL_GLOBE` and `XT_GLOBE`.
CO2_CHECK_CRACK_BAR = 0.02 * CO2_DP_HP_DES

#: CO2 inventory of the battery-limit discharge line [kg], 5234.2. Back-solved from the
#: DCS-measured 345 s feed dead time at the design flow, exactly as the ammonia line is.
FEED_CO2_LINE_KG = CO2_DES_KGH / 3600.0 * FEED_TD_S

#: PFD CO2 feed-line density at 144.2 bar a and 120 C [kg/m3].
#: Source: PFD, V1 `main.py` CO2_LINE_RHO_DES.
CO2_LINE_RHO_DES = 242.70

#: Discharge-line volume [m3], 21.566.
#:
#: NOT a new number. A line holding M kg of gas has BOTH a dead time `M/mdot` and a
#: capacitance `R.T/(V.Mbar)` with `V = M/rho`. Deriving the two from one inventory is a
#: physical CONSTRAINT between them, not a second free parameter — if the real run length ever
#: turns up it replaces the back-solve and both follow it.
CO2_LINE_V_M3 = FEED_CO2_LINE_KG / CO2_LINE_RHO_DES

# ======================================================================================
# SV32064 — the line's certified relief (decided 2026-10-09, handoff B-83 option a)
# ======================================================================================

#: SV32064 on CO02-320202 at 320K002's discharge, protecting 320R001 (P&ID 101): set 160 bar g,
#: 161.013 bar a on its sheet's 1.013 bar (Uhde UD-RL-320-EC-0003; Sempell's selection prints the
#: same set). It reseats 10 % of set below, at 145.013 bar a (Sempell UD-RL-G00-DZ-0001-001
#: page 72).
SV32064_SET_BARA = RELIEF_DEVICES["SV32064"].set_bara
SV32064_RESEAT_BARA = RELIEF_SIZING["SV32064"].reseat_bara(RELIEF_DEVICES["SV32064"])

#: Its certified capacity [kg/h], 74 444.40, on orifice H (615.75 mm2, lift-limited to 5.26 mm,
#: alpha_w 0.654): CO2 gas at 140 C and 177.013 bar a, the set pressure plus 10 %, molar mass
#: 43.370, isentropic exponent 1.510 and compressibility 0.74 as the sheet prints them — which
#: back-solve the orifice the line's gas is vented through.
SV32064_CAP_KGH = RELIEF_SIZING["SV32064"].capacity_kgh
SV32064_P_REL_BARA = RELIEF_SIZING["SV32064"].relieving_bara(RELIEF_DEVICES["SV32064"])
SV32064_T_REL_K = RELIEF_SIZING["SV32064"].t_c + 273.15
SV32064_MW_REL = RELIEF_SIZING["SV32064"].mw
SV32064_K = RELIEF_SIZING["SV32064"].k
SV32064_Z_REL = RELIEF_SIZING["SV32064"].z


__all__ = [
    "CO2_FEED_MOLFRAC", "CO2_FEED_MW", "CO2_MASSFRAC_CO2", "CO2_DES_KMOLH",
    "CO2_T_FEED_C", "CO2_P_DES_BARA",
    "CO2_K_SUCT_P_BARA", "CO2_K_GAMMA",
    "CO2_VENT_P_BARA", "CO2_VENT_T_DES_K", "CO2_VENT_MW_DES", "PV_322203_CHAR",
    "PV_322203_OP_DES_PCT",
    "PIC_322203_KC", "PIC_322203_TI", "PIC_322203_SP_LO_BARA", "PIC_322203_SP_HI_BARA",
    "SYN_P_DES_BARA", "SYN_P_MECH_DESIGN_BARG", "SYN_PSV_SET_BARA",
    "CO2_DP_HP_DES", "CO2_CHECK_CRACK_BAR",
    "FEED_CO2_LINE_KG", "CO2_LINE_RHO_DES", "CO2_LINE_V_M3",
    "SV32064_SET_BARA", "SV32064_RESEAT_BARA", "SV32064_CAP_KGH", "SV32064_P_REL_BARA",
    "SV32064_T_REL_K", "SV32064_MW_REL", "SV32064_K", "SV32064_Z_REL",
]
