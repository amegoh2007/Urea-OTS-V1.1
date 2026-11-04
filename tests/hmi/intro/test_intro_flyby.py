"""Tests of ureasim/hmi/intro/flyby.py: the orbit, the scan, the flow dots, the clear zones, the HUD.

All display-free: ``build_flyby`` returns plain operations, so the loop, the legibility and the camera's
clearance are checked as numbers.
"""

from __future__ import annotations

import dataclasses
import math
import time

import numpy as np
import pytest

from ureasim.data.intro import STAGE, TITLE
from ureasim.data.intro_flyby import CLEAR_ZONES, HUD, LOOK, ORBIT
from ureasim.hmi.intro import flyby
from ureasim.hmi.intro.camera import Camera, look_at, orbit_camera, project, transform_all
from ureasim.hmi.intro.flyby import PLANT, bearing_deg, build_flyby, clear_factor, dot_distances, orbit_state
from ureasim.hmi.intro.model3d import Kind
from ureasim.hmi.intro.ops import Circle, Lines, Op, Polygon, Rect, Text
from ureasim.hmi.intro.scene import view_rect as flyby_view

VIEW = Rect(0.0, 0.0, STAGE.width, STAGE.height)
_HOVER = 10.0  # a scene time after the descent, the scan and the HUD fade-in are all over


def _flat(ops) -> list:
    """Every number and string of a frame, in order, so two frames can be compared."""
    out: list = []

    def walk(x) -> None:
        if isinstance(x, (tuple, list)):
            for y in x:
                walk(y)
        else:
            out.append(x)

    for op in ops:
        out.append(type(op).__name__)
        walk(dataclasses.astuple(op))
    return out


def _same(a, b) -> bool:
    if len(a) != len(b):
        return False
    return all(x == pytest.approx(y, abs=1e-6) if isinstance(x, float) else x == y for x, y in zip(a, b))


# --- the frame ----------------------------------------------------------------------------------


def test_nothing_is_drawn_before_the_fade_in_starts() -> None:
    assert build_flyby(0.0, 0.0, VIEW) == []
    assert build_flyby(-1.0, 5.0, VIEW) == []


def test_a_frame_is_finite_and_small_at_every_stage_of_the_intro() -> None:
    for t in (0.6, 1.0, 2.0, 3.0, 3.9, 4.5, 6.0, _HOVER):
        for wall in (0.0, 1.7, 9.3, 31.9, 77.0):
            ops = build_flyby(t, wall, VIEW)
            assert 0 < len(ops) < 400
            for op in ops:
                assert 0.0 <= op.alpha <= 1.0
            assert all(math.isfinite(v) for v in _flat(ops) if isinstance(v, float))


def test_the_wireframe_is_batched_into_a_few_quantised_inks() -> None:
    allowed = {k / LOOK.alpha_steps for k in range(1, LOOK.alpha_steps + 1)}
    cam, _ = orbit_state(_HOVER, 7.0)
    wires = flyby._wires(cam, 1.0, None, VIEW)
    assert wires and all(isinstance(op, Lines) for op in wires)
    assert {op.alpha for op in wires} <= allowed
    assert len(wires) <= len(Kind) * LOOK.alpha_steps
    assert sum(len(op.segments) for op in wires) > 1000


def test_the_first_instant_of_the_scan_has_nothing_to_draw_and_the_frame_is_empty_not_broken() -> None:
    assert build_flyby(ORBIT.scan[0] - 0.05, 0.0, VIEW) == []


def test_the_hud_comes_in_after_the_model_not_with_it() -> None:
    def texts(t: float) -> list[str]:
        return [op.text for op in build_flyby(t, 0.0, VIEW) if isinstance(op, Text)]

    assert HUD.caption not in texts(ORBIT.fade_in[1] + 0.5)
    assert HUD.caption not in texts(HUD.fade_in[0] - 0.05)
    assert HUD.caption in texts(HUD.fade_in[1] + 0.1)
    assert all(line in texts(_HOVER) for line in HUD.sub)
    assert f"{int(bearing_deg(orbit_state(_HOVER, 0.0)[1])):03d}°" in texts(_HOVER)


