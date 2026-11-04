# Claude.md — Agent Directives for `Urea Simulator V1.1`

These directives are binding for **every** session in this workspace. Read them before touching
any file. They override habit, convenience and any "quicker way" that conflicts with them.

---

## 0. What this workspace is

`Urea Simulator V1.1` is a **ground-up rewrite** of the Urea Plant Operator Training Simulator
(OTS) that lives in `D:\Work\Urea Simulation`. The old project grew organically ("vibe coded"):
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
no curve, no speed, no surge, no operator command and no faceplate. The battery-limit CO2 rate is the
instructor's boundary condition (`co2_set`, on the instructor's panel), never a process screen's
control. Do not model
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
   `hmi` must never compute a bubble point.
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
  whenever any of the following happens:
  - a significant change lands,
  - a milestone in `project.md` flips state,
  - an equation is ported, altered or found to disagree with the original,
  - **before ending a coding session, unconditionally.**
* **Do not use sub-agents / multi-agent fan-out.** Carried over from the V1 directives. Work
  inline, in this session, with this context.
* **Finalize before the context runs out (2026-10-09).** Always finalize the session — the four
  documents updated, the checks run, and the final report of §7 printed — before the
  conversation's context limit is reached; then compact. Never let a compaction cut a session off
  with its documents or its report unwritten.
* **Surgical edits.** Change the lines that must change. Do not reformat a file you are visiting.
* **Rebuild the thermodynamic node stores after any thermo change** (2026-10-03, handoff A-18):
  ``python tools/build_liquid_state_store.py``. A changed parameter or solver makes the stores
  stale; a stale store is ignored, never wrong, and the simulator falls back to tabulating the
  Extended UNIQUAC grids during transients, which stalls it for seconds a tick.
* **One unit at a time.** Port, comment, test and document a single unit operation before
  starting the next. A half-ported flowsheet is worse than an unported one.

## 4. CRITICAL — technical data sourcing

**Never invent a chemical property, dimension, duty, set point or design flow.**

