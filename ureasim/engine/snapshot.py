"""Exercise snapshots — the whole plant state saved and restored, so a restored exercise replays
bit for bit.

What this is for
----------------
An instructor saves an exercise at a moment worth returning to — the plant at 100 % load, the
loop just after a trip, a trainee's mistake — and restores it later, on this machine or another,
to run the same lesson again. A restored plant must then do exactly what the saved one would have
done: every tick after a restore equals, to the bit, the tick the original plant ran. Anything
less and two trainees given "the same" exercise are not.

What is saved
-------------
`PlantState` is everything the engine owns between ticks (its docstring): the clock, the recycle
tears, every unit's and controller's state, what the operator holds and the boundary values. The
schedule is code, not state, and is not saved; nor are caches of pure functions, which return
what they would compute.

How
---
The state is walked as it stands and written as JSON — readable during commissioning, as the
station protocol is — with every value exact:

* a float as its shortest round-tripping decimal (Python's ``repr``), a non-finite one tagged;
* a tuple, a mapping proxy, a set, a deque (a transit line's queue, with its bound) and a mapping
  with non-text keys tagged, so each comes back as what it was;
* an object of a ``ureasim`` class as its class and its attributes, rebuilt without running its
  constructor, so a frozen result or a controller's private integrator state comes back as saved;
* an object reached twice written once and referenced after, so two units sharing one controller
  still share it.

A snapshot names only ``ureasim`` classes; anything else is refused on save and on load. On load
the restored plant's shape — every unit, controller and attribute — is checked against the
present model's, and a snapshot saved by a different model is refused with the first difference
named, never half-restored. The one tolerance is a retired attribute (`data.retired_state`): a
piece of the model since removed, whose state an older save still holds, is dropped before the
object is rebuilt, so that save still loads (trip 22.2, decision 189). A reference left pointing
at a dropped record is refused.

Source: the rewrite's (``project.md`` §3.6: "exercise save and restore are its serialisation");
V1 had no exercise save. The protocol already reserves ``snapshot_save`` and ``snapshot_load``
for the instructor.
"""

from __future__ import annotations

import enum
import importlib
import json
import math
import time
from collections import deque
from types import MappingProxyType
from typing import Any

from ureasim.data.retired_state import RETIRED_ATTRIBUTES
from ureasim.engine.state import PlantState

__all__ = ["FORMAT", "VERSION", "SnapshotError", "encode_state", "decode_state",
           "check_compatible", "dumps", "loads", "save", "load"]

#: The document's format name and version: a reader refuses any other.
FORMAT = "ureasim-exercise"
VERSION = 1

#: Only classes from these modules may be named in a snapshot.
_TRUSTED = "ureasim."


class SnapshotError(ValueError):
    """A snapshot that cannot be written or restored, with the reason."""


# ======================================================================================
# Encoding
# ======================================================================================

def _class_path(cls: type) -> str:
    return f"{cls.__module__}:{cls.__qualname__}"


def _attributes(obj: Any) -> dict:
    """An object's state: its instance dictionary and any slots."""
    attrs = dict(vars(obj)) if hasattr(obj, "__dict__") else {}
    for klass in type(obj).__mro__:
        for name in getattr(klass, "__slots__", ()):
            if name not in ("__dict__", "__weakref__") and hasattr(obj, name):
                attrs[name] = getattr(obj, name)
    return attrs


