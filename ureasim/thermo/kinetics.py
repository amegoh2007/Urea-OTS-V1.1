"""Liquid-phase reaction rate constants for the NH3-CO2-H2O-urea system.

What this covers
----------------
Rate constants only — the temperature dependence of a reaction, with no knowledge of which
vessel it happens in. A rate constant is a property of the chemistry, the same way a Henry
constant is, so it belongs in the property layer rather than in a unit module. Two different
vessels on this plant run the same urea hydrolysis at different temperatures and holdups; they
must not carry two copies of its Arrhenius line.

Source
------
Ported from V1 ``backend/main.py``, `urea_hydrolysis_k_m3_kmol_h` and the two Inoue & Otsuka
constants above it.

Scope discipline
----------------
A function belongs here only if it can be written without naming a tag. Anything that needs a
residence time, a holdup volume or a feed vector is a *unit* calculation and belongs to the
unit that owns those numbers — for example the 328C003 conversion integral, or the stripper's
rate group, both of which call the constant below and supply their own vessel.
"""

from __future__ import annotations

import math

from ureasim.thermo.parameters import R_FITTED

# ======================================================================================
# Urea hydrolysis:  NH2CONH2 + H2O -> 2 NH3 + CO2
# ======================================================================================
#
# The reverse of urea formation, and the reaction the whole desorption/hydrolysis section
# exists to drive to completion. It also runs, unwanted, wherever urea solution is held hot:
# in the stripper sump, in the recirculation heaters and in the evaporators. It is what puts
# ammonia into a process condensate that is supposed to be clean.
#
# Inoue & Otsuka (1973), Eq. (6):
#
#     ln k_H = 21.8 - 11100 / T          T in kelvin
#
# The paper reports k in L/(mol h), which is numerically identical to m3/(kmol h), so the
# coefficients are used as published with no unit conversion. Both are quoted here as the
# literature values they are, not as fitted numbers.

#: Pre-exponential term of the Inoue-Otsuka line, as ln A [-].
#: Source: Inoue & Otsuka (1973) Eq. (6), via V1 `main.py` R328_HYD_K_LN_A.
HYDROLYSIS_LN_A = 21.8

#: Activation term of the Inoue-Otsuka line [K], i.e. Ea/R.
#: Source: Inoue & Otsuka (1973) Eq. (6), via V1 `main.py` R328_HYD_K_B_K.
HYDROLYSIS_B_K = 11_100.0


def urea_hydrolysis_k_m3_kmol_h(temperature_c: float) -> float:
    """Second-order urea-hydrolysis rate constant [m3/(kmol h)] at ``temperature_c`` [deg C].

    Process utility
    ---------------
    Fixes how fast urea is destroyed in any hot liquid holdup. Where the section is *meant*
    to hydrolyse — 328C003 — this constant sizes the vessel against the 1 ppm product
    guarantee. Where it is not meant to — the 322E001 sump, the 323 heaters, the evaporators
    — the same constant is what turns a long residence time into a yield loss and an ammonia
    excursion in the process condensate.

    The strong temperature dependence is the operating lesson: 11 100 K in the exponent means
    the rate roughly doubles for every 10 deg C, so holding a urea melt 20 deg C hot to keep
    it fluid is not a free decision.

    Equation
    --------
        k_H(T) = exp( ln_A - B / (T + 273.15) )        [Inoue & Otsuka (1973), Eq. (6)]
    """
    return math.exp(HYDROLYSIS_LN_A - HYDROLYSIS_B_K / (temperature_c + 273.15))


