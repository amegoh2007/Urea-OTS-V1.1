# Phase checklist, Phases 0 to 7 — complete

Moved verbatim from `project.md` on 2026-11-11 (session 96, `CLAUDE.md` section 3a). `project.md` section 4. Every item is done; the file is
frozen. Later work is recorded in `docs/history/session-log.md` and in the As-Built reference.

---

## 4. Progress checklist

Legend: `[ ]` not started · `[~]` in progress · `[x]` done · `[!]` blocked (see `handoff.md`)

### Phase 0 — Workspace
- [x] Create `D:\Work\Urea Simulator V1.1`
- [x] `Claude.md` — agent directives
- [x] `project.md` — this file
- [x] `handoff.md` — issue tracker
- [x] `Urea OTS — As-Built Mathematical Reference.md`
- [x] Package skeleton (`ureasim/…`, `tests/`, `tools/`)
- [x] `requirements.txt`, `README.md`, `run.py`, `pytest.ini`, `.gitignore`
- [x] V1-equivalence harness (`tests/equivalence/v1_loader.py`)

### Phase 1 — Thermodynamic core (`ureasim/thermo`)
- [x] `iapws.py` — IAPWS-IF97 R7-97 water/steam boundary — **bit-exact, 65 assertions**
- [x] `parameters.py` — verbatim Extended UNIQUAC tables (data only)
- [x] `standard_state.py` — Helgeson Cp, Gibbs-Helmholtz, ln K, H0, dH_rxn
- [x] `henry.py` — Rumpf & Maurer (NH3, CO2) + IAPWS G7-04 (N2, O2, CH4, H2)
- [x] `activity.py` — complete Extended UNIQUAC gamma + excess enthalpy
- [x] `srk.py` — SRK vapour fugacity, k_ij = 0
- [x] `speciation.py` — R1-R5 damped log-space Newton, with neighbour seeding
- [x] `properties.py` — package facade — **bit-exact, 202 assertions**
- [x] `enthalpy.py` — H0 elemental datum — **bit-exact, 145 assertions**
- [x] `extended_uniquac.py` — neutral H2O/urea binary (Voskov & Voronin)
- [x] `vle_grid.py` — the 1215-node activity table: continuation build, cache, interpolation
- [x] `vle.py` — liquor bubble points and partial pressures
- [x] `real_gas.py` — SRK isenthalpic letdown and compressibility
- [x] `domains.py` — species, domain classification, the refusal
- [x] `memo.py` — quantised memo policy and the canonical point
- [x] `kvalues.py` — K-values, the anchored ratio, bubble and dew points
- [x] `service.py` — unified flash service façade
- [x] `empirical.py` — anchored bulk properties for the 10 Hz inner loop
- [x] `data/design_point.py` — the PFD anchors those departures are taken from

**Phase 1 is complete.** 18 modules, every one under the 600-line house cap, every relation
proven bit-for-bit against V1.

### Phase 2 — Core primitives (`ureasim/core`)
- [x] `numeric.py` — both V1 limiters, including what each does with a NaN
- [x] `units_of_measure.py` — the unit conventions and the two atmospheric constants
- [x] `packet.py` — `StreamPacket`: mass, temperature, cp and composition as one object
- [x] `transport.py` — plug-flow dead time, routes, the two transit-time forms
- [x] `signal.py` — instrument conditioning: lag, dead time, FOPTD
- [x] `node.py` — vapour-space pressure, liquid holdup, anchored level indication
- [x] `stream.py` — the published process-stream record behind the stream inspector
- [x] `flowsheet.py` — the directed graph, declared recycle tears, checked solve order
- [x] `relief.py` — the safety valve on a node: V1's API 520 capacity law (moved here from
      `control/` in session 29), the pop action and blowdown, the vent to the reseat pressure
- [x] `data/process_routes.py` — the five product-line routes and their derived dead times
- [x] `data/design_point.py` — the 323 design flow chain the routes are anchored on

**Phase 2 is complete.** Three modules more than the original five: `numeric.py` exists
because V1 defines `clamp` twice with different NaN behaviour and the difference is load
bearing; `packet.py` is split from `transport.py` because a stream sample and a line delay
are two concepts; `signal.py` is split from `transport.py` because one moves material and
the other moves a number to a screen, and confusing them is how a state acquires an
invented time constant.

`flowsheet.py` is the one module with **no V1 counterpart** — V1's evaluation order is the
order its 4,051 lines happen to be written in. It contains no physics: it refuses a recycle
that has no declared tear, and otherwise says nothing.

### Phase 3 — Control layer (`ureasim/control`)
- [x] `valve.py` — IEC 60534-2-1 trim laws, choking, back-solved Cv, anchored ratio forms,
      gravity discharge, non-return valve
- [x] `relief.py` — API 520 Part I pressure-relief valve, critical vapour flow (moved to
      `core/relief.py` in session 29, with the relief law built on it)
- [x] `process_loop.py` — the engineering-unit I-PD loop (V1 `_ctrl_ipd`) and the flow loop
      built around it (V1 `_fic_flow`), including the volumetric migration
- [x] `controller.py` — the per-cent-of-span faceplate controller (V1 `controllers.py`)
- [x] `ratio.py` — ratio master with external-reset feedback; open-loop ratio demand
- [x] `interlocks.py` — trips 21.x / 22.x: plain, armed, reset-banded, self-clearing
- [x] `machines.py` — centrifugal compressor on a polytropic map, surge and stonewall (deleted in
      session 46: 320K002, its only user, is a boundary feed, decision 73)
- [x] `core/node.py` — `solve_node_pressure`, the bracketed node-balance solve
- [x] `core/units_of_measure.py` — `PA_PER_BAR`, `R_GAS_J_KMOL`

`cascade.py` was NOT written, deliberately. V1 has no cascade block: cascade is the CAS mode
of a controller plus a `cas_sp` argument, and the wiring between a primary and a secondary is
the unit's. A module would have been invented structure. Recorded here so the absence reads
as a decision rather than an omission.

Phase 3 is complete. Every module is proven against V1 except `interlocks.py`, whose source
is thirty lines written inline inside `step_sim` and cannot be executed in isolation; its
rules are transcribed into the test and that weaker standard of evidence is logged as
handoff **A-12**.

### Phase 4 — Unit operations (`ureasim/units`) — one section at a time

