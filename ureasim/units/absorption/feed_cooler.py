"""322E006 — the LP absorber feed cooler: 744 cooled against cooling water into 755.

What this models
----------------
The plate exchanger between 322P002 and 322C001's lower bed. PFD 744 leaves 328D003's
compartment I at the tank's live temperature, crosses the hot side and reaches the absorber as
755; cooling water crosses the cold side counter-current. 755's temperature is the absorber's
only cooling, so this exchanger sets how much ammonia the lower bed can hold back: a hotter wash
raises the liquor's back-pressure and the slip to atmosphere.

    744 (compartment I) --hot--> 322E006 --> 755 --> 322C001
    cooling water supply --cold--> 322E006 --> cooling water return

Decided by the process engineer on 2026-10-01 (handoff B-54, option b). V1 models no 322E006:
it fixes 755 at 40 C whatever 744's temperature, the cooling water or the load, so a cooling-
water failure could not be trained. The rewrite ports the exchanger on its datasheet UA.

Equations
---------
Counter-current effectiveness-NTU, on the design-anchored UA and the datasheet's heat
capacities:

    C_h = m_744 cp_h / 3600,  C_c = m_cw cp_c / 3600                       [kW/K]
    NTU = UA / C_min,  Cr = C_min / C_max
    eps = (1 - exp(-NTU (1 - Cr))) / (1 - Cr exp(-NTU (1 - Cr)))          Cr < 1
        = NTU / (1 + NTU)                                                    Cr = 1
    Q   = eps C_min (T_744 - T_cw)
    T_755 = T_744 - Q / C_h,   T_cw,out = T_cw + Q / C_c

Steady state each tick: the plates hold about 20 kg of ammonia water (the datasheet's 590 kg
filled against 570 dry), under 3 s of 744.

The design anchor
-----------------
The cooling water enters at its 30 C supply and crosses the plates at PFD 28's 14 t/h, streams
1010 and 1011 (decided 2026-10-22, decision 151) — the flow the session-31 port back-solved,
10 374 kg/h on the datasheet UA, before PFD 28 was read. On the datasheet's 30.776 kW/K that water
would bring the PFD's 744 to 39.23 C, not the PFD's 40, so the conductance is the quantity
back-solved: the UA that takes the PFD's 744 to exactly 40 C on PFD 28's water,
`E006_UA_DES_KW_K`, 20.448 kW/K, two-thirds of the datasheet's, which stays the rated surface's
margin (decision 44's class). The water returns at 39.05 C against PFD 28's rounded 40.

Source: Uhde UD-AU-322-EC-0012 (`ureasim.data.unit_322e006`); PFD 744 and 755; PFD 28
(UD-VT-329-FB-0004), streams 1010 and 1011.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ureasim.data.unit_322e006 import (
    E006_CP_CW,
    E006_CP_HOT,
    E006_M744_DES_KGH,
    E006_M_CW_PFD_KGH,
    E006_T744_DES_C,
    E006_T755_DES_C,
    E006_T_CW_SUPPLY_C,
)

#: The bracket the design UA is searched in [kW/K], and the bisection's iteration count: a
#: bracket of 1e3 halved 200 times is below one ulp of any conductance in it.
UA_BRACKET_KW_K = (1.0e-3, 1.0e3)
UA_BISECTIONS = 200


@dataclass(frozen=True)
class FeedCoolerResult:
    """What 322E006 publishes on one tick."""

    #: 755 to 322C001 [deg C], and the cooling-water return [deg C].
    t_755_c: float
    t_cw_out_c: float
    #: The duty [kW], positive when 744 is cooled.
    q_kw: float
    #: The effectiveness [-] on the side with the smaller capacity flow.
    eps: float
    #: The flows it was called with [kg/h].
    m_744_kgh: float
    m_cw_kgh: float


def effectiveness(ntu: float, cr: float) -> float:
    """Counter-current exchanger effectiveness [-] for ``NTU`` and capacity ratio ``Cr``.

    Process utility
    ---------------
    The fraction of the largest possible duty the plates deliver: it falls as the cooling water
    is throttled (NTU on the water side drops) and as the plates foul (UA drops), which is what
    warms 755 and loads the absorber.

    Equation
    --------
        eps = (1 - exp(-NTU (1 - Cr))) / (1 - Cr exp(-NTU (1 - Cr)))      Cr < 1
            = NTU / (1 + NTU)                                               Cr = 1
    """
    if cr >= 1.0:
        return ntu / (1.0 + ntu)
    e = math.exp(-ntu * (1.0 - cr))
    return (1.0 - e) / (1.0 - cr * e)


def feed_cooler_322e006(m_744_kgh: float, t_744_c: float, m_cw_kgh: float,
                        t_cw_c: float = E006_T_CW_SUPPLY_C,
                        ua_kw_k: float | None = None) -> FeedCoolerResult:
    """322E006 on one tick: 744 in at compartment I's temperature, 755 out to 322C001.

    Process utility
    ---------------
    The absorber's wash temperature. With the cooling water lost, 755 arrives at 744's own
    temperature; with 322P002 stopped there is no 755 and the exchanger does nothing.

    Arguments
    ---------
    m_744_kgh, t_744_c
        744 from 328D003's compartment I through 322P002 [kg/h, deg C].
    m_cw_kgh, t_cw_c
        The cooling water through the plates [kg/h] and its supply temperature [deg C].
    ua_kw_k
        The conductance [kW/K]; None is the design-anchored `E006_UA_DES_KW_K`.
    """
    c_h = max(m_744_kgh, 0.0) * E006_CP_HOT / 3600.0
    c_c = max(m_cw_kgh, 0.0) * E006_CP_CW / 3600.0
    c_min, c_max = min(c_h, c_c), max(c_h, c_c)
    if c_min <= 0.0:
        # No flow on one side: nothing crosses the plates.
        return FeedCoolerResult(t_755_c=t_744_c, t_cw_out_c=t_cw_c, q_kw=0.0, eps=0.0,
                                m_744_kgh=m_744_kgh, m_cw_kgh=m_cw_kgh)
    ua = E006_UA_DES_KW_K if ua_kw_k is None else ua_kw_k
    eps = effectiveness(ua / c_min, c_min / c_max)
    q = eps * c_min * (t_744_c - t_cw_c)
    return FeedCoolerResult(t_755_c=t_744_c - q / c_h, t_cw_out_c=t_cw_c + q / c_c, q_kw=q,
                            eps=eps, m_744_kgh=m_744_kgh, m_cw_kgh=m_cw_kgh)


def _design_ua_kw_k() -> float:
    """The conductance that takes the PFD's 744 to exactly the PFD's 755 on PFD 28's cooling
    water and the 30 C supply [kW/K].

    755's temperature falls monotonically as the conductance rises, so it is bisected and then
    stepped one float at a time until 755 reads the PFD's 40 C exactly, so the design point
    holds to the bit."""
    def t_out(ua: float) -> float:
        return feed_cooler_322e006(E006_M744_DES_KGH, E006_T744_DES_C, E006_M_CW_DES_KGH,
                                   ua_kw_k=ua).t_755_c

    lo, hi = UA_BRACKET_KW_K
    for _ in range(UA_BISECTIONS):
        mid = 0.5 * (lo + hi)
        if t_out(mid) > E006_T755_DES_C:
            lo = mid
        else:
            hi = mid
    ua = hi
    for _ in range(64):
        t = t_out(ua)
        if t == E006_T755_DES_C:
            return ua
        ua = math.nextafter(ua, math.inf if t > E006_T755_DES_C else -math.inf)
    raise ValueError("no conductance takes 744 to 755 exactly")


#: The design cooling-water flow [kg/h]: PFD 28's 14 t/h (decision 151).
E006_M_CW_DES_KGH = E006_M_CW_PFD_KGH

#: The design-anchored conductance [kW/K], 20.448: back-solved on PFD 28's water (see the module
#: docstring); the datasheet's 30.776 is `E006_UA_KW_K`.
E006_UA_DES_KW_K = _design_ua_kw_k()

#: 322E006 at the design point: PFD 744 to PFD 755.
DESIGN = feed_cooler_322e006(E006_M744_DES_KGH, E006_T744_DES_C, E006_M_CW_DES_KGH)


__all__ = [
    "UA_BRACKET_KW_K", "UA_BISECTIONS", "FeedCoolerResult", "effectiveness",
    "feed_cooler_322e006", "E006_M_CW_DES_KGH", "E006_UA_DES_KW_K", "DESIGN",
]
