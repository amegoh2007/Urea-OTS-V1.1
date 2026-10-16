"""321D003 — the ammonia feed drum, and the instruments that decide whether the pumps run.

What this models
----------------
A 1.03 m3 vertical drum holding liquid ammonia between the battery-limit import and the
321P002 suction. Small — about 650 kg at the working level, against a pump draw of 42.8 t/h
— so it holds roughly a minute of inventory. That is the point of it: it is a buffer, not a
storage tank, and it is why LIC-321501's makeup has to track the draw rather than chase a
level.

Source
------
Ported from V1 ``backend/main.py``, the 321D003 block of `step_sim` (level control, mass
balance, energy balance, PT/PY/PDY instruments) and `psat_nh3_bara`.

Equations implemented
---------------------
    F_BL    = clamp(F_draw + K_p (L_sp - L),  0,  F_BL,max)      LIC-321501 makeup
    dM/dt   = F_BL - F_draw                                      drum inventory
    M cp dT/dt = F_BL cp (T_BL - T)                              adiabatic drum
    P_suct  = P_top + rho g L H / 1e5 - dP_static                PT-321201/202
    PY      = Psat_NH3(T)                                        PY-321201/202
    PDY     = (P_suct,abs) - PY                                  PDYI-321203/204

Why the sub-cooling margin is a published number
-------------------------------------------------
PDYI-321203/204 is not a diagnostic. It is an initiator of trip 21.2, the urea synthesis main
trip, and it fires below 0.1 bar. A reciprocating pump handling liquid at its bubble point
flashes it on the suction stroke and knocks; the margin is what says the liquid is still
liquid. Two different upsets destroy it — the level falls, or the temperature rises — and one
equation catches both, which is why it is computed here rather than inferred from either.
"""

from __future__ import annotations

from dataclasses import dataclass

from ureasim.core.numeric import clamp
from ureasim.core.units_of_measure import ATM_BARA, G_ACC
from ureasim.data.unit_321 import (
    NH3_RHO,
    SUCTION_LOSS_BAR,
    TANK_BL_MAX_TH,
    TANK_H,
    TANK_LEVEL_MIN_FRAC,
    TANK_LEVEL_SP_FRAC,
    TANK_LIC_KP_TH,
    TANK_P_TOP_DES_BARG,
    TANK_VOL,
    T_BL_FEED_C,
)
from ureasim.thermo.empirical import nh3_psat_bara

#: Inventory below which the drum's temperature is held rather than integrated [kg].
#: Source: V1 `main.py`, the `if M_tank_kg > 1.0` guard. Dividing an energy balance by a
#: nearly empty drum gives an unbounded temperature rate; holding the last value is the
#: honest answer, because a drum with a kilogram in it has no bulk temperature to speak of.
DRUM_MIN_INVENTORY_KG = 1.0


def makeup_flow_th(pump_draw_th: float, level_frac: float) -> float:
    """LIC-321501 battery-limit ammonia import [t/h].

    Process utility
    ---------------
    The import valve carries the live pump draw as a FEED-FORWARD term plus a proportional
    level-restoring term. Feed-forward is what makes the arrangement work on a drum this
    small: a plain P controller on a one-minute inventory either lets it drain into the 21.2
    low-level trip or floods it on a feed disturbance, because by the time the level has moved
    enough to generate an error the inventory is already gone.

    With the draw fed forward, import equals draw at steady state and the proportional term is
    a correction rather than the whole signal — so the level holds at set point with ZERO
    offset, and at design (level = SP) the makeup is exactly the draw, bit-exact.

    Equation
    --------
        F_BL = clamp(F_draw + K_p (L_sp - L),  0,  F_BL,max)
    """
    return clamp(pump_draw_th + TANK_LIC_KP_TH * (TANK_LEVEL_SP_FRAC - level_frac),
                 0.0, TANK_BL_MAX_TH)


