"""The consoles' faceplates and the instructor's panel: which command each control emits.

What this is
------------
A console's faceplate is a dumb window on the packet: it shows what the engine published and sends
the operator's entry as one of the engine's commands (`ureasim.engine.command`). Which command a
faceplate sends, with which payload field, is V1's own front-end table (``frontend/app.js``),
carried here as data so that no Qt module holds plant knowledge and a test can pin every entry to
the engine handler that takes it.

Three corrections to V1's table, each a V1 front-end defect, not a change of what an operator may
do (`CLAUDE.md` §4a rule 2):

* HIC-329605, HIC-329606 and HIC-323605 send ``op``. V1's front end sent ``value``, which its own
  ``handle_cmd`` never read (``if "op" in cmd``), so those three faceplates did nothing.
* No faceplate keeps a local mode, set point or output for a loop the packet does not carry (V1's
  ``localStorage`` store, ``ots_ctl_v1``): a console owns nothing (§4a rule 1). Such a faceplate
  says the loop is not on this model.
* The cascade notes name the masters the port wires, not V1's list: SIC-323901 under LIC-323502
  and FIC-328406 under LIC-328505 (decided 2026-09-30, handoff B-50) are added; UF85's FIC-335405
  under FFIC-335406 is V1's own (decision 123 runs it live).

Source: V1 ``frontend/app.js`` — the hand-valve table (``CMD``, ``NOTE``, ``TTL``, 516-531), the
generic controller's routing (``CAS_MASTER``, ``CAS_UNWIRED``, ``T``, 691-768), the pump interlock
(570-579), the SIC faceplates (861-1165) and the MASTER SP faceplate (1167-1282); ``index.html``
(the faceplates' fields); ``co2_compressor.js`` (322-1's CO2 feed hand station); the engine's
handlers for the port's corrections.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from ureasim.data.operator_commands import FACEPLATE_MODES
from ureasim.data.unit_335 import HEADER_VALVES_MAX

__all__ = [
    "HandValve", "HAND_VALVES", "LOOP_COMMANDS", "CAS_MASTERS", "CAS_UNWIRED",
    "SpeedController", "SPEED_CONTROLLERS", "PUMP_TRIPS", "PUMP_COMMANDS", "MASTER_SP_LEGS",
    "Malfunction", "MALFUNCTIONS", "CO2_DEMAND_MAX_FRAC", "CO2_DEMAND_STEP_FRAC",
    "CO2_STEP_COMMAND", "CO2_STEP_FIELD", "CO2_DEMAND_PCT_DECIMALS", "CO2_DEMAND_TH_DECIMALS",
    "GRANULATION_HEADERS_TAG", "GRANULATION_STEP_COMMAND", "GRANULATION_STEP_FIELD", "StepPanel",
    "STEP_PANELS", "loop_command",
]


# ======================================================================================
# Hand valves: one opening, no mode
# ======================================================================================

@dataclass(frozen=True)
class HandValve:
    """A hand station's faceplate: the command it sends, the payload field, its caption."""

    command: str
    field: str
    title: str
    note: str
    unit: str = "%"


_HV_NOTE = "Hand valve — operator sets opening directly (no controller mode)."


def _hv(command: str, field: str, number: str, note: str = _HV_NOTE) -> HandValve:
    return HandValve(command, field, f"HIC-{number} → HV-{number} (MANUAL)", note)


_HAND = {
    "322602": _hv("hic_set", "value", "322602", "↓ opening ⇒ ↑ 322E003 suction (↑ μ)"),
    "322605": _hv("hic605_set", "op", "322605"),
    "322604": _hv("hic604_set", "op", "322604"),
    "329601": _hv("steam_hpvent_set", "op", "329601"),
    "329602": _hv("hic329602_set", "op", "329602"),
    "329605": _hv("hic9605_set", "op", "329605",
                  "↑ opening ⇒ ↑ 324F002 vacuum (↓ 324E002 pressure)"),
    "329606": _hv("hic9606_set", "op", "329606",
                  "↑ opening ⇒ ↑ 324F004/F005 vacuum (↓ 324F003 pressure)"),
    "323605": _hv("hic323605_set", "op", "323605",
                  "↓ opening ⇒ ↑ 323F010 pressure (↓ vacuum)"),
    "335602": _hv("hic335602_set", "op", "335602",
                  "↑ opening ⇒ the melt header drains to 335D004 (↓ PIC-335201); opens in 3 s, "
                  "closes in 25 s"),
}

