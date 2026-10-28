"""V1 <-> V1.1 for the steam network's decided divergences, each asserted from both sides.

`test_steam_network_equivalence.py` proves the transcription ``==`` V1's executed ``step_steam``
with every switch off and ``==`` the port with every switch on. Here each departure runs both
ways: V1's lines for it (the transcription with that one switch off, each on its own design
basis) against the port, and what each side does is measured. Three were decided by the process
engineer for this unit on 2026-10-02 (the users live on their headers, B-68; the waters the drums
pay and no LP floor, B-70; and B-69, the LP header at 4.0 bar g, which is V1's and needs no
switch), and one more on the same day, the LP header downstream of 322D001A/B ("917"); the rest are classes decided on other units and applied under §5 rule 7 (decisions 47,
33 and 11, 23 and 31, 10 and 21, 26 / 27 / 39, 32) and §4's order of sources (the butterflies'
loop-summary cases).
"""

from __future__ import annotations

import pytest

from ureasim.thermo import water_steam as ws
from ureasim.units.steam.drums import D001
from ureasim.units.steam.steam_network import SteamNetwork, v1_butterflies
from tests.equivalence import test_steam_network_equivalence as h
from tests.equivalence.v1_loader import v1_available

pytestmark = pytest.mark.skipif(
    not v1_available(), reason="V1 source tree not present on this machine"
)

v1 = h.v1
DT = h.DT


def _snap(s, r) -> dict:
    """What each side's tick leaves: V1's pressures, strokes, levels and flows; the port's."""
    v1_side = {"P_MP": s.P_MP, "P_9": s.P_9, "P_LP": s.P_LP, "m_supply": s.m_supply * 3600.0,
               "m_flash9": s.m_flash9 * 3600.0, "m_ld": s.m_ld * 3600.0,
               "m_water": s.m_water * 3600.0, "m_vent_hp": s.m_vent_hp * 3600.0,
               "m_vent": s.m_vent * 3600.0, "m_963": s.m_963 * 3600.0,
               "m_turbine": s.m_turbine * 3600.0, "supply_pct": s.valve_supply_pct,
               "sp204": s.pic204_sp, "admit9_pct": s.valve_admit9_pct,
               "letdown_pct": s.valve_letdown_pct, "lvl502": s.lic502_lvl,
               "lvl503": s.lic503_lvl, "lvl504": s.lic504_lvl, "op502": s.lic502_op,
               "pv207b": s.pv207b_pct, "relief": dict(s.relief),
               "water_d005": s.mass_residual_d005_liquid * 3600.0,
               "lvl_d001": D001.level_pct(s.m_d001) if hasattr(s, "m_d001") else None}
    return {"v1": v1_side, "port": r}


def pair(v1, off, n_ticks, act=None, **over):
    """V1's lines for departure ``off`` (the transcription with that switch off, on its own
    design inputs) and the port, side by side, on the same disturbance."""
    dec = h.ALL - {off}
    script_v1 = h.scenario(v1, dec, n_ticks=n_ticks, **over)
    script_port = h.scenario(v1, h.ALL, n_ticks=n_ticks, **over)
    s = h._v1_state(v1, dec, script_v1[0][0])
    net = SteamNetwork(**v1_butterflies())
    hist = []
    for k in range(n_ticks):
        if act is not None:
            act(k, s, net)
        x1, trip = script_v1[k]
        x2, _ = script_port[k]
        if "B-68" in dec:
            s.m_users_lp = x1["users_lp"]
        h._v1_steam(v1, s, DT, x1, dec, trip)
        hist.append(_snap(s, net.step(h.port_draws(x2), DT, trip)))
    return hist