@dataclass
class FeedDrum:
    """The 321D003 inventory, its temperature, and the suction instruments.

    Process utility
    ---------------
    Everything the pumps depend on. The level decides whether there is suction at all, the
    temperature decides the ammonia's vapour pressure, and the two together decide the
    sub-cooling margin that trip 21.2 watches.
    """

    #: Liquid inventory as a fraction of the shell volume [-]. LI-321501.
    level_frac: float = TANK_LEVEL_SP_FRAC
    #: Bulk liquid temperature [C]. TT-321001 / TT-321002.
    temperature_c: float = T_BL_FEED_C
    #: Drum top operating pressure [bar g]. A boundary in this model.
    top_pressure_barg: float = TANK_P_TOP_DES_BARG
    #: Battery-limit import as LIC-321501 last commanded it [t/h].
    makeup_th: float = 0.0
    #: FQT-321401 running total of ammonia delivered to the loop [t].
    totalizer_t: float = 0.0

    @property
    def inventory_kg(self) -> float:
        """Liquid ammonia held [kg]."""
        return self.level_frac * TANK_VOL * NH3_RHO

    def suction_available(self, xv_321901_open: bool) -> bool:
        """Whether the pumps have suction.

        Process utility
        ---------------
        Two ways to lose it: the operator shuts the quick-closing valve, or the drum empties.
        The level threshold is also one of the 21.2 main-trip initiators, so the same number
        appears in both places deliberately — losing suction and tripping on lost suction are
        the same event, not two.
        """
        return bool(xv_321901_open) and self.level_frac > TANK_LEVEL_MIN_FRAC

    def step(self, pump_draw_th: float, dt: float) -> None:
        """Advance the inventory, the temperature and the totalizer by one tick.

        Process utility
        ---------------
        The mass balance runs on the BL import LIC-321501 computes from the live draw, so at
        design the two cancel and the level does not move at all — `dM = 0` exactly, which is
        what keeps the boot pin bit-exact.

        The energy balance is adiabatic: the drum has no heat input and its environmental loss
        is negligible against a one-minute residence time, so the bulk temperature simply
        relaxes toward the battery-limit supply temperature at the dilution rate.

            M cp dT/dt = F_BL cp (T_BL - T)   =>   dT/dt = F_BL (T_BL - T) / M

        The specific heat cancels, which is why it does not appear in the code.
        """
        self.makeup_th = makeup_flow_th(pump_draw_th, self.level_frac)

        dm_kg = (self.makeup_th - pump_draw_th) * 1000.0 / 3600.0 * dt
        volume_new = clamp(self.level_frac * TANK_VOL + dm_kg / NH3_RHO, 0.0, TANK_VOL)
        self.level_frac = volume_new / TANK_VOL

        self.totalizer_t += pump_draw_th * dt / 3600.0

        inventory_kg = self.inventory_kg
        makeup_kgs = self.makeup_th * 1000.0 / 3600.0
        if inventory_kg > DRUM_MIN_INVENTORY_KG:
            self.temperature_c += (makeup_kgs * (T_BL_FEED_C - self.temperature_c)
                                   / inventory_kg) * dt

    # -- instruments --------------------------------------------------------------------

    def suction_pressure_barg(self, suction_open: bool) -> float:
        """Real static pressure at the pump suction [bar g].

        Process utility
        ---------------
        The physical suction head: drum top pressure, plus the static head of the liquid
        standing above the tapping, less the line loss. It is what the pump actually sees, and
        it is kept even though the transmitters do not read it — see
        :meth:`feed_pressure_barg`. With the quick-closing valve shut there is no suction at
        all, and the model says zero rather than a stale number.

        Equation
        --------
            P = P_top + rho g L H / 1e5 - dP_static
        """
        if not suction_open:
            return 0.0
        # Standard gravity, where V1 writes 9.81 (handoff B-7, decided 2026-10-07): 1.8e-5 bar
        # less head at the design level, four orders under trip 21.2's 0.1 bar margin.
        head_bar = (NH3_RHO * G_ACC * self.level_frac * TANK_H) / 1e5
        return self.top_pressure_barg + head_bar - SUCTION_LOSS_BAR

    def feed_pressure_barg(self) -> float:
        """PT-321201 / PT-321202 as the transmitters read them [bar g].

        Process utility
        ---------------
        Both transmitters read the NH3 FEED-STREAM pressure at the drum — that is, the top
        operating pressure — which is what matches the plant's own feed-stream reading. It is
        deliberately NOT :meth:`suction_pressure_barg`: the physical head is kept for the
        physics and the trips, and this is kept for the screens, because the two are different
        numbers on the plant and an operator reads this one.
        """
        return self.top_pressure_barg

    def vapour_pressure_bara(self) -> float:
        """PY-321201 / PY-321202 — ammonia saturation pressure at TT-321002 [bar a]."""
        return nh3_psat_bara(self.temperature_c)

    def subcooling_margin_bar(self) -> float:
        """PDYI-321203 / PDYI-321204 — sub-cooling margin [bar]. Positive means liquid.

        Process utility
        ---------------
        An initiator of trip 21.2, firing below 0.1 bar. Computed on the ABSOLUTE feed
        pressure against the absolute saturation pressure, so the atmospheric constant used
        here is the process one and not the display one — the two differ by 0.25 mbar and this
        difference feeds a trip.

        Equation
        --------
            PDY = (P_feed[bar g] + P_atm) - Psat(T)
        """
        return (self.feed_pressure_barg() + ATM_BARA) - self.vapour_pressure_bara()


__all__ = [
    "DRUM_MIN_INVENTORY_KG",
    "makeup_flow_th",
    "FeedDrum",
]
