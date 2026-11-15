"""The LP absorption section's schedule entries — `ureasim.engine.plant.absorption`.

Pinned: I 22.1 sets on TT-322015 above its 110 C limit and holds until the temperature is back
below 108 C, opening XV-322915 while it is set unless HS-322915 is held; the section seeds 322C001
with its loops and the trips with XV-322915 shut; its three steps read what V1's sections 22 and
35 read, and the absorber's read of XV-322915 is the one declared tear, a step behind the trips.
"""

from __future__ import annotations

from ureasim.engine.plant.absorption import PlantTrips, TripsResult, steps, tears, units
from ureasim.engine.schedule import Boundary, Operator, Result, State


def test_i_22_1_sets_holds_and_releases_on_its_hysteresis():
    trips = PlantTrips()
    assert trips.xv_322915_open is False
    seq = [(100.0, False), (110.5, False), (109.0, False), (107.9, False)]
    got = [trips.step(t, hs) for t, hs in seq]
    assert got == [TripsResult(False, False), TripsResult(True, True), TripsResult(True, True),
                   TripsResult(False, False)]
    held = trips.step(111.0, True)
    assert held == TripsResult(True, False) and trips.xv_322915_open is False


def test_the_section_is_seeded_on_the_design():
    plant_units, loops = units()
    assert set(plant_units) == {"322C001", "TRIPS"} and set(loops) == {"322C001"}
    assert plant_units["TRIPS"].xv_322915_open is False
    assert len(loops["322C001"]) == 1


def test_the_steps_read_what_v1_reads_and_the_trips_act_a_tick_late():
    s = steps()
    assert list(s) == ["322E006", "322C001", "TRIPS"]
    assert [step.v1_section for step in s.values()] == [22, 22, 35]
    assert s["322E006"].wiring["m_cw_kgh"] == Boundary("322E006.cw_kgh")
    assert s["322C001"].wiring["m_cpl_kgh"] == Operator("FIC-322404")
    assert s["322C001"].wiring["xv_322915_open"] == State("TRIPS", "xv_322915_open")
    assert s["TRIPS"].wiring == {"ti_322015_c": Result("322C001", "t_ti_322015_c"),
                                 "hs_322915": Operator("HS-322915")}
    (tear,) = tears()
    assert tear.source == State("TRIPS", "xv_322915_open") and tear.reader == "322C001"
