"""Soave-Redlich-Kwong vapour-phase fugacity — the gas side of the gamma-phi formulation.

What this gives the plant model
-------------------------------
The vapour phase's departure from ideality. Everywhere the simulator computes a K-value it
uses the gamma-phi form

    K_i = gamma_i H_i / (phi_i^V P)

and `phi_i^V` is what this module supplies. It matters most exactly where the plant is
most interesting:

    322 HP loop      140-145 bar a — an ideal-gas vapour there is simply wrong
    HV-322604        letdown 140.7 -> 4.0 bar a; the SRK residual enthalpy is what makes
                     the Joule-Thomson result depend on the gas's real composition instead
                     of on a constant K/bar
    324 vacuum       0.131-0.33 bar a — here phi is close to 1, and the model says so
                     rather than being told so

Why SRK with k_ij = 0
---------------------
Thomsen (2005), the definitive open specification of the Extended UNIQUAC electrolyte
model this simulator's liquid phase uses, pairs it with SRK at k_ij = 0 for water and the
volatile solutes. Using the same gas model keeps the gamma-phi formulation internally
consistent with the source that fitted the liquid.

k_ij = 0 is a deliberate choice, not an omission: no binary interaction data exists in this
repository for these pairs, and inventing one would break the no-fabrication rule. The same
reasoning extends the mixing rule to the four synthesis-loop inerts.

Critical constants are public NIST/DIPPR values.

    Note on H2: its acentric factor is NEGATIVE (-0.216). That is the accepted published
    value, not a sign error, and it is what makes the SRK alpha function behave correctly
    for a quantum gas.

Ported from V1 `backend/props_nh3co2h2o.py` (SRK block). Numerically identical.
"""

from __future__ import annotations

import math

from ureasim.thermo.parameters import R

#: species -> (Tc [K], Pc [Pa], acentric factor omega). Public NIST/DIPPR values.
SRK_CRIT = {
    "H2O": (647.096, 22.064e6, 0.3443),
    "NH3": (405.40,  11.353e6, 0.2560),
    "CO2": (304.13,   7.377e6, 0.2239),
    # The four synthesis-loop inerts. Same class of public critical constants as the three
    # rows above, and the same k_ij = 0 mixing rule — no binary interaction data is invented
    # for them, which is exactly the stated reason k_ij = 0 was chosen for the first three.
    "N2":  (126.20,   3.3958e6,  0.0372),
    "O2":  (154.581,  5.043e6,   0.0222),
    "CH4": (190.564,  4.5992e6,  0.01142),
    "H2":  (33.145,   1.2964e6, -0.216),
}


def srk_ai_bi(sp: str, T: float) -> tuple[float, float]:
    """Pure-component SRK parameters ``(a_i, b_i)`` at T [K].

    Equations
    ---------
        m      = 0.480 + 1.574 w - 0.176 w^2
        alpha  = [ 1 + m (1 - sqrt(T/Tc)) ]^2
        a_i    = 0.42748 R^2 Tc^2 / Pc * alpha
        b_i    = 0.08664 R Tc / Pc

    The Soave alpha function is what gives SRK its vapour-pressure accuracy; ``b_i`` is the
    co-volume, which is what makes the compressibility fall below 1 at high pressure.
    """
    Tc, Pc, w = SRK_CRIT[sp]
    m = 0.480 + 1.574 * w - 0.176 * w * w
    alpha = (1.0 + m * (1.0 - math.sqrt(T / Tc))) ** 2
    ai = 0.42748 * R * R * Tc * Tc / Pc * alpha
    bi = 0.08664 * R * Tc / Pc
    return ai, bi


