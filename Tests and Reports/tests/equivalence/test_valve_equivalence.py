"""V1 <-> V1.1 equivalence for the valve laws in `ureasim.control` and the relief law in
`ureasim.core`.

What is being proved
--------------------
`ureasim.control.valve` and `ureasim.core.relief`'s capacity law are a verbatim port of the
valve half of V1's `backend/hydraulics.py`. "Verbatim" is a claim about floating-point
arithmetic, not about intent, so it is asserted with `==` rather than `approx`: same
expression, same operation order, same operands, therefore the same bits. An `approx` here
would pass on a re-associated expression that drifts a 6-hour run off its anchor, which is
exactly the failure V1's own comments say the anchored form exists to prevent.

Three things beyond the raw numbers are pinned:

  * the **design-point identity**. Both anchored forms must return the design flow to the
    last bit at the design condition, because the boot pin asserts the PFD exactly. This is
    tested as an identity (`is_design == w_des`), not to a tolerance.
  * the **two FF conventions**. V1's absolute liquid law holds FF at its 0.96 intercept
    while the anchored law evaluates the full correlation. That difference is real and is
    preserved; a test that only exercised pv = 0 would not notice it being harmonised away.
  * the **choke saturation**. Past the critical ratio the gas flow must stop responding to
    the downstream pressure. That is V1 finding D-2 and it is the property most likely to be
    lost to a well-meaning simplification.

The V1 module is loaded by file path (see `v1_loader`), so this is V1's code running, not a
re-derivation of it.
"""

from __future__ import annotations

import math

import pytest

from ureasim.control import valve
from ureasim.core import relief
from tests.equivalence import decided_valves as dv
from tests.equivalence.v1_loader import load, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)


@pytest.fixture(scope="module")
def v1():
    return load("hydraulics")


# --------------------------------------------------------------------------------------
# The standard's constants
# --------------------------------------------------------------------------------------
# A constant silently retyped is the cheapest possible way to rescale every valve on the
# plant, and nothing downstream would fail.

def test_the_iec_constants_are_the_same_numbers(v1):
    assert valve.N6 == v1.N6
    assert valve.N8 == v1.N8
    assert valve.FL_GLOBE == v1.FL_GLOBE
    assert valve.FF_CONST == v1.FF_CONST
    assert valve.PC_WATER_BARA == v1.PC_WATER_BARA
    assert valve.XT_GLOBE == v1.XT_GLOBE
    assert valve.EQUAL_PCT_RANGE == v1.EQUAL_PCT_RANGE


# --------------------------------------------------------------------------------------
# Installed characteristic
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("characteristic", ["equal_pct", "linear", "quick_open"])
@pytest.mark.parametrize(
    "h", [-1.0, -1e-12, 0.0, 1e-9, 0.05, 0.25, 0.5, 0.632, 0.75, 0.999, 1.0, 1.5, 12.0])
def test_cv_fraction_matches_v1_at_every_stroke(h, characteristic, v1):
    assert valve.cv_fraction(h, characteristic) == v1.cv_fraction(h, characteristic)


def test_an_unknown_characteristic_falls_through_to_equal_percentage_in_both(v1):
    """V1 has no error branch: anything that is not linear or quick_open is equal-%."""
    assert valve.cv_fraction(0.4, "butterfly") == v1.cv_fraction(0.4, "butterfly")
    assert valve.cv_fraction(0.4, "butterfly") == valve.cv_fraction(0.4, "equal_pct")


@pytest.mark.parametrize(
    "h", [-1.0, 0.0, 1e-9, 0.05, 0.09, 0.25, 0.3338, 0.334, 0.5, 0.632, 0.75, 1.0, 1.5])
