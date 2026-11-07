"""Behaviour of 324E003 / 324F003, stage 2 of unit 324 — `ureasim.units.evaporation.second_evaporator`.

Equivalence with V1 is proven tick by tick in
`tests/equivalence/test_second_evaporator_equivalence.py` and each departure both ways in
`test_second_evaporator_decided_equivalence.py`. This file pins what the stage DOES: the design
seed held on 324F004's design-anchored map (handoff B-61), PV-324203's vendor trim, a lost header,
a lost feed boiling the held melt (B-62), LV-324501B taking the melt when the 335 header backs up,
stage 1 and stage 2 run together — and a feed-pump trip, stage 2 taking the leg's strength (B-63).
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_324 as d
from ureasim.data.design_point import R324_FEED_DES
from ureasim.data.unit_323 import MEVAP_DES_KGH, W_S317
from ureasim.data.unit_329 import P_LP_BARA, P_MP_BARA
from ureasim.units.evaporation import ejector_map as em
from ureasim.units.evaporation import first_evaporator as fe
from ureasim.units.evaporation import second_evaporator as se
from ureasim.units.evaporation.vacuum_condenser import design_specs

TV5 = design_specs()["324E005"].t_v_solved_des
TV2 = design_specs()["324E002"].t_v_solved_des

#: 324F004's motive at its nozzle at design and 324E006, what it discharges into [bar a].
P_MOTIVE = em.nozzle_pressure_bara("324F004", d.EJECTOR_DESIGN_LOADS["324F004"].motive_kgh)
P_E006 = d.E006_P_DES_BARA


def _run(n, feed=d.P1_DES_KGH, p_mp=P_MP_BARA, p335=d.PIC_335201_DES_BARG):
    unit, loops = se.SecondEvaporator(), se.SecondEvaporatorLoops()
    r = None
    for _ in range(n):
        r = unit.step(loops, feed, d.E001_T_DES_C, d.W_S401, p_mp, P_MOTIVE, P_E006, TV5, p335,
                      0.1)
    return unit, loops, r


def test_the_design_seed_holds():
    """An hour at design on 324F004's design-anchored map: the melt at 140 C, PT-324203 at
    0.131 bar a to 1e-14 (324E005's condenser falsi reaches the last bits), PV-324203 at its 92.03 %, LV-324501A at its 75.35 % (decision 150), PFD 709's 2738 kg/h
    boiled, PFD 402 at 97.71 %, 3741 kg/h of 9-bar steam; the fixed point in one iteration."""
    unit, loops, r = _run(36000)
    assert r.t_c == 140.0
    assert r.p_bara == pytest.approx(0.131, abs=1e-14)
    assert loops.vacuum.op == pytest.approx(d.PV_324203_OP_DES_PCT, abs=1e-9)
    assert loops.level.op == d.LV_324501A_OP_DES_PCT and unit.m_kg == pytest.approx(d.F003_M_DES_KG, rel=1e-12)
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
    chord, before decision 170, 2026-11-06 put Valmet's S-Disc table between its printed points.)"""
    unit, loops = se.SecondEvaporator(), se.SecondEvaporatorLoops()
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


def test_the_335_header_backing_up_sends_the_melt_to_323d002():
    """PIC-335201 above its 3.8 bar g relief setting: LIC-324501's stroke goes to LV-324501B and
    the whole drain, the raw melt at 140 C, returns to 323D002; nothing goes forward. On its sheet
    (decision 150) LV-324501B passes 95.7 t/h at the stroke, its 5.1 bar to 323D002 against A's
    3.2; V1's span law passed the design drain on either valve."""
    _, _, r = _run(10, p335=4.0)
    assert r.recycle_selected and (r.lv_a_pct, r.lv_b_pct) == (0.0, pytest.approx(75.286,
                                                                                  abs=1e-3))
    assert (r.route.route, r.route.forward_kgh) == ("B", 0.0)
    assert r.route.recycle_kgh == r.m_402_kgh == pytest.approx(95657.2, abs=0.1)
    assert r.route.recycle_t_c == 140.0
    assert sum(r.route.recycle_w.values()) == pytest.approx(1.0, abs=1e-12)


def _chain(n, cut_at=None):
    u1, l1 = fe.FirstEvaporator(), fe.FirstEvaporatorLoops()
    u2, l2 = se.SecondEvaporator(), se.SecondEvaporatorLoops()
    out = []
    for k in range(n):
        m = 0.0 if cut_at is not None and k >= cut_at else R324_FEED_DES
        r1 = u1.step(l1, m, 99.0, W_S317, P_LP_BARA, 4.1, 1.0, MEVAP_DES_KGH, None, TV2, 0.1)
        r2 = u2.step(l2, r1.m_401_kgh, r1.t_c, r1.w, P_MP_BARA, P_MOTIVE, P_E006, TV5,
                     d.PIC_335201_DES_BARG, 0.1)
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
    the feed at the leg's strength and finishes it: 1265 kg/h of the feed's water and 659 of its
    own holdup's boil off (662 on the chord, before decision 170), the melt at 141.9 C and 97.79 %
    (the chests on their vendor trims). The leg runs dry onto stage 1's heel
    at 350 s; stage 2 boils its last, LIC-324501 shuts LV-324501A at 638 s with the level at 21.6 %
    (its equal percentage passing little at low stroke, decision 150), and the melt holds 1496 kg
    at 98.40 % urea and 161.40 C (161.75 on the chord), the chest isolated at its saturation. The melt never
    falls below its 140 C design, where V1 — the strength stage 1 made, 0 — boiled the whole leg
    as water to -83 C in a minute."""
    run = _chain(12005, cut_at=5)
    r1, r2 = run[300]
    assert r1.w_melt == 0.0 and r1.w["Urea"] == pytest.approx(0.96054, abs=1e-5)
    assert r1.m_401_kgh == pytest.approx(71534.39, abs=0.01)
    assert r2.feed_urea_kgh == pytest.approx(68718.27, abs=0.01)
    assert (r2.m_vap_kgh, r2.m_boil_kgh) == (pytest.approx(1264.94, abs=0.01),
                                             pytest.approx(658.87, abs=0.01))
    assert (r2.t_c, r2.w_melt) == (pytest.approx(141.8909, abs=1e-4),
                                   pytest.approx(0.97793, abs=1e-5))
    assert all(r.converged and r.t_c >= 140.0 for _, r in run)
    assert next(k for k in range(400, 12005) if run[k][1].m_402_kgh == 0.0) == 6376
    r1, r2 = run[12004]
    assert r1.m_401_kgh == 0.0 and r2.m_402_kgh == 0.0 and r2.m_vap_kgh == 0.0 == r2.m_boil_kgh
    assert (r2.m_kg, r2.w["Urea"], r2.t_c) == (pytest.approx(1496.39, abs=0.01),
                                               pytest.approx(0.98396, abs=1e-5),
                                               pytest.approx(161.3953, abs=1e-4))
