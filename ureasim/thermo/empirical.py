"""Anchored bulk properties — the fast path the 10 Hz inner loop runs on.

What this is for
----------------
A speciating electrolyte solve costs about 15 ms. A simulation tick has 100 ms for the
whole plant. So the quantities that every unit needs every tick — a solution's specific
heat, its density, a viscosity — are correlations, **anchored** on the PFD so the design
point is exact and the model supplies only the slope:

    phi_live = phi_anchor + [ phi_raw(live) - phi_raw(design) ]      additive
    phi_live = phi_anchor * [ phi_raw(live) / phi_raw(design) ]      multiplicative

At the design state the bracket is exactly 0 (or 1). See the As-Built reference, Part 0,
Rule 1.

Process utility
---------------
A urea solution's c_p falls and its density rises as it concentrates from 68 % through the
recirculation train to 99.7 % at the evaporator outlet. A single constant c_p would make
every evaporator duty wrong in the same direction — and the error would be invisible,
because the design point would still close.

Why water comes from IAPWS and not from the PFD's density row
---------------------------------------------------------------
The strict-source rule makes the PFD authoritative, so departing from its tabulated density
needs a reason stronger than "the number looks wrong". Here is the reason, and it is
specific rather than general: **the PFD's density row is right almost everywhere and wrong
for exactly two streams.**

  * The utility sheet's seven steam condensates, 142-212 C, match IAPWS-IF97 to a mean
    0.04 %.
  * The desorption sheet's own pure-water streams match to 0.02 % (742G 88 C, 740 89 C,
    739 143 C). So this is not one sheet being sloppy.
  * Only the "Amm. Water" mixture-model family is off, and only above 150 C: stream 746
    (190 C) tabulates 908.5 against 876.08, and 747 (200 C) tabulates 897.7 against 864.67
    — +3.70 % and +3.82 %.

Those two are not merely improbable, they are **impossible**, and three independent checks
say so:

  1. Compressed liquid explains almost none of it. At their tabulated pressures the density
     gain over the saturation line is +0.009 % and +0.018 % — 0.24 % and 0.47 % of the gap.
  2. Dissolved solids would need NEGATIVE volume. Solving
     ``1/rho = (1-ws)/rho_w + ws/rho_app``, the water alone already occupies more than the
     tabulated total volume, giving apparent solute densities of -308 and -12 507 kg/m3.
     Even if every solute were as dense as SOLID urea (1335), the maxima are 867.6 and
     886.2 — still below the tabulated values.
  3. Composition cannot be the variable at all: 743->746 and 749->747 are the same streams
     *heated*, at identical composition and identical mass flow, yet the excess grows by
     +3.06 and +3.25 points over about 51 K.

The artefact is identified. Solving ``rho(T2)/rho(T1) = exp(-beta (T2-T1))`` across three
independent composition families gives beta = 5.22, 5.57 and 5.74e-4 /K — water's true
expansivity at 60-68 C, i.e. the desorption section's own 56-60 C reference temperature.
Water's actual beta at 190 C is 1.27e-3, more than double. The licensor's mixture model
carried a **constant thermal-expansion coefficient frozen near the section reference**; a
single beta = 5.5e-4 reproduces every high-T entry from its low-T partner to within 0.14 %.
The identical pattern appears in the 1925 MTPD PFD, so it is systematic behaviour, not a
transcription slip.

Crucially, **neither impossible value is used as a constant anywhere in this engine.** The
328 anchors are 933.0 kg/m3 at 139 C and 923.28 at 143 C, which sit +0.64 % and -0.02 %
from real water. So the fix never has to anchor on a bad number: the strict source is
honoured where the PFD is sound, and the derivative comes from physics.

Ported from V1 `backend/core/thermo.py` and `backend/main.py` (property block).
Numerically identical.
"""

from __future__ import annotations

import math

from ureasim.data.design_point import (
    C10_RHO_A,
    C10_RHO_B,
    C10_RHO_C,
    C10_T_DES,
    C10_W_DES,
    R323_CP_SOLN,
)

# ======================================================================================
# Water
# ======================================================================================

