# project.md — Urea Plant OTS, Version 1.1

**Working directory:** `D:\Work\Urea Simulator V1.1`
**Predecessor:** `E:\Simulator\Urea Simulation` (V1 — reference only, never edited from here; decision 165),
read from its copy `D:\Work\Urea Simulation V1` (decision 223); the files the suite reads are copied into
`Tests and Reports/tests/equivalence/v1_reference` (decision 210), so V1.1 runs and tests without V1
**Last updated:** 2026-11-18, session 131

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
* **Open.** `handoff.md`: Section A none, Section B four (B-118 with B-120 folded in, B-125, B-126 and B-136),
  Section C none, 9 open data gaps. Every data gap
  waits on a vendor document or on one plant DCS readback session (`Tests and Reports\reports\DCS readback checklist.md`).
* **Sessions 129 to 131** (Parts CXL to CXLIII; decisions 249, 250). The open gaps researched in the archive. Built: PC21's
  page-20 timers as ABB TOFF elements, 21.2 lost 5 min / 15 min / 5 s after its causes (decision 249), and FY-322403's trip
  at the schedule's 8 500 Nm3/h (decision 250). Session 131 checked another tool's closure dossier page by page: none of
  its 13 closures holds (§CXLIII.1); PC21's SR latches read reset-dominant with the trip on R, as built, and 321P002B's
  limits on Peroni's sheets, so row 5 keeps TRIP_84_8's L2 alone. Reports: `Tests and Reports\reports\Session_129_gaps`
  to `Session_131_dossier`.
* **Sessions 121 to 128** (Parts CXXXI, CXXXIII to CXXXIX; decisions 219, 230, 232 to 235, 239 to 248). B-156 closed:
  six levels between their taps, LT-329501 data gap 15; data gaps 2, 8 and 11 closed; 322P002's field delivery to
  FI-322402's 40 m3/h; FY-321404 on the DCS's formula; A-57, B-127, A-59, B-135 and A-60 closed as built. The gap
  surveys: `Tests and Reports\reports\Session_123_gaps`, `Session_128_gaps`.
* **Session 120** (Part CXXX; decisions 218 and 228). Every file the simulator uses lives in its folder; the suite,
  the reports and the scratch live in `Tests and Reports` sub-folders, and saved exercises in the git-ignored
  `exercises` (decision 218). Trips 35.1, 35.3 and 35.4 are built with four overrides on 324-1b; the seed's leaves
  are unchanged to the bit (decision 228, B-146 closed; stand-ins in data gaps 5 and 14). Researched, nothing built:
  the DCS's FFIC-321404 formula is sourced and checked on Book2 (B-128), the CO2 line stands 5 bar over the loop on
  the plant (B-135); A-58 and A-59 raised; then PC21's timers moved to AC4's minutes, A-58 closed (Part CXXXII).
* **Sessions 117 to 119** (Parts CXXVII to CXXIX; decisions 210 to 217). V1.1 runs and tests without V1 (decision 210);
  322P002's delivery set by hand (decision 212); the seven levels move to their nozzles unit by unit (decision 214,
  B-156); AC4's low-level stops on a 5 % L2 with 2 % hysteresis (decision 217); A-38, A-40, A-41 and A-50 closed.
  Scratch: `Tests and Reports\reports\Session_118_research`, `Session_119_build`.
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
  by sessions 119 and 120. Scratch: `Tests and Reports\reports\Session_110_console`, `Session_111_console`.

## Next free numbers

| Series | Next | Where it is written |
|---|---|---|
| Session | 132 | `docs/history/session-log.md` |
| Decision | 251 | `docs/decisions.md` |
| As-Built Part | CXLIV | the As-Built reference, appended at its end |
| Handoff Section A | A-61 | `handoff.md` |
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
