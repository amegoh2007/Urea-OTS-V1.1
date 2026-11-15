"""V1 <-> V1.1 for the synthesis loop's decided departures, each run both ways.

`test_synthesis_loop_equivalence.py` proves the port ``==`` V1's transcribed glue with every switch
on. Here each runs with V1's lines (the transcription with that switch off) beside the port, and
what each side does is measured. A-16 (decision 32, a node relieving through its certified safety
valves) and A-17 (decision 29, a line discharging against its receiver's live pressure) are classes
decided on other units and applied to the loop under §5 rule 7. B-75, B-76 and B-78 items 1 to 3
are the process engineer's decisions of 2026-10-03 on the loop's flagged sinks; B-88 is the decision
of 2026-10-09 that a trip shutting XV-322902 trips the CO2 boundary (21.2's alone since decision
189, of 2026-11-12, removed V1's trip 22.2: switch D-189); B-77 (b), PT-329201 on the loop's vapour
inventory, and A-12, trips 21.2, 21.8 and 21.10 as AC4 executes them, are the decisions of
2026-10-09; B-91 (a), the loop's condensation capped by its liquor's bubble pressure, of
2026-10-10, and B-92, the reactor's liquor at its bubble point, of 2026-10-14. Every other switch is
on on both sides, so each pin carries the others' physics.
"""

from __future__ import annotations

import pytest

from tests.equivalence import test_synthesis_loop_equivalence as h
from ureasim.core.stream import MW_COMP
from ureasim.data.unit_322_loop import SYN_LOOP_RESID_DES_KGH
from ureasim.data.unit_322e003 import HOLDUP_MAX_KG, HOLDUP_NLL_KG, LEVEL_NLL_PCT, OVERFLOW_DES_KMOLH
from ureasim.units.consequence.crystallisation import mushy_flow_factor
from ureasim.units.synthesis.scrubber_sump import ScrubberSump
from tests.equivalence.v1_loader import v1_available

pytestmark = pytest.mark.skipif(not v1_available(), reason="V1 source tree not present")

v1 = h.v1


def test_sv32251_and_sv32252_relieve_the_loop_decided_divergence(v1):
    """A-16. The loop put at 160.5 bar a (21.2's flag is lost on the tick and AC4 cuts the feeds
    from the next on both sides; V1's 22.2 latched with it until decision 189 removed it, and the
    pins of both sides, measured again on 2026-11-12, stand). V1's assumed SV-32201, set at 161.01 bar a, never lifts: the loop falls on its
    boundary to 159.31 bar a in a minute. The port's SV32251 / SV32252, set at 160.01 bar a on
    Sempell's certified K orifices, lift at once and relieve 209 t/h of the reactor top's vapour,
    106 t/h of it ammonia: 157.69 bar a in a minute, V1's 159.31 (with B-91 (a) and B-92, decided 2026-10-10 and 2026-10-14: 157.6948 and
    159.3140 before them; with B-81's lines and B-77 (b) and AC4's trips, decided 2026-10-09: 156.4679 and 158.7766 before them; 156.4672 before FFIC-321404A
    / B, B-85). B-75 and B-78 run on both sides. (On session 46's decisions — 320K002 a boundary
    feed, LIC-322501 and the SICs on the DCS's table, the stopped SICs forced to MAN at their table
    tunings; 159.24 and 156.92 bar a before.)"""
    def act(k, plant, s):
        if k == 0:
            plant.units["PT-329201"].p_syn_bara = s.p_syn = 160.5
    hist, _, _ = h.run_both(v1, 601, act, decided=h.ALL - {"A-16"}, check=False)
    out, res, p_v1 = hist[600]
    pt = res["PT-329201"]
    assert out.m_psv == 0.0 and p_v1 == pytest.approx(159.3133, abs=1e-4)
    assert pt.relief_lifted and pt.p_syn_bara == pytest.approx(157.6919, abs=1e-4)
    assert (pt.m_relief_kgh, pt.m_relief_nh3_kgh) == (pytest.approx(209261.0, abs=0.1),
                                                     pytest.approx(106131.3, abs=0.1))


def test_hv_322604_discharges_against_322c001_decided_divergence(v1):
    """A-17. 322C001 at SV32253's 6.013 bar a: the purge stays choked, 1708.32 kg/h both sides
    (1708.2642 with 322E003 on its own liquor and its sump,
    decided 2026-10-14; 1708.3214 with B-91 (a) and B-92, decided 2026-10-10 and 2026-10-14; 1708.3203 before them);
    let down to 4.0 bar a (V1) it arrives at 94.8 C, to the absorber's live 6.013 at 95.2 C."""
    def act(k, plant, s):
        plant.units["322C001"].p_bara = 6.013
    hist, _, _ = h.run_both(v1, 2, act, decided=h.ALL - {"A-17"}, check=False)
    out, res, _ = hist[1]
    pv = res["HV-322604"].valve
    assert out.hv604.mass_kgh == pv.mass_kgh == pytest.approx(1708.2642, abs=1e-4)
    assert (out.hv604.t_out_c, out.hv604.p_out_bara) == (94.8, 4.0)
    assert (pv.t_out_c, pv.p_out_bara) == (95.2, 6.013)


