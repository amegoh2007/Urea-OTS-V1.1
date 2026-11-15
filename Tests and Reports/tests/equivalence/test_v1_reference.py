"""V1's reference sources in this tree — `tests/equivalence/v1_reference` (decision 210).

Why this exists
---------------
Every equivalence test drives V1's own bytes beside the port (`Claude.md` §5.4). Until decision 210
they were read from a V1 tree outside the repository, and a machine without it skipped 5 862 of
8 016 tests silently (handoff A-33). The files the suite reads are now copied here byte for byte.

Pinned: the copy is present and every file matches its manifest's SHA-256, so the evidence is
V1's exact bytes (V1's boot-pin and VLE-grid caches key on them too); the copy holds nothing the
manifest does not list, and none of V1's own tests, debug scripts or backups; the loader finds it;
every module V1's `main.py` imports, at any depth and inside functions too, is in the copy or is an
installed package, so the Phase 7 driver's whole import of V1 (`tests.phase7.drivers.run_v1`, in a
process of its own) resolves; and no executable string under `ureasim/`, `tests/` or `tools/` points
back at the external V1 tree. These fail rather than skip: a missing reference is a broken checkout,
not an optional extra.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
from pathlib import Path

from tests.equivalence.v1_loader import V1_BACKEND, V1_ROOT, v1_available

REPO = Path(__file__).resolve().parents[3]
MANIFEST = V1_ROOT / "MANIFEST.sha256"
#: The external tree's folder name, lower case, built in two parts so this file is not a hit.
EXTERNAL = "urea simulation" + " v1"


def _manifest() -> dict[str, str]:
    rows = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            digest, rel = line.split("  ", 1)
            rows[rel] = digest
    return rows


def test_the_reference_is_present_and_byte_exact():
    assert v1_available() and V1_BACKEND == V1_ROOT / "backend"
    rows = _manifest()
    assert len(rows) == 38
    for rel, digest in rows.items():
        assert hashlib.sha256((V1_ROOT / rel).read_bytes()).hexdigest() == digest, rel


def test_the_reference_holds_only_its_manifest():
    present = {p.relative_to(V1_ROOT).as_posix() for p in V1_ROOT.rglob("*")
               if p.is_file() and "__pycache__" not in p.parts and p != MANIFEST}
    assert present == set(_manifest())
    for rel in present:
        name = rel.rsplit("/", 1)[-1]
        assert not name.startswith(("test_", "debug_")), rel
        assert not any(tag in name for tag in ("backup", "_orig", ".bak")), rel


def _imported_modules(path: Path) -> set[str]:
    """The module names a V1 file imports, except those a ``try`` guards against their absence."""
    tree = ast.parse(path.read_bytes())
    handled = ("ImportError", "ModuleNotFoundError", "Exception")
    optional = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Try) and any(
                h.type is None or getattr(h.type, "id", "") in handled for h in node.handlers):
            optional.update(id(n) for stmt in node.body for n in ast.walk(stmt))
    names = set()
    for node in ast.walk(tree):
        if id(node) in optional:
            continue
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module)
    return names


def test_v1s_main_imports_resolve_inside_the_copy():
    # V1's main.py puts V1's root, the copy's folder, on sys.path beside its own backend/.
    bases = (V1_BACKEND, V1_ROOT)
    seen, todo, unresolved = set(), [V1_BACKEND / "main.py"], set()
    while todo:
        path = todo.pop()
        if path in seen:
            continue
        seen.add(path)
        for name in _imported_modules(path):
            parts = name.split(".")
            found = [c for b in bases for c in (b.joinpath(*parts).with_suffix(".py"),
                                                b.joinpath(*parts) / "__init__.py") if c.is_file()]
            if found:
                todo.extend(found)
            elif not any(b.joinpath(parts[0]).is_dir() for b in bases):
                try:
                    if importlib.util.find_spec(name) is None:
                        unresolved.add(name)
                except ModuleNotFoundError:
                    unresolved.add(name)
    assert unresolved == set()
    assert {p.relative_to(V1_ROOT).as_posix() for p in seen} <= set(_manifest())


def _code_strings(path: Path):
    """Every string constant in a module that is not a docstring."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                docs.add(id(body[0].value))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in docs):
            yield node.value


def test_nothing_points_back_at_the_external_v1_tree():
    hits = []
    for top in ("ureasim", "Tests and Reports/tests", "tools"):
        assert (REPO / top).is_dir(), top
        for path in sorted((REPO / top).rglob("*.py")):
            if V1_ROOT in path.parents:
                continue
            for s in _code_strings(path):
                if EXTERNAL in s.lower():
                    hits.append(path.relative_to(REPO).as_posix())
    assert hits == []
