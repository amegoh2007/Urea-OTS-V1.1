# handoff.md — Open Issues for the Human Engineer

Tracker for `Urea Simulator V1.1`. It holds **open** items only, each as its **current state**: the
problem, its acceptance tests, what is established, the open options, the next step. A session rewrites
an item's state in place and appends no session paragraph (`CLAUDE.md` §3a). Close an item by deleting it;
its closure is recorded in the session's As-Built Part. Ceiling: 300 lines.

**Last updated:** 2026-11-11, session 97 (the deep audit logged: A-31 to A-37 and B-125 to B-132 raised).

**Section A** — issues created by the V1.1 rewrite.
**Section B** — physics gaps inherited from V1 that the rewrite carries forward. Port V1's behaviour
exactly, including the compromise, and keep the item open here.
**Section C** — calibration deferrals: the port reproduces V1 knowingly and the correction waits on the
process engineer's decision.

History, frozen: `docs/history/handoff-record-to-session-95.md` holds the closure schedule, the closed
items' summaries, B-118's chronicle (sessions 76 to 95) and every data-gap row's full search record.

---

# Section A — Rewrite issues

Raised 2026-11-11, session 97, by the deep audit (As-Built Part CVIII; report
`D:\Work\reports\Deep audit 2026-11-11.md`). None is decided. Each closes with the test it names.

### A-31 — `data` has no place in the layering, and `thermo` imports it

`thermo/empirical.py:74` imports `ureasim.data.design_point`; 66 imports in `ureasim/data/` reach `thermo`,
`core` and `control` (§CVIII.8). `Claude.md` §1 rules 2 and 7 pull opposite ways. Options: (a) state
`data`'s place in rule 2 and enforce the import directions by a test, `tests/test_layering.py`
(recommended); (b) move the constants `thermo` reads into `thermo`.

### A-32 — The console converts gauge and absolute pressure itself

`hmi/faceplates/controller.py:181` and `master_setpoint.py:35,133,140` add and subtract the atmosphere;
`hmi/state_access.py:35` imports `core` (§CVIII.8). One constant serves both, so no value is wrong.
Options: (a) record it as §4a's decided exception and correct `docs/architecture.md` §3.2
(recommended); (b) the engine publishes display values and takes unit-tagged set points.

### A-33 — Without V1 mounted the equivalence layer does not run

83 test files guard on `v1_available()`; on 2026-11-11 5 862 of 8 016 tests skipped (§CVIII.2).
Options: (a) golden vectors of V1's outputs in `tests/equivalence/`, written by a tool when `E:` is
mounted, and a switch that fails a release run on a V1 skip (recommended); (b) keep as built.

### A-34 — No test covers an element, energy across the loop, or a load ramp

`tests/engine/test_dynamic_audit.py:103-157` closes four holdups' mass for a minute (§CVIII.8). Proposed:
`tests/phase7/test_loop_atoms.py`, each synthesis unit's N, C, H and O on every tick of a disturbance to
1e-9 kmol/h, B-126 and B-127 its named exceptions until they close; a turndown test when B-118 closes.

### A-35 — 75 of 237 modules have no test file of their name

`Claude.md` §6 asks for a one-to-one mirror (§CVIII.2). Many are covered under another name. To do:
one table of module against covering test, and an item for each module with none.

### A-36 — Three records disagree with the code

`reactor.py:22-27` claims conservation by construction without naming the tear (B-127); the As-Built
reference's maintenance rule names V1's old path; §CVII.4's "condensed fraction" is the flash's gas
fraction, corrected in §CVIII.3. To do: the first two, one line each.

### A-37 — `bracketed_root` returns silently when it runs out of iterations

`core/numeric.py:72-108`: the bracket's midpoint after 80 iterations, no flag, one tolerance for the width
and the residual (§CVIII.7). A residual with a step in it (a memo bin edge, decision 163) can exhaust it
unseen. Options: (a) count exhaustions in the engine's health, the result unchanged to the bit
(recommended); (b) keep as built.

---

# Section B — Physics gaps inherited from V1

### B-118 — Below 100 % load the engine holds no steady state on the plant's reactor window

*Raised 2026-10-30, session 76. Phase 7. Record: As-Built Parts LXXXIX to XCVIII, C and CIII to CVII;
decisions 177, 180 and 181.*

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

**Established. Do not measure these again; cite the section.**

* The responsible term is 322R001's carbamate source, the gas CO2 from 322E002 less the off-gas CO2.
  It is gone by L 0.85 on the ramp. The column's budget closes on every tick. 322E002's flash loses
  half its CO2 gas per kelvin of TT-322010 (§CVI.1-4).
