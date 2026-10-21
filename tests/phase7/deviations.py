"""The process-deviation scenarios of `References/scenarios`, put to the plant — data.

What this is
------------
`D:/Work/Urea Simulation/References/scenarios` holds four notes on how a Stamicarbon CO2-stripping
urea plant answers a deviation: a level, a pressure, a steam flow, a valve stepped. They are generic
— written for "a Stamicarbon plant", with figures (a 99.7 % melt, an atmospheric flash tank, a
140-145 bar reactor) that are not Helwan's, and the fourth is an analysis of V1's own source files —
so they are not plant data (CLAUDE.md §4) and nothing here is calibrated on them. Each claim is an
EXPECTATION, measured on the port's plant: the deviation applied on the console's own lever, the
indicator the claim names read off the published packet, against an unperturbed run of the same
length (the design seed drifts a little on its own, handoff B-94).

Each `Deviation` names its source section, the Helwan equipment and lever it is put on, the
commands (`ureasim.engine.command`, applied after the settling minute), how long it runs, and the
`Expect` rows: a packet path, the direction the note claims (+1 rises, -1 falls) and whether the
claim is about where the plant ends (``"end"``) or a transient on the way (``"peak"``).

Where Helwan's plant differs from the note — no atmospheric flash tank (323F004 runs at 1.13 bar a
and 323F010 at 0.46), a liquid-ammonia HP ejector (322J001 on HIC-322602) where the note has a steam
ejector, the CO2 compressor a boundary (decision 73) — the deviation is put on the equipment the
note's section describes, and `helwan` says so. A claim no indicator of the model publishes (a
crystallised line, a corroded tube, a cavitating impeller) is listed in `unmodelled` with the reason,
not invented.

Sources: ``Scenarios.md`` (S1), ``Scenarios2.md`` (S2), ``Scenarios3.md`` (S3), ``Scenarios4.md``
(S4) in that folder.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The settling time before a deviation is applied, and the sampling interval [s].
SETTLE_S = 60.0
SAMPLE_S = 5.0


@dataclass(frozen=True)
class Expect:
    """One claimed response: the packet path, the claimed direction, and where it is read."""

    path: str
    sign: int
    claim: str
    measure: str = "end"


@dataclass(frozen=True)
class Deviation:
    """One deviation of the notes, put on Helwan's plant."""

    key: str
    source: str
    title: str
    helwan: str
    commands: tuple
    expects: tuple
    duration_s: float = 900.0
    unmodelled: tuple = ()


def _ctrl(tag: str, **fields) -> dict:
    """An inline faceplate command on units 323, 328 and 324 (`r323_ctrl_set`)."""
    return {"type": "r323_ctrl_set", "id": tag, **fields}


def _man(tag: str, op: float) -> dict:
    return _ctrl(tag, mode="MAN", op=op)


def _sp(tag: str, sp: float) -> dict:
    return _ctrl(tag, mode="AUTO", sp=sp)


E = Expect

