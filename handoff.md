# handoff.md — Open Issues for the Human Engineer

Tracker for `Urea Simulator V1.2` (a copy of V1.1 at commit 5ddc107, decision 251). It holds **open** items only, each as its **current state**: the
problem, its acceptance tests, what is established, the open options, the next step. A session rewrites
an item's state in place and appends no session paragraph (`CLAUDE.md` §3a). Close an item by deleting it;
its closure is recorded in the session's As-Built Part. Ceiling: 300 lines.

**Last updated:** 2026-11-20, session 139.

**Section A** — issues created by the V1.1 rewrite.
**Section B** — physics gaps inherited from V1 that the rewrite carries forward. Port V1's behaviour
exactly, including the compromise, and keep the item open here.
**Section C** — calibration deferrals: the port reproduces V1 knowingly and the correction waits on the
process engineer's decision.

History, frozen: `docs/history/handoff-record-to-session-95.md` holds the closure schedule, the closed
items' summaries, B-118's chronicle (sessions 76 to 95) and every data-gap row's full search record.

---

# Section A — Rewrite issues

### A-61 — 335P001 stops on LY-324501's L2 on every reduced-load hold of the B-118 rig

*Raised 2026-11-19, session 134 (As-Built §CXLVI.11, .19); measured with the operator's rule, session 135
(§CXLVII.1, .2). Decisions 217, 224, 252, 277 and 281; decision 253 taken conditionally on step 2's trace (session 136).* Without the rule the rig's held arms latch PC35's
35.1 and 35.4 when 335P001 stops on LY-324501's 5 % L2: on 2efb181 every arm at 74.4-68.9 % and UA as built at 92.3
and 90.5 %; on the merged tree (79fa8ca) SB693_ldcL at 6 030 s and SB923_luL at 13 660 s (35.4). The plant holds 69 %
for hours with 335P001 running (Book2).
Established cause: the rig holds the ten design header valves online; at LIC-324501's 0 % E1's 2.8 bar g floor still
draws more than the make, so the leg drains (§CXLVI.19).
Acceptance (decision 281): SB693_ldcL252's base with the header and feed rules, 14 400 s at 69.3 %: 335P001 runs to
the end; no PC35 latch; at most one direction change of the header count after the ramp; the count it lands on
reported beside the calculated 6.9-8.1.
Established (§CXLVII.2): with the manual's rule on the rig (a valve off below 3.0 bar g with X at 0 %, on above
3.5 bar g with LV-324501B open; bar g, §CXLVII.1), 335P001 runs every 69.3 % and 92.3 % hold to its end with no
latch, with the rig's 300 s dwell and level guard, and the 100 % seed is unchanged to the bit: the acceptance is
met in scratch. A 900 s dwell is too slow
(SB693_ldcL252 still stopped, 7 020 s); a 300 s dwell with no shedding while LY-324501 rises holds the raw level
above 27 %. At 92.3 % the rule takes one valve off and S + B on UA as built then stands D1 (rise 12.17 K).
Traced (§CXLVIII.3): the 69.3 % feed step (51.0 to 46.5 t/h at 16 610 s) is 323D002 regaining suction (A-62, closed by decision 279), with
no recycle and no shed in the 10 610 s before it; decision 253's condition is met and data gap 16 is closed.
Decision 281's closing run (§CLI.2), the header rule and the feed rule together, 14 400 s at 69.3 %: 335P001 runs
to the end and no PC35 latch fires, but the header count changes direction seven times after the ramp (6 <-> 7 on a
2 400-3 000 s cycle from 14 280 s, on the leg's recycle cycle through LV-324501B); it ends on 7, time-weighted 6.80
(6.44 from 14 280 s), against the calculated 6.9-8.1. Criterion 3 fails; A-61 stays open. The control without the
feed rule (R693b, its 323D002 starved of suction, LIC-323507 at 0 %) moved 10 -> 6 with no reversal; on the ringing
base the header rule alone hunted 6 to 8 with six reversals (§CXLVII.2). So on this pair the feed rule adds the
hunting, against the ruling's premise. The dwell and the guard are the rig's choices, not the manual's.
Next step: the process engineer's reading of §CLI.2 (criterion 3 on the reversals or on the time-weighted count; or
the rule's dwell). The rules are not built into `ureasim/`.

---

# Section B — Physics gaps inherited from V1

### B-118 — Below 100 % load the engine holds no steady state on the plant's reactor window

*Raised 2026-10-30, session 76. Phase 7. Record: As-Built Parts LXXXIX to CLI; decisions 177, 180, 181, 188,
190 and 259 to 282.*

**Problem.** The plant runs for hours at reduced load. The committed engine, ramped from its design seed, does not:
at 70-85 % trip 22.1 in 20-80 minutes, or with 22.2 removed (decision 189) SV32064 lifts and 21.x and 22.1 latch
(§CXV.12), else 322R001 collapses (TT-322005 158-172 C); at 90-95 % a cold branch, TT-322005 168-178 C.

**Acceptance tests (decision 180).** The 100 % design pin held to the bit, and five plant holds on the
plant's own handles, TT-322005 inside Book2's band (+/- 2 K) over the whole hold (decision 269), the rise's
departure within 1.0 K of Book2's (decision 274) and no trip:

| Hold | Source | Plant values |
|---|---|---|
| 92.3 % | `References/DCS Trends/Book2.xlsx`, 755 samples | TT-322005 182.6 C, AY-322701 3.25, PT-329201 137.4 bar, PIC-329204 18.2 bar g, PT-329207 4.11 bar g, TIC-329005 90.0 C, HIC-322604 51.5 %, TT-322002 166.75 C, TT-322004 166.6 C, FY-329403 52.09-55.08 t/h |
| 69.3 %, 3 h | Book2's dwell (As-Built Part C, §CIV.1) | TT-322005 181.5 C, PIC-329204 16.6 bar g, TIC-329005 94.1 C, HV-322602 40 %, HVGT-322605 36.1 %, HIC-322604 46.5 %, AY-322701 3.19, PT-329201 132.1 bar g, PT-329207 4.398 bar g |
| 90.5 %, 2 h 46 min | `Data/Trends 511.2026`, 5 November 2026 (§CV.2-3) | TT-322005 not logged; HV-322602 = 65.4 % (L / 101.95 %)^1.6 |
| 74.4 %, 72 min | the same | TIC-329005 98.3 C, HV-322602 35-40 %, PT-329201 132.5-133.5 bar g at 69-75 % |
| 68.9 %, 46 min | the same | the same |

Licensor's windows (Operating Manual III §5.2): N/C 2.90-3.10, TT-322005 180-183 C, PT-329201 136-143 bar. A-34's atoms
close tick by tick on a turndown (`Tests and Reports/tests/phase7/test_loop_atoms.py`, §CX.1). Decision 190 adds the procedure's criteria (a)-(d) and (f); decision 196 fails a hold on a relief's lift.

**Established. Do not measure these again; cite the section.**

* The cold branch's term is 322R001's carbamate source, 322E002's gas CO2 less the off-gas CO2; the flash loses
  half its CO2 gas per kelvin of TT-322010 (§CVI.1-4); on the holdup bundle it fails first at 92.3 % (§CXIV.6).
* The low holds' latch (session 95's collapse: 322E002's feed N/C through 3.0 onto the low-N/C branch, a
  recycle of 14-21 minutes, §CVIII.3, §CX.8) is the loop's missing species state: with 322R001's liquor
  carried by species it does not come at 74.4, 69.3 or 68.9 %, and with the product unscaled the hump goes
  (§CXIII.3, §CXIV.3, §CXIV.6). 322E003's flood and vent are its symptoms (§CV.3, §CVII.5).
