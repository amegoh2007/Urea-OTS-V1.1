"""V1 <-> V1.1 for 324E003 / 324F003's decided divergences, each asserted from both sides.

`test_second_evaporator_equivalence.py` compares the port with the transcription carrying every
departure on every tick. Here each departure runs both ways: V1's lines for it (the
transcription with that one switch off) against the port, and what each side does is measured.
Four were decided by the process engineer for unit 324 (324F004's pull off its design-anchored
map, handoff B-61; the held melt boiling, B-62; the melt on the PFD's refit and its ceiling, B-58,
all on 2026-10-01; the feed at the strength its leg drains, B-63, on 2026-10-02); five are classes
decided on other units and applied under §5 rule 7 (decisions 20, 10 and 21, 23, 33 and 11). B-67's and B-71's switch (the condensers'
vent on its additive departures where B-71 puts them, decided 2026-10-02) stays on throughout; it is run both ways
in `test_vacuum_condenser_decided_equivalence.py`. The melt header on AC4 PC35.2 (decision 224, B-137,
2026-11-14) is run against V1's selector on LV-324501's vendor trims.
"""

from __future__ import annotations

import pytest

from ureasim.data import unit_324 as d
from tests.equivalence import test_second_evaporator_equivalence as h
from tests.equivalence.v1_loader import v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

v1 = h.v1


def _both(v1, script, n, off, sp=None, setup=None, vendor_trim=False, seal_air=False,
          bisect=False, vendor_drain=False, ac4=False):
    """V1's transcription without the departure `off`, and the port, side by side; returns the
    tick each side's state was first not ``==`` the other's, and per tick (V1, port) records. The
    port runs V1's linear chest valve unless ``vendor_trim`` (PV-329212's own test), V1's sealed
    leg unless ``seal_air`` (B-107's own test), V1's last sweep unless ``bisect`` (B-108's) and
    V1's span law on LV-324501 unless ``vendor_drain`` (decision 150's), and V1's selector unless
    ``ac4`` (AC4's computed header, decision 224's)."""
    dec = h.ALL - {off}
    s = h._v1_state(v1, dec)
    chest = h.se.PV_329212_CHEST if vendor_trim else h.se.V1_CHEST
    unit, loops = (h.se.SecondEvaporator(chest=chest, backward_species=False, seal_air=seal_air,
                                         bisect_fixed_point=bisect, vendor_drain=vendor_drain,
                                         ac4_header=ac4),
                   h.se.SecondEvaporatorLoops(pic=h.se.pic_329212(chest),
                                              level=h.se.lic_324501(vendor=vendor_drain,
                                                                  ac4=ac4)))
    if setup:
        setup(s, loops)
    parted, hist = None, []
    for k in range(n):
        if sp and k == 5:
            for key, val in sp.items():
                getattr(s, key)["sp"] = val
                {"TIC_324002": loops.tic, "PIC_324203": loops.vacuum}[key].sp = val
        x = script(k)
        s.steam.P_9 = x["p9"]
        m_pre = s.r324_f003_M
        a = h._v1_stage2(v1, s, x["m"], x["w_live"], x["t1"], x["w1"], x["hic"], x["pd"],
                         x["tv"], x["p335"], h.DT, dec)
        b = h.port_step(unit, loops, x)
        made = max(1.0 - (m_pre + (a["feed"][0] - a["melt"][2] - a["melt"][3] - a["out"][7])
                          / 3600.0 * h.DT), 0.0)
        if parted is None and (s.r324_e003_T, s.r324_f003_P, s.r324_f003_M) != (
                unit.t_c, unit.p_bara, unit.m_kg):
            parted = k
        hist.append({"T": (s.r324_e003_T, unit.t_c), "P": (s.r324_f003_P, unit.p_bara),
                     "M": (s.r324_f003_M, unit.m_kg), "w": (a["out"][1], b.w_melt),
                     "fa": (a["ctl"][5], b.false_air_kgh),
                     "op": (s.PIC_324203["op"], loops.vacuum.op),
                     "chest": (s.r324_e003_chest_P, unit.chest_p_bara),
                     "leg": (a["out"][7], b.m_402_kgh), "made": made,
                     "boil": (a["melt"][3], b.m_boil_kgh),
                     "urea": (s.w_e003["Urea"], unit.w["Urea"]),
                     "air": b.seal_air_kgh, "level": b.level_pct,
                     "lv": ((a["out"][5], a["out"][6]), (b.lv_a_pct, b.lv_b_pct)),
                     "recycle": (a["out"][7] if a["out"][4] else 0.0, b.route.recycle_kgh)})
    return parted, hist


