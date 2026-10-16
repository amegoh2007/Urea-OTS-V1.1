"""The Phase 7 drivers — one engine through one procedure, at the fixed 0.1 s step.

What this is
------------
`run_v1` drives V1's ``step_sim`` (its own module, imported from its source tree) and `run_port`
the rewrite's scheduler through a `Scenario`, identically: the commands due are applied between
two ticks, before the first tick that starts at or after their time; the disturbance is applied
the way each engine's procedure applies it (the HPCC rupture: V1's script injects water into the
process, the port runs its own tube leak, process into the shell — handoff B-82); the packet is
sampled on the scenario's interval; and every tick the watched pressures and the trips are read
from the engines' states, so a limit cycle a few ticks long cannot hide between samples (handoff
B-51). Each driver returns a plain record, written
as JSON by `tests.phase7.run`, so the two sides can run in two processes at once.

The record
----------
    t            sample times [s]
    values       path -> the sampled value at each time (None where the path was absent)
    watch        name -> per-tick statistics (`ringing`) and the 10-s envelope (min, max)
    trips        trip key -> the first time it latched [s], or None
    commands     (time, command, accepted, reason) as each engine answered it
    stopped_s    the plant time the run ended at, and why
    wall_s       wall-clock seconds the run took; ms_per_tick
"""

from __future__ import annotations

import math
import os
import sys
import time
from typing import Any, Callable

from tests.phase7.scenarios import DT, WATCHES, Scenario, disturbance_at

#: V1's source tree, read only (`tests.equivalence.v1_loader`).
V1_BACKEND = r"D:\Work\Urea Simulation\backend"

#: The cold loop's PT-329201 [bar a]: V1's 5.7 bar g on the standard atmosphere.
COLD_P0_BARA = 5.7 + 1.01325

#: Window of the ringing statistics [ticks] (10 s) and the reversal that counts [bar].
RING_WINDOW_TICKS = 100
RING_STEP_BAR = 0.01


def flatten(packet: Any, prefix: str = "") -> dict:
    """A packet's numeric and boolean leaves by dotted path."""
    out: dict = {}
    if isinstance(packet, dict):
        for k, v in packet.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(packet, bool):
        out[prefix] = packet
    elif isinstance(packet, (int, float)):
        out[prefix] = float(packet)
    return out


class _Watch:
    """A per-tick series reduced as it arrives: the 10-s envelope and the reversals in it.

    Process utility: a pressure integral that rings (B-51) reverses direction every few ticks
    with an amplitude far above anything the process does; a smooth transient does not. Each
    10-s window counts the reversals of the tick-to-tick change whose size passes
    ``RING_STEP_BAR``, and keeps the window's peak-to-peak.
    """

    def __init__(self) -> None:
        self.env: list = []
        self.windows: list = []
        self._buf: list = []
        self._prev = None
        self._prev_d = 0.0
        self._rev = 0

    def add(self, x: float) -> None:
        if self._prev is not None:
            d = x - self._prev
            if abs(d) >= RING_STEP_BAR:
                if self._prev_d and (d > 0) != (self._prev_d > 0):
                    self._rev += 1
                self._prev_d = d
        self._prev = x
        self._buf.append(x)
        if len(self._buf) >= RING_WINDOW_TICKS:
            self._close()

    def _close(self) -> None:
        if self._buf:
            lo, hi = min(self._buf), max(self._buf)
            self.env.append((lo, hi))
            self.windows.append((self._rev, hi - lo))
        self._buf, self._rev = [], 0

    def result(self) -> dict:
        self._close()
        worst = max(self.windows, key=lambda w: (w[0], w[1]), default=(0, 0.0))
        ringing = [i for i, (rev, p2p) in enumerate(self.windows) if rev >= 6 and p2p >= 0.05]
        return {"env": self.env, "max_reversals_10s": worst[0], "p2p_at_max": worst[1],
                "max_p2p_10s": max((w[1] for w in self.windows), default=0.0),
                "ringing_windows": len(ringing),
                "first_ringing_s": (ringing[0] * RING_WINDOW_TICKS * DT) if ringing else None}


def _resolve(cmd: dict, initial: Callable[[dict], float]) -> dict:
    """The command with any "@initial" field replaced by the engine's value at time zero."""
    return {k: (initial(cmd) if v == "@initial" else v) for k, v in cmd.items()}


