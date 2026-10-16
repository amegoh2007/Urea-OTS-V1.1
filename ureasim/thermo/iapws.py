"""IAPWS-IF97 pure-water / steam boundary — the single water reference line.

Equipment modelled
------------------
Not a piece of equipment: this is the *property boundary* every steam-heated shell and
every condensate leg in the plant stands on.

    Unit 329   MP (19.7 bar a) / 9-bar / LP (4.4 bar a) headers, 329D005, 329D009,
               322D001 A/B steam drums, all desuperheaters and let-downs
    322E001    HP stripper reboiler shell   (saturation temperature from P_MP)
    322E002    HP carbamate condenser shell (raises LP steam, saturation from P_LP)
    323E002 / 323E010 / 328E004 / 324E001 / 324E003   steam-heated shells
    every condensate trap and flash drum on those shells

It also supplies the pure-water saturation line that the two activity models
(`properties`, `extended_uniquac`) depart from, so the phase-equilibrium layer and the
steam network cannot disagree about what water does.

Why IAPWS-IF97 and not an Antoine correlation
---------------------------------------------
V1 originally carried an Antoine saturation line (`tsat_steam` / `psat_water_bara`) in two
separate places — once in the engine and once inside the urea/water activity model. Two
water reference lines guarantee the two will disagree somewhere, and Antoine degrades
outside its fit range. IF97 is the international industrial standard, its coefficients are
*published* (nothing here is regressed or fitted), and one module now owns the line.

Regions implemented
-------------------
    Region 4    saturation line, forward Psat(T) and backward Tsat(P)   [R7-97 Sec. 8]
    Region 1    compressed / saturated liquid, T <= 623.15 K            [R7-97 Sec. 5]
    Region 2    vapour / saturated steam                                [R7-97 Sec. 6]

Region 3 (near-critical) and Region 5 (very high temperature) are deliberately absent: the
plant's hottest water is the 25 bar a battery-limit steam at about 224 C, far from both.

Units
-----
Internally SI: T [K], P [MPa], h [kJ/kg], v [m3/kg].
Public wrappers use the simulator convention: T [deg C], P [bar absolute].
Specific gas constant R = 0.461526 kJ/(kg.K)  (IF97 Sec. 2).

Provenance
----------
IAPWS R7-97 (2012 revision), "Industrial Formulation 1997 for the Thermodynamic Properties
of Water and Steam". All coefficients below are the published release values.

Ported from V1 `backend/iapws_if97.py`. Numerically identical — the coefficient tables and
the evaluation order are unchanged, so results are bit-comparable.
"""

from __future__ import annotations

import math

# --------------------------------------------------------------------------------------
# Physical constants and unit bridges
# --------------------------------------------------------------------------------------

#: IF97 specific gas constant for ordinary water substance [kJ/(kg.K)] (R7-97 Sec. 2).
R_KJ_KGK = 0.461526

_MPA_PER_BAR = 0.1      # 1 bar = 0.1 MPa
_KPA_PER_MPA = 1000.0

#: Triple-point temperature [K] — lower bound of the saturation line.
T_MIN_K = 273.15
#: Critical temperature [K] — upper bound of the saturation line.
T_CRIT_K = 647.096
#: Critical pressure [MPa].
P_CRIT_MPA = 22.064
#: Region 1 validity ceiling [K]. Above this the liquid equations are not defined.
REGION1_T_MAX_K = 623.15


class OutOfRange(ValueError):
    """Raised when a saturation request lies outside the IF97 domain.

    Process utility
    ---------------
    This is deliberate: a steam property call that silently clamps at a table edge returns
    a frozen constant from behind a call that looks like a rigorous solve. Refusing is the
    only way that failure stays visible (see the As-Built reference, Part 0, Rule 2).
    """


# ======================================================================================
# Region 4 — the saturation line
# ======================================================================================
# Ten published coefficients shared by the forward and backward saturation equations.
# R7-97 Sec. 8, Table 34.
_N4 = (
    0.11670521452767e4,
    -0.72421316703206e6,
    -0.17073846940092e2,
    0.12020824702470e5,
    -0.32325550322333e7,
    0.14915108613530e2,
    -0.48232657361591e4,
    0.40511340542057e6,
    -0.23855557567849,
    0.65017534844798e3,
)


