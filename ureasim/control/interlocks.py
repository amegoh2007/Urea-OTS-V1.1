"""Safety interlocks — the logic solver, not the actions it commands.

What this models
----------------
The plant's trip schedule: 21.2 the urea synthesis's main trip and 21.8 / 21.10 the HP ammonia
pumps' trips, built as Uhde's DCS application software executes them (AC4, PC21; decided
2026-10-09, handoff A-12); and 22.1 the LP absorber over-temperature steam flood. V1's 22.2, a
synthesis high-high pressure shutdown, is not built: no plant document draws it (decision 189).

Source
------
Uhde's "Application Software AC4", UD-MR-G00-FF-0004 rev 01 (ABB Advant PC diagrams): PC21.1.1
(page 5, TRIP_21_8_FLAG1), PC21.1.2 (page 7, TRIP_21_10_FLAG1) and PC21.5.1 (page 20,
TRIP_21_2_FLAG1); PC22.5.1 for I 22.1. V1 ``backend/main.py``, the "Trips (P1-2 stateful
interlocks)" block of ``step_sim`` and the ``trip_reset`` command handler, for the latch and the
class 22.1 uses. In V1 the logic and the actions it commands are written together inline; here they
are separated — see below.

What is here and what is not
----------------------------
This module decides **whether a trip is latched**. It does NOT stop a pump, shut a valve or
force a controller to manual. Those actions belong to the unit that owns the equipment, for
two reasons that are not stylistic:

  * a trip's action list is plant knowledge — 21.2 closes XV-322901 and 21.4 deliberately
    does not — and plant knowledge does not belong in a logic block;
  * the same action can be commanded by several trips, and the equipment must not learn to
    take orders from one of them in particular.

So a unit reads ``interlock.latched`` and does what its own trip schedule says.

Why a latch is not a comparison
-------------------------------
Every behaviour in this module exists because a real logic solver does not simply follow its
initiator, and a trainee has to learn the difference:

  * **it latches.** Once the condition is met the trip holds, even after the condition clears.
    A plant that recovered on its own would teach an operator that a trip is a transient.
  * **it cannot be reset while the condition is live.** Pressing reset on an active initiator
    does nothing at all, which is the correct and the frustrating behaviour.
  * **arming.** A trip whose initiator is trivially true on an idle plant must not latch itself
    during a black start.
  * **self-clearing, for one trip only.** 22.1 is a protective action rather than a shutdown:
    a limit with hysteresis, as the DCS's analogue input evaluates it, with no reset button.
    What it does to XV-322915 is the unit's (`units.absorption.vent_line.xv_322915_open`).
  * **a DCS trip flag is not a latch.** AC4's 21.2, 21.8 and 21.10 are live AND gates — a healthy
    flag, the trip while any input is lost — with no reset button. What holds the plant down
    after one is the equipment: a pump's motor control stops it and it stays stopped until it is
    started again; XV-321901 and XV-322901 are SR flip-flops the flag resets and only their hand
    switches set again.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class Interlock:
    """A latching trip with an optional arming condition.

    Process utility
    ---------------
    The ordinary case: 21.2, 21.4, 21.8 and 21.10. The initiator is evaluated every tick and
    published as ``live``; the latch is what the plant acts on. An operator clears the latch
    only once the initiator has gone away.

    ``armed`` is the difference between a trip that protects a running plant and one that
    prevents it from ever starting. A pump that is stopped cannot be faulted into a trip, and
    a plant that has not been given CO2 yet has not lost it.
    """

    #: Trip number as the schedule writes it, e.g. "21_2".
    tag: str
    #: What the trip protects, in one line, for the annunciator.
    description: str = ""
    #: The initiator as evaluated this tick. Published, never acted on directly.
    live: bool = False
    #: The latch. This is what the plant acts on.
    latched: bool = False

    #: Whether an operator can clear this latch. False only for a self-clearing action.
    operator_resettable: bool = True

    def update(self, condition: bool, armed: bool = True) -> bool:
        """Evaluate the initiator for one tick and return the latch state.

        The latch is set on a live and armed condition, and never cleared here — clearing is
        an operator action, which is the whole point of a latch.
        """
        self.live = bool(condition)
        if self.live and armed:
            self.latched = True
        return self.latched

    def reset(self) -> bool:
        """Operator clear. Returns True when the latch actually cleared.

        Refused while the initiator is still live. The return value matters to the caller:
        V1 resolves a pump's mechanical fault on a SUCCESSFUL reset, so that "reset" means
        "cause resolved" and the pump can be restarted without immediately re-tripping. A
        refused reset must not resolve anything.
        """
        if self.live or not self.operator_resettable:
            return False
        self.latched = False
        return True


@dataclass
class HystereticInterlock(Interlock):
    """A protective action that sets on a high limit and clears itself on a lower one.

    Process utility
    ---------------
    Trip 22.1, the LP absorber steam flood: TT-322015's high-high limit, set above
    ``trip_above`` and cleared below ``clear_below``. The DCS (AC4, PC22.5.1) holds no latch on
    it and has no reset for it; what it does to XV-322915 is the unit's to model.

    The gap between the two thresholds is deliberate: without it the valve would chatter on a
    measurement sitting on its limit.
    """

    trip_above: float = float("inf")
    clear_below: float = float("-inf")
    operator_resettable: bool = False
    #: A non-finite PV is a live initiator (decision 187, handoff B-131); False is V1's
    #: comparison. A class switch, so a saved exercise keeps its shape.
    nan_is_live: ClassVar[bool] = True

    def update_from_pv(self, pv: float) -> bool:
        """Evaluate against a process value and return the latch state; a failed measurement
        sets the action and holds it."""
        if self.nan_is_live and not math.isfinite(pv):
            self.live = self.latched = True
            return self.latched
        self.live = pv > self.trip_above
        if self.live:
            self.latched = True
        elif pv < self.clear_below:
            self.latched = False
        return self.latched


@dataclass
class DcsTripFlag(Interlock):
    """A trip flag of Uhde's DCS application software: the healthy AND of its inputs, live.

    Process utility
    ---------------
    ``TRIP_21_2_FLAG1``, ``TRIP_21_8_FLAG1``, ``TRIP_21_10_FLAG1``: true while every input is
    healthy, false — the trip — while any is lost. Published as an interlock whose ``live`` and
    ``latched`` both read the trip, so the annunciator shows it; it has no reset (decision 39's
    class: no latch or reset the logic does not draw).
    """

    operator_resettable: bool = False

    def set_healthy(self, healthy: bool) -> bool:
        """Take the flag's value this tick; return whether the trip is active."""
        self.live = self.latched = not healthy
        return self.latched


