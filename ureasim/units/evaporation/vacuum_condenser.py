"""The saturated-vent vacuum condenser — unit 324's four surface condensers.

What this models
----------------
324E002, 324E005, 324E006 and 324E007: shell-and-tube condensers under the evaporators' vacuums,
cooling water in the tubes. The vapour condenses on the tubes; the inert gas, with what vapour it
can still hold, leaves the cold end for the ejectors. Three physical facts carry the model, each
V1's answer to a report on the stand-ins it replaced (A-13, B-9, B-13):

  * **The vent leaves saturated at the cold end.** Every PFD vent row off these condensers sits at
    water saturation at its own temperature and pressure (706: 29.4 mol % water at 45 C and
    0.33 bar a, p_H2O 0.097 against psat 0.096). So the gas that leaves is the inert gas plus the
    vapour it can hold at the cold end's temperature and the shell pressure, and the vent grows
    without bound as the shell pressure falls towards the vapour pressure there. NH3 and CO2
    carry their own partial pressures over the condensate the exchanger is making (the Extended
    UNIQUAC back-pressure of `thermo.ammonia_backpressure`), as a departure from design:

        p_w = Y_des s_w P_des . psat_w(T_v) / psat_w(T_v,des)
        p_k = max(Y_des s_k P_des + (p*_k(w_cond, T_v) - p*_k,des), 0)   p*_k,des <= Y_des s_k P_des
        p_k = Y_des s_k P_des . p*_k(w_cond, T_v) / p*_k,des              p*_k,des >  Y_des s_k P_des
                                                                              k = NH3, CO2
        y_c = (p_w + p_NH3 + p_CO2) / P,    n_vent,k = n_inert . y_c / (1 - y_c) . p_k / sum p

    the condensate taken at the inlet's condensable composition, p*_k,des its back-pressure at
    the design inlet and cold end. DECIDED 2026-10-02 (handoff B-67, option a): V1 multiplies on
    every species; 324E007's design ammonia back-pressure is 24 Pa against the PFD vent's
    1660 Pa, so the ratio multiplied any rise by 68 and, through a 323P003 trip, vented the
    condenser's whole inlet. DECIDED 2026-10-02 (handoff B-71): the addition carries the mirror
    hazard where the design back-pressure is far ABOVE the PFD's partial pressure — 324E007's
    CO2, 22.8 bar against 0.143 — so there V1's ratio stands. The rule falls per species at
    design: the addition on 324E002's NH3 and CO2, 324E006's NH3 and 324E007's NH3, V1's ratio
    on 324E005's NH3 and CO2, 324E006's CO2 and 324E007's CO2. Both forms are exact at design,
    so every condenser's design is unchanged. DECIDED 2026-10-09 (handoff B-87, option b): every
    species the vent carries, and the inerts that size it, is floored at zero, so the vent is
    never negative and the condensate never more than what arrives. V1 sums the inerts as they
    come; an inlet scaled 405 times past its row in Phase 7's cold start booked 1.9 kmol/h of N2
    below zero, and 324E005 vented -2.2e10 kg/h, the same amount booked as condensate.
  * **The cold end is where the heat balance meets the surface.**

        Q_bal(T_v) = H_gas(inlet, T_in) - H_gas(vent, T_v) - H_liq(condensate, T_v)
        Q_UA(T_v)  = UA . LMTD(T_in, T_v ; T_cw,in, T_cw,in + Q / (m_cw cp))

    on the H0 elements datum, per species (43.2 kJ/mol for water at 45 C, 33.6 for NH3, 16.3 for
    CO2), solved for T_v by Illinois regula falsi between the water inlet and the vapour inlet.
  * **The design is the PFD's by construction.** UA is back-solved per exchanger from the same
    balance at the PFD design point, and the published vent is the PFD's times the model's vent
    against the model's vent at design: exactly 1.0 there.

The four condensers' rows are `ureasim.data.unit_324`'s.

Source
------
V1 ``backend/vacuum_condenser.py``: ``condensate_fractions``, ``bp_bracket``, ``bp_at``,
``vent_moles`` (its condenser branch; the saturated-gas branch is `thermo.saturated_vent`'s),
``_q_balance``, ``_inlet_enthalpy``, ``solve``, ``_pack``, ``design_spec``, ``vent_kgh``,
``condensate_back_pressure``, ``vent_kgh_at``, and the lazily filled enthalpy grid (``_h``).
Ported verbatim, but for B-67's departure where B-71 puts it and B-87's floor; reports A-13, B-9,
B-13.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from functools import lru_cache

from ureasim.core.units_of_measure import PA_PER_BAR
from ureasim.data.unit_324 import (
    CONDENSER_ROWS,
    CW_CP_KJKG_K,
    PFD_324_MOL_PCT,
    VAC_PFD_KMOLH,
    VACUUM_CONDENSERS,
)
from ureasim.thermo import enthalpy as h0
from ureasim.thermo import iapws
from ureasim.thermo.ammonia_backpressure import back_pressure
from ureasim.thermo.saturated_vent import (
    CARRIED,
    CONDENSABLE,
    INERT,
    MW,
    SPECIES,
    Y_MAX,
    moles_from_mole_pct,
)

#: The enthalpy grid's step [K]: each species' H0 enthalpy is read off lazily filled nodes 0.05 K
#: apart, linear between them — a pure function of T, so the design solve stays reproducible, and
#: with Cp moving under 1 J/(mol K) per K the interpolation error is below 1e-4 J/mol.
H_STEP_K = 0.05
_H_GRID: dict = {}

#: Half the band the condensate's back-pressure is bracketed over [K].
BP_HALF_BAND_K = 2.0

#: The falsi: the margin inside the water and vapour inlets [K], the residual [kW] and bracket [K]
#: it stops at, its iteration cap, and how often the back-pressure bracket may be re-centred.
FALSI_EDGE_K = 1.0e-6
FALSI_TOL_KW = 1.0e-6
FALSI_TOL_K = 1.0e-8
FALSI_ITERS = 60
RECENTRE_ATTEMPTS = 4

#: Guards V1 writes as literals: a pressure in a ratio [bar a], two equal end differences [K].
P_FLOOR_BARA = 1.0e-9
LMTD_EQUAL_K = 1.0e-12


# ======================================================================================
# Enthalpies, the LMTD and the condensate
# ======================================================================================

def _h_node(k: str, phase: str, i: int) -> float:
    key = (k, phase, i)
    v = _H_GRID.get(key)
    if v is None:
        v = h0.h_species(k, phase, i * H_STEP_K)
        _H_GRID[key] = v
    return v


def _h(k: str, phase: str, t_c: float) -> float:
    """A species' H0 enthalpy [J/mol] off the 0.05 K grid, linear between nodes."""
    x = (t_c + 273.15) / H_STEP_K
    i = math.floor(x)
    f = x - i
    h_lo = _h_node(k, phase, i)
    return h_lo + f * (_h_node(k, phase, i + 1) - h_lo)


