"""V1 vs V1.1 — the deviation-consequence physics shared by every vessel and drain valve.

What is proven here
-------------------
`ureasim.units.consequence.seal` is compared against V1's `backend/consequence.py`, which is
importable directly: it depends only on the standard library, so both implementations run in
the same interpreter and every assertion below compares V1's own bytes against the rewrite's.

`ureasim.units.consequence.crystallisation` is compared against V1's `_f_flow`, which lives
inside `main.py` and therefore comes through the AST lifter.

Why both halves of the comparison matter
-----------------------------------------
These functions decide what a vessel does after it has run dry, which is the one state an
operator has to be able to recognise and reverse. A silent drift in the seal ramp would move
the level at which blow-through starts; a drift in the expansion factor would move the choke
point, and with it the ceiling on how much vapour a dry vessel can put into the section below
it. Neither would show up in a design-point balance, because both are exactly zero there.
"""

from __future__ import annotations

import math

import pytest

from ureasim.units.consequence.crystallisation import mushy_flow_factor
from ureasim.units.consequence.seal import (
    blowthrough_kgh,
    expansion_factor,
    gas_density_ideal,
    seal_fraction,
)

from .v1_loader import lift, load, v1_available

pytestmark = pytest.mark.skipif(not v1_available(),
                                reason="V1 reference tree not present on this machine")


@pytest.fixture(scope="module")
def v1():
    """V1's `consequence` module, imported whole."""
    return load("consequence")


@pytest.fixture(scope="module")
def v1_f_flow():
    """V1's `_f_flow`, lifted out of `main.py`, which cannot be imported."""
    return lift(["_f_flow"], seed={"math": math})["_f_flow"]


# ======================================================================================
# 1. The liquid seal
# ======================================================================================

#: Levels spanning the whole ramp and both sides of it, in transmitter %. The interesting
#: region is 0 to 3 %, so it is sampled finely; the rest confirms the flats.
SEAL_LEVELS = (-5.0, -0.001, 0.0, 0.25, 0.5, 1.0, 1.5, 2.0, 2.5, 2.999, 3.0,
               3.001, 5.0, 12.0, 50.0, 100.0, 140.0)


@pytest.mark.parametrize("level", SEAL_LEVELS)
def test_seal_fraction_matches_v1(v1, level):
    """The seal ramp is the same function of level in both implementations."""
    assert seal_fraction(level) == v1.seal_fraction(level)


@pytest.mark.parametrize("level", SEAL_LEVELS)
@pytest.mark.parametrize("seal_pct,band_pct", [(0.0, 3.0), (5.0, 3.0), (10.0, 8.0),
                                               (2.0, 0.5), (0.0, 1e-12)])
def test_seal_fraction_matches_v1_off_default(v1, level, seal_pct, band_pct):
    """A vessel that passes its own nozzle elevation and bore gets the same ramp too.

    The last case drives `band_pct` below the 1e-9 guard, which is the only branch in the
    function; both implementations must take it identically.
    """
    assert seal_fraction(level, seal_pct, band_pct) \
        == v1.seal_fraction(level, seal_pct, band_pct)


def test_seal_band_default_matches_v1(v1):
    """The 3 % default is the same constant, not a coincidence of two literals."""
    assert seal_fraction(1.5) == v1.seal_fraction(1.5, 0.0, v1.SEAL_BAND_PCT_DEFAULT)


# ======================================================================================
# 2. Gas density
# ======================================================================================

#: (P bar a, T deg C, MW g/mol) — the synthesis loop, the LP recirculation section, the
#: desorption section and a vacuum node, so the whole pressure range the plant runs over.
DENSITY_STATES = (
    (140.7, 172.0, 30.0),      # LV-322501, stripper vapour at the sump
    (144.0, 183.0, 26.4),      # the reactor overflow's vapour space
    (4.2, 140.0, 24.0),        # LV-323501, 323C003
    (3.5, 95.0, 22.0),         # LV-323505, 323F004
    (1.013, 25.0, 28.96),      # atmosphere
    (0.12, 60.0, 18.02),       # a vacuum node on steam
    (1e-12, -250.0, 44.01),    # both guards at once
)


@pytest.mark.parametrize("p_bara,t_c,mw", DENSITY_STATES)
def test_gas_density_matches_v1(v1, p_bara, t_c, mw):
    """Ideal-gas density agrees exactly, including where both floors clip."""
    assert gas_density_ideal(p_bara, t_c, mw) == v1.gas_density_ideal(p_bara, t_c, mw)


