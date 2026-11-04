"""Constants of the intro's Plant Hover Flyby: the orbit camera, the ink, the clear zones, the HUD.

Plant equipment modelled
------------------------
None here. The equipment, its tags and its connections are in ``intro_plant.py`` (read from the flow
sheets 322-1 and 322-2); this module holds how the flyby looks at them: the ring road and the ground
ring of the drawing, the camera's orbit and lens, how the wireframe is inked, which screen rectangles
the wireframe fades out of, and the caption, legend and bearing dial.

Reference documents
-------------------
* ``intro_plant.py`` and, through it, the flow sheets 322-1 and 322-2 supplied 2026-11-03.
* ``project.md`` section 3.4: the intro's design space is the 1366 x 720 stage of the DCS screens.

Equations
---------
None. The projection and the orbit are geometry (see ``hmi/intro/camera.py``). Everything below is a
design choice; each group names its ``source``. Lengths of the model are in model units (mu), a unit of
the drawing only; the camera turns once round the plant in ``Orbit.period`` seconds. Time is in seconds,
screen lengths in design pixels.
"""

from __future__ import annotations

from dataclasses import dataclass

Window = tuple[float, float]


@dataclass(frozen=True)
class Road:
    """The ring road: two kerb lines of a rounded rectangle."""

    x: float
    y: float
    half_w: float
    half_d: float
    corner: float
    width: float
    source: str = "design choice: a ring road round the drawing, not surveyed, not to scale"


@dataclass(frozen=True)
class Rose:
    """The ground ring with its bearing ticks, which makes the orbit readable against the ground."""

    radius: float
    tick_step_deg: float
    major_every: int
    tick_len: float
    major_len: float
    source: str = "design choice (a ring of bearing ticks, no plant datum)"


@dataclass(frozen=True)
class Orbit:
    """The hover camera: one steady turn round the plant, a descent in, and the lens."""

    period: float = 32.0
    yaw_start_deg: float = -105.0
    target: tuple[float, float, float] = (15.0, 26.0, 38.0)
    radius_start: float = 470.0
    radius_hover: float = 300.0
    height_start: float = 260.0
    height_hover: float = 118.0
    bob_height: float = 3.0
    bob_period: float = 8.0
    descent: Window = (0.0, 4.6)
    fade_in: Window = (0.0, 0.9)
    scan: Window = (0.25, 3.7)
    scan_top: float = 98.0
    scan_radius: float = 150.0
    fov_v_deg: float = 42.0
    centre: tuple[float, float] = (990.0, 300.0)
    near: float = 12.0
    source: str = (
        "design choice: 32 s a turn (11.25 degrees a second), starting a little to the left of the front "
        "view; bob_period divides the period, and so does every flow-dot cycle, so the loop closes with "
        "no seam"
    )


@dataclass(frozen=True)
class ClearZone:
    """A screen rectangle the wireframe fades out of, so the text laid over it stays legible."""

    name: str
    x0: float
    y0: float
    x1: float
    y1: float
    floor: float
    soft: float
    source: str = "design choice: the rectangles the logo, titles, button, ribbon, caption, legend and dial occupy"


@dataclass(frozen=True)
class Look:
    """How the wireframe is inked: opacity and width per kind of line, depth cueing, flow dots, labels."""

    alpha_shell: float = 0.62
    alpha_stream: float = 0.95
    alpha_valve: float = 1.0
    alpha_ground: float = 0.50
    width_shell: float = 1.0
    width_stream: float = 2.0
    width_valve: float = 1.7
    width_ground: float = 1.1
    depth_near: float = 120.0
    depth_far: float = 380.0
    depth_far_factor: float = 0.42
    alpha_steps: int = 16
    max_segment: float = 12.0
    valve_half_length: float = 2.4
    valve_half_width: float = 1.8
    valve_stem: float = 3.6
    arrow_length: float = 3.2
    arrow_half_width: float = 1.4
    pulse_speed: float = 14.0
    pulse_spacing: float = 16.0
    pulse_radius_px: float = 2.6
    label_size: float = 11.0
    label_ref_depth: float = 240.0
    label_min_scale: float = 0.78
    label_max_scale: float = 1.25
    label_spacing: float = 1.5
    boundary_size: float = 9.0
    label_sep_x: float = 56.0
    label_sep_y: float = 13.0
    label_sep_from: float = 0.6
    scan_alpha: float = 0.85
    scan_points: int = 48
    source: str = "design choice (legibility over the paper, no plant datum)"


@dataclass(frozen=True)
class Hud:
    """The caption and legend at the top left and the bearing dial at the top right."""

    caption_x: float = 640.0
    caption_y: float = 40.0
    caption_size: float = 12.0
    caption_spacing: float = 3.0
    sub_dy: float = 18.0
    sub_step: float = 14.0
    sub_size: float = 10.0
    sub_spacing: float = 2.0
    legend_x: float = 1196.0
    legend_y: float = 478.0
    legend_step: float = 16.0
    legend_swatch: float = 22.0
    legend_gap: float = 10.0
    legend_size: float = 10.0
    legend_spacing: float = 2.0
    dial_x: float = 1290.0
    dial_y: float = 74.0
    dial_r: float = 30.0
    dial_tick_deg: float = 10.0
    dial_major_every: int = 3
    dial_tick_len: float = 4.0
    dial_major_len: float = 8.0
    dial_value_size: float = 14.0
    dial_label_dy: float = 48.0
    dial_label_size: float = 9.0
    fade_in: Window = (3.2, 4.2)
    caption: str = "PLANT HOVER FLYBY"
    sub: tuple[str, ...] = ("360° ORBIT  ·  HP LOOP, FLOW SHEETS 322-1 / 322-2", "STYLIZED LAYOUT, NOT TO SCALE")
    dial_label: str = "VIEW"
    source: str = (
        "design choice; the dial shows the camera's bearing round the model, 000 at the first frame's "
        "viewpoint. It is a bearing of the drawing, not a compass heading of the site"
    )


ORBIT = Orbit()
LOOK = Look()
HUD = Hud()

CLEAR_ZONES: tuple[ClearZone, ...] = (
    ClearZone("text column", 56.0, 56.0, 604.0, 566.0, 0.10, 44.0),
    ClearZone("ribbon", 70.0, 586.0, 1296.0, 672.0, 0.04, 30.0),
    ClearZone("footer", 0.0, 680.0, 1366.0, 720.0, 0.0, 20.0),
    ClearZone("caption", 626.0, 22.0, 1060.0, 96.0, 0.0, 26.0),
    ClearZone("dial", 1240.0, 28.0, 1342.0, 140.0, 0.0, 30.0),
    ClearZone("legend", 1176.0, 464.0, 1330.0, 548.0, 0.0, 24.0),
)

ROAD = Road(15.0, 25.0, 140.0, 98.0, 28.0, 7.0)
ROSE = Rose(175.0, 5.0, 6, 3.0, 7.0)
