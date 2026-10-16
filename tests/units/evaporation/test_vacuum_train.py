"""Behaviour of unit 324's vacuum train — `ureasim.units.evaporation.vacuum_train`.

Equivalence with V1 is proven in `tests/equivalence/test_vacuum_train_equivalence.py`, and the
decided divergences both ways in `tests/equivalence/test_vacuum_train_decided_equivalence.py`.
This file pins what the train DOES: the PFD's rows at design, the motive valves on their trims,
the PFD's motive steam condensed (handoff B-64), and the train in the loop with both stages as the
plant runs it (`VacuumTrain`) — the cold ends lagged on their tube-side water (handoff B-65), so a
trip no longer pulses, and 324E006's shell live (handoff B-66), so a lost 324E006 breaks stage 2's
vacuum. Each condenser's NH3 and CO2 vent rides B-67's additive departure or V1's ratio, as B-71 puts it
(decided 2026-10-02).
"""

from __future__ import annotations

import math

import pytest

from ureasim.data import unit_324 as d
from ureasim.data import unit_324_train as t
from ureasim.data.design_point import R324_FEED_DES
from ureasim.data.unit_323 import MEVAP_DES_KGH, W_S317
from ureasim.data.unit_323c005 import C005_P_BARA
from ureasim.data.unit_329 import P_LP_BARA, P_MP_BARA
from ureasim.units.evaporation import ejector_map as em
from ureasim.units.evaporation import first_evaporator as fe
from ureasim.units.evaporation import second_evaporator as se
from ureasim.units.evaporation import vacuum_train as vt
from ureasim.units.evaporation.vacuum_condenser import design_specs

DES = (t.HV_329605_OP_DES_PCT, t.HV_329606_OP_DES_PCT)
PFD = {"703": 26840.0, "705": 14799.0, "706": 72.0, "708": 462.0, "709": 3342.0, "712": 584.0,
       "714": 1804.0, "715": 41.0, "717": 221.0, "719": 26768.0, "720": 2758.0, "721": 1763.0,
       "722": 31.0, "759": 190.0, "790": 12040.0, "924": 390.0, "927": 1220.0, "929": 180.0}
E006_CW_KGH = d.VACUUM_CONDENSERS["324E006"].cw_flow_kgh


def _train(motive=vt.MotiveSteam(390.0, 1220.0, 180.0), **over):
    x = {"m790": MEVAP_DES_KGH, "v1": d.V1_DES_KGH, "v2": d.V2_DES_KGH}
    x.update(over)
    return vt.vacuum_train(x["m790"], x["v1"], x["v2"], 21.0, 21.0, motive)


def _plant(n, cut_at=None, hic=lambda k: DES, cw=lambda k: None):
    """Stage 1, stage 2 and the train, in V1's order on each tick: the stages read the train's
    lagged cold ends and 324F004 discharges against 324E006's shell, each as the train left them
    on the tick before."""
    u1, l1 = fe.FirstEvaporator(), fe.FirstEvaporatorLoops()
    u2, l2 = se.SecondEvaporator(), se.SecondEvaporatorLoops()
    train = vt.VacuumTrain()
    out = []
    for k in range(n):
        feed = 0.0 if cut_at is not None and k >= cut_at else R324_FEED_DES
        mot = vt.motive_steam(*hic(k))
        r1 = u1.step(l1, feed, 99.0, W_S317, P_LP_BARA,
                     em.nozzle_pressure_bara("324F002", mot.m_924_kgh), C005_P_BARA,
                     MEVAP_DES_KGH, None, train.cold_end_c("324E002"), 0.1)
        r2 = u2.step(l2, r1.m_401_kgh, r1.t_c, r1.w, P_MP_BARA,
                     em.nozzle_pressure_bara("324F004", mot.m_927_kgh), train.p_324e006_bara,
                     train.cold_end_c("324E005"), d.PIC_335201_DES_BARG, 0.1)
        tr = train.step(MEVAP_DES_KGH, r1.m_vap_kgh + r1.m_boil_kgh,
                        r2.m_vap_kgh + r2.m_boil_kgh, r1.false_air_kgh, r2.false_air_kgh, mot,
                        r1.p_bara, r2.p_bara, 0.1, cw_flow_kgh=cw(k))
        out.append((r1, r2, tr))
    return out