* Measured and not the cause: TT-322011's vent-top correlation and 322E002 over-quenching (Part XCI);
  322E001's overhead fraction (§XCIV.2); 322E003's liquor, tempered water and condensation margin (§XCIV.3-4,
  §XCV.3); 322E001's feed-deficit bottoms term (§XCVI.2); the ramp's rate and HIC-322605's handling (Part CIV);
  the slip gain at 70 % (§CIII.7); P6 (§CVII); E0 (§CX.8); E1eu (§CXII.7, §CXIV.3); the ratio's floor
  (§CXII.8); the AT trim's gain (§CXIV.3). Rejected: P5 (§CVI.5); unbundled: the S2 terms, slip gain 0 (§CVII).
* Boundary facts for every arm. Each handle starts on the engine's design seed and moves as a
  departure with the load (§CVI.5, §CVII.1). FFIC-321404's ratio is on the engine's basis: the
  plant's 2.115 is 2.047-2.053 here (§XCIII.3). HV-322605's anchor is 60.0 % at 100 %, so Book2's
  36.1 % is 43.27 % here (§CIV.1). FT-329403 is stream 901, 60.85 t/h at the design (§XCVIII.2).
  LT-329501 cannot reach Book2's 7 %: 322F001's suction is proportional to the level (§XCVI.2).
