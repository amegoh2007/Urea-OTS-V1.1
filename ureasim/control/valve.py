"""Control-valve, check-valve and gravity-discharge hydraulics — IEC 60534-2-1 / ISA-75.01.01.

What this models
----------------
Every actuated restriction on the plant: the HP let-down valves around the synthesis loop,
the level and flow control valves of the recirculation and evaporation sections, the vent
and pressure-control valves on the low-pressure vessels, the non-return valves that stop a
pump discharge reversing, and the gravity discharges out of the atmospheric tanks.

Source
------
Ported verbatim from V1 ``backend/hydraulics.py`` (the "Phase 2 of the Heuristic Eradication
Report" module). The correlations are IEC 60534-2-1 / ISA-75.01.01; the constants ``N6`` and
``N8`` are that standard's numerical coefficients for this module's unit set.

Equations implemented
---------------------
    Cv(h)/Cv_max = R^(h-1) | h | sqrt(h)        inherent characteristic
    Cv(h)/Cv_max = R_m^(h-1), h >= 1/ln R_m      Valtek modified equal percentage, and below the
                 = h . e . ln R_m / R_m          tangent point the line through the origin
    w = N6.Fp.Cv(h).sqrt(dP_eff.rho1)           liquid, IEC 60534-2-1 §8
    dP_eff = min(dP, FL^2.(P1 - FF.Pv))         liquid choke (flashing / cavitating)
    x = min(dP/P1, F_gamma.xT),  Y = 1 - x/(3.F_gamma.xT)
    w = N8.Fp.Cv(h).P1.Y.sqrt(x.M/(T1.Z))       compressible, IEC 60534-2-1 §9
    w = w_des . [Phi(live)/Phi(design)]         the anchored form the engine calls

ON Cv PROVENANCE — READ THIS BEFORE ADDING A SITE
-------------------------------------------------
``References/Datasheets`` holds no control-valve datasheets, which is why V1 wrote this module
to BACK-SOLVE Cv_max from the licensor's own design duty (``cv_from_design_liquid``,
``cv_from_design_gas``) and to state each site's characteristic as a modelling choice. The
vendor archive holds the valves after all, for part of the plant: Flowserve's Valtek globe
valves (UD-MR-G00-DZ-0048, the summary of items -001, the data sheets -002 and the calculation
sheets -003, which give Kvs, trim, FL and xT and three sizing cases each) and CCI's Drag
valves (UD-MR-G00-DZ-0009). Where a valve is in them, the port runs its vendor trim and places
its design stroke where its Kvs passes the design flow (decided 2026-09-30, handoff B-44;
``ureasim.data.control_valves``); the anchored laws below keep the design point exact either
way. Elsewhere V1's back-solve and stated characteristic stand (handoff §Open data gaps).

Units
-----
Flows kg/h, pressures bar a, temperatures K, densities kg/m3, molar mass kg/kmol. Cv in
US gallons/min at 1 psi. The N-constants follow IEC 60534-2-1 in exactly those units, so a
unit substitution anywhere in this module silently rescales every valve on the plant.
"""

from __future__ import annotations

import math

from ureasim.core.units_of_measure import G_ACC

# --- IEC 60534-2-1 numerical constants, for Cv (US gpm/psi), bar, kg/h, kg/m3, K ----------------
#: Liquid mass-flow constant: w [kg/h] = N6.Fp.Cv.sqrt(dP[bar].rho1[kg/m3]).
N6 = 27.3
#: Gas mass-flow constant: w [kg/h] = N8.Fp.Cv.P1[bar].Y.sqrt(x.M/(T1[K].Z)).
N8 = 94.8

#: Liquid pressure-recovery factor. No valve datasheets exist for this plant (see the module
#: docstring), so this is the IEC 60534-2-1 Table-1 representative value for a globe valve with
#: a contoured plug and flow-to-open — the trim class every throttling service in this plant is
#: described as in the reference documents. It is a stated assumption, applied uniformly, not a
#: fitted constant: it sets only WHERE choking begins, and every site here runs well below that
#: point at design.
FL_GLOBE = 0.90

#: Intercept of the liquid critical pressure ratio factor FF = 0.96 - 0.28.sqrt(Pv/Pc).
FF_CONST = 0.96

#: IAPWS critical pressure — Pc of the aqueous liquors every liquid site on this plant carries.
PC_WATER_BARA = 220.64

