"""Behaviour of 324E003 / 324F003, stage 2 of unit 324 — `ureasim.units.evaporation.second_evaporator`.

Equivalence with V1 is proven tick by tick in
`tests/equivalence/test_second_evaporator_equivalence.py` and each departure both ways in
`test_second_evaporator_decided_equivalence.py`. This file pins what the stage DOES: the design
seed held on 324F004's design-anchored map (handoff B-61), PV-324203's vendor trim, a lost header,
a lost feed boiling the held melt (B-62), on V1's selector LV-324501B taking the melt when the 335
header backs up and on AC4's header (decision 224) LV-324501B returning melt beside LV-324501A,
stage 1 and stage 2 run together — and a feed-pump trip, stage 2 taking the leg's strength (B-63).
"""

from __future__ import annotations

import pytest

from ureasim.control.granulation_trips import Unit35TripInputs, Unit35Trips
from ureasim.data import unit_324 as d
from ureasim.data import unit_335 as u335
from ureasim.data.design_point import R324_FEED_DES
from ureasim.data.unit_323 import MEVAP_DES_KGH, W_S317
from ureasim.data.unit_329 import P_LP_BARA, P_MP_BARA
from ureasim.data.unit_335 import LIC_324501_X_DES_PCT, LV_324501A_HEADER_OP_DES_PCT
from ureasim.units.evaporation import ejector_map as em
from ureasim.units.evaporation import first_evaporator as fe
from ureasim.units.evaporation import second_evaporator as se
from ureasim.units.evaporation.vacuum_condenser import design_specs

TV5 = design_specs()["324E005"].t_v_solved_des
TV2 = design_specs()["324E002"].t_v_solved_des

#: 324F004's motive at its nozzle at design and 324E006, what it discharges into [bar a].
P_MOTIVE = em.nozzle_pressure_bara("324F004", d.EJECTOR_DESIGN_LOADS["324F004"].motive_kgh)
P_E006 = d.E006_P_DES_BARA


def _run(n, feed=d.P1_DES_KGH, p_mp=P_MP_BARA, p335=d.PIC_335201_DES_BARG, ac4=True):
    unit = se.SecondEvaporator(ac4_header=ac4)
    loops = se.SecondEvaporatorLoops(level=se.lic_324501(ac4=ac4))
    r = None
    for _ in range(n):
        r = unit.step(loops, feed, d.E001_T_DES_C, d.W_S401, p_mp, P_MOTIVE, P_E006, TV5, p335,
                      0.1)
    return unit, loops, r


def test_the_design_seed_holds():
    """An hour at design on 324F004's design-anchored map: the melt at 140 C, PT-324203 at
    0.131 bar a to 1e-14 (324E005's condenser falsi reaches the last bits), PV-324203 at its 92.03 %, PFD 709's 2738 kg/h
    boiled, PFD 402 at 97.71 %, 3741 kg/h of 9-bar steam; the fixed point in one iteration. On
    AC4's header (decision 224) LIC-324501 holds its 35 % output, E1 on the 3.5 bar g header, and
    PIC-335201 holds LV-324501A at the header's 79.09 % (decision 237; the trim's 75.35 % on its
    sizing case, decision 150), LV-324501B shut, each to the bit."""
    unit, loops, r = _run(36000)
    assert r.t_c == 140.0
    assert r.p_bara == pytest.approx(0.131, abs=1e-14)
    assert loops.vacuum.op == pytest.approx(d.PV_324203_OP_DES_PCT, abs=1e-9)
    assert loops.level.op == LIC_324501_X_DES_PCT and loops.header.op == LV_324501A_HEADER_OP_DES_PCT
    assert (r.header.p_barg, r.lv_a_pct, r.lv_b_pct) == (3.5, LV_324501A_HEADER_OP_DES_PCT, 0.0)
    assert unit.header.lv_a_position_pct == LV_324501A_HEADER_OP_DES_PCT
    assert unit.m_kg == pytest.approx(d.F003_M_DES_KG, rel=1e-12)
    assert r.m_vap_kgh == pytest.approx(d.V2_DES_KGH, rel=1e-12) and r.m_boil_kgh == 0.0
    assert r.w_melt == pytest.approx(0.9771, abs=1e-12)
    assert r.steam_kgh == pytest.approx(3741.02, abs=0.01)
    assert r.converged and r.iterations == 1