def test_the_users_live_on_their_header_decided_divergence(v1):
    """B-68, decided 2026-10-02. 324E001's chest draws 10 t/h more. V1's LP header carries its
    users as one constant set at boot, so it never notices: 5.013 bar a, PV-329207B on its 50 %
    bias. The port's falls to 4.84 bar a in 4.5 s and 4.81 at 30 s, PV-329207B cutting the
    turbine's export to 10.3 t/h and PV-329207C admitting 3.0 t/h, and is back at 4.92 in five
    minutes."""
    hist = pair(v1, "B-68", 3000, users_lp=1.0 + 10000.0 / 52222.0)
    for k in (50, 300, 2999):
        assert hist[k]["v1"]["P_LP"] == pytest.approx(5.01325, abs=1e-9)
        assert hist[k]["v1"]["pv207b"] == pytest.approx(50.0, abs=1e-9)
    r = hist[50]["port"]
    assert r.p_lp_bara == pytest.approx(4.8407, abs=1e-4)
    r = hist[300]["port"]
    assert (r.p_lp_bara, r.flows_kgh["932"], r.flows_kgh["963"]) == (
        pytest.approx(4.8117, abs=1e-4), pytest.approx(10285.8, abs=0.1),
        pytest.approx(3045.5, abs=0.1))
    assert hist[2999]["port"].p_lp_bara == pytest.approx(4.9242, abs=1e-4)


def test_the_pfds_basis_decided_divergence(v1):
    """Decision 47's class. V1 seeds PV-329204 on the stripper's 39 400 kW / 1850 kJ/kg, 76 670
    kg/h, and its flash fraction on that flow (6.08 %); the port on PFD 902's 57 989 and 904's
    (8.03 %). Each holds its own design; the 906 flash is 4658 kg/h on either. The stripper 20 %
    down: in ten seconds both supplies have closed to 44.2 %, V1's passing 61.2 t/h, the port's
    46.3."""
    hist = pair(v1, "47", 600, strip=0.8)
    a, r = hist[4]["v1"], hist[4]["port"]
    assert (a["m_supply"], a["m_flash9"], a["P_MP"]) == (
        pytest.approx(76670.27, abs=0.01), pytest.approx(4658.0, abs=1e-6),
        pytest.approx(19.7, abs=1e-9))
    assert (r.flows_kgh["902"], r.flows_kgh["906"], r.p_hp_bara) == (
        pytest.approx(57989.0, abs=1e-6), pytest.approx(4658.0, abs=1e-6),
        pytest.approx(19.7, abs=1e-9))
    a, r = hist[100]["v1"], hist[100]["port"]
    assert (a["supply_pct"], r.strokes_pct["PV-329204"]) == (pytest.approx(44.2047, abs=1e-4),
                                                            pytest.approx(44.2054, abs=1e-4))
    assert (a["m_supply"], r.flows_kgh["902"]) == (pytest.approx(61249.5, abs=0.1),
                                                  pytest.approx(46312.4, abs=0.1))


def test_the_waters_the_drums_pay_decided_divergence(v1):
    """B-70, decided 2026-10-02. At design the port's 329D005 boils 8913 kg/h of its water on
    902's superheat — the stripper condenses 66 902 — 913 flashes 2570 kg/h into the LP header and
    959 blows 3628 down; V1 has none of them. 324E003 lost: 30 s on, PIC-329205's PI (its DCS row,
    decided 2026-10-28) has PV-329205B letting 1957 kg/h down, and V1 adds 25.3 kg/h of letdown
    water to the LP vapour from nowhere, holding 322D001's level; the port adds none — the letdown
    joins the header past the drums ("917", the next test) — and its level moves.
    The HPCC's raising lost: V1 holds the LP header at its 3.5 bar a floor, PV-329207C wide open;
    the port's falls through it, 2.58 bar a in two minutes, 2.11 in five."""
    r = pair(v1, "B-70", 10)[0]["port"]
    f = r.flows_kgh
    assert (f["ds_329D005"], f["strip"], f["915"], f["959"]) == (
        pytest.approx(8912.66, abs=0.01), pytest.approx(66901.66, abs=0.01),
        pytest.approx(2570.42, abs=0.01), pytest.approx(3628.0, abs=1e-9))
    hist = pair(v1, "B-70", 3000, users_9=0.0)
    a, r = hist[300]["v1"], hist[300]["port"]
    assert (a["m_ld"], a["m_water"], a["lvl504"]) == (
        pytest.approx(1956.82, abs=0.01), pytest.approx(25.260, abs=1e-3),
        pytest.approx(50.0, abs=1e-9))
    assert (r.flows_kgh["960"], r.flows_kgh["ds_322D001"]) == (pytest.approx(1959.00, abs=0.01),
                                                               0.0)
    assert r.levels_pct["LIC-329504"] == pytest.approx(50.1253, abs=1e-4)
    hist = pair(v1, "B-70", 3000, **{"raise": 0.0})
    for k in (300, 1200, 2999):
        assert hist[k]["v1"]["P_LP"] == 3.5
    assert (hist[1200]["port"].p_lp_bara, hist[2999]["port"].p_lp_bara) == (
        pytest.approx(2.5777, abs=1e-4), pytest.approx(2.1070, abs=1e-4))