**Mandatory search for plant data and references (2026-10-01).** For every plant datum and every
reference — a dimension, a duty, a set point, a span, a vendor rating, a trend, a licensor chart —
always search `D:\Work\Urea Simulation\References\` **and every one of its subfolders**
(`Sources\`, `Datasheets\`, `DCS Trends\`, `Gaps Closure\` and any other), not only the files
named below, and **then** invoke the `/soft-copy-search` skill on the vendor archive. Both
searches are made every time, in that order, before a datum is taken from V1 or logged as a gap;
when `References\` already holds the datum, the archive search is its cross-check.

Resolution order for any datum:

1. `D:\Work\Urea Simulation\References\` — primary archive. In particular:
   - `Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md` — **the strict design basis**
     (stream table, 100 % load, 1750 MTPD). Anchor every design point here.
   - `Combined_1925_MTPD_100% load_PFD TablesProcess_Data.md` — alternate load case.
   - `References\Datasheets\` — equipment database: dimensions, nozzle elevations, instrument
     positions, tube counts, areas, materials.
   - `References\DCS Trends\` — measured plant behaviour for dynamic validation.
   - `References\Gaps Closure\` — closure memos for previously-open modelling gaps.
2. `skill: soft-copy-search` — the Helwan Fertilizers Company vendor-document archive. Use it
   when the datum is equipment-specific and not in `References\`.
3. The V1 source, `D:\Work\Urea Simulation\backend\` — acceptable **only** for values that V1
   itself back-solved or anchored. When you take one, copy its provenance comment with it.

If none of the three yields the datum: **stop, do not guess, log it in `handoff.md` §Open Data
Gaps** and proceed with the rest of the work.

## 4a. Console-engine boundary rules

The simulator is **one plant with a single local console** (2026-10-22, `project.md`
decision 149): `python run.py` (or `launch.bat`) starts the headless engine on the loopback
interface and the console attached to it over `ureasim/hmi/bridge.py`. Three rules follow, and
none of them is optional:

1. **The engine owns the plant; a console owns nothing.** A console renders the snapshot it
   is sent and emits commands. It never computes, caches or corrects a value. A console
   showing a number the engine did not publish for a tag is a defect by construction.
2. **The engine enforces the process; the console separates plant operation from instructor
   controls in the UI.** The operator mimics and faceplates expose only what the plant DCS
   exposes — exactly what V1's operator screens allowed; re-classifying a plant control would
   change what a trainee is being taught, which §5 forbids. The controls that are not plant
   equipment — malfunctions, pacing, freeze, reset, exercise save and restore, and the
   battery-limit `co2_set` — live in the Instructor menu's panel. No command is refused for who
   sent it; whether the plant will *accept* it — a latched trip, an interlock, a closed valve —
   is the engine's answer, and it travels back to the console's status bar with its process
   reason. Station roles, the station token, the roster and unit assignment by section were the
   multi-station deployment's (decisions 72, 124 and 125) and are retired.
3. **Faceplates and the instructor's panel are dumb (2026-10-03).** Everything under
   `ureasim/hmi/faceplates/` and `ureasim/hmi/instructor/` renders the published packet and
   emits commands over the bridge, nothing else: no new logic, no local state, no decision
   the server or the engine owns. Which command a control sends is data
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
   could let a V1 module satisfy a V1.1 import (handoff A-3, closed).
5. **Do not silently widen a clamp.** V1's limiters encode real operating envelopes.
6. **A decided divergence is the only exception, and never the rewrite's own call.** When the
   process engineer decides a handoff item in favour of NOT reproducing V1, make the change.
   Then the equivalence test asserts both sides — what V1 does and what the rewrite does
   instead. The As-Built register row names the divergence and the date of the decision, and
   the handoff item is deleted.
7. **A decided class applies to every new unit (2026-09-30).** Once the process engineer has
   decided a class of V1 flaw, apply it without re-asking wherever a new unit shows it: a pump
   capped at its vessel's heel, a full vessel's excess published as an overflow, a transmitter
   reading the delivered flow (decision 11); a fixed-effectiveness exchanger's feed taking only
   what the hot side gave (decision 14); a loop gain read per cent of its transmitter's span, a
   cascade master's output onto its slave's span, and no scale V1 derived to hold an
   engineering-unit loop gain (decisions 10, 21); a design differential written as a subtraction
   of two design pressures (A-13; closed 2026-10-16, `tests/engine/test_check_valve_audit.py` enforces
   it); a heater's chest on its datasheet's pressure (decision 20); a
   control valve on its vendor's trim, its design stroke where its rated capacity passes the design
   flow (decision 23); a column's negative net duty condensing vapour, not clamped (decision 15); a
   liquid losing, and paying the latent heat of, what boils, not what its overhead passes (decision
   24); a cooler's stroke-proportional duty held to what brings its process to the coolant's
   temperature (decision 28); a vent or overhead line discharging against its receiver's live
   pressure, not a design constant (decision 29); a loop with no table row keeping V1's own
   tuning, logged in handoff Section C (B-52) — unless V1's tuning is measured unstable, when
   decision 22 gave TIC-323012 its sibling's row; a control structure the P&ID and a functional
   diagram both draw and V1 did not build —
   a ratio station, a level master over a flow slave — wired as drawn, once measured stable on the
   model (decisions 26, 27; B-48 was kept as V1 because V1's measurement runs it away); a letdown
   handed its liquor's live vapour pressure, at most its inlet pressure, so it chokes where its
   downstream condition warrants it (decision 31); a node relieving through its certified safety
   valves — pop action at set, the vendor's blowdown, API 520 on the certified capacity, in
   `core/relief.py` (decision 32); a liquid-rated safety valve on a vapour node relieving on its
   orifice's own area at the full-lift gas coefficient Sempell prints for that orifice in gas service,
   0.922 for F, K and M, and the gas blowdown (decision 34, 2026-10-01; the coefficient read
   2026-10-16, decision 130); a vessel's volume with its heads, and a
   level read between its transmitter's taps (decision 33); an exchanger V1 replaced with a fixed
   outlet temperature ported on its datasheet UA, its coolant at the supply temperature and the
   flow no document fixes back-solved so the design point holds (decision 36); a utility a trip
   admits put where the P&ID injects it, as the stream that carries its heat, and the trip on the
   instrument where the P&ID draws it (decision 37); a gas letdown below its dew point flashed
   onto the liquor it condenses, V1's single-phase answer kept for a dry gas (decision 38); an
   interlock built as Uhde's DCS application software executes it, with no latch or reset its logic
   does not draw and its hand switches as the loop summaries type them (decision 39), and no operator
   command on the console the DCS does not have — a generated screen changed only through the
   converter's `DECIDED_EDITS` (decision 40); a utility a valve admits at its loop summary's rated
   flow, where V1 back-calculated a duty (decision 41); a melt's strength capped at what its
   non-volatiles leave (decision 42); an equipment curve the archive lacks synthesized by its 1-D
   model on the vendor's geometry, its capacity anchored on the PFD's design load and the vendor's
   duty kept as margin (decisions 43, 44); a chest-heated vessel's held liquor boiling past its own
   boiling point at its live vacuum — on the melt's equilibrium in an evaporator separator, on the
   bubble point of its whole composition in the pre-evaporator — the excess sensible heat paid as
   latent heat, evaluated inside the vacuum's implicit step (decisions 45, 48); a stage fed by
   another's barometric leg taking the strength the leg drains, anchored on the design (decision
   46); a flowsheet stream on the PFD's material balance where a vendor rating differs, the
   vendor's figure kept inside its equipment's own model (decision 47); a condenser cold end a
   vacuum balance reads lagged on its tube-side water residence, tau = V_tubes / Q_cw on the
   datasheet's tubes and the PFD's water, not handed over a bare one-tick tear (decision 49); a
   condenser shell between two ejectors a live vacuum node on its name plate's volume, its upstream
   ejector discharging against it and bounded by the next shell's pressure, not a design constant
   (decision 50); a design-anchored partial pressure's departure added to the design partial
   pressure, floored at zero, not multiplied into it, where its design back-pressure is at most that
   partial pressure, and V1's ratio kept where it is above (decisions 51, 55); every simulated steam user's live
   draw on its header, the users the simulator does not model constant at their PFD rows, each unit's
   draw its live ratio on its PFD row where its own model's design differs (decisions 52, 47); a
   superheated steam inlet boiling its drum's own water, a saturated condensate let down flashing
   into its receiver, a blowdown leaving its drum's water, and no floor holding a header up
   (decision 54); a steam user on its valve against its header's live pressure, anchored on the
   header's design, a choked nozzle's pressure solved on the flow its valve passes (decision 56); a
   steam drum feeding its header through the PFD's stream, a letdown joining the header downstream of
   the drums carrying its superheat to the header's users and boiling no drum water, a shell boiling
   its drums' water at their saturation (decision 58); a design credit that mirrors a load-scaled
   deduction scaled by the same load (decision 59); mass a model holds back, recondenses or pulses
   kept in a physical inventory — a backlog's recondensate returned to the condensate it left, a full
   sump's excess held back in the vessel draining into it, a throttle on a vessel's outflow so what it
   holds back stays, a pulse drawn from the vessel that supplies it (decisions 60, 62); a
   liquor line delivering
   its live flow and delaying only the liquor's temperature and composition (handoff B-21); a gas
   node's volume taking every vessel open to its gas space (decision 68); two saturating rises that
   describe one end state sharing one ceiling (decision 69); a published instrument pinned on the PFD's
   and the plant's value where V1 pinned a model pseudo-quantity, the pseudo-quantity kept inside its
   own unit (decision 70); one atmosphere, 1.01325 bar, and one gravity, 9.80665 m/s2, in every
   relation and display, a relief valve keeping the atmosphere its sheet states (decision 71); a machine
   outside the simulation's scope a boundary that delivers what the process asks of it, with no curve,
   speed or operator lever (decision 73); a line's dead time on its isometrics' as-built straight pipe
   and elbow arcs, each size at its own bore, where V1 estimated a run (decision 74); a known
   continuous inflow — a restriction orifice's rated steam — put where its P&ID ties it in, and taken
   out of the PFD row that carries it (decision 75); a loop with a row in the plant DCS's tuning table
   (`References/Master_PID_Tuning_Constants.md`, checked on its faceplate photograph) on that row, its
   derivative and filter included, its gain read onto the PV the model carries (decisions 76, 77); a
   vapour-space pressure whose explicit step would ring — dt . df/dP below -1 on its own
   linearisation — taking the backward step on that tick, its outflow at the pressure it settles on,
   V1's explicit step kept to the bit elsewhere (`core.node.stable_pressure_step`, decision 78); a
   condenser's vent never negative, every species it carries and the inerts that size it floored at
   zero, so it condenses no more than it receives (decision 80); a flow loop on the stream every
   plant source puts it on, a draw with no control valve on its P&ID at its pump's PFD delivery, and
   a level only open-loop transmitters read left to the operator (decision 81); a held liquor whose
   boiling point lies below its equilibrium model's window not boiling, its stage on V1's closure
   (decision 82); a trip that isolates a boundary machine's delivery taking that boundary's demand to
   zero, a demand refused while it is latched (decision 83); a generated screen's geometry changed
   only through the converter's ``NUDGE`` rows, zero overlap on every screen (decision 84); no gate
   that freezes a unit's physics at its operating point (decision 86); an equipment leak flowing
   from the high-pressure side into the low on its live differential, its mass and heat booked on
   both sides (decision 87); a malfunction's consequence shown on the instrument the plant's DCS
   reads it on, published in a port block when V1's packet has no key (decision 89); a line
   downstream of a letdown holding the valve's design flash at the homogeneous two-phase density,
   the valve's place on its line read from the isometrics (decision 91); a ratio controller the
   functional diagram draws, trimming its slave, built as drawn with its balance tracking (decision
   92, decisions 26 and 27's class); no loop with the DCS table's deadband, the model having no
   measurement noise (decision 93); no reaction a design point cannot anchor, its omission recorded
   (decision 94); a vapour node's capacity its vessels' free volume on the gas law at the PFD's
   density with its liquors' buffering read once off the design's solubility, a holdup's gain over
   its own step liquid, not pressure (decision 95); an interlock ported from Uhde's application
   software as drawn, its flags live with no reset the logic does not draw, a limit the archive
   lacks a logged stand-in (decision 96); a condensing unit's liquor holding no more gas than its
   bubble point at the live loop pressure allows, on the saturation fraction of its deficit (decision
   97); a console element V1's screens lack added only through the converter's `DECIDED_ADDITIONS`
   (decision 98); a stream V1 books into nothing taken into the unit its loop summary names (decision
   100); a non-volatile a PFD row's rounding leaves unaccounted closed on the drain, water giving way
   (decision 101); a held liquor's node at most at its bubble point at the live pressure, the excess
   heat flashing its volatiles, and a kinetics' residence on the liquid passing, not on the outflow
   alone (decision 102); a value the process engineer reads back from the plant DCS the datum where
   the archive is silent, applied on the PV the model carries (decision 103); a stream a PFD unit's
   balance closes without entering as its departure from its PFD row, zero at design (decision 104);
   a condensing unit's liquor held to its own bubble pressure, and a full sump condensing no more than
   drains from it (decision 105); a vendor sheet that prints its capacity at its cases' travels and
   names no curve run on its printed points (decision 108); an interlock's analogue limit the archive
   gives no hysteresis carrying a stated 2-unit stand-in (decision 111); a dry gas above a solid's
   saturation laying the solid down, its heat paid and the deposit carried to its receiver
   (decision 112); a condenser's capacity on its dew point against its coolant, anchored on V1's
   constant at the design node and not capped at the gas that arrives, its vent passing nothing below
   its receiver's pressure (decision 114); a held liquor relaxing to its bubble point at its
   separator's live pressure (decision 115); a vendor sheet that prints no density carrying
   IAPWS-IF97's at its rating temperature (decision 116); an inlet charged at its producer's live
   temperature as its departure from the producer's design, T_in,des + (T_producer - T_producer,des),
   read the same tick where the producer steps first and a tick late where it steps after, a utility
   with no circuit kept at its design (decision 118); a mixing point no unit computes a temperature
   for — an ejector's discharge — on its adiabatic first law at its receiver's pressure, its water
   condensing below its dew point, as its departure from the design mix (decision 121); a V1 cascade
   its step_sim builds and calls with its permissive forced, run on the live permissive and seeded at
   its fixed point on the plant's design (decision 123); a liquor stage's species step taking what
   it drains and boils off at the step's end composition where its outflows pass more on the tick
   than it holds (decisions 133, 137, decision 78's class); a saturation fraction and the bubble
   pressure it sets solved together on the tick, not across it (decision 135); a cooler's
   condensation capacity on its shell's effectiveness at the live coolant flow, its duty capped at it
   (decision 136); a heater's duty bounded by what its shell transfers at the live utility's LMTD
   against the process side's design profile, on its design duty's anchor, the lift it cannot pay for
   left in the product and a band holding the design seed's own drift unbound (decision 139); a
   held-back inventory capped at what the vessel holding it holds full, the vessel upstream keeping
   the rest and discharging no more than the full one passes, and a heat-transfer surface standing
   submerged derated linearly to its flooded-surface floor, its product cooling by the same factor
   (decision 140, decision 62's class); a liquor stage V1 runs mass-only carrying its species as its
   departure from its PFD row, each inlet at its own row, its consumer on the live composition and
   temperature a line residence late on its line's isometrics (decisions 141, 146); a melt's
   bubble-pressure law below its azeotrope following the Extended UNIQUAC model's rise, added in bar
   as its departure from the branch, not multiplied onto the design pressure (decisions 142, 147,
   decision 51's class); a vacuum vessel's lost liquid seal admitting atmospheric air through its
   drain's trim on the blow-through law (decision 143); a stage's coupled temperature-pressure
   iteration that does not settle solved for its temperature on its own energy balance by a
   bracketed root, V1's iteration kept to the bit wherever it converges (decision 144, decision 78's
   class); an instrument that reads a liquor's bubble pressure capped at the pressure the liquor
   stands at where it flashes, the threshold its own saturation fraction uses (decision 145); a
   published reading with no transmitter of its own on its PFD's design pressure, its line's design
   differential the subtraction of the PFD's two design pressures and its flow and density factors
   normalised on the design seed, where V1 wrote the differential on the live loop pressure
   (decision 148, decision 70's and A-13's classes); a vendor sheet sized on a density that is not
   its fluid's taken to the fluid's density, a trim passing m = Kv sqrt(rho dP) — the Kv a mass flow
   needs scaling as m / sqrt(rho), the mass a stroke passes as sqrt(rho) (decision 150, decision
   23's class); an exchanger whose coolant flow a PFD fixes running on that flow, its UA
   back-solved so the design point holds and the datasheet's kept as margin (decision 151, decision
   36's class); a unit replaced at a turnaround run on the replacement's own drawings and process
   datasheet — its limits, holdups and capacity — the PFD still the flowsheet's anchor and the
   equipment V1 models kept on every harness's switch (decision 154); an exchanger with plugged tubes
   keeping its tube counts and active surface and its plugged bores out of its process volume, its
   conductance re-anchored on the bundle in service so the PFD's design point holds by construction,
   the clean bundle on the harnesses' switch (decisions 155, 157); a photograph of the plant DCS's
   faceplate a tuning-table row, a range and a limit as decisions 76, 77 and 103 take them (decision
   156); an event shorter than a survey's sample — a safety valve's lift — read on its peak between
   samples, and a premise checked in the code before a relation is changed for it (decision 158); a
   trend taken at another load not moving the 1750 MTPD design basis (decision 159); a faceplate's
   gain on a PV the model carries in other units taken through their local slope at the design, and
   a ratio station's design seed kept where the PFD closes the design, the photographed limits held
   on what an operator enters (decision 160); a cascade master integrating while its slave is out of
   cascade, as V1's ``_ctrl_ipd`` builds it, kept (decision 160, B-117, decision 120's class); a
   vessel draining through a barometric leg its drawings show taller than any column the vacuum can
   hold draining on its own liquid head, the vessel's pressure no part of the drive (decision 161);
   a held liquor's boil-off on a tick where it boils — at the old pressure, the Jacobian's probe or
   the linearised step — taking its vapour space's backward step solved itself, the boil's kink at
   the bubble point and a root pinned on a memo bin's edge being what the linearisation cannot
   carry, the linearised step kept to the bit elsewhere (decision 162, decision 78's class);
   V1's thermo memo kept as ported where a stage chatters on its bin edges below its
   transmitter's resolution (decision 163, B-123);
   and no approximation of
   the physics bought for a pacing target (decision 88). A
   new mechanism still goes to the process engineer, with both sides measured.

## 6. Clean-codebase rules

* No file enters this tree unless it is part of the product, its tests, or its documentation.
* No `debug_*.py`, no `*_backup.py`, no `*_orig.py`, no `tmp_*`, no scratch output.
* Scratch work goes to the session scratchpad directory, never to the project.
* No asset is copied from V1 unless a screen actually renders it.
* `tests/` mirrors `ureasim/` one-to-one. A module with no test is an open item in `handoff.md`.

## 7. Session checklist

Start:
1. Invoke `Skill(caveman)` at `full`.
2. Read `project.md` (state) and `handoff.md` (open items).
3. Search claude-mem (`Skill(claude-mem:mem-search)`) for the history of the items the session
   takes up.

End (mandatory):
1. Update `project.md` checklist.
2. Update `handoff.md` — add new gaps, **delete closed ones**.
3. Update `Urea OTS — As-Built Mathematical Reference.md` for every equation touched.
4. State plainly what was finished, what was not, and why.
5. List all open gaps in the final report (mandatory, 2026-10-03): every open `handoff.md` item
   and open data gap, each with its status in a line, not only those the session touched.

## Sonnet + Opus Advisor Workflow

Binding whenever the session's main model is any version of Claude Sonnet (2026-11-04). A session
run on Opus works as the rest of this file says.

1. **Configuration and parity.** Use the latest Claude Opus as the advisor through the `advisor`
   tool — `"advisorModel": "opus"` in `.claude/settings.json` — held to the main model's thinking
   depth and effort, ultracode and high-effort coding included. The tool takes no parameters: the
   parity is the standard the advice is asked for, not a setting.
2. **Stage 1 — Ingestion (Sonnet only).** First read every document, source file, image, PDF and
   media file the task involves, and summarise its key context and constraints. Do not call the
   advisor before this context gathering is complete.
3. **Stage 2 — Thinking and planning (Opus advisor).** Before writing or modifying any code, invoke
   the `advisor` tool so that Opus does the architectural thinking, the edge-case analysis and the
   step-by-step implementation plan.
4. **Stage 3 — Execution (Sonnet only).** Follow the advisor's plan strictly. Sonnet makes every
   file edit, writes the boilerplate and runs every tool. If an unexpected blocker contradicts the
   plan, stop and consult the advisor again before going on.
5. **Stage 4 — Testing and verification (Opus advisor).** Whenever testing is required, consult the
   advisor to define the test cases, and have it audit the raw test output and logs before the task
   is declared complete. Where Opus needs direct command-line execution to debug a complex test, an
   Opus sub-agent may be started through the Agent (Task) tool: the one exception to §3's
   no-sub-agents rule, for that purpose and in Sonnet sessions only.
