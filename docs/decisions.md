# Design decisions on record

Moved verbatim from `project.md` on 2026-11-11 (session 96, `CLAUDE.md` section 3a). `project.md` section 5. **`project.md` decision N, wherever
the code, the tests or a document cites it, is entry N below.** A new decision takes the next number
(`project.md`, Next free numbers) and is appended at the end. Never read it whole:
`grep -n "^181\. " docs/decisions.md` finds decision 181, and `grep -n "B-118" docs/decisions.md` every
decision on an item.

---

## 5. Design decisions on record

1. **PyQt6, not PyQt5.** Qt6 is current, has proper high-DPI scaling for the 1366×720 stage,
   and `QGraphicsView` transforms give the anisotropic icon un-squash for free.
2. **Raw TCP, not FastAPI/WebSocket and not ZeroMQ.** Multi-station needs a transport, so the
   question is which. A WebSocket stack brings `fastapi` + `uvicorn` and an HTTP server to
   carry frames between two Python processes on a closed network; ZeroMQ brings a native
   dependency. Length-prefixed JSON over TCP needs neither, and `QTcpSocket` is
   signal-driven — so the console has no worker thread, no lock and no queue between the
   wire and the widgets. Framing is twelve lines and is unit-tested against split and
   oversized frames.
3. **JSON, not a binary codec.** A training simulator's snapshot is read by humans during
   commissioning. At 10 Hz across a handful of stations the cost is irrelevant, and V1 sent
   the same payload over a WebSocket.
4. **Snapshot key paths are preserved.** The UI binds by dot-path (`controllers.SIC_321950.pv`).
   Keeping V1's exact packet shape means `overlays.js` bindings convert mechanically and the
   trend tag-to-path resolution is unchanged.
5. **Scalar property correlations stay scalar.** Vectorising them would change floating-point
   results and break the equivalence tests. Only the flowsheet solver uses NumPy.
6. **Design basis is 1750 MTPD / 100 % load** per V1 directives. The 1925 MTPD table is an
   alternate case, not the anchor.
7. **A divergence from V1 is made only on the process engineer's decision** (2026-09-26, first
   applied to PIC-322203). The handoff item is closed and deleted. The As-Built register row
   names the divergence, and the equivalence test asserts both sides of it: what V1 does, and
   what the rewrite does instead.
8. **Recycle tears keep V1's one-tick delay** (2026-09-26, handoff A-10). There is no in-tick
   convergence solver, because the tears feed holdups and are not algebraic loops. A solver
   would change every transient that crosses a tear, and Phase 7 compares transients against
   V1.
9. **The physics step is fixed at 0.1 s** (2026-09-27, handoff A-14; `Claude.md` §1 rule 10).
   V1 steps on the wall clock, so its tear delays — one step each, by decision 8 — move with
   machine load. The engine pays wall-clock x pacing in whole 0.1 s steps; SLOW and FAST run the
   same steps, and an exercise replays bit for bit. Phase 7 drives V1 at the same fixed step.
10. **The DCS tuning table's gains are read per cent of span** (2026-09-27, handoff B-32). A loop
    running on its PV in engineering units carries the table's gain times 100 over its
    transmitter's calibrated span: PIC-323203 (0-1 bar g, 60 %/bar), PIC-323202 (the table's
    row on 0-5 bar g, 20 %/bar, 100 s) and TIC-323013 (0-100 C, V1's own 1.0 %/K). A loop whose
    output V1 carries in the PV's own units on the same span, SIC-323901 (0-145 rpm, rpm per
    rpm), keeps the table's number. Level loops were already right. Extended to FIC-328402 on
    2026-09-27 (handoff B-38): 0.75 on FT-328402's 0-70 m3/h, 1.071 %/(m3/h), where V1 ran 0.06
    per kg/h. Extended to every ported flow loop on 2026-09-30 (handoff B-41, the "Typo Rule"):
    V1 applied their table numbers per kg/h, times the density; FIC-323401 (0-4 m3/h),
    FIC-323402 (0-3.3), FIC-328405 (0-2.3), FIC-328406 (0-60), FIC-323418 (0-10) and FIC-324401
    (0-110 m3/h, 126.6 t/h) now carry them per cent of span, the spans from Uhde's loop summaries.
    The temperature and pressure loops still on V1's per-unit numbers (TIC-323007, TIC-323012,
    PIC-329202, PIC-329208) keep them until their spans are sourced and the decision is extended.
    Extended on 2026-10-07 to FIC-329409 and TIC-329005, their spans read from Uhde's loop summaries
    (FT-329409 0-500 m3/h, TT-329005 0-200 C): the table's 0.60 / 250 s and 1.50 / 300 s.
11. **A pump never drains its vessel's floor** (2026-09-27, handoffs B-26, B-29, B-33). Where
    V1 floors a holdup at 1 kg, the draw is capped at the liquid above that heel plus what
    arrives on the tick, the loss of suction is flagged and the transmitter reads the delivered
    flow — and a transmitter behind a stopped pump reads nothing (FT-328402 with 322P002
    stopped, B-38). Decided per vessel: 323D002, 323F010's leg, 323D011, 323D001 (B-35), and 328D003,
    where the process engineer asked for the rule to be applied wherever the survey finds the
    flaw. Where bays communicate, the heel is one level — the level at which the smallest bay
    holds the floor — so the levelling cannot carry a bay below it. A full vessel's excess is
    published as an overflow stream, not clamped away or held above capacity (323D002, 328D003).
12. **323E003 condenses its whole capacity** (2026-09-27, handoff B-34). V1 capped the LPCC's
    dew-point capacity at the gas that arrives, which froze the node under surplus cooling; the
    port lets the condenser draw on the envelope's gas until the capacity meets the load.
    323E011's constant capacity is B-30's, and stays V1's.
13. **A control structure the P&ID does not show is not built** (2026-09-27, handoff B-36).
    Where vendor documents disagree on a control scheme and the P&ID does not carry the change,
    V1's structure stands: PIC-323202 drives one vent, and TIC-323013 its own set point.
14. **An interchanger never makes heat** (2026-09-27, B-40, raised and decided in session 24).
    Where V1 fixes a feed/effluent exchanger's cold outlet by a temperature effectiveness and
    clamps the hot outlet at the pinch, the feed takes only what the hot side gave, less the
    shell loss, bounded by V1's share; a loss the hot side cannot pay is not charged to the feed.
    Decided on 328E007; extended on 2026-09-30 to every fixed-effectiveness exchanger V1 writes
    this way — 328E021 takes the same cap when 328C003 is ported.
15. **A column's negative duty condenses vapour** (2026-09-30, B-42, raised and decided in session
    25). Where V1 sets a column's boil-up as an anchored ratio of its net duty and clamps it at
    zero, the port drops the clamp: a negative duty condenses vapour, and the pressure and its
    bubble point fall until the duty balances. On 328C002, with the stripping vapour lost, V1
    holds 128.5 C and makes 622.5 kW; the port cools to the feeds' 111.3 C.
16. **A valve's flash choke reads the liquor at the valve** (2026-09-30, B-43, raised and decided
    in session 25). Where V1 reads a liquor's bubble pressure somewhere other than the valve's
    inlet, the port reads it at the inlet the loop summary gives: LV-328503 upstream of 328E021,
    at the bottoms' 139 C, not 328E021's 190 C outlet.
17. **Every open item has a phase** (2026-09-30). The process engineer scheduled every open
    handoff item into Phase 4 (with the unit ports), 5 (engine), 6 (HMI) or 7 (validation and
    the calibration deferrals); the table heads `handoff.md`. Items raised later are scheduled
    when raised.
18. **The flash runs 60 sweeps** (2026-09-30, handoff A-9). V1's 40 stop one short on a dilute hot
    liquor and flag a good solve unconverged. The change is not flag-only, as the handoff had
    said: the 323 stages' rigorous vapour departure refuses an unconverged flash, so states needing
    41 to 60 sweeps take the rigorous branch where V1 fell back. Decided with that measured
    (323F010's superheat 16.45 -> 19.90 K in one case; no design point moves).
19. **A liquid-full line delivers its flow at once** (2026-09-30, handoff B-21). The product lines
    delay only the liquor's temperature, composition and cp; the flow arrives on the tick it
    leaves. V1's lines delayed the flow too, and a stopped line kept delivering for half an hour.
20. **A steam chest is anchored on its datasheet** (2026-09-30, handoff B-23 and Open data gaps).
    323E002 on 3.9 bar a and 323E010 on 2.5 bar a — the heaters' DDS and PFD 918 / 926 — where V1
    anchored on 3.96 and 1.76 bar a, leftovers of a retired 4.4 bar a header. The printed 145 and
    139 C are the header steam's superheat after its isenthalpic letdown, which the chest law
    ignores. The stroke and the conductance are re-derived by V1's own expressions.
21. **A cascade reads the table on span, and V1's basis scales go with the wrong basis**
    (2026-09-30, decision 10 extended). TIC-323007, PIC-329202 and PIC-329208 run the DCS table's
    gains per cent of their transmitters' spans, the master's output scaled onto its slave's
    range as the functional diagrams give it. V1's chest-gain scale, which only held a loop gain
    V1 had tuned on an engineering-unit basis, is dropped and deleted.
22. **A loop with no table row runs its sibling's** (2026-09-30, handoff B-45). TIC-323012 has
    none, and V1's own retune limit-cycles once its slave is on span; it runs TIC-323007's row —
    the same cascade on the same unit — on its own spans, a stated tuning for Phase 7 to check.
23. **A vendor valve runs its own trim** (2026-09-30, handoff B-44). Every ported valve in
    Flowserve's and CCI's sheets runs its trim — Valtek's modified equal percentage fitted to its
    own 41 sizing cases (44 with PV-328203's), linear, or CCI's equal percentage — from the stroke at which its rated
    capacity passes the design flow on its normal case, on the sheet's FL; a valve shut at design
    is anchored on its full-stroke capacity. V1 ran every valve linear from 50 %. A transmitter
    behind a valve that can now ask more than its supply reads what is delivered (decision 11).
24. **The liquid pays what boils** (2026-09-30, raised on 328C003 and decided the same session).
    Where V1 takes a column's overhead VALVE flow out of the liquid — and charges its latent heat
    on it — while the pressure integral fills the head space with what the column GENERATES, the
    port charges the liquid the generation: holdup, species, the heel cap and the latent heat. The
    head space holds the difference, which the pressure integral already carried. Built on
    328C003 and retro-fitted to 328C002, where a negative boil-up (decision 15) returns its
    condensate to the liquid. V1 makes exactly its integral of generation less overhead: 505 kg
    and 3.1 K with PV-328203 at 20 % for an hour. The missing relief is B-47.
25. **FFIC-329401 ratios the LP steam to the desorbers' feed, 735** (2026-09-30, handoff B-39's
    ratio). The P&ID and the functional diagram take the ratio's feed from FIC-328402 on 735; V1
    reads 744. Built with 328C004: the ratio reads the tank's 735 this tick at PFD 735's density.
    FIC-328402 itself stays on 744 until Phase 7 (B-39).
26. **FFIC-329401 is a ratio station** (2026-09-30, handoff B-49). As UD-MR-329-FF-0002 page 2
    draws it: FIC-329401's set point is the ratio set point times the feed times 1000; the ratio
    tracks while the slave is out of cascade. V1's PI on the measured ratio is gone.
27. **LIC-328505 is FIC-328406's master; 741 is drawn from 328C004** (2026-09-30, handoff B-50).
    As UD-MR-328-FF-0002 page 2 and P&ID 104 draw it: in cascade FIC-328406's set point is
    LIC-328505's output / 100 x 60 m3/h and LV-328505 is switched shut; 741 leaves the column's
    bottoms ahead of LV-328505 and FIC-328406 steps with 328C004. TIC-328012's cascade (B-48)
    was measured to run away on V1's PV and kept as V1, deferred to Phase 7.
28. **328E004 cannot cool the drum below its cooling water** (2026-09-30, raised on 328D001
    and decided the same session). V1's duty is Q_des . op / 50 on TV-328002 alone; the port caps
    it at what brings the drum to the 30 C supply on the tick. Inert above 30 C.
29. **328D001's vent discharges against 323E011's live pressure** (2026-09-30), the tick before's,
    where V1 holds 323E011's design 1.13 bar a.
30. **A full 328C002's overflow enters 328D001** (2026-09-30, handoff A-15), at the column's
    bottoms temperature: the liquid a flooded column carries out through its overhead line to
    328E004. The drum's own overflow is to be wired to 323E011 through the vent line in Phase 5.
31. **Every letdown flashes where its downstream condition warrants it** (2026-09-30, handoff
    B-46, the "Typo Rule"). V1's IEC 60534 liquid law is handed the liquor's live vapour pressure
    and its design value, so it chokes on FL^2 (P1 - FF . Pv) where the valve's differential
    exceeds it; the liquid at a valve is at most saturated at its inlet. Built on LV-322501,
    LV-323501, LV-323505 and LV-328505.
32. **A node relieves through its certified safety valves** (2026-09-30, handoff B-47). Pop
    action at the set pressure, reseat at the vendor's blowdown (10 % of set on gas, 20 % on
    liquid), API 520 critical flow on an orifice back-solved from the vendor's certified capacity,
    the vapour vented to atmosphere and published. Built on 328C003 and 328C002; the rest, A-16.
33. **A vessel's volume includes its heads, and a level transmitter reads between its taps**
    (2026-09-30, handoff B-53, the "Typo Rule"). Built on 328D001: 5500 l, LT-328501's 1510 mm
    span. Applied to 322C001 under rule 7 (session 30): 3.60 m3, LT-322502's 800 mm.
34. **A liquid-rated safety valve on a vapour node relieves gas at the series' full-lift
    coefficient** (2026-10-01, handoff A-16, option b). Its orifice's own area, alpha_w 0.917 —
    SV32351/52's certified gas coefficient — the law's k 1.30, the gas blowdown (10 %): an
    assumption, logged in Open data gaps for Phase 7. "Leaving a node unrelieved causes
    unphysical runaways." Built on SV32357 (323D011), SV32353 (328D001) and SV32253 (322C001).
35. **Every physical unit is ported before the scheduler** (2026-10-01). The schedule depends on
    the completed plant's data-flow dependencies, so Phase 4 is re-opened for 322C001, unit 324
    and the steam system; Phase 5's `schedule.py` and `scheduler.py` follow them.
36. **322E006 is a true exchanger** (2026-10-01, handoff B-54, option b, the "Typo Rule": V1
    replaced the exchanger with a 40 C boundary). Its datasheet UA, 30.776 kW/K, and the 30 C
    cooling-water supply; the water through the plates back-solved so the PFD's 744 -> 755 holds
    exactly (10 374 kg/h, Open data gaps); 755's temperature an argument of 322C001.
37. **XV-322915's flood goes into the vent gas, and trip 22.1 watches the vent** (2026-10-01,
    handoff B-55, option b). The 500 kW as the LP steam that carries it, 854 kg/h, into line
    150-GCB6-322254 where P&ID 102 injects it; TI-322015 the line's mix; V1's 57 / 55 C. The
    liquor's balance no longer sees the flood. Its consequence, the self-holding latch, is B-56.
38. **A letdown below its gas's dew point condenses** (2026-10-01, handoff B-19, "the rigorous
    solution"). The true isenthalpic flash down to the actual downstream pressure, onto an
    ammonium-carbamate liquor on the beds' own thermodynamics (`thermo/condensing_letdown.py`);
    V1's single-phase relation kept for a dry gas; the liquor into 322C001's sump; L3-7 fires while
    it condenses; HV-322604's outlet pressure an argument.
39. **I 22.1 is built as the DCS executes it** (2026-10-01, handoff B-56: "strictly follows the
    physical DCS interlock documentation ... apply the Typo Rule"). AC4's PC22.5.1: XVY-322915 =
    NOT(TT-322015 > H2) OR HS-322915 on a fail-open valve; no latch and no reset the logic does not
    draw; HS-322915 a maintained keyswitch. V1's 57 / 55 C stay as the limit until its database
    value is found (Open data gaps).
40. **XV-322915 has no operator open** (2026-10-01, handoff B-59: "the physical AC4 DCS logic is
    the absolute authority"). The console carries the plant's controls only: the overlay's valve a
    status display and its override button HS-322915, a maintained keyswitch (`keyswitch_set`);
    what a generated screen element does changes only through the converter's `DECIDED_EDITS`,
    each naming its decision.
41. **The flood is XV-322915's rated steam** (2026-10-01, handoff B-60, the Typo Rule). 1000 kg/h
    at 9.0 bar a and 175 C, the loop summary X 322915, where V1 back-calculated 500 kW; TI-322015
    112.35 C over the design vent.
42. **The melt's equilibrium is grounded on the PFD and on Fahmy-Nassar** (2026-10-01, handoff
    B-58, option a). UNIQUAC's one interaction energy refitted to PFD 401/402 under 705/709,
    -85.3 K, the anchored departure kept; the temperature slopes within 5 % of the Fahmy-Nassar
    plant correlation and within 10 % of Uhde's own urea-water chart for Helwan (UD-VT-G00-DC-0003
    Figure 15, digitised), asserted in the tests; the strength capped at what the feed's biuret and
    formaldehyde leave (the heel class). Other callers keep the published parameter.
