# handoff.md — Open Issues for the Human Engineer

Tracker for `Urea Simulator V1.1`. It holds **open** items only, each as its **current state**: the
problem, its acceptance tests, what is established, the open options, the next step. A session rewrites
an item's state in place and appends no session paragraph (`CLAUDE.md` §3a). Close an item by deleting it;
its closure is recorded in the session's As-Built Part. Ceiling: 300 lines.

**Last updated:** 2026-11-12, session 103.

**Section A** — issues created by the V1.1 rewrite.
**Section B** — physics gaps inherited from V1 that the rewrite carries forward. Port V1's behaviour
exactly, including the compromise, and keep the item open here.
**Section C** — calibration deferrals: the port reproduces V1 knowingly and the correction waits on the
process engineer's decision.

History, frozen: `docs/history/handoff-record-to-session-95.md` holds the closure schedule, the closed
items' summaries, B-118's chronicle (sessions 76 to 95) and every data-gap row's full search record.

---

# Section A — Rewrite issues

A-33 was raised 2026-11-11 by session 97's deep audit (As-Built Part CVIII); A-38 by session 99 (§CX.6).

### A-33 — Without V1 mounted the equivalence layer does not run

83 test files guard on `v1_available()`; on 2026-11-11 5 862 of 8 016 tests skipped (§CVIII.2).
Options: (a) golden vectors of V1's outputs in `tests/equivalence/`, written by a tool when `E:` is
mounted, and a switch that fails a release run on a V1 skip (recommended); (b) keep as built.

### A-38 — Sixteen modules are tested only through the plant

*Raised 2026-11-11, session 99 (As-Built §CX.6; A-35's reconciliation).* No test imports or names
`engine.plant.absorption`, `engine.plant.boundary`, `hmi.trend.plot`, `hmi.widgets.bargraph`,
`hmi.widgets.icon_geometry`, `hmi.widgets.icons`, `thermo.activity`, `thermo.henry`, `thermo.kvalues`,
`thermo.speciation`, `thermo.splits`, `thermo.srk`, `thermo.standard_state`, `thermo.vle_grid`,
`units.synthesis.hp_split` or `units.synthesis.reactor_calibration`; six more are reached only by V1 equivalence
suites (§CX.6). To do: a behaviour test of each, the thermo ones on the stores' own fixed points.

---

# Section B — Physics gaps inherited from V1

### B-118 — Below 100 % load the engine holds no steady state on the plant's reactor window

*Raised 2026-10-30, session 76. Phase 7. Record: As-Built Parts LXXXIX to XCVIII, C, CIII to CVII and
CX to CXIV; decisions 177, 180, 181 and 188.*

**Problem.** The plant runs for hours at reduced load. The committed engine, ramped from its design
seed, does not, on every operating policy tried:

* 70 to 85 %: trip 22.1 within 20 to 80 minutes (322E003's sump floods, or it vents and TT-322015
  passes 110 C), or trip 22.2; where neither fires, 322R001 collapses (TT-322005 158-172 C).
* 90 to 95 %: a cold branch, TT-322005 168-178 C, conversion 36-48 %.

**Acceptance tests (decision 180).** The 100 % design pin held to the bit, and five plant holds on the
plant's own handles, TT-322005 inside Book2's band (+/- 2 K) and no trip:

| Hold | Source | Plant values |
|---|---|---|
| 92.3 % | `References/DCS Trends/Book2.xlsx`, 755 samples | TT-322005 182.6 C, AY-322701 3.25, PT-329201 137.4 bar, PIC-329204 18.2 bar g, PT-329207 4.11 bar g, TIC-329005 90.0 C, HIC-322604 51.5 %, TT-322002 166.75 C, TT-322004 166.6 C, FY-329403 52.09-55.08 t/h |
| 69.3 %, 3 h | Book2's dwell (As-Built Part C, §CIV.1) | TT-322005 181.5 C, PIC-329204 16.6 bar g, TIC-329005 94.1 C, HV-322602 40 %, HVGT-322605 36.1 %, HIC-322604 46.5 %, AY-322701 3.19, PT-329201 132.1 bar g, PT-329207 4.398 bar g |
| 90.5 %, 2 h 46 min | `Data/Trends 511.2026`, 5 November 2026 (§CV.2-3) | TT-322005 not logged; HV-322602 = 65.4 % (L / 101.95 %)^1.6 |
| 74.4 %, 72 min | the same | TIC-329005 98.3 C, HV-322602 35-40 %, PT-329201 132.5-133.5 bar g at 69-75 % |
| 68.9 %, 46 min | the same | the same |

Licensor's windows (Operating Manual III §5.2): N/C 2.90-3.10, TT-322005 180-183 C, PT-329201 136-143 bar.
And A-34's atoms closed tick by tick on a turndown (`tests/phase7/test_loop_atoms.py`, §CX.1).

**Established. Do not measure these again; cite the section.**

* The cold branch's term is 322R001's carbamate source, the gas CO2 from 322E002 less the off-gas CO2;
  322E002's flash loses half its CO2 gas per kelvin of TT-322010; the column's budget closes on every tick
  (§CVI.1-4). On the holdup bundle it is again the first term to fail at 92.3 % (§CXIV.6).
* The low holds' latch (session 95's collapse: 322E002's feed N/C through 3.0 onto the low-N/C branch, a
  recycle of 14-21 minutes, §CVIII.3, §CX.8) is the loop's missing species state: with 322R001's liquor
  carried by species it does not come at 74.4, 69.3 or 68.9 %, and with the product unscaled the hump goes
  (§CXIII.3, §CXIV.3, §CXIV.6). 322E003's flood and vent are its symptoms (§CV.3, §CVII.5).
