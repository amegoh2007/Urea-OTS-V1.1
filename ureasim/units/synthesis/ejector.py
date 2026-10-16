"""322F001 — the HP carbamate ejector, on a constant-area jet-pump closure.

What this models
----------------
The circulator of the HP synthesis loop, and the only thing that moves liquid round it.
Liquid ammonia from the 321P002 A/B triplex pumps drives a nozzle, entrains the 322E003 HP
scrubber's carbamate overflow, mixes with it in a constant-area throat and recovers pressure
in a diffuser. The mixture goes to 322E002 as its liquid feed.

It has no moving parts, which is why it is there: the loop runs at 144 bar a, and a pump with
a seal at that pressure on a carbamate stream would be a maintenance item measured in weeks.
What it costs instead is that the loop's circulation is hostage to the ammonia feed — lose
the motive, and the whole HP loop stops circulating, whatever else is still running.

What is in this module, and what is next door
-----------------------------------------------
`control.jet_pump` carries the momentum balance, the single-root proof and the geometry
back-solve, and knows nothing about the plant. This module is the plant wiring: which
pressures, which composition, which anchor, and the two things the closure does not model —
the gravity suction head from the scrubber sump, and the discharge heat balance.

Source
------
Ported from V1 `backend/main.py` `ejector_322f001` (Phase 4b, finding D-6).

Anchoring
---------
The forward call is the RATIO of the closure to itself at the design condition, so the design
duty is reproduced BIT-EXACTLY. That is the same construction the anchored valve laws use and
it is there for the same reason: a back-solved geometry does not multiply back through to the
original float, and this engine's boot pin asserts the design point to the last bit.

The reference is the licensor's design PAIR — the design motive flow and the design suction —
which is the same pair the geometry is back-solved from, so the anchor and the geometry
cannot disagree. It is deliberately NOT the settled motive flow that V1's retired `phi_m`
normalised on: the settled loop runs 0.078 % under the PFD motive, and this closure amplifies
that about tenfold, because the machine sits within 10 % of its own shutoff head. Anchoring
on a settled value would move that offset onto the FIRST TICK from a fresh state, which is
exactly where the boot pin and every unit test measure the design point.
"""

from __future__ import annotations

from dataclasses import dataclass

from ureasim.control import jet_pump
from ureasim.core.numeric import clamp
from ureasim.core.stream import MW_COMP
from ureasim.data.unit_321 import NH3_RHO
from ureasim.data.unit_322f001 import (
    A_M_M2,
    A_T_DES_M2,
    CARBAMATE_FRAC,
    CP_CARBAMATE,
    CP_DISCHARGE,
    CP_MOTIVE,
    HYDRAULIC_FRAC_MAX,
    MOTIVE_DES_KGH,
    MOTIVE_T_DES_C,
    MOTIVE_W,
    OPEN_DES_PCT,
    OPEN_MIN_PCT,
    P_DISCHARGE_DES_BARA,
    P_SUCTION_DES_BARA,
    RHO_DISCHARGE,
    RHO_SUCTION,
    SPINDLE_A_FULL_PCT,
    SUCTION_DES_TOTAL_KGH,
    T_SUCTION_DES_C,
)


@dataclass(frozen=True)
class EjectorResult:
    """One evaluation of 322F001, as 322E002 and the screens read it."""

    #: Discharge composition [kg/h per component] — the 322E002 liquid feed.
    comp_kgh: dict
    #: Discharge total [kg/h] and [kmol/h].
    total_kgh: float
    mol_kmolh: float
    #: Entrained carbamate actually drawn from 322E003 [kg/h].
    suction_kgh: float
    #: Discharge mean molecular weight [g/mol].
    mw: float
    #: TT-322012 discharge temperature [deg C].
    t_c: float
    #: Discharge pressure [bar a] and the volumetric rate at the design density.
    p_bara: float
    rho: float
    vol_m3h: float
    #: Entrainment ratio, entrained mass per unit of motive mass [-].
    mu: float
    #: Suction capacity as a fraction of design, before the sump-head multiplier [-]. The
    #: spindle's effect on the machine, separated from the scrubber's level.
    phi_spindle: float
    #: The jet cannot develop the required lift even at zero entrainment.
    stalled: bool
    #: The throat-entry static pressure has reached the suction fluid's vapour pressure.
    cavitating: bool