#: Gas pressure-differential ratio factor at choking, same Table-1 basis and the same caveat
#: as FL_GLOBE above.
XT_GLOBE = 0.75

#: Rangeability of an equal-percentage globe trim. 50:1 is the IEC 60534-2-1 representative
#: value for a contoured plug and is what the equal-% law below is written around.
EQUAL_PCT_RANGE = 50.0

#: Rangeability of Valtek's modified equal-percentage plug (plug code ...G, Flowserve), fitted
#: to its own calculation sheets: 44 sizing cases on 15 of this plant's valves, 9 % to 91 %
#: stroke (UD-MR-G00-DZ-0048-003, PDF pages 46-64, scanned, read from the page images). With
#: 20:1 and the tangent line below, every printed stroke is reproduced to within 0.50 % — the
#: sheets print the stroke to a whole per cent. The least-squares optimum, 19.9, is no better.
MOD_EQUAL_PCT_RANGE = 20.0


# ==================================================================================================
#  Installed characteristic
# ==================================================================================================
def _printed_curve(h: float, points: tuple) -> float:
    """The Cv fraction a vendor's printed points give at stroke ``h``, linear between them."""
    for (h0, f0), (h1, f1) in zip(points, points[1:]):
        if h <= h1:
            return f0 + (f1 - f0) * (h - h0) / (h1 - h0)
    return points[-1][1]


def _printed_stroke(phi: float, points: tuple) -> float:
    """The stroke at which a vendor's printed points pass ``phi`` of the rated Cv."""
    for (h0, f0), (h1, f1) in zip(points, points[1:]):
        if phi <= f1:
            return h0 + (h1 - h0) * (phi - f0) / (f1 - f0)
    return points[-1][0]


def cv_fraction(h: float, characteristic: str | tuple = "equal_pct") -> float:
    """Fraction of rated Cv passed at fractional stroke ``h`` in [0, 1].

    Process utility
    ---------------
    The characteristic is what decides whether a loop is stable across its range. An
    equal-percentage trim gives constant gain in per cent of flow per per cent of lift, which
    is the basis every throttling controller on this plant is tuned around; a linear trim on
    the same service would be sluggish when nearly shut and violent when nearly open. Getting
    this wrong does not change the design point at all — it changes how the plant answers the
    operator away from it, which is precisely what a training simulator is for.

    Equations
    ---------
        equal_pct      Cv/Cv_max = R^(h-1)     R = EQUAL_PCT_RANGE
        mod_equal_pct  Cv/Cv_max = R^(h-1)     R = MOD_EQUAL_PCT_RANGE, above h0 = 1/ln R
                       Cv/Cv_max = h.e.ln(R)/R  below h0: the line through the origin tangent
                                                to the exponential at h0 (33.4 % stroke)
        linear         Cv/Cv_max = h
        quick_open     Cv/Cv_max = sqrt(h)
        printed        a tuple of (h, Cv/Cv_max) points from the vendor's sizing sheet, from
                       (0, 0) to (1, 1), linear between them — a trim whose sheet prints its
                       capacity at its cases' travels and names no curve (Metso's Neldisc)

    The modified equal-percentage trim is Valtek's: a true equal percentage over the throttling
    range, and linear near the seat, where a pure exponential would still pass 5 % of Kvs at
    zero lift. Its two pieces meet with equal value and slope, so the gain has no step.

    Clamped at both ends: a valve cannot pass more than rated, and R^(h-1) never reaches zero,
    so a commanded 0 % returns a hard 0 rather than the 2 % leakage the bare exponential
    implies.

    Note on the limiter
    -------------------
    ``min(max(h, 0.0), 1.0)`` is V1's own form and is kept literally rather than replaced by
    ``ureasim.core.numeric.clamp``. The two disagree on a NaN stroke — this form propagates
    the NaN, ``clamp`` returns 1.0, i.e. a wide-open valve — and a NaN stroke is exactly what
    a diverging controller produces. Propagating it is the safer of the two behaviours and it
    is the behaviour the V1 engine was proven against.
    """
    h = min(max(h, 0.0), 1.0)
    if h <= 0.0:
        return 0.0
    if isinstance(characteristic, tuple):
        return _printed_curve(h, characteristic)
    if characteristic == "linear":
        return h
    if characteristic == "quick_open":
        return math.sqrt(h)
    if characteristic == "mod_equal_pct":
        a = math.log(MOD_EQUAL_PCT_RANGE)
        if h >= 1.0 / a:
            return MOD_EQUAL_PCT_RANGE ** (h - 1.0)
        return h * math.e * a / MOD_EQUAL_PCT_RANGE
    return EQUAL_PCT_RANGE ** (h - 1.0)