* Measured and not the cause: TT-322011's vent-top correlation and 322E002 over-quenching (Part XCI);
  322E001's overhead fraction (§XCIV.2); 322E003's liquor, tempered water and condensation margin (§XCIV.3-4,
  §XCV.3); 322E001's feed-deficit bottoms term (§XCVI.2); the ramp's rate and HIC-322605's handling (Part CIV);
  the slip gain at 70 % (§CIII.7); P6 (§CVII); E0 (§CX.8); E1eu (§CXII.7, §CXIV.3); the ratio's floor
  (§CXII.8); the AT trim's gain (§CXIV.3).
* Rejected: P5 (§CVI.5). Unbundled (decision 181): the S2 stripper terms and slip gain 0 (§CVII).
* Boundary facts for every arm. Each handle starts on the engine's design seed and moves as a
  departure with the load (§CVI.5, §CVII.1). FFIC-321404's ratio is on the engine's basis: the
  plant's 2.115 is 2.047-2.053 here (§XCIII.3). HV-322605's anchor is 60.0 % at 100 %, so Book2's
  36.1 % is 43.27 % here (§CIV.1). FT-329403 is stream 901, 60.85 t/h at the design (§XCVIII.2).
  LT-329501 cannot reach Book2's 7 %: 322F001's suction is proportional to the level (§XCVI.2).

**Bundle A (decision 181), scratch only; `ureasim/` is as built.** P1, 322E002's UA on the battery-limit
CO2 demand ratio to the power 0.77 (§CVII.1); P4, the wall loss on a stagnant reactor only; the 322F001 lift
p_disch,eff = p_disch - 2.41 (1 - r^2) (decision 180); `unit_322e001.SLIP_GAIN` 4.0.

**The holds, on bundle A (§CXII.10) and with B-126 (b)'s holdup added (§CXIV.6).**

| Hold | Bundle A | Bundle A and 322R001's species holdup |
|---|---|---|
| 92.3 % | passes | fails: the cold branch (latch 6 990 s; with E1eu 161.3 C, no latch) |
| 90.5 % | trip-free, out of band 47 min | latches 6 800 s on the cold branch |
| 74.4 % | latches 4 680 s | trip-free; AT-322701 falling 0.11 per hour |
| 69.3 %, 3 h | latches 5 040 s | passes; AT-322701 levels at 2.45 as the seed's liquor washes out |
| 68.9 % | latches 4 920 s | trip-free; AT-322701 falling 0.15 per hour |
| 111 % | quiet, out of Book2's bands | out of band, swinging (8 000-9 000 s), three handles at their bounds |

