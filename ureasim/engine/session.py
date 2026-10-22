"""The engine session — one plant, its clock, its historian, and the commands that reach it.

What this is
------------
The object the station server's engine host drives (`ureasim.net.engine_host`): it owns the plant
(`engine.plant`), steps it through the fixed-step simulator (`engine.simulator`) on the wall clock
and the instructor's pacing, records the console packet in the historian (`engine.historian`) on
the plant clock, publishes that packet (`engine.packet`) with the engine's health, applies the
operator's commands (`engine.command`) and answers the simulator's own controls, which the protocol
reserves for the instructor:

    set_sim_mode   SLOW or FAST pacing (V1's ``SIM_SPEED``)
    freeze         hold the plant clock, or release it
    reset_sim      the plant back to its design seed, the trends restarted (V1's
                   ``reset_simulation``)
    snapshot_save  the exercise saved under a name (`engine.snapshot`)
    snapshot_load  an exercise restored by name, checked against the present model; the trends
                   restart, since the plant clock has jumped

Every answer is (accepted, reason), the reason a refusal's, so it reaches the console that asked.

The health block
----------------
V1 staples a ``_health`` block on every packet it pushes so a console can tell a crashed engine (a
step raised: ``ok`` false, the error and its traceback) from a hung one (``age_s`` climbing while
``ok`` stays true) from a live one. The session keeps the same fields: a step that raises freezes
the plant for the rest of its pass (`Simulator`), the fault is held here, and the next pass that
steps cleanly clears it.

Source: V1 ``backend/main.py`` ``sim_task`` (the stepping loop and its historian sample),
``health`` and ``_flag_health_error`` / ``_clear_health_error`` (11975-12020), ``reset_simulation``
and ``handle_cmd``'s ``set_sim_mode`` / ``reset_sim`` branches; the rest the rewrite's.
"""

from __future__ import annotations

import os
import re
import time
import traceback
from pathlib import Path
from typing import Any, Mapping

from ureasim.data.engine import SIM_SPEED
from ureasim.engine import snapshot
from ureasim.engine.command import SIMULATOR_COMMANDS, apply_command
from ureasim.engine.historian import Historian
from ureasim.engine.packet import build_packet
from ureasim.engine.plant import build_plant
from ureasim.engine.scheduler import Scheduler
from ureasim.engine.simulator import Simulator
from ureasim.engine.state import PlantState

__all__ = ["EXERCISE_DIR_ENV", "STALLED_AFTER_S", "EngineSession"]

#: The environment variable naming where exercises are saved; ``~/ureasim-exercises`` without it.
EXERCISE_DIR_ENV = "UREASIM_EXERCISES"

#: No clean step for this long and the engine reads as stalled [s] (V1's ``/api/health``).
STALLED_AFTER_S = 5.0

#: What an exercise may be called: a file name on any system.
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


