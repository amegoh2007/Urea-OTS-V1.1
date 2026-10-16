"""What the seal and blow-through relations DO — behaviour, with no V1 tree required.

Why this is separate from the equivalence suite
-----------------------------------------------
`tests/equivalence/test_consequence_equivalence.py` proves the port is V1. This file proves
the relations behave like a drain valve losing its seal. The second question does not need
the V1 tree, so these tests keep running on a machine that has only the rewrite.

Five properties are pinned, each one an operating lesson and each one that a silent
regression would otherwise survive:

  * at any normal level the seal is EXACTLY 1.0 and the blow-through EXACTLY 0.0, so the
    design point is untouched by construction rather than by tolerance;
  * blow-through starts before the transmitter reads zero when the tap sits above the nozzle,
    and it is fully reversible — restoring level restores the seal;
  * the rate has a CEILING, because the valve chokes; pulling the downstream side further
    away buys no more flow;
  * the same event is far more violent for the LP section than for the HP one, because the
    volumetric ratio scales with `sqrt(rho_liq / rho_gas)`;
  * a lost seal does not stop the drain — it converts it, which is the lesson the `if level
    <= 0` guard this replaced could never teach.
"""

from __future__ import annotations

import math

import pytest

from ureasim.units.consequence.seal import (
    GAMMA_DEFAULT,
    SEAL_BAND_PCT_DEFAULT,
    X_T_DEFAULT,
    blowthrough_kgh,
    expansion_factor,
    gas_density_ideal,
    seal_fraction,
)

# --------------------------------------------------------------------------------------
# Two real valves, so the tests read against equipment rather than against arithmetic.
# --------------------------------------------------------------------------------------

#: LV-322501, the 322E001 stripper-bottoms letdown, at the design loop pressure: 130 t/h of
#: 1135 kg/m3 liquor across 136.7 bar. The vapour above it is the stripper's own top gas at
#: the sump, 144 kg/m3 at 140.7 bar a and 172 deg C once the SRK compressibility is applied.
#: These are exactly the arguments `synthesis.stripper_sump` passes at design.
LV322501 = dict(m_liq_des_kgh=130482.0, rho_liq=1134.64, dp_des_bar=136.7,
                rho_gas=144.05, p_up_bara=140.7, dp_bar=136.7)

#: LV-323501, the 323C003 rectifier drain: the same event two sections downstream, at a
#: seventieth of the head and with a vapour 50 times lighter.
LV323501 = dict(m_liq_des_kgh=39000.0, rho_liq=1080.0, dp_des_bar=1.9,
                rho_gas=2.6, p_up_bara=4.2, dp_bar=1.9)


def blow(valve: dict, theta: float, seal: float) -> float:
    """Blow-through for one of the two valves above, at a stroke and a remaining seal."""
    return blowthrough_kgh(valve["m_liq_des_kgh"], valve["rho_liq"], valve["dp_des_bar"],
                           theta, valve["rho_gas"], valve["p_up_bara"], valve["dp_bar"],
                           seal)


# ======================================================================================
# 1. The design anchor — exactly 1.0 and exactly 0.0
# ======================================================================================

@pytest.mark.parametrize("level", [3.0, 5.0, 12.0, 30.0, 50.0, 78.0, 100.0])
def test_seal_is_identically_one_at_every_normal_level(level):
    """Not approximately 1.0. Every consequence keyed on `(1 - seal)` must vanish exactly."""
    assert seal_fraction(level) == 1.0


@pytest.mark.parametrize("valve", [LV322501, LV323501])
@pytest.mark.parametrize("theta", [0.1, 0.461, 1.0, 2.0])
def test_blowthrough_is_identically_zero_while_sealed(valve, theta):
    """Zero by RETURN, not by arithmetic — the `seal >= 1.0` short circuit.

    The distinction matters at the design point: an arithmetic zero from a `(1 - 1.0)`
    multiply would still evaluate a square root of a ratio of guarded quantities, and any
    later change to those guards could leak a denormal into a balance that is meant to be
    bit-exact.
    """
    assert blow(valve, theta, 1.0) == 0.0
    assert blow(valve, theta, 1.5) == 0.0


