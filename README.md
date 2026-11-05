# Urea Plant Operator Training Simulator — V1.1

A dynamic simulator for a 1750 MTPD Stamicarbon-type CO2-stripping urea plant, with a
PyQt6 DCS-replica operator console.

This is a ground-up rewrite of `D:\Work\Urea Simulation`. The process engineering is
carried across unchanged and proven equal by regression test; the architecture around it is
new.

## Install

```bash
python -m pip install -r requirements.txt
```

Python 3.11 or newer.

## Run

The simulator is **one plant with a single local console** (decided 2026-10-22): the headless
engine and the console window on one machine, talking over the loopback interface.

On Windows, double-click **`launch.bat`** in this folder. It finds Python (the `py` launcher, or
`python` on the PATH), checks for 3.11 or newer and for the packages in `requirements.txt`, and
starts the engine with its console; if anything is missing it says what and waits. Any arguments
are passed to `run.py`.

The console opens on the Helwan Fertilizers start-up intro. The plant is built and held at its design
seed, the 1750 MTPD design basis, while the intro plays, and it starts when you press **100% LOAD**
(click the button, or press Enter or Space). Any key or click before the button appears skips the
animation without starting the plant. `--no-intro` skips the intro and runs the plant from the start;
`--fullscreen-intro` plays it full screen. The intro is drawn on the GPU where the machine has one
(a hardware OpenGL 2.0 context) and by the CPU everywhere else; set the environment variable
`UREASIM_INTRO_RENDERER=raster` to force the CPU if a driver misbehaves.

Or from a shell:

```bash
python run.py
```

The console opens on screen 321-1. Navigate with the tab bar, with a nav hotspot on the
graphic, or by right-clicking any element.

The status bar carries an audit line naming the last accepted command. A command the *plant*
will not accept — a latched trip, an interlock, a closed valve — is refused by the engine, and the
refusal says why.

### The engine

The engine runs the plant on its own physics thread: the design seed at start, fixed 0.1 s
steps at the instructor's pacing, the console packet (V1's WebSocket key paths) published to
the console ten times a second, each command applied between two ticks and answered with the
plant's reason when it is refused. Exercises are saved under `~/ureasim-exercises` unless
`UREASIM_EXERCISES` names another folder. The status bar shows whether the engine is running,
frozen or faulted.

A console that loses its link goes blank and says why — it does not keep showing the last
values it received.

### Faceplates and the instructor's panel

A left-click on an instrument opens its faceplate — a loop's PV, set point, output and mode, a
pump's START / STOP, a hand valve's opening, a block valve's OPEN / CLOSE — one per instrument.
ENTER sets the value typed and closes it; a refusal is shown with its reason. The **Instructor**
menu (Ctrl+I) opens the controls that are not plant equipment, kept off the process screens:
pacing, freeze, reset, the malfunctions, the CO2 demand on 320K002 (the battery-limit boundary)
and exercise save and restore.

### The stream inspector

A left-click on a drawn process line, or on an AE analyser, opens the stream inspector: the route,
phase, temperature, pressure, the mass, molar and volumetric flows, molar mass, density, enthalpy and
the composition on both bases (an analyser shows the composition alone), exactly as the engine
publishes the stream, redrawn with every packet.

### The trend window

**View > Trend window** (Ctrl+T) opens the multi-pen trend in its own window: ten pens, spans of
one minute to eight hours (or one typed, such as `30s` or `3h`), ten rulers, and a table of each
pen's live value, MIN / MAX / AVG over the view and its value under each ruler. Right-click an
instrument and choose **Trend**, or drag it onto the plot or a row, to add a pen. Every trace comes
from the engine's historian — the window keeps no samples of its own — so it shows the last eight
hours of the exercise whenever it is opened.

## Test

```bash
python -m pytest
```

The suite includes **V1-equivalence regressions**: they load the V1 modules from
`D:\Work\Urea Simulation\backend` by file path and assert bit-for-bit agreement with the
ported code. If the V1 tree is absent those tests skip, and the rest of the suite still
runs.

The Phase 7 transient runner drives V1 and the rewrite through the same operating procedure at
the same fixed 0.1 s step, one process each, and writes a comparison report outside the project
tree (by default `<temp>/ureasim_phase7`). The scenarios are `cold_start`, `trip_22_2`,
`hpcc_rupture`, `vacuum_break` and `steady_state` (the design seed for an hour, every packet leaf
compared); `--duration` shortens one for a smoke run:

```bash
python -m tests.phase7.run all --side both
```

## Regenerate the screen layout

The ten screens' overlay geometry is generated from V1's `frontend/overlays.js` — never
typed by hand:

```bash
python tools/convert_overlays.py
```

## Documents

| file | what it is |
|---|---|
| `Claude.md` | binding directives for any agent working in this workspace |
| `project.md` | architecture and the living progress checklist |
| `handoff.md` | open issues for the human engineer |
| `Urea OTS — As-Built Mathematical Reference.md` | every equation and thermodynamic package, with the case for each |

## Layout

```
ureasim/
  thermo/   property and VLE packages   — no plant knowledge
  core/     stream / node / flowsheet primitives
  control/  PID, ratio, valves, jet pump, interlocks
  units/    unit operations, one package per plant section
  engine/   integrator, state, scheduler, historian, console packet, session
  net/      console protocol, server, engine host — headless
  hmi/      PyQt6 console                — no physics
  data/     design basis, generated screen layout
```

Imports flow downward only. `thermo` knows nothing about the plant; `hmi` computes nothing.

The engine runs headless, so **nothing at or below `ureasim/net` may import Qt**:

```bash
grep -rn "PyQt6" ureasim/net ureasim/engine ureasim/units ureasim/control ureasim/core ureasim/thermo
```

That must print nothing.
