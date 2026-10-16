"""What 322F001 DOES — behaviour, with no V1 tree required.

Why this is separate from the equivalence suite
-----------------------------------------------
`tests/equivalence/test_ejector_equivalence.py` proves the port is V1. This file proves the
model is a jet pump. The second question does not need the V1 tree, so these tests keep
running on a machine that has only the rewrite.

Six behaviours are pinned, and two of them are findings the closure produced rather than
properties it was built to have:

  * the design point is the licensor duty exactly, and the spindle factor is a literal 1.0;
  * HV-322602 runs BACKWARDS — closing it raises entrainment — and the range it covers is
    about 38:1, not the 2.15:1 the retired law asserted;
  * the machine sits within 10 % of its own shutoff head, so a 9 % motive loss stalls the
    circulation of the entire HP loop;
  * TT-322012 does not fall smoothly on a motive rundown: it drops toward the motive's own
    temperature and then JUMPS to the suction temperature at zero flow;
  * the 322E003 sump's level multiplies the entrainment and the throat chokes at 1.25;
  * the discharge carries the motive's trace inerts, which is where the plant's CH4 and H2
    come from.
"""

from __future__ import annotations

import pytest

from ureasim.control import jet_pump
from ureasim.core.stream import MW_COMP
from ureasim.data import unit_322f001 as d
from ureasim.units.synthesis.ejector import (
    DESIGN,
    DISCHARGE_DES_KGH,
    T_DISCHARGE_DES_C,
    ejector_322f001,
)

MOTIVE = d.MOTIVE_DES_KGH
T_MOTIVE = d.MOTIVE_T_DES_C
OPEN = d.OPEN_DES_PCT


def run(motive=None, t_motive=None, opening=None, **kwargs):
    """The ejector at design, with named arguments replaced."""
    return ejector_322f001(MOTIVE if motive is None else motive,
                           T_MOTIVE if t_motive is None else t_motive,
                           OPEN if opening is None else opening, **kwargs)


# ======================================================================================
# 1. The design anchor
# ======================================================================================

def test_the_design_call_is_the_licensor_duty():
    """The entrainment is the design suction EXACTLY, not to a tolerance.

    That is what the ratio-of-the-closure-to-itself construction buys. The back-solved areas
    do not multiply back through to the original float, so an absolute form would land a few
    ulps away and the boot pin asserts this to the bit.
    """
    assert DESIGN.phi_spindle == 1.0
    assert DESIGN.suction_kgh == d.SUCTION_DES_TOTAL_KGH
    assert DESIGN.total_kgh == MOTIVE + d.SUCTION_DES_TOTAL_KGH
    assert DESIGN.stalled is False
    assert DESIGN.cavitating is False


def test_the_design_discharge_and_temperature():
    """100.3 t/h at 107.6 C — the 322E002 liquid feed and TT-322012."""
    assert DISCHARGE_DES_KGH == pytest.approx(100_323.4, abs=0.1)
    assert T_DISCHARGE_DES_C == pytest.approx(107.57, abs=0.01)
    assert DESIGN.mu == pytest.approx(1.34608, abs=1e-5)
    assert DESIGN.mw == pytest.approx(19.945, abs=0.001)


def test_the_design_geometry_is_a_falsifiable_prediction():
    """A 16.7 mm nozzle in a 50.2 mm throat, at 89 m/s and 16 m/s.

    Those four numbers are the model's prediction of what is inside a scan it cannot read,
    and the throat velocity is the reason this root was taken rather than the other: the
    large-area-ratio root puts the carbamate through at 54 m/s, which is an erosion rate.
    10-20 m/s is where a liquid jet pump is drawn.
    """
    assert d.GEOMETRY["d_t_mm"] == pytest.approx(16.72, abs=0.01)
    assert d.GEOMETRY["d_m_mm"] == pytest.approx(50.23, abs=0.01)
    assert d.GEOMETRY["v_nozzle_ms"] == pytest.approx(89.4, abs=0.1)
    assert 10.0 < d.GEOMETRY["v_throat_ms"] < 20.0
    assert d.GEOMETRY["b"] == pytest.approx(0.1108, abs=0.0001)


def test_the_closure_is_single_rooted_at_these_densities():
    """The property the abandoned attempt did not have, asserted rather than assumed."""
    assert jet_pump.monotonicity_margin(d.RHO_SUCTION, d.RHO_DISCHARGE) \
        == pytest.approx(1.792, abs=0.001)