class EngineSession:
    """One plant served to the consoles."""

    def __init__(self, exercise_dir: str | os.PathLike | None = None) -> None:
        self.schedule, plant = build_plant()
        self.scheduler = Scheduler(self.schedule, plant)
        self.simulator = Simulator(step=self._step)
        self.historian = Historian()
        self.frozen = False
        self.exercise_dir = Path(exercise_dir or os.environ.get(EXERCISE_DIR_ENV)
                                 or Path.home() / "ureasim-exercises")
        self._health = {"ok": True, "error": None, "type": None, "traceback": None,
                        "sim_t": None, "since": None, "count": 0}
        self._last_step_wall = time.time()

    @property
    def plant(self) -> PlantState:
        """The plant the session owns."""
        return self.scheduler.plant

    @property
    def t_plant(self) -> float:
        """The plant clock [s]."""
        return self.plant.clock.time_s

    # ---- the clock ----

    def _step(self, dt: float) -> None:
        self.scheduler.tick(dt)
        now = time.time()
        self._last_step_wall = now
        self.historian.maybe_sample(lambda: self.packet(now, health=False), self.t_plant, now)

    def advance(self, elapsed_ns: int) -> int:
        """Pay the plant ``elapsed_ns`` of wall-clock time at the pacing, unless frozen; the steps
        run. A step that raises is held as the engine's fault until a pass steps cleanly."""
        if self.frozen:
            return 0
        steps = self.simulator.advance(elapsed_ns)
        self._note_health()
        return steps

    def _note_health(self) -> None:
        exc = self.simulator.fault
        h = self._health
        if exc is None:
            if not h["ok"]:
                h.update(ok=True, error=None, type=None, traceback=None, sim_t=None, since=None,
                         count=0)
            return
        h.update(ok=False, type=type(exc).__name__, error=f"{type(exc).__name__}: {exc}",
                 traceback="".join(traceback.format_exception(exc)), sim_t=self.t_plant,
                 count=h["count"] + 1)
        if h["since"] is None:
            h["since"] = time.time()

    def health(self, now: float | None = None) -> dict:
        """V1's ``_health`` block: whether the plant is stepping cleanly, its heartbeat (the steps
        run), the seconds since the last good step and, after a fault, what raised."""
        now = time.time() if now is None else now
        return {"ok": self._health["ok"], "heartbeat": self.simulator.steps,
                "age_s": round(now - self._last_step_wall, 2), "error": self._health["error"],
                "type": self._health["type"], "traceback": self._health["traceback"],
                "sim_t": self._health["sim_t"], "since": self._health["since"],
                "count": self._health["count"], "server_wall": now}

    # ---- what the consoles read ----

    def packet(self, t_wall: float | None = None, *, health: bool = True) -> dict:
        """The console packet after the last tick, on V1's key paths, with the health block
        unless ``health`` is false; empty before the plant's first tick."""
        if not self.scheduler.results:
            return {}
        t_wall = time.time() if t_wall is None else t_wall
        return build_packet(self.plant, self.scheduler.results, self.scheduler.tears_read,
                            sim_mode=self.simulator.pacing, t_wall=t_wall,
                            health=self.health(t_wall) if health else None)

    def published_state(self) -> dict:
        """What the server sends every console: the packet, now."""
        return self.packet()

    def history(self, paths, span_s: float, max_points: int = 800, end_sim=None) -> dict:
        """A trend's backfill: ``span_s`` plant seconds of history for ``paths`` (V1's
        ``/api/hist``)."""
        return self.historian.query(list(paths), max(1.0, float(span_s)),
                                    max(2, int(max_points)), end_sim=end_sim)

    def history_paths(self) -> dict:
        """Every path the historian records, and each ring's occupancy (V1's
        ``/api/hist/paths``)."""
        return {"paths": self.historian.paths(), "rings": self.historian.stats()}

    def exercises(self) -> list[str]:
        """The saved exercises' names, for the instructor's panel: every ``<name>.json`` in the
        exercise directory whose name a ``snapshot_load`` would take."""
        if not self.exercise_dir.is_dir():
            return []
        return sorted(p.stem for p in self.exercise_dir.glob("*.json") if _NAME.match(p.stem))

    # ---- commands ----

    def handle(self, cmd: Mapping[str, Any], station: str = "") -> tuple[bool, str]:
        """The engine's command handler: (accepted, the reason it was not)."""
        kind = str(cmd.get("type", ""))
        if kind in SIMULATOR_COMMANDS:
            return self._simulator_command(kind, cmd)
        result = apply_command(self.plant, cmd, self.scheduler.results)
        return result.ok, result.reason

    def _simulator_command(self, kind: str, cmd: Mapping[str, Any]) -> tuple[bool, str]:
        if kind == "set_sim_mode":
            mode = str(cmd.get("mode", "")).upper()
            if mode not in SIM_SPEED:
                return False, f"no pacing {cmd.get('mode')!r}: one of {', '.join(sorted(SIM_SPEED))}"
            self.simulator.set_pacing(mode)
            return True, ""
        if kind == "freeze":
            self.frozen = (not self.frozen) if cmd.get("on") is None else bool(cmd["on"])
            return True, ""
        if kind == "reset_sim":
            self._install(build_plant()[1])
            return True, ""
        if kind in ("snapshot_save", "snapshot_load"):
            name = str(cmd.get("name", ""))
            if not _NAME.match(name):
                return False, f"an exercise name is letters, digits, '.', '_' or '-': {name!r}"
            path = self.exercise_dir / f"{name}.json"
            try:
                if kind == "snapshot_save":
                    self.exercise_dir.mkdir(parents=True, exist_ok=True)
                    snapshot.save(self.plant, str(path), note=str(cmd.get("note", "")))
                else:
                    self._install(snapshot.load(str(path), build_plant()[1]))
            except (snapshot.SnapshotError, OSError) as exc:
                return False, str(exc)
            return True, ""
        raise ValueError(f"no handler for the simulator command {kind!r}")

    def _install(self, plant: PlantState) -> None:
        """Run ``plant`` from now on: the clock restarts from its tick, the trends from empty."""
        self.scheduler = Scheduler(self.schedule, plant)
        self.simulator.owed_ns = 0
        self.historian = Historian()