* The procedure (§CXV.14): L1, L6, L3 (bundle A) and L2's raise are needed, L12's shown by the engine; L3 is not
  fulfilled (B-136); L2's one-sided response is B-125's edge (§CXVII.4, correcting §CXV.4); (e) is met on no engine;
  the L2 board loop as approved fails (§CXV.7); the seed carries the 2 700-3 000 s mode and wanders (§CXLIX.4; B-157).
* The holdup bundle (scratch). Its cold branch at 92.3 % follows 322E001's `g_hc` (§CXV.6a). Its holds at 74.4
  and 69.3 % rest on 322E001's feed-deficit rise (off: TT-322004 follows the plant, all five holds lost,
  §CXVII.6), and the 69.3 % one boils on the bubble point, off the plant on TT-322004, PT-329201, AT-322701 and
  the steam (§CXVII.2). The loss needs neither 322E002's live law, the conversion's residence time, its slip nor
  its movement (§CXVII.9). 322R001 sits at 60 % of its equilibrium by V1's `X_INF`; the licensor gives 95 % (§CXVII.8).
* 322R001's loop path by path, rise off (§CXVIII.6-11): alone, 322E002's edge (PV) or V1's re-flash at the live
  pressure (ZP) loses 92.3 and 69.3 %, the conversion and its slip amplifying 1.0 K per K; the three pinned, the top
  stands on its bubble point at 92.3 % and boils at 69.3 % (§CXVIII.8).
* Sessions 109-112 (§CXIX.6, Part CXXII): 322E002's flash target swings 0.16-0.27 inside 1 K and 1.3 bar; B lifts the
  rise (over 15 000 s it fails 5 tags late, damping the seed's wander, §CL.2). Session 134 (Part CXLVI): S + B on UA
  as built settles at 92.3 % on the plant's signs, 12.03-12.18 K; no inert or liquid term carries the 3-6 bar (§CXLVI.3); below 90.5 % every hold is 7.3-9.8 K cold or latches PC35
  (A-61). Session 135 (§CXLVII.2): with the header rule 92.3 % runs latch-free; 69.3 % misses (rise 4.2-5.0 K).

**Bundle A (decision 181), scratch only; `ureasim/` is as built.** P1 (322E002's UA on the CO2 demand ratio^0.77,
§CVII.1), P4 (the wall loss on a stagnant reactor only), the 322F001 lift p_disch - 2.41 (1 - r^2) (decision 180), the
slip gain 4.0. It passes 92.3 % and latches or leaves the band below; with B-126 (b) the low holds are trip-free and
92.3 and 90.5 % latch on the cold branch; 111 % is out of band on both (§CXII.10, §CXIV.6).

* Sessions 136-137 (§CXLVIII.5, .12, §CXLIX; decisions 269, 270, 274, 275): no wave M arm stands; the reactor's law is
  cleared (refit not built); the seed's rise is 0.68 K under Book2's 100 %; the u set fails decision 278 (§CL.2).
* 322R001 on the engine's step, boundary frozen (§CL.3, retracting §CXLIX.5 at 92.3 %): one stable root at every load,
  the engine on it (92.3 % 12.097 K; 69.3 % 6.739 K). Not the reactor's branch selection (decision 280; loop-level
  multiplicity untested); the loss is the boundary, 322E002's split first: 92.3 % -1.10 K (split alone -2.51 K),
  69.3 % -7.46 K (-8.03 K). The plant's split is the seed's by assumption (§CL.4; data gap 17).
