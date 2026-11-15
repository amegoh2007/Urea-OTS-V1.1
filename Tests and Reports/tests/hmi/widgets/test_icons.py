"""Pump and block-valve symbols — `ureasim.hmi.widgets.icons`.

Pinned: a pump bound to its machine object runs on the object's ``on`` field, and on a bare boolean
too; an unbound pump shows its drawn default and says it is not modelled; a block valve follows its
bound state and keeps its own when unbound; every image the symbols paint ships with the console.
"""

from __future__ import annotations

import pytest

from ureasim.hmi.widgets.icons import ICON_DIR, BlockValveWidget, PumpWidget


@pytest.fixture()
def pump(qapp):
    w = PumpWidget({"x": 100, "y": 100, "tag": "P-1", "bind": "X.pumpA"})
    yield w
    w.close()


def test_a_bound_pump_runs_on_its_machine(pump):
    pump.update_from({"X": {"pumpA": {"on": False, "mode": "AUTO"}}})
    assert pump._state is False and pump.toolTip().startswith("P-1 — OFF")
    pump.update_from({"X": {"pumpA": True}})
    assert pump._state is True and "START/STOP" in pump.toolTip()


def test_an_unbound_pump_shows_its_drawn_default(qapp):
    spare = PumpWidget({"x": 100, "y": 100, "tag": "P-2B", "def": False})
    spare.update_from({})
    assert spare._state is False and spare.toolTip() == "P-2B — OFF (not modelled)"
    spare.close()


def test_a_block_valve_follows_its_state(qapp):
    xv = BlockValveWidget({"x": 100, "y": 100, "tag": "XV-1", "bind": "X.xv"})
    xv.update_from({"X": {"xv": False}})
    assert xv._state is False and xv.toolTip() == "XV-1 — CLOSED"
    loose = BlockValveWidget({"x": 100, "y": 100, "tag": "XV-2", "def": False})
    loose.update_from({"X": {"xv": True}})
    assert loose._state is False
    xv.close()
    loose.close()


def test_the_artwork_ships():
    for name in ("pump-on.png", "pump-off.png", "xv-open.png", "xv-close.png"):
        assert (ICON_DIR / name).is_file()
