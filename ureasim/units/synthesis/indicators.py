"""The synthesis loop's displayed indicators — the lags V1's section 6 relaxes them by.

What this models
----------------
Ten indications on screens 322-1 and 322-2 do not show their process value the instant it moves:
a thermowell on a liquid holdup, the HPCC's pressure transmitter on a carbamate inventory, the
N/C analyser on its sample line. Each is relaxed toward its process value with its own time
constant, every tick, so an upstream step ramps the indicator the way the plant's instrument
would. Nothing in the plant reads the lagged values: they are what the consoles show, and the
console packet (`ureasim.engine.packet`) publishes them.

Why a scheduled step and not the packet
---------------------------------------
V1 computes the lags inside ``step_sim``, once per physics step. The implicit Euler weight
``dt / (tau + dt)`` is not additive over steps, so a lag advanced once per console publish — one
plant second under x10 pacing — would not be V1's indicator. A step also puts the lag store in
the plant state, so an exercise saved and restored replays its indicators too.

Source
------
V1 ``backend/main.py`` ``step_sim`` section 6 (8183-8204), with ``_lag1`` (5938, ported as
`ureasim.core.signal.first_order_lag`) and ``react_nc_ratio`` (5899, `ureasim.core.stream.
atom_ratio` on 322R001's atoms). The time constants are `ureasim.data.indicator_lags`.

Equations
---------
    y_k = y_(k-1) + dt / (tau + dt) . (x_k - y_(k-1)),     y_0 = x_0          (each indicator)
    PI-322E002 = min(lag(P_bub, 30 s), 144.2 bar a)
    AT-322701  = lag(N/C of the reactor overflow on an atom basis, 40 s)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ureasim.core.signal import first_order_lag
from ureasim.core.stream import atom_ratio
from ureasim.data.indicator_lags import (
    AT_322701_TAU_S,
    CCW_T_TAU_S,
    EJ_T_TAU_S,
    HPCC_P_DISPLAY_MAX_BARA,
    HPCC_P_TAU_S,
    HPCC_T_TAU_S,
    OFFGAS_T_TAU_S,
    SCRUB_T_TAU_S,
    STRIP_T_TAU_S,
)
from ureasim.data.unit_322r001 import C_ATOMS, N_ATOMS, NC_SPAN_MAX

__all__ = ["IndicatorResult", "SynthesisIndicators"]


@dataclass(frozen=True)
class IndicatorResult:
    """The lagged indications, as the consoles show them [deg C, bar a, -]."""

    tt_322012_c: float      # 322F001's discharge into 322E002
    tt_322013_c: float      # 322E001's top gas into 322E002
    tt_323001_c: float      # downstream of LV-322501, the letdown flash
    tt_322010_c: float      # 322E002's liquid product into 322R001
    pi_322e002_bara: float  # 322E002's bubble-point synthesis pressure
    tt_322002_c: float      # 322E003's overflow to 322F001
    tt_322011_c: float      # 322E003's off-gas into HV-322604
    tt_322011_lp_c: float   # the off-gas downstream of HV-322604
    tt_329125_c: float      # the tempered water's return from 322E003's shell
    at_322701: float        # the reactor overflow's N/C


@dataclass
class SynthesisIndicators:
    """The lag store, keyed as V1's ``s.tlag`` keys it."""

    lag_state: dict = field(default_factory=dict)

    def step(self, t_ejector_c: float, t_top_c: float, tt_323001_c: float, t_prod_c: float,
             p_bub_bara: float, t_overflow_c: float, t_offgas_c: float, t_purge_c: float,
             t_ccw_out_c: float, overflow_kmolh: dict, dt: float) -> IndicatorResult:
        """Relax each indicator one tick toward this tick's process value.

        Process utility
        ---------------
        An operator reading TT-322010 after a feed change sees the condenser's product warm over
        four minutes, as the bundle's metal and holdup make it, not in one step. The lags start
        on their process values, so the design seed shows no boot transient.
        """
        lag = self.lag_state
        nc = atom_ratio(overflow_kmolh, N_ATOMS, C_ATOMS, NC_SPAN_MAX)
        return IndicatorResult(
            tt_322012_c=first_order_lag(lag, "TT322012", t_ejector_c, EJ_T_TAU_S, dt),
            tt_322013_c=first_order_lag(lag, "TT322013", t_top_c, STRIP_T_TAU_S, dt),
            tt_323001_c=first_order_lag(lag, "TT323001", tt_323001_c, STRIP_T_TAU_S, dt),
            tt_322010_c=first_order_lag(lag, "TT322010", t_prod_c, HPCC_T_TAU_S, dt),
            pi_322e002_bara=min(first_order_lag(lag, "HPCCP", p_bub_bara, HPCC_P_TAU_S, dt),
                                HPCC_P_DISPLAY_MAX_BARA),
            tt_322002_c=first_order_lag(lag, "TT322002", t_overflow_c, SCRUB_T_TAU_S, dt),
            tt_322011_c=first_order_lag(lag, "TT322011", t_offgas_c, OFFGAS_T_TAU_S, dt),
            tt_322011_lp_c=first_order_lag(lag, "TT322011l", t_purge_c, OFFGAS_T_TAU_S, dt),
            tt_329125_c=first_order_lag(lag, "TT329125", t_ccw_out_c, CCW_T_TAU_S, dt),
            at_322701=first_order_lag(lag, "AT322701", nc, AT_322701_TAU_S, dt),
        )
