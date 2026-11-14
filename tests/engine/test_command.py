"""The operator's commands — `ureasim.engine.command`.

V1's ``handle_cmd`` acts on V1's ``State``, which cannot be built outside ``step_sim`` (handoff
A-12), so its command set is checked by its source: every type it handles is answered here. The
semantics are pinned family by family as V1 writes them — the clamps, the bumpless entry into AUTO,
a restart that acknowledges a recovered trip — and so are the refusals the rewrite returns where V1
was silent, each with the process reason the operator reads.
"""

from __future__ import annotations

import math
import re

import pytest

from tests.equivalence.v1_loader import V1_BACKEND, v1_available
from ureasim.data.operator_commands import RUN_STATE_PAIRS
from ureasim.engine.command import PLANT_COMMANDS, SIMULATOR_COMMANDS, apply_command
from ureasim.engine.plant import build_plant
from ureasim.engine.scheduler import Scheduler
from ureasim.units.steam.drums import D005


@pytest.fixture
def plant():
    return build_plant()[1]


def _ok(plant, **cmd):
    r = apply_command(plant, cmd)
    assert r.ok, r.reason
    return r


def _refused(plant, match, **cmd):
    r = apply_command(plant, cmd)
    assert not r.ok and re.search(match, r.reason), r.reason
    return r


@pytest.mark.skipif(not v1_available(), reason="V1 source tree not present")
def test_every_command_v1_handles_is_answered():
    """The types V1's handler branches on, read from its source, are all the plant's or the
    simulator's here, except V1's reset of its trip 22.2, which went with the trip (decision 189,
    a decided divergence: V1 handles it, the rewrite refuses it as unknown), and V1's 335 header
    entry and LV-324501 route switch, which went with the boundary header (decision 224: the header
    is computed, its valves and HIC-335602 the operator's)."""
    src = (V1_BACKEND / "main.py").read_text(encoding="utf-8")
    body = src[src.index("def handle_cmd(cmd: dict):"):src.index("# ----- FastAPI app -----")]
    types = set()
    for line in body.splitlines():
        branch = re.match(r'\s*(?:el)?if t (?:==|in) (.*):', line)
        if branch:
            types |= set(re.findall(r'"([a-z0-9_]+)"', branch.group(1).split(" or ")[0]))
    types.discard("set")                        # the generic form, a fault only
    assert types - set(PLANT_COMMANDS) - SIMULATOR_COMMANDS == {"trip_reset", "pic335201_set",
                                                                "lv324501_route_set"}


def test_hand_valves_clamp_as_v1(plant):
    _ok(plant, type="hic_set", value=150.0)
    _ok(plant, type="co2_set", value=-5.0)
    _ok(plant, type="cpl_set", value=9999.0)
    _ok(plant, type="hic605_set", op=45.0)
    assert (plant.operator["HIC-322602"], plant.operator["320K002-CO2"],
            plant.operator["FIC-322404"], plant.operator["HIC-322605"]) == (100.0, 0.0, 3500.0, 45.0)
    _refused(plant, "needs 'op'", type="hic604_set", value=10.0)
    _refused(plant, "finite", type="hic_set", value=float("nan"))


def test_a_start_is_refused_while_the_pumps_flag_is_lost(plant):
    """321P002B on AC4's logic (handoff A-12, decided 2026-10-09): while TRIP_21_10_FLAG1 is lost
    the start is refused, naming what holds it — 21.2's flag and its bypass, or the pump's own
    inputs; with the flag healthy the start goes and resolves the machine's fault. 21.2, 21.8 and
    21.10 hold no latch to reset."""
    st, trips = plant.units["321"], plant.units["SYN-TRIPS"]
    st.pump_b.running, st.pump_b.fault = False, True
    trips.i_21_2.set_healthy(False)
    trips.i_21_10.set_healthy(False)
    r = _refused(plant, r"trip 21\.10's flag is lost: trip 21\.2's flag is lost .*HS-321634",
                 type="pump_toggle", id="B", on=True)
    assert not st.pump_b.running and r.reason.startswith("321P002B")
    trips.i_21_2.set_healthy(True)
    _refused(plant, r"XV-321901 shut", type="pump_toggle", id="B", on=True)
    trips.i_21_10.set_healthy(True)
    r = _ok(plant, type="pump_toggle", id="B", on=True)
    assert st.pump_b.running and not st.pump_b.fault
    assert "acknowledged 321P002B fault" in r.text
    _ok(plant, type="pump_toggle", id="B", on=False)          # stopping is always allowed
    assert not st.pump_b.running


