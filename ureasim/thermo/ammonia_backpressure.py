"""Ammonia and carbon dioxide back-pressure over a dilute ammonia water, and its heat of absorption.

What this gives the plant model
-------------------------------
An absorber takes up ammonia only while the gas's partial pressure stands above what its wash
liquor already exerts. This module answers, for a dilute NH3-CO2-H2O liquid: what NH3 and CO2
partial pressures does it hold back, how steeply do they rise as it loads up (the slope of the
absorber's equilibrium line), and how much heat does each mol it takes up release. A liquor
that has loaded up or warmed up holds back more, so its absorber takes less.

The chemistry is carried, not fitted: the Extended UNIQUAC speciation (`thermo.speciation`)
splits the total ammonia and CO2 into free NH3(aq), CO2(aq) and the ions, and only the free
molecules exert a pressure, on the Rumpf & Maurer / Darde Henry constants (`thermo.henry`):

    p_NH3 = H_NH3(T) . x_NH3(aq) . gamma_NH3(aq)
    p_CO2 = H_CO2(T) . x_CO2(aq) . gamma_CO2(aq)

The grid
--------
A speciation is a full Newton solve, too slow for every tick, so the pressures and slopes are
tabulated lazily, one node at a time, on a grid geometric in both molalities (ratio 1.2) and
linear in temperature (1 K), and interpolated trilinearly on the LOGARITHMS of the pressures:
across the NH3:CO2 stoichiometric line the pressures span decades, and a dilute condensate at
0.06 mol/kg CO2 must not borrow the pressure of an acidic 0.25 mol/kg neighbour. The speciation
is regressed on 10-100 C; beyond it each pressure carries on along van 't Hoff at the edge's own
heat of absorption, continuous at the edge:

    ln p = ln p_edge - dH / R . (1/T - 1/T_edge)

The heat of absorption is the temperature slope of the same back-pressure at fixed liquid
composition — so CO2 is charged its carbamate heat (80-99 kJ/mol over the 322C001 liquor), not
its physical solution heat (16 kJ/mol, the bare Henry constant's):

    dH_i = -R . d ln p_i / d(1/T)

The liquid's state, for a flash
-------------------------------
`liquid_state` is the V1.1 addition the condensing letdown (`thermo.condensing_letdown`, handoff
B-19) stands on: the two pressures and the water activity, a_w = x_H2O . gamma_H2O, from one
speciation per node on a second lazy grid of the same spacing, without the slopes a flash does
not use. The water a liquor holds back is p_H2O = a_w . psat(T); a concentrated ammonium-
carbamate liquor holds its water at a_w 0.2 to 0.5, which is what lets it condense from a gas
far above water's own dew point. Beyond 10-100 C the pressures carry on along van 't Hoff as in
`back_pressure` and the activity is held at the edge. V1's grid and its four outputs are
untouched. Its two pressures are V1's grid's to the bit (one speciation computes both), so the
liquor's heats of absorption read off it are V1's too (`liquor_heat_of_absorption_j_mol`).

The node stores
---------------
A node costs a speciation, about 20 ms (three on V1's grid, for the slopes), and a property search
walked into a region no earlier run visited tabulates hundreds in one tick: a lost motive stalled
the simulator up to 26 s a tick on HV-322604's letdown, and the vacuum train's back condensers and
322C001's start-up calibration stall it for seconds on V1's grid (handoff A-18). The whole block a
liquor up to 1000 mol/kg water reads, 10 to 100 C — 460 460 nodes a grid — is therefore tabulated
ahead of time (`build_state_store`, `build_back_store`) and kept beside this module
(`thermo.node_store`), each store keyed on the hash of everything its nodes depend on; a node is
served from its store, bit for bit what the lazy path computes. A missing or stale store is never
an error: the grid tabulates lazily, as before, until the store is rebuilt.

Source: V1 ``backend/packed_absorber.py`` (the back-pressure block, ``henry_nh3_pa`` and
``heat_of_absorption_j_mol``), on V1 ``props_nh3co2h2o`` — ported in `thermo.speciation`,
`thermo.activity` and `thermo.henry`. Ported verbatim; `liquid_state` is the rewrite's.
"""

from __future__ import annotations

import hashlib
import inspect
import math
import os

