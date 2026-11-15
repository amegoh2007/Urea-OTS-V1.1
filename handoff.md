# handoff.md — Open Issues for the Human Engineer

Tracker for `Urea Simulator V1.1`. It holds **open** items only, each as its **current state**: the
problem, its acceptance tests, what is established, the open options, the next step. A session rewrites
an item's state in place and appends no session paragraph (`CLAUDE.md` §3a). Close an item by deleting it;
its closure is recorded in the session's As-Built Part. Ceiling: 300 lines.

**Last updated:** 2026-11-15, session 118.

**Section A** — issues created by the V1.1 rewrite.
**Section B** — physics gaps inherited from V1 that the rewrite carries forward. Port V1's behaviour
exactly, including the compromise, and keep the item open here.
**Section C** — calibration deferrals: the port reproduces V1 knowingly and the correction waits on the
process engineer's decision.

History, frozen: `docs/history/handoff-record-to-session-95.md` holds the closure schedule, the closed
items' summaries, B-118's chronicle (sessions 76 to 95) and every data-gap row's full search record.

---

# Section A — Rewrite issues

A-38 was raised by session 99 (§CX.6); A-40 by session 105 (§CXV.2); A-50 by session 113 (Part CXXIII).

### A-40 — The CO2 line's bad-sample test predates decision 186

*Raised 2026-11-12, session 105 (As-Built §CXV.2).* `test_a_bad_sample_costs_one_tick_of_control_action_and_nothing_else`
(`tests/equivalence/test_co2_line_equivalence.py`) asserts that after one bad sample PIC-322203 is, to the bit, the loop
that never saw it. Decision 186 made `ProcessLoop` reseed its PV history on the first good sample, which drops one
tick's proportional step by design (1.0 % of stroke on the tick after the frozen one). It is the suite's one failure on
HEAD (§CXXIII.1). The process engineer's answer of 2026-11-12: not decided, the test stays failing. Options: (a) restate
the test as decision 186's (frozen for the bad tick, the integral alone on the next, then the clean loop's increments;
its V1 sibling still asserts V1's kick), a test change only; (b) reopen decision 186. Next step: the process engineer's.

### A-38 — Five run flags have no unit test