@pytest.mark.parametrize("name, over, p, fa", [
    ("motive halved", {"hic": 25.0}, (0.13432, 0.13071), (20.162, 21.075)),
    ("324E006 at 0.5 bar a", {"pd": 0.5}, (0.13100, 0.13133), (21.000, 20.916)),
])
def test_the_pull_off_the_design_anchored_map_decided_divergence(v1, name, over, p, fa):
    """B-61, decided 2026-10-01. At design both pull PFD 712's 584 kg/h at 0.131 bar a. Halve
    HIC-329606: V1 halves its pull and the vacuum rises to 0.1343 bar a after ten minutes,
    PIC-324203 throttling the bleed to 20.2 kg/h; the map, still critical, pulls a little more and
    the vacuum deepens to 0.1307. Back 324E006 up to 0.5 bar a: V1 does not notice; the ejector,
    critical only to 0.369 bar a, passes its break and the vacuum rises to 0.1313."""
    _, hist = _both(v1, h._step(v1, 5, **over), 6000, "B-61")
    r = hist[5999]
    assert r["P"] == (pytest.approx(p[0], abs=1e-5), pytest.approx(p[1], abs=1e-5))
    assert r["fa"] == (pytest.approx(fa[0], abs=1e-3), pytest.approx(fa[1], abs=1e-3))


def test_the_held_melt_boils_decided_divergence(v1):
    """B-62, decided 2026-10-01. Stage 1's leg stops. V1 boils the feed's water only, so nothing
    boils and the held melt superheats: 147.8 C after 30 s, still 97.70 % urea. The port's holdup
    boils — 1316 kg/h at once, 879 at 30 s — and holds at its boiling point, 145.6 C at 97.94 %,
    climbing as it concentrates, until at the 9-bar chest's saturation, 174.9 C, its equilibrium
    at the vacuum is 98.64 % and it stops. V1's held melt ends at 175.1 C and 97.70 %."""
    _, hist = _both(v1, h._step(v1, 5, m=0.0), 3001, "B-62")
    assert hist[5]["boil"] == (0.0, pytest.approx(1316.31, abs=0.01))
    assert hist[300]["T"] == (pytest.approx(147.7593, abs=1e-4),
                              pytest.approx(145.5662, abs=1e-4))
    assert hist[300]["boil"] == (0.0, pytest.approx(879.32, abs=0.01))
    assert hist[300]["urea"] == (pytest.approx(0.97701, abs=1e-5),
                                 pytest.approx(0.97935, abs=1e-5))
    assert hist[3000]["T"] == (pytest.approx(175.1070, abs=1e-4),
                               pytest.approx(174.9192, abs=1e-4))
    assert hist[3000]["urea"] == (pytest.approx(0.97701, abs=1e-5),
                                  pytest.approx(0.98638, abs=1e-5))