def test_pv_324203_on_its_vendor_trim():
    """PFD 783's 21 kg/h at the 92.03 % Flowserve's sizing gives; wide open, the 26.7 kg/h its
    Kvs 1.6 passes on the sizing case."""
    assert se.false_air_kgh(d.PV_324203_OP_DES_PCT) == pytest.approx(21.0, rel=1e-12)
    assert se.false_air_kgh(100.0) == pytest.approx(26.667, abs=1e-3)


def test_a_lost_header_dilutes_the_melt():
    """The 9-bar header to 4.0 bar a: on PV-329212's vendor trim (decided 2026-10-14) the chest
    falls to 3.79 bar a, the melt to 129.9 C and 97.16 % urea, and the stage boils 2309 kg/h where
    it boiled 2738 (3.35 bar a, 127.3 C, 96.98 % and 2168 on V1's linear valve); the held melt, cooling, does not
    boil on its own."""
    _, _, r = _run(18000, p_mp=4.0)
    assert r.chest_p_bara == pytest.approx(3.7948, abs=1e-4)
    assert r.t_c == pytest.approx(129.916, abs=1e-3)
    assert r.w_melt == pytest.approx(0.97161, abs=1e-5)
    assert r.m_vap_kgh == pytest.approx(2308.9, abs=0.1)
    assert r.m_boil_kgh == 0.0


def test_a_lost_feed_boils_the_held_melt_b62():
    """Handoff B-62, decided 2026-10-01. Stage 1's leg stops. The chest's duty, no longer spent on
    the feed, boils the held melt — 607 kg/h after a minute, the melt at 151.3 C and 98.13 %,
    holding at its own boiling point as it concentrates. LIC-324501 shuts the drain as the level
    falls and holds 1285 kg (LV-324501A's equal percentage, decision 150); the chest fills toward
    the 9-bar header (PV-329212 on its vendor trim), and at 170.2 C the melt's equilibrium at the
    vacuum is 98.57 % and it boils no more. (616 kg/h, 151.4 C and 170.6 C with PV-329212 on the
    chord, before decision 170, 2026-11-06 put Valmet's S-Disc table between its printed points.)
    On V1's selector, the harness's side of decision 224; AC4's header is pinned below."""
    unit = se.SecondEvaporator(ac4_header=False)
    loops = se.SecondEvaporatorLoops(level=se.lic_324501(ac4=False))
    for k in range(6000):
        feed = 0.0 if k >= 5 else d.P1_DES_KGH
        r = unit.step(loops, feed, d.E001_T_DES_C, d.W_S401, P_MP_BARA, P_MOTIVE, P_E006, TV5,
                      d.PIC_335201_DES_BARG, 0.1)
        if k == 600:
            assert (r.t_c, r.m_boil_kgh, unit.w["Urea"]) == (
                pytest.approx(151.2600, abs=1e-4), pytest.approx(607.46, abs=0.01),
                pytest.approx(0.98129, abs=1e-5))
        assert r.converged
    assert r.m_402_kgh == 0.0 and unit.m_kg == pytest.approx(1284.98, abs=0.01)
    assert r.m_vap_kgh == 0.0 == r.m_boil_kgh
    assert r.t_c == pytest.approx(170.198, abs=1e-3)
    assert unit.w["Urea"] == pytest.approx(0.98565, abs=1e-5)