def test_the_lp_header_downstream_of_the_drums_decided_divergence(v1):
    """The topology note, 2026-10-02 (PFD 26, P&ID 107/1): 322D001A/B's tops discharge 917 into
    the LP header and 960 joins the header past them. At design the drums discharge 68 929 kg/h,
    PFD 917's 68 928. 324E003 lost, PV-329205B letting 1957 kg/h down 30 s on (PIC-329205's PI,
    decided 2026-10-28): B-70's build boils 29.2 kg/h of 322D001's water on 960's superheat, the
    header at 5.10183 bar a and the drum at 50.1247 %; the port boils none, 5.10107 bar a and
    50.1253 %, and its drums discharge 69 960 kg/h — the header's users and valves less 960."""
    r = pair(v1, "917", 10)[0]["port"]
    assert r.flows_kgh["917"] == pytest.approx(68929.0, abs=1e-6)
    assert r.flows_kgh["917"] == (r.flows_kgh["users_lp"] + r.flows_kgh["PV-329207A"]
                                  + r.flows_kgh["932"] - r.flows_kgh["960"])
    hist = pair(v1, "917", 301, users_9=0.0)
    a, r = hist[300]["v1"], hist[300]["port"]
    ds_960 = a["m_ld"] * ws.superheat_water_ratio(ws.h_vapour_sat_at_kjkg(a["P_9"]), a["P_LP"])
    assert (ds_960, a["P_LP"], a["lvl_d001"]) == (pytest.approx(29.193, abs=1e-3),
                                                  pytest.approx(5.10183, abs=1e-5),
                                                  pytest.approx(50.1247, abs=1e-4))
    assert (r.flows_kgh["ds_322D001"], r.p_lp_bara, r.levels_pct["LIC-329504"]) == (
        0.0, pytest.approx(5.10107, abs=1e-5), pytest.approx(50.1253, abs=1e-4))
    assert r.flows_kgh["917"] == pytest.approx(69959.9, abs=0.1)


def test_the_drum_between_its_taps_decided_divergence(v1):
    """Decisions 33 and 11. LV-329502 wide open by hand: 329D005's water, 66.9 t/h in, 85.9 t/h
    out. V1's level, on the mid-chord's 11 223 kg per 100 %, reaches 0 % at 12 min 3 s and stays
    there with the valve still passing 85.9 t/h — 27.9 t/h of water from nothing. The port's drum
    holds its heads (10.0 m2 at the axis, not 8.8): its transmitter reads 0 % at 11 min 38 s, when
    the water is at the lower tap, not gone; at the heel LV-329502 passes only what arrives, 60.4
    t/h. On PIC-329205's PI (decided 2026-10-28) both hold 329D009 at its 9.0 bar a."""
    def act(k, s, net):
        if k == 5:
            s.lic502_mode, s.lic502_op = "MAN", 100.0
            net.lic_329502.mode, net.lic_329502.op_pct = "MAN", 100.0
    hist = pair(v1, "taps", 15000, act=act)
    assert next(k for k in range(15000) if hist[k]["v1"]["lvl502"] == 0.0) == 7234
    assert next(k for k in range(15000) if hist[k]["port"].levels_pct["LIC-329502"] == 0.0) == 6980
    a, r = hist[14999]["v1"], hist[14999]["port"]
    assert a["water_d005"] == pytest.approx(-27943.0, abs=0.1)
    assert (a["P_9"], r.p_9_bara) == (pytest.approx(9.0000, abs=1e-4),
                                      pytest.approx(9.0000, abs=1e-4))
    assert r.flows_kgh["904"] == pytest.approx(60380.1, abs=0.1)
    assert r.water_residual_kgh["329D005"] == pytest.approx(0.0, abs=1e-6)


