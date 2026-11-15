"""The liquid critical-pressure factor F_F: one form for each valve's sizing and its live law (handoff
B-132, session 99).

What this pins
--------------
`ureasim.control.valve` carries two forms of IEC 60534's F_F, both V1's. The absolute pair,
`valve_flow_liquid` with `cv_from_design_liquid` and `gravity_outflow_kgh` built on it, holds F_F at its
0.96 intercept; the anchored law, `valve_liquid_anchored`, evaluates 0.96 - 0.28 sqrt(Pv / Pc) on its
design reference and its live flow alike. A valve sized on one form and run on the other would choke at
the wrong pressure. Walked on 2026-11-11 (As-Built Part CX):

* every liquid valve the engine runs, in `ureasim/units/`, calls the anchored law, and nothing outside
  `control/valve.py` calls the absolute pair, which only the equivalence suite drives against V1;
* the vendor-sized valves of `ureasim/data/` (`valve_sizing`, the Flowserve, CCI, Metso and Fisher
  catalogues) take their design stroke from the vendor's printed capacity ratio, which carries no F_F;
* the anchored law's design reference and its live flow use the full correlation, so its choke falls
  where the full F_F puts it and the design point returns its duty exactly.

No mismatch was found; no relation changed.
"""

from __future__ import annotations

import ast
import math
from pathlib import Path

import pytest

from ureasim.control import valve
from ureasim.control.valve import FF_CONST, FL_GLOBE, PC_WATER_BARA, valve_liquid_anchored

ROOT = Path(__file__).resolve().parents[3] / "ureasim"

#: The absolute pair, on the flat intercept, and the anchored law, on the full correlation.
ABSOLUTE = {"valve_flow_liquid", "cv_from_design_liquid", "gravity_outflow_kgh"}
ANCHORED = "valve_liquid_anchored"


def _called(path: Path) -> set[str]:
    """The names a module calls, as written (``f(...)`` or ``mod.f(...)``)."""
    out = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call):
            f = node.func
            out.add(f.id if isinstance(f, ast.Name) else getattr(f, "attr", ""))
    return out


CALLS = {p.relative_to(ROOT).as_posix(): _called(p) for p in sorted(ROOT.rglob("*.py"))
         if p.relative_to(ROOT).as_posix() != "control/valve.py"}


def test_no_engine_valve_runs_the_flat_intercept():
    """Nothing outside `control/valve.py` sizes or runs a valve on the absolute pair."""
    assert {m: c & ABSOLUTE for m, c in CALLS.items() if c & ABSOLUTE} == {}


def test_the_liquid_valves_run_the_anchored_law():
    """The engine's liquid valves, nine calls in seven modules at session 99's walk, all on the
    anchored law."""
    users = sorted(m for m, c in CALLS.items() if ANCHORED in c)
    assert users == ["units/desorption/first_desorber.py", "units/desorption/hydrolyser.py",
                     "units/desorption/second_desorber.py", "units/recirc/flash_tank.py",
                     "units/recirc/rectifying_column.py", "units/steam/steam_valves.py",
                     "units/synthesis/stripper_sump.py"]


def test_the_vendor_sizing_carries_no_ff():
    """The catalogued valves' design stroke is the vendor's capacity ratio: `valve_sizing` and the
    catalogues compute no choke, so they cannot hold a second form of F_F."""
    for name in ("valve_sizing.py", "control_valves.py", "control_valves_metso.py",
                 "control_valves_fisher.py"):
        src = (ROOT / "data" / name).read_text(encoding="utf-8")
        assert "FF_CONST" not in src and "PC_WATER_BARA" not in src, name
        assert not (CALLS[f"data/{name}"] & (ABSOLUTE | {ANCHORED})), name


@pytest.mark.parametrize("pv", [0.0, 5.0, 12.0])
def test_the_anchored_law_chokes_on_the_full_correlation(pv):
    """A hot liquor through a valve whose design was unchoked: the anchored flow is the full-F_F
    choke's ratio to the design, at Pv 0 the intercept's, and at the design the duty exactly."""
    w_des, h, p1, p2, rho = 50_000.0, 0.6, 15.0, 1.5, 900.0
    p1_des, p2_des, pv_des = 15.0, 10.0, 0.0
    frac = valve.cv_fraction(h, "equal_pct") / valve.cv_fraction(0.5, "equal_pct")
    ff = FF_CONST - 0.28 * math.sqrt(pv / PC_WATER_BARA)
    dp_eff = min(p1 - p2, FL_GLOBE ** 2 * (p1 - ff * pv))
    expect = w_des * frac * math.sqrt(dp_eff / (p1_des - p2_des))
    got = valve_liquid_anchored(w_des, h, p1, p2, rho, 0.5, p1_des, p2_des, rho, pv_bara=pv,
                                pv_des_bara=pv_des)
    assert got == pytest.approx(expect, rel=1e-12)
    assert valve_liquid_anchored(w_des, 0.5, p1_des, p2_des, rho, 0.5, p1_des, p2_des, rho,
                                 pv_bara=pv_des, pv_des_bara=pv_des) == w_des
