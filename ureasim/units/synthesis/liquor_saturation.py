"""The synthesis loop's carbamate liquor at its bubble point: its buffering, what it condenses.

What this models
----------------
The loop's liquor — 322E002's melt, 322R001's and 322E003's carbamate — holds NH3 and CO2 only up
to its bubble pressure. Two consequences, both read off the design liquor's solubility:

  * **Its buffering** (handoff B-77 (b), decided 2026-10-09): a rising loop pressure condenses gas
    into the liquor, a falling one flashes it out — b_207, what a kilogram of PFD 207's liquor
    absorbs per bar, the Extended UNIQUAC slope of its bubble pressure anchored on its 141.3 bar a.
  * **Its saturation** (handoff B-91 (a), decided 2026-10-10): a liquor already at its bubble point
    for the loop's pressure condenses no more gas. While PT-329201 stands below the pressure the
    melt would boil at, 322E002 and 322E003 condense only the fraction f of what they would, and the
    reactor's liquor buffers only f of its b_207, so the feeds' gas stays in the vapour and builds
    the loop's pressure, as on a start-up:

        d = (P_bub - P_loop) - (P_bub,des - P_loop,des)        the deficit [bar]
        f = 1                     d <= 0
        f = max(1 - b_207 d, 0)   d > 0

    P_bub is PI-322E002, the model's own law for the melt's bubble pressure on its temperature,
    N/C and H/C (`carbamate_condenser.bubble_p_322e002`), anchored on the condenser outlet's 144.2
    bar a at 170 C; P_bub,des - P_loop,des is that outlet's design head over PT-329201, 3.5 bar
    (A-13's subtraction). At design d is zero and f exactly 1. Since 2026-10-14 (B-91) 322E003
    reads its own sump liquor's bubble pressure on the same law, anchored on PFD 206
    (`scrubber.liquor_bubble_p_bara`), its design head zero, in place of 322E002's fraction.

Source: decisions 95 and 97 (`project.md`); PFD stream 207 and the reactor's off-gas; `thermo.vle`;
`data.unit_322_loop`, `data.unit_322e002`.
"""

from __future__ import annotations

import math

from ureasim.core.stream import MW_COMP
from ureasim.data.unit_322_loop import BUFFER_DLN_FRAC, LIQUOR_DP_DES_BAR
from ureasim.data.unit_322r001 import (
    OFFGAS_DES_KMOLH,
    OFFGAS_P_DES_BARA,
    OVERFLOW_DES_KMOLH,
    REACTOR_T_DES_C,
)
from ureasim.thermo.vle import bubble_p_bara

__all__ = ["liquor_buffering_per_bar", "B_207_PER_BAR", "saturation_fraction"]


def liquor_buffering_per_bar(liquor_kmolh: dict, t_c: float, gas_kmolh: dict,
                             p_anchor_bara: float) -> float:
    """What a kilogram of liquor absorbs of the loop's gas per bar [kg/(kg.bar)].

    Process utility
    ---------------
    The loop's pressure is held by more than its vapour's compressibility: a rising pressure
    condenses NH3 and CO2 into the carbamate liquor, a falling one flashes them out. This is that
    buffering, read once off the design liquor's solubility so the node does not differentiate the
    electrolyte model every tick (decided 2026-10-09, handoff B-77 (b)).

    Equation
    --------
        b = 1 / (P_anchor . dln P_bub / dm),
        dln P_bub / dm = [ln P_bub(w + dm . y) - ln P_bub(w - dm . y)] / (2 dm),

    w the liquor's mass fractions, y the gas's condensables (NH3, CO2, H2O) by mass, dm
    ``BUFFER_DLN_FRAC`` kilograms per kilogram, P_bub the Extended UNIQUAC bubble pressure at
    ``t_c`` (`thermo.vle.bubble_p_bara`). The model puts PFD 207's bubble point at 40 bar a, outside
    the window its LP stages validate, so its logarithmic slope is lifted onto the stream's own
    pressure — the anchoring V1 gives every correlation it pins on the design.
    """
    m = {k: v * MW_COMP[k] for k, v in liquor_kmolh.items() if v}
    m_tot = sum(m.values())
    w = {k: v / m_tot for k, v in m.items()}
    g = {k: gas_kmolh.get(k, 0.0) * MW_COMP[k] for k in ("NH3", "CO2", "H2O")}
    g_tot = sum(g.values())
    y = {k: v / g_tot for k, v in g.items()}
    keys = set(w) | set(y)

    def p_bub(d: float) -> float:
        return bubble_p_bara({k: (w.get(k, 0.0) + d * y.get(k, 0.0)) / (1.0 + d) for k in keys},
                             t_c)

    dln = ((math.log(p_bub(BUFFER_DLN_FRAC)) - math.log(p_bub(-BUFFER_DLN_FRAC)))
           / (2.0 * BUFFER_DLN_FRAC))
    return 1.0 / (p_anchor_bara * dln)


#: The reactor liquor's buffering [kg/(kg.bar)], about 0.0154: PFD 207 at 183 C in the reactor's
#: design off-gas, anchored on its 141.3 bar a.
B_207_PER_BAR = liquor_buffering_per_bar(OVERFLOW_DES_KMOLH, REACTOR_T_DES_C, OFFGAS_DES_KMOLH,
                                         OFFGAS_P_DES_BARA)


def saturation_fraction(p_bub_bara: float, p_loop_bara: float,
                        dp_des_bar: float = LIQUOR_DP_DES_BAR) -> float:
    """What the loop's liquor can still condense, as a fraction of what its units would [-].

    Process utility
    ---------------
    A liquor at its bubble point holds no more gas. When PT-329201 stands below the pressure the
    loop's melt would boil at, 322E002 and 322E003 cannot condense what they would and the
    reactor's liquor does not take up the gas: it stays in the vapour and builds the pressure, which
    is how the loop pressurises on a start-up (decided 2026-10-10, handoff B-91 (a)). At or above
    the melt's bubble pressure the liquor condenses as designed.

    Equation
    --------
        d = (P_bub - P_loop) - (P_bub,des - P_loop,des),
        f = 1 for d <= 0, max(1 - b_207 . d, 0) above,

    b_207 the liquor's buffering, what a kilogram gives up per bar its bubble pressure stands above
    the loop's (decision 95's linearisation, read once at the design). ``p_bub_bara`` is
    PI-322E002 and ``p_loop_bara`` PT-329201; the design head ``dp_des_bar`` is a subtraction of
    the two design pressures, so the design point returns exactly 1 — 322E002's 3.5 bar by default,
    322E003's sump liquor's own, zero, where it reads its own bubble pressure (B-91, decided
    2026-10-14; `scrubber.liquor_bubble_p_bara`).
    """
    deficit = (p_bub_bara - p_loop_bara) - dp_des_bar
    if deficit <= 0.0:
        return 1.0
    return max(1.0 - B_207_PER_BAR * deficit, 0.0)
