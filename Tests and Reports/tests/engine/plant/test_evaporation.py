"""`ureasim.engine.plant.evaporation`'s step for AC4 PC35's trips 35.1, 35.3 and 35.4 (decision 228).

What this pins
--------------
On the whole plant: the seed raises no trip; both 335P001 stopped lose 35.1 and 35.4 at the tick's
end and the header, LIC-324501 and the UF85 pumps act on them from the next tick; the restart AC4
draws — a pump started, HS-335201A turned so that PIC-335201 opens LV-324501A off its closed limit,
then released — runs to a forward melt flow with every flag healthy; and an exercise saved before
the trips existed loads with them healthy.
"""

from __future__ import annotations

import json

import pytest

from ureasim.control.granulation_trips import HEALTHY_35
from ureasim.data.operator_commands import TRIP_35_HAND_SWITCHES
from ureasim.engine import snapshot
from ureasim.engine.command import apply_command
from ureasim.engine.packet import build_packet
from ureasim.engine.plant import build_plant
from ureasim.engine.plant.evaporation import TRIPS_35
from ureasim.engine.scheduler import Scheduler


def _run(s: Scheduler, seconds: float) -> None:
    for _ in range(int(round(seconds / 0.1))):
        s.tick()


def _cmd(s: Scheduler, **cmd) -> None:
    assert apply_command(s.plant, cmd).ok


def _packet(s: Scheduler) -> dict:
    return build_packet(s.plant, s.results, s.tears_read, sim_mode="SLOW", t_wall=0.0)


@pytest.fixture(scope="module")
def stopped():
    """Both 335P001 stopped at the seed, one tick, then one more."""
    s = Scheduler(*build_plant())
    _run(s, 1.0)
    assert s.plant.units[TRIPS_35].actions == HEALTHY_35
    _cmd(s, type="aux_pump_toggle", id="335P001A", on=False)
    _cmd(s, type="aux_pump_toggle", id="335P001B", on=False)
    s.tick()
    first = _packet(s)
    s.tick()
    return s, first, _packet(s)


def test_both_335p001_stopped_lose_35_1_and_35_4_at_the_ticks_end(stopped):
    s, first, _ = stopped
    assert {k: first["trip_latched"][k] for k in ("35_1", "35_4")} == {"35_1": True, "35_4": True}
    assert first["PUMPS"]["335P002A"] == {"on": False, "cmd": True, "mode": "AUTO"}
    assert first["PUMPS"]["335P001A"]["on"] is False


def test_from_the_next_tick_the_header_is_shut_and_drained_and_the_uf85_pumps_stop(stopped):
    s, _, second = stopped
    e3, loops = s.results["324E003"], s.plant.loops["324E003"][0]
    assert (e3.header.lv_a_position_pct, e3.header.forward_kgh, e3.header.p_barg) == (0.0, 0.0, 0.0)
    assert e3.header.hv_pct == pytest.approx(100.0 / 30.0, abs=1e-9)
    assert (loops.level.op, loops.header.op, e3.lv_b_pct) == (100.0, 0.0, 100.0)
    assert s.results["335"].delivered_kgh == 0.0 and second["HAND_SWITCHES"]["HS_335201A"] is False


def test_the_restart_through_hs_335201a_runs_to_a_forward_melt_flow():
    """A pump restarted: 35.1 heals and LIC-324501 resumes from its 100 % clamp on LV-324501B, but
    35.4 stays lost on LVSL-324501A; HS-335201A turned lets PIC-335201 open LV-324501A, 35.4 heals
    and 335P002 runs again; released, the header carries the melt forward."""
    s = Scheduler(*build_plant())
    _run(s, 1.0)
    _cmd(s, type="aux_pump_toggle", id="335P001A", on=False)
    _cmd(s, type="aux_pump_toggle", id="335P001B", on=False)
    _run(s, 30.0)
    _cmd(s, type="aux_pump_toggle", id="335P001A", on=True)
    _run(s, 10.0)
    t = s.plant.units[TRIPS_35]
    assert (t.flag_35_1.latched, t.flag_35_4.latched, t.p002_held) == (False, True, True)
    assert s.results["324E003"].header.forward_kgh == 0.0
    assert s.results["324E003"].header.recycle_kgh > 0.0
    _cmd(s, type="keyswitch_set", id="HS-335201A", on=True)
    _run(s, 30.0)
    assert (t.flag_35_1.latched, t.flag_35_4.latched, t.p002_held) == (False, False, False)
    _cmd(s, type="keyswitch_set", id="HS-335201A", on=False)
    _run(s, 60.0)
    assert t.actions == HEALTHY_35 and not _packet(s)["trip_latched"]["35_4"]
    assert s.results["324E003"].header.forward_kgh > 0.5 * s.results["324E003"].m_402_kgh > 0.0
    assert s.results["335"].delivered_kgh > 0.0


