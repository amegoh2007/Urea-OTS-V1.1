# Claude.md — Agent Directives for `Urea Simulator V1.1`

These directives are binding for **every** session in this workspace. Read them before touching
any file. They override habit, convenience and any "quicker way" that conflicts with them.

---

## 0. What this workspace is

`Urea Simulator V1.1` is a **ground-up rewrite** of the Urea Plant Operator Training Simulator
(OTS) that lives in `E:\Simulator\Urea Simulation` (read from its copy `D:\Work\Urea Simulation V1`,
decision 223; the V1 files the suite reads are copied into `tests/equivalence/v1_reference`, decision 210,
so V1.1 runs and tests without V1). The old project grew organically ("vibe coded"):
a 12,500-line `main.py` with a 4,100-line `step_sim()` function, five near-duplicate `main_*.py`
backups, ~40 `debug_*.py` scratch files, and a browser HMI in hand-written HTML/JS.

V1.1 keeps **100 % of the process engineering** and discards **100 % of the mess**.

| | Old (`Urea Simulation`) | New (`Urea Simulator V1.1`) |
|---|---|---|
| Language | Python 3 | Python 3 (unchanged) |
| UI | HTML + vanilla JS + WebSocket | **PyQt6** desktop client |
| Transport | FastAPI / WebSocket / JSON | length-prefixed JSON over TCP (`ureasim/net`) |
| Stations | any number of browsers, no roles | single local console (operator screens + instructor panel in one application) |
| Structure | one monolith + orphans | strict layered package `ureasim/` |
| Physics | correct, but buried | **identical equations**, extracted into named units |

**The physics is the asset. The code around it is not.** Never "improve", re-derive, re-tune or
re-anchor an equation during the rewrite. Port it exactly, then prove it ports exactly.

**Scope boundary (2026-10-08, `project.md` decision 73).** The simulated plant is urea units 321 to
329 and the parts of 335 V1 models. **320K002, the CO2 compressor, is outside it:** a fully
automated boundary feed (`units/synthesis/co2_compressor.py`) whose hardwired governor and surge
protection deliver the demanded CO2 into the discharge line at whatever pressure the line presents —
no curve, no speed, no surge, no faceplate and no operator command on the machine itself. The
battery-limit CO2 rate is the instructor's boundary condition (`co2_set`, on the instructor's panel);
322-1's CO2 FEED panel, V1's own hand station restored (2026-11-13, decision 220), steps the same
demand by 2 % of design (`co2_step`) and moves nothing else. Do not model
the machine's curves, its governor or its antisurge loop.

---

## 1. Coding standard — "neat engineer coded"

This is the house style. It is not negotiable.

1. **Modular.** One physical concept per module. A module that models two unit operations is
   two modules. Target ceiling: **600 lines per file**. Above 800 lines, split it — no exceptions
   without a written justification in `project.md`. A split moves its lines verbatim along a
   physical seam, the new module importing nothing from the one it left, and the module it left
   re-exports every public name it lost, so no caller changes an import (2026-10-23, session 70:
   every module under `ureasim/` at or below 600 lines). Before a split writes a module, check
   that no module of that name exists: an equipment tag's module may already hold part of its
   basis, and the split then goes into it.
2. **Layered, one direction.** Dependencies flow *downward* only:

   ```
   ureasim/hmi        (PyQt6 — presentation only, zero physics)
        │  ureasim/hmi/bridge.py  ──── TCP ────┐
        │                                      │
   ureasim/net        (station protocol + server — pure Python, NO Qt)
        │
   ureasim/engine     (integrator, scheduler, state container, historian — NO Qt)
        │
   ureasim/units      (unit operations: reactor, stripper, HPCC, ...)
        │
   ureasim/control    (PID / ratio / cascade blocks, valve actuators)
        │
   ureasim/core       (Stream, Node, flowsheet graph, units-of-measure)
        │
   ureasim/thermo     (property + VLE packages — no plant knowledge at all)
   ```

   An `import` that points *upward* is a defect. `thermo` must never know a reactor exists;
   `hmi` must never compute a bubble point. `ureasim/data`, rule 7's constants, sits beside the
   ranking between `control` and `units` (2026-11-11, decision 182): it may import `thermo`,
   `core` and `control`, and `thermo`, `core` and `control` read nothing from it, except
   `thermo/empirical.py`'s read of the leaf `data/design_point.py`. `tests/test_layering.py`
   enforces these directions and rule 3.
