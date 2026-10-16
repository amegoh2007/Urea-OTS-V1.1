"""Framing, message schema and role authorisation.

Pure-Python tests: no sockets, no Qt. The protocol module is the contract between the
engine and every console, so it is exercised on its own before anything binds a port.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ureasim.net import protocol
from ureasim.net.protocol import FrameReader, Kind, ProtocolError, Role


# --------------------------------------------------------------------------------------
# Framing
# --------------------------------------------------------------------------------------

def test_round_trip():
    message = protocol.snapshot(7, 123.5, {"a": {"b": 1.0}})
    frames = list(FrameReader().feed(protocol.encode(message)))
    assert frames == [message]


def test_several_frames_in_one_chunk():
    """A single TCP read commonly carries more than one frame."""
    blob = (protocol.encode(protocol.ping(1))
            + protocol.encode(protocol.ping(2))
            + protocol.encode(protocol.ping(3)))
    got = list(FrameReader().feed(blob))
    assert [m["id"] for m in got] == [1, 2, 3]


def test_frame_split_across_reads():
    """A frame arriving in pieces must be held, not mis-parsed.

    This is the case that breaks a naive reader, and it is guaranteed to happen with a
    snapshot large enough to exceed the socket's read size.
    """
    blob = protocol.encode(protocol.snapshot(1, 0.0, {"x": list(range(500))}))
    reader = FrameReader()
    got = []
    for i in range(0, len(blob), 97):              # deliberately not a frame boundary
        got.extend(reader.feed(blob[i:i + 97]))
    assert len(got) == 1
    assert got[0]["seq"] == 1
    assert reader.pending_bytes == 0


def test_partial_frame_is_held_not_yielded():
    blob = protocol.encode(protocol.ping(1))
    reader = FrameReader()
    assert list(reader.feed(blob[:-1])) == []
    assert reader.pending_bytes == len(blob) - 1
    assert [m["id"] for m in reader.feed(blob[-1:])] == [1]


def test_reset_discards_a_partial_frame():
    reader = FrameReader()
    list(reader.feed(protocol.encode(protocol.ping(1))[:5]))
    assert reader.pending_bytes > 0
    reader.reset()
    assert reader.pending_bytes == 0


def test_oversized_declared_length_is_refused():
    """A corrupt header must fail immediately, not stall waiting for bytes that never come."""
    header = (protocol.MAX_FRAME_BYTES + 1).to_bytes(4, "big")
    with pytest.raises(ProtocolError):
        list(FrameReader().feed(header + b"x"))


def test_undecodable_body_is_refused():
    body = b"{not json"
    frame = len(body).to_bytes(4, "big") + body
    with pytest.raises(ProtocolError):
        list(FrameReader().feed(frame))


def test_untagged_object_is_refused():
    body = json.dumps({"no": "tag"}).encode()
    frame = len(body).to_bytes(4, "big") + body
    with pytest.raises(ProtocolError):
        list(FrameReader().feed(frame))


def test_nan_is_refused_at_encode():
    """NaN is not valid JSON, and a silently emitted `NaN` token breaks strict parsers.

    A NaN reaching the wire means a solver diverged; that must surface as an error in the
    engine, not as an unparseable frame on every console.
    """
    with pytest.raises(ValueError):
        protocol.encode(protocol.snapshot(1, 0.0, {"x": float("nan")}))


def test_encoding_is_compact():
    """No whitespace padding: at 10 Hz the default separators cost real bandwidth."""
    blob = protocol.encode(protocol.snapshot(1, 0.0, {"a": 1, "b": 2}))
    assert b", " not in blob and b'": ' not in blob


# --------------------------------------------------------------------------------------
# Message constructors
# --------------------------------------------------------------------------------------

def test_every_constructor_tags_its_message():
    messages = [
        protocol.hello(Role.OPERATOR, "s1"),
        protocol.welcome(Role.OPERATOR, "s1", "engine"),
        protocol.assignment("s1", ["323"]),
        protocol.refused("nope"),
        protocol.snapshot(1, 0.0, {}),
        protocol.status("x", "ok"),
        protocol.command(1, {"type": "pump_toggle", "id": "A"}),
        protocol.ack(1, True),
        protocol.event("s1", Role.OPERATOR, {"type": "pump_toggle"}, "text"),
        protocol.ping(1),
        protocol.pong(1),
        protocol.history(1, ["a.b"], 60.0),
        protocol.history_paths(1),
        protocol.history_data(1, True, "", {}),
        protocol.roster([]),
        protocol.exercise_list(1),
        protocol.exercises(1, True),
    ]
    kinds = {m["t"] for m in messages}
    assert kinds == {k.value for k in Kind}


def test_a_hello_carries_the_station_token_only_when_it_has_one():
    """The station login (handoff A-2, closed 2026-10-16): with no token the ``hello`` is the
    message it always was, so a token-less engine and its consoles see no change."""
    assert protocol.hello(Role.OPERATOR, "s1") == {
        "t": "hello", "role": "operator", "station": "s1", "protocol": protocol.PROTOCOL_VERSION}
    sent = list(FrameReader().feed(protocol.encode(
        protocol.hello(Role.INSTRUCTOR, "s1", "class-7"))))[0]
    assert sent["token"] == "class-7" and sent["role"] == "instructor"


def test_a_history_request_names_its_pens_and_window():
    """V1's ``/api/hist`` arguments, carried as one message; the answer carries the id back."""
    req = protocol.history(4, ("RECIRC_323.C003.TIC_323007.pv",), 3600.0, 400, 120.0)
    assert req == {"t": "history", "id": 4, "paths": ["RECIRC_323.C003.TIC_323007.pv"],
                   "span": 3600.0, "max_points": 400, "end": 120.0}
    assert protocol.history_data(4, False, "why")["reason"] == "why"