def test_the_equipment_tags_of_the_slides_are_the_labels_the_orbit_shows() -> None:
    shown = {op.text for op in build_flyby(_HOVER, 3.0, VIEW) if isinstance(op, Text)}
    tags = {lab.text for lab in PLANT.labels if not lab.boundary}
    # at a given bearing some labels sit inside a clear zone and fade out; over a turn each is seen
    seen: set[str] = set()
    for k in range(64):
        seen |= {op.text for op in build_flyby(_HOVER, k * 0.5, VIEW) if isinstance(op, Text)}
    assert tags <= seen
    assert shown  # and the frame at one bearing is never bare


# --- the orbit ----------------------------------------------------------------------------------


def test_the_yaw_turns_once_round_per_period_at_a_constant_rate() -> None:
    rate = 2.0 * math.pi / ORBIT.period
    for wall in (0.0, 3.0, 12.5, 40.0):
        y0 = orbit_state(_HOVER, wall)[1]
        assert orbit_state(_HOVER, wall + 1.0)[1] - y0 == pytest.approx(rate)
        assert orbit_state(_HOVER, wall + ORBIT.period)[1] - y0 == pytest.approx(2.0 * math.pi)


def test_the_orbit_follows_the_wall_clock_and_the_descent_follows_the_scene_clock() -> None:
    assert orbit_state(1.0, 10.0)[1] == pytest.approx(orbit_state(8.0, 10.0)[1])
    cam0, _ = orbit_state(0.0, 0.0)
    cam1, _ = orbit_state(ORBIT.descent[1], 0.0)
    r0 = math.hypot(cam0.eye[0] - ORBIT.target[0], cam0.eye[1] - ORBIT.target[1])
    r1 = math.hypot(cam1.eye[0] - ORBIT.target[0], cam1.eye[1] - ORBIT.target[1])
    assert r0 == pytest.approx(ORBIT.radius_start) and cam0.eye[2] == pytest.approx(ORBIT.height_start)
    assert r1 == pytest.approx(ORBIT.radius_hover)
    assert cam1.eye[2] == pytest.approx(ORBIT.height_hover, abs=1e-9)  # wall 0: the bob is at zero
    for wall in (0.0, 2.0, 6.0, 11.0):
        cam, _ = orbit_state(_HOVER, wall)
        assert abs(cam.eye[2] - ORBIT.height_hover) <= ORBIT.bob_height + 1e-9


def test_the_bearing_is_zero_at_the_first_frame_and_rises_one_turn_per_period() -> None:
    assert bearing_deg(orbit_state(_HOVER, 0.0)[1]) == pytest.approx(0.0, abs=1e-9)
    assert bearing_deg(orbit_state(_HOVER, ORBIT.period / 4.0)[1]) == pytest.approx(90.0)
    assert bearing_deg(orbit_state(_HOVER, ORBIT.period * 0.99)[1]) == pytest.approx(356.4)
    assert 0.0 <= bearing_deg(orbit_state(_HOVER, ORBIT.period * 3.3)[1]) < 360.0


def test_the_target_stays_at_the_clear_screen_point_through_the_whole_orbit() -> None:
    for t in (0.0, 2.0, _HOVER):
        for k in range(0, 64):
            cam, _ = orbit_state(t, k * 0.5)
            sx, sy, _ = project(cam, ORBIT.target)
            assert (sx, sy) == pytest.approx(ORBIT.centre)
    assert clear_factor(*ORBIT.centre) == pytest.approx(1.0)


