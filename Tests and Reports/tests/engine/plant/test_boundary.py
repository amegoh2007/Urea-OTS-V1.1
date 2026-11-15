"""The plant's battery limits and operator seeds — `ureasim.engine.plant.boundary`.

Pinned: the boundary values are 323C005's atmosphere and 322E006's 14 t/h of cooling water; the
operator's seeds are the design positions the module states — the CO2 demand on PFD 101's
54.618 t/h, HIC-322602 at 74 %, HIC-322605 at 60 %, HIC-322604 at decision 99's 72 %, XV-322903
open, ten of the twelve header valves online and HIC-335602 shut, every trip 21 hand switch and
HS-322915 released, every run-state pair running and each auxiliary pair's A machine running with
B its spare, both in AUTO; and every call hands back fresh objects, so a caller's edit never
reaches the next seed.
"""

from __future__ import annotations

from ureasim.data.operator_commands import (AUX_PUMP_SEEDS, EXT_OVERRIDE_TAG, RUN_STATE_PAIRS,
                                            TRIP_21_HAND_SWITCHES)
from ureasim.engine.plant.boundary import BOUNDARY_SINKS, boundary_values, operator_seeds


def test_the_boundary_values():
    assert boundary_values() == {"323C005.p_bara": 1.0, "322E006.cw_kgh": 14000.0}
    assert set(BOUNDARY_SINKS) == {"328C003", "328C004", "322C001", "320K002"}


def test_the_operator_seeds_are_the_design_positions():
    s = operator_seeds()
    assert s["320K002-CO2"] == 54.618
    assert (s["HIC-322602"], s["HIC-322605"], s["HIC-322604"]) == (74.0, 60.0, 72.0)
    assert s["XV-322903"] is True and s["GRANULATION-HEADERS"] == 10 and s["HIC-335602"] == 0.0
    assert s["FIC-322404"] == 1750.0
    assert s["HS-322915"] is False and s["HV-323D002-TIE"] is False
    assert all(s[f"HS-{t}"] is False for t in TRIP_21_HAND_SWITCHES)
    assert all(s[pair] is True for pair in RUN_STATE_PAIRS)
    for pump, (on, mode) in AUX_PUMP_SEEDS.items():
        assert s[pump] == {"on": on, "mode": mode}
        assert mode == "AUTO" and on is pump.endswith("A")
    assert s[EXT_OVERRIDE_TAG] is False


def test_every_call_hands_back_fresh_objects():
    first = operator_seeds()
    first["HIC-322602"] = 0.0
    first["323P001A"]["on"] = False
    again = operator_seeds()
    assert again["HIC-322602"] == 74.0 and again["323P001A"]["on"] is True
    bv = boundary_values()
    bv["322E006.cw_kgh"] = 0.0
    assert boundary_values()["322E006.cw_kgh"] == 14000.0
