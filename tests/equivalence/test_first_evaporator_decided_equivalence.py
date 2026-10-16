"""V1 <-> V1.1 for 324E001 / 324F001's decided divergences, each asserted from both sides.

`test_first_evaporator_equivalence.py` compares the port with the transcription carrying every
departure on every tick. Here each departure runs both ways: V1's lines for it (the
transcription with that one switch off) against the port, and what each side does is measured.
Three were decided by the process engineer for this unit on 2026-10-01 (the melt on the PFD's
refit and its ceiling, handoff B-58; 324F002's pull off its design-anchored map, B-61; the held
melt boiling, B-62); five are classes decided on other units and applied under §5 rule 7
(decisions 20, 10 and 21, 23, 11, and handoff B-21's line). B-67's and B-71's switch (the
condensers' vent on its additive departures where B-71 puts them, decided 2026-10-02) stays on
throughout; it is run both ways
in `test_vacuum_condenser_decided_equivalence.py`.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_324 as d
from ureasim.data.design_point import R324_FEED_DES
from ureasim.data.unit_329 import P_LP_BARA
from tests.equivalence import test_first_evaporator_equivalence as h
from tests.equivalence.v1_loader import v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

v1 = h.v1


def _both(v1, script, n, off, sp=None, vendor_trim=False):
    """V1's transcription without the departure `off`, and the port, side by side; returns the
    tick each side's state was first not ``==`` the other's, and per tick (V1, port) records. The
    port runs V1's linear chest valve unless ``vendor_trim`` (PV-329203's own test)."""
    dec = h.ALL - {off}
    s = h._v1_state(v1, dec)
    chest = h.fe.PV_329203_CHEST if vendor_trim else h.fe.V1_CHEST
    unit = h.fe.FirstEvaporator(chest=chest, lv_329505=None)
    loops = h.fe.FirstEvaporatorLoops(pic=h.fe.pic_329203(chest),
                                      trap=h.fe.lic_329505(h.fe.V1_TRAP_OP_DES_PCT))
    parted, hist = None, []
    for k in range(n):
        if sp and k == 5:
            for key, val in sp.items():
                getattr(s, key)["sp"] = val
                {"TIC_324001": loops.tic, "PIC_324202": loops.vacuum}[key].sp = val
        x = script(k)
        s.steam.P_LP = x["p_lp"]
        m_pre = s.r324_f001_M
        a = h._v1_stage1(v1, s, x["m324"], x["t"], x["w"], x["f010"], x["sub"], x["motive"],
                         x["pd"], x["tv"], h.DT, dec)
        b = h.port_step(unit, loops, x)
        made = max(1.0 - (m_pre + (a["feed"][0] - a["melt"][2] - a["melt"][3] - a["out"][2])
                          / 3600.0 * h.DT), 0.0)
        if parted is None and (s.r324_e001_T, s.r324_f001_P, s.r324_f001_M) != (
                unit.t_c, unit.p_bara, unit.m_kg):
            parted = k
        hist.append({"T": (s.r324_e001_T, unit.t_c), "P": (s.r324_f001_P, unit.p_bara),
                     "M": (s.r324_f001_M, unit.m_kg), "w": (a["out"][1], b.w_melt),
                     "feed": (a["feed"][0], b.feed_kgh), "fa": (a["ctl"][4], b.false_air_kgh),
                     "chest": (s.r324_e001_chest_P, unit.chest_p_bara),
                     "leg": (a["out"][2], b.m_401_kgh), "made": made,
                     "boil": (a["melt"][3], b.m_boil_kgh), "vap": (a["melt"][2], b.m_vap_kgh),
                     "urea": (s.w_e001["Urea"], unit.w["Urea"]), "op": (s.PIC_324202["op"],
                                                                       loops.vacuum.op)})
    return parted, hist


def test_the_melt_on_the_refit_decided_divergence(v1):
    """B-58. The LP header 10 % down from 0.5 s: TIC-324001 holds the melt temperature on its
    chest, and the melt's strength follows the equilibrium. After five minutes V1's (the
    published parameter) has fallen to 93.88 %, the port's (the PFD's refit) to 93.99 %: V1's
    melt answers the same temperature half as hard again."""
    _, hist = _both(v1, h._step(v1, 5, p_lp=0.9 * P_LP_BARA), 3001, "B-58")
    assert hist[3000]["w"] == (pytest.approx(0.938848, abs=1e-6),
                               pytest.approx(0.939903, abs=1e-6))
    assert hist[3000]["T"] == (pytest.approx(128.3011, abs=1e-4),
                               pytest.approx(128.1984, abs=1e-4))


def test_the_chest_on_its_datasheet_decided_divergence(v1):
    """Decision 20. V1's chest sits at 3.96 bar a, 0.90 x a retired header; the port's at the
    DDS's 3.7, its conductance 969.7 kW/K where V1's is 785.6. Both hold the design; with the LP
    header 10 % down the port's chest holds the melt 0.29 K warmer after ten minutes."""
    _, hist = _both(v1, h._step(v1, 5, p_lp=0.9 * P_LP_BARA), 6000, "chest")
    assert hist[0]["chest"] == (3.96, 3.7)
    assert hist[5999]["T"] == (pytest.approx(128.5382, abs=1e-4),
                               pytest.approx(128.8321, abs=1e-4))


