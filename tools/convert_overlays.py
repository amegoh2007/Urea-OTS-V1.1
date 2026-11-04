"""Convert V1's `frontend/overlays.js` into `ureasim/data/screen_layout.py`.

Why this tool exists
--------------------
V1's HMI is image-backed. Each of the ten process screens is a PowerPoint equipment
drawing exported to a 1366x720 PNG with the live symbols **deleted**, and an overlay
element placed at the exact centre of each deleted shape — so an overlay cannot drift off
its symbol: it lands in the hole the symbol left.

`overlays.js` holds that geometry as a pure declarative table: 387 elements across ten
screens, each carrying the shape's own centre, extent, rotation and mirror, plus its DCS
tag and the dot-path it reads from the state packet.

**Coordinates are never retyped by hand.** That was V1's migration rule and it survives the
rewrite: a hand-typed coordinate is a silent defect that only a pixel comparison catches.
This converter is the only path from the drawing geometry into V1.1. What an element DOES
may be changed by a decision of the process engineer, and only through `DECIDED_EDITS`,
which names the decision beside each edit, or for a whole type through `DECIDED_RETYPES`; where an element sits, only through `NUDGE`, V1's
migration table for the same purpose, each row a decision (handoff A-7); and an element V1's
screens lack is added only through `DECIDED_ADDITIONS`, each a decision (decision 40).

Failure policy
--------------
If a record cannot be parsed, this tool **raises**. It never skips a record. A skipped
overlay is an instrument that silently stops existing, which is exactly the class of
failure the rewrite is meant to remove.

Usage
-----
    python tools/convert_overlays.py [--source <overlays.js>] [--out <screen_layout.py>]

Defaults:
    source  E:\\Simulator\\Urea Simulation\\frontend\\overlays.js
    out     ureasim/data/screen_layout.py
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_SOURCE = Path(r"E:\Simulator\Urea Simulation\frontend\overlays.js")
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "ureasim" / "data" / "screen_layout.py"

#: Element types V1 defines. A record carrying anything else is a parse failure, not a
#: new feature — the widget registry in `hmi/widgets` is keyed on exactly this set.
KNOWN_TYPES = {"ind", "nav", "avalve", "pump", "bar", "strm", "xv", "hs", "ae", "ovrd", "btn"}

#: The process engineer's decisions that change what a screen element DOES, applied to the
#: parsed records before emission: (screen, element key, fields to set — None removes the
#: field). Geometry is never edited here, only in `NUDGE`. A key that is not found raises: an
#: edit that silently stops applying is a decided divergence that silently stops existing.
DECIDED_EDITS = (
    # Handoff B-59, decided 2026-10-01 (project.md decision 40): XV-322915 has no operator open
    # on the DCS. AC4's PC22.5.1 drives it from TT-322015's limit and HS-322915 only, and the
    # loop summaries list no other hand switch for it, so the valve is a status display and the
    # panel's override button is HS-322915, a maintained control-room keyswitch.
    ("screen-328-2", "xv322915", {"cmd": None}),
    ("screen-328-2", "ovrxv322915", {
        "tag": "HS-322915", "cmd": "HS-322915",
        "note": ("HS-322915 OVERRIDE CLOSE, a maintained control-room keyswitch: while it is "
                 "turned XV-322915 stays shut whatever I 22.1's limit says (AC4 PC22.5.1); "
                 "the square is green, red while the override is on, and framed amber while "
                 "TT-322015 is over its limit"),
        # The slide's square (328-2, shape 208, its comment): "the green background turns red"
        # when the override is activated. Decided 2026-10-16 (decision 129).
        "key": "HAND_SWITCHES.HS_322915",
    }),
    # Handoff B-39, decided 2026-10-09 (project.md decision 81): FIC-328402 meters PFD 735,
    # 328P003's feed to 328E007 and the desorbers, where V1 hangs it on 744. The indicator keeps
    # V1's place and binding; only the note V1 wrote for 744 changes.
    ("screen-328-1", "fic328402", {
        "note": ("FIC-328402 on PFD 735, 328P003's feed from 328D003 compartment II to 328E007 and "
                 "the desorbers (31114 kg/h = 31.4 m3/h des), via FV-328402"),
    }),
)

#: The process engineer's decisions that put on a screen a console element V1's screens lack:
#: (screen, the element, its geometry included), appended after the decided edits. Each sits in the
#: free space its drawing leaves beside the equipment it serves, clear of every other element
#: (decision 84).
_KEY_NOTE = ("a maintained control-room keyswitch on AC4 PC21's trip 21.2 (UD-MR-G00-FF-0004): the "
             "lamp is amber while 21.2's flag is lost, green while the key is turned")
#: HS-321603 and HS-321604 are typed by their loop summaries (UD-MR-321-EC-0001, H 321603 /
#: H 321604, read 2026-10-16) as emergency shut-off switches, one in the control room and one
#: local, not keyswitches; each holds until it is released.
_ESD_NOTE = ("emergency shut-off switch on AC4 PC21's trip 21.2 (UD-MR-G00-FF-0004): the lamp is "
             "amber while 21.2's flag is lost, green while the switch is operated")
DECIDED_ADDITIONS = (
    # Decided 2026-10-10 (project.md decision 98, handoff A-12's open screen elements): the five
    # hand switches of trip 21.2, so an operator can bypass its inputs and start the plant — the
    # three start-up bypasses and the two trip switches on unit 321's screen beside the pumps,
    # HS-322606 beside XV-322902 on 322-1, HS-323604 beside 323P001 on 323-2 — and AI-329701, the
    # LP condensate's conductivity (handoff B-90), on the steam system's screen.
    ("screen-321-1", {"k": "ovrhs321634", "t": "ovrd", "x": 1180, "y": 540, "w": 120, "h": 18,
                      "tag": "HS-321634", "cmd": "HS-321634", "xv": "HAND_SWITCHES.HS_321634",
                      "latch": "21_2",
                      "note": "HS-321634 BYPASS 321P002A/B RUNNING, " + _KEY_NOTE}),
    ("screen-321-1", {"k": "ovrhs321603", "t": "ovrd", "x": 1180, "y": 570, "w": 120, "h": 18,
                      "tag": "HS-321603", "cmd": "HS-321603", "xv": "HAND_SWITCHES.HS_321603",
                      "latch": "21_2",
                      "note": "HS-321603 TRIP 21.2, the control room's " + _ESD_NOTE}),
    ("screen-321-1", {"k": "ovrhs321604", "t": "ovrd", "x": 1180, "y": 600, "w": 120, "h": 18,
                      "tag": "HS-321604", "cmd": "HS-321604", "xv": "HAND_SWITCHES.HS_321604",
                      "latch": "21_2",
                      "note": "HS-321604 TRIP 21.2, the local " + _ESD_NOTE}),
    ("screen-322-1", {"k": "ovrhs322606", "t": "ovrd", "x": 900, "y": 634, "w": 120, "h": 18,
                      "tag": "HS-322606", "cmd": "HS-322606", "xv": "HAND_SWITCHES.HS_322606",
                      "latch": "21_2",
                      "note": ("HS-322606 BYPASS CO2 TO 322E001 (XV-322902, FY-322403), "
                               + _KEY_NOTE)}),
    ("screen-323-2", {"k": "ovrhs323604", "t": "ovrd", "x": 200, "y": 675, "w": 120, "h": 18,
                      "tag": "HS-323604", "cmd": "HS-323604", "xv": "HAND_SWITCHES.HS_323604",
                      "latch": "21_2",
                      "note": "HS-323604 BYPASS 323P001A/B RUNNING, " + _KEY_NOTE}),
    ("screen-329-1", {"k": "ai329701", "t": "ind", "x": 1265, "y": 410, "tag": "AI-329701",
                      "bind": "ANALYSERS.AI_329701", "u": "uS/cm", "dec": 3,
                      "note": ("AI-329701, the LP condensate's conductivity in 329D001 on its "
                               "0-30 uS/cm range: a 322E002 tube leak's ammonium bicarbonate")}),
)

#: Element types the process engineer decided to render as another type, every element of the
#: type at once: {source type: (new type, fields set where the element has none)}. Decided
#: 2026-10-16 (project.md decision 129): no valve icon on a screen but the block valves' (XV).
#: Each modulating valve's icon stood on the slide's tag label below the drawn valve, a second
#: valve over the drawing's own; it becomes a plain readout of the valve's opening in per cent,
#: keeping its binding, its click and its faceplate route.
DECIDED_RETYPES = {
    "avalve": ("ind", {"u": "%", "dec": 1}),
}

#: The only geometry edits: V1's migration procedure's ``NUDGE`` table, each row a decision of the
#: process engineer that moves or resizes one element off its recorded shape (screen, element
#: key, the centre and size it takes). Handoff A-7, decided 2026-10-09: zero overlap on every
#: screen, as V1's procedure requires. A stream hotspot is placed by hand (nothing in the slide
#: says which polyline is which stream), so it yields: shrunk from its far end, its near edge kept,
#: by the fewest pixels that clear a nav label, and to one pixel short of a crossing run. The
#: rectangle is centre - size / 2, so a half-pixel centre keeps the near edge where it was.
NUDGE = (
    # strm-soglp, 1100-1199 px, ran 11 px into nav-c001 (1189-1280): 1100-1188, the nav wins.
    ("screen-322-2", "strm-soglp", {"x": 1144.5, "w": 89}),
    # strm-sbot, 1095-1204 px, ran 31 px into nav-c003 (1174-1265): 1095-1173.
    ("screen-322-1", "strm-sbot", {"x": 1134.5, "w": 79}),
    # strm-stm and strm-cond, 800-999 px, crossed strm-stop (953-966): each now ends at 951,
    # a one-pixel dead zone before the run it crosses.
    ("screen-322-1", "strm-stm", {"x": 876, "w": 152}),
    ("screen-322-1", "strm-cond", {"x": 876, "w": 152}),
    # TV-323013B, drawn 31 px below TV-323013A while the valve and its readout stand 34 px: down
    # 3 px, so the two 34-px stacks meet without overlapping (211-244 and 245-278).
    ("screen-323-2", "tv323013b", {"y": 262}),
    # Decided 2026-10-16 (project.md decision 129, the pages revised from their slides): no
    # readout covers a drawn label, symbol or block, nor touches another with one more digit.
    # HS-322915's override is the slide's 23.6 x 17.6 square inside its panel (shape 208), not a
    # 120-px labelled button over the panel's text.
    ("screen-328-2", "ovrxv322915", {"w": 24, "h": 18}),
    # Each the least move, with a 2-px clearance, that leaves the readout off every drawn
    # label, symbol and block and off every other element at one more digit:
    # PIC-322203 off the CO2 Compressor block, up 9.
    ("screen-322-1", "pic203", {"y": 552}),
    # PT-323201 clear of LV-322501's opening, right 11.
    ("screen-322-1", "pt3201", {"x": 1126}),
    # TDY-329125 clear of FIC-329409, left 10.
    ("screen-322-2", "tdy25", {"x": 599}),
    # LV-323503's opening off its valve symbol, left 7.
    ("screen-323-2", "lv323503", {"x": 803}),
    # FIC-323418 and FIC-323401 off their valves' actuators.
    ("screen-323-2", "fic323418", {"x": 631, "y": 547}),
    ("screen-323-2", "fic323401", {"x": 563, "y": 648}),
    # FIC-329402, FIC-328406 and FIC-328402 off their valves' actuators.
    ("screen-328-1", "fic329402", {"y": 416}),
    ("screen-328-1", "fic328406", {"x": 1221, "y": 469}),
    ("screen-328-1", "fic328402", {"x": 741, "y": 669}),
    # PT-324204 off 324F003's shoulder; TIC-324002 off 324E003's shell.
    ("screen-324-1b", "pt324204", {"x": 444, "y": 169}),
    ("screen-324-1b", "tic324002", {"x": 436}),
    # HIC-323605 off its valve's actuator, PY-324701 off 324F003's shell, TT-328006 clear of
    # AI-328701: each a pixel or five.
    ("screen-324-1", "hic323605", {"x": 519}),
    ("screen-324-1b", "py324701", {"y": 231}),
    ("screen-328-1", "tt328006", {"x": 907}),
)


class ConversionError(RuntimeError):
    """Raised when the source cannot be parsed faithfully. Never swallowed."""


# ======================================================================================
# Lexical pre-processing
# ======================================================================================

def strip_comments(text: str) -> str:
    """Remove ``//`` and ``/* */`` comments without touching string literals.

    A naive regex would eat the ``//`` inside a URL or a path in a quoted string. This
    walks the text character by character and tracks quote state, which is cheap at this
    file size and cannot be fooled.
    """
    out = []
    i = 0
    n = len(text)
    quote = None
    while i < n:
        ch = text[i]
        if quote:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in "'\"":
            quote = ch
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def extract_ov_block(text: str) -> str:
    """Return the body of ``const OV = { ... };`` by brace matching.

    Brace matching rather than a regex, because the block is 500 lines of nested literals
    and a non-greedy regex would stop at the first ``}``.
    """
    m = re.search(r"\bconst\s+OV\s*=\s*\{", text)
    if not m:
        raise ConversionError("could not locate 'const OV = {' in the source")
    start = m.end() - 1
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i]
    raise ConversionError("unbalanced braces in the OV block")


def split_screens(body: str) -> list[tuple[str, str]]:
    """Split the OV body into ``(screen_id, array_body)`` pairs, in source order.

    Source order is preserved deliberately: V1's own verification procedure dumps overlays
    in emitted order and compares against the slide's shape boxes, so reordering here would
    break the comparison.
    """
    screens = []
    for m in re.finditer(r"'(screen-[^']+)'\s*:\s*\[", body):
        sid = m.group(1)
        start = m.end() - 1
        depth = 0
        end = None
        for i in range(start, len(body)):
            if body[i] == "[":
                depth += 1
            elif body[i] == "]":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end is None:
            raise ConversionError(f"unbalanced brackets in screen {sid}")
        screens.append((sid, body[start + 1:end]))
    if not screens:
        raise ConversionError("no 'screen-...' entries found in the OV block")
    return screens


def split_records(array_body: str) -> list[str]:
    """Split a screen's array body into individual ``{ ... }`` record texts."""
    records = []
    depth = 0
    start = None
    quote = None
    for i, ch in enumerate(array_body):
        if quote:
            if ch == quote:
                quote = None
            continue
        if ch in "'\"":
            quote = ch
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                records.append(array_body[start:i + 1])
            elif depth < 0:
                raise ConversionError("unbalanced braces inside a screen array")
    if depth != 0:
        raise ConversionError("unterminated record in a screen array")
    return records


