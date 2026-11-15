"""The trend window's constants — `ureasim.data.trend` and the trend palette in `ureasim.hmi.theme`
— against V1's ``frontend/trend.js`` and ``overlays.js``, read from V1's source.

Pinned: the ten pens, the seven spans and their labels, the one-hour default, the 800 points, the ten
rulers, the quarter-span scroll, the seed ranges by unit, the trendable element types, the pen and
ruler colours, and the custom-span bounds.
"""

from __future__ import annotations

import re

import pytest

from ureasim.data import trend as tr
from ureasim.hmi import theme
from tests.equivalence.v1_loader import V1_ROOT

TREND_JS = V1_ROOT / "frontend" / "trend.js"
OVERLAYS_JS = V1_ROOT / "frontend" / "overlays.js"

pytestmark = pytest.mark.skipif(not TREND_JS.is_file(), reason="V1's front end not on this machine")


@pytest.fixture(scope="module")
def js():
    return TREND_JS.read_text(encoding="utf-8")


def _const(js: str, name: str) -> str:
    return re.search(rf"const {name} = (.+?);", js, re.S).group(1)


def test_slots_spans_points_rulers_and_scroll(js):
    assert tr.SLOTS == int(_const(js, "SLOTS"))
    spans = re.findall(r"\{ s: (\d+),\s*lbl: '(\w+)'\s*\}", _const(js, "SPANS"))
    assert tr.SPANS == tuple((int(s), lbl) for s, lbl in spans)
    assert tr.DEFAULT_SPAN_S == int(_const(js, "DEFAULT_SPAN").split()[0])
    assert tr.MAX_POINTS == int(_const(js, "MAX_POINTS"))
    assert tr.RULERS_MAX == int(_const(js, "RULERS_MAX"))
    assert tr.PAN_FRACTION == float(_const(js, "PAN_FRACTION"))
    assert "Math.min(nowSim, 28800)" in js and tr.HISTORY_DEPTH_S == 28800
    assert "s >= 5 && s <= 86400" in js and (tr.SPAN_MIN_S, tr.SPAN_MAX_S) == (5, 86400)
    assert "(nowSim - last.t) > 30" in js and tr.STALE_S == 30.0


def test_the_seed_ranges_by_unit(js):
    body = _const(js, "UNIT_RANGE")
    theirs = {k: (float(a), float(b)) for k, a, b in
              re.findall(r"'([^']*)': \[(\d+), (\d+)\]", body)}
    assert tr.UNIT_RANGE == theirs


def test_the_pen_and_ruler_colours(js):
    pens = tuple(re.findall(r"'(#[0-9a-fA-F]{6})'", _const(js, "PENS")))
    rulers = tuple(re.findall(r"'(#[0-9a-fA-F]{6})'", _const(js, "RULER_COLORS")))
    assert theme.TREND_PENS == pens and theme.TREND_RULERS == rulers
    assert "PENS[i] + '40'" in js and theme.TREND_FADE_ALPHA == 0x40
    assert "hi ? 3.2 : 1.4" in js and (theme.TREND_PEN_W_MARKED, theme.TREND_PEN_W) == (3.2, 1.4)


def test_the_trendable_types_and_the_trend_map():
    ov = OVERLAYS_JS.read_text(encoding="utf-8")
    trendable = re.search(r"const TRENDABLE = \{([^}]*)\}", ov).group(1)
    assert tr.TRENDABLE == frozenset(re.findall(r"(\w+): 1", trendable))
    assert "(o.t === 'ind' || o.t === 'avalve' || o.t === 'btn') && o.bind" in ov
    assert tr.ANALOGUE_TYPES == ("ind", "avalve", "btn")
    assert "(o.t === 'xv' || o.t === 'pump') && o.bind" in ov
    assert "o.t === 'pump' ? o.bind + '.on' : o.bind" in ov
    assert tr.DIGITAL_TYPES == ("xv", "pump")
