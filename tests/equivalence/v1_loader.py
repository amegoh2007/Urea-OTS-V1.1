"""Load V1 modules side by side with V1.1, without a name collision.

Why this exists
---------------
`Claude.md` §5.4 requires every ported relation to be proven equal to its V1 counterpart.
That means both implementations must be importable *in the same interpreter*, and they
share module names: V1 has top-level `reactor`, `controllers`, `hydraulics`,
`thermo_service`, `iapws_if97`; V1.1 has `ureasim.units.synthesis.reactor`,
`ureasim.control.controller`, and so on. A plain `import reactor` would be ambiguous and,
worse, would let a V1 module accidentally satisfy a V1.1 import.

So V1 modules are loaded **by explicit file path** into a private namespace prefixed
`v1_`, never by a plain import statement.

V1 internal imports
-------------------
V1's own modules import each other by bare name (`import props_nh3co2h2o as _props`).
For those to resolve, `E:\\Simulator\\Urea Simulation\\backend` must be on `sys.path` while a V1
module executes. `load()` adds it, and registers the loaded module under **both** its bare
V1 name and its `v1_`-prefixed alias, so a later V1 module finds the same object rather
than re-executing it.

The bare-name registration is the price of V1's import style. It is confined to modules
this loader has been explicitly asked for, and V1.1 never imports by bare name, so the two
cannot be confused.

Usage
-----
    from tests.equivalence.v1_loader import load, v1_available

    v1_iapws = load("iapws_if97")
    assert v1_iapws.tsat_c(4.4) == pytest.approx(...)

If the V1 tree is absent (a machine that only has the rewrite), `v1_available()` returns
False and the equivalence tests skip rather than fail — the rewrite must remain testable
on its own.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

#: Root of the V1 project. Reference only — nothing here ever writes to it.
V1_ROOT = Path(r"E:\Simulator\Urea Simulation")

#: V1's Python package directory. V1 modules import each other by bare name from here.
V1_BACKEND = V1_ROOT / "backend"

#: Cache of already-loaded V1 modules, keyed by bare module name.
_LOADED: dict[str, ModuleType] = {}


def v1_available() -> bool:
    """True when the V1 source tree is present and importable on this machine."""
    return V1_BACKEND.is_dir() and (V1_BACKEND / "iapws_if97.py").is_file()


def _ensure_path() -> None:
    """Put V1's backend directory on `sys.path` so its bare-name imports resolve."""
    p = str(V1_BACKEND)
    if p not in sys.path:
        # Appended, not prepended: V1.1's own packages must win any name contest.
        sys.path.append(p)


def load(module_name: str) -> ModuleType:
    """Load a V1 module by bare name and return it.

    Parameters
    ----------
    module_name
        The V1 module's bare name without ``.py`` — for example ``"iapws_if97"`` or
        ``"props_nh3co2h2o"``. Sub-package modules use a slash-free dotted form
        (``"core.thermo"``), which is resolved to ``backend/core/thermo.py``.

    Raises
    ------
    FileNotFoundError
        If the V1 tree, or that module inside it, is absent. Callers guard with
        `v1_available()` and skip.
    """
    if module_name in _LOADED:
        return _LOADED[module_name]

    if not v1_available():
        raise FileNotFoundError(f"V1 source tree not found at {V1_BACKEND}")

    rel = Path(*module_name.split(".")).with_suffix(".py")
    path = V1_BACKEND / rel
    if not path.is_file():
        raise FileNotFoundError(f"V1 module not found: {path}")

    _ensure_path()

    alias = "v1_" + module_name.replace(".", "_")
    spec = importlib.util.spec_from_file_location(alias, path)
    if spec is None or spec.loader is None:            # pragma: no cover - defensive
        raise ImportError(f"cannot build import spec for {path}")
    module = importlib.util.module_from_spec(spec)

    # Register under the alias AND the bare V1 name before executing, so that a V1 module
    # importing itself transitively (or a circular V1 import) resolves to this object
    # rather than re-executing the file.
    sys.modules[alias] = module
    sys.modules.setdefault(module_name, module)
    spec.loader.exec_module(module)

    _LOADED[module_name] = module
    return module


