"""The stand-ins the open data gaps run on, one row each (handoff Open data gaps; session 99, wave 5).

What this pins
--------------
Each open data gap is a datum the archives do not give, run on a stand-in the process engineer accepted
(decision 128's ledger). This file names the constant that holds each stand-in and its value, so that the
day the plant's readback or the vendor's curve arrives, closing the gap is one constant changed and one row
here re-pinned, and nothing else moves unseen. The table is As-Built §CX.9.

Gap 1's stand-ins are the open-literature loss coefficients of `control/jet_pump.py` and the two areas
back-solved through them from the licensor's design duty; gap 3's are the in-situ factors that anchor each
vendor map on the PFD's design load (decided B-61) and, since decision 322, the deduced break curves' width and the
plant's design stroke stage 2's readings are read on (their nodes are the plant's readings, `EJECTOR_BREAKS`).
Körting's curves would replace exactly these. The design
duties they are anchored on are PFD data, not stand-ins, and are not pinned here.
"""

from __future__ import annotations

import importlib

import pytest

#: (gap, module, constant, stand-in value, what it stands in for)
STANDINS = [
    (1, "ureasim.control.jet_pump", "K_NOZZLE", 0.05, "322F001's motive-nozzle loss, open literature"),
    (1, "ureasim.control.jet_pump", "K_ENTRY", 0.10, "its suction-inlet loss, open literature"),
    (1, "ureasim.control.jet_pump", "K_THROAT", 0.05, "its mixing-throat friction, open literature"),
    (1, "ureasim.control.jet_pump", "ETA_DIFF", 0.80, "its diffuser recovery, open literature"),
    (3, "ureasim.data.unit_324", "EJECTOR_BREAK_WIDTH", 1.04, "the ejectors' break width, decision 322 [E]"),
    (3, "ureasim.data.unit_324", "HIC_329606_PLANT_DES_PCT", 44.3,
     "stage 2's readings read on HIC-329606's plant design stroke, decision 322 [E]"),
    (4, "ureasim.data.unit_324", "F003_M_TAU_S", 180.0, "LI-324501 on V1's holdup ratio: the melt's residence"),
    (4, "ureasim.data.unit_324", "F003_LEVEL_SP_PCT", 54.7, "LIC-324501's set point, V1's"),
    (5, "ureasim.data.unit_322_loop", "TRIP_21_8_PDY_L2_BAR", 0.1, "PDY-321203 / 204's L2"),
    (9, "ureasim.data.unit_335", "FIC_335405_KC", 100.0, "FIC-335405's gain, V1's"),
    (9, "ureasim.data.unit_335", "FIC_335405_TI_S", 15.0, "FIC-335405's integral time, V1's"),
    (10, "ureasim.data.unit_324", "E001_COND_TAU_S", 90.0, "LI-329505 on V1's holdup ratio: the chest condensate's residence"),
    (10, "ureasim.data.unit_324", "E001_COND_LEVEL_SP_PCT", 50.0, "LIC-329505's set point, V1's"),
    (12, "ureasim.data.unit_335", "LV_324501A_TAU_S", 1.0, "LV-324501A's positioner lag, the process engineer's"),
    (14, "ureasim.data.unit_335", "LVSL_324501A_PCT", 0.0, "LVSL-324501A's make point, the process engineer's"),
    (15, "ureasim.data.unit_322e003", "LEVEL_NLL_PCT", 50.0, "LI-329501 on V1's holdup ratio: its design reading"),
    (15, "ureasim.data.unit_322e003", "TAU_HOLDUP_MIN", 4.0, "the sump's residence, V1's back-solved scale"),
]


@pytest.mark.parametrize("gap, module, name, value, meaning", STANDINS,
                         ids=[f"gap{g}-{n}" for g, _, n, _, _ in STANDINS])
def test_each_open_gap_runs_on_its_recorded_standin(gap, module, name, value, meaning):
    assert getattr(importlib.import_module(module), name) == value, meaning


def test_gap1_the_areas_back_solved_through_the_literature_coefficients():
    """322F001's nozzle at the design opening and its mixing throat, 16.72 and 50.23 mm bores."""
    from ureasim.data import unit_322f001 as d
    assert d.A_T_DES_M2 == pytest.approx(2.1959110e-4, rel=1e-6)
    assert d.A_M_M2 == pytest.approx(1.9814767e-3, rel=1e-6)


@pytest.mark.parametrize("tag, k", [("324F002", 0.33635), ("324F004", 0.91921), ("324F005", 0.49739)])
def test_gap3_the_in_situ_factors_anchoring_each_vendor_map(tag, k):
    """K_des = K_duty . m_s,des / C_duty,table on the PFD's design load (B-61)."""
    from ureasim.units.evaporation.ejector_map import ejector_map
    assert ejector_map(tag).k_capacity == pytest.approx(k, abs=1e-5)


def test_every_open_gap_has_a_row():
    """The open gaps of `handoff.md`: 1, 3, 4, 5, 9, 10, 12, 14 and 15 (2 and 8 closed by decision 242, 11 by
    decision 247; 15 opened by decision 248)."""
    assert sorted({row[0] for row in STANDINS} | {1, 3}) == [1, 3, 4, 5, 9, 10, 12, 14, 15]
