"""LY-324501 — 324F003's level as AC4 computes it from LT-324501 and PT-324203 (decision 252).

What this models
----------------
LT-324501 is a single-seal gauge transmitter on 324F003's barometric leg to the melt pump
335P001, its tap at EL +8.495 (UD-RL-100-MB-0180). It reads the melt's head over the tap plus the
separator's gauge pressure, so AC4 subtracts PT-324203 to give the level LIC-324501 controls, the
console shows and 335P001's low-level stop reads (AC4 PC35.2.1, UD-MR-G00-FF-0004 p. 248). The
transmitter reads no lower than its calibrated LRV, Rosemount's -700 mbar (UD-MR-G00-DZ-0012-002
p. 76), so at the separator's vacuum LY-324501 has a floor: about 20.6 % at the design 0.131 bar a.

The level read is V1's holdup ratio, kept (decision 252): the formula and the floor apply to it.
Above the floor the formula's round trip returns the level unchanged, so the design point is kept
to the bit (As-Built §CXLV.3).

Equations
---------
    LT-324501 = 885 LY / 100 + 1000 (P - P_atm)             [mbar g, the leg's head and the gauge]
    LY-324501 = (max(LT-324501, LRV) - 1000 (P - P_atm)) / 885 x 100     [AC4 PC35.2.1]
             = max(LY, LY_floor),  LY_floor = (LRV - 1000 (P - P_atm)) / 885 x 100

Source: As-Built §CXLI.6 (AC4's formula), §CXL.1 (the LRV), §CXLV.2 (the floor); `data.unit_324`.
"""

from __future__ import annotations

from ureasim.core.numeric import clamp
from ureasim.core.units_of_measure import ATM_BARA
from ureasim.data.unit_324 import LT_324501_LRV_MBAR, LY_324501_SPAN_MBAR

__all__ = ["ly_floor_pct", "ly_324501"]


def ly_floor_pct(p_bara: float) -> float:
    """The lowest LY-324501 can read at the separator's pressure [%].

    Process utility
    ---------------
    With the melt at or below the tap, LT-324501 sits at its LRV, and AC4's subtraction of the
    vacuum turns that into a positive level: at the design vacuum the console reads about 20 % on
    an empty leg, and 335P001's 5 % low-level stop cannot act until the vacuum breaks above
    0.269 bar a (As-Built §CXLV.2).

    Equation
    --------
        LY_floor = (LRV - 1000 (P - P_atm)) / 885 x 100
    """
    return (LT_324501_LRV_MBAR - 1000.0 * (p_bara - ATM_BARA)) / LY_324501_SPAN_MBAR * 100.0


def ly_324501(level_pct: float, p_bara: float, ac4: bool = True) -> float:
    """LY-324501 [%] for the leg's level and PT-324203's pressure.

    Process utility
    ---------------
    The one level the plant's DCS gives for stage 2's melt: LIC-324501's measurement, the
    console's LI-324501 and the input of 335P001's low-level stop.

    Equation
    --------
        LY = max(clamp(level, 0, 100), LY_floor(P))
    The clamp is V1's 0 to 100 %; ``ac4=False`` returns it alone, V1's reading, which the
    equivalence harnesses keep. Above the floor the level is returned unchanged, the formula's
    round trip (to 1.4e-14 %) taken as exact.
    """
    level = clamp(level_pct, 0.0, 100.0)
    if not ac4:
        return level
    return max(level, ly_floor_pct(p_bara))
