"""322E003's shell — what the tempered water can condense of the scrubber's carbamate.

What this module models
-----------------------
The HP scrubber's shell side: the tempered water of the 329P006 circulation (FIC-329409) that
takes the heat of the carbamate condensing in the tubes. Three relations: the temperature the
carbamate condenses at, which rides the loop pressure; the water's effective conductance on the
datasheet's UA; and the condensation capacity as a fraction of the demand on it, the entry point of
the loss-of-cooling scenario.

Equations
---------
    1/T_cond(P) = 1/T_des - (R / dH_carb) . ln(P / P_des)
    C = max(m . cp / 3600, C_floor),   eps = 1 - exp(-UA / C),   G = max(eps . C, G_floor)
    rho = (G(m) / G(m_des)) . pump_frac . max(f_th, 0) / s
    f_th = (T_cond(P) - T_ccw,in) / (T_cond,des - T_ccw,in,des)

Moved out of `scrubber` unchanged (2026-10-23, the housekeeping split); `scrubber` re-exports every
name, and its duty's effectiveness-NTU bridge takes the two conductance floors from here.

Source: V1 `backend/main.py` `scrub_cond_t_c` and the rho_cond block of `step_sim`; the capacity on
the shell's effectiveness decided 2026-10-17 (handoff B-99 (b1)).
"""

from __future__ import annotations

import math

from ureasim.data.unit_322e003 import (
    CCW_CP_KJKGK,
    CCW_KGH_DES,
    CCW_T_IN_DES_C,
    COND_DH_JMOL,
    COND_P_DES_BARA,
    COND_R_JMOLK,
    COND_T_DES_K,
    OVERFLOW_T_DES_C,
    UA_KWK,
)

#: Floor on the heat-capacity rate of the cooling water [kW/K].
#:
#: Not a physical limit — a pole. FIC-329409 can be shut, and the effectiveness-NTU bridge
#: divides by this rate twice. Flooring it at 1e-6 lets the water rate go to zero and takes
#: the effectiveness to 1, which is the correct limit: with no water the process side and
#: the "return" temperature both walk up to the condensation ceiling. Source: V1 `main.py`.
C_CCW_FLOOR_KWK = 1.0e-6

#: Floor on the effective conductance [kW/K], for the same division.
UA_EFF_FLOOR_KWK = 1.0e-6

#: Floor on the pressure the Clausius-Clapeyron relation takes a logarithm of [bar a].
COND_P_FLOOR_BARA = 1.0e-6

#: Reciprocal of the condensing-temperature anchor [1/K], held so that a call at the design
#: pressure produces a literal ``log(1.0) == 0.0`` and an identical reciprocal.
_COND_INV_DES = 1.0 / COND_T_DES_K


def condensing_temperature_c(p_bara: float) -> float:
    """Temperature the shell condenses carbamate at, at the live loop pressure [deg C].

    Process utility
    ---------------
    The driving force the cooling water works against is the gap between the condensing
    temperature and the water, and the condensing temperature is not a constant: it rides
    the loop pressure, because that is what a condensing vapour does. A loop drifting up in
    pressure condenses MORE readily, not less.

    That sign is the reason this function exists. V1's earlier form held the condensing
    temperature at its design anchor and divided the whole capacity by the pressure ratio
    instead, which asserts the opposite — and with the sign wrong the loop fed back on
    itself: capacity fell, off-gas went uncondensed, the retained vapour pushed the pressure
    higher, and capacity fell further. Six of the eight design-seed inertness gaps in the
    cooling-water chain were that one loop.

    Equation
    --------
        1/T_cond(P) = 1/T_des - (R / dH_carb) . ln(P / P_des)

    Written as an INCREMENT on the design temperature, so at the design pressure the
    logarithm is a literal 0.0, the reciprocal is identical, and the bracket is exactly 0.0.
    The design point cannot move. The slope at the anchor is R.T^2/(dH.P) = 0.0709 K/bar, so
    the 0.7 bar the loop drifts over an hour is worth 0.05 C of driving force.

    Source: V1 `main.py` `scrub_cond_t_c`.
    """
    inv = _COND_INV_DES - (COND_R_JMOLK / COND_DH_JMOL) * math.log(
        max(p_bara, COND_P_FLOOR_BARA) / COND_P_DES_BARA)
    return OVERFLOW_T_DES_C + (1.0 / inv - 1.0 / _COND_INV_DES)