def _pulses(xs, threshold):
    """Reversals of a series where both legs exceed the threshold: a tear ringing."""
    return sum(1 for a, b, c in zip(xs, xs[1:], xs[2:])
               if (b - a) * (c - b) < 0 and abs(b - a) > threshold and abs(c - b) > threshold)


def test_the_design_is_the_pfd():
    """Every row PFD-21's at design to 1e-8 kg/h (324E007's vent, B-67 / B-71, reaches 722 and
    759 at 2.5e-9), the four condensates 31 479 kg/h to 328D003, the cold ends the design
    solves', and 708's inerts 324E002's vent's."""
    tr = _train()
    assert tr.streams_kgh == pytest.approx(PFD, abs=1e-8)
    assert tr.condensate_kgh == pytest.approx(31479.0, abs=1e-8)
    assert tr.mixing_residual_703_kgh == 1.0
    assert tr.p_324e006_bara == 0.3
    for tag in ("324E002", "324E005"):
        assert tr.nodes[tag].t_vent_c == design_specs()[tag].t_v_solved_des
    assert tr.inert_706_kmolh == {k: tr.nodes["324E002"].vent_kmolh[k] for k in ("N2", "O2")}
    assert all(abs(n.mass_residual_kgh) < 1e-9 for n in tr.nodes.values())


def test_the_motive_steam_at_its_design_strokes():
    """HV-329605 at 69.06 % and HV-329606 at 80.16 % on the LP header's 4.0 bar g pass the PFD's
    390, 1220 and 180 kg/h to the bit, the nozzles at the duties' 4.1 bar a; shut, nothing."""
    assert DES == (pytest.approx(69.057, abs=1e-3), pytest.approx(80.165, abs=1e-3))
    m = vt.motive_steam(*DES)
    assert (m.m_924_kgh, m.m_927_kgh, m.m_929_kgh) == (390.0, 1220.0, 180.0)
    assert vt.motive_steam(*DES, p_lp_bara=P_LP_BARA) == m
    assert vt.motive_steam(0.0, 0.0) == vt.MotiveSteam(0.0, 0.0, 0.0)
    assert em.nozzle_pressure_bara("324F004", m.m_927_kgh) == 4.1


@pytest.mark.parametrize("p_lp, m_924, m_927", [(4.8, 373.663, 1168.910), (4.5, 350.658, 1096.965),
                                                (4.1, 319.942, 1000.899), (2.1, 165.443, 517.654)])
def test_the_motive_steam_follows_the_lp_header_b73(p_lp, m_924, m_927):
    """Handoff B-73, decided 2026-10-02 (the Typo Rule). The valves pass the LP header's steam to
    the nozzles they feed, so at their design strokes the motive falls with the header: 96 % of it
    at 4.8 bar a, 82 % at the nozzles' own 4.1 bar a, 42 % at 2.1 bar a — where V1's lines pass
    the design motive from a header at any pressure. On each the valve's flow and the nozzle's
    agree: the flow is the nozzle's pressure's, P_n / 4.1 of the design."""
    m = vt.motive_steam(*DES, p_lp_bara=p_lp)
    assert (m.m_924_kgh, m.m_927_kgh) == (pytest.approx(m_924, abs=1e-3),
                                          pytest.approx(m_927, abs=1e-3))
    assert m.m_929_kgh == pytest.approx(m.m_927_kgh * 180.0 / 1220.0, rel=1e-12)
    p_n = em.nozzle_pressure_bara("324F002", m.m_924_kgh)
    assert vt.motive_ratio(DES[0], DES[0], t.HV_329605_XT, p_lp) == pytest.approx(
        p_n / 4.1, rel=1e-12)


