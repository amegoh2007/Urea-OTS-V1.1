"""Dynamic and closed-loop audits of the assembled plant (session 73).

What this audits
----------------
The equivalence suites prove each unit against V1 and the unit suites pin each mechanism; these
four audits put the plant the console runs through transients and check what no single unit's test
can:

1. **Conservation.** A minute of a multi-unit disturbance: the liquid holdups the loop node and
   328D001 integrate close on their own flows tick by tick, each holdup's published accumulation
   sums to its inventory's change, the selector's and the vacuum condensers' residuals stay zero,
   and nothing published is non-finite.
2. **Control and safety logic.** Each trip initiator's path on the running plant: 21.2 by its trip
   switch, carrying 21.8 and 21.10; 22.2 and 323P008's L2 on their measurements injected; 22.1 on
   its limit, which a process path reaches only after about twenty minutes. And the updated
   controllers' transfers: PIC-329205's PI and TIC-328008 on their rows leaving their limits on the
   first reversed tick (velocity forms, no windup), MAN to AUTO bumpless, FFIC-335406's ratio station
   tracking while its slave is out of cascade. TIC-328008, like every V1 cascade master, keeps
   integrating while its slave is out of cascade: the slave's set point jumps on re-entry (handoff
   B-117).
3. **Transient fidelity.** The synthesis shut down by 21.2 with LV-322501 forced wide open, run at
   FAST: no simulator fault, no pressure node ringing, every evaporator stage's fixed point solved,
   and SV32351 / SV32352 lifting at their set (B-114).
4. **OTS integrity.** Freeze, snapshot, reload and resume through the engine session at FAST, the
   resumed plant the saved one's to the bit; and a seeded fuzz of simultaneous malfunctions with no
   exception, no non-finite value and no packet key lost or gained.

Every figure was measured on the plant before it was written down (As-Built Part LXXXVIII).
"""

from __future__ import annotations

import math
import random
from types import SimpleNamespace

import pytest

from ureasim.data import desorption_train as t
from ureasim.data import unit_324 as d324
from ureasim.data import unit_328c002 as c2
from ureasim.data import unit_328d001 as d
from ureasim.data.unit_322_loop import SYN_P_DES_BARA
from ureasim.data.unit_322e001 import RHO_BOTTOM
from ureasim.data.unit_323c003 import SV32351_SET_BARA
from ureasim.data.unit_323e011 import D011_LVL_SP_PCT, D011_M_DES_KG
from ureasim.engine import snapshot
from ureasim.engine.command import apply_command
from ureasim.engine.historian import flatten
from ureasim.engine.packet import build_packet
from ureasim.engine.plant import build_plant
from ureasim.engine.scheduler import Scheduler
from ureasim.engine.session import EngineSession
from ureasim.engine.simulator import Simulator
from ureasim.thermo import condensing_letdown
from ureasim.units.desorption import reflux_drum as rd
from ureasim.units.finishing import uf85_dosing as uf
from ureasim.units.synthesis.condenser_holdup import E002_SPAN_KG

DT = 0.1


def _plant(settle: int = 20) -> Scheduler:
    sched = Scheduler(*build_plant())
    for _ in range(settle):
        sched.tick()
    return sched


def _ok(sched: Scheduler, **cmd):
    r = apply_command(sched.plant, cmd, sched.results)
    assert r.ok, (cmd, r.reason)
    return r


def _packet(sched: Scheduler) -> dict:
    return flatten(build_packet(sched.plant, sched.results, sched.tears_read, sim_mode="SLOW",
                                t_wall=0.0))


def _non_finite(flat: dict) -> list:
    return [p for p, v in flat.items() if isinstance(v, float) and not math.isfinite(v)]


# ======================================================================================
# 1. Conservation
# ======================================================================================

def _inventories(units: dict) -> dict:
    """What each audited holdup holds [kg]."""
    sump, e003 = units["322E001"], units["322E003"]
    return {"322E001": sump.level_pct / 100.0 * sump.bundle.v_sump_m3 * RHO_BOTTOM + sump.held_kg,
            "322E002": units["322E002"].level_pct / 100.0 * E002_SPAN_KG,
            "322E003": e003.holdup_kg + e003.held_kg,
            "328D001": units["328D001"].m_kg}