43. **The ejectors pull on synthesized maps** (2026-10-01, handoff B-57, the Typo Rule). The 1-D
    model (V1's `ejector_huang.py`, Huang 1999) on each ejector's throats, anchored on its vendor
    duty point and Uhde's 1061 / 366 kg/h of motive, the break on the duty's discharge pressure,
    tabulated on suction and motive pressure and interpolated. Built and asserted both ways; not
    wired into the stages until B-61 is decided (the maps cannot hold the PFD's vacuums).
44. **The ejectors' capacity is anchored on the PFD's design loads** (2026-10-01, handoff B-61,
    option a: "the physical plant trend data (0.343 bar a) proves the system operates at the PFD
    design conditions"). Each map keeps the 1-D shape on its vendor's throats and the vendor's
    break; its capacity K scaled so the table gives PFD 706, 712 and 715 at 0.33, 0.131 and
    0.3 bar a on 4.1 bar a of motive — 324F004's K 0.919, the installed ejector's in-situ losses
    against the loss-free model; the vendor duties stand as margin. The stages pull on them.
45. **A separator's held melt boils** (2026-10-01, handoff B-62, option a, the Typo Rule: "if heat
    transfers from the chest and the fluid's vapor pressure exceeds the ambient vacuum, it must
    boil"). Past its own boiling point at the live vacuum the holdup boils, the excess sensible
    heat paid as latent heat, on the stage's anchored equilibrium at the holdup's own design
    composition; the feed's term is V1's. Evaluated at the trial pressure inside the vacuum's
    backward step.
46. **Stage 2 takes its feed at the strength its leg drains** (2026-10-02, handoff B-63, option a:
    "the liquid entering Stage 2 must have the exact thermodynamic state ... of the liquid leaving
    Stage 1's separator leg"). The urea basis of stage 2's boil-off is stage 1's holdup strength,
    anchored on the design (w_401,des + w_leg - w_leg,des), where V1 took the strength stage 1 made
    on the tick; a 323P003 trip no longer boils the leg as water.
47. **The PFD's motive steam is the train's** (2026-10-02, handoff B-64, option a: "the PFD material
    balance is the master document for the flowsheet integration"). PFD 924, 927 and 929 (390, 1220,
    180 kg/h) are the design motive the train condenses and the nozzle pressure is anchored on, for
    all three ejectors; the vendors' 650, 1061 and 366 stay the nozzles' rating inside the maps.
48. **323F010's held liquor boils** (2026-10-02, handoff B-24, B-62's class extended: "the laws of
    thermodynamics do not change between vessels"). Past the bubble point of its whole composition at
    the live PT-323204 the holdup boils, inside the vacuum's backward step; V1's two branches stay.
    The Calibration Deferral is removed; B-22's deeper-vacuum half is resolved with it.
49. **The cold ends the vacuums read are lagged on their tubes' water** (2026-10-02, handoff B-65,
    option a: "the tube-side water residence time lag physically damps the system while remaining
    cheap, apply the lag"). Each condenser cold end a vacuum balance reads — 324E002's and 324E005's
    for the stages, 324E006's for its shell — is lagged on tau = V_tubes / Q_cw (11.54, 7.67, 3.12 s
    from the datasheets' tubes and the PFD's water), where V1 hands the last solve's over a one-tick
    tear; a 323P003 trip no longer pulses.
50. **324E006's shell is a live vacuum node** (2026-10-02, handoff B-66, the Typo Rule: "we want the
    condenser to spike to 1 bar a when cooling is lost; we want 324F004 to break; and we want Stage 2
    vacuum to collapse"). On its name plate's 0.542 m3, 324F004 discharging against it, 324F005 pulling
    it into 324E007, bounded by 324E007's 1.0 bar a, where V1 holds the PFD's 0.3 bar a.
51. **The condensers' vent on additive departures** (2026-10-02, handoff B-67, option a: "a scaling
    ratio that blows up 68x when the divisor approaches zero is a numerical hazard, not physical
    behavior"). Each vacuum condenser's NH3 and CO2 vent pressures are the PFD's partial pressures plus
    the condensate's back-pressure departure from design, floored at zero, where V1 multiplies by the
    departure's ratio; every design unchanged. Its mirror on 324E007's CO2 is B-71.
52. **Every simulated steam user live on its header** (2026-10-02, handoff B-68: "simulated units must
    physically couple to the header"). The unsimulated users are constant at their PFD rows; each
    unit's draw is its live ratio on its PFD row where its own model's design differs (decision 47's
    class). V1 lumps every LP user but the HPCC into one constant set at boot.
53. **The LP header at 4.0 bar g** (2026-10-02, handoff B-69: "it must match what the operators see on
    their screens today"). V1's 5.01325 bar a stands; 913's flash and the HPCC's design raising are
    taken on it, not the PFD's 4.4 bar a.
54. **The drums pay their own waters** (2026-10-02, handoff B-70: "draw water from the drum, include
    the blowdown, and let the live header pressure respond physically"). Each superheated inlet boils
    its drum's water, which the level loses; a saturated condensate let down flashes into its
    receiver; 959 blows 322D001 down; no floor holds the LP header up.
55. **The vent's ratio where its design back-pressure is above** (2026-10-02, handoff B-71: "use V1's
    proportional ratio where the design back-pressure exceeds partial pressure ... and the additive
    formulation where it sits below"). Decided per species at design; 324E005 is V1's, 324E007's CO2
    and 324E006's CO2 V1's ratio, the rest B-67's addition.
56. **The steam users on their valves against their headers** (2026-10-02, handoff B-73, the Typo Rule:
    "static mass sinks break physical header dynamics"). HV-329605 / HV-329606 on their vendor gas
    sizing with the nozzles' pressure solved on the flow; FV-329401 on V1's butterfly law to 328C004's
    bottom; XV-322915's flood choked on 329D009's header; each anchored at its header's design, so the
    design draws are the PFD's rows to the bit.
57. **B-72 and B-74 are Calibration Deferrals** (2026-10-02): the instant valves' relays and the
    cut-off left as built, valve stroking times in Phase 7; 322E002's 62.6 MW kept, re-examined in
    Phase 7 against the DCS trends.
58. **The LP header downstream of 322D001A/B** (2026-10-02, the process engineer's topology note: "the
    4 barg LP steam network is physically located downstream of 322D001 A/B"; "322D001A/B water is
    boiled in the shell side of 322E002"). The drums feed the header through PFD 917; 960 joins the
    header downstream of them and its superheat boils no drum water; 322E002's shell boils the drums'
    water at their saturation. PFD 26 and P&ID 107/1.
59. **PT-329201's residual credit at the reactor's load ratio** (2026-10-03, handoff B-75 (b): "a
    hardcoded mass credit is a mathematical crutch that breaks turndown dynamics"). The credit
    f_loop . s . R_des scales with the CO2 load ratio the reactor scales the boot pin's recycle tear
    by, so the two mirrors cancel at any load.
60. **The recondensed backlog returns to 322E003's sump** (2026-10-03, handoff B-76 (b): "vapor
    cannot magically vanish"). What PT-329201's backlog recondenses runs into the sump on the next
    tick at the overflow's composition.
61. **The loop's lumped capacity is a Phase 7 Calibration Deferral, its vapour-inventory node
    pursued** (2026-10-03, handoff B-77 (a), "aggressively pursue (b)"). The vessels' process volumes
    read from the vendor's arrangement drawings in session 40.
62. **The loop's inventories conserve their mass** (2026-10-03, handoff B-78 (b) for items 1-3, (a)
    for item 4: "mass must route to a physical destination, not disappear"). The full sump's excess
    held back in 322E003; the forward-carbamate pulse drawn from the sump; the mushy zone on the
    sump's outflow, what it holds back staying in the sump. The production surge's recycle lag kept
    as a numerical buffer (Section C).
63. **A dry, CO2-rich purge keeps the flagged dry outlet; the solid carbamate is a Phase 7 data gap**
    (2026-10-03, handoff B-79 (a): "we cannot invent a dissociation constant for solid carbamate").
    The letdown returns the single-phase outlet, flagged not converged, and HV-322604's deposition
    alarm fires below 20 C, as built; the solid's deposition waits for its dissociation constant
    (Section C).
64. **The stripper's blow-through reaches 323C003, which relieves it** (2026-10-03, handoff A-16: "323C003
    relief is supplied by 322E001's gas blow-through (via LV-322501)"). The gas loads the column's
    overhead line by its own volume; SV32351 / SV32352 relieve the head space on decision 32's law, at
    most the gas it receives on the tick; the rest leaves overhead to 323E003.
65. **The overflows routed: 328D001's to 323E011, three to boundary sinks** (2026-10-03, handoff A-15).
    A full 328D001's overflow enters 323E011 as liquid; 328C003's, 328C004's and 322C001's overflows
    terminate as boundary sinks, published to telemetry (the packet's ``BOUNDARY_SINKS``, the
    historian) and read by no unit.
66. **V1's diagnostic blocks stay out of the console packet** (2026-10-03, handoff A-19 (a)): engine-
    internal telemetry no plant screen shows, which would cost every console bandwidth and give it
    values it does not own. B-79's decision (63) confirmed the same day.
67. **A full 323E011 / 323D011 envelope overflows to 323C005** (2026-10-03, handoff A-20 (b)): through
    PV-323203's vent line, the envelope's only outlet above its liquid, into the atmospheric absorber,
    which takes it into its sump as liquid a tick later. The node's ring at its vapour floor is not
    the routing's to settle; it joins B-51.
68. **323F004's vapour space is part of the 323E011 node** (2026-10-07, handoff B-51, the "Typo
    Rule"): the drum, the vapour line, the shell and the tank are one gas space, so the node integrates
    on the envelope's free volume plus the drum's 1.083 m3 above its level set point. V1's transients,
    dominated by the floor's numerical ring, are departed from knowingly.
69. **322E001's two flood rises share one ceiling** (2026-10-07, handoff B-9, asked and answered):
    ``max(dT_bot, dT_flood)``; a flooded stripper's bottoms tend to the 183 C liquor fed.
70. **TT-322002 is pinned on 165 C** (2026-09-29 schedule, built 2026-10-07, handoff B-16): the PFD's
    and the plant's value; what V1 anchors on the pin follows it; 322F001 keeps its 178.8 C enthalpy
    carrier.
71. **One atmosphere, 1.01325 bar, and one gravity, 9.80665 m/s2** (2026-09-29 schedule, built
    2026-10-07, handoffs B-6, B-7): every process relation and every display; a relief valve keeps the
    atmosphere its sheet states.
72. **Single-machine deployment until the port is complete** (2026-10-07, handoffs A-2, A-8): one
    engine and one local console, the superuser — every command, never assigned, granted to a loopback
    peer only; the station login and unit assignment deferred; the instructor's panel paused.
    Lifted 2026-10-16 (decisions 124, 125); one machine stays the default deployment. **Superseded
    by decision 149** (2026-10-22): one machine is the only deployment, its console no role at all.
73. **320K002 is a boundary feed outside the simulation's scope** (2026-10-08, revising the
    2026-10-07 decision that put it on Nuovo Pignone's curves): "a fully automated boundary feed ...
    without any operator intervention or faceplate exposure". Its hardwired governor and surge
    protection deliver the demanded CO2 into the discharge line at whatever pressure the line
    presents — no curve, speed, surge or stonewall; the battery-limit rate is the instructor's
    (`co2_set`, an Instructor Panel boundary condition since decision 149, not a server-enforced
    role gate); the line, its check valve and PV-322203 stay as built.
74. **The product-line routes on the isometrics** (2026-10-07, handoff A-11: "A physics-based
    simulation cannot rely on layout estimates when the actual plant geometry is available"): each
    route's as-built straight pipe and long-radius elbow arcs from its bill of material, each size at
    its own bore; valve bodies and fittings uncounted, the volume a lower bound.
75. **Known mass inflows are modelled: 322C001's trace steam** (2026-10-07: "Do not ignore known mass
    inflows"): FO-329458 and FO-322457's 60 kg/h into the vent line ahead of TI-322015, FO-329459's 30
    kg/h into SV32253's discharge, choked on the 9-bar header and taken out of PFD 910.
76. **FIC-329409 and TIC-329005 stay on the DCS table's rows** (2026-10-07, confirming session 44):
    "If the physical DCS responds slower than V1's arbitrary tuning, the simulator must reflect that
    slower response. A trainee must experience the true latency of the cooling water circuit."
77. **A loop with a row in the DCS's tuning table runs that row** (2026-10-08, the process engineer's
    request for the original constants; decision 76's class): LIC-322501 (0.20, 280 s, a 1.0 s
    derivative behind a 1.0 s filter), SIC-321950 (4.00, 35 s) and SIC-321951 (1.20, 50 s) on their
    rows, read again on the faceplate photographs, the SICs' gain on SI-321950's 0-180 rpm. The
    deadband stays B-28's; FFIC-321404A / B's structure is B-85.
78. **A vapour-space pressure takes the backward step where its explicit step would ring**
    (2026-10-09, handoff B-51, the process engineer's choice of "switch on stability" over a
    free-volume threshold or every node always): on a tick where dt . df/dP, the explicit step's own
    linearised gain, falls below -1, the node steps backward Euler on its own dP/dt, its outflow at the
    pressure it settles on; elsewhere V1's explicit step to the bit (`core.node.stable_pressure_step`,
    328C004 first). A numerical change: it acts on a head space closing towards the roof and where an
    overhead line's differential closes towards zero.
79. **SV32064 relieves the CO2 discharge line** (2026-10-09, handoff B-83 option (a)): decision 32's
    law on the line node — set 161.013 bar a, reseat 145.013, orifice H back-solved from Sempell's
    certified 74 444 kg/h at 177.013 bar a (UD-RL-G00-DZ-0001-001 page 72); PIC-322203's set point stays
    V1's 168.01 bar a, above the valve's set.
80. **A condenser's vent is never negative** (2026-10-09, handoff B-87 option (b), "the conservation
    rule": "a condenser cannot physically pass more condensate than it receives as vapour"): every
    species `vacuum_condenser.vent_moles` vents, and the inerts that size the vent, floored at zero,
    so the condensate is never more than what arrives. V1 sums the inerts as they come; an inlet
    scaled 405 times past its row booked N2 below zero and 324E005 vented -2.2e10 kg/h.
81. **FIC-328402 meters 735, as the plant does** (2026-10-09, handoff B-39 and B-87 option (c), "the
    topology rule"): the loop on 328P003's discharge to 328E007 and the desorbers, at 735's density,
    FV-328402's stroke on 735; 744 what 322P002 delivers, which has no control valve (P&ID 102,
    FI-322402 only); 328D003's level the operator's on FIC-328402's set point (LT-328507 and
    LT-328508 are open-loop indicators). V1 hangs the loop on 744 and draws 735 in proportion to
    compartment II's holdup. The console keeps V1's key and place; only the indicator's note changes
    (`tools/convert_overlays.DECIDED_EDITS`).
82. **A held melt whose boiling point lies below the melt model's window does not boil** (2026-10-09,
    handoff B-86 option (c), "the extrapolation rule"): where the window's 99 C edge holds a stronger
    melt than the holdup at the live vacuum, the stage runs on V1's closure alone, at the temperature
    its step gives. Session 46's bound boiled such a melt down to the edge every tick.
83. **Trip 22.2 trips the CO2 boundary** (2026-10-09, handoff B-88 option (c)): with XV-322902 shut
    the boundary's demand (``co2_set``) goes to zero, as the compressor's own trip would take it; a
    demand is refused while the trip is latched, and the instructor restores it once the trip is
    reset. A change to decision 73's boundary; 320K002's internals stay out of scope.
84. **Zero overlay overlap** (2026-10-09, handoff A-7): nav labels win over stream hotspots, which
    shrink from their far end by the fewest pixels that clear them; crossing stream hotspots stop one
    pixel short of the run they cross; TV-323013B moves down 3 px. Geometry leaves a recorded shape
    only through the converter's ``NUDGE`` table, V1's name for it, each row a decision.
85. **323E011's creep at design is accepted** (2026-10-09, handoff B-89): recorded as a known
    artefact of the integration, untraced; the item closed.
86. **322E002's gate is 1.0 permanently** (2026-10-09, handoff B-13): the film dynamics, the flash
    and the NTU quench live at every operating point; a loop that self-excites is answered at its
    root (the steam header's feedback), not by freezing the thermodynamics. Already the state of both
    engines: the port passes 1.0, and V1's ``step_sim`` sets ``g_dist = 1.0`` and never calls its
    ``_disturbance_gate``.
87. **A 322E002 tube rupture leaks process into the shell** (2026-10-09, handoff B-82): the
    instructor's malfunction (``trigger_fault`` id ``322E002``, its rate in t/h at the design
    differential) leaks the two-phase product on the live differential, sqrt(dP / dP_des); PT-329201
    loses it; its ammonia, CO2 and inerts leave with the LP steam, its water and solids join
    322D001A/B's water, its heat on the elements datum boils or condenses that water; the solids
    stay in the drums until the blowdown takes them (`units/synthesis/tube_leak.py`). V1's script
    injects the shell's water into the process, against the differential.
88. **FAST runs as fast as the machine allows** (2026-10-09, handoff A-18 option c): no
    interpolation table and no approximation for a pacing target; the physics sets the CPU cost.
    The engine already pays the owed time in whole 0.1 s steps (A-14).
89. **A 322E002 tube leak shows on AI-329701; the malfunction takes a rate** (2026-10-09, handoff
    B-90): the conductivity analyser on 329D001's LP condensate (A 329701, 0-10 uS/cm, the DCS's AH
    and SAHH) reads the leak's ammonia and CO2 as ammonium bicarbonate in the users' condensate,
    published in the port block ``ANALYSERS`` with the drums' solids; ``trigger_fault 322E002``
    takes ``rate`` (or ``value``) in t/h, 10 t/h on a bare trigger, and the instructor's panel has a
    rate box (`units/steam/condensate_analyser.py`).
90. **Trip 22.1 keeps V1's 57 / 55 C on TI-322015** (2026-10-09, handoff B-84): the HPCC rupture's
    cascade into 22.1 is emergent behaviour to teach; the margin stands until the DCS database's
    value is found.
91. **Downstream of a letdown the line holds its flash at the homogeneous density** (2026-10-09,
    handoff B-81): rho_m = 1 / (x / rho_g + (1 - x) / rho_l) on each valve's design flash, the run
    after the valve read from the isometrics (`data/process_routes.py`).
92. **FFIC-321404A / B are built as drawn** (2026-10-09, handoff B-85): PI ratio controllers on
    FY-321404 (0-4), 1.00 / 100 s and 1.00 / 90 s, each the external set point of its machine's SIC
    and following it while the SIC is not on cascade (UD-MR-321-FF-0002); V1's open-loop demand
    deleted (`units/feed/station.py`).
93. **No loop models the DCS table's deadband** (2026-10-09, handoff B-28): in a noiseless model a
    deadband only stalls the integral; LIC-329505's 2 %, V1's one use, set to zero too.
94. **323D002 forms no biuret** (2026-10-09, handoff B-25): V1's blender kept; the design formation
    is below the PFD's resolution and an anchored kinetic term would over-model it.
95. **PT-329201 is the loop's vapour inventory** (2026-10-09, handoff B-77 (b)): the vendor's 241.7 m3
    less the liquid the model holds, on the gas law at the PFD's off-gas density, with the reactor
    liquor's carbamate buffering — the Extended UNIQUAC slope of PFD 207's bubble pressure, anchored
    on its 141.3 bar a, read once at the design (0.01536 kg/(kg.bar)); each unit's holdup gain over
    its own step is liquid, not pressure; the backlog adds no pseudo-mass; V1's 1500 kg/bar deleted
    (`units/synthesis/loop_pressure.py`).
96. **Trips 21.2, 21.8 and 21.10 as AC4 executes them** (2026-10-09, handoff A-12): Uhde's application
    software ported (UD-MR-G00-FF-0004 PC21.1.1, 21.1.2, 21.5.1): live flags, no latch and no reset;
    21.2 resets XV-321901 / XV-322901's flip-flops, each pump's flag stops its machine; the bypass and
    trip hand switches maintained keyswitches; the DCS's limits the archive lacks stand-ins or not
    modelled; V1's 21.4 gone (no flag in AC4); 22.2 V1's, 155.0 / 148.0 bar a with decision 83's cut
    (`control/interlocks.Unit21Trips`).
97. **The loop's liquor condenses no more than it can hold at its bubble point** (2026-10-10, handoff
    B-91 (a)): PI-322E002 of the tick before against PT-329201, the condenser outlet's design head a
    subtraction of the two design pressures, sets the saturation fraction f = 1 - b_207 . d on the
    deficit d (decision 95's buffering), exactly 1 at and above the bubble pressure; 322E002's melt
    holds f of each distributing species' liquid, 322E003 condenses at most f of its demand, the
    reactor liquor buffers f of its b_207 (`units/synthesis/liquor_saturation.py`).
98. **Trip 21.2's five hand switches and AI-329701 on the screens** (2026-10-10): the converter's
    `DECIDED_ADDITIONS` — HS-321634, HS-321603 and HS-321604 on 321-1, HS-322606 on 322-1, HS-323604
    on 323-2, maintained keyswitches on the override widget, their positions in the packet's
    ``HAND_SWITCHES``; AI-329701 an indicator on 329-1 (`tools/convert_overlays.py`).
99. **HV-322604 is anchored at 72 %** (2026-10-10, handoff B-18): the stroke its vendor's trim passes
    the design purge at (UD-MR-G00-DZ-0042-010), decision 23's class; 322E003's two vent-opening
    terms read the same anchor (`data.unit_322e003.HIC604_DES_PCT`).
100. **PFD 734 enters 323E003** (2026-10-10, handoff B-37): FIC-323401's ammonia water from 328D003,
     a liquid inlet at the PFD's 56 C, as Uhde's loop summary names the service; V1's sink closed.
     The PFD's 323E003 balance does not carry it: LIC-323502 passes it on in PFD 308, and the
     plant's design seed relaxes onto its own steady state (`units/recirc/lp_carbamate_condenser`).
101. **Urea closes on a stage's drain** (2026-10-10, handoff B-20): PFD 314's urea, less the biuret
     323C003 makes, leaves by the drain, water giving way, and PFD 319's the same way; 323C003's
     design seed is a fixed point (`thermo.urea_liquor.close_urea_on_drain`, `data/unit_323.py`).
102. **322R001's liquor stands at most at its bubble point, and the residence time runs on the liquid
     passing** (2026-10-14, handoff B-92): no node above the liquor's bubble temperature at the live
     loop pressure — PI-322E002's Clausius-Clapeyron slope anchored on the pinned 183 C top node
     under the off-gas line's 141.3 bar a — the excess heat flashing the overflow's volatiles into
     the off-gas on their own enthalpies; the kinetics' throughput the larger of the liquid that left
     the column and the liquid that entered its holdup, so a filling reactor does not react for ever
     (`units/synthesis/reactor_boil.py`, `reactor_inventory.py`). Decisions 45 / 48's class.
103. **The plant DCS's readback is the datum** (2026-10-14): the process engineer's handwritten note
     of 13 October 2026 (`Urea Simulation Docs/Data/DCS_Extract_2026-10-13.jpg`) supplies LIC-323502's
     tuning (1.2, 400 s, DZ 2.0 % — the dead zone not modelled, decision 93), TT-322015's H2, 110 C
     (V1's 57 / 55 C superseded, decision 90's stand-in; V1's 2 K hysteresis kept), AI-329701's H1 /
     H2, 15 / 18 uS/cm, 323P008's low-level trip, 5 %, and 324F003's vacuum, -0.9 bar g; applied
     where a model reads them, recorded where none does yet.
104. **A stream a PFD unit balance closes without enters as its departure from its PFD row**
     (2026-10-14, handoff B-94): PFD 734 into 323E003 as 734 - 1534 kg/h in the tank's mass, its
     sensible term and its capacity — zero at design, the whole of FIC-323401's change off it
     (decision 100 kept). Rule 7 class.
105. **A condensing unit's liquor on its own bubble pressure, and a full sump condensing no more than
     drains from it** (2026-10-14, handoff B-91): 322E003's sump liquor on the melt's law anchored on
     PFD 206, its design head zero, in place of 322E002's fraction; the condensate capped at the sump's
     room less the wash and carryover, the rest left in the vapour. The retained gas behind HV-322604's
     seat is not added to PT-329201's node, which holds it already. Rule 7 class (decision 97's).
106. **323P008's low-level trip as AC4 draws it** (2026-10-14, handoff B-93): PC23.1.9 / 1.10's IC2 on
     LT-323503 < L2, the DCS's 5 %, live (decision 96's class); its relay raised as B-96.
107. **Trip 22.1's self-hold is the plant's logic** (2026-10-14, handoff B-95): the flood steam holds
     TI-322015 above H2 until the keyswitch HS-322915; closed with no code change.
108. **A valve sheet that prints its capacity at its cases' travels and names no curve runs on its
     printed points** (2026-10-14): PV-329203 and PV-329212 on Metso's Neldisc sheets, linear between
     the printed points to the rated Cv at full travel, the design stroke decision 23's, the normal
     case's xT. Rule 7 class (decision 23's).
109. **329D001's volume entered** (2026-10-14): 50 m3 on UD-AU-329-TL-0001; data only.
110. **B-91 accepted** (2026-10-15): the cold start (fit 136.04 bar g, tau 1 305 s) and trip 22.2 not
     reached (148.2 bar a) are the vapour-inventory node's answers to V1's procedure; closed. Its
     cold-start record was re-baselined on the committed engine by decision 168 (2026-11-04).
111. **An interlock's analogue limit carries a stated hysteresis where the archive lacks it**
     (2026-10-15, handoff B-96): LT-323503's L2 2 %, trip below 5 %, restart at 7 % — TT-322015's
     2-unit convention; logged in Open data gaps. Rule 7 class (decision 96's stand-in).
112. **A dry gas above a solid's saturation lays the solid down, its heat paid** (2026-10-14, handoff
     B-79 (b)): solid ammonium carbamate on Egan, Potts and Potts (1946) and Voskov and Voronin's
     enthalpy, the deposit carried to the receiver's liquor. Rule 7 class.
113. **The remaining vendor sheets applied** (2026-10-15): Metso's PV-329202 and PV-329208 on their
     printed points (decision 108), LV-329505 on Flowserve's trim with its normal capacity calculated
     by IEC 60534-2-1 (decision 23, session 37's method); FV-329401, PV-329204, PV-329207A / B
     catalogued, to be wired.
114. **A condenser's capacity on its dew point, its vent never reversed** (2026-10-15, handoff B-30,
     options (b) and (c)): 323E011's capacity on T_dew = 45 + Tsat(P) - Tsat(1.13) against the 35 C
     water, anchored on V1's 5589 kg/h, not capped at the gas that arrives (323E003's form, B-34);
     PV-323203's differential max(P - 1.0, 0). Rule 7 class.