def test_the_train_condenses_the_pfds_motive_b64():
    """Handoff B-64, decided 2026-10-02, option a. On the PFD's 1220 and 180 kg/h of motive steam
    324E006 and 324E007 see their anchored 1804 and 221 kg/h and the PFD's rows close. On Uhde's
    1061 and 366 — the nozzles' rating — 324E006 would see 1645 kg/h and 324E007 402, twice its
    row: its cold end at 93.3 C where the PFD has 55, and 109 kg/h to atmosphere where it has 31."""
    tr = _train()
    assert (tr.streams_kgh["714"], tr.streams_kgh["717"]) == (1804.0,
                                                              pytest.approx(221.0, abs=1e-9))
    uhde = _train(vt.MotiveSteam(390.0, 1061.0, 366.0))
    s = uhde.streams_kgh
    assert (s["714"], s["717"]) == (pytest.approx(1645.0, abs=1e-9),
                                    pytest.approx(402.200, abs=1e-3))
    assert uhde.nodes["324E007"].t_vent_c == pytest.approx(93.331, abs=1e-3)
    assert s["722"] == pytest.approx(109.030, abs=1e-3)


def test_the_cold_end_lags_are_the_tubes_water_residence_b65():
    """Handoff B-65, decided 2026-10-02. tau = V_tubes / Q_cw on the datasheets' tubes and the
    PFD's cooling water at its mean temperature's density: 324E002's 2329 tubes of 21.8 mm bore
    over 5.9 m hold 5.13 m3 against 1591 t/h, 11.54 s; 324E005's 486 over 4.9 m, 7.67 s;
    324E006's 250 of 16 mm over 3.6 m, 3.12 s."""
    taus = {tag: vt.cold_end_tau_s(tag) for tag in vt.LAGGED_COLD_ENDS}
    assert taus == {"324E002": pytest.approx(11.536, abs=1e-3),
                    "324E005": pytest.approx(7.672, abs=1e-3),
                    "324E006": pytest.approx(3.116, abs=1e-3)}
    r = d.VACUUM_CONDENSERS["324E002"]
    v_tubes = r.tube_count * math.pi / 4.0 * 0.0218 ** 2 * 5.9
    assert v_tubes == pytest.approx(5.1289, abs=1e-4)
    assert taus["324E002"] == pytest.approx(v_tubes / (r.cw_flow_kgh / 3600.0 / 993.996),
                                            rel=1e-4)


def test_the_train_alone_holds_its_design_seed():
    """Seeded on the design, the train on the design's inputs keeps 324E006's shell at 0.3 bar a
    to 1e-13 (324F005's map reads its design load as 41.00000000000001 kg/h) and the lagged cold
    ends where the design solves put them."""
    train = vt.VacuumTrain()
    mot = vt.motive_steam(*DES)
    for _ in range(20):
        tr = train.step(MEVAP_DES_KGH, d.V1_DES_KGH, d.V2_DES_KGH, 21.0, 21.0, mot,
                        d.F001_P_DES_BARA, d.F003_P_DES_BARA, 0.1)
    assert train.p_324e006_bara == pytest.approx(0.3, abs=1e-13)
    assert tr.p_324e006_bara == train.p_324e006_bara
    for tag in vt.LAGGED_COLD_ENDS:
        assert train.cold_end_c(tag) == pytest.approx(design_specs()[tag].t_v_solved_des,
                                                      abs=1e-9)
    assert tr.streams_kgh == pytest.approx(PFD, abs=1e-8)


def test_the_two_stages_and_the_train_hold_the_design_together():
    """Five minutes of the three in the loop: both stages on their design points (within 2e-5 K,
    the chests' vendor trims answering the seed's own first-tick move, decided 2026-10-14), every row
    within 0.04 kg/h of the PFD's — stage 1's held melt boils 1.6 kg/h, PFD 317's 80.0016 %
    urea against V1's 80 % (B-62) — 324E006's shell within 4e-7 bar of 0.3 and the cold ends
    within 1e-4 K of the design solves', 324E007's within 6e-4 K (its vent, B-67 / B-71)."""
    r1, r2, tr = _plant(3000)[-1]
    assert (r1.t_c, r1.p_bara) == (pytest.approx(130.0, abs=1e-5), pytest.approx(0.33, abs=1e-6))
    assert (r2.t_c, r2.p_bara) == (pytest.approx(140.0, abs=2e-5),
                                   pytest.approx(0.131, abs=1e-6))
    assert tr.streams_kgh == pytest.approx(PFD, abs=0.04)
    assert tr.p_324e006_bara == pytest.approx(0.3, abs=4e-7)
    for tag in ("324E002", "324E005", "324E006", "324E007"):
        assert tr.nodes[tag].t_vent_c == pytest.approx(design_specs()[tag].t_v_solved_des,
                                                       abs=6e-4 if tag == "324E007" else 1e-4)


