"""The Phase 7 command line — run a scenario on V1 and on the rewrite, and compare them.

Usage
-----
    python -m tests.phase7.run <scenario>|all [--side both|v1|port|compare] [--out DIR] [--duration S]

``--side both`` (the default) starts one process per engine — V1 keeps its plant in module
globals, so the two cannot share one — waits for both, then writes ``<scenario>.md`` with the
comparison beside the two records, ``<scenario>_v1.json`` and ``<scenario>_port.json``. ``--side
v1`` or ``port`` runs that engine in this process and writes its record only; ``--side compare``
compares the two records already in ``--out`` and writes the report. ``--duration``
shortens the procedure (a smoke run). The output goes to ``--out``, by default
``<temp>/ureasim_phase7``: the records are working files, not part of the product.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from tests.phase7.compare import compare, report_markdown
from tests.phase7.scenarios import SCENARIOS

#: The project root, the working directory each engine's process is started in.
ROOT = Path(__file__).resolve().parents[2]

#: Default output directory, outside the project tree (CLAUDE.md §6).
DEFAULT_OUT = Path(tempfile.gettempdir()) / "ureasim_phase7"


def _scenario(name: str, duration_s: float | None):
    sc = SCENARIOS[name]
    return dataclasses.replace(sc, duration_s=duration_s) if duration_s else sc


def run_side(name: str, side: str, out: Path, duration_s: float | None = None) -> Path:
    """One engine through one scenario, in this process; the record's path."""
    from tests.phase7.drivers import run_port, run_v1
    rec = (run_v1 if side == "v1" else run_port)(_scenario(name, duration_s))
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{name}_{side}.json"
    path.write_text(json.dumps(rec), encoding="utf-8")
    return path


def run_both(name: str, out: Path, duration_s: float | None = None) -> Path:
    """Both engines, one process each, at once; then the comparison. The report's path."""
    out.mkdir(parents=True, exist_ok=True)
    procs = {}
    for side in ("v1", "port"):
        args = [sys.executable, "-m", "tests.phase7.run", name, "--side", side, "--out", str(out)]
        if duration_s:
            args += ["--duration", str(duration_s)]
        log = open(out / f"{name}_{side}.log", "w", encoding="utf-8")
        procs[side] = (subprocess.Popen(args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                        env={**os.environ, "PYTHONPATH": str(ROOT)}), log)
    for side, (p, log) in procs.items():
        if p.wait() != 0:
            log.close()
            raise RuntimeError(f"{name}: the {side} run failed, see {out / (name + '_' + side)}.log")
        log.close()
    return compare_records(name, out)


def compare_records(name: str, out: Path) -> Path:
    """The comparison of the two records in ``out``; the report's path."""
    recs = {side: json.loads((out / f"{name}_{side}.json").read_text(encoding="utf-8"))
            for side in ("v1", "port")}
    cmp = compare(name, recs["v1"], recs["port"])
    (out / f"{name}_compare.json").write_text(json.dumps(cmp), encoding="utf-8")
    report = out / f"{name}.md"
    report.write_text(report_markdown(cmp, SCENARIOS[name].title), encoding="utf-8")
    return report


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tests.phase7.run", description=__doc__.split(
        "\n")[0])
    ap.add_argument("scenario", choices=[*SCENARIOS, "all"])
    ap.add_argument("--side", choices=("both", "v1", "port", "compare"), default="both")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--duration", type=float, default=None,
                    help="shorten the procedure to this many seconds of plant time")
    a = ap.parse_args(argv)
    names = list(SCENARIOS) if a.scenario == "all" else [a.scenario]
    for name in names:
        if a.side == "both":
            print(run_both(name, a.out, a.duration))
        elif a.side == "compare":
            print(compare_records(name, a.out))
        else:
            print(run_side(name, a.side, a.out, a.duration))
    return 0


if __name__ == "__main__":
    sys.exit(main())
