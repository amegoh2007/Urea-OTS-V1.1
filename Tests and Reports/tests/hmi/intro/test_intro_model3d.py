"""Tests of ``ureasim/hmi/intro/model3d.py``: the wireframe built from the tables of ``data/intro_plant.py``:
what each pipe joins and in which direction, the valves on it, and the geometry that makes each connection
real (nozzles on the surface, no pipe through other equipment, nothing below the ground).

The expected tables are written out from the two slides (flow sheets 322-1 and 322-2); they are deliberately
not computed from the data they check. The data tables themselves are tested in
``tests/data/test_intro_plant.py``.
"""

from __future__ import annotations

import math

import pytest

from ureasim.data.intro_flyby import LOOK, ORBIT, ROSE
from ureasim.data.intro_plant import (
    BLOCKS,
    BOUNDARIES,
    DRUMS,
    PIPES,
    PORTS,
    PUMPS,
    REACTOR,
    SCRUBBER,
    VESSELS,
)
from ureasim.hmi.intro import model3d
from ureasim.hmi.intro.model3d import (
    Kind,
    build_plant,
    pipe_points,
    resolve_ports,
)

_EQUIPMENT_ON_THE_SLIDES = {
    "322R001", "322E001", "322E002", "322E003", "322F001", "322D001", "322C001", "323C003", "320K002",
    "321P002A/B", "323P001A/B", "329P006A/B", "329E004",
}  # fmt: skip


_BOUNDARY_NAMES = {"EXTR STEAM", "CONDENSATE", "VENT"}


def _equipment():
    return [REACTOR, SCRUBBER, *VESSELS, *DRUMS, *BLOCKS, *PUMPS]


def _on_path(points, q, tol: float = 0.01) -> bool:
    for a, b in zip(points, points[1:]):
        ab = [b[i] - a[i] for i in range(3)]
        aq = [q[i] - a[i] for i in range(3)]
        n2 = sum(c * c for c in ab)
        u = max(0.0, min(1.0, sum(x * y for x, y in zip(ab, aq)) / n2)) if n2 else 0.0
        if math.dist(q, [a[i] + ab[i] * u for i in range(3)]) <= tol:
            return True
    return False


def _dome_z(ro: float, r: float, top: float, rise: float) -> float:
    return top + rise * math.sqrt(max(0.0, 1.0 - (ro / r) ** 2))


def _gap(tag: str, p) -> float:
    """Distance from a point to the surface of the item with this tag (approximate, exact on the nozzles)."""
    for e in [REACTOR, *VESSELS]:
        if e.tag == tag:
            ro = math.hypot(p[0] - e.x, p[1] - e.y)
            if p[2] <= e.height + 1e-9:
                return abs(ro - e.radius) if p[2] >= 0.0 else math.inf
            return abs(p[2] - _dome_z(ro, e.radius, e.height, e.dome)) if ro <= e.radius else math.inf
    if tag == SCRUBBER.tag:
        s = SCRUBBER
        ro = math.hypot(p[0] - s.x, p[1] - s.y)
        centre = s.shaft_height + s.dome_height * math.sin(math.radians(60.0))
        f = math.sqrt((ro / s.dome_radius) ** 2 + ((p[2] - centre) / s.dome_height) ** 2)
        head = abs(f - 1.0) * s.dome_height if p[2] >= s.shaft_height - 1e-9 else math.inf
        shaft = abs(ro - s.shaft_radius) if 0.0 <= p[2] <= s.shaft_height else math.inf
        return min(head, shaft)
    for d in DRUMS:
        if d.tag == tag:
            ro = math.hypot(p[1] - d.y, p[2] - d.z)
            along = abs(p[0] - d.x)
            side = abs(ro - d.radius) if along <= d.length / 2.0 + 1e-9 else math.inf
            end = abs(along - d.length / 2.0) if ro <= d.radius + 1e-9 else math.inf
            return min(side, end)
    for k in BLOCKS:
        if k.tag == tag:
            dx, dy = abs(p[0] - k.x) - k.w / 2.0, abs(p[1] - k.y) - k.d / 2.0
            inside_xy = dx <= 1e-9 and dy <= 1e-9 and 0.0 <= p[2] <= k.h
            return min(abs(dx), abs(dy)) if inside_xy else math.inf
    raise AssertionError(tag)