# ======================================================================================
# Record parsing
# ======================================================================================

_KEY = r"([A-Za-z_][A-Za-z0-9_]*)"
_TOKEN = re.compile(
    _KEY + r"\s*:\s*("
    r"'(?:[^'\\]|\\.)*'"          # single-quoted string
    r'|"(?:[^"\\]|\\.)*"'         # double-quoted string
    r"|-?\d+\.\d+|-?\.\d+|-?\d+"  # number
    r"|true|false|null"           # literal
    r")"
)


def parse_record(text: str, sid: str) -> dict:
    """Parse one ``{ key: value, ... }`` record into a Python dict.

    Raises
    ------
    ConversionError
        If the record contains a construct this parser does not understand. Raising is the
        point: an unparsed field is a binding that silently disappears.
    """
    body = text.strip()
    if not (body.startswith("{") and body.endswith("}")):
        raise ConversionError(f"{sid}: record is not a brace literal: {body[:80]!r}")
    inner = body[1:-1]

    out = {}
    consumed = 0
    for m in _TOKEN.finditer(inner):
        key, raw = m.group(1), m.group(2)
        out[key] = _literal(raw)
        consumed = m.end()

    # Anything left over that is not whitespace or a separating comma means the parser did
    # not understand part of the record. Fail rather than lose it.
    residue = re.sub(r"[\s,]", "", inner[consumed:])
    if residue:
        raise ConversionError(f"{sid}: unparsed residue in record: {residue[:80]!r}")
    if not out:
        raise ConversionError(f"{sid}: empty record: {body[:80]!r}")
    return out