def test_command_dict_is_copied():
    """The caller's dict must not be aliased into a queued message."""
    cmd = {"type": "pump_toggle", "id": "A"}
    message = protocol.command(1, cmd)
    cmd["id"] = "B"
    assert message["cmd"]["id"] == "A"


def test_ack_refusal_carries_a_reason():
    assert protocol.ack(3, False, "latched trip 21_2")["reason"] == "latched trip 21_2"


# --------------------------------------------------------------------------------------
# Role authorisation
# --------------------------------------------------------------------------------------

#: Plant commands V1's operator screens exposed. An operator station must keep every one:
#: re-classifying a plant control would change what a trainee is being taught.
OPERATOR_COMMANDS = [
    "pump_toggle", "xv_toggle", "aux_pump_toggle", "trip_reset", "ext_override",
    "controller_set", "ratio_set", "cpl_set",
    "hic_set", "hic2_set", "hic605_set", "pic_set", "lic_set", "hic604_set",
    "steam_supply_set", "steam_letdown_set", "master207_set", "fic_set", "tic_set",
    "r323_ctrl_set", "lv324501_route_set",
    "keyswitch_set",      # HS-322915, XV-322915's only operator input (B-59)
]

#: Simulator controls — not plant equipment — and the one boundary the instructor sets.
INSTRUCTOR_COMMANDS = [
    "trigger_fault", "clear_fault", "reset_sim", "set_sim_mode",
    "freeze", "snapshot_save", "snapshot_load", "assign", "co2_set",
]


@pytest.mark.parametrize("cmd", OPERATOR_COMMANDS)
def test_operator_keeps_every_v1_plant_command(cmd):
    assert protocol.is_authorised(Role.OPERATOR, cmd)
    assert protocol.is_authorised(Role.INSTRUCTOR, cmd)


@pytest.mark.parametrize("cmd", INSTRUCTOR_COMMANDS)
def test_simulator_controls_are_instructor_only(cmd):
    assert protocol.is_authorised(Role.INSTRUCTOR, cmd)
    assert not protocol.is_authorised(Role.OPERATOR, cmd)


