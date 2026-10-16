"""H0 absolute stream enthalpy on a single elements-at-298.15 K datum.

What this gives the plant model
-------------------------------
An enthalpy you can add up across a reacting node. Every energy balance in the simulator —
reactor, stripper, condenser, evaporator, desorber — needs stream enthalpies that do not
create or destroy energy when a reaction happens inside the node. That requires a
**formation** datum, and this module is it.

It is also what makes an isenthalpic flash (`flash_ph`, the HV-322604 letdown) possible at
all: without an absolute enthalpy there is nothing to hold constant.

The decomposition, and why the tier flag exists
-----------------------------------------------
    H_stream = sum_i n_i h_i(T)            +  H^E(T, x)
               |__formation + sensible__|     |__mixing non-ideality__|
                  available from published       needs the tier's activity model
                  data right now

Rather than publish nothing until the excess term lands everywhere, every stream carries a
**declared basis flag**:

    H0    formation + sensible + phase reference, IDEAL solution (H^E = 0)   <- this module
    H1    H0 + H^E from the tier's activity model
    H2    H1 reconciled against the licensor / plant heat balance

H0 is usable for heat balances and duty/trend estimates. It is **not** design-grade inside
a strongly non-ideal liquid — that is H1 — and the flag makes that honest per stream
instead of being a footnote someone forgets.

Why a formation datum and not sensible heat alone
--------------------------------------------------
Because every h_i is referenced to its **elements** at 298.15 K / 1 bar (that is what a
formation enthalpy *is*), a reaction's enthalpy is automatically the difference of its
members' formation enthalpies. H0 therefore does not create or destroy energy across a
reacting node. A sensible-only enthalpy does, which is why sensible-only was refused.

Provenance
----------
    H2O(l), NH3(aq), CO2(aq)   reuse the SAME formation enthalpy and Helgeson Cp(T) already
                               validated in `thermo.properties` — imported, not
                               re-transcribed, so the two modules cannot diverge.
    ideal-gas dHf              CODATA Key Values / NIST-JANAF at 298.15 K.
    urea, biuret (s and l)     Tischer, Boernhorst, Amsler, Schoch, Deutschmann,
                               Phys. Chem. Chem. Phys. 21 (2019) 16785 (open access, CC BY-NC).
    ammonium carbamate,        Voskov & Voronin, J. Chem. Eng. Data 61 (2016) 4110, Table 1:
    and Berman-Brown Cp        dHf(s) -645.05, dHf(l) -624.32 kJ/mol; Cp = a + e T^-0.5.

Carbamate's **explicit** formation enthalpy is what makes the loop enthalpy
reaction-consistent *through the carbamate node*, not merely across the net
2 NH3 + CO2 -> urea + H2O.

Cross-check against this plant's own licensor manual
-----------------------------------------------------
Uhde UD-VT-G00-DC-0003 (`References/Sources/02 FUNDAMENTALS.pdf`). The elements datum
reproduces the manual's reaction enthalpies:

    2 NH3(g) + CO2(g) -> carbamate(s)     this module ~ -159.6    manual ~ -159 kJ/mol
    carbamate(l) -> urea(l) + H2O(l)      this module ~  +18.8    manual   +15.5 kJ/mol
    urea fusion at 25 C                   this module    13.9     plant remelt 15.1 kJ/mol

All inside the H0 declared band.

Declared approximation
----------------------
Gas-phase sensible heat uses a constant Cp near mid-window. Over 25-200 C that is a
few-percent approximation on the SENSIBLE part only; the formation term, which dominates a
reactive balance by one to two orders of magnitude, is exact. That approximation is a
declared property of the H0 tier, not a hidden one.

Ported from V1 `backend/gap_g6_h0_enthalpy.py`. Numerically identical.
"""

from __future__ import annotations

import math
from enum import Enum
from functools import lru_cache

from ureasim.thermo import properties as props

#: Reference temperature of the datum [K].
T0 = 298.15

#: Universal gas constant [J/(mol.K)].
R = 8.314462618


class EnthalpyBasis(str, Enum):
    """Declared quality tier for a published stream enthalpy.

    Travels with every enthalpy the simulator publishes, so a consumer can tell a
    design-grade number from an ideal-solution estimate without reading the source.
    """

    H0 = "H0_formation_sensible_ideal"     # this module; excludes mixing non-ideality
    H1 = "H1_plus_excess"                  # H0 + H^E from the tier's activity model
    H2 = "H2_plant_reconciled"             # H1 reconciled to the licensor/plant heat balance