@dataclass
class OnDelayTimer:
    """ABB Advant's timer element T, read as an on-delay: true once its input has held for TD.

    Process utility
    ---------------
    A healthy signal a trip flag only accepts once it has stood for its delay — a pump running
    5 s, CO2 flowing 5 s. The scans draw the element's mode as a symbol they do not resolve; the
    on-delay is the process engineer's reading (2026-10-09). Seeded settled, the plant at its seed
    having held every input for longer than any delay.
    """

    td_s: float
    elapsed_s: float | None = None

    def __post_init__(self) -> None:
        if self.elapsed_s is None:
            self.elapsed_s = self.td_s

    def step(self, i: bool, dt: float) -> bool:
        """Advance one tick on input ``i``; return the output."""
        self.elapsed_s = min(self.elapsed_s + dt, self.td_s) if i else 0.0
        return i and self.elapsed_s >= self.td_s - 1e-9


@dataclass
class Monoflop:
    """ABB Advant's element MONO with RTG set: a pulse of TP on each rising edge of its input.

    Process utility
    ---------------
    PC21.1.1's ten seconds after a pump stops, during which its trip flag is false and its motor
    control will not start it again.
    """

    tp_s: float
    remaining_s: float = 0.0
    #: The input on the tick before; None until the first tick, which sees no edge.
    previous: bool | None = None

    def step(self, i: bool, dt: float) -> bool:
        """Advance one tick on input ``i``; return the output."""
        if i and self.previous is False:
            self.remaining_s = self.tp_s
        self.previous = i
        out = self.remaining_s > 1e-9
        self.remaining_s = max(self.remaining_s - dt, 0.0)
        return out


