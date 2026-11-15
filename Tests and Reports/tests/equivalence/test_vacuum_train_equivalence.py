"""V1 <-> V1.1 equivalence for unit 324's vacuum train — `ureasim.units.evaporation.vacuum_train`.

What is being proved
--------------------
V1's ``vacuum_train_324`` is a module-level function, so it is lifted out of ``main.py`` and
EXECUTED on V1's own ``vacuum_condenser`` module and condenser specs, as V1 runs it through
``core/vacuum.py`` ``VacuumTrain324.solve``: the live shells and the blow-through share passed, no
``tv_prev``, no cooling-water factors. The port runs on the same inputs; every stream, every field
of the four condensers' books and the mixing residual are compared with ``==``, over loads, false
air, motive steam, shell pressures, blow-through and cooling water.

The motive valves are V1's inline lines (``main.py`` 9765, 10039-10041), TRANSCRIBED below and
declared as such: HV-329605 linear from 50 % on ``R324_HV9605_SPAN``, HV-329606 linear from 50 % on
PFD 927 and 929. The port runs both on their Flowserve trims from the strokes that pass the PFD's
design motive (decision 23's class, §5 rule 7) — a decided divergence, asserted both ways.

V1's condenser module runs with handoff B-67's and B-71's switch (decided 2026-10-02): the NH3 and
CO2 vent on the PFD's partial pressures plus the condensate's back-pressure departure where the
design back-pressure is at most that partial pressure, V1's ``vent_moles`` transcribed with that
one change (`tests.equivalence.b67_switch`); B-67 both ways is
`test_vacuum_condenser_decided_equivalence.py`'s, through the 323P003 trip.
"""

from __future__ import annotations

import math

import pytest

from ureasim.data import unit_324 as d
from ureasim.data import unit_324_train as t
from ureasim.data.unit_323 import MEVAP_DES_KGH
from ureasim.units.evaporation import vacuum_train as vt
from tests.equivalence.b67_switch import switched_module
from tests.equivalence.v1_loader import lift, v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

FIELDS = ("tag", "inlet_kgh", "condensate_kgh", "vent_kgh", "q_kw", "lmtd_k", "ua_kw_k",
          "cw_flow_kgh", "cw_in_c", "cw_out_c", "hot_in_c", "hot_out_c", "t_vent_c", "p_bara",
          "vent_kmolh", "mass_residual_kgh", "energy_residual_kw")
TAGS = ("324E002", "324E005", "324E006", "324E007")


@pytest.fixture(scope="module")
def v1():
    return lift(["vacuum_train_324", "VACUUM_CONDENSERS", "R324_V1_DES", "R324_V2_DES",
                 "R323_MEVAP_DES", "R324_F001_FA_DES", "R324_F003_FA_DES",
                 "R324_F002_MOTIVE_DES", "R324_F004_MOTIVE_DES", "R324_F005_MOTIVE_DES",
                 "R324_HIC9605_DES_PCT", "R324_HV9605_SPAN", "R324_HIC9606_DES_PCT",
                 "R324_F001_P_BARA", "R324_F003_P_BARA"],
                seed={"math": math, "vacuum_condenser": switched_module()})


def v1_motive(v1, hic_605: float, hic_606: float) -> tuple:
    """V1 `main.py` 9765 and 10039-10041, TRANSCRIBED: (924, 927, 929) [kg/h]."""
    mot9605_m = hic_605 / 100.0 * v1["R324_HV9605_SPAN"]
    motive_ratio_606 = max(hic_606 / v1["R324_HIC9606_DES_PCT"], 0.0)
    return (mot9605_m, v1["R324_F004_MOTIVE_DES"] * motive_ratio_606,
            v1["R324_F005_MOTIVE_DES"] * motive_ratio_606)


def _inputs(**over) -> dict:
    x = {"m790": MEVAP_DES_KGH, "v1": d.V1_DES_KGH, "v2": d.V2_DES_KGH, "fa1": 21.0,
         "fa2": 21.0, "motive": (390.0, 1220.0, 180.0), "p002": d.F001_P_DES_BARA,
         "p005": d.F003_P_DES_BARA, "sub": None, "cw": {}}
    x.update(over)
    return x