def test_the_master_on_span_decided_divergence(v1):
    """Decisions 10 and 21. TIC-324001 to 132 C. V1 reads the table's 1.50 as bar per kelvin and
    takes the melt to 131.78 C in ten minutes; on its span (1.50 x 6 bar / 160 K) the master
    moves the chest 27 times more gently and the melt is at 130.52 C."""
    _, hist = _both(v1, h._step(v1, 5), 6000, "gains", sp={"TIC_324001": 132.0})
    assert hist[5999]["T"] == (pytest.approx(131.7792, abs=1e-4),
                               pytest.approx(130.5241, abs=1e-4))


def test_the_vacuum_on_span_decided_divergence(v1):
    """Decision 10. PIC-324202 to 0.30 bar a. V1's 2.0 %/bar barely shuts PV-324202 (20.89 kg/h
    of air after ten minutes, PT-324202 0.3298); on PT-324202's 1 bar span, 200 %/bar, the port
    has cut the air to 15.07 kg/h and the vacuum is at 0.3153 bar a and still falling."""
    _, hist = _both(v1, h._step(v1, 5), 6000, "gains", sp={"PIC_324202": 0.30})
    assert hist[5999]["P"] == (pytest.approx(0.32976, abs=1e-5),
                               pytest.approx(0.31534, abs=1e-5))
    assert hist[5999]["fa"] == (pytest.approx(20.888, abs=1e-3),
                                pytest.approx(15.075, abs=1e-3))


def test_pv_324202_on_its_vendor_trim_decided_divergence(v1):
    """Decision 23. PIC-324202 to 0.30 bar a on span both sides. V1 strokes PV-324202 linear from
    50 %, the port the modified equal-percentage trim from 61.07 %: the same stroke admits less
    air, and after ten minutes the vacuum is 0.0024 bar deeper."""
    _, hist = _both(v1, h._step(v1, 5), 6000, "valve", sp={"PIC_324202": 0.30})
    assert hist[5999]["fa"] == (pytest.approx(15.806, abs=1e-3),
                                pytest.approx(15.075, abs=1e-3))
    assert hist[5999]["P"] == (pytest.approx(0.31772, abs=1e-5),
                               pytest.approx(0.31534, abs=1e-5))


def test_the_barometric_leg_above_its_heel_decided_divergence(v1):
    """Decision 11's class (B-29). 323P003 stops: both drain 324F001 down its leg identically
    until the 1 kg floor. There V1's leg still draws 1254 kg/h, which the floor restores every
    tick — 17.5 kg of melt made from nothing; the port's leg drains nothing below the floor."""
    parted, hist = _both(v1, h._step(v1, 5, m324=0.0), 4000, "heel")
    assert parted is None
    assert hist[3999]["M"] == (1.0, 1.0)
    assert hist[3999]["leg"] == (pytest.approx(1254.399, abs=1e-3), 0.0)
    assert sum(r["made"] for r in hist) == pytest.approx(17.496, abs=1e-3)


def test_the_inlet_line_delivers_the_live_flow_decided_divergence(v1):
    """Handoff B-21's class. 323P003 10 % down from 0.5 s. V1's line delivers its packet's mass,
    so the stage sees the old flow until the 40 m line turns over, about 100 s; the port's
    delivers the live flow at once and delays only the liquor's temperature and composition."""
    parted, hist = _both(v1, h._step(v1, 5, m324=0.9 * R324_FEED_DES), 1001, "line")
    assert parted == 5
    assert hist[50]["feed"] == (pytest.approx(R324_FEED_DES, rel=1e-12),
                                pytest.approx(0.9 * R324_FEED_DES, rel=1e-12))
    assert hist[1000]["feed"][0] == pytest.approx(0.9 * R324_FEED_DES, rel=1e-12)


