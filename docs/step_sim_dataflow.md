# step_sim() data flow — the boundary-crossing map

**GENERATED FILE** — produced by `tools/analyse_step_sim.py` from
`D:\Work\Urea Simulation\backend\main.py`. Re-run it rather than editing it.

## Why this exists

V1's `step_sim()` is one straight-line function of **4051 lines** covering **38 sections**. Splitting it into
unit-operation modules means turning every value that crosses a section boundary into
either a function argument (a same-tick process coupling) or engine state (a one-tick
recycle tear). This table is the checklist of those values.

`handoff.md` A-4 gates Phase 4 on this document existing.

## How to read it, and what it does NOT promise

This is a **static** map, so it over-reports: a name written on both sides of a branch
looks like a coupling from each. It never under-reports a plain assignment, which is
what matters — work through it as a checklist, resolving each entry by reading that
code. Anything it does not flag is not a plain cross-section assignment.

Section numbers below index the table in §1.


## 1. Sections

| # | line | section |
|---|---|---|
| 0 | 7269 | function preamble |
| 1 | 7281 | CO2 feed line (320K002 -> XV-322902 -> 322E001), vent via PV-322203 |
| 2 | 7298 | 320K002 on its polytropic map, feeding a CAPACITIVE pressure NODE (report D-5) |
| 3 | 7538 | HP Stripper 322E001: reactor effluent + live CO2 strip gas -> top gas (322E002) |
| 4 | 7823 | Steam balance handshake (reverse pass): forward duties -> header mass draws -> Euler tick. |
| 5 | 7989 | 322E003 HP Scrubber: reactor off-gas + weak carbamate (323P001 A/B) -> off-gas line |
| 6 | 8183 | Section-322 tear display lags (compute ONCE per tick -> shared by both telemetry views) |
| 7 | 8254 | Stage 1: Rectifying Column 323C003 + Recirc Heater 323E002  (hold 135 C) |
| 8 | 8363 | 323C003 -> 323F004 drain line: plug-flow transport of the CLOSED packet |
| 9 | 8410 | Stage 2: Flash Tank 323F004  (adiabatic letdown 4.1 -> 1.13 bar, hold 106 C) |
| 10 | 8460 | 323F004 -> 323F010 drain line (LV-323505): plug-flow transport of the CLOSED packet |
| 11 | 8509 | Stage 3: Pre-evaporator 323F010 + Heater 323E010  (vacuum 0.46 bar, hold 99 C) |
| 12 | 8564 | 323F010 -> 323D002 product line: plug-flow transport of the CLOSED packet |
| 13 | 8656 | Stage 4: Urea Solution Tank 323D002  (atmospheric, two compartments) |
| 14 | 8847 | Stage 1 : 323C005 vent scrub -> 328V001 -> Comp-II feed |
| 15 | 8883 | Stage 2 : 328D003 active bays I/II + communicating accumulation bay III |
| 16 | 8952 | 328E007 feed/effluent interchanger (AUDIT C10) |
| 17 | 8965 | Stage 3 : 328C002  Desorber-I (bottoms 139°C, floats PIC-328202) |
| 18 | 9062 | Stage 4 : 328C003  Hydrolyser (200°C, MP-steam 911) |
| 19 | 9169 | Stage 5 : 328C004  Desorber-II (143°C, LP-steam 931, FFIC) |
| 20 | 9255 | Stage 6 : 328D001  Desorber-I reflux drum (61°C, 328E004) |
| 21 | 9349 | AUDIT C4 : unit-328 ENERGY-CLOSURE DIAGNOSTIC |
| 22 | 9405 | Stage 7 : 322C001  LP absorber (43°C, live GCB off-gas) |
| 23 | 9513 | Stage 8 : 323E003 + 323D001  LPCC (74°C, tempered water) |
| 24 | 9580 | Stage 9 : 323E011 + 323D011  LP carbamate condenser (45°C) |
| 25 | 9665 | recycle-tear writes (one-tick delay -> next step reads these) |
| 26 | 9695 | Stage 1 : Evaporator I 324E001 + separator 324F001 (0.33 bar a, 130 C) |
| 27 | 9696 | 323D002 -> 324E001 feed line: plug-flow transport of the CLOSED packet |
| 28 | 9885 | 324E001 steam-side condensate : LIC-329505 "active controlled steam trap" |
| 29 | 9896 | Stage 2 : Evaporator II 324E003 + separator 324F003 (0.131 bar a, 140 C) |
| 30 | 10029 | UF85 ratio injection (FFIC-335406 ratio station -> FIC-335405 flow) |
| 31 | 10035 | four-condenser vacuum train |
| 32 | 10066 | recycle tear write (one-tick delay -> next step reads it) |
| 33 | 10072 | auxiliary faceplate trims (stepped for liveness; off the network) |
| 34 | 10086 | Trips (P1-2 stateful interlocks) |
| 35 | 10135 | Trip 22.1 (LP absorber 322C001 over-temperature steam-flood) |
| 36 | 10150 | Trip 22.2 (synthesis high-high pressure -> ESD); not built: in no plant document (decision 189) |
| 37 | 10181 | uniform process-stream registry (clickable stream inspector) |

