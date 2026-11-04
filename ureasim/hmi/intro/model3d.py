"""The plant of the Plant Hover Flyby as a wireframe: equipment, pipes, valves, labels. Display-free.

Plant equipment modelled: none computed. The model draws the HP loop of flow sheets 322-1 and 322-2
(see ``ureasim/data/intro_plant.py``): its equipment, the pipes between them in the order the sheets
draw them, and the tagged valves on the pipes. The layout is a design choice, not to scale.
Reference document: ``ureasim/data/intro_plant.py``.
Equations: none beyond circles, ellipses and straight lines in model units (x right, y back, z up).

Process utility
---------------
The operator meets the plant first as a picture, and the picture must not mislead about what is joined
to what. Every pipe here is built from the data table that the tests compare with the flow sheets, from
a port on the equipment its line leaves to a port on the equipment its arrow enters, with an arrowhead
at the end and the flow direction kept in its path so the flyby can run dots along it the right way.
The mesh is built once; a frame of the flyby only moves the camera over it. No Qt.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import IntEnum

from ureasim.data.intro_flyby import LOOK, ROAD, ROSE, Road, Rose
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
    Block,
    Drum,
    Pipe,
    PumpPair,
    Scrubber,
    Valve,
    Vessel,
)

Vec3 = tuple[float, float, float]
Edge = tuple[int, int, int]  # vertex, vertex, Kind


class Kind(IntEnum):
    """What an edge is; the value is also the drawing order: ground, shells, streams, valves."""

    GROUND = 0
    SHELL = 1
    GAS = 2
    LIQUID = 3
    STEAM = 4
    WATER = 5
    VALVE = 6


STREAM_KIND = {"gas": Kind.GAS, "liquid": Kind.LIQUID, "steam": Kind.STEAM, "water": Kind.WATER}


@dataclass(frozen=True, slots=True)
class PipePath:
    """The centre line of one pipe, from where the flow leaves to where it enters."""

    name: str
    kind: int
    points: tuple[Vec3, ...]
    cumulative: tuple[float, ...]

    @property
    def length(self) -> float:
        return self.cumulative[-1]

    def point_at(self, s: float) -> Vec3:
        """The point ``s`` along the path from its start (clamped to the ends)."""
        s = min(max(s, 0.0), self.length)
        for i in range(1, len(self.points)):
            if s <= self.cumulative[i]:
                span = self.cumulative[i] - self.cumulative[i - 1]
                u = (s - self.cumulative[i - 1]) / span if span > 0.0 else 0.0
                a, b = self.points[i - 1], self.points[i]
                return a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u
        return self.points[-1]


@dataclass(frozen=True, slots=True)
class Label:
    """A tag floating at a point of the model."""

    text: str
    point: Vec3
    boundary: bool = False


@dataclass(frozen=True, slots=True)
class Plant:
    """Shared vertices and edges, the pipe paths the flow runs along, and the labels."""

    points: tuple[Vec3, ...]
    edges: tuple[Edge, ...]
    paths: tuple[PipePath, ...]
    labels: tuple[Label, ...]

    @property
    def top(self) -> float:
        """Height of the highest vertex."""
        return max(p[2] for p in self.points)


class _Builder:
    """Collects edges, welds equal vertices and cuts long segments so the fade can follow the screen."""

    def __init__(self, max_segment: float) -> None:
        self._max = max_segment
        self.points: list[Vec3] = []
        self._index: dict[Vec3, int] = {}
        self.edges: list[Edge] = []

    def _vertex(self, p: Vec3) -> int:
        key = (round(p[0], 4), round(p[1], 4), round(p[2], 4))
        i = self._index.get(key)
        if i is None:
            i = len(self.points)
            self._index[key] = i
            self.points.append(key)
        return i

    def segment(self, a: Vec3, b: Vec3, kind: Kind) -> None:
        length = math.dist(a, b)
        if length < 1e-9:
            return
        parts = max(1, math.ceil(length / self._max))
        prev = self._vertex(a)
        for k in range(1, parts + 1):
            u = k / parts
            nxt = self._vertex((a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u))
            if nxt != prev:
                self.edges.append((prev, nxt, int(kind)))
            prev = nxt

    def path(self, pts: Sequence[Vec3], kind: Kind, *, closed: bool = False) -> None:
        for a, b in zip(pts, pts[1:]):
            self.segment(a, b, kind)
        if closed and len(pts) > 2:
            self.segment(pts[-1], pts[0], kind)


def _ring(x: float, y: float, z: float, r: float, n: int) -> list[Vec3]:
    return [(x + r * math.cos(2.0 * math.pi * k / n), y + r * math.sin(2.0 * math.pi * k / n), z) for k in range(n)]


def _vessel(b: _Builder, v: Vessel) -> None:
    levels = [0.0] + [v.height * (i + 1) / (v.rings + 1) for i in range(v.rings)] + [v.height]
    for z in levels:
        b.path(_ring(v.x, v.y, z, v.radius, v.sides), Kind.SHELL, closed=True)
    caps = (30.0, 60.0)
    for deg in caps:
        phi = math.radians(deg)
        b.path(_ring(v.x, v.y, v.height + v.dome * math.sin(phi), v.radius * math.cos(phi), v.sides), Kind.SHELL, closed=True)
    for k in range(0, v.sides, 2):
        a = 2.0 * math.pi * k / v.sides
        c, s = math.cos(a), math.sin(a)
        line: list[Vec3] = [(v.x + v.radius * c, v.y + v.radius * s, 0.0), (v.x + v.radius * c, v.y + v.radius * s, v.height)]
        for deg in caps:
            phi = math.radians(deg)
            r = v.radius * math.cos(phi)
            line.append((v.x + r * c, v.y + r * s, v.height + v.dome * math.sin(phi)))
        line.append((v.x, v.y, v.height + v.dome))
        b.path(line, Kind.SHELL)


def _scrubber(b: _Builder, s: Scrubber) -> None:
    """A shaft carrying a wide domed head; the head is a spheroid whose lowest ring sits on the shaft top."""
    shaft_sides, dome_sides = 12, 16
    for z in (0.0, s.shaft_height / 2.0, s.shaft_height):
        b.path(_ring(s.x, s.y, z, s.shaft_radius, shaft_sides), Kind.SHELL, closed=True)
    for k in range(0, shaft_sides, 2):
        a = 2.0 * math.pi * k / shaft_sides
        b.segment(
            (s.x + s.shaft_radius * math.cos(a), s.y + s.shaft_radius * math.sin(a), 0.0),
            (s.x + s.shaft_radius * math.cos(a), s.y + s.shaft_radius * math.sin(a), s.shaft_height),
            Kind.SHELL,
        )
    centre = s.shaft_height + s.dome_height * math.sin(math.radians(60.0))
    phis = (-60.0, -30.0, 0.0, 30.0, 60.0)
    for deg in phis:
        phi = math.radians(deg)
        b.path(_ring(s.x, s.y, centre + s.dome_height * math.sin(phi), s.dome_radius * math.cos(phi), dome_sides), Kind.SHELL, closed=True)
    for k in range(0, dome_sides, 2):
        a = 2.0 * math.pi * k / dome_sides
        c, sn = math.cos(a), math.sin(a)
        line = [(s.x + s.dome_radius * math.cos(math.radians(d)) * c, s.y + s.dome_radius * math.cos(math.radians(d)) * sn, centre + s.dome_height * math.sin(math.radians(d))) for d in phis]
        line.append((s.x, s.y, centre + s.dome_height))
        b.path(line, Kind.SHELL)


def _drum(b: _Builder, d: Drum) -> None:
    """A horizontal cylinder along x with rings, longitudinal lines and, if it floats, two legs."""
    x0, x1 = d.x - d.length / 2.0, d.x + d.length / 2.0
    xs = [x0 + d.length * i / (d.rings + 1) for i in range(d.rings + 2)]
    for x in xs:
        b.path([(x, d.y + d.radius * math.cos(2.0 * math.pi * k / d.sides), d.z + d.radius * math.sin(2.0 * math.pi * k / d.sides)) for k in range(d.sides)], Kind.SHELL, closed=True)
    for k in range(0, d.sides, 2):
        a = 2.0 * math.pi * k / d.sides
        y, z = d.y + d.radius * math.cos(a), d.z + d.radius * math.sin(a)
        b.segment((x0, y, z), (x1, y, z), Kind.SHELL)
    if d.radius >= 3.0:
        for x in (x0 + d.length * 0.1, x1 - d.length * 0.1):
            b.segment((x, d.y, 0.0), (x, d.y, d.z - d.radius), Kind.SHELL)


def _box_loop(x: float, y: float, w: float, dd: float, z: float) -> list[Vec3]:
    return [(x - w / 2.0, y - dd / 2.0, z), (x + w / 2.0, y - dd / 2.0, z), (x + w / 2.0, y + dd / 2.0, z), (x - w / 2.0, y + dd / 2.0, z)]


def _block(b: _Builder, k: Block) -> None:
    base, roof = _box_loop(k.x, k.y, k.w, k.d, 0.0), _box_loop(k.x, k.y, k.w, k.d, k.h)
    b.path(base, Kind.SHELL, closed=True)
    b.path(roof, Kind.SHELL, closed=True)
    for p, q in zip(base, roof):
        b.segment(p, q, Kind.SHELL)
    for i in range(1, k.bands + 1):
        b.path(_box_loop(k.x, k.y, k.w, k.d, k.h * i / (k.bands + 1)), Kind.SHELL, closed=True)
    for i in range(4):
        p0, p1 = base[i], base[(i + 1) % 4]
        for n in range(1, k.bays):
            u = n / k.bays
            x, y = p0[0] + (p1[0] - p0[0]) * u, p0[1] + (p1[1] - p0[1]) * u
            b.segment((x, y, 0.0), (x, y, k.h), Kind.SHELL)


def _pump_levels(p: PumpPair) -> tuple[float, float]:
    """Height of the casing centre and of the common discharge line."""
    centre = p.casing_radius + 0.5
    return centre, centre + p.casing_radius + p.lift


def _pump_ports(p: PumpPair) -> dict[str, Vec3]:
    centre, top = _pump_levels(p)
    return {
        f"{p.tag}.suction": (p.x - p.casing_radius - p.stub, p.y, centre),
        f"{p.tag}.discharge": (p.x, p.y, top),
    }


def _pumps(b: _Builder, p: PumpPair) -> None:
    """Two pumps, each a casing ring and a motor, branching from one suction and one discharge point."""
    centre, top = _pump_levels(p)
    kind = STREAM_KIND[p.stream]
    sx = p.x - p.casing_radius - p.stub
    ys = (p.y - p.spacing / 2.0, p.y + p.spacing / 2.0)
    for y in ys:
        b.path([(p.x, y + p.casing_radius * math.cos(2.0 * math.pi * k / 16), centre + p.casing_radius * math.sin(2.0 * math.pi * k / 16)) for k in range(16)], Kind.SHELL, closed=True)
        for x in (p.x + 1.0, p.x + 1.0 + p.motor_length):
            b.path([(x, y + p.motor_radius * math.cos(2.0 * math.pi * k / 8), centre + p.motor_radius * math.sin(2.0 * math.pi * k / 8)) for k in range(8)], Kind.SHELL, closed=True)
        for k in range(0, 8, 2):
            a = 2.0 * math.pi * k / 8
            yy, zz = y + p.motor_radius * math.cos(a), centre + p.motor_radius * math.sin(a)
            b.segment((p.x + 1.0, yy, zz), (p.x + 1.0 + p.motor_length, yy, zz), Kind.SHELL)
        b.segment((p.x - p.casing_radius, y, centre), (sx, y, centre), kind)
        b.segment((p.x, y, centre + p.casing_radius), (p.x, y, top), kind)
    b.segment((sx, ys[0], centre), (sx, ys[1], centre), kind)
    b.segment((p.x, ys[0], top), (p.x, ys[1], top), kind)


def resolve_ports() -> dict[str, Vec3]:
    """Every nozzle of the model by key ``"TAG.port"``: the data table plus the pump pairs' common points."""
    ports: dict[str, Vec3] = dict(PORTS)
    for p in PUMPS:
        ports.update(_pump_ports(p))
    return ports


