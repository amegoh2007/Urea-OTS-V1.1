"""Unit 322 (screen 328-2) — the LP absorber, the plant's last ammonia barrier before atmosphere.

The HP loop's inert purge, let down through HV-322604, is washed of its ammonia and carbon
dioxide in two packed beds before its inerts are vented, and the liquor it makes goes on to the
atmospheric absorber.

Package map

    packed_beds
                        322C001's two packed beds: Onda transfer units on Colburn's
                        counter-current balance against the washes' speciated back-pressure,
                        the upper bed's heat of absorption, the vent saturated with water, and
                        the design calibration on the PFD's 204 -> 797 split
    feed_cooler
                        322E006, the plate cooler between 322P002 and the lower bed: 744 cooled
                        against cooling water into 755, counter-current on its datasheet UA
    vent_line
                        PV-322201 to atmosphere: the beds' top, XV-322915's LP steam flood
                        and TI-322015, trip 22.1's process value
    lp_absorber
                        322C001: 204 from HV-322604 (its gas to the beds, its condensed liquor
                        to the sump), 755 from 322E006 and 954 on FT-322404 in; 797 vented
                        through PV-322201 on PIC-322201, 756 drawn to 323C005 through LV-322502
                        on LIC-322502; its pressure, temperature, holdup and species, SV32253,
                        the heel and the full column
"""