## 2. One-tick recycle tears — `s.<attr>` read before it is written

These are the recycles. V1 writes them at the end of a tick for the **next** tick to
read, so each becomes an explicit piece of engine state with a documented one-tick
delay — not a hidden ordering dependency.

**39 tears.**

| state attribute | written in | read in |
|---|---|---|
| `s.XV_321901` | 34 | 0,37 |
| `s.XV_322901` | 34 | 0,37 |
| `s.XV_322902` | 36 | 1,37 |
| `s.XV_322915` | 35 | 22,37 |
| `s.a328_c001_T` | 22 | 0,13,14,22,35,37 |
| `s.a328_c002_T` | 17 | 13,17,18,19,20,37 |
| `s.a328_c003_P` | 18 | 17,18,37 |
| `s.a328_c003_T` | 18 | 13,17,18,33,37 |
| `s.a328_c004_P` | 19 | 18,19,37 |
| `s.a328_c004_T` | 19 | 13,16,19,37 |
| `s.a328_d001_P` | 20 | 17,20,37 |
| `s.a328_d001_T` | 20 | 13,20,21,37 |
| `s.a328_d003_TI` | 15 | 13,15,37 |
| `s.a328_d003_TII` | 15 | 13,15,16,20,21,37 |
| `s.p_syn_bara` | 37 | 2,3,5,36,37 |
| `s.r3232_d001_P` | 23 | 8,23,37 |
| `s.r3232_e011_P` | 24 | 10,23,24,37 |
| `s.r323_c003_M` | 8 | 7,8,37 |
| `s.r323_c003_P` | 8 | 7,8,37 |
| `s.r323_c003_T` | 7 | 6,7,8,37 |
| `s.r323_f004_M` | 10 | 9,10,37 |
| `s.r323_f004_P` | 10 | 7,9,10,37 |
| `s.r323_f004_T` | 10 | 6,9,10,37 |
| `s.r323_f010_M` | 12 | 11,12,37 |
| `s.r323_f010_P` | 12 | 9,11,12,37 |
| `s.r323_f010_T` | 12 | 6,11,12,37 |
| `s.r324_f001_P` | 27 | 12,27,31,37 |
| `s.react_T_overflow` | 3 | 0,3,5,37 |
| `s.react_level_pct` | 4 | 3,4,5 |
| `s.react_overflow_kmolh` | 4 | 3 |
| `s.scrub_level_pct` | 5 | 2,5,37 |
| `s.tank_level_frac` | 2 | 0,2,34,37 |
| `s.w_c003` | 8 | 6,7,8,37 |
| `s.w_e003` | 29 | 13,29,37 |
| `s.w_f004` | 10 | 6,9,10,37 |
| `s.w_f010` | 12 | 6,11,12,37 |
| `s.y_328_748` | 18 | 17,18 |
| `s.y_328_750` | 19 | 17,19 |
| `s.y_scrub_ovf` | 5 | 2 |

