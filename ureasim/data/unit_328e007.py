"""328E007 — the desorber heat exchanger: the design basis.

328E007 is the plate exchanger that preheats the desorbers' feed. Its cold side takes PFD 735,
the ammonia water 328P003 draws from 328D003's compartment II, and sends it on as 738 to
328C002; its hot side takes 739, the purified condensate LV-328505 lets out of 328C004's
bottoms, and sends it on as 740 to 328P007, 328E001 and the battery limit.

    735 (56 C) --cold--> 328E007 --> 738 (114 C) --> 328C002
    739 (143 C) --hot--> 328E007 --> 740 (89 C) --> 742 / 741

Sources
-------
* ``Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md`` — streams 735, 738, 739 and 740
  (PFD-22): 31 114 kg/h from 56 C to 114 C, 33 724 kg/h from 143 C to 89 C.
* V1 ``backend/main.py``, the 328E007 block (2007-2021, "AUDIT C10") and ``R328_C004_T`` (1380).
  Each value carries its provenance.

Not used: the datasheet case in ``References/328P003, ..., 328E007, 328E001 Datasheets.md``
(UD-AU-328-EC-0007: 10.58 m2, 25 plates, 2649 kW on 44 252 kg/h from 60.4 C to 111.3 C against
45 479 kg/h from 143.0 C to 93.5 C) is the exchanger's rating case, not the 1750 MTPD design
point, and V1 anchors on the PFD. V1's ``R328_E007_EPS = 0.6667`` is dead in V1 (defined, never
read) and is not ported; the effectiveness below is its exact form.
"""

from __future__ import annotations

from ureasim.data.unit_328d003 import C004_M739_DES_KGH, D003_TII_C, M735_DES_KGH

#: The hot inlet at design [deg C]: 328C004's bottoms, PFD 739 at 143 C — V1 ``R328_C004_T``,
#: the desorber-II bulk temperature the exchanger reads.
E007_T739_DES_C = 143.0

#: The two outlets at design [deg C], PFD 738 and 740 — V1 ``R328_E007_TC_OUT`` and
#: ``R328_E007_TH_OUT``, the design anchors.
E007_T738_DES_C = 114.0
E007_T740_DES_C = 89.0

#: The cold side's temperature effectiveness [-], back-solved from the design temperatures —
#: V1 ``R328_E007_EPS_T``: (114 - 56) / (143 - 56) = 58/87 = 0.66667. The cold inlet is compartment
#: II's temperature, which 735 leaves at.
E007_EPS_T = (E007_T738_DES_C - D003_TII_C) / (E007_T739_DES_C - D003_TII_C)

#: The shell loss in flow-temperature units [kg.K/h], back-solved from the design state — V1
#: ``R328_E007_LOSS_DT``: the hot duty the cold side does not receive,
#: 33 724 x (143 - 89) - 31 114 x (114 - 56) = 16 484 kg.K/h, 18.32 kW at cp 4.0.
E007_LOSS_DT_KGKH = (C004_M739_DES_KGH * (E007_T739_DES_C - E007_T740_DES_C)
                     - M735_DES_KGH * (E007_T738_DES_C - D003_TII_C))

#: The shell loss V1 books in unit 328's energy diagnostic [kW] — V1 ``R328_E007_LOSS``, a literal
#: with no source; the back-solve above gives 18.32 kW.
E007_LOSS_KW = 18.3

#: The numerical floor on the hot flow in the hot outlet's balance [kg/h], V1's literal.
E007_HOT_FLOW_FLOOR_KGH = 1e-6

__all__ = [
    "E007_T739_DES_C", "E007_T738_DES_C", "E007_T740_DES_C", "E007_EPS_T", "E007_LOSS_DT_KGKH",
    "E007_LOSS_KW", "E007_HOT_FLOW_FLOOR_KGH",
]
