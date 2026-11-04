"""Tests of ureasim/hmi/intro/scene.py: the frame as a function of time, with no display."""

from __future__ import annotations

import math

import pytest

from ureasim.data.intro import BUTTON, LOGO, PALETTE, RIBBON, SECTIONS, START_OPTION, STAGE, STRINGS, TIMELINE, TITLE
from ureasim.hmi.intro import scene
from ureasim.hmi.intro.ops import Circle, GradientRect, Image, Line, Lines, Polygon, Rect, RoundRect, Static, Text, flatten
from ureasim.hmi.intro.scene import ButtonState

_VIEWS = [(1366, 720), (1920, 1080), (1920, 1200), (1280, 1024), (2560, 1080)]
_KNOWN = (GradientRect, Line, Lines, Circle, RoundRect, Polygon, Text, Image)


def _frame(t: float, view: Rect, **kwargs) -> list:
    """The frame's drawing operations with every ``Static`` group opened (the tests read the drawing, not
    how the painter may cache it); ``test_the_paper_is_one_static_group`` pins the grouping itself."""
    return list(flatten(scene.build_frame(t, view, **kwargs)))


def _stage_view() -> Rect:
    return scene.view_rect(STAGE.width, STAGE.height)


def _texts(ops) -> list[Text]:
    return [o for o in ops if isinstance(o, Text)]


def _images(ops) -> list[Image]:
    return [o for o in ops if isinstance(o, Image)]


@pytest.mark.parametrize("size", _VIEWS)
def test_view_keeps_the_whole_stage_centred(size) -> None:
    w, h = size
    v = scene.view_rect(w, h)
    assert v.x <= 1e-9 and v.y <= 1e-9
    assert v.right >= STAGE.width - 1e-9 and v.bottom >= STAGE.height - 1e-9
    assert v.cx == pytest.approx(STAGE.width / 2.0) and v.cy == pytest.approx(STAGE.height / 2.0)
    assert v.w / v.h == pytest.approx(w / h)
    assert scene.pixel_scale(w, h) * v.w == pytest.approx(w)


def test_first_frame_is_paper_and_grid_only() -> None:
    ops = _frame(0.0, _stage_view())
    assert len(ops) == 1 and isinstance(ops[0], GradientRect)


@pytest.mark.parametrize("size", _VIEWS)
def test_every_operation_is_finite_and_inside_its_ranges(size) -> None:
    view = scene.view_rect(*size)
    t = 0.0
    while t <= TIMELINE.hold + 0.5:
        for op in _frame(t, view, status="starting console", wall=t + 3.7):
            assert isinstance(op, _KNOWN)
            if isinstance(op, GradientRect):
                continue
            assert 0.0 <= getattr(op, "alpha") <= 1.0, (t, op)
            if isinstance(op, Circle):
                assert math.isfinite(op.cx + op.cy + op.r) and op.r >= 0.0 and op.width >= 0.0
            elif isinstance(op, Line):
                assert math.isfinite(op.x1 + op.y1 + op.x2 + op.y2) and op.width > 0.0
            elif isinstance(op, Lines):
                assert op.segments and op.width > 0.0 and all(math.isfinite(c) for seg in op.segments for c in seg)
            elif isinstance(op, Text):
                assert math.isfinite(op.x + op.y) and op.size > 0.0 and op.spacing >= 0.0 and op.text
            elif isinstance(op, Image):
                assert op.src.w > 0.0 and op.src.h > 0.0 and op.dst.w >= 0.0 and op.dst.h >= 0.0
            elif isinstance(op, RoundRect):
                assert op.rect.w > 0.0 and op.rect.h > 0.0 and op.radius >= 0.0 and op.width >= 0.0
            elif isinstance(op, Polygon):
                assert len(op.points) >= 3
        t += 0.05


def test_frame_is_deterministic() -> None:
    v = _stage_view()
    assert _frame(3.3, v, status="x", wall=9.0) == _frame(3.3, v, status="x", wall=9.0)


def test_time_past_the_hold_is_the_hold_frame() -> None:
    v = _stage_view()
    assert _frame(TIMELINE.hold + 5.0, v, wall=TIMELINE.hold) == _frame(TIMELINE.hold, v)
    assert _frame(-4.0, v) == _frame(0.0, v)


