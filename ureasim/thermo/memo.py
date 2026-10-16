"""Quantised memoisation for the flash and the bubble point — and the bug it had to fix.

Why memoise at all
------------------
A converged flash costs about 17 ms: the gamma-phi outer loop runs ~20 sweeps and each
sweep walks the electrolyte table and an SRK cubic. A bubble temperature is 60 bisection
steps of a full gamma-phi bubble pressure, about 8 ms. The engine integrates at
dt = 0.1 s and up to 60x real time, so re-solving three flashes every tick is roughly 500x
over budget.

It is also pointless. A flash is a **state function** of (T, P, z), and those inputs move
on stage residence times of 150-600 s, not on a 0.1 s tick. So the result is memoised
against **quantised** inputs and the solve repeats only once the state has actually moved
by more than a quantum.

The quanta are far below instrument resolution in absolute terms — but not in effect for a
trace volatile: 1e-4 mass fraction is 1.5 % of 323F004's 0.665 wt% CO2, and moves its
bubble point 0.19 C. That is why a memo entry is **never served flat**; see below.

The bug: path dependence
------------------------
Both memos originally solved at the **caller's** (T, P, z) and stored that answer for the
whole bin, so every later point in the bin got the value of whichever point happened to
fill it *first* — and what filled it first depended on everything the process had computed
before.

Measured, in one process with identical globals and a bit-identical seed state: 1200 s from
the design seed put 323F010 at

    99.000257 C   with the memo as imported
    99.010351 C   after clearing the cache
    99.005956 C   after a boot settle had filled it

A cold boot-pin cache takes the last branch, so the engine's answers after a model change
differed from its answers after a cached boot, and a generational clear re-rolled them
inside any long run.

The mechanism that made it matter is the **departure form**: the design value is stored
once, at import, while the live call reads the bin. With first-filler semantics those agree
only while the design point is still the bin's filler; after any clear, a live point refills
it and the "zero at design" bracket becomes a constant offset of up to one quantum's worth
of bubble point.

The fix, and the second bug it created
---------------------------------------
Solving at the bin's **canonical point** — its integer key times the quantum — makes every
memo entry a pure function of its key, so fill order, clears and boot path cannot change it.

But serving that canonical value *flat* across the bin was the first attempt, and it was
also wrong. A 1e-4 mass-fraction bin is 1.5 % wide in 323F004's CO2 and the electrolyte
bubble point moves 0.19 C across it, so flat canonical values turned every bin edge into a
0.19 C relay. The F004 pressure loop sat on one and **chattered**: saturation temperature
flipping 105.87 <-> 106.06 C every two seconds, the flash vapour 4.40 <-> 4.45 t/h. (The
first-filler memo had the same 0.19 C inside every such bin — it hid it as history-dependent
bias instead of showing it as a step.)

So each entry stores what is needed to answer for the **caller's own point**:

    bubble_t   a first-order expansion about the canonical point
    flash      the canonical K, with Rachford-Rice re-solved on the caller's own feed

Both are continuous across bin edges and independent of fill order.

Where memoisation is deliberately NOT used
-------------------------------------------
`thermo.kvalues.k_ratio` is not memoised, and that is the one place in this layer where a
quantised memo is the *wrong* answer. See its docstring.

Ported from V1 `backend/thermo_service.py` (memo block). Numerically identical.
"""

from __future__ import annotations

from ureasim.thermo.domains import SPECIES

# ======================================================================================
# Quanta
# ======================================================================================

#: Temperature quantum [deg C] — 25x finer than any TT resolution in the plant.
T_QUANTUM_C = 0.02

#: Pressure quantum [bar a] — 100x finer than any PT resolution.
P_QUANTUM_BARA = 1.0e-4

#: Composition quantum [mass fraction] — 100 ppm, about 100x below any analyser.
W_QUANTUM = 1.0e-4

#: Set to 0 to disable the flash memo entirely and solve every call.
FLASH_CACHE_SIZE = 4096

#: Set to 0 to disable the bubble-temperature memo.
BUBT_CACHE_SIZE = 4096

#: Warm-start buckets for the flash's successive-substitution start point. Coarse enough
#: that one stage keeps one entry across its whole operating excursion, fine enough that
#: two different stages never share one.
WARM_T_BUCKET_C = 10.0
WARM_P_BUCKET_BARA = 0.5


# ======================================================================================
# Caches
# ======================================================================================

#: key -> FlashResult solved at the bin's canonical point.
flash_cache: dict = {}

#: key -> (T_c, P_c, z_c, dP/dz, dP/dT) linearisation about the canonical point.
bubble_t_cache: dict = {}

#: (T, P) bucket -> converged liquid composition, used only to start the SS loop faster.
warm_start: dict = {}

_flash_stats = {"hit": 0, "miss": 0}
_bubble_t_stats = {"hit": 0, "miss": 0}


def canonical_point(p_key: int, z_key: tuple) -> tuple[float, dict]:
    """The one ``(P, z)`` a memo bin stands for: its integer key times the quantum.

    This is what makes every memo entry a pure function of its key — see the module
    docstring for the path-dependence bug it fixes.
    """
    z_q = {s: k * W_QUANTUM for s, k in zip(SPECIES, z_key)}
    return p_key * P_QUANTUM_BARA, z_q


def flash_cache_stats() -> dict:
    """Hit/miss counters for the quantised flash memo — telemetry and tests."""
    total = _flash_stats["hit"] + _flash_stats["miss"]
    return {"hit": _flash_stats["hit"], "miss": _flash_stats["miss"],
            "entries": len(flash_cache),
            "hit_rate": (_flash_stats["hit"] / total) if total else 0.0}


def bubble_t_cache_stats() -> dict:
    """Hit/miss counters for the quantised bubble-T memo — telemetry and tests."""
    total = _bubble_t_stats["hit"] + _bubble_t_stats["miss"]
    return {"hit": _bubble_t_stats["hit"], "miss": _bubble_t_stats["miss"],
            "entries": len(bubble_t_cache),
            "hit_rate": (_bubble_t_stats["hit"] / total) if total else 0.0}


def record_flash(hit: bool) -> None:
    _flash_stats["hit" if hit else "miss"] += 1


def record_bubble_t(hit: bool) -> None:
    _bubble_t_stats["hit" if hit else "miss"] += 1


def clear() -> None:
    """Drop every cached solve and reset the counters.

    Safe at any time: an entry is a pure function of its key, so clearing changes
    performance and nothing else. That was NOT true before the canonical point — a clear
    used to change the engine's answers.
    """
    flash_cache.clear()
    warm_start.clear()
    bubble_t_cache.clear()
    _flash_stats["hit"] = _flash_stats["miss"] = 0
    _bubble_t_stats["hit"] = _bubble_t_stats["miss"] = 0


__all__ = [
    "T_QUANTUM_C", "P_QUANTUM_BARA", "W_QUANTUM",
    "FLASH_CACHE_SIZE", "BUBT_CACHE_SIZE",
    "WARM_T_BUCKET_C", "WARM_P_BUCKET_BARA",
    "flash_cache", "bubble_t_cache", "warm_start",
    "canonical_point", "flash_cache_stats", "bubble_t_cache_stats",
    "record_flash", "record_bubble_t", "clear",
]