## 3. Same-tick couplings — locals written in one section, read in a later one

**232 in total**, split by WHO READS THEM, because the two halves become
different things and only one of them constrains the port.

Sections 21, 33, 37 publish rather than compute: they consume converged values and
feed nothing back into the plant. A value read only by those is **telemetry** — it
becomes a field on the state snapshot, not an argument between two unit modules, and
it can be wired at the end of Phase 4 without blocking any unit port.


### 3a. Process couplings — 125

These are the ones that constrain the port. Each becomes an argument, or a field on
a small result object, when the producing section becomes a unit module.

`docs/coupling_resolution.md` carries the row-by-row resolution.

| value | written in | read in |
|---|---|---|
| `F_CO2_syn_th` | 2 | 3 |
| `M_c003_pre` | 7,18 | 8,18 |
| `PDY_A` | 2 | 34,37 |
| `PDY_B` | 2 | 34,37 |
| `P_c003` | 7,18 | 18 |
| `Q_e001_kw` | 27 | 28,37 |
| `Q_e010_kw` | 11 | 12,37 |
| `TT_323001` | 3 | 6,7 |
| `T_314_in` | 8 | 9,10 |
| `T_317_in` | 12 | 13 |
| `T_319_in` | 10 | 11,12 |
| `T_738` | 16 | 17,37 |
| `T_746` | 18 | 19,33,37 |
| `T_bot_disp` | 3 | 6 |
| `T_dep_314` | 7 | 8 |
| `Tc003` | 18 | 19 |
| `_cp` | 6 | 8,10 |
| `_phi_sp_theta` | 4 | 5 |
| `a_rec` | 3 | 4 |
| `blow_322501_kgh` | 3 | 23,37 |
| `blow_323501_kgh` | 7 | 23,24,37 |
| `blow_323505_kgh` | 9 | 12,24,37 |
| `bot_c005` | 14 | 15,37 |
| `cp_314_in` | 8 | 9,10 |
| `cp_319_in` | 10 | 11,12 |
| `cp_322c001` | 13 | 22 |
| `cp_328c002` | 13 | 17 |
| `cp_328c003` | 13 | 18 |
| `cp_328c004` | 13 | 19 |
| `cp_328d001` | 13 | 20 |
| `cp_328d3i` | 13 | 15 |
| `cp_328d3ii` | 13 | 15 |
| `cp_331` | 6 | 11,12 |
| `cp_c003` | 6 | 7,8 |
| `cp_f004` | 6 | 9,10 |
| `cp_f010` | 6 | 11,12 |
| `cp_feed323` | 6 | 7 |
| `disch_open` | 0 | 2,34 |
| `drain_kgh` | 3 | 6,37 |
| `ej` | 2 | 3,4,5,6,37 |
| `fa202_m` | 27 | 31,37 |
| `fa203_m` | 29 | 31,37 |
| `feed_factor` | 1 | 2 |
| `hpcc` | 3 | 4,5,6,37 |
| `hv604` | 5 | 6,22,37 |
| `in_c002` | 17 | 20 |
| `lic501_op` | 20,29 | 29 |
| `lic503_op` | 17,24 | 24 |
| `lvl_c003` | 7,18 | 18 |
| `m702_prev` | 13 | 14,37 |
| `m708_prev` | 13 | 14,37 |
| `m718A_prev` | 13 | 20,21,37 |
| `m718B_prev` | 13 | 23 |
| `m739_prev` | 13 | 15,16,21 |
| `m744_prev` | 13 | 19 |
| `m748_prev` | 13 | 17,37 |
| `m750_prev` | 13 | 17,37 |
| `m756_prev` | 13 | 14,37 |
| `m775_prev` | 13 | 17,20,37 |
| `m931_prev` | 13 | 19,37 |
| `m_305` | 7 | 8,23,37 |
| `m_314` | 7 | 8,37 |
| `m_314_in` | 8 | 9,10 |
| `m_317` | 11 | 12,37 |
| `m_317_in` | 12 | 13 |
| `m_319` | 9 | 10,37 |
| `m_319_in` | 10 | 11,12 |
| `m_321` | 23 | 24,37 |
| `m_324` | 13 | 27,37 |
| `m_331` | 11 | 12,37 |
| `m_402` | 15 | 24,37 |
| `m_701` | 9 | 10,24,37 |
| `m_718A` | 24 | 25,37 |
| `m_718B` | 24 | 25,37 |
| `m_735` | 15 | 16,17,21,37 |
| `m_737` | 17 | 20,37 |
| `m_739` | 19 | 25,37 |
| `m_743` | 17 | 18,37 |
| `m_744` | 15 | 25,37 |
| `m_746` | 18 | 19 |
| `m_747` | 18 | 19,37 |
| `m_748` | 18 | 25,37 |
| `m_750` | 19 | 25,37 |
| `m_755` | 15 | 22,37 |
| `m_756` | 22 | 25,37 |
| `m_775` | 20 | 25,37 |
| `m_776` | 20 | 21,23,37 |
| `m_786_d001` | 20 | 21,24,37 |
| `m_793` | 15 | 20,21,37 |
| `m_931` | 19 | 21,25,37 |
| `m_evap` | 11 | 12,37 |
| `m_feed_323` | 6 | 7,8,37 |
| `m_flash_gas` | 7 | 8,23 |
| `m_fwd` | 29 | 30,37 |
| `m_p1` | 27 | 29,37 |
| `m_pool_vap` | 7 | 8,23 |
| `m_recyc` | 29 | 32,37 |
| `m_v011` | 24 | 25,37 |
| `mot9605_m` | 27 | 31,37 |
| `n_blow_323505` | 9 | 12 |
| `new_T` | 3 | 4 |
| `p` | 2 | 12,27,29 |
| `phi_fwd` | 2 | 4,36,37 |
| `pic` | 1 | 2,37 |
| `pic203_op` | 24,27 | 27 |
| `pull` | 12,27,29 | 27,29 |
| `pull_f010` | 12 | 27,31 |
| `pv_open` | 1 | 2,37 |
| `react` | 3 | 4,5,6,37 |
| `react_carry_kmolh` | 4 | 5 |
| `route501` | 29 | 30,32,37 |
| `scrub` | 5 | 6,37 |
| `strip` | 3 | 4,5,6,37 |
| `sub_703` | 12 | 27,31 |
| `suct_open` | 0 | 2 |
| `v1_m` | 27 | 31,37 |
| `v2_m` | 29 | 31,37 |
| `vent` | 27,29 | 29 |
| `w1_live` | 27 | 29,37 |
| `w_314_in` | 8 | 10 |
| `w_317_in` | 12 | 13 |
| `w_319_in` | 10 | 12 |
| `w_dep_314` | 7 | 8 |
| `w_feed_323` | 6 | 8 |
| `y_blow_323505` | 9 | 12 |