def test_the_camera_never_comes_near_the_model_or_inside_it() -> None:
    nearest = math.inf
    for t in (0.0, 1.0, 2.5, ORBIT.descent[1], _HOVER):
        for k in range(0, 64):
            eye = orbit_state(t, k * 0.5)[0].eye
            nearest = min(nearest, min(math.dist(eye, p) for p in PLANT.points))
    assert nearest > 100.0  # far enough that no edge is cut by the near plane or fills the screen


def test_the_equipment_stays_on_the_stage_at_every_bearing() -> None:
    solid = {i for i, j, k in PLANT.edges if k != int(Kind.GROUND) for i in (i, j)}
    for k in range(0, 64):
        cam, _ = orbit_state(_HOVER, k * 0.5)
        on = 0
        for i in solid:
            s = project(cam, PLANT.points[i])
            on += s is not None and 0.0 <= s[0] <= STAGE.width and 0.0 <= s[1] <= STAGE.height
        assert on / len(solid) > 0.9, f"bearing {bearing_deg(orbit_state(_HOVER, k * 0.5)[1]):.0f}"


# --- the loop closes ----------------------------------------------------------------------------


@pytest.mark.parametrize("wall", [0.0, 2.3, 7.7, 19.0, 31.0])
def test_the_picture_after_one_period_is_the_picture_before_it(wall: float) -> None:
    a = _flat(build_flyby(_HOVER, wall, VIEW))
    b = _flat(build_flyby(_HOVER, wall + ORBIT.period, VIEW))
    assert _same(a, b), "the orbit, the bob or a flow-dot train does not close in one period"
    c = _flat(build_flyby(_HOVER, wall + 5 * ORBIT.period, VIEW))
    assert _same(a, c)


def test_the_picture_moves_between_two_instants_of_a_period() -> None:
    assert not _same(_flat(build_flyby(_HOVER, 0.0, VIEW)), _flat(build_flyby(_HOVER, 4.0, VIEW)))


def test_the_orbit_does_not_depend_on_the_scene_clock_once_the_scan_is_over() -> None:
    a = _flat([op for op in build_flyby(8.0, 6.0, VIEW) if not isinstance(op, Text)])
    b = _flat([op for op in build_flyby(30.0, 6.0, VIEW) if not isinstance(op, Text)])
    assert _same(a, b)


# --- the flow dots ------------------------------------------------------------------------------


def test_every_dot_train_is_evenly_spaced_inside_its_pipe() -> None:
    for path in PLANT.paths:
        d = sorted(dot_distances(path.length, 5.3))
        assert all(0.0 <= s < path.length for s in d)
        gaps = [b - a for a, b in zip(d, d[1:])] + [d[0] + path.length - d[-1]] if len(d) > 1 else [path.length]
        assert max(gaps) == pytest.approx(min(gaps))
        assert gaps[0] == pytest.approx(path.length / len(d))
        assert 0.6 * LOOK.pulse_spacing < gaps[0] < 1.6 * LOOK.pulse_spacing or len(d) == 1


def test_the_dots_run_from_the_start_of_a_pipe_toward_its_arrow() -> None:
    dt = 0.05
    for path in PLANT.paths:
        before = dot_distances(path.length, 3.0)
        after = dot_distances(path.length, 3.0 + dt)
        step = [(b - a) % path.length for a, b in zip(before, after)]
        assert all(s > 0.0 for s in step)
        assert all(s < path.length / 2.0 for s in step), f"{path.name}: the dots run backwards"
        speed = step[0] / dt
        assert 0.8 * LOOK.pulse_speed < speed < 1.2 * LOOK.pulse_speed, f"{path.name}: {speed:.1f} mu/s"


def test_every_dot_train_comes_back_to_itself_in_one_period() -> None:
    for path in PLANT.paths:
        a = sorted(dot_distances(path.length, 4.1))
        b = sorted(dot_distances(path.length, 4.1 + ORBIT.period))
        assert a == pytest.approx(b)


