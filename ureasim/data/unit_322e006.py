"""322E006 — the LP absorber feed cooler: the design basis.

What this equipment is
----------------------
322E006 is the bolted plate exchanger that cools the LP absorber's main wash. 322P002 draws PFD
744 from 328D003's compartment I and sends it through the hot side, which leaves as PFD 755 to
322C001's lower bed; cooling water takes the heat on the cold side.

    744 (44 C) --hot--> 322E006 --> 755 (40 C) --> 322C001 lower bed
    cooling water (30 C) --cold--> 322E006 --> return

Its outlet temperature is the absorber's only cooling: 322C001 has no cooling water of its own,
and the heat of absorption leaves in the liquor as sensible heat against 755.

Sources
-------
* Uhde technical specification UD-AU-322-EC-0012 rev 00 (05.08.04), ``References/Datasheets/
  322E006 Database.pdf`` (scanned, read from the page image), page 2, "Design data sheet for
  plate heat ex. (DDS), operating case 1": surface 6.44 m2, 16 plates (frame for 10 % more),
  heat duty 222 kW; fluid 1 ammonia water, 38 200 kg/h, 45.00 -> 40.00 C, cp 1.003 kcal/(kg K);
  fluid 2 "cooling water return", 19 150 kg/h, 30.00 -> 40.00 C, cp 0.998 / 0.996 kcal/(kg K);
  20.0 % excess heat-exchange area on each side; the line for the heat-transfer coefficient is
  blank.
* ``Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md``, PFD-22: 744, 31 478 kg/h at 44 C;
  755, 31 478 kg/h at 40 C — the design point, which the datasheet's case 1 rates with margin.

Decided by the process engineer on 2026-10-01 (handoff B-54, option b): V1 holds 755 at a
fixed 40 C and models no 322E006; the rewrite ports the exchanger on its datasheet UA with the
cooling water at its 30 C supply.
"""

from __future__ import annotations

import math

from ureasim.core.units_of_measure import KJ_PER_KCAL
from ureasim.data.unit_322c001 import C001_T_755_C
from ureasim.data.unit_328d003 import D003_TI_C, M744_DES_KGH

#: The heat-transfer surface [m2] and the rated duty [kW] (DDS lines 3 and 78).
E006_AREA_M2 = 6.44
E006_Q_DS_KW = 222.0

#: The rated terminal temperatures [deg C] (DDS line 55): ammonia water 45 -> 40, cooling water
#: 30 -> 40.
E006_T_HOT_IN_DS_C = 45.0
E006_T_HOT_OUT_DS_C = 40.0
E006_T_CW_IN_DS_C = 30.0
E006_T_CW_OUT_DS_C = 40.0

#: The rated flows [kg/h] (DDS line 49): ammonia water 38 200, cooling water 19 150.
E006_M_HOT_DS_KGH = 38200.0
E006_M_CW_DS_KGH = 19150.0

#: Heat capacities [kJ/(kg K)] (DDS line 59): the ammonia water's 1.003 kcal/(kg K); the
#: cooling water's mean of its inlet and outlet values, 0.998 and 0.996.
E006_CP_HOT = 1.003 * KJ_PER_KCAL
E006_CP_CW = 0.5 * (0.998 + 0.996) * KJ_PER_KCAL

#: The rated log-mean temperature difference [K], counter-current on the DDS's terminal
#: temperatures: (10 - 5) / ln(10 / 5) = 7.2135.
E006_LMTD_DS_K = (((E006_T_HOT_OUT_DS_C - E006_T_CW_IN_DS_C)
                   - (E006_T_HOT_IN_DS_C - E006_T_CW_OUT_DS_C))
                  / math.log((E006_T_HOT_OUT_DS_C - E006_T_CW_IN_DS_C)
                             / (E006_T_HOT_IN_DS_C - E006_T_CW_OUT_DS_C)))

#: The datasheet UA [kW/K]: the rated duty over the rated LMTD, 222 / 7.2135 = 30.776 — U = 4779
#: W/(m2 K) on the full 6.44 m2, the area that carries the 20 % fouling margin.
E006_UA_KW_K = E006_Q_DS_KW / E006_LMTD_DS_K

#: The cooling-water supply temperature [deg C]: the DDS's 30.00 C inlet.
E006_T_CW_SUPPLY_C = E006_T_CW_IN_DS_C

#: The design point: PFD 744 in, 31 478 kg/h at compartment I's 44 C, and PFD 755 out at 40 C.
E006_M744_DES_KGH = M744_DES_KGH
E006_T744_DES_C = D003_TI_C
E006_T755_DES_C = C001_T_755_C

__all__ = [
    "E006_AREA_M2", "E006_Q_DS_KW", "E006_T_HOT_IN_DS_C", "E006_T_HOT_OUT_DS_C",
    "E006_T_CW_IN_DS_C", "E006_T_CW_OUT_DS_C", "E006_M_HOT_DS_KGH", "E006_M_CW_DS_KGH",
    "E006_CP_HOT", "E006_CP_CW", "E006_LMTD_DS_K", "E006_UA_KW_K", "E006_T_CW_SUPPLY_C",
    "E006_M744_DES_KGH", "E006_T744_DES_C", "E006_T755_DES_C",
]
