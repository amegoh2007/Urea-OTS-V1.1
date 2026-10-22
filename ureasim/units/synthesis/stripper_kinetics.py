"""322E001's two side reactions — urea hydrolysis and biuret formation in the falling film.

What this models
----------------
The urea the HP stripper loses on its way through the tubes, on real rate laws anchored on the
PFD's extents (`stripper.stripper_322e001` calls both on every tick):

  * **Hydrolysis**, Urea + H2O -> 2 NH3 + CO2: the second-order Inoue-Otsuka group
    ``k(T) . C_urea . C_H2O . V_liq`` as a ratio on its own design value, times the PFD extent.
  * **Biuret**, 2 Urea -> Biuret + NH3: second order in urea, Arrhenius in the bottoms'
    temperature, over the same live liquid volume, times the PFD extent.

Each extent is capped by the reagents actually present. Both are exactly their PFD extents at
the design state.

Source: V1 ``backend/main.py`` `stripper_322e001`, its reaction block; moved here from
`stripper` unchanged (2026-10-22, session 64) to keep that module inside its line target.
"""

from __future__ import annotations

import math

from ureasim.data.unit_322e001 import (
    BIURET_EA_JMOL,
    BIURET_R_GAS_J,
    BIURET_T_DES_K,
    FEED_UREA_DES_KMOLH,
    HYDROLYSIS_T_DES_C,
    V_LIQ_DES_M3,
    VDOT_DES_M3H,
    XI_BIURET_DES,
    XI_HYDROLYSIS_DES,
)
from ureasim.data.unit_322e001 import FEED_DES_KMOLH as _FEED_DES_KMOLH
from ureasim.thermo.kinetics import urea_hydrolysis_k_m3_kmol_h

__all__ = ["hydrolysis_rate_group", "HYDROLYSIS_GROUP_DES", "hydrolysis_extent",
           "biuret_extent"]


def hydrolysis_rate_group(t_c: float, urea_kmolh: float, h2o_kmolh: float,
                          vdot_m3h: float, v_liq_m3: float) -> float:
    """Second-order Inoue-Otsuka group ``k(T) . C_urea . C_H2O . V_liq`` [kmol/h].

    Process utility
    ---------------
    This is the part of the stripper's urea loss that CAN be predicted from first principles:
    how the extent moves with temperature, with how concentrated the melt is, and with how
    much liquid is being held. It is used as a RATIO against its own design value, so the
    units and any common factor cancel and only that movement survives.

    Why a ratio and not an absolute extent
    ---------------------------------------
    Evaluated at this stripper's own design state the law returns about 12 kmol/h over the
    whole bundle, or 17.5 kmol/h with the sump flooded as well, against a PFD extent of 88.1.
    It would need a liquid fraction of 7.3 where the physical maximum is 1. The PFD constant
    therefore is not urea hydrolysis alone — it almost certainly lumps carbamate
    decomposition, which is what the stripper is for — so predicting it from a hydrolysis rate
    law would be fitting a rate constant to a different reaction. The PFD extent stays the
    anchor and this supplies the departure.

    Concentrations are per unit of VOLUMETRIC throughput, which is the falling film's own
    basis. A zero or negative throughput returns 0.0 rather than dividing: an empty tube
    hydrolyses nothing.
    """
    if vdot_m3h <= 1e-9 or v_liq_m3 <= 0.0:
        return 0.0
    c_urea = max(urea_kmolh, 0.0) / vdot_m3h
    c_h2o = max(h2o_kmolh, 0.0) / vdot_m3h
    return urea_hydrolysis_k_m3_kmol_h(t_c) * c_urea * c_h2o * v_liq_m3


#: The rate group at the design state [kmol/h] — the denominator that makes the departure
#: exactly 1.0 there. Derived from the design constants, never entered.
HYDROLYSIS_GROUP_DES = hydrolysis_rate_group(
    HYDROLYSIS_T_DES_C, _FEED_DES_KMOLH["Urea"], _FEED_DES_KMOLH["H2O"],
    VDOT_DES_M3H, V_LIQ_DES_M3)


def hydrolysis_extent(t_bot_c: float, urea_kmolh: float, h2o_kmolh: float,
                      vdot_m3h: float, v_liq_m3: float) -> float:
    """Urea hydrolysed in the tubes [kmol/h]: the PFD extent times the rate law's departure.

    Process utility
    ---------------
    The holdup tracks the LIVE sump level, so a level or throughput excursion moves the
    extent. The extent can never exceed either reagent that is actually present.
    """
    group = hydrolysis_rate_group(t_bot_c, urea_kmolh, h2o_kmolh, vdot_m3h, v_liq_m3)
    xi_hyd_raw = XI_HYDROLYSIS_DES * (group / HYDROLYSIS_GROUP_DES
                                      if HYDROLYSIS_GROUP_DES > 0.0 else 1.0)
    return max(min(xi_hyd_raw, urea_kmolh, h2o_kmolh), 0.0)


def biuret_extent(t_bot_k: float, urea_kmolh: float, vdot_m3h: float, v_liq_m3: float,
                  urea_after_hyd: float) -> float:
    """Biuret formed in the tubes, 2 Urea -> Biuret + NH3 [kmol/h].

    Process utility
    ---------------
    SECOND order in urea, because that is the stoichiometry, and integrated over the same
    live liquid volume. A deep turndown — more urea-rich melt sitting longer — raises it,
    which is exactly what happens on the plant and is why biuret is a turndown problem.
    The extent can never consume more than the urea left after hydrolysis, at 2 per biuret.
    """
    xi_biu_raw = (XI_BIURET_DES
                  * math.exp((BIURET_EA_JMOL / BIURET_R_GAS_J)
                             * (1.0 / BIURET_T_DES_K - 1.0 / t_bot_k))
                  * (urea_kmolh / FEED_UREA_DES_KMOLH) ** 2
                  * (VDOT_DES_M3H / vdot_m3h) * (v_liq_m3 / V_LIQ_DES_M3))
    return max(min(xi_biu_raw, 0.5 * urea_after_hyd), 0.0)