def test_a_dot_is_drawn_on_the_pipe_it_belongs_to_and_in_the_colour_of_its_stream() -> None:
    cam, _ = orbit_state(_HOVER, 5.0)
    dots = [op for op in flyby._dots(cam, 5.0, None, 1.0)]
    assert dots and all(isinstance(op, Circle) for op in dots)
    colours = {st.color for st in flyby.STREAMS}
    assert {op.color for op in dots} <= colours
    assert len({op.color for op in dots}) == len(colours)  # all four streams carry dots


# --- the scan -----------------------------------------------------------------------------------


def test_the_scan_has_drawn_the_whole_model_by_the_time_it_ends() -> None:
    assert ORBIT.scan_top >= PLANT.top
    assert flyby._scan_height(ORBIT.scan[0]) == pytest.approx(-1.0)
    assert flyby._scan_height(ORBIT.scan[1]) is None
    assert flyby._scan_height(ORBIT.scan[1] + 5.0) is None
    heights = [flyby._scan_height(ORBIT.scan[0] + (ORBIT.scan[1] - ORBIT.scan[0]) * k / 40.0) for k in range(40)]
    assert all(b > a for a, b in zip(heights, heights[1:]))
    assert heights[-1] > 0.8 * PLANT.top


def test_the_scan_draws_the_model_on_from_the_ground_up() -> None:
    cam, _ = orbit_state(_HOVER, 0.0)

    def segments(scan) -> int:
        return sum(len(op.segments) for op in flyby._wires(cam, 1.0, scan, VIEW))

    assert segments(-1.0) == 0
    counts = [segments(h) for h in range(0, int(PLANT.top) + 4, 6)]
    assert all(b >= a for a, b in zip(counts, counts[1:])), counts
    assert counts[0] < counts[-1] // 4 and counts[-1] > 500
    assert _flat(flyby._wires(cam, 1.0, 10_000.0, VIEW)) == _flat(flyby._wires(cam, 1.0, None, VIEW))


def test_the_scan_ring_exists_only_while_the_model_is_being_drawn() -> None:
    cam, _ = orbit_state(2.0, 0.0)
    mid = (ORBIT.scan[0] + ORBIT.scan[1]) / 2.0
    ring = flyby._scan_ring(cam, mid, flyby._scan_height(mid))
    assert ring and all(isinstance(op, Lines) for op in ring)
    assert sum(len(op.segments) for op in ring) >= 20
    assert flyby._scan_ring(cam, ORBIT.scan[1] + 1.0, None) == []


def test_the_scan_ring_fades_out_where_text_is_laid() -> None:
    zone = next(z for z in CLEAR_ZONES if z.name == "text column")
    for k in range(0, 40, 3):
        tt = ORBIT.scan[0] + (ORBIT.scan[1] - ORBIT.scan[0]) * (0.2 + 0.6 * k / 40.0)
        for op in flyby._scan_ring(orbit_state(tt, tt)[0], tt, flyby._scan_height(tt)):
            for x1, y1, x2, y2 in op.segments:
                mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
                if zone.x0 + 20 < mx < zone.x1 - 20 and zone.y0 + 20 < my < zone.y1 - 20:
                    assert op.alpha <= zone.floor + 1.0 / LOOK.alpha_steps


# --- the text stays readable --------------------------------------------------------------------


# A point just past each zone's soft edge on the side that faces open stage (the footer's falloff is
# inside the ribbon's, so it has no open side of its own).
_OPEN_SIDE = {
    "text column": lambda z: (z.x1 + z.soft + 1.0, (z.y0 + z.y1) / 2.0),
    "ribbon": lambda z: (700.0, z.y0 - z.soft - 1.0),
    "caption": lambda z: ((z.x0 + z.x1) / 2.0, z.y1 + z.soft + 1.0),
    "dial": lambda z: (z.x0 - z.soft - 1.0, (z.y0 + z.y1) / 2.0),
    "legend": lambda z: (z.x0 - z.soft - 1.0, (z.y0 + z.y1) / 2.0),
}


