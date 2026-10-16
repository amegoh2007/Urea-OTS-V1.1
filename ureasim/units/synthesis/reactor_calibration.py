"""322R001's two back-solves — tying the column march to the plant's published design point.

Why a reactor needs calibrating at all
---------------------------------------
No vendor kinetics exist for this vessel. The licensor sells a converged design, not a rate
law: the PFD says the reactor makes 1302.27 kmol/h of urea from a stated feed in a stated
volume at a stated temperature, and says nothing about the pre-exponential that would produce
it. So two numbers have to come from the plant, and this module is where they come from.

That is the same treatment the Phase 2 valve coefficients got, and it is bounded in the same
way: **one design point determines one parameter.** Two anchors, two unknowns. Everything else
in the model — the Arrhenius temperature response, the van 't Hoff shift of the equilibrium,
the concentration dependence, the residence-time scaling — is first-principles once these are
fixed, and none of it was tuned to make a response look right.

The two anchors, and which unknown each one fixes
--------------------------------------------------
    Kov_ref     <-  the conversion CEILING.  At X_INF the overall reaction is at equilibrium
                    by definition, so evaluating the equilibrium quotient at the composition
                    that ceiling implies gives the constant directly. No iteration.
    A2          <-  the design urea EXTENT.  Solved by bisection on the march, which is
                    monotone in A2, so the solve is robust.

Why the second solve is JOINT with the temperature profile
-----------------------------------------------------------
Because closing the energy balance means the reactor temperature is no longer imposed: the
node temperatures set the dehydration extents, the extents set the heat released, and the heat
released sets the node temperatures. A2 back-solved at a guessed profile is A2 at the wrong
temperatures. V1 measured exactly that when it first closed the loop — 1236 kmol/h against
1302.27, with the column settling at 184.42 C rather than 183.0 — and `thermal_kinetic_fixed_point`
is the fix: it solves the profile and A2 together against their two plant anchors,

    T_overflow == 183.0 C        (PFD)   ->  the axial profile
    xi_urea    == 1302.27 kmol/h (PFD)   ->  A2

Iterating that little system takes milliseconds. Settling the whole plant for each trial value
takes a quarter of an hour, which is why the calibration lives here and not in a boot settle.

Sources
-------
Ported from V1 ``backend/reactor.py``, `calibrate_kinetics` and `thermal_kinetic_fixed_point`,
with V1's ``main.py`` notes on which design vectors they are solved against.
"""

from __future__ import annotations

import math

from ureasim.thermo.kinetics import biuret_k_m3_kmol_h
from ureasim.units.synthesis.reactor_column import (
    ColumnKinetics,
    carbamate_node_extents,
    node_heat_kjh,
    node_liquid_volumes,
    urea_extent_pfr,
)

#: Bisection steps for the dehydration pre-exponential. Geometric, because the unknown is a
#: scale factor spanning decades rather than a bounded quantity.
A2_BISECT_ITERS = 500

#: Bracket for that bisection [1/h]. Thirty decades on purpose: at 107.8 kJ/mol and 453 K the
#: Arrhenius factor is exp(-28.6) = 3.7e-13, so a physically ordinary liquid-phase
#: pre-exponential lands near 1e12 and a bracket that merely looked generous would not hold it.
A2_BRACKET_LO = 1.0e-6
A2_BRACKET_HI = 1.0e30

#: Relative width at which the geometric bisection stops early, having run out of float.
A2_BISECT_TOL = 1.0e-14

#: Iterations of the joint profile / pre-exponential fixed point.
THERMAL_FIXED_POINT_ITERS = 400

#: Damping on the profile update [-]. The loop is stiff — an Arrhenius rate on top of an
#: equilibrium approach — and an undamped step oscillates instead of converging.
THERMAL_DAMPING = 0.5

#: Exponent on the pre-exponential correction [-]. Under-relaxed for the same reason: the
#: extent responds to A2 faster than linearly through the equilibrium approach, so applying
#: the full ratio overshoots.
A2_RELAXATION = 0.7


