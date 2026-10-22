"""322E003's sump level, and what LT-329501 reads of it.

What this module models
-----------------------
The sump inventory the engine integrates, read as a level, and the indication of LT-329501, the DP
cell on the sump: the level itself while the shell condenses in full, and above it, hunting, when
the shell stops condensing and the sump froths. The two-phase swell and the froth's hunt both scale
with the condensation deficit and are zero at design.

Equations
---------
    level     = clamp(M / M_NLL . L_NLL, 0, 100)
    swell     = S_max . (1 - c)
    hunt      = N . (1 - c) . [sin(2 pi t / T1) + 0.6 sin(2 pi t / T2)] / 1.6
    LT-329501 = clamp(level + swell + hunt, 0, 100)

Moved out of `scrubber` unchanged (2026-10-23, the housekeeping split); `scrubber` re-exports every
name.

Source: V1 `backend/main.py` `step_sim`, the 322E003 inventory block and the LT-329501 swell
overlay (``scrub_swell_pct``, ``scrub_swell_noise``).
"""

from __future__ import annotations

import math

from ureasim.core.numeric import clamp
from ureasim.data.unit_322e003 import (
    HOLDUP_NLL_KG,
    LEVEL_NLL_PCT,
    SWELL_NOISE_PCT,
    SWELL_NOISE_T1_S,
    SWELL_NOISE_T2_S,
    SWELL_PCT_MAX,
)


def sump_level_pct(holdup_kg: float) -> float:
    """True sump inventory as a level [%], from the holdup the engine integrates.

    Process utility
    ---------------
    The level the physics reads — the condensation choke above and the ejector's suction
    head both key off this, not off the transmitter. Linear in holdup, because the sump is
    a constant cross-section, and scaled so the design inventory reads normal level exactly.

    Source: V1 `main.py` `step_sim`, the 322E003 inventory block.
    """
    return clamp(holdup_kg / HOLDUP_NLL_KG * LEVEL_NLL_PCT, 0.0, 100.0)


def lt_329501_indication(level_pct: float, cool_frac: float, sim_t_s: float) -> float:
    """What the LT-329501 transmitter READS [%], which is not the level.

    Process utility
    ---------------
    This is an operator trap and it is modelled deliberately. LT-329501 is a differential-
    pressure cell: it reads the hydrostatic head of the column between its taps, not the
    mass in the vessel. Stop condensing and the sump boils; the mixture density collapses
    with the void fraction and the column swells upward to hold the same mass. Over a fast
    transient the swell beats the density loss, so **the cell reads HIGH while the vessel is
    actually draining** — the drain to 322F001 keeps pulling after the condensate make has
    stopped.

    And it hunts as well as reading high: a DP cell straddling a frothing column sees the
    head fluctuate as slugs and bubbles cross its taps. Two incommensurate periods off the
    simulation clock, not a random number, so an instructor replays the same excursion the
    same way every time.

    Both terms scale with the condensation deficit, so at design they are identically zero
    and the indication IS the level, bit-exact.

    Source: V1 `main.py` `step_sim`, the LT-329501 swell overlay.
    """
    return clamp(level_pct + lt_329501_swell(cool_frac) + lt_329501_noise(cool_frac, sim_t_s),
                 0.0, 100.0)


def lt_329501_swell(cool_frac: float) -> float:
    """The two-phase swell LT-329501's indication carries [% of span], zero while the shell
    condenses in full. V1 publishes it beside the indication. Source: V1 `main.py`
    ``scrub_swell_pct``."""
    return SWELL_PCT_MAX * (1.0 - cool_frac)


def lt_329501_noise(cool_frac: float, sim_t_s: float) -> float:
    """The froth's hunt on LT-329501's head [+/- % of span], off the plant clock. V1 publishes it
    beside the indication. Source: V1 `main.py` ``scrub_swell_noise``."""
    return SWELL_NOISE_PCT * (1.0 - cool_frac) * (
        math.sin(2.0 * math.pi * sim_t_s / SWELL_NOISE_T1_S)
        + 0.6 * math.sin(2.0 * math.pi * sim_t_s / SWELL_NOISE_T2_S)) / 1.6

__all__ = ["sump_level_pct", "lt_329501_indication", "lt_329501_swell", "lt_329501_noise"]
