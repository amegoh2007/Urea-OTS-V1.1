"""The six-species urea liquor: its bubble point, its vapour, and a stage's design anchor.

What this models
----------------
Every stage between the stripper bottoms and the urea melt — 323C003, 323F004, 323F010 in the
LP recirculation, 324E001 and 324E003 in the evaporation — holds the same liquid: urea, biuret,
ammonia, carbon dioxide, water and a trace of formaldehyde from the UF85 dosing. This module is
that liquor's physics, with no plant knowledge in it: what boils it, what leaves it as vapour,
and how a stage's design point is read off the licensor's stream table.

The species balance every stage integrates is

    d(M . w_i)/dt = m_in . w_in,i - m_liq . w_i - m_vap . y_i + nu_i . xi ,    sum w = sum y = 1

and the pieces of it that are properties of the liquor, rather than of a vessel, live here:

  * the **bubble point**, rigorous from `thermo.service` and Raoult-on-water as the fallback;
  * the **vapour composition**, by relative volatility and the C6 summation
    ``y_i = alpha_i . w_i / sum_j alpha_j . w_j``;
  * the **design back-solve** — the biuret extent and the relative volatilities that make a
    stage close exactly on its PFD rows.

Everything is anchored. At the design liquid composition the vapour is the design vapour, every
species flow is its design value and dw/dt is zero, so this layer cannot move the heat and
material balance.

Source
------
Ported from V1 ``backend/main.py``, the "solution species" block (``MW_SOL`` through
``sol_advance``, lines 2340-2930), with its report references: TD-014 (the bubble point), A-11
(one thermodynamic surface per loop), B-8 (the rigorous vapour departure), F-11 (323F010's
second feed) and G3 (the melt reconciliation). The compositions it is anchored on are the PFD
rows in ``Combined_1750_MTPD_100% load_PFD TablesProcess_Data.md``, carried in
`ureasim.data.unit_323`.

A note on formaldehyde's molar mass. The PFD's own molar-mass column lists formaldehyde at
32.031, and `thermo.domains.MW` carries that number. CH2O is 30.026. The PFD is the strict
design basis and the species is at most 0.5 wt% anywhere, so the design value is kept.
"""

from __future__ import annotations

from dataclasses import dataclass

from ureasim.thermo import iapws, service
from ureasim.thermo.domains import MW, NONVOLATILE, OutOfDomain

#: The liquor's species, in the order every balance and every sum runs over them. The order is
#: load-bearing: each total is a float addition, and V1 adds them in exactly this order.
SOLUTION_SPECIES = ("Urea", "Biuret", "NH3", "CO2", "H2O", "HCHO")

#: Species the design BACK-SOLVE treats as never leaving in the vapour. Urea is deliberately not
#: in this set: the back-solve gives it a small apparent volatility (323C003 and 323F010), which
#: the runtime zeroes through `thermo.domains.NONVOLATILE` instead — see `stage_anchor`.
#: Source: V1 `main.py` SOL_NONVOL.
ANCHOR_NONVOLATILE = ("Biuret", "HCHO")

#: The failures the rigorous surface signals when a state is off its fitted envelope. Each one
#: sends the caller to its anchored fallback rather than stopping the engine.
RIGOROUS_FAILURES = (OutOfDomain, ValueError, ZeroDivisionError)

#: Numerical floors, all V1's own. None of them binds at a physical state.
MASS_FLOOR = 1e-12          # a stage outflow or a species fraction [kg/h or -]
MOLE_FLOOR = 1e-15          # a total mole or alpha-weighted sum [-]
VAPOUR_FLOOR = 1e-9         # an overhead flow worth back-solving [kg/h]
X_WATER_FLOOR = 1e-6        # the water mole fraction under the Raoult bubble point [-]


