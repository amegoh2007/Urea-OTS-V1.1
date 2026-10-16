"""The console packet as a whole — `ureasim.engine.packet` — against V1's WebSocket packet.

What is being proved
--------------------
* **The key paths are V1's.** V1's packet is the dictionary literal `step_sim` returns. It is read
  out of ``main.py`` statically — every key path down to each leaf, a comprehension or a ``**``
  splat standing for the dictionary at its path — and the port's packet has exactly those paths,
  less V1's five diagnostic blocks, and no path V1 does not have.
* **Two decided divergences, both ways** (the process engineer, 2026-10-03): V1's packet carries
  its five diagnostic blocks and the port's none of them (A-19 (a)); the port's carries the
  boundary sinks and V1's does not (A-15).
* **Every binding a console carries resolves.** Each dot-path the screens' overlays bind
  (`ureasim.data.screen_layout`: values, modes, cascade set points, block-valve states) reads a
  value from the packet, but the four of unit 335's faceplates, which is not ported.
* The packet is JSON, carries the plant clock, the pacing and the health block.

The values are each block's own test's (``test_<block>.py``).
"""

from __future__ import annotations

import ast
import json

import pytest

from ureasim.data import screen_layout
from ureasim.engine.packet import DIAGNOSTIC_BLOCKS, PORT_BLOCKS
from ureasim.hmi.state_access import get_path
from tests.equivalence.v1_loader import V1_BACKEND, v1_available

#: The overlay fields that hold a dot-path into the packet.
PATH_FIELDS = ("bind", "mode", "cas", "ctlBind", "xv")

def _v1_paths() -> tuple[set, set]:
    """V1's packet: its leaf paths, and the paths of the dictionaries it builds by comprehension
    or splat (whose keys are data)."""
    src = (V1_BACKEND / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    step = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "step_sim")
    ret = max((n for n in ast.walk(step) if isinstance(n, ast.Return)
               and isinstance(n.value, ast.Dict)), key=lambda r: len(r.value.keys))
    leaves, dynamic = set(), set()

    def walk(node, prefix):
        for k, v in zip(node.keys, node.values):
            if k is None:
                dynamic.add(prefix)
                continue
            path = f"{prefix}.{k.value}" if prefix else k.value
            if isinstance(v, ast.Dict):
                walk(v, path)
            elif isinstance(v, ast.DictComp):
                dynamic.add(path)
            else:
                leaves.add(path)
    walk(ret.value, "")
    return leaves, dynamic


def _port_paths(d, prefix="") -> set:
    out = set()
    for k, v in d.items():
        path = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict) and v:
            out |= _port_paths(v, path)
        else:
            out.add(path)
    return out


@pytest.mark.skipif(not v1_available(), reason="V1 source tree not present on this machine")
def test_the_key_paths_are_v1s(design):
    """Every leaf V1 publishes is at its path in the port's packet, every dictionary V1 builds by
    comprehension is a dictionary there, and the port publishes nothing V1 does not — V1's
    diagnostic blocks aside, which V1 publishes and the port, decided, does not (A-19 (a)). Dictionaries whose keys are data (species, streams, flags,
    controllers, a leaf that is itself a dictionary such as a stream's composition) are compared
    at their own path."""
    leaves, dynamic = _v1_paths()
    assert set(DIAGNOSTIC_BLOCKS) <= {p.split(".")[0] for p in leaves | dynamic}
    keep = lambda p: p.split(".")[0] not in DIAGNOSTIC_BLOCKS          # noqa: E731
    leaves, dynamic = set(filter(keep, leaves)), set(filter(keep, dynamic))
    assert not set(PORT_BLOCKS) & {p.split(".")[0] for p in leaves | dynamic}
    pkt = {k: v for k, v in design.packet.items() if k != "_health" and k not in PORT_BLOCKS}
    assert set(PORT_BLOCKS) <= set(design.packet)
    for path in leaves | dynamic:
        node = pkt
        for key in path.split("."):
            assert isinstance(node, dict) and key in node, path
            node = node[key]
    for path in dynamic:
        assert isinstance(get_path(pkt, path), dict), path
    for path in _port_paths(pkt):
        assert path in leaves or any(path.startswith(f"{d}.") for d in dynamic) or any(
            path.startswith(f"{leaf}.") for leaf in leaves), path
    assert not set(DIAGNOSTIC_BLOCKS) & set(pkt)


def test_every_binding_the_consoles_carry_resolves(design):
    """All 274 of the screens' bound paths read a value, unit 335's four UF85 faceplate fields
    since session 55 (decision 123). Six are decision 98's: the five trip 21.2 keyswitches'
    ``HAND_SWITCHES`` and AI-329701."""
    paths = {e[f] for els in screen_layout.OVERLAYS.values() for e in els for f in PATH_FIELDS
             if isinstance(e.get(f), str) and e[f]}
    unresolved = {p for p in paths if get_path(design.packet, p) is None}
    assert len(paths) == 274 and unresolved == set()


def test_the_packet_is_json_with_its_clocks_and_health(design):
    """Encodable as strict JSON; the plant clock at its tenth tick, the pacing and its speed,
    the health block as handed in."""
    json.dumps(design.packet, allow_nan=False)
    p = design.packet
    assert p["t"] == 1.0e9 and p["t_sim"] == pytest.approx(1.0, abs=1e-12)
    assert (p["sim_mode"], p["sim_speed"]) == ("SLOW", 1)
    assert p["_health"] == {"ok": True}
    assert list(p)[:3] == ["t", "t_sim", "FI_321401"]
    assert list(p)[-1] == "_health"
