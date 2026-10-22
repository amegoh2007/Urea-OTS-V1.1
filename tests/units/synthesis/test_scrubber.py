"""322E003 — what the HP scrubber DOES, as opposed to what it agrees with.

The equivalence suite proves this unit is V1's arithmetic to the bit. This one asks whether
that arithmetic behaves like a reactive absorber: does it recover the ammonia it is there to
recover, does it close per species, does the cooling-water loop respond the way a condenser
responds, and do the two operator traps it carries — the swell on LT-329501 and the choke
signature on TDY-329125 — actually appear.

Every number quoted in a docstring below was MEASURED from the module, not carried over from
a V1 comment.
"""

from __future__ import annotations

import math

import pytest

from ureasim.core.stream import MW_COMP, atom_ratio
from ureasim.data.unit_322e003 import (
    CCW_KGH_DES,
    CCW_T_IN_DES_C,
    COND_CHOKE_MIN,
    HIC604_DES_PCT,
    HOLDUP_MAX_KG,
    HOLDUP_NLL_KG,
    LEVEL_NLL_PCT,
    OFFGAS_DES_KMOLH,
    OFFGAS_NC_DES,
    OFFGAS_T_DES_C,
    OVERFLOW_DES_KMOLH,
    OVERFLOW_P_DES_BARA,
    OVERFLOW_T_DES_C,
    Q_CCW_DES_KW,
    T_PROC_C,
    VENT_INERTS,
    WASH_KMOLH_DES,
)
from ureasim.data.unit_322r001 import (
    C_ATOMS,
    NC_SPAN_MAX,
    N_ATOMS,
    OFFGAS_DES_KMOLH as REACTOR_OFFGAS_DES_KMOLH,
)
from ureasim.units.synthesis.scrubber import (
    DESIGN,
    condensation_capacity,
    condensing_temperature_c,
    liquor_bubble_p_bara,
    lt_329501_indication,
    lt_329501_noise,
    lt_329501_swell,
    scrubber_322e003,
    sump_level_pct,
    vent_kmolh,
)


def _kgh(vec: dict) -> float:
    """Mass flow [kg/h] of a molar vector."""
    return sum(vec[k] * MW_COMP[k] for k in MW_COMP)


def _run(**kw):
    """Drive the unit off the design reactor off-gas, overriding what the case names."""
    return scrubber_322e003(REACTOR_OFFGAS_DES_KMOLH,
                            kw.pop("co2_scale", 1.0),
                            kw.pop("t_ccw_in_c", CCW_T_IN_DES_C),
                            kw.pop("m_ccw_kgh", CCW_KGH_DES), **kw)


# ==========================================================================================
# What the vessel is for
# ==========================================================================================

def test_the_scrubber_recovers_996_percent_of_the_ammonia_offered():
    """The number that pays for the equipment.

    1329.2 kmol/h of ammonia enters the tubes and 5.35 leaves with the vent: **99.60 %
    recovery**. On a mass basis the plant vents 91.1 kg/h where the reactor off-gas alone
    carried 11 338 kg/h — so without this vessel the purge would throw away 11.3 t/h of
    ammonia to get rid of 58 kmol/h of nitrogen, oxygen, methane and hydrogen.
    """
    nh3_in = DESIGN.feed_kmolh["NH3"]
    nh3_out = DESIGN.offgas_kmolh["NH3"]
    assert nh3_in == pytest.approx(1329.23, abs=0.01)
    assert nh3_out == pytest.approx(5.351, abs=0.001)
    assert 1.0 - nh3_out / nh3_in == pytest.approx(0.9960, abs=0.0001)
    assert nh3_out * MW_COMP["NH3"] == pytest.approx(91.1, abs=0.1)
    assert REACTOR_OFFGAS_DES_KMOLH["NH3"] * MW_COMP["NH3"] == pytest.approx(11337.6, abs=0.1)


def test_the_vent_is_89_percent_inert_which_is_the_point_of_purging():
    """Nearly nine tenths of what leaves is something the loop cannot use.

    Measured 89.26 mol %. A purge whose inert fraction were low would mean the wash had
    failed, and the inert fraction is the cleanest single indicator of that.
    """
    total = sum(DESIGN.offgas_kmolh.values())
    inert = sum(DESIGN.offgas_kmolh[k] for k in VENT_INERTS)
    assert inert / total == pytest.approx(0.8926, abs=0.0001)


def test_every_inert_that_enters_leaves_and_none_of_it_dissolves():
    """The structural claim the vent closure is built on, checked per species.

    Nitrogen, oxygen, methane and hydrogen appear in the vent at exactly their feed rate —
    by the arithmetic, not within a tolerance — and at exactly zero in the overflow. A
    scrubber that dissolved its own nitrogen would be a new claim and there is no datum for
    one.
    """
    for k in VENT_INERTS:
        fed = REACTOR_OFFGAS_DES_KMOLH.get(k, 0.0) + WASH_KMOLH_DES[k]
        assert DESIGN.offgas_kmolh[k] == fed
        assert DESIGN.overflow_kmolh[k] == 0.0


