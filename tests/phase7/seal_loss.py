"""The HP stripper's level loss of `References/scenarios/Scenarios6.docx`, put to the plant.

What this is
------------
``Scenarios6.docx`` is a narrative of 322E001's bottom sump draining to nothing: the runaway drain
of LV-322501 opened in MAN (its S2-2.3a), the valve forced wide open, the reactor's overflow
starved behind a valve held at its stroke (S2-2.2b), and LT-322501 reading high in AUTO; then the
seal's loss, the synthesis gas blowing through LV-322501 into 323C003, and the consequences down
both the LP train and the synthesis loop. Like ``Scenarios5.md`` (`tests.phase7.coupled`) it is no
plant data (CLAUDE.md §4): its figures are printed as images the text does not carry and its own
first line says they were made on the old stripper, so each sentence that names a direction is an
EXPECTATION, measured on the port's plant — the 2,950-tube replacement and the plugged tubes
(decisions 154, 155) — against an unperturbed run of the same length, in the waves of
`tests.phase7.coupled`: ``W1`` the largest departure in the first five minutes, ``W2`` the mean
over 15 to 45 minutes, ``REV`` the second less the first.

Helwan's levers: LV-322501 is LIC-322501's (``lic_set``: MAN and an output, or AUTO and a set
point); the reactor's overflow is HV-322605 on HIC-322605 (``hic605_set``). The console has no
transmitter fault, so a high-reading LT-322501 is put as what it does to the loop: LIC-322501 in
AUTO on a set point 50 % below its reading, which drives LV-322501 open until the sump is empty.

Source: ``D:/Work/Urea Simulation/References/scenarios/Scenarios6.docx`` (text read 2026-10-28,
session 72; sections 2 to 4 and the tables of section 3).
"""

from __future__ import annotations

from tests.phase7.coupled import Claim, Coupled

C = Claim

# ---- the indicators, by what the note calls them ---------------------------------------------
ST_LEVEL = "STRIP_322E001.LI_322501"          # LT-322501, the sump's level
ST_LV = "STRIP_322E001.LV_322501"             # LV-322501's stroke
ST_DRAIN = "STRIP_322E001.drain_th"           # the liquid LV-322501 passes
ST_BLOW = "STRIP_322E001.blowthrough_th"      # the gas it passes once the seal is lost
ST_T_BOT = "STRIP_322E001.TT_322004"
ST_T_DOWN = "STRIP_322E001.TT_323001"         # downstream of the letdown's flash
ST_NH3 = "STRIP_322E001.bot_mass_pct.NH3"     # the carbamate left in the bottoms
ST_UREA = "STRIP_322E001.bot_mass_pct.Urea"
ST_TOP = "STRIP_322E001.top_th"               # the top gas to 322E002, PFD 201
ST_T_TOP = "STRIP_322E001.TT_322013"
C003_P = "RECIRC_323.C003.P_bara"             # PT-323201
LPCC_P = "LPCC_3232.E003.PIC_323202.pv"       # PT-323202
LPCC_VENT = "LPCC_3232.E003.PIC_323202.op"    # PV-323202
LPCC_LEVEL = "LPCC_3232.E003.LI_323502"
PUMP_308 = "LPCC_3232.E003.carbamate308_th"   # 323P001's delivery, PFD 308
F004_LEVEL = "RECIRC_323.F004.LI_323505"
E011_P = "LPCC_3232.E011.PIC_323203.pv"       # PT-323203, the 323E011 / 323D011 node
D011_LEVEL = "LPCC_3232.E011.LI_323D011"      # LT-323503
F010_T = "RECIRC_323.F010.TT_323010"
EVAP_FEED = "RECIRC_323.D002.FIC_324401.pv"   # FV-324401, the evaporators' feed
E001_T = "EVAP_324.E001.TT_324001"
UF85 = "EVAP_324.E003.FIC_335405.pv"          # the UF85 dosing
D001_P = "DESORB_328.D001.PIC_328202.pv"      # PT-328202
P_SYN = "x.p_syn_bara"                        # PT-329201, unrounded
HPCC_T = "HPCC_322E002.TT_322010"
HPCC_SAT = "x.hpcc_sat_frac"                  # 322E002's saturation fraction
HPCC_P_BUB = "x.hpcc_p_bub_bara"              # PI-322E002, the melt's bubble pressure
R_LEVEL = "REACT_322R001.LT_322504"
R_NC = "REACT_322R001.L_feed"
LP_P = "STEAM_SYSTEM.LP.P_bara"               # the LP header 322D001A/B raise into
C003_RELIEF = "x.c003_relief_th"              # what SV32351 / SV32352 relieve of 323C003

#: What the runaway drain does to the LP train while the sump still holds liquid (§2.2 Phase I,
#: §3.1, §4.1), common to the valve opened and the valve forced wide open.
_DRAIN_W1 = (
    C("2.2", ST_LEVEL, -1, "W1", "the sump level falls"),
    C("2.2", ST_DRAIN, +1, "W1", "the drain flow spikes"),
    C("2.2", C003_P, +1, "W1", "the increased prompt flash elevates PT-323201"),
    C("3.1", ST_NH3, +1, "W1", "unstripped carbamate breaks through into the bottoms"),
    C("3.1", ST_UREA, -1, "W1", "the bottoms' urea is diluted"),
    C("3.2", ST_TOP, +1, "W1", "the top gas evolution is boosted"),
    C("3.2", ST_T_TOP, +1, "W1", "TT-322013 climbs"),
    C("4.1", F010_T, -1, "W1", "the hydraulic flush cools TT-323010"),
    C("4.1", LPCC_P, +1, "W1", "PT-323202 climbs"),
    C("4.1", LPCC_VENT, +1, "W1", "PIC-323202 drives PV-323202 open"),
    C("4.1", LPCC_LEVEL, +1, "W1", "the condensed gas swells LI-323502"),
    C("4.1", PUMP_308, +1, "W1", "LIC-323502 accelerates 323P001"),
    C("4.1", F004_LEVEL, +1, "W1", "the liquid surge fills 323F004"),
    C("4.1", E011_P, +1, "W1", "PT-323203 rises"),
)

