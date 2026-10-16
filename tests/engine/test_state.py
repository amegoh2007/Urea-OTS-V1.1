"""The plant state — `ureasim.engine.state`.

Pins the recycle tears' structure (handoff A-10): every tear is a named field seeded with its
design flow; a consumer reads during the tick what its producer wrote on the tick before, and
nothing written during a tick reaches a reader before the tick is committed; a write to a name
that is not a tear is refused. And the clock: plant time is the step count times the fixed step.
V1's seeds are proved `==` in `tests/equivalence/test_state_equivalence.py`.
"""

from __future__ import annotations

import pytest

from ureasim.data.desorption_train import C002_M748_DES_KGH, C004_M739_DES_KGH
from ureasim.data.engine import DT_S
from ureasim.data.unit_323c005 import C005_M702_DES_KGH
from ureasim.engine.state import TEAR_NAMES, PlantClock, PlantState, TearState


def test_the_tears_that_cross_units_are_named_and_seeded_on_their_design_flows():
    """V1's eight cross-unit recycles, then the other cross-tick flows the schedule needs (session
    38): unit 324's condensates and vent inerts, 328C004's 741, LV-324501B's recycle, the steam
    users' draws and 911; and 323P001's 308 wash the scrubber takes (session 39); 323E011's
    envelope overflow to 323C005 (A-20, session 43); unit 324's condensers' cold ends to 328D003
    (B-31, session 54); 324F002's discharge temperature to 323C005 (B-97, session 55) — each
    seeded on its design."""
    tears = TearState()
    assert TEAR_NAMES == ("m_702_kgh", "m_756_kgh", "m_708_kgh", "m_748_kgh", "m_750_kgh",
                          "m_718a_kgh", "m_718b_kgh", "m_739_kgh", "m_719_kgh", "m_720_kgh",
                          "m_721_kgh", "m_759_kgh", "inert_706_kmolh", "m_741_kgh",
                          "m_recycle_324_kgh", "t_recycle_324_c", "w_recycle_324",
                          "steam_users_lp_kgh", "steam_users_9_kgh", "m_911_kgh", "m_308_kgh",
                          "m_e011_over_kgh", "t_e011_over_c", "t_719_c", "t_720_c", "t_721_c",
                          "t_759_c", "t_708_c")
    assert (tears.m_702_kgh, tears.m_748_kgh, tears.m_739_kgh) == (
        C005_M702_DES_KGH, C002_M748_DES_KGH, C004_M739_DES_KGH)
    assert (tears.m_719_kgh, tears.m_720_kgh, tears.m_721_kgh, tears.m_759_kgh) == (
        26768.0, 2758.0, 1763.0, 190.0)
    assert (tears.m_741_kgh, tears.m_recycle_324_kgh, tears.m_911_kgh) == (0.0, 0.0, 1105.0)
    assert tears.m_308_kgh == pytest.approx(36835.2, abs=0.1)
    assert (tears.m_e011_over_kgh, tears.t_e011_over_c) == (0.0, 45.0)
    assert (tears.t_719_c, tears.t_720_c, tears.t_721_c, tears.t_759_c) == (45.0, 40.0, 41.0, 55.0)
    assert tears.t_708_c == 121.0
    assert dict(tears.steam_users_lp_kgh) == {
        "918": 9027.0, "919": 18489.0, "926": 11230.0, "924": 390.0, "927": 1220.0,
        "929": 180.0, "931": 6495.0, "923": 2917.0, "928": 545.0, "965": 729.0, "999": 1000.0}
    # 322C001's trace steam at its rating, out of PFD 910's 1094 (decided 2026-10-07).
    assert dict(tears.steam_users_9_kgh) == {"920": 4158.0, "flood": 0.0, "trace": 90.0,
                                             "910": 1004.0, "912": 1435.0}


def test_a_consumer_reads_last_ticks_write_and_never_this_ticks():
    """The producer's value reaches its consumer exactly one tick later."""
    state = PlantState()
    produced = [900.0, 950.0, 1000.0]
    read = []
    for value in produced:
        read.append(state.tears.m_748_kgh)       # the consumer, during the tick
        writes = {"m_748_kgh": value}             # the producer, later in the same tick
        assert state.tears.m_748_kgh == read[-1]  # nothing changed under the reader
        state.end_tick(writes)
    assert read == [C002_M748_DES_KGH, 900.0, 950.0]
    assert state.tears.m_748_kgh == 1000.0


def test_an_unwritten_tear_holds_its_last_value():
    state = PlantState()
    state.end_tick({"m_750_kgh": 7000.0})
    state.end_tick({})
    assert state.tears.m_750_kgh == 7000.0 and state.tears.m_748_kgh == C002_M748_DES_KGH


def test_a_write_to_a_name_that_is_not_a_tear_is_refused():
    """A misspelt tear would otherwise be a new, silent recycle."""
    state = PlantState()
    with pytest.raises(KeyError, match="m_747_kgh"):
        state.end_tick({"m_747_kgh": 1.0})
    assert state.clock.tick == 0


def test_the_tears_cannot_be_written_in_place():
    with pytest.raises(AttributeError):
        TearState().m_748_kgh = 1.0  # type: ignore[misc]


def test_plant_time_is_the_step_count_times_the_step_exactly():
    """An hour is 36 000 steps to the bit, where a running sum of tenths is not."""
    clock = PlantClock(tick=36_000)
    assert clock.time_s == 3600.0
    total = 0.0
    for _ in range(36_000):
        total += DT_S
    assert total != 3600.0
    state = PlantState()
    for _ in range(3):
        state.end_tick({})
    assert state.clock.tick == 3 and state.clock.time_s == 3 * DT_S
