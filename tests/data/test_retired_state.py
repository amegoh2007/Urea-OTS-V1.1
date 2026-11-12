"""Retired state — `ureasim.data.retired_state`.

Pinned: every class the table names is a class of the present model, none of its instances in the
assembled plant still carries a retired attribute, so the snapshot reader tolerates only what was
removed; and the table is read-only.
"""

from __future__ import annotations

import importlib

import pytest

from ureasim.data.retired_state import RETIRED_ATTRIBUTES
from ureasim.engine.plant import build_plant


def test_each_retired_attribute_is_gone_from_its_class():
    _, plant = build_plant()
    for path, names in RETIRED_ATTRIBUTES.items():
        module, _, qualname = path.partition(":")
        cls = getattr(importlib.import_module(module), qualname)
        instances = [u for u in plant.units.values() if type(u) is cls]
        assert instances, path
        assert not any(hasattr(u, n) for u in instances for n in names), path


def test_trip_22_2_is_the_one_retired_record():
    """Decision 189."""
    assert dict(RETIRED_ATTRIBUTES) == {
        "ureasim.engine.plant.synthesis_loop:SynthesisTrips": ("i_22_2",)}


def test_the_table_is_read_only():
    with pytest.raises(TypeError):
        RETIRED_ATTRIBUTES["ureasim.engine.plant.synthesis_loop:SynthesisTrips"] = ()
