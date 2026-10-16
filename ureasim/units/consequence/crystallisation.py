"""The mushy-zone flow restriction, as a urea- or carbamate-bearing line cools.

What this models
----------------
A urea melt and an ammonium-carbamate liquor both salt out as they cool, and neither of them
does it at a point. Between the temperature at which the first crystals appear and the
temperature at which the stream is a solid there is a mushy zone: a slurry whose apparent
viscosity climbs until the line no longer flows. Every urea-bearing line in this plant sits
above that boundary by design, and the ones with the least margin — the stripper bottoms, the
322E003 scrubber overflow, the Stage-2 melt — are the ones that plug on a real plant.

Why this is a flow FACTOR and not a trip
-----------------------------------------
Because plugging is progressive and recoverable, and a trainee has to be able to see it
happening and reverse it. A restriction that ramps from 1.0 to 0.0 across the mushy zone
leaves the un-drained mass in the vessel's own level ODE, so the level rises while the drain
falls — which is the signature an operator actually gets, several minutes before anything
stops moving. A threshold would give them a working line and then a dead one.

Source
------
Ported from V1 `backend/main.py` `_f_flow`.

What is deliberately NOT ported
--------------------------------
V1's `backend/consequence.py` carries a generalised variant, `mushy_flow_factor`, with a
metastable-zone offset and a full urea / carbamate solubility curve behind it, so that the
boundary temperature could be computed from a liquor's composition instead of being passed
in. Nothing in V1 ever calls it: all three live call sites use `_f_flow` with a literal
boundary. Porting the unreachable variant would bring a solubility curve into the rewrite
that no equation depends on, which §6 of the agent directives forbids, so only the reachable
relation is here. The composition-dependent boundary belongs with the first unit that needs
one, and the difference is recorded in `handoff.md`.
"""

from __future__ import annotations

from ureasim.core.numeric import clamp

#: Width of the mushy zone above the solidus [deg C]. Flow is fully established at
#: ``T_cryst + MUSHY_BAND_DEFAULT_C`` and has stopped at ``T_cryst``.
#: Source: V1 `backend/main.py` `_f_flow` default argument.
MUSHY_BAND_DEFAULT_C = 5.0


def mushy_flow_factor(t_c: float, t_cryst_c: float,
                      dt_mush: float = MUSHY_BAND_DEFAULT_C) -> float:
    """Flow factor across the mushy zone [-]: 1.0 fully molten, 0.0 at the solidus.

    Process utility
    ---------------
    Multiplies whatever flow the line would otherwise pass. On the stripper bottoms it
    throttles the LV-322501 letdown as TT-322004 falls toward the 132.7 deg C urea melting
    point; on the 322E003 overflow it throttles the scrubber drain as the carbamate approaches
    60 deg C. In both cases the mass that does not leave stays in the vessel inventory, so the
    level climbs — and that, not the flow itself, is what the operator sees first.

    Equation
    --------
        f = clamp( (T - T_cryst) / dT_mush , 0, 1 )

    Linear across the band. The real apparent-viscosity curve is steeper than linear near the
    solidus, but a linear ramp is the conservative training behaviour: the trainee gets a
    visible, recoverable warning band rather than a cliff.

    Anchoring
    ---------
    Exactly 1.0 at every design state in this flowsheet, since every stream runs well above
    its own boundary, so the relation contributes nothing at the design point.

    A non-finite temperature returns 1.0, because this uses the engine limiter rather than
    the consequence-layer one; see `core.numeric.clamp`. That is V1's behaviour at these call
    sites and it is ported unchanged, but it is worth stating plainly: a NaN bottoms
    temperature reports an unrestricted drain.
    """
    return clamp((t_c - t_cryst_c) / dt_mush, 0.0, 1.0)


__all__ = ["MUSHY_BAND_DEFAULT_C", "mushy_flow_factor"]