**Next step.** The holdup bundle is a build candidate under the plan's rule (§CXIV.8); the options are
§CXIV.11's and the process engineer's. Recommended, scratch: its cold branch at 92.3 %, why TT-322010 falls
and takes 322E002's CO2 gas with it, and whether the holdup's design-composition seed moves it.

**B-120 folded in (decisions 177, 181).** V1's stripper slip gain drives a loop mode: gain 0 removes it
at 92.3 % on the S2 prototype and at 111 % (§XCVIII.3), and alone runs the reactor 12.4 K colder at
92.3 % (§CIII.7). On the holdup bundle (§CXIV.7) gain 0 neither holds 92.3 % (TT-322005 161.9-182.9 C, one
cycle) nor removes the 111 % mode, and no arm reaches 603 kmol/h of gas CO2 to 322R001 at 92.3 %, the
passing control included. The gain stays 4.0.

### B-125 — 322E002's saturation law has no margin at the design and contradicts Book2

*Raised 2026-11-11, session 97 (§CVIII.4). Decisions 97 and 135's law.* `saturation_fraction` loses 1.54 %
of all condensation per bar its deficit stands above zero, and the deficit is zero at the design. As
built it gives 0.857 at Book2's 92.3 % band and 0.798 at 69.3 %, where the plant condenses fully (the melt
N/C taken as AY-322701 + 0.2, an inference). The outlet temperature is an NTU quench of a 350 K spike.
Established: the deficit is +6.4 to +11.2 bar at Book2's five bands (§CX.8); on the 74.4 % ramp the K_N line
is the whole deficit through the N/C hump (§CXI.2), and makes the fraction's dip, not the hump (§CXII.7).
Session 101 (§CXII.2-3, §CXII.7): E1eu, Extended UNIQUAC's shape on both sides (ridge at 4.5, `BUB_KN`
retired), needs a margin of 4.38 bar, set by the 69.3 % band. It holds the fraction at 1 on the seed and
through the 74.4 % hump; the hump stays, and the melt N/C falls through 3.0 before the fraction leaves 1: the
law does not initiate B-118's collapse. Its seed is not bit-identical: 644 physical leaves pass 1e-5 and 19
console strings flip a last digit, the largest departures last-digit flips; the unit at the design feeds is
identical on the engine's anchor and not on its default (P_bub +0.146 bar). Options: (a) keep as built;
(b) E1eu, on a seed criterion the process engineer restates (the design pin, each published tag to its last
digit, the fraction); (c) the outlet at the melt's bubble temperature, only if (b) fails. Alone, (b) leaves
the as-built cold branch as it is (§CXII.7); as a rider on B-126's holdup (H4, §CXIV.3, §CXIV.6) it
matches the holdup without it at every hold scored: no bundle measured needs it.

### B-126 — 322R001's 136 t of liquor has no composition

*Raised 2026-11-11, session 97 (§CVIII.5).* `reactor_inventory.py:328-329` sends on the tick's reaction
product scaled to the hydraulic outflow. Measured 305 s after a 20 % CO2 cut: the overflow carries
2 933 kmol/h more N and 576 kmol/h more C than the reaction step produced. On the 74.4 % descent (N3,
§CXII.9, §CXIII.2) the inventory sends on 8.40 t more than its reaction sent it, at the product's
composition, and creates 213 kmol of N and 71 of C booked at the overflow's. The loop's 153 t of liquor
(322R001 135.9 t, 322E002 9.5, 322E001 3.9, 322E003 3.8) holds no species (§CXIII.3).
Measured in scratch (Part CXIV): (b), the holdup's species carried in twelve compartments on its eleven trays,
the overflow at the last one's composition, the hydraulics as built (decisions 141 and 146's class), on bundle
A. Its balance closes to 6e-14 kmol a tick. The 74.4 % hump falls from 3.649 to 3.197 and the latch goes at
74.4, 69.3 and 68.9 %; the seed's N-rich liquor washes out for about 4 h at 69.3 % (AT-322701 levels 0.53 under
the target); 92.3 and 90.5 % then fall onto the cold branch. Its seed against the plain seed: 849 leaves differ,
742 above 1e-5, 24 console strings by a last digit (bundle A alone 752, 417, 11). The loop's other holdups
(H5) close the loop's atoms to 7e-6 of the N in. A build candidate under the plan's rule, not built. Options
(§CXIV.11): (a) keep as built; (b) build the bundle, a seed criterion restated first; (c) measure its cold
branch at 92.3 % first (recommended); (d) the loop's other holdups with it.