def test_the_wireframe_fades_out_inside_each_zone_that_carries_text_and_is_full_in_the_open() -> None:
    for z in CLEAR_ZONES:
        assert clear_factor((z.x0 + z.x1) / 2.0, (z.y0 + z.y1) / 2.0) <= z.floor + 1e-9, z.name
        assert clear_factor(z.x0 + 1.0, z.y0 + 1.0) <= z.floor + 1e-9, z.name
        if z.name in _OPEN_SIDE:
            assert clear_factor(*_OPEN_SIDE[z.name](z)) == 1.0, z.name
    assert {z.name for z in CLEAR_ZONES} - {"footer"} == set(_OPEN_SIDE)
    assert clear_factor(*ORBIT.centre) == 1.0
    assert clear_factor(1000.0, 300.0) == 1.0


def test_the_fade_out_is_gradual_not_a_hard_edge() -> None:
    z = next(z for z in CLEAR_ZONES if z.name == "text column")
    y = (z.y0 + z.y1) / 2.0
    run = [clear_factor(z.x1 + z.soft * k / 10.0, y) for k in range(11)]
    assert run[0] == pytest.approx(z.floor) and run[-1] == pytest.approx(1.0)
    assert all(b >= a - 1e-12 for a, b in zip(run, run[1:]))
    assert max(b - a for a, b in zip(run, run[1:])) < 0.25  # no step bigger than a quarter of the ink


def test_no_wireframe_ink_is_strong_inside_the_text_column() -> None:
    zone = next(z for z in CLEAR_ZONES if z.name == "text column")
    for k in range(0, 64, 4):
        cam, _ = orbit_state(_HOVER, k * 0.5)
        for op in flyby._wires(cam, 1.0, None, VIEW):
            for x1, y1, x2, y2 in op.segments:
                mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
                if zone.x0 + 20 < mx < zone.x1 - 20 and zone.y0 + 20 < my < zone.y1 - 20:
                    assert op.alpha <= zone.floor + 1e-9


def test_the_text_column_clear_zone_is_centred_on_the_title_column() -> None:
    zone = next(z for z in CLEAR_ZONES if z.name == "text column")
    assert (zone.x0 + zone.x1) / 2.0 == pytest.approx(TITLE.cx)
    assert zone.x1 - zone.x0 > 2.0 * TITLE.divider_half_width  # wider than the widest rule under the title


def test_the_model_sits_right_of_the_text_column_and_clear_of_its_fade() -> None:
    zone = next(z for z in CLEAR_ZONES if z.name == "text column")
    assert ORBIT.centre[0] > STAGE.width / 2.0
    assert ORBIT.centre[0] > zone.x1 + zone.soft


def test_two_tags_never_overprint_at_any_bearing() -> None:
    tags = {lab.text for lab in PLANT.labels}
    for k in range(64):
        shown = [op for op in build_flyby(_HOVER, k * 0.5, VIEW) if isinstance(op, Text) and op.text in tags and op.alpha >= 0.5]
        for i, a in enumerate(shown):
            for b in shown[i + 1 :]:
                assert not (abs(a.x - b.x) < 30.0 and abs(a.y - b.y) < 7.0), (k, a.text, b.text)


def test_the_nearest_tag_is_always_kept() -> None:
    cam, _ = orbit_state(_HOVER, 12.0)
    ops = flyby._labels(cam, None, 1.0)
    nearest = min((lab for lab in PLANT.labels), key=lambda lab: project(cam, lab.point)[2] if project(cam, lab.point) else 1e9)
    q = project(cam, nearest.point)
    mine = [op for op in ops if op.text == nearest.text]
    # unless it sits inside a clear zone, the nearest tag is drawn at full strength
    if clear_factor(q[0], q[1]) == 1.0:
        assert mine and mine[0].alpha > 0.5