def test_a_lost_feed_on_ac4s_header_drains_stage_2_to_its_heel_b62():
    """B-62 on AC4's header (decision 224). The held melt boils as on V1's selector, 593 kg/h after
    a minute at 151.65 C and 98.14 %, but the drain does not stop: LIC-324501 winds X to 0 and E1 to
    its 2.8 bar g floor, where ten header valves still pass 89 % of PFD 402, and PIC-335201 opens
    LV-324501A to hold it. The leg uncovers at 176.5 s and draws air, the heel limits the drain
    at 187.3 s and the melt holds its 1 kg heel at 175.36 C and 98.63 %; over the 32 ticks the
    holdup empties the sweeps do not settle and the energy balance solves the fixed point (B-108).
    Run with 335P001A / B's low-level stop on LY-324501 off (decision 217), whose own arm follows.
    (151.6476 C, 593.40 kg/h, 176.7 s and 187.4 s before decisions 236 and 237.)"""
    unit, loops = se.SecondEvaporator(), se.SecondEvaporatorLoops()
    unit.l2_stop = False
    stalled, air, zero = [], None, None
    for k in range(6000):
        feed = 0.0 if k >= 5 else d.P1_DES_KGH
        r = unit.step(loops, feed, d.E001_T_DES_C, d.W_S401, P_MP_BARA, P_MOTIVE, P_E006, TV5,
                      d.PIC_335201_DES_BARG, 0.1)
        if k == 600:
            assert (r.t_c, r.m_boil_kgh, unit.w["Urea"]) == (
                pytest.approx(151.6481, abs=1e-4), pytest.approx(593.39, abs=0.01),
                pytest.approx(0.98141, abs=1e-5))
        stalled += [] if r.converged else [k] if r.bisected else [-k]
        air = k if air is None and r.seal_air_kgh > 0.0 else air
        zero = k if zero is None and k > 5 and r.m_402_kgh == 0.0 else zero
    assert (air, zero) == (1765, 1873) and stalled == list(range(1868, 1900))
    assert r.m_402_kgh == 0.0 and unit.m_kg == 1.0 and r.header.capped
    assert (r.t_c, unit.w["Urea"]) == (pytest.approx(175.358, abs=1e-3),
                                       pytest.approx(0.98628, abs=1e-5))
    assert loops.level.op == 0.0 and r.seal_air_kgh > 0.0


def test_the_335_header_backing_up_sends_the_melt_to_323d002():
    """V1's selector (the harness's side of decision 224): PIC-335201 above its 3.8 bar g relief
    setting, LIC-324501's stroke goes to LV-324501B and the whole drain, the raw melt at 140 C,
    returns to 323D002; nothing goes forward. On its sheet (decision 150) LV-324501B passes 95.7 t/h
    at the stroke, its 5.1 bar to 323D002 against A's 3.2; V1's span law passed the design drain on
    either valve."""
    _, _, r = _run(10, p335=4.0, ac4=False)
    assert r.recycle_selected and (r.lv_a_pct, r.lv_b_pct) == (0.0, pytest.approx(75.286,
                                                                                  abs=1e-3))
    assert (r.route.route, r.route.forward_kgh) == ("B", 0.0)
    assert r.route.recycle_kgh == r.m_402_kgh == pytest.approx(95657.2, abs=0.1)
    assert r.route.recycle_t_c == 140.0
    assert sum(r.route.recycle_w.values()) == pytest.approx(1.0, abs=1e-12)


def test_ac4s_header_returns_the_excess_beside_the_forward_melt():
    """Decision 224: with one header valve fewer than the load asks for, the level rises, LIC-324501
    lifts E1 to its 3.8 bar g ceiling and opens LV-324501B, so LV-324501A and LV-324501B both pass
    melt and the drain still matches the feed; nothing is drained to 335D004 with HV-335602 shut.
    LV-324501B relays at its seat on this excess (As-Built Part CXXI, handoff B-145), so the last
    five minutes are read, not the last tick: E1 rides its ceiling on 77 % of them, LV-324501B open
    on each of those, and the mean header and drain stand on 3.8 bar g and the feed."""
    unit = se.SecondEvaporator()
    loops = se.SecondEvaporatorLoops()
    tail = []
    for k in range(15000):
        r = unit.step(loops, d.P1_DES_KGH, d.E001_T_DES_C, d.W_S401, P_MP_BARA, P_MOTIVE, P_E006,
                      TV5, 0.0, 0.1, headers_online=9)
        if k >= 12000:
            tail.append(r)
        assert r.route.drain_kgh == 0.0
    ceiling = [r for r in tail if r.header.e1_barg == 3.8]
    assert len(ceiling) > 0.7 * len(tail) and max(r.header.e1_barg for r in tail) == 3.8
    assert all(r.lv_b_pct > 0.0 and r.route.route == "AB" and r.route.forward_kgh > 0.0
               and r.route.recycle_kgh > 0.0 for r in ceiling)
    assert sum(r.header.p_barg for r in tail) / len(tail) == pytest.approx(3.8, abs=0.01)
    assert sum(r.m_402_kgh for r in tail) / len(tail) == pytest.approx(d.P2_DES_KGH, rel=5e-3)