@pytest.mark.parametrize("valve", [LV322501, LV323501])
def test_blowthrough_is_zero_when_the_valve_is_shut_or_the_head_has_gone(valve):
    """A shut valve and a collapsed differential both pass nothing, however dry the vessel."""
    assert blow(valve, 0.0, 0.0) == 0.0
    assert blow(valve, -0.1, 0.0) == 0.0
    args = dict(valve, dp_bar=0.0)
    assert blow(args, 1.0, 0.0) == 0.0
    args = dict(valve, dp_bar=-5.0)
    assert blow(args, 1.0, 0.0) == 0.0


# ======================================================================================
# 2. The seal ramp — early, continuous and reversible
# ======================================================================================

def test_seal_ramp_spans_exactly_the_nozzle_bore():
    """Fully open at the nozzle centreline, fully sealed one bore above it."""
    assert seal_fraction(0.0) == 0.0
    assert seal_fraction(SEAL_BAND_PCT_DEFAULT) == 1.0
    assert seal_fraction(SEAL_BAND_PCT_DEFAULT / 2.0) == pytest.approx(0.5)


def test_blowthrough_starts_before_the_transmitter_reads_zero():
    """A tap above the nozzle is the normal installation, and it is why this is a ramp.

    With the nozzle centreline at 8 % of span, the vessel is already passing gas while the
    transmitter still reads 9 %. A guard on `level <= 0` would show the operator a healthy
    drain right up to the point where it stopped being one.
    """
    seal = seal_fraction(9.0, seal_pct=8.0)
    assert 0.0 < seal < 1.0
    assert blow(LV322501, 1.0, seal) > 0.0
    # And it is gone again one bore higher, with no residue.
    assert seal_fraction(11.0, seal_pct=8.0) == 1.0
    assert blow(LV322501, 1.0, seal_fraction(11.0, seal_pct=8.0)) == 0.0


def test_the_seal_is_a_function_of_level_alone_so_recovery_is_exact():
    """Restoring level restores the seal bit-for-bit: no latch, no hysteresis, no state."""
    before = seal_fraction(40.0)
    for excursion in (1.2, 0.4, 0.0, -3.0, 0.9):
        seal_fraction(excursion)
    assert seal_fraction(40.0) == before


@pytest.mark.parametrize("valve", [LV322501, LV323501])
def test_blowthrough_rises_monotonically_as_the_seal_is_lost(valve):
    """The vessel does not step into blow-through; it slides into it."""
    rates = [blow(valve, 1.0, s) for s in (1.0, 0.9, 0.75, 0.5, 0.25, 0.1, 0.0)]
    assert all(b > a for a, b in zip(rates, rates[1:]))


@pytest.mark.parametrize("valve", [LV322501, LV323501])
def test_blowthrough_is_linear_in_the_lost_fraction(valve):
    """Half the nozzle uncovered passes half the gas — the `(1 - seal)` factor, alone.

    Worth pinning because it is the reason the relation cannot produce a runaway: the level
    ODE drives `seal` and `seal` scales the escape, so the feedback is bounded by the bore.
    """
    full = blow(valve, 1.0, 0.0)
    assert blow(valve, 1.0, 0.5) == pytest.approx(0.5 * full, rel=1e-12)
    assert blow(valve, 1.0, 0.25) == pytest.approx(0.75 * full, rel=1e-12)


# ======================================================================================
# 3. The choke ceiling
# ======================================================================================

def test_expansion_factor_runs_from_one_to_exactly_two_thirds():
    """Y is 1.0 at a vanishing drop and exactly 2/3 at and beyond the choke point."""
    y_zero, _, choked_zero = expansion_factor(0.0, 144.0)
    assert y_zero == 1.0
    assert choked_zero is False
    x_ch = (GAMMA_DEFAULT / 1.40) * X_T_DEFAULT
    y_ch, dp_ch, choked = expansion_factor(x_ch * 144.0, 144.0)
    assert y_ch == pytest.approx(2.0 / 3.0)
    assert dp_ch == pytest.approx(x_ch * 144.0)
    assert choked is True


def test_the_effective_drop_stops_growing_at_the_choke_point():
    """This is the ceiling. Past x_ch the downstream side has no further influence at all."""
    x_ch = (GAMMA_DEFAULT / 1.40) * X_T_DEFAULT
    reference = expansion_factor(x_ch * 144.0, 144.0)
    for dp_bar in (100.0, 120.0, 143.9, 144.0, 500.0):
        assert expansion_factor(dp_bar, 144.0) == reference


