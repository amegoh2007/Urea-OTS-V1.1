"""The Phase 7 operating procedures — what both engines are put through.

Each scenario is data: an initial condition, a script of commands at plant times, a disturbance,
a stop rule, and the packet paths compared. The procedures are V1's own wherever V1 has one, so the
comparison is of the same exercise:

* **cold start** — V1's ``test_transient_coldstart.py``: a cold, empty, depressurised synthesis
  loop (PT-329201 at 5.7 bar g, the reactor, 322E002, 322E001 and 322E003 holdups empty) with the
  design feed lineup on; PT-329201's rise identified as a first-order-plus-dead-time step by Smith's
  two-point method and set against the 3 June 2025 start-up trend's band (tau 2884-4055 s, dead
  time at most 572 s, final 137.5-150.5 bar g).
* **tempered-water loss** — V1's ``test_ccw_loss_chain.py`` phase 2: both tempered-water pumps,
  329P006A and B, stopped; 322E003 loses its cooling and the loop pressure climbs. V1's trip 22.2
  latches at its high-high, cutting the CO2 and both HP ammonia pumps, and V1 runs to ten minutes
  past the latch. The port has no 22.2 (decision 189: no plant document draws a trip on the loop's
  pressure, whose limit is SV32251 / SV32252) and runs the procedure's whole duration.
* **HPCC rupture** — V1's ``tests/run_hpcc_rupture.py``: a 322E002 tube leak in steps of 0, 2.5,
  5, 10, 20 and 40 t/h, ten minutes each, the ammonia feed drum's level held (continuous make-up) so
  trip 21.2 stays dormant. V1 injects the shell's water into the process; the port runs its own
  malfunction, process into the shell on the live differential at those rates at design (handoff
  B-82, decided 2026-10-09) — the same exercise on each engine's leak.
* **vacuum break** — 324F002's motive steam lost (HIC-329605 to 0 %) for fifteen minutes, then
  restored to where each engine had it: 324F001's vacuum and, through 324E002's shell, 323F010's
  break and recover (handoff B-22, whose decision this informs).
* **steady state** — the design seed, 1750 MTPD at 100 % load, left alone for an hour: every
  numeric leaf of both packets sampled, so the comparison covers the whole console, not a list.

Every scenario also watches 328C004's and 323E011's pressure on every tick (handoff B-51).
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: The fixed physics step [s] (A-14).
DT = 0.1

#: Paths every scenario samples: the synthesis loop, its feeds, the trips, and the recirculation
#: and evaporation states a synthesis upset reaches.
CORE_TAGS = (
    "SCRUB_322E003.P_overflow",            # PT-329201 [bar a]
    "REACT_322R001.P_bara",
    "CO2_FEED.FY_322403",                  # CO2 to the loop [t/h]
    "CO2_FEED.XV_322902",
    "FI_321401",                           # NH3 to the loop
    "pumpA.on", "pumpB.on",
    "REACT_322R001.AT_322701",             # reactor N/C
    "REACT_322R001.X_conv",
    "REACT_322R001.W_feed",
    "REACT_322R001.LT_322504",
    "HPCC_322E002.LT_322E002",
    "HPCC_322E002.TT_322012",
    "SCRUB_322E003.TT_322002",
    "SCRUB_322E003.LT_329501",
    "STRIP_322E001.LI_322501",
    "STRIP_322E001.bot_mass_pct.Urea",
    "STRIP_322E001.TT_322004",
    "RECIRC_323.C003.P_bara",
    "RECIRC_323.F004.P_bara",
    "RECIRC_323.F010.P_bara",
    "RECIRC_323.D002.urea_pct",
    "LPCC_3232.E011.P_bara",
    "ABSORB_328.C001.P_bara",
    "ABSORB_328.C001.TT_322015",
    "DESORB_328.C004.P_bara",
    "DESORB_328.C004.LI_328505",
    "EVAP_324.E001.PT_324201",
    "EVAP_324.E001.TT_324001",
    "EVAP_324.E001.urea_pct",
    "EVAP_324.E003.PT_324204",
    "EVAP_324.E003.urea_pct",
    "trip_latched.21_2", "trip_latched.22_1",
)

#: Per-tick watches for ringing (handoff B-51): name -> (V1 state field, the rewrite's unit).
WATCHES = {
    "328C004 P [bar a]": ("a328_c004_P", "328C004"),
    "323E011 P [bar a]": ("r3232_e011_P", "323E011"),
    "PT-329201 [bar a]": ("p_syn_bara", "PT-329201"),
}


@dataclass(frozen=True)
class Scenario:
    """One operating procedure, as both engines are put through it."""

    name: str
    title: str
    #: The longest the procedure runs [s] of plant time.
    duration_s: float
    #: Packet sampling interval [s].
    sample_s: float
    #: (plant time [s], command) — sent before the first tick that starts at or after the time.
    #: A command field "@initial" is replaced by the value that engine had at time zero.
    script: tuple = ()
    #: An initial condition the drivers know by name, or None for the design seed.
    initial: str | None = None
    #: A disturbance the drivers know by name: a schedule of (plant time [s], magnitude).
    disturbance: tuple | None = None
    #: (trip key, tail [s]): stop that long after the trip latches.
    stop_after_trip: tuple | None = None
    #: The packet paths sampled; empty for every numeric and boolean leaf of the packet.
    tags: tuple = CORE_TAGS
    notes: str = field(default="")


SCENARIOS = {
    "cold_start": Scenario(
        name="cold_start",
        title="Cold start: an empty, depressurised synthesis loop, the feeds on",
        duration_s=16000.0, sample_s=30.0, initial="cold_loop",
        notes="V1 test_transient_coldstart.py; DCS band from the 3 June 2025 start-up trend."),
    "tempered_water_loss": Scenario(
        name="tempered_water_loss",
        title="Tempered-water loss: both 329P006 pumps stopped, the loop to its limit",
        duration_s=48000.0, sample_s=10.0,
        script=((60.0, {"type": "pump_toggle", "id": "329P006A", "on": False}),
                (60.0, {"type": "pump_toggle", "id": "329P006B", "on": False})),
        stop_after_trip=("22_2", 600.0),
        notes="V1 test_ccw_loss_chain.py phase 2; the stop is V1's 22.2, which the port does "
              "not publish (decision 189)."),
    "hpcc_rupture": Scenario(
        name="hpcc_rupture",
        title="HPCC rupture: a 322E002 tube leak, 0 to 40 t/h in six steps",
        duration_s=3600.0, sample_s=10.0, initial="pinned_drum",
        disturbance=((0.0, 0.0), (600.0, 2500.0), (1200.0, 5000.0), (1800.0, 10000.0),
                     (2400.0, 20000.0), (3000.0, 40000.0)),
        notes="V1 tests/run_hpcc_rupture.py: water into the HPCC product [kg/h]; the port's "
              "tube leak, process into the shell, at that rate at design (B-82)."),
    "vacuum_break": Scenario(
        name="vacuum_break",
        title="Vacuum break: 324F002's motive steam lost for 15 minutes, then restored",
        duration_s=2700.0, sample_s=5.0,
        script=((60.0, {"type": "hic9605_set", "op": 0.0}),
                (960.0, {"type": "hic9605_set", "op": "@initial"})),
        notes="HIC-329605 to 0 %, restored at 960 s to the engine's own design opening."),
    "steady_state": Scenario(
        name="steady_state",
        title="Steady state: the design seed, 1750 MTPD at 100 % load, an hour untouched",
        duration_s=3600.0, sample_s=60.0, tags=(),
        notes="Every packet leaf; the design point both engines are anchored on (PFD 1750 MTPD)."),
}


def disturbance_at(scenario: Scenario, t_s: float) -> float:
    """The disturbance's magnitude in force at plant time ``t_s`` (a step schedule)."""
    value = 0.0
    for t0, v in scenario.disturbance or ():
        if t_s >= t0:
            value = v
    return value


__all__ = ["DT", "CORE_TAGS", "WATCHES", "Scenario", "SCENARIOS", "disturbance_at"]