def test_the_residual_credit_scales_with_the_load_decided_divergence(v1):
    """B-75. The CO2 demand cut to 80 %: the reactor's load ratio settles at 0.79 and the recycle
    tear it deletes falls with it. V1 still credits the design residual, 2024.9 kg/h, and its loop
    runs down; the port credits the residual at the same ratio (1522.0 (1522.1 before decision 178) (1521.7 before decision 170) kg/h after two minutes).
    After two minutes V1's PT-329201 reads 141.4889 (141.4864 before decision 178) (141.4877 before decision 170) bar a, the port's 141.5020 (141.4994 before decision 178) (141.5007 before decision 170) (load ratio 0.7915,
    with the session-69 valves on their vendor sheets and 322E006 on PFD 28's water, decisions
    150 and 151; 141.4894, 141.5024 and 1521.6 with HV-323605, PV-323203 and TV-328002 on their Metso trims, 2026-10-17 — V1's side through the
    steam network it shares with the port; 141.4895 and 141.5025 on session 53's code, 2026-10-15;
    141.4957, 141.5088, 0.7916 and 1523.2 with PV-329202 and
    PV-329208 on their vendor trims, 2026-10-15; 141.4928 and 141.5058 before them;
    with 322E003 on its own liquor and its sump, decided 2026-10-14; 141.6382 and 141.6505 with B-91 (a) and B-92, decided 2026-10-10 and 2026-10-14,
    the reactor's residence on the liquid passing: the load ratio 0.7867; 1640.8, 140.3239 and
    140.3293 before them, at 0.8103; with B-81's lines
    and B-77 (b) and AC4's trips, decided 2026-10-09, the load ratio 0.8103: 1610.4, 141.0024 and
    141.0106 before them, at 0.7953; with FFIC-321404A / B, decided 2026-10-09, B-85: 1610.5,
    140.9960 and 141.0042 before; and with 320K002 a boundary feed and SIC-321951 and LIC-322501 on
    the DCS's table, decided 2026-10-08: the ammonia follows the CO2 cut on SIC-321951's 50 s;
    140.7011 and 140.7094 before the tunings, 140.6997 and 140.7079 on 320K002's vendor curves,
    140.6989 and 140.7072 on V1's fitted map)."""
    def act(k, plant, s):
        if k == 0:
            plant.operator["320K002-CO2"] *= 0.8
            s.co2_raw_th *= 0.8
    hist, _, s = h.run_both(v1, 1200, act, decided=h.ALL - {"B-75"}, check=False)
    _, res, p_v1 = hist[-1]
    pt, ratio = res["PT-329201"], res["322R001"].reaction.co2_scale
    assert ratio == pytest.approx(0.7915, abs=1e-4)
    assert pt.resid_credit_kgh == pt.loop_mass_frac * ratio * SYN_LOOP_RESID_DES_KGH
    assert pt.resid_credit_kgh == pytest.approx(1522.0, abs=0.1)
    assert (p_v1, pt.p_syn_bara) == (pytest.approx(141.4889, abs=1e-4),
                                     pytest.approx(141.5020, abs=1e-4))


def test_the_recondensed_backlog_returns_to_the_sump_decided_divergence(v1):
    """B-76. 329P006A stopped for a minute: the backlog builds while 322E003 cannot condense and
    recondenses after. V1 deletes what recondenses; the port returns it to 322E003's sump on the
    next tick, 141.66 (141.71 before decision 170) kg in three minutes. V1's sump ends at 3649.25 (3649.33 before decision 178) (3650.42 before decision 170) kg, the port's at 3765.34 (3765.41 before decision 178) (3766.32 before decision 170)
    (decisions 150 and 151's valves and water, through 323E003's 308; 3650.65 and 3766.57 with
    323F004 on its geometry, B-100, decided 2026-10-17, through 323E003's 308; 3650.52 and 3766.49
    with the three Metso valves on their trims, 2026-10-17; 3650.55 and 3766.50 on session 54's code,
    B-31 decided 2026-10-16; 3650.56 and 3766.51 on session 53's; 141.63, 3650.40 and 3766.41 before; with B-91 (a) and B-92, decided 2026-10-10 and 2026-10-14: 141.49, 3634.17 and 3745.06 before them; with
    B-81's lines and B-77 (b) and AC4's trips, decided 2026-10-09: 138.79, 3636.88 and 3746.40
    before them; both sides with FFIC-321404A / B, B-85 decided 2026-10-09 — 138.64, 3639.66 and
    3749.20 before; on the session-44 decisions: TT-322002 on 165 C, the standard atmosphere,
    FIC-329409 and TIC-329005 on the table's rows — 137.46, 3634.21 and 3742.25 before them — and on
    session 46's: 320K002 a boundary feed, LIC-322501 and the SICs on the table's rows — 137.84,
    3633.18 and 3741.60 before the tunings, 3632.99 and 3741.41 on 320K002's vendor curves, 3633.03
    and 3741.44 on V1's fitted map)."""
    def act(k, plant, s):
        if k == 5:
            plant.loops["322E003"][0].p329p006a = s.P329P006A = False
        if k == 605:
            plant.loops["322E003"][0].p329p006a = s.P329P006A = True
    hist, sched, s = h.run_both(v1, 1800, act, decided=h.ALL - {"B-76"}, check=False)
    rec_kg = sum(r["PT-329201"].m_recond_kgh for _, r, _ in hist[:-1]) * h.DT / 3600.0
    sump = sched.plant.units["322E003"]
    assert rec_kg == pytest.approx(141.66, abs=0.01)
    assert (s.scrub_holdup_kg, sump.holdup_kg) == (pytest.approx(3649.25, abs=0.01),
                                                   pytest.approx(3765.34, abs=0.01))


def test_a_full_sump_holds_its_excess_in_the_scrubber_decided_divergence(v1):
    """B-78 item 1. 322E003's sump 50 kg short of full and XV-322903 shut for 30 s: the ejector
    entrains nothing. V1 holds the sump at its maximum and deletes the rest; the port holds 275.9 kg
    back in the scrubber (the wash and the carryover; at a full sump it condenses no more than drains,
    B-91, decided 2026-10-14), which runs down once XV-322903 reopens (nothing held after a minute).
    After 90 s V1's sump holds 7512.0 kg, the port's 7618.9 (7511.9 for V1's before decisions 150
    and 151; 7619.0 before session 53's code;
    406.7, 209.0, 7486.8 and a full
    7674.8 before the full-sump cap; with B-91 (a) and B-92, decided 2026-10-10 and 2026-10-14:
    413.3, 197.5 and 7466.3 before them; with B-81's lines and
    B-77 (b) and AC4's trips, decided 2026-10-09: 415.1, 192.8 and 7452.5 before them; with
    FFIC-321404A / B, B-85 decided 2026-10-09: 415.2, 189.9 and 7449.6 before; with 320K002 a
    boundary feed and LIC-322501 and the SICs on the DCS's table, decided 2026-10-08; 226.3 and
    7486.2 before the tunings, 226.2 and 7486.1 on 320K002's vendor curves)."""
    def act(k, plant, s):
        if k == 0:
            m = HOLDUP_MAX_KG - 50.0
            unit = plant.units["322E003"]
            unit.holdup_kg = s.scrub_holdup_kg = m
            unit.level_pct = s.scrub_level_pct = m / HOLDUP_NLL_KG * LEVEL_NLL_PCT
            plant.operator["XV-322903"] = s.XV_322903 = False
        if k == 300:
            plant.operator["XV-322903"] = s.XV_322903 = True
    hist, sched, s = h.run_both(v1, 900, act, decided=h.ALL - {"B-78"}, check=False)
    assert hist[299][1]["322E003"].sump.held_kg == pytest.approx(275.95, abs=0.01)
    sump = sched.plant.units["322E003"]
    assert sump.held_kg == pytest.approx(0.00, abs=0.01)
    assert (s.scrub_holdup_kg, sump.holdup_kg) == (pytest.approx(7512.34, abs=0.01),
                                                   pytest.approx(7619.20, abs=0.01))


