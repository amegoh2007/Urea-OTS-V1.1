# handoff.md — Open Issues for the Human Engineer

Tracker for `Urea Simulator V1.1`. It holds **open** items only, each as its **current state**: the
problem, its acceptance tests, what is established, the open options, the next step. A session rewrites
an item's state in place and appends no session paragraph (`CLAUDE.md` §3a). Close an item by deleting it;
its closure is recorded in the session's As-Built Part. Ceiling: 300 lines.

**Last updated:** 2026-11-14, session 109.

**Section A** — issues created by the V1.1 rewrite.
**Section B** — physics gaps inherited from V1 that the rewrite carries forward. Port V1's behaviour
exactly, including the compromise, and keep the item open here.
**Section C** — calibration deferrals: the port reproduces V1 knowingly and the correction waits on the
process engineer's decision.

History, frozen: `docs/history/handoff-record-to-session-95.md` holds the closure schedule, the closed
items' summaries, B-118's chronicle (sessions 76 to 95) and every data-gap row's full search record.

---

# Section A — Rewrite issues

A-33 was raised 2026-11-11 by session 97's deep audit (As-Built Part CVIII); A-38 by session 99 (§CX.6);
A-40 by session 105 (§CXV.2).

### A-33 — Without V1 mounted the equivalence layer does not run

83 test files guard on `v1_available()`; on 2026-11-11 5 862 of 8 016 tests skipped (§CVIII.2). With `E:`
mounted the whole suite runs: on 2026-11-12, 8 079 passed and 4 failed, none skipped (§CXV.2); on HEAD 18a7656,
8 082 passed, 1 failed (A-40), none skipped (§CXV.16). One failure (A-40) had been hidden by the skip since session 99. Options: (a) golden vectors
of V1's outputs in `tests/equivalence/`, written by a tool when `E:` is mounted, and a switch that fails a release
run on a V1 skip (recommended); (b) keep as built.

### A-40 — The CO2 line's bad-sample test predates decision 186

*Raised 2026-11-12, session 105 (As-Built §CXV.2); drafted as B-134, filed here as the rewrite's own.*
`test_a_bad_sample_costs_one_tick_of_control_action_and_nothing_else`
(`tests/equivalence/test_co2_line_equivalence.py`) asserts that after one bad sample PIC-322203 is, to the bit,
the loop that never saw it. Decision 186 (session 99, B-130 (b)) made `ProcessLoop` reseed its PV history on the
first good sample, which drops one tick's proportional step by design: the two traces part by Kc times the PV's
move through the outage, 1.0 x 1.0 bar = 1.0 % of stroke, on the tick after the frozen one. The test fails on
commits 0d9736a and 18a7656; the module skips when V1 is absent, so session 99's and 103's suites did not run it.
The process engineer's answer of 2026-11-12 (R1): not decided; the test stays failing and logged. Acceptance:
the test asserts decision 186's behaviour (frozen for the bad tick, the integral alone on the next, then the clean
loop's increments), and its V1 sibling still asserts V1's kick. Options: (a) restate the test as decision 186's,
a test change only; (b) reopen decision 186. Next step: the process engineer's choice.

### A-38 — Sixteen modules are tested only through the plant

