#!/usr/bin/env python3
"""Build the thermodynamic node stores, once per model change and ahead of any exercise.

The condensing letdown (HV-322604) and the liquor heats read the Extended UNIQUAC liquid-state
grid of `ureasim.thermo.ammonia_backpressure`; 322C001's beds and the vacuum train's back
condensers read V1's back-pressure grid beside it. Tabulated lazily, a transient that walks into a
new region of either stalls the simulator (handoff A-18). This tool tabulates the whole block a
liquor up to 1000 mol/kg water reads, 10 to 100 C — 460 460 nodes a grid — on every core, and
writes each store beside the module. The engine then serves every node from the stores; the
values are bit for bit the lazy path's. Rerun it whenever a thermodynamic parameter or solver
changes: a stale store is ignored, never wrong, and only slow.

    python tools/build_liquid_state_store.py [--workers N] [--only state|back]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ureasim.thermo import ammonia_backpressure as ab  # noqa: E402
from ureasim.thermo import node_store  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workers", type=int, default=None,
                        help="processes to tabulate on (default: every core)")
    parser.add_argument("--only", choices=("state", "back"), default=None,
                        help="build one store (default: both)")
    args = parser.parse_args(argv)
    grids = {"state": (ab.STATE_STORE_PATH, ab.state_store_key, ab.build_state_store),
             "back": (ab.BACK_STORE_PATH, ab.back_store_key, ab.build_back_store)}
    for name, (path, key_fn, build) in grids.items():
        if args.only not in (None, name):
            continue
        key = key_fn()
        if node_store.read_store(path, key) is not None:
            print(f"[store] {path} is current (key {key[:16]}); nothing to do.")
            continue
        t0 = time.time()
        last = [0.0]

        def progress(done: int, total: int) -> None:
            now = time.time()
            if now - last[0] >= 10.0 or done == total:
                last[0] = now
                print(f"[store] {name}: {done}/{total} columns, {now - t0:.0f} s", flush=True)

        store = build(workers=args.workers, progress=progress)
        bad = sum(1 for v in store.values[::store.width] if v != v)
        print(f"[store] written {path}: {len(store.values) // store.width} nodes, "
              f"{bad} not computable, {time.time() - t0:.0f} s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
