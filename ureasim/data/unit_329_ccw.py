"""Unit 329's tempered cooling water on 322E003's shell — 329P006 A/B, FIC-329409, TIC-329005.

What this is
------------
The closed loop that takes the carbamate-formation exotherm out of the HP scrubber: 329P006 A/B
circulate 306 t/h through the shell, FV-329409 sets the rate on FIC-329409, and TV-329005 sets
the supply temperature on TIC-329005 by its branch through the tempered-water cooler. The
design rate, temperatures and duty are 322E003's (`data.unit_322e003`, PFD 1111 / 1112); this
module carries the two controllers V1 writes inline, with V1's plant lags.

The DCS table's tunings on their transmitters' spans (decision 10's class, applied 2026-10-07 once
the spans were read): FIC-329409's row, 0.60 and 250 s, on FT-329409's 0-500 m3/h, and
TIC-329005's, 1.50 and 300 s, on TT-329005's 0-200 C (``References/Master_PID_Tuning_Constants.md``;
Uhde's loop summaries F 329409 and T 329005, UD-MR-329-EC-0001 rev 1, PDF pages 18 and 167). V1
runs 0.08 %/(t/h) and 6 s, and 1.0 %/K and 15 s.

Source: V1 ``backend/main.py`` 4896-4911 (``SCRUB_FV409_DES_PCT`` ... ``TIC_329005_LOAD_GAIN``),
the 322E003 block of ``step_sim`` (7992-8028).
"""

from __future__ import annotations

from ureasim.data.control_valves import FV_329409, design_stroke_pct
from ureasim.data.unit_322e003 import CCW_KGH_DES

__all__ = [
    "FV_329409_OP_DES_PCT", "FV_329409_TRIM_OP_DES_PCT", "TV_329005_OP_DES_PCT",
    "FT_329409_SPAN_M3H", "FT_329409_RHO_KGM3", "FT_329409_SPAN_TH",
    "FIC_329409_KC_TABLE", "FIC_329409_TAU_S", "FIC_329409_KC", "FIC_329409_TI_S",
    "TT_329005_SPAN_K", "TIC_329005_KC_TABLE",
    "TIC_329005_TAU_S", "TIC_329005_KC", "TIC_329005_TI_S", "TIC_329005_LOAD_GAIN_K",
    "TIC_329005_T_SS_MIN_C",
]

#: FV-329409's and TV-329005's design strokes [%]. Source: V1 ``SCRUB_FV409_DES_PCT``,
#: ``SCRUB_TV005_DES_PCT``.
FV_329409_OP_DES_PCT = 60.0
TV_329005_OP_DES_PCT = 50.0

#: FV-329409 on its vendor's trim (decision 108's class, decided 2026-10-15): Metso's DN 150
#: Neldisc, Cv 1240 (`data.control_valves.FV_329409`, item 25), its design stroke where its normal
#: case passes 322E003's 306 t/h at the sheet's 95 C, 46.85 % (the case's 312 m3/h at 46.4 %). V1
#: runs it linear from 60 % above, which the equivalence harness keeps.
FV_329409_TRIM_OP_DES_PCT = design_stroke_pct(FV_329409, CCW_KGH_DES)

#: FT-329409's calibrated range [m3/h] and the circulating water's density there [kg/m3], and the
#: range on the loop's t/h basis. Source: Uhde's loop summary F 329409 (UD-MR-329-EC-0001 rev 1,
#: PDF page 18): volume flow, range 0 to 500 m3/h, normal 306, 972 kg/m3 at 80 C and 9.0 bar a.
FT_329409_SPAN_M3H = 500.0
FT_329409_RHO_KGM3 = 972.0
FT_329409_SPAN_TH = FT_329409_SPAN_M3H * FT_329409_RHO_KGM3 / 1000.0

#: FIC-329409: the flow's plant lag [s] (the circulation pumps are fast), the DCS table's gain, the
#: reverse-acting velocity gain on the span [% per t/h, on the loop's t/h PV], 0.1235, and the
#: table's integral time [s]. Decision 10's class, applied 2026-10-07; V1 runs 0.08 and 6 s.
#: Source: V1 ``FIC_329409_TAU_S``; the table's row (``Master_PID_Tuning_Constants.md``).
FIC_329409_TAU_S = 3.0
FIC_329409_KC_TABLE = 0.60
FIC_329409_KC = FIC_329409_KC_TABLE * 100.0 / FT_329409_SPAN_TH
FIC_329409_TI_S = 250.0

#: TT-329005's calibrated range [K]. Source: Uhde's loop summary T 329005 (UD-MR-329-EC-0001 rev 1,
#: PDF page 167): 0 to 200 C, normal 80 C.
TT_329005_SPAN_K = 200.0

#: TIC-329005: the supply temperature's plant lag [s] (the tempered water's thermal mass), the DCS
#: table's gain, the direct-acting velocity gain on the span [% per K], 0.75, and the table's
#: integral time [s]. Decision 10's class, applied 2026-10-07; V1 runs 1.0 and 15 s.
#: Source: V1 ``TIC_329005_TAU_S``; the table's row (``Master_PID_Tuning_Constants.md``).
TIC_329005_TAU_S = 25.0
TIC_329005_KC_TABLE = 1.50
TIC_329005_KC = TIC_329005_KC_TABLE * 100.0 / TT_329005_SPAN_K
TIC_329005_TI_S = 300.0

#: The returning water's warming per unit of the reactor's load departure [K]: the supply
#: temperature's steady target rises by this times ((s - 1) + delta_X), zero at design.
#: Source: V1 ``TIC_329005_LOAD_GAIN``.
TIC_329005_LOAD_GAIN_K = 10.0

#: The floor of the supply temperature's steady target [deg C]. Source: V1's literal 20.0 in
#: ``step_sim`` 8019-8021.
TIC_329005_T_SS_MIN_C = 20.0