def test_the_feed_at_the_strength_its_leg_drains_decided_divergence(v1):
    """B-63, decided 2026-10-02. The leg drains stage 1's design melt at the design rate while
    stage 1 makes none — a 323P003 trip as stage 2 sees it, where V1's ``w1_live`` is 0. V1 takes
    the 75.9 t/h as urea-free and boils all of it: the melt falls to 114.3 C in 5 s, -9.3 C in
    30 s and -103.5 C in a minute. The port takes the leg's 94.31 % and holds the design: the melt
    to the bit, PT-324203 to 1e-14 (324E005's condenser falsi)."""
    _, hist = _both(v1, h._step(v1, 5, w_live=0.0), 601, "B-63")
    assert hist[4]["T"] == (140.0, 140.0)
    assert hist[50]["T"] == (pytest.approx(114.3459, abs=1e-4), 140.0)
    assert hist[300]["T"] == (pytest.approx(-9.2860, abs=1e-4), 140.0)
    assert hist[600]["T"] == (pytest.approx(-103.4622, abs=1e-4), 140.0)
    assert hist[600]["P"][1] == pytest.approx(0.131, abs=1e-14)


def test_the_melt_on_the_refit_decided_divergence(v1):
    """B-58. The 9-bar header 10 % down from 0.5 s: after five minutes V1's melt (the published
    parameter) is at 97.64 % and 139.00 C, the port's (the refit) at 97.66 % and 138.92 C."""
    _, hist = _both(v1, h._step(v1, 5, p9=8.1), 3001, "B-58")
    assert hist[3000]["w"] == (pytest.approx(0.976394, abs=1e-6),
                               pytest.approx(0.976604, abs=1e-6))
    assert hist[3000]["T"] == (pytest.approx(138.9980, abs=1e-4),
                               pytest.approx(138.9208, abs=1e-4))


def test_the_chest_on_its_datasheet_decided_divergence(v1):
    """Decision 20. V1's chest sits at 8.1 bar a, 90 % of the 9-bar header; the port's at the
    DDS's 5.9, its conductance 116.1 kW/K where V1's is 68.2. Both hold the design; with the
    header 10 % down V1's chest falls to 7.44 bar a and its melt to 138.31 C after ten minutes,
    the port's to 5.76 and 139.29 C — a full kelvin warmer, its chest further from the header."""
    _, hist = _both(v1, h._step(v1, 5, p9=8.1), 6000, "chest")
    assert hist[0]["chest"] == (8.1, 5.9)
    assert hist[5999]["chest"] == (pytest.approx(7.44213, abs=1e-5),
                                   pytest.approx(5.76165, abs=1e-5))
    assert hist[5999]["T"] == (pytest.approx(138.3109, abs=1e-4),
                               pytest.approx(139.2893, abs=1e-4))


def test_the_master_on_span_decided_divergence(v1):
    """Decisions 10 and 21. TIC-324002 to 142 C. V1 reads the table's 2.00 as bar per kelvin and
    takes the melt to 141.89 C in ten minutes; on its span (2.00 x 16 bar / 160 K) the master
    moves the chest ten times more gently and the melt is at 140.72 C."""
    _, hist = _both(v1, h._step(v1, 5), 6000, "gains", sp={"TIC_324002": 142.0})
    assert hist[5999]["T"] == (pytest.approx(141.8868, abs=1e-4),
                               pytest.approx(140.7161, abs=1e-4))


def test_the_vacuum_on_span_decided_divergence(v1):
    """Decision 10. PIC-324203 to 0.12 bar a. V1's 2.0 %/bar barely moves PV-324203 (20.96 kg/h
    of air after ten minutes, PT-324203 0.13099); on PT-324203's 2 bar span, 100 %/bar, the port
    has cut the air to 19.07 kg/h and the vacuum is at 0.13067 bar a and still falling."""
    _, hist = _both(v1, h._step(v1, 5), 6000, "gains", sp={"PIC_324203": 0.12})
    assert hist[5999]["P"] == (pytest.approx(0.130993, abs=1e-6),
                               pytest.approx(0.130672, abs=1e-6))
    assert hist[5999]["fa"] == (pytest.approx(20.958, abs=1e-3),
                                pytest.approx(19.072, abs=1e-3))


