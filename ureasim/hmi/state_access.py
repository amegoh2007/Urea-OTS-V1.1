"""Reading the engine snapshot from the HMI — dot-paths, formatting, shared tags.

This is the **only** place the presentation layer touches engine data, and it is read-only.
No widget navigates the snapshot itself; every widget is handed a resolved value.

Three jobs
----------
1. **Dot-path resolution.** Overlay bindings are paths like ``'controllers.SIC_321950.pv'``
   or ``'RECIRC_323.D002.T_C'``. A missing path yields ``None``, never an exception — an
   instrument whose unit is not yet modelled must read ``--``, not crash the screen.

2. **Formatting.** Fixed decimals with tabular figures, and the gauge-pressure convention.

3. **Shared tags.** The same DCS tag can appear on more than one screen, and only one of
   those occurrences may carry the binding. `BindMap` makes every occurrence read the same
   value, so a trainee cannot see one number on 323-1 and a different one on 323-2 for the
   same instrument.

Gauge-pressure convention
-------------------------
Every pressure transmitter and controller on these screens displays **gauge** pressure,
while the engine works in absolute. The conversion happens here, once, at the display
boundary:

    if unit is 'BAR A':  value -> value - 1.01325,  unit -> 'BARG'

Doing it in the engine would corrupt the physics; doing it per widget would guarantee that
one widget eventually forgets.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from ureasim.core.units_of_measure import ATM_BARA

#: Standard atmosphere [bar]. The absolute-to-gauge offset: the engine's one atmosphere (handoff
#: B-6, decided 2026-10-07).
ATM_BAR = ATM_BARA

#: What an indicator shows when its bound path is absent or not a number.
NO_DATA = "--"

#: Controller mode letters as the DCS prints them.
MODE_LETTER = {"MAN": "M", "AUTO": "A", "CAS": "E", "OOS": "O",
               "M": "M", "A": "A", "E": "E", "O": "O"}


def get_path(snapshot: Mapping[str, Any] | None, path: str | None) -> Any:
    """Resolve a dot-path into the snapshot. Returns ``None`` if any step is missing.

    Deliberately total: a screen may be drawn before the unit behind a tag is modelled, and
    that case must render as an empty slot rather than raise on every tick.
    """
    if not path or snapshot is None:
        return None
    node: Any = snapshot
    for key in path.split("."):
        if isinstance(node, Mapping):
            node = node.get(key)
        else:
            node = getattr(node, key, None)
        if node is None:
            return None
    return node


def format_value(value: Any, decimals: int | None = 1) -> str:
    """Format a numeric value for a DCS readout, or ``'--'`` when there is none."""
    if value is None:
        return NO_DATA
    try:
        v = float(value)
    except (TypeError, ValueError):
        return NO_DATA
    if v != v:                       # NaN
        return NO_DATA
    return f"{v:.{1 if decimals is None else decimals}f}"


def to_display_units(value: Any, unit: str | None) -> tuple[Any, str | None]:
    """Apply the display-unit convention. Returns ``(value, unit)``.

    Currently one rule: absolute pressure is shown as gauge. See the module docstring.
    """
    if unit == "BAR A" and isinstance(value, (int, float)) and not isinstance(value, bool):
        return value - ATM_BAR, "BARG"
    return value, unit


def mode_letter(snapshot: Mapping[str, Any] | None, element: Mapping[str, Any]) -> str:
    """Controller mode letter for an indicator, or ``''`` when it is not a controller.

    A tag beginning ``HIC`` is an operator **hand station**: it has no automatic mode, so
    it always reads M regardless of what the snapshot says. Showing it as AUTO would tell a
    trainee the loop is closed when there is no loop.
    """
    tag = str(element.get("tag", ""))
    if tag.upper().startswith("HIC"):
        return "M"
    raw = get_path(snapshot, element.get("mode"))
    if raw is None:
        return ""
    return MODE_LETTER.get(str(raw).upper(), "")


class BindMap:
    """Tag -> binding, so a shared tag reads the same value on every screen it appears on.

    Why this is needed
    ------------------
    The ten drawings were produced independently, and a given instrument may be printed on
    two of them — a controller on its own unit's screen and again on the screen of the unit
    it feeds. Only one occurrence carries the binding; the other is an empty slot.

    Without this map, the same instrument would show a live value on one screen and ``--``
    on another. With it, the first bound occurrence found across all screens supplies the
    binding, unit, decimals and faceplate route for every other occurrence of that tag.

    Build it once from the layout table, then call `effective` per element.
    """

    #: Fields an unbound occurrence inherits from the bound one.
    INHERITED = ("bind", "u", "dec", "face", "fp", "mode", "cas")

    def __init__(self, screens: Mapping[str, Iterable[Mapping[str, Any]]]):
        self._by_tag: dict[str, dict[str, Any]] = {}
        for elements in screens.values():
            for el in elements:
                tag = el.get("tag")
                if not tag or not el.get("bind"):
                    continue
                if tag not in self._by_tag:
                    self._by_tag[tag] = {k: el[k] for k in self.INHERITED if k in el}

    def effective(self, element: Mapping[str, Any]) -> Mapping[str, Any]:
        """Return `element`, or a copy with an inherited binding if it has none.

        Only indicators inherit. An unbound pump or valve icon is inert by design — a
        symbol is only clickable when the backend models that machine.
        """
        if element.get("t") != "ind" or element.get("bind"):
            return element
        inherited = self._by_tag.get(element.get("tag", ""))
        if not inherited:
            return element
        merged = dict(element)
        merged.update(inherited)
        return merged

    def bound_tags(self) -> set[str]:
        """Every tag that has a binding somewhere. Used by the coverage test."""
        return set(self._by_tag)


__all__ = [
    "ATM_BAR", "NO_DATA", "MODE_LETTER",
    "get_path", "format_value", "to_display_units", "mode_letter", "BindMap",
]
