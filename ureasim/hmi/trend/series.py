"""What a trend pen reads: the tag-to-path registry, and the historian's answer read for display.

What this is
------------
The trend window plots the engine historian's ring buffers and nothing else. It keeps no
samples of its own: once a second it asks for its whole visible window (`ureasim.hmi.bridge.
EngineBridge.request_history`) and repaints the answer, so two consoles trending the same tag
draw the same trace and a console that reconnects loses nothing. This module turns that answer
into what the window draws — each pen's points, its range, its statistics over the view and
its value under a ruler — without touching Qt, so every rule is testable on a plain answer.

The registry is V1's: a tag trends the path its first bound indicator, valve opening or push
button binds, or a block valve's or a pump's state as a 0 / 1 pen; an absolute pressure reads
gauge, as every transmitter on the screens does (`ureasim.hmi.state_access`).

Source: V1 ``frontend/trend.js`` (``Registry``, ``backfill``, ``rescale``, ``valueAt``,
``windowStats``, ``wallAt``, ``norm``, ``hms``, ``deskClock``, ``parseSpan``) and
``frontend/overlays.js`` (``buildBindMap``'s trend map).
"""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from ureasim.data.trend import (
    ANALOGUE_TYPES,
    DIGITAL_TYPES,
    SPAN_MAX_S,
    SPAN_MIN_S,
    SPANS,
    UNIT_RANGE,
)
from ureasim.hmi.state_access import ATM_BAR

#: A flat trace is given this band either side of its value, so it reads (V1's 0.5).
FLAT_BAND = 0.5
#: An auto-scaled pen is padded by this fraction of its range above and below (V1's 5 %).
AUTO_PAD = 0.05
#: A range narrower than this is a point: the pen draws at mid-scale (V1's 1e-12).
RANGE_EPS = 1e-12

#: A typed span: a number, then s, m or h (V1's ``parseSpan`` pattern).
_SPAN_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*([smh]?)$", re.IGNORECASE)


@dataclass(frozen=True)
class PenSource:
    """What one tag trends: the packet path, its display unit and decimals, its seed range."""

    tag: str
    path: str
    #: The unit shown; an absolute pressure shows BARG.
    unit: str
    dec: int
    #: The range shown until the first samples arrive.
    seed: tuple[float, float]
    #: True for an absolute pressure, which is drawn gauge.
    gauge: bool

    @property
    def digital(self) -> bool:
        """A 0 / 1 state pen, drawn stepped on a fixed 0 - 1 scale."""
        return self.unit == ""


def _source(tag: str, bind: str, u: Any, dec: Any, rng: Any) -> PenSource:
    unit = str(u or "").upper()
    seed = tuple(rng) if rng else UNIT_RANGE.get(unit, (0.0, 1.0))
    return PenSource(tag=tag, path=bind, unit="BARG" if unit == "BAR A" else unit,
                     dec=1 if dec is None else int(dec), seed=(float(seed[0]), float(seed[1])),
                     gauge=unit == "BAR A")


def trend_sources(screens: Mapping[str, Iterable[Mapping[str, Any]]]) -> dict[str, PenSource]:
    """Every trendable tag and what it trends, the first bound occurrence across all screens.

    Process utility
    ---------------
    A trainee can trend any instrument they can see, by the tag printed beside it, and a tag
    drawn on two screens trends the same path from either.
    """
    out: dict[str, PenSource] = {}
    for elements in screens.values():
        for el in elements:
            tag, bind, kind = el.get("tag"), el.get("bind"), el.get("t")
            if not tag or not bind or tag in out:
                continue
            if kind in ANALOGUE_TYPES:
                out[tag] = _source(tag, bind, el.get("u"), el.get("dec"), el.get("rng"))
            elif kind in DIGITAL_TYPES:
                path = f"{bind}.on" if kind == "pump" else bind
                out[tag] = _source(tag, path, "", 0, (0.0, 1.0))
    return out


# ======================================================================================
# The historian's answer, read for display
# ======================================================================================

def pen_points(answer: Mapping[str, Any] | None, source: PenSource) -> list[tuple[float, float]]:
    """One pen's points [(plant s, value)] from a history answer, gauge where it reads gauge.

    A sample the historian holds as "no data" is left out, so the trace breaks rather than
    drawing to zero.
    """
    if not answer:
        return []
    values = (answer.get("series") or {}).get(source.path)
    if not values:
        return []
    out = []
    for t, v in zip(answer.get("t_sim") or (), values):
        if t is None or v is None or not math.isfinite(v):
            continue
        out.append((float(t), float(v) - ATM_BAR if source.gauge else float(v)))
    return out