def test_pv_324203_on_its_vendor_trim_decided_divergence(v1):
    """Decision 23. PIC-324203 to 0.12 bar a on span both sides. V1 strokes PV-324203 linear from
    50 % and has shut it to 46.8 % after ten minutes (19.64 kg/h); the port the modified
    equal-percentage trim from 92.03 % — its design flow near the top of a trim sized for 23 kg/h —
    and is at 88.8 % (19.07 kg/h), the vacuum 0.0001 bar deeper."""
    _, hist = _both(v1, h._step(v1, 5), 6000, "valve", sp={"PIC_324203": 0.12})
    assert hist[5999]["op"] == (pytest.approx(46.761, abs=1e-3), pytest.approx(88.811, abs=1e-3))
    assert hist[5999]["fa"] == (pytest.approx(19.640, abs=1e-3), pytest.approx(19.072, abs=1e-3))
    assert hist[5999]["P"] == (pytest.approx(0.130769, abs=1e-6),
                               pytest.approx(0.130672, abs=1e-6))


def test_the_separator_with_its_heads_decided_divergence(v1):
    """Decision 33. 324F003 on the drawing's 10.7 m3 (7.59 m3 of vapour at design) where V1 takes
    the 7.43 m3 cylinder (4.32). HIC-329606 halved: the vacuum node is quick either way — 0.5 s
    later V1's has moved 0.182 mbar, the port's 0.138 — and both settle at 0.13070 bar a within
    1.5 s."""
    _, hist = _both(v1, h._step(v1, 5, hic=25.0), 1200, "volume")
    assert hist[5]["P"] == (pytest.approx(0.1308178, abs=1e-7),
                            pytest.approx(0.1308624, abs=1e-7))
    assert hist[1199]["P"] == (pytest.approx(0.1306998, abs=1e-7),
                               pytest.approx(0.1306998, abs=1e-7))


def test_the_drain_above_its_heel_decided_divergence(v1):
    """Decision 11's class. Stage 1's leg stops with LIC-324501 in MAN at 100 %: both drain 324F003
    down LV-324501 identically until the 1 kg floor, at 134.6 s. There V1's drain still passes
    101 t/h, which the floor restores every tick — 4651 kg of melt made from nothing in the next
    165 s; the port's drains nothing below the floor."""
    def setup(s, loops):
        s.LIC_324501["mode"], s.LIC_324501["op"] = "MAN", 100.0
        loops.level.mode, loops.level.op = "MAN", 100.0
    parted, hist = _both(v1, h._step(v1, 5, m=0.0), 3000, "heel", setup=setup)
    assert parted == 1347
    assert hist[2999]["M"] == (1.0, 1.0)
    assert hist[2999]["leg"] == (pytest.approx(d.LV_324501_SPAN_KGH, rel=1e-12), 0.0)
    assert sum(r["made"] for r in hist) == pytest.approx(4651.013, abs=1e-3)


def test_lv_324501_on_flowserves_sheets_decided_divergence(v1):
    """Decision 150: LV-324501A on Flowserve's equal percentage from 75.35 %, where V1's span law
    runs the drain linear from 75 %. Both drain the design melt to the bit on the seed tick; stage
    1's feed cut a fifth from 0.5 s, they part on the tick LIC-324501 first moves. Five minutes on,
    V1's drain passes 60.7 t/h and its separator holds 3189 kg; the port's trim, its gain lower at
    the design stroke, passes 57.7 t/h and holds 3571 kg."""
    parted, hist = _both(v1, h._step(v1, 5, m=0.8 * d.P1_DES_KGH), 3001, None, vendor_drain=True)
    assert hist[0]["leg"] == (d.P2_DES_KGH, pytest.approx(d.P2_DES_KGH, rel=1e-12))
    assert parted == 6
    assert hist[3000]["leg"] == (pytest.approx(60742.6, abs=0.1), pytest.approx(57669.0, abs=0.1))
    assert hist[3000]["M"] == (pytest.approx(3189.09, abs=0.01), pytest.approx(3570.75, abs=0.01))


