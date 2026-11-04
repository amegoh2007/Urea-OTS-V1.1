"""Tests of ``ureasim/data/intro_plant.py``: the equipment, nozzles and pipes read from flow sheets 322-1 and
322-2, checked against what the slides say, without building the wireframe.

The expected tables below are written out from the two slides (their lines, arrow heads and tagged valves)
and from ``project.md`` section 1; they are deliberately not computed from the data they check. The tests of
the mesh built from these tables are in ``tests/hmi/intro/test_intro_model3d.py``.
"""

from __future__ import annotations

from collections import defaultdict

from ureasim.data.intro_plant import (
    BLOCKS,
    DRUMS,
    PIPES,
    PUMPS,
    REACTOR,
    SCRUBBER,
    STREAMS,
    VESSELS,
)

_EQUIPMENT_ON_THE_SLIDES = {
    "322R001", "322E001", "322E002", "322E003", "322F001", "322D001", "322C001", "323C003", "320K002",
    "321P002A/B", "323P001A/B", "329P006A/B", "329E004",
}  # fmt: skip


# (stream, from, to): one row per line of the slides, in the direction of its arrow.
_LINES_ON_THE_SLIDES = {
    ("gas", "320K002", "322E001"),  # 322-1: CO2 compressor to the stripper's bottom
    ("gas", "320K002", "@VENT"),  # 322-1: PV-322203's vent branch
    ("liquid", "321P002A/B", "322F001"),  # 322-2: NH3 up to the ejector (motive)
    ("liquid", "322E003", "322F001"),  # 322-2: scrubber overflow to the ejector (suction)
    ("liquid", "322F001", "322E002"),  # 322-1: ejector to the condenser top
    ("gas", "322E001", "322E002"),  # 322-1: stripper top gas to the condenser top
    ("liquid", "322E002", "322R001"),  # 322-1: condenser outlet to the reactor bottom
    ("liquid", "322R001", "322E001"),  # 322-1: reactor liquid through HV-322605 to the stripper top
    ("gas", "322R001", "322E003"),  # 322-1 and 322-2: reactor top gas to the scrubber head
    ("liquid", "323P001A/B", "322E003"),  # 322-2: carbamate to the scrubber head
    ("gas", "322E003", "322C001"),  # 322-2: scrubber vent through HV-322604 to the absorber
    ("gas", "322E003", "322E003"),  # 322-2: the head's gas goes down outside and enters the shaft bottom
    ("liquid", "322E001", "323C003"),  # 322-1: stripper bottoms through LV-322501 to the column
    ("steam", "322E002", "322D001"),  # 322-1: red line, condenser shell to the steam drum
    ("water", "322D001", "322E002"),  # 322-1: green line, drum water back to the condenser shell
    ("steam", "@EXTR STEAM", "322E001"),  # 322-1: extraction steam into the stripper
    ("water", "322E001", "@CONDENSATE"),  # 322-1: stripper condensate out
    ("water", "322E003", "329P006A/B"),  # 322-2: scrubber shell water to the pumps
    ("water", "329P006A/B", "322E003"),  # 322-2: pumps through FV-329409 to the scrubber shell
    ("water", "329P006A/B", "329E004"),  # 322-2: branch to the cooler
    ("water", "329E004", "322E003"),  # 322-2: cooler through TV-329005 back to the shell line
}  # fmt: skip


# The tagged valves on each line, in the order the slide draws them along it.
_VALVES_ON_THE_SLIDES = {
    "CO2 to stripper": ["XV-322902"],
    "CO2 vent": ["PV-322203"],
    "NH3 to ejector": ["XV-322903"],
    "reactor to stripper": ["HV-322605"],
    "scrubber vent to absorber": ["HV-322604"],
    "stripper bottoms to column": ["LV-322501"],
    "pumps to scrubber water inlet": ["FV-329409"],
    "cooler to scrubber water inlet": ["TV-329005"],
}


_PLAIN_VALVES = {"XV-322902", "XV-322903"}  # drawn without an actuator on the slides


