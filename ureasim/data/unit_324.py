"""Unit 324 — the two-stage vacuum evaporation: the design basis (the stages' anchors, the
vacuum condensers).

What this equipment is
----------------------
323D002's urea solution is concentrated to a melt in two vacuum stages: 324E001 / 324F001 at
0.33 bar a and 130 C, 324E003 / 324F003 at 0.131 bar a and 140 C. Each stage's vapour is condensed
in a shell-and-tube surface condenser under its stage's vacuum, the inert gas and what it still
holds leaving the cold end for the steam ejectors that pull the vacuum:

    324F001 (+ 323F010's 790) --703--> 324E002 --706--> 324F002 --708--> 323C005
    324F003 --709--> 324E005 --712--> 324F004 --714--> 324E006 --715--> 324F005 --717--> 324E007
                                                                         --722--> atmosphere
    condensates 719 (324E002), 720 (324E005), 721 (324E006), 759 (324E007) --> 328D003 I

Every condenser's cold end sits at water saturation at its own temperature and shell pressure;
each is anchored on its PFD inlet and vent rows (`units.evaporation.vacuum_condenser`).

Sources
-------
* ``Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md`` — the vapour rows 703, 706, 709, 712,
  714, 715, 717, 722 (mole per cent: V1's ``PFD_324_MASS_PCT`` is named for mass per cent, and its
  vapour rows are the PFD's mole per cent — the F-8 unit convention) and their molar totals; the
  condensers' flows and temperatures (PFD-21 / PFD-28); the melt rows 401 and 402 (mass per
  cent, the PFD's convention for its liquid rows).
* The four condensers' datasheets (``References/Sources/324E002``, ``324E005``, ``324E006``,
  ``324E007 Datasheet.pdf``): areas, tube counts, lengths, shells and tubes, as V1 transcribed them.
* V1 ``backend/main.py`` 3797-3910 (``CW_CP_KJKG_K``, ``_vacuum_condenser_spec``,
  ``VACUUM_CONDENSERS``, ``PFD_324_MASS_PCT``, ``_VAC_PFD_KMOLH``, ``_VAC_AIR_*``,
  ``VACUUM_CONDENSER_SPECS``), 2141-2340 (the stages' design vacuums). Each value carries its
  provenance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ureasim.core.packet import normalise_solution_mass_fraction as _w_norm
from ureasim.core.stream import MW_COMP
from ureasim.data.control_valves import (
    PV_324202,
    PV_324203,
    PV_329203,
    LV_329505,
    PV_329212,
    design_stroke_pct,
)
from ureasim.data.design_point import R324_FEED_DES, R324_W_IN
from ureasim.data.unit_323 import F010_T_SP_C, MEVAP_DES_KGH, W_S317
from ureasim.data.unit_323c005 import PFD_703_KMOLH, PFD_703_MOL_PCT
from ureasim.data.unit_329 import H_F_MP_KJKG, H_G_MP_KJKG, P_LP_BARA, P_MP_BARA, STEAM_PFD_KGH
from ureasim.thermo import iapws
from ureasim.thermo.empirical import urea_soln_cp
from ureasim.thermo.urea_liquor import LiquorStage, bubble_t_raoult, reconcile_melt, stage_anchor

# ======================================================================================
# The two stages' design vacuums
# ======================================================================================

#: 324F001's and 324F003's design vacuums [bar a]: 0.33 and 0.131, the HARD anchors of V1's
#: stages (``R324_F001_P_BARA``, ``R324_F003_P_BARA``; PT-324201, PT-324204).
F001_P_DES_BARA = 0.33
F003_P_DES_BARA = 0.131

#: The two stages' melts at design: urea mass fraction [-] and temperature [deg C], PFD 401
#: (94.31 wt% urea at 130 C) and 402 (97.71 wt% at 140 C), the HARD anchors of V1's stages
#: (``R324_W_EV1``, ``R324_E001_T_SP_C``, ``R324_W_EV2``, ``R324_E003_T_SP_C``; TIC-324001,
#: TIC-324002). V1's "95 %" and "98.6 %" are urea and biuret together (94.31 + 0.69, 97.71 + 0.85).
E001_W_UREA_DES = 0.9431
E001_T_DES_C = 130.0
E003_W_UREA_DES = 0.9771
E003_T_DES_C = 140.0

#: The melt's UNIQUAC urea -> H2O interaction energy [K], refitted to Helwan's PFD (handoff B-58,
#: decided 2026-10-01). The vapour rows 705 and 709 put the water at 96.77 and 87.58 mol % of the
#: 0.33 and 0.131 bar a vapour, so the melts 401 and 402 hold their water with an activity
#: coefficient of 0.7908 and 0.7010; the one-parameter fits are -71.66 K (401) and -98.92 K (402),
#: and their mean to 0.1 K carries both within 4.5 %. Checked against the Fahmy-Nassar plant
#: correlation (``References/Urea-Water VLE Data Research.md`` sec. 4.1): the anchored strength
#: moves +0.175 and +0.045 wt% per kelvin, Fahmy-Nassar's +0.167 and +0.045. Voskov-Voronin's
#: published -211.96 K (V1's) gives 0.517 and 0.485, and slopes half as steep again.
MELT_A_UREA_WATER_K = -85.3

#: 324E006's and 324E007's shell pressures at design [bar a]: the PFD's 0.3 and 1.0 (V1's
#: literals in ``VACUUM_CONDENSER_SPECS``).
E006_P_DES_BARA = 0.3
E007_P_DES_BARA = 1.0

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

#: Each condenser's inlet row, vent row and design shell pressure [bar a] (V1's
#: ``VACUUM_CONDENSER_SPECS`` table): 324E002 and 324E005 on the two stages' vacuums.
CONDENSER_ROWS = {
    "324E002": ("703", "706", F001_P_DES_BARA),
    "324E005": ("709", "712", F003_P_DES_BARA),
    "324E006": ("714", "715", E006_P_DES_BARA),
    "324E007": ("717", "722", E007_P_DES_BARA),
}

# ======================================================================================
# The design mass balance (V1 ``R324_U_DES`` ... ``R324_V2_DES``)
# ======================================================================================

#: The feed's temperature at design [deg C]: 323D002's, 323F010's set point (V1 ``R324_FEED_T_C``).
FEED_T_DES_C = F010_T_SP_C

#: Urea conserved end to end [kg/h]; each stage's melt the urea over its strength, its vapour the
#: rest (V1 2213-2218: the design balance is a pure function of the live design feed).
U_DES_KGH = R324_W_IN * R324_FEED_DES
P1_DES_KGH = U_DES_KGH / E001_W_UREA_DES
V1_DES_KGH = R324_FEED_DES - P1_DES_KGH
P2_DES_KGH = U_DES_KGH / E003_W_UREA_DES
V2_DES_KGH = P1_DES_KGH - P2_DES_KGH

#: The two melts' rows, PFD-21 (mass per cent, rounded; V1 ``W_S401_TAB``, ``W_S402_TAB``), and
#: the same rows reconciled on their feeds so every species closes (V1 ``W_S401``, ``W_S402``,
#: report G3).
W_S401_TAB = _w_norm(dict(Urea=94.31, Biuret=0.69, NH3=0.03, H2O=4.97, HCHO=0.00948))
W_S402_TAB = _w_norm(dict(Urea=97.71, Biuret=0.85, NH3=0.04, H2O=1.39, HCHO=0.0099))
W_S401 = reconcile_melt(W_S317, R324_FEED_DES, P1_DES_KGH, W_S401_TAB)
W_S402 = reconcile_melt(W_S401, P1_DES_KGH, P2_DES_KGH, W_S402_TAB)

# ======================================================================================
# Stage 1 — 324E001 / 324F001 (V1 ``main.py`` 2234-2327)
# ======================================================================================

#: 324F001's volume [m3]: the assembly drawing's nominal volume, body, UD-AU-324-DZ-0006-001 rev 00
#: sheet 1 (heads included; the tracing coil's 0.083 m3 excluded), as V1 read it
#: (``R324_F001_VOL_M3``). The melt's density [kg/m3], DDS line 8 (``R324_F001_RHO_L``).
F001_VOL_M3 = 70.5
F001_RHO_L = 1200.0

#: The separator's vapour molar mass [kg/kmol], from the DDS's own pair: 0.14 kg/m3 at 0.3 bar a and
#: 130 C, M = rho R T / P (V1 ``R324_F001_MW_VAP``, its literals: about 15.6, under water's 18.02
#: because the vapour carries NH3 and CO2).
F001_MW_VAP = 0.14 * 8.314e3 * (130.0 + 273.15) / (0.3 * 1.0e5)

#: Water's latent heat at 130 C [kJ/kg] (V1 ``R324_LAM_V1``).
E001_LAMBDA_KJKG = 2174.0

#: 324E001's chest at design [bar a]: the DDS's shell side, "LP Steam - saturated", 3.7 bar a in
#: and out (UD-AU-324 DDS 324E001 rev 00 page 2, line 21, `References/Datasheets/324E001
#: Database.pdf`, read from the page image; its 144 C is the header steam's superheat after the
#: letdown). Decision 20's class (§5 rule 7): V1 anchors on 3.96 bar a, 0.90 x its retired 4.4.
#: The stroke and the conductance follow from V1's own expressions.
E001_PCHEST_DES_BARA = 3.7
E001_OP_DES_PCT = E001_PCHEST_DES_BARA / P_LP_BARA * 100.0

#: PV-329203 on its vendor's trim (decision 23's class, decided 2026-10-14): Metso's DN 250 Neldisc,
#: maximum Cv 4870 (`data.control_valves.PV_329203`), its design stroke where it passes PFD 919's
#: 18 489 kg/h on its normal case, 39.31 %, and the normal case's xT. V1 runs the valve linear from
#: E001_OP_DES_PCT above, 73.80 %, which the equivalence harness keeps.
PV_329203_OP_DES_PCT = design_stroke_pct(PV_329203, STEAM_PFD_KGH["919"])
PV_329203_XT = PV_329203.normal_case.xt

#: The feed's and the holdup's heat capacities at design [kJ/(kg K)] (V1 ``R324_CP_FEED1``,
#: ``R324_CP_HOLD1``, AUDIT C10: each at its own composition and temperature).
CP_FEED1_DES = urea_soln_cp(R324_W_IN, FEED_T_DES_C)
CP_HOLD1_DES = urea_soln_cp(E001_W_UREA_DES, E001_T_DES_C)

#: The design duty [kW] — the feed to 130 C and the stage-1 vapour's latent heat — and the
#: conductance [kW/K] that gives it from the design chest (V1 ``R324_E001_Q_DES_KW``,
#: ``R324_E001_UA_KW``).
E001_Q_DES_KW = (R324_FEED_DES / 3600.0 * CP_FEED1_DES * (E001_T_DES_C - FEED_T_DES_C)
                 + V1_DES_KGH / 3600.0 * E001_LAMBDA_KJKG)
E001_UA_KW = E001_Q_DES_KW / (iapws.tsat_c(E001_PCHEST_DES_BARA) - E001_T_DES_C)

#: The melt's residence [s], the indicative level at design [%] (324F001 has no level
#: transmitter: unit 324's loop summary lists none), and the holdups [kg] (V1 ``R324_F001_M_*``).
F001_M_TAU_S = 180.0
F001_LEVEL_DES_PCT = 55.0
F001_M_DES_KG = P1_DES_KGH / 3600.0 * F001_M_TAU_S
F001_M_FULL_KG = F001_M_DES_KG / (F001_LEVEL_DES_PCT / 100.0)
F001_M_FLOOR_KG = 1.0

#: The false air PIC-324202 admits at design [kg/h], PFD 784 (V1 ``R324_F001_FA_DES``), through
#: PV-324202 on its vendor trim (decision 23's class): the stroke at which Flowserve's Pos. 55 passes
#: it on its sizing case, 61.07 %, where V1 runs the valve linear from 50 %.
F001_FA_DES_KGH = 21.0
PV_324202_OP_DES_PCT = design_stroke_pct(PV_324202, F001_FA_DES_KGH)

#: 324E002's design inlet [kg/h], the vapour stage 1 and 323F010 send it at design, as V1 writes
#: the trial inlet (``VACUUM_CONDENSERS["324E002"]["inlet_kgh"]`` and ``R323_MEVAP_DES``).
E002_INLET_DES_KGH = VACUUM_CONDENSERS["324E002"].inlet_kgh
F010_VAPOUR_DES_KGH = MEVAP_DES_KGH

#: 324E001's chest condensate, LIC-329505's "active controlled steam trap": the steam's latent heat
#: [kJ/kg] (V1's literal, read at its 3.96 bar a anchor; IAPWS gives 2140 at 3.7), the condensate at
#: design [kg/h], the level set point [%], its residence [s] and holdups [kg], LV-329505's design
#: stroke [%] and full-open capacity [kg/h] (V1 ``R324_E001_LAM_STEAM`` ... ``R324_LV9505_SPAN``).
#: LV-329505 runs linear as V1 has it: Flowserve's Pos. 71 prints a capacity only on its maximum
#: case (Kv 46.57 at 74 %, flashing), and LI-329505's taps (3000 mm apart, loop summary L 329505)
#: have no elevation in the archive (handoff Open data gaps).
E001_LAMBDA_STEAM_KJKG = 2133.0
E001_COND_DES_KGH = E001_Q_DES_KW / E001_LAMBDA_STEAM_KJKG * 3600.0
E001_COND_LEVEL_SP_PCT = 50.0
E001_COND_TAU_S = 90.0
E001_COND_M_DES_KG = E001_COND_DES_KGH / 3600.0 * E001_COND_TAU_S
E001_COND_M_FULL_KG = E001_COND_M_DES_KG / (E001_COND_LEVEL_SP_PCT / 100.0)
E001_COND_M_FLOOR_KG = 0.01
LV_329505_OP_DES_PCT = 50.0
LV_329505_SPAN_KGH = E001_COND_DES_KGH / (LV_329505_OP_DES_PCT / 100.0)

#: LV-329505 on its vendor's trim (decision 23's class, decided 2026-10-15): Flowserve's Pos. 71,
#: Valtek modified equal percentage, Kvs 100 (`data.control_valves.LV_329505`), its design stroke
#: where its calculated normal capacity passes PFD 919's 18 489 kg/h of condensate, 62.19 %, the
#: trap's flow anchored on the chest's design condensate there. V1 runs it linear from 50 % on the
#: span above, which the equivalence harness keeps. No pressure term: V1's trap has none.
LV_329505_VENDOR_OP_DES_PCT = design_stroke_pct(LV_329505, STEAM_PFD_KGH["919"])

#: The stage-1 species layer, anchored on PFD 317 -> 401 and 705 (V1 ``SOL_E001`` and its
#: ``SOL_STAGES`` row): the volatilities, the biuret extent, and the design holdup and state the
#: extent departs from. The vapour is the licensor's volatility alone (V1 ``sol_vapour_y``), so
#: the rigorous bubble-point and volatility memos are not built for this stage.
E001_LIQUOR = LiquorStage(
    w_des=W_S401,
    anchor=stage_anchor(W_S317, W_S401, R324_FEED_DES, V1_DES_KGH, P1_DES_KGH),
    m_des_kg=F001_M_DES_KG, t_des_c=E001_T_DES_C, p_des_bara=F001_P_DES_BARA,
    tbub_des_c=None, tbub_raoult_des_c=bubble_t_raoult(F001_P_DES_BARA, W_S401),
    alpha_model_des=None)

#: The P-T fixed point's tolerance [bar and K] and iteration cap (V1 ``R324_PT_LOOP_TOL``,
#: ``R324_PT_LOOP_MAXIT``, G7: under 7 of 20 iterations to 1e-12 over 0.05-0.80 bar a).
PT_LOOP_TOL = 1e-12
PT_LOOP_MAXIT = 20

#: 324F001's pressure bracket for its backward step [bar a] (V1's literals at the call).
F001_P_MIN_BARA = 0.05
F001_P_MAX_BARA = 1.0

#: The stage-1 controllers on the DCS tuning table's rows read per cent of span (decisions 10 and
#: 21, §5 rule 7). Spans: TT-324001 0-160 C (UD-MR-324-EC-0001, T 324001, line D07); PT-329203
#: 0-6 bar g (UD-MR-329-EC-0001, P 329203); PT-324202 -1 to 0 bar g (UD-MR-324-EC-0001, P 324202);
#: all scanned, read from the page images. The table (`References/Master_PID_Tuning_Constants.md`):
#: TIC-324001 1.50 and 320 s; PIC-329203 0.30 and 75 s; PIC-324202 2.00 and 200 s; LIC-329505
#: 2.50, 60 s, deadband 2 %. V1 runs TIC-324001 at 1.5 bar/K, PIC-329203 at 0.30 x its chest scale
#: and PIC-324202 at 2.0 %/bar.
TT_324001_SPAN_C = 160.0
PT_329203_SPAN_BAR = 6.0
PT_324202_SPAN_BAR = 1.0
TIC_324001_KC = 1.50 * PT_329203_SPAN_BAR / TT_324001_SPAN_C
TIC_324001_TI_S = 320.0
PIC_329203_KC = 0.30 * 100.0 / PT_329203_SPAN_BAR
PIC_329203_TI_S = 75.0
PIC_324202_KC = 2.00 * 100.0 / PT_324202_SPAN_BAR
PIC_324202_TI_S = 200.0
LIC_329505_KC = 2.50
LIC_329505_TI_S = 60.0
#: LIC-329505's deadband [% of span]: zero. The table's 2 % (V1 applies it on this loop alone) is
#: not modelled on any loop — decided 2026-10-09 (handoff B-28): in a noiseless model a deadband
#: only stalls the integral and leaves a permanent offset; on the plant it stops an integral hunting
#: on measurement noise, which the model has none of.
LIC_329505_DZ_PCT = 0.0

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

#: The three ejectors' design loads (handoff B-61, decided 2026-10-01, option a): each map's
#: capacity anchored on the PFD's design flow at its design vacuum and the duty's 4.1 bar a of
#: motive — 324F002 PFD 706, 72 kg/h out of 324E002 at 0.33 bar a; 324F004 PFD 712, 584 out of
#: 324E005 at 0.131; 324F005 PFD 715, 41 out of 324E006 at 0.3 (the condensers' vent rows,
#: `VACUUM_CONDENSERS`). The vendor ratings (`EJECTOR_DUTIES`) stand as margin. The design motive
#: is the PFD's for all three, 924, 927 and 929 (handoff B-64, decided 2026-10-02, option a).
EJECTOR_DESIGN_LOADS = {
    "324F002": EjectorLoad("324F002", VACUUM_CONDENSERS["324E002"].vent_kgh, F001_P_DES_BARA,
                           F002_MOTIVE_DES_KGH),
    "324F004": EjectorLoad("324F004", VACUUM_CONDENSERS["324E005"].vent_kgh, F003_P_DES_BARA,
                           F004_MOTIVE_DES_KGH),
    "324F005": EjectorLoad("324F005", VACUUM_CONDENSERS["324E006"].vent_kgh, E006_P_DES_BARA,
                           F005_MOTIVE_DES_KGH),
}

# ======================================================================================
# Stage 2 — 324E003 / 324F003 (V1 ``main.py`` 2287-2328, 3388-3402)
# ======================================================================================

#: 324F003's volume [m3]: the assembly drawing's nominal volume, body, 10.7 m3 (UD-AU-324-DZ-0008-001
#: rev 00, Aguilar y Salas 12148-0, its AD-2000 design table; scanned, read from the page image;
#: heads included, the steam coil's 0.035 m3 excluded). Decision 33's class (§5 rule 7): V1 takes the
#: cylinder alone, pi/4 x 2.470^2 x 1.550 = 7.427 m3, on the DDS's 2500 mm OD and 1550 mm height
#: (UD-AU-324-EC-0008 page 2, `References/Datasheets/324F003 Datasheet.pdf`, whose nominal volume,
#: line 19, is blank) less a 15 mm wall it assumes (``R324_F003_VOL_M3``). The melt's density
#: [kg/m3], DDS line 8 (``R324_F003_RHO_L``).
F003_VOL_M3 = 10.7
F003_RHO_L = 1220.0

#: The vapour space's molar mass [kg/kmol]: dry air, V1's stated basis for this node's balance — the
#: condensables leave by condensing in 324E005, and PIC-324203 acts by admitting air
#: (``R324_F003_MW_VAP``).
F003_MW_VAP = 28.9647

#: Water's latent heat at 140 C [kJ/kg] (V1 ``R324_LAM_V2``).
E003_LAMBDA_KJKG = 2144.0

#: 324E003's chest at design [bar a]: the DDS's shell side, 5.9 bar a (`References/Datasheets/324E003
#: Datasheet.pdf`, read from the page image), PV-329212's outlet on all three of its loop-summary
#: cases (UD-MR-329-EC-0001, P 329212 sheet 2: 4160 kg/h normal, 8.9 -> 5.9 bar a, 175 C; a butterfly
#: valve with no Kvs, so V1's linear chest law stays). Decision 20's class (§5 rule 7): V1 anchors on
#: 8.1 bar a, 90 % of the 9-bar header (``R324_E003_OP_DES``, ``R324_E003_PCHEST_DES``). The stroke
#: follows from V1's own relation between the two, the conductance from V1's own expression.
E003_PCHEST_DES_BARA = 5.9
E003_OP_DES_PCT = E003_PCHEST_DES_BARA / P_MP_BARA * 100.0

#: PV-329212 on its vendor's trim (decision 23's class, decided 2026-10-14): Metso's DN 80 balanced
#: Neldisc, maximum Cv 150 (`data.control_valves.PV_329212`), its design stroke where it passes PFD
#: 920's 4158 kg/h on its normal case, 54.68 %, and the normal case's xT. V1 runs the valve linear
#: from E003_OP_DES_PCT above, 65.56 %, which the equivalence harness keeps.
PV_329212_OP_DES_PCT = design_stroke_pct(PV_329212, STEAM_PFD_KGH["920"])
PV_329212_XT = PV_329212.normal_case.xt

#: The feed's and the holdup's heat capacities at design [kJ/(kg K)]: the feed is stage 1's melt
#: (V1 ``R324_CP_FEED2``, ``R324_CP_HOLD2``).
CP_FEED2_DES = CP_HOLD1_DES
CP_HOLD2_DES = urea_soln_cp(E003_W_UREA_DES, E003_T_DES_C)

#: The design duty [kW] — stage 1's melt to 140 C and the stage-2 vapour's latent heat — and the
#: conductance [kW/K] that gives it from the design chest (V1 ``R324_E003_Q_DES_KW``,
#: ``R324_E003_UA_KW``); the chest's steam's latent heat [kJ/kg], V1's, the 9-bar header's
#: h_g - h_f (``R324_E003_LAM_STEAM``).
E003_Q_DES_KW = (P1_DES_KGH / 3600.0 * CP_FEED2_DES * (E003_T_DES_C - E001_T_DES_C)
                 + V2_DES_KGH / 3600.0 * E003_LAMBDA_KJKG)
E003_UA_KW = E003_Q_DES_KW / (iapws.tsat_c(E003_PCHEST_DES_BARA) - E003_T_DES_C)
E003_LAMBDA_STEAM_KJKG = H_G_MP_KJKG - H_F_MP_KJKG

#: The melt's residence [s], LIC-324501's set point [%] (V1's, "tagged screenshot") and the
#: holdups [kg] (V1 ``R324_F003_M_*``). LT-324501 reads the barometric leg to 335P001, not the
#: vessel (UD-AU-324-EC-0008; loop summary L 324501, range 0-100 %, no tap distance): the level is
#: V1's holdup ratio (handoff Open data gaps).
F003_M_TAU_S = 180.0
F003_LEVEL_SP_PCT = 54.7
F003_M_DES_KG = P2_DES_KGH / 3600.0 * F003_M_TAU_S
F003_M_FULL_KG = F003_M_DES_KG / (F003_LEVEL_SP_PCT / 100.0)
F003_M_FLOOR_KG = 1.0

#: The false air PIC-324203 admits at design [kg/h], PFD 783 (V1 ``R324_F003_FA_DES``), through
#: PV-324203 on its vendor trim (decision 23's class): the stroke at which Flowserve's Pos. 56 passes
#: it on its sizing case, 92.03 %, where V1 runs the valve linear from 50 %.
F003_FA_DES_KGH = 21.0
PV_324203_OP_DES_PCT = design_stroke_pct(PV_324203, F003_FA_DES_KGH)

#: 324E005's design inlet [kg/h], as V1 writes the trial inlet
#: (``VACUUM_CONDENSERS["324E005"]["inlet_kgh"]``).
E005_INLET_DES_KGH = VACUUM_CONDENSERS["324E005"].inlet_kgh

#: LIC-324501's drain: LV-324501A's design stroke [%] and full-open capacity [kg/h] (V1
#: ``R324_LIC501_OP_DES``, ``R324_LVA_SPAN``), linear as V1 has it: the loop summary gives LV-324501A's
#: cases (8.0 / 70.5 / 82.0 m3/h at 1221 kg/m3, 6.9 -> 3.7 bar a, fail closed) but no vendor
#: sizing sheet is in the archive (Flowserve's summary of items lists no LV-324501; handoff Open data
#: gaps).
LIC_324501_OP_DES_PCT = 75.0
LV_324501_SPAN_KGH = P2_DES_KGH / (LIC_324501_OP_DES_PCT / 100.0)

#: PIC-335201, the 335 melt header [bar g]: the set point above which LV-324501B opens and diverts the
#: melt to 323D002, and the design header (V1 ``R335_LVB_RELIEF_BARG``, ``R335_PIC201_DES_BARG``,
#: V1's approved G12 data; a battery-limit input, the granulator outside the simulated plant).
PIC_335201_RELIEF_BARG = 3.8
PIC_335201_DES_BARG = 3.5

#: The stage-2 species layer, anchored on PFD 401 -> 402 and 709 (V1 ``SOL_E003`` and its
#: ``SOL_STAGES`` row).
E003_LIQUOR = LiquorStage(
    w_des=W_S402,
    anchor=stage_anchor(W_S401, W_S402, P1_DES_KGH, V2_DES_KGH, P2_DES_KGH),
    m_des_kg=F003_M_DES_KG, t_des_c=E003_T_DES_C, p_des_bara=F003_P_DES_BARA,
    tbub_des_c=None, tbub_raoult_des_c=bubble_t_raoult(F003_P_DES_BARA, W_S402),
    alpha_model_des=None)

#: 324F003's pressure bracket for its backward step [bar a] (V1's literals at the call).
F003_P_MIN_BARA = 0.02
F003_P_MAX_BARA = 1.0

#: The stage-2 controllers on the DCS tuning table's rows read per cent of span (decisions 10 and
#: 21, §5 rule 7). Spans: TT-324002 0-160 C (UD-MR-324-EC-0001, T 324002, line D07; the faceplate's
#: scale); PT-329212 0-16 bar g (UD-MR-329-EC-0001, P 329212); PT-324203 -1 to +1 bar g on 324E005's
#: nozzle N10 (UD-MR-324-EC-0001, P 324203); LT-324501 0-100 % (L 324501); all scanned, read from
#: the page images. The table (`References/Master_PID_Tuning_Constants.md`): TIC-324002 2.00 and
#: 300 s; PIC-329212 0.65 and 130 s; PIC-324203 2.00 and 200 s; LIC-324501 0.85 and 200 s. V1 runs
#: TIC-324002 at 2.0 bar/K, PIC-329212 at 0.65 x its chest scale, PIC-324203 at 2.0 %/bar;
#: LIC-324501's 0.85 %/% is already per cent of span.
TT_324002_SPAN_C = 160.0
PT_329212_SPAN_BAR = 16.0
PT_324203_SPAN_BAR = 2.0
TIC_324002_KC = 2.00 * PT_329212_SPAN_BAR / TT_324002_SPAN_C
TIC_324002_TI_S = 300.0
PIC_329212_KC = 0.65 * 100.0 / PT_329212_SPAN_BAR
PIC_329212_TI_S = 130.0
PIC_324203_KC = 2.00 * 100.0 / PT_324203_SPAN_BAR
PIC_324203_TI_S = 200.0
LIC_324501_KC = 0.85
LIC_324501_TI_S = 200.0

__all__ = [
    "F001_P_DES_BARA", "F003_P_DES_BARA", "E001_W_UREA_DES", "E001_T_DES_C", "E003_W_UREA_DES",
    "E003_T_DES_C", "MELT_A_UREA_WATER_K", "E006_P_DES_BARA", "E007_P_DES_BARA", "CW_CP_KJKG_K",
    "lmtd_countercurrent", "CondenserRating", "VACUUM_CONDENSERS",
    "PFD_324_MOL_PCT", "VAC_PFD_KMOLH", "VAC_AIR_MW", "VAC_AIR_FRAC", "CONDENSER_ROWS",
    "EjectorDuty", "F004_DUTY_GAS_KGH", "EJECTOR_DUTIES", "EjectorLoad", "F002_MOTIVE_DES_KGH",
    "F004_MOTIVE_DES_KGH", "F005_MOTIVE_DES_KGH", "EJECTOR_DESIGN_LOADS",
    "FEED_T_DES_C", "U_DES_KGH", "P1_DES_KGH", "V1_DES_KGH", "P2_DES_KGH", "V2_DES_KGH",
    "W_S401_TAB", "W_S402_TAB", "W_S401", "W_S402",
    "F001_VOL_M3", "F001_RHO_L", "F001_MW_VAP", "E001_LAMBDA_KJKG", "E001_PCHEST_DES_BARA",
    "E001_OP_DES_PCT", "PV_329203_OP_DES_PCT", "PV_329203_XT", "CP_FEED1_DES", "CP_HOLD1_DES", "E001_Q_DES_KW", "E001_UA_KW",
    "F001_M_TAU_S", "F001_LEVEL_DES_PCT", "F001_M_DES_KG", "F001_M_FULL_KG", "F001_M_FLOOR_KG",
    "F001_FA_DES_KGH", "PV_324202_OP_DES_PCT", "E002_INLET_DES_KGH", "F010_VAPOUR_DES_KGH",
    "E001_LAMBDA_STEAM_KJKG", "E001_COND_DES_KGH", "E001_COND_LEVEL_SP_PCT", "E001_COND_TAU_S",
    "E001_COND_M_DES_KG", "E001_COND_M_FULL_KG", "E001_COND_M_FLOOR_KG", "LV_329505_OP_DES_PCT", "LV_329505_VENDOR_OP_DES_PCT",
    "LV_329505_SPAN_KGH", "E001_LIQUOR", "PT_LOOP_TOL", "PT_LOOP_MAXIT", "F001_P_MIN_BARA",
    "F001_P_MAX_BARA", "TT_324001_SPAN_C", "PT_329203_SPAN_BAR", "PT_324202_SPAN_BAR",
    "TIC_324001_KC", "TIC_324001_TI_S", "PIC_329203_KC", "PIC_329203_TI_S", "PIC_324202_KC",
    "PIC_324202_TI_S", "LIC_329505_KC", "LIC_329505_TI_S", "LIC_329505_DZ_PCT",
    "F003_VOL_M3", "F003_RHO_L", "F003_MW_VAP", "E003_LAMBDA_KJKG", "E003_PCHEST_DES_BARA",
    "E003_OP_DES_PCT", "PV_329212_OP_DES_PCT", "PV_329212_XT", "CP_FEED2_DES", "CP_HOLD2_DES", "E003_Q_DES_KW", "E003_UA_KW",
    "E003_LAMBDA_STEAM_KJKG", "F003_M_TAU_S", "F003_LEVEL_SP_PCT", "F003_M_DES_KG",
    "F003_M_FULL_KG", "F003_M_FLOOR_KG", "F003_FA_DES_KGH", "PV_324203_OP_DES_PCT",
    "E005_INLET_DES_KGH", "LIC_324501_OP_DES_PCT", "LV_324501_SPAN_KGH", "PIC_335201_RELIEF_BARG",
    "PIC_335201_DES_BARG", "E003_LIQUOR", "F003_P_MIN_BARA", "F003_P_MAX_BARA",
    "TT_324002_SPAN_C", "PT_329212_SPAN_BAR", "PT_324203_SPAN_BAR", "TIC_324002_KC",
    "TIC_324002_TI_S", "PIC_329212_KC", "PIC_329212_TI_S", "PIC_324203_KC", "PIC_324203_TI_S",
    "LIC_324501_KC", "LIC_324501_TI_S",
]