def _unit(a: Vec3) -> Vec3:
    n = math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2)
    return a[0] / n, a[1] / n, a[2] / n


def _frame_of(d: Vec3) -> tuple[Vec3, Vec3]:
    """A stem direction and a side direction, both across the pipe direction ``d``: the stem is up, or +x on a riser."""
    stem: Vec3 = (0.0, 0.0, 1.0) if abs(d[2]) < 0.9 else (1.0, 0.0, 0.0)
    side = _unit((d[1] * stem[2] - d[2] * stem[1], d[2] * stem[0] - d[0] * stem[2], d[0] * stem[1] - d[1] * stem[0]))
    return stem, side


def _add(a: Vec3, d: Vec3, s: float) -> Vec3:
    return a[0] + d[0] * s, a[1] + d[1] * s, a[2] + d[2] * s


def _valve(b: _Builder, a: Vec3, c: Vec3, v: Valve) -> None:
    """A bow-tie across the pipe at the middle of the segment a-c; a control valve also gets a stem and a T."""
    d = _unit((c[0] - a[0], c[1] - a[1], c[2] - a[2]))
    mid = ((a[0] + c[0]) / 2.0, (a[1] + c[1]) / 2.0, (a[2] + c[2]) / 2.0)
    stem, side = _frame_of(d)
    ln, w = LOOK.valve_half_length, LOOK.valve_half_width
    for sign in (-1.0, 1.0):
        base = _add(mid, d, sign * ln)
        p1, p2 = _add(base, side, w), _add(base, side, -w)
        b.path([p1, p2], Kind.VALVE)
        b.segment(p1, mid, Kind.VALVE)
        b.segment(p2, mid, Kind.VALVE)
    if v.control:
        top = _add(mid, stem, LOOK.valve_stem)
        b.segment(mid, top, Kind.VALVE)
        b.segment(_add(top, side, -1.3), _add(top, side, 1.3), Kind.VALVE)