def test_the_discharge_falls_monotonically_with_entrainment():
    """Which is what single-rooted MEANS, checked on the curve rather than on the bound."""
    rises = [jet_pump.discharge_rise_bar(MOTIVE, m_s, d.A_T_DES_M2, d.A_M_M2,
                                         604.8, d.RHO_SUCTION, d.RHO_DISCHARGE)
             for m_s in (0.0, 20_000.0, 57_561.0, 100_000.0, 200_000.0, 400_000.0)]
    assert all(b < a for a, b in zip(rises, rises[1:]))
    # And the first of them is the shutoff head, which is where the stall margin comes from.
    assert rises[0] == pytest.approx(d.SHUTOFF_DES_BAR, rel=1e-12)


# ======================================================================================
# 2. HV-322602 runs backwards
# ======================================================================================

def test_closing_the_spindle_raises_entrainment():
    """The inverse law, and it is derived rather than asserted.

    The motive comes from positive-displacement pumps, so the valve cannot change the mass
    flow — only the area it leaves through. At constant mass a smaller area raises the jet
    momentum `m_p^2/(rho A_t)` and therefore the head the pump can develop, and more head
    available means more entrainment at the same lift.

    An operator who treats HV-322602 like a throttle will get the opposite of what they
    intend, which is precisely why it is worth a test of its own.
    """
    capacities = [run(opening=theta).suction_kgh
                  for theta in (10.0, 25.0, 50.0, 74.0, 90.0, 100.0)]
    assert all(b < a for a, b in zip(capacities, capacities[1:]))


def test_the_spindle_range_is_far_wider_than_the_retired_law_asserted():
    """About 38:1 across the DDS band, against the 2.15:1 of `EJ_SPINDLE_R`.

    A FINDING, not a tuning. The retired rangeability was itself back-solved from this same
    free-area map, but through the linear-ish capacity relation the old model assumed — and
    that assumed relation is exactly what the momentum balance replaces. The machine runs
    close to its own shutoff head, where capacity is a steep function of jet momentum, so
    the derived range is an order of magnitude wider.
    """
    widest = run(opening=10.0).suction_kgh
    narrowest = run(opening=100.0).suction_kgh
    assert widest / narrowest == pytest.approx(37.7, abs=1.0)
    assert widest / narrowest > 10.0 * 2.1517


def test_the_spindle_factor_is_exactly_one_at_the_design_opening():
    """So the design duty is untouched by the spindle model, by construction."""
    assert run(opening=OPEN).phi_spindle == 1.0


@pytest.mark.parametrize("opening", [-50.0, 0.0, 5.0, 9.999])
def test_the_spindle_holds_below_its_stated_band(opening):
    """The DDS states the free-area map over the travel band; below it the model holds.

    Extrapolating a datasheet map past its own stated range would be inventing data, which
    §4 of the agent directives forbids, so the stroke clips at 10 % instead.
    """
    assert run(opening=opening).suction_kgh == run(opening=10.0).suction_kgh


# ======================================================================================
# 3. Stall — the finding that matters most for training
# ======================================================================================

def test_the_machine_runs_within_ten_per_cent_of_its_own_shutoff_head():
    """The design lift is 4.2 bar against a 5.11 bar shutoff. There is very little margin."""
    lift = d.P_DISCHARGE_DES_BARA - d.P_SUCTION_DES_BARA
    assert lift == pytest.approx(4.2, abs=1e-9)
    assert d.SHUTOFF_DES_BAR == pytest.approx(5.106, abs=0.001)
    assert d.STALL_PHI_MOTIVE == pytest.approx(0.907, abs=0.001)


def test_a_nine_per_cent_motive_loss_stops_the_whole_hp_loop():
    """And the collapse before it is steep, which is the operating lesson.

    Half the entrainment is gone by the time the motive is 5 % low. There is no gentle
    turndown here: the ejector is the loop's only circulator, so this is the fastest way to
    stop the HP loop that does not involve a trip.
    """
    assert run(motive=0.95 * MOTIVE).suction_kgh < 0.55 * d.SUCTION_DES_TOTAL_KGH
    assert run(motive=0.92 * MOTIVE).suction_kgh < 0.20 * d.SUCTION_DES_TOTAL_KGH
    just_above = run(motive=(d.STALL_PHI_MOTIVE + 0.0005) * MOTIVE)
    just_below = run(motive=(d.STALL_PHI_MOTIVE - 0.0005) * MOTIVE)
    assert just_above.stalled is False
    assert just_below.stalled is True
    assert just_below.suction_kgh == 0.0


def test_stall_is_the_closure_speaking_and_not_a_fitted_knee():
    """Zero entrainment exactly, with no recovery fraction and no convexity exponent.

    V1's retired law put the knee at a motive fraction of 0.20 with a quadratic recovery to
    0.35 and called everything above that healthy. The momentum balance says the machine
    stalls at 0.907. The two are not close, and only the second follows from anything.
    """
    for fraction in (0.90, 0.75, 0.50, 0.20, 0.05):
        result = run(motive=fraction * MOTIVE)
        assert result.stalled is True
        assert result.suction_kgh == 0.0
        assert result.mu == 0.0