def test_the_unit_closes_per_species_by_construction():
    """Feed minus vent minus overflow is zero for every component, at every state tested.

    This is not a numerical result, it is the consequence of solving the vent and taking the
    overflow by difference. The published residual is a diagnostic that reads exactly zero.
    """
    cases = [{}, {"co2_scale": 0.7}, {"cool_frac": 0.4}, {"wash_ratio": 1.3},
             {"choke_level_pct": 90.0}, {"hic604_pct": 100.0},
             {"liq_carry_kmolh": {"Urea": 40.0, "NH3": 120.0, "CO2": 27.0, "H2O": 66.0},
              "t_carry_c": 183.0, "cool_frac": 0.3}]
    for kw in cases:
        r = _run(**kw)
        for k in MW_COMP:
            assert r.feed_kmolh[k] - r.offgas_kmolh[k] - r.overflow_kmolh[k] \
                == pytest.approx(0.0, abs=1e-9), (kw, k)
        assert r.closure_resid == pytest.approx(0.0, abs=1e-9)


def test_the_design_call_lands_on_the_published_pfd_rows():
    """PFD streams 204 and 206, reproduced from the reactor off-gas and the wash alone.

    Vent 64.787 kmol/h / 1708.3 kg/h / 26.368 kg/kmol against the published 64.78 / 1708 /
    26.36; overflow 2517.49 kmol/h / 57 561.3 kg/h against 2517.69 / 57 564. Nothing was
    fitted to land there.
    """
    assert sum(DESIGN.offgas_kmolh.values()) == pytest.approx(64.78, abs=0.01)
    assert _kgh(DESIGN.offgas_kmolh) == pytest.approx(1708.0, abs=0.4)
    assert sum(DESIGN.overflow_kmolh.values()) == pytest.approx(2517.69, abs=0.25)
    assert _kgh(DESIGN.overflow_kmolh) == pytest.approx(57564.0, abs=3.0)
    for k in MW_COMP:
        assert DESIGN.offgas_kmolh[k] == OFFGAS_DES_KMOLH[k]
        assert DESIGN.overflow_kmolh[k] == OVERFLOW_DES_KMOLH[k]


# ==========================================================================================
# The wash, and what a surplus of it does
# ==========================================================================================

def test_a_surplus_wash_leaves_with_the_overflow_and_absorbs_nothing_extra():
    """Finding A-2's central claim, measured.

    Delivering 20 % more weak carbamate adds 7383 kg/h to the overflow and changes the vent
    by **exactly zero bytes** — the vented mass is the same float at 0.8, 1.0 and 1.2 — and
    the CO2 absorbed is likewise unchanged at 196.25 kmol/h.

    That is the physics: what the cold top can hold is set by the saturation and the inert
    rate, not by how much liquid is running past it. The absorption gain this replaced —
    0.15 kmol of CO2 per kmol of extra wash — was asserting the opposite.
    """
    short, design, surplus = (_run(wash_ratio=w) for w in (0.8, 1.0, 1.2))
    assert _kgh(short.offgas_kmolh) == _kgh(design.offgas_kmolh) == _kgh(surplus.offgas_kmolh)
    assert short.co2_abs == design.co2_abs == surplus.co2_abs
    assert design.co2_abs == pytest.approx(196.25, abs=0.01)
    assert _kgh(surplus.overflow_kmolh) - _kgh(design.overflow_kmolh) \
        == pytest.approx(7383.0, abs=1.0)


def test_the_wash_defaults_to_throughput_when_no_live_delivery_is_given():
    """Two paths to the same vector: the unit-test path scales with CO2, the engine path
    passes what 323P001 actually delivered. They agree when the two ratios agree."""
    assert _run(co2_scale=0.85).carb_kmolh == _run(co2_scale=0.85, wash_ratio=0.85).carb_kmolh


# ==========================================================================================
# The loop pressure
# ==========================================================================================

def test_the_vent_barely_responds_to_loop_pressure_and_the_sign_is_negative():
    """Measured **-1.089 kg/h per bar**, which is -0.064 % of the vent.

    Raising the loop pressure pushes the condensables back into the liquid, so the saturated
    vent shrinks — but the condensables are only 11 mol % of it, so the effect on the total
    is small. It matters that it is small: HV-322604's choked law moves the vent the other
    way at about +12 kg/h per bar, an order of magnitude harder, so the valve dominates the
    saturation and the loop cannot chase its own tail through this term.
    """
    lo, hi = (_run(p_loop_bara=p) for p in (139.7, 141.7))
    slope = (_kgh(hi.offgas_kmolh) - _kgh(lo.offgas_kmolh)) / 2.0
    assert slope == pytest.approx(-1.089, abs=0.002)
    assert slope / _kgh(DESIGN.offgas_kmolh) * 100.0 == pytest.approx(-0.0637, abs=0.0005)