def _h_gas(k: str, t_c: float) -> float:
    return _h(k, h0.reference_phase(k, "vapour"), t_c)


def _h_liq(k: str, t_c: float) -> float:
    return _h(k, h0.reference_phase(k, "liquid"), t_c)


def lmtd(hot_in: float, hot_out: float, cold_in: float, cold_out: float) -> float:
    """Counter-current LMTD [K], zero across a crossed or touching end (V1 ``_lmtd``)."""
    d1, d2 = hot_in - cold_out, hot_out - cold_in
    if d1 <= 0.0 or d2 <= 0.0:
        return 0.0
    if abs(d1 - d2) <= LMTD_EQUAL_K:
        return 0.5 * (d1 + d2)
    return (d1 - d2) / math.log(d1 / d2)


def condensate_fractions(n_in: dict) -> dict:
    """Mass fractions of what a condenser makes, taken at its inlet's condensable composition.

    Process utility
    ---------------
    The liquor the cold end's NH3 and CO2 pressures are read over. While the vent carries a few
    per cent of the condensables, the condensate is the inlet's condensables, and an ammonia-rich
    inlet raises p_NH3 more than in proportion, because less of it is bound to CO2.
    """
    m = {k: max(n_in.get(k, 0.0), 0.0) * MW[k] for k in CONDENSABLE + CARRIED}
    tot = sum(m.values())
    return {k: v / tot for k, v in m.items()} if tot > 0.0 else {}