def test_the_trip_21_2_hand_switches_are_keyswitches(plant):
    """AC4 PC21.5.1's bypasses and trip switches, maintained, released at the seed."""
    for hs in ("HS-321634", "HS-323604", "HS-322606", "HS-321603", "HS-321604"):
        assert plant.operator[hs] is False
        _ok(plant, type="keyswitch_set", id=hs, on=True)
        assert plant.operator[hs] is True
    _refused(plant, "no keyswitch", type="keyswitch_set", id="HS-321999", on=True)


def test_the_tempered_water_pumps_have_no_interlock(plant):
    _ok(plant, type="pump_toggle", id="329P006A", on=False)
    _ok(plant, type="pump_toggle", id="329P006B")
    ccw = plant.loops["322E003"][0]
    assert (ccw.p329p006a, ccw.p329p006b) == (False, True)


def test_trip_reset_went_with_trip_22_2(plant):
    """Decision 189: 22.2 held the only latch an operator reset; AC4's flags and I 22.1 hold none,
    so the command is gone and the synthesis trips carry no 22.2."""
    _refused(plant, "unknown command 'trip_reset'", type="trip_reset", id="21_2")
    assert not hasattr(plant.units["SYN-TRIPS"], "i_22_2")


def test_xv_322915_has_no_operator_open(plant):
    """B-59: XV-322915's only control is HS-322915. (A trip's hold on XV-322902 is 21.2's, below;
    V1's 22.2 hold is gone, decision 189.)"""
    _refused(plant, "no operator open", type="xv_toggle", id="322915")
    _ok(plant, type="keyswitch_set", id="HS-322915", on=True)
    assert plant.operator["HS-322915"] is True
    _ok(plant, type="xv_toggle", id="322903")
    assert plant.operator["XV-322903"] is False


def test_trip_21_2_holds_xv_322902_and_xv_322903_shut(plant):
    """AC4 PC21.5.1 .14 / .15 (decided 2026-10-16): while 21.2's flag is lost, XV-322902 — through
    the Safeguard SG1 — and XV-322903 are held shut beside XV-321901 and XV-322901: the open is
    refused with the flag's name, the close is not, and with the flag back both open again."""
    trips = plant.units["SYN-TRIPS"]
    trips.i_21_2.latched = True
    for xv in ("322902", "322903"):
        _ok(plant, type="xv_toggle", id=xv)                     # close
        _refused(plant, rf"XV-{xv} is held shut by trip 21\.2's flag", type="xv_toggle", id=xv)
    assert plant.units["320K002"].xv_322902_open is False and plant.operator["XV-322903"] is False
    _refused(plant, r"held shut by trip 21\.2's flag", type="co2_set", value=67.0)
    _ok(plant, type="co2_set", value=0.0)
    trips.i_21_2.latched = False
    for xv in ("322902", "322903"):
        _ok(plant, type="xv_toggle", id=xv)
    assert plant.units["320K002"].xv_322902_open is True and plant.operator["XV-322903"] is True
    _ok(plant, type="co2_set", value=67.0)


def test_the_co2_demand_is_refused_only_on_21_2s_flag(plant):
    """B-88's refusal is 21.2's alone (decision 189: V1's 22.2 refusal is gone): with every flag
    healthy a demand is taken."""
    _ok(plant, type="co2_set", value=50.0)
    assert plant.operator["320K002-CO2"] == 50.0


