"""Tests of ``ureasim/data/intro.py``: the constants of the start-up intro.

Pinned: every constant group names its source (CLAUDE.md section 1 rule 7); the stage is the DCS screens'
stage; the timeline's windows are ordered and end by the hold; the logo's file and regions agree; the
sections stand in the console's tab order with the scope table's names; each start key sends an engine
command the engine handles, and LOAD's restore is the engine's own; the start-up waits and the hairline
threshold are the ones their sources give.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

import pytest

from ureasim.data import intro
from ureasim.data.intro import (
    BUTTON,
    CHOOSER,
    HAIRLINE_MAX_PX,
    LOAD_OPTION,
    LOGO,
    PALETTE,
    RESTORE_COMMAND,
    RIBBON,
    SECTIONS,
    STAGE,
    STARTUP,
    START_COMMANDS,
    START_OPTION,
    START_OPTIONS,
    STRINGS,
    TICK_MS,
    TIMELINE,
    TITLE,
)
from ureasim.data.screen_layout import SCREENS
from ureasim.engine.command import SIMULATOR_COMMANDS

_GROUPS = (STAGE, PALETTE, TIMELINE, LOGO, TITLE, RIBBON, STRINGS, BUTTON, START_OPTION, LOAD_OPTION, STARTUP,
           CHOOSER)


@pytest.mark.parametrize("group", _GROUPS, ids=lambda g: type(g).__name__)
def test_every_constant_group_names_its_source(group) -> None:
    assert group.source.strip(), type(group).__name__


def test_every_section_names_its_source() -> None:
    assert all(s.source.strip() for s in SECTIONS)


def test_the_stage_is_the_dcs_screens_stage() -> None:
    assert (STAGE.width, STAGE.height) == (1366.0, 720.0)


def test_the_palette_is_six_digit_hex_colours() -> None:
    colours = [v for k, v in vars(PALETTE).items() if k != "source"]
    assert len(colours) == 7 and all(re.fullmatch(r"#[0-9A-F]{6}", c) for c in colours)


def test_the_timeline_windows_are_ordered_and_end_by_the_hold() -> None:
    windows = {k: v for k, v in vars(TIMELINE).items() if isinstance(v, tuple)}
    assert len(windows) >= 14
    for name, (start, end) in windows.items():
        assert 0.0 <= start < end <= TIMELINE.hold, name
    assert TIMELINE.button_in[1] <= TIMELINE.hold and TIMELINE.ribbon_run[1] <= TIMELINE.button_in[0]
    assert TIMELINE.fade > 0.0


def test_the_logo_file_is_the_supplied_mark_doubled_and_its_regions_fit() -> None:
    """The supplied mark was 640 x 301 with regions (0, 0, 242, 191), (286, 0, 354, 191), (286, 206, 354, 46) and
    (286, 252, 354, 49); the file is its exact 2x resample and the regions are doubled with it."""
    supplied = ((0.0, 0.0, 242.0, 191.0), (286.0, 0.0, 354.0, 191.0), (286.0, 206.0, 354.0, 46.0), (286.0, 252.0, 354.0, 49.0))
    assert (LOGO.atlas_width, LOGO.atlas_height) == (2 * 640.0, 2 * 301.0)
    doubled = tuple(tuple(2.0 * v for v in region) for region in supplied)
    assert (LOGO.emblem, LOGO.letters, LOGO.name_en, LOGO.name_ar) == doubled
    for x, y, w, h in doubled:
        assert x >= 0 and y >= 0 and x + w <= LOGO.atlas_width and y + h <= LOGO.atlas_height


def test_the_logo_file_is_rgba_at_the_size_the_data_says() -> None:
    png = Path(intro.__file__).resolve().parents[1] / "hmi" / "intro" / "assets" / f"{LOGO.name}.png"
    header = png.read_bytes()[:26]
    width, height, depth, colour_type = struct.unpack(">IIBB", header[16:26])
    assert (width, height) == (LOGO.atlas_width, LOGO.atlas_height)
    assert (depth, colour_type) == (8, 6)  # 8-bit RGBA: the alpha channel the mark's edges need


def test_the_logo_is_drawn_inside_the_text_column() -> None:
    """The mark is LOGO.width wide, centred on the column; the scale between file and stage is not above 1,
    so the file is never scaled up on a windowed stage."""
    assert LOGO.width / LOGO.atlas_width <= 1.0
    assert TITLE.cx - LOGO.width / 2.0 >= 0.0 and TITLE.cx + LOGO.width / 2.0 <= STAGE.width / 2.0


def test_the_ribbon_has_a_node_for_each_section_inside_its_track() -> None:
    last = RIBBON.first_node_x + (len(SECTIONS) - 1) * RIBBON.node_spacing
    assert RIBBON.track_start_x <= RIBBON.first_node_x and last <= RIBBON.track_end_x


# -- the sections ----------------------------------------------------------------------------------------

_SECTION_NAMES = {
    "321": "NH3 PUMPING",
    "322": "UREA SYNTHESIS",
    "323": "LP RECIRCULATION",
    "328": "DESORPTION",
    "324": "EVAPORATION",
    "329": "STEAM & UTILITIES",
}


def _tab_order_of_sections() -> list[str]:
    """The unit numbers in the order the console's tab bar first reaches them, read from its own list."""
    order: list[str] = []
    for screen_id, _title in SCREENS:  # e.g. ("screen-322-2", "322-2 UREA SYNTHESIS HP SCRUBBER")
        number = screen_id.split("-")[1]
        if number not in order:
            order.append(number)
    return order