#: Molar masses [g/mol] for the condensed-phase species set plus the volatile and inert
#: gases that appear in the vapour streams.
MOLAR_MASS = {
    "Urea": 60.056, "Biuret": 103.081, "Carbamate": 78.0714, "NH3": 17.0304, "CO2": 44.0098,
    "H2O": 18.0152, "HCHO": 32.031, "N2": 28.0134, "O2": 31.9988,
    "H2": 2.0158, "CH4": 16.043, "Ar": 39.948,
}


# ======================================================================================
# Heat-capacity shapes
# ======================================================================================

def _cp_const(value: float):
    """Constant heat capacity [J/(mol.K)]."""
    return lambda T: value


def _cp_berman(a: float, e: float):
    """Berman-Brown truncated heat capacity ``Cp(T) = a + e T^-0.5`` [J/(mol.K)].

    Voskov & Voronin 2016, Table 1. This is the shape the condensed urea, biuret and
    carbamate phases use.

    The returned callable carries its own **exact** antiderivative on ``.integral``, so
    `h_species` never has to quadrature this form:

        integral (a + e T^-0.5) dT = a T + 2 e sqrt(T)

    Putting the closed form on the function rather than special-casing it in the caller
    keeps the enthalpy of the three condensed species free of quadrature error — and those
    are the species that dominate a urea melt's enthalpy.
    """
    cp = lambda T: a + e * T ** (-0.5)
    cp.integral = lambda T1, T2: a * (T2 - T1) + 2.0 * e * (math.sqrt(T2) - math.sqrt(T1))
    return cp


_cp_urea_solid = _cp_berman(253.64, -2763.3)     # Voskov & Voronin 2016 (a, e), urea solid


# ======================================================================================
# Pure-component data, by phase
# ======================================================================================
# Each entry is (dHf(298.15) [J/mol], Cp) where Cp is a float (constant) or a callable.
#
#     h_i(T) = dHf + integral_{T0}^{T} Cp dT'
#
# ``Cp = None`` means "delegate to the validated Helgeson Cp in `thermo.properties`", which
# is how H2O(l), NH3(aq) and CO2(aq) stay on exactly the same datum as the electrolyte core.
PURE_COMPONENT = {
    # --- condensed urea -----------------------------------------------------------------
    # dHf on Tischer 2019 (the solid + liquid pair reproduces the MEASURED fusion enthalpy
    # 13.9 kJ/mol); Cp on Voskov 2016. Urea(l) reduces to ~150 J/(mol.K) at Tm = 405 K,
    # matching the constant 150.43 the VLE documentation previously used.
    #
    # Voskov's own dHf pair gives a fusion of 10.9 kJ/mol — an outlier against Tischer's
    # 13.9 and the plant's 15.1 — so the internally consistent Tischer pair is kept and
    # fusion matches direct calorimetry.
    ("Urea", "liquid"):   (-319700.0, _cp_berman(287.59, -2763.3)),  # dHf Tischer; (a,e) Voskov
    ("Urea", "solid"):    (-333599.0, _cp_urea_solid),               # dHf Tischer; (a,e) Voskov

    # --- ammonium carbamate: the reactive HPCC / reactor intermediate --------------------
    # Explicit formation enthalpies are what make the synthesis loop reaction-consistent
    # THROUGH the carbamate node rather than only across the net urea reaction.
    ("Carbamate", "solid"):  (-645047.0, _cp_berman(311.85, -3137.5)),   # Voskov dHf & (a,e)
    ("Carbamate", "liquid"): (-624323.0, _cp_berman(346.37, -3137.5)),   # Voskov dHf & (a,e)

    # --- biuret: the product-quality species ---------------------------------------------
    ("Biuret", "liquid"): (-537060.0, _cp_const(93.0)),      # Tischer 2019 Table 2
    ("Biuret", "solid"):  (-563700.0, _cp_const(131.3)),     # Tischer 2019 Table 2

    # --- water: liquid reuses props (Helgeson Cp); gas is CODATA/JANAF -------------------
    ("H2O", "liquid"):    (-285830.0, None),                 # Cp via props.cp0("H2O", T)
    ("H2O", "gas"):       (-241826.0, _cp_const(33.60)),     # CODATA dHf(g); Cp,g ~33.6

    # --- ammonia: aqueous reuses props; gas is CODATA ------------------------------------
    ("NH3", "aqueous"):   (-80290.0,  None),                 # props.cp0("NH3(aq)") = 72.04
    ("NH3", "gas"):       (-45940.0,  _cp_const(35.65)),     # CODATA dHf(g); Cp,g ~35.65

    # --- carbon dioxide: aqueous reuses props; gas is CODATA -----------------------------
    ("CO2", "aqueous"):   (-413800.0, None),                 # props.cp0("CO2(aq)") = 238.05
    ("CO2", "gas"):       (-393522.0, _cp_const(37.13)),     # CODATA dHf(g); Cp,g ~37.13

    # --- formaldehyde: the UF85 anti-caking additive -------------------------------------
    ("HCHO", "gas"):      (-108600.0, _cp_const(35.40)),     # NIST dHf(g); Cp,g ~35.4

    # --- inert and light gases (elements have dHf = 0; JANAF Cp,g) -----------------------
    ("N2", "gas"):        (0.0, _cp_const(29.12)),
    ("O2", "gas"):        (0.0, _cp_const(29.38)),
    ("H2", "gas"):        (0.0, _cp_const(28.84)),
    ("CH4", "gas"):       (-74600.0, _cp_const(35.69)),      # NIST dHf(g)
    ("Ar", "gas"):        (0.0, _cp_const(20.79)),
}


