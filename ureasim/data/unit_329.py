"""Unit 329 — the steam network: its headers, the PFD's design rows, its users and its closure.

What this is
------------
The steam the urea plant runs on. The 25 bar a battery-limit supply from 320MT02 (PFD 901) is
let down by PV-329204 into 329D005, the HP saturator feeding 322E001's shell (19.7 bar a); by
PV-329205A into 329D009, the 9-bar drum whose vapour is the 9-bar header; and by PV-329207C or
HV-329602 into 322D001A/B, the LP drums 322E002 raises its steam in, whose vapour is the LP
header. The condensate cascades 329D005 -> LV-329502 -> 329D009 -> LV-329503 -> 322D001, flashing
at each drop; LV-329504 makes 322D001 up from 329P001A/B; 322E002 blows down 959 continuously.

This module carries the header pressures, the PFD's rows, the inlet states, each header's users
and the design closure the network is anchored on; the drums, valves, controllers and relief are
`ureasim.data.unit_329_network`'s.

Decided 2026-10-02
------------------
* **B-68**: every simulated user draws its live load from its header; the unsimulated users are
  constant boundary conditions at their PFD rows. V1 lumps every LP user but the HPCC into one
  constant set at boot.
* **B-69**: the LP header runs at 4.0 bar g, the plant's operating point, not the PFD's 4.4 bar a.
* **B-70**: each superheated inlet desuperheats on its drum's water, which the level loses; the
  9-bar drum's 275 kg/h of "saturation water" is its own water; no letdown water from nowhere; no
  3.5 bar a floor under the LP header; 959 leaves 322D001's water.
* **Decision 47's class** (§5 rule 7): a flowsheet stream on the PFD's balance where an
  equipment's own figure differs, that figure kept inside the equipment's model. The stripper's
  model draws 39 400 kW / 1850 kJ/kg = 76.7 t/h at design, the HPCC's raises 106.3 t/h (62.6 MW
  / 2120 kJ/kg; Uhde's datasheet 44 900 kW and 79 t/h), 324E003's chest condenses 3741 kg/h; the
  headers see each unit's live ratio to its own design on the rows below.

The design closure, PFD-21's steam block on IAPWS-IF97 [kg/h]
-------------------------------------------------------------
    329D005 vapour  902 + ds_5 = strip              ds_5 = 902 (h_902 - h_g) / h_fg at 19.7 bar a
    329D005 water   strip = ds_5 + 904              the stripper's condensate returns to the drum
    329D009 vapour  903 + 906 + ds_9 = 920 + 910 + 912        906 = 904 . 4658 / 57 989 (V1's)
    329D009 water   904 - 906 = 913 + ds_9          ds_9 = 275 . 903 / 1754 (V1's, the drum's water)
    322D001 vapour  raise + 915 = the LP users + 932          915 = 913 . x(9.0 -> 5.013 bar a)
    322D001 water   913 - 915 + 916 = raise + 959

902 = 57 989 and ds_5 = 8913 (902 at the PFD's 328 C): the stripper condenses 66 902 kg/h. 913 =
53 056, the PFD's row. 915 = 2570 at 4.0 bar g where the PFD's 3062 is at 4.4 bar a (B-69), so the
HPCC's design raising is 66 359 where the PFD's 917 - 915 is 65 866. 916 = 19 501 against the PFD's
19 500, the PFD's rounding.

Sources
-------
PFD-21, ``References/Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md``, streams 901-999.
``References/Mapping of the steam system.md`` (the users, "as per PFD figures" for the rest). V1
``backend/steam_system.py`` (the pressures, V1's anchors). As-Built Part LIII and Part LIV.
"""

from __future__ import annotations

from ureasim.core.units_of_measure import ATM_BARA
from ureasim.thermo.iapws import h_vapour_kjkg
from ureasim.thermo.water_steam import flash_fraction, superheat_water_ratio

# ======================================================================================
# The headers
# ======================================================================================

#: LP steam header design pressure [bar a] — the 322D001A/B LP drums at 4.0 bar g, the plant's
#: operating point (handoff B-69, decided 2026-10-02: the operators' screens, not the PFD's 4.4
#: bar a). Every LP steam chest's design valve stroke is derived from its datasheet chest pressure
#: against this header. V1 writes the gauge-to-absolute conversion with 1.01325 bar, the engine's
#: one atmosphere (handoff B-6, decided). Source: V1 `steam_system.py` P_LP_BARA.
P_LP_BARA = 5.01325

