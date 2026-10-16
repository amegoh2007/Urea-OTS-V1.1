"""323C005 — the atmospheric absorber: the design basis.

323C005 scrubs the LP gas that reaches atmospheric pressure — PFD 702, the inert-laden vent of
the LP flash gas node through PV-323203, and PFD 708, the vapour from unit 324's vacuum train —
with the cold lean solvent PFD 756, and lets the inert gas go to 328V001's stack as PFD 341. The
liquor, PFD 343, drains from the sump through N4 into 328V001 and on to 328D003's compartment II.

    756 (lean solvent, 43 C) --> packing <-- 702 (45 C) + 708 (121 C)
                 |                    |
                 v                    +--> 341 vent (43 C) --> 328V001 stack
        sump --N4--> 343 (34 180 kg/h) --> 328V001 --> 328D003 compartment II

No controller acts on it: the sump drains freely and the vent is open to the stack.

Sources
-------
* ``Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md`` — streams 341, 343, 702, 703, 708
  and 756: flows, temperatures, and the vapour rows' mole per cent (PFD-21 / PFD-22).
* ``References/323C005 328V001 Datasheets.md`` (Uhde DDS UD-AU-323-EC-0003) — the shell ID,
  the N4 outlet pipe, the liquid density and the 1.00 bar a operating pressure.
* V1 ``backend/main.py``, the "323C005 + 328V001 + 328D003" block (1831-1937) and the vent
  anchor of report D-11 (3908-3918). Each value carries its provenance.
"""

from __future__ import annotations

from ureasim.data.unit_323e011 import CP_LP_CARBAMATE
from ureasim.thermo import saturated_vent as sv

# ======================================================================================
# The design flows [kg/h] and temperatures [deg C]
# ======================================================================================

#: PFD 756, the lean solvent from the LP absorber's circuit, onto the packing.
C005_M756_DES_KGH = 33358.0

#: PFD 702, the LP flash gas node's vent through PV-323203 (`unit_323e011.E011_MV_DES_KGH`).
C005_M702_DES_KGH = 440.0

#: PFD 708, the vacuum train's vapour to the absorber.
C005_M708_DES_KGH = 462.0

#: PFD 341, the vent to 328V001's stack.
C005_VENT_DES_KGH = 80.0

#: PFD 343, the bottoms to 328V001 and 328D003. 756 + 702 + 708 = 343 + 341 exactly.
C005_BOT_DES_KGH = 34180.0

#: The absorber's liquor temperature at design [deg C] — V1's; PFD 343 prints 56 C.
C005_T_C = 55.0

#: The inlets' temperatures the energy balance charges: 756 at the LP absorber's design (V1
#: ``A328_C001_T``), 702 and 708 as V1's step writes them (literals). All three are the PFD's.
C005_T756_C = 43.0
C005_T702_C = 45.0
C005_T708_C = 121.0

#: The liquor's heat capacity [kJ/(kg K)], V1's ``R3232_CP``, the LP carbamate value.
C005_CP = CP_LP_CARBAMATE

#: The gas the solvent absorbs at design [kg/h], 702 + 708 less the vent, 822; the inlets'
#: sensible heat onto the 55 C liquor at design [kW], -311.8; and the heat of absorption that
#: closes the balance on it [kJ/kg], 1365.7 — back-solved so the design holds, as V1 writes it.
C005_ABS_DES_KGH = C005_M702_DES_KGH + C005_M708_DES_KGH - C005_VENT_DES_KGH
C005_SENS_DES_KW = ((C005_M756_DES_KGH * (C005_T756_C - C005_T_C)
                     + C005_M702_DES_KGH * (C005_T702_C - C005_T_C)
                     + C005_M708_DES_KGH * (C005_T708_C - C005_T_C))
                    / 3600.0 * C005_CP)
C005_LAM_KJKG = -C005_SENS_DES_KW * 3600.0 / C005_ABS_DES_KGH

# ======================================================================================
# The column and its sump
# ======================================================================================

#: Shell ID [m] (DDS line 27) and the bottom head's depth [m], 2:1 ellipsoidal (V1's reading;
#: the head type is not on the DDS).
C005_ID_M = 1.180
C005_HEAD_A_M = C005_ID_M / 4.0

