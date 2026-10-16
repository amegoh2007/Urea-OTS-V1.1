"""The process historian — every numeric leaf of the plant's tick, sampled on plant time.

What this is for
----------------
A trend pen opened halfway through an exercise must show the past, not start blank. The historian
records every numeric and boolean leaf of the console packet from the moment the engine starts, so
any trend can be backfilled, and an instructor can scroll back over what a trainee did.

Design (V1's, kept)
-------------------
* **Columnar, with a shared time index.** Every path is sampled on the same tick, so the two
  timestamp arrays are held once for the whole ring rather than once per path.
* **Plant-time cadence.** Sampling is driven by the plant clock, not the wall clock, so a 1-hour
  trend covers one hour of plant behaviour at 1x (SLOW) or 60x (FAST).
* **Fixed-capacity circular buffers over ``array('f')``.** A deque of Python floats costs about
  8x the memory for the same data.
* **Two rings**: 1 s x 3600 (the 1 min to 1 h spans at full resolution) and 10 s x 2880 (2 h to
  8 h). About 26 kB a path across both.
* **Min/max decimation** on read, so a spike between two output points still appears.

What V1.1 records
-----------------
V1 logged its WebSocket packet, and so does V1.1: the console packet (`ureasim.engine.packet`),
on V1's key paths, so a trend pen asks for the path its overlay binds
(``RECIRC_323.C003.TIC_323007.pv``) and gets its history. `flatten` also walks a tick's result
objects — mappings and dataclasses by field, tuples by index, booleans as 0 / 1 — for the tests
that compare two runs tick by tick. A composition vector (a mapping keyed by species) is a stream
table, not an instrument, and is left out as V1 left out ``STREAMS``: 704 of the packet's 788
numeric leaves remain; no console binds one of the 84.

Threading: the engine samples after each tick and answers queries between ticks, on the engine
host's physics thread (`ureasim.net.engine_host`), so no lock is needed (V1's arrangement, on one
thread).

Source: V1 ``backend/historian.py`` (ported verbatim but for `flatten`'s object walk and the
composition rule); its design note ``docs/superpowers/specs/2026-08-07-trend-system-design.md``.
"""

from __future__ import annotations

import dataclasses
from array import array
from collections.abc import Mapping
from math import isnan

from ureasim.thermo.domains import MW

__all__ = ["NAN", "PATH_EXCLUDE", "RINGS", "flatten", "Ring", "Historian"]

NAN = float("nan")

#: Top-level keys never logged. V1 left out its packet's ``STREAMS``; V1.1's results have no such
#: key, so the rule is kept for a published packet that carries one.
PATH_EXCLUDE = ("STREAMS",)

#: ring name -> (sample period in PLANT seconds, capacity in samples). Source: V1 ``RINGS``.
RINGS = (("fast", 1.0, 3600), ("slow", 10.0, 2880))

#: The species a composition vector is keyed by, formaldehyde (unit 335's) included.
_SPECIES = frozenset(MW)


def _is_composition(obj: Mapping) -> bool:
    """True for a non-empty mapping keyed only by species: a stream table, not an instrument."""
    return bool(obj) and all(isinstance(k, str) and k in _SPECIES for k in obj)


def flatten(pkt, prefix: str = "", out: dict | None = None) -> dict:
    """Flatten a tick's results (or a packet) to {dot.path: float}. Booleans become 0.0 / 1.0.

    Process utility
    ---------------
    Every instrument and computed value the plant produced this tick, under the name a trend pen
    asks for. Excluded top-level subtrees and composition vectors are skipped whole.
    """
    if out is None:
        out = {}
    if isinstance(pkt, Mapping):
        if prefix and _is_composition(pkt):
            return out
        for k, v in pkt.items():
            path = f"{prefix}.{k}" if prefix else str(k)
            if not prefix and k in PATH_EXCLUDE:
                continue
            flatten(v, path, out)
    elif isinstance(pkt, bool):
        out[prefix] = 1.0 if pkt else 0.0
    elif isinstance(pkt, (int, float)):
        out[prefix] = float(pkt)
    elif dataclasses.is_dataclass(pkt) and not isinstance(pkt, type):
        for f in dataclasses.fields(pkt):
            flatten(getattr(pkt, f.name), f"{prefix}.{f.name}" if prefix else f.name, out)
    elif isinstance(pkt, (tuple, list)):
        for i, v in enumerate(pkt):
            flatten(v, f"{prefix}.{i}" if prefix else str(i), out)
    return out