@pytest.fixture(scope="module")
def disturbed():
    """A minute of 320K002's CO2 cut a fifth, HV-322605 throttled to 45 %, 329P006A stopped and a
    5 t/h tube leak in 322E002, from five seconds after the seed; each tick's closures recorded."""
    sched = _plant(50)
    units = sched.plant.units
    _ok(sched, type="co2_set", value=0.8 * sched.plant.operator["320K002-CO2"])
    _ok(sched, type="hic605_set", op=45.0)
    _ok(sched, type="pump_toggle", id="329P006A", on=False)
    _ok(sched, type="trigger_fault", id="322E002", value=5.0)
    out = SimpleNamespace(closure={"322E001": 0.0, "328D001": 0.0}, booked={}, start=None,
                          end=None, non_finite=[])
    out.start = _inventories(units)
    booked = dict.fromkeys(("322E001", "322E002", "322E003"), 0.0)
    for k in range(600):
        pre = _inventories(units)
        r = sched.tick().results
        post = _inventories(units)
        s, dr = r["322E001"].sump, r["328D001"]
        flows = {"322E001": s.bottoms_in_kgh - s.drain_kgh - s.backup_kgh,
                 "328D001": dr.in_kgh - dr.gen_kgh - dr.m_775_kgh - dr.m_776_kgh
                 - dr.m_overflow_kgh}
        for tag, net in flows.items():
            out.closure[tag] = max(out.closure[tag], abs(post[tag] - pre[tag] - net * DT / 3600.0))
        for tag, dm in (("322E001", s.dm_kgh), ("322E002", r["322E002"].holdup.dm_kgh),
                        ("322E003", r["322E003"].sump.dm_kgh)):
            booked[tag] += dm * DT / 3600.0
        if k % 10 == 9:
            out.non_finite += [(k, p) for p in _non_finite(flatten(r))]
    out.end, out.booked, out.packet = _inventories(units), booked, _packet(sched)
    return out


def test_the_holdups_close_on_their_own_flows(disturbed):
    """322E001's sump and 328D001 gain, on every tick, exactly what their published flows bring
    less what they send (the sump's bottoms in, drain and backup; the drum's inlets, the vapour it
    makes, the reflux, the draw and an overflow): 9e-13 and 2e-13 kg at most, rounding."""
    assert disturbed.closure["322E001"] < 1.0e-9
    assert disturbed.closure["328D001"] < 1.0e-9


def test_the_loop_books_what_its_holdups_hold(disturbed):
    """The accumulation each synthesis holdup publishes, which PT-329201's node takes as the loop's
    liquid growth, sums over the minute to the holdup's own change: no uncompensated drift between
    what the node books and what the vessels hold (322E001's sump lost 316.59 kg; 317.36 with the
    balanced Neldiscs on the chord, before decision 170, 2026-11-06)."""
    for tag, booked in disturbed.booked.items():
        change = disturbed.end[tag] - disturbed.start[tag]
        assert booked == pytest.approx(change, abs=1.0e-6), tag
    assert disturbed.end["322E001"] - disturbed.start["322E001"] == pytest.approx(-316.590,
                                                                                    abs=1e-3)


def test_nothing_published_is_non_finite_and_the_residuals_stay_zero(disturbed):
    """Every result field, every tenth tick, is finite; LV-324501's selector closes mass, species and
    energy to the bit and the four vacuum condensers close theirs, through the disturbance."""
    assert disturbed.non_finite == []
    p = disturbed.packet
    assert _non_finite(p) == []
    assert p["EVAP_324.E003.route_mass_residual_kgh"] == 0.0
    assert p["EVAP_324.E003.route_energy_residual_kw"] == 0.0
    for tag in ("324E002", "324E005", "324E006", "324E007"):
        assert p[f"EVAP_324.VAC.{tag}.mass_residual_kgh"] == 0.0, tag
        assert p[f"EVAP_324.VAC.{tag}.energy_residual_kW"] == 0.0, tag