def _arrowhead(b: _Builder, tip: Vec3, before: Vec3, kind: Kind) -> None:
    """Two short lines back from the pipe's last point: the arrow of the flow sheet."""
    d = _unit((tip[0] - before[0], tip[1] - before[1], tip[2] - before[2]))
    _, side = _frame_of(d)
    back = _add(tip, d, -LOOK.arrow_length)
    b.segment(_add(back, side, LOOK.arrow_half_width), tip, kind)
    b.segment(_add(back, side, -LOOK.arrow_half_width), tip, kind)


def pipe_points(pipe: Pipe, ports: dict[str, Vec3]) -> tuple[Vec3, ...]:
    """The pipe's centre line: its start, its bends, its end."""
    start = ports[pipe.start] if isinstance(pipe.start, str) else pipe.start
    end = ports[pipe.end] if isinstance(pipe.end, str) else pipe.end
    return (start, *pipe.via, end)


def _pipe(b: _Builder, pipe: Pipe, pts: tuple[Vec3, ...]) -> PipePath:
    kind = STREAM_KIND[pipe.stream]
    b.path(pts, kind)
    _arrowhead(b, pts[-1], pts[-2], kind)
    for v in pipe.valves:
        _valve(b, pts[v.segment], pts[v.segment + 1], v)
    cumulative = [0.0]
    for p, q in zip(pts, pts[1:]):
        cumulative.append(cumulative[-1] + math.dist(p, q))
    return PipePath(pipe.name, int(kind), pts, tuple(cumulative))


