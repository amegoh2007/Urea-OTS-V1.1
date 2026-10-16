"""Behaviour of 324E001 / 324F001, stage 1 of unit 324 — `ureasim.units.evaporation.first_evaporator`.

Equivalence with V1 is proven tick by tick in `tests/equivalence/test_first_evaporator_equivalence.py`
and each departure both ways in `test_first_evaporator_decided_equivalence.py`. This file pins
what the stage DOES: the design seed held on 324F002's design-anchored map (handoff B-61),
PV-324202's vendor trim, a lost header, a lost feed boiling the held melt (B-62), and the vendor
anchor B-61 replaced.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_324 as d
from ureasim.data.design_point import R324_FEED_DES
from ureasim.data.unit_323 import MEVAP_DES_KGH, W_S317
from ureasim.data.unit_329 import P_LP_BARA
from ureasim.units.evaporation import ejector_map as em
from ureasim.units.evaporation import first_evaporator as fe
from ureasim.units.evaporation.vacuum_condenser import design_specs

TV = design_specs()["324E002"].t_v_solved_des

#: 324F002's motive at its nozzle at design [bar a] and 323C005, what it discharges into.
P_MOTIVE = em.nozzle_pressure_bara("324F002", d.F002_MOTIVE_DES_KGH)
P_C005 = 1.0


def _run(n, feed=R324_FEED_DES, p_lp=P_LP_BARA, p_motive=P_MOTIVE):
    unit, loops = fe.FirstEvaporator(), fe.FirstEvaporatorLoops()
    r = None
    for _ in range(n):
        r = unit.step(loops, feed, 99.0, W_S317, p_lp, p_motive, P_C005, MEVAP_DES_KGH, None,
                      TV, 0.1)
    return unit, loops, r


def test_the_design_seed_holds():
    """An hour at design on 324F002's design-anchored map: the melt within 1e-6 K of 130 C,
    PT-324201 within 1e-9 bar of 0.33, PV-324202 at its 61.07 %, PFD 705's 14 072 kg/h boiled.
    PFD 317 normalised is 80.0016 % urea against V1's 80 %, which is all that moves: the held
    melt boils it off, 1.6 kg/h (B-62)."""
    unit, loops, r = _run(36000)
    assert r.t_c == pytest.approx(130.0, abs=1e-6)
    assert r.p_bara == pytest.approx(0.33, abs=1e-9)
    assert loops.vacuum.op == pytest.approx(d.PV_324202_OP_DES_PCT, abs=1e-4)
    assert r.m_vap_kgh == pytest.approx(14071.5, abs=0.1)
    assert r.m_boil_kgh == pytest.approx(1.65, abs=0.01)
    assert r.w_melt == pytest.approx(0.94310, abs=1e-5)
    assert r.converged and r.iterations <= 7


def test_pv_324202_on_its_vendor_trim():
    """PFD 784's 21 kg/h at the 61.07 % Flowserve's sizing gives; wide open, the 67.4 kg/h its
    Kvs 4 passes on the sizing case."""
    assert fe.false_air_kgh(d.PV_324202_OP_DES_PCT) == pytest.approx(21.0, rel=1e-12)
    assert fe.false_air_kgh(100.0) == pytest.approx(67.399, abs=1e-3)
    assert fe.barometric_leg_kgh(d.F001_M_DES_KG) == d.P1_DES_KGH


def test_a_lost_header_dilutes_the_melt():
    """The LP header to 1.2 bar a: on PV-329203's vendor trim (decided 2026-10-14) the melt falls
    to 101.46 C and 84.45 % urea, and the stage boils 4882 kg/h where it boiled 14 072 (99.9 C,
    83.4 % and 3780 on V1's linear valve); the held melt, cooling, does not boil on its own."""
    _, _, r = _run(18000, p_lp=1.2)
    assert r.t_c == pytest.approx(101.458, abs=0.001)
    assert r.w_melt == pytest.approx(0.8445, abs=1e-4)
    assert r.m_vap_kgh == pytest.approx(4882.1, abs=0.5)
    assert r.m_boil_kgh == 0.0


def test_a_lost_feed_boils_the_held_melt_as_it_drains_b62():
    """Handoff B-62, decided 2026-10-01. 323P003 stops. The chest's duty, no longer spent on the
    feed, boils the held melt: about 1.14 t/h after a minute, the melt at 150.15 C and 96.81 %,
    holding at its own boiling point as it concentrates. The chest fills to the 5.013 bar a
    header; at 151.82 C (PV-329203 on its vendor trim) the melt's equilibrium at the vacuum is
    97.06 % and it
    boils no more. The leg drains 324F001 to its 1 kg floor in ten minutes and no further."""
    unit, loops = fe.FirstEvaporator(), fe.FirstEvaporatorLoops()
    for k in range(6000):
        r = unit.step(loops, 0.0, 99.0, W_S317, P_LP_BARA, P_MOTIVE, P_C005, MEVAP_DES_KGH, None,
                      TV, 0.1)
        if k == 600:
            assert (r.t_c, r.m_boil_kgh, unit.w["Urea"]) == (
                pytest.approx(150.1493, abs=1e-4), pytest.approx(1135.67, abs=0.01),
                pytest.approx(0.96814, abs=1e-5))
        assert r.converged
    assert unit.m_kg == 1.0 and r.m_401_kgh == 0.0
    assert r.m_vap_kgh == 0.0 == r.m_boil_kgh
    assert r.t_c == pytest.approx(151.824, abs=1e-3)
    assert unit.w["Urea"] == pytest.approx(0.97065, abs=1e-5)


def test_on_the_vendor_anchor_pv_324202_would_run_out_of_air_b61():
    """Handoff B-61's measurement, the anchor not taken. 324F002 on its vendor duty would pull
    214 kg/h at 0.33 bar a where PFD 706 is 72: PV-324202 wide open, 67.4 kg/h of air, could not
    hold the design vacuum. On the decided map the design holds at PV-324202's 61.07 %
    (`test_the_design_seed_holds`)."""
    vendor = em.vendor_map("324F002")
    assert em.critical_capacity_kgh(vendor, 0.33, P_MOTIVE) == pytest.approx(214.063, abs=1e-3)
    assert em.suction_capacity_kgh("324F002", 0.33, P_MOTIVE, P_C005) == pytest.approx(
        72.0, rel=1e-14)
    assert fe.false_air_kgh(100.0) < 214.063 - 72.0
