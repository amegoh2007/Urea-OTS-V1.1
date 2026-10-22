"""323E003 / 323D001 / 323P001 — the LP carbamate condenser: the design basis.

323E003 condenses the 323C003 overhead (PFD 305) on a tempered-water circuit, with 718B from
323D011, 776 from 328D001 and the inert-laden 797 recycle; the liquid falls into 323D001, and
323P001 A/B, plunger pumps on a Voith scoop-tube drive, return it to the HP synthesis as PFD 308.
What does not condense leaves through PV-323202 to the 323E011 node, PFD 321.

    PIC-323202 (323D001 pressure)       ->  PV-323202 (vent 321 to 323E011)
    LIC-323502 (323D001 level)          ->  SIC-323901 (323P001A speed)  ->  PFD 308
    TIC-323013 (tempered-water supply)  ->  TV-323013A / TV-323013B (split range)

Sources
-------
* ``Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md`` and ``References/323E003 323D001
  323P001 Datasheets.md`` — streams 305, 308, 321, 718B, 776 and 797, the tempered water (1102
  at 55 C, 1103 at 65 C), the 14 000 kW duty, 323D001's 11.10 m3 and the 3.2 bar a set point,
  and 323P001's plunger geometry.
* ``References/Master_PID_Tuning_Constants.md`` — PIC-323202 (its "B" row), SIC-323901 and
  TIC-323013.
* Uhde loop summaries for unit 323, UD-MR-323-EC-0001 rev 1 (the vendor archive) — PT-323202's,
  TT-323013's and ST-323901's calibrated ranges; the functional diagrams, UD-MR-323-FF-0002,
  for the LIC-323502 -> SIC-323901 cascade.
* V1 ``backend/main.py``, the "323E003 + 323D001 + 323P001" constant block (1733-1828), the
  boundary feeds (1299) and the 328C002 / 328D001 block (1305-1583) for PFD 776; the controller
  seeds in ``State.__init__`` (6887-6948). Each value carries its provenance.
"""

from __future__ import annotations

from ureasim.data.control_valves import design_stroke_pct
from ureasim.data.control_valves_fisher import PV_323202
from ureasim.data.unit_323 import E003_P_DES_BARA, M305_DES_KGH
from ureasim.data.unit_323e011 import (
    CP_LP_CARBAMATE,
    E011_T_C,
    M718A_DES_KGH,
    M718B_DES_KGH,
)
from ureasim.thermo import iapws

# ======================================================================================
# The design flows [kg/h]
# ======================================================================================

#: PFD 305, the 323C003 overhead, as the column's design split delivers it (24 563; the PFD
#: prints 24 582).
E003_M305_DES_KGH = M305_DES_KGH

#: PFD 718B, lean carbamate from 323D011 on FIC-323418.
E003_M718B_DES_KGH = M718B_DES_KGH

#: PFD 776, the 328D001 bottoms on LIC-328501, 8275.5 (PFD 8275). A boundary until unit 328 is
#: ported, written as V1 writes it: 328D001 takes the 328C002 overhead (its 6665 / 40 434 split
#: of 738 + 748 + 750 + 775) and 718A, and loses the 786 vent and the 775 reflux. Source: V1
#: `main.py` R328_D001_M776_DES and the constants it is built from.
_C002_IN_DES_KGH = 31114.0 + 812.0 + 6833.0 + 1675.0
_C002_M737_DES_KGH = 6665.0 / 40434.0 * _C002_IN_DES_KGH
E003_M776_DES_KGH = (_C002_M737_DES_KGH + M718A_DES_KGH) - 276.0 - 1675.0

#: PFD 797, the inert-laden recycle into 323E003 [kg/h], and its temperature [deg C]. A
#: battery-limit constant in V1 (``R3232_M797_DES``, ``R3232_M797_T``).
E003_M797_DES_KGH = 1758.0
E003_T797_C = 46.0

