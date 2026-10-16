"""Unit conventions and the physical constants that convert between them.

The conventions this engine works in, stated once
-------------------------------------------------
======================  ==========================================================
Quantity                Unit
======================  ==========================================================
Mass flow               kg/h  (t/h only where a plant instrument reads t/h)
Molar flow              kmol/h
Pressure                bar a internally; bar g only at a gauge-reading instrument
Temperature             deg C internally; K inside a thermodynamic relation
Energy flow             kW; kJ/h only where a V1 relation was written that way
Time                    s  (the integration step `dt`)
Volume                  m3
Density                 kg/m3
Specific heat           kJ/(kg.K)
======================  ==========================================================

Process utility
---------------
Mixing bar a with bar g is how a pressure model gets a silent 1 bar offset, and at a
vacuum node — where 0.33 bar a is a normal operating point — that offset is the difference
between the evaporator working and the evaporator being underwater. Every conversion in
this engine goes through one of the functions below, so the offset is in one place.

**One atmosphere and one gravity (decided 2026-10-07, handoffs B-6 and B-7).**
V1 carries two of each: `P_ATM_BAR = 1.013` in `backend/main.py` against `P_ATM_BARA = 1.01325`
in `backend/consequence.py` and its browser HMI, and `G = 9.81` in the 321D003 suction head
against standard gravity, 9.80665, in `consequence.py`. The process engineer standardised both
on the exact values, in every process relation and every display: the SV-32201 set pressure is
now ``160.0 barg + 1.01325 = 161.01325 bar a`` (V1's 161.013), SV-32253's is the vendor sheet's
own atmosphere as before (`data.relief_devices`), the 321P002 differential and trip 21.2's
10 / 12 bar g are on 1.01325, the 322C001 vent line discharges at 1.01325, and PT-321201/202 read
the drum head on standard gravity (1.8e-5 bar below V1's at the design level).
"""

from __future__ import annotations

from ureasim.thermo.parameters import R_FITTED

__all__ = [
    "R_GAS_J", "R_GAS_KJ", "R_GAS_J_KMOL", "R_GAS_FITTED_J", "G_ACC",
    "ATM_BARA", "NM3_PER_KMOL", "ABSOLUTE_ZERO_C",
    "PA_PER_BAR", "KJ_PER_KCAL",
    "c_to_k", "k_to_c", "bara_to_barg", "barg_to_bara",
    "kgh_to_th", "th_to_kgh", "kgh_to_kgs",
    "kjh_to_kw", "kw_to_kjh", "kmolh_to_molps",
]

# ======================================================================================
# Physical constants
# ======================================================================================

#: Universal gas constant [J/(mol.K)] — CODATA, exact since the 2019 SI redefinition.
#: Source: V1 `backend/hydraulics.py` R_GAS and `backend/consequence.py` R_GAS_J, which
#: carry the same value; also `thermo.parameters.R`.
R_GAS_J = 8.314462618

#: The same constant in kJ/(kmol.K), which is numerically identical — the factor 1000 in the
#: numerator (J -> kJ) and in the denominator (mol -> kmol) cancel. Named separately because
#: the molar balances in this engine are written in kmol and reading `R_GAS_J` there looks
#: like a units error when it is not.
R_GAS_KJ = R_GAS_J

#: The same constant in J/(kmol.K). Source: V1 `backend/machines.py` R_GAS_J, which is written
#: as this literal because the compressor head group is per KILOMOLE. It happens to equal
#: `R_GAS_J * 1000.0` exactly in IEEE 754, but it is carried as the literal so the polytropic
#: head does not depend on that coincidence holding.
R_GAS_J_KMOL = 8314.462618

#: The ROUNDED gas constant V1's fitted correlations were calibrated against [J/(mol.K)].
#:
#: Defined in `thermo.parameters` and re-exported here. It belongs at the bottom layer
#: because `thermo.kinetics` derives the 322R001 dehydration activation energy from it, and
#: it is named here because every layer above reads its gas constants from this module. The
#: reason the two values are kept apart is written where it is defined.
#:
#: Call sites: the biuret rate law shared by 322E001 and 322R001, the carbamate-equilibrium
#: and bubble-pressure slopes in 322E002, and the 322R001 rate laws.
R_GAS_FITTED_J = R_FITTED