def stroke_for_cv_fraction(phi: float, characteristic: str | tuple) -> float:
    """The fractional stroke [0, 1] at which a trim passes ``phi`` of its rated Cv — the inverse
    of `cv_fraction`.

    Process utility
    ---------------
    Places a vendor valve's design stroke: the opening at which its rated Kvs passes the
    design flow on its own sizing case. That, not the rated Kvs itself, is what an anchored
    valve law needs, because it decides where on the trim's curve the loop works — and so the
    loop's gain.
    """
    if not 0.0 < phi <= 1.0:
        raise ValueError(f"a Cv fraction lies in (0, 1]: {phi!r}")
    if isinstance(characteristic, tuple):
        return _printed_stroke(phi, characteristic)
    if characteristic == "linear":
        return phi
    if characteristic == "quick_open":
        return phi * phi
    if characteristic == "mod_equal_pct":
        a = math.log(MOD_EQUAL_PCT_RANGE)
        if phi >= math.e ** (1.0 - a):
            return 1.0 + math.log(phi) / a
        return phi * MOD_EQUAL_PCT_RANGE / (math.e * a)
    return 1.0 + math.log(phi) / math.log(EQUAL_PCT_RANGE)


# ==================================================================================================
#  Liquid service — IEC 60534-2-1 incompressible, with the cavitation / choking limit
# ==================================================================================================
def valve_flow_liquid(cv_max: float, h: float, p1_bara: float, p2_bara: float, rho_kgm3: float,
                      characteristic: str = "equal_pct", fl: float = FL_GLOBE,
                      pv_bara: float = 0.0, fp: float = 1.0) -> float:
    """Mass flow (kg/h) through a liquid-service control valve.

    Process utility
    ---------------
    This is the absolute form: it answers "how much passes", not "how much passes relative to
    design", so it is what a site with a genuinely known Cv uses, and what
    :func:`gravity_outflow_kgh` builds on. The choke term is the operational content: once the
    vena contracta reaches the liquid's vapour pressure the valve is flashing, flow stops
    responding to the downstream pressure, and opening the valve further buys nothing. An
    operator who has not seen that behaviour in a simulator will not recognise it on the plant.

    Equations
    ---------
        w      = N6 . Fp . Cv(h) . sqrt(dP_eff . rho1)
        dP_eff = min(p1 - p2, FL^2 . (p1 - FF.Pv))

    Both pressures are LIVE node pressures — that is the whole point of the replacement.
    Reverse dP returns 0.0 rather than a negative or imaginary flow; a real check valve or a
    reversing service needs its own model (:func:`check_valve_kgh`), not a sign flip here.

    Note on FF
    ----------
    This absolute form uses the flat intercept ``FF_CONST``, which is FF only in its Pv << Pc
    limit. The anchored form used by the engine, :func:`valve_liquid_anchored`, evaluates the
    full correlation. Both are V1's, and the difference is preserved rather than harmonised:
    unifying them would change the ported flows at the sites that call the absolute form.
    """
    if cv_max <= 0.0 or rho_kgm3 <= 0.0:
        return 0.0
    frac = cv_fraction(h, characteristic)
    if frac <= 0.0:
        return 0.0
    dp = p1_bara - p2_bara
    if dp <= 0.0:
        return 0.0
    dp_choked = fl * fl * (p1_bara - FF_CONST * pv_bara)
    dp_eff = min(dp, dp_choked) if dp_choked > 0.0 else dp
    return N6 * fp * cv_max * frac * math.sqrt(dp_eff * rho_kgm3)


