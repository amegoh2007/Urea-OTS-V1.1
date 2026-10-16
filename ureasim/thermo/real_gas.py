"""Real-gas isenthalpic letdown and compressibility — HV-322604 and the HP blow-through.

Equipment modelled
------------------
    HV-322604   lets 322E003 off-gas down from the synthesis loop (140.7 bar a) to the LP
                absorber 322C001 (4.0 bar a) — a pressure ratio of 0.028.
    LV-322501   the stripper bottoms letdown, whose gas blow-through rate needs a real
                density at 140.7 bar a.

What this replaced
------------------
A constant Joule-Thomson coefficient:

    T_out = T_in - 0.55 C/bar . dP    ->   114 - 0.55(136.7) = 38.8 C at design

0.55 K/bar is typical of an NH3/CO2-rich gas. **PFD stream 204 is not that gas.** It is
68.8 mol% N2, 11.4 % O2, 5.9 % CH4, 3.1 % H2 and only 8.3 % NH3 / 2.2 % CO2. A constant
coefficient cannot follow either the composition or the inlet state, so the model could not
respond to inert accumulation — the very thing the purge exists to manage.

The physics
-----------
A letdown valve is adiabatic and does no work, so it is **isenthalpic**:

    h_ig(T_out) + h_res(T_out, P_out) = h_ig(T_in) + h_res(T_in, P_in)

with the ideal-gas part from the H0 elemental datum (`thermo.enthalpy`) — the same datum
every stream enthalpy in the engine is published on — and the residual from the SRK cubic
(`thermo.srk`), same critical constants, same k_ij = 0 mixing:

    h_res = R T (Z - 1) + (T da_m/dT - a_m)/b_m . ln((Z + B)/Z)

Result
------
On the PFD 204 composition that gives **94.8 C** at the 322C001 inlet — a mean coefficient
of 0.14 K/bar, a quarter of the constant it replaced, which is what a gas that is mostly
nitrogen does.

No plant instrument sits downstream of HV-322604, so there is nothing to anchor to: this is
a first-principles result, and it is labelled as one.

Scope
-----
Single-phase gas. At the design outlet the NH3 and water partial pressures (0.33 and 0.01
bar) are far from saturation, so no liquid forms. `condensing` flags an outlet where water
*would* condense, because this routine does not do the two-phase flash that state needs —
the flag is a refusal to answer, not a correction. The two-phase answer below the dew point
is `thermo.condensing_letdown`'s (handoff B-19, decided 2026-10-01), which keeps this
relation for every gas that stays dry.

Ported from V1 `backend/real_gas.py`. Numerically identical.
"""

from __future__ import annotations

import math

from ureasim.thermo import enthalpy as h0
from ureasim.thermo import iapws
from ureasim.thermo.parameters import R
from ureasim.thermo.srk import SRK_CRIT, cubic_largest_root, srk_ai_bi

#: Vapour-phase reference column, so every species is priced as a gas.
_GAS = h0._VAPOUR_PHASE

#: Species the SRK parameter set covers: H2O NH3 CO2 N2 O2 CH4 H2.
SPECIES = tuple(SRK_CRIT)


def _mix(y: dict, t_k: float) -> tuple[float, float]:
    """SRK mixture parameters ``(a_m(T), b_m)`` for mole fractions ``y``, k_ij = 0."""
    s = 0.0
    b = 0.0
    for k, v in y.items():
        a_i, b_i = srk_ai_bi(k, t_k)
        s += v * math.sqrt(a_i)
        b += v * b_i
    return s * s, b


def mole_fractions(comp_kmolh: dict) -> dict:
    """Normalise a ``{species: kmol/h}`` vector to mole fractions over `SPECIES`.

    Species outside the SRK set are dropped: they are the non-volatile condensed species
    (urea, biuret, carbamate), which do not belong in a vapour calculation at all.
    """
    n = {k: max(comp_kmolh.get(k, 0.0), 0.0) for k in SPECIES}
    tot = sum(n.values())
    return {k: v / tot for k, v in n.items() if v > 0.0} if tot > 0.0 else {}


def h_residual(y: dict, t_k: float, p_pa: float) -> float:
    """SRK residual molar enthalpy [J/mol] of a vapour mixture.

    Process utility
    ---------------
    The departure from ideal-gas enthalpy. This term is the entire Joule-Thomson effect: an
    ideal gas has zero residual enthalpy and therefore does not cool on letdown at all.

    Equation
    --------
        h_res = R T (Z - 1) + (T da_m/dT - a_m) / b_m . ln((Z + B)/Z)

    ``da_m/dT`` is taken by central difference over 1 mK. An analytic derivative exists but
    is a second transcription of the Soave alpha function, and an error in it would be
    silent — it would shift the outlet temperature without failing.
    """
    a_m, b_m = _mix(y, t_k)
    big_a = a_m * p_pa / (R * R * t_k * t_k)
    big_b = b_m * p_pa / (R * t_k)
    z = cubic_largest_root(1.0, -1.0, big_a - big_b - big_b * big_b, -big_a * big_b)
    h = 1.0e-3
    da_dt = (_mix(y, t_k + h)[0] - _mix(y, t_k - h)[0]) / (2.0 * h)
    return R * t_k * (z - 1.0) + (t_k * da_dt - a_m) / b_m * math.log((z + big_b) / z)


