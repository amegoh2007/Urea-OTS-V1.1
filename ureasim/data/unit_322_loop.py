"""The HP synthesis loop's pressure node, PT-329201, and its trips — V1's constants.

What this is
------------
The numbers V1's loop-pressure integration and the synthesis trips run on (``main.py`` 4945-5110,
10086-10181, 10345-10445). Several are V1's own assumptions or back-solved residuals and say so;
the loop's flagged sinks (As-Built Part LVI, handoff B-75 to B-78) are carried here as V1 writes
them, until the process engineer decides them.

Source: V1 ``backend/main.py``; Sempell's orifice selection for SV32251 / SV32252
(`data.relief_devices`); the vendor's arrangement drawings for the loop's volumes and the PFD for
322E002's liquor (handoff B-77 (b), decided 2026-10-09).
"""

from __future__ import annotations

from ureasim.core.stream import MW_COMP
from ureasim.data.design_point import STRIP_BOT_DES_KGH
from ureasim.data.relief_devices import RELIEF_DEVICES, RELIEF_SIZING
from ureasim.data.unit_320 import SYN_P_DES_BARA
from ureasim.data.unit_321 import CO2_DES_KGH
from ureasim.data.unit_322e002 import P_DES_BARA as HPCC_P_DES_BARA
from ureasim.data.unit_322e003 import OFFGAS_DES_KMOLH
from ureasim.data.unit_322e002 import T_PROD_DES_C as HPCC_T_PROD_DES_C
from ureasim.data.unit_322f001 import MOTIVE_DES_KGH
from ureasim.data.unit_322r001 import FEED_W_UREA_DES, OVERFLOW_RHO
from ureasim.data.unit_322r001 import TOP_P_DES_BARA as REACT_TOP_P_DES_BARA
from ureasim.data.unit_323e003 import E003_M308_DES_KGH
from ureasim.thermo.empirical import urea_soln_rho

__all__ = [
    "SYN_P_TAU_MIN", "V_R001_M3", "V_E001_M3", "V_E002_M3", "V_E003_M3", "SYN_LOOP_V_M3",
    "RHO_E002_LIQ", "BUFFER_DLN_FRAC", "LIQUOR_DP_DES_BAR", "REACT_FEED_DP_DES_BAR",
    "REACT_FEED_RHO_DES_LIVE",
    "SYN_LOOP_IN_DES_KGH", "SYN_LOOP_OUT_DES_KGH",
    "SYN_LOOP_RESID_DES_KGH", "SYN_P_FLOOR_BARA", "SYN_P_CEILING_BARA",
    "LOOP_LEVEL_NLL_SUM_PCT",
    "SV32251_SET_BARA", "SV32251_RESEAT_BARA", "SV32251_CAP_KGH", "SV32251_P_REL_BARA",
    "SV32251_T_REL_K", "SV32251_MW_REL", "SV32251_Z_REL", "SV32251_K", "SV32251_COUNT",
    "TRIP_22_2_BARA", "TRIP_22_2_RESET_BARA", "TRIP_21_2_PUMPS_TD_S", "TRIP_21_2_P001_TD_S",
    "TRIP_21_2_FY_TD_S", "TRIP_21_8_RUN_TD_S", "TRIP_21_8_STOP_TP_S", "TRIP_21_8_PDY_L2_BAR",
    "TRIP_21_2_FY_L2_FRAC",
]

# ======================================================================================
# PT-329201, the loop's vapour inventory (handoff B-77 (b))
# ======================================================================================

#: The loop's vapour-inventory time constant [min]: the uncondensed backlog passes the scrubber's
#: shell again on it, a fraction cool_frac condensing each pass. Source: V1 ``SYN_P_TAU_MIN``.
SYN_P_TAU_MIN = 4.0