**Re-opened 2026-10-01** (session 30, decision 35). Closed for the flowsheet's assembly in
session 29; the process engineer then ruled that every physical unit is ported before the
scheduler, which is built on the completed plant's data flow. Ported: `feed/`, `synthesis/`,
`recirc/`, `desorption/`, `absorption/` (session 30). Open: unit 324 (`evaporation/`) and the
steam system (`steam/`).
- [x] `docs/step_sim_dataflow.md` — the boundary-crossing map that gates this phase
- [x] Split the 232 couplings into 125 process and 107 telemetry-only
- [x] `docs/coupling_resolution.md` — all 125 process couplings resolved, row by row
- [x] `tests/docs/test_coupling_resolution.py` — the two documents cannot drift apart
- [x] `feed/` — 321D003, 321P002 A/B, NH3/CO2 ratio block
      (`pump.py`, `feed_drum.py`, `station.py`, plus `data/unit_321.py` and
      `thermo/empirical.nh3_psat_bara`)
- [x] `synthesis/` — **complete.** 320K002 (a boundary feed since session 46, decision 73), its discharge line, the whole of 322E001 — the
      falling-film bundle and its bottom sump — the 322F001 ejector, the 322E002 carbamate
      condenser, the whole of 322R001, the 322E003 HP scrubber and the HV-322604 purge letdown
      (`co2_compressor.py`, `co2_line.py`, `stripper.py`, `stripper_sump.py`, `ejector.py`,
      `carbamate_condenser.py`, `reactor.py`, `reactor_column.py`, `reactor_calibration.py`,
      `reactor_hydraulics.py`, `scrubber.py`, `purge_valve.py`, `hp_split.py`, plus
      `data/unit_320.py`, `data/unit_322e001.py`, `data/unit_322e002.py`,
      `data/unit_322e003.py`, `data/unit_322f001.py` and `data/unit_322r001.py`). The step_sim
      wiring — the node ODEs and the tears — is Phase 5 work, as planned; done in session 39
      (`loop_hydraulics.py`, `reactor_inventory.py`, `condenser_holdup.py`, `ccw_loop.py`,
      `scrubber_sump.py`, `loop_pressure.py`, `data/synthesis_pin.py`, `data/unit_322_loop.py`,
      `data/unit_329_ccw.py`; As-Built Part LVI)
- [x] `recirc/` — **done: the liquor train and both LP gas nodes.** The shared urea-liquor
      stage layer (`thermo/urea_liquor.py`, `units/liquor_stage.py`), the liquor lines
      (`units/recirc/liquor_line.py`), 323C003 / 323E002 (`units/recirc/rectifying_column.py`,
      with the shared `units/steam_chest.py`), 323F004 (`units/recirc/flash_tank.py`),
      323E010 / 323F010 (`units/recirc/pre_evaporator.py`), 323D002
      (`units/recirc/solution_tank.py`), 323E011 / 323D011 with PIC-323203
      (`units/recirc/flash_condenser.py`) and 323E003 / 323D001 / 323P001 with PIC-323202,
      LIC-323502 -> SIC-323901 and TIC-323013 (`units/recirc/lp_carbamate_condenser.py`), on
      `data/unit_323.py`, `data/unit_323e011.py`, `data/unit_323e003.py` and `data/unit_329.py`.
      Six decided divergences stand in it (323D002, 323F010's leg, 323D011's pump, the
      span-rescaled gains of PIC-323203 and PIC-323202, 323E003's uncapped capacity and
      323D001's pump), and one decision to keep V1 (PIC-323202's single vent); open items B-20
      to B-25, B-28, B-30, B-31. 323C005 / 328V001, which take PFD 702, are `desorption/`'s.
- [x] `desorption/` — **done** (session 28; unit 328 closed). 323C005, the atmospheric absorber
      (`units/desorption/atmospheric_absorber.py`, on `data/unit_323c005.py`, with the
      saturated-gas law `thermo/saturated_vent.py`), and 328D003, the ammonia water tank
      (`units/desorption/ammonia_water_tank.py`, on `data/unit_328d003.py`), 328E007, the
      desorber heat exchanger (`units/desorption/feed_effluent_interchanger.py`, on
      `data/unit_328e007.py`), and 328C002, desorber I (`units/desorption/first_desorber.py`, on
      `data/unit_328c002.py`), with the train's shared species layer (`thermo/ammonia_water.py`,
      `units/desorption/desorber_stage.py`, `data/desorption_train.py`), and 328C003, the
      hydrolyser, with 328E021 (`units/desorption/hydrolyser.py`, on `data/unit_328c003.py`), are
      ported. Decided divergences in it: 328D003's heel and overflow, the five tank loops' gains
      per cent of span, FIC-328402's transmitter, 328E007's pinch, 328C002's condensing duty,
      level-valve choke, heel and overflow, the liquid paying what boils on 328C002 and 328C003,
      328C003's five rule-7 classes, and 328C004, desorber II (`units/desorption/second_desorber.py`,
      on `data/unit_328c004.py`), with FFIC-329401 on 735, FFIC-329401 a ratio station and
      LIC-328505 over FIC-328406 with 741 drawn from the column (decisions 26, 27), and six rule-7
      classes, and 328D001 with 328E004, the reflux drum (`units/desorption/reflux_drum.py`, on
      `data/unit_328d001.py`), with 328E004 held above its cooling water, the vent on 323E011's
      live pressure, 328C002's overflow taken in (decisions 28-30), and five rule-7 classes. Session
      29: the letdowns flash (decision 31; LV-322501, LV-323501, LV-323505, LV-328505), 328C003
      and 328C002 relieve through their safety valves (decision 32), 328D001 on its vessel with
      heads and LT-328501's taps (decision 33). Open in it: A-15's other overflows and A-16's
      relief nodes (Phase 5), B-52.
