# project.md — Urea Plant OTS, Version 1.1

**Working directory:** `D:\Work\Urea Simulator V1.1`
**Predecessor:** `E:\Simulator\Urea Simulation` (V1 — reference only, never edited from here; decision 165),
read from its copy `D:\Work\Urea Simulation V1` (decision 223); the files the suite reads are copied into
`tests/equivalence/v1_reference` (decision 210), so V1.1 runs and tests without V1
**Last updated:** 2026-11-15, session 118

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
* **Verified.** The design pin holds at 1750 MTPD, 100 % load. The load study verified 100 % on both
  objectives and 105 % on the steam objective; the engine holds no steady state below 100 % load or at
  110 to 115 % (sessions 78 and 80, As-Built Parts XCI and XCIII). That is handoff B-118.
* **Open.** `handoff.md`: Section A four (A-38, A-40, A-41 and A-50), Section B eleven (B-118 with B-120
  folded in, B-125 to B-128, B-133, B-135, B-136, B-145, B-146 and B-156), Section C none, 10 open data gaps. Every data gap
  waits on a vendor document or on one plant DCS readback session (`D:\Work\reports\DCS readback checklist.md`).
* **Session 113 reviewed sessions 111 and 112** on their files (Part CXXIII; report and the plans for sessions 114
  and 115 in `D:\Work\reports`, `Sessions 111 and 112 review s113.md`). The full suite on HEAD 4593bb2: 8 156 passed,
  1 failed (A-40), none skipped. Session 112's 92.3 % S + B arms ring and were scored unsettled; the licensor's
  bubble point follows the system pressure, which the engine's reactor cap does not separate from the inerts'.
  328P007's run state contradicts P&ID 104 (A-41).
* **Sessions 117 and 118** (Parts CXXVII, CXXVIII; decisions 210, 211). V1.1 runs and tests without V1: the 38 V1
  files the suite reads are copied byte for byte into `tests/equivalence/v1_reference` with a SHA-256 manifest (A-33
  closed), and with the external tree blocked 8 324 of 8 325 tests pass (A-40 fails). The trend window has a CLEAR
  button; A-38's sixteen modules have unit tests. Session 118 searched the archive for the open gaps and closed none:
  Uhde's level-transmitter sheets confirm the six modelled tap spans and leave seven levels on V1's holdup ratio
  (B-156); Operating Manual III sets B-133's flow by hand at FI-322402; LV-324501B's 2 % floor is its sheet's 50:1
  (B-145); no set-point list, no KSB test and no positioner response time is in the archive. Research:
  `D:\Work\reports\Session_118_research`.
* **Session 116 built A-51's choice** (Part CXXVI; decisions 236, 237): LV-324501A follows PIC-335201 on a 1 s
  positioner lag inside the header solve (a stand-in, data gap 12) and takes its sheet's 6.9 bar a inlet. One header
  valve now steps the header as the plant did on 5 November 2026 (ratio within 0.004, PIC-335201's kick within 0.4 %).
  The seed moves PIC-335201's output and LV-324501A to 79.09 %. A restored exercise opens LV-324501A at the stroke
  that passes its drain, on the header it restores (decision 238; A-56 raised and closed).
  Scratch: `D:\Work\reports\Session_116_header`.
* **B-118 in scratch, sessions 99 to 112** (As-Built Parts CX to CXIX and CXXII). Session 99 ran the gap
  resolution plan (decisions 182 to 188). On bundle A 92.3 % passes decision 180's test and the low holds latch;
  B-126 (b)'s species holdup removes the low holds' latch and loses 92.3 % on the cold branch (session 103).
  Session 105 removed trip 22.2 (decision 189) and measured the load-reduction procedure (B-135, B-136). Session
  108 took 322R001's loop apart by path clamps; no candidate held. Session 112 measured two laws: B, the re-flash on
  the top's subcooling, lifts the reactor's rise; B with S (322E002 closed on its duty), on UA as built with the
  stripper's lean rise on, stands at 92.3 % (13.24 K); S alone moves nothing; at 69.3 % D1 stands only with 322E002
  pinned, and the top boils. The choice is the process engineer's (B-118). Runs: `D:\Work\reports\B118_s101` to
  `B118_s112`.
* **The console instructions of 2026-11-13** (sessions 106 and 109 to 111; Parts CXVI and CXIX to CXXI). Built:
  328-2's revised slide, 322-1's CO2 FEED panel (decisions 220, 221), START / STOP on every pump icon (decision
  222), V1 read from its copy on D: (decision 223). Session 111 built the melt header from the twelve header
  valves (the GRANULATION HEADERS panel on 324-1b), LV-324501A on 335P001's curve, LV-324501B and HV-335602, with
  PIC-335201 inside the solve and LIC-324501's X setting its set point (decisions 224 to 226; saves migrate), and
  a run state on the eight pump pairs that had none (decision 227), one commit each. Open from it: the four pairs'
  L2 stops and 328P007's service (A-41), LV-324501B's seat relay (B-145), 324F003's low-level protection (B-146).
  Scratch: `D:\Work\reports\Session_110_console`, `Session_111_console`.

## Next free numbers

| Series | Next | Where it is written |
|---|---|---|
| Session | 119 | `docs/history/session-log.md` |
| Decision | 212 | `docs/decisions.md` |
| As-Built Part | CXXIX | the As-Built reference, appended at its end |
| Handoff Section A | A-57 | `handoff.md` |
| Handoff Sections B and C | B-157 | `handoff.md` |

A session that takes a number updates this table in the same edit. A side session claims its numbers
here before it writes anything else.

**Claimed ahead** (2026-11-13, session 106), so that the gap-closing sessions of the running series and
the console changes never meet on a number. A session of the running series skips what this row holds;
the console session uses only this row, cuts it to the numbers it used and marks them taken.

| Claimed for | Session | Decisions | As-Built Part | Handoff |
|---|---|---|---|---|
| the console changes of A-41 and B-137 (`D:\Work\reports\Session 110 plan prompt s106.md`) | 110, taken | 220 to 223, taken | CXX, taken | none taken |
| the console build, the melt header and the eight pump pairs (`Session 111 plan prompt s109.md`; claimed 2026-11-14, session 109) | 111, taken | 224 to 227, taken | CXXI, taken | B-145 and B-146, taken |
| B-118, 322R001's loop (`B-118 plan prompt s107.md`'s successor; 2026-11-13) | 108, taken | none taken | CXVIII, taken | none taken |
| B-118, the laws S and B in scratch (`Session 112 plan prompt s109.md`; claimed 2026-11-14, session 109) | 112, taken | none taken | CXXII, taken | none taken |
| B-118, the wave session 112 left (`Session 114 plan prompt s113.md`; claimed 2026-11-15, session 113) | 114 | 205 to 209 | CXXIV | A-52, B-150 to B-152 |
| the build: trips 35.1 / 35.3 / 35.4, 328P007, A-38's flags, A-50 (`Session 115 plan prompt s113.md`; 2026-11-15) | 115 | 228 to 235 | CXXV | A-53 to A-55, B-153 to B-155 |
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