def _v1_co2_step(demand_th: float, direction: int) -> float:
    """V1's 322-1 hand station, ``frontend/co2_compressor.js``, as the browser computed it:
    ``render`` snaps the readout to the demand, ``step`` adds 2 % and sends ``toFixed(3)``."""
    js_round = lambda v: math.floor(v + 0.5)                       # noqa: E731  Math.round
    clamp = lambda v: max(0.0, min(120.0, v))                      # noqa: E731
    pct = clamp(js_round(demand_th / 54.618 * 100 * 10) / 10)
    pct = clamp(js_round((pct + 2.0 * direction) * 10) / 10)
    return float(f"{54.618 * pct / 100:.3f}")


def test_the_co2_feed_panel_steps_the_demand_as_v1s_did(plant):
    """Decision 220: one press is 2 % of the 54.618 t/h design; UP then DOWN returns the design
    demand to the bit; an off-grid demand is snapped onto the 0.1 % grid before the step, as V1's
    readout snapped it; the demand stops at 120 % and at none. Over the whole 0.1 % grid each step
    is V1's own."""
    assert plant.operator["320K002-CO2"] == 54.618
    r = _ok(plant, type="co2_step", dir=1)
    assert plant.operator["320K002-CO2"] == 55.71 and "102.0 %" in r.text
    _ok(plant, type="co2_step", dir=-1)
    assert plant.operator["320K002-CO2"] == 54.618
    _ok(plant, type="co2_set", value=50.0)                         # 91.545 %: snapped to 91.5
    _ok(plant, type="co2_step", dir=1)
    assert plant.operator["320K002-CO2"] == 51.068
    _ok(plant, type="co2_set", value=64.995)                       # 119.0 %
    for _ in range(2):
        _ok(plant, type="co2_step", dir=1)
        assert plant.operator["320K002-CO2"] == 65.542            # 120.0 %
    _ok(plant, type="co2_set", value=0.5)                          # 0.9 %
    for _ in range(2):
        _ok(plant, type="co2_step", dir=-1)
        assert plant.operator["320K002-CO2"] == 0.0
    for tenth in range(0, 1201):
        start = float(f"{54.618 * tenth / 1000:.3f}")
        for direction in (-1, 1):
            plant.operator["320K002-CO2"] = start
            _ok(plant, type="co2_step", dir=direction)
            assert plant.operator["320K002-CO2"] == _v1_co2_step(start, direction), (tenth, direction)


def test_the_co2_feed_panel_cannot_restore_the_feed_past_trip_21_2(plant):
    """While 21.2's flag is lost the step up is refused with the instructor's reason, and the
    demand is unchanged; a step down to none is taken. A direction other than +1 or -1 is
    refused."""
    plant.units["SYN-TRIPS"].i_21_2.latched = True
    _ok(plant, type="co2_set", value=0.0)
    _refused(plant, r"XV-322902 is held shut by trip 21\.2's flag", type="co2_step", dir=1)
    assert plant.operator["320K002-CO2"] == 0.0
    _ok(plant, type="co2_step", dir=-1)
    plant.units["SYN-TRIPS"].i_21_2.latched = False
    for bad in (0, 2, True, "1", None):
        _refused(plant, r"co2_step needs 'dir' = \+1 or -1", type="co2_step", dir=bad)


def test_the_granulation_panel_moves_one_header_valve_a_press(plant):
    """Decision 224: ten of twelve valves online at the seed; INCREASE brings one online up to
    twelve, DECREASE takes one off down to none, each press answered with the count; a direction
    other than +1 or -1 is refused."""
    assert plant.operator["GRANULATION-HEADERS"] == 10
    r = _ok(plant, type="granulation_headers", dir=1)
    assert plant.operator["GRANULATION-HEADERS"] == 11 and r.text == "11 of 12 header valves online"
    for _ in range(3):
        _ok(plant, type="granulation_headers", dir=1)
    assert plant.operator["GRANULATION-HEADERS"] == 12
    for _ in range(14):
        _ok(plant, type="granulation_headers", dir=-1)
    assert plant.operator["GRANULATION-HEADERS"] == 0
    for bad in (0, 2, True, "1", None):
        _refused(plant, r"granulation_headers needs 'dir' = \+1 or -1", type="granulation_headers",
                 dir=bad)