- [x] `absorption/` — **done** (session 30). 322C001, the LP absorber
      (`units/absorption/lp_absorber.py`, on `data/unit_322c001.py`), with its two packed beds
      (`units/absorption/packed_beds.py`: Onda transfer units on Colburn's balance, calibrated on
      PFD 204 -> 797) and the thermodynamics under them (`thermo/ammonia_backpressure.py`,
      `thermo/transport_properties.py`). Decided divergences: SV32253 at its certified 6.013 bar a
      (decision 34's class), and under rule 7 the vessel's 3.60 m3 with LT-322502's taps, the
      heel, the full column, PV-322201's and LV-322502's vendor trims, PIC-322201 on span.
      Session 31, decided (36-38): 322E006 on its datasheet UA (`units/absorption/feed_cooler.py`,
      on `data/unit_322e006.py`); XV-322915's flood in the vent line with trip 22.1 on TI-322015
      (`units/absorption/vent_line.py`); HV-322604's letdown flashed onto the carbamate liquor it
      condenses (`thermo/condensing_letdown.py`), the liquor into the sump. Session 32, decided
      (39): I 22.1 on AC4's PC22.5.1, HS-322915 a maintained keyswitch
      (`vent_line.xv_322915_open`). Session 33, decided (40, 41): XV-322915 with no operator
      open, HS-322915 its only control (`keyswitch_set`, the overlay's decided edits); the flood
      on the valve's rated 1000 kg/h of 9 bar a steam. Open: A-17 (wired with the schedule).
- [x] `evaporation/` — 324E001/F001, 324E003/F003, vacuum train, UF85. Surveyed in session 31:
      the vacuums are live states, the ejectors linear pulls (B-57, decide before the vacuum
      train). Ported (session 31): the four vacuum condensers, 324E002 / E005 / E006 / E007
      (`units/evaporation/vacuum_condenser.py`, on `data/unit_324.py`), bit-exact; the
      saturated-gas branch already in `thermo/saturated_vent.py`. Ported (session 32): the
      condensers as nodes (`condenser_node.py`), the melt's anchored equilibrium
      (`thermo/urea_melt.py`), both bit-exact. Session 33, decided (42, 43): the melt on UNIQUAC
      refitted to the PFD with the non-volatile ceiling; the ejectors' maps synthesized on their
      throats and vendor duty points (`ejector_map.py`, `ejector_gas_dynamics.py`), not wired
      until B-61 (the maps cannot hold the PFD's vacuums). Ported (session 33): stage 1,
      324E001 / 324F001 (`first_evaporator.py`), bit-exact tick by tick, six departures both
      ways, the pull an argument; B-62 raised (no feed, no boil-off). Session 34, decided (44,
      45): the maps' capacity on the PFD's design loads, wired into both stages; the held melt
      boils past its own boiling point (`holdup_boil.py`). Ported (session 34): stage 2,
      324E003 / 324F003 (`second_evaporator.py`), bit-exact tick by tick, eight departures both
      ways, LV-324501's selector (UF85 deferred); B-63 and B-64 raised. Session 35, decided
      (46-48): stage 2's feed at its leg's strength; the PFD's motive steam; 323F010's liquor
      boils past its bubble point. Ported (session 35): the vacuum train (`vacuum_train.py`),
      bit-exact against V1's executed train, the motive valves on their vendor trims; B-65 and
      B-66 raised. Session 36, decided (49, 50): the cold ends lagged on their tubes' water;
      324E006's shell a live vacuum node (`VacuumTrain`); B-67 raised. Session 37, decided (51):
      the condensers' vent on additive departures; B-71 raised. Session 38, decided (55, 56): V1's
      ratio where a design back-pressure exceeds the PFD's partial pressure; the motive valves
      against the live LP header and their nozzles. Unit 324 complete but for UF85 (unit 335).
      Session 55, decided (121, 123): 708 at 324F002's adiabatic discharge temperature; UF85 ported
      (`units/finishing/uf85_dosing.py`, `data/unit_335.py`) and dosing live on route A
- [x] `steam/` — 329D005, 329D009, 322D001A/B and their headers, the condensate cascade, the
      letdowns (session 37; decisions 52-54: every simulated user live on its header, the LP
      header at 4.0 bar g, the drums' own waters and no floor); V1's ``step_steam`` transcribed
      with nine switches, ``==`` V1 executed and ``==`` the port; B-72 to B-74 raised. Session 38,
      decided (56, 57): the motive steam, FV-329401 and XV-322915's flood on their valves against
      their headers' live pressures; B-72 and B-74 Calibration Deferrals. Session 39 (decision 58):
      322D001A/B feed the LP header through 917, 960 joining it downstream of the drums. The cooling
      water V1 writes in `main.py` as per-exchanger factors goes with the scheduler
- [x] `consequence/` — **part done, and it will stay part done on purpose** (ticked as built,
      session 56). `seal.py` (the
      liquid seal over a drain nozzle and the IEC 60534 gas blow-through) and
      `crystallisation.py` (the mushy-zone flow restriction) are ported, which is every
      function of V1's `backend/consequence.py` that V1 itself ever calls. Carry-over, NPSH,
      the urea and carbamate solubility curves, air ingress and the one-call vessel block are
      written in V1 and referenced from nowhere — see the Session 8 log. They are ported if
      and when a unit needs one, not before.

### Phase 5 — Engine and transport (`ureasim/engine`, `ureasim/net`)
- [x] `net/protocol.py` — framing, message kinds, roles, command authorisation (roles retired in
      session 68, decision 149)
- [x] `net/server.py` — asyncio fan-out, audit broadcast, late joiners, back-pressure (one loopback
      console since session 68, decision 149)
- [x] `hmi/bridge.py` — `QTcpSocket` client, reconnect backoff, staleness watchdog
- [x] `run.py` — `server` / `station` / combined launch modes (the combined launch alone since
      session 68, decision 149)
- [x] `state.py` — the plant clock and the recycle tears (session 29): the eight that cross
      units in a frozen `TearState` committed at the end of the tick, V1's seeds `==`, 748/750
      `==` V1's `s.tlag` over 3000 coupled ticks; the units and controllers join it with the
      schedule (session 38: the units, their controllers, the operator's positions, the boundary
      values; twelve more cross-tick flows named)
- [x] `schedule.py`, `scheduler.py`, `plant/` — V1's section order as a checked, data-driven
      schedule; one-tick tears (session 38, As-Built Part LV): every ported unit scheduled, the order
      a topological order of the torn flowsheet, each unit once a tick, the liquor train ``==`` V1's
      chain through it. Session 39 (Part LVI): the synthesis loop scheduled — 32 steps, 64 declared
      one-tick reads, no synthesis boundary left, the glue ``==`` V1's transcription on every tick
      through seven scenarios on V1's boot pin; the plant at 100 % load holding an hour, its LP
      header at 4.0 bar g. Session 40 (Part LVII): B-75, B-76, B-78 items 1-3 decided and built; the
      motive-loss stall fixed (node stores, the letdown's stop rule). Session 41 (Part LVIII): 34
      steps — V1's section 6 display lags (`322-DISPLAY`) and section 33's standby faceplate
      (SIC-323902) scheduled. Session 42 (Part LIX): the stripper's blow-through to 323C003 and its
      relief, 328D001's overflow to 323E011, three boundary sinks (A-15, A-16). Session 43 (Part
      LX): 323E011's envelope overflow to 323C005 (A-20), two tears. Open: A-18's FAST pace
- [x] `simulator.py` — the fixed 0.1 s step (decided 2026-09-27, handoff A-14) paid out of an
      integer wall-clock account (session 29); SLOW/FAST pacing changes the step count, never the
      step; the replay test bit for bit
- [x] `historian.py` — V1's ring buffers ported, every query ``==`` V1's module (session 40, As-Built
      §LVII.3); session 41: it records the console packet on V1's paths, as V1 did, and answers over
      the station protocol
- [x] `snapshot.py` — exercise save and restore, the restored plant replaying bit for bit (session
      40, §LVII.4; the process engineer's assignment of the module). The console packet, V1's
      WebSocket key paths and section 6's display lags, moves to `packet.py`
- [x] `command.py` — V1's `handle_cmd` port, all 41 types, `(accepted, reason)` with the process
      reason on every refusal; B-59's keyswitch (session 40, §LVII.5)
- [x] `session.py` — the server's command handler: the plant, its simulator, the historian, the
      commands, pacing, freeze, reset, exercise save and restore (session 40, §LVII.6)
- [x] `packet/` — the console packet on V1's WebSocket key paths (session 41, As-Built §LVIII.2):
      every path V1's `step_sim` returns but its five diagnostic blocks (A-19), each value the port's
      with V1's rounding; 264 of the screens' 268 bindings resolve (the four others unit 335's;
      all 274 since session 55, decision 123);
      section 6's lags a scheduled step, ``==`` V1 on every tick (§LVIII.1)
- [x] `net/engine_host.py` — the server's engine loop (session 41, §LVIII.4): the plant on its own
      physics thread, commands between two ticks, the packet ten times a second with V1's health
      block, trend backfill over the protocol (V1's `/api/hist`); `run.py` serves the live plant

### Phase 6 — HMI (`ureasim/hmi`)
- [x] `tools/convert_overlays.py` — `overlays.js` → `screen_layout.py` — **387/387 elements**
- [x] Copy the 10 background PNGs + pump/XV icons
- [x] `theme.py` — colour tokens transcribed from the V1 stylesheet
- [x] `state_access.py` — dot-paths, formatting, gauge-pressure rule, shared-tag `BindMap`
- [x] `widgets/icon_geometry.py` — anisotropic un-squash (`SLIDE_RX = 1.0671875`)
- [x] `widgets/` — all eleven element widgets
- [x] `screen_view.py` — stage, uniform scaling, overlay placement, edit-layout mode
- [x] `main_window.py` — tab bar, screen menu, health LED, layout persistence
- [x] `engine/bridge.py` — the single engine-to-UI boundary
- [x] Geometry gates: centring, stage bounds, pinned collision set
- [x] Role badge, audit line and refusal reporting in the status bar (the role badge and the
      assignment readout retired in session 68, decision 149)
- [x] Unit assignment: tag-to-section resolver, server enforcement, station status bar; session 41:
      every engine command type attributed to the section it moves, `r323_ctrl_set` by its
      faceplate (§LVIII.5); retired in session 68 with `data/tags.py` (decision 149)
- [x] The engine attached: `run.py` serves the live plant to every console (session 41)
- [x] The console's history request (`hmi/bridge.py`), with the trend window (session 43, As-Built
      §LX.3): ``request_history``, ``history_received``
- [x] `faceplates/` — PID, pump, HIC, master-setpoint (session 42, As-Built §LIX.5): V1's routing
      over every element; the loop, speed, pump, hand-valve, block-valve, keyswitch, route, MASTER SP
      and indicator faceplates, each a renderer of the packet and an emitter of the engine's commands
- [x] `instructor/` — malfunction panel, unit assignment, freeze, exercise save/restore,
      station roster (session 42, §LIX.6; the roster and the exercise list on the protocol); the
      roster and unit assignment retired and the CO2 demand added in session 68 (decision 149)
- [x] `trend/` — separate window, 10 pens, rulers, spans (session 43, §LX.4): V1's window over the
      engine historian alone, the whole window asked once a second; a pen from an element's menu or
      by dragging the element onto the window
- [x] Stream inspector popup (session 44, As-Built §LXI.8): `hmi/widgets/stream_hotspot.py`, V1's
      ``renderStream`` over the packet's ``STREAMS``, proved by node on every published stream
- [x] Single-machine mode (session 44, §LXI.7): the console the superuser, granted on the engine's
      own machine only; A-2 (authentication) and A-8 (unit assignment) deferred until the port is
      complete, the instructor's panel paused — all three lifted in session 56
- [x] The multi-station deployment (session 56, decisions 124, 125, As-Built Part LXXII): A-8's
      section assignment signed off as built; A-2 closed on the optional station token
      (`run.py --token` or ``UREASIM_TOKEN``), checked at ``hello`` in constant time, a refused
      station disconnected and its console not retrying; the instructor's panel unpaused
- [x] The single-console conversion (session 68, decision 149, As-Built Part LXXXIII): `run.py`'s
      `server` and `station` modes, roles, the station token, the roster and unit assignment
      removed; the loopback bridge, back-pressure, the 5 s watchdog and the engine's process
      refusals kept; ``co2_set`` on the instructor's panel
- [x] The Phase 6 display gaps (session 44, §LXI.2-6): B-5, B-6 / B-7, B-9, B-11, B-16 closed
- [x] `hmi/intro/` and `hmi/startup.py` — the start-up intro and the 100% LOAD start (session 84,
      decision 166, As-Built Part XCVII): the HFC mark and a "Plant Hover Flyby" (a continuous
      360-degree orbit, 32 s a turn, round a stylized wireframe of the HP loop of flow sheets 322-1 and
      322-2, its equipment joined in the sheets' order, flow dots along the arrows) ending on a 100% LOAD
      button, supplied by another AI model and integrated here; scene, flyby, camera, model and sequencer
      Qt-free, `painter.py` and `splash.py` the only Qt; constants in `data/intro.py`, `data/intro_flyby.py`
      and the equipment and connections in `data/intro_plant.py` (the layout is a design choice, not to
      scale). `run.py` builds the engine held at its design seed while the intro plays; the press builds
      the console, connects it and releases the hold with the engine's own `freeze` command
      (`hmi/startup.py`, `data/intro.py` `START_COMMANDS`). `--no-intro` runs the plant from the start
- [x] The start-up intro's six open points closed (session 85, decision 167, As-Built Part XCVII.3-XCVII.9):
      the frame cost cut from 46.8 ms to about 15.5 ms at 125 % scaling (a bitmapped paper, flat caps,
      hairline thin wires, numpy wires held bit-for-bit to the scalar version, a pooled QLineF list, cached
      fonts and a font warm-up); the bridge's staleness watchdog armed strictly only after the first
      packet (`FIRST_PACKET_STALE_MS`); the sections in the console's tab order; the flyby's drawing
      choices signed off; the logo resampled 2x; and a one-to-one test file for every intro module
- [x] The intro's frame rate and a held plant's packet closed (session 87, decision 169, As-Built Part XCIX):
      A-26 - the intro painted on a multisampled `QOpenGLWidget` canvas where a hardware OpenGL 2.0 context
      exists and by the CPU rasterizer elsewhere (`hmi/intro/canvas.py`, `RENDER`, the kill switch
      `UREASIM_INTRO_RENDERER=raster`): main-thread paint 7.5 ms windowed and 8.2 ms fullscreen at 125 %
      scaling (CPU 11.5 and 14.2), 60 fps held through 4 busy processes of 20 logical in both modes and
      fullscreen through 8, windowed not at 8; the fixed-stage layer, the azimuth cache and worker threads
      measured and rejected. A-27 - a plant reset or restored while frozen publishes its rehearsed first tick,
      the plant not stepped (`engine/rehearsal.py`), proved through the real bridge and console at the 5 s
      watchdog; the held start at launch stays silent (decisions 166 and 167). A-28 raised
- [x] The intro's LOAD button (session 90, decision 171, As-Built Part CII): a second pill beside 100% LOAD
      starts the plant from a saved exercise; the start-up controller asks the engine for its exercises, the
      chooser (`hmi/exercise_chooser.py`) opens over the intro, the chosen one is restored and only then the
      plant released, and the hand-over ends on the packet after the release's acceptance; a refused exercise
      reopens the chooser with the engine's reason; Cancel or no exercise takes the intro back to its buttons,
      saying so, nothing started; the engine lists the repository's `scenarios`, shipped and never written,
      beside the instructor's folder, which SAVE writes (`engine/session.py`, `run.py`). A-30 raised
- [x] A-28 and A-30 closed (session 91, decisions 172 and 173, As-Built Part CIII): the server replays no packet
      older than `SNAPSHOT_REPLAY_MAX_AGE_S` (1.0 s) and says ENGINE SILENT, restoring the stored status on the
      next publish; a closed bridge does not reconnect; trip 22.2 named "22.2 (simulator)" (decision 174)

### Phase 7 — Verification
- [x] V1-vs-V1.1 steady-state comparison at 1750 MTPD / 100 % load (session 48, As-Built §LXIV.6):
      every packet leaf for an hour on both engines, 3 084 of 3 188 shared leaves within 1 %, the 104
      others each a decided divergence but 323E011's creep (B-89, accepted)
- [x] Transient comparison: cold start, trip 22.2, HPCC rupture, vacuum break — the runner
      (`tests/phase7/`, sessions 45-46, As-Built §LXII.4) built and the four scenarios run on both
      engines at the fixed 0.1 s step (A-14 closed); the comparison is the process engineer's to read
- [x] B-51 decided and built (session 47, decision 78, As-Built §LXIII.1): the backward pressure
      step on a tick where the explicit one would ring, 328C004 first
- [x] B-83 decided and built (session 47, decision 79, §LXIII.2): SV32064 on the CO2 line
- [x] B-87 traced on both engines (session 47, §LXIII.3); decided and built in session 48 with B-86,
      B-88 and B-39 (decisions 80-83, §LXIV.1-4): the cold start no longer floods 328C004
- [x] Overlay geometry test (zero overlap, per V1's migration procedure; session 48, A-7 decided,
      §LXIV.7)
- [x] B-13 closed (322E002's gate 1.0, already built) and B-82 built — 322E002's tube leak, process
      into the shell; the HPCC rupture re-run on it (session 48, §LXIV.8-9)
- [x] A-18's FAST pace: profiled in session 48 (§LXIV.11), exact caching no gain; decided in
      session 49 (decision 88): as fast as the machine allows
- [x] B-90, B-84, B-81, B-85, B-28 and B-25 decided and built or closed (session 49, decisions
      89-94, As-Built §LXV.1-4)
- [x] B-77 (b), the loop's vapour-inventory node: decided and built in session 49 (decision 95,
      As-Built §LXV.5)
- [x] Trips 21.2, 21.8 and 21.10 on Uhde's application software (A-12): decided and built in
      session 49 (decision 96, §LXV.6); 22.2 V1's — its logic is the Safeguard's, not traced
- [x] The Phase 7 scenarios re-run on B-77 (b), B-81, B-85, B-90 and AC4's trips (session 49,
      §LXV.7)
- [x] B-91 option (a) built (session 50, decision 97, §LXVI.1) and the reactor's boiling cap, B-92
      (decision 102, §LXVI.2)
- [x] B-91: the cold start reaches 79.7 bar a after 16 000 s, still rising, short of the
      137.5-150.5 bar g band (session 50, §LXVI.9) — the remaining sink to the process engineer;
      superseded, B-91 accepted and closed in session 52 (decision 110)
- [x] B-18, B-37 and B-20 decided, built and closed (session 50, decisions 99-101, §LXVI.3-5)
- [x] Trip 21.2's five hand switches and AI-329701 on the overlay screens (session 50, decision 98,
      §LXVI.6)
- [x] The plant DCS's readback of 2026-10-13 applied (session 50, decision 103, §LXVI.7)
- [x] B-93, B-94 and B-95 decided and closed (session 51, decisions 104, 106, 107, §LXVII.1, 4, 5)
- [x] B-91: 322E003 on its own liquor's bubble point and a full sump (session 51, decision 105,
      §LXVII.2); the retained-gas term not built (the node holds that gas already); the start-up
      procedure compared (§LXVII.3)
- [x] B-91: the cold start's fit, 136.04 bar g and tau 1 305 s, against the 137.5-150.5 bar g and
      2 884-4 055 s band (session 51, §LXVII.8) — the plant's procedure or acceptance
      to the process engineer; superseded, B-91 accepted and closed in session 52 (decision 110)
- [x] PV-329203 and PV-329212 on Metso's trims (session 51, decision 108, §LXVII.6); 329D001's
      volume entered (decision 109, §LXVII.7)
- [x] B-96: 323P008's trip on a 2 % hysteresis stand-in (session 52, decision 111, §LXVIII.2)
- [x] B-91 accepted and closed (session 52, decision 110); B-79 (b), solid carbamate, built and
      closed (decision 112, §LXVIII.3)
- [x] Metso's sheets 25-32 read; PV-329202, PV-329208 and LV-329505 on their trims (session 52,
      decision 113, §LXVIII.4-5)
- [x] FV-329401, PV-329204, PV-329207A and PV-329207B on their Metso trims; FV-329409 catalogued on
      IAPWS's density and wired (session 53, decision 116, §LXIX.3-5)
- [x] B-30 decided and built: 323E011 on its dew point, PV-323203 never venting backwards (session
      53, decision 114, §LXIX.1)
- [x] B-22 decided and built: 323F010's bubble point on the live PT-323204; the vacuum break re-run
      without oscillation (session 53, decision 115, §LXIX.2)
- [x] A-6 closed: the ten backgrounds frozen (session 53, decision 117, §LXIX.6)
- [x] The Phase 7 scenarios re-run on session 51's code (§LXVII.8); the vacuum break and the steady
      state on session 53's (§LXIX.2, §LXIX.7), the steady state on session 54's (§LXX.5) and
      session 55's (§LXXI.5)
- [x] B-31 decided and built: the inlets of 323E011, 323E003, 323C005, 328D003 and 328C002 at their
      producers' live temperatures, in departure form (session 54, decision 118, §LXX.2); 708's
      temperature, which no unit computes, raised as B-97
- [x] A-13 closed on its audit test (session 54, decision 119, §LXX.3)
- [x] B-2, B-17, B-45, B-48, B-52, B-72, B-74 and B-78 signed off and closed; Section C empty
      (session 54, decision 120, §LXX.4)
- [x] B-97 decided and built: 708 at 324F002's adiabatic mix of 706 and 924, as its departure from
      the design mix (session 55, decision 121, §LXXI.1)
- [x] UF85 (unit 335) ported, its dosing live on LV-324501A's route; 274 of 274 console bindings
      resolve (session 55, decision 123, §LXXI.2)
- [x] B-1, B-4 and B-12 signed off and closed; Section B empty (session 55, decision 122, §LXXI.3)
- [x] A-3, A-4 and A-5 deleted from `handoff.md`, A-3's rule in `CLAUDE.md` §5;
      `flash_condenser.py` under 600 lines, its gas-node relations in `flash_gas_node.py` (§LXXI.4)
- [x] 323P003's low-level trip searched — AC4 PC23.1.7 / 1.8, the functional diagram and the loop
      summaries draw none — and its NPSH read (3.8 m required, 5 m available); trip 21.2's five hand
      switches typed and TRIP_84_8 traced to the Safeguard SG1's instrument-air trip (session 57,
      §LXXIII.1-2)
- [x] Decision 95's reactor-liquor buffering signed off, the 322E002 / 322E001 liquor gap closed
      (session 57, decision 126, §LXXIII.3)
- [x] The register's planning rows 12-20 pointed at their ported rows; `stripper.py` at 600 lines;
      §3 brought up to date (session 57, §LXXIII.4)
- [x] The vendor archive searched for the open data gaps (session 57, §LXXIII.7-9): 328D003's
      overflow (N12, EL +5352, compartment III) and 323D002's (to 335D004) traced, their rows
      closed; trip 22.2 confirmed absent from AC4 and SG1; LT-329505's upper tap found
- [x] Trip 21.2 shuts XV-322902 (through the Safeguard SG1) and XV-322903 as AC4 PC21.5.1 draws
      them, 320K002's demand to zero while the flag is lost (session 57, decision 127, §LXXIII.7)
- [x] The console revised from the UI-page slides: hover fixed, valve icons replaced by readouts,
      51 page buttons' blocks restored, readouts off the drawing and each other (session 58,
      decision 129, §LXXIV.1)