def test_the_forward_pulse_is_drawn_from_the_sump_decided_divergence(v1):
    """B-78 item 2. HV-322602 from 74 to 60 %: the forward-carbamate pulse puts 674.7 kg into the
    reactor in two minutes (674.6 before session 53's code; 677.9 kg before B-91 (a) and B-92, decided 2026-10-10 and 2026-10-14,
    with B-81's lines and B-77 (b) and AC4's trips, decided
    2026-10-09; 675.8 kg with FFIC-321404A / B, B-85 decided 2026-10-09; 675.3 kg on session 46's
    tunings). V1 draws it from nowhere; the port draws it from 322E003's sump, which ends 2727.6 kg
    against V1's 3228.7 (3228.4 before decision 170) (2727.7 and 3228.5 before decisions 150 and 151; 2727.4 and 3228.2 before
    session 53's code; 2727.3 and 3228.1 before the chests' vendor trims; 2786.6 and 3307.6 and a 683.7 kg pulse before 322E003's own liquor, decided
    2026-10-14; 2737.3 and 3211.9 before B-91 and B-92; 2738.7 and 3213.8 before B-81,
    B-77 and A-12; 2740.8 and 3216.3 before
    B-85; on the session-44 decisions, 320K002 a boundary feed and LIC-322501 and the SICs on the
    DCS's table, decided 2026-10-08; 678.9, 2735.9 and 3215.0 before the tunings, 2735.9 and 3214.9
    on 320K002's vendor curves, 679.0, 2736.2 and 3215.3 before)."""
    def act(k, plant, s):
        if k == 5:
            plant.operator["HIC-322602"] = s.HIC_322602 = 60.0
    hist, sched, s = h.run_both(v1, 1200, act, decided=h.ALL - {"B-78"}, check=False)
    pulse_kg = sum(r["322R001"].m_fwd_kgh for _, r, _ in hist) * h.DT / 3600.0
    assert pulse_kg == pytest.approx(674.67, abs=0.01)
    assert (s.scrub_holdup_kg, sched.plant.units["322E003"].holdup_kg) == (
        pytest.approx(3228.73, abs=0.01), pytest.approx(2727.97, abs=0.01))


def test_the_mushy_zone_holds_back_into_the_sump_decided_divergence():
    """B-78 item 3. An overflow at 62 C, 2 K into carbamate's 5 K mushy band, for one tick with the
    ejector stopped: V1 lets 40 % of it into the sump and deletes the rest (``step_sim`` 8113-8160,
    as the transcription writes it); the port takes it all in and throttles the line to 322F001 by
    the same 0.4 on the next tick. Not reached on the plant in any scenario measured."""
    m_ovf = sum(v * MW_COMP[k] for k, v in OVERFLOW_DES_KMOLH.items())
    f = mushy_flow_factor(62.0, 60.0)
    v1_holdup = min(max(HOLDUP_NLL_KG + (f * m_ovf - 0.0) * (h.DT / 3600.0), 0.0), HOLDUP_MAX_KG)
    sump = ScrubberSump()
    r = sump.step(dict(OVERFLOW_DES_KMOLH), 62.0, 0.0, 1.0, 0.1, h.DT)
    assert f == pytest.approx(0.4, rel=1e-12) and sump.mushy_factor == f
    assert v1_holdup == pytest.approx(HOLDUP_NLL_KG + 0.4 * m_ovf * h.DT / 3600.0, rel=1e-12)
    assert r.holdup_kg == pytest.approx(HOLDUP_NLL_KG + m_ovf * h.DT / 3600.0, rel=1e-12)


def test_a_trip_shutting_xv_322902_trips_the_co2_boundary_decided_divergence(v1):
    """B-88 (decided 2026-10-09, option c). The loop put at 155.5 bar a: the pressure stepped onto
    the loop starves the CO2 line, 21.2's flag is lost on its first tick and both sides shut
    XV-322902 from the next through the Safeguard SG1 (V1's 22.2 latched with it until decision 189
    removed it; the pins of both sides, measured again on 2026-11-12, stand). V1 leaves 320K002 delivering the
    instructor's 54.618 t/h into the blocked line, which packs until SV32064 lifts on tick 316
    (31.7 s) and still holds 159.70 bar a after a minute. The port trips the machine with the
    valve: the boundary's demand is zero from the same tick, the line holds 144.25 bar a and
    SV32064 never lifts."""
    seen = []

    def act(k, plant, s):
        if k == 0:
            plant.units["PT-329201"].p_syn_bara = s.p_syn = 155.5
        seen.append(s.line.sv_32064.valve.lifted)
    hist, sched, s = h.run_both(v1, 601, act, decided=h.ALL - {"B-88"}, check=False)
    assert seen.index(True) == 317 and s.co2_raw_th == pytest.approx(54.618, abs=1e-9)
    assert s.line.pressure_bara == pytest.approx(159.6998, abs=1e-4)
    assert sched.plant.operator["320K002-CO2"] == 0.0
    assert not any(r["320K002"].relief_lifted for _, r, _ in hist)
    assert sched.plant.units["320K002"].pressure_bara == pytest.approx(144.2532, abs=1e-4)