def test_the_melt_header_on_ac4_decided_divergence(v1):
    """Decision 224, decided 2026-11-14 (handoff B-137): LIC-324501's output sets PIC-335201's set
    point, E1 = 2.8 + X / 50 bar g, PIC-335201 strokes LV-324501A on the computed header and, above
    X = 50, LV-324501B opens beside it, where V1's selector strokes one valve on LIC-324501's demand.
    Both on LV-324501's vendor trims (decision 150): the design drain on the first tick on both, and
    with stage 1's feed cut a fifth from 0.5 s they part on tick 6; five minutes on V1's drain passes
    60.7 t/h on LV-324501A at 60.0 % and holds 3189 kg, AC4's 71.7 t/h at 75.6 % and 2654 kg, the
    header following E1 down, neither recycling. AC4's side before decisions 236 and 237 (the
    positioner lag and the sheet's inlet): 71 673.1 kg/h at 72.287 % and 2 656.69 kg."""
    parted, hist = _both(v1, h._step(v1, 5, m=0.8 * d.P1_DES_KGH), 3001, None, vendor_drain=True,
                         ac4=True)
    assert hist[0]["leg"] == (d.P2_DES_KGH, d.P2_DES_KGH) and parted == 6
    assert hist[3000]["leg"] == (pytest.approx(60742.6, abs=0.1), pytest.approx(71725.7, abs=0.1))
    assert hist[3000]["M"] == (pytest.approx(3189.09, abs=0.01), pytest.approx(2653.95, abs=0.01))
    assert hist[3000]["lv"] == ((pytest.approx(59.992, abs=1e-3), 0.0),
                                (pytest.approx(75.563, abs=1e-3), 0.0))
    assert all(r["recycle"] == (0.0, 0.0) for r in hist)


def test_one_header_valve_fewer_on_ac4_decided_divergence(v1):
    """Decision 224: at the design feed with one of the granulator's ten header valves taken off,
    V1 has no header valve to take and its selector holds the design drain forward on LV-324501A
    alone; on AC4 the header rises, LIC-324501 lifts E1 to its 3.8 bar g ceiling and LV-324501B
    opens beside LV-324501A. They part on tick 5; fifteen minutes on V1 still drains the design's
    75.9 t/h, all forward, while AC4's LV-324501B stands at 15.6 % returning 9.3 t/h of the 80.5 t/h
    drain as the level, lifted 96 kg, comes back down (LV-324501B's widest 17.0 %). AC4's side
    before decisions 236 and 237: 80 458.6 kg/h, 3 893.12 kg, PIC-335201's output 75.163 % and
    LV-324501B 15.545 %, 9 241.4 kg/h returned, LV-324501B's widest 16.932 %."""
    parted, hist = _both(v1, h._step(v1, 5, headers=9), 9001, None, vendor_drain=True, ac4=True)
    assert parted == 5 and all(r["recycle"][0] == 0.0 and r["lv"][0][1] == 0.0 for r in hist)
    assert hist[9000]["leg"] == (d.P2_DES_KGH, pytest.approx(80477.6, abs=0.1))
    assert hist[9000]["M"] == (pytest.approx(d.F003_M_DES_KG, rel=1e-12),
                               pytest.approx(3892.46, abs=0.01))
    assert hist[9000]["lv"][1] == (pytest.approx(79.450, abs=1e-3), pytest.approx(15.594, abs=1e-3))
    assert hist[9000]["recycle"][1] == pytest.approx(9259.0, abs=0.1)
    assert max(r["lv"][1][1] for r in hist) == pytest.approx(17.006, abs=1e-3)