def psat_mpa(temperature_k: float) -> float:
    """Saturation pressure [MPa] from temperature [K] — IF97 Eq. 30.

    Process utility
    ---------------
    Fixes the pressure a steam drum sits at once its temperature is known, and supplies the
    pure-water partial-pressure term in every liquor bubble point (`thermo.vle`). It is also
    what decides whether a condensate leg flashes when it is let down.

    Equation
    --------
        theta = T + n9 / (T - n10)
        a = theta^2 + n1 theta + n2
        b = n3 theta^2 + n4 theta + n5
        c = n6 theta^2 + n7 theta + n8
        Psat = [ 2c / (-b + sqrt(b^2 - 4ac)) ]^4
    """
    if not math.isfinite(temperature_k) or not (T_MIN_K <= temperature_k <= T_CRIT_K):
        raise OutOfRange(
            f"saturation temperature must be within {T_MIN_K}-{T_CRIT_K} K"
        )
    n = _N4
    theta = temperature_k + n[8] / (temperature_k - n[9])
    a = theta * theta + n[0] * theta + n[1]
    b = n[2] * theta * theta + n[3] * theta + n[4]
    c = n[5] * theta * theta + n[6] * theta + n[7]
    return (2.0 * c / (-b + math.sqrt(b * b - 4.0 * a * c))) ** 4


def tsat_k(pressure_mpa: float) -> float:
    """Saturation temperature [K] from pressure [MPa] — IF97 Eq. 31.

    Process utility
    ---------------
    This is the single most load-bearing steam call in the simulator. The plant heat and
    mass balance couples to the steam network through exactly two numbers:

        Tsat(P_MP)  -> HP stripper 322E001 reboiler shell temperature
        Tsat(P_LP)  -> HP carbamate condenser 322E002 shell temperature

    Everything the synthesis loop does downstream of those two temperatures follows from
    them, so a header-pressure excursion reaches the reactor through this function.

    Equation
    --------
        beta = P^0.25
        e = beta^2 + n3 beta + n6
        f = n1 beta^2 + n4 beta + n7
        g = n2 beta^2 + n5 beta + n8
        d = 2g / (-f - sqrt(f^2 - 4eg))
        Tsat = [ n10 + d - sqrt((n10 + d)^2 - 4(n9 + n10 d)) ] / 2
    """
    if not math.isfinite(pressure_mpa) or not (0.0 < pressure_mpa <= P_CRIT_MPA):
        raise OutOfRange(
            f"saturation pressure must be within (0, {P_CRIT_MPA}] MPa"
        )
    n = _N4
    beta = pressure_mpa ** 0.25
    e = beta * beta + n[2] * beta + n[5]
    f = n[0] * beta * beta + n[3] * beta + n[6]
    g = n[1] * beta * beta + n[4] * beta + n[7]
    d = 2.0 * g / (-f - math.sqrt(f * f - 4.0 * e * g))
    return (n[9] + d - math.sqrt((n[9] + d) ** 2 - 4.0 * (n[8] + n[9] * d))) / 2.0


# ======================================================================================
# Region 1 — compressed and saturated liquid
# ======================================================================================
# Dimensionless Gibbs free energy gamma(pi, tau) as 34 terms n_ij (7.1 - pi)^i (tau - 1.222)^j
# with pi = P / 16.53 MPa and tau = 1386 K / T.   R7-97 Sec. 5, Table 2.
_R1 = (
    (0, -2, 0.14632971213167),
    (0, -1, -0.84548187169114),
    (0, 0, -0.37563603672040e1),
    (0, 1, 0.33855169168385e1),
    (0, 2, -0.95791963387872),
    (0, 3, 0.15772038513228),
    (0, 4, -0.16616417199501e-1),
    (0, 5, 0.81214629983568e-3),
    (1, -9, 0.28319080123804e-3),
    (1, -7, -0.60706301565874e-3),
    (1, -1, -0.18990068218419e-1),
    (1, 0, -0.32529748770505e-1),
    (1, 1, -0.21841717175414e-1),
    (1, 3, -0.52838357969930e-4),
    (2, -3, -0.47184321073267e-3),
    (2, 0, -0.30001780793026e-3),
    (2, 1, 0.47661393906987e-4),
    (2, 3, -0.44141845330846e-5),
    (2, 17, -0.72694996297594e-15),
    (3, -4, -0.31679644845054e-4),
    (3, 0, -0.28270797985312e-5),
    (3, 6, -0.85205128120103e-9),
    (4, -5, -0.22425281908000e-5),
    (4, -2, -0.65171222895601e-6),
    (4, 10, -0.14341729937924e-12),
    (5, -8, -0.40516996860117e-6),
    (8, -11, -0.12734301741641e-8),
    (8, -6, -0.17424871230634e-9),
    (21, -29, -0.68762131295531e-18),
    (23, -31, 0.14478307828521e-19),
    (29, -38, 0.26335781662795e-22),
    (30, -39, -0.11947622640071e-22),
    (31, -40, 0.18228094581404e-23),
    (32, -41, -0.93537087292458e-25),
)


