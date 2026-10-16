"""A dense, pre-tabulated block of a lazily tabulated property grid, kept on disk.

What this is for
----------------
Several property grids here are tabulated lazily, one node at a time, on first use (the
back-pressure and liquid-state grids of `thermo.ammonia_backpressure`). A node costs a full
speciation, about 20 ms. A steady plant asks for a handful of nodes and never notices; a
transient that walks a property search into a region no earlier run has visited asks for
hundreds in one tick and stalls the simulator for seconds — HV-322604's condensing letdown on a
lost motive did, up to 26 s a tick (handoff A-18).

A node store is the same nodes computed ahead of time over the whole block a search can reach,
and kept on disk: the grid reads a stored node instead of computing it, so no tick ever
tabulates. The stored values are the doubles the lazy path computes, written and read back
bit for bit, so a store changes how fast an answer comes and never what it is.

The file
--------
One header line, ``UREASIM-NODES 1 <json>``, then the values as little-endian IEEE doubles,
node by node in (i, j, k) order, ``width`` values to a node. The JSON names the block's
extents, the width and a key: the SHA-256 of everything the stored values depend on. A store
whose key differs from the caller's is stale and is not read; the caller tabulates lazily, as
if there were no store, until it is rebuilt.

Source: the rewrite's (handoff A-18, session 40); the key follows `thermo.vle_grid`'s cache.
"""

from __future__ import annotations

import json
import os
import sys
from array import array
from dataclasses import dataclass

__all__ = ["MAGIC", "NodeStore", "read_store", "write_store", "build_store"]

#: The header's first word and the format's version.
MAGIC = "UREASIM-NODES 1"


@dataclass(frozen=True)
class NodeStore:
    """A dense block of grid nodes: i in [i_lo, i_hi], j in [j_lo, j_hi], k in [k_lo, k_hi],
    ``width`` values to a node."""

    i_lo: int
    i_hi: int
    j_lo: int
    j_hi: int
    k_lo: int
    k_hi: int
    width: int
    values: array

    @property
    def shape(self) -> tuple[int, int, int]:
        """The node counts along i, j and k."""
        return (self.i_hi - self.i_lo + 1, self.j_hi - self.j_lo + 1, self.k_hi - self.k_lo + 1)

    def get(self, i: int, j: int, k: int) -> tuple | None:
        """The node's values, or None outside the block.

        Process utility
        ---------------
        The grid's lookup ahead of tabulation: a stored node is served, an unstored one is
        computed as before.
        """
        if not (self.i_lo <= i <= self.i_hi and self.j_lo <= j <= self.j_hi
                and self.k_lo <= k <= self.k_hi):
            return None
        _, nj, nk = self.shape
        at = (((i - self.i_lo) * nj + (j - self.j_lo)) * nk + (k - self.k_lo)) * self.width
        return tuple(self.values[at:at + self.width])


def _header(store: NodeStore, key: str) -> bytes:
    meta = {"key": key, "width": store.width,
            "i": [store.i_lo, store.i_hi], "j": [store.j_lo, store.j_hi],
            "k": [store.k_lo, store.k_hi]}
    return f"{MAGIC} {json.dumps(meta, sort_keys=True)}\n".encode("ascii")


def write_store(path: str, store: NodeStore, key: str) -> None:
    """Write ``store`` to ``path`` under ``key``, atomically (a temporary file renamed into place),
    so a reader never sees half a store."""
    ni, nj, nk = store.shape
    if len(store.values) != ni * nj * nk * store.width:
        raise ValueError("the values do not fill the block")
    data = array("d", store.values)
    if sys.byteorder != "little":
        data.byteswap()
    tmp = f"{path}.tmp{os.getpid()}"
    with open(tmp, "wb") as f:
        f.write(_header(store, key))
        data.tofile(f)
    os.replace(tmp, path)


def read_store(path: str, key: str) -> NodeStore | None:
    """The store at ``path`` if it exists, is whole and was written under ``key``; else None."""
    try:
        with open(path, "rb") as f:
            line = f.readline().decode("ascii")
            if not line.startswith(MAGIC + " "):
                return None
            meta = json.loads(line[len(MAGIC) + 1:])
            if meta.get("key") != key:
                return None
            (i_lo, i_hi), (j_lo, j_hi), (k_lo, k_hi) = meta["i"], meta["j"], meta["k"]
            width = int(meta["width"])
            count = (i_hi - i_lo + 1) * (j_hi - j_lo + 1) * (k_hi - k_lo + 1) * width
            values = array("d")
            values.fromfile(f, count)
            if f.read(1):
                return None
    except (OSError, ValueError, KeyError, EOFError, UnicodeDecodeError):
        return None
    if sys.byteorder != "little":
        values.byteswap()
    return NodeStore(i_lo, i_hi, j_lo, j_hi, k_lo, k_hi, width, values)


def _column(task: tuple) -> list:
    """One (i, j) column of a block, k from k_lo to k_hi: the node function's values, NaN where
    the node cannot be computed (it is then left to the lazy path, which raises as before)."""
    fn, i, j, k_lo, k_hi, width = task
    out = []
    for k in range(k_lo, k_hi + 1):
        try:
            vals = fn(i, j, k)
        except (ValueError, ArithmeticError):
            vals = (float("nan"),) * width
        out.extend(vals)
    return out


def build_store(fn, i_range: tuple, j_range: tuple, k_range: tuple, width: int,
                workers: int | None = None, progress=None) -> NodeStore:
    """Tabulate ``fn(i, j, k)`` (a module-level function returning ``width`` floats) over the
    block, on ``workers`` processes (all the machine's cores by default; 1 runs in this process).

    Process utility
    ---------------
    Done once per model change, ahead of any exercise, so the simulator never tabulates during
    one. ``progress(done, total)`` is called as columns complete.
    """
    (i_lo, i_hi), (j_lo, j_hi), (k_lo, k_hi) = i_range, j_range, k_range
    tasks = [(fn, i, j, k_lo, k_hi, width) for i in range(i_lo, i_hi + 1)
             for j in range(j_lo, j_hi + 1)]
    values = array("d")
    workers = workers or os.cpu_count() or 1
    if workers == 1:
        results = map(_column, tasks)
        pool = None
    else:
        import multiprocessing
        pool = multiprocessing.Pool(workers)
        results = pool.imap(_column, tasks, chunksize=4)
    try:
        for n, col in enumerate(results, 1):
            values.extend(col)
            if progress is not None:
                progress(n, len(tasks))
    finally:
        if pool is not None:
            pool.close()
            pool.join()
    return NodeStore(i_lo, i_hi, j_lo, j_hi, k_lo, k_hi, width, values)