def test_the_seal_air_leg_uncovers_on_pic_335201s_stroke():
    """On AC4's header the lost seal's air rides LV-324501A's stroke of the tick before, behind
    its positioner on PIC-335201's output (decisions 224 and 236), not LIC-324501's X: with the level
    at 2 % and LIC-324501 forced to 0 % the leg still draws air through LV-324501A at the header's
    design stroke, where on V1's selector LIC-324501's 0 % stroke would shut it."""
    from ureasim.units.evaporation.leg_seal import seal_air_kgh
    unit = se.SecondEvaporator()
    loops = se.SecondEvaporatorLoops()
    loops.level.mode, loops.level.op = "MAN", 0.0
    unit.m_kg = 0.02 * d.F003_M_FULL_KG
    level, stroke, p = (unit.m_kg / d.F003_M_FULL_KG * 100.0, unit.header.lv_a_position_pct,
                        unit.p_bara)
    r = unit.step(loops, d.P1_DES_KGH, d.E001_T_DES_C, d.W_S401, P_MP_BARA, P_MOTIVE, P_E006, TV5,
                  0.0, 0.1)
    assert stroke == LV_324501A_HEADER_OP_DES_PCT
    assert r.seal_air_kgh == seal_air_kgh(level, stroke, p) > 0.0 == seal_air_kgh(level, 0.0, p)


def _trips_beside(trips, unit):
    # AC4 PC35's trips on stage 2's state after its step, read a tick late as the engine reads them.
    if trips is not None:
        trips.step(Unit35TripInputs(not unit.p001_stopped, trips.actions.p002_permit,
                                    unit.header.lv_a_position_pct <= u335.LVSL_324501A_PCT), 0.1)


def _pc35():
    return Unit35Trips(u335.TRIP_35_4_P002_TD_S, u335.LIC_324501_CLAMPREF_PCT,
                       u335.PIC_335201_CLAMPREF_PCT)


def _chain(n, cut_at=None, ac4=True, stop=True, trips=None):
    u1, l1 = fe.FirstEvaporator(), fe.FirstEvaporatorLoops()
    u2 = se.SecondEvaporator(ac4_header=ac4)
    if not stop:
        u2.l2_stop = False
    l2 = se.SecondEvaporatorLoops(level=se.lic_324501(ac4=ac4))
    out = []
    for k in range(n):
        m = 0.0 if cut_at is not None and k >= cut_at else R324_FEED_DES
        r1 = u1.step(l1, m, 99.0, W_S317, P_LP_BARA, 4.1, 1.0, MEVAP_DES_KGH, None, TV2, 0.1)
        r2 = u2.step(l2, r1.m_401_kgh, r1.t_c, r1.w, P_MP_BARA, P_MOTIVE, P_E006, TV5,
                     d.PIC_335201_DES_BARG, 0.1, trips=trips.actions if trips else se.HEALTHY_35)
        _trips_beside(trips, u2)
        out.append((r1, r2))
    return out


def test_the_two_stages_together_hold_the_design():
    """Stage 1's leg into stage 2 for five minutes: both stages on their design points within
    1e-5 K and 1e-7 bar (the chests' vendor trims answer the seed's own 3e-7 bar first-tick move,
    decided 2026-10-14), PFD 402 at 97.71 % and 140 C (PFD 317's 80.0016 % urea against V1's 80 %
    is all that moves)."""
    r1, r2 = _chain(3000)[-1]
    assert (r1.t_c, r1.p_bara) == (pytest.approx(130.0, abs=1e-5), pytest.approx(0.33, abs=1e-7))
    assert (r2.t_c, r2.p_bara) == (pytest.approx(140.0, abs=1e-5), pytest.approx(0.131, abs=1e-7))
    assert r2.w_melt == pytest.approx(0.9771, abs=1e-8)