*Raised 2026-11-11, session 99 (As-Built §CX.6; A-35's reconciliation).* No test imports or names
`engine.plant.absorption`, `engine.plant.boundary`, `hmi.trend.plot`, `hmi.widgets.bargraph`,
`hmi.widgets.icon_geometry`, `hmi.widgets.icons`, `thermo.activity`, `thermo.henry`, `thermo.kvalues`,
`thermo.speciation`, `thermo.splits`, `thermo.srk`, `thermo.standard_state`, `thermo.vle_grid`,
`units.synthesis.hp_split` or `units.synthesis.reactor_calibration`; six more are reached only by V1 equivalence
suites (§CX.6). To do: a behaviour test of each, the thermo ones on the stores' own fixed points.

### A-41 — Eight pump pairs hold no run state; their icons open no faceplate

*Raised 2026-11-13, session 106; rewritten session 109 (As-Built §CXX.3, §CXX.5, §CXIX.1-2).* Instructed: every
pump icon opens START / STOP, simulating the pump's field start and stop. Built (decision 222): the five pairs
with a run state. Open: 323P003, 323P008, 328P002, 328P006, 328P007, 329P003, 335P001 and 335P002. Established:
each pair's service and the flow its STOP must stop (§CXX.5); AC4's MOTCON sheets on the images (§CXIX.2): no
process interlock on 323P003 and 329P003, a low level (L2) on five, the trips on 335P002; only LT-323503's L2 is
in hand, the others not searched beyond AC4. Acceptance: both machines stopped, the pair's flow is zero on the
engine; the seed unmoved; the icon opens the faceplate. Next step: session 111
(`D:\Work\reports\Session 111 plan prompt s109.md`), one pair at a time; a stop only on a sourced limit.

---

# Section B — Physics gaps inherited from V1

### B-118 — Below 100 % load the engine holds no steady state on the plant's reactor window

*Raised 2026-10-30, session 76. Phase 7. Record: As-Built Parts LXXXIX to XCVIII, C, CIII to CVII,
CX to CXV and CXVII to CXIX; decisions 177, 180, 181, 188 and 190.*

**Problem.** The plant runs for hours at reduced load. The committed engine, ramped from its design
seed, does not, on every operating policy tried:

* 70 to 85 %: trip 22.1 within 20 to 80 minutes (322E003's sump floods, or it vents and TT-322015
  passes 110 C), or, with 22.2 removed (decision 189), SV32064 lifts and 21.2, 21.8, 21.10 and 22.1 latch
  (§CXV.12); where none fires, 322R001 collapses (TT-322005 158-172 C).
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
Decision 190 adds the procedure's criteria (a)-(d) and (f); decision 196 fails a hold on a relief's lift.

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
* The procedure (§CXV.14): L1, L6, L3 (bundle A) and L2's raise (for TT-322005) are needed; L12's need is
  shown by the engine; L3 is not fulfilled (B-136); L6 acts in the procedure's sense and L2's one-sided
  response is B-125's edge (§CXVII.4, correcting §CXV.4); (e) is met on no engine; the L2 board loop as approved
  fails (§CXV.7); the seed carries the 2 700-3 000 s mode.
* The holdup bundle (scratch). Its cold branch at 92.3 % follows 322E001's `g_hc` (§CXV.6a). Its holds at 74.4
  and 69.3 % rest on 322E001's feed-deficit rise (off: TT-322004 follows the plant, all five holds lost,
  §CXVII.6), and the 69.3 % one boils on the bubble point, off the plant on TT-322004, PT-329201, AT-322701 and
  the steam (§CXVII.2). The loss needs neither 322E002's live law, the conversion's residence time, its slip nor
  its movement (§CXVII.9). 322R001 sits at 60 % of its equilibrium by V1's `X_INF`; the licensor gives 95 % (§CXVII.8).
* 322R001's loop path by path, rise off (scratch, §CXVIII.6-11). Alone, 322E002's edge (PV) or V1's re-flash of the
  off-gas at the live pressure (ZP) loses 92.3 and 69.3 %; the conversion and its slip amplify (1.0 K per K). With
  the three pinned the top stands on its bubble point at 92.3 %, as the seed's, and boils at 69.3 %: 0.53 K a bar of
  the engine's shallow pressure fall (§CXVIII.8). The 95 % re-anchor halves the 92.3 % loss; its seed drifts.
* Session 109 on those runs (§CXIX.6): 322E002's flash target swings 0.16-0.27 inside 1 K and 1.3 bar. Desk, to be
  redone by session 112 (§CXIX.7): Book2's pressure falls about 6 bar at 69.3 % beyond its thermowells' fall.

**Bundle A (decision 181), scratch only; `ureasim/` is as built.** P1, 322E002's UA on the battery-limit
CO2 demand ratio to the power 0.77 (§CVII.1); P4, the wall loss on a stagnant reactor only; the 322F001 lift
p_disch,eff = p_disch - 2.41 (1 - r^2) (decision 180); `unit_322e001.SLIP_GAIN` 4.0.

**The holds (§CXII.10, §CXIV.6).** Bundle A passes 92.3 % and latches or leaves the band below it; with B-126
(b)'s holdup the low holds are trip-free and 92.3 and 90.5 % latch on the cold branch; 111 % is out of band on both.

