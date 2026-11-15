"""The engine session — `ureasim.engine.session`.

The session ties the plant, the fixed-step simulator, the historian, the commands and the
snapshots together for the station server. Pinned: the wall clock paid in whole steps at the
pacing; freeze; the operator's command reaching the plant and a refusal carrying its reason; an
exercise saved, the plant moved on, the exercise restored and replaying; reset to the seed; the
console packet published with V1's health block, recorded in the historian on V1's paths and
read back as a trend's backfill; a physics fault held in the health block until a clean pass; the
exercises shipped with the simulator listed and restored beside the instructor's, never written or
shadowed (decision 171).

A held plant is not a silent one (handoff A-27, decision 169): a plant reset or restored while frozen
shows its rehearsed first tick, with its own clock, and is not stepped; the first tick it takes later
publishes the same packet; the plant at the engine's launch publishes nothing until it steps.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ureasim.engine import session as session_module
from ureasim.engine.session import EngineSession


def _body(packet: dict) -> str:
    """A packet without its clocks, health and wall time, as text that compares."""
    keep = {k: v for k, v in packet.items() if k not in ("t", "t_sim", "_health")}
    return json.dumps(keep, sort_keys=True, default=repr)


def _find(node, key):
    """The first value stored under ``key`` anywhere in a packet."""
    if isinstance(node, dict):
        if key in node:
            return node[key]
        for v in node.values():
            found = _find(v, key)
            if found is not None:
                return found
    return None


def test_the_wall_clock_is_paid_in_whole_steps_at_the_pacing(tmp_path):
    s = EngineSession(tmp_path)
    assert s.advance(250_000_000) == 2 and s.plant.clock.tick == 2     # 0.25 s at SLOW
    assert s.handle({"type": "set_sim_mode", "mode": "FAST"}) == (True, "")
    assert s.advance(100_000_000) == 60                                 # 0.1 s at 60x
    assert s.handle({"type": "freeze", "on": True}) == (True, "")
    assert s.advance(100_000_000) == 0
    ok, reason = s.handle({"type": "set_sim_mode", "mode": "WARP"})
    assert not ok and "no pacing" in reason
    assert s.historian.stats()["fast"]["samples"] == 7                  # one a plant second


def test_commands_reach_the_plant_or_say_why_not(tmp_path):
    s = EngineSession(tmp_path)
    assert s.handle({"type": "hic605_set", "op": 45.0}) == (True, "")
    assert s.plant.operator["HIC-322605"] == 45.0
    ok, reason = s.handle({"type": "xv_toggle", "id": "322915"})
    assert not ok and "HS-322915" in reason


def test_an_exercise_saved_and_restored_replays(tmp_path):
    """Saved after 10 s with HV-322605 at 45 %; the plant runs on and is reset; restored, it runs
    the same 10 s it ran after the save, to the bit."""
    s = EngineSession(tmp_path)
    s.handle({"type": "hic605_set", "op": 45.0})
    s.simulator.run(100)
    assert s.handle({"type": "snapshot_save", "name": "hv605-45", "note": "throttled"}) == (True, "")
    s.simulator.run(100)
    after = s.packet(0.0, health=False)
    assert s.handle({"type": "reset_sim"}) == (True, "") and s.plant.clock.tick == 0
    assert s.packet()["t_sim"] == 0.0           # a reset plant shows its seed, though it has not stepped
    assert s.handle({"type": "snapshot_load", "name": "hv605-45"}) == (True, "")
    assert s.plant.clock.tick == 100 and s.plant.operator["HIC-322605"] == 45.0
    s.simulator.run(100)
    assert s.packet(0.0, health=False) == after
    ok, reason = s.handle({"type": "snapshot_load", "name": "no-such"})
    assert not ok and "cannot read" in reason
    ok, reason = s.handle({"type": "snapshot_save", "name": "../escape"})
    assert not ok and "exercise name" in reason
    (tmp_path / "not an exercise.json").write_text("{}", encoding="utf-8")
    assert s.exercises() == ["hv605-45"]
    assert EngineSession(tmp_path / "none-yet").exercises() == []


def test_the_packet_is_published_with_its_health_and_recorded_on_v1s_paths(tmp_path):
    """Ten plant seconds: the packet carries V1's ``_health`` (clean, the heartbeat the steps
    run, no bracketed solve run out of iterations, A-37); the historian has recorded the packet's paths ten times, and a trend's backfill reads
    them back."""
    s = EngineSession(tmp_path)
    assert s.published_state() == {}
    for _ in range(20):
        s.advance(500_000_000)                  # a pass pays at most V1's 0.5 s
    p = s.published_state()
    assert p["t_sim"] == s.t_plant == 10.0
    h = p["_health"]
    assert h["ok"] is True and h["heartbeat"] == 100 and h["error"] is None
    assert h["roots_exhausted"] == 0
    assert s.historian.stats()["fast"]["samples"] == 10
    q = s.history(["RECIRC_323.C003.TIC_323007.pv", "no.such.path"], 60.0)
    assert q["series"]["RECIRC_323.C003.TIC_323007.pv"][-1] == 135.0
    assert q["missing"] == ["no.such.path"]
    assert "STRIP_322E001.LIC_322501.pv" in s.history_paths()["paths"]


def test_a_physics_fault_is_held_in_the_health_block_until_a_clean_pass(tmp_path, monkeypatch):
    """A tick that raises freezes the pass and reads as V1's crash: ``ok`` false with the error
    and its traceback; the next clean pass clears it."""
    s = EngineSession(tmp_path)
    s.advance(100_000_000)
    real = s.scheduler.tick

    def broken(dt):
        raise FloatingPointError("a unit diverged")
    monkeypatch.setattr(s.scheduler, "tick", broken)
    assert s.advance(300_000_000) == 0
    h = s.health()
    assert h["ok"] is False and h["type"] == "FloatingPointError" and h["count"] == 1
    assert "a unit diverged" in h["error"] and "FloatingPointError" in h["traceback"]
    monkeypatch.setattr(s.scheduler, "tick", real)
    assert s.advance(100_000_000) == 1 and s.health()["ok"] is True


# ---- a held plant is not a silent one (handoff A-27) ----


def _held(tmp_path, command: dict) -> EngineSession:
    """A session that has run, frozen, then given ``command`` (a reset or a restore)."""
    s = EngineSession(tmp_path)
    s.simulator.run(30)
    assert s.handle({"type": "snapshot_save", "name": "t3"}) == (True, "")
    s.simulator.run(20)
    assert s.handle({"type": "freeze", "on": True}) == (True, "")
    assert s.handle(command) == (True, "")
    return s


def test_a_plant_reset_while_frozen_shows_its_seed_and_is_not_stepped(tmp_path):
    s = _held(tmp_path, {"type": "reset_sim"})
    for _ in range(3):                                     # the console is sent it every pass
        p = s.published_state()
        assert p and p["t_sim"] == 0.0 and p["_health"]["ok"] is True
    assert s.advance(500_000_000) == 0 and s.plant.clock.tick == 0
    assert s.scheduler.results == {} and s.historian.stats()["fast"]["samples"] == 0


def test_an_exercise_restored_while_frozen_shows_the_exercises_own_time(tmp_path):
    s = _held(tmp_path, {"type": "snapshot_load", "name": "t3"})
    p = s.published_state()
    assert p and p["t_sim"] == 3.0 == s.t_plant and s.plant.clock.tick == 30
    assert s.advance(500_000_000) == 0 and s.plant.clock.tick == 30


def test_the_held_packet_is_the_one_the_first_real_tick_publishes(tmp_path):
    for command in ({"type": "reset_sim"}, {"type": "snapshot_load", "name": "t3"}):
        s = _held(tmp_path, command)
        shown = s.packet(0.0, health=False)
        s.frozen = False
        assert s.advance(100_000_000) == 1
        assert _body(s.packet(0.0, health=False)) == _body(shown), command


def test_a_restore_after_a_reset_shows_the_restored_plant_not_the_reset_one(tmp_path):
    s = _held(tmp_path, {"type": "reset_sim"})
    assert s.published_state()["t_sim"] == 0.0              # the reset plant's rehearsal is made and kept
    assert s.handle({"type": "snapshot_load", "name": "t3"}) == (True, "")
    assert s.published_state()["t_sim"] == 3.0 and s.plant.clock.tick == 30


def test_a_reset_and_a_freeze_drained_in_one_gap_still_leave_a_packet(tmp_path):
    """The host drains its queue whole between two ticks, so a reset and a freeze can both be applied
    before the plant has taken a step: the packet must not depend on the freeze coming first."""
    s = EngineSession(tmp_path)
    s.simulator.run(10)
    assert s.handle({"type": "reset_sim"}) == (True, "")
    assert s.handle({"type": "freeze", "on": True}) == (True, "")
    assert s.advance(500_000_000) == 0
    assert s.published_state()["t_sim"] == 0.0


def test_a_command_accepted_by_a_held_plant_shows_and_a_refused_one_changes_nothing(tmp_path):
    s = _held(tmp_path, {"type": "reset_sim"})
    before = s.packet(0.0, health=False)
    assert _find(before, "HIC_322605") != 45.0
    assert s.handle({"type": "hic605_set", "op": 45.0}) == (True, "")
    after = s.packet(0.0, health=False)
    assert _find(after, "HIC_322605") == 45.0 and _body(after) != _body(before)
    ok, _ = s.handle({"type": "xv_toggle", "id": "322915"})
    assert not ok and s.packet(0.0, health=False) == after
    assert s.plant.clock.tick == 0


def test_the_rehearsal_is_made_once_per_install_and_again_after_an_accepted_command(tmp_path, monkeypatch):
    calls = []
    real = session_module.rehearse

    def counted(schedule, plant):
        calls.append(plant.clock.tick)
        return real(schedule, plant)
    monkeypatch.setattr(session_module, "rehearse", counted)
    s = _held(tmp_path, {"type": "reset_sim"})
    for _ in range(5):
        s.published_state()
    assert calls == [0]
    s.handle({"type": "hic605_set", "op": 45.0})
    s.published_state()
    s.published_state()
    assert calls == [0, 0]
    assert not s.handle({"type": "xv_toggle", "id": "322915"})[0]       # refused: the plant did not change
    s.published_state()
    assert calls == [0, 0]
    s.handle({"type": "reset_sim"})
    s.published_state()
    assert calls == [0, 0, 0]


def test_a_plant_that_cannot_be_rehearsed_publishes_nothing_and_says_so_once(tmp_path, monkeypatch, caplog):
    s = EngineSession(tmp_path)
    calls = []

    def broken(schedule, plant):
        calls.append(1)
        raise FloatingPointError("a unit diverged")
    monkeypatch.setattr(session_module, "rehearse", broken)
    s.handle({"type": "reset_sim"})
    with caplog.at_level("ERROR"):
        assert s.published_state() == {} and s.published_state() == {}
    assert calls == [1] and sum("could not be rehearsed" in r.getMessage() for r in caplog.records) == 1


def test_the_plant_at_launch_is_held_silent_until_it_steps(tmp_path):
    """Decision 166: behind the start-up intro the plant publishes nothing, which the start-up
    controller reads as 'not released yet'; only a reset or a restore earns a preview."""
    s = EngineSession(tmp_path)
    s.frozen = True
    assert s.published_state() == {} and s.advance(500_000_000) == 0 and s.published_state() == {}
    s.frozen = False
    assert s.advance(100_000_000) == 1 and s.published_state()["t_sim"] == pytest.approx(0.1)


def test_the_first_real_tick_replaces_the_rehearsal(tmp_path):
    s = _held(tmp_path, {"type": "reset_sim"})
    assert s.published_state()["t_sim"] == 0.0
    s.frozen = False
    s.advance(300_000_000)
    assert s.published_state()["t_sim"] == pytest.approx(0.3) and s.scheduler.results


# -- the shipped exercises beside the instructor's (decision 171) --------------------------------------------


def _two_folders(tmp_path) -> tuple[EngineSession, object, object]:
    """A shipped folder holding one saved state and an instructor's folder holding another, both real."""
    shipped, own = tmp_path / "shipped", tmp_path / "own"
    shipped.mkdir()
    s = EngineSession(own, shipped_dir=shipped)
    s.simulator.run(10)
    assert s.handle({"type": "snapshot_save", "name": "drill"}) == (True, "")
    (own / "drill.json").replace(shipped / "steady.json")             # a state shipped with the simulator
    s.simulator.run(10)
    assert s.handle({"type": "snapshot_save", "name": "drill"}) == (True, "")
    return s, shipped, own