def z_factor(comp_kmolh: dict, t_c: float, p_bara: float) -> float:
    """SRK vapour compressibility Z of a gas mixture; 1.0 for an empty vector.

    Process utility
    ---------------
    Gas density is ``P M / (Z R T)``. The LV-322501 blow-through takes its density this
    way: the stripper gas at 140.7 bar a is NH3/CO2-rich, where the ideal-gas density is
    well off, and the blow-through rate is proportional to the square root of it.
    """
    y = mole_fractions(comp_kmolh)
    if not y or p_bara <= 0.0:
        return 1.0
    t_k = t_c + 273.15
    a_m, b_m = _mix(y, t_k)
    p_pa = p_bara * 1.0e5
    big_a = a_m * p_pa / (R * R * t_k * t_k)
    big_b = b_m * p_pa / (R * t_k)
    return cubic_largest_root(1.0, -1.0, big_a - big_b - big_b * big_b, -big_a * big_b)


def h_molar(y: dict, t_k: float, p_pa: float) -> float:
    """Real-gas molar enthalpy [J/mol] on the elements-at-298.15 K datum.

    Ideal-gas formation plus sensible heat, from the shared H0 datum, plus the SRK
    residual. Being on the elements datum is what lets this enthalpy be compared with any
    other stream in the plant.
    """
    return (sum(v * h0.h_species(k, _GAS[k], t_k) for k, v in y.items())
            + h_residual(y, t_k, p_pa))


def isenthalpic_letdown(comp_kmolh: dict, t_in_c: float,
                        p_in_bara: float, p_out_bara: float) -> dict:
    """Outlet temperature of an adiabatic, isenthalpic letdown of a single-phase gas.

    Process utility
    ---------------
    HV-322604's outlet temperature sets the LP absorber's inlet condition, which sets how
    much NH3 the absorber's upper bed has to take up. Because it is computed from the real
    composition, inert accumulation in the loop now *changes* it — which is the mechanism
    behind the "loop is going soft" scenario a trainee has to recognise.

    Returns
    -------
    dict
        ``t_out_c``, ``mu_jt_k_bar`` (the mean Joule-Thomson coefficient actually
        realised), and ``condensing``.

    Method
    ------
    Illinois regula falsi on ``T_out`` over ``(T_in - 150 K, T_in + 20 K)``. The lower end
    is far below any letdown this plant makes; the upper end covers the **reverse**
    (heating) effect of a hydrogen-rich gas, which is real — hydrogen's inversion
    temperature is below ambient, so it warms on expansion.

    The Illinois modification halves the retained endpoint's function value when the same
    side is kept twice, which prevents the slow one-sided crawl plain regula falsi suffers
    on a convex residual. Deterministic in its operands: no random restarts, fixed
    iteration cap.
    """
    y = mole_fractions(comp_kmolh)
    if not y or p_out_bara >= p_in_bara:
        # Not a letdown. Returning the inlet unchanged is correct and avoids a spurious
        # temperature change when a valve is shut or the loop pressure has collapsed.
        return {"t_out_c": t_in_c, "mu_jt_k_bar": 0.0, "condensing": False}

    t_in = t_in_c + 273.15
    h_in = h_molar(y, t_in, p_in_bara * 1.0e5)

    def f(t_k: float) -> float:
        """Enthalpy departure from the inlet, at the OUTLET pressure."""
        return h_molar(y, t_k, p_out_bara * 1.0e5) - h_in

    lo, hi = t_in - 150.0, t_in + 20.0
    f_lo, f_hi = f(lo), f(hi)
    if f_lo >= 0.0:
        t_out = lo
    elif f_hi <= 0.0:
        t_out = hi
    else:
        side = 0
        t_out = t_in
        for _ in range(60):
            t_out = (lo * f_hi - hi * f_lo) / (f_hi - f_lo)
            r = f(t_out)
            if abs(r) <= 1.0e-6 or hi - lo <= 1.0e-9:
                break
            if r < 0.0:
                lo, f_lo = t_out, r
                if side == 1:
                    f_hi *= 0.5          # Illinois: deflate the stagnant endpoint
                side = 1
            else:
                hi, f_hi = t_out, r
                if side == -1:
                    f_lo *= 0.5
                side = -1

    t_out_c = t_out - 273.15
    p_h2o = y.get("H2O", 0.0) * p_out_bara
    return {
        "t_out_c": t_out_c,
        "mu_jt_k_bar": (t_in_c - t_out_c) / (p_in_bara - p_out_bara),
        # A flag, not a correction: this routine does no two-phase flash, so an outlet
        # where water would condense is outside its scope and says so.
        "condensing": p_h2o >= iapws.psat_bara(max(t_out_c, 0.01)),
    }


__all__ = [
    "SPECIES",
    "mole_fractions",
    "h_residual",
    "z_factor",
    "h_molar",
    "isenthalpic_letdown",
]