# ======================================================================================
# Phase selection — H0 does no flash
# ======================================================================================
# The caller's stream phase label selects which reference phase each species takes.
# Condensed-only species stay condensed; permanent gases stay gas.

_LIQUID_PHASE = {
    "Urea": "liquid", "Biuret": "liquid", "Carbamate": "liquid", "H2O": "liquid",
    "NH3": "aqueous", "CO2": "aqueous",
    "HCHO": "gas", "N2": "gas", "O2": "gas", "H2": "gas", "CH4": "gas", "Ar": "gas",
}

_VAPOUR_PHASE = {
    "H2O": "gas", "NH3": "gas", "CO2": "gas", "HCHO": "gas",
    "N2": "gas", "O2": "gas", "H2": "gas", "CH4": "gas", "Ar": "gas",
    # Urea, biuret and carbamate carried in a vapour stream are non-volatile — if present
    # as entrainment, keep them in their condensed state.
    "Urea": "liquid", "Biuret": "liquid", "Carbamate": "solid",
}


def _phase_map(phase: str) -> dict:
    """Select the per-species reference-phase column for a caller's stream phase label.

    The engine tags vapour streams ``'vapor'`` and non-condensable ones ``'gas'``; this
    module's own documentation says ``'vapour'``. All three must reach the vapour column.

    This is not cosmetic: a ``'gas'`` stream falling through to the liquid column would
    price NH3 and CO2 as *aqueous*, shifting the stream enthalpy by 35-44 kJ/mol with no
    error raised anywhere.
    """
    return _VAPOUR_PHASE if phase.strip().lower().startswith(("vap", "gas")) else _LIQUID_PHASE


def reference_phase(species: str, phase: str) -> str:
    """The reference phase ``species`` takes in a stream labelled ``phase``.

    Process utility
    ---------------
    Lets a unit price one species of a gas or a liquid on the datum its stream is published on
    — 322C001 bringing each species of its purge from the let-down temperature to the liquor's.
    """
    return _phase_map(phase)[species]


def unsupported_species(species) -> set:
    """Species the H0 datum cannot evaluate in BOTH reference phases.

    Lets a caller assert its own component set is covered **once at import**, instead of
    discovering a `KeyError` from `h0_stream` on a live simulation tick.
    """
    missing = set()
    for sp in species:
        if sp not in MOLAR_MASS or sp not in _LIQUID_PHASE or sp not in _VAPOUR_PHASE:
            missing.add(sp)
            continue
        if any((sp, column[sp]) not in PURE_COMPONENT
               for column in (_LIQUID_PHASE, _VAPOUR_PHASE)):
            missing.add(sp)
    return missing


# ======================================================================================
# Enthalpy evaluation
# ======================================================================================

