# Architecture — Urea Plant OTS, Version 1.1

Moved verbatim from `project.md` on 2026-11-11 (session 96, `CLAUDE.md` section 3a). `project.md` sections 2 and 3: why V1.1 exists, the
technology, the layers, the directory layout, the HMI's parity with V1, single-console operation and
the engine scheduler as built. A citation of `project.md` section 3.x means the section of that number
below. Read it when a change touches the architecture; it is not session-start reading.

---

## 2. Why V1.1 exists

V1 is physically correct and structurally unmaintainable:

* `backend/main.py` — 12,511 lines, of which `step_sim()` alone is 4,122.
* Four near-identical abandoned copies: `main_orig.py`, `main_backup.py`, `main_debug.py`,
  `main_test_fix.py` (~36,000 lines of dead weight).
* ~40 `debug_*.py` / `patch_*.py` / `probe_*.py` scratch scripts in the package root.
* A stale git worktree (`backend/.claude/worktrees/...`) duplicating the whole tree again.
* HMI in hand-written HTML/JS talking to the physics over a WebSocket, so the UI cannot be
  reasoned about, tested, or shipped as one application.

V1.1 keeps the physics **byte-for-byte equivalent** and rebuilds everything around it.

---

## 3. Architecture

### 3.1 Technology

* **Python 3.11+** — core language, physics and engine.
* **PyQt6** — desktop HMI. No browser, no web server, no WebSocket.
* **NumPy** — vector/matrix work in the flowsheet solver only. The property correlations stay
  scalar, exactly as V1 wrote them, so numerical results are bit-comparable.
* **pytest** — regression harness, including V1-vs-V1.1 equivalence tests.

PyQt6 replaces the browser stack. The OTS runs as a **single local console** (decision 149)
communicating with the headless physics engine thread over `ureasim/hmi/bridge.EngineBridge`,
which speaks the console protocol over a `QTcpSocket` on the loopback interface (`127.0.0.1`).
The console talks to the plant through exactly that one boundary object. Nothing else crosses.

**Nothing at or below `ureasim/net` may import Qt.** Physics stays decoupled from presentation,
and the test suites and the Phase 7 runners drive the engine with no display.

### 3.2 Layers

```
                 ┌──────────────────────────────────────────┐
                 │  ureasim/hmi          PyQt6 presentation │   no physics
                 │  ├─ main_window.py    tab bar, screens   │
                 │  ├─ screens/          10 process screens │
                 │  ├─ widgets/          indicator, valve,  │
                 │  │                    pump, bargraph, XV │
                 │  ├─ faceplates/       PID / pump / HIC   │
                 │  ├─ instructor/       exercise panel     │
                 │  └─ trend/            multi-pen trend    │
                 │  └─ bridge.py         EngineBridge        │
                 └──────────────────┬───────────────────────┘
                                    │  TCP, length-prefixed JSON
                 ┌──────────────────┴───────────────────────┐
                 │  ureasim/net          console transport  │   no Qt
                 │  ├─ protocol.py       frames, messages    │
                 │  ├─ server.py         asyncio, loopback   │
                 │  └─ engine_host.py    the physics thread  │
                 └──────────────────┬───────────────────────┘
                 ┌──────────────────┴───────────────────────┐
                 │  ureasim/engine       simulation runtime │   no Qt
                 │  ├─ simulator.py      fixed-step loop    │
                 │  ├─ state.py          plant state vector │
                 │  ├─ scheduler.py      unit execution order + tear resolution
                 │  ├─ historian.py      ring-buffer trends │
                 │  ├─ snapshot.py       exercise save/load │
                 │  ├─ packet/           state -> UI packet │
                 │  ├─ command.py        operator commands  │
                 │  └─ session.py        the served plant   │
                 └──────────────────┬───────────────────────┘
                 ┌──────────────────┴───────────────────────┐
                 │  ureasim/units        unit operations    │
                 │  synthesis/  recirc/  desorption/        │
                 │  evaporation/  steam/  utilities/        │
                 └──────────────────┬───────────────────────┘
                 ┌──────────────────┴───────────────────────┐
                 │  ureasim/control      DCS control layer  │
                 │  ├─ controller.py     PID (I-PD form)    │
                 │  ├─ process_loop.py   regulatory loops   │
                 │  ├─ ratio.py          ratio stations     │
                 │  ├─ jet_pump.py       322F001's closure  │
                 │  ├─ valve.py          IEC 60534 actuators│
                 │  └─ interlocks.py     trips / ESD        │
                 └──────────────────┬───────────────────────┘
                 ┌──────────────────┴───────────────────────┐
                 │  ureasim/core         flowsheet primitives│
                 │  ├─ stream.py         Stream state vector │
                 │  ├─ node.py           capacitive nodes    │
                 │  ├─ flowsheet.py      directed graph      │
                 │  ├─ transport.py      plug-flow line lag  │
                 │  └─ units_of_measure.py                   │
                 └──────────────────┬───────────────────────┘
                 ┌──────────────────┴───────────────────────┐
                 │  ureasim/thermo       property packages   │   no plant knowledge
                 │  ├─ iapws.py          IAPWS-IF97 R7-97    │
                 │  ├─ properties.py     NH3-CO2-H2O props   │
                 │  ├─ vle.py            liquor bubble points│
                 │  ├─ extended_uniquac.py                   │
                 │  ├─ enthalpy.py       H0 elemental datum  │
                 │  ├─ real_gas.py       SRK equation of state│
                 │  └─ service.py        unified flash service│
                 └──────────────────────────────────────────┘
                 ┌──────────────────────────────────────────┐
                 │  ureasim/data         design basis        │
                 │  constants.py, design_point.py, ...       │
                 └──────────────────────────────────────────┘
```

