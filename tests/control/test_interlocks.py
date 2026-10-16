"""The latching interlocks, against a transcription of V1's own inline trip block.

Why this is not an equivalence test
-----------------------------------
Every other ported module in this package is proven by RUNNING V1's code beside the
rewrite's. That is not possible here. V1's trip logic is not a function: it is thirty lines
written inline inside `step_sim`, reading `s.pumpA`, `s.XV_322901`, `s.SIC_321950` and a
dozen other attributes of a plant state object that only exists once `main.py` has built a
FastAPI application. There is nothing to import and nothing to lift.

So the four latch rules are TRANSCRIBED below, from V1 `backend/main.py` — the trip block of
`step_sim` and the `trip_reset` command handler — and the rewrite is driven against them over
exhaustive condition sequences. This is weaker evidence than the other equivalence files
provide, and it is recorded as such in `handoff.md`: the transcription is checked by eye
against the source, not executed from it.

What the transcription covers
-----------------------------
    21_2 / 21_8 / 21_10   latch on a live condition; reset only once it has cleared
    21_4                  the same, but latched only while ARMED (synthesis running)
    22_1                  hysteretic self-clear, no operator reset
    22_2                  latch at the trip point, reset blocked by a wider band

The plant's 21.2, 21.8 and 21.10 are no longer V1's latches but AC4's live flags (handoff A-12,
decided 2026-10-09); the latch classes' tests keep V1's trip names as their examples. AC4's logic
is pinned at the foot of this file against the application software's PC diagrams.
"""

from __future__ import annotations

import itertools

import pytest

from ureasim.control.interlocks import (
    BandedInterlock,
    HystereticInterlock,
    Interlock,
    InterlockSet,
    Monoflop,
    OnDelayTimer,
    Unit21TripInputs,
    Unit21Trips,
)

#  V1 `backend/main.py` lines 4963-4964, quoted verbatim rather than imported because
#  `main.py` cannot be imported:
#      SYN_P_TRIP_BARA     = 155.0   # bar a, trip 22.2 synthesis high-high -> ESD
#      SYN_P_TRIP_RESET_BARA = 148.0 # bar a, live condition clears below this
SYN_P_TRIP_BARA = 155.0
SYN_P_TRIP_RESET_BARA = 148.0


# --------------------------------------------------------------------------------------
# V1's rules, transcribed
# --------------------------------------------------------------------------------------

def _v1_plain(live: bool, latched: bool) -> bool:
    """V1: `for _tk in ("21_2", "21_8", "21_10"): if s.trips[_tk]: s.trip_latched[_tk] = True`."""
    return True if live else latched


def _v1_armed(live: bool, armed: bool, latched: bool) -> bool:
    """V1: `if co2_lost_21_4 and syn_running_214: s.trip_latched["21_4"] = True`."""
    return True if (live and armed) else latched


def _v1_reset(live: bool, latched: bool) -> bool:
    """V1: `if k in s.trip_latched and not s.trips.get(k, False): s.trip_latched[k] = False`."""
    return latched and live


def _v1_hysteretic(pv: float, latched: bool) -> tuple[bool, bool]:
    """V1 trip 22.1, verbatim structure."""
    live = pv > 57.0
    if live:
        latched = True
    elif pv < 55.0:
        latched = False
    return live, latched


def _v1_banded(pv: float, latched: bool) -> tuple[bool, bool]:
    """V1 trip 22.2, verbatim structure."""
    if latched:
        live = pv >= SYN_P_TRIP_RESET_BARA
    else:
        live = pv >= SYN_P_TRIP_BARA
        if live:
            latched = True
    return live, latched


# --------------------------------------------------------------------------------------
# The plain latch
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("sequence", list(itertools.product([False, True], repeat=5)))
def test_the_plain_latch_follows_v1_over_every_condition_sequence(sequence):
    trip = Interlock("21_2", "Urea synthesis main trip")
    latched = False
    for live in sequence:
        latched = _v1_plain(live, latched)
        assert trip.update(live) == latched


def test_a_latch_holds_after_the_condition_clears():
    """The behaviour that makes it a trip and not a comparison."""
    trip = Interlock("21_2")
    trip.update(True)
    assert trip.latched is True
    trip.update(False)
    assert trip.latched is True
    assert trip.live is False


def test_a_latch_cannot_be_reset_while_its_condition_is_live():
    trip = Interlock("21_2")
    trip.update(True)
    assert trip.reset() is False
    assert trip.latched is True
    trip.update(False)
    assert trip.reset() is True
    assert trip.latched is False


