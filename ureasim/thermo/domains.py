"""Species list, domain classification, and the refusal that keeps the models honest.

The problem this solves
-----------------------
No single liquid model covers this plant. Two are fitted here, and they own different
parts of it:

    DOMAIN_ELECTROLYTE    the volatiles carry the bubble point. Water activity from the
                          Extended UNIQUAC electrolyte table. Correct for the 323
                          recirculation / flash train, 328 desorption, 322C001.
    DOMAIN_NEUTRAL_UREA   a near-binary urea/water melt whose volatiles are traces. Water
                          activity from the neutral binary, because at 94-98 wt% urea the
                          electrolyte model's "urea is a mole-fraction diluent" assumption
                          fails hard — it reads the 324E001 melt +30.6 % and the 324E003
                          melt +65.7 % on bubble pressure.

Dispatching on composition is not a fudge. It is the only honest reading of what each model
was fitted to.

The third answer, and why it matters most
------------------------------------------
`classify` can return **None**, and that is a first-class answer.

The underlying interpolator **clamps** at its table edges rather than extrapolating. An
out-of-envelope call therefore does not fail loudly and does not extrapolate wildly — it
silently returns the edge node, i.e. **a frozen constant behind a call that looks like a
solve**. That is strictly worse than an honest hardcoded split vector, because the
heuristic becomes invisible.

So this layer refuses instead. `classify` returns None and the flash raises `OutOfDomain`
whenever the state leaves the fitted envelope, and the caller keeps whatever anchored model
it already has. The HP synthesis loop is entirely in that category today — see
`thermo.kvalues.k_ratio` for what it does instead.

Basis conventions
-----------------
Compositions in and out are **mass fractions**, matching the engine's species layer.
Internals work in mole fractions.

Ported from V1 `backend/thermo_service.py` (species and classification block).
Numerically identical.
"""

from __future__ import annotations

import math

from ureasim.thermo import extended_uniquac as neutral
from ureasim.thermo import vle

MODEL_NAME = ("unified gamma-phi (Extended UNIQUAC electrolyte + neutral urea/water) "
              "with SRK vapour")

#: Molar masses of every species the flowsheet tracks [g/mol].
MW = {"Urea": 60.056, "Biuret": 103.081, "NH3": 17.0304,
      "CO2": 44.0098, "H2O": 18.0152, "HCHO": 32.031,
      "N2": 28.0134, "O2": 31.9988, "CH4": 16.0425, "H2": 2.01588}

SPECIES = tuple(MW)

#: No vapour pressure at these conditions. They dilute, and nothing else. K = 0 exactly.
NONVOLATILE = ("Urea", "Biuret", "HCHO")

#: The CONDENSABLE volatiles — the three the electrolyte model speciates and gives
#: activities to.
VOLATILE = ("NH3", "CO2", "H2O")

#: The permanent gases. They distribute — overwhelmingly to the vapour — but they are NOT
#: UNIQUAC species: their liquid side is Henry's law on a gamma* = 1 infinite-dilution
#: reference, which IS the standard state, not a placeholder for a missing parameter.
INERTS = vle.INERTS

#: Everything that appears in both phases.
DISTRIBUTING = VOLATILE + INERTS

DOMAIN_ELECTROLYTE = "electrolyte_gamma_phi"
DOMAIN_NEUTRAL_UREA = "neutral_urea_water_uniquac"

#: Above this urea mass fraction the electrolyte model's non-volatile-diluent treatment of
#: urea is no longer defensible and the neutral binary takes the water activity. 0.90 sits
#: between the 323F010 product (80.0 wt%, electrolyte, +1.7 %) and the 324E001 melt
#: (94.3 wt%, where the electrolyte model is already +30.6 %), so each stage lands on the
#: model that was fitted for it.
UREA_NEUTRAL_THRESHOLD = 0.90

#: Below this total volatile loading a liquor has no meaningful NH3/CO2 bubble-point
#: contribution [mol per kg water].
VOLATILE_TRACE_LOADING = 1.0e-3


class OutOfDomain(ValueError):
    """The requested state lies outside every fitted envelope this service owns.

    Raised rather than answered. See the module docstring: a clamped edge lookup wearing
    the shape of a solve is the failure this whole layer exists to prevent.
    """


# ======================================================================================
# Composition helpers
# ======================================================================================

def norm_mass(w: dict) -> dict:
    """Normalise a mass-fraction vector over `SPECIES`.

    An empty or negative vector returns pure water rather than dividing by zero: a stream
    with no mass has no composition, and pure water is the neutral choice that keeps every
    downstream ratio finite.
    """
    tot = sum(max(w.get(k, 0.0), 0.0) for k in SPECIES)
    if tot <= 0.0:
        return {k: (1.0 if k == "H2O" else 0.0) for k in SPECIES}
    return {k: max(w.get(k, 0.0), 0.0) / tot for k in SPECIES}


