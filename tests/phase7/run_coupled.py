"""Put every case of `tests.phase7.coupled` (``Scenarios5.md``) to the port's plant, both waves.

Usage
-----
    python -m tests.phase7.run_coupled OUT_DIR [KEY ...] [--workers N]

Each case and one unperturbed control start from the design seed and step the scheduler at the
fixed 0.1 s (`run_deviations.run_plant`): the case's commands are applied after the settling
minute, the packet and the `EXTRA` indicators are sampled every 5 s for 45 minutes, and each claim
is read as the case's departure from the control at the same plant time — in its wave
(`coupled.W1_S`, `coupled.W2_S`): the largest departure in the first five minutes, the mean over 15
to 45 minutes, or the second less the first for a reversal. Packet values are the console's: a move
inside an indicator's display resolution reads as none, which is why PT-329201 is read unrounded.

`OUT_DIR` receives ``runs/<key>.json`` as each run finishes, then ``coupled.json`` (every record and
verdict) and ``coupled.md`` (the verdict tables).
"""

from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from statistics import fmean

from tests.phase7.coupled import COUPLED, NOT_PUT, W1_S, W2_S, Coupled
from tests.phase7.run_deviations import REL_TOL, run_plant


def _offgas_th(r) -> float:
    from ureasim.core.stream import MW_COMP
    og = r["322R001"].reaction.offgas_kmolh
    return sum(og.get(k, 0.0) * MW_COMP[k] for k in MW_COMP) / 1000.0


#: Indicators no packet field carries, read off the tick's results.
EXTRA = {
    "x.p_syn_bara": lambda r: r["PT-329201"].p_syn_bara,
    "x.reactor_offgas_th": _offgas_th,
    "x.stripper_lambda": lambda r: r["322E001"].stripper.shell_lambda,
    "x.stripper_held_kg": lambda r: r["322E001"].sump.held_kg,
    "x.hpcc_sat_frac": lambda r: r["322E002"].holdup.sat_frac,
    "x.hpcc_p_bub_bara": lambda r: r["322E002"].holdup.condenser.p_bub_bara,
    "x.hpcc_melt_nc": lambda r: r["322E002"].holdup.condenser.melt_nc,
    "x.stripper_submerged": lambda r: r["322E001"].stripper.submerged_frac,
    "x.stripper_backup_kgh": lambda r: r["322E001"].sump.backup_kgh,
    "x.reactor_m_out_kgh": lambda r: r["322R001"].m_out_kgh,
    "x.lpcc_w308_h2o": lambda r: r["323E003"].w_308["H2O"],
    "x.reactor_pt_bara": lambda r: r["322R001"].p_bara,
    "x.stage2_bisected": lambda r: float(r["324E003"].bisected),
}


def _paths(cases) -> list:
    return sorted({c.path for case in cases for c in case.claims if not c.path.startswith("x.")})


def _job(key: str) -> dict:
    case = next(c for c in COUPLED if c.key == key)
    return run_plant(case, case.duration_s, _paths([case]), EXTRA)


def _control_job(duration_s: float, paths: list) -> dict:
    return run_plant(None, duration_s, paths, EXTRA)


def _departures(rec: dict, control: dict, path: str) -> list:
    n = len(rec["t"])
    return [(t, float(a) - float(c)) for t, a, c in
            zip(rec["t"], rec["values"][path], control["values"][path][:n])
            if a is not None and c is not None]


def verdicts(case: Coupled, rec: dict, control: dict) -> list:
    """Each claim as measured in its wave: the departure, its sign, and whether it is the claim's."""
    out = []
    for c in case.claims:
        deps = _departures(rec, control, c.path)
        w1 = [d for t, d in deps if W1_S[0] < t <= W1_S[1]]
        w2 = [d for t, d in deps if W2_S[0] <= t <= W2_S[1]]
        row = {"step": c.step, "path": c.path, "claim": c.claim, "claimed": c.sign,
               "wave": c.wave, "w1": None, "w2": None, "rev": None, "measured": None,
               "agrees": None}
        if w1 and w2:
            row["w1"] = max(w1, key=abs)
            row["w2"] = fmean(w2)
            row["rev"] = row["w2"] - row["w1"]
            value = {"W1": row["w1"], "W2": row["w2"], "REV": row["rev"]}[c.wave]
            base = control["values"][c.path][0]
            tol = REL_TOL * max(abs(float(base)) if base is not None else 1.0, 1.0)
            row["measured"] = 0 if abs(value) <= tol else (1 if value > 0 else -1)
            row["agrees"] = row["measured"] == c.sign
            row["base"] = float(base) if base is not None else None
        out.append(row)
    return out


