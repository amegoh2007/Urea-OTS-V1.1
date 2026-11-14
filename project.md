# project.md — Urea Plant OTS, Version 1.1

**Working directory:** `D:\Work\Urea Simulator V1.1`
**Predecessor:** `E:\Simulator\Urea Simulation` (V1 — reference only, never edited from here; decision 165),
read from its copy `D:\Work\Urea Simulation V1` (decision 223)
**Last updated:** 2026-11-14, session 109

This file is the project's state, read whole at every session start. It is rewritten in place, never
appended to; its ceiling is 150 lines (`CLAUDE.md` §3a). History lives in `docs/`.

---

## State

* **Built.** Phases 0 to 7 of the port are complete, 196 checklist items
  (`docs/history/phase-checklist.md`). The whole plant runs — units 321 to 329 and the parts of 335 V1
  models, 320K002 a boundary feed (decision 73) — on a headless engine with a single local console
  (decision 149). Every module under `ureasim/` is at or below 600 lines (decision 152). Trip 22.2 is removed
  (decision 189).
* **Verified.** The design pin holds at 1750 MTPD, 100 % load. The load study verified 100 % on both
  objectives and 105 % on the steam objective; the engine holds no steady state below 100 % load or at
  110 to 115 % (sessions 78 and 80, As-Built Parts XCI and XCIII). That is handoff B-118.
* **Open.** `handoff.md`: Section A four (A-33, A-38, A-40 and A-41), Section B nine (B-118 with B-120 folded
  in, B-125 to B-128, B-133 and B-135 to B-137), Section C none, 8 open data gaps. Every data gap waits on a vendor curve or on one
  plant DCS readback session (`D:\Work\reports\DCS readback checklist.md`).
* **Session 99** executed the resolution plan (`D:\Work\reports\Open gaps resolution plan and Opus 5.5
  prompt s98.md`) on the process engineer's decision table (As-Built Part CX). Wave 1 closed A-31, A-32,
  A-34 to A-37 and B-132 (decisions 182 to 184; A-38 raised); Wave 2 built B-129 to B-131 as decided
  divergences, each on a harness switch, the seed identical on every leaf (decisions 185 to 187); Wave 3
  stopped at E0, which fails (B-118's next step is the process engineer's); Wave 4 had nothing decided to
  build; Wave 5 tabled the data gaps' stand-ins and drafted the checklist rows and the Körting request.
  Suite: 2 208 passed, 5 862 skipped (V1 not mounted), none failed (§CX.10).
* **B-118's scratch programme (sessions 100 to 103, As-Built Parts CXI to CXIV).** No file under `ureasim/`
  changed after session 99; A-39 closed; decision 188. On the tree with bundle A (§CXII.10): 92.3 % passes
  decision 180's test; 90.5 % trip-free, out of band 47 min; 74.4, 69.3 and 68.9 % latch. Session 103
  (§CXIV): B-126 (b), 322R001's species holdup in twelve compartments, removes the three low holds' latch
  (69.3 % passes on its band) but loses 92.3 % and latches 90.5 % on the cold branch, and AT-322701 sits
  below its clause while the seed's liquor washes out; E1eu, the ratio fixed, the trim's gain and slip gain 0
  change no verdict. The bundle is a build candidate, not built; the options are §CXIV.11's and the process
  engineer's. Runs: `D:\Work\reports\B118_s101`, `D:\Work\reports\B118_s103`.
  Suite: 2 212 passed, 5 862 skipped, none failed (18 min 01 s) (`E:` not mounted).
* **Session 105** (As-Built Part CXV) removed trip 22.2 (decision 189), the only build, and measured the
  plant's thirteen load-reduction steps in scratch under decision 190: L1, L6 and (bundle A) L3 are needed;
  L3 is not fulfilled (B-136); the L2 board loop as approved fails; criterion (e) is met on no engine. On the
  engine the CO2 line's SV32064 lifts before the loop's reliefs (B-135). The holdup bundle's cold branch at
  92.3 % follows 322E001's `g_hc` and is not L3's or the ramp rate's doing (B-126). Runs:
  `D:\Work\reports\B118_s105`. Suite on HEAD: 8 082 passed, 1 failed (A-40), none skipped.
* **Session 106** (As-Built Part CXVI) researched four console instructions of 2026-11-13 and built
  nothing: the CO2 feed control of 322-1, page 328-2's revised slide, START and STOP on every pump icon
  (A-41), the granulator's header valves and the melt header (B-137). The plan for the build, session 110
  (claimed below), is `D:\Work\reports\Session 110 plan prompt s106.md`.
* **Session 110** (As-Built Part CXX) built the console instructions up to their checkpoint: 328-2's revised
  slide (decision 221), 322-1's CO2 FEED panel stepping 320K002's demand (decision 220) and START / STOP on
  the five pump pairs with a run state (decision 222). The melt header (B-137) was measured in scratch and the
  eight pairs with no run state (A-41) surveyed; both are session 111's build (below).
  The tests and tools now read V1 from its copy on D:, drive E: no longer needed (decision 223).
  Scratch: `D:\Work\reports\Session_110_console`.