def test_the_condensing_temperature_rises_with_pressure():
    """0.0709 K/bar on the 165 C pin (handoff B-16), and the sign is the whole reason the
    relation is written this way.

    A condenser at a higher pressure condenses MORE readily. V1's earlier formulation
    asserted the opposite and the loop fed back on itself: capacity fell, vapour was
    retained, the pressure rose, and capacity fell further.
    """
    assert condensing_temperature_c(OVERFLOW_P_DES_BARA) == OVERFLOW_T_DES_C
    assert condensing_temperature_c(130.0) < OVERFLOW_T_DES_C < condensing_temperature_c(150.0)
    slope = (condensing_temperature_c(141.7) - condensing_temperature_c(139.7)) / 2.0
    assert slope == pytest.approx(0.0709, abs=0.0005)


# ==========================================================================================
# The shell side
# ==========================================================================================

def test_the_design_duty_reproduces_both_published_temperatures_from_one_conductance():
    """The effectiveness-NTU inversion is the anchor, and it pins two numbers with one.

    At the design circulation the process side comes out at 178.8 C and the cooling-water
    return at exactly 95.0 C — a 15.0 K rise, which is TDY-329125's design reading. Neither
    was asserted; both fall out of the back-solved conductance.
    """
    assert DESIGN.q_ccw_kw == Q_CCW_DES_KW
    assert DESIGN.t_overflow_c == pytest.approx(OVERFLOW_T_DES_C, abs=1e-12)
    assert DESIGN.t_ccw_out_c == 95.0
    assert DESIGN.dt_ccw_c == 15.0


def test_throttling_the_cooling_water_heats_both_sides_and_never_diverges():
    """The pole a naive duty-over-flow balance has at zero water is gone.

    Measured on the 165 C pin (handoff B-16): at 200 t/h the overflow is 169.3 C and the return
    103.0; at 100 t/h the overflow is 182.5, still under the 185 C ceiling (on V1's 178.8 pin it
    was against it); at 30 t/h it is on the ceiling; at zero flow the effectiveness is exactly 1
    and both sit at 185.0 rather than at 1e9. The CCW rise TDY-329125 RISES as the flow falls —
    15.0 K at design, 105.0 K at no flow — because the same duty is being carried by less water.
    """
    seen = [(m, _run(m_ccw_kgh=m)) for m in (306000.0, 200000.0, 100000.0, 30000.0, 0.0)]
    rises = [r.dt_ccw_c for _, r in seen]
    assert rises == sorted(rises), "the CCW rise must grow monotonically as flow falls"
    assert seen[1][1].t_overflow_c == pytest.approx(169.30, abs=0.01)
    assert seen[1][1].t_ccw_out_c == pytest.approx(102.95, abs=0.01)
    assert seen[2][1].t_overflow_c == pytest.approx(182.47, abs=0.01)
    for _, r in seen[3:]:
        assert r.t_overflow_c == T_PROC_C
    assert seen[-1][1].eps_ht == 1.0
    assert seen[-1][1].t_ccw_out_c == T_PROC_C
    assert seen[-1][1].dt_ccw_c == pytest.approx(105.0, abs=0.01)


def test_the_condensation_ceiling_is_a_rail_with_room_below_it():
    """Design sits 20 C below the ceiling on the PFD's 165 C pin (handoff B-16, decided 2026-10-07).

    On V1's 178.8 C pin the margin was 6.2 C, and +7 % throughput, the purge valve below 24 %
    open, a 35 % stronger ejector spindle or half the cooling water each reached the rail on its
    own — above which the model reports the ceiling and stops telling a bad state from a worse
    one. On the PFD's pin those same excursions read 170.95, 173.00, 170.51 and 173.23 C, the
    purge valve shut 177.0 (the valve at 24 % on its 72 % anchor, B-18; 171.24 on V1's
    50 %). The rail is still reached, and by what should reach it: +23.5 %
    throughput, or the cooling water cut to 30 % of design (91.6 t/h).
    """
    assert T_PROC_C - OVERFLOW_T_DES_C == pytest.approx(20.0, abs=1e-9)
    for kw, t in (({"co2_scale": 1.07}, 170.95), ({"hic604_pct": 24.0}, 173.00),
                  ({"spindle_phi": 1.35}, 170.51), ({"m_ccw_kgh": 153000.0}, 173.23),
                  ({"hic604_pct": 0.0}, 177.00)):
        assert _run(**kw).t_overflow_c == pytest.approx(t, abs=0.01), kw
    for kw in ({"co2_scale": 1.24}, {"m_ccw_kgh": 91000.0}):
        assert _run(**kw).t_overflow_c == T_PROC_C, kw
    # ... and just inside each threshold the model is still resolving.
    for kw in ({"co2_scale": 1.23}, {"m_ccw_kgh": 92500.0}):
        assert _run(**kw).t_overflow_c < T_PROC_C, kw


def test_a_flooding_sump_makes_the_cooling_water_return_colder():
    """The choke signature, and it is the counter-intuitive one.

    Liquid rising above normal level floods the condensation surface from the bottom, so
    less is condensed and less heat reaches the water. Measured TDY-329125: 15.0 K at normal
    level, 9.75 at 75 %, **4.5 at a full sump**. An operator watching the cooling-water rise
    fall away could read it as the duty easing off; it is the duty dying.
    """
    rises = [(L, _run(choke_level_pct=L).dt_ccw_c) for L in (50.0, 60.0, 75.0, 90.0, 100.0)]
    assert [d for _, d in rises] == sorted((d for _, d in rises), reverse=True)
    assert rises[0][1] == 15.0
    assert rises[2][1] == pytest.approx(9.75, abs=0.01)
    assert rises[-1][1] == pytest.approx(4.5, abs=0.01)
    # ... and it floors rather than stopping: the upper tubes stay wetted.
    assert _run(choke_level_pct=100.0).q_ccw_kw / Q_CCW_DES_KW \
        == pytest.approx(COND_CHOKE_MIN, abs=1e-12)