*Raised 2026-11-11, session 99 (As-Built §CX.6); widened session 113 (§CXXIII.2); the sixteen modules tested in
session 117 (§CXXVII.3).* Decision 227's `pump_running` in `first_desorber`, `reflux_drum`, `second_desorber`,
`flash_condenser` and `solution_tank` is named by no unit test (the engine's tests reach it). To do: a behaviour
test of each (session 115's Track C).

### A-41 — Four pump pairs' low-level stops are not built; 328P007's service contradicts P&ID 104

*Raised 2026-11-13, session 106; rewritten sessions 111 and 113 (As-Built §CXXI.8, §CXIX.2, §CXXIII.4; decision
227).* Built: the eight pairs hold a run state, their icons open START / STOP, both machines stopped stop the pair's
flow, a swap moves nothing; 323P008 keeps its stop on LT-323503's L2. Open: (1) AC4 stops 328P002, 328P006, 328P007
and 335P001 when LT-328501, LT-328503, LT-328505 and LY-324501 fall below L2; no L2 value is in either archive, so no
stop is built (data gap 8; for 335P001, B-146). (2) 328P007's service: P&ID 104, the PFD (739 to 741 all at 3.9 bar a)
and the pumps' data sheet (25 m3/h, "to the granulation unit") take 740 to LV-328505 and 741 to FV-328406 on 328C004's
pressure, past the pumps' suction; decision 227 stops LV-328505's flow with the pair, after `Mapping of Desorber
Hydrolyzer unit.md`. Options for (2): (a) as built; (b) as the P&ID draws it, the pair moving no modelled stream. Next
step: the DCS readback for (1); the process engineer's line for (2) (session 115's prompt, D1).

### A-50 — The synthesis loop's azeotrope test pins a value on a tick-to-tick ring

*Raised 2026-11-15, session 113 (As-Built §CXXIII.2).* The azeotrope test of `test_synthesis_loop_decided_equivalence.py`
pins 322E002's condensation at tick 1 000, where it falls 100 to 15 t/h in two seconds and alternates tick to tick;
decision 224's 3 kg/h moved it 14 t/h, decisions 236 and 237 6.8 t/h more (§CXXVI.5); it has been re-pinned six times.
Acceptance: B-106's divergence asserted on statistics both trees agree on; tick 50's pins kept. A test change only.

---

# Section B — Physics gaps inherited from V1

### B-118 — Below 100 % load the engine holds no steady state on the plant's reactor window

*Raised 2026-10-30, session 76. Phase 7. Record: As-Built Parts LXXXIX to XCVIII, C, CIII to CVII,
CX to CXV, CXVII to CXIX and CXXII; decisions 177, 180, 181, 188 and 190.*

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

Licensor's windows (Operating Manual III §5.2): N/C 2.90-3.10, TT-322005 180-183 C, PT-329201 136-143 bar. A-34's atoms
close tick by tick on a turndown (`tests/phase7/test_loop_atoms.py`, §CX.1). Decision 190 adds the procedure's criteria (a)-(d) and (f); decision 196 fails a hold on a relief's lift.

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
* The procedure (§CXV.14): L1, L6, L3 (bundle A) and L2's raise are needed, L12's shown by the engine; L3 is not
  fulfilled (B-136); L2's one-sided response is B-125's edge (§CXVII.4, correcting §CXV.4); (e) is met on no engine;
  the L2 board loop as approved fails (§CXV.7); the seed carries the 2 700-3 000 s mode.
* The holdup bundle (scratch). Its cold branch at 92.3 % follows 322E001's `g_hc` (§CXV.6a). Its holds at 74.4
  and 69.3 % rest on 322E001's feed-deficit rise (off: TT-322004 follows the plant, all five holds lost,
  §CXVII.6), and the 69.3 % one boils on the bubble point, off the plant on TT-322004, PT-329201, AT-322701 and
  the steam (§CXVII.2). The loss needs neither 322E002's live law, the conversion's residence time, its slip nor
  its movement (§CXVII.9). 322R001 sits at 60 % of its equilibrium by V1's `X_INF`; the licensor gives 95 % (§CXVII.8).
* 322R001's loop path by path, rise off (§CXVIII.6-11): alone, 322E002's edge (PV) or V1's re-flash at the live
  pressure (ZP) loses 92.3 and 69.3 %, the conversion and its slip amplifying 1.0 K per K; the three pinned, the top
  stands on its bubble point at 92.3 % and boils at 69.3 % (§CXVIII.8). The 95 % re-anchor halves the 92.3 % loss.
* Session 109 (§CXIX.6): 322E002's flash target swings 0.16-0.27 inside 1 K and 1.3 bar. Book2's pressure falls about
  6 bar at 69.3 % beyond its thermowells' (desk); the licensor's bubble point follows the system pressure, the synthesis
  pressure less the inerts (8.5 bar at the design), which the engine's cap does not subtract (§CXXIII.5).
