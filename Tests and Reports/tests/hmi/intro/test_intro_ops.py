"""Tests of ``ureasim/hmi/intro/ops.py``: the drawing operations the intro's scene is written in.

Pinned: the operations are plain frozen data (hashable and compared by value, which is what lets the
painter see that a group repeated), a ``Rect`` knows its edges and centre, and ``flatten`` opens every
``Static`` group in drawing order, nested ones included.
"""

from __future__ import annotations

import dataclasses

import pytest

from ureasim.hmi.intro import ops
from ureasim.hmi.intro.ops import Circle, GradientRect, Image, Line, Lines, Polygon, Rect, RoundRect, Static, Text, flatten

_RECT = Rect(10.0, 20.0, 30.0, 40.0)
_ALL = (
    GradientRect(_RECT, "#fff", "#000"),
    Line(0.0, 0.0, 1.0, 1.0, "#000", 1.0),
    Lines(((0.0, 0.0, 1.0, 1.0),), "#000", 1.0),
    Circle(1.0, 2.0, 3.0, "#000"),
    RoundRect(_RECT, 4.0, "#000"),
    Polygon(((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)), "#000"),
    Text(1.0, 2.0, "TAG", 11.0, "#000"),
    Image("logo", _RECT, _RECT),
    Static((Line(0.0, 0.0, 1.0, 1.0, "#000", 1.0),)),
)


def test_a_rect_knows_its_edges_and_its_centre() -> None:
    assert (_RECT.right, _RECT.bottom, _RECT.cx, _RECT.cy) == (40.0, 60.0, 25.0, 40.0)


@pytest.mark.parametrize("op", _ALL, ids=lambda o: type(o).__name__)
def test_every_operation_is_frozen_hashable_data_compared_by_value(op) -> None:
    assert dataclasses.is_dataclass(op) and hash(op) == hash(dataclasses.replace(op))
    assert op == dataclasses.replace(op)
    with pytest.raises(dataclasses.FrozenInstanceError):
        op.__setattr__(dataclasses.fields(op)[0].name, None)


def test_the_operation_union_names_every_operation() -> None:
    assert set(ops.Op.__args__) == {type(o) for o in _ALL}


def test_the_defaults_are_opaque_ink_and_a_filled_shape() -> None:
    assert Line(0, 0, 1, 1, "#000", 1.0).alpha == 1.0 and Circle(0, 0, 1, "#000").width == 0.0
    assert Text(0, 0, "A", 10.0, "#000").anchor == "center" and Text(0, 0, "A", 10.0, "#000").bold is False
    assert Static(()).opaque is False


def test_a_static_group_compares_by_content_so_a_repeat_is_seen() -> None:
    a = Static((Line(0.0, 0.0, 1.0, 1.0, "#000", 1.0), Circle(1.0, 1.0, 2.0, "#111")), opaque=True)
    b = Static((Line(0.0, 0.0, 1.0, 1.0, "#000", 1.0), Circle(1.0, 1.0, 2.0, "#111")), opaque=True)
    assert a == b and a is not b and hash(a) == hash(b)
    assert a != Static(a.ops, opaque=False)
    assert a != Static((Line(0.0, 0.0, 1.0, 1.1, "#000", 1.0),) + a.ops[1:], opaque=True)


def test_flatten_opens_static_groups_in_drawing_order_nested_ones_too() -> None:
    first, second, third, fourth = (Line(float(i), 0.0, float(i), 1.0, "#000", 1.0) for i in range(4))
    frame = [first, Static((second, Static((third,)))), fourth]
    assert list(flatten(frame)) == [first, second, third, fourth]
    assert list(flatten([])) == [] and list(flatten([Static(())])) == []


def test_flatten_leaves_a_frame_with_no_groups_as_it_is() -> None:
    frame = list(_ALL[:-1])
    assert list(flatten(frame)) == frame
