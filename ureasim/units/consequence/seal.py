"""The liquid seal over a drain nozzle, and the gas that escapes once it is lost.

What this models
----------------
Every level-controlled vessel in this plant drains through a control valve that is sized for
liquid. While the drain nozzle is covered, that is all it passes. When the level falls to the
nozzle, the valve starts to see the vessel's gas inventory instead — through a trim whose
flow coefficient was fixed by a LIQUID duty, at whatever differential the vessel happens to
be holding.

Two pieces of physics follow, and this module is both of them:

1. **How much of the nozzle is still covered** (`seal_fraction`). A nozzle does not uncover
   at a mathematical point; it uncovers over its own bore, and across that band the valve
   passes a two-phase mixture whose gas fraction grows with the uncovered area.
2. **What the same trim passes as gas** (`blowthrough_kgh`). Compressible flow through a
   control valve is IEC 60534 / ISA-75.01, and the valve's own liquid design duty supplies
   the flow coefficient, so nothing here is tuned.

Why this matters on the plant
------------------------------
Because the consequence of losing a seal is not that the drain stops. It is that the drain
keeps flowing and starts passing gas: the downstream section — sized for liquid, and often at
a small fraction of the upstream pressure — takes a vapour load it was never designed for,
and the valve trim erodes because a flashing gas stream through a liquid trim is a sandblaster.
On LV-322501 that is 140 bar a of stripper vapour arriving in a 4 bar a recirculation section.

Why the seal is a ramp and not an `if`
---------------------------------------
`if level <= 0` is a step change in the right-hand side of a level ODE. It chatters, it
arrives with zero transport lag however far downstream the affected equipment sits, and on
most of these vessels it is simply wrong — the level tap sits above the drain nozzle, so
blow-through starts BEFORE the transmitter reads zero. A linear ramp across the nozzle bore
removes the step, reproduces the early start, and makes the transition reversible, so
restoring level restores the seal instead of leaving a latched state.

Source
------
Ported from V1 `backend/consequence.py`, sections 1 and 2.

References
----------
Control-valve sizing — the gas expansion factor Y, the terminal pressure-drop ratio x_T and
the specific-heat-ratio factor F_k — is IEC 60534-2-1 / ISA-75.01.01 in its standard form:

    m = N . C . Y . sqrt(x . P1 . rho1)
    Y = 1 - x / (3 . F_k . x_T)
    x_choked = F_k . x_T
"""

from __future__ import annotations

import math

from ureasim.core.numeric import clamp_preserving_nan
from ureasim.core.units_of_measure import R_GAS_J

# ======================================================================================
# Section 1 — the liquid seal
# ======================================================================================

#: Width of the seal ramp [% of level span] — the drain-nozzle bore expressed in the units
#: the level transmitter reads in. 3 % of span is the generic value V1 applied to every
#: vessel; a vessel with a datasheet nozzle size and a datasheet level span can pass its own.
#:
#: Source: V1 `backend/consequence.py` SEAL_BAND_PCT_DEFAULT.
SEAL_BAND_PCT_DEFAULT = 3.0


def seal_fraction(level_pct: float, seal_pct: float = 0.0,
                  band_pct: float = SEAL_BAND_PCT_DEFAULT) -> float:
    """Fraction of the drain nozzle still covered by liquid [-]. 1.0 sealed, 0.0 open to gas.

    Process utility
    ---------------
    This is the single number that says whether a vessel is still draining liquid or has
    started passing its own vapour inventory downstream. Every consequence keyed on a lost
    seal is written as ``(1 - seal_fraction)``, so all of them are exactly 0.0 whenever the
    vessel holds a normal level — which is the design-anchor contract, not a tolerance.

    Equation
    --------
        seal = clamp( (level - seal_pct) / band_pct , 0, 1 )

    ``seal_pct`` is the transmitter reading at which the nozzle is JUST fully uncovered — the
    nozzle centreline — and ``band_pct`` is the bore in the same % units. Both default to the
    generic case: a nozzle at the bottom of the span, 3 % of span across.

    The limiter preserves a NaN rather than pinning it to 1.0. A NaN level that came back as
    "fully sealed" would silently report a healthy drain, which is the one failure mode this
    function exists to catch; see `core.numeric.clamp_preserving_nan`.
    """
    return clamp_preserving_nan((level_pct - seal_pct) / max(band_pct, 1e-9), 0.0, 1.0)