* 322E003's flood and vent are symptoms of the reactor's collapse (§CV.3). Its sump factor does not
  throttle; the sump fills only after the trip stops the motive (§CVII.5).
* Measured and not the cause: TT-322011's vent-top correlation and 322E002 over-quenching (Part XCI);
  322E001's overhead fraction, flat on the ramp (§XCIV.2); 322E003's liquor, tempered water and
  condensation margin (§XCIV.3-4, §XCV.3); 322E001's feed-deficit bottoms term alone (§XCVI.2); the
  ramp's rate and HIC-322605's handling (Part CIV); V1's stripper slip gain at 70 % (§CIII.7); the
  reactor's conversion-deficit slip, P6 (§CVII).
* Rejected: P5, the off-gas split at the live top temperature (§CVI.5). Unbundled (decision 181): the S2
  stripper terms and slip gain 0, which starve the carbamate source (486-502 against 603 kmol/h at 92.3 %).
* Boundary facts for every arm. Each handle starts on the engine's design seed and moves as a
  departure with the load (§CVI.5, §CVII.1). FFIC-321404's ratio is on the engine's basis: the
  plant's 2.115 is 2.047-2.053 here (§XCIII.3). HV-322605's anchor is 60.0 % at 100 %, so Book2's
  36.1 % is 43.27 % here (§CIV.1). FT-329403 is stream 901, 60.85 t/h at the design (§XCVIII.2).
  LT-329501 cannot reach Book2's 7 %: 322F001's suction is proportional to the level (§XCVI.2).
* Session 95's collapse starts when 322E002's feed N/C falls through 3.0, onto the low-N/C branch
  (decisions 142, 147): collapsed samples hold a melt N/C of 2.23-2.58, condensing ones 2.76-3.35. It is
  a recycle of 14-21 minutes through 322R001, 322E003 and 322F001, its gain above one below about 2.8
  (an inference); FFIC-321404's ratio sat on its floor and could not act (B-128; §CVIII.3).
* 322E002's saturation fraction reads 0.85-0.93 from L 0.92 to 0.80 in every session 95 arm: 7-15 % of
  its condensables recycle, its feed does not fall with the load, and P1's two bases differ (B-125).

**Candidate bundle (decision 181). Scratch only; `ureasim/` is as built.**

* P1: 322E002's UA on the battery-limit CO2 demand ratio to the power 0.77. On that basis the seed is
  identical on every leaf; on `co2_scale` it is not (§CVII.1).
* P4: the reactor's wall loss on a stagnant reactor only.
* The 322F001 lift (decision 180): p_disch,eff = p_disch - 2.41 (1 - r^2), r the motive ratio.
* On the as-built stripper, `unit_322e001.SLIP_GAIN` 4.0. P6 is out: it changes nothing.

**Session 95's verification (§CVII.3-4; runs in `D:\Work\reports\B118_bundle_verification_s95`).**
92.3 % passes (TT-322005 182.4 C, no trip). 90.5 % has no trip but is out of band for 47-50 minutes
(down to 178.3 C). 74.4, 69.3 and 68.9 % hold 181.4-182.5 C through the ramp, then fail 960-1 680 s
after it: 322E002's saturation fraction collapses from L 0.76, its duty from 40 to 3 MW, and the loop
pressure reaches trip 22.2's 155.0 bar a. The collapse comes with P1 on the load ratio alone; without
P1, or with P1 on the feed mass, 322E002 holds and the reactor falls to 161-179 C.

**Open options and next step: the process engineer's choice.**

* (a) Recommended. Continue in scratch on the audit's sequence (§CVIII.9): E0, the AY-322701 target
  ramped to the plant's absolute value; E0t, the tick-resolution probe; E1 and E1r, the saturation law
  fitted on Book2 (B-125); E2, P1 on the condenser's own feed mass with P4 and the lift on the five
  holds; E3, 322R001's species holdup (B-126), then B-120's gain measured. First: E0 and E0t at 74.4 %.
* (b) Build the bundle now as decided divergences: one hold of five passes, one is trip-free and out
  of band, three trip.

**B-120 folded in (decision 177, revised by decision 181).** V1's stripper slip gain drives a loop mode:
gain 0 removes it at 92.3 % on the S2 prototype and at 111 % (§XCVIII.3), and alone on the committed
engine runs the reactor 12.4 K colder at 92.3 % (§CIII.7). The gain stays 4.0. Setting it to 0 waits
on the process engineer's review, apart from B-118's bundle.

