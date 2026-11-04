"""The Plant Hover Flyby as a function of time: ``build_flyby(t, wall, view)`` returns drawing operations.

Plant equipment modelled: none computed. The camera circles a wireframe of the HP loop of flow sheets
322-1 and 322-2 (see ``model3d.py``); the only motion on the pipes is a dot running along each in the
direction of its arrow. No process value is shown.
Reference documents: ``ureasim/data/intro_flyby.py`` and ``ureasim/data/intro_plant.py``.
Equations: the projection of ``camera.py``; the orbit is yaw = yaw_start + 2 pi wall / period, so the
camera turns once in ``ORBIT.period`` seconds at a constant rate.

Process utility
---------------
Behind the logo the operator sees the plant from the air: the camera descends to a hover, a scan ring
climbs the model and draws it on from the ground up, and then the camera keeps circling, a full 360
degrees every 32 seconds, for as long as the start button waits. The pipes are coloured by stream as on
the DCS screens and a dot runs along each in the direction of its arrow, so the order of the plant can be
followed by eye from the CO2 compressor and the NH3 pumps to the reactor, the stripper and the column.
Three details keep it honest and readable: the layout is labelled "not to scale", the dial's bearing is
the drawing's own (000 at the first frame), and the wireframe fades out of the rectangles that carry text.

``t`` is the scene clock (descent, scan, fade-in); ``wall`` is the unclamped clock that drives the orbit,
the bob and the flow dots, so the loop closes with no seam: every motion that uses ``wall`` has a period
that divides ``ORBIT.period``. This module imports nothing from Qt.

Frame cost (session 85, As-Built Part XCVII). The wireframe is some 2,000 edges that the camera moves
every frame, and moving them edge by edge in Python took more than the sixteen milliseconds a frame has.
``_wires`` therefore holds the topology in numpy arrays built once at import and does the clip, the
projection, the depth cue and the text-zone fade on whole arrays. Every step is elementwise and in the
order the scalar code had, so the picture is the same to the last bit: the tests keep the scalar
version as their reference and demand equality.
"""

from __future__ import annotations

import math

import numpy as np

from ureasim.data.intro import PALETTE
from ureasim.data.intro_flyby import CLEAR_ZONES, HUD, LOOK, ORBIT
from ureasim.data.intro_plant import STREAMS
from ureasim.hmi.intro.camera import Camera, orbit_camera, project, transform_array
from ureasim.hmi.intro.model3d import STREAM_KIND, Kind, build_plant
from ureasim.hmi.intro.ops import Circle, Lines, Op, Polygon, Rect, Text
from ureasim.hmi.intro.timeline import clamp01, ease_in_out_cubic, ease_out_cubic, lerp, window

PLANT = build_plant((ORBIT.target[0], ORBIT.target[1]))
_HEIGHTS = tuple(p[2] for p in PLANT.points)
_STREAM_COLOR = {int(STREAM_KIND[st.name]): st.color for st in STREAMS}
_INK = {
    int(Kind.GROUND): (PALETTE.slate, LOOK.width_ground, LOOK.alpha_ground),
    int(Kind.SHELL): (PALETTE.teal_deep, LOOK.width_shell, LOOK.alpha_shell),
    int(Kind.VALVE): (PALETTE.teal_deep, LOOK.width_valve, LOOK.alpha_valve),
    **{k: (c, LOOK.width_stream, LOOK.alpha_stream) for k, c in _STREAM_COLOR.items()},
}
_ZONES = tuple((z.x0, z.y0, z.x1, z.y1, z.floor, 1.0 / z.soft) for z in CLEAR_ZONES)
_ZONE_COLUMNS = tuple(np.array(column) for column in zip(*_ZONES))  # x0, y0, x1, y1, floor, inv; six each
_YAW0 = math.radians(ORBIT.yaw_start_deg)
_DEPTH_SPAN = LOOK.depth_far - LOOK.depth_near
_CULL = 60.0

