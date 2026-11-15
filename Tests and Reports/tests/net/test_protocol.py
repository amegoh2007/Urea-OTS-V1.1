"""Framing and message schema.

Pure-Python tests: no sockets, no Qt. The protocol module is the contract between the
engine and its console, so it is exercised on its own before anything binds a port.
"""

from __future__ import annotations

import json

import pytest

from ureasim.net import protocol
from ureasim.net.protocol import FrameReader, Kind, ProtocolError


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
        protocol.hello("s1"),
        protocol.welcome("s1", "engine"),
        protocol.refused("nope"),
        protocol.snapshot(1, 0.0, {}),
        protocol.status("x", "ok"),
        protocol.command(1, {"type": "pump_toggle", "id": "A"}),
        protocol.ack(1, True),
        protocol.event("s1", {"type": "pump_toggle"}, "text"),
        protocol.ping(1),
        protocol.pong(1),
        protocol.history(1, ["a.b"], 60.0),
        protocol.history_paths(1),
        protocol.history_data(1, True, "", {}),
        protocol.exercise_list(1),
        protocol.exercises(1, True),
    ]
    kinds = {m["t"] for m in messages}
    assert kinds == {k.value for k in Kind}


def test_the_handshake_carries_no_role_token_or_sections():
    """The single console (decision 149, 2026-10-22): `hello` names the console and its version,
    `welcome` the engine, and neither carries the multi-station role, token or plant sections; the
    version moved to 2 with them, so a console of the older protocol is refused, not misread."""
    assert protocol.PROTOCOL_VERSION == 2
    assert protocol.hello("s1") == {"t": "hello", "station": "s1", "protocol": 2}
    assert protocol.welcome("s1", "e") == {"t": "welcome", "station": "s1", "protocol": 2,
                                           "engine": "e"}
    assert protocol.event("s1", {"type": "freeze"}, "s1: freeze") == {
        "t": "event", "station": "s1", "cmd": {"type": "freeze"}, "text": "s1: freeze"}
    assert not hasattr(protocol, "Role") and not hasattr(protocol, "is_authorised")


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
# The instructor's list
# --------------------------------------------------------------------------------------

def test_the_exercises_survive_the_wire():
    assert protocol.exercise_list(4) == {"t": "exercise_list", "id": 4}
    answer = list(FrameReader().feed(
        protocol.encode(protocol.exercises(4, True, "", ("a", "b")))))[0]
    assert answer == {"t": "exercises", "id": 4, "ok": True, "reason": "", "names": ["a", "b"]}
    assert protocol.exercises(5, False, "no engine attached")["names"] == []