def test_the_vendor_trims_decided_divergence(v1):
    """Decision 23. PV-329205A sits at 19.55 % on Flowserve's trim, V1's at 50 %. 324E003 lost:
    PIC-329205 shuts A and opens B, its PI (decided 2026-10-28) bringing 329D009 back to its set
    point: 30 s on, V1's linear PV-329205B (K 2.0) stands at 6.9 % passing 1230 kg/h at 10.915 bar
    a, the vendor's modified equal-percentage trim at 37.3 % passing 1959; five minutes on, 33.2 %
    for 4770 kg/h at 9.025 bar a against the trim's 73.2 % for 4663 at 9.039."""
    hist = pair(v1, "trim", 3000, users_9=0.0)
    a, r = hist[0]["v1"], hist[0]["port"]
    assert (a["admit9_pct"], r.strokes_pct["PV-329205A"]) == (50.0,
                                                              pytest.approx(19.5479, abs=1e-4))
    a, r = hist[300]["v1"], hist[300]["port"]
    assert (a["letdown_pct"], a["m_ld"], a["P_9"]) == (
        pytest.approx(6.8593, abs=1e-4), pytest.approx(1229.54, abs=0.01),
        pytest.approx(10.9147, abs=1e-4))
    assert (r.strokes_pct["PV-329205B"], r.flows_kgh["960"], r.p_9_bara) == (
        pytest.approx(37.3109, abs=1e-4), pytest.approx(1959.00, abs=0.01),
        pytest.approx(10.9145, abs=1e-4))
    a, r = hist[2999]["v1"], hist[2999]["port"]
    assert (a["letdown_pct"], a["m_ld"], a["P_9"]) == (
        pytest.approx(33.1540, abs=1e-4), pytest.approx(4770.00, abs=0.01),
        pytest.approx(9.0246, abs=1e-4))
    assert (r.strokes_pct["PV-329205B"], r.flows_kgh["960"], r.p_9_bara) == (
        pytest.approx(73.1974, abs=1e-4), pytest.approx(4662.73, abs=0.01),
        pytest.approx(9.0386, abs=1e-4))


def test_the_butterflies_on_their_loop_summaries_decided_divergence(v1):
    """§4's order. HV-329601 opened wide by hand on 329D005: on V1's coefficient it vents 288 t/h
    of 19.7 bar a steam through a DN 80 body, more than the supply can give, and 329D005
    falls to 7.4 bar a in thirty seconds; on its loop summary's maximum case it vents 8.9 t/h, PIC-329204 opening the supply
    to 54 % and holding 19.0 bar a."""
    def act(k, s, net):
        if k == 5:
            s.hv601.hic_pct = s.hv_vent_hp_pct = net.hv_329601.hic_pct = 100.0
    hist = pair(v1, "loopsum", 1200, act=act)
    assert hist[5]["v1"]["m_vent_hp"] == pytest.approx(287929.4, abs=0.1)
    assert hist[300]["v1"]["P_MP"] == pytest.approx(7.4087, abs=1e-4)
    r = hist[300]["port"]
    assert (r.flows_kgh["HV-329601"], r.strokes_pct["PV-329204"], r.p_hp_bara) == (
        pytest.approx(8891.8, abs=0.1), pytest.approx(54.1005, abs=1e-4),
        pytest.approx(19.0040, abs=1e-4))


