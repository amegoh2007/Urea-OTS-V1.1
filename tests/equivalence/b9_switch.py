"""Handoff B-9's switch on the V1 side of the stripper equivalences.

What this is
------------
Decided 2026-10-07 (handoff B-9, closed; As-Built §LXI.2): 322E001's two flood rises share one
ceiling, the 11 C gap to the reactor liquor,

    dT_bot = max(dT_bot, dT_flood)

where V1 adds them (``dT_bot = dT_bot + dT_flood``), so a flooded stripper's bottoms tend to the
183 C liquor fed rather than to 194 C. The port runs the decided line
(`units.synthesis.stripper.stripper_322e001`).

To keep proving the rest of the stripper, and every harness that runs it, against V1's own bytes,
`switch` recompiles V1's ``stripper_322e001`` — lifted out of ``main.py`` by `v1_loader.lift` —
with that one statement replaced, into the namespace it was lifted into: every other line it runs
is V1's, character for character. The replacement is made on the parsed function, and the switch
fails unless it finds exactly one such statement, so a V1 edit cannot silently void it. A namespace
lifted without `switch` is V1 verbatim, for the tests that run the departure both ways.
"""

from __future__ import annotations

import ast

from tests.equivalence.v1_loader import V1_BACKEND

#: The V1 function the switch recompiles.
FUNCTION = "stripper_322e001"


class _MaxInsteadOfSum(ast.NodeTransformer):
    """``dT_bot = dT_bot + dT_flood``  ->  ``dT_bot = max(dT_bot, dT_flood)``."""

    def __init__(self):
        self.replaced = 0

    def visit_Assign(self, node: ast.Assign):
        value = node.value
        if (len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "dT_bot" and isinstance(value, ast.BinOp)
                and isinstance(value.op, ast.Add)
                and isinstance(value.left, ast.Name) and value.left.id == "dT_bot"
                and isinstance(value.right, ast.Name) and value.right.id == "dT_flood"):
            self.replaced += 1
            call = ast.Call(func=ast.Name("max", ast.Load()),
                            args=[ast.Name("dT_bot", ast.Load()),
                                  ast.Name("dT_flood", ast.Load())], keywords=[])
            return ast.copy_location(ast.Assign(targets=node.targets, value=call), node)
        return node


def switch(ns: dict) -> dict:
    """Replace ``ns[FUNCTION]`` — V1's stripper, lifted into `ns` — with B-9's switched copy."""
    tree = ast.parse((V1_BACKEND / "main.py").read_text(encoding="utf-8", errors="replace"))
    fn = next(s for s in tree.body if isinstance(s, ast.FunctionDef) and s.name == FUNCTION)
    swap = _MaxInsteadOfSum()
    fn = ast.fix_missing_locations(swap.visit(fn))
    if swap.replaced != 1:
        raise AssertionError(f"B-9's statement found {swap.replaced} times in V1's {FUNCTION}")
    exec(compile(ast.Module([fn], []), "<v1 main.py, B-9 switched>", "exec"), ns)
    return ns


__all__ = ["FUNCTION", "switch"]