#: The loop's process-side volumes [m3], read in session 40 from the vendor's arrangement drawings,
#: each visually verified: 322R001 185.4 (UD-AU-322-DZ-0006-003; Uhde's data sheet's 171.00 m3 is
#: the shell between tangents), 322E001 24.7 (UD-AU-322-DZ-0003-003), 322E002 21.6
#: (UD-AU-322-DZ-0004-003) and 322E003 10.0 (UD-AU-322-DZ-0005-003). Every one is open to the loop's
#: gas, so the vapour inventory is their sum less the liquid the model holds in them (decision 68's
#: class). They replace V1's lumped 1500 kg/bar (``SYN_LOOP_C_KG_PER_BAR``, report A-1: "still a
#: lumped constant, not a vapour-space EOS"; decided 2026-10-09, handoff B-77 (b)).
V_R001_M3 = 185.4
V_E001_M3 = 24.7
V_E002_M3 = 21.6
V_E003_M3 = 10.0
SYN_LOOP_V_M3 = V_R001_M3 + V_E001_M3 + V_E002_M3 + V_E003_M3

#: 322E002's carbamate liquor to 322R001 [kg/m3]: the volume LT-322E002's holdup takes in the
#: vessel. Source: PFD, "Carb. Liq." at 170 C and 144.2 bar a.
RHO_E002_LIQ = 1139.0

#: The step of the central difference that reads the reactor liquor's buffering off the Extended
#: UNIQUAC bubble pressure [kg of loop gas per kg of liquor] (`loop_pressure`). A numerical choice,
#: not a datum: 1e-3 and 1e-2 forward agree to 0.7 %, and the central difference at 1e-3 is
#: converged well inside that.
BUFFER_DLN_FRAC = 1.0e-3

#: 322E002's outlet over PT-329201 at design [bar], 3.5: the PFD's 144.2 bar a at the
#: condenser's outlet, where PI-322E002 reads the melt's bubble pressure at 170 C
#: (`data.unit_322e002`), less the loop's 140.7, written as a subtraction of the two design
#: pressures (A-13). The loop's liquor is at its bubble point at design, so PI-322E002 less this
#: differential is the loop pressure the liquor holds (`liquor_saturation`; decided 2026-10-10,
#: handoff B-91 (a)).
LIQUOR_DP_DES_BAR = HPCC_P_DES_BARA - SYN_P_DES_BARA

#: 322R001's feed line at design [bar], 2.9: 322E002's outlet at the PFD's 144.2 bar a (streams 202
#: and 205) less the reactor's top at 141.3 (streams 203 and 207), written as a subtraction of the
#: two design pressures (A-13). The design drop the published PT on 322R001 is normalised against
#: (`loop_hydraulics.reactor_bara`; decided 2026-10-22, handoff B-112).
REACT_FEED_DP_DES_BAR = HPCC_P_DES_BARA - REACT_TOP_P_DES_BARA

#: The feed line's design density [kg/m3], about 752.2: the urea-solution correlation V1's line
#: uses, at the design seed's feed (`unit_322r001.FEED_W_UREA_DES`) and 322E002's 170.0 C product,
#: so the line's density ratio is exactly 1.0 at design (handoff B-112), as
#: `unit_322r001.OVERFLOW_RHO_DES_LIVE` is the stripper's. V1 normalises on the nominal 990, which
#: the correlation returns only at its own reference state.
REACT_FEED_RHO_DES_LIVE = urea_soln_rho(FEED_W_UREA_DES, HPCC_T_PROD_DES_C, OVERFLOW_RHO)

#: The boundary's design flows [kg/h] and the residual they leave, +2024.9: in, the motive on its
#: re-pin (42 762.05), PFD 101's CO2 and 323E003's 308; out, PFD 208's bottoms and PFD 204's vent.
#: V1 credits the residual back through the loop-mass fraction so PT-329201 holds at the seed; it
#: is the mirror of the recycle tear subtracted inside the reactor (flagged, handoff B-75).
#: Source: V1 ``SYN_LOOP_IN_DES_KGH``, ``SYN_LOOP_OUT_DES_KGH``, ``SYN_LOOP_RESID_DES_KGH``.
SYN_LOOP_IN_DES_KGH = MOTIVE_DES_KGH + CO2_DES_KGH + E003_M308_DES_KGH
SYN_LOOP_OUT_DES_KGH = STRIP_BOT_DES_KGH + sum(OFFGAS_DES_KMOLH[k] * MW_COMP[k] for k in MW_COMP)
SYN_LOOP_RESID_DES_KGH = SYN_LOOP_IN_DES_KGH - SYN_LOOP_OUT_DES_KGH