def _compare(v1, x):
    theirs = v1["vacuum_train_324"](
        x["m790"], x["v1"], x["v2"], x["fa1"], x["fa2"], *x["motive"],
        cw_factors=x["cw"], p_e002_bara=x["p002"], p_e005_bara=x["p005"], sub_703=x["sub"])
    cw_flow = {tag: v1["VACUUM_CONDENSERS"][tag]["cw_flow_kgh"] * f for tag, f in x["cw"].items()}
    mine = vt.vacuum_train(x["m790"], x["v1"], x["v2"], x["fa1"], x["fa2"],
                           vt.MotiveSteam(*x["motive"]), x["p002"], x["p005"], x["sub"],
                           cw_flow)
    assert mine.streams_kgh == theirs["streams_kgh"]
    assert mine.mixing_residual_703_kgh == theirs["mixing_residual_703_kgh"]
    for tag in TAGS:
        for name in FIELDS:
            assert getattr(mine.nodes[tag], name) == theirs["nodes"][tag][name], (tag, name)
    s = theirs["streams_kgh"]
    assert mine.condensate_kgh == s["719"] + s["720"] + s["721"] + s["759"]
    return mine, theirs


def test_the_train_uses_v1s_design_basis(v1):
    """The rows V1 writes as literals in ``vacuum_train_324``, the departures' references and the
    motive anchors: ``==`` V1's."""
    assert (t.PFD_703_KGH, t.PFD_705_KGH, t.PFD_709_KGH, t.PFD_790_KGH) == (
        26840.0, 14799.0, 3342.0, 12040.0)
    assert (d.V1_DES_KGH, d.V2_DES_KGH, MEVAP_DES_KGH, d.F001_FA_DES_KGH, d.F003_FA_DES_KGH) == (
        v1["R324_V1_DES"], v1["R324_V2_DES"], v1["R323_MEVAP_DES"], v1["R324_F001_FA_DES"],
        v1["R324_F003_FA_DES"])
    assert (d.F002_MOTIVE_DES_KGH, d.F004_MOTIVE_DES_KGH, d.F005_MOTIVE_DES_KGH) == (
        v1["R324_F002_MOTIVE_DES"], v1["R324_F004_MOTIVE_DES"], v1["R324_F005_MOTIVE_DES"])
    assert (d.F001_P_DES_BARA, d.F003_P_DES_BARA) == (v1["R324_F001_P_BARA"],
                                                      v1["R324_F003_P_BARA"])


BLOW = (850.0, {"NH3": 0.55, "CO2": 0.30, "H2O": 0.15})


@pytest.mark.parametrize("name, over", [
    ("design", {}),
    ("stage 1 boils 10 % more, twice the false air", {"v1": 1.1 * d.V1_DES_KGH, "fa1": 42.0}),
    ("323F010's overhead 20 % down", {"m790": 0.8 * MEVAP_DES_KGH}),
    ("stage 2 boils 30 % less", {"v2": 0.7 * d.V2_DES_KGH, "fa2": 10.0}),
    ("motive halved", {"motive": (195.0, 610.0, 90.0)}),
    ("motive 20 % up", {"motive": (468.0, 1464.0, 216.0)}),
    ("motive shut", {"motive": (0.0, 0.0, 0.0)}),
    ("shells off their vacuums", {"p002": 0.36, "p005": 0.12}),
    ("LV-323505 blowing through", {"sub": BLOW}),
    ("324E006's water halved", {"cw": {"324E006": 0.5}}),
    ("everything at once", {"v1": 1.05 * d.V1_DES_KGH, "m790": 1.1 * MEVAP_DES_KGH,
                            "v2": 1.2 * d.V2_DES_KGH, "fa1": 30.0, "fa2": 15.0,
                            "motive": (420.0, 1100.0, 200.0), "p002": 0.35, "p005": 0.14,
                            "sub": BLOW, "cw": {"324E002": 0.9, "324E007": 1.5}}),
])
def test_the_train_is_v1s(v1, name, over):
    """Every stream, every condenser field and the mixing residual ``==`` V1's."""
    _compare(v1, _inputs(**over))


