"""The NH3-CO2-H2O activity table — nodes, continuation build, cache, interpolation.

What this is
------------
The Extended UNIQUAC liquid model is a speciating Newton solve (`thermo.speciation`). At
roughly 15 ms per converged call it cannot run at every node of every unit on every 10 Hz
tick. So it is solved **once** on a grid, cached, and interpolated.

This module owns that grid. `thermo.vle` owns the physics that reads it.

The coordinates, and why they are not molalities
-------------------------------------------------
The first version of this table was indexed by ``(T, N, C)`` with N and C the loading in
mol per kg of **water**. That is the natural coordinate of a molality-referenced
electrolyte model, and it is fine everywhere water is the solvent. In the HP synthesis loop
it is not a coordinate at all:

    stage                          T (C)   N (mol/kg water)   C (mol/kg water)
    322R001 overflow (stream 207)  183           100.0               22.4
    322E003 off-gas feed           183           869.3              258.1

against a table that stopped at N = 16, C = 7. Those are not large numbers because the
liquor is exotic — they are large because **the denominator is vanishing**. The molality of
a liquor with no water in it is infinite, so no molality grid can ever be wide enough, and
every finite one silently clamps: a frozen constant wearing a rigorous-looking call.

The grid is therefore indexed by two **bounded** coordinates on the water + volatile
sub-system:

    s = (n_NH3 + n_CO2) / (n_NH3 + n_CO2 + n_H2O)     total volatile mole fraction, [0, 1)
    f = n_CO2 / (n_NH3 + n_CO2)                       CO2 share of the volatiles, [0, 1]

In those, the same two states are unremarkable: ``s`` = 0.688 and 0.953.

**The evidence that this is a coordinate transform and not a new model:** on the re-indexed
grid the three validated 323 stages move by under one percentage point, and at two of the
three they move *toward* the plant.

Why there is no pressure axis
------------------------------
The Extended UNIQUAC activity model has no pressure dependence at all, and the one term
that would give it one — the Poynting factor ``exp(v_inf (P - Psat)/RT)`` — needs
infinite-dilution partial molar volumes this repository does not hold from any source.

The liquid side is therefore pressure-independent **by construction**. The missing Poynting
term is worth roughly +15 % on an NH3 or CO2 partial pressure at 144 bar and is very nearly
constant across the loop's band, so it is absorbed by the anchored **ratio** form the 322
loop uses and cancels there. It does **not** cancel for an absolute bubble pressure, which
is one more reason no absolute HP-loop number reaches the engine.

Continuation, and why a node can fail
--------------------------------------
`speciate`'s dilute initial guess stops converging above about N = 40 mol/kg water — a
basin-of-attraction failure, not a domain limit. Seeded from a converged neighbour the
identical solver reaches N = 869 in five Newton steps at a residual of 8.5e-14. So the
build **marches**: temperature outermost, then s, then f, each node seeded from the
converged node one step back.

A node that survives none of its seeds is **stored with its flag cleared** rather than
dropped, so the interpolator can refuse cells that touch it instead of silently
interpolating through a non-solution.

Ported from V1 `backend/vle_nh3co2h2o.py` (grid half). Numerically identical.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time

from ureasim.thermo import properties as props
from ureasim.thermo.parameters import N_W_PER_KG, SOLUTES

# ======================================================================================
# Node definitions
# ======================================================================================
# T : 80-210 C. The top was raised for the synthesis loop (183 C at the reactor overflow)
#     and for the 328C004 reboiler band. Nodes sit ON the three stages whose bubble
#     pressures are validated (99 / 135) and on the reactor (183), so those states are read
#     off a solved node in the temperature direction rather than between two.
_T_NODES = (80.0, 99.0, 118.0, 135.0, 152.0, 168.0, 183.0, 197.0, 210.0)

# s : total volatile mole fraction. Design values are 323F010 0.0047, 323C003 0.088,
#     322R001 overflow 0.688, 322E003 feed 0.953. Spaced so the nodes cluster where the
#     plant lives at BOTH ends, and bracketed on logit(s) — see `_bracket`.
_S_NODES = (1.0e-5, 1.0e-4, 1.0e-3, 5.0e-3, 0.02, 0.06, 0.13, 0.24,
            0.38, 0.53, 0.67, 0.79, 0.88, 0.94, 0.98)

# f : CO2 share of the volatiles, i.e. 1/(1 + N/C). Design values are 323F010 0.077,
#     323C003 0.160, 322R001 0.183, 322E003 0.229; the band spans N/C from 500 down to 0.28.
_F_NODES = (0.002, 0.01, 0.03, 0.07, 0.14, 0.24, 0.38, 0.56, 0.78)

#: A node is accepted only if its speciation residual is at or below this. `speciate`'s own
#: loop tolerance is 1e-11, so 1e-8 leaves three decades of slack for the hardest nodes
#: without letting a non-solution through — a basin failure returns a residual of order 1
#: to 200, which is nowhere near this.
NODE_RESID_TOL = 1.0e-8

#: Bump when `_node_activities` changes what a node MEANS. "3" is the re-index from
#: (T, N, C) molalities to (T, s, f) mole fractions.
_TABLE_VERSION = "3"

_HERE = os.path.dirname(os.path.abspath(__file__))
_CACHE_PATH = os.path.join(_HERE, ".vle_activity_grid.json")

#: [i_T][i_s][i_f] -> [a_NH3, a_CO2, a_H2O, n_sub_per_kg_water, converged]
_TABLE = None
_BUILD_STATS = None

#: Property modules the stored nodes depend on. The cache key hashes these rather than this
#: whole file, so editing the interpolator or the docstrings does not throw away a build —
#: but changing any parameter or solver does.
_PROPERTY_SOURCES = ("parameters.py", "standard_state.py", "activity.py", "speciation.py")


def _clamp(x, lo, hi):
    return lo if x < lo else (hi if x > hi else x)


def _cache_key() -> str:
    """Hash of everything a stored node depends on."""
    h = hashlib.sha256()
    for name in _PROPERTY_SOURCES:
        try:
            with open(os.path.join(_HERE, name), "rb") as f:
                h.update(f.read())
        except OSError:
            h.update(b"\x00")
    h.update(repr((_TABLE_VERSION, _T_NODES, _S_NODES, _F_NODES,
                   NODE_RESID_TOL)).encode())
    return h.hexdigest()


# ======================================================================================
# Coordinates
# ======================================================================================

def sf_to_loadings(s: float, f: float) -> tuple[float, float]:
    """``(s, f)`` -> ``(N, C)`` in mol per kg of water. Exact inverse of `loadings_to_sf`."""
    s = _clamp(s, 0.0, 1.0 - 1e-12)
    r = N_W_PER_KG * s / (1.0 - s)          # total volatile mol per kg water
    return r * (1.0 - f), r * f


def loadings_to_sf(n_load: float, c_load: float) -> tuple[float, float]:
    """``(N, C)`` in mol/kg water -> ``(s, f)``. Finite for every finite loading, C = 0 included."""
    tot = max(n_load, 0.0) + max(c_load, 0.0)
    if tot <= 0.0:
        return 0.0, 0.0
    return tot / (N_W_PER_KG + tot), max(c_load, 0.0) / tot


def nodes() -> tuple[tuple, tuple, tuple]:
    """The three node axes, for a caller that needs to report or test the envelope."""
    return _T_NODES, _S_NODES, _F_NODES


# ======================================================================================
# Node solve and continuation
# ======================================================================================

def _node_activities(t_c: float, s: float, f: float, seed=None):
    """Solve one grid node: liquid speciation plus full Extended UNIQUAC activities.

    Returns ``(a_NH3, a_CO2, a_H2O, n_sub_per_kg_water, ok, molalities)`` where
    ``a_i = x_i gamma_i`` on the mole-fraction scale of the water + electrolyte sub-system
    (urea and biuret enter later, as a dilution factor), ``ok`` is True only if the
    speciation residual met `NODE_RESID_TOL`, and ``molalities`` is the raw solution vector
    so the next node can be seeded from it.
    """
    t_k = t_c + 273.15
    n_load, c_load = sf_to_loadings(s, f)
    md = props.speciate(max(n_load, 1e-6), max(c_load, 1e-6), T=t_k, m_guess=seed)
    ok = md.get("resid", float("inf")) <= NODE_RESID_TOL
    n_sub = N_W_PER_KG + sum(md[sp] for sp in SOLUTES)
    x = {"H2O": N_W_PER_KG / n_sub}
    for sp in SOLUTES:
        x[sp] = md[sp] / n_sub
    lng = props.activity_ln_gamma(x, t_k)
    return (x["NH3(aq)"] * math.exp(lng["NH3(aq)"]),
            x["CO2(aq)"] * math.exp(lng["CO2(aq)"]),
            x["H2O"] * math.exp(lng["H2O"]),
            n_sub, ok, {sp: md[sp] for sp in SOLUTES})


def _march_temperature(t_from, t_to, s, f, seed, depth=0):
    """Solve ``(t_to, s, f)`` seeded from a solution at ``(t_from, s, f)``, bisecting T on failure.

    Temperature is the smoothest continuation direction of the three — the speciation moves
    continuously along it and the activity coefficients with it — so this is the fallback
    that rescues the handful of nodes a single jump cannot reach.
    """
    res = _node_activities(t_to, s, f, seed)
    if res[4] or depth >= 6 or t_from is None:
        return res
    t_mid = 0.5 * (t_from + t_to)
    mid = _march_temperature(t_from, t_mid, s, f, seed, depth + 1)
    if not mid[4]:
        return res
    return _march_temperature(t_mid, t_to, s, f, mid[5], depth + 1)


def _build_table():
    """Build the whole (T, s, f) table by continuation.

    Marching order is TEMPERATURE outermost, then s, then f. Each node is attempted from
    the converged node one step back in T first — measured, that seed alone carries 958 of
    960 probe nodes and cuts the mean solve from 84 ms to 15 ms — then from its
    s-neighbour, then from its f-neighbour, then cold.
    """
    nt, ns, nf = len(_T_NODES), len(_S_NODES), len(_F_NODES)
    table = [[[None] * nf for _ in range(ns)] for _ in range(nt)]
    seeds = [[[None] * nf for _ in range(ns)] for _ in range(nt)]
    failed = 0
    for it in range(nt):
        t_c = _T_NODES[it]
        t_prev = _T_NODES[it - 1] if it else None
        for i_s in range(ns):
            for i_f in range(nf):
                cands = []
                if it and seeds[it - 1][i_s][i_f] is not None:
                    cands.append((seeds[it - 1][i_s][i_f], t_prev))
                if i_s and seeds[it][i_s - 1][i_f] is not None:
                    cands.append((seeds[it][i_s - 1][i_f], None))
                if i_f and seeds[it][i_s][i_f - 1] is not None:
                    cands.append((seeds[it][i_s][i_f - 1], None))
                cands.append((None, None))            # cold, the original dilute ansatz
                best = None
                for seed, t_from in cands:
                    res = (_march_temperature(t_from, t_c, _S_NODES[i_s],
                                              _F_NODES[i_f], seed)
                           if t_from is not None
                           else _node_activities(t_c, _S_NODES[i_s], _F_NODES[i_f], seed))
                    if res[4]:
                        best = res
                        break
                    if best is None:
                        best = res
                if not best[4]:
                    failed += 1
                # Stored WITH its flag either way, so `_interp` can refuse a cell that
                # touches a non-solution rather than interpolating through it.
                table[it][i_s][i_f] = [best[0], best[1], best[2], best[3],
                                       1.0 if best[4] else 0.0]
                seeds[it][i_s][i_f] = best[5] if best[4] else None
    return table, failed


def ensure_table():
    """Load the cached table, or build it. Idempotent."""
    global _TABLE, _BUILD_STATS
    if _TABLE is not None:
        return _TABLE
    key = _cache_key()
    try:
        with open(_CACHE_PATH, "r", encoding="utf-8") as f:
            doc = json.load(f)
        if doc.get("key") == key:
            _TABLE = doc["table"]
            _BUILD_STATS = {"nodes": len(_T_NODES) * len(_S_NODES) * len(_F_NODES),
                            "failed": doc.get("failed", 0),
                            "seconds": doc.get("seconds", 0.0), "cached": True}
            return _TABLE
    except (OSError, ValueError, KeyError):
        pass

    n_nodes = len(_T_NODES) * len(_S_NODES) * len(_F_NODES)
    print(f"[vle] building NH3-CO2-H2O Extended UNIQUAC activity table by continuation "
          f"({n_nodes} nodes, ~20 s, once per model change)", flush=True)
    t0 = time.time()
    _TABLE, failed = _build_table()
    seconds = time.time() - t0
    _BUILD_STATS = {"nodes": n_nodes, "failed": failed,
                    "seconds": seconds, "cached": False}
    print(f"[vle] table built in {seconds:.1f} s "
          f"({n_nodes - failed}/{n_nodes} nodes converged)", flush=True)
    try:
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({"key": key, "table": _TABLE,
                       "failed": failed, "seconds": seconds}, f)
    except OSError:
        pass          # the cache is an optimisation, never a hard dependency
    return _TABLE


def build_stats() -> dict:
    """Node count, failure count and build wall time — for the boot report and for tests."""
    ensure_table()
    return dict(_BUILD_STATS or {})


# ======================================================================================
# Interpolation
# ======================================================================================

def _bracket(axis, v, mode: str = "linear"):
    """``(index, weight)`` for interpolation, clamped at both ends — never extrapolating.

    ``mode`` selects the coordinate the weight is taken on:

        linear   v itself.
        log      ln(v). For f, whose activities span decades across the band.
        logit    ln(v/(1-v)). For s. This is exactly ln(N + C) up to the constant
                 ln(55.508), so in the dilute limit the weighting is IDENTICAL to the
                 log-molality weighting the pre-re-index table used — which is what makes
                 the re-index a coordinate change rather than a new interpolation error.
    """
    if v <= axis[0]:
        return 0, 0.0
    if v >= axis[-1]:
        return len(axis) - 2, 1.0
    if mode == "logit":
        def g(u):
            return (math.log(u / (1.0 - u)) if 0.0 < u < 1.0
                    else (-745.0 if u <= 0.0 else 745.0))
    elif mode == "log":
        def g(u):
            return math.log(max(u, 1e-300))
    else:
        def g(u):
            return u
    for i in range(1, len(axis)):
        if v <= axis[i]:
            lo, hi = g(axis[i - 1]), g(axis[i])
            return i - 1, (g(v) - lo) / (hi - lo) if hi > lo else 0.0
    return len(axis) - 2, 1.0


def interp(t_c: float, s: float, f: float):
    """Trilinear interpolation of ``(a_NH3, a_CO2, a_H2O, n_sub)`` plus a converged flag.

    ``a_NH3`` and ``a_CO2`` are interpolated as **log(a)**: they are strictly positive,
    span many decades, and their true shape between nodes is exponential, so a linear blend
    of the logs is both exact at the nodes and far closer in between. ``a_H2O`` (order 1)
    and ``n_sub`` (order 56) stay linear.

    The fifth return value is False if **any** of the eight corner nodes actually used
    failed to converge. That is the honest form of the clamp warning: a cell touching a
    non-solution is not a solve, whatever its coordinates say.
    """
    tab = ensure_table()
    it, ft = _bracket(_T_NODES, t_c)
    i_s, fs = _bracket(_S_NODES, s, mode="logit")
    i_f, ff = _bracket(_F_NODES, f, mode="log")
    ln_a_nh3 = ln_a_co2 = a_h2o = n_sub = 0.0
    corners_ok = True
    for dt_ in (0, 1):
        wt = ft if dt_ else (1.0 - ft)
        if wt == 0.0:
            continue
        for ds in (0, 1):
            ws = fs if ds else (1.0 - fs)
            if ws == 0.0:
                continue
            for df in (0, 1):
                wf = ff if df else (1.0 - ff)
                if wf == 0.0:
                    continue
                node = tab[it + dt_][i_s + ds][i_f + df]
                w = wt * ws * wf
                ln_a_nh3 += w * math.log(max(node[0], 1e-300))
                ln_a_co2 += w * math.log(max(node[1], 1e-300))
                a_h2o += w * node[2]
                n_sub += w * node[3]
                if node[4] < 0.5:
                    corners_ok = False
    return math.exp(ln_a_nh3), math.exp(ln_a_co2), a_h2o, n_sub, corners_ok


def in_box(t_c: float, s: float, f: float) -> bool:
    """Axis test for the tabulated envelope.

    The two composition axes are bounded from **above only**, and that asymmetry is the
    physics, not a slip.

    Clamping at the TOP of s or f fabricates a frozen constant: the true activity keeps
    rising past the last node and the table hands back the node instead — exactly the
    failure this module exists to make visible.

    Clamping at the BOTTOM lands in the dilute limit, where every volatile term is
    vanishing anyway. At the floor nodes (s = 1e-5, f = 0.002) the tabulated CO2 loading is
    1.1e-6 mol per kg of water and ``a_CO2`` is of order 1e-8, so treating a liquor with
    *less* CO2 than that as though it had exactly that much moves its bubble pressure far
    below any pressure this plant resolves. Refusing there instead would put pure steam,
    and every 324 urea melt whose volatiles are traces, outside every fitted model in the
    repository — which is not what the fit says.

    TEMPERATURE is bounded on BOTH sides and stays that way: below the 80 C node the
    activities are not vanishing, they are simply untabulated. A 323F010 liquor carrying
    1.6 wt% NH3 has a real bubble point below 80 C at 0.46 bar a, and a clamped 80.0 came
    back looking like an answer.
    """
    return (_T_NODES[0] <= t_c <= _T_NODES[-1]
            and s <= _S_NODES[-1] and f <= _F_NODES[-1]
            and s >= 0.0 and f >= 0.0)


__all__ = [
    "NODE_RESID_TOL",
    "sf_to_loadings", "loadings_to_sf", "nodes",
    "ensure_table", "build_stats", "interp", "in_box",
]
