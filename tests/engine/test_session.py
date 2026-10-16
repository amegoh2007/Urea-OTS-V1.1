"""The engine session — `ureasim.engine.session`.

The session ties the plant, the fixed-step simulator, the historian, the commands and the
snapshots together for the station server. Pinned: the wall clock paid in whole steps at the
pacing; freeze; the operator's command reaching the plant and a refusal carrying its reason; an
exercise saved, the plant moved on, the exercise restored and replaying; reset to the seed; the
console packet published with V1's health block, recorded in the historian on V1's paths and
read back as a trend's backfill; a physics fault held in the health block until a clean pass.
"""

from __future__ import annotations

from ureasim.engine.session import EngineSession


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
    assert s.packet() == {}
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
    run); the historian has recorded the packet's paths ten times, and a trend's backfill reads
    them back."""
    s = EngineSession(tmp_path)
    assert s.published_state() == {}
    for _ in range(20):
        s.advance(500_000_000)                  # a pass pays at most V1's 0.5 s
    p = s.published_state()
    assert p["t_sim"] == s.t_plant == 10.0
    h = p["_health"]
    assert h["ok"] is True and h["heartbeat"] == 100 and h["error"] is None
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
