"""The equipment and the connections of the Plant Hover Flyby, taken from the flow sheets 322-1 and 322-2.

Plant equipment modelled
------------------------
The urea synthesis (HP loop) of unit 322 and what it is joined to on the two sheets: 322R001 reactor,
322E001 HP stripper, 322E002 HP carbamate condenser, 322E003 HP scrubber, 322F001 HP ejector, 322D001
steam drum, 322C001 LP absorber, 323C003 rectifying column, 320K002 CO2 compressor, the pump sets
321P002 A/B, 323P001 A/B and 329P006 A/B, the cooler 329E004, and the tagged valves on the lines.
Nothing is computed: the flyby shows the equipment and the order of its connections, never a value.

Reference documents
-------------------
* The flow sheets ``322-1 UREA SYNTHESIS`` and ``322-2 UREA SYNTHESIS HP SCRUBBER`` (two slides,
  supplied 2026-11-03): every item, every line, the arrow on it, its colour (the stream) and the tagged
  valve on it. Read from the slides' shapes: line ends, arrow heads, colours.
* ``project.md`` section 1 (plant scope table) for what each tag is (322F001 is the HP ejector, 322F001's
  discharge feeds 322E002's top channel with the stripper's top gas, 320K002 is a boundary feed outside
  the simulation) and ``As-Built Mathematical Reference.md`` Parts XXIII and XXV (322E002's shell raises
  steam from 322D001 water; 322E003's shell is a tempered cooling-water loop circulated by 329P006 A/B
  with FIC-329409 on the rate and TIC-329005 on the supply temperature).

Equations
---------
None. **Layout is a design choice**: the positions, heights and radii of the model are invented to make
the order of the connections readable from every side of the orbit; they are not the plant's drawings,
not to scale, and the flyby says so on screen. What is not a choice is the connection: each pipe below
runs from the equipment the slide's line leaves to the equipment its arrow enters, through the tagged
valves in the order the slide draws them. Lengths are in the model units (mu) of ``intro_flyby.py``.

Where the slides leave something open
-------------------------------------
* The slides draw 322D001 as two boxes (steam out, water in); project.md lists 322D001 A/B. One drum is
  drawn, labelled 322D001, with both lines on it.
* 322F001 is a box on 322-1 and the pink ejector symbol (spindle HV-322602) on 322-2; it is drawn once,
  on the line between 321P002 A/B plus the 322E003 overflow and the top of 322E002.
* Unlabelled valves and every instrument (transmitters, controllers, level column) are not drawn.
"""

from __future__ import annotations

from dataclasses import dataclass

Point3 = tuple[float, float, float]
_SLIDES = "flow sheets 322-1 and 322-2 (supplied 2026-11-03); layout and dimensions are a design choice, not to scale"


@dataclass(frozen=True)
class Vessel:
    """A vertical cylinder with a domed top: reactor, stripper, condenser, columns."""

    tag: str
    role: str
    x: float
    y: float
    radius: float
    height: float
    dome: float
    rings: int
    sides: int
    label: Point3
    source: str = _SLIDES


@dataclass(frozen=True)
class Scrubber:
    """322E003 as drawn on 322-2: a long narrow shaft carrying a wide domed head."""

    tag: str
    role: str
    x: float
    y: float
    shaft_radius: float
    shaft_height: float
    dome_radius: float
    dome_height: float
    label: Point3
    source: str = _SLIDES


@dataclass(frozen=True)
class Drum:
    """A horizontal cylinder along x: steam drum, ejector, cooler."""

    tag: str
    role: str
    x: float
    y: float
    z: float
    length: float
    radius: float
    rings: int
    sides: int
    label: Point3
    source: str = _SLIDES


@dataclass(frozen=True)
class Block:
    """A box: the CO2 compressor house."""

    tag: str
    role: str
    x: float
    y: float
    w: float
    d: float
    h: float
    bands: int
    bays: int
    label: Point3
    source: str = _SLIDES


