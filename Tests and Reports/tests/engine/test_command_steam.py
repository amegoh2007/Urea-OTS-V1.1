"""The operator's commands on unit 329 — `ureasim.engine.command_steam` (split from
`engine.command`, 2026-10-23).

Pins the steam handlers called directly on a built plant, and that the dispatch table runs on
them. The commands' paths through `apply_command` are pinned in `test_command.py`.
"""

from __future__ import annotations

import pytest

from ureasim.data.operator_commands import STEAM_SP_MAX_BARA
from ureasim.engine import command_steam as cs
from ureasim.engine.command import PLANT_COMMANDS
from ureasim.engine.command_payload import _Refused
from ureasim.engine.plant import build_plant


@pytest.fixture(scope="module")
def plant():
    return build_plant()[1]


def test_the_dispatch_table_runs_on_these_handlers():
    assert PLANT_COMMANDS["pic329204_set"] is cs._pic329204_set
    assert PLANT_COMMANDS["pic329205_set"] is cs._pic329205_set
    assert PLANT_COMMANDS["master207_set"] is cs._master207_set
    names = {"steam_supply_set", "steam_letdown_set", "steam_hpvent_set", "steam_963_set",
             "hic329602_set", "lic329502_set", "lic329503_set", "lic329504_set",
             "pic329207_set", "pic329207a_set", "pic329207b_set", "pic329207c_set"}
    assert {PLANT_COMMANDS[n].__module__ for n in names} == {cs.__name__}


def test_a_steam_controller_offers_auto_and_man_only(plant):
    with pytest.raises(_Refused, match="PIC-329204 offers AUTO and MAN, not CAS"):
        cs._pic329204_set(plant, {"mode": "CAS"}, {})


def test_the_header_set_point_is_clamped_to_its_ceiling(plant):
    """V1's 25 bar a ceiling on every steam header's set point."""
    assert cs._pic329204_set(plant, {"mode": "AUTO", "sp": 99.0}, {}) == "PIC-329204 AUTO"
    assert plant.units["329"].pic_329204.sp_bara == STEAM_SP_MAX_BARA == 25.0


@pytest.mark.parametrize("op, a, b", [(25.0, 50.0, 0.0), (50.0, 100.0, 0.0), (75.0, 0.0, 50.0)])
def test_pic_329205s_split_range(plant, op, a, b):
    """One output: 0-50 % opens PV-329205A, 50-100 % PV-329205B."""
    cs._pic329205_set(plant, {"mode": "MAN", "op": op}, {})
    pic = plant.units["329"].pic_329205
    assert (pic.op_a_pct, pic.op_b_pct) == (a, b)


def test_a_steam_valve_written_by_hand(plant):
    """The stroke is clamped to 0-100 % and written where its path points."""
    handler = cs._steam_valve(("hv_329602_pct",), "HV-329602")
    assert handler(plant, {"op": 140.0}, {}) == "HV-329602 100 %"
    assert plant.units["329"].hv_329602_pct == 100.0