def test_hic_335602_sets_its_hand_station(plant):
    _ok(plant, type="hic335602_set", op=40.0)
    assert plant.operator["HIC-335602"] == 40.0
    _ok(plant, type="hic335602_set", op=140.0)
    assert plant.operator["HIC-335602"] == 100.0


@pytest.mark.parametrize("pair", RUN_STATE_PAIRS)
def test_a_pump_pair_runs_while_either_of_its_machines_does(plant, pair):
    """322P002 as V1 holds it, and each pair decision 227 gives a run state."""
    assert plant.operator[pair] is True
    _ok(plant, type="aux_pump_toggle", id=pair + "B", on=True)
    _ok(plant, type="aux_pump_toggle", id=pair + "A", on=False)
    assert plant.operator[pair] is True
    _ok(plant, type="aux_pump_toggle", id=pair + "B", mode="MAN", on=False)
    assert plant.operator[pair] is False and plant.operator[pair + "B"]["mode"] == "MAN"
    _ok(plant, type="aux_pump_toggle", id=pair + "A", on=True)
    assert plant.operator[pair] is True


def test_a_faceplate_enters_auto_bumpless_and_takes_what_its_mode_allows(plant):
    """LIC-323505 to MAN and an output; back to AUTO its set point takes the PV; a set point in
    MAN, a mode it does not offer and a tag with no faceplate are each refused, and a refused
    command changes nothing. A cascade master's output is its slave's set point, clamped to its
    own range (TIC-323007's, in bar a — decision 21)."""
    loop = plant.loops["323F004"][0]
    _ok(plant, type="r323_ctrl_set", id="LIC_323505", mode="MAN", op=40.0)
    assert (loop.mode, loop.op) == ("MAN", 40.0)
    loop.pv = loop.sp + 3.0
    _refused(plant, "AUTO only", type="r323_ctrl_set", id="LIC-323505", sp=60.0)
    _refused(plant, "offers MAN, AUTO, not CAS", type="r323_ctrl_set", id="LIC-323505",
             mode="CAS")
    _refused(plant, "AUTO only", type="r323_ctrl_set", id="LIC-323505", mode="MAN", sp=1.0)
    assert loop.mode == "MAN"
    _ok(plant, type="r323_ctrl_set", id="LIC-323505", mode="AUTO")
    assert loop.sp == loop.pv
    tic = plant.loops["323C003"][0]
    _ok(plant, type="r323_ctrl_set", id="TIC-323007", mode="MAN", op=40.0)
    assert tic.op == tic.op_hi < 40.0
    # UF85's slave, on the model since session 55 (decision 123); a tag with no faceplate.
    uf = plant.loops["335"][1].loop
    _ok(plant, type="r323_ctrl_set", id="FIC_335405", mode="MAN", op=30.0)
    assert (uf.mode, uf.op) == ("MAN", 30.0)
    _refused(plant, "no faceplate", type="r323_ctrl_set", id="FIC_999999", mode="MAN")


def test_the_ratio_station_and_the_standby_take_their_faceplates(plant):
    """FFIC-329401, Uhde's ratio station, takes r323_ctrl_set as V1's dictionary did: into MAN
    with the slave's set point by hand, back to AUTO on the ratio it makes. SIC-323902, the
    standby's faceplate, offers MAN alone and takes its output."""
    station = plant.loops["328C004"][0].ffic_329401
    _ok(plant, type="r323_ctrl_set", id="FFIC_329401", mode="MAN", op=6000.0)
    assert (station.mode, station.op) == ("MAN", 6000.0)
    _ok(plant, type="r323_ctrl_set", id="FFIC_329401", mode="AUTO")
    assert station.mode == "AUTO" and station.sp == station.pv
    spare = plant.loops["SIC-323902"][0]
    _ok(plant, type="r323_ctrl_set", id="SIC_323902", op=25.0)
    assert (spare.mode, spare.op) == ("MAN", 25.0)
    _refused(plant, "offers MAN, not AUTO", type="r323_ctrl_set", id="SIC_323902", mode="AUTO")


