"""How a calibrated phase split is allowed to move.

What this module is
-------------------
Every separation in this plant that the licensor calibrated arrives as a FROZEN vector: the
fraction of each species that left overhead at one operating point. Frozen, such a vector has
a derivative of exactly zero. An operator could raise the loop pressure ten bar, open the
stripping steam, or let the inerts build, and not one mole would move between the phases —
which is the wrong answer for the variables a trainee has most authority over.

These three functions are how those vectors move. Each takes the calibrated split and a
measure of how far the live state has travelled from the state it was calibrated at, and each
returns the moved split. None of them ever uses an ABSOLUTE number out of the property model,
because in the HP synthesis loop the Extended UNIQUAC parameter set is extrapolated and the
absolute numbers there are not usable. What survives extrapolation is the derivative, so a
ratio of the model to itself is all any of them takes.

    ratio_shift_frac      the phase ratio is FIXED by something else (a column, an absorber)
    anchored_split        the phase ratio is FREE and must be re-solved (a flash, a reactor top)
    saturated_inert_vent  the gas rate is FIXED by the non-condensables (a wash top, a vacuum
                          condenser vent)

Which one a unit uses is a statement about the equipment, not a modelling preference, and
picking the wrong one invents physics. A stripping column has no vapour fraction to solve for;
a condenser cannot be given one arbitrarily; and a vent over an inert purge is neither.

Every one of the three returns its input to the last bit when the live state IS the calibration
state — by the arithmetic, not by a short-circuit and not within a tolerance. That is what lets
the published design point be reproduced exactly by a model that is nevertheless live.

Ported from V1 `backend/main.py`: `_ratio_shift_frac`, `_anchored_split` (the G-VLE-3 block)
and `scrub_vent_kmolh` (report A-2).
"""

from __future__ import annotations

#: Bisection sweeps for the anchored Rachford-Rice split. The bracket is [0, 1], so 60
#: halvings resolve the phase ratio to 2^-60 — below the last bit of a double over that
#: range. Fixed, never convergence-tested: an OTS tick has a deadline.
ANCHORED_SPLIT_ITERS = 60


def ratio_shift_frac(theta: float, r: float) -> float:
    """Move a split fraction by a K-value ratio at a FIXED phase ratio.

    Process utility
    ---------------
    A stripping column and an absorber are not flashes: nothing fixes their vapour fraction,
    so inventing one in order to move a calibrated split would be inventing physics. This is
    what is used instead. It takes the licensor's measured split fraction for one species and
    moves it by that species' K-value ratio, leaving the phase ratio wherever the calibration
    put it.

    Equation
    --------
    Back-solve K from the calibrated split at an unknown phase ratio psi,

        theta = K.psi / (1 + psi(K - 1))

    re-insert ``K.r``, and the ``(1 - psi)`` factors cancel and psi drops out entirely:

        theta' = r.theta / (1 + (r - 1).theta)

    Two properties matter and both are structural rather than clamped. It maps [0, 1] onto
    [0, 1] for any r > 0, so it can never ask a column to strip more of a species than it was
    fed — which a bare ``theta * r`` multiply can and does. And at ``r == 1.0`` the term
    ``(r - 1.0)`` is exactly 0.0, so it returns ``theta`` to the last bit by the arithmetic,
    not by a short-circuit.

    A split of exactly 0 or exactly 1 is a NON-DISTRIBUTING species — urea does not leave
    overhead and an inert does not stay down — and is returned unchanged. That is a structural
    statement about the component, not a limiter on the correlation.
    """
    if theta <= 0.0 or theta >= 1.0 or r <= 0.0:
        return theta
    return r * theta / (1.0 + (r - 1.0) * theta)