def _literal(raw: str):
    """Convert a JS literal token to its Python value."""
    if raw in ("true", "false"):
        return raw == "true"
    if raw == "null":
        return None
    if raw[0] in "'\"":
        return raw[1:-1].replace("\\'", "'").replace('\\"', '"').replace("\\\\", "\\")
    return float(raw) if ("." in raw) else int(raw)


# ======================================================================================
# Validation
# ======================================================================================

def validate(screens: dict[str, list[dict]]) -> dict[str, int]:
    """Check the converted table against V1's own structural invariants.

    These are the invariants V1's migration procedure gates on. They are checked here, at
    conversion time, so a bad conversion cannot reach the UI.
    """
    counts: dict[str, int] = {}
    seen_keys: set[tuple[str, str]] = set()

    for sid, elements in screens.items():
        for el in elements:
            if "t" not in el:
                raise ConversionError(f"{sid}: record has no type field 't': {el}")
            if el["t"] not in KNOWN_TYPES:
                raise ConversionError(f"{sid}: unknown element type {el['t']!r}")
            if "k" not in el:
                raise ConversionError(f"{sid}: record has no key field 'k': {el}")
            pair = (sid, el["k"])
            if pair in seen_keys:
                raise ConversionError(f"{sid}: duplicate element key {el['k']!r}")
            seen_keys.add(pair)
            for axis in ("x", "y"):
                if axis not in el:
                    raise ConversionError(f"{sid}/{el['k']}: missing '{axis}'")
            counts[el["t"]] = counts.get(el["t"], 0) + 1

    # A nav hotspot with no destination steals a click and goes nowhere.
    for sid, elements in screens.items():
        for el in elements:
            if el["t"] == "nav" and not el.get("goto"):
                raise ConversionError(f"{sid}/{el['k']}: nav hotspot with no 'goto'")

    return counts