def test_the_vendor_trim_decided_divergence(h, v1):
    """Handoff B-44, decided 2026-09-30, both sides. The port knows Valtek's modified equal
    percentage — the decided relation, stated independently in `decided_valves.trim`; V1 has no
    such trim, and its name falls through V1's `cv_fraction` to the 50:1 equal percentage."""
    assert valve.cv_fraction(h, "mod_equal_pct") == dv.trim(h)
    assert v1.cv_fraction(h, "mod_equal_pct") == v1.cv_fraction(h, "equal_pct")


def test_a_shut_valve_is_a_hard_zero_not_the_two_per_cent_the_exponential_implies(v1):
    """R^(h-1) at h = 0 is 1/50, i.e. 2 % leakage. Both implementations refuse it."""
    assert valve.cv_fraction(0.0) == 0.0
    assert v1.cv_fraction(0.0) == 0.0
    assert valve.EQUAL_PCT_RANGE ** -1.0 == pytest.approx(0.02)


def test_a_nan_stroke_propagates_in_both_rather_than_opening_the_valve(v1):
    """The limiter choice documented in `cv_fraction`. A diverging controller emits NaN.

    `min(max(nan, 0), 1)` keeps the NaN; `core.numeric.clamp` would return 1.0, which is a
    wide-open valve. Both implementations must keep V1's behaviour, so a substitution of the
    shared limiter for the inline one would fail here.
    """
    assert math.isnan(valve.cv_fraction(float("nan")))
    assert math.isnan(v1.cv_fraction(float("nan")))


# --------------------------------------------------------------------------------------
# Liquid service, absolute form
# --------------------------------------------------------------------------------------
#  Conditions below span the plant's real liquid sites: HP carbamate let-down (150 -> 18 bar a,
#  dense hot liquor), LP level control (18 -> 4 bar a), and an evaporator bottoms draw near
#  atmospheric where the vapour pressure is a large fraction of the inlet pressure.

LIQUID_CASES = [
    # cv_max,  h,    p1,     p2,    rho,    pv
    (120.0, 0.60, 150.0, 18.0, 1080.0, 0.0),
    (120.0, 0.60, 150.0, 18.0, 1080.0, 12.6),
    (85.0, 0.45, 18.0, 4.2, 1151.0, 4.0),
    (85.0, 0.95, 18.0, 4.2, 1151.0, 4.0),
    (40.0, 0.30, 4.2, 1.013, 1240.0, 0.9),
    (40.0, 0.30, 4.2, 4.2, 1240.0, 0.9),      # zero dP
    (40.0, 0.30, 1.013, 4.2, 1240.0, 0.9),    # reverse dP
    (40.0, 0.0, 4.2, 1.013, 1240.0, 0.9),     # shut
    (0.0, 0.50, 4.2, 1.013, 1240.0, 0.9),     # no Cv
    (40.0, 0.50, 4.2, 1.013, 0.0, 0.9),       # no density
]


@pytest.mark.parametrize("characteristic", ["equal_pct", "linear"])
@pytest.mark.parametrize("cv_max,h,p1,p2,rho,pv", LIQUID_CASES)
def test_liquid_valve_flow_matches_v1_bit_for_bit(cv_max, h, p1, p2, rho, pv,
                                                  characteristic, v1):
    assert valve.valve_flow_liquid(cv_max, h, p1, p2, rho, characteristic, pv_bara=pv) == \
        v1.valve_flow_liquid(cv_max, h, p1, p2, rho, characteristic, pv_bara=pv)


def test_the_liquid_choke_stops_the_flow_responding_to_the_downstream_pressure(v1):
    """Flashing service: below the choke point, opening the gap to p2 buys nothing.

    Vapour pressure 12.6 bar a at 150 bar a inlet chokes at FL^2.(p1 - FF.Pv) = 111.7 bar,
    so every p2 below 38.3 bar a passes the same flow.
    """
    flows = [valve.valve_flow_liquid(120.0, 0.6, 150.0, p2, 1080.0, pv_bara=12.6)
             for p2 in (35.0, 20.0, 5.0, 1.013)]
    assert len(set(flows)) == 1
    assert flows[0] == v1.valve_flow_liquid(120.0, 0.6, 150.0, 1.013, 1080.0, pv_bara=12.6)