### 3b. Telemetry only — 107

Read exclusively by a publishing section, so each becomes a snapshot field.

<details><summary>list</summary>

| value | written in | read in |
|---|---|---|
| `FT_322403` | 2 | 37 |
| `FY_322403` | 2 | 37 |
| `F_CO2_feed_kgh` | 2 | 37 |
| `F_pump_total_th` | 2 | 37 |
| `LT_329501_ind` | 5 | 37 |
| `Load_pct` | 2 | 37 |
| `NC_A` | 2 | 37 |
| `NC_B` | 2 | 37 |
| `PT_A` | 2 | 37 |
| `PT_B` | 2 | 37 |
| `PY` | 2 | 37 |
| `P_LP_hpcc` | 3 | 37 |
| `P_disch_header_barG` | 36 | 37 |
| `P_line_bara` | 2 | 37 |
| `P_strip_live` | 3 | 37 |
| `Q_e002_kw` | 7 | 37 |
| `Q_e003_kw` | 29 | 37 |
| `Q_e004` | 20 | 21 |
| `Q_strip_kjh` | 4 | 37 |
| `TDY_329125` | 5 | 37 |
| `TI_321020` | 2 | 37 |
| `T_740` | 16 | 21,37 |
| `T_feed_323` | 6 | 37 |
| `T_shell_lp` | 3 | 37 |
| `T_tw_ret` | 23 | 37 |
| `ab_c001` | 22 | 37 |
| `abs_c001` | 22 | 37 |
| `cond_gen` | 28 | 37 |
| `ctrl` | 2,37 | 37 |
| `d_AT322701` | 6 | 37 |
| `d_HPCC_P` | 6 | 37 |
| `d_TT322002` | 6 | 37 |
| `d_TT322004` | 6 | 37 |
| `d_TT322010` | 6 | 37 |
| `d_TT322011` | 6 | 37 |
| `d_TT322011l` | 6 | 37 |
| `d_TT322012` | 6 | 37 |
| `d_TT322013` | 6 | 37 |
| `d_TT323001` | 6 | 37 |
| `d_TT329125` | 6 | 37 |
| `feed1_m` | 27 | 37 |
| `feed2_m` | 29 | 37 |
| `fic` | 5 | 37 |
| `gas_hyd` | 18 | 37 |
| `gas_str` | 18 | 37 |
| `gcb_T` | 22 | 37 |
| `gcb_m` | 22 | 37 |
| `lic` | 3 | 37 |
| `lv_open` | 3 | 37 |
| `lva_stroke` | 29 | 37 |
| `lvb_stroke` | 29 | 37 |
| `lvl_d002_I` | 13 | 37 |
| `m_308` | 23 | 37 |
| `m_324_cond` | 31 | 37 |
| `m_324_vent` | 31 | 37 |
| `m_341` | 14 | 37 |
| `m_401` | 15 | 37 |
| `m_719` | 15 | 37 |
| `m_720` | 15 | 37 |
| `m_721` | 15 | 37 |
| `m_738` | 17 | 37 |
| `m_741` | 15 | 37 |
| `m_759` | 15 | 37 |
| `m_911` | 18 | 21,37 |
| `m_ccw_kgh` | 5 | 37 |
| `m_loop_frac` | 5 | 37 |
| `m_product` | 30 | 37 |
| `m_strip` | 4 | 37 |
| `m_uf` | 30 | 37 |
| `motive_nh3_kgh` | 2 | 37 |
| `p_chest_e001` | 27 | 37 |
| `p_chest_e003` | 29 | 37 |
| `ppm_urea_747` | 18 | 37 |
| `q328_in` | 21 | 37 |
| `q328_out` | 21 | 37 |
| `q328_react` | 21 | 37 |
| `q328_resid` | 21 | 37 |
| `q_e004_kw` | 5 | 37 |
| `recycle_selected` | 29 | 37 |
| `rho_d002` | 13 | 37 |
| `scrub_swell_noise` | 5 | 37 |
| `scrub_swell_pct` | 5 | 37 |
| `tic` | 5 | 37 |
| `tic13_op` | 23 | 37 |
| `uf_cascade` | 29 | 37 |
| `urea_in_328` | 18 | 37 |
| `v_II_full` | 13 | 37 |
| `vac324` | 31 | 37 |
| `vac_stream` | 31 | 37 |
| `vent_c001` | 22 | 37 |
| `w2_live` | 29 | 37 |
| `x_hyd_328` | 18 | 37 |
| `xi_c003` | 8 | 37 |
| `xi_e001` | 27 | 37 |
| `xi_e003` | 29 | 37 |
| `xi_f004` | 10 | 37 |
| `xi_f010` | 12 | 37 |
| `xi_hyd_328` | 18 | 37 |
| `y_305` | 8 | 37 |
| `y_701` | 10 | 37 |
| `y_737` | 17 | 37 |
| `y_748` | 18 | 37 |
| `y_750` | 19 | 37 |
| `y_evap` | 12 | 37 |
| `y_v1` | 27 | 37 |
| `y_v2` | 29 | 37 |
| `y_vent` | 22 | 37 |