def _region1(temperature_k: float, pressure_mpa: float) -> tuple[float, float]:
    """Liquid-water enthalpy and specific volume — ``(h [kJ/kg], v [m3/kg])``.

    Process utility
    ---------------
    Supplies condensate enthalpy (so a trap's flash fraction is real) and saturated-liquid
    density (so a drum's level-to-mass conversion is real rather than a fixed 1000 kg/m3).

    Equation
    --------
        v = R T pi   gamma_pi  / P
        h = R T tau  gamma_tau
    with the derivatives of the dimensionless Gibbs energy taken term by term over `_R1`.
    """
    pi = pressure_mpa / 16.53
    tau = 1386.0 / temperature_k
    a = 7.1 - pi
    b = tau - 1.222
    gamma_pi = 0.0     # d(gamma)/d(pi)   — note the sign from d(7.1 - pi)/d(pi) = -1
    gamma_tau = 0.0    # d(gamma)/d(tau)
    for i, j, nij in _R1:
        gamma_pi += -nij * i * a ** (i - 1) * b ** j
        gamma_tau += nij * a ** i * j * b ** (j - 1)
    p_kpa = pressure_mpa * _KPA_PER_MPA
    v = R_KJ_KGK * temperature_k * pi * gamma_pi / p_kpa
    h = R_KJ_KGK * temperature_k * tau * gamma_tau
    return h, v


# ======================================================================================
# Region 2 — vapour and saturated steam
# ======================================================================================
# gamma = gamma_ideal(pi, tau) + gamma_residual(pi, tau), pi = P / 1 MPa, tau = 540 K / T.
# R7-97 Sec. 6, Tables 10 (ideal, 9 terms) and 11 (residual, 43 terms).
_R2_IDEAL = (
    (0, -0.96927686500217e1),
    (1, 0.10086655968018e2),
    (-5, -0.56087911283020e-2),
    (-4, 0.71452738081455e-1),
    (-3, -0.40710498223928),
    (-2, 0.14240819171444e1),
    (-1, -0.43839511319450e1),
    (2, -0.28408632460772),
    (3, 0.21268463753307e-1),
)

_R2_RES = (
    (1, 0, -0.17731742473213e-2),
    (1, 1, -0.17834862292358e-1),
    (1, 2, -0.45996013696365e-1),
    (1, 3, -0.57581259083432e-1),
    (1, 6, -0.50325278727930e-1),
    (2, 1, -0.33032641670203e-4),
    (2, 2, -0.18948987516315e-3),
    (2, 4, -0.39392777243355e-2),
    (2, 7, -0.43797295650573e-1),
    (2, 36, -0.26674547914087e-4),
    (3, 0, 0.20481737692309e-7),
    (3, 1, 0.43870667284435e-6),
    (3, 3, -0.32277677238570e-4),
    (3, 6, -0.15033924542148e-2),
    (3, 35, -0.40668253562649e-1),
    (4, 1, -0.78847309559367e-9),
    (4, 2, 0.12790717852285e-7),
    (4, 3, 0.48225372718507e-6),
    (5, 7, 0.22922076337661e-5),
    (6, 3, -0.16714766451061e-10),
    (6, 16, -0.21171472321355e-2),
    (6, 35, -0.23895741934104e2),
    (7, 0, -0.59059564324270e-17),
    (7, 11, -0.12621808899101e-5),
    (7, 25, -0.38946842435739e-1),
    (8, 8, 0.11256211360459e-10),
    (8, 36, -0.82311340897998e1),
    (9, 13, 0.19809712802088e-7),
    (10, 4, 0.10406965210174e-18),
    (10, 10, -0.10234747095929e-12),
    (10, 14, -0.10018179379511e-8),
    (16, 29, -0.80882908646985e-10),
    (16, 50, 0.10693031879409),
    (18, 57, -0.33662250574171),
    (20, 20, 0.89185845355421e-24),
    (20, 35, 0.30629316876232e-12),
    (20, 48, -0.42002467698208e-5),
    (21, 21, -0.59056029685639e-25),
    (22, 53, 0.37826947613457e-5),
    (23, 39, -0.12768608934681e-14),
    (24, 26, 0.73087610595061e-28),
    (24, 40, 0.55414715350778e-16),
    (24, 58, -0.94369707241210e-6),
)


