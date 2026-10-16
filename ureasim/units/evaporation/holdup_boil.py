"""The held liquor's own boil-off — 324F001 and 324F003, unit 324's evaporator separators, and
323F010, the pre-evaporator's.

What this models
----------------
The melt a vacuum separator holds boiling on its own. When the steam chest heats the holdup past
the boiling point of its own composition at the live vacuum, the excess sensible heat goes to
latent heat: water, and the volatiles with it, leave the holdup, the melt concentrates, and it
holds at its boiling point — which climbs as it concentrates, until its water is gone.

Decided 2026-10-01 (handoff B-62, option a; the Typo Rule). V1's boil-off is the feed's water
alone, the steady-flow closure of TD-016,

    m_vap = clamp( m_feed - m_urea / w_eq(T, P), 0, m_feed )

so a stage with no feed boils nothing: stop 323P003 and 324F001's held melt superheats to the
chest's saturation, 151.9 C, still 94.3 % urea, where at the vacuum it holds it would boil to
97 %. The trapped holdup is a bulk fluid: heated past its bubble point at the live vacuum, it
boils. The feed's term is V1's, untouched, so the design point holds exactly.

Equations
---------
The holdup's boiling strength is the stage's anchored melt equilibrium (`thermo.urea_melt`) on
the holdup's own design composition, so the design holdup sits exactly at its boiling point, and
under the holdup's own ceiling (decision 42's class):

    w_b(T, P) = min( w_u,des + [ w_model(T, P) - w_model(T_des, P_des) ],  w_max,hold )

The stage's temperature step gives T*. The holdup is superheated when w_b(T*, P) > w_u, its urea
mass fraction. It then boils x kg in the tick, the latent heat paid out of the step's own heat
capacity C (the semi-implicit step's denominator, M cp + k_cap dt), the vapour the stage's
(urea at y_u):

    T'       = T* - x lambda / C
    w_u'(x)  = (w_u M - y_u x) / (M - x)
    w_b(T', P) = w_u'(x)                              solved for x in (0, x_max]

x_max the volatiles above the ceiling, M (w_max - w_u) / (w_max - y_u), and at most the holdup
above its floor (decision 11's heel class); a vapour with y_u >= w_max — a dry melt's — cannot
concentrate it, and the melt does not boil; nor does a melt below the model's window, 99 C, where
the equilibrium holds the window's edge and no longer falls as the melt cools — x_max is also held
to the latent heat that brings T' to that edge, C (T* - 99) / lambda. The residual falls strictly with x — the melt cools
as it boils and strengthens as it loses water — so the root is unique; it is found by the
Illinois variant of regula falsi on the bracket.

DECIDED 2026-10-09 (handoff B-86, option c). A melt weaker than the window's edge allows at the
live vacuum, w_b(99, P) > w_u, boils below 99 C, where the model's equilibrium does not reach; its
boiling point is unknown, so the holdup does not boil and the stage runs on V1's closure alone, at
whatever temperature its step gives. Session 46's bound left such a melt boiling down to the edge
on every tick, so 324F003 parked at 99.0 C through Phase 7's cold start, and the tick it first
reached the edge it boiled 1.35 million kg/h (handoff B-87). A melt whose boiling point is inside
the window boils as before; there the root lies at T' >= 99 and the edge's cap never binds.

323F010 (decided 2026-10-02, handoff B-24, B-62's class). The pre-evaporator's liquor — 72 to 80 %
urea with its ammonia and CO2 — boils at the bubble point of its whole composition, not on the
melts' urea-water equilibrium, so its boil-off is solved in temperature on the stage's own bubble
point at the live vacuum (`liquor_boil`):

    T'          = T* - x lambda / C
    w_k'(x)     = (w_k M - y_k x) / (M - x)                     every species, y the overhead's
    T_bub(w'(x), P) = T'                                        solved for x in (0, x_max]

x_max the excess sensible heat paid as latent heat with the bubble point held, C (T* - T_bub) /
lambda, at most the holdup above its floor and the first species the overhead would exhaust. The
bubble point climbs as the overhead strips the volatiles, so the residual falls strictly and x_max
brackets the root; the same Illinois iteration finds it. V1 caps the overhead at the design split
of the feed (``min(phi m_feed, duty branch)``), so above design the surplus heat superheated the
liquor instead of concentrating it.

Source
------
Handoffs B-62 (As-Built §L) and B-24 (§LI). The equilibrium: `thermo.urea_melt` (V1
``evap_w_eq``, the B-58 refit and ceiling); 323F010's bubble point: `units.liquor_stage.bubble_t`
(V1 ``sol_bubble_t_dep``); the latent heats and the steps: the stages' (V1 ``main.py`` 8611-8617,
9800-9802, 9942-9944).
"""