#: PFD 734, the ammonia water FIC-323401 sends from 328D003's compartment II, and its temperature
#: [deg C]: 56 C on the PFD's row (1534 kg/h, 4.1 bar a). DECIDED 2026-10-10 (handoff B-37,
#: project.md decision 100): it enters 323E003, as Uhde's loop summary for F 323401 names its
#: service, "AW to 323E003 LP Carb. Condenser" (UD-MR-323-EC-0001 rev 1, sheet 1/2), a live inlet
#: of 328D003's. V1 books it out of the tank into no unit. The PFD's 323E003 balance closes
#: without it, so the design inlets and PFD 308 below stay the PFD's and 734 enters as its departure
#: from the PFD's row (decided 2026-10-14, handoff B-94): nothing at design, its whole change off it.
E003_M734_DES_KGH = 1534.0
E003_T734_C = 56.0

#: The condenser's four physical inlets at design.
E003_IN_DES_KGH = E003_M305_DES_KGH + E003_M718B_DES_KGH + E003_M776_DES_KGH + E003_M797_DES_KGH

#: PFD 321, the PV-323202 vent to 323E011: 1323 kg/h (PFD table 20 prints 132.3, a decimal
#: slip; see `unit_323e011.E011_M321_DES_KGH`), carried as V1 carries it, a split of 305 + 797.
E003_PHI321 = 1323.0 / (E003_M305_DES_KGH + E003_M797_DES_KGH)
E003_M321_DES_KGH = E003_PHI321 * (E003_M305_DES_KGH + E003_M797_DES_KGH)

#: PFD 308, what 323P001 returns to the HP synthesis: every inlet less the vent, 36 835 (36 915
#: on the PFD).
E003_M308_DES_KGH = E003_IN_DES_KGH - E003_M321_DES_KGH

#: Gas the envelope condenses at design: 305 + 797 less the vent, 24 998.
E003_M_COND_DES_KGH = E003_M305_DES_KGH + E003_M797_DES_KGH - E003_M321_DES_KGH

# ======================================================================================
# The temperatures [deg C]
# ======================================================================================

#: 323E003 shell liquid, PFD 308 (TT-323006).
E003_T_C = 74.0

#: The inlet temperatures the energy balance charges: PFD 305 off the column, 718B at 323D011's
#: design, 776 at 328D001's (V1 ``R328_D001_T``). V1 holds all of them at design (handoff B-31).
E003_T305_C = 119.0
E003_T718B_C = E011_T_C
E003_T776_C = 61.0

#: Tempered water, PFD 1102 supply (TIC-323013's set point) and 1103 return (TT-323015), and
#: their mean — the DESIGN datum the duty is back-solved on, never a live value.
TW_SUP_T_C = 55.0
TW_RET_T_C = 65.0
TW_T_C = 60.0

#: TV-323013A's design stroke [%] and the supply temperature's lag behind it [s]. Source: V1
#: `main.py` R3232_TV13_DES_PCT, R3232_TW_TAU_S.
TV13_DES_PCT = 50.0
TW_TAU_S = 25.0

#: The floor V1 puts on the supply the split range can reach [deg C], its literal ``20.0``. The
#: stroke alone spans 45 to 65 C, so it never binds.
TW_SUP_FLOOR_C = 20.0

# ======================================================================================
# 323D001 and the gas envelope
# ======================================================================================

#: Node pressure at design [bar a], PIC-323202's set point: "maintains the tank ... at a
#: setpoint of 3.2 bar a" (the datasheet narrative). PFD 308 and 321 at 3.2.
D001_P_BARA = E003_P_DES_BARA

#: PV-323202's design stroke [%]: Fisher's sheet (UD-MR-G00-DZ-0014, item 021, tagged TV-323013
#: as on P&ID 103/1; its cases the loop summary P 323202's) — a linear Whisper I trim, rated Cv
#: 99.1 — passes PFD 321 on its normal case at 36.45 % (decided 2026-10-22, decision 150; decision
#: 23's class). PIC-323202 is seeded there. V1 runs it linear from 25 % (R3232_E003_PV_OP_DES).
E003_PV_OP_DES_PCT = design_stroke_pct(PV_323202, E003_M321_DES_KGH)

#: 323D001 nominal volume [m3] (datasheet: ID 2178 mm, T-T 2350 mm, 11.10 m3) and the
#: carbamate density [kg/m3], PFD 308. The full holdup is their product, 13 520 kg.
D001_VOL_M3 = 11.10
D001_RHO_KGM3 = 1218.0
D001_M_FULL_KG = D001_VOL_M3 * D001_RHO_KGM3

