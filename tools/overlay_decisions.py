"""The process engineer's decided edits to V1's screens, applied by `tools/convert_overlays.py`.

What this is
------------
The four tables the converter applies on top of V1's ``overlays.js`` after parsing it: what an element
DOES (`DECIDED_EDITS`), a whole element type rendered as another (`DECIDED_RETYPES`), where an element
sits (`NUDGE`, V1's migration table for the purpose) and an element V1's screens lack
(`DECIDED_ADDITIONS`). Each row names its decision. Moved verbatim out of the converter on 2026-11-13
(session 110) so that the converter stays under the 600-line ceiling as the tables grow; the converter
re-exports every name, and the generated `ureasim/data/screen_layout.py` is byte-identical across the
move.
"""

from __future__ import annotations

__all__ = ["DECIDED_EDITS", "DECIDED_ADDITIONS", "DECIDED_RETYPES", "NUDGE"]

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
    # Decided 2026-11-13 (decision 222, the process engineer's instruction I-4): the auxiliary pump
    # pairs whose run state the engine holds open the START / STOP faceplate. Each icon binds the
    # pump's state, at V1's own path for 322P002 and in the port's PUMPS block for the others, and
    # loses its drawn default.
    *((sid, f"p{tag.lower()}", {"bind": path, "id": tag, "def": None}) for sid, tag, path in (
        ("screen-328-2", "322P002A", "ABSORB_328.D003.P002A"),
        ("screen-328-2", "322P002B", "ABSORB_328.D003.P002B"),
        ("screen-323-2", "323P001A", "PUMPS.323P001A"),
        ("screen-323-2", "323P001B", "PUMPS.323P001B"),
        ("screen-328-2", "328P003A", "PUMPS.328P003A"),
        ("screen-328-2", "328P003B", "PUMPS.328P003B"),
    )),
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
    # Decided 2026-11-13 (decision 220, the process engineer's instruction I-1): V1's CO2 feed
    # hand station on 322-1 restored, at V1's own place (frontend/co2_compressor.js: left 6, top
    # 352, 196 x 53; the slide's marker meets AT-322701). The engine holds the demand and steps it.
    ("screen-322-1", {"k": "co2step", "t": "step", "x": 104, "y": 378.5, "w": 196, "h": 53,
                      "tag": "320K002", "cap": "CO2 FEED", "bind": "CO2_FEED.demand_pct",
                      "u": "%", "dec": 1, "cmd": "co2_step",
                      "note": ("CO2 demand on 320K002 in % of the 54.618 t/h design feed; DOWN and "
                               "UP step it by 2 %, from 0 to 120 %")}),
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
