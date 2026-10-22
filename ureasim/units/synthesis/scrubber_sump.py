"""322E003's sump — the condensate the scrubber makes, what 322F001 entrains, LT-329501.

What this models
----------------
The liquid inventory at the scrubber's foot (Option 3): the overflow the scrubber condenses runs
in, with the backlog PT-329201 recondensed on the tick before; the ejector's entrainment and the
forward-carbamate pulse run out; and the holdup integrates the difference,

    dM/dt = m_cond,in + m_recond - m_entrained - m_pulse,     L = M / M_NLL . L_NLL,

so an ejector stall floods the sump and a lost condensation drains it. Three more things ride on
the same tick:

  * **the mushy zone (L3-5)**: the line from the sump to 322F001 throttles as the overflow cools
    toward carbamate's 60 C solidus, f = clamp((T - 60) / 5, 0, 1), on the next tick's suction;
  * **the composition the ejector entrains next tick (report D-6)**: the overflow's mass fractions,
    left where they were if the overflow has gone dry;
  * **the liquor's bubble pressure (handoff B-91, decided 2026-10-14)**: the overflow's at
    TT-322002 (`scrubber.liquor_bubble_p_bara`), which sets the scrubber's saturation on the next
    tick, left where it was if the overflow has gone dry;
  * **LT-329501's reading**, which is not the level: the swell and hunt of a boiling column scaled
    by the condensation deficit (`scrubber.lt_329501_indication`).

A sump that has emptied gives the ejector at most what runs in. Its holdup is held between empty
and full; what the full sump cannot hold is held back in the scrubber above it and runs down as
the sump makes room — a flooding sump already chokes the scrubber's condensation through its level.

322E003 also owns its wash's inlet line, PFD 308 from 323P001 (decided 2026-10-22, handoff B-110):
the flow arrives at once, the liquor's composition and temperature a line residence late
(`wash_arrival`, B-21's class, on the line's isometrics).

Decided by the process engineer on 2026-10-03 (handoff B-76, B-78 items 1 to 3): V1 deletes what
recondenses from the loop's backlog, the full sump's excess and what the mushy zone holds back of
the overflow, and draws the forward-carbamate pulse from nowhere. Here each reaches an inventory.

Source: V1 ``backend/main.py`` ``step_sim`` 8113-8160; `data.unit_322e003`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ureasim.core.numeric import clamp
from ureasim.core.stream import MW_COMP
from ureasim.data.unit_322e003 import (
    HOLDUP_MAX_KG,
    HOLDUP_NLL_KG,
    LEVEL_NLL_PCT,
    OVERFLOW_P_DES_BARA,
    OVERFLOW_T_CRYST_C,
)
from ureasim.data.unit_322f001 import CARBAMATE_FRAC
from ureasim.data.unit_323e003 import E003_T_C, W_308
from ureasim.thermo.empirical import urea_soln_cp
from ureasim.units.consequence.crystallisation import mushy_flow_factor
from ureasim.units.recirc.liquor_line import receive_liquor
from ureasim.units.synthesis.scrubber import (
    liquor_bubble_p_bara,
    lt_329501_indication,
    lt_329501_noise,
    lt_329501_swell,
)

__all__ = ["WASH_ROUTE", "WASH_CP_DES", "ScrubberSumpResult", "ScrubberSump"]

#: PFD 308's line from 323P001 to 322E003/N5 (`data.process_routes`), and the wash's design
#: specific heat [kJ/(kg K)], the anchor its packet's cp departs from (`liquor_line.stream_cp`).
WASH_ROUTE = "323P001_TO_322E003"
WASH_CP_DES = urea_soln_cp(W_308["Urea"], E003_T_C)


@dataclass(frozen=True)
class ScrubberSumpResult:
    """One tick of the sump [kg/h, kmol/h, %]."""

    #: The scrubber's overflow into the sump [kmol/h] and its mass [kg/h]; the backlog that
    #: recondensed into it [kg/h] (B-76) and the pulse drawn to 322R001 [kg/h] (B-78, item 2).
    overflow_kmolh: dict
    m_cond_in_kgh: float
    recond_kgh: float
    pulse_kgh: float
    #: The mushy-zone factor the next tick's suction runs on [-], and whether it binds.
    mushy_factor: float
    solidification: bool
    #: What the ejector entrained, at most what runs in once the sump is empty [kg/h].
    suction_kgh: float
    #: The holdup [kg], its level and LT-329501's reading [%].
    holdup_kg: float
    level_pct: float
    lt_329501_pct: float
    #: The swell and the hunt the indication carries [% of span], V1's published diagnostics.
    lt_329501_swell_pct: float
    lt_329501_noise_pct: float
    #: The condensate held back in the scrubber above the full sump [kg] (B-78, item 1).
    held_kg: float
    #: What the sump and the scrubber's held-back liquid gained this tick [kg/h] (B-77 (b)).
    dm_kgh: float = 0.0
    #: The liquor's bubble pressure, which the scrubber's saturation reads next tick [bar a] (B-91).
    p_bub_bara: float = OVERFLOW_P_DES_BARA


@dataclass
class ScrubberSump:
    """The sump's states, seeded at its NLL on the design composition (V1 ``State``)."""

    holdup_kg: float = HOLDUP_NLL_KG
    level_pct: float = LEVEL_NLL_PCT
    #: The overflow's mass fractions, which 322F001 entrains on the next tick.
    y_overflow: dict = field(default_factory=lambda: dict(CARBAMATE_FRAC))
    #: The condensate held back in the scrubber above a full sump [kg] (B-78, item 1).
    held_kg: float = 0.0
    #: The mushy-zone factor of the last overflow [-], which throttles 322F001's suction on the
    #: next tick (B-78, item 3).
    mushy_factor: float = 1.0
    #: The last overflow's bubble pressure [bar a], the scrubber's saturation next tick (B-91).
    p_bub_bara: float = OVERFLOW_P_DES_BARA
    #: 322E003's capacity on its shell's effectiveness and its duty capped at it (decided
    #: 2026-10-17, handoff B-99 (b1)); False is V1's linear flow law, which the harness keeps.
    effectiveness_capacity: bool = True
    #: PFD 308's line from 323P001, the inlet 322E003 owns (decided 2026-10-22, handoff B-110),
    #: and its state; False is the wash a tick late with no transit, which the harnesses keep.
    wash_line: bool = True
    line_state: dict = field(default_factory=dict)

    def wash_arrival(self, m_308_kgh: float, t_308_c: float, w_308: dict,
                     dt: float) -> tuple[float, dict]:
        """PFD 308 as it reaches 322E003/N5: its temperature [deg C] and mass fractions [-].

        Process utility
        ---------------
        The weak carbamate 323P001 pumps up to the scrubber's wash is the liquor 323D001 held a line
        residence ago: 48 m of high-pressure pipe, about 25 s at the design 36.8 t/h, longer as
        the pump slows. Its flow reaches the scrubber at once, a liquid-full line (B-21's class);
        a change in 323D001's water or temperature reaches the wash and the reactor's feed only
        after the line has turned over. A settled line hands back what departed, to the bit.

        Source: handoff B-110 (decision 74's and B-21's classes), the line on its isometrics
        (`data.process_routes`, ``323P001_TO_322E003``).
        """
        if not self.wash_line:
            return t_308_c, w_308
        arrived = receive_liquor(self.line_state, WASH_ROUTE, m_308_kgh, t_308_c, dict(w_308),
                                 WASH_CP_DES, dt)
        return arrived.t_c, arrived.w

    def step(self, overflow_kmolh: dict, t_overflow_c: float, suction_kgh: float,
             cool_frac: float, sim_t_s: float, dt: float, recond_kgh: float = 0.0,
             pulse_kgh: float = 0.0) -> ScrubberSumpResult:
        """Advance the sump on this tick's scrubber overflow, the backlog PT-329201 recondensed on
        the tick before (``recond_kgh``, B-76), the ejector's entrainment and the forward-carbamate
        pulse 322R001 drew this tick (``pulse_kgh``, B-78 item 2)."""
        # The mushy zone throttles the line to 322F001, not the overflow: what it holds back stays
        # in the sump (B-78, item 3).
        self.mushy_factor = f_ovf = mushy_flow_factor(t_overflow_c, OVERFLOW_T_CRYST_C)
        overflow = dict(overflow_kmolh)
        m_cond_in = sum(overflow[k] * MW_COMP[k] for k in overflow)
        if m_cond_in > 1.0:
            self.y_overflow = {k: overflow.get(k, 0.0) * MW_COMP[k] / m_cond_in
                               for k in MW_COMP}
            self.p_bub_bara = liquor_bubble_p_bara(overflow, t_overflow_c)
        # The backlog recondenses at the overflow's composition (B-76).
        m_in = m_cond_in + recond_kgh
        if self.level_pct <= 0.0 and suction_kgh > m_in:
            suction_kgh = max(m_in, 0.0)
        # What the scrubber held back runs down first; what the full sump cannot take stays held.
        m_0 = self.holdup_kg + self.held_kg
        m = self.holdup_kg + self.held_kg + (m_in - suction_kgh - pulse_kgh) * (dt / 3600.0)
        self.held_kg = max(m - HOLDUP_MAX_KG, 0.0)
        self.holdup_kg = clamp(m, 0.0, HOLDUP_MAX_KG)
        self.level_pct = clamp(self.holdup_kg / HOLDUP_NLL_KG * LEVEL_NLL_PCT, 0.0, 100.0)
        return ScrubberSumpResult(
            overflow_kmolh=overflow, m_cond_in_kgh=m_cond_in, recond_kgh=recond_kgh,
            pulse_kgh=pulse_kgh, mushy_factor=f_ovf, solidification=bool(f_ovf < 1.0),
            suction_kgh=suction_kgh, holdup_kg=self.holdup_kg, level_pct=self.level_pct,
            lt_329501_pct=lt_329501_indication(self.level_pct, cool_frac, sim_t_s),
            lt_329501_swell_pct=lt_329501_swell(cool_frac),
            lt_329501_noise_pct=lt_329501_noise(cool_frac, sim_t_s), held_kg=self.held_kg,
            dm_kgh=(self.holdup_kg + self.held_kg - m_0) * (3600.0 / dt),
            p_bub_bara=self.p_bub_bara)
