"""Handoff A-13's audit: every check valve and every anchored design differential is a subtraction.

What is being proved
--------------------
An anchored law returns its design flow to the last bit only if the differential it is normalised
against is the SAME float its live arguments make at design. A rounded decimal does not oblige —
``5.60 - 4.20`` is ``1.4000000000000004``, not ``1.40`` — so the rule (A-13, restated by the process
engineer 2026-09-30 for every unit) is that a design differential is written as the subtraction of
its two design pressures, never as a literal. Closed 2026-10-16:

* every module-level differential in ``ureasim/data`` and ``ureasim/units`` is a subtraction in the
  source, and equals the float subtraction of the two pressures it names;
* every ``check_valve_kgh`` call passes its differential by one of those names;
* the assembled flowsheet's first tick passes the design flows to the bit — XV-322902's tie-in
  check valve the PFD's 54 618 kg/h of CO2, LV-322501's anchored letdown its 130 482 kg/h.

Four module-level names carry ``DP`` and are not an anchored law's design differential: a vent
law's two floors, a pump's rated head and a numerical probe (`NOT_DIFFERENTIALS`).
"""

from __future__ import annotations

import ast
import pathlib
import re

from ureasim.data import unit_320, unit_322_loop, unit_322e001, unit_322e002
from ureasim.data import unit_324, unit_328c002, unit_328c004
from ureasim.data.design_point import R323_FEED_DES_KGH
from ureasim.data.unit_321 import CO2_DES_KGH
from ureasim.engine.plant import build_plant
from ureasim.engine.scheduler import Scheduler
from ureasim.thermo import iapws
from ureasim.units.synthesis import reactor_boil, scrubber, stripper_sump

ROOT = pathlib.Path(__file__).resolve().parents[2] / "ureasim"

#: Every anchored design differential, its module, and the two design pressures it subtracts.
DIFFERENTIALS = {
    "CO2_DP_HP_DES": (unit_320, unit_320.CO2_P_DES_BARA, unit_320.SYN_P_DES_BARA),
    "DP_TO_LOOP_DES_BAR": (unit_322e001, unit_322e001.P_DES_BARA, unit_322e001.SYN_P_DES_BARA),
    "LV_322501_DP_DES_BAR": (unit_322e001, unit_322e001.P_DES_BARA,
                             unit_322e001.P_DOWNSTREAM_BARA),
    "LEAK_DP_DES_BAR": (unit_322e002, unit_322e002.SYN_P_DES_BARA, unit_322e002.P_LP_BARA),
    "unit_322_loop.LIQUOR_DP_DES_BAR": (unit_322_loop, unit_322_loop.HPCC_P_DES_BARA,
                                        unit_322_loop.SYN_P_DES_BARA),
    "REACT_FEED_DP_DES_BAR": (unit_322_loop, unit_322_loop.HPCC_P_DES_BARA,
                              unit_322_loop.REACT_TOP_P_DES_BARA),
    "C002_DP_COL_BAR": (unit_328c002, iapws.psat_bara(unit_328c002.C002_T_BOT_C),
                        unit_328c002.C002_P_TOP_BARA),
    "C004_DP_COL_BAR": (unit_328c004, iapws.psat_bara(unit_328c004.C004_T_C),
                        unit_328c004.C004_P_BARA),
    "BOIL_DP_DES_BAR": (reactor_boil, reactor_boil.OFFGAS_P_DES_BARA, reactor_boil.SYN_P_DES_BARA),
    "scrubber.LIQUOR_DP_DES_BAR": (scrubber, scrubber.OVERFLOW_P_DES_BARA,
                                   scrubber.SYN_P_DES_BARA),
    "LV_322501_DP_ANCHOR_BAR": (stripper_sump, stripper_sump.SYN_P_DES_BARA,
                                stripper_sump.LV_322501_P_DOWN_BARA),
    "LV_324501_DP_DES_BAR": (unit_324, unit_324.LV_324501_P_UP_BARA,
                             unit_324.LV_324501_P_DOWN_BARA),
}

#: The names that carry ``DP`` and are no anchored law's design differential, and why.
NOT_DIFFERENTIALS = {
    "VENT_DP_FLOOR_BAR": "V1's floor on PV-323203's differential, a clamp (B-30)",
    "VENT_DP_MIN_BAR": "the port's floor on PV-323203's differential, a clamp (B-30)",
    "P006_DP_PUMP_BAR": "328P006's rated head; LV-328503's design inlet is built on the same sum",
    "DP_PROBE_BAR": "the steam network's numerical probe on its header residuals",
}

_DP_NAME = re.compile(r"(^|_)DP(_|$)")


def _module_level_dp_names() -> dict:
    """Every module-level ``*DP*`` assignment under data and units: name -> (path, value node)."""
    found = {}
    for path in sorted(list((ROOT / "data").glob("*.py")) + list((ROOT / "units").rglob("*.py"))):
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            targets = (node.targets if isinstance(node, ast.Assign)
                       else [node.target] if isinstance(node, ast.AnnAssign) else [])
            for t in targets:
                if isinstance(t, ast.Name) and _DP_NAME.search(t.id):
                    found.setdefault(t.id, []).append((path, node.value))
    return found


def _bare(name: str) -> str:
    return name.split(".")[-1]


def test_every_design_differential_is_a_subtraction_in_the_source():
    """No differential is written as a literal: each is ``a - b`` (A-13's rule), and every
    ``DP`` name the source assigns is either audited here or named as no differential."""
    found = _module_level_dp_names()
    audited = {_bare(n) for n in DIFFERENTIALS}
    assert set(found) == audited | set(NOT_DIFFERENTIALS)
    for name in audited:
        for path, value in found[name]:
            assert isinstance(value, ast.BinOp) and isinstance(value.op, ast.Sub), (
                name, str(path), ast.unparse(value))


def test_every_design_differential_is_the_float_its_two_pressures_make():
    """Bit for bit: the constant is the subtraction of the two design pressures it names, so an
    anchored law's live differential at design is the same float."""
    for name, (module, up, down) in DIFFERENTIALS.items():
        assert getattr(module, _bare(name)) == up - down, name


def test_every_check_valve_takes_its_differential_by_an_audited_name():
    """`check_valve_kgh(w_des, p_up, p_down, dp_des, p_crack)`: its fourth argument at every call
    site under units is a name this audit pins, never a literal."""
    calls = []
    for path in (ROOT / "units").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "check_valve_kgh"):
                calls.append((path.name, node.args[3]))
    assert [p for p, _ in calls] == ["co2_line.py"]
    for path, arg in calls:
        assert isinstance(arg, ast.Name) and arg.id in {_bare(n) for n in DIFFERENTIALS}, path


def test_the_assembled_flowsheet_boots_on_the_design_flows():
    """The plant's first tick on its design seed: XV-322902's check valve passes the PFD's CO2
    and LV-322501's anchored letdown the stripper's design bottoms, each ``==``, not approx."""
    sch, plant = build_plant()
    r = Scheduler(sch, plant).tick().results
    assert r["320K002"].feed_kgh == CO2_DES_KGH == 54618.0
    assert r["322E001"].sump.drain_kgh == R323_FEED_DES_KGH == 130482.0
