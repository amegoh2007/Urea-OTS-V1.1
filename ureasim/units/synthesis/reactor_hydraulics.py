"""322R001's inventory and its discharge — level, the overflow funnel, HV-322605, wall loss.

What this models
----------------
Everything about the reactor that is not the reaction: how much liquid is in it, how high
that reads on LT-322504, how it gets out, and what happens to its temperature when nothing is
flowing. These are the right-hand sides of the vessel's dynamic states; the engine owns the
integration, as it does for every other holdup on the plant.

Why the level is a state and not a pass-through
------------------------------------------------
The reactor is a true liquid holdup with an operator valve on its outlet, so its inlet and its
outlet are independent and the difference accumulates. Two mechanisms make that matter:

* **The funnel.** The liquid leaves over the lip of an internal overflow funnel, 0.7 m below
  the normal level, and down a 305 mm downcomer to HV-322605. Below that lip the vessel
  CANNOT discharge, so a feed trip parks the level at the lip instead of draining the reactor.
* **Thermal contraction.** Level is volume, and volume is mass over density. A cooling melt
  contracts, so the same holdup reads a lower level — which is what takes a stagnant reactor
  below the funnel lip once the exotherm stops.

Both are zero-effect at the design state, deliberately: the published design point must be
reproduced bit-exactly, so a mechanism may only act on a departure from it.

What is NOT here
----------------
The Euler integration itself, the recycle-inventory lag on the inflow, the forward-carbamate
pulse from the ejector, the flood carryover to 322E003, and the LT-322504 narrow-band display
scaling. Those are engine wiring over these right-hand sides and they belong to Phase 5, the
same way the ejector's instrument lag does. V1 keeps the same division: the rate laws are in
`reactor.py`, the Euler steps are in `step_sim`.

Sources
-------
Ported from V1 ``backend/reactor.py``, the Fix-2 stagnant-flow block and the report A-12
outlet-line block. Geometry from the datasheets named in `data.unit_322r001`.
"""

from __future__ import annotations

import math

from ureasim.data.unit_322r001 import (
    HV322605_KV_TABLE,
    MELT_BETA_THERMAL,
    MELT_RHO_REF,
    REACTOR_T_DES_C,
    T_AMBIENT_C,
    TAU_LOSS_S,
)

#: Floor on the melt density [kg/m3]. Guards the level calculation against a division by a
#: density the linear expansion law has driven to zero, which needs a temperature about
#: 1400 C above the reference and therefore never happens — but the level is a divisor and a
#: divisor gets a floor. Source: V1 `reactor.py` `liquid_density`.
RHO_FLOOR = 1.0e-3

#: Floor on the vessel cross-section [m2] used by the level calculation, for the same reason.
AREA_FLOOR = 1.0e-6


# ======================================================================================
# The melt
# ======================================================================================

def melt_density(temperature_c: float, rho_ref: float = MELT_RHO_REF,
                 beta: float = MELT_BETA_THERMAL,
                 t_ref_c: float = REACTOR_T_DES_C) -> float:
    """Density of the carbamate / urea / ammonia melt [kg/m3].

    Process utility
    ---------------
    Converts the reactor's conserved holdup MASS into the level an operator sees, and the
    coupling runs the way that surprises people: cooling RAISES the density, so a fixed mass
    occupies less volume and the level FALLS. A reactor that loses its exotherm therefore
    loses indicated level without losing an ounce of inventory, and the level will keep
    falling as it cools even with the discharge valve shut.

    It also converts the design volumetric throughput into the mass the weir passes.

    Equation
    --------
        rho(T) = rho_ref . [ 1 - beta . (T - T_ref) ]

    A linear departure about the design bulk state, floored strictly positive. Source: V1
    `reactor.py` `liquid_density`, whose reference is the 990 kg/m3 urea-solution figure the
    PFD carries.
    """
    return max(rho_ref * (1.0 - beta * (temperature_c - t_ref_c)), RHO_FLOOR)