def test_a_save_made_before_the_trips_loads_with_them_healthy():
    """Decision 228's migration: a save lacking the trips' unit and the four overrides is filled
    from the present model's seed, and the plant then runs with no trip."""
    sch, plant = build_plant()
    doc = json.loads(snapshot.dumps(plant))
    units, operator = doc["state"]["a"]["units"]["$d"], doc["state"]["a"]["operator"]["$d"]
    del units[TRIPS_35]
    for t in TRIP_35_HAND_SWITCHES:
        del operator[f"HS-{t}"]
    back = snapshot.loads(json.dumps(doc), build_plant()[1])
    assert back.units[TRIPS_35].actions == HEALTHY_35
    assert all(back.operator[f"HS-{t}"] is False for t in TRIP_35_HAND_SWITCHES)
    s = Scheduler(sch, back)
    _run(s, 1.0)
    assert back.units[TRIPS_35].actions == HEALTHY_35


#: Decision 251: the motive valves' strokes and what the separators' loops do 300 s after each step
#: from the seed run 60 s (measured: 64 % 0.330 bar a / 61.1 %; 55 % 0.349 / 52.5 %, PT-323204 0.465;
#: 40 % 0.129 / 92.5 %; 38 % 0.150 / 87.3 %).
MOTIVE_STEPS = [
    ("hic9605_set", 64.0, "E001", "PIC_324202", "PT_324202", False),
    ("hic9605_set", 55.0, "E001", "PIC_324202", "PT_324202", True),
    ("hic9606_set", 40.0, "E003", "PIC_324203", "PT_324203", False),
    ("hic9606_set", 38.0, "E003", "PIC_324203", "PT_324203", True),
]


@pytest.mark.parametrize("kind, op, stage, pic, pt, lost", MOTIVE_STEPS,
                         ids=[f"{k}_{o:.0f}" for k, o, *_ in MOTIVE_STEPS])
def test_the_motive_valves_hold_and_lose_the_vacuums_on_the_plants_bracket_decision_251(
        kind, op, stage, pic, pt, lost):
    """Decision 251, As-Built §CXLIV.3. On the plant, 5 November 2026, HIC-329605 held 324F001's
    vacuum at 64 % and lost it at 55 %, HIC-329606 held 324F003's at 40 % and lost it at 38 %. At
    the held stroke the bleed takes the step and the vacuum stays; at the lost stroke the
    separator's pressure rises and its PIC closes the bleed, and stage 1's loss reaches 323F010
    (PT-323204), whose vapour 324E002 condenses beside 324F001's."""
    s = Scheduler(*build_plant())
    _run(s, 60.0)
    seed = _packet(s)
    _cmd(s, type=kind, op=op)
    _run(s, 300.0)
    p = _packet(s)
    p0, p1 = seed["EVAP_324"][stage][pt], p["EVAP_324"][stage][pt]
    op0, op1 = seed["EVAP_324"][stage][pic]["op"], p["EVAP_324"][stage][pic]["op"]
    if lost:
        assert p1 - p0 > 0.015 and op0 - op1 > 4.0
    else:
        assert abs(p1 - p0) <= 0.003 and abs(op1 - op0) <= 1.5
    if kind == "hic9605_set":
        t0, t1 = seed["RECIRC_323"]["F010"]["P_bara"], p["RECIRC_323"]["F010"]["P_bara"]
        assert (t1 - t0 > 0.003) if lost else (abs(t1 - t0) <= 0.001)
