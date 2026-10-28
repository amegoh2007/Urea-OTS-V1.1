"""Behaviour of unit 329's steam network — `ureasim.units.steam.steam_network`.

Equivalence with V1 is proven in `tests/equivalence/test_steam_network_equivalence.py` (the port
``==`` V1's ``step_steam`` transcribed with nine switches, every switch off ``==`` V1 executed), and
each decided divergence both ways in `tests/equivalence/test_steam_network_decided_equivalence.py`.
This file pins what the network DOES: the design closure on the PFD (handoffs B-68 to B-70), the
headers' answers to their users, the drums' water, trip 21.2 and the safety valves.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from ureasim.data import unit_329 as d
from ureasim.units.steam.steam_network import (
    SteamDraws,
    SteamNetwork,
    pfd_basis_kgh,
    v1_butterflies,
)

D = SteamDraws()


def _run(n, draws_at=lambda k: D, act=None, trip_at=None):
    net, out = SteamNetwork(), []
    for k in range(n):
        if act is not None:
            act(k, net)
        out.append(net.step(draws_at(k), 0.1,
                            trip_21_2=trip_at is not None and k >= trip_at))
    return net, out


def test_the_design_is_the_pfds_and_holds():
    """An hour at design: every vapour node and every drum's water balances to 1e-10 kg/h, the
    headers stay at 19.7, 9.0 and 4.0 bar g to the bit, the levels at 50 %; the flows the PFD's — 902 57 989,
    903 1754, 904 57 989, 906 4658, 913 53 056, 932 16 707, 959 3628, 901 60 848 on FT-329403 —
    and the closure's: the stripper condenses 66 902, 8913 of them 329D005's own water; 322E002
    raises 66 359 and 913 flashes 2570 at 4.0 bar g; LV-329504 makes up 19 501."""
    _, out = _run(36000)
    r = out[-1]
    assert (r.p_hp_bara, r.p_9_bara, r.p_lp_bara) == (19.7, 9.0, 5.01325)
    assert all(abs(v) < 1e-10 for v in r.vapour_residual_kgh.values())
    assert all(abs(v) < 1e-10 for v in r.water_residual_kgh.values())
    assert all(v == pytest.approx(50.0, abs=1e-12) for v in r.levels_pct.values())
    f = r.flows_kgh
    for key, pfd in (("902", 57989.0), ("903", 1754.0), ("904", 57989.0), ("906", 4658.0),
                     ("913", 53056.0), ("932", 16707.0), ("959", 3628.0), ("901", 60848.0)):
        assert f[key] == pytest.approx(pfd, abs=1e-6), key
    assert (f["strip"], f["ds_329D005"], f["raise"], f["915"], f["916"]) == (
        pytest.approx(66901.66, abs=0.01), pytest.approx(8912.66, abs=0.01),
        pytest.approx(66358.58, abs=0.01), pytest.approx(2570.42, abs=0.01),
        pytest.approx(19501.0, abs=1e-6))
    assert (f["960"], f["963"], f["HV-329601"], f["PV-329207A"]) == (0.0, 0.0, 0.0, 0.0)
    assert sum(r.relief_kgh.values()) == 0.0 and sum(r.overflow_kgh.values()) == 0.0


def test_a_unit_draws_on_the_pfds_basis():
    """Decision 47's class: a unit's live ratio on its PFD row."""
    assert pfd_basis_kgh(4158.0, 3741.0 * 1.1, 3741.0) == pytest.approx(4573.8, abs=1e-9)
    assert pfd_basis_kgh(4158.0, 10.0, 0.0) == 0.0


def test_the_lp_header_answers_its_users():
    """B-68: 324E001's chest 10 t/h up. The header falls to 4.84 bar a in 4.5 s; PV-329207B cuts
    the turbine's export to 10.4 t/h and PV-329207C admits 3.1 t/h of supply steam by 30 s; in five
    minutes the header is back at 4.92 bar a, B carrying the load at 30.4 % on its Neldisc
    (decided 2026-10-15; 25.6 % on V1's valve), C on its Mark One (decision 150)."""
    up = dict(D.users_lp_kgh)
    up["919"] += 10000.0
    _, out = _run(3000, lambda k: replace(D, users_lp_kgh=up) if k >= 5 else D)
    assert out[50].p_lp_bara == pytest.approx(4.8393, abs=1e-4)
    r = out[300]
    assert (r.p_lp_bara, r.flows_kgh["932"], r.flows_kgh["963"]) == (
        pytest.approx(4.8091, abs=1e-4), pytest.approx(10355.6, abs=0.1),
        pytest.approx(3106.0, abs=0.1))
    r = out[2999]
    assert (r.p_lp_bara, r.strokes_pct["PV-329207B"]) == (pytest.approx(4.9237, abs=1e-4),
                                                          pytest.approx(30.352, abs=1e-3))


def test_nothing_holds_the_lp_header_up():
    """B-70: 322E002's raising lost with the users at their design draws. PV-329207C wide open
    admits 39.4 t/h on its Mark One (decision 150), short of the 52 t/h the users take: the header
    falls through V1's 3.5 bar a floor at 13.5 s and to 1.96 bar a in five minutes; 322D001's level rises, LV-329504 still making
    up."""
    _, out = _run(3000, lambda k: replace(D, raise_kgh=0.0) if k >= 5 else D)
    assert next(k for k in range(3000) if out[k].p_lp_bara < 3.5) == 135
    r = out[2999]
    assert (r.p_lp_bara, r.flows_kgh["963"]) == (pytest.approx(1.9553, abs=1e-4),
                                                 pytest.approx(39370.7, abs=0.1))
    assert r.levels_pct["LIC-329504"] == pytest.approx(65.462, abs=1e-3)


def test_a_drum_drains_to_its_heel_not_past_it():
    """Decisions 33 and 11: LV-329502 wide open by hand. 329D005's transmitter reads 0 % at
    11 min 38 s; the drum goes on draining to its 1 kg heel, and then LV-329502 passes only what
    arrives, 60 380 kg/h, the drum's water balanced."""
    def act(k, net):
        if k == 5:
            net.lic_329502.mode, net.lic_329502.op_pct = "MAN", 100.0
    net, out = _run(12000, act=act)
    assert next(k for k in range(12000) if out[k].levels_pct["LIC-329502"] == 0.0) == 6980
    assert net.m_d005_kg == pytest.approx(1.0, abs=1e-9)
    r = out[-1]
    assert r.flows_kgh["904"] == pytest.approx(60379.6, abs=0.1)
    assert r.water_residual_kgh["329D005"] == pytest.approx(0.0, abs=1e-6)


def test_a_full_drum_overflows():
    """Decision 11: LV-329503 shut by hand. 329D009 fills in 4 minutes and its excess, the 53 056
    kg/h LV-329502 still sends, is published as an overflow; 322D001, unfed, falls to 40.7 %."""
    def act(k, net):
        if k == 5:
            net.lic_329503.mode, net.lic_329503.op_pct = "MAN", 0.0
    _, out = _run(6000, act=act)
    assert next(k for k in range(6000) if out[k].overflow_kgh["329D009"] > 0.0) == 2398
    r = out[-1]
    assert r.overflow_kgh["329D009"] == pytest.approx(53056.0, abs=1e-3)
    assert r.levels_pct["LIC-329503"] == 100.0
    assert r.levels_pct["LIC-329504"] == pytest.approx(40.709, abs=1e-3)


def test_trip_21_2():
    """The stripper stops on trip 21.2: PIC-329204's set point to 10 bar g; HV-329601 forced open
    at once, venting 15.9 t/h on its Mark One (decision 150), the operator blocked; 329D005 at
    16.8 bar a after 30 s (the Neldisc on PV-329204, decided 2026-10-15, shuts it faster than V1's
    valve), 13.0 after five minutes, HV-329601 then shut and the operator's again."""
    net, out = _run(3000, lambda k: replace(D, strip_kgh=0.0) if k >= 5 else D, trip_at=5)
    r = out[6]
    assert (r.strokes_pct["HV-329601"], r.hv_329601_blocked) == (100.0, True)
    assert r.flows_kgh["HV-329601"] == pytest.approx(15934.8, abs=0.1)
    assert net.pic_329204.sp_bara == pytest.approx(11.01325, abs=1e-12)    # 10 bar g (B-6)
    assert out[300].p_hp_bara == pytest.approx(16.7586, abs=1e-4)
    r = out[2999]
    assert (r.p_hp_bara, r.strokes_pct["HV-329601"], r.hv_329601_blocked) == (
        pytest.approx(13.0102, abs=1e-4), 0.0, False)


def test_sv32952_relieves_329d009():
    """Decision 32: 324E003 lost with PV-329205A held wide open. 329D009 passes SV32952's set,
    12.013 bar a, in 1.2 s; the valve lifts and holds the drum just above its 10.913 bar a reseat,
    venting 27.6 t/h at 30 s."""
    def act(k, net):
        if k == 5:
            net.pic_329205.mode, net.pic_329205.op_a_pct = "MAN", 100.0
    u9 = dict(D.users_9_kgh)
    u9["920"] = 0.0
    _, out = _run(3000, lambda k: replace(D, users_9_kgh=u9) if k >= 5 else D, act=act)
    k = next(k for k in range(3000) if out[k].relief_kgh["SV32952"] > 0.0)
    assert k == 13 and out[k - 1].p_9_bara > 12.013
    r = out[300]
    assert (r.p_9_bara, r.relief_kgh["SV32952"]) == (pytest.approx(10.9283, abs=1e-4),
                                                     pytest.approx(27551.6, abs=0.1))


def test_the_users_at_their_pfd_rows():
    """The design draws: the LP users 52 222 kg/h besides 932, the 9-bar users PFD 907's 6687."""
    assert sum(D.users_lp_kgh.values()) == d.LP_USERS_DES_KGH == 52222.0
    assert sum(D.users_9_kgh.values()) == d.MP9_USERS_DES_KGH == 6687.0
    assert D.users_9_kgh["flood"] == 0.0


# --------------------------------------------------------------------------------------
# Handoff B-73: the users on their valves, against their headers' live pressures
# --------------------------------------------------------------------------------------

def _run_b73(n, raise_at=None, flood_at=None):
    """The network with the motive steam, FV-329401 and XV-322915's flood on their valves, each
    reading its header as the network left it on the tick before (B-73); 322E002's raising lost
    at `raise_at`, the flood opened at `flood_at`."""
    from ureasim.data import unit_324_train as t
    from ureasim.data import unit_328c004 as c
    from ureasim.units.absorption import vent_line as vl
    from ureasim.units.desorption import second_desorber as sd
    from ureasim.units.evaporation import vacuum_train as vt

    net, fic, out = SteamNetwork(), sd.fic_329401(), []
    for k in range(n):
        lp, mp9 = dict(D.users_lp_kgh), dict(D.users_9_kgh)
        mot = vt.motive_steam(t.HV_329605_OP_DES_PCT, t.HV_329606_OP_DES_PCT, net.p_lp_bara)
        lp["924"], lp["927"], lp["929"] = mot.m_924_kgh, mot.m_927_kgh, mot.m_929_kgh
        lp["931"] = fic.step(0.1, cas_sp=c.C004_M931_DES_KGH, pressure_ratio=(
            sd.fv_329401_pressure_ratio(net.p_lp_bara, c.FV_329401_P2_DES_BARA, c.FV_329401_XT)))
        if flood_at is not None and k >= flood_at:
            mp9["flood"] = vl.flood_steam_kgh(net.p_9_bara)
        lost = raise_at is not None and k >= raise_at
        draws = replace(D, users_lp_kgh=lp, users_9_kgh=mp9,
                        raise_kgh=0.0 if lost else D.raise_kgh)
        out.append((net.step(draws, 0.1), lp, mp9, fic.loop.op))
    return out


def _reversals(xs, threshold):
    return sum(1 for a, b, c in zip(xs, xs[1:], xs[2:])
               if (b - a) * (c - b) < 0 and abs(b - a) > threshold and abs(c - b) > threshold)


def test_the_users_on_their_valves_hold_the_design_b73():
    """At design the motive valves, FV-329401 and the shut flood draw their PFD rows to the bit
    from a header at its 4.0 bar g, and the network holds it there for an hour — the plant
    started at 100 % load holds its LP header at the operators' 4.0 bar g, FV-329401 on its
    Neldisc's 26.0 % design stroke."""
    out = _run_b73(36000)
    r, lp, mp9, op = out[-1]
    assert (r.p_hp_bara, r.p_9_bara, r.p_lp_bara) == (19.7, 9.0, 5.01325)
    assert all(r.p_lp_bara == 5.01325 for r, _, _, _ in out)
    assert (lp["924"], lp["927"], lp["929"], lp["931"], mp9["flood"], op) == (
        390.0, 1220.0, 180.0, 6495.0, 0.0, 26.0)
    assert all(abs(v) < 1e-10 for v in r.vapour_residual_kgh.values())


def test_a_lost_raising_starves_the_users_b73():
    """B-73, decided 2026-10-02. 322E002's raising lost: with every user at its design draw the
    header fell through 3.5 bar a in 14 s to 2.11 bar a in five minutes. On their valves the
    users draw less as it falls — the motive steam with it, FV-329401 opening against it — so it
    bottoms at 3.65 bar a and is at 3.95 bar a in five minutes, the motive at 79 % of design,
    FV-329401 at 58.9 % on its Neldisc passing 4029 kg/h (decided 2026-10-15; PV-329207C on its
    Mark One, decision 150; on V1's valves 4.09 bar a, FV-329401 at 83 % passing 4119). One
    minimum, no ringing."""
    out = _run_b73(3005, raise_at=5)
    p = [r.p_lp_bara for r, _, _, _ in out]
    assert (min(p), p[145], p[-1]) == (pytest.approx(3.6524, abs=1e-4),
                                       pytest.approx(3.6694, abs=1e-4),
                                       pytest.approx(3.9541, abs=1e-4))
    _, lp, _, op = out[-1]
    assert (lp["924"], lp["927"], lp["931"], op) == (
        pytest.approx(308.7, abs=0.1), pytest.approx(965.8, abs=0.1),
        pytest.approx(4029.2, abs=0.1), pytest.approx(58.88, abs=0.01))
    assert _reversals(p, 1e-6) == 1


def test_the_flood_draws_the_9_bar_header_b73():
    """XV-322915 opened at design: the flood draws 329D009's header to 8.575 bar a in ten seconds;
    PIC-329205's integral (its DCS row, decided 2026-10-28) restores it to 8.999 in five minutes,
    passing 999.9 kg/h — its rating at 9.0 bar a is 1000 (V1's proportional split held 8.765 and
    975 kg/h); one turn on the 9-bar header, the LP header settling without ringing."""
    out = _run_b73(3005, flood_at=5)
    p9 = [r.p_9_bara for r, _, _, _ in out]
    assert (p9[105], p9[-1]) == (pytest.approx(8.5752, abs=1e-4), pytest.approx(8.9987, abs=1e-4))
    assert out[-1][2]["flood"] == pytest.approx(999.87, abs=0.01)
    assert _reversals(p9, 1e-7) == 1
    assert _reversals([r.p_lp_bara for r, _, _, _ in out], 1e-7) == 0


def _both(draws_at, n=3000):
    """The network on V1's butterflies and on Metso's trims, side by side."""
    runs = []
    for net in (SteamNetwork(**v1_butterflies()), SteamNetwork()):
        runs.append([net.step(draws_at(k), 0.1) for k in range(n)])
    return runs


def test_the_butterflies_on_metsos_trims():
    """Decision 108's class, decided 2026-10-15: PV-329204 on its Neldisc from 44.1 %, PV-329207B
    from 54.96 %, PV-329207A on its full stroke's 165 770 kg/h (the harness proves V1's ``==``).
    The stripper 10 % up: V1's PV-329204 opens to 53.1 % in 30 s and 329D005 dips to 19.176 bar a,
    the Neldisc to 46.2 % and 19.346 bar a; after five minutes 19.582 and 19.648. The LP users
    15 t/h down: V1's PV-329207A vents 8.4 t/h at 30 s, the header at 5.194 bar a; the Neldisc 6.4
    t/h at 5.175, PV-329207B exporting 25.3 t/h against 23.3; after five minutes the Neldisc vents
    1.6 t/h at 1.9 % (V1 5.7 t/h at 6.7 %) and exports 30.1 t/h (V1 26.0)."""
    v1, port = _both(lambda k: replace(D, strip_kgh=D.strip_kgh * 1.1) if k >= 5 else D)
    assert (v1[300].p_hp_bara, v1[300].strokes_pct["PV-329204"]) == (
        pytest.approx(19.1755, abs=1e-4), pytest.approx(53.091, abs=1e-3))
    assert (port[300].p_hp_bara, port[300].strokes_pct["PV-329204"]) == (
        pytest.approx(19.3455, abs=1e-4), pytest.approx(46.207, abs=1e-3))
    assert (v1[-1].p_hp_bara, port[-1].p_hp_bara) == (pytest.approx(19.5823, abs=1e-4),
                                                      pytest.approx(19.6480, abs=1e-4))
    down = dict(D.users_lp_kgh)
    down["919"] -= 15000.0
    v1, port = _both(lambda k: replace(D, users_lp_kgh=down) if k >= 5 else D)
    assert (v1[300].p_lp_bara, v1[300].flows_kgh["PV-329207A"], v1[300].flows_kgh["932"]) == (
        pytest.approx(5.1944, abs=1e-4), pytest.approx(8411.7, abs=0.1),
        pytest.approx(23258.2, abs=0.1))
    assert (port[300].p_lp_bara, port[300].flows_kgh["PV-329207A"],
            port[300].flows_kgh["932"]) == (pytest.approx(5.1751, abs=1e-4),
                                            pytest.approx(6419.9, abs=0.1),
                                            pytest.approx(25260.3, abs=0.1))
    assert (v1[-1].flows_kgh["PV-329207A"], v1[-1].strokes_pct["PV-329207A"]) == (
        pytest.approx(5688.1, abs=0.1), pytest.approx(6.692, abs=1e-3))
    assert (port[-1].flows_kgh["PV-329207A"], port[-1].strokes_pct["PV-329207A"],
            port[-1].flows_kgh["932"]) == (pytest.approx(1584.5, abs=0.1),
                                           pytest.approx(1.871, abs=1e-3),
                                           pytest.approx(30075.4, abs=0.1))