@dataclass(frozen=True)
class PumpPair:
    """Two parallel pumps A and B on a common suction and a common discharge, axes along x."""

    tag: str
    role: str
    x: float
    y: float
    stream: str
    label: Point3
    spacing: float = 10.0
    casing_radius: float = 3.0
    motor_length: float = 9.0
    motor_radius: float = 2.2
    stub: float = 4.0
    lift: float = 5.0
    source: str = _SLIDES


@dataclass(frozen=True)
class Stream:
    """A stream colour of the flow sheets: the colour of the line, darkened to read on the paper."""

    name: str
    sheet_color: str
    color: str
    meaning: str
    source: str = (
        "sheet_color is the line colour read from flow sheets 322-1 and 322-2 (gas FFFF00, steam FF0000, "
        "water theme accent6 4EA72E, liquid theme accent5 A02B93 lightened to D86ECC); color is the same "
        "hue darkened to read on the light paper, a design choice"
    )


@dataclass(frozen=True)
class Valve:
    """A tagged valve on segment ``segment`` (0-based) of a pipe, at the middle of that segment."""

    tag: str
    segment: int
    control: bool
    source: str = _SLIDES


@dataclass(frozen=True)
class Pipe:
    """One line of the flow sheets, from the equipment it leaves to the equipment its arrow enters.

    ``start`` and ``end`` are a port key ``"TAG.port"`` or a literal point (a tee on another pipe, or a
    boundary of the drawing). ``via`` are the bends in between; every leg runs along one axis.
    """

    name: str
    stream: str
    src: str
    dst: str
    start: str | Point3
    end: str | Point3
    via: tuple[Point3, ...] = ()
    valves: tuple[Valve, ...] = ()
    source: str = _SLIDES


@dataclass(frozen=True)
class Boundary:
    """Where a line leaves or enters the drawing (an arrow at the edge of the slide)."""

    name: str
    at: Point3
    source: str = _SLIDES


STREAMS: tuple[Stream, ...] = (
    Stream("gas", "#FFFF00", "#D6A100", "CO2, NH3 and inert vapour"),
    Stream("liquid", "#D86ECC", "#C23D9E", "carbamate, NH3 and urea solution"),
    Stream("steam", "#FF0000", "#D83A2E", "steam"),
    Stream("water", "#4EA72E", "#3F9B3C", "boiler feed water, condensate and cooling water"),
)

REACTOR = Vessel("322R001", "reactor", -55.0, 0.0, 8.0, 80.0, 6.0, 6, 12, (-55.0, 0.0, 94.0))
VESSELS: tuple[Vessel, ...] = (
    Vessel("322E002", "HP carbamate condenser", 5.0, 0.0, 6.5, 50.0, 5.0, 4, 12, (5.0, 0.0, 62.0)),
    Vessel("322E001", "HP stripper", 62.0, 0.0, 7.0, 44.0, 5.0, 3, 12, (62.0, 0.0, 56.0)),
    Vessel("323C003", "rectifying column", 125.0, 0.0, 6.0, 64.0, 5.0, 5, 12, (125.0, 0.0, 75.0)),
    Vessel("322C001", "LP absorber", -10.0, 96.0, 5.0, 48.0, 4.0, 3, 12, (-10.0, 96.0, 59.0)),
)
SCRUBBER = Scrubber("322E003", "HP scrubber", -55.0, 48.0, 5.0, 48.0, 11.0, 8.0, (-55.0, 48.0, 70.0))
DRUMS: tuple[Drum, ...] = (
    Drum("322D001", "steam drum", 30.0, 30.0, 66.0, 24.0, 5.0, 2, 12, (30.0, 30.0, 75.0)),
    Drum("322F001", "HP ejector", -22.0, 17.0, 60.0, 14.0, 1.8, 1, 8, (-22.0, 17.0, 67.0)),
    Drum("329E004", "scrubber water cooler", -16.0, 57.0, 32.0, 14.0, 3.0, 2, 10, (-16.0, 57.0, 38.0)),
)
BLOCKS: tuple[Block, ...] = (Block("320K002", "CO2 compressor", -20.0, -48.0, 24.0, 10.0, 7.0, 1, 4, (-20.0, -48.0, 15.0)),)
PUMPS: tuple[PumpPair, ...] = (
    PumpPair("321P002A/B", "NH3 pumps", -96.0, 17.0, "liquid", (-96.0, 17.0, 17.0)),
    PumpPair("323P001A/B", "LP carbamate pumps", -100.0, 67.0, "liquid", (-100.0, 67.0, 17.0)),
    PumpPair("329P006A/B", "scrubber water pumps", -28.0, 66.0, "water", (-28.0, 66.0, 17.0)),
)

