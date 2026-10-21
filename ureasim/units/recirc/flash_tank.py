"""323F004 — the flash tank, stage 2 of unit 323.

What this models
----------------
The 323C003 bottoms, PFD 314 (135 C, 4.1 bar a, 68.7 % urea), let down through LV-323501 into
323F004 at about 1.13 bar a. That pressure is below the liquor's bubble point, so part of it
flashes: the residual carbamate decomposes into ammonia and CO2, some water boils, and the
latent heat comes out of the liquor's own sensible heat, cooling it to 106 C. The drum has no
heater. It is adiabatic, and the letdown's sensible heat is all it has to flash with.

  * The vapour, PFD 701 (4.43 t/h; by mole 62 % water, 34 % ammonia, 4 % CO2), leaves the top
    for the 323E011 flash condenser.
  * The liquid, PFD 319 (71.7 % urea), drains through LV-323505 to the 323E010 pre-evaporator
    and its 323F010 separator under vacuum.

    LIC-323505 (drum level)  ->  LV-323505 (drain to 323E010 / 323F010)

The drum is a well-mixed liquid holdup with a mass, an energy and a species balance:

    dM/dt      = m_314 - m_701 - m_319
    M cp dT/dt = m_314 . cp_314 . (T_314 - T) - m_701 . lambda_701           [adiabatic]
    d(M w)/dt  = the species balance of `units.liquor_stage`

The flash, energy-limited
-------------------------
A flashing drum's temperature and pressure are not independent: its liquid sits at its bubble
point. The flash is therefore what the letdown's sensible heat can boil, less what is needed to
walk the holdup to the bubble point over its own residence time:

    q_avail = m_314 . cp_314 . (T_314 - T)                  heat the letdown brings above the drum
    q_relax = M . cp . (T_bub(w, P) - T) / tau               heat retained to reach the bubble point
    m_701   = max( m_701,des . (q_avail - q_relax) / q_701,des , 0 )

and lambda_701 = q_701,des / m_701,des, so while m_701 > 0 the energy balance reduces exactly to
M cp dT/dt = q_relax: the drum temperature relaxes to its bubble point, energy is conserved, and
a hotter or larger drain flashes more, not a frozen fraction of it (V1 report F-1). A drain
colder than the drum flashes nothing; its sensible heat then only moves the temperature. At
design every bracket is exact — P = 1.13, T_bub = 106.0, q_relax = 0.0, q_avail = q_701,des —
and m_701 is PFD 701 to the bit.

The mass balance: where the vapour goes
---------------------------------------
m_701 leaves this unit's balance as vapour and is published for the 323E011 condenser, which
takes it as one inflow of its gas node. It does not return to 323C003 in any form: stream 302 is
the gas 323C003's own heater raises from 323C003's own pool, and it leaves with PFD 305 for the
323E003 LP carbamate condenser — a different condenser at a different pressure. The two flash
streams of unit 323 go to two separate places.

Two corrections to that vapour belong to the node, not to the drum, and the drum publishes
what they need. When 323C003's level falls through the LV-323501 nozzle, column gas blows
through into this drum's gas space and continues to 323E011 (323C003 publishes it). When this
drum's level falls through the LV-323505 nozzle, the drum's own vapour blows through to
323F010 instead of going to 323E011 (published here, with its composition). The node takes
    m_701 - blow-through(LV-323505) + blow-through(LV-323501).

The pressure: floating, and set downstream
------------------------------------------
Nothing on this drum controls its pressure, and there is no valve between the drum and the
323E011 condenser. PIC-323203 holds 1.13 bar a on the condenser's VENT (PV-323203, to the
323C005 atmospheric absorber), and that back-pressure is exerted across one gas space — the
drum, the vapour line, the 323E011 shell and the 323D011 level tank (`References/323F004
323E010 323F010.md` §4, `References/323C005 328V001 Datasheets.md`). So the drum pressure is
neither fixed nor the product of a law of its own: it IS the 323E011 / 323D011 node pressure,
which the condenser unit integrates on its measured 3.14 m3 envelope.

    P_323F004 = P_323E011 node                                  [bar a]

1.13 bar a appears in this module only as a design ANCHOR — of the bubble-point departure, of
the flash vapour's volatility departure, and of LV-323505's anchored valve law — where it is
the state at which each is pinned to the PFD. The live pressure is what drives them:

  * the bubble point rides it, which closes the loop the plant has: more flash -> the node
    pressure rises -> the bubble point rises -> the next flash is smaller;
  * LV-323505's flow rides it against the 323F010 vacuum, which couples the level loop to both;
  * 323C003's LV-323501 reads it as its downstream pressure.

It is an explicit tear, V1's: at the end of each tick the drum adopts the node pressure as the
node stood at the START of the tick (the condenser advances later in the tick). Every relation
in the tick therefore works on the pressure adopted one tick earlier. At design both are
1.13 bar a and nothing moves.

V1's constant block still carries a comment describing an older law, P_target = 1.13 + K .
(relative flash excess) with a 90 s lag. V1 retired it (report A-7: pressure followed flow,
where physically flow follows pressure); it is not ported.

A full drum overflows into 323E011 (decided 2026-10-17, handoff A-22)
---------------------------------------------------------------------
V1 clamps LI-323505's reading at 100 % and not the holdup, so a drum whose drain is pinched keeps
filling with nothing leaving. Decision 11's class: above the full drum (on V1's drum, the holdup at
which LI-323505 reads 100 %) the excess leaves as a published overflow, at the drum's composition
and temperature,

    m_overflow = (M_new - M_full) / dt,   M_new = M_full,

and the process engineer routed it up the vapour line into 323E011's shell — the one gas space
the drum shares (B-51) — where it lands in 323D011 with its sensible heat, as a full 328D001's
does (A-15). Inert below a full drum. ``FlashTank(ceiling=False)`` is V1's, which the
equivalence harness keeps.

The drum on its geometry (decided 2026-10-17, handoff B-100 (b), decision 33's class)
------------------------------------------------------------------------------------
V1 sizes the holdup on a 180 s residence, 5075 kg — ten times the 518 kg of operating fluid the
datasheet's weights give and more than the 3.40 m3 drum holds — and reads LI-323505 as that holdup
over 0.6. Here the drum is its shell, 1384 mm by 1800 mm between two DIN 28013 heads
(`data.unit_323.F004_VESSEL`), and LT-323505 reads the liquid's height between its taps: a DP
cell from the outlet line, 867 mm below the bottom tangent, to N7 on the top head, 2900 mm above
(`data.unit_323.lt_323505_pct`). LIC-323505's 60 % then holds 1837 kg, 874 mm above the bottom
tangent, 65 s of PFD 319; a full drum, 3761 kg, overflows (A-22); and LV-323505's nozzle, N3 at
the bottom head's lowest point, reads 17.8 %, where its seal is placed (``seal_fraction``'s nozzle
at that reading, V1's 3 % band). ``V1_DRUM`` — V1's holdup, its level law and no ceiling — is the
equivalence harness's.

Source
------
V1 ``backend/main.py`` step_sim, "Stage 2: Flash Tank 323F004" (lines 8410-8507) and the
323C003 -> 323F004 line transport (8363-8375); reports F-1 (the energy-limited flash), A-11
(the bubble point), A-7 (the pressure), D-1 (the IEC letdown), D-20 (the seal), F-8 / TD-009
(the species layer). The design data are in `ureasim.data.unit_323`, each with its source.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ureasim.control.process_loop import ProcessLoop
from ureasim.control.valve import cv_fraction, valve_liquid_anchored
from ureasim.core.numeric import clamp
from ureasim.core.stream import MW_COMP
from ureasim.data.design_point import R323_M319_DES
from ureasim.data.unit_323 import (
    CP_C003_DES,
    CP_F004_DES,
    F004_LIQUOR,
    F004_LVL_SP_PCT,
    F004_M_DES_KG,
    F004_M_DES_KG_V1,
    F004_M_FLOOR_KG,
    F004_M_FULL_KG,
    F004_M_FULL_KG_V1,
    F004_M_TAU_S,
    F004_P_BARA,
    F004_T_SP_C,
    F010_P_BARA,
    LAMBDA_701_KJKG,
    LIC_323505_KC,
    LIC_323505_TI_S,
    LV505_CHAR,
    LV505_FL,
    LV505_OP_DES_PCT,
    LV505_PV_DES_BARA,
    LT_323505_NOZZLE_PCT,
    M701_DES_KGH,
    Q701_DES_KW,
    RHO_F004_DES,
    RHO_S319,
    W_S319,
    lt_323505_pct,
)
from ureasim.thermo.empirical import urea_soln_rho
from ureasim.thermo.urea_liquor import stage_bubble_p
from ureasim.units import liquor_stage
from ureasim.units.consequence.seal import blowthrough_kgh, gas_density_ideal, seal_fraction
from ureasim.units.recirc.liquor_line import receive_liquor, stream_cp

#: The 323C003 -> 323F004 line, which this unit owns as the receiving vessel. Source: V1
#: `main.py`, ``_transport_process(s, "323C003_TO_323F004", ...)``.
INLET_ROUTE = "323C003_TO_323F004"

#: Numerical floors, V1's own literals at this stage: the temperature integration's heat
#: capacity [kJ/K] and the blow-through gas molar sum [-].
HEAT_CAPACITY_FLOOR_KJK = 1e-6
MOLAR_SUM_FLOOR = 1e-9

#: Guard on the tick in the overflow [s], as 328D001's.
DT_FLOOR_S = 1e-9

#: V1's drum, which the equivalence harness runs: its 5075 kg holdup on its level law, no ceiling.
V1_DRUM = {"ceiling": False, "geometric": False, "m_kg": F004_M_DES_KG_V1}


def lic_323505() -> ProcessLoop:
    """LIC-323505, the drum level. DIRECT acting: a level above set point opens LV-323505."""
    return ProcessLoop(
        tag="LIC-323505", Kc=LIC_323505_KC, Ti=LIC_323505_TI_S, Td=0.0, act=-1.0,
        op=LV505_OP_DES_PCT, sp=F004_LVL_SP_PCT,
        pv=F004_LVL_SP_PCT, pv1=F004_LVL_SP_PCT, pv2=F004_LVL_SP_PCT,
        op_lo=0.0, op_hi=100.0, sp_lo=0.0, sp_hi=100.0)


def letdown_kgh(stroke_pct: float, p_drum_bara: float, p_separator_bara: float,
                w_urea: float, t_c: float, pv_bara: float) -> float:
    """LV-323505 liquid flow to 323E010 / 323F010 [kg/h], on the anchored IEC 60534 liquid law.

    Process utility
    ---------------
    The drum's drain. It lets the flash liquid down from about 1.13 bar a to the 0.46 bar a
    vacuum of the pre-evaporator, so it follows the stroke, the live drum pressure and the
    live density of what it passes.

    The liquor reaches the valve at its bubble point and flashes into the vacuum: its flow chokes
    on FL^2 (P1 - FF . Pv), ``pv_bara`` the drum liquor's live bubble pressure (decided
    2026-09-30, handoff B-46). At the design state the choke binds, so a vacuum upset downstream
    no longer reaches the drum level through this valve; the drum's own pressure and temperature
    do.
    """
    return valve_liquid_anchored(
        R323_M319_DES, stroke_pct / 100.0, p_drum_bara, p_separator_bara,
        urea_soln_rho(w_urea, t_c, RHO_S319),
        LV505_OP_DES_PCT / 100.0, F004_P_BARA, F010_P_BARA, RHO_F004_DES,
        characteristic=LV505_CHAR, fl=LV505_FL, pv_bara=pv_bara, pv_des_bara=LV505_PV_DES_BARA)


@dataclass(frozen=True)
class FlashTankResult:
    """Everything stage 2 publishes on one tick."""

    #: The 323C003 bottoms as they arrived through the 323C003 -> 323F004 line
    #: [kg/h], [deg C], [-], [kJ/(kg.K)].
    feed_kgh: float
    feed_t_c: float
    feed_w: dict
    feed_cp: float
    #: The bubble point the holdup relaxes toward [deg C], the duty retained to get there [kW],
    #: and the heat the letdown brings above the drum [kW].
    t_bub_c: float
    q_relax_kw: float
    q_avail_kw: float
    #: PFD 701, the flash vapour to 323E011 [kg/h], its composition, and the surface it came off.
    m_701_kgh: float
    y_701: dict
    vapour_domain: str | None
    #: LIC-323505's input and output [%], the drain [kg/h], and the seal on its nozzle.
    level_pct: float
    lv505_op_pct: float
    m_319_kgh: float
    seal_fraction: float
    #: What a full drum overflows into 323E011's shell [kg/h], at its temperature (A-22).
    m_overflow_kgh: float
    #: Drum vapour passing an uncovered LV-323505 into 323F010 [kg/h], [kmol/h], and its mass
    #: fractions (None while the nozzle is sealed).
    blowthrough_kgh: float
    blowthrough_kmolh: float
    blowthrough_y: dict | None
    lv505_blowthrough: bool
    #: The state the drain departed at — the drum's temperature [deg C] and composition
    #: BEFORE this tick advanced them. 323F010 carries it down its inlet line.
    drain_t_c: float
    drain_w: dict
    #: Biuret formed [kmol/h]. The PFD back-solve gives this drum none.
    xi_kmolh: float
    #: The state after this tick. p_bara is the node pressure the drum adopted.
    m_kg: float
    t_c: float
    p_bara: float
    w: dict


@dataclass
class FlashTank:
    """323F004: the drum's state and its step."""

    #: Liquid holdup [kg], temperature (TT-323005) [deg C], pressure [bar a] and composition.
    m_kg: float = F004_M_DES_KG
    t_c: float = F004_T_SP_C
    p_bara: float = F004_P_BARA
    w: dict = field(default_factory=lambda: dict(W_S319))
    #: The inlet line's packet FIFO.
    line_state: dict = field(default_factory=dict)
    #: A full drum overflowing into 323E011 (decided 2026-10-17, handoff A-22); False is V1's
    #: uncapped holdup, which the equivalence harness keeps.
    ceiling: bool = True
    #: The drum on its geometry and LT-323505 between its taps (decided 2026-10-17, handoff
    #: B-100); False is V1's holdup over 0.6 (`V1_DRUM`).
    geometric: bool = True

    def step(self, lic: ProcessLoop, drain_kgh: float, drain_t_c: float, drain_w: dict,
             p_e011_bara: float, p_f010_bara: float, dt: float) -> FlashTankResult:
        """Advance stage 2 by one tick.

        Arguments
        ---------
        drain_kgh, drain_t_c, drain_w
            323C003's drain through LV-323501 as it departed on this tick: the flow [kg/h] and
            the column's temperature [deg C] and composition before the column advanced
            (`RectifyingColumnResult.m_314_kgh`, `.drain_t_c`, `.drain_w`).
        p_e011_bara
            The 323E011 / 323D011 gas-node pressure at the start of the tick [bar a]. The drum
            adopts it at the end of the tick; see the module docstring.
        p_f010_bara
            The 323F010 separator pressure at the start of the tick [bar a], downstream of
            LV-323505 — an explicit tear, advanced by its own unit later in the tick.

        The order is V1's and it is not interchangeable: the flash, the level loop and the
        drain act on the state at the top of the tick; the temperature advances before the
        vapour composition and the biuret extent are evaluated, which therefore see the NEW
        temperature and the OLD composition and pressure; the pressure is adopted last.
        """
        cp_drum = stream_cp(self.w.get("Urea", 0.0), self.t_c, CP_F004_DES)
        # ----- the inlet: one closed packet down the 323C003 -> 323F004 line -----------
        feed = receive_liquor(self.line_state, INLET_ROUTE, drain_kgh, drain_t_c, drain_w,
                              CP_C003_DES, dt)

        # ----- the isenthalpic flash, energy-limited ----------------------------------
        # The liquid sits at its bubble point on the live pressure; the letdown's sensible
        # surplus flashes, less what walks the holdup to that bubble point (report F-1).
        t_bub = liquor_stage.bubble_t(F004_LIQUOR, self.w, self.p_bara)
        q_relax = self.m_kg * cp_drum * (t_bub - self.t_c) / F004_M_TAU_S
        q_avail = feed.m_kgh / 3600.0 * feed.cp_kj_kgk * (feed.t_c - self.t_c)
        m_701 = max(M701_DES_KGH * ((q_avail - q_relax) / Q701_DES_KW), 0.0)

        # ----- LIC-323505 -> LV-323505, and the seal on its nozzle --------------------
        if self.geometric:
            level = lt_323505_pct(self.m_kg)
        else:
            level = clamp(self.m_kg / F004_M_FULL_KG_V1 * 100.0, 0.0, 100.0)
        lv505_op = lic.step(level, dt)
        m_319 = letdown_kgh(lv505_op, self.p_bara, p_f010_bara, self.w.get("Urea", 0.0),
                            self.t_c, stage_bubble_p(F004_LIQUOR, self.w, self.t_c, self.p_bara))
        # The valve keeps its 1.13 -> 0.46 bar a drop when the drum empties. Without a seal
        # the liquid kept draining at the full valve rate and the holdup floor put the
        # missing mass back, so an empty drum MADE liquor (report D-20). Uncovered, the trim
        # passes the drum's own vapour on IEC 60534 compressible flow; near atmospheric that
        # vapour is ideal (SRK Z > 0.99). Sealed, the gas is exactly 0.0.
        seal = seal_fraction(level, LT_323505_NOZZLE_PCT if self.geometric else 0.0)
        m_319 *= seal
        blow = 0.0
        blow_kmolh = 0.0
        blow_y = None
        if seal < 1.0:
            y_gas, _ = liquor_stage.vapour(F004_LIQUOR, self.w, self.t_c, self.p_bara)
            mw_gas = 1.0 / max(sum(v / MW_COMP[k] for k, v in y_gas.items() if v > 0.0),
                               MOLAR_SUM_FLOOR)
            blow = blowthrough_kgh(
                R323_M319_DES, RHO_F004_DES, F004_P_BARA - F010_P_BARA,
                cv_fraction(lv505_op / 100.0, LV505_CHAR)
                / cv_fraction(LV505_OP_DES_PCT / 100.0, LV505_CHAR),
                gas_density_ideal(self.p_bara, self.t_c, mw_gas),
                self.p_bara, max(self.p_bara - p_f010_bara, 0.0), seal)
            blow_kmolh = blow / mw_gas
            blow_y = y_gas

        # ----- the balances ------------------------------------------------------------
        # Adiabatic: the letdown's sensible load, less the latent heat the flash carries off.
        p_net = q_avail - m_701 / 3600.0 * LAMBDA_701_KJKG
        m_pre, t_pre, w_pre = self.m_kg, self.t_c, self.w
        # SEMI-IMPLICIT in the letdown's sensible load, whose heat-capacity rate belongs to
        # the FLOW and keeps driving after the inventory has gone. The bubble-point
        # relaxation is not in it: it scales with M and vanishes with the inventory. Exactly
        # the explicit step at the seed, where p_net is 0.
        k_cap = feed.m_kgh / 3600.0 * feed.cp_kj_kgk
        self.t_c = t_pre + p_net * dt / max(m_pre * cp_drum + k_cap * dt,
                                            HEAT_CAPACITY_FLOOR_KJK)
        m_new = max(m_pre + (feed.m_kgh - m_701 - m_319) / 3600.0 * dt, F004_M_FLOOR_KG)
        # Above a full drum the excess overflows to 323E011 at the drum's
        # composition (decision 11's class, A-22). Inert below a full drum.
        m_overflow = 0.0
        m_full = F004_M_FULL_KG if self.geometric else F004_M_FULL_KG_V1
        if self.ceiling and m_new > m_full:
            m_overflow = (m_new - m_full) / max(dt, DT_FLOOR_S) * 3600.0
            m_new = m_full
        self.m_kg = m_new
        y_701, domain = liquor_stage.vapour(F004_LIQUOR, w_pre, self.t_c, self.p_bara)
        xi = liquor_stage.biuret_extent(F004_LIQUOR, m_pre, w_pre, self.t_c)
        self.w = liquor_stage.advance_species(w_pre, m_pre, self.m_kg, feed.m_kgh, feed.w,
                                              m_701, y_701, m_319 + m_overflow, xi, dt)

        # ----- the pressure: the 323E011 / 323D011 node's, adopted last -----------------
        self.p_bara = p_e011_bara

        return FlashTankResult(
            feed_kgh=feed.m_kgh, feed_t_c=feed.t_c, feed_w=feed.w, feed_cp=feed.cp_kj_kgk,
            t_bub_c=t_bub, q_relax_kw=q_relax, q_avail_kw=q_avail,
            m_701_kgh=m_701, y_701=y_701, vapour_domain=domain,
            level_pct=level, lv505_op_pct=lv505_op, m_319_kgh=m_319, seal_fraction=seal,
            m_overflow_kgh=m_overflow,
            blowthrough_kgh=blow, blowthrough_kmolh=blow_kmolh, blowthrough_y=blow_y,
            lv505_blowthrough=bool(blow > 0.0),
            drain_t_c=t_pre, drain_w=w_pre, xi_kmolh=xi,
            m_kg=self.m_kg, t_c=self.t_c, p_bara=self.p_bara, w=self.w,
        )


__all__ = [
    "INLET_ROUTE", "HEAT_CAPACITY_FLOOR_KJK", "MOLAR_SUM_FLOOR", "DT_FLOOR_S", "V1_DRUM",
    "lic_323505", "letdown_kgh",
    "FlashTankResult", "FlashTank",
]