def anchored_split(frac_des: dict, feed_kmolh: dict, ratio: dict,
                   iters: int = ANCHORED_SPLIT_ITERS) -> dict:
    """Move a calibrated component split by K-value ratios, RE-SOLVING the phase ratio.

    Process utility
    ---------------
    The other half of the pair `ratio_shift_frac` opens. Where the unit genuinely IS a flash
    — a condenser, or the vapour disengaging off the top of a reactor — the phase ratio is
    not free: every species competes for the same vapour, so moving one split has to move the
    others. This solves that competition, where `ratio_shift_frac` deliberately refuses to.

    What it is for on the plant is that a frozen split vector has a derivative of exactly
    zero. Raise the loop pressure on a reactor top and, with a frozen vector, not one mole
    moves from the off-gas into the melt — which is the wrong answer for the one variable an
    operator has most authority over.

    Equation
    --------
    Back-solve the design K-values from the calibrated split against the LIVE feed, so the
    activity coefficients of this strongly non-ideal melt stay baked into them exactly as
    measured, and only the DEVIATION is model-driven:

        psi_des = sum_i z_i . theta_des,i
        K_des,i = theta_des,i (1 - psi_des) / ( psi_des (1 - theta_des,i) )
        K_i     = K_des,i . r_i

    then re-solve Rachford-Rice for the phase ratio and read the splits back off it:

        g(psi)   = sum_i z_i (K_i - 1) / (1 + psi (K_i - 1))  = 0
        theta_i  = K_i psi / (1 + psi (K_i - 1))

    Why bisection and not Newton
    -----------------------------
    g(psi) is strictly decreasing on [0, 1], so a fixed sweep count is exact to 2^-iters at
    bounded cost with no possible convergence failure. A simulator tick must never miss its
    deadline, which is the same argument that keeps the flowsheet sequential-modular.

    Non-distributing species
    ------------------------
    A calibrated split of exactly 0 or exactly 1 is structural — urea does not leave overhead
    and an inert does not dissolve — so those species stay out of the flash entirely and are
    returned unchanged. That is why a reactor modelled this way never dissolves its own
    nitrogen: it falls out of the arithmetic, not out of an exception list.

    Degenerate inputs
    -----------------
    Two guards, and neither is an identity short-circuit: with no distributing feed, or with a
    feed the calibration already puts entirely in one phase, there is no flash to solve and
    the design vector IS the answer. Both protect a division on the following line.

    At ``r == 1.0`` every K is multiplied by exactly 1.0 and the solve returns the calibrated
    vector to the last bit.

    Source: V1 `backend/main.py` `_anchored_split`, the G-VLE-3 block.
    """
    dist = [k for k in frac_des if 0.0 < frac_des.get(k, 0.0) < 1.0]
    f_d = sum(feed_kmolh.get(k, 0.0) for k in dist)
    if f_d <= 1e-12:
        return dict(frac_des)
    z = {k: feed_kmolh.get(k, 0.0) / f_d for k in dist}
    psi_des = sum(z[k] * frac_des[k] for k in dist)
    if not (1e-9 < psi_des < 1.0 - 1e-9):
        return dict(frac_des)
    k_live = {}
    for k in dist:
        phi_d = frac_des[k]
        k_des = phi_d * (1.0 - psi_des) / (psi_des * (1.0 - phi_d))
        k_live[k] = max(k_des * max(ratio.get(k, 1.0), 0.0), 0.0)

    def residual(psi: float) -> float:
        """Rachford-Rice residual; strictly decreasing in psi."""
        return sum(z[k] * (k_live[k] - 1.0) / (1.0 + psi * (k_live[k] - 1.0)) for k in dist)

    lo, hi = 1e-12, 1.0 - 1e-12
    if residual(hi) >= 0.0:
        psi = hi                       # above the dew point: everything leaves as gas
    elif residual(lo) <= 0.0:
        psi = lo                       # below the bubble point: everything condenses
    else:
        for _ in range(iters):
            mid = 0.5 * (lo + hi)
            if residual(mid) > 0.0:
                lo = mid
            else:
                hi = mid
        psi = 0.5 * (lo + hi)
    out = dict(frac_des)
    for k in dist:
        # `max(lo, min(hi, x))` written out: this layer sits below `core.numeric`,
        # and the form is the engine limiter's, so a NaN resolves to the upper rail
        # exactly as it does everywhere else in the flowsheet.
        out[k] = max(0.0, min(1.0, k_live[k] * psi / (1.0 + psi * (k_live[k] - 1.0))))
    return out