def bp_bracket(w_cond: dict, t_c: float) -> tuple:
    """The condensate's back-pressure at ``t_c`` and BP_HALF_BAND_K either side.

    Process utility
    ---------------
    One bracket for a whole solve: the back-pressure grid's nodes cost three speciations each the
    first time a run reaches them, and three anchors that move only as the cold end moves are
    nodes the run almost always holds already.
    """
    return (t_c, back_pressure(w_cond, t_c - BP_HALF_BAND_K), back_pressure(w_cond, t_c),
            back_pressure(w_cond, t_c + BP_HALF_BAND_K))


def bp_at(bracket: tuple, t_c: float) -> tuple:
    """A bracket read at ``t_c``: log-linear through its anchors, the same slope outside them.

    Process utility
    ---------------
    The partial pressures are very nearly exponential in T, so over 2 K this is good to a few parts
    in 1e5; at the centre it returns that anchor itself, which keeps the design point bit-exact.
    """
    t0, lo, mid, hi = bracket
    if t_c == t0:
        return mid
    if t_c > t0:
        f, a, b = (t_c - t0) / BP_HALF_BAND_K, mid, hi
    else:
        f, a, b = (t0 - t_c) / BP_HALF_BAND_K, mid, lo
    return tuple(a[i] * (b[i] / a[i]) ** f for i in range(len(a)))


# ======================================================================================
# The design spec
# ======================================================================================

@dataclass(frozen=True)
class CondenserSpec:
    """One condenser anchored on its PFD rows (V1 ``design_spec``'s dictionary, typed)."""

    tag: str
    #: The design shell pressure [bar a], the inlet's and the cold end's temperatures [deg C].
    p_des: float
    t_in_des: float
    t_v_des: float
    #: The vent row's condensable mole fraction, its split, water's vapour pressure at T_v,des.
    y_des: float
    split: dict
    psat_v_des: float
    #: The cooling water at design [kg/h, deg C] and its heat capacity [kJ/(kg K)].
    cw_flow_kgh: float
    cw_in_c: float
    cw_cp: float
    #: The design inlet [kmol/h], and the PFD's inlet and vent [kg/h].
    n_in_des: dict
    inlet_kgh: float
    vent_kgh: float
    #: The condensate's back-pressure at design [Pa], (p_NH3, p_CO2, slopes).
    bp_des: tuple = ()
    #: The back-solved UA [kW/K] and design duty [kW]; the model's vent at design [kg/h] and the
    #: cold end the design solve settles at [deg C].
    ua_kw_k: float = 0.0
    q_des_kw: float = 0.0
    vent_model_des_kgh: float = 0.0
    t_v_solved_des: float = 0.0


@dataclass(frozen=True)
class CondenserResult:
    """One solve (V1 ``_pack``): the cold end [deg C], the duty from the balance and through the
    surface [kW], the cooling water [deg C, kg/h], the vent [kmol/h], the model's vent, inlet and
    condensate [kg/h], and the LMTD [K]."""

    t_vent_c: float
    q_kw: float
    q_ua_kw: float
    cw_in_c: float
    cw_out_c: float
    cw_flow_kgh: float
    vent_kmolh: dict = field(default_factory=dict)
    vent_model_kgh: float = 0.0
    inlet_model_kgh: float = 0.0
    condensate_model_kgh: float = 0.0
    lmtd_k: float = 0.0


