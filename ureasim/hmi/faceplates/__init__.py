"""Faceplates — what a left-click on a process screen opens.

`faceplate_for` routes an overlay element exactly as V1's ``overlays.js`` ``activate`` did:

=====================================  ===========================================================
element                                faceplate
=====================================  ===========================================================
a pump the engine models (bind + id)   `PumpFaceplate` (START / STOP); an unbound pump is inert
a block valve, a hand switch           `BlockValveFaceplate` (V1 toggled a valve on its symbol)
HS-322915, the override keyswitch      `KeyswitchFaceplate`
LV-324501A / B (a ``route``)           `RouteFaceplate`
``face: 'hic' / 'hic2'``               `HandValveFaceplate`
``face: 'pic'``                        `ControllerFaceplate` on PIC-322203's fields
``fp: SIC_321950 / SIC_321951``        `SpeedFaceplate`
``fp: MASTER_SP_329207``               `MasterSetpointFaceplate`
``ctl`` (one field of a loop)          `ControllerFaceplate` of that loop
a ``*IC-3xx`` tag                      `ControllerFaceplate`
any other bound value                  `IndicatorFaceplate`
a stream hotspot, an analyser          `StreamInspector` (`hmi.widgets.stream_hotspot`), when
                                       the packet publishes the stream
=====================================  ===========================================================

Navigation hotspots never reach here. Every faceplate is a dumb renderer of the packet and an emitter of the
engine's commands (`ureasim.hmi.faceplates.base`).

Source: V1 ``frontend/overlays.js`` 640 (``CTRL_RE``) and 723-778.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QWidget

from ureasim.hmi.faceplates.base import Faceplate
from ureasim.hmi.faceplates.controller import ControllerFaceplate, loop_spec
from ureasim.hmi.faceplates.hand_valve import HandValveFaceplate, hand_valve_of
from ureasim.hmi.faceplates.indicator import IndicatorFaceplate
from ureasim.hmi.faceplates.master_setpoint import MasterSetpointFaceplate
from ureasim.hmi.faceplates.pump import PumpFaceplate
from ureasim.hmi.faceplates.speed import SpeedFaceplate
from ureasim.hmi.faceplates.switches import BlockValveFaceplate, KeyswitchFaceplate, RouteFaceplate
from ureasim.hmi.widgets.stream_hotspot import StreamInspector, published_stream

__all__ = ["faceplate_for", "faceplate_key", "Faceplate", "CTRL_RE"]

#: Any loop controller tag of the urea plant (PIC / HIC / LIC / TIC / FIC / SIC-3xx). V1's.
CTRL_RE = re.compile(r"[A-Z]IC-3\d{2}", re.IGNORECASE)


def faceplate_key(element: Mapping[str, Any]) -> str:
    """One faceplate per instrument: the key a console keeps an open faceplate under."""
    if element.get("fp"):
        return str(element["fp"])
    if element.get("ctl"):
        return str(element["ctl"])
    if element.get("face") == "hic2":
        return "HIC-322203"
    return str(element.get("tag", ""))


def faceplate_for(element: Mapping[str, Any], bridge: QObject,
                  parent: QWidget | None = None) -> Faceplate | None:
    """The faceplate an overlay element opens, or None when it opens none."""
    t = element.get("t")
    tag = str(element.get("tag", ""))
    if t == "pump":
        if element.get("bind") and element.get("id"):
            return PumpFaceplate(bridge, element, parent)
        return None
    if t in ("xv", "hs"):
        return BlockValveFaceplate(bridge, element, parent)
    if t == "ovrd":
        return KeyswitchFaceplate(bridge, element, parent)
    if t in ("ae", "strm"):
        # V1 opens nothing for a stream the packet does not carry.
        if published_stream(bridge.latest, str(element.get("stream") or "")) is None:
            return None
        return StreamInspector(bridge, element, parent)
    if t == "nav":
        return None
    if t == "avalve" and element.get("route"):
        return RouteFaceplate(bridge, element, parent)
    face = element.get("face")
    if face in ("hic", "hic2") and hand_valve_of(element) is not None:
        return HandValveFaceplate(bridge, element, parent)
    if face == "pic":
        return ControllerFaceplate(bridge, loop_spec(element), parent)
    fp = element.get("fp")
    if fp in ("SIC_321950", "SIC_321951"):
        return SpeedFaceplate(bridge, str(fp), parent)
    if fp == "MASTER_SP_329207":
        return MasterSetpointFaceplate(bridge, parent)
    if element.get("ctl"):
        loop = dict(element, tag=element["ctl"], bind=element.get("ctlBind"),
                    u=element.get("ctlU") or element.get("u"))
        return ControllerFaceplate(bridge, loop_spec(loop), parent)
    if CTRL_RE.search(tag):
        return ControllerFaceplate(bridge, loop_spec(element), parent)
    if element.get("bind"):
        return IndicatorFaceplate(bridge, element, parent)
    return None
