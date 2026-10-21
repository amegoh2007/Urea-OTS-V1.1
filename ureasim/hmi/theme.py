"""DCS colour tokens and fonts — one place, so no widget invents a colour.

Parity note
-----------
These are the exact values from V1's `frontend/index.html` ``:root`` block and the overlay
stylesheet. Operators are trained on colour: green means running, magenta means the NH3
line, yellow means an armed interlock. Changing any of these changes what the screen
*means*, so they are transcribed rather than re-chosen.

Anything that needs a colour imports it from here. A literal ``#22ff22`` anywhere else in
`ureasim.hmi` is a defect.
"""

from __future__ import annotations

# ======================================================================================
# Process-graphic palette (V1 :root custom properties)
# ======================================================================================

#: Stage background — the teal every process screen sits on.
BG = "#1d4d52"

#: Page background behind the stage.
PAGE_BG = "#0a1416"

#: Classic process-indicator box: black field, white frame, white text.
PI_BG = "#000000"
PI_BORDER = "#ffffff"
PI_TEXT = "#ffffff"
PI_ALARM = "#ff3030"

#: Running / energised green, and the darker "commanded off" green.
BTN_GREEN = "#22ff22"
BTN_OFF = "#0aa64d"

#: Process line colours — these encode WHICH fluid a line carries.
LINE_NH3 = "#ff00ff"      # liquid ammonia
LINE_CPL = "#22d622"      # clean process liquid
LINE_CARB = "#ff9a3c"     # carbamate
SIGNAL = "#9bbabb"        # instrument signal
RATIO = "#2e8a8f"         # ratio-block signal

# ======================================================================================
# Overlay element colours
# ======================================================================================

#: Live indicator: dark field, near-white frame, pale green value text.
IND_BG = "#04110d"
IND_BORDER = "#e8f4f0"
IND_TEXT = "#d6f3e4"
IND_UNIT = "#82b3a3"

#: Empty slot — a tag the drawing publishes but the engine does not yet model. It is drawn
#: as a WHITE FRAME with the tag text and no value, so an unmodelled instrument is visibly
#: unmodelled rather than silently showing a stale number.
IND_EMPTY_BG = "rgba(8, 16, 14, 115)"
IND_EMPTY_BORDER = "#ffffff"
IND_EMPTY_TEXT = "#eeeeff"

#: A box that opens a faceplate is outlined in cyan.
IND_FACEPLATE_BORDER = "#7fd0d8"

#: Controller mode badge colours (A auto, E cascade, M manual, O out of service).
MODE_COLOURS = {
    "A": "#5fe08f",
    "E": "#7fd0d8",
    "M": "#e0b85f",
    "O": "#e06f6f",
}

#: Full mode names, for tooltips.
MODE_NAMES = {"A": "AUTO", "M": "MAN", "E": "CAS", "O": "OOS"}

#: Level bargraph.
BAR_BG = "#04110d"
BAR_BORDER = "#e8f4f0"
BAR_FILL = BTN_GREEN
BAR_EMPTY_BORDER = "#ffffff"

#: Analyser element (AE-*) — composition readout.
AE_BG = "#0c1a28"
AE_BORDER = "#2f5a78"
AE_TEXT = "#8fd0ff"
AE_HOVER_BG = "#1a2e42"
AE_HOVER_BORDER = "#4aa587"
AE_HOVER_TEXT = "#aff0ff"

#: Interlock override pushbutton.
OVRD_BG = "#1a1208"
OVRD_BORDER = "#6b5a2f"
OVRD_TEXT = "#cdbb78"
OVRD_LAMP_IDLE = "#3a3320"
OVRD_ARMED = "#ffd000"
OVRD_ARMED_BG = "#241a06"

#: Hand switch beside a block valve.
HS_BG = "#1a2808"
HS_BORDER = "#4a6b2f"
HS_TEXT = "#a0e060"

#: Hover highlight for transparent hotspots (nav, stream).
HOTSPOT_HOVER_BORDER = "rgba(127, 208, 216, 217)"
HOTSPOT_HOVER_BG = "rgba(80, 160, 220, 41)"