def _drive(scenario: Scenario, tick: Callable[[], None], packet: Callable[[], dict],
           apply: Callable[[dict], tuple], watch_reads: dict, trips: Callable[[], dict],
           initial: Callable[[dict], float], after_tick: Callable[[float], None],
           before_tick: Callable[[float], None]) -> dict:
    """The loop both engines share: commands, disturbance, tick, watches, trips, samples."""
    script = sorted(scenario.script, key=lambda e: e[0])
    n_max = int(round(scenario.duration_s / DT))
    every = max(int(round(scenario.sample_s / DT)), 1)
    rec = {"t": [], "values": {p: [] for p in scenario.tags}, "trips": {}, "commands": []}
    every_leaf = not scenario.tags
    watches = {name: _Watch() for name in watch_reads}
    tail_end = None
    stop = ("duration", n_max * DT)
    i_cmd = 0
    t0 = time.perf_counter()
    k = 0
    for k in range(n_max):
        t = k * DT
        while i_cmd < len(script) and script[i_cmd][0] <= t + 1e-9:
            cmd = _resolve(script[i_cmd][1], initial)
            ok, reason = apply(cmd)
            rec["commands"].append((round(t, 1), cmd, ok, reason))
            i_cmd += 1
        before_tick(t)
        tick()
        after_tick(t + DT)
        for name, read in watch_reads.items():
            watches[name].add(read())
        for key, latched in trips().items():
            if latched and rec["trips"].get(key) is None:
                rec["trips"][key] = round(t + DT, 1)
        if (k + 1) % every == 0:
            flat = flatten(packet())
            n = len(rec["t"])
            rec["t"].append(round(t + DT, 3))
            for p in (flat if every_leaf else scenario.tags):
                # A leaf first seen late is padded with None for the samples it missed.
                rec["values"].setdefault(p, [None] * n).append(flat.get(p))
            for vals in rec["values"].values():       # a leaf gone from this sample
                if len(vals) <= n:
                    vals.append(None)
        if scenario.stop_after_trip and tail_end is None:
            key, tail = scenario.stop_after_trip
            if rec["trips"].get(key) is not None:
                tail_end = rec["trips"][key] + tail
        if tail_end is not None and t + DT >= tail_end - 1e-9:
            stop = (f"{scenario.stop_after_trip[0]} latched + tail", t + DT)
            break
    wall = time.perf_counter() - t0
    rec["watch"] = {name: w.result() for name, w in watches.items()}
    rec["stopped"] = {"why": stop[0], "t_s": round(stop[1], 1)}
    rec["wall_s"] = round(wall, 1)
    rec["ms_per_tick"] = round(wall / max(k + 1, 1) * 1000.0, 2)
    return rec


# ======================================================================================
# V1
# ======================================================================================

def run_v1(scenario: Scenario) -> dict:
    """V1's ``step_sim`` through the procedure, in this process (one engine a process: V1 keeps
    its plant in module globals)."""
    if V1_BACKEND not in sys.path:
        sys.path.append(V1_BACKEND)
    cache = os.path.join(V1_BACKEND, ".boot_pin_cache.json")
    mtime = os.path.getmtime(cache) if os.path.exists(cache) else None
    import main  # noqa: E402  (V1's own module, by its bare name, from its source tree)
    rebuilt = (os.path.getmtime(cache) if os.path.exists(cache) else None) != mtime
    main.state = main.State()
    s = main.state
    holder = {"pkt": {}}
    if scenario.initial == "cold_loop":
        s.p_syn_bara = COLD_P0_BARA
        s.react_level_pct = 0.0
        s.react_lt322504_pct = 0.0
        s.react_m_liq = main.reactor.M_HOLDUP_MIN
        s.react_m_in_lag = 0.0
        s.react_fwd_wash = 0.0
        s.hpcc_level_pct = 0.0
        s.strip_level = 0.0
        s.scrub_holdup_kg = 0.0
        s.scrub_level_pct = 0.0
        s.tlag = {}
    drum_pin = s.tank_level_frac
    leak = {"kgh": 0.0}
    if scenario.disturbance is not None:
        original = main.hpcc_322e002

        def _hpcc_leak(*a, **kw):
            out = original(*a, **kw)
            if leak["kgh"] > 0.0:
                out["feed_kmolh"]["H2O"] += leak["kgh"] / main.MW_COMP["H2O"]
            return out
        main.hpcc_322e002 = _hpcc_leak
    initials = {"hic9605_set": s.HIC_329605}

    def tick():
        holder["pkt"] = main.step_sim(DT)

    def before(t):
        leak["kgh"] = disturbance_at(scenario, t) if scenario.disturbance else 0.0

    def after(_t):
        if scenario.initial == "pinned_drum":
            s.tank_level_frac = drum_pin

    def apply(cmd):
        main.handle_cmd(cmd)
        return True, ""

    reads = {name: (lambda f=field: float(getattr(main.state, f)))
             for name, (field, _unit) in WATCHES.items()}
    rec = _drive(scenario, tick, lambda: holder["pkt"], apply, reads,
                 lambda: dict(main.state.trip_latched), lambda c: initials[c["type"]],
                 after, before)
    rec["side"] = "v1"
    rec["v1_pin_cache_rebuilt"] = rebuilt
    return rec


