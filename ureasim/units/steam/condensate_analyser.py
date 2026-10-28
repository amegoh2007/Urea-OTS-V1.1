"""AI-329701 — the conductivity analyser on 329D001, the steam condensate tank.

What this models
----------------
The DCS conductivity measurement on the low-pressure condensate collected in 329D001 (Uhde's loop
summary UD-MR-329-EC-0001 rev 1, A 329701: function AI, realised in the control system with a high
alarm and a high-high safety alarm, 0-30 uS/cm on the plant DCS, on line 0-CPL2-329D001; P&ID 107/2). Clean steam
condensate is nearly pure water; ammonia and carbon dioxide dissolved in it ionise as ammonium and
bicarbonate, and a few milligrams a litre take the reading off its scale. On the plant it is the
instrument that shows process leaking into the steam system — a 322E002 tube leak (handoff B-82)
puts the loop's ammonia and CO2 into the LP header, and the users' condensate brings them to
329D001. Decided 2026-10-09 (handoff B-90): the leak's contamination is shown on AI-329701. The
archive draws no analyser on 322D001A/B or their blowdown (A 329702 on 322E002's shell condensate is
a local sample probe), and the urea a leak leaves in the drums' water does not conduct.

Equations
---------
    c     = min(n_NH3, n_CO2) / Q_condensate                 [mol/L] ammonium bicarbonate
    kappa = kappa_w + (lambda_NH4 + lambda_HCO3) . c . 1000  [uS/cm]
    PV    = min(kappa, 10)                                   the transmitter's range
    AH    = kappa > 15,   AHH = kappa > 18                   the plant DCS's H1 and H2 (2026-10-13)

The leak's ammonia and CO2 are taken whole into the condensate of the LP users' steam; the CO2,
the lesser in a synthesis liquor, pairs with as much ammonia as ammonium bicarbonate at infinite
dilution, and the excess ammonia, a weak base suppressed by the ammonium, is neglected. 329D001's
holdup is not modelled, so the reading follows the leak on the tick (its mixing lag an open data
gap: the tank's working volume).

Source: the loop summary above; the limiting ionic conductivities and pure water's conductivity,
CRC Handbook of Chemistry and Physics (`ureasim.data.unit_329`).
"""

from __future__ import annotations

from ureasim.data.unit_329 import (
    AI_329701_H1_US_CM,
    AI_329701_H2_US_CM,
    AI_329701_SPAN_US_CM,
    KAPPA_WATER_US_CM,
    LAMBDA0_HCO3_SCM2,
    LAMBDA0_NH4_SCM2,
)

__all__ = ["condensate_conductivity_us_cm", "ai_329701_reading", "ai_329701_alarms"]


def condensate_conductivity_us_cm(n_nh3_kmolh: float, n_co2_kmolh: float,
                                  m_condensate_kgh: float) -> float:
    """The LP condensate's conductivity at 25 C [uS/cm].

    Process utility
    ---------------
    What AI-329701 sees of the ammonia and CO2 a tube leak puts into the steam: the condensate's
    ammonium bicarbonate, on the ions' limiting conductivities, over pure water's own. With no
    contamination it reads pure water, 0.055 uS/cm.

    Equation
    --------
        c     = min(n_NH3, n_CO2) . 1000 / Q        [mol/L, a dilute condensate's litre a kilogram]
        kappa = kappa_w + (lambda_NH4 + lambda_HCO3) . c . 1000
    """
    if m_condensate_kgh <= 0.0:
        return KAPPA_WATER_US_CM
    c_mol_l = max(min(n_nh3_kmolh, n_co2_kmolh), 0.0) * 1000.0 / m_condensate_kgh
    return KAPPA_WATER_US_CM + (LAMBDA0_NH4_SCM2 + LAMBDA0_HCO3_SCM2) * c_mol_l * 1000.0


def ai_329701_reading(kappa_us_cm: float) -> tuple[float, bool]:
    """AI-329701's reading and whether it is over its range.

    Process utility
    ---------------
    The transmitter spans 0-30 uS/cm; past its upper range value it reads the top of its scale,
    and the operator sees an analyser pinned at 30 with its high-high alarm, not the number.
    """
    return min(kappa_us_cm, AI_329701_SPAN_US_CM), kappa_us_cm > AI_329701_SPAN_US_CM


def ai_329701_alarms(kappa_us_cm: float) -> tuple[bool, bool]:
    """AI-329701's high alarm and high-high safety alarm.

    Process utility
    ---------------
    What tells the board operator the steam condensate is contaminated: the plant DCS's H1 at 15
    and H2 at 18 uS/cm (read back 2026-10-13). They are evaluated on the condensate's conductivity
    itself, as they always were: both lie inside the transmitter's present 0-30 uS/cm.
    """
    return kappa_us_cm > AI_329701_H1_US_CM, kappa_us_cm > AI_329701_H2_US_CM