### B-127 — The loop's design boundary does not close, and the reactor's tear follows the CO2 load

*Raised 2026-11-11, session 97 (§CVIII.6); V1's reconciliation, once flagged as B-75.* In 134 215.2,
out 132 190.3 kg/h. The reactor removes 2 107.45 kg/h from its feed, NH3 129.1 kmol/h of it, 5.1 % of the
fresh ammonia, scaled on the CO2 load ratio. E5's trace (§CXII.5): the PFD's own boundary closes within 0.4
kmol/h; row 116, the motive re-pinned on the engine's ratio basis (42 762.05 against 40 756 kg/h), carries
117.46 kmol/h of NH3, 91 % of the tear's NH3 and 97 % of its N; the bottoms' and 308's re-pins the rest. On
the descent the tear and the fresh ammonia follow the delivered CO2 within 18 kmol/h; 322E001's bottoms do
not (§CXII.9). [I: the tear and B-128's basis are one fact.] Options: (a) keep as built; (b) the correction
moved onto row 116 as its departure, decision 104's class, once B-128's basis is decided.

### B-128 — FFIC-321404's 2.0 floor binds on the engine's basis

*Raised 2026-11-11, session 97 (§CVIII.7).* `RATIO_SP_MIN` 2.0 is applied to the engine's ratio (design
2.0231 for the plant's 2.086 molar): 1.1 % of downward authority against the plant's 5.4 %. Options: (a)
keep as built (the process engineer's, for now); (b) the faceplate shows and takes the plant's basis; (c)
the floor restated on the engine's basis, 1.9397. Measured (§CXI.2, §CXII.8): on the 74.4 % ramp the set
point sits on the floor from 900 to 1 680 s while the PV stays at 2.021-2.028; with the floor at 1.9397
session 95's trim asks for at most 0.0045 below 2.0, the hump moves by 0.002, the collapse by 10 s, the
latch by -250 s. On this trim the floor does not decide B-118. Row 116's re-pin is the same basis (B-127).
The DCS readback checklist's row 15 asks the faceplate's limits and basis.

---

# Section C — Calibration Deferrals

*None open.*

---

# Open data gaps

*`Claude.md` §4: a datum that `References\`, the vendor archive and the V1 source all fail to supply.
The ledger was accepted by the process engineer on 2026-10-16 (decision 128); the numbers are the
ledger's. Each row keeps its stand-in as built. Every row's full search record is in
`docs/history/handoff-record-to-session-95.md`: grep the tag there before the archive is searched
again. Rows 2, 4, 5, 8, 9 and 10 close on one plant DCS readback session
(`D:\Work\reports\DCS readback checklist.md`); rows 1 and 3 on Körting's curves. The checklist's row 14, TV-323013B's flow and differential, is
decision 178's cross-check and no ledger row.*

| # | Datum | Needed by | As built | Found so far | Route to close |
|---|---|---|---|---|---|
| 1 | 322F001's nozzle and mixing-throat geometry, loss coefficients and performance diagrams | `control/jet_pump.py`, `data/unit_322f001.py` | both areas back-solved from the licensor's design duty on open-literature loss coefficients; the design point exact, the stall margin not (B-12's 90.7 %, §LXXI.3); the lift a fixed 4.2 bar | no vendor geometry or curve in either archive (§LIX.4). The plant keeps the entrainment ratio from 69 to 102 % load, mu / mu_ref 1.031 +/- 0.044, n 15; the as-built closure stalls on that line at 69.9-80.7 %; a friction share of at least 2.41 bar of the lift passes it, a fit (§CV.3-4). Book2's points: LT-329501 11 % at HV-322602 40 % (69.3 %), 1 % at 54 % (80.4 %). LT-329501 is not in the 5 November trends, so the level term is unfitted; session 99 (§CX.9): the friction share needed is 0-2.41 bar over the 15 windows, and no level law fits Book2's four points (V1's passes 1-23 % of the plant's suction there) | Körting's 14 diagrams, order 2/131/4/04219 (draft request: `D:\Work\reports\Koerting request draft s99.md`). The lift prototype is held with B-118 (decision 180) |
| 2 | TT-322015's H2 hysteresis | I 22.1's release (B-56) | H2 110 C (the DCS readback, decision 103); hysteresis V1's 2 K, cleared below 108 C | the object display shows range 0-200 C, H1 100.0, H2 110.0, delay 0 and no hysteresis field (photograph of 24 October 2026) | checklist row 1: the engineering view of the limit; else the 2 K stand-in signed off |
| 3 | Körting's performance curves of 324F002, 324F004 and 324F005 | `ejector_map`, B-57's interpolation on the synthesized maps (§XLIX.4, §L.1) | synthesized maps, anchored on the PFD's design loads; in-situ factors 0.919, 0.336, 0.497 | one duty point an ejector; no curve in the archive (§XLVIII.2). The plant's motive break-off, the datum a curve must meet: HIC-329605 between 55 and 64 % (HIC-329606 38-40 %) at PT-329207 4.20-4.24 bar g, 5 November 2026 13:11-13:16, 75 % load; the engine's vacuum still holds there (§CV.5) | Körting, orders 2/115/4/09674 and 2/232/4/00503 (the same draft); checklist row 13: 324E002's and 324E005's cold-end and cooling-water temperatures for 5 November 13:00-13:30 |
| 4 | LT-324501's taps | LI-324501 between its taps (decision 33's class) | V1's holdup ratio (§L.4) | one 80 mm instrument on the barometric leg at EL +8495 (isometric UD-RL-100-MB-0180, item 22); no second connection drawn; the span cannot be weighed from the trends (§CV.7) | checklist row 11: LRV, URV and the reference connection; a walk-down |
| 5 | AC4 PC21's limits and elements: FY-322403's L2; PT-321211 / 221's L2; ST-321952 / 953's H2; the T elements' mode; the SR flip-flops' dominance; TRIP_84_8_FLAG1's L2 | trips 21.2, 21.8 and 21.10 (§LXV.6) | FY-322403's L2 V1's 5 %; PDY's L2 0.1 bar; the T elements on-delays; reset dominant; PT-321211 / 221, ST-321952 / 953 and TRIP_84_8 taken healthy | the limits are database entries; the scan does not resolve the timer symbol (UD-MR-G00-FF-0004 pages 5, 7, 20); TRIP_84_8 is the instrument air, two of PT-384207A / B / C below L2 (§LXXIII.2) | checklist rows 3 to 8, one readback session |
| 8 | LT-323503's L2 hysteresis | 323P008's restart (B-96) | trip below 5 %, restart at 7 %: the 2 % stand-in of 2026-10-15 (§LXVIII.2) | the faceplate confirms L2 5.0 %, H1 80.0 %, L1 20.0 %, delay 0 s; no hysteresis shown | checklist row 2; else the stand-in signed off |
| 9 | FIC-335405's row in the DCS tuning table | the loop on the plant's tuning (decisions 76, 77) | V1's 100 per t/h and 15 s | not in `References/Master_PID_Tuning_Constants.md`; not photographed; the trends log FT-335405 alone, its ratio to FT-335401 0.0046-0.0050 (§CV.7) | checklist row 9: the faceplate's tuning page, then decision 10's span conversion |
| 10 | LT-329505's tap elevations | LI-329505 between its taps (decision 33's class) | V1's holdup ratio; LV-329505 on Flowserve's trim (§LXVIII.5) | upper tap 324E001 / N5 at EL +15129; lower tap on the DN700 condensate pot at EL +10651 (isometric UD-RL-100-MB-0312): 4 478 mm apart. The loop summary prints 3 000 mm. The conflict is logged, not resolved (§CIII.5) | checklist row 10: the transmitter's LRV and URV decide which span its 0-100 % covers |