# ======================================================================================
# 2. Control and safety logic
# ======================================================================================

def test_trip_21_2_by_its_switch_carries_21_8_and_21_10_and_stops_the_pumps():
    """HS-321603 turned (AC4 PC21.5.1): on the next ticks 21.2's flag is lost, both pumps' flags
    with it, 321P002A / B stopped, and the packet's latches say so. Released, the flags stay lost —
    no HP ammonia pump runs, 21.2's own input — and a start is refused naming the flag."""
    sched = _plant()
    trips, st = sched.plant.units["SYN-TRIPS"], sched.plant.units["321"]
    _ok(sched, type="keyswitch_set", id="HS-321603", on=True)
    for _ in range(3):
        sched.tick()
    assert trips.latched == {"21_2": True, "21_8": True, "21_10": True, "22_2": False}
    assert (st.pump_a.running, st.pump_b.running) == (False, False)
    p = _packet(sched)
    assert [p[f"trip_latched.{k}"] for k in ("21_2", "21_8", "21_10")] == [True] * 3
    _ok(sched, type="keyswitch_set", id="HS-321603", on=False)
    for _ in range(3):
        sched.tick()
    assert trips.latched["21_2"] and not st.pump_a.running
    r = apply_command(sched.plant, {"type": "pump_toggle", "id": "A", "on": True}, sched.results)
    assert not r.ok and "21.8" in r.reason


def test_trip_22_2_latches_on_its_pressure_and_resets_only_below_its_band():
    """PT-329201 injected at 165 bar a, over 22.2's 155: latched on the tick, 320K002's demand
    refused, the reset refused while the cause is live; at the design's 140.7, below the 148 reset
    band, the reset is taken."""
    sched = _plant()
    loop, trips = sched.plant.units["PT-329201"], sched.plant.units["SYN-TRIPS"]
    loop.p_syn_bara = 165.0
    sched.tick()
    assert trips.i_22_2.latched
    r = apply_command(sched.plant, {"type": "co2_set", "value": 50.0}, sched.results)
    assert not r.ok and "320K002 is tripped by trip 22.2" in r.reason
    r = apply_command(sched.plant, {"type": "trip_reset", "id": "22_2"}, sched.results)
    assert not r.ok and "still live" in r.reason
    loop.p_syn_bara = SYN_P_DES_BARA
    sched.tick()
    _ok(sched, type="trip_reset", id="22_2")
    assert not trips.i_22_2.latched


def test_trip_22_1_floods_the_vent_line_until_its_keyswitch_closes_it():
    """I 22.1 on TT-322015 over its 110 C (injected: the line runs at 50 C, and a process path
    takes twenty minutes): XV-322915 opens and the next tick floods the line with its rated 1000
    kg/h, 961.6 five seconds on as the 9-bar header gives. TI-322015 stands downstream of the
    injection, so the steam holds it over the limit and the valve open; HS-322915, its OVERRIDE
    CLOSE (B-59), shuts it whatever the limit says, and the line cools below the 108 C clear."""
    sched = _plant()
    trips = sched.plant.units["TRIPS"]
    assert trips.step(111.0, False).xv_322915_open
    assert sched.tick().results["322C001"].m_flood_kgh == pytest.approx(1000.0, abs=1e-3)
    for _ in range(50):
        r = sched.tick().results
    assert r["322C001"].m_flood_kgh > 900.0 and r["322C001"].t_ti_322015_c > 108.0
    assert trips.i_22_1.latched and trips.xv_322915_open
    _ok(sched, type="keyswitch_set", id="HS-322915", on=True)
    for _ in range(50):
        r = sched.tick().results
    assert not trips.xv_322915_open and r["322C001"].m_flood_kgh == 0.0
    assert r["322C001"].t_ti_322015_c < 108.0 and not trips.i_22_1.latched


