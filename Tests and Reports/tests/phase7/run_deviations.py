"""Put every deviation of `tests.phase7.deviations` to the port's plant and report what it does.

Usage
-----
    python -m tests.phase7.run_deviations OUT_DIR [KEY ...] [--workers N]

Each deviation and one unperturbed control run start from the design seed and step the scheduler
at the fixed 0.1 s; the deviation's commands are applied after `SETTLE_S`, the packet is sampled
every `SAMPLE_S`, and each claimed response is read as the deviation's departure from the control
at the same plant time — at the end, or at its extreme on the way (`Expect.measure`). The control
absorbs the seed's own slow drift (handoff B-94). Values are read off the published packet, as the
console shows them: a change smaller than an indicator's display resolution reads as none.

`OUT_DIR` receives ``runs/<key>.json`` as each run finishes, then ``deviations.json`` (every
record) and ``deviations.md`` (the verdict table).
"""

from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

from tests.phase7.deviations import DEVIATIONS, SAMPLE_S, SETTLE_S, Deviation
from tests.phase7.drivers import flatten
from tests.phase7.scenarios import DT

#: A departure counts once it passes this fraction of the control value (or of 1.0, below it).
REL_TOL = 1.0e-4


def _paths(devs) -> list:
    return sorted({e.path for d in devs for e in d.expects})


def run_plant(dev: Deviation | None, duration_s: float, paths: list, extra: dict = None,
              watch=None) -> dict:
    """The design seed through ``dev`` (None: left alone) for ``duration_s`` after settling.
    ``extra`` maps a name to a function of the tick's results, sampled beside the packet; ``watch``,
    if given, is called with every tick's results, for an indicator that must see between samples."""
    from ureasim.engine.command import apply_command
    from ureasim.engine.packet import build_packet
    from ureasim.engine.plant import build_plant
    from ureasim.engine.scheduler import Scheduler

    sched = Scheduler(*build_plant())
    plant = sched.plant
    n_settle = int(round(SETTLE_S / DT))
    n_total = n_settle + int(round(duration_s / DT))
    every = int(round(SAMPLE_S / DT))
    extra = extra or {}
    rec = {"key": dev.key if dev else "control", "t": [],
           "values": {p: [] for p in (*paths, *extra)}, "commands": [], "trips": {}, "flags": {}}
    t0 = time.perf_counter()
    for k in range(1, n_total + 1):
        if dev is not None and k == n_settle + 1:
            for cmd in dev.commands:
                r = apply_command(plant, cmd, sched.results)
                rec["commands"].append((cmd, r.ok, r.reason))
        sched.tick()
        if watch is not None:
            watch(sched.results)
        if k % every == 0:
            flat = flatten(build_packet(plant, sched.results, sched.tears_read, sim_mode="x1",
                                        t_wall=0.0))
            t = round(k * DT - SETTLE_S, 6)
            rec["t"].append(t)
            for p in paths:
                rec["values"][p].append(flat.get(p))
            for name, fn in extra.items():
                rec["values"][name].append(fn(sched.results))
            for key, val in flat.items():
                if val is True and (key.startswith("trip_latched.") or key.startswith("flags.")):
                    rec["trips" if key.startswith("trip") else "flags"].setdefault(key, t)
    rec["wall_s"] = time.perf_counter() - t0
    return rec


def _job(key: str) -> dict:
    dev = next(d for d in DEVIATIONS if d.key == key)
    return run_plant(dev, dev.duration_s, _paths([dev]))


def verdicts(dev: Deviation, rec: dict, control: dict) -> list:
    """Each claimed response as measured: the departure, its sign, and whether it is the claim's."""
    n = len(rec["t"])
    out = []
    for e in dev.expects:
        a, c = rec["values"][e.path], control["values"][e.path][:n]
        diffs = [float(x) - float(y) for x, y in zip(a, c) if x is not None and y is not None]
        if not diffs:
            out.append({"path": e.path, "claim": e.claim, "claimed": e.sign, "measure": e.measure,
                        "departure": None, "measured": None, "agrees": None})
            continue
        if e.measure == "peak":
            dep = max(diffs) if e.sign > 0 else min(diffs)
        else:
            dep = diffs[-1]
        ref = abs(float(c[len(diffs) - 1])) if c[len(diffs) - 1] is not None else 1.0
        tol = REL_TOL * max(ref, 1.0)
        sign = 0 if abs(dep) <= tol else (1 if dep > 0 else -1)
        out.append({"path": e.path, "claim": e.claim, "claimed": e.sign, "measure": e.measure,
                    "base": float(c[0]) if c and c[0] is not None else None,
                    "departure": dep, "measured": sign, "agrees": sign == e.sign})
    return out


def _md(results: list) -> str:
    lines = ["| key | deviation | indicator | claimed | measured | departure | agrees |",
             "|---|---|---|---|---|---|---|"]
    arrow = {1: "rises", -1: "falls", 0: "no change", None: "n/a"}
    for dev, rows, rec in results:
        for i, r in enumerate(rows):
            dep = "" if r["departure"] is None else f"{r['departure']:+.4g}"
            lines.append(f"| {dev.key if i == 0 else ''} | {dev.title if i == 0 else ''} | "
                         f"{r['path']} ({r['measure']}) | {arrow[r['claimed']]} | "
                         f"{arrow[r['measured']]} | {dep} | "
                         f"{'yes' if r['agrees'] else 'NO'} |")
        refused = [c for c in rec["commands"] if not c[1]]
        if refused:
            lines.append(f"| | refused: {refused} | | | | | |")
    return "\n".join(lines) + "\n"


def main(argv: list) -> int:
    workers = 8
    if "--workers" in argv:
        i = argv.index("--workers")
        workers = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    out_dir, keys = argv[0], argv[1:] or [d.key for d in DEVIATIONS]
    devs = [d for d in DEVIATIONS if d.key in keys]
    os.makedirs(os.path.join(out_dir, "runs"), exist_ok=True)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        control_f = pool.submit(run_plant, None, max(d.duration_s for d in devs), _paths(devs))
        futures = {pool.submit(_job, d.key): d.key for d in devs}
        recs = {}
        for f in as_completed(futures):
            rec = f.result()
            recs[futures[f]] = rec
            with open(os.path.join(out_dir, "runs", f"{futures[f]}.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(rec, fh, default=str)
            print(f"{futures[f]} done in {rec['wall_s']:.0f} s ({len(recs)} of {len(devs)})",
                  flush=True)
        control = control_f.result()
    results = [(d, verdicts(d, recs[d.key], control), recs[d.key]) for d in devs]
    with open(os.path.join(out_dir, "deviations.json"), "w", encoding="utf-8") as fh:
        json.dump({"control": control, "runs": recs,
                   "verdicts": {d.key: rows for d, rows, _ in results}}, fh, default=str)
    with open(os.path.join(out_dir, "deviations.md"), "w", encoding="utf-8") as fh:
        fh.write(_md(results))
    agree = sum(r["agrees"] is True for _, rows, _ in results for r in rows)
    total = sum(len(rows) for _, rows, _ in results)
    print(f"{agree} of {total} claimed responses as claimed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