from __future__ import annotations

from ureasim.thermo.domains import NONVOLATILE
from ureasim.thermo.extended_uniquac import VALID_TEMPERATURE_K
from ureasim.thermo.urea_melt import KELVIN, equilibrium_urea_fraction, strength_ceiling

#: The root's convergence: the bracket's width relative to its upper end, and the iteration cap
#: (the residual falls strictly and smoothly, so the Illinois iterates converge in about twenty).
ROOT_REL_TOL = 1.0e-14
ROOT_MAXIT = 200

#: The melt model's lowest temperature [deg C], 99: below it `equilibrium_urea_fraction` holds the
#: window's edge, so the strength no longer falls as the melt cools and every holdup a hair weaker
#: than it reads as superheated at any temperature. A held melt does not boil below it, and the
#: latent heat it pays cannot take it there (Phase 7, the cold start: 324F003 boiled down to -770 C;
#: As-Built §LXII.4).
T_WINDOW_LO_C = VALID_TEMPERATURE_K[0] - KELVIN


def _illinois(residual, lo: float, f_lo: float, hi: float, f_hi: float) -> float:
    """The root of a residual falling strictly on [lo, hi], f(lo) > 0 > f(hi): regula falsi,
    halving the retained end's residual when one end sticks (the Illinois variant)."""
    x, side = hi, 0
    for _ in range(ROOT_MAXIT):
        x = (lo * f_hi - hi * f_lo) / (f_hi - f_lo)
        f_x = residual(x)
        if f_x == 0.0 or hi - lo <= ROOT_REL_TOL * hi:
            break
        if f_x < 0.0:
            hi, f_hi = x, f_x
            if side == -1:
                f_lo *= 0.5
            side = -1
        else:
            lo, f_lo = x, f_x
            if side == +1:
                f_hi *= 0.5
            side = +1
    return x


def holdup_boil(t_c: float, p_bara: float, m_kg: float, w_hold: dict, heat_capacity_kjk: float,
                lambda_kjkg: float, y_urea: float, m_floor_kg: float, dt: float, *,
                w_des: float, t_des_c: float, p_des_bara: float,
                a_urea_water_k: float | None) -> tuple[float, float]:
    """(the holdup's own boil-off [kg/h], its temperature after boiling [deg C]).

    Process utility
    ---------------
    Lets a separator's held melt boil when its chest heats it past its own boiling point at the
    vacuum: a feed pump trip, a chest pushed above the feed's demand. The melt holds at its
    boiling point and concentrates, the condensers see the vapour, and TIC-324001 / TIC-324002
    see the temperature they act on — where V1's held melt superheats to the chest.

    Arguments
    ---------
    t_c
        T*, the stage's temperature step before the holdup boils [deg C].
    p_bara
        The live vacuum [bar a].
    m_kg, w_hold
        The holdup [kg] and its mass fractions at the top of the tick.
    heat_capacity_kjk
        C, the step's heat capacity [kJ/K]: what one kelvin of the step is worth.
    lambda_kjkg, y_urea
        The latent heat the stage pays [kJ/kg] and the vapour's urea mass fraction [-].
    m_floor_kg
        The holdup's floor [kg]: nothing below it boils.
    w_des, t_des_c, p_des_bara, a_urea_water_k
        The holdup's design urea fraction, the stage's design point and the melt's parameter.

    Equations in the module docstring.
    """
    w_u = w_hold.get("Urea", 0.0)
    w_max = strength_ceiling(w_u, sum(w_hold.get(k, 0.0) for k in NONVOLATILE if k != "Urea"))
    available_kg = m_kg - m_floor_kg
    # A vapour at least as rich in urea as the ceiling cannot concentrate the melt: a holdup whose
    # water is gone boils off urea alone, which x_max's denominator would turn negative — a
    # condensation of vapour the stage does not hold. Such a melt does not boil (Phase 7, the cold
    # start: 324F001 held dry on its floor for 6000 s, then fed; As-Built §LXII.4).
    if (available_kg <= 0.0 or w_u >= w_max or y_urea >= w_max or heat_capacity_kjk <= 0.0
            or t_c <= T_WINDOW_LO_C):
        return 0.0, t_c

    def w_boil(t: float) -> float:
        return equilibrium_urea_fraction(t, p_bara, w_des, t_des_c, p_des_bara,
                                         a_urea_water_k=a_urea_water_k, w_max=w_max)

    def residual(x: float) -> float:
        return w_boil(t_c - x * lambda_kjkg / heat_capacity_kjk) - (
            (w_u * m_kg - y_urea * x) / (m_kg - x))

    lo, f_lo = 0.0, w_boil(t_c) - w_u
    if f_lo <= 0.0:
        return 0.0, t_c
    # B-86: a melt weaker than the window's edge allows at this vacuum boils below 99 C, where the
    # model does not reach. Its boiling point is unknown, so it does not boil: V1's closure alone.
    if w_boil(T_WINDOW_LO_C) > w_u:
        return 0.0, t_c
    hi = min(m_kg * (w_max - w_u) / (w_max - y_urea), available_kg,
             heat_capacity_kjk * (t_c - T_WINDOW_LO_C) / lambda_kjkg)
    f_hi = residual(hi)
    x = hi if f_hi >= 0.0 else _illinois(residual, lo, f_lo, hi, f_hi)
    return x / dt * 3600.0, t_c - x * lambda_kjkg / heat_capacity_kjk


