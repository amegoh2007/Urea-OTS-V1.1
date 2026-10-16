"""Unit 324 (screens 324-1 / 324-1B) — the two-stage vacuum evaporation.

323D002's urea solution is concentrated to the melt the finishing section takes, in two
evaporator stages under vacuum; their vapour is condensed under the same vacuums, and steam
ejectors pull the inert gas the condensers leave.

Package map

    vacuum_condenser
                        324E002, 324E005, 324E006, 324E007: the saturated-vent surface
                        condenser — the cold end where the H0 heat balance meets UA . LMTD,
                        the vent saturated over the condensate, anchored on the PFD rows
    condenser_node      the same condensers as flowsheet nodes: the live inlet (the PFD row
                        scaled, the false air, a blow-through part), the vent capped at the
                        inlet, the condensate as the rest
    ejector_gas_dynamics
                        the 1-D compressible flow of a steam-jet ejector (Huang 1999, V1's
                        ejector_huang.py): choked nozzles, the jet's expansion, the shock
    ejector_map         324F002, 324F004, 324F005: each ejector's performance map synthesized
                        on its throats, its capacity anchored on the PFD's design load (the
                        vendor's duty kept as margin), tabulated on suction and motive pressure
                        and interpolated, with the break
    holdup_boil         a separator's held melt boiling past its own boiling point at the
                        vacuum, the excess sensible heat paid as latent heat (and 323F010's
                        liquor past its bubble point, for unit 323)
    first_evaporator    324E001 / 324F001, stage 1: the TIC -> PIC chest cascade, the boil-off
                        to the melt's equilibrium strength and the holdup's own, T and P solved
                        together against 324E002's vent and 324F002's pull, the barometric leg,
                        the species, LIC-329505's condensate trap
    second_evaporator   324E003 / 324F003, stage 2: the same on the 9-bar chest, 324E005's vent
                        and 324F004's pull; LIC-324501 and the LV-324501A / B selector
    vacuum_train        the four condensers in series with the three ejectors as mixing nodes:
                        the stages' overheads in, the condensates to 328D003, 708 to 323C005,
                        722 to atmosphere; HV-329605 / HV-329606 on their vendor trims; as the
                        plant runs it, 324E006's shell a vacuum node between 324F004 and
                        324F005, and the cold ends the vacuums read lagged on their tubes' water
"""
