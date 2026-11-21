# handoff.md — Open Issues for the Human Engineer

Tracker for `Urea Simulator V1.2` (a copy of V1.1 at commit 5ddc107, decision 251). It holds **open** items only, each as its **current state**: the
problem, its acceptance tests, what is established, the open options, the next step. A session rewrites
an item's state in place and appends no session paragraph (`CLAUDE.md` §3a). Close an item by deleting it;
its closure is recorded in the session's As-Built Part. Ceiling: 300 lines.

**Last updated:** 2026-11-20, session 144.

**Section A** — issues created by the V1.1 rewrite.
**Section B** — physics gaps inherited from V1 that the rewrite carries forward. Port V1's behaviour
exactly, including the compromise, and keep the item open here.
**Section C** — calibration deferrals: the port reproduces V1 knowingly and the correction waits on the
process engineer's decision.

History, frozen: `docs/history/handoff-record-to-session-95.md` holds the closure schedule, the closed
items' summaries, B-118's chronicle (sessions 76 to 95) and every data-gap row's full search record.

---

# Section A — Rewrite issues

### A-63 — The as-built seed's 322R001 top boils on the first tick under the rewrite's cap

*Raised 2026-11-20, session 142 (decisions 290, 294, 296; As-Built §CLIII.6, Parts CLIV to CLVI).*

**Problem.** V1 seeds 322R001's node profile at the fixed point of `reactor.KINETICS` at 228.46 m3/h (the PFD overflow
on a constant 990 kg/m3) and steps on `PINNED_KINETICS`, anchored at 227.50 m3/h (`liquid_density` of the profile's
mean). V1 has no ceiling, so its 0.045 K top excess stands as a temperature. The rewrite's cap (decision 102) sits on
the design top with zero margin and clips it: the seed's top boils 29.93 kg/h on the first tick and 30-123 kg/h over
N100A's 15 000 s, against decision 102's premise that nothing flashes at the design seed. A test comment records the
boil as built (`Tests and Reports/tests/engine/packet/test_synthesis.py`, the 39 399 kW assertion).

