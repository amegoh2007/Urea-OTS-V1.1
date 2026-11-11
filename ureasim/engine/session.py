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
    snapshot_save  the exercise saved under a name (`engine.snapshot`), in the instructor's folder
    snapshot_load  an exercise restored by name, checked against the present model; the trends
                   restart, since the plant clock has jumped

Exercises live in the instructor's folder (``UREASIM_EXERCISES``, or ``~/ureasim-exercises``), which
SAVE writes, and, when one is given, a folder of exercises shipped with the simulator (the repository's
``scenarios``, verified steady states) that is listed and restored beside it and never written. A
shipped name always means the shipped file: a save under it is refused, so no instructor's file shadows
a verified state, and the repository stays clean of training saves (`project.md` decision 171).

Every answer is (accepted, reason), the reason a refusal's, so it reaches the console that asked.

A held plant is not a silent one (handoff A-27)
-----------------------------------------------
A packet is built from the results of a tick, and a plant that was just reset or restored has none, so
the engine would publish nothing until it first stepped. Held by ``freeze``, that is for ever, and a
console that hears nothing for five seconds reads the link as dead and blanks. A reset or a restored
exercise therefore shows its first tick, rehearsed on a copy (`engine.rehearsal`), with the plant's own
clock: the plant is not stepped, and the packet is the one its first real tick will publish. The plant
at the engine's launch is the exception: it is held behind the start-up intro and publishes nothing
until it is released (`project.md` decision 166), which the start-up controller counts on.

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

import logging
import os
import re
import time
import traceback
from pathlib import Path
from typing import Any, Mapping

from ureasim.core.numeric import ROOT_LEDGER
from ureasim.data.engine import SIM_SPEED
from ureasim.engine import snapshot
from ureasim.engine.command import SIMULATOR_COMMANDS, apply_command
from ureasim.engine.historian import Historian
from ureasim.engine.packet import build_packet
from ureasim.engine.plant import build_plant
from ureasim.engine.rehearsal import Rehearsal, rehearse
from ureasim.engine.scheduler import Scheduler
from ureasim.engine.simulator import Simulator
from ureasim.engine.state import PlantState

__all__ = ["EXERCISE_DIR_ENV", "STALLED_AFTER_S", "EngineSession"]

log = logging.getLogger(__name__)

#: The environment variable naming where exercises are saved; ``~/ureasim-exercises`` without it.
EXERCISE_DIR_ENV = "UREASIM_EXERCISES"

#: No clean step for this long and the engine reads as stalled [s] (V1's ``/api/health``).
STALLED_AFTER_S = 5.0

#: What an exercise may be called: a file name on any system.
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