#: The 9-bar (MP) steam header [bar a] — 329D009's design, Tsat about 175 C — that 324E003's chest
#: draws from through PV-329212; and the saturated steam's and its condensate's specific enthalpies
#: there [kJ/kg], whose difference V1 takes as the latent heat 324E003's chest pays per kilogram.
#: Source: V1 `steam_system.py` P_MP_BARA, H_G_MP, H_F_MP.
P_MP_BARA = 9.0
H_G_MP_KJKG = 2773.0
H_F_MP_KJKG = 742.0

#: 329D005, the HP saturator, at design [bar a] — 322E001's shell steam. Source: V1
#: `steam_system.py` P_HP_BARA; PFD 902 and 904.
P_HP_BARA = 19.7

#: The battery-limit supply, PFD 901, held [bar a, deg C]. Source: PFD 901; V1 P_SUP_BARA.
P_SUP_BARA = 25.0
T_SUP_C = 330.0

#: Turbine 320MT02's inlet behind PV-329207B, PFD 932 [bar a]. Source: V1 P_TURBINE_OUT_BARA.
P_TURBINE_OUT_BARA = 3.9

#: Atmosphere, where HV-329601 and PV-329207A discharge [bar a]. Source: V1 `steam_system.py`
#: (the literal 1.01325 in its vent calls); the engine's one atmosphere (handoff B-6).
P_ATM_VENT_BARA = ATM_BARA

#: Ratio of specific heats of saturated steam over this pressure range [-]. F_gamma = 0.9286, so
#: a steam valve chokes at dP/P1 = 0.696 on the globe trim assumed throughout. Source: V1
#: `steam_system.py` STEAM_GAMMA.
STEAM_GAMMA = 1.30

#: Molar mass of steam [kg/kmol]. V1's steam network carries the precise 18.01528; the liquor
#: species table carries the PFD's 18.0152. Each is kept where V1 uses it. Source: V1
#: `steam_system.py` STEAM_MW.
STEAM_MW = 18.01528

# ======================================================================================
# The PFD's rows and the inlet states
# ======================================================================================

#: PFD-21's steam and condensate rows the network carries [kg/h].
STEAM_PFD_KGH = {
    "901": 60848.0, "902": 57989.0, "903": 1754.0, "904": 57989.0, "905": 53331.0,
    "906": 4658.0, "907": 6687.0, "910": 1094.0, "911": 1105.0, "912": 1435.0, "913": 53056.0,
    "914": 49993.0, "915": 3062.0, "916": 19500.0, "917": 68928.0, "918": 9027.0,
    "919": 18489.0, "920": 4158.0, "923": 2917.0, "924": 390.0, "926": 11230.0, "927": 1220.0,
    "928": 545.0, "929": 180.0, "931": 6495.0, "932": 16707.0, "959": 3628.0, "960": 0.0,
    "963": 0.0, "965": 729.0, "999": 1000.0,
}

#: The superheated inlets' enthalpies [kJ/kg], each on its PFD state: 902 at 328 C and 19.7 bar a,
#: 903 at 317 C and 9 bar a, 963 at 312 C and 4.4 bar a — the battery limit's steam let down
#: through PV-329204, PV-329205A and PV-329207C / HV-329602, whose upstream is held.
H_902_KJKG = h_vapour_kjkg(328.0, 19.7)
H_903_KJKG = h_vapour_kjkg(317.0, 9.0)
H_963_KJKG = h_vapour_kjkg(312.0, 4.4)

#: 916's state: 329P001A/B's discharge into LV-329504, 100 C condensate at 9.0 bar a, held (the
#: pumps are not modelled) [bar a, deg C, kg/m3]. Source: PFD 916; V1 P_916_BARA, RHO_916.
P_916_BARA = 9.0
T_916_C = 100.0
RHO_916_KGM3 = 958.58

# ======================================================================================
# The users (handoff B-68)
# ======================================================================================

#: The LP header's simulated users, each its unit's live draw [PFD stream: what draws it].
LP_USERS_LIVE = {
    "918": "323E002's chest (PIC-329202)",
    "919": "324E001's chest (PV-329203)",
    "926": "323E010's chest (PIC-329208)",
    "924": "324F002's motive steam (HV-329605)",
    "927": "324F004's motive steam (HV-329606)",
    "929": "324F005's motive steam (HV-329606)",
    "931": "328C004's stripping steam (FV-329401)",
}

#: The LP header's users the simulator does not model, at their PFD rows (`References/Mapping of
#: the steam system.md`: "as per PFD figures until added in future units").
LP_USERS_PFD = {"923": "steam tracing", "928": "PFD 928", "965": "the melt line",
                "999": "LP steam to storage, battery limit"}