# ==================================================================================================
#  Compressible service — IEC 60534-2-1 with the expansion factor and a hard choke
# ==================================================================================================
def expansion_factor(x: float, f_gamma: float, xt: float = XT_GLOBE) -> float:
    """Expansion factor Y, floored at the choked value 2/3.

    Process utility
    ---------------
    Y accounts for the density change of a gas through the restriction. At x = F_gamma.xT the
    flow chokes and Y = 2/3 exactly; beyond that neither x nor Y may keep rising, which is what
    makes the flow a function of UPSTREAM conditions only — the property an incompressible
    sqrt(dP) law destroys. On this plant that matters most at the HP let-down valves, which run
    deeply choked at every normal operating point.

    Equation
    --------
        Y = max(1 - x / (3.F_gamma.xT), 2/3)
    """
    denom = 3.0 * f_gamma * xt
    if denom <= 0.0:
        return 2.0 / 3.0
    return max(1.0 - x / denom, 2.0 / 3.0)


def valve_flow_gas(cv_max: float, h: float, p1_bara: float, p2_bara: float, t1_k: float,
                   mw: float, gamma: float = 1.30, z: float = 1.0,
                   characteristic: str = "equal_pct", xt: float = XT_GLOBE,
                   fp: float = 1.0) -> float:
    """Mass flow (kg/h) through a compressible-service control valve.

    Process utility
    ---------------
    Vapour let-down: reactor off-gas to the scrubber, stripper overheads, the vents off the
    low-pressure vessels. The ``min()`` IS the choke — once dP/P1 reaches F_gamma.xT, x stops
    rising, Y sits at 2/3, and the flow depends on p2 not at all. HV-322604 runs at
    dP/P1 = 0.97 against an F_gamma.xT of about 0.70, i.e. deeply choked, and the
    incompressible law it replaces had flow still climbing as the downstream pressure fell.

    Equations
    ---------
        F_gamma = gamma / 1.40
        x       = min(dP/P1, F_gamma.xT)
        Y       = 1 - x / (3.F_gamma.xT)
        w       = N8 . Fp . Cv(h) . P1 . Y . sqrt(x.M / (T1.Z))
    """
    if cv_max <= 0.0 or p1_bara <= 0.0 or t1_k <= 0.0 or mw <= 0.0:
        return 0.0
    frac = cv_fraction(h, characteristic)
    if frac <= 0.0:
        return 0.0
    dp = p1_bara - p2_bara
    if dp <= 0.0:
        return 0.0
    f_gamma = gamma / 1.40
    x = min(dp / p1_bara, f_gamma * xt)
    y = expansion_factor(x, f_gamma, xt)
    return N8 * fp * cv_max * frac * p1_bara * y * math.sqrt(x * mw / (t1_k * max(z, 1e-9)))


# ==================================================================================================
#  Back-solving Cv_max from the licensor's design case (see the module docstring on provenance)
# ==================================================================================================
def cv_from_design_liquid(w_des_kgh: float, h_des: float, p1_des: float, p2_des: float,
                          rho_des: float, characteristic: str = "equal_pct",
                          fl: float = FL_GLOBE, pv_bara: float = 0.0, fp: float = 1.0) -> float:
    """Cv_max such that :func:`valve_flow_liquid` returns exactly ``w_des_kgh`` at design.

    Process utility
    ---------------
    The plant has no control-valve datasheets, so this is where a valve's size comes from: the
    duty the licensor specified it against. Inverting the same expression the forward call
    uses, in the same operation order, is what makes the design point reproduce BIT-EXACTLY and
    leaves the boot pin untouched.
    """
    frac = cv_fraction(h_des, characteristic)
    dp = p1_des - p2_des
    if frac <= 0.0 or dp <= 0.0 or rho_des <= 0.0 or w_des_kgh <= 0.0:
        return 0.0
    dp_choked = fl * fl * (p1_des - FF_CONST * pv_bara)
    dp_eff = min(dp, dp_choked) if dp_choked > 0.0 else dp
    return w_des_kgh / (N6 * fp * frac * math.sqrt(dp_eff * rho_des))


def cv_from_design_gas(w_des_kgh: float, h_des: float, p1_des: float, p2_des: float,
                       t1_des_k: float, mw: float, gamma: float = 1.30, z: float = 1.0,
                       characteristic: str = "equal_pct", xt: float = XT_GLOBE,
                       fp: float = 1.0) -> float:
    """Cv_max such that :func:`valve_flow_gas` returns exactly ``w_des_kgh`` at design.

    Process utility
    ---------------
    As for the liquid back-solve. Note that a gas site sized at a CHOKED design point carries
    no information about its unchoked behaviour beyond the standard's own expansion factor —
    which is a limitation of the sizing basis, not of this function.
    """
    frac = cv_fraction(h_des, characteristic)
    dp = p1_des - p2_des
    if frac <= 0.0 or dp <= 0.0 or w_des_kgh <= 0.0 or p1_des <= 0.0:
        return 0.0
    f_gamma = gamma / 1.40
    x = min(dp / p1_des, f_gamma * xt)
    y = expansion_factor(x, f_gamma, xt)
    return w_des_kgh / (N8 * fp * frac * p1_des * y * math.sqrt(x * mw / (t1_des_k * max(z, 1e-9))))