def ejector_322f001(motive_nh3_kgh: float, t_motive_c: float, hv_open_pct: float,
                    scrub_level_frac: float = 1.0, xv_322903_open: bool = True,
                    carb_frac: dict = None, p_suct_bara: float = None,
                    p_disch_bara: float = None, outflow_frac: float = 1.0) -> EjectorResult:
    """One tick of the HP carbamate ejector.

    Parameters
    ----------
    motive_nh3_kgh, t_motive_c
        The 321P002 delivery after its battery-limit transit, and TI-321020.
    hv_open_pct
        HV-322602, the motive-nozzle spindle.
    scrub_level_frac
        322E003 sump level as a fraction of its normal level. 1.0 at design.
    xv_322903_open
        The block valve on the 322E003 overflow into the suction.
    carb_frac
        The live 322E003 overflow mass split, from the previous tick. `None` takes the design
        vector, which keeps every reference call bit-exact.
    p_suct_bara, p_disch_bara
        The live synthesis pressures either side of the machine. `None` takes the design
        pair, whose DIFFERENCE is the 4.2 bar lift the jet pump has to make.
    outflow_frac
        The line from the 322E003 sump to the suction, throttled by the overflow's mushy zone
        (handoff B-78 item 3, decided 2026-10-03; V1 throttles the overflow into the sump
        instead). 1.0 while the carbamate stays clear of its solidus.

    Order of the physics
    --------------------
    Spindle -> nozzle area -> closure -> capacity -> sump head -> block valve -> composition
    -> heat balance. The spindle acts first because it acts on the NOZZLE, and everything
    downstream of the nozzle is a consequence of the jet it produces.
    """
    # ----- no motive: a dead jet pump, which is not the same as a cold one -----------------
    if motive_nh3_kgh <= 1e-6:
        # Zero MASS, but TT-322012 does not read 0 C. The thermowell sits in the stagnant
        # fluid backed up into the dead pump, which is 322E003 carbamate at the suction
        # temperature. Losing the COLD motive ammonia — the ~29 C stream that normally pulls
        # the design blend down to about 108 C — leaves only the hot carbamate, so the tag
        # RISES on a motive trip rather than collapsing. This is a stateless reduced model,
        # so there is no thermal-inertia decay on the way there.
        #
        # The mass leaving is 0, so 322E002 sees no liquid feed and its mixed-feed
        # temperature is unperturbed by this branch.
        return EjectorResult(
            comp_kgh={k: 0.0 for k in MW_COMP}, total_kgh=0.0, mol_kmolh=0.0,
            suction_kgh=0.0, mw=0.0, t_c=T_SUCTION_DES_C, p_bara=0.0,
            rho=0.0, vol_m3h=0.0, mu=0.0, phi_spindle=1.0,
            stalled=True, cavitating=False)

    # ----- HV-322602 acts on the nozzle area ----------------------------------------------
    # The DDS free-area map is linear in travel, and closing the spindle RAISES entrainment,
    # because at constant motive mass a smaller area raises the jet momentum. That direction
    # is derived here rather than asserted: the motive comes from positive-displacement
    # pumps, so the valve cannot change the mass flow, only the velocity it leaves at.
    open_eff = clamp(hv_open_pct, OPEN_MIN_PCT, 100.0)
    a_t = A_T_DES_M2 * (40.0 + 0.6 * open_eff) / SPINDLE_A_FULL_PCT

    # ----- the closure, live and at the design reference ----------------------------------
    p_s = P_SUCTION_DES_BARA if p_suct_bara is None else p_suct_bara
    p_d = P_DISCHARGE_DES_BARA if p_disch_bara is None else p_disch_bara
    live = jet_pump.entrainment_kgh(motive_nh3_kgh, p_s, p_d, a_t, A_M_M2,
                                    NH3_RHO, RHO_SUCTION, RHO_DISCHARGE)
    ref = jet_pump.entrainment_kgh(MOTIVE_DES_KGH, P_SUCTION_DES_BARA, P_DISCHARGE_DES_BARA,
                                   A_T_DES_M2, A_M_M2, NH3_RHO, RHO_SUCTION, RHO_DISCHARGE)
    capacity = (SUCTION_DES_TOTAL_KGH * (live["kgh"] / ref["kgh"])) if ref["kgh"] > 0.0 else 0.0
    phi_spindle = capacity / SUCTION_DES_TOTAL_KGH if SUCTION_DES_TOTAL_KGH > 0.0 else 1.0

    # ----- the gravity suction head, and the throat-choke ceiling --------------------------
    # The 322E003 sump's own level helps or hinders the suction. At design the level is at
    # normal, so the multiplier is a literal 1.0 and the entrainment is the capacity to the
    # bit. The ceiling is what stops a flooded sump self-amplifying its own recirculation
    # into the loop. Source: V1 finding D-19.
    m_suc = capacity * (min(max(scrub_level_frac, 0.0), HYDRAULIC_FRAC_MAX) * outflow_frac)

    # XV-322903 is a block valve, not a throttle: shut, the suction line carries nothing and
    # the jet entrains nothing, whatever the spindle and the sump head are doing.
    if not xv_322903_open:
        m_suc = 0.0

    # ----- composition ---------------------------------------------------------------------
    # The entrained stream carries the LIVE 322E003 sump composition. The scrubber is solved
    # after the ejector, so this is the previous tick's overflow split — the same one-tick
    # tear the desorption columns use. At design it is the design vector to the last bit.
    frac = CARBAMATE_FRAC if carb_frac is None else carb_frac
    suction = {k: m_suc * frac.get(k, 0.0) for k in MW_COMP}
    discharge = {k: motive_nh3_kgh * MOTIVE_W[k] + suction[k] for k in MW_COMP}
    m_d = sum(discharge.values())
    n_d = sum(discharge[k] / MW_COMP[k] for k in MW_COMP)
    m_suc = sum(suction.values())

    # ----- the discharge heat balance -> TT-322012 ------------------------------------------
    #     T_d = (m_mot.cp_N.T_mot + m_suc.cp_C.T_suc) / (m_d.cp_D)
    #
    # cp-weighted on BOTH sides. The literal mass-only denominator (m_mot + m_suc) is
    # dimensionally an enthalpy rather than a temperature and breaks the design pin, so the
    # dimensionally correct form is the one carried and cp_D is the number back-solved to
    # hold the design TT-322012. The capped `m_suc` above is what drives it, so a choked
    # throat shows up in the temperature as well as in the flow.
    t_d = (motive_nh3_kgh * CP_MOTIVE * t_motive_c
           + m_suc * CP_CARBAMATE * T_SUCTION_DES_C) / (m_d * CP_DISCHARGE)

    return EjectorResult(
        comp_kgh=discharge,
        total_kgh=m_d,
        mol_kmolh=n_d,
        suction_kgh=m_suc,
        mw=(m_d / n_d if n_d else 0.0),
        t_c=t_d,
        p_bara=p_d,
        rho=RHO_DISCHARGE,
        vol_m3h=m_d / RHO_DISCHARGE,
        mu=m_suc / motive_nh3_kgh,
        phi_spindle=phi_spindle,
        stalled=bool(live["stalled"]),
        cavitating=bool(live["cavitating"]),
    )