class _Encoder:
    """Walks a state into JSON-able data, writing each shared mutable object once."""

    def __init__(self) -> None:
        self.ids: dict = {}

    def _shared(self, obj: Any, build) -> Any:
        n = self.ids.get(id(obj))
        if n is not None:
            return {"$r": n}
        n = self.ids[id(obj)] = len(self.ids)
        return build(n)

    def enc(self, obj: Any, path: str) -> Any:
        if obj is None or isinstance(obj, (bool, str)):
            return obj
        if isinstance(obj, int):
            return int(obj)
        if isinstance(obj, float):
            if math.isfinite(obj):
                return float(obj)
            return {"$f": "nan" if obj != obj else ("inf" if obj > 0 else "-inf")}
        if isinstance(obj, enum.Enum):
            return {"$e": _class_path(type(obj)), "v": obj.name}
        if isinstance(obj, tuple):
            return {"$t": [self.enc(v, f"{path}[{i}]") for i, v in enumerate(obj)]}
        if isinstance(obj, frozenset):
            return {"$fs": [self.enc(v, f"{path}{{}}") for v in obj]}
        if isinstance(obj, list):
            return self._shared(obj, lambda n: {"$l": [self.enc(v, f"{path}[{i}]")
                                                       for i, v in enumerate(obj)], "$id": n})
        if isinstance(obj, set):
            return self._shared(obj, lambda n: {"$s": [self.enc(v, f"{path}{{}}") for v in obj],
                                                "$id": n})
        if isinstance(obj, deque):
            return self._shared(obj, lambda n: {"$q": [self.enc(v, f"{path}[{i}]")
                                                       for i, v in enumerate(obj)],
                                                "maxlen": obj.maxlen, "$id": n})
        if isinstance(obj, MappingProxyType):
            return {"$mp": self.enc(dict(obj), path)}
        if isinstance(obj, dict):
            return self._shared(obj, lambda n: self._mapping(obj, path, n))
        cls = type(obj)
        if not cls.__module__.startswith(_TRUSTED):
            raise SnapshotError(f"{path}: a {cls.__module__}.{cls.__qualname__} cannot be saved")
        return self._shared(obj, lambda n: {
            "$o": _class_path(cls), "$id": n,
            "a": {k: self.enc(v, f"{path}.{k}") for k, v in _attributes(obj).items()}})

    def _mapping(self, obj: dict, path: str, n: int) -> dict:
        if all(isinstance(k, str) for k in obj):
            return {"$d": {k: self.enc(v, f"{path}[{k!r}]") for k, v in obj.items()}, "$id": n}
        return {"$m": [[self.enc(k, path), self.enc(v, f"{path}[{k!r}]")] for k, v in obj.items()],
                "$id": n}


def encode_state(plant: PlantState) -> dict:
    """The plant's state as JSON-able data (module docstring)."""
    return _Encoder().enc(plant, "plant")


# ======================================================================================
# Decoding
# ======================================================================================

def _resolve(path: str) -> type:
    module, _, qual = path.partition(":")
    if not (module + ".").startswith(_TRUSTED) or not qual:
        raise SnapshotError(f"the snapshot names {path!r}, which is not a ureasim class")
    try:
        obj = importlib.import_module(module)
        for part in qual.split("."):
            obj = getattr(obj, part)
    except (ImportError, AttributeError) as exc:
        raise SnapshotError(f"the snapshot names {path!r}, which this model does not have") from exc
    if not isinstance(obj, type):
        raise SnapshotError(f"the snapshot names {path!r}, which is not a class")
    return obj


class _Decoder:
    """Rebuilds a state from its encoding, shared objects shared again."""

    def __init__(self) -> None:
        self.objs: dict = {}

    def dec(self, data: Any) -> Any:
        if data is None or isinstance(data, (bool, int, float, str)):
            return data
        if isinstance(data, list):
            raise SnapshotError("an untagged list in the snapshot")
        if "$r" in data:
            try:
                return self.objs[data["$r"]]
            except KeyError:
                raise SnapshotError(f"the snapshot refers to object {data['$r']}, which it does "
                                    "not hold (a retired record referred to elsewhere?)") from None
        if "$f" in data:
            return float(data["$f"])
        if "$t" in data:
            return tuple(self.dec(v) for v in data["$t"])
        if "$fs" in data:
            return frozenset(self.dec(v) for v in data["$fs"])
        if "$mp" in data:
            return MappingProxyType(self.dec(data["$mp"]))
        if "$e" in data:
            return _resolve(data["$e"])[data["v"]]
        if "$l" in data:
            out: list = []
            self.objs[data["$id"]] = out
            out.extend(self.dec(v) for v in data["$l"])
            return out
        if "$q" in data:
            out_q: deque = deque(maxlen=data["maxlen"])
            self.objs[data["$id"]] = out_q
            out_q.extend(self.dec(v) for v in data["$q"])
            return out_q
        if "$s" in data:
            out_s: set = set()
            self.objs[data["$id"]] = out_s
            out_s.update(self.dec(v) for v in data["$s"])
            return out_s
        if "$d" in data or "$m" in data:
            out_d: dict = {}
            self.objs[data["$id"]] = out_d
            items = (data["$d"].items() if "$d" in data
                     else ((self.dec(k), v) for k, v in data["$m"]))
            for k, v in items:
                out_d[k] = self.dec(v)
            return out_d
        if "$o" in data:
            cls = _resolve(data["$o"])
            obj = cls.__new__(cls)
            self.objs[data["$id"]] = obj
            retired = RETIRED_ATTRIBUTES.get(data["$o"], ())
            for k, v in data["a"].items():
                if k not in retired:            # a removed piece's state, not rebuilt
                    object.__setattr__(obj, k, self.dec(v))
            return obj
        raise SnapshotError(f"an untagged object in the snapshot: {sorted(data)[:3]}")


