"""The species layer every urea-liquor stage integrates — shared by units 323 and 324.

What this models
----------------
One well-mixed liquor stage's composition, tick by tick: the bubble point it is driven toward,
the vapour it boils off, the biuret it makes, and the species holdup that results. The stage's
total mass and energy balances belong to the stage's own module; this layer rides on them and
never re-derives the total, so it cannot perturb them.

    d(M . w_i)/dt = m_in . w_in,i - m_liq . w_i - m_vap . y_i + nu_i . xi

Every relation here is written as a DEPARTURE from the stage's design point
(`thermo.urea_liquor.LiquorStage`): a live rigorous value minus the same rigorous value at the
design state, added to the licensor's design number. At the design state each bracket is a
literal zero or a literal one, so the PFD is reproduced bit-exactly, and away from it the model
supplies the slope — which is what the model is good for — while the licensor supplies the
level, which is measured plant data.

Source
------
Ported from V1 ``backend/main.py``: ``sol_bubble_t_dep``, ``sol_vapour_y_vle``,
``sol_biuret_xi`` and ``sol_advance`` (reports TD-014, A-11, B-8, F-8, TD-009, F-11).

What changed in the port, and why it is not a physics change
------------------------------------------------------------
V1 keeps three module-level dictionaries — the two design memos and ``SOL_VLE_DOMAIN``, which
every vapour call WRITES as a side effect so the tick packet can report which stages stood on
the rigorous surface. The memos are now fields of the stage's `LiquorStage` record, built once
at import, and the domain is RETURNED beside the vapour composition instead of written to a
global. The numbers are identical; only where they live has moved.
"""

from __future__ import annotations

import math

from ureasim.core.units_of_measure import ABSOLUTE_ZERO_C
from ureasim.data.unit_322e001 import BIURET_EA_JMOL, BIURET_R_GAS_J
from ureasim.data.unit_323 import BIURET_ORDER
from ureasim.thermo import service
from ureasim.thermo.domains import MW, NONVOLATILE
from ureasim.thermo.urea_liquor import (
    MASS_FLOOR,
    MOLE_FLOOR,
    RIGOROUS_FAILURES,
    SOLUTION_SPECIES,
    LiquorStage,
    bubble_t_raoult,
    model_alpha,
    vapour_y,
)

#: A design-state model volatility below which a species has no reference to depart from [-].
#: V1's own threshold in `sol_vapour_y_vle`.
ALPHA_REF_FLOOR = 1.0e-30

#: Stoichiometric mass change per kmol of 2 Urea -> Biuret + NH3 [kg/kmol], by species.
_NU_KG = {"Urea": 2.0 * -MW["Urea"], "Biuret": MW["Biuret"], "NH3": MW["NH3"]}


def bubble_t(stage: LiquorStage, w: dict, p_bara: float) -> float:
    """A stage's live bubble point [deg C], in departure form, on its flash's own surface.

    Process utility
    ---------------
    The temperature a boiling stage walks its holdup toward. Taking the bubble point and the
    vapour composition off the same thermodynamic surface is what lets the stage's loop —
    composition to bubble point to boil-up to vapour to composition — settle where the
    physics puts it, rather than where two different models happen to cross (V1 finding A-11,
    a 2 C and 3.4-point urea miss at 323F010 before it was closed).

    Equation
    --------
        T_bub = T_sp + [ T_bub,rigorous(w, P) - T_bub,rigorous(w_des, P_des) ]

    and when the rigorous surface refuses the state, the matched Raoult pair:

        T_bub = T_sp + [ T_bub,Raoult(P, w) - T_bub,Raoult(P_des, w_des) ]

    At the design composition and pressure the bracket is a literal 0.0.
    """
    if stage.tbub_des_c is not None:
        try:
            return stage.t_des_c + (service.bubble_t(w, p_bara) - stage.tbub_des_c)
        except RIGOROUS_FAILURES:
            pass
    return stage.t_des_c + (bubble_t_raoult(p_bara, w) - stage.tbub_raoult_des_c)