def test_less_motive_on_hv_329606_unloads_the_back_of_the_train():
    """HV-329606 ten points below its design stroke: 87 % of the motive, 1066 and 157 kg/h, the
    nozzles at 3.58 bar a — their lower back-pressure opens the valve's differential (B-73). 324F004's
    map, still critical, pulls a shade more (B-61) and after ten minutes stage 2 sits at 0.13058 bar
    a with PIC-324203 bleeding 21.1 kg/h; 324F005's map pulls 324E006's shell down to 0.276 bar a
    (B-66); 324E006 condenses 1622 kg/h where it condensed 1763, and 324E007 sends 26.7 kg/h to
    atmosphere."""
    r1, r2, tr = _plant(6005, hic=lambda k: (DES[0], DES[1] - 10.0) if k >= 5 else DES)[-1]
    s = tr.streams_kgh
    assert (s["927"], s["929"]) == (pytest.approx(1065.972, abs=1e-3),
                                    pytest.approx(157.275, abs=1e-3))
    assert em.nozzle_pressure_bara("324F004", s["927"]) == pytest.approx(3.5824, abs=1e-4)
    assert r2.p_bara == pytest.approx(0.1305824, abs=1e-6)
    assert r2.false_air_kgh == pytest.approx(21.0968, abs=1e-3)
    assert tr.p_324e006_bara == pytest.approx(0.276426, abs=1e-5)
    assert (s["714"], s["721"], s["722"]) == (pytest.approx(1661.415, abs=0.01),
                                              pytest.approx(1622.252, abs=0.01),
                                              pytest.approx(26.672, abs=0.01))
    assert r1.p_bara == pytest.approx(0.33, abs=1e-6)


def test_a_lost_324e006_breaks_stage_2s_vacuum_b66():
    """Handoff B-66, decided 2026-10-02. 324E006's cooling water lost. Its shell reaches
    324E007's 1.0 bar a 2.4 s later; 324F004, discharging against it, breaks — its critical back
    pressure 0.54 bar a at the suction stage 2 climbs to, so it keeps 1.4 % of its capacity — and
    stage 2's vacuum is lost: 0.152 bar a in 4.5 s, 0.2587 in two minutes, the melt from 140 to
    144.0 C, PIC-324203 closing its bleed to 73 % (12.0 kg/h) against it. 324E005 still condenses
    stage 2's vapour, so the vacuum holds there; 324E007 takes what 324E006 no longer condenses
    and sends 1128 kg/h to atmosphere. No pulse on the way."""
    run = _plant(1200, cw=lambda k: {"324E006": 0.0} if k >= 5 else None)
    shell = [tr.p_324e006_bara for _, _, tr in run]
    assert shell[5] == pytest.approx(0.3, abs=1e-8)
    assert shell.index(1.0) == 29
    _, r2, tr = run[50]
    # 0.151936 before the held melt's boil was bounded at the melt model's 99 C window (Phase 7,
    # As-Built §LXII.4): the implicit pressure step's deep trial vacuums boil a little less.
    assert r2.p_bara == pytest.approx(0.151562, abs=1e-6)
    r1, r2, tr = run[-1]
    assert r2.p_bara == pytest.approx(0.258704, abs=1e-6)
    assert r2.t_c == pytest.approx(143.966, abs=1e-3)
    assert (r2.vacuum_op_pct, r2.false_air_kgh) == (pytest.approx(73.414, abs=1e-3),
                                                    pytest.approx(12.0272, abs=1e-3))
    _, p_crit = em.interpolated("324F004", r2.p_bara, 4.1)
    assert p_crit == pytest.approx(0.5404, abs=1e-4)
    assert em.unchoked_fraction(tr.p_324e006_bara, p_crit) == pytest.approx(0.0136, abs=1e-4)
    s = tr.streams_kgh
    assert (s["712"], s["721"], s["722"]) == (pytest.approx(17.270, abs=1e-3), 0.0,
                                              pytest.approx(1127.976, abs=1e-3))
    assert r1.p_bara == pytest.approx(0.33, abs=1e-6)
    assert _pulses([r2.p_bara for _, r2, _ in run], 1e-5) == 0
    assert _pulses(shell, 1e-5) == 0


