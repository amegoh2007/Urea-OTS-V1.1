"""323D002 — unit 323's fourth stage, the urea solution tank: the design basis.

What this equipment is
----------------------
The pre-evaporator's 80 % product (PFD 317) drains into Compartment I of the atmospheric 323D002,
the flow-through zone the 323P003A/B pumps take from and LV-324501B's melt recycle returns to;
Compartment II, behind the internal baffle, is a passive buffer with no nozzle of its own.
LIC-323507 holds Compartment I at about 10 % by cascading onto FIC-324401, which sends the solution
through FV-324401 to the evaporators (PFD 324).

This module carries the compartments' volumes and design holdups, FV-324401's trim and the two
stage-4 controllers. Moved out of `unit_323` unchanged (2026-10-23, the housekeeping split);
`unit_323` re-exports every name.

Sources
-------
* ``References/323D002.md`` §3.2 and §3.3 — the two compartments and the level set point.
* V1 ``backend/main.py``, the unit-323 constant block and ``State.__init__`` — the volumes, the set
  point, the floor and V1's tuning. Each carries its provenance.
* Uhde loop summary for unit 324, UD-MR-324-EC-0001 rev 1 (the vendor archive) — FT-324401's
  calibrated range.
* The plant DCS tuning table, ``References/Master_PID_Tuning_Constants.md`` — FIC-324401's row.
* Flowserve's calculation sheet for FV-324401 (`ureasim.data.control_valves`) — its trim and design
  stroke.
* The design flow chain and the liquor's density live in `ureasim.data.design_point`.
"""

from __future__ import annotations

from ureasim.data.control_valves import FV_324401, design_stroke_pct
from ureasim.data.design_point import R323_D002_RHO, R323_M324_DES

# ======================================================================================
# 323D002 — the urea solution tank, stage 4
# ======================================================================================

#: Compartment volumes [m3]. Compartment I is the active flow-through zone: the 323F010 drain,
#: the 323P003A/B suction and the LV-324501B melt recycle all land in it. Compartment II is the
#: passive buffer behind the internal baffle, dry in normal operation, with no nozzle of its
#: own. Source: `References/323D002.md` §3.2 and §3.3; V1 `main.py` R323_D002_VOL_I_M3 and
#: R323_D002_VOL_II_M3.
D002_VOL_I_M3 = 80.0
D002_VOL_II_M3 = 300.0

#: LIC-323507 set point [%]. Deliberately low: the licensor holds Compartment I at about 10 %
#: so the active residence stays near six minutes (8 m3 against 80.6 m3/h), because the
#: ammonia that suppresses biuret formation has already been flashed off at 80 % urea and
#: 99 C. Source: `References/323D002.md` §3.2; V1 `main.py` R323_D002_LVL_SP.
D002_LVL_SP_PCT = 10.0

#: FV-324401, the solution to the evaporators: a Valtek modified equal-percentage trim, Kvs 160.
#: DECIDED 2026-09-30 (handoff B-44): it runs its vendor trim from the stroke at which its Kvs
#: passes PFD 324 on the vendor's normal case, 72.36 %, where V1 runs it linear from 50 %
#: (R323_FV401_OP_DES).
FV401_OP_DES_PCT = design_stroke_pct(FV_324401, R323_M324_DES)
FV401_CHAR = FV_324401.characteristic

#: Compartment I at 100 % and at its set point [kg], on the PFD density. The live spans are
#: taken on the live density at run time; these fix only the design seed.
D002_M_I_FULL_KG = D002_VOL_I_M3 * R323_D002_RHO
D002_M_I_DES_KG = D002_M_I_FULL_KG * (D002_LVL_SP_PCT / 100.0)

#: Floor on the Compartment I holdup [kg]. Source: V1 `main.py` step_sim, ``max(..., 1.0)``.
D002_M_I_FLOOR_KG = 1.0