* Session 112 (Part CXXII, re-read in §CXXIII.3); D1: decisions 180 and 196, the rise in 13.05 +/- 1.0 K. B lifts the
  rise and is seed-neutral; S alone moves neither the rise nor the latch and drifts 0.20 K on the seed. Z + B stands D1
  at 92.3 % (13.15 K). S + B on UA as built at 92.3 % rings (period 2 300-2 400 s, decaying; TT-322005 181.7 C and
  rising at the end, every sign the plant's): not settled, no verdict. At 69.3 % the result turns on 322E002's UA
  exponent (as built the top cools to 173.9 C; P1 rises 39-45 K); Z + B with the lean rise on stands but boils 1.8 t/h.

**Bundle A (decision 181), scratch only; `ureasim/` is as built.** P1, 322E002's UA on the battery-limit
CO2 demand ratio to the power 0.77 (§CVII.1); P4, the wall loss on a stagnant reactor only; the 322F001 lift
p_disch,eff = p_disch - 2.41 (1 - r^2) (decision 180); `unit_322e001.SLIP_GAIN` 4.0. **Holds** (§CXII.10,
§CXIV.6): bundle A passes 92.3 % and latches or leaves the band below it; with B-126 (b)'s holdup the low holds are
trip-free and 92.3 and 90.5 % latch on the cold branch; 111 % is out of band on both.

**Next step.** Session 114 (`D:\Work\reports\Session 114 plan prompt s113.md`), scratch: the desk tracks, S on design-
point references, S + B at 92.3 % to its settled state, the UA exponent from Book2, the pressure as a clamp, then 69.3 %
and the other holds. Then the process engineer's choice. B-126, B-135 and B-136 held.

**B-120 folded in (decisions 177, 181).** V1's stripper slip gain drives a loop mode: gain 0 removes it at 92.3 %
on S2 and at 111 % (§XCVIII.3), runs the reactor 12.4 K colder at 92.3 % (§CIII.7), holds nothing on the holdup
bundle (§CXIV.7) and, rise off, brings the loss forward (§CXVII.6). The gain stays 4.0.

### B-125 — 322E002's saturation law has no margin at the design and contradicts Book2

*Raised 2026-11-11, session 97 (§CVIII.4). Decisions 97 and 135's law.* `saturation_fraction` loses 1.54 %
of all condensation per bar its deficit stands above zero, and the deficit is zero at the design. As
built it gives 0.857 at Book2's 92.3 % band and 0.798 at 69.3 %, where the plant condenses fully (the melt
N/C taken as AY-322701 + 0.2, an inference). The outlet temperature is an NTU quench of a 350 K spike.
Established: the deficit is +6.4 to +11.2 bar at Book2's five bands (§CX.8); on the 74.4 % ramp the K_N line is
the whole deficit through the N/C hump and makes the fraction's dip, not the hump (§CXI.2, §CXII.7). E1eu, Extended
UNIQUAC's shape on both sides, needs a 4.38 bar margin set by the 69.3 % band; it holds the fraction at 1 on the seed
and through the hump, does not initiate B-118's collapse, is not bit-identical on the seed (§CXII.2-3), and changes
no hold scored alone or on B-126's holdup (§CXII.7, §CXIV.3, §CXIV.6). Step L2's one-sided response is this edge
(§CXVII.4). Rise off (§CXVIII.11): on P1 the edge alone loses 322R001 at 92.3 and 69.3 %, its UA on its own feed
sooner, its split on Book2's departures boils 1.4 t/h at 92.3 %; the split is ill-conditioned at every load
(§CXIX.6, §CXIX.8). S, the split from the duty with the outlet on the melt's bubble line (§CXXII.3, §CXXII.6): alone
it moves neither the rise nor the latch at 92.3 or 69.3 %, on UA as built or P1 (on P1 at 69.3 % the top boils 9-11
t/h); with B-118's B on UA as built and 322E001's lean rise on it stands at 92.3 % (13.24 K). Options: (a) keep as
built; (b) E1eu, on a seed criterion the process engineer restates; (c) S with B (B-118). Next step: B-118's.

### B-126 — 322R001's 136 t of liquor has no composition

*Raised 2026-11-11, session 97 (§CVIII.5).* `reactor_inventory.py:328-329` sends on the tick's reaction product scaled
to the hydraulic outflow: 305 s after a 20 % CO2 cut the overflow carries 2 933 kmol/h more N and 576 more C than the
reaction produced (§CXII.9, §CXIII.2). The loop's 153 t of liquor holds no species (§CXIII.3). Measured in scratch (Part
CXIV): (b), the holdup's species in twelve compartments, closes to 6e-14 kmol a tick; the 74.4 % hump falls 3.649 to
3.197, the latch goes at 74.4, 69.3 and 68.9 %, and 92.3 and 90.5 % fall onto the cold branch (322E001's `g_hc`,
§CXV.6a); 849 seed leaves differ. Its low holds rest on 322E001's feed-deficit rise and the 69.3 % one boils
(§CXVII.2, §CXVII.6): not a build candidate as measured. Options: (a) keep as built; (b) the bundle with the change that
holds 322R001 (B-118), a seed criterion restated first; (c) C2's second half; (d) the loop's other holdups (H5).

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
latch by -250 s; the floor does not decide B-118 on this trim. Row 116's re-pin is the same basis (B-127); checklist row 15 asks the faceplate's limits and basis.