#: The 9-bar header's simulated users. XV-322915's flood of 322C001's vent line draws the valve's
#: rated 1000 kg/h while open (decision 41; handoff B-60), nothing at design. 322C001's three
#: restriction orifices (FO-322457, FO-329458, FO-329459) draw their rated 90 kg/h, live on the
#: header (decided 2026-10-07); the PFD carries them in 910, so their design draw is taken out
#: of it.
MP9_USERS_LIVE = {"920": "324E003's chest (PV-329212)", "flood": "XV-322915's vent-line flood",
                  "trace": "322C001's trace steam and SV32253's purge"}

#: The 9-bar header's users the simulator does not model, at their PFD rows. PFD 26 draws 910 as
#: "steam tracing" off 329D009's header; 912 goes to the granulation unit (PFD 27, 335E002).
MP9_USERS_PFD = {"910": "PFD 910, steam tracing", "912": "PFD 912, the granulation unit"}


#: 322C001's three trace-steam restriction orifices off this header [kg/h], each DN15 and rated
#: 30 kg/h of saturated steam from 9.0 to 1.0 bar a at 175 C: FO-329458 into the vent line between
#: the column's top nozzle and PV-322201, FO-322457 across XV-322915 downstream of it, FO-329459
#: into SV32253's discharge. Uhde's loop summaries F 322457 (UD-MR-322-EC-0001) and F 329458 /
#: F 329459 (UD-MR-329-EC-0001 rev 1, PDF pages 33 and 34), scanned; the tie-ins from P&ID
#: UD-VT-322-FB-0003, sheet 102. Decided by the process engineer 2026-10-07: modelled.
FO_329458_KGH = 30.0
FO_322457_KGH = 30.0
FO_329459_KGH = 30.0

#: The three at their rating [kg/h], 90: inside PFD 910 at design.
MP9_TRACE_DES_KGH = FO_329458_KGH + FO_322457_KGH + FO_329459_KGH


def design_users(users: dict) -> dict:
    """Each named user at its PFD row [kg/h] (the flood at nothing); the trace steam at its rating,
    out of PFD 910's steam tracing, where both are named."""
    out = {k: STEAM_PFD_KGH.get(k, 0.0) for k in users}
    if "trace" in out and "910" in out:
        out["trace"] = MP9_TRACE_DES_KGH
        out["910"] -= MP9_TRACE_DES_KGH
    return out


#: The LP users' design sum [kg/h], 932 apart (PV-329207B passes it): 52 222.
LP_USERS_DES_KGH = sum(design_users({**LP_USERS_LIVE, **LP_USERS_PFD}).values())

#: The 9-bar users' design sum [kg/h]: 6687, PFD 907.
MP9_USERS_DES_KGH = sum(design_users({**MP9_USERS_LIVE, **MP9_USERS_PFD}).values())

# ======================================================================================
# The design closure
# ======================================================================================

#: 329D005's water 902's superheat boils at design [kg/h], 8913.
DS5_DES_KGH = STEAM_PFD_KGH["902"] * superheat_water_ratio(H_902_KJKG, P_HP_BARA)

#: The steam 322E001's shell condenses at design [kg/h], 66 902: what the header sees the
#: stripper draw, scaled by the stripper's duty ratio (decision 47's class).
STRIP_DES_KGH = STEAM_PFD_KGH["902"] + DS5_DES_KGH

#: 329D009's own water 903's superheat boils at design [kg/h], 275: V1's closure of PFD 907
#: (M_ATTEMPER9_DES = 907 - 903 - 906), drawn from the drum's water (B-70).
DS9_DES_KGH = STEAM_PFD_KGH["907"] - STEAM_PFD_KGH["903"] - STEAM_PFD_KGH["906"]

#: The fraction of LV-329502's condensate that flashes in 329D009 [-]: V1's anchor, 906 over
#: LV-329502's design flow, on the PFD's 904 (decision 47; V1's 4658 over its 76.7 t/h).
FLASH9_FRACTION = STEAM_PFD_KGH["906"] / STEAM_PFD_KGH["904"]

#: LV-329503's design flow [kg/h], 53 056: 905 less the 9-bar drum's desuperheating water.
M_913_DES_KGH = STEAM_PFD_KGH["904"] - STEAM_PFD_KGH["906"] - DS9_DES_KGH

#: 913's flash in 322D001 at design [kg/h], 2570, on IAPWS at the 4.0 bar g header.
FLASH4_DES_KGH = M_913_DES_KGH * flash_fraction(P_MP_BARA, P_LP_BARA)

#: The steam 322E002 raises at design [kg/h], 66 359: what closes the LP header on its users and
#: 932; the header sees the HPCC's live raising ratio on it (decision 47's class).
RAISE_DES_KGH = LP_USERS_DES_KGH + STEAM_PFD_KGH["932"] - FLASH4_DES_KGH

