"""The adiabatic mix of steam into a gas that carries water vapour, at a fixed pressure.

What this gives the plant model
-------------------------------
No equipment: the temperature an adiabatic mixing point reaches when steam joins a gas — a
steam ejector's discharge, its motive steam and the vapour it entrains, with the jet's kinetic
energy recovered in the diffuser, so the stream leaves with the inlets' enthalpy (handoff B-97,
decided 2026-10-16: 324F002's discharge, PFD 708).

Equations
---------
The inlets' enthalpy, the gas's water saturated vapour at the gas's temperature, its other species
on the H0 vapour datum, the steam at the enthalpy it arrives with:

    H_in = sum_k n_k h_k(T_g) + m_w,g h_g,sat(T_g) + m_s h_s           [kJ/h]

The mix at pressure P and temperature T. The water stays vapour while its partial pressure stays
under saturation; past it, the gas holds the vapour saturation allows and the rest condenses:

    n_w,v = n_w                                   if P n_w / (n_w + n_g) <= p_sat(T)
    n_w,v = n_g p_sat(T) / (P - p_sat(T))         otherwise (p_sat(T) < P)

    H(T) = sum_k n_k h_k(T) + M_w n_w,v h_v(T, p_w,v) + M_w (n_w - n_w,v) h_f(T),
    p_w,v = P n_w,v / (n_w,v + n_g)

each species at its own partial pressure, the water on IAPWS-IF97 (`thermo.iapws`), the other
species on `thermo.enthalpy` (whose formation terms cancel: no species reacts). H rises with T,
so H(T) = H_in has one root, found by the Illinois variant of regula falsi on IF97's liquid
range, [T_triple, 350 C], until its bracket closes to MIX_TOL_K.

Declared approximation: NH3 and CO2 stay in the gas when water condenses; what of them the
condensate would dissolve, and its heat, are left out. The mix is the gas's sensible heat and the
water's latent heat only.

Source: the first law across an adiabatic mixing point; IAPWS-IF97 for water and steam;
CODATA / NIST-JANAF heat capacities for the gases (`thermo.enthalpy`).
"""

from __future__ import annotations

from ureasim.thermo import iapws
from ureasim.thermo.enthalpy import MOLAR_MASS, h_species, reference_phase

#: The bracket the mix temperature is solved on [deg C]: IF97's triple point and its liquid
#: region's ceiling, the range on which every water property the mix evaluates is defined.
MIX_T_MIN_C = iapws.T_MIN_K - 273.15
MIX_T_MAX_C = iapws.REGION1_T_MAX_K - 273.15

#: The width the bracket closes to [K]: far below any temperature a console shows.
MIX_TOL_K = 1.0e-9

#: The water's molar mass [kg/kmol].
M_H2O = MOLAR_MASS["H2O"]


def _gas_kjh(n_kmolh: dict, t_c: float) -> float:
    """The non-water species' enthalpy [kJ/h]: kmol/h times J/mol is kJ/h."""
    t_k = t_c + 273.15
    return sum(n * h_species(k, reference_phase(k, "vapour"), t_k)
               for k, n in n_kmolh.items() if n > 0.0)


def mixture_kjh(gas_kmolh: dict, n_w_kmolh: float, t_c: float, p_bara: float) -> float:
    """The mix's enthalpy at a trial temperature [kJ/h] (equations in the module docstring).

    Process utility
    ---------------
    The left-hand side of the mixing point's first law: how much enthalpy the stream must carry
    to leave at ``t_c``. Below its dew point the condensing water's latent heat is what keeps
    an ejector's discharge from falling to its suction's temperature when its motive steam fails.
    """
    n_g = sum(gas_kmolh.values())
    p_s = iapws.psat_bara(t_c)
    n_wv = n_w_kmolh
    if p_s < p_bara and p_bara * n_w_kmolh > p_s * (n_w_kmolh + n_g):
        n_wv = n_g * p_s / (p_bara - p_s)
    h = _gas_kjh(gas_kmolh, t_c)
    if n_wv > 0.0:
        h += M_H2O * n_wv * iapws.h_vapour_kjkg(t_c, p_bara * n_wv / (n_wv + n_g))
    if n_w_kmolh > n_wv:
        h += M_H2O * (n_w_kmolh - n_wv) * iapws.h_liquid_sat_kjkg(t_c)
    return h


def mix_temperature_c(gas_kmolh: dict, t_gas_c: float, steam_kgh: float, h_steam_kjkg: float,
                      p_bara: float) -> float:
    """The temperature an adiabatic mix of steam into a wet gas leaves at [deg C].

    Process utility
    ---------------
    A steam ejector's discharge temperature: the motive steam's enthalpy shared with what it
    entrains. Less motive steam, or a colder suction, and the discharge runs cooler; a header at
    a higher pressure brings steam of more enthalpy and runs it warmer.

    Arguments
    ---------
    gas_kmolh
        The gas's species [kmol/h], its water ("H2O") saturated vapour at ``t_gas_c``.
    t_gas_c
        The gas's temperature [deg C].
    steam_kgh, h_steam_kjkg
        The steam [kg/h] and its specific enthalpy [kJ/kg] on IF97's datum.
    p_bara
        The mixing point's pressure [bar a].

    Raises ValueError when nothing arrives: a mix of nothing has no temperature.
    """
    n_w = gas_kmolh.get("H2O", 0.0) + steam_kgh / M_H2O
    gas = {k: n for k, n in gas_kmolh.items() if k != "H2O"}
    if n_w + sum(gas.values()) <= 0.0:
        raise ValueError("nothing arrives at the mixing point")
    h_in = (_gas_kjh(gas, t_gas_c) + steam_kgh * h_steam_kjkg
            + M_H2O * gas_kmolh.get("H2O", 0.0) * iapws.h_vapour_sat_kjkg(t_gas_c))

    # Illinois regula falsi: the secant through the bracket's ends, the end kept twice having
    # its residual halved so the bracket closes from both sides.
    lo, hi = MIX_T_MIN_C, MIX_T_MAX_C
    f_lo = mixture_kjh(gas, n_w, lo, p_bara) - h_in
    f_hi = mixture_kjh(gas, n_w, hi, p_bara) - h_in
    kept = 0
    while hi - lo > MIX_TOL_K:
        t = (lo * f_hi - hi * f_lo) / (f_hi - f_lo)
        if not lo < t < hi:
            t = 0.5 * (lo + hi)
        f = mixture_kjh(gas, n_w, t, p_bara) - h_in
        if f == 0.0:
            return t
        if (f > 0.0) == (f_hi > 0.0):
            hi, f_hi = t, f
            if kept == 1:
                f_lo *= 0.5
            kept = 1
        else:
            lo, f_lo = t, f
            if kept == -1:
                f_hi *= 0.5
            kept = -1
    return 0.5 * (lo + hi)


__all__ = ["MIX_T_MIN_C", "MIX_T_MAX_C", "MIX_TOL_K", "M_H2O", "mixture_kjh",
           "mix_temperature_c"]