* The reactor as the meter (§CLI.4): the boil cap lies 1.3-3.5 K under Book2's TT-322005 at every reduced band, so no
  share fits the rise; the thermowells read 0.171-0.180 at 94.2 % on law B, not identifiable at 69.3 %: not a datum.
  322E002 at unit level (§CLI.5): its NTU-quench outlet (1.2 K off Book2's departure at 94.2 %, 8.5 K at 69.3 %) sets
  its share; no closure can be scored.

**Next step.** The plant's 322E002 split (gap 17, readback row 30 on LIC-329504 and LIC-329503), then the
decomposition on it; or the process engineer's call to take the seed's share. The outlet's quench (§CLI.5) is the
term to measure in the loop. Decision 277's rule rides every arm; B-126, B-136 inside (265, 266).

**B-120 folded in (decisions 177, 181).** V1's stripper slip gain drives a loop mode (§XCVIII.3, §CIII.7, §CXIV.7,
§CXVII.6); the gain stays 4.0.

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
t/h); with B-118's B on UA as built and 322E001's lean rise on it stands at 92.3 % (13.24 K). S on design references
(§CXLVI.6-7) is the design point to the bit at t = 0; with B, the lean rise off, on UA as built it settles at 92.3 % on
every plant sign; on Book2's UA exponent, 0.50 (§CXLVI.2), it rings (§CXLVI.12, .14). Decided (decision 264): (c),
S with B, measured inside B-118; 322E002's UA as built, the clamp rejected (decision 267). On the 100 % seed S alone
(on N100A) fails decision 259 on 16 tags over 15 000 s by a growing oscillation (TT-322011 to 8.4 K, AT-322701 0.072,
FT-329403 3.0 t/h; §CXLIX.4); with the holdup and the other four laws the residue is small and fails decision 278's paired test where the arm holds still and N100A wanders (§CL.2).
At unit level on Book2's bands (§CLI.5) as built and E1eu coincide on the quench's outlet (saturation 0.99-1.0);
with the outlet held on Book2's departure the law separates them (as built 0.957 at 94.2 %, 0.895 at 69.3 %, on a
boundary other than the 0.857 / 0.798 above; E1eu 1.0, 0.956) and the shares by 0.02-0.03; S at unit level raises the share where S in the loop lowered it
(unexplained). No plant share exists to score them against (gap 17). Next step: B-118's.

### B-126 — 322R001's 136 t of liquor has no composition

