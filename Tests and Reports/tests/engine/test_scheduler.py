"""The tick — `ureasim.engine.scheduler` — on a toy schedule and on the plant.

A tick steps every unit once in the schedule's order, resolves each argument from its declared
source, and commits the recycle tears and the clock at its end. These tests pin the delays the
sources carry — a ``Result`` the same tick, a later unit's ``State`` and a ``Tear`` exactly one tick
late — the fixed step, and on the plant: every unit once a tick, and the design held from a start
at 100 % load, the LP header at the operators' 4.0 bar g.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import pytest

from ureasim.data import unit_322_loop as loop
from ureasim.data.unit_322e002 import T_PROD_DES_C
from ureasim.data.unit_323 import E010_PCHEST_DES_BARA
from ureasim.data.unit_329 import P_LP_BARA
from ureasim.engine import plant as P
from ureasim.engine.schedule import (
    DeclaredTear,
    Operator,
    Result,
    Schedule,
    ScheduleError,
    State,
    Step,
    Tear,
)
from ureasim.engine.scheduler import Scheduler
from ureasim.engine.state import PlantState


@dataclass
class _Counter:
    """A toy unit: its state counts its own steps."""

    n: int = 0


@dataclass(frozen=True)
class _Out:
    n: int
    seen: tuple


def _toy():
    seen = []

    def run_a(plant, a, dt):
        plant.units["A"].n += 1
        seen.append(("A", a["b_n"], a["m"], a["hic"]))
        return _Out(plant.units["A"].n, ())

    def run_b(plant, a, dt):
        plant.units["B"].n += 1
        seen.append(("B", a["a_n"]))
        return _Out(plant.units["B"].n * 10, ())

    s = Schedule(
        steps=(Step("A", "a", "000", 1, {"b_n": State("B", "n"), "m": Tear("m_702_kgh"),
                                         "hic": Operator("HIC")}, run_a),
               Step("B", "b", "000", 2, {"a_n": Result("A", "n")}, run_b)),
        tears=(DeclaredTear(State("B", "n"), "A", "B steps later"),
               DeclaredTear(Tear("m_702_kgh"), "A", "B's output, committed")),
        tear_writes={"m_702_kgh": Result("B", "n")})
    plant = PlantState(units={"A": _Counter(), "B": _Counter()}, operator={"HIC": 50.0})
    return Scheduler(s, plant), seen


def test_a_result_is_same_tick_and_a_state_and_a_tear_one_tick_late():
    """On tick k, B reads A's result of tick k; A reads B's state and the tear as B left them at
    the end of tick k - 1 — the tear its design seed on the first tick."""
    sch, seen = _toy()
    first = sch.plant.tears.m_702_kgh
    for _ in range(3):
        sch.tick()
    assert seen == [("A", 0, first, 50.0), ("B", 1),
                    ("A", 1, 10, 50.0), ("B", 2),
                    ("A", 2, 20, 50.0), ("B", 3)]
    assert sch.plant.clock.tick == 3 and sch.plant.tears.m_702_kgh == 30


def test_the_step_is_fixed():
    sch, _ = _toy()
    with pytest.raises(ValueError, match="fixed"):
        sch.tick(0.25)


def test_a_schedule_is_checked_before_the_first_tick():
    sch, _ = _toy()
    bad = replace(sch.schedule, tears=())
    with pytest.raises(ScheduleError):
        Scheduler(bad, sch.plant)


# --------------------------------------------------------------------------------------
# The plant
# --------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def plant_minute():
    """The plant from its design seed, one minute of ticks."""
    schedule, plant = P.build_plant()
    sch = Scheduler(schedule, plant)
    reports = [sch.tick() for _ in range(600)]
    return sch, reports


def test_every_unit_steps_exactly_once_a_tick(plant_minute):
    _, reports = plant_minute
    assert all(set(r.runs) == set(P.ORDER) and set(r.runs.values()) == {1} for r in reports)
    assert [r.tick for r in reports] == list(range(1, 601))


def test_the_plant_holds_the_pfd_on_its_plugged_tubes(plant_minute):
    """The tubes plugged at the last turnaround, each exchanger's conductance re-anchored on the
    tubes still in service (decided 2026-10-28, handoff B-113 (b)): the plant's first tick is the
    PFD's to the bit — 322E002's product at 170.0 C on a saturated melt, 322E003 condensing its
    whole demand, 323E010's chest on PFD 926's 2.5 bar a. What the plugging leaves is the loop's
    vessels less the plugged bores; V1's clean vessels are the harnesses' switch."""
    sch, reports = plant_minute
    r = reports[0].results
    assert (r["322E002"].holdup.condenser.t_prod, r["322E002"].holdup.sat_frac) == (T_PROD_DES_C,
                                                                                    1.0)
    assert r["322E003"].rho_cond == 1.0
    assert r["323F010"].chest_p_bara == E010_PCHEST_DES_BARA
    assert sch.plant.units["PT-329201"].vessels_m3 == loop.SYN_LOOP_V_M3
    assert loop.SYN_LOOP_V_M3 - loop.SYN_LOOP_V_V1_M3 == pytest.approx(28.83 - 24.7 - 0.2222,
                                                                       abs=1e-4)


def test_the_tears_carry_their_producers_outputs_one_tick_late(plant_minute):
    """At every commit each tear holds what its producer made that tick; 323C005 reads it on the
    next."""
    sch, reports = plant_minute
    last = reports[-1].results
    for name, src in P.TEAR_WRITES.items():
        from ureasim.engine.schedule import lookup
        assert getattr(sch.plant.tears, name) == lookup(last[src.unit], src.field), name


def test_the_plant_started_at_full_load_holds_its_lp_header_at_4_barg(plant_minute):
    """Started on the design seed at 100 % load, the assembled plant holds the LP header at the
    operators' 4.0 bar g, 5.01325 bar a (handoff B-69): within 0.3 mbar over the minute, the
    users drawing their PFD rows on their valves (B-68, B-73) — the motive steam, FV-329401 and
    the chests within 0.02 % of their rows. The units' own design points meet their
    neighbours' to a few parts in 10^5 (stage 1's held melt boils 1.6 kg/h, B-62; the stripper's
    bottoms leave its sump 1.6 kg/h under LV-322501's design drain), which moved the header 0.028
    mbar; 322R001's top node, settling 0.02 K over its pinned 183 C, now stands on the liquor's
    bubble point and flashes some 35 kg/h (handoff B-92, decided 2026-10-14), which moves it 0.27
    mbar (0.034 mbar with the synthesis loop live in session 39, 0.024 with it held). Since the reactor
    ceiling's margin (decision 301) the top no longer flashes at the seed, and 918 draws 9 025.12 kg/h,
    0.0208 % under its row: it is held within 0.025 % (decision 305), the other rows within 0.02 %."""
    sch, reports = plant_minute
    p = [r.results["329"].p_lp_bara for r in reports]
    assert max(abs(x - P_LP_BARA) for x in p) < 3e-4
    users = sch.plant.tears.steam_users_lp_kgh
    for stream, row in (("924", 390.0), ("927", 1220.0), ("929", 180.0), ("931", 6495.0),
                        ("918", 9027.0), ("919", 18489.0), ("926", 11230.0)):
        assert users[stream] == pytest.approx(row, rel=2.5e-4 if stream == "918" else 2e-4), stream
