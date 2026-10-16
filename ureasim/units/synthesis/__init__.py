"""Unit 322 and its feed — the HP synthesis loop.

CO2 arrives from 320K002 through its discharge line; ammonia arrives from unit 321 as the
322F001 ejector's motive stream. Inside the loop, carbamate forms in 322E002, urea forms in
322R001, and 322E001 strips the unconverted carbamate back out with CO2 gas. 322E003 closes
it: everything that leaves the section as gas is washed there first, and what the wash
recovers is what the ejector entrains. HV-322604 is the loop's only inert exit, letting
322E003's vent down to the LP absorber.

Package map

    co2_compressor   320K002, a boundary feed: its hardwired governor delivers the demand
    co2_line         the discharge line: a pressure node with volume, the XV-322902 check
                     valve tie-in, and the PV-322203 vent under PIC-322203
    carbamate_condenser  322E002, where synthesis starts and the plant's LP steam is
                     raised: a calibrated split with a real flash on top of it
    ejector          322F001, the HP carbamate ejector that circulates the loop
    hp_split         the anchored K-value ratio every split in this loop is moved by
    purge_valve      HV-322604, the inert-purge letdown to 322C001: choked flow on the
                     vendor's equal-percentage trim, the seat ceiling, the SRK outlet
    reactor          322R001, the urea reactor: the component balance, the vapour
                     disengagement at the top, and the analysers
    reactor_column   its axial march -- the reactions integrated up the column's own
                     liquid volume, node by node
    reactor_calibration  the two back-solves that tie that march to the plant's design
                     point, solved jointly with the temperature profile
    reactor_hydraulics   its inventory: level, the overflow funnel, HV-322605 and the
                     node energy balance's right-hand side
    scrubber         322E003, the HP scrubber: the saturated inert vent, the overflow
                     that closes the recycle, the shell-side cooling water and the sump
    stripper         322E001, the falling-film CO2 stripper
    stripper_sump    322E001's bottom head: LT-322501, LIC-322501 and the LV-322501
                     letdown to LP recirculation

The loop is cyclic by construction — 322F001 -> 322E002 -> 322R001 -> 322E003 -> 322F001 —
so it cannot be evaluated in an order until the recycle is torn. The tears are declared to
`ureasim.core.flowsheet`, which refuses a cycle that has none rather than picking an order.
"""