@dataclass(frozen=True)
class Unit21TripInputs:
    """What AC4's PC21 trip flags read on one tick — the DCS's inputs, by tag."""

    #: 21P2AM1RS / 21P2BM1RS, 321P002A / B running; 23P1AM1RS / 23P1BM1RS, 323P001A / B running.
    p002a_running: bool
    p002b_running: bool
    p001_running: bool
    #: XVSH-322902, XV-322902 open; XVSL-321901, XV-321901 closed; XVSH-322901, XV-322901 open.
    xv_322902_open: bool
    xv_321901_closed: bool
    xv_322901_open: bool
    #: FY-322403 below its L2; PDY-321203 / 204 below their L2.
    fy_322403_low: bool
    pdy_321203_low: bool
    pdy_321204_low: bool
    #: The hand switches: the bypasses HS-321634, HS-323604 and HS-322606 turned; HS-321603 and
    #: HS-321604 turned (the flag's inputs 5 and 6 lost).
    hs_321634: bool = False
    hs_323604: bool = False
    hs_322606: bool = False
    hs_321603: bool = False
    hs_321604: bool = False
    #: TRIP_84_8_FLAG1, the Safeguard SG1's instrument-air trip (UD-MR-G00-FF-0006 PC15.1.5: two of
    #: PT-384207A / B / C below L2, latched until RS_TR_84_8), healthy — the instrument air is not
    #: simulated; PT-321211 / 221 below and ST-321952 / 953 above their limits — not modelled,
    #: healthy (handoff Open data gaps).
    trip_84_8_healthy: bool = True
    pt_321211_low: bool = False
    pt_321221_low: bool = False
    st_321952_high: bool = False
    st_321953_high: bool = False


@dataclass
class Unit21Trips:
    """AC4 PC21's trip flags 21.2, 21.8 and 21.10, as the application software draws them.

    Process utility
    ---------------
    The synthesis's ammonia side is held only while it can run: a pump turning, the carbamate
    recycle pump turning, CO2 reaching the stripper, and each HP ammonia pump on a healthy
    suction with its discharge path open.

    Logic (UD-MR-G00-FF-0004)
    -------------------------
    TRIP_21_2_FLAG1 (PC21.5.1, page 20) = AND of
        T5(321P002A running or 321P002B running or HS-321634),
        T15(323P001A running or 323P001B running or HS-323604),
        XVSH-322902 or HS-322606,
        [T5(not FY-322403 < L2) or HS-322606] and TRIP_84_8_FLAG1,
        not HS-321603, not HS-321604;
    TRIP_21_8_FLAG1 (PC21.1.1, page 5) = AND of
        TRIP_21_2_FLAG1, not PT-321211 < L2, not ST-321952 > H2, not XVSL-321901,
        not PDY-321203 < L2,
        [not T5(321P002A running) or XVSH-322901] and not MONO10(not 321P002A running);
    TRIP_21_10_FLAG1 (PC21.1.2, page 7) the same on 321P002B, PT-321221, ST-321953 and
        PDY-321204.
    Each T an on-delay of TD seconds, MONO a retriggerable pulse of TP seconds.
    """

    td_pumps_s: float
    td_p001_s: float
    td_fy_s: float
    td_run_s: float
    tp_stop_s: float
    flag_21_2: DcsTripFlag = field(default_factory=lambda: DcsTripFlag("21_2",
                                                                         "urea synthesis main"))
    flag_21_8: DcsTripFlag = field(default_factory=lambda: DcsTripFlag("21_8", "321P002A"))
    flag_21_10: DcsTripFlag = field(default_factory=lambda: DcsTripFlag("21_10", "321P002B"))
    t_pumps: OnDelayTimer = field(init=False)
    t_p001: OnDelayTimer = field(init=False)
    t_fy: OnDelayTimer = field(init=False)
    t_run_a: OnDelayTimer = field(init=False)
    t_run_b: OnDelayTimer = field(init=False)
    mono_a: Monoflop = field(init=False)
    mono_b: Monoflop = field(init=False)

    def __post_init__(self) -> None:
        self.t_pumps = OnDelayTimer(self.td_pumps_s)
        self.t_p001 = OnDelayTimer(self.td_p001_s)
        self.t_fy = OnDelayTimer(self.td_fy_s)
        self.t_run_a = OnDelayTimer(self.td_run_s)
        self.t_run_b = OnDelayTimer(self.td_run_s)
        self.mono_a = Monoflop(self.tp_stop_s)
        self.mono_b = Monoflop(self.tp_stop_s)

    def step(self, x: Unit21TripInputs, dt: float) -> tuple[bool, bool, bool]:
        """Evaluate the three flags on this tick's inputs; return 21.2's, 21.8's and 21.10's
        trips (True while the flag is lost)."""
        pumps = self.t_pumps.step(x.p002a_running or x.p002b_running or x.hs_321634, dt)
        p001 = self.t_p001.step(x.p001_running or x.hs_323604, dt)
        co2_line = x.xv_322902_open or x.hs_322606
        fy = (self.t_fy.step(not x.fy_322403_low, dt) or x.hs_322606) and x.trip_84_8_healthy
        ok_2 = pumps and p001 and co2_line and fy and not x.hs_321603 and not x.hs_321604
        self.flag_21_2.set_healthy(ok_2)

        def pump_flag(running, timer, mono, pt_low, st_high, pdy_low):
            started = timer.step(running, dt)
            stopping = mono.step(not running, dt)
            return (ok_2 and not pt_low and not st_high and not x.xv_321901_closed
                    and not pdy_low and (not started or x.xv_322901_open) and not stopping)

        self.flag_21_8.set_healthy(pump_flag(x.p002a_running, self.t_run_a, self.mono_a,
                                             x.pt_321211_low, x.st_321952_high,
                                             x.pdy_321203_low))
        self.flag_21_10.set_healthy(pump_flag(x.p002b_running, self.t_run_b, self.mono_b,
                                              x.pt_321221_low, x.st_321953_high,
                                              x.pdy_321204_low))
        return self.flag_21_2.latched, self.flag_21_8.latched, self.flag_21_10.latched