def test_hold_frame_shows_the_whole_logo_at_full_strength() -> None:
    images = _images(_frame(TIMELINE.hold, _stage_view()))
    assert len(images) == 4
    assert all(i.alpha == pytest.approx(1.0) and i.name == LOGO.name for i in images)
    sources = {(i.src.x, i.src.y, i.src.w, i.src.h) for i in images}
    assert sources == {LOGO.emblem, LOGO.letters, LOGO.name_en, LOGO.name_ar}
    # the group is centred on the text column and as wide as the data module says
    left = min(i.dst.x for i in images)
    right = max(i.dst.right for i in images)
    assert (left + right) / 2.0 == pytest.approx(TITLE.cx, abs=1.0)
    assert right - left == pytest.approx(LOGO.width, abs=1.0)


def test_logo_pieces_never_leave_the_atlas() -> None:
    v = _stage_view()
    t = 0.0
    while t <= TIMELINE.hold:
        for i in _images(_frame(t, v)):
            assert 0.0 <= i.src.x and i.src.right <= LOGO.atlas_width + 1e-9
            assert 0.0 <= i.src.y and i.src.bottom <= LOGO.atlas_height + 1e-9
        t += 0.02


def test_logo_pieces_are_revealed_not_removed() -> None:
    v = _stage_view()
    seen = 0
    t = 0.0
    while t <= TIMELINE.hold:
        n = len(_images(_frame(t, v)))
        assert n >= seen
        seen = n
        t += 0.02
    assert seen == 4


def test_letters_wipe_left_to_right() -> None:
    v = _stage_view()
    widths = []
    t = TIMELINE.letters[0]
    while t <= TIMELINE.letters[1] + 0.05:
        letters = [i for i in _images(_frame(t, v)) if i.src.x == LOGO.letters[0]]
        if letters:
            widths.append(letters[0].src.w)
            assert letters[0].dst.x == pytest.approx(scene._logo_dst(LOGO.letters).x)
        t += 0.02
    assert widths == sorted(widths)
    assert widths[0] < 0.1 * LOGO.letters[2] and widths[-1] == pytest.approx(LOGO.letters[2])


def test_hold_frame_carries_every_text_of_the_intro() -> None:
    texts = {t.text for t in _texts(_frame(TIMELINE.hold, _stage_view()))}
    assert {STRINGS.title_1, STRINGS.title_2, STRINGS.subtitle, STRINGS.version, STRINGS.start_hint} <= texts
    assert START_OPTION.label in texts
    assert {s.number for s in SECTIONS} <= texts and {s.name for s in SECTIONS} <= texts


def test_the_paper_is_one_static_group() -> None:
    """The grid is the same every frame once faded in; as one opaque ``Static`` it may be bitmapped."""
    for t in (0.0, 0.5, TIMELINE.hold):
        ops = scene.build_frame(t, _stage_view())
        groups = [o for o in ops if isinstance(o, Static)]
        assert len(groups) == 1 and groups[0].opaque and ops[0] is groups[0]
        assert isinstance(groups[0].ops[0], GradientRect)
    settled = scene.build_frame(TIMELINE.hold, _stage_view())[0]
    assert settled is scene.build_frame(TIMELINE.hold + 3.0, _stage_view())[0]  # the same object, frame after frame


def test_sections_light_in_the_order_of_the_console_tabs() -> None:
    v = _stage_view()
    first_seen: dict[str, float] = {}
    t = 0.0
    while t <= TIMELINE.hold:
        for tx in _texts(_frame(t, v)):
            if tx.text in {s.number for s in SECTIONS} and tx.alpha > 0.0:
                first_seen.setdefault(tx.text, t)
        t += 0.01
    order = [first_seen[s.number] for s in SECTIONS]
    assert order == sorted(order) and len(set(order)) == len(order)
    for seen, lit in zip(order, scene.NODE_LIT_TIMES):
        assert seen == pytest.approx(lit, abs=0.02)


def test_every_node_is_lit_before_the_hold_with_time_to_read_it() -> None:
    assert scene.NODE_LIT_TIMES == tuple(sorted(scene.NODE_LIT_TIMES))
    assert scene.NODE_LIT_TIMES[0] > TIMELINE.ribbon_run[0]
    assert scene.NODE_LIT_TIMES[-1] + 0.4 <= TIMELINE.hold


def test_ribbon_is_symmetric_about_the_stage_centre() -> None:
    xs = scene._NODE_X
    assert sum(xs) / len(xs) == pytest.approx(STAGE.width / 2.0)
    assert (RIBBON.track_start_x + RIBBON.track_end_x) / 2.0 == pytest.approx(STAGE.width / 2.0)