# ======================================================================================
# Urea synthesis: the two steps, their enthalpies, and their rate laws
# ======================================================================================
#
# The forward direction of the reaction above, run deliberately at 140 bar a. It is two
# steps, and which of them controls depends on where you stand (Stamicarbon / Inoue):
#
#     (1)  2 NH3 + CO2  <-> NH2COONH4            fast, equilibrium-limited, exothermic
#     (2)  NH2COONH4    <-> NH2CONH2 + H2O       rate-controlling, endothermic
#
# Step 1 is taken to completion in the liquid, which is the standard assumption at 140 bar a
# and N/C around 3: essentially all the CO2 present in the melt is carbamate. So a model that
# marches CO2 up a column is marching the carbamate inventory, and step 2 is what consumes it.
#
# Why the enthalpies live here rather than in a unit module
# ---------------------------------------------------------
# Three units on this plant run these same two steps and only the direction differs. 322R001
# drives them forward; 322E001's sump and 328C003 run the reverse (hydrolysis) and carry the
# same numbers with the opposite sign. V1 wrote them out three times -- `reactor.DH_CARB_JMOL`,
# `main.STRIP_DH_HYD_JMOL` and `main.R328_HYD_DH_KJMOL` -- in three units of measure. They are
# one set of chemistry constants and they have one home.

#: Carbamate-formation enthalpy [J/mol], 2 NH3 + CO2 -> NH2COONH4. Strongly exothermic, and
#: the reason 322E002 raises the plant's LP steam and 322R001 needs no fired heat at all.
#: Source: Helwan Fundamentals, via V1 `reactor.py` DH_CARB_JMOL.
CARBAMATE_DH_JMOL = -117_000.0

#: Dehydration enthalpy [J/mol], NH2COONH4 -> NH2CONH2 + H2O. Mildly ENDOTHERMIC, which is
#: the sign that matters: a reactor making more urea releases LESS net heat, not more.
#: Source: Helwan Fundamentals, via V1 `reactor.py` DH_DEHYD_JMOL (and, with the opposite
#: sign for the reverse direction, `main.py` STRIP_DH_HYD_JMOL).
DEHYDRATION_DH_JMOL = 15_500.0

#: Overall enthalpy [J/mol], 2 NH3 + CO2 -> NH2CONH2 + H2O. Exothermic.
#:
#: Which equilibrium constrains the reactor was got wrong once in V1 and is worth stating.
#: The rate-controlling step is dehydration, which is endothermic, so ITS equilibrium
#: constant RISES with temperature; constraining a conversion march with that alone teaches
#: that a hotter reactor converts more, which is the opposite of the truth and dangerous in a
#: training simulator. The conversion is limited by the OVERALL reaction, which is exothermic,
#: so its attainable conversion FALLS with temperature. That, against a rate constant that
#: rises with temperature, is what produces a conversion optimum -- no fitted parabola needed.
#: Source: the sum above; the same figure V1 carries as `main.py` R328_HYD_DH_KJMOL (101.5
#: kJ/mol) for the reverse direction.
UREA_OVERALL_DH_JMOL = CARBAMATE_DH_JMOL + DEHYDRATION_DH_JMOL

#: Activation energy of the rate-controlling dehydration step [J/mol], DERIVED rather than
#: asserted.
#:
#: Inoue & Otsuka give the REVERSE step (urea + H2O -> carbamate) directly: the `B` term of
#: the hydrolysis line above is Ea/R, so Ea_reverse = 11 100 . R = 92.3 kJ/mol. For one
#: elementary step run both ways the two activation energies differ by the step enthalpy, so
#: the forward barrier is the reverse one plus the endothermic dehydration heat:
#:
#:     Ea_forward = 11 100 . R + 15 500 = 107 785.4 J/mol
#:
#: Evaluated with the ROUNDED gas constant, because that is the constant the back-solved
#: pre-exponential was fitted against; see `R_FITTED`.
#: Source: derived here from `HYDROLYSIS_B_K` and `DEHYDRATION_DH_JMOL`, as V1 `reactor.py`
#: EA_DEHYD_JMOL derives it.
DEHYDRATION_EA_JMOL = HYDROLYSIS_B_K * R_FITTED + DEHYDRATION_DH_JMOL

#: Biuret-formation activation energy [J/mol], 2 Urea -> Biuret + NH3.
#:
#: Biuret is the plant's principal product-quality specification and it forms wherever urea
#: is held hot: in the reactor column, in the stripper sump, and in the evaporators. One
#: activation energy serves all of them. Source: V1 `main.py` STRIP_BIU_EA, which V1
#: `reactor.py` BIU_EA_JMOL then repeats with the comment "the activation energy the stripper
#: already uses".
BIURET_FORMATION_EA_JMOL = 85_000.0