- [x] The research PDF of 2026-10-16 worked through: the liquid-rated safety valves' gas coefficient
      read and its gap closed (decision 130); five Metso sheets catalogued, not wired; LT-329505's
      upper tap traced (session 58, §LXXIV.2-5)
- [x] HV-323605, PV-323203 and TV-328002 on their Metso sheets, V1's laws on the harness switches,
      each both ways (session 59, decision 131, §LXXV.1)
- [x] The process-deviation notes of `References/scenarios` put to the plant: 78 deviations, 147 of
      191 claimed responses as claimed, the rest classified; A-21, A-22, B-98 and B-99 raised
      (session 59, §LXXV.2-4)
- [x] A-22 (a): a full 323F004 overflows into 323E011, V1's uncapped drum on the harness switch,
      both ways (session 60, decision 132, §LXXVI.1)
- [x] B-98 (b): the backward species step at a heel, V1's explicit step on the harness switches,
      both ways (session 60, decision 133, §LXXVI.2)
- [x] A-21 (b) traced and its remedy prototyped; B-99 (b) measured both ways on two prototypes
      (session 60, §LXXVI.3-4); no crystallisation restriction on the evaporators (decision 134)
- [x] A-21 (b): 322E002's saturation fraction solved with its own melt's bubble pressure on the
      tick, the tear on the synthesis harness's switch, both ways (session 61, decision 135, §LXXVII.1)