#: Edit-layout mode outlines.
EDIT_OUTLINE = "#ffd000"
EDIT_NAV_OUTLINE = "rgba(255, 208, 0, 153)"
EDIT_STREAM_OUTLINE = "rgba(255, 160, 60, 178)"


def rgba(spec: str) -> tuple[int, int, int, int]:
    """A CSS ``rgba(r, g, b, a)`` token as the four integers a ``QColor`` takes.

    ``QColor`` does not parse the CSS form: handed ``"rgba(80, 160, 220, 41)"`` it is invalid
    and paints opaque black, which is what blacked out a hovered nav button over the label it
    sits on (fixed 2026-10-16). A painter takes these tokens through this function; a Qt
    stylesheet, which does parse the CSS form, takes them as they are.
    """
    body = spec.strip()
    if not (body.startswith("rgba(") and body.endswith(")")):
        raise ValueError(f"not an rgba() colour token: {spec!r}")
    parts = [int(p) for p in body[5:-1].split(",")]
    if len(parts) != 4:
        raise ValueError(f"not an rgba() colour token: {spec!r}")
    return parts[0], parts[1], parts[2], parts[3]

# ======================================================================================
# Tab bar and chrome
# ======================================================================================

TAB_BAR_BG = "#0c2b2e"
TAB_BG = "#1b4a4f"
TAB_TEXT = "#cfeff1"
TAB_BORDER = "#2f6f75"
TAB_HOVER_BG = "#27666d"
TAB_ACTIVE_TEXT = "#ffd000"
TAB_ACTIVE_BORDER = "#7fd0d8"

PANEL_BG = "#13202c"
PANEL_BORDER = "#2f4858"
PANEL_TEXT = "#cfe"

#: Health LED states.
HEALTH_OK = "#22ff22"
HEALTH_WARN = "#ffb000"
HEALTH_FAULT = "#ff3030"
HEALTH_IDLE = "#3a6b4e"

# ======================================================================================
# Faceplates and the instructor panel (V1's ``.modal`` stylesheet)
# ======================================================================================

FP_BG = "#1b2a30"
FP_TEXT = "#ffffff"
FP_BORDER = "#888888"

#: An entry field, a read-only field, a field the mode does not use, a value expanded to 3 dp.
FP_FIELD_BG = "#000000"
FP_FIELD_TEXT = "#ffffff"
FP_READONLY_BG = "#0a0a0a"
FP_READONLY_TEXT = "#7fd6ff"
FP_DISABLED_TEXT = "#666666"
FP_DISABLED_BORDER = "#3a3a3a"
FP_EXPANDED_TEXT = "#ffd27f"

#: Buttons: plain, the primary (SET / START), the active mode, and a dead one — a command the
#: plant is already in reads colourless.
FP_BUTTON_BG = "#2a4046"
FP_BUTTON_BORDER = "#aaaaaa"
FP_PRIMARY_BG = BTN_OFF
FP_ACTIVE_BORDER = BTN_GREEN
FP_DEAD_TEXT = "#777777"
FP_DEAD_BORDER = "#555555"

#: The cause-and-effect note, the cascade note, the loop's status flags, and the outcome of the
#: last command (accepted / refused).
FP_NOTE_TEXT = TAB_TEXT
FP_CAS_NOTE_TEXT = FP_EXPANDED_TEXT
FP_STATUS_TEXT = "#ff5252"
FP_MSG_OK = "#7fffae"
FP_MSG_FAULT = "#ff7f7f"

#: The live mode chip on a faceplate's title: MAN red, AUTO green, CAS yellow, OOS orange; the
#: MASTER SP chip red OFF, green ON.
FP_MODE_COLOURS = {"MAN": PI_ALARM, "AUTO": BTN_GREEN, "CAS": OVRD_ARMED, "OOS": "#ff8a3d",
                   "OFF": PI_ALARM, "ON": BTN_GREEN}

#: The caption under a sub-controller's tag on the MASTER SP faceplate.
FP_CAPTION_TEXT = AE_TEXT