class EngineSession:
    """One plant served to the consoles."""

    def __init__(self, exercise_dir: str | os.PathLike | None = None,
                 shipped_dir: str | os.PathLike | None = None) -> None:
        self.schedule, plant = build_plant()
        self.scheduler = Scheduler(self.schedule, plant)
        self.simulator = Simulator(step=self._step)
        self.historian = Historian()
        self.frozen = False
        self._installed = False                  # a plant was reset or restored: it may show a rehearsal
        self._rehearsal: Rehearsal | None = None
        self._rehearsal_failed = False
        self.exercise_dir = Path(exercise_dir or os.environ.get(EXERCISE_DIR_ENV)
                                 or Path.home() / "ureasim-exercises")
        #: The exercises shipped with the simulator, read and never written; None without them.
        self.shipped_dir = Path(shipped_dir) if shipped_dir else None
        self._health = {"ok": True, "error": None, "type": None, "traceback": None,
                        "sim_t": None, "since": None, "count": 0}
        self._last_step_wall = time.time()
        #: The bracketed solves that ran out of iterations before this session began (A-37).
        self._roots_before = ROOT_LEDGER.exhausted

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
        self._rehearsal = None                   # the plant has results of its own now
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
        run), the seconds since the last good step and, after a fault, what raised; and the
        rewrite's count of bracketed solves that ran out of iterations since the session began
        (``roots_exhausted``, handoff A-37, decision 184)."""
        now = time.time() if now is None else now
        return {"ok": self._health["ok"], "heartbeat": self.simulator.steps,
                "age_s": round(now - self._last_step_wall, 2), "error": self._health["error"],
                "type": self._health["type"], "traceback": self._health["traceback"],
                "sim_t": self._health["sim_t"], "since": self._health["since"],
                "count": self._health["count"], "server_wall": now,
                "roots_exhausted": ROOT_LEDGER.exhausted - self._roots_before}

    # ---- what the consoles read ----

    def packet(self, t_wall: float | None = None, *, health: bool = True) -> dict:
        """The console packet after the last tick, on V1's key paths, with the health block
        unless ``health`` is false; empty before the plant's first tick, except that a plant reset or
        restored shows its rehearsed first tick (module docstring)."""
        shown = self._shown()
        if shown is None:
            return {}
        plant, results, tears_read = shown
        t_wall = time.time() if t_wall is None else t_wall
        return build_packet(plant, results, tears_read, sim_mode=self.simulator.pacing, t_wall=t_wall,
                            health=self.health(t_wall) if health else None)

    def _shown(self) -> tuple[PlantState, dict, Any] | None:
        """The plant, results and tears a packet is built from: the last tick's, or the rehearsal's
        for a plant reset or restored that has not stepped; None for a plant that has shown nothing."""
        if self.scheduler.results:
            return self.plant, self.scheduler.results, self.scheduler.tears_read
        if not self._installed or self._rehearsal_failed:
            return None
        if self._rehearsal is None:
            try:
                self._rehearsal = rehearse(self.schedule, self.plant)
            except Exception:  # noqa: BLE001 - a plant that cannot tick shows nothing, as it always did
                log.exception("the first tick of the installed plant could not be rehearsed")
                self._rehearsal_failed = True
                return None
        r = self._rehearsal
        return r.plant, r.results, r.tears_read

    def _forget_rehearsal(self) -> None:
        """The plant changed under its rehearsal: the next packet rehearses it again."""
        self._rehearsal = None
        self._rehearsal_failed = False

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
        """The saved exercises' names, for the intro's LOAD and the instructor's panel: every
        ``<name>.json`` whose name a ``snapshot_load`` would take, in the shipped folder and the
        instructor's, each name once."""
        names: set[str] = set()
        for folder in self._folders():
            if folder.is_dir():
                names.update(p.stem for p in folder.glob("*.json") if _NAME.match(p.stem))
        return sorted(names)

    def _folders(self) -> tuple[Path, ...]:
        """Where an exercise is looked for, the shipped folder first: a shipped name is the shipped file."""
        return (self.exercise_dir,) if self.shipped_dir is None else (self.shipped_dir, self.exercise_dir)

    def _shipped(self, name: str) -> bool:
        """Whether ``name`` is an exercise shipped with the simulator."""
        return self.shipped_dir is not None and (self.shipped_dir / f"{name}.json").is_file()

    # ---- commands ----

    def handle(self, cmd: Mapping[str, Any], station: str = "") -> tuple[bool, str]:
        """The engine's command handler: (accepted, the reason it was not)."""
        kind = str(cmd.get("type", ""))
        if kind in SIMULATOR_COMMANDS:
            return self._simulator_command(kind, cmd)
        result = apply_command(self.plant, cmd, self.scheduler.results)
        if result.ok:
            self._forget_rehearsal()             # a held plant shows what the command did
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
                    if self._shipped(name):
                        return False, f"{name!r} is an exercise shipped with the simulator: save under another name"
                    self.exercise_dir.mkdir(parents=True, exist_ok=True)
                    snapshot.save(self.plant, str(path), note=str(cmd.get("note", "")))
                else:
                    if self._shipped(name):
                        path = self.shipped_dir / f"{name}.json"
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
        self._installed = True
        self._forget_rehearsal()