- [x] B-99 (b1): 322E003's capacity on its shell's effectiveness, its duty capped at it, V1's flow
      law on the switch, both ways (session 61, decision 136, §LXXVII.2)
- [x] B-101 (b): the vapour draw in the heel's backward species step (session 61, decision 137,
      §LXXVII.3)
- [x] B-100 (b): 323F004 on its geometry and LT-323505 between its taps, measured stable first,
      V1's drum on the switch, both ways (session 61, decision 138, §LXXVII.4); Sections A, B and C
      of `handoff.md` empty again
- [x] Full `pytest` suite green (session 61, 7535 collected; two synthesis pins re-pinned, their file green)
- [x] S1-1.2's conversion traced tick by tick and A-21's option (c) prototyped and measured on
      S1-1.2 and S2-3.1a, scratch only (session 62, §LXXVIII); B-102 and B-103 raised
- [x] B-102 decided (b) and built: 322E001's duty bounded by its shell on the live steam's LMTD
      against the tube side's design profile, a 5e-4 band (session 63, decision 139, §LXXIX.1)
- [x] B-103 built on decision 62's class: LT-322501's full sump held back in the tubes (session 63,
      §LXXIX.2)
- [x] `Scenarios5.md`'s coupled loop transients put to the plant, both waves
      (`tests/phase7/coupled.py`, `run_coupled.py`; session 63, §LXXIX.3-4)
