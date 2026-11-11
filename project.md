# project.md — Urea Plant OTS, Version 1.1

**Working directory:** `D:\Work\Urea Simulator V1.1`
**Predecessor:** `E:\Simulator\Urea Simulation` (V1 — reference only, never edited from here; decision 165)
**Last updated:** 2026-11-11, session 97

This file is the project's state, read whole at every session start. It is rewritten in place, never
appended to; its ceiling is 150 lines (`CLAUDE.md` §3a). History lives in `docs/`.

---

## State

* **Built.** Phases 0 to 7 of the port are complete, 196 checklist items
  (`docs/history/phase-checklist.md`). The whole plant runs — units 321 to 329 and the parts of 335 V1
  models, 320K002 a boundary feed (decision 73) — on a headless engine with a single local console
  (decision 149). Every module under `ureasim/` is at or below 600 lines (decision 152).
* **Verified.** The design pin holds at 1750 MTPD, 100 % load. The load study verified 100 % on both
  objectives and 105 % on the steam objective; the engine holds no steady state below 100 % load or at
  110 to 115 % (sessions 78 and 80, As-Built Parts XCI and XCIII). That is handoff B-118.
* **Open.** `handoff.md`: Section A seven (A-31 to A-37), Section B nine (B-118 with B-120 folded in,
  and B-125 to B-132), Section C none, 8 open data gaps. Every data gap waits on a vendor curve or on
  one plant DCS readback session (`D:\Work\reports\DCS readback checklist.md`).
* **In hand.** B-118: the candidate bundle (P1, P4 and the 322F001 lift, decision 181) was verified in
  scratch on the five acceptance holds in session 95 (As-Built Part CVII). One hold passes, one is
  trip-free and out of band, three trip on 322E002's condensation collapse under P1. Options (a) and
  (b) are with the process engineer; `ureasim/` is as built.
* **Session 97** audited the committed engine read-only (As-Built Part CVIII): no critical finding, 15
  handoff items raised, none decided. Session 95's collapse is read as 322E002's feed N/C crossing 3.0
  on a recycle, and B-118's next steps are the scratch sequence E0 to E3 (§CVIII.9). No code and no
  relation changed. Suite: 2 154 passed, 5 862 skipped (V1 not mounted), none failed.

## Next free numbers

| Series | Next | Where it is written |
|---|---|---|
| Session | 98 | `docs/history/session-log.md` |
| Decision | 182 | `docs/decisions.md` |
| As-Built Part | CIX | the As-Built reference, appended at its end |
| Handoff Section A | A-38 | `handoff.md` |
| Handoff Sections B and C | B-133 | `handoff.md` |

A session that takes a number updates this table in the same edit. A side session claims its numbers
here before it writes anything else.

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