**Dependency rule:** imports flow downward only. `thermo` imports nothing from the project
above it but the leaf `data/design_point.py`; `data` sits beside the ranking between `control` and
`units` (decision 182). `hmi` imports `net` and `data` and, below them, `core.units_of_measure`
alone: the faceplates convert a gauge display to absolute and back on the engine's own atmosphere
(decision 183, handoff A-32). `tests/test_layering.py` enforces every direction.

### 3.3 Directory layout

```
Urea Simulator V1.1/
├─ Claude.md                                  agent directives (binding)
├─ project.md                                 this file
├─ handoff.md                                 open issues for the human engineer
├─ Urea OTS — As-Built Mathematical Reference.md   every equation, with justification
├─ README.md                                  install + run
├─ requirements.txt
├─ run.py                                     application entry point
├─ launch.bat                                 Windows launcher: checks Python, starts run.py
├─ ureasim/
│  ├─ thermo/      property + VLE packages
│  ├─ core/        stream / node / flowsheet primitives
│  ├─ control/     PID, cascade, ratio, valves, interlocks
│  ├─ units/       unit operations, one package per plant section
│  ├─ engine/      integrator, state, scheduler, historian, snapshot
│  ├─ net/         console protocol + server (headless)
│  ├─ hmi/         PyQt6 client (screens, widgets, faceplates, trend)
│  └─ data/        design basis, tag registry, screen definitions
├─ tests/          mirrors ureasim/, plus V1-equivalence regressions
└─ tools/          migration utilities (overlay converter)
```

### 3.4 HMI design — parity with V1

The V1 HMI is **image-backed**: each screen is a PowerPoint equipment drawing exported to a
1366×720 PNG with the live symbols *deleted*, and live overlay elements positioned at the exact
centre of each deleted shape. That approach is preserved verbatim.