def _region2(temperature_k: float, pressure_mpa: float) -> tuple[float, float]:
    """Water-vapour enthalpy and specific volume — ``(h [kJ/kg], v [m3/kg])``.

    Process utility
    ---------------
    Gives each steam header its live vapour enthalpy and specific volume. The specific
    volume is what turns a drum's steam space into a real capacitance
    (dP/dt = RT/(V_v M) * net mass), replacing the single copy-pasted coefficient that nine
    vessels of different size used to share.

    Equation
    --------
        v = R T pi   (gamma_o_pi  + gamma_r_pi)  / P
        h = R T tau  (gamma_o_tau + gamma_r_tau)
    """
    pi = pressure_mpa / 1.0
    tau = 540.0 / temperature_k

    # Ideal-gas part: gamma_o = ln(pi) + sum n_j tau^j, so d/d(pi) = 1/pi.
    gamma_o_pi = 1.0 / pi
    gamma_o_tau = 0.0
    for j, n in _R2_IDEAL:
        gamma_o_tau += n * j * tau ** (j - 1)

    # Residual part: sum n_ij pi^i (tau - 0.5)^j
    gamma_r_pi = 0.0
    gamma_r_tau = 0.0
    b = tau - 0.5
    for i, j, n in _R2_RES:
        gamma_r_pi += n * i * pi ** (i - 1) * b ** j
        gamma_r_tau += n * pi ** i * j * b ** (j - 1)

    p_kpa = pressure_mpa * _KPA_PER_MPA
    v = R_KJ_KGK * temperature_k * pi * (gamma_o_pi + gamma_r_pi) / p_kpa
    h = R_KJ_KGK * temperature_k * tau * (gamma_o_tau + gamma_r_tau)
    return h, v


# ======================================================================================
# Convenience wrappers in simulator units (deg C, bar absolute, kJ/kg)
# ======================================================================================

def psat_bara(temperature_c: float) -> float:
    """Saturation pressure [bar a] from temperature [deg C]."""
    return psat_mpa(temperature_c + 273.15) / _MPA_PER_BAR


def tsat_c(pressure_bara: float) -> float:
    """Saturation temperature [deg C] from pressure [bar a].

    The pressure is floored at 1e-6 bar a so a vacuum node that momentarily integrates to
    zero or below during a transient does not raise; the physical floor is enforced by the
    vessel model, not by the property call.
    """
    return tsat_k(max(pressure_bara, 1.0e-6) * _MPA_PER_BAR) - 273.15


def _sat_liquid_temperature_k(temperature_c_plus_273: float) -> float:
    """Guard the Region 1 ceiling.

    Region 1 is defined to 623.15 K. The plant's steam/condensate line never approaches
    that ceiling (hottest is ~224 C at the 25 bar a battery limit), so a call above it means
    a caller has gone wrong — fail loudly rather than extrapolate.
    """
    if temperature_c_plus_273 > REGION1_T_MAX_K:
        raise OutOfRange("saturated-liquid enthalpy above Region 1 ceiling (623.15 K)")
    return temperature_c_plus_273