* **Session 108** (As-Built Part CXVIII) took B-118's reactor loop apart in scratch and built nothing. With the
  stripper's feed-deficit rise off, 322E002's saturation edge or V1's re-flash of 322R001's off-gas at the live
  pressure each loses 92.3 % alone; with the three paths pinned the top stands on its bubble point, as the seed's
  does, and falls 0.53 K a bar of the engine's shallow pressure turndown. At 69.3 % nothing stands, and 322E002's
  alternatives bracket the top (its own-feed UA loses it, its split on Book2's departures boils it). No candidate
  holds; the choice is the process engineer's (B-118). Runs: `D:\Work\reports\B118_s108`.
* **Session 109** (As-Built Part CXIX; a review, nothing built) read sessions 108 and 110 on their files and
  filed session 107's Part CXVII. The process engineer's notes of 2026-11-14 answer session 110's checkpoint: the
  melt header at 3.2 to 3.8 bar g with the headers following the load, LV-324501B returning the excess above
  3.8 bar g (AC4 PC35.2 as configured), the pump faceplates the field start and stop. For B-118: two laws
  session 108 did not run, 322E002 closed on its duty (S) and the re-flash on the top's subcooling (B). Plans:
  `D:\Work\reports\Session 111 plan prompt s109.md` (the console build) and `Session 112 plan prompt s109.md`.

## Next free numbers

| Series | Next | Where it is written |
|---|---|---|
| Session | 113 | `docs/history/session-log.md` |
| Decision | 205 | `docs/decisions.md` |
| As-Built Part | CXXIII | the As-Built reference, appended at its end |
| Handoff Section A | A-50 | `handoff.md` |
| Handoff Sections B and C | B-150 | `handoff.md` |

A session that takes a number updates this table in the same edit. A side session claims its numbers
here before it writes anything else.

**Claimed ahead** (2026-11-13, session 106), so that the gap-closing sessions of the running series and
the console changes never meet on a number. A session of the running series skips what this row holds;
the console session uses only this row, cuts it to the numbers it used and marks them taken.

| Claimed for | Session | Decisions | As-Built Part | Handoff |
|---|---|---|---|---|
| the console changes of A-41 and B-137 (`D:\Work\reports\Session 110 plan prompt s106.md`) | 110, taken | 220 to 223, taken | CXX, taken | none taken |
| the console build, the melt header and the eight pump pairs (`Session 111 plan prompt s109.md`; claimed 2026-11-14, session 109) | 111 | 224 to 239 | CXXI | A-45 to A-49, B-145 to B-149 |
| B-118, 322R001's loop (`B-118 plan prompt s107.md`'s successor; 2026-11-13) | 108, taken | none taken | CXVIII, taken | none taken |
| B-118, the laws S and B in scratch (`Session 112 plan prompt s109.md`; claimed 2026-11-14, session 109) | 112 | 197 to 204 | CXXII | A-42 to A-44, B-138 to B-144 |

---

## 1. What the software is

A dynamic **Operator Training Simulator** for a 1750 MTPD Stamicarbon-type CO2-stripping urea
plant (Helwan Fertilizers Company). It runs the synthesis loop, LP recirculation, desorption /
hydrolysis, evaporation and steam systems as a coupled, time-stepped dynamic model, and presents
them on ten DCS-replica HMI screens plus a multi-pen trend window.

It is a training tool, so the requirement is not steady-state accuracy alone — it is that the
**transients look and feel like the plant**: levels swell, pumps cavitate, vacuum breaks,
carbamate crystallises, and interlocks trip, at the right rates and for the right reasons.

### Plant scope modelled

| Section | Screen(s) | Principal equipment |
|---|---|---|
| NH3 pumping station | 321-1 | 321D003 feed drum, 321P002 A/B triplex pumps, NH3/CO2 ratio block |
| Urea synthesis (HP loop) | 322-1, 322-2 | 320K002 CO2 compressor (an automated boundary feed outside the simulation's scope, decision 73), 322E001 HP stripper, 322E002 HP carbamate condenser, 322R001 reactor, 322E003 HP scrubber, 322F001 HP ejector, HV-322604 inert purge |
| LP recirculation | 323-1, 323-2 | 323C003 rectifying column + 323E002, 323F004 flash tank, 323F010 pre-evaporator + 323E010, 323D002 urea solution tank, 323E003/323D001 LPCC, 323E011/323D011 LP carbamate condenser, 323P001 A/B |
| Desorption / hydrolysis | 328-1 | 323C005 / 328V001, 328D003 feed drum, 328E007 interchanger, 328C002 Desorber-I, 328C003 hydrolyser, 328C004 Desorber-II, 328D001 reflux drum |
| LP absorption | 328-2 | 322C001 two-bed packed absorber |
| Evaporation + finishing | 324-1, 324-1b | 324E001/324F001 Evap-I, 324E003/324F003 Evap-II, four-condenser vacuum train, UF85 injection (FFIC-335406) |
| Steam / utilities | 329-1 | MP and LP headers, steam drums, condensate, CCW chain |

---

## Phases

| Phase | Content | State |
|---|---|---|
| 0 | Workspace | done |
| 1 | Thermodynamic core (`ureasim/thermo`) | done |
| 2 | Core primitives (`ureasim/core`) | done |
| 3 | Control layer (`ureasim/control`) | done |
| 4 | Unit operations (`ureasim/units`) | done; closed with UF85 in session 55 |
| 5 | Engine and transport (`ureasim/engine`, `ureasim/net`) | done |
| 6 | HMI (`ureasim/hmi`) | done; single console since session 68 |
| 7 | Verification | checklist done; the turndown stays open as B-118 |

## Where the rest of this file went

Citations elsewhere keep their old form; this table resolves them.

| Citation | Now in |
|---|---|
| `project.md` §2, §3, §3.1 to §3.6 | `docs/architecture.md`, the same section numbers |
| `project.md` §4, the progress checklist | `docs/history/phase-checklist.md` (frozen) |
| `project.md` §4a, the session log | `docs/history/session-log.md` (append-only) |
| `project.md` decision N (§5) | `docs/decisions.md`, entry N |
| `Claude.md` §5 rule 7's classes | `docs/decided-classes.md` |
| `handoff.md` before session 96 | `docs/history/handoff-record-to-session-95.md` (frozen) |