def test_the_design_is_the_pfd(v1):
    """At design both reproduce PFD-21's rows to 1e-8 kg/h (324E007's falsi's last bits reach 722
    and 759 at 2.5e-9); 703 - 705 - 790 is the PFD's own 1 kg/h of rounding (26840 - 14799 - 12040)."""
    mine, _ = _compare(v1, _inputs())
    pfd = {"703": 26840.0, "705": 14799.0, "706": 72.0, "708": 462.0, "709": 3342.0,
           "712": 584.0, "714": 1804.0, "715": 41.0, "717": 221.0, "719": 26768.0,
           "720": 2758.0, "721": 1763.0, "722": 31.0, "759": 190.0, "790": 12040.0,
           "924": 390.0, "927": 1220.0, "929": 180.0}
    assert mine.streams_kgh == pytest.approx(pfd, abs=1e-8)
    assert mine.mixing_residual_703_kgh == 1.0


#: The port's strokes [%]: the design strokes, and ten points below them.
DES = (t.HV_329605_OP_DES_PCT, t.HV_329606_OP_DES_PCT)
SHUT_10 = (DES[0] - 10.0, DES[1] - 10.0)


@pytest.mark.parametrize("hic, v1_kgh, strokes, port_kgh", [
    ((50.0, 50.0), (390.0, 1220.0, 180.0), DES, (390.0, 1220.0, 180.0)),
    ((40.0, 40.0), (312.0, 976.0, 144.0), SHUT_10, (342.01, 1065.97, 157.27)),
    ((100.0, 100.0), (780.0, 2440.0, 360.0), (100.0, 100.0), (460.43, 1396.39, 206.03)),
    ((0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0), (0.0, 0.0, 0.0)),
])
def test_the_motive_valves_on_their_vendor_trims_decided_divergence(v1, hic, v1_kgh, strokes,
                                                                    port_kgh):
    """Decision 23's class (§5 rule 7). V1 strokes HV-329605 and HV-329606 linear from 50 %; the
    port on Flowserve's modified equal-percentage trims (Pos. 66, 67) from 69.06 and 80.16 %,
    where they pass PFD 924's 390 and 927 + 929's 1400 kg/h, between the LP header and the
    nozzles they feed (handoff B-73, decided 2026-10-02): a choked nozzle's pressure rises with its
    flow and throttles the valve. Both deliver the PFD's motive at their design strokes. Ten points
    shut, V1 passes 80 % of it, the port 88 % and 87 % (on the trims alone 74 %). Wide open V1
    passes twice the design; the port 1.18 and 1.14 times, its nozzles near the header's
    5.013 bar a — on the trims alone HV-329605, sized for 429 kg/h at 72 %, would pass 2.53 times."""
    assert v1_motive(v1, *hic) == pytest.approx(v1_kgh, abs=1e-9)
    m = vt.motive_steam(*strokes)
    assert (m.m_924_kgh, m.m_927_kgh, m.m_929_kgh) == pytest.approx(port_kgh, abs=0.01)
    if strokes == DES:
        assert (m.m_924_kgh, m.m_927_kgh, m.m_929_kgh) == (390.0, 1220.0, 180.0)


@pytest.mark.parametrize("over, t_708", [
    ({}, 121.0),
    ({"motive": (195.0, 610.0, 90.0)}, 112.9171),
    ({"motive": (0.0, 0.0, 0.0)}, 63.0401),
    ({"p002": 0.36}, 121.7668),
])
def test_708s_temperature_decided_divergence(v1, over, t_708):
    """B-97, decided 2026-10-16: the port publishes 708's temperature, 324F002's adiabatic mix
    of 706 and 924 as its departure from the design mix; V1's train returns 708's mass alone —
    streams, nodes and the mixing residual — and its 323C005 charges 121 C. Both ways: every
    stream and condenser field ``==`` V1's, and the port's 708 at 121 C to the bit at design,
    112.92 C on half the motive, 63.04 C with it shut, 121.77 C with stage 1's shell at 0.36 bar a
    (706 brings 4.7 kg/h less cold vapour to cool the steam)."""
    mine, theirs = _compare(v1, _inputs(**over))
    assert set(theirs) == {"streams_kgh", "nodes", "mixing_residual_703_kgh"}
    if over:
        assert mine.t_708_c == pytest.approx(t_708, abs=1e-4)
    else:
        assert mine.t_708_c == t_708
