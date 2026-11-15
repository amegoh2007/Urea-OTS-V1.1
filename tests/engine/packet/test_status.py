"""The annunciation in the console packet — `ureasim.engine.packet.status`.

Pinned: V1's flags in V1's order less 320K002's surge and stonewall (a boundary feed, decided
2026-10-08), all clear at design; the four trips live and latched — V1's 21.4 has no flag in AC4's
application software (handoff A-12, decided 2026-10-09), and V1's 22.2 is in no plant document
(decision 189) — clear at design; a synthesis loop put over V1's 22.2 set point publishes no 22.2,
and over SV32251's set the relief lifts; the keyswitches' positions (decision 98) released at the seed
and turned as the operator turns them.
"""

from __future__ import annotations

from ureasim.data.unit_322_loop import SV32251_SET_BARA
from tests.engine.packet.conftest import run

V1_FLAGS = ["SCRUBBER_SOLIDIFICATION", "STRIPPER_SOLIDIFICATION", "LV322501_EROSION",
            "LV323505_BLOWTHROUGH", "LV323501_BLOWTHROUGH", "CARBAMATE_DEPOSITION",
            "RATIO_PV_BAD", "SYN_PSV_LIFT", "TOXIC_RELEASE", "LP_ABSORBER_OVERLOAD",
            "LP_ABSORBER_RELIEF", "EJECTOR_STALL"]
TRIPS = ["21_2", "21_8", "21_10", "22_1"]


def test_all_clear_at_design(design):
    p = design.packet
    assert list(p["flags"]) == V1_FLAGS and not any(p["flags"].values())
    assert list(p["trips"]) == list(p["trip_latched"]) == TRIPS
    assert not any(p["trips"].values()) and not any(p["trip_latched"].values())


#: V1's trip 22.2 set point [bar a], V1 ``SYN_P_TRIP_BARA``: the rewrite has no such trip.
V1_TRIP_22_2_BARA = 155.0


def test_the_loop_over_v1s_22_2_trips_nothing_of_its_own_and_over_sv32251_the_relief_lifts():
    """Decision 189: no plant document draws a trip on the loop's pressure; SV32251 / SV32252 are
    its limit (Operating Manual III page 5-8). A pressure stepped onto the loop starves the CO2 line
    for the tick, so 21.2's FY-322403 input drops — AC4's trip, not a pressure trip."""
    def at(p_bara):
        def setup(plant):
            plant.units["PT-329201"].p_syn_bara = p_bara
        return setup
    p = run(1, at(V1_TRIP_22_2_BARA + 0.5)).packet
    assert list(p["trip_latched"]) == TRIPS and not p["flags"]["SYN_PSV_LIFT"]
    p = run(1, at(SV32251_SET_BARA + 1.0)).packet
    assert list(p["trip_latched"]) == TRIPS and p["flags"]["SYN_PSV_LIFT"]


def test_the_boundary_sinks_publish_each_overflow_and_its_temperature():
    """Not V1's (handoff A-15, decided 2026-10-03): 328C003's, 328C004's and 322C001's overflows,
    and SV32064's relief of the CO2 line (handoff B-83, decided 2026-10-09), nothing at design;
    322C001 flooded with LV-322502 shut, 33.4 t/h leaves it at 43 C; the CO2 line above SV32064's
    set with XV-322902 shut, the valve lifts and vents the line's gas at 120 C."""
    p = run(1).packet
    assert list(p["BOUNDARY_SINKS"]) == ["328C003", "328C004", "322C001", "320K002"]
    assert all(v["m_kgh"] == 0.0 for v in p["BOUNDARY_SINKS"].values())

    def packed(plant):
        plant.units["320K002"].xv_322902_open = False
        plant.units["320K002"].pressure_bara = 161.1
    ran = run(1, packed)
    co2 = ran.packet["BOUNDARY_SINKS"]["320K002"]
    assert co2 == {"m_kgh": round(ran.results["320K002"].relief_kgh, 1), "t_c": 120.0}
    assert co2["m_kgh"] > 50000.0 and ran.results["320K002"].relief_lifted

    def shut(plant):
        plant.loops["322C001"][0].lic_322502.set_mode("MAN")
        plant.loops["322C001"][0].lic_322502.op = 0.0
        plant.units["322C001"].m_kg = 3617.0
    ran = run(5, shut)
    sink = ran.packet["BOUNDARY_SINKS"]["322C001"]
    r = ran.results["322C001"]
    assert sink == {"m_kgh": round(r.m_overflow_kgh, 1), "t_c": round(r.t_c, 2)}
    assert sink["m_kgh"] > 30000.0


def test_the_hand_switches_publish_each_keyswitchs_position():
    """Not V1's (decision 98, 2026-10-10): HS-322915 and trip 21.2's five, released at the seed;
    HS-321634 turned reads turned."""
    p = run(1).packet
    assert p["HAND_SWITCHES"] == dict.fromkeys(
        ("HS_322915", "HS_321634", "HS_323604", "HS_322606", "HS_321603", "HS_321604"), False)

    def turned(plant):
        plant.operator["HS-321634"] = True
    assert run(1, turned).packet["HAND_SWITCHES"]["HS_321634"] is True


def test_the_pumps_publish_their_run_feedback_apart_from_the_command(monkeypatch):
    """Review of decision 217: the icon showed 328P002A running while AC4's low-level stop held
    the pair. ``on`` is the machine's feedback and ``cmd`` the operator's command; they differ
    only while a stop holds the pair (here LT-328501's limit raised to 99 %, above the drum's
    design level)."""
    from ureasim.units.desorption import reflux_drum
    pumps = run(1).packet["PUMPS"]
    assert all(p["on"] == p["cmd"] for p in pumps.values()) and pumps["328P002A"]["on"]
    monkeypatch.setattr(reflux_drum, "L2_PCT", {"LT-328501": 99.0})
    pumps = run(1).packet["PUMPS"]
    assert pumps["328P002A"] == {"on": False, "cmd": True, "mode": "AUTO"}
    assert pumps["328P006A"]["on"] and pumps["335P001A"]["on"]
