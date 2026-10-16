"""The multi-pen trend window's fixed choices: pens, spans, rulers, seed ranges.

What this is
------------
The constants V1's trend window was built on, kept so the port's window offers a trainee the
same ten pens, the same seven spans and the same ten rulers. They are presentation choices, not
plant data: which element types can carry a pen, how far back a pen looks, how many points one
request returns, and the range a pen shows until its first samples arrive.

One choice is the port's own. V1's window kept the points every packet brought and backfilled
the rest from the historian; the port's console keeps no process data, so its window asks the
historian for the whole visible window once a second and repaints the answer (`POLL_MS`).

source = V1 ``frontend/trend.js`` (``SLOTS``, ``SPANS``, ``DEFAULT_SPAN``, ``MAX_POINTS``,
``RULERS_MAX``, ``UNIT_RANGE``, ``PAN_FRACTION``, the 5 s - 24 h custom-span bounds of
``parseSpan``, the 30 s ``STALE`` rule) and ``frontend/overlays.js`` (``TRENDABLE`` and
``buildBindMap``'s trend map).
"""

from __future__ import annotations

#: Pens a window holds. Source: V1 ``SLOTS``.
SLOTS = 10

#: The span buttons [plant s] and their labels. Source: V1 ``SPANS``.
SPANS = ((60, "1m"), (300, "5m"), (1800, "30m"), (3600, "1h"), (7200, "2h"), (14400, "4h"),
         (28800, "8h"))

#: The span a new window opens on [plant s], one hour. Source: V1 ``DEFAULT_SPAN``.
DEFAULT_SPAN_S = 3600

#: The bounds a typed span must fall within [s]. Source: V1 ``parseSpan``.
SPAN_MIN_S = 5
SPAN_MAX_S = 86400

#: Points one history request returns a pen at most; the historian decimates to it with a
#: min/max envelope. Source: V1 ``MAX_POINTS``.
MAX_POINTS = 800

#: Rulers a window holds. Source: V1 ``RULERS_MAX``.
RULERS_MAX = 10

#: How far one scroll moves the window, as a fraction of its span. Source: V1 ``PAN_FRACTION``.
PAN_FRACTION = 0.25

#: The oldest a window may look back [plant s]: the historian's slow ring, 2880 x 10 s.
#: Source: V1 ``maxPanBack`` (28 800 s); ``ureasim.engine.historian.RINGS``.
HISTORY_DEPTH_S = 28800

#: A pen whose newest sample is older than this reads STALE [plant s]. Source: V1 ``renderRows``.
STALE_S = 30.0

#: How often a live window asks the historian for its whole window [ms]. The port's choice: the
#: historian's fine ring samples once a plant second, so a faster poll would return the same
#: points; one request is in flight at a time.
POLL_MS = 1000

#: The range a pen shows until its first samples arrive, by its unit. Analogue pens then
#: auto-scale to the samples in view; a digital pen (no unit) stays on 0 - 1. Source: V1
#: ``UNIT_RANGE``.
UNIT_RANGE = {
    "%": (0.0, 100.0), "C": (0.0, 250.0), "BAR G": (0.0, 200.0), "BARG": (0.0, 200.0),
    "BAR A": (0.0, 200.0), "T/H": (0.0, 100.0), "RPM": (0.0, 3000.0), "A": (0.0, 200.0),
    "NM3/H": (0.0, 40000.0), "KG/H": (0.0, 50000.0), "M3/H": (0.0, 500.0), "KW": (0.0, 5000.0),
    "": (0.0, 1.0),
}

#: Element types whose value a pen can carry: an analogue value, a valve opening, a valve's or
#: a pump's state. Source: V1 ``TRENDABLE``.
TRENDABLE = frozenset({"ind", "avalve", "xv", "pump", "bar", "btn"})

#: Element types that trend their bound analogue value, and those that trend as a 0 / 1
#: digital pen (a pump on its ``.on`` flag). A ``bar`` is trendable but carries no pen of its
#: own: it trends only when an indicator of the same tag does. Source: V1 ``buildBindMap``.
ANALOGUE_TYPES = ("ind", "avalve", "btn")
DIGITAL_TYPES = ("xv", "pump")

__all__ = ["SLOTS", "SPANS", "DEFAULT_SPAN_S", "SPAN_MIN_S", "SPAN_MAX_S", "MAX_POINTS",
           "RULERS_MAX", "PAN_FRACTION", "HISTORY_DEPTH_S", "STALE_S", "POLL_MS", "UNIT_RANGE",
           "TRENDABLE", "ANALOGUE_TYPES", "DIGITAL_TYPES"]