def test_323p008_stops_on_lt_323503s_l2_and_runs_again_above_its_hysteresis():
    """LT-323503 injected at 3 %, under its 5 % L2 (B-93): AC4 stops 323P008A / B on the tick, 718A
    with them; the tank refills on its inflows and the pumps run again 48.1 s on, the level past
    the 2 % stand-in hysteresis (B-96)."""
    sched = _plant()
    fc = sched.plant.units["323E011"]
    fc.m_kg = 0.03 / (D011_LVL_SP_PCT / 100.0) * D011_M_DES_KG
    r = sched.tick().results
    assert fc.p008_tripped and r["323E011"].m_718a_kgh == 0.0
    for k in range(1, 1201):
        sched.tick()
        if not fc.p008_tripped:
            break
    assert k * DT == pytest.approx(48.1, abs=0.15)
    assert fc.m_kg / D011_M_DES_KG * D011_LVL_SP_PCT >= 7.0


def test_pic_329205s_pi_is_bumpless_from_man_and_leaves_its_limit_at_once():
    """PIC-329205 on its row (decision 156): in MAN the split tracks the strokes, so AUTO takes over
    on the stroke it found; driven to PV-329205A's 100 % by a sustained error, the velocity form
    leaves the limit on the first tick the error reverses — nothing wound up behind it."""
    pic = build_plant()[1].units["329"].pic_329205
    pic.mode, pic.op_a_pct, pic.op_b_pct = "MAN", 40.0, 0.0
    pic.step(pic.sp_bara, DT)
    pic.mode = "AUTO"
    assert pic.step(pic.sp_bara, DT) == (40.0, 0.0)
    for _ in range(600):
        pic.step(pic.sp_bara - 5.0, DT)
    assert (pic.split_pct, pic.op_a_pct) == (100.0, 100.0)
    a, b = pic.step(pic.sp_bara + 1.0, DT)
    assert a < 100.0 or b > 0.0


def _drum():
    """328D001 and its loops alone on the design's boundaries, settled a second."""
    drum, loops = rd.RefluxDrum(), rd.RefluxDrumLoops()
    x = (t.C002_M737_DES_KGH, t.C002_T_BOT_C, t.C002_P_TOP_BARA, c2.C002_M_DES_KG,
         t.C002_IN_DES_KGH, 0.0, d.D001_M718A_DES_KGH, 0.0, 56.0, d.PV202_P2_BARA)

    def step():
        return drum.step(loops, *x, DT)
    for _ in range(10):
        step()
    return loops, step


def test_tic_328008_leaves_its_limit_at_once_and_bumps_its_slave_on_cas_re_entry():
    """TIC-328008 on its faceplate's row (decision 160). Its velocity form leaves its 4000 kg/h
    limit on the first reversed tick. But as every V1 cascade master it integrates while its slave
    is out of cascade: FIC-328404 in AUTO, the set point moved to 48 mol%, the reflux it would ask
    winds from 1675 to 917.96 kg/h in five minutes against a PV the slave no longer moves, and the
    return to CAS steps FIC-328404 from 1.5297 to 0.8381 m3/h (V1 ``_ctrl_ipd``; handoff B-117)."""
    loops, step = _drum()
    tic, fic = loops.tic_328008, loops.fic_328404.loop
    for _ in range(1500):
        tic.step(tic.sp + 10.0, DT)
    assert tic.op == d.TIC_328008_OP_HI_KGH
    assert tic.step(tic.sp - 10.0, DT) < d.TIC_328008_OP_HI_KGH
    loops, step = _drum()
    tic, fic = loops.tic_328008, loops.fic_328404.loop
    fic.mode, tic.sp = "AUTO", 48.0
    for _ in range(3000):
        step()
    assert tic.op == pytest.approx(917.958, abs=1e-3) and fic.sp == pytest.approx(1.529680,
                                                                                   abs=1e-6)
    fic.mode = "CAS"
    step()
    assert fic.sp == pytest.approx(0.838088, abs=1e-6)