#: Each hand station by its HIC and its HV tag (V1 routes either), and FT-322404's condensate
#: entry and HIC-322203's minimum opening, which share the faceplate.
HAND_VALVES = MappingProxyType({
    **{f"HIC-{n}": hv for n, hv in _HAND.items()},
    **{f"HV-{n}": hv for n, hv in _HAND.items()},
    "FT-322404": HandValve(
        "cpl_set", "value", "FT-322404  CONDENSATE 954 → 322C001 (MANUAL, kg/h)",
        "operator sets 954 condensate feed (kg/h) ⇒ ↑322C001 sump ⇒ LIC-322502 opens ⇒ ↑756 "
        "draw ⇒ make dilutes", "kg/h"),
    "HIC-322203": HandValve("hic2_set", "value", "HIC-322203 → PV-322203 MIN OPENING",
                            "PV-322203 forced ≥ this minimum"),
})


# ======================================================================================
# Loop faceplates: which command a controller's SET sends
# ======================================================================================

#: The loops with a handler of their own; every other inline faceplate takes ``r323_ctrl_set``
#: (`FACEPLATE_MODES`), and the speed controllers ``controller_set``. Source: V1 ``T``.
LOOP_COMMANDS = MappingProxyType({
    "PIC-322203": "pic_set",
    "LIC-322501": "lic_set",
    "FIC-329409": "fic_set",
    "TIC-329005": "tic_set",
    "PIC-329204": "pic329204_set",
    "PIC-329205": "pic329205_set",
    "PIC-329207": "pic329207_set",
    "LIC-329502": "lic329502_set",
    "LIC-329503": "lic329503_set",
    "LIC-329504": "lic329504_set",
})

#: Each cascade slave and the master that writes its set point, as the port wires them.
CAS_MASTERS = MappingProxyType({
    "PIC-329202": "TIC-323007",
    "PIC-329208": "TIC-323012",
    "PIC-329203": "TIC-324001",
    "PIC-329212": "TIC-324002",
    "FIC-324401": "LIC-323507",
    "SIC-323901": "LIC-323502",
    "FIC-329401": "FFIC-329401",
    "FIC-328404": "TIC-328008",
    "FIC-328406": "LIC-328505",
    "FIC-335405": "FFIC-335406",
    "PIC-335201": "LIC-324501",
})

#: Loops seeded in CAS whose master the model does not wire: CAS holds the seeded set point.
CAS_UNWIRED = MappingProxyType({
    "TIC-323013": "no master is wired to it",
    "FIC-329402": "its master on the plant, TIC-328012, is not wired (handoff B-48)",
})


def loop_command(tag: str) -> str | None:
    """The command a loop faceplate's SET sends, or None for a loop no handler takes."""
    if tag in LOOP_COMMANDS:
        return LOOP_COMMANDS[tag]
    if tag in FACEPLATE_MODES:
        return "r323_ctrl_set"
    return None


# ======================================================================================
# The feed pumps' speed controllers, the pumps, the 4-bar header's master set point
# ======================================================================================

@dataclass(frozen=True)
class SpeedController:
    """SIC-321950 / SIC-321951: the pump it drives and the ratio master over it."""

    pump: str
    pump_bind: str
    master: str


SPEED_CONTROLLERS = MappingProxyType({
    "SIC_321950": SpeedController("321P002A", "pumpA", "FFIC-321404A"),
    "SIC_321951": SpeedController("321P002B", "pumpB", "FFIC-321404B"),
})

#: The synthesis trips that hold each feed pump, as V1's pump faceplate reads them: 21.2 for both,
#: 21.8 for A and 21.10 for B (AC4 PC21; V1's 21.4 has no flag there, handoff A-12; V1's 22.2 is not
#: built, decision 189). The tempered-water pumps carry none.
PUMP_TRIPS = MappingProxyType({"A": ("21_2", "21_8"),
                               "B": ("21_2", "21_10")})

#: The command each pump's START / STOP sends, by the pump's tag: the machines V1's pump faceplate
#: drove (``pump_toggle``), and the auxiliary pairs whose run state the engine holds
#: (``aux_pump_toggle``, V1's own handler, which V1's front end never sent). Decided 2026-11-13
#: (decision 222, the process engineer's instruction I-4): every pump icon whose machine has a run
#: state opens the faceplate. Source: V1 ``frontend/app.js`` 554-598, ``backend/main.py``
#: ``handle_cmd`` (``pump_toggle``, ``aux_pump_toggle``).
PUMP_COMMANDS = MappingProxyType({
    "321P002A": "pump_toggle", "321P002B": "pump_toggle",
    "329P006A": "pump_toggle", "329P006B": "pump_toggle",
    **{tag: "aux_pump_toggle" for tag in ("322P002A", "322P002B", "323P001A", "323P001B", "328P003A",
                                          "328P003B", "335P002A", "335P002B", "329P003A", "329P003B",
                                          "328P007A", "328P007B")},
})