def test_a_feed_pump_trip_sends_stage_2_the_melt_its_leg_drains_b63():
    """Handoff B-63, decided 2026-10-02. 323P003 stops: stage 1 makes no melt, while its leg
    drains the melt it holds — 71.5 t/h at 96.05 % urea after 30 s, B-62 boiling it. Stage 2 takes
    the feed at the leg's strength and finishes it: 1273 (1265 before decision 178) kg/h of the feed's water and 655 (659 before decision 178) of its
    own holdup's boil off (662 on the chord, before decision 170), the melt at 141.9 C and 97.79 %
    (the chests on their vendor trims). The leg runs dry onto stage 1's heel
    at 350 s; stage 2 boils its last, LIC-324501 shuts LV-324501A at 638 s with the level at 21.6 %
    (its equal percentage passing little at low stroke, decision 150), and the melt holds 1496 kg
    at 98.40 % urea and 161.41 (161.40 before decision 178) C (161.75 on the chord), the chest isolated at its saturation. The melt never
    falls below its 140 C design, where V1 — the strength stage 1 made, 0 — boiled the whole leg
    as water to -83 C in a minute. On V1's selector, the harness's side of decision 224; AC4's
    header is pinned below."""
    run = _chain(12005, cut_at=5, ac4=False)
    r1, r2 = run[300]
    assert r1.w_melt == 0.0 and r1.w["Urea"] == pytest.approx(0.96043, abs=1e-5)
    assert r1.m_401_kgh == pytest.approx(71538.71, abs=0.01)
    assert r2.feed_urea_kgh == pytest.approx(68714.39, abs=0.01)
    assert (r2.m_vap_kgh, r2.m_boil_kgh) == (pytest.approx(1272.97, abs=0.01),
                                             pytest.approx(654.54, abs=0.01))
    assert (r2.t_c, r2.w_melt) == (pytest.approx(141.8821, abs=1e-4),
                                   pytest.approx(0.97793, abs=1e-5))
    assert all(r.converged and r.t_c >= 140.0 for _, r in run)
    assert next(k for k in range(400, 12005) if run[k][1].m_402_kgh == 0.0) == 6376
    r1, r2 = run[12004]
    assert r1.m_401_kgh == 0.0 and r2.m_402_kgh == 0.0 and r2.m_vap_kgh == 0.0 == r2.m_boil_kgh
    assert (r2.m_kg, r2.w["Urea"], r2.t_c) == (pytest.approx(1496.39, abs=0.01),
                                               pytest.approx(0.98396, abs=1e-5),
                                               pytest.approx(161.4070, abs=1e-4))


def test_a_feed_pump_trip_on_ac4s_header_drains_stage_2_to_its_heel_b63():
    """B-63 on AC4's header (decision 224). Stage 2 finishes the leg's melt as on V1's selector,
    1273 kg/h of the feed's water and 655 of its own boil off at 30 s, the melt at 141.88 C, and
    never falls below 140 C; but PIC-335201 holds the header on E1's 2.8 bar g floor as the level
    falls, so the drain runs on after the leg runs dry: the seal uncovers at 361.3 s, the heel
    limits the drain at 372.2 s and the melt holds its 1 kg heel at 98.41 % and 162.18 C, the leg
    drawing 1.9 t/h of air. Run with 335P001A / B's low-level stop on LY-324501 off (decision 217),
    whose own arm follows. (361.6 s, 372.4 s and 162.1832 C before decisions 236 and 237.)"""
    run = _chain(12005, cut_at=5, stop=False)
    _r1, r2 = run[300]
    assert (r2.m_vap_kgh, r2.m_boil_kgh, r2.t_c) == (pytest.approx(1272.98, abs=0.01),
                                                     pytest.approx(654.51, abs=0.01),
                                                     pytest.approx(141.8825, abs=1e-4))
    assert all(r.converged and r.t_c >= 140.0 for _, r in run)
    assert next(k for k in range(12005) if run[k][1].seal_air_kgh > 0.0) == 3613
    assert next(k for k in range(400, 12005) if run[k][1].m_402_kgh == 0.0) == 3722
    r1, r2 = run[12004]
    assert r1.m_401_kgh == 0.0 and r2.m_402_kgh == 0.0 and r2.m_kg == 1.0 and r2.header.capped
    assert (r2.w["Urea"], r2.t_c) == (pytest.approx(0.98413, abs=1e-5),
                                      pytest.approx(162.1849, abs=1e-4))
    assert r2.seal_air_kgh == pytest.approx(1882.0, abs=1.0)