from ureasim.thermo import node_store
from ureasim.thermo.activity import activity_ln_gamma
from ureasim.thermo.domains import MW
from ureasim.thermo.henry import henry_co2_MPa, henry_nh3_MPa
from ureasim.thermo.parameters import M_W, N_W_PER_KG, R, SOLUTES
from ureasim.thermo.speciation import speciate

__all__ = [
    "GRID_RATIO", "GRID_DT", "N_FLOOR", "C_FLOOR", "T_SPEC_LO_K", "T_SPEC_HI_K",
    "henry_nh3_pa", "molalities", "back_pressure", "heat_of_absorption_j_mol",
    "liquid_state", "liquor_heat_of_absorption_j_mol", "state_node_values",
    "STATE_STORE_MOLAL_MAX", "STATE_STORE_I", "STATE_STORE_J", "STATE_STORE_K",
    "STATE_STORE_PATH", "state_store_key", "build_state_store",
    "back_pressure_node_values", "BACK_STORE_PATH", "back_store_key", "build_back_store",
]

#: The grid: the molality ratio between neighbouring nodes, and the temperature step [K].
GRID_RATIO, GRID_DT = 1.2, 1.0

#: The lowest molalities the grid resolves [mol per kg of water]: NH3, CO2.
N_FLOOR, C_FLOOR = 0.01, 0.001

#: The speciation's regressed range [K], 10-100 C; van 't Hoff beyond.
T_SPEC_LO_K, T_SPEC_HI_K = 283.15, 373.15

_LN_R = math.log(GRID_RATIO)

#: Floor on a liquid's water fraction in its molalities [-].
_WATER_FLOOR = 1e-9

#: Floor on a tabulated pressure or slope before its logarithm [Pa, Pa per mole fraction].
_LOG_FLOOR = 1e-12

#: The relative step of the slope's finite difference [-].
_SLOPE_STEP = 0.02

#: The tabulated nodes: (i, j, k) -> the logarithms of (p_NH3, p_CO2, dp_NH3/dx, dp_CO2/dx).
_NODES: dict = {}

#: The liquid-state nodes, same spacing: (i, j, k) -> the logarithms of (p_NH3, p_CO2, a_H2O).
_STATE_NODES: dict = {}

#: The pre-tabulated liquid-state block: every node a liquor of molalities up to 1000 mol/kg water
#: — the condensing letdown's ``MOLAL_MAX`` — reads between 10 and 100 C; i and j from the floors,
#: k over the clamped temperatures and the node above the top one.
STATE_STORE_MOLAL_MAX = 1000.0
STATE_STORE_I = (0, int(math.floor(math.log(STATE_STORE_MOLAL_MAX / N_FLOOR) / _LN_R)) + 1)
STATE_STORE_J = (0, int(math.floor(math.log(STATE_STORE_MOLAL_MAX / C_FLOOR) / _LN_R)) + 1)
STATE_STORE_K = (int(T_SPEC_LO_K // GRID_DT), int(T_SPEC_HI_K // GRID_DT) + 1)

#: Where the stores are kept: beside this module, as `thermo.vle_grid` keeps its table. V1's grid
#: is stored over the same block.
STATE_STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".liquid_state_grid.bin")
BACK_STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               ".back_pressure_grid.bin")

#: The property modules a node depends on, hashed into the store's key with the node's own code.
_STORE_SOURCES = ("parameters.py", "standard_state.py", "activity.py", "speciation.py",
                  "henry.py", "iapws.py")

#: Each store once read, by path: absent until its grid's first node is asked for, False when
#: there is none valid.
_STORES: dict = {}


def henry_nh3_pa(t_k: float) -> float:
    """Henry's constant for NH3 in water [Pa, mole-fraction scale]."""
    return henry_nh3_MPa(t_k) * 1.0e6


def molalities(w: dict) -> tuple[float, float]:
    """Total NH3 and CO2 of a liquid of mass fractions ``w`` [mol per kg of water], each held
    at the grid's floor.

    Process utility
    ---------------
    Puts a liquor's loading on the speciation's basis. A clean condensate reads the floor, so
    its back-pressure is the grid's smallest, not a logarithm of zero.
    """
    ww = max(w.get("H2O", 0.0), _WATER_FLOOR)
    return (max(w.get("NH3", 0.0) / (MW["NH3"] / 1000.0) / ww, N_FLOOR),
            max(w.get("CO2", 0.0) / (MW["CO2"] / 1000.0) / ww, C_FLOOR))