def test_the_vapour_inventory_node_decided_divergence(v1):
    """B-77 (b), decided 2026-10-09: HV-322605 from 60 to 45 %, two minutes. The reactor gains
    1492 kg. V1's lumped node counts it as pressure, PT-329201 141.3400 (141.3408 before decision 170) bar a; the port's vapour
    inventory carries it as liquid, 140.6789 (140.6794 before decision 170) — the vapour's 75.3 kg/bar and the reactor liquor's
    2110.8 (2110.9 before decision 170) kg/bar buffering (141.3412, 140.6792 and 75.4 before session 53's code), the liquid's gain 34.5 t/h on the last tick (with B-91 (a) and B-92, decided 2026-10-10 and 2026-10-14:
    141.2423 and 140.6904 bar a, 73.9 and 2110.4 kg/bar before them)."""
    def act(k, plant, s):
        if k == 5:
            plant.operator["HIC-322605"] = s.HIC_322605 = 45.0
    hist, sched, s = h.run_both(v1, 1200, act, decided=h.ALL - {"B-77"}, check=False)
    _, res, p_v1 = hist[-1]
    pt = res["PT-329201"]
    assert (p_v1, pt.p_syn_bara) == (pytest.approx(141.3400, abs=1e-4),
                                     pytest.approx(140.6789, abs=1e-4))
    assert sched.plant.units["322R001"].m_liq_kg == pytest.approx(137389.59, abs=0.01)
    assert (pt.c_vap_kg_per_bar, pt.c_buf_kg_per_bar) == (pytest.approx(75.19, abs=0.01),
                                                         pytest.approx(2110.84, abs=0.01))


@pytest.mark.parametrize("case", ["fault", "co2"])
def test_the_trips_as_ac4_executes_them_decided_divergence(v1, case):
    """A-12, decided 2026-10-09. 321P002B's fault (the standby A stopped): V1 latches 21.10 and
    stops B, the valves open; on AC4 B stops on its own protection, no HP ammonia pump runs, and
    21.2's flag is lost, both pumps' flags with it, XV-321901, XV-322901, XV-322903 and — through
    the Safeguard SG1 — XV-322902 shut (PC21.5.1 .12-.15; XV-322902 and XV-322903 decided
    2026-10-16). The CO2 demand cut to zero: V1 latches 21.4 and stops the machines, the valves
    open; on AC4 FY-322403 below its L2 loses 21.2, the machines stop on their flags and the valves
    shut. After a minute V1's loop stands at 139.2789 / 139.5422 (139.5461 before decision 178) (139.5473 before decision 170) bar a, AC4's, blocked in with the
    CO2 and the carbamate recycle isolated, at 141.1457 / 140.8893 (140.8892 before decision 178) (140.8885 before decision 170) (139.2729 / 139.5413 and
    141.1460 / 140.8889 before decisions 150 and 151; V1's CO2 case 139.5415 before
    the three Metso valves went on their trims, 2026-10-17; before 2026-10-16, when 21.2
    left XV-322902 and XV-322903 open, both at 139.4947 / 139.5184; V1's side moves too, through
    the steam network it shares with the port)."""
    def act(k, plant, s):
        if k == 5 and case == "fault":
            plant.units["321"].pump_b.fault = s.station.pump_b.fault = True
        if k == 5 and case == "co2":
            plant.operator["320K002-CO2"] = s.co2_raw_th = 0.0
    ends = {}
    for dec in (h.ALL - {"A-12"}, h.ALL):
        _, sched, s = h.run_both(v1, 600, act, decided=dec, check=False)
        st = s.station
        ends["A-12" in dec] = (dict(s.latched), st.pump_a.running, st.pump_b.running,
                               st.xv_321901_open, st.xv_322901_open, round(s.p_syn, 4),
                               s.line.xv_322902_open, s.XV_322903,
                               sched.plant.units["320K002"].xv_322902_open,
                               sched.plant.operator["XV-322903"])
    v1_trip = {"fault": "21_10", "co2": "21_4"}[case]
    assert ends[False][0] == {**dict.fromkeys(("21_2", "21_4", "21_8", "21_10", "22_2"), False),
                              v1_trip: True}
    assert ends[False][1:5] == (False, False, True, True)
    assert ends[True][0] == {"21_2": True, "21_4": False, "21_8": True, "21_10": True,
                             "22_2": False}
    assert ends[True][1:5] == (False, False, False, False)
    assert ends[False][6:8] == (True, True)
    assert ends[True][6:] == (False, False, False, False)
    assert (ends[False][5], ends[True][5]) == {"fault": (139.2789, 141.1457),
                                               "co2": (139.5422, 140.8893)}[case]


def _the_loop_at_130_7(k, plant, s):
    """The loop started 10 bar below its design, 130.7 bar a."""
    if k == 0:
        plant.units["PT-329201"].p_syn_bara = s.p_syn = 130.7


def test_the_loop_condenses_no_more_than_its_bubble_point_decided_divergence(v1):
    """B-91 (a), decided 2026-10-10. The loop started at 130.7 bar a, two minutes. On the first tick
    322E002's liquor, at its design bubble pressure, stands 10.0 bar above the loop's 3.5 bar design
    head: the port's saturation fraction is 0.8464, so 322E002's melt and 322E003 condense, and the
    reactor liquor buffers, 85 % of what V1's do. The melt's bubble pressure falls to 122.7 bar a,
    the fraction returns to 1 and the loop ends at 130.4825 (130.4826 before decision 178) bar a where V1's ends at 130.4012
    (122.9 and 130.4837 before session 53's code, 2026-10-15)."""
    hist, _, _ = h.run_both(v1, 1200, _the_loop_at_130_7, decided=h.ALL - {"B-91"}, check=False)
    _, res, p_v1 = hist[-1]
    first, last = hist[0][1]["322E002"].holdup, res["322E002"].holdup
    assert first.sat_frac == pytest.approx(0.8464, abs=1e-4) and last.sat_frac == 1.0
    assert last.condenser.p_bub_bara == pytest.approx(122.562, abs=1e-3)
    assert (p_v1, res["PT-329201"].p_syn_bara) == (pytest.approx(130.4012, abs=1e-4),
                                                   pytest.approx(130.4825, abs=1e-4))


