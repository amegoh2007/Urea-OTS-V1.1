"""The LP flash gas node's gas balance: what 323E011 condenses and what PV-323203 vents.

What this models
----------------
The four relations `flash_condenser` integrates the node's pressure on (As-Built §XXXIII): the gas
323E011 cannot condense on V1's constant capacity, the condenser's dew point at the node pressure
and its capacity on that dew point against the cooling water (handoff B-30, decided 2026-10-15),
and PV-323203's square-root vent to 323C005, its differential floored at zero (B-30):

    gen   = max(G - 5589, 0)                                          [V1's]
    T_dew = 45 + Tsat(P) - Tsat(1.13)
    C(P)  = 5589 max(T_dew - 35, 0) / (45 - 35)
    m_702 = 440 (h / 25) sqrt( max(P - 1.0, floor) / (1.13 - 1.0) )

Split from `flash_condenser` (2026-10-16) to hold that module under the house's 600 lines; the
unit re-exports all four under their own names, so every caller and test reads them as before.

Source
------
V1 ``backend/c003_pressure_coupling.py`` ``e011_vent_generation_kgh``; V1 ``backend/main.py``
step_sim, "Stage 9 : 323E011 + 323D011", ``m_v011``; the dew-point form of V1's 323E003
(`lp_carbamate_condenser`). The design data are in `ureasim.data.unit_323e011`.
"""

from __future__ import annotations

import math

from ureasim.data.unit_323e011 import (
    C005_P_BARA,
    E011_CONDENSATION_CAPACITY_DES_KGH,
    E011_CW_T_C,
    E011_MV_DES_KGH,
    E011_P_BARA,
    E011_PV_OP_DES_PCT,
    E011_T_C,
    TSAT_E011_DES_C,
    VENT_DP_MIN_BAR,
)
from ureasim.thermo import iapws



def vent_generation_kgh(gas_inlet_kgh: float) -> float:
    """The gas 323E011 cannot condense, which must leave through PV-323203 [kg/h].

    Process utility
    ---------------
    The condenser's side of the node's gas balance: what it adds to the vapour space. V1 takes
    the condensation as saturated at its design capacity because the cooling surface is fixed,
    so a falling gas load generates no vent gas at all — the condenser absorbs it — and every
    kilogram above the capacity has to be vented. The capacity does not move with the node
    pressure, the condenser temperature or the cooling water (handoff B-30).

    Equation
    --------
        gen = max(G - 5589, 0)

    Refuses a non-finite or negative load, as V1 does.

    Source: V1 ``c003_pressure_coupling.e011_vent_generation_kgh``.
    """
    if not math.isfinite(gas_inlet_kgh):
        raise ValueError("E011 gas inlet must be finite")
    if gas_inlet_kgh < 0.0:
        raise ValueError("E011 gas inlet must be nonnegative")
    return max(gas_inlet_kgh - E011_CONDENSATION_CAPACITY_DES_KGH, 0.0)


def dew_point_c(p_node_bara: float) -> float:
    """323E011's dew point at the node pressure [deg C] (handoff B-30, decided 2026-10-15).

    Process utility
    ---------------
    Where the node's restoring force comes from: more gas raises the pressure, the dew point with
    it, and the driving force to the cooling water. The gas is not water, so only the SLOPE is
    water's and the design node is the anchor — the frozen-offset idiom of 323E003's dew point.

    Equation
    --------
        T_dew = 45 + Tsat(P) - Tsat(1.13)

    Source: the form of V1's 323E003 (`lp_carbamate_condenser.dew_point_c`), anchored on
    323E011's design node.
    """
    return E011_T_C + (iapws.tsat_c(p_node_bara) - TSAT_E011_DES_C)


def condensation_capacity_kgh(p_node_bara: float) -> float:
    """What 323E011 condenses out of the node at its pressure [kg/h] (B-30, decided 2026-10-15).

    Process utility
    ---------------
    The condenser's side of the node's gas balance, on its dew point against the cooling water:
    5589 kg/h at the design node on the design 10 K. A higher node condenses more and a lower one
    less, so the condenser holds the node where V1's constant held nothing. Like 323E003's (handoff
    B-34) it is not capped at the gas that arrives: with surplus cooling the condenser draws on the
    gas the node holds until its dew point has closed on the water far enough. It is zero where
    the dew point meets the water, about 0.79 bar a.

    Equation
    --------
        cap = 5589 . max(T_dew - 35, 0) / (45 - 35)

    Source: the form of V1's 323E003 (`lp_carbamate_condenser.condensation_capacity_kgh`), V1's
    5589 kg/h (`c003_pressure_coupling.E011_CONDENSATION_CAPACITY_DES_KGH`) its anchor.
    """
    return (E011_CONDENSATION_CAPACITY_DES_KGH * max(dew_point_c(p_node_bara) - E011_CW_T_C, 0.0)
            / (E011_T_C - E011_CW_T_C))


def vent_valve_kgh(stroke_pct: float, p_node_bara: float,
                   dp_floor_bar: float = VENT_DP_MIN_BAR) -> float:
    """What PV-323203 passes from the node to 323C005 [kg/h], PFD 702.

    Process utility
    ---------------
    The only way out of the 1.13 bar a gas space, and so the one lever on the 323F004 flash
    pressure. Opening the vent lowers the node, which lowers the flash drum's bubble point and
    flashes more; pinching it raises both.

    Equation
    --------
    A design-anchored square-root law against an atmospheric 323C005:

        m_702 = 440 . (h / 25) . sqrt( max(P - 1.0, 0) / (1.13 - 1.0) )

    Exactly PFD 702 at the design stroke and pressure. V1 floors the differential at 0.001 bar
    (``dp_floor_bar``, `data.unit_323e011.VENT_DP_FLOOR_BAR`), so its vent still passes the flow of
    that differential at or below 1.0 bar a — a reverse differential, which walks the node to its
    0.1 bar a floor when nothing is generated. The port floors it at zero (decided 2026-10-15,
    handoff B-30): the vent passes nothing out of a node at or below the absorber it discharges to.

    Source: V1 `main.py` step_sim, ``m_v011``.
    """
    dp = max(p_node_bara - C005_P_BARA, dp_floor_bar)
    return (E011_MV_DES_KGH * (stroke_pct / E011_PV_OP_DES_PCT)
            * math.sqrt(dp / (E011_P_BARA - C005_P_BARA)))


__all__ = ["vent_generation_kgh", "dew_point_c", "condensation_capacity_kgh", "vent_valve_kgh"]