def _liquid_state(n_tot: float, c_tot: float, t_k: float) -> tuple[float, float, float]:
    """(p_NH3 [Pa], p_CO2 [Pa], a_H2O [-]) over a liquid of total NH3 and CO2 [mol/kg water] at
    ``t_k``, from one speciation."""
    sp = speciate(n_tot, c_tot, t_k)
    ntot = N_W_PER_KG + sum(sp[s] for s in SOLUTES)
    x = {"H2O": N_W_PER_KG / ntot}
    for s in SOLUTES:
        x[s] = sp[s] / ntot
    lng = activity_ln_gamma(x, t_k)
    return (henry_nh3_pa(t_k) * x["NH3(aq)"] * math.exp(lng["NH3(aq)"]),
            henry_co2_MPa(t_k) * 1.0e6 * x["CO2(aq)"] * math.exp(lng["CO2(aq)"]),
            x["H2O"] * math.exp(lng["H2O"]))


def _partials(n_tot: float, c_tot: float, t_k: float) -> tuple[float, float]:
    """(p_NH3, p_CO2) [Pa] over a liquid of total NH3 and CO2 [mol/kg water] at ``t_k``."""
    p_n, p_c, _ = _liquid_state(n_tot, c_tot, t_k)
    return p_n, p_c


def back_pressure_node_values(i: int, j: int, k: int) -> tuple:
    """One grid node computed: the logarithms of the two pressures [Pa] and of the equilibrium
    slopes [Pa per unit liquid mole fraction, dx = dm . M_w], from three speciations. What the lazy
    path tabulates and the store holds."""
    n_tot, c_tot, t_k = N_FLOOR * GRID_RATIO ** i, C_FLOOR * GRID_RATIO ** j, k * GRID_DT
    p_n, p_c = _partials(n_tot, c_tot, t_k)
    dn, dc = _SLOPE_STEP * n_tot, _SLOPE_STEP * c_tot
    p_n2, _ = _partials(n_tot + dn, c_tot, t_k)
    _, p_c2 = _partials(n_tot, c_tot + dc, t_k)
    vals = (p_n, p_c, (p_n2 - p_n) / (dn * M_W), (p_c2 - p_c) / (dc * M_W))
    return tuple(math.log(max(v, _LOG_FLOOR)) for v in vals)


def back_store_key() -> str:
    """The SHA-256 of everything a stored node of V1's grid depends on (`state_store_key`'s, with
    the slopes' finite difference)."""
    h = hashlib.sha256()
    here = os.path.dirname(os.path.abspath(__file__))
    for name in _STORE_SOURCES:
        with open(os.path.join(here, name), "rb") as f:
            h.update(f.read())
    for fn in (_liquid_state, _partials, back_pressure_node_values):
        h.update(inspect.getsource(fn).encode())
    h.update(repr((GRID_RATIO, GRID_DT, N_FLOOR, C_FLOOR, _LOG_FLOOR, _SLOPE_STEP, M_W,
                   STATE_STORE_I, STATE_STORE_J, STATE_STORE_K)).encode())
    return h.hexdigest()


def _store(path: str, key_fn):
    """The store at ``path``, read on first use; False when there is none valid."""
    store = _STORES.get(path)
    if store is None:
        store = node_store.read_store(path, key_fn()) or False
        _STORES[path] = store
    return store


def _build(node_fn, key_fn, path: str, width: int, workers, progress) -> node_store.NodeStore:
    """Tabulate a grid's whole block, write it to ``path`` and serve the grid from it."""
    store = node_store.build_store(node_fn, STATE_STORE_I, STATE_STORE_J, STATE_STORE_K, width,
                                   workers, progress)
    node_store.write_store(path, store, key_fn())
    _STORES[path] = store
    return store


def build_back_store(workers: int | None = None, progress=None,
                     path: str = BACK_STORE_PATH) -> node_store.NodeStore:
    """Tabulate V1's whole back-pressure block on ``workers`` processes and serve the grid from it
    (``tools/build_liquid_state_store.py``); three speciations a node."""
    return _build(back_pressure_node_values, back_store_key, path, 4, workers, progress)