def shell_conductance_kwk(m_ccw_kgh: float) -> float:
    """The tempered water's effective conductance eps . C [kW/K] at a circulation [kg/h].

    Process utility
    ---------------
    What the shell can carry per kelvin of driving force: the effectiveness-NTU bridge on the
    datasheet's UA, as the duty's temperatures use it. At a UA-limited shell more water adds little
    and less takes little away.

    Equation
    --------
        C = max(m . cp / 3600, C_floor),   eps = 1 - exp(-UA / C),   G = max(eps . C, G_floor)
    """
    c_kwk = max(m_ccw_kgh * CCW_CP_KJKGK / 3600.0, C_CCW_FLOOR_KWK)
    return max((1.0 - math.exp(-UA_KWK / c_kwk)) * c_kwk, UA_EFF_FLOOR_KWK)


#: The conductance at the design circulation [kW/K], the effectiveness ratio's denominator.
_CONDUCTANCE_DES_KWK = shell_conductance_kwk(CCW_KGH_DES)


def condensation_capacity(m_ccw_kgh: float, ccw_pump_frac: float, t_ccw_in_c: float,
                          p_loop_bara: float, co2_scale: float,
                          effectiveness: bool = True) -> float:
    """Condensation capacity as a fraction of the demand on it [-].

    Process utility
    ---------------
    The one number that decides whether this vessel is doing its job. Above 1.0 the shell
    condenses everything the loop sends it and the unit behaves as designed. Below 1.0 the
    shortfall stays in the vapour, leaves with the vent instead of the overflow, and — since
    322E003 is INSIDE the loop and nothing has crossed a boundary — shows up as rising
    synthesis pressure rather than as a mass imbalance. It is the entry point of the
    loss-of-cooling scenario.

    Equation
    --------
        f_th = (T_cond(P) - T_ccw,in) / (T_cond,des - T_ccw,in,des)    thermal driving force
        rho  = (G(m_ccw) / G(m_ccw,des)) . pump_frac . max(f_th, 0) / s capacity over demand

    G the shell's conductance (`shell_conductance_kwk`, decided 2026-10-17, B-99 (b1)); V1 takes
    the flow ratio m_ccw / m_ccw,des in its place (``effectiveness=False``).

    Three independent ways to lose it, which is what makes the scenario teachable: throttle
    the water (the flow term), lose the temper (the driving-force term), or stop the pumps
    (the pump term). All three are exactly 1.0 at design, so the product is too.

    Why the pump fraction is separate from the flow
    -------------------------------------------------
    The flow term reads the FT-329409 transmitter, which carries a 25 s plant lag. The
    circulation itself stops with the pumps, immediately, because their discharge check
    valves shut. Reading the capacity off the lagged indication alone left 0.33 % of design
    condensation alive long after both 329P006 machines had been stopped.

    Source: V1 `main.py` `step_sim`, the rho_cond block.
    """
    t_cond = condensing_temperature_c(p_loop_bara)
    f_th = (t_cond - t_ccw_in_c) / max(OVERFLOW_T_DES_C - CCW_T_IN_DES_C, 1e-6)
    flow = (shell_conductance_kwk(m_ccw_kgh) / _CONDUCTANCE_DES_KWK if effectiveness
            else m_ccw_kgh / CCW_KGH_DES)
    return flow * ccw_pump_frac * max(f_th, 0.0) / max(co2_scale, 1e-6)

__all__ = ["C_CCW_FLOOR_KWK", "UA_EFF_FLOOR_KWK", "COND_P_FLOOR_BARA", "condensing_temperature_c",
           "shell_conductance_kwk", "condensation_capacity"]