# The mesh as arrays, built once: the vertices, each edge's two vertices and kind, and the height of each
# edge's two ends (for the scan). The alpha of each kind is looked up by the kind's value.
_POINTS = np.array(PLANT.points, dtype=float)
_EDGE_I = np.array([e[0] for e in PLANT.edges], dtype=np.intp)
_EDGE_J = np.array([e[1] for e in PLANT.edges], dtype=np.intp)
_EDGE_KIND = np.array([e[2] for e in PLANT.edges], dtype=np.intp)
_HEIGHT_I = _POINTS[_EDGE_I, 2]
_HEIGHT_J = _POINTS[_EDGE_J, 2]
_KIND_ALPHA = np.zeros(max(_INK) + 1)
for _k, _ink in _INK.items():
    _KIND_ALPHA[_k] = _ink[2]
_LEVEL_STRIDE = 1024  # a bucket's sort key is kind * stride + level; the level never reaches it


def orbit_state(t: float, wall: float) -> tuple[Camera, float]:
    """The camera and its yaw (radians) at scene time ``t`` and wall time ``wall``."""
    u = ease_out_cubic(window(t, *ORBIT.descent))
    radius = lerp(ORBIT.radius_start, ORBIT.radius_hover, u)
    height = lerp(ORBIT.height_start, ORBIT.height_hover, u) + u * ORBIT.bob_height * math.sin(2.0 * math.pi * wall / ORBIT.bob_period)
    yaw = _YAW0 + 2.0 * math.pi * wall / ORBIT.period
    return orbit_camera(ORBIT.target, radius, height, yaw), yaw


def bearing_deg(yaw: float) -> float:
    """The camera's bearing round the model in [0, 360): 0 at the first frame, rising with the orbit."""
    return math.degrees(yaw - _YAW0) % 360.0


def clear_factor(x: float, y: float) -> float:
    """How much of the wireframe survives at a screen point: 1 in the open, the zone's floor inside text."""
    m = 1.0
    for x0, y0, x1, y1, floor, inv in _ZONES:
        dx = x0 - x if x < x0 else (x - x1 if x > x1 else 0.0)
        dy = y0 - y if y < y0 else (y - y1 if y > y1 else 0.0)
        u = math.sqrt(dx * dx + dy * dy) * inv
        if u < 1.0:
            f = floor + (1.0 - floor) * u * u * (3.0 - 2.0 * u)
            if f < m:
                m = f
    return m


