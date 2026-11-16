# project.md — Urea Plant OTS, Version 1.1

**Working directory:** `D:\Work\Urea Simulator V1.1`
**Predecessor:** `E:\Simulator\Urea Simulation` (V1 — reference only, never edited from here; decision 165),
read from its copy `D:\Work\Urea Simulation V1` (decision 223); the files the suite reads are copied into
`Tests and Reports/tests/equivalence/v1_reference` (decision 210), so V1.1 runs and tests without V1
**Last updated:** 2026-11-16, session 121

This file is the project's state, read whole at every session start. It is rewritten in place, never
appended to; its ceiling is 150 lines (`CLAUDE.md` §3a). History lives in `docs/`.

---

## State

* **Built.** Phases 0 to 7 of the port are complete, 196 checklist items
  (`docs/history/phase-checklist.md`). The whole plant runs — units 321 to 329 and the parts of 335 V1
  models, 320K002 a boundary feed (decision 73) — on a headless engine with a single local console
  (decision 149). Every module under `ureasim/` is at or below 600 lines (decision 152). Trip 22.2 is removed
  (decision 189). The 335 melt header is computed on AC4 PC35.2 (decision 224), LV-324501A on a 1 s positioner lag
  and its sheet's 6.9 bar a inlet (decisions 236, 237); a restore opens it on the save's drain (decision 238).
  Trips 35.1, 35.3 and 35.4 act on the header as AC4 PC35 draws them (decision 228). LI-323502 reads between
  LT-323502's taps (decision 219), the first of B-156's seven. 21.2's pump timers run AC4's minutes (decision 229).
* **Verified.** The design pin holds at 1750 MTPD, 100 % load. The load study verified 100 % on both
  objectives and 105 % on the steam objective; the engine holds no steady state below 100 % load or at
  110 to 115 % (sessions 78 and 80, As-Built Parts XCI and XCIII). That is handoff B-118.
* **Open.** `handoff.md`: Section A three (A-57 to A-59), Section B eight (B-118 with B-120 folded in, B-125 to B-128,
  B-135, B-136 and B-156), Section C none, 12 open data gaps. Every data gap
  waits on a vendor document or on one plant DCS readback session (`Tests and Reports\reports\DCS readback checklist.md`).
* **Session 121** (Part CXXXI; decision 219). B-156's first unit: LI-323502 reads between LT-323502's taps on
  323D001's datasheet 11.10 m3, the design holdup 50 % to the bit, V1's ratio on a switch for the harnesses. The
  seed is identical at tick 1 and drifts after it (B-94), by at most 6e-5 by 600 s (decision 230, pinned).
  Scratch: `Tests and Reports\reports\Session_121_b156`.
* **Session 120** (Part CXXX; decisions 218 and 228). Every file the simulator uses lives in its folder; the suite,
  the reports and the scratch live in `Tests and Reports` sub-folders, and saved exercises in the git-ignored
  `exercises` (decision 218). Trips 35.1, 35.3 and 35.4 are built with four overrides on 324-1b; the seed's leaves
  are unchanged to the bit (decision 228, B-146 closed; stand-ins in data gaps 5 and 14). Researched, nothing built:
  the DCS's FFIC-321404 formula is sourced and checked on Book2 (B-128), the CO2 line stands 5 bar over the loop on
  the plant (B-135); A-58 and A-59 raised; then 21.2's pump timers moved to AC4's minutes (Part CXXXII).
* **Sessions 117 and 118** (Parts CXXVII, CXXVIII; decisions 210 to 214). V1.1 runs and tests without V1 (decision
  210, A-33 closed); the trend window has a CLEAR button; the archive was searched for the open gaps; 322P002's
  delivery is set by hand in the field (decision 212); B-145 closed as built (decision 213); the seven levels on V1's
  holdup ratio move to their nozzles unit by unit (decision 214, B-156). Research: `Tests and Reports\reports\Session_118_research`.
* **Session 119 closed A-38, A-40, A-41 and A-50** (Part CXXIX; decisions 215 to 217). `master` is pushed to its own repository.
  AC4's low-level stops of 328P002, 328P006, 328P007 and 335P001 are built on the process engineer's 5 % L2 with
  2 % hysteresis (decision 217, A-41); 328P007's service is kept as built (decision 215); the bad-sample test is
  restated on decision 186 (decision 216, A-40); A-38's run flags have tests; the azeotrope test asserts B-106 on
  window means three trees agree on (A-50); the engine's own sawtooth there is raised as A-57. The seed is unchanged to the bit. The
  suite: 8 355 tests, all passing (the whole suite, 8 353, before the review's fix and 335P001's test; their files rerun after). Scratch: `Tests and Reports\reports\Session_119_build`.