115. **A held liquor's bubble point on its live vacuum** (2026-10-15, handoff B-22, option (b)):
     323F010 relaxes to its bubble point at PT-323204, V1's TD-016 design vacuum retired now that
     324E002's cold end is lagged (decision 49). Rule 7 class.
116. **Every Metso valve the archive prints on its trim** (2026-10-15): FV-329401, PV-329204,
     PV-329207A and PV-329207B wired on their printed points (decision 108's class); FV-329409
     catalogued, its cases on IAPWS-IF97's saturated liquid at the sheet's 95 C (the sheet prints no
     density), and wired. Rule 7 class (the density).
117. **The background PNGs frozen** (2026-10-15, handoff A-6): the ten 1366 x 720 renders are the
     canonical baseline; every symbol change through `tools/convert_overlays.py`'s ``DECIDED_EDITS``,
     ``DECIDED_ADDITIONS`` and ``NUDGE``; no PowerPoint toolchain ported.
118. **Every inlet at its producer's live temperature, in departure form** (2026-10-16, handoff
     B-31): T_in = T_in,des + (T_producer - T_producer,des), read the same tick where the producer
     steps first and a tick late where it steps after, so a producer at its design leaves the inlet
     V1's to the bit; utilities with no circuit (323E011's cooling water, 741 after 328E001, 954,
     911's enthalpy drop) at design. Rule 7 class.
119. **A-13 closed on its audit** (2026-10-16): every design differential an anchored law is
     normalised against written as the subtraction of its two design pressures, enforced by
     `tests/engine/test_check_valve_audit.py` with the assembled flowsheet's boot pin; the rule
     stands.
120. **Eight items signed off** (2026-10-16): B-2 (session 39's measurement), B-17 (13.8 C over the
     one steady record, B-3's reference), B-45 and B-52 (stable for training; their DCS rows a data
     gap), B-48 (kept as V1: no tray temperature in a lumped 328C003), B-72, B-74 and B-78
     (validated by Phase 7's runs).
121. **708 at 324F002's discharge temperature** (2026-10-16, handoff B-97, option (b)): the
     ejector's adiabatic mix of 706 at 324E002's cold end and 924 at the LP header's saturated steam
     enthalpy, at 323C005's pressure, its water condensing below its dew point, as its departure
     from the design mix, anchored on the PFD's 121 C. Rule 7 class.
122. **B-1, B-4 and B-12 signed off** (2026-10-16): the evaporators' anchored vapour vector with
     B-58's melt, 323C003's two-path friction-head law, 322F001's momentum closure and its 90.7 %
     stall, each the validated V1.1 baseline; their data gaps stay open.
123. **UF85 dosing live** (2026-10-16, asked in session 55): V1's ``step_uf85_cascade`` and
     ``route_lv324501``, which V1's step calls with the permissive forced, run on the live route,
     LV-324501B the interlock, FIC-335405 seeded at the PFD's ratio on the plant's design drain,
     617.07 kg/h; V1's tunings (no DCS row). Rule 7 class.
124. **Unit assignment by plant section, signed off** (2026-10-16, handoff A-8 closed): the
     section-level assignment built in sessions 3, 41 and 42 is the final V1.1 design; per-tag
     locking is not built. Every plant command type is attributed and tested; ``None`` unrestricted,
     ``[]`` assigned nothing; instructors and the loopback superuser never narrowed. **Superseded
     by decision 149** (2026-10-22): unit assignment and `data/tags.py` removed.
125. **The station token** (2026-10-16, handoff A-2 closed): an engine started with ``--token``
     admits only the stations whose ``hello`` presents it, the superuser included, and disconnects
     the rest with the reason; with no token, every station, as before. The token admits a station;
     its role is still the one it requests. The multi-station deployment is supported and the
     instructor's panel unpaused; one machine with the superuser stays the default. **Superseded
     by decision 149** (2026-10-22): the station token removed.
126. **The reactor liquor's buffering signed off** (2026-10-16, the 322E002 / 322E001 liquor data gap
     closed): decision 95's PT-329201 node — the loop's vapour on the gas law plus the reactor
     liquor's carbamate buffering on PFD 207's solubility, 2 160 kg/bar at design — is the V1.1
     baseline, the cold start it gives accepted in session 52 (decision 110). The condenser's and the
     stripper's liquors are not added to the buffering.
127. **Trip 21.2 shuts XV-322902 and XV-322903** (2026-10-16, decision 96's class): AC4 PC21.5.1's
     flag also resets XVY-322903's flip-flop and XVY_322902's, which the Safeguard SG1 ANDs into
     XV-322902's command; both valves shut while the flag is lost and their opens are refused.
     320K002's demand goes to zero and a demand is refused while the flag is lost (decision 83's
     class). V1's 21.2 shut neither. Confirmed as built by the process engineer, the demand cut
     included, 2026-10-16.
128. **The open data gaps are the final V1.1 ledger** (2026-10-16): the archive's drawings,
     isometrics, loop summaries and AC4 / SG1 diagrams are searched; the 19 rows left in
     `handoff.md` need vendor curves (Körting, Metso, Flowserve) or the plant DCS's database, and
     each keeps its stand-in, assumption or V1 value as built.