# --------------------------------------------------------------------------------------
# Compressible service, absolute form
# --------------------------------------------------------------------------------------
#  HV-322604 is the case V1's docstring names: vapour let-down 140.7 -> 4 bar a, dP/P1 = 0.97
#  against an F_gamma.xT of about 0.70, i.e. deeply choked.

GAS_CASES = [
    # cv_max,  h,   p1,     p2,    t1_k,   mw,    gamma
    (60.0, 0.55, 140.7, 4.0, 453.15, 30.2, 1.30),
    (60.0, 0.55, 140.7, 110.0, 453.15, 30.2, 1.30),   # unchoked
    (60.0, 1.00, 140.7, 4.0, 453.15, 30.2, 1.30),
    (25.0, 0.40, 18.0, 4.2, 393.15, 22.5, 1.31),
    (25.0, 0.40, 4.2, 1.013, 353.15, 17.03, 1.31),
    (25.0, 0.40, 1.013, 1.013, 353.15, 17.03, 1.31),  # zero dP
    (25.0, 0.40, 1.013, 4.2, 353.15, 17.03, 1.31),    # reverse dP
    (25.0, 0.00, 4.2, 1.013, 353.15, 17.03, 1.31),    # shut
    (25.0, 0.40, 4.2, 1.013, 353.15, 0.0, 1.31),      # no molar mass
]


@pytest.mark.parametrize("characteristic", ["equal_pct", "linear"])
@pytest.mark.parametrize("cv_max,h,p1,p2,t1,mw,gamma", GAS_CASES)
def test_gas_valve_flow_matches_v1_bit_for_bit(cv_max, h, p1, p2, t1, mw, gamma,
                                               characteristic, v1):
    assert valve.valve_flow_gas(cv_max, h, p1, p2, t1, mw, gamma,
                                characteristic=characteristic) == \
        v1.valve_flow_gas(cv_max, h, p1, p2, t1, mw, gamma, characteristic=characteristic)


@pytest.mark.parametrize("x", [0.0, 0.1, 0.3, 0.5, 0.6964, 0.7, 1.0, 5.0])
@pytest.mark.parametrize("f_gamma", [0.0, 0.7142857142857143, 0.9285714285714286])
def test_expansion_factor_matches_v1_including_its_two_thirds_floor(x, f_gamma, v1):
    assert valve.expansion_factor(x, f_gamma) == v1.expansion_factor(x, f_gamma)


def test_the_gas_choke_makes_flow_a_function_of_upstream_conditions_only(v1):
    """V1 finding D-2. Past F_gamma.xT the downstream pressure leaves the equation."""
    choked = [valve.valve_flow_gas(60.0, 0.55, 140.7, p2, 453.15, 30.2)
              for p2 in (40.0, 20.0, 4.0, 1.013)]
    assert len(set(choked)) == 1
    assert choked[0] == v1.valve_flow_gas(60.0, 0.55, 140.7, 1.013, 453.15, 30.2)


# --------------------------------------------------------------------------------------
# Back-solved Cv
# --------------------------------------------------------------------------------------

def test_cv_back_solved_from_the_design_duty_matches_v1_liquid(v1):
    assert valve.cv_from_design_liquid(101490.0, 0.5, 18.0, 4.2, 1151.0) == \
        v1.cv_from_design_liquid(101490.0, 0.5, 18.0, 4.2, 1151.0)


def test_cv_back_solved_from_the_design_duty_matches_v1_gas(v1):
    assert valve.cv_from_design_gas(24582.0, 0.5, 140.7, 4.0, 453.15, 30.2) == \
        v1.cv_from_design_gas(24582.0, 0.5, 140.7, 4.0, 453.15, 30.2)