#: Standard gravity [m/s2], the only gravity in the engine (decided 2026-10-07, handoff B-7: V1's
#: `main.py` G = 9.81 in the 321D003 suction head is replaced). Source: V1 `backend/consequence.py`
#: G_ACC. Used by every static head: a gravity-drained sump, a column's leg, a drum's suction,
#: the NPSH margin.
G_ACC = 9.80665

#: Atmospheric pressure [bar a], the standard atmosphere — every gauge-to-absolute conversion, in
#: a process relation and on a display (decided 2026-10-07, handoff B-6: V1's `main.py` P_ATM_BAR
#: = 1.013 is replaced). Source: V1 `frontend/app.js` and `backend/consequence.py`, 1.01325.
ATM_BARA = 1.01325

#: Normal molar volume [Nm3/kmol] at 0 deg C and 1 atm. Source: V1 `backend/main.py`
#: NM3_PER_KMOL. This is the basis FT-322403 reads on, so the CO2 feed indication is a
#: normal volume and not an actual one.
NM3_PER_KMOL = 22.414

#: Offset between the Celsius and Kelvin scales [K].
ABSOLUTE_ZERO_C = 273.15

#: Pascals per bar. Source: V1 `backend/hydraulics.py` _BAR_TO_PA. The plant is worked in bar
#: throughout; this appears only where a correlation is written in SI base units — the API 520
#: relief mass flux is the one such place — and never as a display conversion.
PA_PER_BAR = 1.0e5

#: Kilojoules per International Table kilocalorie. Uhde's exchanger data sheets print heat
#: capacities in kcal/(kg K); this is the only conversion they need.
KJ_PER_KCAL = 4.1868


# ======================================================================================
# Temperature
# ======================================================================================

def c_to_k(t_c: float) -> float:
    """deg C -> K. Every thermodynamic relation works in K; every instrument reads deg C."""
    return t_c + ABSOLUTE_ZERO_C


def k_to_c(t_k: float) -> float:
    """K -> deg C."""
    return t_k - ABSOLUTE_ZERO_C


# ======================================================================================
# Pressure
# ======================================================================================

def bara_to_barg(p_bara: float) -> float:
    """bar a -> bar g, on the standard atmosphere: a gauge reading, a relief set point, a pump
    differential alike (handoff B-6, decided)."""
    return p_bara - ATM_BARA


def barg_to_bara(p_barg: float) -> float:
    """bar g -> bar a, on the standard atmosphere."""
    return p_barg + ATM_BARA


# ======================================================================================
# Flow
# ======================================================================================

def kgh_to_th(w_kgh: float) -> float:
    """kg/h -> t/h. The CO2 and NH3 feed instruments (FY-322403, FIC-321401) read t/h."""
    return w_kgh / 1000.0


def th_to_kgh(w_th: float) -> float:
    """t/h -> kg/h."""
    return w_th * 1000.0


def kgh_to_kgs(w_kgh: float) -> float:
    """kg/h -> kg/s. Needed wherever a flow multiplies the integration step `dt` [s]."""
    return w_kgh / 3600.0


def kmolh_to_molps(n_kmolh: float) -> float:
    """kmol/h -> mol/s, the form the ideal-gas accumulation term `R.T/V . dn/dt` needs."""
    return n_kmolh * 1000.0 / 3600.0


# ======================================================================================
# Energy
# ======================================================================================

def kjh_to_kw(q_kjh: float) -> float:
    """kJ/h -> kW. V1 writes some duties as kJ/h (`Q_strip_kjh`) and others as kW."""
    return q_kjh / 3600.0


def kw_to_kjh(q_kw: float) -> float:
    """kW -> kJ/h."""
    return q_kw * 3600.0
