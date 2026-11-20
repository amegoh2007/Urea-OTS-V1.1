"""322R001's liquor at its bubble point — the node temperatures' ceiling and the gas it flashes.

What this models
----------------
The reactor is a bubbling column: its liquor cannot be hotter than its bubble point at the
pressure it stands under. V1's node energy balance (`reactor_hydraulics.node_dtdt`) has no such
ceiling, so wherever the carbamate exotherm outruns the liquid that carries it — a start-up, a
loop far below its design pressure — the nodes run away (420 C on V1's own cold start, 600 C on
the port's) and the hot kinetics turn the whole feed into urea and biuret, a liquid that holds
the loop's mass out of its vapour.

Decided by the process engineer on 2026-10-14 (handoff B-92; decision 45 / 48's class, the held
liquor boiling past its own boiling point): each node is held at most at the liquor's bubble
temperature at the live loop pressure, and the excess heat is paid as latent heat — it flashes
the liquor's volatiles back into the off-gas, which returns their mass to the loop's vapour.

    1 / T_bub(P) = 1 / T_des - (R / dH_vap) . ln(P_top / P_des),   P_top = PT-329201 + (P_des - P_loop,des)

    E_n   = m cp . tau_n . (T_n - T_bub) / dt     for every node above T_bub        [kJ/h]
    H     = n_CO2 . dH_carb + max(n_NH3 - 2 n_CO2, 0) . dH_vap + n_H2O . dH_H2O    [kJ/h]
    x     = min( sum E_n / H , 1 )                the share of the overflow's volatiles that flash
    T_n   = min(T_n, T_bub)

The bubble law is the model's own for the loop's melt, PI-322E002's Clausius-Clapeyron slope
(`carbamate_condenser.bubble_p_322e002`, 23 kJ/mol), anchored where the reactor's liquor boils at
design: its top node's pinned 183 C under the off-gas line's 141.3 bar a (PFD 207), the line's
design head over PT-329201 a subtraction of the two design pressures (A-13). ``m cp . tau_n`` is
the node's own thermal mass in V1's balance (tau_n = rho V_n / m), so the heat removed is exactly
what the balance put in above the ceiling. The volatiles leave in the proportions the overflow
holds them, each on its own enthalpy: the carbamate's CO2 with its two NH3 on the reactor's own
formation enthalpy (117 MJ/kmol, the heat that put it there), the free ammonia on the melt's
vaporisation enthalpy, the water on its latent heat. A liquor with no volatile left boils nothing:
what its volatiles cannot pay on a tick is published (``q_unpaid_kjh``) and leaves with the off-gas
as sensible heat — non-zero only where a state starts far above its ceiling, a start-up's first
ticks.

At the design seed the top node stands exactly on its bubble point and nothing flashes: the seed is
V1's to the bit.

Source: decision 102 (`project.md`); V1 ``backend/reactor.py`` ``node_dTdt`` for the balance it
bounds; `data.unit_322e002` (the melt's bubble law), `thermo.kinetics` (the carbamate enthalpy),
`data.synthesis_pin` (the pinned node profile).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ureasim.core.stream import MW_COMP
from ureasim.data.synthesis_pin import REACT_NODE_SS_DES_C
from ureasim.data.unit_320 import SYN_P_DES_BARA
from ureasim.data.unit_322e002 import BUB_DHVAP_JMOL, FLASH_DH, FLASH_R_GAS_J
from ureasim.data.unit_322r001 import OFFGAS_P_DES_BARA
from ureasim.thermo.kinetics import CARBAMATE_DH_JMOL

__all__ = ["BOIL_T_DES_C", "BOIL_DP_DES_BAR", "VOLATILES", "NodeBoil", "NO_BOIL",
           "liquor_bubble_t_c", "volatile_enthalpy_kjh", "node_boil"]

#: Where the reactor's liquor boils at design [deg C]: the pinned top node, PFD 207's 183 C.
BOIL_T_DES_C = REACT_NODE_SS_DES_C[-1]

#: The reactor top over PT-329201 at design [bar], 0.6: the off-gas line's 141.3 bar a less the
#: loop's 140.7, a subtraction of the two design pressures (A-13).
BOIL_DP_DES_BAR = OFFGAS_P_DES_BARA - SYN_P_DES_BARA

#: The liquor's volatiles, which a boil returns to the off-gas.
VOLATILES = ("NH3", "CO2", "H2O")

#: The enthalpies a kilomole of each pays [kJ/kmol]: carbamate back to its CO2 and two NH3 (the
#: reactor's own formation enthalpy), free ammonia off the melt, water's latent heat at 170 C.
_DH_CARB = -CARBAMATE_DH_JMOL
_DH_NH3 = BUB_DHVAP_JMOL
_DH_H2O = FLASH_DH["H2O"]

#: The reciprocal of the design anchor [1/K], held so the design pressure returns the anchor to
#: the bit (`scrubber.condensing_temperature_c`'s form).
_INV_DES = 1.0 / (BOIL_T_DES_C + 273.15)

#: Floor on the pressure the bubble law takes a logarithm of [bar a].
_P_FLOOR_BARA = 1.0e-6


@dataclass(frozen=True)
class NodeBoil:
    """One tick of the reactor liquor's boil."""

    #: The node temperatures, none above the bubble temperature [deg C].
    t_nodes_c: tuple
    #: The liquor's bubble temperature at the live pressure [deg C].
    t_bub_c: float
    #: The share of the overflow's volatiles that flashed [-], and what flashed [kmol/h, kg/h].
    frac: float
    flash_kmolh: dict
    m_kgh: float
    #: The heat the flash paid, and the excess the liquor's volatiles could not pay [kJ/h].
    q_kjh: float
    q_unpaid_kjh: float