@pytest.mark.parametrize("bad", [
    dict(w_des_kgh=0.0, h_des=0.5, p1_des=18.0, p2_des=4.2, rho_des=1151.0),
    dict(w_des_kgh=101490.0, h_des=0.0, p1_des=18.0, p2_des=4.2, rho_des=1151.0),
    dict(w_des_kgh=101490.0, h_des=0.5, p1_des=4.2, p2_des=18.0, rho_des=1151.0),
    dict(w_des_kgh=101490.0, h_des=0.5, p1_des=18.0, p2_des=4.2, rho_des=0.0),
])
def test_an_unusable_design_case_returns_zero_in_both_rather_than_dividing(bad, v1):
    assert valve.cv_from_design_liquid(**bad) == v1.cv_from_design_liquid(**bad)
    assert valve.cv_from_design_liquid(**bad) == 0.0


def test_the_back_solved_cv_reproduces_the_design_flow_through_the_absolute_law():
    """The property the back-solve exists for — and the reason it is not good enough.

    It returns the design flow to within a float rounding, NOT exactly. V1 measured
    101490.00000000001 against 101490.0, which is why the engine calls the anchored ratio
    form instead. Asserting the near-miss here documents the motive rather than leaving it
    as a comment nobody checks.
    """
    w_des, h_des, p1, p2, rho = 101490.0, 0.5, 18.0, 4.2, 1151.0
    cv = valve.cv_from_design_liquid(w_des, h_des, p1, p2, rho)
    back = valve.valve_flow_liquid(cv, h_des, p1, p2, rho)
    assert back == pytest.approx(w_des, rel=1e-12)


# --------------------------------------------------------------------------------------
# Anchored forms — the calls the engine actually makes
# --------------------------------------------------------------------------------------

#  Design condition of a representative LP level control valve, and the live excursions a
#  trainee can drive it to: stroke away from design, both node pressures moving, and the
#  density changing as the liquor concentrates.
LIQ_DES = dict(w_des_kgh=101490.0, h_des=0.5, p1_des=18.0, p2_des=4.2, rho_des=1151.0)

LIQ_LIVE = [
    (0.5, 18.0, 4.2, 1151.0),      # exactly design
    (0.8, 18.0, 4.2, 1151.0),
    (0.2, 18.0, 4.2, 1151.0),
    (0.5, 16.0, 4.2, 1151.0),
    (0.5, 18.0, 9.0, 1151.0),
    (0.5, 18.0, 4.2, 1310.0),
    (0.5, 4.2, 18.0, 1151.0),      # reversed
    (0.0, 18.0, 4.2, 1151.0),      # shut
]


@pytest.mark.parametrize("h,p1,p2,rho", LIQ_LIVE)
@pytest.mark.parametrize("pv,pv_des", [(0.0, None), (4.0, 4.0), (6.5, 4.0)])
def test_anchored_liquid_flow_matches_v1_bit_for_bit(h, p1, p2, rho, pv, pv_des, v1):
    assert valve.valve_liquid_anchored(h=h, p1=p1, p2=p2, rho=rho,
                                       pv_bara=pv, pv_des_bara=pv_des, **LIQ_DES) == \
        v1.valve_liquid_anchored(h=h, p1=p1, p2=p2, rho=rho,
                                 pv_bara=pv, pv_des_bara=pv_des, **LIQ_DES)


def test_the_anchored_liquid_law_is_bit_exact_at_the_design_condition():
    """Not `approx`. The boot pin asserts the PFD to the last bit, so this must be `==`."""
    at_design = valve.valve_liquid_anchored(
        h=LIQ_DES["h_des"], p1=LIQ_DES["p1_des"], p2=LIQ_DES["p2_des"],
        rho=LIQ_DES["rho_des"], **LIQ_DES)
    assert at_design == LIQ_DES["w_des_kgh"]


GAS_DES = dict(w_des_kgh=24582.0, h_des=0.5, p1_des=140.7, p2_des=4.0, t1_des_k=453.15)

