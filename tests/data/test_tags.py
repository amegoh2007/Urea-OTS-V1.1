"""Tag-to-section resolution — what unit assignment stands on.

Every row here is a command shape V1 actually sends. If the resolver gets one wrong, a
trainee is either locked out of their own plant or let into someone else's, and neither
failure is visible on screen.
"""

from __future__ import annotations

import pytest

from ureasim.data import tags


# --------------------------------------------------------------------------------------
# Tag pattern
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("tag,section", [
    ("LIC-322501", "322"),
    ("SIC-321950", "321"),
    ("TT-328011", "328"),
    ("FFIC-335406", "335"),
    ("PIC-329207", "329"),
    ("TIC-323007", "323"),
    ("LV-324501", "324"),
    ("321P002A", "321"),          # equipment tags follow the same rule
    ("329P006B", "329"),
    ("322E003", "322"),
    ("328C003", "328"),
])
def test_section_of_tag(tag, section):
    assert tags.section_of_tag(tag) == section


@pytest.mark.parametrize("tag,section", [
    ("320K002", "322"),           # CO2 compressor: its discharge line is on 322-1
    ("372D001", "328"),           # effluent, downstream of desorption
])
def test_aliased_units_fold_into_the_section_that_works_them(tag, section):
    assert tags.section_of_tag(tag) == section


@pytest.mark.parametrize("tag", [None, "", "BL", "CW TOWER MAKEUP", "MASTER"])
def test_unattributable_tags_return_none(tag):
    assert tags.section_of_tag(tag) is None


def test_unknown_unit_number_is_not_invented():
    """A three-digit number that is not a section must not become one."""
    assert tags.section_of_tag("PI-999001") is None


# --------------------------------------------------------------------------------------
# Command resolution
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("cmd,section", [
    # Generic types carry their target in the payload.
    ({"type": "controller_set", "tag": "LIC-322501"}, "322"),
    ({"type": "controller_set", "tag": "TIC-323007"}, "323"),
    ({"type": "xv_toggle", "id": "321901"}, "321"),
    ({"type": "xv_toggle", "id": "322901"}, "322"),
    ({"type": "keyswitch_set", "id": "HS-322915", "on": True}, "322"),
    ({"type": "aux_pump_toggle", "id": "322P002A"}, "322"),
    ({"type": "aux_pump_toggle", "id": "329P006A"}, "329"),
    # 321P002 A/B are addressed by bare duty letter.
    ({"type": "pump_toggle", "id": "A"}, "321"),
    ({"type": "pump_toggle", "id": "B"}, "321"),
    ({"type": "pump_toggle", "id": "329P006A"}, "329"),
    # Bespoke types are hardwired to one instrument and need the table.
    ({"type": "hic604_set", "v": 50}, "322"),
    ({"type": "lic_set", "sp": 80}, "322"),
    ({"type": "hic323605_set", "v": 10}, "323"),
    # The inline faceplates: attributed by the faceplate the engine acts on, its ``id``.
    ({"type": "r323_ctrl_set", "id": "TIC_323007"}, "323"),
    ({"type": "r323_ctrl_set", "id": "FIC_329402"}, "329"),
    ({"type": "r323_ctrl_set", "id": "LIC_328501"}, "328"),
    ({"type": "r323_ctrl_set", "id": "TIC_324001"}, "324"),
    ({"type": "r323_ctrl_set", "id": "PIC_322201"}, "322"),
    ({"type": "r323_ctrl_set", "id": "FFIC_335406"}, "335"),
    ({"type": "pic329207a_set", "sp": 5.0}, "329"),
    ({"type": "pic329207c_set", "op": 10.0}, "329"),
    # controller_set acts on ``id`` and falls back to ``tag``, and is attributed the same way.
    ({"type": "controller_set", "id": "SIC_321950", "tag": "LIC-323501"}, "321"),
    ({"type": "pic335201_set", "v": 3.0}, "335"),
    ({"type": "lv324501_route_set", "route": "A"}, "324"),
    ({"type": "steam_hpvent_set", "v": 0}, "329"),
    ({"type": "master207_set", "sp": 4.4}, "329"),
    ({"type": "fic_set", "sp": 300}, "329"),
    ({"type": "ratio_set", "sp": 1.928}, "321"),
    ({"type": "ext_override", "on": True}, "321"),
    ({"type": "co2_set", "v": 43.8}, "322"),
    ({"type": "cpl_set", "v": 1200}, "322"),
    # Trip latches: 21_x is unit 321, 22_x is unit 322.
    ({"type": "trip_reset", "id": "21_8"}, "321"),
    ({"type": "trip_reset", "id": "22_2"}, "322"),
])
def test_section_of_command(cmd, section):
    assert tags.section_of_command(cmd) == section


@pytest.mark.parametrize("cmd", [
    {"type": "trip_reset"},                 # clears every latch, plant-wide
    {"type": "trip_reset", "id": "ALL"},
    {"type": "some_future_command"},        # no row yet
    {"type": "controller_set"},             # no tag in the payload
    {"type": "r323_ctrl_set", "tag": "TIC-323007"},   # the engine reads ``id``, not ``tag``
])
def test_unattributable_commands_return_none(cmd):
    """`None` makes an assigned station fail CLOSED — see `ureasim/data/tags.py`."""
    assert tags.section_of_command(cmd) is None


