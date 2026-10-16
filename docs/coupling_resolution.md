# Resolving the same-tick process couplings

Companion to `docs/step_sim_dataflow.md`, which is GENERATED. This file is written by hand: each row below is the outcome of reading V1's own code at the writing site.

## Why this document is the gate on Phase 4

`step_sim()` is straight-line code, so a value computed in one place and used 800 lines later needs no declaration — the name is simply still in scope. Splitting the function into unit modules removes that scope, so every one of those values has to become something explicit. The generated map lists them; this file says what each one becomes.

A row left unresolved is not a style problem. It is a value that will be silently recomputed from the wrong state, or passed from the wrong tick, in a way that still runs and still closes its balance.

## What the static map over-reports, and why that is expected

The map is built by parsing, so a name written in two unrelated places looks like one value crossing a boundary. Two patterns account for every such case here:

* **Name reuse.** `M_c003_pre` is the 323C003 inventory in section 7 and the 328C003 inventory in section 18 — two vessels in two different plant units that happen to share a local name. Same for `P_c003`, `lvl_c003`, and three controller-output names.

* **Nested-closure parameters.** `p` is the argument of the 323F010 pressure-residual closure `_dpdt_f010(p)`, and of its two twins in the 324 vacuum train. It collides with the `for p, ctrl in ...` pump loop variable in section 2. `pull` and `vent` are locals inside those same closures.

Nine rows are artefacts of this kind. They are listed rather than filtered out, because "the analyser over-reported this one" is a claim that has to be checkable.

## One thing the static map UNDER-reports

Eleven `*_prev` names read from `s.tlag` with a design default:

```python
    m748_prev = s.tlag.get("R328_748", R328_C002_M748_DES)
```

That is LAST tick's flow. The parser cannot see through a `.get()` on a store dict, so these appear here as same-tick couplings when they are in fact one-tick recycle tears and belong with section 2 of the generated map. Each becomes an explicit engine-state field with a documented delay — which is the whole point of listing the tears separately. Finding these is the single most valuable thing this pass produced.

## The seven dispositions

| disposition | meaning |
|---|---|
| **ARTEFACT** | not a coupling |
| **TEAR** | one-tick tear |
| **PACKET** | transported packet |
| **PROPERTY** | tick-start property |
| **CONTROL** | control output |
| **RESULT** | unit result field |
| **ARG** | function argument |

| disposition | rows |
|---|---|
| ARTEFACT | 9 |
| TEAR | 12 |
| PACKET | 16 |
| PROPERTY | 13 |
| CONTROL | 6 |
| RESULT | 26 |
| ARG | 43 |
| **total** | **125** |

## The resolution

Section numbers index the table in `docs/step_sim_dataflow.md` section 1.