def test_the_reactor_liquor_stands_at_its_bubble_point_decided_divergence(v1):
    """B-92, decided 2026-10-14. The same start, 130.7 bar a: the liquor's bubble point falls to
    177.55 C under nodes at their design temperatures. V1's nodes have no ceiling: after two minutes
    the top node stands at 181.75 C, 4 K above the bubble point. The port flashes the excess heat
    as the overflow's volatiles, 127.5 t/h on the first tick, and its nodes end at or below the
    bubble point, the top at 176.78 C; its loop at 130.4825 (130.4826 before decision 178) bar a against V1's 130.5108 (130.5110 before decision 170) (181.76,
    130.4837 and 130.5120 before session 53's code, 2026-10-15)."""
    hist, _, s = h.run_both(v1, 1200, _the_loop_at_130_7, decided=h.ALL - {"B-92"}, check=False)
    _, res, p_v1 = hist[-1]
    first, last = hist[0][1]["322R001"], res["322R001"]
    assert first.t_bub_c == pytest.approx(177.545, abs=1e-3)
    assert first.boil_kgh == pytest.approx(127451.8, abs=0.1)
    assert s.react_T_node[3] == pytest.approx(181.752, abs=1e-3)
    assert s.react_T_node[3] > last.t_bub_c
    assert max(last.t_nodes_c) <= last.t_bub_c + 1e-9
    assert last.t_nodes_c[3] == pytest.approx(176.778, abs=1e-3)
    assert (p_v1, res["PT-329201"].p_syn_bara) == (pytest.approx(130.5108, abs=1e-4),
                                                   pytest.approx(130.4825, abs=1e-4))


def test_the_saturation_fraction_solved_on_the_tick_decided_divergence(v1):
    """A-21, decided 2026-10-17: 322E002's saturation fraction solved with its own melt's bubble
    pressure on the tick, against V1's lines with B-91's fraction read a tick late (the
    transcription). HV-322605 60 -> 100 % at 0.5 s. On the tear the fraction rings with a period
    of two ticks — 322E002 condenses 3.7 then 227.3 t/h, its melt at 171 then 220 bar a — and the
    gas it passes builds the loop to 152.52 bar a in 30 s; solved on the tick it condenses a
    steady 131.8 t/h at a fraction of 0.514, its melt at 176.5 bar a, and the loop stands at
    141.357 bar a. Before the step the two differ by the seed's own drift (the tear's fraction
    dips to 0.99998 in the first ticks; solved, the seed condenses at 1.0 on its first)."""
    def act(k, plant, s):
        if k == 0:
            plant.units["322E002"].implicit_saturation = True
        if k == 5:
            plant.operator["HIC-322605"] = s.HIC_322605 = 100.0
    hist, _, _ = h.run_both(v1, 301, act, decided=h.ALL, check=False)
    out, res, p_v1 = hist[4]
    assert res["322E002"].holdup.condenser.liq_kgh == pytest.approx(out.hpcc["liq_kgh"], rel=1e-4)
    (a, ra, _), (b, rb, p_v1) = hist[299], hist[300]
    assert (a.hpcc["liq_kgh"], b.hpcc["liq_kgh"]) == (pytest.approx(3742.7, abs=0.1),
                                                     pytest.approx(227352.6, abs=0.1))
    assert (a.hpcc["P_bub"], b.hpcc["P_bub"]) == (pytest.approx(171.29, abs=0.01),
                                                 pytest.approx(220.29, abs=0.01))
    assert p_v1 == pytest.approx(152.5155, abs=1e-4)
    hp = rb["322E002"].holdup
    assert (hp.condenser.liq_kgh, hp.condenser.p_bub_bara, hp.sat_frac) == (
        pytest.approx(131846.0, abs=0.1), pytest.approx(176.47, abs=0.01),
        pytest.approx(0.5143, abs=1e-4))
    assert ra["322E002"].holdup.condenser.liq_kgh == pytest.approx(131859.3, abs=0.1)
    assert rb["PT-329201"].p_syn_bara == pytest.approx(141.3572, abs=1e-4)


def test_322e003s_capacity_on_its_shells_effectiveness_decided_divergence(v1):
    """B-99, decided 2026-10-17: 322E003's condensation capacity on its shell's conductance eps . C
    at the live circulation, its published duty capped at that capacity, against V1's linear flow
    law (the transcription). FIC-329409's set point 306 -> 250 t/h at 0.5 s: the two part on the
    tick after; two minutes on, with FT-329409 at 296.7 t/h, V1's capacity is 0.9695 and leaves
    631.0 kg/h of the loop's gas uncondensed, the loop 140.7047 bar a; on the shell's effectiveness
    — UA-limited, NTU 0.19 — 0.9971 and 115.3 kg/h, 140.7007 bar a, the duty 5313.7 kW, that
    fraction of the 5329.5 demanded, and TT-329125 95.428 C."""
    def act(k, plant, s):
        if k == 0:
            plant.units["322E003"].effectiveness_capacity = True
        if k == 5:
            plant.loops["322E003"][0].fic_sp = s.FIC["sp"] = 250.0
    hist, _, _ = h.run_both(v1, 1201, act, decided=h.ALL, check=False)
    parted = next(k for k, (out, res, _) in enumerate(hist)
                  if res["322E003"].rho_cond != out.rho_cond)
    assert parted == 6
    out, res, p_v1 = hist[1200]
    sc = res["322E003"]
    assert (out.rho_cond, out.scrub["uncond_kgh"], p_v1) == (
        pytest.approx(0.96947, abs=1e-5), pytest.approx(631.0, abs=0.1),
        pytest.approx(140.7047, abs=1e-4))
    assert (sc.rho_cond, sc.scrubber.uncond_kgh, res["PT-329201"].p_syn_bara) == (
        pytest.approx(0.99705, abs=1e-5), pytest.approx(115.3, abs=0.1),
        pytest.approx(140.7007, abs=1e-4))
    assert sc.ccw.m_ccw_kgh == pytest.approx(296659.0, abs=1.0)
    assert sc.scrubber.q_ccw_kw == pytest.approx(5313.7, abs=0.1)
    assert sc.scrubber.t_ccw_out_c == pytest.approx(95.428, abs=1e-3)