def cp_water_kjkgk(T_C: float) -> float:
    """Saturated-liquid water c_p [kJ/(kg.K)].

    Least squares against IAPWS-IF97 at 19 points spanning 0-212 C, which is the full range
    this engine's aqueous streams occupy — 40 C absorber liquor to 200 C hydrolyser. Worst
    residual 0.0090 kJ/(kg.K), 0.21 %.

    **Cubic, not quadratic.** c_p(T) has a minimum near 35 C and then curves upward
    increasingly steeply — 4.18 at 40 C but 4.56 at 212 C — and a quadratic fitted over
    20-200 C could not hold 0.02 kJ/(kg.K) at both ends of the wider range: it missed IF97
    by 0.021 at 212 C.
    """
    return (4.21143048 - 0.0010464288 * T_C
            + 0.000008708461 * T_C * T_C + 0.00000001809921 * T_C ** 3)


#: Critical constants of ordinary water (IAPWS).
WATER_TC_K = 647.096        # K
WATER_RHOC = 322.0          # kg/m3

#: Wagner & Pruss, J. Phys. Chem. Ref. Data 22 (1993) 783, Eq. 2.6; reproduced as the
#: auxiliary saturated-liquid equation in IAPWS R7-97 §8.1. Six PUBLISHED coefficients —
#: nothing is fitted here, so the no-fabrication rule is satisfied without any regression.
#: Verified against an independent IF97 implementation: worst deviation 0.0047 % over
#: 0-220 C, 0.043 % out to 250 C.
_WP_B = (1.99274064, 1.09965342, -0.510839303, -1.75493479, -45.5170352, -6.74694450e5)
_WP_E = (1.0 / 3.0, 2.0 / 3.0, 5.0 / 3.0, 16.0 / 3.0, 43.0 / 3.0, 110.0 / 3.0)


def water_rho_sat(T_C: float) -> float:
    """Saturated-liquid density of ordinary water [kg/m3] — Wagner & Pruss (1993) Eq. 2.6.

        rho = rho_c [ 1 + sum_i b_i tau^(e_i) ],   tau = 1 - T/T_c
    """
    tau = 1.0 - (T_C + 273.15) / WATER_TC_K
    if tau <= 0.0:
        return WATER_RHOC
    return WATER_RHOC * (1.0 + sum(b * tau ** e for b, e in zip(_WP_B, _WP_E)))


# ======================================================================================
# Urea solutions
# ======================================================================================

#: c_p of molten urea [kJ/(kg.K)] — **back-solved**, not hardcoded, so it can never drift
#: out of step with `cp_water_kjkgk` or with the anchor it came from. The mixing rule is
#: required to reproduce `R323_CP_SOLN` at the design composition, and the urea term solved
#: for. The result is about 2.072, and the published value for molten urea is 2.0-2.1 — an
#: independent corroboration rather than an input.
CP_UREA_MELT = ((R323_CP_SOLN - (1.0 - C10_W_DES) * cp_water_kjkgk(C10_T_DES))
                / C10_W_DES)


def _urea_cp_raw(w_urea: float, T_C: float) -> float:
    """Ideal mixing rule for solution c_p, before anchoring."""
    w = min(max(w_urea, 0.0), 1.0)
    return w * CP_UREA_MELT + (1.0 - w) * cp_water_kjkgk(T_C)


def _urea_rho_raw(w_urea: float, T_C: float) -> float:
    """PFD density regression, before anchoring: ``A + B w + C (T - 100)``."""
    w = min(max(w_urea, 0.0), 1.0)
    return C10_RHO_A + C10_RHO_B * w + C10_RHO_C * (T_C - 100.0)


#: Raw values at the design anchor, evaluated once. These are what make the departure form
#: return the anchor bit-exactly at design: the same function on the same inputs gives a
#: literal 0.0 difference.
_CP_RAW_DES = _urea_cp_raw(C10_W_DES, C10_T_DES)
_RHO_RAW_DES = _urea_rho_raw(C10_W_DES, C10_T_DES)


def urea_soln_cp(w_urea: float, T_C: float, anchor: float = R323_CP_SOLN) -> float:
    """Specific heat of a urea solution [kJ/(kg.K)], as a departure from the design anchor.

    Returns ``anchor`` bit-exactly at the design composition and temperature.
    """
    return anchor + (_urea_cp_raw(w_urea, T_C) - _CP_RAW_DES)


def urea_soln_rho(w_urea: float, T_C: float, anchor: float) -> float:
    """Density of a urea solution [kg/m3], as a departure from the caller's own anchor.

    Each call site keeps its PFD-published design density and gains the correct slopes
    around it.
    """
    return anchor + (_urea_rho_raw(w_urea, T_C) - _RHO_RAW_DES)


# ======================================================================================
# Aqueous streams
# ======================================================================================

