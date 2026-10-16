"""322E003's tempered cooling water — 329P006 A/B, FIC-329409 and TIC-329005, as V1 steps them.

What this models
----------------
The loop that removes the scrubber's carbamate-formation exotherm. Two hand-rolled controllers on
first-order plant lags:

  * **FIC-329409** (reverse acting): the flow's steady value follows FV-329409's trim about its
    design stroke, times whether either circulation pump runs (either alone gives the full head;
    neither, none);
        F_ss = F_des . phi(op) / phi(op_des) . f_pump,     tau_F dF/dt = F_ss - F;
    phi Metso's Neldisc on its printed points from 46.85 % (decided 2026-10-15, decision 108's
    class); V1 runs it linear from 60 %, ``CcwLoop(**V1_FV_329409)``, which the harness keeps.
  * **TIC-329005** (direct acting): the supply temperature's steady value falls linearly as
    TV-329005 opens its cooler branch, and rises with the reactor's load departure, which warms the
    returning water,
        T_ss = clamp(T_out,des - (T_out,des - T_in,des) . op / op_des
                     + G ((s - 1) + delta_X), 20, T_out,des),     tau_T dT/dt = T_ss - T.

Each runs a velocity-form PI on its own PV in AUTO, P on the PV, I on the error, so a steady PV at
its set point moves nothing; a non-finite PV holds the design (L3-9). The scrubber reads the
lagged FT-329409 as the circulation and TIC-329005's PV as the supply temperature. The tunings are
the DCS table's rows on the transmitters' spans (decision 10's class, applied 2026-10-07): a 10 %
flow cut settles in about an hour and a 5 K supply step in more than an hour, where V1's tunings
settle them in two and five minutes.

Source: V1 ``backend/main.py`` ``step_sim`` 7992-8028; `data.unit_329_ccw`, `data.unit_322e003`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ureasim.control.process_loop import pv_ok
from ureasim.control.valve import cv_fraction
from ureasim.core.numeric import clamp
from ureasim.data.control_valves import FV_329409
from ureasim.data.unit_322e003 import CCW_KGH_DES, CCW_T_IN_DES_C, CCW_T_OUT_DES_C
from ureasim.data.unit_329_ccw import (
    FIC_329409_KC,
    FIC_329409_TAU_S,
    FIC_329409_TI_S,
    FV_329409_OP_DES_PCT,
    FV_329409_TRIM_OP_DES_PCT,
    TIC_329005_KC,
    TIC_329005_LOAD_GAIN_K,
    TIC_329005_T_SS_MIN_C,
    TIC_329005_TAU_S,
    TIC_329005_TI_S,
    TV_329005_OP_DES_PCT,
)

__all__ = ["FV_329409_TRIM", "V1_FV_329409", "CcwResult", "CcwLoop"]

#: FV-329409 as the port runs it — its design stroke and Metso's Neldisc on its printed points
#: (decided 2026-10-15) — and CcwLoop's fields as V1 runs it, linear from 60 %, which the
#: equivalence harness keeps: ``CcwLoop(**V1_FV_329409)``.
FV_329409_TRIM = (FV_329409_TRIM_OP_DES_PCT, FV_329409.characteristic)
V1_FV_329409 = {"fv_329409": None, "fic_op": FV_329409_OP_DES_PCT}


@dataclass(frozen=True)
class CcwResult:
    """The tempered water the scrubber sees on this tick."""

    #: FT-329409's circulation [kg/h], floored at 1 g/h.
    m_ccw_kgh: float
    #: TIC-329005's supply temperature [deg C].
    t_ccw_in_c: float
    #: 1.0 with either 329P006 running, 0.0 with neither.
    pump_frac: float
    #: FV-329409's and TV-329005's strokes [%].
    fv_329409_pct: float
    tv_329005_pct: float


@dataclass
class CcwLoop:
    """The two controllers' faceplates and the two pumps, seeded on the design (V1 ``State``)."""

    p329p006a: bool = True
    p329p006b: bool = False
    fic_mode: str = "AUTO"
    fic_op: float = FV_329409_TRIM_OP_DES_PCT
    fic_sp: float = CCW_KGH_DES / 1000.0          # t/h
    fic_pv: float = CCW_KGH_DES / 1000.0
    fic_pv_prev: float = CCW_KGH_DES / 1000.0
    tic_mode: str = "AUTO"
    tic_op: float = TV_329005_OP_DES_PCT
    tic_sp: float = CCW_T_IN_DES_C
    tic_pv: float = CCW_T_IN_DES_C
    tic_pv_prev: float = CCW_T_IN_DES_C
    #: FV-329409's design stroke [%] and trim; None is V1's linear valve from 60 %.
    fv_329409: tuple | None = FV_329409_TRIM

    def step(self, co2_scale: float, delta_x: float, dt: float) -> CcwResult:
        """Advance both loops one tick on the reactor's load ratio and conversion deficit."""
        pump_frac = 1.0 if (self.p329p006a or self.p329p006b) else 0.0

        # FIC-329409.
        if not pv_ok(self.fic_sp, self.fic_op, self.fic_pv):
            if not math.isfinite(self.fic_op):
                self.fic_op = (FV_329409_OP_DES_PCT if self.fv_329409 is None
                               else self.fv_329409[0])
            self.fic_pv = (CCW_KGH_DES / 1000.0) * pump_frac
        else:
            if self.fv_329409 is None:
                stroke = self.fic_op / max(FV_329409_OP_DES_PCT, 1e-6)
            else:
                op_des, trim = self.fv_329409
                stroke = cv_fraction(self.fic_op / 100.0, trim) / cv_fraction(op_des / 100.0, trim)
            flow_ss = (CCW_KGH_DES / 1000.0) * stroke * pump_frac
            pv_prev = self.fic_pv_prev
            self.fic_pv += (dt / FIC_329409_TAU_S) * (flow_ss - self.fic_pv)
            if self.fic_mode == "AUTO":
                self.fic_op = clamp(self.fic_op + FIC_329409_KC * (
                    -(self.fic_pv - pv_prev) + (dt / FIC_329409_TI_S) * (self.fic_sp - self.fic_pv)),
                    0.0, 100.0)
            self.fic_pv_prev = self.fic_pv

        # TIC-329005.
        if not pv_ok(self.tic_sp, self.tic_op, self.tic_pv):
            if not math.isfinite(self.tic_op):
                self.tic_op = TV_329005_OP_DES_PCT
            self.tic_pv = CCW_T_IN_DES_C
        else:
            t_load = TIC_329005_LOAD_GAIN_K * ((co2_scale - 1.0) + delta_x)
            t_ss = clamp(CCW_T_OUT_DES_C - (CCW_T_OUT_DES_C - CCW_T_IN_DES_C)
                         * (self.tic_op / max(TV_329005_OP_DES_PCT, 1e-6)) + t_load,
                         TIC_329005_T_SS_MIN_C, CCW_T_OUT_DES_C)
            pv_prev = self.tic_pv_prev
            self.tic_pv += (dt / TIC_329005_TAU_S) * (t_ss - self.tic_pv)
            if self.tic_mode == "AUTO":
                self.tic_op = clamp(self.tic_op + TIC_329005_KC * (
                    (self.tic_pv - pv_prev) + (dt / TIC_329005_TI_S) * (self.tic_pv - self.tic_sp)),
                    0.0, 100.0)
            self.tic_pv_prev = self.tic_pv

        return CcwResult(m_ccw_kgh=max(self.fic_pv, 1e-6) * 1000.0, t_ccw_in_c=self.tic_pv,
                         pump_frac=pump_frac, fv_329409_pct=self.fic_op,
                         tv_329005_pct=self.tic_op)
