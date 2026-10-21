"""322E002 stepped — its film, its outlet temperature's tear and LT-322E002's liquid inventory.

What this models
----------------
The carbamate condenser as the loop steps it each tick, around the pure condenser model
(`carbamate_condenser.carbamate_condenser_322e002`):

  * the shell boils 322D001A/B's water at the drums' saturation, so its temperature is the LP
    steam's, read from the network as it stood on the tick before;
  * the (T, P) flash that moves the split needs the outlet temperature it also produces, and the
    loop pressure, so both enter from the tick before (AUDIT F-6 / TD-007), and the film's split
    relaxes from where the last tick left it;
  * LT-322E002, a gravity-drained sump: the liquid make in, the ejector's forward circulation out
    in proportion to the level, so the level settles at L_eq = NLL . phi_in / phi_fwd instead of
    winding to a rail (ISSUE-c/e),

        dL/dt = (phi_in - phi_fwd . L / L_NLL) . 100 / tau_fill,   phi_in = m_liq / m_liq,des.

The bubble pressure is anchored on the design melt's N/C and the make on the seed's liquid make,
both from the boot pin; at the seed the level is stationary at its NLL to the bit.

The melt's saturation (handoff B-91 (a), decided 2026-10-10): PI-322E002 against PT-329201 of the
tick before sets the fraction of the condensing volatiles the melt can hold
(`liquor_saturation.saturation_fraction`), which this tick's split takes and 322E003 and PT-329201's
buffering read.

The fraction solved on the tick (decided 2026-10-17, handoff A-21 (b); decision 78's class on
decision 97). The melt's bubble pressure moves with what it condenses — condensing more heats it
and raises its bubble pressure — so the fraction and PI-322E002 are one algebraic loop. Read across
the tick (V1's tear) it rings with a period of two ticks on a step in the stripper's top gas, all
condensed then nothing, and locks the condensation off. Wherever the melt the tick-before fraction
lets condense would move the fraction, it is solved with its own melt's bubble pressure:

    f = f( P_bub(f), PT-329201 ),   h(f) = f(P_bub(f)) - f = 0 on [0, 1]

h falls monotonically in f, so the root is unique: f = 1 where condensing everything leaves the melt
within its head of the loop, 0 where condensing nothing does not, else the bracketed root
(`core.numeric.bracketed_root`). Where the fraction already stands at its fixed point — 1 at the
design, or a settled fraction below it — the tick is the tear's to the bit. (The seed's own drift
moves the tear's fraction to 0.99998 in its first ticks; solved, it stays at 1.)
``CondenserHoldup(implicit_saturation=False)`` keeps the tick-late tear, which the synthesis
harness runs.

A tube leak (`tube_leak`, handoff B-82, decided 2026-10-09) takes its share of the product before
322R001 and the sump read it; the instructor sets its rate at the design differential
(``leak_severity_kgh``), zero by default, where every flow is the condenser's to the bit.

Source: V1 ``backend/main.py`` ``step_sim`` 7695-7705 and 7970-7987; `data.synthesis_pin`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ureasim.core.numeric import bracketed_root, clamp
from ureasim.data.synthesis_pin import HPCC_LIQ_DES_LIVE_KGH, HPCC_NC_DES_LIVE
from ureasim.data.unit_322e002 import (
    FRAC_GAS_DES,
    LEVEL_NLL_PCT,
    P_DES_BARA,
    T_PROD_DES_C,
    TAU_FILL_MIN,
)
from ureasim.data.unit_329 import P_LP_BARA
from ureasim.units.synthesis.carbamate_condenser import (
    CondenserResult,
    carbamate_condenser_322e002,
)
from ureasim.units.synthesis.liquor_saturation import saturation_fraction
from ureasim.units.synthesis.tube_leak import NO_LEAK, TubeLeakResult, tube_leak

__all__ = ["CondenserStepResult", "CondenserHoldup", "SATURATION_TOL"]


@dataclass(frozen=True)
class CondenserStepResult:
    """One tick of 322E002: the condenser's result as 322R001 receives it, LT-322E002 [%] and the
    tube leak."""

    condenser: CondenserResult
    level_pct: float
    leak: TubeLeakResult = NO_LEAK
    #: What LT-322E002's holdup gained this tick [kg/h] (B-77 (b)).
    dm_kgh: float = 0.0
    #: The melt's saturation fraction this tick took [-] (B-91 (a)).
    sat_frac: float = 1.0


#: The saturation fraction's tolerance in its on-tick solution [-]: a numerical bound, a tenth of a
#: part per billion of the condensing volatiles.
SATURATION_TOL = 1e-10

#: LT-322E002's holdup over its span [kg]: the level law integrates the condenser's liquor over
#: TAU_FILL_MIN of the design make, so 100 % is that mass.
E002_SPAN_KG = HPCC_LIQ_DES_LIVE_KGH * TAU_FILL_MIN / 60.0


@dataclass
class CondenserHoldup:
    """322E002's states, seeded on the design (V1 ``State``)."""

    #: TT-322010 of the tick before [deg C], the flash's tear.
    t_prod_prev_c: float = T_PROD_DES_C
    #: The film's gas split of the tick before [-, by species].
    phi: dict = field(default_factory=lambda: dict(FRAC_GAS_DES))
    #: LT-322E002 [% of the sump's span].
    level_pct: float = LEVEL_NLL_PCT
    #: The instructor's tube leak, its rate at the design differential [kg/h] (handoff B-82).
    leak_severity_kgh: float = 0.0
    #: PI-322E002 of the tick before [bar a], the melt's bubble pressure its saturation reads.
    p_bub_prev_bara: float = P_DES_BARA
    #: The saturation fraction solved with its own melt's bubble pressure on the tick (decided
    #: 2026-10-17, handoff A-21); False is the tick-late tear the synthesis harness keeps.
    implicit_saturation: bool = True

    def step(self, top_kmolh: dict, t_top_c: float, ej_comp_kgh: dict, ej_t_c: float,
             t_shell_c: float, p_syn_bara: float, phi_fwd: float,
             dt: float, p_shell_bara: float = P_LP_BARA) -> CondenserStepResult:
        """Advance the condenser one tick.

        ``top_kmolh`` / ``t_top_c`` are this tick's 322E001 top gas and TT-322013, ``ej_comp_kgh`` /
        ``ej_t_c`` 322F001's discharge and TT-322012, ``t_shell_c`` 322D001A/B's saturation of the
        tick before, ``p_syn_bara`` PT-329201 of the tick before, ``phi_fwd`` the ejector's
        forward-circulation fraction (unit 321's phi_m squared), ``p_shell_bara`` 322D001A/B's
        steam space of the tick before, the leak's downstream.
        """
        memo: dict = {}

        def condense(f: float) -> CondenserResult:
            """The condenser on this tick's feeds at the saturation fraction ``f``."""
            if f not in memo:
                memo[f] = carbamate_condenser_322e002(
                    top_kmolh, t_top_c, ej_comp_kgh, ej_t_c, t_shell_c=t_shell_c, gate=1.0,
                    t_prod_prev_c=self.t_prod_prev_c, p_loop_bara=p_syn_bara, phi_prev=self.phi,
                    dt=dt, nc_anchor=HPCC_NC_DES_LIVE, sat_frac=f)
            return memo[f]

        sat = saturation_fraction(self.p_bub_prev_bara, p_syn_bara)
        hpcc = condense(sat)
        # Solved where the melt this fraction makes would move it: at its fixed point the tick is
        # the tear's to the bit.
        if (self.implicit_saturation
                and abs(saturation_fraction(hpcc.p_bub_bara, p_syn_bara) - sat) > SATURATION_TOL):
            sat = self._solved_fraction(condense, p_syn_bara)
            hpcc = condense(sat)
        self.t_prod_prev_c = hpcc.t_prod
        self.phi = dict(hpcc.phi_film)
        self.p_bub_prev_bara = hpcc.p_bub_bara
        leak, hpcc = tube_leak(self.leak_severity_kgh, p_syn_bara, p_shell_bara, hpcc, t_shell_c)

        # LT-322E002: the make in, the gravity drain out in proportion to the head.
        phi_in = hpcc.liq_kgh / HPCC_LIQ_DES_LIVE_KGH if HPCC_LIQ_DES_LIVE_KGH else phi_fwd
        phi_out = phi_fwd * (self.level_pct / LEVEL_NLL_PCT)
        level_0 = self.level_pct
        self.level_pct = clamp(
            self.level_pct + (phi_in - phi_out) * 100.0 * dt / (TAU_FILL_MIN * 60.0), 0.0, 100.0)
        return CondenserStepResult(
            condenser=hpcc, level_pct=self.level_pct, leak=leak,
            dm_kgh=(self.level_pct - level_0) / 100.0 * E002_SPAN_KG * (3600.0 / dt),
            sat_frac=sat)

    @staticmethod
    def _solved_fraction(condense, p_syn_bara: float) -> float:
        """The saturation fraction consistent with the melt it lets condense [-] (A-21).

        Process utility
        ---------------
        Holds 322E002 at the condensation its melt's bubble pressure allows on this tick, so a
        hot, ammonia-rich top gas condenses part of itself steadily instead of all and nothing on
        alternate ticks.
        """
        def excess(f: float) -> float:
            return saturation_fraction(condense(f).p_bub_bara, p_syn_bara) - f

        h_hi = excess(1.0)
        if h_hi >= 0.0:
            return 1.0
        h_lo = excess(0.0)
        if h_lo <= 0.0:
            return 0.0
        return bracketed_root(excess, 0.0, 1.0, h_lo, h_hi, tol=SATURATION_TOL)