def _rounded_rect(x: float, y: float, hw: float, hd: float, corner: float, per_corner: int = 6) -> list[Vec3]:
    pts: list[Vec3] = []
    for (sx, sy), start in (((1, 1), 0.0), ((-1, 1), 90.0), ((-1, -1), 180.0), ((1, -1), 270.0)):
        cx, cy = x + sx * (hw - corner), y + sy * (hd - corner)
        for i in range(per_corner + 1):
            a = math.radians(start + 90.0 * i / per_corner)
            pts.append((cx + corner * math.cos(a), cy + corner * math.sin(a), 0.0))
    return pts


def _road(b: _Builder, r: Road) -> None:
    for grow in (-r.width / 2.0, r.width / 2.0):
        b.path(_rounded_rect(r.x, r.y, r.half_w + grow, r.half_d + grow, r.corner + grow), Kind.GROUND, closed=True)


def _rose(b: _Builder, r: Rose, centre_xy: tuple[float, float]) -> None:
    x, y = centre_xy
    b.path(_ring(x, y, 0.0, r.radius, 72), Kind.GROUND, closed=True)
    n = round(360.0 / r.tick_step_deg)
    for k in range(n):
        a = 2.0 * math.pi * k / n
        c, s = math.cos(a), math.sin(a)
        length = r.major_len if k % r.major_every == 0 else r.tick_len
        b.segment((x + r.radius * c, y + r.radius * s, 0.0), (x + (r.radius + length) * c, y + (r.radius + length) * s, 0.0), Kind.GROUND)


def _labels() -> tuple[Label, ...]:
    tagged = [REACTOR, SCRUBBER, *VESSELS, *DRUMS, *BLOCKS, *PUMPS]
    out = [Label(e.tag, e.label) for e in tagged]
    out += [Label(bd.name, (bd.at[0], bd.at[1], bd.at[2] + 5.0), True) for bd in BOUNDARIES]
    return tuple(out)


def build_plant(centre_xy: tuple[float, float] = (0.0, 0.0)) -> Plant:
    """The whole model: ground ring centred on ``centre_xy``, every equipment item, every pipe."""
    b = _Builder(LOOK.max_segment)
    _rose(b, ROSE, centre_xy)
    _road(b, ROAD)
    _vessel(b, REACTOR)
    for v in VESSELS:
        _vessel(b, v)
    _scrubber(b, SCRUBBER)
    for d in DRUMS:
        _drum(b, d)
    for k in BLOCKS:
        _block(b, k)
    for p in PUMPS:
        _pumps(b, p)
    ports = resolve_ports()
    paths = tuple(_pipe(b, pipe, pipe_points(pipe, ports)) for pipe in PIPES)
    return Plant(tuple(b.points), tuple(b.edges), paths, _labels())
