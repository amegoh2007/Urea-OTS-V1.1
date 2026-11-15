"""Trips 35.1, 35.3 and 35.4 — the granulator feed's protection, as AC4 PC35 executes it.

What this models
----------------
The logic of Uhde's DCS application software on unit 335's melt feed (decided 2026-11-15,
decision 228, handoff B-146): TRIP_35_1_FLAG1 while 335P001A / B run, TRIP_35_4_FLAG1 while the
granulator can take the melt, and 335P002A / B's motor-control interlock IC2, trip 35.3, on both
flags. Each flag is a live AND of its inputs (`DcsTripFlag`): no latch and no reset, as the
sheets draw none (decision 39's class). What holds the header down after a trip is the equipment:
LV-324501A, shut by its solenoid, opens LVSL-324501A's contact, which is itself an input of 35.4,
so the flag stays lost until the operator overrides the valve with HS-335201A and PIC-335201
opens it. 35.4 lost also withholds 335P002's permit; ten minutes on, the UF85 pumps' timer holds
35.4 lost as well, and HS-335620 must first let them run.

Source
------
UD-MR-G00-FF-0004 rev 01 ("Application Software AC4"), read on the page images (As-Built
§CXXX.2): PC35.5.1 (PDF page 282) and PC35.5.2 (page 283); 335P002A / B's MOTCON blocks (pages 232
and 233, As-Built §CXIX.2). UD-MR-324-FF-0002 page 2 for the two controllers' clamps. The trip
schedule UAN 01-3042 sheets 335/1+ and 335/2+ (`References/trip_and_interlock_schedule.md` §5.1 and
§5.2) for the actions.

Logic
-----
    TRIP_35_1_FLAG1 = (35P1AM1RS or 35P1BM1RS) and not PT-335202 < L2               PC35.5.1 .1, .3
    LVY-324501B     = TRIP_35_1_FLAG1 or HS-335201B                                  PC35.5.1 .2
    TRIP_35_4_FLAG1 = not T600(not 35P2AM1RS and not 35P2BM1RS) and TRIP_35_1_FLAG1
                      and HS-335621 and 35K1M1RS and TRIP_35_16_FLAG1 and TRIP_35_18_FLAG1
                      and not LVSL-324501A                                           PC35.5.2 .1-.3
    HVY-335602      = TRIP_35_4_FLAG1 or HS-335602                                   PC35.5.2 .4
    LVY-324501A     = TRIP_35_4_FLAG1 or HS-335201A                                  PC35.5.2 .5
    335P002 IC2     = (TRIP_35_1_FLAG1 and TRIP_35_4_FLAG1) or HS-335620             trip 35.3
    PIC-335201 CLAMP = (not TRIP_35_1_FLAG1 or not TRIP_35_4_FLAG1) and not HS-335201A
    LIC-324501 CLAMP = not TRIP_35_1_FLAG1 and not HS-335201B
A de-energised solenoid is the trip's action: LV-324501B and HV-335602 fail open, LV-324501A shuts.
T600 is PC35.5.2's timer, TD "10:0"; the scan does not resolve its mode, and it is read as an
on-delay of both pumps stopped (the process engineer's reading, decision 228; data gap 5).

What is held healthy
--------------------
The inputs outside the simulated plant: the sprayer air's PSLL-335202 (PT-335202 < L2, on 35.1); the
emergency-off push-button HS-335621, the fluidisation fan 335K001 running and the fans' trips 35.16
(335K002) and 35.18 (335K004), on 35.4. 35.4's other action, TIC-335015 to 125 deg C and manual, is
not built: the granulator is not simulated.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ureasim.control.interlocks import DcsTripFlag, OnDelayTimer

__all__ = ["Unit35TripInputs", "Unit35Actions", "HEALTHY_35", "Unit35Trips"]


@dataclass(frozen=True)
class Unit35TripInputs:
    """What AC4's PC35 flags read on one tick — the DCS's inputs, by tag."""

    #: 35P1AM1RS / 35P1BM1RS, either 335P001 running; 35P2AM1RS / 35P2BM1RS, either 335P002 running.
    p001_running: bool
    p002_running: bool
    #: LVSL-324501A, LV-324501A at its closed limit.
    lvsl_324501a: bool
    #: The four override keyswitches (DCS software): HS-335201A on LV-324501A and PIC-335201's
    #: clamp, HS-335201B on LV-324501B and LIC-324501's, HS-335602 on HV-335602, HS-335620 on
    #: 335P002's interlock.
    hs_335201a: bool = False
    hs_335201b: bool = False
    hs_335602: bool = False
    hs_335620: bool = False


@dataclass(frozen=True)
class Unit35Actions:
    """What PC35 commands on the header this tick: each solenoid de-energised, each controller's
    clamp reference while it is clamped [%] (None, free), and whether 335P002A / B may run."""

    lv_324501a_shut: bool = False
    lv_324501b_open: bool = False
    hv_335602_open: bool = False
    pic_335201_hold_pct: float | None = None
    lic_324501_hold_pct: float | None = None
    p002_permit: bool = True


#: Every flag healthy: no action on the header.
HEALTHY_35 = Unit35Actions()


@dataclass
class Unit35Trips:
    """AC4 PC35's flags 35.1 and 35.4 and 335P002's interlock 35.3, as the application software
    draws them (module docstring).

    Process utility
    ---------------
    The melt goes to the granulator only while it can be taken: a feed pump turning, the UF85
    pumps running or stopped for less than ten minutes, and the feed valve not shut. When the
    feed is lost the header is shut and drained, the evaporator's level passes to the recycle, and
    the UF85 pumps stop, so that the granulator does not block with melt it cannot spray.
    """

    td_p002_s: float
    lic_clampref_pct: float
    pic_clampref_pct: float
    flag_35_1: DcsTripFlag = field(default_factory=lambda: DcsTripFlag("35_1", "335P001A / B"))
    flag_35_4: DcsTripFlag = field(default_factory=lambda: DcsTripFlag("35_4",
                                                                         "granulator feed"))
    t_p002: OnDelayTimer = field(init=False)
    actions: Unit35Actions = HEALTHY_35

    def __post_init__(self) -> None:
        # Started, not settled: at the seed the pumps run and the timer stands at zero.
        self.t_p002 = OnDelayTimer(self.td_p002_s, elapsed_s=0.0)

    @property
    def p002_held(self) -> bool:
        """335P002A / B held stopped by their interlock 35.3."""
        return not self.actions.p002_permit

    def step(self, x: Unit35TripInputs, dt: float) -> Unit35Actions:
        """Evaluate the flags on this tick's inputs; return, and keep, what they command."""
        ok_1 = x.p001_running
        self.flag_35_1.set_healthy(ok_1)
        p002_lost = self.t_p002.step(not x.p002_running, dt)
        ok_4 = not p002_lost and ok_1 and not x.lvsl_324501a
        self.flag_35_4.set_healthy(ok_4)
        self.actions = Unit35Actions(
            lv_324501a_shut=not (ok_4 or x.hs_335201a),
            lv_324501b_open=not (ok_1 or x.hs_335201b),
            hv_335602_open=not (ok_4 or x.hs_335602),
            pic_335201_hold_pct=(self.pic_clampref_pct if not (ok_1 and ok_4) and not x.hs_335201a
                                 else None),
            lic_324501_hold_pct=self.lic_clampref_pct if not ok_1 and not x.hs_335201b else None,
            p002_permit=(ok_1 and ok_4) or x.hs_335620)
        return self.actions