def apply_decided_edits(screens: list[tuple[str, list[dict]]]) -> None:
    """Apply `DECIDED_RETYPES`, `DECIDED_EDITS` and `NUDGE` in place, then append
    `DECIDED_ADDITIONS`; raise if an edited element does not exist or an added one is not a
    valid new element."""
    for _sid, elements in screens:
        for el in elements:
            if el["t"] in DECIDED_RETYPES:
                new_type, defaults = DECIDED_RETYPES[el["t"]]
                el["t"] = new_type
                for name, value in defaults.items():
                    el.setdefault(name, value)
    by_key = {(sid, el["k"]): el for sid, elements in screens for el in elements}
    for sid, key, fields in DECIDED_EDITS + NUDGE:
        el = by_key.get((sid, key))
        if el is None:
            raise ConversionError(f"{sid}/{key}: a decided edit names an element that is gone")
        for name, value in fields.items():
            if value is None:
                el.pop(name, None)
            else:
                el[name] = value
    lists = dict(screens)
    for sid, el in DECIDED_ADDITIONS:
        if sid not in lists:
            raise ConversionError(f"{sid}: a decided addition names a screen that is gone")
        if (sid, el["k"]) in by_key:
            raise ConversionError(f"{sid}/{el['k']}: a decided addition duplicates a key")
        if el["t"] not in KNOWN_TYPES:
            raise ConversionError(f"{sid}/{el['k']}: unknown element type {el['t']!r}")
        lists[sid].append(dict(el))
        by_key[(sid, el["k"])] = lists[sid][-1]