GAS_LIVE = [
    (0.5, 140.7, 4.0, 453.15),     # exactly design
    (0.9, 140.7, 4.0, 453.15),
    (0.5, 120.0, 4.0, 453.15),
    (0.5, 140.7, 60.0, 453.15),
    (0.5, 140.7, 4.0, 483.15),
    (0.5, 4.0, 140.7, 453.15),     # reversed
    (0.0, 140.7, 4.0, 453.15),     # shut
]


@pytest.mark.parametrize("h,p1,p2,t1", GAS_LIVE)
@pytest.mark.parametrize("mw,mw_des", [(30.2, None), (30.2, 30.2), (24.0, 30.2)])
def test_anchored_gas_flow_matches_v1_bit_for_bit(h, p1, p2, t1, mw, mw_des, v1):
    assert valve.valve_gas_anchored(h=h, p1=p1, p2=p2, t1_k=t1, mw=mw, mw_des=mw_des,
                                    **GAS_DES) == \
        v1.valve_gas_anchored(h=h, p1=p1, p2=p2, t1_k=t1, mw=mw, mw_des=mw_des, **GAS_DES)


def test_the_anchored_gas_law_is_bit_exact_at_the_design_condition():
    at_design = valve.valve_gas_anchored(
        h=GAS_DES["h_des"], p1=GAS_DES["p1_des"], p2=GAS_DES["p2_des"],
        t1_k=GAS_DES["t1_des_k"], mw=30.2, **GAS_DES)
    assert at_design == GAS_DES["w_des_kgh"]


def test_a_fixed_composition_cancels_out_of_the_gas_ratio_but_a_moving_one_does_not():
    """The `mw_des` default is a modelling decision, not a convenience.

    Defaulted, the composition cancels and a heavier off-gas passes the same kilograms.
    Supplied, the w ~ sqrt(M) dependence survives. Both behaviours are V1's and a call site
    picks between them, so neither may quietly become the other.
    """
    heavier = dict(h=0.5, p1=140.7, p2=4.0, t1_k=453.15)
    cancelled = valve.valve_gas_anchored(mw=44.01, **heavier, **GAS_DES)
    survives = valve.valve_gas_anchored(mw=44.01, mw_des=30.2, **heavier, **GAS_DES)
    assert cancelled == GAS_DES["w_des_kgh"]
    assert survives == pytest.approx(
        GAS_DES["w_des_kgh"] * math.sqrt(44.01 / 30.2), rel=1e-12)
    assert survives > cancelled


def test_the_two_liquid_forms_disagree_on_ff_exactly_as_v1_does(v1):
    """The absolute law holds FF at 0.96; the anchored law evaluates the full correlation.

    At a hot liquor's vapour pressure the two choke at different differentials. The
    difference is V1's and is preserved deliberately — this test fails if they are ever
    harmonised, which is the point.
    """
    pv = 40.0
    ff_full = valve.FF_CONST - 0.28 * math.sqrt(pv / valve.PC_WATER_BARA)
    assert ff_full != valve.FF_CONST
    absolute_choke = valve.FL_GLOBE ** 2 * (60.0 - valve.FF_CONST * pv)
    anchored_choke = valve.FL_GLOBE ** 2 * (60.0 - ff_full * pv)
    assert anchored_choke > absolute_choke
    # And both engines agree on each of their own forms.
    assert valve.valve_flow_liquid(50.0, 0.6, 60.0, 2.0, 1100.0, pv_bara=pv) == \
        v1.valve_flow_liquid(50.0, 0.6, 60.0, 2.0, 1100.0, pv_bara=pv)
    assert valve.valve_liquid_anchored(w_des_kgh=50000.0, h=0.6, p1=60.0, p2=2.0, rho=1100.0,
                                       h_des=0.5, p1_des=60.0, p2_des=20.0, rho_des=1100.0,
                                       pv_bara=pv, pv_des_bara=pv) == \
        v1.valve_liquid_anchored(w_des_kgh=50000.0, h=0.6, p1=60.0, p2=2.0, rho=1100.0,
                                 h_des=0.5, p1_des=60.0, p2_des=20.0, rho_des=1100.0,
                                 pv_bara=pv, pv_des_bara=pv)