</details>


## 4. Backward local reads — read before any write in this tick

Usually a loop-carried local or a name shadowed by a branch. Each needs a decision:
it is either a genuine tear that happens to live in a local rather than on `s`, or it
is an artefact of the flat layout that disappears when the section becomes a function.

**0 names.**

| value | written in | read earlier in |
|---|---|---|

## 5. Plant state that is read but never written here

Design constants, operator inputs and values other modules own. They become
constructor arguments or design-basis constants, not state.

**79 attributes.**

| state attribute | read in |
|---|---|
| `s.FFIC_329401` | 19,37 |
| `s.FFIC_335406` | 37 |
| `s.FIC_323401` | 15,37 |
| `s.FIC_323402` | 15,37 |
| `s.FIC_323418` | 24,37 |
| `s.FIC_324401` | 13,37 |
| `s.FIC_328402` | 15,37 |
| `s.FIC_328404` | 20,37 |
| `s.FIC_328405` | 15,37 |
| `s.FIC_328406` | 15,37 |
| `s.FIC_329401` | 19,37 |
| `s.FIC_329402` | 18,37 |
| `s.FIC_329409` | 5 |
| `s.FIC_335405` | 37 |
| `s.F_CO2_raw_th` | 2,37 |
| `s.HIC_322203` | 1,37 |
| `s.HIC_322602` | 2,4,37 |
| `s.HIC_322604` | 5,37 |
| `s.HIC_322605` | 3,4,37 |
| `s.HIC_323605` | 12,37 |
| `s.HIC_329605` | 27,37 |
| `s.HIC_329606` | 29,31,37 |
| `s.HV_323D002_TIE` | 13,37 |
| `s.LIC_322501` | 3 |
| `s.LIC_322502` | 22,37 |
| `s.LIC_323501` | 7,37 |
| `s.LIC_323502` | 23,37 |
| `s.LIC_323503` | 24,37 |
| `s.LIC_323505` | 9,37 |
| `s.LIC_323507` | 13,37 |
| `s.LIC_324501` | 29,37 |
| `s.LIC_328501` | 20,37 |
| `s.LIC_328503` | 17,37 |
| `s.LIC_328504` | 18,37 |
| `s.LIC_328505` | 19,37 |
| `s.LIC_329505` | 28,37 |
| `s.P329P006A` | 5,37 |
| `s.P329P006B` | 5,37 |
| `s.PIC_322201` | 22,37 |
| `s.PIC_322203` | 1 |
| `s.PIC_323202` | 23,37 |
| `s.PIC_323203` | 24,37 |
| `s.PIC_324202` | 27,37 |
| `s.PIC_324203` | 29,37 |
| `s.PIC_328202` | 20,37 |
| `s.PIC_328203` | 18,37 |
| `s.PIC_329202` | 7,37 |
| `s.PIC_329203` | 27,37 |
| `s.PIC_329208` | 11,37 |
| `s.PIC_329212` | 29,37 |
| `s.PIC_335201` | 29,37 |
| `s.SIC_321950` | 2,34,36 |
| `s.SIC_321951` | 2,34,36 |
| `s.SIC_323901` | 23,37 |
| `s.SIC_323902` | 33,37 |
| `s.TIC_323007` | 7,37 |
| `s.TIC_323012` | 11,37 |
| `s.TIC_323013` | 23,37 |
| `s.TIC_324001` | 27,37 |
| `s.TIC_324002` | 29,37 |
| `s.TIC_328002` | 20,37 |
| `s.TIC_328008` | 20,37 |
| `s.TIC_328012` | 33,37 |
| `s.TIC_329005` | 5 |
| `s.XV_322903` | 2,37 |
| `s.aux_pumps` | 15,37 |
| `s.controllers` | 37 |
| `s.cpl_flow_kgh` | 22,37 |
| `s.ext_override` | 37 |
| `s.flags` | 2,3,5,7,9,22,+1 |
| `s.pumpA` | 2,34,36,37 |
| `s.pumpB` | 2,34,36,37 |
| `s.ratio_SP` | 2,37 |
| `s.sim_mode` | 37 |
| `s.steam` | 3,4,7,11,27,29,+1 |
| `s.tank_P_top_barG` | 2,37 |
| `s.tlag` | 2,3,5,6,7,11,+15 |
| `s.trip_latched` | 34,35,36,37 |
| `s.trips` | 34,35,36,37 |

