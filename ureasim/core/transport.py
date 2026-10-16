"""Plug-flow transport of material between two pieces of equipment.

What this models
----------------
The pipe. Not the vessel at either end — the run of line between them, and the time the
fluid spends inside it.

Process utility
---------------
Without this layer a property step at one vessel's outlet is consumed by the next vessel on
the SAME tick: the parcel teleports, and mass, temperature and composition all appear
downstream with zero dead time. That contradicts every entry in the plant's deduced-lag
table, whose theta_p column is exactly this transit time, and it removes the single most
important thing a trainee has to learn about a continuous plant — that a correction takes
time to arrive, and that the time it takes DEPENDS ON THE FLOW.

Dead time is therefore derived, never tuned:

    td = rho . V_line / m_dot

so it RISES as the plant slows and falls as it speeds up. A trainee who cuts the feed must
see the downstream response get slower, not merely smaller. A fixed FIFO delay cannot do
that: at 50 % load the real transit time DOUBLES.

Two transit-time forms, and why both are kept
---------------------------------------------
V1 carries `transport_time_s` in both `backend/hydraulics.py` and `backend/consequence.py`.
They are the same equation with different guards and different caps (3600 s against 1800 s),
and different argument orders. Merging them would silently re-cap one family of call sites,
so they are ported as two named functions and each call site keeps the one V1 gave it.

A liquid-full line delays what the liquor IS, not how much of it flows
-------------------------------------------------------------------------
V1 carries the FLOW RATE in the packet with the temperature and composition, so a product line
delays its flow by the dead time: a stopped line kept delivering its design drain for the
1800 s cap — 53 t into 323F004 from a line that holds 470 kg — and a cut or a rise created or
destroyed liquor it never gave back. Liquor is incompressible: a flow change at the inlet is
the same change at the outlet at once, and only the temperature, composition and cp of what
arrives take a line residence. Decided by the process engineer on 2026-09-30 (handoff B-21,
closed): `transport_process_properties` carries a property packet on a unit flow through the
same FIFO, and the receiving stage takes the live departure flow. At a settled state the
arrived packet equals the departed one, as before, so the design point is untouched.

Source: V1 `backend/consequence.py` section 6 and `backend/hydraulics.py` section "Physical
transport delay (D-8)". Ported verbatim, but for the decided divergence above.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

from ureasim.core.numeric import clamp_preserving_nan
from ureasim.core.packet import ZERO_PACKET, StreamPacket, packet_from_mass_fraction

__all__ = [
    "ConsequenceRoute", "transport_stream_packet", "transport_process_packet",
    "PROPERTY_CARRIER_KGH", "property_packet", "transport_process_properties",
    "packet_transport_time_s", "line_residence_time_s",
    "pipe_volume_from_mm", "pipe_volume_from_m",
]


# ======================================================================================
# Line geometry
# ======================================================================================

def pipe_volume_from_mm(dn_mm: float, length_m: float) -> float:
    """Internal volume of a run of pipe [m3] from a bore in MILLIMETRES.

    Process utility: this volume, times the liquid density, is the line inventory — the
    mass that must be displaced before a change at the upstream vessel reaches the
    downstream one.

        V = pi/4 . D^2 . L

    Source: V1 `backend/consequence.py` `pipe_volume_m3`.
    """
    d = max(dn_mm, 0.0) / 1000.0
    return math.pi / 4.0 * d * d * max(length_m, 0.0)


def pipe_volume_from_m(d_inner_m: float, length_m: float) -> float:
    """Internal volume of a run of pipe [m3] from a bore in METRES.

    Same equation as `pipe_volume_from_mm`, written for the call sites that already hold an
    internal diameter in metres from a datasheet nozzle table.

    Source: V1 `backend/hydraulics.py` `line_volume_m3`.
    """
    return math.pi * d_inner_m * d_inner_m * 0.25 * length_m


# ======================================================================================
# Transit time
# ======================================================================================

def packet_transport_time_s(volume_m3: float, mass_flow_kgh: float, rho: float,
                            td_max_s: float = 1800.0) -> float:
    """Plug-flow transit time of a connecting line [s]:  ``td = rho.V / m_dot``.

    Process utility
    ---------------
    The honest way to get a dead time: it falls as the plant speeds up and rises as the
    plant slows down, which is exactly what a trainee needs to see after cutting a feed.
    Capped so a stalled line gives a long-but-finite delay rather than an unbounded buffer.

    This is the **packet** form — it is what `ConsequenceRoute` and the product-line routes
    use, and its cap is 1800 s. Note the argument order: volume, flow, density.

    Source: V1 `backend/consequence.py` `transport_time_s`.
    """
    if mass_flow_kgh <= 1e-9:
        return td_max_s
    return clamp_preserving_nan(
        max(rho, 1e-9) * max(volume_m3, 0.0) * 3600.0 / mass_flow_kgh, 0.0, td_max_s)


def line_residence_time_s(v_line_m3: float, rho_kgm3: float, mdot_kgh: float,
                          t_max_s: float = 3600.0) -> float:
    """Line residence time [s]:  ``td = rho.V_line / m_dot``.

    Process utility
    ---------------
    The **scalar-signal** form, used for feed-line dead times such as the battery-limit CO2
    run: the CO2 the synthesis loop receives now left the BL meter some minutes ago. It
    caps at 3600 s and takes its arguments as volume, density, flow — note that this is a
    DIFFERENT order from `packet_transport_time_s`, which is V1's own convention and is
    preserved so that a ported call site reads the same as its original.

    Passing a line inventory in kg with ``rho_kgm3 = 1.0`` expresses a back-solved holdup
    through the same equation, which is how V1's feed lines are specified.

    Source: V1 `backend/hydraulics.py` `transport_time_s`.
    """
    if mdot_kgh <= 1e-9 or v_line_m3 <= 0.0 or rho_kgm3 <= 0.0:
        return t_max_s
    return min(rho_kgm3 * v_line_m3 / mdot_kgh * 3600.0, t_max_s)


# ======================================================================================
# A named connection between two pieces of equipment
# ======================================================================================

@dataclass(frozen=True)
class ConsequenceRoute:
    """A physical connection whose line inventory sets its dead time.

    Process utility
    ---------------
    The route is specified by its DESIGN condition — the design carrier flow and the design
    transit time — because that pair is what the PFD and the layout give. The inventory
    follows from them, and the live dead time then follows from the inventory and the live
    flow. So a route is anchored at design (Rule 1 of the As-Built reference) and responds
    correctly off design, without a single fitted lag anywhere.
    """

    source: str
    destination: str
    design_carrier_kgh: float
    design_dead_time_s: float
    max_dead_time_s: float = 1800.0

    @property
    def line_inventory_kg(self) -> float:
        """Mass the line holds [kg] — ``m_dot_design . td_design``.

        This is the quantity that is physically constant. Everything else about the route's
        timing is derived from it.
        """
        return max(self.design_carrier_kgh, 0.0) * max(self.design_dead_time_s, 0.0) / 3600.0

    def dead_time_s(self, live_carrier_kgh: float) -> float:
        """Live dead time [s] at the current carrier flow.

        A stopped line returns the cap rather than infinity: nothing is arriving, so the
        exact value is immaterial, but an unbounded delay would grow the FIFO without limit.
        """
        if live_carrier_kgh <= 1.0e-9:
            return max(self.max_dead_time_s, 0.0)
        value = self.line_inventory_kg * 3600.0 / live_carrier_kgh
        return clamp_preserving_nan(value, 0.0, max(self.max_dead_time_s, 0.0))


# ======================================================================================
# Moving a packet down a route
# ======================================================================================
#
# Both functions below are the same timestamped, zero-order-held FIFO. They differ in ONE
# thing — what the line contains before the first packet arrives — and that difference is
# not cosmetic:
#
#   * `transport_stream_packet` starts EMPTY, because it transports a CONSEQUENCE. A seal
#     leak that has not happened yet must not arrive at the downstream vessel at t = 0.
#   * `transport_process_packet` starts FULL, because it transports a PROCESS stream. The
#     product line between 323C003 and 323F004 is full of 135 C liquor at simulation start,
#     and a line that started empty would starve the whole recirculation train for one dead
#     time on every boot — which would break the design pin.
#
# The FIFO is timestamped rather than counted because the integrator advances in sub-steps
# whose size is NOT fixed: a remainder sub-step is often a numerical crumb of ~1e-8 s, and a
# buffer length derived as n = td/dt would explode to ~1e10 entries on one.
# ======================================================================================

def _advance_fifo(state: dict, target: StreamPacket, route: ConsequenceRoute,
                  live_carrier_kgh: float, dt: float) -> StreamPacket:
    """One tick of the shared zero-order-held FIFO. Returns what has ARRIVED.

    Identical consecutive packets are coalesced, so a settled run keeps exactly one history
    sample however long it runs — the buffer's size tracks how much the plant is MOVING,
    not how long it has been running.
    """
    state["time_s"] += dt
    now = state["time_s"]
    dead_time = route.dead_time_s(live_carrier_kgh)
    state["dead_time_s"] = dead_time
    buffer = state["buffer"]
    if not buffer or buffer[-1][1] != target:
        buffer.append((now, target))
    cutoff = now - dead_time
    # Drop only SUPERSEDED samples: keep the newest whose entry time is already older than
    # the cutoff, so the zero-order hold always has a value to emit.
    while len(buffer) >= 2 and buffer[1][0] <= cutoff + 1.0e-9:
        buffer.popleft()
    if buffer and buffer[0][0] <= cutoff + 1.0e-9:
        state["output"] = buffer[0][1]
    return state["output"]


def transport_stream_packet(store: dict, key: str, target: StreamPacket,
                            route: ConsequenceRoute, live_carrier_kgh: float,
                            dt: float) -> StreamPacket:
    """Delay a CONSEQUENCE packet through one line. The line starts EMPTY.

    Process utility: a consequence — carry-over, a leak, an off-spec slug — is a departure
    from the background, and the background is already accounted for elsewhere. Emitting
    the design stream here as well would double-count it.

    Source: V1 `backend/consequence.py` `transport_stream_packet`.
    """
    if dt <= 0.0:
        return target
    state = store.get(key)
    if state is None:
        state = {"time_s": 0.0, "buffer": deque(), "output": ZERO_PACKET,
                 "dead_time_s": route.dead_time_s(live_carrier_kgh)}
        store[key] = state
    return _advance_fifo(state, target, route, live_carrier_kgh, dt)


def transport_process_packet(store: dict, key: str, target: StreamPacket,
                             route: ConsequenceRoute, live_carrier_kgh: float,
                             dt: float) -> StreamPacket:
    """Delay a PROCESS packet through one line. The line starts FULL of the first packet.

    Process utility: seeding both history and output from the first live packet preserves
    the boot steady state exactly — at a settled state the arrived packet EQUALS the
    departed packet, so the pinned design point is bit-exact and the dead time shows only
    when something actually changes.

    Source: V1 `backend/consequence.py` `transport_process_packet`.
    """
    if dt <= 0.0:
        return target
    state = store.get(key)
    if state is None:
        state = {
            "time_s": 0.0,
            "buffer": deque([(0.0, target)]),
            "output": target,
            "dead_time_s": route.dead_time_s(live_carrier_kgh),
        }
        store[key] = state
    return _advance_fifo(state, target, route, live_carrier_kgh, dt)


# ======================================================================================
# A liquid-full line: the flow at once, the properties a line residence later (B-21)
# ======================================================================================

#: The flow a property packet is carried on [kg/h]. The unit makes the packet a pure function
#: of the liquor's temperature, composition and cp, so a flow change neither enters the FIFO
#: nor stops a settled line comparing equal.
PROPERTY_CARRIER_KGH = 1.0


def property_packet(temperature_c: float, mass_fraction: dict, cp_kj_kgk: float) -> StreamPacket:
    """What a liquor IS, as a packet on the unit carrier flow.

    Process utility: the part of a process stream a liquid-full line delays. Its flow is
    delivered at once; this is what arrives a line residence later.
    """
    return packet_from_mass_fraction(PROPERTY_CARRIER_KGH, temperature_c, mass_fraction,
                                     cp_kj_kgk)


def transport_process_properties(store: dict, key: str, target: StreamPacket,
                                 route: ConsequenceRoute, live_carrier_kgh: float,
                                 dt: float) -> StreamPacket:
    """Delay a PROCESS stream's properties through a liquid-full line. The line starts FULL.

    Process utility
    ---------------
    Conserves mass exactly on every product line: what enters leaves on the same tick, and the
    liquor that leaves is the liquor that entered one line residence ago — its temperature,
    composition and cp. The dead time is the line's inventory over the LIVE flow, as before, so
    a slower plant still sees a slower response; a stopped line delivers nothing and holds its
    liquor. ``target`` is a `property_packet`; the caller delivers its own live flow.

    Decided divergence (handoff B-21, 2026-09-30): V1 delays the flow with the properties.
    """
    return transport_process_packet(store, key, target, route, live_carrier_kgh, dt)