# --------------------------------------------------------------------------------------
# Gravity discharge
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("level_m", [0.0, -0.4, 0.05, 0.8, 1.6, 3.2])
@pytest.mark.parametrize("p_vessel,p_dest", [(1.013, 1.013), (1.6, 1.013), (1.013, 1.6)])
def test_gravity_outflow_matches_v1(level_m, p_vessel, p_dest, v1):
    assert valve.gravity_outflow_kgh(35.0, 0.7, level_m, 1180.0, p_vessel, p_dest) == \
        v1.gravity_outflow_kgh(35.0, 0.7, level_m, 1180.0, p_vessel, p_dest)


def test_an_empty_unpressurised_vessel_stops_draining_without_a_guard(v1):
    """The reason V1's `if level <= 0` patches could be deleted rather than ported."""
    assert valve.gravity_outflow_kgh(35.0, 0.7, 0.0, 1180.0, 1.013, 1.013) == 0.0
    assert valve.gravity_outflow_kgh(35.0, 0.7, -2.0, 1180.0, 1.013, 1.013) == 0.0


def test_the_discharge_decays_with_the_head_it_is_driven_by():
    """Flow ~ sqrt(level) once the vessel and destination are at the same pressure."""
    flows = [valve.gravity_outflow_kgh(35.0, 0.7, lv, 1180.0, 1.013, 1.013)
             for lv in (4.0, 2.0, 1.0, 0.25)]
    assert flows == sorted(flows, reverse=True)
    assert flows[0] / flows[2] == pytest.approx(2.0, rel=1e-12)


# --------------------------------------------------------------------------------------
# Check valve
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("p_up,p_down", [
    (5.60, 4.20), (6.00, 4.20), (4.60, 4.20), (4.24, 4.20), (4.20, 4.20), (3.90, 4.20)])
@pytest.mark.parametrize("p_crack", [0.0, 0.028])
def test_check_valve_matches_v1(p_up, p_down, p_crack, v1):
    assert valve.check_valve_kgh(38000.0, p_up, p_down, 1.40, p_crack) == \
        v1.check_valve_kgh(38000.0, p_up, p_down, 1.40, p_crack)


def test_the_check_valve_is_bit_exact_at_its_design_differential():
    """The identity is exact in the ARITHMETIC, which is a narrower claim than it looks.

    `w_des . sqrt(dp/ref)` returns `w_des` to the last bit when `p_up - p_down - p_crack`
    evaluates to the same float as `dp_des - p_crack`. Decimal plant pressures rarely do:
    5.60 - 4.20 is 1.4000000000000004, not 1.40, and the check valve then returns
    37999.99999999999. The binary-exact values below isolate the property being asserted
    from that separate, and unavoidable, subtraction error.

    The practical consequence is recorded rather than papered over: a site anchored on
    decimal pressures is bit-exact only if its design differential is stored as the
    subtraction of its two design pressures, not as a rounded decimal. That is how the unit
    modules must derive `dp_des_bar`.
    """
    assert valve.check_valve_kgh(38000.0, 5.5, 4.0, 1.5, 0.03125) == 38000.0
    assert valve.check_valve_kgh(38000.0, 5.5, 4.0, 1.5) == 38000.0
    # The same site written in decimals misses by one ulp — hence the rule above.
    assert valve.check_valve_kgh(38000.0, 5.60, 4.20, 1.40, 0.028) == pytest.approx(
        38000.0, rel=1e-12)
    assert valve.check_valve_kgh(38000.0, 5.60, 4.20, 5.60 - 4.20, 0.028) == 38000.0