129. **The console revised from its slides** (2026-10-16, the process engineer's request): no valve
     icon but the XVs' — each modulating valve a readout of its opening in per cent; no readout over
     another or over the drawing at design with a digit to spare (the converter's `NUDGE` rows); the
     destination blocks V1's migration stripped from seven backgrounds restored from the slides; a
     hovered page button tinted, not blacked out; HS-322915's square green, red while turned, as its
     slide's comment asks.
130. **The liquid-rated safety valves relieve gas on Sempell's coefficient for their orifices**
     (2026-10-16, decision 34's assumption replaced): 0.922, what Sempell prints for orifices F, K and
     M in gas service at full lift in the same file (UD-RL-G00-DZ-0001-001); 0.917 was assumed. The
     open data gap closed.
131. **HV-323605, PV-323203 and TV-328002 on their Metso sheets** (2026-10-17, decision 23's and
     108's class): each on its printed Neldisc capacities from the stroke where its normal case
     passes the design flow — HV-323605 64.08 % on xT 0.38 (the overhead V1's balance gives,
     12 013 kg/h), PV-323203 21.64 % (PFD 702), TV-328002 55.04 % (PFD 1028, 408 t/h) — HIC-323605,
     PIC-323203 and TIC-328002 seeded there, V1's linear laws on the equivalence harness's switches.
     PV-323202A / B (TV-323013A / B) stay catalogued: TIC-323013 models the tempered water's supply
     temperature directly (decision 13).
132. **A full 323F004 overflows into 323E011** (2026-10-17, handoff A-22 (a), decision 11's class):
     above the holdup LI-323505 reads as 100 % the excess leaves at the drum's composition and
     temperature, up its vapour line into 323E011's shell the same tick, liquid not gas load, as a
     full 328D001's (A-15); ``FlashTank(ceiling=False)``, V1's uncapped holdup, on the equivalence
     harness's switch.
133. **The backward species step at a liquor stage's heel** (2026-10-17, handoff B-98 (b), decision
     78's class): where the drain passes more on the tick than the stage holds, m_liq dt / 3600 >
     M_new, `liquor_stage.advance_species` takes the drained composition at the end of the step;
     V1's explicit step to the bit everywhere else, and on the harness switch (``backward=False``,
     the units' ``backward_species``) where an equivalence test reaches a heel.
134. **No crystallisation restriction on 324F001 / 324F003** (2026-10-17, the process engineer): as
     V1, whose ``mushy_flow_factor`` acts on 322E001's bottoms and 322E003's overflow alone; one on
     the evaporators would interfere with the cold start's drainage. A melt the model cools below
     its crystallisation point there (S4-chest-close, 58 C) is recorded, not restricted.
135. **322E002's saturation fraction solved on the tick** (2026-10-17, handoff A-21 (b); decision
     78's class on decision 97): wherever the melt the tick-before fraction lets condense would move
     the fraction, f = f(P_bub(f), PT-329201) is solved within the tick, its root bracketed on [0, 1];
     at its fixed point the tick is the tear's to the bit. The stripper's split is not bounded by its
     shell (option (c) not taken then; decided 2026-10-21 as decision 139).
     ``CondenserHoldup(implicit_saturation=False)``, the tear, on the
     synthesis harness's switch.
136. **322E003's capacity on its shell's effectiveness** (2026-10-17, handoff B-99 (b1); decision 36's
     class): the condensation capacity's flow term is the shell's conductance eps . C over its
     design's, where V1 takes the flow ratio, and where the capacity falls below the demand the
     published duty and TT-329125 follow it; TT-322002 stays on the demand.
     ``ScrubberSump(effectiveness_capacity=False)`` on the harness's switch.
137. **The vapour draw in the heel's backward species step** (2026-10-17, handoff B-101 (b);
     decision 133 extended): where the drain and the vapour together pass more on the tick than the
     stage holds, both leave at the step's end composition, each species boiling off at its live
     y / w.
138. **323F004 on its geometry** (2026-10-17, handoff B-100 (b), measured first; decision 33's
     class): the drum's shell and two DIN 28013 heads (3.402 m3), LT-323505 read between its taps,
     2900 mm apart from the outlet line to N7 on the top head, V1's 60 % set point holding 1837 kg;
     the A-22 ceiling at the full drum; LV-323505's seal at the reading of an empty bottom head.
     ``V1_DRUM`` on the harness's switch; 323E011's 323F004 vapour space (B-51) unchanged.
139. **322E001's duty bounded by its shell** (2026-10-21, handoff B-102 (b), session 63): the split's
     per-species enthalpy balance bounded by Q_max = Q_des . LMTD(T_steam, 187, 172) / LMTD_des, the
     live 329D005 saturation against the tube side's design profile (the live TT-322013 / TT-322004
     measured binding every turndown: 80 % load kept 42 % of its lift); past Q_max . (1 + 5e-4) — the
     band the smallest round number above the seed's drift, 1.68e-4 — the lift of NH3, CO2 and H2O
     beyond the sweep scaled by lambda until the balance meets it, the rest left in the bottoms.
     ``stripper_322e001(shell_bound=False)`` and ``StripperSump(shell_bound=False)`` on the harnesses.
     B-103 (the same session) is decision 62's class, applied: LT-322501's full sump held back in the
     tubes above it, ``StripperSump(hold_full=False)`` V1's clamp on the harnesses.
140. **322E001's tubes standing full** (2026-10-22, handoff B-104, session 64; decision 62's class
     extended): the liquor a full LT-322501 sump holds back in the tubes capped at the bundle
     standing full, 8 688.7 kg (7.658 m3 at 1 134.64 kg/m3); holding any, the tubes take the drain
     and their unsubmerged share of the design bottoms, take = drain + (1 - sigma) . 130 482 kg/h,
     and 322R001 discharges through HV-322605 no more than that on this tick's bottoms per kilogram
     taken, keeping the rest; what still arrives past the ceiling handed back to its holdup. The
     shell's capacity derated by f_sub = 1 - 0.70 sigma (322E003's flooded-surface floor) and the
     bottoms cooled to T_cryst + f_sub (T_bot - T_cryst), the process engineer choosing the
     crystallisation floor, 132.7 C, as the "flooded limit" (AskUserQuestion, session 64). Two caps
     measured and rejected first (the room over the live transit starves; the transit's contents
     are not conserved by its dead time). ``StripperSump(tube_ceiling=False)`` on the harnesses.
141. **323D001's liquor carried into 322E003** (2026-10-22, handoff B-105, session 64): the tank's
     NH3, CO2, H2O and urea as its departure from PFD 308, each liquid inlet at its PFD row and the
     condensate at the gas's closure on PFD 308, stepped backward on the holdup; 322E003's wash on
     308's live composition (each species' departure on the delivered wash) and TT-322002 blended
     by the wash's share on its temperature's departure from 74 C; both a tick late with 308's flow.
     ``LpCarbamateCondenser(track_species=False)`` on the harnesses. `Scenarios5.md`'s LPCC case on
     FV-323401 in MAN at 100 %, about 7 000 kg/h, past FIC-323401's 2 000 kg/h set-point ceiling.
142. **322E002's melt below its azeotrope** (2026-10-22, handoff B-106, session 64): below N/C 3.0
     the bubble pressure's N/C factor f_N(3.0) . P_EU(N/C) / P_EU(3.0), the Extended UNIQUAC
     bubble pressure of the design tube-side feed at 170 C, its shape only; V1's K_N line at and
     above 3.0. ``CondenserHoldup(low_nc_branch=False)`` on the harnesses.
143. **324F003's lost seal admits air** (2026-10-22, handoff B-107, session 64): below LT-324501's
     seal band atmospheric air at PFD 783's 32 C enters on the blow-through law on LV-324501A's
     liquid sizing (the loop summary's 1221 kg/m3, 6.9 -> 3.7 bar a; PFD 402 at the 75 % design
     stroke), choked, joining PV-324203's false air into 324E005.
     ``SecondEvaporator(seal_air=False)`` on the harnesses.
144. **Stage 2's fixed point on its energy balance** (2026-10-22, handoff B-108, session 66; decision
     78's class): where V1's G7 sweeps do not settle to 1e-12 in 20, the stage's temperature solved
     on its own energy balance, G(T) = T_sweep(T, P(T)) - T, P(T) the sweep's backward vacuum step
     settled at the trial T, bracketed between the coldest of the feed and the melt and the hottest
     of the chest and the melt, by false position to 1e-12; no sign change leaves V1's last sweep.
     ``SecondEvaporator(bisect_fixed_point=False)`` on the harnesses.
145. **PT on 322R001 capped where the melt flashes** (2026-10-22, handoff B-109, session 66;
     decision 70's class): the reading's base min(P_bub, PT-329201 + 3.5 bar), the head
     `liquor_saturation` uses, so V1's reading holds wherever the melt does and at the design. The
     paste's min(P_bub, PT-329201) would have moved the design reading 3.5 bar, the design melt
     bubbling at 322E002's 144.2. ``ReactorInventory(flash_cap=False)`` on the harness.
146. **PFD 308's line on its isometrics** (2026-10-22, handoff B-110, session 66; B-21's and decision
     74's classes): 323006 (UD-RL-100-MB-0017) and 323004 (MB-0015), 9.6 + 38.4 - 0.2 m of 88.9 x 7.1
     high-pressure pipe, 0.2095 m3, 24.94 s at 36 835 kg/h and 1218 kg/m3; 322E003 owns the line,
     its flow at once, 323D001's composition and temperature a residence late.
     ``ScrubberSump(wash_line=False)`` on the harness.
147. **The azeotropic rise added in bar** (2026-10-22, handoff B-111, session 66; decision 51's class
     on decision 142): below N/C 3.0, f_N = f_N(3.0) + (P_EU(N/C) - P_EU(3.0)) / P_des, where the
     ratio multiplied the Extended UNIQUAC model's rise by 144.2 / 44.37 = 3.25.
148. **PT on 322R001 on its feed line's PFD drop** (2026-10-22, handoff B-112 (a), session 67;
     decision 70's and A-13's classes): P_R001 = min(P_bub, PT-329201 + 3.5) - 2.9 (rho_des / rho)
     (m / m_des)^2, the 2.9 bar the PFD's 144.2 at 322E002's outlet (202, 205) less 141.3 at the
     reactor's top (203, 207) written as their subtraction (`unit_322_loop.REACT_FEED_DP_DES_BAR`),
     rho_des the urea-solution correlation at the design seed's feed and 170 C (752.2 kg/m3),
     m_des the seed's 250 639 kg/h, so the reading is 141.3 at the design to the bit and moves one
     bar per bar of PT-329201 where B-109's cap binds. V1's ``p_syn - 144.2`` on the nominal 990 and
     the condenser's liquid make read 136.12 at the design. 322R001 carries no transmitter of its
     own (P&ID 102, UD-MR-322-EC-0001); the reading is the packet's and the stream inspector's.
     ``ReactorInventory(design_drop=False)`` on the harness.
149. **Single-console architecture** (2026-10-22, session 68; superseding decisions 72, 124 and
     125): the simulator is a single-console desktop application (`python run.py`, or
     `launch.bat`). The multi-station server and station launch modes, station roles, the station
     token, the station roster and trainee section assignment are removed, `data/tags.py` with
     them. Retained: the headless engine boundary (`ureasim/net`, `hmi/bridge.EngineBridge` over
     loopback `127.0.0.1`, the physics thread of `engine_host`), snapshot back-pressure, the 5 s
     staleness watchdog, history backfill, and the engine's process refusals with their reasons.
     The plant controls stay on the DCS screens and faceplates; pacing, freeze, reset,
     malfunctions, the battery-limit `co2_set` and exercise save and restore stay in the
     Instructor menu's panel, executed without a role gate. The server refuses a `hello` from any
     address but the engine's own machine; the protocol version is 2.
150. **Seven control valves on the vendor sheets found in session 69** (2026-10-22, decision 23's
     class, confirmed by the process engineer): LV-328503, LV-328504, HV-329602 and the 323D001
     vent (TV-323013 on the sheet, the port's PV-323202) on Fisher's UD-MR-G00-DZ-0014; HV-329601,
     PV-329207C and LV-324501A / B on Flowserve's Pos. 65, 76, 148 and 149 — each on its sheet's
     named curve (the port's equal percentage on the IEC 50:1, its linear), its design stroke where
     its rated capacity passes the design flow on its normal case, a valve shut at design on its
     full-stroke capacity there, FL or xT from the sheet (the Mark Ones' xT from their printed
     choke drop). The travels the sheets print sit off the named curves (two to twenty points) and
     are recorded, not run. LV-324501A / B's sheets size the melt on SG 0.751: their capacities are
     taken to the melt's 1221 kg/m3 on m = Kv sqrt(rho dP) — the Kv a mass flow needs scales as
     m / sqrt(rho), the mass a stroke passes as sqrt(rho), 1.275 times the sheet's — which puts A's
     design stroke at 75.35 % and B's full stroke at 251.5 t/h (197.3 t/h at the sheet's density).
     V1's laws stay on each harness's switch.
151. **322E006 on PFD 28's cooling water** (2026-10-22, decision 36's class, confirmed by the
     process engineer): 14 t/h (streams 1010 / 1011) where the port back-solved 10 374 kg/h on the
     datasheet UA for want of a document; the UA is back-solved instead, 20.448 kW/K, so 755 holds
     the PFD's 40 C, and the datasheet's 30.776 kW/K stays the rated surface's margin.
152. **Every module inside the 600-line target** (2026-10-23, session 70, a pasted directive;
     `CLAUDE.md` §1 rule 1): the six modules above 600 lines split along their physical seams with
     no change to a relation — the vendor sizing records and Metso's catalogue out of
     `control_valves` (`valve_sizing`, `control_valves_metso`); 323C003's stage into the column's
     tag module `unit_323c003` beside its relief, and 323D002's into `unit_323d002`; the vacuum
     train's condenser ratings, vapour rows and ejector ratings into `unit_324_train`; 322E003's
     shell and sump level into `scrubber_shell` and `scrubber_level`; the command payload helpers
     and unit 329's handlers into `command_payload` and `command_steam`; solid carbamate's
     saturation into `thermo.carbamate_solid`. The lines move verbatim; the module a name left
     re-exports it, so no caller changed an import; each new module imports nothing from the one
     it left; each has its own test file.
153. **Two data-gap rows closed** (2026-10-23, session 71, the process engineer, on an external
     report audited against the code): 322C001's bottom head volume, 0.1029 m3 — the arrangement
     drawing's Da 950 and R 760 on DIN 28013's proportions, the exact torispherical integral, which
     two correlations confirm within 1.2 % — is the vessel's geometry, as decision 138 built
     323F004's heads, not a missing datum; the NH3 / CO2 Henry constant on a urea-melt basis is
     closed as a quantity no vendor, no DCS database and neither archive holds, B-1's PFD-anchored
     vapour vector on B-58's melt (decisions 42, 122) the model. The Neldisc row stays open on
     decision 108's linear chord: the Neles bulletins the report tabulates are in no archive and
     miss the sheets' printed points.
154. **322E001 on its 2,950-tube replacement** (2026-10-28, session 72, the process engineer): the
     equipment model runs the bundle installed at the last turnaround — Resta 6355 for Stamicarbon,
     2,950 tubes 31 x 2.5 mm on 6.000 m, 1,724 m2, 28.83 m3 tube side, a 2,425 mm bottom channel —
     while the 1750 MTPD PFD stays the flowsheet's anchor (decision 47). The flooding limit per tube
     scales from V1's 145 kg/h on Wallis's counter-current law, as D^2.5 (159.9 kg/h on the 26 mm
     bore); the shell's capacity is V1's design duty times the two process datasheets' U.A ratio,
     1.142 (1,325.7 against 1,160.5 kW/K, each on its own terminal temperatures); the holdup, the
     standing-full mass (10,663 kg), the sump's span and the loop's vessel volume are the
     replacement's. V1's 2,600-tube bundle stays on every harness's switch.
155. **The plugged tubes derate their exchangers** (2026-10-28, session 72, the process engineer):
     60 of 322E002's 2,929 tubes, 16 of 322E003's 525 and 15 of 323E010's 1,087 plugged at the last
     turnaround; each conductance is its clean value times the share in service (0.97952, 0.96952,
     0.98620), the coefficient held, and the plugged bores leave the loop's vessel volume. The clean
     bundles stay on the harnesses' switches (`plugged=False`). The plugged plant leaves the PFD's
     seed (B-113).
156. **The plant DCS's faceplates of 24 October 2026 are tuning rows** (2026-10-28, session 72,
     decisions 76, 77 and 103's classes): TIC-323012 1.00 and 300 s (on its 0-160 C and PT-329208's
     0-6 bar), FIC-328404 1.00 and 200 s on 0-8.0 m3/h, PIC-329205 3.00 and 50 s on 0-16 bar g — a PI
     on its split where V1's is proportional at 40 %/bar — LIC-329502 3.00 and 250 s with its
     derivative off, TIC-328012 0.20 and 3000 s on 0-200; AT-329701's object display gives
     AI-329701's present range, 0-30 uS/cm. V1's tunings stay on the harnesses.