def test_a_lost_feed_on_ac4s_header_stops_335p001_on_ly_324501s_l2_b62():
    """Decision 217 on B-62: AC4 stops 335P001A / B on LY-324501 below L2 (the stand-in 5 %, 2 %
    hysteresis). The pumps stop at 169.3 s on 4.99 %, the header drawing 69.5 t/h the tick before;
    with no feed the level cannot recover and the pair stays stopped, so the seal never uncovers and
    stage 2 holds 346.0 kg of melt at 175.33 C and 98.64 %, where with the stop off it drains to its
    1 kg heel and draws air. Trips 35.1, 35.3 and 35.4 act beside it in the engine (decision 228)."""
    unit, loops = se.SecondEvaporator(), se.SecondEvaporatorLoops()
    out = []
    for k in range(3000):
        feed = 0.0 if k >= 5 else d.P1_DES_KGH
        r = unit.step(loops, feed, d.E001_T_DES_C, d.W_S401, P_MP_BARA, P_MOTIVE, P_E006, TV5,
                      d.PIC_335201_DES_BARG, 0.1)
        out.append((r, unit.p001_stopped))
    first = next(k for k, (_, s) in enumerate(out) if s)
    assert first == 1693 and all(s and r.m_402_kgh == 0.0 for r, s in out[first:])
    assert out[first][0].level_pct < 5.0 <= out[first - 1][0].level_pct
    assert out[first - 1][0].m_402_kgh == pytest.approx(69499.13, abs=0.01)
    assert all(r.converged and r.seal_air_kgh == 0.0 for r, _ in out)
    assert (unit.m_kg, r.t_c, unit.w["Urea"]) == (pytest.approx(346.043, abs=1e-3),
                                                  pytest.approx(175.3256, abs=1e-4),
                                                  pytest.approx(0.98644, abs=1e-5))


def test_a_feed_pump_trip_on_ac4s_header_stops_335p001_on_ly_324501s_l2_b63():
    """Decision 217 on B-63: stage 2 finishes the leg's melt as with the stop off, and when
    LY-324501 passes below 5 % at 354.0 s AC4 stops 335P001A / B; the leg has run dry, so the level
    cannot recover: the drain stays shut, the seal never uncovers and stage 2 holds 346.7 kg of melt
    at 162.18 C and 98.41 %, never below 140 C."""
    run = _chain(4000, cut_at=5)
    first = next(k for k in range(400, 4000) if run[k][1].m_402_kgh == 0.0)
    assert first == 3540 and all(r2.m_402_kgh == 0.0 for _, r2 in run[first:])
    assert run[first][1].level_pct < 5.0 <= run[first - 1][1].level_pct
    assert all(r.converged and r.t_c >= 140.0 and r.seal_air_kgh == 0.0 for _, r in run)
    r2 = run[-1][1]
    assert (r2.m_kg, r2.t_c, r2.w["Urea"]) == (pytest.approx(346.693, abs=1e-3),
                                               pytest.approx(162.1849, abs=1e-4),
                                               pytest.approx(0.98413, abs=1e-5))


def test_on_b62_and_b63_the_trips_follow_the_l2_stop_and_leave_the_holdup_as_it_was():
    """Decision 228 on §CXXI.6's two cases: the L2 stop loses 35.1 and 35.4 on its tick, and from
    the next LV-324501A is shut, LIC-324501 clamped at 100 %, HV-335602 driven open and 335P002
    held. With no feed the pumps stay stopped, so stage 2 holds what it holds without the trips, to
    the bit: the seal is the L2 stop's. What the trips change is the valves: LV-324501A parked shut
    where without them PIC-335201 winds it open on the empty header."""
    trips, unit, loops = _pc35(), se.SecondEvaporator(), se.SecondEvaporatorLoops()
    for k in range(3000):
        feed = 0.0 if k >= 5 else d.P1_DES_KGH
        r = unit.step(loops, feed, d.E001_T_DES_C, d.W_S401, P_MP_BARA, P_MOTIVE, P_E006, TV5,
                      d.PIC_335201_DES_BARG, 0.1, trips=trips.actions)
        _trips_beside(trips, unit)
    assert (unit.m_kg, r.t_c, unit.w["Urea"]) == (pytest.approx(346.043, abs=1e-3),
                                                  pytest.approx(175.3256, abs=1e-4),
                                                  pytest.approx(0.98644, abs=1e-5))
    assert (trips.flag_35_1.latched, trips.flag_35_4.latched, trips.p002_held) == (True,) * 3
    assert (loops.level.op, unit.header.lv_a_position_pct, unit.header.hv_pct) == (100.0, 0.0, 100.0)
    off, on = _chain(4000, cut_at=5), _chain(4000, cut_at=5, trips=_pc35())
    assert [(a[1].m_kg, a[1].t_c, a[1].m_402_kgh) for a in off] == [
        (b[1].m_kg, b[1].t_c, b[1].m_402_kgh) for b in on]
