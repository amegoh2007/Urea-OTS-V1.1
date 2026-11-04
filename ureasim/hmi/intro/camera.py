"""Orbit camera of the Plant Hover Flyby: a look-at perspective projection, display-free.

Plant equipment modelled: none (presentation only).
Reference document: ``ureasim/data/intro_flyby.py`` (the orbit and the lens).
Equations: with the eye at ``E``, the target at ``T``, world up ``k`` = (0, 0, 1)

    forward f = (T - E) / |T - E|,   right r = (f x k) / |f x k|,   up u = r x f
    camera space of a point P:  (xc, yc, zc) = ((P - E).r, (P - E).u, (P - E).f)
    screen:  sx = cx + F xc / zc,   sy = cy - F yc / zc,   F = (H / 2) / tan(fov_v / 2)

where H is the stage height and (cx, cy) the screen point the target lands on.

Process utility
---------------
The flyby shows the plant from a camera that hovers and circles it. The projection is the one piece of
geometry the picture rests on; keeping it here, pure and tested, means a wrong sign or a swapped axis
shows up as a failing test rather than as a plant that appears to turn the wrong way round.
This module imports nothing from Qt. ``transform_array`` is the same transform on a numpy array: the
flyby moves some 1,700 points a frame, which in plain Python costs more than the frame's whole budget.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ureasim.data.intro import STAGE
from ureasim.data.intro_flyby import ORBIT

Vec3 = tuple[float, float, float]

_UP: Vec3 = (0.0, 0.0, 1.0)


def _sub(a: Vec3, b: Vec3) -> Vec3:
    return a[0] - b[0], a[1] - b[1], a[2] - b[2]


def _dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]


def _unit(a: Vec3) -> Vec3:
    n = math.sqrt(_dot(a, a))
    if n == 0.0:
        raise ValueError("a camera needs a distance between its eye and its target")
    return a[0] / n, a[1] / n, a[2] / n


FOCAL = (STAGE.height / 2.0) / math.tan(math.radians(ORBIT.fov_v_deg) / 2.0)


@dataclass(frozen=True, slots=True)
class Camera:
    """A pinhole camera: eye, orthonormal basis, focal length in design pixels, screen centre."""

    eye: Vec3
    right: Vec3
    up: Vec3
    forward: Vec3
    focal: float
    cx: float
    cy: float


def look_at(eye: Vec3, target: Vec3, *, focal: float = FOCAL, centre: tuple[float, float] = ORBIT.centre) -> Camera:
    """A camera at ``eye`` that holds ``target`` at the screen point ``centre``."""
    forward = _unit(_sub(target, eye))
    right = _unit(_cross(forward, _UP))
    up = _cross(right, forward)
    return Camera(eye, right, up, forward, focal, centre[0], centre[1])


def orbit_camera(target: Vec3, radius: float, height: float, yaw: float) -> Camera:
    """The camera on a circle of ``radius`` round ``target`` at world height ``height``.

    ``yaw`` is the camera's azimuth from the +x axis, counter-clockwise seen from above, in radians.
    """
    eye = (target[0] + radius * math.cos(yaw), target[1] + radius * math.sin(yaw), height)
    return look_at(eye, target)


def to_camera(cam: Camera, p: Vec3) -> Vec3:
    """A world point in camera space (x right, y up, z along the view direction)."""
    v = _sub(p, cam.eye)
    return _dot(v, cam.right), _dot(v, cam.up), _dot(v, cam.forward)


def project(cam: Camera, p: Vec3, near: float = ORBIT.near) -> tuple[float, float, float] | None:
    """A world point as ``(sx, sy, depth)`` on the stage, or ``None`` when it is not in front of the lens."""
    xc, yc, zc = to_camera(cam, p)
    if zc < near:
        return None
    return cam.cx + cam.focal * xc / zc, cam.cy - cam.focal * yc / zc, zc


def transform_all(cam: Camera, points: tuple[Vec3, ...]) -> list[Vec3]:
    """Camera-space coordinates of many world points (the per-frame hot path of the wireframe)."""
    ex, ey, ez = cam.eye
    rx, ry, rz = cam.right
    ux, uy, uz = cam.up
    fx, fy, fz = cam.forward
    out: list[Vec3] = []
    append = out.append
    for x, y, z in points:
        dx, dy, dz = x - ex, y - ey, z - ez
        append((dx * rx + dy * ry + dz * rz, dx * ux + dy * uy + dz * uz, dx * fx + dy * fy + dz * fz))
    return out


def transform_array(cam: Camera, points: np.ndarray) -> np.ndarray:
    """Camera-space coordinates of an (N, 3) array of world points, as ``transform_all`` gives them.

    The arithmetic is elementwise and in the same order as ``transform_all`` (no matrix product, whose
    summation order may differ), so the two agree to the last bit.
    """
    dx = points[:, 0] - cam.eye[0]
    dy = points[:, 1] - cam.eye[1]
    dz = points[:, 2] - cam.eye[2]
    out = np.empty_like(points)
    out[:, 0] = dx * cam.right[0] + dy * cam.right[1] + dz * cam.right[2]
    out[:, 1] = dx * cam.up[0] + dy * cam.up[1] + dz * cam.up[2]
    out[:, 2] = dx * cam.forward[0] + dy * cam.forward[1] + dz * cam.forward[2]
    return out
