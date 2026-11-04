"""Constants of the start-up intro.

Plant equipment modelled
------------------------
None. The intro is presentation: it shows the company mark, the simulator's name, the plant
sections the console carries and a stylized flyby of the plant (its constants are in
``intro_flyby.py``). It computes no process quantity and reads no engine value.

Reference documents
-------------------
* ``project.md`` section 1 (plant scope table): the six plant sections and their unit numbers.
* ``project.md`` section 3.4: the V1 screens are 1366 x 720 stages; the intro's design space is the
  same stage, so the intro and the DCS screens share one coordinate frame.
* ``hfc-logo.png`` (Helwan Fertilizers Co. mark, supplied with the request): the pixel regions and the
  brand colours were measured on that file.

Equations
---------
None. Every number below is a design choice or a measurement on the logo file; each group names its
own ``source``. Time is in seconds, lengths in design pixels of the 1366 x 720 stage.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

Window = tuple[float, float]
Region = tuple[float, float, float, float]  # x, y, width, height


@dataclass(frozen=True)
class Stage:
    """The design space every intro coordinate lives in."""

    width: float = 1366.0
    height: float = 720.0
    source: str = "project.md section 3.4: V1 screens are 1366 x 720 stages"


@dataclass(frozen=True)
class Palette:
    """Colours of the intro; the brand pair is read off the logo, the rest is derived from it."""

    paper_top: str = "#F8FAF9"
    paper_bottom: str = "#E8EEED"
    orange: str = "#EB8629"
    teal: str = "#3A8277"
    teal_deep: str = "#1F5A58"
    slate: str = "#5C7775"
    white: str = "#FFFFFF"
    source: str = (
        "hfc-logo.png: orange is the dominant HFC letter colour (235, 134, 41), teal the company-name "
        "colour (58, 130, 119); paper, teal_deep and slate are tones derived from them by the design"
    )


@dataclass(frozen=True)
class Timeline:
    """When each element of the intro appears; ``hold`` is the last scene frame, ``fade`` the exit."""

    backdrop_in: Window = (0.00, 0.60)
    emblem: Window = (0.60, 1.50)
    ring_a: Window = (1.05, 2.05)
    ring_b: Window = (1.25, 2.25)
    letters: Window = (1.30, 2.10)
    name_en: Window = (1.90, 2.50)
    name_ar: Window = (2.10, 2.70)
    divider: Window = (2.60, 3.20)
    title_1: Window = (2.95, 3.85)
    title_2: Window = (3.35, 4.15)
    subtitle: Window = (4.05, 4.65)
    track_in: Window = (3.90, 4.40)
    ribbon_run: Window = (4.40, 6.80)
    hint_in: Window = (1.00, 1.60)
    button_in: Window = (6.90, 7.50)
    hold: float = 7.60
    fade: float = 0.60
    source: str = (
        "design choice: the scene runs 7.6 s and holds on its last frame until the operator presses the "
        "start button; a key press or click before then skips to that frame; the exit fade is 0.6 s"
    )


@dataclass(frozen=True)
class Logo:
    """Where the logo's four pieces sit in the file and on the stage."""

    name: str = "hfc-logo"
    atlas_width: float = 1280.0
    atlas_height: float = 602.0
    width: float = 480.0
    top: float = 70.0
    emblem: Region = (0.0, 0.0, 484.0, 382.0)
    letters: Region = (572.0, 0.0, 708.0, 382.0)
    name_en: Region = (572.0, 412.0, 708.0, 92.0)
    name_ar: Region = (572.0, 504.0, 708.0, 98.0)
    source: str = (
        "hfc-logo.png (1280 x 602, RGBA): the supplied 640 x 301 mark (md5 f66903d8fa9929a07314077ef0ea35bc, "
        "kept in the intro's source folder) resampled exactly 2x on premultiplied alpha with Lanczos, each "
        "output pixel then clamped to the range of its 3 x 3 source neighbourhood, which removes the ringing "
        "and halo Lanczos alone leaves (an overshoot of up to 46 in 255 before the clamp); the regions are the "
        "supplied file's, measured there (ink columns 0-241 and 286-639, rows 0-190, 212-245 and 257-300), "
        "doubled. A resample adds no detail: it keeps full-screen playback from scaling the source up, and a "
        "vector mark from HFC would be the real sharpening (session 85, A-25 point 5)"
    )


@dataclass(frozen=True)
class TitleLayout:
    """Where the text column stands and the vertical rhythm of the divider and the lines under the logo."""

    cx: float = 330.0
    divider_y: float = 322.0
    divider_half_width: float = 210.0
    line_1_y: float = 372.0
    line_1_size: float = 44.0
    line_1_spacing: float = 13.0
    line_1_spacing_start: float = 32.0
    line_2_y: float = 418.0
    line_2_size: float = 19.0
    line_2_spacing: float = 6.0
    line_2_spacing_start: float = 16.0
    subtitle_y: float = 452.0
    subtitle_size: float = 14.0
    subtitle_spacing: float = 4.0
    footer_y: float = 696.0
    footer_size: float = 11.0
    footer_spacing: float = 3.0
    footer_margin: float = 40.0
    source: str = (
        "design choice (no plant datum): the logo, titles and button stand in a column centred at cx, in the "
        "left third of the stage, so the Plant Hover Flyby has the right two-thirds to itself"
    )