def test_ffic_335406_tracks_while_its_slave_is_out_of_cascade_and_returns_bumplessly():
    """FFIC-335406's ratio station (decision 160): FIC-335405 in MAN at 40 % delivers 555.2 kg/h,
    and the station's ratio set point follows what the plant makes, 0.0073112, inside RAT H; back
    in CAS the slave is handed exactly the flow it has, so nothing moves."""
    station, slave = uf.ffic_335406(), uf.fic_335405()
    slave.loop.mode, slave.loop.op = "MAN", 40.0
    for _ in range(600):
        r = uf.uf85_step(station, slave, d324.P2_DES_KGH, d324.W_S402, 140.0, False, DT)
    assert station.sp == r.measured_ratio == pytest.approx(0.0073112, abs=1e-7)
    pv = slave.loop.pv
    slave.loop.mode = "CAS"
    r = uf.uf85_step(station, slave, d324.P2_DES_KGH, d324.W_S402, 140.0, False, DT)
    assert slave.loop.sp == pytest.approx(pv, rel=1e-12)
    assert r.delivered_kgh == pytest.approx(555.2, abs=1e-9)


def test_the_updated_faceplates_enter_auto_bumpless():
    """MAN to AUTO from the console on TIC-328008 and FFIC-335406 adopts the PV as the set point,
    so the loop resumes on what it measures (the faceplate handler's transfer) — FFIC-335406's
    within its RAT H: the design's 0.008126 enters AUTO as 0.0080."""
    sched = _plant(1)
    for tag, op in (("TIC_328008", 1500.0), ("FFIC_335406", 0.5)):
        _ok(sched, type="r323_ctrl_set", id=tag, mode="MAN", op=op)
        _ok(sched, type="r323_ctrl_set", id=tag, mode="AUTO")
    loops = sched.plant.loops
    tic, station = loops["328D001"][0].tic_328008, loops["335"][0]
    assert (tic.mode, tic.sp) == ("AUTO", tic.pv)
    assert (station.mode, station.sp) == ("AUTO", min(station.pv, station.sp_hi))
    assert station.sp == 0.0080


# ======================================================================================
# 3. Transient fidelity and solver stability
# ======================================================================================

def _pressures(r: dict) -> dict:
    return {"PT-329201": r["PT-329201"].p_syn_bara, "PT-323201": r["323C003"].p_bara,
            "329D005": r["329"].p_hp_bara, "329D009": r["329"].p_9_bara,
            "LP header": r["329"].p_lp_bara, "323F010": r["323F010"].p_bara}


def test_a_fast_shutdown_with_lv_322501_wide_open_stays_stable():
    """Trip 21.2 by its switch and LV-322501 forced wide open, two minutes at FAST on irregular
    passes: no step faults; no pressure node rings — never more than two successive reversals of
    its step (decision 78); stage 1's and stage 2's fixed points settle, or stage 2 takes its
    bracketed root (decision 144), on every tick; and the blow-through lifts SV32351 / SV32352 at
    their 6.01 bar a set (B-114: 35 ticks lifted, PT-323201 to 6.0205)."""
    sched = Scheduler(*build_plant())
    seen = []

    def step(dt: float) -> None:
        r = sched.tick(dt).results
        seen.append((_pressures(r), r["324E001"].converged,
                     r["324E003"].converged or r["324E003"].bisected, r["323C003"].relief_lifted))

    _ok(sched, type="keyswitch_set", id="HS-321603", on=True)
    _ok(sched, type="lic_set", mode="MAN", op=100.0)
    sim = Simulator(step=step, pacing="FAST")
    passes = (16, 9, 23, 40)
    while sim.steps < 1200:
        sim.advance(passes[sim.steps % len(passes)] * 1_000_000)
    assert sim.fault is None and len(seen) == sim.steps >= 1200
    assert all(s[1] and s[2] for s in seen)
    for name in seen[0][0]:
        xs = [s[0][name] for s in seen]
        assert all(math.isfinite(x) for x in xs), name
        steps = [b - a for a, b in zip(xs, xs[1:])]
        run = longest = 0
        for a, b in zip(steps, steps[1:]):
            run = run + 1 if a * b < 0.0 and min(abs(a), abs(b)) > 1.0e-7 else 0
            longest = max(longest, run)
        assert longest <= 2, name
    lifted = [s for s in seen if s[3]]
    assert lifted and max(s[0]["PT-323201"] for s in seen) >= SV32351_SET_BARA