def reconcile_melt(w_in: dict, m_in: float, m_out: float, w_out_tab: dict) -> dict:
    """An atom-consistent outlet liquor row from a rounded PFD row and its feed.

    Process utility
    ---------------
    The PFD rounds each stream row to two decimals, and across a flash or an evaporator that is
    enough for a tabulated outlet to hold more of a species than its feed supplies. A design
    back-solve on such a row asks for negative vapour, which it would have to clip — a design
    point that does not close. This caps every species at its conservation limit, so the
    back-solve closes on the licensor's hard numbers (the urea strength and the flows).

    Equation
    --------
        cap_i = m_in . w_in,i / m_out
        w_i   = cap_i                      for biuret and formaldehyde (conserved exactly)
        w_i   = min(w_tab,i, cap_i)         for urea, NH3 and CO2 (cannot concentrate up)
        w_H2O = 1 - sum of the others, and the row is renormalised.

    V1's own comment lists urea with the conserved species; its code, ported here, does not.
    At 323F004 the two agree to the table's rounding.

    Source: V1 `main.py` `_reconcile_melt` (report G3).
    """
    out = {}
    for k in SOLUTION_SPECIES:
        if k == "H2O":
            continue
        conserved = m_in * w_in.get(k, 0.0) / max(m_out, MASS_FLOOR)
        out[k] = conserved if k in ANCHOR_NONVOLATILE else min(w_out_tab.get(k, 0.0), conserved)
    out["H2O"] = max(1.0 - sum(out.values()), 0.0)
    tot = sum(out.values())
    return {k: out[k] / tot for k in SOLUTION_SPECIES}


def close_urea_on_drain(w_in: dict, m_in: float, m_out: float, w_out_tab: dict) -> dict:
    """A stage's liquid outlet row with its urea closed against the feed: all of it leaves by the
    drain [mass fractions].

    Process utility
    ---------------
    Urea does not boil. Where the PFD's rounding leaves a stage's outlet holding less urea than
    its feed less the biuret it makes, a design back-solve sends the remainder overhead as an
    apparent volatility the runtime then zeroes, and the stage's design state is not a fixed
    point: the urea stays in the liquor and the stage drifts off its seed. Closing the remainder
    into the outlet, water giving way, makes the design seed stationary (decided 2026-10-10,
    handoff B-20).

    Equation
    --------
        xi      = max( (m_out . w_tab,B - m_in . w_in,B) / MW_B , 0 )     the biuret the rows make
        w_U     = (m_in . w_in,U - 2 . MW_U . xi) / m_out
        w_H2O   = 1 - sum of the others,                every other species the table's

    The outlet's mass flow is the PFD's; only its urea and water exchange.
    """
    xi = max((m_out * w_out_tab.get("Biuret", 0.0) - m_in * w_in.get("Biuret", 0.0))
             / MW["Biuret"], 0.0)
    out = {k: w_out_tab.get(k, 0.0) for k in SOLUTION_SPECIES if k != "H2O"}
    out["Urea"] = (m_in * w_in.get("Urea", 0.0) - 2.0 * MW["Urea"] * xi) / max(m_out, MASS_FLOOR)
    out["H2O"] = 1.0 - sum(out.values())
    return {k: out[k] for k in SOLUTION_SPECIES}


def x_water_mol(w: dict) -> float:
    """Water mole fraction of the liquor, from its mass fractions.

    Process utility
    ---------------
    Urea, biuret and formaldehyde raise the boiling point by diluting the water on a MOLE basis,
    so the mass vector has to be converted before Raoult's law can be applied to it.
    """
    n = {k: w.get(k, 0.0) / MW[k] for k in SOLUTION_SPECIES}
    tot = sum(n.values())
    return n["H2O"] / tot if tot > MOLE_FLOOR else 1.0


def bubble_t_raoult(p_bara: float, w: dict) -> float:
    """Bubble point [deg C] of a liquor whose only volatile is water, by Raoult's law.

    Process utility
    ---------------
    The fallback bubble point, used when the rigorous surface refuses a state. Nothing is
    fitted: the dissolved solids raise the boiling point purely by diluting the water, and V1
    measured this reproducing 88 to 99 % of a 20 to 90 C elevation on the 323F010 and 324 PFD
    triplets. The residual is the non-ideality, and every caller absorbs it by taking the
    DEPARTURE from this same function at the design composition, so only the slope matters.

    Not valid on its own for 323C003 and 323F004, whose liquors carry NH3 and CO2; there it
    overshoots by 33 and 16 C, which is why those stages use it only as a matched departure.

    Equation
    --------
        Psat(T_bub) = P / x_H2O       =>      T_bub = Tsat(P / x_H2O)

    A liquor with almost no water left asks for Tsat above water's critical pressure, where
    there is no boiling liquid; the bubble point is then held at the critical temperature.

    Source: V1 `main.py` `bubble_T_raoult` (report TD-014).
    """
    return iapws.tsat_c(min(p_bara / max(x_water_mol(w), X_WATER_FLOOR),
                            iapws.P_CRIT_MPA * 10.0))