def mass_to_mole(w: dict) -> dict:
    """Mass fractions -> mole fractions over `SPECIES`.

    Total-species basis, no speciation: the flowsheet's mass balance tracks *total* NH3 and
    *total* CO2, so that is the basis every K-value here is on.
    """
    n = {k: max(w.get(k, 0.0), 0.0) / MW[k] for k in SPECIES}
    tot = sum(n.values())
    if tot <= 0.0:
        return {k: (1.0 if k == "H2O" else 0.0) for k in SPECIES}
    return {k: n[k] / tot for k in SPECIES}


def mole_to_mass(x: dict) -> dict:
    """Mole fractions -> mass fractions over `SPECIES`."""
    m = {k: max(x.get(k, 0.0), 0.0) * MW[k] for k in SPECIES}
    tot = sum(m.values())
    if tot <= 0.0:
        return {k: (1.0 if k == "H2O" else 0.0) for k in SPECIES}
    return {k: m[k] / tot for k in SPECIES}


# ======================================================================================
# Domain classification
# ======================================================================================

def classify(w: dict, t_c: float, p_bara: float = None) -> str | None:
    """Which fitted model owns this state, or ``None`` if neither does.

    Process utility
    ---------------
    Every phase-equilibrium call in the plant starts here. Returning None is what lets a
    323 stage use a rigorous flash while the 322 loop keeps its licensor-anchored split,
    without either of them having to know about the other.
    """
    w = norm_mass(w)
    if not math.isfinite(t_c):
        return None
    n_load, c_load = vle.loadings(w)
    if not (math.isfinite(n_load) and math.isfinite(c_load)):
        return None

    urea_like = w.get("Urea", 0.0) + w.get("Biuret", 0.0)
    if urea_like >= UREA_NEUTRAL_THRESHOLD:
        # The neutral binary owns the water activity here, so its own declared window
        # governs — not the electrolyte grid's.
        t_k = t_c + 273.15
        t_lo, t_hi = neutral.VALID_TEMPERATURE_K
        if not (t_lo <= t_k <= t_hi):
            return None
        if p_bara is not None:
            p_lo, p_hi = neutral.VALID_PRESSURE_BARA
            if not (p_lo <= p_bara <= p_hi):
                return None
        # The trace volatiles still ride the electrolyte dilute limit, so its grid must
        # hold them too.
        if not vle.in_grid(w, t_c):
            return None
        return DOMAIN_NEUTRAL_UREA

    # The envelope test is the table's OWN `in_grid`, not a pair of axis comparisons
    # restated here. That flag is stricter than the box: it is False if any of the eight
    # corner nodes the interpolation actually uses failed to converge, so a corner of the
    # envelope the continuation could not reach cannot be classified as owned. It is also
    # the single place the bound lives, so a re-graded grid cannot leave this function
    # testing the old one.
    if not vle.in_grid(w, t_c):
        return None

    # The pressure bound is stated rather than tabulated, because the activity model
    # carries no pressure dependence at all — see `thermo.vle_grid`. It is enforced here so
    # that the loop's 144 bar a is inside a DECLARED band instead of inside no band, and so
    # that a wild transient pressure refuses (and `k_ratio` falls back to the licensor's
    # split) rather than being answered by a model with no opinion about pressure.
    if p_bara is not None:
        p_lo, p_hi = vle.VALID_PRESSURE_BARA
        if not (p_lo <= p_bara <= p_hi):
            return None
    return DOMAIN_ELECTROLYTE


def domain_report(w: dict, t_c: float, p_bara: float = None) -> dict:
    """Diagnostic companion to `classify` — says WHICH bound failed.

    Carried into every `OutOfDomain` message and into telemetry, so a refusal in the field
    names its own cause instead of needing a debugger.
    """
    w = norm_mass(w)
    n_load, c_load = vle.loadings(w)
    s, f = vle.coords(w)
    env = vle.envelope()
    return {
        "domain": classify(w, t_c, p_bara),
        "t_c": t_c, "p_bara": p_bara,
        # Molalities are RETAINED here even though nothing interpolates on them any more:
        # "N = 869 against a 16 top node" is the most legible statement of what used to be
        # wrong, and it stays visible in telemetry.
        "n_load_mol_per_kg_water": n_load, "c_load_mol_per_kg_water": c_load,
        "s_volatile_mole_frac": s, "f_co2_of_volatiles": f,
        "t_envelope_c": env["t_c"], "s_envelope": env["s"], "f_envelope": env["f"],
        "in_grid": vle.in_grid(w, t_c),
        "urea_like_mass_frac": w.get("Urea", 0.0) + w.get("Biuret", 0.0),
        "model": MODEL_NAME,
    }


__all__ = [
    "MODEL_NAME", "MW", "SPECIES", "NONVOLATILE", "VOLATILE", "INERTS", "DISTRIBUTING",
    "DOMAIN_ELECTROLYTE", "DOMAIN_NEUTRAL_UREA",
    "UREA_NEUTRAL_THRESHOLD", "VOLATILE_TRACE_LOADING",
    "OutOfDomain", "norm_mass", "mass_to_mole", "mole_to_mass",
    "classify", "domain_report",
]
