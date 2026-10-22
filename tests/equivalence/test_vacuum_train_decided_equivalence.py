"""V1 <-> V1.1 for the vacuum train's decided divergences, each asserted from both sides.

`test_vacuum_train_equivalence.py` proves `vacuum_train` ``==`` V1's ``vacuum_train_324``,
executed. The plant runs it through `VacuumTrain`, which departs from V1 twice, both decided by
the process engineer on 2026-10-02:

  * **The cold ends lagged on their tube-side water** (handoff B-65): V1 hands each stage the cold
    end its condenser settled at in the last solve, one tick late, and the held melt's boil-off
    (B-62) pulses on that tear through a trip. The port lags each cold end a vacuum balance reads
    on its tubes' water residence.
  * **324E006's shell a live vacuum node** (handoff B-66, the Typo Rule): V1 solves 324E006 at the
    PFD's 0.3 bar a whatever it condenses, so a lost 324E006 never reaches stage 2. The port
    integrates the shell between 324F004's discharge and 324F005's pull.

V1's side runs V1's own train, executed, with V1's tear: its solved cold ends fed straight back;
its condenser module carries handoff B-67's and B-71's switch (decided 2026-10-02,
`tests.equivalence.b67_switch`), so each departure here is run with the other decisions in force.
The stages are the port's on both sides (their own decided divergences are run both ways in their
files); at the design strokes V1's motive lines and the port's trims deliver the same steam.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_324 as d
from ureasim.data.design_point import R324_FEED_DES
from ureasim.data.unit_323 import MEVAP_DES_KGH, W_S317
from ureasim.data.unit_323c005 import C005_P_BARA
from ureasim.data.unit_329 import P_LP_BARA, P_MP_BARA
from ureasim.units.evaporation import ejector_map as em
from ureasim.units.evaporation import first_evaporator as fe
from ureasim.units.evaporation import second_evaporator as se
from ureasim.units.evaporation import vacuum_train as vt
from ureasim.units.evaporation.vacuum_condenser import design_specs
from tests.equivalence import test_vacuum_train_equivalence as h
from tests.equivalence.v1_loader import v1_available
from tests.units.evaporation.test_vacuum_train import _plant, _pulses

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

v1 = h.v1

#: The design motive, V1's lines at 50 % and the port's trims at their design strokes alike.
MOTIVE = (390.0, 1220.0, 180.0)


def _v1_tear_trip(v1, n: int, cut_at: int) -> list:
    """323P003 stops at tick `cut_at`: the two stages and V1's train, executed, in V1's order,
    V1's solved cold ends handed to the stages on the next tick (``324E002_T_VENT``,
    ``324E005_T_VENT``) and 324F004 discharging against V1's 0.3 bar a."""
    # V1's linear chest valves: PV-329203's and PV-329212's trims have their own tests.
    u1 = fe.FirstEvaporator(chest=fe.V1_CHEST, lv_329505=None)
    l1 = fe.FirstEvaporatorLoops(pic=fe.pic_329203(fe.V1_CHEST),
                                 trap=fe.lic_329505(fe.V1_TRAP_OP_DES_PCT))
    u2 = se.SecondEvaporator(chest=se.V1_CHEST, backward_species=False, seal_air=False,
                             bisect_fixed_point=False)
    l2 = se.SecondEvaporatorLoops(pic=se.pic_329212(se.V1_CHEST))
    tv2 = design_specs()["324E002"].t_v_solved_des
    tv5 = design_specs()["324E005"].t_v_solved_des
    out = []
    for k in range(n):
        feed = 0.0 if k >= cut_at else R324_FEED_DES
        r1 = u1.step(l1, feed, 99.0, W_S317, P_LP_BARA,
                     em.nozzle_pressure_bara("324F002", MOTIVE[0]), C005_P_BARA, MEVAP_DES_KGH,
                     None, tv2, 0.1)
        r2 = u2.step(l2, r1.m_401_kgh, r1.t_c, r1.w, P_MP_BARA,
                     em.nozzle_pressure_bara("324F004", MOTIVE[1]), d.E006_P_DES_BARA, tv5,
                     d.PIC_335201_DES_BARG, 0.1)
        tr = v1["vacuum_train_324"](
            MEVAP_DES_KGH, r1.m_vap_kgh + r1.m_boil_kgh, r2.m_vap_kgh + r2.m_boil_kgh,
            r1.false_air_kgh, r2.false_air_kgh, *MOTIVE, cw_factors={},
            p_e002_bara=r1.p_bara, p_e005_bara=r2.p_bara, sub_703=None)
        tv2 = tr["nodes"]["324E002"]["t_vent_c"]
        tv5 = tr["nodes"]["324E005"]["t_vent_c"]
        out.append((r1, r2, tr["streams_kgh"]))
    return out


