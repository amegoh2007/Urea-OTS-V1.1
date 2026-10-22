"""`run.py` — the single-console launch (decided 2026-10-22, `project.md` decision 149).

``python run.py`` starts the engine on the loopback interface and the console attached to it;
there is no server-only or station-only mode, and no role or token to give.
"""

from __future__ import annotations

import pytest

import run


def _launched(monkeypatch, argv):
    """The port the engine `run.main(argv)` would start serves, and the console it would open."""
    served, consoles = [], []

    def serve(port):
        served.append(port)

    def console(port, name):
        consoles.append((port, name))
        return 0
    monkeypatch.setattr(run, "_serve_in_background", serve)
    monkeypatch.setattr(run, "_run_console", console)
    assert run.main(argv) == 0
    return served, consoles


def test_the_engine_and_its_console_start_together_on_one_port(monkeypatch):
    served, consoles = _launched(monkeypatch, ["--port", "8766", "--station", "desk"])
    assert served == [8766] and consoles == [(8766, "desk")]


def test_the_engine_serves_the_loopback_interface_only():
    assert run.DEFAULT_HOST == "127.0.0.1"


@pytest.mark.parametrize("argv", [["server"], ["station"], ["--role", "instructor"],
                                  ["--token", "T"], ["--host", "0.0.0.0"]])
def test_the_multi_station_options_are_gone(argv):
    with pytest.raises(SystemExit):
        run._parse_args(argv)