# Nozzles on the surface of the equipment above (pump pairs derive theirs, see model3d.resolve_ports).
PORTS: dict[str, Point3] = {
    "322R001.top": (-55.0, 0.0, 86.0),
    "322R001.in_bottom": (-47.0, 0.0, 5.0),
    "322R001.liquid_out": (-55.0, -8.0, 5.0),
    "322E002.top_left": (2.5, 0.0, 54.62),
    "322E002.top_right": (7.5, 0.0, 54.62),
    "322E002.bottom_out": (-1.5, 0.0, 5.0),
    "322E002.steam_out": (11.5, 0.0, 38.0),
    "322E002.water_in": (11.5, 0.0, 24.0),
    "322E001.top": (62.0, 0.0, 49.0),
    "322E001.liquid_in": (55.0, 0.0, 36.0),
    "322E001.co2_in": (62.0, -7.0, 5.0),
    "322E001.bottom_out": (62.0, 7.0, 3.0),
    "322E001.steam_in": (69.0, 0.0, 30.0),
    "322E001.cond_out": (69.0, 0.0, 12.0),
    "323C003.feed_in": (125.0, 6.0, 30.0),
    "322C001.top_in": (-10.0, 96.0, 52.0),
    "322E003.gas_in": (-55.0, 40.0, 60.4),
    "322E003.carb_in": (-65.0, 48.0, 58.27),
    "322E003.overflow": (-45.47, 48.0, 50.93),
    "322E003.vent": (-55.0, 48.0, 62.93),
    "322E003.recirc_out": (-55.0, 57.53, 50.93),
    "322E003.recirc_in": (-55.0, 53.0, 1.5),
    "322E003.cw_out": (-50.0, 48.0, 3.5),
    "322E003.cw_in": (-50.0, 48.0, 24.0),
    "322D001.steam_in": (24.0, 30.0, 61.0),
    "322D001.water_out": (36.0, 30.0, 61.0),
    "322F001.motive_in": (-29.0, 17.0, 60.0),
    "322F001.suction": (-22.0, 18.8, 60.0),
    "322F001.out": (-15.0, 17.0, 60.0),
    "329E004.in": (-23.0, 57.0, 32.0),
    "329E004.out": (-9.0, 57.0, 32.0),
    "320K002.discharge": (-8.0, -48.0, 5.0),
}

BOUNDARIES: tuple[Boundary, ...] = (
    Boundary("EXTR STEAM", (96.0, 0.0, 30.0)),
    Boundary("CONDENSATE", (96.0, 0.0, 12.0)),
    Boundary("VENT", (0.0, -48.0, 22.0)),
)