def test_335p001s_low_level_stop_on_ac4_decided_divergence(v1):
    """Decision 217 on AC4's header (decision 224). Stage 1's leg stops at 0.5 s. V1's selector
    throttles LV-324501 on LIC-324501's demand as the level falls and has no stop: five minutes on
    it still drains 352 kg/h and holds 775 kg. On AC4 the header draws what the granulator takes
    until LY-324501 first reads below its 5 % stand-in L2, at 169.3 s, 69.5 t/h going forward the
    tick before; there 335P001A and B stop, and the separator holds 345.6 kg, its seal covered."""
    parted, hist = _both(v1, h._step(v1, 5, m=0.0), 3000, "heel", vendor_drain=True, ac4=True)
    stop = next(k for k, r in enumerate(hist) if r["level"] < 5.0)
    assert parted == 6 and stop == 1693
    assert hist[stop - 1]["leg"][1] == pytest.approx(69498.8, abs=0.1)
    assert all(r["leg"][1] == 0.0 and r["air"] == 0.0 for r in hist[stop:])
    assert hist[2999]["M"] == (pytest.approx(774.60, abs=0.01), pytest.approx(345.553, abs=1e-3))
    assert hist[2999]["leg"][0] == pytest.approx(351.63, abs=0.01)


def test_pv_329212_on_its_vendor_trim_decided_divergence(v1):
    """Decision 23's class, decided 2026-10-14: PV-329212 on Metso's DN 80 balanced Neldisc, its
    printed capacities as its curve (and, since decision 170, 2026-11-06, Valmet's S-Disc shape between
    them: the vendor-trim numbers below are the chord's and are to be re-measured when `E:` is back),
    from its 54.68 % design stroke and the normal case's xT 0.57,
    where V1 runs the chest valve linear from 65.56 %. Both hold the design to the bit; with the
    9-bar header 10 % down from 0.5 s the two part on tick 5, and after five minutes the chest
    stands at 5.6360 bar a on V1's valve and 5.7394 (5.7619 before decision 170) on the vendor's, the melt at 138.921 and
    139.390 C."""
    parted, hist = _both(v1, h._step(v1, 5, p9=8.1), 3001, "PV-329212", vendor_trim=True)
    assert parted == 5
    assert hist[3000]["chest"] == (pytest.approx(5.636, abs=1e-4), pytest.approx(5.7394, abs=1e-4))
    assert hist[3000]["T"] == (pytest.approx(138.9208, abs=1e-4), pytest.approx(139.3046, abs=1e-4))


def test_the_lost_seal_admits_air_decided_divergence(v1):
    """B-107, decided 2026-10-22: once LT-324501 uncovers its barometric seal, atmospheric air enters
    324F003 through the drain's trim on the blow-through law, where V1's empty leg admits nothing.
    LIC-324501's set point 54.7 -> 10 % (S1-5.4b): the loop drains the leg past its set point on both
    sides alike until LI-324501 crosses the seal's 3 % at 686.6 s. V1's vacuum stays at 0.131 bar a.
    The port's leg admits up to 625 kg/h, PT-324203 peaks at 0.2416 bar a at 838 s with the level at
    0.47 %, PIC-324203 throttling its bleed to 12.7 kg/h, and the melt weakens to 96.71 % urea; the
    level recovers, the seal closes at 1 053.5 s, and after 25 minutes the vacuum stands at
    0.1299 bar a and the melt at 139.03 C against V1's 140."""
    def setup(s, loops):
        s.LIC_324501["sp"] = loops.level.sp = 10.0
    parted, hist = _both(v1, h._step(v1, 5), 15000, None, setup=setup, seal_air=True)
    assert parted == 6866 and hist[6865]["air"] == 0.0 < hist[6866]["air"]
    assert hist[6865]["level"] > 3.0 > hist[6866]["level"]
    peak = max(range(15000), key=lambda k: hist[k]["P"][1])
    assert peak == 8381
    assert hist[peak]["P"] == (pytest.approx(0.131, abs=1e-12), pytest.approx(0.24164, abs=1e-5))
    assert hist[peak]["fa"][1] == pytest.approx(12.713, abs=1e-3)
    assert max(r["air"] for r in hist) == pytest.approx(625.46, abs=0.01)
    assert (max(r["w"][0] for r in hist), min(r["w"][1] for r in hist)) == (
        pytest.approx(0.9771, abs=1e-12), pytest.approx(0.96710, abs=1e-5))
    assert next(k for k in range(peak, 15000) if hist[k]["air"] == 0.0) == 10535
    end = hist[14999]
    assert end["P"] == (pytest.approx(0.131, abs=1e-12), pytest.approx(0.12987, abs=1e-5))
    assert end["T"] == (pytest.approx(140.0, abs=1e-9), pytest.approx(139.027, abs=1e-3))