**Next step.** Session 112 (`D:\Work\reports\Session 112 plan prompt s109.md`), scratch: S (B-125 (c)); B, the
re-flash on the top's subcooling, clamp (b)'s live form (§CXIX.8); both; "stands" scored on the column's rise
(13.05 +/- 1.0 K), not the boil-off. Then the process engineer's choice, §CXVIII.12's (a) to (d). B-126, B-135, B-136 held.

**B-120 folded in (decisions 177, 181).** V1's stripper slip gain drives a loop mode: gain 0 removes it
at 92.3 % on the S2 prototype and at 111 % (§XCVIII.3), and alone runs the reactor 12.4 K colder at
92.3 % (§CIII.7). On the holdup bundle gain 0 neither holds 92.3 % nor removes the 111 % mode (§CXIV.7), and
with the feed-deficit rise off it brings the loss forward at 92.3 and 69.3 % (§CXVII.6). The gain stays 4.0.

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
identical on the engine's anchor and not on its default (P_bub +0.146 bar). Alone, E1eu leaves the as-built cold
branch as it is (§CXII.7); on B-126's holdup it changes no hold scored (§CXIV.3, §CXIV.6). Step L2's one-sided
response is this edge (§CXVII.4). Session 108 (§CXVIII.11), rise off: on bundle A's P1 the edge alone loses
322R001 at 92.3 and 69.3 %; its UA on its own feed sooner; its split on Book2's departures boils 1.4 t/h at
92.3 %. Session 109 (§CXIX.6, §CXIX.8): the split is ill-conditioned at every load. Options: (a) keep as built;
(b) E1eu, on a seed criterion the process engineer restates; (c) S, the split from the duty with the outlet on
the melt's bubble line, defined and not measured. Next step: session 112 measures (c).

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
(H5) close the loop's atoms to 7e-6 of the N in. Its cold branch at 92.3 % (§CXV.6, §CXV.6a): 322R001's feed
reaches H2O / CO2 0.52, 322E001's `g_hc` falls to 0.82, the gas CO2 to 322R001 peaks at 832 kmol/h and falls by
two thirds, and TT-322005 follows; PIC-329204 at its seed or a halved ramp move the latch by 6 min. Its low holds
rest on 322E001's feed-deficit rise and the 69.3 % one boils (§CXVII.2, §CXVII.6): not a build candidate as
measured. Options: (a) keep as built; (b) the bundle with the change that holds 322R001 (B-118), a seed criterion
restated first; (c) C2's second half (the holdup re-seeded at the ramp's end); (d) the loop's other holdups.

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

### B-133 — L10 has no handle: the ammonia water to 322C001 is not controlled

*Raised 2026-11-12, session 105 (As-Built §CXV.3; decision 194).* The procedure's step L10 lowers the ammonia
water to the LP absorber, watched on FT-322402. FT-322402 reads 322P002's draw to 322C001 (the console's stream
755, design 31.3 m3/h); 322P002's delivery has no control valve and P&ID 102 draws FI-322402 only (decision 81).
Neither the console nor the plant's DCS gives the operator a move on it, and Book2 holds it at 30.9 m3/h from 92
to 111 % load. Acceptance: the process engineer names the plant's handle for the step (a field valve, 322P002's
recycle, or none) from the plant, its document cited; the console then carries the plant's handle and nothing
else. Options: (a) keep as built, L10 reported as no move; (b) the plant's handle modelled once its document is
found. Searched (§CXVIII.5, §CXIX.5): neither P&ID 102 nor the pumps' own sheet (UD-VT-328-FB-0003) draws a control
or remote valve; each discharge has a check valve and a manual valve. Next step: the process engineer's answer.

### B-135 — The CO2 line's relief lifts before the loop's