157. **The plugged tubes re-anchored on the bundle in service** (2026-10-28, session 73, handoff
     B-113, option (b); amends decision 155): each of the three conductances is back-solved on the
     PFD's design point and the plant runs that point with its tubes plugged, so the conductance
     holds on the tubes in service at a coefficient 1 / f_tubes above the clean bundle's
     (`PluggedBundle.u_service_ratio`); the tube counts, the active surfaces and the plugged bores
     out of the loop's vessels (245.61 m3) stay. The plant's first tick is the PFD to the bit and
     thirty minutes hold the clean basis to the printed digits. V1's clean vessel volume stays on
     the harnesses' switch (`LoopPressure.vessels_m3`).
158. **LV-322501's failure case read tick by tick** (2026-10-28, session 73, handoff B-114; signed
     off as built, session 74): V1 and the port already scale the blow-through by the stroke over
     its design stroke (V1 `main.py` 7633, `stripper_sump.py`), and SV32351 / SV32352 already pop at
     their 6.010 bar a set on the sheets' 1.010 bar atmosphere (decision 71), reseating at 5.51; no
     relation changes. LV-322501 forced wide open lifts them 91.0 s on, 12.6 s lifted, 51.4 t/h at the
     peak, PT-323201 to 6.027 bar a; the 31.5 t/h ceiling is the sump's level standing in its seal
     band (1.2 %, the nozzle 42 % covered by the bottoms still arriving). A Phase 7 survey reads a
     relief, an event shorter than its sample, on its peak between samples.
159. **The vacuum bleeds on the 1750 MTPD design basis** (2026-10-28, handoff B-115, option (a);
     decisions 6 and 47): the 8-10 October 2026 trend is the plant at 112.5 % load on deeper set
     points (-0.72 and -0.90 bar g, HIC-329605 at 91.5 %, the bleeds 0.2 and 0.5 %); the model keeps
     the PFD's design strokes (PV-324202 61.07 %, PIC-324203 92.0 %). The bleed valves' data-gap row
     is closed.
160. **TIC-328008 and FFIC-335406 on their faceplates** (2026-10-28, handoff B-116, options (b) and
     (a); decisions 10, 21, 26, 77 and 103's classes): TIC-328008's 1.00 on 0-100 wt% water and 60 s,
     its output on FIC-328404's 0-8.0 m3/h in mass, carried onto the model's mol% PV by 737's local
     slope at the PFD's composition, d(wt%)/d(mol%) = 0.96559 — 84.59 kg/h of reflux per mol%;
     FFIC-335406 a ratio station, RAT 0 to 0.0080, OUT 0 to 0.80 t/h, FIC-335405's set point the
     ratio times the melt, its ratio tracking the achieved one while FIC-335405 is out of cascade.
     V1's tunings and V1's PI master (``ffic_335406(station=False)``) stay on the harnesses. Signed
     off as built (session 74): the design seed is the PFD's ratio, 694 / 85 405 = 0.0081260, which
     closes the design at 617.0722 kg/h to the bit, 1.6 % above RAT H; an operator's ratio and a mode
     transfer are held to RAT H. B-117, the dynamic audits' finding — TIC-328008, as every cascade
     master V1's ``_ctrl_ipd`` builds (`ProcessLoop`), integrating while its slave is out of cascade,
     so FIC-328404 steps on its return — signed off as built (decision 120's class).
161. **323F010 drains on its own head** (2026-10-30, handoff B-119, option (b), session 78; decision
     158's class for its premise): the leg's isometric (UD-RL-100-MB-0142) puts 323F010/N2 at
     EL +15 740, 9.645 m above 323D002/N1, which the tank's general assembly (UD-AU-323-TL-0001)
     places 5 295 mm above its +800 reference with a dip pipe into Compartment I. A full vacuum holds
     8.98 m of PFD 317's 1 151 kg/m3 melt, so with the tank at its design liquid level the leg's
     column stands 1.013 m below N2 and never fills to the separator. The separator drains through
     N2 on its own head, m_317 = m_317,des . sqrt(M / M_des), anchored on V1's design holdup and
     drain, its pressure no part of the drive (`units.recirc.barometric_leg`). V1's leg (report
     A-17), which takes the column as standing full to the separator, stays on the harnesses'
     switch, ``PreEvaporator(own_head_leg=False)``.

162. **323F010's pressure step solved itself where its holdup boils** (2026-10-30, handoff B-122,
     option (b), session 79; decision 78's class): on a tick where the held liquor boils past its
     bubble point (B-24) at the old PT-323204, at the Jacobian's 1e-6 bar probe or at the
     linearised step's end, the backward step P' = P + f(P') dt is solved itself between the old
     pressure and the explicit step (`core.node.backward_euler_pressure`, V1's `_backward_euler_p`
     ported verbatim); elsewhere the linearised step, to the bit. The boil-off is zero above the
     pressure that brings the liquor to its bubble point and falls about 9 t/h per mbar below it,
     and its root can sit on a thermo-memo bin's edge, where it stops answering the pressure: the
     linearisation carries neither, and under LV-322501's blow-through surge it overshot into
     single-tick flashes of 9 to 21 t/h that the pressure never saw. A settled state is untouched:
     there f(P) is 0 and both steps return P. The equivalence transcription carries it under its
     ``boil_decided`` switch; ``boil_decided=False`` is V1 verbatim. The synthesis loop's harness
     keeps the linearised step on every tick, ``PreEvaporator(exact_boil_step=False)``, as it keeps
     V1's leg (decision 161): the LP header carries the step's difference to the loop, and the
     harness's knife-edge transients answer it at length. The stage's tests assert both sides.
163. **V1's thermo memo kept on 323F010** (2026-10-31, handoff B-123, option (a), session 79): the
     memo (`thermo/memo.py`, ported numerically identical) answers 323F010's bubble point on the
     first-order expansion about its bin's canonical point and its flash on the bin's K-values, so
     the bubble point lies up to 0.035 C off the rigorous surface and steps up to 0.026 C at a bin
     edge. PT-323204 chatters by ±0.012 mbar in a quiet boil and rings period-two at ±0.22 mbar
     under a 2.75-fold feed surge on the stage alone, below the transmitter's resolution; the memo
     stays as ported and no relation changes.
164. **B-121 closed as built: PIC-323202 and the unit 328 pair are operator moves** (2026-11-02,
     handoff B-121, option (a), session 80): the ammonia water 328D003 gains at 105 % load above
     FIC-328402's design flow is the LP section's vented ammonia scrubbed into 343 (As-Built §XCII.3,
     §XCIII.2), not a unit 328 relation. PIC-323202 at the loop summary's 3.9 bar a — any set point
     from 3.5 bar a — holds the LP vents shut at 105 and 110 % and takes 3.1 t/h off 343; FIC-328402
     and FIC-329402 scaled together on load balance 328D003 and keep 328C003 from filling or
     draining. Both are entries on existing faceplates; no relation changes (As-Built §XCIII.10).
165. **V1's source tree named at `E:\Simulator\Urea Simulation`** (2026-11-04, handoff A-24,
     session 82): the tree whose `backend\main.py` is 920 232 bytes of 2026-09-18 and whose
     boot-pin cache carries the key `ureasim/data/synthesis_pin.py` pins. Every equivalence test and
     the Phase 7 runner's V1 side load V1 from it; the older copies (`main.py` 669 044 bytes,
     2026-08-20) are not used. No relation changes (As-Built §XCV.1).
166. **The plant starts when the operator presses 100% LOAD** (2026-11-04, session 84, the process engineer's
     request): the start-up intro ends on a 100% LOAD button, and until it is pressed the engine is held at
     its design seed, the 1750 MTPD design basis, on its own `freeze`; the press releases it with the same
     command the instructor's RUN sends, `on` stated. The console is built at the press and connected only
     then, shown on the first packet, and a failed or silent step shows it anyway with the reason in the
     status bar. `python run.py --no-intro` keeps the earlier behaviour, the plant running from the start.
     No relation changes; the intro computes no process quantity (As-Built Part XCVII).
167. **The start-up intro's six open points decided and closed** (2026-11-04, session 85, the process
     engineer's directive, handoff A-25): (1) the frame cost is cut without changing the picture, by
     measured steps (As-Built XCVII.3), and what a cache replaces is held to the original by a reference or a
     pixel-identity test; (2) the first packet after a held start is allowed 30 s by the bridge's watchdog
     (`FIRST_PACKET_STALE_MS`) and the strict 5 s applies from the first packet on, the thermo memo untouched;
     (3) the intro lights the sections in the console's tab order, 321, 322, 329, 323, 328, 324; (4) the
     flyby's drawing choices stand as built, a stylized splash and not an operator training mimic (322D001
     drawn once, 322F001 at the junction, HV-322602, instruments and unlabelled valves omitted, 322R001's
     liquid outlet at the bottom nozzle); (5) the logo is resampled 2x and drawn with smooth pixmap
     filtering; (6) every intro module has a test file of its own. No relation changes.
168. **B-124 closed on option (a): the cold start accepted as the committed engine's, decision 110's
     record re-baselined** (2026-11-04, handoff B-124, session 86). 322E002's low-N/C branch
     (decisions 142 and 147) stays as built. Neither archive bounds the melt's bubble pressure below
     N/C 2.6, decision 147 states no validity range, and with the branch off the start is still
     outside the start-up band. The Phase 7 cold start's record is now the committed engine's (unchanged
     since 7a8fa3a):
     - trip 22.1 at 107.9 s;
     - PT-329201 111.5 bar a at 2 000 s and 150.7 at 3 000 s, peaking at 154.7 bar a at 3 300 s;
     - trip 22.2 at 3 322 s, cutting the CO2 and both ammonia pumps; 79.7 bar a by 16 000 s;
     - LT-322504 at 0 % throughout, the trip coming before the reactor reaches its lip.
     Its fit (tau 540 s, dead time 540 s, final 78.61 bar g) is of a tripped trajectory and not a
     start-up answer. On record with it:
     - Session 82's bisect to 15e66c2;
     - the branch off: no 22.2, tau 1 350 s, dead time 540 s, final 137.45 bar g, the reactor at its
       lip from 6 420 s;
     - the SOP's filling ratio: 22.2 at 5 863 s;
     - the fill probe: LT-322504's 36 % is a full reactor at its lip, session 52's full at 8 000 s the
       band's top; the backup above the lip moved with 322E001's shell bound (decision 139, B-102, in 15e66c2): with it off LT-322504 peaks at 91.2 % at 7 740 s, while B-103/B-104 and the bundle alone do not restore it.
     The trip 22.2 scenario keeps decision 110's answer. No test pins the record, and no relation
     changes (As-Built §XCVIII.1).
169. **A-26 and A-27 closed: the intro painted on a GPU canvas where there is one, and a frozen plant's first
     tick rehearsed so its console has a packet** (2026-11-04, session 87, the process engineer's directive,
     handoffs A-26 and A-27). (1) The start-up intro is painted through a multisampled `QOpenGLWidget` child
     (`hmi/intro/canvas.py`) where a hardware OpenGL 2.0 context can be made off screen, and by the window itself
     on every other platform, on a software renderer, when `UREASIM_INTRO_RENDERER` is `raster`, and when the
     canvas has no valid context a second after it shows. The painter, the scene and the data are the same either
     way, the picture matches within 3 in 255 and the edge energy within 0.5 %, the start-up path, the exit fade
     and the status line painted before a blocking step are checked under it, and the layering rule stands (only
     `painter.py`, `canvas.py`, `splash.py` and `__main__.py` import Qt). The fixed-stage layer, a cache per
     azimuth and worker threads were measured and rejected. The claim is bounded by what was measured: 60 fps
     through 4 busy processes of 20 logical in both window modes and fullscreen through 8, the main thread's
     paint at 7.5 ms windowed and 8.2 ms fullscreen; the whole frame is GPU-bound at 13.5 and 15.6 ms, a GPU in
     use by something else was not tested, and windowed under 8 busy processes neither renderer holds 60 fps.
     (2) A plant reset or restored while the engine is frozen publishes its first tick, rehearsed on a copy of
     the plant, labelled with the plant's own time and not stepped (`engine/rehearsal.py`), so the console's 5 s
     watchdog stays for a dead link and never fires on a held engine; an accepted command on the held plant is
     shown, a refused one changes nothing. The plant held behind the start-up intro stays silent until 100% LOAD
     (the process engineer, asked, kept decisions 166 and 167 for it: the start-up controller reads the first
     packet as the plant running, and the thermo memo is not warmed). No relation changes; fresh-process runs show
     no trace of the rehearsal on the ticks that follow (As-Built Part XCIX).

170. **The five balanced Neldiscs on Valmet's S-Disc table through their sheets' printed points** (2026-11-06,
     session 89, the process engineer's directive, data gap 7; decisions 108 and 153's class, a decided
     divergence from the chord). Metso's NELPROF sheets print three capacities per valve and name no curve; the
     chord drawn between them, and from the last to wide open, overstated a balanced valve's capacity by up to
     30 % between widely spaced points. Valmet's public bulletin 2SL120EN (4/2022) Table 2, the balanced Neldisc's
     Cv / Cv_max at 10-100 % opening by ANSI class, reproduces the printed points of PV-329212, PV-329207A / B and
     PV-329208 (sheet valve series S-L-ANSI150, ASME 150 column) and PV-329204 (S-L-ANSI300, ASME 300) to within
     1.3 % on the catalogue Cv. The trim is now every printed point of its sheet, exactly, and between them and
     from the last to wide open the table's shape mapped affinely onto each segment (`control_valves_metso._s_disc`,
     ``S_DISC_RELATIVE_CV``); `rated`, the cases and the sheets' FL and xT are unchanged, so the full-open
     capacity, every printed flow and the design flow hold, and the Fp of the two valves in a larger line needs no
     separate treatment (the report's suggestion to normalise on the catalogue Cv was dropped: anchoring on the
     printed points leaves PV-329204's and PV-329207B's full-open capacity at their FpCv). The design strokes move
     only where the design flow lies between printed points: PV-329207B 54.9630 to 55.9717 %, PV-329208 27.2232 to
     27.2640 %, PV-329212 54.6805 to 54.6843 %; PV-329204 (a printed point) and PV-329207A (full stroke) none.
     The nine conventional Neldiscs keep the chord (no table is published; bulletin 2LW22EN prints none), and
     session 71's "up to 30 %" against the bulletin is corrected: it set the S-Disc table against a conventional
     valve (As-Built §CI.1). Both sides are pinned in `tests/data/test_control_valves_metso.py`
     (`test_decision_170_both_sides`, the chord rebuilt through `_neldisc`); the design seed's packet differs from the
     chord's by at most the PIC-329207B output's intended 1 point (15 minutes, 24 914 leaf-samples above 1, 56 beyond
     0.1 %); the dynamic pins of the pre-evaporator, the steam network, stage 2 and the vacuum train moved with the
     valves' gain between the printed points (As-Built §CI.1). The V1-side equivalence suites need `E:` and were
     not run (the drive is not mounted); their decided-equivalence modules assert the vendor-trim side and are to be
     re-run when it is back (handoff A-29).