def h_liquid_sat_kjkg(temperature_c: float) -> float:
    """Saturated-liquid specific enthalpy [kJ/kg] at temperature [deg C].

    Process utility: the condensate enthalpy leaving a steam-heated shell. Together with
    ``h_vapour_sat_kjkg`` it fixes the latent heat a shell actually delivers.
    """
    t_k = _sat_liquid_temperature_k(temperature_c + 273.15)
    p_mpa = psat_mpa(t_k)
    return _region1(t_k, p_mpa)[0]


def h_vapour_sat_kjkg(temperature_c: float) -> float:
    """Saturated-vapour specific enthalpy [kJ/kg] at temperature [deg C]."""
    t_k = temperature_c + 273.15
    p_mpa = psat_mpa(t_k)
    return _region2(t_k, p_mpa)[0]


def hvap_kjkg(temperature_c: float) -> float:
    """Latent heat of vaporisation [kJ/kg] at temperature [deg C].

    Process utility
    ---------------
    Converts a shell's heat duty into a steam mass draw, and a steam mass draw into a
    header pressure change. Because it falls with temperature, a header that drifts up
    delivers *less* heat per kilogram — which is why the steam balance has to be solved
    rather than assumed.
    """
    return h_vapour_sat_kjkg(temperature_c) - h_liquid_sat_kjkg(temperature_c)


def v_liquid_sat_m3kg(temperature_c: float) -> float:
    """Saturated-liquid specific volume [m3/kg] at temperature [deg C]."""
    t_k = _sat_liquid_temperature_k(temperature_c + 273.15)
    return _region1(t_k, psat_mpa(t_k))[1]


def v_vapour_sat_m3kg(temperature_c: float) -> float:
    """Saturated-vapour specific volume [m3/kg] at temperature [deg C].

    Process utility: the steam space of a drum. This is the ``v`` in the real vapour-space
    capacitance that replaced the shared 0.02 bar/(kg/s) coefficient.
    """
    t_k = temperature_c + 273.15
    return _region2(t_k, psat_mpa(t_k))[1]


def rho_liquid_sat_kgm3(temperature_c: float) -> float:
    """Saturated-liquid density [kg/m3] at temperature [deg C].

    Process utility: converts a drum level to a mass inventory at the drum's *own*
    pressure. A fixed 1000 kg/m3 would over-read a 19.7 bar a saturator by about 15 %.
    """
    return 1.0 / v_liquid_sat_m3kg(temperature_c)


def h_liquid_kjkg(temperature_c: float, pressure_bara: float) -> float:
    """Compressed-liquid specific enthalpy [kJ/kg] (Region 1)."""
    return _region1(_sat_liquid_temperature_k(temperature_c + 273.15),
                    pressure_bara * _MPA_PER_BAR)[0]


def h_vapour_kjkg(temperature_c: float, pressure_bara: float) -> float:
    """Superheated-vapour specific enthalpy [kJ/kg] (Region 2).

    Process utility: the enthalpy of desuperheated let-down steam, which is what sets the
    attemperator water demand on the 9 -> 4 bar let-down.
    """
    return _region2(temperature_c + 273.15, pressure_bara * _MPA_PER_BAR)[0]


def v_vapour_m3kg(temperature_c: float, pressure_bara: float) -> float:
    """Superheated-vapour specific volume [m3/kg] (Region 2).

    Process utility: the compressibility of the steam a safety valve's capacity is certified
    on, Z = P v M / (R T), which carries that capacity across to the vapour a node vents.
    """
    return _region2(temperature_c + 273.15, pressure_bara * _MPA_PER_BAR)[1]


__all__ = [
    "OutOfRange",
    "R_KJ_KGK",
    "T_MIN_K",
    "T_CRIT_K",
    "P_CRIT_MPA",
    "REGION1_T_MAX_K",
    "psat_mpa",
    "tsat_k",
    "psat_bara",
    "tsat_c",
    "h_liquid_sat_kjkg",
    "h_vapour_sat_kjkg",
    "hvap_kjkg",
    "v_liquid_sat_m3kg",
    "v_vapour_sat_m3kg",
    "rho_liquid_sat_kgm3",
    "h_liquid_kjkg",
    "h_vapour_kjkg",
    "v_vapour_m3kg",
]