*Raised 2026-11-13, session 105 (As-Built §CXV.12; the process engineer's R3: an item with options, nothing
built).* With trip 22.2 removed (decision 189) the first relief to lift on the synthesis side is SV32064 on the
CO2 discharge line (set 161.013 bar a, Uhde UD-RL-320-EC-0003), not SV32251 / SV32252 (160.013 bar a), which the
plant's documents name as the loop's limit (§CXV.1). The boundary feed (decision 73) delivers the demand at
whatever pressure the line presents, and the line stands 1.6 to 2.9 bar above the loop, so it reaches its
relief's set while the loop is 0.6 to 1.9 bar under SV32251's. Established: the cold start lifts SV32064 at
3 426.6 s with XV-322902 open (1 608 kg in 103 s), FY-322403 falls under trip 21.2's limit and 21.2, 21.8 and
21.10 latch at 3 525.5 s; bundle A at 74.4 % lifts it at 4 833.7 s and latches the same three 3.9 s later, as the
line falls onto the loop's pressure and the CO2 flow stops, and 22.1 0.1 s after them. It is not B-88's symptom (no trip latched, XV-322902 open). Decision 196 fails a hold on it. The order is the design's: sets 1 bar apart, the line 2.9 bar above the reactor top on the licensor's table (§CXVII.4). Acceptance:
the process engineer names what bounds the CO2 discharge on the plant when the loop stands at 158-160 bar a, from a
plant document or a trend. Options: (a) keep as built, SV32064 the first relief, reported; (b) the line's drop at
reduced loop pressure checked against 320K002's datasheet and the 5 November trends, and SV32064's set against its
datasheet; (c) a discharge-pressure bound on the boundary feed, which decision 73 excludes unless the process
engineer reopens it. Found (§CXVIII.5, §CXIX.5): 320K002's data sheet runs a 70 % turndown case at 148.0 bar a and
rates the HP casing at 175 bar g, no discharge limit; SV32064's sheet is the one cited. Next step: the process engineer's.

### B-136 — Step L3 is not fulfilled: 322E001's bottoms run hot at reduced load

*Raised 2026-11-13, session 105 (As-Built §CXV.11; decision 190).* L3 lowers the stripper's steam to prevent the
hydrolysis of urea and the loss of pressure in the recirculation section. On every engine TT-322004 rises with the
load cut, 9-12 K at 90-92 % and 20-25 K at 69-74 %, where the plant's falls 1.4 K at 94.2 % and 5.7 K at 69.3 %
(§C.2, §CXVII.4). Established: 322E001 hydrolyses 1.9-2.4 times the seed's urea at 90-92 % and 5.3-7.1 times at
the low holds; biuret 0.8-1.4 wt %; 323D001 at 2.5-2.9 bar a against 3.20 with PIC-323202 and PIC-323203 shut. The
term is V1's feed-deficit rise (§XCVI.2): the unit alone gives 201 C at the plant's 69.3 % against 162 C, and V1's
0.7 K/K on the steam is the plant's (§CXVII.3). Option (b) measured on the holdup bundle (§CXVII.6): rise off,
TT-322004 falls 1.5 K at 92.4 % and 5.5 K at 69.6 %, the hydrolysis stays at 1.0-1.4 times the seed's per unit
load, and all five holds are lost. Acceptance: the plant's TT-322004, the hydrolysis per tonne at the seed's or
below, 323D001 at its set point, the 100 % pin to the bit. Options: (a) keep as built, L3 reported as not
fulfilled; (b) the rise off with the change that holds 322R001 (B-118), never alone. Next step: B-118's.

### B-137 — The melt header's pressure is a boundary constant; the header valves are not modelled

*Raised 2026-11-13, session 106; rewritten session 109 (As-Built §CXVI.4-5, §CXX.4, §CXIX.3-4).* PIC-335201 is
V1's 3.5 bar g constant; the melt goes whole to LV-324501A, or to B above 3.8 bar g. Instructed (I-3; 2026-11-14):
a GRANULATION faceplate steps the twelve header valves; the header runs at 3.2 to 3.8 bar g with the headers
following the load and 323D002's small compartment level constant; above 3.8 bar g LV-324501B returns the excess
to 323D002. Established: the rule is AC4 PC35.2 as configured, X setting LV-324501B (X 50-100) and PIC-335201's
set point 2.8 + min(X / 50, 1) (§CXX.4, §CXIX.3); N valves hold the band at loads of N / 10 x 95.6-104.2 %;
PIC-335201 read inside the header solve settles, a tick late it rings, V1's selector relays (§CXX.4); HV-335602
drains to 335D004, outside the plant (§CXIX.4). Acceptance: ten valves reproduce the seed but LIC-324501.op
(75.3 -> 35.0); nine ride the 3.8 bar g ceiling, LV-324501B returning the excess; the unit alone holds 3.5 bar g
at 70 to 120 % on 7 to 12 valves. Open after the build: trips 35.1 and 35.4, 335P001's impeller. Next step: session 111.

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