#: LI-323502's set point [%] and the design holdup it implies [kg], 6760.
D001_LVL_SP_PCT = 50.0
D001_M_DES_KG = D001_M_FULL_KG * (D001_LVL_SP_PCT / 100.0)

#: Floors on the holdup [kg] and on the node [bar a]: V1's ``max(..., 1.0)`` and
#: ``max(..., 0.1)``.
D001_M_FLOOR_KG = 1.0
D001_P_FLOOR_BARA = 0.1

#: The envelope's gas capacitance [kg/bar], 10.37. 323C003's vapour space, the 323E003 shell
#: and 323D001 are one gas inventory (stream 305 has no valve); only the tank's volume is
#: published, so V1 takes it alone — the documented lower bound — at the PFD stream-332 gas
#: density, 2.99 kg/m3 at 3.2 bar a and 74 C: ideal gas at fixed temperature, dM/dP = M / P.
ENV_GAS_RHO_DES_KGM3 = 2.99
ENV_GAS_C_KG_BAR = D001_VOL_M3 * ENV_GAS_RHO_DES_KGM3 / D001_P_BARA

#: Water's saturation temperature at the design node [deg C]: the anchor of the dew point's
#: frozen offset.
TSAT_E003_DES_C = iapws.tsat_c(D001_P_BARA)

# ======================================================================================
# The energy balance at design
# ======================================================================================

#: The tempered-water duty [kW], the datasheet's 14 000, and the duty per kelvin of shell to
#: water mean [kW/K], 1000.
E003_Q_DES_KW = 14000.0
E003_UA_KW = E003_Q_DES_KW / (E003_T_C - TW_T_C)

#: The inlets' sensible heat onto the 74 C liquid at design [kW], and the latent heat of the
#: condensed gas that closes the balance on the design duty [kJ/kg]. Written as V1 writes them.
E003_SENS_KW = ((E003_M305_DES_KGH * (E003_T305_C - E003_T_C)
                 + E003_M718B_DES_KGH * (E003_T718B_C - E003_T_C)
                 + E003_M776_DES_KGH * (E003_T776_C - E003_T_C)
                 + E003_M797_DES_KGH * (E003_T797_C - E003_T_C))
                / 3600.0 * CP_LP_CARBAMATE)
E003_LAMC_KJKG = ((E003_Q_DES_KW - E003_SENS_KW) / (E003_M_COND_DES_KGH / 3600.0))

# ======================================================================================
# 323P001, the HP carbamate pump
# ======================================================================================

#: Delivered volume per revolution-minute [m3/h per rpm]: three 130 mm plungers on a 220 mm
#: stroke sweep 0.5256 n m3/h, and a 96 % volumetric efficiency leaves 0.5046 n (the datasheet's
#: kinematic deduction).
P001_M3H_PER_RPM = 0.5046

#: 323P001's speed at the design draw [rpm], 59.93 (V1's comment says 62.99; the datasheet runs
#: 64 rpm for 32.3 m3/h). SIC-323901 runs in rpm, so this is its seed and the scale of the draw.
P001_RPM_DES = E003_M308_DES_KGH / (D001_RHO_KGM3 * P001_M3H_PER_RPM)

#: SIC-323901's speed measurement lag [s]. Source: V1 `main.py`, ``_lag1(..., "S_323901", ...,
#: 3.0, dt)``.
SIC_323901_PV_TAU_S = 3.0

# ======================================================================================
# The controllers
# ======================================================================================
# The DCS tuning table gives each gain as per cent of output per per cent of the PV's span. A
# loop running on its PV in engineering units carries the table's gain times 100 / span — decided
# 2026-09-27 for PIC-323203 and the two LPCC loops below (handoff B-32).

#: PIC-323202: the table's row, "PIC-323202B | 329058,WC", 1.00 and 100 s, derivative off. V1
#: ran 5.0 %/bar and 40 s, which no source gives; the port runs the table.
PIC_323202_KC_TABLE = 1.0
PIC_323202_TI_S = 100.0
PIC_323202_TD_S = 0.0

