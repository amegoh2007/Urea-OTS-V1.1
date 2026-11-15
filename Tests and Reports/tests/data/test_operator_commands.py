"""V1 <-> V1.1 for the operator's command data — `ureasim.data.operator_commands`.

The faceplate whitelist and the auxiliary pump list are lifted out of V1's ``main.py``; the pump
roster's seeds live in V1's ``State`` constructor, which cannot run, and are read from its source.
"""

from __future__ import annotations

import re

import pytest

from tests.equivalence.v1_loader import V1_BACKEND, lift, v1_available
from ureasim.data import operator_commands as oc

pytestmark = pytest.mark.skipif(not v1_available(), reason="V1 source tree not present")


def _v1_pumps() -> dict:
    """The roster less the pairs decision 227 adds, which V1 does not have (its 322P002 kept)."""
    added = set(oc.RUN_STATE_PAIRS) - {"322P002"}
    return {tag: seed for tag, seed in oc.AUX_PUMP_SEEDS.items() if tag[:-1] not in added}


def test_the_faceplate_whitelist_is_v1s():
    """Every faceplate and every mode V1 offers it, V1's underscore keys written as DCS tags —
    but FIC-328406, both ways: V1 offers MAN alone, the port MAN, AUTO and CAS, because decision
    B-50 made it LIC-328505's cascade slave (2026-10-03, As-Built §LIX.5); and PIC-335201, which
    V1 holds as a boundary constant and the port computes as AC4 PC35.2's loop (decision 224)."""
    ns = lift(["R323_CTRL_MODES", "AUX_PUMPS"])
    v1 = {k.replace("_", "-", 1): v for k, v in ns["R323_CTRL_MODES"].items()}
    assert v1["FIC-328406"] == ("MAN",) and "PIC-335201" not in v1
    assert oc.FACEPLATE_MODES["FIC-328406"] == ("MAN", "AUTO", "CAS")
    assert dict(oc.FACEPLATE_MODES) == dict(v1, **{"FIC-328406": ("MAN", "AUTO", "CAS"),
                                                   "PIC-335201": ("MAN", "AUTO", "CAS")})
    assert tuple(_v1_pumps()) == ns["AUX_PUMPS"]


def test_the_pump_roster_is_seeded_as_v1s():
    src = (V1_BACKEND / "main.py").read_text(encoding="utf-8")
    block = src[src.index("self.aux_pumps = {"):]
    block = block[:block.index("}}") + 2]
    seeds = {m[0]: (m[1] == "True", m[2])
             for m in re.findall(r'"(\w+)": \{"on": (True|False),\s*"mode": "(\w+)"\}', block)}
    assert seeds == _v1_pumps()