# ==================================================================================================
#  Anchored form — the one the engine actually calls
# ==================================================================================================
#  WHY NOT JUST BACK-SOLVE Cv AND CALL THE ABSOLUTE LAW. Because it is not bit-exact. Inverting
#  w = N6.Fp.Cv.frac.sqrt(dP.rho) for Cv and multiplying straight back through does not return the
#  original float — V1 measured 101490.00000000001 against 101490.0 — and this engine's boot pin
#  asserts the design point to the LAST BIT. A 1-ulp drift at every valve on every tick is exactly
#  the kind of thing that walks a 6-hour run off its anchor.
#
#  So the engine calls the RATIO of the ISA law to itself at the design condition:
#
#      w = w_des . [Phi(live) / Phi(design)],   Phi = frac(h) . sqrt(dP_eff . rho)          (liquid)
#                                               Phi = frac(h) . P1 . Y . sqrt(x.M/(T1.Z))  (gas)
#
#  N6/N8, Fp and Cv_max are identical in numerator and denominator, so they cancel ALGEBRAICALLY —
#  which also means the absent valve datasheets (see the module docstring) stop mattering for these
#  sites: the answer never depended on Cv_max at all. What survives is every term a frozen
#  `design x stroke/stroke_des` form is missing: the installed characteristic, the live density, the
#  live dP from node pressures on both sides, and the choke. At the design condition numerator and
#  denominator are the same expression on the same operands, so the bracket is exactly 1.0 and
#  w == w_des bit-exact.
#
#  This is Rule 1 of the rewrite — design anchoring — in its valve-shaped form.
# ==================================================================================================
def _phi_liquid(h, p1, p2, rho, characteristic, fl, pv):
    """Liquid shape function Phi = frac(h).sqrt(dP_eff.rho); the ratio of two of these is a flow."""
    frac = cv_fraction(h, characteristic)
    dp = p1 - p2
    if frac <= 0.0 or dp <= 0.0 or rho <= 0.0:
        return 0.0
    # IEC 60534-2-1 in full. FF is held at its 0.96 intercept in the ABSOLUTE form above, which is
    # only its Pv << Pc limit: a 190 C liquor at 15 bar a has FF = 0.887. At pv = 0 the expression
    # below is the intercept exactly, so the two forms agree wherever vapour pressure is not
    # supplied — which is why the difference is invisible until a hot liquor site passes one.
    ff = FF_CONST - 0.28 * math.sqrt(max(pv, 0.0) / PC_WATER_BARA)
    dp_choked = fl * fl * (p1 - ff * pv)
    dp_eff = min(dp, dp_choked) if dp_choked > 0.0 else dp
    return frac * math.sqrt(dp_eff * rho)


def _phi_gas(h, p1, p2, t1_k, mw, gamma, z, characteristic, xt):
    """Compressible shape function Phi = frac(h).P1.Y.sqrt(x.M/(T1.Z)), carrying the choke."""
    frac = cv_fraction(h, characteristic)
    dp = p1 - p2
    if frac <= 0.0 or dp <= 0.0 or p1 <= 0.0 or t1_k <= 0.0 or mw <= 0.0:
        return 0.0
    f_gamma = gamma / 1.40
    x = min(dp / p1, f_gamma * xt)
    y = expansion_factor(x, f_gamma, xt)
    return frac * p1 * y * math.sqrt(x * mw / (t1_k * max(z, 1e-9)))


def compressible_shape(h: float, p1: float, p2: float, t1_k: float, mw: float, gamma: float,
                       z: float, characteristic: str, xt: float) -> float:
    """The compressible shape Phi whose ratio is an anchored gas flow (``_phi_gas``).

    Process utility
    ---------------
    For a valve whose design flow is written in its own idiom rather than as a flow at a
    design stroke — V1's steam butterflies, K . op . sqrt(dP_des) — the ratio of two of these,
    live over design, is the whole of the choke and the expansion.
    """
    return _phi_gas(h, p1, p2, t1_k, mw, gamma, z, characteristic, xt)