#: No boil: the result of a tick whose nodes all stand at or below the bubble temperature is
#: built by `node_boil` itself; this is the flash it carries.
NO_BOIL = {k: 0.0 for k in VOLATILES}


def liquor_bubble_t_c(p_syn_bara: float) -> float:
    """The temperature 322R001's liquor boils at under the live loop pressure [deg C].

    Process utility
    ---------------
    The ceiling on the four thermowells: a liquor hotter than this flashes down to it. It rides
    the loop pressure, 0.532 K per bar at design (As-Built §CLIII), so a falling loop flashes the reactor's liquor
    and a rising one lets it hold more carbamate — the reactor's pressure and top temperature are
    tied as on the plant.

    Equation
    --------
        1 / T_bub = 1 / T_des - (R / dH_vap) . ln((P + dP_des) / P_des)

    written as an increment on the anchor, so the design pressure returns exactly 183 C.
    """
    inv = _INV_DES - (FLASH_R_GAS_J / BUB_DHVAP_JMOL) * math.log(
        max(p_syn_bara + BOIL_DP_DES_BAR, _P_FLOOR_BARA) / OFFGAS_P_DES_BARA)
    return BOIL_T_DES_C + (1.0 / inv - 1.0 / _INV_DES)


def volatile_enthalpy_kjh(overflow_kmolh: dict) -> float:
    """The heat that flashes every volatile the overflow holds [kJ/h].

    Process utility
    ---------------
    How much excess heat the liquor can pay by boiling: its CO2 leaves as carbamate decomposing,
    with two NH3, its ammonia beyond that as free ammonia, its water as steam.
    """
    co2 = max(overflow_kmolh.get("CO2", 0.0), 0.0)
    nh3 = max(overflow_kmolh.get("NH3", 0.0), 0.0)
    h2o = max(overflow_kmolh.get("H2O", 0.0), 0.0)
    return co2 * _DH_CARB + max(nh3 - 2.0 * co2, 0.0) * _DH_NH3 + h2o * _DH_H2O


def node_boil(t_nodes_c, p_syn_bara: float, mcp_kjhk: float, tau_nodes_s,
              overflow_kmolh: dict, dt: float) -> NodeBoil:
    """Hold the nodes at the liquor's bubble point and flash what the excess heat boils.

    Process utility
    ---------------
    Keeps the reactor's liquor where a boiling liquid can be, and puts the gas it gives up back
    in the off-gas: on a start-up the feeds' NH3 and CO2 stay vapour until the loop's pressure
    has risen to what the liquor's temperature can hold, which is how the loop pressurises.

    ``t_nodes_c`` are the node temperatures the energy balance has just stepped to, ``mcp_kjhk``
    the liquid's heat-capacity rate the balance ran on, ``tau_nodes_s`` each node's residence
    this tick, ``overflow_kmolh`` the reaction's liquid product this tick. Returns the capped
    temperatures and the flash (module docstring).
    """
    t_bub = liquor_bubble_t_c(p_syn_bara)
    excess = sum(mcp_kjhk * tau * (t - t_bub) / dt
                 for t, tau in zip(t_nodes_c, tau_nodes_s) if t > t_bub and math.isfinite(tau))
    if excess <= 0.0:
        return NodeBoil(t_nodes_c=tuple(t_nodes_c), t_bub_c=t_bub, frac=0.0,
                        flash_kmolh=dict(NO_BOIL), m_kgh=0.0, q_kjh=0.0, q_unpaid_kjh=0.0)
    heat = volatile_enthalpy_kjh(overflow_kmolh)
    frac = min(excess / heat, 1.0) if heat > 0.0 else 0.0
    flash = {k: frac * max(overflow_kmolh.get(k, 0.0), 0.0) for k in VOLATILES}
    paid = frac * heat
    return NodeBoil(
        t_nodes_c=tuple(min(t, t_bub) for t in t_nodes_c), t_bub_c=t_bub, frac=frac,
        flash_kmolh=flash, m_kgh=sum(flash[k] * MW_COMP[k] for k in VOLATILES), q_kjh=paid,
        q_unpaid_kjh=excess - paid)