* **Session 116 built A-51's choice** (Part CXXVI; decisions 236 to 238): LV-324501A on a 1 s positioner lag inside
  the header solve (data gap 12) and its sheet's 6.9 bar a inlet; one header valve steps the header as the plant did
  on 5 November 2026; a restore opens LV-324501A on its drain. Scratch: `Tests and Reports\reports\Session_116_header`.
* **B-118 in scratch, sessions 99 to 112** (As-Built Parts CX to CXIX and CXXII). Session 99 ran the gap
  resolution plan (decisions 182 to 188). On bundle A 92.3 % passes decision 180's test and the low holds latch;
  B-126 (b)'s species holdup removes the low holds' latch and loses 92.3 % on the cold branch (session 103).
  Session 105 removed trip 22.2 (decision 189) and measured the load-reduction procedure (B-135, B-136). Session
  108 took 322R001's loop apart by path clamps; no candidate held. Session 112 measured two laws: B, the re-flash on
  the top's subcooling, lifts the reactor's rise; B with S (322E002 closed on its duty), on UA as built with the
  stripper's lean rise on, stands at 92.3 % (13.24 K); S alone moves nothing; at 69.3 % D1 stands only with 322E002
  pinned, and the top boils. The choice is the process engineer's (B-118). Runs: `Tests and Reports\reports\B118_s101` to
  `B118_s112`.
* **The console instructions of 2026-11-13** (sessions 106 and 109 to 111; Parts CXVI and CXIX to CXXI). Built:
  328-2's revised slide, 322-1's CO2 FEED panel (decisions 220, 221), START / STOP on every pump icon (decision
  222), V1 read from its copy on D: (decision 223). Session 111 built the melt header from the twelve header
  valves (the GRANULATION HEADERS panel on 324-1b), LV-324501A on 335P001's curve, LV-324501B and HV-335602, with
  PIC-335201 inside the solve and LIC-324501's X setting its set point (decisions 224 to 226; saves migrate), and
  a run state on the eight pump pairs that had none (decision 227), one commit each; its open items were closed
  by sessions 119 and 120.
  Scratch: `Tests and Reports\reports\Session_110_console`, `Session_111_console`.

## Next free numbers

| Series | Next | Where it is written |
|---|---|---|
| Session | 122 (121 taken by B-156's first unit, 2026-11-16) | `docs/history/session-log.md` |
| Decision | 231 (219 and 230 taken by session 121, 229 by session 120's A-58; 220 to 228 already taken) | `docs/decisions.md` |
| As-Built Part | CXXXIII (CXXXI taken by session 121, CXXXII by session 120's A-58) | the As-Built reference, appended at its end |
| Handoff Section A | A-60 | `handoff.md` |
| Handoff Sections B and C | B-157 | `handoff.md` |

A session that takes a number updates this table in the same edit. A side session claims its numbers
here before it writes anything else.

**Claimed ahead** (2026-11-13, session 106), so that the gap-closing sessions of the running series and
the console changes never meet on a number. A session of the running series skips what this row holds;
the console session uses only this row, cuts it to the numbers it used and marks them taken.

| Claimed for | Session | Decisions | As-Built Part | Handoff |
|---|---|---|---|---|
| the console changes of A-41 and B-137 (`Tests and Reports\reports\Session 110 plan prompt s106.md`) | 110, taken | 220 to 223, taken | CXX, taken | none taken |
| the console build, the melt header and the eight pump pairs (`Session 111 plan prompt s109.md`; claimed 2026-11-14, session 109) | 111, taken | 224 to 227, taken | CXXI, taken | B-145 and B-146, taken |
| B-118, 322R001's loop (`B-118 plan prompt s107.md`'s successor; 2026-11-13) | 108, taken | none taken | CXVIII, taken | none taken |
| B-118, the laws S and B in scratch (`Session 112 plan prompt s109.md`; claimed 2026-11-14, session 109) | 112, taken | none taken | CXXII, taken | none taken |
| B-118, the wave session 112 left (`Session 114 plan prompt s113.md`; claimed 2026-11-15, session 113) | 114 | 205 to 209 | CXXIV | A-52, B-150 to B-152 |
| the build: trips 35.1 / 35.3 / 35.4 (`Session 115 plan prompt s113.md`'s Track B; built by session 120) | 120, taken | 228, taken; 229 to 235 released | none taken; CXXV released | none taken; A-53 to A-55, B-153 to B-155 released |
| A-51, the melt header's step on a header valve (claimed 2026-11-15, session 113) | 116, taken | 236 to 238, taken | CXXVI, taken | A-56, taken |

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
| `tests/X`, and `D:\Work\reports\X`, before session 120 | `Tests and Reports/tests/X`, `Tests and Reports\reports\X` (decision 218) |
