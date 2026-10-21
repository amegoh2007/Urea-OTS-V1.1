"""Overlay element widgets, and the registry that maps a layout type to one of them.

Every element in `ureasim.data.screen_layout` carries a type field ``t``. The registry
below is the single place that turns that letter code into a widget class, so adding an
element type is one entry here plus one module — and an unknown type fails loudly at build
time rather than silently rendering nothing.
"""

from __future__ import annotations

from typing import Any, Mapping

from PyQt6.QtWidgets import QWidget

from ureasim.hmi.widgets.bargraph import BargraphWidget
from ureasim.hmi.widgets.base import OverlayWidget
from ureasim.hmi.widgets.hotspots import (
    AnalyserWidget,
    HandSwitchWidget,
    NavHotspotWidget,
    OverrideButtonWidget,
    PushButtonWidget,
    StreamHotspotWidget,
)
from ureasim.hmi.widgets.icons import BlockValveWidget, PumpWidget
from ureasim.hmi.widgets.indicator import IndicatorWidget

#: Layout type code -> widget class. Mirrors ``screen_layout.ELEMENT_TYPES``.
WIDGET_REGISTRY: dict[str, type[OverlayWidget]] = {
    "ind": IndicatorWidget,
    "nav": NavHotspotWidget,
    "pump": PumpWidget,
    "bar": BargraphWidget,
    "strm": StreamHotspotWidget,
    "xv": BlockValveWidget,
    "hs": HandSwitchWidget,
    "ae": AnalyserWidget,
    "ovrd": OverrideButtonWidget,
    "btn": PushButtonWidget,
}


def build_widget(element: Mapping[str, Any],
                 parent: QWidget | None = None) -> OverlayWidget:
    """Construct the widget for one layout element.

    Raises
    ------
    KeyError
        For an unknown element type. Failing here is deliberate: a silently skipped
        element is an instrument that stops existing, and only a pixel comparison would
        ever catch it.
    """
    kind = element.get("t")
    try:
        cls = WIDGET_REGISTRY[kind]
    except KeyError:
        raise KeyError(
            f"no widget registered for element type {kind!r} "
            f"(element {element.get('k')!r}, tag {element.get('tag')!r})"
        ) from None
    return cls(element, parent)


__all__ = [
    "WIDGET_REGISTRY", "build_widget", "OverlayWidget",
    "IndicatorWidget", "BargraphWidget", "PumpWidget", "BlockValveWidget",
    "NavHotspotWidget", "StreamHotspotWidget",
    "AnalyserWidget", "HandSwitchWidget", "OverrideButtonWidget", "PushButtonWidget",
]