def test_the_crack_band_is_shut_not_merely_passing_very_little():
    """A diode, not a resistor. Between seated and cracked the line is closed."""
    assert valve.check_valve_kgh(38000.0, 4.21, 4.20, 1.40, 0.028) == 0.0
    assert valve.check_valve_kgh(38000.0, 4.20, 4.20, 1.40, 0.028) == 0.0
    assert valve.check_valve_kgh(38000.0, 3.00, 4.20, 1.40, 0.028) == 0.0
    assert valve.check_valve_kgh(38000.0, 4.24, 4.20, 1.40, 0.028) > 0.0


def test_the_check_valve_is_not_capped_at_its_design_flow():
    """V1 finding D-5: a `min(1, sqrt(dP/dP_des))` delivery fraction cannot pass more than
    design however hard the line pushes. A real orifice can, and does."""
    assert valve.check_valve_kgh(38000.0, 12.0, 4.20, 1.40) > 38000.0


# --------------------------------------------------------------------------------------
# Relief — API 520 Part I
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("k", [1.10, 1.30, 1.31, 1.40])
def test_choked_pressure_ratio_matches_v1(k, v1):
    assert relief.psv_choked_ratio(k) == v1.psv_choked_ratio(k)


@pytest.mark.parametrize("area_m2", [0.0, 1.0, 0.00284, 0.01])
@pytest.mark.parametrize("p1,t1,mw", [
    (161.013, 463.15, 28.6), (180.0, 470.0, 28.6), (18.9, 423.15, 22.0),
    (4.6, 393.15, 17.03), (4.6, 393.15, 0.0)])
def test_psv_capacity_matches_v1(area_m2, p1, t1, mw, v1):
    assert relief.psv_api520_choked_kgh(area_m2, p1, t1, mw) == \
        v1.psv_api520_choked_kgh(area_m2, p1, t1, mw)


def test_psv_area_back_solved_from_a_rated_capacity_matches_v1(v1):
    assert relief.psv_area_from_rated_m2(96000.0, 161.013, 463.15, 28.6) == \
        v1.psv_area_from_rated_m2(96000.0, 161.013, 463.15, 28.6)


def test_the_rated_point_is_reproduced_whatever_is_assumed_for_the_coefficients():
    """Why the anchor is worth having: Kd, Kb, Kc, k and Z all cancel on the round trip.

    None of them is documented for these valves, so the model must not depend on them at the
    one point that IS documented — the nameplate capacity.
    """
    rated = dict(w_rated_kgh=96000.0, p1_rated_bara=161.013, t1_rated_k=463.15,
                 mw_rated=28.6)
    for kd, kb, k in ((0.975, 1.0, 1.30), (0.865, 0.92, 1.18), (0.62, 1.0, 1.40)):
        area = relief.psv_area_from_rated_m2(kd=kd, kb=kb, k=k, **rated)
        back = relief.psv_api520_choked_kgh(area, rated["p1_rated_bara"],
                                            rated["t1_rated_k"], rated["mw_rated"],
                                            k=k, kd=kd, kb=kb)
        assert back == pytest.approx(rated["w_rated_kgh"], rel=1e-12)


def test_relief_capacity_is_linear_in_the_upstream_pressure_not_in_the_overpressure():
    """A spring PSV pops and then flows choked; it does not ramp from zero at the set point.

    Doubling the absolute relieving pressure doubles the capacity. The ramp form this
    replaces would have passed a few per cent just above set, which teaches the wrong
    recovery.
    """
    area = relief.psv_area_from_rated_m2(96000.0, 161.013, 463.15, 28.6)
    at_set = relief.psv_api520_choked_kgh(area, 161.013, 463.15, 28.6)
    at_double = relief.psv_api520_choked_kgh(area, 322.026, 463.15, 28.6)
    assert at_double == pytest.approx(2.0 * at_set, rel=1e-12)
    assert at_set == pytest.approx(96000.0, rel=1e-12)