def test_the_two_derates_are_exactly_inert_at_their_design_positions():
    """At or below normal level, and at the design spindle, the duty is untouched.

    Not nearly untouched — the same float. That is what keeps every pin below them exact.
    """
    assert _run(choke_level_pct=LEVEL_NLL_PCT).q_ccw_kw == DESIGN.q_ccw_kw
    assert _run(choke_level_pct=0.0).q_ccw_kw == DESIGN.q_ccw_kw
    assert _run(spindle_phi=1.0).q_ccw_kw == DESIGN.q_ccw_kw


def test_closing_the_ejector_spindle_raises_the_condensation_duty():
    """A harder jet draws the gas down through the condensation zone more vigorously.

    Measured duty: 4758 kW at a weak jet (phi 0.7), 5330 at design, 5637 at phi 1.3. The
    sign is the same one the reactor's forward-carbamate coupling uses, and it is driven off
    the same (1 - 1/phi) term, so the two cannot disagree about which way HV-322602 pushes.
    """
    duties = [_run(spindle_phi=p).q_ccw_kw for p in (0.7, 1.0, 1.3)]
    assert duties == sorted(duties)
    assert duties[0] == pytest.approx(4758.5, abs=0.5)
    assert duties[2] == pytest.approx(5637.0, abs=0.5)


# ==========================================================================================
# The purge valve and the analyser
# ==========================================================================================

def test_the_purge_valve_moves_the_two_thermowells_in_opposite_directions():
    """One action, two published temperatures, and they must not move together.

    Measured across the full stroke: TT-322011 rises 94.0 -> 121.8 C as HIC-322604 opens
    0 -> 100 %, because more uncondensed vapour goes over the top; TT-322002 falls
    177.0 -> 160.3 C over the same stroke (on V1's 178.8 C pin it started on the 185 C ceiling),
    because relieving the vessel cools the bottom carbamate. Both are exactly at their design
    pins at the design opening, 72 % (handoff B-18, decided 2026-10-10; on V1's 50 % anchor the
    stroke spanned 94.0 -> 134.0 and 177.0 -> 153.0 C).
    """
    tops = [(h, _run(hic604_pct=h).t_offgas_c) for h in (0.0, 25.0, 50.0, 75.0, 100.0)]
    bots = [(h, _run(hic604_pct=h).t_overflow_c) for h in (0.0, 25.0, 50.0, 75.0, 100.0)]
    assert [t for _, t in tops] == sorted(t for _, t in tops)
    assert [t for _, t in bots] == sorted((t for _, t in bots), reverse=True)
    assert tops[0][1] == pytest.approx(94.0, abs=0.01)
    assert tops[-1][1] == pytest.approx(121.78, abs=0.01)
    assert (bots[0][1], bots[-1][1]) == pytest.approx((177.0, 160.33), abs=0.01)
    assert _run(hic604_pct=HIC604_DES_PCT).t_offgas_c == OFFGAS_T_DES_C


def test_the_vent_top_temperature_rides_the_loop_ammonia_slip():
    """A CO2-limited loop cannot absorb its excess ammonia, so the vent top runs hot.

    120 C per unit of N/C, so 0.2 of analyser movement is 24 C on TT-322011. At the design
    reference the deviation is exactly zero and the published value is the 114.0 C pin.
    """
    assert _run(nc_act=OFFGAS_NC_DES).t_offgas_c == OFFGAS_T_DES_C
    assert _run(nc_act=OFFGAS_NC_DES + 0.2).t_offgas_c \
        == pytest.approx(OFFGAS_T_DES_C + 24.0, abs=0.01)
    assert _run(nc_act=OFFGAS_NC_DES - 0.2).t_offgas_c \
        == pytest.approx(OFFGAS_T_DES_C - 24.0, abs=0.01)


def test_the_vent_top_correlation_overshoots_the_plants_own_trend():
    """Handoff B-17, pinned as a measurement rather than left as an impression.

    Driven at the plant's own normal-operation means — HIC-322604 at 78.188 %, AY-322701 at
    3.236, TIC-329005 at 84.459 C, PT-329201 at 139.603 bar a — the correlation predicts
    **144.1 C against a measured TT-322011 of 130.3 C**. It overshoots by 13.8 C, in the
    direction its slip gain drives: on HIC-322604's 72 % anchor (handoff B-18, decided 2026-10-10)
    the vent-opening term is +1.7 C, where V1's 50 % made it +11.3 C and the overshoot 23.3 C
    (153.6 C). The slip gain is calibrated rather than sourced, and no trend in ``References/``
    moves it in isolation.
    """
    r = _run(hic604_pct=78.188, nc_act=3.236, t_ccw_in_c=84.459,
             p_loop_bara=139.603, vent_ratio=139.603 / 140.7)
    assert r.t_offgas_c == pytest.approx(144.1, abs=0.1)
    assert r.t_offgas_c - 130.316 == pytest.approx(13.8, abs=0.1)
    # The bottom thermowell, on the PFD's 165 C pin (B-16), reads 2.1 C over the plant's own
    # 165.7 C mean (on V1's 50 % anchor 162.0, 3.7 C under; on its 178.8 C pin 175.7).
    assert r.t_overflow_c == pytest.approx(167.8, abs=0.1)


