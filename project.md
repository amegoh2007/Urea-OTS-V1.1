# project.md — Urea Plant OTS, Version 1.2

**Working directory:** `D:\Work\Urea Simulator V1.2`, git branch `v1.2`, a copy of V1.1 at commit 5ddc107; V1.1
is kept unchanged as the version to return to (session 132)
**Predecessor:** `E:\Simulator\Urea Simulation` (V1 — reference only, never edited from here; decision 165),
read from its copy `D:\Work\Urea Simulation V1` (decision 223); the files the suite reads are copied into
`Tests and Reports/tests/equivalence/v1_reference` (decision 210), so V1.1 runs and tests without V1
**Last updated:** 2026-11-20, session 139

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
  Trips 35.1, 35.3 and 35.4 act on the header as AC4 PC35 draws them (decision 228). LI-323502, LI-323503 and
  LI-323501, LI-328503, LI-328505 and LI-328504 read between their taps (decisions 219, 233, 241, 243, 244, 246); B-156
  closed on those six, LT-329501 is data gap 15 (decision 248). PC21's timers run AC4's minutes (decisions 229, 231).
  FY-321404 is shown and set on the DCS's formula (decision 235).
* **Verified.** The design pin holds at 1750 MTPD, 100 % load. The load study verified 100 % on both
  objectives and 105 % on the steam objective; the engine holds no steady state below 100 % load or at
  110 to 115 % (sessions 78 and 80, As-Built Parts XCI and XCIII). That is handoff B-118.
* **Open.** `handoff.md`: Section A one (A-61), Section B five (B-118 with B-120 folded in, B-125, B-126, B-136 and
  B-157), Section C none, 5 open data gaps (1, 3, 10, 15, 17). Each waits on a vendor document (Körting) or on one plant
  DCS readback session (`Tests and Reports\reports\DCS readback checklist.md`).
* **Session 139** (Part CLI; decisions 280 to 282 on the rulings of 2026-11-20; nothing built). A-61's closing run
  keeps 335P001 running with no latch, but the header count hunts 6 <-> 7 (criterion 3 fails; A-61 open). No share
  fits Book2's rise under the boil cap; the thermowells read the seed's share at 94.2 %, not a datum (gap 17 open,
  row 30 on LIC-329504 / 503). 322E002's quench outlet sets its share. B-157's placed seed: a kick, not a cure.
* **Session 138** (Part CL; decisions 277 to 279; 276 rejected). On the engine's own 322R001 step the column has one
  stable fixed point at every load: the rise loss is its boundary, 322E002's gas-CO2 split first (data gap 17).
  Decision 259 is a paired test (278); the seed's own wander is B-157. A-62 closed (279).
* **Sessions 135 to 137** (Parts CXLVII to CXLIX; decisions 253 to 275). The manual's header-valve rule on the B-118
  rig (253); the refit picks V1's approach; no wave M arm stands; the T693b trace closed gap 16; the letters and the
  readback checklist made.
* **Session 133** (Part CXLV; decision 252, built on branch `v1.2-d252` and merged into `v1.2` after session 134's runs). LY-324501 built on AC4's formula over V1's level with Rosemount's LRV floor, the seed unchanged to the bit; at the design vacuum 335P001's L2 stop cannot act, kept as built (2026-11-19). Researched: 324F003's and the leg's drawings (232 kg at the plant's 50 %), the cooling-water lead ruled out, PT-323204's two decimals, the UF85 pumps' capacity, the Drive copy's hash. The session 114 scratch plan ran in session 134.
* **Session 132** (Part CXLIV; decision 251). V1.2 made; the separators' ejectors break on the 5 November bracket.
* **Sessions 129 to 131** (Parts CXL to CXLIII; decisions 249, 250). Built: PC21's page-20 timers as ABB TOFF elements
  (decision 249) and FY-322403's trip at 8 500 Nm3/h (decision 250); another tool's 13 closures checked, none holds.
* **Sessions 121 to 128** (Parts CXXXI, CXXXIII to CXXXIX; decisions 219, 230, 232 to 235, 239 to 248). B-156 closed;
  data gaps 2, 8, 11 closed; A-57, B-127, A-59, B-135, A-60 closed as built. Surveys: `Session_123_gaps`, `Session_128_gaps`.
* **Session 120** (Parts CXXX, CXXXII; decisions 218, 228). Every file the simulator uses lives in its folder, the
  suite, reports and scratch in `Tests and Reports` (decision 218). Trips 35.1, 35.3 and 35.4 built, the seed to the
  bit (decision 228; data gaps 5, 14). FFIC-321404's formula sourced (B-128); PC21's timers on AC4's minutes.
* **Sessions 117 to 119** (Parts CXXVII to CXXIX; decisions 210 to 217). V1.1 runs without V1 (decision 210); AC4's
  low-level stops on a 5 % L2 (decision 217); the levels to their nozzles (decision 214); A-38, A-40, A-41, A-50 closed.
* **B-118 in scratch, sessions 99 to 112 and 134** (As-Built Parts CX to CXIX, CXXII and CXLVI). Session 99 ran the
  gap resolution plan (decisions 182 to 188). On bundle A 92.3 % passes decision 180's test and the low holds latch;
  B-126 (b)'s species holdup removes the low holds' latch (session 103). Session 105 removed trip 22.2 (decision 189)
  and measured the load-reduction procedure (B-135, B-136). Session 112 measured the laws B (the re-flash on the top's
  subcooling) and S (322E002 closed on its duty). Session 134 ran session 114's plan on V1.2: S + B on UA as built
  settles at 92.3 % on every plant sign and stands on session 112's tree, on HEAD 0.02 K under D1's floor; no HEAD arm
  stands at any hold; Book2's UA exponent rings; every reduced-load HEAD arm stops 335P001 on LY-324501's L2 (A-61).
  The choice is the process engineer's (B-118). Runs: `Tests and Reports\reports\B118_s101` to `B118_s112`,
  `Session_134_b118`.
* **The console instructions of 2026-11-13** (sessions 106 and 109 to 111; Parts CXVI and CXIX to CXXI). Built:
  328-2's revised slide, 322-1's CO2 FEED panel (decisions 220, 221), START / STOP on every pump icon (decision
  222), V1 read from its copy on D: (decision 223). Session 111 built the melt header from the twelve header
  valves (the GRANULATION HEADERS panel on 324-1b), LV-324501A on 335P001's curve, LV-324501B and HV-335602, with
  PIC-335201 inside the solve and LIC-324501's X setting its set point (decisions 224 to 226; saves migrate), and
  a run state on the eight pump pairs that had none (decision 227), one commit each; its open items were closed
  by sessions 119 and 120. Scratch: `Tests and Reports\reports\Session_110_console`, `Session_111_console`.

## Next free numbers

| Series | Next | Where it is written |
|---|---|---|
| Session | 140 (139 taken 2026-11-20: the rulings as decisions 280-282, A-61's closing run, the reactor as 322E002's meter) | `docs/history/session-log.md` |
| Decision | 283 (253 to 267 taken by session 136; 268, 271 to 273 claimed by session 136, proposed, not taken; 269, 270, 274 and 275 taken by session 137; 276 rejected, 277 to 279 taken by session 138; 280 to 282 by session 139) | `docs/decisions.md` |
| As-Built Part | CLII (CLI taken by session 139) | the As-Built reference, appended at its end |
| Handoff Section A | A-63 (A-62 session 136's, closed by decision 279) | `handoff.md` |
| Handoff Sections B and C | B-158 (B-157 session 138's) | `handoff.md` |

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