def dehydration_k_per_h(temperature_c: float, pre_exponential_per_h: float) -> float:
    """Rate constant of the rate-controlling dehydration step [1/h].

    Process utility
    ---------------
    This is the number that decides whether a urea reactor is a reactor or a pipe. At
    107.8 kJ/mol the rate roughly triples for every 10 deg C, so the residence time a column
    needs is a steep function of how hot the carbamate exotherm has managed to make it -- and
    a reactor that loses its feed temperature does not convert slowly, it stops converting.

    Why the pre-exponential is an ARGUMENT
    --------------------------------------
    No vendor kinetics exist for this reactor, so the pre-exponential is back-solved from one
    plant design point, which makes it a property of that vessel rather than of the
    chemistry. Passing it in keeps this module free of plant knowledge, and it keeps the
    caller honest: a vessel that has not calibrated has nothing to pass.

    Equation
    --------
        k2(T) = A2 . exp( -Ea_dehyd / (R . T) )        [Arrhenius, T in kelvin]
    """
    return pre_exponential_per_h * math.exp(
        -DEHYDRATION_EA_JMOL / (R_FITTED * (temperature_c + 273.15)))


def urea_keq_overall(temperature_c: float, keq_ref: float, t_ref_k: float) -> float:
    """Equilibrium constant [m3/kmol] of 2 NH3 + CO2 <-> urea + H2O at ``temperature_c``.

    Process utility
    ---------------
    Sets the conversion the reactor could reach if it had infinite time, which is the ceiling
    every operating decision is made against. Because the overall reaction is exothermic this
    ceiling FALLS as the column heats, so pushing reactor temperature buys rate at the cost of
    attainable conversion. The optimum an operator is trained to hold is where those two
    cross, and it comes out of this constant against `dehydration_k_per_h` rather than being
    asserted.

    Equation
    --------
        Kov(T) = Kov_ref . exp( -dH_overall / R . (1/T - 1/T_ref) )     [van t Hoff]

    with dH_overall < 0, so Kov decreases as T rises.

    Both ``keq_ref`` and ``t_ref_k`` are the calibrating vessel's, for the same reason the
    pre-exponential above is an argument.
    """
    t_k = temperature_c + 273.15
    return keq_ref * math.exp(
        -UREA_OVERALL_DH_JMOL / R_FITTED * (1.0 / t_k - 1.0 / t_ref_k))


def biuret_k_m3_kmol_h(temperature_c: float, pre_exponential: float) -> float:
    """Second-order biuret-formation rate constant [m3/(kmol h)], 2 Urea -> Biuret + NH3.

    Process utility
    ---------------
    Biuret is what a hot, long-held urea melt turns into, and it is capped by contract at a
    fraction of a per cent. Nothing an operator does raises biuret quickly; everything that
    raises it -- a hot reactor, a flooded sump, an evaporator held above temperature -- raises
    it steadily and cannot be undone downstream. The second order in urea concentration is
    why the evaporators, not the reactor, are where a quality excursion usually begins.

    Equation
    --------
        k_b(T) = A_b . exp( -Ea_biu / (R . T) )        [Arrhenius, T in kelvin]
    """
    return pre_exponential * math.exp(
        -BIURET_FORMATION_EA_JMOL / (R_FITTED * (temperature_c + 273.15)))


__all__ = [
    "HYDROLYSIS_LN_A",
    "HYDROLYSIS_B_K",
    "urea_hydrolysis_k_m3_kmol_h",
    "CARBAMATE_DH_JMOL",
    "DEHYDRATION_DH_JMOL",
    "UREA_OVERALL_DH_JMOL",
    "DEHYDRATION_EA_JMOL",
    "BIURET_FORMATION_EA_JMOL",
    "dehydration_k_per_h",
    "urea_keq_overall",
    "biuret_k_m3_kmol_h",
]