# ======================================================================================
# 4. OTS features and software integrity
# ======================================================================================

def test_freeze_snapshot_reload_resume_replays_to_the_bit(tmp_path):
    """Through the engine session at FAST: thirty seconds into a transient the plant is frozen —
    the wall clock passes and the plant clock holds — saved, released and run twenty seconds on;
    a second session loads the exercise and runs the same twenty seconds: the two plants are the
    same document to the bit, every published value equal."""
    session = EngineSession(tmp_path)
    assert session.handle({"type": "set_sim_mode", "mode": "FAST"}) == (True, "")
    assert session.handle({"type": "hic605_set", "op": 45.0})[0]
    assert session.handle({"type": "trigger_fault", "id": "322E002", "value": 5.0})[0]
    session.simulator.run(300)
    assert session.handle({"type": "freeze", "on": True}) == (True, "")
    t_frozen = session.t_plant
    assert session.advance(500_000_000) == 0 and session.t_plant == t_frozen
    assert session.handle({"type": "snapshot_save", "name": "audit73"}) == (True, "")
    assert session.handle({"type": "freeze", "on": False}) == (True, "")
    session.simulator.run(200)
    saved = snapshot_text(session)
    condensing_letdown._CACHE.clear()
    resumed = EngineSession(tmp_path)
    assert resumed.handle({"type": "snapshot_load", "name": "audit73"}) == (True, "")
    assert resumed.t_plant == t_frozen
    resumed.simulator.run(200)
    assert snapshot_text(resumed) == saved
    assert flatten(resumed.scheduler.results) == flatten(session.scheduler.results)


def snapshot_text(session: EngineSession) -> dict:
    """The session's plant as a snapshot encodes it, every attribute of every object."""
    return snapshot.encode_state(session.plant)


#: The instructor's and the operator's levers the fuzz draws on: the tube leak, both HP ammonia
#: pumps' faults, the CO2 boundary cut and restored, trip resets, a restart, the tempered water,
#: the melt header over LV-324501B's relief, HV-322605 and 21.2's trip switch.
FUZZ_MENU = (
    {"type": "trigger_fault", "id": "322E002", "value": 8.0},
    {"type": "clear_fault", "id": "322E002"},
    {"type": "trigger_fault", "id": "A"},
    {"type": "trigger_fault", "id": "B"},
    {"type": "clear_fault", "id": "A"},
    {"type": "co2_set", "value": 0.0},
    {"type": "co2_set", "value": 67.0},
    {"type": "trip_reset"},
    {"type": "trip_reset", "id": "22_2"},
    {"type": "pump_toggle", "id": "A", "on": True},
    {"type": "pump_toggle", "id": "329P006A", "on": False},
    {"type": "pic335201_set", "op": 4.0},
    {"type": "pic335201_set", "op": 2.0},
    {"type": "hic605_set", "op": 30.0},
    {"type": "keyswitch_set", "id": "HS-321603", "on": True},
    {"type": "keyswitch_set", "id": "HS-321603", "on": False},
)


def test_simultaneous_malfunctions_break_nothing():
    """A minute of commands drawn every four seconds from `FUZZ_MENU` (seed 73), on top of each
    other: every command is answered — taken or refused with its reason — no tick raises, and every
    packet, every two seconds, is finite and carries exactly the design packet's keys."""
    rng = random.Random(73)
    sched = _plant(1)
    keys = set(_packet(sched))
    for k in range(1, 601):
        if k % 40 == 0:
            r = apply_command(sched.plant, rng.choice(FUZZ_MENU), sched.results)
            assert r.ok or r.reason
        sched.tick()
        if k % 20 == 0:
            p = _packet(sched)
            assert set(p) == keys and _non_finite(p) == [], k