def vapour_y(w: dict, alpha: dict) -> dict:
    """Vapour mass fractions leaving a liquor, by relative volatility — the C6 summation.

    Process utility
    ---------------
    The vapour is not a free vector: it is set by the liquid it boils off. With alpha
    back-solved at the design point this returns the design vapour exactly at the design
    liquid, and moves with the liquid everywhere else.

    Equation
    --------
        y_i = alpha_i . w_i / sum_j alpha_j . w_j          (so sum y == 1 by construction)

    A liquor with no volatile left returns pure water vapour.

    Source: V1 `main.py` `sol_vapour_y`.
    """
    num = {k: alpha[k] * w.get(k, 0.0) for k in SOLUTION_SPECIES}
    tot = sum(num.values())
    if tot <= MOLE_FLOOR:
        return {k: (1.0 if k == "H2O" else 0.0) for k in SOLUTION_SPECIES}
    return {k: num[k] / tot for k in SOLUTION_SPECIES}


def model_alpha(w: dict, t_c: float, p_bara: float) -> tuple[dict, str]:
    """Mass-basis relative volatility from the rigorous gamma-phi flash, and its domain.

    Process utility
    ---------------
    The SLOPE of the vapour split with temperature, pressure and composition. The licensor's
    back-solved alpha fixes the split at design; this supplies how it moves. Any common factor
    cancels in the ratio the caller takes, so no normalisation is needed.

    Equation
    --------
        alpha_i ~ y_i / w_i          from `thermo.service.flash(w, T, P)`

    Raises `OutOfDomain` when the flash does not converge, so the caller falls back.

    Source: V1 `main.py` `_sol_model_alpha`.
    """
    fr = service.flash(w, t_c, p_bara)
    if not fr.converged:
        raise OutOfDomain("flash did not converge at %s C / %s bar a" % (t_c, p_bara))
    out = {}
    for k in SOLUTION_SPECIES:
        wi = w.get(k, 0.0)
        out[k] = (fr.y.get(k, 0.0) / wi) if wi > MASS_FLOOR else 0.0
    return out, fr.domain


@dataclass(frozen=True)
class StageAnchor:
    """One stage's design point, back-solved from its PFD rows."""

    #: Biuret formation extent at design [kmol/h], 2 Urea -> Biuret + NH3.
    xi: float
    #: Design vapour mass fractions.
    y: dict
    #: Relative volatility against water [-]; water is 1 by definition.
    alpha: dict
    #: Negative vapour that had to be clipped to close the balance [kg/h]. Reported, never hidden.
    resid: float
    #: Mass fraction of the overhead that is entrained LIQUOR rather than vapour [-].
    entrain: float