| value | written in | read in | disposition | becomes |
|---|---|---|---|---|
| `F_CO2_syn_th` | 2 | 3 | ARG | the CO2 feed the synthesis loop actually receives, i.e. the battery-limit flow after its transport dead time. Becomes the delayed feed signal the loop takes as input. |
| `M_c003_pre` | 7,18 | 8,18 | ARTEFACT | two unrelated locals sharing a name: 323C003 in section 7, 328C003 in section 18. Each stays inside its own unit module. |
| `PDY_A` | 2 | 34,37 | ARG | the 321P002 suction/discharge gauge differentials. Become fields of the pump block's own result, read by the trip logic. |
| `PDY_B` | 2 | 34,37 | ARG | the 321P002 suction/discharge gauge differentials. Become fields of the pump block's own result, read by the trip logic. |
| `P_c003` | 7,18 | 18 | ARTEFACT | two unrelated locals sharing a name: 323C003 in section 7, 328C003 in section 18. Each stays inside its own unit module. |
| `Q_e001_kw` | 27 | 28,37 | RESULT | an exchanger duty. Becomes a field of that exchanger's result. |
| `Q_e010_kw` | 11 | 12,37 | RESULT | an exchanger duty. Becomes a field of that exchanger's result. |
| `TT_323001` | 3 | 6,7 | ARG | the TT-323001 indication, derived from the stripper's displayed bottoms temperature. Becomes an instrument reading published by the stripper and consumed by 323C003. |
| `T_314_in` | 8 | 9,10 | PACKET | a field of the `StreamPacket` that `core.transport` already carries down this line. The four properties cross the boundary together by construction, so none of them becomes an argument of its own. 323C003 -> 323F004, arrival side. |
| `T_317_in` | 12 | 13 | PACKET | a field of the `StreamPacket` that `core.transport` already carries down this line. The four properties cross the boundary together by construction, so none of them becomes an argument of its own. 323F010 -> 323D002, arrival side. |
| `T_319_in` | 10 | 11,12 | PACKET | a field of the `StreamPacket` that `core.transport` already carries down this line. The four properties cross the boundary together by construction, so none of them becomes an argument of its own. 323F004 -> 323F010, arrival side. |
| `T_738` | 16 | 17,37 | RESULT | an interchanger or trim-cooler outlet temperature. Becomes a field of that exchanger's result. |
| `T_746` | 18 | 19,33,37 | RESULT | an interchanger or trim-cooler outlet temperature. Becomes a field of that exchanger's result. |
| `T_bot_disp` | 3 | 6 | RESULT | the stripper's displayed bottoms temperature, including the sump hot-film residence term. Becomes a field of the stripper result. |
| `T_dep_314` | 7 | 8 | PACKET | a field of the `StreamPacket` that `core.transport` already carries down this line. The four properties cross the boundary together by construction, so none of them becomes an argument of its own. 323C003 -> 323F004, departure side. |
| `Tc003` | 18 | 19 | TEAR | a local alias of the `s.a328_c003_T` tear, captured before section 18 advances it. 328C004 receives it as the incoming tear value, not as a same-tick argument. |
| `_cp` | 6 | 8,10 | PROPERTY | the anchored departure-form lambda itself. Becomes `thermo.empirical.urea_soln_cp` called with each stage's own design anchor; no value crosses a boundary at all. |
| `_phi_sp_theta` | 4 | 5 | CONTROL | an ejector spindle / area ratio from HIC-322602. Becomes a field of the ejector actuator's own state. |
| `a_rec` | 3 | 4 | ARG | the reactor recycle lag coefficient, `dt / (tau . 60)`. It is the step and a design constant, nothing else: derived inside the reactor rather than passed. |
| `blow_322501_kgh` | 3 | 23,37 | RESULT | a valve blow-through rate from the consequence layer. Becomes a field of that valve's result, alongside the flow it accompanies. |
| `blow_323501_kgh` | 7 | 23,24,37 | RESULT | a valve blow-through rate from the consequence layer. Becomes a field of that valve's result, alongside the flow it accompanies. |
| `blow_323505_kgh` | 9 | 12,24,37 | RESULT | a valve blow-through rate from the consequence layer. Becomes a field of that valve's result, alongside the flow it accompanies. |
| `bot_c005` | 14 | 15,37 | RESULT | the 323C005 sump bottoms draw. Becomes a field of the 323C005 result. |
| `cp_314_in` | 8 | 9,10 | PACKET | a field of the `StreamPacket` that `core.transport` already carries down this line. The four properties cross the boundary together by construction, so none of them becomes an argument of its own. 323C003 -> 323F004, arrival side. |
| `cp_319_in` | 10 | 11,12 | PACKET | a field of the `StreamPacket` that `core.transport` already carries down this line. The four properties cross the boundary together by construction, so none of them becomes an argument of its own. 323F004 -> 323F010, arrival side. |
| `cp_322c001` | 13 | 22 | PROPERTY | a specific heat evaluated ONCE per tick from the tear state, before any unit advances it. Becomes a field on a tick-start property snapshot passed to the units, NOT a recomputation inside each unit: the units that read it run after the state has moved, so re-evaluating there would give a different number. |
| `cp_328c002` | 13 | 17 | PROPERTY | a specific heat evaluated ONCE per tick from the tear state, before any unit advances it. Becomes a field on a tick-start property snapshot passed to the units, NOT a recomputation inside each unit: the units that read it run after the state has moved, so re-evaluating there would give a different number. |
| `cp_328c003` | 13 | 18 | PROPERTY | a specific heat evaluated ONCE per tick from the tear state, before any unit advances it. Becomes a field on a tick-start property snapshot passed to the units, NOT a recomputation inside each unit: the units that read it run after the state has moved, so re-evaluating there would give a different number. |
| `cp_328c004` | 13 | 19 | PROPERTY | a specific heat evaluated ONCE per tick from the tear state, before any unit advances it. Becomes a field on a tick-start property snapshot passed to the units, NOT a recomputation inside each unit: the units that read it run after the state has moved, so re-evaluating there would give a different number. |
| `cp_328d001` | 13 | 20 | PROPERTY | a specific heat evaluated ONCE per tick from the tear state, before any unit advances it. Becomes a field on a tick-start property snapshot passed to the units, NOT a recomputation inside each unit: the units that read it run after the state has moved, so re-evaluating there would give a different number. |
| `cp_328d3i` | 13 | 15 | PROPERTY | a specific heat evaluated ONCE per tick from the tear state, before any unit advances it. Becomes a field on a tick-start property snapshot passed to the units, NOT a recomputation inside each unit: the units that read it run after the state has moved, so re-evaluating there would give a different number. |
| `cp_328d3ii` | 13 | 15 | PROPERTY | a specific heat evaluated ONCE per tick from the tear state, before any unit advances it. Becomes a field on a tick-start property snapshot passed to the units, NOT a recomputation inside each unit: the units that read it run after the state has moved, so re-evaluating there would give a different number. |
| `cp_331` | 6 | 11,12 | PROPERTY | a specific heat evaluated ONCE per tick from the tear state, before any unit advances it. Becomes a field on a tick-start property snapshot passed to the units, NOT a recomputation inside each unit: the units that read it run after the state has moved, so re-evaluating there would give a different number. |
| `cp_c003` | 6 | 7,8 | PROPERTY | a specific heat evaluated ONCE per tick from the tear state, before any unit advances it. Becomes a field on a tick-start property snapshot passed to the units, NOT a recomputation inside each unit: the units that read it run after the state has moved, so re-evaluating there would give a different number. |
| `cp_f004` | 6 | 9,10 | PROPERTY | a specific heat evaluated ONCE per tick from the tear state, before any unit advances it. Becomes a field on a tick-start property snapshot passed to the units, NOT a recomputation inside each unit: the units that read it run after the state has moved, so re-evaluating there would give a different number. |
| `cp_f010` | 6 | 11,12 | PROPERTY | a specific heat evaluated ONCE per tick from the tear state, before any unit advances it. Becomes a field on a tick-start property snapshot passed to the units, NOT a recomputation inside each unit: the units that read it run after the state has moved, so re-evaluating there would give a different number. |
| `cp_feed323` | 6 | 7 | PROPERTY | a specific heat evaluated ONCE per tick from the tear state, before any unit advances it. Becomes a field on a tick-start property snapshot passed to the units, NOT a recomputation inside each unit: the units that read it run after the state has moved, so re-evaluating there would give a different number. |
| `disch_open` | 0 | 2,34 | CONTROL | an isolation-valve position read at the top of the tick. Becomes part of the plant command state the control layer publishes, not a value passed between units. |
| `drain_kgh` | 3 | 6,37 | RESULT | the 322E001 bottoms drain, after the LV-322501 stroke, the freeze gate and the seal factor. Becomes a field of the stripper result. |
| `ej` | 2 | 3,4,5,6,37 | RESULT | the unit's whole result object. V1 already returns a dict; it becomes a typed result dataclass and every consumer reads a named field of it. |
| `fa202_m` | 27 | 31,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. False-air ingress at PV-324202 / PV-324203. |
| `fa203_m` | 29 | 31,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. False-air ingress at PV-324202 / PV-324203. |
| `feed_factor` | 1 | 2 | CONTROL | an isolation-valve position read at the top of the tick. Becomes part of the plant command state the control layer publishes, not a value passed between units. |
| `hpcc` | 3 | 4,5,6,37 | RESULT | the unit's whole result object. V1 already returns a dict; it becomes a typed result dataclass and every consumer reads a named field of it. |
| `hv604` | 5 | 6,22,37 | RESULT | the unit's whole result object. V1 already returns a dict; it becomes a typed result dataclass and every consumer reads a named field of it. |
| `in_c002` | 17 | 20 | ARG | the 328D001 total inlet, a SUM of one live flow and three one-tick tears. Becomes the inlet mixing expression inside 328D001, built from its named inputs rather than from a pre-summed local. |
| `lic501_op` | 20,29 | 29 | ARTEFACT | two different controllers sharing a name: LIC-328501 in section 20, LIC-324501 in section 29. Each belongs to its own unit. |
| `lic503_op` | 17,24 | 24 | ARTEFACT | two different controllers sharing a name: LIC-328503 in section 17, LIC-323503 in section 24. |
| `lvl_c003` | 7,18 | 18 | ARTEFACT | two unrelated locals sharing a name: 323C003 in section 7, 328C003 in section 18. Each stays inside its own unit module. |
| `m702_prev` | 13 | 14,37 | TEAR | read from `s.tlag` with a design-value default, so it is LAST tick's flow: a one-tick recycle the static map cannot see through a `.get()`. Belongs with section 2, not here. Becomes an explicit engine-state field with a documented one-tick delay. |
| `m708_prev` | 13 | 14,37 | TEAR | read from `s.tlag` with a design-value default, so it is LAST tick's flow: a one-tick recycle the static map cannot see through a `.get()`. Belongs with section 2, not here. Becomes an explicit engine-state field with a documented one-tick delay. |
| `m718A_prev` | 13 | 20,21,37 | TEAR | read from `s.tlag` with a design-value default, so it is LAST tick's flow: a one-tick recycle the static map cannot see through a `.get()`. Belongs with section 2, not here. Becomes an explicit engine-state field with a documented one-tick delay. |
| `m718B_prev` | 13 | 23 | TEAR | read from `s.tlag` with a design-value default, so it is LAST tick's flow: a one-tick recycle the static map cannot see through a `.get()`. Belongs with section 2, not here. Becomes an explicit engine-state field with a documented one-tick delay. |
| `m739_prev` | 13 | 15,16,21 | TEAR | read from `s.tlag` with a design-value default, so it is LAST tick's flow: a one-tick recycle the static map cannot see through a `.get()`. Belongs with section 2, not here. Becomes an explicit engine-state field with a documented one-tick delay. |
| `m744_prev` | 13 | 19 | TEAR | read from `s.tlag` with a design-value default, so it is LAST tick's flow: a one-tick recycle the static map cannot see through a `.get()`. Belongs with section 2, not here. Becomes an explicit engine-state field with a documented one-tick delay. |
| `m748_prev` | 13 | 17,37 | TEAR | read from `s.tlag` with a design-value default, so it is LAST tick's flow: a one-tick recycle the static map cannot see through a `.get()`. Belongs with section 2, not here. Becomes an explicit engine-state field with a documented one-tick delay. |
| `m750_prev` | 13 | 17,37 | TEAR | read from `s.tlag` with a design-value default, so it is LAST tick's flow: a one-tick recycle the static map cannot see through a `.get()`. Belongs with section 2, not here. Becomes an explicit engine-state field with a documented one-tick delay. |
| `m756_prev` | 13 | 14,37 | TEAR | read from `s.tlag` with a design-value default, so it is LAST tick's flow: a one-tick recycle the static map cannot see through a `.get()`. Belongs with section 2, not here. Becomes an explicit engine-state field with a documented one-tick delay. |
| `m775_prev` | 13 | 17,20,37 | TEAR | read from `s.tlag` with a design-value default, so it is LAST tick's flow: a one-tick recycle the static map cannot see through a `.get()`. Belongs with section 2, not here. Becomes an explicit engine-state field with a documented one-tick delay. |
| `m931_prev` | 13 | 19,37 | TEAR | read from `s.tlag` with a design-value default, so it is LAST tick's flow: a one-tick recycle the static map cannot see through a `.get()`. Belongs with section 2, not here. Becomes an explicit engine-state field with a documented one-tick delay. |
| `m_305` | 7 | 8,23,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Stream 305, 323C003 top vapour -> 323E003 LPCC. |
| `m_314` | 7 | 8,37 | PACKET | a field of the `StreamPacket` that `core.transport` already carries down this line. The four properties cross the boundary together by construction, so none of them becomes an argument of its own. 323C003 -> 323F004, departure side. |
| `m_314_in` | 8 | 9,10 | PACKET | a field of the `StreamPacket` that `core.transport` already carries down this line. The four properties cross the boundary together by construction, so none of them becomes an argument of its own. 323C003 -> 323F004, arrival side. |
| `m_317` | 11 | 12,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Stream 317, 323F010 -> 323D002. |
| `m_317_in` | 12 | 13 | PACKET | a field of the `StreamPacket` that `core.transport` already carries down this line. The four properties cross the boundary together by construction, so none of them becomes an argument of its own. 323F010 -> 323D002, arrival side. |
| `m_319` | 9 | 10,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Stream 319, 323F004 -> 323F010. |
| `m_319_in` | 10 | 11,12 | PACKET | a field of the `StreamPacket` that `core.transport` already carries down this line. The four properties cross the boundary together by construction, so none of them becomes an argument of its own. 323F004 -> 323F010, arrival side. |
| `m_321` | 23 | 24,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Stream 321, 323D001 -> 323D011. |
| `m_324` | 13 | 27,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Stream 324, 323D002 -> 324E001. |
| `m_331` | 11 | 12,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Stream 331, a fixed design return into 323F010. |
| `m_402` | 15 | 24,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Stream 402, FIC-323402 into 323E011. |
| `m_701` | 9 | 10,24,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Stream 701, 323F004 flash vapour -> LPCC. |
| `m_718A` | 24 | 25,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Streams 718A / 718B out of 323D011. |
| `m_718B` | 24 | 25,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Streams 718A / 718B out of 323D011. |
| `m_735` | 15 | 16,17,21,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Stream 735, 328D003 Comp II -> 328E007 -> 738. |
| `m_737` | 17 | 20,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Streams 737 / 738 / 743 out of 328C002. |
| `m_739` | 19 | 25,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Stream 739, 328C004 bottoms. |
| `m_743` | 17 | 18,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Streams 737 / 738 / 743 out of 328C002. |
| `m_744` | 15 | 25,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Stream 744, 328D003 Comp I -> 322P002. |
| `m_746` | 18 | 19 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Stream 746, 328C003 feed; V1 aliases it to `m_743` via 328E021. |
| `m_747` | 18 | 19,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Streams 747 / 748 out of 328C003. |
| `m_748` | 18 | 25,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Streams 747 / 748 out of 328C003. |
| `m_750` | 19 | 25,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Stream 750, 328C004 overhead. |
| `m_755` | 15 | 22,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Stream 755, the cooled absorber feed; V1 aliases it to `m_744`. |
| `m_756` | 22 | 25,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Stream 756, 322C001 liquor -> 323C005. |
| `m_775` | 20 | 25,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Streams 775 / 776 / 786 out of 328D001. |
| `m_776` | 20 | 21,23,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Streams 775 / 776 / 786 out of 328D001. |
| `m_786_d001` | 20 | 21,24,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Streams 775 / 776 / 786 out of 328D001. |
| `m_793` | 15 | 20,21,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Stream 793, FIC-328405 into 328D001. |
| `m_931` | 19 | 21,25,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Stream 931, LP steam to 328C004. |
| `m_evap` | 11 | 12,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. 323F010 evaporation rate into the vacuum train. |
| `m_feed_323` | 6 | 7,8,37 | PACKET | a field of the `StreamPacket` that `core.transport` already carries down this line. The four properties cross the boundary together by construction, so none of them becomes an argument of its own. 322E001 bottoms -> 323C003. |
| `m_flash_gas` | 7 | 8,23 | RESULT | the 323C003 vapour split between the flash gas and the heater pool boil-up. Becomes two fields of the 323C003 result, because the PT-323201 pressure target needs them separately and neither can be inferred from the other. |
| `m_fwd` | 29 | 30,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. LV-324501 forward and recycle splits. |
| `m_p1` | 27 | 29,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. The 324E001 melt to evaporator stage 2. |
| `m_pool_vap` | 7 | 8,23 | RESULT | the 323C003 vapour split between the flash gas and the heater pool boil-up. Becomes two fields of the 323C003 result, because the PT-323201 pressure target needs them separately and neither can be inferred from the other. |
| `m_recyc` | 29 | 32,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. LV-324501 forward and recycle splits. |
| `m_v011` | 24 | 25,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. The 323E011 vapour draw, PIC-323203 -> 324 vacuum train. |
| `mot9605_m` | 27 | 31,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. HV-329605 ejector motive steam. |
| `n_blow_323505` | 9 | 12 | RESULT | a valve blow-through rate from the consequence layer. Becomes a field of that valve's result, alongside the flow it accompanies. |
| `new_T` | 3 | 4 | RESULT | the reactor's four-node temperature profile. Becomes a field of the reactor result, so the steam-balance pass reads the profile rather than a leftover local. |
| `p` | 2 | 12,27,29 | ARTEFACT | the parameter of a nested pressure-residual closure (`_dpdt_f010(p)` and its 324 twins), which collides with the `for p, ctrl in ...` pump loop variable in section 2. Three unrelated names. |
| `phi_fwd` | 2 | 4,36,37 | RESULT | **re-resolved while porting unit 321.** It is not an actuator position at all: `phi_fwd = phi_m^2` where `phi_m = motive_nh3_kgh / EJ_MOTIVE_NH3_DES`, the affinity-law head fraction of the delivered motive flow. Becomes `FeedResult.phi_forward`, a named field of the feed station's result. |
| `pic` | 1 | 2,37 | CONTROL | a valve stroke from the PIC-322203 controller block. Becomes that block's output. |
| `pic203_op` | 24,27 | 27 | ARTEFACT | two different controllers sharing a name: PIC-323203 in section 24, PIC-329203 in section 27. |
| `pull` | 12,27,29 | 27,29 | ARTEFACT | the parameter of a nested pressure-residual closure (`_dpdt_f010(p)` and its 324 twins), which collides with the `for p, ctrl in ...` pump loop variable in section 2. Three unrelated names. |
| `pull_f010` | 12 | 27,31 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Stream 790, what HV-323605 actually passed at the solved pressure. |
| `pv_open` | 1 | 2,37 | CONTROL | a valve stroke from the PIC-322203 controller block. Becomes that block's output. |
| `react` | 3 | 4,5,6,37 | RESULT | the unit's whole result object. V1 already returns a dict; it becomes a typed result dataclass and every consumer reads a named field of it. |
| `react_carry_kmolh` | 4 | 5 | RESULT | carry-over out of the reactor overflow. Becomes a field of the reactor result. |
| `route501` | 29 | 30,32,37 | RESULT | the unit's whole result object. V1 already returns a dict; it becomes a typed result dataclass and every consumer reads a named field of it. |
| `scrub` | 5 | 6,37 | RESULT | the unit's whole result object. V1 already returns a dict; it becomes a typed result dataclass and every consumer reads a named field of it. |
| `strip` | 3 | 4,5,6,37 | RESULT | the unit's whole result object. V1 already returns a dict; it becomes a typed result dataclass and every consumer reads a named field of it. |
| `sub_703` | 12 | 27,31 | RESULT | a valve blow-through rate from the consequence layer. Becomes a field of that valve's result, alongside the flow it accompanies. |
| `suct_open` | 0 | 2 | CONTROL | an isolation-valve position read at the top of the tick. Becomes part of the plant command state the control layer publishes, not a value passed between units. |
| `v1_m` | 27 | 31,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Stage-1 and stage-2 evaporator vapour loads. |
| `v2_m` | 29 | 31,37 | ARG | a stream flow between two units. Becomes the connection: the producing unit returns it and the consuming unit takes it as an argument. Stage-1 and stage-2 evaporator vapour loads. |
| `vent` | 27,29 | 29 | ARTEFACT | a local inside each vacuum condenser's own block: 324E002 in section 27, 324E005 in section 29. |
| `w1_live` | 27 | 29,37 | RESULT | the live urea mass fraction leaving evaporator stage 1. Becomes a field of that stage's result. |
| `w_314_in` | 8 | 10 | PACKET | a field of the `StreamPacket` that `core.transport` already carries down this line. The four properties cross the boundary together by construction, so none of them becomes an argument of its own. 323C003 -> 323F004, arrival side. |
| `w_317_in` | 12 | 13 | PACKET | a field of the `StreamPacket` that `core.transport` already carries down this line. The four properties cross the boundary together by construction, so none of them becomes an argument of its own. 323F010 -> 323D002, arrival side. |
| `w_319_in` | 10 | 12 | PACKET | a field of the `StreamPacket` that `core.transport` already carries down this line. The four properties cross the boundary together by construction, so none of them becomes an argument of its own. 323F004 -> 323F010, arrival side. |
| `w_dep_314` | 7 | 8 | PACKET | a field of the `StreamPacket` that `core.transport` already carries down this line. The four properties cross the boundary together by construction, so none of them becomes an argument of its own. 323C003 -> 323F004, departure side. |
| `w_feed_323` | 6 | 8 | PACKET | a field of the `StreamPacket` that `core.transport` already carries down this line. The four properties cross the boundary together by construction, so none of them becomes an argument of its own. 322E001 bottoms -> 323C003. |
| `y_blow_323505` | 9 | 12 | RESULT | a valve blow-through rate from the consequence layer. Becomes a field of that valve's result, alongside the flow it accompanies. |

## What this changes for Phase 4

1. **Four transported lines carry sixteen of these rows.** The `_in` / `_dep_` families are not sixteen arguments; they are four `StreamPacket` objects that `core.transport` already builds and delays. Porting the 323 train means wiring four packets, not sixteen signals.

2. **Thirteen property evaluations are one tick-start snapshot.** They are evaluated from the tear state before any unit advances it, and the units that read them run afterwards. Re-evaluating inside each unit would use the ALREADY-ADVANCED state and give a different number, so the snapshot has to be a real object passed down, not an optimisation that can be inlined away.

3. **Twelve rows move to the tear list** — the eleven `*_prev` flows and the `Tc003` alias — and with them the obligation to give each a named state field instead of a `s.tlag.get()` with a magic default.

4. **Nine rows disappear.** They were never couplings.

5. **The remainder — flows, duties, temperatures and result objects — are ordinary connections.** They become arguments and result fields, which is what the module boundaries were going to be anyway.

## Staying honest

`tests/docs/test_coupling_resolution.py` parses this file and the generated map and asserts they describe exactly the same set of names. If V1 changes, or if a row is dropped while editing, the test fails rather than the omission going unnoticed.

