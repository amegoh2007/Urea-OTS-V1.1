"""Time constants of the synthesis loop's displayed indicators — V1's section 6.

What these are
--------------
V1 relaxes ten of the synthesis loop's published indications toward their process values, so an
upstream step ramps an indicator instead of snapping it in one 0.1 s tick: the temperatures the
loop's liquid holdups and shell metal carry (TT-322012, TT-322013, TT-323001, TT-322010,
TT-322002), the off-gas line's thermowells (TT-322011 either side of HV-322604), the tempered
water's return (TT-329125), the HPCC's bubble-point pressure (PI-322E002) and the on-line N/C
analyser (AT-322701). Nothing in the plant reads the lagged values; they are what the consoles
show. TT-322004's lag, on the same 180 s, is carried by 322E001's sump
(`ureasim.units.synthesis.stripper_sump`), where its process belongs.

Source
------
V1 ``backend/main.py`` lines 5927-5934 (the ``*_TAU_S`` block, each with V1's own reason quoted
below) and ``step_sim`` section 6, lines 8183-8204. No reference document carries these: they are
V1's, taken under ``CLAUDE.md`` §4 rule 3 with V1's provenance comments.
"""

from __future__ import annotations

from ureasim.data.unit_322e001 import T_STRIPPER_TAU_S
from ureasim.data.unit_322e002 import P_DES_BARA as HPCC_P_DES_BARA

__all__ = [
    "EJ_T_TAU_S", "STRIP_T_TAU_S", "HPCC_T_TAU_S", "HPCC_P_TAU_S", "SCRUB_T_TAU_S",
    "OFFGAS_T_TAU_S", "CCW_T_TAU_S", "AT_322701_TAU_S", "HPCC_P_DISPLAY_MAX_BARA",
]

#: 322F001's discharge and suction-side carbamate inventory, thermal mass [s]; TT-322012.
#: Source: V1 `main.py` EJ_T_TAU_S.
EJ_T_TAU_S = 120.0

#: 322E001's liquid holdup (falling film and bottom sump) and HP shell metal [s]; TT-322013 and
#: TT-323001. Source: V1 `main.py` STRIP_T_TAU_S, the port's `unit_322e001.T_STRIPPER_TAU_S`.
STRIP_T_TAU_S = T_STRIPPER_TAU_S

#: 322E002's carbamate liquid product and tube-bundle metal, slow [s]; TT-322010.
#: Source: V1 `main.py` HPCC_T_TAU_S.
HPCC_T_TAU_S = 240.0

#: 322E002's bubble-point synthesis pressure, the carbamate condenser's liquid holdup [s];
#: PI-322E002. Source: V1 `main.py` HPCC_P_TAU_S.
HPCC_P_TAU_S = 30.0

#: 322E003's overflow liquid pool and HP shell metal [s]; TT-322002.
#: Source: V1 `main.py` SCRUB_T_TAU_S.
SCRUB_T_TAU_S = 180.0

#: The off-gas line and HV-322604's vent thermowell, the vapour line's holdup and metal [s];
#: TT-322011 upstream and downstream of the valve. Source: V1 `main.py` OFFGAS_T_TAU_S.
OFFGAS_T_TAU_S = 120.0

#: The tempered water's shell return, matching TIC-329005's plant lag [s]; TT-329125.
#: Source: V1 `main.py` CCW_T_TAU_S.
CCW_T_TAU_S = 25.0

#: AT-322701, the on-line N/C analyser: its sample dead time and measurement lag [s].
#: Source: V1 `main.py` AT_322701_TAU_S.
AT_322701_TAU_S = 40.0

#: The ceiling on the PUBLISHED PI-322E002 [bar a]: 322E002 cannot be pressurised past what the
#: CO2, HPCC and ejector feeds deliver, 144.2 bar a; off design the melt's bubble point can compute
#: above it (221 bar a was measured at 40 % load). At design the bubble point equals it, so the
#: cap binds at equality. Source: V1 `main.py` SYN_P_MAX_BARA = HPCC_P_DES_BARA, report CP-5.
HPCC_P_DISPLAY_MAX_BARA = HPCC_P_DES_BARA
