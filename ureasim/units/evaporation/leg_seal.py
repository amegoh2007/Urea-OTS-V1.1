"""324F003's barometric leg — the seal it holds against the atmosphere, and the air it admits lost.

What this models
----------------
Stage 2's melt, PFD 402, leaves 324F003 down a barometric leg to the melt pump 335P001;
LT-324501 reads the leg's level, not the vessel's (UD-AU-324-EC-0008). The leg's melt is the seal
between the separator's 0.13 bar a and the atmosphere. Run it down until LT-324501 uncovers the
seal and atmospheric air enters the vacuum through the drain's path: the condenser 324E005 behind
the separator blankets, 324F004 cannot hold the load, and stage 2's vacuum breaks (handoff B-107,
decided 2026-10-22; `Scenarios.md` §5.4). V1's empty leg admits nothing.

The air's rate is the drain trim's own: LV-324501A's liquid sizing on the blow-through law of
`consequence.seal` (As-Built §XIX.1-2), nothing tuned.

Source: the loop summary L 324501 (UD-MR-324-EC-0001 rev 1, sheet 2/4) for LV-324501A's case;
PFD 783 for the air; `data.unit_324`.
"""

from __future__ import annotations

from ureasim.control.valve import cv_fraction
from ureasim.core.units_of_measure import ATM_BARA
from ureasim.data.unit_324 import (
    LIC_324501_OP_DES_PCT,
    LV_324501A_OP_DES_PCT,
    LV_324501_CHAR,
    LV_324501_DP_DES_BAR,
    LV_324501_RHO_KGM3,
    P2_DES_KGH,
    SEAL_AIR_GAMMA,
    SEAL_AIR_T_C,
    VAC_AIR_MW,
)
from ureasim.units.consequence.seal import blowthrough_kgh, gas_density_ideal, seal_fraction

__all__ = ["SEAL_AIR_RHO_KGM3", "seal_air_kgh"]


#: The atmosphere's air at PFD 783's 32 C [kg/m3], about 1.152: what a lost seal draws in.
SEAL_AIR_RHO_KGM3 = gas_density_ideal(ATM_BARA, SEAL_AIR_T_C, VAC_AIR_MW)


def seal_air_kgh(level_pct: float, stroke_pct: float, p_bara: float,
                 vendor: bool = True) -> float:
    """The atmospheric air 324F003's lost barometric seal admits [kg/h] (handoff B-107).

    Process utility
    ---------------
    The melt leg under 324F003 is the seal between the deep vacuum and the atmosphere. Run its
    level down until LT-324501 uncovers the seal and air rushes up through the empty leg into the
    separator: the condenser behind it blankets, the ejector cannot hold it, and stage 2's vacuum
    breaks — the warning a falling LI-324501 gives before the melt's strength is lost.

    Equation
    --------
    The drain's trim passing gas instead of melt, on its own liquid sizing (`consequence.seal`):

        m_air = m_des . (phi(h) / phi(h_des)) . Y . sqrt(rho_air . dP_eff / (rho_melt . dP_des))
                . (1 - seal)

    phi LV-324501A's equal-percentage trim on Flowserve's sheet and h_des its 75.35 % (decision
    150); ``vendor`` False is V1's linear h / 75. m_des the design drain at the design stroke, the
    loop summary's 1221 kg/m3 and 6.9 -> 3.7 bar a, the air at the atmosphere and PFD 783's 32 C, dP from the atmosphere to
    PT-324203, choked below 0.30 bar a (x_T 0.70, F_k 1 for air): about 730 kg/h at the design
    stroke on a fully lost seal, against PFD 783's 21. Exactly zero while the seal holds.
    """
    if vendor:
        trim = (cv_fraction(stroke_pct / 100.0, LV_324501_CHAR)
                / cv_fraction(LV_324501A_OP_DES_PCT / 100.0, LV_324501_CHAR))
    else:
        trim = stroke_pct / LIC_324501_OP_DES_PCT
    return blowthrough_kgh(P2_DES_KGH, LV_324501_RHO_KGM3, LV_324501_DP_DES_BAR,
                           trim, SEAL_AIR_RHO_KGM3, ATM_BARA,
                           ATM_BARA - p_bara, seal_fraction(level_pct), gamma=SEAL_AIR_GAMMA)