#: What the seal's loss does once the sump is empty (§2.2 Phase III, §3, §4.1 and §4.2).
_SEAL_LOST_W2 = (
    C("2.2", ST_BLOW, +1, "W2", "synthesis gas blows through LV-322501"),
    C("4.1", C003_P, +1, "W2", "the blow-through holds PT-323201 elevated"),
    C("4.1", C003_RELIEF, +1, "W2", "SV32351 / SV32352 pop and cycle"),
    C("3.2", ST_TOP, -1, "W2", "the top gas drops by the CO2 sweep lost out of LV-322501"),
    C("4.2", HPCC_T, +1, "W2", "322E002's product temperature climbs"),
    C("4.2", HPCC_SAT, -1, "W2", "its saturation fraction drops"),
    C("4.2", HPCC_P_BUB, +1, "W2", "PI-322E002, the melt's bubble pressure, rises"),
    C("4.2", P_SYN, +1, "W2", "uncondensed gas drives PT-329201 up"),
    C("4.2", R_NC, +1, "W2", "CO2 starvation spikes the reactor feed's N/C"),
    C("4.2", LP_P, -1, "W2", "the LP steam header sags as 322E002 loses condensation"),
    C("4.1", F004_LEVEL, -1, "W2", "323F004 empties once 323C003 stops draining liquid"),
    C("4.1", D011_LEVEL, -1, "W2", "323P008 drains 323D011 once the flash dies out"),
    C("4.1", EVAP_FEED, -1, "W2", "LIC-323507 throttles FV-324401, cutting the evaporators' feed"),
    C("4.1", E001_T, +1, "W2", "stage 1's held melt concentrates, TT-324001 climbing"),
    C("4.1", UF85, -1, "W2", "the UF85 ratio cascade throttles the dosing"),
    C("4.1", D001_P, +1, "W2", "323E011's pressure back-pressures 328D001"),
)

SEAL_LOSS = (
    Coupled(
        "S6-1", "Scenarios6.docx §2.1, the runaway drain (S2-2.3a)",
        "LV-322501 opened in MAN above its equilibrium stroke",
        "LIC-322501 to MAN, LV-322501 46.1 -> 70 %",
        ({"type": "lic_set", "mode": "MAN", "op": 70.0},),
        _DRAIN_W1 + _SEAL_LOST_W2),
    Coupled(
        "S6-2", "Scenarios6.docx §2.2 row 6, the valve forced wide open",
        "LV-322501 forced wide open", "LIC-322501 to MAN, LV-322501 46.1 -> 100 %",
        ({"type": "lic_set", "mode": "MAN", "op": 100.0},),
        _DRAIN_W1 + _SEAL_LOST_W2),
    Coupled(
        "S6-3", "Scenarios6.docx §2.1, feed starvation behind a held valve (S2-2.2b)",
        "Reactor overflow throttled while LV-322501 stays at its stroke",
        "LIC-322501 to MAN at its design 46.1 % (a manual minimum stop); HV-322605 throttled, "
        "HIC-322605 60 -> 40 %",
        ({"type": "lic_set", "mode": "MAN", "op": 46.1}, {"type": "hic605_set", "op": 40.0}),
        (C("2.1", ST_LEVEL, -1, "W1", "the sump level declines"),
         C("2.1", R_LEVEL, +1, "W1", "the reactor holds back what it no longer passes"),
         C("2.2", ST_BLOW, +1, "W2", "gas blow-through once the nozzle uncovers"),
         C("2.2", C003_P, +1, "W2", "the slip elevates PT-323201"),
         C("3.1", ST_T_BOT, -1, "W2", "under a low drain TT-322004 cools toward the floor"),
         C("3.1", ST_T_DOWN, -1, "W2", "the downstream flash temperature falls"))),
    Coupled(
        "S6-4", "Scenarios6.docx §2.1, LT-322501 reading high in AUTO",
        "LT-322501 drifts high: LIC-322501 drives LV-322501 open",
        "no transmitter fault on the console: LIC-322501 in AUTO, set point 50 -> 0 % — the loop "
        "seeing its level 50 % above where it wants it, as a reading drifted high does",
        ({"type": "lic_set", "mode": "AUTO", "sp": 0.0},),
        (C("2.1", ST_LV, +1, "W1", "LIC-322501 gradually drives LV-322501 open"),
         C("2.1", ST_LEVEL, -1, "W1", "the physical sump empties"),
         C("2.1", ST_DRAIN, +1, "W1", "the drain rises"),
         C("2.2", ST_BLOW, +1, "W2", "until gas blows through"),
         C("2.2", C003_P, +1, "W2", "into 323C003"))),
)

#: The note's cases the console has no lever for, and why: none (LT-322501's drift is put as what
#: it does to LIC-322501, S6-4).
NOT_PUT: dict = {}

__all__ = ["SEAL_LOSS", "NOT_PUT"]