def vapour(stage: LiquorStage, w: dict, t_c: float, p_bara: float) -> tuple[dict, str | None]:
    """Vapour mass fractions leaving a stage, and the rigorous domain they stood on.

    Process utility
    ---------------
    What the stage sends overhead — to the LP carbamate condenser, the flash condenser or the
    vacuum system — and therefore how much ammonia and CO2 each stage recovers. V1 once held
    this as a frozen vector with zero derivative in T, P and w; measured, that let the
    323F010 liquor settle at 76.6 % urea against the 80.0 % product spec.

    Equation
    --------
        alpha_i(live) = alpha_i,PFD . [ alpha_i,model(T, P, w) / alpha_i,model(design) ]
        y_i           = alpha_i . w_i / sum_j alpha_j . w_j

    The licensor's absolute split is kept and the model supplies only how it moves: the raw
    flash is 37 to 55 % low on ammonia against the PFD rows, while its slope is sound. Urea,
    biuret and formaldehyde are zeroed outright — K == 0 by structure, not by bias.

    Returns the domain as None whenever the stage fell back to its frozen vector: a state off
    the fitted envelope, a stage whose design state is itself off-envelope, or a liquor with no
    volatile left. That is published, so a stage on the fallback is visible, not assumed.
    """
    alpha = stage.anchor.alpha
    ref = stage.alpha_model_des
    if ref is None:
        return vapour_y(w, alpha), None
    try:
        live, domain = model_alpha(w, t_c, p_bara)
    except RIGOROUS_FAILURES:
        return vapour_y(w, alpha), None
    a = {}
    for k in SOLUTION_SPECIES:
        if k in NONVOLATILE:
            a[k] = 0.0                               # K == 0 by structure, not by model bias
        elif ref[k] > ALPHA_REF_FLOOR:
            a[k] = alpha[k] * (live[k] / ref[k])     # == alpha[k] exactly at the design state
        else:
            a[k] = alpha[k]                          # no design-state reference to depart from
    if sum(a[k] * w.get(k, 0.0) for k in SOLUTION_SPECIES) <= MOLE_FLOOR:
        return vapour_y(w, alpha), None              # degenerate: no volatile left
    return vapour_y(w, a), domain


def biuret_extent(stage: LiquorStage, m_kg: float, w: dict, t_c: float) -> float:
    """Biuret formed in a stage [kmol/h], 2 Urea -> Biuret + NH3.

    Process utility
    ---------------
    Biuret is the product-quality specification that only ever gets worse, and every warm
    stage adds to it; V1's back-solve of the PFD puts 0.66 kmol/h at 323C003 and none at the
    323F004 flash or at 323F010, whose rows carry a biuret excess instead (handoff B-20), with
    the two evaporators making most of the rest. It
    scales with the holdup (residence), with the urea fraction squared and with temperature, so
    a stage run hotter, fuller or more concentrated makes more.

    Equation
    --------
        xi = xi_des . (M / M_des) . (w_U / w_U,des)^2
                    . exp[ (Ea / R) . (1/T_des - 1/T) ]

    Every factor is exactly 1.0 at the design state. A stage whose design extent is zero makes
    none at any state.
    """
    a = stage.anchor
    if a.xi <= 0.0:
        return 0.0
    r_hold = max(m_kg, 0.0) / stage.m_des_kg
    r_urea = (w.get("Urea", 0.0) / stage.w_des["Urea"]) ** BIURET_ORDER
    r_arrh = math.exp((BIURET_EA_JMOL / BIURET_R_GAS_J)
                      * (1.0 / (stage.t_des_c + ABSOLUTE_ZERO_C)
                         - 1.0 / (t_c + ABSOLUTE_ZERO_C)))
    return a.xi * r_hold * r_urea * r_arrh


def advance_species(w: dict, m_pre_kg: float, m_new_kg: float, m_in_kgh: float, w_in: dict,
                    m_vap_kgh: float, y: dict, m_liq_kgh: float, xi_kmolh: float, dt: float,
                    m_in2_kgh: float = 0.0, w_in2: dict = None) -> dict:
    """Integrate one stage's species holdup by one step and return its new composition.

    Process utility
    ---------------
    Carries composition down the train as a tracked quantity, so a change in the stripper's
    efficiency reaches the product: the ammonia 322E001 fails to strip arrives at 323C003,
    the ammonia 323C003 fails to boil off arrives at 323F004, and so on. The total holdup is
    taken from the stage's own mass balance — both ``m_pre_kg`` and ``m_new_kg`` — so this can
    never re-derive or disturb it.

    Equation
    --------
        (M . w_i)_new = M_pre . w_i + [ m_in . w_in,i + m_in2 . w_in2,i - m_vap . y_i
                                        - m_liq . w_i + nu_i . xi ] . dt / 3600
        w_new         = (M . w)_new / sum (M . w)_new          (C6: sum w == 1)

    Each species holdup is floored at zero. A stage with nothing left keeps its composition.
    """
    out = {}
    for k in SOLUTION_SPECIES:
        m_k = (m_pre_kg * w.get(k, 0.0)
               + (m_in_kgh * w_in.get(k, 0.0)
                  + (m_in2_kgh * w_in2.get(k, 0.0) if w_in2 else 0.0)
                  - m_vap_kgh * y.get(k, 0.0) - m_liq_kgh * w.get(k, 0.0)
                  + _NU_KG.get(k, 0.0) * xi_kmolh) / 3600.0 * dt)
        out[k] = max(m_k, 0.0)
    tot = sum(out.values())
    if tot <= MASS_FLOOR or m_new_kg <= MASS_FLOOR:
        return dict(w)
    return {k: out[k] / tot for k in SOLUTION_SPECIES}


__all__ = [
    "ALPHA_REF_FLOOR",
    "bubble_t",
    "vapour",
    "biuret_extent",
    "advance_species",
]