def test_gas_constant_is_the_same_number(v1):
    """The rewrite takes R from `core.units_of_measure`; it must be V1's own value.

    An 8.314 against V1's 8.314462618 would be a 0.006 % density error — invisible in any
    single test and systematically wrong in every blow-through rate.
    """
    from ureasim.core.units_of_measure import R_GAS_J

    assert R_GAS_J == v1.R_GAS_J


# ======================================================================================
# 3. The IEC 60534 expansion factor
# ======================================================================================

#: (dP bar, P1 bar a) — subcritical, at the choke point, and far past it.
EXPANSION_STATES = (
    (0.0, 140.7), (1.0, 140.7), (10.0, 140.7), (90.0, 140.7),
    (91.455, 140.7),            # x = x_ch exactly: F_k.x_T = (1.30/1.40).0.70 = 0.65
    (100.0, 140.7), (136.7, 140.7), (140.7, 140.7), (200.0, 140.7),
    (0.2, 4.2), (2.73, 4.2), (4.2, 4.2),
    (-1.0, 4.2),                # a negative drop: the clamp floor
    (1.0, 0.0),                 # the P1 guard
)


@pytest.mark.parametrize("dp_bar,p1_bara", EXPANSION_STATES)
def test_expansion_factor_matches_v1(v1, dp_bar, p1_bara):
    """Y, the effective drop and the choke flag all agree exactly."""
    assert expansion_factor(dp_bar, p1_bara) == v1.expansion_factor(dp_bar, p1_bara)


@pytest.mark.parametrize("x_t,gamma", [(0.70, 1.30), (0.75, 1.40), (0.60, 1.20),
                                       (0.90, 1.667), (1e-9, 1.30)])
def test_expansion_factor_matches_v1_off_default(v1, x_t, gamma):
    """Another trim style or another vapour gives the same Y in both implementations.

    The last case drives `x_ch` onto its 1e-6 floor, which is the function's only guard.
    """
    for dp_bar, p1_bara in EXPANSION_STATES:
        assert expansion_factor(dp_bar, p1_bara, x_t, gamma) \
            == v1.expansion_factor(dp_bar, p1_bara, x_t, gamma)


def test_expansion_defaults_match_v1(v1):
    """x_T = 0.70 and gamma = 1.30 in the rewrite are V1's own defaults."""
    assert expansion_factor(50.0, 140.7) == v1.expansion_factor(50.0, 140.7, 0.70, 1.30)


# ======================================================================================
# 4. Blow-through
# ======================================================================================

#: LV-322501's own arguments: the stripper-bottoms design duty, the bottoms density, the
#: design letdown differential, and the stripper vapour at the sump.
LV322501 = dict(m_liq_des_kgh=130482.0, rho_liq=1134.64, dp_des_bar=140.0,
                rho_gas=27.0, p_up_bara=140.7, dp_bar=136.7)

#: LV-323501's, which is the same event two sections downstream at a thirtieth of the head.
LV323501 = dict(m_liq_des_kgh=39000.0, rho_liq=1080.0, dp_des_bar=1.9,
                rho_gas=2.6, p_up_bara=4.2, dp_bar=1.9)


@pytest.mark.parametrize("valve", [LV322501, LV323501])
@pytest.mark.parametrize("seal", [0.0, 0.05, 0.25, 0.5, 0.75, 0.999, 1.0, 1.5, -0.2])
@pytest.mark.parametrize("theta", [0.0, 0.05, 0.461, 1.0, 1.4, -0.1])
def test_blowthrough_matches_v1(v1, valve, seal, theta):
    """Every combination of stroke and remaining seal gives the same rate.

    This is the grid that matters: the stroke and the seal are the two things that move
    during the upset, and the product of them is what the downstream section receives.
    """
    ours = blowthrough_kgh(valve["m_liq_des_kgh"], valve["rho_liq"], valve["dp_des_bar"],
                           theta, valve["rho_gas"], valve["p_up_bara"], valve["dp_bar"],
                           seal)
    theirs = v1.blowthrough_kgh(valve["m_liq_des_kgh"], valve["rho_liq"],
                                valve["dp_des_bar"], theta, valve["rho_gas"],
                                valve["p_up_bara"], valve["dp_bar"], seal)
    assert ours == theirs