def valve_liquid_anchored(w_des_kgh: float, h: float, p1: float, p2: float, rho: float,
                          h_des: float, p1_des: float, p2_des: float, rho_des: float,
                          characteristic: str = "equal_pct", fl: float = FL_GLOBE,
                          pv_bara: float = 0.0, pv_des_bara: float | None = None) -> float:
    """IEC 60534 liquid flow, anchored on the licensor's design duty. Bit-exact at design.

    Process utility
    ---------------
    The engine's standard liquid valve call. Every level and flow control valve on the
    recirculation, desorption and evaporation sections runs through this function, which is
    why its design-point exactness is not a nicety: the whole flowsheet is pinned to the PFD
    through it.

    Arguments
    ---------
    ``pv_bara`` is the live vapour pressure of the liquid at the valve inlet and
    ``pv_des_bara`` its design value (defaulting to the live one). Pass both wherever the inlet
    temperature or composition can move, or the choke point cancels out of the ratio and the
    valve will not flash when the plant says it should.
    """
    pv_d = pv_bara if pv_des_bara is None else pv_des_bara
    ref = _phi_liquid(h_des, p1_des, p2_des, rho_des, characteristic, fl, pv_d)
    if ref <= 0.0:
        return 0.0
    return w_des_kgh * (_phi_liquid(h, p1, p2, rho, characteristic, fl, pv_bara) / ref)


def valve_gas_anchored(w_des_kgh: float, h: float, p1: float, p2: float, t1_k: float,
                       h_des: float, p1_des: float, p2_des: float, t1_des_k: float,
                       mw: float, gamma: float = 1.30, z: float = 1.0,
                       characteristic: str = "equal_pct", xt: float = XT_GLOBE,
                       mw_des: float | None = None, z_des: float | None = None) -> float:
    """IEC 60534 compressible flow, anchored on the licensor's design duty. Bit-exact at design.

    Process utility
    ---------------
    The engine's standard vapour valve call. The choke lives in ``_phi_gas``, so a site
    anchored at an UNCHOKED design condition still saturates correctly when the downstream
    pressure falls away — which is the whole of V1's finding D-2.

    Arguments
    ---------
    ``mw_des`` and ``z_des`` default to ``mw`` and ``z``, which makes the composition CANCEL
    out of the ratio. That default is right only where the vapour composition is genuinely
    fixed. Pass the design values explicitly wherever the composition can move, and the
    w ~ sqrt(M) dependence survives: a heavier off-gas really does put more kilograms through
    the same trim at the same pressures.
    """
    mw_d = mw if mw_des is None else mw_des
    z_d = z if z_des is None else z_des
    ref = _phi_gas(h_des, p1_des, p2_des, t1_des_k, mw_d, gamma, z_d, characteristic, xt)
    if ref <= 0.0:
        return 0.0
    return w_des_kgh * (_phi_gas(h, p1, p2, t1_k, mw, gamma, z, characteristic, xt) / ref)


# ==================================================================================================
#  Gravity discharge
# ==================================================================================================
def gravity_outflow_kgh(cv_max: float, h_valve: float, level_m: float, rho_kgm3: float,
                        p_vessel_bara: float, p_dest_bara: float,
                        characteristic: str = "equal_pct", fl: float = FL_GLOBE) -> float:
    """Liquid discharge driven by hydrostatic head plus the vessel/destination differential.

    Process utility
    ---------------
    This is what makes an empty-vessel guard unnecessary rather than merely deleted. As the
    level goes to zero the head term goes to zero, and if the vessel is not pushing against the
    destination the total dP goes to zero with it, so the flow goes to zero on its own. V1's
    ``if level <= 0: suction = min(suction, inflow)`` was patching a hole that the head term
    fills. An operator draining a tank sees the flow decay as the head decays, which is the
    behaviour being taught.

    Equation
    --------
        dP = (P_vessel - P_dest) + rho.g.h / 1e5        [bar]

    then the standard liquid valve law on that differential.
    """
    head_bar = rho_kgm3 * G_ACC * max(level_m, 0.0) / 1.0e5
    p1 = p_vessel_bara + head_bar
    return valve_flow_liquid(cv_max, h_valve, p1, p_dest_bara, rho_kgm3,
                             characteristic=characteristic, fl=fl)