def vent_moles(spec: CondenserSpec, p_bara: float, t_v_c: float, n_in: dict,
               bp: tuple | None = None) -> dict:
    """The gas leaving the cold end [kmol/h]: every inert, plus the condensables it holds.

    Process utility
    ---------------
    The load the ejector behind the condenser must pull. A warmer cold end or a lower shell
    pressure lets more vapour through; an ammonia-rich inlet raises its own pressure over the
    condensate, by what its back-pressure rises above design (B-67), or in its proportion where
    the design back-pressure exceeds the PFD's partial pressure (B-71). ``bp`` is the condensate's back-pressure when the caller has paid for it already;
    without it, it is taken at this call's own temperature.

    Equations in the module docstring.
    """
    # B-87 (decided 2026-10-09): no species leaves below zero. An inlet scaled far past its row
    # (`condenser_node.inlet_kmolh`) can book an inert below zero, and the inerts' sum then turned
    # n_c, and the whole vent, negative: a vent drawing vapour back into the condenser, booked as
    # condensate created from nothing.
    n_i = sum(max(n_in.get(k, 0.0), 0.0) for k in INERT)
    ratio = spec.p_des / max(p_bara, P_FLOOR_BARA)
    y = spec.y_des * ratio * (iapws.psat_bara(t_v_c) / spec.psat_v_des)
    split = spec.split
    w_cond = condensate_fractions(n_in) if spec.bp_des else {}
    if w_cond:
        if bp is None:
            bp = back_pressure(w_cond, t_v_c)
        # B-71: a species whose design back-pressure exceeds the PFD's partial pressure keeps
        # V1's ratio; one below it takes B-67's departure, added to the PFD's partial pressure.
        p = max(p_bara, P_FLOOR_BARA)
        rel = {"H2O": y * split["H2O"]}
        for i, k in enumerate(("NH3", "CO2")):
            if spec.bp_des[i] > spec.y_des * split[k] * spec.p_des * PA_PER_BAR:
                rel[k] = spec.y_des * split[k] * ratio * (bp[i] / spec.bp_des[i])
            else:
                rel[k] = max(spec.y_des * split[k] * ratio
                             + (bp[i] - spec.bp_des[i]) / (PA_PER_BAR * p), 0.0)
        y = sum(rel.values())
        split = {k: rel[k] / y for k in CONDENSABLE} if y > 0.0 else split
    y = min(max(y, 0.0), Y_MAX)
    n_c = n_i * y / (1.0 - y)
    vent = {k: max(min(n_c * split[k], n_in.get(k, 0.0)), 0.0) for k in CONDENSABLE}
    for k in INERT:
        vent[k] = max(n_in.get(k, 0.0), 0.0)
    vent["Urea"] = 0.0
    return vent


def _q_balance(spec: CondenserSpec, p_bara: float, t_v: float, n_in: dict, h_in: float,
               bracket: tuple | None = None) -> tuple[float, dict]:
    """The heat the vapour gives up between its inlet and the cold end [kW], and the vent."""
    vent = vent_moles(spec, p_bara, t_v, n_in, bp_at(bracket, t_v) if bracket else None)
    q = h_in
    for k in SPECIES:
        nv = vent.get(k, 0.0)
        nc = n_in.get(k, 0.0) - nv
        if nv:
            q -= nv * _h_gas(k, t_v)
        if nc:
            q -= nc * _h_liq(k, t_v)
    return q * 1000.0 / 3600.0 / 1000.0, vent


def _inlet_enthalpy(n_in: dict, t_in: float) -> float:
    """The inlet's enthalpy [kmol/h x J/mol]: vapour species as gas, entrained liquor as liquid."""
    return sum(n * (_h_liq(k, t_in) if k in CARRIED else _h_gas(k, t_in))
               for k, n in n_in.items() if n)


def _pack(n_in: dict, vent: dict, t_v: float, q: float, cw_in: float, cw_out: float,
          q_ua: float, cw_flow: float, t_in: float) -> CondenserResult:
    vent_kgh = sum(vent.get(k, 0.0) * MW[k] for k in SPECIES)
    in_kgh = sum(n_in.get(k, 0.0) * MW[k] for k in SPECIES)
    return CondenserResult(
        t_vent_c=t_v, q_kw=q, q_ua_kw=q_ua, cw_in_c=cw_in, cw_out_c=cw_out, cw_flow_kgh=cw_flow,
        vent_kmolh=vent, vent_model_kgh=vent_kgh, inlet_model_kgh=in_kgh,
        condensate_model_kgh=in_kgh - vent_kgh,
        lmtd_k=lmtd(t_in, t_v, cw_in, cw_out) if q else 0.0)


