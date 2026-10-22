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

The condensers' ratings, the vapour rows and the ejectors' vendor ratings were moved here out of
`unit_324` unchanged (2026-10-23, the housekeeping split): `unit_324` re-exports every name, and
keeps on the stages' vacuums the condensers' rows (``CONDENSER_ROWS``) and the ejectors' design
loads (``EJECTOR_DESIGN_LOADS``).

Sources
-------
* ``Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md`` (PFD-21): the vapour rows 703, 705,
  706, 709, 712, 714, 715, 717, 722 and 790 (mole per cent: V1's ``PFD_324_MASS_PCT`` is named for
  mass per cent, and its vapour rows are the PFD's mole per cent — the F-8 unit convention) and
  their molar totals; the condensers' flows and temperatures (PFD-21 / PFD-28); the LP steam rows
  924, 927 and 929 (390, 1220 and 180 kg/h at 4.1 bar a and 146 C).
* The four condensers' datasheets (``References/Sources/324E002``, ``324E005``, ``324E006``,
  ``324E007 Datasheet.pdf``): areas, tube counts, lengths, shells and tubes, as V1 transcribed them.
* Flowserve's calculation sheets, UD-MR-G00-DZ-0048-003, Pos. 66 (HV-329605) and Pos. 67
  (HV-329606): the trims and their xT on the normal cases (`data.control_valves`).
* Körting's and Uhde's ejector duty points (UD-AU-324-DZ-0009-005, UD-AU-324-DZ-0007-006): every
  nozzle at 4.1 bar a on its duty (``EJECTOR_DUTIES``).
