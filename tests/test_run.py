"""`run.py` — which console each mode starts, and the station token each end is given.

Single-machine mode is the default deployment (decided 2026-10-07): the engine and one console on
one machine, the console the superuser. ``--token`` (handoff A-2, closed 2026-10-16) is handed to the
server and to the console alike, from the command line or ``UREASIM_TOKEN``; with neither, none.
"""

from __future__ import annotations

import pytest

import run
from ureasim.net.protocol import Role


def _launched(monkeypatch, argv, tokens=None):
    """The (host, role) of the console `run.main(argv)` would open, and the server it starts;
    the token each was handed is filed in ``tokens`` when given."""
    served, consoles = [], []
    tokens = [] if tokens is None else tokens

    def serve(host, port, token=None):
        served.append(host)
        tokens.append(("server", token))

    def station(host, port, role, name, token=None):
        consoles.append((host, role))
        tokens.append(("station", token))
        return 0
    monkeypatch.setattr(run, "_serve_in_background", serve)
    monkeypatch.setattr(run, "_run_station", station)
    assert run.main(argv) == 0
    return served, consoles


def test_with_no_mode_the_engine_serves_this_machine_and_the_console_is_the_superuser(
        monkeypatch):
    served, consoles = _launched(monkeypatch, [])
    assert served == ["127.0.0.1"]
    assert consoles == [("127.0.0.1", Role.SUPERUSER)]


def test_a_station_still_asks_for_an_operator_by_default(monkeypatch):
    served, consoles = _launched(monkeypatch, ["station", "--host", "10.0.0.5"])
    assert served == []
    assert consoles == [("10.0.0.5", Role.OPERATOR)]


def test_a_role_asked_for_is_the_role_requested(monkeypatch):
    _, consoles = _launched(monkeypatch, ["--role", "instructor"])
    assert consoles == [("127.0.0.1", Role.INSTRUCTOR)]


@pytest.fixture()
def no_env_token(monkeypatch):
    monkeypatch.delenv("UREASIM_TOKEN", raising=False)


def test_with_no_token_neither_end_is_given_one(monkeypatch, no_env_token):
    tokens = []
    _launched(monkeypatch, [], tokens)
    assert tokens == [("server", None), ("station", None)]


def test_the_token_guards_both_ends_of_the_single_machine(monkeypatch, no_env_token):
    tokens = []
    _launched(monkeypatch, ["--token", "class-7"], tokens)
    assert tokens == [("server", "class-7"), ("station", "class-7")]


def test_a_station_presents_the_token_it_is_given(monkeypatch, no_env_token):
    tokens = []
    _launched(monkeypatch, ["station", "--host", "10.0.0.5", "--token", "class-7"], tokens)
    assert tokens == [("station", "class-7")]


def test_the_token_may_come_from_the_environment_and_an_empty_one_is_none(monkeypatch):
    """``UREASIM_TOKEN`` keeps the token out of the process list; an empty token is no token,
    which the server would otherwise refuse to start on."""
    monkeypatch.setenv("UREASIM_TOKEN", "from-env")
    tokens = []
    _launched(monkeypatch, [], tokens)
    assert tokens == [("server", "from-env"), ("station", "from-env")]
    tokens.clear()
    _launched(monkeypatch, ["--token", ""], tokens)
    assert tokens == [("server", None), ("station", None)]