PIPES: tuple[Pipe, ...] = (
    Pipe("CO2 to stripper", "gas", "320K002", "322E001", "320K002.discharge", "322E001.co2_in", ((62.0, -48.0, 5.0),), (Valve("XV-322902", 0, False),)),
    Pipe("CO2 vent", "gas", "320K002", "@VENT", (0.0, -48.0, 5.0), (0.0, -48.0, 22.0), (), (Valve("PV-322203", 0, True),)),
    Pipe(
        "NH3 to ejector", "liquid", "321P002A/B", "322F001", "321P002A/B.discharge", "322F001.motive_in",
        ((-84.0, 17.0, 11.5), (-84.0, 17.0, 60.0)), (Valve("XV-322903", 1, False),),
    ),
    Pipe(
        "scrubber overflow to ejector", "liquid", "322E003", "322F001", "322E003.overflow", "322F001.suction",
        ((-22.0, 48.0, 50.93), (-22.0, 48.0, 60.0)),
    ),
    Pipe("ejector to condenser", "liquid", "322F001", "322E002", "322F001.out", "322E002.top_left", ((2.5, 17.0, 60.0), (2.5, 0.0, 60.0))),
    Pipe("stripper gas to condenser", "gas", "322E001", "322E002", "322E001.top", "322E002.top_right", ((62.0, 0.0, 70.0), (7.5, 0.0, 70.0))),
    Pipe("condenser to reactor", "liquid", "322E002", "322R001", "322E002.bottom_out", "322R001.in_bottom"),
    Pipe(
        "reactor to stripper", "liquid", "322R001", "322E001", "322R001.liquid_out", "322E001.liquid_in",
        ((-55.0, -16.0, 5.0), (40.0, -16.0, 5.0), (40.0, -16.0, 36.0), (40.0, 0.0, 36.0)), (Valve("HV-322605", 1, True),),
    ),
    Pipe("reactor gas to scrubber", "gas", "322R001", "322E003", "322R001.top", "322E003.gas_in", ((-55.0, 40.0, 86.0),)),
    Pipe(
        "carbamate to scrubber", "liquid", "323P001A/B", "322E003", "323P001A/B.discharge", "322E003.carb_in",
        ((-94.0, 67.0, 11.5), (-94.0, 67.0, 58.27), (-94.0, 48.0, 58.27)),
    ),
    Pipe(
        "scrubber vent to absorber", "gas", "322E003", "322C001", "322E003.vent", "322C001.top_in",
        ((-55.0, 48.0, 75.0), (-55.0, 96.0, 75.0), (-10.0, 96.0, 75.0)), (Valve("HV-322604", 2, True),),
    ),
    Pipe("scrubber gas recirculation", "gas", "322E003", "322E003", "322E003.recirc_out", "322E003.recirc_in", ((-55.0, 64.0, 50.93), (-55.0, 64.0, 1.5))),
    Pipe(
        "stripper bottoms to column", "liquid", "322E001", "323C003", "322E001.bottom_out", "323C003.feed_in",
        ((62.0, 16.0, 3.0), (125.0, 16.0, 3.0), (125.0, 16.0, 30.0)), (Valve("LV-322501", 1, True),),
    ),
    Pipe("steam to drum", "steam", "322E002", "322D001", "322E002.steam_out", "322D001.steam_in", ((24.0, 0.0, 38.0), (24.0, 30.0, 38.0))),
    Pipe("drum water to condenser", "water", "322D001", "322E002", "322D001.water_out", "322E002.water_in", ((36.0, 30.0, 24.0), (36.0, 0.0, 24.0))),
    Pipe("extraction steam to stripper", "steam", "@EXTR STEAM", "322E001", (96.0, 0.0, 30.0), "322E001.steam_in"),
    Pipe("stripper condensate out", "water", "322E001", "@CONDENSATE", "322E001.cond_out", (96.0, 0.0, 12.0)),
    Pipe("scrubber water to pumps", "water", "322E003", "329P006A/B", "322E003.cw_out", "329P006A/B.suction", ((-35.0, 48.0, 3.5),)),
    Pipe(
        "pumps to scrubber water inlet", "water", "329P006A/B", "322E003", "329P006A/B.discharge", "322E003.cw_in",
        ((-28.0, 66.0, 24.0), (-28.0, 48.0, 24.0)), (Valve("FV-329409", 2, True),),
    ),
    Pipe("water to cooler", "water", "329P006A/B", "329E004", (-28.0, 57.0, 24.0), "329E004.in", ((-28.0, 57.0, 32.0),)),
    Pipe(
        "cooler to scrubber water inlet", "water", "329E004", "322E003", "329E004.out", (-45.0, 48.0, 24.0),
        ((-9.0, 57.0, 40.0), (-45.0, 57.0, 40.0), (-45.0, 48.0, 40.0)), (Valve("TV-329005", 0, True),),
    ),
)