def decode_state(data: Any) -> PlantState:
    """A plant state rebuilt from `encode_state`'s data."""
    plant = _Decoder().dec(data)
    if not isinstance(plant, PlantState):
        raise SnapshotError("the snapshot does not hold a plant state")
    return plant


# ======================================================================================
# Compatibility with the present model
# ======================================================================================

def _shape(obj: Any, path: str, out: dict, seen: set) -> None:
    """Every object's class and attribute names, and every unit mapping's keys, by path."""
    if id(obj) in seen:
        return
    if isinstance(obj, (dict, MappingProxyType)):
        if path.count(".") < 2:         # the plant's own mappings: units, loops, operator, ...
            out[path] = ("keys", tuple(sorted(map(str, obj))))
        seen.add(id(obj))
        for k, v in obj.items():
            _shape(v, f"{path}[{k!r}]", out, seen)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _shape(v, f"{path}[{i}]", out, seen)
    elif type(obj).__module__.startswith(_TRUSTED) and not isinstance(obj, enum.Enum):
        seen.add(id(obj))
        attrs = _attributes(obj)
        out[path] = (_class_path(type(obj)), tuple(sorted(attrs)))
        for k, v in attrs.items():
            _shape(v, f"{path}.{k}", out, seen)


def check_compatible(plant: PlantState, reference: PlantState) -> None:
    """Refuse ``plant`` unless every unit, controller and attribute of ``reference`` — a plant
    the present model builds — is there in the same shape; name the first difference."""
    mine: dict = {}
    theirs: dict = {}
    _shape(plant, "plant", mine, set())
    _shape(reference, "plant", theirs, set())
    # A state the run itself creates (a line's transit queue filled, a latch's record) exists on
    # one side only; every path both hold must agree, and the plant's own mappings always exist.
    top = {p for p in theirs if theirs[p][0] == "keys"}
    for path in sorted((set(mine) & set(theirs)) | top):
        if mine.get(path) != theirs.get(path):
            raise SnapshotError(f"the snapshot was saved by a different model: {path} is "
                                f"{mine.get(path)} in the snapshot, {theirs.get(path)} now")


# ======================================================================================
# Documents and files
# ======================================================================================

def dumps(plant: PlantState, note: str = "") -> str:
    """The plant as a snapshot document, JSON text."""
    doc = {"format": FORMAT, "version": VERSION, "tick": plant.clock.tick,
           "t_plant_s": plant.clock.time_s, "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "note": note, "state": encode_state(plant)}
    return json.dumps(doc, separators=(",", ":"), allow_nan=False)


def loads(text: str, reference: PlantState | None = None) -> PlantState:
    """A plant from a snapshot document; checked against ``reference`` (a freshly built plant)
    when one is given."""
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SnapshotError(f"not a snapshot: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("format") != FORMAT:
        raise SnapshotError("not a ureasim exercise snapshot")
    if doc.get("version") != VERSION:
        raise SnapshotError(f"snapshot version {doc.get('version')}, this engine reads {VERSION}")
    plant = decode_state(doc["state"])
    if reference is not None:
        check_compatible(plant, reference)
    return plant


def save(plant: PlantState, path: str, note: str = "") -> None:
    """Write the plant's snapshot to ``path``."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(dumps(plant, note))


def load(path: str, reference: PlantState | None = None) -> PlantState:
    """Read a plant from the snapshot at ``path`` (`loads`)."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as exc:
        raise SnapshotError(f"cannot read {path}: {exc}") from exc
    return loads(text, reference)