* Backgrounds: the same ten PNGs (`screen-321-1.png` … `screen-329-1.png`), copied once.
* Overlays: `frontend/overlays.js` holds a pure declarative table of 387 elements across ten
  screens. It is mechanically converted to `ureasim/data/screen_layout.py` by
  `tools/convert_overlays.py` — no coordinate is retyped by hand. The console renders 393: V1's
  387 and the six the process engineer added through the converter's `DECIDED_ADDITIONS`
  (decision 98: trip 21.2's five hand switches and AI-329701). Since decision 129 (2026-10-16) the
  47 modulating valves are readouts of their opening in per cent, not icons: only the XVs carry a
  valve symbol over the drawing's own.
* Element types:

  | type | count | PyQt widget |
  |---|---|---|
  | `ind` | 247 | `IndicatorWidget` — black box, live value + unit (a valve's opening among them) |
  | `nav` | 67 | `NavHotspotWidget` — transparent screen jump |
  | `pump` | 26 | `PumpWidget` — green running / grey stopped |
  | `bar` | 22 | `BargraphWidget` — vertical level fill |
  | `strm` | 12 | `StreamHotspotWidget` — stream inspector popup |
  | `xv` | 6 | `BlockValveWidget` — bowtie, open/closed |
  | `hs` | 4 | `HandSwitchWidget` |
  | `ae` | 2 | `AnalyserWidget` |
  | `ovrd` | 6 | `OverrideButtonWidget` |
  | `btn` | 1 | `PushButtonWidget` |

* The anisotropic slide mapping (`SLIDE_RX = (1366/12192000)/(720/6858000) = 1.06719`) that
  un-squashes rotated icons is reproduced in `widgets/icon_geometry.py`.
* Trend window stays a **separate top-level window** with 10 pens, 7 spans and 10 rulers,
  as in V1.

### 3.5 Single-console operation

The simulator is one plant with a single local console (decision 149, 2026-10-22; it superseded
the multi-station deployment of decisions 72, 124 and 125). `python run.py` (or `launch.bat`)
starts the engine and the console on one machine:

```
   console (PyQt6) ── loopback TCP ──> StationServer ──> engine host ──> engine (one plant)
```

All plant controls sit on the ten DCS screens and their faceplates, exactly what V1's operator
screens exposed. The controls that are not plant equipment — pacing, freeze, reset, malfunction
injection, the battery-limit CO2 demand (`co2_set`) and exercise save and restore — sit in the
Instructor menu's panel, so the process screens stay true to the DCS. The separation is the
console's layout: no command is refused for who sent it. The one exception is the start-up intro's
LOAD button, which restores a saved exercise before the held plant first runs (decision 171). The
exercises are the instructor's folder (`UREASIM_EXERCISES`, or `~/ureasim-exercises`), which SAVE
writes, and the repository's `scenarios`, shipped beside it and never written.

**Engine process refusals.** The engine decides whether the *plant* will accept a command — a
latched trip, an interlock, a closed valve — and its reason travels back to the console's status
bar. V1 dropped unknown commands silently, which teaches a trainee that the plant ignored them.

**Audit.** Every accepted command is echoed back to the console, naming the console that issued
it; the status bar's audit line shows the last one.

**Back-pressure.** Snapshots are dropped for a console that falls behind; commands and acks
never are. A slow console sees the latest plant state when it catches up, not a backlog of
stale ones.

**A disconnected console goes blank.** Every indicator returns to `--` and the status bar
says why. A frozen screen that still looks live is the most dangerous thing an OTS console
can do. A link silent for 5 s is treated as dead (the staleness watchdog).

```bash
python run.py                                  # the engine and its console
```

The engine binds `127.0.0.1` only, and refuses a `hello` from any other address. The console
still talks over a real socket rather than sharing objects with the engine, so no widget can
reach into the physics and the engine never waits on a repaint.

### 3.6 The engine scheduler — as built in Phase 5

**Status: built in session 38 (As-Built Part LV)** for every ported unit; the synthesis loop joined
it in session 39 (Part LVI), and since Phase 4 closed (UF85, session 55) it runs the whole plant. As built: the five sources, the checks and the tick are `engine/schedule.py`
and `engine/scheduler.py`; the plant's own schedule is `engine/plant/`, one module per plant
section; the trips are the tick's last step; besides A-10's tears, `TearState` names the other
cross-tick flows the schedule needs (unit 324's condensates and inerts, 741, LV-324501B's recycle,
the steam users' draws). The draft as written in 2026-09-27 follows. It was written then because
three unit-323 stages already passed state to each other, and the way they did it in the
equivalence tests is the way the engine has had to.

**What it must reproduce.** V1's `step_sim()` is 38 sections run in source order
(`docs/step_sim_dataflow.md` §1). That order is physics, not bookkeeping: whether a unit reads a
neighbour's state before or after the neighbour advances decides every one-tick delay in the
plant. So the scheduler REPRODUCES V1's order; it never derives one of its own. A topological sort
of the flowsheet would be a legal order and a different plant.

**1. One tick.**

```text
tick(dt):
  1. commands   apply the accepted commands queued since the last tick — hand valves, modes,
                set points, malfunctions — to the objects in the plant state, atomically
  2. units      step every unit in V1's section order; each returns a frozen Result
  3. tears      copy the named producer outputs into TearState at V1's two tear-write points
                (sections 25 and 32), for the next tick to read
  4. trips      interlocks on the advanced state (V1 sections 34-36), acting from the next tick
  5. publish    the stream registry, the snapshot, the historian sample
```

**2. The schedule is data, and it is checked.** `engine/schedule.py` holds an ordered tuple of
steps, one per unit, each with a wiring table that names where every argument of the unit's
`step()` comes from. There are exactly five kinds of source:

| source | meaning | example |
|---|---|---|
| `Result(unit, field)` | a same-tick output of an EARLIER step | 323F010 takes `FlashTankResult.m_319_kgh`, `.drain_t_c`, `.drain_w`; 328D003 takes `AtmosphericAbsorberResult.m_343_kgh`, 323E011 takes `AmmoniaWaterTankResult.m_791_kgh` (As-Built §XXXV.6); 328E007 takes `AmmoniaWaterTankResult.m_735_kgh` and `.t_ii_c` (§XXXVI.3); 328C002 takes `DesorberHeatExchangerResult.m_738_kgh` and `.t_738_c` (§XXXVIII.5) |
| `State(unit, field)` | a LATER unit's state as it stood at the top of the tick | 323F004 reads `PreEvaporator.p_bara` for LV-323505's downstream pressure, and `FlashCondenser.p_bara`, the LP flash gas node it rides; 323C003 reads `LpCarbamateCondenser.p_bara`, the node PT-323201 rides; 323E003 reads `FlashCondenser.p_bara`, the node PV-323202 vents to |
| `Tear(name)` | a named TearState field, written last tick | A-10's `m748_prev`, seeded with its design flow; LV-324501B's melt recycle into 323D002; 323E011's 718B into 323E003 |
| `Operator(tag)` | a hand-valve position or set point held in the plant state | HIC-323605 |
| `Boundary(name)` | a battery-limit or utility value | the LP header, PFD 331 |

At start-up the scheduler validates the wiring against `core/flowsheet.py`: a `Result` must come
from a step that runs earlier; every `State` read of a later unit, and every `Tear`, must match a
declared `flowsheet.Tear`; and the schedule must be a legal evaluation order of the torn graph,
which `Flowsheet.evaluation_order()` already refuses when it is not. A wiring that reads the
future without a declared tear stops the engine at start-up instead of surfacing as a late
transient.

**3. Passing state: three channels, and no fourth.**

* **Result objects** carry everything that flows forward within a tick — including a drain's
  DEPARTURE state, because the receiving unit owns its inlet line (`liquor_line.receive_liquor`).
* **A unit's own state, read at the top of the tick,** carries every backward pressure or
  temperature read. The reader runs before the owner, so the value is last tick's by
  construction; that IS the tear, and it is declared.
* **TearState** carries the inter-section flows V1 kept in `s.tlag` (A-10's eleven, and the
  others of `docs/step_sim_dataflow.md` §2): one named field each, its seed declared with its
  source in the producing unit's data module, its one-tick delay stated beside it.

There is no global dictionary and no `s.tlag.get(key, default)`. `engine/state.py` owns the unit
objects, the controller objects, the hand-valve positions, TearState and the plant clock;
exercise save and restore are its serialisation, and the snapshot is a read of it.

**4. Recycle tears: one tick of delay, no in-tick convergence** (decision 8, handoff A-10). There is
no Wegstein, no Broyden and no successive substitution. Each tear carries exactly one step of
delay, as in V1, and that is stable for reasons the ported units already show:

* every tear feeds a capacitance — a liquid holdup or a vapour space — and those time constants
  are three orders above the step: 323C003 120 s, 323F004 180 s, 323F010 240 s of residence;
* the STIFF couplings live inside units and are integrated there, semi-implicitly: PT-323204's
  0.78 s vapour node by a backward-Euler step on its own valve, the 323 temperature steps with
  their flows' heat-capacity rates, each steam chest by a bracketed solve. No stiff loop crosses
  a tear, so none needs iterating across one;
* iterating a tear to convergence inside the tick would delete its delay and change every
  transient that crosses it, which Phase 7's transient comparison with V1 would then fail by
  construction; and it would not fix a real runaway — B-13 is a loop gain above 1.

If a Phase 5 run shows a tear ringing, it is measured, and a relaxation is added on THAT tear with
its measurement in handoff A-10. Never a global iteration.

**5. The step is fixed** (decided 2026-09-27, handoff A-14; `Claude.md` §1 rule 10; decision 9).
Every tear's delay is one step, so the step must not move. V1 steps on the wall clock — a variable
step up to 0.25 s — which makes a transient depend on machine load. The law: a fixed 0.1 s, V1's
`DT` and the step every equivalence test runs at; `simulator.py` accumulates wall-clock x pacing
and pays it in whole steps, so SLOW and FAST run the identical steps and an exercise replays bit
for bit.

**6. What is built, in order, and how it is proven.** `state.py`, `schedule.py` (the wiring and its
validation), `scheduler.py` (the tick), `simulator.py` (pacing), `snapshot.py`, `historian.py`,
`command.py`. Three proofs: a schedule test that is REFUSED an undeclared future read; the four
ported 323 stages run through the scheduler, bit-exact against the chained equivalence test that
already runs V1's stages 1 to 4 against the port
(`test_solution_tank_equivalence.py::test_all_four_stages_coupled_through_a_stripper_feed_cut`
is the template); and the design pin held over the assembled plant.

