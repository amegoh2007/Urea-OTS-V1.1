"""Plant tag registry — which section a tag, and therefore a command, belongs to.

Why this exists
---------------
Trainee stations are **assigned plant sections** (`handoff.md` A-8): a trainee working the
LP recirculation must not be able to move a valve in the synthesis loop that another
trainee is running. To enforce that, the server has to answer one question for every
command that arrives:

    which section of the plant does this command act on?

This module answers it, and it is the only place that knows. The transport layer holds the
assignments; the resolution lives here, with the tag convention it depends on.

The tag convention
------------------
Helwan tags carry their unit in the first three digits of their number:

    LIC-322501   ->  322    synthesis
    SIC-321950   ->  321    NH3 pumping
    TT-328011    ->  328    desorption
    FFIC-335406  ->  335    finishing
    321P002A     ->  321    equipment tags follow the same rule

So most commands resolve by pattern. What does not resolve by pattern is V1's set of
**bespoke command types**: `hic604_set`, `steam_hpvent_set`, `lic329503_set` and the rest
are each hardwired to exactly one instrument, and the tag appears nowhere in the payload.
Those need a table, and the table is below.

The section is read from the same field the engine acts on
-----------------------------------------------------------
A command that carries its instrument in the payload is attributed from the field
`ureasim.engine.command` reads to find that instrument, and in the same order of precedence:
``controller_set`` acts on ``id`` and falls back to ``tag``, so it is attributed the same way. A
resolver that read a different field than the engine could be handed a payload whose
attribution and action disagree — a command one station does not own, executed under a section
it does. ``r323_ctrl_set`` drives every inline faceplate on units 322, 323, 324, 328 and 329, so
it is attributed from its ``id``, never from a fixed section.

Failing closed
--------------
`section_of_command` returns ``None`` when it cannot attribute a command. An **assigned**
station is then refused, by name, so the gap is visible and fixable by adding one row —
rather than silently becoming a hole through which the assignment can be bypassed. An
unassigned station is unaffected, because it has no restriction to bypass.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

#: Plant sections a trainee can be assigned, with the screens each one owns.
#:
#: A section is the unit a trainee is given for an exercise, not a strict drawing boundary:
#: 320K002 (the CO2 compressor) is a unit-320 machine, a boundary feed with no operator lever
#: (decided 2026-10-08); its discharge line, XV-322902 and PV-322203, is worked from screen
#: 322-1, so it is assigned with 322.
SECTIONS: dict[str, dict[str, Any]] = {
    "321": {"name": "NH3 pumping station",
            "screens": ["screen-321-1"]},
    "322": {"name": "Urea synthesis, HP loop",
            "screens": ["screen-322-1", "screen-322-2", "screen-328-2"]},
    "323": {"name": "LP recirculation",
            "screens": ["screen-323-1", "screen-323-2"]},
    "324": {"name": "Evaporation",
            "screens": ["screen-324-1", "screen-324-1b"]},
    "328": {"name": "Desorption and hydrolysis",
            "screens": ["screen-328-1"]},
    "329": {"name": "Steam and utilities",
            "screens": ["screen-329-1"]},
    "335": {"name": "Finishing and UF85",
            "screens": ["screen-324-1b"]},
}

#: Every valid section id.
SECTION_IDS = frozenset(SECTIONS)

#: Unit numbers that are not assignable on their own and fold into the section whose
#: operators actually work them.
_SECTION_ALIASES = {
    "320": "322",      # 320K002 CO2 compressor — its discharge line is worked on 322-1
    "372": "328",      # 372D001 effluent — downstream of desorption
}

#: Bespoke V1 command types, each hardwired to one instrument, with the tag it acts on.
#: The tag is carried so a refusal can name the instrument rather than only the section.
COMMAND_TAGS: dict[str, str] = {
    # --- unit 321 -----------------------------------------------------------------------
    "ratio_set":          "FFIC-321404",     # NH3/CO2 ratio block
    "ext_override":       "321P002",         # EXT. OVERRIDE of 321P002 A/B run signal
    # --- unit 322 -----------------------------------------------------------------------
    "co2_set":            "322FT-322402",    # raw CO2 from 320K002 into the loop
    "cpl_set":            "FT-322404",       # condensate 954 -> 322C001
    "hic_set":            "HIC-322602",      # HV-322602 ejector opening
    "hic2_set":           "HIC-322203",      # PV-322203 minimum opening
    "hic605_set":         "HIC-322605",      # HV-322605 reactor overflow valve
    "hic604_set":         "HIC-322604",      # HV-322604 scrubber off-gas valve
    "pic_set":            "PIC-322203",      # CO2 line-pressure controller
    "lic_set":            "LIC-322501",      # bottom-solution level controller
    # --- unit 323 -----------------------------------------------------------------------
    "hic323605_set":      "HIC-323605",      # HV-323605 323F010 gas outlet
    # --- unit 324 / 335 -------------------------------------------------------------------
    "lv324501_route_set": "LV-324501",       # A = export to BL, B = relief recycle
    "pic335201_set":      "PIC-335201",      # 335 melt-header pressure
    # --- unit 329 -----------------------------------------------------------------------
    "steam_supply_set":   "PV-329204",       # MP supply valve, utility import
    "steam_letdown_set":  "PV-329205B",      # 9 -> 4 bar let-down
    "steam_hpvent_set":   "HV-329601",       # 329D005 atmospheric vent
    "steam_963_set":      "PV-329207C",      # BL 25 -> 4 bar make-up
    "hic329602_set":      "HV-329602",       # BL 25 -> 4 bar block
    "pic329204_set":      "PIC-329204",
    "pic329205_set":      "PIC-329205",
    "pic329207_set":      "PIC-329207",
    "pic329207a_set":     "PV-329207A",      # the trio's vent leg (master OFF)
    "pic329207b_set":     "PV-329207B",      # the trio's turbine leg (master OFF)
    "pic329207c_set":     "PV-329207C",      # the trio's make-up leg (master OFF)
    "master207_set":      "MASTER-329207",   # 4-bar header master setpoint
    "lic329502_set":      "LIC-329502",
    "lic329503_set":      "LIC-329503",
    "lic329504_set":      "LIC-329504",
    "fic_set":            "FIC-329409",      # CCW circulation flow
    "tic_set":            "TIC-329005",      # CCW supply temperature
    "hic9605_set":        "HIC-329605",      # HV-329605 324F002 motive steam
    "hic9606_set":        "HIC-329606",      # HV-329606 324F004/F005 motive steam
}

#: Command types whose target comes from the payload: the fields the engine reads to find its
#: instrument, in the engine's order of precedence.
_TARGET_FIELDS = {
    "controller_set": ("id", "tag"),
    "pump_toggle": ("id",),
    "aux_pump_toggle": ("id",),
    "xv_toggle": ("id",),
    "trip_reset": ("id",),
    # A maintained hand switch, set or released: {"type": "keyswitch_set", "id": "HS-322915",
    # "on": bool}. HS-322915 is XV-322915's only operator input (handoff B-59, decided
    # 2026-10-01: the valve has no operator open on the DCS).
    "keyswitch_set": ("id",),
    # An inline faceplate on any unit: {"type": "r323_ctrl_set", "id": "TIC_323007", ...}.
    "r323_ctrl_set": ("id",),
}

#: 321P002 A/B are the only pumps addressed by a bare duty letter.
_BARE_PUMP_IDS = {"A": "321", "B": "321"}

#: Interlock latch prefixes. 21_x latch unit 321; 22_x latch unit 322.
_LATCH_SECTIONS = {"21": "321", "22": "322"}

#: First run of three or more digits in a tag or equipment number.
_DIGITS = re.compile(r"(\d{3,})")


def section_of_tag(tag: str | None) -> str | None:
    """Section a DCS tag or equipment number belongs to, or ``None``.

    The first three digits of the number carry the unit, so ``LIC-322501`` is 322 and
    ``329P006A`` is 329. Aliases fold a non-assignable unit into the section whose
    operators work it.
    """
    if not tag:
        return None
    match = _DIGITS.search(str(tag))
    if not match:
        return None
    unit = match.group(1)[:3]
    unit = _SECTION_ALIASES.get(unit, unit)
    return unit if unit in SECTION_IDS else None


def target_of_command(cmd: Mapping[str, Any]) -> str | None:
    """The tag or equipment number a command acts on, as best it can be determined."""
    cmd_type = str(cmd.get("type", ""))

    fixed = COMMAND_TAGS.get(cmd_type)
    if fixed is not None:
        return fixed

    for field in _TARGET_FIELDS.get(cmd_type, ()):
        value = cmd.get(field)
        if value is not None:
            return str(value)
    return None


def section_of_command(cmd: Mapping[str, Any]) -> str | None:
    """Section a command acts on, or ``None`` when it cannot be attributed.

    Process utility
    ---------------
    This is what keeps two trainees out of each other's plant. A trainee assigned the LP
    recirculation who reaches for LIC-322501 is refused here, with the instrument named,
    before the command reaches the engine.

    ``None`` means "not attributable". The caller fails closed for an assigned station —
    see the module docstring.
    """
    cmd_type = str(cmd.get("type", ""))

    # Trip reset addresses an interlock latch, not an instrument. A bare reset with no id
    # (or "ALL") clears every latch across the plant, so it is not attributable to one
    # section and an assigned station cannot issue it.
    if cmd_type == "trip_reset":
        latch = cmd.get("id")
        if latch in (None, "ALL"):
            return None
        return _LATCH_SECTIONS.get(str(latch).split("_")[0])

    # 321P002 A/B are addressed by duty letter alone.
    if cmd_type == "pump_toggle":
        pump_id = str(cmd.get("id", ""))
        if pump_id in _BARE_PUMP_IDS:
            return _BARE_PUMP_IDS[pump_id]

    return section_of_tag(target_of_command(cmd))


def describe_sections(sections) -> str:
    """Human-readable section list for a status bar or a refusal message."""
    ordered = sorted(sections)
    if not ordered:
        return "none"
    return ", ".join(f"{s} {SECTIONS[s]['name']}" for s in ordered if s in SECTIONS)


def screens_of_sections(sections) -> list[str]:
    """Screens the given sections own, in `SECTIONS` order and without duplicates.

    Lets a console dim or hide the tabs a trainee is not working, once the instructor
    panel can set assignments.
    """
    seen: list[str] = []
    for section_id, meta in SECTIONS.items():
        if section_id in sections:
            for screen in meta["screens"]:
                if screen not in seen:
                    seen.append(screen)
    return seen


__all__ = [
    "SECTIONS", "SECTION_IDS", "COMMAND_TAGS",
    "section_of_tag", "target_of_command", "section_of_command",
    "describe_sections", "screens_of_sections",
]
