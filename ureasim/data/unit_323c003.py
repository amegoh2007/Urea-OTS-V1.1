"""323C003's relief and the stripper gas it receives: the design basis (handoff A-16).

What this equipment is
----------------------
323C003, the rectifying column of unit 323's first stage, takes the 322E001 stripper bottoms
through LV-322501. When the stripper's bottom seal is lost, LV-322501 passes HP stripper gas as
well, and that gas reaches the column's head space with the letdown flash. Two spring-loaded
safety valves on the column, SV32351 and SV32352, are sized for exactly that case ("Failure of
LV 322501", 60 t/h of carbamate gas).

The column's own design basis — its holdup, its heater, its two-source pressure law — is
`ureasim.data.unit_323`; this module holds only what the relief and the blow-through need.

Sources
-------
* Uhde's technical specifications UD-RL-323-EC-0001 and -0002 (SV32351, SV32352; P&ID 103/1, line
  GCB4-323201-EG07D): set 5.0 bar g on the sheets' 1.010 bar a, 2.0 bar a back pressure.
* Sempell's orifice selection, UD-RL-G00-DZ-0002-001 page 3: orifice T, 20 106.2 mm2, alpha_w
  0.917, 72 273.6 kg/h certified on carbamate gas of molar mass 25.07, k 1.010, Z 1.00 at 125 C
  and the set pressure plus 10 %; 10 % blowdown.
* ``Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md`` — stream 305, the column's overhead
  gas: average molar weight 24.92 at 4.1 bar a and 119 C.

Every relief value is read through `ureasim.data.relief_devices`, which carries the documents.
"""

from __future__ import annotations

from ureasim.data.relief_devices import RELIEF_DEVICES, RELIEF_SIZING

# ======================================================================================
# SV32351 and SV32352, the column's relief (decided 2026-10-03, handoff A-16)
# ======================================================================================

#: SV32351 and SV32352, alike: set 5.0 bar g, 6.01 bar a, on the sheets' 1.010 bar a. They reseat
#: 10 % of set below, at 5.51 bar a (Sempell UD-RL-G00-DZ-0002-001 page 3).
SV32351_SET_BARA = RELIEF_DEVICES["SV32351"].set_bara
SV32351_RESEAT_BARA = RELIEF_SIZING["SV32351"].reseat_bara(RELIEF_DEVICES["SV32351"])

#: Each one's certified capacity [kg/h], 72 273.6, on orifice T: carbamate gas of molar mass
#: 25.07, k 1.010 and Z 1.00 at 125 C and 6.51 bar a, the set pressure plus 10 % [bar a]. Two
#: valves, set alike, lift and reseat together.
SV32351_CAP_KGH = RELIEF_SIZING["SV32351"].capacity_kgh
SV32351_P_REL_BARA = RELIEF_SIZING["SV32351"].relieving_bara(RELIEF_DEVICES["SV32351"])
SV32351_T_REL_K = RELIEF_SIZING["SV32351"].t_c + 273.15
SV32351_MW_REL = RELIEF_SIZING["SV32351"].mw
SV32351_Z_REL = RELIEF_SIZING["SV32351"].z
SV32351_K = RELIEF_SIZING["SV32351"].k
SV32351_COUNT = 2

# ======================================================================================
# The gas the column's head space holds
# ======================================================================================

#: Molar mass of the column's own overhead gas [kg/kmol]: PFD 305, average molar weight 24.92.
#: What the valves relieve of the gas the column raises itself; the stripper's blow-through is
#: relieved at the stripper top vapour's own live molar mass.
MW_305 = 24.92

__all__ = [
    "SV32351_SET_BARA", "SV32351_RESEAT_BARA", "SV32351_CAP_KGH", "SV32351_P_REL_BARA",
    "SV32351_T_REL_K", "SV32351_MW_REL", "SV32351_Z_REL", "SV32351_K", "SV32351_COUNT", "MW_305",
]
