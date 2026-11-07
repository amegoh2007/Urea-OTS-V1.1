"""The start-up intro as a function of time: ``build_frame(t, view)`` returns the drawing operations.

Plant equipment modelled: none computed. The Plant Hover Flyby (``flyby.py``) pictures a stylized
plant and the ribbon names the six plant sections the console carries.
Reference documents: ``ureasim/data/intro.py`` (project.md sections 1 and 3.4; hfc-logo.png) and
``ureasim/data/intro_flyby.py`` (the plant photograph).
Equations: none beyond the easing curves of ``timeline.py``.

Process utility
---------------
The operator's first sight of the simulator. The company mark arrives over a wireframe flyby of the
plant that never stops circling, the simulator's name settles under it, and a ribbon of the plant
sections lights in the order the console's tab bar first reaches them (NH3 pumping, synthesis, steam and
utilities, LP recirculation, desorption, evaporation). The intro states no plant
condition: it never shows a value, a status tick or a "connected" word that the engine did not send,
and the only live text is the status line the application itself passes in.

The scene ends on a row of start buttons: "100% LOAD", the plant from its 1750 MTPD design seed, and
"LOAD", the plant from a saved exercise the operator chooses. Nothing leaves the screen until the
operator presses one: the intro is the doorway to the simulator, not a film that runs into it. The
buttons' geometry and hit test live here, next to the pixels they are drawn on, so a click and a
drawing can never disagree.

The frame is pure data (see ``ops.py``). ``t`` is the scene clock, held at ``TIMELINE.hold`` once the
scene is complete; ``wall`` is the unclamped clock that keeps the idle motion (the flyby's orbit, flow particles, the
status pulse, the button's breathing ring) alive while the operator decides.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from enum import Enum, auto
from functools import lru_cache

from ureasim.data.intro import (
    BUTTON,
    GRID_MAJOR_EVERY,
    GRID_MINOR,
    LOGO,
    PALETTE,
    RIBBON,
    SECTIONS,
    START_OPTION,
    START_OPTIONS,
    STAGE,
    STRINGS,
    TIMELINE,
    TITLE,
    Region,
    StartOption,
)
from ureasim.hmi.intro.flyby import build_flyby
from ureasim.hmi.intro.ops import (
    Circle,
    GradientRect,
    Image,
    Line,
    Op,
    Polygon,
    Rect,
    RoundRect,
    Static,
    Text,
)
from ureasim.hmi.intro.timeline import (
    clamp01,
    ease_in_out_cubic,
    ease_out_back,
    ease_out_cubic,
    invert_monotonic,
    lerp,
    window,
)

_STAGE_CX = STAGE.width / 2.0
_CX = TITLE.cx  # the text column: logo, titles, button


def pixel_scale(width_px: float, height_px: float) -> float:
    """Design pixels to screen pixels: the stage is fitted whole inside the widget."""
    return min(width_px / STAGE.width, height_px / STAGE.height)


def view_rect(width_px: float, height_px: float) -> Rect:
    """The part of design space a widget of this size shows, centred on the stage.

    Process utility: on a screen that is not 1366:720 the stage stays whole and centred, and the paper
    and grid run on to the widget's edges instead of leaving bars.
    """
    s = pixel_scale(width_px, height_px)
    vw, vh = width_px / s, height_px / s
    return Rect(_STAGE_CX - vw / 2.0, STAGE.height / 2.0 - vh / 2.0, vw, vh)


def _mix(c0: str, c1: str, u: float) -> str:
    """Blend two ``#RRGGBB`` colours; used for the node fill that must match the paper."""
    a = [int(c0[i : i + 2], 16) for i in (1, 3, 5)]
    b = [int(c1[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(lerp(x, y, u)):02X}" for x, y in zip(a, b))


_PAPER_AT_RIBBON = _mix(PALETTE.paper_top, PALETTE.paper_bottom, 0.82)


def _paper(view: Rect, t: float) -> list[Op]:
    """Paper gradient and the engineering-drawing grid the flyby is drawn over, faded in at the start.

    One ``Static`` group: once the grid has faded in it is the same every frame, and the painter draws it
    once into a bitmap (``IntroPainter``) instead of stroking its sixty lines sixty times a second."""
    return [_paper_group(view, ease_out_cubic(window(t, *TIMELINE.backdrop_in)))]


@lru_cache(maxsize=8)
def _paper_group(view: Rect, k: float) -> Static:
    """The paper and, at fade ``k``, its grid. Kept per (view, fade) so a settled frame returns the very same
    object and the painter's check that the group is unchanged is an identity test, not sixty comparisons."""
    ops: list[Op] = [GradientRect(view, PALETTE.paper_top, PALETTE.paper_bottom)]
    if k > 0.0:
        first = math.floor(view.x / GRID_MINOR)
        last = math.ceil(view.right / GRID_MINOR)
        for i in range(first, last + 1):
            a = (0.10 if i % GRID_MAJOR_EVERY == 0 else 0.045) * k
            ops.append(Line(i * GRID_MINOR, view.y, i * GRID_MINOR, view.bottom, PALETTE.teal, 1.0, a))
        first = math.floor(view.y / GRID_MINOR)
        last = math.ceil(view.bottom / GRID_MINOR)
        for i in range(first, last + 1):
            a = (0.10 if i % GRID_MAJOR_EVERY == 0 else 0.045) * k
            ops.append(Line(view.x, i * GRID_MINOR, view.right, i * GRID_MINOR, PALETTE.teal, 1.0, a))
    return Static(tuple(ops), opaque=True)


_LOGO_K = LOGO.width / LOGO.atlas_width
_LOGO_X0 = _CX - LOGO.width / 2.0


def _rect_of(region: Region) -> Rect:
    """A (x, y, w, h) region of the data module as a ``Rect``."""
    return Rect(*region)


def _logo_dst(region: Region) -> Rect:
    """Where a region of the logo file lands on the stage."""
    x, y, w, h = region
    return Rect(_LOGO_X0 + x * _LOGO_K, LOGO.top + y * _LOGO_K, w * _LOGO_K, h * _LOGO_K)


def _logo(t: float) -> list[Op]:
    """The mark in four pieces: emblem pops in with two rings, letters wipe on, the names rise."""
    ops: list[Op] = []
    emblem_dst = _logo_dst(LOGO.emblem)
    emblem_src = _rect_of(LOGO.emblem)

    for win in (TIMELINE.ring_a, TIMELINE.ring_b):
        p = window(t, *win)
        if 0.0 < p < 1.0:
            ops.append(
                Circle(
                    emblem_dst.cx,
                    emblem_dst.cy,
                    lerp(70.0, 250.0, ease_out_cubic(p)),
                    PALETTE.orange,
                    0.45 * (1.0 - p) ** 1.5,
                    width=2.2,
                )
            )

    p = window(t, *TIMELINE.emblem)
    if p > 0.0:
        s = lerp(0.78, 1.0, ease_out_back(p))
        w, h = emblem_dst.w * s, emblem_dst.h * s
        dst = Rect(emblem_dst.cx - w / 2.0, emblem_dst.cy - h / 2.0, w, h)
        ops.append(Image(LOGO.name, emblem_src, dst, ease_out_cubic(clamp01(p * 2.2))))

    p = window(t, *TIMELINE.letters)
    if p > 0.0:
        e = ease_out_cubic(p)
        src = _rect_of(LOGO.letters)
        dst = _logo_dst(LOGO.letters)
        reveal = max(e, 1e-3)
        ops.append(
            Image(
                LOGO.name,
                Rect(src.x, src.y, src.w * reveal, src.h),
                Rect(dst.x, dst.y, dst.w * reveal, dst.h),
                clamp01(p * 3.0),
            )
        )

    for win, region in ((TIMELINE.name_en, LOGO.name_en), (TIMELINE.name_ar, LOGO.name_ar)):
        p = window(t, *win)
        if p > 0.0:
            e = ease_out_cubic(p)
            dst = _logo_dst(region)
            ops.append(Image(LOGO.name, _rect_of(region), Rect(dst.x, dst.y + (1.0 - e) * 10.0, dst.w, dst.h), e))
    return ops


def _titles(t: float) -> list[Op]:
    """The divider and the three lines of text under the logo."""
    ops: list[Op] = []
    p = window(t, *TIMELINE.divider)
    if p > 0.0:
        half = TITLE.divider_half_width * ease_out_cubic(p)
        ops.append(Line(_CX - half, TITLE.divider_y, _CX + half, TITLE.divider_y, PALETTE.orange, 2.5))
        ops.append(Circle(_CX, TITLE.divider_y, 4.0, PALETTE.orange))

    lines = (
        (TIMELINE.title_1, TITLE.line_1_y, STRINGS.title_1, TITLE.line_1_size, TITLE.line_1_spacing_start, TITLE.line_1_spacing, PALETTE.teal_deep, True),
        (TIMELINE.title_2, TITLE.line_2_y, STRINGS.title_2, TITLE.line_2_size, TITLE.line_2_spacing_start, TITLE.line_2_spacing, PALETTE.teal, False),
    )
    for win, y, text, size, sp0, sp1, color, bold in lines:
        p = window(t, *win)
        if p > 0.0:
            e = ease_out_cubic(p)
            ops.append(Text(_CX, y + (1.0 - e) * 12.0, text, size, color, e, "center", lerp(sp0, sp1, e), bold))

    p = window(t, *TIMELINE.subtitle)
    if p > 0.0:
        e = ease_out_cubic(p)
        ops.append(Text(_CX, TITLE.subtitle_y, STRINGS.subtitle, TITLE.subtitle_size, PALETTE.slate, e, "center", TITLE.subtitle_spacing))
    return ops


_NODE_X = tuple(RIBBON.first_node_x + i * RIBBON.node_spacing for i in range(len(SECTIONS)))
_TRACK_LEN = RIBBON.track_end_x - RIBBON.track_start_x


def _lit_time(node_x: float) -> float:
    """Instant the eased flow front passes a node, from the ribbon's run window."""
    u = invert_monotonic(ease_in_out_cubic, (node_x - RIBBON.track_start_x) / _TRACK_LEN)
    start, end = TIMELINE.ribbon_run
    return start + (end - start) * u


NODE_LIT_TIMES = tuple(_lit_time(x) for x in _NODE_X)


def _ribbon(t: float, wall: float) -> list[Op]:
    """The plant-section ribbon: a track the flow front fills, particles on it, the lit nodes."""
    a_track = ease_out_cubic(window(t, *TIMELINE.track_in))
    if a_track <= 0.0:
        return []
    y = RIBBON.y
    x0, x1 = RIBBON.track_start_x, RIBBON.track_end_x
    ops: list[Op] = [Line(x0, y, x1, y, PALETTE.slate, 3.0, 0.20 * a_track)]

    front = ease_in_out_cubic(window(t, *TIMELINE.ribbon_run))
    front_x = x0 + front * _TRACK_LEN
    if front > 0.0:
        ops.append(Line(x0, y, front_x, y, PALETTE.teal, 3.0, 0.95 * a_track))
        for k in range(RIBBON.particle_count):
            s = (k / RIBBON.particle_count + wall * RIBBON.particle_speed / _TRACK_LEN) % 1.0
            x = x0 + s * _TRACK_LEN
            if x < front_x - 2.0:
                fade = clamp01(s * _TRACK_LEN / 30.0) * clamp01((front_x - x) / 30.0)
                ops.append(Circle(x, y, 2.8, PALETTE.orange, 0.9 * fade))

    r = RIBBON.node_radius
    for nx, lit_t, sec in zip(_NODE_X, NODE_LIT_TIMES, SECTIONS):
        ops.append(Circle(nx, y, r, _PAPER_AT_RIBBON, a_track))
        age = t - lit_t
        if age < 0.0:
            ops.append(Circle(nx, y, r, PALETTE.teal, 0.45 * a_track, width=2.0))
            continue
        ops.append(Circle(nx, y, r, PALETTE.teal, 0.95, width=2.2))
        pop = ease_out_back(window(age, 0.0, 0.35))
        ops.append(Circle(nx, y, 6.2 * pop, PALETTE.orange))
        ping = window(age, 0.0, 0.6)
        if 0.0 < ping < 1.0:
            ops.append(Circle(nx, y, lerp(r, r + 16.0, ease_out_cubic(ping)), PALETTE.orange, 0.55 * (1.0 - ping), width=1.8))
        la = ease_out_cubic(window(age, 0.0, 0.4))
        ops.append(Text(nx, y + RIBBON.number_dy, sec.number, RIBBON.number_size, PALETTE.teal_deep, la, "center", 1.5, True))
        ops.append(Text(nx, y + RIBBON.name_dy, sec.name, RIBBON.name_size, PALETTE.slate, la, "center", RIBBON.name_spacing))
    return ops


def _footer(t: float, status: str, wall: float, busy: bool) -> list[Op]:
    """Version at the left, key hint at the right, the application's own status line in the middle.

    Once the start is pressed (``busy``) there is nothing left to press, so the key hint goes."""
    y = TITLE.footer_y
    a = ease_out_cubic(window(t, *TIMELINE.hint_in))
    ops: list[Op] = []
    if a <= 0.0:
        return ops
    left, right = TITLE.footer_margin, STAGE.width - TITLE.footer_margin
    ops.append(Text(left, y, STRINGS.version, TITLE.footer_size, PALETTE.slate, 0.7 * a, "left", TITLE.footer_spacing, True))
    # The hint changes meaning when the button arrives: before it a key skips, after it a key starts.
    swap = ease_out_cubic(window(t, *TIMELINE.button_in))
    if swap < 1.0:
        ops.append(Text(right, y, STRINGS.hint, TITLE.footer_size, PALETTE.slate, 0.55 * a * (1.0 - swap), "right", TITLE.footer_spacing))
    if swap > 0.0 and not busy:
        ops.append(Text(right, y, STRINGS.start_hint, TITLE.footer_size, PALETTE.slate, 0.55 * swap, "right", TITLE.footer_spacing))
    if status:
        pulse = 0.65 + 0.35 * math.sin(2.0 * math.pi * wall / 1.4)
        ops.append(Text(_STAGE_CX, y, status.upper(), TITLE.footer_size, PALETTE.teal_deep, pulse * a, "center", TITLE.footer_spacing, True))
    return ops


class ButtonState(Enum):
    """How a start button is drawn: waiting, under the pointer, or pressed and working."""

    IDLE = auto()
    HOVER = auto()
    BUSY = auto()


#: One state for every start button, or one per option key (a key it does not name is IDLE).
ButtonStates = ButtonState | Mapping[str, ButtonState]

_OPTIONS = {option.key: option for option in START_OPTIONS}
_ROW_WIDTH = sum(option.width for option in START_OPTIONS) + BUTTON.gap * (len(START_OPTIONS) - 1)


def _row_lefts() -> dict[str, float]:
    """Each pill's left edge: the options left to right, the row centred on the text column."""
    lefts: dict[str, float] = {}
    x = _CX - _ROW_WIDTH / 2.0
    for option in START_OPTIONS:
        lefts[option.key] = x
        x += option.width + BUTTON.gap
    return lefts


_PILL_LEFT = _row_lefts()


def button_rect(key: str = START_OPTION.key) -> Rect:
    """A start button's rectangle in design pixels, at rest (its hit area); the 100% LOAD button's by default."""
    return Rect(_PILL_LEFT[key], BUTTON.center_y - BUTTON.height / 2.0, _OPTIONS[key].width, BUTTON.height)


def to_design(x_px: float, y_px: float, view: Rect, width_px: float, height_px: float) -> tuple[float, float]:
    """A pixel of a widget of this size as a point of design space (the inverse of the painter's map)."""
    s = pixel_scale(width_px, height_px)
    return view.x + x_px / s, view.y + y_px / s


def button_at(x: float, y: float) -> str | None:
    """The key of the start button a design-space point lies on, or None between and beside them."""
    for option in START_OPTIONS:
        r = button_rect(option.key)
        if r.x <= x <= r.right and r.y <= y <= r.bottom:
            return option.key
    return None


def button_contains(x: float, y: float) -> bool:
    """Whether a design-space point lies on a start button."""
    return button_at(x, y) is not None


def _state_of(button: ButtonStates, key: str) -> ButtonState:
    """How the pill of ``key`` is drawn."""
    return button if isinstance(button, ButtonState) else button.get(key, ButtonState.IDLE)


def _busy(button: ButtonStates) -> bool:
    """A start was pressed: some pill is drawn working."""
    states = (button,) if isinstance(button, ButtonState) else tuple(button.values())
    return any(state is ButtonState.BUSY for state in states)


def _icon(option: StartOption, rect: Rect, alpha: float) -> Polygon:
    """The pill's glyph: a play triangle for the start at 100 % load, a folder for a saved exercise."""
    ix = rect.cx + option.icon_dx
    h = BUTTON.icon_half_height
    if option.icon == "folder":
        top, tab, bottom = rect.cy - 0.8 * h, rect.cy - 0.45 * h, rect.cy + 0.8 * h
        points = ((ix - 1.1 * h, top), (ix - 0.25 * h, top), (ix - 0.05 * h, tab), (ix + 1.1 * h, tab),
                  (ix + 1.1 * h, bottom), (ix - 1.1 * h, bottom))
    else:
        points = ((ix - h * 0.7, rect.cy - h), (ix + h * 1.1, rect.cy), (ix - h * 0.7, rect.cy + h))
    return Polygon(points, PALETTE.orange, alpha)


def _buttons(t: float, wall: float, button: ButtonStates) -> list[Op]:
    """The row of start pills, 100% LOAD first."""
    ops: list[Op] = []
    for option in START_OPTIONS:
        ops += _button(t, wall, option, _state_of(button, option.key))
    return ops


def _button(t: float, wall: float, option: StartOption, state: ButtonState) -> list[Op]:
    """One start button: a pill that rises in, breathes while it waits, dims while it works."""
    a = ease_out_cubic(window(t, *TIMELINE.button_in))
    if a <= 0.0:
        return []
    base = button_rect(option.key)
    rect = Rect(base.x, base.y + (1.0 - a) * BUTTON.rise, base.w, base.h)
    pill = rect.h / 2.0
    ops: list[Op] = []
    if state is ButtonState.IDLE:
        breath = 0.5 + 0.5 * math.sin(2.0 * math.pi * wall / 1.6)
        gap = BUTTON.ring_gap + 2.0 * breath
        ring = Rect(rect.x - gap, rect.y - gap, rect.w + 2.0 * gap, rect.h + 2.0 * gap)
        ops.append(RoundRect(ring, pill + gap, PALETTE.orange, (0.30 + 0.30 * breath) * a, 2.0))
        fill, fill_alpha = PALETTE.teal_deep, a
    elif state is ButtonState.HOVER:
        ring = Rect(rect.x - BUTTON.ring_gap, rect.y - BUTTON.ring_gap, rect.w + 2.0 * BUTTON.ring_gap, rect.h + 2.0 * BUTTON.ring_gap)
        ops.append(RoundRect(ring, pill + BUTTON.ring_gap, PALETTE.orange, 0.95 * a, 2.0))
        fill, fill_alpha = PALETTE.teal, a
    else:
        fill, fill_alpha = PALETTE.slate, 0.75 * a
    ops.append(RoundRect(rect, pill, fill, fill_alpha))
    label_alpha = a if state is not ButtonState.BUSY else 0.85 * a
    ops.append(_icon(option, rect, label_alpha))
    ops.append(
        Text(rect.cx + option.label_dx, rect.cy, option.label, BUTTON.label_size, PALETTE.white, label_alpha, "center", BUTTON.label_spacing, True)
    )
    return ops


def build_frame(
    t: float,
    view: Rect,
    *,
    status: str = "",
    wall: float | None = None,
    button: ButtonStates = ButtonState.IDLE,
) -> list[Op]:
    """Every drawing operation of the intro at scene time ``t``, back to front.

    ``view`` is the visible region of design space (see ``view_rect``); ``status`` is the line the
    application wants shown while it works; ``wall`` is the unclamped clock for idle motion and
    defaults to ``t``; ``button`` is how the start buttons are drawn, one state for all of them or one
    per option key.
    """
    clock = min(max(t, 0.0), TIMELINE.hold)
    idle = clock if wall is None else wall
    ops = _paper(view, clock)
    ops += build_flyby(clock, idle, view)
    ops += _logo(clock)
    ops += _titles(clock)
    ops += _ribbon(clock, idle)
    ops += _buttons(clock, idle, button)
    ops += _footer(clock, status, idle, _busy(button))
    return ops
