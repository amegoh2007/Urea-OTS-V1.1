"""Signal conditioning — what an INDICATOR does to the value it displays.

What this models
----------------
The path from a process quantity to the number on the operator's screen: a thermowell's
thermal mass, a transmitter's damping filter, the time a sample takes to reach an analyser.
These act on the PUBLISHED signal only. They never touch a physics state.

Process utility
---------------
An operator does not see the plant, they see the instruments, and the instruments lag. A
trainee who opens a valve and watches TT-322011 must see the indication move the way the
real transmitter moves — smoothly, a little late — or they learn a reaction time that will
be wrong on the plant. Equally, a trainee must NOT be able to out-run the instrumentation:
if the displayed temperature snapped to the new steady state, every control exercise would
be easier in the simulator than in the control room.

Where this must not be used
---------------------------
A lag applied to a STATE is an invented time constant, and V1's directives forbid it: the
dynamics of a vessel come from its inventory and its duty, not from a filter bolted on
afterwards. Everything in this module operates on a value that has already been computed by
the physics and is on its way to a screen.

Numerical note — why a timestamped FIFO and not a sample counter
-----------------------------------------------------------------
The integrator advances each real tick in bounded sub-steps whose size is NOT fixed: the
remainder sub-step is frequently a numerical crumb of order 1e-8 s. A dead-time buffer
sized as ``n = td/dt`` would therefore have to hold ~1e10 samples on one of those, which is
a MemoryError, not a lag. Timestamping the samples and zero-order-holding against a
per-sub-step clock removes the dependence on `dt` entirely.

All three functions keep their state in a caller-supplied ``store`` dict keyed by ``key``,
which is the engine's transport-lag store. Nothing here holds module-level state, so two
simulator instances in one process cannot interfere.

Source: V1 `backend/main.py` `_lag1`, `_delay`, `_foptd`. Ported verbatim.
"""

from __future__ import annotations

from collections import deque

__all__ = ["first_order_lag", "dead_time", "first_order_plus_dead_time"]


def first_order_lag(store: dict, key: str, target: float, tau_s: float, dt: float) -> float:
    """First-order lag of a displayed value toward ``target``, time constant ``tau_s`` [s].

    Process utility
    ---------------
    A thermowell, a filled-system bulb, or a transmitter's damping. The indication
    approaches the process value exponentially rather than stepping to it.

    Equation
    --------
        y_new = y + a (target - y),      a = dt / (tau + dt)

    This is implicit (backward) Euler, which is unconditionally stable for ANY ratio of
    dt to tau — including the crumb sub-steps described in the module docstring, where an
    explicit form would ring or diverge. At steady state it converges exactly to ``target``,
    so the design point stays bit-exact.

    Lazy-initialised to ``target`` on the first call, so there is no boot transient on a
    display that should already be showing the design value.
    """
    prev = store.get(key)
    if prev is None or tau_s <= 0.0:
        store[key] = target
        return target
    a = dt / (tau_s + dt)
    val = prev + a * (target - prev)
    store[key] = val
    return val


def dead_time(store: dict, key: str, target: float, td_s: float, dt: float) -> float:
    """Pure transport delay ``y(t) = u(t - td)``, robust to a VARIABLE sub-step ``dt``.

    Process utility
    ---------------
    A sample line, an analyser cycle, or a feed run between the battery-limit meter and the
    point of use. Unlike a lag, a dead time changes nothing about the SHAPE of the signal —
    it moves it in time, which is the harder thing for a trainee to control around.

    Conservation-safe: every input sample is emitted exactly once, only re-timed, never
    scaled and never created. Until ``td`` seconds of history have accumulated the input
    passes through unchanged, and a constant input yields a constant output for all t — so
    the design pin survives the first ``td`` seconds of a run.
    """
    if td_s <= 0.0 or dt <= 0.0:
        return target
    st = store.get(key)
    if st is None:
        st = {"t": 0.0, "buf": deque()}          # buf: (entry_time, value), oldest first
        store[key] = st
    st["t"] += dt
    now = st["t"]
    buf = st["buf"]
    buf.append((now, target))
    cutoff = now - td_s
    # Drop only superseded samples: keep the newest whose entry time is already at or
    # before the cutoff, so the zero-order hold still has a value to emit on later ticks.
    # O(1) amortised per tick.
    while len(buf) >= 2 and buf[1][0] <= cutoff:
        buf.popleft()
    if buf[0][0] <= cutoff:
        return buf[0][1]
    return target                                # history younger than td -> pass through


def first_order_plus_dead_time(store: dict, key: str, target: float, tau_s: float,
                               td_s: float, dt: float) -> float:
    """First-order-plus-dead-time:  ``dy/dt = (u(t - td) - y) / tau``.

    Process utility
    ---------------
    The shape almost every real measurement has, and the shape every loop in this plant was
    tuned against: transport first, then the sensor's own thermal or damping lag. Realises
    ``G(s) = exp(-td.s) / (tau.s + 1)`` on a published signal without touching the physics
    state underneath it.

    Composed from `dead_time` and `first_order_lag` on two derived keys, so the two pieces
    of state stay separate and neither can be confused for the other in the store.
    """
    u_delayed = dead_time(store, key + ":dl", target, td_s, dt)
    return first_order_lag(store, key + ":lag", u_delayed, tau_s, dt)