#: The N4 outlet's bore [m]: the nozzle table's 168.3 x 5.6 mm pipe.
C005_N4_ID_M = 0.1683 - 2.0 * 0.0056

#: The liquor density [kg/m3] (DDS line 6) and the operating pressure [bar a] (DDS line 13).
C005_RHO_KGM3 = 977.99
C005_P_BARA = 1.00

#: The N4 inlet's two capacity laws: a sharp-edged orifice's discharge coefficient and the
#: Francis weir coefficient [SI]. Source: V1 `main.py` A323_C005_CD_ORIF, A323_C005_C_WEIR.
C005_CD_ORIFICE = 0.61
C005_C_WEIR = 1.84

# ======================================================================================
# The vent, PFD 341 (V1 report D-11)
# ======================================================================================

#: The PFD vapour rows [mole per cent] and molar totals [kmol/h] the vent is built on:
#: 341 the vent, 702 and 708 the gases, 703 the 324E002 inlet whose inerts 708's scale with.
PFD_341_MOL_PCT = {"CO2": 1.17, "H2O": 8.21, "N2": 68.04, "NH3": 5.05, "O2": 17.53}
PFD_702_MOL_PCT = {"CO2": 0.14, "H2O": 6.35, "N2": 3.30, "NH3": 89.40, "O2": 0.81}
PFD_708_MOL_PCT = {"CO2": 0.46, "H2O": 91.45, "N2": 4.68, "NH3": 2.17, "O2": 1.24}
PFD_703_MOL_PCT = {"CO2": 1.47, "H2O": 93.78, "N2": 0.08, "NH3": 4.45, "O2": 0.02, "Urea": 0.20}
PFD_702_KMOLH = 24.99
PFD_708_KMOLH = 24.64
PFD_703_KMOLH = 1454.67

#: The vent leaves saturated at the absorber top, in equilibrium with the lean solvent entering
#: there: anchored on the 341 row at 1.0 bar a and the solvent's design 43 C.
C005_VENT_SPEC = sv.saturated_gas_spec(PFD_341_MOL_PCT, C005_P_BARA, C005_T756_C)

#: 702's and 708's species at design [kmol/h], and the condensable vapour the two bring — the
#: most the vent can carry.
C005_N702_KMOLH = sv.moles_from_mole_pct(PFD_702_KMOLH, PFD_702_MOL_PCT)
C005_N708_KMOLH = sv.moles_from_mole_pct(PFD_708_KMOLH, PFD_708_MOL_PCT)
C005_CAP_KMOLH = {k: C005_N702_KMOLH[k] + C005_N708_KMOLH[k] for k in sv.CONDENSABLE}

#: The inert gas into 324E002 at design [kmol/h], PFD 703's N2 and O2: 708's inerts move with
#: it. V1 ``_E002_INERT_DES``, read off its 324E002 design spec, which takes them from this row.
E002_INERT_DES_KMOLH = {k: sv.moles_from_mole_pct(PFD_703_KMOLH, PFD_703_MOL_PCT)[k]
                        for k in sv.INERT}

__all__ = [
    "C005_M756_DES_KGH", "C005_M702_DES_KGH", "C005_M708_DES_KGH", "C005_VENT_DES_KGH",
    "C005_BOT_DES_KGH", "C005_T_C", "C005_T756_C", "C005_T702_C", "C005_T708_C", "C005_CP",
    "C005_ABS_DES_KGH", "C005_SENS_DES_KW", "C005_LAM_KJKG", "C005_ID_M", "C005_HEAD_A_M", "C005_N4_ID_M", "C005_RHO_KGM3", "C005_P_BARA",
    "C005_CD_ORIFICE", "C005_C_WEIR", "PFD_341_MOL_PCT", "PFD_702_MOL_PCT", "PFD_708_MOL_PCT",
    "PFD_703_MOL_PCT", "PFD_702_KMOLH", "PFD_708_KMOLH", "PFD_703_KMOLH", "C005_VENT_SPEC",
    "C005_N702_KMOLH", "C005_N708_KMOLH", "C005_CAP_KMOLH", "E002_INERT_DES_KMOLH",
]