def clear_factors(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """``clear_factor`` of many screen points at once, step for step the same arithmetic.

    A point further than a zone's softness from the zone is 1 for that zone, so the formula is evaluated
    only for the points that some zone can reach, a small share of the wireframe."""
    m = np.ones_like(x)
    x0, y0, x1, y1, floor, inv = (column[:, None] for column in _ZONE_COLUMNS)
    soft = 1.0 / inv
    near = ((x > x0 - soft) & (x < x1 + soft) & (y > y0 - soft) & (y < y1 + soft)).any(axis=0)
    if not near.any():
        return m
    xs, ys = x[near], y[near]
    dx = np.where(xs < x0, x0 - xs, np.where(xs > x1, xs - x1, 0.0))
    dy = np.where(ys < y0, y0 - ys, np.where(ys > y1, ys - y1, 0.0))
    u = np.sqrt(dx * dx + dy * dy) * inv
    f = floor + (1.0 - floor) * u * u * (3.0 - 2.0 * u)
    m[near] = np.minimum(1.0, np.where(u < 1.0, f, 1.0).min(axis=0))
    return m


def _scan_height(t: float) -> float | None:
    """Height the scan has reached, or ``None`` once the whole model is drawn."""
    p = window(t, *ORBIT.scan)
    if p >= 1.0:
        return None
    return -1.0 + ease_in_out_cubic(p) * (ORBIT.scan_top + 2.0)


def _wires(cam: Camera, env: float, scan: float | None, view: Rect) -> list[Op]:
    """The wireframe, clipped to the scan height and the lens, inked by depth and by the text zones.

    One ``Lines`` operation per (kind, opacity level), in kind then level order, the segments of each in
    the order of the model's edges; the same operations the edge-by-edge version drew.

    Every step runs on the whole edge list and a mask says which edges still count; the edges are
    compressed once, at the end. The clip arithmetic runs only when some edge is actually cut. Rows that
    are masked out may hold inf or nan from a division by a depth behind the lens, which is why the
    floating-point warnings are off: nothing computed on them is ever read.
    """
    pts = transform_array(cam, _POINTS)
    a, b = pts[_EDGE_I], pts[_EDGE_J]
    keep = np.ones(len(a), dtype=bool)
    if scan is not None:
        above_a, above_b = _HEIGHT_I > scan, _HEIGHT_J > scan
        keep &= ~(above_a & above_b)
        cut = above_a ^ above_b                        # exactly one end is above the scan: shorten the edge
        if cut.any():
            u = (scan - _HEIGHT_I) / np.where(cut, _HEIGHT_J - _HEIGHT_I, 1.0)
            mix = a + (b - a) * u[:, None]
            a = np.where((cut & above_a)[:, None], mix, a)
            b = np.where((cut & above_b)[:, None], mix, b)
    near = ORBIT.near
    behind_a, behind_b = a[:, 2] < near, b[:, 2] < near
    keep &= ~(behind_a & behind_b)
    cut = behind_a ^ behind_b                          # exactly one end is behind the lens: shorten it
    if cut.any():
        u = (near - a[:, 2]) / np.where(cut, b[:, 2] - a[:, 2], 1.0)
        mix = a + (b - a) * u[:, None]
        mix[:, 2] = near
        a = np.where((cut & behind_a)[:, None], mix, a)
        b = np.where((cut & behind_b)[:, None], mix, b)
    focal = cam.focal
    left, right = view.x - _CULL, view.right + _CULL
    top, bottom = view.y - _CULL, view.bottom + _CULL
    steps = LOOK.alpha_steps
    with np.errstate(all="ignore"):
        x1, y1 = cam.cx + focal * a[:, 0] / a[:, 2], cam.cy - focal * a[:, 1] / a[:, 2]
        x2, y2 = cam.cx + focal * b[:, 0] / b[:, 2], cam.cy - focal * b[:, 1] / b[:, 2]
        out = ((x1 < left) & (x2 < left)) | ((x1 > right) & (x2 > right)) | ((y1 < top) & (y2 < top)) | ((y1 > bottom) & (y2 > bottom))
        keep &= ~out
        depth = (a[:, 2] + b[:, 2]) * 0.5
        cue = 1.0 - (1.0 - LOOK.depth_far_factor) * np.minimum(1.0, np.maximum(0.0, (depth - LOOK.depth_near) / _DEPTH_SPAN))
        ink = (_KIND_ALPHA * env)[_EDGE_KIND] * cue * clear_factors((x1 + x2) * 0.5, (y1 + y2) * 0.5) * steps + 0.5
        level = np.floor(np.where(keep, ink, 0.0)).astype(np.intp)
    lit = np.flatnonzero(level > 0)
    if not len(lit):
        return []
    kind, level = _EDGE_KIND[lit], level[lit]
    key = kind * _LEVEL_STRIDE + level
    order = np.argsort(key, kind="stable")             # stable: edge order kept inside a bucket
    key = key[order]
    rows = np.stack((x1[lit], y1[lit], x2[lit], y2[lit]), axis=1)[order].tolist()
    edges = np.flatnonzero(np.diff(key)) + 1
    ops: list[Op] = []
    for lo, hi in zip([0, *edges.tolist()], [*edges.tolist(), len(key)]):
        k, lv = divmod(int(key[lo]), _LEVEL_STRIDE)
        color, width, _ = _INK[k]
        ops.append(Lines(tuple(map(tuple, rows[lo:hi])), color, width, lv / steps))
    return ops


def _scan_ring(cam: Camera, t: float, scan: float | None) -> list[Op]:
    """The orange ring that climbs the model while it is drawn on; it fades out where text is laid."""
    if scan is None:
        return []
    p = window(t, *ORBIT.scan)
    fade = clamp01(p / 0.08) * clamp01((1.0 - p) / 0.15)
    if fade <= 0.0:
        return []
    tx, ty = ORBIT.target[0], ORBIT.target[1]
    pts: list[tuple[float, float] | None] = []
    for k in range(LOOK.scan_points + 1):
        a = 2.0 * math.pi * k / LOOK.scan_points
        s = project(cam, (tx + ORBIT.scan_radius * math.cos(a), ty + ORBIT.scan_radius * math.sin(a), max(scan, 0.0)))
        pts.append(None if s is None else (s[0], s[1]))
    steps = LOOK.alpha_steps
    buckets: dict[int, list[tuple[float, float, float, float]]] = {}
    for a, b in zip(pts, pts[1:]):
        if a is None or b is None:
            continue
        level = int(LOOK.scan_alpha * fade * clear_factor((a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5) * steps + 0.5)
        if level > 0:
            buckets.setdefault(level, []).append((a[0], a[1], b[0], b[1]))
    return [Lines(tuple(seg), PALETTE.orange, 1.8, level / steps) for level, seg in sorted(buckets.items())]


def _depth_scale(depth: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, LOOK.label_ref_depth / depth))


def _cue(depth: float) -> float:
    """Depth cueing: 1 near the lens, ``depth_far_factor`` far from it."""
    return 1.0 - (1.0 - LOOK.depth_far_factor) * clamp01((depth - LOOK.depth_near) / _DEPTH_SPAN)


def dot_distances(length: float, wall: float) -> list[float]:
    """Distances from the start of a pipe of ``length`` at which its flow dots are at ``wall``.

    The dots advance toward the pipe's end at about ``LOOK.pulse_speed``; the train makes a whole number
    of laps in one orbit period, so the loop closes with no seam.
    """
    cycles = max(1, round(ORBIT.period * LOOK.pulse_speed / length))
    count = max(1, round(length / LOOK.pulse_spacing))
    phase = (wall * cycles / ORBIT.period) % 1.0
    return [((phase + k / count) % 1.0) * length for k in range(count)]


def _dots(cam: Camera, wall: float, scan: float | None, env: float) -> list[Op]:
    """One flow dot train per pipe, running from the pipe's start to its end, the way its arrow points."""
    ops: list[Op] = []
    for path in PLANT.paths:
        length = path.length
        color = _STREAM_COLOR[path.kind]
        for s in dot_distances(length, wall):
            p = path.point_at(s)
            if scan is not None and p[2] > scan:
                continue
            q = project(cam, p)
            if q is None:
                continue
            ends = clamp01(s / 3.0) * clamp01((length - s) / 3.0)
            a = env * ends * _cue(q[2]) * clear_factor(q[0], q[1])
            if a > 0.02:
                ops.append(Circle(q[0], q[1], LOOK.pulse_radius_px * _depth_scale(q[2], 0.7, 1.3), color, min(1.0, a)))
    return ops


def _labels(cam: Camera, scan: float | None, env: float) -> list[Op]:
    """The tag of each equipment item and the name of each boundary, floating at their anchors.

    Where two tags would overprint, the farther one fades out (smoothly, so nothing pops), which keeps
    the nearest tag readable at every bearing of the orbit.
    """
    seen: list[tuple[float, float, float, str, bool]] = []
    for lab in PLANT.labels:
        if scan is not None and lab.point[2] > scan:
            continue
        q = project(cam, lab.point)
        if q is not None:
            seen.append((q[2], q[0], q[1], lab.text, lab.boundary))
    seen.sort()
    ops: list[Op] = []
    placed: list[tuple[float, float]] = []
    lo = LOOK.label_sep_from
    for depth, x, y, text, boundary in seen:
        a = env * clear_factor(x, y) * (0.55 + 0.45 * _cue(depth))
        for px, py in placed:
            d = math.hypot((x - px) / LOOK.label_sep_x, (y - py) / LOOK.label_sep_y)
            if d < 1.0:
                u = clamp01((d - lo) / (1.0 - lo))
                a *= u * u * (3.0 - 2.0 * u)
        if a <= 0.03:
            continue
        placed.append((x, y))
        size = (LOOK.boundary_size if boundary else LOOK.label_size) * _depth_scale(depth, LOOK.label_min_scale, LOOK.label_max_scale)
        color = PALETTE.slate if boundary else PALETTE.teal_deep
        ops.append(Text(x, y, text, size, color, min(1.0, a), "center", LOOK.label_spacing, not boundary))
    return ops


def _hud(t: float, yaw: float) -> list[Op]:
    """The caption at the top left and the bearing dial at the top right."""
    a = ease_out_cubic(window(t, *HUD.fade_in))
    if a <= 0.0:
        return []
    ops: list[Op] = [Text(HUD.caption_x, HUD.caption_y, HUD.caption, HUD.caption_size, PALETTE.teal_deep, a, "left", HUD.caption_spacing, True)]
    for i, line in enumerate(HUD.sub):
        ops.append(Text(HUD.caption_x, HUD.caption_y + HUD.sub_dy + i * HUD.sub_step, line, HUD.sub_size, PALETTE.slate, 0.85 * a, "left", HUD.sub_spacing))
    for i, st in enumerate(STREAMS):
        y = HUD.legend_y + i * HUD.legend_step
        ops.append(Lines(((HUD.legend_x, y, HUD.legend_x + HUD.legend_swatch, y),), st.color, 2.4, a))
        ops.append(Text(HUD.legend_x + HUD.legend_swatch + HUD.legend_gap, y, st.name.upper(), HUD.legend_size, PALETTE.slate, 0.9 * a, "left", HUD.legend_spacing))
    cx, cy, r = HUD.dial_x, HUD.dial_y, HUD.dial_r
    bearing = bearing_deg(yaw)
    ops.append(Circle(cx, cy, r, PALETTE.slate, 0.5 * a, width=1.2))
    minor: list[tuple[float, float, float, float]] = []
    major: list[tuple[float, float, float, float]] = []
    n = round(360.0 / HUD.dial_tick_deg)
    for k in range(n):
        ang = math.radians(k * HUD.dial_tick_deg - bearing)
        s, c = math.sin(ang), -math.cos(ang)
        is_major = k % HUD.dial_major_every == 0
        inner = r - (HUD.dial_major_len if is_major else HUD.dial_tick_len)
        (major if is_major else minor).append((cx + s * inner, cy + c * inner, cx + s * r, cy + c * r))
    ops.append(Lines(tuple(minor), PALETTE.slate, 1.0, 0.55 * a))
    ops.append(Lines(tuple(major), PALETTE.teal_deep, 1.4, 0.85 * a))
    ops.append(Polygon(((cx - 4.5, cy - r - 11.0), (cx + 4.5, cy - r - 11.0), (cx, cy - r - 2.5)), PALETTE.orange, a))
    ops.append(Text(cx, cy, f"{int(bearing):03d}°", HUD.dial_value_size, PALETTE.teal_deep, a, "center", 1.0, True))
    ops.append(Text(cx, cy + HUD.dial_label_dy, HUD.dial_label, HUD.dial_label_size, PALETTE.slate, 0.85 * a, "center", 3.0))
    return ops


def build_flyby(t: float, wall: float, view: Rect) -> list[Op]:
    """Every drawing operation of the flyby at scene time ``t`` and wall time ``wall``, back to front."""
    env = ease_out_cubic(window(t, *ORBIT.fade_in))
    if env <= 0.0:
        return []
    cam, yaw = orbit_state(t, wall)
    scan = _scan_height(t)
    ops = _wires(cam, env, scan, view)
    ops += _scan_ring(cam, t, scan)
    ops += _dots(cam, wall, scan, env)
    ops += _labels(cam, scan, env)
    ops += _hud(t, yaw)
    return ops