*Raised 2026-11-11, session 97 (§CVIII.5).* `reactor_inventory.py:328-329` sends on the tick's reaction product scaled
to the hydraulic outflow: 305 s after a 20 % CO2 cut the overflow carries 2 933 kmol/h more N and 576 more C than the
reaction produced (§CXII.9, §CXIII.2). The loop's 153 t of liquor holds no species (§CXIII.3). Measured in scratch (Part
CXIV): (b), the holdup's species in twelve compartments, closes to 6e-14 kmol a tick; the 74.4 % hump falls 3.649 to
3.197, the latch goes at 74.4, 69.3 and 68.9 %, and 92.3 and 90.5 % fall onto the cold branch (322E001's `g_hc`,
§CXV.6a); 849 seed leaves differ. Its low holds rest on 322E001's feed-deficit rise and the 69.3 % one boils
(§CXVII.2, §CXVII.6): not a build candidate as measured. The 5 s cycle below N/C 3.0 (A-57, kept as built, decision
232) runs on this path's missing holdup; a 60 s lag on the overflow slows it (§CXXXIII.4-5). Options: (a) keep as
built; (b) the bundle with the change that holds 322R001 (B-118), a seed criterion restated first; (c) C2's second
half; (d) the loop's other holdups (H5). On V1.2's seed (b) differs in 11 248 leaves and keeps every published tag
inside its last displayed digit over 600 s: the criterion it needs is a display-resolution one, the process engineer's
to restate (§CXLVI.8). Every session 134 arm carries it (§CXLVI.12-13).
Decided (decision 265): (b), measured on decision 259's seed criterion, every published tag within its display step
over 14 400 s; not built. On the 100 % seed the holdup alone (on N100A) fails it on 22 tags over 15 000 s by a
growing oscillation (LT-322504 to 8.2 %, PV-329207B 9.6, FT-329407 5.4 t/h; §CXLIX.4); with S the residue is §CL.2's
(the arm still where N100A wanders). Next step: B-118's.

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
below, 323D001 at its set point, the 100 % pin to the bit. With S + B (session 134, §CXLVI.13), (b) gives TT-322004
-1.7 K at 92.3 %, -2.1 to -2.3 K at 90.5 %, -4.6 K at 74.4 % and -9.5 to -10.4 K at 69.3-68.9 %: the plant's sign,
0.8-1.8 times its size.
Lead (§CXLI.7): the plant's notebooks close 322E001's lower shell-condensate block valve at 100 % load and below. On
the new stripper's GA the outlets are N6A at EL +7154 and N6B at +6554; N6B shut leaves 0.866 of the tubes active
(calculated, §CXLVI.9). If the design duty is on that area, nothing changes below 100 %; if on the full area, the lean
rise returns at 74.4 % and below, tried only on a ringing law (§CXLVI.14). Which reading holds is the process
engineer's. Decided (decision 266): (b), the rise off, measured only together with decision 263's refit of 322R001.
Next step: B-118's.

### B-157 — The as-built 100 % seed is not stationary over 15 000 s