# ======================================================================================
# Emission
# ======================================================================================

_HEADER = '''"""Overlay geometry and tag bindings for the ten process screens.

GENERATED FILE — do not edit by hand.

Produced by ``tools/convert_overlays.py`` from
``D:\\\\Work\\\\Urea Simulation\\\\frontend\\\\overlays.js``, with the process engineer's
decided edits applied (``DECIDED_EDITS``, ``NUDGE`` and ``DECIDED_ADDITIONS`` in the tool, each
naming its decision).

What the numbers are
--------------------
Each screen's background is a PowerPoint equipment drawing (``UI Pages/*.pptx``) exported
to a {stage_w}x{stage_h} PNG with the live symbols DELETED. Each element below sits at the
centre of the shape that was deleted, sized from that shape's own extent and carrying its
own rotation and mirror. An overlay therefore lands in the hole its symbol left, and cannot
drift off it.

Slides are 12192000 x 6858000 EMU and the stage is {stage_w} x {stage_h}, so the mapping is
**anisotropic**: ``sx = {stage_w}/12192000`` across, ``sy = {stage_h}/6858000`` down. The
ratio ``SLIDE_RX = sx/sy`` is applied to rotated icons by
``ureasim.hmi.widgets.icon_geometry`` to un-squash them; without it a 90-degree pump reads
as an ellipse.

Field reference
---------------
    k        element key, unique within a screen
    t        element type — see ``ELEMENT_TYPES``
    x, y     centre position on the stage [px]
    w, h     extent [px] (icons only)
    rot      rotation [degrees], PowerPoint convention
    fx       mirror the symbol horizontally inside its own box
    fy       mirror the symbol vertically inside its own box
    fs       type size [px] the slide specified for this box
    tag      DCS tag as printed on the drawing
    bind     dot-path into the engine state snapshot
    u        engineering unit shown beside the value
    dec      decimal places
    mode     dot-path to the controller mode letter (A / M / E / O)
    fp       controller id for the left-click faceplate
    face     faceplate variant
    cas      dot-path to the cascade setpoint this box tracks
    ctl      controller tag a panel readout routes its faceplate to
    ctlBind  dot-path that faceplate reads as its PV
    ctlU     unit that faceplate shows, when it differs from ``u``
    cmd      command id for a clickable block valve or hand switch
    xv       the block-valve state a hand switch or override reflects
    latch    interlock id an override pushbutton is armed by
    id       pump duty designator (A / B)
    def      default boolean state for an unmodelled icon
    goto     destination screen id for a nav hotspot
    stream   stream id for the stream-inspector popup
    route    bespoke command route for a valve with no standard loop
    note     physics note carried from the source
"""

from __future__ import annotations

#: Stage size in pixels. Every coordinate below is in this frame.
STAGE_W = {stage_w}
STAGE_H = {stage_h}

#: PowerPoint slide extent in EMU, and the anisotropic squash it implies.
SLIDE_EMU_W = 12192000
SLIDE_EMU_H = 6858000
SLIDE_RX = (STAGE_W / SLIDE_EMU_W) / (STAGE_H / SLIDE_EMU_H)

#: Element types, with the widget each maps to.
ELEMENT_TYPES = {{
    "ind":    "IndicatorWidget",       # black box, live value + unit
    "nav":    "NavHotspotWidget",      # transparent screen-jump hotspot
    "pump":   "PumpWidget",            # green running / grey stopped
    "bar":    "BargraphWidget",        # vertical level fill
    "strm":   "StreamHotspotWidget",   # stream inspector popup
    "xv":     "BlockValveWidget",      # bowtie, open / closed
    "hs":     "HandSwitchWidget",      # hand switch beside a block valve
    "ae":     "AnalyserWidget",        # analyser element
    "ovrd":   "OverrideButtonWidget",  # override pushbutton
    "btn":    "PushButtonWidget",      # generic pushbutton
}}

#: Screens in tab-bar order, with the title shown in the header.
SCREENS = [
{screens_list}
]

#: screen id -> list of overlay elements, in source (emitted) order.
OVERLAYS = {{
'''