### B-125 — 322E002's saturation law has no margin at the design and contradicts Book2

*Raised 2026-11-11, session 97 (§CVIII.4). Decisions 97 and 135's law.* `saturation_fraction` loses 1.54 %
of all condensation per bar its deficit stands above zero, and the deficit is zero at the design. As
built it gives 0.857 at Book2's 92.3 % band and 0.798 at 69.3 %, where the plant condenses fully; with
`BUB_KN` at 0 it gives 1.000 and 0.920 (the melt N/C taken as AY-322701 + 0.2, an inference). The outlet
temperature is an NTU quench of a 350 K spike, about -59 K per unit of ln UA. Options: (a) keep as built;
(b) fit the N/C slope above the branch and a margin so the deficit is at most zero at every Book2 band,
the seed unchanged, a harness switch, both sides measured (recommended, as B-118's steps E1 and E1r);
(c) the outlet at the melt's bubble temperature, the conductance setting the duty, only if (b) fails.

### B-126 — 322R001's 136 t of liquor has no composition

*Raised 2026-11-11, session 97 (§CVIII.5).* `reactor_inventory.py:328-329` sends on the tick's reaction
product scaled to the hydraulic outflow. Measured 305 s after a 20 % CO2 cut: the overflow carries
2 933 kmol/h more N and 576 kmol/h more C than the reaction step produced. A candidate cause of B-120's
loop mode (an inference). Options: (a) keep as built; (b) carry the holdup's species, the overflow at the
holdup's composition, identical at the seed, decisions 141 and 146's class (recommended, as step E3).

### B-127 — The loop's design boundary does not close, and the reactor's tear follows the CO2 load

*Raised 2026-11-11, session 97 (§CVIII.6); V1's reconciliation, once flagged as B-75.* In 134 215.2,
out 132 190.3 kg/h. The reactor removes 2 107.45 kg/h from its feed, NH3 129.1 kmol/h of it, 5.1 % of the
fresh ammonia, scaled on the CO2 load ratio. Exact at the design; off it the stream it corrects need not
follow the CO2 (PFD 308 at 0.50 of seed at L 0.71), a bias of at most about 27 kmol/h (an inference).
Options: (a) keep as built; (b) trace which boundary row carries the 129 kmol/h and move the correction
onto it as its departure, decision 104's class (recommended: the trace first, in scratch).

### B-128 — FFIC-321404's 2.0 floor binds on the engine's basis

*Raised 2026-11-11, session 97 (§CVIII.7).* `RATIO_SP_MIN` 2.0 is applied to the engine's ratio (design
2.0231 for the plant's 2.086 molar): 1.1 % of downward authority against the plant's 5.4 %. Options: (a)
keep as built; (b) the faceplate shows and takes the plant's basis; (c) the floor restated on the
engine's basis. The process engineer's call (decision 160's class).

### B-129 — 322E002 drops the heat of a net CO2 release

*Raised 2026-11-11, session 97 (§CVIII.7).* `carbamate_condenser.py:461` clamps the CO2 absorbed at zero.
It binds only as the saturation fraction goes to zero, on a start-up. Options: (a) keep as built; (b) let
the term go negative, the outlet floored at the shell's temperature, the seed unchanged.

### B-130 — `ProcessLoop` kicks on recovery from a bad PV

*Raised 2026-11-11, session 97 (§CVIII.7); V1's behaviour.* The PV history does not advance through a bad
PV (`process_loop.py:158-159`), so the first good sample steps the output by Kc times the PV's move.
`Controller` demotes to MAN and resets. Options: (a) keep as built; (b) reseed the history on the first
good sample, V1's on the harness switch.

### B-131 — The interlocks read a non-finite PV as healthy

*Raised 2026-11-11, session 97 (§CVIII.7).* `interlocks.py:135-143` and `:164-171`: a NaN fails both
comparisons, so trip 22.2 does not fire on one. The dynamic audit's finite-value check mitigates it.
Options: (a) keep as built; (b) a non-finite PV is live.

### B-132 — Two forms of the liquid critical-pressure factor

*Raised 2026-11-11, session 97 (§CVIII.7).* `valve.py:233` and `:316` hold F_F at 0.96; `:377` uses
0.96 - 0.28 sqrt(Pv / Pc) on water's Pc. Each pair is self-consistent; no valve was checked. To do: a
test that walks every valve in `data/` and asserts its sizing and its live law use one form.

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
| 1 | 322F001's nozzle and mixing-throat geometry, loss coefficients and performance diagrams | `control/jet_pump.py`, `data/unit_322f001.py` | both areas back-solved from the licensor's design duty on open-literature loss coefficients; the design point exact, the stall margin not (B-12's 90.7 %, §LXXI.3); the lift a fixed 4.2 bar | no vendor geometry or curve in either archive (§LIX.4). The plant keeps the entrainment ratio from 69 to 102 % load, mu / mu_ref 1.031 +/- 0.044, n 15; the as-built closure stalls on that line at 69.9-80.7 %; a friction share of at least 2.41 bar of the lift passes it, a fit (§CV.3-4). Book2's points: LT-329501 11 % at HV-322602 40 % (69.3 %), 1 % at 54 % (80.4 %). LT-329501 is not in the 5 November trends, so the level term is unfitted | Körting's 14 diagrams, order 2/131/4/04219. The lift prototype is held with B-118 (decision 180) |
| 2 | TT-322015's H2 hysteresis | I 22.1's release (B-56) | H2 110 C (the DCS readback, decision 103); hysteresis V1's 2 K, cleared below 108 C | the object display shows range 0-200 C, H1 100.0, H2 110.0, delay 0 and no hysteresis field (photograph of 24 October 2026) | checklist row 1: the engineering view of the limit; else the 2 K stand-in signed off |
| 3 | Körting's performance curves of 324F002, 324F004 and 324F005 | `ejector_map`, B-57's interpolation on the synthesized maps (§XLIX.4, §L.1) | synthesized maps, anchored on the PFD's design loads; in-situ factors 0.919, 0.336, 0.497 | one duty point an ejector; no curve in the archive (§XLVIII.2). The plant's motive break-off, the datum a curve must meet: HIC-329605 between 55 and 64 % (HIC-329606 38-40 %) at PT-329207 4.20-4.24 bar g, 5 November 2026 13:11-13:16, 75 % load; the engine's vacuum still holds there (§CV.5) | Körting, orders 2/115/4/09674 and 2/232/4/00503; checklist row 13: 324E002's and 324E005's cold-end and cooling-water temperatures for 5 November 13:00-13:30 |
| 4 | LT-324501's taps | LI-324501 between its taps (decision 33's class) | V1's holdup ratio (§L.4) | one 80 mm instrument on the barometric leg at EL +8495 (isometric UD-RL-100-MB-0180, item 22); no second connection drawn; the span cannot be weighed from the trends (§CV.7) | checklist row 11: LRV, URV and the reference connection; a walk-down |
| 5 | AC4 PC21's limits and elements: FY-322403's L2; PT-321211 / 221's L2; ST-321952 / 953's H2; the T elements' mode; the SR flip-flops' dominance; TRIP_84_8_FLAG1's L2 | trips 21.2, 21.8 and 21.10 (§LXV.6) | FY-322403's L2 V1's 5 %; PDY's L2 0.1 bar; the T elements on-delays; reset dominant; PT-321211 / 221, ST-321952 / 953 and TRIP_84_8 taken healthy | the limits are database entries; the scan does not resolve the timer symbol (UD-MR-G00-FF-0004 pages 5, 7, 20); TRIP_84_8 is the instrument air, two of PT-384207A / B / C below L2 (§LXXIII.2) | checklist rows 3 to 8, one readback session |
| 8 | LT-323503's L2 hysteresis | 323P008's restart (B-96) | trip below 5 %, restart at 7 %: the 2 % stand-in of 2026-10-15 (§LXVIII.2) | the faceplate confirms L2 5.0 %, H1 80.0 %, L1 20.0 %, delay 0 s; no hysteresis shown | checklist row 2; else the stand-in signed off |
| 9 | FIC-335405's row in the DCS tuning table | the loop on the plant's tuning (decisions 76, 77) | V1's 100 per t/h and 15 s | not in `References/Master_PID_Tuning_Constants.md`; not photographed; the trends log FT-335405 alone, its ratio to FT-335401 0.0046-0.0050 (§CV.7) | checklist row 9: the faceplate's tuning page, then decision 10's span conversion |
| 10 | LT-329505's tap elevations | LI-329505 between its taps (decision 33's class) | V1's holdup ratio; LV-329505 on Flowserve's trim (§LXVIII.5) | upper tap 324E001 / N5 at EL +15129; lower tap on the DN700 condensate pot at EL +10651 (isometric UD-RL-100-MB-0312): 4 478 mm apart. The loop summary prints 3 000 mm. The conflict is logged, not resolved (§CIII.5) | checklist row 10: the transmitter's LRV and URV decide which span its 0-100 % covers |
