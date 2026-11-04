"""Tests of ``ureasim/data/intro_flyby.py``: the constants of the Plant Hover Flyby.

Pinned: every group names its source; the orbit closes with no seam (the bob period and every flow-dot
cycle divide the orbit period, as the data's own note says); the lens and the near plane are possible; the
clear zones lie on the stage, can fade a line to a floor between 0 and 1, and the HUD sits inside the zones
meant to keep it legible.
"""

from __future__ import annotations

import pytest

from ureasim.data.intro import STAGE
from ureasim.data.intro_flyby import CLEAR_ZONES, HUD, LOOK, ORBIT, ROAD, ROSE

_GROUPS = (ORBIT, LOOK, HUD, ROAD, ROSE)


@pytest.mark.parametrize("group", _GROUPS, ids=lambda g: type(g).__name__)
def test_every_constant_group_names_its_source(group) -> None:
    assert group.source.strip()


def test_every_clear_zone_names_its_source() -> None:
    assert all(z.source.strip() for z in CLEAR_ZONES)


def test_the_orbit_closes_with_no_seam() -> None:
    """The bob divides the orbit period whole, so the picture one period on is the same picture."""
    assert ORBIT.period / ORBIT.bob_period == pytest.approx(round(ORBIT.period / ORBIT.bob_period))
    assert ORBIT.period == 32.0 and ORBIT.bob_period == 8.0  # 11.25 degrees a second, the data's own note


def test_the_orbit_descends_and_scans_inside_the_scene() -> None:
    assert ORBIT.radius_start > ORBIT.radius_hover > 0 and ORBIT.height_start > ORBIT.height_hover > 0
    for start, end in (ORBIT.descent, ORBIT.fade_in, ORBIT.scan):
        assert 0.0 <= start < end
    assert 0.0 < ORBIT.fov_v_deg < 90.0 and ORBIT.near > 0.0 and ORBIT.scan_top > 0.0


def test_the_orbit_centre_is_on_the_stage() -> None:
    cx, cy = ORBIT.centre
    assert 0.0 < cx < STAGE.width and 0.0 < cy < STAGE.height


def test_the_ink_is_visible_and_the_steps_are_whole() -> None:
    for alpha in (LOOK.alpha_shell, LOOK.alpha_stream, LOOK.alpha_valve, LOOK.alpha_ground, LOOK.scan_alpha):
        assert 0.0 < alpha <= 1.0
    for width in (LOOK.width_shell, LOOK.width_stream, LOOK.width_valve, LOOK.width_ground):
        assert width > 0.0
    assert isinstance(LOOK.alpha_steps, int) and 2 <= LOOK.alpha_steps < 1024  # a bucket's sort key allows < 1024
    assert LOOK.depth_near < LOOK.depth_far and 0.0 < LOOK.depth_far_factor < 1.0
    assert LOOK.max_segment > 0.0 and LOOK.scan_points >= 8


def test_the_flow_dots_run_at_a_speed_that_gives_whole_laps_in_an_orbit() -> None:
    """The dots' cycle count is rounded to a whole number per orbit, which needs a speed and spacing > 0."""
    assert LOOK.pulse_speed > 0.0 and LOOK.pulse_spacing > 0.0 and LOOK.pulse_radius_px > 0.0


def test_the_clear_zones_lie_on_the_stage_and_fade_to_a_floor() -> None:
    names = [z.name for z in CLEAR_ZONES]
    assert len(names) == len(set(names)) == 6
    for z in CLEAR_ZONES:
        assert 0.0 <= z.x0 < z.x1 <= STAGE.width and 0.0 <= z.y0 < z.y1 <= STAGE.height, z.name
        assert 0.0 <= z.floor < 1.0 and z.soft > 0.0, z.name


def test_the_hud_sits_inside_the_zones_that_keep_it_legible() -> None:
    zones = {z.name: z for z in CLEAR_ZONES}
    cap = zones["caption"]
    assert cap.x0 <= HUD.caption_x <= cap.x1 and cap.y0 <= HUD.caption_y <= cap.y1
    dial = zones["dial"]
    assert dial.x0 <= HUD.dial_x - HUD.dial_r and HUD.dial_x + HUD.dial_r <= dial.x1
    assert dial.y0 <= HUD.dial_y - HUD.dial_r and HUD.dial_y + HUD.dial_r <= dial.y1
    legend = zones["legend"]
    assert legend.x0 <= HUD.legend_x <= legend.x1 and legend.y0 <= HUD.legend_y <= legend.y1
    assert HUD.dial_tick_deg > 0 and 360.0 / HUD.dial_tick_deg == round(360.0 / HUD.dial_tick_deg)


def test_the_ground_ring_and_road_are_inside_the_orbit() -> None:
    assert 0.0 < ROSE.radius < ORBIT.radius_hover and ROSE.tick_step_deg > 0.0 and 360.0 / ROSE.tick_step_deg == round(360.0 / ROSE.tick_step_deg)
    assert ROAD.half_w > ROAD.corner > 0.0 and ROAD.half_d > ROAD.corner and ROAD.width > 0.0