def test_both_published_temperatures_are_bounded_by_physics_not_by_range_checks():
    """Neither can fall below the cooling water nor rise above the condensation ceiling.

    The rails are the two things that are physically true regardless of how far off design
    the correlation is driven, which is why they are the right rails: a fitted gain pushed
    hard enough would otherwise publish a vent hotter than the reactor.
    """
    hot = _run(nc_act=OFFGAS_NC_DES + 5.0, hic604_pct=100.0)
    assert hot.t_offgas_c == T_PROC_C
    cold = _run(nc_act=0.0, hic604_pct=0.0, t_ccw_in_c=70.0)
    assert cold.t_offgas_c == 70.0


# ==========================================================================================
# Losing the cooling
# ==========================================================================================

def test_losing_the_cooling_turns_the_purge_into_the_loop_vent():
    """The scenario this unit exists to teach, measured end to end.

    With no condensation capacity the vent goes from 1708 kg/h to **22 355 kg/h — thirteen
    times design** — and it carries 665.7 kmol/h of ammonia, which is the whole of the
    reactor off-gas. At half capacity it is already 12 032 kg/h.

    Nothing has crossed the loop boundary while this happens: 322E003 sits INSIDE the
    synthesis loop, so a boundary mass balance reads unchanged and the event is invisible to
    it. What actually changes is the specific volume of the retained mass, and that is
    pressure.
    """
    full, half, none = (_run(cool_frac=cf) for cf in (1.0, 0.5, 0.0))
    assert full.uncond_kgh == 0.0
    assert _kgh(half.offgas_kmolh) == pytest.approx(12031.5, abs=1.0)
    assert _kgh(none.offgas_kmolh) == pytest.approx(22354.6, abs=1.0)
    assert _kgh(none.offgas_kmolh) / _kgh(full.offgas_kmolh) == pytest.approx(13.1, abs=0.1)
    assert none.offgas_kmolh["NH3"] == pytest.approx(REACTOR_OFFGAS_DES_KMOLH["NH3"], abs=0.1)


def test_the_uncondensed_mass_comes_out_of_the_liquid_and_not_out_of_nowhere():
    """Every kmol added to the vent is taken off the overflow, per species."""
    full, part = _run(), _run(cool_frac=0.35)
    for k in MW_COMP:
        gained = part.offgas_kmolh[k] - full.offgas_kmolh[k]
        lost = full.overflow_kmolh[k] - part.overflow_kmolh[k]
        assert gained == pytest.approx(lost, abs=1e-9), k
    assert part.uncond_kmolh == pytest.approx(
        sum(part.offgas_kmolh[k] - full.offgas_kmolh[k] for k in MW_COMP), abs=1e-9)


def test_the_wash_liquid_itself_never_flashes_back():
    """Only what was CONDENSED here can be un-condensed.

    The weak carbamate arrived as liquid and leaves as liquid however hot the shell gets, so
    even at total loss of cooling the overflow still carries the full wash. Measured: the
    overflow at zero capacity is 35 207 kg/h, and the wash alone is 36 915 — the difference
    is the small urea and water the reactor contributed, not a shortfall in the wash.
    """
    none = _run(cool_frac=0.0)
    for k in MW_COMP:
        assert none.overflow_kmolh[k] >= -1e-12
    assert none.overflow_kmolh["NH3"] >= WASH_KMOLH_DES["NH3"] - 1e-9
    assert none.overflow_kmolh["CO2"] >= WASH_KMOLH_DES["CO2"] - 1e-9


def test_the_capacity_gate_has_three_independent_failures():
    """Throttle the water, lose the temper, or stop the pumps — each alone is enough.

    All three read exactly 1.0 at design, so the product does too and the gate is inert
    there. Measured: half flow gives 0.912 on the shell's effectiveness (decided 2026-10-17,
    B-99 (b1): the shell is UA-limited, NTU 0.19) where V1's linear law gives 0.5, stopped pumps
    give 0.0, and a supply temperature at the condensing temperature gives 0.0 because the
    driving force has gone.
    """
    assert condensation_capacity(CCW_KGH_DES, 1.0, CCW_T_IN_DES_C,
                                 OVERFLOW_P_DES_BARA, 1.0) == 1.0
    assert condensation_capacity(CCW_KGH_DES / 2, 1.0, CCW_T_IN_DES_C,
                                 OVERFLOW_P_DES_BARA, 1.0) == pytest.approx(0.91176, abs=1e-5)
    assert condensation_capacity(CCW_KGH_DES / 2, 1.0, CCW_T_IN_DES_C,
                                 OVERFLOW_P_DES_BARA, 1.0, effectiveness=False) == 0.5
    assert condensation_capacity(CCW_KGH_DES, 0.0, CCW_T_IN_DES_C,
                                 OVERFLOW_P_DES_BARA, 1.0) == 0.0
    assert condensation_capacity(CCW_KGH_DES, 1.0, OVERFLOW_T_DES_C,
                                 OVERFLOW_P_DES_BARA, 1.0) == 0.0
    # More throughput is more demand on the same shell, so capacity falls with load.
    assert condensation_capacity(CCW_KGH_DES, 1.0, CCW_T_IN_DES_C,
                                 OVERFLOW_P_DES_BARA, 1.25) == 0.8