#: PT-323202's calibrated range [bar]: 0 to 5 bar g, gauge pressure, on 323D001 (normal
#: 3.9 bar a on the loop summary). Source: UD-MR-323-EC-0001 rev 1, loop P 323202, sheet 1/2,
#: line D07 (scanned, read from the page image).
PT_323202_SPAN_BAR = 5.0

#: PIC-323202: DIRECT acting — a node above set point opens the vent. 1.00 on a 5 bar span is
#: 20 %/bar. Its set-point range [bar a] is V1's.
PIC_323202_KC = PIC_323202_KC_TABLE * 100.0 / PT_323202_SPAN_BAR
PIC_323202_SP_LO_BARA = 2.0
PIC_323202_SP_HI_BARA = 5.0

#: ST-323901's calibrated range [rpm]: 0 to 145 rpm on 323P001A. Source: UD-MR-323-EC-0001
#: rev 1, loop S 323901, sheet 1/2, line D07 (scanned, read from the page image).
ST_323901_SPAN_RPM = 145.0

#: LIC-323502: DIRECT acting on SIC-323901's speed demand. The plant DCS's PIDCON19: gain 1.2,
#: TI 400 s, TD 0, TF 0, DZ 2.0 % (the process engineer's readback of the plant DCS, 13 October 2026, the
#: handwritten note `Urea Simulation Docs/Data/DCS_Extract_2026-10-13.jpg`; decision 76's class).
#: The model carries the output as the speed demand in rpm; the functional diagram scales it onto
#: SIC-323901's range (UD-MR-323-FF-0002: SP = OUTP . SIC-323901:MAX / 100), so the DCS's 1.2 per
#: cent per per cent is 1.74 rpm per per cent of level (decisions 10, 21). The dead zone is not
#: modelled (decision 93). V1 runs its own 1.5 rpm per per cent and 300 s.
LIC_323502_KC_TABLE = 1.2
LIC_323502_KC = LIC_323502_KC_TABLE * ST_323901_SPAN_RPM / 100.0
LIC_323502_TI_S = 400.0

#: SIC-323901: REVERSE acting, the cascade slave. The table's "HP CARB.PUM.323P001A", 1.10 and
#: 30 s. V1 carries both the measured speed and the output — the speed demand to the Voith
#: drive — in rpm, so on ST-323901's span the table's per cent per per cent is the same number
#: in rpm per rpm: the span rule leaves V1's 1.10.
SIC_323901_KC_TABLE = 1.1
SIC_323901_KC = SIC_323901_KC_TABLE
SIC_323901_TI_S = 30.0

#: TIC-323013: DIRECT acting on the tempered-water supply. The table's "329058,CW", 1.00 and
#: 100 s; TT-323013's range is 0 to 100 C (UD-MR-323-EC-0001 rev 1, loop T 323013, sheet 1/4,
#: line D07), so the rescaled gain is the table's own, 1.0 %/K — V1's number.
TIC_323013_KC_TABLE = 1.0
TT_323013_SPAN_C = 100.0
TIC_323013_KC = TIC_323013_KC_TABLE * 100.0 / TT_323013_SPAN_C
TIC_323013_TI_S = 100.0

#: TIC-323013's set-point range [deg C]: the supply the split range can reach, 45 C with
#: TV-323013A wide open to the 65 C return with it shut. Source: V1's seed.
TIC_323013_SP_LO_C = 45.0
TIC_323013_SP_HI_C = TW_RET_T_C

# ======================================================================================
# The liquor's composition (handoff B-105, decided 2026-10-22)
# ======================================================================================

#: The species 323D001's liquor carries: the LP carbamate's condensables. The inerts 797 brings
#: leave in the vent, 321, and are not the tank's.
LIQUOR_SPECIES = ("NH3", "CO2", "H2O", "Urea")


def _mass_fractions(mass_pct: dict) -> dict:
    """A PFD liquid row's mass per cent over the liquor's species, as fractions summing to 1."""
    total = sum(mass_pct[k] for k in LIQUOR_SPECIES)
    return {k: mass_pct[k] / total for k in LIQUOR_SPECIES}


