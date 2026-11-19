"""The low-level stops of four pump pairs: AC4's motor-control interlock on their suction vessels.

What this holds
---------------
Uhde's application software (AC4, UD-MR-G00-FF-0004, one MOTCON block a machine, read on the page
images; As-Built §CXIX.2) wires each of these pairs' process interlock IC2 to a level below its L2:

    328P002A / B   reflux pump              LT-328501 < L2   (PDF pages 103 / 104)
    328P006A / B   hydrolyser feed pump     LT-328503 < L2   (pages 107 / 108)
    328P007A / B   process condensate pump  LT-328505 < L2   (pages 109 / 110)
    335P001A / B   urea feed pump           LY-324501 < L2   (pages 230 / 231)

The L2 values are DCS database entries that neither archive holds. The values below are
the process engineer's stand-in of 2026-11-15 (decision 217): every limit is LT-323503's L2, 5 %, the
one such limit read back from the plant DCS (decision 103), with the 2-unit hysteresis decision 111's
class gives an analogue limit whose hysteresis the archive does not give (323P008's B-96 stand-in).
The process engineer signed them off as built on 2026-11-16 (decision 242); a readback (checklist rows
17 to 20) would replace them.

Process utility
---------------
Each stop protects a pump from running its suction vessel dry: below the limit the pair delivers
nothing, and it delivers again once the level has recovered past the limit by the hysteresis.
LY-324501 carries LT-324501's LRV floor (decision 252): at 324F003's vacuum it reads no lower than
about 20.7 %, so 335P001's stop acts only once the vacuum has broken above 0.269 bar a, and it
releases the pumps again when the vacuum recovers.
"""

from __future__ import annotations

from types import MappingProxyType

#: L2 [% of the transmitter's span] below which AC4 stops the pair the tag protects. source = the
#: process engineer's stand-in of 2026-11-15 (decision 217): LT-323503's DCS L2, 5 %, read back on
#: 2026-10-13 (decision 103); signed off as built (decision 242).
L2_PCT = MappingProxyType({
    "LT-328501": 5.0,
    "LT-328503": 5.0,
    "LT-328505": 5.0,
    "LY-324501": 5.0,
})

#: The limit's hysteresis [% of span]: a pair stopped below L2 delivers again at L2 + 2 %. source =
#: decision 111's class (an analogue limit with no hysteresis in the archive carries a stated 2-unit
#: stand-in), as 323P008's stop carries it (B-96, decided 2026-10-15).
L2_HYST_PCT = 2.0

__all__ = ["L2_PCT", "L2_HYST_PCT"]