def test_the_gate_dead_band_keeps_the_design_state_exactly_inert():
    """A controller residual of 1e-9 is not a condensation deficit.

    TIC-329005 settles on 80.00000005 C, which leaves the capacity a whisker under 1. Taken
    literally that would make the uncondensed mass non-zero at design and carry the level
    swell and the loop-pressure phase term with it. Inside the dead band the gate is skipped
    outright, so the uncondensed mass is a literal 0.0.
    """
    assert _run(cool_frac=1.0 - 1.0e-9).uncond_kgh == 0.0
    assert _run(cool_frac=1.0 - 1.0e-9).cool_frac == 1.0
    assert _run(cool_frac=1.0 - 1.0e-4).uncond_kgh > 0.0


# ==========================================================================================
# The sump
# ==========================================================================================

def test_the_sump_level_is_linear_in_holdup_and_pinned_at_normal():
    """3837 kg reads 50 %, 7675 kg reads 100 %, and both rails hold."""
    assert sump_level_pct(HOLDUP_NLL_KG) == LEVEL_NLL_PCT
    assert sump_level_pct(HOLDUP_MAX_KG) == 100.0
    assert sump_level_pct(0.0) == 0.0
    assert sump_level_pct(-1.0) == 0.0
    assert sump_level_pct(1e9) == 100.0
    assert HOLDUP_NLL_KG == pytest.approx(3837.4, abs=0.1)


def test_the_transmitter_reads_high_while_the_vessel_drains():
    """The operator trap, measured.

    A sump actually holding 40 % is displayed at **58 %** once condensation has stopped, and
    the reading hunts across roughly 56 to 60 % as the two froth periods beat against each
    other. The trainee is meant to reach for the real evidence — the cooling-water rise,
    which is collapsing — rather than the level they can see.
    """
    true_level = 40.0
    assert lt_329501_indication(true_level, 0.0, 0.0) == pytest.approx(58.0, abs=0.01)
    readings = [lt_329501_indication(true_level, 0.0, t) for t in range(0, 60)]
    assert min(readings) == pytest.approx(56.0, abs=0.2)
    assert max(readings) == pytest.approx(60.0, abs=0.2)
    assert all(r > true_level for r in readings)


def test_the_transmitter_is_the_level_whenever_the_shell_is_condensing():
    """No overlay at full capacity, at any point on the clock, bit-exact."""
    for t in (0.0, 7.3, 17.0, 123.4, 10000.0):
        assert lt_329501_indication(37.5, 1.0, t) == 37.5


def test_the_published_swell_and_hunt_make_up_the_indication():
    """V1 publishes the swell and the hunt beside the reading: they are its two terms."""
    for cf, t in ((0.0, 0.0), (0.4, 11.3), (1.0, 5.0)):
        assert lt_329501_indication(40.0, cf, t) == 40.0 + lt_329501_swell(cf) + lt_329501_noise(
            cf, t)
    assert lt_329501_swell(0.0) == 18.0 and lt_329501_noise(1.0, 3.0) == 0.0


def test_the_swell_saturates_at_the_top_of_the_span():
    """A cell cannot read above 100 %, however hard the column froths."""
    assert lt_329501_indication(95.0, 0.0, 0.0) == 100.0
    assert lt_329501_indication(1.0, 0.0, 30.0) >= 0.0


# ==========================================================================================
# Load, conservation and degenerate inputs
# ==========================================================================================

def test_turndown_moves_the_duty_but_not_the_vent():
    """The two respond to different things, and that is correct.

    The duty is throughput-scaled, so it falls with load: 3198 kW at 60 %, 5330 at design.
    The vent does not move at all, because the inert rate in the reactor off-gas handed to
    this unit has not moved — the caller is turning the CO2 down, not the inerts. Measured
    identical to the bit at 0.6, 0.7 and 1.0.
    """
    runs = [(s, _run(co2_scale=s)) for s in (0.6, 0.7, 1.0, 1.1)]
    duties = [r.q_ccw_kw for _, r in runs]
    assert duties == sorted(duties)
    assert duties[0] == pytest.approx(3197.7, abs=0.5)
    vents = {_kgh(r.offgas_kmolh) for _, r in runs}
    assert len(vents) == 1