DEVIATIONS = (
    # ==================================================================================
    # Scenarios.md — the reactor and the concentration train
    # ==================================================================================
    Deviation(
        "S1-1.1", "Scenarios.md §1.1", "Reactor high level (overfilling)",
        "322R001's level rises when HV-322605, its overflow valve to 322E001, is pinched "
        "(HIC-322605 60 -> 30 %)",
        ({"type": "hic605_set", "op": 30.0},),
        (E("REACT_322R001.LT_322504", +1, "the reactor level rises"),
         E("SCRUB_322E003.TT_322002", -1, "HP scrubber outlet temperature drops (flooding)"),
         E("ABSORB_328.C001.P_bara", +1, "LP absorber overload raises its pressure"),
         E("SCRUB_322E003.P_overflow", +1, "synthesis loop pressure spikes", "peak"),
         E("STRIP_322E001.LV_322501", +1, "the stripper's level valve opens aggressively",
           "peak")),
        1800.0,
        ("liquid carried into the reactor's vent line (no two-phase entrainment model)",)),
    Deviation(
        "S1-1.2", "Scenarios.md §1.2", "Reactor low level (loss of holdup)",
        "HV-322605 opened wide (HIC-322605 60 -> 100 %) drains 322R001 into 322E001",
        ({"type": "hic605_set", "op": 100.0},),
        (E("REACT_322R001.LT_322504", -1, "the reactor level falls"),
         E("SCRUB_322E003.P_overflow", -1, "synthesis pressure drops"),
         E("REACT_322R001.X_conv", -1, "reactor conversion drops (less residence)"),
         E("STRIP_322E001.bot_mass_pct.NH3", +1, "stripping efficiency lost: NH3 slips"),
         E("RECIRC_323.C003.v305_th", +1, "recycle loop overloaded: more LP vapour")),
        1800.0,
        ("passive oxide layer stripped, corrosion (no corrosion model)",)),
    Deviation(
        "S1-2.1", "Scenarios.md §2.1", "Flash tank high level (overfilling)",
        "Helwan has no atmospheric flash tank: 323F004, the LP flash at 1.13 bar a, filled by "
        "LV-323505 pinched in MAN (67.7 -> 30 %)",
        (_man("LIC-323505", 30.0),),
        (E("RECIRC_323.F004.LI_323505", +1, "the flash tank level rises"),
         E("LPCC_3232.E011.LI_323D011", +1, "the condenser below floods"),
         E("LPCC_3232.E011.P_bara", +1, "the condenser's node rises (vapour line choked)",
           "peak")),
        900.0,
        ("crystallisation in the vapour line", "conductivity of the process condensate")),
    Deviation(
        "S1-2.2", "Scenarios.md §2.2", "Flash tank low level (loss of liquid seal)",
        "323F004 drained by LV-323505 opened in MAN (67.7 -> 100 %): its vapour blows through "
        "into 323F010, the vacuum stage below",
        (_man("LIC-323505", 100.0),),
        (E("RECIRC_323.F004.LI_323505", -1, "the flash tank level falls"),
         E("RECIRC_323.F004.blow505_th", +1, "gas blows through the bottom valve", "peak"),
         E("RECIRC_323.F010.P_bara", +1, "the downstream vacuum is lost", "peak"),
         E("RECIRC_323.F010.TT_323010", +1, "the downstream temperature spikes", "peak")),
        900.0,
        ("biuret in the downstream stage (not published per stage)",
         "pump cavitation (323F004 drains through a valve, no pump)")),
    Deviation(
        "S1-3.1a", "Scenarios.md §3.1", "Pre-evaporator steam increased",
        "323E010's chest: TIC-323012 99 -> 101 C raises PIC-329208's demand",
        (_sp("TIC-323012", 101.0),),
        (E("RECIRC_323.D002.urea_pct", +1, "over-concentration of the product"),
         E("RECIRC_323.F010.TT_323010", +1, "bulk temperature rises"),
         E("EVAP_324.VAC.324E002.Q_kW", +1, "the condenser is overloaded")),
        900.0, ("biuret and hydrolysis in 323F010 (not published per stage)",)),
    Deviation(
        "S1-3.1b", "Scenarios.md §3.1", "Pre-evaporator steam decreased",
        "TIC-323012 99 -> 97 C",
        (_sp("TIC-323012", 97.0),),
        (E("RECIRC_323.D002.urea_pct", -1, "under-concentration"),
         E("EVAP_324.E001.Q_kW", +1, "the load shifts to the first vacuum evaporator"),
         E("EVAP_324.E001.PIC_329203.op", +1, "it takes more steam")),
        900.0),
    Deviation(
        "S1-3.2a", "Scenarios.md §3.2", "Pre-evaporator drum pressure increased",
        "PT-323204 raised by HV-323605 pinched to half its design capacity (HIC-323605 64.1 -> "
        "32.0 %)",
        ({"type": "hic323605_set", "op": 32.0},),
        (E("RECIRC_323.F010.P_bara", +1, "the drum pressure rises"),
         E("RECIRC_323.F010.evap_th", -1, "flashing is suppressed"),
         E("RECIRC_323.F010.TT_323010", +1, "sensible heat builds the bulk temperature",
           "peak")),
        900.0),
    Deviation(
        "S1-3.2b", "Scenarios.md §3.2", "Pre-evaporator drum pressure decreased",
        "HV-323605 opened to 1.6 times its design capacity (HIC-323605 64.1 -> 79.1 %)",
        ({"type": "hic323605_set", "op": 79.1},),
        (E("RECIRC_323.F010.P_bara", -1, "the drum pressure falls"),
         E("RECIRC_323.F010.TT_323010", -1, "aggressive flashing cools the liquor", "peak")),
        900.0, ("pump cavitation (323F010 drains by its barometric leg)",)),
    Deviation(
        "S1-4.1a", "Scenarios.md §4.1", "First vacuum evaporator steam increased",
        "324E001's chest: TIC-324001 130 -> 133 C",
        (_sp("TIC-324001", 133.0),),
        (E("EVAP_324.E001.urea_pct", +1, "the melt concentration rises"),
         E("EVAP_324.E001.PT_324201", +1, "the vacuum condenser is overloaded", "peak")),
        900.0, ("biuret in 324F001 (not published per stage)",)),
    Deviation(
        "S1-4.1b", "Scenarios.md §4.1", "First vacuum evaporator steam decreased",
        "TIC-324001 130 -> 127 C",
        (_sp("TIC-324001", 127.0),),
        (E("EVAP_324.E001.urea_pct", -1, "the melt is wet"),
         E("EVAP_324.E003.Q_kW", +1, "the second stage is loaded")),
        900.0, ("crystallisation near 115 C",)),
    Deviation(
        "S1-4.2a", "Scenarios.md §4.2", "First vacuum evaporator pressure increased",
        "PIC-324202 0.33 -> 0.40 bar a (the bleed valve admits air)",
        (_sp("PIC-324202", 0.40),),
        (E("EVAP_324.E001.PT_324201", +1, "the vacuum is lost"),
         E("EVAP_324.E001.urea_pct", -1, "the boiling point rises, less water leaves"),
         E("EVAP_324.E001.PIC_329203.op", +1, "TIC-324001 asks more steam to hold 130 C")),
        900.0),
    Deviation(
        "S1-4.2b", "Scenarios.md §4.2", "First vacuum evaporator pressure decreased",
        "PIC-324202 0.33 -> 0.28 bar a",
        (_sp("PIC-324202", 0.28),),
        (E("EVAP_324.E001.PT_324201", -1, "the vacuum deepens"),
         E("EVAP_324.E001.urea_pct", +1, "more water flashes")),
        900.0),
    Deviation(
        "S1-5.1a", "Scenarios.md §5.1", "Second vacuum evaporator steam increased",
        "324E003's chest: TIC-324002 140 -> 143 C",
        (_sp("TIC-324002", 143.0),),
        (E("EVAP_324.E003.urea_pct", +1, "drier melt"),
         E("EVAP_324.E003.PT_324203", +1, "vapour velocity loads the condensers", "peak")),
        900.0, ("biuret, entrainment into the vacuum condensers",)),
    Deviation(
        "S1-5.1b", "Scenarios.md §5.1", "Second vacuum evaporator steam decreased",
        "TIC-324002 140 -> 137 C",
        (_sp("TIC-324002", 137.0),),
        (E("EVAP_324.E003.urea_pct", -1, "moisture left in the product"),),
        900.0, ("freezing on the heater tubes",)),
    Deviation(
        "S1-5.2a", "Scenarios.md §5.2", "Second vacuum evaporator vacuum lost",
        "PIC-324203 0.131 -> 0.20 bar a",
        (_sp("PIC-324203", 0.20),),
        (E("EVAP_324.E003.PT_324203", +1, "the vacuum is lost"),
         E("EVAP_324.E003.urea_pct", -1, "boiling is suppressed"),
         E("EVAP_324.E003.PIC_329212.op", +1, "the operator's steam goes up (TIC-324002)")),
        900.0, ("raining in the prill tower",)),
    Deviation(
        "S1-5.2b", "Scenarios.md §5.2", "Second vacuum evaporator vacuum deepened",
        "PIC-324203 0.131 -> 0.10 bar a",
        (_sp("PIC-324203", 0.10),),
        (E("EVAP_324.E003.PT_324203", -1, "the vacuum deepens"),
         E("EVAP_324.E003.urea_pct", +1, "more water flashes")),
        900.0, ("flash freezing below 132.7 C",)),
    Deviation(
        "S1-5.4a", "Scenarios.md §5.4", "Second evaporator discharge level high",
        "LIC-324501 54.7 -> 80 %",
        (_sp("LIC-324501", 80.0),),
        (E("EVAP_324.E003.LI_324F003", +1, "the level rises"),
         E("EVAP_324.E003.product_th", -1, "the discharge holds back while it fills", "peak")),
        900.0, ("biuret from the longer residence (not published per stage)",)),
    Deviation(
        "S1-5.4b", "Scenarios.md §5.4", "Second evaporator discharge level low",
        "LIC-324501 54.7 -> 10 %",
        (_sp("LIC-324501", 10.0),),
        (E("EVAP_324.E003.LI_324F003", -1, "the level falls"),
         E("EVAP_324.E003.PT_324203", +1, "the seal breaks and the vacuum crashes", "peak")),
        900.0, ("melt pump NPSH",)),

    # ==================================================================================
    # Scenarios2.md — the synthesis loop, the LP and the waste-water sections
    # ==================================================================================
    Deviation(
        "S2-1.1", "Scenarios2.md §1.1", "HP ejector opening decreased",
        "322J001, the liquid-ammonia ejector: HIC-322602 74 -> 60 %",
        ({"type": "hic_set", "value": 60.0},),
        (E("SCRUB_322E003.LT_329501", -1, "the scrubber overflow level falls"),
         E("SCRUB_322E003.TT_322011", -1, "the overflow line cools"),
         E("EJ_322F001.TT_322012", +1, "the NH3 to the HPCC is hotter"),
         E("SCRUB_322E003.ccw.TT_329125", +1, "the tempered water warms slightly")),
        900.0),
    Deviation(
        "S2-1.2", "Scenarios2.md §1.2", "HP scrubber vent valve opened",
        "HV-322604, 322E003's off-gas valve: HIC-322604 72 -> 90 %",
        ({"type": "hic604_set", "op": 90.0},),
        (E("SCRUB_322E003.P_overflow", -1, "synthesis pressure falls"),
         E("SCRUB_322E003.TT_322011_lp", +1, "the vent line warms"),
         E("SCRUB_322E003.ccw.TT_329125", +1, "the tempered water warms"),
         E("SCRUB_322E003.LT_329501", +1, "the overflow level rises"),
         E("SCRUB_322E003.TT_322011", +1, "the overflow temperature rises")),
        900.0),
    Deviation(
        "S2-1.3", "Scenarios2.md §1.3", "Recycle carbamate to the HP scrubber increased",
        "323P001 on SIC-323901 in MAN, 59.9 -> 70 % (PFD 308)",
        (_man("SIC-323901", 70.0),),
        (E("SCRUB_322E003.P_overflow", -1, "synthesis pressure falls"),
         E("SCRUB_322E003.LT_329501", +1, "the overflow level rises"),
         E("SCRUB_322E003.TT_322002", -1, "the vent temperature drops"),
         E("SCRUB_322E003.TT_322011", -1, "the overflow temperature drops"),
         E("SCRUB_322E003.ccw.TT_329125", -1, "the tempered-water outlet drops"),
         E("EJ_322F001.TT_322012", -1, "the ejector's NH3 cools")),
        900.0),
    Deviation(
        "S2-1.4a", "Scenarios2.md §1.4", "HP scrubber tempered-water inlet colder",
        "TIC-329005 80 -> 75 C",
        ({"type": "tic_set", "mode": "AUTO", "sp": 75.0},),
        (E("SCRUB_322E003.P_overflow", -1, "condensation rises, synthesis pressure falls"),
         E("SCRUB_322E003.LT_329501", +1, "the overflow level rises"),
         E("SCRUB_322E003.TT_322002", -1, "the vent line cools"),
         E("SCRUB_322E003.TT_322011", -1, "the overflow cools"),
         E("EJ_322F001.TT_322012", -1, "the ejector discharge cools")),
        900.0),
    Deviation(
        "S2-1.4b", "Scenarios2.md §1.4", "HP scrubber tempered water flow increased",
        "FIC-329409 306 -> 360 m3/h, TIC-329005 in MAN (no tempering adjustment)",
        ({"type": "tic_set", "mode": "MAN", "op": 50.0},
         {"type": "fic_set", "mode": "AUTO", "sp": 360.0}),
        (E("SCRUB_322E003.P_overflow", +1, "the loop heats up, synthesis pressure rises"),
         E("SCRUB_322E003.LT_329501", -1, "the level drops"),
         E("SCRUB_322E003.TT_322002", +1, "scrubber temperatures rise")),
        900.0),
    Deviation(
        "S2-2.1a", "Scenarios2.md §2.1", "HP stripper steam increased",
        "329D005's MP header: PIC-329204 19.7 -> 20.5 bar a",
        ({"type": "pic329204_set", "mode": "AUTO", "sp": 20.5},),
        (E("STRIP_322E001.TT_322004", +1, "the stripper bottoms temperature rises"),
         E("STRIP_322E001.bot_mass_pct.NH3", -1, "stripping efficiency rises"),
         E("SCRUB_322E003.P_overflow", +1, "synthesis pressure spikes", "peak"),
         E("HPCC_322E002.steam.kgh", +1, "LP steam export rises"),
         E("STRIP_322E001.bot_mass_pct.Biuret", +1, "biuret rises")),
        900.0),
    Deviation(
        "S2-2.1b", "Scenarios2.md §2.1", "HP stripper steam decreased",
        "PIC-329204 19.7 -> 18.9 bar a",
        ({"type": "pic329204_set", "mode": "AUTO", "sp": 18.9},),
        (E("STRIP_322E001.bot_mass_pct.NH3", +1, "carbamate slips to the LP section"),
         E("HPCC_322E002.steam.kgh", -1, "LP steam export drops"),
         E("RECIRC_323.C003.v305_th", +1, "the LP section is overwhelmed")),
        900.0),
    Deviation(
        "S2-2.2a", "Scenarios2.md §2.2", "HP stripper high level (flooding)",
        "LIC-322501 50 -> 85 %",
        ({"type": "lic_set", "mode": "AUTO", "sp": 85.0},),
        (E("STRIP_322E001.LI_322501", +1, "the stripper floods"),
         E("STRIP_322E001.bot_mass_pct.NH3", +1, "stripping efficiency drops"),
         E("RECIRC_323.C003.v305_th", +1, "undecomposed carbamate overwhelms the LP section")),
        900.0),
    Deviation(
        "S2-2.2b", "Scenarios2.md §2.2", "HP stripper low level (loss of seal)",
        "LIC-322501 50 -> 2 %",
        ({"type": "lic_set", "mode": "AUTO", "sp": 2.0},),
        (E("STRIP_322E001.LI_322501", -1, "the level falls"),
         E("STRIP_322E001.blowthrough_th", +1, "gas blows through to the LP section", "peak"),
         E("RECIRC_323.C003.P_bara", +1, "the LP section is overpressured", "peak")),
        900.0, ("valve erosion is a flag (LV322501_EROSION), not wear",)),
    Deviation(
        "S2-2.3a", "Scenarios2.md §2.3", "Stripper level valve: big step opening",
        "LIC-322501 in MAN, LV-322501 46 -> 90 %",
        ({"type": "lic_set", "mode": "MAN", "op": 90.0},),
        (E("STRIP_322E001.LI_322501", -1, "the stripper drains"),
         E("STRIP_322E001.blowthrough_th", +1, "loss of seal, blow-through", "peak"),
         E("RECIRC_323.C003.P_bara", +1, "the LP condensers are overloaded", "peak")),
        900.0),
    Deviation(
        "S2-2.3b", "Scenarios2.md §2.3", "Stripper level valve: big step closing",
        "LIC-322501 in MAN, LV-322501 46 -> 10 %",
        ({"type": "lic_set", "mode": "MAN", "op": 10.0},),
        (E("STRIP_322E001.LI_322501", +1, "the stripper floods"),
         E("RECIRC_323.D002.product324_th", -1, "the evaporators are starved", "peak")),
        900.0),
    Deviation(
        "S2-3.1a", "Scenarios2.md §3.1", "Reactor downcomer valve: big step opening",
        "HV-322605 60 -> 100 %",
        ({"type": "hic605_set", "op": 100.0},),
        (E("STRIP_322E001.LI_322501", +1, "a wave floods the stripper", "peak"),
         E("REACT_322R001.LT_322504", -1, "the reactor level drops")),
        900.0),
    Deviation(
        "S2-3.1b", "Scenarios2.md §3.1", "Reactor downcomer valve: big step closing",
        "HV-322605 60 -> 20 %",
        ({"type": "hic605_set", "op": 20.0},),
        (E("REACT_322R001.LT_322504", +1, "liquid backs up in the reactor"),
         E("STRIP_322E001.TT_322004", +1, "the starved stripper's bottoms heat up", "peak"),
         E("SCRUB_322E003.P_overflow", +1, "the loop pressure rises", "peak")),
        900.0, ("dry-out corrosion",)),
    Deviation(
        "S2-4.1a", "Scenarios2.md §4.1", "Rectifying column steam increased",
        "323C003 / 323E002: TIC-323007 135 -> 140 C",
        (_sp("TIC-323007", 140.0),),
        (E("RECIRC_323.C003.v305_th", +1, "the LP carbamate condenser gets more vapour"),
         E("LPCC_3232.E003.P_bara", +1, "the LPCC is overloaded", "peak")),
        900.0, ("biuret in the rectifier",)),
    Deviation(
        "S2-4.1b", "Scenarios2.md §4.1", "Rectifying column steam decreased",
        "TIC-323007 135 -> 128 C",
        (_sp("TIC-323007", 128.0),),
        (E("RECIRC_323.C003.v305_th", -1, "less is decomposed"),
         E("RECIRC_323.F010.P_bara", +1, "the carbamate flashes in the vacuum stages", "peak"),
         E("RECIRC_323.D002.urea_pct", -1, "wet, off-spec product")),
        900.0),
    Deviation(
        "S2-4.2a", "Scenarios2.md §4.2", "Rectifying column high level",
        "LIC-323501 60 -> 90 %",
        (_sp("LIC-323501", 90.0),),
        (E("RECIRC_323.C003.LI_323501", +1, "the level rises"),),
        900.0, ("boil-over of urea into the overhead (no entrainment model)",)),
    Deviation(
        "S2-4.2b", "Scenarios2.md §4.2", "Rectifying column low level (loss of seal)",
        "LIC-323501 60 -> 2 %",
        (_sp("LIC-323501", 2.0),),
        (E("RECIRC_323.C003.LI_323501", -1, "the level falls"),
         E("RECIRC_323.C003.blow501_th", +1, "LP gas blows through", "peak"),
         E("RECIRC_323.F004.P_bara", +1, "the next stage's pressure rises", "peak")),
        900.0),
    Deviation(
        "S2-4.3a", "Scenarios2.md §4.3", "Rectifying level valve: big step opening",
        "LIC-323501 in MAN, LV-323501 56.6 -> 95 %",
        (_man("LIC-323501", 95.0),),
        (E("RECIRC_323.C003.drain314_th", +1, "a wave reaches the next stages", "peak"),
         E("RECIRC_323.F010.TT_323010", -1, "the stage's temperature crashes", "peak")),
        900.0),
    Deviation(
        "S2-4.3b", "Scenarios2.md §4.3", "Rectifying level valve: big step closing",
        "LIC-323501 in MAN, LV-323501 56.6 -> 15 %",
        (_man("LIC-323501", 15.0),),
        (E("RECIRC_323.C003.LI_323501", +1, "the column floods"),
         E("RECIRC_323.D002.product324_th", -1, "the evaporators are starved", "peak")),
        900.0),
    Deviation(
        "S2-5.1", "Scenarios2.md §5.1", "Feed to the desorption and hydrolysis unit increased",
        "FIC-328402 31.4 -> 36 m3/h",
        (_sp("FIC-328402", 36.0),),
        (E("DESORB_328.C002.TT_328007", -1, "the cold feed quenches the desorber", "peak"),
         E("DESORB_328.C004.FIC_329401.op", +1, "the steam valves open"),
         E("DESORB_328.C004.nh3_740_ppm", +1, "more NH3 slips"),
         E("DESORB_328.C004.urea_740_ppm", +1, "more urea slips")),
        1800.0),
    Deviation(
        "S2-5.2a", "Scenarios2.md §5.2", "Steam to the second desorber increased",
        "328C004's FFIC-329401 0.2068 -> 0.24",
        (_sp("FFIC-329401", 0.24),),
        (E("DESORB_328.C004.nh3_740_ppm", -1, "lower NH3 slip"),
         E("DESORB_328.C004.P_bara", +1, "the column's pressure drop rises"),
         E("DESORB_328.C004.ovhd750_th", +1, "more vapour to the overhead")),
        1800.0),
    Deviation(
        "S2-5.2b", "Scenarios2.md §5.2", "Steam to the second desorber decreased",
        "FFIC-329401 0.2068 -> 0.17",
        (_sp("FFIC-329401", 0.17),),
        (E("DESORB_328.C004.nh3_740_ppm", +1, "NH3 slips"),
         E("DESORB_328.C004.urea_740_ppm", +1, "urea slips")),
        1800.0),
    Deviation(
        "S2-5.3a", "Scenarios2.md §5.3", "Steam to the hydrolyser increased",
        "328C003: TIC-328012 in MAN, FIC-329402 to 1300 kg/h",
        (_man("TIC-328012", 50.0), _sp("FIC-329402", 1300.0)),
        (E("DESORB_328.C003.urea_slip_ppm", -1, "urea slip falls"),
         E("DESORB_328.C003.ovhd748_th", +1, "a vapour surge to the first desorber")),
        1800.0),
    Deviation(
        "S2-5.3b", "Scenarios2.md §5.3", "Steam to the hydrolyser decreased",
        "TIC-328012 in MAN, FIC-329402 to 900 kg/h",
        (_man("TIC-328012", 50.0), _sp("FIC-329402", 900.0)),
        (E("DESORB_328.C003.urea_slip_ppm", +1, "hydrolysis kinetics crash"),
         E("DESORB_328.C004.urea_740_ppm", +1, "urea passes to the effluent")),
        1800.0),

    # ==================================================================================
    # Scenarios3.md — the LP condensers, the tanks and the desorbers
    # ==================================================================================
    Deviation(
        "S3-1.1a", "Scenarios3.md §1.1", "Ammonia water to the LPCC increased",
        "734 on FIC-323401 1.55 -> 2.5 m3/h",
        (_sp("FIC-323401", 2.5),),
        (E("LPCC_3232.E003.carbamate308_th", +1, "more water recycled to the HP section"),),
        900.0, ("crystallisation margin, H/C ratio (not published)",)),
    Deviation(
        "S3-1.1b", "Scenarios3.md §1.1", "Ammonia water to the LPCC decreased",
        "FIC-323401 1.55 -> 0.5 m3/h",
        (_sp("FIC-323401", 0.5),),
        (E("LPCC_3232.E003.vent321_th", +1, "less absorption: more vapour to the vent"),),
        900.0, ("crystallisation in the tubes",)),
    Deviation(
        "S3-1.2a", "Scenarios3.md §1.2", "LPCC drum level increased",
        "323D001: LIC-323502 50 -> 80 %",
        (_sp("LIC-323502", 80.0),),
        (E("LPCC_3232.E003.LI_323502", +1, "the level rises"),),
        900.0, ("entrainment to the absorber (no model)",)),
    Deviation(
        "S3-1.2b", "Scenarios3.md §1.2", "LPCC drum level decreased",
        "LIC-323502 50 -> 10 %",
        (_sp("LIC-323502", 10.0),),
        (E("LPCC_3232.E003.LI_323502", -1, "the level falls"),),
        900.0, ("pump cavitation",)),
    Deviation(
        "S3-1.3a", "Scenarios3.md §1.3", "LPCC drum pressure increased",
        "PIC-323202 3.2 -> 3.6 bar a",
        (_sp("PIC-323202", 3.6),),
        (E("LPCC_3232.E003.P_bara", +1, "the pressure rises"),
         E("RECIRC_323.C003.P_bara", +1, "back-pressure on the rectifier"),
         E("LPCC_3232.E003.vent321_th", -1, "better condensation")),
        900.0),
    Deviation(
        "S3-1.3b", "Scenarios3.md §1.3", "LPCC drum pressure decreased",
        "PIC-323202 3.2 -> 2.8 bar a",
        (_sp("PIC-323202", 2.8),),
        (E("LPCC_3232.E003.P_bara", -1, "the pressure falls"),
         E("LPCC_3232.E003.vent321_th", +1, "uncondensed gas bypasses to the absorber")),
        900.0),
    Deviation(
        "S3-1.4a", "Scenarios3.md §1.4", "LPCC tempered water warmer",
        "TIC-323013 55 -> 60 C",
        (_sp("TIC-323013", 60.0),),
        (E("LPCC_3232.E003.TT_323006", +1, "the process temperature rises"),
         E("LPCC_3232.E003.PIC_323202.op", +1, "the vent opens to hold the pressure"),
         E("LPCC_3232.E003.vent321_th", +1, "incomplete condensation vents more")),
        900.0),
    Deviation(
        "S3-1.4b", "Scenarios3.md §1.4", "LPCC tempered water colder",
        "TIC-323013 55 -> 50 C",
        (_sp("TIC-323013", 50.0),),
        (E("LPCC_3232.E003.TT_323006", -1, "the process temperature falls"),
         E("LPCC_3232.E003.vent321_th", -1, "more condenses")),
        900.0, ("crystallisation on cold tube walls",)),
    Deviation(
        "S3-1.5", "Scenarios3.md §1.5", "LPCC tempered water flow decreased",
        "TIC-323013 in MAN, its split range 50 -> 30 %",
        (_man("TIC-323013", 30.0),),
        (E("LPCC_3232.E003.TT_323006", +1, "the condensing temperature rises"),
         E("LPCC_3232.E003.vent321_th", +1, "more gas escapes to the vent")),
        900.0),
    Deviation(
        "S3-1.6", "Scenarios3.md §1.6", "Solution from the reflux pump to the LPCC increased",
        "776 from 328D001: LIC-328501 in MAN, LV-328501 29.4 -> 40 %",
        (_man("LIC-328501", 40.0),),
        (E("DESORB_328.D001.draw776_th", +1, "more solution to the LPCC"),
         E("LPCC_3232.E003.carbamate308_th", +1, "more water to the HP loop")),
        900.0),
    Deviation(
        "S3-1.7a", "Scenarios3.md §1.7", "Lean carbamate pump flow increased",
        "323P001 (SIC-323901 in MAN) 59.9 -> 70 %: Helwan's LPCC pump to the HP scrubber",
        (_man("SIC-323901", 70.0),),
        (E("LPCC_3232.E003.LI_323502", -1, "the LPCC drum drains"),
         E("LPCC_3232.E003.carbamate308_th", +1, "more flow to the HP scrubber")),
        900.0),
    Deviation(
        "S3-1.7b", "Scenarios3.md §1.7", "Lean carbamate pump flow decreased",
        "SIC-323901 in MAN 59.9 -> 50 %",
        (_man("SIC-323901", 50.0),),
        (E("LPCC_3232.E003.LI_323502", +1, "the LPCC level backs up"),
         E("LPCC_3232.E003.carbamate308_th", -1, "the HP loop is starved of recycle")),
        900.0),
    Deviation(
        "S3-2.1", "Scenarios3.md §2.1", "Ammonia water to the reflux condenser increased",
        "793 on FIC-328405 0 -> 1.5 m3/h",
        (_sp("FIC-328405", 1.5),),
        (E("DESORB_328.D001.draw776_th", +1, "more water recycled"),),
        900.0),
    Deviation(
        "S3-2.2a", "Scenarios3.md §2.2", "Reflux accumulator level increased",
        "328D001: LIC-328501 50.5 -> 80 %",
        (_sp("LIC-328501", 80.0),),
        (E("DESORB_328.D001.LI_328501", +1, "the level rises"),),
        900.0, ("entrainment to the vents",)),
    Deviation(
        "S3-2.2b", "Scenarios3.md §2.2", "Reflux accumulator level decreased",
        "LIC-328501 50.5 -> 5 %",
        (_sp("LIC-328501", 5.0),),
        (E("DESORB_328.D001.LI_328501", -1, "the level falls"),),
        900.0, ("reflux pump NPSH",)),
    Deviation(
        "S3-2.3a", "Scenarios3.md §2.3", "Reflux condenser pressure increased",
        "PIC-328202 3.5 -> 3.9 bar a (on 328C002)",
        (_sp("PIC-328202", 3.9),),
        (E("DESORB_328.C002.P_bara", +1, "back-pressure on the desorber"),
         E("DESORB_328.C002.ovhd737_th", -1, "boiling and stripping suppressed", "peak"),
         E("DESORB_328.D001.vent786_th", -1, "better condensation, less vent", "peak")),
        900.0),
    Deviation(
        "S3-2.3b", "Scenarios3.md §2.3", "Reflux condenser pressure decreased",
        "PIC-328202 3.5 -> 3.1 bar a",
        (_sp("PIC-328202", 3.1),),
        (E("DESORB_328.C002.P_bara", -1, "the pressure falls"),
         E("DESORB_328.D001.vent786_th", +1, "uncondensed gas vented", "peak")),
        900.0),
    Deviation(
        "S3-2.4", "Scenarios3.md §2.4", "Lean carbamate to the reflux condenser decreased",
        "718A is LIC-323503's remainder: FIC-323418 3.34 -> 4.0 m3/h takes it to 718B",
        (_sp("FIC-323418", 4.0),),
        (E("LPCC_3232.E011.carb718A_th", -1, "the condenser's absorbent falls"),
         E("DESORB_328.D001.TT_328D001", +1, "temperature spike in the condenser", "peak"),
         E("DESORB_328.D001.vent786_th", +1, "more venting", "peak")),
        900.0),
    Deviation(
        "S3-3.1a", "Scenarios3.md §3.1", "Ammonia water to the flash tank condenser increased",
        "791 on FIC-323402 1.55 -> 2.5 m3/h",
        (_sp("FIC-323402", 2.5),),
        (E("LPCC_3232.E011.P_bara", -1, "the condenser pressure drops", "peak"),
         E("LPCC_3232.E011.TT_323011", -1, "the condenser cools")),
        900.0),
    Deviation(
        "S3-3.1b", "Scenarios3.md §3.1", "Ammonia water to the flash tank condenser decreased",
        "FIC-323402 1.55 -> 0.3 m3/h",
        (_sp("FIC-323402", 0.3),),
        (E("LPCC_3232.E011.P_bara", +1, "the condenser pressure spikes", "peak"),
         E("RECIRC_323.F004.P_bara", +1, "back-pressure on the flash tank", "peak"),
         E("LPCC_3232.E011.vap011_th", +1, "ammonia vented", "peak")),
        900.0),
    Deviation(
        "S3-3.2a", "Scenarios3.md §3.2", "Flash tank condenser level tank high",
        "323D011: LIC-323503 50 -> 85 %",
        (_sp("LIC-323503", 85.0),),
        (E("LPCC_3232.E011.LI_323D011", +1, "the level rises"),),
        900.0, ("carry-over to the vent scrubber",)),
    Deviation(
        "S3-3.2b", "Scenarios3.md §3.2", "Flash tank condenser level tank low",
        "LIC-323503 50 -> 6 %",
        (_sp("LIC-323503", 6.0),),
        (E("LPCC_3232.E011.LI_323D011", -1, "the level falls"),),
        900.0, ("pump NPSH; AC4 stops 323P008 below L2 5 % (B-93), not reached here",)),
    Deviation(
        "S3-4.3a", "Scenarios3.md §4.3", "Urea solution tank level high",
        "323D002: LIC-323507 10 -> 40 %",
        (_sp("LIC-323507", 40.0),),
        (E("RECIRC_323.D002.LI_323507", +1, "the level rises"),
         E("RECIRC_323.D002.product324_th", -1, "the feed to evaporation is held back",
           "peak")),
        900.0, ("biuret from the residence",)),
    Deviation(
        "S3-4.3b", "Scenarios3.md §4.3", "Urea solution tank level low",
        "LIC-323507 10 -> 2 %",
        (_sp("LIC-323507", 2.0),),
        (E("RECIRC_323.D002.LI_323507", -1, "the level falls"),),
        900.0, ("feed pump trip (no low-level interlock on 323D002 in the archive)",)),
    Deviation(
        "S3-4.4", "Scenarios3.md §4.4", "Urea solution tank temperature increased",
        "323D002 takes 323F010's temperature: TIC-323012 99 -> 101 C",
        (_sp("TIC-323012", 101.0),),
        (E("RECIRC_323.D002.TI_323008", +1, "the tank temperature rises"),),
        900.0, ("biuret and hydrolysis in the tank",)),
    Deviation(
        "S3-5.1a", "Scenarios3.md §5.1", "Reflux to the first desorber increased",
        "FT-328404: TIC-328008 in MAN, FIC-328404's set point 1675 -> 2200 kg/h",
        (_man("TIC-328008", 2200.0),),
        (E("DESORB_328.C002.TT_328008", -1, "the top temperature falls"),
         E("DESORB_328.D001.TIC_328008.pv", -1, "less water vapour overhead")),
        900.0),
    Deviation(
        "S3-5.1b", "Scenarios3.md §5.1", "Reflux to the first desorber decreased",
        "TIC-328008 in MAN, 1675 -> 1100 kg/h",
        (_man("TIC-328008", 1100.0),),
        (E("DESORB_328.C002.TT_328008", +1, "the top temperature rises"),
         E("DESORB_328.D001.TIC_328008.pv", +1, "more water vapour overhead"),
         E("DESORB_328.D001.P_bara", +1, "the reflux condenser's pressure rises", "peak")),
        900.0, ("urea carry-over and fouling",)),
    Deviation(
        "S3-6.1a", "Scenarios3.md §6.1", "Rectifying column pressure increased",
        "323C003 rides on 323E003's pressure: PIC-323202 3.2 -> 3.6 bar a",
        (_sp("PIC-323202", 3.6),),
        (E("RECIRC_323.C003.P_bara", +1, "the column's pressure rises"),
         E("RECIRC_323.C003.PIC_329202.op", +1, "the LP heater needs more steam"),
         E("LPCC_3232.E003.vent321_th", -1, "less venting from the LPCC")),
        900.0),
    Deviation(
        "S3-6.1b", "Scenarios3.md §6.1", "Rectifying column pressure decreased",
        "PIC-323202 3.2 -> 2.8 bar a",
        (_sp("PIC-323202", 2.8),),
        (E("RECIRC_323.C003.P_bara", -1, "the column's pressure falls"),
         E("RECIRC_323.C003.PIC_329202.op", -1, "less steam"),
         E("LPCC_3232.E003.vent321_th", +1, "massive venting from the LPCC")),
        900.0),

    # ==================================================================================
    # Scenarios4.md — valve steps
    # ==================================================================================
    Deviation(
        "S4-steam-open", "Scenarios4.md, steam supply", "MP supply valve: huge opening",
        "PV-329204 (25 bar to 329D005) in MAN 44 -> 90 %",
        ({"type": "pic329204_set", "mode": "MAN", "op": 90.0},),
        (E("STEAM_SYSTEM.MP.P_bara", +1, "the MP header floods"),
         E("STRIP_322E001.steam.duty_kW", +1, "the stripper takes more")),
        600.0),
    Deviation(
        "S4-steam-close", "Scenarios4.md, steam supply", "MP supply valve: huge closing",
        "PV-329204 in MAN 44 -> 5 %",
        ({"type": "pic329204_set", "mode": "MAN", "op": 5.0},),
        (E("STEAM_SYSTEM.MP.P_bara", -1, "the MP header collapses"),
         E("STRIP_322E001.steam.duty_kW", -1, "stripping halts"),
         E("STRIP_322E001.bot_mass_pct.NH3", +1, "carbamate passes undecomposed")),
        600.0),
    Deviation(
        "S4-letdown-open", "Scenarios4.md, 9-bar letdown", "9-bar letdown: huge opening",
        "PIC-329205 in MAN, its split range to PV-329205B 100 %",
        ({"type": "pic329205_set", "mode": "MAN", "op": 100.0},),
        (E("STEAM_SYSTEM.DRUM_9BAR.P_bara", -1, "the 9-bar inventory collapses"),),
        600.0, ("desuperheating water demand (no desuperheater in the model)",)),
    Deviation(
        "S4-offgas-open", "Scenarios4.md, scrubber off-gas", "Scrubber off-gas valve: huge "
        "opening", "HV-322604 72 -> 100 %",
        ({"type": "hic604_set", "op": 100.0},),
        (E("SCRUB_322E003.P_overflow", -1, "the loop pressure falls"),
         E("SCRUB_322E003.TT_322011_lp", -1, "Joule-Thomson cooling of the let-down")),
        900.0, ("solid carbamate deposition is a flag (CARBAMATE_DEPOSITION)",)),
    Deviation(
        "S4-offgas-close", "Scenarios4.md, scrubber off-gas", "Scrubber off-gas valve: huge "
        "closing", "HV-322604 72 -> 20 %",
        ({"type": "hic604_set", "op": 20.0},),
        (E("SCRUB_322E003.P_overflow", +1, "inerts accumulate"),
         E("REACT_322R001.X_conv", -1, "conversion is suppressed")),
        1800.0),
    Deviation(
        "S4-ejector-close", "Scenarios4.md, ejector motive", "HP ejector: huge closing",
        "HIC-322602 74 -> 20 %",
        ({"type": "hic_set", "value": 20.0},),
        (E("SCRUB_322E003.LT_329501", +1, "un-entrained carbamate backs up into the scrubber"),
         E("EJ_322F001.suction_kgh", -1, "entrainment collapses")),
        900.0),
    Deviation(
        "S4-chest-close", "Scenarios4.md, evaporator steam chest", "Evaporator chest: huge "
        "closing", "PV-329203 shut: PIC-329203 in MAN 0 %",
        (_man("PIC-329203", 0.0),),
        (E("EVAP_324.E001.Q_kW", -1, "evaporation halts"),
         E("EVAP_324.E001.TT_324001", -1, "the melt cools")),
        900.0, ("the note's 'refrigeration to 14 C' is a V1 artefact it reports; the port's "
                "chest duty cannot go negative (report F-10)",)),
)

__all__ = ["SETTLE_S", "SAMPLE_S", "Expect", "Deviation", "DEVIATIONS"]