def liquor_boil(t_c: float, m_kg: float, w_hold: dict, heat_capacity_kjk: float,
                lambda_kjkg: float, y_overhead: dict, m_floor_kg: float, dt: float,
                bubble_t) -> tuple[float, float]:
    """(the holdup's own boil-off [kg/h], its temperature after boiling [deg C]) for a liquor
    that boils at the bubble point of its whole composition — 323F010's.

    Process utility
    ---------------
    Lets the pre-evaporator's liquor boil when its chest heats it past its own bubble point at
    the live vacuum — more steam, a higher TIC-323012 set point, a deeper vacuum through
    HV-323605 — so the product concentrates and the liquor holds at its bubble point, where V1's
    overhead stops at the design split and the surplus superheats the liquor.

    Arguments
    ---------
    t_c
        T*, the stage's temperature step before the holdup boils [deg C].
    m_kg, w_hold
        The holdup [kg] and its mass fractions at the top of the tick.
    heat_capacity_kjk
        C, the step's heat capacity [kJ/K].
    lambda_kjkg, y_overhead
        The latent heat the stage pays [kJ/kg] and the overhead's mass fractions [-].
    m_floor_kg
        The holdup's floor [kg]: nothing below it boils.
    bubble_t
        The liquor's bubble point at the live vacuum as a function of its mass fractions
        [deg C] — the caller closes it over the trial pressure.

    Equations in the module docstring.
    """
    available_kg = m_kg - m_floor_kg
    if available_kg <= 0.0 or heat_capacity_kjk <= 0.0:
        return 0.0, t_c
    f_lo = t_c - bubble_t(w_hold)
    if f_lo <= 0.0:
        return 0.0, t_c
    hi = min(f_lo * heat_capacity_kjk / lambda_kjkg, available_kg,
             *(w_hold.get(k, 0.0) * m_kg / y for k, y in y_overhead.items() if y > 0.0))

    def residual(x: float) -> float:
        after = {k: (w * m_kg - y_overhead.get(k, 0.0) * x) / (m_kg - x)
                 for k, w in w_hold.items()}
        return t_c - x * lambda_kjkg / heat_capacity_kjk - bubble_t(after)

    f_hi = residual(hi)
    x = hi if f_hi >= 0.0 else _illinois(residual, 0.0, f_lo, hi, f_hi)
    return x / dt * 3600.0, t_c - x * lambda_kjkg / heat_capacity_kjk


__all__ = ["ROOT_REL_TOL", "ROOT_MAXIT", "holdup_boil", "liquor_boil"]