### B-133 — L10 has no handle: the ammonia water to 322C001 is not controlled

*Raised 2026-11-12, session 105 (As-Built §CXV.3; decision 194).* The procedure's step L10 lowers the ammonia
water to the LP absorber, watched on FT-322402. FT-322402 reads 322P002's draw to 322C001 (the console's stream
755, design 31.3 m3/h); 322P002's delivery has no control valve and P&ID 102 draws FI-322402 only (decision 81).
Neither the console nor the plant's DCS gives the operator a move on it, and Book2 holds it at 30.9 m3/h from 92
to 111 % load. Acceptance: the process engineer names the plant's handle for the step (a field valve, 322P002's
recycle, or none) from the plant, its document cited; the console then carries the plant's handle and nothing
else. Options: (a) keep as built, L10 reported as no move; (b) the plant's handle modelled once its document is
found. Searched (§CXVIII.5, §CXIX.5): neither P&ID 102 nor the pumps' own sheet (UD-VT-328-FB-0003) draws a control
or remote valve; each discharge has a check valve and a manual valve. Established (§CXXVIII.4): Operating Manual
III sets 322P002's flow by hand, "adjusted through FI322402" (p. 1-58), and gives 15, 30 and 31.3 m3/h via
FI-322402 at start-up (pp. 4-8, 4-14, 4-19); it names no controller or control valve, so the plant's handle is a
field hand valve on 322P002's delivery, read on FI-322402. Next step: the process engineer's choice of (a) or (b).

### B-135 — The CO2 line's relief lifts before the loop's