def test_322e001s_duty_bounded_by_its_shell_decided_divergence(v1):
    """B-102, decided 2026-10-21: 322E001's split bounded by the duty its shell transfers at the live
    steam's LMTD against the tube side's design profile, against V1's unbounded split (the
    transcription). HV-322605 60 -> 100 % at 0.5 s: the two part on the tick after, when the drained
    liquor asks V1's split for 1.584 design duties, which V1 books on the MP header. The port's shell
    gives 1.0005 of its design duty at the live steam (capacity 1.000007): lambda 0.6347 lifts
    147.4 t/h overhead where V1 lifts 200.8, and the bottoms leave with 21.37 % NH3 where V1's leave
    with 11.43 %. Ten seconds on V1's split asks 3.13 duties and its loop stands at 145.258 bar a;
    the port's lambda is 0.508 and its loop 140.689. Before the step the two are identical: the
    seed's own drift stays inside the band."""
    from ureasim.units.synthesis.stripper import DUTY_RAW_DES_KW

    def act(k, plant, s):
        if k == 0:
            plant.units["322E001"].shell_bound = True
        if k == 5:
            plant.operator["HIC-322605"] = s.HIC_322605 = 100.0
    hist, _, _ = h.run_both(v1, 101, act, decided=h.ALL, check=False)
    parted = next(k for k, (out, res, _) in enumerate(hist)
                  if res["322E001"].stripper.top_kmolh != out.strip["top_kmolh"])
    assert parted == 6
    out, res, _ = hist[6]
    st = res["322E001"].stripper
    assert out.strip["duty_raw_kw"] == st.duty_demand_raw_kw
    assert st.duty_demand_raw_kw / DUTY_RAW_DES_KW == pytest.approx(1.58445, abs=1e-5)
    assert (st.shell_capacity_ratio, st.duty_raw_kw / DUTY_RAW_DES_KW, st.shell_lambda) == (
        pytest.approx(1.000007, abs=1e-6), pytest.approx(1.000507, abs=1e-6),
        pytest.approx(0.63473, abs=1e-5))
    assert (out.strip["top_kgh"], st.top_kgh) == (pytest.approx(200845.6, abs=0.1),
                                                 pytest.approx(147381.0, abs=0.1))
    assert (out.strip["bot_mass_pct"]["NH3"], st.bot_mass_pct["NH3"]) == (
        pytest.approx(11.434, abs=1e-3), pytest.approx(21.375, abs=1e-3))
    out, res, p_v1 = hist[100]
    st = res["322E001"].stripper
    assert out.strip["duty_raw_kw"] / DUTY_RAW_DES_KW == pytest.approx(3.1302, abs=1e-4)
    assert st.shell_lambda == pytest.approx(0.50796, abs=1e-5)
    assert (p_v1, res["PT-329201"].p_syn_bara) == (pytest.approx(145.2592, abs=1e-4),
                                                   pytest.approx(140.6887, abs=1e-4))


def test_322e001s_full_sump_holds_its_excess_back_decided_divergence(v1):
    """B-103, decided 2026-10-21 (decision 62's class): a full LT-322501 sump's excess held back in the
    tubes above it, against V1's clamp (the transcription's sump, the switch off). LIC-322501 in MAN,
    LV-322501 46.1 -> 10 % at 0.5 s (S2-2.3b): the sump fills at about 100 t/h net and is full at
    140.2 s on both sides. V1 clamps the level at 100 % and deletes what runs in after — and
    PT-329201's vapour balance, which books the sump's gain as liquid, counts the deleted liquor as
    gas: 80 s on, its loop stands at 141.995 (141.997 before decision 170) bar a. The port holds 2 223 kg back in the tubes, books
    it as liquid, and its loop stands at 141.041. Without the tubes' ceiling and their submergence
    (B-104, its own test)."""
    def act(k, plant, s):
        if k == 0:
            plant.units["322E001"].hold_full = True
        if k == 5:
            for lic in (plant.loops["322E001"][0], s.lic):
                lic.mode, lic.op = "MAN", 10.0
    hist, _, _ = h.run_both(v1, 2201, act, decided=h.ALL, check=False)
    full = next(k for k, (_, res, _) in enumerate(hist) if res["322E001"].sump.level_pct >= 100.0)
    assert full == 1402 and hist[full][0].sump.level_pct == 100.0
    assert hist[full - 1][1]["PT-329201"].p_syn_bara == hist[full - 1][2]
    out, res, p_v1 = hist[2200]
    sp = res["322E001"].sump
    assert (out.sump.level_pct, out.sump.held_kg) == (100.0, 0.0)
    assert (sp.level_pct, sp.held_kg) == (100.0, pytest.approx(2223.71, abs=0.01))
    assert (p_v1, res["PT-329201"].p_syn_bara) == (pytest.approx(141.9946, abs=1e-4),
                                                   pytest.approx(141.0387, abs=1e-4))