def test_v1s_dictionary_loops_take_a_set_point_in_any_mode(plant):
    """PIC-322203: into AUTO bumpless, the set point clamped to 120-175 bar a in any mode."""
    pic = plant.loops["320K002"][0]
    _ok(plant, type="pic_set", mode="MAN", op=30.0, sp=200.0)
    assert (pic.mode, pic.op, pic.sp) == ("MAN", 30.0, 175.0)
    pic.pv = 150.0
    _ok(plant, type="pic_set", mode="AUTO")
    assert pic.sp == 150.0
    _ok(plant, type="fic_set", sp=1000.0)
    assert plant.loops["322E003"][0].fic_sp == 612.0


def test_the_steam_loops(plant):
    """LIC-329502 into AUTO on 329D005's level; the PIC-329207 legs locked while the master is ON;
    HV-329601 refused while trip 21.2 forces it."""
    st = plant.units["329"]
    _ok(plant, type="lic329502_set", mode="MAN", op=20.0)
    st.m_d005_kg *= 1.1
    _ok(plant, type="lic329502_set", mode="AUTO")
    assert st.lic_329502.sp_pct == pytest.approx(D005.level_pct(st.m_d005_kg), abs=1e-12)
    _refused(plant, "follows MASTER-329207", type="pic329207c_set", mode="MAN", op=10.0)
    _ok(plant, type="master207_set", on=False)
    _ok(plant, type="pic329207c_set", mode="MAN", op=10.0)
    assert st.pic_329207.legs["C"].op_pct == 10.0
    _ok(plant, type="pic329205_set", mode="MAN", op=75.0)
    assert (st.pic_329205.op_a_pct, st.pic_329205.op_b_pct) == (0.0, 50.0)
    st.hv_329601.blocked = True
    _refused(plant, "forced by trip 21.2", type="steam_hpvent_set", op=50.0)


def test_the_speed_controllers_and_the_ratio(plant):
    st = plant.units["321"]
    _ok(plant, type="controller_set", id="SIC_321951", mode="MAN", op=55.0)
    assert (st.sic_b.mode, st.sic_b.mv) == ("MAN", 55.0)
    _refused(plant, "AUTO only", type="controller_set", id="SIC_321951", sp=50.0)
    st.ratio_pv = 3.14159
    _ok(plant, type="controller_set", id="SIC_321951", mode="CAS")
    assert st.ratio_sp == 3.142
    _ok(plant, type="ratio_set", sp=9.0)
    assert st.ratio_sp == 5.0


def test_simulator_and_unknown_commands_are_not_the_plants(plant):
    _refused(plant, "simulator's control", type="reset_sim")
    _refused(plant, "unknown command", type="warp_drive")


#: Each pair decision 227 gives a run state, and the flow its two machines stopped must stop: the
#: unit's result and its field.
PAIR_FLOWS = {
    "328P002": ("328D001", "m_776_kgh"),
    "328P006": ("328C002", "m_743_kgh"),
    "328P007": ("328C004", "m_export_kgh"),
    "329P003": ("323E003", "q_kw"),
    "335P002": ("335", "delivered_kgh"),
}


@pytest.mark.parametrize("pair", PAIR_FLOWS)
def test_a_pump_pair_stopped_stops_its_flow_and_restarted_runs_again(pair):
    """Both machines stopped between ticks: the pair's flow is zero on the next tick; either one
    started again, it runs."""
    unit, field = PAIR_FLOWS[pair]
    sch, plant = build_plant()
    s = Scheduler(sch, plant)
    assert getattr(s.tick().results[unit], field) > 0.0
    _ok(plant, type="aux_pump_toggle", id=pair + "A", on=False)
    assert getattr(s.tick().results[unit], field) == 0.0
    _ok(plant, type="aux_pump_toggle", id=pair + "B", on=True)
    for _ in range(600):
        r = s.tick().results[unit]
    assert getattr(r, field) > 0.0


def test_a_command_reaches_the_plant_on_the_next_tick():
    """HIC-322605 to 45 % between ticks: the reactor's outlet line takes it on the next tick."""
    sch, plant = build_plant()
    s = Scheduler(sch, plant)
    before = s.tick().results["322R001"].m_out_kgh
    _ok(plant, type="hic605_set", op=45.0)
    assert s.tick().results["322R001"].m_out_kgh < before