@pytest.mark.parametrize("name, over, p, fa", [
    ("design", {}, (0.33, 0.33), (21.0, 21.0)),
    ("motive halved", {"motive": 195.0}, (0.38788, 0.31878), (6.333, 28.180)),
    ("323C005 at 1.9 bar a", {"pd": 1.9}, (0.33, 0.33908), (21.0, 16.929)),
])
def test_the_pull_off_the_design_anchored_map_decided_divergence(v1, name, over, p, fa):
    """B-61, decided 2026-10-01. At design both pull PFD 706's 72 kg/h at 0.33 bar a — V1's
    line by construction, 324F002's map on its design anchor — and PV-324202 sits at its
    61.07 %. Halve the motive: V1 halves its pull and the vacuum rises to 0.388 bar a after ten
    minutes, PIC-324202 shutting the bleed to 6.3 kg/h; the map, still critical, pulls a little
    more and the vacuum deepens to 0.319, the bleed opening to 28.2. Back 323C005 up to 1.9 bar a:
    V1 does not notice; the ejector passes its break (critical to 1.31 bar a) and the vacuum
    rises to 0.339 with the bleed throttled to 16.9."""
    _, hist = _both(v1, h._step(v1, 5, **over), 6000, "B-61")
    r = hist[5999]
    assert r["P"] == (pytest.approx(p[0], abs=1e-5), pytest.approx(p[1], abs=1e-5))
    assert r["fa"] == (pytest.approx(fa[0], abs=1e-3), pytest.approx(fa[1], abs=1e-3))
    if name == "design":
        assert r["op"] == (pytest.approx(d.PV_324202_OP_DES_PCT, abs=1e-4),
                           pytest.approx(d.PV_324202_OP_DES_PCT, abs=1e-4))


def test_the_held_melt_boils_decided_divergence(v1):
    """B-62, decided 2026-10-01. 323P003 stops. The chest's 10.5 MW, no longer spent on the
    feed, goes into the holdup. V1 boils the feed's water only, so nothing boils and the held
    melt superheats: 150.0 C after 30 s, still 94.30 % urea. The port's holdup boils — 11.2 t/h
    at once, 5.2 t/h at 30 s — and holds at its own boiling point, 142.6 C at 96.07 %, climbing
    as it concentrates; at the chest's saturation, 151.94 C, its equilibrium at the vacuum is
    97.07 %, and there it stops. Both drain to the heel; V1's heel is 94.30 %, the port's
    97.07 %."""
    _, hist = _both(v1, h._step(v1, 5, m324=0.0), 6000, "B-62")
    assert hist[5]["boil"] == (0.0, pytest.approx(11182.07, abs=0.01))
    assert hist[300]["T"] == (pytest.approx(150.0022, abs=1e-4),
                              pytest.approx(142.6417, abs=1e-4))
    assert hist[300]["boil"] == (0.0, pytest.approx(5174.88, abs=0.01))
    assert hist[300]["urea"] == (pytest.approx(0.94301, abs=1e-5),
                                 pytest.approx(0.96072, abs=1e-5))
    assert hist[5999]["M"] == (1.0, 1.0)
    assert hist[5999]["T"] == (pytest.approx(151.9360, abs=1e-4),
                               pytest.approx(151.9360, abs=1e-4))
    assert hist[5999]["urea"] == (pytest.approx(0.94301, abs=1e-5),
                                  pytest.approx(0.97073, abs=1e-5))


def test_pv_329203_on_its_vendor_trim_decided_divergence(v1):
    """Decision 23's class, decided 2026-10-14: PV-329203 on Metso's DN 250 Neldisc, its printed
    capacities as its curve, from its 39.31 % design stroke and the normal case's xT 0.52, where
    V1 runs the chest valve linear from 73.80 %. The seed's chest moves 3e-7 bar on the first
    tick on both, and the two trims answer that within 2e-8 bar until the LP header falls 10 % at
    0.5 s; after five minutes the chest stands at 3.4881 bar a on V1's valve and 3.6289 on the
    vendor's, the melt at 128.198 and 129.391 C — the Neldisc, low on its curve, holds the chest."""
    parted, hist = _both(v1, h._step(v1, 5, p_lp=0.9 * P_LP_BARA), 3001, "PV-329203",
                         vendor_trim=True)
    assert parted == 1
    assert abs(hist[4]['chest'][0] - hist[4]['chest'][1]) < 2e-8
    assert hist[3000]["chest"] == (pytest.approx(3.4881, abs=1e-4), pytest.approx(3.6289, abs=1e-4))
    assert hist[3000]["T"] == (pytest.approx(128.1984, abs=1e-4), pytest.approx(129.3905, abs=1e-4))