171. **The start-up intro's LOAD button: the plant started from a saved exercise** (2026-11-06, session 90, the
     process engineer's request of 2026-11-05 and answers of 2026-11-06). The intro ends on two buttons:
     100% LOAD, as decision 166 built it, and LOAD, which starts the same held plant from a saved exercise. After
     LOAD the console asks the engine for its exercises (the protocol's `exercise_list`), the operator chooses one
     in a chooser over the intro that renders the engine's names and reads no file (`hmi/exercise_chooser.py`), the
     engine restores it (`snapshot_load`, the instructor's RESTORE), and only once the engine has accepted it is the
     plant released with decision 166's `freeze` command. The hand-over ends on the first packet after the release is
     accepted, never on the restored plant's rehearsed one (decision 169). Cancel, or no saved exercise, takes the
     intro back to its two buttons with the reason on its status line, nothing started, until the operator presses
     one; a refused exercise reopens the chooser with the engine's reason, the plant still held and untouched; the
     wait for the engine does not run while the chooser or the buttons wait on the operator. The engine lists, beside
     the instructor's folder (`UREASIM_EXERCISES`, or `~/ureasim-exercises`), which SAVE writes, a folder of exercises
     shipped with the simulator, the repository's `scenarios`, which it never writes: a shipped name is the shipped
     file and a save under it is refused (CLAUDE.md section 6 keeps training saves out of the repository). LOAD is the
     one exercise restore outside the Instructor menu (CLAUDE.md section 4a), at the process engineer's request; Enter
     keeps pressing 100% LOAD. No relation changes; in the engine only `EngineSession`'s exercise folders change
     (As-Built Part CII).
172. **A silent engine's last packet is not replayed** (2026-11-06, session 91, handoff A-28 option (a), the
     process engineer's decision). The console server stamps each published packet on a monotonic wall clock and
     replays to a console that connects only a packet at most `data.engine.SNAPSHOT_REPLAY_MAX_AGE_S` (1.0 s, ten
     publish passes) old; an older one is not sent: the console gets an empty snapshot and the status "ENGINE
     SILENT — no packet for N s" (fault) in place of the stored status, and the engine's next publish sends the
     stored status again, then its packet. A running or frozen engine publishes every pass, so it is never
     affected; an engine that has never published (the plant held behind the start-up intro) is answered as
     before. No relation changes (As-Built §CIII.1).
173. **A closed bridge does not reconnect** (2026-11-06, session 91, handoff A-30 option (a), the process engineer's
     decision). `EngineBridge.close()` sets a closed flag before it aborts the socket, and the retry scheduler
     declines while it is set; `connect_to` clears it. No relation changes (As-Built §CIII.2).
174. **Trip 22.2 kept as the simulator's own protection and named so on the console** (2026-11-06, session 91, open
     data gap 6, the process engineer's decision). Neither AC4's application software nor the Safeguard SG1 draws a
     synthesis high-high pressure trip (As-Built §LXXIII.7); V1's trip, its logic and its 155.0 / 148.0 bar a stay
     as built (the decision of 2026-10-09), and the console names it "22.2 (simulator)" wherever it names the
     trip: the pump faceplate's interlock line and the engine's refusals and acknowledgements
     (`data.unit_322_loop.TRIP_LABELS`, `trip_label`). The data gap's row is closed (As-Built §CIII.3).
175. **322E001's service coefficient closed by decision** (2026-11-06, session 91, open data gap 11, the process
     engineer's decision). The replacement bundle's terminal-temperature U.A (1 325.7 kW/K) and V1's bundle's
     (1 160.5 kW/K) agree per square metre of surface within 0.65 %, so decision 154's bound on the design duty
     times the two U.A's ratio, 1.142, stands as built; Stamicarbon's equipment data sheet A4-93540 would confirm
     it and is no longer a gap. No relation changes (As-Built §CIII.4).
176. **B-120 option (b) taken: V1's stripper slip gain measured against Book2's bands** (2026-11-06, session 91,
     the process engineer's decision, 70-80 % load kept in scope). The gain (`unit_322e001.SLIP_GAIN`, V1's 4.0)
     was run against 0 with the same trims at 70, 92.3, 100 and 111 % before any change. It drives B-120's mode
     (gain 0 removes it at 92.3 % on S2's prototype and at 111 %); the 100 % arm did not reach B-120's 168 C trigger
     (TT-322004 169.4 C), where session 78 found gain 0 steady; on the committed engine at
     92.3 % runs the reactor 12 K colder (TT-322005 171.1 against 183.5 C); both gains trip 22.1 on the ramp to
     70 %. No relation changes: the gain stays at V1's 4.0 until the process engineer chooses among handoff B-120's
     options (As-Built §CIII.7).
177. **B-120 decided (b2): V1's stripper slip gain set to 0 only with B-118's turndown change** (2026-11-07,
     session 91, the process engineer's decision on decision 176's measurements). `unit_322e001.SLIP_GAIN` stays at
     V1's 4.0 in the committed tree; when B-118's stripper and reactor turndown change is decided it is built in the
     same change with the gain at 0, both sides measured. B-120 is closed and carried by B-118. No relation changes
     (As-Built §CIII.9).
178. **The nine conventional Neldiscs on Valmet's L-series Cv rows through their sheets' printed points**
     (2026-11-07, session 91, the process engineer's decision on As-Built §CIII.9's proposal, data gap 7). PV-329203,
     FV-329401, PV-329202, FV-329409, HV-323605, PV-323203, PV-323202A / B and TV-328002 keep every printed point and
     their rated capacity (PV-323203 its FpCv 634.57 on the DN 125 row's Cv 840 curve) and take the shape between the
     points, and from the last to wide open, from Valmet's online Cv table for their sheets' series codes
     (L1_LANSI150, L1_LANSI300; `control_valves_metso.L_SERIES_CV`, `_l_series`), as decision 170 put the five
     balanced valves on theirs. The rows reproduce the printed points within 1.5 %. Design strokes move by 0 to +0.54
     stroke-% (HV-323605 64.08 to 64.62); away from the design the valves pass up to 0.11 of rated less than the chord
     (FV-329401, PV-329202 at 70 %). Supersedes decisions 108 and 153's chord for these valves. Data gap 7 closed;
     both sides pinned (As-Built §CIII.10).
179. **The dynamic audit applies decision 163 on 323F010** (2026-11-07, session 91, the process engineer's answer).
     Under decision 178 the fast shutdown with LV-322501 wide open parks PT-323204 on a thermo memo pressure-bin edge
     (0.50585 bar a) and it alternates there three times by 0.00015-0.0003 mbar, decision 163's chatter. On 323F010
     only, the audit counts a reversal above decision 163's accepted 0.012 mbar, and a third successive reversal at
     the general 1e-7 bar floor must stay below it; every other node keeps the 1e-7 bar floor and the limit of two. No
     relation changes (As-Built §CIII.11).
180. **Session 93's options decided: B-118 narrowed to 322R001's heat balance, 322F001 held as built**
     (2026-11-08, the process engineer's decisions on As-Built Part CV). (1) 322F001 stays as built; the lift-friction
     prototype, p_disch,eff = p_disch - 2.41 (1 - r^2) on the motive ratio to the seed, is held in B-118's workspace
     with decision 177's slip gain 0 and built with them once 322R001's turndown heat balance is resolved. (2) B-118
     takes (b), narrowed to 322R001's heat balance and 322E002's gas and thermal hand-off into 322R001 on the ramp;
     the 5 November 2026 holds at 68.9, 74.4 and 90.5 % join Book2's 69.3 % and 92.3 % bands as acceptance tests.
     (3) 322E003 keeps its 1750 MTPD PFD anchor (decision 159's class). (4) Data gap 3: the synthesized ejector maps
     kept, the plant's break-off bracket recorded (HIC-329605 55-64 % at PT-329207 4.2 bar g), 324E002/E005's cold
     ends for 5 Nov 13:00-13:30 added to the DCS readback checklist. (5) Decision 178 kept; data gaps 2, 4, 5, 8, 9 and
     10 stay on the checklist, TV-323013B's flow and differential added. No relation changes (As-Built §CV.9).
181. **Session 94's options decided: (a), and B-118 unbundled from S2 and slip gain 0** (2026-11-09, the process
     engineer's decision on As-Built Part CVI). `ureasim/` stays as built. The S2 stripper terms and decision 177's
     slip gain 0 leave B-118's workspace (decisions 177 and 180 revised): they starve 322R001's carbamate source at
     turndown. B-118's candidate bundle is P1 (322E002's UA on the load to the power 0.77), P4 (the wall loss on a
     stagnant reactor only) and decision 180's 322F001 lift on the as-built stripper (slip gain 4.0), verified next
     in scratch on the five holds with the seed stationary and the handles moved as departures from the engine's
     design seed, then wired as option (b) once measured. No relation changes (As-Built §CVI.8).
182. **`data`'s place in the layering, enforced by a test** (2026-11-11, the process engineer's decision table of
     the session 98 plan, A-31 (a)). `ureasim/data` sits beside the ranking between `control` and `units`: it may
     import `thermo`, `core` and `control`; `thermo`, `core` and `control` read nothing from it but `thermo/empirical.py`'s
     read of the leaf `data/design_point.py`. Stated in `CLAUDE.md` §1 rule 2; `tests/test_layering.py` enforces it with
     rule 3's PyQt6 check. No import moved (As-Built §CX.2).
183. **The console's gauge conversion is §4a's one decided exception** (2026-11-11, the same table, A-32 (a)). A
     faceplate shows a pressure in bar g and sends its set point in bar a on `core.units_of_measure`'s atmosphere, the
     engine's own; `hmi` may import `net`, `data` and that module of `core`. `CLAUDE.md` §4a rule 1 and
     `docs/architecture.md` §3.2 say so (As-Built §CX.5).
184. **`bracketed_root`'s exhaustions counted in the engine's health** (2026-11-11, the same table, A-37 (a)).
     `core.numeric.ROOT_LEDGER` counts a solve that runs out of iterations with its bracket open; the session publishes
     the count as `_health.roots_exhausted`. The root returned is unchanged to the bit (As-Built §CX.3).
185. **322E002 charges the heat of a net CO2 release** (2026-11-11, the process engineer's decision table of the
     session 98 plan, B-129 (b)). The CO2 absorbed may go negative; where it does, the outlet is held at the shell's
     temperature. `release_heat` on `carbamate_condenser_322e002` and `CondenserHoldup`, False is V1's clamp at zero.
     The seed is unchanged on every leaf (As-Built §CX.7).
186. **`ProcessLoop` reseeds its PV history on the first good sample after a bad one** (2026-11-11, the same table,
     B-130 (b)). `ProcessLoop.reseed_after_bad`, False is V1's step of Kc times the PV's move through the outage
     (As-Built §CX.7).
187. **A non-finite PV is a live initiator of 22.2 and 22.1** (2026-11-11, the same table, B-131 (b)).
     `nan_is_live` on `BandedInterlock` and `HystereticInterlock`, False is V1's comparison (As-Built §CX.7).
188. **Bundle A runs with the 322F001 lift on the live motive, its seed not bit-identical** (2026-11-11, the
     process engineer, session 101). The lift departs from the plain seed at tick 3 (CVII.1's drift; 743
     physical leaves and 11 console strings over 18 000 ticks); kept for comparability with sessions 95 and 99,
     the criterion "every leaf identical" waived for it (As-Built §CXII.3).
189. **Trip 22.2 removed: no plant document draws a trip on the synthesis loop's pressure** (2026-11-12, the
     process engineer's instruction I-1 of session 105, after its recheck). The recheck (As-Built §CXV.1;
     D:\Work\reports\Trip_22_2_recheck_s105) read the plant's as-built Trip and Interlock Schedule (UAN
     01-3042-602 Rev. 03: unit 322 holds trips 22.1 and 22.5 only), AC4's application software, the Safeguards SG1
     and SG2, the ESD specification, the loop summaries of units 320, 322 and 329, the functional diagrams of 322 and
     329, P&ID 102, Operating Manual III and the archive's index: no interlock 22.2 and no synthesis high-high
     pressure trip under any number; SV32251 / SV32252 are the loop's limit. The trip, its set points and label,
     its latch, its actions on 320K002's demand, XV-322902 and the HP ammonia pumps, its refusals, its packet key,
     `trip_reset` (no other latch used it) and `BandedInterlock` are removed; a save holding its record loads, the
     record dropped (`data.retired_state`), and the six shipped exercises lose it. Supersedes decision 174,
     decision 83 as far as it names 22.2 (its class stands for 21.2's flag, B-88), 22.2's half of decision 187 and
     decided-class line 115. A decided divergence: V1's 22.2 (155.0 / 148.0 bar a) is the transcription's switch
     D-189 (As-Built §CXV.2).
190. **The load-reduction procedure is the turndown's acceptance** (2026-11-12, the process engineer's instruction
     I-2 of session 105). The thirteen steps L1-L13 (As-Built §CXV.3) are judged on (a) the handle on the console as
     on the DCS, (b) its direction alone at the seed and at a reduced load, (c) the consequence of leaving it out, (d)
     its settled departure against the plant's, (e) decision 180's five holds passed with TT-322010 inside 168-173 C
     (168.82-173.82 C on the engine's 170.0 C seed), the levels the procedure names in their bands and the licensor's
     windows met, and (f) every AUTO and CAS loop in mode, its PV near its set point and its output off its bounds.
     Decision 180's holds stand; the procedure adds (a)-(d) and (f) to them. Measured: As-Built §CXV.14.
191. **B-126 (b) taken as option (c), in scratch** (2026-11-12, session 105's plan, D1). 322R001's twelve-compartment
     species holdup (session 103's `proto103.py`) is measured against bundle A in scratch only; nothing is built.
192. **L4 holds the engine's seed ratio** (2026-11-12, D2). The procedure's N/C 2.0 is held as FFIC-321404's seed,
     2.0231315 on the engine for the plant's 2.086; the offset stays B-128's, open.
193. **A save keeps loading when state is removed** (2026-11-12, D3). A removed record is named in
     `data.retired_state` and dropped on load, every other shape difference still refused; the shipped exercises are
     cut at the byte level (decision 189).
194. **L5 and L10 are reported as found, with no handle built** (2026-11-12, D4). L5 has no handle by decision 73: the
     CO2 feed's oxygen is a fixed composition. L10's FT-322402 is an indicator on stream 755 with no valve (decision
     81); the gap is handoff B-133.
195. **Session 105 builds only the removal of trip 22.2** (2026-11-12, D5). Every other experiment of the session is
     a monkeypatch in scratch.
196. **A relief-valve lift fails a hold** (2026-11-12, D6, worded as the process engineer's R2 of the closing review).
     Under decision 180's test a hold in which SV32251, SV32252 or SV32064 lifts fails, whatever the other criteria
     read. SV32064, the CO2 line's relief, is the one that lifts first on the engine (As-Built §CXV.12, handoff B-135).
220. **322-1's CO2 FEED panel is restored** (2026-11-13, the process engineer's instruction I-1 of session 110, with
     defaults D1-D3). V1's own hand station (`frontend/co2_compressor.js`) returns to page 322-1 as a step panel
     captioned CO2 FEED, at V1's centre (104, 378.5), 196 x 53. DOWN and UP each send `co2_step`, which steps
     320K002's demand by 2 % of the 54.618 t/h design on V1's own arithmetic: the per cent to 0.1 and the demand to
     1 kg/h, each rounded half up, clamped to 0-120 %. The panel shows `CO2_FEED.demand_pct`, a leaf the port adds
     (PORT_LEAVES). The instructor keeps `co2_set`, and trip 21.2's flag refuses both. The machine stays a boundary
     (decision 73). CLAUDE.md §0 and §4a rule 2 and decided-class line 55 name the exception (As-Built §CXX.2).
221. **Page 328-2 takes its revised slide** (2026-11-13, instruction I-2, default D4). FT-322402's label leads right
     to the ammonia-water line; the old tick is gone. `tools/restore_slide_regions.py` copies only the revised
     regions of the slide's render into the background, clipped at every overlay's geometry (As-Built §CXX.1).
222. **Every pump icon with a run state opens START/STOP** (2026-11-13, instruction I-4, first part, default D8).
     The faceplate sends the command its tag takes (`data.faceplates.PUMP_COMMANDS`): `pump_toggle` for 321P002A/B
     and 329P006A/B, `aux_pump_toggle` (V1's handler, which V1's front end never sent) for 322P002A/B, 323P001A/B
     and 328P003A/B. The packet's new PUMPS block publishes 323P001A/B's and 328P003A/B's run state. The eight
     pairs with no run state are surveyed for the process engineer before any is built (As-Built §CXX.3).
223. **V1's tree is read from its copy on D:** (2026-11-13, the process engineer's instruction of session 110,
     "copy all required files from E: so it will not be required anymore"). Decision 165's tree, everything but
     its `References` (Urea Simulation Docs holds them), is copied to `D:\Work\Urea Simulation V1`: `backend\main.py`
     920 232 bytes of 2026-09-18, byte-identical. `tests/equivalence/v1_loader.py`, the Phase 7 drivers, the CO2
     compressor test, `tools/convert_overlays.py` and `tools/analyse_step_sim.py` read it there. No relation changes.
224. **The 335 melt header is computed on AC4 PC35.2** (2026-11-14, the process engineer's instruction I-3 and
     the session 111 prompt's D1-D3; handoff B-137). PIC-335201's 3.5 bar g boundary constant and V1's exclusive
     route selector are retired on the plant. `units/finishing/melt_header.py` solves the header from the twelve
     header valves (the operator's GRANULATION HEADERS panel on 324-1b), LV-324501A on 335P001's curve, LV-324501B
     and HV-335602, in ratio form, every factor 1.0 at the seed. LIC-324501's output X sets LV-324501B (2 (X - 50)
     on 50-100 %) and PIC-335201's cascade set point E1 = 2.8 + min(X / 50, 1) bar g (UD-MR-G00-FF-0004 pp. 249-252);
     PIC-335201 (reverse acting, Kc 16.25 %/bar on K 0.65, Ti 40 s, DZ 0 under decision 93) strokes LV-324501A and
     is read inside the header solve, committed once at the root. LIC-324501 runs the tuning table's K 0.85 and
     Ti 200 s. The seed: X 35.0 %, LV-324501A 75.35 %, 3.5 bar g, every other leaf as before. V1's selector stays
     as the harness's side (`SecondEvaporator(ac4_header=False)`); the decided-equivalence tests assert both.
     Trips 35.1 and 35.4 and 335P001's L2 stop on LY-324501 are not built (no L2 value in either archive; D4).
     As-Built §CXXI.1-4.
225. **HV-335602 drains the melt header to 335D004, a boundary outflow** (2026-11-14, session 111 prompt D5).
     HIC-335602, a hand station on 324-1b, strokes it (3 s open, 25 s close); its flow (Flowserve Pos. 150, Kvs 25,
     equal percentage 50:1) leaves the plant on its own packet leaf, `drain_335D004_th`, counted in the selector's
     mass closure and added neither to the product nor to 323D002. As-Built §CXXI.2.
226. **A save made before the header was computed loads on it** (2026-11-14). `data/retired_state.py` gains
     `RETIRED_BOUNDARY` (PIC-335201.barg), `ADDED_OPERATOR` and `ADDED_ATTRIBUTES`: on load each added entry and
     attribute is filled from a fresh plant at the same path, and the retired boundary pressure goes to
     `engine.plant.evaporation.adopt_boundary_header`. The save's load is its drain on V1's selector over PFD 402;
     the header valves online are the number whose header passing that drain stands nearest 3.5 bar g without
     rising above E1's 3.8 bar g ceiling; LV-324501A keeps the save's stroke and LIC-324501's X becomes the one whose
     E1 is that header. The six shipped exercises load on 9, 9, 10, 10, 11 and 11 valves. As-Built §CXXI.5.
     LV-324501A's stroke on restore: decision 238.
227. **Each pump pair the console opens holds a run state** (2026-11-14, the process engineer's instruction I-4; handoff
     A-41). `data/operator_commands.RUN_STATE_PAIRS` lists the pairs whose flow follows their run state: 322P002, as
     V1 holds it, and the pairs session 111 builds. Each machine is seeded as V1 seeds its own pairs (A running, B
     standby, AUTO); the engine holds the pair's flag, True while either machine runs, and the pair's unit multiplies
     the flow its machines deliver by it, exactly 1.0 at the seed. Each icon binds `PUMPS.<tag>` and opens the
     START / STOP faceplate. A save made before a pair existed is filled from a fresh plant (decision 226's
     mechanism). No interlock stop is built on a limit no archive gives (the L2 levels of LT-328501, LT-328503,
     LT-328505 and LY-324501). As-Built §CXXI.8.
236. **LV-324501A follows PIC-335201's output on a 1 s positioner lag inside the header solve** (2026-11-15, the
     process engineer's choice (c) on handoff A-51, closed). `units/finishing/melt_header.py`: on each trial header
     the valve stands at h = h_prev + (dt / tau)(u(P) - h_prev), u PIC-335201's trial step, and both are committed at
     the root; tau = 0 is decision 224's header to the bit (7 400 ticks over valve steps, LV-324501B open, HV-335602
     travelling, the pumps stopped, the heel cap and MAN: none differs). tau is `data/unit_335.LV_324501A_TAU_S`, 1 s,
     a stand-in (data gap 12): no document gives the positioner's response. The seal's blow-through rides the
     position; `MeltHeaderResult.lv_a_pct` stays PIC-335201's output and `lv_a_position_pct` is the valve's. A save
     made before the position existed stands the valve on the save's PIC-335201 output (decision 226's mechanism,
     `engine.plant.evaporation.adopt_header_position`). As-Built §CXXVI.1, §CXXVI.3, §CXXVI.4. The restored stroke:
     decision 238.
237. **LV-324501A's inlet stands at its sheet's 6.9 bar a at design** (2026-11-15, the same choice). `data/unit_335`:
     the valve's differential on the 3.5 bar g header is 6.9 - (3.5 + p_atm) = 2.387 bar (3.2 before: the sheet's
     sizing case moved onto the header, an inlet of 7.71 bar a); kappa 0.152 (0.113); the header's design stroke, where
     the trim passes the design drain across that differential, 79.09 % (75.35), the same trim, so
     `unit_324.LV_324501A_OP_DES_PCT` and `LV_324501_DP_DES_BAR` stay for V1's side and the seal; the dead head
     6.25 bar g (7.06). With decision 236 a header valve's step lands within 0.004 of the plant's dip ratio and 0.4 % of
     PIC-335201's kick on 5 November 2026 at 13:30, and the stroke within 1.5 % at four trend windows (2.4 to 4.3 % low
     before). As-Built §CXXIII.9, §CXXVI.2.
238. **A restored exercise opens LV-324501A at the stroke that passes its drain** (2026-11-15, the process engineer's
     choice (b) on handoff A-56, closed). It replaces decision 226's "LV-324501A keeps the save's stroke" and decision
     236's "stands the valve on the save's PIC-335201 output". `units/finishing/melt_header.passing_stroke_pct`
     inverts the forward law (round trip within 2e-14 %). A save made before decision 224: PIC-335201's output and the
     position stand at the stroke that passes the save's load at the adopted header. A save made on decision 224's
     header: at the stroke that passes what the header valves online and HV-335602 took at the saved header (the save
     holds no drain; their laws are unchanged), except with PIC-335201 in MAN or both 335P001 pumps stopped, where the
     valve stands on the save's output. A save holding the position is untouched. The six shipped exercises open on
     their adopted header within 1e-10 bar (0.10 to 0.45 bar dips before). As-Built §CXXVI.7.
210. **V1's reference sources ship in the tree** (2026-11-15, the process engineer's instruction on handoff A-33,
     closed: "copy all required data from V1 so V1.1 will become independent from V1"). It is neither of A-33's
     options: not golden vectors, but V1's own bytes. An audit hook over the whole suite (15 groups, 8 180 tests)
     recorded every file it read from `D:\Work\Urea Simulation V1`: 33 backend files (31 modules, the boot-pin
     cache and the VLE-grid cache) and 4 front-end scripts; the Phase 7 driver's whole import of V1's `main.py`, in a
     process of its own, adds V1's root module `pressure_drop.py`: 38 files, 1.76 MB. They are copied byte for byte into
     `tests/equivalence/v1_reference` with a SHA-256 manifest, the folder `-text` in `.gitattributes` (20 of the
     files are CRLF, and V1's caches key on the exact bytes); `v1_loader.V1_ROOT`, `phase7.drivers`, the CO2
     compressor test and the two tools read the copy. `test_v1_reference` fails, never skips, on a missing or
     changed file, and no executable string outside the copy names the external tree. `Claude.md` §0, §4, §5.4 and
     §6 amended. As-Built §CXXVII.1.
211. **The trend window has a CLEAR button** (2026-11-15, the process engineer's request). V1's `trend.js` has none.
     CLEAR takes every pen off the plot and the table and keeps the span and the rulers; the cleared view is kept,
     and with no pen the window asks the historian nothing, so an answer still due is dropped. A console view
     action only: no command, no engine change. As-Built §CXXVII.2.

212. **322P002's delivery to 322C001 is set by hand in the field** (2026-11-15, the process engineer's choice on
     handoff B-133, closed). Uhde's Operating Manual III sets the flow at FI-322402 by hand (pp. 1-58, 4-8, 4-14,
     4-19) and P&ID 102 draws no control valve, so L10's move is a field operator's. The instructor's panel gains
     a Field group: `p002_delivery_set` takes the delivery in FI-322402's m3/h on FT-322402's 1005 kg/m3, from
     none to the design delivery, and the operator entry `322P002-DELIVERY` holds it in kg/h, seeded at the PFD's
     744 to the bit; 322P002 delivers it while either machine runs, the heel cap unchanged. The hand valve's Cv
     and the line's resistance are on no sheet, so the delivery is set, not a stroke; a delivery above design
     waits on 322P002's maximum read from KSB's sheet (data gap 13). A decided divergence: V1 delivers PFD 744 always. Saves
     made before it fill the entry from the seed (`ADDED_OPERATOR`). As-Built §CXXVIII.7.
213. **B-145 is closed as built** (2026-11-15, the process engineer's choice). LV-324501B's 2 % floor is the 50:1
     rangeability its Flowserve sheet prints (Pos. 149), so the floor read from the sheet is the floor built.
     B-145's acceptance, no relay on any header and load, is accepted as unmet: the relay at the seat on a small
     excess at a fixed feed stays, and the engine's saves avoid it (decision 226). PIC-335201 keeps decision 93's
     deadzone 0. As-Built §CXXVIII.3.
214. **Decision 33's class reaches the seven levels on V1's holdup ratio unit by unit** (2026-11-15, the process
     engineer's direction on handoff B-156). LT-323501, LT-323502, LT-323503, LT-328503, LT-328504, LT-328505 and
     LT-329501 each move to read between the nozzles Uhde's data sheet prints, on their vessel's datasheet
     geometry with the design level reproduced, one unit a session, each measured on both sides before it is
     built; B-156 stays open as the work list. As-Built §CXXVIII.5.
215. **328P007A / B's run state keeps stopping LV-328505's letdown** (2026-11-15, the process engineer's choice on
     handoff A-41 (2), closed as built). P&ID 104, the PFD (739 to 741 all at 3.9 bar a) and the pumps' data sheet
     (KSB CPK 50-160, 25 m3/h, "to the granulation unit") draw stream 740 to LV-328505 past the pumps' suction
     manifold, so on the drawings the pair moves no modelled stream; decision 227's wiring, after `Mapping of Desorber
     Hydrolyzer unit.md`, stops LV-328505's flow with both machines, and it stays. As-Built §CXXIX.2.
216. **A-40's test is restated on decision 186** (2026-11-15, the process engineer's choice; handoff A-40 closed). The
     bad-sample test asserts the loop frozen on the bad tick, its integral alone on the first good sample, to the bit,
     and afterwards the clean loop's moves offset by the proportional step not taken, 1.0 % of stroke; V1's step on
     recovery stays asserted in `tests/control/test_process_loop.py`. A test change only. As-Built §CXXIX.3.
217. **AC4's low-level stops of 328P002, 328P006, 328P007 and 335P001 are built on a 5 % stand-in** (2026-11-15, the
     process engineer's choice on handoff A-41 (1), closed). Each pair's motor-control interlock IC2
     (UD-MR-G00-FF-0004, As-Built §CXIX.2) stops both machines while LT-328501, LT-328503, LT-328505 or LY-324501
     stands below its L2. Neither archive gives the L2 values, so every limit is LT-323503's read-back 5 % (decision
     103), with decision 111's 2-unit hysteresis, held in `data/low_level_stops.py` and logged in data gap 8 until
     the readback. Built as 323P008's stop (B-93): in the unit that holds the level and the flow
     (`control.interlocks.low_level_stop`), no latch (decision 39), ``l2_stop = False`` V1's. The seed is unchanged to
     the bit. A save carries the switch, never the limit, which the unit reads from the data module on every tick;
     a save made before it fills the new state (`ADDED_ATTRIBUTES`). A decided divergence: V1 has no such stop.
     As-Built §CXXIX.1.
218. **Every file the simulator uses lives in its folder; the non-essential ones in `Tests and Reports`** (2026-11-15,
     the process engineer's instruction, session 120). The suite moves to `Tests and Reports/tests` (the package
     `tests` kept; `pytest.ini` names the path and puts the folder and `Tests and Reports` on the import path),
     `D:\Work\reports` to `Tests and Reports/reports`, scratch to `Tests and Reports/scratch/session-NNN`; reports
     and scratch are ignored by git. The instructor's saved exercises default to the folder's `exercises`, ignored by
     git, in place of `~/ureasim-exercises` (amends decision 171; `UREASIM_EXERCISES` still overrides it).
     `CLAUDE.md` §6 holds the table of sub-folders. As-Built §CXXX.1.
228. **Trips 35.1, 35.3 and 35.4 are built as AC4 PC35 draws them** (2026-11-15, the process engineer's choice on
     handoff B-146: D2, D3, D5 and D6 of session 115's Track B). `control/granulation_trips.py`, a step at the
     tick's end (`335-TRIPS`, after SYN-TRIPS): TRIP_35_1_FLAG1 while either 335P001 runs; TRIP_35_4_FLAG1 while
     35.1 holds, both 335P002 are not stopped for ten minutes (PC35.5.2's TD "10:0", read as an on-delay, data gap
     5) and LV-324501A is off its closed limit (LVSL-324501A at 0 % of stroke, a stand-in, data gap 14); 335P002's
     IC2, trip 35.3, on both flags. Each flag is a live AND with no latch (decision 39's class). The actions are the
     de-energised solenoids — LV-324501A shut, LV-324501B and HV-335602 open — and the controllers' CLAMP:
     LIC-324501 at 100 % on 35.1 (UD-MR-324-FF-0002), PIC-335201 at 0 % on either flag (a stand-in, data gap 5).
     Four overrides on 324-1b, HS-335201A, HS-335201B, HS-335602 and HS-335620, released at the seed
     (`data.operator_commands.TRIP_35_HAND_SWITCHES`). Held healthy and named in the module: PSLL-335202,
     HS-335621, 335K001 and trips 35.16 / 35.18; TIC-335015's action is not built. The seed's packet leaves are
     unchanged to the bit; eight are added. Saves migrate (`retired_state.ADDED_UNITS`, `ADDED_OPERATOR`). A
     decided divergence: V1 has none of the three. As-Built §CXXX.2, §CXXX.3.
219. **LI-323502 reads between LT-323502's taps on 323D001's 11.10 m3** (2026-11-16, the process engineer's choices on
     handoff B-156's first unit, decision 214's class). 323D001 is vertical, 2 178 mm inside, 2 350 mm between
     tangent lines (UD-AU-323-EC-0005; the as-built drawing UD-AU-323-DZ-0005-005 rev 03); LT-323502's taps stand
     220 mm inside each tangent line, 1 910 mm apart, the nozzle distance of UD-MR-G00-EC-0134 sheet 3. Symmetric
     about the shell's mid-plane, they read 50 % at half the vessel: on the datasheet's nominal 11.10 m3, choice (a)
     (the drawing's 2:1 heads give 11.46 m3; the calculation's 11.83 m3 counts the straight flanges twice), that is
     V1's design holdup, 6 759.9 kg. LI-323502 = clamp(50 + (M - M_half) / (rho A 1.910 m) x 100, 0, 100), written as
     its departure from M_half so that the design reads 50.0 to the bit; a kilogram moves it 1.56 times as far as V1's
     M / M_full. LIC-323502 keeps V1's 50 % set point and the plant DCS's tuning; the 245 mbar set range is not applied
     and no ceiling or overflow is added. ``taps = False``, V1's, is ``V1_TANK`` on the harnesses; a save made before
     it fills the switch (`ADDED_ATTRIBUTES`). The seed is identical to HEAD at tick 1 and drifts after it, because
     the seed is not a fixed point (B-94); the process engineer accepted "identical at tick 1, within 1e-5 by 600 s"
     for this unit and B-156's six after it, put to them on the packet's leaves; measured unrounded, the state and
     flows move by up to 5.7e-5 by 600 s, and the bound is decision 230. A decided divergence: V1 reads
     the holdup over the drum's. As-Built §CXXXI.
229. **Trip 21.2's pump timers run the sheet's minutes** (2026-11-16, the process engineer's choice on handoff
     A-58). AC4 PC21.5.1 prints .2 "D=5:0-2" and .4 "D=15:0-2": ``TRIP_21_2_PUMPS_TD_S`` is 300 s and
     ``TRIP_21_2_P001_TD_S`` 900 s, the trip schedule's 5 and 15 min. The on-delay is kept (the 2026-10-09 reading;
     pages 5 and 7's start-up override draws the same element and works only as one), so 21.2 is still lost at
     once and its bypasses act after their delay. The six shipped exercises carry the new timers; an older save
     keeps its own. 21.8 / 21.10's run timer stays 5 s (A-58). As-Built §CXXXII.
230. **B-156's seed bound is 6e-5 by 600 s, as measured** (2026-11-16, the process engineer's choice, session 121).
     A level moved between its taps leaves the plant's seed identical to the bit at tick 1; after it the seed's own
     drift (B-94) reads at the new law's gain. By 600 s the plant may part from V1's law by 6e-5 relative on every
     unrounded state and flow above 1 in magnitude, with the names that carry a rate of change, a residual, a
     relaxation, a lag, a controller's memory or a closure left out, and by 2e-3 on the two boil-off flows of a few
     kg/h (324E001's and 322R001's), their measured ceiling. LT-323502 measures 5.69e-5 (323F004's holdup and its 319)
     and 1.9e-3 (324E001's boil-off). Replaces the 1e-5 first accepted on the packet's rounded leaves. It holds for
     B-156's six other units; each pins it beside `tests/engine/plant/test_recirc.py`. As-Built §CXXXI.7.
231. **Each 321P002's start-up override runs the sheets' 5 min** (2026-11-16, the process engineer's choice on
     handoff A-58, closed). AC4 PC21.1.1 / .2 print T .2 "D=5:0-2" on the pump running, the trip schedule's
     "automatic start up override 5 min.": ``TRIP_21_8_RUN_TD_S`` is 300 s, so a pump started with XV-322901 shut
     keeps 21.8 / 21.10 for 5 min. The six shipped exercises carry it; an older save keeps its 5 s. As-Built
     §CXXXII.7.
232. **322E002's sawtooth below N/C 3.0 is kept as built** (2026-11-16, the process engineer's choice on handoff
     A-57, closed). On B-106's branch and A-21's solve the synthesis recycle runs a relaxation cycle of about 5 s:
     322E002's fraction falls with the N/C, what it does not condense 322R001 absorbs and 322E001 returns in its top
     gas a tick later, so the fraction runs to 0; PT-329201's jump at the bound cuts the CO2 the tie-in passes to
     322E001, its top gas leans, and condensation returns. No plant record lies below N/C 3.02, and Operating Manual
     III's sections 1 and 5, the two read, describe no such cycle. Nothing is changed; the window means stay what A-50's test asserts. A held melt on
     322E002 was measured and not taken, since it moves those means; the loop's composition holdups stay with B-126.
     As-Built Part CXXXIII.
233. **LI-323503 reads between LT-323503's taps on 323D011** (2026-11-16, the process engineer's choice, session 123;
     B-156's second unit). N2B 220 mm above the bottom tangent line and N2A 1310 mm above N2B (Uhde's datasheet
     UD-AU-323-EC-0006 p. 5; UD-MR-G00-EC-0134 p. 4), the nominal 3.15 m3 (decision 219's basis), the sheet's
     1065 kg/m3: `data.unit_323e011.lt_323503_pct`, written as the departure from V1's design holdup, which reads
     26.77 %. LIC-323503's set point and history are seeded there; a save made on V1's reading is restated as the
     tap reading of the holdup it held (`engine.plant.recirc.adopt_tap_reading`). AC4's L2 stop reads it, so
     323P008A / B stop at 763 kg, not 119 kg. ``taps=False`` is V1's on the harnesses. The seed is identical at tick
     1; decision 230's bound is restated for this unit at its measured values, 3.2e-4 (323E011's 718A) and 4.2e-3
     (324E001's boil-off) by 600 s. As-Built §CXXXIV.1-4.
234. **322P002's field-set delivery reaches FI-322402's 40 m3/h** (2026-11-16, the process engineer's choice, data
     gap 13 closed). The instructor's ``p002_delivery_set`` takes none to 40 m3/h, FI-322402's range (Uhde's loop
     summary UD-MR-322-EC-0001 p. 30), inside 322P002A / B's 6 to 60 m3/h (UD-AU-322-EC-0015 p. 6, KSB CPKC1
     50-315); the panel opens on the design delivery, PFD 744 on FT-322402's density. Replaces decision 212's
     ceiling at the design. As-Built §CXXXIV.5.
235. **FY-321404 is published and set on the DCS's formula; the loop's boundary is kept** (2026-11-16, the process
     engineer's choice on B-128 (b) and B-127 (a), both closed). The engine publishes FFIC-321404's PV, balance,
     set point and the machines' shares as its ratio times 1.0317, the DCS formula's factor at design
     (UD-MR-321-FF-0002 p. 4; As-Built §CXXX.4), and divides a ``ratio_set`` by it after the 2.0 to 5.0 limits, so
     the floor stands at 2.0 on the display, 1.9386 on the engine's basis; CAS takes the set point on the display's
     three places. The loop, its gain, the saves and the scenarios are as built. A fixed factor: exact at design,
     about 1.4 % low at 70 % load. B-127's tear and row 116 are kept: the engine's motive now displays 2.087 where
     the plant shows 2.116. As-Built §CXXXIV.6.
239. **Phase 7's cold start keeps its driver** (2026-11-16, handoff A-59 closed on option (a); session 123's call on
     the process engineer's "do the most recommended", no recommendation having been on record). The cold start
     makes no operator move on trips 35.1 and 35.4: the cycle at 335P001's restarts is PC35's with no operator. As-Built
     §CXXXIV.7.
240. **SV32064 lifting before the loop's reliefs is kept as built** (2026-11-16, handoff B-135 closed on option (a),
     session 120's recommendation). The boundary feed delivers at the line's pressure (decision 73); PIC-322203 keeps
     V1's 168.01 bar a (decision 79), and the plant's own 4.98 bar static offset puts SV32064 first there too.
     As-Built §CXXXIV.7.
241. **LI-323501 reads between LT-323501's taps on 323C003** (2026-11-16, the process engineer's choice, session 124;
     B-156's third unit). N8 1750 mm above R.L. (EL +15.703 m) and the seal on line 400-US14-323266 2000 mm below it
     (Uhde's sketch UD-AU-323-EC-0001 p. 5 and Glatt's UD-AU-323-DZ-0001-001; UD-MR-G00-EC-0134 p. 4), 1106 kg/m3,
     over the neck of 323E002's 1160 mm bore, the 15-degree cone and the 1600 mm shell (EC-0001 p. 2), 323E002's
     tubes below R.L.: `data.unit_323c003.lt_323501_pct`, written as the departure from V1's design holdup, which
     reads the plant's 40 % (Book2's LIC-323501). LIC-323501's set point and history are seeded there; a save made
     on V1's reading is restated as the tap reading of the holdup it held. LV-323501's seal is lost at N5's lower
     edge, 29.21 % (decision 138's class), not at the bottom of V1's span. ``V1_COLUMN`` and
     ``lic_323501(taps=False)`` are V1's on the harnesses. The seed is identical at tick 1 but for the column's
     reading; by 600 s its flows stay within decision 230's 6e-5 (4.86e-5), and the boil-off bound is restated for
     the unit at its measured value, 1.6e-2 (324E001's, 1.58e-2 of 1.30 kg/h). With 323C003 between its taps on
     both sides, decision 233's own boil-off part measures 4.24e-3, and its bound is restated on the same terms,
     4.3e-3 (session 124's restatement at the measured value). As-Built §CXXXV.1-4.
242. **Data gaps 2 and 8 close on their stand-ins, signed off as built** (2026-11-16, session 124's call on the process
     engineer's "Choose the recommended choice", no option having been marked). TT-322015's H2 clears 2 K below its
     110 C (V1's band); LT-323503's L2 hysteresis stays 2 % (B-96); the L2 of LT-328501, LT-328503, LT-328505 and
     LY-324501 stays LT-323503's 5 % with the same 2 % (decision 217). Nothing in the model moves. A DCS readback
     (checklist rows 1, 2 and 17 to 20) would still replace them. As-Built §CXXXV.5.
243. **LI-328503 reads between LT-328503's taps on 328C002** (2026-11-17, the process engineer's choice, session 125;
     B-156's fourth unit). N7B and N7A at EL 13 330 and 14 530 mm on Uhde's principle sketch (UD-AU-328-EC-0001 p. 6),
     300 and 1 500 mm above the flat partition at EL 13 030 mm that is 328C002's floor (the tray arrangement, p. 7);
     Uhde's level sheet UD-MR-G00-EC-0134 p. 6 prints the 1 200 mm and 923.0 kg/m3: `data.unit_328c002.lt_328503_pct`,
     written as the departure from V1's design holdup, which reads 70.83 %. V1's 1.150 m sump is the drawing's H.L.L.
     (its N.L.L. is 725 mm), kept as the design holdup. LIC-328503's set point and history are seeded there; a save made
     on V1's reading is restated as the tap reading of the holdup it held. AC4's L2 stop reads it, so 328P006A / B stop
     at 693 kg, not 159 kg. ``taps=False`` and ``lic_328503(taps=False)`` are V1's on the harnesses. The seed is
     identical at tick 1 but for the reading; by 600 s its flows part 1.96e-5 and the boil-off 6.6e-5, inside decision
     230's bound with no restatement. The process engineer also confirmed session 124's restatement of decision 233's
     boil-off bound to 4.3e-3 (decision 241). As-Built §CXXXVI.1-3.
244. **LI-328505 reads between LT-328505's taps on 328C004** (2026-11-17, the process engineer's choice, session 126;
     B-156's fifth unit). N11B and N11A at EL 210 and 1 210 mm above 328C004's bottom tangent line in the nozzle table
     of Uhde's principle sketch (UD-AU-328-EC-0001 p. 6); Uhde's level sheet UD-MR-G00-EC-0134 p. 7 prints the 1 000 mm
     and 923 kg/m3: `data.unit_328c004.lt_328505_pct`, written as the departure from V1's design holdup, which reads
     71.00 %. V1's 0.920 m sump is the drawing's H.L.L. (its N.L.L. is 510 mm, its L.L.L. 100 mm), kept as the design
     holdup; the drawing's N.L.L. (30.00 %) was measured and not taken. LIC-328505's set point and history are seeded
     at 71.00 %; a save made on V1's reading is restated as the tap reading of the holdup it held. AC4's L2 stop reads
     it, so 328P007A / B stop at 689 kg, not 144 kg. ``taps=False`` and ``lic_328505(taps=False)`` are V1's on the
     harnesses. The seed is identical at tick 1 but for the reading; by 600 s its flows part 2.36e-5 and the boil-off
     5.1e-7, inside decision 230's bound with no restatement; 323C003's boil-off part stays 1.582e-2. As-Built
     §CXXXVII.1-4.
245. **A-60 closed as built: B-104's two-tick ring is kept, its means asserted** (2026-11-17, the process engineer's
     choice of option (a), session 126). The ring is traced to LV-322501's flashing choke: in B-104's scenario
     322E001's bottoms (CO2 25-32 wt %, NH3 3 wt %, 136 C) lie on the edge of the rigorous bubble-point surface, which
     returns about 907 bar on one tick (clamped to PT-329201) and refuses the composition on the next, where
     `stripper_sump.bottoms_pv_bara` falls back to water's 3.5 bar; the drain flips 21.7 / 41.8 t/h and closes the loop
     through 322E001's one-tick read of 322R001's overflow. Not taken: the solve on the tick (b), not prototyped, whose map the two
     link-breaking arms suggest has no root across the jump, and a continuous fallback at the loop pressure (c), a new mechanism. As-Built §CXXXVII.5.
246. **LI-328504 reads between LT-328504's taps on 328C003, V1's design holdup read as the drawing's N.L.L.**
     (2026-11-17, the process engineer's instruction, session 127; B-156's sixth unit). Uhde's principle sketch
     UD-AU-328-EC-0003 p. 5 puts N5A 475 mm and N5B 1 475 mm below the top tangent line (20.375 and 19.375 m above the
     bottom one) and the N.L.L. 975 mm below it, at the span's mid-point; Uhde's level sheet UD-MR-G00-EC-0134 p. 6
     (rev. 2) prints 1 000 mm and 0-96.15 mbar on 908 kg/m3. V1's design holdup, an hour of 747, stands 12.554 m deep,
     6.8 m under N5B; it is kept, with the vapour space, the head and the thermal inertia it carries, and read as the
     N.L.L.: `data.unit_328c003.lt_328504_pct`, the departure from it over the span's 2 712 kg, 50 % at design, V1's own
     reading, so LIC-328504's seed is unchanged and a save is restated only off the design holdup. This does not place
     the liquid at the taps' elevation; the reading moves 25.1 times as far per kilogram as V1's. The bound is restated
     for the unit on its measured value (decisions 233 and 241's route): AI-328701's conductivity may part 2e-4 by
     600 s (measured 1.87e-4); every other state keeps decision 230's 6e-5 and 2e-3. The move takes 323D011's part
     (decision 233) to 4.330e-3 on 324E001's boil-off, and that bound is restated from 4.3e-3 to 4.4e-3; 323C003's
     part stays inside decision 241's 1.6e-2 (1.587e-2). ``taps=False`` is V1's on the harnesses. As-Built
     §CXXXVIII.2-4.
247. **Data gap 11 closed: 335P001's head law kept on KSB's factory test** (2026-11-17, the process engineer's choice,
     session 127). KSB's acceptance test protocols K 77746 and K 77747 (UD-AU-335-DZ-0026-012 pp. 25 and 29, ISO 9906
     class 1, cold water) give the executed impeller, 213 mm, and six points each at 2 940 1/min: shut-off 68.68 and
     68.96 m, a rise to 69.9-70.6 m at 42 m3/h, 66.91 and 66.79 m at the 82 m3/h guarantee. H = 71 - 5 (Q / 80)^2 m is
     kept: its slope at the header's 62.2 m3/h, -0.097 m per m3/h, is the test's (-0.083 to -0.094); its shut-off stands
     2.0-2.3 m above the test's, so `KAPPA` and the dead-head bracket carry about 0.28 bar more droop than the pump. A
     refit, measured and not taken, would turn `KAPPA` negative (-0.03 to -0.07). As-Built §CXXXVIII.1.
248. **LT-329501 leaves B-156 for the data-gap ledger, V1's holdup ratio kept; B-156 closes on six units** (2026-11-18,
     session 128; the recommended option, taken under the process engineer's instruction for the session to choose the
     most recommended answer). Both taps sit on line 322004, 322E003's outlet to 322F001, not on a vessel: Uhde's
     piping list UD-RL-G00-MB-0001 pp. 91-92 (PDF 94-95) runs the purged impulse lines 329256 and 329257 to 322004, and the as-built
     isometric UD-RL-100-MB-0004 rev 03 puts their branches at EL +8300, on the run to 322F001/N1, and EL +21089, beside
     322E003/N6: 12 789 mm apart, against the 10 000 mm of Uhde's sheet (EC-0133 p. 3) and loop summary
     (UD-MR-329-EC-0001 p. 77). The model carries the scrubber's lumped holdup, not the downcomer's level, and no page
     gives the span the 0-1 200 mbar covers or a design level between the taps (UD-AU-322-EC-0005 p. 27's +16.65 m
     stands in 322E003's bottom part). As LT-324501 and LT-329505 (data gaps 4 and 10), it becomes data gap 15 and keeps
     V1's holdup ratio; decision 214's other six units stand as built. Nothing under `ureasim/` moves. As-Built §CXXXIX.2.
249. **Trip 21.2's three timers are off-delays: 21.2 trips 5 min, 15 min and 5 s after its causes** (2026-11-18,
     session 130; the process engineer's "Measure then build"). ABB's AC 400 PC Elements Reference Manual
     (UD-MR-G00-DZ-0045-016 p. 447) tells TON (T at the left of I /--/ O) from TOFF (T at the right). AC4 page 20 draws
     PC21.5.1's .2 (5:0), .4 (15:0) and .16 (5) with the T at the right, as the trip schedule's "time delay 5 min." and
     "15 min." read; pages 5 and 7's start-up override stays TON; PC35's T600 is TOFF, equivalent to its build. Built:
     `control/interlocks.OffDelayTimer` for `Unit21Trips.t_pumps`, `t_p001`, `t_fy`, seeded settled, the six shipped
     exercises' three timers moved onto it; a save made before keeps its `OnDelayTimer` objects. Supersedes the
     on-delay of decision 229 for these three. As-Built §CXLI.1, §CXLII.
250. **FY-322403's L2 is the schedule's 8 500 Nm3/h** (2026-11-18, session 130; the process engineer's "Measure then
     build"). Uhde's Trip and Interlock Schedule UAN 01-3042-602 rev 03 as-built, sheet 321/1, trips 21.2 at FY-322403
     8 500 Nm3/h (pre-alarm 10 000), in `References\trip_and_interlock_schedule.md` line 71. Built:
     `data/unit_322_loop.TRIP_21_2_FY_L2_NM3H`, compared on FT-322403's own Nm3 basis, 30.0 % of the design CO2,
     replacing V1's 5 % (data gap 5's stand-in). As-Built §CXLI.2, §CXLII.