def _node(i: int, j: int, k: int) -> tuple:
    """One grid node: from the store when it holds it, else tabulated on first use."""
    key = (i, j, k)
    node = _NODES.get(key)
    if node is None:
        store = _store(BACK_STORE_PATH, back_store_key)
        node = store.get(i, j, k) if store else None
        if node is None or node[0] != node[0]:       # unstored, or stored as not computable
            node = back_pressure_node_values(i, j, k)
        _NODES[key] = node
    return node


def state_node_values(i: int, j: int, k: int) -> tuple:
    """One liquid-state node computed: the logarithms of the two pressures [Pa] and of the water
    activity [-], from one speciation. What the lazy path tabulates and the store holds."""
    vals = _liquid_state(N_FLOOR * GRID_RATIO ** i, C_FLOOR * GRID_RATIO ** j, k * GRID_DT)
    return tuple(math.log(max(v, _LOG_FLOOR)) for v in vals)


def state_store_key() -> str:
    """The SHA-256 of everything a stored node depends on: the property modules, the node's own
    code and the grid's spacing and block. Editing a docstring elsewhere keeps the store."""
    h = hashlib.sha256()
    here = os.path.dirname(os.path.abspath(__file__))
    for name in _STORE_SOURCES:
        with open(os.path.join(here, name), "rb") as f:
            h.update(f.read())
    for fn in (_liquid_state, state_node_values):
        h.update(inspect.getsource(fn).encode())
    h.update(repr((GRID_RATIO, GRID_DT, N_FLOOR, C_FLOOR, _LOG_FLOOR, STATE_STORE_I,
                   STATE_STORE_J, STATE_STORE_K)).encode())
    return h.hexdigest()


def build_state_store(workers: int | None = None, progress=None,
                      path: str = STATE_STORE_PATH) -> node_store.NodeStore:
    """Tabulate the whole liquid-state block on ``workers`` processes, write it to ``path`` and
    serve the grid from it. Once per model change, ahead of any exercise (``tools/
    build_liquid_state_store.py``); about half an hour on twenty cores."""
    return _build(state_node_values, state_store_key, path, 3, workers, progress)


def _state_node(i: int, j: int, k: int) -> tuple:
    """One liquid-state node: from the store when it holds it, else tabulated on first use."""
    key = (i, j, k)
    node = _STATE_NODES.get(key)
    if node is None:
        store = _store(STATE_STORE_PATH, state_store_key)
        node = store.get(i, j, k) if store else None
        if node is None or node[0] != node[0]:       # unstored, or stored as not computable
            node = state_node_values(i, j, k)
        _STATE_NODES[key] = node
    return node


def _grid_pressure(w: dict, t_k: float, node=_node, width: int = 4) -> tuple:
    """The trilinear interpolation of a grid in (ln m_N, ln m_C, T), on the logarithms: V1's
    unless ``node`` names the liquid-state grid, whose nodes carry ``width`` = 3 values."""
    n_tot, c_tot = molalities(w)
    t_k = min(max(t_k, T_SPEC_LO_K), T_SPEC_HI_K)
    fi, fj, fk = math.log(n_tot / N_FLOOR) / _LN_R, math.log(c_tot / C_FLOOR) / _LN_R, t_k / GRID_DT
    i0, j0, k0 = int(math.floor(fi)), int(math.floor(fj)), int(math.floor(fk))
    di, dj, dk = fi - i0, fj - j0, fk - k0
    out = [0.0] * width
    for a, wa in ((i0, 1.0 - di), (i0 + 1, di)):
        for b, wb in ((j0, 1.0 - dj), (j0 + 1, dj)):
            for c, wc in ((k0, 1.0 - dk), (k0 + 1, dk)):
                wt = wa * wb * wc
                if wt == 0.0:
                    continue
                vals = node(a, b, c)
                for n in range(width):
                    out[n] += wt * vals[n]
    return tuple(math.exp(v) for v in out)


def heat_of_absorption_j_mol(w: dict, t_c: float) -> tuple[float, float]:
    """(NH3, CO2) differential heat released per mol a liquid of composition ``w`` takes up
    [J/mol].

    Process utility
    ---------------
    What warms a wash as it absorbs, and so what an absorber's energy balance charges for the
    gas it takes in: NH3 31-36 and CO2 80-99 kJ/mol over the 322C001 liquor. Held 1 K inside the
    speciation's range so the difference never straddles its flat edge.

    Equation
    --------
        dH_i = -R . (ln p_i(T + 1) - ln p_i(T - 1)) / (1/(T + 1) - 1/(T - 1))
    """
    return _heats(w, t_c, _node, 4)