def lift(names, module_name: str = "main", seed: dict = None) -> dict:
    """Execute just enough of a V1 module to make ``names`` callable, and return that namespace.

    Why lifting is needed at all
    ----------------------------
    V1's `main.py` cannot be imported: at import time it builds a FastAPI application, a full
    plant state and a historian thread. But most of the physics worth proving lives in
    module-level functions and constants in that same file. So the statements that define the
    wanted names — and, transitively, everything THOSE names need — are compiled and executed
    on their own, in source order, into a private namespace.

    What this is and is not
    -----------------------
    It IS execution of V1's own bytes: the functions that come back are V1's, character for
    character, not a transcription. That is the strong evidence standard `Claude.md` §5.4
    asks for.

    It is NOT a way to run `step_sim`. Only module-level `Assign`, `AnnAssign` and
    `FunctionDef` statements are candidates, so anything written inside a function body, an
    `if` or a `try` is invisible here and must be transcribed instead, and declared as such
    (handoff A-12).

    A tuple assignment binds all of its names, and asking for any one of them executes the
    whole statement — which is the only correct answer, since the statement cannot be split.

    Parameters
    ----------
    names
        The V1 names to make available.
    module_name
        Which V1 module to lift out of. Defaults to `main`, the one that cannot be imported.
    seed
        Objects the lifted statements need that are not themselves liftable — V1 modules that
        DO import cleanly, and the standard library. Anything in `seed` is never overwritten
        by a lifted statement, so a caller cannot accidentally shadow a real module with a
        same-named constant.

    Raises
    ------
    KeyError
        If a requested name has no module-level definition. Failing loudly matters: silently
        returning a namespace short of one constant would make an equivalence test compare
        the rewrite against a partially-initialised V1.
    """
    if not v1_available():
        raise FileNotFoundError(f"V1 source tree not found at {V1_BACKEND}")
    path = V1_BACKEND / Path(*module_name.split(".")).with_suffix(".py")
    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))

    # Index every top-level definition by the name it binds.
    defines: dict[str, int] = {}
    for i, stmt in enumerate(tree.body):
        if isinstance(stmt, ast.FunctionDef):
            defines.setdefault(stmt.name, i)
        elif isinstance(stmt, ast.Assign):
            # Every Name bound by this statement, which includes tuple unpacking: V1 writes
            # `EJ_CP_N, EJ_CP_C, EJ_CP_D = 4.74, 3.10, 3.50` and all three have to be
            # findable. Walking the target covers nested and starred forms too.
            for target in stmt.targets:
                for node in ast.walk(target):
                    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                        defines.setdefault(node.id, i)
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            defines.setdefault(stmt.target.id, i)

    seed = dict(seed or {})
    wanted = list(names)
    missing = [n for n in wanted if n not in defines]
    if missing:
        raise KeyError(f"no module-level definition in V1 {module_name}.py for {missing}")

    # Transitive closure: pull in every statement whose name a selected statement reads.
    chosen: set[int] = set()
    queue = [defines[n] for n in wanted]
    while queue:
        i = queue.pop()
        if i in chosen:
            continue
        chosen.add(i)
        for node in ast.walk(tree.body[i]):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                j = defines.get(node.id)
                if j is not None and j not in chosen and node.id not in seed:
                    queue.append(j)

    ns: dict = dict(seed)
    for i in sorted(chosen):
        exec(compile(ast.Module([tree.body[i]], []), f"<v1 {module_name}.py>", "exec"), ns)
    return ns


#: The flash budget the port runs [sweeps] — handoff A-9, decided 2026-09-30. V1's default is 40.
DECIDED_FLASH_ITERS = 60

#: The budget V1's flash memo was last filled on. V1's memo keys ignore the budget, so a bin
#: solved on one budget must not be served to a caller on the other.
_MEMO_BUDGET: list = [None]


class FlashBudget:
    """V1's `thermo_service`, its `flash` run on a stated budget; everything else V1's own.

    Why: the port's service runs 60 successive-substitution sweeps where V1 runs 40 (A-9), and
    the 323 stages' rigorous vapour departure takes a different branch wherever the two part.
    A transcription seeded with ``FlashBudget(load("thermo_service"), 60)`` executes V1's own
    flash on the port's budget; one seeded on 40 is V1 verbatim. V1's memo is cleared whenever
    the budget changes, since its keys do not carry it.
    """

    def __init__(self, module: ModuleType, outer_iters: int):
        self._module = module
        self._outer_iters = outer_iters

    def __getattr__(self, name):
        return getattr(self._module, name)

    def flash(self, *args, **kwargs):
        kwargs.setdefault("outer_iters", self._outer_iters)
        if _MEMO_BUDGET[0] != kwargs["outer_iters"]:
            self._module.flash_cache_clear()
            _MEMO_BUDGET[0] = kwargs["outer_iters"]
        return self._module.flash(*args, **kwargs)


def v1_service(outer_iters: int = DECIDED_FLASH_ITERS) -> FlashBudget:
    """V1's `thermo_service` on the port's flash budget (default) or on another."""
    return FlashBudget(load("thermo_service"), outer_iters)


__all__ = ["V1_ROOT", "V1_BACKEND", "v1_available", "load", "lift", "DECIDED_FLASH_ITERS",
           "FlashBudget", "v1_service"]