def _diagnostics(rec: dict) -> dict:
    """What B-102 and B-103 did on the run: the least lambda and the most liquor held back."""
    lam = [v for v in rec["values"]["x.stripper_lambda"] if v is not None]
    held = [v for v in rec["values"]["x.stripper_held_kg"] if v is not None]
    sat = [v for v in rec["values"]["x.hpcc_sat_frac"] if v is not None]
    return {"lambda_min": min(lam) if lam else None, "held_max_kg": max(held) if held else None,
            "hpcc_sat_min": min(sat) if sat else None, "trips": rec["trips"],
            "flags": rec["flags"]}


def _md(results: list, not_put: dict = NOT_PUT) -> str:
    arrow = {1: "rises", -1: "falls", 0: "no change", None: "n/a"}
    fmt = (lambda v: "" if v is None else f"{v:+.4g}")
    lines = []
    for case, rows, rec in results:
        agree = sum(r["agrees"] is True for r in rows)
        lines += [f"### {case.key} — {case.title} ({agree} of {len(rows)})", "",
                  f"{case.helwan}.", "",
                  "| step | indicator | wave | claimed | W1 (0-5 min) | W2 (15-45 min) | W2 - W1 "
                  "| measured | agrees |", "|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            lines.append(f"| {r['step']} | {r['path']} — {r['claim']} | {r['wave']} | "
                         f"{arrow[r['claimed']]} | {fmt(r['w1'])} | {fmt(r['w2'])} | "
                         f"{fmt(r['rev'])} | {arrow[r['measured']]} | "
                         f"{'yes' if r['agrees'] else 'NO'} |")
        refused = [c for c in rec["commands"] if not c[1]]
        diag = _diagnostics(rec)
        lines += ["", f"lambda min {diag['lambda_min']}, held max {diag['held_max_kg']} kg, "
                  f"HPCC saturation min {diag['hpcc_sat_min']}; trips {diag['trips']}; "
                  f"flags {diag['flags']}" + (f"; refused {refused}" if refused else ""), ""]
        for u in case.unmodelled:
            lines.append(f"* not modelled: {u}")
        lines.append("")
    for key, (source, why) in not_put.items():
        lines += [f"### {key} — {source}: not put", "", why, ""]
    return "\n".join(lines)


def main(argv: list) -> int:
    workers = 13
    if "--workers" in argv:
        i = argv.index("--workers")
        workers = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    out_dir, keys = argv[0], argv[1:] or [c.key for c in COUPLED]
    cases = [c for c in COUPLED if c.key in keys]
    os.makedirs(os.path.join(out_dir, "runs"), exist_ok=True)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        control_f = pool.submit(_control_job, max(c.duration_s for c in cases), _paths(cases))
        futures = {pool.submit(_job, c.key): c.key for c in cases}
        recs = {}
        for f in as_completed(futures):
            rec = f.result()
            recs[futures[f]] = rec
            with open(os.path.join(out_dir, "runs", f"{futures[f]}.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(rec, fh, default=str)
            print(f"{futures[f]} done in {rec['wall_s']:.0f} s ({len(recs)} of {len(cases)})",
                  flush=True)
        control = control_f.result()
    with open(os.path.join(out_dir, "runs", "control.json"), "w", encoding="utf-8") as fh:
        json.dump(control, fh, default=str)
    results = [(c, verdicts(c, recs[c.key], control), recs[c.key]) for c in cases]
    with open(os.path.join(out_dir, "coupled.json"), "w", encoding="utf-8") as fh:
        json.dump({"control": control, "runs": recs,
                   "verdicts": {c.key: rows for c, rows, _ in results},
                   "diagnostics": {c.key: _diagnostics(rec) for c, _, rec in results}},
                  fh, default=str)
    with open(os.path.join(out_dir, "coupled.md"), "w", encoding="utf-8") as fh:
        fh.write(_md(results))
    agree = sum(r["agrees"] is True for _, rows, _ in results for r in rows)
    total = sum(len(rows) for _, rows, _ in results)
    print(f"{agree} of {total} claims as claimed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