def test_a_stalled_ejector_still_delivers_its_motive():
    """It stops ENTRAINING; it does not stop flowing. 322E002 still gets the ammonia."""
    stalled = run(motive=0.5 * MOTIVE)
    assert stalled.stalled is True
    assert stalled.total_kgh == pytest.approx(0.5 * MOTIVE, rel=1e-12)
    assert stalled.comp_kgh["NH3"] > 0.0


# ======================================================================================
# 4. TT-322012, and the step at the bottom of a rundown
# ======================================================================================

def test_the_discharge_temperature_falls_as_the_entrainment_goes():
    """The motive is cold and the carbamate is hot, so losing suction cools the discharge."""
    temperatures = [run(motive=f * MOTIVE).t_c for f in (1.0, 0.97, 0.95, 0.93, 0.91)]
    assert all(b < a for a, b in zip(temperatures, temperatures[1:]))
    assert temperatures[0] == pytest.approx(107.57, abs=0.01)


def test_a_fully_stalled_ejector_reads_the_motive_temperature():
    """Pure ammonia through a dead jet pump, scaled by the two heat capacities."""
    stalled = run(motive=0.5 * MOTIVE)
    assert stalled.t_c == pytest.approx(T_MOTIVE * d.CP_MOTIVE / d.CP_DISCHARGE, rel=1e-12)
    assert stalled.t_c == pytest.approx(39.18, abs=0.01)


def test_the_no_flow_branch_reads_the_suction_temperature_instead():
    """A dead pump with NO motive at all reads the stagnant carbamate backed up into it.

    That is the right answer and it is the opposite of intuition: TT-322012 RISES on a
    complete motive trip, because the cold ammonia that was holding the blend down has gone
    and only the hot 322E003 liquor is left against the thermowell.
    """
    dead = run(motive=0.0)
    assert dead.t_c == d.T_SUCTION_DES_C
    assert dead.total_kgh == 0.0
    assert dead.stalled is True


def test_the_two_branches_do_not_meet(recwarn):
    """TT-322012's ejector temperature steps 140 C between a trickle of motive and none.

    Approaching zero motive from above, the discharge is pure cold ammonia at 39.2 C. At a
    motive of 1e-6 kg/h and below, the no-flow branch hands back the 178.8 C suction
    temperature. Both are defensible descriptions of their own situation, and the threshold
    between them is a microgram per hour. Reproduced, per §5 of the agent directives: the
    published TT-322012 reads it through V1's 120 s thermal lag, so the screen ramps (handoff
    B-11, closed 2026-10-07; `tests/units/synthesis/test_indicators.py`).
    """
    trickle = run(motive=1.1e-6)
    dead = run(motive=1.0e-6)
    assert trickle.t_c == pytest.approx(39.18, abs=0.01)
    assert dead.t_c == d.T_SUCTION_DES_C
    assert dead.t_c - trickle.t_c > 139.0


# ======================================================================================
# 5. The 322E003 sump head, and the choked throat
# ======================================================================================

@pytest.mark.parametrize("level,expected", [(0.0, 0.0), (0.5, 0.5), (0.9, 0.9), (1.0, 1.0)])
def test_the_sump_level_multiplies_the_entrainment(level, expected):
    """The gravity head the closure does not model, entering as a ratio to its own design."""
    assert run(scrub_level_frac=level).suction_kgh \
        == pytest.approx(expected * d.SUCTION_DES_TOTAL_KGH, rel=1e-12)


@pytest.mark.parametrize("level", [1.25, 1.5, 2.0, 10.0])
def test_the_throat_chokes_at_the_hydraulic_ceiling(level):
    """A flooded scrubber cannot recirculate itself into the loop without limit.

    Above the ceiling the entrainment stops rising with head, which is what a choked throat
    does, and the un-pumpable excess backs up in the 322E003 sump instead of being carried
    through 322E002 into the reactor — where the conversion self-loop would re-amplify it.
    """
    assert run(scrub_level_frac=level).suction_kgh \
        == pytest.approx(d.HYDRAULIC_FRAC_MAX * d.SUCTION_DES_TOTAL_KGH, rel=1e-12)


def test_the_ceiling_never_engages_at_design():
    """Being above 1.0, it is a limit on an upset and not a term in the design balance."""
    assert d.HYDRAULIC_FRAC_MAX > 1.0
    assert run(scrub_level_frac=1.0).suction_kgh == d.SUCTION_DES_TOTAL_KGH


def test_a_negative_level_is_treated_as_empty_rather_than_reversing():
    """A transmitter below zero must not make the ejector run backwards."""
    assert run(scrub_level_frac=-0.5).suction_kgh == 0.0