- [x] A-23: the console tests on settings of their own (session 64, §LXXX.1)
- [x] B-104: 322E001's tubes standing full — the ceiling, HV-322605 capped at what the tubes take,
      the submerged share derating the shell and cooling TT-322004 (session 64-65, decision 140,
      §LXXX.2)
- [x] B-105: 323D001's species and temperature into 322E003's wash (session 64, decision 141,
      §LXXX.3)
- [x] B-106: 322E002's melt on the Extended UNIQUAC rise below N/C 3.0 (session 64, decision 142,
      §LXXX.4)
- [x] B-107: 324F003's lost seal admits air (session 64, decision 143, §LXXX.5)
- [x] `stripper.py` and `stripper_sump.py` inside 600 lines: `stripper_kinetics`, `stripper_level`
      split out (session 64, §LXXX.6)
- [x] `Scenarios5.md` re-run on the four, 14 cases, 83 of 165; eight deviations re-run, 16 of 22
      (session 65, §LXXX.7-8)
- [x] B-108: stage 2's temperature on its energy balance where its iteration does not settle
      (session 66, decision 144, §LXXXI.1); LV-324501's selector split out to `melt_route`
- [x] B-109: PT on 322R001 capped where the melt flashes (session 66, decision 145, §LXXXI.2)
- [x] B-110: PFD 308's line from 323P001 to 322E003 on its isometrics, 24.94 s (session 66,
      decision 146, §LXXXI.3)