def test_the_fixed_point_on_the_energy_balance_at_the_heel_decided_divergence():
    """B-108, decided 2026-10-22. LIC-324501 in MAN at 100 % drains 324F003 with B-107's lost seal
    admitting air; V1's own sealed leg never meets this, so its side is the port with V1's last
    sweep. Both stay ``==`` until the sweeps first miss their 1e-12, at 537.1 s; the drain reaches
    the 1 kg floor at 540.4 s and the vacuum breaks to 0.29 bar a. V1's sweeps then swing — the
    residual up to 158 K, TT-324002 between 43.1 and 146.5 C, 78.16 C after 15 minutes — and the
    stage passes stage 1's melt at 94.31 %. Solved on the energy balance, the heel holds 147.2 to
    143.3 C under TIC-324002, the melt 96.44 to 95.95 % and the vacuum 0.304 bar a, every
    unconverged tick bracketed to 1e-12."""
    sides = []
    for bisect in (False, True):
        unit = h.se.SecondEvaporator(chest=h.se.V1_CHEST, backward_species=False, seal_air=True,
                                     bisect_fixed_point=bisect, vendor_drain=False,
                                     ac4_header=False)
        loops = h.se.SecondEvaporatorLoops(pic=h.se.pic_329212(h.se.V1_CHEST),
                                           level=h.se.lic_324501(vendor=False))
        loops.level.mode, loops.level.op = "MAN", 100.0
        sides.append((unit, loops))
    hist, parted = [], None
    for k in range(9000):
        x = h._design(None)
        hist.append([h.port_step(unit, loops, x) for unit, loops in sides])
        if parted is None and (sides[0][0].t_c, sides[0][0].p_bara, sides[0][0].m_kg) != (
                sides[1][0].t_c, sides[1][0].p_bara, sides[1][0].m_kg):
            parted = k
    assert parted == 5371 == next(k for k in range(9000) if not hist[k][0].converged)
    floor = next(k for k in range(9000) if hist[k][1].m_kg == d.F003_M_FLOOR_KG)
    assert floor == 5404
    heel = [hist[k] for k in range(floor, 9000)]
    assert max(r[0].residual for r in heel) == pytest.approx(158.20, abs=0.01)
    assert (min(r[0].t_c for r in heel), max(r[0].t_c for r in heel)) == (
        pytest.approx(43.10, abs=0.01), pytest.approx(146.52, abs=0.01))
    assert min(r[0].w_melt for r in heel) == pytest.approx(0.9431, abs=1e-12)
    assert all(r[1].bisected for r in hist if not r[1].converged)
    assert max(r[1].residual for r in hist) <= d.PT_LOOP_TOL
    assert (min(r[1].t_c for r in heel), max(r[1].t_c for r in heel)) == (
        pytest.approx(143.341, abs=1e-3), pytest.approx(147.188, abs=1e-3))
    assert (min(r[1].w_melt for r in heel), max(r[1].w_melt for r in heel)) == (
        pytest.approx(0.95954, abs=1e-5), pytest.approx(0.96439, abs=1e-5))
    end = hist[8999]
    assert (end[0].t_c, end[1].t_c) == (pytest.approx(78.159, abs=1e-3),
                                        pytest.approx(143.341, abs=1e-3))
    assert (end[0].p_bara, end[1].p_bara) == (pytest.approx(0.28706, abs=1e-5),
                                              pytest.approx(0.30377, abs=1e-5))
