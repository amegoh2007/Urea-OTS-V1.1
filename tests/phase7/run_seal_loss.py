"""Put every case of `tests.phase7.seal_loss` (``Scenarios6.docx``) to the port's plant, both waves.

Usage
-----
    python -m tests.phase7.run_seal_loss OUT_DIR [KEY ...] [--workers N]

Each case and one unperturbed control start from the design seed and step the scheduler at the
fixed 0.1 s (`run_deviations.run_plant`); the case's commands land after the settling minute, the
packet and the indicators below are sampled every 5 s for 45 minutes, and each claim is read in
its wave by `run_coupled.verdicts`. `OUT_DIR` receives ``runs/<key>.json`` as each run finishes,
then ``seal_loss.json`` and ``seal_loss.md``.
"""

from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

from tests.phase7 import run_coupled as rc
from tests.phase7.run_deviations import run_plant
from tests.phase7.seal_loss import NOT_PUT, SEAL_LOSS

class ReliefPeak:
    """What SV32351 / SV32352 relieved of 323C003 [t/h], the most since the last sample: a lift
    lasts seconds, shorter than the survey's 5 s sample, so the valves are watched every tick
    (session 73: sampled, S6-2's 12.6 s of lifts in its first two minutes read as none, B-114)."""

    def __init__(self) -> None:
        self.peak = 0.0

    def watch(self, results: dict) -> None:
        self.peak = max(self.peak, results["323C003"].relief_kgh / 1000.0)

    def take(self, _results: dict) -> float:
        peak, self.peak = self.peak, 0.0
        return peak


def extra(peak: ReliefPeak) -> dict:
    """The coupled survey's indicators, and 323C003's two relief valves, which no packet field
    carries."""
    out = dict(rc.EXTRA)
    out["x.c003_relief_th"] = peak.take
    return out


def _run(case, duration_s: float, paths: list) -> dict:
    peak = ReliefPeak()
    return run_plant(case, duration_s, paths, extra(peak), peak.watch)


def _job(key: str) -> dict:
    case = next(c for c in SEAL_LOSS if c.key == key)
    return _run(case, case.duration_s, rc._paths([case]))


def _control_job(duration_s: float, paths: list) -> dict:
    return _run(None, duration_s, paths)


def score(results: list) -> tuple:
    """(claims as claimed, claims read, claims put): what the survey reports."""
    rows = [r for _, rs, _ in results for r in rs]
    return (sum(r["agrees"] is True for r in rows), sum(r["agrees"] is not None for r in rows),
            len(rows))


def main(argv: list) -> int:
    workers = len(SEAL_LOSS) + 1
    if "--workers" in argv:
        i = argv.index("--workers")
        workers = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    out_dir, keys = argv[0], argv[1:] or [c.key for c in SEAL_LOSS]
    cases = [c for c in SEAL_LOSS if c.key in keys]
    os.makedirs(os.path.join(out_dir, "runs"), exist_ok=True)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        control_f = pool.submit(_control_job, max(c.duration_s for c in cases), rc._paths(cases))
        futures = {pool.submit(_job, c.key): c.key for c in cases}
        recs = {}
        for f in as_completed(futures):
            recs[futures[f]] = f.result()
            with open(os.path.join(out_dir, "runs", f"{futures[f]}.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(recs[futures[f]], fh, default=str)
            print(f"{futures[f]} done in {recs[futures[f]]['wall_s']:.0f} s", flush=True)
        control = control_f.result()
    results = [(c, rc.verdicts(c, recs[c.key], control), recs[c.key]) for c in cases]
    with open(os.path.join(out_dir, "seal_loss.json"), "w", encoding="utf-8") as fh:
        json.dump({"control": control, "runs": recs,
                   "verdicts": {c.key: rows for c, rows, _ in results}}, fh, default=str)
    with open(os.path.join(out_dir, "seal_loss.md"), "w", encoding="utf-8") as fh:
        fh.write(rc._md(results, NOT_PUT))
    agree, read, total = score(results)
    print(f"{agree} of {total} claims as claimed ({read} read)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