*Raised 2026-11-13, session 105 (As-Built §CXV.12; the process engineer's R3: options, nothing built).* With trip
22.2 removed (decision 189) the first relief to lift on the synthesis side is SV32064 on the CO2 discharge line (set
161.013 bar a, UD-RL-320-EC-0003), not SV32251 / SV32252 (160.013 bar a), the loop's limit in the plant's documents
(§CXV.1): the boundary feed (decision 73) delivers at whatever pressure the line presents, 1.6 to 2.9 bar above the
loop. The cold start lifts it at 3 426.6 s and latches 21.2, 21.8 and 21.10 at 3 525.5 s; bundle A at 74.4 % at
4 833.7 s, 22.1 0.1 s after. Not B-88's symptom; decision 196 fails a hold on it; the sets 1 bar apart are the
design's (§CXVII.4). 320K002's sheet runs a 70 % case at 148.0 bar a, no discharge limit (§CXIX.5). Acceptance: the
process engineer names what bounds the CO2 discharge at a loop of 158-160 bar a. Options: (a) keep as built; (b) the
line's drop checked against 320K002's datasheet and the 5 November trends; (c) a discharge bound, which decision 73
excludes unless reopened. Next step: the process engineer's.

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

### B-145 — LV-324501B relays at its seat on a small excess

*Raised 2026-11-14, session 111 (As-Built §CXXI.4; decisions 150 and 224).* Decision 150's 2 % trim floor on
LV-324501B is 6.6 % of PFD 402; one header valve fewer than the load asks leaves 6.2 % at a fixed feed, and
unit-alone the valve relays at its seat (1 218 flips in 1 000 s). On the engine at 9 valves and 100 % the recycle
raises the feed past the floor; a save at 90 % on 8 valves relayed (decision 226 now loads it on 9). Asked with it:
PIC-335201 runs decision 93's deadzone 0, not the tuning table's 2 %, which parks the header within 0.08 bar of E1.
Acceptance: no relay on any header and load the console reaches. Options: (a) keep as built; (b) LV-324501B's
floor read from its sizing sheet (decision 150's class reviewed). Established (§CXXVIII.3): (b) gives the floor
built. Decision 150 runs LV-324501B on its sheet's equal percent and the 50:1 the sheet prints (Pos. 149,
"50.0-1"); 1/50 is the 2 % floor, and the sheet's smallest case is 8 % stroke at Kv 2.599 of Kvs 100. Next step:
the process engineer's: (a), which (b) now equals, and PIC-335201's deadzone.

### B-146 — 324F003 has no low-level protection; trips 35.1 and 35.4 are not built

*Raised 2026-11-14, session 111 (As-Built §CXXI.4, §CXXI.8, §CXXIII.6; decision 224).* At E1's 2.8 bar g floor the
header valves still pass 89 % of their design share: AC4's header cannot shut stage 2's drain when its feed fails. AC4
stops 335P001A and B on LY-324501 below L2 (§CXIX.2; no L2 in hand). Trips 35.1, 35.3 and 35.4 (UAN 01-3042 sheets
335/1+, 335/2+) clamp LV-324501A and B, open HV-335602 and stop 335P002; the initiators the engine holds are both
335P001 stopped, both 335P002 stopped (10 min) and LV-324501A not open (§CXXIII.6). None is built. On a lost feed, a
feed-pump trip, 12 valves at 100 % or HV-335602 open, stage 2 drains to its heel. Options: (a) keep as built; (b) the
trips on the run states now (session 115's Track B), the L2 stop at the readback (checklist row 20).

### B-156 — Seven level transmitters read V1's holdup ratio, not their taps

*Raised 2026-11-15, session 118 (As-Built §CXXVIII.5).* Uhde's data sheets (UD-MR-G00-EC-0133, EC-0134) print every
level transmitter's nozzle distance. Six modelled levels read between their taps on those distances
(`tests/data/test_level_transmitter_sheets.py`). Seven still read V1's holdup ratio: LT-323501 (323C003, 2 000 mm),
LT-323502 (323D001, 1 910 mm), LT-323503 (323D011, 1 310 mm), LT-328503 (328C002, 1 200 mm), LT-328504 (328C003, 1
000 mm), LT-328505 (328C004, 1 000 mm) and LT-329501 (322E003's sump, 10 000 mm). Acceptance: each reads between its
sheet's nozzles on its vessel's datasheet geometry, its design level reproduced, or the process engineer keeps V1's
ratio for it. Established: the set ranges are 0.99 to 1.08 times the head over the nozzle distance (93 to 101 % at
the upper nozzle); LT-329504 and LT-329505 are set at 100 mbar per metre, 1.11 times; LT-329502's 92 mbar is 0.742
times, its range ending 1.113 m above the lower nozzle of the modelled 1.500 m. Decision 33's class reached 323F004
only after the process engineer chose it with both sides measured (decision 138). Options: (a) the class applied unit
by unit, each measured on both sides first; (b) V1's ratio kept. Next step: the process engineer's direction.

---

# Section C — Calibration Deferrals

*None open.*

---

# Open data gaps

*`Claude.md` §4: a datum that `References\`, the vendor archive and the V1 source all fail to supply. The ledger was accepted by the process engineer on 2026-10-16 (decision 128); each row keeps its stand-in as built; every row's full search record is in `docs/history/handoff-record-to-session-95.md` (grep the tag before the archive is searched again).
Rows 2, 4, 5, 8, 9 and 10 close on one plant DCS readback session (`D:\Work\reports\DCS readback checklist.md`); rows 1 and 3 on Körting's curves, row 11 on KSB's sheet, row 12 on the SRI986 positioner's response data or a plant step test. The checklist's row 14, TV-323013B's flow and differential, is decision 178's cross-check and no ledger row.*

| # | Datum | Needed by | As built | Found so far | Route to close |
|---|---|---|---|---|---|
| 1 | 322F001's nozzle and mixing-throat geometry, loss coefficients and performance diagrams | `control/jet_pump.py`, `data/unit_322f001.py` | both areas back-solved from the licensor's design duty on open-literature loss coefficients; the design point exact, the stall margin not (B-12's 90.7 %, §LXXI.3); the lift a fixed 4.2 bar | no vendor geometry or curve in either archive (§LIX.4). The plant keeps the entrainment ratio from 69 to 102 % load, mu / mu_ref 1.031 +/- 0.044, n 15; the as-built closure stalls on that line at 69.9-80.7 %; a friction share of at least 2.41 bar of the lift passes it, a fit (§CV.3-4). Book2's points: LT-329501 11 % at HV-322602 40 % (69.3 %), 1 % at 54 % (80.4 %). LT-329501 is not in the 5 November trends, so the level term is unfitted; session 99 (§CX.9): the friction share needed is 0-2.41 bar over the 15 windows, and no level law fits Book2's four points (V1's passes 1-23 % of the plant's suction there) | Körting's 14 diagrams, order 2/131/4/04219 (draft request: `D:\Work\reports\Koerting request draft s99.md`). The lift prototype is held with B-118 (decision 180) |
| 2 | TT-322015's H2 hysteresis | I 22.1's release (B-56) | H2 110 C (the DCS readback, decision 103); hysteresis V1's 2 K, cleared below 108 C | the object display shows range 0-200 C, H1 100.0, H2 110.0, delay 0 and no hysteresis field (photograph of 24 October 2026); the archive holds no set-point or alarm list (§CXXVIII.1) | checklist row 1: the engineering view of the limit; else the 2 K stand-in signed off |
| 3 | Körting's performance curves of 324F002, 324F004 and 324F005 | `ejector_map`, B-57's interpolation on the synthesized maps (§XLIX.4, §L.1) | synthesized maps, anchored on the PFD's design loads; in-situ factors 0.919, 0.336, 0.497 | one duty point an ejector; no curve in the archive (§XLVIII.2). The plant's motive break-off, the datum a curve must meet: HIC-329605 between 55 and 64 % (HIC-329606 38-40 %) at PT-329207 4.20-4.24 bar g, 5 November 2026 13:11-13:16, 75 % load; the engine's vacuum still holds there (§CV.5) | Körting, orders 2/115/4/09674 and 2/232/4/00503 (the same draft); checklist row 13: 324E002's and 324E005's cold-end and cooling-water temperatures for 5 November 13:00-13:30 |
| 4 | LT-324501's taps | LI-324501 between its taps (decision 33's class) | V1's holdup ratio (§L.4) | one 80 mm instrument on the barometric leg at EL +8495 (isometric UD-RL-100-MB-0180, item 22); no second connection drawn; the span cannot be weighed from the trends (§CV.7). Uhde's data sheet UD-MR-G00-EC-0136 p. 3: set range -700 to 900 mbar on 1 220 kg/m3, nozzle distance blank, an HP-side flanged seal and no LP-side connection (§CXXVII.5). Its level, like row 10's, is a holdup ratio on no vessel geometry (§CXXVIII.5) | checklist row 11: LRV, URV and the reference connection; a walk-down |
| 5 | AC4 PC21's limits and elements: FY-322403's L2; PT-321211 / 221's L2; ST-321952 / 953's H2; the T elements' mode; the SR flip-flops' dominance; TRIP_84_8_FLAG1's L2 | trips 21.2, 21.8 and 21.10 (§LXV.6) | FY-322403's L2 V1's 5 %; PDY's L2 0.1 bar; the T elements on-delays; reset dominant; PT-321211 / 221, ST-321952 / 953 and TRIP_84_8 taken healthy | the limits are database entries; the scan does not resolve the timer symbol (UD-MR-G00-FF-0004 pages 5, 7, 20); TRIP_84_8 is the instrument air, two of PT-384207A / B / C below L2 (§LXXIII.2); no set-point list in the archive (§CXXVIII.1) | checklist rows 3 to 8, one readback session |
| 8 | LT-323503's L2 hysteresis; the L2 limits of LT-328501, LT-328503, LT-328505 and LY-324501 | 323P008's restart (B-96); the stops of 328P002, 328P006, 328P007 and 335P001 (A-41, B-146) | trip below 5 %, restart at 7 %: the 2 % stand-in of 2026-10-15 (§LXVIII.2); the four other stops not built | the faceplate confirms L2 5.0 %, H1 80.0 %, L1 20.0 %, delay 0 s; no hysteresis shown. The four L2 values are DCS database entries (AC4 MOTCON IC2, §CXIX.2); `References\` and the vendor archive searched in session 111: none; no set-point list in its TOC (§CXXVIII.1) | checklist rows 2 and 17 to 20; else the stand-in signed off |
| 9 | FIC-335405's row in the DCS tuning table | the loop on the plant's tuning (decisions 76, 77) | V1's 100 per t/h and 15 s | not in `References/Master_PID_Tuning_Constants.md`; not photographed; the trends log FT-335405 alone, its ratio to FT-335401 0.0046-0.0050 (§CV.7) | checklist row 9: the faceplate's tuning page, then decision 10's span conversion |
| 10 | LT-329505's tap elevations | LI-329505 between its taps (decision 33's class) | V1's holdup ratio; LV-329505 on Flowserve's trim (§LXVIII.5) | upper tap 324E001 / N5 at EL +15129; lower tap on the DN700 condensate pot at EL +10651 (isometric UD-RL-100-MB-0312): 4 478 mm apart. The loop summary prints 3 000 mm. The conflict is logged, not resolved (§CIII.5). Uhde's data sheet UD-MR-G00-EC-0133 p. 4: nozzle distance 3 000 mm, set range 0 to 300 mbar on 922 kg/m3, so the 4 478 mm would over-range it (§CXXVII.5); the range is 100 mbar per metre of nozzle distance, 1.11 times the head of 922 kg/m3, as LT-329504's is (§CXXVIII.5) | checklist row 10: the transmitter's LRV and URV decide which span its 0-100 % covers |
| 11 | 335P001A / B's impeller and head curve | `units/finishing/melt_header.py`: LV-324501A's inlet moves with the curve's droop | H = 71 - 5 (Q / 80)^2 m, read off the middle of three curves (`data/unit_335.py`) | KSB CPK 80-250, data sheet UD-AU-335-EC-0039: shut-off about 71 m, duty about 80 m3/h at 65 m; the impeller legend is unreadable on the scan (§CXIX.4). KSB's installation plan UD-AU-335-DZ-0026-001 (CPK-CHXYD 80-250): 82 m3/h at 65.2 m, 7.2 bar, 1221 kg/m3, 140 C; the law gives 65.75 m there. The parts list (-004, sheet 2) lists two impellers, 230 "260/115/17" and 230.02 "242-P03-250-D", not decoded (§CXXVII.4). No performance test in the archive: DZ-0026-007 is KSB's test description with no result, DZ-0007-049 is fan 335K007's (§CXXVIII.2) | a legible copy of the sheet, or the pump's nameplate |
| 12 | LV-324501A's positioner response: its stroking time or time constant | `units/finishing/melt_header.py`: the header's step on a header valve (decision 236) | a first-order lag, tau 1 s (`data/unit_335.LV_324501A_TAU_S`), the process engineer's stand-in of 2026-11-15, the better of 1 and 2 s on the 5 November 2026 13:30 steps (§CXXIII.9, §CXXVI.1) | PIC-335201's filter 0.0 s (the tuning table); PT-335201's loop sheet prints no damping; AC4's cycle time is not in the archive; Flowserve (Pos. 148) gives the trip closure, under 3 s, not the positioner's response. The positioner is a Foxboro Eckardt SRI986-BIDS7EAANA-CL (Pos. 148; Uhde's UD-MR-G00-EC-0211); neither gives a response or stroking time (§CXXVIII.3) | the SRI986's response data from Foxboro Eckardt; else a plant step: PIC-335201 in MAN, its output stepped, LV-324501A's stroke feedback trended |