#: Screen titles, taken from V1's `index.html` `data-label` attributes.
SCREEN_TITLES = {
    "screen-321-1": "321-1 NH3 PUMPING STATION",
    "screen-322-1": "322-1 UREA SYNTHESIS",
    "screen-322-2": "322-2 UREA SYNTHESIS HP SCRUBBER",
    "screen-323-1": "323-1 LP RECIRC & PRE-EVAP",
    "screen-323-2": "323-2 LP RECIRCULATION 2",
    "screen-324-1": "324-1 EVAPORATION 1",
    "screen-324-1b": "324-1b EVAPORATION 2",
    "screen-328-1": "328-1 DESORPTION",
    "screen-328-2": "328-2 ABSORPTION",
    "screen-329-1": "329-1 UREA STEAM SYSTEM",
}

#: Field emission order. Geometry first, then identity, then behaviour — so a diff between
#: two generated files lines up column-wise and is readable.
_FIELD_ORDER = ["k", "t", "x", "y", "w", "h", "rot", "fx", "fy", "fs",
                "tag", "bind", "u", "dec", "mode", "cas", "fp", "face",
                "ctl", "ctlBind", "ctlU",
                "cmd", "xv", "latch", "id", "def", "goto", "stream", "route", "note"]


def emit(screens: list[tuple[str, list[dict]]], stage_w: int, stage_h: int) -> str:
    """Render the generated module text."""
    screens_list = "\n".join(
        f'    ({sid!r}, {SCREEN_TITLES.get(sid, sid)!r}),' for sid, _ in screens
    )
    parts = [_HEADER.format(stage_w=stage_w, stage_h=stage_h, screens_list=screens_list)]

    for sid, elements in screens:
        parts.append(f"    {sid!r}: [\n")
        for el in elements:
            ordered = {k: el[k] for k in _FIELD_ORDER if k in el}
            # Anything the field order does not know about is still emitted, after the
            # known fields, so no source data is lost.
            for k in el:
                if k not in ordered:
                    ordered[k] = el[k]
            fields = ", ".join(f"{k!r}: {v!r}" for k, v in ordered.items())
            parts.append(f"        {{{fields}}},\n")
        parts.append("    ],\n")

    parts.append("}\n\n")
    parts.append('__all__ = ["STAGE_W", "STAGE_H", "SLIDE_RX", "SLIDE_EMU_W", '
                 '"SLIDE_EMU_H",\n           "ELEMENT_TYPES", "SCREENS", "OVERLAYS"]\n')
    return "".join(parts)


