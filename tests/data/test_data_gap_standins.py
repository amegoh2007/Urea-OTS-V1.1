"""The stand-ins the open data gaps run on, one row each (handoff Open data gaps; session 99, wave 5).

What this pins
--------------
Each open data gap is a datum the archives do not give, run on a stand-in the process engineer accepted
(decision 128's ledger). This file names the constant that holds each stand-in and its value, so that the
day the plant's readback or the vendor's curve arrives, closing the gap is one constant changed in
`ureasim/data/` and one row here re-pinned, and nothing else moves unseen. The table is As-Built §CX.9.

Gaps 1 and 3 (Körting's curves) stand on back-solved geometry and synthesized maps whose own unit tests pin
them (`tests/units/synthesis/test_ejector.py`, `tests/units/evaporation/test_ejector_map.py`); their rows here
pin the inputs the curves would replace.
"""

from __future__ import annotations

import importlib

import pytest

#: (gap, module under ``ureasim.data``, constant, stand-in value, what it stands in for)
STANDINS = [
    (1, "unit_322f001", "P_DISCHARGE_DES_BARA", 144.2,
     "322F001's discharge at the design: the fixed lift the nozzle and throat are back-solved on"),
    (2, "unit_322c001", "TRIP_22_1_HIGH_C", 110.0, "TT-322015's H2, the DCS readback"),
    (2, "unit_322c001", "TRIP_22_1_CLEAR_C", 108.0, "its clearing point: V1's 2 K hysteresis"),
    (3, "unit_324_train", "F002_MOTIVE_DES_KGH", 390.0, "324F002's design motive, the synthesized map's anchor"),
    (3, "unit_324_train", "F004_MOTIVE_DES_KGH", 1220.0, "324F004's design motive"),
    (3, "unit_324_train", "F005_MOTIVE_DES_KGH", 180.0, "324F005's design motive"),
    (4, "unit_324", "F003_M_TAU_S", 180.0, "LI-324501 on V1's holdup ratio: the melt's residence"),
    (4, "unit_324", "F003_LEVEL_SP_PCT", 54.7, "LIC-324501's set point, V1's"),
    (5, "unit_322_loop", "TRIP_21_2_FY_L2_FRAC", 0.05, "FY-322403's L2: V1's 21.4 threshold"),
    (5, "unit_322_loop", "TRIP_21_8_PDY_L2_BAR", 0.1, "PDY-321203 / 204's L2"),
    (8, "unit_323e011", "LT_323503_L2_PCT", 5.0, "LT-323503's L2, the faceplate's"),
    (8, "unit_323e011", "LT_323503_L2_HYST_PCT", 2.0, "its restart hysteresis, the 2 % stand-in"),
    (9, "unit_335", "FIC_335405_KC", 100.0, "FIC-335405's gain, V1's"),
    (9, "unit_335", "FIC_335405_TI_S", 15.0, "FIC-335405's integral time, V1's"),
    (10, "unit_324", "E001_COND_TAU_S", 90.0, "LI-329505 on V1's holdup ratio: the chest condensate's residence"),
    (10, "unit_324", "E001_COND_LEVEL_SP_PCT", 50.0, "LIC-329505's set point, V1's"),
]


@pytest.mark.parametrize("gap, module, name, value, meaning", STANDINS,
                         ids=[f"gap{g}-{n}" for g, _, n, _, _ in STANDINS])
def test_each_open_gap_runs_on_its_recorded_standin(gap, module, name, value, meaning):
    assert getattr(importlib.import_module(f"ureasim.data.{module}"), name) == value, meaning


def test_every_open_gap_has_a_row():
    """The open gaps of `handoff.md`: 1, 2, 3, 4, 5, 8, 9 and 10."""
    assert sorted({row[0] for row in STANDINS}) == [1, 2, 3, 4, 5, 8, 9, 10]
