"""The saturated-gas vent law — a gas leaving in equilibrium with a cold liquid.

Equipment modelled
------------------
Not a piece of equipment: the relation every gas outlet obeys that leaves over a cold liquid
it has been in contact with — the top of a scrubber or an absorber, the cold end of a surface
condenser. It is used today by 323C005, the atmospheric absorber, whose vent (PFD 341) is the
inert gas of 702 and 708 leaving saturated at the absorber top. The 324 vacuum condensers ride
the same law with a speciated back-pressure over their condensate; that branch arrives with
unit 324.

The physics
-----------
Every PFD vent row off such an outlet sits at water saturation at its own temperature and
pressure: stream 341 carries water at 0.0821 bar partial pressure at 1.0 bar a against
psat(43 C) = 0.0865, a water activity of 0.95. So the gas that leaves is the inert gas plus
whatever condensable vapour it can hold at that temperature and pressure:

    y_c(T, P) = Y_des . (P_des / P) . psat_w(T) / psat_w(T_des)       condensable mole fraction
    n_vent,c  = n_inert . y_c / (1 - y_c)          split among H2O / NH3 / CO2 as the PFD vent row

NH3 and CO2 ride water's saturation line with the design row's fixed split. The vent grows
without bound — until it is the whole inlet — as the pressure falls towards the vapour pressure
at the outlet temperature, and no condensable leaves in excess of what arrives.

Units: kmol/h for the species flows, bar a, deg C.

Source
------
V1 ``backend/vacuum_condenser.py`` — ``CONDENSABLE``, ``INERT``, ``CARRIED``, ``SPECIES``, ``MW``,
``_Y_MAX``, ``moles_from_mole_pct``, ``saturated_gas_spec``, ``vent_moles`` (its saturated-gas
branch, the one a spec without ``bp_des`` takes) and ``vent_mass_kgh``; V1 report D-11.
"""

from __future__ import annotations

from dataclasses import dataclass

from ureasim.thermo import iapws
from ureasim.thermo.enthalpy import MOLAR_MASS

#: The vapours a cold liquid takes back, the gases it does not, and the entrained liquor that is
#: liquid on both sides. The order is V1's and fixes the order every sum is taken in.
CONDENSABLE = ("H2O", "NH3", "CO2")
INERT = ("N2", "O2")
CARRIED = ("Urea",)
SPECIES = CONDENSABLE + INERT + CARRIED

#: Molar masses [kg/kmol], the enthalpy layer's.
MW = {k: MOLAR_MASS[k] for k in SPECIES}

#: The condensable mole fraction is held just short of 1: at 1 the vent would be infinite.
Y_MAX = 1.0 - 1.0e-9

#: Guard on the pressure in the saturation ratio [bar a], V1's literal.
P_FLOOR_BARA = 1.0e-9


@dataclass(frozen=True)
class SaturatedGasSpec:
    """A gas outlet anchored on its PFD vent row: the design pressure [bar a] and temperature
    [deg C], water's vapour pressure there [bar a], the condensable mole fraction of the row, and
    how that fraction splits among H2O, NH3 and CO2."""

    p_des: float
    t_v_des: float
    psat_v_des: float
    y_des: float
    split: dict


def moles_from_mole_pct(total_kmolh: float, pct: dict) -> dict:
    """Species flows [kmol/h] of a PFD vapour row.

    Process utility
    ---------------
    Turns the PFD's vapour rows — mole per cent, in V1's table named for mass per cent (the F-8
    unit convention) — into the species flows a vent is computed on.

    Equation
    --------
        n_k = N . pct_k / sum(pct)      over SPECIES, the row renormalised

    Source: V1 `vacuum_condenser.moles_from_mole_pct`.
    """
    tot = sum(pct.get(k, 0.0) for k in SPECIES)
    return {k: total_kmolh * pct.get(k, 0.0) / tot for k in SPECIES}


def saturated_gas_spec(vent_row: dict, p_des: float, t_des: float) -> SaturatedGasSpec:
    """Anchor a gas outlet on its PFD vent row at its design pressure and temperature.

    Process utility
    ---------------
    Fixes how much condensable vapour the outlet carries at design, and in what proportions, so
    the live vent departs from the PFD only as the outlet's temperature and pressure move.

    Equation
    --------
        Y_des = sum(row_c) / sum(row_c + row_inert),   split_k = row_k / sum(row_c)

    Source: V1 `vacuum_condenser.saturated_gas_spec`.
    """
    y_c = sum(vent_row.get(k, 0.0) for k in CONDENSABLE)
    return SaturatedGasSpec(
        p_des=p_des, t_v_des=t_des, psat_v_des=iapws.psat_bara(t_des),
        y_des=y_c / sum(vent_row.get(k, 0.0) for k in CONDENSABLE + INERT),
        split={k: vent_row.get(k, 0.0) / y_c for k in CONDENSABLE})


def vent_moles(spec: SaturatedGasSpec, p_bara: float, t_v_c: float, n_in: dict) -> dict:
    """The gas leaving [kmol/h]: every inert, plus the condensables it holds saturated at T, P.

    Process utility
    ---------------
    What an absorber top or a condenser's cold end lets go of: a warmer outlet, or a lower
    pressure, carries more NH3 and water out with the inerts; more inert gas carries more of
    both. It never releases more of a condensable than arrives, and it keeps no inert.

    Equation
    --------
        y   = clamp( Y_des (P_des / P) psat_w(T) / psat_w(T_des),  0,  1 - 1e-9 )
        n_c = n_inert . y / (1 - y)
        vent_k = min(n_c . split_k, n_in,k)   k in H2O, NH3, CO2;   vent_inert = n_in,inert

    Source: V1 `vacuum_condenser.vent_moles`, its saturated-gas branch.
    """
    n_i = sum(n_in.get(k, 0.0) for k in INERT)
    y = (spec.y_des * (spec.p_des / max(p_bara, P_FLOOR_BARA))
         * (iapws.psat_bara(t_v_c) / spec.psat_v_des))
    y = min(max(y, 0.0), Y_MAX)
    n_c = n_i * y / (1.0 - y)
    vent = {k: min(n_c * spec.split[k], n_in.get(k, 0.0)) for k in CONDENSABLE}
    for k in INERT:
        vent[k] = n_in.get(k, 0.0)
    vent["Urea"] = 0.0
    return vent


def vent_mass_kgh(vent: dict) -> float:
    """The vent's mass flow [kg/h] from its species flows [kmol/h].

    Source: V1 `vacuum_condenser.vent_mass_kgh`.
    """
    return sum(vent.get(k, 0.0) * MW[k] for k in SPECIES)


__all__ = [
    "CONDENSABLE", "INERT", "CARRIED", "SPECIES", "MW", "Y_MAX", "P_FLOOR_BARA",
    "SaturatedGasSpec", "moles_from_mole_pct", "saturated_gas_spec", "vent_moles",
    "vent_mass_kgh",
]