def test_the_block_valve_stops_the_suction_and_nothing_else():
    """XV-322903 shut: no carbamate, full motive, and the discharge is pure ammonia."""
    shut = run(xv_322903_open=False)
    assert shut.suction_kgh == 0.0
    assert shut.mu == 0.0
    assert shut.total_kgh == pytest.approx(MOTIVE, rel=1e-12)
    assert shut.stalled is False          # the JET is healthy; the line is isolated


# ======================================================================================
# 6. Composition
# ======================================================================================

def test_the_discharge_carries_the_motive_trace_inerts():
    """This is where the plant's CH4 and H2 come from, and the only place.

    PFD 204 puts 3.84 kmol/h of methane and 2.03 of hydrogen in the 322E003 vent. With a
    pure-ammonia motive the recycle tear had to create them out of nothing; with the PFD 116
    liquid row the balance closes to within 4 %.
    """
    comp = DESIGN.comp_kgh
    assert comp["CH4"] / MW_COMP["CH4"] == pytest.approx(4.00, abs=0.05)
    assert comp["H2"] / MW_COMP["H2"] == pytest.approx(2.12, abs=0.05)
    assert d.SUCTION_DES_KGH["CH4"] == 0.0        # not from the scrubber overflow
    assert d.SUCTION_DES_KGH["H2"] == 0.0


def test_the_discharge_closes_on_its_two_feeds():
    """Mass in equals mass out, component by component. No reaction happens in a jet pump."""
    for k in MW_COMP:
        expected = MOTIVE * d.MOTIVE_W[k] + d.SUCTION_DES_KGH[k]
        assert DESIGN.comp_kgh[k] == pytest.approx(expected, rel=1e-12, abs=1e-12)
    assert sum(DESIGN.comp_kgh.values()) == pytest.approx(DESIGN.total_kgh, rel=1e-12)


def test_a_live_carbamate_split_changes_the_discharge_but_not_the_flow():
    """The entrained SPLIT is the previous tick's scrubber overflow; the MASS is hydraulic.

    An NH3-rich, CO2-lean overflow — a scrubber running hot, say — arrives as exactly the
    same tonnage and a different composition. Nothing in the jet pump reacts, so what comes
    out is the motive plus the entrained stream, species by species. The discharge
    TEMPERATURE does not move at all, because the heat balance is written on mass and two
    lumped specific heats rather than per species.
    """
    nh3_rich = {"CO2": 0.30, "NH3": 0.52, "H2O": 0.17, "Urea": 0.01,
                "CH4": 0.0, "H2": 0.0, "N2": 0.0, "O2": 0.0, "Biuret": 0.0}
    live = run(carb_frac=nh3_rich)
    assert live.suction_kgh == pytest.approx(DESIGN.suction_kgh, rel=1e-12)
    for k, frac in nh3_rich.items():
        expected = MOTIVE * d.MOTIVE_W[k] + DESIGN.suction_kgh * frac
        assert live.comp_kgh[k] == pytest.approx(expected, rel=1e-12, abs=1e-12)
    # CO2 0.30 is LEANER than the design overflow's 0.397, so that component falls.
    assert live.comp_kgh["CO2"] < DESIGN.comp_kgh["CO2"]
    assert live.comp_kgh["NH3"] > DESIGN.comp_kgh["NH3"]
    assert live.t_c == pytest.approx(DESIGN.t_c, rel=1e-9)


# ======================================================================================
# 7. Cavitation — a guard, not an operating state
# ======================================================================================

def test_the_cavitation_ceiling_is_unreachable_in_the_hp_loop():
    """At 140 bar a of suction the annulus cannot reach a vacuum, so the bound never binds.

    It becomes real only at a suction below about 0.2 bar a, which this machine never sees.
    That is because the vapour-pressure argument is left at its absolute-pressure floor: the
    322F001 seal-leg height is in no document in the reference archive, so the true NPSH
    limit cannot be stated. The bound that IS enforced is still a strict thermodynamic one —
    a static pressure cannot go negative — and this test records which of the two is running.
    """
    assert run().cavitating is False
    for p_s in (140.0, 50.0, 5.0, 1.0):
        assert run(p_suct_bara=p_s, p_disch_bara=p_s + 4.2).cavitating is False
    assert run(p_suct_bara=0.2, p_disch_bara=4.4).cavitating is True


def test_a_higher_lift_cuts_the_entrainment():
    """Which is the pump curve, read the way an operator meets it: more head, less flow."""
    flows = [run(p_suct_bara=140.0, p_disch_bara=p_d).suction_kgh
             for p_d in (141.0, 142.0, 144.2, 144.6, 145.0)]
    assert all(b < a for a, b in zip(flows, flows[1:]))