# ======================================================================================
# Entry point
# ======================================================================================

def convert(source: Path, out: Path) -> dict[str, int]:
    """Convert `source` to `out` and return the per-type element counts."""
    text = source.read_text(encoding="utf-8")

    stage = re.search(r"const\s+STAGE_W\s*=\s*(\d+)\s*,\s*STAGE_H\s*=\s*(\d+)", text)
    if not stage:
        raise ConversionError("could not read STAGE_W / STAGE_H from the source")
    stage_w, stage_h = int(stage.group(1)), int(stage.group(2))

    clean = strip_comments(text)
    body = extract_ov_block(clean)

    screens: list[tuple[str, list[dict]]] = []
    for sid, array_body in split_screens(body):
        elements = [parse_record(r, sid) for r in split_records(array_body)]
        screens.append((sid, elements))

    validate(dict(screens))
    apply_decided_edits(screens)
    counts = validate(dict(screens))

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(emit(screens, stage_w, stage_h), encoding="utf-8")
    return counts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    if not args.source.is_file():
        print(f"source not found: {args.source}", file=sys.stderr)
        return 2

    counts = convert(args.source, args.out)
    total = sum(counts.values())
    print(f"wrote {args.out}")
    print(f"  {total} elements")
    for t in sorted(counts, key=lambda k: -counts[k]):
        print(f"    {t:7s} {counts[t]:4d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
