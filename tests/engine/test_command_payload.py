"""The command handlers' shared helpers — `ureasim.engine.command_payload` (split from
`engine.command`, 2026-10-23).

Pins each check a handler makes on V1's command dictionary, and the refusal it raises, on payloads
built for the test; no plant is needed. The handlers themselves are pinned in `test_command.py`.
"""

from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

from ureasim.engine import command_payload as cp


def test_a_number_is_finite_and_clamped():
    """V1's ``_finite`` and ``clamp``: a string that reads as a number is taken; out of range is
    clamped, not refused."""
    assert cp._num({"op": "42.5"}, "op") == 42.5
    assert cp._num({"op": 140.0}, "op", 0.0, 100.0) == 100.0
    assert cp._num({"op": -3.0}, "op", 0.0, 100.0) == 0.0


@pytest.mark.parametrize("cmd, reason", [
    ({}, "the command needs 'op'"),
    ({"op": "open"}, "'op' must be a number"),
    ({"op": None}, "'op' must be a number"),
    ({"op": math.inf}, "'op' must be finite"),
    ({"op": math.nan}, "'op' must be finite"),
])
def test_a_bad_number_is_refused_with_its_reason(cmd, reason):
    with pytest.raises(cp._Refused, match=reason):
        cp._num(cmd, "op")


def test_start_stop_or_toggle():
    assert (cp._want({}), cp._want({"on": None})) == (None, None)
    assert (cp._want({"on": 1}), cp._want({"on": False})) == (True, False)


def test_the_clamp():
    assert (cp._clamp(5.0, 0.0, 1.0), cp._clamp(-5.0, 0.0, 1.0), cp._clamp(0.5, 0.0, 1.0)) == (
        1.0, 0.0, 0.5)


def test_a_field_the_mode_does_not_use_is_refused():
    """V1's REST rule: an output in MAN only, a set point in AUTO only."""
    cp._needs({"op": 10.0}, "MAN", op="MAN", sp="AUTO")
    with pytest.raises(cp._Refused, match="'op' is the operator's in MAN only"):
        cp._needs({"op": 10.0}, "AUTO", op="MAN", sp="AUTO")


def test_a_trip_by_its_key():
    """The interlock ``i_<key>`` on the synthesis trips; an unknown key refused; the name the
    operator reads."""
    trip = object()
    plant = SimpleNamespace(units={"SYN-TRIPS": SimpleNamespace(i_21_2=trip)})
    assert cp._trip(plant, "21_2") is trip
    with pytest.raises(cp._Refused, match="no trip '9_9'"):
        cp._trip(plant, "9_9")
    assert cp._trip_name("21_2") == "trip 21.2"
