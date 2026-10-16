"""The dense node store a lazily tabulated grid is served from — `ureasim.thermo.node_store`.

The store must change how fast a grid answers and never what it answers: these tests pin the
round trip to the bit, the refusal of a stale, damaged or foreign file, and the builder's handling
of a node that cannot be computed.
"""

from __future__ import annotations

import math

import pytest

from ureasim.thermo import node_store


def _node(i: int, j: int, k: int) -> tuple:
    """A stand-in node function: irrational values, so a lost bit shows."""
    if (i, j, k) == (1, 2, 5):
        raise ValueError("no solution at this node")
    return (math.sqrt(2.0) * i + math.pi * j, math.exp(-k / 7.0), math.log(1.0 + i + j + k))


def test_a_store_round_trips_to_the_bit(tmp_path):
    store = node_store.build_store(_node, (0, 2), (1, 3), (4, 6), 3, workers=1)
    path = str(tmp_path / "s.bin")
    node_store.write_store(path, store, "k1")
    back = node_store.read_store(path, "k1")
    assert back.shape == (3, 3, 3)
    for i in range(0, 3):
        for j in range(1, 4):
            for k in range(4, 7):
                if (i, j, k) != (1, 2, 5):
                    assert back.get(i, j, k) == _node(i, j, k)


def test_a_node_that_cannot_be_computed_is_stored_as_nan():
    """Left to the lazy path, which raises as it always did."""
    store = node_store.build_store(_node, (1, 1), (2, 2), (4, 6), 3, workers=1)
    assert all(v != v for v in store.get(1, 2, 5))
    assert store.get(1, 2, 4) == _node(1, 2, 4)


def test_outside_the_block_there_is_no_node():
    store = node_store.build_store(_node, (0, 0), (1, 1), (4, 4), 3, workers=1)
    assert store.get(1, 1, 4) is None and store.get(0, 1, 5) is None


@pytest.mark.parametrize("damage", ["key", "truncated", "trailing", "magic", "missing"])
def test_a_stale_or_damaged_store_is_not_read(tmp_path, damage):
    store = node_store.build_store(_node, (0, 1), (1, 2), (4, 4), 3, workers=1)
    path = tmp_path / "s.bin"
    node_store.write_store(str(path), store, "k1")
    raw = path.read_bytes()
    key = "k1"
    if damage == "key":
        key = "k2"
    elif damage == "truncated":
        path.write_bytes(raw[:-8])
    elif damage == "trailing":
        path.write_bytes(raw + b"\x00")
    elif damage == "magic":
        path.write_bytes(b"X" + raw[1:])
    else:
        path.unlink()
    assert node_store.read_store(str(path), key) is None


def test_a_store_that_does_not_fill_its_block_is_refused(tmp_path):
    from array import array
    bad = node_store.NodeStore(0, 1, 0, 0, 0, 0, 3, array("d", [1.0] * 5))
    with pytest.raises(ValueError):
        node_store.write_store(str(tmp_path / "s.bin"), bad, "k")