def stage_anchor(w_in: dict, w_out: dict, m_in: float, m_vap: float, m_liq: float,
                 w_in2: dict = None, m_in2: float = 0.0, entrain: bool = False) -> StageAnchor:
    """Back-solve a stage's design biuret extent and relative volatilities from its PFD rows.

    Process utility
    ---------------
    Makes a stage close EXACTLY on the licensor's stream table: whatever the feed brings in,
    less the liquid out, less what the biuret reaction consumes and makes, is the vapour — and
    the vapour's composition against the liquid's is the volatility. A stage with a second
    inlet (323F010 takes the granulation return, PFD 331, beside stream 319) sums the two feeds
    first.

    Equations
    ---------
        xi     = max( (m_liq . w_B - m_in,B) / MW_B , 0 )
        vap_i  = m_in,i + nu_i . xi - m_liq . w_i - f . m_vap . w_i      (nu: urea -2, biuret +1, NH3 +1)
        y_i    = vap_i / ((1 - f) . m_vap)          water closes the balance as the reference
        alpha_i = (y_i / w_i) / (y_H2O / w_H2O)

    ``entrain`` is for a stage whose PFD overhead lists urea, which cannot evaporate and
    therefore left as droplets of the vessel's own liquor. The carryover fraction f and the
    extent then close urea and biuret together, because the droplets carry biuret too:

        urea:    m_in,U - 2 . MW_U . xi - m_liq . w_U - f . m_vap . w_U = 0
        biuret:  m_in,B +     MW_B . xi - m_liq . w_B - f . m_vap . w_B = 0

    unless that asks for a negative extent, in which case xi = 0 and f closes urea alone.

    Source: V1 `main.py` `_sol_stage_anchor` (reports F-11, G3).
    """
    m_i = {k: m_in * w_in[k] + (m_in2 * w_in2[k] if w_in2 else 0.0) for k in SOLUTION_SPECIES}
    xi = max((m_liq * w_out["Biuret"] - m_i["Biuret"]) / MW["Biuret"], 0.0)
    f_ent = 0.0
    if entrain and m_vap > VAPOUR_FLOOR:
        r_ub = 2.0 * MW["Urea"] / MW["Biuret"]
        a_u = m_i["Urea"] - m_liq * w_out["Urea"]
        b_b = m_i["Biuret"] - m_liq * w_out["Biuret"]
        f_ent = max((a_u + r_ub * b_b) / (m_vap * (w_out["Urea"] + r_ub * w_out["Biuret"])), 0.0)
        xi = (f_ent * m_vap * w_out["Biuret"] - b_b) / MW["Biuret"]
        if xi < 0.0:
            # 323F010: the biuret rows leave no room for formation (5 kg/h more biuret in than
            # out, inside the 0.005 wt% rounding of a 101 t/h feed), so the carryover closes
            # urea alone.
            xi = 0.0
            f_ent = max(a_u / (m_vap * w_out["Urea"]), 0.0)
    gen = {k: 0.0 for k in SOLUTION_SPECIES}
    gen["Biuret"] = +xi * MW["Biuret"]
    gen["Urea"] = -xi * 2.0 * MW["Urea"]
    gen["NH3"] = +xi * MW["NH3"]
    vap = {k: m_i[k] + gen[k] - m_liq * w_out[k] - f_ent * m_vap * w_out[k]
           for k in SOLUTION_SPECIES}
    if f_ent > 0.0:
        vap["Urea"] = 0.0                       # closed by construction; kill the round-off
    resid = sum(v for v in vap.values() if v < 0.0)
    for k in SOLUTION_SPECIES:
        if k in ANCHOR_NONVOLATILE or vap[k] < 0.0:
            vap[k] = 0.0
    m_v = (1.0 - f_ent) * m_vap                 # the part of the overhead that is vapour
    vap["H2O"] += m_v - sum(vap.values())       # water closes the balance (reference species)
    y = {k: vap[k] / m_v for k in SOLUTION_SPECIES} if m_v > VAPOUR_FLOOR else dict(w_out)
    aw = y["H2O"] / w_out["H2O"]
    alpha = {k: ((y[k] / w_out[k]) / aw if (w_out[k] > MASS_FLOOR and k not in ANCHOR_NONVOLATILE)
                 else 0.0)
             for k in SOLUTION_SPECIES}
    alpha["H2O"] = 1.0                          # reference species, by definition
    return StageAnchor(xi=xi, y=y, alpha=alpha, resid=resid, entrain=f_ent)


def design_bubble_t(w_des: dict, p_bara: float) -> float | None:
    """A stage's design bubble point on the rigorous surface, or None if it is off-envelope.

    Process utility
    ---------------
    The zero of the stage's departure bubble point. Computed once, at the design composition,
    so that the live call at the design state returns the identical float and the departure is
    a literal 0.0 there. None sends the stage to its Raoult pair for good.

    Source: V1 `main.py` `_sol_tbub_anchor`.
    """
    try:
        return service.bubble_t(w_des, p_bara)
    except RIGOROUS_FAILURES:
        return None


def design_model_alpha(w_des: dict, t_c: float, p_bara: float) -> dict | None:
    """A stage's model volatility at its design state, or None if that state is off-envelope.

    Process utility
    ---------------
    The denominator of the stage's departure vapour split, taken at exactly the (w, T, P)
    triplet the licensor's alpha was back-solved from, so the ratio is 1.0 there.

    Source: V1 `main.py` `_sol_alpha_anchor`.
    """
    try:
        return model_alpha(w_des, t_c, p_bara)[0]
    except RIGOROUS_FAILURES:
        return None