def test_the_co2_rate_is_the_instructors_boundary_decided_divergence():
    """320K002 is a boundary feed outside the simulated plant (decided 2026-10-08): V1's operator
    screen 322-1 carried its COMPRESSOR SPEED hand station (``frontend/co2_compressor.js``, which
    sends ``co2_set``); the rewrite gives the battery-limit CO2 rate to the instructor alone."""
    js = Path(r"D:/Work/Urea Simulation/frontend/co2_compressor.js")
    if js.exists():
        assert "type:'co2_set'" in js.read_text(encoding="utf-8", errors="replace")
    assert "co2_set" in protocol.INSTRUCTOR_ONLY_COMMANDS
    assert not protocol.is_authorised(Role.OPERATOR, "co2_set")
    assert protocol.is_authorised(Role.INSTRUCTOR, "co2_set")


def test_fault_suffix_form_is_also_gated():
    """V1 accepted fault injection through its generic `set` handler by tag suffix.

    A trainee who can clear their own malfunction is not being trained, so the suffix form
    is gated too — otherwise the role check would be trivially bypassable.
    """
    assert not protocol.is_authorised(Role.OPERATOR, "pumpA_fault")
    assert protocol.is_authorised(Role.INSTRUCTOR, "pumpA_fault")


@pytest.mark.parametrize("cmd", OPERATOR_COMMANDS + INSTRUCTOR_COMMANDS)
def test_observer_commands_nothing(cmd):
    assert not protocol.is_authorised(Role.OBSERVER, cmd)


@pytest.mark.parametrize("cmd", OPERATOR_COMMANDS + INSTRUCTOR_COMMANDS
                         + ["pumpA_fault", "a_command_no_table_names"])
def test_the_superuser_is_refused_nothing(cmd):
    """The single-machine console (decided 2026-10-07): no command type
    is refused for its role."""
    assert protocol.is_authorised(Role.SUPERUSER, cmd)


def test_the_superuser_runs_the_exercise_and_only_on_its_own_machine():
    assert protocol.runs_the_exercise(Role.SUPERUSER)
    assert protocol.runs_the_exercise(Role.INSTRUCTOR)
    assert not protocol.runs_the_exercise(Role.OPERATOR)
    assert not protocol.runs_the_exercise(Role.OBSERVER)
    assert protocol.LOCAL_ONLY_ROLES == {Role.SUPERUSER}


# --------------------------------------------------------------------------------------
# Assignment message
# --------------------------------------------------------------------------------------

def test_assignment_distinguishes_unrestricted_from_assigned_nothing():
    """`None` and `[]` are different states and must survive the wire as different states.

    `None` means the instructor has not narrowed this station; `[]` means they narrowed it
    to nothing. A console shows the second in red and says nothing for the first.
    """
    unrestricted = list(FrameReader().feed(
        protocol.encode(protocol.assignment("s1", None))))[0]
    nothing = list(FrameReader().feed(
        protocol.encode(protocol.assignment("s1", []))))[0]
    assert unrestricted["sections"] is None
    assert nothing["sections"] == []


def test_welcome_carries_the_assignment():
    message = protocol.welcome(Role.OPERATOR, "s1", "e", {"329", "323"})
    assert message["sections"] == ["323", "329"]          # sorted, for a stable display
    assert protocol.welcome(Role.OPERATOR, "s1", "e")["sections"] is None


# --------------------------------------------------------------------------------------
# The instructor's lists
# --------------------------------------------------------------------------------------

def test_the_roster_and_the_exercises_survive_the_wire():
    roster = list(FrameReader().feed(protocol.encode(protocol.roster(
        [{"station": "s1", "role": "operator", "sections": None}]))))[0]
    assert roster == {"t": "roster",
                      "stations": [{"station": "s1", "role": "operator", "sections": None}]}
    assert protocol.exercise_list(4) == {"t": "exercise_list", "id": 4}
    answer = protocol.exercises(4, True, "", ("a", "b"))
    assert answer == {"t": "exercises", "id": 4, "ok": True, "reason": "", "names": ["a", "b"]}
    assert protocol.exercises(5, False, "no engine attached")["names"] == []