def test_the_cold_ends_lagged_on_their_water_decided_divergence(v1):
    """Handoff B-65, decided 2026-10-02, option a. 323P003 stops; two minutes.

    V1: stage 2's held melt boils in pulses on V1's one-tick tear — 3698 kg/h, nothing for four
    ticks, 5685, nothing for three — 339 times (342 before the boil was bounded at the melt model's
    99 C window, As-Built §LXII.4); on the bursts 324E006 and 324E007 overload and 722
    sends up to 8.5 t/h to atmosphere. The port: the cold ends lag on their tubes' water (324E002
    11.54 s, 324E005 7.67 s, 324E006 3.12 s), and nothing pulses — not the boil-off, stage 2's
    vacuum, 324E006's shell, PFD 709 nor stage 1's boil-off. Stage 2's boil-off climbs from 110
    kg/h two seconds in to 1099 at thirty and 1240 at a minute (PV-329203 and PV-329212 on their
    vendor trims, decided 2026-10-14); 722 stays at the PFD's 31 kg/h;
    the melt never falls below its 140 C design."""
    theirs = _v1_tear_trip(v1, 1200, 5)
    b2 = [r2.m_boil_kgh for _, r2, _ in theirs]
    assert [round(x, 1) for x in b2[26:31]] == [0.0, 5685.0, 0.0, 0.0, 0.0]
    assert _pulses(b2, 50.0) == 339
    assert max(s["722"] for _, _, s in theirs[:700]) == pytest.approx(8469.71, abs=0.01)

    mine = _plant(1200, cut_at=5)
    b2 = [r2.m_boil_kgh for _, r2, _ in mine]
    assert _pulses(b2, 50.0) == 0
    assert _pulses([r2.p_bara for _, r2, _ in mine], 1e-5) == 0
    assert _pulses([tr.p_324e006_bara for _, _, tr in mine], 1e-5) == 0
    assert _pulses([tr.streams_kgh["709"] for _, _, tr in mine], 50.0) == 0
    assert _pulses([r1.m_boil_kgh for r1, _, _ in mine], 50.0) == 0
    assert [round(b2[k], 1) for k in (26, 300, 600)] == [109.6, 1099.2, 1240.5]
    assert max(tr.streams_kgh["722"] for _, _, tr in mine[:700]) == pytest.approx(31.000,
                                                                                  abs=1e-3)
    assert min(r2.t_c for _, r2, _ in mine) >= 140.0


def test_324e006s_shell_live_decided_divergence(v1):
    """Handoff B-66, decided 2026-10-02 (the Typo Rule). 324E006's cooling water lost at design.

    V1, executed: 324E006 condenses nothing and passes all 1804 kg/h on — 722 sends 1638 kg/h to
    atmosphere — yet its shell stays at the literal 0.3 bar a, and 324E005, the condenser stage 2
    reads, is to the bit what it was: stage 2 never learns. The port's `vacuum_train` is V1's
    here too. The port's `VacuumTrain`: the shell, 0.542 m3 on 324E006's name plate, reaches
    324E007's 1.0 bar a in 2.5 s (0.876 bar a at 2.1 s); against it 324F004 entrains nothing at stage 2's design
    vacuum (its critical back pressure 0.369 bar a; it passes nothing past 1.85 times that)."""
    x = h._inputs(cw={"324E006": 0.0})
    mine, theirs = h._compare(v1, x)
    base = v1["vacuum_train_324"](MEVAP_DES_KGH, d.V1_DES_KGH, d.V2_DES_KGH, 21.0, 21.0,
                                  *MOTIVE, cw_factors={}, p_e002_bara=d.F001_P_DES_BARA,
                                  p_e005_bara=d.F003_P_DES_BARA, sub_703=None)
    e006 = theirs["nodes"]["324E006"]
    assert (e006["p_bara"], e006["condensate_kgh"], e006["vent_kgh"]) == (0.3, 0.0, 1804.0)
    assert theirs["streams_kgh"]["722"] == pytest.approx(1638.13, abs=0.01)
    assert theirs["nodes"]["324E005"] == base["nodes"]["324E005"]
    assert mine.p_324e006_bara == 0.3

    train = vt.VacuumTrain()
    mot = vt.MotiveSteam(*MOTIVE)
    shell = []
    for _ in range(40):
        train.step(MEVAP_DES_KGH, d.V1_DES_KGH, d.V2_DES_KGH, 21.0, 21.0, mot,
                   d.F001_P_DES_BARA, d.F003_P_DES_BARA, 0.1, cw_flow_kgh={"324E006": 0.0})
        shell.append(train.p_324e006_bara)
    assert shell[0] == pytest.approx(0.3, abs=1e-12)
    assert shell[20] == pytest.approx(0.8760, abs=1e-4)
    assert shell.index(1.0) == 24
    _, p_crit = em.interpolated("324F004", d.F003_P_DES_BARA, 4.1)
    assert p_crit == pytest.approx(0.369, abs=1e-3)
    assert em.unchoked_fraction(train.p_324e006_bara, p_crit) == 0.0
    assert em.unchoked_fraction(0.3, p_crit) == 1.0
