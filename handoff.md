# handoff.md — Open Issues for the Human Engineer

Tracker for `Urea Simulator V1.1`. Retains **open** items only. Close an item by deleting it and
recording the closure in `Urea OTS — As-Built Mathematical Reference.md`.

**Last updated:** 2026-11-04 (session 83: Session 82 committed (6ac6f08); B-124's evidence gathered — no melt datum below N/C 2.6 in either archive, the plant's 3 June 2025 start-up NH3-rich (AY-322701 3.69-3.16, no overshoot) and its SOP feeding N/C 3.0 to the reactor's overflow — and the full cold start run: with the branch off no trip 22.2, tau 1350 s, dead time 540 s, final 137.45 bar g, 322R001 not full by 16 000 s (LT-322504 36 % at 8 000 s, where session 52 was full); on the SOP's ratio with the branch on, trip 22.2 at 5 863 s; no source bounds the branch, so (a) is recommended. B-118: at 92.3 % the HP steam runs 14-20 % above Book2's at both loads and 322E001's bottoms 10 K hot; the bottoms term alone is not the re-anchoring. B-120: Uhde's datasheet rates 322E003 at 8 000 kW, 1.49 times the PFD; with that margin 322E003 vents nothing at 111 %, and the loop runs NH3-rich on its fixed ratio. LT-329501 cannot reach Book2's levels (322F001's suction proportional to the level). No band held, and no relation changed (As-Built Part XCVI). Session 82: A-24 closed — the process engineer named `E:\Simulator\Urea Simulation` V1's source tree (decision 165); `tests/equivalence/v1_loader.py`, the Phase 7 runner's V1 side, two tools' defaults and CLAUDE.md §0 and §4 follow it, and the boot pin's test and the stripper's equivalence module run on it (102 passed, none skipped). B-124 bisected on option (b): 15e66c2 moved the cold start, and within it 322E002's low-N/C branch (decisions 142, 147) alone restores it: with that switch off HEAD returns to session 52's answer to 3 600 s and 22.2 is not reached, while a prototype taking the rise at the melt's live temperature does not restore it. B-118 and B-120's option (b) measured on a TT-322002 prototype at Book2's 92.3 and 111 % bands: the liquor matches the plant at 92.3 % but acts only through its saturation fraction; the 92.3 % miss is in 322R001 and 322E001 (f held at 1 still gives 178.9 and 176.7 C); at 111 % 322E003's capacity leaves 4.4 t/h uncondensed. No band held, and no relation changed. Section A none open, Section B three open; 11 data gaps remain (As-Built Part XCV). Session 81: B-118's and B-120's narrowed option (b) measured as scratch patches at Book2's 92.3 and 111 % bands; neither band held, and no relation changed. On the turndown ramp 322E001's NH3 overhead fraction stays flat; the excursion is carried by the reactor overflow's NH3, as 322R001's holdup drains at a fixed HIC-322605 and 322F001's suction halves at its design spindle, both operator handles. At the plant's 92.3 % set points 322E003's liquor has a bubble pressure 35.4 bar above the plant's PT-329201 at AY-322701 3.25, 30.2 bar of it temperature, because TT-322002 follows the tempered water to 174-178 C where the plant's holds 166.75 C. A 40 bar margin removes the saturation venting but leaves the reactor cold (TT-322005 178.9 C, X 49.9 %). At 111 %, near the plant's 322E003 level, the sump does not drain and the H/C slip is small; 322E003 vents 3.5 t/h, its liquor 13 K hotter than the plant's, as at 92.3 %. The Phase 7 cold start was found tripping 22.2 at 3 322 s on the committed engine (B-124 raised). V1's source tree and the References archive were moved (A-24 raised, CLAUDE.md §4). Section A one open, Section B three open; 11 data gaps remain (As-Built Part XCIV). Session 80: every controller and hand station given a load relation (72 entries) and the schedule run from 70 to 115 % on both objectives with slow supervisory trims, then re-held at 100, 105 and 110 % on the resume directive — 100 % verified on both objectives and 105 % on the steam objective, no steady state below 100 % or at 110-115 %; B-118 updated — the excursion is 322E001's top gas at its design shell pressure, FFIC-321404's ratio on the engine's basis (the plant's 2.115 is 2.05 here), the turndown unchanged with every controller scheduled; B-120 updated — no oscillation at 168 C with AT-322701 fed back but the loop NH3-lean, the mode on load steps, and at 110 % the guard's stripper cut driving the loop NH3-lean to trip 22.2; B-121 closed on option (a), PIC-323202 and the unit 328 pair operator moves (`project.md` decision 164); Section B two open; 11 data gaps remain (As-Built Part XCIII). Session 79: B-122 decided (b), built and closed — 323F010's pressure step solved itself on every tick its holdup boils (`project.md` decision 162), the dynamic audit's limit of two restored for every node; B-121 traced to the LP section's vents, 323E003's 321 and 323E011's 702 scrubbed into 343, unit 328's relations matching Book2, a PIC-323202 set point measured as the option; B-118's ramp excursion traced to the reactor's real feed N/C, its NH3 partition and conversion slip under 0.01, and 322E003's vent at the plant's 92 % set points to its saturation fraction; B-123 raised — the thermo memo's bin edges on 323F010 — and signed off as built, option (a), on 2026-10-31 (decision 163); the synthesis loop's harness kept on the linearised step; Section B three open; 11 data gaps remain (As-Built Part XCII). Session 78: a pasted analysis of B-118 to B-121 checked against the code and measured as scratch patches — its two B-118 mechanisms are not the engine's, and neither of its changes, nor V1's conversion-deficit slip switched off, holds 80 or 90 %; the stripper's slip gain measured as B-120's driver, no gain giving a steady hold; at 105 % FIC-328402 raised 10 % passes once 328C003 settles (X121F2, now the workbook's 105 % column), the analysis's 4.5 % does not; two errors in session 77's R105f record corrected — FIC-328402 in m3/h, 328C003's level falling; 323F010's barometric leg found on its isometric (9.645 m against the 8.98 m full-vacuum column) and B-119 decided (b), built and closed — 323F010 draining on its own head, at its throughput level from 90 to 115 %, the design point unchanged (`project.md` decision 161); B-121 kept open for (b) by the process engineer; B-122 raised — 323F010's boil-off spiking under LV-322501's blow-through surge, the dynamic audit's one exception; Section B four open; 11 data gaps remain (As-Built Part XCI). Session 77: the load-optimisation workbook retried on the process engineer's control document, its schedule on the live load and HIC-322605 operated by hand on the solution 322R001 discharges — 100 % verified on both objectives, 105 % near-steady, no steady state elsewhere; B-118 and B-119 updated with the measurements, B-121 raised — unit 328's ammonia water at 105 % — Section B four open; 11 data gaps remain (As-Built Part XC). Sessions 75 and 76: the load range 70-115 % studied on the committed engine for the load-optimisation workbook, no relation changed; B-118 — below 100 % load no steady state on the plant's reactor window, the plant's own 92 % set points included — B-119 — 323F010's barometric leg fills above about 105 % and drains below design — and B-120 — a 2-8 K cut of TT-322004 at design load starts a ~1.1 h loop oscillation — raised, Section B three open; 11 data gaps remain (As-Built Part LXXXIX). Sessions 73 and 74: B-113 decided (b) and built — the plugged tubes' conductances re-anchored on the bundle in service (`project.md` decision 157); B-114 measured and signed off as built — SV32351 / SV32352 lift at their 6.010 bar a set when LV-322501 fails open, the survey's 5 s samples had missed them (decision 158); B-115 decided (a), the bleeds on the 1750 MTPD basis (decision 159); B-116 built and signed off, TIC-328008 and FFIC-335406 on their faceplates (decision 160); all four closed; the dynamic audits built (`tests/engine/test_dynamic_audit.py`, 14 tests) and their one finding, B-117, signed off as built; `Scenarios6.docx` 47 of 71; the bleed valves' row closed and the tuning row narrowed to FIC-335405; 11 data gaps remain, Sections A, B and C empty (As-Built Part LXXXVIII). Session 72: 322E001 replaced by its 2,950-tube Stamicarbon / Resta bundle, V1's 2,600 tubes on the harness switch (`project.md` decision 154); the turnaround's plugged tubes in 322E002, 322E003 and 323E010 derating their conductances (decision 155); the photographs of `References/Gaps Closure/Gaps` read — AI-329701's range closed, five tuning rows wired (decision 156), the bleed valves' strokes found; `Scenarios6.docx` put to the plant, 45 of 71 claims as claimed; B-113 (the plugged seed), B-114 (LV-322501's failure case), B-115 (the bleeds) and B-116 (TIC-328008, FFIC-335406) raised; 12 data gaps remain; the full suite green (As-Built Part LXXXVII). Session 71: an external report on five data-gap rows audited against the code and the archives — 322C001's bottom head volume closed (the drawing's dimensions on DIN 28013's geometry, three methods within 1.2 %) and the urea-melt Henry constant closed as a quantity no source holds, both by the process engineer's decision (`project.md` decision 153); the Neldisc row annotated and kept linear (the bulletins in no archive, the chord's departure measured on the sheets' own points); 13 data gaps remain, Sections A, B and C empty (As-Built Part LXXXVI). Session 70: the housekeeping split — every module under `ureasim/` at or below the 600-line target, the moved lines verbatim and re-exported, no relation touched (`project.md` decision 152, As-Built Part LXXXV); session 69's LV-324501A / B density correction checked and found right; no item opened or closed, 15 data gaps remain, Sections A, B and C empty. Session 69: the open data gaps searched again in `D:/Work/Urea Simulation`, `D:/Work/Urea Simulation Docs` and the vendor archive — four closed: Fisher's file UD-MR-G00-DZ-0014 found with LV-328503, LV-328504, HV-329602 and the 323D001 vent (TV-323013, the port's PV-323202), Flowserve's Pos. 65, 76, 148 and 149 with HV-329601, PV-329207C and LV-324501A / B, all seven wired on their sheets (`project.md` decision 150), and PFD 28's 14 t/h of cooling water through 322E006 with its UA re-anchored (decision 151); As-Built Part LXXXIV; 15 data gaps remain, Sections A, B and C empty. Session 68: the simulator converted to a single console (`project.md` decision 149, As-Built Part LXXXIII) — the multi-station roles, the station token, the roster and section assignment removed, so A-2's and A-8's mechanisms are retired; no item opened, Sections A, B and C empty. Session 67: B-112 decided (a) and built — PT on 322R001 on its feed line's PFD drop, 144.2 - 141.3 at the seed's feed, reading PFD 203/207's 141.3 bar a at the design and moving one bar per bar of PT-329201 where B-109's cap binds (decision 148) — and closed; P&ID 102 and loop summary UD-MR-322-EC-0001 searched, 322R001 carries no pressure transmitter of its own; session 66's B-108 to B-111 confirmed as built; Sections A, B and C empty, the open data gaps the only open items (As-Built Part LXXXII). Session 66: B-108 decided and built — stage 2's temperature solved on its energy balance where its iteration does not settle (decision 144) — B-109 — PT on 322R001 capped where the melt flashes, at PT-329201 plus its 3.5 bar head (decision 145) — B-110 — PFD 308's line on its isometrics, 47.8 m, 24.94 s (decision 146) — and B-111 — the azeotropic rise added in bar (decision 147) — all closed; `Scenarios5.md` re-run, 82 of 165 claims as claimed, the four tripping cases tripping 30 to 95 s later (As-Built Part LXXXI); B-112 (PT on 322R001 on V1's feed-line law) raised. Sessions 64 and 65: A-23 fixed — the console tests on settings of their own — and closed; B-104 decided and built — 322E001's tubes standing full, the held liquor capped at 8 689 kg, HV-322605 capped at what the tubes take and the reactor keeping the rest, the submerged share derating the shell and cooling TT-322004 toward 132.7 C (decision 140) — B-105 — 323D001's species and temperature carried into 322E003's wash (decision 141) — B-106 — 322E002's melt bubbling on the Extended UNIQUAC model's rise below N/C 3.0 (decision 142) — and B-107 — 324F003's lost seal admitting air on LV-324501A's blow-through law (decision 143) — all closed; `Scenarios5.md` re-run, 83 of 165 claims as claimed (As-Built Part LXXX); B-108 (stage 2's fixed point at its 1 kg heel), B-109 (PT on 322R001 reading the melt's bubble pressure), B-110 (308's line transit) and B-111 (B-106's fast trips) raised. Session 63: B-102 decided (b) and built — 322E001's duty bounded by its shell on the live steam's LMTD against the tube side's design profile, a 5e-4 band (decision 139) — and closed; B-103 built on decision 62's class — LT-322501's full sump held back in the tubes — and closed; `Scenarios5.md`'s coupled loop transients put to the plant, 74 of 152 claims as claimed (As-Built Part LXXIX); B-104 (the stripper flooded into its tubes), B-105 (the LPCC's water not carried into 322E003), B-106 (low N/C's bubble pressure reaching the loop only as a ceiling), B-107 (324F003's lost seal admits no air) and A-23 (the trend-window test reads the console's own settings) raised. Session 62: S1-1.2's conversion traced — it falls while HV-322605 drains the reactor, then rides a slow oscillation of the loop's chemistry, the stripper's H/C slip keeping the drained ammonia in the loop; A-21's option (c), the stripper's overhead bounded by its shell, prototyped and measured on S1-1.2 and S2-3.1a, no source changed; B-102 (322E001's duty not bounded by its shell) and B-103 (LT-322501's clamp deletes a full sump's excess) raised; 322E001's service U logged as an open data gap. Session 61: A-21 decided (b) — 322E002's saturation fraction solved with its own melt's bubble pressure on the tick (decision 135); B-99 decided (b1) — 322E003's capacity on its shell's effectiveness, its duty capped at it (decision 136); B-101 decided (b) — the vapour draw in the heel's backward species step (decision 137); B-100 decided (b), measured stable and built — 323F004 on its geometry, LT-323505 between its taps (decision 138); all four built and closed, Sections A, B and C empty, the open data gaps the only open items. Session 60: A-22 decided (a) and built — a full 323F004 overflows into 323E011 (decision 132) — and closed; B-98 decided (b) and built — the backward species step at a heel (decision 133) — and closed; no crystallisation restriction on the evaporators (decision 134); A-21 traced to B-91's fraction ringing a tick late on 322E002's melt, the fraction solved on the tick prototyped and measured holding the loop; B-99 measured both ways on two prototypes; B-100 (323F004's holdup against its drum) and B-101 (the vapour draw at a heel) raised. Session 59: HV-323605, PV-323203 and TV-328002 wired on their Metso sheets (decision 131); the process-deviation notes of `References/scenarios` put to the plant — 78 deviations, 147 of 191 claimed responses as claimed (As-Built §LXXV.3) — and A-21, A-22, B-98 and B-99 raised from what differs. Session 58: the research PDF of 2026-10-16 worked through against the archive — the liquid-rated safety valves' gas coefficient read from Sempell's sheets and its row closed (decision 130, 0.922 where 0.917 was assumed); five more Metso sizing sheets found and catalogued (HV-323605, PV-323203, TV-328002, PV-323202A / B), not wired; LT-329505's upper tap traced to its transmitter; the PDF's other claims checked and recorded; the console revised from the UI-page slides (decision 129). Session 57, decided: decision 127 confirmed as built, the open data gaps accepted as the final V1.1 ledger, decision 128. Session 57, continued: the vendor archive searched for the open data gaps — 328D003's and 323D002's overflows traced and their rows closed, XV-322902's command traced through the Safeguard SG1 and trip 21.2's shutting of XV-322902 and XV-322903 built (decision 127), trip 22.2's absence from AC4 and SG1 confirmed, LT-329505's upper tap found. Session 57: 323P003's low-level trip searched — AC4, the functional diagram and the loop summaries draw none — and its NPSH read, the 323D002 row narrowed to the seal pot's drain; trip 21.2's five hand switches typed from their loop summaries and TRIP_84_8_FLAG1 traced to the Safeguard SG1's instrument-air trip; decision 95's reactor-liquor buffering signed off and its data gap closed. Session 56: A-8 signed off — unit assignment by plant section, no per-tag locking — and closed; A-2 closed on an optional station token, the multi-station deployment supported and the instructor's panel unpaused; Sections A, B and C empty, the open data gaps the only open items. Session 55: B-97 decided — 708 at 324F002's adiabatic discharge temperature, in departure form — built and closed; UF85 (unit 335) ported and dosing live on LV-324501A's route, decided, every console binding resolving; B-1, B-4 and B-12 signed off and closed, Section B empty; the closed A-3, A-4 and A-5 deleted, A-3's rule in `CLAUDE.md` §5; 323E011's gas-node relations split out of `flash_condenser`. Session 54: B-31 decided — every LP condenser's, 323C005's, 328D003's and 328C002's inlet at its producer's live temperature as its departure from the producer's design — built and closed, 708's temperature raised as B-97; A-13 closed on its audit test; B-2, B-17, B-45, B-48, B-52, B-72, B-74 and B-78 signed off and closed; Section C empty. Session 53: B-30 decided — 323E011 on its dew point, PV-323203 never venting backwards — built and closed; B-22 decided — 323F010's bubble point on the live PT-323204 — built and closed; A-6 closed, the backgrounds frozen; FV-329401, PV-329204, PV-329207A / B on their Metso trims and FV-329409 catalogued and wired, its data gap closed. Session 52: B-91 accepted and closed; B-96 decided — 323P008's trip on a 2 % hysteresis stand-in — and closed; B-79 (b) built, solid carbamate on Egan, Potts and Potts, and closed; Metso's sheets 25-32 read, PV-329202 and PV-329208 on their trims, LV-329505 on Flowserve's; FV-329401, PV-329204, PV-329207A / B catalogued, not wired. Session 51: B-94, B-93, B-95 closed; 322E003 on its own liquor; the Metso chests PV-329203 / 212)
**Section A** — issues created by the V1.1 rewrite.
**Section B** — physics gaps inherited from V1 that the rewrite must carry forward, not silently
lose. These were open in `D:\Work\Urea Simulation\handoff.md` at the time of the fork.
**Section C** — calibration deferrals: places where the port reproduces V1 knowingly and the
correction is deferred to a re-tuning pass after the Phase 7 validation against V1.

## The closure schedule (the process engineer, 2026-09-30)

Every open item has a phase in which it is closed. Items raised later are scheduled when raised.

| phase | items |
|---|---|
| **4 — re-opened in session 30** | The process engineer re-opened Phase 4 on 2026-10-01 (`project.md` decision 35): unit 324 and the steam system are ported before the scheduler, which is built on the completed plant's data flow. Unit 324, the steam system and UF85 (unit 335, session 55, decision 123) are ported: Phase 4's physical plant is complete. A-13 closed in session 54 on its audit test (`tests/engine/test_check_valve_audit.py`; the rule stands); the data hunt's open ends — three HP angle valves' CONVAL sets, the valves no vendor set lists. Done in session 38: B-71 and B-73 decided and built, closed — the condensers' NH3 and CO2 vent on V1's ratio where the design back-pressure exceeds the PFD's partial pressure and on B-67's addition where it is below (`vacuum_condenser.vent_moles`; 324E005 V1's on every inlet, 324E007's CO2 on the ratio: 30.74 / 31.27 kg/h at -1 / +1 % CO2 where the addition gave 23.81 / 37.51); the motive steam on HV-329605 / HV-329606's vendor gas sizing between the live LP header and the nozzles' pressure solved on the flow (`vacuum_train.motive_ratio`), FV-329401 on V1's butterfly law between the live header and 328C004's bottom (`FlowLoop.step(pressure_ratio=)`, `second_desorber.fv_329401_pressure_ratio`), XV-322915's flood choked on 329D009's live header (`vent_line.flood_steam_kgh`) — on the network with the HPCC's raising lost the LP header bottoms at 3.66 bar a and recovers to 4.09 where it fell to 2.11, no ringing; B-72 and B-74 decided as Phase 7 Calibration Deferrals, moved to Section C. Done in session 37: B-67, B-68, B-69 and B-70 decided and built, closed — the condensers' NH3 and CO2 vent on additive departures (`vacuum_condenser.vent_moles`; every equivalence against V1's module with the switch, `tests/equivalence/b67_switch.py`; 324E007 no longer vents its inlet in a 323P003 trip: V1's train 217 kg/h to atmosphere, the port's 30.2); the steam network ported (`units/steam/`: `drums`, `steam_valves`, `header_control`, `steam_network`; `data/unit_329.py`, `data/unit_329_network.py`, `thermo/water_steam.py`) — V1's ``step_steam`` transcribed with nine switches, every switch off ``==`` V1 executed, every switch on ``==`` the port; every simulated user live on its header and the rest at their PFD rows (B-68), each unit's draw on its PFD row by its live ratio (decision 47's class); the LP header at 4.0 bar g (B-69, V1's); each superheated inlet boiling its drum's water, 913 flashing into the LP header, 959 blowing down, no floor (B-70); Flowserve's trims on PV-329205A / B and LV-329502 / 503 / 504 (decision 23; LV-329503's and LV-329504's normal capacities calculated by IEC 60534-2-1, the calculation reproducing every capacity Flowserve prints to 0.04 %), the letdowns choking on their condensate (decision 31); the drums' water over their vessels and the levels between their taps (329D005's and 329D009's GAs read), a 1 kg heel and an overflow (decisions 33, 11); the gains on span (decisions 10, 21); trip 21.2 on PIC-329204 and HV-329601 as Uhde's functional diagram draws it (decisions 26, 27, 39; UD-MR-329-FF-0002 read); the drums' safety valves on Sempell's certified capacities (decision 32; their orifice selections read); HV-329601, PV-329207A / C and HV-329602 wide open on their loop summaries' maximum cases where V1 gives literal coefficients (§4); PV-329207A / C's 3 % cut-off measured chattering, not wired; 322E002's datasheet read (44 900 kW); B-71 to B-74 raised. Done in session 36: B-65 and B-66 decided and built, closed — the cold ends the vacuums read lagged on their tubes' water residence (`VacuumTrain.cold_end_c`; 324E002 11.54 s, 324E005 7.67 s, 324E006 3.12 s from the datasheets' tubes and the PFD's water — the 11.6 s session 35 quoted was a rounding of 11.55 on a 995 kg/m3 density), so a 323P003 trip no longer pulses (V1's tear: 335 pulses and 9.8 t/h to atmosphere in two minutes; the port: none, under 50 kg/h); 324E006's shell a live vacuum node on its name plate's 0.542 m3 (UD-AU-324-DZ-0005-008, read from the scan), so a lost 324E006 drives the shell to 1.0 bar a in 2.4 s, 324F004 breaks and stage 2's vacuum is lost to 0.259 bar a in two minutes, PIC-324203 closing its bleed against it, no ringing; the water back, the shell recovers in two and a half minutes; B-67 raised; the steam system surveyed (As-Built Part LIII: V1's `steam_system.py`, the PFD's steam block closed on IAPWS, 322E001's datasheet, the unit 329 loop summaries and Flowserve's Pos. 68-70, 74, 75 read from the scans — LV-329502 / 503 / 504 and PV-329205A / B are Valtek globes with vendor trims, the butterflies have none), B-68, B-69 and B-70 raised. Done in session 35: B-63, B-64 and B-24 decided and built, closed — stage 2 takes its feed at the strength its leg drains (`second_evaporator.leg_urea_strength`, anchored; a 323P003 trip no longer boils the leg as water: stage 2 finishes the 96 % melt and holds 1040 kg at 98.49 % and 165.75 C, never below 140 C); the PFD's 1220 and 180 kg/h are the train's motive and the nozzle pressure's anchor; 323F010's liquor boils past its bubble point at the live PT-323204 (`holdup_boil.liquor_boil`), its Calibration Deferral removed; the vacuum train ported (`units/evaporation/vacuum_train.py`, `data/unit_324_train.py`, bit-exact against V1's executed ``vacuum_train_324``), HV-329605 / HV-329606 on their vendor trims (69.06 / 80.16 %); the user's 324F006 / 324F007 are not plant tags (the archive's TOC, the P&IDs and the PFD carry 324F001-324F005); B-65 and B-66 raised. Done in session 34: B-61 and B-62 decided and built, closed — every ejector map's capacity anchored on the PFD's design load (K 0.919 for 324F004, 0.336 for 324F002, 0.497 for 324F005; the vendor duties kept as margin), 324F002's map wired into stage 1; a separator's held melt boils past its own boiling point (`units/evaporation/holdup_boil.py`), evaluated at the trial vacuum inside the implicit pressure step; stage 2, 324E003 / 324F003, ported (`units/evaporation/second_evaporator.py`, bit-exact tick by tick against the switched transcription, eight departures both ways: B-61, B-62, B-58, decisions 20, 10 / 21, 23, 33 — 324F003 on its drawing's 10.7 m3, read from UD-AU-324-DZ-0008-001 — and 11); LV-324501's selector ported without UF85; B-63 and B-64 raised; `CLAUDE.md` §4 mandates `References\` and every subfolder, then the vendor archive, for every datum. Done in session 33: B-57, B-58, B-59 and B-60 decided and built, closed — the ejectors' maps synthesized on their throats and vendor duty points (`units/evaporation/ejector_map.py`, `ejector_gas_dynamics.py`), the melt on UNIQUAC refitted to the PFD with the non-volatile ceiling (`thermo/urea_melt.py`), XV-322915 with no operator open (the overlay's decided edits, `keyswitch_set`), the flood on the valve's rated 1000 kg/h of 9 bar a steam; unit 324's four vacuum valves read and catalogued; B-61 raised; the melt's refit also confirmed on Uhde's own urea-water chart for Helwan (UD-VT-G00-DC-0003 Figure 15, digitised); stage 1, 324E001 / 324F001, ported (`units/evaporation/first_evaporator.py`, bit-exact tick by tick against the switched transcription, six departures both ways, the pull an argument); B-62 raised. Done in session 32: B-56 decided and built, closed — I 22.1 on AC4's PC22.5.1 (`vent_line.xv_322915_open`: no latch, HS-322915 a maintained keyswitch); B-57's decision met an archive with no curve (every Körting and Uhde ejector document read, §XLVIII.2); the melt's equilibrium ported (`thermo/urea_melt.py`, bit-exact) and checked against the PFD's own water activity (B-58 raised); the condensers as nodes ported (`units/evaporation/condenser_node.py`, bit-exact); the stages surveyed. Done in session 31: B-54, B-55 and B-19 decided and built, closed — 322E006 ported on its datasheet UA (`units/absorption/feed_cooler.py`), XV-322915's flood in the vent line with trip 22.1 on TI-322015 (`vent_line.py`), HV-322604's letdown flashed onto the carbamate liquor it condenses (`thermo/condensing_letdown.py`); unit 324 surveyed (B-57 raised, the ejector data located) and its four vacuum condensers ported (`units/evaporation/vacuum_condenser.py`, bit-exact). Done in session 30: A-16's two liquid-rated valves decided (option b, an assumed gas coefficient logged in Open data gaps) and built on 323D011 and 328D001; 322C001 ported (`units/absorption/`), SV32253 on the same class. Done in session 29: B-46, B-47 and B-53 decided and built, closed — every letdown flashes where its downstream condition warrants it (LV-322501 on Uhde's CONVAL sheet, read); 328C003 and 328C002 relieve through their certified safety valves, the relief law in `core/relief.py`; 328D001 the vendor's 5500 l with its heads, LI-328501 across its taps. The relief nodes the flowsheet must wire, and the two liquid-rated valves, move to A-16 (Phase 5). Done in session 28: 328D001 and 328E004 ported, unit 328 closed; decisions 28-30 (328E004 held above its cooling water, the vent on 323E011's live pressure, 328C002's overflow into the drum — decided, built); B-52 kept as V1 (Section C); B-53 raised. Done in session 27: B-49 and B-50 (FFIC-329401 a ratio station; LIC-328505 on FIC-328406, 741 drawn from 328C004 — decided, built, closed); B-48 kept as V1, deferred to Phase 7; B-51 deferred to the solver review. Done in session 26: the 323E002 and 323E010 chest anchors, the chest cascades on span, B-44's vendor valves (all decided, built, closed); Flowserve's and CCI's sheets read in full; 328C003 and 328E021 ported; decision 24, the liquid pays what boils, built on 328C003 and 328C002; every urea-plant safety valve and rupture disc read and catalogued; 328C004 ported, FFIC-329401 on 735 (B-39's ratio, decided and built). Done in session 25: A-9 and B-21 (decided, built, closed); B-2 measured at the stage level (its plant-level measurement moves to Phase 5); the 323E002 and 323E010 chest pressures found (the re-anchoring is B-23's and the gap's decision); Henry constants on a urea-melt basis searched, none found (B-1) |
| **5 — engine and scheduler** (the scheduler after Phase 4) | **Session 68 (As-Built Part LXXXIII):** the transport serves one loopback console with no role, token or section check (decision 149); A-2 and A-8 superseded and retired. **Session 44 (As-Built Part LXI):** B-51's 323E011 instance decided and built (323F004's 1.083 m3 vapour space in the node's free volume; a full envelope holds 1.1300 bar a where it rang 0.59-1.82), the 328C004 instance stays with the solver review; FIC-329409 and TIC-329005 on the DCS table's rows on their spans (decision 10's class, the spans read). **Session 43 (As-Built Part LX):** A-20 decided (b) and built, closed — a full 323E011 / 323D011 envelope overflows through PV-323203's vent line into 323C005's sump; the node's ring at its vapour floor, which the routing does not reach, measured and filed with B-51's class. **Session 42 (As-Built Part LIX):** A-15, A-16 and A-19 decided and built, closed — the stripper's blow-through loads 323C003 and SV32351 / SV32352 relieve it, a full 328D001 overflows into 323E011, 328C003's, 328C004's and 322C001's overflows are boundary sinks published to the consoles, V1's diagnostic blocks stay out of the packet; decision 11's ceiling on 323D011's envelope; A-20 raised. **Closed into Phase 6 (session 41, As-Built Part LVIII):** the console packet on V1's WebSocket key paths (`engine/packet/`: every path V1's `step_sim` returns, its five diagnostic blocks aside; 264 of the screens' 268 bindings resolve, the other four unit 335's), V1's section 6 display lags as a scheduled step (`322-DISPLAY`, ``==`` V1 on every tick), 323P001B's standby faceplate SIC-323902 (V1's section 33), the historian recording the packet on V1's paths, the engine host (`net/engine_host.py`: the plant on its own physics thread, commands applied between two ticks in arrival order, the packet published ten times a second with V1's health block, trend backfill over the protocol) and `run.py` serving the live plant; the tag resolver attributing `r323_ctrl_set` by the faceplate it moves (it read every faceplate as unit 323) and every engine command type proven attributed (A-8); B-79 decided, to Section C. **Session 40 (Part LVII):** B-75, B-76, B-78 items 1-3 built and closed; the motive-loss stall fixed (A-18); `engine/historian.py`, `snapshot.py`, `command.py`, `session.py`. B-2 signed off and closed in session 54; A-18's FAST pace and A-12 with decision 39's trip data closed in session 49 (decisions 88, 96); A-14's Phase 7 driver built in session 46 and A-14 closed |
| **6 — HMI and architecture** | **Session 68 (As-Built Part LXXXIII):** A-2 (station authentication) and A-8 (unit assignment) superseded and retired by decision 149, the single-console conversion: the station token, the roles, the roster and section assignment removed. **Session 44 (As-Built Part LXI):** the process engineer deferred A-2 and A-8 until the physical and UI port is complete and paused the instructor's panel; the simulator runs on one machine, its console the superuser (`net/protocol.py` ``Role.SUPERUSER``, granted to a loopback peer only; `run.py`'s default); the stream inspector (`hmi/widgets/stream_hotspot.py`: V1's ``renderStream`` over the packet's ``STREAMS``, proved by node on every published stream); B-5 (closed by measurement: no two thermocouples share a path on V1's reissued screens), B-6 / B-7 (one atmosphere and one gravity), B-9 (one flood ceiling), B-11 (TT-322012's 120 s lag, V1's, built in session 41) and B-16 (TT-322002 on 165 C) closed. **Session 43 (As-Built Part LX):** the console's history request (`hmi/bridge.py`: `request_history`, `history_received`) and the trend window (`hmi/trend/`: ten pens, seven spans and a typed one, ten rulers, the historian its only source, polled once a second for the whole window; a trendable element's menu and a drag onto the plot or a row add a pen). **Session 42 (As-Built Part LIX):** the faceplates (`hmi/faceplates/`: V1's routing over every element, each a renderer of the packet and an emitter of the engine's commands) and the instructor's panel (`hmi/instructor/`: pacing, freeze, reset, malfunctions, exercises, unit assignment; the roster and the exercise list on the protocol). **Opened in session 41** on the process engineer's authorisation: the engine serves the live plant to the consoles (Phase 5's row). A-6 decided and closed in session 53: the ten backgrounds frozen, every symbol change through the converter. A-7 (the five overlay collisions) decided and closed in session 48: zero overlap, the converter's `NUDGE` rows. A-2 and A-8, deferred in session 44 until the port was complete, closed in session 56 (As-Built Part LXXII): A-8's section assignment signed off as the final design, A-2 on the optional station token, the instructor's panel unpaused |
| **7 — validation and the calibration deferrals** | **Session 80 (As-Built Part XCIII):** every controller's load relation tabulated (72 entries) and the schedule run 70-115 % on both objectives, re-held at 100-110 %; B-118 and B-120 updated for this phase; B-121 closed on option (a) (decision 164). **Session 79 (As-Built Part XCII):** B-122 decided (b), built and closed (decision 162); B-121 and B-118 traced against Book2's bands; B-123 raised and signed off as built (decision 163); the synthesis loop's harness kept on the linearised step. **Session 78 (As-Built Part XCI):** a pasted analysis of B-118 to B-121 checked and measured; B-119 decided (b), built and closed (decision 161); B-122 raised; the 105 % hold verified. **Session 77 (As-Built Part XC):** the workbook retried on the process engineer's control document with HIC-322605 by hand; B-118 and B-119 updated, B-121 raised for this phase. **Sessions 75 and 76 (As-Built Part LXXXIX):** the load range 70-115 % studied for the optimisation workbook; B-118, B-119 and B-120 raised for this phase, Book2.xlsx's 92 % and 111 % plant bands their acceptance data. **Sessions 73 and 74 (As-Built Part LXXXVIII):** B-113 (b), B-115 (a) and B-116 decided and built, B-114 measured and signed off as built, all four closed (decisions 157 to 160); the dynamic audits built, 14 tests, their finding B-117 raised and signed off as built; `Scenarios6.docx` re-run, 47 of 71; the bleed valves' data-gap row closed and the tuning row narrowed to FIC-335405; 11 data gaps open. **Session 72 (As-Built Part LXXXVII):** 322E001 on its 2,950-tube replacement (decision 154), the turnaround's plugged tubes (decision 155), the faceplate photographs of 24 October 2026 (decision 156: AI-329701's range and five tunings), `Scenarios6.docx` put to the plant (45 of 71), the stream inspector's tie rounding fixed; B-113 to B-116 raised. **Session 71 (As-Built Part LXXXVI):** an external report on five data-gap rows audited, 322C001's head volume and the urea-melt Henry constant closed (decision 153). **Session 70 (As-Built Part LXXXV):** the housekeeping split, every module inside 600 lines (decision 152); no item opened or closed. **Session 69 (As-Built Part LXXXIV):** the data gaps searched in both user folders and the archive; seven valves on their vendor sheets (decision 150) and 322E006 on PFD 28's water (decision 151), four data-gap rows closed. **Session 67 (As-Built Part LXXXII):** B-112 built and closed (decision 148); Sections A, B and C empty. **Session 66 (As-Built Part LXXXI):** B-108 to B-111 built and closed (decisions 144-147); `Scenarios5.md` re-run, 82 of 165; B-112 raised. **Sessions 64-65 (As-Built Part LXXX):** A-23 and B-104 to B-107 built and closed; `Scenarios5.md` re-run, 83 of 165; B-108 to B-111 raised. **Session 63 (As-Built Part LXXIX):** B-102 and B-103 built and closed; `Scenarios5.md` surveyed, 74 of 152; B-104 to B-107 and A-23 raised. **Session 62 (As-Built Part LXXVIII):** S1-1.2's conversion traced, A-21's option (c) measured; B-102 raised for the process engineer's decision, B-103 raised on decision 62's class. **Session 61 (As-Built Part LXXVII):** A-21, B-99, B-100 and B-101 built and closed (decisions 135-138), the affected scenarios re-run. **Session 60 (As-Built Part LXXVI):** A-22 and B-98 built and closed (decisions 132, 133), A-21 and B-99 measured for the final decision, B-100 and B-101 raised. **Session 59 (As-Built Part LXXV):** three Metso valves wired (decision 131); the process-deviation survey (`tests/phase7/deviations.py`, `run_deviations.py`) run, A-21, A-22, B-98 and B-99 raised for this phase. **Session 57 (As-Built Part LXXIII):** decision 95's reactor-liquor buffering signed off as the V1.1 baseline (decision 126), the 322E002 / 322E001 liquor data gap closed; trip 21.2 shuts XV-322902 (through the Safeguard SG1) and XV-322903 as AC4 PC21.5.1 draws them, the CO2 demand to zero on decision 83's class (decision 127); 323P003's protection, trip 21.2's hand switches and TRIP_84_8 read from the archive. **Session 55 (As-Built Part LXXI):** B-97 decided and closed (decision 121: 708 at 324F002's adiabatic mix of 706 and 924, as its departure from the design mix); B-1, B-4 and B-12 signed off and closed (decision 122) — Section B is empty; UF85 dosing live (decision 123). **Session 54 (As-Built Part LXX):** B-31 decided and closed (decision 118: the five units' inlets at their producers' live temperatures as departures from the producers' designs, the utilities at design; 708, whose temperature no unit computes, raised as B-97); A-13 closed on its audit (decision 119); B-2, B-17, B-45, B-48, B-52, B-72, B-74 and B-78 signed off and closed (decision 120) — Section C is empty. **Session 53 (As-Built Part LXIX):** B-30 decided and closed (decision 114: 323E011 on its dew point, anchored on V1's 5589 kg/h at the design node, uncapped as 323E003's, and PV-323203's differential floored at zero); B-22 decided and closed (decision 115: 323F010's bubble point on the live PT-323204 — the vacuum break re-run, no oscillation, the liquor to 103.1 C and its evaporation 12.0 to 7.6 t/h); FV-329401, PV-329204, PV-329207A / B and FV-329409 on Metso's trims (decision 116). **Session 52 (As-Built Part LXVIII):** B-91 accepted and closed (decision 110); B-96 closed on a 2 % hysteresis stand-in (decision 111); B-79 (b) built and closed — solid carbamate on Egan, Potts and Potts (decision 112); PV-329202, PV-329208 and LV-329505 on their vendor trims, FV-329401, PV-329204 and PV-329207A / B catalogued (decision 113). **Session 51 (As-Built Part LXVII):** B-94 decided and closed (decision 104: PFD 734 as its departure from the PFD's row; the steady state 3080 of 3188 within 1 %); B-91: 322E003 on its own liquor's bubble pressure and on a full sump (decision 105), the retained-gas term not built (the node holds that gas already), the start-up procedure compared (option (b)); trip 22.2 still not reached, 148.2 bar a after 48 000 s with the tempered water lost (V1 at 20 099 s) — the cold start now reaches 137.9 bar a at 3 000 s, fit 136.04 bar g and tau 1 305 s (session 50: 78.07 bar g, 4 860 s), B-91 open; B-93 decided and closed (decision 106: AC4 PC23.1.9 / 1.10's trip on LT-323503 < L2 built; its live flag relays, B-96); B-95 closed as designed (decision 107); PV-329203 and PV-329212 on Metso's trims (decision 108); 329D001's volume (decision 109). **Session 50 (As-Built Part LXVI):** B-91 option (a) built (decision 97: 322E002's melt, 322E003's condensation and the reactor's buffering capped by the saturation fraction on the liquor's bubble pressure); B-92 decided and built (decision 102: 322R001's nodes at most at the liquor's bubble point, the excess flashing the overflow's volatiles, the kinetics' residence on the liquid passing); B-18 (decision 99, HV-322604 at 72 %), B-37 (decision 100, PFD 734 into 323E003) and B-20 (decision 101, urea closed on the drain) decided, built and closed; the five AC4 hand switches and AI-329701 on the overlay screens (decision 98); the plant DCS's readback of 13 October 2026 applied (decision 103). The Phase 7 scenarios re-run (§LXVI.9): the cold start reaches 79.7 bar a after 16 000 s, still rising about 2.2 bar per 1 000 s (session 49: 30.4), short of the 137.5-150.5 bar g band — B-91 stays open on the measured sink (322E003's condensation into a full sump, 322F001 stalling); the HPCC rupture holds 139.1 bar a with TT-322015 at most 56.1 C, no trip; the vacuum break unchanged; the steady state 2 858 of 3 188 leaves within 1 % (3 083), the seed relaxing; with the tempered water lost the loop settles at 147.5 bar a and trip 22.2 is still not reached (V1 at 20 099 s); B-93 (323P008's 5 % trip), B-94 (the design seed no longer a fixed point) and B-95 (trip 22.1 held by its own flood steam) raised. **Session 49 (As-Built Part LXV):** A-18, B-90, B-84, B-81, B-85, B-28 and B-25 decided and closed (decisions 88-94) — FAST as fast as the machine allows, AI-329701 and the malfunction's rate, V1's 57 / 55 C on TI-322015, the letdowns' lines two-phase, FFIC-321404A / B built, no deadband (LIC-329505's too), no biuret; B-77 (b) decided and built, closed (decision 95: 241.7 m3 less the liquid, the reactor liquor's buffering anchored on PFD 207's solubility); A-12 decided and built, closed (decision 96: AC4 PC21's flags 21.2, 21.8 and 21.10 as drawn, V1's 21.4 gone, 22.2 V1's); the Phase 7 scenarios re-run on them (§LXV.7): the steady state 3 083 of 3 188 shared leaves within 1 %, the vacuum break without a trip, the HPCC rupture holding PT-329201 at 139.0 bar a and stopping 0.7 K short of trip 22.1 (TT-322015 56.3 C), AI-329701 over range from its first step; the cold start no longer pressurises (30.4 bar a after 16 000 s against V1's 146.2) and the tempered water's loss settles near 147 bar a without trip 22.2 — B-91 raised. **Session 48 (As-Built Part LXIV):** B-86, B-87, B-88 and B-39 decided and built, closed — no held melt boils below the melt model's window (decision 82), no condenser vents below zero (decision 80), FIC-328402 meters 735 and 744 is 322P002's delivery (decision 81), trip 22.2 takes the CO2 boundary's demand to zero (decision 83); the cold start and trip 22.2 re-run; the steady-state comparison at 1750 MTPD run (`tests/phase7` ``steady_state``, every packet leaf); the overlay gate at zero overlap on every screen (A-7 decided: the converter's `NUDGE` rows); B-13 closed as built (322E002's gate 1.0 on both engines); B-82 built — 322E002's tube leak, process into the shell on the live differential, the instructor's malfunction, the Phase 7 HPCC rupture run on it; B-89 accepted and closed; A-18 profiled (the named bottlenecks 37 % of a 10.4 ms tick, exact caching no gain), open; B-90 raised. **Session 47 (As-Built Part LXIII):** B-51 and B-83 decided and built, closed — the vapour-space pressure takes the backward step on a tick where the explicit one would ring (`core.node.stable_pressure_step`, 328C004; decision 78), SV32064 relieves the CO2 line on Sempell's orifice H (decision 79); B-87 traced to 324F003 at the melt window's edge (B-86) and the vacuum train's negative vent; B-88 raised (SV32064 after trip 22.2; closed in session 48). **Opened in session 46 (As-Built Part LXII):** the transient runner (`tests/phase7/`: V1's `step_sim` and the port's scheduler through one procedure at the same fixed 0.1 s step, one process each, B-51's pressures watched every tick) built and its four scenarios run — the cold start, trip 22.2, the HPCC rupture and the vacuum break (§LXII.4); A-14 closed. Raised for this phase: B-81 (the letdowns' two-phase lines), B-82 (the HPCC rupture's direction, closed in session 48), B-83 (SV32064 on the CO2 line, closed in session 47), B-84 (TI-322015 with the trace steam), B-85 (FFIC-321404A / B), B-86 (the separators below the melt model's window), B-87 (328C004 flooding in the port's cold start) — both closed in session 48. Section C unlocked once the baseline transient comparison is complete: B-79 (the solid carbamate a dry purge would deposit, its dissociation constant a data gap), B-77 (the loop's lumped capacity; built and closed in session 49), B-78 (the production surge's recycle lag), B-45 (TIC-323012's stated tuning), B-30 (the LP condensers' dew-point capacities), B-31 (live inlet temperatures), B-18 and B-37 (decided and closed in session 50); B-48 (TIC-328012's cascade, once a tray temperature exists); B-52 (the reflux loops' tunings); trend checks of B-4 (the two-path pressure model), B-12 (322F001's stall margin) and B-17 (the vent-top overshoot) against the DCS trends; B-72 (the steam relays) and B-74 (322E002's raising), both decided Calibration Deferrals on 2026-10-02; PIC-329205's and LIC-329502's V1 tunings (B-52's class) |

---

# Section A — Rewrite issues

*(Closed: A-8 was signed off and A-2 closed on the station token on 2026-10-16, session 56,
As-Built Part LXXII; both multi-station mechanisms were removed when the simulator was converted to a
single-console architecture on 2026-10-22, session 68, decision 149, As-Built Part LXXXIII. A-22 was decided (a) and built, a full 323F004 overflowing into 323E011, and
closed on 2026-10-17, session 60, As-Built §LXXVI.1. A-21 was decided (b) and built, 322E002's
saturation fraction solved on the tick, and closed on 2026-10-21, session 61, As-Built §LXXVII.1.
A-23 was fixed, the console tests on settings of their own, and closed on 2026-10-22, session 64,
As-Built §LXXX.1. A-24 was decided, V1's source tree named at `E:\Simulator\Urea Simulation`
(decision 165), and closed on 2026-11-04, session 82, As-Built §XCV.1. None open.)*

---

# Section B — Physics gaps inherited from V1

These are **not** rewrite defects. They are open modelling questions in the physics being ported.
Port the V1 behaviour exactly, including the compromise, and keep the item open here.

*(Closed: B-1, B-4 and B-12 were signed off and B-97 decided and built, and all four closed on
2026-10-16, session 55, As-Built §LXXI.1 and §LXXI.3. B-98 was decided (b) and built, the backward
species step at a heel, and closed on 2026-10-17, session 60, As-Built §LXXVI.2. B-99 (b1), B-100
(b) and B-101 (b) were decided and built — 322E003's capacity on its shell's effectiveness, 323F004
on its geometry, the vapour draw in the heel's backward step — and closed on 2026-10-21, session
61, As-Built §LXXVII.2-4. B-102 was decided (b) and built, 322E001's duty bounded by its shell on
the live steam's LMTD (decision 139), and B-103 built on decision 62's class, LT-322501's full sump
held back in the tubes, and both closed on 2026-10-21, session 63, As-Built §LXXIX.1-2. B-104,
B-105, B-106 and B-107 were decided and built — 322E001's tubes standing full, 323D001's liquor into
322E003, the melt below its azeotrope, 324F003's lost seal admitting air (decisions 140 to 143) —
and closed on 2026-10-22, sessions 64 and 65, As-Built §LXXX.2-5. B-108, B-109, B-110 and B-111 were
decided and built — stage 2's temperature on its energy balance where its iteration does not settle,
PT on 322R001 capped where the melt flashes, PFD 308's line on its isometrics, the azeotropic rise
added in bar (decisions 144 to 147) — and closed on 2026-10-22, session 66, As-Built §LXXXI.1-4.
B-112 was decided (a) and built, PT on 322R001 on its feed line's PFD drop and reading the PFD's
141.3 bar a at the design (decision 148), and closed on 2026-10-22, session 67, As-Built
§LXXXII.1; the two display-only notes of §LXXXII.3 were signed off as built, no item raised. B-113 was
decided (b) and built, the plugged tubes' conductances re-anchored on the bundle in service; B-114
was measured tick by tick — SV32351 / SV32352 lift at their set — and signed off as built; B-115
was decided (a), the bleeds on the design basis; B-116 was built and signed off, TIC-328008 and
FFIC-335406 on their faceplates (decisions 157 to 160); all four closed on 2026-10-28, sessions 73
and 74, As-Built §LXXXVIII.1-4. B-117, raised by session 73's dynamic audits — TIC-328008, as every
cascade master V1's `_ctrl_ipd` builds, integrating while its slave is out of cascade — was signed
off as built (decision 120's class) and closed the same day, §LXXXVIII.5. Four opened 2026-10-30; B-119 decided (b), built and closed the same day (decision 161, §XCI.7); B-122 opened the same day, decided (b), built and closed in session 79, the pressure step solved itself where 323F010's holdup boils (decision 162, §XCII.2); B-123 opened in session 79, signed off as built, option (a), and closed on 2026-10-31, V1's thermo memo kept, its chatter on 323F010 below PT-323204's resolution (decision 163, §XCII.2). B-121 was closed on option (a) on 2026-11-02, session 80, the engine kept as built: PIC-323202 at 3.5-3.9 bar a and FIC-328402 with FIC-329402 scaled on load are the operator's moves, and no relation changes (decision 164, §XCIII.10).)*

### B-118 — Below 100 % load the engine holds no steady state on the plant's reactor window

*Raised 2026-10-30, session 76, by the load-optimisation study (As-Built Part LXXXIX). Phase 7.*

The plant runs steadily at reduced load: `References/DCS Trends/Book2.xlsx` (July to September
2023) holds 755 samples at 90-95 % with TT-322005 at 182.6 C, AY-322701 3.25, PT-329201 137.4 bar,
PIC-329204 18.2 bar g, PT-329207 4.11 bar g, TIC-329005 90.0 C, HIC-322604 51.5 %, FFIC-321404B 2.115;
the licensor's windows (Operating Manual Part III, UD-VT-G00-DC-0003 section 5.2) are N/C 2.90-3.10,
TT-322005 180-183 C, PT-329201 136-143 bar. The committed engine, ramped from its design seed, holds
none of it. Every operating policy tried — design handles; PIC-329204 on TT-322004; MASTER-329207 on
TT-322005 or on PT-329201 (up to the LP header's 6.2 bar a); HIC-322604 on PT-329201; TIC-329005
lowered while 322E003 vents; and the plant's own 92 % set points above — ends one of two ways:

* **70-85 %:** trip 22.1 within 20-80 minutes (322E003's sump floods with HIC-322602 at its 10 % floor,
  or 322E003 vents 2-7 t/h of condensable gas and TT-322015 runs past 110 C), or, where it does not
  trip, the reactor collapses: TT-322005 158-172 C, conversion 27-40 %, 322R001's off-gas 22 to
  57 t/h at 85 % (policy PS).
* **90-95 %:** a cold branch: TT-322005 168-178 C, conversion 36-48 %, 322E003 venting 0.1-4.6 t/h,
  the carbon balance open by up to 13 % after three hours, steam import above the 100 % figure
  (73 t/h at 90 % on the design handles).
* **The plant's 92 % set points** (TIC-329005 90 C, ratio 2.115, LP 4.11 bar g): 322E003 vents 7.2 t/h
  at once and trip 22.1 fires at 20 minutes at 90 % and 95 % load.

The sequence, as measured: once TT-322005 dips during the ramp, the reactor's conversion falls below
its pinned design value and V1's conversion-slip term (`reactor.py`, the slip amplifier on
`delta_x`) sends the unconverted NH3 and CO2 to 322E003 as off-gas (322R001's off-gas 22 to 57 t/h at
85 %), which takes still more carbamate heat out of the reactor — a positive feedback that raising
MASTER-329207 to the LP header's 6.2 bar a (322E002's shell at 160 C, its duty still 77-84 % of design
at 85 % load) does not stop; and 322E003 is anchored at design on its whole demand (decision 157: no
condensation margin), so the extra off-gas, or tempered water warmer than 80 C, is vented. Above
design none of this binds: the reactor runs hot.

Session 77 (2026-10-30, As-Built Part XC) retried the turndown on the process engineer's control
document. Its schedule ran on the live load: HIC-322604 on its equal-percentage inverse, PIC-329204
lowered no further than its LMTD floor, MASTER-329207 and TIC-329005 raised, and 322F001's
entrainment in proportion to load. HIC-322605 was operated by hand on the solution 322R001
discharges. The end was the same:

* trip 22.1 at 53-55 minutes at 70-80 %;
* trip 22.2 at 80 minutes at 85 %;
* the cold branch at 90 % (TT-322005 171.6 C, X 41 %) and a slide at 95 %;
* an operator lowering the ratio toward AT-322701 3.02 reached the faceplate's 2.0 floor and vented
  more;
* a 0.1 %/min ramp slid from 98 %.

The first link is now measured. With the fresh ratio fixed, AT-322701 rises from 3.00 to 3.30 on the
ramp to 90 %, while the reactor feed's N/C moves only from 3.073 to 3.088. TT-322011 follows its
correlation (`scrubber.py`, 120 K per unit of N/C) to 147 C, 322E003's saturation fraction falls to
0.93, and 1.6-2.4 t/h of condensable gas is vented. Meanwhile 322R001's discharge and 308's wash stay
at their design rates, and conversion is under its pin within minutes. The plant holds AY-322701
3.25 at every band, with TT-322011 at 130-134 C; the engine's correlation gives 144 C at 3.25.

Session 78 (2026-10-30, As-Built Part XCI) checked a pasted analysis that put the turndown on two
other mechanisms, and measured its changes as scratch patches. Neither mechanism is the engine's.
322E003's vent split reads its K-values at the design temperature, so TT-322011's correlation sets
only the reading and HV-322604's purge. 322E002 does not over-quench (TT-322010 167.9-171.5 C): its
melt holds less gas at turndown, not more. At 90 %, TT-322011's slope cut to 75.9 C per N/C unit
changes nothing else. 322E002's conductance scaled on (m / m_des)^0.75 delays the slide by about 20
minutes (X 45.9 % and TT-322005 175.7 C at 60 minutes, against 40.9 % and 171.4 C). With V1's
conversion-deficit slip switched off the reactor still slides, to X 44 % at 90 % and 31 % at 80 %
(TT-322005 174 and 165 C), its off-gas growing less (33 against 46 t/h at 90 %). In every run the
loop N/C's excursion on the ramp, AT-322701 at 3.3 within 20 minutes, precedes the slide.

Options: (a) keep as built, the simulator's working envelope stated as 100 % to about 105 % load and
the turndown scenarios left to a later calibration; (b) re-anchor the turndown on Book2's 92 % band:
the overflow's N/C partition and the vent-top correlation against the plant's AY-322701 3.25 and
TT-322011 130-134 C at every band,
322E003's condensation capacity given the margin the plant shows (TIC-329005 90 C with no venting),
the slip term reviewed against the plant's steady 182.6 C, and 322E002's duty's dependence on its
shell temperature measured against TT-329001 and FY-329403 in the same band. Recommended: (b), with
Book2's 92 % and 111 % bands as the acceptance tests. Session 78 narrows (b): the vent-top
correlation sets only the reading and HV-322604's purge, and neither 322E002's conductance nor the
slip term causes the slide; the N/C excursion on the ramp and 322E003's margin at AT-322701 3.25
remain.

Session 79 (As-Built §XCII.4) traced the excursion term by term. On the design handles' ramp to
90 % (0.5 %/min, 323F010 on its own head), AT-322701 rises from 3.000 to 3.31 at 16 minutes and 3.54
at 20. The reactor's NH3 partition moves the overflow's N/C by at most +0.006 and the conversion
slip by at most 0.006; the re-flashed split takes 0.06-0.14 off it. The rest is the
reactor's real feed, 322E002's melt and gas, whose atom N/C rises from 3.11 to 3.47 in the same 16
minutes and which the reactor carries atom for atom. The 3.073-3.088 that session 77 recorded is
``l_feed``, the reactor's blended driver — 30 % the fresh-feed ratio's prompt and 70 % its lag,
V1's REACT_NC_LOOP_GAIN construction — which sets the kinetics and the partition and never sees
the loop's composition. The engine's AT-322701 of 3.00 is the PFD's design overflow on an atom basis
(2.99975); Book2's AY-322701 stands at 3.25 in every band, above the licensor's 2.90-3.10, so the
plant runs NH3-richer than the design at every load, and the engine's correlations anchored at 3.00
(TT-322011, 120 K per N/C unit) read 144 C where the plant reads 130-134 C. At Book2's 92 % set points 322E003's vent is its saturation fraction on its own liquor (decision 105),
not its shell's capacity: f is 0.93 within 30 s, the liquor bubbling at 145.5 bar a against the
loop's 140.7 (1.5 t/h), and 0.76 at 22 minutes as AT-322701 runs past 3.9 (7.8 t/h); with f held at
1 at most 0.47 t/h stays uncondensed, with the capacity held at 1 nothing changes. At the plant's
ratio the engine's AT-322701 reaches 4.27 in 28 minutes, where the plant holds 3.25: the turndown's
first link is the loop's nitrogen balance, which the saturation fraction then turns into vent. Whether
these changes damp B-120's mode was not measured.

Session 80 (As-Built §XCIII.3, §XCIII.4, §XCIII.8) traced the excursion stream by stream and ran
the whole schedule. On the design handles' ramp to 90 % the rise is 322E001's top gas: its nitrogen
grows 23 % (3 662 to 4 507 kmol/h) and its carbon falls 11 % while the load falls 10 %, its N/C
1.94 to 2.69 and the reactor feed's 3.11 to 3.96 at 22 minutes; the stripper, at its design shell
pressure, gives the loop's ammonia back faster than the fresh feed falls, and only LV-322501's drain
takes ammonia out of the loop. 322F001, its spindle at the design 74 %, stalls 4-10 minutes after
the ramp ends; on the ramp to 80 % it stalls at 86-88 % and the loop's circulation collapses. A PI on
AT-322701 onto the ratio meets the faceplate's 2.0 floor with AT-322701 at 3.76. FFIC-321404's ratio
is on the engine's basis — its design 2.0231 is a true molar 2.086 — so the plant's 2.115 is
2.047-2.053 here: on Book2's 92.3 % set points 2.052 still trips 22.1 (at 31 minutes, against 19 at
2.115), and at 100 % it holds (X 56.46 %, AT-322701 settling at 3.14). With every controller and hand
station on its load relation, 322F001's spindle closed with load and slow supervisory trims
(§XCIII.5-8) the turndown is unchanged in kind: at 70-80 % 322E003's sump fills to 90-97 % with
322F001 still entraining (HIC-322602 13-29 %), vents 7-13 t/h and trip 22.1 fires at 51-62
minutes; at 80-85 % the loop goes NH3-lean and trip 22.2 fires at 66-81 minutes; at 85-95 % the
holds complete and fail on levels, the conversion objective NH3-rich (AT-322701 3.29-3.96) with
322D001A/B's or 324F001's level running away, the steam objective cold (TT-322005 177-179 C,
X 48-49 %) with 324F001 filling. Recommended: (b), narrowed to 322E001's overhead at its design shell
pressure on the ramp and 322E003's margin at AT-322701 3.25, Book2's 92 % band the acceptance test.

Session 81 (As-Built §XCIV.2-4) measured the narrowed (b) at Book2's 92.3 % set points. Every arm
started from the design seed, settled three hours and held one, as scratch patches.

* **322E001's overhead does not carry the excursion.** On the design handles' ramp to 90 % its NH3
  overhead fraction stays at 0.855-0.835. What rises is what it is fed: the reactor overflow's NH3,
  +29 % (4 003 to 5 159 kmol/h) while the load falls 10 %. Two things feed it:
  - 322R001's holdup drains at a fixed HIC-322605 (-24.5 t/h at 22 minutes) and its conversion falls;
  - 322F001's suction nitrogen halves at its design spindle.

  The nitrogen into 322E002 stays at 7 490-7 580 kmol/h while its carbon falls. Both carriers are
  operator handles. Session 80's reading above is corrected accordingly: the stripper returns its
  usual fraction of a growing feed. Scaling the NH3 overhead with load (A3s) stops the venting only
  by driving the loop NH3-lean (AT-322701 2.60, TT-322004 182.3 C), and then 322E003 vents again.
* **322E003's liquor at the plant's set points is hot.** TT-322002 follows the tempered water: +1 K per
  K of TIC-329005, plus 12 K per unit of HV-322604's opening deviation. It reaches 174-178 C, where
  the plant's TT-322002 holds 166.75 C (165.7-167.5 C in every band).
  - At AY-322701 3.25 and TIC-329005 90 C the liquor's bubble pressure is 173.7 bar a, 35.4 bar above
    Book2's 138.39 bar a: 30.2 bar of temperature and 5.2 of composition. That is the minimum margin
    m*, and no N/C slope closes it.
  - A 40 bar design head (A40) removes the saturation venting, but the hold sits on the cold branch:
    TT-322005 178.9 C, X 49.9 %, 998 kg/t and 1.0 t/h still vented on the shell's capacity. Its
    saturation fraction is 1 throughout the hold, so a larger margin is inert, no margin holds the
    band, and m* itself was not run.
  - The cold start with the margin is no better than without it (B-124).

Options now:

* (a) keep as built, the simulator's working envelope stated as 100 % to about 105 % load;
* (b) measure TT-322002's dependence on the tempered water and HV-322604 against Book2's bands, as a
  new mechanism with both sides measured, together with the two operator handles on the ramp.

Recommended: (b), with Book2's 92.3 % band the acceptance test.

Session 82 (As-Built §XCV.3) measured option (b) on a scratch prototype: TT-322002's ceiling at the
shell's own condensing temperature at PT-329201 (V1's `scrub_cond_t_c`, 165.0 C at design), so the
liquor no longer follows the tempered water. It keeps the design seed to the bit.

* At Book2's 92.3 % set points it holds TT-322002 at 167.3 C, against the plant's 166.75.
* 322E003's liquor acts on the process only through its saturation fraction: 322F001's discharge is
  on its design suction temperature. The liquor law still leaves f at 0.92 there, and 322E003 vents
  1.8 t/h.
* With f held at 1 (the liquor capped at its own bubble point), the hold reads TT-322005 178.9 C,
  322E001's bottoms 176.7 C and X 49.9 %, as A40 did at a 50 % sump. The plant reads 182.6 and
  166.6 C.
* LT-329501 did not reach Book2's 7.05 %. It held 21 % with HIC-322602 at 23 %, still falling.

No band held. The 92.3 % miss is not in 322E003's liquor. Recommended: (b) narrowed again, to 322R001
and 322E001 at Book2's 92.3 % set points: 322E001's bottoms 10 K hot on the plant's PIC-329204, and
322R001 3.7 K cold.

Session 83 (As-Built §XCVI.2) traced 322E001 and 322R001 at Book2's 92.3 % set points, f held at 1.

* **Term by term, the bottoms are** 172.0 - 0.86 (steam) + 5.82 (V1's feed-deficit rise: the liquid feed is
  0.965 of design) + 0 (strip cooling) = 177.0 C, against the plant's 166.6.
* **The HP steam runs high at both loads, and the bottoms' excess grows at turndown.** On like-for-like tags
  the engine's FT-329403 goes from 75.7 to 64.0 t/h between 111 and 92.3 % (0.85), as Book2's FY-329403
  goes from 66.3 to 53.5 (0.81): 14-20 % high at both loads. That is a level offset, to be checked
  against the PFD's HP steam at 100 % (decision 159's class) before it is called a turndown term. The
  TT-322004 excess does grow at turndown (+10 K at 92.3 %, +7 K at 111 %): V1's feed-deficit term.
* **The bottoms term alone is not the re-anchoring.** Taking V1's feed-deficit rise off (and the steam
  slope at Book2's 1.26 K/K) cools the bottoms to 170.2-170.9 C, but FT-329403 stays at 63 t/h and the
  reactor cools to 177.7 C.
* **LT-329501 cannot reach Book2's 7.05 %.** 322F001's suction is proportional to the level, and at 7.05 %
  even its 10 % spindle floor entrains 25.9 t/h of the 58.9 t/h the sump must pass; it holds about 16 % at
  best.

Recommended: (b), on 322E001's HP steam against the PFD at 100 % and Book2's FY-329403 at both loads
(53.5 t/h at 92 %, 66.3 at 111 %), then 322R001's heat with it. No re-anchoring that holds 92.3 % was
found, and LT-329501 settled in no arm (falling 2.7-3.2 %/h).

### B-120 — A cut of 2-8 K on TT-322004 at design load starts a slow loop oscillation

*Raised 2026-10-30, session 76 (As-Built §LXXXIX.4). Phase 7.*

At 100 % load, PIC-329204 trimmed to hold TT-322004 at 168 or 164 C (design 172) settles for an hour
and then cycles with a period of about 1.1 h and growing amplitude: urea leaving the stripper
62-81 t/h, conversion 49-65 %, AT-322701 2.76-3.46, 308's wash 23-43 t/h, LT-322501 swinging 15 %
peak to peak, 323F010 sixty per cent; at 170 C the same cycle with LV-322501's erosion flag and
322E001's seal down to 0.979. It is the undamped loop mode session 62 recorded on S1-1.2. The
licensor allows TT-322004 162-176 C (+5 K). Options: (a) keep as built; (b) trace the mode on the
stripper's H/C slip and 322E002's saturation (session 62's attribution) and measure it against
Book2's 92 % band, where the plant holds TT-322004 at 166.6 C steadily. Recommended: (b), with B-118.

Session 78 (As-Built §XCI.3) re-ran the 168 C case with HIC-322605 by hand and measured the
stripper's slip gain (`unit_322e001.SLIP_GAIN`, V1's calibrated STRIP_SLIP_GAIN 4.0), as a pasted
analysis proposed. By hand the mode keeps its period at about a quarter of the swing: X 54.3-59.1 %
over 100-180 minutes against 48.8-66.2 %. The gain sets its size: 55.4-56.9 % at 2, 56.3-56.7 % at
0. No gain gives a steady hold. At 2 LT-322501 still swings 11 points; at 0 the loop is steady, but
323F010 drains 16 %/h (B-119) and AT-322701 stands at 3.15, outside the licensor's window. With
323F010's leg on its own head (B-119's prototype) and the gain at zero, 323F010 holds 55-59 %, but
322R001's level drifts +3.4 %/h, AT-322701 stands at 3.15 and the carbon yield is 0.956. Changing
the gain is a decided divergence from V1.

Session 80 (As-Built §XCIII.7-9) measured the mode with AT-322701 fed back to the ratio and on load
changes. At 100 % with TT-322004 held at 168 C there was no oscillation in four hours, but AT-322701
stood at 2.70 while the ratio operator raised FFIC-321404B from 2.023 to 2.083: with less stripping
the ammonia leaves in LV-322501's drain and the loop's N/C no longer answers the feed (X 51.4 %, the
hold failing on 323F010 and 324F001). At Book2's 92.3 % with TT-322004 toward 166.6 C, PIC-329204 fell
to 12 bar a, AT-322701 ran NH3-lean to 1.87 and trip 22.2 fired at 51 minutes. The mode appears on
load steps too: at 105 % AT-322701 swings 3.13-3.32 with a 1.1 h period, decaying, and the liquor's
density moves LT-322504's reading by up to 1 % while the true level holds at 80.0-80.15 %. On the
turn-up the loop goes NH3-lean: at 115 % both objectives trip 22.2 at 32 minutes, AT-322701 at 2.78, 322F001
stalling with the trip. At 110 % the directive's guard — HIC-322604 capped at 76 %, MASTER-329207 floored at
4.5 bar a, TIC-329005 at 70 C and PIC-329204 on a low select of TT-322004's target, PT-329201 <= 143
bar a and TT-322005 <= 183 C — took its three handles to their limits. On the steam objective PT-329201
settled at 143.3 bar a and TT-322005 at 184.4 C, just outside the limits, and the hold completed
without relief or trip (SV32253 held by the 76 % cap) and failed on six levels, 328C003 and
LT-322504's reading the largest. On the conversion objective, where PT-329201 never fell below
144.6 bar a, the stripper's cut to 19.7 bar a shrank the reactor's
off-gas from 35 to 29 t/h, 322E003's sump drained within three minutes at 25 minutes with 322F001's
spindle already fully open, the ejector lost its suction and the loop went NH3-lean, trip 22.2 at 51
minutes. Holding TT-322005 or PT-329201 by cutting the stripper's steam drives the loop NH3-lean, as
the 92.3 % cut does. Recommended: (b), the trace extended to the turn-up — the stripper's H/C slip and
322E003's make against 322F001's capacity at its full spindle — with Book2's 92 % and 111 % bands as
the acceptance tests.

Session 81 (As-Built §XCIV.5) ran the plant's own 111 % set points from the design seed:
TIC-329005 80 C, PIC-329204 21.02 bar a, MASTER-329207 4.913 bar a, HIC-322604 56 %, the ratio 2.053
on the engine's basis. 322F001's spindle was solved for LT-329501 at 50 % and, as the plant holds
it, at 10.8 %. 322E003's sump balance closes to within 50 kg/h.

* **The sump does not drain at the plant's set points.** Near the plant's level (16.6 %, still
  closing) 322E003 makes 42.9 t/h, about twice 322F001's full-spindle entrainment at that level
  (22.5 t/h), with HIC-322602 at 58.7 % against the plant's 76 %. It drains only under Session 80's
  stripper-steam cut (RC110).
* **The H/C slip is a branch of the engine's 50 % sump.** Held at 50 %, the ejector recirculates
  73 t/h, the reactor feed's H/C rises to 0.59, and V1's slip gain (g_hc 0.71) doubles the reactor's
  off-gas. At the plant's level the slip is 0.08, and zeroing its gain changes little.
* **What misses the band is 322E003's liquor, as at 92.3 %.** Near the plant's level AT-322701 (3.22)
  and TT-322004 (172.0 C) match the plant's 3.25 and 172.25 C. But TT-322005 runs 2.3 K high,
  PT-329201 1.2 bar high, and 322E003 vents 3.5-4.2 t/h: its liquor stands at TT-322002 180-182 C,
  where the plant's is at 167.5 C.

No hold passes. Recommended: (b), joined to B-118's, with Book2's 111 % band the acceptance test:

* TT-322002's dependence on the tempered water against Book2's bands (167.5 C at 111 % with
  TIC-329005 at 80 C);
* 322F001's spindle at the plant's level, noted on the data gap.

Session 82 (As-Built §XCV.3) ran the same prototype at Book2's 111 % set points, with LT-329501
solved on its published reading for the plant's 10.8 %.

* **It does not match Book2 there.** TT-322002 holds 164.6 C against the plant's 167.5: the wash's
  live temperature (323D001's liquor at 63.6 C, against PFD 308's 74 C) takes 3.4 K off under the
  ceiling.
* **The saturation fraction is 1, but the shell's capacity leaves 4.4 t/h uncondensed**: 0.905 at
  TIC-329005 80 C on the design circulation. The loop runs NH3-rich and hot: AT-322701 3.50,
  TT-322005 185.4 C, PT-329201 145.3 bar a.
* The level held 23-25 % and was still falling.
* Book2 carries TDY-329125, 322E003's tempered-water rise, at 28.8 K; the hold's logged duty
  `q_ccw_kw` over the design 306 t/h is 17.1 K. FV-329409 is a valve opening, so the plant's
  circulation is not known.

Recommended: (b), now on 322E003's condensing capacity at 111 %. Compare the tempered water's
circulation and rise against Book2 (FV-329409, TDY-329125), after CLAUDE.md §4's two searches for
FIC-329409's flow.

Session 83 (As-Built §XCVI.3) made CLAUDE.md §4's two searches and measured the capacity.

* **The PFD scales the duty with load:** 329E004's duty is 5.36 MW at 1750 MTPD and 5.90 at 1925.
* **Uhde rated 322E003's shell at 8 000 kW** on 460 t/h of circulating water at 80 to 95 C
  (UD-AU-322-EC-0005, page 4), 1.49 times the PFD's duty.
* **The start-up record** reads FIC-329409 at 330-336 m3/h at FV-329409 46-49 %.
* **The margin removes the venting.** With the shell's capacity lifted by that margin where it is short,
  322E003 vents nothing at 111 % and the deposition flag clears. The loop then runs NH3-rich (AT-322701
  3.60 on the fixed ratio), hot (TT-322005 185.3 C) and at 145.1 bar a.
* LT-329501 cannot reach Book2's 10.8 %: 322F001 holds about 12.5 % at best.

* The records disagree on the circulation. The plant's ~320 t/h (FIC-329409 333 m3/h) at Book2's 28.8 K
  is about 10.7 MW, above Uhde's 8 000 kW. The engine runs PFD streams 1111/1112's 306 t/h, and the
  datasheet says 460 t/h. C1's result holds for any margin of at least 1.11.

Recommended: (b) as a proposal for the process engineer. A capacity margin from the vendor's rating would
revisit decision 151's class, which keeps a datasheet's surplus out of the model. Measure it with
FFIC-321404 trimmed on AY-322701 as the plant runs it.

### B-124 — The Phase 7 cold start trips 22.2 at 3 322 s on the committed engine

*Raised 2026-11-04, session 81 (As-Built §XCIV.6). Phase 7.*

The Phase 7 cold start (V1's `test_transient_coldstart.py`, `tests/phase7`, port side) no longer
gives the answer decision 110 accepted in session 52. On d047fd8:

* PT-329201 rises faster: 111.5 bar a at 2 000 s and 150.7 at 3 000 s, against session 52's 95.4
  and 137.9.
* It overshoots to 154.7 bar a (322R001's PT 157.6) at 3 300 s. Trip 22.2 latches at 3 322 s, cuts
  the CO2 and both ammonia pumps, and the loop falls to 79.7 bar a by 16 000 s.
* The fit is tau 540 s, dead time 540 s, final 78.61 bar g. The trend's band is 2 884-4 055 s, at
  most 572 s and 137.5-150.5 bar g; session 52 gave 1 305 s, 555 s and 136.04 bar g.
* Trip 22.1 latches at 107.9 s (134.0 s in session 52). LT-322504 stays at 0 %, where session 52
  had it full at 8 000 s, and LT-329501 is at 100 % from 600 s.
* A 40 bar 322E003 margin changes little: trip 22.2 latches at 3 291 s.

The trip 22.2 scenario (both tempered-water pumps stopped at 60 s) still gives decision 110's answer on the committed engine: trip 22.1 latches on the flood steam at 93.9 s and 22.2 is not reached in 48 000 s, PT-329201 creeping from 140.7 to 148.3 bar a at 43 200 s and 150.0 at 48 000 s (session 52: 148.2), faster over the last 80 minutes (0.35 bar per 1 000 s against 0.02).

No Phase 7 cold start is recorded between session 52 and this one, so the change lies in sessions
53 to 80. The repository's first commit, 0313003, already holds sessions 52 to 57.

Session 82 (As-Built §XCV.2) bisected the commits on the port side, each to 3 600 s in a scratch
worktree. 0313003 reproduces session 52's answer: trip 22.1 at 134.5 s, 95.5 and 137.8 bar a at
2 000 and 3 000 s, and 22.2 not reached.

* **15e66c2 (sessions 62-67) moves it.** Later commits move it by about 1 bar.
* **Inside 15e66c2, 322E002's low-N/C branch alone restores it** (B-106 and B-111, decisions 142 and
  147). With that switch off on HEAD, trip 22.1 latches at 135.4 s, PT-329201 reads 95.1 and 136.1 bar
  a at 2 000 and 3 000 s, and 22.2 is not reached to 3 600 s. B-105's wash departure, in the same
  commit, adds about 2 bar by 1 500 s.
* **The cold start runs NH3-lean**, AT-322701 at about 2.0 for its first 20 minutes. Below a melt N/C
  of 3.0 the branch adds the Extended UNIQUAC rise toward the azeotrope: 630 bar at N/C 2.0 and
  170 C, carried to the live temperature on the condenser's 23 kJ/mol law. By the law, 322E002 then
  condenses less and the loop rises faster. That is inferred: PI-322E002 and its saturation fraction
  are not in the Phase 7 record.
* **Taking the rise at the melt's live temperature was measured and does not restore the start**:
  22.2 latches at 3 165 s.
* LT-322504 at 0 % and LT-329501 at 100 % are not distinguishable from 0313003's to 3 600 s.

Options:

* (a) accept the new answer as the engine's under decisions 142 and 147, and re-baseline decision
  110's cold start (session 52's own answer already sat 1.5 bar under the start-up band);
* (b) bound the branch's reach below N/C 2.6 (decision 147's docstring examples; Session 83 found the decision states no range), on a
  source: the melt's bubble pressure below N/C 2.6 from the archive after CLAUDE.md §4's two
  searches, no value taken from the model alone.

Recommended: first the evidence that decides between them. Run §4's search for the melt's bubble
pressure below N/C 2.6, and check whether the 3 June 2025 start-up trend carries AY-322701 through
N/C ≈ 2 without the overshoot. Then (b) if a source bounds the rise, otherwise (a). Whichever is
chosen, run the full 16 000 s cold start and fit it against the start-up band before re-baselining.

Session 83 (As-Built §XCVI.1) gathered the evidence and ran the cold start to 16 000 s.

* **No datum for the melt's bubble pressure below N/C 2.6** is in either archive: the fundamentals and the
  Uhde manual are qualitative, and Voskov & Voronin's grid is cited but not held.
* **The plant's start-up runs the loop NH3-rich.** On 3 June 2025 AY-322701 reads 3.69, 3.32 and 3.16, and
  PT-329201 peaks at 141.9 bar g. The SOP feeds N/C 3.0 until the reactor overflows.
* **With the branch off:** no trip 22.2, tau 1350 s, dead time 540 s, final 137.45 bar g, 322R001 not full by 16 000 s (LT-322504 36 % at 8 000 s, where session 52 was full). Session 52 gave 1 305 s, 555 s and 136.04 bar g.
* **On the SOP's feed ratio with the branch on**, the trip moves from 3 322 s to 5 863 s, after the ratio
  returns to design at the reactor's overflow.
* The engine's reactor overflow reads N/C 2.00 (stoichiometric carbamate) for its first half hour on every
  version and ratio.

Options, revised:

* (a) accept, and re-baseline decision 110's cold start on the branch;
* (b) bound the branch below a melt N/C. Decision 147 states no validity range: its 2.6-3.0 figures are
  docstring examples, so any bound is unsourced. And the branch fully off (the most any bound recovers)
  is still out of the band: tau 1 350 s, final 137.45 bar g, 322R001 not full by 16 000 s;
* (c) re-examine the early cold start's melt, which reads stoichiometric carbamate where the plant's loop
  is NH3-rich.

Open: with the branch off, LT-322504 reads 36 % at 8 000 s where session 52's reactor was full. The
branch restores the start only to 3 600 s. The B-104 discharge cap (15e66c2) and f21f058's bundle are
untested candidates. The SOP candidate tested only the filling ratio: the reactor's overflow was a proxy
(LI-322501 at 3 %), the ratio returned to the design 2.023, not the SOP's 2.0, and the SOP's trim of the
reactor's N/C to 2.9-3.1 was not modelled.

Recommended (this supersedes Session 82's recommendation): (a). No source bounds the rise, and even the
branch fully off returns only decision 110's own out-of-band answer.

# Section C — Calibration Deferrals

Items found during the port where V1's behaviour is reproduced exactly, the evidence says it is
not the plant's, and the correction is deliberately deferred: making it now would move a ported
relation off V1 before the Phase 7 steady-state and transient comparisons have been run, and
those comparisons are what show a re-tuning to be safe. Each item keeps its measured evidence
and the test that pins it, and each still needs the process engineer's decision before its
stated gate. Item numbers continue Section B's, so every reference to them stays valid.

*(None open. B-31, B-45, B-48, B-52, B-72, B-74 and B-78 were decided or signed off and closed on
2026-10-16, session 54, As-Built §LXX.2 and §LXX.4.)*

---

# Open data gaps

*(Populate per `Claude.md` §4: any datum that `References\`, the vendor archive and the V1 source
all fail to supply. Empty at fork time.)*

*Accepted by the process engineer on 2026-10-16 as the final V1.1 ledger (`project.md` decision 128),
19 rows, one closed since in session 58 (decision 130); one added in session 62, 322E001's U:
the archive is searched; each row below needs a vendor curve or the plant DCS's database, and keeps
its stand-in, assumption or V1 value as built. Session 69 (As-Built Part LXXXIV) searched every row
again — `D:\Work\Urea Simulation` and `D:\Work\Urea Simulation Docs` and their subfolders (486
documents text-extracted, the faceplate and trend photographs read), then the vendor archive — and
closed four: the control valves no set listed (Fisher's UD-MR-G00-DZ-0014, never read before:
LV-328503, LV-328504, HV-329602 and the 323D001 vent, tagged TV-323013), LV-324501A / B and
PV-329207C / HV-329601 (Flowserve's Pos. 148-149, 65 and 76, on summary pages earlier sessions had
not reached), all seven wired (decision 150); and 322E006's cooling water (PFD 28, streams 1010 /
1011, 14 t/h; decision 151). 15 rows remain. Session 71 (As-Built Part LXXXVI) audited an external report on five rows against the code and the archives and closed two by the process engineer's decision (`project.md` decision 153): 322C001's bottom head volume, the arrangement drawing's dimensions on DIN 28013's geometry, and the urea-melt Henry constant, a quantity no source holds; the Neldisc row annotated and kept linear. 13 rows remain. Session 72 (As-Built Part LXXXVII) read the 26 photographs of `References/Gaps Closure/Gaps` (22-24 October 2026) and the replacement stripper's folder: AI-329701's present range found, 0-30 uS/cm, and its row closed (decision 156); five of the eight tuning rows wired; the bleed valves' strokes found on a two-day trend; the TT-322015, LT-323503 and 322E001 rows annotated. 12 rows remain. Sessions 73 and 74 (As-Built Part LXXXVIII): the bleed valves' row closed — the 8-10 October trend is the plant at 112.5 % load on deeper set points, and the model keeps the 1750 MTPD design basis (decisions 6, 47 and 159) — and the tuning row narrowed to FIC-335405, TIC-328008 and FFIC-335406 wired on their faceplates (decision 160). 11 rows remain.*

| Datum | Needed by | Searched | Status |
|---|---|---|---|
| 322F001 nozzle and mixing-throat geometry, its loss coefficients, and its performance diagrams | `control/jet_pump.py`, `data/unit_322f001.py` | `References/Datasheets/322F001 Design Calculations.pdf` (UD-AU-322-DZ-0013-003), read from the scan 2026-10-03: AD 2000 strength calculations only; the vendor archive's 322F001 file — the arrangement drawing (-002: the throats drawn, not dimensioned), the operating instructions (-005: §5 names 14 performance diagrams, not enclosed), the fabrication dossier (-006), Uhde's specification (EC-0013) — As-Built §LIX.4 | **no vendor geometry or curve exists in either archive** (obtainable from Körting, order 2/131/4/04219). Both areas are back-solved from the licensor design duty through open-literature loss coefficients (Cunningham; ESDU 85032), stated openly at the constants and applied uniformly. The design point is exact either way; the STALL MARGIN is not — B-12's 90.7 %, signed off 2026-10-16 on the momentum closure (As-Built §LXXI.3); Körting's 14 diagrams would confirm it. Session 81 (As-Built §XCIV.5): at Book2's 111 % set points with LT-329501 at 16.6 % (closing toward the plant's 10.8 %) the engine holds the sump with HIC-322602 at 58.7 %, where the plant runs 76 %; not conclusive, the level not settled. Session 82 (As-Built §XCV.3): at Book2's 92.3 % set points, with HIC-322602 solved down to 23 % (the plant runs 63 %), LT-329501 was still at 21 % and falling at the hold's end; not settled. Session 83 (As-Built §XCVI.2): 322F001's suction is proportional to the level; at Book2's 7.05 % even the 10 % spindle floor entrains 25.9 t/h of the 58.9 the sump must pass (lowest holdable about 16 % at 92.3 %, 12.5 % at 111 %), where the plant holds 7-11 % at 63-76 %. |
| TT-322015's H2 hysteresis | I 22.1's release (B-56, decided) | AC4's application software UD-MR-G00-FF-0004 (PC22.5.1 reads "TT-322015:VALUE>H2"); the loop summary T 322015 (AH, SAHH, range 0-200 C); P&ID 102; the TOC (no alarm and trip setting list) | **H2 found: 110 C**, the plant DCS's readback of 2026-10-13, built (decision 103); the hysteresis open — V1's 2 K kept, cleared below 108 C; session 58: the research PDF's "ABB default 1 % of span" cites third-party manuals, not the plant's database — consistent with the stand-in, not a datum; session 72: the DCS's object display of TT-322015 ("LP ABSORBER VENT", photograph of 24 October 2026, `References/Gaps Closure/Gaps/20261024_031042.jpg`) shows range 0-200 C, H1 100.0, H2 110.0, alarm delay 0 and no hysteresis field — H2 confirmed, the hysteresis still not shown |
| Körting performance curves of 324F002, 324F004, 324F005 (suction capacity on suction, discharge and motive pressure) | B-57's decided interpolation (built on the synthesized maps, As-Built §XLIX.4; their capacity on the PFD's design loads, B-61, decided, §L.1); a measured curve would validate the in-situ factors (0.919, 0.336, 0.497) | Uhde's specifications UD-AU-324-EC-0007/-0009/-0010; Körting's instructions UD-AU-324-DZ-0007-006, -0009-005, -0010-005; design calculations -004; fabrication dossiers -007/-006; `References/Datasheets/324F00x` (As-Built §XLVIII.2; their design calculations re-read 2026-10-03: AD 2000 strength calculations, §LIX.4) | **no curve exists in this archive**: one duty point per ejector, Körting's generic molar-mass correction; 324F004/F005's nozzle and diffuser throats; 324F002's nozzle not given. Obtainable only from Körting (order 2/115/4/09674, 2/232/4/00503); session 58: the research PDF's 324F002 nozzle (19.33 mm, from 324F004's and 324F005's choked flux) is the construction the port already makes (`ejector_map`, the duty's motive choked at its motive state); not a vendor datum, the mixing throat and the curves still missing |
| LT-324501's taps | LI-324501 between its taps (decision 33's class) | the loop summary L 324501 (range 0-100 %, 80 mm nozzle, no tap distance); UD-AU-324-EC-0008's narrative: the level is measured in the barometric leg to 335P001, not in 324F003 | open — LI-324501 on V1's holdup ratio (As-Built §L.4); session 58: 324F003's trim isometric UD-RL-100-MB-0766 carries vents and drains only |
| AC4 PC21's limits and elements: FY-322403's L2; PT-321211 / 221's L2; ST-321952 / 953's H2; the T elements' mode (on- or off-delay); the SR flip-flops' dominance; TRIP_84_8_FLAG1's L2 | trips 21.2, 21.8 and 21.10 as built (A-12, decided and built 2026-10-09, As-Built §LXV.6) | AC4's application software UD-MR-G00-FF-0004 pages 5, 7, 20 (read from the scans: the limits are database entries, "VALUE<L2"; the timers drawn as a symbol the scan does not resolve); the functional diagram UD-MR-321-FF-0002 page 5 (PDYSLL 0.1 bar); session 57 (As-Built §LXXIII.2): the five hand switches' loop summaries read (UD-MR-321-EC-0001, -322-, -323-: three control-room keyswitches, HS-321603 and HS-321604 emergency shut-off switches, control-room and local), and TRIP_84_8_FLAG1 traced to the Safeguard SG1, UD-MR-G00-FF-0006 PC15.1.5: the instrument air's low pressure, two of PT-384207A / B / C below L2 (loop summaries UD-MR-384-EC-0001: ZALL, 4.5 bar g normal, 0-16 bar g, no setting printed), latched until RS_TR_84_8; PC21.5.1's flip-flops read in full: 21.2 also resets XVY-322903 (.15) and XVY_322902 (.14, through SG1) — built (decision 127) | open — database values: FY-322403's L2 V1's 5 %, PDY's L2 0.1 bar, the T elements on-delays, the reset dominant; PT-321211 / 221 and ST-321952 / 953 not modelled (healthy); TRIP_84_8 healthy, the instrument air outside the simulation; session 58: the research PDF's ABB element semantics (SR reset-dominant, TON on-delays) cite third-party manuals and agree with the stand-ins; not the plant's database |
| Trip 22.2's logic and set point | 22.2 (V1's 155.0 / 148.0 bar a, kept by the process engineer 2026-10-09) | AC4's PC22 (pages 25-56): no 22.2; XV-322902 is commanded from the Safeguard SG1 (PC22.5.6: DAT1:14 VALUE11), whose PC20 (UD-MR-G00-FF-0006 pages 53-58, unit 320's ESD) writes XVY_322902 from an AC4 input (DAT29:5 VALUE2); session 57 (As-Built §LXXIII.7) traced it: AC4 PC21.5.1 .14, a flip-flop set by HS-322902 and reset by 21.2's flag lost or trip 20.1, ANDed in SG1 PC20.1.1 .32 with TRIP_20_1_FLAG1 — 320K002's machine trip, whose causes (pages 55-58) are the machine's own: the turbine exhaust's PSHH-320207 (320E005's inlet), vibration, overspeed, lube oil, the knock-out drums; no synthesis pressure enters either; external reports (2026-10-13): one OCR-searched AC4, SG1 and SG2 in full and found no 22.2, the other lists initiators (TSHH-322015, PSL-322202 145 bar, PSH-322224 30 bar) from a `Trip22-1_master.doc` not in `References/` | **not in the archive** (verified, session 57): neither AC4 nor SG1 draws a synthesis high-high pressure trip; V1's logic and set point kept by the process engineer's decision of 2026-10-09; the second report's initiators are 22.1's document's and unverified; session 58: the research PDF's reading — 22.2 a proxy for a high-high CO2 discharge pressure on 320K002's fourth stage in SG1's trip 20.1 — is not what PC20.1.1 draws (pages 55-58): its pressure initiators are PSHH-320207 (320E005's inlet, the turbine side) and the low pressures of PT-320251 / 280 / 360; no CO2 discharge pressure enters it |
| Metso Neldisc characteristic above the last printed travel (all twelve: PV-329203 above 61 %, PV-329212 above 70.5 %, FV-329401 and PV-329202 above 52.9 %, PV-329204 above 77.7 %, PV-329207A above 64.2 %, PV-329207B and PV-329208 above 63.3 / 58 %, FV-329409 above 63.5 %; since session 59 HV-323605 above 78.1 %, PV-323203 above 44.6 %, TV-328002 above 90.5 %) | the valves on their vendor trims (decisions 108, 113, 116, 131) | UD-MR-G00-DZ-0031-009 pages 20-33 (two or three cases each, no curve named) | assumed — linear from the last printed point to the rated Cv at full travel (As-Built §LXVII.6, §LXIX.3-5); session 69: Uhde's instrument specifications in Metso's file (UD-MR-G00-DZ-0031-001, 79 pages OCR-searched; UD-MR-G00-EC-0022) name the Neldiscs' characteristic "equal percentage" and print no curve; nor do the instrumentation drawings (-006) or the L1-series instructions (-012), also read; session 71: the Neles bulletins an external report tabulates (2SL120EN, 2LW22EN, 2LBF20EN) are in no archive (`References/`, `Urea Simulation Docs` and the vendor archive searched by name) and miss the sheets' own printed points by up to 30 % (FV-329401 0.228 of rated at 52.9 % against the bulletin's 0.326); measured on the sheets' points, the linear chord departs from the bulletin's curve, rescaled through the last point and the rated Cv, by +13.4 % (PV-323203 at 60 %) to -4.7 % (HV-323605 at 90 %); every design stroke lies below its last printed travel (PV-329207A shut), so the design point does not depend on it; kept linear by the process engineer (decision 153, As-Built §LXXXVI.4) |
| LT-323503's L2 hysteresis | 323P008's restart (B-96, decided) | AC4 UD-MR-G00-FF-0004 PC23.1.9 / 1.10 (the limit a database value); UD-AU-323-EC-0017 (no instrument); session 51 | **assumed 2 %** — trip below 5 %, restart at 7 %, the stand-in the process engineer chose 2026-10-15 (TT-322015's 2 K convention), As-Built §LXVIII.2; session 58: the research PDF's "ABB default 1 % of span" cites third-party manuals, not the plant's database — consistent with the stand-in, not a datum; session 72: LT-323503's faceplate (`References/Gaps Closure/Gaps/20261024_033527.jpg`): H1 80.0 %, L1 20.0 %, L2 5.0 %, alarm delay 0 s — the 5 % trip limit confirmed, no hysteresis shown |
| The DCS tuning-table row of FIC-335405 | the loop on the plant's tuning (decisions 76, 77) | `References/Master_PID_Tuning_Constants.md` (no row); the faceplate photographs of 10 July 2026; session 72: the faceplates of 24 October 2026 (`References/Gaps Closure/Gaps/20261024_0336*.jpg` to `_034014.jpg`) | open — FIC-335405 not photographed; V1's 100 per t/h and 15 s kept. Seven of the eight rows this row held are wired on their faceplates: TIC-323012, FIC-328404, PIC-329205, LIC-329502 and TIC-328012 (decision 156); TIC-328008, 1.00 and 60 s on 0-100 wt% water, carried onto 737's mol% by its local slope, and FFIC-335406, a ratio station on RAT H 0.0080 and OUT H 0.80 t/h (decision 160) |
| LT-329505's tap elevations | LI-329505 between its taps (decision 33's class) | the loop summary L 329505 (taps 3000 mm apart, no elevation); session 57: 324E001's general assembly UD-AU-324-DZ-0001-001 (scan, read from the image): nozzle N5 "LT 329505", DN25, 2290 mm below EL +17419, so EL +15129; no second LT nozzle in its table (N1-N7) | **partly found** — the upper tap; the lower, 3000 mm below (EL +12129, calculated), is off the vessel and not traced; LI-329505 on V1's holdup ratio; LV-329505 itself on Flowserve's trim since session 52 (its normal capacity calculated by IEC 60534-2-1, As-Built §LXVIII.5); session 58: 324E001's shell trim isometric UD-RL-100-MB-0182 sheet B3: N5 at EL +15129 runs down a DN25 line to the transmitter, item 13 "PRESS. INST. LT 329505", at EL +7308 — a wet reference leg; the other leg is "conn. to Ermeto piping", instrument tubing no piping isometric carries (sheets B1, B2, B4: vent and drain blinds) |
| 322E001's service heat-transfer coefficient and corrected mean temperature difference | the shell's duty bound (decision 139) | `References/Datasheets/322E001 Datasheet.pdf` (UD-AU-322-EC-0003, page 4, read from the scan: rows 74 and 76 blank); the vendor archive's 322E001 file (UD-AM-G00-AB-0022 pages 871-874), session 62; **session 72: the 2,950-tube replacement's folder** (`Licensor and Vendor Documentation/New Stripper`: Stamicarbon's process data sheet A4-101124, Resta's 6355 drawings and part list, the IOM 2323) | open — the replacement's process data sheet prints its duty, 41 738 kW, and its terminal temperatures (212 C steam, gas out at 187 C, liquor out at 173 C), not its coefficient or corrected MTD; it refers to Stamicarbon's proprietary equipment data sheet A4-93540, not in the folder. Terminal-temperature U.A: 1 325.7 kW/K (V1's bundle 1 160.5); per square metre the two agree within 0.65 %. The bound runs on the design duty times the two U.A's ratio, 1.142 (decision 154) |
