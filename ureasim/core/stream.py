"""The published process stream — one uniform record per connection in the flowsheet.

What this is
------------
The object behind the stream inspector: click a line on the HMI and this is what opens.
Name, source, destination, phase, temperature, pressure, total flow on three bases, molar
weight, density, volumetric flow, enthalpy with its quality tier, and the full component
vector as both mol % and mass %.

Process utility
---------------
It is the simulator's answer to "what is actually in this pipe right now", and it is how a
trainee checks their own reasoning against the plant. The single most important property of
the record is that **both composition bases come from the same per-component kmol/h
vector**, so mol % and mass % cannot drift apart — a stream cannot be 38.6 % nitrogen by
mole on one line of the display and 38.6 % by mass on the next.

This layer is READ-ONLY. It consumes converged state and feeds nothing back, so it cannot
perturb the design anchors the mass solvers are pinned to. Anything that changes the plant
belongs upstream of here.

Rounding
--------
Component vectors stay at calculation precision; the totals and percentages are rounded
because they are display values. The rounding is V1's, digit for digit, because the
equivalence tests compare the published records field by field.

Source: V1 `backend/main.py` `make_stream`, `make_stream_mass_pct`, `make_stream_mole_pct`,
`_vent_mole_pct`. Ported verbatim.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ureasim.thermo.enthalpy import EnthalpyBasis, h0_stream, unsupported_species

__all__ = ["MW_COMP", "StreamRecord", "make_stream", "make_stream_mass_pct",
           "make_stream_mole_pct", "vent_mole_pct", "mass_fractions_from_kmolh",
           "atom_ratio"]


# ======================================================================================
# The molar-mass table the published records are built on
# ======================================================================================
#
# ATOM-CONSISTENT, and that is the whole point of having a separate table here.
#
#     Urea   MW = C + 2N + 4H + O   -> urea couple   (CO2 + 2 NH3 -> Urea + H2O)
#     Biuret MW = 2.Urea - NH3      -> biuret couple (2 Urea -> Biuret + NH3)
#
# Both couples satisfy ``sum(nu_i . MW_i) = 0`` EXACTLY against the listed CO2, NH3 and H2O
# molar masses, so a reacting node closes its mass balance to machine zero rather than to a
# few grams per hour that accumulate over a shift. The difference from the thermodynamic
# table in `thermo.enthalpy.MOLAR_MASS` is in the last digits of Urea and Biuret only, and
# it is deliberate: that table is fitted to calorimetric data, this one is fitted to the
# stoichiometry. `make_stream` re-specifies the mass-specific enthalpy against THIS table's
# mass total so the two conventions never mix inside one record.
#
# Source: V1 `backend/main.py` MW_COMP.
MW_COMP = {"CO2": 44.0098, "CH4": 16.043, "H2": 2.0158, "H2O": 18.0152,
           "N2": 28.0134, "NH3": 17.0304, "O2": 31.9988,
           "Urea": 60.0554, "Biuret": 103.0804}

#: Guard, run at import: every published species must have an H0 enthalpy datum, or a
#: stream could be published with a silently missing enthalpy contribution.
_H0_GAPS = unsupported_species(MW_COMP)
assert not _H0_GAPS, (
    f"no H0 enthalpy datum for {sorted(_H0_GAPS)}; add it before publishing streams")


# ======================================================================================
# The record
# ======================================================================================

@dataclass(frozen=True)
class StreamRecord:
    """One published process stream.

    Frozen because a published record is a statement about a converged tick. A consumer
    that wants a different number must ask the engine for it, not edit the record.
    """

    name: str
    src: str
    dst: str
    phase: str
    T_C: float
    P_bara: float
    mass_kgh: float
    mass_th: float
    mol_kmolh: float
    MW: float
    rho: float | None
    vol_m3h: float | None
    enthalpy_kJkg: float | None
    enthalpy_flow_kW: float
    enthalpy_basis: str
    component_kmolh: dict = field(default_factory=dict)
    component_kgh: dict = field(default_factory=dict)
    mol_pct: dict = field(default_factory=dict)
    mass_pct: dict = field(default_factory=dict)

    def as_packet(self) -> dict:
        """The record as the dict the HMI snapshot carries.

        The key names and their order are V1's WebSocket payload exactly, so the stream
        inspector's bindings port across without translation.
        """
        return {
            "name": self.name, "src": self.src, "dst": self.dst, "phase": self.phase,
            "T_C": self.T_C, "P_bara": self.P_bara,
            "mass_kgh": self.mass_kgh, "mass_th": self.mass_th,
            "mol_kmolh": self.mol_kmolh,
            "MW": self.MW,
            "rho": self.rho, "vol_m3h": self.vol_m3h,
            "enthalpy_kJkg": self.enthalpy_kJkg,
            "enthalpy_flow_kW": self.enthalpy_flow_kW,
            "enthalpy_basis": self.enthalpy_basis,
            "component_kmolh": dict(self.component_kmolh),
            "component_kgh": dict(self.component_kgh),
            "mol_pct": dict(self.mol_pct),
            "mass_pct": dict(self.mass_pct),
        }


# ======================================================================================
# Constructors
# ======================================================================================

def make_stream(comp_kmolh: dict, T: float, P: float, name: str, src: str, dst: str,
                phase: str, rho: float | None = None,
                h_kjkg: float | None = None) -> StreamRecord:
    """Build a published stream from a per-component kmol/h vector.

    Process utility
    ---------------
    Derives BOTH mol % and mass % from that one vector, so the two bases can never drift.
    An unknown density stays ``None`` and the volumetric flow with it — no fabricated
    property ever enters a published record.

    Enthalpy
    --------
    Published on the **H0 tier**: formation plus sensible plus phase reference, on the
    elements-at-298.15 K datum, ideal solution. Because every constituent is referenced to
    its elements, the value is reaction-consistent and may be summed across a reacting
    node — which is exactly what a synthesis-loop energy balance needs.

    The excess (mixing) term H^E is NOT included, so this is not design-grade inside a
    strongly non-ideal liquid. `enthalpy_basis` declares that per stream rather than leaving
    it implied, which is the difference between a caveat and a trap.

    An explicit ``h_kjkg`` overrides the calculation and is published as plant-reconciled
    (H2) — the tier for a number that came from the licensor's own heat balance.
    """
    n = {k: comp_kmolh.get(k, 0.0) for k in MW_COMP}
    m = {k: n[k] * MW_COMP[k] for k in MW_COMP}
    n_tot = sum(n.values())
    m_tot = sum(m.values())
    if h_kjkg is not None:
        h_spec = h_kjkg
        H_kW = m_tot * h_kjkg / 3600.0
        basis = EnthalpyBasis.H2.value
    else:
        h0 = h0_stream(n, T, phase)
        H_kW = h0["enthalpy_flow_kW"]
        # Re-specify against THIS record's own mass total: MW_COMP is atom-consistent for
        # the reactor couples and differs in the last digits from the H0 module's molar
        # masses, so dividing the H0 module's enthalpy flow by the H0 module's mass total
        # would publish a kJ/kg that does not multiply back to the published kg/h.
        h_spec = H_kW * 3600.0 / m_tot if m_tot > 0.0 else None
        basis = h0["enthalpy_basis"]
    return StreamRecord(
        name=name, src=src, dst=dst, phase=phase,
        T_C=round(T, 1), P_bara=round(P, 1),
        mass_kgh=round(m_tot, 1), mass_th=round(m_tot / 1000.0, 3),
        mol_kmolh=round(n_tot, 2),
        MW=round(m_tot / n_tot, 3) if n_tot else 0.0,
        rho=(round(rho, 1) if rho else None),
        vol_m3h=(round(m_tot / rho, 2) if rho else None),
        enthalpy_kJkg=(round(h_spec, 3) if h_spec is not None else None),
        enthalpy_flow_kW=round(H_kW, 3),
        enthalpy_basis=basis,
        component_kmolh=dict(n),
        component_kgh=dict(m),
        mol_pct={k: round(n[k] / n_tot * 100.0, 3) if n_tot else 0.0 for k in MW_COMP},
        mass_pct={k: round(m[k] / m_tot * 100.0, 3) if m_tot else 0.0 for k in MW_COMP},
    )


def make_stream_mass_pct(mass_kgh: float, mass_pct: dict, T: float, P: float, name: str,
                         src: str, dst: str, phase: str, rho: float | None = None,
                         h_kjkg: float | None = None) -> StreamRecord:
    """Build a stream from an independently rounded PFD **mass-per-cent** row.

    Process utility
    ---------------
    Every liquid row in the PFD stream table is given as mass %, and each component is
    rounded on its own, so the row does not sum to 100. Normalising against the row's own
    total and scaling to the LIVE mass flow is what keeps the published record closed while
    still reproducing the licensor's composition.
    """
    total_pct = sum(max(mass_pct.get(k, 0.0), 0.0) for k in MW_COMP)
    if mass_kgh <= 0.0 or total_pct <= 0.0:
        return make_stream({}, T, P, name, src, dst, phase, rho=rho, h_kjkg=h_kjkg)
    comp_kmolh = {
        k: mass_kgh * max(mass_pct.get(k, 0.0), 0.0) / total_pct / MW_COMP[k]
        for k in MW_COMP
    }
    return make_stream(comp_kmolh, T, P, name, src, dst, phase, rho=rho, h_kjkg=h_kjkg)


def make_stream_mole_pct(mass_kgh: float, mole_pct: dict, T: float, P: float, name: str,
                         src: str, dst: str, phase: str, rho: float | None = None,
                         h_kjkg: float | None = None) -> StreamRecord:
    """Build a stream from a PFD **mole-per-cent** row, scaled to the live mass flow.

    Process utility
    ---------------
    Every vapour and gas row in the PFD is tabulated on a MOLE basis. Reading one as mass %
    is not a rounding-level error: stream 706 then publishes 38.6 % of its MASS as nitrogen
    when 38.6 % of its MOLES are, and an average molar weight of 22.38 against the PFD's
    own 24.13. The composition is converted here, once, at the boundary.

        n_i propto mole_pct_i ,   m_i = mass_kgh . n_i . MW_i / sum_j(n_j . MW_j)
    """
    n_rel = {k: max(mole_pct.get(k, 0.0), 0.0) for k in MW_COMP}
    m_rel = sum(n_rel[k] * MW_COMP[k] for k in MW_COMP)
    if mass_kgh <= 0.0 or m_rel <= 0.0:
        return make_stream({}, T, P, name, src, dst, phase, rho=rho, h_kjkg=h_kjkg)
    return make_stream({k: mass_kgh * n_rel[k] / m_rel for k in MW_COMP},
                       T, P, name, src, dst, phase, rho=rho, h_kjkg=h_kjkg)


def vent_mole_pct(vent_kmolh: dict) -> dict:
    """A condenser vent's LIVE composition, as mole per cent.

    Process utility
    ---------------
    A vacuum-train vent is the one place where the PFD row is the WRONG composition to
    publish: its non-condensable fraction is whatever the condenser did not condense on
    this tick, which is the quantity a trainee watches when the vacuum starts to slip. So
    the published record takes the live vent vector, not the design row.
    """
    tot = sum(vent_kmolh.values())
    return {k: (x / tot * 100.0 if tot > 0.0 else 0.0) for k, x in vent_kmolh.items()}


def mass_fractions_from_kmolh(kmolh: dict) -> dict:
    """A molar flow vector [kmol/h] as mass fractions [-], for the property service.

    Process utility
    ---------------
    The flowsheet counts moles, because that is what reactions and splits conserve; the
    thermodynamic service is indexed on mass fractions. This is the one conversion between
    them, kept in the module that owns `MW_COMP` so a second molar mass can never enter the
    plant through a private copy of this loop.

    An empty or non-positive vector returns PURE WATER rather than raising or returning
    zeros. That is the deliberate choice V1 made: a composition of all zeros is not a
    composition, and a property call on it is meaningless, whereas water is the one component
    always present in this plant and is the safest thing to evaluate a property at during a
    black start. The caller sees a finite, sane property instead of an exception on a vessel
    that is merely empty.
    """
    m = {k: max(kmolh.get(k, 0.0), 0.0) * MW_COMP[k] for k in MW_COMP}
    total = sum(m.values())
    if total <= 0.0:
        return {k: (1.0 if k == "H2O" else 0.0) for k in MW_COMP}
    return {k: v / total for k, v in m.items()}


def atom_ratio(comp_kmolh: dict, numerator_atoms: dict, denominator_atoms: dict,
               span_max: float) -> float:
    """Ratio of two atom counts in a stream, as an on-line analyser reads it [-].

    Process utility
    ---------------
    This is what an N/C or an H/C analyser measures. It counts atoms rather than molecules,
    so it is invariant to which compound the nitrogen or the carbon currently sits in —
    ammonia, carbamate or urea all read the same nitrogen — which is exactly why the
    measurement is useful for controlling a reacting loop: it moves when the FEED ratio moves
    and not when the conversion does.

    Why the span cap is part of the measurement
    --------------------------------------------
    The denominator can go to zero while the numerator does not. Cut the CO2 feed to the
    synthesis loop and the carbon inventory drains away against an ammonia inventory that
    does not, so the true ratio runs away without bound — V1 measured 6.1e9 on a tripped
    loop. A real analyser has a span and pegs at the top of it. Publishing 1e9 instead
    teaches a trainee nothing and poisons every correlation keyed on the reading, so the
    saturation is modelled rather than left out.

    A denominator of exactly zero returns 0.0, not the span: no carbon at all is the absence
    of a measurement rather than an over-range, and that is V1's behaviour.

    The atom maps are arguments because the species-to-atom count is plant data and this
    layer holds none. Their iteration order fixes the order of the two sums, so the caller
    also owns the last bit of the result.

    Source: V1 `backend/main.py` `react_nc_ratio`.
    """
    n = sum(comp_kmolh.get(k, 0.0) * a for k, a in numerator_atoms.items())
    c = sum(comp_kmolh.get(k, 0.0) * a for k, a in denominator_atoms.items())
    return min(n / c, span_max) if c else 0.0