## 6. State owned within one section

**77 attributes** are written and read inside a single section,
so they move with that unit and need no boundary at all.

<details><summary>list</summary>

`s.F_CO2_th`, `s.F_CO2_vent_th`, `s.F_in_BL_th`, `s._debug_m_305`, `s._debug_m_feed_323`, `s._debug_m_flash`, `s._debug_m_pool`, `s.a323_c005_M`, `s.a323_c005_T`, `s.a328_c001_M`, `s.a328_c001_P`, `s.a328_c001_T_prev`, `s.a328_c001_w`, `s.a328_c002_M`, `s.a328_c002_P`, `s.a328_c002_T_prev`, `s.a328_c003_M`, `s.a328_c003_T_prev`, `s.a328_c004_M`, `s.a328_c004_T_prev`, `s.a328_d001_M`, `s.a328_d001_T_prev`, `s.a328_d003_MI`, `s.a328_d003_MII`, `s.a328_d003_MIII`, `s.a328_d003_TIII`, `s.co2_line_bara`, `s.hpcc_level_pct`, `s.hpcc_phi`, `s.k002_deliv_kgh`, `s.k002_speed`, `s.r3232_d001_M`, `s.r3232_e003_T`, `s.r3232_e011_M`, `s.r3232_e011_T`, `s.r3232_e011_T_prev`, `s.r323_d002_M_I`, `s.r323_d002_M_II`, `s.r323_d002_T`, `s.r323_e002_chest_P`, `s.r323_e010_chest_P`, `s.r324_e001_T`, `s.r324_e001_chest_P`, `s.r324_e001_cond_M`, `s.r324_e003_T`, `s.r324_e003_chest_P`, `s.r324_f001_M`, `s.r324_f003_M`, `s.r324_f003_P`, `s.ratio_PV`, `s.ratio_bal`, `s.react_L_feed`, `s.react_L_rec`, `s.react_T_node`, `s.react_T_offgas`, `s.react_W_feed`, `s.react_W_rec`, `s.react_conv_fac`, `s.react_fwd_wash`, `s.react_lt322504_pct`, `s.react_m_in_lag`, `s.react_m_liq`, `s.scrub_holdup_kg`, `s.sim_t`, `s.strip_level`, `s.syn_psv_open`, `s.syn_vap_excess_kg`, `s.tank_T_C`, `s.totalizer_t`, `s.w_328c002`, `s.w_328c003`, `s.w_328c004`, `s.w_d002`, `s.w_d002_II`, `s.w_e001`, `s.y_328_737`, `s.y_evap_f010`

</details>

