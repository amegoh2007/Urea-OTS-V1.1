"""The urea melt's equilibrium strength under vacuum — 324E001 / 324F001 and 324E003 / 324F003.

Equipment served
----------------
The two evaporator stages of unit 324 and the two soft sensors that report their melt:
PY-324201 / AY-324701. A stage's melt leaves at the urea mass fraction whose water vapour
pressure holds the stage's vacuum at the stage's temperature — the boiling-point elevation of
the near-anhydrous melt read the other way round.

Equations
---------
The neutral H2O/urea UNIQUAC root (`extended_uniquac.solve_urea_mass_fraction_fast`), anchored
on the stage's design point as a departure:

    w_eq(T, P) = min( w_des + [ w_model(T, P) - w_model(T_des, P_des) ],  w_max )
                 in (1e-9, 1 - 1e-9)

so the PFD melt holds bit-exactly at design and only the off-design slope comes from the model.
Outside the model's window (99-200 C, 0.02-1.00 bar a) the arguments are held at its edge; a
state with no boiling root inside the window returns the design strength, no departure.

w_max is the strongest melt a stage can make from its feed: all its water boiled, its biuret
and formaldehyde still in it (`strength_ceiling`),

    w_max = w_urea / (w_urea + w_biuret + w_HCHO)        on the feed.

The model's one parameter is the caller's (``a_urea_water_k``, the urea -> H2O interaction
energy [K]; None is Voskov-Voronin's published -211.96 K, V1's).

Decided 2026-10-01 (handoff B-58, option a). The published parameter gives the PFD melts a water
activity coefficient of 0.52 and 0.48 where the PFD's own vapour rows imply 0.79 and 0.70: raw,
it boils them 13-14 K hotter, and anchored, its slopes run half as steep again as the plant's.
The stages run the parameter refitted to Helwan's PFD rows (-85.3 K, `data.unit_324`), which
lands on the Fahmy-Nassar plant correlation's temperature slopes within 5 %, and the cap, so a
stage can never boil its biuret as water (the heel class: what leaves cannot exceed what is
there). V1 runs the published parameter and no cap.

Source
------
V1 ``backend/main.py`` ``conc_infer_324`` (111-119), ``evap_w_eq`` (122-153),
``evap_thermo_diag`` (156-168), ported verbatim; the refit and the cap, handoff B-58.
"""

from __future__ import annotations

import math

from ureasim.thermo import extended_uniquac

#: The departure's limits on the urea mass fraction [-] (V1's literals).
W_FLOOR = 1.0e-9
W_CEILING = 1.0 - 1.0e-9

#: Kelvin offset as V1 writes it in these three functions.
KELVIN = 273.15


def _clamp(x: float, lo: float, hi: float) -> float:
    """V1's limiter, ``max(lo, min(hi, x))`` (``core.numeric.clamp``, which this layer may not
    import): a NaN comes back as ``hi``."""
    return max(lo, min(hi, x))


def strength_ceiling(w_urea: float, w_nonvolatile: float) -> float:
    """The strongest melt a stage can make from a feed [urea mass fraction, -].

    Process utility
    ---------------
    The melt's urea cannot pass what its non-volatiles leave room for: boil away every
    kilogram of water and the biuret and formaldehyde are still there. PFD 402 carries 0.86 wt%
    of them, so its urea tops out at 99.13 %. A stage asked for more would be boiling its
    biuret as water; this is the heel class of decision 11 applied to the melt (handoff B-58).

    Equation
    --------
        w_max = w_urea / (w_urea + w_nonvolatile)

    on the feed's mass fractions, ``w_nonvolatile`` the non-volatile species other than urea.
    A feed with no urea has no ceiling to speak of: 1.
    """
    total = w_urea + max(w_nonvolatile, 0.0)
    return w_urea / total if total > 0.0 else 1.0