def liquor_heat_of_absorption_j_mol(w: dict, t_c: float) -> tuple[float, float]:
    """`heat_of_absorption_j_mol` read off the liquid-state grid [J/mol]: the same pressures at
    the same nodes, so the same heats to the bit, without tabulating the slopes a liquor's heat
    does not use (three speciations a node on V1's grid, one here).

    Process utility
    ---------------
    What a carbamate liquor condensing in HV-322604's outlet line releases per mol it takes up.
    """
    return _heats(w, t_c, _state_node, 3)


def _heats(w: dict, t_c: float, node, width: int) -> tuple[float, float]:
    """The heats of absorption on the grid ``node`` names (`heat_of_absorption_j_mol`)."""
    t_k = min(max(t_c + 273.15, T_SPEC_LO_K + 1.0), T_SPEC_HI_K - 1.0)
    lo = _grid_pressure(w, t_k - 1.0, node, width)
    hi = _grid_pressure(w, t_k + 1.0, node, width)
    x = 1.0 / (t_k + 1.0) - 1.0 / (t_k - 1.0)
    return tuple(-R * (math.log(hi[i]) - math.log(lo[i])) / x for i in (0, 1))


def back_pressure(w: dict, t_c: float) -> tuple[float, float, float, float]:
    """(p_NH3, p_CO2, dp_NH3/dx_NH3, dp_CO2/dx_CO2) [Pa] over an ammonia-water liquid.

    Process utility
    ---------------
    The equilibrium an absorber bed works against: the pressure fixes the gas composition the
    bed can approach, the slope fixes its absorption factor. Beyond 10-100 C the pressures carry
    on along van 't Hoff at the edge's heat of absorption: held flat instead, a cooling-loss dump
    that took the liquor to 150 C kept a 100 C liquor's back-pressure, and the column went on
    absorbing 80 % of the loop's gas while it boiled.
    """
    t_k = t_c + 273.15
    if T_SPEC_LO_K <= t_k <= T_SPEC_HI_K:
        return _grid_pressure(w, t_k)
    t_e = T_SPEC_HI_K if t_k > T_SPEC_HI_K else T_SPEC_LO_K
    edge = _grid_pressure(w, t_e)
    dh_n, dh_c = heat_of_absorption_j_mol(w, t_e - 273.15)
    f_n = math.exp(-dh_n / R * (1.0 / t_k - 1.0 / t_e))
    f_c = math.exp(-dh_c / R * (1.0 / t_k - 1.0 / t_e))
    return edge[0] * f_n, edge[1] * f_c, edge[2] * f_n, edge[3] * f_c


def liquid_state(w: dict, t_c: float) -> tuple[float, float, float]:
    """(p_NH3 [Pa], p_CO2 [Pa], a_H2O [-]) of an ammonia-water liquid of mass fractions ``w``.

    Process utility
    ---------------
    What a liquor holds back, water included: p_H2O = a_H2O . psat(T). A dilute wash's water is
    near 1; the concentrated ammonium-carbamate liquor a cooling-loss purge condenses in
    HV-322604's outlet line holds its water at 0.2 to 0.5, so it condenses tens of kelvin above
    water's own dew point.

    Equations
    ---------
        p_i   = H_i(T) . x_i(aq) . gamma_i(aq),   a_H2O = x_H2O . gamma_H2O
        beyond 10-100 C:  ln p_i = ln p_i,edge - dH_i / R . (1/T - 1/T_edge),  a_H2O held
    """
    t_k = t_c + 273.15
    if T_SPEC_LO_K <= t_k <= T_SPEC_HI_K:
        return _grid_pressure(w, t_k, _state_node, 3)
    t_e = T_SPEC_HI_K if t_k > T_SPEC_HI_K else T_SPEC_LO_K
    p_n, p_c, a_w = _grid_pressure(w, t_e, _state_node, 3)
    dh_n, dh_c = liquor_heat_of_absorption_j_mol(w, t_e - 273.15)
    return (p_n * math.exp(-dh_n / R * (1.0 / t_k - 1.0 / t_e)),
            p_c * math.exp(-dh_c / R * (1.0 / t_k - 1.0 / t_e)), a_w)