3. **The engine is headless. Nothing at or below `ureasim/net` may import Qt.**
   The simulator has a single local console (decision 149), and the engine still runs headless
   on its own physics thread behind a loopback server: physics stays strictly decoupled from
   presentation, and the `pytest` equivalence suites and the Phase 7 transient runners drive
   the engine with no display at all. A stray `from PyQt6 import ...` below the `hmi` layer
   breaks that separation and will not be noticed on a developer's laptop, where a display
   always exists.

   The check is one command:

   ```bash
   grep -rn "PyQt6" ureasim/net ureasim/engine ureasim/units ureasim/control ureasim/core ureasim/thermo
   ```

   It must print nothing.
4. **Separation of UI and physics is absolute.** The PyQt layer may only *read* a published
   state snapshot and *emit* operator commands, and both cross
   `ureasim/hmi/bridge.py`. If a widget calls a thermodynamic function, or opens its own
   socket, the design is wrong.
5. **Typed.** Public functions carry type hints. Dataclasses for state, not bare dicts, wherever
   the shape is fixed.
6. **Pure where possible.** Unit-operation solvers are functions of `(inputs, state) -> outputs`.
   Mutation lives in the engine, not in the physics.
7. **No magic numbers.** Every constant lives in `ureasim/data/` with a `source =` field naming
   the datasheet, PFD table or report it came from.
8. **Names are English words.** `carbamate_condenser`, not `hpcc2`. Tags (`322E002`, `LIC-323501`)
   are plant identifiers and stay verbatim.
9. **Dead code is deleted, not commented out.** Git is the history.
10. **The physics step is fixed at 0.1 s.** The engine advances the plant in whole steps of
    exactly 0.1 s — V1's `DT`, the step of its design pin and of every equivalence test.
    Pacing (SLOW, FAST, a loaded machine) changes how many steps run per wall-clock second,
    never the size of a step. Every recycle tear carries one step of delay, so a variable
    step would make every transient depend on machine load and no exercise would replay.
    Decided 2026-09-27 (handoff A-14, `project.md` decision 9).

## 2. Commenting standard

Every module opens with a docstring stating: what plant equipment it models, which reference
document it is sourced from, and which equations it implements.

Every thermodynamic relation and every function carries a comment explaining **its process
utility** — what it is *for* on the plant, not what the Python does:

```python
def bubble_T_raoult(P_bara: float, w: dict) -> float:
    """Bubble point of an NH3-CO2-H2O liquor by modified Raoult's law.

    Process utility
    ---------------
    Fixes the temperature at which a recirculation stage starts to flash. The LP
    recirculation heaters are rated on approach to this temperature: too close and the
    downstream pump cavitates (NPSH collapse), too far and the carbamate does not
    decompose, so ammonia carries to the evaporator.

    Equation
    --------
        P = sum_i (x_i * gamma_i * Psat_i(T))        [Raoult, activity-corrected]
    solved for T by bisection on [T_lo, T_hi].

    Source: References/Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md, stage table.
    """
```

Comment density matches the physics density: a solver loop gets a comment per algebraic step;
a Qt layout method gets none.

## 3. Standing operational rules

* **ALWAYS use the caveman skill.** Invoke `Skill(caveman)` at session start, level `full`.
  Chat replies stay compressed. **Persisted artefacts — source code, code comments, the four
  Markdown documents, commit messages — are written in normal professional English.** Caveman is
  a chat register, never a documentation register.
