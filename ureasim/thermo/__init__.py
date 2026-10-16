"""Thermodynamic property and phase-equilibrium packages.

This package knows about *chemistry*, never about the plant. Nothing here may import from
`ureasim.core`, `ureasim.units`, `ureasim.control`, `ureasim.engine` or `ureasim.hmi`.

Package map (see the As-Built Mathematical Reference, Part I, for the selection rationale):

    iapws              IAPWS-IF97 R7-97 pure water and steam
    properties         NH3-CO2-H2O Extended UNIQUAC basis, speciation, SRK, Henry
    enthalpy           H0 absolute enthalpy on the elements-at-298.15 K datum
    extended_uniquac   neutral H2O/urea binary UNIQUAC (Voskov & Voronin)
    urea_melt          the evaporator melt's anchored equilibrium strength, its soft sensor
                       (PY-324201 / AY-324701) and its validity diagnostics
    vle                liquor bubble points and apparent K-values
    kvalues            apparent K-values, the anchored K ratio, bubble and dew points
    splits             how a calibrated phase split is allowed to move off design
    real_gas           SRK isenthalpic letdown
    condensing_letdown a gas letdown that condenses an ammonium-carbamate liquor below its dew
                       point (HV-322604, handoff B-19)
    ammonia_backpressure
                       NH3 and CO2 back-pressure, water activity and heats of absorption over
                       an ammonia water (322C001's beds)
    transport_properties
                       the viscosities, surface tension and diffusivities the beds need
    urea_liquor        the six-species urea liquor: bubble point, vapour by relative
                       volatility, and a stage's design back-solve off its PFD rows
    ammonia_water      the desorption train's liquor: vapour rows in mole %, the N-feed design
                       back-solve, Kremser's volatility, the liquor's vapour pressure at a valve
    service            unified flash service with explicit domain refusal
    empirical          anchored empirical fallbacks for the 10 Hz inner loop
"""