class Ring:
    """One fixed-capacity circular buffer sampled every ``period`` plant-seconds."""

    def __init__(self, name: str, period: float, capacity: int) -> None:
        self.name = name
        self.period = float(period)
        self.cap = int(capacity)
        self.t_sim = array("d", bytes(8 * self.cap))
        self.t_wall = array("d", bytes(8 * self.cap))
        self.cols: dict = {}        # path -> array('f') of length cap
        self.cursor = 0             # next slot to write
        self.count = 0              # samples written, saturating at cap
        self.next_due = None        # plant time of the next sample

    # ---- write side ----

    def _column(self, path: str) -> array:
        col = self.cols.get(path)
        if col is None:
            # A path that appears mid-run is NaN-padded, so its history reads "no data" for the
            # period before it existed rather than a misleading zero.
            col = array("f", [NAN]) * self.cap
            self.cols[path] = col
        return col

    def due(self, t_sim: float) -> bool:
        return self.next_due is None or t_sim >= self.next_due

    def write(self, flat: dict, t_sim: float, t_wall: float) -> None:
        i = self.cursor
        self.t_sim[i] = t_sim
        self.t_wall[i] = t_wall
        for path, val in flat.items():
            self._column(path)[i] = val
        # Paths absent from this sample keep whatever the slot held one lap ago, a stale value
        # from about an hour back. Blank them instead.
        if len(self.cols) != len(flat):
            for path, col in self.cols.items():
                if path not in flat:
                    col[i] = NAN
        self.cursor = (i + 1) % self.cap
        self.count = min(self.count + 1, self.cap)
        self.next_due = t_sim + self.period

    # ---- read side ----

    def order(self):
        """Slot indices oldest to newest."""
        if self.count < self.cap:
            return range(0, self.count)
        return [(self.cursor + n) % self.cap for n in range(self.cap)]

    def span_covered(self) -> float:
        """Plant seconds between the oldest and newest retained sample."""
        idx = self.order()
        if len(idx) < 2:
            return 0.0
        first = idx[0] if isinstance(idx, list) else 0
        last = idx[-1] if isinstance(idx, list) else self.count - 1
        return self.t_sim[last] - self.t_sim[first]

    def window(self, span_s: float, end_sim: float) -> list:
        """Slot indices in ``(end_sim - span_s, end_sim]``, oldest first — bounded at both ends,
        so a scrolled-back trend gets the window it asked for."""
        cutoff = end_sim - span_s
        return [i for i in self.order()
                if self.t_sim[i] >= cutoff and self.t_sim[i] <= end_sim]


