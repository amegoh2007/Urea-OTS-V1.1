"""Unit 323 — LP recirculation and pre-evaporation.

The stripper bottoms come down from 144 bar in three steps, giving up their ammonia and CO2 as
gas for the LP carbamate condenser and concentrating from 56 to 80 wt% urea for unit 324. Every
stage holds the same six-species liquor, integrated through `ureasim.units.liquor_stage`.

Package map

    liquor_line         the lines between the stages: each liquor's cp, and a drain's arrival
                        at the next stage through its inlet line
    rectifying_column   323C003 and its 323E002 steam heater, stage 1: the two-source column
                        pressure, the energy-limited boil-up, the LV-323501 drain
    flash_tank          323F004, stage 2: the adiabatic flash to PFD 701, the drum pressure
                        taken from the 323E011 node, the LV-323505 drain
    pre_evaporator      323E010 and 323F010, stage 3: the steam-heated evaporation under
                        vacuum, the PT-323204 vapour space on HV-323605, the barometric leg
    solution_tank       323D002, stage 4: the two-compartment atmospheric buffer, the baffle
                        spill, the tie-in spool, the LIC-323507 -> FIC-324401 draw to unit 324
    flash_condenser     323E011 and 323D011: the 1.13 bar a flash gas node under PIC-323203,
                        which 323F004 rides; the level tank and the 718A / 718B draw
    lp_carbamate_condenser
                        323E003, 323D001 and 323P001: the 3.2 bar a node the column rides,
                        held by the dew point against the tempered water under PIC-323202 and
                        TIC-323013; the LIC-323502 -> SIC-323901 draw to the HP synthesis
"""