def saturated_inert_vent(feed_kmolh: dict, inerts, condensables, y_des: dict,
                         y_max: float, ratio: dict = None) -> dict:
    """Vent off a two-phase contactor whose gas rate is fixed by its non-condensables.

    Process utility
    ---------------
    The third member of the family `ratio_shift_frac` and `anchored_split` belong to, and the
    one that applies when the vapour leaving a vessel is not a flash at all.

    At the cold top of a wash column, or over a vacuum condenser, the gas that leaves is
    **not** whatever a phase ratio decides. Every mole of nitrogen, oxygen, methane and
    hydrogen that entered has to leave, because nothing absorbs or condenses it, and that
    inert stream carries with it the condensables' equilibrium vapour at the top temperature
    and pressure. So the inerts set the gas RATE and the saturation sets its COMPOSITION —
    which is why an inert-rich feed loses more ammonia overhead than an inert-lean one at the
    same duty, and why letting inerts build in a loop is expensive rather than merely untidy.

    Equation
    --------
    With ``y_c`` the condensables' saturated mole fractions and ``n_inert`` the total
    non-condensable feed, the vent is the inert flow scaled up by the room the condensables
    occupy in it::

        n_inert = sum_j feed_j                     j over the inerts
        y_c     = y_des,c . r_c                    the design saturation, moved by a K ratio
        vent_j  = feed_j                           every inert leaves
        vent_c  = n_inert . y_c / (1 - sum_c y_c)

    which is the simplified Colburn-Hougen closure for condensation in the presence of a
    non-condensable: the ``1/(1 - sum y_c)`` factor is the inert-basis conversion, and it is
    what makes the ammonia loss rise faster than linearly as the top warms.

    The two limits, and why each one is structural
    -----------------------------------------------
    * **``y_max``.** As ``sum y_c`` approaches 1 the inert-basis factor diverges: the closure
      is asserting a gas with no inerts in it, which is a condition this relation does not
      describe rather than a very large vent. The saturation vector is scaled back to
      ``y_max`` when it would exceed it, so the factor stays bounded.
    * **The feed cap.** A condensable cannot leave faster than it arrives. An inert-rich,
      ammonia-starved feed vents the ammonia it has and no more, so each condensable is
      capped at its own feed.

    Neither is a tuning limiter and neither binds at a normal operating point.

    At ``ratio`` of exactly 1.0 — or omitted — each ``y_des`` is multiplied by a literal 1.0,
    so a design call and a live call at the design state are the same arithmetic and return
    the same float.

    Parameters
    ----------
    feed_kmolh   combined feed to the contactor [kmol/h].
    inerts       the non-condensable species, in the order their total is summed.
    condensables the absorbable/condensable species, in the order ``sum y_c`` is summed.
    y_des        design saturated mole fraction of each condensable [-].
    y_max        cap on ``sum y_c`` [-]; the caller owns this number and its source.
    ratio        per-species K-value ratio against the design state; None is the design K.

    Returns the vent over the inerts and condensables only [kmol/h]; a species in neither
    list is not in the vent at all, which is the statement that it is non-volatile.

    Source: V1 `backend/main.py` `scrub_vent_kmolh`, report A-2.
    """
    r = ratio or {}
    n_inert = sum(max(feed_kmolh.get(k, 0.0), 0.0) for k in inerts)
    y = {k: y_des[k] * r.get(k, 1.0) for k in condensables}
    y_sum = sum(y.values())
    if y_sum > y_max:
        # Scaled, not truncated: the RELATIVE saturation the calibration measured between the
        # condensables is preserved, and only the inert-basis divergence is removed.
        y = {k: v * y_max / y_sum for k, v in y.items()}
        y_sum = y_max
    vent = {}
    for k in inerts:
        vent[k] = max(feed_kmolh.get(k, 0.0), 0.0)
    for k in condensables:
        vent[k] = min(n_inert * y[k] / (1.0 - y_sum), max(feed_kmolh.get(k, 0.0), 0.0))
    return vent


__all__ = ["ratio_shift_frac", "anchored_split", "ANCHORED_SPLIT_ITERS",
           "saturated_inert_vent"]