def newest_time(answer: Mapping[str, Any] | None) -> float | None:
    """The plant time of the answer's newest sample, or None for an empty answer."""
    stamps = (answer or {}).get("t_sim") or []
    return float(stamps[-1]) if stamps else None


def value_at(points: list[tuple[float, float]], t: float | None) -> float | None:
    """A pen's value at plant time t: the last sample at or before it, as a DCS cursor reads."""
    if t is None:
        return None
    best = None
    for pt, v in points:
        if pt > t:
            break
        best = v
    return best


def window_stats(points: list[tuple[float, float]], start: float,
                 end: float) -> tuple[float, float, float] | None:
    """MIN, MAX and AVG of a pen's samples in view [start, end], or None when none are."""
    seen = [v for t, v in points if start <= t <= end]
    if not seen:
        return None
    return min(seen), max(seen), sum(seen) / len(seen)


def auto_range(points: list[tuple[float, float]], start: float,
               end: float) -> tuple[float, float] | None:
    """The range an auto-scaled pen shows: its samples in view, padded 5 %; a flat trace gets
    a band of 0.5 either side. None when no sample is in view (the pen keeps its range)."""
    stats = window_stats(points, start, end)
    if stats is None:
        return None
    lo, hi = stats[0], stats[1]
    if hi - lo < 1e-9:
        lo, hi = lo - FLAT_BAND, hi + FLAT_BAND
    pad = (hi - lo) * AUTO_PAD
    return lo - pad, hi + pad


def to_percent(v: float, lo: float, hi: float) -> float:
    """A value on a pen's range as per cent of the plot's height."""
    if hi - lo < RANGE_EPS:
        return 50.0
    return (v - lo) / (hi - lo) * 100.0


def wall_at(answer: Mapping[str, Any] | None, t: float) -> float | None:
    """The desktop clock [epoch s] the engine stamped at plant time t, from the answer's own
    pairs: interpolated between samples, carried past the newest at one second a second, None
    before the oldest."""
    sims = (answer or {}).get("t_sim") or []
    walls = (answer or {}).get("t_wall") or []
    if not sims or t < sims[0]:
        return None
    for i in range(len(sims) - 1, -1, -1):
        if sims[i] <= t:
            if i + 1 >= len(sims):
                return walls[i] + (t - sims[i])
            f = (t - sims[i]) / max(1e-9, sims[i + 1] - sims[i])
            return walls[i] + f * (walls[i + 1] - walls[i])
    return None


# ======================================================================================
# Clocks and spans
# ======================================================================================

def hms(seconds: float) -> str:
    """Plant time as HH:MM:SS."""
    s = max(0, int(math.floor(seconds)))
    return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}"


def desk_clock(epoch: float | None) -> str:
    """The desktop clock as HH:MM:SS local time, or --:--:-- when unknown."""
    if epoch is None or not math.isfinite(epoch):
        return "--:--:--"
    return time.strftime("%H:%M:%S", time.localtime(epoch))


def parse_span(text: str) -> int | None:
    """A typed span — "30s", "10m", "3h", or bare seconds — in whole seconds, or None when it
    does not parse or falls outside 5 s to 24 h."""
    m = _SPAN_RE.match((text or "").strip())
    if not m:
        return None
    s = float(m.group(1)) * {"h": 3600.0, "m": 60.0}.get(m.group(2).lower(), 1.0)
    return int(round(s)) if SPAN_MIN_S <= s <= SPAN_MAX_S else None


def span_label(span_s: int) -> str:
    """A span as its button reads, or as a typed span would be written back."""
    for s, label in SPANS:
        if s == span_s:
            return label
    if span_s % 3600 == 0:
        return f"{span_s // 3600}h"
    if span_s % 60 == 0:
        return f"{span_s // 60}m"
    return f"{span_s}s"


__all__ = ["PenSource", "trend_sources", "pen_points", "newest_time", "value_at",
           "window_stats", "auto_range", "to_percent", "wall_at", "hms", "desk_clock",
           "parse_span", "span_label", "FLAT_BAND", "AUTO_PAD", "RANGE_EPS"]