@pytest.mark.parametrize("live,latched", list(itertools.product([False, True], repeat=2)))
def test_the_reset_rule_follows_v1(live, latched):
    trip = Interlock("21_8")
    trip.live, trip.latched = live, latched
    trip.reset()
    assert trip.latched == _v1_reset(live, latched)


def test_a_successful_reset_is_reported_so_the_cause_can_be_resolved():
    """V1 clears a pump's mechanical fault on a SUCCESSFUL reset only.

    That is what makes "reset" mean "cause resolved" rather than "annunciator silenced". A
    refused reset must not resolve anything, so the return value is the signal the caller
    acts on.
    """
    trip = Interlock("21_8", "HP NH3 pump A equipment fault")
    trip.update(True)
    assert trip.reset() is False          # still faulted: nothing is resolved
    trip.update(False)
    assert trip.reset() is True           # now it is


# --------------------------------------------------------------------------------------
# Arming
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("sequence", list(itertools.product(
    [(False, False), (False, True), (True, False), (True, True)], repeat=3)))
def test_the_armed_latch_follows_v1_over_every_sequence(sequence):
    trip = Interlock("21_4", "Loss of CO2 feed -> NH3 main interlock")
    latched = False
    for live, armed in sequence:
        latched = _v1_armed(live, armed, latched)
        assert trip.update(live, armed) == latched


def test_an_idle_plant_does_not_latch_itself_out_of_a_black_start():
    """21.4's initiator — no CO2 — is trivially true on a plant that has not started.

    Without arming, a cold plant would latch its own NH3 trip before anyone touched it, and
    a trainee doing a black start would be stopped by a trip that protects nothing.
    """
    trip = Interlock("21_4")
    for _ in range(100):
        trip.update(condition=True, armed=False)      # no CO2, but nothing is running
    assert trip.latched is False
    trip.update(condition=True, armed=True)           # synthesis running and CO2 lost
    assert trip.latched is True


def test_the_live_flag_is_published_even_when_the_trip_is_not_armed():
    """The annunciator shows the initiator; the plant acts on the latch. Not the same thing."""
    trip = Interlock("21_4")
    trip.update(condition=True, armed=False)
    assert trip.live is True
    assert trip.latched is False


# --------------------------------------------------------------------------------------
# The hysteretic action
# --------------------------------------------------------------------------------------

PV_22_1 = [43.0, 54.0, 56.0, 57.0, 57.5, 60.0, 56.5, 55.5, 54.9, 50.0, 58.0, 43.0]


def test_the_hysteretic_action_follows_v1_over_a_full_excursion():
    trip = HystereticInterlock("22_1", "322C001 over-temperature steam flood",
                               trip_above=57.0, clear_below=55.0)
    latched = False
    for pv in PV_22_1:
        live, latched = _v1_hysteretic(pv, latched)
        assert trip.update_from_pv(pv) == latched
        assert trip.live == live


def test_the_flood_stays_open_across_the_dead_band():
    """Between 55 and 57 C the valve neither opens nor closes — that is what stops it
    chattering on a measurement sitting on its limit."""
    trip = HystereticInterlock("22_1", trip_above=57.0, clear_below=55.0)
    trip.update_from_pv(58.0)
    assert trip.latched is True
    for pv in (56.9, 56.0, 55.1, 55.0):
        assert trip.update_from_pv(pv) is True
    assert trip.update_from_pv(54.9) is False


def test_the_self_clearing_action_has_no_reset_button():
    """There is no reset control for 22.1 on the overlay, so there is none in the model."""
    trip = HystereticInterlock("22_1", trip_above=57.0, clear_below=55.0)
    trip.update_from_pv(60.0)
    assert trip.operator_resettable is False
    assert trip.reset() is False
    assert trip.latched is True


def test_the_design_absorber_temperature_leaves_the_flood_shut():
    """At design Tc001 is about 43 C, so the condition is False and the action is zero —
    which is what keeps the design steady state bit-exact."""
    trip = HystereticInterlock("22_1", trip_above=57.0, clear_below=55.0)
    assert trip.update_from_pv(43.0) is False
    assert trip.live is False


# --------------------------------------------------------------------------------------
# The reset-block band
# --------------------------------------------------------------------------------------

PV_22_2 = [140.7, 146.0, 152.0, 154.9, 155.0, 160.0, 152.0, 149.0, 148.0, 147.9, 140.7]


def test_the_banded_trip_follows_v1_over_a_full_excursion():
    trip = BandedInterlock("22_2", "Synthesis high-high pressure ESD",
                           trip_at=SYN_P_TRIP_BARA, reset_below=SYN_P_TRIP_RESET_BARA)
    latched = False
    for pv in PV_22_2:
        live, latched = _v1_banded(pv, latched)
        assert trip.update_from_pv(pv) == latched
        assert trip.live == live