- [x] B-111: the azeotropic rise added in bar (session 66, decision 147, §LXXXI.4)
- [x] `Scenarios5.md` re-run on the four (session 66, §LXXXI.5)
- [x] B-112: PT on 322R001 on its feed line's PFD drop, 141.3 bar a at the design (session 67,
      decision 148, §LXXXII.1); 322R001 has no transmitter of its own (P&ID 102,
      UD-MR-322-EC-0001)
- [x] Session 66's B-108 to B-111 confirmed as built by the process engineer (session 67)
- [x] As-Built §LXXXII.3's two display-only notes signed off as built, no B-113 (session 67)
- [x] Sessions 62 to 67 committed (session 67)
- [x] Session 68 committed (session 68); the repository has no remote, so nothing is pushed
- [x] The open data gaps searched again in `D:/Work/Urea Simulation`, `D:/Work/Urea Simulation
      Docs` and the vendor archive; LV-328503, LV-328504, HV-329602 and the 323D001 vent on
      Fisher's sheets, HV-329601, PV-329207C and LV-324501A / B on Flowserve's, each wired with
      both sides tested (decision 150); 322E006 on PFD 28's 14 t/h, its UA re-anchored (decision
      151); four data-gap rows closed, 15 open (session 69, As-Built Part LXXXIV)
- [x] Session 69's LV-324501A / B density correction checked (mass capacity on sqrt(rho), not
      inverted), the wording of `CLAUDE.md` §5.7 and decision 150 clarified, and session 69
      committed (`2e4d64c`)
- [x] Every module under `ureasim/` at or below the 600-line target: `control_valves`,
      `unit_323`, `unit_324`, `scrubber`, `engine/command` and `condensing_letdown` split along
      their seams, the lines moved verbatim and every moved name re-exported; a test file for each
      new module (session 70, decision 152, As-Built Part LXXXV)
- [x] An external report on five data-gap rows audited against the code and the archives;
      322C001's bottom head volume and the urea-melt Henry constant closed, the Neldisc row
      kept linear and annotated; 13 data gaps open (session 71, decision 153, As-Built Part
      LXXXVI)
- [x] 322E001 on its 2,950-tube replacement, V1's bundle on the harness switch (decision 154); the
      plugged tubes of 322E002, 322E003 and 323E010 derating their conductances (decision 155);
      AI-329701's range and five tunings from the faceplate photographs (decision 156); the
      `Scenarios6.docx` survey, 45 of 71; B-113 to B-116 raised; 12 data gaps open (session 72,
      As-Built Part LXXXVII)
- [x] The full suite green on session 72's changes, every group (2026-10-28): the stream inspector
      rounding as V1's ``toFixed`` (a defect the audit found), the synthesis harness keeping the
      LP side's session-72 changes on its switches, the design-seed tests on the clean bundles
      (`build_plant(plugged=False)`), the documented values the DCS rows moved re-measured
- [x] B-113 to B-116 decided and built (decisions 157 to 160); the dynamic audits built,
      `tests/engine/test_dynamic_audit.py`, 14 tests — the holdups' balances integrated over a
      disturbance, the trip paths and the updated controllers' transfers, a FAST shutdown with no
      node ringing, freeze-snapshot-reload-resume under FAST and a seeded malfunction fuzz; their
      one finding, B-117, signed off as built; step responses measured on TIC-328008's row (no plant
      trend of the loop to fit); `Scenarios6.docx` 47 of 71; 11 data gaps open (sessions 73 and 74,
      As-Built Part LXXXVIII)