def calibrate_kinetics(feed_des_kmolh: dict, t_nodes_des_c, zeta_nodes, area_m2: float,
                       h_span_m: float, level_frac_des: float, vdot_des_m3h: float,
                       xi_urea_des: float, xi_biuret_des: float, x_ceiling: float,
                       urea_out_des_kmolh: float) -> ColumnKinetics:
    """Solve the equilibrium constant, the dehydration pre-exponential and the biuret one.

    Process utility
    ---------------
    Makes the model reproduce the plant it is a model of. Without this the reactor would
    produce whatever a textbook rate law says, which is not what this reactor produces, and
    every unit downstream of it would be fed the wrong stream from the first tick.

    The equilibrium constant, without iteration
    --------------------------------------------
    At the plant-anchored ceiling X_INF the overall reaction is AT equilibrium, by the
    definition of a ceiling. So the equilibrium quotient can be evaluated directly at the
    composition that ceiling implies:

        xi_eq   = X_inf . CO2_feed
        Kov_ref = C_urea . C_H2O / ( C_NH3^2 . C_carb )      all at feed + nu . xi_eq

    quoted at the design node-mean temperature, which is what `t_ref_k` carries. The two
    floors of 1e-12 are there because the ceiling is close enough to complete conversion that
    the carbamate and ammonia concentrations it implies are small; they guard the division,
    and at X_inf = 0.914 against N/C = 3.07 neither is anywhere near binding.

    The dehydration pre-exponential, by bisection
    ----------------------------------------------
    The march is monotone in A2 — more rate constant, more extent, always — so bisection
    cannot land on the wrong root and there is no root to be wrong about. Geometric, because
    the bracket spans thirty decades.

    The biuret pre-exponential, in closed form
    -------------------------------------------
    The biuret rate is linear in its own pre-exponential and does not deplete what it feeds
    on, so its design extent divides straight out: no iteration, one design point, one
    parameter, the same treatment as the other two. The concentration basis is the design
    OUTLET urea, because that is what is in the column at the design state.
    """
    co2_0 = feed_des_kmolh.get("CO2", 0.0)
    urea_0 = feed_des_kmolh.get("Urea", 0.0)
    h2o_0 = feed_des_kmolh.get("H2O", 0.0)
    nh3_0 = feed_des_kmolh.get("NH3", 0.0)

    # ---- the equilibrium constant, at the ceiling composition -------------------------
    t_bulk = sum(t_nodes_des_c) / len(t_nodes_des_c)
    t_ref_k = t_bulk + 273.15
    xi_eq = x_ceiling * co2_0
    c_carb_eq = max(co2_0 - xi_eq, 1e-12) / vdot_des_m3h
    c_urea_eq = (urea_0 + xi_eq) / vdot_des_m3h
    c_h2o_eq = (h2o_0 + xi_eq) / vdot_des_m3h
    c_nh3_eq = max(nh3_0 - 2.0 * xi_eq, 1e-12) / vdot_des_m3h
    keq_ov_ref = c_urea_eq * c_h2o_eq / (c_nh3_eq * c_nh3_eq * c_carb_eq)

    # ---- the dehydration pre-exponential, against the design extent --------------------
    def march(a2_pre: float) -> float:
        """Total urea extent the design march produces at this pre-exponential [kmol/h]."""
        trial = ColumnKinetics(a2_pre_per_h=a2_pre, keq_ov_ref=keq_ov_ref,
                               t_ref_k=t_ref_k, biuret_a=0.0)
        xi, _ = urea_extent_pfr(feed_des_kmolh, t_nodes_des_c, zeta_nodes, area_m2,
                                h_span_m, level_frac_des, vdot_des_m3h, trial)
        return xi

    lo, hi = A2_BRACKET_LO, A2_BRACKET_HI
    for _ in range(A2_BISECT_ITERS):
        mid = math.sqrt(lo * hi)
        if march(mid) < xi_urea_des:
            lo = mid
        else:
            hi = mid
        if hi / lo < 1.0 + A2_BISECT_TOL:
            break
    a2_pre = math.sqrt(lo * hi)

    # ---- the biuret pre-exponential, in closed form ------------------------------------
    c_urea = max(urea_out_des_kmolh, 0.0) / vdot_des_m3h
    vols = node_liquid_volumes(zeta_nodes, area_m2, h_span_m, level_frac_des)
    denominator = sum(biuret_k_m3_kmol_h(t, 1.0) * c_urea * c_urea * v
                      for v, t in zip(vols, t_nodes_des_c) if v > 0.0)
    biuret_a = (xi_biuret_des / denominator) if denominator > 0.0 else 0.0

    return ColumnKinetics(a2_pre_per_h=a2_pre, keq_ov_ref=keq_ov_ref,
                          t_ref_k=t_ref_k, biuret_a=biuret_a)