def test_blowthrough_has_a_ceiling_as_the_downstream_section_depressurises():
    """The trainable consequence: the LP section fills at a bounded rate, it does not explode.

    LV-322501 is already choked at its normal 140 bar differential, so blowing the downstream
    section down to vacuum adds nothing to what the stripper can put into it.
    """
    at_design_dp = blow(LV322501, 1.0, 0.0)
    to_vacuum = blow(dict(LV322501, dp_bar=143.9), 1.0, 0.0)
    assert to_vacuum == at_design_dp


# ======================================================================================
# 4. Mass, volume, and why the LP section suffers more
# ======================================================================================

def test_a_lost_seal_converts_the_drain_rather_than_stopping_it():
    """LV-322501 fully uncovered still passes 25 t/h — as gas, against 130 t/h of liquid.

    The number is the whole argument for deriving the rate instead of picking one: at the
    design stroke and the design loop pressure it lands on 25.4 t/h, against the 25 t/h that
    had been hand-entered for this one valve in V1, and the same equation now applies to
    every other drain valve in the plant without a second constant.
    """
    rate = blow(LV322501, 1.0, 0.0)
    assert rate == pytest.approx(25_400.0, rel=0.01)
    assert rate < LV322501["m_liq_des_kgh"]


def test_the_volumetric_ratio_is_what_makes_the_lp_event_the_violent_one():
    """Mass falls at both valves; volume does not, and volume is what a vessel sees.

    The ratio is `Y . sqrt(rho_liq / rho_gas)` at a matched differential. At 140.7 bar a the
    stripper vapour is dense (144 kg/m3) so the sump passes only about 1.5 times the
    volume; at 4.2 bar a the rectifier vapour is 2.6 kg/m3 and the same event passes about
    16 times the volume, which is why the LP section is the one that overpressures.
    """
    hp_vol = blow(LV322501, 1.0, 0.0) / LV322501["rho_gas"] \
        / (LV322501["m_liq_des_kgh"] / LV322501["rho_liq"])
    lp_vol = blow(LV323501, 1.0, 0.0) / LV323501["rho_gas"] \
        / (LV323501["m_liq_des_kgh"] / LV323501["rho_liq"])
    assert hp_vol == pytest.approx(1.53, abs=0.1)
    assert lp_vol == pytest.approx(15.7, abs=1.0)
    assert lp_vol > hp_vol

    # And in MASS terms both valves pass far less than their liquid duty, which is the half
    # of the story that makes a blow-through easy to miss on a flow indication alone.
    assert blow(LV322501, 1.0, 0.0) < 0.25 * LV322501["m_liq_des_kgh"]
    assert blow(LV323501, 1.0, 0.0) < 0.10 * LV323501["m_liq_des_kgh"]


# ======================================================================================
# 5. Gas density
# ======================================================================================

def test_gas_density_is_the_ideal_gas_law_in_plant_units():
    """One hand-computed point, so a units slip in the 1e5 or the 1/1000 cannot pass.

    Air at 1.01325 bar a and 25 deg C is 1.184 kg/m3, which is the value every engineer
    carries in their head.
    """
    assert gas_density_ideal(1.01325, 25.0, 28.96) == pytest.approx(1.184, abs=0.002)


def test_gas_density_is_linear_in_pressure_and_inverse_in_absolute_temperature():
    """The two dependencies the blow-through rate inherits."""
    base = gas_density_ideal(4.2, 140.0, 24.0)
    assert gas_density_ideal(8.4, 140.0, 24.0) == pytest.approx(2.0 * base, rel=1e-12)
    hot = gas_density_ideal(4.2, 2 * 140.0 + 273.15, 24.0)
    assert hot == pytest.approx(base * (140.0 + 273.15) / (2 * 140.0 + 273.15 + 273.15),
                                rel=1e-12)


def test_gas_density_guards_do_not_raise_on_a_dead_node():
    """A node at zero pressure and a cryogenic temperature both clip rather than divide."""
    assert gas_density_ideal(0.0, 25.0, 28.96) > 0.0
    assert math.isfinite(gas_density_ideal(1.0, -273.15, 28.96))