def level_from_holdup(m_liquid_kg: float, t_bulk_c: float, area_m2: float) -> float:
    """Liquid level [m] from the conserved holdup mass and its temperature.

    Process utility
    ---------------
    LT-322504's physical head. The level is a state of the MASS, which is what the vessel
    actually conserves — not a pass-through of the inlet flow, which is what a model without a
    holdup would make it. That is the difference between a reactor an operator can flood by
    throttling HV-322605 and one that simply passes whatever arrives.

    Equation
    --------
        level = V / A = m_liquid / ( rho(T_bulk) . A_cs )
    """
    return m_liquid_kg / (melt_density(t_bulk_c) * max(area_m2, AREA_FLOOR))


# ======================================================================================
# The column energy balance, per node
# ======================================================================================

def node_dtdt(t_node_c: float, t_below_c: float, dt_reaction_c: float, tau_node_s: float,
              flow_frac: float, t_ambient_c: float = T_AMBIENT_C,
              tau_loss_s: float = TAU_LOSS_S) -> float:
    """Rate of change of one node's temperature [deg C/s].

    Process utility
    ---------------
    The four thermowells an operator watches to know what the reactor is doing. Two terms,
    and which one dominates says what state the vessel is in.

    Equation
    --------
        dT_n/dt = [ (T_{n-1} - T_n) + dT_rxn,n ] / tau_n        flow-driven
                  - (1 - flow_frac) . (T_n - T_amb) / tau_loss   wall loss, GATED

    The first term is the lumped node energy balance

        rho_n V_n c_p dT_n/dt = m_dot c_p (T_{n-1} - T_n) + Q_n - U_n A_n (T_n - T_amb)

    divided through by m_dot . c_p, with tau_n = rho_n V_n / m_dot. `dt_reaction_c` is
    Q_n / (m_dot . c_p) — real energy from `reactor_column.node_heat_kjh`, not a shape
    function times a prescribed column rise.

    Why the wall loss is gated on flow
    -----------------------------------
    `flow_frac` is the throughput over its design value, clipped to [0, 1], so the gate
    (1 - flow_frac) is EXACTLY zero at design flow and the as-built profile is bit-exact —
    the exotherm anchor already nets out the design-flow wall loss, and counting it twice
    would cool the column below the PFD. The gate opens to full strength as flow collapses, so
    a stagnant reactor, whose flow term has gone to zero with it, relaxes toward ambient over
    six hours instead of freezing at whatever temperature it stopped at. A trainee who trips
    the feed and walks away should come back to a cold reactor.

    Zero-flow safe: an infinite residence time zeroes the flow term rather than dividing by
    zero, which is how the caller signals no flow.

    The gate is written as `min(max(x, 0), 1)` rather than through the engine's `clamp`
    because the two disagree on NaN — V1's form propagates it, `clamp` would return 1.0 and
    silently apply full wall loss to a broken temperature. Source: V1 `reactor.py` node_dTdt.
    """
    if math.isfinite(tau_node_s) and tau_node_s > 0.0:
        flow_term = ((t_below_c - t_node_c) + dt_reaction_c) / tau_node_s
    else:
        flow_term = 0.0
    gate = min(max(1.0 - flow_frac, 0.0), 1.0)
    loss_term = gate * (t_node_c - t_ambient_c) / tau_loss_s
    return flow_term - loss_term


# ======================================================================================
# The discharge: the funnel lip and HV-322605
# ======================================================================================

def weir_outflow_kgh(level_m: float, t_bulk_c: float, crest_m: float, cw_m3h: float) -> float:
    """Free overflow over the funnel lip [kg/h], decoupled from the inlet.

    Process utility
    ---------------
    What the vessel can discharge on head alone. Below the lip it is exactly zero, which is
    the safety-relevant behaviour: the reactor cannot drain itself through N5 however wide
    HV-322605 is opened, because the nozzle is fed by the funnel and the funnel is 0.7 m above
    the design surface. Cut the feed and the level parks at the lip.

    At design the head is 0.7 m over a lip more than three metres in circumference, so the
    weir passes many times the production rate and is not what sets the flow — the valve is.

    Equation
    --------
        H     = max(level - crest, 0)          head over the lip; no backflow below it
        Q     = C_w . H^1.5                    Francis weir, C_w = Cd.(2/3).sqrt(2g).b
        m_out = rho(T_bulk) . Q
    """
    head = max(0.0, level_m - crest_m)
    q_vol = cw_m3h * head ** 1.5
    return melt_density(t_bulk_c) * q_vol