def test_flood_carryover_passes_through_and_conserves_every_atom():
    """Entrained reactor melt joins the feed and leaves with the overflow: net zero.

    It also lifts the bottom temperature, as an enthalpy blend over the post-carryover
    overflow — measured 179.4 C against 178.8 with the same cooling state. Below the flood
    lip there is no carryover and every term is identically unchanged.
    """
    carry = {"Urea": 40.0, "Biuret": 0.1, "NH3": 120.0, "CO2": 27.0, "H2O": 66.0,
             "N2": 0.0, "O2": 0.0, "CH4": 0.0, "H2": 0.0}
    base, flood = _run(), _run(liq_carry_kmolh=carry, t_carry_c=183.0)
    for k in MW_COMP:
        assert flood.overflow_kmolh[k] - base.overflow_kmolh[k] \
            == pytest.approx(carry.get(k, 0.0), abs=1e-9), k
        assert flood.offgas_kmolh[k] == base.offgas_kmolh[k], k
    assert flood.t_overflow_c > base.t_overflow_c
    assert _run(liq_carry_kmolh=None).t_overflow_c == base.t_overflow_c
    assert _run(liq_carry_kmolh={}).t_overflow_c == base.t_overflow_c


def test_nitrogen_and_carbon_are_conserved_across_the_vessel():
    """Nothing reacts away here: this is absorption, not synthesis.

    The atom counts in the two products equal the atom counts in the feed, which is the check
    that the vent closure and the cooling-limited flash-back are both pure re-partitions.
    """
    for kw in ({}, {"cool_frac": 0.4}, {"wash_ratio": 1.15}, {"co2_scale": 0.8}):
        r = _run(**kw)
        for atoms in (N_ATOMS, C_ATOMS):
            fed = sum(r.feed_kmolh.get(k, 0.0) * a for k, a in atoms.items())
            out = sum((r.offgas_kmolh.get(k, 0.0) + r.overflow_kmolh.get(k, 0.0)) * a
                      for k, a in atoms.items())
            assert out == pytest.approx(fed, abs=1e-8), kw


def test_an_ammonia_starved_feed_vents_only_what_it_has():
    """The feed cap, which stops the saturation inventing ammonia.

    Handed a feed with almost no ammonia in it, the closure cannot vent the saturation it
    would like to; each condensable is capped at what arrived.
    """
    starved = {"N2": 44.5, "O2": 7.4, "CH4": 3.9, "H2": 2.0,
               "NH3": 0.4, "CO2": 0.2, "H2O": 900.0, "Urea": 0.0, "Biuret": 0.0}
    v = vent_kmolh(starved)
    assert v["NH3"] == 0.4
    assert v["CO2"] == 0.2
    assert v["H2O"] < starved["H2O"]


def test_an_inert_free_feed_vents_nothing_at_all():
    """No non-condensables means no carrier, which means no vent.

    Not a guard — the arithmetic. The inert total multiplies the saturation, so with nothing
    to carry the condensables they all stay in the liquid, which is what a scrubber with no
    purge load does.
    """
    v = vent_kmolh({"NH3": 600.0, "CO2": 200.0, "H2O": 100.0,
                    "N2": 0.0, "O2": 0.0, "CH4": 0.0, "H2": 0.0,
                    "Urea": 0.0, "Biuret": 0.0})
    assert sum(v.values()) == 0.0


def test_an_empty_feed_produces_nothing():
    """Zero in, zero out — the null-feed rule, per species and in both products."""
    r = scrubber_322e003({k: 0.0 for k in MW_COMP}, 0.0, CCW_T_IN_DES_C, CCW_KGH_DES)
    for k in MW_COMP:
        assert r.offgas_kmolh[k] == 0.0
        assert r.overflow_kmolh[k] == 0.0
    assert r.co2_abs == 0.0
    assert r.q_carb_kw == 0.0


def test_the_analyser_reference_is_the_reactor_overflow_and_reads_three():
    """AT-322701's zero, and why it belongs to the reactor rather than to this vessel.

    The analyser sits on the reactor product line, so the reference is the reactor overflow's
    own N/C — measured 2.99975, four decades inside the analyser span. Writing the vent-top
    correlation as a deviation from it is what makes the 114.0 C pin exact.
    """
    assert OFFGAS_NC_DES == pytest.approx(3.0, abs=0.001)
    assert OFFGAS_NC_DES == atom_ratio(
        __import__("ureasim.data.unit_322r001", fromlist=["OVERFLOW_DES_KMOLH"]
                   ).OVERFLOW_DES_KMOLH, N_ATOMS, C_ATOMS, NC_SPAN_MAX)
    # And the span, which exists because the denominator can reach zero on a CO2 trip.
    assert atom_ratio({"NH3": 100.0, "CO2": 1e-12}, N_ATOMS, C_ATOMS, NC_SPAN_MAX) \
        == NC_SPAN_MAX
    assert atom_ratio({"NH3": 100.0}, N_ATOMS, C_ATOMS, NC_SPAN_MAX) == 0.0