#: PIC-329207's three legs: the packet key, the command, the caption.
MASTER_SP_LEGS = (
    ("A", "PIC_329207A", "pic329207a_set", "vent PV-329207A"),
    ("B", "PIC_329207B", "pic329207b_set", "turbine 320MT02"),
    ("C", "PIC_329207C", "pic329207c_set", "BL admit PV-329207C"),
)


# ======================================================================================
# The instructor's malfunctions
# ======================================================================================

@dataclass(frozen=True)
class Malfunction:
    """An equipment fault the engine can inject: its label and the command's ``id``; a fault with
    a rate names its unit and the rate the panel offers first (the command's ``rate``)."""

    label: str
    equipment: str
    fault_id: str
    rate_unit: str | None = None
    rate_default: float | None = None


#: Every malfunction the engine takes (``trigger_fault`` / ``clear_fault``): V1's lube-oil
#: abstraction on the feed pumps, which arms the pump's trip while it runs, and 322E002's tube
#: leak, process into the shell at its rate at the design differential (B-82, B-90).
MALFUNCTIONS = (
    Malfunction("321P002A lube-oil fault (arms trip 21.8 while running)", "321P002A", "A"),
    Malfunction("321P002B lube-oil fault (arms trip 21.10 while running)", "321P002B", "B"),
    Malfunction("322E002 tube leak, process into the shell (rate at the design differential)",
                "322E002", "322E002", rate_unit="t/h", rate_default=10.0),
)


# ======================================================================================
# The instructor's boundary
# ======================================================================================

#: The CO2 demand on 320K002, as a fraction of the design feed: from none to V1's hard ceiling of
#: 120 %. The instructor's panel sets it in t/h (``co2_set``); 322-1's CO2 FEED panel steps it
#: (``co2_step``), V1's own hand station restored (decision 220, 2026-11-13). The machine stays a
#: boundary with no curve, speed or governor (decision 73). Source: V1
#: ``frontend/co2_compressor.js`` (``MIN``, ``MAX``; its 54.618 t/h is `unit_321.CO2_DES_KGH`).
CO2_DEMAND_MAX_FRAC = 1.20

#: One press of the CO2 FEED panel's DOWN or UP: 2 % of the design feed. Source: V1
#: ``frontend/co2_compressor.js`` (``STEP``).
CO2_DEMAND_STEP_FRAC = 0.02
#: The command a press sends and its payload field, the step's direction (+1 or -1).
CO2_STEP_COMMAND, CO2_STEP_FIELD = "co2_step", "dir"
#: V1's two roundings of the step, kept so that UP then DOWN returns a demand to the bit: the
#: per cent to one decimal (``Math.round(x * 10) / 10``) and the demand to the kilogram per hour
#: (``toFixed(3)`` on t/h), each rounding a half upward. Source: V1 ``frontend/co2_compressor.js``
#: (``step``, ``render``).
CO2_DEMAND_PCT_DECIMALS, CO2_DEMAND_TH_DECIMALS = 1, 3


# ======================================================================================
# The step panels: a readout between two buttons, each press one step in the engine
# ======================================================================================

#: The granulator's header valves online, the operator entry 324-1b's GRANULATION HEADERS panel
#: steps (decision 224, the process engineer's instruction I-3 of 2026-11-14), the command a press
#: sends and its payload field, the step's direction (+1 or -1).
GRANULATION_HEADERS_TAG = "GRANULATION-HEADERS"
GRANULATION_STEP_COMMAND, GRANULATION_STEP_FIELD = "granulation_headers", "dir"


@dataclass(frozen=True)
class StepPanel:
    """A step panel: the command a press sends and its field, the readout's published limits, the
    two buttons' captions and width [px], and the panel's hint."""

    command: str
    field: str
    lo: float
    hi: float
    labels: tuple
    button_px: int
    hint: str


#: Each step panel by the command its element names: 322-1's CO2 FEED panel (decision 220), V1's
#: own captions and button width, and 324-1b's GRANULATION HEADERS panel (decision 224), its
#: buttons wide enough for INCREASE.
STEP_PANELS = MappingProxyType({
    CO2_STEP_COMMAND: StepPanel(
        CO2_STEP_COMMAND, CO2_STEP_FIELD, 0.0, CO2_DEMAND_MAX_FRAC * 100.0, ("DOWN", "UP"), 48,
        f"DOWN and UP step it by {CO2_DEMAND_STEP_FRAC * 100:g} % of its design"),
    GRANULATION_STEP_COMMAND: StepPanel(
        GRANULATION_STEP_COMMAND, GRANULATION_STEP_FIELD, 0.0, float(HEADER_VALVES_MAX),
        ("DECREASE", "INCREASE"), 84,
        "DECREASE takes one header valve off, INCREASE brings one online"),
})