def thermal_kinetic_fixed_point(feed_kmolh: dict, zeta_nodes, area_m2: float, h_span_m: float,
                                level_frac: float, vdot_m3h: float, t_feed_c: float,
                                t_overflow_des_c: float, xi_carbamate: float,
                                m_overflow_kgh: float, cp_melt: float, xi_urea_des: float,
                                kinetics: ColumnKinetics,
                                iters: int = THERMAL_FIXED_POINT_ITERS
                                ) -> tuple[list[float], ColumnKinetics]:
    """Solve the axial profile and the pre-exponential together. Returns both.

    Process utility
    ---------------
    Produces the temperature profile the plant actually runs at, which is what the four
    thermowells are compared against and what the design seed of every dynamic state is taken
    from. It is also the only place the two design anchors are reconciled: a profile that
    reaches 183 C at the lip AND a march that makes 1302.27 kmol/h getting there.

    Equation
    --------
    Each sweep marches the reaction at the current profile, converts the per-node heat into a
    cumulative temperature rise, and corrects the pre-exponential toward the design extent:

        xi_n            = urea_extent_pfr(T)                    [per node]
        Q_n             = xi_carb,n . 117 000 - xi_n . 15 500   [kJ/h]
        T_n             = T_{n-1} + Q_n / (m_overflow . cp)     [T_0 = T_feed]
        T <- 0.5 . T_new + 0.5 . T_old                          [damped]
        A2 <- A2 . (xi_des / xi)^0.7                            [under-relaxed]

    Fixed sweep count, no convergence test, for the same reason every solver in this engine
    has one: the cost must be bounded. It runs once at import, so 400 sweeps is free.

    Why the carbamate extents are computed ONCE
    --------------------------------------------
    `xi_carbamate` is a stream balance, not a kinetic prediction — the free CO2 arriving from
    322E002 minus the CO2 leaving in the off-gas — so it does not move as the profile does,
    and neither does its distribution over the nodes.

    Why the seed here is LINEAR
    ----------------------------
    Deliberately not the residence-time shape the equilibrium constant's reference temperature
    was taken from. Starting the fixed point somewhere other than its own answer is the point:
    a seed that already carried the old fitted shape would make it harder to see whether the
    energy balance had moved off it. It converges to the same profile from either.

    Which design vectors this is solved on, and which it is NOT
    ------------------------------------------------------------
    The PFD design vectors, and deliberately not a live capture from a settled plant. V1 tried
    both live references and both are the wrong operating point: the warm-up settle sits on an
    attractor whose carbamate balance reads 253 kmol/h against the 279 the runtime produces
    (the melt heat capacity came out 3.20 and the column ran away to 184.3 C), and a post-reset
    capture is one tick off the seed, which is the seed. On the design vectors every input is
    source-anchored and the profile lands on 183.0 exactly.
    """
    vols = node_liquid_volumes(zeta_nodes, area_m2, h_span_m, level_frac)
    mcp = max(m_overflow_kgh * cp_melt, 1e-9)                # kJ per deg C per hour of flow
    carbamate = carbamate_node_extents(xi_carbamate, vols)
    n_nodes = len(zeta_nodes)
    t_nodes = [t_feed_c + (t_overflow_des_c - t_feed_c) * (i + 1) / n_nodes
               for i in range(n_nodes)]
    a2_pre = kinetics.a2_pre_per_h
    for _ in range(iters):
        trial = ColumnKinetics(a2_pre_per_h=a2_pre, keq_ov_ref=kinetics.keq_ov_ref,
                               t_ref_k=kinetics.t_ref_k, biuret_a=kinetics.biuret_a)
        xi, per_node = urea_extent_pfr(feed_kmolh, t_nodes, zeta_nodes, area_m2, h_span_m,
                                       level_frac, vdot_m3h, trial)
        previous, updated = t_feed_c, []
        for q in node_heat_kjh(carbamate, per_node):
            previous = previous + q / mcp
            updated.append(previous)
        t_nodes = [THERMAL_DAMPING * new + (1.0 - THERMAL_DAMPING) * old
                   for new, old in zip(updated, t_nodes)]
        if xi > 0.0:
            a2_pre *= (xi_urea_des / xi) ** A2_RELAXATION
    return t_nodes, ColumnKinetics(a2_pre_per_h=a2_pre, keq_ov_ref=kinetics.keq_ov_ref,
                                   t_ref_k=kinetics.t_ref_k, biuret_a=kinetics.biuret_a)


__all__ = [
    "A2_BISECT_ITERS",
    "A2_BRACKET_LO",
    "A2_BRACKET_HI",
    "A2_BISECT_TOL",
    "THERMAL_FIXED_POINT_ITERS",
    "THERMAL_DAMPING",
    "A2_RELAXATION",
    "calibrate_kinetics",
    "thermal_kinetic_fixed_point",
]
