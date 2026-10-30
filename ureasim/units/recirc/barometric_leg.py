"""323F010's barometric leg — the separator's drain to 323D002, line 200-US6-323256.

What this models
----------------
PFD 317, the 80 % urea the 323F010 separator drains into Compartment I of the atmospheric 323D002.
The separator has no level control and its leg no valve: the melt leaves the separator's bottom
nozzle N2 (DN 400, behind a vortex breaker) and falls down the leg, whose foot dips into the tank
through N1. The separator's pressure stands on the leg's column, which rises and falls with the
vacuum.

The leg on its drawings — decided 2026-10-30 (handoff B-119, option (b))
-----------------------------------------------------------------------
Isometric UD-RL-100-MB-0142 runs the leg from 323F010/N2 at EL +15 740 to 323D002/N1 at EL +6 095,
and the tank's general assembly UD-AU-323-TL-0001 dips N1 into Compartment I and gives a design
liquid level of 4.95 m above the bottom plate at EL +800. A full vacuum holds 8.98 m of PFD 317's
1 151 kg/m3 melt, so with the tank at its design liquid level the column's top stands about 1.01 m
below N2 at the deepest vacuum (`unit_323.F010_LEG_MARGIN_M`): the leg never fills to the
separator. The melt falls through N2 into a leg whose space above the column stands at the
separator's own pressure, so the separator drains on its own liquid head alone:

    m_317 = m_317,des . sqrt( M / M_des )

the orifice law on the head M g / A that V1's law takes for the separator's liquid, anchored on
the design holdup and drain, so the design point is V1's to the bit.

V1's leg, kept on the harnesses' switch
---------------------------------------
V1 (its report A-17) takes the leg as a column standing full to the separator, rho g h_leg = P_atm,
so the separator's absolute pressure enters the drive (`barometric_leg_kgh`). Its 0.46 bar a
outweighs the design holdup's 6 383 Pa of head, so V1's drain hardly answers the holdup: away from
the design throughput the separator fills without bound above about 105 % load and drains dry
below design (handoff B-119). ``PreEvaporator(own_head_leg=False)`` is V1's, which the
equivalence harness keeps.

Source
------
V1 ``backend/main.py`` ``gravity_outflow_323f010`` (report A-17); the isometric and the general
assembly above, read from the vendor archive's scans (As-Built §XCI.6). The design data are in
`ureasim.data.unit_323` and `ureasim.data.unit_323d002`, each with its source.
"""

from __future__ import annotations

import math

from ureasim.core.units_of_measure import G_ACC, PA_PER_BAR
from ureasim.data.design_point import R323_M317_DES
from ureasim.data.unit_323 import F010_AREA_M2, F010_M_DES_KG, F010_P_BARA


def own_head_leg_kgh(holdup_kg: float) -> float:
    """The separator's drain through N2 on its own liquid head [kg/h], decided 2026-10-30.

    Process utility
    ---------------
    PFD 317, the product to the tank. The leg is taller than any column the separator's vacuum
    can hold (`unit_323.F010_LEG_MARGIN_M`), so the vacuum stands on the leg's column, never on
    the separator's liquid: what drains the separator is the melt standing above N2. Its level
    therefore follows its throughput, 21 % more holdup for 10 % more product, and a lost vacuum
    leaves the drain where it was. V1's leg floods the separator above about 105 % load and drains
    it below design (handoff B-119, option (b)).

    Equation
    --------
        m_317 = m_317,des . sqrt( M / M_des )

    the orifice law on the liquid head M g / A over the separator's bore, normalised on the design
    holdup, so the drain is the design drain at the design holdup whatever the pressure.

    Source: isometric UD-RL-100-MB-0142 and 323D002's general assembly UD-AU-323-TL-0001 for the
    premise; V1 `main.py` R323_F010_M_TAU_S and the PFD's 317 for the anchor.
    """
    return R323_M317_DES * math.sqrt(max(holdup_kg, 0.0) / F010_M_DES_KG)


def barometric_leg_kgh(holdup_kg: float, p_separator_bara: float) -> float:
    """The separator's drain through its barometric leg to 323D002 [kg/h], V1 report A-17.

    Process utility
    ---------------
    PFD 317, the product to the tank. The leg has no valve: it discharges into the
    ATMOSPHERIC 323D002, so its liquid column — about 8 m of 80 % melt — stands against the
    atmosphere, and what drives the drain is the liquor standing in the separator plus the
    separator's own absolute pressure. A falling level lowers the drain, and losing the vacuum
    raises it, because the column no longer holds the atmosphere back.

    Equation
    --------
    With rho . g . h_leg = P_atm the melt density cancels from both the vessel head and the leg,
    which matters because no source pins it for this stream:

        dP_drive = M g / A + P_separator
        m_317    = m_317,des . sqrt( dP_drive / dP_drive,des )

    with A the separator bore (datasheet ID 3478 mm). Exactly the design drain at the design
    holdup and 0.46 bar a.

    Source: V1 `main.py` `gravity_outflow_323f010`.
    """
    dp_des = F010_M_DES_KG * G_ACC / F010_AREA_M2 + F010_P_BARA * PA_PER_BAR
    dp_live = (max(holdup_kg, 0.0) * G_ACC / F010_AREA_M2
               + max(p_separator_bara, 0.0) * PA_PER_BAR)
    return R323_M317_DES * math.sqrt(max(dp_live / dp_des, 0.0))


__all__ = ["own_head_leg_kgh", "barometric_leg_kgh"]