- [x] B-119 decided (b) and built: 323F010 drains on its own head through N2, the premise read from
      the leg's isometric and the tank's general assembly (decision 161); V1's leg on the harnesses'
      switch, asserted from both sides; a pasted analysis of B-118 to B-121 checked and measured,
      105 % verified with FIC-328402 raised 10 % (session 78, As-Built Part XCI)
- [x] B-122 decided (b) and built: 323F010's pressure step solved itself on every tick its holdup
      boils (decision 162), the dynamic audit's limit of two successive reversals restored for
      every node, the synthesis loop's harness kept on the linearised step; B-121 and B-118
      measured against Book2's bands; B-123 raised and signed off as built, V1's thermo memo kept
      (decision 163) (session 79, As-Built Part XCII)
- [x] Every controller and hand station given a load relation (72 entries, set against Book2's
      four bands) and the schedule run from 70 to 115 % on both objectives with slow supervisory
      trims, then re-held at 100, 105 and 110 %: 100 % verified on both objectives and 105 % on the
      steam objective; B-118 and B-120 updated; B-121 closed on option (a) (decision 164); the
      load-optimisation workbook rebuilt with the schedule; the Sonnet + Opus advisor workflow added
      to `CLAUDE.md` and `.claude/settings.json` (session 80, As-Built Part XCIII)
- [x] B-118's and B-120's narrowed option (b) measured as scratch patches at Book2's 92.3 and 111 %
      bands; neither holds, and no relation changed. The Phase 7 cold start was re-run, and its trip
      22.2 on the committed engine raised as B-124. V1's moved source tree raised as A-24, and
      CLAUDE.md §4 pointed at the archive's new home (session 81, As-Built Part XCIV)
- [x] A-24 closed: V1's source tree named at `E:\Simulator\Urea Simulation` (decision 165);
      `tests/equivalence/v1_loader.py`, the Phase 7 runner's V1 side, two tools' defaults and
      CLAUDE.md §0 and §4 follow it; the boot pin's test and the stripper's equivalence
      module run on it, 102 passed and none skipped (session 82, As-Built §XCV.1)
- [x] B-124 bisected on option (b): 15e66c2 moved the cold start, and 322E002's low-N/C branch
      (decisions 142, 147) alone restores it to 3 600 s; B-118's and B-120's option (b) measured on a TT-322002
      prototype at Book2's 92.3 and 111 % bands, no band held and no relation changed (session 82,
      As-Built §XCV.2-3)
- [x] B-124's evidence gathered (no melt datum below N/C 2.6; the plant's start-up NH3-rich) and the
      16 000 s cold start fitted; B-118's 322E001 and 322R001 traced at 92.3 %; B-120's 322E003 capacity
      measured on the vendor's 8 000 kW rating; no band held, no relation changed (session 83,
      As-Built Part XCVI)
- [x] B-124 closed on option (a): 322E002's low-N/C branch kept and decision 110's cold-start record
      re-baselined on the committed engine (decision 168); 322R001's fill probed (LT-322504's narrow
      band; the backup above the lip moved with 322E001's shell bound (decision 139, B-102, in 15e66c2): with it off LT-322504 peaks at 91.2 % at 7 740 s, while B-103/B-104 and the bundle alone do not restore it); FT-329403 checked at the design point (stream 901, 60.85 t/h); B-118 and B-120
      measured under active closed-loop trims at 92.3 and 111 %, no 1 h hold passed, no relation changed
      (session 86, As-Built Part XCVIII)
- [x] The load workbook's gaps researched and the workbook finalized on the evidence (session 88, As-Built
      Part C): Book2's load dwells at 60.7, 69.3 and 80.4 % found, the licensor's start-up and shutdown
      through 70 % and 4.1.5.9's load rules read; plant values at 70, 80 and 95 %, a band sheet and a gap
      register added; no engine value changed, no decision taken
- [x] The routes to every open gap researched (session 89, As-Built Part CI): the S-Disc table of Valmet's
      2SL120EN checked against the five balanced Neldiscs' sheets (within 1.3 %), session 71's "30 %" traced to a
      family mismatch; the vendor TOC and the urea loop diagrams searched; decision 170 built, data gap 7
      narrowed to the nine conventional valves, 29 pins re-measured
- [x] The open items taken up again (session 91, As-Built Part CIII): A-29 run on `E:` and closed (20 tests' decided pins
      re-pinned on decision 170); data gaps 6 and 11 closed by decision (174, 175); B-120 option (b) measured at
      70-111 % (decision 176), the build of the gain waiting on the process engineer; LT-329505's lower tap and
      LT-324501's tap traced
- [x] Decision 178 built (session 91, As-Built §CIII.10): the nine conventional Neldiscs on Valmet's L-series Cv rows,
      data gap 7 closed, the suite re-pinned; decision 179, the dynamic audit applying decision 163 on 323F010;
      B-118 at Book2's 69.3 % dwell set points, trip 22.1 on the ramp in both arms (§CIII.12)
- [x] B-118 re-run at Book2's 69.3 % dwell on the process engineer's corrected boundary (session 92, As-Built Part CIV):
      HIC-322605 on its anchor (43.27 %) or by the board operator, HIC-322602 on the spindle solve, MASTER-329207 on
      PT-329207's dwell median; all six arms trip 22.1 before the hold, the acceptance test not met; Book2's own descent
      read; no relation changed
- [x] `Data/Trends 511.2026` read (session 93, As-Built Part CV): the plant's 5 November 2026 turndown from 75
      photographs, tables transcribed and traces digitized with QA; data gaps 1, 3, 4 and 9 annotated, decision 178's
      valves checked, a 322F001 friction-share prototype measured on twelve B-118 arms; no relation changed;
      the options decided 2026-11-08 (decision 180), B-118 narrowed to 322R001's heat balance
- [x] B-118's term audit (session 94, As-Built Part CVI): 322R001's turndown budget decomposed, the carbamate
      source found responsible, four seed-exact prototypes measured; no relation changed; option (a) decided
      2026-11-09 (decision 181), S2 and slip gain 0 unbundled from B-118
- [x] B-118's candidate bundle verified on the five holds (session 95, As-Built Part CVII): P1 rebased on the
      CO2 demand ratio, the seed identical, the handles as departures; 92.3 % passes, 90.5 % trip-free out of band, 74.4,
      69.3 and 68.9 % fail on 322E002's collapse under P1 and trip 22.2; no relation changed; options open

