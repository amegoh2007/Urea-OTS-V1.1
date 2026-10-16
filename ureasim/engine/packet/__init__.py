"""The console packet — the plant after a tick, on V1's WebSocket key paths.

What this is
------------
Every console renders one dictionary: V1's ``step_sim`` return value, which V1's push task sent to
every browser at 10 Hz with a ``_health`` block stapled on. The screens bind into it by dot-path
(``RECIRC_323.C003.TIC_323007.pv``, ``controllers.SIC_321950.mode``), the trend window resolves its
pens through the same paths, and the stream inspector reads its ``STREAMS``. `build_packet`
publishes that dictionary from the port's plant: the same keys, nested the same way, rounded as V1
rounds them, each value the port's equivalent of V1's — so the overlay bindings converted from V1
(`ureasim.data.screen_layout`) resolve unchanged.

Where the port has decided a divergence the value is the port's (the module of each block names
them). A quantity the port does not model publishes None under V1's key, and a console shows it
as ``--``: V1's unit-328 energy ledger (unit 335's UF85 cascade publishes since session 55,
decision 123).

What is not published
---------------------
V1's five diagnostic blocks — ``RECYCLE_TEAR_RESIDUAL``, ``sm_diagnostics``,
``CONSEQUENCE_TRANSPORT``, ``RECYCLE_CLASSIFICATION`` and ``SPECIES_323_324`` — are V1's solver
audit: its internal dictionaries, its anchors' clip residuals, its flash cache. No screen, pen or
popup reads them, and the port's own results, which the historian records, carry its audit.
Decided 2026-10-03 (handoff A-19, option (a)): they stay out — engine-internal telemetry no plant
screen shows, which would cost every console bandwidth and give it values it does not own.

The blocks
----------
======================  =================================================  ====================
key(s)                  what                                               module
======================  =================================================  ====================
``t``, ``t_sim``        the desktop clock and the plant clock              here
``FI_321401`` ...       unit 321's indications, ``pumpA``, ``pumpB``       `unit_321`
``EJ_322F001`` ...      the synthesis loop                                 `synthesis`
``RECIRC_323``          the liquor train                                   `recirculation`
``LPCC_3232``           the LP condensers and 323C005                      `recirculation`
``DESORB_328``          desorption and hydrolysis                          `desorption`
``ABSORB_328``          322C001 and 328D003                                `desorption`
``EVAP_324``            evaporation and the vacuum train                   `evaporation`
``STEAM_SYSTEM``        unit 329                                           `steam`
``STREAMS``             the stream inspector's records                     `streams`
``BOUNDARY_SINKS``      the overflows leaving the plant (not V1's, A-15)   `status`
``ANALYSERS``           AI-329701, the drums' solids (not V1's, B-90)      `steam`
``HAND_SWITCHES``       the keyswitches' positions (not V1's, decision 98) `status`
``flags`` ...           the alarms, the trips, their latches               `status`
``ratio`` ...           the N/C block, EXT. OVERRIDE, the SIC faceplates   `unit_321`
``sim_mode``            the instructor's pacing                            here
``_health``             the engine's health, stapled on at publish         here
======================  =================================================  ====================

Source: V1 ``backend/main.py`` ``step_sim``'s return (10445-11320), ``_packet_with_health``
(12039-12062), ``push_task``.
"""

from __future__ import annotations

from typing import Any, Mapping

from ureasim.data.engine import SIM_SPEED
from ureasim.engine.packet import (
    desorption,
    evaporation,
    recirculation,
    status,
    steam,
    streams,
    synthesis,
    unit_321,
)
from ureasim.engine.packet._common import Tick
from ureasim.engine.state import PlantState

__all__ = ["build_packet", "DIAGNOSTIC_BLOCKS", "PORT_BLOCKS"]

#: V1's packet keys the port does not publish: its solver audit (module docstring).
DIAGNOSTIC_BLOCKS = ("RECYCLE_TEAR_RESIDUAL", "sm_diagnostics", "CONSEQUENCE_TRANSPORT",
                     "RECYCLE_CLASSIFICATION", "SPECIES_323_324")

#: The port's packet keys V1 does not publish: the boundary sinks (handoff A-15, decided
#: 2026-10-03), the analysers that show a 322E002 tube leak (handoff B-90, decided 2026-10-09) and
#: the keyswitches' positions (decision 98, 2026-10-10).
PORT_BLOCKS = ("BOUNDARY_SINKS", "ANALYSERS", "HAND_SWITCHES")


def build_packet(plant: PlantState, results: Mapping[str, Any], tears_read: Any, *,
                 sim_mode: str, t_wall: float, health: Mapping[str, Any] | None = None) -> dict:
    """The console packet for the plant after its last tick.

    Process utility
    ---------------
    What every console on the classroom network draws, in the key order V1 sent it: the plant
    clock first (the trends' axis), then the units in V1's order, the stream registry, the
    alarms and trips, the instructor's pacing and the speed controllers' faceplates. ``health``
    is the engine's state as V1's ``_health`` reports it, so a console can tell a stalled engine
    from a live one.
    """
    t = Tick(plant, results, tears_read)
    registry = streams.streams(t)
    packet = {"t": t_wall, "t_sim": plant.clock.time_s}
    packet.update(unit_321.flat_keys(t))
    packet.update({
        "EJ_322F001": synthesis.ejector(t),
        "CO2_FEED": synthesis.co2_feed(t),
        "STRIP_322E001": synthesis.stripper(t),
        "RECIRC_323": recirculation.recirc(t),
        "LPCC_3232": recirculation.lpcc(t),
        "DESORB_328": desorption.desorb(t),
        "ABSORB_328": desorption.absorb(t),
        "EVAP_324": evaporation.evap(t),
        "HPCC_322E002": synthesis.hpcc(t),
        "STEAM_SYSTEM": steam.steam(t),
        "REACT_322R001": synthesis.reactor(t),
        "SCRUB_322E003": synthesis.scrubber(t, registry),
        "STREAMS": registry,
        "BOUNDARY_SINKS": status.boundary_sinks(t),
        "ANALYSERS": steam.analysers(t),
        "HAND_SWITCHES": status.hand_switches(t),
        "flags": status.flags(t),
        "ratio": unit_321.ratio(t),
        "ext_override": unit_321.ext_override(t),
        "sim_mode": sim_mode,
        "sim_speed": SIM_SPEED.get(sim_mode, 1.0),
        "trips": status.trips(t),
        "trip_latched": status.trip_latched(t),
        "controllers": unit_321.controllers(t),
    })
    if health is not None:
        packet["_health"] = dict(health)
    return packet
