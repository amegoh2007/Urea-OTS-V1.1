"""Tests of ``ureasim/hmi/intro/__init__.py``: the package's lazy export of the splash window.

The scene, the sequencer and the timeline import without Qt; the window is loaded on first use, so a tool or
a test on a machine with no display never pays for, or needs, PyQt6.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

import ureasim.hmi.intro as intro


def test_the_package_exports_the_splash_window_and_nothing_else() -> None:
    assert intro.__all__ == ["IntroSplash"]


def test_the_splash_is_loaded_on_first_use() -> None:
    pytest.importorskip("PyQt6")
    from ureasim.hmi.intro.splash import IntroSplash

    assert intro.IntroSplash is IntroSplash


def test_an_unknown_name_is_an_attribute_error() -> None:
    with pytest.raises(AttributeError, match="no attribute 'Nothing'"):
        intro.Nothing  # noqa: B018


def test_importing_the_package_and_the_scene_loads_no_qt() -> None:
    """In a fresh interpreter: the package, the scene and the sequencer, and PyQt6 is not in sys.modules."""
    code = (
        "import sys\n"
        "import ureasim.hmi.intro, ureasim.hmi.intro.scene, ureasim.hmi.intro.sequencer, ureasim.hmi.intro.flyby\n"
        "print(any(name.startswith('PyQt6') for name in sys.modules))\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True, cwd=str(_root()))
    assert out.stdout.strip() == "False"


def _root():
    from pathlib import Path

    return Path(__file__).resolve().parents[3]
