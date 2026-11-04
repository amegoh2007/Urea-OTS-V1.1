"""Tests of ureasim/hmi/intro/camera.py: the look-at projection and the orbit, with no display."""

from __future__ import annotations

import math

import numpy as np
import pytest

from ureasim.data.intro import STAGE
from ureasim.data.intro_flyby import ORBIT
from ureasim.hmi.intro import camera
from ureasim.hmi.intro.camera import FOCAL, look_at, orbit_camera, project, to_camera, transform_all, transform_array

_EYES = [(0.0, -200.0, 90.0), (150.0, 30.0, 60.0), (-120.0, 140.0, 200.0), (15.0, 26.0 + 240.0, 100.0)]
_TARGET = (15.0, 26.0, 38.0)


def _dot(a, b) -> float:
    return sum(x * y for x, y in zip(a, b))


@pytest.mark.parametrize("eye", _EYES)
def test_the_basis_is_orthonormal_and_the_camera_looks_at_the_target(eye) -> None:
    cam = look_at(eye, _TARGET)
    for v in (cam.right, cam.up, cam.forward):
        assert _dot(v, v) == pytest.approx(1.0)
    assert _dot(cam.right, cam.up) == pytest.approx(0.0, abs=1e-12)
    assert _dot(cam.right, cam.forward) == pytest.approx(0.0, abs=1e-12)
    assert _dot(cam.up, cam.forward) == pytest.approx(0.0, abs=1e-12)
    to_target = [_TARGET[i] - eye[i] for i in range(3)]
    assert to_camera(cam, _TARGET) == pytest.approx((0.0, 0.0, math.sqrt(_dot(to_target, to_target))), abs=1e-9)
    assert cam.up[2] > 0.0  # the world's up stays up on the screen


@pytest.mark.parametrize("eye", _EYES)
def test_the_target_lands_on_the_screen_centre(eye) -> None:
    cam = look_at(eye, _TARGET)
    sx, sy, depth = project(cam, _TARGET)
    assert (sx, sy) == pytest.approx(ORBIT.centre) and depth > 0.0


def test_right_is_right_up_is_up_and_the_front_view_is_not_mirrored() -> None:
    """From the front (the camera in front of the plant, looking back) the x axis runs to the right."""
    cam = orbit_camera(_TARGET, 240.0, 100.0, -math.pi / 2.0)  # the camera at -y, looking toward +y
    cx, cy = ORBIT.centre
    assert project(cam, (_TARGET[0] + 40.0, _TARGET[1], _TARGET[2]))[0] > cx  # +x to the right: 322R001 left, 323C003 right
    assert project(cam, (_TARGET[0] - 40.0, _TARGET[1], _TARGET[2]))[0] < cx
    assert project(cam, (_TARGET[0], _TARGET[1], _TARGET[2] + 20.0))[1] < cy  # higher is nearer the top of the screen
    near = project(cam, (_TARGET[0], _TARGET[1] - 50.0, _TARGET[2]))
    far = project(cam, (_TARGET[0], _TARGET[1] + 50.0, _TARGET[2]))
    assert near[2] < far[2]


def test_a_point_behind_the_lens_is_not_projected() -> None:
    cam = look_at((0.0, -200.0, 50.0), (0.0, 0.0, 50.0))
    assert project(cam, (0.0, -300.0, 50.0)) is None
    assert project(cam, (0.0, -200.0 + ORBIT.near - 0.1, 50.0)) is None
    assert project(cam, (0.0, -200.0 + ORBIT.near + 0.1, 50.0)) is not None


def test_the_focal_length_gives_the_vertical_field_of_view_over_the_stage_height() -> None:
    assert FOCAL == pytest.approx((STAGE.height / 2.0) / math.tan(math.radians(ORBIT.fov_v_deg) / 2.0))
    cam = look_at((0.0, -100.0, 0.0), (0.0, 0.0, 0.0), centre=(STAGE.width / 2.0, STAGE.height / 2.0))
    half = math.radians(ORBIT.fov_v_deg) / 2.0
    top = project(cam, (0.0, 0.0, 100.0 * math.tan(half)))
    assert top[1] == pytest.approx(0.0, abs=1e-6)


def test_the_orbit_goes_counter_clockwise_seen_from_above_at_the_given_radius_and_height() -> None:
    for yaw, (dx, dy) in ((0.0, (1.0, 0.0)), (math.pi / 2.0, (0.0, 1.0)), (math.pi, (-1.0, 0.0)), (-math.pi / 2.0, (0.0, -1.0))):
        cam = camera.orbit_camera(_TARGET, 240.0, 100.0, yaw)
        assert cam.eye == pytest.approx((_TARGET[0] + 240.0 * dx, _TARGET[1] + 240.0 * dy, 100.0), abs=1e-9)


def test_transform_all_agrees_with_the_one_point_transform() -> None:
    cam = look_at(_EYES[1], _TARGET)
    pts = tuple((x * 7.0 - 50.0, x * -3.0 + 20.0, x * 2.0) for x in range(12))
    assert transform_all(cam, pts) == pytest.approx([to_camera(cam, p) for p in pts])


def test_two_equal_points_ask_for_no_camera() -> None:
    with pytest.raises(ValueError):
        look_at(_TARGET, _TARGET)


def test_transform_array_is_transform_all_to_the_last_bit() -> None:
    """The numpy transform does the same elementwise arithmetic in the same order, so the flyby's picture
    does not change when it replaces the scalar loop."""
    cam = orbit_camera((15.0, 26.0, 38.0), 300.0, 118.0, 0.7)
    rng = np.random.default_rng(85)
    pts = tuple(map(tuple, (rng.random((500, 3)) * 200.0 - 50.0).tolist()))
    assert transform_array(cam, np.array(pts)).tolist() == [list(p) for p in transform_all(cam, pts)]


def test_transform_array_keeps_the_shape_and_leaves_its_input_alone() -> None:
    cam = look_at((0.0, -100.0, 20.0), (0.0, 0.0, 20.0))
    pts = np.array([[0.0, 0.0, 20.0], [10.0, 5.0, 25.0]])
    before = pts.copy()
    out = transform_array(cam, pts)
    assert out.shape == (2, 3) and (pts == before).all()
    assert out[0].tolist() == pytest.approx([0.0, 0.0, 100.0])
