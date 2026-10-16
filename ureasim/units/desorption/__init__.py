"""Units 323-2 / 328 — the LP vent scrub, ammonia water collection, desorption and hydrolysis.

What the LP section cannot condense reaches atmospheric pressure here and is scrubbed, and the
ammonia water the plant collects is stripped of its NH3 and CO2 and hydrolysed, so the process
condensate can leave clean and the recovered gas can return to the LP carbamate condenser.

Package map

    atmospheric_absorber
                        323C005: the lean-solvent scrub of PFD 702 and 708 at 1.0 bar a, the
                        saturated vent 341 to 328V001's stack, the freely draining sump and its
                        343 bottoms to 328D003
    ammonia_water_tank
                        328D003: three communicating bays levelled as one pool, the vacuum
                        train's condensates and 343 in, 744 to 322P002 and 735 / 734 / 791 / 793
                        to 328P003 out, the four flow loops on those draws, the tank's heel and
                        its overflow; 741 back from 328C004 into compartment II
    feed_effluent_interchanger
                        328E007: the desorbers' feed 735 preheated to 738 on 328C004's bottoms
                        739, cooled to 740 — V1's anchored effectiveness and energy-balance form
    desorber_stage
                        the species layer the three unit-328 columns share: the live Kremser
                        volatility and the implicit species step
    first_desorber
                        328C002: desorber I — 738, 775 and the hot overheads 748 and 750 in, 737
                        overhead and 743 through 328P006 and LV-328503 out; its boil-up,
                        pressure, bubble point, holdup and species, LIC-328503, the heel and
                        the full shell; the liquid loses what boils
    hydrolyser
                        328C003 and 328E021: the urea hydrolysis at 200 C and 16.8 bar a, 746 in
                        through 328E021's cold side and MP steam 911 on FIC-329402, 748 overhead
                        through PV-328203 and 747 through LV-328504 and 328E021's hot side to
                        328C004; its conversion, pressure, heat balance, holdup and species,
                        the four loops, the heel and the full shell
    second_desorber
                        328C004: desorber II — 749 and LP steam 931 in, 750 overhead to
                        328C002 and 739 out, through LV-328505 or back to 328D003 as 741 on
                        FIC-328406; its boil-up, pressure, bubble point, holdup and species,
                        FFIC-329401, a ratio station on the desorbers' feed 735, FIC-329401,
                        LIC-328505 on LV-328505 or over FIC-328406, AI-328701, the heel and the
                        full shell
    reflux_drum
                        328D001 and 328E004: 737, 718A, 793 and a full 328C002's overflow in,
                        condensed on cooling water (never below it); 786 vented through
                        PV-328202 to 323E011's live pressure, 775 back to 328C002 on FIC-328404
                        under TIC-328008, 776 forward to 323E003 on LV-328501; its pressure,
                        temperature and holdup, the heel and the full drum
"""
