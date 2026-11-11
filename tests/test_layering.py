"""The package's import directions, as `Claude.md` section 1 rules 2 and 3 state them (handoff A-31).

What this enforces
------------------
The layers rank downward, ``hmi`` > ``net`` > ``engine`` > ``units`` > ``control`` > ``core`` >
``thermo``; an import that points upward is a defect (rule 2). ``data``, the constants of rule 7, sits
beside the ranking, between ``control`` and ``units``: it may import ``thermo``, ``core`` and
``control`` (the sizing helpers that turn a datasheet into a constant) and nothing above them, and
``thermo``, ``core`` and ``control`` read nothing from it, except ``thermo``'s one read of the leaf
``data/design_point.py``, which imports nothing of ``ureasim`` (decision 182). The console reads
``net``, ``data`` and, for the atmosphere its faceplates convert gauge pressure on, ``core``'s units
of measure alone (decision 183, handoff A-32). Nothing at or below ``net`` names PyQt6 (rule 3).

The graph is read from the source by ``ast``, so a module need not import cleanly to be checked.
Measured 2026-11-11 (session 99): 20 package-to-package edges, every one of them inside these rules
(As-Built Part CX).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "ureasim"

#: The ranked layers, lowest first (`Claude.md` section 1 rule 2).
RANK = {"thermo": 0, "core": 1, "control": 2, "units": 3, "engine": 4, "net": 5, "hmi": 6}

#: What ``data`` may import, and the ranked layers that may not import it.
DATA_MAY_IMPORT = {"thermo", "core", "control"}
BELOW_DATA = {"thermo", "core", "control"}

#: The decided exceptions, (importing module, imported module), both relative to ``ureasim``.
EXCEPTIONS = {
    # Decision 182: thermo's empirical fits read their design anchors from the constants layer.
    ("thermo/empirical.py", "ureasim.data.design_point"),
}

#: What the console may import beyond ``net`` and ``data`` (decision 183).
HMI_MAY_IMPORT = {"ureasim.core.units_of_measure"}

#: The packages at or below the transport, which must never name Qt (`Claude.md` section 1 rule 3).
HEADLESS = ("net", "engine", "units", "control", "core", "thermo")


def _imports(path: Path) -> list[tuple[str, int]]:
    """Every ``ureasim`` module a source file imports, with its line, relative imports resolved."""
    rel = path.relative_to(ROOT).parts
    out = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            out += [(a.name, node.lineno) for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = list(rel[:-1])[: len(rel) - node.level]
                out.append((".".join(["ureasim", *base, *([node.module] if node.module else [])]),
                            node.lineno))
            elif node.module:
                out.append((node.module, node.lineno))
    return [(m, n) for m, n in out if m.split(".")[0] == "ureasim" and "." in m]


def _edges() -> list[tuple[str, str, str, int]]:
    """(source package, source file, imported module, line) for every cross-package import."""
    edges = []
    for path in sorted(ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT)
        if len(rel.parts) < 2:
            continue
        src = rel.parts[0]
        for mod, line in _imports(path):
            if mod.split(".")[1] != src:
                edges.append((src, rel.as_posix(), mod, line))
    return edges


EDGES = _edges()


def test_the_graph_was_read():
    """The scan finds the package's cross-layer imports (several hundred), so an empty pass is not a
    false green."""
    assert len(EDGES) > 400


def test_no_ranked_layer_imports_upward():
    bad = [e for e in EDGES if e[0] in RANK and e[2].split(".")[1] in RANK
           and RANK[e[2].split(".")[1]] > RANK[e[0]]]
    assert bad == []


def test_data_sits_between_control_and_units():
    up = [e for e in EDGES if e[0] == "data" and e[2].split(".")[1] not in DATA_MAY_IMPORT]
    down = [e for e in EDGES if e[0] in BELOW_DATA and e[2].split(".")[1] == "data"
            and (e[1], e[2]) not in EXCEPTIONS]
    assert up == [] and down == []


def test_the_exceptions_hold_and_are_live():
    """Each decided exception still exists (a stale one is deleted, not kept), and the design-point
    module ``thermo`` reads imports nothing of ``ureasim``, so it closes no cycle."""
    live = {(e[1], e[2]) for e in EDGES}
    assert EXCEPTIONS <= live
    assert _imports(ROOT / "data" / "design_point.py") == []


def test_the_console_reads_the_transport_and_the_constants_only():
    bad = [e for e in EDGES if e[0] == "hmi" and e[2].split(".")[1] not in ("net", "data")
           and e[2] not in HMI_MAY_IMPORT]
    assert bad == []


@pytest.mark.parametrize("package", HEADLESS)
def test_nothing_below_the_console_names_qt(package):
    """`Claude.md` section 1 rule 3's grep, as a test: no file at or below ``net`` contains
    ``PyQt6``."""
    hits = [p.relative_to(ROOT).as_posix() for p in (ROOT / package).rglob("*.py")
            if "PyQt6" in p.read_text(encoding="utf-8")]
    assert hits == []
