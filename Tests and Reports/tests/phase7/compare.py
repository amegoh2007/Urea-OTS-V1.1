"""The Phase 7 comparison — V1's record and the rewrite's, side by side.

What this is
------------
Reads the two records `tests.phase7.drivers` writes for one scenario and reduces them to what the
validation asks of a transient: for each sampled path, where the two engines start, how far apart
they run and where they end; when each trip latched on each side; what each engine answered to the
procedure's commands; whether a watched pressure rang (handoff B-51); and, for the cold start,
PT-329201's rise identified as a first-order-plus-dead-time step by Smith's two-point method and set
against the 3 June 2025 start-up trend's band. `report_markdown` writes it for `project.md`'s log
and the As-Built reference.

Nothing here judges a difference: the comparison measures, the process engineer decides (CLAUDE.md
§5.6). A path with a decided divergence differs by design.
"""

from __future__ import annotations

import math

from tests.phase7.drivers import COLD_P0_BARA, smith_foptd

#: One atmosphere [bar], for PT-329201's gauge reading (decision 71).
ATM_BAR = 1.01325

#: The synthesis section's trips, listed whether they latched or not: V1's six; the port has no 21.4
#: (no flag in AC4's application software, handoff A-12, decided 2026-10-09) and no 22.2 (in no
#: plant document, decision 189).
TRIP_KEYS = ("21_2", "21_4", "21_8", "21_10", "22_1", "22_2")

#: PT-329201's path in both packets [bar a].
PT_329201 = "SCRUB_322E003.P_overflow"

#: The cold start's acceptance band, from the 3 June 2025 synthesis start-up trend
#: (``References/3.6.2025 Synthesis startup.md``, V1 ``test_transient_coldstart.py``): the time
#: constant [s], the dead time's ceiling [s] and the final pressure [bar g].
COLD_TAU_BAND_S = (2884.0, 4055.0)
COLD_TD_MAX_S = 572.0
COLD_FINAL_BAND_BARG = (137.5, 150.5)