def solve(spec: CondenserSpec, p_bara: float, n_in: dict, t_in_c: float, cw_flow_kgh: float,
          cw_in_c: float, ua_kw_k: float | None = None,
          t_v_prev: float | None = None) -> CondenserResult:
    """The cold end, vent and condensate of one condenser at a live shell pressure.

    Process utility
    ---------------
    What the condenser hands its ejector and its condensate line. Less cooling water, warmer
    water or a fouled surface lift the cold end and with it the vent; a falling shell pressure
    swells the vent until it is the whole inlet.

    Method
    ------
    Illinois regula falsi on R(T_v) = Q_bal - UA . LMTD over (T_cw,in, T_in): R > 0 at the cold
    end, where the LMTD vanishes, and R < 0 at the hot end, where the vent holds everything. One
    back-pressure bracket for the whole falsi, centred on the cold end the condenser last settled
    at (the design outlet the first time); re-centred and repeated, at most four times, when the
    answer leaves it. No water, no surface or an inlet no warmer than the water: nothing
    condenses.
    """
    ua = spec.ua_kw_k if ua_kw_k is None else ua_kw_k
    h_in = _inlet_enthalpy(n_in, t_in_c)
    cp = spec.cw_cp
    w_cond = condensate_fractions(n_in) if spec.bp_des else {}
    bracket = (bp_bracket(w_cond, spec.t_v_des if t_v_prev is None else t_v_prev)
               if w_cond else None)
    if cw_flow_kgh <= 0.0 or ua <= 0.0 or t_in_c <= cw_in_c:
        vent = {k: n_in.get(k, 0.0) for k in CONDENSABLE + INERT}
        vent["Urea"] = 0.0
        return _pack(n_in, vent, t_in_c, 0.0, cw_in_c, cw_in_c, 0.0, cw_flow_kgh, t_in_c)

    def resid(t_v):
        q, vent = _q_balance(spec, p_bara, t_v, n_in, h_in, bracket)
        cw_out = cw_in_c + max(q, 0.0) * 3600.0 / (cw_flow_kgh * cp)
        return q - ua * lmtd(t_in_c, t_v, cw_in_c, cw_out), q, vent, cw_out

    t_v = cw_in_c
    for _attempt in range(RECENTRE_ATTEMPTS):
        lo, hi = cw_in_c + FALSI_EDGE_K, t_in_c - FALSI_EDGE_K
        r_lo = resid(lo)[0]
        r_hi = resid(hi)[0]
        if r_lo <= 0.0:                 # the surface cools the vent to the water inlet
            t_v = lo
        elif r_hi >= 0.0:
            t_v = hi
        else:
            side = 0
            t_v = lo
            for _ in range(FALSI_ITERS):
                t_v = (lo * r_hi - hi * r_lo) / (r_hi - r_lo)
                r = resid(t_v)[0]
                if abs(r) <= FALSI_TOL_KW or hi - lo <= FALSI_TOL_K:
                    break
                if r > 0.0:
                    lo, r_lo = t_v, r
                    if side == 1:
                        r_hi *= 0.5
                    side = 1
                else:
                    hi, r_hi = t_v, r
                    if side == -1:
                        r_lo *= 0.5
                    side = -1
        if bracket is None or abs(t_v - bracket[0]) <= BP_HALF_BAND_K:
            break
        bracket = bp_bracket(w_cond, t_v)                        # the cold end left the band
    r, q, vent, cw_out = resid(t_v)
    return _pack(n_in, vent, t_v, q, cw_in_c, cw_out, ua * lmtd(t_in_c, t_v, cw_in_c, cw_out),
                 cw_flow_kgh, t_in_c)