#: PFD 308, what 323P001 returns to the HP synthesis [mass fractions]: 30.61 % NH3, 38.49 % CO2,
#: 30.83 % H2O, 0.07 % urea (the PFD's liquid rows are mass per cent, `unit_322e003.WASH_MASSPCT`).
W_308 = _mass_fractions({"NH3": 30.61, "CO2": 38.49, "H2O": 30.83, "Urea": 0.07})

#: The liquid inlets' PFD rows [mass fractions]: 718B from 323D011 (25.21 / 17.38 / 57.24 / 0.18,
#: 100.01 as printed), 776 from 328D001 (29.21 / 23.63 / 47.10 / 0.06) and 734, 328D003's ammonia
#: water (5.23 / 3.71 / 90.24 / 0.82). Source: the PFD's stream table.
W_718B = _mass_fractions({"NH3": 25.21, "CO2": 17.38, "H2O": 57.24, "Urea": 0.18})
W_776 = _mass_fractions({"NH3": 29.21, "CO2": 23.63, "H2O": 47.10, "Urea": 0.06})
W_734 = _mass_fractions({"NH3": 5.23, "CO2": 3.71, "H2O": 90.24, "Urea": 0.82})

#: What 323E003 condenses out of its gas at design [mass fractions], by closure: PFD 308's species
#: less the two liquid inlets', over the design condensate, so the design tank is PFD 308 exactly
#: (about 31.8 % NH3, 46.4 % CO2, 21.7 % H2O). The 305 row alone does not close the PFD's 308 on
#: the PFD's liquid rows, and 797's inerts leave in the vent.
W_COND = _mass_fractions({
    k: (E003_M308_DES_KGH * W_308[k] - E003_M718B_DES_KGH * W_718B[k]
        - E003_M776_DES_KGH * W_776[k]) / E003_M_COND_DES_KGH * 100.0
    for k in LIQUOR_SPECIES})

__all__ = [
    "E003_M305_DES_KGH", "E003_M718B_DES_KGH", "E003_M776_DES_KGH", "E003_M797_DES_KGH",
    "E003_T797_C", "E003_M734_DES_KGH", "E003_T734_C",
    "E003_IN_DES_KGH", "E003_PHI321", "E003_M321_DES_KGH", "E003_M308_DES_KGH",
    "E003_M_COND_DES_KGH", "E003_T_C", "E003_T305_C", "E003_T718B_C", "E003_T776_C",
    "TW_SUP_T_C", "TW_RET_T_C", "TW_T_C", "TV13_DES_PCT", "TW_TAU_S", "TW_SUP_FLOOR_C",
    "D001_P_BARA", "E003_PV_OP_DES_PCT", "D001_VOL_M3", "D001_RHO_KGM3", "D001_M_FULL_KG",
    "D001_LVL_SP_PCT", "D001_M_DES_KG", "D001_M_FLOOR_KG", "D001_P_FLOOR_BARA",
    "ENV_GAS_RHO_DES_KGM3", "ENV_GAS_C_KG_BAR", "TSAT_E003_DES_C", "E003_Q_DES_KW",
    "E003_UA_KW", "E003_SENS_KW", "E003_LAMC_KJKG", "P001_M3H_PER_RPM", "P001_RPM_DES",
    "SIC_323901_PV_TAU_S", "PIC_323202_KC_TABLE", "PIC_323202_TI_S", "PIC_323202_TD_S",
    "PT_323202_SPAN_BAR", "PIC_323202_KC", "PIC_323202_SP_LO_BARA", "PIC_323202_SP_HI_BARA",
    "LIC_323502_KC_TABLE", "LIC_323502_KC", "LIC_323502_TI_S", "ST_323901_SPAN_RPM", "SIC_323901_KC_TABLE",
    "SIC_323901_KC", "SIC_323901_TI_S",
    "TIC_323013_KC_TABLE", "TT_323013_SPAN_C", "TIC_323013_KC", "TIC_323013_TI_S",
    "TIC_323013_SP_LO_C", "TIC_323013_SP_HI_C",
    "LIQUOR_SPECIES", "W_308", "W_718B", "W_776", "W_734", "W_COND",
]