# ======================================================================================
# The rewrite
# ======================================================================================

def run_port(scenario: Scenario) -> dict:
    """The rewrite's scheduler through the procedure."""
    from ureasim.engine.command import apply_command
    from ureasim.engine.packet import build_packet
    from ureasim.engine.plant import build_plant
    from ureasim.engine.scheduler import Scheduler
    from ureasim.units.synthesis.reactor_inventory import M_HOLDUP_MIN

    sched = Scheduler(*build_plant())
    plant = sched.plant
    u = plant.units
    if scenario.initial == "cold_loop":
        u["PT-329201"].p_syn_bara = COLD_P0_BARA
        rx = u["322R001"]
        rx.level_pct = rx.lt_322504_pct = 0.0
        rx.m_liq_kg = M_HOLDUP_MIN
        rx.m_in_lag_kgh = rx.fwd_wash_kgh = 0.0
        u["322E002"].level_pct = 0.0
        u["322E001"].level_pct = 0.0
        u["322E003"].holdup_kg = 0.0
        u["322E003"].level_pct = 0.0
    drum = u["321"].drum
    drum_pin = drum.level_frac
    initials = {"hic9605_set": plant.operator["HIC-329605"]}

    def before(t):
        # The HPCC rupture is the engine's own malfunction (handoff B-82, decided 2026-10-09):
        # process into the shell on the live differential, the schedule its rate at design.
        if scenario.disturbance:
            u["322E002"].leak_severity_kgh = disturbance_at(scenario, t)

    def after(_t):
        if scenario.initial == "pinned_drum":
            drum.level_frac = drum_pin

    def apply(cmd):
        r = apply_command(plant, cmd, sched.results)
        return r.ok, r.reason

    def trips():
        syn = u["SYN-TRIPS"]
        out = {key: getattr(syn, f"i_{key}").latched
               for key in ("21_2", "21_8", "21_10", "22_2")}
        out["22_1"] = u["TRIPS"].i_22_1.latched
        return out

    def _read(unit, attr):
        return lambda: float(getattr(u[unit], attr))
    reads = {name: _read(unit, "p_syn_bara" if unit == "PT-329201" else "p_bara")
             for name, (_field, unit) in WATCHES.items()}
    rec = _drive(scenario, sched.tick,
                 lambda: build_packet(plant, sched.results, sched.tears_read, sim_mode="SLOW",
                                      t_wall=0.0),
                 apply, reads, trips, lambda c: initials[c["type"]], after, before)
    rec["side"] = "port"
    return rec


def smith_foptd(t: list, p: list, p0: float, n_final: int = 15) -> dict:
    """Smith's two-point first-order-plus-dead-time identification of a rising step.

    Process utility: V1's cold-start acceptance (``test_transient_coldstart.py``) — model-free,
    so no assumed model shape biases it. ``p0`` the step's start, the final value the mean of the
    last ``n_final`` samples; t28 and t63 the first times past 28.3 and 63.2 % of the span.

        tau = 1.5 (t63 - t28),    t_d = t63 - tau
    """
    good = [(ti, pi) for ti, pi in zip(t, p) if pi is not None and math.isfinite(pi)]
    if len(good) < n_final + 2:
        return {"tau_s": None, "td_s": None, "p_final": None}
    pf = sum(pi for _, pi in good[-n_final:]) / n_final
    span = pf - p0

    def first(frac):
        target = p0 + frac * span
        return next((ti for ti, pi in good if (pi - target) * (1.0 if span > 0 else -1.0) >= 0.0),
                    None)
    t28, t63 = first(0.283), first(0.632)
    if t28 is None or t63 is None:
        return {"tau_s": None, "td_s": None, "p_final": pf}
    tau = 1.5 * (t63 - t28)
    return {"tau_s": tau, "td_s": t63 - tau, "p_final": pf, "t28_s": t28, "t63_s": t63}


__all__ = ["V1_BACKEND", "COLD_P0_BARA", "RING_WINDOW_TICKS", "RING_STEP_BAR", "flatten",
           "run_v1", "run_port", "smith_foptd"]