* **ALWAYS use the claude-mem skill (2026-10-22).** At session start, and before re-deriving any
  earlier session's work, search claude-mem's cross-session memory (`Skill(claude-mem:mem-search)`)
  for what is already known — a measurement, a decision, a dead end. It complements the four living
  documents and never replaces them; claude-mem's skills that fan work out to sub-agents
  (`claude-mem:do`, `claude-mem:build`) stay excluded by the no-sub-agents rule below.
* **ALWAYS update the four living documents** — `project.md`, `handoff.md`,
  `Urea OTS — As-Built Mathematical Reference.md` and this file when its rules change —
  each fact once, in the home §3a gives it, whenever any of the following happens:
  - a significant change lands,
  - a milestone in `project.md` flips state,
  - an equation is ported, altered or found to disagree with the original,
  - **before ending a coding session, unconditionally.**
* **Do not use sub-agents / multi-agent fan-out.** Carried over from the V1 directives. Work
  inline, in this session, with this context.
* **Finalize before the context runs out (2026-10-09).** Always finalize the session — the four
  documents updated, the checks run, and the final report of §7 printed — before the
  conversation's context limit is reached; then compact. Never let a compaction cut a session off
  with its documents or its report unwritten. The auto-compact window is set to 400k tokens
  (2026-11-11, the process engineer's `/autocompact 400k`).
* **Surgical edits.** Change the lines that must change. Do not reformat a file you are visiting.
* **Rebuild the thermodynamic node stores after any thermo change** (2026-10-03, handoff A-18):
  ``python tools/build_liquid_state_store.py``. A changed parameter or solver makes the stores
  stale; a stale store is ignored, never wrong, and the simulator falls back to tabulating the
  Extended UNIQUAC grids during transients, which stalls it for seconds a tick.
* **One unit at a time.** Port, comment, test and document a single unit operation before
  starting the next. A half-ported flowsheet is worse than an unported one.

## 3a. Document map and reading budget (2026-11-11)

The documents are written to be cheap to read. Before session 96 a session start read 165 000 tokens
of history; it now reads the state. These rules keep it so, and they bind as the rest of this file.

| Document | Holds | How it is read |
|---|---|---|
| `project.md` | the state now, the scope, the next free numbers | whole, at session start; ceiling 150 lines |
| `handoff.md` | the open items and open data gaps, each as its current state | whole, at session start; ceiling 300 lines |
| `Urea OTS — As-Built Mathematical Reference.md` | every equation, measurement and closure; one Part a session | never whole: grep a heading, read that section |
| `docs/decisions.md` | the numbered decisions; "`project.md` decision N" means entry N there | never whole: `grep -n "^N\. "` |
| `docs/decided-classes.md` | §5 rule 7's classes | grep for the mechanism before a unit's physics changes |
| `docs/architecture.md` | the layers, the HMI, the single console, the scheduler | when a change touches the architecture |
| `docs/history/session-log.md` | one entry a session | append-only; `grep -n "^### Session"` |
| `docs/history/phase-checklist.md`, `docs/history/handoff-record-to-session-95.md` | the completed checklist; the tracker's history, B-118's chronicle, the data gaps' search records | frozen; grep before a search or a measurement is repeated |

1. **One fact, one home.** An equation, a measurement, a closure: the session's As-Built Part. An
   open item: `handoff.md`. A decision: one numbered entry in `docs/decisions.md`. Every other
   document cites it (`As-Built §CVII.4`, `decision 181`) and never restates it.
2. **State, not history.** `project.md`'s State block and a `handoff.md` item are rewritten in place.
   No session paragraph is appended to either, and "Last updated" is a date and a session number.
3. **A `handoff.md` item** holds its problem, its acceptance tests, what is established (a line each,
   with its As-Built section), what is ruled out, the open options and the next step: at most 80
   lines. A data-gap row holds the datum, its consumer, the stand-in as built, what is found and the
   route to close. A closed item is deleted, and no list of closed items is kept.
4. **A session-log entry** is at most 12 lines: the date, what was decided, built and measured, and
   the Part and the decisions that hold it.
5. **Read by grep.** Grep, then read the section, never the file. Send a long run's output to a file
   in the scratchpad and read its tail. Do not print a document to check an edit.
6. **A document over its ceiling** is cut back in the same session: the excess is history, and it is
   already in the As-Built Part it cites.

## 4. CRITICAL — technical data sourcing

**Never invent a chemical property, dimension, duty, set point or design flow.**

**Mandatory search for plant data and references (2026-10-01).** For every plant datum and every
reference — a dimension, a duty, a set point, a span, a vendor rating, a trend, a licensor chart —
always search `D:\Work\Urea Simulation Docs\References\` **and every one of its subfolders**
(`Sources\`, `Datasheets\`, `DCS Trends\`, `Gaps Closure\` and any other), not only the files
named below, and **then** invoke the `/soft-copy-search` skill on the vendor archive. Both
searches are made every time, in that order, before a datum is taken from V1 or logged as a gap;
when `References\` already holds the datum, the archive search is its cross-check. The archive
was moved there from `D:\Work\Urea Simulation\References\` on 2026-11-04; earlier records cite
the old path.

Resolution order for any datum:

1. `D:\Work\Urea Simulation Docs\References\` — primary archive. In particular:
   - `Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md` — **the strict design basis**
     (stream table, 100 % load, 1750 MTPD). Anchor every design point here.
   - `Combined_1925_MTPD_100% load_PFD TablesProcess_Data.md` — alternate load case.
   - `References\Datasheets\` — equipment database: dimensions, nozzle elevations, instrument
     positions, tube counts, areas, materials.
   - `References\DCS Trends\` — measured plant behaviour for dynamic validation.
   - `References\Gaps Closure\` — closure memos for previously-open modelling gaps.
2. `skill: soft-copy-search` — the Helwan Fertilizers Company vendor-document archive. Use it
   when the datum is equipment-specific and not in `References\`.
3. The V1 source: `tests/equivalence/v1_reference/`, V1's files the suite reads in V1's own layout
   (decision 210),
   and for any other file `D:\Work\Urea Simulation V1\backend\` (E:'s tree, copied; decision 223) —
   acceptable **only** for values that V1
   itself back-solved or anchored. When you take one, copy its provenance comment with it.

If none of the three yields the datum: **stop, do not guess, log it in `handoff.md` §Open Data
Gaps** and proceed with the rest of the work.

## 4a. Console-engine boundary rules

The simulator is **one plant with a single local console** (2026-10-22, `project.md`
decision 149): `python run.py` (or `launch.bat`) starts the headless engine on the loopback
interface and the console attached to it over `ureasim/hmi/bridge.py`. Behind the start-up intro the
plant is held at its design seed until the operator presses 100% LOAD (2026-11-04, `project.md`
decision 166; `--no-intro` runs it from the start), or presses LOAD, which restores a saved exercise
the operator chooses from the engine's list before the same release (2026-11-06, decision 171; the
list is the instructor's folder, `UREASIM_EXERCISES` or `~/ureasim-exercises`, which SAVE writes, and
the repository's shipped `scenarios`, which nothing writes, so training saves stay out of the tree). A plant
reset or restored while frozen publishes its rehearsed first tick, the plant unstepped (2026-11-04,
decision 169), so a held console is never blank; an engine that has stopped publishing is never shown as
live: the server replays no packet older than `data.engine.SNAPSHOT_REPLAY_MAX_AGE_S` to a console that
connects, and says the engine is silent (2026-11-06, decision 172).
Three rules follow, and
none of them is optional:

1. **The engine owns the plant; a console owns nothing.** A console renders the snapshot it
   is sent and emits commands. It never computes, caches or corrects a value. A console
   showing a number the engine did not publish for a tag is a defect by construction. The one
   decided exception (2026-11-11, decision 183): a faceplate shows a pressure in bar g and sends
   its set point in bar a, converting on `core.units_of_measure`'s atmosphere, the engine's own.
2. **The engine enforces the process; the console separates plant operation from instructor
   controls in the UI.** The operator mimics and faceplates expose only what the plant DCS
   exposes — exactly what V1's operator screens allowed; re-classifying a plant control would
   change what a trainee is being taught, which §5 forbids. The controls that are not plant
   equipment — malfunctions, pacing, freeze, reset, exercise save and restore, the
   battery-limit `co2_set`, and a field operator's move the DCS has no handle for (322P002's
   delivery set by hand at FI-322402, `p002_delivery_set`; 2026-11-15, decision 212) — live in
   the Instructor menu's panel. The exceptions are the
   start-up intro's LOAD button, an exercise restore before the plant first runs, at the process
   engineer's explicit request of 2026-11-05 (decision 171), and 322-1's CO2 FEED panel, V1's own
   hand station restored, which steps the battery-limit demand by 2 % of design (`co2_step`;
   2026-11-13, decision 220) while `co2_set` stays on the panel. No command is refused for who
   sent it; whether the plant will *accept* it — a latched trip, an interlock, a closed valve —
   is the engine's answer, and it travels back to the console's status bar with its process
   reason. Station roles, the station token, the roster and unit assignment by section were the
   multi-station deployment's (decisions 72, 124 and 125) and are retired.
3. **Faceplates and the instructor's panel are dumb (2026-10-03).** Everything under
   `ureasim/hmi/faceplates/` and `ureasim/hmi/instructor/`, and the intro's exercise chooser
   (`ureasim/hmi/exercise_chooser.py`, decision 171: the engine's names, no file read), renders
   what the engine published and emits commands over the bridge, nothing else: no new logic, no
   local state, no decision the server or the engine owns. Which command a control sends is data
   (`ureasim/data/faceplates.py`), pinned by a test to the engine handler that takes it.
   **The trend window plots the engine historian and keeps no samples (2026-10-03).**
   `ureasim/hmi/trend/` asks for its whole visible window over the protocol and repaints the
   answer; it never accumulates packet values of its own. What it keeps is its view — the pens,
   the span, the ranges — not process data. **The stream inspector renders the packet's
   ``STREAMS`` record and computes nothing (2026-10-07)** (`ureasim/hmi/widgets/stream_hotspot.py`).

## 5. Fidelity rules for the port

1. **Equation identity.** A ported relation must be algebraically identical to V1's. Same
   correlation, same coefficients, same anchoring, same clamps, same units.
2. **Anchoring is part of the equation.** V1 pins many correlations to a design point so the
   PFD is reproduced by construction. That pin is physics, not a fudge — port it, and port the
   comment that explains it.
3. **Provenance travels with the number.** If V1 says a coefficient was back-solved from
   PFD table 3, the new code says so too.
4. **Port, then prove.** Every ported unit gets a regression test in `tests/` that drives the
   V1 module and the V1.1 module with the same inputs and asserts agreement to tolerance.
   Record the tolerance actually achieved in the As-Built reference. A test reaches V1 only through
   `tests/equivalence/v1_loader.py`: `load("reactor")` (or `lift(...)`), never a bare
   `import reactor` — V1's backend is appended to `sys.path`, so a bare V1 name is ambiguous and
   could let a V1 module satisfy a V1.1 import (handoff A-3, closed). The loader reads the in-tree
   copy `tests/equivalence/v1_reference` (decision 210); a test that needs another V1 file copies it
   there byte for byte and adds its row to `MANIFEST.sha256`, and never points at a path outside.
5. **Do not silently widen a clamp.** V1's limiters encode real operating envelopes.
6. **A decided divergence is the only exception, and never the rewrite's own call.** When the
   process engineer decides a handoff item in favour of NOT reproducing V1, make the change.
   Then the equivalence test asserts both sides — what V1 does and what the rewrite does
   instead. The As-Built register row names the divergence and the date of the decision, and
   the handoff item is deleted.
7. **A decided class applies to every new unit (2026-09-30).** Once the process engineer has
   decided a class of V1 flaw, apply it without re-asking wherever a new unit shows it. The classes,
   103 of them, one a line with its decision number, are in `docs/decided-classes.md` and are binding
   (moved there 2026-11-11, wording unchanged). Before a unit's physics is ported or changed, grep
   that file for the mechanism and for the equipment's kind; never read it whole. A class decided
   later is appended there as one line. A new mechanism still goes to the process engineer, with
   both sides measured.

## 6. Clean-codebase rules

* No file enters this tree unless it is part of the product, its tests, or its documentation.
* No `debug_*.py`, no `*_backup.py`, no `*_orig.py`, no `tmp_*`, no scratch output.
* Scratch work goes to the session scratchpad directory, never to the project.
* No asset is copied from V1 unless a screen actually renders it. The one exception is
  `tests/equivalence/v1_reference` (decision 210): the V1 files the suite reads, byte for byte,
  `-text` in `.gitattributes`, never edited.
* `tests/` mirrors `ureasim/` one-to-one. A module with no test is an open item in `handoff.md`.

## 7. Session checklist

Start:
1. Invoke `Skill(caveman)` at `full`.
2. Read `project.md` (state) and `handoff.md` (open items), whole. Read nothing else until the
   task names it (§3a).
3. Search claude-mem (`Skill(claude-mem:mem-search)`) for the history of the items the session
   takes up.

End (mandatory):
1. Update `project.md`: the State block and the Next free numbers, rewritten in place. Append the
   session's entry to `docs/history/session-log.md`, and each decision taken to `docs/decisions.md`.
2. Update `handoff.md` — rewrite the state of each item touched, add new gaps, **delete closed ones**.
3. Update `Urea OTS — As-Built Mathematical Reference.md`: one new Part for every equation touched
   and every measurement made.
4. State plainly what was finished, what was not, and why.
5. List all open gaps in the final report (mandatory, 2026-10-03): every open `handoff.md` item
   and open data gap, each with its status in a line, not only those the session touched.

## Advisor Workflow (Opus + Fable, Sonnet + Opus)

A session whose main model is any version of Claude Opus (binding from 2026-11-12, the process
engineer's instruction) or of Claude Sonnet (binding from 2026-11-04) operates in hybrid mode with a
stronger model through the `advisor` tool, at matching effort and ultracode standards. A session run
on Fable works as the rest of this file says.

| Main model | Advisor | How it is set |
|---|---|---|
| Claude Opus | Claude Fable | `"advisorModel": "fable"` in `.claude/settings.json`, the project's default |
| Claude Sonnet | Claude Opus | for that session: `claude --advisor opus`, or `/advisor opus` |

The advisor is a server-side tool, not a sub-agent: §3's rule against sub-agents does not exclude it.
It reads the whole transcript anew on every call, so it is called at the stages below and at a
blocker, never between routine steps. Before Stage 2, confirm that the `advisor` tool is offered and
which model answers (`/advisor` prints it). Where it is not offered — Fable access or its
usage-credits consent missing (`/model fable` gives it), or the pairing refused — stop and tell the
process engineer; do not work on without it.

1. **Stage 1 — Ingestion (the main model only).** Read and parse all required documents, source
   files, images and media first. Never call the `advisor` tool before gathering context.
2. **Stage 2 — Thinking & planning (the advisor).** Before writing or editing any code, call the
   `advisor` tool (it takes no arguments) so the advisor analyzes the context in the transcript and
   produces the architecture and step-by-step plan.
3. **Stage 3 — Execution (the main model only).** Implement the advisor's plan strictly. If a
   blocker contradicts the plan, call the `advisor` tool again before deviating.
4. **Stage 4 — Testing & verification (the advisor).** When testing is required, run the test
   commands on the main model and call the `advisor` tool afterward so the advisor audits the test
   output and verifies edge-case coverage before marking the task complete.