# --- cost ---------------------------------------------------------------------------------------


def test_a_frame_is_cheap_enough_for_a_30_fps_timer() -> None:
    best = math.inf
    for k in range(30):
        t0 = time.perf_counter()
        build_flyby(_HOVER, k * 0.3, VIEW)
        best = min(best, time.perf_counter() - t0)
    assert best < 0.030  # the intro ticks every TICK_MS; measured ~4 ms, a generous 30 ms bound here


def test_the_only_polygon_of_a_frame_is_the_dial_pointer() -> None:
    polys = [op for op in build_flyby(_HOVER, 0.0, VIEW) if isinstance(op, Polygon)]
    assert len(polys) == 1
    xs = [p[0] for p in polys[0].points]
    assert abs((min(xs) + max(xs)) / 2.0 - HUD.dial_x) < 1e-9


# -- the numpy wireframe against its scalar reference (session 85, handoff A-25 point 1) -----------------------
#
# ``flyby._wires`` does the clip, the projection, the depth cue and the text-zone fade on whole arrays. The
# edge-by-edge version it replaced is kept here, word for word, as the reference, and the two must give the
# very same operations: same buckets, same order, same segments, to the last bit.

def _wires_scalar(cam: Camera, env: float, scan: float | None, view: Rect) -> list[Op]:
    """The wireframe, clipped to the scan height and the lens, inked by depth and by the text zones."""
    pts = transform_all(cam, PLANT.points)
    heights = flyby._HEIGHTS
    cx, cy, focal, near = cam.cx, cam.cy, cam.focal, ORBIT.near
    steps = LOOK.alpha_steps
    far_gain = 1.0 - LOOK.depth_far_factor
    left, right = view.x - flyby._CULL, view.right + flyby._CULL
    top, bottom = view.y - flyby._CULL, view.bottom + flyby._CULL
    base = {k: ink[2] * env for k, ink in flyby._INK.items()}
    buckets: dict[tuple[int, int], list[tuple[float, float, float, float]]] = {}
    for i, j, kind in PLANT.edges:
        a, b = pts[i], pts[j]
        if scan is not None:
            za, zb = heights[i], heights[j]
            if za > scan and zb > scan:
                continue
            if za > scan or zb > scan:
                u = (scan - za) / (zb - za)
                mix = (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u)
                if za > scan:
                    a = mix
                else:
                    b = mix
        if a[2] < near or b[2] < near:
            if a[2] < near and b[2] < near:
                continue
            u = (near - a[2]) / (b[2] - a[2])
            mix = (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, near)
            if a[2] < near:
                a = mix
            else:
                b = mix
        x1, y1 = cx + focal * a[0] / a[2], cy - focal * a[1] / a[2]
        x2, y2 = cx + focal * b[0] / b[2], cy - focal * b[1] / b[2]
        if (x1 < left and x2 < left) or (x1 > right and x2 > right) or (y1 < top and y2 < top) or (y1 > bottom and y2 > bottom):
            continue
        depth = (a[2] + b[2]) * 0.5
        cue = 1.0 - far_gain * min(1.0, max(0.0, (depth - LOOK.depth_near) / flyby._DEPTH_SPAN))
        level = int(base[kind] * cue * clear_factor((x1 + x2) * 0.5, (y1 + y2) * 0.5) * steps + 0.5)
        if level > 0:
            buckets.setdefault((kind, level), []).append((x1, y1, x2, y2))
    ops: list[Op] = []
    for (kind, level), segments in sorted(buckets.items()):
        color, width, _ = flyby._INK[kind]
        ops.append(Lines(tuple(segments), color, width, level / steps))
    return ops


def _same_wires(cam, env, scan, view) -> None:
    assert flyby._wires(cam, env, scan, view) == _wires_scalar(cam, env, scan, view)