def test_sections_are_the_six_of_the_plant_scope_table_named_as_the_scope_table_names_them() -> None:
    """Pinned to project.md section 1 (plant scope table): the intro must not invent or rename one."""
    assert {s.number: s.name for s in SECTIONS} == _SECTION_NAMES


def test_sections_stand_in_the_order_of_the_console_tab_bar() -> None:
    """Decided 2026-11-04 (handoff A-25 point 3): the order is the console's own, derived here from its tab
    list, so a change to the tabs fails this test instead of leaving the intro out of step. 329 is fourth."""
    assert [s.number for s in SECTIONS] == _tab_order_of_sections()
    assert [s.number for s in SECTIONS] == ["321", "322", "329", "323", "328", "324"]


# -- the start -------------------------------------------------------------------------------------------


def test_the_start_key_sends_the_engines_own_release_with_on_stated() -> None:
    """The 100% LOAD key maps to the engine's ``freeze`` command, ``on`` stated (a missing ``on`` toggles)."""
    command = START_COMMANDS[START_OPTION.key]
    assert command["type"] == "freeze" and command["type"] in SIMULATOR_COMMANDS
    assert command["on"] is False


def test_there_is_one_start_command_for_each_start_option_and_each_is_the_release() -> None:
    assert set(START_COMMANDS) == {o.key for o in START_OPTIONS} == {"load_100", "load_exercise"}
    assert all(dict(START_COMMANDS[o.key]) == {"type": "freeze", "on": False} for o in START_OPTIONS)


def test_100_percent_load_is_first_and_only_load_restores_an_exercise() -> None:
    """Enter presses the first option; the start from a saved exercise is LOAD's alone (decision 171)."""
    assert START_OPTIONS == (START_OPTION, LOAD_OPTION)
    assert not START_OPTION.restores_exercise and LOAD_OPTION.restores_exercise
    assert (START_OPTION.label, LOAD_OPTION.label) == ("100% LOAD", "LOAD")
    assert len({o.key for o in START_OPTIONS}) == len(START_OPTIONS)
    assert {o.icon for o in START_OPTIONS} == {"play", "folder"}


def test_the_restore_command_is_the_engines_own_snapshot_load() -> None:
    """The instructor's RESTORE: an engine command that exists, the exercise named when it is sent."""
    assert dict(RESTORE_COMMAND) == {"type": "snapshot_load"}
    assert RESTORE_COMMAND["type"] in SIMULATOR_COMMANDS


def test_the_start_up_waits_are_ordered_and_the_status_texts_are_set() -> None:
    assert 0 < STARTUP.poll_ms <= STARTUP.watch_ms <= 1000
    assert STARTUP.engine_timeout_s == 60.0  # run.py's own wait for the engine
    assert STARTUP.packet_timeout_s > 30.0  # the bridge's first-packet allowance; pinned in tests/hmi/test_startup.py
    assert all(t.strip() for t in (STARTUP.building, STARTUP.engine, STARTUP.connecting, STARTUP.releasing,
                                   STARTUP.listing, STARTUP.choosing, STARTUP.no_choice, STARTUP.no_exercises))
    assert STARTUP.restoring.format(name="load100_steam").endswith("load100_steam")
    refusal = STARTUP.refused.format(name="load100_steam", reason="cannot read it")
    assert "load100_steam" in refusal and refusal.endswith("cannot read it")
    assert "chosen" in STARTUP.no_choice and "exercise" in STARTUP.no_exercises          # the status says why
    assert STRINGS.starting.strip()


def test_the_chooser_has_its_texts_and_a_usable_size() -> None:
    assert all(t.strip() for t in (CHOOSER.title, CHOOSER.prompt, CHOOSER.retry, CHOOSER.load, CHOOSER.cancel))
    assert CHOOSER.cancel in CHOOSER.retry and "start buttons" in CHOOSER.retry  # Cancel's outcome, stated
    assert CHOOSER.min_width >= 300 and CHOOSER.min_height >= 200


def test_the_hairline_threshold_sits_between_one_and_two_device_pixels() -> None:
    """Above one pixel (so a 1.25-pixel shell line at 125 % scaling qualifies), below the 2 px streams of a
    100 % display's twice (so wide lines keep their width)."""
    assert 1.0 < HAIRLINE_MAX_PX < 2.0


def test_the_repaint_period_is_about_sixty_a_second() -> None:
    assert 1000.0 / TICK_MS == pytest.approx(60.0, rel=0.05)
    assert intro.FONT_FAMILIES and intro.GRID_MINOR > 0 and intro.GRID_MAJOR_EVERY > 0