def test_the_absorption_duty_counts_what_the_gas_lost():
    """196.25 kmol/h of CO2 crosses into the liquid at design, worth 8722 kW.

    Measured off the GAS, not off the liquid: the wash brings its own carbon in and that was
    never absorbed here. The duty is a diagnostic — the shell-side balance is what actually
    sets the temperatures — and it is about 64 % larger than the cooling water removes, which
    is the model saying that the two are separately anchored rather than solved together.
    """
    assert DESIGN.co2_abs == pytest.approx(196.25, abs=0.01)
    assert DESIGN.q_carb_kw == pytest.approx(8722.3, abs=0.5)
    assert DESIGN.q_carb_kw / DESIGN.q_ccw_kw == pytest.approx(1.64, abs=0.01)
    assert math.isfinite(DESIGN.q_carb_kw)


# ==========================================================================================
# Handoff B-91, decided 2026-10-14: its own liquor's bubble point, and a full sump
# ==========================================================================================

def test_the_sump_liquor_boils_at_the_loop_pressure_at_design_and_lower_when_cold():
    """322E003's liquor on the melt's law anchored on PFD 206: its design overflow at 165 C stands
    at the loop's 140.7 bar a, so the saturation is exactly 1 at design; 74.61 bar a at 125 C and
    30.78 at 80 C; 10 % more ammonia lifts it to 147.16, 10 % more water drops it to 136.13."""
    ov = DESIGN.overflow_kmolh
    assert liquor_bubble_p_bara(ov, DESIGN.t_overflow_c) == pytest.approx(140.7, rel=1e-12)
    assert liquor_bubble_p_bara(ov, 125.0) == pytest.approx(74.613, abs=1e-3)
    assert liquor_bubble_p_bara(ov, 80.0) == pytest.approx(30.782, abs=1e-3)
    rich, wet = dict(ov), dict(ov)
    rich["NH3"] *= 1.1
    wet["H2O"] *= 1.1
    assert liquor_bubble_p_bara(rich, 165.0) == pytest.approx(147.159, abs=1e-3)
    assert liquor_bubble_p_bara(wet, 165.0) == pytest.approx(136.132, abs=1e-3)


def test_a_full_sump_condenses_no_more_than_it_can_take():
    """The sump's room caps the condensate, the wash running in regardless: room for half the
    design condensate passes 47 238.2 kg/h of overflow (the 36 915 kg/h wash and half the rest)
    and hands 10 323.2 kg/h back to the vapour; no room passes the wash alone. Mass closes on
    every call, and an unbounded room is the design call to the bit."""
    wash = _kgh(DESIGN.carb_kmolh)
    cond = _kgh(DESIGN.overflow_kmolh) - wash
    half = _run(sump_room_kgh=wash + 0.5 * cond)
    assert _kgh(half.overflow_kmolh) == pytest.approx(47238.16, abs=0.01)
    assert (half.sump_frac, half.cool_frac) == (pytest.approx(0.5), pytest.approx(0.5))
    assert half.uncond_kgh == pytest.approx(10323.16, abs=0.01)
    assert half.closure_resid == 0.0
    none = _run(sump_room_kgh=0.0)
    assert _kgh(none.overflow_kmolh) == pytest.approx(wash, rel=1e-12)
    assert none.sump_frac == 0.0
    assert _run(sump_room_kgh=1.0e9) == DESIGN


def test_the_wash_arrives_as_323d001_delivers_it():
    """Handoff B-105, decided 2026-10-22: the wash on 308's live composition and temperature, each
    as its departure from PFD 308. Zero departures are V1's design wash to the bit. 323D001 diluted
    by FV-323401 wide open (38.51 % water, 15 % more wash): the sump liquor's H/C rises from 1.355
    to 1.812 and its N/C from 2.508 to 2.559, and the liquor boils at 122.84 bar a where the design
    carbamate boils at 137.67, so it condenses more before its saturation binds. A wash 10 K cold
    takes TT-322002 down 6.41 K."""
    from ureasim.data import unit_323e003 as e3
    base = _run(wash_ratio=1.0)
    assert _run(wash_ratio=1.0, wash_dw={k: 0.0 for k in e3.W_308}, wash_dt_c=0.0) == base
    diluted = {"NH3": 0.27327, "CO2": 0.33996, "H2O": 0.38510, "Urea": 0.00167}
    dw = {k: diluted[k] - e3.W_308[k] for k in diluted}
    v1, port = _run(wash_ratio=1.15), _run(wash_ratio=1.15, wash_dw=dw)
    assert _kgh(port.carb_kmolh) == pytest.approx(_kgh(v1.carb_kmolh), rel=1e-12)
    for r, hc, nc, p_bub in ((v1, 1.3547, 2.5081, 137.669), (port, 1.8120, 2.5594, 122.839)):
        ov = r.overflow_kmolh
        assert ov["H2O"] / ov["CO2"] == pytest.approx(hc, abs=1e-4)
        assert ov["NH3"] / ov["CO2"] == pytest.approx(nc, abs=1e-4)
        assert liquor_bubble_p_bara(ov, r.t_overflow_c) == pytest.approx(p_bub, abs=1e-3)
    assert _run(wash_ratio=1.0, wash_dt_c=-10.0).t_overflow_c - base.t_overflow_c == \
        pytest.approx(-6.413, abs=1e-3)