def _inside(e, p, shrink: float) -> bool:
    """Deep inside the solid of ``e`` (shrunk by ``shrink`` so a pipe running along a shell is not a hit)."""
    if e in [REACTOR, *VESSELS]:
        ro = math.hypot(p[0] - e.x, p[1] - e.y)
        if 0.0 <= p[2] <= e.height:
            return ro < e.radius - shrink
        return p[2] > e.height and ro <= e.radius - shrink and p[2] < _dome_z(ro, e.radius, e.height, e.dome) - shrink
    if e is SCRUBBER:
        ro = math.hypot(p[0] - e.x, p[1] - e.y)
        if 0.0 <= p[2] <= e.shaft_height and ro < e.shaft_radius - shrink:
            return True
        centre = e.shaft_height + e.dome_height * math.sin(math.radians(60.0))
        return p[2] >= e.shaft_height and (ro / (e.dome_radius - shrink)) ** 2 + ((p[2] - centre) / (e.dome_height - shrink)) ** 2 < 1.0
    if e in DRUMS:
        return abs(p[0] - e.x) < e.length / 2.0 - shrink and math.hypot(p[1] - e.y, p[2] - e.z) < e.radius - shrink
    if e in BLOCKS:
        return abs(p[0] - e.x) < e.w / 2.0 - shrink and abs(p[1] - e.y) < e.d / 2.0 - shrink and 0.0 < p[2] < e.h - shrink
    pp = e  # a pump pair: its bounding box
    centre, top = model3d._pump_levels(pp)
    return (
        pp.x - pp.casing_radius - pp.stub < p[0] < pp.x + 1.0 + pp.motor_length
        and pp.y - pp.spacing / 2.0 - pp.casing_radius < p[1] < pp.y + pp.spacing / 2.0 + pp.casing_radius
        and 0.0 < p[2] < centre + pp.casing_radius - shrink
    )


def test_every_item_has_a_label_and_every_boundary_has_one() -> None:
    labels = {lab.text: lab for lab in build_plant().labels}
    assert set(labels) == _EQUIPMENT_ON_THE_SLIDES | _BOUNDARY_NAMES
    assert {n for n, lab in labels.items() if lab.boundary} == _BOUNDARY_NAMES
    assert {b.name for b in BOUNDARIES} == _BOUNDARY_NAMES


def test_a_valve_fits_on_the_straight_leg_it_sits_on() -> None:
    ports = resolve_ports()
    for p in PIPES:
        pts = pipe_points(p, ports)
        for v in p.valves:
            assert 0 <= v.segment < len(pts) - 1
            assert math.dist(pts[v.segment], pts[v.segment + 1]) >= 2.0 * LOOK.valve_half_length + 3.0, v.tag


def test_every_pipe_starts_and_ends_on_a_nozzle_or_a_declared_point() -> None:
    ports = resolve_ports()
    bounds = {f"@{b.name}": b.at for b in BOUNDARIES}
    paths = {p.name: pipe_points(p, ports) for p in PIPES}
    for p in PIPES:
        for end, ref, tag in ((paths[p.name][0], p.start, p.src), (paths[p.name][-1], p.end, p.dst)):
            if isinstance(ref, str):
                assert ref in ports, ref
                assert ref.split(".")[0] == tag, (p.name, ref, tag)
            elif tag.startswith("@"):
                assert end == bounds[tag], (p.name, tag)
            else:
                # a tee: the point lies on another pipe that carries the same flow
                hosts = [q for q in PIPES if q is not p and _on_path(paths[q.name], end)]
                assert hosts, (p.name, end)
                host = hosts[0]
                assert (host.src == tag) if ref is p.start else (host.dst == tag), (p.name, host.name)
                assert host.stream == p.stream


def test_every_leg_runs_along_one_axis_and_has_length() -> None:
    ports = resolve_ports()
    for p in PIPES:
        pts = pipe_points(p, ports)
        assert len(pts) >= 2
        for a, b in zip(pts, pts[1:]):
            moved = [i for i in range(3) if abs(a[i] - b[i]) > 1e-6]
            assert len(moved) == 1, (p.name, a, b)