def test_vertical_rhythm_has_no_overlaps() -> None:
    k = LOGO.width / LOGO.atlas_width
    logo_bottom = LOGO.top + LOGO.atlas_height * k
    rhythm = [
        logo_bottom,
        TITLE.divider_y,
        TITLE.line_1_y - TITLE.line_1_size / 2.0,
        TITLE.line_1_y + TITLE.line_1_size / 2.0,
        TITLE.line_2_y - TITLE.line_2_size / 2.0,
        TITLE.line_2_y + TITLE.line_2_size / 2.0,
        TITLE.subtitle_y - TITLE.subtitle_size / 2.0,
        TITLE.subtitle_y + TITLE.subtitle_size / 2.0,
        scene.button_rect().y - BUTTON.ring_gap - 2.0,
        scene.button_rect().bottom + BUTTON.ring_gap + 2.0,
        RIBBON.y + RIBBON.number_dy - RIBBON.number_size / 2.0,
        RIBBON.y + RIBBON.name_dy + RIBBON.name_size / 2.0,
        TITLE.footer_y - TITLE.footer_size / 2.0,
    ]
    assert rhythm == sorted(rhythm) and len(set(rhythm)) == len(rhythm)
    assert TITLE.footer_y + TITLE.footer_size / 2.0 <= STAGE.height


def test_ribbon_labels_do_not_collide_across_neighbouring_nodes() -> None:
    longest = max(len(s.name) for s in SECTIONS)
    approx_width = longest * (RIBBON.name_size * 0.75 + RIBBON.name_spacing)  # generous sans estimate
    assert approx_width < RIBBON.node_spacing


def test_status_line_is_shown_only_when_given_and_in_capitals() -> None:
    v = _stage_view()
    assert "STARTING CONSOLE" in {t.text for t in _texts(_frame(TIMELINE.hold, v, status="Starting console"))}
    plain = {t.text for t in _texts(_frame(TIMELINE.hold, v))}
    assert not any("STARTING" in s for s in plain)


def test_idle_clock_leaves_the_paper_the_grid_and_the_logo_alone() -> None:
    """The wall clock drives the orbit, the flow dots, the particles and the pulses; nothing static moves."""
    v = _stage_view()
    a = _frame(TIMELINE.hold, v, status="s", wall=10.0)
    b = _frame(TIMELINE.hold, v, status="s", wall=10.4)
    assert a != b
    static = lambda ops: [o for o in ops if isinstance(o, (Image, GradientRect, Line))]  # noqa: E731
    assert static(a) == static(b)


def test_grid_runs_to_the_widget_edge_on_a_wide_view() -> None:
    view = scene.view_rect(2560, 1080)
    lines = [o for o in _frame(TIMELINE.hold, view) if isinstance(o, Line) and o.y1 == view.y]
    xs = [o.x1 for o in lines]
    assert min(xs) <= view.x + 40.0 and max(xs) >= view.right - 40.0


# -- the start button ---------------------------------------------------------------------------


def _button_ops(ops):
    """The button's own operations: its pill and ring, its play triangle, its label (not the dial's pointer)."""
    r = scene.button_rect()
    on_button = lambda o: all(r.x <= x <= r.right and r.y - 12.0 <= y <= r.bottom + 12.0 for x, y in o.points)  # noqa: E731
    return [
        o
        for o in ops
        if isinstance(o, RoundRect) or (isinstance(o, Polygon) and on_button(o)) or (isinstance(o, Text) and o.text == START_OPTION.label)
    ]


def test_start_option_is_the_100_percent_load_button() -> None:
    assert START_OPTION.label == "100% LOAD" and START_OPTION.key == "load_100"


def test_button_is_absent_until_its_window_and_complete_at_the_hold() -> None:
    v = _stage_view()
    assert _button_ops(_frame(TIMELINE.button_in[0] - 0.01, v)) == []
    assert _button_ops(_frame(TIMELINE.button_in[0] + 0.15, v))
    label = [o for o in _texts(_frame(TIMELINE.hold, v)) if o.text == START_OPTION.label]
    assert len(label) == 1 and label[0].alpha == pytest.approx(1.0)


def test_button_arrives_after_the_last_section_is_lit() -> None:
    assert scene.NODE_LIT_TIMES[-1] + 0.4 <= TIMELINE.button_in[0]
    assert TIMELINE.button_in[1] <= TIMELINE.hold


def test_button_rect_is_centred_on_the_text_column_and_sized_from_the_data() -> None:
    r = scene.button_rect()
    assert r.cx == pytest.approx(TITLE.cx) and r.cy == pytest.approx(BUTTON.center_y)
    assert (r.w, r.h) == (BUTTON.width, BUTTON.height)