@pytest.mark.parametrize("dp_bar", [0.0, -3.0, 1e-9, 0.5, 60.0, 136.7, 300.0])
def test_blowthrough_matches_v1_over_the_differential(v1, dp_bar):
    """Including where the head collapses and where the valve is deep into choke."""
    args = (130482.0, 1134.64, 140.0, 0.461, 27.0, 140.7, dp_bar, 0.4)
    assert blowthrough_kgh(*args) == v1.blowthrough_kgh(*args)


@pytest.mark.parametrize("rho_gas,rho_liq,dp_des", [(0.0, 1134.64, 140.0),
                                                    (27.0, 0.0, 140.0),
                                                    (27.0, 1134.64, 0.0),
                                                    (0.0, 0.0, 0.0)])
def test_blowthrough_guards_match_v1(v1, rho_gas, rho_liq, dp_des):
    """The three 1e-9 floors are hit identically rather than raising in either version."""
    args = (130482.0, rho_liq, dp_des, 0.461, rho_gas, 140.7, 136.7, 0.4)
    assert blowthrough_kgh(*args) == v1.blowthrough_kgh(*args)


def test_blowthrough_defaults_match_v1(v1):
    """The trim defaults reach `expansion_factor` unchanged through `blowthrough_kgh`."""
    args = (130482.0, 1134.64, 140.0, 0.461, 27.0, 140.7, 136.7, 0.4)
    assert blowthrough_kgh(*args) == v1.blowthrough_kgh(*args, 0.70, 1.30)


# ======================================================================================
# 5. The mushy zone
# ======================================================================================

#: The two boundaries V1 actually uses: 132.7 deg C for the urea melt at the stripper
#: bottoms, 60.0 deg C for the carbamate at the 322E003 overflow.
@pytest.mark.parametrize("t_cryst", [132.7, 60.0])
@pytest.mark.parametrize("offset", [-20.0, -5.0, -0.001, 0.0, 0.5, 2.5, 4.999, 5.0,
                                    5.001, 11.0, 40.0])
def test_mushy_flow_factor_matches_v1(v1_f_flow, t_cryst, offset):
    """The ramp is the same function of temperature in both implementations."""
    t_c = t_cryst + offset
    assert mushy_flow_factor(t_c, t_cryst) == v1_f_flow(t_c, t_cryst)


@pytest.mark.parametrize("dt_mush", [5.0, 1.0, 12.0])
def test_mushy_flow_factor_matches_v1_off_default(v1_f_flow, dt_mush):
    """A wider or narrower mushy band gives the same ramp too."""
    for offset in (-2.0, 0.0, 0.5, 3.0, 12.0):
        assert mushy_flow_factor(132.7 + offset, 132.7, dt_mush) \
            == v1_f_flow(132.7 + offset, 132.7, dt_mush)


def test_mushy_band_default_matches_v1(v1_f_flow):
    """The 5 deg C band in the rewrite is V1's own default argument."""
    assert mushy_flow_factor(134.0, 132.7) == v1_f_flow(134.0, 132.7, 5.0)


def test_mushy_flow_factor_takes_the_engine_limiter(v1_f_flow):
    """A NaN temperature returns 1.0, matching `_f_flow` and NOT V1's consequence variant.

    V1 holds two copies of this relation. `main.py`'s `_f_flow` uses the engine limiter, so
    a NaN comes back as the upper bound; `consequence.mushy_flow_factor` uses the
    consequence-layer limiter, so a NaN comes back as a NaN. They differ only here, and
    nothing in V1 calls the second one. The rewrite ports the one that is reachable, and
    this test states which that is so the choice is visible rather than incidental.
    """
    assert mushy_flow_factor(float("nan"), 132.7) == 1.0
    assert v1_f_flow(float("nan"), 132.7) == 1.0


def test_v1_consequence_variant_is_unreachable(v1):
    """V1's generalised `mushy_flow_factor` exists and is never called — hence not ported.

    Pinned as a test rather than left as a comment, because if a later V1 read shows a call
    site appearing, the decision recorded in `handoff.md` has to be revisited.
    """
    assert hasattr(v1, "mushy_flow_factor")
    assert v1.mushy_flow_factor(134.0, 132.7) == mushy_flow_factor(134.0, 132.7)
    assert math.isnan(v1.mushy_flow_factor(float("nan"), 132.7))