**Acceptance (decision 296, superseding 294's gate).** The fix to test is (b), the cap with a 3.5 K design margin [E]
(the final value from the bubble-line literature, decision 293), alone on the as-built seed, law B re-referenced to it:
(1) the design pin to its printed digits at t = 0; (2) zero boil at the top; (3) at every sample every displayed tag no
further from its printed value than N100A at the same time, plus one display step; (4) the top settled, B143 and
N100A run to 30 000 s. If the top levels off inside one display step of 183.0 C, (b) is accepted and built with an
equivalence test asserting both sides, and the seed becomes N100B.

**Established** (Parts CLIV to CLVI, scratch only):
* The joint re-solve (§CLIV.2-3) clears the first tick, but the boil returns from 30 s on the cap's zero margin.
* (b) on B144 to 30 000 s (§CLVI.3): (1) met at tick 1 (every printed value); (2) met, no boil on any sample, the
  margin 3.43-3.50 K (N100A boils on every sample, to 127.6 kg/h); (4) met on the criterion registered before the read,
  narrowly: slope +0.0013 K per 1 000 s over 15 000-30 000 s, the last three 3 000 s means within 0.016 K, the top
  183.000-183.077 C, displayed 183.1 on 56 % of the samples after 15 000 s.
* (3) fails as written, sample-wise, on 323F010's level (840 samples, 5 steps over N100A), FT-329407 (786, 5), FT-329403
  (126, 3), LT-322504 (288, 1) and m308 (105, 1): the two arms wander out of phase. On the run's largest excursion it
  fails on 323F010's level alone (7 steps against 4), a level held by the rig's HIC-323605 trim. Those tags sit on the
  323C003 -> 323F004 -> 323F010 chain that (b) enlarges (§CLVI.4; B-157).
* FT rates over 15 000-30 000 s: FT-329403 +0.0004 t/h per 1 000 s under (b) (N100A -0.0006); FT-329407 +0.0015 (+0.0012).

**Open options**, the engineer's: condition 3 read (i) at every sample, so (b) fails; or (ii) on the run's largest
excursion, (b) then failing on 323F010's level alone, which the engineer may count or set aside as the rig's trim.
Condition 3 is worded on the printed design value: sample-wise the failing tags with a printed value are FT-329407 and
FT-329403; on the largest excursion no tag with a printed value fails (323F010's level has none, scored from N100A's
first sample).
(b) is not built and N100B is not made: the plan's trigger, condition 4, is met, but the gate is four conditions.

**Next step.** The engineer's reading of condition 3; on a pass, the build of (b) with its equivalence test and N100B
as decision 278's new reference.

---

# Section B — Physics gaps inherited from V1

### B-118 — Below 100 % load the engine holds no steady state on the plant's reactor window

*Raised 2026-10-30, session 76. Phase 7. Record: As-Built Parts LXXXIX to CLVI; decisions 177, 180, 181, 188,
190, 259 to 284, 286, 288, 290 to 293 and 295 to 300.*

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
* Measured and not the cause (Part XCI, §XCIV.2-4, §XCV.3, §XCVI.2, Part CIV, §CIII.7, §CVII, §CX.8, §CXII.7-8,
  §CXIV.3): TT-322011's vent top, 322E002's over-quench, 322E001's overhead and bottoms terms, 322E003, the ramp, the
  slip gain at 70 %, P6, E0, E1eu, the ratio's floor, the AT trim. Rejected: P5 (§CVI.5); unbundled: S2 (§CVII).
* Boundary facts: each handle starts on the design seed and moves as a departure with the load (§CVI.5, §CVII.1).
  FFIC-321404's plant 2.115 is 2.047-2.053 on the engine's basis (§XCIII.3); HV-322605's Book2 36.1 % is 43.27 % here
  (§CIV.1); FT-329403 is stream 901, 60.85 t/h at design (§XCVIII.2); LT-329501 cannot reach Book2's 7 % (§XCVI.2).
* The procedure (§CXV.14): L1, L6, L3 (bundle A) and L2's raise are needed, L12's shown by the engine; L3 is not
  fulfilled (B-136); L2's one-sided response is B-125's edge (§CXVII.4, correcting §CXV.4); (e) is met on no engine;
  the L2 board loop as approved fails (§CXV.7); the seed carries the 2 700-3 000 s mode and wanders (§CXLIX.4; B-157).
* The holdup bundle (scratch; §CXV.6a, §CXVII.2-9, §CXVIII.6-11): its cold branch follows 322E001's `g_hc`; its low
  holds rest on 322E001's feed-deficit rise; 322R001 at 60 % of equilibrium by V1's `X_INF` (licensor 95 %); rise off,
  322E002's edge or V1's re-flash alone loses 92.3 and 69.3 %.
* Sessions 109-112, 134, 135 (§CXIX.6, Part CXXII, §CXLVI.3, §CXLVII.2, §CL.2): B lifts the rise; S + B on UA as
  built settles at 92.3 % on the plant's signs, 12.03-12.18 K; no inert or liquid term carries the 3-6 bar; below
  90.5 % every hold is 7.3-9.8 K cold or latches PC35 (A-61, closed by decision 287 on the header rule); with the
  header rule 92.3 % runs latch-free, 69.3 % misses (rise 4.2-5.0 K).

**Bundle A (decision 181), scratch only.** P1 (322E002's UA on the CO2 demand ratio^0.77), P4 (the wall loss on a
stagnant reactor), the 322F001 lift p_disch - 2.41 (1 - r^2), slip gain 4.0: passes 92.3 %, latches or leaves the band
below; with B-126 (b) the low holds are trip-free, 92.3 and 90.5 % cold; 111 % out of band (§CXII.10, §CXIV.6).

* Sessions 136-137 (§CXLVIII.5, .12, §CXLIX, §CL.2): no wave M arm stands; the seed's rise 0.68 K under Book2's 100 %.
* 322R001 on the engine's step, boundary frozen (§CL.3, retracting §CXLIX.5 at 92.3 %): one stable root at every load
  (decision 280); the loss is the boundary, 322E002's split first (92.3 % -1.10 K, 69.3 % -7.46 K), the plant's split
  the seed's by assumption (§CL.4; gap 17). As the meter under the cap (§CLI.4-5) no share fits the rise (decision 284).
* The boil cap (Part CLIII; decisions 286, 288): 23 kJ/mol, 0.532 K/bar, rejected by Book2 in every band but 80.4 %;
  candidates (a) 87 kJ/mol and (b) the slope with a 3.5 K design margin (A-63); through `node_boil` neither moves a
  reduced-load hold. Cap released (§CLIV.6, [I]): the share on Book2's rise is 0.165-0.174, law B at its floor, a
  model clause, not B-125's target (decision 295). Law B's floor binds in no hold (§CLV.3), closed as a lead
  (decision 298); under (b) law B is re-referenced to (b)'s margin (decisions 292, 296).
* 322E002's steam pressure (§CLVI.2): Uhde's manual (UD-VT-G00-DC-0003 pp. 1-54, 1-55, 5-7) makes PIC-329207 the
  handle on 322E002's condensation, TI322005 its indicator, low drum pressure the cause of a cold top; no gain printed.
  Every arm moves the set point by Book2's departure (4.347 bar g at 69.3 %, 0.05 bar under Book2's 4.398, about 0.02
  of share on S). On U693's frozen S + B boundary (unit level, [I]) S answers 0.37 of share per bar (0.169 at 4.54-4.59
  bar g), the law as built 0.008 (saturation 1.0, the quench 3.6-4.0 K over the shell), a boundary other than §XCI.2's:
  B-125's insensitivity is located there, not shown in the committed engine's loop.