def test_hit_test_agrees_with_the_drawn_pill() -> None:
    r = scene.button_rect()
    assert scene.button_contains(r.cx, r.cy)
    assert scene.button_contains(r.x + 1, r.y + 1) and scene.button_contains(r.right - 1, r.bottom - 1)
    assert not scene.button_contains(r.x - 2, r.cy) and not scene.button_contains(r.cx, r.bottom + 2)
    assert not scene.button_contains(0.0, 0.0)
    hold = _frame(TIMELINE.hold, _stage_view())
    pill = [o for o in hold if isinstance(o, RoundRect) and o.width == 0.0 and o.color == PALETTE.teal_deep][0]
    assert (pill.rect.x, pill.rect.y, pill.rect.w, pill.rect.h) == pytest.approx((r.x, r.y, r.w, r.h))


@pytest.mark.parametrize("size", _VIEWS)
def test_pixel_to_design_inverts_the_painter_map(size) -> None:
    w, h = size
    view = scene.view_rect(w, h)
    s = scene.pixel_scale(w, h)
    for dx, dy in ((683.0, 522.0), (0.0, 0.0), (1366.0, 720.0), (560.0, 500.0)):
        px, py = (dx - view.x) * s, (dy - view.y) * s  # the painter's map, design to pixel
        assert scene.to_design(px, py, view, w, h) == pytest.approx((dx, dy))
    cx, cy = scene.button_rect().cx, scene.button_rect().cy
    assert scene.button_contains(*scene.to_design((cx - view.x) * s, (cy - view.y) * s, view, w, h))


def test_button_states_are_drawn_differently() -> None:
    v = _stage_view()
    idle, hover, busy = (_frame(TIMELINE.hold, v, button=b) for b in ButtonState)
    assert idle != hover and hover != busy and idle != busy
    fill = lambda ops: [o for o in ops if isinstance(o, RoundRect) and o.width == 0.0][0]  # noqa: E731
    assert fill(idle).color == PALETTE.teal_deep and fill(hover).color == PALETTE.teal and fill(busy).color == PALETTE.slate


def test_idle_button_breathes_but_the_busy_one_is_still() -> None:
    v = _stage_view()
    a = _frame(TIMELINE.hold, v, wall=10.0, button=ButtonState.IDLE)
    b = _frame(TIMELINE.hold, v, wall=10.4, button=ButtonState.IDLE)
    ring = lambda ops: [o for o in ops if isinstance(o, RoundRect) and o.width > 0.0]  # noqa: E731
    assert ring(a) != ring(b)
    c = _frame(TIMELINE.hold, v, wall=10.0, button=ButtonState.BUSY)
    d = _frame(TIMELINE.hold, v, wall=10.4, button=ButtonState.BUSY)
    assert [o for o in c if isinstance(o, (RoundRect, Polygon))] == [o for o in d if isinstance(o, (RoundRect, Polygon))]
    assert not ring(c)


def test_hint_changes_from_skip_to_start_when_the_button_arrives() -> None:
    v = _stage_view()
    early = {t.text: t.alpha for t in _texts(_frame(TIMELINE.button_in[0] - 0.05, v))}
    assert early[STRINGS.hint] > 0.4 and STRINGS.start_hint not in early
    late = {t.text: t.alpha for t in _texts(_frame(TIMELINE.hold, v))}
    assert late[STRINGS.start_hint] > 0.4 and late.get(STRINGS.hint, 0.0) == pytest.approx(0.0)


def test_the_key_hint_goes_once_the_start_is_pressed() -> None:
    texts = {t.text for t in _texts(_frame(TIMELINE.hold, _stage_view(), status="s", button=ButtonState.BUSY))}
    assert STRINGS.start_hint not in texts and STRINGS.hint not in texts
    assert STRINGS.version in texts and "S" in texts  # the version and the application's status line stay


def test_the_text_column_stands_in_the_left_third_and_leaves_the_flyby_the_rest() -> None:
    """Logo, titles and button all lie left of the flyby's region; the stage centre is not where they stand."""
    half = LOGO.width / 2.0
    assert TITLE.cx + half < 0.5 * STAGE.width
    assert TITLE.cx - half >= 0.0
    r = scene.button_rect()
    assert r.right < 0.5 * STAGE.width
    title_half = TITLE.divider_half_width
    assert TITLE.cx + title_half < 0.5 * STAGE.width