@dataclass
class InterlockSet:
    """The plant's trip schedule as one addressable object.

    Process utility
    ---------------
    The instructor panel and the annunciator both want every trip at once, and the operator's
    reset button may address one trip or all of them. Holding them in one set is also what
    keeps the published packet's shape fixed: a trip that is missing from a snapshot reads on
    a console as a trip that is healthy.
    """

    interlocks: dict[str, Interlock] = field(default_factory=dict)

    def add(self, interlock: Interlock) -> Interlock:
        if interlock.tag in self.interlocks:
            raise ValueError(f"interlock {interlock.tag} is already in the set")
        self.interlocks[interlock.tag] = interlock
        return interlock

    def __getitem__(self, tag: str) -> Interlock:
        return self.interlocks[tag]

    @property
    def any_latched(self) -> bool:
        return any(i.latched for i in self.interlocks.values())

    def reset(self, tag: str | None = None) -> tuple[str, ...]:
        """Operator clear of one trip, or of every resettable trip when ``tag`` is None.

        Returns the tags that actually cleared. A trip whose initiator is still live, and a
        self-clearing one, are both silently skipped — which is what the plant does, and the
        operator learns it from the annunciator not changing.
        """
        targets = (self.interlocks.values() if tag is None
                   else [self.interlocks[tag]] if tag in self.interlocks else [])
        return tuple(i.tag for i in targets if i.reset())

    def as_packet(self) -> dict:
        """Live initiators and latches, in the two-dictionary shape V1 publishes."""
        return {
            "trips": {tag: i.live for tag, i in self.interlocks.items()},
            "trip_latched": {tag: i.latched for tag, i in self.interlocks.items()},
        }


__all__ = [
    "Interlock",
    "HystereticInterlock",
    "DcsTripFlag",
    "OnDelayTimer",
    "Monoflop",
    "Unit21TripInputs",
    "Unit21Trips",
    "InterlockSet",
]