def cubic_largest_root(a3: float, a2: float, a1: float, a0: float) -> float:
    """Largest real root of ``a3 x^3 + a2 x^2 + a1 x + a0 = 0``.

    For the SRK cubic in Z this is the **vapour** compressibility root; the smallest real
    root would be the liquid one. Solved in closed form (Cardano for one real root, the
    trigonometric form for three) rather than iteratively, so the gas properties carry no
    solver tolerance.
    """
    p = a2 / a3
    q = a1 / a3
    r = a0 / a3
    # Depressed cubic t^3 + P t + Q = 0 with x = t - p/3.
    P = q - p * p / 3.0
    Q = 2.0 * p ** 3 / 27.0 - p * q / 3.0 + r
    disc = Q * Q / 4.0 + P ** 3 / 27.0
    if disc >= 0.0:
        # One real root — Cardano. copysign preserves the real cube root of a negative.
        sq = math.sqrt(disc)
        u = math.copysign(abs(-Q / 2.0 + sq) ** (1.0 / 3.0), -Q / 2.0 + sq)
        v = math.copysign(abs(-Q / 2.0 - sq) ** (1.0 / 3.0), -Q / 2.0 - sq)
        return u + v - p / 3.0
    # Three real roots — trigonometric form. Take the largest (the vapour root).
    m = 2.0 * math.sqrt(-P / 3.0)
    arg = (3.0 * Q) / (2.0 * P) * math.sqrt(-3.0 / P)
    arg = max(-1.0, min(1.0, arg))          # guard acos against round-off past +/-1
    phi = math.acos(arg) / 3.0
    roots = [m * math.cos(phi - 2.0 * math.pi * k / 3.0) - p / 3.0 for k in range(3)]
    return max(roots)


def srk_phi(y: dict, T: float, P: float) -> tuple[dict, float]:
    """SRK vapour fugacity coefficients for mixture ``y`` at T [K], P [Pa].

    Process utility
    ---------------
    Converts a partial pressure into a fugacity, which is what phase equilibrium is
    actually written in. At 140 bar a in the synthesis loop, phi for CO2 is well below 1,
    so treating the vapour as ideal would overstate its escaping tendency and put the HP
    loop's split in the wrong place.

    Parameters
    ----------
    y
        Vapour mole fractions, keyed by `SRK_CRIT` species names.
    T, P
        Temperature [K] and pressure [Pa].

    Returns
    -------
    ``(phi, Z)``
        Fugacity coefficients per species, and the vapour compressibility factor.

    Equations
    ---------
    Van der Waals one-fluid mixing with k_ij = 0:

        a_mix = ( sum_i y_i sqrt(a_i) )^2,        b_mix = sum_i y_i b_i
        A     = a_mix P / (R T)^2,                B     = b_mix P / (R T)
        Z^3 - Z^2 + (A - B - B^2) Z - A B = 0

        ln phi_i = (b_i/b_m)(Z - 1) - ln(Z - B)
                   - (A/B) [ 2 sqrt(a_i/a_m) - b_i/b_m ] ln(1 + B/Z)

    The ``2 sqrt(a_i/a_m)`` group is the k_ij = 0 simplification of
    ``2 (sum_j y_j a_ij) / a_m``.
    """
    sp = [s for s in y if y[s] > 0.0]
    a = {}
    b = {}
    for s in sp:
        a[s], b[s] = srk_ai_bi(s, T)
    sqrt_a = {s: math.sqrt(a[s]) for s in sp}
    am = sum(y[s] * sqrt_a[s] for s in sp) ** 2
    bm = sum(y[s] * b[s] for s in sp)
    A = am * P / (R * R * T * T)
    B = bm * P / (R * T)
    Z = cubic_largest_root(1.0, -1.0, A - B - B * B, -A * B)
    phi = {}
    for s in sp:
        bi_bm = b[s] / bm
        term = 2.0 * math.sqrt(a[s] / am)        # = 2 (sum_j y_j a_sj)/a_m when k_ij = 0
        ln_phi = (bi_bm * (Z - 1.0) - math.log(Z - B)
                  - (A / B) * (term - bi_bm) * math.log(1.0 + B / Z))
        phi[s] = math.exp(ln_phi)
    return phi, Z


__all__ = ["SRK_CRIT", "srk_ai_bi", "cubic_largest_root", "srk_phi"]