# ======================================================================================
# Section 2 — compressible flow through a valve sized for liquid
# ======================================================================================

#: Terminal pressure-drop ratio x_T [-] for a generic single-seat globe trim, flow-to-open.
#: The ratio dP/P1 at which the vena contracta chokes. Source: IEC 60534-2-1 typical values,
#: carried through V1 `backend/consequence.py` as the `x_t` default.
X_T_DEFAULT = 0.70

#: Specific-heat ratio [-] of the process vapour. 1.30 is the generic value V1 used for the
#: NH3 / CO2 / H2O vapours in this plant, which sit between the 1.3 of ammonia and the 1.29
#: of carbon dioxide at process conditions. Source: V1 `backend/consequence.py` `gamma`.
GAMMA_DEFAULT = 1.30


def gas_density_ideal(p_bara: float, t_c: float, mw_g_mol: float) -> float:
    """Ideal-gas density [kg/m3]:  ``rho = P . M / (R . T)``.

    Process utility
    ---------------
    The mass a valve passes as gas scales with ``sqrt(rho_gas)``, so this is what converts a
    vessel's live pressure and temperature into a blow-through rate. Ideal gas is deliberate
    at the API boundary: where a node is dense enough for it to matter — the 140 bar a
    synthesis loop is the obvious one — the caller divides by a compressibility factor from
    `thermo.real_gas`, which keeps the equation of state in the thermo layer where it belongs
    rather than burying an SRK call inside a consequence helper.

    The pressure floor is a guard against a divide-by-zero further down, not a physical
    minimum; the temperature floor of 1 K likewise.
    """
    return max(p_bara, 1e-9) * 1e5 * (mw_g_mol / 1000.0) / (R_GAS_J * max(t_c + 273.15, 1.0))


def expansion_factor(dp_bar: float, p1_bara: float, x_t: float = X_T_DEFAULT,
                     gamma: float = GAMMA_DEFAULT) -> tuple[float, float, bool]:
    """IEC 60534-2-1 compressible correction. Returns ``(Y, dp_effective_bar, choked)``.

    Process utility
    ---------------
    A gas is compressible, so it does not keep accelerating as the downstream pressure is
    pulled away: past the choke point the vena contracta reaches sonic velocity and the mass
    flow stops responding to the downstream side entirely. That is exactly why a seal-loss
    blow-through has a CEILING rather than running away as the downstream section
    depressurises, and it is the difference between a trainable upset and a numerical
    explosion in the downstream pressure node.

    Equations
    ---------
        x      = dP / P1                     pressure-drop ratio
        F_k    = gamma / 1.40                specific-heat-ratio factor
        x_ch   = F_k . x_T                   the ratio at which the vena contracta chokes
        x_eff  = min(x, x_ch)                beyond the choke point, no further work is done
        Y      = 1 - x_eff / (3 . x_ch)      expansion factor, bounded to [2/3, 1]
        dP_eff = x_eff . P1                  the drop that actually drives the flow

    Y runs from 1 at a vanishing drop (the gas behaves as an incompressible fluid) to exactly
    2/3 at the choke point, which is the standard bound: the 1.40 in F_k is air, the reference
    gas the x_T tables are measured on.
    """
    p1 = max(p1_bara, 1e-9)
    x = clamp_preserving_nan(dp_bar / p1, 0.0, 1.0)
    x_ch = max((gamma / 1.40) * x_t, 1e-6)
    choked = x >= x_ch
    x_eff = min(x, x_ch)
    y = clamp_preserving_nan(1.0 - x_eff / (3.0 * x_ch), 2.0 / 3.0, 1.0)
    return y, x_eff * p1, choked


