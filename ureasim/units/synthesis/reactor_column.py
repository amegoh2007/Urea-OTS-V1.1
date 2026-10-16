"""322R001's axial march — the reaction integrated up the column's own liquid volume.

What this models
----------------
The inside of the urea reactor, as a plug of liquid rising 25 m through eleven sieve trays
over about three quarters of an hour. It is not an exchanger and it is not a stirred tank:
nothing is added and nothing is removed between the bottom nozzle and the overflow lip, so
the only variables are how hot the liquid is, how concentrated it is, and how long it stays.

The plug is divided into four nodes at the four thermowell elevations, because those are the
only places the plant can actually tell you the temperature. Each node runs the reaction at
its own temperature over its own residence time, and hands the depleted composition up to the
next one. That is what gives an axial profile at all — the driving force falls as the plug
rises, which a single lumped conversion has no way to represent.

What is here and what is next door
-----------------------------------
`thermo.kinetics` owns the rate laws and the reaction enthalpies: they are chemistry and two
other units on this plant run the same reactions backwards. This module owns everything that
needs a vessel — the wetted volume of a node, the residence time that follows from it, the
equilibrium extent at a live composition, and the two back-solves that tie the whole thing to
the plant's published design point.

`reactor.py` next door owns the streams: which split, which analyser, which tag.

What this replaced in V1
------------------------
Until V1's Phase 3 the extent was `XI_UREA_DES . s . cf(L, W, T)` — the design extent times
the CO2 load ratio times a dimensionless separable correlation renormalised to return exactly
1.0 at design. Reaction extent was therefore independent of residence time, of holdup volume
and of concentration except through two feed RATIOS, and biuret — the plant's principal
product-quality specification — was `XI_BIU_DES . s`, with no temperature dependence at all.
A reactor could not be made to produce a quality excursion by running it hot.

The superseded correlation is NOT ported. It is unreachable from V1's engine: `inoue_kanai_X`,
`conversion_factor`, `t_opt_c`, `f_T_parabola` and `react_couple` have no live call site left
in `main.py`, and neither do the four coefficients they were fitted with (a = 3.6180,
b = 0.85, k = 0.0015 /C2, Topt in [185, 195] C). Two things survive it and are carried in
`data.unit_322r001`: `X_INF`, the 0.9140 conversion ceiling, which the equilibrium constant
below is anchored on, and `X_DES`, the published 0.543 per-pass conversion.

Activity basis — stated, not hidden
------------------------------------
This march uses CONCENTRATIONS, not activities. The Extended UNIQUAC service refuses the HP
loop and is right to: finding G-VLE-3 measured the 322E003 feed at 869 mol per kg of water
against a 16.0 top node on the loading grid, so asking it for an activity coefficient at
183 C and 140 bar a returns a clamped edge lookup wearing a thermodynamic name. Concentrations
are a real limitation and this is the right place for an HP activity package when one exists.
It does not weaken what the march is for: temperature, concentration, holdup volume and
residence time drive the extent, where previously none of them did.

Sources
-------
Ported from V1 ``backend/reactor.py``, the Phase 3 (report C-1 / C-2) and report A-8 blocks.
The licensor's account of where the carbamate heat is released is
``References/322R001 Description.md`` section 4; the axial profile is validated against
``References/Urea_NormalOp_29-06-2025_Trends.md``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ureasim.thermo.kinetics import (
    CARBAMATE_DH_JMOL,
    DEHYDRATION_DH_JMOL,
    biuret_k_m3_kmol_h,
    dehydration_k_per_h,
    urea_keq_overall,
)

#: Iterations of the equilibrium-extent bisection. The bracket is the full stoichiometric
#: range, so 80 halvings resolve it to 2^-80 of that range — far below any float it is
#: compared against. Fixed rather than convergence-tested for the reason every solver in this
#: engine is: a simulator tick must never miss its deadline.
EQUILIBRIUM_ITERS = 80

#: Ceiling on the Damkohler group k2.tau inside one node [-]. exp(-700) is the smallest
#: non-zero double, so this is the point past which the node is simply AT equilibrium; the
#: clamp exists to keep `math.exp` from underflowing to a domain error rather than to bound
#: any physics. Source: V1 `reactor.py`.
DAMKOHLER_MAX = 700.0


@dataclass(frozen=True)
class ColumnKinetics:
    """The four numbers this vessel's rate laws are calibrated with.

    V1 held these as module globals that `calibrate_kinetics` assigned with a `global`
    statement, which meant the rate laws could be called before calibration and would either
    raise or silently return zero. Here they travel together in one frozen object that cannot
    exist half-filled, and every function that needs them takes it as an argument. The
    arithmetic is unchanged; what changes is that an uncalibrated call is now impossible to
    write rather than merely discouraged.

    None of the four is a free parameter fitted to shape a response. Two are back-solved from
    one plant design point each, exactly as the Phase 2 valve coefficients were, because no
    vendor kinetics exist for this reactor; the other two are the reference state the first
    two are quoted at. Every temperature, concentration and residence-time response of the
    model follows from the rate laws themselves once these are fixed.
    """

    #: Dehydration pre-exponential [1/h]. Back-solved so the march reproduces the PFD urea
    #: extent at the design state. Lands near 4e12, which is an ordinary liquid-phase value:
    #: at 107.8 kJ/mol and 453 K the Arrhenius factor is exp(-28.6) = 3.7e-13.
    a2_pre_per_h: float
    #: Overall equilibrium constant [m3/kmol] at ``t_ref_k``. Anchored so the EQUILIBRIUM
    #: conversion at the design state is the plant's X_INF ceiling.
    keq_ov_ref: float
    #: Temperature the equilibrium constant is quoted at [K] — the design node-mean.
    t_ref_k: float
    #: Biuret pre-exponential [m3/(kmol.h)]. Back-solved against the PFD biuret extent.
    biuret_a: float


# ======================================================================================
# Geometry: what volume the reaction actually has
# ======================================================================================

def node_liquid_volumes(zeta_nodes, area_m2: float, h_span_m: float,
                        level_frac: float) -> list[float]:
    """Wetted liquid volume of each node [m3], truncated at the live level.

    Process utility
    ---------------
    This is what makes residence time a plant variable rather than a constant. A level drop
    shortens the column the plug actually flows through, and nodes above the surface
    contribute nothing at all — so losing level in this reactor is losing conversion, promptly
    and proportionally, and an operator who drains it to protect the stripper pays for it in
    the product. Nothing about that is visible in a model with a fixed residence time.

    Equation
    --------
        V_n = max( min(zeta_n, L) - min(zeta_{n-1}, L), 0 ) . H_span . A_cs

    with L the level as a fraction of the span. The two `min` calls clip the node's own slice
    at the surface, so a partly-submerged node contributes only its wetted part.
    """
    vols = []
    prev = 0.0
    for z in zeta_nodes:
        lo = min(prev, level_frac)
        hi = min(z, level_frac)
        vols.append(max(hi - lo, 0.0) * h_span_m * area_m2)
        prev = z
    return vols


# ======================================================================================
# The equilibrium the march is pulled toward
# ======================================================================================

def equilibrium_extent(n_kmolh: dict, vdot_m3h: float, keq_overall_value: float) -> float:
    """Extent [kmol/h] at which the OVERALL reaction is at equilibrium for this composition.

    Process utility
    ---------------
    The target the reaction is running toward at this node's temperature — how far it COULD
    go, before any question of whether it has time to. Signed, and the sign is the teaching
    point: a stream that is already past equilibrium returns a NEGATIVE extent and the
    reaction runs backwards. That is what makes an over-hot reactor LOSE conversion instead of
    quietly making more, and it comes out of the exothermic overall enthalpy rather than out
    of a fitted parabola.

    Equation
    --------
    Solves, for the extent xi,

        C_carb - C_urea . C_H2O / ( Kov . C_NH3^2 ) = 0

    with every concentration written as (moles + nu.xi) / Vdot. Bisection on the bracket the
    stoichiometry allows:

        upper = min(CO2, NH3/2)     forward, until a reagent runs out
        lower = -min(Urea, H2O)     reverse, until a product runs out

    both pulled in by one part in 1e12 so the concentrations at the bracket ends stay finite.

    Two early returns, and neither is an approximation. If the function is already non-positive
    at the lower bracket the stream is past equilibrium beyond what the products can supply, so
    the reverse bound IS the answer; if it is still positive at the upper bracket the
    stoichiometry binds before equilibrium does, so the forward bound is. Bisection is only
    entered when a root is genuinely enclosed.
    """
    co2 = max(n_kmolh.get("CO2", 0.0), 0.0)
    nh3 = max(n_kmolh.get("NH3", 0.0), 0.0)
    urea = max(n_kmolh.get("Urea", 0.0), 0.0)
    h2o = max(n_kmolh.get("H2O", 0.0), 0.0)
    # No flow means no volume to react in, and a collapsed equilibrium constant means the
    # quotient below is meaningless rather than large. Either way the honest answer is zero.
    if vdot_m3h <= 1e-12 or keq_overall_value <= 1e-30:
        return 0.0

    def residual(xi: float) -> float:
        """Carbamate concentration minus what equilibrium would leave, at extent ``xi``."""
        c_carb = (co2 - xi) / vdot_m3h
        c_nh3 = (nh3 - 2.0 * xi) / vdot_m3h
        c_urea = (urea + xi) / vdot_m3h
        c_h2o = (h2o + xi) / vdot_m3h
        # Ammonia exhausted: the quotient diverges, so report a large negative rather than
        # dividing. The magnitude is arbitrary; only its sign is read, by the bisection.
        if c_nh3 <= 1e-12:
            return -1.0e30
        return c_carb - c_urea * c_h2o / (keq_overall_value * c_nh3 * c_nh3)

    hi = min(co2, 0.5 * nh3) * (1.0 - 1.0e-12)
    lo = -min(urea, h2o) * (1.0 - 1.0e-12)
    if residual(lo) <= 0.0:
        return lo                     # already past equilibrium in the reverse direction
    if residual(hi) >= 0.0:
        return hi                     # stoichiometry binds before equilibrium does
    for _ in range(EQUILIBRIUM_ITERS):
        mid = 0.5 * (lo + hi)
        if residual(mid) > 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ======================================================================================
# The march itself
# ======================================================================================

def urea_extent_pfr(feed_kmolh: dict, t_nodes_c, zeta_nodes, area_m2: float,
                    h_span_m: float, level_frac: float, vdot_m3h: float,
                    kinetics: ColumnKinetics) -> tuple[float, list[float]]:
    """Per-pass urea extent [kmol/h] by marching the liquid plug up the column.

    Process utility
    ---------------
    The plant's output. Everything downstream of this vessel is sized on it, and every
    operating decision an operator makes about the synthesis loop — the N/C ratio, the reactor
    level, the feed rate — reaches the product through this one number.

    Returns the total and the per-node breakdown, because the node-by-node extents are also
    the node-by-node heat sinks and the energy balance needs them separately.

    Equation
    --------
        dN_i/dz = nu_i . r2 . A_cs         integrated node by node, T from that node's state

        r2 = k2(T) . ( C_carb - C_urea . C_H2O / ( Kov(T) . C_NH3^2 ) )      kmol/(m3.h)

    Why the node is integrated EXACTLY rather than as r2.V_n
    ---------------------------------------------------------
    The rate is linear in its own driving force, so within a node the approach is first order,

        dxi/dt = k2 . (xi_eq - xi)   ->   dxi = xi_eq . ( 1 - exp(-k2 . tau_n) )

    and that closed form is used. Multiplying the rate by the node volume instead lets a large
    k2 overshoot the equilibrium inside one node and reverse in the next, which makes the total
    extent non-monotone in the pre-exponential and leaves the design back-solve with nothing to
    converge on. This is a numerical point, not a physical one, but it decides whether the
    calibration exists.

    Feasibility clamp
    -----------------
    Each node's step is bounded by what that node's stream actually holds — forward by the CO2
    and half the ammonia, reverse by the urea and the water. Non-binding anywhere near design;
    it binds under reagent starvation, where an unbounded step would take a component negative
    and put phantom mass into the stripper feed.
    """
    if vdot_m3h <= 1e-9:
        return 0.0, [0.0] * len(zeta_nodes)
    # Local copy: the march depletes the composition as the plug rises, and the caller's feed
    # vector is also the reactor's published feed.
    n = {k: float(v) for k, v in feed_kmolh.items()}
    vols = node_liquid_volumes(zeta_nodes, area_m2, h_span_m, level_frac)
    xi_total = 0.0
    per_node = []
    for v_n, t_c in zip(vols, t_nodes_c):
        if v_n <= 0.0:                                 # node is above the liquid surface
            per_node.append(0.0)
            continue
        tau_n = v_n / vdot_m3h                         # h, this node's own residence time
        xi_eq = equilibrium_extent(
            n, vdot_m3h, urea_keq_overall(t_c, kinetics.keq_ov_ref, kinetics.t_ref_k))
        damkohler = dehydration_k_per_h(t_c, kinetics.a2_pre_per_h) * tau_n
        dxi = xi_eq * (1.0 - math.exp(-min(damkohler, DAMKOHLER_MAX)))
        if dxi > 0.0:
            dxi = min(dxi, n.get("CO2", 0.0), 0.5 * n.get("NH3", 0.0))
        else:
            dxi = max(dxi, -n.get("Urea", 0.0), -n.get("H2O", 0.0))
        n["CO2"] = n.get("CO2", 0.0) - dxi
        n["NH3"] = n.get("NH3", 0.0) - 2.0 * dxi
        n["Urea"] = n.get("Urea", 0.0) + dxi
        n["H2O"] = n.get("H2O", 0.0) + dxi
        xi_total += dxi
        per_node.append(dxi)
    return xi_total, per_node


def biuret_extent(t_nodes_c, zeta_nodes, area_m2: float, h_span_m: float, level_frac: float,
                  vdot_m3h: float, urea_kmolh: float, kinetics: ColumnKinetics) -> float:
    """Biuret extent [kmol/h] over the wetted column, 2 Urea -> Biuret + NH3.

    Process utility
    ---------------
    The product-quality specification, and the one number in this vessel that only ever gets
    worse. It is second order in urea concentration and Arrhenius in temperature, so the
    reactor makes more of it exactly when it is doing well — hot, converting, and full of
    urea. That trade-off is the operating lesson, and it is invisible in a model where biuret
    is a load-scaled constant.

    Equation
    --------
        r_biu = A . exp(-Ea/RT) . C_urea^2 ,   xi = sum over nodes of r_biu . V_n

    integrated as a plain rate times volume, unlike the urea march above: the driving force is
    a concentration rather than a distance from equilibrium, and the extent is four orders of
    magnitude below the urea inventory, so it does not deplete what it feeds on.

    The concentration basis is the urea ACTUALLY in the column — the feed urea plus what this
    pass just made — which the caller supplies. Scaling a design constant by load instead
    makes the concentration s/s = constant and the extent comes out load-invariant, i.e. still
    a frozen number wearing an Arrhenius coat.
    """
    if vdot_m3h <= 1e-9:
        return 0.0
    c_urea = max(urea_kmolh, 0.0) / vdot_m3h
    vols = node_liquid_volumes(zeta_nodes, area_m2, h_span_m, level_frac)
    xi = 0.0
    for v_n, t_c in zip(vols, t_nodes_c):
        if v_n <= 0.0:
            continue
        xi += biuret_k_m3_kmol_h(t_c, kinetics.biuret_a) * c_urea * c_urea * v_n
    return xi


# ======================================================================================
# The column exotherm as an energy quantity
# ======================================================================================
#
# V1's report A-8. The temperature rise used to be PRESCRIBED: 13.0 C times the per-pass
# conversion ratio, distributed over the nodes by a fitted Damkohler shape with a fitted decay
# constant. Nothing in that was energy, and the SIGN was wrong — a reactor making twice the
# urea got twice the temperature rise, when dehydration is endothermic and more urea means
# LESS net heat.

def carbamate_node_extents(xi_carb_total: float, node_volumes_m3) -> list[float]:
    """Distribute the carbamate-formation extent over the nodes [kmol/h each].

    Process utility
    ---------------
    Says WHERE the reactor gets hot, which is what the four thermowells actually measure and
    what an operator uses to tell a healthy column from one that is channelling or flooded.

    Why proportional to liquid volume
    ----------------------------------
    The licensor's own description, not a fit. `References/322R001 Description.md` section 4:
    a controlled amount of uncondensed NH3 and CO2 from 322E002 is allowed to enter the
    reactor, and as the endothermic reaction cools the liquid it induces further physical
    absorption and condensation of those gases from the bubbles, maintaining a steady, slightly
    rising profile. The release is therefore distributed up the whole column by gas-liquid mass
    transfer from rising bubbles — it is NOT a bottom-loaded exotherm.

    For a bubbling column the interfacial area per unit liquid volume is uniform, so absorption
    is taken proportional to each node's liquid volume. That introduces no fitted shape
    parameter at all, where the superseded Damkohler form needed one.

    `xi_carb_total` comes from the STREAM BALANCE — the free CO2 entering from 322E002 minus
    the CO2 leaving in the off-gas — so it stays consistent with the off-gas split instead of
    becoming a second, independent prediction of the same quantity that can disagree with it.
    """
    v_tot = sum(v for v in node_volumes_m3 if v > 0.0)
    if v_tot <= 0.0 or xi_carb_total <= 0.0:
        return [0.0] * len(node_volumes_m3)
    return [xi_carb_total * (max(v, 0.0) / v_tot) for v in node_volumes_m3]


def node_heat_kjh(per_node_carbamate, per_node_dehydration) -> list[float]:
    """Net heat released in each node [kJ/h].

    Process utility
    ---------------
    The reactor's only heat source and its only heat sink, in one line. There is no jacket and
    no coil: the 13 C the liquid gains between the inlet nozzle and the overflow is the
    arithmetic difference of these two terms, and nothing else on the plant can change it
    except by changing what arrives.

    Equation
    --------
        Q_n = xi_carb,n . 117 000  -  xi_dehyd,n . 15 500        [kJ/h]

    The signs are the physics and they OPPOSE: carbamate formation heats the column, urea
    dehydration cools it. A conversion excursion therefore moves the temperature the way the
    plant moves it.
    """
    return [c * (-CARBAMATE_DH_JMOL) - d * DEHYDRATION_DH_JMOL
            for c, d in zip(per_node_carbamate, per_node_dehydration)]


# ======================================================================================
# The seed profile
# ======================================================================================
#
# The energy balance has to be solved from somewhere, and where it is solved from is a
# residence-time approach with a first-order shape. That shape was once the model; it is now
# only a starting guess, and the joint solve below moves off it immediately.

def damkohler_g(zeta: float, beta: float) -> float:
    """Cumulative heat-release fraction below dimensionless elevation ``zeta`` [-].

        G(zeta) = 1 - exp(-beta . zeta)

    Monotone increasing with G(0) = 0, and deliberately UN-normalised: G(1) < 1, so the
    residual above the top thermowell is carried by the freeboard between it and the overflow
    lip. Normalising to G(1) = 1 would lift the interior probes about 0.1 C off the as-built
    residence-time profile. Source: V1 `reactor.py` damkohler_G.
    """
    return 1.0 - math.exp(-beta * zeta)


def node_profile_ss(t_feed_c: float, t_overflow_c: float, zeta_nodes, beta: float) -> list[float]:
    """Steady-state node temperatures on the residence-time shape [deg C].

        T_n = T_feed + (T_overflow - T_feed) . G(zeta_n)

    Used only to seed `thermal_kinetic_fixed_point`, and through it the equilibrium constant's
    reference temperature. The profile the plant actually runs is the fixed point's, not this.
    """
    dt = t_overflow_c - t_feed_c
    return [t_feed_c + dt * damkohler_g(z, beta) for z in zeta_nodes]


__all__ = [
    "EQUILIBRIUM_ITERS",
    "DAMKOHLER_MAX",
    "ColumnKinetics",
    "node_liquid_volumes",
    "equilibrium_extent",
    "urea_extent_pfr",
    "biuret_extent",
    "carbamate_node_extents",
    "node_heat_kjh",
    "damkohler_g",
    "node_profile_ss",
]