def test_the_numpy_wireframe_is_the_scalar_one_to_the_last_bit_over_the_whole_scene() -> None:
    """From the first scan frames through the hold, at three window shapes."""
    for view in (flyby_view(1366.0, 720.0), flyby_view(1100.0, 700.0), flyby_view(1920.0, 1012.0)):
        for k in range(120):
            t, wall = k / 7.0, k / 7.0 + 3.3
            cam, _ = orbit_state(t, wall)
            _same_wires(cam, 1.0, flyby._scan_height(t), view)
        for k in range(40):
            cam, _ = orbit_state(10.0, 10.0 + k * 0.81)
            _same_wires(cam, 1.0, None, view)


@pytest.mark.parametrize("env", [0.0, 0.05, 0.5, 1.0])
def test_the_numpy_wireframe_agrees_while_the_flyby_fades_in(env: float) -> None:
    cam, _ = orbit_state(0.4, 0.4)
    _same_wires(cam, env, None, VIEW)
    _same_wires(cam, env, 40.0, VIEW)


def test_the_numpy_wireframe_agrees_when_the_lens_cuts_edges() -> None:
    """A camera inside the model has edges behind the lens: the near-plane clip must agree too."""
    for yaw in (0.0, 1.1, 2.3, 4.0):
        cam = orbit_camera(ORBIT.target, 45.0, 60.0, yaw)
        _same_wires(cam, 1.0, None, VIEW)
        _same_wires(cam, 1.0, 55.0, VIEW)


def test_the_numpy_wireframe_agrees_when_an_edge_straddles_the_lens() -> None:
    """A camera at the middle of the longest level edge, looking along it: that edge has one end in front of the
    lens and one behind, so the near-plane clip must shorten it exactly as the scalar code does (and not drop it)."""
    level = [e for e in PLANT.edges if abs(PLANT.points[e[0]][2] - PLANT.points[e[1]][2]) < 1e-9]
    i, j, _ = max(level, key=lambda e: math.dist(PLANT.points[e[0]], PLANT.points[e[1]]))
    a, b = PLANT.points[i], PLANT.points[j]
    length = math.dist(a, b)
    direction = tuple((q - p) / length for p, q in zip(a, b))
    eye = tuple((p + q) / 2.0 for p, q in zip(a, b))
    eye = (eye[0], eye[1], eye[2] + 3.0)
    cam = look_at(eye, tuple(e + 100.0 * d for e, d in zip(eye, direction)))
    depths = transform_all(cam, PLANT.points)
    straddlers = [e for e in PLANT.edges if (depths[e[0]][2] < ORBIT.near) != (depths[e[1]][2] < ORBIT.near)]
    assert len(straddlers) >= 1, "the camera was meant to put at least one edge across the lens"
    _same_wires(cam, 1.0, None, VIEW)
    _same_wires(cam, 1.0, 60.0, VIEW)
    # and the cut edge is really drawn, not dropped: a segment of the stream or shell ink reaches the screen
    assert sum(len(op.segments) for op in flyby._wires(cam, 1.0, None, VIEW)) > 0


def test_the_numpy_wireframe_agrees_when_everything_is_scanned_away_or_behind() -> None:
    cam, _ = orbit_state(10.0, 10.0)
    _same_wires(cam, 1.0, -50.0, VIEW)  # the scan is below the ground: nothing is drawn
    assert flyby._wires(cam, 1.0, -50.0, VIEW) == []


def test_clear_factors_is_clear_factor_for_every_point_to_the_last_bit() -> None:
    rng = np.random.default_rng(85)
    x, y = rng.random(4000) * 1500.0 - 60.0, rng.random(4000) * 800.0 - 40.0
    assert flyby.clear_factors(x, y).tolist() == [clear_factor(a, b) for a, b in zip(x.tolist(), y.tolist())]
    assert flyby.clear_factors(np.array([1000.0]), np.array([300.0])).tolist() == [1.0]