# ==================================================================================================
#  Non-return (check) valve — a hydraulic diode
# ==================================================================================================
#  A check valve is NOT a control valve with a sign test bolted on. Three properties define it, and
#  all three matter to the CO2 tie-in this was written for:
#
#    * it is a fixed resistance in the forward direction, so the flow follows sqrt(dP) like any
#      other orifice — NOT a `min(1, sqrt(dP/dP_des))` DELIVERY FRACTION, which saturates at the
#      design differential and therefore cannot pass more than design however hard the line pushes;
#    * it does not open until the differential lifts the disc off its seat. The crack pressure is
#      small but it is the whole reason the valve is a diode and not a resistor: between
#      p_up = p_down and p_up = p_down + p_crack the line is SHUT, not merely passing very little;
#    * reverse flow is exactly zero, not a small negative number. A sign test on a sqrt law gives 0
#      for the wrong reason (the argument goes imaginary); this returns 0 because the disc is on its
#      seat, which is also true for the whole crack band above.
#
#  ANCHORING. As everywhere else in this module the law is written as the RATIO of itself to its own
#  design condition, so the vendor Cv/Kv that does not exist in either repository cancels
#  algebraically and the design duty is reproduced BIT-EXACTLY.
#
#  WHY ONE RESISTANCE AND NOT TWO. What that anchor buys is also what it costs: the check valve's
#  own seat resistance and the resistance of the line and equipment inlet downstream of it are in
#  SERIES and both follow sqrt(dP), so they lump into one equivalent resistance and only their SUM
#  is observable from a single design point. The model therefore carries one resistance and says so,
#  rather than inventing a split between them.
#
#  ON p_crack. `References/Datasheets` holds no check-valve datasheet, so the crack pressure is a
#  STATED modelling assumption of the same class as FL_GLOBE and XT_GLOBE above — a representative
#  value, applied openly, not a fitted one. Its influence is confined to the last per cent of the
#  differential: at the design point the anchor makes it cancel exactly, and in the normal band it
#  shifts the passed flow by sqrt((dP - p_crack)/(dP_des - p_crack)) / sqrt(dP/dP_des), which for
#  p_crack = 2 % of dP_des is under 0.1 % anywhere above half the design differential. What it does
#  fix, and what no other number in the model fixes, is exactly WHERE the valve slams shut.
# ==================================================================================================
def check_valve_kgh(w_des_kgh: float, p_up_bara: float, p_down_bara: float,
                    dp_des_bar: float, p_crack_bar: float = 0.0) -> float:
    """Forward-only flow through a non-return valve, anchored on its design duty.

    Process utility
    ---------------
    A check valve is the difference between a pump trip that coasts down and a pump trip that
    back-flows the whole discharge header into the suction vessel. The hard zero below is the
    modelled behaviour that matters: the disc seats, and reverse flow is not small, it is
    absent.

    Equations
    ---------
        w = w_des . sqrt((p_up - p_down - p_crack) / (dP_des - p_crack))   forward, disc lifted
        w = 0                                                             otherwise

    Bit-exact at p_up - p_down == dP_des: numerator and denominator are then the same
    expression on the same operands and the bracket is a literal 1.0.
    """
    if w_des_kgh <= 0.0:
        return 0.0
    ref = dp_des_bar - p_crack_bar
    if ref <= 0.0:
        return 0.0
    dp = p_up_bara - p_down_bara - p_crack_bar
    if dp <= 0.0:
        return 0.0                      # disc seated: reverse flow and the crack band are both ZERO
    return w_des_kgh * math.sqrt(dp / ref)


__all__ = [
    "N6",
    "N8",
    "FL_GLOBE",
    "FF_CONST",
    "PC_WATER_BARA",
    "XT_GLOBE",
    "compressible_shape",
    "EQUAL_PCT_RANGE",
    "MOD_EQUAL_PCT_RANGE",
    "cv_fraction",
    "stroke_for_cv_fraction",
    "valve_flow_liquid",
    "expansion_factor",
    "valve_flow_gas",
    "cv_from_design_liquid",
    "cv_from_design_gas",
    "valve_liquid_anchored",
    "valve_gas_anchored",
    "gravity_outflow_kgh",
    "check_valve_kgh",
]
