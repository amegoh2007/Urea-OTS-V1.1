"""A node — one lump of inventory with a pressure and a level.

What this models
----------------
Any place in the flowsheet where material accumulates: a vessel, a separator, a column
sump, a reflux drum, and — this is the part that is easy to miss — a run of line between
two machines. The 320K002 discharge header holds 5234 kg of CO2 in 21.566 m3 and behaves
exactly like a small vessel, so it uses this same module.

Process utility
---------------
A node is what makes the plant *dynamic*. Without inventory, every branch has to satisfy
its mass balance instantaneously, which makes the junction far stiffer than the plant and
turns a pressure into an algebraic consequence of flow. On the plant it is the other way
round: flow follows pressure, and pressure follows inventory.

The two equations
-----------------
Vapour space::

    dP/dt = (R.T / V_v) . (n_gen - n_out)  +  (P/T) . dT/dt  -  (P/V_v) . dV_v/dt

Liquid space::

    dM/dt = m_in - m_out

Term by term, and why each one had to be there
-----------------------------------------------
* **Molar accumulation** needs MOLES, not mass. V1's predecessor used a single lumped
  ``dP/dt = K (gen - out)`` with one copy-pasted ``K = 0.02 bar/(kg/s)`` shared by nine
  vessels — a 0.46 bar a vacuum separator and a 16.8 bar a hydrolyser on the same
  coefficient, and NH3 (MW 17) and CO2 (MW 44) treated as the same gas. The real
  coefficient is ``R.T/V_v``, which each vessel computes from its own geometry and its own
  live state.
* **The thermal term** is why heating a closed vapour space raises its pressure with no
  molar change at all — the mechanism behind a blocked-in line and behind every
  steam-flood trip in this plant.
* **The swell term** is the coupling a lumped capacitance throws away: a vessel filling up
  gets a STIFFER pressure response, and that is what makes a level excursion show on the
  pressure transmitter.

Source: V1 `backend/hydraulics.py`, "Vapour-space pressure state (A-6 / A-7)", plus the
liquid-inventory integration V1 writes inline at each stage. Ported verbatim.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from ureasim.core.numeric import clamp
from ureasim.core.units_of_measure import R_GAS_J

__all__ = ["vapour_volume_m3", "vessel_dpdt", "backward_euler_pressure", "stable_pressure_step",
           "EXPLICIT_STEP_LIMIT", "advance_holdup_kg", "level_pct_from_holdup",
           "solve_node_pressure"]

#: The backward step's Newton: iterations, the derivative's probe [bar] and the step that counts
#: as converged to rounding [bar] (V1's literals in `_backward_euler_p`).
BACKWARD_EULER_ITERS = 40
BACKWARD_EULER_PROBE_BARA = 1.0e-7
BACKWARD_EULER_STEP_TOL_BARA = 1.0e-14

#: The explicit step's limit on its own linearisation, dt . df/dP [-] (handoff B-51, decided
#: 2026-10-09). Forward Euler multiplies a departure from the pressure the node is heading for by
#: 1 + dt . df/dP each tick: at -1 that factor reaches zero, and below it the step overshoots and
#: the departure changes sign every tick — the ringing B-51 measured. Not a tuning: the analytic
#: edge of a monotone explicit step.
EXPLICIT_STEP_LIMIT = -1.0


# ======================================================================================
# Vapour space
# ======================================================================================

def vapour_volume_m3(v_vessel_m3: float, m_liquid_kg: float, rho_liquid_kgm3: float,
                     v_min_frac: float = 0.02) -> float:
    """Free vapour volume [m3]:  ``V_v = V_vessel - M_l / rho_l``.

    Process utility
    ---------------
    The vapour space is what the pressure state integrates over, and it shrinks as the
    vessel fills. Floored at a small fraction of the shell so that a momentarily over-full
    inventory gives a very stiff pressure response — which is physically what happens —
    rather than a division by zero.
    """
    if v_vessel_m3 <= 0.0 or rho_liquid_kgm3 <= 0.0:
        return max(v_vessel_m3, 1e-6)
    return max(v_vessel_m3 - m_liquid_kg / rho_liquid_kgm3, v_min_frac * v_vessel_m3)


def vessel_dpdt(p_bara: float, t_k: float, v_v_m3: float, mw_vap: float,
                n_gen_kmolh: float, n_out_kmolh: float,
                dtdt_k_s: float = 0.0, dvvdt_m3_s: float = 0.0) -> float:
    """Rate of change of a vapour-space pressure [bar/s].

        dP/dt = (R.T / V_v) . (n_gen - n_out)  +  (P/T) . dT/dt  -  (P/V_v) . dV_v/dt

    Process utility
    ---------------
    One equation for every gas-holding node in the plant, so a line node and a vessel node
    cannot drift apart in convention. Pass the generation and withdrawal rates in kmol/h;
    the factor ``1000/3600`` converts to mol/s and the ``1e-5`` converts Pa to bar.

    ``mw_vap`` is accepted for call-site symmetry and dimensional checking. The molar form
    does not use it — that is the point: the vapour's molecular weight has already been
    accounted for by the caller expressing its rates in kmol/h rather than kg/h, which is
    precisely the conversion the old lumped form skipped.

    A zero or negative vapour volume, or a non-physical temperature, returns 0.0 rather
    than raising: the pressure simply does not move, which is a safe answer for one tick
    and leaves the defect visible in the level or temperature that produced it.
    """
    if v_v_m3 <= 0.0 or t_k <= 0.0:
        return 0.0
    #  R.T/V_v . dn/dt :  kmol/h -> mol/s is (1000/3600);  J/m3 -> bar is 1e-5
    molar = (R_GAS_J * t_k / v_v_m3) * (n_gen_kmolh - n_out_kmolh) * (1000.0 / 3600.0) * 1.0e-5
    thermal = (p_bara / t_k) * dtdt_k_s
    swell = -(p_bara / v_v_m3) * dvvdt_m3_s
    return molar + thermal + swell


def backward_euler_pressure(p_old_bara: float, dt: float, dpdt: Callable[[float], float],
                            p_lo_bara: float, p_hi_bara: float) -> float:
    """One backward-Euler step of a vacuum node's pressure, P' = P + dt . f(P') [bar a].

    Process utility
    ---------------
    A vacuum separator whose condenser vents saturated gas: the vent grows steeply as the shell
    pressure falls (324F003's by 42 % for a 10 % drop), so dt . df/dP passes -1 and an explicit
    step, or a plain fixed point, rings and diverges. The implicit step stays on the physical
    branch at any step size.

    Method
    ------
    g(P) = P - P_old - dt . f(P) rises with P (the vent falls and the ejector's pull rises), so
    Newton from P_old, kept inside the bracket [p_lo, p_hi] that each residual's sign narrows,
    bisecting when a step would leave it. At a stationary state f(P_old) is a literal 0.0 and
    P_old comes back untouched — the design seed holds to the bit.

    Source: V1 `backend/main.py` `_backward_euler_p` (reports A-13, B-9, B-13). Ported verbatim.
    """
    g0 = -dt * dpdt(p_old_bara)
    if g0 == 0.0:
        return p_old_bara
    lo, hi = p_lo_bara, p_hi_bara
    p = p_old_bara
    g = g0
    for _ in range(BACKWARD_EULER_ITERS):
        if g > 0.0:
            hi = p
        elif g < 0.0:
            lo = p
        else:
            break
        h = BACKWARD_EULER_PROBE_BARA
        dg = ((p + h) - p_old_bara - dt * dpdt(p + h) - g) / h
        if dg > 0.0 and lo <= p - g / dg <= hi:
            step = g / dg
            p -= step
            if abs(step) <= BACKWARD_EULER_STEP_TOL_BARA:   # at the root to rounding
                break
        else:
            p = 0.5 * (lo + hi)
        g = p - p_old_bara - dt * dpdt(p)
    return min(max(p, p_lo_bara), p_hi_bara)


def stable_pressure_step(p_old_bara: float, dt: float, dpdt: Callable[[float], float],
                         p_floor_bara: float) -> tuple[float, bool]:
    """One step of a vapour-space pressure: V1's explicit step wherever it is monotone, the
    backward step where it would ring [bar a] (handoff B-51, decided 2026-10-09).

    Process utility
    ---------------
    A vessel filling towards its roof — 328C004 with its letdown shut — squeezes its head space
    toward nothing, and the pressure's sensitivity to its overhead flow grows as 1 / V_v. Past a
    point the explicit step jumps over the pressure the node is heading for and the overhead line
    alternates between shut and wide open every tick: a numerical limit cycle, swinging bar a
    peak to peak, that no plant does. This keeps V1's explicit step, to the bit, on every tick
    whose own linearised gain leaves it monotone, and takes the backward step only on the ticks
    where it is not.

    Method
    ------
        f0   = f(P)                                  the node's dP/dt this tick
        gain = dt . (f(P + h) - f0) / h              the explicit step's own linearised gain
        gain >= -1:  P' = P + f0 . dt                V1's step, bit for bit
        gain <  -1:  P' = P + dt . f(P')             `backward_euler_pressure`

    The backward step's bracket is the old pressure and the explicit one, floored: where the
    outflow rises with the pressure, the root lies between them. Returns the new pressure and
    True where the backward step was taken.
    """
    f0 = dpdt(p_old_bara)
    p_explicit = p_old_bara + f0 * dt
    h = BACKWARD_EULER_PROBE_BARA
    if dt * (dpdt(p_old_bara + h) - f0) / h >= EXPLICIT_STEP_LIMIT:
        return p_explicit, False
    lo = max(min(p_old_bara, p_explicit), p_floor_bara)
    hi = max(p_old_bara, p_explicit)
    return backward_euler_pressure(p_old_bara, dt, dpdt, lo, hi), True


# ======================================================================================
# Liquid space
# ======================================================================================

def advance_holdup_kg(m_prev_kg: float, inflow_kgh: float, outflow_kgh: float,
                      dt: float, m_min_kg: float = 1.0) -> float:
    """Advance a liquid inventory one step [kg]:  ``M_new = M + (m_in - m_out) . dt / 3600``.

    Process utility
    ---------------
    Explicit Euler on the vessel mass balance — the form V1 uses at every stage of the
    recirculation train, written out here once so the flooring convention is stated rather
    than repeated.

    **Why the floor is 1 kg and not 0.** A vessel's species balance divides by its
    inventory, and its specific heat rate multiplies it; at exactly zero both become
    singular and one tick of numerical noise turns into a NaN that propagates through the
    whole train. 1 kg against a 3000 kg design holdup is 0.03 % — far below anything an
    operator can see — but it keeps every downstream division finite. It is a numerical
    floor, NOT a process claim that the vessel cannot be emptied: emptying is represented
    by the level reaching zero and the trip acting on it, not by the inventory state
    reaching zero.

    Note that the caller decides what ``inflow`` means. For a transported line the OUTflow
    of the upstream vessel and the INflow of the downstream one are DIFFERENT numbers
    during a transient — the departed packet and the arrived packet — and the line
    inventory legitimately absorbs the difference. Collapsing them back into one flow is
    the teleporting-parcel defect `core.transport` exists to remove.
    """
    return max(m_prev_kg + (inflow_kgh - outflow_kgh) / 3600.0 * dt, m_min_kg)


def level_pct_from_holdup(m_liquid_kg: float, m_nll_kg: float, nll_pct: float) -> float:
    """Level indication [%] from inventory, ANCHORED on the vessel's normal liquid level.

        level_% = M / M_NLL * NLL_%,   limited to 0-100

    Process utility
    ---------------
    What the level transmitter reads. The anchor is the point the licensor specified — the
    design holdup and the per cent that holdup corresponds to on the tapping span — so at
    the design state the indication is the design per cent by construction, and the model
    supplies only the response away from it. That is Rule 1 of the As-Built reference
    applied to a level: the PFD number is preserved to the bit.

    Anchored rather than volumetric because the source data supports the anchor and does
    not support the alternative: `References/Datasheets` gives shell volumes and tapping
    elevations, but a head-versus-volume curve for a dished-end vessel with internals is
    not in it, and inventing one would be inventing plant geometry.

    Source: V1 `backend/main.py`, the 322E003 sump (`SCRUB_HOLDUP_NLL_KG`,
    `SCRUB_LEVEL_NLL_PCT`) and the 328C003 hydrolyser (`R328_C003_M_DES`, 50 %), which use
    this same form with their own anchors.
    """
    if m_nll_kg <= 0.0:
        return 0.0
    return clamp(m_liquid_kg / m_nll_kg * nll_pct, 0.0, 100.0)


# ======================================================================================
# Pressure-node network solve
# ======================================================================================

def solve_node_pressure(supply: Callable[[float], float],
                        branches: Sequence[Callable[[float], float]],
                        p_lo: float, p_hi: float, p_seed: float | None = None,
                        tol: float = 1.0e-10, max_iter: int = 80) -> float:
    """Node pressure at which a supply balances the sum of its branch draws [bar a].

    Process utility
    ---------------
    Where a machine discharges into two or more destinations there is no split FRACTION to
    assign. The branches meet at a node, the node has ONE pressure, and that pressure is
    whatever makes the supply's delivery equal the sum of what the branches can pass. A
    normalised conductance ratio forces the branch flows to sum to the supply by
    construction, which cannot represent a vent wide open while the loop also draws hard,
    and cannot let the node pressure fall below the destination pressure and shut a check
    valve on its own. This is V1 finding D-5, and it is what the 320K002 discharge needs.

    Equation
    --------
        residual(P) = supply(P) - sum_i branch_i(P) = 0

    Why bisection is the right solver here
    --------------------------------------
    ``supply`` is monotonically DECREASING in P — a compressor delivers less against more
    back pressure — and each branch is monotonically INCREASING, so the residual is strictly
    decreasing. A bracketed bisection on a strictly monotone residual is unconditionally
    convergent: no Jacobian, no initial-guess sensitivity, and no chance of landing on the
    wrong root. A Newton step would be faster and would occasionally find a root that is not
    the physical one, which in an operator trainer is the worse trade.

    The design seed
    ---------------
    ``p_seed`` is the design node pressure. When the residual there is EXACTLY zero the seed
    is returned unchanged, which is what keeps a design-anchored flowsheet bit-exact:
    bisection would otherwise return a value a few ulp away and unpin every constant
    downstream of it.

    The two bracket returns are physical answers, not failures. A residual that is already
    negative at ``p_lo`` means the supply cannot hold even the low end; a residual still
    positive at ``p_hi`` means it outruns every branch. Both are real plant states and both
    report the bracket they ran into.

    Source: V1 `backend/machines.py` solve_node_pressure.
    """
    def residual(p: float) -> float:
        return supply(p) - sum(b(p) for b in branches)

    if p_seed is not None:
        r_seed = residual(p_seed)
        if r_seed == 0.0:
            return p_seed

    lo, hi = p_lo, p_hi
    r_lo, r_hi = residual(lo), residual(hi)
    if r_lo <= 0.0:                     # the supply cannot even hold the low end
        return lo
    if r_hi >= 0.0:                     # the supply outruns every branch at the high end
        return hi
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        r = residual(mid)
        if r == 0.0 or (hi - lo) < tol:
            return mid
        if r > 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)