@dataclass(frozen=True)
class RibbonLayout:
    """The plant-section ribbon along the foot of the stage."""

    y: float = 626.0
    track_start_x: float = 103.0
    track_end_x: float = 1263.0
    first_node_x: float = 183.0
    node_spacing: float = 200.0
    node_radius: float = 11.0
    number_dy: float = -30.0
    name_dy: float = 30.0
    number_size: float = 15.0
    name_size: float = 11.0
    name_spacing: float = 2.0
    particle_count: int = 14
    particle_speed: float = 150.0
    source: str = "design choice (no plant datum)"


@dataclass(frozen=True)
class ButtonLayout:
    """The start button under the subtitle, in design pixels."""

    center_y: float = 522.0
    width: float = 250.0
    height: float = 56.0
    label_size: float = 19.0
    label_spacing: float = 4.0
    label_dx: float = 14.0
    icon_dx: float = -81.0
    icon_half_height: float = 7.0
    ring_gap: float = 5.0
    rise: float = 8.0
    source: str = "design choice (no plant datum)"


@dataclass(frozen=True)
class StartOption:
    """The one way the intro offers to start the simulator."""

    key: str = "load_100"
    label: str = "100% LOAD"
    source: str = (
        "request of the process engineer (2026-11-02): the intro ends with a '100% load' button that "
        "starts the simulator; 100 % load is the 1750 MTPD design basis of project.md section 1"
    )


@dataclass(frozen=True)
class Strings:
    """Texts of the intro."""

    title_1: str = "UREA PLANT"
    title_2: str = "OPERATOR TRAINING SIMULATOR"
    subtitle: str = "1750 MTPD  ·  CO2 STRIPPING PROCESS"
    version: str = "V1.1"
    hint: str = "PRESS ANY KEY TO SKIP"
    start_hint: str = "PRESS ENTER TO START"
    starting: str = "Starting simulator"
    source: str = (
        "project.md section 1: 1750 MTPD CO2-stripping urea plant of Helwan Fertilizers Company; "
        "project.md header: Version 1.1"
    )


@dataclass(frozen=True)
class Section:
    """One plant section the console carries, in the order of the scope table."""

    number: str
    name: str
    source: str = "project.md section 1, plant scope table"


@dataclass(frozen=True)
class Startup:
    """How the application starts the plant once the start button is pressed.

    The engine is built and held at its design seed while the intro plays (``run.py``); the press builds
    the console, connects it and releases the hold, and the console is shown when its first packet
    arrives. These are the texts the intro shows meanwhile and the longest the application waits for
    each step before it shows the console anyway, so the status bar tells the operator what is wrong
    instead of the intro waiting for ever.
    """

    building: str = "Building screens"
    engine: str = "Starting engine"
    connecting: str = "Connecting to the engine"
    releasing: str = "Starting the plant"
    poll_ms: int = 50
    watch_ms: int = 250
    engine_timeout_s: float = 60.0
    packet_timeout_s: float = 45.0
    source: str = (
        "design choice (no plant datum); engine_timeout_s is run.py's own 60 s wait for the engine; "
        "packet_timeout_s is 15 s beyond the bridge's FIRST_PACKET_STALE_MS (30 s, itself more than ten times "
        "the 2.3 s a cold first tick took on the development machine, session 84), so the bridge's own "
        "watchdog speaks first"
    )


#: The engine command each start key sends. The plant is built at the design seed (the 1750 MTPD
#: design basis, 100 % load) and held by the engine's own freeze (``freeze``, ``on`` always stated,
#: because a missing ``on`` toggles); the 100 % LOAD button releases that hold. The command is the
#: engine's existing one, the one the instructor's RUN button sends, so no new engine behaviour exists.
START_COMMANDS = MappingProxyType({
    "load_100": MappingProxyType({"type": "freeze", "on": False}),
})


STAGE = Stage()
PALETTE = Palette()
TIMELINE = Timeline()
LOGO = Logo()
TITLE = TitleLayout()
RIBBON = RibbonLayout()
STRINGS = Strings()
BUTTON = ButtonLayout()
START_OPTION = StartOption()
STARTUP = Startup()

# The six sections in the order the console's tab bar first reaches them (`screen_layout.SCREENS`: 321-1,
# 322-2, 322-1, 329-1, 323-1, 323-2, 328-1, 328-2, 324-1, 324-1b), so the intro lights them as the operator
# will meet them: 329, the steam system, stands fourth, after synthesis. Decided by the process engineer on
# 2026-11-04 (handoff A-25 point 3); a test derives the order from `SCREENS` and holds the two together.
SECTIONS: tuple[Section, ...] = (
    Section("321", "NH3 PUMPING"),
    Section("322", "UREA SYNTHESIS"),
    Section("329", "STEAM & UTILITIES"),
    Section("323", "LP RECIRCULATION"),
    Section("328", "DESORPTION"),
    Section("324", "EVAPORATION"),
)

# Look of the engineering-drawing grid behind the flyby.
GRID_MINOR = 40.0
GRID_MAJOR_EVERY = 5

# Fonts tried in order; the first one the machine has is used.
FONT_FAMILIES: tuple[str, ...] = ("Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans")

# Repaint period of the splash window (about 60 frames a second).
TICK_MS = 16

# A batch of separate wire segments no wider than this on the device is drawn one device pixel wide with
# its opacity scaled by its width, so the ink (coverage times opacity) is kept. Qt rasterizes a pen of one
# pixel or less on a fast path that costs about 40 % less than the stroker a wider pen needs; measured on
# the hold frame the ink differs by 3.7 % at 125 % display scaling and 1 % at 100 % (session 85).
HAIRLINE_MAX_PX = 1.5
