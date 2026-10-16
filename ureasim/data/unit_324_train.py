"""Unit 324's vacuum train — the design basis of the four condensers in series and their ejectors.

What this equipment is
----------------------
The two evaporation stages' overheads condense in four shell-and-tube surface condensers, the
inert gas and what it still holds pulled on by three steam-jet ejectors:

    324F001 (705) + 323F010 (790) --703--> 324E002 --706--> 324F002 (+924) --708--> 323C005
    324F003 --709--> 324E005 --712--> 324F004 (+927) --714--> 324E006 --715--> 324F005 (+929)
                                                         --717--> 324E007 --722--> atmosphere
    condensates 719 (324E002), 720 (324E005), 721 (324E006), 759 (324E007) --> 328D003 I

The motive steam comes off the LP header through two hand valves: HV-329605 (HIC-329605) to
324F002, and HV-329606 (HIC-329606) to 324F004 and 324F005 together (``References/Mapping of
Evaporation Section.md``, lines 15 and 35). The archive knows no 324F006 or 324F007: the vendor
TOC (UD-AM-G00-AB-0022), the P&IDs and the PFD carry 324F001 to 324F005 only.

Sources
-------
* ``Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md`` (PFD-21): the vapour rows 703, 705,
  709 and 790, and the LP steam rows 924, 927 and 929 (390, 1220 and 180 kg/h at 4.1 bar a and
  146 C).
* Flowserve's calculation sheets, UD-MR-G00-DZ-0048-003, Pos. 66 (HV-329605) and Pos. 67
  (HV-329606): the trims and their xT on the normal cases (`data.control_valves`).
* Körting's and Uhde's ejector duty points: every nozzle at 4.1 bar a on its duty
  (`data.unit_324.EJECTOR_DUTIES`).
* V1 ``backend/main.py`` ``vacuum_train_324`` (3987-4048) and its call (10036-10063): the rows'
  literals, V1's linear motive valves (``R324_HV9605_SPAN``, ``R324_F004_MOTIVE_DES`` x HIC-329606 /
  ``R324_HIC9606_DES_PCT``).
"""

from __future__ import annotations

from ureasim.data.control_valves import HV_329605, HV_329606, design_stroke_pct
from ureasim.data.unit_324 import (
    EJECTOR_DUTIES,
    F002_MOTIVE_DES_KGH,
    F004_MOTIVE_DES_KGH,
    F005_MOTIVE_DES_KGH,
    VACUUM_CONDENSERS,
)
from ureasim.data.unit_329 import P_LP_BARA

# ======================================================================================
# The rows the train's departures are taken from [kg/h]
# ======================================================================================

#: PFD 703, 324E002's inlet: 705 and 790 mixed (V1's literal 26840.0).
PFD_703_KGH = VACUUM_CONDENSERS["324E002"].inlet_kgh

#: PFD 705, 324F001's overhead with PFD 784's false air (V1's literal 14799.0).
PFD_705_KGH = 14799.0

#: PFD 709, 324F003's overhead with PFD 783's false air, 324E005's inlet (V1's literal 3342.0).
PFD_709_KGH = VACUUM_CONDENSERS["324E005"].inlet_kgh

#: PFD 790, 323F010's overhead through HV-323605 (V1's literal 12040.0; the pre-evaporator's own
#: model overhead at design, `unit_323.MEVAP_DES_KGH`, is 12013 kg/h, and the train reads the live
#: overhead as a departure from it).
PFD_790_KGH = 12040.0

# ======================================================================================
# The motive steam valves on their vendor trims (decision 23's class)
# ======================================================================================

#: HV-329606's design flow [kg/h]: PFD 927 and 929 together, the two ejectors on one valve
#: (handoff B-64, decided 2026-10-02, option a: the PFD's 1220 and 180 kg/h). Flowserve sized it for
#: Uhde's 1061 + 366 = 1427 kg/h on its normal case.
HV_329606_DES_KGH = F004_MOTIVE_DES_KGH + F005_MOTIVE_DES_KGH

#: The two hand valves' design strokes [%]: where their vendor trims pass the design motive on
#: their normal cases (decision 23's class, §5 rule 7) — HV-329605 PFD 924's 390 kg/h at 69.06 %,
#: HV-329606 the 1400 kg/h above at 80.16 %. V1 runs both linear from 50 %
#: (``R324_HIC9605_DES_PCT``, ``R324_HIC9606_DES_PCT``).
HV_329605_OP_DES_PCT = design_stroke_pct(HV_329605, F002_MOTIVE_DES_KGH)
HV_329606_OP_DES_PCT = design_stroke_pct(HV_329606, HV_329606_DES_KGH)

#: The motive valves' design pressures [bar a] (handoff B-73, decided 2026-10-02): upstream the LP
#: header the operators run, 4.0 bar g (handoff B-69, `unit_329.P_LP_BARA`); downstream the nozzles,
#: at the 4.1 bar a every ejector's duty puts them on its design motive (all three duties print
#: 4.1). Flowserve sized both valves 4.1 -> 3.8 bar a; on these pressures the anchored gas law
#: passes the design motive at the design stroke above.
MOTIVE_P1_DES_BARA = P_LP_BARA
MOTIVE_P2_DES_BARA = EJECTOR_DUTIES["324F002"].p_motive_bara

#: The two valves' pressure-differential ratio factors xT [-], Flowserve's on the normal cases.
HV_329605_XT = HV_329605.normal_case.xt
HV_329606_XT = HV_329606.normal_case.xt

# ======================================================================================
# 324E006's shell, the vacuum node between 324F004 and 324F005 (handoff B-66)
# ======================================================================================

#: 324E006's shell-side volume [m3], what its vacuum node integrates over (decided 2026-10-02,
#: handoff B-66). Source: Uhde's name plate, UD-AU-324-DZ-0005-008 rev. 01 (Aguilar y Salas
#: 12160-8), "Volume — shell side 0.542 m3, tube side 0.455 m3", a scan read visually. The
#: datasheet's 550 mm shell less its 250 tubes over 3.6 m gives 0.573 m3; the name plate's figure is
#: the vendor's own, baffles and nozzles counted (decision 33's class).
E006_SHELL_VOL_M3 = 0.542

__all__ = [
    "PFD_703_KGH", "PFD_705_KGH", "PFD_709_KGH", "PFD_790_KGH", "HV_329606_DES_KGH",
    "HV_329605_OP_DES_PCT", "HV_329606_OP_DES_PCT", "MOTIVE_P1_DES_BARA", "MOTIVE_P2_DES_BARA",
    "HV_329605_XT", "HV_329606_XT", "E006_SHELL_VOL_M3",
]