#: 959, 322E002's continuous blowdown [kg/h] ("static", the mapping).
BLOWDOWN_KGH = STEAM_PFD_KGH["959"]

#: LV-329504's design flow [kg/h], 19 501: the make-up that closes 322D001's water.
M_916_DES_KGH = RAISE_DES_KGH + BLOWDOWN_KGH - (M_913_DES_KGH - FLASH4_DES_KGH)

#: AI-329701, the conductivity analyser on 329D001, the steam condensate tank: 0-10 uS/cm, in the
#: DCS with a high alarm and a high-high safety alarm (Uhde's loop summary UD-MR-329-EC-0001 rev 1,
#: A 329701, PDF pages 6-7, line D07; P&ID 107/2). The alarms' set points are DCS database values,
#: not in the archive. Decided 2026-10-09 (handoff B-90): it shows a 322E002 tube leak.
AI_329701_SPAN_US_CM = 10.0

#: AI-329701's alarms: H1 15 and H2 18 (the process engineer's readback of the plant DCS, 13 October 2026,
#: "AI-329701 Alarm setpoints H1 = 15 H2 = 18", the handwritten note
#: `Urea Simulation Docs/Data/DCS_Extract_2026-10-13.jpg`). The note prints no unit: the PV's,
#: uS/cm. Both stand above the loop summary's 0-10 uS/cm range, so the transmitter's range has been
#: changed since 2007 and its present value is not known (handoff Open data gaps): the alarms are
#: evaluated on the condensate's conductivity, the reading keeps the archive's range. AC4's
#: PC29.5.2 reads the H2 flag into trip 29.2 and LVY-329506A, which the simulator does not model.
AI_329701_H1_US_CM = 15.0
AI_329701_H2_US_CM = 18.0

#: 329D001, the steam condensate tank AI-329701 samples: name plate nominal capacity 50 m3, inside
#: diameter 3.59 m, design liquid level 4.95 m (pi/4 . 3.59^2 . 4.95 = 50.1 m3; geometric volume
#: 51.7 m3, shell 5100 mm). Source: the general assembly UD-AU-329-TL-0001 rev 00, one scanned
#: sheet, read 2026-10-14 (applied 2026-10-14, handoff Open data gaps). The normal level and the
#: drawdown are not printed. No model reads it yet: a mixing lag on AI-329701 is a new mechanism.
CONDENSATE_TANK_VOL_M3 = 50.0
CONDENSATE_TANK_ID_M = 3.59
CONDENSATE_TANK_LEVEL_DES_M = 4.95

#: Limiting molar ionic conductivities in water at 25 C [S cm2/mol]: NH4+ 73.5, HCO3- 44.5. Source:
#: CRC Handbook of Chemistry and Physics, "Ionic conductivity and diffusion at infinite dilution".
LAMBDA0_NH4_SCM2 = 73.5
LAMBDA0_HCO3_SCM2 = 44.5

#: Pure water's conductivity at 25 C [uS/cm] (18.2 MOhm cm). Source: CRC Handbook of Chemistry and
#: Physics, "Electrical conductivity of water".
KAPPA_WATER_US_CM = 0.055


__all__ = [
    "P_LP_BARA", "P_MP_BARA", "H_G_MP_KJKG", "H_F_MP_KJKG", "P_HP_BARA", "P_SUP_BARA", "T_SUP_C",
    "P_TURBINE_OUT_BARA", "P_ATM_VENT_BARA", "STEAM_GAMMA", "STEAM_MW", "STEAM_PFD_KGH",
    "H_902_KJKG", "H_903_KJKG", "H_963_KJKG", "P_916_BARA", "T_916_C", "RHO_916_KGM3",
    "LP_USERS_LIVE", "LP_USERS_PFD", "MP9_USERS_LIVE", "MP9_USERS_PFD", "FO_329458_KGH",
    "FO_322457_KGH", "FO_329459_KGH", "MP9_TRACE_DES_KGH",
    "design_users",
    "LP_USERS_DES_KGH", "MP9_USERS_DES_KGH", "DS5_DES_KGH", "STRIP_DES_KGH", "DS9_DES_KGH",
    "FLASH9_FRACTION", "M_913_DES_KGH", "FLASH4_DES_KGH", "RAISE_DES_KGH", "BLOWDOWN_KGH",
    "M_916_DES_KGH", "AI_329701_SPAN_US_CM", "AI_329701_H1_US_CM", "AI_329701_H2_US_CM", "CONDENSATE_TANK_VOL_M3", "CONDENSATE_TANK_ID_M",
    "CONDENSATE_TANK_LEVEL_DES_M", "LAMBDA0_NH4_SCM2", "LAMBDA0_HCO3_SCM2",
    "KAPPA_WATER_US_CM",
]