# --- The stage-4 controllers ------------------------------------------------------------
# LIC-323507 (Compartment I level, master) -> FIC-324401 (product flow, slave) -> FV-324401.
# Source: V1 `main.py` State.__init__.

#: LIC-323507: DIRECT acting; output is the product-flow demand [t/h], 0 to 150. The loop has
#: no row in the plant DCS table. V1's note: "faceplate missing: Ti = hydraulic settling time
#: V_I/Q = 80/(92.75/1.3) ~ 4030 s" — Compartment I's full volume over the design flow, on the
#: retired 1300 kg/m3 density; 3574 s on the PFD's 1151.
LIC_323507_KC = 1.0
LIC_323507_TI_S = 4030.0
LIC_323507_OP_HI_TH = 150.0

#: FIC-324401's gain as the DCS table gives it [% of output per % of span]: 0.40, with Ti 30 s,
#: Td -1 s, Tf 0. Source: `References/Master_PID_Tuning_Constants.md`; V1 `main.py`
#: State.__init__ seeds the same numbers but applies the gain per t/h. The table's 2 % deadband
#: is not carried by V1 (handoff B-28).
FIC_324401_KC_TABLE = 0.4

#: FT-324401's calibrated range: 0 to 110 m3/h, volume flow, a magnetic inductive meter on
#: 323P003A/B's discharge. Source: Uhde loop summary UD-MR-324-EC-0001 rev 1, loop F 324401, sheet
#: 1/2, line D07 (vendor archive, scanned, read from the page image): "Disch. 323P003A/B US Pump",
#: line 150-US9-323255, 51.1 / 80.5 / 100.0 m3/h, 99 C. The loop runs in t/h, so the span is carried
#: to mass on the liquor's design density, PFD 317's 1151 kg/m3 — the density this port converts
#: the stream with; the sheet's own 1174.0 kg/m3 does not reproduce its 80.5 m3/h normal flow from
#: the PFD's.
FT_324401_SPAN_M3H = 110.0
FT_324401_SPAN_TH = FT_324401_SPAN_M3H * R323_D002_RHO / 1000.0

#: FIC-324401: output is the FV-324401 stroke [%]; set-point span 0 to 150 t/h. The table's gain
#: rescaled to t/h, 0.40 %/% on 126.6 t/h, 0.316 %/(t/h); V1 runs 0.40, and the port departs from
#: it by decision of 2026-09-30 (handoff B-41).
FIC_324401_KC = FIC_324401_KC_TABLE * 100.0 / FT_324401_SPAN_TH
FIC_324401_TI_S = 30.0
FIC_324401_TD_S = -1.0
FIC_324401_SP_HI_TH = 150.0

#: FT-324401 time constant [s]: the transmitter plus the valve's stroke dynamics. The valve is a
#: pure gain of 1.855 t/h per %, and an UNLAGGED velocity-form PV puts a loop pole at -Kc . G.
#: V1's note gives |z| = 2.78, which is Kc 1.5 — an earlier tuning — and would diverge; at V1's
#: Kc 0.4 the pole is -0.74, and at the port's 0.316 -0.59, stable but ringing tick to tick. The
#: lag removes it. Source:
#: V1 `main.py` step_sim, ``_lag1(..., 5.0, dt)``.
FT_324401_TAU_S = 5.0

__all__ = [
    "D002_VOL_I_M3", "D002_VOL_II_M3", "D002_LVL_SP_PCT", "FV401_OP_DES_PCT", "FV401_CHAR",
    "D002_M_I_FULL_KG", "D002_M_I_DES_KG", "D002_M_I_FLOOR_KG", "LIC_323507_KC", "LIC_323507_TI_S",
    "LIC_323507_OP_HI_TH", "FIC_324401_KC_TABLE", "FT_324401_SPAN_M3H", "FT_324401_SPAN_TH",
    "FIC_324401_KC", "FIC_324401_TI_S", "FIC_324401_TD_S", "FIC_324401_SP_HI_TH",
    "FT_324401_TAU_S",
]