#: The integration's clamp [bar a]. Source: V1's literals in ``step_sim`` 10443.
SYN_P_FLOOR_BARA = 10.0
SYN_P_CEILING_BARA = 180.0

#: The three liquid inventories' normal levels summed [%]: LT-322504's 80, LT-322E002's 50 and
#: LIC-322501's 50 — the loop-mass fraction's denominator. Source: V1 ``m_loop_frac``.
LOOP_LEVEL_NLL_SUM_PCT = 80.0 + 50.0 + 50.0

# ======================================================================================
# SV32251 / SV32252 on 322R001 (decision 32's class, handoff A-16)
# ======================================================================================

#: Set 159.0 bar g on the sheets' atmosphere; reseat 10 % of set below (Sempell); each certified
#: for 116 667 kg/h of carbamate gas on a lift-limited K orifice, alpha_w 0.732, at 183 C, M 24.0,
#: k 1.010, Z 0.78 and the set pressure plus 10 %. Two alike, lifting and reseating together.
#: V1 relieves the loop through one assumed SV-32201 instead (set 161.01 bar a, 200 t/h).
SV32251_SET_BARA = RELIEF_DEVICES["SV32251"].set_bara
SV32251_RESEAT_BARA = RELIEF_SIZING["SV32251"].reseat_bara(RELIEF_DEVICES["SV32251"])
SV32251_CAP_KGH = RELIEF_SIZING["SV32251"].capacity_kgh
SV32251_P_REL_BARA = RELIEF_SIZING["SV32251"].relieving_bara(RELIEF_DEVICES["SV32251"])
SV32251_T_REL_K = RELIEF_SIZING["SV32251"].t_c + 273.15
SV32251_MW_REL = RELIEF_SIZING["SV32251"].mw
SV32251_Z_REL = RELIEF_SIZING["SV32251"].z
SV32251_K = RELIEF_SIZING["SV32251"].k
SV32251_COUNT = 2

# ======================================================================================
# The synthesis trips (V1's initiators)
# ======================================================================================

#: Trip 22.2, synthesis high-high: trips at 155.0 bar a, its reset blocked above 148.0. V1's
#: ASSUMPTION — no trip schedule in References carried the set point, and 22.2's logic is not in
#: AC4's application software (XV-322902 is commanded from the Safeguard SG1); kept by the process
#: engineer's decision of 2026-10-09 (handoff A-12). Source: V1 ``SYN_P_TRIP_BARA``,
#: ``SYN_P_TRIP_RESET_BARA``.
TRIP_22_2_BARA = 155.0
TRIP_22_2_RESET_BARA = 148.0

#: AC4 PC21's timers [s] (UD-MR-G00-FF-0004): TRIP_21_2_FLAG1's 5 s on the HP ammonia pumps
#: running, 15 s on 323P001A / B running and 5 s on FY-322403 above its L2 (page 20); each pump's
#: flag's 5 s from its start to XV-322901 open and 10 s after it stops (pages 5 and 7).
TRIP_21_2_PUMPS_TD_S = 5.0
TRIP_21_2_P001_TD_S = 15.0
TRIP_21_2_FY_TD_S = 5.0
TRIP_21_8_RUN_TD_S = 5.0
TRIP_21_8_STOP_TP_S = 10.0

#: PDY-321203 / 204's L2 [bar], the sub-cooling margin that trips its pump (21.8 / 21.10): the
#: functional diagram's PDYSLL at 0.1 bar (UD-MR-321-FF-0002 page 5), the number V1's 21.2 used.
TRIP_21_8_PDY_L2_BAR = 0.1

#: FY-322403's L2 [-, of the design CO2], the CO2 flow below which 21.2 trips: a DCS database value
#: the archive does not hold; V1's 21.4 threshold, 5 %, stands in (decided 2026-10-09, handoff Open
#: data gaps). Source: V1 ``step_sim`` 10101.
TRIP_21_2_FY_L2_FRAC = 0.05