@dataclass(frozen=True)
class LiquorStage:
    """Everything a stage's species layer is anchored on — built once, from the PFD."""

    #: Design liquid composition, which is the stage's own outlet row.
    w_des: dict
    #: The design back-solve.
    anchor: StageAnchor
    #: Design holdup [kg], temperature [deg C] and pressure [bar a].
    m_des_kg: float
    t_des_c: float
    p_des_bara: float
    #: Design bubble point on the rigorous surface, or None off-envelope.
    tbub_des_c: float | None
    #: Design bubble point on the Raoult fallback — the fallback's own anchor.
    tbub_raoult_des_c: float
    #: Model volatility at the design state, or None off-envelope.
    alpha_model_des: dict | None


def liquor_stage(w_in: dict, w_out: dict, m_in: float, m_vap: float, m_liq: float,
                 m_des_kg: float, t_des_c: float, p_des_bara: float,
                 w_in2: dict = None, m_in2: float = 0.0, entrain: bool = False) -> LiquorStage:
    """Build a stage's full design anchor from its PFD rows and its design state.

    Process utility
    ---------------
    One call per stage, at import: the back-solve, the two bubble-point zeros and the
    volatility zero, all taken on the stage's own design liquid (its outlet row) at its own
    design temperature and pressure.
    """
    return LiquorStage(
        w_des=w_out,
        anchor=stage_anchor(w_in, w_out, m_in, m_vap, m_liq,
                            w_in2=w_in2, m_in2=m_in2, entrain=entrain),
        m_des_kg=m_des_kg,
        t_des_c=t_des_c,
        p_des_bara=p_des_bara,
        tbub_des_c=design_bubble_t(w_out, p_des_bara),
        tbub_raoult_des_c=bubble_t_raoult(p_des_bara, w_out),
        alpha_model_des=design_model_alpha(w_out, t_des_c, p_des_bara),
    )


def stage_bubble_p(stage: LiquorStage, w: dict, t_c: float, p_bara: float) -> float:
    """A stage liquor's live bubble pressure at its temperature, at most the stage's own
    pressure [bar a] — the Pv its letdown valve flashes on.

    Process utility
    ---------------
    A liquor leaving a boiling stage is at, or near, its bubble point; its letdown drops it
    below that and it flashes in the valve. IEC 60534-2-1 then limits the flow to the choked
    differential FL^2 (P1 - FF . Pv), set by the upstream pressure and this vapour pressure, not
    by the vessel downstream (decided 2026-09-30, handoff B-46).

    Equation
    --------
    The exact inverse of the stage's departure bubble point (`units.liquor_stage.bubble_t`),
    ``T = T_sp + [T_bub(w, P) - T_bub(w_des, P_des)]``, solved for P:

        Pv = min(P_bub,rigorous(w, T - (T_sp - T_bub,des)), P)

    At the design state it is the design pressure, to the bubble-point solver's tolerance. Off
    the rigorous surface the liquor is taken as saturated at the stage's own pressure, P.

    The cap at P is the liquid the valve receives. A liquor whose bubble pressure exceeds the
    vessel's has boiled down to it in the vessel, so the valve sees at most saturated liquid —
    the domain of the IEC liquid law, whose FL^2 (P1 - FF . Pv) otherwise turns negative and
    falls back to the full differential, three times the design flow out of a superheated column
    (the stage's temperature and pressure relax on separate balances, so a feed cut can carry
    the bubble pressure 9 % over the column's).
    """
    if stage.tbub_des_c is not None:
        try:
            return min(service.bubble_p(w, t_c - (stage.t_des_c - stage.tbub_des_c)), p_bara)
        except RIGOROUS_FAILURES:
            pass
    return p_bara


__all__ = [
    "SOLUTION_SPECIES", "ANCHOR_NONVOLATILE", "NONVOLATILE", "RIGOROUS_FAILURES",
    "MASS_FLOOR", "MOLE_FLOOR", "VAPOUR_FLOOR", "X_WATER_FLOOR",
    "reconcile_melt", "close_urea_on_drain", "x_water_mol", "bubble_t_raoult", "vapour_y", "model_alpha",
    "StageAnchor", "stage_anchor", "design_bubble_t", "design_model_alpha",
    "LiquorStage", "liquor_stage", "stage_bubble_p",
]
