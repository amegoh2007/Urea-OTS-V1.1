# Session log

Moved verbatim from `project.md` on 2026-11-11 (session 96, `CLAUDE.md` section 3a). `project.md`'s status header as it stood at session 95,
then section 4a, sessions 1 to 95. Append-only: a new session adds one entry of at most 12 lines at
the end (`CLAUDE.md` section 3a). Never read it whole: `grep -n "^### Session" docs/history/session-log.md`
lists the entries, and the As-Built Part an entry names holds the detail.

---

## Status header as it stood at session 95


**Status:** Phases 1-5 complete (the engine serves the live plant to the consoles); Phase 6 (HMI) opened in session 41, its faceplates and the instructor's panel built in session 42, the trend window in session 43, the stream inspector and the display gaps in session 44; single-machine mode, the default (A-2 and A-8 deferred in session 44, closed in session 56); 320K002 an automated boundary feed outside the simulation's scope (session 46, decision 73); Phase 7 (verification) opened in sessions 45-46 — the transient runner built and its four scenarios run on both engines, the comparison with the process engineer; B-51 and B-83 decided and built, B-87 traced (session 47); B-86 to B-89, B-39, A-7, B-13 and B-82 decided and built, the cold start no longer flooding, the steady state at 1750 MTPD compared over every packet leaf, zero overlay overlap, 322E002's tube leak a malfunction (session 48); A-18, B-90, B-84, B-81,
B-85, B-28 and B-25 decided — FFIC-321404A / B built, the letdowns' lines two-phase, AI-329701 and
the malfunction's rate — PT-329201 on the loop's vapour inventory and trips 21.2 / 21.8 / 21.10 as
AC4 executes them, the Phase 7 scenarios re-run (session 49); B-91 (a) and the reactor's boiling cap
built, B-18, B-37 and B-20 decided and closed, trip 21.2's hand switches and AI-329701 on the
screens, the plant DCS's readback applied — the cold start reaches 79.7 bar a in 16 000 s, still
short of the start-up band (session 50); B-94 closed on PFD 734's departure form, the steady state
3080 of 3188, 322E003 on its own liquor and a full sump, 323P008's trip from AC4 PC23, B-95 closed
as designed, PV-329203 / 212 on Metso's trims, 329D001 read — the cold start at 136.04 bar g, 1.5 bar under the start-up band, its tau 1 305 s faster than the trend's (session 51); B-91 accepted, B-96 and B-79 closed — solid carbamate on Egan, Potts and Potts — PV-329202, PV-329208 and LV-329505 on their vendor trims (session 52); B-30 and B-22 decided and closed — 323E011 on its dew point, 323F010 on its live vacuum — A-6 closed, and every Metso valve the archive prints on its trim (session 53); B-31 decided and closed — every LP inlet at its producer's live temperature — A-13 closed on its audit, eight Section B and C items signed off and Section C empty (session 54); B-97 decided and closed — 708 at 324F002's adiabatic discharge temperature — UF85 (unit 335) dosing live, the physical plant complete and every console binding resolving, B-1, B-4 and B-12 signed off and Section B empty (session 55); A-8's section assignment signed off and A-2 closed on an optional station token, the multi-station deployment supported and the instructor's panel unpaused, `handoff.md`'s Sections A, B and C all empty (session 56); 323P003's low-level trip searched (none drawn) and its NPSH read, trip 21.2's hand switches typed and TRIP_84_8 traced to the instrument air, decision 95's buffering signed off; the archive searched for the open data gaps — 328D003's and 323D002's overflows traced, trip 21.2 shutting XV-322902 and XV-322903 as AC4 draws it (session 57); the software converted to a single-console simulator (decision 149), retiring the multi-station roles, the station token, the roster and section assignment (decisions 72, 124 and 125; session 68); the open data gaps searched again in both user folders and the archive, seven control valves wired on the vendor sheets found (decision 150) and 322E006 on PFD 28's cooling water (decision 151), four data-gap rows closed (session 69); every module under `ureasim/` split inside the 600-line target, the moved lines verbatim and re-exported, no relation touched (decision 152, session 70); an external report on five data-gap rows audited against the code, 322C001's head volume and the urea-melt Henry constant closed (decision 153, session 71); 322E001 on its 2,950-tube replacement (decision 154), the turnaround's plugged tubes derating 322E002, 322E003 and 323E010 (decision 155), five loops and AI-329701's range on the plant DCS's faceplates of 24 October 2026 (decision 156), `Scenarios6.docx` put to the plant (session 72); the plugged tubes' conductances re-anchored on the bundle in service (decision 157), LV-322501's failure case read tick by tick — SV32351 / SV32352 lift at their set (decision 158) — the vacuum bleeds kept on the 1750 MTPD basis (decision 159), TIC-328008 and FFIC-335406 on their faceplates (decision 160), the dynamic audits built and their one finding, B-117, signed off as built, `Scenarios6.docx` 47 of 71; Sections A, B and C empty, 11 data gaps open (sessions 73 and 74); the load range 70-115 % studied on the committed engine for the load-optimisation workbook (`D:\Work\Urea_Plant_Load_Optimization_70_to_115.xlsx`): 100 % verified on both objectives, the engine's turndown, 323F010's barometric leg and a stripper cut's loop oscillation raised as B-118 to B-120, no relation changed (sessions 75 and 76); the workbook retried on the process engineer's control document with HIC-322605 operated by hand: 100 % verified on both objectives, 105 % near-steady, the turndown unchanged, B-118 and B-119 updated and B-121 raised, no relation changed (session 77); a pasted analysis of B-118 to B-121 checked and measured as scratch patches, 105 % verified with FIC-328402 raised 10 %, two errors in session 77's record corrected, B-119 decided (b) and built — 323F010 draining on its own head through N2, its leg taller than any column the vacuum holds (decision 161) (session 78); B-122 decided (b) and built — 323F010's pressure step solved itself where its holdup boils (decision 162) — and closed, the dynamic audit's two restored for every node; B-121 traced to the LP section's vents, not unit 328; B-118's N/C excursion traced to the reactor's real feed and 322E003's vent to its saturation fraction; B-123 raised and signed off as built, V1's thermo memo kept (decision 163); the synthesis loop's harness kept on the linearised step (session 79); every controller and hand station given a load relation (72 entries) and the schedule run from 70 to 115 % on both objectives with slow supervisory trims, then re-held at 100-110 %: 100 % verified on both objectives and 105 % on the steam objective, no steady state below 100 % or at 110-115 %, B-118 and B-120 updated, FFIC-321404's ratio found on the engine's basis (the plant's 2.115 is 2.05 here); B-121 closed on option (a), PIC-323202 and the unit 328 pair operator moves (decision 164); the load-optimisation workbook rebuilt with the 72-entry schedule; the Sonnet + Opus advisor workflow added to `CLAUDE.md` (session 80); B-118's and B-120's narrowed option (b) measured at Book2's 92.3 and 111 % bands as scratch patches, neither band held and no relation changed. B-118: 322E001's overhead fraction flat on the ramp, the excursion an operator handles' effect, and 322E003's liquor hot on the tempered water. B-120: near the plant's 111 % level the H/C slip is small and 322E003 vents on the same hot liquor. The Phase 7 cold start was found tripping 22.2 on the committed engine (B-124). V1's source tree and the References archive were moved (A-24, CLAUDE.md §4) (session 81); A-24 closed, V1's source tree named at `E:\Simulator\Urea Simulation`, its boot pin's test and the stripper's equivalence run on it (decision 165, session 82); B-124 bisected to 15e66c2, 322E002's low-N/C branch (decisions 142, 147) taking the NH3-lean cold start to trip 22.2; B-118's and B-120's TT-322002 prototype measured at Book2's 92.3 and 111 % bands, no band held and no relation changed (session 82); B-124's evidence gathered and the full cold start run (the branch off: no trip 22.2, tau 1350 s, dead time 540 s, final 137.45 bar g, 322R001 at its funnel's lip from 6 420 s), 322E001's turndown traced at 92.3 %, 322E003 on the vendor's margin at 111 %, no band held and no relation changed (session 83); B-124 closed on option (a), 322E002's low-N/C branch kept and decision 110's cold-start record re-baselined on the committed engine (decision 168), the fill probe reading LT-322504's narrow band (36 % a full reactor at its lip; session 52's full at 8 000 s the band's top, the backup above the lip moved with 322E001's shell bound (decision 139, B-102, in 15e66c2): with it off LT-322504 peaks at 91.2 % at 7 740 s, while B-103/B-104 and the bundle alone do not restore it); FT-329403 found on stream 901 at the design point (60.85 t/h, Uhde's loop summary 60.8); B-118 and B-120 measured under active closed-loop trims, no band held, B-120's mode absent with V1's stripper slip off (session 86)
**Working directory:** `D:\Work\Urea Simulator V1.1`
**Predecessor:** `E:\Simulator\Urea Simulation` (V1 — reference only, never edited from here; at `D:\Work\Urea Simulation` until 2026-11-04, decision 165)
**Last updated:** 2026-11-07 (sessions 75 to 92; session 92, a side session of session 91 (As-Built Part CIV): B-118 re-run at Book2's 69.3 % dwell on the process engineer's three corrections, measurement only: all six arms trip 22.1 before the hold, 322R001 cooling to 156-160 C on the ramp, no relation changed, B-118 open; session 91 continued: decision 178 built, the nine conventional Neldiscs on Valmet's L-series rows, data gap 7 closed, 8 data gaps; decision 179, the dynamic audit applying decision 163 on 323F010; B-118 at Book2's 69.3 % dwell, both arms tripping 22.1 on the ramp; session 91 (As-Built Part CIII), on the process engineer's "resolve all open items": A-28 and A-30 built on option (a) and closed (decisions 172, 173); A-29 run on `E:` and closed, the pins decision 170 moved in 20 decided-equivalence tests re-pinned and the whole suite passing; trip 22.2 kept as the simulator's own protection and named so (decision 174, data gap 6 closed); 322E001's U closed by decision (decision 175, data gap 11 closed); B-120 option (b) measured (decision 176) and decided (b2), its gain set to 0 only with B-118's turndown change (decision 177); data gap 7's L1 table found on Valmet's site and proposed, not built; LT-329505's lower tap and LT-324501's tap traced; Section A empty, Section B one open (B-118), 9 data gaps; session 90, a side session of session 88, added the start-up intro's LOAD button, the plant started from a saved exercise (the repository's shipped `scenarios` or the instructor's own folder), decision 171, As-Built Part CII, and raised A-30; session 89 researched the routes to every open gap and built decision 170, the five balanced Neldiscs on Valmet's S-Disc table, As-Built Part CI; session 88 researched the load workbook's gaps, As-Built Part C, and took no decision; session 87 closed A-26 and A-27, decision 169, and raised A-28; session 86 closed B-124 on option (a), decision 168, and measured B-118 and B-120 under active closed-loop trims; session 84 attached the start-up intro and holds the plant until the operator presses 100% LOAD, decision 166; session 85 decided and closed its six open points, decision 167)

---

## 4a. Session log

### Session 1 — 2026-09-23

Delivered:

* The four governing documents.
* The layered package skeleton, entry point, requirements and test configuration.
* **V1-equivalence harness.** V1 modules load by explicit file path into a `v1_`-prefixed
  namespace, so both implementations run in one interpreter despite sharing module names.
* **Thermodynamic core, first three modules**, split from V1's single 778-line property
  file into six by concern. 412 equivalence assertions, all **bit-for-bit**.
* **Overlay converter**: 387 / 387 elements across ten screens, no coordinate retyped.
* **PyQt6 console, running**: ten image-backed screens, all eleven element types, tab bar,
  nav hotspots, screen menu, edit-layout mode with per-machine persistence, health LED.

Measured, not assumed:

* 420 tests pass.
* Overlay geometry: every element centred on its recorded point to within 0.5 px; five
  collisions, all inherited from V1 and pinned with their reasons (handoff A-7).
* Indicator boxes had to be **painted** rather than laid out — a Qt layout's size hint
  carries each child label's margins and inflated the box by about 20 px, creating
  collisions the drawing does not have.

Next:

* `thermo/extended_uniquac.py`, `vle.py`, `real_gas.py`, `service.py`, `empirical.py`.
* `docs/step_sim_dataflow.md` — the boundary-crossing variable table Phase 4 needs
  (handoff A-4).
* Decide handoff A-2 item 1 (single station vs. instructor + trainee stations) before the
  engine layer is written.

### Session 2 — 2026-09-23

**Decision taken: multi-station operation is required** (handoff A-2 item 1). That makes the
engine a headless server and every console a network client, so it landed before any engine
code was written rather than as a retrofit.

Delivered:

* `ureasim/net/protocol.py` — length-prefixed JSON framing, message kinds, three roles, and
  the command-authorisation table.
* `ureasim/net/server.py` — asyncio TCP server: one encode per snapshot fanned out to every
  station, audit broadcast, late-joiner catch-up, and snapshot-only back-pressure.
* `ureasim/hmi/bridge.py` — the console end on `QTcpSocket`, with reconnect backoff and a
  staleness watchdog that blanks the screen rather than freezing it.
* `run.py` — `server` / `station` / combined modes.
* Status bar now carries the granted role, the audit line and refusal reasons.

Structural consequence, and an improvement: `engine/bridge.py` imported Qt, which a headless
engine cannot. It moved to `hmi/bridge.py`, and `Claude.md` §1.3 now carries a one-command
check that nothing at or below `ureasim/net` imports PyQt6.

Measured, not assumed:

* 508 tests pass (88 new, covering framing, split frames, oversized-length refusal, role
  authorisation, fan-out, late joiners, audit, and engine-refusal pass-through).
* End to end with two real consoles against one server: a trainee's `trigger_fault` never
  reached the engine, the instructor's did, an engine interlock refusal arrived in the
  trainee's status bar with its reason, and both consoles showed the same live values.

One defect found only by running it: a `pyqtSignal` named `event` silently replaces
`QObject.event()`, the virtual Qt calls for every event delivery, and the process dies on
construction with no traceback. Renamed to `audit_event`, with the reason recorded at the
declaration.

Next:

* `thermo/extended_uniquac.py`, `vle.py`, `real_gas.py`, `service.py`, `empirical.py`.
* `docs/step_sim_dataflow.md` — the boundary-crossing variable table Phase 4 needs
  (handoff A-4).
* Decide handoff A-8 (command arbitration between trainee stations) before the instructor
  panel is built.

### Session 3 — 2026-09-23

**Decision taken: assign units per trainee** (handoff A-8).

Delivered:

* `ureasim/data/tags.py` — tag-to-section resolution, by pattern for generic commands and by
  table for V1's ~30 bespoke ones. Server-side enforcement, refusals naming the instrument,
  assignments keyed by station name so they survive a reconnect, and a fail-closed rule for
  any command that cannot be attributed.
* **Phase 1 complete.** The remaining thermodynamic modules: the neutral H2O/urea binary,
  the 1215-node activity grid, the liquor VLE, the SRK letdown, domain classification, the
  quantised memo, the K-value layer and the flash service, plus the anchored bulk-property
  layer and the design anchors it departs from.
* `tools/analyse_step_sim.py` and `docs/step_sim_dataflow.md` — the Phase 4 gate.

Measured, not assumed:

* 908 tests pass.
* The activity table builds 1215/1215 nodes and reproduces the documented validation exactly
  — 323C003 +6.1 %, 323F004 +15.0 %, 323F010 +1.8 % against the PFD.
* `k_ratio` returns **exactly 1.0** at its reference point for every stage tested, with no
  tolerance and no identity short-circuit. That is what keeps the licensor's HP split
  bit-exact.
* The HV-322604 purge lands at 94.8 C, a mean Joule-Thomson coefficient of 0.14 K/bar
  against the 0.55 constant it replaced — what a gas that is 69 mol% nitrogen actually does.
* `step_sim()`: 38 sections, 39 one-tick recycle tears, 232 same-tick couplings.

Two findings from running it:

* A dilute hot 328 liquor misses the flash's 40-sweep budget by one sweep — identical in V1.
  Handoff A-9.
* An earlier test liquor carrying 1.2 wt% dissolved nitrogen produced a bubble pressure of
  2000 bar and a non-monotone P(T). That was unphysical test data, not a model defect:
  permanent-gas Henry constants are of order 1e5 bar and real dissolved inerts are tens of
  ppm. It did demonstrate that the IAPWS G7-04 turning point is reproduced correctly, which
  is now its own test.

Next:

* Resolve the 232 same-tick couplings in `docs/step_sim_dataflow.md`, then begin Phase 2-3
  (`core/` primitives and the control layer) before the first unit operation.
* Decide handoff A-9 before the 328 units are wired.

### Session 4 — 2026-09-24

**Phase 2 complete, and the Phase 4 gate closed.**

Delivered:

* `ureasim/core` — eight modules: `numeric`, `units_of_measure`, `packet`, `transport`,
  `signal`, `node`, `stream`, `flowsheet`. Plus `data/process_routes.py` and the 323 design
  flow chain in `data/design_point.py`.
* `docs/coupling_resolution.md` — every one of the 125 process couplings resolved against
  V1's own code at the writing site, under seven dispositions.
* `tools/analyse_step_sim.py` now separates **process** couplings from **telemetry-only**
  ones by identifying the three publishing sections from the author's own banner text, and
  fails loudly if it cannot find them.
* `tests/equivalence/test_core_equivalence.py` (67 tests) and
  `tests/core/test_flowsheet.py`, `tests/docs/test_coupling_resolution.py`.

Measured, not assumed:

* 1001 tests pass in 2.0 s.
* The core layer agrees with V1 tick for tick, not merely at steady state: the transport
  FIFO, the three signal blocks and the published stream records are compared sample by
  sample across a 60 s step with mixed sub-step sizes.
* Of the 232 couplings, **107 are telemetry**: read only by the stream registry, the
  energy-closure audit or the off-network faceplate trims. They become snapshot fields and
  block no unit port.
* Of the remaining 125: 43 arguments, 25 result fields, 16 packet fields, 13 property-
  snapshot fields, 12 one-tick tears, 9 artefacts, 7 control outputs. (One of those seven,
  `phi_fwd`, was re-resolved to a RESULT in Session 6 when unit 321 was ported — see that
  log entry. The live counts are 26 and 6.)

Three findings from doing it:

* **The static map under-reports by eleven.** `m748_prev = s.tlag.get("R328_748",
  R328_C002_M748_DES)` is last tick's flow with a design default. The parser cannot see
  through a `.get()`, so eleven genuine recycle tears present as same-tick couplings.
  Handoff A-10 — they need named state fields in Phase 5, not a ported cache lookup.
* **Nine rows were never couplings.** `M_c003_pre` is the 323C003 inventory in one place and
  the 328C003 inventory in another; `p` is a nested closure's parameter colliding with the
  pump loop variable. Listed rather than filtered, so the claim stays checkable.
* **V1 has two atmospheric pressures and both are load bearing** — 1.013 in the engine,
  1.01325 on the screens. The first sets the SV-32201 relief at 161.013 bar a; the second is
  what every gauge reads. Both are ported under separate names. Handoff B-6.

Next:

* Phase 3 — the control layer. `valve.py` first, because `data/process_routes.py` and eleven
  of the resolved ARG rows are valve flows waiting on it.
* Decide handoff A-9 before the 328 units are wired.

### Session 5 — 2026-09-24

**Phase 3 complete: the whole control layer is ported and proven.**

Delivered — seven modules in `ureasim/control`, plus two additions below them:

| module | lines | what it carries |
|---|---|---|
| `valve.py` | 497 | IEC 60534-2-1 liquid and gas trim laws, the installed characteristic, both choke limits, the back-solved Cv, the anchored ratio forms the engine calls, gravity discharge, the non-return valve |
| `process_loop.py` | 345 | the engineering-unit I-PD loop and the flow loop around it, including the volumetric migration |
| `controller.py` | 461 | the per-cent-of-span faceplate controller with slew limiting, OOS and bumpless transfer |
| `machines.py` | 301 | polytropic head, the normalised centrifugal characteristic, surge and stonewall |
| `interlocks.py` | 218 | latching trips: plain, armed, reset-banded, self-clearing |
| `ratio.py` | 160 | the ratio master with external-reset feedback; the open-loop ratio demand |
| `relief.py` | 137 | API 520 Part I critical-flow relief capacity, anchored on a rated point |

* `core/node.py` gained `solve_node_pressure` — the bracketed supply-versus-branches balance.
  It went to `core`, not `control`, because it knows nothing about a compressor.
* `core/units_of_measure.py` gained `PA_PER_BAR` and `R_GAS_J_KMOL`.

Tests: `test_valve_equivalence.py`, `test_controller_equivalence.py`,
`test_process_loop_equivalence.py`, `test_machines_equivalence.py`,
`test_ratio_equivalence.py`, and `tests/control/test_interlocks.py`.

Measured, not assumed:

* **1631 tests pass in 2.7 s**, up from 1001.
* The valve and machine laws are asserted with `==`, not `approx`. They are the same
  expressions on the same operands, so they are the same bits; an `approx` would pass on a
  re-associated expression that walks a six-hour run off its anchor.
* Both controllers are compared **state for state at every tick** — output, set point and all
  three PV history slots — over 500-tick scenarios including mode changes, cascade, limits,
  failed transmitters and variable sub-steps down to 1e-8 s.
* The UF85 ratio cascade is rebuilt out of the rewrite's blocks and run beside V1's own
  `step_uf85_cascade`, matching on every published field tick for tick.

Four findings from doing it:

* **V1 has TWO controller implementations and uses both.** `backend/controllers.py` is a
  per-cent-of-span class used on SIC-321950 and SIC-321951; `main.py _ctrl_ipd` is an
  engineering-unit dict used on every other tag. They differ on the bad-PV band, on whether a
  bad PV drops the loop to MAN, on output slew limiting, on the OOS mode and on the Td = -1
  sentinel. Merging them would declare a 183 C reactor measurement failed and freeze the
  valve on a plant that is running normally. Both are ported, and the divergence is asserted
  from both sides.
* **`Td = -1` is a sentinel, not a number.** The DCS writes it to mean "derivative disabled";
  FIC-324401 carries it. Used as a gain it flips the sign of the derivative term and kicks the
  valve the wrong way on every transient. V1 guards it; so does the port, and a test pins it.
* **The check valve's bit-exactness has a precondition nobody had written down.**
  `w_des . sqrt(dp/ref)` returns the design flow exactly only when `p_up - p_down - p_crack`
  evaluates to the same float as `dp_des - p_crack`. Decimal plant pressures do not:
  5.60 - 4.20 is 1.4000000000000004, and the valve returns 37999.99999999999. Unit modules
  must therefore derive `dp_des_bar` as the subtraction of the two design pressures, never as
  a rounded decimal. Handoff **A-13**.
* **V1's liquid valve law uses two different FF conventions.** The absolute form holds FF at
  its 0.96 intercept; the anchored form the engine calls evaluates the full correlation
  `FF = 0.96 - 0.28.sqrt(Pv/Pc)`. At a 190 C liquor the two choke at different differentials.
  Both are ported unchanged and a test fails if they are ever harmonised.

`cascade.py` was not written, deliberately: V1 has no cascade block, and the wiring between a
primary and a secondary is the unit's. Recorded in the Phase 3 checklist so the absence reads
as a decision.

Next:

* Phase 4 — unit operations, starting with `feed/` (321D003, 321P002 A/B, the N/C ratio
  block), which is the section the control layer was built to serve.
* Decide handoff A-9 before the 328 units are wired, and A-13 before the first check valve is
  anchored.

### Session 6 — 2026-09-24

**Phase 4 opened: unit 321, the NH3 pumping station, is ported.**

Delivered:

| module | lines | what it carries |
|---|---|---|
| `units/feed/station.py` | 297 | the section step: N/C ratio cascade, both machines, the drum, the motive stream and its battery-limit transit |
| `units/feed/feed_drum.py` | 217 | 321D003 inventory, adiabatic energy balance, LIC-321501 makeup, PT / PY / PDYI instruments |
| `units/feed/pump.py` | 189 | 321P002 A/B triplex capacity, shaft power, motor current, the VOITH scoop |
| `data/unit_321.py` | 265 | every constant the section uses, each with its provenance |

* `thermo/empirical.py` gained `nh3_psat_bara` — the NIST Antoine ammonia vapour pressure,
  which sits directly under the 21.2 trip through the sub-cooling margin.
* `core/units_of_measure.py` is unchanged; unit 321 carries its own `G_SUCTION_HEAD`
  (see below).

Measured, not assumed:

* **1701 tests pass in 3.2 s**, up from 1631.
* The section is compared to V1 **field for field at every tick** — both pump flows, the
  motive stream, both anchoring fractions, the drum level, temperature and totalizer, both
  machine openings, the currents, the faceplate mode letters, all four instruments and the
  ratio PV — across 900-tick scenarios covering a swinging plant rate, an N/C set-point
  change, starting the standby machine, shutting both isolation valves, stopping both
  machines, and variable sub-steps down to 1e-8 s. **Every comparison is exact equality.**
* The design fixed point is exact: pump B at its derived design opening delivers exactly
  `EJ_MOTIVE_NH3_DES`, the drum level does not move at all, `phi_motive` is 1.0, and the
  cascade asks for the opening the machine already has.

Evidence standard, stated plainly. This is a MIXTURE and it is the best available:

* **executed V1 code** — the pump capacity law, the current proxy, the ammonia saturation
  curve, the transport-time law, the dead-time FIFO and the whole SIC-321950/951 controller
  are lifted by AST from `main.py`, or imported from `controllers.py`, and run.
* **transcribed wiring** — the roughly thirty assignment statements of `step_sim` that glue
  them together are copied line for line into the test's `_v1_feed_block`, because they live
  inside a 4,100-line function reading a plant state that only exists after `main.py` has
  built a FastAPI application. Tracked under handoff A-12 with the trip logic.

Three findings from doing it:

* **A resolved coupling was resolved wrongly.** `docs/coupling_resolution.md` had `phi_fwd`
  as CONTROL, "an ejector spindle / area ratio from HIC-322602". It is nothing of the kind:
  `phi_fwd = phi_m^2` where `phi_m = motive_nh3_kgh / EJ_MOTIVE_NH3_DES`, the affinity-law
  head fraction of the delivered motive flow. Re-resolved to RESULT and the summary counts
  corrected to 26 RESULT / 6 CONTROL. Found only because the port reached the section that
  writes it, which is an argument for porting section by section rather than in bulk.
* **V1 carries two gravity constants**, exactly as it carries two atmospheric pressures:
  9.81 in the 321D003 suction head, 9.80665 in `consequence.py`. The difference is 1.8e-5 bar
  at the design level and it feeds PDYI-321203/204, a 21.2 trip initiator. Both are ported
  under separate names. Handoff **B-7**.
* **The field-calibrated `PUMP_ETA_V` deliberately departs from the pump datasheet.** At
  eta_v = 0.95 the swept volume reproduces the datasheet's 67.1 and 82 m3/h to 0.3 %; at the
  field-calibrated 0.980 it passes 69.0 and 84.6. The datasheet agreement is the check that
  the GEOMETRY is right and belongs to the superseded efficiency — so the test pins the
  geometry, not the delivered flow, and the constant carries its own degeneracy caveat.

One file is over the 600-line target and stays that way on purpose:
`tests/equivalence/test_feed_equivalence.py` is 691 lines. Splitting it would duplicate the
AST-lifting harness that gives the file its whole value — one V1 namespace, one seeded state,
one transcription of the wiring — across two files that would then be able to drift apart.
It is well under the 800-line hard limit and is a test, not a module.

Next:

* `synthesis/` — 320K002 on its map into the capacitive discharge node, then 322E001,
  322E002, 322R001, 322E003 and the 322F001 ejector. The feed station already hands over the
  motive stream and the two anchoring fractions the ejector needs.
* Decide handoff A-9 before the 328 units are wired, and A-13 before the first check valve is
  anchored — the CO2 tie-in in `synthesis/` is the first one.

### Session 7 — 2026-09-25

**`synthesis/` opened: 320K002 and the CO2 discharge line are ported.**

Delivered:

| module | lines | what it carries |
|---|---|---|
| `units/synthesis/co2_line.py` | 347 | the capacitive discharge node, PIC-322203 and PV-322203, the XV-322902 tie-in and its check valve, the line dead time |
| `units/synthesis/co2_compressor.py` | 167 | 320K002 anchored on its polytropic map, and the speed governor that makes the open-loop map stable |
| `data/unit_320.py` | 187 | the feed composition and every constant of the compressor, the vent and the line |
| `units/synthesis/__init__.py` | 16 | package map |

`tests/equivalence/test_co2_line_equivalence.py` is 633 lines, for the same reason
`test_feed_equivalence.py` is 691: one AST-lifted V1 namespace, one seeded state, one
transcription of the wiring. Splitting it would duplicate the harness and let the halves
drift. Under the 800-line hard limit, and a test rather than a module.

The design point closes exactly. One tick from the design seed leaves `P = 144.2` bar a
unchanged, `feed = 54.618 t/h`, `vent = 0.0`, `load = 100.0 %` and `speed = 1.0` — a literal
zero node imbalance, not a small one. The derived anchors are `head_des = 320.37 kJ/kg` and
`q_in_des = 20568.62 m3/h`, against V1's stated 320.4.

Three things worth recording from doing it:

* **Handoff A-13 is followed at its first site, and that site proves nothing.** The rule
  written last session — a check valve's design differential must be derived as a subtraction
  of its two design pressures — is what V1 already does here:
  `CO2_DP_HP_DES = CO2_P_DES_BARA - SYN_P_DES_BARA`. But `144.2 - 140.7` evaluates to exactly
  `3.5`, so a literal would have been bit-exact too. The site follows the rule and does not
  test it. A-13 therefore stays open, which is the honest reading rather than the flattering
  one.
* **A latent defect in V1's vent controller is reproduced, not corrected.** PIC-322203 guards
  its increment against a bad PV but advances `pv_prev` regardless, so one non-finite line
  pressure poisons the next tick's proportional term, `du` comes out NaN, and V1's limiter
  turns a NaN into its upper bound. The vent latches wide open one tick after the measurement
  recovers. `Claude.md` §5 forbids improving a ported relation, so it is reproduced, tested
  from both sides against `ProcessLoop`, and logged as handoff **B-8** for the process
  engineer to decide.
* **Five of the failing tests were the test's fault, not the port's.** Every V1-versus-V1.1
  equality assertion passed on the first run. What failed were five expectations of mine about
  what the plant does — when isolation actually shuts, that a packed line resumes feeding after
  an over-pressure, that packing against a shut tie-in reaches surge when the vent opens first.
  Each was corrected to what the flowsheet does, not tuned until it passed.

`python -m pytest` — **1778 passed**, up from 1701 after the feed units. The headless grep over
`net`, `engine`, `units`, `control`, `core` and `thermo` still prints nothing.

**Then 322E001, the HP stripper — the first port proven wholly by EXECUTION.**

| module | lines | what it carries |
|---|---|---|
| `units/synthesis/stripper.py` | 594 | the component split, the four temperature drivers, the hydrodynamic flooding limit, both reaction rate laws and the per-species enthalpy balance |
| `data/unit_322e001.py` | 521 | the design feed and split, the licensor tube geometry, the flooding limit, the enthalpy constants, the sump and LV-322501 |
| `units/synthesis/hp_split.py` | 69 | the anchored K-value ratio every split in the 322 loop is moved by |
| `thermo/kinetics.py` | 80 | the Inoue-Otsuka urea-hydrolysis rate constant, which 328C003 will share |
| `data/unit_322r001.py` | 47 | three reactor design anchors the stripper's penalties need before the reactor is ported |

`core/stream.py` gained `mass_fractions_from_kmolh` and `thermo/kvalues.py` gained
`ratio_shift_frac`; both are V1 helpers that had no home yet and belong below the units.

**The evidence standard rose, and for a structural reason.** Unit 321 and the CO2 line are a
mixture of executed V1 correlations and transcribed `step_sim` wiring. The stripper's physics
is a module-level FUNCTION in V1, so it can be lifted whole: `tests/equivalence/v1_loader.py`
gained `lift()`, which takes a set of V1 names, walks the transitive closure of everything
they read, and executes just those statements out of `main.py` — which cannot be imported,
because importing it builds a FastAPI application and a plant state. Every assertion in
`test_stripper_equivalence.py` therefore compares V1's own bytes against V1.1's. The only part
not covered is the `step_sim` wiring, which belongs to the sump module and stays under A-12.

`lift()` is reusable and the next three units in this section will use it.

Three findings from doing it:

* **A latent issue in the bottom-temperature model, logged as handoff B-9.** Two saturating
  flood branches — steam dilution and hydrodynamic flooding — are each scaled on the same
  11 deg C reactor-liquor gap, and both code comments say they share that ceiling. The code
  ADDS them, so TT-322004 asymptotes to 194 deg C rather than 183. It is not unphysical (the
  shell is at 211.6 deg C and the hard `min(..., T_steam)` holds), but the two branches always
  co-activate because both are functions of the same feed mass, so it is what every flood
  excursion does rather than an edge case. Reproduced, tested from both sides, and left for
  the process engineer.
* **The hydraulic efficiency floor is unreachable.** `FLOOD_ETA_FLOOR = 0.50` is a guard, not
  an operating state: the knockdown is a ratio in which the feed mass cancels, so it saturates
  at about 0.93 however far the stripper is pushed. Recorded in the test so nobody reads the
  constant and expects a deep hydraulic collapse — that is `g_T`'s job.
* **Four of my own test expectations were wrong; every V1-versus-V1.1 assertion passed.** The
  flooding tests scaled the reactor overflow and forgot the CO2 sweep is part of the tube-side
  mass; the feed-spike ceiling is the shell and not the liquor (B-9); and a proportional
  turndown does NOT raise biuret per unit of urea, because concentration and residence time
  move together and cancel. What raises it is holding the sump up while throughput falls, and
  the corrected test says so.

`test_stripper_equivalence.py` reached 815 lines, over the 800-line hard limit, and was split
along the seam already in it: the equivalence file keeps what drives both implementations
(344 lines), and `tests/units/synthesis/test_stripper.py` takes what asserts the model's
behaviour (495 lines). The second needs no V1 tree, so it keeps running on a machine that has
only the rewrite. That is the split the `tests/` mirror rule wanted anyway, and it opens the
`tests/units/` tree the remaining Phase 4 sections will use.

`python -m pytest` — **1874 passed**, up from 1778 after the CO2 line.

Next:

* 322E001's bottom sump: LT-322501, LIC-322501, LV-322501, the bottoms transit lag and the
  sump energy balance. It needs `consequence.seal_fraction` and `consequence.blowthrough_kgh`,
  so those two go into `units/consequence/` as their own module first rather than being
  copied into the stripper.
* Then 322E002, 322R001, 322E003 and the 322F001 ejector — one unit at a time, per
  `Claude.md` §3.
* Decide handoff A-9 before the 328 units are wired, and B-9 before the stripper's bottom
  temperature is put on a screen. A-13 stays open until a check valve is anchored at a site
  that does not inherit the subtraction from V1.

### Session 8 — `units/consequence/` opened, and 322E001 finished

**Three quarters of V1's consequence layer is unreachable, and measuring that decided the
scope of this session.** `backend/consequence.py` is 640 lines of genuinely good generic
physics: a Souders-Brown carry-over departure, an NPSH margin knee, a urea and ammonium
carbamate solubility curve, a choked air-ingress orifice, and a one-call vessel block that
would give every level-controlled vessel the full set at once. Counting the call sites in
`main.py` gives this:

| function | call sites in V1 |
|---|---|
| `seal_fraction` | 3 |
| `blowthrough_kgh` | 3 |
| `gas_density_ideal` | 3 |
| `expansion_factor` | 0 — called only by `blowthrough_kgh` |
| `entrainment_carryover_kgh`, `pump_capacity_factor`, `npsh_available_m`, `urea_crystallization_T`, `carbamate_crystallization_T`, `liquor_crystallization_T`, `air_ingress_kgh`, `vessel_consequences`, `mushy_flow_factor` | **0** |

The three live functions serve LV-322501, LV-323501 and LV-323505 — the same event at three
drain valves, which is exactly the generalisation the module was written to achieve. The rest
was written ahead of its call sites and never wired.

So `units/consequence/` carries the reachable part and nothing else, per `Claude.md` §6. That
is not a judgement on the unported functions: the carry-over departure and the solubility
curve are better physics than what the units they were meant for currently contain, and they
should come back with the unit that needs them, at which point they get a call site and a
test. What must not happen is 500 lines of untestable generic physics entering the rewrite
because it existed in V1.

| module | lines | what it carries |
|---|---|---|
| `units/consequence/seal.py` | 234 | the seal ramp over a drain-nozzle bore, the IEC 60534 expansion factor and choke, the ideal-gas density and the blow-through law |
| `units/consequence/crystallisation.py` | 79 | the mushy-zone flow restriction, V1's `_f_flow` |
| `units/consequence/__init__.py` | 34 | package map and the design-anchor contract |

`consequence.py` also holds a second copy of the mushy-zone relation, and the two copies
differ on exactly one input: `main.py`'s `_f_flow` takes the engine limiter, so a NaN
temperature returns 1.0, and `consequence.mushy_flow_factor` takes the consequence-layer
limiter, so a NaN returns a NaN. Only the first is reachable. The rewrite ports the first and
`tests/equivalence/test_consequence_equivalence.py` asserts both behaviours, so the choice is
visible rather than incidental.

**Then 322E001's bottom sump, which completes the unit.**

| module | lines | what it carries |
|---|---|---|
| `units/synthesis/stripper_sump.py` | 482 | LIC-322501, the LV-322501 letdown law, the mushy-zone and seal restrictions, the bottoms transit, the LT-322501 mass balance and the sump energy balance |

Findings D-8, D-20, A-3, L3-1, L3-6 and L3-7 travel with it. Two constants were added to
`data/unit_322e001.py`: the 180 s stripper thermal time constant and the 0.7 letdown-flash
gain that sets TT-323001.

LIC-322501 is the only loop in V1 written as a velocity PI on the ERROR rather than on the
PV, so it is a third controller form and it stays local to the sump rather than becoming a
generic class in `control/`. With a constant set point it is arithmetically the direct-acting
I-PD the rest of the plant uses; the two separate the moment an operator moves the set point,
where this form gives a proportional kick out of the valve and the I-PD form gives none.

Three findings:

* **Handoff B-10, and it needs deciding before `recirc/` is written.** V1 writes the lagged
  TT-322004 into `s.tlag` under the key `"TT322004"` and reads it back one section later
  under `"TT_322004"`. The underscored key is never written, so the 323C003 letdown-flash
  duty has been running on the constant 172.0 C since the line was written, and the flash gas
  leaving 323C003 does not respond to how hot the stripper bottoms actually are. It is one of
  the eleven A-10 recycle tears, and the only one whose source never publishes — which is the
  strongest argument in the file for giving every tear a named state field.
* **A second A-13 site, and a failure mode adjacent to the one A-13 describes.** LV-322501 has
  two legitimate design differentials — 139.8 bar from the valve datasheet, and 136.7 bar
  between PT-329201 and the LP reference the law is normalised against. Both are subtractions,
  both are correct, and substituting one for the other moves the blow-through by 1.1 % while
  leaving every design-point assertion passing, because the ratio is 1.0 either way. Writing a
  differential as a subtraction is necessary and not sufficient; it has to be the right
  subtraction. Recorded under A-13.
* **In AUTO, this sump cannot blow through.** Emptying it drives LIC-322501's output to zero
  within a tick or two, so the valve shuts before the nozzle uncovers. Blow-through is a
  manual-mode or a saturation event, which is correct, and is also when it is most likely to
  happen on the plant. Pinned as a test, because it would otherwise look as though the D-20
  consequence had failed to wire up.

Four of my own test expectations were wrong again, and the pattern repeats last session's:
every V1-versus-V1.1 assertion passed first run, and the wrong ones were all claims about what
the model would DO. The output rails do not saturate on a level offset, because the loop
simply corrects it; the thermal lag is lazy-initialised, so it shows against a change and not
against a constant; the tracked error is one tick behind the published PV, which is the
declared tear; and the blow-through's choke removes the DOWNSTREAM pressure from the answer,
not the upstream one, so the rate still rises with the loop pressure — slightly faster than
linearly, because the compressibility falls as the loop is pushed up.

`python -m pytest` — **2308 passed**, up from 1874 after the stripper. `pyflakes` is clean over
the whole tree: the two dead bindings it had been reporting, an unused `h` in
`hmi/widgets/icons.py` and an unused `pathlib.Path` import in an equivalence test, are deleted
per `Claude.md` §1.9.

Next:

* 322E002, the HP carbamate condenser, then 322R001, 322E003 and the 322F001 ejector — one
  unit at a time, per `Claude.md` §3. All three remaining exchangers have their physics in
  module-level functions in V1, so `lift()` applies and they can be proven by execution.
* Decide handoff A-9 before the 328 units are wired, B-9 before the stripper's bottom
  temperature is put on a screen, and **B-10 before `recirc/` is written** — that one decides
  whether the 323 section's existing calibration still holds.

### Session 9 — 322F001, and why it came before 322E002

**The planned order was wrong, and reading 322E002 is what showed it.** The HP carbamate
condenser's tube-side feed is the stripper's top gas PLUS the ejector's discharge, and its
design anchor is a single call:

```python
_HPCC_DES = hpcc_322e002(stripper_322e001(...), ejector_322f001(...))
```

so 322E002 cannot be anchored without the ejector. Its shell conductance is back-solved the
same way — V1's `_pin_hpcc_ua` runs an 18 000-tick settle, but the UA line inside it uses a
SYNTHETIC single call at the reconciled design feed, not the settled state, so it is
computable at module scope once the ejector exists. 322F001 therefore went first. `Claude.md`
§3 says one unit at a time; it does not say which one, and the dependency does.

| module | lines | what it carries |
|---|---|---|
| `control/jet_pump.py` | 421 | the constant-area momentum closure, its single-root proof, the cavitation ceiling and the geometry back-solve |
| `data/unit_322f001.py` | 292 | the design duty, the PFD 116 motive composition, the reconciled 322E003 overflow, and the back-solved geometry |
| `units/synthesis/ejector.py` | 235 | the plant wiring: the spindle, the anchored forward call, the sump head, the block valve and the discharge heat balance |

`jet_pump` went to `control/` beside `machines`, not into `units/`, because it names no tag.
The layer's own docstring is the test: "nothing here knows which piece of equipment it is
attached to."

**Proven wholly by EXECUTION, both halves.** `backend/jet_pump.py` imports cleanly, so V1's
module object is compared function by function; `ejector_322f001` is a module-level function,
so it comes through `lift()`. There is no transcription anywhere in this unit, which makes it
the second port at the strong evidence standard after 322E001's bundle.

`lift()` gained one capability on the way: it now indexes every Name a module-level statement
BINDS, including tuple unpacking. V1 writes `EJ_CP_N, EJ_CP_C, EJ_CP_D = 4.74, 3.10, 3.50`,
and before this the three heat capacities were simply invisible to the lifter.

Design closure is bit-exact on all thirteen published fields and on all nineteen constants,
including the two that are the output of a 200-step bisection over a fixed-point inner solve:
the nozzle area 0.00021959110412042918 m2 and the throat area 0.0019814767245892343 m2.

**Three findings.**

* **Handoff B-11 — TT-322012 steps 140 C at the bottom of a motive rundown.** The flowing
  branch takes the discharge to 39.2 C (pure cold ammonia through a stalled pump) and the
  no-flow branch hands back 178.8 C (stagnant carbamate against the thermowell). Both are
  right for their own situation; the threshold between them is a microgram per hour. V1 gets
  away with it because the published tag carries a 120 s thermal lag, which the rewrite has
  not ported — the ejector is a pure function with nowhere to keep it. The finding and the
  missing lag are the same gap.
* **Handoff B-12 — the machine stalls at 91 % motive.** The jet develops 5.106 bar of shutoff
  head against a 4.2 bar design lift, so it runs within 10 % of its own limit: a 5 % ammonia
  shortfall halves the loop's circulation and a 9 % shortfall stops it. That is a strong claim
  about a single point of failure for the whole synthesis section, it replaces a fitted knee
  at 20-35 % motive that had nothing behind it, and it should be confirmed against plant
  experience before it is taught.
* **HV-322602's range is about 38:1, not the 2.15:1 the retired constant asserted.** Same
  cause as B-12: the machine sits close to its shutoff head, where capacity is a steep
  function of jet momentum. The spindle also runs BACKWARDS — closing it RAISES entrainment,
  because the motive is positive-displacement so the valve sets the jet velocity and not the
  mass flow. Pinned as a test, because an operator who treats it as a throttle gets the
  opposite of what they intend.

V1's own comment block for this machine carries stale geometry — b = 0.1085, a 50.8 mm throat,
15.0 m/s, a 4.988 bar shutoff, a 0.918 stall fraction — and a stale inert balance. All of it
predates the motive re-pin from 40 756 to 42 762 kg/h. The rewrite carries the computed values
(0.11082, 50.23 mm, 16.02 m/s, 5.106 bar, 0.907; CH4 4.00 and H2 2.12 kmol/h) and the
divergence is recorded under B-12 so nobody re-derives it.

One of my test expectations was wrong: I called a CO2 mass fraction of 0.30 a rich carbamate
when the design overflow is 0.397, so the component falls rather than rises. Every
V1-versus-V1.1 assertion passed first run.

`python -m pytest` — **2553 passed**, up from 2308 after the sump.

Next:

* **322E002, the HP carbamate condenser**, which is now unblocked. It is the most coupled unit
  in the section: an isothermal Rachford-Rice flash anchored on a measured split, a film
  relaxation that makes the split a dynamic state, an effectiveness-NTU quench against the
  shell, and a bubble-pressure telemetry path. Two of its inputs are whole-plant machinery
  that belongs to Phase 5 rather than to the unit — the Option-1 disturbance gate, which reads
  every exogenous operator handle, and `HPCC_NC_DES_LIVE`, which V1 captures at boot. Both
  need a decision on where they live before the unit is wired, and the unit can be ported and
  tested against V1 with them as arguments in the meantime.
* Then 322R001 and 322E003, which close the loop.
* Decide handoff A-9 before the 328 units are wired, B-9 before the stripper's bottom
  temperature is put on a screen, **B-10 before `recirc/` is written**, and B-12 before the
  ejector's stall margin is used in a training scenario.

### Session 10 — 322E002, the HP carbamate condenser

The most coupled unit in the section, and the one where the rewrite's layering earned its
keep: four separate pieces of physics stacked on one calibration, plus two whole-plant
mechanisms that had to be kept OUT of the unit.

| module | lines | what it carries |
|---|---|---|
| `units/synthesis/carbamate_condenser.py` | 507 | the calibrated split, the anchored Rachford-Rice flash, the film relaxation, the NTU quench, the duty split and the melt bubble pressure |
| `data/unit_322e002.py` | 189 | the measured split, the shell state, the carbamate exotherm, the flash slopes and the bubble-pressure calibration |

Proven wholly by EXECUTION — the third such unit. `hpcc_322e002`, `_hpcc_flash_split` and
`bubble_p_322e002` are all module-level functions, so all three come through `lift()`. All 26
published fields and all 17 constants agree with V1 to the bit, including the shell
conductance, which is the output of a logarithm over a design-feed evaluation.

**The shell conductance was the piece that looked blocked and was not.** V1 back-calculates it
inside `_pin_hpcc_ua`, which first settles the plant for 18 000 ticks — so it looked like a
Phase 5 dependency. Reading the routine shows the UA LINE does not use the settle at all: it
evaluates a SYNTHETIC single call at the reconciled design feed, because the settled attractor
has drifted off the reconciled N/C and H/C and pinning on it lands the design quench high.
Both of its inputs, the throughput and the adiabatic temperature, are feed properties
independent of UA and of the gate, so the whole thing resolves at module scope in one pass.
The `ua_kjhk=None` argument is what asks for that pass, and it is V1's `HPCC_UA is None`
branch expressed as a parameter instead of a global.

**Two whole-plant mechanisms stayed out of the unit, deliberately.**

* The **Option-1 disturbance gate** reads every exogenous operator and feed handle on the
  plant, so it is an engine object. It arrives here as a `gate` argument defaulting to 1.0.
  Its consequence is large enough to need a decision and is recorded as handoff **B-13**: at
  the published operating point the gate is 0, which means the flash, the film dynamics and
  the NTU quench are ALL inert and the condenser does not respond to its own shell. That is
  a deliberate fix for a loop whose gain exceeds 1 at the seed, and it is also a fidelity
  statement nobody has signed off on.
* **The bubble-pressure N/C anchor** is captured from a settled boot in V1. The rewrite takes
  it as an argument defaulting to the reactor-feed constant, which is V1's own pre-boot
  fallback, and the 0.1 % telemetry offset that produces is pinned by a test rather than left
  to be discovered.

**Three findings.**

* **Finding A-15 comes out clean, and now it is measurable.** V1 deleted an identity
  short-circuit that used to return the design split whenever the temperature and pressure
  were exactly the design ones, so the flash now CONVERGES to the calibration there instead.
  Measured, the residual is 7e-16 on CO2 and 8e-16 on NH3 — a few ulps. The point of the
  deletion was to make that number visible, and the rewrite's test asserts the convergence
  rather than the branch, so a later change to the K-value model would show up.
* **The equilibrium split really is as stiff as the comment says.** Measured across a 35 C
  band at the design feed, the CO2 split runs from below 0.02 at 155 C to above 0.99 at
  190 C. A pure equilibrium condenser would be unusable; that measurement is the whole
  justification for the film relaxation, and it is now a test rather than an assertion in
  a comment.
* **This unit is a reactor with a cooling jacket, not an exchanger with a reaction in it.**
  The carbamate exotherm is 62.0 MW of the 62.6 MW design duty — 99.1 % — and the sensible
  term is 0.6 MW. Worth having written down, because it says where to look when the duty
  moves and it explains why the LP header is coupled to the synthesis loop's composition
  rather than to its temperature.

`core/units_of_measure.py` gained `R_GAS_FITTED_J = 8.314`, the rounded constant V1's fitted
correlations were calibrated against. It had been duplicated at the biuret rate law and was
about to be duplicated twice more here; it now has one home, and `BIURET_R_GAS_J` keeps its
name and sources its value from it. The name says why the two gas constants are kept apart.

`python -m pytest` — **2784 passed**, up from 2553 after the ejector.

Next:

* **322R001, the urea reactor**, and then **322E003, the HP scrubber** — the last two units in
  the loop. The reactor brings `backend/reactor.py`, which is a real kinetics module and will
  need its own home in `thermo/` or beside it; the scrubber closes the recycle and produces
  the overflow vector `data/unit_322f001.py` currently carries as literals.
* HV-322604 after them, and then the section is complete.
* Decide handoff A-9 before the 328 units are wired, B-9 before the stripper's bottom
  temperature is put on a screen, **B-10 before `recirc/` is written**, B-12 before the
  ejector's stall margin is used in a scenario, and **B-13 before Phase 5 wires the loop** —
  that one decides whether the carbamate condenser responds to anything in normal operation.

### Session 11 — 322R001, the urea reactor

The biggest unit in the section and the only one that is a reactor. It arrived with V1's
`backend/reactor.py`, which is the one module V1 kept quarantined — no dependency on
`main.py` at all — so every relation in it could be compared by direct import rather than
through the lifter.

| module | lines | what it carries |
|---|---|---|
| `units/synthesis/reactor.py` | 516 | the component balance, the vapour disengagement, both analyser shifts, and the design pins |
| `units/synthesis/reactor_column.py` | 440 | the axial march: node volumes, the signed equilibrium extent, the urea PFR, biuret, the exotherm distribution |
| `units/synthesis/reactor_calibration.py` | 255 | the two back-solves, and the joint profile / pre-exponential fixed point |
| `units/synthesis/reactor_hydraulics.py` | 260 | melt density, level from holdup, the funnel weir, HV-322605's Kv table, the node energy RHS |
| `data/unit_322r001.py` | 445 | the two product vectors, the geometry, the four thermowells, the funnel, and the loop-coupling gains |

Proven wholly by EXECUTION, the fourth such unit and by some distance the largest: 204
equivalence tests, every one of them `==` on floats. Every design constant, both
back-solves, the jointly-solved axial profile, all four hydraulic relations and all 24
published fields of the unit agree with V1 to the bit, across sixteen operating points that
span both ratio drives, load turndown and overload, a drained and a flooded column, a cold
and a hot one, both valve extremes and a 45-bar pressure excursion.

**Three things moved to where they belong, and none of them is a physics change.**

* **The shared reaction chemistry** — the carbamate and dehydration enthalpies, their sum,
  the derived dehydration activation energy and the biuret activation energy — went to
  `thermo/kinetics.py`, with the three rate-law forms beside them. V1 wrote the same two
  enthalpies out three times, in three units of measure (`reactor.DH_CARB_JMOL`,
  `main.STRIP_DH_HYD_JMOL`, `main.R328_HYD_DH_KJMOL`), and 328C003 will want them a fourth.
  The rate laws take their back-solved pre-exponentials as ARGUMENTS, which is what keeps
  the module free of plant knowledge and what makes an uncalibrated call impossible to write
  rather than merely discouraged.
* **The fitted gas constant** moved down a layer, from `core/units_of_measure.py` to
  `thermo/parameters.py` beside the CODATA one, because `thermo.kinetics` now needs it and
  thermo must not import core. `core.units_of_measure.R_GAS_FITTED_J` re-exports it, so every
  existing call site is untouched. It matters: deriving the dehydration activation energy
  with the CODATA constant instead moves it 5.1 J/mol and the rate constant 0.13 %.
* **PFD stream 207** moved from `data/unit_322e001.py` to `data/unit_322r001.py`. It is the
  reactor's product before it is the stripper's feed, and the stripper's module already
  imported the reactor's design temperature, so the direction was already one-way. The local
  name `FEED_207_KMOLH` is kept and is now the same object.

**`anchored_split` was the missing shared primitive.** V1's `_anchored_split` has exactly one
call site — this unit's vapour disengagement — but it is the sibling of `ratio_shift_frac`,
which was ported into `thermo/kvalues.py` three sessions ago, and V1's own comment presents
the two as one algebra at two limits. It went beside it. The one thing it is worth stating,
because the algebra does not guarantee it: the calibrated split vector IS a fixed point of
its own Rachford-Rice re-solve. The phase ratio the splits imply need not be the root of the
K-values they back-solve to, and here it is, to 7e-16. That is measured in the unit suite
rather than asserted, and it is what lets the design point survive a live re-flash.

**One real defect, caught by the equivalence suite.** The unit imported the loop's design
pressure from `data/unit_322e001.P_DES_BARA`, which is the STRIPPER's 144.0 bar, not the
loop's 140.7. The reference pressure of the vapour disengagement's K-ratio was therefore
3.3 bar off, which moved the split and put the overflow CO2 1.3 % out. Nothing in the
rewrite's own behaviour tests would have caught it — the design point still looked
self-consistent. The V1 comparison caught it on the first run.

**Two findings, both about the calibration rather than the physics.**

* **B-14: the biuret rate constant is calibrated at a profile the reactor no longer runs.**
  The two-stage calibration re-solves the dehydration pre-exponential against the profile the
  energy balance settles on, and does not re-solve the biuret one. The profile is 2.75 C
  colder on the node mean than the seed the biuret constant was fitted at, which at
  85 kJ/mol is worth a factor of 1.15 — so the design biuret extent comes out **2.0737 kmol/h
  against the PFD's 2.414, 14.1 % low**, on the plant's principal product-quality
  specification. V1 has the same gap and covers it by re-running the whole calibration at
  boot. The obvious fix is to fold the biuret solve into the joint fixed point, where the
  final profile is already known and the solve is one closed-form division; that is a
  structural change to a ported relation, so it is recorded rather than made.
* **B-15: two design throughputs, on two density bases, 0.42 % apart.** The calibration
  divides the design overflow by the PFD's constant 990 kg/m3; the boot anchor divides it by
  the melt density at the column's own bulk temperature, 994.19. Residence time is throughput,
  so that is 0.28 % of urea extent — 1305.9 kmol/h against 1302.27, and 894.6 kmol/h of
  overflow CO2 against the published 897.7. V1 records the same mismatch and resolves it by
  re-calibrating at boot. Both entries are the same obligation stated twice: calibrate at
  whatever state the engine actually seeds.

**One thing V1 needs a pass for and the rewrite does not.** V1 derives the bulk melt
temperature, density and holdup against the import-time SEED profile — the holdup has to
exist before the energy balance can be solved — then replaces the profile twice and never
re-solves them, so its seeded holdup and its seeded profile are two design points 0.9 C
apart. V1 fixes that with a `_rederive_react_bulk_anchors()` pass whose docstring traces the
consequence: a 0.156 % level step on the first tick, straight into the conversion and from
there into TIC-329005's load term. Here the three are simply derived after the fixed point,
which needs no pass, and the equivalence test asserts against V1's POST-re-derive values.

**What was measured rather than carried.**

* **The conversion optimum is real and it is interior.** Held isothermal, the extent peaks at
  **201 C** and falls to two thirds of the peak by 250 C. It is not a fitted parabola — V1's
  superseded correlation used one, with a fitted curvature and a fitted optimum band — but an
  Arrhenius rate constant (1.98 /h at 183 C, 16.7 /h at 220 C) working against an exothermic
  overall equilibrium (Kov 0.698 at 183 C, 0.094 at 220 C).
* **The axial profile against the plant's own DCS trend is better than V1's comment claims.**
  Against the 1921-sample means in `References/Urea_NormalOp_29-06-2025_Trends.md` the model
  lands at **RMS 0.43 C**, worst error 0.59 C. V1's comment quotes 0.78 C and a profile of
  170.77 / 173.60 / 178.20 / 183.00, which the code no longer produces — those figures predate
  the joint solve. Re-measured and pinned by a test.
* **Turndown raises per-pass conversion, and the sign is the point.** 0.660 at 70 % load
  against 0.542 at design and 0.510 at 110 %. The wetted volume is set by geometry and level,
  not by flow, so less throughput is more residence time. V1 measured the opposite sign
  (0.541 at 70 %, 0.559 at 110 %) before the anchor's throughput scaling was added, and the
  scaling exists for exactly this reason.
* **This vessel is 136 tonnes of melt with a 45-minute residence time.** That single number
  is behind every complaint that the reactor is slow to answer, and it is now geometry rather
  than a time constant.

**What was NOT ported, and why.** V1's `reactor.py` still carries the whole superseded
Inoue-Kanai separable correlation — `inoue_kanai_X`, `conversion_factor`, `t_opt_c`,
`f_T_parabola`, `react_couple`, `X_DES_RAW` and the four coefficients they were fitted with.
Not one has a live call site left in `main.py`; the three remaining mentions are comments.
Nor do `node_heat_weights`, `node_tau_s` or `holdup_dmdt_kgph`, all of which `step_sim` now
inlines, nor `TANK_AREA_M2`, a default cross-section V1 labels ILLUSTRATIVE and which is
wrong (5.31 m2 against the real 6.835) but never used. Reachable-only, per §6 and the
`consequence.py` precedent. Two things survive the retired correlation and are carried in
`data/unit_322r001.py`: `X_INF`, the 0.9140 ceiling the equilibrium constant is anchored on,
and `X_DES`, the published 0.543 per-pass conversion.

The step_sim wiring — the recycle-inventory lag on the feed ratios, the Euler integration of
the four node temperatures and the holdup, the forward-carbamate pulse from the ejector, the
flood carryover to 322E003 and the LT-322504 narrow-band display — is engine work and stays
for Phase 5, as the ejector's instrument lag did. Every right-hand side it needs is in
`reactor_hydraulics.py`, so Phase 5 wires rather than derives. V1 divides it the same way.

`python -m pytest` — **3028 passed**, up from 2784 after the condenser.

Next:

* **322E003, the HP scrubber**, which closes the recycle: it consumes this unit's off-gas and
  produces the overflow vector `data/unit_322f001.py` currently carries as literals. Then
  HV-322604, and `synthesis/` is complete.
* Decide handoff A-9 before the 328 units are wired, B-9 before the stripper's bottom
  temperature is put on a screen, **B-10 before `recirc/` is written**, B-12 before the
  ejector's stall margin is used in a scenario, **B-13 before Phase 5 wires the loop**, and
  **B-14 and B-15 before Phase 5 seeds the plant** — those two decide whether the reactor
  makes the published amount of biuret and the published amount of urea.

### Session 12 — 322E003, the HP scrubber

The vessel that closes the recycle, and the one that decides how much ammonia the plant
throws away. Every module in this section now has its producer: the overflow vector
`data/unit_322f001.py` had been carrying as literals is derived here, and it comes out
**bit-exact against the literal** it replaces.

| module | lines | what it carries |
|---|---|---|
| `units/synthesis/scrubber.py` | 536 | the unit, the vent closure at its own vectors, the condensing temperature, the capacity gate, the sump level and the LT-329501 overlay |
| `data/unit_322e003.py` | 455 | the wash, the saturated vent, the three design streams, the shell-side duty and conductance, the sump and the swell |
| `thermo/splits.py` | 254 | NEW — the three split-movement primitives, extracted from `kvalues.py` |

Proven wholly by EXECUTION: **743 equivalence assertions**, every one `==` on floats. All 23
published fields and all 40 scalar constants and 7 design vectors agree with V1 to the bit,
over twenty-seven operating points — load turndown and overload, the loop pressure 128 to
151 bar a, hot and cold cooling water, the water halved and shut, the purge valve at both
stops, the analyser either side of its reference, a flooding and a full sump, both spindle
directions, the condensation capacity at 1, 0.5 and 0, a short and a surplus wash, a reactor
flood, and one case with all of them at once.

**`thermo/splits.py` exists now, and the reason is a scope statement rather than a line
count.** `saturated_inert_vent` is not a 322E003 relation — V1's own comment says the 324
vacuum condensers use the same closure — so it had to go below `units`. Putting it in
`kvalues.py`, whose stated scope is "K-values, the anchored ratio, and the bubble and dew
points", would have taken that file to 715 lines and made its docstring untrue. The three
split-movement functions are one family and they import nothing from the K-value block, so
the extraction was textual: `kvalues.py` 636 -> 499, `splits.py` 254, and `thermo/service.py`
was the only edit, because every consumer already reached them through the facade.

Which of the three a unit uses is a statement about the equipment, not a preference:

| function | the phase ratio is | the equipment |
|---|---|---|
| `ratio_shift_frac` | FIXED by something else | a stripping column, an absorber |
| `anchored_split` | FREE, and re-solved | a flash, a reactor top |
| `saturated_inert_vent` | irrelevant — the inerts fix the gas rate | a wash top, a vacuum condenser vent |

**The structural point of this unit is that the vent is SOLVED and the overflow is a
difference.** V1 originally pinned the overflow and let the vent close the balance, which
took the vent to 214.8 kmol/h at 44 mol % ammonia — 5901 kg/h against the published 1708. The
loop's design flows do not close to better than a couple of tonnes an hour and the vent is
the smallest stream in the section, so it absorbed all of it. Solving it from its own physics
puts it back on PFD 204 to 0.01 % and closes the unit per species by construction; the
published residual is a literal 0.0 and is never injected.

**What was measured rather than assumed.**

* **99.60 % ammonia recovery.** 1329.2 kmol/h into the tubes, 5.35 out with the vent — 91 kg/h
  against the 11 338 kg/h the reactor off-gas alone carried. That single number is why the
  equipment exists, and the vent it produces is 89.26 mol % inert.
* **A surplus wash absorbs nothing extra.** Over a 0.8 / 1.0 / 1.2 sweep the vent mass and the
  CO2 absorbed are the same float at all three; only the overflow grows, by 7383 kg/h per
  20 %. That is finding A-2's claim made measurable, against the 0.15 kmol-per-kmol
  absorption gain it replaced.
* **Losing the cooling turns the purge into the loop vent.** At zero condensation capacity the
  vent goes 1708 -> 22 355 kg/h, thirteen times design, carrying 665.7 kmol/h of ammonia — the
  whole of the reactor off-gas. A boundary mass balance cannot see any of it, because the
  vessel is inside the loop.
* **A flooding sump makes the cooling-water return colder.** TDY-329125 measures 15.0 K at
  normal level, 9.75 at 75 %, 4.50 at a full sump. An operator could read the falling rise as
  the duty easing; it is the duty dying.
* **The LT-329501 swell trap.** A sump actually holding 40 % displays at 58 % once
  condensation stops, hunting across 56 to 60 % — and it is draining while it reads high.
* **The condensation ceiling is a frequently active rail.** Design sits 6.2 C below it, and
  +7 % throughput, the purge valve below 24 % open, a 35 % stronger spindle or half the
  cooling water each reach it alone.

**Two findings, and one of them is the first genuine disagreement with a plant measurement.**

* **B-16: TT-322002's design pin is an ejector pseudo-temperature.** It is pinned at 178.8 C.
  PFD stream 206 says 165 C and the plant's own DCS reads 165.696 C over 1921 samples — the
  two sources agree with each other to 0.7 C and the model is 13.1 C from both. The number is
  V1's `EJ_T_SUCTION_C`, whose own comment says the carbamate heat of mixing is lumped into
  it: a legitimate enthalpy carrier for the ejector's discharge balance, not a thermowell
  reading. It is ported unchanged because the shell-side conductance is back-solved against
  it — at 165 C it would be 62.7 rather than 53.94 kW/K — and because directive 5.2 makes the
  anchoring part of the equation. It also eats the condensation ceiling's headroom, which is
  why 6.2 C is all there is.
* **B-17: the vent-top correlation overshoots the plant's trend by 23 C.** Driven at the
  plant's own means — HIC-322604 78.188 %, AY-322701 3.236, TIC-329005 84.459 C, PT-329201
  139.603 bar a — TT-322011 predicts 153.6 C against a measured 130.316. The plant's departure
  from the model's own zero is +16.3 C and the correlation produces +39.6, so the response is
  2.4x too strong and the ammonia-slip gain dominates the error. Both gains are calibrated
  rather than sourced, and no trend in `References/` moves either in isolation, so this one
  steady record cannot separate them. B-3 explains part of it and not all: at the settled melt
  N/C the prediction falls to 138.8 C, still 8.5 C high.

**Three things moved to their producer.** PFD stream 206 from `data/unit_322f001.py`; the loop
design pressure of 140.7 bar a from `data/unit_320.py`, which now re-exports it under V1's own
alias `SYN_P_DES_BARA` — V1 writes precisely the same assignment — so every call site is
untouched and the CO2 tie-in differential stays a bit-exact subtraction of one float; and
`react_nc_ratio`, which became `core/stream.py` `atom_ratio` with its atom maps and its
instrument span as arguments, so the core layer holds no plant data.

**What was NOT ported.** Four V1 constants in this block have no reader anywhere in V1:
`SCRUB_OFFGAS_MOL_DES` (the published 64.78 kmol/h, superseded by the derived vent total),
`SCRUB_CARB_KMOLH_DES_REF` (a frozen copy of the wash), and `SCRUB_CARB_T_C` /
`SCRUB_CARB_P_BARA` (the wash inlet state). Reachable-only, per §6 and the `consequence.py`
precedent. The FV-329409 and TV-329005 design openings and the two CCW controller tunings are
V1's too, but they belong to the 329 tempered-water loop rather than to this vessel and they
land with it.

The sump inventory ODE, the composition tear the ejector reads, the mushy-zone throttle on the
overflow and the PT-329201 pressure-building term are engine work and stay for Phase 5, as the
reactor's node temperatures did. Every right-hand side they need — `condensation_capacity`,
`sump_level_pct`, `lt_329501_indication` — is in this module, so Phase 5 wires rather than
derives.

`python -m pytest` — **3807 passed**, up from 3028 after the reactor.

Next:

* **HV-322604**, the inert-purge letdown, and `synthesis/` is complete. Its trim is already
  ported — `control/valve.py` `valve_gas_anchored` on an equal-percentage characteristic,
  choked at its own design point — and `thermo/real_gas.isenthalpic_letdown` does the outlet
  temperature, so the unit is the seat's hydraulic ceiling and the 322C001 boundary. The
  ceiling matters most in exactly the scenario above: the vessel offers thirteen times what a
  DN-24 / Kvs 2.1 trim was sized for, and what the seat cannot pass is retained upstream.
* Decide handoff A-9 before the 328 units are wired, B-9 before the stripper's bottom
  temperature is put on a screen, **B-10 before `recirc/` is written**, B-12 before the
  ejector's stall margin is used in a scenario, **B-13 before Phase 5 wires the loop**,
  **B-14 and B-15 before Phase 5 seeds the plant**, and **B-16 and B-17 before TT-322002 and
  TT-322011 go on a screen** — those two decide whether the scrubber's published temperatures
  are the plant's.

### Session 13 — four handoff decisions, and PIC-322203 re-pointed

No new unit this session. The process engineer decided four open handoff items, on a proposal
that arrived as a pasted review. Two parts of that proposal were adopted as written, and two
were rejected on evidence. The evidence is recorded here so the question is not reopened from
memory.

| item | proposal | decision | status |
|---|---|---|---|
| B-8 | fix the PIC-322203 latch before `recirc/` | adopted: install PIC-322203 as a `ProcessLoop` | **done, item closed** |
| B-10 | fix the TT-322004 typo before `recirc/` | adopted: `recirc/` reads the live value | decided; built with the 323 port |
| A-10 | converge the tears with Wegstein or Broyden before Phase 5 | **rejected**: keep V1's one-tick delay, seeds declared per unit | decided; built in Phase 5 |
| B-13 / B-14 | one global `USE_V1_LEGACY_CALIBRATION` flag | **rejected**: no global flag; decided in Phase 5 on a measurement | decided to defer |

**B-8, built.** `co2_line.VentPressureLoop` is gone. PIC-322203 is now
`co2_line.vent_pressure_loop()`, a `control.process_loop.ProcessLoop` with `act = -1`, seeded at
the design point. The line calls it with the measurement published at the end of the previous
tick, so the declared one-tick tear is unchanged. The set-point span it needed, [120, 175]
bar a, is V1's own and comes from the `pic_set` branch of `handle_cmd`; it is now in
`data/unit_320.py` with that source, and no value was invented.

* **On every finite measurement the loop is still V1's to the bit.** The equivalence test
  drives V1's transcribed block and the installed loop side by side over 500 ticks that cross
  the set point and drive the stroke onto both rails, and the whole-line comparison still
  asserts the stroke, the PV and the PV history every tick.
* **On a bad sample it now freezes for one tick and nothing else.** A new test proves the
  strong form: after the bad tick the loop is, to the bit, the loop that never saw the sample.
* **The divergence is asserted from both sides.** The old latch test is now
  `test_a_non_finite_line_pressure_no_longer_latches_the_vent_open`. It still drives V1 and
  still asserts V1's stroke going to 100.0, and it asserts the rewrite's staying at 0.0 beside
  it.
* **A correction to the record.** B-8, and my own summary of it to the process engineer, said
  the re-pointed loop would also get "the bad-PV demotion to MAN that every other loop has".
  That was wrong. `ProcessLoop` stays in its mode on a bad PV; demotion to MAN is the
  per-cent-of-span `Controller`'s behaviour. The benefit that was decided on, no latch, is
  unaffected. The As-Built §XVII.5 states the correct behaviour and claims no demotion.

B-8 is deleted from `handoff.md`, as that file's own rule requires, and its closure is recorded
in the As-Built reference, §XVII.5. The register gained a rule for this: a `[PORTED]` row may
carry a **decided divergence**, provided the row names it and the equivalence test asserts both
sides of it. Row 36 is the first such row.

**B-10: why it was adopted, and why it costs nothing at the validation point.** At the design
tick the sump publishes `tt_322004_c == 172.0` exactly, which is the constant V1's typo freezes
it at, and an existing test already asserts this. So the 323C003 calibration point and the
Phase 7 steady-state comparison do not move. Only off-design behaviour changes, and that is the
purpose.

**A-10: why the solver was rejected.** The eleven tears are not algebraic loops. Each is last
tick's value at a 0.1 s tick, and each feeds a holdup: `m702_prev` and `m756_prev`, for
instance, feed the 323C005 sump mass and its semi-implicit energy balance (V1 `main.py`
8846-8880). The holdup's capacity damps the coupling, and V1 runs stably on it. Converging the
tears inside the tick would remove the one-tick delay. That changes every transient that crosses
a tear, so the Phase 7 transient comparison could not pass by construction. It also would not
fix the one real runaway, B-13, which is a physical loop gain above 1. A relaxation factor is
added in Phase 5 only if a run shows a tear oscillating.

**B-13 / B-14: why the global flag was rejected.** B-13 already has its switch, the `gate`
argument, tested at both ends. A single global flag would tie the condenser's gate to the
reactor's kinetics, which are two unrelated decisions. B-14's V1 path, the re-calibration at
boot, cannot run until the engine exists. Both of its options land the design biuret extent on
the PFD's, so they may not differ at the validation point, and Phase 5 measures that before
choosing.

`python -m pytest` — **3809 passed** (3807 + 2: the set-point span test and the one-tick-cost
test). pyflakes clean; the headless grep prints nothing.

Next:

* **HV-322604**, the inert-purge letdown, and `synthesis/` is complete.
* Still undecided, with their gates: A-9 before the 328 units are wired, B-9 before the
  stripper's bottom temperature is put on a screen, B-12 before the ejector's stall margin is
  used in a scenario, B-15 before Phase 5 seeds the plant, and B-16 and B-17 before TT-322002
  and TT-322011 go on a screen.

### Session 14 — HV-322604, and `synthesis/` closed

The last unit in the section: the inert-purge letdown from 322E003 to the 322C001 LP
absorber, the loop's only inert exit. With it every stream `synthesis/` publishes has a
producer.

| module | lines | what it carries |
|---|---|---|
| `units/synthesis/purge_valve.py` | 270 | the choked law, the seat ceiling, the SRK outlet, the published capacity and the L3-7 deposition flag |
| `data/unit_322e003.py` | 505 | + the absorber pressure, the purge gas's ratio of specific heats and design molar mass, and the deposition threshold |

**Proven against BOTH of V1's copies of the law, by execution.** V1 carries it twice:
`hv_322604` in `main.py`, and `core/valve.py` `Valve322604.solve`, which is the copy
`step_sim` actually steps. V1's report D-2 records that the two once drifted apart, so the
test runs both. The class imports its constants with `from main import ...`, and `main.py`
cannot be imported, so the test installs a stand-in `main` module built from values `lift()`
executed out of the real file, for each test only. **391 equivalence tests, all `==`, all
first run:** ten published fields over 8 offered vents x 6 openings x 7 upstream pressures x
5 seat ceilings, the published capacity over 36 points, and the scrubber-to-valve chain over
ten operating points including the plant's own means. 27 behaviour tests, every number
measured before it was written down.

**The trim is now sourced from the vendor, not only from V1.** The Uhde documentation is in
the vendor archive, as two scans: the instrument specification (`UD-MR-G00-DZ-0042-001`) and
the CONVAL Cv calculation (`UD-MR-G00-DZ-0042-010`). They give equal percentage, Kvs 2.1,
Kv0/Kvs 2 %, xT 0.74, seat 8 mm, fail open. The vendor's Kv-against-stroke table reproduces
the ported law to its printed figures, so the trim V1 back-solved is the vendor's.

**Two findings.**

* **B-18: the anchor opening.** V1 anchors the characteristic at 50 % open, with no source.
  Sized on the vendor's own trim at the licensor's normal purge, the valve needs **72 %**;
  the plant runs it at **78.2 %**. My reproduction of the IEC choked form matches the vendor's
  own Kv at two of its points to 0.1 %, so the 72 % is not a method artefact. On an
  equal-percentage trim anchored at 50 %, the plant's opening passes **three times** the
  design purge. The same constant anchors 322E003's two vent-opening temperature terms, so
  the decision also bears on B-17. Ported unchanged, for the process engineer.
* **B-19: the letdown's solver floor.** The outlet temperature is a single-phase SRK solve on
  a bracket of the inlet -150 K to +20 K. In a cooling loss the purge turns ammonia-rich; from
  about 90 % capacity the answer is below the gas's own dew point, and from about 70 % there
  is no root and the routine returns the bracket floor, **-36.0 C**, as a temperature. V1 does
  the same. The number feeds the 322C001 energy balance, so this needs a decision before
  322C001 is ported.

**Measured behaviour worth keeping.**

* Choked down to 13.2 bar a upstream; above that the flow is exactly proportional to the
  upstream pressure and to sqrt(M/T), and the ratio of specific heats cancels.
* A cooling loss is retained, not vented: at zero capacity 322E003 offers 22 354.6 kg/h, the
  seat passes 1602.2 and 20.75 t/h stays in the loop. Without the ceiling it would vent
  20 966.6 kg/h and the excursion would vanish from a boundary balance.
* The first increment of travel passes 14 % of the design purge — the vendor's Kv0 — so the
  purge cannot be throttled below that except by shutting.
* The outlet is rounded to 0.1 C at source, ported deliberately, because V1's downstream
  physics consumes the rounded value.

**Not ported, per the reachable-only rule:** `_eq_pct` (nothing calls it), `SCRUB_HV604_RANGE`
(read only by `_eq_pct`, and equal to the trim's own 50) and `SCRUB_HV604_DP_DES` (no reader).

One correction to my own check, recorded because it nearly became a finding: V1's scrubber
returns a PINNED off-gas pressure, and I first read that as the valve never seeing the loop
pressure. `step_sim` overwrites it with the live loop pressure at `main.py` 8106, before the
valve is called. No finding; the port's docstring says so, so the next reader does not repeat
the mistake.

`python -m pytest` — **4227 passed** (3809 + 391 + 27). pyflakes clean; the headless grep
prints nothing.

Next:

* **`recirc/`**, starting with 323C003 / 323E002, the rectifying column and recirculation
  heater that receive the stripper bottoms through LV-322501. B-10 is decided — it reads the
  live TT-322004 — and B-4 (the 323C003 two-path pressure model) is its open calibration
  question.
* Still undecided, with their gates: A-9 before the 328 units are wired, B-9 before the
  stripper's bottom temperature is put on a screen, B-12 before the ejector's stall margin is
  used in a scenario, B-15 before Phase 5 seeds the plant, B-16 and B-17 before TT-322002 and
  TT-322011 go on a screen, **B-18 before HIC-322604 goes on a screen**, and **B-19 before
  322C001 is ported**.

### Session 15 — the urea-liquor stage layer, the first unit of `recirc/`

Mapping V1's unit-323 block showed that no 323 stage can be ported on its own. All five liquor
stages — 323C003, 323F004 and 323F010 here, 324E001 and 324E003 in the evaporation — stand on
one shared species layer (`main.py` 2340-2930): the bubble point, the vapour by relative
volatility, the design back-solve off the PFD rows, the biuret extent and the species advance.
So that layer is this session's unit, ported and proven on its own before 323C003 begins.

| module | lines | what it carries |
|---|---|---|
| `thermo/urea_liquor.py` | 361 | NEW — the liquor's own physics, plant-free, and the `LiquorStage` design record |
| `units/liquor_stage.py` | 205 | NEW — the runtime departures, biuret and the species advance, shared by 323 and 324 |
| `data/unit_323.py` | 172 | NEW — the PFD liquor rows, the design states and holdups, the three stage anchors |

**150 equivalence tests, `==` on every float, all numeric assertions first run.** V1's functions
are executed by `lift()` in two passes: V1 fills its design memos with bare module-level calls,
which `lift()` cannot execute, so the fixture makes those six calls with V1's exact arguments;
and `sol_biuret_xi` reads a `SOL_STAGES` whose 324 rows would pull in the whole unit-324 block,
so it is lifted second with the three 323 rows seeded. Both are declared in the test's docstring.
The one failure was the harness's, not the port's: V1 and the port refuse the same off-envelope
state, each with its own package's `OutOfDomain` class. 38 behaviour tests.

**Checked against the strict design basis, not taken from V1.** The five PFD liquor rows match
V1's transcription cell by cell. The 1.13 and 0.46 bar a stage pressures are sourced to the
323F004/323F010 description, not to the PFD's rounded 1.1 and 0.5. And formaldehyde's 32.031 —
CH2O is 30.026 — turned out to be the PFD's own molar-mass column, so it is the design basis's
number, not V1's, and it is kept.

**What was measured.**

* The rigorous bubble point sits 0.6 to 3.3 C under every PFD temperature, and Raoult-on-water
  33 and 16 C over it at the two stages carrying NH3 and CO2. Both cancel in the departure form,
  which is the whole reason it exists.
* **323C003's design seed is not stationary.** Its back-solve sends 8.16 kg/h of apparent urea
  overhead, the runtime zeroes urea's volatility, and the column accumulates it: 0.23 points of
  urea per hour on its holdup. V1 records the remainder and leaves it; so does the port. What it
  costs the settled column is measured when 323C003 is ported.
* On the frozen-vector fallback, the same apparent volatility lets a urea-only liquor at 323C003
  "boil" urea. V1 is identical. It needs a column that has left the envelope and lost its water.
* Biuret at 323C003: +10 C makes 82 % more; twice the holdup, twice; 10 % more urea, 21 % more.

**One structural change, not a physics change.** V1's two design memos and its `SOL_VLE_DOMAIN`
side-effect dictionary became fields of each stage's record and a returned value. The test
compares the returned domain against V1's dictionary after every call.

**One of my own mistakes, recorded.** While cleaning up test logs I ran `rm -f "$TEMP"/*.log`,
and `$TEMP` in this shell is the user's Windows temp folder, not the session scratchpad; any other
`.log` files at that folder's top level were removed with mine. Logs now go only to the
scratchpad.

`python -m pytest` — **4415 passed** (4227 + 150 + 38). pyflakes clean; the headless grep prints
nothing.

Next:

* **323C003 / 323E002**, the rectifying column and its steam heater: the TIC-323007 -> PIC-329202
  cascade, the steam chest, the energy-limited boil-up, the LV-323501 letdown with its seal, the
  drain transport to 323F004, and the PT-323201 two-path pressure model (V1's
  `c003_pressure_coupling.py`, handoff B-4). It reads the live TT-322004 (B-10, decided), and it
  is where the settled cost of the 8.16 kg/h urea remainder is measured.

### Session 16 — 323C003 and 323E002, stage 1 of unit 323

The rectifying column and its steam heater, on the liquor layer of session 15. Four things were
asked for with it, and all four are done: B-18 and B-19 moved into a new handoff **Section C —
Calibration Deferrals**; the column pressure modelled from both of its gas sources, explicitly;
the live TT-322004; and the 8.2 kg/h urea remainder monitored and its cost logged.

| module | lines | what it carries |
|---|---|---|
| `units/recirc/rectifying_column.py` | 486 | NEW — the column's mass, energy, species and pressure balances, the TIC-323007 -> PIC-329202 cascade, LIC-323501 and the LV-323501 seal |
| `units/steam_chest.py` | 146 | NEW — the condensing-steam chest every LP heater shares |
| `data/unit_323.py` | 314 | + the stage-1 design basis, the two gas sources' design rates, the three loops' tunings |
| `data/unit_329.py` | 31 | NEW — the LP header and the steam the valves pass |

**Proven tick by tick.** V1 writes stage 1 inline in `step_sim`, so its ~60 wiring statements are
transcribed into the test and everything they call is executed. Twelve scenarios — a feed cut
through the line's dead time, ammonia-rich bottoms, a sagging header, 323E003 backing up, the
stripper stopping, the steam valve shut, the column drained through its seal, a set-point step,
and all at once — compare every published field, the whole column state and all three loops with
`==` on every tick. 87 tests there, 257 more on the steam chest, 18 behaviour tests. Every numeric
assertion passed on the first run; the one harness fix was comparing V1's and the port's packets
by content, since they are different classes.

**The two gas sources.** PT-323201 is charged by stream 301, the stripper bottoms flashing across
LV-322501, and stream 302, the gas raised in 323E002. Each is its own ratio to its own design rate,
weighted by the PFD's own volumes (64 / 36 %), under one friction-head law to the 323E003 node —
V1's `c003_pressure_coupling.py`, ported bit-exact and commented source by source. Stream 305, the
outlet, is deliberately not a driver. Measured: the stripper flash alone holds 3.594 bar a, the
heater alone 3.332, both exactly 4.1. With the steam shut the stripper keeps the column at 3.618.

**TT-322004, live.** B-10 is built and closed: at 172.0 C the column is V1's to the bit, and off
design it now responds — 60 s at a stripper bottom of 160 / 172 / 180 C gives PT-323201 of
3.956 / 4.100 / 4.151 bar a, where V1 cannot see the stripper at all. Asserted from both sides;
recorded in As-Built §XXVIII.6.

**The urea remainder, measured — B-20.** Open loop, it moves the fixed point: about 6.8 kg/h of urea
goes down the drain instead of the overhead, +0.0033 wt% in the bottoms. Closed loop it does
something the open-loop number hides: TIC-323007 holds exactly 135.000 C, which needs slightly more
boil-up than V1's composition cap allows, the cap binds, and the column settles into a **limit
cycle — 267-268 s, +/-0.01 C, PV-329202 +/-0.1 %**. Attributed by opening the loop (the cycle
vanishes) and checked at three time steps. Tiny, and logged in Section C because the design point
is the thing that is not stationary.

**Two data questions surfaced and logged.** The 323E002 datasheet's steam state, "3.9 bar abs,
145 C", is not a saturated pair; V1 anchors on 3.96 bar a and the heater's conductance depends on
the choice (Open Data Gaps). And V1's comment on the overhead's latent heat, 645.6 kJ/kg, is stale
against its own expression, 1562.4; the expression is ported.

**B-4 rewritten to the ported code.** Its field residual was retired in V1's final coupling module
and its design-point ratio offset is gone under the cp departure form; what remains open is only
that the off-design gains have not been checked against a trend.

`python -m pytest` — **4777 passed** (4415 + 87 + 257 + 18). pyflakes clean; the headless grep
prints nothing.

Next:

* **323F004**, the flash tank: it owns the 323C003 -> 323F004 drain line, the isenthalpic flash to
  1.13 bar a, LIC-323505 and LV-323505, and its gas space with PIC-323203 and 323E011.

### Session 17 — 323F004, stage 2 of unit 323

The flash tank. Three things were asked for with it: V1's logic verified, the mass, energy and
composition balances handled properly, and the pressure coupling documented — whether the drum
pressure is fixed, floating, or set by a downstream condenser, and how the flash vapour is routed.

| module | lines | what it carries |
|---|---|---|
| `units/recirc/flash_tank.py` | 320 | NEW — the drum's mass, energy and species balances, the energy-limited flash to PFD 701, the drum pressure from the 323E011 node, LIC-323505 and the LV-323505 seal |
| `units/recirc/liquor_line.py` | 113 | NEW — `stream_cp` (moved from the column) and `receive_liquor`, the drain's arrival through the receiving stage's inlet line, shared by 323C003, 323F004 and next 323F010 |
| `units/recirc/rectifying_column.py` | 451 | uses `receive_liquor` for its feed; publishes its drain's departure state (`drain_t_c`, `drain_w`) instead of a packet |
| `data/unit_323.py` | 363 | + the stage-2 design basis: level span, LV-323505, PFD 319 density, cp and density anchors, q_701 and lambda_701, LIC-323505 |

**Two premises in the request were checked against V1 and the references, and both corrected.**
The flash vapour does not route through stream 302: 302 is 323C003's own heater gas, off
323C003's own pool, going to 323E003 with PFD 305. The drum's vapour is PFD 701 (4.43 t/h), and it
goes to the 323E011 flash condenser — a different condenser at a different pressure. And there is
no 323C004 in V1 or in `References/`; the downstream condenser is 323E011. The 323C003 docstring
said "the pool still flashes ... by the same path", which invited the misreading; it now says the
column's OWN pool, and that nothing from 323F004 enters the column.

**The pressure: floating, set downstream.** Nothing on the drum controls its pressure, and there
is no valve between the drum and 323E011. PIC-323203 holds 1.13 bar a on the condenser's VENT, and
the back-pressure acts across one gas space — drum, vapour line, 323E011 shell, 323D011 tank. So
the drum pressure IS the 323E011 / 323D011 node pressure, adopted at the end of each tick (V1's
explicit tear). 1.13 bar a is only the design anchor of the bubble point, the vapour departure
and the LV-323505 law. Measured: a node at 1.00 / 1.13 / 1.30 bar a settles the drum at
103.27 / 106.00 / 109.13 C and flashes 4843 / 4427 / 3949 kg/h — more back-pressure, a higher
bubble point, a smaller flash. V1's constant block still describes an older law (a target
pressure driven by the flash excess, with a 90 s lag) that V1 itself retired; it is not ported.
The session-16 note that 323F004 owns "its gas space with PIC-323203 and 323E011" was wrong on
the same point: that gas space is the 323E011 node, and it is ported with the LP carbamate
condenser.

**The balances.** The flash is energy-limited: the letdown's sensible surplus, less what walks the
drum to its bubble point. At design every bracket is exact and the drum is a fixed point for an
hour — no urea remainder here, unlike 323C003. m_701 leaves the drum's balance as vapour and is
published for the node, with the two blow-through corrections the node applies (column gas
through an uncovered LV-323501 in, drum vapour through an uncovered LV-323505 out).

**Proven tick by tick, and end to end.** V1's stage 2 is transcribed with the 323C003 -> 323F004
line; everything it calls is executed. Thirteen scenarios compare every published field, the
whole drum state and LIC-323505 with `==` every tick, and two more run V1's stage 1 into V1's
stage 2 against the ported column into the ported drum, which proves the drain interface. 31
equivalence tests, 13 behaviour, 7 on the liquor line. The 323C003 suite passes unchanged in
substance: it now compares the drain's departure state where it compared the packet.

**One V1 defect found — handoff B-21.** Writing "the drum runs dry when the column stops" as a
test failed: it does not. The product-line FIFO delays the flow rate along with the properties,
and a stopped carrier sends the dead time to its 1800 s cap, so the drum keeps receiving the full
design drain for half an hour — 52 959 kg from a line that holds 470 kg. Ordinary steps are off
too: a 25 % cut creates 157 kg, a 20 % rise destroys 79 kg. V1 is identical, the port reproduces
it, and it is pinned from both sides. The proposed correction — live flow, delayed properties —
is local and changes nothing at a settled state; it needs the process engineer's decision.

`python -m pytest` — **4828 passed** (4777 + 31 + 13 + 7). pyflakes clean; the headless grep
prints nothing.

Next:

* **323F010 / 323E010**, the pre-evaporator and its separator: it owns the 323F004 -> 323F010
  line (through `receive_liquor`), takes stream 331 as its cold second feed, the TIC-323012 ->
  PIC-329208 cascade on the 323E010 chest, the drum's LV-323505 blow-through into its vapour, and
  the PT-323204 vacuum with HV-323605.

### Session 18 — 323E010 / 323F010, stage 3 of unit 323, and the scheduler draft

The pre-evaporator. Three things were asked with it: that it use the shared liquor line, that the
coupling between the 323E010 steam chest and the 0.46 bar a separator be checked for hard-coded
assumptions, and that Phase 5's scheduler be outlined.

| module | lines | what it carries |
|---|---|---|
| `units/recirc/pre_evaporator.py` | 495 | NEW — the separator's mass, energy and species balances with PFD 331 as a second feed, the 323E010 chest under TIC-323012 -> PIC-329208, the PT-323204 vapour space on HV-323605, the barometric leg |
| `data/unit_323.py` | 481 | + the stage-3 design basis: geometry, latent heat, cp anchors, the 323E010 chest and conductance, HV-323605, the 324E002 design shell, the two controllers |

**The liquor line.** 323F010 owns the 323F004 -> 323F010 line and receives its feed through
`liquor_line.receive_liquor`, exactly as 323C003 and 323F004 do; the drum publishes only its
drain's departure state. It publishes its own product's departure state for 323D002 in turn. The
chained equivalence test runs V1's stages 1 to 3 against the ported three and matches every tick,
so the two drain interfaces are proven end to end.

**The chest and the vacuum: what V1 solves and what it pins.** Both pressures are SOLVED. The
323E010 chest is found every tick from valve admission against wall condensation, and sees the
separator only through the liquor temperature. PT-323204 is a molar vapour-space ODE on the
datasheet shell, stepped backward-Euler against HV-323605's compressible flow into the 324E002
shell (a 0.78 s node, verified). What is PINNED is the bubble point: V1 evaluates it on the design
0.46 bar a always (its TD-016). So the separator pressure reaches the barometric-leg drain, the
vapour composition and 323F004's LV-323505 — but not the boiling temperature, the chest's driving
difference or the evaporation.

**Three V1 physics gaps, measured and logged — each needs a decision:**

* **B-22 — the design-vacuum bubble point.** HV-323605 at 25 % puts PT-323204 at 0.768 bar a in a
  minute, where the liquor boils at 114.2 C; the model holds 99.06 C and keeps evaporating
  11.97 t/h until the barometric leg drains the separator dry at 1132 s. At 10 % the pressure sits
  on its 1.0 bar a clamp and vapour is destroyed. A scratch what-if on the live pressure did not
  oscillate on this stage alone and went the plant's way; the unit-324 loop V1 feared cannot be
  tested until unit 324 is ported.
* **B-23 — the chest anchor.** 1.76 bar a is not a datasheet value: V1 derived it as 40 % of a
  retired 4.4 bar a header and kept the number. PFD 926 says 2.5 bar a, 139 C, 11 230 kg/h. Design
  exact either way; the heater's off-design gain is not (UA 421 against 255 kW/K). 323E002's 3.96
  has the same origin.
* **B-24 — the evaporation cap.** `min(design split, duty)` is one-sided: less steam dilutes the
  product, but more steam, a higher TIC-323012 set point or a deeper vacuum superheats the liquor
  instead — 3.9 K at a 101 C set point, 16.4 K with PV-329208 at 45 % — and the product never passes
  80.00 %. Same structure as 323C003's cap in B-20.

The design seed also carries a 4.85 kg/h biuret remainder, the B-20 class; it is recorded there.

**The scheduler draft** is §3.6: V1's section order as a checked data schedule, three channels for
state (same-tick Result objects, top-of-tick unit state for backward reads, named TearState
fields), one-tick tears with no in-tick convergence per decision 8, and a fixed step. The fixed step
is new and is logged as handoff A-14: V1 steps on the wall clock, which makes every tear's delay
depend on machine load.

**Proof.** 57 equivalence tests (26 design constants, the barometric leg and HV-323605 with V1's
functions executed, fifteen tick-by-tick scenarios on the stage alone, three coupled to stage 2,
one through all three stages) and 13 behaviour tests. `python -m pytest` — **4898 passed**
(4828 + 57 + 13). pyflakes clean; the headless grep prints nothing.

Next:

* **323D002**, the two-compartment urea solution tank: it owns the 323F010 -> 323D002 line through
  `receive_liquor`, the LIC-323507 -> FIC-324401 cascade on FV-324401, the Comp I / Comp II baffle
  spill and the HV-323D002-TIE spool, and the LV-324501B recycle from unit 324 as a declared tear.

### Session 19 — 323D002, stage 4 of unit 323, and the handoff re-sorted

Three things were asked: move B-22, B-23 and B-24 into Section C, make A-14 an architectural law,
and port the two-compartment tank with a close look at how its compartments exchange liquor.

**The handoff.** B-22 to B-24 now sit in Section C (Calibration Deferrals) beside B-18 to B-20,
keeping their numbers; their "DECISION NEEDED" suffix is dropped, as Section C's items carry their
gate in the text. A-14 is DECIDED: the physics step is a fixed 0.1 s, written into `Claude.md` §1 as
rule 10, recorded below as decision 9 and in §3.6; the handoff item stays open until
`engine/simulator.py` builds it, as A-10 does. The `# Section B` heading, which had drifted above
A-10 to A-14, is back above B-1.

| module | lines | what it carries |
|---|---|---|
| `units/recirc/solution_tank.py` | 344 | NEW — the two compartments, the baffle spill, the tie-in spool, TI-323008, the blender species balance, LIC-323507 -> FIC-324401 -> FV-324401 with the FT-324401 lag |
| `data/unit_323.py` | 545 | + the stage-4 design basis: compartment volumes, the 10 % set point, FV-324401's design stroke, the two controllers, the transmitter lag |
| `data/design_point.py` | 131 | + the two unit-324 strengths unit 323 reads, `R324_W_IN` and `R324_W_EV2` |

**The liquor line.** 323D002 owns the 323F010 -> 323D002 line and receives the barometric-leg drain
through `liquor_line.receive_liquor`, as every stage before it does. Its own discharge departs with
the tank's state AFTER the tick — unit 324 reads the tank later in the same tick — so the
323D002 -> 324E001 line is unit 324's to own. The chained equivalence test now runs V1's stages 1
to 4 against the ported four and matches every tick.

**How the tank mixes — the answer to the watch-out.** No residence time is configured anywhere;
each compartment's is its holdup over its through-flow:

* **Compartment I is perfectly mixed** — one temperature, one composition, both the outlet's. At
  the 10 % set point it turns over in 357 s, set by LIC-323507, not by a constant; TI-323008 follows
  a product step on that time constant (93.68 C 357 s after a step from 99 to 90 C).
* **The baffle is an ideal sharp weir** at Compartment I's full volume on the LIVE density: the
  excess spills in the same tick, at Compartment I's composition from before the tick. No crest
  equation, no spill limit.
* **Compartment II is a perfectly mixed dead end** with the tie shut — no outlet, so an unbounded
  residence — with a composition but no temperature.
* **The tie-in spool makes one vessel in one tick** — an equal level fraction, an equal head, no
  spool hydraulics — with one pooled composition and one temperature. Opening it on a dry
  Compartment II drops LIC-323507 from 10 % to 2.1 %.
* **Plug flow lives only in the lines**, owned by the receiving units.

**Four V1 gaps, measured and logged:**

* **B-25 — no biuret in the tank.** The 10 % set point exists to limit biuret, and the tank forms
  none, so the set point carries no quality consequence. 323C003's kinetics would put 21 kg/h at
  10 % and 170 kg/h at 80 %, but they overstate the design point the PFD rows bound under 4.6 kg/h.
* **B-26 — the pump runs on an empty compartment.** FV-324401 at 60 % in MAN empties Compartment I
  in 1787 s and then creates 18.55 t/h. 323F010's leg had the same hole and V1 capped it.
* **B-27 — Compartment II's bookkeeping.** A full tank drops 128 t in 83 minutes with the pump
  stopped, Compartment II's mass fractions then sum to 1.37, and it has no temperature: stranded
  liquor joins the pool 1.6 K colder than its enthalpy says.
* **B-28 — the DCS deadband.** The tuning table gives every loop a 2 % deadband; V1 applies it on
  LIC-329505 alone. Logged in Section C as a tuning deferral.

Also found and fixed in comments only: V1's note that an unlagged FT-324401 puts the loop pole at
2.78 is Kc 1.5, an earlier tuning — at the present 0.4 it is -0.74; and `liquor_stage`'s docstring
credited 323F010 with 0.14 kmol/h of biuret, where its anchor has none (B-20). The design seed reads
LIC-323507 at 9.99996 %, because the normalised PFD row carries 80.0016 % urea against the density
anchor's 80.00; the loop takes back 0.03 kg. V1 is identical.

**Proof.** 25 equivalence tests (6 design constants, the unit-324 strengths and the flow span, the
controller and state seeds; ten tick-by-tick scenarios on the tank alone plus five more that force
the spill, the full tank, the part-filled tie, the dry compartment and FIC-324401 in AUTO; one
coupled to stage 3 and one through all four stages) and 9 behaviour tests. A deliberate mutation —
the spill carrying the post-tick composition — fails the baffle scenario. `python -m pytest` —
**4932 passed** (4898 + 25 + 9). pyflakes clean; the headless grep prints nothing.

Next:

* **The LP carbamate condensation side of unit 323** — 323E003 / 323D001 (the LPCC) and
  323E011 / 323D011 with PIC-323203 — which takes the two gas streams the liquor stages publish,
  323C003's PFD 305 and 323F004's PFD 701, and closes the pressure node the flash tank reads.

### Session 20 — 323D002's books closed, and 323E011 / 323D011, the LP flash gas node

Three things were asked: report the last suite and implement the B-26 / B-27 corrections in
323D002; name the next unit of `recirc/` and survey it; and, with the port of the LP carbamate
section authorised, document how PIC-323203 sets the back-pressure of the whole upstream gas space
and log V1's caps and floors on carbamate condensation as calibration deferrals. The request
arrived as pasted text only; the process engineer confirmed it before any physics changed, and
chose the Compartment II temperature with the two mass corrections.

**The suite.** Session 19's last run: 4932 passed, exit 0.

**323D002: a decided divergence (2026-09-27, handoffs B-26 and B-27 closed and deleted).**

| item | V1 | the port, from 2026-09-27 |
|---|---|---|
| B-26, the pump | FV-324401's flow whatever the tank holds; the 1 kg floor made the difference — 9.3 t in an hour at 60 % | capped at the liquid above a 1 kg heel plus what arrives; a loss-of-suction flag; FT-324401 reads the flow delivered |
| B-27, a full tank | the excess clamped away — 128 t in 83 minutes | the same holdups, the excess published as an overflow stream |
| B-27, the blend | divided by the clamped holdup — the fractions summed to 1.37 | divided by the holdup before the overflow — they sum to one |
| B-27, the temperature | none for Compartment II; the pool took Compartment I's | Compartment II charged with each spill; the pool starts from the enthalpy balance |

Every change is inert until its limit, so every V1 scenario stayed bit-exact; four new tests assert
both sides at the limits. The heel matters: a cap "at the liquid present plus what arrives", the
form V1 gave 323F010's leg (report A-17), counts the floor's kilogram as drainable, and the floor
then restores it every tick — 36 t/h. That is exactly what 323F010 still does: measured with its
drain stopped, the leg delivers 28 to 39 t/h from an empty separator, 98 t created in 3 h. Logged
as **B-29**, not changed.

**The next unit.** Yes — 323E011, the "Flash Tank Condenser" of the datasheets, with 323D011, its
level tank; V1 calls it the LP carbamate condenser. V1 steps the LPCC (323E003 / 323D001, its
stage 8) before it (stage 9), but the two are one pair — the LPCC vents into this node and this
node returns 718B to the LPCC — and this node is the one the ported 323F004 already rides, so it
was ported first.

| module | lines | what it carries |
|---|---|---|
| `units/recirc/flash_condenser.py` | 384 | NEW — the gas node, PV-323203's law and the vent generation, the tank, LIC-323503, FIC-323418 and the 718A remainder, TT-323011 |
| `data/unit_323e011.py` | 269 | NEW — the PFD flows and their closure, the capacity, the envelope geometry, the duty, the three controllers |
| `units/recirc/solution_tank.py` | 429 | the decided divergence |

**The pressure watch-out — the answer.** 323E011 condenses a CONSTANT, 5589 kg/h; only gas above
it is generated into the node, and PV-323203 vents on a square-root law against a 1.0 bar a
absorber. So above the capacity the node settles at P = 1.0 + 0.13 (25 (G - 5589) / (440 h))^2 —
1.13 bar a is h = 25 % against 440 kg/h, 1.81 at 10 %, 1.03 at 50 % — in seconds (4.4 s at
design); below it the condenser has no equilibrium at all. What holds the node is 323F004: it takes
the node's pressure one tick later, and a lower node flashes more, about 2800 kg/h per bar against
the vent's 1700. Coupled, a 10 % cut in the column bottoms settles at 1.043 bar a and a shut vent
at 1.287, where the flash equals the capacity. PIC-323203 itself is a slow trim: it runs the DCS
gain per bar, and a set point of 1.30 reaches 1.17 in an hour.

**Calibration deferrals, logged in Section C.** **B-30** — the constant capacity: below it the vent,
whose differential is floored at 0.001 bar, runs backwards out of a sub-atmospheric node to the
0.1 bar a floor in three minutes; a shut vent has no ceiling of its own (25 bar a in 400 s); and the
energy balance condenses what the pressure balance does not. **B-31** — both LP condensers charge
their inlets at design temperatures and 323E011 its water at 35 C. **B-32** — PIC-323203's gain in
engineering units, 67 times weaker than the DCS's on its set-point span. **B-34** — from the LPCC
survey: 323E003's dew-point capacity is capped at the gas that arrives, so with surplus cooling
PIC-323202 shuts and the node freezes (2.725 bar a with TIC-323013 at 45 C) instead of falling to
where the capacity meets the load. And in Section B, **B-33** — FIC-323418 keeps drawing 718B from
an empty 323D011: a stripper trip empties it in 31 minutes and creates 2.78 t in four hours.

**Proof.** 76 equivalence tests (the design basis, V1's vent generation executed with its
refusals, the seeds, 17 tick-by-tick scenarios on the unit, four coupled to V1's 323F004, and one
through V1's stages 1 to 4 into the condenser) and 11 behaviour tests; two mutations caught. For
323D002, 27 equivalence and 12 behaviour tests. `python -m pytest` — **5024 passed** (4932 - 5 + 10
+ 76 + 11). pyflakes clean; the headless grep prints nothing.

Next:

* **The LPCC, 323E003 / 323D001**, with PIC-323202, LIC-323502 -> SIC-323901 and TIC-323013 on the
  tempered-water circuit — the last unit of `recirc/`. It closes the node PT-323201 rides (so the
  column's downstream pressure stops being the design constant in the chained tests), takes 718B
  from 323E011 on a tear and vents into its node. Its survey is done (B-34).

### Session 21 — three decided divergences, the vendor archive, and the LPCC: `recirc/` done

Three things were asked: apply the B-29, B-33 and B-32 corrections as decided divergences and
prove them inert at design; port the LPCC, 323E003 / 323D001; and search the vendor archive for
323E011's relief setting, 323P008's trip and the 323E003 data before writing its design basis. The
request arrived as pasted text only; the process engineer confirmed it before any physics changed,
chose to rescale the LPCC's loops too, and, when V1's PIC-323202 turned out not to carry the
table's tuning at all, chose the table's row on PT-323202's span.

**The vendor archive** (`soft-copy-search`; every value read from a scanned page image):

| asked for | found | where |
|---|---|---|
| 323E011 / 323D011 relief | SV32357 on 323D011 N6, set 5.0 bar g (6.01 bar a), blocked liquid outlet, 12 000 kg/h. No relief on 323E011 in unit 323's list | Uhde UD-RL-323-EC-0006 |
| 323P008 low-level trip | none: LIC-323503 carries a high and a low alarm only; the functional diagrams carry no 323P008 logic | UD-MR-323-EC-0001, UD-MR-323-FF-0002 |
| PT-323203's range (for B-32) | 0 to 1 bar g, on 323F004 | UD-MR-323-EC-0001, loop P 323203 |
| the LPCC loops | PT-323202 0 to 5 bar g (normal 3.9 bar a on the sheet, 3.2 everywhere else); TT-323013 0 to 100 C; PV-323202A a DN 80 globe vent; PIC-323202's split range onto PV-323202A / B | UD-MR-323-EC-0001, UD-MR-323-FF-0002 |

**The decided divergences** (2026-09-27; handoffs B-29, B-32 and B-33 closed and deleted; As-Built
§XXX.9, §XXXII.11, §XXXIII.7):

| item | V1 | the port |
|---|---|---|
| B-29, 323F010's leg | capped at the liquid present plus what arrives: the floor's kilogram drained and restored every tick, 36 t/h | capped at the liquid above a 1 kg heel plus what arrives, net of the evaporation |
| B-33, 323P008 | FIC-323418's flow whatever 323D011 holds: 2.78 t made in four hours after a stripper trip | capped at the heel, 718B first, a loss-of-suction flag, FT-323418 on the delivered flow (`FlowLoop.step(flow_cap=...)`) |
| B-32, PIC-323203 | the table's 0.60 per bar: a slow trim | 0.60 on its 1 bar span, 60 %/bar |
| B-32, PIC-323202 | 5.0 %/bar, 40 s, no source | the table's 1.00 and 100 s on its 5 bar span, 20 %/bar |
| B-32, TIC-323013 | the table's 1.00 per K | 1.00 on its 100 C span: the same number |

Each is inert at design: the heel caps bind only within one tick of a vessel's floor, and a gain
multiplies an error that is zero on the set point. Every V1 scenario on the heels stays bit-exact;
the gains are proved bit-exact on the set point (600 ticks) and the identity scenarios run V1's
tuning, so the rest of each unit is still compared with V1 on every tick. Five tests assert both
sides off the set point or at the heel, and two prove the new gains inert on it. On 323E011 the new gain changes what the node does below the capacity: the
vent shuts within two minutes instead of walking the node to 0.1 bar a (B-30, updated).

**The LPCC.** 323E003 condenses on its dew point against the tempered water, so unlike 323E011
its node has a restoring force, about 19 300 kg/h per bar against the vent's 320; PIC-323202 is a
trim on it. The capacity's cap on the gas that arrives freezes the node under surplus cooling
(B-34, now pinned: 2.840 bar a on the decided tuning, 2.725 on V1's). Two new items: **B-35**, V1's
floor guard on 323P001 makes up one tick's overdraw once (6.2 kg at a 1 s step); **B-36**, V1
models PIC-323202's split range as one vent, with no cascade onto the cooling — which is why
nothing takes the cooling back when the vent has shut.

| module | lines | what it carries |
|---|---|---|
| `units/recirc/lp_carbamate_condenser.py` | 446 | NEW — the gas envelope on the dew point, PV-323202's law, the tempered-water split range, the tank, LIC-323502 -> SIC-323901 and 323P001 |
| `data/unit_323e003.py` | 239 | NEW — PFD 305 to 797, the envelope, the duty, 323P001's kinematics, the four controllers with the two rescales |
| `units/recirc/flash_condenser.py` | 430 | B-32 and B-33 |
| `data/unit_323e011.py` | 282 | PT-323203's span; PIC-323203's gain rescaled |
| `units/recirc/pre_evaporator.py` | 511 | B-29 |
| `control/process_loop.py` | 355 | `FlowLoop.step(flow_cap=...)` |

**Proof.** 78 equivalence tests for the LPCC (34 constants, its four relations against V1's
expressions, 18 scenarios alone, the decided tuning both ways, and three coupled runs: the column
riding the node, 323E011 through 321 and the 718B tear, and V1's stages 1 to 4, 8 and 9 end to
end) and 7 behaviour tests; two mutations caught at once. `python -m pytest` — **5115 passed**,
exit 0 (5024 + 6 for the divergences + 78 + 7). pyflakes clean on every touched file; the
headless grep prints nothing.

Next:

* **`desorption/`**, starting where the LP section's boundaries end: 323C005 / 328V001, which
  take PFD 702 from 323E011, and 328D001, whose 776 and 786 the two LP condensers hold at design.
* Open decisions from this unit: B-34 and B-36 together (the cap, and the cooling cascade that
  would release it), B-35 (the heel cap on 323P001), B-30 and B-31.

### Session 22 — the LPCC's last three decisions, 323P001's documents, and 323C005: `desorption/` begun

The process engineer decided the LPCC's open items, again as pasted text, and confirmed before
any physics changed: B-35 and B-34 as decided divergences, and — for B-36, whose sources turned
out to disagree — V1's single vent, "as this change was not reflected in PID".

| item | V1 | the port, from 2026-09-27 |
|---|---|---|
| B-34, 323E003's capacity | capped at the gas that arrives: under surplus cooling the node froze once PV-323202 shut (TIC-323013 at 45 C: 2.725 bar a, 6119 kg/h of capacity unused) | the whole dew-point capacity: the node follows the water down to where the capacity meets the load, 2.458 bar a |
| B-35, 323P001 | guarded only once 323D001 is on its floor: 6.2 kg made on the tick it gets there | the heel cap of decision 11, with a loss-of-suction flag |
| B-36, PIC-323202's split range | one vent on the whole output | kept: one vent. The functional diagram's PV-323202B is not built |

Both divergences are inert at design. The equivalence transcription now carries the two decided
lines as a switch, so every identity scenario still compares the rest of V1's stage 8 tick for
tick, including the ten where V1's cap or guard would have acted (the gas cut and the gas gone,
both blow-throughs, TIC-323013 at 45 C and in MAN, PIC-323202 on 3.5 bar a, the pump at the heel,
and two of the coupled runs); four new tests assert both sides on V1's own lines. Two mutations — the cap restored, the flag never
raised — are caught.

**The vendor archive** (`soft-copy-search`; every value read from a scanned page image):

| asked for | found | where |
|---|---|---|
| SIC-323901's speed range | ST-323901 0 to 145 rpm. V1 carries PV and output in rpm, so the span rule leaves 1.10 | UD-MR-323-EC-0001, loop S 323901, sheet 1 |
| LIC-323502's tuning | none: the pump's documents carry no DCS tuning, the tuning table has no row. The functional diagram gives the cascade's scaling, SP = OUTP . 145 / 100, and a 130 rpm limit on the speed demand | UD-AU-323-EC-0014, UD-AU-323-DZ-0013-061, UD-MR-323-FF-0002 |
| 323P001's performance | 41 m3/h at the rated 81 rpm, 32 at 64, 9.6 at 19: V1's 0.5046 m3/h per rpm within 1 % | UD-AU-323-EC-0014, sheets 7 and 8 |
| PV-323202B's service | the P&IDs tag the cooler 329E002's outlet and bypass valves PV-323202A / B and the gas vent TV-323013; the 2007 loop summaries give the vent to PIC-323202 and the cooler valves to TIC-323013 as TV-323013A / B | P&ID 103/1 and 109 (`References/Merged_Searchable_PIDs.pdf`), UD-MR-323-EC-0001 loops P 323202 and T 323013 |

| module | lines | what changed |
|---|---|---|
| `units/recirc/lp_carbamate_condenser.py` | 480 | the capacity uncapped; the heel cap and `suction_lost` |
| `data/unit_323e003.py` | 249 | ST-323901's span; SIC-323901's gain written as the table's |

**Proof** (the LPCC decisions). `python -m pytest` — **5119 passed**, exit 0 (5115 + 3 + 1).

**323C005, the atmospheric absorber — `desorption/` begun.** V1 steps it first in its LP
recirculation and desorption block: it scrubs PFD 702 (323E011's vent) and 708 (the vacuum
train's vapour) with the lean solvent 756, vents 341 saturated at the solvent's temperature
(V1 report D-11, the saturated-gas law of V1's `vacuum_condenser`, ported to `thermo/`), cuts
its absorption at water's boiling point when the solvent is lost, and drains 343 freely through
N4 to 328V001 on a weir-then-orifice sump holding 8 kg (report A-16). Every stream into it is a
V1 tear — 702 (`R3232_702`), 756, 708 and 324E002's inerts — read as it stood at the end of the
tick before, because V1 steps the absorber before the units that make them; the port reproduces
that one delay on 702 and adds none, proved by a coupled run against V1's 323E011 through the
tear. PFD 776 and 786 do not enter 323C005: they are 328D001's, taken by the two LP condensers on
the same tick in V1, and held at design until 328D001 is ported. One new observation, filed
under B-31: 756 is charged at a design 43 C while its live temperature, 322C001's, sets the vent.

| module | lines | what it carries |
|---|---|---|
| `units/desorption/atmospheric_absorber.py` | 373 | NEW — the sump and its N4 drain, the anchored vent, the absorption heat and its boiling-point cut |
| `data/unit_323c005.py` | 128 | NEW — PFD 341 to 756, the vapour rows, the column and N4, the back-solved absorption heat |
| `thermo/saturated_vent.py` | 152 | NEW — the saturated-gas vent law; the condenser branch arrives with unit 324 |

**Proof.** 96 equivalence tests (the design basis, the vent law against V1's `vacuum_condenser`
executed, the sump and the vent at many states, eleven scenarios tick by tick, the coupled 702
tear) and 16 behaviour tests; three mutations caught at once. `python -m pytest` —
**5231 passed**, exit 0 (5119 + 96 + 13 + 3). pyflakes clean on every touched file; the
headless grep prints nothing.

Next:

* `desorption/` stage 2, **328D003** and its three communicating compartments, which take 343
  on the same tick, with 328V001's temperature and the 328E007 interchanger; then 328C002,
  328C003, 328C004 and 328D001 in V1's order. 328D001 releases 776 and 786 to the two LP
  condensers, which must then step after it.
* Open decisions: B-30 and B-31 (Section C, kept as V1 by the process engineer's choice for
  now), and the rest listed in `handoff.md`.

### Session 23 — 328D003, the ammonia water tank

Three things were asked: port 328D003, V1's desorption stage 2; handle 323C005's 343 hand-off as
the zero-delay connection it is, not as a tear; and survey the tank for the boundary flaws found
in 323D002 — a pump on an empty suction, an overflow with nowhere to go — applying the heel cap
and the routed overflow wherever found.

**The survey.** V1's stage 2 (`main.py` 8883-8950) steps compartments I and II on their own
streams, floors each at 1 kg, and levels the three bays through `redistribute_communicating_
compartments`. Three flaws:

| flaw | V1 | what was done |
|---|---|---|
| empty suction | 322P002 and 328P003 draw their full flows whatever the tank holds; the floors make the liquid — 34 273 kg in an hour from an empty tank | the heel cap, as one level for the three bays (decision 11 extended) |
| no overflow | the bays level above their 490 m3 without limit: 104 % with 741 open, 155 % with 322P002 stopped as well | the overflow at the approved capacity, published as a stream (decision 11 extended) |
| 734 delivered to no unit | FIC-323401's 1534 kg/h leaves the tank and the plant | reproduced, logged as B-37: the sources disagree on its destination |

The heel had to be a level, not 1 kg per bay: the levelling carries a bay below its floor into
compartment III, and the floor then restores it every tick — measured at 3040 kg/h, which
328P003 pumps out. With the heel at the level where compartment I holds 1 kg (compartment II
2.39 kg), the pumps stop with 27.22 kg in the tank and the only liquid made is V1's own 1 kg/h
table rounding. The overflow's destination is outside the model; the P&ID UD-VT-328-FB-0003 shows
a high shell connection through the loop seal Z2801Z to the drain system, unlabelled, logged in
Open data gaps.

**The 343 hand-off.** V1 steps 328D003 immediately after 323C005, and the tank takes this
tick's bottoms — a same-tick `Result`, which the scheduler draft already carries (§3.6, now
naming it). Three tests hold it: the flowsheet 323C005 -> 328D003 -> 323E011 orders exactly as V1
steps, with 702 its only tear; a coupled run of V1's stages 1, 2 and 9 against the ported three
for 3000 ticks; and a control that feeds the tank last tick's 343 and leaves V1 on the first tick
the bottoms move. 791 goes forward the same way to 323E011.

**Other findings.** FIC-328402 runs V1's 0.06 where the DCS table gives 0.75, and its transmitter
reads the valve's flow with 322P002 stopped (B-38). 343 is charged at a design 56 C whatever
323C005's liquor does, and the condensates and 741 at design temperatures (added to B-31).
Compartment I's back-solved heat term, which V1 names an exotherm, is a 13.9 kW sink at design:
the condensates arrive 0.40 K above 44 C. The vendor archive holds only the tank's site-quality
file (UDS-BM-328-*), unread; `MAP_328D003.md`, which the approved-capacity note cites, is not in
V1's tree.

| module | lines | what it carries |
|---|---|---|
| `units/desorption/ammonia_water_tank.py` | 483 | NEW — the two active bays, the openings, the five flow loops, the heel and the overflow |
| `data/unit_328d003.py` | 215 | NEW — PFD 343 to 793, the approved capacities, the back-solved heat term, the loops' tuning |

**Proof.** 80 equivalence tests (the design basis, the five loops' seeds, the openings and their
refusals against V1's function executed, fourteen scenarios tick by tick V1 verbatim, each limit
both ways, the flowsheet order, the coupled run and its control) and 8 behaviour tests; seven
mutations caught. `python -m pytest` — **5319 passed**, exit 0 (5231 + 80 + 8). pyflakes clean on
every touched file; the headless grep prints nothing.

Next:

* `desorption/`: **328E007**, the feed/effluent interchanger V1 steps right after the tank (735
  and compartment II's temperature on the same tick, 328C004's bottoms and temperature as
  tears); then 328C002, 328C003, 328C004 and 328D001 in V1's order. 328D001 releases 776 and 786
  to the two LP condensers, which must then step after it.
* Open decisions: B-37 (734's destination) and B-38 (FIC-328402), new; B-30 and B-31 (Section C);
  the rest listed in `handoff.md`.

### Session 24 — FIC-328402 decided, and 328E007, the desorber heat exchanger

The process engineer confirmed 328D003's overflow and pro-rata starvation, kept B-37 as V1 under
the calibration deferrals (734 an open sink until Phase 7), and decided B-38: FT-328402 reads what
322P002 delivers, and FIC-328402 carries the DCS table's 0.75 read per cent of span. Then 328E007
was authorised, with attention to how it handles the condensate returns.

**B-38.** FT-328402's range, 0 to 70 m3/h, was read from Uhde's loop summary UD-MR-328-EC-0001
(scanned). The gain is 1.071 %/(m3/h), 56 times weaker than V1's 60.15; the transmitter takes the
heel caps' form, the previous tick's delivered flow. Measured at 0.1 s: a set-point move settles
within 1 % in 476.9 s, where V1 took 199.5 s; with 322P002 stopped the tank is bit-exact with V1
on every tick, and FV-328402 winds open in 34.3 s; on restart the open valve passes twice design
and the loop is back within 1 % after 449.8 s. The same loop sheet puts FIC-328402 on 328P003's
discharge — PFD 735, 56 C — not on 744, where V1 hangs it (B-39, kept as V1 until Phase 7 by the
process engineer's choice). And decision 10's note that the volumetric flow loops "were already
right" was wrong: V1 applies their table numbers per kg/h, and FIC-328406 in AUTO on V1's gain
bang-bangs FV-328406 between 0 and 100 % every tick at 0.1 s (B-41).

**328E007.** V1's block (`main.py` 8952-8967) is a temperature effectiveness on the cold side,
58/87 back-solved from the PFD, and an energy balance on the hot side with a back-solved shell
loss, the hot outlet clamped between the inlets. No thermal loop closes in a tick: the feed's
heat comes back through 328C004's temperature a tick late, and the condensate return 740 ->
328E001 -> 741 is open, 741 entering the tank at a design 40 C (B-31). The survey found one hole:
the cold outlet ignores the hot flow, so where 739 cannot pay — below 62 % of its design, or with
735 above 162 %, which the tank sends above 80.8 % level — the clamp hides heat made from
nothing, 2023 kW with 328C004's bottoms stopped. Raised as B-40 and decided the same session
(decision 14): the feed takes only what 739 gave, less the shell loss, bounded by V1's share.

| module | lines | what it carries |
|---|---|---|
| `units/desorption/feed_effluent_interchanger.py` | 155 | NEW — the exchange law, the decided pinch cap, 328E007 |
| `data/unit_328e007.py` | 59 | NEW — PFD 735 to 740, the back-solved effectiveness and shell loss |
| `units/desorption/ammonia_water_tank.py` | 491 | FT-328402 on the delivered flow while 322P002 is stopped |
| `data/unit_328d003.py` | 230 | FT-328402's span; FIC-328402 on the table's gain |

**Proof.** 328E007: 14 equivalence tests (the design basis, 81 inlet sets across every branch
of the clamp, the pinch both ways, the thresholds, the flowsheet order, 3000 ticks coupled to V1's
stages 1 and 2) and 16 behaviour tests; eight mutations caught, a ninth equivalent. B-38: 5
equivalence tests in a new file, both departures both ways; the tank's own equivalence file gives
up its two FIC-328402 scenarios to it (78 tests), and its behaviour file gains the restart and the
gain (10). `python -m pytest` — **5354 passed**, exit 0. pyflakes clean on every touched file;
the headless grep prints nothing.

Next:

* `desorption/`: **328C002**, desorber I, which takes 738 from 328E007 on the same tick; then
  328C003 (with 328E021, whose law V1 writes as 328E007's — decision 14 is not yet extended to
  it), 328C004 (FFIC-329401's basis, B-39) and 328D001.
* Open decisions: B-39 and B-41, new (Section C); B-37 moved to Section C; B-30 and B-31; the
  rest listed in `handoff.md`.

### Session 25 — the flow loops on their spans, and 328C002, desorber I

The process engineer decided B-41 under the "Typo Rule" — FIC-328406 and every sibling flow loop
rescaled on its transmitter's span — extended decision 14 to every fixed-effectiveness exchanger,
confirmed the working directory (A-1, closed), set a phase for every open item (decision 17), and
authorised 328C002 with attention to its overhead and reflux.

**B-41.** The six spans were read from Uhde's loop summaries (scanned): FT-323401 0-4, FT-323402
0-3.3, FT-323418 0-10, FT-324401 0-110, FT-328405 0-2.3 and FT-328406 0-60 m3/h. The gains fall 23
to 595 times (1.27 on FIC-324401, whose t/h span rides PFD 317's 1151 kg/m3). At 0.1 s FIC-328406
in AUTO goes from slamming FV-328406 0/100 % every tick to settling on 10 m3/h in 1223 s; the
other set-point moves take 219 to 743 s where V1 took 26 to 328, every one monotone. Each unit's
transcription carries the decided gains; `test_flow_loop_gains_equivalence.py` runs V1 verbatim
against the port. Two loop sheets bear on open items: F 323401's service is "AW to 323E003" (734's
destination, B-37), and F 328405's puts 793 into 328E004 at 1.02 m3/h where V1 holds it shut.

**328C002.** V1's stage (`main.py` 8965-9060) pulls in the desorption train's species layer:
vapour rows read as mole %, an N-feed back-solve whose anchors chain (328C003's and 328C004's
vapours feed 328C002's), a Kremser-lumped volatility on the rigorous model's T/P derivative, the
implicit species step, and the liquor's bubble pressure at the level valve. The overhead and the
reflux, as asked: 737's flow, composition and molar mass are live; its boil-up is an anchored
energy ratio with constant latent heats; the bottoms sit on water's bubble point at the column
pressure; 775 enters at 328D001's design 61 C and 748 and 750 at the PFD's 188 and 140 C, not the
live temperatures (added to B-31); 738 and 775 carry PFD rows. The condensing itself is 328D001's:
328E004's duty is stroke-proportional and the drum condenses 737 at 2163.55 kJ/kg where 328C002
boils it at 1879 — for that port. The survey found two holes, raised and decided the same session:

* **B-42 (decision 15).** V1 clamps the boil-up at zero; with 748 and 750 lost the bottoms stay at
  128.5 C, 17 K over the feeds' mixing temperature, making 622.5 kW. The port condenses vapour
  and cools to 111.3 C at 1.48 bar a.
* **B-43 (decision 16).** V1 reads LV-328503's flash choke at 328E021's outlet, 190 C; Uhde's loop
  summary L 328503 puts the valve upstream at 140 C (design 170 C). On V1, halving 750 chokes the
  valve and fills the column to 613 % in an hour; the port holds 50 %.

Decision 11 applied as the standing rule: 328P006 capped at the heel; the shell's 11 988 kg a
ceiling, the excess an overflow stream whose destination waits for 328D001 (A-15, new).

| module | lines | what it carries |
|---|---|---|
| `thermo/ammonia_water.py` | 335 | NEW — the liquor: mole-% rows, the N-feed back-solve, Kremser, the stage builder, the volatility ratio, the valve Pv |
| `units/desorption/desorber_stage.py` | 131 | NEW — the live volatility and the implicit species step, shared by the three columns |
| `units/desorption/first_desorber.py` | 360 | NEW — 328C002: boil-up, overhead line, pressure, bubble point, holdup, species, LIC-328503, heel, overflow |
| `data/desorption_train.py` | 224 | NEW — PFD-22 flows and compositions for the three columns, the tower, the three anchors |
| `data/unit_328c002.py` | 204 | NEW — 328C002's vessel, energy anchor, LV-328503 and 328P006, LIC-328503, its stage |
| `data/unit_328d003.py`, `unit_323e011.py`, `unit_323.py` | 258, 294, 563 | the six flow loops' spans and gains |

**Proof.** 328C002: 108 equivalence tests (72 design constants, the anchors and the Kremser stage,
eleven scenarios against the switched transcription and seven of them V1 verbatim, each of the four
departures both ways, the flowsheet order, 3000 ticks coupled to V1's 328D003 and 328E007); 15, 6
and 8 behaviour tests on the liquor, the stage and the column; ten mutations caught. B-41: 11
equivalence tests in a new file; the three units' harnesses carry the decided gains; two stage-4
behaviour pins moved (110 221.4 -> 110 227.2 kg/h; 7.1595 -> 7.1556 %). `python -m pytest` —
**5502 passed**, exit 0. pyflakes clean on every touched file; the headless grep prints nothing.

**Phase 4's scheduled items (decision 17).**

* **A-9 (decision 18).** `thermo.service.FLASH_OUTER_ITERS` = 60. Measured before building: the
  323 stages' rigorous departure refuses an unconverged flash, so the budget moves physics at
  states needing 41 to 60 sweeps — raised again, decided the same way. Six behaviour pins moved
  (323F010 superheat 16.448 -> 19.901 K with PV-329208 at 45 %; the rest by 0.0003 to 0.8). Every
  harness that lifts V1 physics now seeds V1's `thermo_service` on the port's budget
  (`tests/equivalence/v1_loader.v1_service`, a proxy that clears V1's memo when the budget
  changes); the budget is asserted both ways.
* **B-21 (decision 19).** `core/transport.py` gains `property_packet` and
  `transport_process_properties`; `units/recirc/liquor_line.receive_liquor` delivers the live
  departure flow. The four stage transcriptions carry a `line_decided` switch; the stopped drain
  runs both ways (V1's drum takes in 3.5 t in two minutes the column never sent).
* **B-2, measured.** On the port's 323 train with design boundaries, both the per-species form and
  the whole-volatile-sub-vector form settle within 0.3 % of design CO2 at 20 000 s: V1's offsets are
  not a stage-level effect. Off design the forms part widely (323F010's NH3 +49 % against +147 %
  with CO2-rich bottoms). Re-measure on the assembled plant in Phase 5.
* **The data hunt.** 323E002's DDS gives its chest at 3.900 bar a saturated (145 C is 2 K of
  superheat on the inlet); 323E010's at 2.5 bar a and 139 C, with PFD 926 (B-23). Flowserve's
  summary gives Kvs and characteristic for sixteen ported valves — twelve of them modified equal
  percentage where V1 runs linear (B-44, new, Section C); CCI's sheet gives PV-322203. No
  urea-melt Henry constants exist in either archive (B-1).
* **A-1** closed: the working directory is `D:\Work\Urea Simulator V1.1`. **A-13** restated as a
  standing rule; 328C002 has no check valve and forms its differentials inside its laws.

| module | lines | what changed |
|---|---|---|
| `thermo/service.py` | 501 | `FLASH_OUTER_ITERS` = 60 (A-9) |
| `core/transport.py` | 313 | `property_packet`, `transport_process_properties` (B-21) |
| `units/recirc/liquor_line.py` | 115 | the live flow delivered (B-21) |
| `tests/equivalence/v1_loader.py` | 246 | `FlashBudget`, `v1_service` |

`python -m pytest` — **5510 passed**, exit 0, after A-9 and B-21.

Next:

* `desorption/`: **328C003**, the hydrolyser, with 328E021 on decision 14's cap; then 328C004
  (FFIC-329401's basis, B-39) and 328D001 (the overflow of A-15, the 737 latent gap).
* Decisions waiting: re-anchoring 323E002's chest on 3.9 bar a and 323E010's on 2.5 (B-23, Open
  data gaps); the vendor valve characteristics (B-44); the rest listed in `handoff.md`.

### Session 26 — the chests and their cascades, the vendor valves, and 328C003

The process engineer decided the three items session 25 left waiting under the "Typo Rule": the
two chests re-anchored on their datasheets (decision 20), the vendor valves on their own trims and
Kvs (decision 23), and the percent-of-span rule extended to TIC-323007, TIC-323012, PIC-329202 and
PIC-329208 "if V1 applied the DCS table gains in engineering units". Two points the build raised
went back to the engineer, measured, and were decided the same session: V1's chest-gain scale goes
(decision 21), and TIC-323012 — whose gain is V1's own retune, not the table's — runs its
sibling's row (decision 22, B-45).

**The chests (As-Built §XL.1).** Re-read before building: 323E010's sheet prints 2.5 bar a beside
139 C "saturated", which is 3.5 bar a's saturation, and PT-329208's loop summary gives the normal as
3.5 bar a. IAPWS-IF97 settles it: PFD 917's saturated 4.4 bar a header let down isenthalpically is
145.06 C at 3.9 bar a and 139.28 C at 2.5 — both datasheets' figures — and both densities are the
lower pressures'. UA 760.6 and 255.1 kW/K; strokes 77.79 and 49.87 %. On V1's 3.96 bar a an LP header
at 4.6 bar a pins PV-329202 wide open and leaves 323C003 0.11 K low for good; on 3.9 it recovers.

**The cascades (As-Built §XL.2).** Spans from the loop summaries (TT-323007 and TT-323012 0-160 C,
PT-329202 and PT-329208 0-6 bar g), the cascade scaling from UD-MR-323-FF-0002 sheets 4 and 5.
TIC-323007 2.0 -> 0.075 bar/K, PIC-329202 3.82 -> 10.83 %/bar, PIC-329208 0.372 -> 3.33 %/bar,
TIC-323012 3.6 bar/K and 1200 s -> 0.075 bar/K and 500 s. `chest_slave_kc_scale` deleted. B-20's
closed-loop limit cycle turns out to be V1's master gain: on the span gain the column holds 135.000
C and the overhead never reaches the cap (the open-loop offset stays).

**The vendor valves (As-Built §XL.3).** Flowserve's calculation sheets read for every urea-plant
position, CCI's for PV-322203 (its only urea-plant valve), catalogued in the new
`data/control_valves.py`. The modified equal-percentage trim — R 20, the tangent line through the
origin below 33.4 % — reproduces all 41 printed strokes within 0.50 %. Nine ported valves change
trim and design stroke, LV-323501 its stroke and FL, PV-322203 its trim and anchor (wide open it now
passes 2.2 times the feed); FT-328406 reads the 741 diverted. Not built, and raised: the vendor sized
LV-323501 flashing, which V1's law, given no vapour pressure, cannot do (B-46).

| module | lines | what changed |
|---|---|---|
| `data/control_valves.py` | 268 | NEW — the vendor catalogue, `design_stroke_pct`, `full_stroke_m3h` |
| `control/valve.py` | 541 | `mod_equal_pct`, `MOD_EQUAL_PCT_RANGE`, `stroke_for_cv_fraction` |
| `control/process_loop.py` | 375 | `FlowLoop.characteristic`, `stroke_flow` |
| `units/steam_chest.py` | 125 | `chest_slave_kc_scale` deleted |
| `data/unit_323.py` | 639 | the anchors, the spans and gains, three valves |
| `data/unit_328d003.py`, `unit_323e011.py`, `unit_320.py` | 288, 300, 210 | their vendor valves |
| the six units | — | the trims wired: `ammonia_water_tank`, `flash_condenser`, `flash_tank`, `solution_tank`, `rectifying_column`, `co2_line`; `pre_evaporator` the gains |
| `tests/equivalence/decided_valves.py` | 105 | NEW — the trim, V1's `_fic_flow` on it, V1's hydraulics on it |


### Session 26, continued — 328C003, the vapour books, the relief devices, and 328C004

**328C003 and 328E021 (As-Built Part XLI)** ported bit-exact tick by tick, coupled to 328C002, with
five rule-7 classes: 328E021's pinch cap (decision 14), LV-328504's heel and the full shell
(decision 11), PV-328203 on its vendor trim (decision 23, PV-328203 added to the catalogue) and
PIC-328203 / FIC-329402 on span (decision 10). The survey found a vapour-inventory hole — V1's
liquid loses the overhead valve's flow while the head space fills with the generation — raised with
both sides measured and decided: the liquid pays what boils (decision 24), built on 328C003 and
retro-fitted to 328C002; V1 makes 505 kg and runs 3.1 K hot with PV-328203 at 20 % for an hour,
exactly its integral of generation less overhead; the port's books close within 50 g. On the new
books 328C003 with its overhead shut passes 24.01 bar a at 458.5 s.

**The relief devices (As-Built §XLI.6).** The process engineer asked for 328C003's PSV and every
plant PSV. Uhde's technical specifications for units 320-335 read in full — 61 safety valves and 3
rupture discs (UD-RL-3xx-EC-00nn, scanned) — and catalogued in `data/relief_devices.py`, every
relieving pressure checked against set + 10 %; Sempell's set-pressure certificates confirm those
checked. 328C003's is SV32852, set 23.0 bar g on its MP steam inlet. No relief is modelled: B-47.

**328C004 (As-Built Part XLII)** ported bit-exact tick by tick, coupled to 328C002 and 328C003, with
FFIC-329401 re-based on 735 as the process engineer decided (decision 25) and six rule-7 classes:
decisions 24 and 15, the heel and the full shell (11), LV-328505 on its vendor trim (23),
FIC-329401 on FT-329401's span (10). AI-328701's conductivity inference ported into
`thermo/ammonia_water.py`. The survey read the P&ID and the functional diagrams and found three
control structures V1 does not build — TIC-328012 over FIC-329402 (B-48), FFIC-329401 as a ratio
station (B-49), LIC-328505 over FIC-328406 (B-50) — and a full column's ringing pressure (B-51).

| module | lines | what changed |
|---|---|---|
| `units/desorption/hydrolyser.py` | 498 | NEW — 328C003 and 328E021 |
| `data/unit_328c003.py` | 239 | NEW |
| `units/desorption/second_desorber.py` | 374 | NEW — 328C004 |
| `data/unit_328c004.py` | 221 | NEW |
| `data/relief_devices.py` | 277 | NEW — the urea plant's relief devices |
| `units/desorption/first_desorber.py` | 368 | decision 24 retro-fitted |
| `thermo/ammonia_water.py` | 393 | `condensate_conductivity_us_cm` (AI-328701) |
| `data/control_valves.py` | 276 | PV_328203 |

`python -m pytest` — **5841 passed** before 328C004, **5902 passed** after it, exit 0.

Next:

* `desorption/`: **328D001**, the reflux drum (the overflows of A-15, the 737 latent gap), which
  closes unit 328.
* Decisions waiting: B-46 (the letdowns sized flashing), B-47 (relief), B-48 to B-51 (the three
  unbuilt control structures, the full column's pressure).


### Session 27 — 328C004's control structures: the ratio station and the 741 recycle

The process engineer decided the three control structures the survey had raised on 328C004 and
328C003 (the "typo rule": V1 missed wiring the P&IDs and the functional diagrams draw), with the
recycle's topology and span put to them as a question:

* **B-49 — FFIC-329401 a ratio station** (decision 26). `control/ratio.py` gains `RatioStation`:
  its output, FIC-329401's set point, is the ratio set point times 735 in m3/h times 1000; the
  ratio tracks the measured one while FIC-329401 is out of cascade, so the return is bumpless;
  nothing integrates. On a 735 cut V1's PI slams FIC-329401's set point to 0 kg/h for 47 s; the
  station asks the ratio's 5196 kg/h on the tick (As-Built §XLII.4).
* **B-50 — LIC-328505 over FIC-328406** (decision 27). FIC-328406 moved from the tank to
  `second_desorber.py`: 741 leaves 328C004's bottoms ahead of LV-328505 (P&ID 104), the heel
  serving it first; in cascade LV-328505 is switched shut and FIC-328406's set point is
  LIC-328505's output across FT-328406's 0-60 m3/h (V1's limit 34.0). The tank takes 741 as a
  boundary, a tick late. In cascade at design the level swings 30.7-77.2 % and settles in two
  hours (§XLII.5).
* **B-48 kept as V1**, TIC-328012 faceplate-only, deferred to Phase 7: on V1's PV, T - T_746, the
  drawn direct action runs away (911 from 1105 to 193 kg/h in two hours with 328C002 2 K hotter);
  moved to handoff Section C. **B-51** (a flooded column's ringing pressure) deferred to the
  solver review of Phases 5 and 7, Section C.

Both structures are switches in 328C004's transcription ("station", "recycle"), compared on every
tick of every scenario, and run both ways in the new
`tests/equivalence/test_second_desorber_control_equivalence.py` (7 tests: the station through a
feed cut, on the tick through two feed moves and a ratio step, tracking and bumpless against V1's
wind-up; FIC-328406 into cascade and by hand, the recycle at the heel; TIC-328012 driving
nothing). `tests/control/test_ratio.py` is new (5 tests). The flow-loop gains file's FIC-328406
test now runs 328C004's loop beside V1's tank stage; its Part XXXVII table was re-measured on the
vendor trims.

| module | lines | what changed |
|---|---|---|
| `control/ratio.py` | 247 | `RatioStation` |
| `units/desorption/second_desorber.py` | 449 | the station, FIC-328406, the switch, the recycle at the heel |
| `units/desorption/ammonia_water_tank.py` | 488 | FIC-328406 out; 741 a boundary |
| `data/unit_328c004.py` | 228 | `FFIC_329401_FACTOR`; the PI's tuning removed |
| `data/unit_328d003.py` | 291 | FIC-328406's set point to FT-328406's span |

`python -m pytest` — **5915 passed**, exit 0 (5902 before; 12 in the two new files and 2 behaviour tests on 328C004, the tank's equivalence file at 76, its 741 scenarios merged). pyflakes clean on every touched file; the headless grep prints
nothing.

Next:

* `desorption/`: **328D001**, the reflux drum, with 328E004 — survey begun: 786 vents through
  PV-328202 to 323E011 against 323E011's design pressure, 776 goes to 323E003 on LV-328501, 775
  back to 328C002 on FIC-328404 under TIC-328008; A-15's overflows and the 737 latent gap close
  with it.
* Decisions waiting: B-46 (the letdowns sized flashing), B-47 (relief).

### Session 28 — 328D001 and 328E004, the reflux drum: unit 328 closed

**The survey.** V1's stage 6 read in full with the sources the port had not yet opened: Uhde's
loop summary UD-MR-328-EC-0001 (L 328501, P 328202, T 328002, F 328404, T 328008), P&ID sheet
103/2, and the vendor's as-built drawing of the drum, UD-AU-328-DZ-0006-003. The vapour route the
process engineer asked about: 786 leaves the drum through PV-328202 and 323E011 takes exactly that
flow on the same tick, so V1's mass closes — but V1 discharges it against 323E011's DESIGN 1.13
bar a, where it uses the live downstream pressure for 737 and 750. The liquid goes forward as 776
to 323E003 on the same tick, and back as 775 to 328C002 a tick late with the drum's pressure.
PIC-328202's transmitter is on 328C002 (the loop summary confirms V1's AUDIT B5).

**The port (As-Built Part XLIII)** — `units/desorption/reflux_drum.py` on `data/unit_328d001.py` —
bit-exact tick by tick against the switched transcription over thirteen scenarios and 3000 ticks
coupled to V1's 328C002, with five rule-7 classes: the liquid loses what stays vapour (24),
328P002 at the heel and the full drum (11), LV-328501, FV-328404 and PV-328202 on their vendor
trims (23), PIC-328202 and TIC-328002 on span (10) — PIC-328202 ten times V1's gain, measured
monotone closed through 328C002. Three new mechanisms went to the process engineer with both
sides measured, and each recommendation was chosen:

* **328E004 held above its cooling water** (decision 28). V1's stroke-proportional duty cools a
  drum that has lost 737 without limit: with TV-328002 at 50 % it passes 30 C at 66.5 s and
  absolute zero at 791.5 s. The duty is capped at what brings the drum to the 30 C supply.
* **The vent on 323E011's live pressure** (decision 29), the tick before's.
* **A full 328C002's overflow enters the drum** (decision 30), part of A-15; the drum's own
  overflow waits for Phase 5's wiring to 323E011, with 328C003's and 328C004's.

FIC-328404 and TIC-328008 have no table rows and keep V1's own tunings (B-52, Section C). The
drawing gives LT-328501's taps 220 mm inside each tangent line and the vessel 5500 l with its
heads, where V1 reads the 4.343 m3 cylinder (B-53, raised).

| module | lines | what changed |
|---|---|---|
| `units/desorption/reflux_drum.py` | 460 | NEW — 328D001 and 328E004 |
| `data/unit_328d001.py` | 272 | NEW |
| `units/desorption/first_desorber.py`, `hydrolyser.py`, `__init__.py` | — | the overflows' destinations, the package map |

`python -m pytest` — **5996 passed**, exit 0 (5915 + 81: 62 and 12 equivalence tests, 7 behaviour tests). pyflakes clean on every touched file; the headless grep prints
nothing.

Next:

* **Phase 5 — the engine and the scheduler**: every unit of `synthesis/`, `recirc/` and
  `desorption/` is ported; the flowsheet's wiring (the tears, A-10; A-15's overflows; 786 and 776
  into 323E011 and 323E003 live) and the fixed 0.1 s step (A-14).
* Decisions waiting: B-46 (the letdowns sized flashing), B-47 (relief), B-53 (LI-328501's span).

### Session 29 — the letdowns flash, the nodes relieve, 328D001 has heads; Phase 4 closed

The process engineer decided the three items Phase 4 had left (the decisions 31-33 below), each
built as a decided divergence asserted from both sides (As-Built Part XLIV):

* **B-53, 328D001's vessel and taps.** The vendor's 5500 l with its heads; LI-328501 across
  LT-328501's 1510 mm taps, 220 mm above the bottom tangent; the design holdup the one reading
  50.5 % to the last bit (3029.66 kg). The drum is full at 6022.5 kg.
* **B-46, the letdowns flash.** V1's own IEC 60534 law handed each letdown's live vapour
  pressure: LV-322501 on Uhde's CONVAL sheet (read this session: FL^2 0.845, pv1 99.0 bar a,
  "Flashing!"), its Pv the stripper's bottoms on the rigorous surface scaled to the vendor's;
  LV-323501 and LV-323505 on their stages' bubble pressures; LV-328505 on 740 at 328E007's hot
  outlet. The first three choke at design; LV-328505 stands 0.03 bar short and chokes on a hot
  740. The coupled liquor train found the law's fallback: a feed cut carries 323C003's bubble
  pressure 9 % over its pressure and the uncapped law drains three times PFD 314 — the liquid at a
  valve is at most saturated at its inlet, and Pv is capped there.
* **B-47, relief.** The safety valve in `core/relief.py`: V1's API 520 law (moved from
  `control/relief.py`) on an orifice back-solved from Sempell's certified capacity, pop action at
  the set pressure, reseating at the vendor's blowdown — 10 % of set on gas, 20 % on liquid — and
  at most the vapour above the reseat pressure in a tick. Sempell's orifice selections for ten
  valves catalogued. Built on 328C003 (SV32852: the 53 bar a runaway now cycles between 24.01 and
  21.71 bar a, a lift every 165.5 s with the overhead shut) and 328C002 (SV32850/51). The rest —
  322R001 and 323C003 on the Phase 5 flowsheet, and the liquid-rated SV32357 and SV32353 whose gas
  coefficients the archive does not hold — are A-16, with options for the process engineer.

| module | lines | what changed |
|---|---|---|
| `core/relief.py` | 232 | NEW — the relief law; V1's API 520 capacity law moved in from `control/relief.py` (deleted) |
| `data/relief_devices.py` | 360 | Sempell's orifice selections, `RELIEF_SIZING` |
| `units/desorption/hydrolyser.py`, `first_desorber.py` | 529, 398 | SV32852; SV32850/51 |
| `units/desorption/second_desorber.py` | 458 | LV-328505 flashes; `t_740_c` an argument |
| `units/synthesis/stripper_sump.py` | 551 | LV-322501 flashes; `bot_mass_pct` an argument |
| `units/recirc/rectifying_column.py`, `flash_tank.py` | 463, 330 | LV-323501, LV-323505 flash |
| `thermo/urea_liquor.py` | 397 | `stage_bubble_p`, capped at the stage pressure |
| `units/desorption/reflux_drum.py`, `data/unit_328d001.py` | 514, 287 | the vessel and its taps |
| `tests/equivalence/decided_relief.py` | 54 | NEW — the relief law transcribed on V1's own capacity law |

`unit_323.py` is 653 lines, data only, over the 600 target and under the 800 limit.

**Phase 5 begun (As-Built Part XLV).** `engine/state.py`: the recycle tears as a frozen
`TearState` — the eight that cross units, seeded on V1's boot defaults (`==`), replaced only when
`PlantState.end_tick` commits the tick, so the one-tick delay is structural and no tear is iterated
(A-10); 775 and 931 stay their producers' state, 744 is retired by decision 25. 328C002, 328C003
and 328C004 coupled through the plant state's 748 and 750 are V1's `s.tlag` coupling `==` for 3000
ticks. `engine/simulator.py`: whole 0.1 s steps paid out of an integer wall-clock account at V1's
pacings, V1's 0.5 s per-pass cap, a faulted step freezing the pass; the A-14 replay — 328C003
cycling on SV32852, SLOW and FAST on irregular passes, 12 000 states to the bit.

| module | lines | what changed |
|---|---|---|
| `engine/state.py` | 146 | NEW — `TearState`, `PlantClock`, `PlantState` |
| `engine/simulator.py` | 95 | NEW — `Simulator` |
| `data/engine.py` | 38 | NEW — `DT_S`, `SIM_SPEED`, the per-pass cap |

`python -m pytest` — **6041 passed**, exit 0 (5996 at session 28; 45 new: the B-46 and B-47
both-ways and behaviour tests, the relief law's, the engine's and the tears'). pyflakes clean; the
headless grep prints nothing.

Next:

* **Phase 5, the schedule** — `schedule.py` and `scheduler.py` (§3.6): the wiring tables, V1's
  section order, the five sources checked against `core/flowsheet.py`; the four 323 stages and
  the 328 train run through it against their chained equivalence tests; every tear read from the
  plant state (A-10's close); A-15's overflows; A-16's relief on 322R001 and 323C003.
* Waiting on the process engineer: A-16's two liquid-rated valves (SV32357, SV32353 — options
  stated), and where 322C001, unit 324 and the steam system fall in the schedule.

### Session 30 — the liquid-rated valves relieve gas; Phase 4 re-opened; 322C001 ported

The process engineer confirmed the B-46 cap (the liquid at a valve is at most saturated at its
inlet — "the Typo Rule in action"), chose A-16's option (b) and re-opened Phase 4 (decisions 34,
35). As-Built Part XLVI.

**A-16, the liquid-rated valves (decision 34).** A valve Sempell rated on liquid alone relieves the
gas of a vapour node on its orifice's own area at the series' full-lift gas coefficient, 0.917 —
SV32351/52's certified alpha_w — with the law's k 1.30, reseating on the gas blowdown, 10 %; the
coefficient is an assumption, logged in handoff Open data gaps for Phase 7. `GasReliefValve` gained
`kd`. **SV32357** on 323D011: PV-323203 shut, the node lifts at 82.1 s and cycles every 19.1 s
between 5.51 and 6.01 bar a, where V1 has no ceiling (24.9 bar a at 400 s); the relief, like the
vent, is booked against the tank. **SV32353** on 328D001: PV-328202 shut, a lift every 12.5 s, where
V1 reaches 111.6 bar a. Both ways on V1's own capacity law.

**322C001, the LP absorber** — the first unit of `units/absorption/`. HV-322604's purge climbs two
packed beds (V1's `packed_absorber`: Onda transfer units on Colburn's counter-current balance
against the washes' Extended UNIQUAC back-pressure, the upper bed's heat of absorption, the vent
saturated with water, calibrated on PFD 204 -> 797 at the design pin, c 0.80 / 0.84, a_w 0.88);
755 from 322E006 washes the lower, 954 the upper; PV-322201 vents 797 on PIC-322201, LV-322502
draws 756 to 323C005 on LIC-322502. The back-pressure grid and the transport properties are thermo
modules of their own. **Bit-exact**: V1's `packed_absorber` executed beside the port in 183 tests;
the unit tick by tick over thirteen scenarios against the transcribed stage, the design pin `==`
V1's boot pin on the same gas. **Six departures**, each both ways: SV32253 at its certified 5.0 bar g
(V1 sets the vessel's 30 bar g design pressure and ramps it linearly); under rule 7 the name plate's
3.60 m3 with LI-322502 between LT-322502's taps (200 mm above the tangent, 800 mm apart; the design
holdup 506 kg where V1's is 1392), the heel (V1 makes 31.8 t in 20 minutes with LV-322502 wide
open), the full column, the vendor trims, PIC-322201 at 21.43 %/bar on PT-322201's 0-28 bar g.

**The process engineer's question — the absorber's cooling.** V1's is a fixed approach, not a
heat-transfer coefficient: 322C001 has no cooling water, the heat of absorption leaves in the
liquor, and 755 arrives at 322E006's 40 C outlet whatever 322E006's load or cooling water — 322E006
is not modelled (datasheet: plate exchanger, 6.44 m2, 222 kW, U 4781 W/m2 K). Raised as B-54 with
the options measured. **Two findings** raised with it: XV-322915's flood puts 500 kW into the
liquor with no steam, where the reference floods the gas line — flooded, the liquor holds 56.24 C,
above the trip's 55 C reset, so the latch holds itself in (B-55); and B-19 measured: the let-down
solver's -36 C floor keeps a rich purge's liquor at 55.6 C where 26 C gives 57.6, either side of
trip 22.1's 57 C. **The "LP scrubber" return**: 322C001 takes no liquid back from another
scrubber — its liquids are 755 (328D003 compartment I through 322P002 and 322E006) and 954 (steam
condensate on FT-322404), and its liquor goes forward to 323C005 (TearState 756).

| module | lines | what changed |
|---|---|---|
| `units/absorption/lp_absorber.py` | 499 | NEW — 322C001, `design_pin`, PIC-322201, LIC-322502, SV32253 |
| `units/absorption/packed_beds.py` | 398 | NEW — the two beds and their calibration |
| `thermo/ammonia_backpressure.py` | 186 | NEW — the back-pressure grid and the heats of absorption |
| `thermo/transport_properties.py` | 90 | NEW — Vogel, IAPWS R1-76, Sutherland, Fuller |
| `data/unit_322c001.py` | 321 | NEW — the design basis, the vessel, the packing, the loops, SV32253 |
| `thermo/enthalpy.py` | 385 | `reference_phase` |
| `core/relief.py`, `data/relief_devices.py` | 239, 389 | `kd`; `GAS_KD_ASSUMED`, `GAS_BLOWDOWN`, `gas_reseat_bara` |
| `units/recirc/flash_condenser.py`, `units/desorption/reflux_drum.py` | 476, 548 | SV32357; SV32353 |

`python -m pytest` — **6310 passed**, exit 0 (6041 at session 29; 269 new: 183, 50 and 7 in
the three 322C001 harnesses, 23 behaviour tests, 6 for the relief). pyflakes clean; the headless
grep prints nothing.

Next:

* **Phase 4, unit 324** — `evaporation/`: 324E001/F001, 324E003/F003, the vacuum train and UF85,
  on the shared liquor-stage layer (B-1's anchored vapour vector stands); then the steam system.
* Waiting on the process engineer: B-54 (322E006), B-55 (XV-322915), B-19 (the let-down floor).

### Session 31 — 322E006, the flood in the vent line, the letdown that condenses; unit 324 surveyed

The process engineer decided the three findings raised on 322C001 (decisions 36-38), each the
option the survey offered, and asked for unit 324 next, with a watch on its vacuum ejectors.
As-Built Part XLVII.

**B-54, 322E006** (decision 36). The plate cooler between 322P002 and the lower bed, ported on its
datasheet (Uhde UD-AU-322-EC-0012, read from the scan): counter-current effectiveness-NTU on
UA = 222 kW / 7.2135 K = 30.776 kW/K, the cooling water at its 30 C supply. At the PFD's 31 478
kg/h from 44 C the datasheet's 19 150 kg/h of water would give 755 at 38.5 C, so the water through
the plates — undocumented at the design point — is back-solved to 10 374 kg/h, 755 exactly 40.0 C
(Open data gaps). 755's temperature is now an argument of `LpAbsorber.step`. The water lost: 755 at
744's 44 C, the liquor at 46.72 C where V1 holds 43.0, the slip 2.12 kg/h of NH3 against 1.79.

**B-55, the flood in the vent line** (decision 37). P&ID 102 (UD-VT-322-FB-0003) read: XV-322915
injects LP steam into line 150-GCB6-322254 just downstream of PV-322201, and TI-322015 stands on
the same line further down. `units/absorption/vent_line.py`: the gas leaving the beds' top (954's
46 C at design, PFD 797's, while the polish outweighs the gas; the lower bed's when it is lost or
outweighed), the 500 kW as the 854 kg/h of LP steam that carries it, TI-322015 the line's adiabatic
mix, trip 22.1 on it (`trip_22_1`, V1's 57 / 55 C). Flooded, V1's liquor goes to 56.24 C; the
port's stays at 43.0 and TI-322015 reads 96.3 C. **Finding B-56**: TI-322015 downstream of the
injection holds a latched flood in — 96.3 C is above the 55 C release — so the trip clears only
when the steam stops; P&ID 102's HS-322915 override is the release (options stated).

**B-19, the letdown that condenses** (decision 38). `thermo/condensing_letdown.py`: below its dew
point the purge condenses an ammonium-carbamate liquor on the beds' own Extended UNIQUAC
speciation (with the water activity now on a second lazy grid, `ammonia_backpressure.liquid_state`),
SRK vapour and H0 enthalpy; V1's single-phase answer kept for a dry gas, the design's 94.8 C to the
bit. On a cooling loss in 322E003 the outlet holds a few kelvin under the dew point — 66.8 C at
95 % cooling, 71.7 at 90, 76.5 at 70, 77.9 at none — where V1 gives 53.3, 26.0 and its -36 C floor;
the liquor (24 kg/h to 4.3 t/h) rides the line into 322C001's sump. `PurgeValveResult` carries the
gas, the liquor and the flag; L3-7 also fires while a liquor condenses; the outlet pressure is an
argument (A-17's class). On 322C001 both ways: at 90 % the liquor ends within 0.02 K of V1's (the
enthalpy is the same), at the floor 0.7 K above. Solid carbamate is not a phase — its dissociation
constant is in no archive (Open data gaps).

**Unit 324 surveyed — the watchout.** The vacuums are not hardcoded: 324F001 and 324F003 are live
molar balances on their vapour spaces, between the vacuum condensers' saturated vents and the
ejectors' pulls. But each pull is a straight line anchored on the PFD — proportional to the motive
(or HIC-329606) and to the suction pressure — with no break pressure, discharge limit, motive
pressure or stall (handoff B-57, options stated). V1's own 1-D ejector model (Huang 1999) is
unwired. Located: Körting's operating data for 324F002 (one point) and for 324F004/F005 with their
nozzle and diffuser diameters, and Uhde's vacuum-unit table, whose motives (1061 and 366 kg/h)
dispute the PFD's (1220 and 180).

**The vacuum condensers — `evaporation/` begun.** V1's `vacuum_condenser.py` ported verbatim:
324E002, 324E005, 324E006, 324E007, each a saturated vent over its condensate's back-pressure at a
cold end where the H0 balance meets UA . LMTD, UA back-solved on the PFD rows and the vent anchored
on them (72, 584, 41, 31 kg/h to the bit). Bit-exact against V1's module over 96 cases a condenser
(394 tests). The node, the train and the stages follow B-57's decision.

| module | lines | what changed |
|---|---|---|
| `units/absorption/feed_cooler.py` | 168 | NEW — 322E006 |
| `units/absorption/vent_line.py` | 227 | NEW — the beds' top, the flood, TI-322015, trip 22.1 |
| `thermo/condensing_letdown.py` | 468 | NEW — the two-phase isenthalpic letdown |
| `data/unit_322e006.py` | 84 | NEW — the datasheet |
| `thermo/ammonia_backpressure.py` | 245 | `liquid_state` on its own grid |
| `units/synthesis/purge_valve.py` | 304 | the flash, the gas and the liquor, `p_out_bara` |
| `units/absorption/lp_absorber.py` | 531 | 755's temperature, the liquor, the vent line |
| `data/unit_322c001.py`, `core/units_of_measure.py` | 330, 192 | trip 22.1's thresholds; `KJ_PER_KCAL` |
| `units/evaporation/vacuum_condenser.py` | 456 | NEW — the four vacuum condensers |
| `data/unit_324.py` | 168 | NEW — their ratings and rows, the stages' vacuums |

`python -m pytest` — **6743 passed**, exit 0 (6310 at session 30; 433 new: 10 for 322E006, 9 for
the vent line, 5 for the flash, 4 decided and 2 tick-by-tick on 322C001, 1 each in its and the
purge valve's behaviour, 394 and 7 for the vacuum condensers). pyflakes clean; the headless grep prints nothing.

Next:

* **Phase 4, unit 324** — `evaporation/`: B-57 decided first; then the condenser node and the
  vacuum train, 324E001/F001 with 324F002, 324E003/F003 with 324F004/F005, the melt drain and UF85;
  then the steam system.
* Waiting on the process engineer: B-56 (trip 22.1's override), B-57 (the 324 ejectors).

### Session 32 — I 22.1 on the DCS's logic; unit 324: the ejector data exhausted, the melt checked

The process engineer decided B-56 and B-57 and asked for the evaporation stages' boil-off and the
melt's boiling-point elevation to be checked. As-Built Part XLVIII.

**B-56, I 22.1 as the DCS executes it** (decision 39). Uhde's application software for AC4
(UD-MR-G00-FF-0004, PC22.5.1, read from the scan) draws XVY-322915 = NOT(TT-322015 > H2) OR
HS-322915, the valve fail open (loop summary X 322915), HS-322915 a control-room keyswitch (H
322915). No latch, no reset, no operator open. `vent_line.xv_322915_open`: the flood still holds
its own reading over the limit (TI-322015 96.3 C), and the keyswitch shuts it, TI-322015 falls to
46.0 C, the limit clears, and the valve stays shut when the key is released; V1 re-opened every
operator close in the same step. Asserted both ways. The limit's value and hysteresis are database
entries the archive lacks: V1's 57 / 55 C kept (Open data gaps). Raised: **B-59** (V1's operator
open has no DCS counterpart) and **B-60** (the loop summary rates the flood at 1000 kg/h of 9 bar a
steam: TI-322015 112.4 C, not 96.3).

**B-57, the Körting curves: not in the archive.** Every Körting and Uhde document for 324F002,
324F004 and 324F005 was read — specifications, operating instructions, design calculations,
fabrication dossiers: one duty point per ejector and Körting's generic molar-mass correction, no
suction-capacity curve, no motive-pressure correction, no break pressure. The decision cannot be
built as worded, so nothing was built and B-57 goes back with measured options: Körting's nozzles
choke 1085 and 374 kg/h of motive (Uhde's table 1061 / 366, not the PFD's 1220 / 180); a loss-free
1-D model on the nozzle and diffuser throats gives 529 kg/h against Körting's 761 at 0.122 bar a
and break pressures of 1.34 and 2.39 bar a.

**The melt — the watchout.** V1's stages boil to the anchored UNIQUAC strength; there is no hard
ceiling. Ported bit-exact (`thermo/urea_melt.py`). Checked against Helwan's own PFD rows, which fix
the melt's water activity coefficient at 0.79 and 0.70: the model gives 0.52 and 0.48 (raw, it
boils the PFD melts 13-14 K hotter), so the anchored strength moves +0.249 and +0.069 wt%/K where
a refit to the PFD gives +0.175 and +0.045 and the Fahmy-Nassar plant correlation +0.167 and
+0.045. And the urea-only strength passes what the melt's biuret leaves below 0.052 bar a at 140 C
(**B-58**). The 99.7 % target is not Helwan's: PFD 402 is 97.71 % urea + 0.85 biuret, 98.6 %.

**The condensers as nodes.** V1's `vacuum_inlet_kmolh` and `vacuum_condenser_node` ported
verbatim (`units/evaporation/condenser_node.py`): the PFD row scaled on its air-free mass plus the
live false air, a blow-through part swapped in, the vent capped at the inlet. 73 cases ``==``.

**The stages surveyed.** TIC -> PIC chest cascades (324E003's chest on the 9-bar header), the
boil-off to the equilibrium strength, the melt temperature semi-implicit, the separator's vapour
balance stepped backward in P, T and P closed by Picard — with the ejector's pull inside the loop,
so the stages wait on B-57. V1's design vapours sit 4.9 % (705) and 18.1 % (709) under the PFD
rows (no urea in the vapour, no biuret formed); the condensers see the PFD rows by departure.

| module | lines | what changed |
|---|---|---|
| `units/absorption/vent_line.py` | 270 | `xv_322915_open`, PC22.5.1 |
| `control/interlocks.py`, `data/unit_322c001.py` | 217, 332 | 22.1's provenance |
| `thermo/urea_melt.py` | 110 | NEW — the melt's anchored equilibrium |
| `units/evaporation/condenser_node.py` | 143 | NEW — the condensers as nodes |
| `data/unit_324.py` | 180 | the stages' melt anchors |

`python -m pytest` — **6838 passed**, exit 0 (6743 at session 31; 95 new: 9 and 6 for the melt,
73 and 5 for the condenser nodes, 1 decided on 322C001, 1 net on the vent line). pyflakes clean;
the headless grep prints nothing.

Next:

* **Phase 4, unit 324** — B-57 and B-58 decided first; then 324E001/F001 with 324F002,
  324E003/F003 with 324F004/F005 and the vacuum train, the melt drain and UF85; then the steam
  system (B-60's header with it).
* Waiting on the process engineer: B-57 (again), B-58, B-59, B-60.

### Session 33 — four decisions built; the ejectors' maps and B-61; the melt on the licensor's chart; stage 1 of unit 324

The process engineer decided B-57 (again), B-58, B-59 and B-60, each as recommended, and authorised
the port of the 324 stages. As-Built Part XLIX.

**B-59, XV-322915 has no operator open** (decision 40). The overlay is generated, so the converter
gained `DECIDED_EDITS`: XV-322915's symbol is a status display, its override button HS-322915, a
maintained keyswitch (`keyswitch_set`). The command layer refuses an `xv_toggle` on 322915 (Phase 5).

**B-60, the flood on the valve's rated steam** (decision 41): 1000 kg/h at 9.0 bar a and 175 C,
Uhde's loop summary; TI-322015 112.35 C over the design vent (V1's 500 kW, 96.31).

**B-58, the melt on the PFD** (decision 42). UNIQUAC's one urea -> H2O energy an argument;
refitted to PFD 401/402 under 705/709, -85.3 K (fits -71.66 and -98.92); the anchored departure
kept; the strength capped at what the feed's biuret and formaldehyde leave. The temperature slopes
+0.175 and +0.045 wt%/K: Fahmy-Nassar +0.167 and +0.045. The process engineer then pointed to
`References/Sources/Urea Production Diagrams.pdf`: Uhde's Helwan Fundamentals, whose Figure 15 is
the licensor's own urea-water chart. Digitised from the scan, it puts the refit within 13 % of
every line from 92.5 to 99 % (V1's parameter 27-35 % low) and its slopes at +0.159 and +0.044
(the refit within 10 and 3 %). Its 99.7 % line is the chart's illustrative prilling point D.

**B-57, the ejectors' maps** (decision 43). V1's unwired `ejector_huang.py` ported
(`ejector_gas_dynamics.py`, bit-exact); each ejector's map synthesized on its throats (Körting's
24.7 / 106.5 and 14.5 / 30.8 mm; 324F002's fitted on its duty), anchored on its vendor duty point
(761 kg/h at 0.12 bar a; 84 at 0.33; 94 at 0.2) and Uhde's 1061 / 366 kg/h of motive, the break on
the duty's discharge pressure with a subsonic closure, tabulated on suction and motive pressure
and interpolated (`ejector_map.py`). **B-61**: at the PFD's vacuums the maps out-pull the PFD's
loads (845 against 584 kg/h, 214 against 72); the bleeds that would hold 0.131 and 0.33 bar a
need 108 and 104 kg/h of air where Flowserve's PV-324203 and PV-324202 pass 26.7 and 67.4 wide
open (read this session, with HV-329605 / 606); the vacuums settle at 0.120 and 0.229-0.288 bar a.
The plant's own trend (Book2.xlsx) holds PT-324201 at 0.343 bar a. The maps are built and tested,
not wired: the decision's anchor, the PFD's, or a throttled motive go back as B-61's options.

**Stage 1, 324E001 / 324F001** (`units/evaporation/first_evaporator.py`): V1's stage line for
line, the T-P fixed point, `core.node.backward_euler_pressure` (V1's `_backward_euler_p`), the
species, LIC-329505's trap; the pull an argument. Six departures, both ways: B-58; decision 20
(the chest on the DDS's 3.7 bar a, read); decisions 10 and 21 (TIC-324001, PIC-329203, PIC-324202
on TT-324001's, PT-329203's and PT-324202's spans, read); decision 23 (PV-324202's trim); decision
11 / B-29 (the leg above its heel); B-21 (the live line). LV-329505 stays linear (its sheet prints
no normal capacity; Open data gaps). **B-62**: a stage with no feed boils nothing — the held melt
superheats to the chest's 151.9 C.

| module | lines | what changed |
|---|---|---|
| `units/evaporation/first_evaporator.py` | 474 | NEW — stage 1 |
| `units/evaporation/ejector_map.py`, `ejector_gas_dynamics.py` | 284, 140 | NEW — the maps (B-57) |
| `thermo/urea_melt.py`, `thermo/extended_uniquac.py` | 154, 547 | the refit and the ceiling (B-58) |
| `data/unit_324.py` | 411 | the refit, the ejector duties, stage 1's data |
| `data/control_valves.py` | 307 | PV-324202 / 203, HV-329605 / 606 |
| `core/node.py` | 289 | `backward_euler_pressure` |
| `units/absorption/vent_line.py`, `data/unit_322c001.py` | 272, 339 | the rated flood (B-60) |
| `tools/convert_overlays.py`, `data/screen_layout.py`, `data/tags.py` | 498, 507, 229 | `DECIDED_EDITS`, `keyswitch_set` (B-59) |

`python -m pytest` — **6902 passed**, exit 0 (6838 at session 32; 64 new). pyflakes clean; the
headless grep prints nothing.

Next:

* **Phase 4, unit 324** — stage 2, 324E003 / 324F003 (its chest on the DDS's 5.9 bar a and
  PT-329212's span, read this session; LIC-324501's drain and the LV-324501A / B selector); the
  vacuum train; then the steam system (the flood's 9-bar user with it).
* Waiting on the process engineer: B-61 (the ejectors' anchor), B-62 (the held melt's boil-off).

### Session 34 — B-61 and B-62 built; stage 2 of unit 324; the mandatory data search

The process engineer decided B-61 and B-62, each as recommended, authorised stage 2's port, and
asked that `CLAUDE.md` mandate the search for plant data: `References\` and every subfolder, then
the `/soft-copy-search` archive, every time (§4, done first). As-Built Part L.

**B-61, the maps on the PFD's design loads** (decision 44). `ejector_map` now scales the vendor
map's capacity so its table gives PFD 706, 712 and 715 at the design vacuums on 4.1 bar a of motive:
K 0.336 (324F002), 0.919 (324F004), 0.497 (324F005); `vendor_map` keeps B-57's anchor, the vendor
duties standing as margin (324F004 526 kg/h at 0.12 bar a against Körting's 761). The motive
pressure answers the motive flow on the choked law, anchored on the design motive
(`nozzle_pressure_bara`). Stage 1 now pulls on 324F002's map at its live motive and discharge
pressures; the design holds at PV-324202's 61.07 %.

**B-62, the held melt boils** (decision 45; `units/evaporation/holdup_boil.py`). Past its own
boiling point at the vacuum the holdup boils x kg in the tick, T' = T* - x lambda / C, to its
anchored equilibrium (Illinois regula falsi). Built first at the fixed point's iterate, stage 2's
Picard rang between boiling and not (20 iterations, unconverged, on a feed loss): the boil-off moves
thousands of kg/h per mbar. It is now evaluated at the trial pressure inside the backward step —
5-6 iterations on stage 2, at most 18 on stage 1. A feed loss on stage 1: the holdup boils (11 t/h
at once), holds at its boiling point and concentrates to 97.07 % at the chest's 151.94 C, where V1's
superheats at 94.30 %.

**Stage 2, 324E003 / 324F003** (`units/evaporation/second_evaporator.py`): V1's stage line for line
on stage 1's pattern; the LV-324501 selector (`route_lv324501` at no UF85, `melt_route`). Eight
departures, both ways: B-61, B-62, B-58; decision 20 (the chest on the DDS's 5.9 bar a, and
PV-329212's loop summary; UA 116.1 kW/K where V1's 8.1 bar a gives 68.2); decisions 10 and 21
(TIC-324002, PIC-329212, PIC-324203 on TT-324002's 160 C, PT-329212's 16 bar and PT-324203's 2 bar
spans, read); decision 23 (PV-324203 on Pos. 56 from 92.03 %); decision 33 (324F003 on the
drawing's 10.7 m3 — its DDS leaves the volume blank; UD-AU-324-DZ-0008-001 prints it, read from the
scan — where V1 takes the 7.427 m3 cylinder); decision 11 (the drain above its heel). Kept as V1,
logged as Open data gaps: LV-324501 linear (no vendor sheet), LI-324501 on the holdup ratio (the
level is in the barometric leg), PV-329212 on V1's chest law (a butterfly, no Kvs).

**B-63** (found): stage 2 takes its feed's urea at the strength stage 1 MADE, while the leg drains
stage 1's holdup; on a 323P003 trip stage 1 makes nothing, so stage 2 takes 71.5 t/h of 96 % melt
as urea-free and boils all of it — -83 C in a minute. V1 does the same. **B-64** (preparing the
train): the PFD's rows 714 / 717 close on its motive, 1220 / 180 kg/h; the maps were built on
Uhde's 1061 / 366 — which the train condenses goes to the process engineer.

| module | lines | what changed |
|---|---|---|
| `units/evaporation/second_evaporator.py` | 505 | NEW — stage 2 and LV-324501's selector |
| `units/evaporation/holdup_boil.py` | 134 | NEW — the held melt boils (B-62) |
| `units/evaporation/first_evaporator.py` | 504 | the map's pull, the holdup boil-off |
| `units/evaporation/ejector_map.py` | 366 | `vendor_map`, the design-anchored `ejector_map`, `nozzle_pressure_bara` (B-61) |
| `data/unit_324.py` | 568 | the design loads; stage 2's data |
| `data/unit_329.py` | 39 | the 9-bar header |

`python -m pytest` — **6944 passed**, exit 0 (6902 at session 33; 42 new). pyflakes clean; the
headless grep prints nothing.

Next:

* **Phase 4, unit 324** — the vacuum train (after B-64): the four condensers in cascade, the
  ejectors on their maps with HV-329605 / HV-329606 on their vendor trims, the condensates to
  328D003, the cold ends back to the stages; then the steam system.
* Waiting on the process engineer: B-63 (stage 2's feed strength), B-64 (the train's motive steam).

### Session 35 — B-63, B-64 and B-24 built; the vacuum train of unit 324

The process engineer decided B-63 and B-64 as recommended and extended B-62 to 323F010 (B-24), and
authorised the vacuum train, "324E002, 324F002, 324E005, 324F005, 324E006, 324F006, 324E007,
324F007". The archive knows no 324F006 or 324F007 (the vendor TOC, the merged P&IDs and the PFD carry
324F001-324F005; References' evaporation mapping draws four condensers and three ejectors): the
train is those seven units, said plainly. As-Built Part LI.

**B-63, the leg's strength** (decision 46; `second_evaporator.leg_urea_strength`): the step takes
no ``feed_w_urea``; the design holds to the bit. V1 both ways: the leg draining while stage 1 makes
nothing, V1's stage 2 at -103.5 C in a minute, the port on its design. The chained trip: stage 2
finishes the leg's 96 % melt (141.9 C at 30 s) and holds 1040 kg at 98.49 % and 165.75 C once the
leg runs dry; it never falls below 140 C.

**B-64, the PFD's motive** (decision 47): `F004_MOTIVE_DES_KGH` 1220, `F005_MOTIVE_DES_KGH` 180 in
`EJECTOR_DESIGN_LOADS`; the nozzle pressure on the PFD's flow. Maps and stages unchanged. On Uhde's
motive 324E007 would see twice its row (87.6 C cold end, 125 kg/h to atmosphere). The 324F002
motive data gap closed by the same rule.

**B-24, 323F010's liquor boils** (decision 48; `holdup_boil.liquor_boil`, the Illinois iteration
shared with `holdup_boil` as `_illinois`, stages 1 and 2 bit-identical): TIC-323012 at 101 C now
concentrates the product to 80.72 % (V1: 80.00 %, 3.9 K superheated); PV-329208 at 60 %, 81.01 % at
101.8 C (V1: 106.5 C); HV-323605 at 80 %, 82.59 % and the level at 75 % (V1: 121.5 %). Because the
boil reads the live PT-323204, a smaller overhead (TIC-323012 at 97 C) now gives 79.24 % where V1
gave 78.97 %. TIC-323012's steps re-measured (B-45): +2 K 5587 s, -2 K 5006 s, no overshoot. The
harness gained ``heel_decided`` (B-29) and ``boil_decided`` switches.

**The vacuum train** (`units/evaporation/vacuum_train.py`, `data/unit_324_train.py`): V1's
``vacuum_train_324`` ported verbatim and executed against — every stream and condenser field ``==``
over eleven input sets; HV-329605 / HV-329606 on Flowserve's trims from 69.06 / 80.16 % (decision
23's class), both ways. In the loop with both stages it holds the design within 0.04 kg/h.

**B-65** (found): the stages read the train's cold ends one tick late, so stage 2's boiling holdup
pulses through a trip (335 pulses in two minutes); a lag on each condenser's tube-side water
residence (11.5 s — quoted 11.6 here, a rounding slip corrected in session 36 — and 7.7 s, from
the datasheets) removes it, measured; solving the cold end inside the
implicit step also does, at 16-52 ms a tick. **B-66** (found): V1 holds 324E006 at 0.3 bar a; as a
live node a lost 324E006 breaks 324F004 and stage 2's vacuum (0.259 bar a), where V1's stage 2 does
not notice.

| module | lines | what changed |
|---|---|---|
| `units/evaporation/vacuum_train.py` | 420 | NEW — the train, the motive valves |
| `data/unit_324_train.py` | 88 | NEW — the train's rows and motive strokes |
| `units/evaporation/holdup_boil.py` | 205 | `liquor_boil` (B-24), `_illinois` shared |
| `units/recirc/pre_evaporator.py` | 550 | the held liquor's boil-off (B-24) |
| `units/evaporation/second_evaporator.py` | 538 | `leg_urea_strength` (B-63) |
| `units/evaporation/ejector_map.py` | 368 | the PFD's motive (B-64), docstrings |
| `data/unit_324.py` | 576 | `F004_MOTIVE_DES_KGH`, `F005_MOTIVE_DES_KGH` (B-64) |

`python -m pytest` — **6976 passed**, exit 0 (6944 at session 34; 32 new). pyflakes clean; the
headless grep prints nothing.

Next:

* **Phase 4** — the steam system: the chests' 9-bar and LP draws, the motive steam's header (the
  three ejectors' 1790 kg/h), the condensate; UF85 with unit 335.
* Waiting on the process engineer: B-65 (the 324 cold-end tears) and B-66 (324E006's shell).

### Session 36 — B-65 and B-66 built; the cascade verified; the steam system surveyed

The full suite of session 35 finished at 6976 passed, exit 0. The process engineer then decided B-65
(option a, the lag) and B-66 (the Typo Rule, a live node), asked for the 324E006 cooling-loss cascade
to be verified without ringing, and authorised the survey of the steam headers and letdown stations.
As-Built Parts LII and LIII.

**`VacuumTrain`** (`units/evaporation/vacuum_train.py`): the train with its state, stepped after the
two stages. `vacuum_train` stays V1's (`==` V1's executed train, unchanged) and takes 324E006's shell
as an argument; it was split, operation for operation, into `_first_condensers` and
`_back_condensers` so the node steps between them.

**B-65, the lag** (decision 49): each cold end a vacuum reads lagged on its tubes' water residence,
backward Euler (`core.signal.first_order_lag`), seeded on the design: 324E002 11.54 s, 324E005 7.67 s,
324E006 3.12 s (the residence session 35 quoted as 11.6 s was 11.55 on a 995 kg/m3 density, rounded up;
the density is now IAPWS's at the water's mean temperature). Through a 323P003 trip V1's tear, V1's
train executed, pulses stage 2's boil-off 335 times in two minutes and sends up to 9.8 t/h to
atmosphere; the port pulses nowhere, the boil-off climbing 110 -> 1110 -> 1251 kg/h over a minute,
722 under 50 kg/h, the melt never below 140 C.

**B-66, the shell** (decision 50): 324E006's shell side 0.542 m3 on Uhde's name plate
(UD-AU-324-DZ-0005-008 rev 01, read from the scan; the datasheet's geometry gives 0.573), its
anchored vent at the lagged cold end against 324F005's map into 324E007's 1.0 bar a, stepped
backward between the map's 0.010 bar a and 324E007's shell. Design seed to 1e-13. **The cascade,
verified:** 324E006's water lost, the shell reaches 1.0 bar a in 2.4 s, 324F004 breaks against it,
stage 2's vacuum climbs to 0.152 bar a in 4.5 s and 0.2587 in two minutes (the melt 140 -> 144.1 C,
PIC-324203 closing its bleed to 73 %), 324E007 sends 1185 kg/h to atmosphere — no pulse in stage 2's
vacuum or the shell. The vacuum is lost to 0.259 bar a, not to atmosphere: 324E005 still condenses
stage 2's vapour and the broken 324F004 keeps 1.4 % of its capacity. The water back, the shell is at
0.3 bar a again in two and a half minutes. A fifth of the water: the shell at 0.360, stage 2 untouched.

**B-67** (found verifying the trip): 324E007's ammonia vent rides a design back-pressure of 24 Pa
against the PFD's 1660, so late in the trip the anchor multiplies the free ammonia's rise by 68 and
324E007 vents its whole inlet (722 at 214 kg/h for two minutes); additive departures keep it at 24-34
kg/h, measured. Raised with options.

**The steam system surveyed** (As-Built Part LIII): V1's `steam_system.py` read in full; the PFD's
steam block closed on IAPWS (329D005's superheat evaporates 8 913 kg/h, 329D009's 274 kg/h — the PFD's
"saturation water"); 322E001's datasheet read (75 300 kg/h, 20.5 bar a, 39 400 kW — V1's figures,
12 % above the PFD's 35.18 MW); the unit 329 loop summaries read from the scans (the ranges, the cases of
every header valve; HV-329602 on PV-329207C's line, its index entry wrong); Flowserve's Pos. 68-70, 74,
75 — LV-329502 (Kvs 63), LV-329503 (100, linear), LV-329504 (40), PV-329205A / B (100) — so decision
23's class applies to five steam valves; the six butterflies have no Kvs (Open data gap). B-68 (the
headers' users), B-69 (the LP header's design pressure) and B-70 (the waters and the floor) raised.

| module | lines | what changed |
|---|---|---|
| `units/evaporation/vacuum_train.py` | 421 | `VacuumTrain`, `cold_end_tau_s`; the function split, a shell argument |
| `data/unit_324_train.py` | 88 | `E006_SHELL_VOL_M3` |

`python -m pytest` — **6982 passed**, exit 0 (6976 at session 35; 6 new). pyflakes clean; the
headless grep prints nothing.

Next:

* **Phase 4** — the steam system's port (`units/steam/`), once B-68, B-69 and B-70 are decided; UF85
  with unit 335.
* Waiting on the process engineer: B-67 (before the scheduler wires the 323P003 trip), B-68, B-69,
  B-70.

### Session 37 — B-67 built; the steam network ported

The process engineer decided B-67 (option a), B-68, B-69 and B-70 (decisions 51-54) and authorised the
steam system's port. As-Built Part LIV.

**B-67** (`units/evaporation/vacuum_condenser.py`): the NH3 and CO2 vent pressures as additive departures,
written so the departure is a literal zero at design. Every equivalence that executes V1's condenser
module now executes a private copy of it with V1's ``vent_moles`` transcribed with the switch
(`tests/equivalence/b67_switch.py`); the stages carry it as one more switch; both ways in
`test_vacuum_condenser_decided_equivalence.py` (324E007 without its CO2: V1 vents its whole inlet, the
port 24.6 kg/h; the trip at two minutes: V1's train 217 kg/h to atmosphere, the port's 30.2). The
train's numbers re-pinned (324E006's shell at 1.0 bar a in 2.2 s; the trip's 722 never above the PFD's
31). Building it showed the mirror on 324E007's CO2, its design back-pressure 159 times the PFD's
partial pressure (B-71, a scaled slope measured and recommended).

**The steam network** (`units/steam/`): the three drums as saturated capacitances over their water, V1's
semi-implicit step in V1's order, the eleven valves, the six pressure and three level loops, the safety
valves. The design closes on the PFD on IAPWS (`data/unit_329.py`): the stripper condenses 66 902 kg/h,
8913 of them 329D005's own water on 902's superheat; 322E002 raises 66 359 and 913 flashes 2570 at 4.0
bar g; LV-329504 makes up 19 501; every node and drum balances to 1e-10 kg/h for an hour, the headers
on their design pressures to the bit, 0.46 ms a tick. Decided classes applied (§5 rule 7): decision 47
(PV-329204 on PFD 902; each unit's draw on its row), 23 / 31 (Flowserve's trims on five valves, read;
LV-329503's and LV-329504's normal capacities calculated by IEC 60534-2-1, the calculation reproducing
every printed capacity to 0.04 %), 33 / 11 (the drums' water over their vessels, the levels between
their taps from 329D005's and 329D009's GAs, a heel and an overflow), 10 / 21 (the gains on span), 26 /
27 / 39 (trip 21.2 on PIC-329204 and HV-329601 from Uhde's functional diagrams, read), 32 (Sempell's
orifice selections for the drums' six valves, read); §4 put HV-329601, PV-329207A / C and HV-329602 on
their loop summaries' maximum cases where V1 gives literal coefficients (HV-329601 vented 288 t/h through
a DN 80 body). PV-329207A / C's 3 % cut-off was measured chattering and not wired. Found: two relays on
instant valves (B-72), the users blind to their header's pressure (B-73), 322E002's model duty 39 % above
its datasheet (B-74).

| module | lines | what changed |
|---|---|---|
| `units/evaporation/vacuum_condenser.py` | 466 | B-67's departure |
| `units/steam/drums.py` | 160 | new |
| `units/steam/steam_valves.py` | 190 | new |
| `units/steam/header_control.py` | 230 | new |
| `units/steam/steam_network.py` | 372 | new |
| `data/unit_329.py` | 211 | the PFD's rows, the users, the closure |
| `data/unit_329_network.py` | 280 | new |
| `thermo/water_steam.py` | 136 | new |
| `data/control_valves.py`, `data/relief_devices.py`, `control/valve.py` | — | five valves, six safety valves, `compressible_shape` |

`python -m pytest` — **7047 passed**, exit 0 (6982 at session 36; 65 new). pyflakes clean; the
headless grep prints nothing.

Next:

* **Phase 5** — the engine and the scheduler on the completed plant (decision 35); UF85 with unit 335.
* Waiting on the process engineer: B-71 (before the scheduler wires the 323P003 trip), B-73 (before it
  wires the steam users), B-72 and B-74 (before Phase 7).

### Session 38 — B-71 and B-73 built; the scheduler

The process engineer decided B-71 (the blended vent law), B-72 and B-74 (Calibration Deferrals) and
B-73 (the Typo Rule: the steam users on physical valve equations against their headers' live
pressures), and authorised Phase 5's scheduler; and asked that the plant started at 100 % load hold
its LP header at 4.0 bar g. Decisions 55-57; As-Built Part LV.

**B-71** (`units/evaporation/vacuum_condenser.py`): a species whose design back-pressure exceeds the
PFD's partial pressure keeps V1's ratio, written operand for operand as V1's; one below it takes
B-67's addition. 324E005 (both species) is V1's on every inlet; 324E007's CO2 is on the ratio — +-1 %
inlet CO2 vents 30.74 / 31.27 kg/h (V1 30.76 / 31.25; the addition gave 23.81 / 37.51). The switched V1
module (`tests/equivalence/b67_switch.py`) carries both decisions; the train's numbers re-pinned.

**B-73.** HV-329605 / HV-329606 on their vendor gas sizing between the live LP header and the
nozzles, the nozzle's pressure solved on the flow (`vacuum_train.motive_ratio`, bisected to the last
bit, the design returned exactly); FV-329401 on V1's butterfly law between the header and 328C004's
bottom (`FlowLoop.step(pressure_ratio=)`, `second_desorber.fv_329401_pressure_ratio`); XV-322915's flood
choked on 329D009's header (`vent_line.flood_steam_kgh`) — the 9-bar header, where the loop summary's
line and session 37's network put it. Measured on the network: 322E002's raising lost, the LP header
bottoms at 3.66 bar a and recovers to 4.09 in five minutes where the fixed users let it fall to 2.11;
no ringing. 328C004 both ways at a 4.1 bar a header: V1 holds 6495 kg/h, the port's FIC-329401 opens to
98.5 % and passes 5640 in twenty minutes.

**The scheduler** (`engine/schedule.py`, `engine/scheduler.py`, `engine/plant/`): the plant's 22 steps
in V1's ``step_sim`` order — the steam network; 323C003 to 323D002; 323C005 to 328D001; 322E006 and
322C001; 323E003, 323E011; the motive valves, both evaporator stages and the vacuum train; the steam
users' meter; I 22.1 — each argument wired from one of five sources, 39 one-tick reads declared with
their reasons, 20 tear writes (`TearState` grew by twelve: unit 324's condensates and inerts, 741,
LV-324501B's recycle, the steam users' draws, 911). The schedule is refused if a unit appears twice,
reads a result not yet made, or reads the future without a declared tear; its order is proved a
topological order of the plant's flowsheet once the declared tears are cut. The liquor train through
the scheduler is ``==`` V1's stages 1 to 4 for 500 ticks; started at 100 % load the assembled plant
holds the LP header at 5.01325 bar a within 2.4e-5 bar, every steam user within 0.02 % of its PFD row,
and runs an hour without a runaway (largest drift 323F010's holdup, 0.16 %). The synthesis loop's
outputs are boundary values at their design (`engine/plant/boundary.py`) until its engine glue is
ported — the next unit. A-10 closed; A-18 raised (a tick costs 10 ms; FAST needs 1.7).

| module | lines | what changed |
|---|---|---|
| `engine/schedule.py` | 246 | new |
| `engine/scheduler.py` | 99 | new |
| `engine/state.py` | 218 | the units, loops, operator, boundary; twelve tears |
| `engine/plant/__init__.py` | 88 | new: the order, the tear writes |
| `engine/plant/boundary.py` | 94 | new |
| `engine/plant/recirc.py` | 155 | new |
| `engine/plant/desorption.py` | 167 | new |
| `engine/plant/absorption.py` | 113 | new (with the trips) |
| `engine/plant/evaporation.py` | 111 | new |
| `engine/plant/steam.py` | 103 | new (with the users' meter) |
| `units/evaporation/vacuum_condenser.py` | 476 | B-71 |
| `units/evaporation/vacuum_train.py` | 472 | B-73's motive valves |
| `units/desorption/second_desorber.py` | 502 | B-73's FV-329401 |
| `units/absorption/vent_line.py`, `lp_absorber.py` | 308, 536 | B-73's flood |
| `control/process_loop.py` | 383 | `FlowLoop.step(pressure_ratio=)` |
| `data/unit_324_train.py`, `unit_328c004.py`, `unit_323.py` | — | the valves' design pressures; PFD 208 as printed |

`python -m pytest` — **7091 passed**, exit 0 (7047 at session 37; 44 new). pyflakes clean; the
headless grep prints nothing.

Next:

* **Phase 5, the synthesis loop** — V1's ``step_sim`` sections 1-6, 34, 36 and 37's loop pressure as
  the scheduler's next unit, with B-3, B-14 and B-15 measured on it, A-16's relief and A-17's
  HV-322604; then `snapshot.py`, `historian.py`, `command.py`; A-18.

### Session 39 — the LP header downstream of 322D001A/B; the synthesis loop scheduled

The process engineer noted that the 4 bar g LP network sits downstream of 322D001A/B (and, mid-session,
that the drums' water boils in 322E002's shell), authorised the synthesis loop's engine glue — V1's
sections 1-6, 34, 36 and 37's loop pressure — and asked that every unphysical sink in the loop-pressure
integration be flagged at once. Decision 58; As-Built Part LVI.

**The LP header** (`units/steam/steam_network.py`): PFD 26 and P&ID 107/1 read from their scans — the
drums' tops discharge 917 into the DN 700 header where PT-329207 sits; 960 joins the header past the
drums; 963, 915 and 916 enter the drums. The port lumped drums and header (as the documents allow: no
drop, no line volume) but published no 917 and boiled 322D001's water with 960's superheat. Now the
drums' balance is written on 917 and 960 boils nothing; at design 917 = 68 929 kg/h (PFD 68 928).

**The synthesis loop** (`units/synthesis/`, `engine/plant/synthesis.py`, `synthesis_loop.py`): V1's
boot pin taken from V1's own cache (its key the hash of V1's present source); the glue as unit modules
(the line pressures, 322R001's lags, nodes and holdup, 322E002's sump, the tempered water, 322E003's
sump, PT-329201); the order V1's, 32 steps, 64 one-tick reads; every synthesis boundary retired. The
transcription of V1's glue, calling V1's own units on V1's pin, ``==`` the port on every tick from the
seed, HV-322605 45 %, HV-322602 60 %, 329P006A stopped, the N/C +5 % and trip 22.2. The seed makes the
PFD's 1302.27 kmol/h of urea and 2.414 of biuret at the profile the reactor runs (B-14 closed), on the
calibration's own throughput (B-15 closed); run to 30 000 s it settles at TT-322014 183.03 C (B-3
closed: V1's recorded 183.49 drift is gone); the 323 stages' CO2 within 1.6 % of design (B-2 to Phase
7). A-16 (322R001's certified valves) and A-17 (HV-322604 on 322C001's pressure) applied and closed for
the loop. Flagged and measured, B-75 to B-78: the residual credit and the recycle tear; the recondensed
backlog (1583 kg lost after five minutes without tempered water); the lumped capacity's double count
(HV-322605 45 %: 11 t in the reactor and 5.5 bar on the node); the inventories (an 80 % turndown stalls
322F001 and loses 28 t/h at 322E003's full sump). A lost motive stalls the simulator — HV-322604's
condensing letdown tabulating its liquor grid, up to 26 s a tick (A-18).

| module | lines | what changed |
|---|---|---|
| `units/steam/steam_network.py` | 406 | 917; 960 into the header; the drums' saturations |
| `data/synthesis_pin.py` | 127 | new: V1's boot pin |
| `data/unit_322_loop.py`, `unit_329_ccw.py` | 108, 56 | new |
| `units/synthesis/loop_hydraulics.py` | 141 | new |
| `units/synthesis/reactor_inventory.py` | 286 | new |
| `units/synthesis/condenser_holdup.py` | 81 | new |
| `units/synthesis/ccw_loop.py` | 121 | new |
| `units/synthesis/scrubber_sump.py` | 95 | new |
| `units/synthesis/loop_pressure.py` | 160 | new |
| `units/synthesis/ejector.py`, `co2_line.py` | 265, 328 | `spindle_phi`; `feed_kgh` |
| `engine/plant/synthesis.py`, `synthesis_loop.py` | 240, 235 | new |
| `engine/plant/__init__.py`, `boundary.py`, `steam.py`, `recirc.py`, `absorption.py`; `engine/state.py` | — | the order, the tear writes, the operator's seeds; the boundaries retired; ``m_308_kgh`` |

`python -m pytest` — **7136 passed**, exit 0 (7091 at session 38; 45 new). pyflakes clean; the
headless grep prints nothing.

Next:

* **The process engineer's decisions on B-75 to B-78**, then A-18 (the condensing letdown's grid);
  `snapshot.py` (with V1's section 6 display lags), `historian.py`, `command.py`; the data for
  decisions 10 / 21 and 39 on the loop's controllers and trips.

### Session 40 — the loop's sinks decided, the motive-loss stall fixed, the operational shell

The process engineer decided the synthesis loop's flagged sinks — B-75 (b), B-76 (b), B-77 (a) with
(b) pursued, B-78 (b) for items 1-3 and (a) for item 4 — required the simulator to survive a lost
motive in real time (A-18), and authorised `snapshot.py` (state saving and loading), `historian.py`
and `command.py`. Decisions 59 to 62; As-Built Part LVII.

**The sinks** (`loop_pressure.py`, `scrubber_sump.py`, `reactor_inventory.py`, `ejector.py`,
`engine/plant/synthesis.py`, `synthesis_loop.py`): PT-329201's residual credit at the reactor's load
ratio; the recondensed backlog into 322E003's sump; the full sump's excess held back in the
scrubber; the forward-carbamate pulse drawn from the sump; the mushy zone on the sump's outflow.
Each both ways against V1's transcription; with every switch on the glue stays ``==`` it. Three new
declared one-tick reads (67). B-77's volumes read from the vendor's arrangement drawings (322R001
185.4 m3, 322E001 24.7, 322E002 21.6, 322E003 10 on the process side); the vapour spaces give about
65 kg/bar against V1's lumped 1500 — the liquors' carbamate buffering must carry the rest in (b).

**The stall** (`thermo/condensing_letdown.py`, `ammonia_backpressure.py`, `node_store.py`,
`tools/build_liquid_state_store.py`): captured and replayed, the lost motive's purge is CO2-rich and
almost dry; no liquor in the model's range condenses from it and the flash ran 50 000 to 100 000
failing evaluations a call while tabulating the grid. The flash now stops at the first isothermal
flash with no answer (every converged answer unchanged, 42 cases to the bit); the liquor heats read
the liquid-state grid (V1's to the bit); both Extended UNIQUAC grids are pre-tabulated, 460 460 nodes
each, in stores keyed on their sources. Measured on the assembled plant, 321P002B stopped by hand, 15 minutes with both stores: a mean tick of 20.4 ms, 4.9 times faster than the plant clock; ten ticks of 103 to 179 ms, which the simulator's half-second passes absorb, and 1.03 s once at start-up (the stores read, 322C001's calibration), before any exercise begins — where session 39 stalled at up to 26 s a tick. B-79 raised (the purge would deposit solid
carbamate on the plant).

**The shell** (`engine/historian.py`, `snapshot.py`, `command.py`, `session.py`,
`data/operator_commands.py`): V1's historian, ``==`` V1's module; exercise save and restore through
JSON, replaying bit for bit; V1's command set with every refusal's process reason; the session the
server attaches to.

| module | lines | what changed |
|---|---|---|
| `units/synthesis/loop_pressure.py`, `scrubber_sump.py` | 168, 116 | B-75, B-76; B-76, B-78 items 1-3 |
| `units/synthesis/reactor_inventory.py`, `ejector.py` | 294, 269 | the pulse from the sump; the outflow's mushy throttle |
| `thermo/condensing_letdown.py`, `ammonia_backpressure.py`, `node_store.py` | 494, 389, 169 | the stop rule; the stores and the liquor heats; new |
| `engine/historian.py`, `snapshot.py`, `command.py`, `session.py` | 299, 315, 598, 128 | new |
| `data/operator_commands.py`; `engine/plant/boundary.py` | 112; — | new; the auxiliary pumps' roster |
| `tools/build_liquid_state_store.py` | 62 | new: builds both stores |
| `tests/equivalence/test_synthesis_loop_equivalence.py` | 616 | three decided switches in the transcription: over the 600-line target, under the 800 limit; the transcription is one function of V1's glue and is not split |

`python -m pytest` — **7184 passed**, exit 0 (7136 at session 39; 48 new). pyflakes clean; the
headless grep prints nothing.

Next:

* **B-79** (the process engineer); `packet.py` — the console packet on V1's key paths with section
  6's display lags — the historian's query over the station protocol and the server's engine loop;
  A-18's FAST pace; B-77 (b); the data for decisions 10 / 21 and 39 on the loop's controllers and trips.

### Session 41 — the console packet, the engine served, Phase 6 opened

The process engineer decided B-79 (option (a): keep the flagged dry outlet and the deposition alarm;
the solid carbamate's dissociation constant a Phase 7 data gap), made the final report's list of
open gaps mandatory (`CLAUDE.md` §7 rule 5), authorised Phase 6, and asked for `packet.py` on V1's
key paths and for the server to honour the arbitration rules. Decision 63; As-Built Part LVIII.

**The packet** (`engine/packet/`, nine modules): V1's `step_sim` return dictionary — every key, its
nesting and its rounding — published from the port's results, unit objects and loops, each value
the port's equivalent of V1's (decided divergences the port's). Proven against V1's source: its key
paths read statically out of ``main.py`` equal the port's, less V1's five diagnostic blocks (A-19).
264 of the screens' 268 bound paths resolve; the four others are unit 335's UF85 faceplates, which
publish None under V1's keys. 2.7 ms a packet, 70 kB of JSON.

**V1's display blocks scheduled:** section 6's ten lags (`units/synthesis/indicators.py`, step
`322-DISPLAY`, ``==`` V1's lifted `_lag1` on every tick through a step and a ramp), and section
33's SIC-323902, 323P001B's standby faceplate (stepped on its own output). FFIC-329401, Uhde's ratio
station, now takes `r323_ctrl_set` (it was refused as "not on this model").

**The engine served** (`net/engine_host.py`, `engine/session.py`, `net/server.py`,
`net/protocol.py`, `run.py`): the plant on a physics thread, each command queued and applied whole
between two ticks, acked with the plant's answer; the pass paid in 10 ms slices, which runs exactly
the steps one call runs; V1's `_health` block; the historian records the packet (704 paths) and
answers `history` / `history_paths`; a NaN publishes as None. Measured over a real socket: real time
at SLOW, acks in arrival order.

**Arbitration:** `r323_ctrl_set` was attributed to unit 323 whatever faceplate it named — a trainee
assigned 323 could move units 328's, 324's and 329's faceplates. It is now attributed by its `id`,
`controller_set` by `id` then `tag` as the engine reads it, PIC-329207A / B / C's commands carry
rows, and a test pins every engine command type to its section. End to end, a trainee assigned 323
is refused LIC-328505, FIC-329402 and HIC-322605, an observer everything, a trainee `freeze`.

**B-79 measured:** in a lost motive the flash has no answer for 127 s of the first 142 s and the
deposition alarm fires for 80 s; its threshold is V1's 20 C, not the 60 C session 40 wrote.

| module | lines | what changed |
|---|---|---|
| `engine/packet/` (`__init__`, `_common`, `unit_321`, `synthesis`, `recirculation`, `desorption`, `evaporation`, `steam`, `streams`, `status`) | 115, 76, 95, 256, 136, 163, 168, 145, 203, 56 | new |
| `units/synthesis/indicators.py`; `data/indicator_lags.py`, `data/console_packet.py` | 101; 67, 120 | new |
| `net/engine_host.py`; `net/server.py`, `net/protocol.py` | 190; 514, 342 | new; awaited answers, history, NaN; the history messages |
| `engine/session.py`, `historian.py`, `scheduler.py`, `command.py` | 203, 303, 104, 600 | the packet, health, history; the lazy sample; the tears read; the ratio station's faceplate |
| `data/tags.py`; `run.py` | 244; 185 | the resolver on the engine's fields; the engine attached |
| `engine/plant/` (`__init__`, `synthesis`, `synthesis_loop`, `recirc`) | 105, 256, 271, 165 | 34 steps; the stripper's duty, the shell's temperature, HV-322604's vent capacity published |
| `units/synthesis/scrubber.py`, `scrubber_sump.py`; `units/steam/steam_network.py`; `units/recirc/lp_carbamate_condenser.py` | 547, 124; 408; 491 | LT-329501's swell and hunt published; the LP header's start-of-tick pressure; SIC-323902 |

`python -m pytest` — **7243 passed**, exit 0 (7184 at session 40; 59 new). pyflakes clean; the
headless grep prints nothing.

Next:

* The console's end of the history request and the trend window; the faceplates; the instructor
  panel (Phase 6). The process engineer's answer on the A-15 / A-16 strategy pasted with this
  session's request, and on A-19. A-18's FAST pace; B-77 (b); the data for decisions 10 / 21 and 39.

### Session 42 — the relief and overflow routings decided, the faceplates and the instructor's panel

The process engineer confirmed B-79 as built, decided A-19 (a) — V1's diagnostic blocks stay out of
the packet — and A-15 and A-16 as the strategy pasted in session 41 laid out, asked for the ejector
design calculations in `References\Datasheets` to be checked, and authorised the faceplates and the
instructor's panel as dumb renderers and command emitters. Decisions 64 to 66; As-Built Part LIX.

**A-16** (`units/recirc/rectifying_column.py`, `engine/plant/recirc.py`, `data/unit_323c003.py`): the
gas an uncovered LV-322501 passes loads 323C003's overhead line by its own volume; SV32351 / SV32352,
on Sempell's certified capacity, pop at 6.01 bar a and relieve the head space — at most the gas it
receives on the tick — reseating at 5.51; what is left goes overhead to 323E003. With no blow-through
and the valves shut the column is V1's to the bit. Measured with LV-322501 forced open: 29.6 t/h
blows through, the valves lift 20 times in the first minute, then the column rides 5.6-5.8 bar a.

**A-15** (`units/recirc/flash_condenser.py`, `engine/plant/boundary.py`, `engine/packet/status.py`):
a full 328D001 overflows into 323E011 as liquid, the same tick; 328C003's, 328C004's and 322C001's
overflows are boundary sinks, read by no unit, published as the port's ``BOUNDARY_SINKS``. The
routing made a full 323D011 reachable: decision 11's ceiling is applied to its envelope (4204.5 kg),
and its overflow's destination and the node's ring at its vapour floor are A-20.

**A-19** closed both ways in `test_packet.py`. **The ejector documents:** `References\Datasheets`'
322F001 and 324F00x design calculations are AD 2000 strength calculations; 322F001's vendor file was
read whole — its operating instructions name 14 performance diagrams that are not in the archive.

**The faceplates and the instructor's panel** (`hmi/faceplates/`, `hmi/instructor/`,
`data/faceplates.py`; `net/protocol.py`, `net/server.py`, `hmi/bridge.py`, `engine/session.py`):
V1's routing and faceplates, the operator's typed field kept, ENTER as SET, every command one the
engine takes (tests apply each to a plant); V1's three front-end defects corrected — HIC-329605 /
-329606 / -323605 send ``op`` (V1's ``value`` was never read), no browser-kept loop state, and
FIC-328406's decided cascade offered (its whitelist row was V1's MAN alone). The panel: pacing,
freeze, reset, the malfunctions, exercises, unit assignment, with the roster pushed to instructors and
the exercise list answered on the protocol.

| module | lines | what changed |
|---|---|---|
| `hmi/faceplates/` (`__init__`, `base`, `controller`, `speed`, `pump`, `hand_valve`, `switches`, `master_setpoint`, `indicator`) | 97, 272, 182, 105, 75, 62, 111, 149, 49 | new |
| `hmi/instructor/panel.py`; `data/faceplates.py`, `data/unit_323c003.py` | 272; 190, 63 | new |
| `units/recirc/rectifying_column.py`, `flash_condenser.py`; `data/unit_323e011.py` | 567, 500; 328 | A-16's blow-through and relief; A-15's overflow and the envelope's ceiling |
| `engine/plant/recirc.py`, `boundary.py`; `engine/packet/__init__.py`, `status.py` | 184, 95; 123, 70 | the routings; the sinks; ``BOUNDARY_SINKS`` |
| `net/protocol.py`, `server.py`, `engine_host.py`; `engine/session.py`; `hmi/bridge.py`, `main_window.py`, `theme.py` | 371, 555, 192; 210; 334, 440, 203 | the roster and the exercises; the exercise list; the faceplates, the Instructor menu, the faceplate tokens |
| `data/operator_commands.py` | 114 | FIC-328406's modes |

`python -m pytest` — **7312 passed**, exit 0 (7243 at session 41; 69 new). pyflakes clean; the
headless grep prints nothing.

Next:

* The trend window and the console's history request; the stream inspector (Phase 6). A-20 (the
  process engineer). A-18's FAST pace; B-77 (b); the data for decisions 10 / 21 and 39.

### Session 43 — 323E011's overflow to 323C005, the history request and the trend window

The process engineer decided A-20 (b) — a full 323E011 / 323D011 envelope overflows through
PV-323203's vent line into 323C005 — asked for the node's oscillation to be measured on it, and
authorised the console's history request and the trend window, which plots the engine historian over
the protocol and keeps no samples of its own. Decision 67; As-Built Part LX.

**A-20** (`units/desorption/atmospheric_absorber.py`, `engine/state.py`, `engine/plant/__init__.py`,
`engine/plant/desorption.py`): the overflow and its temperature are two new one-tick tears into
323C005 (it steps before 323E011); liquid, with its sensible heat, to the sump and on to 328D003.
With none the column is V1's to the bit. Measured with LIC-328501 shut: the envelope overflows 7.4 to
9.4 t/h from about 2650 s; 323C005's sump 10.7 kg, PFD 343 42.5 t/h, the liquor 52 to 54 C.

**The node still rings** — 0.87 to 1.63 bar a at full envelope, as before: the routing is downstream
and does not reach it. A tick-by-tick trace shows a four-tick limit cycle between the node at its
2 % vapour floor (0.0875 m3 against 3.14 at design) and 323F004's one-tick-late flash. Filed with
B-51's class (a full vessel's vapour-space integral at its floor, deferred to the solver review on
2026-09-30). Measured, not built: with 323F004's own vapour space (1.08 m3, its datasheet shell above
its level set point) in the node's volume, the same snapshot runs without a ring — for the process
engineer, a new mechanism.

**The history request and the trend window** (`hmi/bridge.py`, `hmi/trend/`, `data/trend.py`,
`hmi/theme.py`, `hmi/main_window.py`, `hmi/widgets/base.py`, `hmi/screen_view.py`): V1's ten pens,
seven spans and a typed one, ten rulers, MIN / MAX / AVG, LOW / HIGH, marking, the quarter-span
scroll and both clocks; the historian the only source, asked for the whole window once a second with
one request in flight (4.4 ms of the physics thread for ten pens over an hour); a refusal or a lost
link blanks the pens. A pen is added from an element's menu or by dragging the element onto the plot
or a row; a click now fires on release without a drag, as V1's browser click did. The plot is
pyqtgraph's (0.14 installed), added to `requirements.txt`; only the console imports it.

| module | lines | what changed |
|---|---|---|
| `hmi/trend/` (`__init__`, `series`, `plot`, `table`, `window`); `data/trend.py` | 14, 229, 179, 200, 544; 80 | new |
| `hmi/bridge.py`, `main_window.py`, `screen_view.py`, `widgets/base.py`, `theme.py` | 372, 494, 181, 165, 252 | the history request; the trend window, its menu and the drag; the click on release; the trend tokens |
| `units/desorption/atmospheric_absorber.py`; `engine/state.py`, `engine/plant/__init__.py`, `desorption.py` | 400; 230, 107, 175 | A-20's overflow into the sump; its two tears |
| `units/recirc/flash_condenser.py` | 502 | the overflow's destination in its docstring |

`python -m pytest` — **7342 passed**, none failed (7312 at session 42; 30 new), in two parts: the
full run stopped at its 30-minute background limit after 6928, and the last 443 were run again, exit 0. pyflakes clean; the
headless grep prints nothing.

Next:

* The stream inspector (Phase 6); A-2's station login. The 323F004 vapour space for the 323E011 node
  (the process engineer; B-51). A-18's FAST pace; B-77 (b); the data for decisions 10 / 21 and 39.

### Session 44 — the display gaps decided, single-machine mode, the stream inspector, the data report

The process engineer decided B-51's 323E011 instance (323F004's vapour space in the node), deferred
A-2 and A-8 until the physical and UI port is complete — one machine, one console with universal
permissions, the instructor's panel paused — authorised the stream inspector, asked for the Phase 6
display gaps to be resolved as scheduled on 2026-09-29, and attached an archive report made by another
tool to be checked against the open data gaps. Asked this session: B-9 (one ceiling, 183 C) and the
station login (deferred with A-2). Decisions 68-72; As-Built Part LXI.

**B-51, 323E011** (`data/unit_323e011.py`, `units/recirc/flash_condenser.py`): 323F004's 1.083 m3
vapour space added to the node's free volume. A full envelope holds 1.1300 bar a where the envelope
alone rang 0.59-1.82 bar a; from session 43's full-envelope snapshot the node falls smoothly to 1.13
in ten minutes, where it rang 0.87-1.63. Every node transient slows by a third (3.14 to 4.22 m3).

**The display gaps.** B-9 (`units/synthesis/stripper.py`): the two flood rises share one ceiling,
``max``; a flooded stripper tends to 183 C, V1's to 194. B-16 (`data/unit_322e003.py`): TT-322002 on
the PFD's 165 C, the conductance 58.5 to 69.0 kW/K, the ejector's 178.8 kept; the overflow 20 C under
its ceiling where V1's sat 6.2 C under it. B-6 / B-7 (`core/units_of_measure.py`): one atmosphere,
1.01325 bar, and one gravity, 9.80665, everywhere; SV-32201 161.01325 bar a, trip 21.2's 11.01325 /
13.01325, the 322C001 vent at 1.01325. B-11: V1's 120 s TT-322012 lag, built in session 41, ramps the
ejector's 140 C branch step on the screen — closed. B-5: no two thermocouples share a path on V1's
reissued screens — closed.

**Single-machine mode** (`net/protocol.py`, `net/server.py`, `run.py`, `hmi/main_window.py`):
``Role.SUPERUSER`` — every command, the instructor's lists, never assigned — granted to a loopback
peer only; `run.py`'s default console. **The stream inspector** (`hmi/widgets/stream_hotspot.py`):
V1's ``renderStream`` on the packet's ``STREAMS``, proved string for string by executing V1's own
JavaScript in node over every published stream; an analyser shows the composition; it redraws from
every packet (V1 filled its popup once).

**The data report.** Every cited document opened. Found in the archive and recorded: Nuovo Pignone's
320K002 performance curves (UD-AU-320-DZ-0001-165, the gap said none existed; not digitised); the
isometric files for units 323 / 324 (A-11's run lengths now measurable; not measured); 323D002's
overflow nozzle (N12, EL +5452) and seal pot; the HP angle valves' CONVAL sets (HV-322605 already the
port's Kv table; XV-322902 / 322903 on/off, Kvs 196); FO-329458 / 329459 at 30 kg/h each; FT-329409's
and TT-329005's spans — on which FIC-329409 and TIC-329005 now run the DCS table's rows (decision 10's
class; a 10 % flow cut settles in an hour where V1's tuning took two minutes). Refuted: gas
coefficients on the liquid-rated relief valves, an overflow on 328D003's trim isometric. Uncited web
values (Henry constants, carbamate dissociation) not taken.

| module | lines | what changed |
|---|---|---|
| `hmi/widgets/stream_hotspot.py` | 153 | new: the stream inspector |
| `hmi/faceplates/__init__.py`, `main_window.py`, `theme.py`, `state_access.py` | 104, 496, 256, 159 | the inspector routed; the superuser's menu; the inspector's cells; the one atmosphere |
| `net/protocol.py`, `net/server.py`, `run.py` | 400, 582, 195 | the superuser |
| `units/recirc/flash_condenser.py`, `data/unit_323e011.py` | 517, 343 | B-51: 323F004's vapour space |
| `units/synthesis/stripper.py` | 604 | B-9 |
| `data/unit_322e003.py`, `units/synthesis/scrubber.py`, `data/unit_322f001.py` | 515, 547, 303 | B-16 |
| `core/units_of_measure.py`; `data/unit_320.py`, `unit_321.py`, `unit_329.py`, `unit_329_network.py`; `units/feed/feed_drum.py`, `station.py`; `units/absorption/vent_line.py`; `engine/packet/steam.py` | 175; 210, 250, 212, 281; 216, 297; 308; 145 | B-6 / B-7 |
| `data/unit_329_ccw.py`, `units/synthesis/ccw_loop.py` | 73, 124 | the CCW loops on the table's rows |

`python -m pytest` — **7413 passed**, one skipped (the screen geometry, which needs the console's
fonts), run in four parallel parts; the eight tests those parts failed — pins the session's
decisions moved — re-pinned and rerun green (7342 at session 43; 71 new). pyflakes clean; the
headless grep prints nothing. `stripper.py` is 604 lines (the target is 600; the B-9 comment);
`test_flash_condenser_equivalence.py` 799.

Next:

* For the process engineer: digitise 320K002's vendor curves and put the machine on them; measure
  A-11's routes on the isometrics; model the 90 kg/h of trace steam in 322C001's vent line; read
  323P008's own documents for a low-level trip. A-18's FAST pace; B-77 (b); decision 39's data
  (trips 21.x / 22.2).

### Session 45 — 320K002 on its vendor's curves, the isometrics' routes, the trace steam; Phase 7 begun

The process engineer decided four items on 2026-10-07 — "If vendor data exists, we use it": 320K002
onto Nuovo Pignone's curves; A-11's routes measured on the isometrics; 322C001's 90 kg/h of trace
steam modelled; FIC-329409 and TIC-329005 kept on the DCS table's rows — and authorised Phase 7, the
transient runner first, B-51's ringing to be watched. The session ended on the usage limit before any
document was updated; session 46 recorded it (As-Built Part LXII).

**320K002** (withdrawn in session 46): the vendor's stage curves digitised from the scans (every speed
line of the four stages, 21 points each, drawn back over the scan), the machine stacked stage by stage
on its data sheet's normal point with SRK's Z, from the PFD's 1.3 bar a / 35 C suction; it reproduced
the vendor's overall curve within 0.5-3 % of flow and its 148.0 bar a within 0.06 bar, and surged at
80 % load where V1's map did not. **A-11** (`data/process_routes.py`): each route's straight pipe and
long-radius elbow arcs from its isometric's bill of material, each size at its own bore — dead times
28.2, 32.6, 23.1, 30.5 and 25.0 s where V1's estimates gave 21.8, 16.0, 16.8, 36.9 and 49.1; the
harnesses take them through `tests/equivalence/routes_switch.py`. **The trace steam**
(`units/absorption/vent_line.py`, `data/unit_329.py`, `data/unit_322c001.py`, `engine/plant/steam.py`):
FO-329458 and FO-322457's 60 kg/h into the vent line, mixed into TI-322015, FO-329459's 30 kg/h into
SV32253's discharge, all three choked on the 9-bar header and taken out of PFD 910; TI-322015 reads
53.7 C at design (46.0 before; the DCS 43.4). **Phase 7**: `tests/phase7/scenarios.py` and
`drivers.py` written.

### Session 46 — 320K002 a boundary feed, the DCS's tunings, the Phase 7 runner run

The process engineer revised 320K002 — outside the simulation's scope, a fully automated boundary
feed, no operator intervention or faceplate — confirmed A-11, the trace steam and the CCW tunings,
asked for session 45's documents, the runner finished and its four transients run, and the original
DCS tuning constants found in the attached table. Decisions 73-77; As-Built Part LXII.

**320K002** (`units/synthesis/co2_compressor.py`, `units/synthesis/co2_line.py`, `data/unit_320.py`,
`net/protocol.py`, `engine/packet/status.py`): the boundary delivers the demand into the discharge line
— no curve, speed, surge or stonewall; `co2_set` instructor-only; V1's surge and stonewall flags no
longer published; `control/machines.py`, `data/unit_320_k002.py` and their tests deleted. A part load
is delivered on the first tick (V1's governor: 54.1 t/h on the first tick, 43.7 after ten minutes),
the settled line the same to 1e-6.

**The DCS's tuning constants.** The attachment is `References/Master_PID_Tuning_Constants.md` byte for
byte. Every loop audited against it: 45 of its 50 rows for units 321-329 already ran; LIC-322501 (0.20,
280 s, a 1.0 s derivative behind a 1.0 s filter), SIC-321950 (4.00, 35 s) and SIC-321951 (1.20, 50 s)
still ran V1's and now run their rows, checked on the faceplate photographs, the SICs' gain on
SI-321950's 0-180 rpm (UD-MR-321-EC-0001, line D07). Measured: LIC-322501 settles in 1.8 h where V1's
settled inside 4,000 s; an emptied sump in AUTO blows 28 kg of gas through to 323C003 before the seal recovers;
starting the standby 321P002A in cascade overshoots the N/C to 2.31. FFIC-321404A / B are a structure
V1 did not build (B-85).

**A port defect found by the runner**: the console's PT-329201 (``EJ_322F001.PI_329201``) and 322E003's
``P_overflow`` / ``P_offgas`` published the scrubber's design pins, 140.7 bar a whatever the loop did;
V1 overwrites them with the live loop pressure (`main.py` 8105-8106). Fixed in
`engine/plant/synthesis_loop.py` and pinned (`tests/engine/packet/test_synthesis.py`). **And a second**: the port's
first cold start ran its evaporators away (324F001 to 1635 C) and crashed at 8112 s — 324F001, boiled
dry on its floor for 6000 s, gave a pure-urea vapour above its melt's ceiling, and `holdup_boil`'s bound
went negative, condensing vapour the stage did not hold; run again, 324F003 boiled itself through 0 C
below the melt model's 99 C window, where the equilibrium holds its edge. A melt whose vapour cannot
concentrate it, or below the window, no longer boils, nor below the edge
(`units/evaporation/holdup_boil.py`, pinned on both captured states).

**The Phase 7 runner** (`tests/phase7/`): `compare.py`, `run.py` (``--side both|v1|port|compare``),
`test_scenario_runner.py`; the four scenarios run on both engines at the fixed 0.1 s step.

Results (As-Built §LXII.4). **Cold start**: PT-329201 on both inside the start-up trend's tau and
dead-time band (V1 3825 / 435 s, the port 3645 / 405 s); V1 settles at 145.1 bar g, in band, the port
overshoots to 146.4 bar a and sags to 134.9 bar g, 2.6 bar under it; 328C004 floods on the port from
11 000 s (LI-328505 514 % at the end; V1 50 %) and then rings, B-51's instance in a realistic run
(B-87). **Trip 22.2**: V1 latches at 20 099 s, the port at 14 769 s; trip 22.1 first on both (299 /
66 s); after the latch the port's stripper sump drains to 0 % on the DCS's LIC-322501 where V1's
holds 38.7 %. **HPCC rupture**: the two track — PT-329201 to 137.2 / 136.8 bar a, N/C to 2.01, 322R001
flooded — and part where a decision acts. **Vacuum break**: both break 324F001's vacuum (0.709 / 0.585
bar a) and recover (1765 / 1330 s). **B-51** flooded on purpose: both engines ring (V1 1.32 bar, the
port 2.54 bar peak to peak in 10 s). Two port defects found and fixed: PT-329201 published at its
design pin, and the held melt's boil past the melt model's reach.

| module | lines | what changed |
|---|---|---|
| `units/synthesis/co2_compressor.py`, `co2_line.py`; `data/unit_320.py` | 53, 317; 173 | 320K002 a boundary feed |
| `control/machines.py`, `data/unit_320_k002.py` | deleted | the vendor curves withdrawn |
| `net/protocol.py`, `engine/packet/status.py`, `engine/plant/synthesis.py`, `engine/command.py`, `engine/packet/synthesis.py`, `data/tags.py` | 402, 68, 258, 600, 256, 245 | `co2_set` instructor-only, the flags dropped, the loops re-indexed |
| `data/unit_321.py`, `data/unit_322e001.py`, `units/synthesis/stripper_sump.py` | 273, 562, 574 | the SICs and LIC-322501 on the DCS's table |
| `engine/plant/synthesis_loop.py` | 274 | PT-329201 published live |
| `units/evaporation/holdup_boil.py` | 222 | a dry melt, or one below the model's window, does not boil |
| `data/process_routes.py`, `data/unit_329.py`, `data/unit_322c001.py`, `units/absorption/vent_line.py`, `units/absorption/lp_absorber.py`, `engine/plant/steam.py` | 186, 238, 351, 353, 545, 116 | session 45: A-11's routes, the trace steam |
| `tests/phase7/` | 902 | the transient runner |

`python -m pytest` — **7264 passed**, none failed, run in six parallel parts (7413 at session 44: the
vendor curves' and V1's map's equivalence tests went with the modules; the first run of the six
failed six pins the tunings moved, and the evaporator fixes two — re-pinned, the values before kept
in the docstrings, and rerun green). pyflakes clean; the headless grep prints nothing. `engine/command.py` is 600 lines;
`test_flash_condenser_equivalence.py` 800.

Next:

* For the process engineer: the Phase 7 comparison (As-Built §LXII.4); B-51's integration strategy
  (it rings in the port's cold start); B-81 to B-87; B-28 (the deadband) before the loops are compared
  on trends; the steady-state comparison at 1750 MTPD; A-18's
  FAST pace; B-77 (b); decision 39's data (trips 21.x / 22.2).

### Session 47 — the session 46 decisions verified as built

The process engineer re-sent the 2026-10-07 / 08 decisions (320K002 a boundary feed, A-11 on the
isometrics, 322C001's trace steam, FIC-329409 and TIC-329005 on the DCS table) with the same next
steps: the 320K002 refactor, the routes and the trace steam, the interrupted documents, and the
Phase 7 runner and its four transients. Every item was already built and recorded in session 46
(decisions 73-76, As-Built Part LXII); nothing was rebuilt. Verified instead:

* the code: `units/synthesis/co2_compressor.py` the boundary (``delivery = max(demand, 0)``),
  `control/machines.py` and `data/unit_320_k002.py` gone with no import left, ``co2_set``
  instructor-only, no 320K002 element on any screen or faceplate; `data/process_routes.py` on the
  isometrics; the trace steam in `units/absorption/vent_line.py`, `data/unit_329.py` and
  `engine/plant/steam.py`; FIC-329409 (0.60, 250 s) and TIC-329005 (1.50, 300 s) on their spans in
  `data/unit_329_ccw.py`;
* the runner: `tests/phase7/` (`scenarios.py`, `drivers.py`, `compare.py`, `run.py`,
  `test_scenario_runner.py`) and the four reports and records of session 46's runs, outside the tree;
* the documents: decisions 73-77, handoff B-81 to B-87, As-Built Part LXII, `CLAUDE.md`'s scope
  boundary.

Document drift fixed: this file's status line and date (still session 44's), its scope table and
Phase 4 entry now name 320K002 a boundary feed; `README.md` and `ureasim/__init__.py` no longer list
`machines` in `control/`; `README.md` gives the Phase 7 command line. No equation was touched, so the
As-Built reference is unchanged.

`python -m pytest` — **7264 passed**, none failed, none skipped, run in six parallel parts (the same
count as session 46). pyflakes clean; the headless grep prints nothing.

Next: as session 46's list — the process engineer's reading of the Phase 7 comparison (As-Built
§LXII.4) and the decisions it waits on (B-51, B-81 to B-87, B-28); the steady-state comparison at
1750 MTPD; the overlay geometry test; A-18's FAST pace; B-77 (b); decision 39's data.

**Session 47, continued — B-51 and B-83 decided and built, B-87 traced (As-Built Part LXIII).** A
second paste carried an external tool's report claiming B-51's implicit step and SV32064 built and
B-87 traced; that tool said itself it had no access to the files, and the tree had not changed. The
process engineer then decided, asked: B-51 switched on the step's own stability (decision 78) and
B-83 option (a) (decision 79). Built:

* `core/node.stable_pressure_step` — V1's explicit step where dt . df/dP >= -1, to the bit;
  `backward_euler_pressure` in a bracket where it is below; used by 328C004, 750 re-evaluated at the
  settled pressure. Flooded at 0.1 s V1's explicit step rings (62 windows, 2.09-4.76 bar a), the port
  holds 3.6997-3.6998 bar a; session 46's whole-plant flood no longer rings (no reversal in any 10-s
  window, 3.23-3.78 bar a, where it swung 2.4-4.7). It also acts where 750's differential closes
  towards zero (the LP steam lost).
* SV32064 on the CO2 line node: Sempell's orifice selection read (UD-RL-G00-DZ-0001-001 page 72,
  orifice H, 74 444.40 kg/h at 177.013 bar a, alpha_w 0.654, lift-limited); set 161.013, reseat
  145.013 bar a; a blocked line at the design feed holds 147.55 bar a with the valve lifted, where V1
  packs on; published in ``BOUNDARY_SINKS`` (V1's ``CO2_FEED`` has no key for it).
* B-87 traced on both engines: the flood starts in unit 324. 324F003 parks at the melt model's
  99 C edge (B-86) at 0.02 bar a; with 324E006 at its 0.01 bar a floor, 324E005's vent goes
  negative and the condensates 720 / 721 take the same positive — 3 298 t into 328D003 in 339
  ticks, 1 331 t in the first; the tank fills from 41.9 to 100 % in 10 s; 735, drawn in proportion
  to its holdup, doubles to 62 t/h; LV-328505 on its vendor trim saturates from 11 400 s and
  328C004 floods. Options in handoff B-87. B-88 raised: after trip 22.2 SV32064 relieves the whole
  CO2 feed, since XV-322902 shuts while the boundary keeps delivering.

`python -m pytest` — **7273 passed**, none failed, none skipped, run in six parallel parts (9 new:
`tests/core/test_node.py` 6, B-51's both-ways test, SV32064's part-load cycling, its sizing datum).
pyflakes clean; the headless grep prints nothing.

Next: the process engineer's decisions on B-87 and B-88; the rest of session 46's list — B-81, B-82,
B-84 to B-86, B-28; the steady-state comparison at 1750 MTPD; the overlay geometry test; A-18's FAST
pace; B-77 (b); decision 39's data.

### Session 48 — B-86, B-87, B-88, B-39, A-7, B-13, B-82 and B-89 decided; the steady state at 1750 MTPD

Two pastes of the process engineer's decisions, each answering the options the last report listed.

**The first** (As-Built §LXIV.1-6): B-87 as option (b) with (c) — "the conservation rule" and "the
topology rule"; B-86 option (c), "the extrapolation rule"; B-88 option (c). Built:

* `vacuum_condenser.vent_moles` floors every vented species and the inerts that size the vent at
  zero (decision 80): at Phase 7's burst 324E005's inlet booked 1.889 kmol/h of N2 below zero and
  vented -2.2e10 kg/h; now 1.322e6, condensing no more than arrives. The V1 transcription
  (`b67_switch`) carries the floor.
* FIC-328402 on 735 (decision 81, B-39 closed): the loop at 735's density, FV-328402's stroke on it
  (58.40 %), 744 the PFD's while 322P002 runs (P&ID 102 draws no control valve, FI-322402 only),
  328D003's level the operator's (LT-328507 / 508 open-loop). The tank's transcription carries a
  ``b39`` switch; the console keeps V1's key, the indicator's note a decided edit.
* `holdup_boil`: no boil when the melt's boiling point at the live vacuum lies below the window
  (decision 82).
* Trip 22.2 takes the CO2 boundary's demand to zero, a demand refused while latched (decision 83).
* Re-run (V1's records unchanged): the cold start no longer floods 328C004 (LI-328505 49.4-50.8 %,
  V1 49.8-50.1; session 47 to 513.9 %); the train's books close on every tick, every vent >= 0;
  328D003 peaks at 50.02 %; trip 22.2 latches at 15 031.2 s (264 s later, from B-39's 735).
* The steady-state comparison at 1750 MTPD (`tests/phase7` ``steady_state``: every packet leaf, an
  hour, both engines): 3 084 of 3 188 shared leaves within 1 %; the 104 others each a decided
  divergence but 323E011's creep (B-89 raised); no trip, no ringing.
* The overlay gate measured on the installed fonts: A-7's five pinned collisions and no other.

**The second** (§LXIV.7-11), with the instruction to finalize every session before the context limit
(now `CLAUDE.md` §3): A-7 — zero overlap, nav labels win, crossings one pixel clear, TV-323013B
nudged; B-89 accepted and closed; B-13 — the gate at 1.0; B-82 — the HPCC rupture rebuilt, process
into the shell; A-18 — targeted profiling and caching. Built and measured:

* The converter's ``NUDGE`` table (decision 84): five rows, zero overlap on all ten screens.
* B-13 (decision 86) was already the state of both engines: the port passes 1.0 and V1's ``step_sim``
  sets ``g_dist = 1.0``, never calling its ``_disturbance_gate``; the docstrings record it.
* `units/synthesis/tube_leak.py` (decision 87): the instructor's ``trigger_fault`` ``322E002`` with a
  rate in t/h at the design differential; the leak on sqrt(dP / dP_des), out of PT-329201's
  boundary; its volatiles to the LP steam, its water and solids to 322D001A/B's water, its heat on the
  elements datum (10 t/h at design: 9.31 t/h to the steam, 0.69 t/h to the drums, -1 382 kW,
  condensing 2.36 t/h of steam). The Phase 7 HPCC rupture now runs it on the port: PT-329201 134.8
  bar a after the six steps (V1's water 137.2), the reactor's level 35.7 % (V1's 100 %); trip 22.1
  latches at 3 378.9 s in the 40 t/h step — the off-gas turns ammonia-rich with the reactor drawn
  down, 322C001's vent crosses V1's 57 C, B-84's 3.3 K margin.
* A-18: a design tick 10.35 ms; the named bottlenecks 37 % of it, so not enough for FAST's 1.7 ms even
  at no cost; exact caching measured no gain, none built; open.
* B-90 raised: the leak's contamination shows on no console instrument, and the paused panel has no
  rate entry for it.

`python -m pytest` — **7284 passed**, none failed, none skipped, run in six parallel parts (11 new). pyflakes clean; the headless grep prints nothing.

Next: the process engineer's reading of the steady state and the re-runs; B-90; A-18's options;
the rest of the open list — B-81, B-84, B-85, B-28, B-25, B-77 (b), decision 39's data.

### Session 49 — seven open items decided; the loop's vapour inventory; trips 21.x as AC4 executes them

Two pastes of the process engineer's decisions (As-Built Part LXV).

**The first** decided A-18, B-90, B-84, B-81, B-85, B-28 and B-25 (decisions 88-94) and set the next
steps. Built:

* FFIC-321404A / B (`units/feed/station.py`, decision 92): PI ratio controllers on FY-321404's 0-4
  span, 1.00 / 100 s and 1.00 / 90 s, each its SIC's external set point and tracking a SIC not on
  cascade; V1's open-loop demand deleted. A 10 % CO2 step is back within 0.005 in 539.8 s (V1's
  demand 375.3 s); harness switch ``b85``.
* The letdowns' lines two-phase (`data/process_routes.py`, decision 91): the homogeneous density on
  each valve's design flash, the valve's place read from the isometrics; 2.32, 13.75 and 21.88 s for
  28.17, 32.63 and 23.06 as liquid plugs.
* AI-329701 (`units/steam/condensate_analyser.py`, decision 89): the leak's ammonium bicarbonate in
  the LP users' condensate, 0-10 uS/cm with an over-range flag, in the port block ``ANALYSERS``; the
  malfunction takes ``rate`` / ``value``, 10 t/h on a bare trigger; the instructor's panel a rate box.
* B-28 (decision 93): LIC-329505's 2 % deadband set to zero too. A-18, B-84 and B-25 closed as decided
  (decisions 88, 90, 94), nothing to build.
* B-77 (b) measured on the cold start (a pure vapour node: tau 990 s, 151.95 bar g) and AC4's trip 21.2
  read; both put back to the engineer.

**The second** decided both. Built:

* PT-329201 on the loop's vapour inventory (`units/synthesis/loop_pressure.py`, decision 95): 241.7
  m3 less the liquid the model holds, Z_des 0.7627 on the PFD's off-gas density, the reactor liquor's
  buffering 0.015364 kg/(kg.bar) — the Extended UNIQUAC slope of PFD 207's bubble pressure anchored on
  its 141.3 bar a — 2 160 kg/bar at design against V1's 1500; each holdup's gain over its own step is
  liquid, not pressure (322R001, 322E003's sump, LT-322E002, LT-322501 publish it); the backlog no
  pseudo-mass. Harness switch "B-77". HV-322605 to 45 %: V1 +0.54 bar in two minutes, the port -0.01.
* Trips 21.2, 21.8 and 21.10 as AC4 executes them (`control/interlocks.Unit21Trips`, decision 96):
  the paste's premise that AC4 draws 21.4 and 22.2 did not hold — re-read, 21.8 and 21.10 are on the
  pumps' motor pages (5, 7), 21.4 has no flag, 22.2 is the Safeguard's; asked once, answered "build as
  drawn". Live flags, no reset; 21.2 shuts XV-321901 / XV-322901, each pump's flag stops its machine;
  the bypass and trip hand switches keyswitches; the DCS limits the archive lacks stand-ins or not
  modelled (Open data gaps); 22.2 V1's. Harness switch "A-12".
* The Phase 7 scenarios re-run (§LXV.7): the steady state 3 083 of 3 188 shared leaves within 1 %; the
  vacuum break without a trip; the HPCC rupture holds PT-329201 at 139.0 bar a (session 48 134.8)
  and stops 0.7 K short of trip 22.1, AI-329701 over range from its first step. **The cold start no
  longer pressurises** — 30.4 bar a after 16 000 s (V1 146.2): the design-anchored units condense
  their design fractions at any loop pressure, so the boundary's inflow is liquid and the vapour
  inventory starves; and with the tempered water lost the loop settles near 147 bar a without trip
  22.2. Decision 95's own test is failed: B-91 raised with options.

`python -m pytest` — **7304 passed**, none failed, none skipped, six parallel parts. pyflakes clean;
the headless grep prints nothing.

Next: B-91 — the cold start and trip 22.2 on the vapour inventory, the process engineer's choice
among its options; the reading of the other re-runs (the HPCC rupture no longer reaches trip 22.1); AC4's limits and the hand switches' types; trip 22.2's
Safeguard logic; screen elements for AI-329701 and the trip 21.2 hand switches (``DECIDED_EDITS``).


### Session 50 — B-91 (a) and the reactor's boiling cap; B-18, B-37 and B-20 closed; the hand switches on the screens; the plant DCS's readback

Two pastes of the process engineer's decisions (As-Built Part LXVI).

**The first** (2026-10-10) decided B-91 option (a), the converter's decided edits for trip 21.2's
five hand switches and AI-329701, B-18 at 72 %, B-37's 734 into 323E003 and B-20's urea on the drain
(decisions 97-101), with the Phase 7 cold start and trip 22.2 to be verified in the 137.5-150.5 bar g
band. Built:

* The saturation fraction (`units/synthesis/liquor_saturation.py`, decision 97): f = 1 - b_207 . d
  on the deficit of the loop below PI-322E002 of the tick before less the 3.5 bar design head;
  322E002's melt holds f of its liquid, 322E003 condenses at most f, the reactor buffers f of b_207.
  f is 1 at design. Harness switch "B-91".
* HV-322604 at 72 % (`data.unit_322e003.HIC604_DES_PCT`, decision 99), switch `b18_switch`; PFD 734
  into 323E003 at 56 C (`lp_carbamate_condenser.step(m_734_kgh=)`, decision 100); PFD 314 and 319
  closed on their urea (`thermo.urea_liquor.close_urea_on_drain`, decision 101), switch `b20_switch`
  on the four unit-323 harnesses.
* The converter's ``DECIDED_ADDITIONS`` (decision 98): HS-321634 / 321603 / 321604 on 321-1,
  HS-322606 on 322-1, HS-323604 on 323-2, AI-329701 on 329-1; the packet's ``HAND_SWITCHES`` block;
  the keyswitch faceplate generalised. 393 elements, zero overlap.

A diagnostic cold start on (a): near 51 bar a at 3 000 s where session 49 reached 30.4.

**The second** (2026-10-14) asked for the suite cleared on the new baselines, the reported 597 C
reactor runaway fixed (a semi-implicit node balance or a boiling cap), the plateau broken and the
documents finished; it carried four data reports and the handwritten DCS readback of 13 October.
Built:

* 322R001's nodes at most at the liquor's bubble point (`units/synthesis/reactor_boil.py`, decision
  102): PI-322E002's Clausius-Clapeyron law anchored on the pinned 183 C top node under 141.3 bar a;
  the excess heat flashes the overflow's volatiles into the off-gas on their own enthalpies. The
  runaway is V1's (its own cold start reaches 420 C at 1 500 s). The ceiling alone left the loop near
  45 bar a: a filling reactor's residence sat on its floor and converted 1 000-1 400 kmol/h of urea.
  The kinetics' throughput is now the larger of the liquid out and the liquid in
  (`reactor_inventory.m_in_prev_kgh`). Harness switch "B-92".
* The plant DCS's readback (decision 103): LIC-323502 at 1.2 on SIC-323901's span (1.74 rpm per per
  cent) and 400 s; trip 22.1 at TT-322015's 110 C, cleared at 108; AI-329701's H1 / H2 at 15 / 18
  uS/cm in the packet's ``ANALYSERS``; 323P008's 5 % and 324F003's -0.9 bar g recorded.
* The rectifying column's B-20 cycle test on a V1-verbatim namespace (`v1_verbatim`): V1's rows cycle,
  the closed rows hold 135.000 C on V1's own loop.

**Measured, not met:** the Phase 7 cold start reaches 47.8 bar a at 1 000 s, 52.0 at 3 000 s and
then climbs about 2.2 bar per 1 000 s to 79.7 bar a at 16 000 s (fit tau 4 860 s, final 78.07 bar g;
V1 145.13; the band 137.5-150.5). In the diagnostic runs 322E003 condenses about 30 % of the
reactor's off-gas into a full sump; B-78's held inventory grows; 322F001's suction swings 0-66 t/h
and the ejector stalls near 47 bar a. B-91 stays open with options. The other re-runs: the HPCC
rupture holds 139.1 bar a, TT-322015 at most 56.1 C (no trip at 110 C); the vacuum break unchanged;
the steady state 2 858 of 3 188 leaves within 1 % (3 083); trip 22.2's scenario settles at
147.5 bar a, 22.2 never latched (V1 at 20 099 s). TT-322015 reads XV-322915's flood steam,
about 175 C, once trip 22.1 opens it, so the trip holds itself (B-95, as in session 49). The design seed is no
longer stationary (B-94): 734 adds 1.54 t/h to 308 with a 50-minute decaying oscillation, and the
reactor flashes about 35 kg/h at design. B-93 raised for 323P008's trip. The four reports disagree on
329D001's volume, PV-329212's sizing and trip 22.2; two were opened on their pages — Metso's sheets
(PV-329203 DN 250, Cv 4870; PV-329212 DN 80, Cv 150) and 329D001's GA (50 m3) — and logged, not
applied; the rest are leads.

`python -m pytest` — **7 334 collected**, six parallel parts: 7 332 passed, two failed on the first
run (a chained ``pytest.approx`` in the new B-92 test; a pre-evaporator pin 1.4e-4 K off), both
fixed and their files re-run green. pyflakes clean; the headless grep prints nothing. The six new
console elements rendered off screen on a live packet.

Next: B-91's remaining sink (322E003's own saturation, the start-up procedure, or acceptance); B-93;
B-94's re-seed; B-95; PV-329203 / 212 on their verified Metso trims (decision 23's class); the
other leads in Open data gaps (the other Metso butterflies, the solid carbamate correlation).

### Session 51 — B-94, B-91, B-93, B-95 and the Metso valves decided; 329D001 read

The process engineer's paste of 2026-10-14 decided the items session 50 raised. Built and measured
(As-Built Part LXVII):

* **B-94** (decision 104): PFD 734 enters 323E003 as its departure from the PFD's 1534 kg/h, which
  the PFD's 323E003 balance closes without — zero at design, the unit V1's on every tick. The steady
  state from the seed: 3080 of 3188 leaves within 1 % (session 50 2858, session 49 3083), 323P001 18
  kg/h under its design where it ran 1.54 t/h over. B-92 checked at the seed: its law returns the
  pinned 183.00 C at 140.7 bar a exactly, but V1's pinned node profile is not stationary on the live
  chain (the top node +6.05 uK on the first tick, 0.0224 K over its pin within the hour, uncapped), so
  the ceiling flashes 30-37 kg/h from the first tick; nothing changed — the residual is V1's pin's,
  and without the ceiling 322E003's new saturation would read the hotter liquor.
* **B-91** (decision 105): 322E003 on its own sump liquor's bubble pressure (the melt's law anchored on
  PFD 206, design head zero) and, at a full sump, condensing no more than drains from it. The decision's
  "0.30 floor" is the duty's flooded-surface derate, not a condensation limit. The retained gas behind
  HV-322604's seat was NOT added to PT-329201's node: the node already integrates it (boundary less
  liquid; the purge capped at the offer less the uncondensed gas), and adding it would count it twice.
  Option (b) checked: the HFC SOP and the 3 June 2025 trend preheat the loop, fill 322E003 first, hold
  HV-322605 shut to 20 % level and feed 70 % CO2; the scenario starts empty on the design lineup. V1's
  lumped node counts the fill's liquid as pressure (about 92 bar for the reactor's 137.4 t), the port's
  does not. On the Phase 7 cold start PT-329201 now reaches 137.9 bar a at 3 000 s
  (session 50: 52.0), peaks at 149.6 bar a at 3 630 s and settles at 136.9-143.1 bar a;
  fit tau 1 305 s, dead time 555 s, final 136.04 bar g against the band's 2 884-4 055 s
  and 137.5-150.5 bar g — faster than the plant and 1.5 bar under, so B-91 stays open.
* **B-93** (decision 106): searched — UD-AU-323-EC-0017 (the pump's datasheet, no instrument) and AC4
  PC23 sheets 13 and 14 (PDF pages 71-72): 323P008A / B's MOTCON interlock IC2 on "LT-323503:VALUE<L2".
  Built as drawn on the DCS's 5 %, live: a drained tank trips at 5 % and the flag relays (5810 stops in
  four hours on the flash lost) — B-96 raised.
* **B-95** (decision 107): closed as designed on PC22.5.1 and P&ID 102 — TI-322015 downstream of the
  injection, the keyswitch HS-322915 the release. No code change.
* **PV-329203 / PV-329212** (decision 108): Metso's Neldisc trims, the sheets' printed capacities as the
  curve, from 39.31 and 54.68 % (V1 linear from 73.80 and 65.56 %), the normal cases' xT. The headers 10 %
  down: 324E001's chest 3.6289 against V1's 3.4881 bar a, 324E003's 5.7619 against 5.6360.
* **329D001** (decision 109): 50 m3, ID 3.59 m, 4.95 m design level in `data/unit_329.py` (the paste named
  `unit_329_ccw.py`, which is 322E003's tempered water); no model reads it.

The Phase 7 scenarios re-run on this code (§LXVII.8): the cold start as above; trip 22.2 148.2 bar a after 48 000 s, still creeping about 0.02 bar per 1 000 s, 22.2 never latched (V1 at 20 099 s; session 50 147.5 bar a); 22.1 at 95.0 s on the flood steam, as designed; the HPCC rupture holds 139.0 bar a,
TT-322015 at most 56.4 C, no trip; the vacuum break, no trip (323F010 to 0.656 bar a and
back to 0.455); the steady state 3 080 of 3 188 leaves within 1 %.

`python -m pytest` — **7 343 collected**, six parallel parts: two failed on the first run (the
valve catalogue's count; a vacuum-condenser test pinned on the old chest valves), both fixed and
their files re-run green. pyflakes clean; the headless grep prints nothing.

Next: B-91's choice (the plant's procedure in the scenario, or acceptance); B-96; the other Metso
butterflies (Open data gaps).

### Session 52 — B-91 accepted; B-96 and B-79 closed; the Metso steam valves and LV-329505

The process engineer's paste of 2026-10-15 decided B-91 (accept), B-96, B-79 and the remaining
vendor sheets. Built and measured (As-Built Part LXVIII):

* **B-91** (decision 110): the cold start and trip 22.2 accepted; closed, no code change.
* **B-96** (decision 111): 323P008 trips below LT-323503's 5 % and restarts at 7 % (a 2 % stand-in,
  TT-322015's convention): 48 cycles in four hours on the flash lost against the live flag's 5810.
* **B-79 (b)** (decision 112): Egan, Potts and Potts admitted (Kp = (4/27) P^3, log10 P = 8.2697 -
  2741.9 / T); a gas the liquor leaves dry and above the solid's saturation lays solid carbamate in
  the letdown, the outlet and the deposit solved together on the enthalpy balance with Voskov and
  Voronin's solid. The lost-motive vent: 29.60 -> 51.01 C, 4.449 mmol per mole; on today's plant
  321P002B stopped for 300 s puts 1.02 kg through HV-322604's line, the outlet 24.1 C at 30 s where
  the dry answer is -8.7. HV-322604 carries the deposit on to 322C001; its alarm fires while it lays it.
* **The vendor trims** (decision 113): Metso's sheets 25-32 read from the scans — FV-329401, FV-329409
  (the tempered water, not catalogued), PV-329202, PV-329203, PV-329204, PV-329207A, PV-329207B,
  PV-329208. Six catalogued on their printed points; PV-329202 (32.92 %) and PV-329208 (27.22 %) wired
  into their chests (the LP header 10 % down: 323E002's chest 3.8940 against V1's 3.8084 bar a).
  LV-329505 on Flowserve's Pos. 71 — its normal capacity by IEC 60534-2-1 (32.366; the printed maximum
  reproduced to 0.05 %), its design stroke 62.19 %. FV-329401, PV-329204 and PV-329207A / B are
  catalogued and not wired: each moves a relation eight harnesses compare.

`python -m pytest` — **7 350 collected**, six parallel parts; the first run's failures were the
pins the decided trims moved (the valve count, the recirculation's unit tests, the synthesis loop's
decided tests through the 308 wash, the scheduler's liquor train on V1's valves), each re-pinned on
its measured value and its file re-run green. pyflakes clean; the headless grep prints nothing.

Next: FV-329401, PV-329204, PV-329207A / B on their trims; FV-329409's sheet; LT-329505's taps.

### Session 53 — B-30 and B-22 decided; every Metso valve on its trim; A-6 closed

The process engineer's paste of 2026-10-15 decided B-30, B-22, A-6, the four catalogued Metso steam
valves and FV-329409. Built and measured (As-Built Part LXIX):

* **B-30** (decision 114): 323E011 condenses on its dew point, T_dew = 45 + Tsat(P) - Tsat(1.13),
  C = 5589 (T_dew - 35) / 10, uncapped as 323E003's, and PV-323203's differential floored at zero.
  The node now has an equilibrium on both sides: 701 down 10 % holds 1.1024 bar a where V1's ran to
  its 0.1 bar a floor venting backwards; a shut vent stands at 1.1615 where V1's had no ceiling.
  The backward pressure step (decision 78's class) guards the stiff node; the harnesses run V1's.
* **B-22** (decision 115): 323F010 relaxes to its bubble point at the live PT-323204. HV-323605 at
  25 %: 101.5 C after a minute, its 104.2 C bubble point by 300 s, 7.65 t/h after two hours and
  never dry (V1: 99.06 C, 12 t/h, dry at 1132 s). Phase 7's vacuum break: PT-323204 to 0.599 bar a,
  TT-323010 to 103.1 C, the evaporation 12.0 to 7.56 t/h, the level held at 49 %; no oscillation, no
  trip.
* **The Metso valves** (decision 116): FV-329401 (FIC-329401's FlowLoop from 26.0 %, xT 0.53),
  PV-329204 (from 44.1 %), PV-329207A (its full stroke on its normal case, 165 773 kg/h) and PV-329207B
  (from 54.96 %) on `valve_gas_anchored`, PIC-329204's and the trio's leg B's biases on their design
  strokes; FV-329409 catalogued (the sheet prints no density: IAPWS's 961.89 kg/m3 at 95 C) and
  FIC-329409's steady flow on its trim from 46.85 %. Each both ways; V1's valves in every harness
  (``V1_FV_329401``, ``v1_butterflies()``, ``V1_FV_329409``).
* **A-6** (decision 117): the ten backgrounds frozen; closed.

`python -m pytest` — **7 363 collected**, thirteen parallel parts; the first run's failures were
the synthesis loop's decided tests, its tempered-water test and the tube leak's instructor test,
which the session's decisions reach through the plant (the A-12 fault case 0.13 bar lower on
PV-329204's Neldisc, measured with V1's butterflies at 139.6253), each re-pinned on its measured
value and its file re-run green. The Phase 7 steady state 3 086 of 3 188 within 1 %. pyflakes clean;
the headless grep prints nothing.

Next: LT-329505's taps; the sheets of PV-329207C, HV-329601 and HV-329602.

### Session 54 — B-31 decided; A-13 closed on its audit; eight items signed off

The process engineer's paste of 2026-10-16 closed session 53's tail, decided B-31 and A-13, and
signed off eight Section B and C items. Built and measured (As-Built Part LXX):

* **Session 53's tail** (§LXX.1): chunk 06 green on its pins. A-12's shift measured on `run_both`
  with each session 53 decision switched back: all on V1's returns session 52's pins (139.62505 /
  139.51511 bar a); the steam butterflies alone carry 0.1306 of the fault case's 0.1303 bar.
  FV-329409 is not in it — the harness runs it on V1's law.
* **B-31** (decision 118): 323E011's 701, 786, 321 and 791, 323E003's 305, 718B, 776 and 797,
  323C005's 756 and 702, 328D003's 343 and four condensates, and 328C002's 775, 748 and 750 at their
  producers' live temperatures, T_in = T_in,des + (T_prod - T_prod,des), this tick's where the
  producer steps first and the tick before's otherwise (eight new declared tears, four new state
  tears for unit 324's cold ends). Each unit's ``live_inlets`` (False is V1's) and
  `engine.plant.LIVE_INLET_UNITS`; each both ways. The utilities stay at design; 708, whose
  temperature no unit computes (324F002's discharge), stays at 121 C and is raised as B-97.
* **A-13** (decision 119): `tests/engine/test_check_valve_audit.py` — every module-level design
  differential under data and units a subtraction equal to its two pressures' float, the one
  check-valve call site on an audited name, the assembled flowsheet's first tick on the design
  flows ``==``; ``LV_322501_DP_DES_BAR``, the last literal, rewritten. Closed.
* **Signed off** (decision 120): B-2, B-17 (TT-322011 and TT-322002 already on HIC-322604's 72 %),
  B-45, B-52, B-48, B-72, B-74 and B-78. Section C is empty; the six loops' missing DCS rows are an
  open data gap.

`python -m pytest` — **7 372 collected**, thirteen parallel parts; the first run's ten failures
were tests handing B-31's producers off-design temperatures (323C005's warm solvent and A-20's
overflow, 323E011's overflow), the schedule's and the state's tear counts, and two synthesis-loop
pins B-31 reaches through 323E003's 308 (B-76's sumps 0.01 kg, A-12's CO2 case 0.0001 bar), each
fixed and its file re-run green. The Phase 7 steady state 3 086 of 3 188 within 1 %, no trip, no
ringing. pyflakes clean; the headless grep prints nothing.

Next: B-97; LT-329505's taps; the sheets of PV-329207C, HV-329601 and HV-329602.

### Session 55 — B-97 decided; UF85 dosing live; B-1, B-4 and B-12 signed off

The process engineer's paste of 2026-10-16 decided B-97 (option (b)), signed off B-1, B-4 and B-12,
asked for `handoff.md`'s closed Section A items to go and `flash_condenser.py` to come back under 600
lines, and asked for unit 335's UF85 dosing; asked how, the process engineer chose live dosing.
Built and measured (As-Built Part LXXI):

* **B-97** (decision 121): 708 at 324F002's discharge — 706 at 324E002's cold end and 924 at the LP
  header's saturated enthalpy mixed adiabatically at 323C005's 1.0 bar a, each species at its
  partial pressure, the water condensing below its dew point (`thermo/steam_gas_mixing.py`, new) —
  as its departure from the design mix, 125.62 C: 121 C to the bit at design, 112.92 on half the
  motive, 63.04 with HIC-329605 shut. `VacuumTrainResult.t_708_c`, a tear to 323C005 (78 declared),
  charged under ``live_inlets``; both ways.
* **UF85** (decision 123): `units/finishing/uf85_dosing.py` and `data/unit_335.py` (new), V1's
  ``step_uf85_cascade`` on `control.ratio` and the selector's UF85 terms in
  `second_evaporator.melt_route`; step "335" in V1's section 30. V1 calls both with the permissive
  forced; the port doses live, seeded at the PFD's ratio on the design drain, 617.07 kg/h (the PFD's
  694 kg/h is the granulator's 2 000 MTPD case; the operating manual gives 625). From V1's seeds
  ``==`` V1's functions on every tick, and ``==`` V1's forced call on its switch. The packet's UF85
  fields and faceplates publish: 274 of 274 bindings resolve. V1's slow ratio master is kept (no DCS
  row): a 20 % rate step leaves the dosing 1.6 % under its ratio after two minutes.
* **Signed off** (decision 122): B-1, B-4 and B-12; Section B is empty. The Henry constants and
  Körting's diagrams stay open data gaps.
* **Housekeeping**: A-3, A-4 and A-5 deleted (A-3's rule now `CLAUDE.md` §5 rule 4);
  `flash_condenser.py` 679 to 578 lines, 323E011's four gas-node relations verbatim in
  `units/recirc/flash_gas_node.py`, re-exported under their own names.

`python -m pytest` — **7 398 collected** (26 new), thirteen parallel parts, every part green on
its first run; the touched files' counts and pins (78 tears, 35 steps, the historian's 831 paths,
274 of 274 bindings, FIC-335405 on the model) fixed before it. The Phase 7 steady state 3 087 of
3 197 within 1 % (UF85's nine leaves now shared), no trip, no ringing. pyflakes clean; the headless
grep prints nothing.

Next: LT-329505's taps; the sheets of PV-329207C, HV-329601 and HV-329602; A-2 and A-8 when the
process engineer resumes the multi-station work.

### Session 56 — A-8 signed off; A-2 closed on the station token; the checklist complete

The process engineer's paste of 2026-10-16 signed off A-8's section-level assignment as the final
design (no per-tag locking), asked for A-2 to close on an optional station token with the
instructor's panel unpaused, and for the last three unticked checklist lines to be ticked. Built and
measured (As-Built Part LXXII):

* **A-8** (decision 124): unit assignment by plant section, as built in sessions 3, 41 and 42 —
  `data/tags.py` attributes each of the engine's 41 plant command types (the 38 an operator may
  send, each to the section of the instrument it moves; the three malfunction and CO2-rate types the
  instructor's, never narrowed); ``None`` unrestricted, ``[]`` nothing; instructors and the loopback
  superuser never narrowed.
* **A-2** (decision 125): `run.py --token` (or ``UREASIM_TOKEN``) gives the engine a shared station
  token and the console the same; `net/server.py` refuses a ``hello`` without it, or with another,
  before reading the role — the superuser included — in constant time (`hmac.compare_digest`), with
  the reason, and disconnects the station; with no token nothing changes, and the ``hello`` is the
  message it was. The token admits; among the admitted stations the role is still requested.
* **The console's refusal** (`hmi/bridge.py`): a refused console said it would not retry and did —
  the abort's ``disconnected`` scheduled a reconnect, so a wrong token was retried every few seconds
  and the refusal overwritten by "link lost". Measured on a real socket (three attempts in 1.5 s),
  fixed: one attempt, the refusal's reason left on the bar.
* **The instructor's panel unpaused**: an instructor station admitted on the token is sent the roster
  and its exercise list (measured through the bridge on a real socket).
* **The checklist**: `consequence/` and the two B-91 lines ticked; Phases 0-7 have none open.

`python -m pytest` — **7 414 collected** (16 new: the token's login on a real socket, the
``hello``, `run.py`'s token to both ends, the console's admission and refusal on a real
``QTcpSocket``), thirteen parallel parts, every part green on its first run. `run.py server` with
``UREASIM_TOKEN`` run live on the real engine: the instructor with the token welcomed, a wrong token
and none refused with their reasons and disconnected. pyflakes clean; the headless grep prints
nothing.

Next: the open data gaps, when the archive or the plant yields them.

### Session 57 — 323P003's protection, trip 21.2's hand switches and TRIP_84_8 read; decision 95 signed off

The process engineer's paste of 2026-10-16 asked for three data-gap rows to be settled and for the
documents' stale counts to be brought up to date. Read from the scans and measured (As-Built Part
LXXIII):

* **323P003** (the 323D002 row): no low-level trip exists to wire. AC4's MOTCONs PC23.1.7 / 1.8 carry
  no interlock (IC2 constant 1, only the field switch on IC1), where 323P008's carry LT-323503 < L2;
  the functional diagram UD-MR-323-FF-0002 and 323D002's level loops (L 323504, L 323507: AH / AL)
  draw no trip. Uhde's specification UD-AU-323-EC-0016: NPSH required 3.8 m at the rated 97 + 35
  m3/h, available 5 m (preliminary); KSB's curve 3.2-3.4 m over the operating range. The port's
  suction cap (B-26) stays, no trip; the row keeps the seal pot's onward drain only.
* **Trip 21.2's hand switches** (AC4 PC21's row): the loop summaries type HS-321634, HS-322606 and
  HS-323604 as control-room keyswitches, HS-321603 and HS-321604 as emergency shut-off switches,
  control-room and local. All five stay maintained, as built; the two switches' console notes
  corrected through the converter.
* **TRIP_84_8_FLAG1**: the Safeguard SG1's PC15.1.5 (UD-MR-G00-FF-0006 page 51), the instrument air's
  low pressure — two of PT-384207A / B / C below L2, latched until RS_TR_84_8 — sent to AC2, AC3 and
  AC4. The instrument air is not simulated; the flag stays healthy. The row keeps the DCS database
  limits only.
* **Decision 95 signed off** (decision 126): the reactor liquor's buffering, 2 159.6 kg/bar at design
  (71.6 vapour, 2 088.0 buffering), is the V1.1 baseline; the 322E002 / 322E001 liquor row deleted.
* **Housekeeping**: register rows 12-20 point at the rows that ported them; `stripper.py` 600 lines,
  comments only; §3's diagram, element counts, roles and scheduler status brought up to date. Six
  modules still sit between 601 and 693 lines, under the 800-line split.

`python -m pytest` — **7 414 collected**, none new (no physics or logic changed: comments, two
console notes, documents), thirteen parallel parts, every part green on its first run; the
touched files' 337 tests first. pyflakes clean; the headless grep prints nothing.

**Continued — the archive searched for the open data gaps** (`/soft-copy-search`, As-Built
§LXXIII.7-9):

* **328D003's overflow**: N12, DN200, compartment III, 4552 mm above the bottom plate, EL +5352 (the
  site file's nozzle record and drawings, UDS-BM-328-QC-0001), through seal pot Z2801Z to drain
  system 30 and pit 329F001; 488.6 m3 to its centre, the approved 490 within 0.3 %. Row closed.
* **323D002's overflow**: seal pot Z2301Z to the underground drain and 335D004, the recycle tank
  (P&ID 116). Row closed. Neither receiver is simulated; both stay published overflow streams.
* **Trip 22.2**: XV-322902's command traced — AC4 PC21.5.1's flip-flop, reset by 21.2 or trip 20.1,
  ANDed in SG1 with 320K002's machine trip; no synthesis pressure trip in either. V1's 22.2 stays.
* **Trip 21.2 shuts XV-322902 and XV-322903** (decision 127): PC21.5.1 resets their flip-flops too,
  which A-12 had not built. Asked and decided, built: both shut while the flag is lost, their opens
  refused; with the CO2 left on, SV32064 relieved 59 t/h, so decision 83's class takes 320K002's
  demand to zero and refuses a demand while the flag is lost. Measured: the loop blocked in at
  141.7 bar a after ten minutes, nothing relieved.
* **LT-329505**: the upper tap, N5 on 324E001 at EL +15129; the lower tap is off the vessel.
* Not found: the other butterflies' and LV-324501's sizing sheets, the DCS database values.
* **Decided after the search** (the process engineer's paste of 2026-10-16): decision 127 confirmed
  as built, the demand cut included; the 19 open data gaps accepted as the final V1.1 ledger
  (decision 128).

`python -m pytest` — **7 415 collected** (1 new: trip 21.2 holding XV-322902 and XV-322903
shut and refusing the CO2 demand; the AC4 trips test, the tear count and the harness's
A-12 branch updated), thirteen parallel parts, every part green on its first run. pyflakes
clean; the headless grep prints nothing.

**The Windows launcher** (`launch.bat`, at the user's request): finds Python, checks 3.11 and the
packages of `requirements.txt`, starts `run.py` from its own folder with any arguments passed
through, and waits on a failure. Measured: `launch.bat --help` exits 0; started offscreen from
another folder, the engine listened on its port and the console connected.

Next: the open data gaps, when the archive or the plant yields them.

### Session 58 — the console revised from its slides; the research PDF worked through

The process engineer asked for four console changes and for the open data gaps to be closed from a
research report (`D:/Work/Urea Simulation Docs/Data/Urea Simulation Missing Data Research.pdf`).
Built and measured (As-Built Part LXXIV):

* **Hover** (decision 129): a hovered page button painted opaque black over its label — the theme's
  CSS ``rgba()`` tokens are invalid to ``QColor``. `theme.rgba` converts them; the button now tints.
* **Valve icons**: the 47 modulating valves' bowties, drawn over the slide's labels beside the drawn
  valves, are readouts of the opening in per cent (`DECIDED_RETYPES`); `ActuatedValveWidget` deleted.
* **The slides**: exported through PowerPoint (`tools/export_slides.ps1`) and compared with the
  backgrounds; V1's migration had stripped 51 destination blocks from seven pages, so their page
  buttons stood on nothing. `tools/restore_nav_blocks.py` restored them from the slides. HS-322915 is
  the slide's square, green, red while turned; the 322-1 CO2-compressor widget the slide asks for is
  not built (decision 73).
* **Overlaps**: at design with a digit to spare, 14 readouts moved by 1-24 px off the drawing's
  symbols and blocks and off their neighbours (`NUDGE`); a test now holds it.
* **Data** (decision 130): the liquid-rated SV32353 / SV32357 / SV32253 on Sempell's printed gas
  coefficient for their orifices, 0.922 (0.917 assumed), the gap closed. Metso's sheets for HV-323605,
  PV-323203, TV-328002 and PV-323202A / B (= TV-323013A / B) found and catalogued, not wired.
  LT-329505's upper tap traced to its transmitter. The report's other claims checked: its trip 22.2
  reading is not what SG1 draws; its ABB defaults and its 324F002 nozzle are not plant data.

`python -m pytest` — **7 419 collected** (4 new: no valve icon, no readout over the drawing or
another at design, every page button's block drawn, a hovered hotspot tinted), thirteen parallel
parts, every part green on its first run. Updated: the geometry floors (247 indicators, no
``avalve``), the vendor-valve count (42), the gas coefficient's tests (0.922; SV32357's shut-vent
cycle 25.1-25.3 s and 36.6 kg), two faceplate tests' sample element types. pyflakes clean; the
headless grep prints nothing.

Next: whether to wire the five Metso valves (HV-323605 at 64.2 %, PV-323203 at 21.6 % at design).

### Session 59 — three Metso valves wired; the process-deviation scenarios put to the plant

The process engineer decided session 58's question (decision 131) and asked for the scenarios in
`D:/Work/Urea Simulation/References/scenarios` to be covered with the right response. Built and
measured (As-Built Part LXXV):

* **The valves** (decision 131): HV-323605 on its Neldisc from 64.08 % on xT 0.38 (the 64.2 % quoted
  was PFD 790's printed 12 040 kg/h; the valve passes V1's 12 013), PV-323203 from 21.64 %,
  TV-328002 from 55.04 % on PFD 1028's 408 t/h; HIC-323605, PIC-323203 and TIC-328002 seeded there;
  V1's laws on each harness's switch, ``==`` V1 tick by tick, and one both-ways test each. A pinched
  or opened valve in the unit tests restated as the same fraction of its design capacity. The
  Neldisc chokes HV-323605 below 0.298 bar a in 324E002; PV-323203 is large for its duty, 1.85 times
  V1's gain at design. PV-323202A / B stay catalogued.
* **The scenarios**: the four notes are generic Stamicarbon material (one an analysis of V1's own
  files), not plant data. `tests/phase7/deviations.py` puts every section on Helwan's plant on the
  console's own levers — 78 deviations, 191 claimed responses, each read off the packet against an
  unperturbed control run (`run_deviations.py`, 45 minutes on 16 workers). 147 come out as claimed;
  of the 44 that do not, 7 are a controller in AUTO holding what the note describes open-loop, 3 a
  lever with no authority (PIC-324203), 8 a mechanism the model does not carry, 3 below the display,
  12 the note against the model's physics (Scenarios2 and Scenarios4 contradict each other on the HP
  ejector), and 11 four defects, raised: **A-21** a wide-open HV-322605 collapses the loop and trips
  it in 37 s where V1 holds 140.7 bar a (B-77's and B-91's decided lines together); **A-22** a full
  323F004 has no ceiling; **B-98** the explicit species step at a heel (found restating HV-323605's
  tests); **B-99** 322E003's condensation does not answer its tempered water.

`python -m pytest` — **7 507 collected** (88 new: 82 in `tests/phase7/test_deviations.py`, three vendor-trim tests and three both-ways tests for the valves), thirteen parallel parts, every part green on its first run. Re-pinned to the vendor trims: 27 unit tests of 323F010, 323E011 / 323D011, the gas node and 328D001 (restated where they held a valve at V1's stroke), the equivalence harnesses put on V1's laws through their switches, and three synthesis-loop tests whose V1 side shares the port's steam network (1-3e-4 bar). pyflakes clean; the headless grep prints nothing.

Next: A-21, A-22, B-98 and B-99 — the process engineer's decisions.

### Session 60 — A-22 and B-98 built; A-21 traced and B-99 measured

The process engineer decided session 59's four items and the evaporators' crystallisation. Built and
measured (As-Built Part LXXVI):

* **A-22 (a), decision 132:** above LI-323505's 100 % (8458 kg) a full 323F004's excess overflows at
  its composition and temperature into 323E011's shell the same tick, liquid not gas load, as a full
  328D001's; ``FlashTank(ceiling=False)`` on the harnesses. The deviation S1-2.1 now 3 of 3 (149 of
  session 59's 191). Building it found **B-100**: V1's 323F004 holdup (180 s, 5075 kg) is ten times
  the drum's 518 kg of operating fluid and above its 3.45 m3 flooded volume.
* **B-98 (b), decision 133:** `liquor_stage.advance_species` takes the drained composition at the
  step's end where the drain passes more than the stage holds, V1's explicit step to the bit
  elsewhere and on the harness switches (``backward=False``; ``backward_species`` on 324F003 and
  323D002, whose both-ways tests reach a heel). 323F010's heel keeps a liquor (72.96 % urea where
  V1 reads 0.000 %), but the vapour draw stays explicit and rings tick to tick at the heel, 74.53 /
  75.88 % against the throughflow's 80.07 % — session 59's "74.5 %" was an even-tick sample;
  raised as **B-101**, the vapour draw backward too measured settling at 79.8-80.0 %.
* **A-21 (b), traced:** B-91's saturation fraction, read a tick late on a melt whose bubble pressure
  moves with its own condensation, rings with a period of two ticks and from 4 s locks 322E002's
  condensation off; B-77 turns the 410 t/h of gas into pressure, the CO2 line cannot follow, the
  reactor's N/C rises and V1's slip lifts the stripper's overhead to 78-88 % with 108-129 MW asked of
  its 39.4 MW shell. The fraction solved on the tick (prototype): no trip, PT-329201 at most 143.3
  bar a, 142.0 at 15 minutes.
* **B-99 (b), measured:** colder or more water moves only the temperatures — at design nothing is
  left to condense; warmer or less water already cuts the condensation as built (90 C: NH3 in the
  purge 91 -> 1335 kg/h, +0.07 bar). The capacity on the shell's own effectiveness (p1) changes the
  flow side only (250 m3/h: 703 kg/h uncondensed where V1's linear term leaves 3370); no case
  oscillates.
* **Decision 134:** no crystallisation restriction on 324F001 / 324F003, as V1.

`python -m pytest` — **7 515 collected** (8 new: two 323F004 overflow tests, one in 323E011, the full drum both ways, the 323F010 heel both ways and the heel step both ways at three stages), thirteen parallel parts. The first run parted three both-ways tests at a heel (324F003's drain above its heel and its feed loss with the drain wide open, 323D002's compartment I run dry) a tick before their decided divergences; with ``backward_species=False`` on their harnesses every part is green, and `tests/docs` green again after the documents. No unit test re-pinned. pyflakes clean; the headless grep prints nothing.

Next: A-21's and B-99's final decisions; B-100 and B-101.

### Session 61 — A-21, B-99, B-100 and B-101 built and closed

The process engineer decided the four open items (decisions 135-138). Built and measured (As-Built
Part LXXVII):

* **A-21 (b), decision 135:** `condenser_holdup.CondenserHoldup` solves 322E002's saturation
  fraction with the bubble pressure of the melt it lets condense, on the tick, wherever the tick-
  before fraction would move (`core.numeric.bracketed_root`, Illinois). A wide-open HV-322605 no
  longer trips the loop: PT-329201 peaks at 143.3 bar a and holds 142.0 at 15 minutes, the CO2 feed
  never below 51.6 t/h. Option (c), the stripper's overhead bounded by its shell, not built: the
  stripper still asks for up to 77.9 MW in the first two minutes. The seed's own drift dips the
  tear's fraction to 0.99998 in its first ticks; solved, it stays at 1.
* **B-99 (b1), decision 136:** 322E003's condensation capacity on its shell's conductance eps . C at
  the live circulation (UA-limited, NTU 0.19: half the water still 0.912 of the capacity, V1's 0.5),
  its published duty and TT-329125 capped at it where it binds.
* **B-101 (b), decision 137:** the heel's backward species step takes the vapour draw too, where the
  drain and the vapour pass more than the stage holds: 323F010's heel at 79.77 / 80.03 % urea on
  alternate ticks (the throughflow's 80.07 %), where the drain alone rang 74.53 / 75.88 %. What
  still alternates is the vapour's composition, evaluated on the liquor at the start of the tick.
* **B-100 (b), decision 138:** the archive read — Reuther's as-built drawing and parts list (two DIN
  28013 heads Da 1400 x 8), the datasheet (LT-323505 on N7, the top head; the high liquid level
  80 mm above the bottom tangent) and loop summary L 323505 (a DP cell, its taps 2900 mm apart) —
  showed session 60's residence estimate rested on the right numbers for V1's 60 % set point:
  measured on the drum's geometry, LIC-323505 does not ring (a 25 % feed cut: -5.2 %, inside 0.5 %
  in 318 s, V1's drum -4.5 % and 540 s), so it is built: 1837 kg at the 60 % set point, 65 s of
  PFD 319, full at 3761.5 kg on 3.402 m3, an empty drum reading 17.8 %. 323E011's 1.083 m3 of
  323F004 vapour space (B-51) is left as decided. `core.vessel_geometry` is new.
* **Scenarios re-run** (S1-1.2, S2-3.1a, S2-1.4a / b, S1-2.1): 7 of their 18 claims as claimed
  (6 in session 59); the survey at 148 of 191. A wide-open HV-322605 now runs: the reactor drains
  43.5 points, PT-329201 ends 1.5 bar up, and the conversion ends 11.4 points above the control's
  (session 59's "falls" agreed only through the trip) — measured, not explained, recorded.

`python -m pytest` — **7 535 collected** (20 new: 14 in `tests/core/test_vessel_geometry.py`, 3 in `tests/core/test_numeric.py`, the A-21, B-99 and B-100 both-ways tests), thirteen parallel parts. Twelve parts green on their first run; the thirteenth parted on two synthesis pins whose V1 side shares the port's plant — B-76's sump, 3650.52 / 3766.49 -> 3650.65 / 3766.57 kg, and A-21's tear side, 227 109.3 -> 227 106.6 kg/h — moved by the geometric 323F004 through 323E003's 308; re-pinned, `test_synthesis_loop_decided_equivalence.py` green. `tests/docs` green after the documents. pyflakes clean; the headless grep prints nothing.

Next: the open data gaps (the final V1.1 ledger); Sections A, B and C are empty.

### Session 62 — S1-1.2's conversion traced; A-21's option (c) measured

Scratch traces and a scratch prototype only; no source file changed (As-Built Part LXXVIII).

* **The conversion (S1-1.2, HIC-322605 60 -> 100 %).** Every tick recorded against a control, and
  the reactor's extent recomputed with one input at a time taken from the control. While
  HV-322605 drains the reactor (372 t/h for 146 s) the throughput the residence runs on rises to
  374 m3/h and the conversion falls to 0.39-0.46, as Scenarios.md claims. The level then sits on
  the funnel lip, 19.35 m, the outflow the production's, and the residence costs 1.2 points. From
  about 4 minutes the conversion rises on the loop's chemistry: the reactor feed's H/C blend
  (to 0.52) trips the stripper's H/C penalty (V1's volatile breakthrough, slip to 0.18), the
  drained ammonia stays in the loop (feed N/C to 4.46), 322E002's melt bubbles above the loop
  (fraction to 0.69), up to 113 t/h of gas reach the reactor and its carbamate heat lifts nodes 1-3
  to the bubble point — the nodes worth 9.4 points at 30 minutes, the N/C 4.9. Run to an hour it
  is a slow oscillation of about 50 minutes, undamped over the hour: +11.4 points at 30 minutes
  (session 61's reading, its crest), -5.0 at 47. Trip 22.1's vent flood is set from 40 s in
  session 61's runs too; "no trip" there meant the synthesis trips.
* **Option (c) prototyped.** Q_max = Q_des . LMTD(live) / LMTD_des on 329D005's saturation,
  TT-322013 and TT-322004, the desorbed NH3, CO2 and H2O scaled to meet it. 322E001's datasheet
  (UD-AU-322-EC-0003 p. 4) leaves U and the corrected MTD blank and the archive's 322E001 file is
  mechanical only, so the bound is anchored on the design duty (UA 1 160.5 kW/K calculated from the
  datasheet's terminal temperatures, logged as a data gap). On S1-1.2: the duty held at 29.5-39.7
  MW (lambda 0.36 at 60 s) where 78 MW was asked; the drained volatiles to 323C003 in the bottoms
  (up to 304 t/h, 30 % NH3); 322E002 at least 0.97 saturated; PT-329201 at most 141.2 bar a; no vent
  flood; the slow excursion a third of the as-built one. The claims agree as before (S1-1.2 1 of 5,
  S2-3.1a 2 of 2), every departure smaller. Costs: the seed's own drift binds it (lambda 0.9999);
  LT-322501 full for 32 s.
* **Raised.** B-102 (the duty bound, options for the process engineer) and B-103 (LT-322501's clamp
  deletes a full sump's excess, V1's — S2-2.3b on the as-built plant holds 100 % from 140 s, about
  100 t/h; decision 62's class, to build).

No source changed: the suite, pyflakes and the headless grep are as session 61 left them;
`tests/docs` re-run after the documents, green.

Next: B-102's decision; B-103 built on decision 62's class.

### Session 63 — B-102 and B-103 built; Scenarios5.md put to the plant

The process engineer decided B-102 (b) and asked for B-103 on decision 62's class; both built, each on
a harness switch with both-ways tests (As-Built Part LXXIX).

* **B-102, decision 139.** 322E001's split bounded by its shell: Q_max = Q_des . LMTD / LMTD_des,
  past Q_max . (1 + 5e-4) the lift of NH3, CO2 and H2O beyond the sweep scaled by lambda (bisection)
  until the per-species enthalpy balance meets it, the rest left in the bottoms
  (`units/synthesis/stripper_shell`, new; `stripper_322e001(shell_bound=)`;
  `StripperSump.shell_bound`). Two measurements went back to the process engineer first: a 1e-4
  band, as asked, still binds on the seed's drift (1.68e-4 within the hour), so the band is 5e-4 and
  the duty clamps continuously at its edge; and the LMTD on the live TT-322013 / TT-322004 binds at
  every turndown (80 % load kept 42 % of its lift, V1's bottoms temperature rising on both sides of
  the design), so the LMTD is the live steam's against the tube side's design 187 / 172 C. The
  unperturbed seed: lambda 1.0 for an hour (the ratio at most 1.000184). HV-322605 to 100 % on the
  loop harness: V1 asks 1.584 design duties on the tick after, the port pays 1.0005, lambda 0.635.
* **B-103.** LT-322501's full sump holds its excess in the tubes (``held_kg``), run down first as the
  sump drains, its gain booked as liquid; V1's clamp on the switch. S2-2.3b on the loop harness: 2.2 t
  held 80 s after the sump fills, and V1's loop 1 bar higher — PT-329201's balance counted the liquor
  V1 deleted as gas.
* **Scenarios5.md.** `tests/phase7/coupled.py` (13 cases on the console's levers, Case 10 with no
  lever), `run_coupled.py` (both waves, against a control, 45 minutes each), `test_coupled.py`;
  `run_deviations.run_plant` samples result indicators beside the packet. **74 of 152 claims as
  claimed**: the loop's first wave mostly as the note says, its delayed LP wave (the LPCC's pressure,
  level and 308 surging back) once in 21, Helwan's hand-valved reactor draining to its lip where the
  note's holds its level. The four mechanisms asked about, measured: the LPCC's water composition into
  322E003 — needed (B-105); low N/C's azeotropic rise — in the thermo, reaching the loop only as
  322E002's ceiling, not reached at N/C 2.93 (B-106, measure at 2.6 first); the stripper flooded into
  its tubes — needed, B-103's held liquor reaching 64.6 t with no ceiling while the reactor drains
  into it (B-104); 324F003's lost seal admitting air — needed (B-107, S1-5.4b re-run: PT-324203 flat).
  Switched off (V1's split and clamp), the first twelve cases read 69 of 139 against the built
  65 — eight claims move, two into agreement — and the trips move more: on V1's clamp S5-5a
  latches every loop trip at 1 375 s, on V1's split S5-5b and S5-9 flood 322C001's vent (22.1);
  built, none of the three, and S5-7 gains a 22.1 at 2 295 s.

`python -m pytest` — **7 584 collected**, thirteen parallel parts: twelve green; the HMI part fails one
test, `test_main_window.py::test_the_trend_window_opens_once_and_takes_trendable_tags`, on the
committed tree as well — it reads the console's saved trend view from the user's `QSettings` (A-23).
`tests/phase7/test_coupled.py` re-run green with S5-6b; `tests/docs` green after the documents.
pyflakes clean; the headless grep prints nothing.

Next: B-104 to B-107 (the process engineer's decisions); A-23 at the next code session.

### Sessions 64 and 65 — B-104 to B-107 decided and built; A-23 closed; Scenarios5.md re-run

The process engineer decided the four mechanisms session 63 measured and asked for A-23 (session 64's
paste); session 65 completed the work after a context break. One question went back first: the
paste's "flooded limit" for TT-322004 named no temperature, and the process engineer chose the
crystallisation floor, 132.7 C. Each mechanism is on a harness switch with both-ways tests (As-Built
Part LXXX).

* **A-23.** `tests/hmi/conftest.py` gives every console test an INI file of its own for
  `main_window`'s ``QSettings``; the trend-window test passes.
* **B-104, decision 140.** The held liquor capped at the tubes standing full, 8 688.7 kg; holding any,
  the tubes take the drain and (1 - sigma) of the design bottoms, HV-322605's discharge capped at it
  and 322R001 keeping the rest, what still arrives past the ceiling handed back to its holdup; the
  shell's capacity times 1 - 0.70 sigma and the bottoms to 132.7 + f_sub (T - 132.7). Two caps were
  measured and rejected first: the room over the bottoms' live transit starved itself (the reactor
  stopped discharging with the tubes 78 % full) and counting the transit's contents failed on its
  dead time, which does not conserve them. Both ways on S5-5a's lever: from 218.1 s the take caps
  HV-322605; ten minutes on the reactor discharges 26.3 t/h against V1's 226.2 and stands at 85.94 %.
* **B-105, decision 141.** 323D001 carries NH3, CO2, H2O and urea as its departure from PFD 308 (each
  inlet at its PFD row, the condensate at the gas's closure on PFD 308) and 322E003 washes with 308's
  live composition and temperature. FV-323401 wide open: 308 to 33.45 % water in four minutes, the
  reactor feed's H/C 0.4142 against V1's 0.4014. The seed's own LP drift reaches 308 at 1e-6.
* **B-106, decision 142.** The melt's N/C factor below 3.0 on the Extended UNIQUAC rise; the paste's
  diagnosis confirmed — the saturation fraction reads the K_N line, not the thermo, correcting session
  63's handoff text. CO2 +20 % on a held pump: the loop reaches trip 22.2 at 161.6 s where V1's stands
  at 141.5 bar a.
* **B-107, decision 143.** The lost seal's air on LV-324501A's blow-through law (`units/evaporation/
  leg_seal`). S1-5.4b: PT-324203 to 0.242 bar a, the melt to 96.71 %. At the 1 kg heel the stage's
  fixed point no longer converges (B-108).
* **Structure.** `stripper.py` 573 lines and `stripper_sump.py` 526, `stripper_kinetics` and
  `stripper_level` split out unchanged; `leg_seal` new.
* **Scenarios5.md re-run** (S5-W on FV-323401 in MAN at 100 %, S5-6c at CO2 +20 %): **83 of 165**; the
  thirteen of session 63 74 of 152 again with sixteen claims moving — S5-W 6 -> 10 on B-105; S5-5a,
  S5-6a, S5-6b and S5-6c reach trip 22.2 on B-106's rise, S5-5a's through the stripper the tubes'
  cap starves. Eight deviations re-run: 16 of 22, S1-5.4b's vacuum now breaking.

Raised: B-108 (stage 2's fixed point at its heel), B-109 (PT on 322R001 reading the melt's bubble
pressure), B-110 (308's line transit), B-111 (B-106's fast trips).

`python -m pytest` — **7 627 collected** (7 584 at session 63), thirteen parallel parts, all green:
the HMI part on A-23's fixture; the two synthesis-harness parts re-run after the transcription's
condenser was put on V1's line (`test_synthesis_loop_equivalence._hpcc_port(low_nc=False)` — it had
picked up B-106's default and parted from the port at tick 6); three engine enumerations extended
(81 declared tears, ``TEAR_NAMES`` with ``w_308`` and ``t_308_c``, ``LV_324501_DP_DES_BAR`` in
A-13's audit). `tests/docs` green; pyflakes clean; the headless grep prints nothing.

`CLAUDE.md` §3 gains the user's rule: always use the claude-mem skill (its search was offline this
session — the Chroma store unreachable — and returned nothing).

Next: B-108 to B-111 (the process engineer's decisions; B-110's data search first).

### Session 66 — B-108 to B-111 decided and built; Scenarios5.md re-run

The process engineer decided the four items sessions 64 and 65 raised (a pasted root-cause note and
directive). The note's numbers were measured first and two differ from the code (As-Built Part
LXXXI):

* The Extended UNIQUAC melt bubbles at 44.37 bar a at N/C 3.0, not 49.4, so the ratio amplified the
  rise 3.25 times, not 2.92.
* B-109's min(P_bub, PT-329201) would have moved the design reading 3.5 bar. The cap is placed at
  the saturation fraction's threshold instead.

* **B-108, decision 144.** Where stage 2's G7 sweeps do not settle, the temperature is solved on the
  stage's energy balance by bracketed false position (`units/evaporation/stage_fixed_point`).
  * At the 1 kg heel under a broken vacuum TT-324002 holds 147 to 143 C where V1's last sweep
    wandered between 43 and 146 C.
  * LV-324501's selector moved to `units/evaporation/melt_route` (`second_evaporator.py` 552 lines).
* **B-109, decision 145.** PT on 322R001 on min(P_bub, PT-329201 + 3.5 bar) plus V1's line drop.
  * A melt at 216 bar a on a loop at 151 reads 170.2 where V1's read 231.7.
  * The rest is V1's line law, raised as B-112.
* **B-110, decision 146.** PFD 308's line found in the vendor archive. 323006 (UD-RL-100-MB-0017) and
  323004 (MB-0015) give 47.8 m of 88.9 x 7.1 high-pressure pipe, 0.2095 m3, 24.94 s at design.
  * 322E003 owns the line (`ScrubberSump.wash_line`).
  * With FV-323401 wide open, TT-322002 is 163.61 C on the line against 163.43 on B-105's tear after
    four minutes.
* **B-111, decision 147.** The azeotropic rise added in bar: +9.38 at N/C 2.8, +38.04 at 2.6.
  * CO2 +20 % on a held pump still trips 22.2, at 192.7 s (161.6 on the ratio): the melt reaches
    N/C 2.40 in ten seconds.
* **Scenarios5.md re-run**, 14 cases: **82 of 165** (83).
  * S5-W 10 -> 9: the loop pressure's late rebound shrank inside its tolerance with 308's line.
  * The four tripping cases trip 30 to 95 s later and no other verdict moves: S5-6c 195 s, S5-6b 445,
    S5-5a 575, S5-6a 1 330.
  * Eight deviations re-run: 15 of 22 (16). S1-1.2's loop now ends 0.6 bar up where it ended 11,
    and its bottoms' ammonia claim, gained on the ratio, is lost.

Raised: B-112 (PT on 322R001 on V1's feed-line law: 136.1 bar a at the design against the PFD's
141.3, moving 2.31 bar per bar of PT-329201).

`python -m pytest` — **7 636 collected** (7 627 at session 65; nine new), thirteen parallel parts, all green on their first run, the re-pinned B-106 loop test with them; `tests/docs` green; pyflakes clean; the headless grep prints nothing.

Next: B-112 (the process engineer's decision).

### Session 67 — B-112 decided and built; handoff Sections A, B and C empty

The process engineer confirmed session 66's B-108 to B-111 as built and decided B-112 (a) (a pasted
root-cause note and directive). The note's numbers were measured first and hold: V1's line factor is
2.308 at the design seed (the mass reference 1.754, the density reference 1.316), 136.12 bar a, and
3.31 bar per bar of PT-329201 under B-109's cap (As-Built Part LXXXII).

* **The data search.** 322R001 carries no pressure transmitter: P&ID 102 draws TI-322005 to 009,
  LI-322504 and SV-32251 / 32252 on it; loop summary UD-MR-322-EC-0001 lists no pressure loop on it.
* **B-112, decision 148.** PT on 322R001 on min(P_bub, PT-329201 + 3.5) less the feed line's PFD drop,
  144.2 - 141.3 = 2.9 bar (`unit_322_loop.REACT_FEED_DP_DES_BAR`, in A-13's audit), at the seed's feed
  density (752.2 kg/m3) and mass (250 639 kg/h).
  * The plant's first tick reads 141.3 bar a to the bit; under B-109's cap one bar per bar of
    PT-329201 (151.6 on a loop at 151, where V1's line read 170.2).
  * Display only: S5-6b re-run with its control, every other series identical to session 66's, trip
    22.2 at 445 s, 7 of 13. The control reads 141.30 on a loop at 140.70; S5-6b peaks at 155.42 on
    154.82 (session 66: 183.79 on 154.64).
* **Found, not done** (As-Built §LXXXII.3): about two-thirds of the 2.9 bar is the reactor's own
  liquid column, which the law scales with the flow; after a trip the reading is the cooling melt's
  bubble pressure, 95.6 bar a under a 155 bar a loop, as on V1's line. Both notes signed off as built
  by the process engineer (2026-10-22): the reading reaches no screen and no unit; no B-113.

`python -m pytest` — **7 638 collected** (7 636 at session 66; two new), thirteen parallel parts, all green on their first run; `tests/docs` green; pyflakes clean; the headless grep prints nothing.

`handoff.md`'s Sections A, B and C are empty; the open data gaps are the only open items.

### Session 68 — the single-console conversion (decision 149)

The process engineer signed off As-Built §LXXXII.3's two display-only notes as built (no B-113) and
asked for sessions 62 to 67 to be committed (`15e66c2`), then decided to convert the simulator to a
single console (a pasted directive, confirmed in chat). Built as directed (As-Built Part LXXXIII):

* **Launch.** `run.py` keeps the combined launch alone: the engine on `127.0.0.1` and its console,
  `--port`, `--station` and `--verbose`; the `server` and `station` modes, `--host`, `--role`,
  `--token` and ``UREASIM_TOKEN`` are gone, from `launch.bat` and `README.md` too.
* **Transport.** `net/protocol.py` loses ``Role``, ``INSTRUCTOR_ONLY_COMMANDS``,
  ``is_authorised``, the ``roster`` and ``assignment`` kinds and the token; ``hello`` names the
  console, ``welcome`` the engine, and the version is 2, so an older console is refused, not
  misread. `net/server.py` binds `127.0.0.1`, refuses a ``hello`` from any other address (no login
  stands in front of the plant), checks no role, token or section, and passes every command to the
  engine; back-pressure, the catch-up on ``hello``, the audit echo, history and the exercise list
  are unchanged. `data/tags.py` and its test are deleted: unit assignment was its only consumer.
* **Console.** `hmi/bridge.py` takes no role or token and emits no role, assignment or roster;
  the 5 s watchdog, the blanking on a lost link and the no-retry refusal stay. `main_window.py`
  drops the role badge and the assignment readout and always shows the Instructor menu. The
  instructor's panel drops the roster and unit assignment and gains a **Boundary** group: the CO2
  demand on 320K002 (``co2_set``), 0 to V1's 120 % of the design feed
  (`data/faceplates.CO2_DEMAND_MAX_FRAC`, V1's ``co2_compressor.js``), with the packet's
  ``CO2_FEED.raw_th`` beside it — no console control sent it before.
* **Tests.** `tests/net/test_server_login.py`, `test_server_superuser.py` and
  `tests/data/test_tags.py` deleted; `test_protocol.py`, `test_server.py`, `test_engine_host.py`,
  `tests/hmi/test_bridge.py`, `test_main_window.py`, `instructor/test_panel.py` and
  `tests/test_run.py` rewritten for the single console; `test_co2_compressor.py` now pins that only
  the instructor's panel sends ``co2_set``.
* **Smoke run.** The engine and the console started offscreen through `run.py`'s own functions:
  welcomed, ``ENGINE RUNNING — SLOW``, the panel's CO2 demand set to 60.08 t/h and FREEZE both
  acknowledged, the audit line fed, the packet's demand 60.08.

`python -m pytest` — **7 454 collected** (7 638 at session 67: 184 fewer, the role, token, roster and assignment tests removed with their mechanisms and the single-console tests added), thirteen parallel parts, all green on their first run, and the suites touched after it began re-run green; `tests/docs` green; pyflakes clean; the headless grep prints nothing.

`handoff.md`'s Sections A, B and C stay empty; the open data gaps are the only open items.

### Session 69 — the data gaps searched again; seven valves on their vendor sheets

The process engineer asked for every open data gap to be searched again in `D:/Work/Urea
Simulation` and `D:/Work/Urea Simulation Docs` with their subfolders, then in the vendor archive
(`/soft-copy-search`), and confirmed the two changes that followed (decisions 150 and 151). A pasted
review of session 68 came with the request; it raised nothing to act on. As-Built Part LXXXIV:

* **The search.** 486 documents in the two folders were text-extracted and searched (`References/`
  included), the 73 DCS faceplate photographs and the June 2025 trend photographs read. The
  folders hold no file newer than 2026-10-16 but `References/scenarios/Scenarios5.md`; the AI reports in `Urea Simulation Docs/Data` were
  checked against the archive's pages (memory `external-archive-reports`). What closed the gaps was
  in the archive: **Fisher's control-valve file, UD-MR-G00-DZ-0014** (Emerson, never read: TV-323013
  — the 323D001 vent the port calls PV-323202 — LV-328503, LV-328504 and HV-329602), and pages of
  **Flowserve's summary of items** earlier sessions had not reached (Pos. 65 HV 329601, Pos. 76
  PV 329207C, Pos. 148-149 LV 324501A / B), whose calculation sheets are the same PDF pages of -003.
  **PFD 28** (cooling water) gives 322E006's water, streams 1010 / 1011, where the handoff had found
  no stream.
* **The valves (decision 150).** Catalogued in `data/control_valves.py` (the Flowserve four) and
  the new `data/control_valves_fisher.py`, and wired on decision 23's class, each on its sheet's
  named curve: LV-328503 equal percentage from 56.95 % (V1 linear 50 %), LV-328504 from 57.80 %
  (50 %), PV-323202 linear from 36.45 % (25 %), FL 0.819 on the two letdowns; HV-329601,
  PV-329207C and HV-329602 on their full-stroke capacities on their normal cases (V1's law on the
  loop summaries' maximum cases at full stroke); LV-324501A from 75.35 % (V1's span law 75 %) and
  LV-324501B on its full stroke, both on the sheets' Kv taken to the melt's 1221 kg/m3 — the sheets
  size on SG 0.751 — and the lost-seal air (decision 143) on A's trim. Each equivalence harness
  switches the valve (`valve`, `lv504`, `vent`, `vendor_globes`, `vendor_drain`) and each valve
  runs both ways.
* **322E006 (decision 151).** The plates run on PFD 28's 14 t/h; the UA is back-solved so the
  PFD's 744 still leaves at 40 C, 20.448 kW/K against the datasheet's 30.776, kept as margin.
* **What moved.** The design point nowhere; off design, every test that quotes a transient through
  these valves was re-measured and its docstring restated (the first desorber, the hydrolyser, the
  LPCC, the steam network's trip 21.2 and LP header, stage 2's drain and leg, the vacuum train).
  Three scenarios were restated where a held stroke meant "at design" or "80 % of design" on V1's
  linear trim (PV-323202 held at its design stroke, LV-328504 at the stroke passing 80 %). The
  synthesis-loop harness runs the whole plant, so its decided tests moved in the fourth digit,
  but one: in B-104's scenario the reactor's discharge at ten minutes went from 26.3 to 37.7 t/h,
  traced by reverting each change in turn to PV-323202's anchor alone (323D001 1.5 mbar apart;
  LV-322501's drain at 10 % is that scenario's most sensitive quantity).
* **Not closed.** The other 15 rows: no Körting or 322F001 curve, no 322E001 thermal rating, no
  Neldisc curve (Uhde's specification names "equal percentage", no table), no DCS database values
  for the hystereses, AC4's limits or the eight untuned loops, no LT-324501 / LT-329505 tap
  elevations, no AI-329701 configuration, no 324F003 trend, and no trip 22.2 in any logic file.

`python -m pytest` — **7 475 collected** (7 454 at session 68: 21 more — the new sheets' catalogue, the Fisher module's own test and each valve's both-ways tests), thirteen parallel parts. The first run failed 33 tests, every one a measured value or a held stroke the new valves and water move (the desorbers' unit tests 15, the synthesis loop's decided harness 14, the vacuum condenser's trip, a faceplate's displayed 75.3 % and the catalogue's two); each was re-measured, its docstring restated, B-104's large move traced, and those files re-run green; `tests/docs` green; pyflakes clean; the headless grep prints nothing.

`handoff.md`'s Sections A, B and C stay empty; 15 open data gaps remain.

### Session 70 — the housekeeping split: every module inside 600 lines

The process engineer asked first for session 69's LV-324501A / B density correction to be checked
before its commit: the trims' mass capacity scales as sqrt(rho) on m = Kv sqrt(rho dP) (B's full
stroke 251.5 t/h against 197.3 t/h at the sheets' SG 0.751, a ratio of 1.275), not inverted;
`CLAUDE.md` §5.7 and decision 150 were reworded, and session 69 was committed (`2e4d64c`). Then a
pasted directive asked for every module under `ureasim/` at or below the 600-line target with no
change to the physics (decision 152, As-Built Part LXXXV):

* **The audit.** Six modules above 600: `data/unit_323.py` 772, `units/synthesis/scrubber.py` 703,
  `engine/command.py` 650, `data/unit_324.py` 644, `thermo/condensing_letdown.py` 625,
  `data/control_valves.py` 616.
* **The splits.** `control_valves` 391: the sizing records to `valve_sizing` (107), Metso's
  fourteen Neldiscs to `control_valves_metso` (218). `unit_323` 561: stage 1 into the column's tag
  module `unit_323c003` (308, its relief kept), stage 4 to `unit_323d002` (116). `unit_324` 478:
  the condensers' ratings, the vapour rows and the ejectors' vendor ratings into `unit_324_train`
  (310). `scrubber` 549: the shell to `scrubber_shell` (156), the sump level and LT-329501 to
  `scrubber_level` (94). `engine/command` 506: the payload helpers to `command_payload` (69), unit
  329's handlers to `command_steam` (121). `condensing_letdown` 576: solid carbamate's saturation
  to `thermo/carbamate_solid` (92). The largest module is now `units/recirc/flash_condenser.py`, 600.
* **How.** Lines cut by script on asserted ranges and checked line for line against the
  originals; every moved public name re-exported by the module it left (`scrubber` gained an
  ``__all__``); each new module imports nothing from the one it left; no test patches a moved name.
  The first cut of stage 1 was written over the tracked `unit_323c003.py`; it was restored from
  git before any test ran and the stage merged into it. The node stores' keys hash none of the
  touched modules, so they were not rebuilt.
* **Tests.** One file per new module and one for `unit_324_train`: `tests/data/test_valve_sizing.py`,
  `test_control_valves_metso.py`, `test_unit_323c003.py`, `test_unit_323d002.py`,
  `test_unit_324_train.py`; `tests/units/synthesis/test_scrubber_shell.py`, `test_scrubber_level.py`;
  `tests/engine/test_command_payload.py`, `test_command_steam.py`; `tests/thermo/test_carbamate_solid.py`.

`python -m pytest` — **7 536 collected** (7 475 at session 69: 61 more, the ten new test files), fourteen parallel parts, all green, none skipped. The first run set Qt's offscreen platform, under which Qt lists no font families on this machine, so the two overlap tests of `tests/hmi/test_screen_geometry.py` skipped on their own font guard; the commit message (`2cfa3f2`) called them font skips, but no font is missing: Consolas and Courier New are installed in `C:\Windows\Fonts`, and Qt's native platform also lists Cascadia Mono. Re-run on the native platform, the geometry file passes 17 of 17 and `tests/hmi` 75 of 75; `tests/docs` green; pyflakes clean over `ureasim`, `tests`, `tools` and `run.py`; the headless grep prints nothing.

`handoff.md`'s Sections A, B and C stay empty; 15 open data gaps remain.

### Session 71 — an external report on five data-gap rows; two closed

The process engineer pasted an audit of five open data-gap rows (the urea-melt Henry constants,
322F001's geometry and curves, 322C001's bottom head volume, Körting's ejector curves, the Neldisc
characteristic above the last printed travel) and attached the report behind it. Each of its
numbers was re-measured from the code and each document it cites looked for by name (As-Built Part
LXXXVI):

* **Verified.** The melt refit (-85.3 K; gamma_H2O 0.79 / 0.70 on the PFD against the literature
  parameters' 0.52 / 0.48; the one-row fits -71.66 / -98.92 K); 322F001's back-solve (16.721 mm,
  50.228 mm, b 0.11082, shutoff 5.1058 bar, stall 0.90697); the vacuum train (PV-324202 61.07 %,
  PV-324203 92.03 %, HV-329605 69.06 %, HV-329606 80.16 %, 324F004's and 324F005's throats);
  322C001's head (0.10292 m3 at s 14.0 mm, 0.10266 at 14.4; 0.1298 Di^3 1.2 % under; the C(s/Da)
  correlation 0.10292 / 0.10267). Two attributions corrected: 132.7 C is
  `unit_322e001.T_CRYSTALLISATION_C`, not decision 140; the head volume is computed in
  `data/unit_322c001.py`, which `core/vessel_geometry.py` reuses.
* **Not verified.** The Neldisc deviations: the report evaluated the chord in the bulletin's own
  normalised space, as if each sheet's last point lay on the bulletin's curve; the sheets print up
  to 30 % less (FV-329401 0.228 of rated at 52.9 % against 0.326). On the sheets' own points the
  chord departs from the rescaled bulletin by +13.4 % (PV-323203 at 60 %) to -4.7 % (HV-323605 at
  90 %), not +8.4 % to -3.14 %; every design stroke lies below its last printed travel. The
  bulletins (2SL120EN, 2LW22EN, 2LBF20EN) are in no archive. The report's statement that no
  pure-melt Henry constant can exist is uncited. Its ejector table swaps two vendor duties
  (324F002's is Körting's 94 kg/h at 0.20 bar a, 324F005's Uhde's 84 at 0.33) and gives two break
  pressures the model does not have: at the design suction and motive, `ejector_map`'s critical
  back pressures are 1.305 bar a (324F002), 0.369 (324F004, not 1.34) and 1.105 (324F005, not
  2.39).
* **Decided** (decision 153): 322C001's head volume closed; the Henry constant closed as a
  quantity no source holds; the Neldisc row annotated and kept linear. The 322F001 and Körting
  rows unchanged.

No code changed; `tests/docs` green. `handoff.md`'s Sections A, B and C stay empty; 13 open data
gaps remain.

### Session 72 — the replacement stripper, the plugged tubes, the gap photographs, Scenarios6

Five tasks from the process engineer (As-Built Part LXXXVII):

* **322E001 replaced** (decision 154). The vendor archive's `New Stripper` folder read in full:
  Resta's job 6355 for Stamicarbon (Z524-H1269, built 2025) — 2,950 tubes 31 x 2.5 mm minimum wall,
  6,000 mm tubesheet to tubesheet, 1,724 m2, 28.83 m3 tube side, a 2,425 mm bottom channel, no level
  taps (the radar nozzle N17 blinded); Stamicarbon's process data sheet A4-101124, 41,738 kW, no
  coefficient or corrected MTD (data gap kept). `data/unit_322e001_bundle.py` carries both bundles;
  the units take the bundle the plant runs, the harnesses V1's. The design seed does not move.
* **Plugged tubes** (decision 155). 322E002 2,929 tubes (60 plugged), 322E003 525 (16), 323E010
  1,087 (15), each from its Uhde design data sheet (scans, read from the page images); the
  conductances derated by the share in service, the plugged bores out of the loop's volume. The
  derated plant leaves the PFD seed (322E002's saturation 0.93 after 30 minutes): B-113 raised.
* **The gap photographs** (decision 156). 26 photographs of 22-24 October 2026: AI-329701's range
  0-30 uS/cm (its data-gap row closed); TIC-323012, FIC-328404, PIC-329205 (a PI on its split),
  LIC-329502 and TIC-328012 on their faceplates; TIC-328008 and FFIC-335406 raised as B-116; the
  vacuum bleeds' trend (B-115); LT-323503's and TT-322015's limits confirmed, no hysteresis shown.
* **`Scenarios6.docx`** put to the plant (`tests/phase7/seal_loss.py`, `run_seal_loss.py`): four
  cases, 45 of 71 claims as claimed; LV-322501 failing open blows through 31.5 t/h and does not lift
  323C003's safety valves, sized on 60 t/h each (B-114).
* **The audit**: pyflakes clean on `ureasim`, `tests`, `tools` and `run.py`; every module at or below
  600 lines; nothing below `hmi` imports PyQt6; the check-valve audit and the native-platform screen
  geometry green; the full suite green. One defect found and fixed: the stream inspector rounded a
  tie to even where V1's ``toFixed`` rounds it up (PFD 709's 3 342.5 kg/h read 3342, not 3343).
  The synthesis harness now keeps every LP-side change of the session on its switches; the
  design-seed tests run on the clean bundles. The dynamic audits were not run.

### Sessions 73 and 74 — B-113 to B-117 closed, and the dynamic audits

The process engineer's decisions on session 72's four items, the dynamic audits of the Phase 7
checklist, and the close-out (As-Built Part LXXXVIII):

* **B-113 (b)** (decision 157). The plugged tubes' conductances re-anchored on the bundle in
  service, so the PFD's design point holds by construction: session 72's derate removed with the
  units' `plugged` fields and `build_plant(plugged=)`; the tube counts, the active surfaces and the
  plugged bores out of the loop's vessels kept. The plant's first tick is the PFD to the bit
  (322E002 170.0 C and saturated, 322E003 at its whole demand, 323E010's chest 2.5 bar a).
* **B-114** (decision 158), measured and signed off as built. V1 and the port already scale
  LV-322501's blow-through by the stroke over its design stroke, and SV32351 / SV32352 already pop
  at 6.010 bar a; read every tick, LV-322501 forced wide open lifts them at 91.0 s, 12.6 s lifted,
  51.4 t/h at the peak — the survey's 5 s samples had missed every lift, and now read the peak
  between samples. The 31.5 t/h ceiling is the sump's level standing in its seal band.
* **B-115 (a)** (decision 159). The 8-10 October trend is the plant at 112.5 % load; the bleeds stay
  on the 1750 MTPD design basis; the data-gap row closed.
* **B-116** (decision 160). TIC-328008 on its faceplate's 1.00 and 60 s, carried from wt% onto the
  model's mol% by 737's local slope (84.59 kg/h of reflux per mol%); FFIC-335406 a ratio station on
  its faceplate's limits, the PFD's ratio its seed; V1's tunings on the harnesses; the tuning row
  narrowed to FIC-335405.
* **The dynamic audits** (`tests/engine/test_dynamic_audit.py`, 14 tests, green): the holdups close
  on their flows to rounding through a multi-unit disturbance; every trip initiator's path; the
  updated controllers' anti-windup and transfers; a FAST shutdown with LV-322501 wide open, no node
  ringing and every evaporator stage solved; a freeze-snapshot-reload-resume bit-exact; a seeded fuzz
  of simultaneous malfunctions. One finding, **B-117**: TIC-328008, as every cascade master V1's
  `_ctrl_ipd` builds, integrates while its slave is out of cascade (FIC-328404 steps 1.5297 to
  0.8381 m3/h on re-entry after five minutes in AUTO) — signed off as built (decision 120's class).
* **`Scenarios6.docx`** re-run: 47 of 71 (45). S6-2 gained three — PI-322E002 rising over 15-45
  minutes, the reactor feed's N/C, TT-324001 climbing — and lost 323F004's early surge; S6-1 gained
  323D011 draining and lost the top gas falling: the re-anchored plant no longer drifts from its seed
  under the control run.
* **Session 74**: the four documents; the full suite and pyflakes; the temporary resume files
  deleted; Sessions 72 to 74 committed.

### Sessions 75 and 76 — the load range 70-115 %: an operating study; B-118 to B-120 raised

Session 75 (2026-10-29, interrupted) studied the first request — the handles' optimum set points from
70 to 115 % on three bases (the plugged tubes derating, as committed, the pre-turnaround bundle) — in
scratch; its last 21 staged runs died unfinished with the session and nothing was logged. Session 76
(2026-10-29 and 30) answered the request that superseded it: `D:\Work\Urea_Plant_Load_Optimization_
70_to_115.xlsx`, two sheets — the maximum per-pass conversion in 322R001 and the minimum battery-limit
steam per tonne of urea — at 70-115 % in 5 % steps, each point to be held one hour on the committed
engine (the last turnaround's 322E001 and plugged tubes). No relation, constant or test changed
(As-Built Part LXXXIX):

* **Method.** A scratch runner drove the headless engine at 0.1 s through the command handlers —
  operator trims on the levels, TT-322004 and TT-322005, then a one-hour hold judged on every published
  level, relief, overflow, suction, seal, mushy flow, stall, deposition, trip and flag — about 70 runs,
  candidates branched from exercise snapshots. The licensor's windows were read from Operating Manual
  Part III (UD-VT-G00-DC-0003 sections 2.6 and 5.2) and the plant's own practice from
  `References/DCS Trends/Book2.xlsx` (2023: 755 samples at 90-95 % load, 4 131 at 110-112 %).
* **100 %.** The design point holds (X 54.18 %, 901 60.86 t/h, 835 kg/t against the PFD's 834.5); TT-322004
  176 C, seven hours after the step, holds X 55.94 % at 850 kg/t — the conversion optimum; every cut of
  TT-322004 to 170 C or below starts B-120's oscillation, so the design point is the steam optimum.
* **105 %.** Near-steady, not passed: TT-322004 170 C with HIC-323605 holding 323F010 at 61 % gives X 52.92 %, 901 60.53 t/h, 813 kg/t — the best on both objectives (172 C: X 52.56 %, 834 kg/t; 175 C: X 51.71 %, 868 kg/t) — and meets every criterion over its hold, seven hours after the step, except 328D003's open-loop ammonia-water bays rising 0.75 %/h; FIC-328402 trimmed on them overloads 328C004 (+13 %/h). AT-322701 2.87-2.91, at the licensor's lower edge; 322E003 vents 125-141 kg/h.
* **110-115 %.** No verified steady state: 323F010's barometric leg cannot pass the flow and the
  separator fills (137 % at 110 %, 259 % at 115 %, HIC-323605 at its floor) — B-119; the holds'
  values are reported as failing.
* **70-95 %.** No steady state under seven policies and the plant's own 92 % set points: trip 22.1 at
  70-85 % within 20-80 minutes or a collapse of the reactor, and a cold branch at 90-95 % (TT-322005
  168-178 C, X 36-48 %, 323F010 drained) — B-118. The engine cannot reproduce the plant's 2023 turndown
  (TT-322005 182.6 C at 92 %).
* Off-design ticks cost about 110 ms against 15 ms at design (323C003 / 323F004 bubble points,
  HV-322604's letdown), which bounded the study.
* **B-118, B-119 and B-120** raised for the process engineer, Book2's bands as their acceptance data.

### Session 77 — the load range retried on an attached control schedule, HIC-322605 by hand; B-121 raised

Session 77 (2026-10-30) answered the process engineer's request to retry session 76's workbook after
reading a control document. The document was "Coordinated Setpoint Scheduling and Dynamic
Stabilization of the Stamicarbon HPCC Urea Synthesis Loop Across the 80% to 100% Load Envelope", a
Word file with no document number. During the runs the process engineer added that HIC-322605 is a
hand station. Its purpose is a stable 322R001 level, but it is not wired to the level: the operator
moves it according to the solution 322R001 discharges. `D:\Work\Urea_Plant_Load_Optimization_70_to_
115.xlsx` was rebuilt; session 76's version is kept in the session's scratchpad. No relation,
constant or test changed (As-Built Part XC):

* **The document's schedule.** Its laws were run on the live load and extrapolated outside 80-100 %:
  HIC-322604's equal-percentage inverse; PIC-329204 at -0.06 bar per % of load, never below its shell
  LMTD floor; MASTER-329207 +0.015 bar and TIC-329005 +0.225 K per % cut; 322F001's entrainment in
  proportion to load; an NH3 lead of +1.5 % while the load rises. One anchor is wrong. HV-322605's
  design opening is 60 % in the engine; the document's 50 % is HIC-323605's V1 design. The workbook
  gives each law at each load beside the engine's value.
* **HIC-322605 by hand.** An operator re-types it every 2 to 5 minutes. Each move sizes the valve to
  the reactor's discharge plus its holdup's trend, adds a 30-minute correction toward LT-322504 80 %,
  and inverts the sum through the Kv table. With the funnel flooded the level integrates; settled at
  100 % and 105 % it held its hour with at most one move of 0.03 %.
* **100 %.** The document's schedule is the design point: X 54.20 %, 835.1 kg of steam per tonne,
  PASS, the steam optimum. Session 76's TT-322004 176 C, re-held by hand, gives X 55.94 % and
  850.3 kg/t, PASS, the conversion optimum.
* **105 %.** R105s (session 76's point by hand) gives X 52.92 % and 813.3 kg/t and fails only on
  328D003 (+0.75 %/h). Raising FIC-328402 to 34.5 m3/h holds 328D003 (+0.24 %/h), but 328C003's level
  falls while LIC-328504 recovers (corrected in session 78). This is raised as B-121.
* **Turndown.** On the document's schedule:
  - trip 22.1 at 53-55 minutes at 70-80 %;
  - trip 22.2 at 80 minutes at 85 %;
  - the cold branch at 90 % and a slide at 95 %;
  - an operator on the ratio, toward AT-322701 3.02, reached the 2.0 floor and vented more;
  - a 0.1 %/min ramp slid from 98 %.

  With the fresh ratio fixed, AT-322701 rises to 3.3, TT-322011 to 147 C on its correlation, and
  322E003 vents 1.6-2.4 t/h. Meanwhile the reactor's discharge and 308's wash stay at design. The
  plant holds AY-322701 3.25 with TT-322011 at 130-134 C in every band (Book2). B-118 is updated.
* **Above design.** The document's NH3 lead swung AT-322701 between 2.5 and 3.9, 322E003 vented up
  to 8 t/h, and 323F010 overfilled at 105-115 % (B-119, updated).
* **Plant practice.** Book2's band medians were added to the workbook. The plant follows the
  document's directions: HVGT-322605 at 0.50 times the load, and HIC-322604 at the document's slope.
* **Checks.** No file under `ureasim/`, `tests/` or `tools/` changed; the PyQt6 grep prints nothing.
  The workbook recalculates in Excel with 232 formulas and no error.

### Session 78 — a pasted analysis of B-118 to B-121 checked and measured; 105 % verified; B-119 built

Session 78 (2026-10-30) took up another tool's analysis of session 77's open items, pasted by the
process engineer, with a diagnosis and a recommended change for each. Every claim it makes about the
code was checked in the source and against session 77's records. Each change was measured as a
scratch patch on the committed engine (`patched_run.py` in the session's scratchpad; As-Built Part
XCI). One relation changed, B-119's, on the process engineer's decision (decision 161):

* **B-118.** The analysis's two mechanisms are not the engine's. 322E003's vent split takes its
  K-values at the design temperature, so TT-322011's correlation sets only the reading and
  HV-322604's purge. 322E002 does not over-quench at turndown: TT-322010 stays at 167.9-171.5 C and
  its melt holds less gas, not more. At 90 %, TT-322011's slope cut to the plant's 133 C at 3.25
  changes nothing else, and 322E002's conductance scaled on its flow delays the slide by 20 minutes.
  With V1's conversion-deficit slip switched off the reactor still slides, to X 44 % at 90 % and
  31 % at 80 %. The loop N/C's excursion on the ramp precedes every slide.
* **B-119.** The drain-out below design is confirmed: 323F010 is empty at 80-90 % with HIC-323605
  wide open. The analysis's level-proportional head is option (b) with an assumed rangeability; it
  was not measured.
* **B-120.** With HIC-322605 by hand the 1 h mode keeps its period at about a quarter of session 76's
  swing. The stripper's slip gain sets its size: X swings 4.8 points at V1's 4, 1.6 at 2 and 0.4 at
  0. No gain gives a steady hold; at 0, 323F010 drains 16 %/h.
* **B-121.** The analysis's +4.5 % on FIC-328402 and FIC-329402 leaves the bays at +0.54 %/h. R105f
  (FIC-328402 at 34.5 m3/h), continued so that its hold starts 3.5 h after the step, passes every
  criterion: X 53.24 %, 812 kg of steam per tonne. The workbook's 105 % column now reports it on both
  sheets; it recalculates in Excel with 232 formulas and no error.
* **Corrections.** FIC-328402 reads m3/h, so session 77's 31.4 and 34.5 "t/h" are m3/h (31.1 and
  34.2 t/h). R105f's 328C003 level fell 1.5 % while LIC-328504 recovered: the analysis script printed
  the drift's magnitude, and session 77 read it as a rise. The script now prints signs. As-Built XC.3
  and XC.5, B-121, session 77's entry and the workbook's notes are corrected.
* **Decisions.** The process engineer kept B-121 open for (b). The other three answers did not
  arrive, and the session took the recommended courses, which change nothing: B-118 and B-120 open,
  B-119's leg searched before anything is built. Shown the leg and the prototype, the process
  engineer decided B-119 (b).
* **B-119, continued.** The leg is isometric UD-RL-100-MB-0142 (line 323256): 323F010/N2 at
  EL +15 740 to 323D002/N1 at EL +6 095, N1 carrying a dip pipe (UD-AU-323-TL-0001). The 9.645 m
  drop exceeds the 8.98 m that a full vacuum holds of PFD 317's 1 151 kg/m3 melt, so the separator
  drains on its own head and its pressure has no say. Option (b) was prototyped as
  m_317 = m_317,des . sqrt(M / M_des): the design point is unchanged, and 323F010 settles at its
  throughput level from 90 to 115 % (71.9 % at 110 %, where V1's law reaches 201 %). The 110 % hold
  then fails on 324E001's level and HV-322604's deposition flag, and the 115 % run trips on a loop
  excursion (As-Built §XCI.6).
* **B-119 built** (decision 161, As-Built §XCI.7). `units/recirc/barometric_leg.py` carries the
  drain on the separator's own head and V1's leg, moved there verbatim and re-exported by
  `pre_evaporator` (569 lines); `PreEvaporator.own_head_leg` selects it, False on every
  equivalence harness. The leg's elevations, the tank's reference and design liquid level, and the
  premise's 1.013 m margin are data with their sources. The equivalence test asserts both sides;
  the stage's twelve V1-leg scenarios run on V1's leg and four new ones pin the decided drain.
  The synthesis harness takes V1's leg too, as it keeps the LP side's other changes: the LP header
  carries 323E010's chest to the loop, and five of its decided tests moved without it. The dynamic
  audit's fast shutdown reverses PT-323204's step three times running once, where V1's leg reaches
  its limit of two eleven times: the boil-off's spikes (B-24), raised as B-122, the audit's one
  exception. The workbook's 105 % point re-held on the built engine (Y121F2, from a copy of R105f's snapshot given the new field) passes as before, X 53.24 % and 812 kg/t, with 323F010 at 67.4 % where HIC-323605's trim had held 60 %; the workbook notes both.
* **Checks.** The full suite ran 7 597 tests: 7 591 passed and six failed, the dynamic audit's fast shutdown on PT-323204 and five synthesis-loop decided tests on the LP header. After the synthesis harness took V1's leg and the audit its 323F010 exception (B-122), those six pass, as do the four other harness files (193 tests) and the rest of the decided file (22). The PyQt6 grep prints nothing. Snapshots saved before the build carry the old
  field set and are refused, as after every change of a unit's fields.

### Session 79 — B-122 built; B-121 and B-118 traced against Book2's bands

Session 79 (2026-10-30) worked through the four open Section B items on a pasted plan from the
process engineer: B-122 option (b) to build, B-121 option (b) and B-118 / B-120's narrowed option (b)
to measure and report before any relation changes (As-Built Part XCII). Resumed on 2026-10-31 after a
pause, it kept the synthesis loop's harness on the linearised step and closed B-123 on the process
engineer's sign-off.

* **B-122 traced and built** (decision 162, As-Built §XCII.1-2). In the dynamic audit's fast shutdown
  323F010's liquor holds 1 to 12 mK above its bubble point. Two things break the pressure step's
  linearisation. The boil-off is zero above the pressure that brings the liquor to its bubble point
  and falls about 9 t/h per mbar below it, so a start subcooled by 0.5 mK — the memo's bubble point
  stepping 0.006 to 0.026 C where the liquor's CO2 crosses a bin edge — leaves the Jacobian with the
  valve alone, and the step overshoots into a flash its pressure never saw. And the boil-off's root
  can sit on a bin edge, where it stops answering the pressure. The fix solves the backward step
  itself on every tick the holdup boils, with `core.node.backward_euler_pressure`; elsewhere the
  linearised step is kept to the bit. On the audit the largest tick-to-tick change of 323F010's
  vapour falls from 20.6 to 0.46 t/h on the decided leg (18.1 to 1.0 on V1's), no boil-off spikes
  remain, and PT-323204 never reverses more than twice running; the audit's limit of two is restored
  for every node and B-122 is closed. Three other fixes were measured and set aside: one memo bin
  frozen per tick (it chattered a quiet boil at 492-855 kg/h), the rigorous bubble point expanded
  about the tick's state (smoothest, but up to 0.035 C off the memo V1's relaxation uses, so a
  liquor at 97 C boiled 5.3 kg/h it should not), and the exact step only where the boil starts or
  stops (the pinned root escapes it).
* **B-121 traced** (As-Built §XCII.3). Book2 measures 322P002's delivery (FT-322402) flat at 30.9 in
  every band, as the engine holds PFD 744, and FIC-328402 rising about in proportion to load, 37.0,
  40.2, 42.0 and 44.0 m3/h at 92, 102, 108.6 and 111 %. The engine's extra ammonia water at 105 % does
  not start in unit 328: 323E003's vent 321 grows from 1.32 to 3.4 t/h (its gas +8 %, its capacity
  +1 % at PIC-323202's 3.2 bar a), 323F004's flash 701 from 4.43 to 5.6-5.9 t/h, and 323E011, whose
  capacity is set by its pressure alone, vents the excess as 702 — 3.5 to 3.9 t/h, 3.0 of it NH3 —
  which 323C005 scrubs into 343 (+2.9 to 3.4 t/h). PV-323202 and PV-323203 run 88-94 % open, where
  the plant's PIC-323202B and PIC-323203 outputs stay at 24-28 % and 32-40 % in every band. With
  PIC-323202 at the loop summary's 3.9 bar a (an operating set point, no relation changed), 323E003
  condenses its whole gas at 3.38 bar a, both vents close, 343 falls to 33.9 t/h and the tank's net
  gain at FIC-328402's design falls from 4.75 to 0.55 t/h. No unit 328 relation was changed.
* **B-118 traced** (As-Built §XCII.4). On the 90 % ramp the NH3 partition and the conversion slip
  move the overflow's N/C by less than 0.01: AT-322701 follows the reactor's real feed, 322E002's
  melt and gas, whose atom N/C rises from 3.11 to 3.47 in 16 minutes. The 3.073-3.088 recorded in
  session 77 is the reactor's blended N/C driver, a lag of the fresh-feed ratio, which sets its
  kinetics and never sees the loop's composition. The engine's 3.00 is the PFD's design overflow;
  the plant holds AY-322701 at 3.25 in every band. At Book2's 92 % set points 322E003's vent is its saturation fraction on its own liquor (decision 105):
f falls to 0.93 within 30 s (1.5 t/h) and to 0.76 at 22 minutes (7.8 t/h) as AT-322701 climbs past
3.9; its shell's capacity never binds for more than 0.5 t/h.
* **B-120** was not measured this session.
* **The synthesis loop's harness kept on the linearised step** (As-Built §XCII.2). The whole-plant
  harness boils 323F010's holdup in its fast decided transients — B-104's on 3 782 of 6 001 ticks,
  B-106's on 1 139 of 2 001 — and B-122's step reached six of its decided tests and V1's side of
  A-12's CO2 case through the LP header, on knife edges at length. The LPCC 1.3 mbar apart at ten
  minutes moved B-104's reactor discharge from 37.7 to 26.3 t/h through LV-322501's 10 % drain
  (decision 150). On the harness's V1 switches the LP header rings period-two in B-106's transient
  (36 successive reversals; the product's plant never reverses twice running), so 0.2 mbar at 33 s
  grew to 42 mbar at 100 s and trip 22.2 moved from 190.7 to 193.0 s. As it keeps V1's leg (decision
  161), the harness keeps the linearised step, ``PreEvaporator(exact_boil_step=False)``; every pin
  stands as committed, and the stage's section 7 asserts both sides of the switch.
* **B-123 raised and signed off** (decision 163). V1's thermo memo answers 323F010's bubble point and
  vapour on bin expansions that step at the edges: in a quiet boil PT-323204 chatters ±0.012 mbar,
  and the stage alone under a 2.75-fold feed surge rings period-two at ±0.22 mbar on the vapour's
  CO2, before and after B-122. The process engineer signed it off as built on 2026-10-31, option
  (a): the chatter lies below the transmitter's resolution, and V1's memo stays.
* **Checks.** The full suite collects 7 599 tests, the two of the stage's section 7 new. Run as eight
  parallel groups beside the decided synthesis file, all 7 599 pass: 7 577 in the groups in 15
  minutes' wall time, and the decided file's 22 on the harness's linearised step, every pin as
  committed. The PyQt6 grep prints nothing. Snapshots saved before the build carry
  ``PreEvaporator``'s old field set and are refused, as after every change of a unit's fields.

### Session 80 — the load schedule of every controller; B-121 closed

Session 80 (2026-10-31 to 2026-11-04) worked through three pasted plans from the process engineer:
B-121's option (a) and B-118 / B-120 measured; a load-scheduled control of the whole plant —
every controller and hand station inventoried, given a relation to the load and run from 70 to
115 % on the conversion and the steam objectives; and, on resuming after a shutdown (2026-11-02),
the sweep finished, 100, 105 and 110 % re-held with four further measures, B-121 closed and the
load-optimisation workbook rebuilt (As-Built Part XCIII). Nothing under `ureasim/` changed; the
runners, configs and records are in the session's scratchpad.

* **B-121 closed on option (a)** (decision 164). P&IDs 103 and 109 put PIC-323202 on the tempered
  water through two characterized outputs and tag 323D001's vent TV-323013; the 2007 loop summary
  puts it on the vent at 3.9 bar a; Book2's PIC-323202B is 323D001's own pressure. At 105 % any set
  point from 3.5 bar a shuts the vents, takes 3.1 t/h off 343 and balances 328D003 at FIC-328402 in
  proportion to load (X 54.32-54.39 %, 790-792 kg/t), FIC-329402 following FIC-328402.
* **FFIC-321404's basis.** The engine's ratio counts the whole CO2 feed gas as CO2: its design 2.0231
  is a true molar 2.086, and the plant's 2.115 is 2.047-2.053 here. At 100 % the plant's ratio holds
  (X 56.46 %, AT-322701 3.14); on Book2's 92.3 % set points it still trips 22.1, at 31 minutes.
* **B-118.** On the turndown ramp the reactor feed's N/C rises from 3.11 to 3.96 on 322E001's top gas
  (its nitrogen +23 %, its carbon -11 %), the stripper at its design shell pressure giving the loop's
  ammonia back faster than the feed falls; 322F001 stalls 4-10 minutes after the ramp at its design
  spindle.
* **The load schedule** (`load_schedule80.md`): 72 entries — 34 fixed set points, 9 scaled, 11
  cascade or ratio slaves, 3 ratio stations, 4 hand stations moved with load and 11 held — each
  relation derived from the engine's own equations and set against Book2's 92.3-111.0 % bands.
* **The sweep**, 20 runs from the design seed (3 h settle, 1 h hold): 100 % passes on the conversion
  objective (X 58.14 %, 858 kg/t, 1 797 MTPD); 70-80 % trip 22.1 at 51-62 minutes (B-118's slide);
  80-85 % and 115 % go NH3-lean and trip 22.2; 85-95 % and 105-110 % hold and fail on levels. Five
  runs a shutdown interrupted were re-run and matched their partial records sample for sample.
* **The re-holds** (resume directive): HIC-323605 on its relation, FIC-329402 trimmed on LT-328504 and
  328D003's trim made faster everywhere; at 110 % HIC-322604 capped at 76 % and a guard on PT-329201
  and TT-322005 through MASTER-329207, TIC-329005 and PIC-329204; at 100 % a 0.01 % deadband on
  HIC-322605 and 30 minutes more settle. 100 % passes on both objectives (RC100; RS100s at -0.22 %/h,
  RS100d at -0.37 %/h); 105 % passes on the steam objective after one more hour (RS105x: X 56.78 %,
  784 kg/t, 1 860 MTPD), HIC-323605's relation settling 324F001 and 323F010; the conversion
  objective at 105 % misses on four levels, the largest LT-322504's density-driven reading. The LT-328504 trim cannot
  damp LIC-328504's own ring. At 110 % the guard's handles reach their limits with PT-329201 at
  143.3-146 bar a: the steam objective completes without relief or trip and fails on six levels,
  328C003 and LT-322504's reading the largest; on the
  conversion objective the stripper's cut drains 322E003's sump and trips 22.2 at 51 minutes.
* **B-120.** With AT-322701 fed back the 168 C cut does not oscillate but leaves the loop NH3-lean
  (AT-322701 2.70); the mode shows on load steps (AT-322701 3.13-3.32 at 105 %) and, on the turn-up,
  as the NH3-lean chain to trip 22.2.
* **The workbook** (`D:\Work\Urea_Plant_Load_Optimization_70_to_115.xlsx`) rebuilt on the Session 80
  holds, with a third sheet carrying the 72-entry schedule; recalculated in Excel, 403 formulas and
  no error.
* **`CLAUDE.md`** gained the Sonnet + Opus advisor workflow at the process engineer's request, its
  sub-agent clause the one exception to §3 for Sonnet sessions, and `.claude/settings.json` the
  `"advisorModel": "opus"` setting.
* **Checks.** No source changed, so no test was run; the PyQt6 grep prints nothing.

### Session 81 — B-118 and B-120's narrowed option (b) measured; the cold start's trip 22.2

Session 81 (2026-11-04) first committed Session 80 (d047fd8). The process engineer approved the
Sonnet + Opus advisor workflow as written, its Stage 4 Opus sub-agent kept as the one exception to
§3. The session then measured B-118's and B-120's narrowed option (b) on a pasted plan, as scratch
patches in its scratchpad (As-Built Part XCIV). Nothing under `ureasim/` changed. The References
archive was moved by the process engineer to `D:\Work\Urea Simulation Docs\References`, and
CLAUDE.md §4 now names it. V1's source tree is no longer at `D:\Work\Urea Simulation`, so the
session ran the port side only (A-24).

* **The harness.**
  - `opt_run81.py` adds diagnostics to Session 80's runner.
  - `patch81.py` rebinds each candidate where its caller reads it.
  - Session 80's 92.3 % run is reproduced: the trip at the same tick, eight logged fields identical.
  - The split patch keeps the design seed to the bit. A margin moves it by about 1e-5: the committed
    seed's 322E003 liquor has a bubble pressure 0.0056 bar above the loop's.
* **B-118, 322E001's overhead.** Its NH3 overhead fraction stays at 0.855-0.835 on the ramp to 90 %,
  while the reactor overflow's NH3 grows 29 %. The growth comes from 322R001's holdup draining at a
  fixed HIC-322605 and from 322F001's suction halving at its design spindle. Session 80's attribution
  to the stripper is corrected. Scaling the overhead with load sends the loop NH3-lean (AT-322701
  2.60, TT-322004 182.3 C).
* **B-118, 322E003's margin.** At Book2's 92.3 % set points TT-322002 follows the tempered water to
  174-178 C, where the plant's holds 166.75 C. At AY-322701 3.25 the liquor's bubble pressure
  stands 35.4 bar above the plant's 138.39 bar a: 30.2 bar of temperature, 5.2 of composition. A 40 bar margin stops the saturation
  venting and leaves the reactor cold: TT-322005 178.9 C, X 49.9 %, 998 kg/t.
* **B-120 at 111 %.** On the plant's set points with 322E003's sump near the plant's level, the sump
  does not drain: the make (42.9 t/h) is about twice 322F001's full-spindle entrainment there
  (22.5 t/h), with HIC-322602 at 58.7 % against the plant's 76 %. The H/C slip (g_hc 0.71, the
  off-gas doubled) is a branch of a sump held at 50 %; at the plant's level it is 0.08. AT-322701
  (3.22) and TT-322004 (172.0 C) match the plant. 322E003 still vents 3.5 t/h, its liquor at
  180 C against the plant's 167.5 C, as at 92.3 %. The sump drains only under a stripper-steam
  cut.
* **Phase 7.** The committed engine's cold start trips 22.2 at 3 322 s and ends at 79.7 bar a.
  Session 52 accepted 136.04 bar g with 22.2 not reached (decision 110). This is raised as B-124,
  for a bisect. The trip 22.2 scenario still gives decision 110's answer, 22.2 not reached in 48 000 s (PT-329201 150.0 bar a at the end, 148.2 in session 52).
* **Checks.** No source changed, so no test was run; the PyQt6 grep prints nothing.

### Session 82 — A-24 closed; the cold start's regression bisected; TT-322002 against Book2

Session 82 (2026-11-04) took up three decisions of the process engineer, on a pasted plan.

* **A-24 closed** (decision 165, As-Built §XCV.1). The process engineer named
  `E:\Simulator\Urea Simulation` V1's source tree: `backend\main.py` 920 232 bytes of
  2026-09-18, its boot-pin cache keyed `81269104...d56c`, the key `ureasim/data/synthesis_pin.py`
  carries. `tests/equivalence/v1_loader.py` (`V1_ROOT`), `tests/phase7/drivers.py` (the runner's
  V1 side), `tests/units/synthesis/test_co2_compressor.py`, the default sources of
  `tools/analyse_step_sim.py` and `tools/convert_overlays.py`, and CLAUDE.md §0 and §4 item 3 now
  name it. `v1_available()` is true, the pin's key is the hash of V1's present source, and
  `tests/data/test_synthesis_pin.py` with `tests/equivalence/test_stripper_equivalence.py` pass,
  102 tests, none skipped. After the commit (f244d3e), the whole of `tests/equivalence` and
  `tests/data` passed on it: 6 148 tests, none skipped, in 1 h 34 min.
* **B-124 bisected** (As-Built §XCV.2). Each physics-distinct commit ran the cold start to 3 600 s in a
  scratch worktree. 0313003 reproduces session 52 (trip 22.1 at 134.5 s, 137.8 bar a at 3 000 s);
  15e66c2 moves it (103.6 s, 151.6 bar a, 22.2 at 3 272 s). Inside it, 322E002's low-N/C branch (B-106,
  B-111) alone restores it: switched off on HEAD, 22.1 latches at 135.4 s, 136.1 bar a at 3 000 s,
  22.2 not reached to 3 600 s; B-105's wash departure adds about 2 bar by 1 500 s. The cold start runs NH3-lean (AT-322701 about 2.0), where the branch adds the
  Extended UNIQUAC rise, 630 bar at N/C 2.0 and 170 C. Taking the rise at the live temperature does not
  restore it. Options (a) accept and re-baseline decision 110, (b) bound the branch below N/C 2.6 on a
  source; the deciding evidence first, then the full 16 000 s cold start and its fit. A worktree's checkout writes `activity.py` and `henry.py` in
  CRLF, so its node stores miss their keys until those two are rewritten in LF.
* **B-118 and B-120, TT-322002** (As-Built §XCV.3). A scratch prototype put the liquor's ceiling at
  the shell's condensing temperature at PT-329201, identical at the design seed. The liquor acts
  only through its saturation fraction. At 92.3 % TT-322002 matches the plant (167.3 against 166.75
  C) but f is 0.92 and 322E003 vents 1.8 t/h; with f held at 1, TT-322005 178.9 C and 322E001's
  bottoms 176.7 C against the plant's 182.6 and 166.6. At 111 % it holds 164.6 C against 167.5, f is
  1 and the shell's capacity (0.905) leaves 4.4 t/h uncondensed. LT-329501 settled in no arm. No
  band held; the 100 % guard was not run (RC100's snapshot overwritten; RS100s binds by 0.2 K).
* **Checks.** No source changed after f244d3e; the PyQt6 grep prints nothing.

### Session 83 — B-124's evidence and full cold start; 322E001 at turndown; 322E003's margin

Session 83 (2026-11-04) committed Session 82 (6ac6f08), then measured the pasted plan in its scratchpad
(As-Built Part XCVI). Nothing under `ureasim/` changed.

* **B-124.** Neither archive holds the melt's bubble pressure below N/C 2.6. The 3 June 2025 start-up reads
  AY-322701 3.69-3.16 with no overshoot, and the SOP feeds N/C 3.0 until the reactor overflows. With the
  branch off, the 16 000 s cold start gives no trip 22.2, tau 1350 s, dead time 540 s, final 137.45 bar g, 322R001 at its funnel's lip from 6 420 s (Session 83 read LT-322504's 36 % as not full; corrected in session 86, As-Built §XCVIII.1). On the SOP's ratio with the branch on, trip 22.2
  comes at 5 863 s. Decision 147 states no range, so a bound is unsourced; even the branch off is out of
  band. Recommended (a). Open: 322R001 fills to only 36 % by 8 000 s with the branch off. (Corrected in session 86: 36 % is the reactor full at its lip; the difference from session 52 is the funnel's backup above it, As-Built §XCVIII.1.)
* **B-118.** The engine's FT-329403 runs 14-20 % above Book2's FY-329403 at both loads (64.0 against
  53.5 t/h at 92.3 %), and 322E001's bottoms 10 K hot at 92.3 %. The bottoms term alone (V1's feed-deficit rise off) cools TT-322004 to 171 C
  but leaves the steam and the cold reactor. 322F001 cannot hold Book2's LT-329501 (suction proportional
  to the level): 16 % at best at 92.3 %.
* **B-120.** Uhde's datasheet rates 322E003 at 8 000 kW on 460 t/h (1.49 times the PFD). On that margin
  322E003 vents nothing at 111 %; the loop then runs NH3-rich on its fixed ratio (AT-322701 3.60).
* **Checks.** No source changed; the PyQt6 grep prints nothing.

### Session 84 — the start-up intro attached; the plant starts on 100% LOAD

Session 84 (2026-11-04) took the process engineer's request: an intro developed by another AI model, in
`D:\Work\Urea Simulation Docs\Intro\Sonet 5,5 extra\New folder`, plays when the software starts, and the
simulation starts when the 100% LOAD button is pressed. The advisor (Opus) was consulted on the plan before
any edit.

* **The package.** 33 files, identical in the folder and in its zip (checked byte for byte), copied into
  `ureasim/hmi/intro/` (with `assets/hfc-logo.png`), `ureasim/data/intro*.py` and `tests/hmi/intro/`; the
  preview video and the zip stay out of the tree. Its Qt tests, never run where it was built, all pass on
  real PyQt6. Two edits to its tests: the `QT_QPA_PLATFORM=offscreen` override at import is gone (it would
  have leaked into a full run and turned `test_screen_geometry`'s two overlap tests into skips), and one
  assertion reads the grab in device pixels (the console's 125 % display grabs 854 px for a 683 px window).
* **The hold.** Before this session the plant ran from the moment `run.py` started. The engine is now built
  held (`session.frozen`, set in `run._serve` before the physics thread exists, so nothing races it): its
  clock does not move, no packet is published and no trend fills. The press releases it with the engine's
  own `freeze` command, `on` always stated (a missing `on` toggles), the command the instructor's RUN button
  sends. No engine code changed. `--no-intro` runs the plant from the start, as before.
* **The order after the press** (`hmi/startup.py`, `StartupController`): the console is built hidden; the
  application waits for the engine; the bridge connects only then (a bridge connected to a held engine gets
  no packet, and its 5 s watchdog would blank it and reconnect); the release is sent once per link; the
  first non-empty packet calls `mark_ready()`; the intro asks for the console and fades. A refusal, a silent
  engine (30 s) and an engine that never started (60 s) end the wait with a reason, so the intro never sits
  on "STARTING SIMULATOR" for ever; only the last exits. The engine's thread is watched from launch, not
  from the press, so a port held by another instance still ends the application within a second.
* **Measured on this machine.** Press at 1.7 s, console built in 0.4 s, first packet about 6 s, console
  shown at 6.7 s. The first tick after the release is cold, 2.3 s on its own; the bridge's watchdog (5 s from
  the connect) leaves about 1 s of margin here, and a slower machine reconnects on its own, the console not
  yet shown. A throwaway warm-up tick was not added: it could change the thermo memo's history, and the
  physics is not touched for a start-up delay.
* **Frame cost, measured.** The intro repaints in 46 ms a frame at 125 % scaling (about 22 fps against its
  60 fps target); `drawLines` is 21 ms of it and the Python wire building 14 ms. The two knobs the author
  named, `alpha_steps` and `max_segment`, move it by under 10 % (`max_segment` is read when the model is
  built, so that test is inconclusive). Handoff A-25.
* **Checks.** 201 tests of the intro, the controller and `run.py` pass (`tests/test_run.py` keeps its
  seven earlier tests, its first now run with `--no-intro`); `tests/hmi`, `tests/net`, `tests/data`,
  `tests/docs`, `tests/test_run.py` and `tests/engine/test_session.py` pass, 626 passed and 13
  skipped (V1's tree absent on this machine, none for a font); the PyQt6 grep prints nothing. A scripted run
  of the real `run.py` path (skip, press, wait) showed the console visible with live packets.

### Session 85 — handoff A-25 decided and closed: the intro's frame cost, watchdog, section order, logo and tests

Session 85 (2026-11-04) took the process engineer's directive closing the six points of A-25. The advisor
(Opus) was consulted on the plan before any edit and on the result before the close.

* **1. Frame cost.** Measured first, by operation type, on the real window at 125 % display scaling:
  one repaint took 46.8 ms (21 fps): the shell wires 15.3 ms, the grid 7.0, the stream wires 4.5, the ground
  1.1 wires 3.6, the text 2.7, the circles 2.3 and the Python building of the frame 7.5. What was done, in
  order of payoff, each measured: round pen caps cost three times a flat cap's antialiased fill, so wire
  batches use flat caps (23.3 to 6.8 ms for the wires alone); the paper and grid are one opaque `Static`
  group, drawn once into a bitmap when it repeats on two frames and blitted; the wireframe's clip,
  projection, depth cue and text-zone fade run as numpy array arithmetic, equal to the scalar code **to the
  last bit** (the scalar version is kept in `test_intro_flyby.py` as the reference and a test demands equal
  operations over 969 frames, with the lens cutting edges, the scan and the fade-in); thin batches (no wider
  than 1.5 device pixels) are drawn as one-device-pixel hairlines with their opacity scaled by their width,
  which Qt rasterizes on a fast path (3.7 % ink difference measured at 125 %, 1 % at 100 %); the QLineF list is
  pooled (2.4 to 0.8 ms); fonts and text widths are cached; and the font database, which took 0.6 s on the first
  text and stalled the animation, is warmed before the window shows. Result on this machine: paintEvent median 15.0 to 15.1 ms (95th percentile 18.1 to 18.5 ms), delivered 60.3, 60.5 and 60.7 fps over three 10 s runs on an idle machine (57 to 59 fps while a background job loaded it).
  **Rejected with their numbers:** antialiasing off on the thin wires (3.6 ms, visibly jagged on the vessels);
  coarser `max_segment` (at most 21 % fewer edges, no measurable cost); one stroked path per batch (no gain);
  cosmetic pens (2 ms, but their width does not scale with the window); `QStaticText` (0.5 ms, but 1,148 bytes
  of the frame differ from `drawText`); a bitmap of the logo and titles (Qt blends text onto a transparent
  bitmap and onto the opaque window with different weights, a pixel difference of up to 76 in 255).
* **2. The cold first tick against the 5 s watchdog.** The thermo memo is not warmed. The bridge arms the
  long `FIRST_PACKET_STALE_MS` (30 s) until it has received a packet with content, then the strict
  `STALE_MS` (5 s) for the rest of its life, a reconnect included; the controller's own wait is 45 s, so
  the bridge speaks first. Tests: a first packet later than the strict window does not blank the console; five
  seconds of silence after the first packet still does; a reconnect after a packet gets the strict window; a
  blank snapshot does not end the allowance.
* **3. Section order.** The intro lights 321, 322, 329, 323, 328, 324, the order the console's tab bar first
  reaches them; the test derives the expected order from `screen_layout.SCREENS`.
* **4. The flyby's drawing choices signed off as built** (decision 167).
* **5. Logo.** `SmoothPixmapTransform` was already on in `IntroPainter.paint` and is now pinned by a test. The
  asset is the supplied 640 x 301 mark resampled exactly 2x (1280 x 602, 8-bit RGBA) on premultiplied alpha with
  Lanczos, each pixel clamped to the range of its 3 x 3 source neighbourhood (Lanczos alone overshoots by up
  to 46 in 255 at the mark's hard edges, which is the halo). A resample adds no detail; a vector mark from HFC
  would.
* **6. Test mirrors.** `tests/data/test_intro.py`, `test_intro_flyby.py` and `test_intro_plant.py` (the data
  checks of the old combined file); `tests/hmi/intro/test_intro_ops.py`, `test_intro_model3d.py` (its mesh
  checks), `test_intro_init.py` and `test_intro_main.py`; `ureasim/hmi/startup.py` has `tests/hmi/test_startup.py`.
  The directive names `background.py`: it is not in the package (the author deleted it, as his notes say) and
  was not recreated. Mutation check: nine deliberate breaks of the new behaviour, nine caught.
* **New open items.** A-26: the intro's frame rate has no margin at the hold and falls short fullscreen. A-27: a
  reset or exercise load while the engine is frozen leaves it publishing nothing, which the console shows as a
  blank after 5 s (found by reading the code and confirmed on the engine side; not run through the console).
* **Checks.** The full suite on Qt's native platform: 2,033 passed, 5,862 skipped, none failed, 37 min 56 s (the skips are the equivalence suites: `E:\` is not mounted on this machine today, so V1's tree at `E:\Simulator\Urea Simulation` is unreachable; session 82 ran them with none skipped, and they are to be re-run when the drive is back; no physics changed this session); the intro, bridge, start-up, data and run tests also pass under `QT_QPA_PLATFORM=offscreen` set on the command line (307 passed); pyflakes is clean on every touched file; the PyQt6 grep over net, engine, units, control, core, thermo and data prints nothing; no module is over 600 lines (the largest of the intro, model3d.py, is 389); nine deliberate breaks of the new behaviour were each caught by a test.

### Session 86 — B-124 closed (decision 168); FT-329403 at the design point; B-118 and B-120 under active trims

Session 86 (2026-11-04) ran the process engineer's 'Session 84' paste alongside sessions 84 and 85, which attached
the start-up intro. It committed Session 83 (2b9c891), then took up the pasted plan in its
scratchpad (As-Built Part XCVIII). Nothing under `ureasim/` changed.

* **B-124 closed on option (a)** (decision 168).
  - LT-322504 is a 1.5 m narrow band, so its 36 % is a full reactor overflowing at its lip, which
    0313003 and HEAD both reach at 6 420 s.
  - Session 52's full at 8 000 s is the band's top, where 0313003's funnel backs up from 6 900 s.
  - B-103 and B-104 are not the cause (69.0 to 74.6 % at the peak); the backup above the lip moved with 322E001's shell bound (decision 139, B-102, in 15e66c2): with it off LT-322504 peaks at 91.2 % at 7 740 s, while B-103/B-104 and the bundle alone do not restore it.
  - The cold-start record is re-baselined on the committed engine: trip 22.2 at 3 322 s.
* **FT-329403** is stream 901: 60.85 t/h at the design seed, Uhde's loop summary F 329403 giving 60.8 t/h
  normal. 902 is 57.99 t/h. The request's 66.90 t/h is the engine's 322E001 shell steam (`STRIP_DES_KGH`),
  not PFD 914.
* **B-118 and B-120 under active closed-loop trims.** Every handle holds its own target, live through a
  2 h hold after a 3 h settle. No arm passes the 1 h hold:
  - At 92.3 %, as built and on P1b, PIC-329204 runs to its bound with TT-322004 at 178.9 C.
  - At 92.3 % on S2 the means reach Book2 and B-120's loop mode then grows.
  - With V1's slip gain at 0, the loop holds steady with TT-322004, AY-322701 and FT-329403 in Book2's
    bands; TT-322005 is 5.4 K cold and 324F001 fills.
  - At 111 % the first tuning trips 22.1 and 22.2 at 149 minutes, through 322F001's forward pulse; the
    retuned arms hold out of band.
* **Checks.** No source changed; the PyQt6 grep prints nothing.

### Session 87 — handoff A-26 and A-27 decided and closed: the intro on a GPU canvas, a frozen plant's packet

Session 87 (2026-11-04) took the process engineer's directive closing A-26 and A-27, so that Section A would be
empty. It first committed sessions 84 and 85 (5e4f99f). The advisor (Opus) was consulted on the plan before any
edit and on the result before the close. Session 86, which ran alongside, had taken decision 168 and As-Built Part
XCVIII, so this session is decision 169 and Part XCIX. Nothing the plant computes changed.

* **A-27, a frozen plant's packet** (decision 169). A reset or a restored exercise left the engine with no results
  and so no packet, and a console that hears nothing for 5 s blanks. The engine now rehearses the plant's first tick
  on a copy (`engine/rehearsal.py`), lazily where the packet is built, drops it on an accepted command and on the
  first real tick, and shows the plant's own clock; the plant is not stepped. Asked about the directive's "and
  initial frozen hold", the process engineer kept decisions 166 and 167: the launch plant stays silent. Fresh-process
  runs with and without the rehearsal give equal states and packets after 60 ticks, for a reset and for a restored
  off-design exercise. Proved through a real `EngineBridge` and `MainWindow` over loopback at the 5 s watchdog
  (135 ms to the reset's packet, 98 ms to the restored one, six seconds live, no DISCONNECTED), with the watchdog's
  blanking of a silent engine and of a closed link kept; eight deliberate breaks caught.
* **A-26, the intro's frame rate** (decision 169). Profiled on the real window and decided by measurement, the
  renderers alternating in one sitting at idle and under 2, 4 and 8 busy processes: the fixed-stage wire layer
  (slower, 33 to 36 % softer), a cache per azimuth (6 MB a frame, 2.2 GB for 360 poses, 11 poses a second), worker
  threads (the GIL is held, 0.96 times one thread) and a cosmetic pen (no gain) were rejected; a GPU canvas was
  adopted with the CPU rasterizer as the fallback. Main-thread paint 7.5 ms windowed, 8.2 ms fullscreen; 60 fps held
  through 4 busy processes of 20 in both modes and fullscreen through 8, where the CPU rasterizer drops to 58 fps
  at 4 and 42 fps at 8 fullscreen; windowed at 8 neither renderer holds 60 fps (51.0 and 50.8). Not claimed: the
  whole frame, which is GPU-bound at 13.5 and 15.6 ms unthrottled; a GPU in use by something else, untested. The
  real start-up path, the exit fade, the status line painted before a blocking step and the picture were checked
  under the canvas.
* **Retraction.** An early conversation figure that the GPU path was slower (13.4 against 8.8 ms) came from a harness
  that overrode `paintEvent` on a `QOpenGLWidget` and so never drew the scene; none of it is on record.
* **A-28 raised.** The silent-engine run found the console live again between watchdog blanks, on the server's
  replay of the dead engine's last packet; not changed.
* **Checks.** pyflakes clean on every file touched, the PyQt6 grep empty, every module under 600 lines; the
  affected groups 770 passed and 13 skipped on the native platform, 279 passed and 4 skipped offscreen; the full
  suite on the native platform 2,070 passed, 5,862 skipped (the equivalence suites, `E:\` not mounted today; session
  82 ran them with none skipped, to be re-run when the drive is back), none failed.

### Session 88 — the load workbook's gaps researched: Book2's low-load holds and the licensor's load procedure

Session 88 (2026-11-05) took the process engineer's two directives: commit the open work, and run the deep-research
skill to resolve the gaps of the load workbook (`D:\Work\Urea_Plant_Load_Optimization_70_to_115.xlsx`). The
commits came first: session 86's decision-139 record alone (f1e470b, its hunks staged on HEAD so session 87's
uncommitted edits stayed out), then session 87's A-26 and A-27 work (97f6372) after its affected tests passed (276)
and the PyQt6 grep printed nothing. The research ran inline, CLAUDE.md excluding sub-agents; its notes are in the
session scratchpad (`research_notes/Load workbook gap closure/`) and its report in `D:\Work\reports\`. The advisor
(Opus) was consulted on the plan. Nothing under `ureasim/` changed and no decision was taken.

* **The workbook's engine values stand.** Its basis is 7a8fa3a; from there to 97f6372 only the intro's data and the
  frozen plant's rehearsal changed (decisions 166-169).
* **Book2 dwells below 92 %.** Two planned load cuts, 2023-07-25 and 2023-08-19, dwell 3-4 h near 70 % (69.3 %,
  n 28) and 3.4 h at 60.7 % (n 13); the 80.4 % window (n 9) is the return to load. Near 70 % the reactor top holds
  181.5 C (at most 0.24 K/h) with no trip, at PIC-329204 16.6 bar g, TIC-329005 94 C and HV-322602 40 %, while
  PT-329201 drifts up to +1.2 bar/h and TT-322004 and FY-329403 still move: dwells, not steady states by the
  workbook's criterion (the 92 % run of 2023-07-18 moves at most 0.03 per hour). The engine trips within 51-81 min at 70-85 %.
* **The licensor's start-up and shutdown pass through 70 %.** Operating Manual III (OCR'd from the scans) feeds
  70 % of the design CO2 before the reactor overflows (page 4-16), cuts to 70 % before a planned stop (page 6-3), and moves the loops by rule
  between 70 and 100 % (4.1.5.9, page 4-28); no minimum load and no table for 75-95 % or above 100 %.
* **The workbook finalized on the evidence.** Plant values at 70, 80 and 95 %; the sheets "Plant holds (Book2)"
  (every band from 60.7 to 111 %, the licensor's references) and "Gap register" (10 workbook gaps and the 11 data
  gaps: 3 resolved, 6 awaiting B-118 or B-120, 11 with no source, 1 open); 417 formulas, none in error on Excel's
  recalculation; the original kept in the scratchpad.
* **Data gaps.** No file in `References\` is newer than 2026-10-25; the manual's sections 7 and 8 print no interlock
  limit (gaps 2, 5, 6, 8); Book2 adds two operating points to gap 1.
* **What closes the engine columns:** B-118 and B-120, both with the process engineer; (b) recommended for both,
  the 70 % dwells' reactor top (181.5 C, no trip for 3-4 h) now an acceptance test for B-118 alongside the 92.3 % band.

### Session 89 — the routes to every open gap researched; decision 170: the five balanced Neldiscs on Valmet's S-Disc table

Session 89 (2026-11-06) took the process engineer's directive to find solutions that resolve all open gaps (A-28,
B-118, B-120 and the 11 data gaps). The research ran inline, CLAUDE.md excluding sub-agents; its report is
`D:\Work\reports\Open gaps resolution routes.md`. The advisor (Opus) reviewed the routes before the report was
written, and again before the build. The process engineer approved the report's Neldisc route ("Adopt, measure both"), built as decision 170; no other route changed anything (As-Built Part CI).

* **Neldisc (data gap 7).** Valmet's public bulletin 2SL120EN is the balanced Neldisc ("S-Disc"); its Table 2 reproduces
  the printed points of PV-329212, PV-329207A / B, PV-329208 (ASME 150) and PV-329204 (ASME 300) to within 1.3 % on the
  catalogue Cv (the sheets print "S-L-ANSI150" / "S-L-ANSI300"). The module's linear chord is within -2.9 to +4.6 %
  of rated Cv of it above the last printed travel. Session 71's "up to 30 %" compared a conventional valve
  (FV-329401) with this S-Disc table: a family mismatch, corrected in As-Built §CI.1. The nine conventional Neldiscs
  still have no table (route: a NELPROF output from Valmet). Adopting Table 2 supersedes decision 153 for the five
  balanced valves and is the process engineer's call.
* **The vendor archive.** The TOC's "Performance Curves" rows belong to machines, none to an ejector; the urea-unit
  loop diagrams (`UD-MR-32x-FS-0001`) are wiring only, no limit, hysteresis or tap datum.
* **A-28.** Option (a) built with two additions: the age on a wall-clock stamp, not the plant time, and the replayed
  engine status aged with the packet.
* **Decision 170 built.** `control_valves_metso._s_disc`: every printed point and the rated capacity kept, the table's
  shape between them and to wide open; the nine conventional Neldiscs keep the chord. Design strokes PV-329207B
  54.9630 to 55.9717 %, PV-329208 27.2232 to 27.2640 %, PV-329212 54.6805 to 54.6843 %. The design seed's packet moves by
  at most the PIC-329207B output's intended point; 29 dynamic pins in six modules were re-measured (all 29 pass on
  HEAD's chord, so each fails only on the new trim), the chord's value kept in the docstring where a record. B-122's
  linearised-step ringing demonstration falls from 11 successive reversals to 2 on this state, the solved step's
  none (at most one turning point) still holding. The V1-side equivalence suites were not run (`E:` not mounted)
  (As-Built §CI.5). Data gap 7 narrows to the nine conventional valves.
* **Routes.** One DCS readback session closes gaps 2, 5, 8 and 9; vendor requests gaps 1, 3 and 11; a walk-down gaps
  4 and 10; gap 6 is a decision. B-118 waits on B-120's decision.

### Session 90 — the start-up intro's LOAD button: the plant started from a saved exercise

Session 90 (2026-11-06) was a side session started by session 88 on the process engineer's request of 2026-11-05: a
"load" button on the intro that loads the saved exercise files (session 88's steady states in `scenarios/`, each held
15 minutes within 1 % and no trip). It ran in the main checkout alongside session 88 and session 89, the parallel
"Open gaps" session, which took decision 170, As-Built Part CI and A-29 meanwhile, so this session is decision 171,
Part CII and A-30. The advisor (Opus) was consulted on the plan before any edit and on the result before the
documents. Nothing the plant computes changed; in the engine only `EngineSession`'s exercise folders changed.

* **The intro's last frame.** "LOAD" (160 x 56, a folder glyph) stands beside "100% LOAD" (250 x 56, unchanged), the
  pair centred on the text column with a 24-unit gap, more than the two breathing rings reach, inside the flyby's
  text-column clear zone. The hit test names the pill under the point (`scene.button_at`); the pointer lights one
  pill; a press greys both. Clicking LOAD raises `start_requested("load_exercise")`; Enter and Space press
  100% LOAD only, so its keyboard start and "PRESS ENTER TO START" are as before. One press is taken.
* **The hand-over** (`hmi/startup.py`). After LOAD the controller builds the console and connects as before, asks the
  engine for its exercises, opens the chooser over the intro, restores the one chosen (`snapshot_load`), sends the
  release only once the restore is accepted, and ends on the first packet after the release is accepted: a plant
  restored while held publishes its rehearsed first tick (decision 169), and the server can send a pass's packet
  before that pass's ack. The wait for the engine stops while the chooser is open and restarts whole at the choice.
  The held engine is silent, so the bridge's 30 s first-packet watchdog drops and reconnects the link while the
  operator decides; each step's message goes out once per link and again on the next. The 100% LOAD path is
  unchanged (its release send moved into a helper; its tests unchanged).
* **The process engineer's answers** (2026-11-06). The three points were answered twice, differently, here and in
  session 88; asked which stood, the process engineer settled them in this session: Cancel, or no saved exercise,
  takes the intro back to its two buttons with the reason on its status line, nothing started (`splash.rearm`, the
  sequencer's `cancel_start`; the console and its link stay up, so the next press goes on from the link); a refused
  exercise reopens the chooser with the engine's reason, the plant held and untouched (the brief had it end the
  wait, which would show a held, silent console); SAVE writes the instructor's folder, outside the repository
  (CLAUDE.md section 6), and LOAD lists both folders.
* **The exercise folders** (`engine/session.py`, `run.py`). `EngineSession` takes a shipped folder beside the
  instructor's (`UREASIM_EXERCISES`, or `~/ureasim-exercises`): it lists both, each name once, restores a shipped
  name from the shipped folder, and refuses a save under a shipped name, so no instructor's file shadows a verified
  state and SAVE never writes the repository. `run.py` ships `scenarios/` (`SCENARIO_DIR`). The variable is set
  nowhere on this machine and `launch.bat` sets none.
* **Measured.** The real `run.py` path, scripted: LOAD pressed at 2.31 s, the chooser at 2.57 s, the choice at
  3.08 s, the restore accepted at 3.54 s, the release at 4.46 s, ENGINE RUNNING at 4.50 s, the console shown at
  4.64 s, its clock 25 863.8 s from load105_steam's 25 860.2 s. Cancel in the chooser put both buttons back
  ("NO EXERCISE CHOSEN") and Enter then started the design seed on the same console. Full screen on the GPU canvas
  the chooser is the active modal window and the topmost at its centre (a desktop grab and `WindowFromPoint`).
* **A-30 raised.** `EngineBridge.close()` does not stop the bridge reconnecting: the abort it makes emits
  `disconnected`, whose slot schedules a retry (a probe reconnected 1.5 s after `close()`). Not changed.
* **Checks.** pyflakes clean on every touched file; the PyQt6 grep below `hmi` empty; every touched file at or under
  600 lines (the largest module `scene.py`, 440; the largest test `tests/hmi/test_startup.py`, 489); 25 deliberate breaks of the new behaviour, all but one caught by a test, the one an
  equivalent change (As-Built §CII.7); the full suite on
  the native platform before the engineer's answers were built 2,117 passed, 5,862 skipped (the equivalence suites,
  `E:` not mounted), none failed; the affected groups on the final code 828 passed, 13 skipped (V1's tree absent), none failed.

### Session 91 — the open items resolved where the archive and the process engineer allowed: A-28, A-29, A-30 closed, trip 22.2 named, B-120 measured

Session 91 (2026-11-06 to 2026-11-07) took up every open item on the process engineer's request ("resolve all open
items", `/deep-research`, inline). Session 89's routes report was the starting point, not re-derived. The process
engineer answered four questions: A-28 and A-30 option (a); B-120 option (b), measured first, 70-80 % in scope; trip
22.2 kept and named as the simulator's; 322E001's U closed; the Valmet bulletins downloaded and a DCS readback
checklist written, no mail drafted. The advisor (Opus) was consulted before the work and on the plan.

* **A-28 and A-30 built** (decisions 172, 173, As-Built §CIII.1-2): the server replays no packet older than 1.0 s
  of wall time and says the engine is silent, restoring the stored status on the next publish; a closed bridge does
  not reconnect. Each fix's new test fails with the fix reverted (three mutations, all caught).
* **Trip 22.2 named** (decision 174, §CIII.3): "22.2 (simulator)" on the pump faceplate and in the engine's
  refusals; logic and set points V1's; register row 348. **322E001's U closed** (decision 175, §CIII.4).
* **A-29 closed** (§CIII.6): `E:` was mounted; the suites ran on decision 165's tree. The first run was
  contaminated by this session's own mid-run edit (a module loaded before `trip_label` existed, 81 import errors);
  the clean re-run gave 19 failed, 216 passed. Every moved value was recorded in one pass by a scratch pytest plugin
  that logs each `pytest.approx` pair, re-pinned at its literal's decimals, the old value kept in each docstring;
  the 19 pass. The whole of `tests/equivalence` and `tests/data` then ran on `E:`: 6 204 passed, and the one
  other moved pin (the vacuum condenser's trip through the train) was re-pinned the same way.
* **The process engineer's answers of 2026-11-07** (§CIII.9): B-120 option (b2), the gain to 0 only with B-118's
  change (decision 177), B-120 folded into B-118; the Valin L1 / L2 bulletin downloaded (large sizes only, no
  opening table), and Valmet's online L1 tables found to reproduce the nine conventional Neldiscs' printed points,
  proposed for gap 7, not built; this file's Last updated line and the commit of sessions 88 to 91.
* **The process engineer's paste of 2026-11-07, after the commit** (§CIII.10-12): decision 178 built — the nine
  conventional Neldiscs on Valmet's L-series rows, the pages archived in `D:\Work\reports`, both sides
  pinned — and the suite re-pinned on it (66 values in 22 tests outside the V1 equivalence, 48 in 18 within it,
  five exact compares), data gap 7 closed; one audit check met decision 163's chatter on 323F010, settled by the
  process engineer as decision 179; B-118 run at Book2's 69.3 % dwell set points: both arms trip 22.1 on the ramp.
  The proof run on the final code: 1 800 passed outside the V1 equivalence and 6 216 within it on `E:`, none failed
  (As-Built §CIII.13); the process engineer's note for the next B-118 session is in its handoff item.
* **B-120 (b) measured** (decision 176, §CIII.7): 12 arms through session 86's runner, the gain 4.0 against 0. The
  gain drives the mode; gain 0 alone runs the committed engine 12 K colder at 92.3 %, so the build waits on the
  process engineer's choice among (a), (b1) and (b2).
* **The archive** (§CIII.5): LT-329505's lower tap traced (EL +10651 on the condensate pot, 4 478 mm below N5,
  against the loop summary's 3 000 mm, logged); LT-324501's tap found (EL +8495); the nine conventional Neldiscs are
  L-series, Valmet's public L6 bulletins print no opening table; the urea loop diagrams are wiring only; Gmail holds
  no vendor answer. The DCS readback checklist is `D:\Work\reports\DCS readback checklist.md`.

### Session 92 — B-118 re-run at Book2's 69.3 % dwell on the process engineer's corrected boundary

Session 92 (2026-11-07), a side session of session 91, re-ran B-118's 69.3 % diagnostic with the three corrections of
the process engineer's note. Measurement only: nothing under `ureasim/` changed, no decision was taken, and the slip
gain stays 4.0 in the tree (decision 177). The advisor (Opus) was consulted on the plan and on the reading.

* **Book2 read again** (As-Built §CIV.1). HVGT-322605 reads 50.24 % at 100 % load, so the dwell's 36.14 % is 43.27 % on
  the engine's 60.0 % anchor (the vendor table's flow coefficient ratio, 0.730). PT-329207's dwell median is 4.398 bar
  g, so MASTER-329207 went to 5.411 bar a.
* **Six arms** (§CIV.2) through session 91's runner, copied unedited:
  - HIC-322605 ramped to 43.27 % or held by the board operator on LT-322504;
  - HIC-322602 on the spindle solve on LT-329501;
  - a pair beyond the brief with HIC-322604 on its plant offset (63.5 %);
  - each as built and on S2 with the gain at 0.
* **Result.** All six trip 22.1 before the hold, at 3 720-4 200 s; as built with the operator, at 1 980 s on 322E003's
  vent. In every arm 322R001 cools on the ramp. In the five that reach the ramp's end, TT-322005 reads 156-160 C at the
  trip (conversion 26-30 %) and the off-gas has grown 4.5-fold, until 322E003's sump floods with the spindle at its
  floor. With the operator on HIC-322605 the
  reactor tracks the design-handle arms within 1-2 K at every matched load. Session 91's baseline re-ran identically on
  HEAD.
* **The plant's descent** (§CIV.3). Book2 comes down at 0.7-1.0 %/min, the LP header raised first, with TT-322005
  2 K lower at the dwell. The engine falls more than 20 K on a slower ramp.
* **Not run:** session 86's active trims through the ramp, and the plant's own path. B-118 stays open, recommended (b).

### Session 93 — the plant's 5 November 2026 turndown read from `Data/Trends 511.2026`; data gaps and B-118 measured against it

Session 93 (2026-11-07/08) took up the process engineer's pasted request to resolve or narrow the open data gaps from
the plant DCS trends in `Data/Trends 511.2026`. Measurement only: nothing under `ureasim/` changed, no decision was
taken, and every script and run stayed in the session scratchpad. The advisor (Opus) was consulted on the plan.

* **The folder** (As-Built §CV.1-2) is 75 photographs of the ABB trend display, not an export: five pen groups,
  windows of 1 h and 15 min, all on 5 November 2026. The tables were read visually and transcribed; the traces were
  digitized (gridline-anchored time, RANSAC range lines, pen colours from the table) and checked against the display's
  own window means (391 of 560 pen-windows within tolerance). The table's "Current Value" is the live value of
  7 November (~101.5 % load), and no controller set point or output is logged. The plant held 68.9 %, 90.5 %, 74.4 %
  and 101.7 % that day.
* **Data gap 1, B-118** (§CV.3-4). 322F001 keeps its entrainment ratio (1.031 +/- 0.044) with HV-322602 closed as
  65.4 % (L / 101.95 %)^1.6; the engine's closure stalls on that line at 69.9-80.7 % on its fixed 4.2 bar lift.
  322E003's duty falls with the load, 1.44-1.52 times the PFD at full load: B-118's flood is the reactor's collapse
  upstream. A friction-share prototype of the lift (2.41 bar) keeps the seed's boot tick == and was run on twelve arms;
  it raises 322F001's capacity on the plant's spindle path, and 322R001 cools along the same path in every arm.
* **Data gap 3** (§CV.5). The plant runs both vacuum bleeds shut and holds 324F001 at its design pressure without them;
  the engine with its bleeds shut runs 0.05 bar deeper, and has no break-off where the plant loses its vacuum below
  55-64 % on HIC-329605.
* **Decision 178** (§CV.6). PV-323203 (to about 94 %) and TV-323013B (= PV-323202B, 64-76 %) run above their last
  printed travels; no differential is logged for any of the nine, so no in-situ Cv.
* **Data gaps 2, 4, 5, 8, 9 and 10** (§CV.7): not resolvable from the folder.
* B-118 stays open, recommended (b) narrowed to 322R001's heat on the descent; 8 data gaps remain.
* **Decided 2026-11-08 (decision 180).** The process engineer took session 93's options: B-118 (b) narrowed to
  322R001's heat balance and 322E002's hand-off on the ramp, with the 5 November holds added to Book2's bands as
  acceptance tests; the 322F001 lift prototype held in B-118's workspace with decision 177; 322E003 on its PFD
  anchor; data gap 3's maps kept and the break-off bracket recorded; decision 178 kept; the DCS readback checklist
  given 324E002/E005's cold ends (row 13) and TV-323013B's flow and differential (row 14). Session 93's scripts and
  data archived to `D:\Work\reports\Trends_511_2026_scripts` (outside the tree). Sessions 92 and 93 committed.

Session 94 (2026-11-08/09) took up the process engineer's second request of 2026-11-08: a term-by-term audit of
322R001's energy balance on the turndown ramp, in scratch only, with decision 180's workspace beside the as-built
baseline, and isolated prototypes of the responsible terms, both sides measured (As-Built Part CVI; the report
`D:\Work\reports\B-118 322R001 term audit.md`; the scripts in `D:\Work\reports\B118_term_audit_scripts`).

* Read-only recorders on the reactor and 322E002 (the seed identical on every leaf) close the column's budget
  exactly: TT-322005 - TT-322010 = carbamate - dehydration - wall loss - storage - boil cap; 13.0 = 31.8 - 18.8 K
  at the seed.
* Book2's column rise holds at 13.4-13.9 K from 69 to 111 %; TT-322010 falls 1.2 K at 69.5 % with the shell 2.5 K
  up.
* The carbamate source is the responsible term: zero by L 0.85 in both arms, 322E002's flash first (its CO2 gas
  fraction halving per kelvin of TT-322010), then the reactor's off-gas CO2 growing with the unconverted CO2 and
  V1's slip. The wall loss subtracts 1-5 K, the dehydration sink stabilises, and TT-322010's own departure is
  small on the ramp but 11 K too large at the plant's steady 69.5 % band on a constant UA.
* Four seed-exact prototypes measured; none holds the 69.3 or 68.9 % hold. As built with P1, P4 and decision 180's lift the 92.3 % hold passes; the workspace's S2 terms and slip gain 0 starve the reactor. The arms' handle laws were found
  stepping HIC-322602 and the AY-322701 target off the engine's seed at t = 0.
* Options (a) and (b) presented; no relation changed; Section B one open (B-118), 8 data gaps.
* **Decided 2026-11-09 (decision 181).** Option (a), `ureasim/` as built; S2 and slip gain 0 unbundled from
  B-118; P1, P4 and the 322F001 lift on the as-built stripper held as the candidate bundle, verified next on the
  five holds. Session 94 committed.

Session 95 (2026-11-10/11) took up the process engineer's request of 2026-11-09 (decision 181): Session 94's
documents committed (38561d4), then B-118's candidate bundle (P1 + P4 + the 322F001 lift on the as-built
stripper, with and without P6) verified in scratch on the five acceptance holds, measurement only (As-Built
Part CVII; the report `D:\Work\reports\B-118 bundle verification s95.md`; the scripts and runs in
`D:\Work\reports\B118_bundle_verification_s95`).

* P1's seed drift came from its basis, not its anchor; on the battery-limit CO2 demand ratio the seed is
  identical on every leaf, and CVI.5's statement that `co2_scale` keeps it identical is corrected. The lift
  moves TT-322010 3.9e-5 K by 60 s, 3 % of the seed's own wander. The null ramp is clean.
* 92.3 % passes on both arms; 90.5 % runs trip-free but out of Book2's band for 47 minutes; 74.4, 69.3 and 68.9 % hold
  TT-322005 at 181.4-182.5 C through the ramp, then fail: 322E002's condensation collapses from L 0.76 and
  the loop pressure reaches trip 22.2's 155 bar a. Six discriminators at 74.4 % tie the collapse to P1 on
  the load ratio, the same term that holds the reactor.
* 322E003's sump: the level factor does not throttle, the LP wash falls to 0.50 of seed by L 0.71, the
  sump fills only after the trip. P6 changes nothing.
* Options (a) and (b) presented, (a) recommended; no relation changed; Section B one open (B-118),
  8 data gaps.

### Session 96 — the documents reduced to state (2026-11-11)

At the process engineer's request the four living documents were restructured for reading cost. No
code, no relation and no handoff item changed; no decision number was taken. `project.md` (537 626
bytes) and `handoff.md` (117 439 bytes), read whole at every session start, are now 5 393 and 11 759
bytes: the state, and each open item's current state. The history moved verbatim, checked by script:
`project.md` §2-3 to `docs/architecture.md`, §4 to `docs/history/phase-checklist.md`, §4a to this file
and §5 to `docs/decisions.md`; `handoff.md` as it stood to
`docs/history/handoff-record-to-session-95.md`; `CLAUDE.md` §5 rule 7's 102 classes to
`docs/decided-classes.md`, one a line. `CLAUDE.md` §3a now holds the document map and the reading
budget, and the As-Built reference's stale table of contents gave way to a reading guide. Checks: the
PyQt6 grep prints nothing; `tests/docs` and `tests/test_run.py` pass, 22 tests; the suite was not run.

### Session 97 — the deep audit of the committed engine (2026-11-11)

On the process engineer's nine-pillar brief, read-only: no file under `ureasim/`, `tests/` or `tools/`
changed, no relation changed, no decision taken. The record is As-Built Part CVIII; the report
`D:\Work\reports\Deep audit 2026-11-11.md`. No critical finding; A-31 to A-37 and B-125 to B-132 raised.
Measured: every synthesis unit closes on N, C, H and O but the reactor's tear (B-127); 322R001's holdup
carries no composition (B-126); 322E002's saturation law contradicts Book2's bands (B-125). Session 95's
collapse read again in its archived runs: 322E002's feed N/C crossing 3.0 on a recycle (§CVIII.3).
B-118's scratch sequence E0 to E3 proposed (§CVIII.9). Suite: 2 154 passed, 5 862 skipped (V1 not
mounted), none failed; the PyQt6 grep prints nothing.

### Session 98 — the routes to the open gaps researched; the resolution plan (2026-11-11)

Session 97's documents committed (7ea8437). Then, on the process engineer's request, `/deep-research` (quick
mode), `/research-deep` and `/soft-copy-search`, all inline: the licensor's Figures 1 and 2 give the shape of
322E002's bubble-pressure law, a ridge with both branches rising, and no number (B-125's fit restated,
§CIX.1); 322R001's eleven trays and its archive drawings located (B-126, §CIX.2); no public source for the
Advant hysteresis or Körting's curves. The resolution plan, five waves, and its execution prompt written to
`D:\Work\reports`; its decision table awaits the process engineer. No code, no relation and no decision
changed; the record is As-Built Part CIX.

### Session 99 — the resolution plan executed: Waves 1, 2, 3 to E0 and 5 (2026-11-11)

On the process engineer's prompt and the plan's decision table. Wave 1 (bbdc3de): A-34's loop atoms tested tick
by tick, the layering test, the root ledger, the valve walk, the records corrected; A-31, A-32, A-34 to A-37 and
B-132 closed, A-38 raised; decisions 182 to 184. Wave 2 (27a855d): B-129, B-130 and B-131 built on ClassVar harness
switches, the seed identical on 3 694 leaves; decisions 185 to 187. Wave 3, scratch: E0 fails (the ratio's floor
binds, B-128); E0t classifies the collapse's chatter; E1 as fitted cannot keep the seed (a seed-gated E1 untested);
stopped, E1r to E5 not run. The control departs from session 95's A744 through B-129's heat term alone. Wave 4 skipped. Wave 5: the stand-in table and test, checklist rows 15 and 16, the Körting draft, gap
1's fits. `E:` not mounted. The record is As-Built Part CX.

### Session 100 — session 99 reviewed on its own runs; the next plan (2026-11-11)

On the process engineer's request. The tree holds what Part CX says; the suite on 52cfb57: 2 212 passed, 5 862 skipped (`E:` not mounted), none failed (17 min 05 s).
Session 99's archived runs read again: on the 74.4 % ramp the melt N/C hump is 322E002's K_N line (its term the
whole deficit in 36 of 46 samples), the ratio's PV never falls under 2.021 while its set point sits on the 2.0
floor, and the downswing starts at a ratio at or above the design. So B-128 is not what failed E0, and E1r, not
run, is the next experiment. B-118, B-125 and B-128 rewritten; A-39 raised (a test's race). The plan and its
prompt written to `D:\Work\reports`. No code, relation or decision changed; the record is As-Built Part CXI.

### Session 101 — B-118's scratch programme on session 100's plan; A-39 closed (2026-11-11/12)

On the process engineer's prompt, scratch only. Track 0 (366dbac): A-39's test waits for the running label.
Track S: E1eu's margin 4.38 bar at R 4.5; bundle A's seed departs through the lift's live motive, run as is
(decision 188); E1eu's seed fails the relaxed criterion on last digits; on the 74.4 % ramp E1eu holds 322E002
at full condensation, alone it leaves the as-built cold branch as it is, with bundle A the hump and collapse
stay. Track N: the floor at 1.9397 changes nothing material; the ratio fixed raises the hump; N3 names
322E001's bottoms; E5 puts 91 % of the tear's NH3 on row 116's re-pin; 322R001 has eleven trays. Track B: B0
on the tree, 92.3 % passing decision 180's test (AT-322701 under §CVIII.9's 3.0), 90.5 % out of band 47 min,
the three low holds latched. E2 to E4 not run (E2's gate).
Suite: 2 212 passed, 5 862 skipped, none failed (20 min 20 s); `E:` not mounted. The record is As-Built Part CXII.

### Session 102 — session 101 reviewed on its own runs; the next plan (2026-11-12)

On the process engineer's request. Part CXII's figures hold on session 101's run files, now archived in
`D:\Work\reports\B118_s101`. Read further: on the 74.4 % descent 322R001's inventory sends on 8.40 t more
than its reaction sent it and creates 235-294 kmol/h of N from 900 to 2 700 s; the loop's 153 t of liquor holds
no species, so its N/C is one tick's algebra, and the hump and the collapse are 84 % of the fresh ammonia and
6.5 times it as rates into 322R001's 136 t. B-126's species holdup, which session 100's plan had gated behind
E2, is B-118's next step. B-118, B-125 and B-126 rewritten. The plan and its prompt written to
`D:\Work\reports`. No code, relation or decision changed; the record is As-Built Part CXIII.

### Session 103 — B-126 (b)'s species holdup in scratch; the holds, 111 % and B-120's gain (2026-11-12)

On the process engineer's prompt (`D:\Work\reports\Session 101 review and session 103 plan and prompt.md`),
scratch only. C0 reproduces session 101's A744 and N3 sample for sample. 322R001's species holdup (one inventory,
twelve compartments) closes to 6e-14 kmol a tick; at 74.4 % the hump falls from 3.649 to 3.197 and the latch
goes; H0 (unscaled) shows the hump is the scaling; H5 closes the loop's atoms to 7e-6. On the holds the holdup
bundle passes 69.3 % on its band and 74.4 and 68.9 % trip-free, loses 92.3 % and latches 90.5 % on the cold
branch (the carbamate source first); AT-322701 falls while the seed's liquor washes out. E1eu, the ratio fixed,
the trim's gain doubled and slip gain 0 change no verdict; 111 % swings. A build candidate, not built; no
decision. Runs: `D:\Work\reports\B118_s103`. Suite: 2 212 passed, 5 862 skipped, none failed
(18 min 01 s); `E:` not mounted. The record is As-Built Part CXIV.

### Session 104 — an Opus session's advisor is Fable; the plan prompt for session 105 (2026-11-12)

On the process engineer's request. `CLAUDE.md`'s advisor workflow now pairs an Opus session with Fable and a
Sonnet session with Opus, and `.claude/settings.json` holds `"advisorModel": "fable"` (Claude Code's advisor
documentation accepts the pairing). The plan prompt for session 105 was written to
`D:\Work\reports\Session 105 plan prompt s104.md` on three instructions of 2026-11-12: trip 22.2 rechecked in
the plant documentation and removed if it is absent; the plant's thirteen load-reduction steps fulfilled at
reduced load, read as B-118's acceptance in procedural form; B-126 (b)'s cold branch at 92.3 % (§CXIV.11's
option (c)). Read for it and not measured: session 95's operator moves PIC-329207 on an open-loop schedule of
the load, where the procedure holds TT-322010 at 168-173 C with it; Operating Manual III's OCR text names
trip 21.2 alone, its Section 3 has no OCR text and its Section 8's is 21 lines. No file under `ureasim/`,
`tests/` or `tools/` changed; no decision entry and no As-Built Part.

### Session 105 — trip 22.2 removed; the load-reduction procedure measured; the holdup bundle's cold branch (2026-11-12 to 13)

On the process engineer's instructions I-1 to I-3. Built: trip 22.2's removal (decision 189, commit 18a7656), the
only change under `ureasim/`. Measured in scratch on byte copies of the tree (As-Built Part CXV; runs in
`D:\Work\reports\B118_s105`): the thirteen steps' map, their directions at the seed and at 92.3 %, five steps left
out, the procedure as the operator at five holds. L1, L6 and (on bundle A) L3 are needed; L3 is not fulfilled
(B-136); the L2 board loop as approved fails and helps no hold; the seed carries the 2 900 s mode; the CO2 line's
SV32064 lifts before the loop's reliefs (B-135); the holdup bundle's cold branch follows 322E001's `g_hc` and is not
L3's or the ramp rate's doing. The first reduced-load pass ran on a broken restore and was discarded; the repaired
rig reproduces its source to the bit. Decisions 190 to 196. Reviewed mid-session,
`D:\Work\reports\Session 105 interim review and closing prompt.md`. Suite on HEAD: 8 082 passed, 1 failed (A-40), none skipped.

### Session 106 — four console instructions researched; the plan prompt for session 110 (2026-11-13)

On the process engineer's four instructions: the CO2 feed control of 322-1, page 328-2's revised slide, the
granulator's header valves and the melt header, START and STOP on every pump icon. Research only; no file under
`ureasim/`, `tests/` or `tools/` changed and no decision was taken. Measured (As-Built Part CXVI): 328-2 differs
from its slide in two regions; V1's CO2 panel as read; 26 pump icons, five pairs with a run state; the melt
header's documents (UD-MR-324-FF-0002's structure, the loop sheets, Flowserve) and the trend windows, a header
valve at 3.30 m3/h per sqrt(bar g) `[I]`, ten valves at the engine's design point. "LV-335501A/B" in the
instruction is LV-324501A/B (the process engineer's correction). Raised A-41 and B-137. Plan:
`D:\Work\reports\Session 110 plan prompt s106.md`; scratch: `D:\Work\reports\Session_106_research`. The build is claimed ahead in
`project.md` (session 110, decisions 220 to 239, Part CXX, A-45 to A-49, B-145 to B-149), so it meets the
gap-closing sessions, 107 on, on no number.

### Session 110 — the console instructions built to their checkpoint; the melt header measured in scratch (2026-11-13)

On session 106's plan, its defaults approved: page 328-2 takes its revised slide (decision 221); 322-1's CO2
FEED panel, V1's hand station, steps 320K002's demand by 2 % of design on V1's arithmetic, `co2_step`
(decision 220; CLAUDE.md §0 and §4a amended); every pump with a run state opens START / STOP, a PUMPS block
publishing 323P001's and 328P003's (decision 222). Measured: STOP on 322P002 empties FT-322402, on 323P001
latches trip 21.2 the same tick, on 328P003 changes nothing. In scratch, the melt header (B-137): AC4 PC35.2
sets LV-324501B and PIC-335201's set point 2.8 + min(X / 50, 1) from LIC-324501 (FF-0002's 0.8 is the
functional diagram's); PIC-335201 read one tick late rings (loop gain 1.80), read inside the header solve it
settles; V1's selector relays. The eight pairs with no run state surveyed (A-41). Stopped at the checkpoint for
the process engineer's decisions. V1 read from its copy on D: (decision 223). Suite: 8 100 passed, 1 failed
(A-40), none skipped. Part CXX; scratch `D:\Work\reports\Session_110_console`.

### Session 108 — 322R001's reduced-load loop taken apart by path clamps; nothing built (2026-11-14)

On session 107's plan (B-118), scratch only, the rig proved by continuation (0 columns differing). Desk: V1's
`X_INF` is a back-solve and its slip gain a tuning; re-anchored on the licensor's 95 % approach the column's loop
gain falls from 1.0 to 0.01 K/K, but its design profile misses the plant's thermowells by 2-3 K and its seed
drifts. Path clamps, the stripper's feed-deficit rise off: 322E002's saturation edge or V1's re-flash of the
off-gas at the live pressure each loses 92.3 % alone; with the three paths pinned the top stands on its bubble
point, as the seed's does, 0.53 K a bar of the engine's pressure fall (the law's docstring says 0.75). At 69.3 %
nothing stands. 322E002's UA on its own feed loses the top sooner; its split on Book2's departures boils it 1.4
t/h. The scorer's bubble-cap gate was withdrawn: the seed sits on its bubble point. The plant's thermowells by
load, 320K002's 70 % case and P&ID 102 read. No decision taken. Part CXVIII; scratch `D:\Work\reports\B118_s108`.

### Session 107 — session 105's close-out reviewed; the reactor's loop isolated by clamps (2026-11-13; entry filed by session 109)

A review on session 105's files and its own scratch arms on the holdup engine; nothing built, no decision. With
V1's feed-deficit rise off, 322E001 follows the plant's TT-322004 (-1.5 K at 92.4 %, -5.5 K at 69.6 %) and all
five holds of decision 180 are lost. The loss needs neither 322E002's live law (`e002_clamp`), the conversion's
residence time (`x_clamp`), its slip (`og_clamp`) nor its movement (`x_pin`); the one standing hold boils on its
bubble point. 322E002's flash at the plant's departures gives 0.215 at 92.2 % and 0.310 at 69.5 %. 322R001's
design conversion is 60 % of its equilibrium by V1's `X_INF`; the licensor gives 95 %. Corrections: step L6 acts
in the procedure's sense; step L2's one-sided response is B-125's edge. Plan: `D:\Work\reports\B-118 plan prompt
s107.md`. Part CXVII (filed in session 109, wave 6's table completed); scratch `D:\Work\reports\B118_s107`.

### Session 109 — sessions 108 and 110 reviewed on their files; the plans for sessions 111 and 112 (2026-11-14)

A review; nothing built, no arm run, no decision. The process engineer's notes of 2026-11-14 answer session 110's
checkpoint: the melt header runs at 3.2 to 3.8 bar g with the headers following the load, LV-324501B returns the
excess above 3.8 bar g, and the pump faceplates simulate the field start and stop. That rule is AC4 PC35.2 as
configured; N valves hold the band at loads of N / 10 x 95.6 to 104.2 %. AC4's MOTCON sheets read on the images:
323P003 and 329P003 have no process interlock (§CXX.5's OCR corrected). HV-335602 drains to 335D004 (P&ID 130,
136); 322P002's own sheet shows no control valve (B-133). Session 108's run files carry its figures; beside
them, 322E002's flash target swings 0.16 to 0.27 inside 1 K, the clamp that stands is a law on the top's
subcooling (B), the duty-closed condenser (S, B-125 (c)) was never run, "stands" was scored on a boil-off the
plant does not measure, and (desk) Book2's pressure falls about 6 bar at 69.3 % beyond its thermowells'. Sessions 111
(the console build) and 112 (B-118: S and B) claimed ahead. Part CXIX; report and prompts in `D:\Work\reports`
(`Sessions 108 and 110 review s109.md`); scratch `D:\Work\reports\Session_109_review`.

### Session 111 — the melt header computed on AC4 PC35.2; the eight pump pairs given a run state (2026-11-14)

Built, one commit a track or pump pair, no push. Track H (B-137, closed): `units/finishing/melt_header.py` solves
the header from the twelve header valves (GRANULATION HEADERS on 324-1b), LV-324501A on 335P001's curve,
LV-324501B and HV-335602, PIC-335201 read inside the solve; LIC-324501's X sets LV-324501B and PIC-335201's set
point 2.8 + min(X / 50, 1); at the seed X is 35.0 and no other leaf moves; saves migrate (decisions 224 to 226). Four
downstream tests were re-pinned on the header's 3 kg/h. Track P (A-41): 335P002, 329P003, 328P007, 328P006,
328P002, 323P008, 323P003 and 335P001 hold a run state; both machines stopped stop the pair's flow and a swap moves
nothing (decision 227). Not built: four pairs' L2 stops (no L2 in either archive; data gap 8), trips 35.1 and
35.4. Raised B-145 and B-146. Suite on 463d7e6: 8 155 passed, 2 failed (A-40; the liquor-train scheduler test's
fixture lacked 323P003's run state, fixed in 000bdaa). Part CXXI; scratch `D:\Work\reports\Session_111_console`.

### Session 112 — the laws S and B for 322R001's reduced-load loop measured in scratch (2026-11-14)

Scratch only, run beside session 111; nothing under `ureasim/`, `tests/` or `tools/` changed; no decision. On
session 108's rig (commit 18a7656, its proofs and nulls passed), arms at 92.3 and 69.3 % and two cold starts. D1
(decisions 180 and 196, the rise in 13.05 +/- 1.0 K) stands on Z + B at 92.3 % with 322E001's lean rise off and on
(13.15, 13.14 K), on S + B on UA as built with the lean rise on (13.24 K), and on Z + B at 69.3 % with it on (13.61 K;
the top boils 1.8 t/h, off the licensor's windows). S alone moves neither the rise nor the latch; B lifts the rise;
on the cold start B sits on its 180 bar a bound and adds no lift. Not run: Track 0's desk checks, step L2's
+-0.1 bar steps, Track 4's clamp. B-118 and B-125 rewritten. Part CXXII; runs `D:\Work\reports\B118_s112`.

### Session 113 — sessions 111 and 112 reviewed on their files; the header's step researched (2026-11-15)

A review (Fable, then Opus with the Fable advisor); nothing under `ureasim/`, `tests/` or `tools/` changed; no decision.
The full suite on HEAD 4593bb2: 8 156 passed, 1 failed (A-40), none skipped. Session 111's seed moves 380 old leaves
by at most 1.3e-4 relative against 89428cc: its log entry's "no other leaf moves" is corrected (§CXXIII.2). Session
112's 92.3 % S + B arms ring on a 2 300-2 400 s period and were scored unsettled; S drifts 0.20 K on the seed. The
licensor's bubble point follows the system pressure, the synthesis pressure less the inerts (§CXXIII.5); trips 35.1,
35.3 and 35.4's inputs are read (§CXXIII.6); P&ID 104 takes 740 and 741 past 328P007 (§CXXIII.4). The header's step on
one valve is a third of the plant's 5 November dip (§CXXIII.9). Raised A-50 and A-51; claimed sessions 114 to 116.
Part CXXIII; report and the session 114 and 115 prompts in `D:\Work\reports`; scratch `D:\Work\reports\Session_113_review`.

### Session 116 — LV-324501A's positioner and its sheet inlet on the melt header (2026-11-15)

Opus with the Fable advisor, in session 113's conversation. The process engineer chose A-51's option (c), tau 1 s:
decision 236 puts LV-324501A on a first-order positioner lag inside the header solve (tau 0 is decision 224 to the
bit: 7 400 ticks against HEAD's module, none differing); decision 237 takes its sheet's 6.9 bar a inlet, 2.387 bar on
the design header, the design stroke 79.09 %. One header valve at 13:30 on 5 November 2026: ratio 0.921 and 0.929,
kick 4.9 and 4.4 % (plant 0.918 and 0.932, 5.3 and 4.4 %); the eleventh valve dips 3.5 to 3.2475 bar g, no ring. The
seed moves the output and LV-324501A; 369 far leaves by at most 1.6e-6 relative. A-51 closed; data gap 12 raised. A-56,
the dip a restore then opened with, raised and closed on the engineer's choice (b): decision 238 opens LV-324501A at
the stroke passing the save's drain (six exercises within 1e-10 bar). The suite: 8 179 of 8 180 pass, A-40 failing
(the equivalence groups not rerun after decision 238). Part CXXVI; scratch `D:\Work\reports\Session_116_header`.

### Session 117 — V1.1 independent of V1; the trend window's CLEAR; A-38's sixteen modules tested (2026-11-15)

Opus with the Fable advisor. The process engineer's three instructions. A-33 closed (decision 210): an audit hook over
the whole suite found the 37 files it reads from V1, and the Phase 7 driver's child process, unseen by the hook, added
`pressure_drop.py` (32 modules, two caches, four scripts; 1.76 MB); they are copied byte for byte into
`tests/equivalence/v1_reference` with a SHA-256 manifest and `-text`, the loader, the Phase 7 drivers, the CO2
compressor test and two tools repointed, and a guard test fails, never skips. Decision 211: CLEAR on the trend window
takes every pen off and keeps the span and the rulers. A-38's sixteen modules have 140 unit tests (its five run flags
stay, session 115's Track C). Data gap 11: KSB's plan gives 335P001's 82 m3/h at 65.2 m, the law 0.8 % above. Uhde's
level data sheets (EC-0133, EC-0136) give LT-329505's 0-300 mbar on 3 000 mm and LT-324501's -700 to 900 mbar, not
applied. With V1 blocked: 8 325 tests, 8 324 pass, A-40 failing. Part CXXVII; decisions 210, 211.

### Session 118 — The open gaps searched in the archive; 322P002's field hand valve; B-145 closed; B-156 (2026-11-15)

Opus with the Fable advisor; research inline. The archive holds no set-point list (gaps 2, 5, 8), no KSB test of
335P001 (gap 11) and no response time for LV-324501A's SRI986 positioner (gap 12). Operating Manual III sets 322P002's
flow by hand at FI-322402; Uhde's level sheets confirm the six modelled tap spans (pinned by a new test) and leave
seven levels on V1's holdup ratio (B-156 raised). The process engineer chose: 322P002's delivery set in the field from
the instructor's panel, in FI-322402's m3/h, seeded at PFD 744 (decision 212, B-133 closed; 3 000 ticks identical to
HEAD at the seed); B-145 closed as built, LV-324501B's floor being its sheet's 50:1 (decision 213); decision 33's
class for the seven, unit by unit (decision 214). Research: `D:\Work\reports\Session_118_research`. Part CXXVIII;
decisions 212 to 214.

### Session 119 — A-38, A-40, A-41 and A-50 closed: four low-level stops, 328P007 as built, two tests restated (2026-11-15)

Opus with the Fable advisor; inline. `master` pushed to `Urea-OTS-V1.1`. The process engineer chose: 328P007 kept as
built (decision 215); A-40's test restated on decision 186 (decision 216); L2 = 5 % for all four AC4 low-level stops
(decision 217, A-41). Built: `control.interlocks.low_level_stop` and `data/low_level_stops.py`; 328P002, 328P006,
328P007 and 335P001 stop below 5 % and run again at 7 %, no latch; saves migrate; the seed identical to HEAD over
600 s on 755 leaves. Measured: the three desorption drains cycle between 5 and 7 % and never reach their heels; on
B-62 and B-63 stage 2 holds 346 kg and its seal stays covered. A-38's run flags have unit tests; A-50's test asserts
B-106 on window means three trees agree on to 0.02 t/h; the engine's own sawtooth is A-57. Suite: 8 355 tests, all passing (the whole suite, 8 353, before the review's fix and 335P001's test; their files rerun after). Part CXXIX;
decisions 215 to 217. From the code audit: a faceplate refuses NaN and infinity, which the bridge's strict JSON
could not send and which crashed the console (`hmi/faceplates/base.number`, `test_hand_valve.py`); a failed
exercise save leaves the file it was to replace (`engine/snapshot.save` encodes first and moves a temporary file).
From the review: a pump held by its stop shows stopped, its command published apart; 323P008's stop calls `low_level_stop` (As-Built §CXXIX.1).

### Session 120 — The folder layout; trips 35.1, 35.3 and 35.4 built; B-127, B-128 and B-135 researched (2026-11-16)

Opus with the Fable advisor; inline (no sub-agents, so `/research-deep` was not used). The process engineer chose
every file in the folder, the suite, reports and scratch in `Tests and Reports` sub-folders (decision 218), and B-146
on Track B's D2, D3, D5 and D6 (decision 228). Built: the layout, saved exercises in the git-ignored `exercises`;
`control/granulation_trips.py`, the `335-TRIPS` step, `ProcessLoop.step(hold=)` for AC4's CLAMP and four overrides on
324-1b. Measured: the seed's 775 leaves unchanged to the bit, 8 added; six exercises run with no trip; the B-62 holdup
unchanged; the restart through HS-335201A recovers about 78.9 t/h, LV-324501B passing up to 184 t/h; in the cold start
335P001 cycles on its stop with 35.4 held. Researched: the DCS's FY-321404 formula sourced (UD-MR-321-FF-0002 p. 4)
and checked on Book2; the CO2 line 4.98 bar over PT-329201 on the plant. A-58 and A-59 raised. Then, on the
process engineer's yes, 21.2's pump timers moved to the sheet's 5 and 15 min and 21.8's to 5 min; A-58 closed.
Suite: 8 387 passed (shared tree), 321 (this change), 159 (combined). Parts CXXX, CXXXII; decisions 218, 228, 229, 231.

### Session 121 — B-156's first unit: LI-323502 between LT-323502's taps on 323D001 (2026-11-16)

Started by session 120 on decision 214. Chose 323D001: its datasheet is in `References\`, its as-built drawing in the
archive, both taps on the cylinder. Read 2 178 mm by 2 350 mm, taps 1 910 mm apart symmetric about the mid-plane
(EC-0005, DZ-0005-005, EC-0134); the volume conflict 11.10 / 11.46 / 11.83 m3 explained. Measured both sides in
scratch on an export of HEAD: the unit's four arms, the seed and the six shipped saves. The process engineer chose the
datasheet's 11.10 m3, on which the design holdup reads 50 % to the bit, and accepted a restated seed criterion. Built
``lt_323502_pct`` and the condenser's ``taps`` switch (``V1_TANK`` V1's), a decided-divergence equivalence test, the law's
test and LT-323502's sheet row; two PFD 734 pins moved. The seed: tick 1 identical; unrounded, up to 5.7e-5 by 600 s,
more than the 1e-5 first put to the process engineer, who then accepted the measured 6e-5 (decision 230, pinned). Nothing in decision 217 changes; LT-323503's
move will carry 323P008's stop. Part CXXXI; decision 219; register row 352.

### Session 122 — handoff A-57 closed as built: 322E002's sawtooth below N/C 3.0 traced (2026-11-16)

Traced A-57's 5 s cycle per tick on the harness and on the whole engine, which cycles alike (38 returns in 200 s). The
cause: a relaxation cycle of the synthesis recycle on B-106's rise. The fraction runs to 0 through 322R001's overflow
and 322E001's top gas; at the bound PT-329201's jump cuts the CO2 tie-in's flow to 322E001, whose top-gas CO2 carries
95 % of the N/C's turn. Nine arms: the fraction held, B-106 off or the CO2 into 322E001 held remove the cycle; the boil
ceiling held, the overflow lagged, the stripper's pressure or ratios held do not. No AY-322701 record below 3.02;
Operating Manual III sections 1 and 5 OCR'd, no cycle described. The process engineer kept it as built; a held melt on
322E002, measured, moves the decided means. Nothing built; the docs and layering tests run. Part CXXXIII; decision 232.

### Session 123 — B-156's second unit, 322P002's field ceiling, FY-321404 on the DCS's formula, four items closed (2026-11-16)

Researched every open gap, then closed them one at a time. Data gap 13: FI-322402's 0-40 m3/h (Uhde's loop summary)
inside 322P002A / B's 6-60 m3/h (KSB's sheet) is the field delivery's ceiling (decision 234). LI-323503 reads between
LT-323503's taps on 323D011 (EC-0006's sketch, 1 310 mm, 3.15 m3), the design 26.77 %, LIC-323503 seeded there, saves
restated on load, the three loop factories split to `flash_condenser_loops`; the seed parts 3.2e-4 by 600 s, decision
230's bound restated for the unit (decision 233); seven unit pins moved and restated. FY-321404 is published x 1.0317
and set / 1.0317 on the DCS's formula, the floor 2.0 on the display (decision 235, B-128 (b)); B-127 (a), A-59 (a) and
B-135 (a) closed as built (decisions 235, 239, 240; A-59's (a) the session's call). `/research-deep` not run: it fans
out to agents (§3). Part CXXXIV; register rows 353 and 354.

### Session 124 — B-156's third unit, LI-323501 between its taps; data gaps 2 and 8 signed off (2026-11-16)

Took up session 123's survey (`Tests and Reports\reports\Session_123_gaps`) and closed what needed no readback.
LI-323501 reads between LT-323501's taps on 323C003: R.L. at EL +15.703 m off the isometrics, the neck, the 15-degree
cone and the shell off Glatt's drawing and Uhde's sketch, the sheet's 2000 mm (the isometric's 2073 mm logged); three
design readings measured on the whole plant, the plant's 40 % chosen, LV-323501's seal moved to N5's lower edge
(29.21 %), saves restated on load (decision 241). The seed's flows part 4.86e-5 by 600 s, 324E001's boil-off 1.58e-2,
the bound restated for the unit; decision 233's boil-off bound restated to 4.3e-3 on the same terms. Thirty-five
pins moved and restated; B-104's take rings with a period of two ticks, now asserted on the two-tick mean (A-60).
Data gaps 2 and 8 signed off on their stand-ins (decision 242). Part CXXXV; register row 355.

### Session 125 — the gap-closure docx checked; B-156's fourth unit, LI-328503 between its taps (2026-11-17)

Read 'V1.1 Gap Closure.docx' whole, equations included: a generic steady-state blueprint whose author could not see
the project; it names no open item, its Piotrowski polynomial misses its own worked point, and no number of it is
taken (report: `Tests and Reports\reports\Session_125_gaps`). LI-328503 reads between LT-328503's taps on
328C002: N7B and N7A 300 and 1 500 mm above the partition (UD-AU-328-EC-0001 pp. 6, 7; EC-0134 p. 6), V1's design
holdup kept at 70.83 % (V1's 1.150 m is the drawing's H.L.L.), LIC-328503 seeded there and saves restated; 328P006's
L2 stop moves to 693 kg (decision 243). The seed parts 1.96e-5 on flows and 6.6e-5 on the boil-off by 600 s, inside
decision 230's bound. The process engineer confirmed decision 233's restated 4.3e-3. Part CXXXVI; register row 356.

### Session 126 — B-156's fifth unit, LI-328505 between its taps; A-60 traced and closed (2026-11-17)

Ran a pasted plan, its numbers measured: its N.L.L. for 328C004 (720 mm) is not the drawing's 510 mm. LI-328505 reads
between LT-328505's taps, N11B and N11A 210 and 1 210 mm above the bottom tangent line (UD-AU-328-EC-0001 p. 6;
EC-0134 p. 7), V1's design holdup kept at 71.00 % (V1's 0.920 m is the drawing's H.L.L.), the N.L.L.'s 30.00 % measured
and not taken; 328P007's L2 stop moves to 689 kg (decision 244). The seed parts 2.36e-5 by 600 s, inside decision 230;
323C003's boil-off part stays 1.582e-2. A-60's ring is LV-322501's Pv jumping across the rigorous surface's edge
(907 bar, then refused: water's 3.5 bar) through the one-tick overflow tear; closed as built (decision 245). Part
CXXXVII; register row 357.

### Session 127 — B-156's sixth unit, LI-328504 between its taps; data gap 11 closed (2026-11-17)

Ran a pasted plan, its numbers checked on the page images: KSB's test tables are as pasted; LT-328504's sheet is not
(rev. 2: 908 kg/m3, 0-96.15 mbar, 14.7 bar a, 190 C), nor are its tap heights (N5A / N5B 19.375 / 20.375 m above the
bottom tangent line). The N.L.L. stands mid-span, so V1's design holdup, kept, reads 50 % on the taps: LI-328504 between
them, 25.1 times V1's gain, the loop damped; AI-328701's seed part restated to 2e-4 (decision 246). Data gap 11 closed
on KSB's K 77746 / 77747, the law kept, its slope at design the test's (decision 247). LT-329501's sheet read, not
built. Part CXXXVIII; register row 358.

### Session 128 — the New folder's gap-closure reports checked; LT-329501 to the ledger (2026-11-18)

Asked to close every open gap from `References\Gaps Closure\New folder`: two truncated AI-tool docx reports and three
copies of one HTML blueprint. Each claim was traced to its page, most read on the image (As-Built §CXXXIX.1 says which). None closes an item: the B-118
cluster's "bundle" is the handoff's own options; the 322F001, ejector, LV-324501A and LVSL claims are known, misread or
not on the page. LT-329501's taps were found on line 322004 (piping list pp. 91-92; as-built isometric UD-RL-100-MB-0004),
12 789 mm apart against the sheet's 10 000 mm, and p. 27's +16.65 m belongs to 322E003's bottom part: LT-329501 moved
to the ledger as data gap 15, V1's ratio kept, B-156 closed on six units (decision 248). Rows 1, 9, 12 and 14 updated;
the stale stand-ins test restated on the ledger. Nothing under `ureasim/` changed. Part CXXXIX.

### Session 129 — the open gaps researched in the archive: transmitter records, hook-ups, AC4's UF85 loops (2026-11-18)

Asked for deep research on the open gaps, then a plan, its execution and a commit. Run inline (no fan-out, §3). Three
sources never cited before: Rosemount's factory list and test protocols of the level transmitters (UD-MR-G00-DZ-0012),
Uhde's installation arrangements (UD-MR-G00-LD-0001) and AC4's PC35.2.13. LT-329501's legs are drawn purged full of
condensate (K3V91); LT-324501 is read as a gauge reading at its one tap (K1A42); LT-329505 has a condensate reference leg
(K3V31); the DCS carries FFIC-335406 over FIC-335405A and B; the SRI986's capacity bounds LV-324501A's full stroke at
6.6 s or more on 2.0 bar g, 3.1 s on 6 bar (calculated). No row closes; rows 4, 9, 10, 12, 14 and 15 updated. LT-328503's factory 0-326 mbar against
the 110.51 mbar built: checklist row 26. Nothing under `ureasim/` changed; no decision. Part CXL.

### Session 130 — 2026-11-18: the open gaps researched by seven agents

`/research-deep`'s fan-out ran for the first time: seven read-only agents on `References\` and the soft-copy archive,
one per gap group; every value used was read on the page image. Found: AC4 PC21.5.1's three trip 21.2 timers (page 20)
are ABB TOFF elements (DZ-0045-016 p. 447), so 21.2 trips 5 min / 15 min / 5 s after its causes where the build trips
at once; FY-322403's trip is 8 500 Nm3/h on the as-built schedule (30.0 % of design against V1's 5 %). Both are build
candidates, unmeasured, for the process engineer. PIC-335201's CLAMPREF is a printed 0; LV-324501A has a booster relay,
withdrawing §CXL.4's slew bound. Rows 1, 3, 4, 9, 10, 15 and B-136 narrowed. Then, on "Measure then build": measured
in scratch (a pump stop trips 21.2 at 359.9 s, a CO2 cut to 10 t/h at 78.1 s) and built both: `OffDelayTimer` for
page 20's three T (decision 249) and `TRIP_21_2_FY_L2_NM3H` = 8 500 (decision 250); six exercises and five equivalence
pins restated. Parts CXLI, CXLII; report `Tests and Reports\reports\Session_130_gaps`.

### Session 131 — 2026-11-18: another tool's closure dossier checked against the archive

Asked to close the open items with a closure dossier (`References\Gaps Closure\New folder\urea_simulator_v1_1_final_closure_dossier_...html`)
that marks B-118, B-125, B-126, B-136 and data gaps 1, 3, 4, 5, 9, 10, 12, 14 and 15 closed. Every cited page was
opened: none of the 13 closures holds. Its Section B laws and stream values are in none of its cited files; gaps 1, 3, 9
and 10 are false on the image (322F001's p. 4 is a wall-thickness check; 324F002 prints 94 / 650 / 744 kg/h; F 335405
is 0-1 m3/h; B44 prints 3000 mm, not 3 600). Found on primary sources: PC21's SR latches are reset-dominant with the
inverted 21.2 flag on R (ABB DZ-0045-016 printed p. 407, AC4 p. 20), as built; Peroni's sheets give 3 barg and 152 RPM
for both 321P002 pumps. Row 5 narrowed to TRIP_84_8's L2; row 4 logs FF-0002's PT-324202 against AC4's PT-324203.
Nothing under `ureasim/` changed; no decision. Part CXLIII; renders `Tests and Reports\reports\Session_131_dossier`.

### Session 132 — 2026-11-18: V1.2; the separators' ejectors break on the plant's bracket

V1.2 copied from V1.1 at 5ddc107 (`D:\Work\Urea Simulator V1.2`, branch `v1.2`); V1.1 kept as it was. Asked to fix
two bugs: HV-329605 barely moved PIC-324202, PT-324201 and PT-323204, and HV-329606 barely moved PIC-324203 and
PT-324204. Built (decision 251): each separator ejector's P_c scale and break width put on the plant's 5 November
bracket (64 / 55 %, 40 / 38 %, PT-329207 4.22 bar g); the seed unchanged leaf for leaf. Measured: stage 1 at 0.345
bar a at 55 % and 0.430 at 45 %, stage 2 at 0.150 at 38 % and 0.265 at 35 %, softer than the plant's 0.6. The New
folder's other stand-ins have no Helwan source; 100847-100852 are another plant's drawings; none built. An
essentials zip went to Google Drive in five parts (its 10 MB upload limit). Part CXLIV; runs `Tests and Reports\reports\Session_132_ejector_break`.

### Session 133 — 2026-11-18: LY-324501 on its drawings; three leads checked; the Drive copy

On V1.2. The session 114 B-118 plan was handed to session 134. Read on the images: 324F003's assembly, sectional,
nozzle and calculation sheets and MB-0180; AC4's 885 mbar puts 100 % at the lower T/L, the leg holding 3.1 kg a
percent, 232 kg at the plant's 50 %, where V1's 3 797 kg holdup reads 104.2 %. A scratch arm reading the level on
that profile keeps no bit-identical seed (1.1e-4 on the level by 600 s) and answers a slug 20 times as far; the
AC4 formula on V1's level keeps the seed to the bit, its LRV floor (20.6 %) above the 5 % L2. Uhde's cooling water
lowers the vent and so does not explain stage 1's 0.6 bar a; PT-323204's three decimals are two decided edits; the
Bran + Luebbe pumps move FIC-335405 to 57 %, nothing else at design. The Drive parts were downloaded and joined to the
README's hash. Built on branch `v1.2-d252`: LY-324501 on AC4's formula over V1's level, the seed byte-identical at
600 s; a lost feed now drains 324F003 to its heel before the L2 stop can act, kept as built. Part CXLV; decision 252; runs
`Tests and Reports\reports\Session_133_ly324501`.

### Session 134 — 2026-11-19: B-118, B-125, B-126 and B-136 on session 114's plan, in scratch

A side session of 133, on V1.2's HEAD and session 112's tree, in scratch only. S on design references is the design
point to the bit at t = 0. S + B on UA as built settles at 92.3 % (TT-322005 181.5 C, every sign the plant's): it
stands D1 on session 112's tree; on HEAD its rise reads 12.03-12.18 K by window on the floor's 12.05 K. Book2's
322E002 UA exponent is 0.50 and rings at 92.3 %. No inert or liquid term carries the pressure's 3-6 bar; as a clamp
on plant data it settles UA as built at every reduced load by D2 (74.4 % by its rounding only), 7.3-9.8 K cold below
90.5 %; 111 % rings on every law. No hold at or below 90.5 % stands D1 or runs without a PC35 latch, so the 75 %
HIC-329605 probe stays deferred. B-136 (b) gives TT-322004 the plant's sign, 0.8-1.8 times its size; B-126 (b) needs a
display-resolution seed criterion; N6B shut leaves 0.866 of 322E001's area. 335P001 stops on LY-324501's L2 on every
reduced-load HEAD arm (A-61). On the merged tree (79fa8ca) it still stops at 69.3 %, after the seal is lost: the
rig's ten header valves draw 67.9 t/h on E1's 2.8 bar g floor against a 54 t/h make (CXLVI.19). No Helwan source
gives the plant's header-valve count per load: data gap 16 (CXLVI.20). Nothing built, no decision. Part CXLVI;
runs `Tests and Reports\reports\Session_134_b118`.

### Session 135 — 2026-11-19: the gap-closure session; the operator's header-valve rule on the B-118 rig

The Operating Manual's header-valve rule, read in bar g on E1's two ends, put on the rig in scratch: with a 300 s
dwell and no shedding while LY-324501 rises, 335P001 runs every 69.3 % and 92.3 % hold to its end, no PC35 latch, the
100 % seed to the bit; at 92.3 % S + B on UA as built then stands D1 on all five windows (margin 0.04 K) on tree252,
where without the rule 35.4 latches. Both 69.3 % arms fail the rule's own readings (a sixth valve off; hunting). Data
gaps 4, 5, 9, 10, 12 and 14 measured and prepared to close as built; [E] estimates on open literature for 1, 3 and 15;
D1's band is the seed's, the plant's rise measured 13.4-13.9 K. The decision packet, the Körting and Foxboro Eckardt
letters, the LV-324501A step test and the DCS readback checklist written. Decisions 253 to 257 proposed, none taken;
nothing under `ureasim/` changed. Part CXLVII; `Tests and Reports\reports\Session_135_gaps`.

### Session 136 — 2026-11-19: the process engineer's rulings recorded; 322R001 refitted to Book2; the Q2 matrix launched

The rulings on session 135's packet recorded as decisions 253 to 267, `handoff.md` rewritten on them, data gap rows 4,
5, 9, 12 and 14 deleted. score136 (decisions 259 to 262) re-scores waves H and H2: no arm stands D1; R923 reads 12.10 K
on the thermowells against Book2's 13.88 +/- 1.0 K, the seed itself 13.00 K. Book2's reductions never pass under
180.6 C. 322R001 refitted with law B meets Book2's flat rise at every anchor; the profile picks f 0.58, V1's own, the
licensor's 95 % misses by 2.9 K rms. The literature's ejector break gives 1.12 of the plant's 1.82: no build. The
44 mm bore confirmed as OD less two printed walls, unlabelled as the throat; gap 15's wet reading withdrawn on Book2. The T693b trace puts the 69.3 % feed step on
323D002 regaining suction (lost at 4 980 s with or without the rule): gap 16 closed, A-62 raised. Wave M's seventeen
arms left running, unscored. Decisions 268 to 273 proposed; nothing under `ureasim/` changed. Part CXLVIII;
`Tests and Reports\reports\Session_136_rulings`.