def _equipment():
    return [REACTOR, SCRUBBER, *VESSELS, *DRUMS, *BLOCKS, *PUMPS]


def _graph():
    g: dict[str, set[str]] = defaultdict(set)
    for p in PIPES:
        g[p.src].add(p.dst)
    return g


def _reaches(g, a: str, b: str) -> bool:
    seen, todo = {a}, [a]
    while todo:
        for n in g[todo.pop()]:
            if n == b:
                return True
            if n not in seen:
                seen.add(n)
                todo.append(n)
    return False


def test_every_item_of_the_slides_is_drawn_and_nothing_else() -> None:
    tags = [e.tag for e in _equipment()]
    assert set(tags) == _EQUIPMENT_ON_THE_SLIDES
    assert len(tags) == len(set(tags))


def test_what_each_tag_is_matches_the_plant_scope_table() -> None:
    """project.md section 1: the HP loop's equipment; 320K002 is the boundary-feed CO2 compressor."""
    role = {e.tag: e.role for e in _equipment()}
    assert role["322E001"] == "HP stripper" and role["322E002"] == "HP carbamate condenser"
    assert role["322R001"] == "reactor" and role["322E003"] == "HP scrubber" and role["322F001"] == "HP ejector"
    assert role["320K002"] == "CO2 compressor" and role["322C001"] == "LP absorber"
    assert role["323C003"] == "rectifying column"


def test_stream_colours_are_the_four_of_the_slides() -> None:
    assert {s.name: s.sheet_color for s in STREAMS} == {"gas": "#FFFF00", "liquid": "#D86ECC", "steam": "#FF0000", "water": "#4EA72E"}
    assert {p.stream for p in PIPES} <= {s.name for s in STREAMS}


def test_the_lines_are_exactly_the_lines_of_the_slides_in_their_direction() -> None:
    drawn = [(p.stream, p.src, p.dst) for p in PIPES]
    assert len(drawn) == len(set(drawn))
    assert set(drawn) == _LINES_ON_THE_SLIDES


def test_no_line_is_drawn_backwards() -> None:
    """A line the slides draw A to B must not also exist as B to A (the scrubber water loop is two lines, not one)."""
    drawn = {(p.src, p.dst) for p in PIPES}
    for a, b in drawn:
        if a != b and (b, a) in drawn:
            assert {a, b} == {"322E003", "329P006A/B"} or {a, b} == {"322D001", "322E002"}, (a, b)


def test_the_process_runs_in_the_order_of_the_slides() -> None:
    g = _graph()
    # CO2 enters the stripper bottom, its gas goes to the condenser, the condenser feeds the reactor,
    # the reactor feeds the stripper top and the scrubber, the stripper bottoms leave for the column.
    chain = ["320K002", "322E001", "322E002", "322R001", "322E003", "322C001"]
    for a, b in zip(chain, chain[1:]):
        assert _reaches(g, a, b), (a, b)
    assert "322E002" in g["322F001"] and "322F001" in g["321P002A/B"] and "322F001" in g["322E003"]
    assert "323C003" in g["322E001"]
    assert "322E001" in g["322R001"] and "322E003" in g["322R001"] and "322R001" in g["322E002"]
    # the HP loop closes: condenser to reactor to stripper to condenser
    assert _reaches(g, "322E002", "322E002")
    # the products and vents leave the drawing: nothing leaves the column or the absorber on these sheets
    assert not g["323C003"] and not g["322C001"]
    # NH3 does not reach the reactor except through the ejector and the condenser
    assert not any("322R001" in g[n] for n in ("321P002A/B", "322F001"))


def test_valves_sit_on_the_lines_the_slides_put_them_on_in_order() -> None:
    on_lines = {p.name: [v.tag for v in p.valves] for p in PIPES if p.valves}
    assert on_lines == _VALVES_ON_THE_SLIDES
    tags = [v.tag for p in PIPES for v in p.valves]
    assert len(tags) == len(set(tags))
    for p in PIPES:
        for v in p.valves:
            assert v.control == (v.tag not in _PLAIN_VALVES), v.tag