#: One payload of every command type the engine applies, as a console sends it, and the section
#: of the instrument the engine then moves (`ureasim.engine.command`).
ENGINE_TARGETS = {
    "pump_toggle": ({"id": "A"}, "321"),
    "trip_reset": ({"id": "22_2"}, "322"),
    "controller_set": ({"id": "SIC_321951", "mode": "AUTO"}, "321"),
    "ratio_set": ({"sp": 2.0}, "321"),
    "cpl_set": ({"value": 1750.0}, "322"),
    "hic_set": ({"value": 74.0}, "322"),
    "hic2_set": ({"value": 5.0}, "322"),
    "hic605_set": ({"op": 60.0}, "322"),
    "hic604_set": ({"op": 50.0}, "322"),
    "hic9605_set": ({"op": 69.0}, "329"),
    "hic9606_set": ({"op": 80.0}, "329"),
    "hic323605_set": ({"op": 50.0}, "323"),
    "xv_toggle": ({"id": "322903"}, "322"),
    "keyswitch_set": ({"id": "HS-322915", "on": True}, "322"),
    "aux_pump_toggle": ({"id": "328P001B"}, "328"),
    "ext_override": ({"on": True}, "321"),
    "pic_set": ({"mode": "AUTO"}, "322"),
    "lic_set": ({"mode": "AUTO"}, "322"),
    "fic_set": ({"sp": 306.0}, "329"),
    "tic_set": ({"sp": 80.0}, "329"),
    "r323_ctrl_set": ({"id": "LIC_328505", "mode": "AUTO"}, "328"),
    "pic335201_set": ({"value": 3.0}, "335"),
    "lv324501_route_set": ({"route": "A"}, "324"),
    "steam_supply_set": ({"value": 50.0}, "329"),
    "steam_letdown_set": ({"value": 0.0}, "329"),
    "steam_hpvent_set": ({"value": 0.0}, "329"),
    "steam_963_set": ({"value": 0.0}, "329"),
    "hic329602_set": ({"value": 0.0}, "329"),
    "pic329204_set": ({"mode": "AUTO"}, "329"),
    "pic329205_set": ({"mode": "AUTO"}, "329"),
    "lic329502_set": ({"mode": "AUTO"}, "329"),
    "lic329503_set": ({"mode": "AUTO"}, "329"),
    "lic329504_set": ({"mode": "AUTO"}, "329"),
    "pic329207_set": ({"mode": "AUTO"}, "329"),
    "master207_set": ({"on": True}, "329"),
    "pic329207a_set": ({"mode": "AUTO"}, "329"),
    "pic329207b_set": ({"mode": "AUTO"}, "329"),
    "pic329207c_set": ({"mode": "AUTO"}, "329"),
}


def test_every_plant_command_is_attributed_to_the_section_it_moves():
    """No command type the engine applies is missing from the resolver, and each is attributed
    to the section of the instrument the engine moves: a trainee assigned a section can issue
    every command on it and none off it. Malfunctions are the instructor's and never attributed
    (an instructor is unrestricted)."""
    from ureasim.engine.command import PLANT_COMMANDS
    from ureasim.net.protocol import INSTRUCTOR_ONLY_COMMANDS
    operator_types = {t for t in PLANT_COMMANDS if t not in INSTRUCTOR_ONLY_COMMANDS}
    assert operator_types == set(ENGINE_TARGETS)
    for kind, (payload, section) in ENGINE_TARGETS.items():
        assert tags.section_of_command({"type": kind, **payload}) == section, kind


def test_every_bespoke_command_resolves_to_a_real_section():
    """The table is the assignment's blind spot; a row that resolves to nothing is a hole."""
    unresolved = {
        cmd_type: tag for cmd_type, tag in tags.COMMAND_TAGS.items()
        if tags.section_of_command({"type": cmd_type}) is None
    }
    assert not unresolved, f"COMMAND_TAGS rows that resolve to no section: {unresolved}"


# --------------------------------------------------------------------------------------
# Display helpers
# --------------------------------------------------------------------------------------

def test_describe_sections_is_readable():
    assert tags.describe_sections({"323"}) == "323 LP recirculation"
    assert "321" in tags.describe_sections({"321", "329"})
    assert tags.describe_sections(set()) == "none"


def test_screens_of_sections():
    screens = tags.screens_of_sections({"323"})
    assert screens == ["screen-323-1", "screen-323-2"]
    # 324-1b is owned by both 324 and 335; it must appear once.
    both = tags.screens_of_sections({"324", "335"})
    assert both.count("screen-324-1b") == 1


def test_every_section_owns_at_least_one_screen():
    for section_id, meta in tags.SECTIONS.items():
        assert meta["screens"], section_id


def test_section_screens_exist_in_the_layout():
    """A section pointing at a screen the layout does not have would dim a tab that is not
    there once the instructor panel uses `screens_of_sections`."""
    from ureasim.data.screen_layout import SCREENS
    known = {sid for sid, _ in SCREENS}
    for section_id, meta in tags.SECTIONS.items():
        for screen in meta["screens"]:
            assert screen in known, f"{section_id} -> {screen}"