*Raised 2026-11-20, session 138 (As-Built §CXLIX.4, §CL.2, §CL.3; decision 278).* N100A, the design seed with every
B-118 law off, wanders from its own first sample on the console's decimals: TT-322011 0.4 K (beyond one step at
7 550 s), LT-322504 0.2 % (6 190 s), AT-322701 0.003 (11 350 s), FT-329403 0.05 t/h (6 620 s), FT-329407 0.05 t/h
(500 s), HIC-322605 re-typed six times (60.00 to 60.02 %). Under decision 278 the wander is the reference every law is
paired against.
Established: on AT-322701 and TT-322011 the arms X_ej, X_wall and X_lean hold flat where N100A moves (§CL.2). 322R001's
open-loop relaxation does not reproduce it: on the seed's frozen first-step boundary the column has one stable root
(12.94 K, e-fold about 3 600 s) and relaxes toward it, its top leaving the boil cap by 15 000 s, while N100A's
thermowells hold the cap and drift up 0.01-0.05 K (§CL.3). The reactor multiplicity the session 138 plan offered as
the mechanism does not exist (decision 280). Ruled out (§CLI.6): the seed's 0.06 K offset from its step's root; placed
on the root (P100) the seed is kicked (six tags off N100A from 10-90 s, the top back on the cap by 600 s), not cured.
Ranked (§CLI.6): on the console's decimals FT-329407 leaves first (500 s), then LT-322504, FT-329403, TT-322011 and
AT-322701 (6 190-11 350 s); raw onsets are degenerate (every unit by 20 s), and no unit is named as the origin.
Acceptance: the mechanism named, a seed that holds every displayed tag within one step of its first sample over
15 000 s or the wander accepted as the plant's, the process engineer's call.
Open: which loop path carries it (the trims that re-type HIC-322605; the steam header's flows, FT-329407 from 500 s).
Next step: FT-329407's first 500 s on N100A, term by term (the LP header's inlets and PV-329207B's swing), on a
sampler whose references are not taken by a hook (P100n's null failed on the runner's x_* keys only, §CLI.6).

---

# Section C — Calibration Deferrals

*None open.*

---

# Open data gaps

*`Claude.md` §4: a datum that `References\`, the vendor archive and the V1 source all fail to supply. The ledger was accepted by the process engineer on 2026-10-16 (decision 128); each row keeps its stand-in as built; every row's full search record is in `docs/history/handoff-record-to-session-95.md` (grep the tag before the archive is searched again).
Rows 10, 15 and 17 close on one plant DCS readback session (`Tests and Reports\reports\DCS readback checklist.md`); rows 1 and 3 on Körting's curves. Rows 4, 5, 9, 12 and 14 were closed by decisions 255 to 257 and row 16 on decision 253's condition (2026-11-19, §CXLVIII.3); the checklist's rows 6, 9, 11 and 22 and the LV-324501A step test remain as their checks. The checklist's row 14, TV-323013B's flow and differential, is decision 178's cross-check and no ledger row; its row 26, LT-328503's configured range, is decision 243's (§CXL.1).*

| # | Datum | Needed by | As built | Found so far | Route to close |
|---|---|---|---|---|---|
| 1 | 322F001's nozzle and mixing-throat geometry, loss coefficients and performance diagrams | `control/jet_pump.py`, `data/unit_322f001.py` | both areas back-solved from the licensor's design duty on open-literature loss coefficients; the design point exact, the stall margin not (B-12's 90.7 %, §LXXI.3); the lift a fixed 4.2 bar | no vendor geometry or curve in either archive (§LIX.4). The plant keeps the entrainment ratio from 69 to 102 % load, mu / mu_ref 1.031 +/- 0.044, n 15; the as-built closure stalls on that line at 69.9-80.7 %; a friction share of at least 2.41 bar of the lift passes it, a fit (§CV.3-4). Book2's points: LT-329501 11 % at HV-322602 40 % (69.3 %), 1 % at 54 % (80.4 %). LT-329501 is not in the 5 November trends, so the level term is unfitted; session 99 (§CX.9): the friction share needed is 0-2.41 bar over the 15 windows, and no level law fits Book2's four points (V1's passes 1-23 % of the plant's suction there). The suction line 150-ACA1-322004 (168.3 x 12.5) falls from 322E003/N6 at EL +21192 to 322F001/N1 at EL +8300 (isometric UD-RL-100-MB-0004 rev 03, as built), against Uhde's 10 m L.C. suction head (EC-0013) and the HP-level drawing's +10.00 m ejector (§CXXXIX.2). EC-0013 p. 2: motive 44 600 kg/h at 161.7 bar a, suction 62 000 kg/h at 141.5 bar a, mixed 145.0 bar a, "static pump head 4.2 bar g"; the ejector body (item 10) is printed Da 164 mm on a 60 mm wall (DZ-0013-003 p. 2, "ø164x60" on the as-built drawing), so its neck's bore is 44 mm, calculated; no page labels it the throat (§CXLI.7, §CXLVIII.8) | Körting's 14 diagrams, order 2/131/4/04219 (draft request: `Tests and Reports\reports\Koerting request draft s99.md`). The lift prototype is held with B-118 (decision 180). Session 135 [E] (§CXLVII.6): on a 44 mm throat no literature loss set makes the duty; K_th 0.32-0.54 does. Session 136 (§CXLVIII.8): EC-0013's row 18, "static pump head 4.2 bar g", is defined on no page; read as the lift it back-solves a 45.6 mm throat on EC-0013's densities (a 44 mm throat then needs K_th 0.13, inside the literature), the 3.5 bar pressure difference 52.4 mm; decision 272 proposed (no re-anchor; the letter asks row 18's meaning and the throat). Held with B-118; letter final: `Tests and Reports\reports\Session_135_gaps\Koerting request s135.md` |
| 3 | Körting's performance curves of 324F002, 324F004 and 324F005 | `ejector_map`, B-57's interpolation on the synthesized maps (§XLIX.4, §L.1) | synthesized maps, anchored on the PFD's design loads; in-situ factors 0.919, 0.336, 0.497; the break, P_c's scale and width, on the plant's 5 November bracket (decision 251, §CXLIV) | one duty point an ejector; no curve in the archive (§XLVIII.2). The plant's motive break-off, the datum a curve must meet: HIC-329605 between 55 and 64 % (HIC-329606 38-40 %) at PT-329207 4.20-4.24 bar g, 5 November 2026 13:11-13:16, 75 % load (§CV.5). Since decision 251 the engine holds at 64 % and 40 % and loses both vacuums below, more softly than the plant: stage 1 at 0.345 bar a at 55 %, where the plant logged 0.6 (§CXLIV.3). The ejector file lists no curve (AB-0007); Körting's minimum motive 3.1 bar g for 324F004 / F005; Uhde's condenser cooling-water flows (§CXLI.7) are ruled out as the cause: on them the vent the ejectors draw falls by at most 4 %, and on the sheets' rises they would carry a larger duty (calculated, §CXLV.4) | Körting, orders 2/115/4/09674 and 2/232/4/00503 (the same draft); checklist row 13: 324E002's and 324E005's cold-end and cooling-water temperatures for 5 November 13:00-13:30. Session 135: letter final (`Session_135_gaps\Koerting request s135.md`); the [E] break characteristic is in §CXLVII.10 |
| 10 | LT-329505's tap elevations | LI-329505 between its taps (decision 33's class) | V1's holdup ratio; LV-329505 on Flowserve's trim (§LXVIII.5) | upper tap 324E001 / N5 at EL +15129; lower tap on the DN700 condensate pot at EL +10651 (isometric UD-RL-100-MB-0312): 4 478 mm apart. The loop summary prints 3 000 mm. The conflict is logged, not resolved (§CIII.5). Uhde's data sheet UD-MR-G00-EC-0133 p. 4: nozzle distance 3 000 mm, set range 0 to 300 mbar on 922 kg/m3, so the 4 478 mm would over-range it (§CXXVII.5); the range is 100 mbar per metre of nozzle distance, 1.11 times the head of 922 kg/m3, as LT-329504's is (§CXXVIII.5). Rosemount's factory record: 1151DP4, serial 8063396, 0 to 300 mbar (UD-MR-G00-DZ-0012-002 p. 46; a second unit keyed LT 329505 at 326 mbar is LT 323505's range, a mis-keyed tag). Hook-up K3V31 (UD-MR-G00-LD-0001 p. 76): transmitter below the taps, a vented separator pot on the upper connection, so a condensate-filled reference leg, "3000 liquid head" (§CXL.1-2). Rosemount's compliance and WIKA's seal certificates key LT 329505 with LT 328503 at 0-326 mbar, weakening the mis-keyed reading; only rev 02 of the sheets exists (§CXLI.7) | checklist row 10: the transmitter's LRV and URV decide which span its 0-100 % covers. Session 135 [E] (§CXLVII.7): on the wet leg 0-300 mbar covers the whole 3 m, or the upper 3.32 m of 4.478 m; LI-329505 is logged nowhere, so the display's scale alone moves. Decision 257 keeps the row open on the readback (ruling 8) |
| 15 | LT-329501's calibrated span and its design reading: which tap distance the 0-1 200 mbar covers, the impulse legs' fill, the level the design gives | LI-329501 between its taps (decisions 33 and 214); 322F001's suction (row 1) | V1's holdup ratio, 50 % at 3 837 kg (`data/unit_322e003` `LEVEL_NLL_PCT`, `TAU_HOLDUP_MIN`), which also sets 322F001's suction, the loop-pressure sum and the flooded-surface derate | Uhde's sheet EC-0133 p. 3 and loop summary UD-MR-329-EC-0001 p. 77 (LI, AH): L 329256, U 329257, both legs "High Pressure Condensate", 1 133 kg/m3, 141 bar a, 99 C, 0-1 200 mbar over 10 000 mm. Both impulse lines run to line 322004, 322E003's outlet to 322F001 (piping list UD-RL-G00-MB-0001 pp. 91-92, PDF 94-95); the as-built isometric UD-RL-100-MB-0004 rev 03 puts the branches at EL +8300 and +21089, 12 789 mm apart. The HP-level drawing (UD-AU-322-EC-0005 p. 27) gives 322E003's bottom part +16.65 m, not the downcomer's. MB-0415 / 0416 are field-routed; MB-0420 is the purge header from 329P004A / B. Book2 reads 1-11 % (§CXXXIX.2). Rosemount's factory record: 1151HP5, serial 8063392, 0 to 1 200 mbar (UD-MR-G00-DZ-0012-002 p. 42). Hook-up K3V91 (UD-MR-G00-LD-0001 p. 79): transmitter below both taps, "liquid head 10.000 mm", both impulse lines drawn purged through check valves from FI 329421 and FI 329422, so full of condensate, on a design drawing (§CXL.1-2); Operating Manual III pp. 1-59 and 1-83: both lines continuously injected with condensate from 329P004A / B (§CXLI.7) | checklist row 25: the configured LRV and URV and the legs' arrangement; a walk-down of the taps. Session 135 [E] (§CXLVII.7): with both legs wet (K3V91) Book2's 1-11 % is liquid 8.6-12.1 m above 322F001, on Uhde's 10 m suction head; dry, 0.1-1.2 m; the design reading not computable on V1's holdup. Session 136 (§CXLVIII.9): the wet reading with a zero LRV is withdrawn, since Book2 reads above its 13.7-17.5 % ceiling (100.3 % band mean 21.0 %, maxima to 37.2 %); dry or an elevated span remain, the readback decides (decision 273 proposed) |
| 17 | 322E002's gas-CO2 share (the CO2 it passes to 322R001 uncondensed) at 92 % and 69 % load, or its LP steam make there | B-118's decomposition of 322R001's boundary (§CL.3, §CXLIX.5) | the plant's split taken as the seed's 0.169 at every load | Book2 logs no steam-make tag: FT-329407 is the LP header's swing export to 320MT02, FY-329403 MP stream 901; both fail as proxies on the engine (§CL.4). Archive: F 329404 "CPL fr. 322E002" (UD-MR-329-EC-0001 rev 01, OCR p. 16) is a 3-6 m3/h condensate line, not in Book2; the 29-06-2025 trends hold no steam-make tag. The TT-322010 cross-check fails (§CL.4). Session 139 (decision 282, §CLI.3): no meter on the make-up 916 (the unit 329 loop summary lists none); the drums' level valves exist, LV-329504 (916) and LV-329503 (913, 329D009's cascade), their sheets in §LIII.3, and Book2 logs both outputs (LIC-329504 40.7 to 33.3 %, LIC-329503 66.3 to 57.4 % from 100.3 to 69.3 %, the level at 50 %) and PT-329207 downstream, but neither inlet pressure (loops P 329205 / P 329254 on 329D009, P 329257 / P 329258 on 329P001A/B's discharge), so no flow; the installed differentials and the rangeability are the unknowns. The reactor inverse (§CLI.4): the rise cannot be fitted below the cap; the thermowells read 0.171-0.180 at 94.2 % on law B, not identifiable at 69.3 %; not a datum | checklist row 30: LIC-329504's and LIC-329503's outputs with each valve's inlet pressure in service (P 329257 / P 329258, P 329205 / P 329254) beside PT-329207 at 92 % and 69 %; with 959 and 913's flash they give 322D001A/B's make, and through §CL.4's duty chain the share [I] |
