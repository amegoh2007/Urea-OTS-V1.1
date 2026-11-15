"""`ureasim.control.granulation_trips`: AC4 PC35's trips 35.1, 35.3 and 35.4 (decision 228, B-146).

What this pins
--------------
The logic of UD-MR-G00-FF-0004 PC35.5.1 and PC35.5.2 as built: both 335P001 stopped lose 35.1 and,
through it, 35.4 on the same evaluation (35.4's AND carries 35.1's flag), and with them 35.3, the
UF85 pumps' interlock; both 335P002 stopped lose nothing for 600 s and 35.4 after it; LV-324501A at
its closed limit holds 35.4 lost; each override releases its own action and no other; no flag
latches. A de-energised solenoid is the action: LV-324501A shut, LV-324501B and HV-335602 open.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from ureasim.control.granulation_trips import HEALTHY_35, Unit35Actions, Unit35TripInputs, Unit35Trips
from ureasim.data.unit_335 import (
    LIC_324501_CLAMPREF_PCT,
    PIC_335201_CLAMPREF_PCT,
    TRIP_35_4_P002_TD_S,
)

DT = 0.1
RUNNING = Unit35TripInputs(p001_running=True, p002_running=True, lvsl_324501a=False)
#: Every action of a lost 35.1 and 35.4 with no override.
ALL_TRIPPED = Unit35Actions(lv_324501a_shut=True, lv_324501b_open=True, hv_335602_open=True,
                            pic_335201_hold_pct=PIC_335201_CLAMPREF_PCT,
                            lic_324501_hold_pct=LIC_324501_CLAMPREF_PCT, p002_permit=False)


def _trips() -> Unit35Trips:
    return Unit35Trips(TRIP_35_4_P002_TD_S, LIC_324501_CLAMPREF_PCT, PIC_335201_CLAMPREF_PCT)


def _flags(t: Unit35Trips) -> tuple[bool, bool]:
    return t.flag_35_1.latched, t.flag_35_4.latched


def test_the_seed_raises_nothing_and_commands_nothing():
    t = _trips()
    assert t.actions == HEALTHY_35 and t.t_p002.elapsed_s == 0.0
    for _ in range(100):
        assert t.step(RUNNING, DT) == HEALTHY_35
    assert _flags(t) == (False, False) and not t.p002_held


def test_both_335p001_stopped_lose_35_1_35_4_and_35_3_on_one_evaluation():
    """PC35.5.1 executes before PC35.5.2, so 35.4 reads 35.1's flag of the same scan."""
    t = _trips()
    assert t.step(replace(RUNNING, p001_running=False), DT) == ALL_TRIPPED
    assert _flags(t) == (True, True) and t.p002_held
    assert (t.flag_35_1.operator_resettable, t.flag_35_4.operator_resettable) == (False, False)


def test_both_335p002_stopped_lose_nothing_for_600_s_and_35_4_after_it():
    t = _trips()
    stopped = replace(RUNNING, p002_running=False)
    for _ in range(int(round(TRIP_35_4_P002_TD_S / DT)) - 1):
        assert t.step(stopped, DT) == HEALTHY_35
    a = t.step(stopped, DT)
    assert _flags(t) == (False, True)
    assert a == Unit35Actions(lv_324501a_shut=True, hv_335602_open=True,
                              pic_335201_hold_pct=PIC_335201_CLAMPREF_PCT, p002_permit=False)


def test_a_335p002_restart_inside_the_delay_restarts_the_timer():
    t = _trips()
    stopped = replace(RUNNING, p002_running=False)
    for _ in range(5000):
        t.step(stopped, DT)
    t.step(RUNNING, DT)
    assert t.t_p002.elapsed_s == 0.0
    for _ in range(5000):
        assert t.step(stopped, DT) == HEALTHY_35


def test_lvsl_324501a_holds_35_4_lost_until_hs_335201a_opens_the_valve():
    """The feed valve shut opens its closed-limit contact, an input of 35.4: with the pumps
    running again 35.4 stays lost, and HS-335201A energises LV-324501A's solenoid and unclamps
    PIC-335201, so the valve can open and clear the contact."""
    t = _trips()
    shut = replace(RUNNING, lvsl_324501a=True)
    a = t.step(shut, DT)
    assert _flags(t) == (False, True) and a.lv_324501a_shut and not a.lv_324501b_open
    a = t.step(replace(shut, hs_335201a=True), DT)
    assert _flags(t) == (False, True)
    assert not a.lv_324501a_shut and a.pic_335201_hold_pct is None and a.hv_335602_open
    assert t.step(replace(RUNNING, hs_335201a=True), DT) == HEALTHY_35
    assert _flags(t) == (False, False)


@pytest.mark.parametrize("hs, released", [
    ("hs_335201a", {"lv_324501a_shut": False, "pic_335201_hold_pct": None}),
    ("hs_335201b", {"lv_324501b_open": False, "lic_324501_hold_pct": None}),
    ("hs_335602", {"hv_335602_open": False}),
    ("hs_335620", {"p002_permit": True}),
])
def test_each_override_releases_its_own_action_and_no_other(hs, released):
    t = _trips()
    a = t.step(replace(RUNNING, p001_running=False, **{hs: True}), DT)
    assert a == replace(ALL_TRIPPED, **released)
    assert _flags(t) == (True, True)


def test_no_flag_latches():
    t = _trips()
    t.step(replace(RUNNING, p001_running=False), DT)
    assert t.step(RUNNING, DT) == HEALTHY_35 and _flags(t) == (False, False)