def test_no_two_pipes_run_on_top_of_each_other() -> None:
    ports = resolve_ports()
    legs = []
    for p in PIPES:
        pts = pipe_points(p, ports)
        for a, b in zip(pts, pts[1:]):
            axis = next(i for i in range(3) if abs(a[i] - b[i]) > 1e-6)
            other = tuple(round(a[i], 2) for i in range(3) if i != axis)
            legs.append((p.name, axis, other, min(a[axis], b[axis]), max(a[axis], b[axis])))
    for i, (n1, ax1, o1, lo1, hi1) in enumerate(legs):
        for n2, ax2, o2, lo2, hi2 in legs[i + 1 :]:
            if n1 != n2 and ax1 == ax2 and all(abs(x - y) < 0.1 for x, y in zip(o1, o2)):
                assert min(hi1, hi2) - max(lo1, lo2) < 0.5, (n1, n2)


def test_every_nozzle_lies_on_the_surface_of_its_equipment() -> None:
    for key, p in PORTS.items():
        tag = key.split(".")[0]
        assert _gap(tag, p) <= 0.6, (key, p, _gap(tag, p))
    for pp in PUMPS:
        assert f"{pp.tag}.suction" in resolve_ports() and f"{pp.tag}.discharge" in resolve_ports()


def test_every_equipment_item_has_at_least_one_nozzle_or_is_a_pump_pair() -> None:
    ported = {k.split(".")[0] for k in resolve_ports()}
    assert ported == _EQUIPMENT_ON_THE_SLIDES


def test_no_pipe_passes_through_equipment_it_is_not_connected_to() -> None:
    ports = resolve_ports()
    for p in PIPES:
        pts = pipe_points(p, ports)
        for a, b in zip(pts, pts[1:]):
            n = max(2, int(math.dist(a, b) / 0.5))
            for k in range(n + 1):
                q = tuple(a[i] + (b[i] - a[i]) * k / n for i in range(3))
                for e in _equipment():
                    if e.tag in (p.src, p.dst):
                        continue
                    assert not _inside(e, q, 0.3), (p.name, e.tag, q)


def test_nothing_goes_below_the_ground() -> None:
    plant = build_plant()
    assert min(pt[2] for pt in plant.points) >= -1e-9


def test_the_mesh_carries_every_kind_and_every_pipe_has_a_path() -> None:
    plant = build_plant((ORBIT.target[0], ORBIT.target[1]))
    kinds = {e[2] for e in plant.edges}
    assert kinds == {int(k) for k in Kind}
    assert len(plant.paths) == len(PIPES)
    for e in plant.edges:
        assert 0 <= e[0] < len(plant.points) and 0 <= e[1] < len(plant.points) and e[0] != e[1]


def test_pipe_paths_run_from_the_start_to_the_end_in_the_arrow_direction() -> None:
    ports = resolve_ports()
    plant = build_plant()
    for p, path in zip(PIPES, plant.paths):
        pts = pipe_points(p, ports)
        assert path.name == p.name
        assert path.point_at(0.0) == pytest.approx(pts[0]) and path.point_at(path.length) == pytest.approx(pts[-1])
        assert path.point_at(path.length * 0.5) != pytest.approx(pts[0])
        assert list(path.cumulative) == sorted(path.cumulative) and path.length > 0.0
        # the arrow of the sheet: its last two edges end at the pipe's last point
        tip = tuple(round(c, 4) for c in pts[-1])
        assert tip in set(plant.points)


def test_the_model_fits_inside_the_orbit_and_the_scan() -> None:
    plant = build_plant((ORBIT.target[0], ORBIT.target[1]))
    assert plant.top < ORBIT.scan_top
    tx, ty = ORBIT.target[0], ORBIT.target[1]
    inner = [pt for pt, in ((pt,) for pt in plant.points) if pt[2] > 0.1]  # everything above the ground
    assert max(math.hypot(pt[0] - tx, pt[1] - ty) for pt in inner) < ROSE.radius


def test_the_orbit_target_is_the_middle_of_the_equipment() -> None:
    """The camera circles the equipment, not the ring road: the target is the middle of its plan and half its height."""
    plant = build_plant()
    used = {i for e in plant.edges if e[2] != int(Kind.GROUND) for i in e[:2]}
    xs = [plant.points[i][0] for i in used]
    ys = [plant.points[i][1] for i in used]
    assert (min(xs) + max(xs)) / 2.0 == pytest.approx(ORBIT.target[0], abs=8.0)
    assert (min(ys) + max(ys)) / 2.0 == pytest.approx(ORBIT.target[1], abs=8.0)
    assert ORBIT.target[2] == pytest.approx(plant.top / 2.0, abs=8.0)