def hv322605_kv(stroke_pct: float) -> float:
    """HV-322605 flow coefficient [m3/h] at a stroke, on the vendor characteristic.

    Process utility
    ---------------
    The operator's one hydraulic authority over the reactor: HV-322605 decides how fast melt
    leaves for the stripper, and therefore whether the level rises or falls. It does NOT
    decide the vapour/liquid split at the reactor top — that happens downstream in the 322E001
    tubes — which is a distinction worth making because the valve is often described as if it
    controlled production.

    The characteristic is linear between the vendor's table points. The shut end is the
    class-IV seat, so the first pair is (0 %, 0), not the trim line's 12 m3/h intercept:
    a closed valve passes nothing, and interpolating the line to zero stroke would leave the
    reactor draining at 2 % of full flow with the valve shut.
    """
    s = min(max(stroke_pct, 0.0), 100.0)
    for (s0, k0), (s1, k1) in zip(HV322605_KV_TABLE, HV322605_KV_TABLE[1:]):
        if s <= s1:
            return k0 + (k1 - k0) * (s - s0) / (s1 - s0)
    return HV322605_KV_TABLE[-1][1]


def outlet_line_outflow_kgh(level_m: float, m_des_kgh: float, stroke_pct: float,
                            stroke_des_pct: float, lip_m: float, cw_m3h: float,
                            t_bulk_c: float) -> float:
    """322R001 liquid discharge to the HP stripper [kg/h] — whichever restriction binds.

    Process utility
    ---------------
    The stripper's liquid feed, and the reactor's only outflow. Two things in series can set
    it, and which one does depends on whether the funnel is flooded:

        m_valve = m_des . Kv(theta) / Kv(theta_des)     funnel flooded: the valve sets it
        m_weir  = rho . C_w . max(L - L_lip, 0)^1.5     funnel free: its lip sets it
        m_out   = min(m_valve, m_weir)

    Opening HV-322605 drains the reactor to the lip and the weir then passes production;
    throttling it floods the reactor and starves the stripper. That pair of consequences is
    the whole reason the valve is on an operator's screen.

    Why the valve sees its DESIGN differential pressure
    -----------------------------------------------------
    While the funnel is flooded the reactor's clear-liquid head does not reach the valve. The
    stripper gas enters 322R001 at the bottom nozzle N1, so the stripper back-pressure carries
    the same reactor column the downcomer does, and the two cancel:

        dP_valve = (rho_L - rho_mix) g z_lip + rho_L g (z_R - z_S) - dP_gas-path

    which leaves the valve at its design differential. The departures from that — gas-path
    losses and live liquid density — need the loop pressure network (finding A-1) and the
    piping elevations, and are open.

    At design the Kv ratio is exactly 1.0 and the weir, 0.7 m under the surface, passes more
    than fifty times the production, so the `min` selects the valve term and the design pin is
    bit-exact. Source: V1 `reactor.py` outlet_line_outflow_kgph, As-Built Phase 5r / A-12.
    """
    m_valve = m_des_kgh * hv322605_kv(stroke_pct) / hv322605_kv(stroke_des_pct)
    return min(m_valve, weir_outflow_kgh(level_m, t_bulk_c, crest_m=lip_m, cw_m3h=cw_m3h))


__all__ = [
    "RHO_FLOOR",
    "AREA_FLOOR",
    "melt_density",
    "level_from_holdup",
    "node_dtdt",
    "weir_outflow_kgh",
    "hv322605_kv",
    "outlet_line_outflow_kgh",
]