def test_322e001s_tubes_standing_full_hold_the_liquor_back_in_the_reactor_decided_divergence(v1):
    """B-104, decided 2026-10-22 (decision 62's class): the liquor a full LT-322501 sump holds back in
    the tubes capped at the bundle standing full, 322R001 discharging no more than the tubes take —
    the drain and their unsubmerged share of the design bottoms — and the submerged share derating
    the shell and cooling the bottoms toward the crystallisation floor; against V1's clamp (the
    transcription's sump, the switches off). LIC-322501 in MAN, LV-322501 46.1 -> 10 % at 0.5 s
    (S5-5a): the sump is full at 140.2 s on both sides. From 218.2 s the tubes' take caps HV-322605;
    ten minutes on the tubes hold 8 403.2 kg (sigma 0.967), the reactor discharges 26.3 t/h where V1's
    discharges its 226.2: LV-322501's drain at 10 % is this scenario's most sensitive quantity, 12.2 t/h on
    the LPCC's 1.5 mbar (decision 150), and decision 170's steam valves move the LP side by that much
    (8 392.5 kg, sigma 0.966 and 37.7 t/h, the take 32.7 t/h, before decision 170; 26.3 t/h with PV-323202 on
    V1's 25 % anchor before it). Its level has risen to 85.94 % where V1's stands at 80.34; TT-322004
    reads 141.57 C against 165.59 (165.58 before decision 170). V1's loop climbs to 146.67 bar a — its
    PT-329201 books the liquor its clamp deletes as gas (B-103's finding) — where the port's stands at
    140.01 (140.02 before decision 170). Nothing
    arrives past the ceiling."""
    def act(k, plant, s):
        if k == 0:
            plant.units["322E001"].hold_full = True
            plant.units["322E001"].tube_ceiling = True
        if k == 5:
            for lic in (plant.loops["322E001"][0], s.lic):
                lic.mode, lic.op = "MAN", 10.0
    hist, _, s = h.run_both(v1, 6001, act, decided=h.ALL, check=False)
    full = next(k for k, (_, res, _) in enumerate(hist) if res["322E001"].sump.level_pct >= 100.0)
    assert full == 1402 and hist[full][0].sump.level_pct == 100.0
    capped = next(k for k, (_, res, _) in enumerate(hist) if res["322R001"].m_out_kgh < 226000.0)
    assert capped == 2181
    assert all(res["322E001"].sump.backup_kgh == 0.0 for _, res, _ in hist)
    out, res, p_v1 = hist[6000]
    sp, st, rr = res["322E001"].sump, res["322E001"].stripper, res["322R001"]
    assert (out.sump.held_kg, sp.held_kg) == (0.0, pytest.approx(8403.2, abs=0.1))
    assert st.submerged_frac == pytest.approx(0.9671, abs=1e-4)
    assert (sp.take_kgh, rr.m_out_kgh) == (pytest.approx(20458.1, abs=1.0),
                                           pytest.approx(26284.6, abs=1.0))
    assert (s.react_level_pct, rr.level_pct) == (pytest.approx(80.337, abs=1e-3),
                                                 pytest.approx(85.943, abs=1e-3))
    assert (out.sump.tt_322004_c, sp.tt_322004_c) == (pytest.approx(165.59, abs=0.01),
                                                      pytest.approx(141.57, abs=0.01))
    assert (p_v1, res["PT-329201"].p_syn_bara) == (pytest.approx(146.6702, abs=1e-4),
                                                   pytest.approx(140.0065, abs=1e-4))


def test_the_melts_bubble_pressure_rises_below_its_azeotrope_decided_divergence(v1):
    """B-106, decided 2026-10-22: below N/C 3.0 322E002's melt bubbles on the Extended UNIQUAC
    model's rise toward its azeotrope, added in bar (B-111), against V1's K_N line, which falls.
    The CO2 boundary +20 % at 0.5 s with 321P002B held (SIC-321951 in MAN): 4.5 s on, the melt
    stands at N/C 2.615 on the port and bubbles at 162.97 bar a, so it holds 72 % of what it would
    condense; V1's, condensing everything, falls to N/C 2.515 and 135.09 bar a (the transcription
    reads the port's 308 and LP header, so its side moves with the port's). 100 s on, the port's
    melt condenses 82.2 t/h where V1's condenses 198.8, and PT-329201 stands at 147.58 bar a
    against 141.02; the port's loop reaches V1's trip 22.2 set point, 155 bar a, at 191.3 s and,
    with no such trip (decision 189), stands at 155.75 bar a 8.7 s later, where V1's stands at
    141.69 bar a. At 100 s the port's condensation falls 100 to 15 t/h in two seconds, ringing
    tick to tick: decision 224's melt header, draining PFD 402 exactly where V1's selector drained
    3 kg/h less, moves it a few ticks (74.6 t/h, 190.5 s and 155.68 bar a before it; As-Built
    §CXXI.7), and LV-324501A's positioner and sheet inlet (decisions 236 and 237) a few more
    (89.1 t/h, 147.59 bar a, 192.2 s and 155.81 bar a before them; As-Built §CXXVI.5).
    (Both sides measured on 2026-11-12; until then the port's 22.2 latched on its next
    tick, 190.7 s, and V1's side, reading the port's, stood at 141.72) (the session-69 valves and
    322E006's water upstream, decisions 150
    and 151, move the loop's feed in this fast transient: 101.9, 198.6, 147.64, 192.7 s and 141.72 (141.70 before decision 178)
    before them)."""
    def act(k, plant, s):
        if k == 0:
            plant.units["322E002"].low_nc_branch = True
            plant.units["321"].sic_b.set_mode("MAN")
        if k == 5:
            plant.operator["320K002-CO2"] *= 1.2
            s.co2_raw_th *= 1.2
    hist, _, _ = h.run_both(v1, 2001, act, decided=h.ALL, check=False)
    out, res, _ = hist[50]
    c = res["322E002"].holdup
    assert (c.condenser.melt_nc, out.hpcc["L_hpcc"]) == (pytest.approx(2.6159, abs=1e-4),
                                                         pytest.approx(2.5162, abs=1e-4))
    assert (c.condenser.p_bub_bara, out.hpcc["P_bub"]) == (pytest.approx(162.928, abs=1e-3),
                                                           pytest.approx(135.140, abs=1e-3))
    assert c.sat_frac == pytest.approx(0.72390, abs=1e-5)
    out, res, p_v1 = hist[1000]
    assert (res["322E002"].holdup.condenser.liq_th, out.hpcc["liq_th"]) == (
        pytest.approx(82.25, abs=0.01), pytest.approx(198.76, abs=0.01))
    assert (p_v1, res["PT-329201"].p_syn_bara) == (pytest.approx(141.0214, abs=1e-4),
                                                   pytest.approx(147.5780, abs=1e-4))
    over = next(k for k, (_, res, _) in enumerate(hist) if res["PT-329201"].p_syn_bara >= 155.0)
    assert over == 1913 and hist[2000][2] == pytest.approx(141.6936, abs=1e-4)
    assert hist[2000][1]["PT-329201"].p_syn_bara == pytest.approx(155.7516, abs=1e-4)


