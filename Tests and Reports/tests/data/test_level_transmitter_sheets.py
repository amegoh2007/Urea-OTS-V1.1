"""The modelled level transmitters' tap spans against Uhde's data sheets (session 118, As-Built §CXXVIII.5).

What this pins
--------------
Decision 33's class reads a level between its transmitter's taps. Nine modelled levels do so, each on a tap
span taken from a general arrangement drawing, a nozzle schedule or the isometrics. Uhde's level-transmitter
data sheets (UD-MR-G00-EC-0133 and UD-MR-G00-EC-0134, scans read in session 118 and checked on the page
image) print each transmitter's nozzle distance. This file pins every modelled span to its sheet, so a span
that moves off the sheet fails here. The four levels that still read V1's holdup ratio are handoff B-156
and have no row; LT-324501 and LT-329505 are data gaps 4 and 10.
"""

from __future__ import annotations

import importlib
from typing import Callable

import pytest

#: (tag, vessel, sheet and page, nozzle distance printed on the sheet [mm], module, the modelled span [m])
SHEETS: list[tuple[str, str, str, int, str, Callable[[object], float]]] = [
    ("LT-322502", "322C001", "EC-0134 p. 3", 800, "ureasim.data.unit_322c001",
     lambda m: m.LT_322502_SPAN_M),
    ("LT-323501", "323C003", "EC-0134 p. 4", 2000, "ureasim.data.unit_323c003",
     lambda m: m.LT_323501_SPAN_M),
    ("LT-323502", "323D001", "EC-0134 p. 4", 1910, "ureasim.data.unit_323e003",
     lambda m: m.LT_323502_SPAN_M),
    ("LT-323503", "323D011", "EC-0134 p. 4", 1310, "ureasim.data.unit_323e011",
     lambda m: m.LT_323503_SPAN_M),
    ("LT-323505", "323F004", "EC-0134 p. 5", 2900, "ureasim.data.unit_323",
     lambda m: m.LT_323505_SPAN_M),
    ("LT-328501", "328D001", "EC-0134 p. 6", 1510, "ureasim.data.unit_328d001",
     lambda m: m.LT_328501_SPAN_M),
    ("LT-329502", "329D005", "EC-0133 p. 3", 1500, "ureasim.data.unit_329_network",
     lambda m: 2.0 * m.D005_TAP_HALF_M),
    ("LT-329503", "329D009", "EC-0133 p. 3", 750, "ureasim.data.unit_329_network",
     lambda m: 2.0 * m.D009_TAP_HALF_M),
    ("LT-329504", "322D001A / B", "EC-0133 p. 4", 1500, "ureasim.data.unit_329_network",
     lambda m: m.D001_TAPS_M[1] - m.D001_TAPS_M[0]),
]


@pytest.mark.parametrize(("tag", "vessel", "sheet", "nozzle_mm", "module", "span"), SHEETS,
                         ids=[row[0] for row in SHEETS])
def test_modelled_tap_span_is_the_sheets_nozzle_distance(
        tag: str, vessel: str, sheet: str, nozzle_mm: int, module: str,
        span: Callable[[object], float]) -> None:
    """Process utility: a level read between its taps shows 0 and 100 % where the plant's transmitter does
    only if the modelled taps are the transmitter's nozzles; the sheet is the transmitter's own record."""
    modelled_m = span(importlib.import_module(module))
    assert modelled_m == pytest.approx(nozzle_mm / 1000.0, abs=1e-9), (
        f"{tag} on {vessel}: modelled span {modelled_m} m, Uhde's sheet {sheet} prints {nozzle_mm} mm")