**Stop rule (decision 300).** If no arm holds 74.4-68.9 % with TT-322005 in band by the end of session 146, the engineer
decides between physics and a labelled empirical trim under 90 % (a decided divergence); session 147 brings the measured
case for each.

**Next step.** B-125's target from §CLVI.2: the steam pressure that holds the plant's TT-322005 in the loop, on S (the
closure that answers the handle), measured against Book2's PT-329207. A-63's (b) is the engineer's (decision 296); the
margin's final value on the literature report (decision 293). Gap 17 stays on row 30. Decision 277's rule rides every
arm; B-126, B-136 inside (265, 266).

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
(unexplained). The cap-released share (§CLIV.6) rests on law B's floor and is not a target; scored as a record
(§CLIV.7), no closure lies within 0.02 of it at 94.2 or 69.3 %, the quench and the held outlet bracketing it. No
closure is ranked. The zero-margin class is adopted as "find and measure" (decision 297): this law is an instance (on
the slope on 827 of N100A's 1 500 samples, deficit to 0.058 bar), its margin sourced or measured before any build.
Located (§CLVI.2, unit level [I], on a boundary S made): on U693's turndown boundary the law as built (and E1eu, its saturation 1.0 there)
does not answer 322E002's steam pressure, the plant's handle (share 0.004, +0.008 per bar; the NTU quench 3.6-4.0 K over
the shell), where at the design boundary it answers 0.12 per bar; S answers 0.37 per bar. Next step: B-118's.

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

*Raised 2026-11-20, session 138 (As-Built §CXLIX.4, §CL.2-3, §CLI.6, §CLII.4, §CLIII.6, Parts CLIV to CLVI; decisions
278, 285, 289, 290, 294, 296, 299).*
N100A, the design seed with every B-118 law off, wanders from its own first sample on the console's decimals: TT-322011
0.4 K (beyond one step at 7 550 s), LT-322504 0.2 % (6 190 s), AT-322701 0.003 (11 350 s), FT-329403 0.05 t/h (6 620 s),
FT-329407 0.05 t/h (500 s), HIC-322605 re-typed six times (60.00 to 60.02 %). Under decision 278 the wander is the
reference every law is paired against.
Established: the engine is deterministic (§CLII.4; N142 bit-equal to N100A over 15 000 s, §CLIV.1); unit 329 follows
322E002's raise; no reactor multiplicity (decision 280); re-seeding on the step's root kicks the seed (P100, §CLI.6).
**The synthesis source is A-63** (decision 290): 322R001's profile and kinetics anchored at two flows, its top boil
under the rewrite's cap. With the joint re-solve (§CLIV.3) the wander is smaller and later but not gone (AT-322701,
FT-329403, TT-322011 off the pin from 12 920-13 300 s; LT-322504 holds), so the reactor is not its only source.
**The LP side** (§CLIV.4, §CLV.5): 323C003's feed cp anchor `CP_S208_DES` is V1's (`main.py:2640`) on PFD 208's
printed row; the seed's stripper bottoms stand 0.012 points of urea under it (55.8377 against 55.85 %, 2.4 times the
print's half-step), so the residual is the seed's bottoms, not the row's rounding, and PFD 208 (wt % to two decimals,
no energy row) gives no finer value. Anchored on the seed's bottoms over 15 000 s (L143) every 323 tag keeps its
display (323D001 within 0.0025 bar); record and keep, a re-anchor being a decided divergence. 323P001's flow (m308)
starts on a display edge (36 835.19 kg/h at 10 s, 0.19 above it; the 390 s onset); its 7 steps are LIC-323502's closure
passing the stripper drain's wander (correlation 0.62), 4 steps on the re-solved seed. 323F010's level (2 steps) is
the rig's HIC-323605 trim holding it against the synthesis wander. Neither is the first-tick residual or a tear.
**FT-329407** (§CLIV.5, §CLV.5): the evaporation heaters' draw is 323F010's inlet: 323F004's drain arrives 0.07-0.10 K
colder and 1.5-2.1e-4 leaner in urea by 450 s, about 80 % of 323E010's +6.8-10.8 kW; 324E001 follows 323F010's product
(+5.3-6.5 kW). Larger with both residuals removed, so neither residual's. Under A-63's (b) the wander is smaller in
322E002's duty and x_conv only, against a control (§CLV.2).
**323F004** (§CLVI.4, the time-boxed probe, decision 299): the drum sits on its bubble point and its drain's cooling
(-0.071 K at 450 s) is carried in: 323C003's drain arrives at 135 C but leaner in urea (-2.35e-4) and richer in NH3 and
CO2, lowering the bubble point 0.089 K; 323F004's own pressure offsets +0.013 K. Under (b) (F144b) the move is larger
(-0.094 K at 450 s, -0.150 K at 3 600 s) while (b) moves x_conv less, so the chain does not end in the synthesis wander
A-63's fix shrinks, and decision 299's closure condition is not met. The residual's unit is 323C003 (its bottoms' own
relaxation or its feed's, [I]).
Acceptance: the mechanism named, a seed that holds every displayed tag within one step of its first sample over
15 000 s or the wander accepted as the plant's, the process engineer's call (decision 285: re-seeding is theirs).
Next step: the engineer's, on §CLVI.4 (decision 299: no further session of its own).

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
| 17 | 322E002's gas-CO2 share (the CO2 it passes to 322R001 uncondensed) at 92 % and 69 % load, or its LP steam make there | B-118's decomposition of 322R001's boundary (§CL.3, §CXLIX.5) | the plant's split taken as the seed's 0.169 at every load | Book2 logs no steam-make tag: FT-329407 is the LP header's swing export to 320MT02, FY-329403 MP stream 901; both fail as proxies on the engine (§CL.4). Archive: F 329404 "CPL fr. 322E002" (UD-MR-329-EC-0001 rev 01, OCR p. 16) is a 3-6 m3/h condensate line, not in Book2; the 29-06-2025 trends hold no steam-make tag. The TT-322010 cross-check fails (§CL.4). Session 139 (decision 282, §CLI.3): no meter on the make-up 916 (the unit 329 loop summary lists none); the drums' level valves exist, LV-329504 (916) and LV-329503 (913, 329D009's cascade), their sheets in §LIII.3, and Book2 logs both outputs (LIC-329504 40.7 to 33.3 %, LIC-329503 66.3 to 57.4 % from 100.3 to 69.3 %, the level at 50 %) and PT-329207 downstream, but neither inlet pressure (loops P 329205 / P 329254 on 329D009, P 329257 / P 329258 on 329P001A/B's discharge), so no flow; the installed differentials and the rangeability are the unknowns. The reactor inverse (§CLI.4): the rise cannot be fitted below the cap; the thermowells read 0.171-0.180 at 94.2 % on law B, not identifiable at 69.3 %; not a datum; the seed's share stays a stand-in (decision 284). Cap released (§CLIV.6): the top reads 0.169-0.172 at 94.2 % and 0.165-0.174 at 69.3 % [I] with law B at its floor at every fit and the bubble line through the design top; the floor is a model clause, so not a datum; no 322E002 closure meets it (§CLIV.7) | checklist row 30: LIC-329504's and LIC-329503's outputs with each valve's inlet pressure in service (P 329257 / P 329258, P 329205 / P 329254) beside PT-329207 at 92 % and 69 %; with 959 and 913's flash they give 322D001A/B's make, and through §CL.4's duty chain the share [I] |
