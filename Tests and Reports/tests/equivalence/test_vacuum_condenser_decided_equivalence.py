"""V1 <-> V1.1 for the vacuum condensers' decided divergence, asserted from both sides.

Handoff B-67, decided 2026-10-02 (option a): each condenser's NH3 and CO2 vent pressures are the
PFD's partial pressures plus the departure of the condensate's back-pressure from its design value,
floored at zero, where V1 multiplies the PFD's partial pressure by the back-pressure's ratio to
design. 324E007's condensate, taken at its inlet's condensable composition, carries more CO2 than
its ammonia binds, so its design ammonia back-pressure is 24 Pa against the PFD vent's 1660 Pa of
ammonia: V1's ratio multiplies any rise by 68.

Handoff B-71, decided 2026-10-02: the departure is added only where the design back-pressure is at
most the PFD's partial pressure; above it V1's ratio stands — 324E007's CO2, 22.8 bar against the
PFD's 0.143, where an added departure is 159 times the ratio's response. So 324E005, whose NH3 and
CO2 both sit above, is V1's on every inlet, and 324E002 takes the addition on both.

Handoff B-87, decided 2026-10-09 (option b): every species the vent carries, and the inerts that
size it, is floored at zero, so a vent is never negative and a condenser never condenses more than it
receives; V1 sums the inerts as they come.

V1's side here is V1's own ``vacuum_condenser`` module and ``vacuum_train_324``, executed, unswitched;
`test_vacuum_condenser_equivalence.py` and the train's, stages' and node's equivalences run V1 with
the switch (`tests.equivalence.b67_switch`).
"""

from __future__ import annotations

import math

import pytest

from ureasim.data.unit_323 import MEVAP_DES_KGH
from ureasim.data.unit_324 import F003_FA_DES_KGH
from ureasim.units.evaporation.condenser_node import inlet_kmolh
from ureasim.units.evaporation import vacuum_condenser as vc
from ureasim.units.evaporation import vacuum_train as vt
from tests.equivalence.v1_loader import lift, load, v1_available
from tests.units.evaporation.test_vacuum_train import _plant

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

TAGS = ("324E002", "324E005", "324E006", "324E007")


@pytest.fixture(scope="module")
def v1():
    module = load("vacuum_condenser")
    ns = lift(["vacuum_train_324", "VACUUM_CONDENSER_SPECS"],
              seed={"math": math, "vacuum_condenser": module})
    ns["module"] = module
    return ns


def _both(v1, tag, n_in):
    sp, o = vc.design_specs()[tag], v1["VACUUM_CONDENSER_SPECS"][tag]
    mine = vc.solve(sp, sp.p_des, n_in, sp.t_in_des, sp.cw_flow_kgh, sp.cw_in_c)
    theirs = v1["module"].solve(o, o["p_des"], n_in, o["t_in_des"], o["cw_flow_kgh"],
                                o["cw_in_c"])
    return (v1["module"].vent_kgh(o, theirs), theirs), (vc.vent_kgh(sp, mine), mine)


@pytest.mark.parametrize("tag", TAGS)
def test_both_laws_vent_the_pfds_rows_at_design(v1, tag):
    """At its design inlet each condenser vents its PFD row on either law — the departure is a
    literal zero there, the ratio a literal one."""
    sp = vc.design_specs()[tag]
    (theirs, _), (mine, _) = _both(v1, tag, sp.n_in_des)
    assert theirs == mine == sp.vent_kgh


def test_324e007_without_its_co2_decided_divergence(v1):
    """324E007's inlet with a tenth of its CO2 — 0.027 kmol/h against the design's 0.254, as two
    minutes into a 323P003 trip. V1's ratio lifts the ammonia's partial pressure until the vent
    holds everything: 210.64 of the 210.82 kg/h arriving go to atmosphere, nothing condenses, the
    cold end sits at the water's 30 C. On the departure the port vents 24.55 kg/h and condenses
    186.25, its cold end at 54.76 C.

    Inlet CO2 a per cent either side of the design (handoff B-71): V1 vents 30.76 and 31.25 kg/h;
    the port 30.74 and 31.27 — its CO2 on V1's ratio, its ammonia on the departure. B-67's
    addition on the CO2 too gave 23.81 and 37.51."""
    sp = vc.design_specs()["324E007"]
    n = dict(sp.n_in_des)
    n["CO2"] *= 0.106
    (theirs, t), (mine, m) = _both(v1, "324E007", n)
    assert n["CO2"] == pytest.approx(0.027, abs=1e-3)
    assert (theirs, t["condensate_model_kgh"], t["t_vent_c"]) == (
        pytest.approx(210.641, abs=1e-3), 0.0, pytest.approx(30.0, abs=2e-6))
    assert (mine, m.condensate_model_kgh, m.t_vent_c) == (
        pytest.approx(24.547, abs=1e-3), pytest.approx(186.253, abs=1e-3),
        pytest.approx(54.759, abs=1e-3))
    for f, v1_vent, port_vent in ((0.99, 30.757, 30.741), (1.01, 31.252, 31.267)):
        n = dict(sp.n_in_des)
        n["CO2"] *= f
        (theirs, _), (mine, _) = _both(v1, "324E007", n)
        assert (theirs, mine) == (pytest.approx(v1_vent, abs=1e-3),
                                  pytest.approx(port_vent, abs=1e-3))