def blowthrough_kgh(m_liq_des_kgh: float, rho_liq: float, dp_des_bar: float,
                    theta_frac: float, rho_gas: float, p_up_bara: float, dp_bar: float,
                    seal_frac: float, x_t: float = X_T_DEFAULT,
                    gamma: float = GAMMA_DEFAULT) -> float:
    """Gas mass flow through a drain valve whose liquid seal has been (partly) lost [kg/h].

    Process utility
    ---------------
    This is the rate at which a vessel that has run dry empties its gas inventory into the
    section below it. The operator sees it as a downstream pressure that will not come down,
    a level that will not come back, and — over a shift rather than a minute — a valve that no
    longer shuts off, because a flashing gas stream through a liquid trim erodes the seat.

    Why it is not a tuned number
    -----------------------------
    A control valve's flow coefficient is a property of the VALVE, not of the fluid, so it can
    be eliminated. From the liquid design duty,

        C = m_liq_des / (N . sqrt(rho_liq . dP_des))

    and from IEC 60534 compressible flow at a stroke of theta,

        m_gas = N . C . theta . Y . sqrt(rho_gas . dP_eff)

    Substituting the first into the second, N and C cancel identically and leave

        m_gas = m_liq_des . theta . Y . sqrt( rho_gas . dP_eff / (rho_liq . dP_des) )
                          . (1 - seal_frac)

    so the blow-through rate is fixed by the valve's own design duty and the live gas density.
    Nothing here is picked to taste.

    Evaluated at LV-322501's design stroke and design loop pressure with the nozzle fully
    uncovered, the derived rate is 25.4 t/h against the 25 t/h that had been hand-picked for
    that one valve in V1 — which is the point. The hand number was defensible where it stood
    and could not be transferred to any other valve, and that was the whole problem. (V1's
    own docstring quotes about 30 t/h for the same comparison; that is the rate at a wider
    stroke.)

    The ``sqrt(rho_gas / rho_liq)`` factor is the physical story an operator needs. Gas is
    lighter than the liquor, so the same valve opening passes far less MASS. Whether it also
    passes more VOLUME — and so whether the downstream section overpressures — depends on how
    dense the vapour is, because the volumetric ratio is ``Y . sqrt(rho_liq / rho_gas)`` at a
    matched differential. At LV-322501's 144 bar a the vapour is 141 kg/m3 and the ratio is
    only about 1.6; at LV-323501's 4 bar a it is about 16, which is why the same event is
    far more violent for the LP section than for the HP one.

    Anchoring
    ---------
    The ``(1 - seal_frac)`` factor makes this identically 0.0 whenever the vessel holds a
    normal level, and the three short-circuits below make it exactly 0.0 — by return, not by
    arithmetic — when the vessel is sealed, the valve is shut, or the differential has
    collapsed.
    """
    if seal_frac >= 1.0 or theta_frac <= 0.0 or dp_bar <= 0.0:
        return 0.0
    y, dp_eff, _ = expansion_factor(dp_bar, p_up_bara, x_t, gamma)
    ratio = (max(rho_gas, 1e-9) * max(dp_eff, 0.0)) / (max(rho_liq, 1e-9) * max(dp_des_bar, 1e-9))
    return max(m_liq_des_kgh, 0.0) * max(theta_frac, 0.0) * y * math.sqrt(max(ratio, 0.0)) \
        * (1.0 - seal_frac)


__all__ = [
    "SEAL_BAND_PCT_DEFAULT",
    "X_T_DEFAULT",
    "GAMMA_DEFAULT",
    "seal_fraction",
    "gas_density_ideal",
    "expansion_factor",
    "blowthrough_kgh",
]