def design_spec(tag: str, p_des: float, n_in_des: dict, t_in_des: float, vent_row: dict,
                t_v_des: float, cw_flow_kgh: float, cw_in_c: float, cw_cp: float,
                inlet_kgh_pfd: float, vent_kgh_pfd: float) -> CondenserSpec:
    """Anchor one condenser on its PFD rows and back-solve its UA from the H0 balance at design.

    Process utility
    ---------------
    Pins the one number the datasheets do not give on the model's own basis: UA = Q_bal / LMTD at
    the PFD's inlet, cold end and cooling water, so the design point is reproduced by
    construction (324E002: 18 019 kW against the 18 460 its cooling water carries, the H0 tier's
    missing mixing and carbamate heat).
    """
    y_c = sum(vent_row[k] for k in CONDENSABLE)
    spec = CondenserSpec(
        tag=tag, p_des=p_des, t_in_des=t_in_des, t_v_des=t_v_des,
        y_des=y_c / sum(vent_row[k] for k in CONDENSABLE + INERT),
        split={k: vent_row[k] / y_c for k in CONDENSABLE},
        psat_v_des=iapws.psat_bara(t_v_des), cw_flow_kgh=cw_flow_kgh, cw_in_c=cw_in_c,
        cw_cp=cw_cp, n_in_des=dict(n_in_des), inlet_kgh=inlet_kgh_pfd, vent_kgh=vent_kgh_pfd)
    spec = replace(spec, bp_des=back_pressure(condensate_fractions(n_in_des), t_v_des))
    h_in = _inlet_enthalpy(n_in_des, t_in_des)
    q_des, _ = _q_balance(spec, p_des, t_v_des, n_in_des, h_in)
    cw_out = cw_in_c + q_des * 3600.0 / (cw_flow_kgh * cw_cp)
    spec = replace(spec, ua_kw_k=q_des / lmtd(t_in_des, t_v_des, cw_in_c, cw_out),
                   q_des_kw=q_des)
    des = solve(spec, p_des, n_in_des, t_in_des, cw_flow_kgh, cw_in_c)
    return replace(spec, vent_model_des_kgh=des.vent_model_kgh, t_v_solved_des=des.t_vent_c)


@lru_cache(maxsize=1)
def design_specs() -> dict:
    """The four condensers anchored on their PFD rows, by tag (V1 ``VACUUM_CONDENSER_SPECS``).

    Each on its inlet row at its molar total, its vent row, its design shell pressure, its
    PFD inlet and cold-end temperatures, and its cooling water (`ureasim.data.unit_324`).
    """
    specs = {}
    for tag, (row_in, row_vent, p_des) in CONDENSER_ROWS.items():
        r = VACUUM_CONDENSERS[tag]
        specs[tag] = design_spec(
            tag, p_des, moles_from_mole_pct(VAC_PFD_KMOLH[row_in], PFD_324_MOL_PCT[row_in]),
            r.hot_in_c, PFD_324_MOL_PCT[row_vent], r.hot_out_c, r.cw_flow_kgh, r.cw_in_c,
            CW_CP_KJKG_K, r.inlet_kgh, r.vent_kgh)
    return specs


# ======================================================================================
# The anchored vent
# ======================================================================================

def vent_kgh(spec: CondenserSpec, result: CondenserResult) -> float:
    """The PFD vent anchored on the model [kg/h]: the PFD's value to the bit at the design state.

    Process utility
    ---------------
    The vent the ejector pulls and the vacuum balance books. Equation:
        vent = vent_PFD . vent_model(live) / vent_model(design)
    """
    return spec.vent_kgh * (result.vent_model_kgh / spec.vent_model_des_kgh)


def condensate_back_pressure(n_in: dict, t_v_c: float) -> tuple | None:
    """The back-pressure over what a condenser is condensing [Pa], or None if it has none."""
    w_cond = condensate_fractions(n_in)
    return back_pressure(w_cond, t_v_c) if w_cond else None


def vent_kgh_at(spec: CondenserSpec, p_bara: float, t_v_c: float, n_in: dict,
                bp: tuple | None = None) -> float:
    """The anchored vent at a trial shell pressure with the cold end held [kg/h].

    Process utility
    ---------------
    The cheap inner evaluation a vacuum's pressure loop iterates on: the cold end moves on the
    exchanger's thermal time scale, not the pressure's, so the loop holds it and the composition,
    takes the back-pressure once and passes it in.
    """
    v = vent_moles(spec, p_bara, t_v_c, n_in, bp)
    return spec.vent_kgh * (sum(v[k] * MW[k] for k in SPECIES) / spec.vent_model_des_kgh)


__all__ = [
    "H_STEP_K", "BP_HALF_BAND_K", "FALSI_EDGE_K", "FALSI_TOL_KW", "FALSI_TOL_K", "FALSI_ITERS",
    "RECENTRE_ATTEMPTS", "P_FLOOR_BARA", "LMTD_EQUAL_K", "lmtd", "condensate_fractions",
    "bp_bracket", "bp_at", "CondenserSpec", "CondenserResult", "vent_moles", "solve",
    "design_spec", "design_specs", "vent_kgh", "condensate_back_pressure", "vent_kgh_at",
]
