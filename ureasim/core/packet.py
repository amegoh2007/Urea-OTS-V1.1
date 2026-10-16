"""A stream packet — mass, temperature, heat capacity and composition as ONE object.

What this models
----------------
One sample of a flowing stream, taken at an equipment boundary and treated as indivisible.
It is the unit of material that moves down a line in `core.transport`, and it is the type a
unit operation hands to the unit downstream of it.

Process utility
---------------
The defect this type exists to prevent is *property desynchronisation*. When a boundary is
modelled as three separate signals — a flow, a temperature and a composition — each one can
be lagged, filtered or clamped on its own, and then the receiving vessel is fed 130 t/h of
material at last tick's temperature carrying the tick-before-last's urea fraction. The
inventory still balances, so nothing looks wrong; only the energy balance quietly stops
closing, and a trainee watching the bottom temperature sees a stage respond before the
material that should have caused the response has arrived.

Holding them on one frozen object makes that class of error unrepresentable: the component
vector *is* the composition, the total *is* its sum, and the sensible enthalpy *is* derived
from the same two. Nothing can arrive early.

Source: V1 `backend/consequence.py` section 6 (`StreamPacket`, `make_stream_packet`,
`mix_stream_packets`) and `backend/main.py` `_cq_packet` / `_w_norm`. Ported verbatim.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ureasim.thermo.domains import MW
from ureasim.thermo.urea_liquor import SOLUTION_SPECIES

__all__ = [
    "SOLUTION_SPECIES", "StreamPacket", "ZERO_PACKET",
    "make_stream_packet", "mix_stream_packets", "packet_from_mass_fraction",
    "normalise_solution_mass_fraction",
]

#: The six species a urea-solution stream is tracked in through the recirculation,
#: desorption and evaporation trains.
#:
#: Source: V1 `backend/main.py` MW_SOL / SOL_SPECIES. The tuple is defined once, in
#: `thermo.urea_liquor`, beside the liquor physics that sums over it. Their molar masses are not
#: repeated here — for these six, V1's MW_SOL is value-identical to `thermo.domains.MW`, which
#: is asserted by `tests/equivalence/test_core_equivalence.py` so the two cannot silently
#: diverge. The permanent gases (N2, O2, CH4, H2) are absent by design: they do not stay in
#: a solution stream at these temperatures.


# ======================================================================================
# The packet
# ======================================================================================

@dataclass(frozen=True)
class StreamPacket:
    """One conservative stream-rate sample, transported as an indivisible packet.

    Component rates are held as a sorted tuple rather than a dict so that a frozen packet
    cannot retain a caller-owned mutable mapping — a packet sitting in a transport FIFO
    must not change composition because the producer reused its dictionary on the next
    tick. Total flow, composition and sensible enthalpy are therefore three *views* of one
    component vector, not three independently lagged signals.
    """

    mass_kgh: float
    temperature_c: float
    cp_kj_kgk: float
    _component_items: tuple[tuple[str, float], ...]

    @property
    def component_kgh(self) -> dict[str, float]:
        """Per-species mass flow [kg/h]. A fresh dict each call; the packet keeps the tuple."""
        return dict(self._component_items)

    @property
    def mass_fraction(self) -> dict[str, float]:
        """Per-species mass fraction [-]. Sums to 1 by construction on a non-empty packet."""
        if self.mass_kgh <= 0.0:
            return {name: 0.0 for name, _ in self._component_items}
        return {name: flow / self.mass_kgh for name, flow in self._component_items}

    @property
    def sensible_kw(self) -> float:
        """Sensible enthalpy flow [kW] on a 0 deg C datum: ``m . cp . T``.

        Process utility: this is the term a receiving vessel adds to its energy balance, so
        it must be computed from the SAME mass and temperature the material balance used.
        Deriving it here rather than passing it alongside is what guarantees that.
        """
        return self.mass_kgh * self.cp_kj_kgk * self.temperature_c / 3600.0


#: The empty packet — no mass, no composition, and therefore no temperature to speak of.
#: Returned rather than raised wherever a line legitimately runs dry.
ZERO_PACKET = StreamPacket(0.0, 0.0, 0.0, ())


def make_stream_packet(mass_kgh: float, component_kgh: dict[str, float],
                       temperature_c: float, cp_kj_kgk: float) -> StreamPacket:
    """Build a closed stream packet, REJECTING an independently inconsistent total.

    Process utility
    ---------------
    The total and the component vector are two statements of the same quantity, and the
    check below is the only thing that keeps them one quantity. A caller that computes its
    total from a different expression than its components — which is how a mass balance
    stops closing — is refused here rather than three units downstream, where the
    discrepancy would present as an unexplained inventory drift.

    The tolerance is relative, so it survives the 1.3e5 kg/h main product line and the
    1 kg/h purge with the same statement.
    """
    values: dict[str, float] = {}
    for name, raw in component_kgh.items():
        value = float(raw)
        if not math.isfinite(value) or value < 0.0:
            raise ValueError(f"component mass flow must be finite and nonnegative: {name}")
        if value > 0.0:
            values[str(name)] = value

    total = sum(values.values())
    stated = float(mass_kgh)
    tolerance = max(1.0e-9, 1.0e-9 * max(abs(total), abs(stated), 1.0))
    if not math.isfinite(stated) or stated < 0.0 or abs(stated - total) > tolerance:
        raise ValueError(
            f"component mass flow sum {total:g} kg/h does not match total {stated:g} kg/h"
        )
    if total <= tolerance:
        return ZERO_PACKET
    if not math.isfinite(temperature_c):
        raise ValueError("temperature must be finite")
    if not math.isfinite(cp_kj_kgk) or cp_kj_kgk <= 0.0:
        raise ValueError("heat capacity must be finite and positive")
    return StreamPacket(
        total,
        float(temperature_c),
        float(cp_kj_kgk),
        tuple(sorted(values.items())),
    )


def mix_stream_packets(*packets: StreamPacket) -> StreamPacket:
    """Combine packets by mass AND sensible enthalpy without desynchronising them.

    Process utility
    ---------------
    This is a tee or a vessel inlet with several nozzles: 328D003 taking four condensates,
    or 324F002 taking the ejector discharge on top of the condenser gas. The mixed
    temperature is the one that makes the combined sensible enthalpy equal the sum of the
    parts, which is an energy balance rather than a flow-weighted average of temperature —
    they differ whenever the streams have different heat capacities, which here they do.

        cp_mix = sum(m_i . cp_i) / sum(m_i)
        T_mix  = sum(m_i . cp_i . T_i) / sum(m_i . cp_i)
    """
    components: dict[str, float] = {}
    heat_capacity_rate = 0.0
    sensible_kw = 0.0
    for packet in packets:
        if packet.mass_kgh <= 0.0:
            continue
        for name, flow in packet._component_items:
            components[name] = components.get(name, 0.0) + flow
        heat_capacity_rate += packet.mass_kgh * packet.cp_kj_kgk
        sensible_kw += packet.sensible_kw
    total = sum(components.values())
    if total <= 0.0:
        return ZERO_PACKET
    cp_mix = heat_capacity_rate / total
    temperature_c = sensible_kw * 3600.0 / heat_capacity_rate
    return make_stream_packet(total, components, temperature_c, cp_mix)


# ======================================================================================
# Composition helpers
# ======================================================================================

def normalise_solution_mass_fraction(w: dict, fallback: dict | None = None) -> dict:
    """PFD mass-% row -> mass FRACTIONS over `SOLUTION_SPECIES`, summing to exactly 1.

    Process utility
    ---------------
    This is the summation equation of the stage balance (Sum w_i = 1), applied once at the
    boundary instead of being assumed at every term inside it. A PFD row is independently
    rounded per component and does not sum to 100, so normalising is not cosmetic: skipping
    it leaves the stage's own species balance with a permanent closure residual.

    ``fallback`` is for the TRANSPORT path only, and it exists for a specific failure. An
    empty packet carries no composition, so its `mass_fraction` sums to zero and the
    division below raises — an engine-killing ZeroDivisionError reachable from any upset
    that takes a transported line to exactly zero flow (a total 322E003 cooling-water loss
    does it at the 323C003 bottom drain). Nothing physical is papered over: when no mass
    arrives, the receiving stage's inflow term is zero, so the vector it multiplies is
    arbitrary, and the departure composition is the honest placeholder.

    Every OTHER caller passes a PFD row, where a zero total IS a data error and must still
    raise.

    Source: V1 `backend/main.py` `_w_norm`. Ported verbatim.
    """
    tot = sum(w.get(k, 0.0) for k in SOLUTION_SPECIES)
    if tot <= 0.0 and fallback is not None:
        return normalise_solution_mass_fraction(fallback)
    return {k: w.get(k, 0.0) / tot for k in SOLUTION_SPECIES}


def packet_from_mass_fraction(mass_kgh: float, temperature_c: float,
                              mass_fraction: dict, cp_kj_kgk: float) -> StreamPacket:
    """Mass fractions + total flow -> one closed `StreamPacket`.

    Process utility
    ---------------
    The form every stage boundary uses: a stage knows its own inventory composition as
    fractions and its outflow as a total, and this turns the pair into the closed object
    the line downstream transports.

    The component vector is rebuilt FROM the normalised fractions, so the packet's total is
    the sum of its components by construction — `make_stream_packet` would otherwise reject
    a total that disagrees with the fractions by floating-point epsilon.

    Three degenerate cases return the empty packet rather than raising, because this is a
    boundary-diagnostic path and must not be the thing that takes the plant down:

      * no flow, or a non-finite flow — the line is simply dry;
      * no composition — nothing to normalise against;
      * a non-finite temperature. Deep in a collapse (a total 322E003 cooling-water loss
        runs the reactor N/C off scale and takes the 323 train with it) a stage temperature
        can go non-finite. That is a real defect worth seeing, but `make_stream_packet`
        RAISES on it, and a raise here kills the engine tick.

    A non-positive heat capacity is floored instead: a packet must carry a positive heat
    capacity for its sensible term to mean anything, and 0.1 kJ/(kg.K) is small enough to
    be visibly wrong in telemetry rather than plausibly wrong.

    Source: V1 `backend/main.py` `_cq_packet`. Ported verbatim.
    """
    m = float(mass_kgh)
    if not math.isfinite(m) or m <= 0.0:
        return ZERO_PACKET
    tot_w = sum(v for v in mass_fraction.values() if v > 0.0)
    if tot_w <= 0.0:
        return ZERO_PACKET
    comp = {k: m * v / tot_w for k, v in mass_fraction.items() if v > 0.0}
    cp = float(cp_kj_kgk)
    if not math.isfinite(cp) or cp <= 0.0:
        cp = 0.1
    if not math.isfinite(float(temperature_c)):
        return ZERO_PACKET
    return make_stream_packet(sum(comp.values()), comp, temperature_c, cp)


#: Guard: the six solution species must all exist in the thermodynamic molar-mass table, or
#: a packet could carry a species no property call can evaluate.
_MISSING = [sp for sp in SOLUTION_SPECIES if sp not in MW]
assert not _MISSING, f"solution species missing a molar mass: {_MISSING}"