* V1 ``backend/main.py`` 3797-3910 (``CW_CP_KJKG_K``, ``_vacuum_condenser_spec``,
  ``VACUUM_CONDENSERS``, ``PFD_324_MASS_PCT``, ``_VAC_PFD_KMOLH``, ``_VAC_AIR_*``),
  ``vacuum_train_324`` (3987-4048) and its call (10036-10063): the rows' literals, V1's linear
  motive valves (``R324_HV9605_SPAN``, ``R324_F004_MOTIVE_DES`` x HIC-329606 /
  ``R324_HIC9606_DES_PCT``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ureasim.core.stream import MW_COMP
from ureasim.data.control_valves import HV_329605, HV_329606, design_stroke_pct
from ureasim.data.unit_323c005 import PFD_703_KMOLH, PFD_703_MOL_PCT
from ureasim.data.unit_329 import P_LP_BARA

# ======================================================================================
# The cooling water
# ======================================================================================

#: The cooling water's heat capacity [kJ/(kg K)], back-solved from the largest, best-resolved
#: node: 324E002, 18.46 MW = 1591 t/h x cp x (40 - 30) K; the other three duties round to 1.93,
#: 1.21 and 0.13 MW on it (PFD-28; V1 ``CW_CP_KJKG_K``).
CW_CP_KJKG_K = 18_460.0 * 3600.0 / (1_591_000.0 * 10.0)


def lmtd_countercurrent(hot_in_c: float, hot_out_c: float, cold_in_c: float,
                        cold_out_c: float) -> float:
    """Counter-current log-mean temperature difference [K], zero across a crossed or touching end.

    Process utility
    ---------------
    The rating basis of each condenser's design duty, as V1 states it beside its datasheet.
    Source: V1 ``main.py`` ``lmtd_countercurrent`` (3788).
    """
    dt_hot_end = hot_in_c - cold_out_c
    dt_cold_end = hot_out_c - cold_in_c
    if dt_hot_end <= 0.0 or dt_cold_end <= 0.0:
        return 0.0
    if math.isclose(dt_hot_end, dt_cold_end, rel_tol=0.0, abs_tol=1e-12):
        return 0.5 * (dt_hot_end + dt_cold_end)
    return (dt_hot_end - dt_cold_end) / math.log(dt_hot_end / dt_cold_end)


@dataclass(frozen=True)
class CondenserRating:
    """One vacuum condenser at design (V1 ``_vacuum_condenser_spec``): its PFD flows [kg/h] and
    temperatures [deg C], its cooling water [kg/h, deg C], the rated duty [kW], LMTD [K] and UA
    [kW/K] the cooling water gives, and its datasheet geometry [m2, -, mm]."""

    tag: str
    inlet_kgh: float
    condensate_kgh: float
    vent_kgh: float
    hot_in_c: float
    hot_out_c: float
    cw_flow_kgh: float
    cw_in_c: float
    cw_out_c: float
    area_m2: float
    tube_count: int
    tube_length_mm: float
    shell_id_mm: float
    tube_od_mm: float
    tube_wall_mm: float

    @property
    def q_kw(self) -> float:
        return self.cw_flow_kgh / 3600.0 * CW_CP_KJKG_K * (self.cw_out_c - self.cw_in_c)

    @property
    def lmtd_k(self) -> float:
        return lmtd_countercurrent(self.hot_in_c, self.hot_out_c, self.cw_in_c, self.cw_out_c)

    @property
    def ua_kw_k(self) -> float:
        return self.q_kw / self.lmtd_k


#: The four condensers (V1 ``VACUUM_CONDENSERS``): the operating flows and temperatures are the
#: PFD-21 / PFD-28 anchors, the geometry the datasheets'. 324E006 / 324E007 have no vendor process
#: case, so no process value is inferred from their blank sheets.
VACUUM_CONDENSERS = {
    "324E002": CondenserRating("324E002", 26840.0, 26768.0, 72.0, 116.0, 45.0,
                               1_591_000.0, 30.0, 40.0, 1079.0, 2329, 5900.0, 1850.0, 25.0, 1.6),
    "324E005": CondenserRating("324E005", 3342.0, 2758.0, 584.0, 140.0, 40.0,
                               415_000.0, 30.0, 34.0, 187.0, 486, 4900.0, 925.0, 25.0, 1.6),
    "324E006": CondenserRating("324E006", 1804.0, 1763.0, 41.0, 104.0, 41.0,
                               208_000.0, 30.0, 35.0, 56.5, 250, 3600.0, 550.0, 20.0, 2.0),
    "324E007": CondenserRating("324E007", 221.0, 190.0, 31.0, 120.0, 55.0,
                               23_000.0, 30.0, 35.0, 11.0, 70, 2500.0, 324.0, 20.0, 2.0),
}

# ======================================================================================
# The vapour rows
# ======================================================================================

#: The PFD's vapour rows on the vacuum train, mole per cent (V1 ``PFD_324_MASS_PCT``): each
#: condenser's inlet and vent. 703 is 323C005's row, imported.
PFD_324_MOL_PCT = {
    "703": PFD_703_MOL_PCT,
    "706": {"CO2": 3.81, "H2O": 29.39, "N2": 38.64, "NH3": 17.91, "O2": 10.26},
    "709": {"CO2": 3.54, "H2O": 87.58, "N2": 0.33, "NH3": 7.48, "O2": 0.09, "Urea": 0.98},
    "712": {"CO2": 13.59, "H2O": 57.87, "N2": 2.14, "NH3": 25.84, "O2": 0.57},
    "714": {"CO2": 3.88, "H2O": 87.98, "N2": 0.61, "NH3": 7.37, "O2": 0.16},
    "715": {"CO2": 17.22, "H2O": 21.22, "N2": 39.48, "NH3": 11.63, "O2": 10.45},
    "717": {"CO2": 2.22, "H2O": 89.93, "N2": 5.05, "NH3": 1.49, "O2": 1.34},
    "722": {"CO2": 14.33, "H2O": 15.15, "N2": 54.44, "NH3": 1.66, "O2": 14.42},
}

#: The four inlets' molar totals [kmol/h], the rows' "Molar Flow total" (V1 ``_VAC_PFD_KMOLH``).
VAC_PFD_KMOLH = {"703": PFD_703_KMOLH, "709": 172.98, "714": 94.76, "717": 11.46}

#: The false air the vacuum controllers admit, PFD 783 / 784: its molar mass [kg/kmol] and mole
#: fractions (V1 ``_VAC_AIR_MW``, ``_VAC_AIR_FRAC``).
VAC_AIR_MW = 28.85
VAC_AIR_FRAC = {"N2": 0.7906, "O2": 0.2094}

# ======================================================================================
# The steam-jet ejectors (handoff B-57, decided 2026-10-01)
# ======================================================================================


@dataclass(frozen=True)
class EjectorDuty:
    """One steam-jet ejector as its vendor rated it: the duty point and, where the vendor gives
    them, its throats. Pressures [bar a], temperatures [deg C], flows [kg/h], the suction gas's
    molar mass [kg/kmol], diameters [mm]."""

    tag: str
    suction_kgh: float
    p_suction_bara: float
    t_suction_c: float
    mw_suction: float
    p_discharge_bara: float
    motive_kgh: float
    p_motive_bara: float
    t_motive_c: float
    nozzle_mm: float | None
    diffuser_mm: float | None


def _mw_of_mass_flows(kgh: dict) -> float:
    """The molar mass of a gas given as mass flows by species [kg/kmol], air on the PFD's own
    molar mass (`VAC_AIR_MW`)."""
    mw = dict(MW_COMP, Air=VAC_AIR_MW)
    return sum(kgh.values()) / sum(m / mw[k] for k, m in kgh.items())


def _mw_of_mole_pct(row: dict) -> float:
    """The molar mass of a PFD vapour row given in mole per cent [kg/kmol]."""
    return sum(y * MW_COMP[k] for k, y in row.items()) / sum(row.values())


#: 324F004's suction at its duty, the vendor's gas [kg/h]: Körting's operating data,
#: UD-AU-324-DZ-0009-005 (BAL 211-12/100 E, page 7 of 18, PDF page 8; scanned, read from the page
#: image): 27.4 air, 366 water vapour, 155.3 NH3, 212.3 CO2 at 40 C and 122 mbar.
F004_DUTY_GAS_KGH = {"Air": 27.4, "H2O": 366.0, "NH3": 155.3, "CO2": 212.3}

#: The three ejectors' duty points.
#:
#: * 324F004 and 324F005: Uhde's vacuum-unit stream table, UD-AU-324-DZ-0009-005 PDF page 20
#:   ("Description of vacuum unit", page 6; completed by Körting): 712, 761 kg/h maximum at 0.12
#:   bar a and 40 C; 714 at 0.35 bar a; 715, 84 kg/h at 0.33 bar a and 41 C; 717 at 1.16 bar a;
#:   927 and 929, 1061 and 366 kg/h of motive steam at 4.1 bar a and 146 C — the motive basis
#:   decided for the map, which the nozzles' choked flow backs (handoff B-57). The throats:
#:   Körting's operating data (above), diffuser 106.5 and 30.8 mm, motive nozzle orifice 24.7 and
#:   14.5 mm. 715's molar mass from its PFD row (Uhde's table gives no composition).
#: * 324F002: Körting's operating data, UD-AU-324-DZ-0007-006 page 20 (scanned, read from the
#:   page image): motive 650 kg/h at 4.1 bar a and 144.5 C; suction 94 kg/h of a 24.1 kg/kmol gas
#:   at 0.2 bar a and 45 C; discharge 1.0 bar a. No throat is given in the archive.
EJECTOR_DUTIES = {
    "324F002": EjectorDuty("324F002", 94.0, 0.2, 45.0, 24.1, 1.0, 650.0, 4.1, 144.5,
                           None, None),
    "324F004": EjectorDuty("324F004", 761.0, 0.12, 40.0, _mw_of_mass_flows(F004_DUTY_GAS_KGH),
                           0.35, 1061.0, 4.1, 146.0, 24.7, 106.5),
    "324F005": EjectorDuty("324F005", 84.0, 0.33, 41.0, _mw_of_mole_pct(PFD_324_MOL_PCT["715"]),
                           1.16, 366.0, 4.1, 146.0, 14.5, 30.8),
}


@dataclass(frozen=True)
class EjectorLoad:
    """One steam-jet ejector's design load: the gas it pulls [kg/h] at its suction pressure
    [bar a], at its duty's motive pressure, and the motive steam it takes there [kg/h]."""

    tag: str
    suction_kgh: float
    p_suction_bara: float
    motive_kgh: float


#: 324F002's motive steam at design [kg/h], PFD-21 stream 924 at 4.1 bar a and 146 C: the
#: licensor's own closure around the ejector, 706 (72) + 924 (390) = 708 (462), and Flowserve's
#: normal case for HV-329605 (V1 ``R324_F002_MOTIVE_DES``, its AUDIT C16). Körting's 650 kg/h at
#: 4.1 bar a sized the map's nozzle (`EJECTOR_DUTIES`); the PFD's flow is the design motive, as for
#: the other two (handoff B-64, decided 2026-10-02).
F002_MOTIVE_DES_KGH = 390.0

#: 324F004's and 324F005's motive steam at design [kg/h], PFD-21 streams 927 and 929 at 4.1 bar a
#: and 146 C: the licensor's closures around the two ejectors, 712 (584) + 927 (1220) = 714 (1804),
#: 324E006's anchored inlet, and 715 (41) + 929 (180) = 717 (221), 324E007's (V1
#: ``R324_F004_MOTIVE_DES``, ``R324_F005_MOTIVE_DES``). Decided 2026-10-02 (handoff B-64, option a):
#: the PFD's motive is what the train condenses and what the nozzle pressure is anchored on; Uhde's
#: 1061 and 366 kg/h stay the nozzles' rating inside the maps (`EJECTOR_DUTIES`).
F004_MOTIVE_DES_KGH = 1220.0
F005_MOTIVE_DES_KGH = 180.0

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
    "CW_CP_KJKG_K", "lmtd_countercurrent", "CondenserRating", "VACUUM_CONDENSERS",
    "PFD_324_MOL_PCT", "VAC_PFD_KMOLH", "VAC_AIR_MW", "VAC_AIR_FRAC", "EjectorDuty",
    "F004_DUTY_GAS_KGH", "EJECTOR_DUTIES", "EjectorLoad", "F002_MOTIVE_DES_KGH",
    "F004_MOTIVE_DES_KGH", "F005_MOTIVE_DES_KGH",
    "PFD_703_KGH", "PFD_705_KGH", "PFD_709_KGH", "PFD_790_KGH", "HV_329606_DES_KGH",
    "HV_329605_OP_DES_PCT", "HV_329606_OP_DES_PCT", "MOTIVE_P1_DES_BARA", "MOTIVE_P2_DES_BARA",
    "HV_329605_XT", "HV_329606_XT", "E006_SHELL_VOL_M3",
]