def test_the_shipped_exercises_are_listed_and_restored_beside_the_instructors(tmp_path):
    s, shipped, own = _two_folders(tmp_path)
    assert s.exercises() == ["drill", "steady"]
    assert s.handle({"type": "snapshot_load", "name": "steady"}) == (True, "")
    assert s.plant.clock.tick == 10                                   # the shipped one
    assert s.handle({"type": "snapshot_load", "name": "drill"}) == (True, "")
    assert s.plant.clock.tick == 20                                   # the instructor's own
    assert sorted(p.name for p in shipped.iterdir()) == ["steady.json"]   # nothing written there


def test_a_save_never_writes_the_shipped_folder_or_shadows_a_shipped_name(tmp_path):
    s, shipped, own = _two_folders(tmp_path)
    before = (shipped / "steady.json").read_bytes()
    ok, reason = s.handle({"type": "snapshot_save", "name": "steady"})
    assert not ok and "shipped" in reason and "another name" in reason
    assert (shipped / "steady.json").read_bytes() == before and not (own / "steady.json").exists()
    (own / "steady.json").write_bytes((own / "drill.json").read_bytes())   # a copy put there by hand
    assert s.exercises() == ["drill", "steady"]                       # listed once
    assert s.handle({"type": "snapshot_load", "name": "steady"}) == (True, "")
    assert s.plant.clock.tick == 10                                   # a shipped name is the shipped file


def test_without_a_shipped_folder_the_instructors_folder_is_the_only_one(tmp_path, monkeypatch):
    monkeypatch.delenv(session_module.EXERCISE_DIR_ENV, raising=False)
    root = Path(session_module.__file__).resolve().parents[2]
    assert session_module.DEFAULT_EXERCISE_DIR == root / "exercises"      # inside the folder (decision 218)
    monkeypatch.setattr(session_module, "DEFAULT_EXERCISE_DIR", tmp_path / "exercises")
    s = EngineSession()
    assert s.shipped_dir is None and s.exercise_dir == tmp_path / "exercises"
    assert s.exercises() == []
    monkeypatch.setenv(session_module.EXERCISE_DIR_ENV, str(tmp_path / "env"))
    assert EngineSession(shipped_dir=tmp_path / "shipped").exercise_dir == tmp_path / "env"