@lru_cache(maxsize=512)
def h_species(species: str, phase: str, T_K: float) -> float:
    """Pure-component molar enthalpy h_i(T) [J/mol] on the elements-at-298.15 K datum.

    Process utility
    ---------------
    The building block of every stream enthalpy, and therefore of every energy balance.
    Cached because a single simulation tick evaluates it hundreds of times at a handful of
    distinct temperatures.

    Equation
    --------
        h_i(T) = dHf(298.15) + integral_{298.15}^{T} Cp(T') dT'

    Water(l), NH3(aq) and CO2(aq) delegate their Cp integral to the validated property
    module, so this datum is *shared* with the electrolyte core rather than parallel to it.

    Integration strategy, in order of preference:
      1. closed-form `.integral` if the Cp callable carries one (the Berman-Brown shapes);
      2. Simpson's rule with 20 intervals for any other callable — ample for a smooth Cp
         over a span of at most ~200 K;
      3. a plain ``Cp * dT`` for a constant.
    """
    key = (species, phase)
    if key not in PURE_COMPONENT:
        raise KeyError(f"no H0 constituent data for {key}")
    dHf, cp = PURE_COMPONENT[key]

    if cp is None:
        # Delegate to the validated Helgeson Cp in the property module. `props.h0` already
        # integrates dHf + int Cp, so the datum cannot drift between the two modules.
        props_key = {"H2O": "H2O", "NH3": "NH3(aq)", "CO2": "CO2(aq)"}[species]
        return props.h0(props_key, T_K)

    if T_K == T0:
        return dHf

    if callable(cp):
        exact = getattr(cp, "integral", None)
        if exact is not None:
            return dHf + exact(T0, T_K)
        # Simpson's rule on a smooth Cp.
        n = 20
        h = (T_K - T0) / n
        acc = cp(T0) + cp(T_K)
        for i in range(1, n):
            acc += (4.0 if i % 2 else 2.0) * cp(T0 + i * h)
        return dHf + acc * h / 3.0

    return dHf + cp * (T_K - T0)


def h0_stream(comp_kmolh: dict, T_C: float, phase: str = "liquid") -> dict:
    """H0 absolute enthalpy of a stream.

    Process utility
    ---------------
    The published enthalpy of a process stream, summable across nodes because the datum is
    the elements. This is what a node's energy balance adds up, what a duty calculation
    differences, and what the isenthalpic letdown holds constant.

    Parameters
    ----------
    comp_kmolh
        ``{species: kmol/h}`` using the `MOLAR_MASS` keys.
    T_C
        Stream temperature [deg C].
    phase
        ``'liquid'``, ``'vapour'`` / ``'vapor'``, or ``'gas'`` — selects the per-species
        reference phase. H0 performs no flash; the caller's stream phase decides.

    Returns
    -------
    dict
        ``enthalpy_flow_kW``, ``enthalpy_kJkg``, ``enthalpy_basis``, ``mass_kgh``.
    """
    T_K = T_C + 273.15
    phase_map = _phase_map(phase)
    H_Jh = 0.0            # J/h
    mass_kgh = 0.0
    for sp, nk in comp_kmolh.items():
        if nk == 0.0:
            continue
        if sp not in phase_map:
            raise KeyError(f"unknown species {sp!r} in stream composition")
        n_molh = nk * 1000.0
        H_Jh += n_molh * h_species(sp, phase_map[sp], T_K)
        mass_kgh += nk * MOLAR_MASS[sp]
    return {
        "enthalpy_flow_kW": H_Jh / 3.6e6,                                       # J/h -> kW
        "enthalpy_kJkg": (H_Jh / 1000.0) / mass_kgh if mass_kgh > 0 else None,  # kJ/kg
        "enthalpy_basis": EnthalpyBasis.H0.value,
        "mass_kgh": mass_kgh,
    }


def h0_stream_mass_pct(mass_kgh: float, mass_pct: dict, T_C: float,
                       phase: str = "liquid") -> dict:
    """Mass flow [kg/h] plus mass-% composition -> H0 enthalpy. See `h0_stream`.

    The engine's species layer carries mass fractions, so this is the wrapper most call
    sites actually use. Species not in `MOLAR_MASS` are dropped silently, which is correct
    here: a composition dict may legitimately carry derived entries a caller added.
    """
    comp_kmolh = {}
    for sp, pct in mass_pct.items():
        if sp in MOLAR_MASS and pct:
            comp_kmolh[sp] = mass_kgh * (pct / 100.0) / MOLAR_MASS[sp]
    return h0_stream(comp_kmolh, T_C, phase)


__all__ = [
    "EnthalpyBasis",
    "MOLAR_MASS",
    "PURE_COMPONENT",
    "T0",
    "R",
    "reference_phase",
    "unsupported_species",
    "h_species",
    "h0_stream",
    "h0_stream_mass_pct",
]