def test_the_gains_on_span_decided_divergence(v1):
    """Decisions 10 and 21. The master set point to 4.4 bar a: on V1's 24 %/bar retune the header
    is at 4.75 bar a after five seconds and 4.477 after ten minutes, venting 418 kg/h; on the
    table's gains per cent of PT-329207's span (A 100, B and C 66.7 %/bar) at 4.55 and 4.435, the
    vent shut."""
    def act(k, s, net):
        if k == 5:
            s.master207_sp = net.pic_329207.master_sp_bara = 4.4
    hist = pair(v1, "gains", 6000, act=act)
    assert (hist[50]["v1"]["P_LP"], hist[50]["port"].p_lp_bara) == (
        pytest.approx(4.7502, abs=1e-4), pytest.approx(4.5483, abs=1e-4))
    a, r = hist[5999]["v1"], hist[5999]["port"]
    assert (a["P_LP"], a["m_vent"]) == (pytest.approx(4.4771, abs=1e-4),
                                        pytest.approx(417.77, abs=0.01))
    assert (r.p_lp_bara, r.flows_kgh["PV-329207A"]) == (pytest.approx(4.4353, abs=1e-4), 0.0)


def test_trip_21_2_decided_divergence(v1):
    """Decisions 26, 27 and 39: Uhde's functional diagram (UD-MR-329-FF-0002 sheet 3). The
    stripper stops on trip 21.2. V1 has no logic: PIC-329204 holds its 19.7 bar a set point and
    shuts the supply, 329D005 locked in at 25.0 bar a. The port loads 10 bar g (11.01325 bar a on
    the standard atmosphere, handoff B-6) into
    the set point and forces HV-329601 open above 12 bar g: 329D005 vents 9.2 t/h and falls to
    13.0 bar a in five minutes. Near 12 bar g the forcing relays HV-329601 open for a tick and shut
    for three to six — 214 changes until PV-329204 has shut the supply, the last opening at
    3 min 29 s — then it is the operator's again (handoff B-72)."""
    hist = pair(v1, "trip", 3000, strip=0.0, trip=True)
    a = hist[2999]["v1"]
    assert (a["P_MP"], a["sp204"], a["supply_pct"], a["m_vent_hp"]) == (
        pytest.approx(25.0001, abs=1e-4), 19.7, 0.0, 0.0)
    r = hist[6]["port"]
    assert (r.strokes_pct["HV-329601"], r.hv_329601_blocked) == (100.0, True)
    assert r.flows_kgh["HV-329601"] == pytest.approx(9219.6, abs=0.1)
    r = hist[2999]["port"]
    assert (r.p_hp_bara, r.strokes_pct["HV-329601"], r.hv_329601_blocked) == (
        pytest.approx(12.9912, abs=1e-4), 0.0, False)
    ops = [hist[k]["port"].strokes_pct["HV-329601"] for k in range(3000)]
    assert sum(1 for x, y in zip(ops, ops[1:]) if x != y) == 214
    assert max(k for k in range(3000) if ops[k] > 0.0) == 2087


def test_the_safety_valves_decided_divergence(v1):
    """Decision 32. 324E003 lost and PV-329205A opened wide by hand: V1's 329D009 climbs to the
    battery limit's 25.0 bar a; the port's lifts SV32952 at 12.013 bar a and holds just above its
    10.913 bar a reseat, venting 30.1 t/h."""
    def act(k, s, net):
        if k == 5:
            s.pic205_mode = net.pic_329205.mode = "MAN"
            s.valve_admit9_pct = net.pic_329205.op_a_pct = 100.0
    hist = pair(v1, "relief", 3000, act=act, users_9=0.0)
    assert hist[300]["v1"]["P_9"] == pytest.approx(25.0001, abs=1e-4)
    r = hist[300]["port"]
    assert (r.p_9_bara, r.relief_kgh["SV32952"]) == (pytest.approx(10.9297, abs=1e-4),
                                                     pytest.approx(30080.5, abs=0.1))
