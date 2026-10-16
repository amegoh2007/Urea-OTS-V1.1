"""323C005 — the atmospheric absorber, the LP section's last scrub before the stack.

What this models
----------------
323C005 is a packed column at 1.0 bar a. The gas that reaches atmospheric pressure — PFD 702,
the vent of the LP flash gas node through PV-323203, and PFD 708, the vacuum train's vapour —
rises through the packing against the cold lean solvent PFD 756. The NH3, CO2 and water are
absorbed; the inert gas leaves the top as PFD 341, carrying what vapour it holds there, to
328V001's stack. The liquor collects in the dished bottom head and drains freely through N4
into 328V001, whose overflow seal passes it on to 328D003's compartment II as PFD 343.

    756 (lean solvent) --> packing <-- 702 + 708 (gas)
                  |              |
                  v              +--> 341 (inerts + saturated vapour) --> 328V001 stack
    sump --N4 (weir / orifice)--> 343 --> 328V001 --> 328D003 compartment II

No controller acts on it: the sump holds only the head that pushes the bottoms into N4.

The vent (V1 report D-11)
-------------------------
PFD 341 is the inert gas of 702 and 708 leaving saturated at the absorber top, in equilibrium
with the lean solvent that enters there — its N2 + O2 are what 702 and 708 bring, and its water
partial pressure is psat(43 C) at an activity of 0.95. So the vent is the saturated-gas law
(`ureasim.thermo.saturated_vent`) at the live solvent temperature and the inerts that arrive —
702's with its flow, 708's with the 324E002 vent's — anchored on the PFD's 80 kg/h:

    m_341 = min( 80 . model(m_702 / 440, r_706, T_solvent) / model(1, 1, 43),  m_702 + m_708 )

What the vent does not carry is absorbed: m_abs = m_702 + m_708 - m_341.

The liquor
----------
    M cp dT/dt = sum m_in cp (T_in - T) + m_abs . lambda                 lambda = 1365.7 kJ/kg

semi-implicit in the three inlets, 756 at 43 C, 702 at 45 and 708 at 121. The absorption heat
is back-solved on the design so the design holds. The liquor cannot absorb past its boiling
point at 1.0 bar a: there its NH3 and CO2 back-pressure is above anything the gas carries, so
when a tick would carry the liquor past Tsat(1.0) the absorption is cut to what takes it exactly
there, and the rest vents. With the solvent on, the design liquor sits 45 K below it.

The sump (V1 report A-16)
-------------------------
The bottoms fall from N4 (DN 150, 168.3 x 5.6) about 10 m to 328V001, whose overflow holds its
pool; both gas spaces are atmospheric, so the sump drains freely. It holds only the head that
pushes the bottoms into the N4 pipe — the smaller of a Francis weir over the pipe rim and a
sharp-edged orifice on its bore — 49 mm at the design 34.9 m3/h, about 8 kg in the dished head:

    Q(h) = min( 1.84 . pi d h^1.5,  0.61 . (pi d^2 / 4) sqrt(2 g h) )
    m_343 = 34 180 . Q(h(M)) / Q(h(M_des))                     [exactly PFD 343 at the seed]

stepped backward Euler, since the drain's time constant falls as h^1.5 toward an empty sump.

323E011's overflow (decided 2026-10-03, handoff A-20)
------------------------------------------------------
A full 323E011 / 323D011 envelope overflows through PV-323203's vent line, its only outlet above
the liquid, into this column, which is built to scrub what is vented to it (the process
engineer's routing). The overflow is liquid: it is neither gas load nor vent, it is not absorbed,
and it falls to the sump with its sensible heat at the condensate's temperature, so the bottoms
carry it on to 328V001 and 328D003. The model carries no composition for the liquor, so none of
it flashes at the column's 1.0 bar a. V1 has no such stream; at zero overflow the column is V1's
to the bit.

    M cp dT/dt = ... + m_over cp (T_over - T)          sump inlet: 756 + m_abs + m_over

Each inlet at its producer's live temperature (decided 2026-10-16, handoff B-31)
---------------------------------------------------------------------------------
V1 charges 756 at 43 C and 702 at 45 C whatever 322C001 and 323E011 do, although it reads
322C001's live temperature for the same 756 at the top of its vent. The port charges both as their
departure from their producer's design, ``T_in = T_in,des + (T_producer - T_producer,des)``, each
producer's of the tick before (both step after this unit): the solvent's temperature the vent
already reads, and 323E011's condensate, the overflow's. At the design seed both are V1's to the
bit; ``live_inlets=False`` is V1's, which the plant-level harness keeps. 708 comes at 324F002's
discharge temperature (handoff B-97, decided 2026-10-16): the vacuum train's adiabatic mix of 706
and 924, already its departure from the design mix (`vacuum_train.discharge_708_c`), 121 C at
design, read a tick late (the train steps last).

The boundaries this unit reads, and when
----------------------------------------
V1 steps this unit FIRST in its LP recirculation and desorption block, so every stream into
it is a tear, read as it stood at the end of the tick before:

  * 702 from 323E011 (`FlashCondenserResult.m_702_kgh`; V1 ``R3232_702``);
  * 756 from 322C001's circuit (V1 ``R322_756``), a boundary at design until 322C001 is ported;
  * 708, its temperature (B-97) and 324E002's vent inerts from unit 324 (V1 ``R324_708``,
    ``R324_706_INERT``);
  * 322C001's liquor temperature, the lean solvent's, at the start of the tick — a State read;
  * 323E011's envelope overflow and its temperature, likewise last tick's tears (A-20).

It publishes 343 for 328D003's compartment II on the same tick, and 341 to the stack.

Source
------
V1 ``backend/main.py`` step_sim, "Stage 1 : 323C005 vent scrub -> 328V001 -> Comp-II feed"
(lines 8847-8881); the sump relations and constants (1831-1937); ``c005_vent_kgh`` (3908-3930);
the seeds in ``State.__init__`` (6877-6878). The design data are in `ureasim.data.unit_323c005`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ureasim.core.units_of_measure import G_ACC
from ureasim.data.unit_323c005 import (
    C005_BOT_DES_KGH,
    C005_C_WEIR,
    C005_CAP_KMOLH,
    C005_CD_ORIFICE,
    C005_CP,
    C005_HEAD_A_M,
    C005_ID_M,
    C005_LAM_KJKG,
    C005_M702_DES_KGH,
    C005_N4_ID_M,
    C005_N702_KMOLH,
    C005_N708_KMOLH,
    C005_P_BARA,
    C005_RHO_KGM3,
    C005_T702_C,
    C005_T708_C,
    C005_T756_C,
    C005_T_C,
    C005_VENT_DES_KGH,
    C005_VENT_SPEC,
    E002_INERT_DES_KMOLH,
)
from ureasim.data.unit_322c001 import C001_T_C
from ureasim.data.unit_323e011 import E011_T_C
from ureasim.thermo import iapws
from ureasim.thermo import saturated_vent as sv

#: Bisection passes: the sump's depth from its mass, the design depth, and the backward-Euler
#: depth. Source: V1 `main.py`, ``range(60)``, ``range(80)`` and ``range(60)``.
HEAD_BISECTION_PASSES = 60
DESIGN_HEAD_BISECTION_PASSES = 80

#: The upper bracket of the design-depth bisection [m], V1's literal.
DESIGN_HEAD_BRACKET_M = 2.0

#: Numerical floor on the temperature integration's heat capacity [kJ/K], V1's literal.
HEAT_CAPACITY_FLOOR_KJK = 1e-6


# ======================================================================================
# The sump and its N4 drain
# ======================================================================================

def sump_volume_m3(h_m: float) -> float:
    """Liquor volume [m3] in the bottom head and shell at a depth h [m] above the N4 inlet.

    Process utility
    ---------------
    The sump's geometry: a 2:1 ellipsoidal head, then the cylindrical shell. It turns the
    liquor held into the head that drives the drain.

    Equation
    --------
        V = pi r^2 (h^2 / a - h^3 / (3 a^2))          h <= a,  a = ID / 4
        V = pi r^2 (2 a / 3 + (h - a))                h >  a

    Source: V1 `main.py` ``c005_sump_volume_m3``.
    """
    r2 = (C005_ID_M / 2.0) ** 2
    a = C005_HEAD_A_M
    h = max(h_m, 0.0)
    if h <= a:
        return math.pi * r2 * (h * h / a - h ** 3 / (3.0 * a * a))
    return math.pi * r2 * (2.0 * a / 3.0 + (h - a))


def sump_head_m(m_kg: float) -> float:
    """Depth [m] over the N4 inlet that holds a sump mass [kg].

    Process utility
    ---------------
    The inverse of the geometry: the head the drain sees. Linear in the shell, by bisection in
    the head.

    Source: V1 `main.py` ``c005_sump_head_m``.
    """
    v = max(m_kg, 0.0) / C005_RHO_KGM3
    v_head = sump_volume_m3(C005_HEAD_A_M)
    if v >= v_head:
        return C005_HEAD_A_M + (v - v_head) / (math.pi * (C005_ID_M / 2.0) ** 2)
    lo, hi = 0.0, C005_HEAD_A_M
    for _ in range(HEAD_BISECTION_PASSES):
        mid = 0.5 * (lo + hi)
        if sump_volume_m3(mid) < v:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def sump_drain_m3s(h_m: float) -> float:
    """What the N4 inlet takes [m3/s] at a head h [m]: weir or orifice, whichever is less.

    Process utility
    ---------------
    Why the sump holds only a few kilograms: at low head the liquor spills over the pipe rim
    as over a weir, at high head the bore limits it as an orifice. At the design 34.9 m3/h the
    weir governs, at 49 mm.

    Equation
    --------
        Q = min( C_w pi d h^1.5,  C_d (pi d^2 / 4) sqrt(2 g h) )      C_w 1.84, C_d 0.61

    Source: V1 `main.py` ``c005_drain_m3s``.
    """
    h, d = max(h_m, 0.0), C005_N4_ID_M
    return min(C005_C_WEIR * math.pi * d * h ** 1.5,
               C005_CD_ORIFICE * math.pi * d * d / 4.0 * math.sqrt(2.0 * G_ACC * h))


def _design_head_m() -> float:
    """The head [m] at which N4 takes exactly PFD 343. Source: V1 ``_c005_design_head_m``."""
    q, lo, hi = C005_BOT_DES_KGH / C005_RHO_KGM3 / 3600.0, 0.0, DESIGN_HEAD_BRACKET_M
    for _ in range(DESIGN_HEAD_BISECTION_PASSES):
        mid = 0.5 * (lo + hi)
        if sump_drain_m3s(mid) < q:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


#: The sump's design holdup [kg], about 8, and N4's capacity there [m3/s], the anchor of the
#: bottoms — taken through the same path a tick takes. Source: V1 A323_C005_M_DES, _Q_REF.
SUMP_M_DES_KG = C005_RHO_KGM3 * sump_volume_m3(_design_head_m())
SUMP_Q_REF_M3S = sump_drain_m3s(sump_head_m(SUMP_M_DES_KG))


def sump_step(m_kg: float, in_kgh: float, dt: float) -> tuple[float, float]:
    """Advance the sump by dt [s], backward Euler: returns (the new mass [kg], the bottoms [kg/h]).

    Process utility
    ---------------
    The sump's mass balance on a drain whose time constant falls as h^1.5 toward an empty sump,
    which an explicit step cannot follow. The bottoms are anchored on the design flow,
    34 180 . Q(h) / Q(h_des), exactly PFD 343 at the seed; the flow returned is the one that
    closes the mass balance exactly.

    Equation
    --------
        rho V(h') + 34 180 Q(h') / Q_ref . dt / 3600 = M + m_in . dt / 3600     solved for h'

    Source: V1 `main.py` ``c005_sump_step``.
    """
    bot = C005_BOT_DES_KGH * sump_drain_m3s(sump_head_m(m_kg)) / SUMP_Q_REF_M3S
    if bot == in_kgh or dt <= 0.0:
        return m_kg, bot
    rhs = max(m_kg, 0.0) + max(in_kgh, 0.0) * dt / 3600.0
    lo, hi = 0.0, sump_head_m(rhs)
    for _ in range(HEAD_BISECTION_PASSES):
        mid = 0.5 * (lo + hi)
        f = (C005_RHO_KGM3 * sump_volume_m3(mid)
             + C005_BOT_DES_KGH * sump_drain_m3s(mid) / SUMP_Q_REF_M3S * dt / 3600.0 - rhs)
        if f < 0.0:
            lo = mid
        else:
            hi = mid
    m_new = C005_RHO_KGM3 * sump_volume_m3(lo)
    return m_new, (rhs - m_new) * 3600.0 / dt


# ======================================================================================
# The vent, PFD 341
# ======================================================================================

def _vent_model_kgh(r702: float, r706: dict, t_c: float) -> float:
    """The saturated-gas vent [kg/h] on 702's and 708's inerts scaled, and all their vapour."""
    n = {k: C005_N702_KMOLH[k] * r702 + C005_N708_KMOLH[k] * r706[k] for k in sv.INERT}
    n.update(C005_CAP_KMOLH)
    return sv.vent_mass_kgh(sv.vent_moles(C005_VENT_SPEC, C005_P_BARA, t_c, n))


#: The vent model at the design state [kg/h], the anchor's denominator.
VENT_MODEL_DES_KGH = _vent_model_kgh(1.0, {k: 1.0 for k in sv.INERT}, C005_T756_C)


def vent_kgh(m_702_kgh: float, inert_706_kmolh: dict, t_solvent_c: float) -> float:
    """PFD 341, what 323C005 lets go to the stack [kg/h], before the cap at the gas present.

    Process utility
    ---------------
    The scrub's losses to atmosphere: more inert gas carries more NH3 and water out, and a warmer
    solvent at the top lets more go. 702 brings its inerts in proportion to its flow, 708 in
    proportion to the inerts 324E002 vents.

    Equation
    --------
        m_341 = 80 . model(m_702 / 440, n_706 / n_706,des, T_solvent) / model(1, 1, 43)

    Exactly 80 kg/h at the design state (V1 report D-11).

    Source: V1 `main.py` ``c005_vent_kgh``.
    """
    r706 = {k: inert_706_kmolh.get(k, 0.0) / E002_INERT_DES_KMOLH[k] for k in sv.INERT}
    return C005_VENT_DES_KGH * (_vent_model_kgh(m_702_kgh / C005_M702_DES_KGH, r706, t_solvent_c)
                                / VENT_MODEL_DES_KGH)


#: Where the liquor stops absorbing [deg C]: water's boiling point at the column's 1.0 bar a.
T_BOIL_C = iapws.tsat_c(C005_P_BARA)


# ======================================================================================
# The unit
# ======================================================================================

@dataclass(frozen=True)
class AtmosphericAbsorberResult:
    """Everything 323C005 publishes on one tick."""

    #: The gas that arrives, 702 + 708, and everything onto the packing, 756 + gas [kg/h].
    gas_kgh: float
    in_kgh: float
    #: PFD 341 to the stack and the gas the solvent absorbs [kg/h].
    m_341_kgh: float
    abs_kgh: float
    #: The liquor would have passed its boiling point: the absorption was cut and the rest vented.
    boil_limited: bool
    #: PFD 343 to 328V001 and 328D003's compartment II [kg/h].
    m_343_kgh: float
    #: 323E011's envelope overflow received into the sump [kg/h] (handoff A-20).
    e011_over_kgh: float
    #: The state after this tick: the liquor temperature [deg C], the sump [kg] and its head
    #: over N4 [m].
    t_c: float
    m_kg: float
    sump_head_m: float


@dataclass
class AtmosphericAbsorber:
    """323C005 as one object: the sump and the liquor temperature, and the step."""

    #: The sump's holdup [kg] and the liquor temperature [deg C].
    m_kg: float = SUMP_M_DES_KG
    t_c: float = C005_T_C
    #: 756 and 702 at their producers' live temperatures, as departures from the producers'
    #: designs (decided 2026-10-16, handoff B-31), and 708 at 324F002's discharge (B-97); False is
    #: V1's design temperatures.
    live_inlets: bool = True

    def step(self, m_702_kgh: float, m_756_kgh: float, m_708_kgh: float,
             inert_706_kmolh: dict, t_solvent_c: float, dt: float, *,
             m_e011_over_kgh: float = 0.0,
             t_e011_over_c: float = E011_T_C,
             t_708_c: float = C005_T708_C) -> AtmosphericAbsorberResult:
        """Advance 323C005 by one tick.

        Arguments
        ---------
        m_702_kgh
            323E011's vent, LAST tick's (`FlashCondenserResult.m_702_kgh`), a tear.
        m_756_kgh
            The lean solvent from 322C001's circuit, last tick's, a tear.
        m_708_kgh, inert_706_kmolh
            Unit 324's vapour to the absorber [kg/h] and 324E002's vent inerts {N2, O2}
            [kmol/h], last tick's, tears.
        t_solvent_c
            322C001's liquor temperature at the start of the tick: the solvent at the top, and
            756's live temperature (B-31).
        m_e011_over_kgh, t_e011_over_c
            323E011's envelope overflow through PV-323203's vent line [kg/h] and the condensate
            temperature it leaves at [deg C], last tick's, tears (decided 2026-10-03, handoff
            A-20). Liquid to the sump, with its sensible heat. The temperature is also 702's
            (B-31).
        t_708_c
            708's temperature, 324F002's discharge (`VacuumTrainResult.t_708_c`), last tick's, a
            tear (B-97).

        The order is V1's: the vent on the gas that arrives, the absorption and its heat, the
        boiling-point cut, the sump, the temperature.
        """
        t_pre = self.t_c
        gas = m_702_kgh + m_708_kgh
        m_341 = min(vent_kgh(m_702_kgh, inert_706_kmolh, t_solvent_c), gas)
        m_abs = max(gas - m_341, 0.0)
        in_kgh = m_756_kgh + gas
        # 756 and 702 at their producers' live temperatures, as departures from the producers'
        # designs: zero at design, so V1's to the bit there (decided 2026-10-16, handoff B-31).
        # 708 at 324F002's discharge, the train's departure from its design mix (B-97).
        if self.live_inlets:
            t_756 = C005_T756_C + (t_solvent_c - C001_T_C)
            t_702 = C005_T702_C + (t_e011_over_c - E011_T_C)
            t_708 = t_708_c
        else:
            t_756, t_702, t_708 = C005_T756_C, C005_T702_C, C005_T708_C
        # The three inlets' sensible heat and the absorption heat of what the solvent takes.
        p_net = ((m_756_kgh / 3600.0 * C005_CP * (t_756 - t_pre)
                  + m_702_kgh / 3600.0 * C005_CP * (t_702 - t_pre)
                  + m_708_kgh / 3600.0 * C005_CP * (t_708 - t_pre))
                 + m_abs / 3600.0 * C005_LAM_KJKG)
        # 323E011's overflow brings only its sensible heat (A-20).
        p_net += m_e011_over_kgh / 3600.0 * C005_CP * (t_e011_over_c - t_pre)
        # SEMI-IMPLICIT in the three inlets, the temperature-dependent load.
        k_cap = ((m_756_kgh + m_702_kgh + m_708_kgh) / 3600.0 * C005_CP
                 + m_e011_over_kgh / 3600.0 * C005_CP)
        den = self.m_kg * C005_CP + k_cap * dt
        # The liquor cannot absorb past its boiling point: cut the absorption to what takes it
        # exactly there, and vent the rest.
        boil_limited = False
        if m_abs > 0.0 and t_pre + p_net * dt / max(den, HEAT_CAPACITY_FLOOR_KJK) > T_BOIL_C:
            abs_cap = max(((T_BOIL_C - t_pre) * den / dt
                           - (p_net - m_abs / 3600.0 * C005_LAM_KJKG)) * 3600.0 / C005_LAM_KJKG,
                          0.0)
            if abs_cap < m_abs:
                p_net -= (m_abs - abs_cap) / 3600.0 * C005_LAM_KJKG
                m_abs = abs_cap
                m_341 = gas - m_abs
                boil_limited = True
        # The solvent and what it absorbed fall to the sump, which drains through N4; so does
        # 323E011's overflow (A-20).
        self.m_kg, m_343 = sump_step(self.m_kg, m_756_kgh + m_abs + m_e011_over_kgh, dt)
        self.t_c = t_pre + p_net * dt / max(den, HEAT_CAPACITY_FLOOR_KJK)

        return AtmosphericAbsorberResult(
            gas_kgh=gas, in_kgh=in_kgh, m_341_kgh=m_341, abs_kgh=m_abs,
            boil_limited=boil_limited, m_343_kgh=m_343, e011_over_kgh=m_e011_over_kgh,
            t_c=self.t_c, m_kg=self.m_kg,
            sump_head_m=sump_head_m(self.m_kg),
        )


__all__ = [
    "HEAD_BISECTION_PASSES", "DESIGN_HEAD_BISECTION_PASSES", "DESIGN_HEAD_BRACKET_M",
    "HEAT_CAPACITY_FLOOR_KJK", "sump_volume_m3", "sump_head_m", "sump_drain_m3s",
    "SUMP_M_DES_KG", "SUMP_Q_REF_M3S", "sump_step", "VENT_MODEL_DES_KGH", "vent_kgh",
    "T_BOIL_C", "AtmosphericAbsorberResult", "AtmosphericAbsorber",
]
