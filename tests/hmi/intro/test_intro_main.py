"""Tests of ``ureasim/hmi/intro/__main__.py``: ``python -m ureasim.hmi.intro`` plays the intro on its own.

The event loop is replaced, so no test waits on a window: what is pinned is that the splash is built (full
screen on request), played, and that pressing its button prints the start request and lets it fade.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication

from ureasim.hmi.intro import __main__ as main_module
from ureasim.hmi.intro.splash import IntroSplash


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def spied(app, monkeypatch):
    """The module's QApplication and IntroSplash replaced by an app that does not run a loop and a splash
    that records that it was played."""
    created: list[IntroSplash] = []

    class FakeApp:
        def __init__(self, argv) -> None:
            self.argv = argv

        def exec(self) -> int:
            return 0

        def quit(self) -> None:
            pass

    class SpySplash(IntroSplash):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self.played = False
            created.append(self)

        def play(self) -> None:
            self.played = True

    monkeypatch.setattr(main_module, "QApplication", FakeApp)
    monkeypatch.setattr(main_module, "IntroSplash", SpySplash)
    return created


def test_it_plays_the_intro_windowed_by_default(spied) -> None:
    assert main_module.main(["intro"]) == 0
    assert len(spied) == 1 and spied[0].played and spied[0]._fullscreen is False


def test_it_plays_full_screen_on_request(spied) -> None:
    assert main_module.main(["intro", "--fullscreen"]) == 0
    assert spied[0]._fullscreen is True


def test_pressing_the_button_prints_the_start_request_and_lets_the_splash_fade(spied, capsys) -> None:
    main_module.main(["intro"])
    spied[0].start_requested.emit("load_100")
    assert "start requested: load_100" in capsys.readouterr().out
    assert spied[0]._seq._ready  # mark_ready was called, so the exit fade may begin