FP_FONT_PX = 13
FP_TITLE_PX = 14

#: The stream inspector's cell borders (V1 ``index.html`` ``#streamModal td``: 1px #555, monospace
#: text on the modal's card).
SI_CELL_BORDER = "#555555"

# ======================================================================================
# The trend window (V1's ``trend.js`` palette and ``#trendwin`` stylesheet)
# ======================================================================================

#: The ten pens, in slot order: the DCS tokens first, then distinct additions.
TREND_PENS = ("#22ff22", "#7fd0d8", "#ffd000", "#ff9a3c", "#ff00ff",
              "#5fe08f", "#e06f6f", "#9bbabb", "#c78fff", "#ffffff")
#: The ten rulers, well apart on the dark plot; each is labelled R1 ... R10 as well.
TREND_RULERS = ("#ffd000", "#41e0ff", "#ff5db1", "#7CFC00", "#ff8c1a",
                "#b47cff", "#ff4d4d", "#2ee6a6", "#f0f0f0", "#7aa5ff")
#: An unmarked pen fades to this alpha [0-255] while another is marked (V1's ``+40``).
TREND_FADE_ALPHA = 0x40
#: Pen widths [px]: plain and marked.
TREND_PEN_W = 1.4
TREND_PEN_W_MARKED = 3.2

TW_BG = PANEL_BG
TW_PLOT_BG = PAGE_BG
TW_BAR_BG = "#0f1a24"
TW_BORDER = "#2a4a44"
TW_ACCENT = "#4aa587"
TW_GRID = "#1e3a34"
TW_TICK = "#8fb3ab"
TW_PLANT_TITLE = "#5fe08f"
TW_DESK_TICK = "#7f9ba8"
TW_Y_TICK = IND_TEXT
TW_LABEL = IND_UNIT
TW_BUTTON_BG = FP_BG
TW_BUTTON_TEXT = "#9bbabb"
TW_NAV_TEXT = "#7fd0d8"
TW_SPAN_ON_BG = BTN_OFF
TW_SPAN_ON_BORDER = BTN_GREEN
TW_LIVE_BG = "#0b2b1a"
TW_LIVE_TEXT = "#5fe08f"
TW_HIST_BG = "#3a2f08"
TW_HIST_TEXT = OVRD_ARMED
TW_NOHIST_BG = "#3a2a08"
TW_NOHIST_BORDER = "#b3892f"
TW_NOHIST_TEXT = FP_EXPANDED_TEXT
TW_FLASH_BG = "#3a0d0d"
TW_FLASH_TEXT = "#ff8a8a"
TW_VALUE_TEXT = "#ffffff"
TW_MIN_TEXT = "#7fd0d8"
TW_MAX_TEXT = "#ff9a3c"
TW_AVG_TEXT = PANEL_TEXT
TW_EMPTY_TEXT = "#54706c"
TW_ROW_MARKED_BG = "#16323a"
TW_REMOVE_TEXT = "#e06f6f"

# ======================================================================================
# Fonts
# ======================================================================================

#: Value font. Tabular figures matter: a digit that changes width makes a live readout
#: jitter, which on a 10 Hz screen reads as noise.
VALUE_FONT_FAMILIES = ["Cascadia Mono", "Consolas", "Segoe UI Mono", "Courier New"]
VALUE_FONT_PX = 14
VALUE_FONT_PX_EMPTY = 9
UNIT_FONT_PX = 12
MODE_FONT_PX = 8

#: Chrome font.
UI_FONT_FAMILIES = ["Segoe UI", "Arial", "Helvetica"]
UI_FONT_PX = 12


def value_font_stack() -> str:
    """CSS-style family list for the value font, for use in a Qt stylesheet."""
    return ", ".join(f'"{f}"' for f in VALUE_FONT_FAMILIES)


def ui_font_stack() -> str:
    """CSS-style family list for the chrome font."""
    return ", ".join(f'"{f}"' for f in UI_FONT_FAMILIES)


__all__ = [n for n in dir() if not n.startswith("_")]