def equilibrium_urea_fraction(t_c: float, p_bara: float, w_des: float, t_des_c: float,
                              p_des_bara: float, *, a_urea_water_k: float | None,
                              w_max: float | None = None) -> float:
    """The urea mass fraction a stage's melt reaches at (T, P), anchored on its design point.

    Process utility
    ---------------
    The evaporator's answer: given the vacuum the separator holds and the temperature its steam
    chest delivers, the melt strength — and with the feed's urea, the water the stage boils
    off. During a severe upset (a total 322E003 cooling loss collapses 322 -> 323 -> 324) the
    stage can be driven past the model's window; the arguments are held at the window's edge,
    and a state with no root returns the design strength, so the tick degrades rather than
    stops. ``w_max`` (`strength_ceiling`) holds the melt at what its feed can make.

    Equation in the module docstring. V1 ``evap_w_eq``, with the model's parameter an argument
    and the ceiling (handoff B-58).
    """
    t_lo, t_hi = extended_uniquac.VALID_TEMPERATURE_K
    p_lo, p_hi = extended_uniquac.VALID_PRESSURE_BARA
    t_k = _clamp(t_c + KELVIN, t_lo, t_hi) if math.isfinite(t_c) else t_lo
    p_b = _clamp(p_bara, p_lo, p_hi) if math.isfinite(p_bara) else p_lo
    a = a_urea_water_k
    try:
        w_model = extended_uniquac.solve_urea_mass_fraction_fast(t_k, p_b, a_urea_water_k=a)
        w_model_des = extended_uniquac.solve_urea_mass_fraction_fast(
            t_des_c + KELVIN, p_des_bara, a_urea_water_k=a)
    except (extended_uniquac.UnsupportedThermodynamicDomain, ValueError):
        w = _clamp(w_des, W_FLOOR, W_CEILING)
    else:
        w = _clamp(w_des + (w_model - w_model_des), W_FLOOR, W_CEILING)
    return w if w_max is None else min(w, w_max)


def melt_concentration_pct(w_des: float, t_des_c: float, p_des_bara: float, t_c: float,
                           p_bara: float, *, a_urea_water_k: float | None) -> float:
    """PY-324201 / AY-324701: the melt's urea strength [wt %] inferred from T and P.

    Process utility
    ---------------
    The soft sensor an operator reads for the melt: the same anchored equilibrium the stage's
    mass balance boils to. Inferred from T and P alone it cannot know the feed's biuret, so past
    the stage's ceiling it reads the equilibrium, not the capped melt. V1 ``conc_infer_324``
    (note its argument order: design point first).
    """
    return 100.0 * equilibrium_urea_fraction(t_c, p_bara, w_des, t_des_c, p_des_bara,
                                             a_urea_water_k=a_urea_water_k)


def melt_diagnostics(t_c: float, p_bara: float, w_eq: float, *,
                     a_urea_water_k: float | None) -> tuple[str, float | None]:
    """(validity status, P-x residual [bar]) for a stage, or ("OUTSIDE_MODEL_DOMAIN", None).

    Process utility
    ---------------
    Says when the melt strength is a design-anchored extrapolation and when the stage has left
    the model's window altogether — the telemetry an instructor needs to know a number is not
    validated. V1 ``evap_thermo_diag``, the residual on the stage's own parameter.
    """
    try:
        return (extended_uniquac.validity_status(t_c + KELVIN, p_bara),
                extended_uniquac.px_equilibrium_residual(w_eq, t_c + KELVIN, p_bara,
                                                         a_urea_water_k=a_urea_water_k))
    except (extended_uniquac.UnsupportedThermodynamicDomain, ValueError):
        return ("OUTSIDE_MODEL_DOMAIN", None)


__all__ = [
    "W_FLOOR", "W_CEILING", "KELVIN", "strength_ceiling", "equilibrium_urea_fraction",
    "melt_concentration_pct", "melt_diagnostics",
]