def spindle_phi(hv_open_pct: float) -> float:
    """HV-322602's own capacity characteristic [-]: the entrainment the jet makes at the live
    nozzle area over what it makes at the design area, both at the design motive and pressures.

    Process utility
    ---------------
    What the two spindle couplings of the synthesis loop attribute to the spindle and to nothing
    else: the forward-carbamate pulse into 322R001 on an HV-322602 move and 322E003's spindle duty.
    It is deliberately not the machine's total capacity ratio (`EjectorResult.phi_spindle`), which
    a 0.1 % motive deviation moves about tenfold, so a design-held HIC-322602 would read as a
    spindle move and drift the reactor's level.

    Equation
    --------
        phi_sp = m_suc(A_t(theta)) / m_suc(A_t,des),   A_t = A_t,des (40 + 0.6 theta) / A_full
    on the design motive and the design suction and discharge pressures; exactly 1.0 at the
    design opening, where the two calls are the same expression on the same operands.

    Source: V1 ``main.py`` ``ej_spindle_phi`` (Phase 4b, finding D-6).
    """
    open_eff = clamp(hv_open_pct, OPEN_MIN_PCT, 100.0)
    a_t = A_T_DES_M2 * (40.0 + 0.6 * open_eff) / SPINDLE_A_FULL_PCT
    live = jet_pump.entrainment_kgh(MOTIVE_DES_KGH, P_SUCTION_DES_BARA, P_DISCHARGE_DES_BARA,
                                    a_t, A_M_M2, NH3_RHO, RHO_SUCTION, RHO_DISCHARGE)["kgh"]
    ref = jet_pump.entrainment_kgh(MOTIVE_DES_KGH, P_SUCTION_DES_BARA, P_DISCHARGE_DES_BARA,
                                   A_T_DES_M2, A_M_M2, NH3_RHO, RHO_SUCTION, RHO_DISCHARGE)["kgh"]
    return (live / ref) if ref > 0.0 else 0.0


#: The design evaluation, produced by calling the model at its own design state rather than
#: entered as a vector. 322E002's design anchor reads it, so the two units cannot disagree
#: about what the design discharge is, and a change to the geometry or to the motive
#: composition reaches the condenser automatically.
DESIGN = ejector_322f001(MOTIVE_DES_KGH, MOTIVE_T_DES_C, OPEN_DES_PCT)

#: Design discharge total [kg/h] and TT-322012 at design [deg C].
DISCHARGE_DES_KGH = DESIGN.total_kgh
T_DISCHARGE_DES_C = DESIGN.t_c


__all__ = [
    "EjectorResult",
    "ejector_322f001",
    "spindle_phi",
    "DESIGN",
    "DISCHARGE_DES_KGH",
    "T_DISCHARGE_DES_C",
]