def test_the_plant_cannot_be_reset_onto_the_edge_of_the_condition_it_tripped_on():
    """The band, stated as the operating rule it encodes."""
    trip = BandedInterlock("22_2", trip_at=SYN_P_TRIP_BARA,
                           reset_below=SYN_P_TRIP_RESET_BARA)
    trip.update_from_pv(160.0)
    assert trip.latched is True
    trip.update_from_pv(154.0)          # below the trip point, still inside the band
    assert trip.reset() is False
    trip.update_from_pv(147.0)          # out of the band
    assert trip.reset() is True
    assert trip.latched is False


def test_the_design_synthesis_pressure_leaves_the_esd_clear():
    """PT-329201 reads 140.7 bar a at design, so the latch is clear and the action is zero."""
    trip = BandedInterlock("22_2", trip_at=SYN_P_TRIP_BARA,
                           reset_below=SYN_P_TRIP_RESET_BARA)
    assert trip.update_from_pv(140.7) is False


def test_a_trip_that_has_not_latched_uses_the_trip_point_not_the_band():
    """150 bar a is above the reset band and below the trip point. It must not trip —
    reading the wrong threshold here would trip the plant 7 bar early."""
    trip = BandedInterlock("22_2", trip_at=SYN_P_TRIP_BARA,
                           reset_below=SYN_P_TRIP_RESET_BARA)
    assert trip.update_from_pv(150.0) is False
    assert trip.live is False


# --------------------------------------------------------------------------------------
# The set
# --------------------------------------------------------------------------------------

def _schedule() -> InterlockSet:
    """The plant's six trips, as V1 seeds them."""
    trips = InterlockSet()
    trips.add(Interlock("21_2", "Urea synthesis main trip"))
    trips.add(Interlock("21_4", "Loss of CO2 feed -> NH3 main interlock"))
    trips.add(Interlock("21_8", "HP NH3 pump 321P002A equipment fault"))
    trips.add(Interlock("21_10", "HP NH3 pump 321P002B equipment fault"))
    trips.add(HystereticInterlock("22_1", "322C001 over-temperature steam flood",
                                  trip_above=57.0, clear_below=55.0))
    trips.add(BandedInterlock("22_2", "Synthesis high-high pressure ESD",
                              trip_at=SYN_P_TRIP_BARA, reset_below=SYN_P_TRIP_RESET_BARA))
    return trips


def test_the_schedule_starts_completely_clear():
    trips = _schedule()
    assert trips.any_latched is False
    packet = trips.as_packet()
    assert set(packet) == {"trips", "trip_latched"}
    assert not any(packet["trips"].values())
    assert not any(packet["trip_latched"].values())


def test_reset_all_clears_every_resettable_trip_whose_condition_has_recovered():
    trips = _schedule()
    for tag in ("21_2", "21_4", "21_8", "21_10"):
        trips[tag].update(True)
    trips["22_2"].update_from_pv(160.0)
    trips["22_1"].update_from_pv(60.0)
    assert trips.any_latched is True

    #  Nothing clears while every condition is still live.
    assert trips.reset() == ()

    for tag in ("21_2", "21_4", "21_8", "21_10"):
        trips[tag].update(False)
    trips["22_2"].update_from_pv(140.7)
    cleared = trips.reset()
    assert set(cleared) == {"21_2", "21_4", "21_8", "21_10", "22_2"}
    #  22.1 is self-clearing and is never in a reset list — exactly V1's key tuple.
    assert "22_1" not in cleared
    assert trips["22_1"].latched is True


def test_reset_can_address_one_trip():
    trips = _schedule()
    trips["21_8"].update(True)
    trips["21_10"].update(True)
    trips["21_8"].update(False)
    trips["21_10"].update(False)
    assert trips.reset("21_8") == ("21_8",)
    assert trips["21_10"].latched is True


def test_resetting_a_tag_that_is_not_in_the_schedule_does_nothing_rather_than_raising():
    """A console sending a stale tag must not take the engine down with it."""
    assert _schedule().reset("99_9") == ()


def test_a_duplicate_trip_is_a_defect_not_an_update():
    trips = _schedule()
    with pytest.raises(ValueError, match="already in the set"):
        trips.add(Interlock("21_2"))


def test_the_packet_always_carries_every_trip():
    """A trip missing from a snapshot reads on a console as a trip that is healthy."""
    trips = _schedule()
    trips["21_2"].update(True)
    packet = trips.as_packet()
    assert len(packet["trips"]) == 6
    assert len(packet["trip_latched"]) == 6
    assert packet["trip_latched"]["21_2"] is True
    assert packet["trip_latched"]["21_4"] is False