def _finite(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def path_table(v1: dict, port: dict) -> list:
    """Per path: first, last and range on each side, and the largest gap between them.

    Process utility: a transient comparison is read first by where each engine started (the same
    initial condition should give the same first sample), then by where each went and how far apart
    they ran on the way. Samples are paired by time; a sample one side does not have is skipped.
    """
    rows = []
    t_port = {round(t, 3): i for i, t in enumerate(port["t"])}
    for path in v1["values"]:
        a_all, b_all = v1["values"][path], port["values"].get(path, [])
        pairs = [(a_all[i], b_all[t_port[round(t, 3)]]) for i, t in enumerate(v1["t"])
                 if round(t, 3) in t_port] if b_all else []
        if any(isinstance(a, bool) or isinstance(b, bool) for a, b in pairs):
            flips = sum(1 for a, b in pairs if bool(a) != bool(b))
            rows.append({"path": path, "kind": "flag", "disagree_samples": flips,
                         "v1_last": pairs[-1][0] if pairs else None,
                         "port_last": pairs[-1][1] if pairs else None})
            continue
        num = [(a, b) for a, b in pairs if _finite(a) and _finite(b)]
        if not num:
            rows.append({"path": path, "kind": "missing",
                         "v1_n": sum(_finite(x) for x in a_all),
                         "port_n": sum(_finite(x) for x in b_all)})
            continue
        gaps = [abs(a - b) for a, b in num]
        i_max = max(range(len(gaps)), key=gaps.__getitem__)
        rows.append({
            "path": path, "kind": "value",
            "v1_first": num[0][0], "port_first": num[0][1],
            "v1_last": num[-1][0], "port_last": num[-1][1],
            "v1_min": min(a for a, _ in num), "v1_max": max(a for a, _ in num),
            "port_min": min(b for _, b in num), "port_max": max(b for _, b in num),
            "max_gap": gaps[i_max], "max_gap_t_s": [t for t in v1["t"]
                                                    if round(t, 3) in t_port][i_max],
        })
    return rows


def trip_table(v1: dict, port: dict) -> list:
    """Per trip, the first latch time on each side [s] and the difference."""
    keys = sorted(set(TRIP_KEYS) | set(v1["trips"]) | set(port["trips"]))
    out = []
    for k in keys:
        a, b = v1["trips"].get(k), port["trips"].get(k)
        out.append({"trip": k, "v1_s": a, "port_s": b,
                    "port_minus_v1_s": (b - a) if (a is not None and b is not None) else None})
    return out


def ringing_table(v1: dict, port: dict) -> list:
    """Per watched pressure (B-51): the worst 10-s window on each side and the ringing count."""
    out = []
    for name in v1["watch"]:
        a, b = v1["watch"][name], port["watch"].get(name, {})
        out.append({"watch": name,
                    "v1_ringing_windows": a["ringing_windows"],
                    "port_ringing_windows": b.get("ringing_windows"),
                    "v1_first_ringing_s": a["first_ringing_s"],
                    "port_first_ringing_s": b.get("first_ringing_s"),
                    "v1_max_reversals_10s": a["max_reversals_10s"],
                    "port_max_reversals_10s": b.get("max_reversals_10s"),
                    "v1_max_p2p_10s": a["max_p2p_10s"], "port_max_p2p_10s": b.get("max_p2p_10s")})
    return out


def cold_start(rec: dict) -> dict:
    """PT-329201's rise on one side, identified, and set against the start-up trend's band."""
    fit = smith_foptd(rec["t"], rec["values"].get(PT_329201, []), COLD_P0_BARA)
    final_barg = None if fit["p_final"] is None else fit["p_final"] - ATM_BAR
    return {**fit, "p_final_barg": final_barg,
            "tau_in_band": (fit["tau_s"] is not None
                            and COLD_TAU_BAND_S[0] <= fit["tau_s"] <= COLD_TAU_BAND_S[1]),
            "td_in_band": fit["td_s"] is not None and fit["td_s"] <= COLD_TD_MAX_S,
            "final_in_band": (final_barg is not None
                              and COLD_FINAL_BAND_BARG[0] <= final_barg
                              <= COLD_FINAL_BAND_BARG[1])}


#: The steady state's agreement band: a leaf agrees when its last values differ by at most this
#: share of V1's, or by the absolute floor where V1's value is near zero.
STEADY_REL_TOL = 0.01
STEADY_ABS_FLOOR = 1e-3


def _last_finite(vals: list):
    return next((x for x in reversed(vals) if _finite(x)), None)


def _half_finite(vals: list):
    return next((x for x in vals[len(vals) // 2:] if _finite(x)), None)


def steady_table(v1: dict, port: dict) -> dict:
    """Every leaf both packets publish, at the end of an hour on the design: V1's and the port's
    last values, their gap, and each engine's own drift over the second half hour.

    Process utility: the design point is where both engines are anchored, so a leaf that differs
    there is either a decided divergence that acts at design or a defect; a leaf that drifts on
    either side is a state that is not at rest on the seed. A leaf one side publishes and the
    other does not is listed by name.
    """
    rows, v1_only, flags = [], [], []
    for path, a_vals in v1["values"].items():
        b_vals = port["values"].get(path)
        if b_vals is None:
            v1_only.append(path)
            continue
        a, b = _last_finite(a_vals), _last_finite(b_vals)
        if any(isinstance(x, bool) for x in a_vals + b_vals if x is not None):
            if bool(a_vals[-1]) != bool(b_vals[-1]):
                flags.append({"path": path, "v1": a_vals[-1], "port": b_vals[-1]})
            continue
        if a is None or b is None:
            continue
        gap = abs(a - b)
        rel = gap / abs(a) if abs(a) > STEADY_ABS_FLOOR else gap
        a_half, b_half = _half_finite(a_vals), _half_finite(b_vals)
        rows.append({"path": path, "v1": a, "port": b, "gap": gap, "rel": rel,
                     "agree": rel <= STEADY_REL_TOL or gap <= STEADY_ABS_FLOOR,
                     "v1_drift": None if a_half is None else a - a_half,
                     "port_drift": None if b_half is None else b - b_half})
    port_only = sorted(set(port["values"]) - set(v1["values"]))
    return {"rows": rows, "flags": flags, "v1_only": sorted(v1_only), "port_only": port_only,
            "n_agree": sum(r["agree"] for r in rows), "n_compared": len(rows)}


def compare(scenario_name: str, v1: dict, port: dict) -> dict:
    """The whole comparison of one scenario."""
    out = {"scenario": scenario_name,
           "stopped": {"v1": v1["stopped"], "port": port["stopped"]},
           "speed_ms_per_tick": {"v1": v1["ms_per_tick"], "port": port["ms_per_tick"]},
           "commands": {"v1": v1["commands"], "port": port["commands"]},
           "paths": path_table(v1, port), "trips": trip_table(v1, port),
           "ringing": ringing_table(v1, port)}
    if scenario_name == "cold_start":
        out["cold_start"] = {"v1": cold_start(v1), "port": cold_start(port)}
    if scenario_name == "steady_state":
        out["steady"] = steady_table(v1, port)
    return out


def _f(x, nd: int = 3) -> str:
    if x is None:
        return "-"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def report_markdown(cmp: dict, title: str = "") -> str:
    """The comparison as a Markdown section."""
    lines = [f"## {cmp['scenario']}" + (f" — {title}" if title else ""), ""]
    st = cmp["stopped"]
    lines.append(f"Stopped: V1 {st['v1']['why']} at {st['v1']['t_s']} s; "
                 f"port {st['port']['why']} at {st['port']['t_s']} s. Speed: V1 "
                 f"{cmp['speed_ms_per_tick']['v1']} ms/tick, port "
                 f"{cmp['speed_ms_per_tick']['port']} ms/tick.")
    lines.append("")
    if any(c for c in cmp["commands"].values()):
        lines += ["| t [s] | command | V1 | port |", "|---|---|---|---|"]
        for a, b in zip(cmp["commands"]["v1"], cmp["commands"]["port"]):
            lines.append(f"| {a[0]} | `{a[1]}` | {'accepted' if a[2] else a[3]} | "
                         f"{'accepted' if b[2] else b[3]} |")
        lines.append("")
    lines += ["| trip | V1 latched [s] | port latched [s] | port - V1 [s] |", "|---|---|---|---|"]
    for r in cmp["trips"]:
        lines.append(f"| {r['trip']} | {_f(r['v1_s'], 1)} | {_f(r['port_s'], 1)} | "
                     f"{_f(r['port_minus_v1_s'], 1)} |")
    lines += ["", "| watch (B-51) | V1 ringing windows | port ringing windows | V1 max p2p 10 s | "
              "port max p2p 10 s |", "|---|---|---|---|---|"]
    for r in cmp["ringing"]:
        lines.append(f"| {r['watch']} | {r['v1_ringing_windows']} | {r['port_ringing_windows']} "
                     f"| {_f(r['v1_max_p2p_10s'])} | {_f(r['port_max_p2p_10s'])} |")
    if "cold_start" in cmp:
        lines += ["", "| cold start, PT-329201 | tau [s] | dead time [s] | final [bar g] | "
                  "in band (tau / td / final) |", "|---|---|---|---|---|"]
        for side in ("v1", "port"):
            c = cmp["cold_start"][side]
            lines.append(f"| {side} | {_f(c['tau_s'], 0)} | {_f(c['td_s'], 0)} | "
                         f"{_f(c['p_final_barg'], 2)} | {_f(c['tau_in_band'])} / "
                         f"{_f(c['td_in_band'])} / {_f(c['final_in_band'])} |")
        lines.append(f"| DCS band | {COLD_TAU_BAND_S[0]:.0f}-{COLD_TAU_BAND_S[1]:.0f} | "
                     f"<= {COLD_TD_MAX_S:.0f} | {COLD_FINAL_BAND_BARG[0]}-"
                     f"{COLD_FINAL_BAND_BARG[1]} | |")
    if "steady" in cmp:
        st = cmp["steady"]
        lines += ["", f"Steady state: {st['n_agree']} of {st['n_compared']} numeric leaves agree "
                  f"within {STEADY_REL_TOL:.0%} (or {STEADY_ABS_FLOOR:g} absolute); "
                  f"{len(st['flags'])} flags differ; {len(st['v1_only'])} leaves V1's only, "
                  f"{len(st['port_only'])} the port's only.", "",
                  "| path | V1 | port | gap | rel | V1 drift | port drift |",
                  "|---|---|---|---|---|---|---|"]
        for r in sorted((r for r in st["rows"] if not r["agree"]), key=lambda r: -r["rel"]):
            lines.append(f"| {r['path']} | {_f(r['v1'], 4)} | {_f(r['port'], 4)} | "
                         f"{_f(r['gap'], 4)} | {_f(r['rel'], 4)} | {_f(r['v1_drift'], 4)} | "
                         f"{_f(r['port_drift'], 4)} |")
        for f in st["flags"]:
            lines.append(f"| {f['path']} | {_f(f['v1'])} | {_f(f['port'])} | flag | | | |")
        lines += ["", "V1's only: " + (", ".join(st["v1_only"]) or "none") + ".", "",
                  "The port's only: " + (", ".join(st["port_only"]) or "none") + "."]
        return "\n".join(lines) + "\n"
    lines += ["", "| path | first (V1 / port) | V1 range | port range | last (V1 / port) | max gap "
              "| at [s] |", "|---|---|---|---|---|---|---|"]
    for r in cmp["paths"]:
        if r["kind"] == "value":
            lines.append(f"| {r['path']} | {_f(r['v1_first'])} / {_f(r['port_first'])} | "
                         f"{_f(r['v1_min'])} - {_f(r['v1_max'])} | {_f(r['port_min'])} - "
                         f"{_f(r['port_max'])} | {_f(r['v1_last'])} / {_f(r['port_last'])} | "
                         f"{_f(r['max_gap'])} | {_f(r['max_gap_t_s'], 0)} |")
        elif r["kind"] == "flag":
            lines.append(f"| {r['path']} | | | | {_f(r['v1_last'])} / {_f(r['port_last'])} | "
                         f"{r['disagree_samples']} samples disagree | |")
        else:
            lines.append(f"| {r['path']} | missing: V1 {r['v1_n']}, port {r['port_n']} samples "
                         f"| | | | | |")
    return "\n".join(lines) + "\n"


__all__ = ["ATM_BAR", "TRIP_KEYS", "PT_329201", "COLD_TAU_BAND_S", "COLD_TD_MAX_S", "COLD_FINAL_BAND_BARG",
           "STEADY_REL_TOL", "STEADY_ABS_FLOOR", "path_table", "trip_table", "ringing_table",
           "cold_start", "steady_table", "compare", "report_markdown"]