def test_324e006_on_a_fifth_of_its_water_b66():
    """A fifth of 324E006's cooling water: the shell climbs to 0.3584 bar a and settles, 715 to
    54.7 kg/h; 324F004 stays critical below its 0.369 bar a, so stage 2 holds its vacuum to 2e-8
    bar — the margin an operator has before the next condenser starts to cost stage 2."""
    _, r2, tr = _plant(700, cw=lambda k: {"324E006": 0.2 * E006_CW_KGH} if k >= 5 else None)[-1]
    assert tr.p_324e006_bara == pytest.approx(0.358387, abs=1e-5)
    assert tr.streams_kgh["715"] == pytest.approx(54.723, abs=1e-2)
    assert r2.p_bara == pytest.approx(0.131, abs=5e-8)


def test_324e006s_water_restored_recovers_its_shell_b66():
    """The train alone on the design's inputs: thirty seconds without 324E006's water hold the
    shell at 324E007's 1.0 bar a, its cold end at the vapour's 104 C; the water back, the shell
    is at 0.369 bar a twenty seconds later, 0.3001 in a minute, and back on its 0.3 within 1e-6 in
    two and a half."""
    train = vt.VacuumTrain()
    mot = vt.motive_steam(*DES)
    shell = []
    for k in range(1800):
        tr = train.step(MEVAP_DES_KGH, d.V1_DES_KGH, d.V2_DES_KGH, 21.0, 21.0, mot,
                        d.F001_P_DES_BARA, d.F003_P_DES_BARA, 0.1,
                        cw_flow_kgh={"324E006": 0.0} if k < 300 else None)
        shell.append(train.p_324e006_bara)
        if k == 299:
            assert train.cold_end_c("324E006") == pytest.approx(103.995, abs=1e-3)
            assert tr.streams_kgh["715"] == 1804.0
    assert shell[299] == 1.0
    assert shell[499] == pytest.approx(0.36880, abs=1e-4)
    assert shell[899] == pytest.approx(0.30009, abs=1e-4)
    assert shell[-1] == pytest.approx(0.3, abs=1e-6)
    assert tr.streams_kgh["715"] == pytest.approx(41.0, abs=1e-3)


@pytest.mark.parametrize("motive, p_lp, t_708", [
    ((195.0, 610.0, 90.0), P_LP_BARA, 112.9171),
    ((468.0, 1464.0, 216.0), P_LP_BARA, 122.5274),
    ((0.0, 0.0, 0.0), P_LP_BARA, 63.0401),
    ((390.0, 1220.0, 180.0), 4.4, 118.3998),
])
def test_708_leaves_at_324f002s_discharge_b97(motive, p_lp, t_708):
    """B-97, decided 2026-10-16: 708 at 324F002's adiabatic mix of 706 and 924 as its departure
    from the design mix, 121 C to the bit at design. Half the motive steam sends it at 112.92 C, a
    fifth more at 122.53; HIC-329605 shut, 706 alone at 63.04 C, its water condensing at the mixing
    point; the PFD's 4.4 bar a header, steam of less enthalpy, 118.40. The masses stay V1's."""
    def run(mot, p):
        return vt.vacuum_train(MEVAP_DES_KGH, d.V1_DES_KGH, d.V2_DES_KGH, 21.0, 21.0,
                               vt.MotiveSteam(*mot), p_lp_bara=p)
    assert run((390.0, 1220.0, 180.0), P_LP_BARA).t_708_c == 121.0
    r = run(motive, p_lp)
    assert r.t_708_c == pytest.approx(t_708, abs=1e-4)
    assert r.streams_kgh == run(motive, P_LP_BARA).streams_kgh