# ======================================================================================
# AC4 PC21 (UD-MR-G00-FF-0004 pages 5, 7 and 20), decided 2026-10-09, handoff A-12
# ======================================================================================

DT = 0.1

#: The design: 321P002B running, A its standby, 323P001 running, CO2 to the stripper, both
#: valves open, every sub-cooling margin and hand switch healthy.
DESIGN = dict(p002a_running=False, p002b_running=True, p001_running=True, xv_322902_open=True,
              xv_321901_closed=False, xv_322901_open=True, fy_322403_low=False,
              pdy_321203_low=False, pdy_321204_low=False)


def _ac4() -> Unit21Trips:
    return Unit21Trips(5.0, 15.0, 5.0, 5.0, 10.0)


def _run(trips: Unit21Trips, seconds: float, **change) -> tuple[bool, bool, bool]:
    x = Unit21TripInputs(**{**DESIGN, **change})
    out = None
    for _ in range(round(seconds / DT)):
        out = trips.step(x, DT)
    return out


def test_the_timer_and_the_monoflop():
    """T an on-delay: true once its input has held TD, false at once when it drops; seeded settled.
    MONO: TP after each rising edge, none on its first tick."""
    t = OnDelayTimer(5.0)
    assert t.step(True, DT)
    assert not t.step(False, DT)
    assert [t.step(True, DT) for _ in range(50)].index(True) == 49
    m = Monoflop(10.0)
    assert not m.step(True, DT) and not m.step(True, DT)
    assert [m.step(x, DT) for x in (False, True)] == [False, True]
    assert sum(m.step(True, DT) for _ in range(200)) == 99


def test_the_design_is_healthy():
    assert _run(_ac4(), 30.0) == (False, False, False)


def test_no_pump_running_trips_21_2_and_both_pumps_flags_until_its_bypass():
    """Both machines stopped: 21.2 at once, 21.8 and 21.10 with it; HS-321634 turned, healthy
    5 s later."""
    trips = _ac4()
    assert _run(trips, 0.1, p002b_running=False) == (True, True, True)
    assert _run(trips, 4.9, p002b_running=False, hs_321634=True) == (True, True, True)
    assert _run(trips, 0.2, p002b_running=False, hs_321634=True) == (False, False, False)


def test_323p001_and_the_co2():
    """323P001 stopped: 21.2, its bypass 15 s; FY-322403 below L2: 21.2 at once, back 5 s after
    the CO2 returns, and HS-322606 bypasses it and XV-322902 both."""
    trips = _ac4()
    assert _run(trips, 0.1, p001_running=False)[0]
    assert _run(trips, 14.9, p001_running=False, hs_323604=True)[0]
    assert not _run(trips, 0.2, p001_running=False, hs_323604=True)[0]
    assert _run(trips, 0.1, fy_322403_low=True)[0]
    assert _run(trips, 4.9)[0] and not _run(trips, 0.2)[0]
    assert not _run(trips, 1.0, fy_322403_low=True, xv_322902_open=False, hs_322606=True)[0]
    assert _run(trips, 0.1, xv_322902_open=False)[0]


def test_a_pumps_own_inputs_trip_only_its_flag():
    """321P002B's sub-cooling below PDY-321204's L2: 21.10 alone; XV-321901 shut: both pumps'
    flags; XV-322901 not open with B running past its 5 s: 21.10; 321P002B stopping: its flag
    lost for the monoflop's 10 s, 21.2 with it while nothing runs."""
    trips = _ac4()
    assert _run(trips, 0.1, pdy_321204_low=True) == (False, False, True)
    assert _run(trips, 0.1, xv_321901_closed=True) == (False, True, True)
    assert _run(trips, 0.1, xv_322901_open=False) == (False, False, True)
    trips = _ac4()
    assert _run(trips, 0.1, p002a_running=True) == (False, False, False)
    assert _run(trips, 9.9, p002a_running=True, p002b_running=False) == (False, False, True)
    assert _run(trips, 0.2, p002a_running=True, p002b_running=False) == (False, False, False)


def test_the_trip_hand_switches_and_the_flags_have_no_reset():
    trips = _ac4()
    assert _run(trips, 0.1, hs_321603=True) == (True, True, True)
    assert _run(trips, 0.1, hs_321604=True)[0]
    assert not trips.flag_21_2.reset() and trips.flag_21_2.latched
    assert _run(trips, 0.1) == (False, False, False)