class Historian:
    """The rings, written after each tick and read by the trend window."""

    def __init__(self, rings=RINGS) -> None:
        self.rings = [Ring(*r) for r in rings]

    # ---- write side ----

    def maybe_sample(self, pkt, t_sim: float, t_wall: float) -> bool:
        """Sample every ring that is due. Called once per physics step.

        ``pkt`` is the packet, or a function that builds it: the session hands the console packet
        over lazily, so it is built — and flattened — at most once per call and only when some
        ring is due, and a tick off a sample boundary costs two float comparisons.
        """
        due = [r for r in self.rings if r.due(t_sim)]
        if not due:
            return False
        flat = flatten(pkt() if callable(pkt) else pkt)
        for ring in due:
            ring.write(flat, t_sim, t_wall)
        return True

    # ---- read side ----

    def pick_ring(self, span_s: float) -> Ring:
        """Finest ring whose retention covers ``span_s``; coarsest as fallback."""
        for ring in self.rings:
            if ring.period * ring.cap >= span_s:
                return ring
        return self.rings[-1]

    def query(self, paths, span_s: float, max_points: int = 800, end_sim=None) -> dict:
        """``span_s`` plant-seconds of history for ``paths``, ending at ``end_sim`` (default: the
        newest sample).

        A window read from far back picks its ring by how far back it sits as well as by its span.
        Decimation keeps a min/max envelope on bucket boundaries every path shares: each bucket
        emits two points, at its first and last timestamps, carrying its two extremes in the
        order they occurred.
        """
        newest = self._newest()
        end = newest if end_sim is None else float(end_sim)
        age = 0.0 if newest is None else max(0.0, newest - end)
        ring = self.pick_ring(span_s + age)
        idx = ring.window(span_s, end) if newest is not None else []

        known = [p for p in paths if p in ring.cols]
        missing = [p for p in paths if p not in ring.cols]
        out = {
            "ring": ring.name,
            "period": ring.period,
            "span": span_s,
            "t_sim": [],
            "t_wall": [],
            "series": {p: [] for p in known},
            "missing": missing,
            "truncated": bool(idx) and ring.span_covered() < span_s * 0.999,
        }
        if not idx:
            return out

        buckets = self._buckets(idx, max_points)
        for chunk in buckets:
            out["t_sim"].append(ring.t_sim[chunk[0]])
            out["t_sim"].append(ring.t_sim[chunk[-1]])
            out["t_wall"].append(ring.t_wall[chunk[0]])
            out["t_wall"].append(ring.t_wall[chunk[-1]])
            for path in known:
                col = ring.cols[path]
                lo = hi = None
                lo_at = hi_at = 0
                for pos, i in enumerate(chunk):
                    v = col[i]
                    if isnan(v):
                        continue
                    if lo is None or v < lo:
                        lo, lo_at = v, pos
                    if hi is None or v > hi:
                        hi, hi_at = v, pos
                if lo is None:
                    out["series"][path].extend((None, None))
                elif lo_at <= hi_at:
                    out["series"][path].extend((lo, hi))
                else:
                    out["series"][path].extend((hi, lo))
        return out

    def paths(self) -> dict:
        """Every logged path, with the ring that holds it."""
        seen: dict = {}
        for ring in self.rings:
            for p in ring.cols:
                seen.setdefault(p, ring.name)
        return seen

    def stats(self) -> dict:
        return {
            r.name: {
                "period": r.period,
                "capacity": r.cap,
                "samples": r.count,
                "paths": len(r.cols),
                "bytes": 4 * r.cap * len(r.cols) + 16 * r.cap,
            }
            for r in self.rings
        }

    # ---- internals ----

    @staticmethod
    def _now_sim(ring: Ring):
        if ring.count == 0:
            return None
        newest = (ring.cursor - 1) % ring.cap
        return ring.t_sim[newest]

    def _newest(self):
        """Newest plant timestamp across all rings."""
        stamps = [t for t in (self._now_sim(r) for r in self.rings) if t is not None]
        return max(stamps) if stamps else None

    @staticmethod
    def _buckets(idx, max_points: int) -> list:
        """Split ``idx`` into at most ``max_points // 2`` contiguous chunks."""
        n_buckets = max(1, max_points // 2)
        if len(idx) <= n_buckets:
            return [[i] for i in idx]
        size = len(idx) / n_buckets
        chunks = []
        for b in range(n_buckets):
            lo = int(b * size)
            hi = int((b + 1) * size) if b < n_buckets - 1 else len(idx)
            if hi > lo:
                chunks.append(idx[lo:hi])
        return chunks