def aqueous_rho(anchor: float, T_des_C: float, T_C: float) -> float:
    """Density of an aqueous stream [kg/m3], as a MULTIPLICATIVE departure from its anchor.

    The absolute value stays the PFD's; only the temperature slope comes from IAPWS.

    Multiplicative rather than additive because these anchors sit 0-1.3 % above pure water,
    and a solution's expansivity tracks water's **fractionally**, not absolutely. Across the
    full 44 -> 200 C span the two forms differ by at most 1.5 kg/m3, so this is a
    refinement, not a reversal.

    .. warning::
       The parentheses around the ratio are **load-bearing**, not cosmetic.
       ``anchor * (r/r)`` returns ``anchor`` bit-exactly for every operand;
       ``anchor * r / r``, evaluated left to right, does not — measured at about 10 % of
       random operand pairs. The design anchor depends on it.
    """
    return anchor * (water_rho_sat(T_C) / water_rho_sat(T_des_C))


def aqueous_cp(anchor: float, T_des_C: float, T_C: float) -> float:
    """c_p of an aqueous stream [kJ/(kg.K)], as an additive departure from its own anchor.

    The strict-source rule does not bind here at all: the PFD has **no c_p row anywhere** —
    its rows are flows, molar weight, density, temperature and pressure — so steam tables
    are the only admissible source rather than merely the better one.

    Additive rather than multiplicative because these anchors are LUMPED values well below
    pure water (4.0 and 3.0 against water's 4.18-4.49), so they carry solute content whose
    own c_p should not be scaled by water's temperature slope.
    """
    return anchor + (cp_water_kjkgk(T_C) - cp_water_kjkgk(T_des_C))


# ======================================================================================
# Transport properties
# ======================================================================================

def viscosity_liq_pas(T_C: float) -> float:
    """Urea / carbamate liquid viscosity [Pa.s], Andrade form.

    Process utility: feeds the line pressure drops and the packed-bed wetted-area
    correlation. Typical range 1.0-3.0 cP (0.001-0.003 Pa.s) in the synthesis loop.

        mu = A exp(B/T),   A = 1.2e-5 Pa.s,  B = 2200 K

    Floored at 1e-4 Pa.s so a hot transient cannot drive a Reynolds number to infinity.
    """
    T_k = T_C + 273.15
    mu = 1.2e-5 * math.exp(2200.0 / T_k)
    return max(mu, 1e-4)


def viscosity_gas_pas(T_C: float) -> float:
    """Process-gas viscosity [Pa.s].

    Typical range about 0.015 cP (1.5e-5 Pa.s), rising with temperature as a dilute gas
    does. Feeds the gas-film mass-transfer coefficient in the packed absorber.

        mu = 1.5e-5 (T / 450)^0.8
    """
    T_k = T_C + 273.15
    return 1.5e-5 * (T_k / 450.0) ** 0.8


def nh3_psat_bara(T_C: float) -> float:
    """Saturated vapour pressure of pure ammonia [bar a], NIST Antoine form.

    Process utility
    ---------------
    Sets the sub-cooling margin at the 321P002 suction. A reciprocating pump handling a
    liquid at its bubble point does not cavitate gently — the plunger flashes the liquid on
    the suction stroke and the machine knocks. So PDYI-321203/204 publish
    ``P_feed(abs) - P_sat(T)`` and the 21.2 main trip fires below 0.1 bar of margin. This
    correlation is the ``P_sat(T)`` in that difference and therefore sits directly under a
    trip: it decides when the pumps stop.

    It is also why the feed drum runs at 12.3 bar g on 25 C ammonia — about 10 bar above the
    saturation pressure — rather than at the storage condition.

    Equation
    --------
        log10(P [bar]) = A - B / (T[K] + C),   A = 4.86886, B = 1113.928, C = -10.409

    Valid roughly 239-372 K, which brackets every state the feed drum can reach.

    Source: V1 `backend/main.py` psat_nh3_bara (NIST Antoine coefficients for ammonia).
    """
    A, B, C = 4.86886, 1113.928, -10.409
    T_k = T_C + 273.15
    return 10.0 ** (A - B / (T_k + C))


__all__ = [
    "cp_water_kjkgk", "water_rho_sat", "WATER_TC_K", "WATER_RHOC",
    "CP_UREA_MELT", "urea_soln_cp", "urea_soln_rho",
    "aqueous_rho", "aqueous_cp",
    "viscosity_liq_pas", "viscosity_gas_pas",
    "nh3_psat_bara",
]