def test_the_trip_through_the_train_decided_divergence(v1):
    """323P003 stops; two minutes later the stages send the train 106 (105 before decision 178) and 1277 (1290 before
    decision 224's melt header, 1288 before decision 178) kg/h of vapour at
    0.306 and 0.084 bar a. On the same inputs V1's executed train has 324E007's cold end at 32.0 (32.1 before
    decision 224, 32.0 before decision 178) C,
    near the water's 30, and 136.4 (135.6 before decision 224, 137 before decision 178) kg/h to atmosphere where
    the PFD has 31; the port's keeps 324E007
    condensing at 54.0 C and sends 29.1 kg/h (the chests on their vendor trims, decided
    2026-10-14, and LV-324501A on its, decision 150; 1296 kg/h, 135.9 and 32.1 C on V1's linear
    valves; 1294 kg/h, 135.0 and 32.15 C, the port's 29.05 kg/h, on the Neldisc chord before decision
    170, which feeds both trains the second stage's vapour of PV-329212 on the S-Disc table). Before
    decisions 236 and 237 (LV-324501A's positioner and its sheet inlet) the second stage sent
    1277.205 kg/h and V1's train vented 136.416. With the separators' ejectors on the plant's
    bracket (decision 251) the stages sent 94.8 and 1279.0 kg/h, and V1's train vented 136.6 at
    32.0 C. On the deduced break curves (decision 322) 324F002 holds stage 1 at 0.317 bar a on its
    ratio as the load goes, where its load line would have taken it to 0.306, so the held melt boils
    less, and 324F004 holds stage 2 on its ratio (0.1 bar a at the design motive) as the load goes, so
    its held melt boils less too: the stages send 6.3 and 1062.7 kg/h, V1's train vents 35.9 at 51.3
    C, and the port's sends 28.0 at 53.6 C."""
    r1, r2, tr = _plant(1201, cut_at=5)[1200]
    mot = (tr.streams_kgh["924"], tr.streams_kgh["927"], tr.streams_kgh["929"])
    args = (MEVAP_DES_KGH, r1.m_vap_kgh + r1.m_boil_kgh, r2.m_vap_kgh + r2.m_boil_kgh,
            r1.false_air_kgh, r2.false_air_kgh)
    assert (args[1], args[2]) == (pytest.approx(6.263, abs=1e-3),
                                  pytest.approx(1062.750, abs=1e-3))
    theirs = v1["vacuum_train_324"](*args, *mot, cw_factors={}, p_e002_bara=r1.p_bara,
                                    p_e005_bara=r2.p_bara, sub_703=None)
    mine = vt.vacuum_train(*args, vt.MotiveSteam(*mot), p_324e002_bara=r1.p_bara,
                           p_324e005_bara=r2.p_bara)
    assert (theirs["streams_kgh"]["722"], theirs["nodes"]["324E007"]["t_vent_c"]) == (
        pytest.approx(35.914, abs=1e-3), pytest.approx(51.310, abs=1e-3))
    assert (mine.streams_kgh["722"], mine.nodes["324E007"].t_vent_c) == (
        pytest.approx(27.978, abs=1e-3), pytest.approx(53.645, abs=1e-3))


@pytest.mark.parametrize("k", ("NH3", "CO2"))
@pytest.mark.parametrize("f", (0.5, 0.9, 1.1, 1.5))
def test_the_ratio_where_the_design_back_pressure_is_above_b71(v1, k, f):
    """Handoff B-71, both ways. 324E005's NH3 and CO2 design back-pressures (3841 and 2496 Pa) sit
    above the PFD's partial pressures (3385 and 1780 Pa), so on any inlet the port's condenser is
    V1's to the bit; 324E002's (5468 and 836 Pa against 5910 and 1257) sit below, so the port's
    vent departs from V1's — half its inlet NH3, V1 1113.7 kg/h, the port 210.5."""
    for tag in ("324E005", "324E002"):
        sp = vc.design_specs()[tag]
        n = dict(sp.n_in_des)
        n[k] *= f
        (theirs, _), (mine, _) = _both(v1, tag, n)
        assert (theirs == mine) is (tag == "324E005")
    sp = vc.design_specs()["324E002"]
    n = dict(sp.n_in_des)
    n["NH3"] *= 0.5
    (theirs, _), (mine, _) = _both(v1, "324E002", n)
    assert (theirs, mine) == (pytest.approx(1113.744, abs=1e-3), pytest.approx(210.453, abs=1e-3))


def test_a_vent_is_never_negative_decided_divergence(v1):
    """B-87. 324E005's inlet on the tick Phase 7's cold start reached 99 C in 324F003 (8 876 s):
    709 at 1.352e6 kg/h, 405 times its row, with 0.084 kg/h of false air. The row's N2 is below
    the false air's share of it, so the scaled inlet books 1.889 kmol/h of N2 below zero and the
    inerts' sum is negative. At 0.02 bar a V1 vents -2.176e10 kg/h — the same amount booked as
    condensate — its cold end at the vapour's inlet; the port floors the N2 and vents 1.322e6 kg/h
    of what arrived, its cold end at 133.13 C. 324E005 is V1's on every inlet otherwise (B-71)."""
    n = inlet_kmolh("324E005", 1.352e6, 0.08401, F003_FA_DES_KGH)
    assert n["N2"] == pytest.approx(-1.8891, abs=1e-4)
    sp, o = vc.design_specs()["324E005"], v1["VACUUM_CONDENSER_SPECS"]["324E005"]
    mine = vc.solve(sp, 0.02, n, sp.t_in_des, sp.cw_flow_kgh, sp.cw_in_c)
    theirs = v1["module"].solve(o, 0.02, n, o["t_in_des"], o["cw_flow_kgh"], o["cw_in_c"])
    assert v1["module"].vent_kgh(o, theirs) == pytest.approx(-2.17594e10, rel=1e-5)
    assert vc.vent_kgh(sp, mine) == pytest.approx(1322366.44, abs=0.01)
    assert mine.t_vent_c == pytest.approx(133.1347, abs=1e-4)
    assert min(mine.vent_kmolh.values()) == 0.0 == mine.vent_kmolh["N2"]