def test_323d001s_liquor_reaches_322e003_as_it_is_decided_divergence(v1):
    """B-105, decided 2026-10-22: 323D001 carries its species into PFD 308 and 322E003 washes with
    308's live composition and temperature, against V1's mass-only LPCC (the transcription washes
    with PFD 308's design carbamate, scaled by the 308 the LPCC delivers). FIC-323401 in MAN,
    FV-323401 to 100 % at 0.5 s: about 7 000 kg/h of 328D003's ammonia water into 323E003, which
    both sides take in through the same LPCC. Four minutes on, 308 carries 33.45 % water where PFD
    308 has 30.83; the reactor's feed H/C stands at 0.4142 on the port against V1's 0.4014,
    TT-322002 at 163.41 C against 164.13, the conversion at 53.78 % against 53.96 %, and PT-329201 at
    140.7167 (140.7174 before decision 170) bar a against 140.7109 (140.7116 before decision 170)."""
    from ureasim.engine.command import apply_command

    def act(k, plant, s):
        if k == 0:
            plant.units["323E003"].track_species = True
        if k == 5:
            apply_command(plant, {"type": "r323_ctrl_set", "id": "FIC-323401", "mode": "MAN",
                                  "op": 100.0}, None)
    hist, _, _ = h.run_both(v1, 2401, act, decided=h.ALL, check=False)
    out, res, p_v1 = hist[2400]
    assert res["323E003"].w_308["H2O"] == pytest.approx(0.33447, abs=1e-5)
    rr = res["322R001"].reaction
    assert (out.react["W_feed"], rr.w_feed) == (pytest.approx(0.40137, abs=1e-5),
                                                pytest.approx(0.41412, abs=1e-5))
    assert (out.scrub["T_overflow"], res["322E003"].scrubber.t_overflow_c) == (
        pytest.approx(164.141, abs=1e-3), pytest.approx(163.415, abs=1e-3))
    assert (out.react["X_conv"], rr.x_conv) == (pytest.approx(0.53947, abs=1e-5),
                                                pytest.approx(0.53774, abs=1e-5))
    assert (p_v1, res["PT-329201"].p_syn_bara) == (pytest.approx(140.7109, abs=1e-4),
                                                   pytest.approx(140.7167, abs=1e-4))


def test_308s_composition_reaches_322e003_a_line_residence_late_decided_divergence():
    """B-110, decided 2026-10-22: PFD 308's line from 323P001A to 322E003/N5 on its isometrics
    (MB-0017 and MB-0015, 47.8 m of 74.7 mm bore, 24.94 s at the design 36.8 t/h) delivers its flow
    at once and 323D001's composition and temperature a line residence late (B-21's class); V1's
    side of it is B-105's tear, the wash a tick late. Both ports on B-105, FV-323401 in MAN to 100 %
    at 0.5 s: the step's water reaches the wash 25 s on, so at 25.5 s TT-322002 has fallen 0.0056 K
    on the line against 0.045 on the tear and the reactor feed's H/C has risen 0.00004 against 0.0010;
    at one minute TT-322002 stands at 164.9186 C against 164.8959 (164.8961 before decision 178) (164.8960 before decision 170) and the H/C at 0.39989 against
    0.40102."""
    from ureasim.engine.command import apply_command

    sides = []
    for line in (False, True):
        sched, plant = h.harness_plant()
        plant.units["323E003"].track_species = True
        plant.units["322E003"].wash_line = line
        sides.append((sched, plant))
    hist = []
    for k in range(601):
        reps = []
        for sched, plant in sides:
            if k == 5:
                apply_command(plant, {"type": "r323_ctrl_set", "id": "FIC-323401", "mode": "MAN",
                                      "op": 100.0}, None)
            reps.append(sched.tick().results)
        hist.append([(r["322E003"].scrubber.t_overflow_c, r["322R001"].reaction.w_feed)
                     for r in reps])
    assert hist[0][0] == hist[0][1]
    t0, w0 = hist[5][1][0], hist[5][1][1]
    tear, line = hist[255]
    assert (t0 - tear[0], t0 - line[0]) == (pytest.approx(0.0450, abs=1e-4),
                                            pytest.approx(0.0055, abs=1e-4))
    assert (tear[1] - w0, line[1] - w0) == (pytest.approx(0.00104, abs=1e-5),
                                            pytest.approx(0.00004, abs=1e-5))
    tear, line = hist[600]
    assert (tear[0], line[0]) == (pytest.approx(164.8959, abs=1e-4),
                                  pytest.approx(164.9186, abs=1e-4))
    assert (tear[1], line[1]) == (pytest.approx(0.40102, abs=1e-5), pytest.approx(0.39989, abs=1e-5))


def test_the_reactors_pt_on_its_feed_lines_design_drop_decided_divergence():
    """B-112, decided 2026-10-22: PT on 322R001 on its feed line's PFD drop, 144.2 - 141.3 at the
    seed's feed, reads PFD 203/207's 141.3 bar a at the design seed to the bit, where V1's
    ``p_syn - 144.2`` line reads 136.12. It is a published reading only: two harness plants with
    only the line switched run 5 s with every other reactor output identical, the reading 5.18 bar
    apart throughout."""
    sides = []
    for drop in (False, True):
        sched, plant = h.harness_plant()
        plant.units["322R001"].design_drop = drop
        sides.append(sched)
    for k in range(50):
        theirs, ours = (sched.tick().results["322R001"] for sched in sides)
        if k == 0:
            assert (theirs.p_bara, ours.p_bara) == (pytest.approx(136.1207, abs=1e-4), 141.3)
        assert ours.p_bara - theirs.p_bara == pytest.approx(5.179, abs=1e-3), k
        assert _rest_of_322r001(theirs) == _rest_of_322r001(ours), k


def _rest_of_322r001(r) -> tuple:
    """The reactor's outputs other than its published PT."""
    return (r.overflow_kmolh, r.reaction.offgas_kmolh, r.t_nodes_c, r.p_offgas_bara, r.level_pct)
