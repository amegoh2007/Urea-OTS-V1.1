"""A vacuum stage's temperature-pressure fixed point where V1's Picard does not converge — 324F003.

What this models
----------------
Stage 2 solves its separator's temperature and vacuum together, V1's G7 Picard: each sweep takes
the melt's temperature step and the vacuum's backward step at the last iterate and repeats until
both stop moving (`second_evaporator.SecondEvaporator.step`). Drained to its 1 kg heel the held melt
has almost no heat capacity, and the water the feed boils switches on and off with the iterate's
temperature: the sweeps swing tens of kelvin from one to the next and never settle, and V1 leaves
the stage at the last of them — TT-324002 wandering between 52 and 118 C while the stage passes its
feed unconcentrated (handoff B-108).

Decided 2026-10-22 (handoff B-108, option a; decision 78's class — the implicit step where the
explicit one rings, V1's kept to the bit elsewhere). Where the sweeps do not converge, the
temperature is solved on the stage's own energy balance:

    G(T) = T_sweep(T, P(T)) - T = 0

T_sweep the temperature one sweep returns from the trial T, P(T) the vacuum that sweep's backward
step settles on at that trial temperature (the sweep repeated at T until the pressure stops
moving). G is positive below the root — the chest and the feed heat a melt colder than the balance
— and negative above it, so the root is bracketed and found by false position
(`core.numeric.bracketed_root`). A bracket G does not change sign across leaves V1's last sweep, as
V1 leaves it.

Source: handoff B-108 (As-Built Part LXXXI); V1 ``backend/main.py`` "Stage 2 : Evaporator II", G7.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ureasim.core.numeric import bracketed_root

__all__ = ["FixedPoint", "bisected_fixed_point"]

#: One sweep of the stage's solve from a trial (T, P): the vacuum and temperature it returns
#: [bar a], [deg C] and the holdup's boil-off [kg/h].
Sweep = Callable[[float, float], tuple[float, float, float]]


@dataclass(frozen=True)
class FixedPoint:
    """The stage's solved state: the vacuum [bar a], the temperature [deg C], the holdup's
    boil-off [kg/h], and the last sweep's residual [K or bar]."""

    p_bara: float
    t_c: float
    m_boil_kgh: float
    residual: float


def _settled(sweep: Sweep, t_c: float, p_start_bara: float, tol: float,
             max_sweeps: int) -> tuple[float, float, float, float]:
    """The sweep repeated at the trial temperature ``t_c`` until its vacuum stops moving: the
    pressure, the temperature the sweep returns, the boil-off, and the pressure's last move."""
    p = p_start_bara
    p_next, t_next, m_boil = sweep(t_c, p)
    for _ in range(max_sweeps - 1):
        if abs(p_next - p) <= tol:
            break
        p = p_next
        p_next, t_next, m_boil = sweep(t_c, p)
    return p_next, t_next, m_boil, abs(p_next - p)


def bisected_fixed_point(sweep: Sweep, t_lo_c: float, t_hi_c: float, p_start_bara: float,
                         tol: float, max_sweeps: int) -> FixedPoint | None:
    """The stage's temperature on its energy balance, bracketed in [t_lo, t_hi] [deg C].

    Process utility
    ---------------
    Gives TT-324002 the temperature at which the chest's heat, the feed's sensible heat and the
    water the feed boils balance, on a tick where V1's sweeps swing about it and never settle —
    a separator drained to its heel under a broken vacuum, where the melt has no heat capacity
    left to damp the swing. ``None`` where the bracket holds no sign change: the caller keeps
    V1's last sweep.

    Equation
    --------
        G(T) = T_sweep(T, P(T)) - T,      G(t_lo) > 0 > G(t_hi)

    solved by false position to ``tol``; the returned state is the sweep's at the root.
    """
    def g(t_c: float) -> float:
        return _settled(sweep, t_c, p_start_bara, tol, max_sweeps)[1] - t_c

    g_lo, g_hi = g(t_lo_c), g(t_hi_c)
    if not g_lo > 0.0 > g_hi:
        return None
    t_root = bracketed_root(g, t_lo_c, t_hi_c, g_lo, g_hi, tol=tol)
    p, t_c, m_boil, dp = _settled(sweep, t_root, p_start_bara, tol, max_sweeps)
    return FixedPoint(p_bara=p, t_c=t_c, m_boil_kgh=m_boil, residual=max(abs(t_c - t_root), dp))
